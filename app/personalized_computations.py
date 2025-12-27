"""
Personalized Computations Module for Mission Control - Flight Surgeon.

Provides user-specific physiological calculations based on individual profile data:
- Body fat estimation (US Navy method using neck/waist/hip circumferences)
- Sleep apnea risk assessment (STOP-BANG score components)
- Personalized HRV reference ranges (age/sex-adjusted)
- Cardiovascular risk factors
- Fitness classification based on VO2max
- Hydration requirements based on body weight and activity
- Thermoregulatory capacity estimates

Scientific References:
- US Navy Body Fat: Hodgdon JA, Beckett MB. Naval Health Research Center, 1984
- STOP-BANG Sleep Apnea: Chung F et al. Anesthesiology 2008;108:812-21
- HRV Norms: Nunan D et al. PACE 2010;33:1407-17
- HRV Age Norms: Shaffer F, Ginsberg JP. Front Public Health 2017;5:258
- VO2max Classification: ACSM Guidelines for Exercise Testing, 11th Ed

Author: Dr. Diego Leonel Malpica Hincapié, MD
Version: 1.0.0
"""

from __future__ import annotations

import logging
import math
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, Final, List, Optional, Tuple

# Ensure module is properly registered in sys.modules before dataclass decorators run
# This fixes AttributeError: 'NoneType' object has no attribute '__dict__'
# when using from __future__ import annotations with dataclasses in Python 3.12
# The dataclass decorator needs the module to be in sys.modules to resolve annotations
# Workaround: Ensure the module reference exists before dataclass decorators are processed
if __name__ not in sys.modules or sys.modules[__name__] is None:
    import types
    # Only create if it doesn't exist or is None
    # This ensures dataclass decorator can find the module
    if __name__ not in sys.modules:
        sys.modules[__name__] = types.ModuleType(__name__)
    elif sys.modules[__name__] is None:
        sys.modules[__name__] = types.ModuleType(__name__)

try:
    from logging_config import get_logger
except ImportError:
    get_logger = None  # type: ignore[assignment]

_LOGGER: Final[logging.Logger] = (
    get_logger(__name__) if get_logger is not None else logging.getLogger(__name__)
)


# ---------------------------------------------------------------------------
# Enums and Constants
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
    UNKNOWN = "unknown"


class FitnessCategory(str, Enum):
    """Cardiorespiratory fitness classification based on VO2max."""
    VERY_POOR = "very_poor"
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"
    SUPERIOR = "superior"


class BodyFatCategory(str, Enum):
    """Body fat percentage classification."""
    ESSENTIAL = "essential_fat"
    ATHLETES = "athletes"
    FITNESS = "fitness"
    AVERAGE = "average"
    OBESE = "obese"


# Age-adjusted HRV reference ranges (Nunan et al. 2010, Shaffer & Ginsberg 2017)
# Format: {age_group: {"metric": (mean, sd, percentile_5, percentile_95)}}
HRV_NORMS_BY_AGE: Dict[str, Dict[str, Tuple[float, float, float, float]]] = {
    "20-29": {
        "rmssd_ms": (42.0, 15.0, 19.0, 75.0),
        "sdnn_ms": (50.0, 16.0, 25.0, 85.0),
        "pnn50_pct": (18.0, 12.0, 2.0, 45.0),
        "hf_power_ms2": (975.0, 400.0, 300.0, 2000.0),
        "lf_power_ms2": (1170.0, 480.0, 450.0, 2400.0),
        "lf_hf_ratio": (1.5, 0.7, 0.5, 3.0),
    },
    "30-39": {
        "rmssd_ms": (35.0, 13.0, 15.0, 65.0),
        "sdnn_ms": (45.0, 14.0, 22.0, 75.0),
        "pnn50_pct": (14.0, 10.0, 1.5, 38.0),
        "hf_power_ms2": (755.0, 350.0, 200.0, 1600.0),
        "lf_power_ms2": (1050.0, 420.0, 380.0, 2000.0),
        "lf_hf_ratio": (1.8, 0.8, 0.6, 3.5),
    },
    "40-49": {
        "rmssd_ms": (30.0, 12.0, 12.0, 55.0),
        "sdnn_ms": (40.0, 12.0, 20.0, 65.0),
        "pnn50_pct": (10.0, 8.0, 1.0, 30.0),
        "hf_power_ms2": (560.0, 280.0, 150.0, 1200.0),
        "lf_power_ms2": (900.0, 380.0, 320.0, 1700.0),
        "lf_hf_ratio": (2.0, 0.9, 0.7, 4.0),
    },
    "50-59": {
        "rmssd_ms": (25.0, 10.0, 10.0, 45.0),
        "sdnn_ms": (35.0, 11.0, 18.0, 58.0),
        "pnn50_pct": (7.0, 6.0, 0.5, 22.0),
        "hf_power_ms2": (400.0, 220.0, 100.0, 900.0),
        "lf_power_ms2": (750.0, 340.0, 280.0, 1450.0),
        "lf_hf_ratio": (2.2, 1.0, 0.8, 4.5),
    },
    "60-69": {
        "rmssd_ms": (22.0, 9.0, 8.0, 40.0),
        "sdnn_ms": (32.0, 10.0, 16.0, 52.0),
        "pnn50_pct": (5.0, 5.0, 0.3, 18.0),
        "hf_power_ms2": (280.0, 180.0, 60.0, 700.0),
        "lf_power_ms2": (600.0, 300.0, 200.0, 1250.0),
        "lf_hf_ratio": (2.5, 1.1, 0.9, 5.0),
    },
    "70+": {
        "rmssd_ms": (20.0, 8.0, 7.0, 35.0),
        "sdnn_ms": (28.0, 9.0, 14.0, 46.0),
        "pnn50_pct": (4.0, 4.0, 0.2, 14.0),
        "hf_power_ms2": (200.0, 150.0, 40.0, 550.0),
        "lf_power_ms2": (480.0, 260.0, 150.0, 1050.0),
        "lf_hf_ratio": (2.8, 1.2, 1.0, 5.5),
    },
}

