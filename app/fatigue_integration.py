"""Fatigue Integration Module for HRV App.

Integrates the SAFTE (Sleep, Activity, Fatigue, and Task Effectiveness) model
with Garmin sleep/activity data and HRV analysis for comprehensive fatigue
prediction and performance monitoring.

This module bridges:
- Garmin wellness data (sleep, HR, stress, activity)
- HRV analysis results
- SAFTE biomathematical model predictions

Scientific References:
- Hursh et al. (2004). Fatigue models for applied research in warfighter fatigue.
- Van Dongen et al. (2003). Cumulative cost of additional wakefulness.
- Borbély (1982). Two-process model of sleep regulation.
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from logging_config import get_logger, log_exception
except ImportError:  # pragma: no cover - fallback for relative imports
    from .logging_config import get_logger, log_exception  # type: ignore

try:
    from garmin_import import (
        GarminCredentials,
        GarminWellnessData,
        get_daily_physiology_summary,
        import_garmin_data,
        load_credentials_from_env,
    )
except ImportError:  # pragma: no cover - fallback for relative imports
    from .garmin_import import (  # type: ignore
        GarminCredentials,
        GarminWellnessData,
        get_daily_physiology_summary,
        import_garmin_data,
        load_credentials_from_env,
    )

try:
    from user_database import get_database  # type: ignore
except Exception:  # pragma: no cover - optional during limited environments
    get_database = None  # type: ignore[assignment]

# Local imports
try:
    from .fatigue_calculator.core import (
        enhanced_simulate_cognitive_performance,
        enhanced_circadian_process,
        SAFTEModel,
    )
    from .fatigue_calculator.safte_classic import (
        simulate_classic_safte,
        ClassicSafteParams,
    )
    from .fatigue_calculator.safte_model import SleepEpisode, PhaseShift
    from .fatigue_calculator.safte_data import (
        ColumnMap,
        load_event_csv,
        build_epoch_tables,
        derive_bedtime_hour,
        schedule_from_epoch_table,
    )
except ImportError:
    # Fallback for direct execution
    from fatigue_calculator.core import (
        enhanced_simulate_cognitive_performance,
        enhanced_circadian_process,
        SAFTEModel,
    )
    from fatigue_calculator.safte_classic import (
        simulate_classic_safte,
        ClassicSafteParams,
    )
    from fatigue_calculator.safte_model import SleepEpisode, PhaseShift
    from fatigue_calculator.safte_data import (
        ColumnMap,
        load_event_csv,
        build_epoch_tables,
        derive_bedtime_hour,
        schedule_from_epoch_table,
    )

_LOGGER = get_logger(__name__)

# =============================================================================
# Data Classes
# =============================================================================


@dataclass(frozen=True, slots=True)
class UserProfile:
    """User profile for fatigue modeling."""
    
    age: int = 30
    sex: str = "other"
    chronotype_offset: float = 0.0  # hours (negative = morning person)
    genetic_profile: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SleepScheduleInput:
    """Sleep schedule parameters."""
    
    quality: float = 0.8  # 0-1 scale
    duration: float = 7.0  # hours
    bedtime: int = 23  # hour (0-23)
    waketime: int = 7  # hour (0-23)
    total_sleep_debt: float = 0.0  # hours


@dataclass(frozen=True, slots=True)
class WorkScheduleInput:
    """Work schedule parameters."""
    
    has_work: bool = True
    work_start: int = 9  # hour (0-23)
    work_end: int = 17  # hour (0-23)
    work_hours: int = 8
    cognitive_load: int = 1  # 0-3 scale


@dataclass(slots=True)
class FatigueAnalysisResult:
    """Results from fatigue analysis."""
    
    time_points: List[int]
    performances: List[float]
    circadian_values: List[float]
    analysis: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    recommendations: List[str]
    model_used: str
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)


# =============================================================================
# Schedule Building Functions
# =============================================================================


def build_enhanced_schedules(
    prediction_hours: int,
    user_profile: UserProfile,
    sleep_schedule: SleepScheduleInput,
    work_schedule: WorkScheduleInput,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Build enhanced sleep and work schedules for SAFTE simulation.
    
    Args:
        prediction_hours: Number of hours to simulate
        user_profile: User profile with chronotype offset
        sleep_schedule: Sleep parameters
        work_schedule: Work parameters
        
    Returns:
        Tuple of (enhanced_sleep_schedule, enhanced_work_schedule)
    """
    enhanced_sleep_schedule: Dict[str, Any] = {
        "quality": float(sleep_schedule.quality),
        "quantity": float(sleep_schedule.duration),
        "debt": float(sleep_schedule.total_sleep_debt),
    }

    # Calculate precise sleep boundaries accounting for fractional duration
    # The duration field may contain fractional hours (e.g., 8.5 hours)
    # We need to mark sleep states accurately even when duration is fractional
    sleep_duration_hours = float(sleep_schedule.duration)
    
    for hour in range(prediction_hours):
        hour_of_day = hour % 24
        adjusted_bedtime = int(
            (sleep_schedule.bedtime + user_profile.chronotype_offset) % 24
        )
        adjusted_waketime = int(
            (sleep_schedule.waketime + user_profile.chronotype_offset) % 24
        )
        
        # Calculate if this hour should be marked as sleep
        # Account for fractional duration by checking if hour is within sleep window
        if adjusted_bedtime <= adjusted_waketime:
            # Sleep doesn't span midnight
            is_sleep_time = adjusted_bedtime <= hour_of_day < adjusted_waketime
        else:
            # Sleep spans midnight (e.g., 22:00 to 6:00)
            is_sleep_time = (
                hour_of_day >= adjusted_bedtime or 
                hour_of_day < adjusted_waketime
            )
        
        # If we're at the waketime hour and duration is fractional,
        # we may need to mark partial sleep. However, since we're working
        # with integer hours, we rely on the waketime being adjusted upward
        # in the caller to capture fractional hours (see scheduling_core.py)
        enhanced_sleep_schedule[hour] = is_sleep_time

    enhanced_work_schedule: Dict[str, Any] = {
        "load_rating": (
            int(work_schedule.cognitive_load) if work_schedule.has_work else 0
        ),
        "daily_hours": (
            int(work_schedule.work_hours) if work_schedule.has_work else 0
        ),
    }

    for hour in range(prediction_hours):
        hour_of_day = hour % 24
        if work_schedule.has_work:
            day_of_week = (hour // 24) % 7
            is_weekend = day_of_week >= 5
            if not is_weekend:
                if work_schedule.work_start <= work_schedule.work_end:
                    is_work_time = (
                        work_schedule.work_start <= hour_of_day < 
                        work_schedule.work_end
                    )
                else:
                    is_work_time = (
                        hour_of_day >= work_schedule.work_start or 
                        hour_of_day < work_schedule.work_end
                    )
            else:
                is_work_time = False
        else:
            is_work_time = False
        enhanced_work_schedule[hour] = is_work_time

    return enhanced_sleep_schedule, enhanced_work_schedule


# =============================================================================
# Garmin Data Conversion
# =============================================================================


def garmin_sleep_to_schedule(
    sleep_df: pd.DataFrame,
    start_date: datetime.date,
    days: int = 3,
) -> Tuple[SleepScheduleInput, Dict[int, bool]]:
    """Convert Garmin sleep data to SAFTE schedule format.
    
    Args:
        sleep_df: DataFrame with Garmin sleep data
        start_date: Start date for simulation
        days: Number of days to simulate
        
    Returns:
        Tuple of (SleepScheduleInput, hour-indexed sleep map)
    """
    if sleep_df.empty:
        # Return defaults if no data
        return SleepScheduleInput(), {}
    
    # Calculate average sleep metrics
    avg_quality = float(sleep_df.get("sleep_score", pd.Series([80])).mean() / 100.0)
    avg_duration = float(sleep_df.get("total_sleep_minutes", pd.Series([420])).mean() / 60.0)
    
    # Extract typical bedtime and waketime
    if "sleep_start" in sleep_df.columns:
        bedtimes = pd.to_datetime(sleep_df["sleep_start"]).dt.hour
        avg_bedtime = int(bedtimes.median()) if not bedtimes.empty else 23
    else:
        avg_bedtime = 23
        
    if "sleep_end" in sleep_df.columns:
        waketimes = pd.to_datetime(sleep_df["sleep_end"]).dt.hour
        avg_waketime = int(waketimes.median()) if not waketimes.empty else 7
    else:
        avg_waketime = 7
    
    # Calculate sleep debt (simplified)
    ideal_sleep = 8.0
    recent_deficit = max(0.0, ideal_sleep - avg_duration) * min(days, 7)
    
    schedule_input = SleepScheduleInput(
        quality=min(1.0, max(0.0, avg_quality)),
        duration=avg_duration,
        bedtime=avg_bedtime,
        waketime=avg_waketime,
        total_sleep_debt=recent_deficit,
    )
    
    # Build hour-indexed sleep map
    total_hours = days * 24
    sleep_map: Dict[int, bool] = {}
    
    for hour in range(total_hours):
        hour_of_day = hour % 24
        if avg_bedtime <= avg_waketime:
            is_sleep = avg_bedtime <= hour_of_day < avg_waketime
        else:
            is_sleep = hour_of_day >= avg_bedtime or hour_of_day < avg_waketime
        sleep_map[hour] = is_sleep
    
    return schedule_input, sleep_map


def garmin_stress_to_workload(
    stress_df: pd.DataFrame,
    activity_df: Optional[pd.DataFrame] = None,
) -> WorkScheduleInput:
    """Convert Garmin stress and activity data to work schedule.
    
    Args:
        stress_df: DataFrame with Garmin stress data
        activity_df: Optional DataFrame with activity data
        
    Returns:
        WorkScheduleInput with derived parameters
    """
    if stress_df.empty:
        return WorkScheduleInput()
    
    # Estimate cognitive load from stress levels
    avg_stress = float(stress_df.get("stress_level", pd.Series([30])).mean())
    
    # Map stress to cognitive load (0-3 scale)
    if avg_stress < 25:
        cognitive_load = 0
    elif avg_stress < 50:
        cognitive_load = 1
    elif avg_stress < 75:
        cognitive_load = 2
    else:
        cognitive_load = 3
    
    # Estimate work hours from activity patterns
    work_hours = 8  # Default
    work_start = 9
    work_end = 17
    
    if activity_df is not None and not activity_df.empty:
        if "active_calories" in activity_df.columns:
            # Higher activity might indicate longer work
            avg_calories = float(activity_df["active_calories"].mean())
            if avg_calories > 500:
                work_hours = min(12, work_hours + 2)
    
    return WorkScheduleInput(
        has_work=True,
        work_start=work_start,
        work_end=work_end,
        work_hours=work_hours,
        cognitive_load=cognitive_load,
    )


# =============================================================================
# Simulation Functions
# =============================================================================


def run_fatigue_simulation(
    prediction_hours: int,
    user_profile: UserProfile,
    sleep_schedule: SleepScheduleInput,
    work_schedule: WorkScheduleInput,
    model_type: str = "advanced",
) -> Tuple[List[int], List[float], List[float]]:
    """Run SAFTE fatigue simulation.
    
    Args:
        prediction_hours: Hours to simulate
        user_profile: User profile
        sleep_schedule: Sleep parameters
        work_schedule: Work parameters
        model_type: "advanced" or "classic"
        
    Returns:
        Tuple of (time_points, performances, circadian_values)
    """
    enhanced_sleep_schedule, enhanced_work_schedule = build_enhanced_schedules(
        prediction_hours, user_profile, sleep_schedule, work_schedule
    )

    individual_profile = {
        "genetic_profile": list(user_profile.genetic_profile),
        "sex": user_profile.sex,
        "age": user_profile.age,
        "chronotype_offset": user_profile.chronotype_offset,
    }

    if model_type == "classic":
        # Build classic schedule
        is_asleep_by_hour = {
            h: bool(enhanced_sleep_schedule.get(h, False)) 
            for h in range(prediction_hours)
        }
        bedtime_hour = float(sleep_schedule.bedtime)
        
        start_dt = datetime.datetime.now()
        t0_h = start_dt.hour + start_dt.minute / 60.0 + start_dt.second / 3600.0
        
        time_points, performances = simulate_classic_safte(
            prediction_hours,
            is_asleep_by_hour,
            bedtime_hour,
            t0_local_hour_24=float(t0_h),
        )
        
        # Generate circadian values
        circadian_values = [
            enhanced_circadian_process(float((t0_h + m / 60.0) % 24.0), user_profile.chronotype_offset)
            for m in time_points
        ]
        
        return time_points, performances, circadian_values
    else:
        # Advanced SAFTE
        time_points, circadian_values, performances = (
            enhanced_simulate_cognitive_performance(
                prediction_hours,
                enhanced_sleep_schedule,
                enhanced_work_schedule,
                individual_profile,
                {},
            )
        )
        return time_points, performances, circadian_values


def compute_fatigue_analysis(
    performances: List[float],
) -> Dict[str, Any]:
    """Compute statistical analysis of fatigue predictions.
    
    Args:
        performances: List of performance values
        
    Returns:
        Dictionary with analysis metrics
    """
    performances_array = np.array(performances, dtype=float)
    # Filter out NaN values
    valid_performances = performances_array[~np.isnan(performances_array)]
    
    if len(valid_performances) == 0:
        return {
            "avg": 0.0,
            "min": 0.0,
            "max": 0.0,
            "std": 0.0,
            "zones": [0, 0, 0, 0],
            "risk": 100.0,
        }
    
    avg_performance = float(np.mean(valid_performances))
    min_performance = float(np.min(valid_performances))
    max_performance = float(np.max(valid_performances))
    std_performance = float(np.std(valid_performances))

    # SAFTE/FAST-style operational zones (commonly cited in aviation fatigue ops):
    # - >= 90%: low fatigue risk ("well-rested")
    # - > 77% and < 90%: caution / transitional range
    # - > 70% and <= 77%: high fatigue risk (often compared to ~0.05% BAC impairment)
    # - <= 70%: severe impairment (often compared to ~0.08% BAC impairment)
    #
    # Note: Thresholds are presented in the UI with citations (ICAO/FAA/NASA).
    low_risk_hours = int(np.sum(valid_performances >= 90))
    caution_hours = int(np.sum((valid_performances < 90) & (valid_performances > 77)))
    high_risk_hours = int(np.sum((valid_performances <= 77) & (valid_performances > 70)))
    severe_hours = int(np.sum(valid_performances <= 70))

    total_hours = int(len(valid_performances))
    # "Risk" is defined as time at/under the high-risk threshold (<=77%).
    risk_percentage = float((high_risk_hours + severe_hours) / max(1, total_hours) * 100.0)

    return {
        "avg": avg_performance,
        "min": min_performance,
        "max": max_performance,
        "std": std_performance,
        "zones": [low_risk_hours, caution_hours, high_risk_hours, severe_hours],
        "risk": risk_percentage,
    }


def compute_risk_assessment(
    sleep_schedule: SleepScheduleInput,
    work_schedule: WorkScheduleInput,
    user_profile: UserProfile,
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute comprehensive risk assessment.
    
    Args:
        sleep_schedule: Sleep parameters
        work_schedule: Work parameters
        user_profile: User profile
        analysis: Performance analysis results
        
    Returns:
        Dictionary with risk factors and scores
    """
    # Calculate individual risk factors
    sleep_debt_risk = max(0.0, min(20.0, (7.0 - sleep_schedule.duration) * 3.0))
    quality_risk = max(0.0, min(25.0, (0.8 - sleep_schedule.quality) * 30.0))
    circadian_risk = abs(user_profile.chronotype_offset) * 4.0
    
    work_hours = work_schedule.work_hours if work_schedule.has_work else 0
    work_risk = max(0.0, min(15.0, (work_hours - 8) * 2.5))
    cognitive_risk = work_schedule.cognitive_load * 4.0 if work_schedule.has_work else 0.0
    age_risk = max(0.0, (user_profile.age - 40) * 0.2) if user_profile.age > 40 else 0.0
    
    total_risk = (
        sleep_debt_risk + quality_risk + circadian_risk + 
        work_risk + cognitive_risk + age_risk
    )
    
    # Determine risk level
    if total_risk < 10:
        risk_level = "Very Low"
    elif total_risk < 20:
        risk_level = "Low"
    elif total_risk < 35:
        risk_level = "Moderate"
    elif total_risk < 50:
        risk_level = "High"
    else:
        risk_level = "Critical"
    
    return {
        "total_risk": total_risk,
        "risk_level": risk_level,
        "factors": {
            "sleep_debt": sleep_debt_risk,
            "sleep_quality": quality_risk,
            "circadian_misalignment": circadian_risk,
            "work_hours": work_risk,
            "cognitive_load": cognitive_risk,
            "age": age_risk,
        },
    }


def generate_recommendations(
    risk_assessment: Dict[str, Any],
    sleep_schedule: SleepScheduleInput,
    analysis: Dict[str, Any],
) -> List[str]:
    """Generate personalized recommendations based on risk assessment.
    
    Args:
        risk_assessment: Risk assessment results
        sleep_schedule: Sleep parameters
        analysis: Performance analysis
        
    Returns:
        List of recommendation strings
    """
    recommendations: List[str] = []
    factors = risk_assessment.get("factors", {})
    
    if factors.get("sleep_debt", 0) > 5:
        deficit_minutes = int((7.0 - sleep_schedule.duration) * 60)
        recommendations.append(
            f"💤 Increase sleep duration by {deficit_minutes} minutes to reduce fatigue risk"
        )
    
    if factors.get("sleep_quality", 0) > 5:
        recommendations.append(
            "🌙 Improve sleep quality: reduce screen time before bed, maintain consistent schedule"
        )
    
    if factors.get("circadian_misalignment", 0) > 5:
        recommendations.append(
            "⏰ Consider light exposure therapy to align circadian rhythm"
        )
    
    if factors.get("work_hours", 0) > 5:
        recommendations.append(
            "⚡ Reduce work hours or schedule strategic breaks during extended shifts"
        )
    
    if factors.get("cognitive_load", 0) > 5:
        recommendations.append(
            "🧠 Lower cognitive demands when possible; take mental breaks"
        )
    
    if analysis.get("risk", 0) > 30:
        recommendations.append(
            "⚠️ High fatigue risk detected: avoid safety-critical tasks during predicted low periods"
        )
    
    if not recommendations:
        recommendations.append(
            "✅ Current parameters are well optimized for fatigue management!"
        )
    
    return recommendations


# =============================================================================
# Automated Garmin-driven prediction
# =============================================================================


def _build_user_profile_from_context(
    user_context: Dict[str, Any] | None,
) -> UserProfile:
    """Build UserProfile from active user context."""
    age = int(user_context.get("age_years", 30)) if user_context else 30
    sex = str(user_context.get("sex", "other")) if user_context else "other"
    chronotype = (
        float(user_context.get("chronotype_offset", 0.0)) if user_context else 0.0
    )
    genetic_profile = tuple(user_context.get("genetic_profile", ())) if user_context else tuple()
    return UserProfile(
        age=age,
        sex=sex,
        chronotype_offset=chronotype,
        genetic_profile=genetic_profile,
    )


def _normalize_sleep_minutes(sleep_df: pd.DataFrame) -> pd.DataFrame:
    """Ensure total sleep minutes column is available for schedule derivation."""
    df = sleep_df.copy()
    if "total_sleep_minutes" not in df.columns:
        if "tst_minutes" in df.columns:
            df["total_sleep_minutes"] = df["tst_minutes"]
        elif "total_sleep_seconds" in df.columns:
            df["total_sleep_minutes"] = df["total_sleep_seconds"].fillna(0) / 60.0
    return df


def run_garmin_fatigue_prediction(
    *,
    user_context: Dict[str, Any] | None = None,
    credentials: GarminCredentials | None = None,
    prediction_days: int = 5,
    lookback_days: int = 2,
    include_spo2: bool = True,
    include_respiration: bool = True,
    include_body_battery: bool = True,
    model_type: str = "advanced",
) -> Tuple[FatigueAnalysisResult, GarminWellnessData, pd.DataFrame]:
    """Fetch latest Garmin data and run a fatigue prediction.

    Args:
        user_context: Active user profile context (age_years, sex, chronotype_offset).
        credentials: Garmin Connect credentials. Falls back to environment variables.
        prediction_days: Number of days to forecast (default 5).
        lookback_days: Number of past days to fetch from Garmin (>=1).
        include_spo2: Whether to request SpO₂ data.
        include_respiration: Whether to request respiration data.
        include_body_battery: Whether to request body battery data.
        model_type: "advanced" (default) or "classic" SAFTE.

    Returns:
        Tuple of (FatigueAnalysisResult, GarminWellnessData, daily_summary_df).

    Raises:
        RuntimeError: If credentials are missing.
        ValueError: If no sleep data is returned.
    """
    if lookback_days <= 0:
        raise ValueError("lookback_days must be positive")

    garmin_credentials = credentials or load_credentials_from_env()
    if garmin_credentials is None:
        msg = "GARMIN_EMAIL and GARMIN_PASSWORD must be set in the environment or provided explicitly."
        raise RuntimeError(msg)

    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=lookback_days - 1)

    _LOGGER.info(
        "Fetching Garmin data for %s to %s (lookback=%d days)",
        start_date,
        end_date,
        lookback_days,
    )

    garmin_data = import_garmin_data(
        credentials=garmin_credentials,
        start_date=start_date,
        end_date=end_date,
        include_spo2=include_spo2,
        include_respiration=include_respiration,
        include_body_battery=include_body_battery,
    )

    if garmin_data.sleep_df.empty:
        raise ValueError("No Garmin sleep data available for the requested window.")

    garmin_data.sleep_df = _normalize_sleep_minutes(garmin_data.sleep_df)

    sleep_schedule, _ = garmin_sleep_to_schedule(
        garmin_data.sleep_df,
        start_date=end_date,
        days=prediction_days,
    )
    work_schedule = garmin_stress_to_workload(
        garmin_data.stress_df,
        garmin_data.activity_df,
    )
    user_profile = _build_user_profile_from_context(user_context)

    result = run_integrated_fatigue_analysis(
        garmin_sleep_df=garmin_data.sleep_df,
        garmin_stress_df=garmin_data.stress_df,
        garmin_activity_df=garmin_data.activity_df,
        user_profile=user_profile,
        sleep_schedule=sleep_schedule,
        work_schedule=work_schedule,
        prediction_days=prediction_days,
        model_type=model_type,
    )

    daily_summary = get_daily_physiology_summary(garmin_data)
    return result, garmin_data, daily_summary


# =============================================================================
# Assessment-driven prediction (wrist monitoring preferred, clinical fallback)
# =============================================================================


def _clamp_quality(value: float) -> float:
    """Clamp sleep quality to a safe 0.3–1.0 range."""
    return float(max(0.3, min(1.0, value)))


def _build_sleep_from_wrist_row(
    row: pd.Series,
    *,
    bedtime_hour: int,
    waketime_hour: int,
) -> SleepScheduleInput:
    """Construct sleep schedule from wrist monitoring metrics.

    Args:
        row: Latest wrist monitoring row (Garmin daily metrics).
        bedtime_hour: Default bedtime hour (0..23) used when wrist data lacks a time window.
        waketime_hour: Default waketime hour (0..23) used when wrist data lacks a time window.

    Note:
        sleep_score is used as the primary "efficiency" metric for SAFTE calculations.
        This composite score (0-100) better reflects overall sleep quality and restorative
        value than raw TST/TIB efficiency. Falls back to sleep_efficiency if unavailable.
    """
    duration = float(row.get("sleep_duration_hours", 0.0) or 0.0)
    
    # Priority: sleep_score (composite quality) > sleep_efficiency (TST/TIB ratio)
    # sleep_score is the preferred metric as it incorporates sleep stages, disturbances,
    # and overall restorative quality - better proxy for SAFTE sleep effectiveness
    quality_candidates: list[float] = []
    if pd.notna(row.get("sleep_score")):
        quality_candidates.append(float(row["sleep_score"]) / 100.0)
    if pd.notna(row.get("sleep_efficiency")):
        quality_candidates.append(float(row["sleep_efficiency"]) / 100.0)
    quality = _clamp_quality(quality_candidates[0] if quality_candidates else 0.8)
    sleep_debt = max(0.0, (7.0 - duration)) if duration > 0 else 0.0
    return SleepScheduleInput(
        quality=quality,
        duration=duration if duration > 0 else 7.0,
        bedtime=int(bedtime_hour),
        waketime=int(waketime_hour),
        total_sleep_debt=sleep_debt,
    )


def _build_work_from_wrist_row(
    row: pd.Series,
    *,
    duty_start_hour: int,
    duty_end_hour: int,
) -> WorkScheduleInput:
    """Construct work schedule using wrist stress/activity proxies.

    Args:
        row: Latest wrist monitoring row (Garmin daily metrics).
        duty_start_hour: Default duty start hour (0..23).
        duty_end_hour: Default duty end hour (0..23).
    """
    cognitive_load = 1
    try:
        stress_val = float(row.get("stress_score"))
        if stress_val < 25:
            cognitive_load = 0
        elif stress_val < 50:
            cognitive_load = 1
        elif stress_val < 75:
            cognitive_load = 2
        else:
            cognitive_load = 3
    except Exception:
        cognitive_load = 1
    if int(duty_start_hour) <= int(duty_end_hour):
        work_hours = int(duty_end_hour) - int(duty_start_hour)
    else:
        work_hours = (24 - int(duty_start_hour)) + int(duty_end_hour)
    return WorkScheduleInput(
        has_work=True,
        work_start=int(duty_start_hour),
        work_end=int(duty_end_hour),
        work_hours=int(max(0, min(16, work_hours))),
        cognitive_load=cognitive_load,
    )


def _build_sleep_from_clinical(
    scales: Any,
    *,
    bedtime_hour: int,
    waketime_hour: int,
    typical_sleep_duration_hours: float,
) -> SleepScheduleInput:
    """Construct sleep schedule from clinical subjective assessment.

    Clinical scales do not encode bedtime/waketime, so these are taken from
    the stored fatigue profile defaults (or app defaults).
    """
    psqi = getattr(scales, "pittsburgh_sleep_quality_index", None)
    if psqi is None:
        quality = 0.8
    else:
        try:
            quality = _clamp_quality(1.0 - float(psqi) / 21.0)
        except Exception:
            quality = 0.8

    epworth = getattr(scales, "epworth_sleepiness_scale", None)
    sleep_debt = 0.0
    if epworth is not None:
        try:
            epw = float(epworth)
            sleep_debt = max(0.0, min(8.0, (epw - 8.0) * 0.25))
        except Exception:
            sleep_debt = 0.0

    return SleepScheduleInput(
        quality=quality,
        duration=float(typical_sleep_duration_hours),
        bedtime=int(bedtime_hour),
        waketime=int(waketime_hour),
        total_sleep_debt=sleep_debt,
    )


def run_assessment_fatigue_prediction(
    *,
    user_context: Dict[str, Any] | None,
    user_id: str | None,
    prediction_days: int = 5,
    model_type: str = "advanced",
) -> Tuple[FatigueAnalysisResult, str, pd.DataFrame | None]:
    """Run fatigue forecast using assessment data with priority rules.

    Priority:
    1) Wrist monitoring (garmin_daily_metrics) if available.
    2) Clinical subjective assessment if wrist data is missing.
    3) Garmin Connect fetch (GARMIN_EMAIL/GARMIN_PASSWORD) if configured.
    4) Default schedule if neither is available.

    Returns:
        result, source_label, wrist_dataframe_or_none
    """
    user_profile = _build_user_profile_from_context(user_context)
    sleep_schedule: SleepScheduleInput | None = None
    work_schedule: WorkScheduleInput | None = None
    wrist_df: pd.DataFrame | None = None
    source = "default"

    db = get_database() if get_database is not None else None
    fatigue_defaults: Dict[str, Any] = {}

    if db is not None and user_id and hasattr(db, "get_fatigue_profile_settings"):
        try:
            prof = db.get_fatigue_profile_settings(user_id)  # type: ignore[attr-defined]
            if prof is not None:
                fatigue_defaults = {
                    "bedtime_hour": int(prof.typical_bedtime_hour),
                    "waketime_hour": int(prof.typical_waketime_hour),
                    "duty_start_hour": int(prof.duty_start_hour),
                    "duty_end_hour": int(prof.duty_end_hour),
                    "typical_sleep_duration_hours": float(prof.typical_sleep_duration_hours),
                    "typical_sleep_quality": float(prof.typical_sleep_quality),
                    "include_weekends": bool(prof.include_weekends),
                }
        except Exception:
            fatigue_defaults = {}

    bedtime_hour = int(fatigue_defaults.get("bedtime_hour", 23))
    waketime_hour = int(fatigue_defaults.get("waketime_hour", 7))
    duty_start_hour = int(fatigue_defaults.get("duty_start_hour", 9))
    duty_end_hour = int(fatigue_defaults.get("duty_end_hour", 17))
    typical_sleep_duration_hours = float(fatigue_defaults.get("typical_sleep_duration_hours", 7.0))
    typical_sleep_quality = float(fatigue_defaults.get("typical_sleep_quality", 0.8))

    # 1) Wrist monitoring (assessment tab → wrist monitoring history)
    if db is not None and user_id:
        try:
            wrist_df = db.get_garmin_daily_dataframe(user_id, limit=30)
            if wrist_df is not None and not wrist_df.empty:
                wrist_df = wrist_df.sort_values("metric_date", ascending=False)
                latest = wrist_df.iloc[0]
                sleep_schedule = _build_sleep_from_wrist_row(
                    latest,
                    bedtime_hour=bedtime_hour,
                    waketime_hour=waketime_hour,
                )
                work_schedule = _build_work_from_wrist_row(
                    latest,
                    duty_start_hour=duty_start_hour,
                    duty_end_hour=duty_end_hour,
                )
                source = "wrist_monitoring"
        except Exception:
            wrist_df = None

    # 2) Subjective clinical assessment (sleep quality)
    if sleep_schedule is None and db is not None and user_id:
        try:
            scales_history = db.get_clinical_scales_history(user_id, limit=1)
            if scales_history:
                sleep_schedule = _build_sleep_from_clinical(
                    scales_history[0],
                    bedtime_hour=bedtime_hour,
                    waketime_hour=waketime_hour,
                    typical_sleep_duration_hours=typical_sleep_duration_hours,
                )
                if duty_start_hour <= duty_end_hour:
                    duty_hours = duty_end_hour - duty_start_hour
                else:
                    duty_hours = (24 - duty_start_hour) + duty_end_hour
                work_schedule = WorkScheduleInput(
                    has_work=True,
                    work_start=duty_start_hour,
                    work_end=duty_end_hour,
                    work_hours=int(max(0, min(16, duty_hours))),
                    cognitive_load=1,
                )
                source = "clinical_assessment"
        except Exception:
            pass

    # 3) Garmin Connect fallback (only if credentials are configured)
    if sleep_schedule is None:
        garmin_credentials = load_credentials_from_env()
        if garmin_credentials is not None:
            try:
                garmin_result, _garmin_data, daily_summary_df = run_garmin_fatigue_prediction(
                    user_context=user_context,
                    credentials=garmin_credentials,
                    prediction_days=prediction_days,
                    lookback_days=2,
                    model_type=model_type,
                )
                return garmin_result, "garmin_connect", daily_summary_df
            except ValueError as exc:
                # Common, non-fatal: no data returned for requested window
                _LOGGER.warning("Garmin Connect fatigue fallback unavailable: %s", exc)
            except Exception as exc:  # pragma: no cover - network/provider variability
                log_exception(_LOGGER, "Garmin Connect fatigue fallback failed", exc)

    # 4) Default fallback
    if sleep_schedule is None:
        sleep_debt = max(0.0, 7.5 - typical_sleep_duration_hours)
        sleep_schedule = SleepScheduleInput(
            quality=_clamp_quality(typical_sleep_quality),
            duration=float(typical_sleep_duration_hours),
            bedtime=int(bedtime_hour),
            waketime=int(waketime_hour),
            total_sleep_debt=float(sleep_debt),
        )
        if duty_start_hour <= duty_end_hour:
            duty_hours = duty_end_hour - duty_start_hour
        else:
            duty_hours = (24 - duty_start_hour) + duty_end_hour
        work_schedule = WorkScheduleInput(
            has_work=True,
            work_start=int(duty_start_hour),
            work_end=int(duty_end_hour),
            work_hours=int(max(0, min(16, duty_hours))),
            cognitive_load=1,
        )
        source = "profile_defaults" if fatigue_defaults else "default"

    result = run_integrated_fatigue_analysis(
        garmin_sleep_df=None,
        garmin_stress_df=None,
        garmin_activity_df=None,
        user_profile=user_profile,
        sleep_schedule=sleep_schedule,
        work_schedule=work_schedule,
        prediction_days=prediction_days,
        model_type=model_type,
    )

    return result, source, wrist_df


# =============================================================================
# DataFrame Building
# =============================================================================


def build_fatigue_dataframe(
    time_points: List[int],
    performances: List[float],
    circadian_values: Optional[List[float]] = None,
) -> pd.DataFrame:
    """Build DataFrame from simulation results.
    
    Args:
        time_points: Time points (minutes or hours)
        performances: Performance values
        circadian_values: Optional circadian rhythm values
        
    Returns:
        DataFrame with DateTime, Hour, Day, Performance columns
    """
    start_datetime = datetime.datetime.now()
    
    # Detect whether time_points are minute indices or hourly indices
    if len(time_points) >= 2 and (time_points[1] - time_points[0]) <= 30:
        # Minute indices
        datetimes = [
            start_datetime + datetime.timedelta(minutes=int(tp))
            for tp in time_points
        ]
    else:
        # Hourly indices
        datetimes = [
            start_datetime + datetime.timedelta(hours=int(tp))
            for tp in time_points
        ]
    
    df = pd.DataFrame({
        "DateTime": datetimes,
        "Hour": [dt.hour for dt in datetimes],
        "Day": [((dt - datetimes[0]).days + 1) for dt in datetimes],
        "Performance": performances,
    })
    
    if circadian_values is not None:
        df["Circadian"] = circadian_values
    
    return df


# =============================================================================
# Main Integration Function
# =============================================================================


def run_integrated_fatigue_analysis(
    garmin_sleep_df: Optional[pd.DataFrame] = None,
    garmin_stress_df: Optional[pd.DataFrame] = None,
    garmin_activity_df: Optional[pd.DataFrame] = None,
    user_profile: Optional[UserProfile] = None,
    sleep_schedule: Optional[SleepScheduleInput] = None,
    work_schedule: Optional[WorkScheduleInput] = None,
    prediction_days: int = 3,
    model_type: str = "advanced",
) -> FatigueAnalysisResult:
    """Run integrated fatigue analysis combining Garmin data with SAFTE model.
    
    Args:
        garmin_sleep_df: Optional Garmin sleep data
        garmin_stress_df: Optional Garmin stress data
        garmin_activity_df: Optional Garmin activity data
        user_profile: Optional user profile (uses defaults if None)
        sleep_schedule: Optional sleep schedule (derived from Garmin if None)
        work_schedule: Optional work schedule (derived from Garmin if None)
        prediction_days: Number of days to predict
        model_type: "advanced" or "classic" SAFTE model
        
    Returns:
        FatigueAnalysisResult with predictions and analysis
    """
    # Use defaults or derive from Garmin data
    if user_profile is None:
        user_profile = UserProfile()
    
    if sleep_schedule is None:
        if garmin_sleep_df is not None and not garmin_sleep_df.empty:
            sleep_schedule, _ = garmin_sleep_to_schedule(
                garmin_sleep_df,
                datetime.date.today(),
                prediction_days,
            )
        else:
            sleep_schedule = SleepScheduleInput()
    
    if work_schedule is None:
        if garmin_stress_df is not None:
            work_schedule = garmin_stress_to_workload(
                garmin_stress_df,
                garmin_activity_df,
            )
        else:
            work_schedule = WorkScheduleInput()
    
    # Run simulation
    prediction_hours = prediction_days * 24
    time_points, performances, circadian_values = run_fatigue_simulation(
        prediction_hours,
        user_profile,
        sleep_schedule,
        work_schedule,
        model_type,
    )
    
    # Compute analysis
    analysis = compute_fatigue_analysis(performances)
    
    # Compute risk assessment
    risk_assessment = compute_risk_assessment(
        sleep_schedule,
        work_schedule,
        user_profile,
        analysis,
    )
    
    # Generate recommendations
    recommendations = generate_recommendations(
        risk_assessment,
        sleep_schedule,
        analysis,
    )
    
    return FatigueAnalysisResult(
        time_points=time_points,
        performances=performances,
        circadian_values=circadian_values,
        analysis=analysis,
        risk_assessment=risk_assessment,
        recommendations=recommendations,
        model_used=model_type,
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Data classes
    "UserProfile",
    "SleepScheduleInput",
    "WorkScheduleInput",
    "FatigueAnalysisResult",
    # Functions
    "build_enhanced_schedules",
    "garmin_sleep_to_schedule",
    "garmin_stress_to_workload",
    "run_fatigue_simulation",
    "compute_fatigue_analysis",
    "compute_risk_assessment",
    "generate_recommendations",
    "build_fatigue_dataframe",
    "run_integrated_fatigue_analysis",
    "run_garmin_fatigue_prediction",
    # Re-exports from fatigue_calculator
    "enhanced_circadian_process",
    "SleepEpisode",
    "PhaseShift",
]

