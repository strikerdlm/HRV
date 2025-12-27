"""
Space-weather influence window utilities (Streamlit-free).

This module provides deterministic helpers to:
- Estimate CME Sun→Earth transit time (drag-based model, DBM)
- Recommend fetch/slicing horizons for Space Data based on HRV recording bounds
- Build DONKI-derived "influence windows" suitable for event-aligned HRV analysis

All functions are bounded and fully typed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final, Optional

import pandas as pd

from app.logging_config import get_logger

_LOGGER: Final = get_logger(__name__)

# Sun → Earth distance (1 AU)
AU_KM: Final[float] = 149_597_870.7

# IAU 2015 nominal solar radius (km) (approx; sufficient for travel-time horizons)
SOLAR_RADIUS_KM: Final[float] = 695_700.0

# Distance from solar surface (1 R☉) to Earth's orbit (≈1 AU).
SUN_SURFACE_TO_EARTH_KM: Final[float] = AU_KM - SOLAR_RADIUS_KM


@dataclass(frozen=True, slots=True)
class InfluenceHorizonRecommendation:
    """Recommended horizons for space-weather fetching/slicing around an HRV recording.

    Attributes:
        solar_to_earth_max_hours: Conservative (upper-bound) Sun→Earth transit time
            used to decide how far back to query solar-event catalogs like DONKI.
        assumed_earth_influence_hours: Assumed post-arrival influence horizon on Earth
            (used for RR-aligned padding in Space Data).
        recommended_donki_pad_days: Recommended symmetric padding (days) for DONKI queries
            when syncing to the RR timeline.
        recommended_rr_pad_hours: Recommended RR-window padding (hours) for slicing
            Earth-side indices (Kp/Dst/solar wind) around the HRV interval.
    """

    solar_to_earth_max_hours: float
    assumed_earth_influence_hours: int
    recommended_donki_pad_days: int
    recommended_rr_pad_hours: int


def _dbm_distance_km(
    t_seconds: float,
    *,
    v0_km_s: float,
    w_km_s: float,
    gamma_km_inv: float,
) -> float:
    """Distance traveled in DBM after `t_seconds`.

    Drag-Based Model (DBM) assumes:
        dv/dt = -γ (v - w) |v - w|

    For v0 == w, motion is ballistic at constant speed w.
    For v0 != w, the analytical distance solution is:
        r(t) = w t + s/γ * ln(1 + γ |v0-w| t)
    where s = sign(v0-w).
    """
    if not math.isfinite(t_seconds) or t_seconds < 0:
        raise ValueError("t_seconds must be finite and >= 0.")
    if not math.isfinite(v0_km_s) or v0_km_s <= 0:
        raise ValueError("v0_km_s must be finite and > 0.")
    if not math.isfinite(w_km_s) or w_km_s < 0:
        raise ValueError("w_km_s must be finite and >= 0.")
    if not math.isfinite(gamma_km_inv) or gamma_km_inv < 0:
        raise ValueError("gamma_km_inv must be finite and >= 0.")

    if gamma_km_inv == 0.0:
        return float(v0_km_s * t_seconds)
    if v0_km_s == w_km_s:
        return float(w_km_s * t_seconds)

    delta = float(v0_km_s - w_km_s)
    a = abs(delta)
    s = 1.0 if delta > 0 else -1.0
    term = 1.0 + float(gamma_km_inv) * a * float(t_seconds)
    # With gamma>=0 and t>=0, term must be >=1, but keep a guard.
    if term <= 0:
        raise ValueError("DBM distance term became non-positive (check inputs).")
    return float(w_km_s * t_seconds + s * (1.0 / float(gamma_km_inv)) * math.log(term))


def dbm_transit_time_seconds(
    distance_km: float,
    *,
    v0_km_s: float,
    w_km_s: float,
    gamma_km_inv: float,
    t_max_days: float = 10.0,
    iterations: int = 60,
) -> float:
    """Return DBM transit time (seconds) to reach `distance_km` from 0.

    Uses a bounded binary search (monotonic distance) and is deterministic.
    """
    if not math.isfinite(distance_km) or distance_km <= 0:
        raise ValueError("distance_km must be finite and > 0.")
    if not math.isfinite(t_max_days) or t_max_days <= 0:
        raise ValueError("t_max_days must be finite and > 0.")
    if int(iterations) <= 0 or int(iterations) > 200:
        raise ValueError("iterations must be in [1, 200].")

    t_lo = 0.0
    t_hi = float(t_max_days) * 86400.0

    d_hi = _dbm_distance_km(t_hi, v0_km_s=v0_km_s, w_km_s=w_km_s, gamma_km_inv=gamma_km_inv)
    if d_hi < float(distance_km):
        raise ValueError(
            f"Failed to bracket transit time within {t_max_days} days "
            f"(distance reached={d_hi:.1f} km < target={distance_km:.1f} km)."
        )

    # Binary search for smallest t such that distance(t) >= target.
    for _ in range(int(iterations)):
        t_mid = 0.5 * (t_lo + t_hi)
        d_mid = _dbm_distance_km(t_mid, v0_km_s=v0_km_s, w_km_s=w_km_s, gamma_km_inv=gamma_km_inv)
        if d_mid >= float(distance_km):
            t_hi = t_mid
        else:
            t_lo = t_mid
    return float(t_hi)


def estimate_cme_arrival_range_utc(
    eruption_time_utc: pd.Timestamp,
    *,
    v0_km_s: float,
    w_km_s: float = 400.0,
    gamma_min_km_inv: float = 0.5e-8,
    gamma_max_km_inv: float = 2.0e-8,
    distance_km: float = SUN_SURFACE_TO_EARTH_KM,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Estimate CME arrival time range at Earth (UTC) using DBM.

    Returns a conservative (min_arrival_utc, max_arrival_utc) range obtained by
    evaluating the DBM at two plausible drag parameters.

    Args:
        eruption_time_utc: Start time at the chosen start radius (UTC).
        v0_km_s: Initial CME/shock speed (km/s) at the chosen start radius.
        w_km_s: Background solar wind speed (km/s).
        gamma_min_km_inv: Lower-bound drag parameter (km⁻¹).
        gamma_max_km_inv: Upper-bound drag parameter (km⁻¹).
        distance_km: Propagation distance from the chosen start radius to Earth (km).
            Default uses solar-surface → 1 AU (≈ AU − 1 R☉). If using DONKI `time21_5`,
            pass `AU_KM - 21.5 * SOLAR_RADIUS_KM` for better accuracy.
    """
    if not isinstance(eruption_time_utc, pd.Timestamp):
        raise TypeError("eruption_time_utc must be a pandas.Timestamp.")
    if eruption_time_utc.tzinfo is None or eruption_time_utc.tzinfo.utcoffset(eruption_time_utc) is None:
        eruption_time_utc = eruption_time_utc.tz_localize("UTC")
    else:
        eruption_time_utc = eruption_time_utc.tz_convert("UTC")

    if not math.isfinite(v0_km_s) or float(v0_km_s) <= 0:
        raise ValueError("v0_km_s must be finite and > 0.")
    if not math.isfinite(w_km_s) or float(w_km_s) < 0:
        raise ValueError("w_km_s must be finite and >= 0.")
    if not math.isfinite(gamma_min_km_inv) or float(gamma_min_km_inv) <= 0:
        raise ValueError("gamma_min_km_inv must be finite and > 0.")
    if not math.isfinite(gamma_max_km_inv) or float(gamma_max_km_inv) <= 0:
        raise ValueError("gamma_max_km_inv must be finite and > 0.")
    if not math.isfinite(distance_km) or float(distance_km) <= 0:
        raise ValueError("distance_km must be finite and > 0.")

    gamma_lo = float(min(gamma_min_km_inv, gamma_max_km_inv))
    gamma_hi = float(max(gamma_min_km_inv, gamma_max_km_inv))

    t1 = dbm_transit_time_seconds(float(distance_km), v0_km_s=float(v0_km_s), w_km_s=float(w_km_s), gamma_km_inv=gamma_lo)
    t2 = dbm_transit_time_seconds(float(distance_km), v0_km_s=float(v0_km_s), w_km_s=float(w_km_s), gamma_km_inv=gamma_hi)
    min_s = float(min(t1, t2))
    max_s = float(max(t1, t2))

    return (
        (eruption_time_utc + pd.Timedelta(seconds=min_s)).tz_convert("UTC"),
        (eruption_time_utc + pd.Timedelta(seconds=max_s)).tz_convert("UTC"),
    )