# VO2max classification by age and sex (ACSM Guidelines)
# Format: {sex: {age_group: (very_poor, poor, fair, good, excellent, superior)}}
VO2MAX_CLASSIFICATION: Dict[str, Dict[str, Tuple[float, float, float, float, float, float]]] = {
    "male": {
        "20-29": (24.9, 33.0, 36.5, 42.4, 46.5, 52.4),
        "30-39": (22.9, 31.0, 35.5, 40.0, 44.0, 49.4),
        "40-49": (19.9, 27.0, 32.0, 36.5, 40.0, 44.9),
        "50-59": (17.9, 24.0, 28.5, 33.0, 36.5, 41.0),
        "60-69": (15.9, 21.0, 25.5, 30.0, 33.0, 37.0),
        "70+": (13.9, 18.0, 22.0, 26.0, 29.5, 33.0),
    },
    "female": {
        "20-29": (23.5, 29.0, 33.0, 37.0, 41.0, 46.0),
        "30-39": (22.0, 27.5, 31.5, 35.5, 39.0, 44.0),
        "40-49": (20.0, 25.0, 28.5, 32.5, 36.0, 40.5),
        "50-59": (17.5, 22.0, 25.5, 29.5, 32.5, 37.0),
        "60-69": (15.5, 19.5, 22.5, 26.5, 29.5, 33.5),
        "70+": (13.5, 17.0, 20.0, 23.5, 26.5, 30.0),
    },
}

# Body fat percentage ranges by sex (ACSM Guidelines)
BODY_FAT_RANGES: Dict[str, Dict[str, Tuple[float, float]]] = {
    "male": {
        "essential": (2.0, 5.0),
        "athletes": (6.0, 13.0),
        "fitness": (14.0, 17.0),
        "average": (18.0, 24.0),
        "obese": (25.0, 100.0),
    },
    "female": {
        "essential": (10.0, 13.0),
        "athletes": (14.0, 20.0),
        "fitness": (21.0, 24.0),
        "average": (25.0, 31.0),
        "obese": (32.0, 100.0),
    },
}


# ---------------------------------------------------------------------------
# Data Classes for Personalized Results
# ---------------------------------------------------------------------------

@dataclass
class BodyFatEstimate:
    """Body fat estimation result using US Navy method."""
    
    body_fat_pct: float
    lean_mass_kg: float
    fat_mass_kg: float
    category: BodyFatCategory
    category_label: str
    method: str = "US Navy (Hodgdon & Beckett, 1984)"
    inputs_used: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "body_fat_pct": round(self.body_fat_pct, 1),
            "lean_mass_kg": round(self.lean_mass_kg, 1),
            "fat_mass_kg": round(self.fat_mass_kg, 1),
            "category": self.category.value,
            "category_label": self.category_label,
            "method": self.method,
            "inputs_used": self.inputs_used,
        }


@dataclass
class SleepApneaRisk:
    """Sleep apnea risk assessment using STOP-BANG components."""
    
    total_score: int
    risk_level: RiskLevel
    risk_label: str
    risk_factors: List[str]
    recommendations: List[str]
    components: Dict[str, bool] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_score": self.total_score,
            "risk_level": self.risk_level.value,
            "risk_label": self.risk_label,
            "risk_factors": self.risk_factors,
            "recommendations": self.recommendations,
            "components": self.components,
        }


@dataclass
class PersonalizedHRVNorms:
    """Age/sex-adjusted HRV reference ranges for a specific user."""
    
    age_group: str
    sex: str
    metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    reference: str = "Nunan et al. PACE 2010; Shaffer & Ginsberg 2017"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "age_group": self.age_group,
            "sex": self.sex,
            "metrics": self.metrics,
            "reference": self.reference,
        }


@dataclass
class FitnessClassification:
    """VO2max-based fitness classification."""
    
    vo2max: float
    category: FitnessCategory
    category_label: str
    percentile_estimate: int
    age_group: str
    sex: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "vo2max_ml_kg_min": round(self.vo2max, 1),
            "category": self.category.value,
            "category_label": self.category_label,
            "percentile_estimate": self.percentile_estimate,
            "age_group": self.age_group,
            "sex": self.sex,
        }


