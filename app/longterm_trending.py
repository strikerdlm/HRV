"""Long-Term HRV Trending Analysis Module.

This module provides tools for tracking HRV changes over extended periods
(weeks to months), establishing personalized baselines, detecting trends,
and analyzing seasonal/circadian patterns.

Author: Dr. Diego Malpica, MD
        Aerospace Medicine Specialist
        National University of Colombia

References:
    - Plews, D. J., et al. (2013). Training adaptation and heart rate variability
      in elite endurance athletes. Journal of Strength and Conditioning Research.
    - Buchheit, M. (2014). Monitoring training status with HR measures: do all
      roads lead to Rome? Frontiers in Physiology, 5, 73.
    - Flatt, A. A., & Esco, M. R. (2016). Evaluating individual training adaptation
      with smartphone-derived heart rate variability in a collegiate female
      soccer team. Journal of Strength and Conditioning Research.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta, timezone
from enum import Enum
from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray
import pandas as pd
from scipy import stats
from scipy.signal import detrend

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Baseline calculation parameters
DEFAULT_BASELINE_DAYS: Final[int] = 7  # Rolling baseline window
MIN_BASELINE_DAYS: Final[int] = 3  # Minimum days for baseline
MAX_BASELINE_DAYS: Final[int] = 30  # Maximum baseline window

# Trend detection parameters
MIN_DAYS_FOR_TREND: Final[int] = 7  # Minimum days to detect trend
TREND_SIGNIFICANCE_ALPHA: Final[float] = 0.05  # p-value threshold

# Coefficient of variation thresholds
CV_LOW_THRESHOLD: Final[float] = 3.0  # <3% CV indicates stable baseline
CV_HIGH_THRESHOLD: Final[float] = 10.0  # >10% CV indicates high variability

# Z-score thresholds for anomaly detection
ZSCORE_WARNING: Final[float] = 1.5
ZSCORE_ALERT: Final[float] = 2.0
ZSCORE_CRITICAL: Final[float] = 2.5


class TrendDirection(Enum):
    """Direction of HRV trend."""
    
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    UNKNOWN = "unknown"


class AdaptationStatus(Enum):
    """Training adaptation status based on HRV patterns."""
    
    POSITIVE_ADAPTATION = "positive_adaptation"  # Improving HRV
    FUNCTIONAL_OVERREACHING = "functional_overreaching"  # Temporary decline
    NON_FUNCTIONAL_OVERREACHING = "non_functional_overreaching"  # Prolonged decline
    STABLE = "stable"  # No significant change
    DETRAINING = "detraining"  # Loss of fitness
    UNKNOWN = "unknown"


class ReadinessLevel(Enum):
    """Daily readiness level."""
    
    OPTIMAL = "optimal"  # HRV above baseline
    NORMAL = "normal"  # HRV within normal range
    COMPROMISED = "compromised"  # HRV below baseline
    CRITICAL = "critical"  # HRV significantly below baseline


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class DailyHRVRecord:
    """Single day HRV measurement.
    
    Attributes:
        date: Measurement date.
        rmssd_ms: RMSSD value in milliseconds.
        sdnn_ms: SDNN value in milliseconds (optional).
        mean_hr_bpm: Mean heart rate in BPM.
        ln_rmssd: Natural log of RMSSD.
        hrv_score: Computed HRV score (0-100).
        measurement_time: Time of measurement.
        measurement_duration_s: Duration in seconds.
        context: Measurement context (morning, evening, etc.).
        notes: User notes.
        confidence: Data quality confidence (0-1).
    """
    
    date: date
    rmssd_ms: float
    sdnn_ms: float | None = None
    mean_hr_bpm: float | None = None
    ln_rmssd: float = field(init=False)
    hrv_score: float = field(init=False)
    measurement_time: datetime | None = None
    measurement_duration_s: float | None = None
    context: str = "morning"
    notes: str = ""
    confidence: float = 1.0
    
    def __post_init__(self) -> None:
        """Compute derived values."""
        self.ln_rmssd = np.log(self.rmssd_ms) if self.rmssd_ms > 0 else 0.0
        # Simple HRV score: normalized lnRMSSD (typical range 2.5-4.5 -> 0-100)
        self.hrv_score = max(0, min(100, (self.ln_rmssd - 2.5) / 2.0 * 100))


@dataclass(slots=True)
class BaselineStats:
    """Baseline statistics for HRV metrics.
    
    Attributes:
        period_start: Start date of baseline period.
        period_end: End date of baseline period.
        n_days: Number of days in baseline.
        mean_rmssd: Mean RMSSD.
        std_rmssd: Standard deviation of RMSSD.
        cv_rmssd: Coefficient of variation (%).
        mean_ln_rmssd: Mean lnRMSSD.
        std_ln_rmssd: Standard deviation of lnRMSSD.
        cv_ln_rmssd: Coefficient of variation of lnRMSSD (%).
        mean_hr: Mean heart rate.
        std_hr: Standard deviation of heart rate.
        percentile_25: 25th percentile RMSSD.
        percentile_75: 75th percentile RMSSD.
        smallest_worthwhile_change: SWC for meaningful change detection.
        is_stable: Whether baseline is stable (CV < threshold).
    """
    
    period_start: date
    period_end: date
    n_days: int
    mean_rmssd: float
    std_rmssd: float
    cv_rmssd: float
    mean_ln_rmssd: float
    std_ln_rmssd: float
    cv_ln_rmssd: float
    mean_hr: float = 0.0
    std_hr: float = 0.0
    percentile_25: float = 0.0
    percentile_75: float = 0.0
    smallest_worthwhile_change: float = field(init=False)
    is_stable: bool = field(init=False)
    
    def __post_init__(self) -> None:
        """Compute derived values."""
        # SWC = 0.5 * CV (Buchheit, 2014)
        self.smallest_worthwhile_change = 0.5 * self.cv_ln_rmssd
        self.is_stable = self.cv_ln_rmssd < CV_LOW_THRESHOLD


@dataclass(slots=True)
class TrendAnalysis:
    """Results of trend analysis.
    
    Attributes:
        period_start: Start date of analysis period.
        period_end: End date of analysis period.
        n_days: Number of days analyzed.
        direction: Trend direction.
        slope: Slope of linear regression (units per day).
        slope_pct_per_week: Slope as percentage change per week.
        r_squared: R² of linear fit.
        p_value: Statistical significance of trend.
        is_significant: Whether trend is statistically significant.
        confidence_interval: 95% CI for slope.
        interpretation: Human-readable interpretation.
    """
    
    period_start: date
    period_end: date
    n_days: int
    direction: TrendDirection
    slope: float
    slope_pct_per_week: float
    r_squared: float
    p_value: float
    is_significant: bool
    confidence_interval: tuple[float, float]
    interpretation: str = ""


@dataclass(slots=True)
class DailyReadiness:
    """Daily readiness assessment.
    
    Attributes:
        date: Assessment date.
        rmssd_ms: Today's RMSSD.
        baseline_mean: Baseline mean RMSSD.
        baseline_std: Baseline standard deviation.
        z_score: Z-score relative to baseline.
        percentile: Percentile relative to baseline.
        level: Readiness level classification.
        hrv_trend_7d: 7-day HRV trend.
        hrv_trend_30d: 30-day HRV trend.
        recommendations: List of recommendations.
        confidence: Assessment confidence (0-1).
    """
    
    date: date
    rmssd_ms: float
    baseline_mean: float
    baseline_std: float
    z_score: float
    percentile: float
    level: ReadinessLevel
    hrv_trend_7d: TrendDirection = TrendDirection.UNKNOWN
    hrv_trend_30d: TrendDirection = TrendDirection.UNKNOWN
    recommendations: list[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass(slots=True)
class AdaptationAnalysis:
    """Training adaptation analysis.
    
    Attributes:
        period_start: Start date of analysis.
        period_end: End date of analysis.
        status: Current adaptation status.
        hrv_change_pct: Percentage change in HRV.
        cv_change: Change in coefficient of variation.
        rhr_change_bpm: Change in resting heart rate.
        days_below_baseline: Days with HRV below baseline.
        consecutive_low_days: Consecutive days below baseline.
        recovery_trajectory: Estimated recovery trajectory.
        recommendations: List of recommendations.
    """
    
    period_start: date
    period_end: date
    status: AdaptationStatus
    hrv_change_pct: float
    cv_change: float
    rhr_change_bpm: float
    days_below_baseline: int
    consecutive_low_days: int
    recovery_trajectory: str = ""
    recommendations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SeasonalPattern:
    """Seasonal/circadian pattern analysis.
    
    Attributes:
        period_type: Type of pattern (daily, weekly, monthly, yearly).
        amplitude: Pattern amplitude.
        phase: Phase of pattern (peak timing).
        significance: Statistical significance.
        pattern_data: Pattern values by period.
    """
    
    period_type: str
    amplitude: float
    phase: float
    significance: float
    pattern_data: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Baseline Calculation
# ---------------------------------------------------------------------------


def calculate_baseline(
    records: list[DailyHRVRecord],
    window_days: int = DEFAULT_BASELINE_DAYS,
    end_date: date | None = None,
) -> BaselineStats | None:
    """Calculate baseline statistics from HRV records.
    
    Args:
        records: List of daily HRV records.
        window_days: Number of days for baseline window.
        end_date: End date for baseline (defaults to most recent).
        
    Returns:
        BaselineStats or None if insufficient data.
    """
    if len(records) < MIN_BASELINE_DAYS:
        _LOGGER.warning("Insufficient records for baseline: %d < %d", len(records), MIN_BASELINE_DAYS)
        return None
    
    # Sort by date
    sorted_records = sorted(records, key=lambda r: r.date)
    
    # Filter by date range
    if end_date is None:
        end_date = sorted_records[-1].date
    
    start_date = end_date - timedelta(days=window_days - 1)
    
    filtered = [r for r in sorted_records if start_date <= r.date <= end_date]
    
    if len(filtered) < MIN_BASELINE_DAYS:
        _LOGGER.warning("Insufficient records in window: %d < %d", len(filtered), MIN_BASELINE_DAYS)
        return None
    
    # Extract values
    rmssd_values = np.array([r.rmssd_ms for r in filtered])
    ln_rmssd_values = np.array([r.ln_rmssd for r in filtered])
    hr_values = np.array([r.mean_hr_bpm for r in filtered if r.mean_hr_bpm is not None])
    
    # Calculate statistics
    mean_rmssd = float(np.mean(rmssd_values))
    std_rmssd = float(np.std(rmssd_values, ddof=1))
    cv_rmssd = (std_rmssd / mean_rmssd * 100) if mean_rmssd > 0 else 0.0
    
    mean_ln_rmssd = float(np.mean(ln_rmssd_values))
    std_ln_rmssd = float(np.std(ln_rmssd_values, ddof=1))
    cv_ln_rmssd = (std_ln_rmssd / mean_ln_rmssd * 100) if mean_ln_rmssd > 0 else 0.0
    
    mean_hr = float(np.mean(hr_values)) if len(hr_values) > 0 else 0.0
    std_hr = float(np.std(hr_values, ddof=1)) if len(hr_values) > 1 else 0.0
    
    return BaselineStats(
        period_start=filtered[0].date,
        period_end=filtered[-1].date,
        n_days=len(filtered),
        mean_rmssd=mean_rmssd,
        std_rmssd=std_rmssd,
        cv_rmssd=cv_rmssd,
        mean_ln_rmssd=mean_ln_rmssd,
        std_ln_rmssd=std_ln_rmssd,
        cv_ln_rmssd=cv_ln_rmssd,
        mean_hr=mean_hr,
        std_hr=std_hr,
        percentile_25=float(np.percentile(rmssd_values, 25)),
        percentile_75=float(np.percentile(rmssd_values, 75)),
    )


def calculate_rolling_baseline(
    records: list[DailyHRVRecord],
    window_days: int = DEFAULT_BASELINE_DAYS,
) -> dict[date, BaselineStats]:
    """Calculate rolling baseline for each day.
    
    Args:
        records: List of daily HRV records.
        window_days: Rolling window size in days.
        
    Returns:
        Dictionary mapping dates to their baseline statistics.
    """
    sorted_records = sorted(records, key=lambda r: r.date)
    baselines: dict[date, BaselineStats] = {}
    
    for i, record in enumerate(sorted_records):
        if i < MIN_BASELINE_DAYS - 1:
            continue
        
        # Get records for baseline window
        window_start = max(0, i - window_days + 1)
        window_records = sorted_records[window_start:i + 1]
        
        baseline = calculate_baseline(window_records, window_days=len(window_records))
        if baseline:
            baselines[record.date] = baseline
    
    return baselines


# ---------------------------------------------------------------------------
# Trend Analysis
# ---------------------------------------------------------------------------


def analyze_trend(
    records: list[DailyHRVRecord],
    start_date: date | None = None,
    end_date: date | None = None,
    metric: str = "ln_rmssd",
) -> TrendAnalysis | None:
    """Analyze trend in HRV data.
    
    Uses linear regression to detect trends and assess significance.
    
    Args:
        records: List of daily HRV records.
        start_date: Start date for analysis (optional).
        end_date: End date for analysis (optional).
        metric: Metric to analyze ("rmssd", "ln_rmssd", "hrv_score").
        
    Returns:
        TrendAnalysis or None if insufficient data.
    """
    # Sort and filter records
    sorted_records = sorted(records, key=lambda r: r.date)
    
    if start_date:
        sorted_records = [r for r in sorted_records if r.date >= start_date]
    if end_date:
        sorted_records = [r for r in sorted_records if r.date <= end_date]
    
    if len(sorted_records) < MIN_DAYS_FOR_TREND:
        return None
    
    # Extract values
    dates = np.array([(r.date - sorted_records[0].date).days for r in sorted_records])
    
    if metric == "rmssd":
        values = np.array([r.rmssd_ms for r in sorted_records])
    elif metric == "ln_rmssd":
        values = np.array([r.ln_rmssd for r in sorted_records])
    elif metric == "hrv_score":
        values = np.array([r.hrv_score for r in sorted_records])
    else:
        values = np.array([r.ln_rmssd for r in sorted_records])
    
    # Linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(dates, values)
    
    # Calculate confidence interval for slope
    n = len(dates)
    t_value = stats.t.ppf(0.975, n - 2)
    ci_lower = slope - t_value * std_err
    ci_upper = slope + t_value * std_err
    
    # Determine direction
    if p_value < TREND_SIGNIFICANCE_ALPHA:
        if slope > 0:
            direction = TrendDirection.INCREASING
        else:
            direction = TrendDirection.DECREASING
    else:
        direction = TrendDirection.STABLE
    
    # Calculate percentage change per week
    mean_value = np.mean(values)
    slope_pct_per_week = (slope * 7 / mean_value * 100) if mean_value > 0 else 0.0
    
    # Generate interpretation
    interpretation = _generate_trend_interpretation(
        direction, slope_pct_per_week, p_value, metric
    )
    
    return TrendAnalysis(
        period_start=sorted_records[0].date,
        period_end=sorted_records[-1].date,
        n_days=len(sorted_records),
        direction=direction,
        slope=slope,
        slope_pct_per_week=slope_pct_per_week,
        r_squared=r_value ** 2,
        p_value=p_value,
        is_significant=p_value < TREND_SIGNIFICANCE_ALPHA,
        confidence_interval=(ci_lower, ci_upper),
        interpretation=interpretation,
    )


def _generate_trend_interpretation(
    direction: TrendDirection,
    slope_pct: float,
    p_value: float,
    metric: str,
) -> str:
    """Generate human-readable trend interpretation."""
    
    metric_name = {
        "rmssd": "RMSSD",
        "ln_rmssd": "lnRMSSD",
        "hrv_score": "HRV Score",
    }.get(metric, metric)
    
    if direction == TrendDirection.STABLE:
        return f"{metric_name} is stable with no significant trend (p={p_value:.3f})."
    
    direction_word = "increasing" if direction == TrendDirection.INCREASING else "decreasing"
    magnitude = abs(slope_pct)
    
    if magnitude < 1:
        magnitude_word = "slightly"
    elif magnitude < 3:
        magnitude_word = "moderately"
    else:
        magnitude_word = "significantly"
    
    interpretation = (
        f"{metric_name} is {magnitude_word} {direction_word} at "
        f"{abs(slope_pct):.1f}% per week (p={p_value:.3f})."
    )
    
    # Add clinical context
    if direction == TrendDirection.INCREASING:
        interpretation += " This may indicate improving autonomic function or recovery."
    else:
        interpretation += " This may indicate accumulated fatigue or stress."
    
    return interpretation


# ---------------------------------------------------------------------------
# Readiness Assessment
# ---------------------------------------------------------------------------


def assess_daily_readiness(
    today_record: DailyHRVRecord,
    baseline: BaselineStats,
    recent_records: list[DailyHRVRecord] | None = None,
) -> DailyReadiness:
    """Assess daily readiness based on HRV.
    
    Args:
        today_record: Today's HRV measurement.
        baseline: Baseline statistics.
        recent_records: Recent records for trend analysis (optional).
        
    Returns:
        DailyReadiness assessment.
    """
    # Calculate z-score
    if baseline.std_ln_rmssd > 0:
        z_score = (today_record.ln_rmssd - baseline.mean_ln_rmssd) / baseline.std_ln_rmssd
    else:
        z_score = 0.0
    
    # Calculate percentile (approximate from z-score)
    percentile = stats.norm.cdf(z_score) * 100
    
    # Determine readiness level
    if z_score >= 0.5:
        level = ReadinessLevel.OPTIMAL
    elif z_score >= -0.5:
        level = ReadinessLevel.NORMAL
    elif z_score >= -ZSCORE_ALERT:
        level = ReadinessLevel.COMPROMISED
    else:
        level = ReadinessLevel.CRITICAL
    
    # Analyze recent trends if data available
    hrv_trend_7d = TrendDirection.UNKNOWN
    hrv_trend_30d = TrendDirection.UNKNOWN
    
    if recent_records:
        # 7-day trend
        recent_7d = [r for r in recent_records if (today_record.date - r.date).days <= 7]
        if len(recent_7d) >= 3:
            trend_7d = analyze_trend(recent_7d)
            if trend_7d:
                hrv_trend_7d = trend_7d.direction
        
        # 30-day trend
        recent_30d = [r for r in recent_records if (today_record.date - r.date).days <= 30]
        if len(recent_30d) >= 7:
            trend_30d = analyze_trend(recent_30d)
            if trend_30d:
                hrv_trend_30d = trend_30d.direction
    
    # Generate recommendations
    recommendations = _generate_readiness_recommendations(
        level, z_score, hrv_trend_7d, hrv_trend_30d
    )
    
    return DailyReadiness(
        date=today_record.date,
        rmssd_ms=today_record.rmssd_ms,
        baseline_mean=baseline.mean_rmssd,
        baseline_std=baseline.std_rmssd,
        z_score=z_score,
        percentile=percentile,
        level=level,
        hrv_trend_7d=hrv_trend_7d,
        hrv_trend_30d=hrv_trend_30d,
        recommendations=recommendations,
        confidence=min(today_record.confidence, 1.0 if baseline.is_stable else 0.7),
    )


def _generate_readiness_recommendations(
    level: ReadinessLevel,
    z_score: float,
    trend_7d: TrendDirection,
    trend_30d: TrendDirection,
) -> list[str]:
    """Generate readiness recommendations."""
    
    recommendations: list[str] = []
    
    if level == ReadinessLevel.OPTIMAL:
        recommendations.append("HRV is above baseline - good recovery status.")
        recommendations.append("Consider high-intensity training or demanding activities.")
    
    elif level == ReadinessLevel.NORMAL:
        recommendations.append("HRV is within normal range.")
        recommendations.append("Proceed with planned activities as scheduled.")
    
    elif level == ReadinessLevel.COMPROMISED:
        recommendations.append("HRV is below baseline - consider reducing intensity.")
        recommendations.append("Focus on recovery: sleep, nutrition, stress management.")
        
        if trend_7d == TrendDirection.DECREASING:
            recommendations.append("Declining trend over past week - prioritize rest.")
    
    else:  # CRITICAL
        recommendations.append("HRV is significantly below baseline - rest day recommended.")
        recommendations.append("Avoid high-intensity activities.")
        recommendations.append("Monitor for signs of illness or overtraining.")
        
        if trend_30d == TrendDirection.DECREASING:
            recommendations.append("Consider consulting a healthcare provider if pattern persists.")
    
    return recommendations


# ---------------------------------------------------------------------------
# Adaptation Analysis
# ---------------------------------------------------------------------------


def analyze_adaptation(
    records: list[DailyHRVRecord],
    baseline_period_days: int = 14,
    analysis_period_days: int = 14,
) -> AdaptationAnalysis | None:
    """Analyze training adaptation status.
    
    Based on Plews et al. (2013) and Buchheit (2014) frameworks.
    
    Args:
        records: List of daily HRV records.
        baseline_period_days: Days for initial baseline.
        analysis_period_days: Days for recent analysis.
        
    Returns:
        AdaptationAnalysis or None if insufficient data.
    """
    if len(records) < baseline_period_days + analysis_period_days:
        return None
    
    sorted_records = sorted(records, key=lambda r: r.date)
    
    # Split into baseline and analysis periods
    baseline_records = sorted_records[:baseline_period_days]
    analysis_records = sorted_records[-analysis_period_days:]
    
    # Calculate baselines
    baseline = calculate_baseline(baseline_records, window_days=baseline_period_days)
    current = calculate_baseline(analysis_records, window_days=analysis_period_days)
    
    if not baseline or not current:
        return None
    
    # Calculate changes
    hrv_change_pct = (current.mean_ln_rmssd - baseline.mean_ln_rmssd) / baseline.mean_ln_rmssd * 100
    cv_change = current.cv_ln_rmssd - baseline.cv_ln_rmssd
    rhr_change = current.mean_hr - baseline.mean_hr if baseline.mean_hr > 0 else 0.0
    
    # Count days below baseline
    days_below = sum(1 for r in analysis_records if r.ln_rmssd < baseline.mean_ln_rmssd - baseline.std_ln_rmssd)
    
    # Count consecutive low days
    consecutive_low = 0
    max_consecutive = 0
    for r in analysis_records:
        if r.ln_rmssd < baseline.mean_ln_rmssd - baseline.std_ln_rmssd:
            consecutive_low += 1
            max_consecutive = max(max_consecutive, consecutive_low)
        else:
            consecutive_low = 0
    
    # Determine adaptation status
    status = _classify_adaptation_status(
        hrv_change_pct, cv_change, rhr_change, days_below, max_consecutive, analysis_period_days
    )
    
    # Generate recommendations
    recommendations = _generate_adaptation_recommendations(status, hrv_change_pct, cv_change)
    
    return AdaptationAnalysis(
        period_start=analysis_records[0].date,
        period_end=analysis_records[-1].date,
        status=status,
        hrv_change_pct=hrv_change_pct,
        cv_change=cv_change,
        rhr_change_bpm=rhr_change,
        days_below_baseline=days_below,
        consecutive_low_days=max_consecutive,
        recommendations=recommendations,
    )


def _classify_adaptation_status(
    hrv_change_pct: float,
    cv_change: float,
    rhr_change: float,
    days_below: int,
    consecutive_low: int,
    period_days: int,
) -> AdaptationStatus:
    """Classify adaptation status based on HRV patterns."""
    
    # Positive adaptation: HRV increasing, CV stable or decreasing
    if hrv_change_pct > 3 and cv_change < 2:
        return AdaptationStatus.POSITIVE_ADAPTATION
    
    # Functional overreaching: Temporary decline with increased CV
    if -10 < hrv_change_pct < 0 and cv_change > 2 and consecutive_low < 5:
        return AdaptationStatus.FUNCTIONAL_OVERREACHING
    
    # Non-functional overreaching: Prolonged decline
    if hrv_change_pct < -10 or consecutive_low >= 5 or days_below > period_days * 0.7:
        return AdaptationStatus.NON_FUNCTIONAL_OVERREACHING
    
    # Detraining: Declining HRV with decreasing CV (loss of fitness)
    if hrv_change_pct < -5 and cv_change < -2 and rhr_change > 3:
        return AdaptationStatus.DETRAINING
    
    # Stable
    if abs(hrv_change_pct) < 3 and abs(cv_change) < 2:
        return AdaptationStatus.STABLE
    
    return AdaptationStatus.UNKNOWN


def _generate_adaptation_recommendations(
    status: AdaptationStatus,
    hrv_change_pct: float,
    cv_change: float,
) -> list[str]:
    """Generate adaptation recommendations."""
    
    recommendations: list[str] = []
    
    if status == AdaptationStatus.POSITIVE_ADAPTATION:
        recommendations.append("Positive adaptation detected - training is effective.")
        recommendations.append("Consider progressive overload to continue improvements.")
    
    elif status == AdaptationStatus.FUNCTIONAL_OVERREACHING:
        recommendations.append("Functional overreaching detected - temporary fatigue.")
        recommendations.append("Reduce training load for 3-5 days to allow supercompensation.")
        recommendations.append("Ensure adequate sleep and nutrition.")
    
    elif status == AdaptationStatus.NON_FUNCTIONAL_OVERREACHING:
        recommendations.append("Warning: Non-functional overreaching detected.")
        recommendations.append("Significantly reduce training for 1-2 weeks.")
        recommendations.append("Consider medical evaluation if symptoms persist.")
        recommendations.append("Focus on sleep quality and stress reduction.")
    
    elif status == AdaptationStatus.DETRAINING:
        recommendations.append("Detraining pattern detected - fitness may be declining.")
        recommendations.append("Gradually increase training stimulus.")
        recommendations.append("Review training program structure.")
    
    else:
        recommendations.append("Training status is stable.")
        recommendations.append("Continue current program or consider progression.")
    
    return recommendations


# ---------------------------------------------------------------------------
# Seasonal/Circadian Analysis
# ---------------------------------------------------------------------------


def analyze_weekly_pattern(
    records: list[DailyHRVRecord],
) -> SeasonalPattern | None:
    """Analyze weekly patterns in HRV.
    
    Args:
        records: List of daily HRV records (minimum 4 weeks recommended).
        
    Returns:
        SeasonalPattern or None if insufficient data.
    """
    if len(records) < 14:
        return None
    
    # Group by day of week
    day_values: dict[int, list[float]] = {i: [] for i in range(7)}
    
    for record in records:
        day_of_week = record.date.weekday()
        day_values[day_of_week].append(record.ln_rmssd)
    
    # Calculate means for each day
    day_means: dict[str, float] = {}
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    all_values: list[float] = []
    for day, values in day_values.items():
        if values:
            day_means[day_names[day]] = float(np.mean(values))
            all_values.extend(values)
    
    if not day_means:
        return None
    
    # Calculate amplitude (range of daily means)
    mean_values = list(day_means.values())
    amplitude = max(mean_values) - min(mean_values)
    
    # Find peak day
    peak_day = max(day_means, key=day_means.get)
    peak_index = day_names.index(peak_day)
    
    # Test significance with ANOVA
    groups = [v for v in day_values.values() if len(v) > 0]
    if len(groups) >= 2 and all(len(g) >= 2 for g in groups):
        _, p_value = stats.f_oneway(*groups)
    else:
        p_value = 1.0
    
    return SeasonalPattern(
        period_type="weekly",
        amplitude=amplitude,
        phase=float(peak_index),
        significance=p_value,
        pattern_data=day_means,
    )


def analyze_monthly_pattern(
    records: list[DailyHRVRecord],
) -> SeasonalPattern | None:
    """Analyze monthly patterns in HRV.
    
    Args:
        records: List of daily HRV records (minimum 3 months recommended).
        
    Returns:
        SeasonalPattern or None if insufficient data.
    """
    if len(records) < 60:
        return None
    
    # Group by month
    month_values: dict[int, list[float]] = {i: [] for i in range(1, 13)}
    
    for record in records:
        month = record.date.month
        month_values[month].append(record.ln_rmssd)
    
    # Calculate means for each month
    month_means: dict[str, float] = {}
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    
    for month, values in month_values.items():
        if values:
            month_means[month_names[month - 1]] = float(np.mean(values))
    
    if len(month_means) < 3:
        return None
    
    # Calculate amplitude
    mean_values = list(month_means.values())
    amplitude = max(mean_values) - min(mean_values)
    
    # Find peak month
    peak_month = max(month_means, key=month_means.get)
    peak_index = month_names.index(peak_month)
    
    # Test significance
    groups = [v for v in month_values.values() if len(v) >= 2]
    if len(groups) >= 2:
        _, p_value = stats.f_oneway(*groups)
    else:
        p_value = 1.0
    
    return SeasonalPattern(
        period_type="monthly",
        amplitude=amplitude,
        phase=float(peak_index),
        significance=p_value,
        pattern_data=month_means,
    )


# ---------------------------------------------------------------------------
# Data Export
# ---------------------------------------------------------------------------


def records_to_dataframe(records: list[DailyHRVRecord]) -> pd.DataFrame:
    """Convert HRV records to pandas DataFrame.
    
    Args:
        records: List of daily HRV records.
        
    Returns:
        DataFrame with all record data.
    """
    data = []
    for r in records:
        data.append({
            "date": r.date,
            "rmssd_ms": r.rmssd_ms,
            "sdnn_ms": r.sdnn_ms,
            "mean_hr_bpm": r.mean_hr_bpm,
            "ln_rmssd": r.ln_rmssd,
            "hrv_score": r.hrv_score,
            "measurement_time": r.measurement_time,
            "context": r.context,
            "confidence": r.confidence,
        })
    
    return pd.DataFrame(data)


def create_trend_report(
    records: list[DailyHRVRecord],
    baseline_days: int = 7,
) -> dict[str, Any]:
    """Create comprehensive trend report.
    
    Args:
        records: List of daily HRV records.
        baseline_days: Days for baseline calculation.
        
    Returns:
        Dictionary with all trend analysis results.
    """
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_records": len(records),
    }
    
    if len(records) < MIN_BASELINE_DAYS:
        report["error"] = "Insufficient data for analysis"
        return report
    
    sorted_records = sorted(records, key=lambda r: r.date)
    
    # Date range
    report["date_range"] = {
        "start": sorted_records[0].date.isoformat(),
        "end": sorted_records[-1].date.isoformat(),
        "days": (sorted_records[-1].date - sorted_records[0].date).days + 1,
    }
    
    # Current baseline
    baseline = calculate_baseline(records, window_days=baseline_days)
    if baseline:
        report["baseline"] = {
            "mean_rmssd": baseline.mean_rmssd,
            "std_rmssd": baseline.std_rmssd,
            "cv_rmssd": baseline.cv_rmssd,
            "mean_ln_rmssd": baseline.mean_ln_rmssd,
            "cv_ln_rmssd": baseline.cv_ln_rmssd,
            "is_stable": baseline.is_stable,
            "swc": baseline.smallest_worthwhile_change,
        }
    
    # Trends
    for period_name, days in [("7_day", 7), ("14_day", 14), ("30_day", 30)]:
        recent = [r for r in sorted_records if (sorted_records[-1].date - r.date).days < days]
        trend = analyze_trend(recent)
        if trend:
            report[f"trend_{period_name}"] = {
                "direction": trend.direction.value,
                "slope_pct_per_week": trend.slope_pct_per_week,
                "p_value": trend.p_value,
                "is_significant": trend.is_significant,
                "interpretation": trend.interpretation,
            }
    
    # Today's readiness
    if baseline:
        readiness = assess_daily_readiness(sorted_records[-1], baseline, sorted_records)
        report["today_readiness"] = {
            "level": readiness.level.value,
            "z_score": readiness.z_score,
            "percentile": readiness.percentile,
            "recommendations": readiness.recommendations,
        }
    
    # Adaptation status
    adaptation = analyze_adaptation(records)
    if adaptation:
        report["adaptation"] = {
            "status": adaptation.status.value,
            "hrv_change_pct": adaptation.hrv_change_pct,
            "cv_change": adaptation.cv_change,
            "days_below_baseline": adaptation.days_below_baseline,
            "recommendations": adaptation.recommendations,
        }
    
    # Weekly pattern
    weekly = analyze_weekly_pattern(records)
    if weekly:
        report["weekly_pattern"] = {
            "amplitude": weekly.amplitude,
            "peak_day": list(weekly.pattern_data.keys())[int(weekly.phase)] if weekly.pattern_data else None,
            "significance": weekly.significance,
            "pattern": weekly.pattern_data,
        }
    
    return report

