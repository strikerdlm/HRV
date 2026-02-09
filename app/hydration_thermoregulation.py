# Author: Dr Diego Malpica MD
"""Hydration, thermoregulation, and dehydration performance impact module.

Pure functions implementing validated scientific models for:
- Sweat rate prediction across activity levels (sedentary to hard exercise)
- Core body temperature estimation under heat stress
- Dehydration percentage and cumulative water loss prediction
- Performance decrement from dehydration (cognitive and physical)
- Physiological Strain Index (PhSI) per Moran et al. (1998)
- Integrated hydration-readiness modifier for IHPI fusion
- Heat-stress-adjusted fluid replacement recommendations

Design goals (per project rules):
- Pure functions, no side effects, no recursion.
- Bounded execution, full type hints, frozen dataclasses.
- All thresholds from peer-reviewed literature.

Scientific References:
- Sawka, M.N., Burke, L.M., Eichner, E.R., Maughan, R.J., Montain, S.J.,
  & Stachenfeld, N.S. (2007). American College of Sports Medicine position
  stand. Exercise and fluid replacement. Medicine & Science in Sports &
  Exercise, 39(2), 377-390. DOI: 10.1249/mss.0b013e31802ca597
- Cheuvront, S.N., & Kenefick, R.W. (2014). Dehydration: Physiology,
  assessment, and performance effects. Comprehensive Physiology, 4(1),
  257-285. DOI: 10.1002/cphy.c130017
- Gonzalez-Alonso, J., Teller, C., Andersen, S.L., Jensen, F.B., Hyldig,
  T., & Nielsen, B. (1999). Influence of body temperature on the development
  of fatigue during prolonged exercise in the heat. Journal of Applied
  Physiology, 86(3), 1032-1039. DOI: 10.1152/jappl.1999.86.3.1032
- Moran, D.S., Shitzer, A., & Pandolf, K.B. (1998). A physiological strain
  index to evaluate heat stress. American Journal of Physiology, 275(1),
  R129-R134. DOI: 10.1152/ajpregu.1998.275.1.R129
- Shapiro, Y., Pandolf, K.B., & Goldman, R.F. (1982). Predicting sweat loss
  response to exercise, environment and clothing. European Journal of Applied
  Physiology, 48(1), 83-96. DOI: 10.1007/BF00421168
- Montain, S.J., & Coyle, E.F. (1992). Influence of graded dehydration on
  hyperthermia and cardiovascular drift during exercise. Journal of Applied
  Physiology, 73(4), 1340-1350. DOI: 10.1152/jappl.1992.73.4.1340
- Sawka, M.N., Cheuvront, S.N., & Kenefick, R.W. (2015). Hypohydration and
  human performance: Impact of environment and physiological mechanisms.
  Sports Medicine, 45(Suppl 1), S51-S60. DOI: 10.1007/s40279-015-0395-7
- Casa, D.J., DeMartini, J.K., Bergeron, M.F., et al. (2015). National
  Athletic Trainers' Association position statement: Exertional heat
  illnesses. Journal of Athletic Training, 50(9), 986-1000.
  DOI: 10.4085/1062-6050-50.9.07
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Final, List, Optional

# ---------------------------------------------------------------------------
# Constants — Activity-level metabolic rates (W/m², ISO 8996:2004)
# ---------------------------------------------------------------------------

# Metabolic heat production by activity level (W/m² body surface area)
# Reference: ISO 8996:2004, Parsons (2014) Human Thermal Environments
_MET_SEDENTARY: Final[float] = 58.0      # 1.0 MET — sitting, resting
_MET_LIGHT: Final[float] = 93.0          # 1.6 MET — light office work, walking 3 km/h
_MET_MODERATE: Final[float] = 175.0      # 3.0 MET — walking 5 km/h, light manual work
_MET_VIGOROUS: Final[float] = 290.0      # 5.0 MET — jogging, heavy manual work
_MET_HARD: Final[float] = 400.0          # 6.9 MET — running 8-10 km/h
_MET_VERY_HARD: Final[float] = 520.0     # 9.0 MET — sprinting, competitive sports

# Map activity strings to metabolic rates (W/m²)
_ACTIVITY_MET_RATES: Final[Dict[str, float]] = {
    "sedentary": _MET_SEDENTARY,
    "light": _MET_LIGHT,
    "moderate": _MET_MODERATE,
    "vigorous": _MET_VIGOROUS,
    "hard": _MET_HARD,
    "very_hard": _MET_VERY_HARD,
}

# Sweat rate coefficients — validated against Shapiro et al. (1982)
# Base sweat rate at thermoneutral conditions (22 C, 50% RH), mL/h
_SR_BASE_SEDENTARY: Final[float] = 100.0    # Insensible + minimal sweating
_SR_BASE_LIGHT: Final[float] = 300.0
_SR_BASE_MODERATE: Final[float] = 600.0
_SR_BASE_VIGOROUS: Final[float] = 1000.0
_SR_BASE_HARD: Final[float] = 1500.0
_SR_BASE_VERY_HARD: Final[float] = 2000.0

_ACTIVITY_SR_BASE: Final[Dict[str, float]] = {
    "sedentary": _SR_BASE_SEDENTARY,
    "light": _SR_BASE_LIGHT,
    "moderate": _SR_BASE_MODERATE,
    "vigorous": _SR_BASE_VIGOROUS,
    "hard": _SR_BASE_HARD,
    "very_hard": _SR_BASE_VERY_HARD,
}

# Core temperature thresholds (Gonzalez-Alonso et al., 1999; Casa et al., 2015)
_TC_BASELINE: Final[float] = 37.0      # Normal resting core temperature (C)
_TC_MILD_HYPER: Final[float] = 38.0    # Mild hyperthermia threshold
_TC_MODERATE_HYPER: Final[float] = 39.0  # Moderate hyperthermia
_TC_SEVERE_HYPER: Final[float] = 40.0  # Severe hyperthermia / heat stroke risk
_TC_CRITICAL: Final[float] = 40.5      # Critical — immediate cooling required

# Dehydration performance thresholds (Cheuvront & Kenefick, 2014)
_DEHY_THRESHOLD_MILD: Final[float] = 1.0     # % body mass loss
_DEHY_THRESHOLD_MODERATE: Final[float] = 2.0
_DEHY_THRESHOLD_SIGNIFICANT: Final[float] = 3.0
_DEHY_THRESHOLD_SEVERE: Final[float] = 5.0
_DEHY_THRESHOLD_DANGEROUS: Final[float] = 7.0


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SweatRateEstimate:
    """Predicted sweat rate for given conditions.

    Attributes:
        sweat_rate_ml_h: Sweat rate in mL/hour.
        sweat_rate_l_h: Sweat rate in L/hour.
        activity_level: Activity level string.
        metabolic_rate_w_m2: Metabolic heat production (W/m²).
        wbgt_c: WBGT temperature used (C).
        heat_adjustment_factor: Multiplier applied for heat stress.
        description: Human-readable description.
    """

    sweat_rate_ml_h: float
    sweat_rate_l_h: float
    activity_level: str
    metabolic_rate_w_m2: float
    wbgt_c: float
    heat_adjustment_factor: float
    description: str


@dataclass(frozen=True, slots=True)
class DehydrationEstimate:
    """Cumulative dehydration prediction over a time period.

    Attributes:
        duration_hours: Duration of exposure/activity (h).
        total_sweat_loss_ml: Total predicted sweat loss (mL).
        total_sweat_loss_l: Total predicted sweat loss (L).
        fluid_intake_ml: Estimated fluid intake during period (mL).
        net_fluid_deficit_ml: Net fluid deficit (mL).
        body_mass_loss_pct: Percentage of body mass lost.
        dehydration_category: Severity category string.
        risk_level: Risk classification.
        description: Human-readable interpretation.
    """

    duration_hours: float
    total_sweat_loss_ml: float
    total_sweat_loss_l: float
    fluid_intake_ml: float
    net_fluid_deficit_ml: float
    body_mass_loss_pct: float
    dehydration_category: str
    risk_level: str
    description: str


@dataclass(frozen=True, slots=True)
class CoreTemperatureEstimate:
    """Predicted core body temperature.

    Based on Gonzalez-Alonso et al. (1999) and Montain & Coyle (1992):
    Each 1% dehydration raises Tc by ~0.1-0.23 C during exercise.
    WBGT excess above thermoneutral (22 C) contributes ~0.03 C per degree.

    Attributes:
        core_temp_c: Estimated core temperature (C).
        baseline_c: Resting baseline temperature (C).
        rise_from_exercise_c: Temperature rise from metabolic heat.
        rise_from_heat_stress_c: Temperature rise from environment.
        rise_from_dehydration_c: Temperature rise from hypohydration.
        risk_category: Hyperthermia risk classification.
        description: Human-readable interpretation.
    """

    core_temp_c: float
    baseline_c: float
    rise_from_exercise_c: float
    rise_from_heat_stress_c: float
    rise_from_dehydration_c: float
    risk_category: str
    description: str


@dataclass(frozen=True, slots=True)
class PhysiologicalStrainIndex:
    """Physiological Strain Index (PhSI) per Moran et al. (1998).

    PhSI = 5 * (Tc - Tc0) / (39.5 - Tc0) + 5 * (HR - HR0) / (HRmax - HR0)

    Scale: 0-10
    0-3: Low/no strain
    3-5: Low strain
    5-7: Moderate strain
    7-9: High strain
    9-10: Very high / dangerous strain

    Attributes:
        phsi_value: PhSI score (0-10).
        thermal_component: Thermal strain component (0-5).
        cardiovascular_component: Cardiovascular strain component (0-5).
        strain_category: Category label.
        description: Interpretation.
    """

    phsi_value: float
    thermal_component: float
    cardiovascular_component: float
    strain_category: str
    description: str


@dataclass(frozen=True, slots=True)
class PerformanceDecrement:
    """Cognitive and physical performance impact from dehydration.

    Based on Cheuvront & Kenefick (2014) and Sawka et al. (2015):
    - Aerobic performance: ~2-4% decrement per 1% body mass loss beyond 2%
    - Cognitive performance: measurable impairment at >= 2% body mass loss
    - Strength: relatively preserved until >= 3-4% loss

    Attributes:
        dehydration_pct: Body mass loss percentage.
        aerobic_performance_pct: Aerobic performance remaining (0-100%).
        cognitive_performance_pct: Cognitive performance remaining (0-100%).
        strength_performance_pct: Strength performance remaining (0-100%).
        overall_performance_pct: Weighted overall performance (0-100%).
        readiness_modifier: Bounded modifier for IHPI integration (-10 to 0).
        risk_level: Dehydration risk level string.
        description: Interpretation text.
        recommendations: List of hydration recommendations.
    """

    dehydration_pct: float
    aerobic_performance_pct: float
    cognitive_performance_pct: float
    strength_performance_pct: float
    overall_performance_pct: float
    readiness_modifier: float
    risk_level: str
    description: str
    recommendations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HydrationThermoregulationAssessment:
    """Comprehensive hydration and thermoregulation assessment.

    Integrates all sub-models into a single operational summary suitable
    for dashboard display and IHPI readiness fusion.

    Attributes:
        sweat_rate: Predicted sweat rate.
        dehydration: Cumulative dehydration estimate.
        core_temp: Core temperature prediction.
        phsi: Physiological Strain Index.
        performance: Performance decrement analysis.
        fluid_replacement_ml_h: Recommended fluid intake (mL/h).
        readiness_modifier: Bounded modifier for IHPI fusion (-10 to 0).
        heat_stress_category: Combined heat stress category.
        hydration_status: Overall hydration status label.
        operational_guidance: Actionable guidance string.
    """

    sweat_rate: SweatRateEstimate
    dehydration: DehydrationEstimate
    core_temp: CoreTemperatureEstimate
    phsi: PhysiologicalStrainIndex
    performance: PerformanceDecrement
    fluid_replacement_ml_h: float
    readiness_modifier: float
    heat_stress_category: str
    hydration_status: str
    operational_guidance: str


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a value to [lo, hi]."""
    return max(lo, min(hi, value))


