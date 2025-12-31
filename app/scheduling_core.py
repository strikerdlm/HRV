"""
Crew Scheduling and Human Performance Management - Core Science Layer.

This module implements evidence-based scoring functions for crew scheduling,
performance prediction, and GO/NO-GO decision support following:
- SAFTE-FAST validation evidence (U.S. Senate testimony & military aviation studies)
- NASA Human Performance standards (VO2max ≥32.9 ml/kg/min for EVA)
- IOC Energy Availability thresholds (RED-S consensus)
- Task Force ESC/NASPE HRV standards

Scientific References (with DOI/PMID for verification):
─────────────────────────────────────────────────────────────────────────────
FATIGUE MODELS:
  • Hursh SR, Redmond DP, Johnson ML, et al. (2004). Fatigue models for applied
    research in warfighting. Aviat Space Environ Med. 75(3 Suppl):A44-53.
    PMID: 15018265
    → SAFTE effectiveness thresholds: ≥90% low-risk, ≤70% ~0.08 BAC equivalence

  • Paul MA, Hursh SR, Love R. (2020). Validating Sleep Behavior Models for
    Fatigue Management Software in Military Aviation. Mil Med. 185(11-12):e1986.
    DOI: 10.1093/milmed/usaa210
    → SAFTE-FAST harmonization in Canadian Air Force

HRV & RECOVERY:
  • Task Force ESC/NASPE. (1996). Heart rate variability: standards of
    measurement, physiological interpretation and clinical use.
    Eur Heart J. 17:354-381. DOI: 10.1093/oxfordjournals.eurheartj.a014868
    → 5-min short-term HRV standards, RMSSD for vagal tone

  • Plews DJ, Laursen PB, Stanley J, Kilding AE, Buchheit M. (2013). Training
    adaptation and heart rate variability in elite endurance athletes.
    Sports Med. 43(9):773-781. DOI: 10.1007/s40279-013-0071-8
    → lnRMSSD z-score with 14-28 day rolling baseline

ENERGY AVAILABILITY:
  • Mountjoy M, et al. (2018). IOC Consensus Statement on RED-S: 2018 Update.
    Br J Sports Med. 52(11):687-697. DOI: 10.1136/bjsports-2018-099193
    → EA thresholds: ≥45 optimal, <30 kcal/kg FFM/day low

  • Mountjoy M, et al. (2023). 2023 IOC Consensus Statement on REDs.
    Br J Sports Med. 57(17):1073-1097. DOI: 10.1136/bjsports-2023-106994
    → Updated REDs Clinical Assessment Tool V2

VIGILANCE & SLEEPINESS:
  • Basner M, Dinges DF. (2011). Maximizing sensitivity of the PVT to sleep loss.
    Sleep. 34(5):581-591. DOI: 10.1093/sleep/34.5.581
    → 3-min PVT, 355ms lapse threshold

  • Åkerstedt T, Gillberg M. (1990). Subjective and objective sleepiness.
    Int J Neurosci. 52(1-2):29-37. DOI: 10.3109/00207459008994241
    → KSS validation: 1-5 alert, 8-9 severe

EVA PHYSIOLOGY & NASA STANDARDS:
  • NASA-STD-3001 Vol 1 Rev B. (2022). Human Performance Capabilities.
    → EVA VO₂max requirement: ≥32.9 ml/kg/min

  • Waligora JM, Kumar KV. (1995). Energy utilization rates during shuttle EVA.
    NASA NTRS. PMID: 11540993
    → Shuttle EVA: 194 kcal/hr; Skylab EVA: 238 kcal/hr

METABOLIC EQUIVALENTS:
  • Ainsworth BE, et al. (2024). 2024 Compendium of Physical Activities.
    Med Sci Sports Exerc. 56(Suppl):S1-152. DOI: 10.1249/MSS.0000000000003356
    → Standardized MET values for 800+ activities

HYDRATION:
  • Armstrong LE, et al. (2007). ACSM position stand: Exertional heat illness.
    Med Sci Sports Exerc. 39(3):556-572. DOI: 10.1249/mss.0b013e31802fa199
    → >2% body mass loss impairs cognition; USG ≥1.030 significant dehydration

CIRCADIAN & CREW REST:
  • ICAO Doc 9966. (2016). Manual for Oversight of Fatigue Management.
    → Phase misalignment >6h severely degrades performance

  • AFMAN 11-202V3. (2022). General Flight Rules.
    → Military crew rest requirements
─────────────────────────────────────────────────────────────────────────────

Author: Dr. Diego Leonel Malpica Hincapié, MD
Version: 1.1.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Final, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Constants and Enums
# ---------------------------------------------------------------------------

# NASA EVA Requirements
NASA_EVA_VO2MAX_MIN_ML_KG_MIN: Final[float] = 32.9  # ml/kg/min
NASA_EVA_MIN_RECOVERY_HOURS: Final[float] = 48.0  # Optimal
NASA_EVA_ABSOLUTE_MIN_RECOVERY_HOURS: Final[float] = 24.0  # With FS approval
NASA_EVA_EXTRA_KCAL_PER_HOUR: Final[float] = 200.0  # Nutritional planning

# SAFTE Effectiveness Thresholds (validated)
SAFTE_LOW_RISK_MIN: Final[float] = 90.0  # Low-risk zone
SAFTE_CAUTION_MIN: Final[float] = 80.0  # Elevated accident risk
SAFTE_HIGH_RISK_MIN: Final[float] = 70.0  # Significant degradation
SAFTE_CRITICAL_THRESHOLD: Final[float] = 70.0  # ~0.08 BAC equivalence

# Time awake thresholds
MAX_TIME_AWAKE_HOURS: Final[float] = 21.0  # Very high risk

# Sleep thresholds
MIN_SLEEP_24H_HOURS: Final[float] = 6.0  # Hard NO-GO
MIN_SLEEP_24H_CONSERVATIVE: Final[float] = 7.0  # Conservative

# Hydration thresholds (USG)
USG_EUHYDRATED_MAX: Final[float] = 1.020
USG_HYPOHYDRATED_MAX: Final[float] = 1.029
USG_SIGNIFICANT_HYPOHYDRATION: Final[float] = 1.030

# Body mass loss threshold
MAX_BODY_MASS_LOSS_PCT: Final[float] = 2.0

# Energy Availability thresholds (IOC)
EA_OPTIMAL_KCAL_KG_FFM: Final[float] = 45.0
EA_LOW_THRESHOLD_KCAL_KG_FFM: Final[float] = 30.0

# PVT thresholds (3-min protocol, 355ms lapse)
PVT_HIGH_PERFORMANCE_MAX_LAPSES: Final[int] = 10
PVT_LOW_PERFORMANCE_MIN_LAPSES: Final[int] = 20

# KSS thresholds
KSS_NORMAL_MAX: Final[int] = 5
KSS_CAUTION_MAX: Final[int] = 7
KSS_NOGO_MIN: Final[int] = 8

# ---------------------------------------------------------------------------
# Space Radiation Exposure Limits (NASA-STD-3001 Vol 1 Rev B)
# References:
#   - NASA-STD-3001 Vol 1 Rev B (2022): Human Spaceflight Occupant Safety
#     https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf
#   - National Academies (2021): Space Radiation and Astronaut Health
#     https://nap.nationalacademies.org/read/26155/chapter/5
#   - Cucinotta FA (2014): Space Radiation Cancer Risk Projections
#     https://three.jsc.nasa.gov/articles/astronautradlimitsfc.pdf
# ---------------------------------------------------------------------------

# Career dose limit (effective dose, mSv) - NASA-STD-3001 Vol 1 Rev B
NASA_CAREER_DOSE_LIMIT_MSV: Final[float] = 600.0  # 600 mSv career limit (2022 update)

# Annual dose limit for radiation workers
ANNUAL_DOSE_LIMIT_MSV: Final[float] = 50.0  # 50 mSv/year occupational limit

# 30-day dose limit (blood-forming organs)
THIRTY_DAY_BFO_LIMIT_MSV: Final[float] = 250.0  # Gray-equivalent

# EVA-specific limits (short-term exposure)
EVA_DOSE_LIMIT_MSV_PER_HOUR: Final[float] = 0.5  # ~0.5 mSv/hr in LEO EVA

# Solar Particle Event (SPE) alert thresholds
SPE_ALERT_THRESHOLD_PFU: Final[float] = 10.0  # >10 pfu = enhanced radiation
SPE_WARNING_THRESHOLD_PFU: Final[float] = 100.0  # >100 pfu = significant event
SPE_STORM_THRESHOLD_PFU: Final[float] = 1000.0  # >1000 pfu = major storm

# Galactic Cosmic Ray (GCR) baseline dose rate (mSv/day in LEO)
GCR_BASELINE_DOSE_RATE_MSV_DAY: Final[float] = 0.5  # ~0.5 mSv/day average

# Radiation risk levels for EVA GO/NO-GO
class RadiationRiskLevel(str, Enum):
    """Radiation risk level for EVA scheduling."""
    LOW = "low"  # Normal GCR, no SPE activity
    MODERATE = "moderate"  # Elevated GCR or minor SPE
    HIGH = "high"  # Active SPE, avoid EVA
    CRITICAL = "critical"  # Major SPE/storm, shelter required


# ---------------------------------------------------------------------------
# NASA Scheduling Factors and Constraints
# Based on: NASA-STD-3001 Vol 1/2, SPIFe/Playbook Planning Tools, ISS Operations
# References:
#   - NASA-STD-3001 Vol 2 Rev D: Human Factors, Habitability, Environmental Health
#     https://standards.nasa.gov/standard/NASA/NASA-STD-3001_VOL_2
#   - NASA OCHMO Cognitive Workload Technical Brief (2023)
#     https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-032-cognitive-workload.pdf
#   - NASA NTRS 20190027148: ISS Crew Autonomous Scheduling Test
#     https://ntrs.nasa.gov/citations/20190027148
#   - Playbook/SPIFe Planning Tools: https://hci.arc.nasa.gov/work/playbook.html
# ---------------------------------------------------------------------------

# Workday limits (NASA-STD-3001, ISS Operations)
NOMINAL_WORKDAY_HOURS: Final[float] = 8.5  # Nominal duty hours
MAX_WORKDAY_HOURS: Final[float] = 10.0  # Maximum recommended
EXTENDED_WORKDAY_HOURS: Final[float] = 12.0  # Only for critical ops

# Rest requirements
MIN_REST_BETWEEN_WORKDAYS_HOURS: Final[float] = 8.0  # Minimum rest
RECOMMENDED_SLEEP_HOURS: Final[float] = 8.0  # Optimal sleep
MIN_SLEEP_HOURS: Final[float] = 6.0  # Absolute minimum

# Task scheduling constraints (SPIFe/Playbook derived)
MAX_CONTINUOUS_WORK_HOURS: Final[float] = 2.0  # Before mandatory break
MANDATORY_BREAK_MINUTES: Final[int] = 15  # After continuous work
MEAL_DURATION_MINUTES: Final[int] = 45  # Protected meal time
BRIEFING_DURATION_MINUTES: Final[int] = 60  # Daily planning conference

# Cognitive workload factors (NASA-STD-3001 Vol 2, Bedford Scale)
# Bedford Scale: 1-3 = satisfactory, 4-6 = tolerable, 7-9 = unacceptable
COGNITIVE_WORKLOAD_LOW: Final[float] = 3.0  # Routine tasks
COGNITIVE_WORKLOAD_MEDIUM: Final[float] = 5.0  # Complex science/ops
COGNITIVE_WORKLOAD_HIGH: Final[float] = 7.0  # EVA, emergency procedures

# Physical workload factors (Borg CR-10 Scale)
# Borg CR-10: 0 = nothing, 4 = somewhat strong, 10 = maximal
PHYSICAL_WORKLOAD_TARGET: Final[float] = 4.0  # NASA-STD-3001 requirement

# Activity scheduling rules (ISS Operations)
@dataclass(frozen=True, slots=True)
class SchedulingConstraint:
    """Constraint definition for activity scheduling."""
    name: str
    description: str
    constraint_type: str  # "temporal", "resource", "spatial", "crew"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    required: bool = True

# Standard ISS scheduling constraints
ISS_SCHEDULING_CONSTRAINTS: Tuple[SchedulingConstraint, ...] = (
    # Temporal constraints
    SchedulingConstraint(
        name="workday_hours",
        description="Total duty hours per day",
        constraint_type="temporal",
        min_value=6.0,
        max_value=10.0,
        required=True,
    ),
    SchedulingConstraint(
        name="continuous_work",
        description="Maximum continuous work before break",
        constraint_type="temporal",
        max_value=2.0,
        required=True,
    ),
    SchedulingConstraint(
        name="sleep_period",
        description="Minimum sleep period hours",
        constraint_type="temporal",
        min_value=6.0,
        required=True,
    ),
    SchedulingConstraint(
        name="meal_window",
        description="Protected meal time minutes",
        constraint_type="temporal",
        min_value=30.0,
        max_value=60.0,
        required=True,
    ),
    # Resource constraints
    SchedulingConstraint(
        name="exercise_equipment",
        description="Exercise equipment capacity",
        constraint_type="resource",
        max_value=1.0,
        required=True,
    ),
    SchedulingConstraint(
        name="hygiene_module",
        description="Hygiene module capacity",
        constraint_type="resource",
        max_value=1.0,
        required=True,
    ),
    # Crew constraints
    SchedulingConstraint(
        name="eva_crew",
        description="Maximum crew on EVA simultaneously",
        constraint_type="crew",
        max_value=2.0,
        required=True,
    ),
    SchedulingConstraint(
        name="eva_recovery",
        description="Hours between EVAs for same crew",
        constraint_type="crew",
        min_value=24.0,
        required=True,
    ),
)

# Activity priority levels (ISS Flight Rules derived)
# Lower number = higher priority
PRIORITY_EMERGENCY: Final[int] = 1  # Life-threatening situations
PRIORITY_SAFETY_CRITICAL: Final[int] = 2  # Safety-related activities
PRIORITY_MISSION_CRITICAL: Final[int] = 3  # EVA, critical experiments
PRIORITY_HEALTH_MAINTENANCE: Final[int] = 4  # Exercise, medical
PRIORITY_ROUTINE_OPS: Final[int] = 5  # Nominal operations
PRIORITY_DISCRETIONARY: Final[int] = 6  # Crew preference activities

# Task categorization for workload balancing
# Based on NASA Flight Planning Branch procedures
@dataclass(frozen=True, slots=True)
class TaskCategory:
    """Task category for workload distribution."""
    name: str
    cognitive_load: float  # 1-9 Bedford scale
    physical_load: float  # 0-10 Borg CR-10
    min_crew_proficiency: str  # "basic", "trained", "expert"
    parallel_allowed: bool  # Can be done alongside other tasks


TASK_CATEGORIES: Dict[str, TaskCategory] = {
    "briefing": TaskCategory("Morning Briefing", 3.0, 1.0, "basic", False),
    "meal": TaskCategory("Meal", 1.0, 1.5, "basic", True),
    "exercise": TaskCategory("Physical Exercise", 2.0, 6.0, "trained", False),
    "hygiene": TaskCategory("Personal Hygiene", 1.0, 2.0, "basic", False),
    "sleep": TaskCategory("Sleep", 1.0, 1.0, "basic", False),
    "science_routine": TaskCategory("Routine Science", 4.0, 2.0, "trained", True),
    "science_complex": TaskCategory("Complex Science", 6.0, 2.5, "expert", False),
    "eva_prep": TaskCategory("EVA Preparation", 6.0, 4.0, "expert", False),
    "eva": TaskCategory("EVA Operations", 8.0, 7.0, "expert", False),
    "maintenance": TaskCategory("Station Maintenance", 5.0, 4.0, "trained", True),
    "recreation": TaskCategory("Recreation", 2.0, 2.0, "basic", True),
    "emergency": TaskCategory("Emergency Procedures", 9.0, 6.0, "trained", False),
}


class ActivityCategory(str, Enum):
    """Activity categories for scheduling."""
    FIXED = "fixed"  # Briefing, meals, sleep
    VARIABLE = "variable"  # Lab work, EVA
    RESOURCE_LIMITED = "resource_limited"  # Exercise (capacity constraint)
    INDIVIDUAL = "individual"  # Recreation, hygiene


class RiskLevel(str, Enum):
    """Risk level classifications."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class GONOGOStatus(str, Enum):
    """GO/NO-GO decision status."""
    GO = "go"
    GO_WITH_MITIGATION = "go_with_mitigation"
    HOLD = "hold"
    NOGO = "nogo"


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp value to [lo, hi] range."""
    return max(lo, min(hi, x))


# ---------------------------------------------------------------------------
# MET / Energy Conversions
# ---------------------------------------------------------------------------

def kcal_per_hour_from_met(met: float, mass_kg: float) -> float:
    """
    Convert MET to kcal/hour.
    
    1 MET ≈ 1 kcal/kg/hour (by definition).
    
    Args:
        met: Metabolic Equivalent of Task
        mass_kg: Body mass in kilograms
        
    Returns:
        Energy expenditure in kcal/hour
    """
    return met * mass_kg


def watts_from_kcal_per_hour(kcal_h: float) -> float:
    """
    Convert kcal/hr to Watts.
    
    1 kcal = 4184 J; 1 hour = 3600 s
    Power (W) = (kcal/hr × 4184) / 3600
    
    Args:
        kcal_h: Energy rate in kcal/hour
        
    Returns:
        Power in Watts
    """
    return kcal_h * 4184.0 / 3600.0


def kcal_from_met_duration(met: float, mass_kg: float, minutes: float) -> float:
    """
    Calculate total kcal from MET value and duration.
    
    Args:
        met: Metabolic Equivalent of Task
        mass_kg: Body mass in kilograms
        minutes: Duration in minutes
        
    Returns:
        Total energy expenditure in kcal
    """
    return kcal_per_hour_from_met(met, mass_kg) * (minutes / 60.0)


# ---------------------------------------------------------------------------
# Subscore Mappers (0..1 scale)
# ---------------------------------------------------------------------------

def score_safte(effectiveness_0_100: float) -> float:
    """
    Map SAFTE effectiveness (0-100%) to subscore (0-1).
    
    Anchors (from validated U.S. Senate testimony):
    - ≥90: Low risk zone (accident risk elevated below 90)
    - ≤70: High risk zone (roughly 0.08 BAC / ~21h awake equivalence)
    
    Args:
        effectiveness_0_100: SAFTE effectiveness percentage (0-100)
        
    Returns:
        Normalized score (0-1)
    """
    e = effectiveness_0_100
    if e >= SAFTE_LOW_RISK_MIN:
        return 1.0
    if e <= SAFTE_HIGH_RISK_MIN:
        return 0.0
    # Linear ramp 70→90 maps to 0→1
    return (e - SAFTE_HIGH_RISK_MIN) / 20.0


def score_kss(kss_1_9: float) -> float:
    """
    Map Karolinska Sleepiness Scale (1-9) to subscore (0-1).
    
    Interpretation:
    - 1-5: Good (normal alertness)
    - 6-7: Caution (some sleepiness)
    - 8-9: NO-GO (severe sleepiness)
    
    Args:
        kss_1_9: KSS score (1-9)
        
    Returns:
        Normalized score (0-1)
    """
    k = kss_1_9
    if k <= KSS_NORMAL_MAX:
        return 1.0
    if k >= KSS_NOGO_MIN:
        return 0.0
    # Map 5→8 down to 1→0
    return 1.0 - (k - KSS_NORMAL_MAX) / 3.0


def score_pvt_lapses_3min(lapses: int) -> float:
    """
    Map 3-minute PVT lapse count to subscore (0-1).
    
    Operational anchors (355ms lapse threshold):
    - ≤10 lapses: High-performance band
    - ≥20 lapses: Low-performance band
    
    Args:
        lapses: Number of lapses (RT > 355ms) in 3-min PVT
        
    Returns:
        Normalized score (0-1)
    """
    if lapses <= PVT_HIGH_PERFORMANCE_MAX_LAPSES:
        return 1.0
    if lapses >= PVT_LOW_PERFORMANCE_MIN_LAPSES:
        return 0.0
    return 1.0 - (lapses - PVT_HIGH_PERFORMANCE_MAX_LAPSES) / 10.0


def score_hrv_z(z_lnrmssd: float) -> float:
    """
    Map lnRMSSD z-score to subscore (0-1).
    
    Conservative readiness mapping based on HRV literature:
    - z ≥ -0.5: Normal (Green)
    - z = -0.5 to -1.5: Caution (Yellow)
    - z < -1.5: High risk (Red)
    
    Args:
        z_lnrmssd: lnRMSSD z-score (current - baseline_mean) / baseline_SD
        
    Returns:
        Normalized score (0-1)
    """
    if z_lnrmssd >= -0.5:
        return 1.0
    if z_lnrmssd <= -2.0:
        return 0.0
    # -0.5 → -2.0 maps 1 → 0
    return 1.0 - (abs(z_lnrmssd) - 0.5) / 1.5


def score_hydration(body_mass_change_pct: float, usg: Optional[float]) -> float:
    """
    Map hydration status to subscore (0-1).
    
    Uses both body mass change and Urine Specific Gravity (conservative = min).
    
    Args:
        body_mass_change_pct: Percentage change (negative = loss, e.g., -1.5 for 1.5% loss)
        usg: Urine Specific Gravity (optional)
        
    Returns:
        Normalized score (0-1)
    """
    # Convert to positive "loss %"
    loss = -body_mass_change_pct
    
    # Body mass: 0% loss best, >2% problematic
    if loss <= 0.5:
        bm = 1.0
    elif loss >= MAX_BODY_MASS_LOSS_PCT:
        bm = 0.0
    else:
        bm = 1.0 - (loss - 0.5) / 1.5  # 0.5 → 2.0

    if usg is None:
        return bm

    # USG: <1.020 euhydrated; >=1.030 significant hypohydration
    if usg < USG_EUHYDRATED_MAX:
        u = 1.0
    elif usg >= USG_SIGNIFICANT_HYPOHYDRATION:
        u = 0.0
    else:
        u = 1.0 - (usg - USG_EUHYDRATED_MAX) / 0.010  # 1.020 → 1.030

    # Conservative: use minimum
    return min(bm, u)


def score_energy_availability(ea_kcal_per_kg_ffm_day: float) -> float:
    """
    Map Energy Availability to subscore (0-1).
    
    IOC-style anchors:
    - ≥45: Optimal
    - <30: Low EA threshold (system perturbations expected)
    
    Args:
        ea_kcal_per_kg_ffm_day: Energy Availability in kcal/kg FFM/day
        
    Returns:
        Normalized score (0-1)
    """
    ea = ea_kcal_per_kg_ffm_day
    if ea >= EA_OPTIMAL_KCAL_KG_FFM:
        return 1.0
    if ea <= EA_LOW_THRESHOLD_KCAL_KG_FFM:
        return 0.0
    return (ea - EA_LOW_THRESHOLD_KCAL_KG_FFM) / 15.0


def score_circadian_alignment(phase_offset_hours: float) -> float:
    """
    Map circadian alignment to subscore (0-1).
    
    Phase offset = absolute difference between scheduled sleep midpoint
    and chronotype sleep midpoint.
    
    Args:
        phase_offset_hours: Absolute phase offset in hours
        
    Returns:
        Normalized score (0-1)
    """
    d = abs(phase_offset_hours)
    if d <= 1.0:
        return 1.0
    if d >= 6.0:
        return 0.0
    return 1.0 - (d - 1.0) / 5.0


def score_task_specific(
    vo2max_ml_min_kg: float,
    hours_since_last_eva: float,
) -> float:
    """
    Map task-specific readiness to subscore (0-1).
    
    Args:
        vo2max_ml_min_kg: VO2max in ml/min/kg
        hours_since_last_eva: Hours since last EVA
        
    Returns:
        Normalized score (0-1)
    """
    # NASA EVA requirement: VO2max ≥ 32.9 ml/min/kg
    vo2_ok = 1.0 if vo2max_ml_min_kg >= NASA_EVA_VO2MAX_MIN_ML_KG_MIN else 0.0

    # Recovery: <24h bad, ≥48h good
    if hours_since_last_eva >= NASA_EVA_MIN_RECOVERY_HOURS:
        rec = 1.0
    elif hours_since_last_eva <= NASA_EVA_ABSOLUTE_MIN_RECOVERY_HOURS:
        rec = 0.0
    else:
        rec = (hours_since_last_eva - NASA_EVA_ABSOLUTE_MIN_RECOVERY_HOURS) / 24.0

    return min(vo2_ok, rec)


# ---------------------------------------------------------------------------
# IHPI Composite Score
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class IHPISubscores:
    """Subscores for Integrated Human Performance Indicator calculation."""
    safte: float
    pvt: float
    circadian: float
    hrv: float
    hydration: float
    energy_availability: float
    subjective: float  # KSS + Samn-Perelli combined
    task_specific: float


# Default IHPI weights (science-revised)
DEFAULT_IHPI_WEIGHTS: Dict[str, float] = {
    "safte": 0.30,
    "pvt": 0.20,
    "circadian": 0.10,
    "hrv": 0.10,
    "hydration": 0.10,
    "energy_availability": 0.10,
    "subjective": 0.05,
    "task_specific": 0.05,
}


def compute_ihpi(
    sub: IHPISubscores,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Compute Integrated Human Performance Indicator (0-100).
    
    Includes hard-cap gating: if any critical domain (SAFTE, hydration,
    PVT, subjective) is 0, the final score is capped at 0.
    
    Args:
        sub: Subscores dataclass
        weights: Optional custom weights (default: science-revised weights)
        
    Returns:
        IHPI score (0-100)
    """
    w = weights if weights is not None else DEFAULT_IHPI_WEIGHTS
    
    # Hard-cap logic: if any critical domain is 0, cap score hard
    critical_floor = min(sub.safte, sub.hydration, sub.pvt, sub.subjective)
    if critical_floor <= 0.0:
        return 0.0

    s = (
        w["safte"] * sub.safte +
        w["pvt"] * sub.pvt +
        w["circadian"] * sub.circadian +
        w["hrv"] * sub.hrv +
        w["hydration"] * sub.hydration +
        w["energy_availability"] * sub.energy_availability +
        w["subjective"] * sub.subjective +
        w["task_specific"] * sub.task_specific
    )
    return 100.0 * clamp(s, 0.0, 1.0)