@dataclass
class CardiovascularRiskProfile:
    """Comprehensive cardiovascular risk profile."""
    
    risk_factors: List[str]
    protective_factors: List[str]
    risk_level: RiskLevel
    recommendations: List[str]
    framingham_inputs: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "risk_factors": self.risk_factors,
            "protective_factors": self.protective_factors,
            "risk_level": self.risk_level.value,
            "recommendations": self.recommendations,
            "framingham_inputs": self.framingham_inputs,
        }


@dataclass
class HydrationRequirements:
    """Personalized hydration requirements."""
    
    base_ml: float
    activity_adjusted_ml: float
    total_ml: float
    glasses_8oz: int
    liters: float
    factors: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "base_ml": round(self.base_ml, 0),
            "activity_adjusted_ml": round(self.activity_adjusted_ml, 0),
            "total_ml": round(self.total_ml, 0),
            "glasses_8oz": self.glasses_8oz,
            "liters": round(self.liters, 2),
            "factors": self.factors,
        }


# ---------------------------------------------------------------------------
# Calculation Functions
# ---------------------------------------------------------------------------

def _get_age_group(age: int) -> str:
    """Get age group string for reference tables."""
    if age < 20:
        return "20-29"  # Use youngest adult group
    elif age < 30:
        return "20-29"
    elif age < 40:
        return "30-39"
    elif age < 50:
        return "40-49"
    elif age < 60:
        return "50-59"
    elif age < 70:
        return "60-69"
    else:
        return "70+"


def calculate_body_fat_navy(
    weight_kg: float,
    height_cm: float,
    waist_cm: float,
    neck_cm: float,
    sex: str,
    hip_cm: Optional[float] = None,
) -> Optional[BodyFatEstimate]:
    """
    Calculate body fat percentage using US Navy method.
    
    Reference: Hodgdon JA, Beckett MB. Naval Health Research Center, 1984
    
    Male formula:
        BF% = 495 / (1.0324 - 0.19077 * log10(waist - neck) + 0.15456 * log10(height)) - 450
    
    Female formula:
        BF% = 495 / (1.29579 - 0.35004 * log10(waist + hip - neck) + 0.22100 * log10(height)) - 450
    
    Args:
        weight_kg: Body weight in kilograms
        height_cm: Height in centimeters
        waist_cm: Waist circumference in centimeters (at navel for males, narrowest for females)
        neck_cm: Neck circumference in centimeters (below larynx)
        sex: Biological sex ("male" or "female")
        hip_cm: Hip circumference in centimeters (required for females)
        
    Returns:
        BodyFatEstimate dataclass or None if inputs are invalid
    """
    # Validate inputs
    if not all([weight_kg > 0, height_cm > 0, waist_cm > 0, neck_cm > 0]):
        _LOGGER.warning("Invalid inputs for body fat calculation")
        return None
    
    sex_lower = sex.lower() if sex else "male"
    
    if sex_lower == "female" and not hip_cm:
        _LOGGER.warning("Hip measurement required for female body fat calculation")
        return None
    
    inputs_used = {
        "weight_kg": weight_kg,
        "height_cm": height_cm,
        "waist_cm": waist_cm,
        "neck_cm": neck_cm,
        "sex": sex_lower,
    }
    if hip_cm:
        inputs_used["hip_cm"] = hip_cm
    
    try:
        if sex_lower == "male":
            # Male formula
            if waist_cm <= neck_cm:
                _LOGGER.warning("Invalid: waist must be greater than neck circumference")
                return None
            bf_pct = 495 / (
                1.0324 - 0.19077 * math.log10(waist_cm - neck_cm)
                + 0.15456 * math.log10(height_cm)
            ) - 450
        else:
            # Female formula
            hip_value = hip_cm or waist_cm
            combined = waist_cm + hip_value - neck_cm
            if combined <= 0:
                _LOGGER.warning("Invalid circumference combination for female calculation")
                return None
            bf_pct = 495 / (
                1.29579 - 0.35004 * math.log10(combined)
                + 0.22100 * math.log10(height_cm)
            ) - 450
        
        # Clamp to valid range
        bf_pct = max(2.0, min(60.0, bf_pct))
        
        # Calculate fat and lean mass
        fat_mass_kg = weight_kg * (bf_pct / 100)
        lean_mass_kg = weight_kg - fat_mass_kg
        
        # Classify body fat category
        ranges = BODY_FAT_RANGES.get(sex_lower, BODY_FAT_RANGES["male"])
        
        if bf_pct < ranges["essential"][1]:
            category = BodyFatCategory.ESSENTIAL
            label = "Essential Fat (dangerously low)"
        elif bf_pct <= ranges["athletes"][1]:
            category = BodyFatCategory.ATHLETES
            label = "Athletes Range"
        elif bf_pct <= ranges["fitness"][1]:
            category = BodyFatCategory.FITNESS
            label = "Fitness Range"
        elif bf_pct <= ranges["average"][1]:
            category = BodyFatCategory.AVERAGE
            label = "Average Range"
        else:
            category = BodyFatCategory.OBESE
            label = "Obese Range"
        
        return BodyFatEstimate(
            body_fat_pct=bf_pct,
            lean_mass_kg=lean_mass_kg,
            fat_mass_kg=fat_mass_kg,
            category=category,
            category_label=label,
            inputs_used=inputs_used,
        )
        
    except (ValueError, ZeroDivisionError) as exc:
        _LOGGER.warning("Body fat calculation error: %s", exc)
        return None


