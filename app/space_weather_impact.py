"""
Space Weather Impact Prediction Module

Computes arrival times for different space-weather energy carriers at Earth and
provides Polar H10 monitoring recommendations.

Accuracy note:
- Photon/SEP/geomagnetic values are *observations at/near Earth* (arrival is effectively "now").
- Solar wind plasma is measured at L1 (DSCOVR/ACE) and propagated ballistically to Earth (~30–60 min).
- CME/shock arrivals are *model-based forecasts* (NASA DONKI WSA+ENLIL) and carry uncertainty.

Energy categories tracked:
1. Photons/X-rays (instantaneous ~8.3 min from Sun)
2. Solar Energetic Particles (SEPs) - minutes to hours
3. Solar Wind plasma from L1 - ~30-60 min
4. CME/Shock arrivals - hours to days (via physics-based models)

All times computed for Bogotá, Colombia (UTC-5).
"""

from __future__ import annotations

import datetime
import logging
import math
import os
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Final, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import requests

try:
    # When running as a package (tests)
    from app.logging_config import get_logger, log_exception
except ImportError:  # pragma: no cover - fallback for script execution
    from logging_config import get_logger, log_exception

try:
    # Streamlit-free CME propagation helpers (DBM)
    from app.space_weather_influence import estimate_cme_arrival_range_utc
except ImportError:  # pragma: no cover - fallback for script execution
    from space_weather_influence import estimate_cme_arrival_range_utc  # type: ignore[no-redef]

_LOGGER: Final[logging.Logger] = get_logger(__name__)

_HTTP_SESSION_LOCAL = threading.local()


def _get_http_session() -> requests.Session:
    """Return a thread-local HTTP session configured for connection pooling.

    This module is frequently called from Streamlit callbacks and may execute
    multiple sequential SWPC requests (e.g., plasma + mag). Pooling reduces
    repeated TLS handshakes and lowers latency without introducing shared
    mutable session state across threads.
    """

    session = getattr(_HTTP_SESSION_LOCAL, "session", None)
    if session is None:
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=8,
            pool_maxsize=8,
            max_retries=0,
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        _HTTP_SESSION_LOCAL.session = session
    return session

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BOGOTA_TZ: Final[datetime.timezone] = datetime.timezone(datetime.timedelta(hours=-5))
BOGOTA_TZ_NAME: Final[str] = "COT (UTC-5)"

# L1 (Lagrange point) to Earth distance
L1_EARTH_DISTANCE_KM: Final[float] = 1_500_000.0

# Sun to Earth (1 AU)
AU_KM: Final[float] = 149_597_870.7
LIGHT_SPEED_KM_S: Final[float] = 299_792.458
SUN_EARTH_LIGHT_MINUTES: Final[float] = AU_KM / LIGHT_SPEED_KM_S / 60.0  # ~8.3 min

# IAU nominal solar radius (km) (used to adjust propagation distance when using DONKI `time21_5`)
SOLAR_RADIUS_KM: Final[float] = 695_700.0

# NOAA SWPC endpoints
SWPC_BASE_URL: Final[str] = "https://services.swpc.noaa.gov"
REQUEST_TIMEOUT: Final[float] = 5.0  # Reduced from 15.0 for faster failure

ENDPOINTS: Final[Dict[str, str]] = {
    "xray_1day": f"{SWPC_BASE_URL}/json/goes/primary/xrays-1-day.json",
    "proton_1day": f"{SWPC_BASE_URL}/json/goes/primary/integral-protons-1-day.json",
    "solar_wind_plasma": f"{SWPC_BASE_URL}/products/solar-wind/plasma-1-day.json",
    "solar_wind_mag": f"{SWPC_BASE_URL}/products/solar-wind/mag-1-day.json",
    "enlil_forecast": f"{SWPC_BASE_URL}/products/animations/enlil.json",
    "kp_1min": f"{SWPC_BASE_URL}/json/planetary_k_index_1m.json",
    "dst_1hour": f"{SWPC_BASE_URL}/json/geospace/geospace_dst_1_hour.json",
    "ace_epam": f"{SWPC_BASE_URL}/products/solar-wind/epam-1-day.json",
}

# NASA DONKI (WSA+ENLIL) endpoint for CME/shock arrival forecasts
DONKI_API_BASE: Final[str] = "https://api.nasa.gov/DONKI"
DONKI_TIMEOUT: Final[float] = 10.0
DONKI_ENLIL_ENDPOINT: Final[str] = f"{DONKI_API_BASE}/WSAEnlilSimulations"


# ---------------------------------------------------------------------------
# Enums and Data Classes
# ---------------------------------------------------------------------------


class ImpactSeverity(Enum):
    """Severity classification for space weather impacts."""
    
    QUIET = "quiet"
    MINOR = "minor"
    MODERATE = "moderate"
    STRONG = "strong"
    SEVERE = "severe"
    EXTREME = "extreme"


class EnergyCategory(Enum):
    """Categories of solar energy arriving at Earth."""
    
    PHOTON = "photon"           # X-rays, EUV, radio
    PARTICLE_SEP = "sep"        # Solar Energetic Particles (protons)
    PLASMA_L1 = "plasma_l1"     # Solar wind from L1
    CME_SHOCK = "cme_shock"     # CME-driven shock
    HSS = "hss"                 # High-speed stream
    GEOMAGNETIC = "geomagnetic" # Secondary geomagnetic effects


@dataclass(frozen=True, slots=True)
class ImpactEvent:
    """Represents a predicted or observed space weather impact event."""
    
    category: EnergyCategory
    severity: ImpactSeverity
    observation_time_utc: datetime.datetime
    arrival_time_utc: datetime.datetime
    arrival_time_bogota: datetime.datetime
    travel_time_minutes: float
    source_description: str
    biological_effect: str
    polar_h10_recommendation: str
    raw_value: float = float("nan")
    unit: str = ""
    confidence: float = 1.0  # 0-1 confidence in prediction


@dataclass(slots=True)
class SpaceWeatherSnapshot:
    """Complete snapshot of current space weather conditions."""
    
    timestamp_utc: datetime.datetime
    timestamp_bogota: datetime.datetime
    photon_event: Optional[ImpactEvent] = None
    sep_event: Optional[ImpactEvent] = None
    plasma_event: Optional[ImpactEvent] = None
    cme_event: Optional[ImpactEvent] = None
    geomagnetic_event: Optional[ImpactEvent] = None
    errors: Dict[str, str] = field(default_factory=dict)
    
    def all_events(self) -> List[ImpactEvent]:
        """Return all non-None events sorted by arrival time."""
        events = [
            self.photon_event,
            self.sep_event,
            self.plasma_event,
            self.cme_event,
            self.geomagnetic_event,
        ]
        valid = [e for e in events if e is not None]
        return sorted(valid, key=lambda x: x.arrival_time_utc)
    
    def next_impact(self) -> Optional[ImpactEvent]:
        """Return the next predicted impact event."""
        now = datetime.datetime.now(datetime.timezone.utc)
        future = [e for e in self.all_events() if e.arrival_time_utc > now]
        if not future:
            return None
        return min(future, key=lambda x: x.arrival_time_utc)
    
    def most_severe(self) -> Optional[ImpactEvent]:
        """Return the most severe current/upcoming event."""
        events = self.all_events()
        if not events:
            return None
        severity_order = [
            ImpactSeverity.EXTREME,
            ImpactSeverity.SEVERE,
            ImpactSeverity.STRONG,
            ImpactSeverity.MODERATE,
            ImpactSeverity.MINOR,
            ImpactSeverity.QUIET,
        ]
        for severity in severity_order:
            for event in events:
                if event.severity == severity:
                    return event
        return events[0]


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _safe_float(val: Any, default: float = float("nan")) -> float:
    """Safely convert value to float."""
    if val is None:
        return default
    try:
        result = float(val)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def _parse_iso_utc(ts: Any) -> Optional[datetime.datetime]:
    """Parse ISO 8601 timestamp to aware UTC datetime."""
    if ts is None:
        return None
    if isinstance(ts, datetime.datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=datetime.timezone.utc)
        return ts.astimezone(datetime.timezone.utc)
    if not isinstance(ts, str):
        return None
    ts_str = ts.strip()
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except ValueError:
        return None