# ---------------------------------------------------------------------------
# EVA GO/NO-GO Decision Logic
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EVAGONOGOResult:
    """Result of EVA GO/NO-GO decision."""
    status: GONOGOStatus
    reasons: Tuple[str, ...]
    ihpi_value: float
    safte_effectiveness: float
    all_gates_passed: bool


def eva_go_nogo(
    safte_eff: float,
    kss: float,
    sleep_last_24h_h: float,
    time_awake_h: float,
    body_mass_change_pct: float,
    usg: Optional[float],
    pvt_lapses_3min: int,
    ihpi_value: float,
    vo2max: float,
    hours_since_last_eva: float,
    energy_availability: float = EA_OPTIMAL_KCAL_KG_FFM,
) -> EVAGONOGOResult:
    """
    EVA GO/NO-GO decision with science-based gates.
    
    Implements guardrails-first approach: hard gates checked before IHPI.
    
    Args:
        safte_eff: SAFTE effectiveness (0-100%)
        kss: Karolinska Sleepiness Scale (1-9)
        sleep_last_24h_h: Hours of sleep in last 24 hours
        time_awake_h: Continuous hours awake
        body_mass_change_pct: Body mass change (negative = loss)
        usg: Urine Specific Gravity (optional)
        pvt_lapses_3min: 3-min PVT lapse count
        ihpi_value: Computed IHPI score (0-100)
        vo2max: VO2max in ml/kg/min
        hours_since_last_eva: Hours since last EVA
        energy_availability: EA in kcal/kg FFM/day
        
    Returns:
        EVAGONOGOResult with status, reasons, and metrics
    """
    reasons: List[str] = []
    all_gates_passed = True

    # Hard NO-GO gates
    if safte_eff < SAFTE_CRITICAL_THRESHOLD:
        reasons.append(f"SAFTE effectiveness < {SAFTE_CRITICAL_THRESHOLD}% (critical risk zone)")
        all_gates_passed = False
    if kss >= KSS_NOGO_MIN:
        reasons.append(f"KSS >= {KSS_NOGO_MIN} (severe sleepiness)")
        all_gates_passed = False
    if sleep_last_24h_h < MIN_SLEEP_24H_HOURS:
        reasons.append(f"Sleep < {MIN_SLEEP_24H_HOURS}h in last 24h")
        all_gates_passed = False
    if time_awake_h >= MAX_TIME_AWAKE_HOURS:
        reasons.append(f"Time awake >= {MAX_TIME_AWAKE_HOURS}h (very high risk)")
        all_gates_passed = False
    if (-body_mass_change_pct) > MAX_BODY_MASS_LOSS_PCT:
        reasons.append(f">{MAX_BODY_MASS_LOSS_PCT}% body mass loss (hypohydration)")
        all_gates_passed = False
    if usg is not None and usg >= USG_SIGNIFICANT_HYPOHYDRATION:
        reasons.append(f"USG >= {USG_SIGNIFICANT_HYPOHYDRATION} (significant hypohydration)")
        all_gates_passed = False
    if pvt_lapses_3min >= PVT_LOW_PERFORMANCE_MIN_LAPSES:
        reasons.append(f"3-min PVT lapses >= {PVT_LOW_PERFORMANCE_MIN_LAPSES} (low-performance)")
        all_gates_passed = False
    if vo2max < NASA_EVA_VO2MAX_MIN_ML_KG_MIN:
        reasons.append(f"VO2max < {NASA_EVA_VO2MAX_MIN_ML_KG_MIN} ml/kg/min (NASA EVA requirement)")
        all_gates_passed = False
    if hours_since_last_eva < NASA_EVA_ABSOLUTE_MIN_RECOVERY_HOURS:
        reasons.append(f"Time since last EVA < {NASA_EVA_ABSOLUTE_MIN_RECOVERY_HOURS}h (minimum recovery)")
        all_gates_passed = False
    if energy_availability < EA_LOW_THRESHOLD_KCAL_KG_FFM:
        reasons.append(f"Energy Availability < {EA_LOW_THRESHOLD_KCAL_KG_FFM} kcal/kg FFM/day (low EA)")
        all_gates_passed = False

    if not all_gates_passed:
        return EVAGONOGOResult(
            status=GONOGOStatus.NOGO,
            reasons=tuple(reasons),
            ihpi_value=ihpi_value,
            safte_effectiveness=safte_eff,
            all_gates_passed=False,
        )

    # Balanced ops gate: SAFTE >= 80
    if safte_eff < SAFTE_CAUTION_MIN:
        reasons.append(f"SAFTE effectiveness {SAFTE_HIGH_RISK_MIN}-{SAFTE_CAUTION_MIN}% (high-risk zone)")
        return EVAGONOGOResult(
            status=GONOGOStatus.HOLD,
            reasons=tuple(reasons),
            ihpi_value=ihpi_value,
            safte_effectiveness=safte_eff,
            all_gates_passed=True,
        )

    # IHPI-based final decision
    if ihpi_value >= 85:
        return EVAGONOGOResult(
            status=GONOGOStatus.GO,
            reasons=("All gates passed; IHPI >= 85",),
            ihpi_value=ihpi_value,
            safte_effectiveness=safte_eff,
            all_gates_passed=True,
        )
    if ihpi_value >= 75:
        return EVAGONOGOResult(
            status=GONOGOStatus.GO_WITH_MITIGATION,
            reasons=(
                "All gates passed; IHPI 75-84 (add mitigation: naps/breaks/task simplification)",
            ),
            ihpi_value=ihpi_value,
            safte_effectiveness=safte_eff,
            all_gates_passed=True,
        )
    return EVAGONOGOResult(
        status=GONOGOStatus.HOLD,
        reasons=(
            "All gates passed but IHPI < 75 (optimize sleep / delay EVA / reduce workload)",
        ),
        ihpi_value=ihpi_value,
        safte_effectiveness=safte_eff,
        all_gates_passed=True,
    )