def recommend_influence_horizons_from_hrv(
    hrv_start_utc: pd.Timestamp,
    hrv_end_utc: pd.Timestamp,
    *,
    assumed_earth_influence_hours: int = 72,
    v_min_km_s: float = 300.0,
    w_km_s: float = 400.0,
    gamma_min_km_inv: float = 0.5e-8,
    gamma_max_km_inv: float = 2.0e-8,
    safety_margin_hours: int = 24,
    max_donki_pad_days: int = 30,
) -> InfluenceHorizonRecommendation:
    """Recommend DONKI + Earth-index horizons using HRV recording bounds.

    Notes:
    - This is a *conservative* recommendation intended for data fetching/slicing.
    - It uses a slow-CME transit upper bound (DBM) plus a safety margin to
      ensure relevant solar eruptions are included in the DONKI query window.
    """
    if not isinstance(hrv_start_utc, pd.Timestamp) or not isinstance(hrv_end_utc, pd.Timestamp):
        raise TypeError("hrv_start_utc/hrv_end_utc must be pandas.Timestamp.")
    if hrv_start_utc.tzinfo is None or hrv_start_utc.tzinfo.utcoffset(hrv_start_utc) is None:
        hrv_start_utc = hrv_start_utc.tz_localize("UTC")
    else:
        hrv_start_utc = hrv_start_utc.tz_convert("UTC")
    if hrv_end_utc.tzinfo is None or hrv_end_utc.tzinfo.utcoffset(hrv_end_utc) is None:
        hrv_end_utc = hrv_end_utc.tz_localize("UTC")
    else:
        hrv_end_utc = hrv_end_utc.tz_convert("UTC")
    if hrv_end_utc < hrv_start_utc:
        raise ValueError("hrv_end_utc must be >= hrv_start_utc.")

    if int(assumed_earth_influence_hours) <= 0 or int(assumed_earth_influence_hours) > 24 * 14:
        raise ValueError("assumed_earth_influence_hours must be in (0, 336].")
    if not math.isfinite(v_min_km_s) or float(v_min_km_s) <= 0:
        raise ValueError("v_min_km_s must be finite and > 0.")
    if int(safety_margin_hours) < 0 or int(safety_margin_hours) > 24 * 14:
        raise ValueError("safety_margin_hours must be in [0, 336].")
    if int(max_donki_pad_days) <= 0 or int(max_donki_pad_days) > 90:
        raise ValueError("max_donki_pad_days must be in [1, 90].")

    # Conservative max transit time from Sun to Earth (slow CME + weak drag)
    # Evaluate both gamma endpoints and take the maximum.
    t_lo = dbm_transit_time_seconds(
        SUN_SURFACE_TO_EARTH_KM,
        v0_km_s=float(v_min_km_s),
        w_km_s=float(w_km_s),
        gamma_km_inv=float(min(gamma_min_km_inv, gamma_max_km_inv)),
    )
    t_hi = dbm_transit_time_seconds(
        SUN_SURFACE_TO_EARTH_KM,
        v0_km_s=float(v_min_km_s),
        w_km_s=float(w_km_s),
        gamma_km_inv=float(max(gamma_min_km_inv, gamma_max_km_inv)),
    )
    solar_to_earth_max_hours = (max(t_lo, t_hi) / 3600.0) + float(int(safety_margin_hours))
    pad_days = int(math.ceil(solar_to_earth_max_hours / 24.0))
    pad_days = max(1, min(int(max_donki_pad_days), pad_days))

    rec = InfluenceHorizonRecommendation(
        solar_to_earth_max_hours=float(solar_to_earth_max_hours),
        assumed_earth_influence_hours=int(assumed_earth_influence_hours),
        recommended_donki_pad_days=int(pad_days),
        recommended_rr_pad_hours=int(assumed_earth_influence_hours),
    )
    return rec