def _compute_wbgt_heat_factor(wbgt_c: float) -> float:
    """Compute sweat-rate heat adjustment factor from WBGT.

    Based on ISO 7243:2017 work-rate adjustment and empirical sweat data
    from Sawka et al. (2007).

    Below WBGT 22 C (thermoneutral): factor = 1.0
    Each degree above 22 C adds ~4-5% to sweat rate.
    Capped at 2.5x for extreme heat (WBGT ~45 C).

    Args:
        wbgt_c: Wet Bulb Globe Temperature in Celsius.

    Returns:
        Multiplicative heat adjustment factor (>= 1.0).
    """
    if wbgt_c <= 22.0:
        return 1.0
    excess = wbgt_c - 22.0
    # ~4.5% increase per degree C above thermoneutral
    factor = 1.0 + 0.045 * excess
    return min(factor, 2.5)


# ---------------------------------------------------------------------------
# Sweat Rate Prediction
# ---------------------------------------------------------------------------


def estimate_sweat_rate(
    activity_level: str,
    wbgt_c: float = 22.0,
    *,
    body_mass_kg: float = 70.0,
    acclimatized: bool = True,
) -> SweatRateEstimate:
    """Predict sweat rate based on activity level and heat stress.

    Model synthesized from:
    - Shapiro et al. (1982) — metabolic and environmental determinants
    - Sawka et al. (2007) — ACSM position stand sweat rate ranges
    - ISO 7243:2017 — WBGT-based heat stress classification

    Acclimatization increases sweat rate by ~10-15% (more efficient cooling)
    but also increases sweat sodium concentration adaptation.

    Args:
        activity_level: One of "sedentary", "light", "moderate", "vigorous",
                        "hard", "very_hard".
        wbgt_c: Wet Bulb Globe Temperature (C). Use 22 for thermoneutral.
        body_mass_kg: Body mass in kg (heavier individuals sweat more).
        acclimatized: Whether the individual is heat-acclimatized.

    Returns:
        SweatRateEstimate with predicted sweat rate.

    Raises:
        ValueError: If activity_level is invalid.
    """
    act = activity_level.lower().strip()
    if act not in _ACTIVITY_SR_BASE:
        raise ValueError(
            f"Invalid activity_level '{activity_level}'. "
            f"Must be one of: {', '.join(_ACTIVITY_SR_BASE.keys())}"
        )

    if not math.isfinite(wbgt_c):
        raise ValueError("wbgt_c must be a finite number.")
    if body_mass_kg <= 0 or not math.isfinite(body_mass_kg):
        raise ValueError("body_mass_kg must be a positive finite number.")

    # Base sweat rate for 70 kg reference person
    base_sr = _ACTIVITY_SR_BASE[act]

    # Body mass scaling (linear, Sawka et al. 2007)
    mass_factor = body_mass_kg / 70.0

    # Heat stress adjustment
    heat_factor = _compute_wbgt_heat_factor(wbgt_c)

    # Acclimatization factor (acclimatized = more efficient sweating)
    acclim_factor = 1.12 if acclimatized else 1.0

    sr_ml_h = base_sr * mass_factor * heat_factor * acclim_factor
    sr_ml_h = _clamp(sr_ml_h, 50.0, 3500.0)  # Physiological ceiling

    met_rate = _ACTIVITY_MET_RATES[act]

    # Description
    if sr_ml_h < 300:
        desc = "Minimal sweating. Insensible water losses dominate."
    elif sr_ml_h < 600:
        desc = "Light sweating. Standard hydration sufficient."
    elif sr_ml_h < 1200:
        desc = "Moderate sweating. Active hydration strategy needed."
    elif sr_ml_h < 2000:
        desc = "Heavy sweating. Aggressive fluid replacement required."
    else:
        desc = "Very heavy sweating. Maximum fluid replacement capacity may be exceeded."

    return SweatRateEstimate(
        sweat_rate_ml_h=round(sr_ml_h, 0),
        sweat_rate_l_h=round(sr_ml_h / 1000, 2),
        activity_level=act,
        metabolic_rate_w_m2=met_rate,
        wbgt_c=round(wbgt_c, 1),
        heat_adjustment_factor=round(heat_factor, 2),
        description=desc,
    )