# ---------------------------------------------------------------------------
# Radiation Assessment for EVA Scheduling
# ---------------------------------------------------------------------------
# Scientific References:
#   - NASA-STD-3001 Vol 1 Rev B (2022): Radiation Protection Technical Brief
#     https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf
#   - NOAA Space Weather Prediction Center: Solar Proton Events
#     https://www.swpc.noaa.gov/products/solar-proton-events
#   - Cucinotta FA et al. (2013): Space Radiation Cancer Risks and Uncertainties
#     DOI: 10.1088/0034-4885/76/5/056701
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RadiationAssessment:
    """Radiation environment assessment for EVA scheduling."""
    risk_level: RadiationRiskLevel
    estimated_dose_msv_hr: float
    spe_active: bool
    gcr_level: str  # "low", "moderate", "high"
    kp_index: float  # Geomagnetic activity index (0-9)
    eva_recommendation: str
    reasons: Tuple[str, ...]


def assess_radiation_for_eva(
    proton_flux_pfu: float = 1.0,
    kp_index: float = 2.0,
    solar_cycle_phase: str = "moderate",
) -> RadiationAssessment:
    """
    Assess radiation environment for EVA GO/NO-GO decision.
    
    This function evaluates space weather conditions using NOAA data
    to determine if radiation levels are safe for EVA operations.
    
    Args:
        proton_flux_pfu: >10 MeV proton flux in particle flux units (pfu)
                         Normal: <1, Alert: >10, Warning: >100, Storm: >1000
        kp_index: Geomagnetic activity index (0-9 scale)
                  Quiet: 0-2, Unsettled: 3-4, Storm: 5-6, Severe: 7-9
        solar_cycle_phase: "minimum", "ascending", "maximum", "descending"
        
    Returns:
        RadiationAssessment with risk level and recommendations
        
    References:
        - NOAA SWPC: https://www.swpc.noaa.gov/
        - NASA SRAG: https://srag.jsc.nasa.gov/
    """
    reasons: List[str] = []
    spe_active = False
    
    # Determine GCR level based on solar cycle
    gcr_levels = {
        "minimum": "high",  # Solar minimum = higher GCR
        "ascending": "moderate",
        "maximum": "low",  # Solar maximum = lower GCR
        "descending": "moderate",
    }
    gcr_level = gcr_levels.get(solar_cycle_phase, "moderate")
    
    # Base dose rate from GCR
    gcr_dose_multipliers = {"low": 0.7, "moderate": 1.0, "high": 1.4}
    base_dose = GCR_BASELINE_DOSE_RATE_MSV_DAY / 24.0  # mSv/hr
    gcr_dose = base_dose * gcr_dose_multipliers.get(gcr_level, 1.0)
    
    # Check for Solar Particle Event activity
    if proton_flux_pfu >= SPE_STORM_THRESHOLD_PFU:
        spe_active = True
        risk_level = RadiationRiskLevel.CRITICAL
        estimated_dose = gcr_dose + 5.0  # Major SPE adds significant dose
        reasons.append(f"CRITICAL: Major SPE in progress ({proton_flux_pfu:.0f} pfu)")
        reasons.append("Immediate shelter required - NO EVA")
        recommendation = "NO-GO: Shelter in place. Do not conduct EVA."
    elif proton_flux_pfu >= SPE_WARNING_THRESHOLD_PFU:
        spe_active = True
        risk_level = RadiationRiskLevel.HIGH
        estimated_dose = gcr_dose + 1.5  # Significant SPE
        reasons.append(f"WARNING: Significant SPE activity ({proton_flux_pfu:.0f} pfu)")
        reasons.append("EVA should be postponed until radiation subsides")
        recommendation = "NO-GO: Postpone EVA until proton flux < 100 pfu"
    elif proton_flux_pfu >= SPE_ALERT_THRESHOLD_PFU:
        spe_active = True
        risk_level = RadiationRiskLevel.MODERATE
        estimated_dose = gcr_dose + 0.3  # Minor SPE
        reasons.append(f"ALERT: Enhanced proton activity ({proton_flux_pfu:.0f} pfu)")
        reasons.append("Shorten EVA duration, monitor conditions")
        recommendation = "CAUTION: Limit EVA to 2 hours, continuous monitoring"
    else:
        # Normal conditions
        estimated_dose = gcr_dose
        if kp_index >= 7:
            risk_level = RadiationRiskLevel.HIGH
            reasons.append(f"Severe geomagnetic storm (Kp={kp_index})")
            recommendation = "CAUTION: Possible enhanced radiation, limit EVA"
        elif kp_index >= 5:
            risk_level = RadiationRiskLevel.MODERATE
            reasons.append(f"Geomagnetic storm conditions (Kp={kp_index})")
            recommendation = "GO with monitoring: Watch for radiation alerts"
        else:
            risk_level = RadiationRiskLevel.LOW
            reasons.append(f"Quiet geomagnetic conditions (Kp={kp_index})")
            reasons.append(f"GCR level: {gcr_level} (solar {solar_cycle_phase})")
            recommendation = "GO: Normal radiation environment"
    
    return RadiationAssessment(
        risk_level=risk_level,
        estimated_dose_msv_hr=estimated_dose,
        spe_active=spe_active,
        gcr_level=gcr_level,
        kp_index=kp_index,
        eva_recommendation=recommendation,
        reasons=tuple(reasons),
    )


