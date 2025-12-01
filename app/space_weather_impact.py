"""
Space Weather Impact Prediction Module

Calculates exact arrival times for different space weather events at Earth
and provides Polar H10 EKG monitoring recommendations.

Energy categories tracked:
1. Photons/X-rays (instantaneous ~8.3 min from Sun)
2. Solar Energetic Particles (SEPs) - minutes to hours
3. Solar Wind plasma from L1 - ~30-60 min
4. CME/Shock arrivals - hours to days (via models)

All times computed for Bogotá, Colombia (UTC-5).
"""

from __future__ import annotations

import datetime
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Final, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import requests

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

# NOAA SWPC endpoints
SWPC_BASE_URL: Final[str] = "https://services.swpc.noaa.gov"
REQUEST_TIMEOUT: Final[float] = 15.0

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
        response = requests.get(ENDPOINTS["xray_1day"], timeout=REQUEST_TIMEOUT)
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
        response = requests.get(ENDPOINTS["proton_1day"], timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        return None, f"Proton fetch failed: {exc}"
    except ValueError as exc:
        return None, f"Proton JSON parse failed: {exc}"
    
    if not isinstance(data, list) or len(data) == 0:
        return None, "No proton data available"
    
    # Find most recent valid record
    ref: Optional[Dict[str, Any]] = None
    for rec in reversed(data):
        if isinstance(rec, dict) and "time_tag" in rec:
            ref = rec
            break
    
    if ref is None:
        return None, "No valid proton record found"
    
    obs_time = _parse_iso_utc(ref.get("time_tag"))
    if obs_time is None:
        return None, "Invalid proton timestamp"
    
    # Extract >10 MeV flux (various possible key names)
    p10_flux = float("nan")
    for key, value in ref.items():
        key_lower = key.lower()
        if ">=10" in key_lower or "10 mev" in key_lower or "p10" in key_lower:
            p10_flux = _safe_float(value)
            if math.isfinite(p10_flux):
                break
    
    # Fallback: use largest numeric value
    if not math.isfinite(p10_flux):
        candidates = []
        for key, value in ref.items():
            if key in ("time_tag", "satellite", "energy", "id"):
                continue
            val = _safe_float(value)
            if math.isfinite(val) and val > 0:
                candidates.append(val)
        if candidates:
            p10_flux = max(candidates)
    
    cls, severity, bio_effect = _classify_sep_flux(p10_flux)
    
    # SEPs at GOES (geostationary) are concurrent with Earth magnetosphere exposure
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
        source_description=f"SEP Event: {cls}",
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
        resp_plasma = requests.get(ENDPOINTS["solar_wind_plasma"], timeout=REQUEST_TIMEOUT)
        resp_plasma.raise_for_status()
        plasma_data = resp_plasma.json()
    except requests.RequestException as exc:
        return None, f"Solar wind plasma fetch failed: {exc}"
    except ValueError as exc:
        return None, f"Solar wind plasma JSON parse failed: {exc}"
    
    # Fetch magnetic field data
    bt, bz = float("nan"), float("nan")
    try:
        resp_mag = requests.get(ENDPOINTS["solar_wind_mag"], timeout=REQUEST_TIMEOUT)
        resp_mag.raise_for_status()
        mag_data = resp_mag.json()
        if isinstance(mag_data, list) and len(mag_data) >= 2:
            header = mag_data[0]
            last_row = mag_data[-1]
            if isinstance(header, list) and isinstance(last_row, list):
                mag_dict = dict(zip(header, last_row))
                bt = _safe_float(mag_dict.get("bt"))
                bz = _safe_float(mag_dict.get("bz_gsm", mag_dict.get("bz_gse")))
    except Exception:
        pass  # Magnetic data is optional
    
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
# Geomagnetic Activity (Kp, Dst)
# ---------------------------------------------------------------------------


def _classify_geomagnetic(kp: float, dst: float) -> Tuple[str, ImpactSeverity, str]:
    """Classify geomagnetic conditions from Kp and Dst indices."""
    # Use Kp if available (0-9 scale)
    if math.isfinite(kp):
        if kp >= 8:
            return "G5 Extreme storm", ImpactSeverity.EXTREME, (
                "Extreme geomagnetic storm. Strong HRV reductions documented. "
                "Elevated cardiovascular risk in susceptible populations."
            )
        if kp >= 7:
            return "G4 Severe storm", ImpactSeverity.SEVERE, (
                "Severe storm. Consistent HRV depression (↓SDNN, ↓RMSSD) in studies."
            )
        if kp >= 6:
            return "G3 Strong storm", ImpactSeverity.STRONG, (
                "Strong storm. Moderate HRV changes and autonomic stress signatures."
            )
        if kp >= 5:
            return "G1-G2 Minor/Moderate storm", ImpactSeverity.MODERATE, (
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
        resp = requests.get(ENDPOINTS["kp_1min"], timeout=REQUEST_TIMEOUT)
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
    except Exception:
        pass
    
    # Fetch Dst
    try:
        resp = requests.get(ENDPOINTS["dst_1hour"], timeout=REQUEST_TIMEOUT)
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
    except Exception:
        pass
    
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


def fetch_space_weather_snapshot() -> SpaceWeatherSnapshot:
    """
    Fetch all space weather data and build comprehensive impact snapshot.
    
    Returns a SpaceWeatherSnapshot with all categories populated.
    All times are exact and expressed in UTC and Bogotá timezone.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_bogota = utc_to_bogota(now_utc)
    
    snapshot = SpaceWeatherSnapshot(
        timestamp_utc=now_utc,
        timestamp_bogota=now_bogota,
    )
    
    # Fetch all event types
    photon_event, photon_error = fetch_xray_impact()
    if photon_event:
        snapshot.photon_event = photon_event
    if photon_error:
        snapshot.errors["photon"] = photon_error
    
    sep_event, sep_error = fetch_sep_impact()
    if sep_event:
        snapshot.sep_event = sep_event
    if sep_error:
        snapshot.errors["sep"] = sep_error
    
    plasma_event, plasma_error = fetch_plasma_impact()
    if plasma_event:
        snapshot.plasma_event = plasma_event
    if plasma_error:
        snapshot.errors["plasma"] = plasma_error
    
    geomag_event, geomag_error = fetch_geomagnetic_impact()
    if geomag_event:
        snapshot.geomagnetic_event = geomag_event
    if geomag_error:
        snapshot.errors["geomagnetic"] = geomag_error
    
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