_P10_ENERGY_LABEL_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?:>=|>)\s*10(?:\.0)?\s*mev\s*$",
    flags=re.IGNORECASE,
)


def _is_p10_energy_label(energy: Any) -> bool:
    """Return True if DONKI/SWPC label represents the NOAA S-scale >10 MeV channel."""
    if not isinstance(energy, str):
        return False
    return bool(_P10_ENERGY_LABEL_RE.match(energy.strip()))


def utc_to_bogota(dt_utc: datetime.datetime) -> datetime.datetime:
    """Convert UTC datetime to Bogotá timezone."""
    return dt_utc.astimezone(BOGOTA_TZ)


def format_datetime_bogota(dt: datetime.datetime) -> str:
    """Format datetime in Bogotá timezone for display."""
    bogota_time = dt.astimezone(BOGOTA_TZ)
    return bogota_time.strftime("%Y-%m-%d %H:%M:%S") + f" {BOGOTA_TZ_NAME}"


def format_countdown(delta: datetime.timedelta) -> str:
    """Format timedelta as human-readable countdown."""
    total_seconds = delta.total_seconds()
    if total_seconds < 0:
        return "Already arrived"
    if total_seconds < 60:
        return f"{total_seconds:.0f} seconds"
    if total_seconds < 3600:
        minutes = total_seconds / 60
        return f"{minutes:.1f} minutes"
    if total_seconds < 86400:
        hours = total_seconds / 3600
        return f"{hours:.1f} hours"
    days = total_seconds / 86400
    return f"{days:.1f} days"


# ---------------------------------------------------------------------------
# X-ray / Photon Analysis
# ---------------------------------------------------------------------------


def _classify_xray_flux(flux_long: float, flux_short: float) -> Tuple[str, ImpactSeverity, str]:
    """Classify X-ray flare and return (class, severity, bio_effect)."""
    flux = flux_long if math.isfinite(flux_long) else flux_short
    if not math.isfinite(flux) or flux <= 0:
        return "N/A", ImpactSeverity.QUIET, "No significant ionospheric disturbance expected."
    
    if flux >= 1e-3:
        cls = f"X{flux/1e-3:.1f}"
        severity = ImpactSeverity.EXTREME
        bio_effect = (
            "EXTREME ionospheric disturbance. High SEP/CME probability. "
            "Studies associate with HRV decreases and cardiovascular stress."
        )
    elif flux >= 1e-4:
        cls = f"M{flux/1e-4:.1f}"
        severity = ImpactSeverity.STRONG
        bio_effect = (
            "Strong ionospheric effects. Moderate SEP/CME risk. "
            "Monitor for autonomic responses 0-6h post-flare."
        )
    elif flux >= 1e-5:
        cls = f"C{flux/1e-5:.1f}"
        severity = ImpactSeverity.MINOR
        bio_effect = (
            "Minor ionospheric effects. Low SEP risk. "
            "Background recording recommended for comparison."
        )
    elif flux >= 1e-6:
        cls = f"B{flux/1e-6:.1f}"
        severity = ImpactSeverity.QUIET
        bio_effect = "Background solar activity. Normal HRV expected."
    else:
        cls = f"A{flux/1e-7:.1f}"
        severity = ImpactSeverity.QUIET
        bio_effect = "Quiet Sun conditions. Ideal for baseline recordings."
    
    return cls, severity, bio_effect