# ---------------------------------------------------------------------------
# Activity Definitions with MET Values
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ActivityDefinition:
    """Definition of a schedulable activity."""
    id: str
    name: str
    category: ActivityCategory
    duration_min: int
    met_value: float
    met_source: str
    cognitive_load: str  # "low", "moderate", "high"
    constraints: Tuple[str, ...]  # List of constraint identifiers
    recovery_time_min: int = 0  # Recovery time after activity


# Fixed activities (daily requirements) - MET values from 2024 Adult Compendium
FIXED_ACTIVITIES: Tuple[ActivityDefinition, ...] = (
    ActivityDefinition(
        id="briefing",
        name="Daily Briefing",
        category=ActivityCategory.FIXED,
        duration_min=60,
        met_value=1.5,
        met_source="2024 Adult Compendium - sitting, meeting",
        cognitive_load="moderate",
        constraints=("all_crew_synchronous", "fixed_time_0700"),
    ),
    ActivityDefinition(
        id="breakfast",
        name="Breakfast",
        category=ActivityCategory.FIXED,
        duration_min=45,
        met_value=1.5,
        met_source="2024 Adult Compendium - eating",
        cognitive_load="low",
        constraints=("flexible_timing",),
    ),
    ActivityDefinition(
        id="lunch",
        name="Lunch",
        category=ActivityCategory.FIXED,
        duration_min=45,
        met_value=1.5,
        met_source="2024 Adult Compendium - eating",
        cognitive_load="low",
        constraints=("flexible_timing",),
    ),
    ActivityDefinition(
        id="dinner",
        name="Dinner",
        category=ActivityCategory.FIXED,
        duration_min=45,
        met_value=1.5,
        met_source="2024 Adult Compendium - eating",
        cognitive_load="low",
        constraints=("flexible_timing",),
    ),
    ActivityDefinition(
        id="exercise",
        name="Physical Exercise",
        category=ActivityCategory.RESOURCE_LIMITED,
        duration_min=60,
        met_value=7.0,
        met_source="2024 Adult Compendium - stationary cycling, moderate effort",
        cognitive_load="low",
        constraints=("resource_limited_1",),  # Max 1 concurrent (equipment constraint)
    ),
    ActivityDefinition(
        id="recreation",
        name="Recreation/Fun",
        category=ActivityCategory.INDIVIDUAL,
        duration_min=60,
        met_value=3.0,
        met_source="2024 Adult Compendium - activity-dependent average",
        cognitive_load="low",
        constraints=("individual_scheduling",),
    ),
    ActivityDefinition(
        id="hygiene",
        name="Hygiene/Prep",
        category=ActivityCategory.RESOURCE_LIMITED,
        duration_min=30,
        met_value=2.4,
        met_source="2024 Adult Compendium - personal hygiene average",
        cognitive_load="low",
        constraints=("resource_limited_1", "pre_duty_mandatory"),  # Hygiene module: 1 person
    ),
    ActivityDefinition(
        id="sleep",
        name="Sleep",
        category=ActivityCategory.FIXED,
        duration_min=480,  # 8 hours
        met_value=1.0,
        met_source="2024 Adult Compendium - sleeping",
        cognitive_load="none",
        constraints=("optimized_by_chronotype",),
    ),
)

