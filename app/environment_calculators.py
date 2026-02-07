# Author: Dr Diego Malpica MD
"""Environmental calculators for extreme weather and jet lag performance.

Pure functions implementing validated scientific formulas for:
- Wind Chill Temperature (NWS 2001, Osczevski & Bluestein)
- Frostbite Time estimation (NWS lookup interpolation)
- WBGT Heat Stress Index (ISO 7243:2017, Steadman 1979 simplified)
- Heat Index (NWS/Steadman formula)
- Jet Lag circadian resynchronization model (Waterhouse et al. 2007)

Design goals (per project rules):
- Pure functions, no side effects, no recursion.
- Bounded execution, full type hints.
- All thresholds from peer-reviewed literature.

References:
- Osczevski, R., & Bluestein, M. (2005). The new wind chill equivalent
  temperature chart. Bull Amer Meteor Soc, 86(10), 1453-1458.
- ISO 7243:2017. Ergonomics of the thermal environment -- Assessment of
  heat stress using the WBGT index.
- Steadman, R.G. (1979). The assessment of sultriness. Part I.
  J Appl Meteor, 18, 861-873.
- Waterhouse, J., Reilly, T., Atkinson, G., & Edwards, B. (2007).
  Jet lag: trends and coping strategies. Lancet, 369, 1117-1129.
  PMID: 17398311
- Arendt, J. (2009). Managing jet lag. Sleep Med Rev, 13(4), 249-256.
  PMID: 19153053
- Burgess, H.J., et al. (2003). Preflight adjustment to eastward travel.
  J Biol Rhythms, 18(4), 318-328. PMID: 12932084
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


# ===================================================================
# Wind Chill (NWS 2001 formula)
# ===================================================================

@dataclass(frozen=True, slots=True)
class WindChillResult:
    """Wind chill computation result."""

    wind_chill_c: float
    frostbite_minutes: Optional[float]
    risk_category: str  # "Low", "Moderate", "High", "Very High", "Extreme"
    description: str


def compute_wind_chill(temp_c: float, wind_kmh: float) -> float:
    """Compute wind chill temperature using NWS 2001 formula.

    Formula: WC = 13.12 + 0.6215*Ta - 11.37*V^0.16 + 0.3965*Ta*V^0.16
    Valid for: Ta <= 10 C and V >= 4.8 km/h

    Args:
        temp_c: Air temperature in Celsius.
        wind_kmh: Wind speed at 10m height in km/h.

    Returns:
        Wind chill temperature in Celsius.

    Reference:
        Osczevski & Bluestein (2005). BAMS, 86(10), 1453-1458.
    """
    ta = float(temp_c)
    v = float(wind_kmh)

    if not math.isfinite(ta) or not math.isfinite(v):
        raise ValueError("Temperature and wind speed must be finite numbers.")

    # Formula only valid for cold conditions with wind
    if ta > 10.0 or v < 4.8:
        return ta  # No wind chill effect

    v_exp = v ** 0.16
    wc = 13.12 + 0.6215 * ta - 11.37 * v_exp + 0.3965 * ta * v_exp
    return round(wc, 1)


def estimate_frostbite_time_minutes(wind_chill_c: float) -> Optional[float]:
    """Estimate time to frostbite from wind chill temperature.

    Based on NWS frostbite risk categories and interpolation of the
    official NWS Wind Chill Chart lookup tables.

    Args:
        wind_chill_c: Wind chill temperature in Celsius.

    Returns:
        Estimated minutes to frostbite on exposed skin, or None if
        frostbite risk is negligible (wind chill > -18 C).

    Reference:
        NWS Wind Chill Chart (2001). weather.gov/safety/cold-wind-chill-chart
    """
    wc = float(wind_chill_c)

    if wc > -18.0:
        return None  # Frostbite unlikely
    if wc > -28.0:
        return 30.0  # ~30 minutes
    if wc > -35.0:
        return 15.0  # ~15 minutes (caution)
    if wc > -45.0:
        return 10.0  # ~10 minutes (danger)
    if wc > -55.0:
        return 5.0   # ~5 minutes (extreme danger)
    return 2.0        # <2 minutes (extreme)


def classify_cold_risk(wind_chill_c: float) -> str:
    """Classify frostbite/cold exposure risk from wind chill.

    Categories per NWS Wind Chill Chart:
    - Low: WC > -10 C
    - Moderate: -10 to -27 C
    - High: -28 to -39 C (frostbite in 10-30 min)
    - Very High: -40 to -54 C (frostbite in 5-10 min)
    - Extreme: <= -55 C (frostbite in <5 min)
    """
    wc = float(wind_chill_c)
    if wc > -10.0:
        return "Low"
    if wc > -27.0:
        return "Moderate"
    if wc > -39.0:
        return "High"
    if wc > -54.0:
        return "Very High"
    return "Extreme"


def compute_wind_chill_full(temp_c: float, wind_kmh: float) -> WindChillResult:
    """Compute wind chill with full classification and frostbite estimate."""
    wc = compute_wind_chill(temp_c, wind_kmh)
    fb = estimate_frostbite_time_minutes(wc)
    risk = classify_cold_risk(wc)

    descriptions = {
        "Low": "Minimal risk. Dress warmly for comfort.",
        "Moderate": "Risk of frostbite on prolonged exposure (>30 min). Cover exposed skin.",
        "High": "Frostbite possible in 10-30 minutes. Limit outdoor exposure.",
        "Very High": "Frostbite likely in 5-10 minutes. Avoid unnecessary outdoor activity.",
        "Extreme": "Frostbite in under 5 minutes. Outdoor activity is dangerous.",
    }

    return WindChillResult(
        wind_chill_c=wc,
        frostbite_minutes=fb,
        risk_category=risk,
        description=descriptions.get(risk, ""),
    )


# ===================================================================
# WBGT Heat Stress (ISO 7243:2017 / Steadman 1979 simplified)
# ===================================================================

@dataclass(frozen=True, slots=True)
class WBGTResult:
    """WBGT heat stress computation result."""

    wbgt_c: float
    heat_index_c: float
    risk_category: str  # "Low", "Moderate", "High", "Very High", "Extreme"
    description: str
    work_rest_guidance: str


def _water_vapor_pressure(temp_c: float, rh_pct: float) -> float:
    """Compute water vapor pressure (hPa) from temp and RH.

    Uses the Magnus-Tetens approximation:
        e_s = 6.105 * exp(17.27 * T / (237.7 + T))
        e = e_s * RH / 100

    Reference: Steadman (1979), Eq. 1.
    """
    ta = float(temp_c)
    rh = float(rh_pct)
    e_sat = 6.105 * math.exp(17.27 * ta / (237.7 + ta))
    return e_sat * rh / 100.0


def compute_wbgt_simplified(temp_c: float, rh_pct: float) -> float:
    """Estimate WBGT using the Steadman (1979) simplified formula.

    When natural wet-bulb and globe thermometer data are unavailable:
        WBGT_est = 0.567 * Ta + 0.393 * e + 3.94

    Where e = water vapor pressure (hPa).

    Args:
        temp_c: Air temperature in Celsius.
        rh_pct: Relative humidity in percent (0-100).

    Returns:
        Estimated WBGT in Celsius.

    Reference:
        Steadman, R.G. (1979). J Appl Meteor, 18, 861-873.
        ISO 7243:2017.
    """
    ta = float(temp_c)
    rh = max(0.0, min(100.0, float(rh_pct)))

    if not math.isfinite(ta) or not math.isfinite(rh):
        raise ValueError("Temperature and humidity must be finite numbers.")

    e = _water_vapor_pressure(ta, rh)
    wbgt = 0.567 * ta + 0.393 * e + 3.94
    return round(wbgt, 1)


def compute_heat_index(temp_c: float, rh_pct: float) -> float:
    """Compute Heat Index using the NWS/Rothfusz regression.

    Valid for: Ta >= 27 C (80 F) and RH >= 40%.
    Below threshold returns the air temperature.

    Args:
        temp_c: Air temperature in Celsius.
        rh_pct: Relative humidity in percent.

    Returns:
        Heat index in Celsius.

    Reference:
        Rothfusz, L.P. (1990). NWS Technical Attachment SR 90-23.
    """
    ta = float(temp_c)
    rh = max(0.0, min(100.0, float(rh_pct)))

    if ta < 27.0:
        return ta

    # Convert to Fahrenheit for NWS formula
    tf = ta * 9.0 / 5.0 + 32.0

    hi_f = (
        -42.379
        + 2.04901523 * tf
        + 10.14333127 * rh
        - 0.22475541 * tf * rh
        - 6.83783e-3 * tf * tf
        - 5.481717e-2 * rh * rh
        + 1.22874e-3 * tf * tf * rh
        + 8.5282e-4 * tf * rh * rh
        - 1.99e-6 * tf * tf * rh * rh
    )

    # Adjustments
    if rh < 13.0 and 80.0 <= tf <= 112.0:
        hi_f -= ((13.0 - rh) / 4.0) * math.sqrt((17.0 - abs(tf - 95.0)) / 17.0)
    elif rh > 85.0 and 80.0 <= tf <= 87.0:
        hi_f += ((rh - 85.0) / 10.0) * ((87.0 - tf) / 5.0)

    # Convert back to Celsius
    hi_c = (hi_f - 32.0) * 5.0 / 9.0
    return round(hi_c, 1)


def classify_heat_risk(wbgt_c: float) -> str:
    """Classify heat stress risk from WBGT per ISO 7243 / NIOSH.

    Categories:
    - Low: WBGT < 25 C
    - Moderate: 25-28 C
    - High: 28-30 C
    - Very High: 30-33 C
    - Extreme: > 33 C
    """
    wbgt = float(wbgt_c)
    if wbgt < 25.0:
        return "Low"
    if wbgt < 28.0:
        return "Moderate"
    if wbgt < 30.0:
        return "High"
    if wbgt < 33.0:
        return "Very High"
    return "Extreme"


def compute_wbgt_full(temp_c: float, rh_pct: float) -> WBGTResult:
    """Compute WBGT with full classification and work-rest guidance."""
    wbgt = compute_wbgt_simplified(temp_c, rh_pct)
    hi = compute_heat_index(temp_c, rh_pct)
    risk = classify_heat_risk(wbgt)

    descriptions = {
        "Low": "Minimal heat stress. Normal activity permitted.",
        "Moderate": "Moderate heat stress. Ensure hydration, schedule rest breaks.",
        "High": "High heat stress. Limit strenuous work. Mandatory hydration breaks.",
        "Very High": "Very high heat stress. Restrict heavy work. Medical monitoring advised.",
        "Extreme": "Extreme heat stress. Suspend non-essential outdoor activity.",
    }

    work_rest = {
        "Low": "Continuous work permitted. Monitor hydration.",
        "Moderate": "45 min work / 15 min rest per hour.",
        "High": "30 min work / 30 min rest per hour.",
        "Very High": "15 min work / 45 min rest per hour.",
        "Extreme": "Suspend work. Emergency cooling measures required.",
    }

    return WBGTResult(
        wbgt_c=wbgt,
        heat_index_c=hi,
        risk_category=risk,
        description=descriptions.get(risk, ""),
        work_rest_guidance=work_rest.get(risk, ""),
    )


# ===================================================================
# FITS — Fighter Index of Thermal Stress (USAF SAM-TR-78-6)
# ===================================================================

@dataclass(frozen=True, slots=True)
class FITSResult:
    """Fighter Index of Thermal Stress result."""

    fits_c: float
    zone: str  # "Normal", "Caution", "Danger"
    description: str
    operational_guidance: str


def _psychrometric_wet_bulb(temp_c: float, rh_pct: float) -> float:
    """Estimate psychrometric wet bulb temperature from temp and RH.

    Uses the Stull (2011) approximation valid for RH 5-99% and T 20-50 C:
        Twb = T * atan(0.151977*(RH+8.313659)^0.5) + atan(T+RH)
              - atan(RH-1.676331) + 0.00391838*(RH)^1.5 * atan(0.023101*RH)
              - 4.686035
    """
    t = float(temp_c)
    rh = max(5.0, min(99.0, float(rh_pct)))
    twb = (
        t * math.atan(0.151977 * (rh + 8.313659) ** 0.5)
        + math.atan(t + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * rh ** 1.5 * math.atan(0.023101 * rh)
        - 4.686035
    )
    return round(twb, 2)


def compute_fits(
    temp_c: float,
    rh_pct: float,
    *,
    direct_sun: bool = True,
) -> FITSResult:
    """Compute Fighter Index of Thermal Stress (FITS).

    FITS estimates cockpit WBGT during low-level fighter/trainer flight
    from ground weather data. Developed by Stribley & Nunneley (1978)
    at the USAF School of Aerospace Medicine.

    Equations (SAM-TR-78-6, Eqs. 9-10):
        FITS_DS = 0.8281 * Tpwb + 0.3549 * Tdb + 5.08  (direct sun)
        FITS_MO = 0.8281 * Tpwb + 0.3549 * Tdb + 2.23  (moderate overcast)

    Zones (cockpit WBGT equivalent):
        Normal:  FITS < 32 C
        Caution: 32 <= FITS < 38 C
        Danger:  FITS >= 38 C

    Args:
        temp_c: Ground dry bulb temperature in Celsius.
        rh_pct: Relative humidity in percent (0-100).
        direct_sun: True for clear sky/light overcast, False for moderate
                    overcast with no shadows visible.

    Returns:
        FITSResult with FITS value, zone, and operational guidance.

    Reference:
        Stribley, R.F., & Nunneley, S.A. (1978). Fighter Index of
        Thermal Stress: Development of Interim Guidance for Hot-Weather
        USAF Operations. SAM-TR-78-6. Brooks AFB, TX.
    """
    ta = float(temp_c)
    rh = max(0.0, min(100.0, float(rh_pct)))

    if not math.isfinite(ta) or not math.isfinite(rh):
        raise ValueError("Temperature and humidity must be finite numbers.")

    twb = _psychrometric_wet_bulb(ta, rh)
    offset = 5.08 if direct_sun else 2.23
    fits = 0.8281 * twb + 0.3549 * ta + offset
    fits = round(fits, 1)

    if fits >= 38.0:
        zone = "Danger"
        desc = (
            f"FITS={fits} C (Danger Zone). Cockpit WBGT exceeds 38 C. "
            "Progressive heat storage and dehydration will impair crew "
            "performance and acceleration tolerance."
        )
        guidance = (
            "Cancel low-level flights (<915 m AGL). "
            "Limit ground period to 45 min. "
            "Minimum 2-hr cool recovery between flights. "
            "Cancel all nonessential flights if FITS > 46 C."
        )
    elif fits >= 32.0:
        zone = "Caution"
        desc = (
            f"FITS={fits} C (Caution Zone). Cockpit conditions are tolerable "
            "for low-level flight if precautions are taken. Cumulative "
            "fatigue and decreased learning may occur."
        )
        guidance = (
            "Alert all aircrew to heat conditions. "
            "Limit ground operations (preflight + standby) to 90 min. "
            "Minimum 2-hr cool recovery between flights. "
            "Ensure ample fluid intake."
        )
    else:
        zone = "Normal"
        desc = (
            f"FITS={fits} C (Normal Zone). Cockpit conditions are subjectively "
            "hot but usually safe with standard precautions."
        )
        guidance = (
            "Follow general hot-weather precautions. "
            "Allow acclimatization for personnel newly arrived from cooler climates. "
            "Maintain adequate fluid intake."
        )

    return FITSResult(
        fits_c=fits,
        zone=zone,
        description=desc,
        operational_guidance=guidance,
    )


# ===================================================================
# Jet Lag Performance Model
# ===================================================================

@dataclass(frozen=True, slots=True)
class JetLagAssessment:
    """Jet lag performance impact assessment."""

    time_zones_crossed: int
    direction: str  # "east" or "west"
    days_since_travel: float
    resync_rate_h_per_day: float
    days_to_full_resync: float
    performance_factor: float  # 0.0-1.0 (1.0 = fully recovered)
    readiness_modifier: float  # bounded +/-6
    phase: str  # "acute", "recovering", "recovered"
    description: str


def compute_jet_lag_performance(
    time_zones: int,
    direction: str,
    days_since: float,
) -> JetLagAssessment:
    """Compute jet lag impact on performance.

    Model based on Waterhouse et al. (2007) circadian resynchronization
    rates and exponential recovery dynamics.

    Phase shift rates (Arendt, 2009):
    - Westward: ~1.0 h/day (phase delay, easier)
    - Eastward: ~0.67 h/day (phase advance, harder)

    Performance decrement follows exponential decay:
        factor = 1.0 - peak_penalty * exp(-days / tau)
    Where tau = days_to_resync / 3 (time constant).

    Args:
        time_zones: Absolute number of time zones crossed (1-12).
        direction: "east" or "west".
        days_since: Days elapsed since arrival (0 = just arrived).

    Returns:
        JetLagAssessment with performance factor and readiness modifier.

    References:
        Waterhouse et al. (2007). Lancet, 369, 1117-1129. PMID: 17398311
        Arendt (2009). Sleep Med Rev, 13(4), 249-256. PMID: 19153053
    """
    tz = max(0, min(12, int(time_zones)))
    d = max(0.0, float(days_since))
    dir_str = str(direction).lower().strip()

    if dir_str not in ("east", "west"):
        raise ValueError("direction must be 'east' or 'west'")

    if tz == 0:
        return JetLagAssessment(
            time_zones_crossed=0,
            direction=dir_str,
            days_since_travel=d,
            resync_rate_h_per_day=0.0,
            days_to_full_resync=0.0,
            performance_factor=1.0,
            readiness_modifier=0.0,
            phase="recovered",
            description="No time zone change. No jet lag expected.",
        )

    # Resynchronization rates (Arendt, 2009)
    rate = 1.0 if dir_str == "west" else 0.67  # h/day

    # Days to full resynchronization
    days_full = float(tz) / rate

    # Peak performance penalty: ~3% per time zone, max 30%
    peak_penalty = min(0.30, 0.03 * tz)

    # Exponential recovery: tau = days_full / 3
    tau = max(1.0, days_full / 3.0)

    if d >= days_full:
        perf = 1.0
        phase = "recovered"
    elif d < 1.0:
        perf = 1.0 - peak_penalty
        phase = "acute"
    else:
        perf = 1.0 - peak_penalty * math.exp(-d / tau)
        phase = "recovering"

    perf = max(0.0, min(1.0, perf))

    # Readiness modifier: bounded +/-6 pts
    # Maps performance_factor [0.7, 1.0] -> [-6, 0]
    if perf >= 1.0:
        modifier = 0.0
    else:
        deficit = 1.0 - perf
        modifier = -min(6.0, deficit * 20.0)  # 0.30 deficit -> -6 pts

    modifier = max(-6.0, min(0.0, modifier))

    descriptions = {
        "acute": (
            f"Acute jet lag phase ({tz} zones {dir_str}). "
            f"Performance reduced by ~{peak_penalty * 100:.0f}%. "
            "Expect fatigue, cognitive impairment, sleep disruption. "
            "Avoid critical tasks if possible."
        ),
        "recovering": (
            f"Recovering from {tz}-zone {dir_str}ward travel (day {d:.1f}/{days_full:.0f}). "
            f"Performance at ~{perf * 100:.0f}% of baseline. "
            f"Resynchronizing at ~{rate:.2f} h/day."
        ),
        "recovered": (
            f"Fully resynchronized after {tz}-zone {dir_str}ward travel. "
            "No performance penalty."
        ),
    }

    return JetLagAssessment(
        time_zones_crossed=tz,
        direction=dir_str,
        days_since_travel=d,
        resync_rate_h_per_day=rate,
        days_to_full_resync=round(days_full, 1),
        performance_factor=round(perf, 3),
        readiness_modifier=round(modifier, 1),
        phase=phase,
        description=descriptions.get(phase, ""),
    )


# ===================================================================
# ICE Station Simulated Sensor Data
# ===================================================================

@dataclass(frozen=True, slots=True)
class ICEStationReading:
    """Single ICE station environmental reading."""

    temperature_c: float
    humidity_pct: float
    co2_ppm: float
    pressure_hpa: float
    pm25_ugm3: float
    noise_db: float
    light_lux: float
    o2_pct: float


def generate_ice_station_data(hour_of_day: int = 12) -> ICEStationReading:
    """Generate realistic simulated ICE station sensor readings.

    Simulates an Antarctic research station habitat with realistic
    diurnal patterns and bounded noise.

    Args:
        hour_of_day: Current hour (0-23) for diurnal variation.

    Returns:
        ICEStationReading with all 8 sensor values.
    """
    import random

    h = max(0, min(23, int(hour_of_day)))

    # Temperature: diurnal pattern 19-22 C, cooler at night
    base_temp = 20.5 + 1.5 * math.sin(2 * math.pi * (h - 6) / 24.0)
    temp = base_temp + random.gauss(0, 0.3)

    # Humidity: inverse of temp somewhat, 35-50%
    base_rh = 42.0 - 5.0 * math.sin(2 * math.pi * (h - 6) / 24.0)
    rh = base_rh + random.gauss(0, 2.0)

    # CO2: rises during day (people active), drops at night
    base_co2 = 650 + 200 * math.sin(2 * math.pi * (h - 8) / 24.0)
    co2 = base_co2 + random.gauss(0, 30)

    # Pressure: stable with small drift
    pressure = 985.0 + random.gauss(0, 3.0)

    # PM2.5: low, small spikes during cooking hours
    base_pm = 8.0
    if 7 <= h <= 8 or 12 <= h <= 13 or 18 <= h <= 19:
        base_pm = 18.0
    pm25 = max(1.0, base_pm + random.gauss(0, 3.0))

    # Noise: quieter at night
    base_noise = 35.0 if h < 7 or h > 22 else 45.0
    noise = max(20.0, base_noise + random.gauss(0, 3.0))

    # Light: follows artificial schedule (dark outside in polar winter)
    if 7 <= h <= 22:
        light = 350.0 + random.gauss(0, 30.0)
    else:
        light = max(5.0, 20.0 + random.gauss(0, 5.0))

    # O2: very stable in pressurized habitat
    o2 = 20.8 + random.gauss(0, 0.1)

    return ICEStationReading(
        temperature_c=round(temp, 1),
        humidity_pct=round(max(10, min(90, rh)), 1),
        co2_ppm=round(max(350, co2)),
        pressure_hpa=round(pressure, 1),
        pm25_ugm3=round(max(0, pm25), 1),
        noise_db=round(max(15, noise), 1),
        light_lux=round(max(0, light)),
        o2_pct=round(max(18.0, min(22.0, o2)), 2),
    )