def fetch_xray_impact() -> Tuple[Optional[ImpactEvent], Optional[str]]:
    """Fetch and analyze X-ray flux for photon impact."""
    try:
        response = _get_http_session().get(ENDPOINTS["xray_1day"], timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        return None, f"X-ray fetch failed: {exc}"
    except ValueError as exc:
        return None, f"X-ray JSON parse failed: {exc}"
    
    if not isinstance(data, list) or len(data) == 0:
        return None, "No X-ray data available"
    
    short_band: Optional[Dict[str, Any]] = None
    long_band: Optional[Dict[str, Any]] = None
    
    for record in reversed(data):
        if not isinstance(record, dict):
            continue
        energy = record.get("energy", "")
        if short_band is None and energy == "0.05-0.4nm":
            short_band = record
        if long_band is None and energy == "0.1-0.8nm":
            long_band = record
        if short_band is not None and long_band is not None:
            break
    
    if short_band is None and long_band is None:
        return None, "No X-ray band data found"
    
    ref = long_band or short_band
    if ref is None:
        return None, "No X-ray reference record"
    
    obs_time = _parse_iso_utc(ref.get("time_tag"))
    if obs_time is None:
        return None, "Invalid X-ray timestamp"
    
    flux_short = _safe_float(short_band.get("flux") if short_band else None)
    flux_long = _safe_float(long_band.get("flux") if long_band else None)
    
    cls, severity, bio_effect = _classify_xray_flux(flux_long, flux_short)
    
    # Photons arrive ~8.3 minutes after emission at Sun surface
    # But we observe at Earth, so "arrival" is essentially observation time
    arrival_utc = obs_time
    arrival_bogota = utc_to_bogota(arrival_utc)
    
    recommendation = _get_polar_recommendation_photon(severity)
    
    event = ImpactEvent(
        category=EnergyCategory.PHOTON,
        severity=severity,
        observation_time_utc=obs_time,
        arrival_time_utc=arrival_utc,
        arrival_time_bogota=arrival_bogota,
        travel_time_minutes=0.0,  # Already at Earth
        source_description=f"X-ray flare class {cls}",
        biological_effect=bio_effect,
        polar_h10_recommendation=recommendation,
        raw_value=flux_long if math.isfinite(flux_long) else flux_short,
        unit="W/m²",
        confidence=1.0,
    )
    return event, None


def _get_polar_recommendation_photon(severity: ImpactSeverity) -> str:
    """Get Polar H10 recommendation for photon events."""
    if severity == ImpactSeverity.EXTREME:
        return (
            "🔴 IMMEDIATE: Begin continuous Polar H10 monitoring NOW. "
            "X-class flare detected—high probability of SEP/CME follow-up. "
            "Record for next 6-12 hours for acute autonomic response capture."
        )
    if severity == ImpactSeverity.SEVERE:
        return (
            "🟠 ALERT: Prepare Polar H10. Strong flare detected. "
            "Monitor for SEP onset in next 1-6 hours. "
            "Start recording 30 min before expected particle arrival."
        )
    if severity == ImpactSeverity.STRONG:
        return (
            "🟡 STANDBY: M-class flare. Moderate SEP/CME potential. "
            "Have Polar H10 ready. Begin 5-min baseline recording now, "
            "then monitor news for CME confirmation."
        )
    if severity == ImpactSeverity.MODERATE:
        return (
            "🟢 ROUTINE: Minor flare activity. "
            "Record 5-min baseline for comparison dataset."
        )
    return (
        "⚪ QUIET: Background conditions. "
        "Ideal time for baseline Polar H10 recording (control data)."
    )


# ---------------------------------------------------------------------------
# Solar Energetic Particles (SEPs / Protons)
# ---------------------------------------------------------------------------


def _classify_sep_flux(p10_flux: float) -> Tuple[str, ImpactSeverity, str]:
    """Classify SEP event by >10 MeV proton flux (pfu)."""
    if not math.isfinite(p10_flux) or p10_flux < 10:
        return "No SEP event", ImpactSeverity.QUIET, "Background radiation. No elevated exposure."
    
    if p10_flux >= 100000:
        return "S5 (Extreme)", ImpactSeverity.EXTREME, (
            "Extreme radiation environment. Maximum biological exposure. "
            "Studies show significant HRV perturbations during extreme events."
        )
    if p10_flux >= 10000:
        return "S4 (Severe)", ImpactSeverity.SEVERE, (
            "Severe radiation storm. High aviation/astronaut risk. "
            "Potential cardiovascular and autonomic stress responses."
        )
    if p10_flux >= 1000:
        return "S3 (Strong)", ImpactSeverity.STRONG, (
            "Strong radiation storm. Elevated dose at altitude. "
            "Monitor HRV for stress signatures 0-24h post-onset."
        )
    if p10_flux >= 100:
        return "S2 (Moderate)", ImpactSeverity.MODERATE, (
            "Moderate radiation. Minor satellite effects. "
            "Small but detectable autonomic changes possible."
        )
    return "S1 (Minor)", ImpactSeverity.MINOR, (
        "Minor SEP enhancement. Slight dose increase at altitude. "
        "Record for research correlation with minor effects."
    )


def fetch_sep_impact() -> Tuple[Optional[ImpactEvent], Optional[str]]:
    """Fetch and analyze proton flux for SEP impact."""
    try:
        response = _get_http_session().get(ENDPOINTS["proton_1day"], timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        return None, f"Proton fetch failed: {exc}"
    except ValueError as exc:
        return None, f"Proton JSON parse failed: {exc}"
    
    if not isinstance(data, list) or len(data) == 0:
        return None, "No proton data available"

    # NOAA S-scale is defined on integral proton flux >10 MeV (pfu).
    # The SWPC "integral-protons-1-day.json" contains multiple energy channels
    # (>=10, >=30, >=50, >=60, >=100, etc.). For accuracy, we MUST select the
    # >=10 MeV channel specifically (not simply the most recent record).
    ref: Optional[Dict[str, Any]] = None
    obs_time: Optional[datetime.datetime] = None
    p10_flux = float("nan")
    sat: Optional[Any] = None
    for rec in reversed(data):
        if not isinstance(rec, dict):
            continue
        if not _is_p10_energy_label(rec.get("energy")):
            continue
        parsed = _parse_iso_utc(rec.get("time_tag"))
        flux = _safe_float(rec.get("flux"))
        if parsed is None or not math.isfinite(flux):
            continue
        ref = rec
        obs_time = parsed
        p10_flux = flux
        sat = rec.get("satellite")
        break

    if ref is None or obs_time is None or not math.isfinite(p10_flux):
        return None, "No >=10 MeV proton channel record found (cannot classify SEP reliably)."
    
    cls, severity, bio_effect = _classify_sep_flux(p10_flux)
    
    # SEPs at GOES geostationary orbit are concurrent with Earth exposure.
    arrival_utc = obs_time
    arrival_bogota = utc_to_bogota(arrival_utc)
    
    recommendation = _get_polar_recommendation_sep(severity)
    
    event = ImpactEvent(
        category=EnergyCategory.PARTICLE_SEP,
        severity=severity,
        observation_time_utc=obs_time,
        arrival_time_utc=arrival_utc,
        arrival_time_bogota=arrival_bogota,
        travel_time_minutes=0.0,  # Measured at geostationary = at Earth
        source_description=(
            f"GOES integral protons (>10 MeV): {cls} | flux={p10_flux:.1f} pfu"
            + (f" | satellite={sat}" if sat is not None else "")
        ),
        biological_effect=bio_effect,
        polar_h10_recommendation=recommendation,
        raw_value=p10_flux,
        unit="pfu (>10 MeV)",
        confidence=1.0,
    )
    return event, None


def _get_polar_recommendation_sep(severity: ImpactSeverity) -> str:
    """Get Polar H10 recommendation for SEP events."""
    if severity in (ImpactSeverity.EXTREME, ImpactSeverity.SEVERE):
        return (
            "🔴 ACTIVE SEP EVENT: Polar H10 recording CRITICAL. "
            "Capture continuous data during event and 24h post-peak. "
            "This is a high-priority research opportunity."
        )
    if severity == ImpactSeverity.STRONG:
        return (
            "🟠 STRONG SEP: Begin Polar H10 monitoring. "
            "Record for at least 6 hours during elevated flux. "
            "Continue 24h after flux returns to background."
        )
    if severity == ImpactSeverity.MODERATE:
        return (
            "🟡 MODERATE SEP: Capture 2-hour Polar H10 session. "
            "Compare with baseline for subtle autonomic changes."
        )
    if severity == ImpactSeverity.MINOR:
        return (
            "🟢 MINOR SEP: Optional extended recording (30-60 min). "
            "Useful for detecting threshold effects."
        )
    return "⚪ NO SEP: Background radiation. Routine baseline recording."


# ---------------------------------------------------------------------------
# Solar Wind / Plasma from L1
# ---------------------------------------------------------------------------


def _classify_solar_wind(speed: float, density: float, bt: float, bz: float) -> Tuple[str, ImpactSeverity, str]:
    """Classify solar wind regime and geomagnetic impact potential."""
    if not math.isfinite(speed) or speed <= 0:
        return "Unknown", ImpactSeverity.QUIET, "Insufficient data for classification."
    
    # Check for CME shock signatures
    is_shock = (
        speed > 600 and 
        math.isfinite(density) and density > 15 and
        math.isfinite(bt) and bt > 15
    )
    
    # Southward Bz enhances geomagnetic coupling
    bz_southward = math.isfinite(bz) and bz < -5
    strong_southward = math.isfinite(bz) and bz < -15
    
    if speed >= 800 or (is_shock and strong_southward):
        severity = ImpactSeverity.EXTREME
        cls = "Extreme CME shock / major storm driver"
        bio_effect = (
            "Extreme geomagnetic storm conditions likely. "
            "Literature shows significant HRV reductions (SDNN, RMSSD) during severe storms. "
            "Cardiovascular stress response expected."
        )
    elif speed >= 650 or (speed > 500 and strong_southward):
        severity = ImpactSeverity.SEVERE
        cls = "Strong CME / severe storm potential"
        bio_effect = (
            "High storm potential (G3-G4). "
            "Studies associate with autonomic imbalance and HRV depression."
        )
    elif speed >= 500 or (speed > 400 and bz_southward):
        severity = ImpactSeverity.STRONG
        cls = "High-speed stream / moderate CME"
        bio_effect = (
            "Moderate storm potential (G1-G2). "
            "Small but consistent HRV changes documented in population studies."
        )
    elif speed >= 400:
        severity = ImpactSeverity.MODERATE
        cls = "Enhanced solar wind"
        bio_effect = (
            "Mildly disturbed geomagnetic conditions. "
            "Minor autonomic effects possible in sensitive individuals."
        )
    elif speed >= 350:
        severity = ImpactSeverity.MINOR
        cls = "Normal solar wind"
        bio_effect = "Background to mildly disturbed. Minimal biological impact expected."
    else:
        severity = ImpactSeverity.QUIET
        cls = "Slow solar wind"
        bio_effect = "Quiet geomagnetic conditions. Low autonomic impact."
    
    return cls, severity, bio_effect


def fetch_plasma_impact() -> Tuple[Optional[ImpactEvent], Optional[str]]:
    """Fetch solar wind plasma data and compute L1-to-Earth arrival."""
    try:
        resp_plasma = _get_http_session().get(
            ENDPOINTS["solar_wind_plasma"], timeout=REQUEST_TIMEOUT
        )
        resp_plasma.raise_for_status()
        plasma_data = resp_plasma.json()
    except requests.RequestException as exc:
        return None, f"Solar wind plasma fetch failed: {exc}"
    except ValueError as exc:
        return None, f"Solar wind plasma JSON parse failed: {exc}"
    
    # Fetch magnetic field data
    bt, bz = float("nan"), float("nan")
    try:
        resp_mag = _get_http_session().get(
            ENDPOINTS["solar_wind_mag"], timeout=REQUEST_TIMEOUT
        )
        resp_mag.raise_for_status()
        mag_data = resp_mag.json()
        if isinstance(mag_data, list) and len(mag_data) >= 2:
            header = mag_data[0]
            last_row = mag_data[-1]
            if isinstance(header, list) and isinstance(last_row, list):
                mag_dict = dict(zip(header, last_row))
                bt = _safe_float(mag_dict.get("bt"))
                bz = _safe_float(mag_dict.get("bz_gsm", mag_dict.get("bz_gse")))
    except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
        _LOGGER.debug("Magnetic field data unavailable (optional): %s", exc)
    
    if not isinstance(plasma_data, list) or len(plasma_data) < 2:
        return None, "No solar wind plasma data available"
    
    header = plasma_data[0]
    last_row = plasma_data[-1]
    
    if not isinstance(header, list) or not isinstance(last_row, list):
        return None, "Invalid solar wind plasma format"
    
    plasma_dict = dict(zip(header, last_row))
    obs_time = _parse_iso_utc(plasma_dict.get("time_tag"))
    if obs_time is None:
        return None, "Invalid solar wind timestamp"
    
    speed = _safe_float(plasma_dict.get("speed"))
    density = _safe_float(plasma_dict.get("density"))
    temperature = _safe_float(plasma_dict.get("temperature"))
    
    if not math.isfinite(speed) or speed <= 0:
        return None, "Invalid solar wind speed"
    
    # Calculate L1 to Earth travel time
    travel_seconds = L1_EARTH_DISTANCE_KM / speed
    travel_minutes = travel_seconds / 60.0
    
    arrival_utc = obs_time + datetime.timedelta(seconds=travel_seconds)
    arrival_bogota = utc_to_bogota(arrival_utc)
    
    cls, severity, bio_effect = _classify_solar_wind(speed, density, bt, bz)
    recommendation = _get_polar_recommendation_plasma(severity, travel_minutes)
    
    event = ImpactEvent(
        category=EnergyCategory.PLASMA_L1,
        severity=severity,
        observation_time_utc=obs_time,
        arrival_time_utc=arrival_utc,
        arrival_time_bogota=arrival_bogota,
        travel_time_minutes=travel_minutes,
        source_description=f"{cls} ({speed:.0f} km/s, ρ={density:.1f}/cm³)",
        biological_effect=bio_effect,
        polar_h10_recommendation=recommendation,
        raw_value=speed,
        unit="km/s",
        confidence=0.95,  # High confidence for L1 measurements
    )
    return event, None


def _get_polar_recommendation_plasma(severity: ImpactSeverity, minutes_to_arrival: float) -> str:
    """Get Polar H10 recommendation based on solar wind and arrival time."""
    if minutes_to_arrival < 0:
        time_note = "Plasma has already passed L1"
    elif minutes_to_arrival < 10:
        time_note = f"IMMINENT arrival in {minutes_to_arrival:.0f} min"
    elif minutes_to_arrival < 60:
        time_note = f"Arrival in {minutes_to_arrival:.0f} minutes"
    else:
        time_note = f"Arrival in {minutes_to_arrival/60:.1f} hours"
    
    if severity in (ImpactSeverity.EXTREME, ImpactSeverity.SEVERE):
        return (
            f"🔴 {time_note}. Start Polar H10 NOW. "
            "Record continuously from 30 min before through 4-6 hours after arrival. "
            "This captures both acute impact and recovery phases."
        )
    if severity == ImpactSeverity.STRONG:
        return (
            f"🟠 {time_note}. Prepare Polar H10. "
            "Begin recording 1 hour before expected arrival. "
            "Continue for 3 hours post-arrival for storm response capture."
        )
    if severity == ImpactSeverity.MODERATE:
        return (
            f"🟡 {time_note}. "
            "Optional: 30-min recording around arrival time for research data."
        )
    return f"⚪ {time_note}. Routine baseline recording recommended."


# ---------------------------------------------------------------------------
# CME / Shock Forecasts (NASA DONKI WSA+ENLIL)
# ---------------------------------------------------------------------------


def _get_nasa_api_key() -> str:
    """Return the NASA API key from environment (empty if missing)."""
    return str(os.getenv("NASA_API_KEY", "") or "").strip()


def _enlil_kp_values(sim: Mapping[str, Any]) -> List[float]:
    """Extract any available Kp scenario values from a DONKI ENLIL record."""
    values: List[float] = []
    for key in ("kp_18", "kp_90", "kp_135", "kp_180"):
        val = _safe_float(sim.get(key))
        if math.isfinite(val):
            # Kp is bounded to [0, 9]
            values.append(float(max(0.0, min(9.0, val))))
    return values


def _severity_from_kp(kp: float) -> ImpactSeverity:
    """Map a Kp value to the app's severity scale (aligned to NOAA G-scale semantics)."""
    if not math.isfinite(kp):
        return ImpactSeverity.QUIET
    if kp >= 9:
        return ImpactSeverity.EXTREME
    if kp >= 8:
        return ImpactSeverity.SEVERE
    if kp >= 7:
        return ImpactSeverity.STRONG
    if kp >= 6:
        return ImpactSeverity.MODERATE
    if kp >= 5:
        return ImpactSeverity.MINOR
    return ImpactSeverity.QUIET


def _select_most_accurate_cme_input(cme_inputs: Any) -> Optional[Mapping[str, Any]]:
    """Select the CME input flagged as 'isMostAccurate' if present, else the first."""
    if not isinstance(cme_inputs, list) or not cme_inputs:
        return None
    best: Optional[Mapping[str, Any]] = None
    for item in cme_inputs:
        if not isinstance(item, dict):
            continue
        if bool(item.get("isMostAccurate")):
            best = item
            break
        if best is None:
            best = item
    return best


def _select_best_enlil_record(
    records: Sequence[Any],
    *,
    now_utc: datetime.datetime,
) -> Optional[Mapping[str, Any]]:
    """Select the most relevant ENLIL record for Earth (next arrival if available)."""
    if now_utc.tzinfo is None:
        raise ValueError("now_utc must be timezone-aware (UTC).")

    candidates: List[Tuple[datetime.datetime, datetime.datetime, Mapping[str, Any]]] = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        arrival = _parse_iso_utc(rec.get("estimatedShockArrivalTime"))
        if arrival is None:
            continue
        completion = _parse_iso_utc(rec.get("modelCompletionTime"))
        if completion is None:
            completion = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        candidates.append((arrival, completion, rec))

    if not candidates:
        return None

    # Prefer the next upcoming arrival; if none, use the most recent arrival in the last 24h.
    future = [c for c in candidates if c[0] >= now_utc]
    if future:
        next_arrival = min(future, key=lambda x: x[0])[0]
        same = [c for c in future if c[0] == next_arrival]
        chosen = max(same, key=lambda x: x[1])
        return chosen[2]

    cutoff = now_utc - datetime.timedelta(hours=24)
    recent = [c for c in candidates if cutoff <= c[0] < now_utc]
    if not recent:
        return None
    last_arrival = max(recent, key=lambda x: x[0])[0]
    same = [c for c in recent if c[0] == last_arrival]
    chosen = max(same, key=lambda x: x[1])
    return chosen[2]


def _get_polar_recommendation_cme(severity: ImpactSeverity, minutes_to_arrival: float) -> str:
    """Get Polar H10 recommendation for a forecast CME/shock arrival."""
    if minutes_to_arrival < -60:
        time_note = "Shock likely already arrived (check Kp/Dst and solar wind)."
    elif minutes_to_arrival < 0:
        time_note = "Shock arrival window is now/just passed."
    elif minutes_to_arrival < 120:
        time_note = f"Arrival expected in ~{minutes_to_arrival:.0f} minutes"
    elif minutes_to_arrival < 24 * 60:
        time_note = f"Arrival expected in ~{minutes_to_arrival/60.0:.1f} hours"
    else:
        time_note = f"Arrival expected in ~{minutes_to_arrival/1440.0:.1f} days"

    if severity in (ImpactSeverity.EXTREME, ImpactSeverity.SEVERE, ImpactSeverity.STRONG):
        return (
            f"🟠 CME FORECAST: {time_note}. "
            "Plan a Polar H10 session spanning **3h before → 12h after** the predicted shock arrival. "
            "Add a quiet-day baseline recording for comparison."
        )
    if severity == ImpactSeverity.MODERATE:
        return (
            f"🟡 CME FORECAST: {time_note}. "
            "Record a 10-min baseline now, then a **2–4h** session around the predicted arrival."
        )
    return (
        f"🟢 CME FORECAST: {time_note}. "
        "Optional: brief baseline recording for context."
    )


def _build_cme_event_from_enlil_record(
    rec: Mapping[str, Any],
    *,
    now_utc: datetime.datetime,
) -> Optional[ImpactEvent]:
    """Build a CME/shock ImpactEvent from one DONKI WSA+ENLIL simulation record."""
    arrival = _parse_iso_utc(rec.get("estimatedShockArrivalTime"))
    if arrival is None:
        return None
    completion = _parse_iso_utc(rec.get("modelCompletionTime")) or now_utc

    cme_input = _select_most_accurate_cme_input(rec.get("cmeInputs"))
    speed = _safe_float(cme_input.get("speed") if isinstance(cme_input, dict) else None)
    time21_5 = _parse_iso_utc(cme_input.get("time21_5") if isinstance(cme_input, dict) else None)
    cme_start = _parse_iso_utc(cme_input.get("cmeStartTime") if isinstance(cme_input, dict) else None)

    # Transit time (best-effort): prefer time21_5 (start of IP propagation), else CME start time.
    transit_ref = time21_5 or cme_start
    travel_minutes = float("nan")
    if transit_ref is not None:
        travel_minutes = float((arrival - transit_ref).total_seconds() / 60.0)

    # DBM cross-check range (helps communicate uncertainty)
    dbm_range_text = ""
    try:
        if time21_5 is not None and math.isfinite(speed) and speed > 0:
            a_min, a_max = estimate_cme_arrival_range_utc(
                pd.Timestamp(time21_5),
                v0_km_s=float(speed),
                distance_km=float(AU_KM - (21.5 * SOLAR_RADIUS_KM)),
            )
            dbm_range_text = f" | DBM range: {a_min:%Y-%m-%d %H:%M}–{a_max:%Y-%m-%d %H:%M} UTC"
    except Exception:
        dbm_range_text = ""

    kp_values = _enlil_kp_values(rec)
    kp_min: Optional[float] = min(kp_values) if kp_values else None
    kp_max: Optional[float] = max(kp_values) if kp_values else None
    severity = _severity_from_kp(float(kp_max)) if kp_max is not None else ImpactSeverity.MODERATE

    impact_flag = "direct/nominal"
    if bool(rec.get("isEarthGB")):
        impact_flag = "glancing blow"
    if bool(rec.get("isEarthMinorImpact")):
        impact_flag = "minor impact"

    rmin_re = _safe_float(rec.get("rmin_re"))
    rmin_text = f"{rmin_re:.1f} Re" if math.isfinite(rmin_re) else "n/a"

    kp_text = (
        f"Kp scenarios: {kp_min:.0f}–{kp_max:.0f}"
        if (kp_min is not None and kp_max is not None)
        else "Kp scenarios: n/a"
    )

    minutes_to_arrival = float((arrival - now_utc).total_seconds() / 60.0)
    recommendation = _get_polar_recommendation_cme(severity, minutes_to_arrival)

    sim_id = str(rec.get("simulationID", "") or "").strip()
    link = str(rec.get("link", "") or "").strip()

    source_loc = ""
    if isinstance(cme_input, dict):
        lat = _safe_float(cme_input.get("latitude"))
        lon = _safe_float(cme_input.get("longitude"))
        if math.isfinite(lat) and math.isfinite(lon):
            source_loc = f" | source lat/lon={lat:.0f}/{lon:.0f}°"

    speed_text = f"{speed:.0f} km/s" if math.isfinite(speed) else "n/a"

    desc = (
        f"DONKI WSA+ENLIL ({sim_id}) | shock arrival forecast | {impact_flag}"
        f" | CME v={speed_text}{source_loc}"
        f" | rmin={rmin_text} | {kp_text}{dbm_range_text}"
        + (f" | {link}" if link else "")
    )

    bio_effect = (
        "Forecast CME/shock arrival at Earth. Geomagnetic storm intensity depends strongly on the "
        "interplanetary magnetic field orientation (Bz), which is not deterministically forecast from coronagraph data. "
        "Use the Kp scenario range as an uncertainty bracket; validate with real-time solar wind + Kp/Dst on arrival."
    )

    # Confidence is moderate for model-based forecasts; higher if Kp scenarios are provided.
    confidence = 0.60 + (0.10 if kp_values else 0.0)
    confidence = float(max(0.0, min(0.85, confidence)))

    event = ImpactEvent(
        category=EnergyCategory.CME_SHOCK,
        severity=severity,
        observation_time_utc=completion,
        arrival_time_utc=arrival,
        arrival_time_bogota=utc_to_bogota(arrival),
        travel_time_minutes=travel_minutes if math.isfinite(travel_minutes) else 0.0,
        source_description=desc,
        biological_effect=bio_effect,
        polar_h10_recommendation=recommendation,
        raw_value=float(kp_max) if kp_max is not None else speed,
        unit="Kp (scenario max)" if kp_max is not None else "km/s",
        confidence=confidence,
    )
    return event


def fetch_cme_enlil_impact(*, lookback_days: int = 45) -> Tuple[Optional[ImpactEvent], Optional[str]]:
    """Fetch WSA+ENLIL CME/shock forecasts (DONKI) and return the most relevant Earth arrival."""
    if int(lookback_days) <= 0 or int(lookback_days) > 365:
        raise ValueError("lookback_days must be in [1, 365].")

    api_key = _get_nasa_api_key()
    if not api_key:
        return None, "NASA_API_KEY not set (CME forecasts require NASA DONKI WSA+ENLIL)."

    end = datetime.date.today()
    start = end - datetime.timedelta(days=int(lookback_days))
    params = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "api_key": api_key,
    }

    try:
        resp = _get_http_session().get(DONKI_ENLIL_ENDPOINT, params=params, timeout=DONKI_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 503:
            return (
                None,
                "DONKI WSA+ENLIL temporarily unavailable (HTTP 503). "
                "NOAA/SWPC data remains available.",
            )
        if status_code == 429:
            return (
                None,
                "DONKI WSA+ENLIL rate limited (HTTP 429). "
                "Try refresh after a short cooldown.",
            )
        if status_code is not None:
            return None, f"DONKI WSA+ENLIL fetch failed (HTTP {status_code})."
        return None, f"DONKI WSA+ENLIL network error ({exc.__class__.__name__})."
    except ValueError as exc:
        return None, f"DONKI WSA+ENLIL JSON parse failed: {exc}"

    if not isinstance(payload, list) or not payload:
        return None, "No WSA+ENLIL simulations returned for the requested window."

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    best = _select_best_enlil_record(payload, now_utc=now_utc)
    if best is None:
        return None, "No ENLIL record with an estimated shock arrival time was found."

    event = _build_cme_event_from_enlil_record(best, now_utc=now_utc)
    if event is None:
        return None, "Failed to build CME forecast event from ENLIL record."
    return event, None


# ---------------------------------------------------------------------------
# Geomagnetic Activity (Kp, Dst)
# ---------------------------------------------------------------------------


def _classify_geomagnetic(kp: float, dst: float) -> Tuple[str, ImpactSeverity, str]:
    """Classify geomagnetic conditions from Kp and Dst indices."""
    # Use Kp if available (0-9 scale)
    if math.isfinite(kp):
        # NOAA G-scale mapping (Kp → G1..G5): 5,6,7,8,9
        # Source: NOAA SWPC Space Weather Scales.
        if kp >= 9:
            return "G5 Extreme storm (Kp ≥ 9)", ImpactSeverity.EXTREME, (
                "Extreme geomagnetic storm. Strong HRV reductions documented. "
                "Elevated cardiovascular risk in susceptible populations."
            )
        if kp >= 8:
            return "G4 Severe storm (Kp = 8)", ImpactSeverity.SEVERE, (
                "Severe storm. Consistent HRV depression (↓SDNN, ↓RMSSD) in studies."
            )
        if kp >= 7:
            return "G3 Strong storm (Kp = 7)", ImpactSeverity.STRONG, (
                "Strong storm. Moderate HRV changes and autonomic stress signatures."
            )
        if kp >= 6:
            return "G2 Moderate storm (Kp = 6)", ImpactSeverity.MODERATE, (
                "Moderate storm. Measurable autonomic effects possible in sensitive individuals."
            )
        if kp >= 5:
            return "G1 Minor storm (Kp = 5)", ImpactSeverity.MINOR, (
                "Minor to moderate storm. Small but detectable HRV effects possible."
            )
        if kp >= 4:
            return "Unsettled", ImpactSeverity.MINOR, (
                "Unsettled geomagnetic conditions. Subtle autonomic effects in sensitive individuals."
            )
        return "Quiet", ImpactSeverity.QUIET, (
            "Quiet geomagnetic field. Ideal for baseline recordings."
        )
    
    # Fallback to Dst if Kp not available
    if math.isfinite(dst):
        if dst <= -200:
            return "Extreme storm (Dst)", ImpactSeverity.EXTREME, (
                "Extreme ring current depression. Major storm in progress."
            )
        if dst <= -100:
            return "Severe storm (Dst)", ImpactSeverity.SEVERE, (
                "Severe magnetic storm indicated by Dst."
            )
        if dst <= -50:
            return "Moderate storm (Dst)", ImpactSeverity.MODERATE, (
                "Moderate storm activity per Dst index."
            )
    
    return "Unknown", ImpactSeverity.QUIET, "Insufficient geomagnetic data."


def fetch_geomagnetic_impact() -> Tuple[Optional[ImpactEvent], Optional[str]]:
    """Fetch current geomagnetic indices and assess impact."""
    kp = float("nan")
    dst = float("nan")
    obs_time: Optional[datetime.datetime] = None
    
    # Fetch Kp
    try:
        resp = _get_http_session().get(ENDPOINTS["kp_1min"], timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            for rec in reversed(data):
                if isinstance(rec, dict):
                    kp_val = _safe_float(rec.get("kp_index", rec.get("estimated_kp")))
                    if math.isfinite(kp_val):
                        kp = kp_val
                        obs_time = _parse_iso_utc(rec.get("time_tag"))
                        break
    except (requests.RequestException, ValueError, KeyError) as exc:
        _LOGGER.debug("Kp index fetch failed (will use default): %s", exc)
    
    # Fetch Dst
    try:
        resp = _get_http_session().get(ENDPOINTS["dst_1hour"], timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            for rec in reversed(data):
                if isinstance(rec, dict):
                    dst_val = _safe_float(rec.get("dst"))
                    if math.isfinite(dst_val):
                        dst = dst_val
                        if obs_time is None:
                            obs_time = _parse_iso_utc(rec.get("time_tag"))
                        break
    except (requests.RequestException, ValueError, KeyError) as exc:
        _LOGGER.debug("Dst index fetch failed (will use default): %s", exc)
    
    if obs_time is None:
        obs_time = datetime.datetime.now(datetime.timezone.utc)
    
    cls, severity, bio_effect = _classify_geomagnetic(kp, dst)
    
    # Geomagnetic effects are immediate/ongoing
    arrival_utc = obs_time
    arrival_bogota = utc_to_bogota(arrival_utc)
    
    recommendation = _get_polar_recommendation_geomag(severity, kp)
    
    event = ImpactEvent(
        category=EnergyCategory.GEOMAGNETIC,
        severity=severity,
        observation_time_utc=obs_time,
        arrival_time_utc=arrival_utc,
        arrival_time_bogota=arrival_bogota,
        travel_time_minutes=0.0,
        source_description=f"{cls} (Kp={kp:.1f}, Dst={dst:.0f} nT)",
        biological_effect=bio_effect,
        polar_h10_recommendation=recommendation,
        raw_value=kp if math.isfinite(kp) else dst,
        unit="Kp" if math.isfinite(kp) else "nT",
        confidence=1.0,
    )
    return event, None


def _get_polar_recommendation_geomag(severity: ImpactSeverity, kp: float) -> str:
    """Get Polar H10 recommendation for geomagnetic conditions."""
    if severity in (ImpactSeverity.EXTREME, ImpactSeverity.SEVERE):
        return (
            "🔴 STORM IN PROGRESS: Continuous Polar H10 recording recommended. "
            "Capture entire storm phase (typically 6-24 hours). "
            "Monitor for HRV depression and recovery patterns."
        )
    if severity == ImpactSeverity.STRONG:
        return (
            "🟠 ACTIVE STORM: Extended Polar H10 session (2-4 hours). "
            "Record morning wakeup HRV and evening comparison."
        )
    if severity == ImpactSeverity.MODERATE:
        return (
            "🟡 DISTURBED: 30-60 min Polar H10 recording. "
            "Compare with quiet-day baseline."
        )
    if severity == ImpactSeverity.MINOR:
        return (
            "🟢 UNSETTLED: Standard 5-10 min morning recording. "
            "Note geomagnetic context for later analysis."
        )
    return (
        "⚪ QUIET: Excellent time for baseline recordings. "
        "Use this quiet period to establish your personal HRV reference."
    )


# ---------------------------------------------------------------------------
# Main Snapshot Builder
# ---------------------------------------------------------------------------


def fetch_space_weather_snapshot(*, overall_timeout_s: float = 15.0) -> SpaceWeatherSnapshot:
    """
    Fetch all space weather data and build comprehensive impact snapshot.
    
    Returns a SpaceWeatherSnapshot with all categories populated.
    All times are exact and expressed in UTC and Bogotá timezone.
    
    Uses parallel fetching for faster data retrieval.

    Notes
    -----
    Even with `requests` timeouts, DNS resolution can occasionally stall inside a worker
    thread (especially on some Windows/OneDrive/network setups). To prevent the Streamlit
    UI from appearing to hang indefinitely, this function enforces an overall timeout and
    stops waiting when exceeded (best-effort cancellation; threads may still finish later).
    """
    import concurrent.futures
    
    if overall_timeout_s <= 0:
        raise ValueError("overall_timeout_s must be > 0")

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_bogota = utc_to_bogota(now_utc)
    
    snapshot = SpaceWeatherSnapshot(
        timestamp_utc=now_utc,
        timestamp_bogota=now_bogota,
    )
    
    # Fetch all event types in parallel for faster loading
    fetch_functions = {
        "photon": fetch_xray_impact,
        "sep": fetch_sep_impact,
        "plasma": fetch_plasma_impact,
        "cme": fetch_cme_enlil_impact,
        "geomagnetic": fetch_geomagnetic_impact,
    }
    
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(fetch_functions))
    futures: Dict[concurrent.futures.Future[Tuple[Optional[ImpactEvent], Optional[str]]], str] = {
        executor.submit(func): name for name, func in fetch_functions.items()
    }
    try:
        done, not_done = concurrent.futures.wait(
            set(futures.keys()),
            timeout=float(overall_timeout_s),
            return_when=concurrent.futures.ALL_COMPLETED,
        )

        for future in done:
            name = futures.get(future, "__unknown__")
            try:
                event, error = future.result()
            except Exception as exc:
                snapshot.errors[name] = str(exc)
                log_exception(_LOGGER, f"Impact snapshot fetch failed ({name})", exc)
                continue
            if event:
                if name == "photon":
                    snapshot.photon_event = event
                elif name == "sep":
                    snapshot.sep_event = event
                elif name == "plasma":
                    snapshot.plasma_event = event
                elif name == "cme":
                    snapshot.cme_event = event
                elif name == "geomagnetic":
                    snapshot.geomagnetic_event = event
            if error:
                snapshot.errors[name] = error

        if not_done:
            for pending in not_done:
                name = futures.get(pending, "__unknown__")
                snapshot.errors[name] = f"Timed out fetching {name} (>{overall_timeout_s:.0f}s)."
                _ = pending.cancel()  # best-effort; threads may still be running
    finally:
        # Do not wait for potentially-stuck worker threads; return control to the UI.
        executor.shutdown(wait=False, cancel_futures=True)
    
    return snapshot


def fetch_space_weather_snapshot_with_progress(
    *,
    overall_timeout_s: float = 30.0,
    on_step_start: Optional[Callable[[str], None]] = None,
    on_step_complete: Optional[Callable[[str, Optional[ImpactEvent], Optional[str]], None]] = None,
    on_step_error: Optional[Callable[[str, str], None]] = None,
) -> SpaceWeatherSnapshot:
    """
    Fetch all space weather data with progress callbacks for UI updates.
    
    This version provides real-time feedback on each step of the fetch process,
    making it ideal for detailed progress indicators.
    
    Args:
        overall_timeout_s: Maximum total time to wait for all fetches.
        on_step_start: Callback when a step starts. Called with step name.
        on_step_complete: Callback when a step completes. Called with (name, event, error).
        on_step_error: Callback when a step fails. Called with (name, error_message).
    
    Returns:
        SpaceWeatherSnapshot with all available events.
    """
    import concurrent.futures
    import time
    
    if overall_timeout_s <= 0:
        raise ValueError("overall_timeout_s must be > 0")

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_bogota = utc_to_bogota(now_utc)
    
    snapshot = SpaceWeatherSnapshot(
        timestamp_utc=now_utc,
        timestamp_bogota=now_bogota,
    )
    
    # Fetch functions with descriptive metadata
    fetch_functions: Dict[str, Callable[[], Tuple[Optional[ImpactEvent], Optional[str]]]] = {
        "photon": fetch_xray_impact,
        "sep": fetch_sep_impact,
        "plasma": fetch_plasma_impact,
        "cme": fetch_cme_enlil_impact,
        "geomagnetic": fetch_geomagnetic_impact,
    }
    
    # Track step results with timing
    step_results: Dict[str, Dict[str, Any]] = {}
    
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(fetch_functions))
    futures: Dict[concurrent.futures.Future[Tuple[Optional[ImpactEvent], Optional[str]]], str] = {}
    
    # Submit all tasks and notify step start
    for name, func in fetch_functions.items():
        if on_step_start:
            try:
                on_step_start(name)
            except Exception:
                pass  # Never let callback errors break the fetch
        future = executor.submit(func)
        futures[future] = name
        step_results[name] = {"start_time": time.perf_counter(), "completed": False}
    
    try:
        start_time = time.perf_counter()
        
        # Process results as they complete (better UX than waiting for all)
        while futures:
            elapsed = time.perf_counter() - start_time
            remaining = max(0.1, overall_timeout_s - elapsed)
            
            if elapsed >= overall_timeout_s:
                # Timeout remaining tasks
                for future, name in list(futures.items()):
                    if not future.done():
                        error_msg = f"Timed out after {overall_timeout_s:.0f}s"
                        snapshot.errors[name] = error_msg
                        step_results[name]["completed"] = True
                        step_results[name]["error"] = error_msg
                        if on_step_error:
                            try:
                                on_step_error(name, error_msg)
                            except Exception:
                                pass
                        future.cancel()
                break
            
            # Wait for any future to complete
            done, _ = concurrent.futures.wait(
                set(futures.keys()),
                timeout=min(0.5, remaining),
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            
            for future in done:
                name = futures.pop(future)
                step_results[name]["end_time"] = time.perf_counter()
                step_results[name]["completed"] = True
                
                try:
                    event, error = future.result(timeout=0.1)
                    
                    if event:
                        if name == "photon":
                            snapshot.photon_event = event
                        elif name == "sep":
                            snapshot.sep_event = event
                        elif name == "plasma":
                            snapshot.plasma_event = event
                        elif name == "cme":
                            snapshot.cme_event = event
                        elif name == "geomagnetic":
                            snapshot.geomagnetic_event = event
                    
                    if error:
                        snapshot.errors[name] = error
                    
                    # Notify completion
                    if on_step_complete:
                        try:
                            on_step_complete(name, event, error)
                        except Exception:
                            pass
                            
                except concurrent.futures.TimeoutError:
                    error_msg = f"Timed out fetching {name}"
                    snapshot.errors[name] = error_msg
                    step_results[name]["error"] = error_msg
                    if on_step_error:
                        try:
                            on_step_error(name, error_msg)
                        except Exception:
                            pass
                            
                except Exception as exc:
                    error_msg = str(exc)
                    snapshot.errors[name] = error_msg
                    step_results[name]["error"] = error_msg
                    log_exception(_LOGGER, f"Impact snapshot fetch failed ({name})", exc)
                    if on_step_error:
                        try:
                            on_step_error(name, error_msg)
                        except Exception:
                            pass
    
    finally:
        for future in futures:
            future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
    
    return snapshot


# ---------------------------------------------------------------------------
# Summary Generation for UI
# ---------------------------------------------------------------------------


def build_impact_summary_df(snapshot: SpaceWeatherSnapshot) -> pd.DataFrame:
    """Build a summary DataFrame of all impact events for display."""
    rows: List[Dict[str, Any]] = []
    
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    
    for event in snapshot.all_events():
        time_to_arrival = event.arrival_time_utc - now_utc
        countdown = format_countdown(time_to_arrival)
        
        rows.append({
            "Category": event.category.value.upper(),
            "Severity": event.severity.value.upper(),
            "Confidence": f"{float(max(0.0, min(1.0, event.confidence))) * 100.0:.0f}%",
            "Arrival (Bogotá)": format_datetime_bogota(event.arrival_time_utc),
            "Countdown": countdown,
            "Description": event.source_description,
            "Biological Effect": event.biological_effect,
            "Polar H10 Action": event.polar_h10_recommendation[:100] + "..." 
                if len(event.polar_h10_recommendation) > 100 
                else event.polar_h10_recommendation,
        })
    
    if not rows:
        return pd.DataFrame()
    
    return pd.DataFrame(rows)


def get_priority_recommendation(snapshot: SpaceWeatherSnapshot) -> str:
    """Generate a single priority recommendation based on all events."""
    most_severe = snapshot.most_severe()
    next_impact = snapshot.next_impact()
    
    if most_severe is None:
        return (
            "⚪ **QUIET CONDITIONS**: No significant space weather activity. "
            "This is an ideal time for baseline Polar H10 recordings."
        )
    
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    
    # Build priority message
    parts: List[str] = []
    
    if most_severe.severity in (ImpactSeverity.EXTREME, ImpactSeverity.SEVERE):
        parts.append(
            f"🔴 **ALERT**: {most_severe.severity.value.upper()} "
            f"{most_severe.category.value.upper()} event detected!"
        )
    elif most_severe.severity == ImpactSeverity.STRONG:
        parts.append(
            f"🟠 **ELEVATED**: {most_severe.severity.value.upper()} "
            f"{most_severe.category.value.upper()} activity."
        )
    elif most_severe.severity == ImpactSeverity.MODERATE:
        parts.append(
            f"🟡 **MODERATE**: Enhanced {most_severe.category.value} activity."
        )
    else:
        parts.append(
            f"🟢 **MINOR/QUIET**: Low space weather activity."
        )
    
    if next_impact:
        delta = next_impact.arrival_time_utc - now_utc
        countdown = format_countdown(delta)
        parts.append(
            f"\n\n**Next Impact**: {next_impact.category.value.upper()} "
            f"arriving in **{countdown}** at "
            f"**{format_datetime_bogota(next_impact.arrival_time_utc)}**"
        )
    
    parts.append(f"\n\n**Recommended Action**: {most_severe.polar_h10_recommendation}")
    
    return "\n".join(parts)


def get_severity_color(severity: ImpactSeverity) -> str:
    """Get color code for severity level."""
    colors = {
        ImpactSeverity.EXTREME: "#dc2626",   # Red
        ImpactSeverity.SEVERE: "#ea580c",    # Orange-red
        ImpactSeverity.STRONG: "#f97316",    # Orange
        ImpactSeverity.MODERATE: "#facc15",  # Yellow
        ImpactSeverity.MINOR: "#22c55e",     # Green
        ImpactSeverity.QUIET: "#64748b",     # Gray
    }
    return colors.get(severity, "#64748b")


def get_category_icon(category: EnergyCategory) -> str:
    """Get icon for energy category."""
    icons = {
        EnergyCategory.PHOTON: "☀️",
        EnergyCategory.PARTICLE_SEP: "⚡",
        EnergyCategory.PLASMA_L1: "🌊",
        EnergyCategory.CME_SHOCK: "💥",
        EnergyCategory.HSS: "💨",
        EnergyCategory.GEOMAGNETIC: "🧲",
    }
    return icons.get(category, "🌐")

