"""
Profile Tools Engine for Mission Control - Flight Surgeon.

Provides comprehensive calculation engines accessible per user profile:
- SAFTE fatigue prediction using profile data (age, chronotype, sleep patterns)
- HRV analysis with personalized interpretation (age/sex-adjusted norms)
- Recovery score calculations combining HRV and sleep metrics
- Training readiness assessment based on parasympathetic indices
- Performance forecasting integrating circadian and fatigue models

Each tool uses the user's profile data as context for calculations,
enabling truly personalized physiological assessments.

Scientific References:
- SAFTE Model: Hursh et al. (2004). Fatigue models for applied research
- HRV Norms: Nunan D et al. PACE 2010; Shaffer & Ginsberg 2017
- Recovery: Plews et al. (2013). J Appl Physiol - lnRMSSD for recovery
- Readiness: Kiviniemi et al. (2007). HRV-guided training

Author: Dr. Diego Leonel Malpica Hincapié, MD
Version: 1.0.0
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, Final, List, Optional, Tuple

import numpy as np
import pandas as pd

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

class RecoveryStatus(str, Enum):
    """Recovery status classification."""
    POOR = "poor"
    LOW = "low"
    MODERATE = "moderate"
    GOOD = "good"
    EXCELLENT = "excellent"


class ReadinessLevel(str, Enum):
    """Training readiness level."""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    OPTIMAL = "optimal"


class FatigueRisk(str, Enum):
    """Fatigue risk classification."""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


# Reference thresholds for lnRMSSD recovery (Plews et al. 2013)
RECOVERY_THRESHOLDS: Dict[str, Tuple[float, float]] = {
    "20-29": (3.8, 4.3),  # (low_threshold, high_threshold)
    "30-39": (3.6, 4.1),
    "40-49": (3.4, 3.9),
    "50-59": (3.2, 3.7),
    "60-69": (3.0, 3.5),
    "70+": (2.8, 3.3),
}


# ---------------------------------------------------------------------------
# Data Classes for Tool Results
# ---------------------------------------------------------------------------

@dataclass
class RecoveryScore:
    """Recovery score calculation result."""
    
    score: float  # 0-100 scale
    status: RecoveryStatus
    status_label: str
    ln_rmssd: Optional[float] = None
    ln_rmssd_baseline: Optional[float] = None
    ln_rmssd_cv: Optional[float] = None
    components: Dict[str, float] = field(default_factory=dict)
    interpretation: str = ""
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "score": round(self.score, 1),
            "status": self.status.value,
            "status_label": self.status_label,
            "ln_rmssd": round(self.ln_rmssd, 3) if self.ln_rmssd else None,
            "ln_rmssd_baseline": round(self.ln_rmssd_baseline, 3) if self.ln_rmssd_baseline else None,
            "ln_rmssd_cv": round(self.ln_rmssd_cv, 2) if self.ln_rmssd_cv else None,
            "components": {k: round(v, 2) for k, v in self.components.items()},
            "interpretation": self.interpretation,
            "recommendations": self.recommendations,
        }


@dataclass
class TrainingReadiness:
    """Training readiness assessment result."""
    
    readiness_score: float  # 0-100 scale
    level: ReadinessLevel
    level_label: str
    hrv_component: float
    sleep_component: float
    fatigue_component: float
    strain_component: float
    interpretation: str
    training_recommendations: List[str] = field(default_factory=list)
    workout_suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "readiness_score": round(self.readiness_score, 1),
            "level": self.level.value,
            "level_label": self.level_label,
            "components": {
                "hrv": round(self.hrv_component, 1),
                "sleep": round(self.sleep_component, 1),
                "fatigue": round(self.fatigue_component, 1),
                "strain": round(self.strain_component, 1),
            },
            "interpretation": self.interpretation,
            "training_recommendations": self.training_recommendations,
            "workout_suggestions": self.workout_suggestions,
        }


@dataclass
class FatiguePrediction:
    """SAFTE-based fatigue prediction result."""
    
    current_effectiveness: float  # 0-100 scale
    predicted_effectiveness_4h: float
    predicted_effectiveness_8h: float
    predicted_effectiveness_24h: float
    risk_level: FatigueRisk
    risk_label: str
    sleep_debt_hours: float
    circadian_phase: str
    optimal_sleep_time: str
    recommendations: List[str] = field(default_factory=list)
    performance_curve: List[Tuple[int, float]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_effectiveness": round(self.current_effectiveness, 1),
            "predicted_effectiveness": {
                "4h": round(self.predicted_effectiveness_4h, 1),
                "8h": round(self.predicted_effectiveness_8h, 1),
                "24h": round(self.predicted_effectiveness_24h, 1),
            },
            "risk_level": self.risk_level.value,
            "risk_label": self.risk_label,
            "sleep_debt_hours": round(self.sleep_debt_hours, 1),
            "circadian_phase": self.circadian_phase,
            "optimal_sleep_time": self.optimal_sleep_time,
            "recommendations": self.recommendations,
        }


@dataclass
class PersonalizedHRVAnalysis:
    """Personalized HRV analysis result."""
    
    metrics: Dict[str, Dict[str, Any]]
    overall_status: str
    autonomic_balance: str
    parasympathetic_index: float
    stress_index: float
    age_group: str
    interpretation: str
    clinical_significance: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metrics": self.metrics,
            "overall_status": self.overall_status,
            "autonomic_balance": self.autonomic_balance,
            "parasympathetic_index": round(self.parasympathetic_index, 2),
            "stress_index": round(self.stress_index, 1),
            "age_group": self.age_group,
            "interpretation": self.interpretation,
            "clinical_significance": self.clinical_significance,
            "recommendations": self.recommendations,
        }


@dataclass
class PerformanceForecast:
    """24-hour performance forecast combining circadian and fatigue models."""
    
    current_hour: int
    current_performance: float
    peak_performance_time: str
    low_performance_time: str
    hourly_forecast: List[Dict[str, Any]]
    critical_windows: List[Dict[str, str]]
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_hour": self.current_hour,
            "current_performance": round(self.current_performance, 1),
            "peak_performance_time": self.peak_performance_time,
            "low_performance_time": self.low_performance_time,
            "hourly_forecast": self.hourly_forecast,
            "critical_windows": self.critical_windows,
            "recommendations": self.recommendations,
        }


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _get_age_group(age: int) -> str:
    """Get age group string for reference tables."""
    if age < 20:
        return "20-29"
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


def _calculate_ln_rmssd(rmssd_ms: float) -> float:
    """Calculate natural log of RMSSD."""
    if rmssd_ms <= 0:
        return 0.0
    return math.log(rmssd_ms)


def _circadian_effectiveness(hour: int, chronotype_offset: float = 0.0) -> float:
    """
    Calculate circadian effectiveness for a given hour.
    
    Uses simplified two-process model approximation.
    Peak performance typically 2-4 hours after wake for morning types.
    
    Args:
        hour: Hour of day (0-23)
        chronotype_offset: Hours offset from average (negative = morning person)
    
    Returns:
        Effectiveness multiplier (0.7-1.0)
    """
    # Adjust for chronotype
    adjusted_hour = (hour - chronotype_offset) % 24
    
    # Simplified circadian curve (peak ~10-12, trough ~3-5 AM)
    # Using cosine approximation
    phase = (adjusted_hour - 14) * (2 * math.pi / 24)
    circadian = 0.85 + 0.15 * math.cos(phase)
    
    # Post-lunch dip (~13-15h)
    if 13 <= adjusted_hour <= 15:
        circadian -= 0.05
    
    return max(0.7, min(1.0, circadian))


def _sleep_homeostatic(hours_awake: float, base_effectiveness: float = 100.0) -> float:
    """
    Calculate homeostatic sleep pressure effect on effectiveness.
    
    Based on SAFTE model sleep reservoir depletion.
    
    Args:
        hours_awake: Hours since last sleep
        base_effectiveness: Baseline effectiveness (default 100%)
    
    Returns:
        Effectiveness score (0-100)
    """
    # Sleep reservoir depletion rate ~2.4% per hour awake
    # With recovery during sleep ~7.5% per hour
    depletion_rate = 2.4
    
    # Calculate depletion
    depletion = hours_awake * depletion_rate
    effectiveness = base_effectiveness - depletion
    
    # Apply floor (minimum ~65% after 24h awake)
    return max(65.0, min(100.0, effectiveness))


# ---------------------------------------------------------------------------
# Main Calculation Functions
# ---------------------------------------------------------------------------

def calculate_recovery_score(
    rmssd_ms: float,
    age: int,
    rmssd_history: Optional[List[float]] = None,
    sleep_hours: Optional[float] = None,
    sleep_quality: Optional[float] = None,
    resting_hr: Optional[float] = None,
    resting_hr_baseline: Optional[float] = None,
) -> RecoveryScore:
    """
    Calculate recovery score based on HRV and sleep metrics.
    
    Uses lnRMSSD as primary recovery indicator (Plews et al. 2013).
    Combines with sleep metrics and resting HR for comprehensive assessment.
    
    Args:
        rmssd_ms: Current RMSSD value in milliseconds
        age: Age in years for age-adjusted interpretation
        rmssd_history: Historical RMSSD values for baseline calculation
        sleep_hours: Hours of sleep last night
        sleep_quality: Sleep quality score (0-1 scale)
        resting_hr: Current resting heart rate
        resting_hr_baseline: Baseline resting heart rate
    
    Returns:
        RecoveryScore dataclass with comprehensive recovery assessment
    """
    age_group = _get_age_group(age)
    ln_rmssd = _calculate_ln_rmssd(rmssd_ms)
    
    # Calculate baseline lnRMSSD from history
    ln_rmssd_baseline = None
    ln_rmssd_cv = None
    if rmssd_history and len(rmssd_history) >= 7:
        ln_history = [_calculate_ln_rmssd(r) for r in rmssd_history if r > 0]
        if ln_history:
            ln_rmssd_baseline = float(np.mean(ln_history))
            ln_rmssd_cv = float(np.std(ln_history) / ln_rmssd_baseline * 100) if ln_rmssd_baseline > 0 else 0
    
    # Get age-adjusted thresholds
    low_threshold, high_threshold = RECOVERY_THRESHOLDS.get(
        age_group, RECOVERY_THRESHOLDS["40-49"]
    )
    
    # Calculate HRV recovery component (0-50 points)
    if ln_rmssd_baseline:
        # Compare to personal baseline
        deviation = (ln_rmssd - ln_rmssd_baseline) / ln_rmssd_baseline * 100
        if deviation >= 5:
            hrv_score = 45 + min(5, deviation / 2)  # Above baseline: 45-50
        elif deviation >= -5:
            hrv_score = 35 + (deviation + 5) * 2  # Within normal: 35-45
        elif deviation >= -15:
            hrv_score = 20 + (deviation + 15) * 1.5  # Below baseline: 20-35
        else:
            hrv_score = max(0, 20 + deviation)  # Well below: 0-20
    else:
        # Compare to population norms
        if ln_rmssd >= high_threshold:
            hrv_score = 45
        elif ln_rmssd >= low_threshold:
            hrv_score = 30 + (ln_rmssd - low_threshold) / (high_threshold - low_threshold) * 15
        else:
            hrv_score = max(0, 30 * ln_rmssd / low_threshold)
    
    components: Dict[str, float] = {"hrv": hrv_score}
    
    # Sleep component (0-30 points)
    sleep_score = 15.0  # Default middle value
    if sleep_hours is not None:
        if sleep_hours >= 8:
            sleep_score = 25 + min(5, (sleep_hours - 8) * 2.5)
        elif sleep_hours >= 7:
            sleep_score = 20 + (sleep_hours - 7) * 5
        elif sleep_hours >= 6:
            sleep_score = 10 + (sleep_hours - 6) * 10
        else:
            sleep_score = max(0, sleep_hours * 1.67)
    
    if sleep_quality is not None:
        sleep_score = sleep_score * (0.7 + 0.3 * sleep_quality)
    
    components["sleep"] = sleep_score
    
    # Resting HR component (0-20 points)
    hr_score = 10.0  # Default middle value
    if resting_hr is not None:
        if resting_hr_baseline:
            hr_deviation = (resting_hr - resting_hr_baseline) / resting_hr_baseline * 100
            if hr_deviation <= -5:
                hr_score = 18 + min(2, abs(hr_deviation - 5) / 2)
            elif hr_deviation <= 5:
                hr_score = 12 + (5 - hr_deviation) * 1.2
            elif hr_deviation <= 15:
                hr_score = 5 + (15 - hr_deviation) * 0.7
            else:
                hr_score = max(0, 5 - (hr_deviation - 15) * 0.3)
        else:
            # Use absolute values
            if resting_hr < 60:
                hr_score = 15 + min(5, (60 - resting_hr) / 2)
            elif resting_hr < 70:
                hr_score = 10 + (70 - resting_hr) / 2
            elif resting_hr < 80:
                hr_score = 5 + (80 - resting_hr) / 2
            else:
                hr_score = max(0, 5 - (resting_hr - 80) / 4)
    
    components["resting_hr"] = hr_score
    
    # Calculate total score
    total_score = hrv_score + sleep_score + hr_score
    total_score = max(0, min(100, total_score))
    
    # Determine status
    if total_score >= 80:
        status = RecoveryStatus.EXCELLENT
        status_label = "Excellent Recovery"
        interpretation = "Outstanding recovery. Body is well-rested and parasympathetic tone is high."
        recommendations = [
            "Ideal day for high-intensity training or demanding activities",
            "Can handle increased training load",
            "Maintain current sleep and recovery habits",
        ]
    elif total_score >= 65:
        status = RecoveryStatus.GOOD
        status_label = "Good Recovery"
        interpretation = "Good recovery status. Ready for normal training loads."
        recommendations = [
            "Normal training day - proceed as planned",
            "Monitor for accumulated fatigue if maintained over days",
            "Ensure adequate nutrition and hydration",
        ]
    elif total_score >= 50:
        status = RecoveryStatus.MODERATE
        status_label = "Moderate Recovery"
        interpretation = "Recovery is adequate but not optimal. Some residual fatigue present."
        recommendations = [
            "Consider moderate training intensity",
            "Prioritize recovery strategies (sleep, nutrition)",
            "Avoid adding extra training volume",
        ]
    elif total_score >= 35:
        status = RecoveryStatus.LOW
        status_label = "Low Recovery"
        interpretation = "Recovery is compromised. Elevated sympathetic activity or sleep debt detected."
        recommendations = [
            "Light training or active recovery recommended",
            "Focus on sleep quality and quantity",
            "Review recent stressors (training, life, travel)",
            "Consider additional rest day if persists",
        ]
    else:
        status = RecoveryStatus.POOR
        status_label = "Poor Recovery"
        interpretation = "Significant recovery deficit. High sympathetic activity or severe sleep debt."
        recommendations = [
            "Rest day strongly recommended",
            "Prioritize 8+ hours of sleep",
            "Avoid strenuous activities",
            "Check for illness, overtraining, or major stressors",
            "Consult healthcare provider if persists > 3 days",
        ]
    
    return RecoveryScore(
        score=total_score,
        status=status,
        status_label=status_label,
        ln_rmssd=ln_rmssd,
        ln_rmssd_baseline=ln_rmssd_baseline,
        ln_rmssd_cv=ln_rmssd_cv,
        components=components,
        interpretation=interpretation,
        recommendations=recommendations,
    )


def calculate_training_readiness(
    rmssd_ms: float,
    age: int,
    sleep_hours: float = 7.0,
    sleep_quality: float = 0.7,
    hours_since_last_training: float = 24.0,
    last_training_intensity: float = 0.5,
    accumulated_strain: float = 0.0,
    chronotype_offset: float = 0.0,
) -> TrainingReadiness:
    """
    Calculate training readiness score.
    
    Combines HRV recovery, sleep quality, fatigue, and training strain
    to provide actionable training guidance.
    
    Args:
        rmssd_ms: Current RMSSD in milliseconds
        age: Age in years
        sleep_hours: Hours of sleep last night
        sleep_quality: Sleep quality (0-1 scale)
        hours_since_last_training: Hours since last workout
        last_training_intensity: Intensity of last workout (0-1 scale)
        accumulated_strain: Cumulative strain score (0-100)
        chronotype_offset: Chronotype offset (negative = morning person)
    
    Returns:
        TrainingReadiness dataclass with assessment and recommendations
    """
    # HRV component (0-35 points)
    ln_rmssd = _calculate_ln_rmssd(rmssd_ms)
    age_group = _get_age_group(age)
    low_threshold, high_threshold = RECOVERY_THRESHOLDS.get(
        age_group, RECOVERY_THRESHOLDS["40-49"]
    )
    
    if ln_rmssd >= high_threshold:
        hrv_component = 30 + min(5, (ln_rmssd - high_threshold) * 5)
    elif ln_rmssd >= low_threshold:
        hrv_component = 20 + (ln_rmssd - low_threshold) / (high_threshold - low_threshold) * 10
    else:
        hrv_component = max(0, 20 * ln_rmssd / low_threshold)
    
    # Sleep component (0-25 points)
    sleep_base = 0.0
    if sleep_hours >= 8:
        sleep_base = 20 + min(5, (sleep_hours - 8) * 2.5)
    elif sleep_hours >= 7:
        sleep_base = 15 + (sleep_hours - 7) * 5
    elif sleep_hours >= 6:
        sleep_base = 8 + (sleep_hours - 6) * 7
    else:
        sleep_base = max(0, sleep_hours * 1.33)
    
    sleep_component = sleep_base * (0.6 + 0.4 * sleep_quality)
    
    # Fatigue component (0-20 points, inverse of fatigue)
    # More time since training = less fatigue = higher score
    recovery_factor = min(1.0, hours_since_last_training / 48)  # Full recovery at 48h
    intensity_factor = 1 - (last_training_intensity * 0.5)  # High intensity = more fatigue
    fatigue_component = 20 * recovery_factor * intensity_factor
    
    # Strain component (0-20 points, inverse of strain)
    # Lower accumulated strain = higher readiness
    strain_factor = 1 - (accumulated_strain / 100) * 0.8
    strain_component = 20 * max(0, strain_factor)
    
    # Total readiness score
    readiness_score = hrv_component + sleep_component + fatigue_component + strain_component
    readiness_score = max(0, min(100, readiness_score))
    
    # Determine level and recommendations
    if readiness_score >= 85:
        level = ReadinessLevel.OPTIMAL
        level_label = "Optimal Readiness"
        interpretation = "Peak readiness for high-intensity training or competition."
        training_recommendations = [
            "Ideal for high-intensity interval training (HIIT)",
            "Can perform max strength or power sessions",
            "Competition-ready state",
        ]
        workout_suggestions = [
            "Sprint intervals or VO2max work",
            "Heavy compound lifts",
            "Sport-specific high-intensity drills",
        ]
    elif readiness_score >= 70:
        level = ReadinessLevel.HIGH
        level_label = "High Readiness"
        interpretation = "Good readiness for demanding training sessions."
        training_recommendations = [
            "Proceed with planned training",
            "Can handle moderate-high intensity",
            "Good day for technique work under load",
        ]
        workout_suggestions = [
            "Threshold training",
            "Moderate strength work (70-85% 1RM)",
            "Tempo runs or sustained efforts",
        ]
    elif readiness_score >= 50:
        level = ReadinessLevel.MODERATE
        level_label = "Moderate Readiness"
        interpretation = "Adequate readiness for moderate training."
        training_recommendations = [
            "Reduce intensity by 10-20%",
            "Focus on technique and skill work",
            "Avoid adding extra volume",
        ]
        workout_suggestions = [
            "Aerobic base training",
            "Moderate resistance (60-70% 1RM)",
            "Mobility and flexibility work",
        ]
    elif readiness_score >= 30:
        level = ReadinessLevel.LOW
        level_label = "Low Readiness"
        interpretation = "Recovery deficit detected. Light activity recommended."
        training_recommendations = [
            "Active recovery only",
            "Reduce intensity by 30-50%",
            "Focus on recovery modalities",
        ]
        workout_suggestions = [
            "Light walking or cycling",
            "Yoga or stretching",
            "Swimming or water exercise",
        ]
    else:
        level = ReadinessLevel.VERY_LOW
        level_label = "Very Low Readiness"
        interpretation = "Significant recovery deficit. Rest recommended."
        training_recommendations = [
            "Full rest day recommended",
            "Prioritize sleep and nutrition",
            "Consider seeing healthcare provider if persists",
        ]
        workout_suggestions = [
            "Complete rest",
            "Gentle stretching only if desired",
            "Focus on sleep hygiene",
        ]
    
    return TrainingReadiness(
        readiness_score=readiness_score,
        level=level,
        level_label=level_label,
        hrv_component=hrv_component,
        sleep_component=sleep_component,
        fatigue_component=fatigue_component,
        strain_component=strain_component,
        interpretation=interpretation,
        training_recommendations=training_recommendations,
        workout_suggestions=workout_suggestions,
    )


def predict_fatigue(
    sleep_hours_last_night: float,
    sleep_quality: float,
    hours_awake: float,
    current_hour: int,
    chronotype_offset: float = 0.0,
    accumulated_sleep_debt: float = 0.0,
    workload_intensity: float = 0.5,
) -> FatiguePrediction:
    """
    Predict fatigue and cognitive effectiveness using SAFTE model principles.
    
    Combines circadian rhythms, sleep homeostasis, and accumulated sleep debt
    to forecast performance over the next 24 hours.
    
    Args:
        sleep_hours_last_night: Hours of sleep last night
        sleep_quality: Sleep quality (0-1 scale)
        hours_awake: Hours since waking
        current_hour: Current hour (0-23)
        chronotype_offset: Chronotype offset (negative = morning person)
        accumulated_sleep_debt: Cumulative sleep debt in hours
        workload_intensity: Current workload intensity (0-1)
    
    Returns:
        FatiguePrediction dataclass with forecast and recommendations
    """
    # Calculate base sleep reservoir
    sleep_need = 8.0  # Baseline sleep need
    sleep_efficiency = sleep_quality * 0.95  # Quality affects efficiency
    effective_sleep = sleep_hours_last_night * sleep_efficiency
    
    # Sleep debt calculation
    nightly_debt = max(0, sleep_need - effective_sleep)
    total_debt = accumulated_sleep_debt + nightly_debt
    
    # Calculate current effectiveness
    circadian = _circadian_effectiveness(current_hour, chronotype_offset)
    homeostatic = _sleep_homeostatic(hours_awake)
    debt_penalty = min(15, total_debt * 2)  # Max 15% penalty for debt
    
    current_effectiveness = homeostatic * circadian - debt_penalty
    current_effectiveness = max(50, min(100, current_effectiveness))
    
    # Workload adjustment
    current_effectiveness -= workload_intensity * 5
    
    # Generate 24-hour forecast
    performance_curve: List[Tuple[int, float]] = []
    hourly_forecast: List[Dict[str, Any]] = []
    
    peak_time = current_hour
    peak_performance = current_effectiveness
    low_time = current_hour
    low_performance = current_effectiveness
    
    for h_offset in range(25):
        forecast_hour = (current_hour + h_offset) % 24
        hours_since_wake = hours_awake + h_offset
        
        # Assume sleep if projected hours awake > 16
        if hours_since_wake > 16 and h_offset > 0:
            # Simulate sleep recovery
            sleep_hours_gained = min(8, hours_since_wake - 16)
            hours_since_wake = hours_since_wake - 16 - sleep_hours_gained
            hours_since_wake = max(0, hours_since_wake)
        
        circ = _circadian_effectiveness(forecast_hour, chronotype_offset)
        homeo = _sleep_homeostatic(hours_since_wake)
        
        forecast_eff = homeo * circ - debt_penalty * 0.9  # Debt reduces over time
        forecast_eff = max(50, min(100, forecast_eff))
        
        performance_curve.append((forecast_hour, forecast_eff))
        hourly_forecast.append({
            "hour": forecast_hour,
            "effectiveness": round(forecast_eff, 1),
            "hours_offset": h_offset,
        })
        
        if forecast_eff > peak_performance and h_offset > 0:
            peak_performance = forecast_eff
            peak_time = forecast_hour
        if forecast_eff < low_performance and h_offset > 0:
            low_performance = forecast_eff
            low_time = forecast_hour
    
    # Extract predictions at specific intervals
    pred_4h = hourly_forecast[4]["effectiveness"] if len(hourly_forecast) > 4 else current_effectiveness
    pred_8h = hourly_forecast[8]["effectiveness"] if len(hourly_forecast) > 8 else current_effectiveness
    pred_24h = hourly_forecast[24]["effectiveness"] if len(hourly_forecast) > 24 else current_effectiveness
    
    # Determine risk level
    if current_effectiveness >= 85:
        risk_level = FatigueRisk.MINIMAL
        risk_label = "Minimal Fatigue Risk"
    elif current_effectiveness >= 75:
        risk_level = FatigueRisk.LOW
        risk_label = "Low Fatigue Risk"
    elif current_effectiveness >= 65:
        risk_level = FatigueRisk.MODERATE
        risk_label = "Moderate Fatigue Risk"
    elif current_effectiveness >= 55:
        risk_level = FatigueRisk.HIGH
        risk_label = "High Fatigue Risk"
    else:
        risk_level = FatigueRisk.CRITICAL
        risk_label = "Critical Fatigue Risk"
    
    # Circadian phase description
    if 6 <= current_hour < 12:
        circadian_phase = "Morning alertness rising"
    elif 12 <= current_hour < 14:
        circadian_phase = "Pre-lunch peak"
    elif 14 <= current_hour < 16:
        circadian_phase = "Post-lunch dip"
    elif 16 <= current_hour < 20:
        circadian_phase = "Evening second wind"
    elif 20 <= current_hour < 23:
        circadian_phase = "Evening decline"
    else:
        circadian_phase = "Circadian low (night)"
    
    # Optimal sleep time (based on chronotype)
    optimal_bedtime = int(23 + chronotype_offset) % 24
    optimal_sleep_time = f"{optimal_bedtime:02d}:00"
    
    # Recommendations
    recommendations = []
    if total_debt > 4:
        recommendations.append(f"Sleep debt of {total_debt:.1f}h detected. Prioritize extra sleep.")
    if current_effectiveness < 70:
        recommendations.append("Consider a 20-minute power nap if possible.")
    if 14 <= current_hour <= 16:
        recommendations.append("Post-lunch dip period. Avoid critical decisions if fatigued.")
    if hours_awake > 12:
        recommendations.append("Extended wakefulness. Monitor for decreased alertness.")
    if workload_intensity > 0.7:
        recommendations.append("High workload. Schedule breaks every 90 minutes.")
    
    # Critical windows
    critical_windows = []
    for entry in hourly_forecast[1:13]:  # Next 12 hours
        if entry["effectiveness"] < 65:
            critical_windows.append({
                "hour": f"{entry['hour']:02d}:00",
                "risk": "Performance below 65% - avoid critical tasks",
            })
    
    return FatiguePrediction(
        current_effectiveness=current_effectiveness,
        predicted_effectiveness_4h=pred_4h,
        predicted_effectiveness_8h=pred_8h,
        predicted_effectiveness_24h=pred_24h,
        risk_level=risk_level,
        risk_label=risk_label,
        sleep_debt_hours=total_debt,
        circadian_phase=circadian_phase,
        optimal_sleep_time=optimal_sleep_time,
        recommendations=recommendations,
        performance_curve=performance_curve,
    )


def analyze_hrv_personalized(
    hrv_metrics: Dict[str, float],
    age: int,
    sex: str,
    resting_hr: Optional[float] = None,
    activity_level: str = "moderate",
) -> PersonalizedHRVAnalysis:
    """
    Analyze HRV metrics with personalized age/sex-adjusted interpretation.
    
    Provides clinical-grade interpretation of HRV metrics against
    population norms adjusted for the user's demographics.
    
    Args:
        hrv_metrics: Dictionary of HRV metrics (rmssd_ms, sdnn_ms, pnn50, hf_power, lf_power, etc.)
        age: Age in years
        sex: Biological sex ("male" or "female")
        resting_hr: Resting heart rate if available
        activity_level: Activity level for context
    
    Returns:
        PersonalizedHRVAnalysis dataclass with comprehensive interpretation
    """
    age_group = _get_age_group(age)
    sex_lower = sex.lower() if sex else "male"
    
    # Import personalized norms
    try:
        from personalized_computations import (
            get_personalized_hrv_norms,
            interpret_hrv_metric_personalized,
        )
        hrv_norms = get_personalized_hrv_norms(age, sex_lower)
    except ImportError:
        # Fallback if module not available
        hrv_norms = None
    
    # Analyze each metric
    analyzed_metrics: Dict[str, Dict[str, Any]] = {}
    statuses: List[str] = []
    
    metric_map = {
        "rmssd_ms": "rmssd_ms",
        "rmssd": "rmssd_ms",
        "sdnn_ms": "sdnn_ms",
        "sdnn": "sdnn_ms",
        "pnn50": "pnn50_pct",
        "pnn50_pct": "pnn50_pct",
        "hf_power": "hf_power_ms2",
        "hf_power_ms2": "hf_power_ms2",
        "lf_power": "lf_power_ms2",
        "lf_power_ms2": "lf_power_ms2",
        "lf_hf_ratio": "lf_hf_ratio",
    }
    
    for key, value in hrv_metrics.items():
        if value is None or not isinstance(value, (int, float)):
            continue
        
        norm_key = metric_map.get(key.lower())
        if norm_key and hrv_norms:
            interpretation = interpret_hrv_metric_personalized(norm_key, value, hrv_norms)
            analyzed_metrics[key] = interpretation
            statuses.append(interpretation.get("status", "normal"))
        else:
            analyzed_metrics[key] = {
                "value": value,
                "status": "unknown",
                "interpretation": "No age-adjusted norms available",
            }
    
    # Calculate parasympathetic index (0-10 scale)
    rmssd = hrv_metrics.get("rmssd_ms", hrv_metrics.get("rmssd", 0))
    hf_power = hrv_metrics.get("hf_power", hrv_metrics.get("hf_power_ms2", 0))
    pnn50 = hrv_metrics.get("pnn50", hrv_metrics.get("pnn50_pct", 0))
    
    # Normalize to 0-10 scale based on age-adjusted norms
    ln_rmssd = _calculate_ln_rmssd(rmssd) if rmssd > 0 else 0
    low_t, high_t = RECOVERY_THRESHOLDS.get(age_group, (3.4, 3.9))
    
    if ln_rmssd >= high_t:
        pns_index = 7 + min(3, (ln_rmssd - high_t) * 3)
    elif ln_rmssd >= low_t:
        pns_index = 4 + (ln_rmssd - low_t) / (high_t - low_t) * 3
    else:
        pns_index = max(1, 4 * ln_rmssd / low_t)
    
    # Calculate stress index (Baevsky-style, 0-500 scale typical)
    mean_rr = hrv_metrics.get("mean_rr_ms", hrv_metrics.get("mean_rr", 800))
    sdnn = hrv_metrics.get("sdnn_ms", hrv_metrics.get("sdnn", 50))
    
    if sdnn > 0 and mean_rr > 0:
        # Simplified Baevsky stress index approximation
        mode = mean_rr  # Approximate mode as mean
        amo = 50  # Approximate amplitude of mode
        mxdmn = sdnn * 4  # Approximate range
        stress_index = (amo * 100) / (2 * mode * mxdmn / 1000) if mxdmn > 0 else 100
    else:
        stress_index = 100
    
    # Determine overall status
    status_counts = {s: statuses.count(s) for s in set(statuses)}
    if status_counts.get("very_low", 0) >= 2:
        overall_status = "Significantly below normal - autonomic concern"
    elif status_counts.get("low", 0) >= 2:
        overall_status = "Below normal - reduced parasympathetic activity"
    elif status_counts.get("very_high", 0) >= 2:
        overall_status = "Above normal - elevated vagal tone"
    elif status_counts.get("normal", 0) >= len(statuses) // 2:
        overall_status = "Within normal limits for age group"
    else:
        overall_status = "Mixed pattern - requires clinical interpretation"
    
    # Autonomic balance assessment
    lf_hf = hrv_metrics.get("lf_hf_ratio", hrv_metrics.get("lf_hf", 1.5))
    if lf_hf < 0.5:
        autonomic_balance = "Parasympathetic dominant"
    elif lf_hf < 1.0:
        autonomic_balance = "Balanced, slight parasympathetic"
    elif lf_hf < 2.0:
        autonomic_balance = "Balanced"
    elif lf_hf < 4.0:
        autonomic_balance = "Balanced, slight sympathetic"
    else:
        autonomic_balance = "Sympathetic dominant"
    
    # Clinical significance
    clinical_significance = []
    if rmssd < 20:
        clinical_significance.append("Very low RMSSD may indicate reduced vagal tone or high stress")
    if stress_index > 300:
        clinical_significance.append("Elevated stress index suggests sympathetic hyperactivity")
    if pns_index < 4:
        clinical_significance.append("Low parasympathetic index - recovery may be compromised")
    if pns_index > 8:
        clinical_significance.append("High parasympathetic index - excellent vagal tone")
    
    # Recommendations
    recommendations = []
    if pns_index < 4:
        recommendations.extend([
            "Prioritize stress management techniques",
            "Consider breathing exercises (5-6 breaths/min)",
            "Ensure adequate sleep (7-9 hours)",
        ])
    if stress_index > 200:
        recommendations.append("Monitor for signs of overtraining or chronic stress")
    if overall_status.startswith("Significantly below"):
        recommendations.append("Consider consultation with healthcare provider")
    
    # Build interpretation
    interpretation = f"""