# Variable activities (workload parameters)
VARIABLE_ACTIVITIES: Tuple[ActivityDefinition, ...] = (
    ActivityDefinition(
        id="lab_work",
        name="Laboratory Work",
        category=ActivityCategory.VARIABLE,
        duration_min=120,  # Variable 30-240 min blocks
        met_value=2.0,
        met_source="2024 Adult Compendium - laboratory work, moderate",
        cognitive_load="high",
        constraints=("variable_duration",),
        recovery_time_min=15,  # 15 min per hour
    ),
    # ---------------------------------------------------------------------------
    # Experiments (6 daily experiments, 1 hour each)
    # ---------------------------------------------------------------------------
    ActivityDefinition(
        id="exp_physio_monitoring",
        name="EXP-1: Physiological Monitoring",
        category=ActivityCategory.VARIABLE,
        duration_min=60,
        met_value=1.5,
        met_source="2024 Adult Compendium - sitting, data collection",
        cognitive_load="moderate",
        constraints=("daily_required", "equipment_available"),
    ),
    ActivityDefinition(
        id="exp_cortisol_sampling",
        name="EXP-2: Cortisol Salival Sampling",
        category=ActivityCategory.VARIABLE,
        duration_min=60,
        met_value=1.3,
        met_source="2024 Adult Compendium - sample collection, light",
        cognitive_load="low",
        constraints=("daily_required", "time_sensitive"),
    ),
    ActivityDefinition(
        id="exp_neurocognitive",
        name="EXP-3: Neurocognitive Battery",
        category=ActivityCategory.VARIABLE,
        duration_min=60,
        met_value=1.5,
        met_source="2024 Adult Compendium - cognitive testing",
        cognitive_load="high",
        constraints=("daily_required", "quiet_environment"),
    ),
    ActivityDefinition(
        id="exp_psychological",
        name="EXP-4: Psychological Assessment",
        category=ActivityCategory.VARIABLE,
        duration_min=60,
        met_value=1.3,
        met_source="2024 Adult Compendium - questionnaire completion",
        cognitive_load="moderate",
        constraints=("daily_required",),
    ),
    ActivityDefinition(
        id="exp_sleep_analysis",
        name="EXP-5: Sleep/Actigraphy Analysis",
        category=ActivityCategory.VARIABLE,
        duration_min=60,
        met_value=1.5,
        met_source="2024 Adult Compendium - data review, light",
        cognitive_load="moderate",
        constraints=("daily_required", "morning_preferred"),
    ),
    ActivityDefinition(
        id="exp_matb_workload",
        name="EXP-6: MATB-II Workload Assessment",
        category=ActivityCategory.VARIABLE,
        duration_min=60,
        met_value=1.8,
        met_source="2024 Adult Compendium - multi-tasking cognitive",
        cognitive_load="high",
        constraints=("daily_required", "computer_station"),
    ),
    # ---------------------------------------------------------------------------
    # EVA Activities with ISLE Protocol
    # References:
    #   - NTRS 20110007150: ISLE Prebreathe Protocol Peer Review Assessment
    #   - NASA-STD-3001 Vol 2 Rev B: Decompression Sickness Technical Brief
    #   - Gernhardt & Dervay (2013): EVA Operations Chapter 5.4
    # ---------------------------------------------------------------------------
    ActivityDefinition(
        id="eva_prep_isle",
        name="EVA Prep - ISLE Protocol",
        category=ActivityCategory.VARIABLE,
        duration_min=100,  # 40 min mask O2 + 20 min suit + 40 min in-suit prebreathe
        met_value=2.5,
        met_source="NASA PRP studies - light exercise in-suit (5.8 mL·kg⁻¹·min⁻¹)",
        cognitive_load="moderate",
        constraints=("eva_crew_only", "medical_clearance", "suit_checkout_complete"),
    ),
    ActivityDefinition(
        id="eva",
        name="Extravehicular Activity (EVA)",
        category=ActivityCategory.VARIABLE,
        duration_min=120,  # 2 hours for analog mission simulation
        met_value=4.5,
        met_source="NASA EVA metabolic rate: 194 kcal/hr (Waligora & Kumar 1995, PMID:11540993)",
        cognitive_load="high",
        constraints=(
            "medical_clearance",
            "prebreathe_complete",
            "min_recovery_48h",
            "vo2max_32.9",
            "max_crew_2",
        ),
        recovery_time_min=2880,  # 48 hours minimum (NASA-STD-3001)
    ),
    ActivityDefinition(
        id="eva_post",
        name="EVA Post - Suit Doffing & Debrief",
        category=ActivityCategory.VARIABLE,
        duration_min=60,
        met_value=2.0,
        met_source="NASA EMU doffing operations",
        cognitive_load="moderate",
        constraints=("eva_crew_only",),
    ),
)

# All activities combined
ALL_ACTIVITIES: Dict[str, ActivityDefinition] = {
    **{a.id: a for a in FIXED_ACTIVITIES},
    **{a.id: a for a in VARIABLE_ACTIVITIES},
}


# ---------------------------------------------------------------------------
# Crew Member Status
# ---------------------------------------------------------------------------

@dataclass
class CrewPhysiologicalStatus:
    """Current physiological status of a crew member."""
    crew_id: str
    timestamp: datetime
    
    # SAFTE/Fatigue
    safte_effectiveness: float = 90.0
    hours_awake: float = 8.0
    sleep_last_24h: float = 8.0
    
    # Subjective
    kss_score: float = 3.0
    samn_perelli_score: float = 3.0
    
    # HRV
    lnrmssd_current: float = 3.5
    lnrmssd_baseline_mean: float = 3.5
    lnrmssd_baseline_sd: float = 0.3
    
    # Hydration
    body_mass_change_pct: float = 0.0
    usg: Optional[float] = None
    
    # Energy
    energy_availability: float = 45.0
    
    # PVT
    pvt_lapses_3min: int = 5
    
    # Circadian
    phase_offset_hours: float = 0.0
    chronotype: str = "intermediate"
    
    # Task-specific
    vo2max: float = 40.0
    hours_since_last_eva: float = 100.0
    
    @property
    def lnrmssd_zscore(self) -> float:
        """Calculate lnRMSSD z-score."""
        if self.lnrmssd_baseline_sd <= 0:
            return 0.0
        return (self.lnrmssd_current - self.lnrmssd_baseline_mean) / self.lnrmssd_baseline_sd
    
    @property
    def subjective_score(self) -> float:
        """Combined subjective score (average of KSS and SP mapped to 0-1)."""
        kss_mapped = score_kss(self.kss_score)
        # Samn-Perelli is 1-7, map similarly to KSS
        sp_mapped = 1.0 if self.samn_perelli_score <= 3 else (0.0 if self.samn_perelli_score >= 7 else (1.0 - (self.samn_perelli_score - 3) / 4))
        return (kss_mapped + sp_mapped) / 2.0
    
    def compute_subscores(self) -> IHPISubscores:
        """Compute all IHPI subscores from current status."""
        return IHPISubscores(
            safte=score_safte(self.safte_effectiveness),
            pvt=score_pvt_lapses_3min(self.pvt_lapses_3min),
            circadian=score_circadian_alignment(self.phase_offset_hours),
            hrv=score_hrv_z(self.lnrmssd_zscore),
            hydration=score_hydration(self.body_mass_change_pct, self.usg),
            energy_availability=score_energy_availability(self.energy_availability),
            subjective=self.subjective_score,
            task_specific=score_task_specific(self.vo2max, self.hours_since_last_eva),
        )
    
    def compute_ihpi(self) -> float:
        """Compute IHPI score."""
        return compute_ihpi(self.compute_subscores())
    
    def eva_go_nogo(self) -> EVAGONOGOResult:
        """Evaluate EVA GO/NO-GO status."""
        return eva_go_nogo(
            safte_eff=self.safte_effectiveness,
            kss=self.kss_score,
            sleep_last_24h_h=self.sleep_last_24h,
            time_awake_h=self.hours_awake,
            body_mass_change_pct=self.body_mass_change_pct,
            usg=self.usg,
            pvt_lapses_3min=self.pvt_lapses_3min,
            ihpi_value=self.compute_ihpi(),
            vo2max=self.vo2max,
            hours_since_last_eva=self.hours_since_last_eva,
            energy_availability=self.energy_availability,
        )


@dataclass
class CrewMember:
    """Crew member profile and current status."""
    crew_id: str
    name: str
    role: str
    
    # Static profile
    age_years: int
    sex: str
    weight_kg: float
    height_cm: float
    vo2max_ml_kg_min: float
    chronotype: str = "intermediate"  # "early", "intermediate", "late"
    
    # Dynamic status
    status: Optional[CrewPhysiologicalStatus] = None
    
    def get_ihpi(self) -> float:
        """Get current IHPI score."""
        if self.status is None:
            return 75.0  # Default nominal
        return self.status.compute_ihpi()
    
    def get_risk_level(self) -> RiskLevel:
        """Get current risk level based on IHPI."""
        ihpi = self.get_ihpi()
        if ihpi >= 85:
            return RiskLevel.LOW
        if ihpi >= 75:
            return RiskLevel.MODERATE
        if ihpi >= 60:
            return RiskLevel.HIGH
        return RiskLevel.VERY_HIGH


# ---------------------------------------------------------------------------
# Activity Suitability Matrix
# ---------------------------------------------------------------------------

# Minimum IHPI required for activity domains
ACTIVITY_SUITABILITY_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "eva": {
        "min_ihpi_go": 85,
        "min_ihpi_mitigation": 75,
        "critical_factors": ["hrv", "safte", "energy_availability", "hydration", "vo2max"],
    },
    "aviation_pic": {
        "min_ihpi_go": 80,
        "min_ihpi_mitigation": 70,
        "critical_factors": ["safte", "pvt", "circadian"],
    },
    "extreme_sports": {
        "min_ihpi_go": 75,
        "min_ihpi_mitigation": 65,
        "critical_factors": ["hrv", "energy_availability", "recent_load"],
    },
    "mountaineering": {
        "min_ihpi_go": 70,
        "min_ihpi_mitigation": 60,
        "critical_factors": ["vo2max", "energy_availability", "acclimatization"],
    },
    "technical_diving": {
        "min_ihpi_go": 80,
        "min_ihpi_mitigation": 70,
        "critical_factors": ["safte", "behavioral", "pvt"],
    },
    "lab_work": {
        "min_ihpi_go": 60,
        "min_ihpi_mitigation": 50,
        "critical_factors": ["safte", "circadian"],
    },
}


def check_activity_suitability(
    crew_status: CrewPhysiologicalStatus,
    activity_id: str,
) -> Tuple[bool, str, Optional[str]]:
    """
    Check if crew member is suitable for an activity.
    
    Args:
        crew_status: Current physiological status
        activity_id: Activity identifier
        
    Returns:
        Tuple of (is_suitable, status, mitigation_notes)
    """
    thresholds = ACTIVITY_SUITABILITY_THRESHOLDS.get(
        activity_id,
        {"min_ihpi_go": 60, "min_ihpi_mitigation": 50, "critical_factors": []},
    )
    
    ihpi = crew_status.compute_ihpi()
    min_go = thresholds["min_ihpi_go"]
    min_mit = thresholds["min_ihpi_mitigation"]
    
    if ihpi >= min_go:
        return True, "GO", None
    if ihpi >= min_mit:
        return True, "GO-with-mitigation", "Consider adding breaks, simplifying tasks, or scheduling naps"
    return False, "HOLD", f"IHPI {ihpi:.1f} below minimum {min_mit} for {activity_id}"


# ---------------------------------------------------------------------------
# SAFTE Simulation & Performance Forecasting (Advanced)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SAFTEForecastPoint:
    """A single point in the SAFTE effectiveness forecast."""
    timestamp: datetime
    effectiveness: float  # 0-100
    sleep_reservoir: float  # 0-1
    circadian_phase: float  # 0-2π
    sleep_inertia: float  # 0-1
    risk_level: RiskLevel