def calculate_sleep_apnea_risk(
    sex: str,
    age: int,
    bmi: Optional[float] = None,
    neck_cm: Optional[float] = None,
    snoring: Optional[bool] = None,
    tiredness: Optional[bool] = None,
    observed_apnea: Optional[bool] = None,
    high_blood_pressure: Optional[bool] = None,
) -> SleepApneaRisk:
    """
    Calculate sleep apnea risk using STOP-BANG questionnaire components.
    
    Reference: Chung F et al. Anesthesiology 2008;108:812-21
    
    STOP-BANG Components:
    S - Snoring (loud, heard through closed doors)
    T - Tiredness (daytime fatigue/sleepiness)
    O - Observed apnea (witnessed breathing stops during sleep)
    P - Pressure (high blood pressure, treated or untreated)
    B - BMI > 35 kg/m²
    A - Age > 50 years
    N - Neck circumference > 40 cm (male) or > 38 cm (female)
    G - Gender (male)
    
    Scoring:
    - 0-2: Low risk
    - 3-4: Intermediate risk  
    - 5-8: High risk (especially if ≥2 of B-A-N-G)
    
    Args:
        sex: Biological sex ("male" or "female")
        age: Age in years
        bmi: Body mass index (kg/m²)
        neck_cm: Neck circumference in centimeters
        snoring: Loud snoring
        tiredness: Daytime fatigue/sleepiness
        observed_apnea: Witnessed apnea episodes
        high_blood_pressure: Hypertension
        
    Returns:
        SleepApneaRisk dataclass with score and recommendations
    """
    score = 0
    risk_factors: List[str] = []
    components: Dict[str, bool] = {}
    sex_lower = sex.lower() if sex else "male"
    
    # S - Snoring
    if snoring is True:
        score += 1
        risk_factors.append("Loud snoring")
        components["snoring"] = True
    else:
        components["snoring"] = snoring or False
    
    # T - Tiredness
    if tiredness is True:
        score += 1
        risk_factors.append("Daytime fatigue/sleepiness")
        components["tiredness"] = True
    else:
        components["tiredness"] = tiredness or False
    
    # O - Observed apnea
    if observed_apnea is True:
        score += 1
        risk_factors.append("Witnessed apnea episodes")
        components["observed_apnea"] = True
    else:
        components["observed_apnea"] = observed_apnea or False
    
    # P - Pressure (hypertension)
    if high_blood_pressure is True:
        score += 1
        risk_factors.append("Hypertension")
        components["high_blood_pressure"] = True
    else:
        components["high_blood_pressure"] = high_blood_pressure or False
    
    # B - BMI > 35
    if bmi is not None and bmi > 35:
        score += 1
        risk_factors.append(f"BMI > 35 ({bmi:.1f} kg/m²)")
        components["bmi_elevated"] = True
    else:
        components["bmi_elevated"] = False
    
    # A - Age > 50
    if age > 50:
        score += 1
        risk_factors.append(f"Age > 50 ({age} years)")
        components["age_over_50"] = True
    else:
        components["age_over_50"] = False
    
    # N - Neck circumference
    neck_threshold = 40.0 if sex_lower == "male" else 38.0
    if neck_cm is not None and neck_cm > neck_threshold:
        score += 1
        risk_factors.append(f"Neck circumference > {neck_threshold:.0f} cm ({neck_cm:.1f} cm)")
        components["neck_enlarged"] = True
    else:
        components["neck_enlarged"] = False
    
    # G - Gender (male)
    if sex_lower == "male":
        score += 1
        risk_factors.append("Male sex")
        components["male_sex"] = True
    else:
        components["male_sex"] = False
    
    # Determine risk level
    if score <= 2:
        risk_level = RiskLevel.LOW
        risk_label = "Low risk of OSA"
        recommendations = [
            "Continue healthy sleep habits",
            "Maintain regular sleep schedule",
            "Consider sleep position adjustments if snoring occurs",
        ]
    elif score <= 4:
        risk_level = RiskLevel.MODERATE
        risk_label = "Intermediate risk of OSA"
        recommendations = [
            "Consider clinical evaluation for sleep apnea",
            "Discuss symptoms with healthcare provider",
            "Monitor for worsening symptoms",
            "Weight management if BMI elevated",
            "Avoid alcohol and sedatives before sleep",
        ]
    else:
        risk_level = RiskLevel.HIGH
        risk_label = "High risk of OSA"
        recommendations = [
            "Strongly recommend sleep study (polysomnography)",
            "Consult sleep medicine specialist",
            "Evaluate for CPAP therapy",
            "Cardiac evaluation recommended",
            "Weight loss program if BMI elevated",
            "Avoid supine sleeping position",
        ]
    
    return SleepApneaRisk(
        total_score=score,
        risk_level=risk_level,
        risk_label=risk_label,
        risk_factors=risk_factors,
        recommendations=recommendations,
        components=components,
    )


