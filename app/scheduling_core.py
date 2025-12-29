"""
Crew Scheduling and Human Performance Management - Core Science Layer.

This module implements evidence-based scoring functions for crew scheduling,
performance prediction, and GO/NO-GO decision support following:
- SAFTE-FAST validation evidence (U.S. Senate testimony)
- NASA Human Performance standards (VO2max ≥32.9 ml/kg/min for EVA)
- IOC Energy Availability thresholds
- Task Force ESC/NASPE HRV standards

Scientific References:
- SAFTE-FAST validation: Hursh SR et al. (2004). Aviat Space Environ Med.
- EVA metabolic rates: Skylab EVA ~238 kcal/hr, Shuttle EVA ~194 kcal/hr (NASA NTRS)
- HRV lnRMSSD z-score approach: Plews DJ et al. (2013). Int J Sports Physiol Perform.
- Energy Availability: IOC Consensus Statement (2018). Br J Sports Med.
- MET values: 2024 Adult Compendium of Physical Activities
- NASA VO2max requirement: NASA-STD-3001 Human Performance Capabilities

Author: Dr. Diego Leonel Malpica Hincapié, MD
Version: 1.0.0
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
        constraints=("resource_limited_2",),  # Max 2 concurrent
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
        category=ActivityCategory.FIXED,
        duration_min=30,
        met_value=2.4,
        met_source="2024 Adult Compendium - personal hygiene average",
        cognitive_load="low",
        constraints=("pre_duty_mandatory",),
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
    ActivityDefinition(
        id="eva",
        name="Extravehicular Activity (EVA)",
        category=ActivityCategory.VARIABLE,
        duration_min=360,  # Typically 5-7+ hours
        met_value=4.5,
        met_source="NASA measured EVA metabolic rate (194-238 kcal/hr range, ~4.5 MET for 70kg)",
        cognitive_load="high",
        constraints=(
            "medical_clearance",
            "prebreathe_protocol",
            "min_recovery_48h",
            "vo2max_32.9",
        ),
        recovery_time_min=2880,  # 48 hours minimum
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
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Constants
    "NASA_EVA_VO2MAX_MIN_ML_KG_MIN",
    "SAFTE_LOW_RISK_MIN",
    "SAFTE_CAUTION_MIN",
    "SAFTE_HIGH_RISK_MIN",
    "SAFTE_CRITICAL_THRESHOLD",
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
    "check_activity_suitability",
]