@dataclass
class PerformanceForecast:
    """24-hour performance forecast for a crew member."""
    crew_id: str
    forecast_start: datetime
    forecast_points: List[SAFTEForecastPoint]
    
    # Summary statistics
    min_effectiveness: float = 100.0
    avg_effectiveness: float = 100.0
    time_below_90_minutes: int = 0
    time_below_70_minutes: int = 0
    optimal_work_windows: List[Tuple[datetime, datetime]] = field(default_factory=list)
    recommended_nap_windows: List[Tuple[datetime, datetime]] = field(default_factory=list)
    
    def get_effectiveness_at(self, time: datetime) -> float:
        """Get interpolated effectiveness at a specific time."""
        if not self.forecast_points:
            return 85.0
        
        # Find bracketing points
        for i, point in enumerate(self.forecast_points):
            if point.timestamp >= time:
                if i == 0:
                    return point.effectiveness
                # Linear interpolation
                prev = self.forecast_points[i - 1]
                dt_total = (point.timestamp - prev.timestamp).total_seconds()
                dt_current = (time - prev.timestamp).total_seconds()
                if dt_total > 0:
                    ratio = dt_current / dt_total
                    return prev.effectiveness + ratio * (point.effectiveness - prev.effectiveness)
                return point.effectiveness
        
        return self.forecast_points[-1].effectiveness if self.forecast_points else 85.0


def simulate_safte_24h(
    current_status: CrewPhysiologicalStatus,
    planned_sleep_start: datetime,
    planned_sleep_duration_hours: float = 8.0,
    chronotype_offset_hours: float = 0.0,
    resolution_minutes: int = 15,
) -> PerformanceForecast:
    """
    Simulate 24-hour SAFTE effectiveness forecast.
    
    This is a simplified SAFTE model implementation for scheduling.
    For full SAFTE simulation, use fatigue_calculator/safte_model.py.
    
    Args:
        current_status: Current crew physiological status
        planned_sleep_start: Planned sleep start time
        planned_sleep_duration_hours: Planned sleep duration
        chronotype_offset_hours: Chronotype adjustment (early=-2, late=+2)
        resolution_minutes: Forecast resolution in minutes
        
    Returns:
        24-hour performance forecast
    """
    from datetime import timezone
    
    # Initialize forecast
    now = datetime.now()
    forecast_points: List[SAFTEForecastPoint] = []
    
    # Current state
    current_effectiveness = current_status.safte_effectiveness
    hours_awake = current_status.hours_awake
    sleep_reservoir = min(1.0, current_effectiveness / 100.0)
    
    # SAFTE parameters (simplified, aligned with Hursh et al. 2004)
    # References:
    # - Hursh et al. (2004): Fatigue models for applied research in warfighting
    # - Core body temperature nadir: ~4 AM (end of sleep phase)
    # - Core body temperature peak: ~6 PM (late afternoon/early evening)
    # - Performance peak aligns with temperature peak (4-6 PM)
    TAU_DECAY = 18.2  # Sleep reservoir decay time constant (hours)
    TAU_RECOVERY = 4.5  # Sleep reservoir recovery time constant (hours)
    CIRCADIAN_AMPLITUDE = 15.0  # Circadian modulation amplitude (%)
    CIRCADIAN_PERIOD = 24.0  # hours
    
    # Circadian peak phase (SAFTE standard: 18:00 / 6 PM for typical entrainment)
    # Scientific evidence: Peak performance occurs in late afternoon/early evening (4-6 PM)
    # coinciding with peak core body temperature. Nadir occurs 12 hours earlier (4-6 AM).
    # Early chronotypes peak ~2 hours earlier, late chronotypes ~2 hours later.
    peak_hour = 18.0 - chronotype_offset_hours  # Early types peak earlier, late types later
    nadir_hour = (peak_hour + 12.0) % 24.0  # Nadir is 12 hours from peak
    
    # Simulate each time point
    planned_sleep_end = planned_sleep_start + timedelta(hours=planned_sleep_duration_hours)
    
    for i in range(int(24 * 60 / resolution_minutes) + 1):
        t = now + timedelta(minutes=i * resolution_minutes)
        hour_of_day = t.hour + t.minute / 60.0
        
        # Check if sleeping
        is_sleeping = planned_sleep_start <= t < planned_sleep_end
        
        # Update sleep reservoir
        dt_hours = resolution_minutes / 60.0
        if is_sleeping:
            # Recovery during sleep
            recovery_rate = (1.0 - sleep_reservoir) / TAU_RECOVERY
            sleep_reservoir = min(1.0, sleep_reservoir + recovery_rate * dt_hours)
            hours_awake = 0.0
        else:
            # Decay while awake
            decay_rate = sleep_reservoir / TAU_DECAY
            sleep_reservoir = max(0.0, sleep_reservoir - decay_rate * dt_hours)
            hours_awake += dt_hours
        
        # Circadian component (aligned with SAFTE model: peak at peak_hour, nadir 12h later)
        # Phase relative to peak: 0 at peak (maximum), π at nadir (minimum)
        phase_rel_to_peak = ((hour_of_day - peak_hour) % CIRCADIAN_PERIOD) / CIRCADIAN_PERIOD
        phase_rad = 2 * math.pi * phase_rel_to_peak
        # Cosine: 1 at peak (phase=0), -1 at nadir (phase=π)
        # Map to [1 - amplitude, 1 + amplitude] range, then normalize to [0.85, 1.0] for 15% amplitude
        circadian_cosine = math.cos(phase_rad)
        # SAFTE-style: positive cosine increases effectiveness, negative decreases it
        # Factor ranges from (1 - amplitude/100) at nadir to (1 + amplitude/100) at peak
        circadian_factor = 1.0 + (CIRCADIAN_AMPLITUDE / 100.0) * circadian_cosine
        
        # Sleep inertia (if just woke up)
        inertia = 0.0
        if not is_sleeping and planned_sleep_end <= t < planned_sleep_end + timedelta(minutes=30):
            minutes_since_wake = (t - planned_sleep_end).total_seconds() / 60
            inertia = max(0, 0.15 * (1 - minutes_since_wake / 30))  # 15% reduction for 30 min
        
        # Combined effectiveness
        effectiveness = 100.0 * sleep_reservoir * circadian_factor * (1 - inertia)
        effectiveness = clamp(effectiveness, 0.0, 100.0)
        
        # Determine risk level
        if effectiveness >= SAFTE_LOW_RISK_MIN:
            risk = RiskLevel.LOW
        elif effectiveness >= SAFTE_CAUTION_MIN:
            risk = RiskLevel.MODERATE
        elif effectiveness >= SAFTE_HIGH_RISK_MIN:
            risk = RiskLevel.HIGH
        else:
            risk = RiskLevel.VERY_HIGH
        
        forecast_points.append(SAFTEForecastPoint(
            timestamp=t,
            effectiveness=effectiveness,
            sleep_reservoir=sleep_reservoir,
            circadian_phase=phase_rad,
            sleep_inertia=inertia,
            risk_level=risk,
        ))
    
    # Calculate summary statistics
    effectivenesses = [p.effectiveness for p in forecast_points]
    min_eff = min(effectivenesses)
    avg_eff = sum(effectivenesses) / len(effectivenesses)
    time_below_90 = sum(1 for p in forecast_points if p.effectiveness < 90) * resolution_minutes
    time_below_70 = sum(1 for p in forecast_points if p.effectiveness < 70) * resolution_minutes
    
    # Find optimal work windows (effectiveness >= 90)
    optimal_windows: List[Tuple[datetime, datetime]] = []
    window_start = None
    for p in forecast_points:
        if p.effectiveness >= 90 and window_start is None:
            window_start = p.timestamp
        elif p.effectiveness < 90 and window_start is not None:
            optimal_windows.append((window_start, p.timestamp))
            window_start = None
    if window_start is not None:
        optimal_windows.append((window_start, forecast_points[-1].timestamp))
    
    # Find recommended nap windows (effectiveness < 80, not sleeping)
    nap_windows: List[Tuple[datetime, datetime]] = []
    for p in forecast_points:
        if p.effectiveness < 80:
            # Simple 15-30 min nap recommendation
            is_during_planned_sleep = planned_sleep_start <= p.timestamp < planned_sleep_end
            if not is_during_planned_sleep and 10 <= p.timestamp.hour <= 16:
                nap_windows.append((p.timestamp, p.timestamp + timedelta(minutes=20)))
    
    # Remove duplicate nap windows (keep first per 2-hour block)
    filtered_naps = []
    last_nap_hour = -3
    for start, end in nap_windows:
        if start.hour - last_nap_hour >= 2:
            filtered_naps.append((start, end))
            last_nap_hour = start.hour
    
    return PerformanceForecast(
        crew_id=current_status.crew_id if hasattr(current_status, 'crew_id') else "unknown",
        forecast_start=now,
        forecast_points=forecast_points,
        min_effectiveness=min_eff,
        avg_effectiveness=avg_eff,
        time_below_90_minutes=time_below_90,
        time_below_70_minutes=time_below_70,
        optimal_work_windows=optimal_windows,
        recommended_nap_windows=filtered_naps,
    )


# ---------------------------------------------------------------------------
# What-If Analysis
# ---------------------------------------------------------------------------

@dataclass
class WhatIfScenario:
    """A what-if scenario for schedule analysis."""
    scenario_id: str
    name: str
    description: str
    
    # Modified parameters
    sleep_change_hours: float = 0.0  # Change to sleep duration
    wake_time_shift_hours: float = 0.0  # Shift wake time
    nap_added_minutes: int = 0  # Add a nap
    activity_removed: Optional[str] = None  # Remove an activity
    activity_added: Optional[str] = None  # Add an activity
    
    # Results (computed)
    projected_ihpi: float = 0.0
    projected_risk: RiskLevel = RiskLevel.MODERATE
    effectiveness_delta: float = 0.0
    recommendation: str = ""