def get_personalized_hrv_norms(
    age: int,
    sex: str,
) -> PersonalizedHRVNorms:
    """
    Get age/sex-adjusted HRV reference ranges.
    
    References:
    - Nunan D et al. PACE 2010;33:1407-17
    - Shaffer F, Ginsberg JP. Front Public Health 2017;5:258
    
    Args:
        age: Age in years
        sex: Biological sex ("male" or "female")
        
    Returns:
        PersonalizedHRVNorms with age-appropriate reference values
    """
    age_group = _get_age_group(age)
    sex_lower = sex.lower() if sex else "male"
    
    norms = HRV_NORMS_BY_AGE.get(age_group, HRV_NORMS_BY_AGE["40-49"])
    
    metrics: Dict[str, Dict[str, float]] = {}
    for metric_name, (mean, sd, p5, p95) in norms.items():
        metrics[metric_name] = {
            "mean": mean,
            "sd": sd,
            "percentile_5": p5,
            "percentile_95": p95,
            "low_threshold": mean - sd,
            "high_threshold": mean + sd,
            "very_low_threshold": mean - 2 * sd,
            "very_high_threshold": mean + 2 * sd,
        }
    
    return PersonalizedHRVNorms(
        age_group=age_group,
        sex=sex_lower,
        metrics=metrics,
    )


def interpret_hrv_metric_personalized(
    metric_name: str,
    value: float,
    hrv_norms: PersonalizedHRVNorms,
) -> Dict[str, Any]:
    """
    Interpret an HRV metric value against personalized norms.
    
    Args:
        metric_name: Name of the HRV metric (e.g., "rmssd_ms", "sdnn_ms")
        value: The measured value
        hrv_norms: Personalized norms for the user
        
    Returns:
        Dictionary with interpretation details
    """
    metric_norms = hrv_norms.metrics.get(metric_name)
    
    if metric_norms is None:
        return {
            "value": value,
            "status": "unknown",
            "interpretation": "No reference range available for this metric",
            "percentile_estimate": None,
        }
    
    mean = metric_norms["mean"]
    sd = metric_norms["sd"]
    p5 = metric_norms["percentile_5"]
    p95 = metric_norms["percentile_95"]
    
    # Calculate z-score
    z_score = (value - mean) / sd if sd > 0 else 0
    
    # Estimate percentile based on z-score (assuming normal distribution)
    from math import erf, sqrt
    percentile = int(50 * (1 + erf(z_score / sqrt(2))))
    percentile = max(1, min(99, percentile))
    
    # Determine status
    if value < metric_norms["very_low_threshold"]:
        status = "very_low"
        interpretation = f"Significantly below normal for age {hrv_norms.age_group}"
    elif value < metric_norms["low_threshold"]:
        status = "low"
        interpretation = f"Below normal for age {hrv_norms.age_group}"
    elif value > metric_norms["very_high_threshold"]:
        status = "very_high"
        interpretation = f"Significantly above normal for age {hrv_norms.age_group}"
    elif value > metric_norms["high_threshold"]:
        status = "high"
        interpretation = f"Above normal for age {hrv_norms.age_group}"
    else:
        status = "normal"
        interpretation = f"Within normal range for age {hrv_norms.age_group}"
    
    return {
        "value": round(value, 2),
        "status": status,
        "interpretation": interpretation,
        "percentile_estimate": percentile,
        "z_score": round(z_score, 2),
        "reference_mean": mean,
        "reference_sd": sd,
        "reference_range": f"{p5:.1f} - {p95:.1f}",
        "age_group": hrv_norms.age_group,
    }


def classify_fitness_by_vo2max(
    vo2max: float,
    age: int,
    sex: str,
) -> FitnessClassification:
    """
    Classify cardiorespiratory fitness based on VO2max.
    
    Reference: ACSM's Guidelines for Exercise Testing and Prescription, 11th Ed.
    
    Args:
        vo2max: VO2max in mL/kg/min
        age: Age in years
        sex: Biological sex ("male" or "female")
        
    Returns:
        FitnessClassification dataclass
    """
    age_group = _get_age_group(age)
    sex_lower = sex.lower() if sex else "male"
    
    # Get thresholds for age and sex
    sex_key = sex_lower if sex_lower in VO2MAX_CLASSIFICATION else "male"
    thresholds = VO2MAX_CLASSIFICATION[sex_key].get(
        age_group, VO2MAX_CLASSIFICATION[sex_key]["40-49"]
    )
    
    very_poor, poor, fair, good, excellent, superior = thresholds
    
    # Classify
    if vo2max < very_poor:
        category = FitnessCategory.VERY_POOR
        label = "Very Poor"
        percentile = 5
    elif vo2max < poor:
        category = FitnessCategory.POOR
        label = "Poor"
        percentile = 15
    elif vo2max < fair:
        category = FitnessCategory.FAIR
        label = "Fair"
        percentile = 35
    elif vo2max < good:
        category = FitnessCategory.GOOD
        label = "Good"
        percentile = 55
    elif vo2max < excellent:
        category = FitnessCategory.EXCELLENT
        label = "Excellent"
        percentile = 75
    else:
        category = FitnessCategory.SUPERIOR
        label = "Superior"
        percentile = 95
    
    return FitnessClassification(
        vo2max=vo2max,
        category=category,
        category_label=label,
        percentile_estimate=percentile,
        age_group=age_group,
        sex=sex_lower,
    )