def build_donki_cme_influence_windows(
    cme_analysis_df: pd.DataFrame,
    *,
    influence_hours: int = 72,
    max_events: int = 200,
) -> pd.DataFrame:
    """Build a CME influence-window catalog from DONKI CMEAnalysis.

    The output is designed to be consumed by the Space Analytics event-aligned UI:
    it includes `event_id`, `start_utc`, and `end_utc` at minimum.
    """
    if not isinstance(cme_analysis_df, pd.DataFrame):
        raise TypeError("cme_analysis_df must be a pandas DataFrame.")
    if int(influence_hours) <= 0 or int(influence_hours) > 24 * 14:
        raise ValueError("influence_hours must be in (0, 336].")
    if int(max_events) <= 0 or int(max_events) > 5000:
        raise ValueError("max_events must be in [1, 5000].")

    cols = [
        "event_id",
        "source_time_utc",
        "speed_km_s",
        "arrival_min_utc",
        "arrival_max_utc",
        "arrival_mid_utc",
        "start_utc",
        "end_utc",
        "duration_hours",
        "notes",
    ]
    if cme_analysis_df.empty:
        return pd.DataFrame(columns=cols)

    df = cme_analysis_df.copy()
    # Prefer an explicit associated CME start time; fall back to time21_5.
    time_series: Optional[pd.Series] = None
    source_time_column: Optional[str] = None
    if "associatedCMEstartTime" in df.columns:
        time_series = pd.to_datetime(df["associatedCMEstartTime"], errors="coerce", utc=True)
        source_time_column = "associatedCMEstartTime"
    elif "time21_5" in df.columns:
        time_series = pd.to_datetime(df["time21_5"], errors="coerce", utc=True)
        source_time_column = "time21_5"
    elif "startTime" in df.columns:
        time_series = pd.to_datetime(df["startTime"], errors="coerce", utc=True)
        source_time_column = "startTime"
    if time_series is None:
        _LOGGER.warning("DONKI CMEAnalysis frame missing start-time columns.")
        return pd.DataFrame(columns=cols)
    df["_source_time_utc"] = time_series

    if "speed" not in df.columns:
        _LOGGER.warning("DONKI CMEAnalysis frame missing speed column.")
        return pd.DataFrame(columns=cols)
    df["_speed_km_s"] = pd.to_numeric(df["speed"], errors="coerce")

    df = df.dropna(subset=["_source_time_utc", "_speed_km_s"]).copy()
    if df.empty:
        return pd.DataFrame(columns=cols)
    df = df.sort_values("_source_time_utc").head(int(max_events))

    rows: list[dict[str, object]] = []
    event_id = 0
    source_times = df["_source_time_utc"].tolist()
    speeds = df["_speed_km_s"].tolist()
    for source_time, speed in zip(source_times, speeds):
        if not isinstance(source_time, pd.Timestamp) or pd.isna(source_time):
            continue
        try:
            speed_f = float(speed)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(speed_f) or speed_f <= 0:
            continue

        try:
            # If the DONKI time is `time21_5`, it represents the CME front at ~21.5 R☉.
            # Use the remaining distance to 1 AU for more accurate DBM propagation.
            distance_km = SUN_SURFACE_TO_EARTH_KM
            if source_time_column == "time21_5":
                distance_km = AU_KM - (21.5 * SOLAR_RADIUS_KM)
            a_min, a_max = estimate_cme_arrival_range_utc(
                pd.to_datetime(source_time, utc=True),
                v0_km_s=speed_f,
                distance_km=float(distance_km),
            )
        except Exception as exc:
            _LOGGER.debug("Skipping CMEAnalysis row due to arrival estimate error: %s", exc)
            continue
        a_mid = a_min + (a_max - a_min) / 2.0

        # Influence window: include arrival uncertainty, then extend by influence_hours.
        start_utc = a_min
        end_utc = a_max + pd.Timedelta(hours=int(influence_hours))
        duration_h = float((end_utc - start_utc).total_seconds() / 3600.0)

        event_id += 1
        rows.append(
            {
                "event_id": int(event_id),
                "source_time_utc": pd.to_datetime(source_time, utc=True),
                "speed_km_s": float(speed_f),
                "arrival_min_utc": a_min,
                "arrival_max_utc": a_max,
                "arrival_mid_utc": a_mid,
                "start_utc": start_utc,
                "end_utc": end_utc,
                "duration_hours": float(duration_h),
                "notes": f"CMEAnalysis speed={speed_f:.0f} km/s (DBM arrival range)",
            }
        )

    out = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)
    if not out.empty:
        for c in ("source_time_utc", "arrival_min_utc", "arrival_max_utc", "arrival_mid_utc", "start_utc", "end_utc"):
            out[c] = pd.to_datetime(out[c], utc=True, errors="coerce")
        out = out.dropna(subset=["start_utc", "end_utc"]).sort_values(["start_utc", "end_utc"], ignore_index=True)
    return out


