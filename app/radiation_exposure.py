"""
Radiation Exposure Module for Space Mission Medical Support.

Provides evidence-based radiation dose rate estimates for various space environments
and builds day-by-day cumulative exposure tracking with EVA risk matrices.

References:
- Zhang et al. (2020). First measurements of the radiation dose on the lunar surface.
  Science Advances, 6(39), eaaz1334. DOI: 10.1126/sciadv.aaz1334
- Cucinotta et al. (2013). Space radiation cancer risk projections and uncertainties.
  NASA Technical Report. https://three.jsc.nasa.gov/articles/AstronautRadLimitsFC.pdf
- Berger et al. (2020). MATROSHKA-R experiment: Radiation dose rate estimates on ISS.
  Radiation Measurements, 132, 106244.
- NASA-STD-3001 Vol 1 Rev B (2022). Crew Health Standard.
- Simonsen et al. (2025). Moon to Mars Space Radiation Protection.
  NASA ASCEND Technical Report.
- ICRP Publication 123 (2013). Assessment of radiation exposure of astronauts in space.

Author: Dr Diego Malpica MD
Version: 1.0.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Final, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

try:
    from logging_config import get_logger
except ImportError:  # pragma: no cover
    get_logger = None  # type: ignore[assignment]

_LOGGER: Final[logging.Logger] = (
    get_logger(__name__) if get_logger is not None else logging.getLogger(__name__)
)


# =============================================================================
# RADIATION ENVIRONMENT DEFINITIONS
# =============================================================================

class RadiationEnvironment(Enum):
    """Space radiation environments with reference dose rates."""
    
    # Earth-based analogs
    EARTH_SURFACE = "earth_surface"
    EARTH_FLIGHT_ALTITUDE = "earth_flight_altitude"
    ANTARCTICA = "antarctica"
    
    # Low Earth Orbit
    LEO_ISS = "leo_iss"
    
    # Cislunar
    LUNAR_GATEWAY = "lunar_gateway"
    TRANSLUNAR_INJECTION = "translunar_injection"  # TLI - Earth to Moon transit
    LUNAR_TRANSIT = "lunar_transit"
    
    # Lunar Surface
    LUNAR_SURFACE_NOMINAL = "lunar_surface_nominal"
    LUNAR_SURFACE_SPE = "lunar_surface_spe"  # Solar Particle Event
    
    # Mars
    TRANS_MARTIAN_INJECTION = "trans_martian_injection"  # TMI - Earth to Mars transit
    MARS_TRANSIT = "mars_transit"
    MARS_ORBIT = "mars_orbit"  # Orbiting Mars
    MARS_SURFACE = "mars_surface"


@dataclass(frozen=True, slots=True)
class RadiationDoseRate:
    """Radiation dose rate for a specific environment.
    
    All rates are effective dose in mSv/day.
    """
    
    environment: RadiationEnvironment
    nominal_msv_per_day: float
    range_low_msv_per_day: float
    range_high_msv_per_day: float
    reference: str
    notes: str = ""
    solar_cycle_dependent: bool = True
    eva_multiplier: float = 1.0  # Multiplier for reduced shielding during EVA


# =============================================================================
# EVIDENCE-BASED DOSE RATE DATABASE
# =============================================================================

# Literature-derived dose rates (mSv/day) for each environment
# Sources: Chang'E-4 LND, MSL RAD, ISS measurements, ICRP 123, NASA STD-3001

DOSE_RATE_DATABASE: Dict[RadiationEnvironment, RadiationDoseRate] = {
    # -------------------------------------------------------------------------
    # Earth Surface (~2.4 mSv/year = 0.0066 mSv/day)
    # Source: UNSCEAR 2000 Report
    # -------------------------------------------------------------------------
    RadiationEnvironment.EARTH_SURFACE: RadiationDoseRate(
        environment=RadiationEnvironment.EARTH_SURFACE,
        nominal_msv_per_day=0.0066,  # ~2.4 mSv/year
        range_low_msv_per_day=0.005,
        range_high_msv_per_day=0.011,  # ~4 mSv/year in high background areas
        reference="UNSCEAR 2000; world average effective dose",
        notes="Includes cosmic, terrestrial, radon. Location-dependent.",
        solar_cycle_dependent=False,
        eva_multiplier=1.0,
    ),
    
    # -------------------------------------------------------------------------
    # Earth Flight Altitude (~6 μSv/h = 0.144 mSv/day at 35,000 ft)
    # Source: FAA AC 120-52, ICRP 103
    # -------------------------------------------------------------------------
    RadiationEnvironment.EARTH_FLIGHT_ALTITUDE: RadiationDoseRate(
        environment=RadiationEnvironment.EARTH_FLIGHT_ALTITUDE,
        nominal_msv_per_day=0.144,  # ~6 μSv/h at 35,000 ft
        range_low_msv_per_day=0.072,  # ~3 μSv/h at lower altitudes
        range_high_msv_per_day=0.288,  # ~12 μSv/h at high latitudes/altitudes
        reference="FAA AC 120-52; O'Brien 1978; ICRP 103",
        notes="Polar routes higher; solar max reduces GCR.",
        solar_cycle_dependent=True,
        eva_multiplier=1.0,
    ),
    
    # -------------------------------------------------------------------------
    # Antarctica (High-altitude plateau: ~1-1.5 mSv/year = ~0.003-0.004 mSv/day)
    # Source: Mishev et al. 2023, Radiation Environment in High-Altitude Antarctic
    # -------------------------------------------------------------------------
    RadiationEnvironment.ANTARCTICA: RadiationDoseRate(
        environment=RadiationEnvironment.ANTARCTICA,
        nominal_msv_per_day=0.003,  # ~1.1 mSv/year at sea level
        range_low_msv_per_day=0.0027,  # ~1 mSv/year
        range_high_msv_per_day=0.008,  # ~3 mSv/year at high altitude stations (Dome C)
        reference="Mishev et al. (2023); SANAE IV station data",
        notes="High-altitude stations (Dome C, South Pole) exceed 1 mSv/year ICRP limit.",
        solar_cycle_dependent=True,
        eva_multiplier=1.5,  # Outdoor activities increase exposure
    ),
    
    # -------------------------------------------------------------------------
    # ISS / LEO (~0.3-0.7 mSv/day effective dose)
    # Source: Berger et al. 2020, NASA LSAH Newsletter 2023
    # -------------------------------------------------------------------------
    RadiationEnvironment.LEO_ISS: RadiationDoseRate(
        environment=RadiationEnvironment.LEO_ISS,
        nominal_msv_per_day=0.50,  # Middle of observed range
        range_low_msv_per_day=0.20,  # Solar max, more shielded areas
        range_high_msv_per_day=0.73,  # Solar min, SAA passages
        reference="Berger et al. (2020); NASA LSAH Newsletter 2023",
        notes="~72-160 mSv per 6-month mission. SAA passages dominate.",
        solar_cycle_dependent=True,
        eva_multiplier=1.5,  # EVA outside station hull
    ),
    
    # -------------------------------------------------------------------------
    # Lunar Gateway (Cislunar, ~1.0-1.5 mSv/day)
    # Source: NASA ASCEND Simonsen 2025, ICRP 123
    # -------------------------------------------------------------------------
    RadiationEnvironment.LUNAR_GATEWAY: RadiationDoseRate(
        environment=RadiationEnvironment.LUNAR_GATEWAY,
        nominal_msv_per_day=1.30,  # Design target
        range_low_msv_per_day=0.80,  # Solar max, optimal shielding
        range_high_msv_per_day=1.80,  # Solar min
        reference="Simonsen et al. (2025); NASA ASCEND; ICRP 123",
        notes="No magnetospheric protection. ~2-3x ISS rate.",
        solar_cycle_dependent=True,
        eva_multiplier=1.8,
    ),
    
    # -------------------------------------------------------------------------
    # Translunar Injection (TLI - Earth to Moon transit, ~1.3-1.8 mSv/day)
    # Source: Apollo TLI phase, modern projections
    # -------------------------------------------------------------------------
    RadiationEnvironment.TRANSLUNAR_INJECTION: RadiationDoseRate(
        environment=RadiationEnvironment.TRANSLUNAR_INJECTION,
        nominal_msv_per_day=1.50,  # Similar to lunar transit
        range_low_msv_per_day=1.00,  # Solar max
        range_high_msv_per_day=2.00,  # Solar min
        reference="ICRP 123; Apollo TLI phase; Simonsen (2025)",
        notes="Free-space transit from Earth to Moon. No magnetospheric protection.",
        solar_cycle_dependent=True,
        eva_multiplier=2.0,
    ),
    
    # -------------------------------------------------------------------------
    # Lunar Transit (~1.3-1.8 mSv/day)
    # Source: Apollo dosimetry, modern projections
    # -------------------------------------------------------------------------
    RadiationEnvironment.LUNAR_TRANSIT: RadiationDoseRate(
        environment=RadiationEnvironment.LUNAR_TRANSIT,
        nominal_msv_per_day=1.50,
        range_low_msv_per_day=1.00,
        range_high_msv_per_day=2.00,
        reference="ICRP 123; Apollo retrospective; Simonsen (2025)",
        notes="Free-space, no planetary shielding.",
        solar_cycle_dependent=True,
        eva_multiplier=2.0,
    ),
    
    # -------------------------------------------------------------------------
    # Lunar Surface Nominal (~1.369 mSv/day from Chang'E-4 LND)
    # Source: Zhang et al. 2020, Science Advances
    # -------------------------------------------------------------------------
    RadiationEnvironment.LUNAR_SURFACE_NOMINAL: RadiationDoseRate(
        environment=RadiationEnvironment.LUNAR_SURFACE_NOMINAL,
        nominal_msv_per_day=1.369,  # Chang'E-4 LND measurement
        range_low_msv_per_day=1.00,  # Solar max
        range_high_msv_per_day=1.80,  # Solar min, GCR peak
        reference="Zhang et al. (2020), Science Advances 6(39), eaaz1334",
        notes="First direct lunar surface measurement. ~60 μSv/h = 1.44 mSv/day.",
        solar_cycle_dependent=True,
        eva_multiplier=1.5,  # EVA suit less shielding than habitat
    ),
    
    # -------------------------------------------------------------------------
    # Lunar Surface during SPE (Solar Particle Event)
    # Source: ICRP 123, worst-case SPE modeling
    # -------------------------------------------------------------------------
    RadiationEnvironment.LUNAR_SURFACE_SPE: RadiationDoseRate(
        environment=RadiationEnvironment.LUNAR_SURFACE_SPE,
        nominal_msv_per_day=50.0,  # Moderate SPE
        range_low_msv_per_day=10.0,  # Minor SPE
        range_high_msv_per_day=500.0,  # Carrington-class event
        reference="ICRP 123; Cucinotta (2014); NASA STD-3001",
        notes="SPE can deliver months of GCR dose in hours. Shelter required.",
        solar_cycle_dependent=False,  # SPEs are stochastic
        eva_multiplier=3.0,  # EVA during SPE is prohibited
    ),
    
    # -------------------------------------------------------------------------
    # Trans-Martian Injection (TMI - Earth to Mars transit, ~1.8-2.5 mSv/day)
    # Source: MSL RAD early cruise, modern projections
    # -------------------------------------------------------------------------
    RadiationEnvironment.TRANS_MARTIAN_INJECTION: RadiationDoseRate(
        environment=RadiationEnvironment.TRANS_MARTIAN_INJECTION,
        nominal_msv_per_day=1.90,  # Similar to Mars transit, slightly higher
        range_low_msv_per_day=1.30,  # Solar max
        range_high_msv_per_day=2.50,  # Solar min
        reference="Zeitlin et al. (2013); MSL RAD early cruise; ICRP 123",
        notes="Initial phase of Earth-Mars transit. Free-space, no planetary shielding.",
        solar_cycle_dependent=True,
        eva_multiplier=2.0,
    ),
    
    # -------------------------------------------------------------------------
    # Mars Transit (~1.3-1.8 mSv/day)
    # Source: MSL RAD cruise phase
    # -------------------------------------------------------------------------
    RadiationEnvironment.MARS_TRANSIT: RadiationDoseRate(
        environment=RadiationEnvironment.MARS_TRANSIT,
        nominal_msv_per_day=1.84,  # MSL RAD cruise measurement
        range_low_msv_per_day=1.30,  # Solar max
        range_high_msv_per_day=2.50,  # Solar min
        reference="Zeitlin et al. (2013), Science 340(6136), 1080-1084",
        notes="~331 mSv for 180-day cruise. GCR dominates.",
        solar_cycle_dependent=True,
        eva_multiplier=2.0,
    ),
    
    # -------------------------------------------------------------------------
    # Mars Orbit (~0.7-1.0 mSv/day)
    # Source: MSL RAD approach phase, orbital modeling
    # -------------------------------------------------------------------------
    RadiationEnvironment.MARS_ORBIT: RadiationDoseRate(
        environment=RadiationEnvironment.MARS_ORBIT,
        nominal_msv_per_day=0.85,  # Between transit and surface
        range_low_msv_per_day=0.60,  # Solar max
        range_high_msv_per_day=1.20,  # Solar min
        reference="Zeitlin et al. (2013); MSL RAD approach; orbital modeling",
        notes="Mars orbital environment. Some planetary shielding from Mars.",
        solar_cycle_dependent=True,
        eva_multiplier=1.8,
    ),
    
    # -------------------------------------------------------------------------
    # Mars Surface (~0.64 mSv/day)
    # Source: MSL RAD surface measurements
    # -------------------------------------------------------------------------
    RadiationEnvironment.MARS_SURFACE: RadiationDoseRate(
        environment=RadiationEnvironment.MARS_SURFACE,
        nominal_msv_per_day=0.64,  # MSL RAD surface average
        range_low_msv_per_day=0.45,  # Solar max
        range_high_msv_per_day=0.80,  # Solar min
        reference="Hassler et al. (2014), Science 343(6169), 1244797",
        notes="~233 mSv for 365-day surface stay. Atmosphere provides ~2x shielding.",
        solar_cycle_dependent=True,
        eva_multiplier=1.3,  # Mars EVA suit provides less shielding
    ),
}


# =============================================================================
# RADIATION EXPOSURE RISK THRESHOLDS (NASA STD-3001 Vol 1 Rev B)
# =============================================================================

@dataclass(frozen=True, slots=True)
class RadiationLimits:
    """NASA radiation exposure limits per STD-3001 Vol 1 Rev B (2022)."""
    
    # Career limits
    career_effective_dose_msv: float = 600.0  # NASA 2022 unified limit
    career_legacy_limit_msv: float = 1000.0  # Pre-2022 planning value
    
    # Mission limits
    bfo_30_day_limit_mgy_eq: float = 250.0  # Blood Forming Organs
    bfo_annual_limit_mgy_eq: float = 500.0
    eye_annual_limit_mgy_eq: float = 2000.0
    skin_annual_limit_mgy_eq: float = 3000.0
    
    # Operational thresholds for EVA Go/No-Go
    eva_abort_msv_per_hour: float = 0.5  # Abort EVA if rate exceeds this
    eva_shelter_msv_per_hour: float = 0.2  # Seek shelter if rate exceeds
    eva_nominal_msv_per_hour: float = 0.1  # Normal EVA conditions
    
    # Alert thresholds (% of career limit)
    alert_green_pct: float = 0.0  # 0-30% = GO
    alert_yellow_pct: float = 30.0  # 30-60% = MONITOR
    alert_orange_pct: float = 60.0  # 60-80% = CAUTION
    alert_red_pct: float = 80.0  # >80% = NO-GO for further exposure


NASA_RADIATION_LIMITS: Final[RadiationLimits] = RadiationLimits()


# =============================================================================
# EVA RADIATION RISK MATRIX
# =============================================================================

class EVARadiationStatus(Enum):
    """EVA clearance status based on radiation exposure."""
    GO = "GO"
    GO_WITH_MONITORING = "GO_WITH_MONITORING"
    CAUTION = "CAUTION"
    NO_GO = "NO_GO"


@dataclass(slots=True)
class EVARadiationAssessment:
    """Assessment of radiation risk for EVA operations."""
    
    status: EVARadiationStatus
    cumulative_dose_msv: float
    daily_rate_msv: float
    career_pct_used: float
    remaining_career_msv: float
    max_eva_hours_today: float
    rationale: str
    recommendations: List[str] = field(default_factory=list)
    space_weather_alert: str = "None"


def assess_eva_radiation_risk(
    *,
    cumulative_dose_msv: float,
    environment: RadiationEnvironment,
    eva_duration_hours: float = 6.0,
    space_weather_s_scale: int = 0,
    space_weather_g_scale: int = 0,
    limits: RadiationLimits = NASA_RADIATION_LIMITS,
) -> EVARadiationAssessment:
    """Assess radiation risk for planned EVA.
    
    Args:
        cumulative_dose_msv: Current cumulative career dose (mSv).
        environment: Current radiation environment.
        eva_duration_hours: Planned EVA duration in hours.
        space_weather_s_scale: NOAA S-scale (0-5, radiation storm level).
        space_weather_g_scale: NOAA G-scale (0-5, geomagnetic storm level).
        limits: Radiation limits to apply.
        
    Returns:
        EVARadiationAssessment with Go/No-Go status and recommendations.
    """
    dose_rate = DOSE_RATE_DATABASE.get(environment)
    if dose_rate is None:
        dose_rate = DOSE_RATE_DATABASE[RadiationEnvironment.LEO_ISS]
    
    # Calculate EVA dose rate (apply EVA multiplier)
    eva_msv_per_hour = (dose_rate.nominal_msv_per_day * dose_rate.eva_multiplier) / 24.0
    
    # Adjust for space weather
    if space_weather_s_scale >= 3:
        # S3+ radiation storm: significant enhancement
        eva_msv_per_hour *= (2.0 + space_weather_s_scale)
    elif space_weather_s_scale >= 1:
        eva_msv_per_hour *= (1.5 + 0.3 * space_weather_s_scale)
    
    # Calculate projected EVA dose
    projected_eva_dose = eva_msv_per_hour * eva_duration_hours
    new_cumulative = cumulative_dose_msv + projected_eva_dose
    
    # Career percentage calculations
    career_pct = (new_cumulative / limits.career_effective_dose_msv) * 100.0
    remaining_career = max(0.0, limits.career_effective_dose_msv - new_cumulative)
    
    # Determine status
    recommendations: List[str] = []
    
    # Check space weather constraints first
    if space_weather_s_scale >= 4:
        status = EVARadiationStatus.NO_GO
        rationale = f"S{space_weather_s_scale} radiation storm in progress. EVA prohibited."
        recommendations.append("Shelter in most shielded area of habitat.")
        recommendations.append("Monitor for SPE all-clear from mission control.")
    elif space_weather_s_scale >= 2:
        status = EVARadiationStatus.CAUTION
        rationale = f"S{space_weather_s_scale} radiation storm. EVA requires enhanced monitoring."
        recommendations.append("Limit EVA duration to essential tasks only.")
        recommendations.append("Continuous dosimeter monitoring required.")
    elif eva_msv_per_hour >= limits.eva_abort_msv_per_hour:
        status = EVARadiationStatus.NO_GO
        rationale = f"EVA dose rate {eva_msv_per_hour:.3f} mSv/h exceeds abort threshold."
        recommendations.append("Delay EVA until radiation environment improves.")
    elif career_pct >= limits.alert_red_pct:
        status = EVARadiationStatus.NO_GO
        rationale = f"Career dose at {career_pct:.1f}% of limit. Additional exposure restricted."
        recommendations.append("Prioritize crew member with lower cumulative dose.")
    elif career_pct >= limits.alert_orange_pct:
        status = EVARadiationStatus.CAUTION
        rationale = f"Career dose at {career_pct:.1f}% of limit. Minimize exposure."
        recommendations.append("Limit EVA duration to essential tasks.")
        recommendations.append("Consider task reassignment to other crew members.")
    elif career_pct >= limits.alert_yellow_pct or space_weather_s_scale >= 1:
        status = EVARadiationStatus.GO_WITH_MONITORING
        rationale = f"Elevated monitoring required. Career dose: {career_pct:.1f}%."
        recommendations.append("Active dosimetry monitoring during EVA.")
    else:
        status = EVARadiationStatus.GO
        rationale = f"Nominal radiation conditions. Career dose: {career_pct:.1f}%."
        recommendations.append("Standard EVA radiation monitoring protocols.")
    
    # Calculate max EVA hours remaining today
    remaining_today = max(0.0, (limits.career_effective_dose_msv - cumulative_dose_msv))
    max_eva_hours = remaining_today / eva_msv_per_hour if eva_msv_per_hour > 0 else 24.0
    max_eva_hours = min(max_eva_hours, 12.0)  # Physical limit
    
    # Space weather alert string
    space_alert = "None"
    if space_weather_s_scale >= 1:
        space_alert = f"S{space_weather_s_scale}"
    if space_weather_g_scale >= 1:
        space_alert = f"{space_alert}/G{space_weather_g_scale}" if space_alert != "None" else f"G{space_weather_g_scale}"
    
    return EVARadiationAssessment(
        status=status,
        cumulative_dose_msv=new_cumulative,
        daily_rate_msv=dose_rate.nominal_msv_per_day,
        career_pct_used=career_pct,
        remaining_career_msv=remaining_career,
        max_eva_hours_today=max_eva_hours,
        rationale=rationale,
        recommendations=recommendations,
        space_weather_alert=space_alert,
    )


# =============================================================================
# CUMULATIVE EXPOSURE TIMELINE
# =============================================================================

@dataclass(slots=True)
class DailyRadiationExposure:
    """Daily radiation exposure record."""
    
    date: date
    mission_day: int
    environment: RadiationEnvironment
    daily_dose_msv: float
    eva_hours: float
    eva_dose_msv: float
    total_dose_msv: float
    cumulative_dose_msv: float
    career_pct_used: float
    space_weather_s_scale: int = 0
    space_weather_g_scale: int = 0
    notes: str = ""


def build_radiation_timeline(
    *,
    start_date: date,
    end_date: date,
    environment: RadiationEnvironment,
    initial_cumulative_msv: float = 0.0,
    eva_schedule: Optional[Dict[date, float]] = None,  # date -> EVA hours
    solar_cycle_phase: str = "declining",  # "minimum", "ascending", "maximum", "declining"
    career_limit_msv: float = 600.0,
) -> List[DailyRadiationExposure]:
    """Build a day-by-day radiation exposure timeline.
    
    Args:
        start_date: Mission start date.
        end_date: Mission end date (or projection end).
        environment: Primary radiation environment.
        initial_cumulative_msv: Pre-mission cumulative dose.
        eva_schedule: Optional dict mapping dates to planned EVA hours.
        solar_cycle_phase: Current phase for dose rate adjustment.
        career_limit_msv: Career limit for percentage calculation.
        
    Returns:
        List of DailyRadiationExposure records.
    """
    dose_rate = DOSE_RATE_DATABASE.get(environment)
    if dose_rate is None:
        dose_rate = DOSE_RATE_DATABASE[RadiationEnvironment.LEO_ISS]
    
    # Adjust dose rate for solar cycle
    cycle_multiplier = {
        "minimum": 1.20,  # Solar min = higher GCR
        "ascending": 1.05,
        "maximum": 0.80,  # Solar max = lower GCR
        "declining": 1.00,
    }.get(solar_cycle_phase, 1.00)
    
    base_rate = dose_rate.nominal_msv_per_day * cycle_multiplier
    eva_rate_per_hour = (base_rate * dose_rate.eva_multiplier) / 24.0
    
    eva_schedule = eva_schedule or {}
    timeline: List[DailyRadiationExposure] = []
    cumulative = initial_cumulative_msv
    current_date = start_date
    mission_day = 0
    
    while current_date <= end_date:
        mission_day += 1
        eva_hours = eva_schedule.get(current_date, 0.0)
        eva_dose = eva_hours * eva_rate_per_hour
        daily_dose = base_rate + eva_dose
        cumulative += daily_dose
        career_pct = (cumulative / career_limit_msv) * 100.0
        
        record = DailyRadiationExposure(
            date=current_date,
            mission_day=mission_day,
            environment=environment,
            daily_dose_msv=base_rate,
            eva_hours=eva_hours,
            eva_dose_msv=eva_dose,
            total_dose_msv=daily_dose,
            cumulative_dose_msv=cumulative,
            career_pct_used=career_pct,
        )
        timeline.append(record)
        current_date += timedelta(days=1)
    
    return timeline


def timeline_to_dataframe(timeline: List[DailyRadiationExposure]) -> pd.DataFrame:
    """Convert radiation timeline to pandas DataFrame."""
    if not timeline:
        return pd.DataFrame()
    
    records = []
    for entry in timeline:
        records.append({
            "date": entry.date,
            "mission_day": entry.mission_day,
            "environment": entry.environment.value,
            "daily_dose_msv": entry.daily_dose_msv,
            "eva_hours": entry.eva_hours,
            "eva_dose_msv": entry.eva_dose_msv,
            "total_dose_msv": entry.total_dose_msv,
            "cumulative_dose_msv": entry.cumulative_dose_msv,
            "career_pct_used": entry.career_pct_used,
            "space_weather_s_scale": entry.space_weather_s_scale,
            "space_weather_g_scale": entry.space_weather_g_scale,
        })
    
    return pd.DataFrame(records)


# =============================================================================
# ENVIRONMENT COMPARISON UTILITIES
# =============================================================================

def compare_environments(
    *,
    mission_duration_days: int = 30,
    eva_hours_total: float = 0.0,
    initial_dose_msv: float = 0.0,
) -> pd.DataFrame:
    """Compare cumulative dose across all environments for a given mission duration.
    
    Returns DataFrame with columns: environment, nominal_rate, projected_dose, career_pct.
    """
    results = []
    for env, rate in DOSE_RATE_DATABASE.items():
        # Skip SPE variant (it's an acute event, not steady-state)
        if env == RadiationEnvironment.LUNAR_SURFACE_SPE:
            continue
        
        daily_rate = rate.nominal_msv_per_day
        eva_per_day = eva_hours_total / max(1, mission_duration_days)
        eva_rate = (daily_rate * rate.eva_multiplier - daily_rate) * (eva_per_day / 24.0)
        total_daily = daily_rate + eva_rate
        projected = initial_dose_msv + (total_daily * mission_duration_days)
        career_pct = (projected / NASA_RADIATION_LIMITS.career_effective_dose_msv) * 100.0
        
        results.append({
            "environment": env.value.replace("_", " ").title(),
            "nominal_rate_msv_day": round(daily_rate, 4),
            "total_rate_msv_day": round(total_daily, 4),
            "projected_dose_msv": round(projected, 2),
            "career_pct": round(career_pct, 2),
            "reference": rate.reference,
        })
    
    return pd.DataFrame(results).sort_values("nominal_rate_msv_day")


def get_environment_by_name(name: str) -> Optional[RadiationEnvironment]:
    """Get RadiationEnvironment enum by string name (case-insensitive)."""
    name_lower = name.lower().replace(" ", "_").replace("-", "_")
    for env in RadiationEnvironment:
        if env.value.lower() == name_lower:
            return env
    # Partial matching
    for env in RadiationEnvironment:
        if name_lower in env.value.lower():
            return env
    return None


def get_dose_rate_info(environment: RadiationEnvironment) -> Dict[str, Any]:
    """Get full dose rate information for an environment."""
    rate = DOSE_RATE_DATABASE.get(environment)
    if rate is None:
        return {}
    
    return {
        "environment": environment.value,
        "nominal_msv_per_day": rate.nominal_msv_per_day,
        "range_low_msv_per_day": rate.range_low_msv_per_day,
        "range_high_msv_per_day": rate.range_high_msv_per_day,
        "annual_dose_msv": rate.nominal_msv_per_day * 365.0,
        "eva_multiplier": rate.eva_multiplier,
        "solar_cycle_dependent": rate.solar_cycle_dependent,
        "reference": rate.reference,
        "notes": rate.notes,
    }


# =============================================================================
# GAUGE THRESHOLDS FOR VISUALIZATION
# =============================================================================

def get_radiation_gauge_thresholds(
    career_limit_msv: float = 600.0,
) -> Dict[str, Any]:
    """Get threshold values for radiation exposure ![1766925665221](image/radiation_exposure/1766925665221.png)s.
    
    Returns:
        Dict with keys: thresholds (list), colors (list), labels (list).
    """
    return {
        "thresholds": [
            0.0,
            career_limit_msv * 0.30,  # 30% = Green/GO
            career_limit_msv * 0.60,  # 60% = Yellow/MONITOR
            career_limit_msv * 0.80,  # 80% = Orange/CAUTION
            career_limit_msv,  # 100% = Red/NO-GO
            career_limit_msv * 1.20,  # Overage
        ],
        "colors": [
            "#28a745",  # Green: 0-30%
            "#ffc107",  # Yellow: 30-60%
            "#fd7e14",  # Orange: 60-80%
            "#dc3545",  # Red: 80-100%
            "#6f42c1",  # Purple: overage (shouldn't happen)
        ],
        "labels": [
            "GO",
            "MONITOR",
            "CAUTION",
            "NO-GO",
            "OVER LIMIT",
        ],
        "zone_descriptions": [
            "Nominal exposure. EVA cleared.",
            "Elevated exposure. Active monitoring required.",
            "High exposure. Limit additional EVA.",
            "Near limit. No additional EVA without waiver.",
            "Career limit exceeded. Medical review required.",
        ],
    }


def cumulative_to_status(
    cumulative_msv: float,
    career_limit_msv: float = 600.0,
) -> Tuple[EVARadiationStatus, str, str]:
    """Map cumulative dose to EVA status, color, and label.
    
    Returns:
        Tuple of (status, hex_color, label).
    """
    pct = (cumulative_msv / career_limit_msv) * 100.0
    
    if pct < 30.0:
        return EVARadiationStatus.GO, "#28a745", "GO"
    elif pct < 60.0:
        return EVARadiationStatus.GO_WITH_MONITORING, "#ffc107", "MONITOR"
    elif pct < 80.0:
        return EVARadiationStatus.CAUTION, "#fd7e14", "CAUTION"
    else:
        return EVARadiationStatus.NO_GO, "#dc3545", "NO-GO"


# =============================================================================
# REAL-TIME SPACE WEATHER DATA FETCHING
# =============================================================================

@dataclass(slots=True)
class RealTimeSpaceWeatherData:
    """Real-time space weather data from NOAA/NASA sources."""
    
    # Data source indicators
    data_source: str  # "NOAA", "SpaceWeatherLive", "DONKI", "Manual"
    fetch_timestamp: Optional[datetime] = None
    is_real_time: bool = True
    
    # Space weather parameters
    kp_index: Optional[float] = None
    kp_forecast: List[Dict[str, Any]] = field(default_factory=list)
    proton_flux_pfu: Optional[float] = None  # >10 MeV proton flux
    solar_wind_speed_kms: Optional[float] = None
    solar_wind_density_pcc: Optional[float] = None
    imf_bt_nt: Optional[float] = None
    imf_bz_nt: Optional[float] = None
    
    # NOAA scales
    s_scale: int = 0  # Radiation storm scale (0-5)
    g_scale: int = 0  # Geomagnetic storm scale (0-5)
    
    # Flare probabilities
    c_class_flare_prob: Optional[float] = None
    m_class_flare_prob: Optional[float] = None
    x_class_flare_prob: Optional[float] = None
    
    # CME information
    active_cmes: List[Dict[str, Any]] = field(default_factory=list)
    
    # Solar activity
    sunspot_number: Optional[int] = None
    f107_flux: Optional[float] = None
    
    # Error information
    fetch_error: Optional[str] = None
    is_stale: bool = False


def fetch_realtime_space_weather(
    environment: RadiationEnvironment,
    use_noaa: bool = True,
    use_spaceweatherlive: bool = True,
    timeout_seconds: float = 10.0,
) -> RealTimeSpaceWeatherData:
    """
    Fetch real-time space weather data for a specific mission environment.
    
    Args:
        environment: Mission radiation environment
        use_noaa: Attempt to fetch from NOAA SWPC
        use_spaceweatherlive: Attempt to fetch from SpaceWeatherLive
        timeout_seconds: Request timeout
        
    Returns:
        RealTimeSpaceWeatherData with fetched or default values
    """
    data = RealTimeSpaceWeatherData(
        data_source="Manual",
        is_real_time=False,
        fetch_timestamp=datetime.now(timezone.utc),
    )
    
    # Try NOAA first (best for ISS/LEO)
    if use_noaa:
        try:
            from noaa_space import load_noaa_space_cache
            
            bundles, errors = load_noaa_space_cache()
            
            # Extract Kp index
            if "kp_1min" in bundles:
                kp_df = bundles["kp_1min"]
                if not kp_df.empty and "kp" in kp_df.columns:
                    latest_kp = kp_df["kp"].iloc[-1]
                    if pd.notna(latest_kp):
                        data.kp_index = float(latest_kp)
                        data.data_source = "NOAA"
                        data.is_real_time = True
            
            # Extract proton flux
            if "proton_integral" in bundles:
                proton_df = bundles["proton_integral"]
                if not proton_df.empty:
                    # Look for >10 MeV protons
                    for col in proton_df.columns:
                        if "10mev" in col.lower() or "10_mev" in col.lower():
                            latest_flux = proton_df[col].iloc[-1]
                            if pd.notna(latest_flux) and latest_flux > 0:
                                data.proton_flux_pfu = float(latest_flux)
                                break
                    
                    # Calculate S-scale from proton flux
                    if data.proton_flux_pfu is not None:
                        if data.proton_flux_pfu >= 10000:
                            data.s_scale = 5
                        elif data.proton_flux_pfu >= 1000:
                            data.s_scale = 4
                        elif data.proton_flux_pfu >= 100:
                            data.s_scale = 3
                        elif data.proton_flux_pfu >= 10:
                            data.s_scale = 2
                        elif data.proton_flux_pfu >= 1:
                            data.s_scale = 1
                        else:
                            data.s_scale = 0
            
            # Calculate G-scale from Kp
            if data.kp_index is not None:
                if data.kp_index >= 9.0:
                    data.g_scale = 5
                elif data.kp_index >= 8.0:
                    data.g_scale = 4
                elif data.kp_index >= 7.0:
                    data.g_scale = 3
                elif data.kp_index >= 6.0:
                    data.g_scale = 2
                elif data.kp_index >= 5.0:
                    data.g_scale = 1
                else:
                    data.g_scale = 0
            
        except Exception as e:
            data.fetch_error = f"NOAA fetch error: {str(e)}"
    
    # Try SpaceWeatherLive for additional data (works for all environments)
    if use_spaceweatherlive:
        try:
            from spaceweatherlive_client import fetch_spaceweatherlive_snapshot
            
            snapshot = fetch_spaceweatherlive_snapshot(timeout_s=timeout_seconds)
            
            # Update with SpaceWeatherLive data (prefer if NOAA unavailable)
            if data.data_source == "Manual" or data.kp_index is None:
                # Use Kp forecast if available
                if snapshot.kp_forecast:
                    latest_forecast = snapshot.kp_forecast[0]
                    if latest_forecast.max_kp is not None:
                        data.kp_index = latest_forecast.max_kp
                        data.data_source = "SpaceWeatherLive"
                        data.is_real_time = True
                
                # Update G-scale from Kp
                if data.kp_index is not None:
                    if data.kp_index >= 9.0:
                        data.g_scale = 5
                    elif data.kp_index >= 8.0:
                        data.g_scale = 4
                    elif data.kp_index >= 7.0:
                        data.g_scale = 3
                    elif data.kp_index >= 6.0:
                        data.g_scale = 2
                    elif data.kp_index >= 5.0:
                        data.g_scale = 1
                    else:
                        data.g_scale = 0
            
            # Solar wind parameters
            if snapshot.solar_wind_speed_kms is not None:
                data.solar_wind_speed_kms = snapshot.solar_wind_speed_kms
            if snapshot.solar_wind_density_pcc is not None:
                data.solar_wind_density_pcc = snapshot.solar_wind_density_pcc
            if snapshot.imf_bt_nt is not None:
                data.imf_bt_nt = snapshot.imf_bt_nt
            if snapshot.imf_bz_nt is not None:
                data.imf_bz_nt = snapshot.imf_bz_nt
            
            # Flare probabilities
            if snapshot.flare_probabilities.c_class_pct is not None:
                data.c_class_flare_prob = snapshot.flare_probabilities.c_class_pct
            if snapshot.flare_probabilities.m_class_pct is not None:
                data.m_class_flare_prob = snapshot.flare_probabilities.m_class_pct
            if snapshot.flare_probabilities.x_class_pct is not None:
                data.x_class_flare_prob = snapshot.flare_probabilities.x_class_pct
            
            # Solar activity
            if snapshot.sunspot_number is not None:
                data.sunspot_number = snapshot.sunspot_number
            if snapshot.f107_flux is not None:
                data.f107_flux = snapshot.f107_flux
            
            # CME records
            if snapshot.cme_records:
                data.active_cmes = [
                    {
                        "cactus_id": cme.cactus_id,
                        "onset_time": cme.onset_time_utc.isoformat() if cme.onset_time_utc else None,
                        "velocity_kms": cme.velocity_kms,
                        "halo": cme.halo_class,
                    }
                    for cme in snapshot.cme_records[:5]  # Top 5 most recent
                ]
            
            # Kp forecast
            if snapshot.kp_forecast:
                data.kp_forecast = [
                    {"day": k.day_label, "min_kp": k.min_kp, "max_kp": k.max_kp}
                    for k in snapshot.kp_forecast
                ]
            
        except Exception as e:
            if data.fetch_error:
                data.fetch_error += f"; SpaceWeatherLive error: {str(e)}"
            else:
                data.fetch_error = f"SpaceWeatherLive fetch error: {str(e)}"
    
    # Set fetch timestamp
    data.fetch_timestamp = datetime.now(timezone.utc)
    
    return data


def get_environment_display_name(environment: RadiationEnvironment) -> str:
    """Get human-readable display name for radiation environment."""
    names = {
        RadiationEnvironment.LEO_ISS: "Low Earth Orbit (ISS)",
        RadiationEnvironment.TRANSLUNAR_INJECTION: "Translunar Injection (TLI)",
        RadiationEnvironment.LUNAR_GATEWAY: "Lunar Gateway",
        RadiationEnvironment.LUNAR_SURFACE_NOMINAL: "Lunar Surface",
        RadiationEnvironment.TRANS_MARTIAN_INJECTION: "Trans-Martian Injection (TMI)",
        RadiationEnvironment.MARS_ORBIT: "Martian Orbit",
        RadiationEnvironment.MARS_SURFACE: "Martian Surface",
    }
    return names.get(environment, environment.value.replace("_", " ").title())


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "RadiationEnvironment",
    "RadiationDoseRate",
    "DOSE_RATE_DATABASE",
    "RadiationLimits",
    "NASA_RADIATION_LIMITS",
    "EVARadiationStatus",
    "EVARadiationAssessment",
    "assess_eva_radiation_risk",
    "DailyRadiationExposure",
    "build_radiation_timeline",
    "timeline_to_dataframe",
    "compare_environments",
    "get_environment_by_name",
    "get_dose_rate_info",
    "get_radiation_gauge_thresholds",
    "cumulative_to_status",
    "RealTimeSpaceWeatherData",
    "fetch_realtime_space_weather",
    "get_environment_display_name",
]