def calculate_personalized_hydration(
    weight_kg: float,
    activity_level: str = "moderate",
    exercise_minutes: int = 0,
    hot_environment: bool = False,
    altitude_m: int = 0,
) -> HydrationRequirements:
    """
    Calculate personalized daily hydration requirements.
    
    Reference: NASA-STD-3001 Water Requirements; ACSM Position Stand on Exercise and Fluid Replacement
    
    Base: 30-35 mL/kg body weight (NASA uses 32 mL/kg)
    
    Adjustments:
    - Activity level multiplier
    - Exercise: +500-1000 mL per hour of moderate-vigorous activity
    - Hot environment: +20-30%
    - Altitude > 2500m: +10-15%
    
    Args:
        weight_kg: Body weight in kilograms
        activity_level: "sedentary", "light", "moderate", "active", "very_active"
        exercise_minutes: Additional exercise time in minutes
        hot_environment: Whether in hot/humid conditions
        altitude_m: Altitude in meters
        
    Returns:
        HydrationRequirements dataclass
    """
    # Base requirement (NASA standard)
    base_ml = weight_kg * 32.0
    base_ml = max(base_ml, 2000.0)  # Minimum 2L
    
    # Activity level multiplier
    activity_multipliers = {
        "sedentary": 1.0,
        "light": 1.1,
        "moderate": 1.2,
        "active": 1.3,
        "very_active": 1.4,
    }
    activity_mult = activity_multipliers.get(activity_level.lower(), 1.2)
    
    activity_adjusted_ml = base_ml * activity_mult
    
    # Exercise addition (750 mL per hour average)
    exercise_ml = (exercise_minutes / 60) * 750
    
    # Environmental factors
    env_multiplier = 1.0
    if hot_environment:
        env_multiplier += 0.25
    if altitude_m > 2500:
        env_multiplier += 0.12
    
    total_ml = (activity_adjusted_ml + exercise_ml) * env_multiplier
    
    factors = {
        "base_ml_per_kg": 32.0,
        "activity_multiplier": activity_mult,
        "exercise_ml": exercise_ml,
        "environment_multiplier": env_multiplier,
        "altitude_m": altitude_m,
        "hot_environment": hot_environment,
    }
    
    return HydrationRequirements(
        base_ml=base_ml,
        activity_adjusted_ml=activity_adjusted_ml,
        total_ml=total_ml,
        glasses_8oz=math.ceil(total_ml / 237),
        liters=total_ml / 1000,
        factors=factors,
    )