# ---------------------------------------------------------------------------
# Dehydration Estimation
# ---------------------------------------------------------------------------


def estimate_dehydration(
    sweat_rate_ml_h: float,
    duration_hours: float,
    body_mass_kg: float,
    *,
    fluid_intake_ml_h: float = 0.0,
) -> DehydrationEstimate:
    """Estimate cumulative dehydration over a time period.

    Net fluid deficit = sweat loss - fluid intake.
    Body mass loss % = net deficit / (body mass * 1000) * 100.

    Dehydration categories per Cheuvront & Kenefick (2014):
    - Euhydrated: < 1% body mass loss
    - Mild: 1-2%
    - Moderate: 2-3%
    - Significant: 3-5%
    - Severe: 5-7%
    - Dangerous: > 7%

    Args:
        sweat_rate_ml_h: Sweat rate in mL/hour.
        duration_hours: Duration of exposure in hours.
        body_mass_kg: Body mass in kg.
        fluid_intake_ml_h: Voluntary fluid intake rate (mL/h).

    Returns:
        DehydrationEstimate with deficit and classification.

    Raises:
        ValueError: If inputs are not positive finite numbers.
    """
    if duration_hours < 0 or not math.isfinite(duration_hours):
        raise ValueError("duration_hours must be a non-negative finite number.")
    if body_mass_kg <= 0 or not math.isfinite(body_mass_kg):
        raise ValueError("body_mass_kg must be a positive finite number.")
    if sweat_rate_ml_h < 0 or not math.isfinite(sweat_rate_ml_h):
        raise ValueError("sweat_rate_ml_h must be non-negative and finite.")
    if fluid_intake_ml_h < 0 or not math.isfinite(fluid_intake_ml_h):
        raise ValueError("fluid_intake_ml_h must be non-negative and finite.")

    total_sweat_ml = sweat_rate_ml_h * duration_hours
    total_intake_ml = fluid_intake_ml_h * duration_hours
    net_deficit_ml = max(0.0, total_sweat_ml - total_intake_ml)
    body_mass_g = body_mass_kg * 1000.0
    bm_loss_pct = (net_deficit_ml / body_mass_g) * 100.0 if body_mass_g > 0 else 0.0

    # Classify
    if bm_loss_pct < _DEHY_THRESHOLD_MILD:
        category = "Euhydrated"
        risk = "Low"
        desc = "Adequate hydration status. No performance impact expected."
    elif bm_loss_pct < _DEHY_THRESHOLD_MODERATE:
        category = "Mild Dehydration"
        risk = "Low"
        desc = (
            "Mild dehydration (~1-2% body mass loss). Thirst mechanism activated. "
            "Minor impact on thermoregulation. Increase fluid intake."
        )
    elif bm_loss_pct < _DEHY_THRESHOLD_SIGNIFICANT:
        category = "Moderate Dehydration"
        risk = "Moderate"
        desc = (
            "Moderate dehydration (2-3% body mass loss). Measurable impairment in "
            "aerobic performance and cognitive function (Cheuvront & Kenefick, 2014). "
            "Core temperature rises ~0.1-0.23 C per 1% dehydration."
        )
    elif bm_loss_pct < _DEHY_THRESHOLD_SEVERE:
        category = "Significant Dehydration"
        risk = "High"
        desc = (
            "Significant dehydration (3-5% body mass loss). Substantial performance "
            "decrement. Elevated risk of heat illness. Reduce activity intensity "
            "and increase fluid replacement urgently."
        )
    elif bm_loss_pct < _DEHY_THRESHOLD_DANGEROUS:
        category = "Severe Dehydration"
        risk = "Very High"
        desc = (
            "Severe dehydration (5-7% body mass loss). Dangerous impairment of "
            "thermoregulation and cardiovascular function. Cease strenuous activity. "
            "Medical monitoring required."
        )
    else:
        category = "Dangerous Dehydration"
        risk = "Extreme"
        desc = (
            "Dangerous dehydration (>7% body mass loss). Life-threatening risk of "
            "heat stroke, renal failure, and cardiovascular collapse. "
            "Immediate medical intervention required."
        )

    return DehydrationEstimate(
        duration_hours=round(duration_hours, 1),
        total_sweat_loss_ml=round(total_sweat_ml, 0),
        total_sweat_loss_l=round(total_sweat_ml / 1000, 2),
        fluid_intake_ml=round(total_intake_ml, 0),
        net_fluid_deficit_ml=round(net_deficit_ml, 0),
        body_mass_loss_pct=round(bm_loss_pct, 2),
        dehydration_category=category,
        risk_level=risk,
        description=desc,
    )