def analyze_what_if(
    current_status: CrewPhysiologicalStatus,
    scenario: WhatIfScenario,
) -> WhatIfScenario:
    """
    Analyze a what-if scenario and project outcomes.
    
    Args:
        current_status: Current crew physiological status
        scenario: What-if scenario to analyze
        
    Returns:
        Updated scenario with projected outcomes
    """
    # Start from current effectiveness
    base_effectiveness = current_status.safte_effectiveness
    new_effectiveness = base_effectiveness
    
    # Apply scenario modifications
    if scenario.sleep_change_hours != 0:
        # Each hour of extra sleep ≈ +5 effectiveness, each hour less ≈ -8 effectiveness
        if scenario.sleep_change_hours > 0:
            new_effectiveness += scenario.sleep_change_hours * 5.0
        else:
            new_effectiveness += scenario.sleep_change_hours * 8.0
    
    if scenario.nap_added_minutes > 0:
        # 20-minute nap ≈ +8 effectiveness, diminishing returns
        nap_benefit = min(12.0, scenario.nap_added_minutes * 0.4)
        new_effectiveness += nap_benefit
    
    if scenario.wake_time_shift_hours != 0:
        # Shift toward chronotype optimal = +2-3, away = -2-3
        # Simplified: assume shift is toward optimal
        new_effectiveness += abs(scenario.wake_time_shift_hours) * 1.5
    
    new_effectiveness = clamp(new_effectiveness, 0.0, 100.0)
    
    # Compute projected IHPI
    # Create modified status for IHPI computation
    modified_status = CrewPhysiologicalStatus(
        crew_id=current_status.crew_id,
        timestamp=current_status.timestamp,
        safte_effectiveness=new_effectiveness,
        kss_score=current_status.kss_score,
        samn_perelli_score=current_status.samn_perelli_score,
        pvt_lapses_3min=current_status.pvt_lapses_3min,
        lnrmssd_current=current_status.lnrmssd_current,
        lnrmssd_baseline_mean=current_status.lnrmssd_baseline_mean,
        lnrmssd_baseline_sd=current_status.lnrmssd_baseline_sd,
        body_mass_change_pct=current_status.body_mass_change_pct,
        usg=current_status.usg,
        energy_availability=current_status.energy_availability,
        phase_offset_hours=current_status.phase_offset_hours,
        chronotype=current_status.chronotype,
        vo2max=current_status.vo2max,
        hours_since_last_eva=current_status.hours_since_last_eva,
        hours_awake=max(0, current_status.hours_awake - scenario.nap_added_minutes / 60),
        sleep_last_24h=current_status.sleep_last_24h + scenario.sleep_change_hours,
    )
    
    projected_ihpi = modified_status.compute_ihpi()
    
    # Determine risk level
    if projected_ihpi >= 85:
        risk = RiskLevel.LOW
    elif projected_ihpi >= 75:
        risk = RiskLevel.MODERATE
    elif projected_ihpi >= 60:
        risk = RiskLevel.HIGH
    else:
        risk = RiskLevel.VERY_HIGH
    
    # Generate recommendation
    effectiveness_delta = new_effectiveness - base_effectiveness
    if effectiveness_delta > 5:
        recommendation = f"✅ Scenario improves effectiveness by {effectiveness_delta:.1f}%"
    elif effectiveness_delta > 0:
        recommendation = f"↗️ Slight improvement: +{effectiveness_delta:.1f}%"
    elif effectiveness_delta < -5:
        recommendation = f"⚠️ Scenario reduces effectiveness by {abs(effectiveness_delta):.1f}%"
    else:
        recommendation = "➡️ Minimal impact on effectiveness"
    
    # Update scenario with results
    scenario.projected_ihpi = projected_ihpi
    scenario.projected_risk = risk
    scenario.effectiveness_delta = effectiveness_delta
    scenario.recommendation = recommendation
    
    return scenario


# ---------------------------------------------------------------------------
# Workload Balancing
# ---------------------------------------------------------------------------

@dataclass
class WorkloadMetrics:
    """Workload metrics for a crew member."""
    crew_id: str
    total_work_minutes: int = 0
    total_rest_minutes: int = 0
    high_intensity_minutes: int = 0  # MET > 4
    cognitive_load_minutes: int = 0
    total_kcal_expenditure: float = 0.0
    work_rest_ratio: float = 0.0
    recovery_score: float = 100.0  # 0-100


def compute_workload_balance(
    crew_activities: List[Any],  # List of ScheduledActivity
    crew_weight_kg: float,
) -> WorkloadMetrics:
    """
    Compute workload balance metrics for a crew member's schedule.
    
    Args:
        crew_activities: List of scheduled activities
        crew_weight_kg: Crew member's body weight in kg
        
    Returns:
        Workload metrics
    """
    total_work = 0
    total_rest = 0
    high_intensity = 0
    cognitive = 0
    total_kcal = 0.0
    
    for activity in crew_activities:
        duration = getattr(activity, 'duration_minutes', 60)
        met = getattr(activity, 'met_value', 1.5)
        activity_id = getattr(activity, 'activity_id', '')
        
        # Classify activity
        if activity_id in ('sleep', 'recreation'):
            total_rest += duration
        else:
            total_work += duration
        
        if met > 4.0:
            high_intensity += duration
        
        if activity_id in ('lab_work', 'briefing', 'eva'):
            cognitive += duration
        
        # Energy expenditure
        kcal = kcal_from_met_duration(met, crew_weight_kg, duration)
        total_kcal += kcal
    
    # Work-rest ratio
    work_rest = total_work / max(1, total_rest)
    
    # Recovery score (simplified)
    recovery = 100.0
    if work_rest > 2.0:
        recovery -= (work_rest - 2.0) * 20
    if high_intensity > 120:
        recovery -= (high_intensity - 120) / 10
    recovery = clamp(recovery, 0.0, 100.0)
    
    return WorkloadMetrics(
        crew_id="",  # Set by caller
        total_work_minutes=total_work,
        total_rest_minutes=total_rest,
        high_intensity_minutes=high_intensity,
        cognitive_load_minutes=cognitive,
        total_kcal_expenditure=total_kcal,
        work_rest_ratio=work_rest,
        recovery_score=recovery,
    )


# ---------------------------------------------------------------------------
# EVA Procedures and Checklists
# ---------------------------------------------------------------------------
# Scientific References (verified):
#   - NTRS 20110007150: In-Suit Light Exercise (ISLE) Prebreathe Protocol Peer Review
#     https://ntrs.nasa.gov/citations/20110007150
#   - NASA-STD-3001 Vol 2 Rev B: Human Factors, Habitability, and Environmental Health
#     https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-037-decompression-sickness.pdf
#   - Gernhardt ML, Dervay JP (2013). Chapter 5.4 Extravehicular Activities.
#     https://www.nasa.gov/wp-content/uploads/2023/03/gernhardt-eva-ops-chp-5.4-2013.pdf
#   - NTRS 20000110097: Design and Testing of a 2-Hour O2 Prebreathe Protocol
#     https://ntrs.nasa.gov/citations/20000110097
#   - Katuntsev VP et al. (2004). EVA medical support on Mir. Acta Astronautica 54(8):577-587
#     PMID: 14740657
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EVAChecklistItem:
    """Single item in an EVA checklist."""
    id: str
    description: str
    responsible: str  # "EV1", "EV2", "IV", "MCC", "EVA_OFFICER"
    duration_min: int
    critical: bool = False
    verification_required: bool = False
    notes: str = ""


# ISLE Protocol Timeline (from NASA NTRS 20110007150 & NASA-STD-3001)
ISLE_PROTOCOL_TIMELINE: Tuple[EVAChecklistItem, ...] = (
    EVAChecklistItem(
        id="isle_01",
        description="Crew medical status check - vital signs, hydration, fatigue assessment",
        responsible="MCC",
        duration_min=10,
        critical=True,
        verification_required=True,
        notes="Flight Surgeon approval required for EVA GO",
    ),
    EVAChecklistItem(
        id="isle_02",
        description="Equipment Lock (EL) ingress and EMU power-up",
        responsible="EV1",
        duration_min=15,
        verification_required=True,
    ),
    EVAChecklistItem(
        id="isle_03",
        description="Begin 100% O2 mask prebreathe (40 minutes)",
        responsible="EV1",
        duration_min=40,
        critical=True,
        notes="Prebreathe at 14.7 psia cabin pressure",
    ),
    EVAChecklistItem(
        id="isle_04",
        description="EMU suit donning and checkout",
        responsible="EV1",
        duration_min=20,
        verification_required=True,
        notes="IV crew assists with suit integrity checks",
    ),
    EVAChecklistItem(
        id="isle_05",
        description="Airlock depressurization to 10.2 psia",
        responsible="IV",
        duration_min=5,
        critical=True,
    ),
    EVAChecklistItem(
        id="isle_06",
        description="In-suit light exercise prebreathe (40 min at 10.2 psia)",
        responsible="EV1",
        duration_min=40,
        critical=True,
        notes="Light arm/leg movements, ~5.8 mL·kg⁻¹·min⁻¹ O2 consumption",
    ),
    EVAChecklistItem(
        id="isle_07",
        description="Final suit leak check and systems verification",
        responsible="EV1",
        duration_min=10,
        critical=True,
        verification_required=True,
    ),
    EVAChecklistItem(
        id="isle_08",
        description="Crew Lock depressurization to vacuum (4.3 psia suit)",
        responsible="IV",
        duration_min=10,
        critical=True,
        notes="Depress to <0.5 psia for hatch opening",
    ),
)


# MCC EVA Checklist (Mission Control responsibilities)
MCC_EVA_CHECKLIST: Tuple[EVAChecklistItem, ...] = (
    # T-24 hours
    EVAChecklistItem(
        id="mcc_01",
        description="EVA weather/environment assessment",
        responsible="MCC",
        duration_min=30,
        notes="Solar activity, thermal conditions, lighting",
    ),
    EVAChecklistItem(
        id="mcc_02",
        description="Crew physiological status review (SAFTE, HRV, sleep)",
        responsible="MCC",
        duration_min=20,
        critical=True,
        verification_required=True,
        notes="Verify IHPI ≥75, SAFTE ≥85%, lnRMSSD z-score > -1",
    ),
    EVAChecklistItem(
        id="mcc_03",
        description="EVA timeline review and task prioritization",
        responsible="MCC",
        duration_min=30,
        verification_required=True,
    ),
    EVAChecklistItem(
        id="mcc_04",
        description="Communication systems check - primary and backup",
        responsible="MCC",
        duration_min=15,
        critical=True,
    ),
    # T-2 hours
    EVAChecklistItem(
        id="mcc_05",
        description="Flight Surgeon GO/NO-GO poll",
        responsible="MCC",
        duration_min=10,
        critical=True,
        verification_required=True,
        notes="Medical clearance for each EV crew member",
    ),
    EVAChecklistItem(
        id="mcc_06",
        description="EVA Officer GO/NO-GO poll",
        responsible="MCC",
        duration_min=10,
        critical=True,
        verification_required=True,
    ),
    EVAChecklistItem(
        id="mcc_07",
        description="Final GO/NO-GO poll - all stations",
        responsible="MCC",
        duration_min=15,
        critical=True,
        verification_required=True,
    ),
    # During EVA
    EVAChecklistItem(
        id="mcc_08",
        description="Continuous metabolic rate monitoring",
        responsible="MCC",
        duration_min=0,  # Continuous
        notes="Alert if sustained >300 kcal/hr",
    ),
    EVAChecklistItem(
        id="mcc_09",
        description="Suit consumables monitoring (O2, battery, CO2)",
        responsible="MCC",
        duration_min=0,  # Continuous
        critical=True,
    ),
    EVAChecklistItem(
        id="mcc_10",
        description="30-minute status checks with EV crew",
        responsible="MCC",
        duration_min=5,
        notes="Fatigue assessment, task progress",
    ),
)