def assess_cardiovascular_risk(
    age: int,
    sex: str,
    weight_kg: float,
    height_cm: float,
    systolic_bp: Optional[float] = None,
    total_cholesterol: Optional[float] = None,
    hdl_cholesterol: Optional[float] = None,
    smoker: bool = False,
    diabetes: bool = False,
    hypertension_treated: bool = False,
    family_history_cvd: bool = False,
    vo2max: Optional[float] = None,
    resting_hr: Optional[float] = None,
) -> CardiovascularRiskProfile:
    """
    Assess cardiovascular risk profile based on available data.
    
    Uses simplified Framingham-like risk factors assessment.
    
    Args:
        age: Age in years
        sex: Biological sex
        weight_kg: Body weight in kg
        height_cm: Height in cm
        systolic_bp: Systolic blood pressure (mmHg)
        total_cholesterol: Total cholesterol (mg/dL)
        hdl_cholesterol: HDL cholesterol (mg/dL)
        smoker: Current smoker
        diabetes: Has diabetes
        hypertension_treated: On antihypertensive medication
        family_history_cvd: Family history of premature CVD
        vo2max: VO2max if available
        resting_hr: Resting heart rate if available
        
    Returns:
        CardiovascularRiskProfile dataclass
    """
    risk_factors: List[str] = []
    protective_factors: List[str] = []
    recommendations: List[str] = []
    
    # Calculate BMI
    bmi = weight_kg / ((height_cm / 100) ** 2)
    
    # Age risk
    sex_lower = sex.lower() if sex else "male"
    age_risk_threshold = 45 if sex_lower == "male" else 55
    if age >= age_risk_threshold:
        risk_factors.append(f"Age ≥ {age_risk_threshold} years ({age})")
    
    # BMI assessment
    if bmi >= 30:
        risk_factors.append(f"Obesity (BMI {bmi:.1f})")
        recommendations.append("Weight reduction program recommended")
    elif bmi >= 25:
        risk_factors.append(f"Overweight (BMI {bmi:.1f})")
        recommendations.append("Consider weight management")
    elif 18.5 <= bmi < 25:
        protective_factors.append(f"Healthy BMI ({bmi:.1f})")
    
    # Blood pressure
    if systolic_bp is not None:
        if systolic_bp >= 140:
            risk_factors.append(f"Hypertension (SBP {systolic_bp:.0f} mmHg)")
            recommendations.append("Blood pressure management crucial")
        elif systolic_bp >= 130:
            risk_factors.append(f"Elevated BP (SBP {systolic_bp:.0f} mmHg)")
        elif systolic_bp < 120:
            protective_factors.append("Normal blood pressure")
    
    # Cholesterol
    if total_cholesterol is not None and hdl_cholesterol is not None:
        ratio = total_cholesterol / hdl_cholesterol if hdl_cholesterol > 0 else 999
        if ratio > 5:
            risk_factors.append(f"High TC/HDL ratio ({ratio:.1f})")
            recommendations.append("Lipid management recommended")
        elif ratio < 3.5:
            protective_factors.append(f"Favorable TC/HDL ratio ({ratio:.1f})")
    
    if hdl_cholesterol is not None:
        hdl_threshold = 40 if sex_lower == "male" else 50
        if hdl_cholesterol < hdl_threshold:
            risk_factors.append(f"Low HDL ({hdl_cholesterol:.0f} mg/dL)")
        elif hdl_cholesterol >= 60:
            protective_factors.append(f"High HDL ({hdl_cholesterol:.0f} mg/dL)")
    
    # Smoking
    if smoker:
        risk_factors.append("Current smoker")
        recommendations.append("Smoking cessation strongly recommended")
    else:
        protective_factors.append("Non-smoker")
    
    # Diabetes
    if diabetes:
        risk_factors.append("Diabetes mellitus")
        recommendations.append("Strict glycemic control important")
    
    # Family history
    if family_history_cvd:
        risk_factors.append("Family history of premature CVD")
    
    # Hypertension treatment
    if hypertension_treated:
        risk_factors.append("On antihypertensive medication")
    
    # Fitness (protective if good)
    if vo2max is not None:
        fitness = classify_fitness_by_vo2max(vo2max, age, sex_lower)
        if fitness.category in [FitnessCategory.EXCELLENT, FitnessCategory.SUPERIOR]:
            protective_factors.append(f"Excellent cardiorespiratory fitness (VO2max {vo2max:.1f})")
        elif fitness.category in [FitnessCategory.VERY_POOR, FitnessCategory.POOR]:
            risk_factors.append(f"Poor cardiorespiratory fitness (VO2max {vo2max:.1f})")
            recommendations.append("Aerobic exercise program recommended")
    
    # Resting heart rate
    if resting_hr is not None:
        if resting_hr > 80:
            risk_factors.append(f"Elevated resting HR ({resting_hr:.0f} bpm)")
        elif resting_hr < 60:
            protective_factors.append(f"Low resting HR ({resting_hr:.0f} bpm)")
    
    # Determine overall risk level
    num_risk = len(risk_factors)
    num_protective = len(protective_factors)
    
    if num_risk == 0:
        risk_level = RiskLevel.LOW
    elif num_risk <= 2 and num_protective >= 2:
        risk_level = RiskLevel.LOW
    elif num_risk <= 3:
        risk_level = RiskLevel.MODERATE
    elif num_risk <= 5:
        risk_level = RiskLevel.HIGH
    else:
        risk_level = RiskLevel.VERY_HIGH
    
    # Add general recommendations
    if risk_level != RiskLevel.LOW:
        recommendations.extend([
            "Regular cardiovascular screening recommended",
            "Mediterranean-style diet beneficial",
            "Regular physical activity (150+ min/week moderate intensity)",
        ])
    
    return CardiovascularRiskProfile(
        risk_factors=risk_factors,
        protective_factors=protective_factors,
        risk_level=risk_level,
        recommendations=recommendations,
        framingham_inputs={
            "age": age,
            "sex": sex_lower,
            "bmi": round(bmi, 1),
            "systolic_bp": systolic_bp,
            "total_cholesterol": total_cholesterol,
            "hdl_cholesterol": hdl_cholesterol,
            "smoker": smoker,
            "diabetes": diabetes,
        },
    )