# ---------------------------------------------------------------------------
# Core Temperature Prediction
# ---------------------------------------------------------------------------


def estimate_core_temperature(
    activity_level: str,
    duration_hours: float,
    wbgt_c: float = 22.0,
    dehydration_pct: float = 0.0,
    *,
    baseline_temp_c: float = 37.0,
) -> CoreTemperatureEstimate:
    """Predict core body temperature under given conditions.

    Model based on:
    - Gonzalez-Alonso et al. (1999): exercise-induced Tc rise
    - Montain & Coyle (1992): 0.15-0.23 C rise per 1% dehydration
    - Environmental heat contribution from WBGT excess

    Tc = baseline + exercise_rise + heat_rise + dehydration_rise

    Exercise rise modeled as logarithmic to capture the plateau effect
    (steady-state Tc reached within ~30-60 min of constant exercise).

    Args:
        activity_level: Activity level string.
        duration_hours: Duration of activity (h).
        wbgt_c: WBGT temperature (C).
        dehydration_pct: Current dehydration as % body mass loss.
        baseline_temp_c: Resting baseline core temperature (C).

    Returns:
        CoreTemperatureEstimate with risk classification.

    Raises:
        ValueError: If activity_level is invalid or inputs out of range.
    """
    act = activity_level.lower().strip()
    if act not in _ACTIVITY_MET_RATES:
        raise ValueError(f"Invalid activity_level '{activity_level}'.")

    if not math.isfinite(duration_hours) or duration_hours < 0:
        raise ValueError("duration_hours must be non-negative and finite.")
    if not math.isfinite(wbgt_c):
        raise ValueError("wbgt_c must be finite.")
    if not math.isfinite(dehydration_pct) or dehydration_pct < 0:
        raise ValueError("dehydration_pct must be non-negative and finite.")

    met_rate = _ACTIVITY_MET_RATES[act]

    # Exercise-induced temperature rise (logarithmic plateau model)
    # Normalized to metabolic rate: higher intensity = faster/higher rise
    # Plateau at ~90% of max rise by 1 hour
    met_normalized = (met_rate - _MET_SEDENTARY) / (_MET_VERY_HARD - _MET_SEDENTARY)
    met_normalized = _clamp(met_normalized, 0.0, 1.0)
    max_exercise_rise = met_normalized * 2.5  # Max ~2.5 C at extreme exercise
    # Logarithmic rise: Tc_rise = max * (1 - exp(-k*t))
    # k chosen so 90% of max reached at ~60 min (1 h): k = -ln(0.1)/1 ≈ 2.3
    k_exercise = 2.3
    if duration_hours > 0:
        exercise_rise = max_exercise_rise * (1.0 - math.exp(-k_exercise * duration_hours))
    else:
        exercise_rise = 0.0

    # Environmental heat contribution
    # Each degree of WBGT above thermoneutral (~22 C) adds ~0.03 C
    wbgt_excess = max(0.0, wbgt_c - 22.0)
    heat_rise = 0.03 * wbgt_excess * min(duration_hours, 3.0) / 3.0  # Gradual

    # Dehydration-induced rise (Montain & Coyle, 1992)
    # ~0.15-0.23 C per 1% body mass loss; use 0.18 as midpoint
    dehy_rise = 0.18 * dehydration_pct

    tc = baseline_temp_c + exercise_rise + heat_rise + dehy_rise
    tc = _clamp(tc, 35.0, 42.0)

    # Risk classification
    if tc < _TC_MILD_HYPER:
        risk = "Normal"
        desc = f"Core temperature ~{tc:.1f} C. Within normal physiological range."
    elif tc < _TC_MODERATE_HYPER:
        risk = "Mild Hyperthermia"
        desc = (
            f"Core temperature ~{tc:.1f} C. Mild hyperthermia. "
            "Thermoregulatory strain present. Ensure adequate hydration and ventilation."
        )
    elif tc < _TC_SEVERE_HYPER:
        risk = "Moderate Hyperthermia"
        desc = (
            f"Core temperature ~{tc:.1f} C. Moderate hyperthermia. "
            "Significant heat strain. Reduce intensity and apply active cooling."
        )
    elif tc < _TC_CRITICAL:
        risk = "Severe Hyperthermia"
        desc = (
            f"Core temperature ~{tc:.1f} C. SEVERE hyperthermia approaching heat stroke "
            "threshold. Cease all activity. Initiate emergency cooling."
        )
    else:
        risk = "Heat Stroke Risk"
        desc = (
            f"Core temperature ~{tc:.1f} C. CRITICAL: Heat stroke imminent. "
            "Immediate cold-water immersion and emergency medical care required."
        )

    return CoreTemperatureEstimate(
        core_temp_c=round(tc, 1),
        baseline_c=round(baseline_temp_c, 1),
        rise_from_exercise_c=round(exercise_rise, 2),
        rise_from_heat_stress_c=round(heat_rise, 2),
        rise_from_dehydration_c=round(dehy_rise, 2),
        risk_category=risk,
        description=desc,
    )