HRV analysis for {sex_lower}, age {age} (reference group: {age_group}).

**Parasympathetic Activity**: {"High" if pns_index > 7 else "Normal" if pns_index > 4 else "Low"} (index: {pns_index:.1f}/10)
**Stress Level**: {"Low" if stress_index < 100 else "Moderate" if stress_index < 200 else "Elevated"} (index: {stress_index:.0f})
**Autonomic Balance**: {autonomic_balance}

{overall_status}
""".strip()
    
    return PersonalizedHRVAnalysis(
        metrics=analyzed_metrics,
        overall_status=overall_status,
        autonomic_balance=autonomic_balance,
        parasympathetic_index=pns_index,
        stress_index=stress_index,
        age_group=age_group,
        interpretation=interpretation,
        clinical_significance=clinical_significance,
        recommendations=recommendations,
    )


def generate_performance_forecast(
    current_hour: int,
    sleep_hours_last_night: float = 7.0,
    chronotype_offset: float = 0.0,
    accumulated_fatigue: float = 0.0,
    work_schedule: Optional[List[Tuple[int, int]]] = None,
) -> PerformanceForecast:
    """
    Generate 24-hour performance forecast.
    
    Combines circadian rhythm and fatigue models to predict
    cognitive performance throughout the day.
    
    Args:
        current_hour: Current hour (0-23)
        sleep_hours_last_night: Hours of sleep
        chronotype_offset: Chronotype offset (negative = morning type)
        accumulated_fatigue: Accumulated fatigue score (0-100)
        work_schedule: List of (start_hour, end_hour) work periods
    
    Returns:
        PerformanceForecast dataclass with hourly predictions
    """
    # Estimate hours awake (assume wake at 7 AM adjusted for chronotype)
    typical_wake = int(7 + chronotype_offset) % 24
    if current_hour >= typical_wake:
        hours_awake = current_hour - typical_wake
    else:
        hours_awake = (24 - typical_wake) + current_hour
    
    # Get fatigue prediction for performance curve
    fatigue_pred = predict_fatigue(
        sleep_hours_last_night=sleep_hours_last_night,
        sleep_quality=0.8,  # Assume decent quality
        hours_awake=hours_awake,
        current_hour=current_hour,
        chronotype_offset=chronotype_offset,
        accumulated_sleep_debt=accumulated_fatigue / 10,  # Convert to hours
    )
    
    # Build hourly forecast
    hourly_forecast = []
    peak_hour = current_hour
    peak_perf = 0.0
    low_hour = current_hour
    low_perf = 100.0
    
    for hour, perf in fatigue_pred.performance_curve[:25]:
        hourly_forecast.append({
            "hour": hour,
            "hour_str": f"{hour:02d}:00",
            "effectiveness": round(perf, 1),
            "is_work_hour": any(start <= hour < end for start, end in (work_schedule or [])),
        })
        
        if perf > peak_perf:
            peak_perf = perf
            peak_hour = hour
        if perf < low_perf:
            low_perf = perf
            low_hour = hour
    
    # Identify critical windows
    critical_windows = []
    if work_schedule:
        for start, end in work_schedule:
            for entry in hourly_forecast:
                if start <= entry["hour"] < end and entry["effectiveness"] < 70:
                    critical_windows.append({
                        "period": f"{entry['hour']:02d}:00 - {(entry['hour']+1)%24:02d}:00",
                        "warning": f"Performance at {entry['effectiveness']:.0f}% during work hours",
                    })
    
    # Build recommendations
    recommendations = []
    
    # Best time for demanding tasks
    recommendations.append(
        f"Schedule demanding cognitive tasks around {peak_hour:02d}:00 (peak performance)"
    )
    
    # Avoid critical decisions at low points
    recommendations.append(
        f"Avoid critical decisions around {low_hour:02d}:00 (circadian low)"
    )
    
    # Nap recommendation if afternoon dip is severe
    for entry in hourly_forecast:
        if 13 <= entry["hour"] <= 15 and entry["effectiveness"] < 70:
            recommendations.append("Consider a 20-min power nap during post-lunch dip (13:00-15:00)")
            break
    
    return PerformanceForecast(
        current_hour=current_hour,
        current_performance=fatigue_pred.current_effectiveness,
        peak_performance_time=f"{peak_hour:02d}:00",
        low_performance_time=f"{low_hour:02d}:00",
        hourly_forecast=hourly_forecast,
        critical_windows=critical_windows,
        recommendations=recommendations,
    )


# ---------------------------------------------------------------------------
# Convenience Function: Run All Profile Tools
# ---------------------------------------------------------------------------

def run_all_profile_tools(
    age: int,
    sex: str,
    weight_kg: float,
    height_cm: float,
    rmssd_ms: Optional[float] = None,
    hrv_metrics: Optional[Dict[str, float]] = None,
    sleep_hours: float = 7.0,
    sleep_quality: float = 0.7,
    hours_awake: float = 8.0,
    current_hour: Optional[int] = None,
    chronotype_offset: float = 0.0,
    resting_hr: Optional[float] = None,
    vo2max: Optional[float] = None,
    activity_level: str = "moderate",
) -> Dict[str, Any]:
    """
    Run all profile tools and return comprehensive results.
    
    This is a convenience function that aggregates all tool calculations
    for a user profile into a single results dictionary.
    
    Args:
        age: Age in years
        sex: Biological sex
        weight_kg: Body weight in kg
        height_cm: Height in cm
        rmssd_ms: Current RMSSD value
        hrv_metrics: Dictionary of HRV metrics
        sleep_hours: Hours of sleep last night
        sleep_quality: Sleep quality (0-1)
        hours_awake: Hours since waking
        current_hour: Current hour (0-23), defaults to now
        chronotype_offset: Chronotype offset hours
        resting_hr: Resting heart rate
        vo2max: VO2max value
        activity_level: Activity level string
    
    Returns:
        Dictionary with all tool results
    """
    if current_hour is None:
        current_hour = datetime.now().hour
    
    results: Dict[str, Any] = {
        "user_context": {
            "age": age,
            "sex": sex,
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "current_hour": current_hour,
        },
        "tools_available": [],
        "generated_at": datetime.now().isoformat(),
    }
    
    # Recovery Score
    if rmssd_ms is not None and rmssd_ms > 0:
        try:
            recovery = calculate_recovery_score(
                rmssd_ms=rmssd_ms,
                age=age,
                sleep_hours=sleep_hours,
                sleep_quality=sleep_quality,
                resting_hr=resting_hr,
            )
            results["recovery_score"] = recovery.to_dict()
            results["tools_available"].append("recovery_score")
        except Exception as exc:
            _LOGGER.warning("Recovery score calculation failed: %s", exc)
    
    # Training Readiness
    if rmssd_ms is not None and rmssd_ms > 0:
        try:
            readiness = calculate_training_readiness(
                rmssd_ms=rmssd_ms,
                age=age,
                sleep_hours=sleep_hours,
                sleep_quality=sleep_quality,
                chronotype_offset=chronotype_offset,
            )
            results["training_readiness"] = readiness.to_dict()
            results["tools_available"].append("training_readiness")
        except Exception as exc:
            _LOGGER.warning("Training readiness calculation failed: %s", exc)
    
    # Fatigue Prediction
    try:
        fatigue = predict_fatigue(
            sleep_hours_last_night=sleep_hours,
            sleep_quality=sleep_quality,
            hours_awake=hours_awake,
            current_hour=current_hour,
            chronotype_offset=chronotype_offset,
        )
        results["fatigue_prediction"] = fatigue.to_dict()
        results["tools_available"].append("fatigue_prediction")
    except Exception as exc:
        _LOGGER.warning("Fatigue prediction failed: %s", exc)
    
    # Personalized HRV Analysis
    if hrv_metrics:
        try:
            hrv_analysis = analyze_hrv_personalized(
                hrv_metrics=hrv_metrics,
                age=age,
                sex=sex,
                resting_hr=resting_hr,
                activity_level=activity_level,
            )
            results["hrv_analysis"] = hrv_analysis.to_dict()
            results["tools_available"].append("hrv_analysis")
        except Exception as exc:
            _LOGGER.warning("HRV analysis failed: %s", exc)
    
    # Performance Forecast
    try:
        forecast = generate_performance_forecast(
            current_hour=current_hour,
            sleep_hours_last_night=sleep_hours,
            chronotype_offset=chronotype_offset,
        )
        results["performance_forecast"] = forecast.to_dict()
        results["tools_available"].append("performance_forecast")
    except Exception as exc:
        _LOGGER.warning("Performance forecast failed: %s", exc)
    
    return results


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "RecoveryStatus",
    "ReadinessLevel",
    "FatigueRisk",
    # Data classes
    "RecoveryScore",
    "TrainingReadiness",
    "FatiguePrediction",
    "PersonalizedHRVAnalysis",
    "PerformanceForecast",
    # Calculation functions
    "calculate_recovery_score",
    "calculate_training_readiness",
    "predict_fatigue",
    "analyze_hrv_personalized",
    "generate_performance_forecast",
    "run_all_profile_tools",
    # Reference data
    "RECOVERY_THRESHOLDS",
]