def calculate_all_personalized_metrics(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: str,
    neck_cm: Optional[float] = None,
    waist_cm: Optional[float] = None,
    hip_cm: Optional[float] = None,
    vo2max: Optional[float] = None,
    resting_hr: Optional[float] = None,
    systolic_bp: Optional[float] = None,
    total_cholesterol: Optional[float] = None,
    hdl_cholesterol: Optional[float] = None,
    smoker: bool = False,
    diabetes: bool = False,
    hypertension_treated: bool = False,
    family_history_cvd: bool = False,
    snoring: Optional[bool] = None,
    tiredness: Optional[bool] = None,
    observed_apnea: Optional[bool] = None,
    activity_level: str = "moderate",
) -> Dict[str, Any]:
    """
    Calculate all available personalized metrics for a user profile.
    
    This is a convenience function that aggregates all personalized calculations.
    
    Args:
        weight_kg: Body weight in kg
        height_cm: Height in cm
        age: Age in years
        sex: Biological sex
        neck_cm: Neck circumference (cm) - for body fat and sleep apnea
        waist_cm: Waist circumference (cm) - for body fat
        hip_cm: Hip circumference (cm) - for female body fat
        vo2max: VO2max in mL/kg/min
        resting_hr: Resting heart rate
        systolic_bp: Systolic blood pressure
        total_cholesterol: Total cholesterol mg/dL
        hdl_cholesterol: HDL cholesterol mg/dL
        smoker: Current smoker status
        diabetes: Diabetes status
        hypertension_treated: On BP medication
        family_history_cvd: Family history of CVD
        snoring: Loud snoring (sleep apnea)
        tiredness: Daytime tiredness (sleep apnea)
        observed_apnea: Witnessed apnea (sleep apnea)
        activity_level: Activity level string
        
    Returns:
        Dictionary with all calculated personalized metrics
    """
    results: Dict[str, Any] = {
        "user_inputs": {
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "age": age,
            "sex": sex,
        },
        "calculations_available": [],
    }
    
    # BMI
    bmi = weight_kg / ((height_cm / 100) ** 2)
    results["bmi"] = {
        "value": round(bmi, 1),
        "category": (
            "Underweight" if bmi < 18.5 else
            "Normal" if bmi < 25 else
            "Overweight" if bmi < 30 else
            "Obese"
        ),
    }
    results["calculations_available"].append("bmi")
    
    # Body fat (if circumferences available)
    if neck_cm and waist_cm:
        body_fat = calculate_body_fat_navy(
            weight_kg=weight_kg,
            height_cm=height_cm,
            waist_cm=waist_cm,
            neck_cm=neck_cm,
            sex=sex,
            hip_cm=hip_cm,
        )
        if body_fat:
            results["body_fat"] = body_fat.to_dict()
            results["calculations_available"].append("body_fat")
    
    # Sleep apnea risk
    sleep_apnea = calculate_sleep_apnea_risk(
        sex=sex,
        age=age,
        bmi=bmi,
        neck_cm=neck_cm,
        snoring=snoring,
        tiredness=tiredness,
        observed_apnea=observed_apnea,
        high_blood_pressure=hypertension_treated or (systolic_bp is not None and systolic_bp >= 140),
    )
    results["sleep_apnea_risk"] = sleep_apnea.to_dict()
    results["calculations_available"].append("sleep_apnea_risk")
    
    # Personalized HRV norms
    hrv_norms = get_personalized_hrv_norms(age=age, sex=sex)
    results["hrv_norms"] = hrv_norms.to_dict()
    results["calculations_available"].append("hrv_norms")
    
    # Fitness classification (if VO2max available)
    if vo2max:
        fitness = classify_fitness_by_vo2max(vo2max=vo2max, age=age, sex=sex)
        results["fitness_classification"] = fitness.to_dict()
        results["calculations_available"].append("fitness_classification")
    
    # Cardiovascular risk
    cv_risk = assess_cardiovascular_risk(
        age=age,
        sex=sex,
        weight_kg=weight_kg,
        height_cm=height_cm,
        systolic_bp=systolic_bp,
        total_cholesterol=total_cholesterol,
        hdl_cholesterol=hdl_cholesterol,
        smoker=smoker,
        diabetes=diabetes,
        hypertension_treated=hypertension_treated,
        family_history_cvd=family_history_cvd,
        vo2max=vo2max,
        resting_hr=resting_hr,
    )
    results["cardiovascular_risk"] = cv_risk.to_dict()
    results["calculations_available"].append("cardiovascular_risk")
    
    # Hydration requirements
    hydration = calculate_personalized_hydration(
        weight_kg=weight_kg,
        activity_level=activity_level,
    )
    results["hydration_requirements"] = hydration.to_dict()
    results["calculations_available"].append("hydration_requirements")
    
    return results


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "RiskLevel",
    "FitnessCategory",
    "BodyFatCategory",
    # Data classes
    "BodyFatEstimate",
    "SleepApneaRisk",
    "PersonalizedHRVNorms",
    "FitnessClassification",
    "CardiovascularRiskProfile",
    "HydrationRequirements",
    # Calculation functions
    "calculate_body_fat_navy",
    "calculate_sleep_apnea_risk",
    "get_personalized_hrv_norms",
    "interpret_hrv_metric_personalized",
    "classify_fitness_by_vo2max",
    "calculate_personalized_hydration",
    "assess_cardiovascular_risk",
    "calculate_all_personalized_metrics",
    # Reference data
    "HRV_NORMS_BY_AGE",
    "VO2MAX_CLASSIFICATION",
    "BODY_FAT_RANGES",
]