# ---------------------------------------------------------------------------
# Physiological Strain Index (PhSI)
# ---------------------------------------------------------------------------


def compute_physiological_strain_index(
    core_temp_c: float,
    heart_rate_bpm: float,
    *,
    baseline_temp_c: float = 37.0,
    resting_hr_bpm: float = 70.0,
    max_hr_bpm: float = 190.0,
) -> PhysiologicalStrainIndex:
    """Compute Physiological Strain Index per Moran et al. (1998).

    PhSI = 5 * (Tc - Tc0) / (39.5 - Tc0) + 5 * (HR - HR0) / (HRmax - HR0)

    Scale interpretation:
    0-3:  Low / no physiological strain
    3-5:  Low strain
    5-7:  Moderate strain
    7-9:  High strain
    9-10: Very high strain (dangerous)

    Args:
        core_temp_c: Current or estimated core temperature (C).
        heart_rate_bpm: Current heart rate (bpm).
        baseline_temp_c: Resting core temperature (C).
        resting_hr_bpm: Resting heart rate (bpm).
        max_hr_bpm: Estimated maximum heart rate (bpm).

    Returns:
        PhysiologicalStrainIndex with score and classification.
    """
    if not math.isfinite(core_temp_c) or not math.isfinite(heart_rate_bpm):
        raise ValueError("core_temp_c and heart_rate_bpm must be finite.")
    if max_hr_bpm <= resting_hr_bpm:
        raise ValueError("max_hr_bpm must be greater than resting_hr_bpm.")

    tc_denom = 39.5 - baseline_temp_c
    hr_denom = max_hr_bpm - resting_hr_bpm

    thermal = 5.0 * _clamp(core_temp_c - baseline_temp_c, 0.0, 5.0) / tc_denom
    cardio = 5.0 * _clamp(heart_rate_bpm - resting_hr_bpm, 0.0, hr_denom) / hr_denom

    phsi = _clamp(thermal + cardio, 0.0, 10.0)

    if phsi < 3.0:
        cat = "Low"
        desc = f"PhSI {phsi:.1f}/10. Minimal physiological strain."
    elif phsi < 5.0:
        cat = "Low-Moderate"
        desc = f"PhSI {phsi:.1f}/10. Low strain. Monitor hydration."
    elif phsi < 7.0:
        cat = "Moderate"
        desc = (
            f"PhSI {phsi:.1f}/10. Moderate strain. Active cooling and hydration "
            "strategies recommended."
        )
    elif phsi < 9.0:
        cat = "High"
        desc = (
            f"PhSI {phsi:.1f}/10. HIGH physiological strain. Reduce work intensity. "
            "Consider work-rest cycling."
        )
    else:
        cat = "Very High"
        desc = (
            f"PhSI {phsi:.1f}/10. VERY HIGH strain. Stop activity immediately. "
            "Risk of heat-related illness."
        )

    return PhysiologicalStrainIndex(
        phsi_value=round(phsi, 1),
        thermal_component=round(thermal, 2),
        cardiovascular_component=round(cardio, 2),
        strain_category=cat,
        description=desc,
    )


