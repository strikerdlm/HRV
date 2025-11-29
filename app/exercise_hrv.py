"""Exercise HRV Analysis Module.

This module provides specialized analysis for exercise and recovery HRV patterns,
including pre/during/post exercise comparisons, heart rate recovery analysis,
parasympathetic reactivation curves, and training load quantification.

Author: Dr. Diego Malpica, MD
        Aerospace Medicine Specialist
        National University of Colombia

References:
    - Buchheit, M. (2014). Monitoring training status with HR measures.
      Frontiers in Physiology, 5, 73.
    - Stanley, J., et al. (2013). Cardiac parasympathetic reactivation following
      exercise. Sports Medicine, 43(12), 1259-1277.
    - Plews, D. J., et al. (2013). Training adaptation and HRV in elite athletes.
      Journal of Strength and Conditioning Research, 27(6), 1705-1714.
    - Daanen, H. A., et al. (2012). Heart rate recovery. Sports Medicine, 42(5), 433-447.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta, timezone
from enum import Enum
from typing import Any, Final

import numpy as np
from numpy.typing import NDArray
import pandas as pd
from scipy import stats
from scipy.optimize import curve_fit

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Heart rate recovery windows (seconds after exercise cessation)
HRR_WINDOW_30S: Final[int] = 30
HRR_WINDOW_60S: Final[int] = 60
HRR_WINDOW_120S: Final[int] = 120

# TRIMP zones (percentage of HR reserve)
TRIMP_ZONE_1: Final[tuple[float, float]] = (0.50, 0.60)  # Recovery
TRIMP_ZONE_2: Final[tuple[float, float]] = (0.60, 0.70)  # Aerobic
TRIMP_ZONE_3: Final[tuple[float, float]] = (0.70, 0.80)  # Tempo
TRIMP_ZONE_4: Final[tuple[float, float]] = (0.80, 0.90)  # Threshold
TRIMP_ZONE_5: Final[tuple[float, float]] = (0.90, 1.00)  # VO2max

# TRIMP weighting factors (Banister, 1991)
TRIMP_WEIGHTS: Final[dict[int, float]] = {
    1: 1.0,
    2: 1.1,
    3: 1.2,
    4: 2.2,
    5: 4.5,
}

# HRV recovery thresholds
HRV_RECOVERY_FAST_MIN: Final[int] = 5  # Minutes for fast recovery
HRV_RECOVERY_SLOW_MIN: Final[int] = 30  # Minutes for slow recovery


class ExerciseIntensity(Enum):
    """Exercise intensity classification."""
    
    RECOVERY = "recovery"
    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"
    MAXIMAL = "maximal"


class RecoveryStatus(Enum):
    """Post-exercise recovery status."""
    
    FULLY_RECOVERED = "fully_recovered"
    MOSTLY_RECOVERED = "mostly_recovered"
    PARTIALLY_RECOVERED = "partially_recovered"
    NOT_RECOVERED = "not_recovered"


class TrainingPhase(Enum):
    """Training periodization phase."""
    
    BASE = "base"
    BUILD = "build"
    PEAK = "peak"
    TAPER = "taper"
    RECOVERY = "recovery"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ExerciseSession:
    """Single exercise session data.
    
    Attributes:
        session_id: Unique session identifier.
        date: Session date.
        start_time: Session start time.
        end_time: Session end time.
        duration_minutes: Total duration in minutes.
        exercise_type: Type of exercise (running, cycling, etc.).
        intensity: Exercise intensity classification.
        hr_data: Heart rate time series (timestamp, HR).
        rr_data: RR interval time series (timestamp, RR_ms).
        max_hr: Maximum heart rate achieved.
        avg_hr: Average heart rate.
        resting_hr: Pre-exercise resting HR.
        hr_reserve_used_pct: Percentage of HR reserve used.
        trimp: Training impulse score.
        notes: Session notes.
    """
    
    session_id: str
    date: date
    start_time: datetime
    end_time: datetime
    duration_minutes: float
    exercise_type: str = "unknown"
    intensity: ExerciseIntensity = ExerciseIntensity.MODERATE
    hr_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    rr_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    max_hr: float = 0.0
    avg_hr: float = 0.0
    resting_hr: float = 60.0
    hr_reserve_used_pct: float = 0.0
    trimp: float = 0.0
    notes: str = ""


@dataclass(slots=True)
class HeartRateRecovery:
    """Heart rate recovery analysis.
    
    Attributes:
        session_id: Associated session ID.
        peak_hr: Peak HR at exercise cessation.
        hr_at_30s: HR 30 seconds post-exercise.
        hr_at_60s: HR 60 seconds post-exercise.
        hr_at_120s: HR 120 seconds post-exercise.
        hrr_30s: HR drop in first 30 seconds.
        hrr_60s: HR drop in first 60 seconds.
        hrr_120s: HR drop in first 120 seconds.
        hrr_rate: Rate of HR decay (bpm/min).
        time_constant_s: Exponential decay time constant.
        recovery_quality: Qualitative recovery assessment.
        percentile: Percentile relative to population norms.
    """
    
    session_id: str
    peak_hr: float
    hr_at_30s: float = 0.0
    hr_at_60s: float = 0.0
    hr_at_120s: float = 0.0
    hrr_30s: float = 0.0
    hrr_60s: float = 0.0
    hrr_120s: float = 0.0
    hrr_rate: float = 0.0
    time_constant_s: float = 0.0
    recovery_quality: str = "unknown"
    percentile: float = 50.0


@dataclass(slots=True)
class ParasympatheticReactivation:
    """Parasympathetic reactivation analysis.
    
    Attributes:
        session_id: Associated session ID.
        time_to_hrv_onset_s: Time until HRV starts recovering.
        time_to_50pct_recovery_s: Time to 50% HRV recovery.
        time_to_full_recovery_s: Time to full HRV recovery.
        rmssd_at_5min: RMSSD 5 minutes post-exercise.
        rmssd_at_15min: RMSSD 15 minutes post-exercise.
        rmssd_at_30min: RMSSD 30 minutes post-exercise.
        recovery_slope: Rate of RMSSD recovery.
        recovery_status: Current recovery status.
    """
    
    session_id: str
    time_to_hrv_onset_s: float = 0.0
    time_to_50pct_recovery_s: float = 0.0
    time_to_full_recovery_s: float = 0.0
    rmssd_at_5min: float = 0.0
    rmssd_at_15min: float = 0.0
    rmssd_at_30min: float = 0.0
    recovery_slope: float = 0.0
    recovery_status: RecoveryStatus = RecoveryStatus.NOT_RECOVERED


@dataclass(slots=True)
class TrainingLoad:
    """Training load metrics.
    
    Attributes:
        date: Assessment date.
        acute_load: Acute training load (7-day).
        chronic_load: Chronic training load (28-day).
        acwr: Acute:Chronic workload ratio.
        monotony: Training monotony.
        strain: Training strain.
        fitness: Fitness (chronic positive adaptation).
        fatigue: Fatigue (acute negative adaptation).
        form: Form (fitness - fatigue).
        injury_risk: Estimated injury risk level.
    """
    
    date: date
    acute_load: float = 0.0
    chronic_load: float = 0.0
    acwr: float = 1.0
    monotony: float = 0.0
    strain: float = 0.0
    fitness: float = 0.0
    fatigue: float = 0.0
    form: float = 0.0
    injury_risk: str = "low"


@dataclass(slots=True)
class ExerciseHRVComparison:
    """Pre/during/post exercise HRV comparison.
    
    Attributes:
        session_id: Associated session ID.
        pre_rmssd: RMSSD before exercise.
        during_rmssd: RMSSD during exercise (if measurable).
        post_rmssd_immediate: RMSSD immediately after.
        post_rmssd_1h: RMSSD 1 hour after.
        post_rmssd_24h: RMSSD 24 hours after.
        suppression_pct: HRV suppression during exercise.
        recovery_pct_1h: Recovery percentage at 1 hour.
        recovery_pct_24h: Recovery percentage at 24 hours.
        supercompensation: Whether supercompensation observed.
    """
    
    session_id: str
    pre_rmssd: float = 0.0
    during_rmssd: float | None = None
    post_rmssd_immediate: float = 0.0
    post_rmssd_1h: float | None = None
    post_rmssd_24h: float | None = None
    suppression_pct: float = 0.0
    recovery_pct_1h: float | None = None
    recovery_pct_24h: float | None = None
    supercompensation: bool = False


# ---------------------------------------------------------------------------
# Heart Rate Recovery Analysis
# ---------------------------------------------------------------------------


def calculate_heart_rate_recovery(
    hr_data: pd.DataFrame,
    exercise_end_time: datetime,
    peak_hr: float | None = None,
) -> HeartRateRecovery | None:
    """Calculate heart rate recovery metrics.
    
    Args:
        hr_data: DataFrame with 'timestamp' and 'heart_rate' columns.
        exercise_end_time: Time when exercise ended.
        peak_hr: Peak HR (auto-detected if None).
        
    Returns:
        HeartRateRecovery or None if insufficient data.
    """
    if hr_data.empty or "timestamp" not in hr_data.columns or "heart_rate" not in hr_data.columns:
        return None
    
    # Ensure timestamp is datetime
    hr_data = hr_data.copy()
    hr_data["timestamp"] = pd.to_datetime(hr_data["timestamp"])
    
    # Filter to recovery period (0-3 minutes post-exercise)
    recovery_start = exercise_end_time
    recovery_end = exercise_end_time + timedelta(minutes=3)
    
    recovery_data = hr_data[
        (hr_data["timestamp"] >= recovery_start) &
        (hr_data["timestamp"] <= recovery_end)
    ].copy()
    
    if len(recovery_data) < 5:
        return None
    
    # Calculate seconds from exercise end
    recovery_data["seconds"] = (recovery_data["timestamp"] - recovery_start).dt.total_seconds()
    
    # Get peak HR (either provided or from data)
    if peak_hr is None:
        # Use HR at exercise end
        pre_end_data = hr_data[hr_data["timestamp"] <= exercise_end_time]
        if not pre_end_data.empty:
            peak_hr = pre_end_data["heart_rate"].iloc[-1]
        else:
            peak_hr = recovery_data["heart_rate"].iloc[0]
    
    # Interpolate HR at standard time points
    def get_hr_at_time(seconds: float) -> float:
        closest = recovery_data.iloc[(recovery_data["seconds"] - seconds).abs().argsort()[:1]]
        return float(closest["heart_rate"].iloc[0]) if not closest.empty else 0.0
    
    hr_30s = get_hr_at_time(30)
    hr_60s = get_hr_at_time(60)
    hr_120s = get_hr_at_time(120)
    
    # Calculate HRR values
    hrr_30s = peak_hr - hr_30s
    hrr_60s = peak_hr - hr_60s
    hrr_120s = peak_hr - hr_120s
    
    # Fit exponential decay to estimate time constant
    try:
        def exp_decay(t: NDArray, a: float, tau: float, c: float) -> NDArray:
            return a * np.exp(-t / tau) + c
        
        t_data = recovery_data["seconds"].values
        hr_values = recovery_data["heart_rate"].values
        
        # Initial guesses
        p0 = [peak_hr - hr_values[-1], 60, hr_values[-1]]
        
        popt, _ = curve_fit(exp_decay, t_data, hr_values, p0=p0, maxfev=1000)
        time_constant = popt[1]
    except Exception:
        time_constant = 0.0
    
    # Calculate recovery rate (bpm/min)
    hrr_rate = hrr_60s  # HRR60 is the standard measure
    
    # Assess recovery quality
    if hrr_60s >= 25:
        recovery_quality = "excellent"
        percentile = 85.0
    elif hrr_60s >= 18:
        recovery_quality = "good"
        percentile = 65.0
    elif hrr_60s >= 12:
        recovery_quality = "average"
        percentile = 45.0
    else:
        recovery_quality = "poor"
        percentile = 25.0
    
    return HeartRateRecovery(
        session_id="",
        peak_hr=peak_hr,
        hr_at_30s=hr_30s,
        hr_at_60s=hr_60s,
        hr_at_120s=hr_120s,
        hrr_30s=hrr_30s,
        hrr_60s=hrr_60s,
        hrr_120s=hrr_120s,
        hrr_rate=hrr_rate,
        time_constant_s=time_constant,
        recovery_quality=recovery_quality,
        percentile=percentile,
    )


# ---------------------------------------------------------------------------
# Parasympathetic Reactivation Analysis
# ---------------------------------------------------------------------------


def analyze_parasympathetic_reactivation(
    rr_data: pd.DataFrame,
    exercise_end_time: datetime,
    baseline_rmssd: float,
) -> ParasympatheticReactivation | None:
    """Analyze parasympathetic reactivation after exercise.
    
    Args:
        rr_data: DataFrame with 'timestamp' and 'rr_ms' columns.
        exercise_end_time: Time when exercise ended.
        baseline_rmssd: Pre-exercise baseline RMSSD.
        
    Returns:
        ParasympatheticReactivation or None if insufficient data.
    """
    if rr_data.empty or baseline_rmssd <= 0:
        return None
    
    # Ensure timestamp is datetime
    rr_data = rr_data.copy()
    rr_data["timestamp"] = pd.to_datetime(rr_data["timestamp"])
    
    # Filter to post-exercise period (0-60 minutes)
    recovery_start = exercise_end_time
    recovery_end = exercise_end_time + timedelta(minutes=60)
    
    recovery_data = rr_data[
        (rr_data["timestamp"] >= recovery_start) &
        (rr_data["timestamp"] <= recovery_end)
    ].copy()
    
    if len(recovery_data) < 30:
        return None
    
    # Calculate RMSSD in 5-minute windows
    recovery_data["minutes"] = (recovery_data["timestamp"] - recovery_start).dt.total_seconds() / 60
    
    def calculate_window_rmssd(df: pd.DataFrame, start_min: float, end_min: float) -> float:
        window = df[(df["minutes"] >= start_min) & (df["minutes"] < end_min)]
        if len(window) < 10:
            return 0.0
        rr = window["rr_ms"].values
        diff = np.diff(rr)
        return float(np.sqrt(np.mean(diff ** 2)))
    
    rmssd_5min = calculate_window_rmssd(recovery_data, 4, 6)
    rmssd_15min = calculate_window_rmssd(recovery_data, 14, 16)
    rmssd_30min = calculate_window_rmssd(recovery_data, 29, 31)
    
    # Find time to HRV onset (when RMSSD starts increasing)
    window_size = 30  # 30 beats
    rmssd_series: list[tuple[float, float]] = []
    
    for i in range(0, len(recovery_data) - window_size, 10):
        window = recovery_data.iloc[i:i + window_size]
        rr = window["rr_ms"].values
        diff = np.diff(rr)
        rmssd = float(np.sqrt(np.mean(diff ** 2)))
        time_min = window["minutes"].mean()
        rmssd_series.append((time_min, rmssd))
    
    # Find onset (first sustained increase)
    onset_time = 0.0
    for i in range(1, len(rmssd_series)):
        if rmssd_series[i][1] > rmssd_series[i-1][1] * 1.1:  # 10% increase
            onset_time = rmssd_series[i][0] * 60  # Convert to seconds
            break
    
    # Find time to 50% recovery
    target_50pct = baseline_rmssd * 0.5
    time_50pct = 0.0
    for time_min, rmssd in rmssd_series:
        if rmssd >= target_50pct:
            time_50pct = time_min * 60
            break
    
    # Find time to full recovery
    time_full = 0.0
    for time_min, rmssd in rmssd_series:
        if rmssd >= baseline_rmssd * 0.9:  # 90% of baseline
            time_full = time_min * 60
            break
    
    # Calculate recovery slope
    if len(rmssd_series) >= 2:
        times = np.array([t for t, _ in rmssd_series])
        values = np.array([v for _, v in rmssd_series])
        slope, _, _, _, _ = stats.linregress(times, values)
        recovery_slope = slope
    else:
        recovery_slope = 0.0
    
    # Determine recovery status
    if rmssd_30min >= baseline_rmssd * 0.9:
        status = RecoveryStatus.FULLY_RECOVERED
    elif rmssd_30min >= baseline_rmssd * 0.7:
        status = RecoveryStatus.MOSTLY_RECOVERED
    elif rmssd_30min >= baseline_rmssd * 0.5:
        status = RecoveryStatus.PARTIALLY_RECOVERED
    else:
        status = RecoveryStatus.NOT_RECOVERED
    
    return ParasympatheticReactivation(
        session_id="",
        time_to_hrv_onset_s=onset_time,
        time_to_50pct_recovery_s=time_50pct,
        time_to_full_recovery_s=time_full,
        rmssd_at_5min=rmssd_5min,
        rmssd_at_15min=rmssd_15min,
        rmssd_at_30min=rmssd_30min,
        recovery_slope=recovery_slope,
        recovery_status=status,
    )


# ---------------------------------------------------------------------------
# Training Load Calculation
# ---------------------------------------------------------------------------


def calculate_trimp(
    hr_data: pd.DataFrame,
    resting_hr: float,
    max_hr: float,
    sex: str = "male",
) -> float:
    """Calculate Training Impulse (TRIMP).
    
    Uses Banister's TRIMP formula with gender-specific weighting.
    
    Args:
        hr_data: DataFrame with 'timestamp' and 'heart_rate' columns.
        resting_hr: Resting heart rate.
        max_hr: Maximum heart rate.
        sex: "male" or "female" for weighting factor.
        
    Returns:
        TRIMP score.
    """
    if hr_data.empty or max_hr <= resting_hr:
        return 0.0
    
    # Calculate duration in minutes
    hr_data = hr_data.copy()
    hr_data["timestamp"] = pd.to_datetime(hr_data["timestamp"])
    duration_min = (hr_data["timestamp"].max() - hr_data["timestamp"].min()).total_seconds() / 60
    
    if duration_min <= 0:
        return 0.0
    
    # Calculate average HR reserve fraction
    avg_hr = hr_data["heart_rate"].mean()
    hr_reserve = max_hr - resting_hr
    delta_hr = (avg_hr - resting_hr) / hr_reserve if hr_reserve > 0 else 0
    delta_hr = max(0, min(1, delta_hr))  # Clamp to [0, 1]
    
    # Gender-specific weighting factor
    if sex.lower() == "female":
        y = 0.86 * np.exp(1.67 * delta_hr)
    else:
        y = 0.64 * np.exp(1.92 * delta_hr)
    
    trimp = duration_min * delta_hr * y
    
    return float(trimp)


def calculate_training_load(
    sessions: list[ExerciseSession],
    target_date: date,
) -> TrainingLoad:
    """Calculate training load metrics.
    
    Implements the Fitness-Fatigue model (Banister, 1991).
    
    Args:
        sessions: List of exercise sessions.
        target_date: Date to calculate load for.
        
    Returns:
        TrainingLoad metrics.
    """
    # Filter sessions by date
    acute_window = 7  # days
    chronic_window = 28  # days
    
    acute_start = target_date - timedelta(days=acute_window)
    chronic_start = target_date - timedelta(days=chronic_window)
    
    acute_sessions = [s for s in sessions if acute_start <= s.date <= target_date]
    chronic_sessions = [s for s in sessions if chronic_start <= s.date <= target_date]
    
    # Calculate loads
    acute_load = sum(s.trimp for s in acute_sessions)
    chronic_load = sum(s.trimp for s in chronic_sessions) / (chronic_window / acute_window) if chronic_sessions else 0
    
    # Acute:Chronic Workload Ratio
    acwr = acute_load / chronic_load if chronic_load > 0 else 1.0
    
    # Monotony (daily load variation)
    if acute_sessions:
        daily_loads = []
        for d in range(acute_window):
            day = target_date - timedelta(days=d)
            day_load = sum(s.trimp for s in acute_sessions if s.date == day)
            daily_loads.append(day_load)
        
        mean_load = np.mean(daily_loads)
        std_load = np.std(daily_loads, ddof=1) if len(daily_loads) > 1 else 1
        monotony = mean_load / std_load if std_load > 0 else 0
    else:
        monotony = 0.0
    
    # Strain
    strain = acute_load * monotony
    
    # Fitness-Fatigue model (simplified)
    # Fitness: Exponentially weighted average with 42-day time constant
    # Fatigue: Exponentially weighted average with 7-day time constant
    fitness = 0.0
    fatigue = 0.0
    
    for i, session in enumerate(sorted(chronic_sessions, key=lambda s: s.date)):
        days_ago = (target_date - session.date).days
        fitness += session.trimp * np.exp(-days_ago / 42)
        fatigue += session.trimp * np.exp(-days_ago / 7)
    
    form = fitness - fatigue
    
    # Injury risk assessment based on ACWR
    if acwr < 0.8:
        injury_risk = "low_undertraining"
    elif acwr <= 1.3:
        injury_risk = "low"
    elif acwr <= 1.5:
        injury_risk = "moderate"
    else:
        injury_risk = "high"
    
    return TrainingLoad(
        date=target_date,
        acute_load=acute_load,
        chronic_load=chronic_load,
        acwr=acwr,
        monotony=monotony,
        strain=strain,
        fitness=fitness,
        fatigue=fatigue,
        form=form,
        injury_risk=injury_risk,
    )


# ---------------------------------------------------------------------------
# Exercise HRV Comparison
# ---------------------------------------------------------------------------


def compare_exercise_hrv(
    pre_rr_data: pd.DataFrame,
    post_rr_data: pd.DataFrame,
    post_1h_rr_data: pd.DataFrame | None = None,
    post_24h_rr_data: pd.DataFrame | None = None,
) -> ExerciseHRVComparison:
    """Compare HRV before and after exercise.
    
    Args:
        pre_rr_data: RR intervals before exercise.
        post_rr_data: RR intervals immediately after exercise.
        post_1h_rr_data: RR intervals 1 hour after (optional).
        post_24h_rr_data: RR intervals 24 hours after (optional).
        
    Returns:
        ExerciseHRVComparison analysis.
    """
    def calc_rmssd(df: pd.DataFrame) -> float:
        if df.empty or "rr_ms" not in df.columns:
            return 0.0
        rr = df["rr_ms"].values
        if len(rr) < 10:
            return 0.0
        diff = np.diff(rr)
        return float(np.sqrt(np.mean(diff ** 2)))
    
    pre_rmssd = calc_rmssd(pre_rr_data)
    post_rmssd = calc_rmssd(post_rr_data)
    
    # Calculate suppression
    suppression_pct = ((pre_rmssd - post_rmssd) / pre_rmssd * 100) if pre_rmssd > 0 else 0
    
    # 1-hour recovery
    post_1h_rmssd = None
    recovery_1h = None
    if post_1h_rr_data is not None:
        post_1h_rmssd = calc_rmssd(post_1h_rr_data)
        if pre_rmssd > 0 and post_rmssd > 0:
            recovery_1h = ((post_1h_rmssd - post_rmssd) / (pre_rmssd - post_rmssd) * 100) if pre_rmssd != post_rmssd else 100
    
    # 24-hour recovery
    post_24h_rmssd = None
    recovery_24h = None
    supercompensation = False
    if post_24h_rr_data is not None:
        post_24h_rmssd = calc_rmssd(post_24h_rr_data)
        if pre_rmssd > 0 and post_rmssd > 0:
            recovery_24h = ((post_24h_rmssd - post_rmssd) / (pre_rmssd - post_rmssd) * 100) if pre_rmssd != post_rmssd else 100
            supercompensation = post_24h_rmssd > pre_rmssd * 1.05  # >5% above baseline
    
    return ExerciseHRVComparison(
        session_id="",
        pre_rmssd=pre_rmssd,
        post_rmssd_immediate=post_rmssd,
        post_rmssd_1h=post_1h_rmssd,
        post_rmssd_24h=post_24h_rmssd,
        suppression_pct=suppression_pct,
        recovery_pct_1h=recovery_1h,
        recovery_pct_24h=recovery_24h,
        supercompensation=supercompensation,
    )


# ---------------------------------------------------------------------------
# Intensity Classification
# ---------------------------------------------------------------------------


def classify_exercise_intensity(
    avg_hr: float,
    max_hr: float,
    resting_hr: float,
    age: int | None = None,
) -> ExerciseIntensity:
    """Classify exercise intensity based on heart rate.
    
    Args:
        avg_hr: Average heart rate during exercise.
        max_hr: Maximum heart rate (estimated if not provided).
        resting_hr: Resting heart rate.
        age: Age for max HR estimation (optional).
        
    Returns:
        ExerciseIntensity classification.
    """
    # Estimate max HR if needed
    if max_hr <= 0 and age:
        max_hr = 220 - age  # Simple estimation
    
    if max_hr <= resting_hr:
        return ExerciseIntensity.RECOVERY
    
    # Calculate HR reserve percentage
    hr_reserve = max_hr - resting_hr
    hr_reserve_pct = (avg_hr - resting_hr) / hr_reserve if hr_reserve > 0 else 0
    
    if hr_reserve_pct < 0.5:
        return ExerciseIntensity.RECOVERY
    elif hr_reserve_pct < 0.6:
        return ExerciseIntensity.EASY
    elif hr_reserve_pct < 0.75:
        return ExerciseIntensity.MODERATE
    elif hr_reserve_pct < 0.9:
        return ExerciseIntensity.HARD
    else:
        return ExerciseIntensity.MAXIMAL


# ---------------------------------------------------------------------------
# Overtraining Detection
# ---------------------------------------------------------------------------


def detect_overtraining_risk(
    recent_sessions: list[ExerciseSession],
    hrv_records: list[Any],  # DailyHRVRecord from longterm_trending
    rhr_records: list[tuple[date, float]],
) -> dict[str, Any]:
    """Detect overtraining risk based on multiple markers.
    
    Args:
        recent_sessions: Recent exercise sessions (last 14 days).
        hrv_records: Recent HRV records.
        rhr_records: Recent resting HR records (date, HR).
        
    Returns:
        Dictionary with overtraining risk assessment.
    """
    risk_factors: list[str] = []
    risk_score = 0
    
    # Check training load
    if len(recent_sessions) >= 7:
        total_trimp = sum(s.trimp for s in recent_sessions)
        avg_trimp = total_trimp / len(recent_sessions)
        
        # High monotony
        daily_loads = {}
        for s in recent_sessions:
            if s.date not in daily_loads:
                daily_loads[s.date] = 0
            daily_loads[s.date] += s.trimp
        
        if daily_loads:
            values = list(daily_loads.values())
            monotony = np.mean(values) / np.std(values) if np.std(values) > 0 else 0
            
            if monotony > 2.0:
                risk_factors.append("High training monotony")
                risk_score += 2
    
    # Check HRV trend
    if len(hrv_records) >= 7:
        recent_hrv = sorted(hrv_records, key=lambda r: r.date)[-7:]
        hrv_values = [r.ln_rmssd for r in recent_hrv]
        
        # Check for declining trend
        slope, _, _, p_value, _ = stats.linregress(range(len(hrv_values)), hrv_values)
        
        if slope < 0 and p_value < 0.1:
            risk_factors.append("Declining HRV trend")
            risk_score += 2
        
        # Check for increased variability
        cv = np.std(hrv_values) / np.mean(hrv_values) * 100 if np.mean(hrv_values) > 0 else 0
        if cv > 10:
            risk_factors.append("High HRV variability")
            risk_score += 1
    
    # Check resting HR trend
    if len(rhr_records) >= 7:
        recent_rhr = sorted(rhr_records, key=lambda r: r[0])[-7:]
        rhr_values = [r[1] for r in recent_rhr]
        
        # Check for increasing trend
        slope, _, _, p_value, _ = stats.linregress(range(len(rhr_values)), rhr_values)
        
        if slope > 0.5 and p_value < 0.1:  # >0.5 bpm/day increase
            risk_factors.append("Increasing resting HR")
            risk_score += 2
    
    # Determine overall risk level
    if risk_score >= 5:
        risk_level = "high"
        recommendation = "Consider significant reduction in training load. Prioritize recovery."
    elif risk_score >= 3:
        risk_level = "moderate"
        recommendation = "Monitor closely. Consider reducing intensity or volume."
    elif risk_score >= 1:
        risk_level = "low"
        recommendation = "Continue training with attention to recovery."
    else:
        risk_level = "minimal"
        recommendation = "Training load appears sustainable."
    
    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


def generate_exercise_report(
    session: ExerciseSession,
    hrr: HeartRateRecovery | None = None,
    reactivation: ParasympatheticReactivation | None = None,
    hrv_comparison: ExerciseHRVComparison | None = None,
) -> dict[str, Any]:
    """Generate comprehensive exercise analysis report.
    
    Args:
        session: Exercise session data.
        hrr: Heart rate recovery analysis (optional).
        reactivation: Parasympathetic reactivation analysis (optional).
        hrv_comparison: HRV comparison analysis (optional).
        
    Returns:
        Dictionary with complete exercise report.
    """
    report: dict[str, Any] = {
        "session": {
            "date": session.date.isoformat(),
            "duration_minutes": session.duration_minutes,
            "exercise_type": session.exercise_type,
            "intensity": session.intensity.value,
            "max_hr": session.max_hr,
            "avg_hr": session.avg_hr,
            "trimp": session.trimp,
        }
    }
    
    if hrr:
        report["heart_rate_recovery"] = {
            "peak_hr": hrr.peak_hr,
            "hrr_30s": hrr.hrr_30s,
            "hrr_60s": hrr.hrr_60s,
            "hrr_120s": hrr.hrr_120s,
            "time_constant_s": hrr.time_constant_s,
            "quality": hrr.recovery_quality,
            "percentile": hrr.percentile,
        }
    
    if reactivation:
        report["parasympathetic_reactivation"] = {
            "time_to_onset_s": reactivation.time_to_hrv_onset_s,
            "time_to_50pct_s": reactivation.time_to_50pct_recovery_s,
            "time_to_full_s": reactivation.time_to_full_recovery_s,
            "rmssd_5min": reactivation.rmssd_at_5min,
            "rmssd_30min": reactivation.rmssd_at_30min,
            "status": reactivation.recovery_status.value,
        }
    
    if hrv_comparison:
        report["hrv_comparison"] = {
            "pre_rmssd": hrv_comparison.pre_rmssd,
            "post_rmssd": hrv_comparison.post_rmssd_immediate,
            "suppression_pct": hrv_comparison.suppression_pct,
            "recovery_24h_pct": hrv_comparison.recovery_pct_24h,
            "supercompensation": hrv_comparison.supercompensation,
        }
    
    return report