# EVA Officer Checklist (detailed procedures)
EVA_OFFICER_CHECKLIST: Tuple[EVAChecklistItem, ...] = (
    # Pre-EVA (T-48 hours)
    EVAChecklistItem(
        id="evo_01",
        description="EMU inspection and servicing verification",
        responsible="EVA_OFFICER",
        duration_min=60,
        critical=True,
        verification_required=True,
        notes="Check suit hours, last maintenance, consumable levels",
    ),
    EVAChecklistItem(
        id="evo_02",
        description="Tool kit audit and configuration",
        responsible="EVA_OFFICER",
        duration_min=30,
        verification_required=True,
    ),
    EVAChecklistItem(
        id="evo_03",
        description="Crew EVA readiness certification check",
        responsible="EVA_OFFICER",
        duration_min=20,
        critical=True,
        notes="Verify VO₂max ≥32.9 mL/kg/min, training currency",
    ),
    EVAChecklistItem(
        id="evo_04",
        description="Airlock systems verification",
        responsible="EVA_OFFICER",
        duration_min=45,
        critical=True,
        verification_required=True,
    ),
    # Pre-EVA (T-4 hours)
    EVAChecklistItem(
        id="evo_05",
        description="EMU battery installation and checkout",
        responsible="EVA_OFFICER",
        duration_min=30,
        verification_required=True,
    ),
    EVAChecklistItem(
        id="evo_06",
        description="O2 and H2O recharge verification",
        responsible="EVA_OFFICER",
        duration_min=20,
        critical=True,
        notes="Verify consumables for planned EVA duration + 30 min reserve",
    ),
    EVAChecklistItem(
        id="evo_07",
        description="Comm check with MCC on all frequencies",
        responsible="EVA_OFFICER",
        duration_min=15,
        critical=True,
    ),
    # ISLE Protocol support
    EVAChecklistItem(
        id="evo_08",
        description="O2 mask prebreathe initiation and monitoring",
        responsible="EVA_OFFICER",
        duration_min=40,
        critical=True,
        notes="Start time logged, verify 100% O2 flow",
    ),
    EVAChecklistItem(
        id="evo_09",
        description="Supervise EMU donning and assist with suit-up",
        responsible="EVA_OFFICER",
        duration_min=30,
        verification_required=True,
    ),
    EVAChecklistItem(
        id="evo_10",
        description="Suit integrity leak check (press to 4.3 psi delta-P)",
        responsible="EVA_OFFICER",
        duration_min=15,
        critical=True,
        verification_required=True,
        notes="Max allowable leak rate: 100 sccm",
    ),
    EVAChecklistItem(
        id="evo_11",
        description="In-suit prebreathe monitoring (40 min ISLE)",
        responsible="EVA_OFFICER",
        duration_min=40,
        critical=True,
        notes="Monitor crew comfort, suit parameters, light exercise compliance",
    ),
    # EVA Egress
    EVAChecklistItem(
        id="evo_12",
        description="Final hatch seal verification",
        responsible="EVA_OFFICER",
        duration_min=5,
        critical=True,
    ),
    EVAChecklistItem(
        id="evo_13",
        description="Crew Lock depress and hatch opening clearance",
        responsible="EVA_OFFICER",
        duration_min=10,
        critical=True,
        verification_required=True,
    ),
    # Post-EVA
    EVAChecklistItem(
        id="evo_14",
        description="Hatch close and Crew Lock repress verification",
        responsible="EVA_OFFICER",
        duration_min=15,
        critical=True,
    ),
    EVAChecklistItem(
        id="evo_15",
        description="Post-EVA crew medical assessment",
        responsible="EVA_OFFICER",
        duration_min=20,
        critical=True,
        notes="DCS symptom check, fatigue assessment, hydration status",
    ),
    EVAChecklistItem(
        id="evo_16",
        description="EMU doffing and post-EVA servicing",
        responsible="EVA_OFFICER",
        duration_min=45,
        verification_required=True,
    ),
    EVAChecklistItem(
        id="evo_17",
        description="EVA debrief and lessons learned documentation",
        responsible="EVA_OFFICER",
        duration_min=30,
    ),
)


# Complete EVA procedure timeline for analog missions (2-hour EVA)
ANALOG_EVA_TIMELINE: Dict[str, Any] = {
    "total_duration_min": 280,  # ~4.5 hours total
    "phases": {
        "pre_eva": {
            "duration_min": 100,
            "activities": [
                "Medical clearance (10 min)",
                "O2 mask prebreathe - 40 min at 14.7 psia",
                "EMU donning - 20 min",
                "Depress to 10.2 psia - 5 min",
                "In-suit ISLE prebreathe - 40 min",
                "Final checks - 10 min",
                "Depress to vacuum - 10 min",
            ],
        },
        "eva_operations": {
            "duration_min": 120,  # 2-hour EVA
            "activities": [
                "Hatch opening and egress (10 min)",
                "Translation to worksite (15 min)",
                "Primary tasks (60 min)",
                "Secondary tasks (20 min)",
                "Translation back (10 min)",
                "Hatch ingress (5 min)",
            ],
        },
        "post_eva": {
            "duration_min": 60,
            "activities": [
                "Repress to 14.7 psia (15 min)",
                "Hatch opening and helmet removal (10 min)",
                "EMU doffing (20 min)",
                "Medical assessment (10 min)",
                "Debrief (5 min)",
            ],
        },
    },
    "references": [
        {
            "citation": "NASA NTRS 20110007150: In-Suit Light Exercise (ISLE) Prebreathe Protocol Peer Review Assessment",
            "url": "https://ntrs.nasa.gov/citations/20110007150",
            "key_finding": "ISLE saves 2.5 kg O2/EVA vs previous protocols; 40-min mask + 40-min in-suit prebreathe",
        },
        {
            "citation": "NASA-STD-3001 Technical Brief: Decompression Sickness",
            "url": "https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-037-decompression-sickness.pdf",
            "key_finding": "ISLE protocol: 40 min O2 by mask → 20 min depress to 10.2 psia → 40 min in-suit light exercise",
        },
        {
            "citation": "Gernhardt ML, Dervay JP (2013). EVA Operations Chapter 5.4",
            "url": "https://www.nasa.gov/wp-content/uploads/2023/03/gernhardt-eva-ops-chp-5.4-2013.pdf",
            "key_finding": "Light exercise at 5.8 mL·kg⁻¹·min⁻¹ O2 enhances nitrogen washout",
        },
        {
            "citation": "Katuntsev VP et al. (2004). Mir EVA medical support. PMID:14740657",
            "url": "https://pubmed.ncbi.nlm.nih.gov/14740657/",
            "key_finding": "30-min prebreathe with 40 kPa suit pressure - zero DCS incidents in 78 EVAs",
        },
    ],
}


# Experiment IDs for scheduling
EXPERIMENT_IDS: Tuple[str, ...] = (
    "exp_physio_monitoring",
    "exp_cortisol_sampling",
    "exp_neurocognitive",
    "exp_psychological",
    "exp_sleep_analysis",
    "exp_matb_workload",
)


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Constants
    "NASA_EVA_VO2MAX_MIN_ML_KG_MIN",
    "SAFTE_LOW_RISK_MIN",
    "SAFTE_CAUTION_MIN",
    "SAFTE_HIGH_RISK_MIN",
    "SAFTE_CRITICAL_THRESHOLD",
    # NASA Scheduling Factors
    "NOMINAL_WORKDAY_HOURS",
    "MAX_WORKDAY_HOURS",
    "EXTENDED_WORKDAY_HOURS",
    "MAX_CONTINUOUS_WORK_HOURS",
    "COGNITIVE_WORKLOAD_LOW",
    "COGNITIVE_WORKLOAD_MEDIUM",
    "COGNITIVE_WORKLOAD_HIGH",
    "PHYSICAL_WORKLOAD_TARGET",
    "SchedulingConstraint",
    "ISS_SCHEDULING_CONSTRAINTS",
    "TaskCategory",
    "TASK_CATEGORIES",
    "PRIORITY_EMERGENCY",
    "PRIORITY_SAFETY_CRITICAL",
    "PRIORITY_MISSION_CRITICAL",
    "PRIORITY_HEALTH_MAINTENANCE",
    "PRIORITY_ROUTINE_OPS",
    "PRIORITY_DISCRETIONARY",
    # Enums
    "ActivityCategory",
    "RiskLevel",
    "GONOGOStatus",
    # Utility functions
    "clamp",
    "kcal_per_hour_from_met",
    "watts_from_kcal_per_hour",
    "kcal_from_met_duration",
    # Scoring functions
    "score_safte",
    "score_kss",
    "score_pvt_lapses_3min",
    "score_hrv_z",
    "score_hydration",
    "score_energy_availability",
    "score_circadian_alignment",
    "score_task_specific",
    # IHPI
    "IHPISubscores",
    "DEFAULT_IHPI_WEIGHTS",
    "compute_ihpi",
    # GO/NO-GO
    "EVAGONOGOResult",
    "eva_go_nogo",
    # Radiation Assessment
    "RadiationRiskLevel",
    "RadiationAssessment",
    "assess_radiation_for_eva",
    "NASA_CAREER_DOSE_LIMIT_MSV",
    "SPE_ALERT_THRESHOLD_PFU",
    "SPE_WARNING_THRESHOLD_PFU",
    "SPE_STORM_THRESHOLD_PFU",
    # Activities
    "ActivityDefinition",
    "FIXED_ACTIVITIES",
    "VARIABLE_ACTIVITIES",
    "ALL_ACTIVITIES",
    # Crew
    "CrewPhysiologicalStatus",
    "CrewMember",
    # Suitability
    "ACTIVITY_SUITABILITY_THRESHOLDS",
    # Advanced - SAFTE Simulation
    "SAFTEForecastPoint",
    "PerformanceForecast",
    "simulate_safte_24h",
    # Advanced - What-If Analysis
    "WhatIfScenario",
    "analyze_what_if",
    # Advanced - Workload Balancing
    "WorkloadMetrics",
    "compute_workload_balance",
    "check_activity_suitability",
    # EVA Procedures and Checklists
    "EVAChecklistItem",
    "ISLE_PROTOCOL_TIMELINE",
    "MCC_EVA_CHECKLIST",
    "EVA_OFFICER_CHECKLIST",
    "ANALOG_EVA_TIMELINE",
    "EXPERIMENT_IDS",
]