# ---------------------------------------------------------------------------
# Performance Decrement from Dehydration
# ---------------------------------------------------------------------------


def compute_performance_decrement(
    dehydration_pct: float,
    *,
    heat_stress: bool = False,
) -> PerformanceDecrement:
    """Compute cognitive and physical performance impact of dehydration.

    Based on meta-analysis by Cheuvront & Kenefick (2014) and
    Sawka et al. (2015):

    Aerobic performance (endurance):
    - Decrements begin at ~2% body mass loss
    - ~3-5% decrement per 1% loss beyond 2%
    - Heat stress amplifies the effect by ~50%

    Cognitive performance:
    - Measurable impairment at >= 2% body mass loss
    - Executive function and attention most affected
    - ~2-4% decrement per 1% loss beyond 1%

    Strength/power:
    - Relatively preserved until >= 3-4% loss
    - ~2-3% decrement per 1% loss beyond 3%

    Args:
        dehydration_pct: Body mass loss as percentage.
        heat_stress: Whether heat stress is present (WBGT >= 28 C).

    Returns:
        PerformanceDecrement with per-domain and overall performance.
    """
    d = _clamp(dehydration_pct, 0.0, 15.0)
    heat_mult = 1.5 if heat_stress else 1.0

    # Aerobic performance (endurance)
    if d <= 1.0:
        aero_loss = 0.0
    elif d <= 2.0:
        aero_loss = (d - 1.0) * 2.0 * heat_mult
    else:
        aero_loss = (1.0 * 2.0 + (d - 2.0) * 4.5) * heat_mult
    aerobic_pct = _clamp(100.0 - aero_loss, 40.0, 100.0)

    # Cognitive performance
    if d <= 1.0:
        cog_loss = d * 1.0
    elif d <= 2.0:
        cog_loss = 1.0 + (d - 1.0) * 2.5
    else:
        cog_loss = 3.5 + (d - 2.0) * 4.0
    cognitive_pct = _clamp(100.0 - cog_loss * heat_mult, 45.0, 100.0)

    # Strength/power performance
    if d <= 3.0:
        str_loss = d * 0.5
    else:
        str_loss = 1.5 + (d - 3.0) * 3.0
    strength_pct = _clamp(100.0 - str_loss * heat_mult, 50.0, 100.0)

    # Overall weighted (aerobic 40%, cognitive 35%, strength 25%)
    overall_pct = 0.40 * aerobic_pct + 0.35 * cognitive_pct + 0.25 * strength_pct
    overall_pct = round(_clamp(overall_pct, 40.0, 100.0), 1)

    # Readiness modifier for IHPI (bounded -10 to 0)
    deficit = 100.0 - overall_pct
    modifier = -min(10.0, deficit * 0.2)
    modifier = round(_clamp(modifier, -10.0, 0.0), 1)

    # Risk level
    if d < _DEHY_THRESHOLD_MILD:
        risk = "Low"
    elif d < _DEHY_THRESHOLD_MODERATE:
        risk = "Low"
    elif d < _DEHY_THRESHOLD_SIGNIFICANT:
        risk = "Moderate"
    elif d < _DEHY_THRESHOLD_SEVERE:
        risk = "High"
    else:
        risk = "Very High"

    # Description
    if d < 1.0:
        desc = "Euhydrated. No meaningful performance impact."
    elif d < 2.0:
        desc = (
            "Mild dehydration. Minimal performance impact but thirst present. "
            "Proactive hydration recommended."
        )
    elif d < 3.0:
        desc = (
            f"Moderate dehydration ({d:.1f}% BM loss). Aerobic capacity reduced by "
            f"~{100.0 - aerobic_pct:.0f}%. Cognitive impairment measurable. "
            "ACSM recommends limiting body mass loss to <2% during exercise."
        )
    elif d < 5.0:
        desc = (
            f"Significant dehydration ({d:.1f}% BM loss). Substantial performance "
            f"decrement: aerobic ~{100.0 - aerobic_pct:.0f}%, cognitive ~{100.0 - cognitive_pct:.0f}%. "
            "Elevated heat illness risk. Reduce intensity immediately."
        )
    else:
        desc = (
            f"Severe dehydration ({d:.1f}% BM loss). Dangerous performance impairment. "
            "Thermoregulatory failure risk. Cease activity and initiate fluid resuscitation."
        )

    # Recommendations
    recs: list[str] = []
    if d < 1.0:
        recs.append("Maintain current hydration strategy.")
        recs.append("Drink 150-250 mL every 15-20 min during activity.")
    elif d < 2.0:
        recs.append("Increase fluid intake to 200-300 mL every 15-20 min.")
        recs.append("Add electrolytes if exercising >60 min in heat.")
        recs.append("Monitor urine color (target: pale yellow).")
    elif d < 3.0:
        recs.append("Urgently increase fluid intake to 300-400 mL every 15 min.")
        recs.append("Reduce exercise intensity.")
        recs.append("Seek shade or cooled environment.")
        recs.append("Sports drinks with 4-8% carbohydrate and sodium recommended.")
    else:
        recs.append("STOP strenuous activity immediately.")
        recs.append("Begin oral rehydration with electrolyte solution.")
        recs.append("Cool the body: remove excess clothing, apply cold water/ice.")
        recs.append("Seek medical evaluation if symptoms persist.")
        recs.append("Rehydrate at 1.5x fluid deficit over 2-4 hours.")

    return PerformanceDecrement(
        dehydration_pct=round(d, 2),
        aerobic_performance_pct=round(aerobic_pct, 1),
        cognitive_performance_pct=round(cognitive_pct, 1),
        strength_performance_pct=round(strength_pct, 1),
        overall_performance_pct=overall_pct,
        readiness_modifier=modifier,
        risk_level=risk,
        description=desc,
        recommendations=tuple(recs),
    )


# ---------------------------------------------------------------------------
# Comprehensive Assessment
# ---------------------------------------------------------------------------


def compute_hydration_thermoregulation_assessment(
    activity_level: str = "moderate",
    duration_hours: float = 1.0,
    wbgt_c: float = 22.0,
    body_mass_kg: float = 70.0,
    *,
    fluid_intake_ml_h: float = 0.0,
    acclimatized: bool = True,
    heart_rate_bpm: float = 120.0,
    resting_hr_bpm: float = 70.0,
    age_years: int = 35,
    baseline_temp_c: float = 37.0,
) -> HydrationThermoregulationAssessment:
    """Compute comprehensive hydration and thermoregulation assessment.

    Integrates sweat rate, dehydration, core temperature, PhSI, and
    performance decrement into a single operational assessment.

    Args:
        activity_level: Activity level string.
        duration_hours: Duration of activity (hours).
        wbgt_c: WBGT temperature (C). Use ~22 for thermoneutral.
        body_mass_kg: Body mass (kg).
        fluid_intake_ml_h: Voluntary fluid intake (mL/h).
        acclimatized: Heat acclimatization status.
        heart_rate_bpm: Current or expected heart rate (bpm).
        resting_hr_bpm: Resting heart rate (bpm).
        age_years: Age in years (for max HR estimation).
        baseline_temp_c: Resting core temperature (C).

    Returns:
        HydrationThermoregulationAssessment with all sub-models.
    """
    # Validate critical inputs
    if duration_hours < 0 or not math.isfinite(duration_hours):
        raise ValueError("duration_hours must be non-negative and finite.")
    if body_mass_kg <= 0 or not math.isfinite(body_mass_kg):
        raise ValueError("body_mass_kg must be positive and finite.")

    # 1. Sweat rate
    sr = estimate_sweat_rate(
        activity_level=activity_level,
        wbgt_c=wbgt_c,
        body_mass_kg=body_mass_kg,
        acclimatized=acclimatized,
    )

    # 2. Dehydration
    dehy = estimate_dehydration(
        sweat_rate_ml_h=sr.sweat_rate_ml_h,
        duration_hours=duration_hours,
        body_mass_kg=body_mass_kg,
        fluid_intake_ml_h=fluid_intake_ml_h,
    )

    # 3. Core temperature
    tc = estimate_core_temperature(
        activity_level=activity_level,
        duration_hours=duration_hours,
        wbgt_c=wbgt_c,
        dehydration_pct=dehy.body_mass_loss_pct,
        baseline_temp_c=baseline_temp_c,
    )

    # 4. Physiological Strain Index
    max_hr = max(180.0, 220.0 - float(age_years))
    phsi = compute_physiological_strain_index(
        core_temp_c=tc.core_temp_c,
        heart_rate_bpm=heart_rate_bpm,
        baseline_temp_c=baseline_temp_c,
        resting_hr_bpm=resting_hr_bpm,
        max_hr_bpm=max_hr,
    )

    # 5. Performance decrement
    heat_stress_active = wbgt_c >= 28.0
    perf = compute_performance_decrement(
        dehydration_pct=dehy.body_mass_loss_pct,
        heat_stress=heat_stress_active,
    )

    # 6. Fluid replacement recommendation
    # ACSM: replace ~80% of sweat rate to limit dehydration to <2% BM loss
    fluid_rec_ml_h = round(sr.sweat_rate_ml_h * 0.80, 0)
    # Cap at ~1.2 L/h (gastric emptying limit, Sawka et al. 2007)
    fluid_rec_ml_h = min(fluid_rec_ml_h, 1200.0)

    # 7. Composite readiness modifier (most conservative of sub-models)
    readiness_mod = perf.readiness_modifier
    # Additional penalty from PhSI if high strain
    if phsi.phsi_value >= 7.0:
        phsi_penalty = -min(3.0, (phsi.phsi_value - 7.0) * 1.5)
        readiness_mod = max(-10.0, readiness_mod + phsi_penalty)
    readiness_mod = round(_clamp(readiness_mod, -10.0, 0.0), 1)

    # 8. Overall heat stress category
    if wbgt_c < 25.0 and dehy.body_mass_loss_pct < 1.0:
        heat_cat = "Low"
    elif wbgt_c < 28.0 and dehy.body_mass_loss_pct < 2.0:
        heat_cat = "Moderate"
    elif wbgt_c < 30.0 or dehy.body_mass_loss_pct < 3.0:
        heat_cat = "High"
    elif wbgt_c < 33.0 or dehy.body_mass_loss_pct < 5.0:
        heat_cat = "Very High"
    else:
        heat_cat = "Extreme"

    # 9. Hydration status label
    if dehy.body_mass_loss_pct < 1.0:
        hydration_status = "Well Hydrated"
    elif dehy.body_mass_loss_pct < 2.0:
        hydration_status = "Mildly Dehydrated"
    elif dehy.body_mass_loss_pct < 3.0:
        hydration_status = "Moderately Dehydrated"
    elif dehy.body_mass_loss_pct < 5.0:
        hydration_status = "Significantly Dehydrated"
    else:
        hydration_status = "Severely Dehydrated"

    # 10. Operational guidance
    guidance_parts: list[str] = []
    guidance_parts.append(f"Fluid replacement: {fluid_rec_ml_h:.0f} mL/h.")
    if heat_stress_active:
        guidance_parts.append("Heat stress active: enforce work-rest cycles.")
    if dehy.body_mass_loss_pct >= 2.0:
        guidance_parts.append("Dehydration exceeds 2% BM — reduce activity intensity.")
    if tc.core_temp_c >= 39.0:
        guidance_parts.append("Core temp elevated: initiate active cooling.")
    if phsi.phsi_value >= 7.0:
        guidance_parts.append("High physiological strain — consider activity cessation.")

    return HydrationThermoregulationAssessment(
        sweat_rate=sr,
        dehydration=dehy,
        core_temp=tc,
        phsi=phsi,
        performance=perf,
        fluid_replacement_ml_h=fluid_rec_ml_h,
        readiness_modifier=readiness_mod,
        heat_stress_category=heat_cat,
        hydration_status=hydration_status,
        operational_guidance=" ".join(guidance_parts),
    )


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Data classes
    "SweatRateEstimate",
    "DehydrationEstimate",
    "CoreTemperatureEstimate",
    "PhysiologicalStrainIndex",
    "PerformanceDecrement",
    "HydrationThermoregulationAssessment",
    # Functions
    "estimate_sweat_rate",
    "estimate_dehydration",
    "estimate_core_temperature",
    "compute_physiological_strain_index",
    "compute_performance_decrement",
    "compute_hydration_thermoregulation_assessment",
]
