"""Multi-day longitudinal tracking module for HRV analysis.

This module provides functionality for:
- Tracking HRV metrics across multiple days
- Computing rolling statistics and trends
- Detecting significant changes over time
- Generating longitudinal reports
- Supporting intervention studies (pre/post analysis)

Design principles:
- All data is timestamped and indexed by date
- Rolling windows are configurable
- Trend detection uses robust statistical methods
- Results include confidence intervals

References:
- Plews, D. J., et al. (2013). Training adaptation and HRV.
- Buchheit, M. (2014). Monitoring training status with HR measures.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Final

import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
_MIN_DAYS_TREND: Final[int] = 7
_ROLLING_WINDOW_DEFAULT: Final[int] = 7


class TrendStatus(str, Enum):
    """Trend status for a metric."""

    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    VARIABLE = "variable"
    INSUFFICIENT_DATA = "insufficient_data"


class AlertLevel(str, Enum):
    """Alert level for significant changes."""

    NORMAL = "normal"
    ATTENTION = "attention"
    WARNING = "warning"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DailyHRVRecord:
    """Single day HRV record.

    Attributes:
        date: Recording date.
        rmssd: Root mean square of successive differences (ms).
        sdnn: Standard deviation of NN intervals (ms).
        mean_hr: Mean heart rate (bpm).
        lf_power: Low frequency power (ms²).
        hf_power: High frequency power (ms²).
        lf_hf_ratio: LF/HF ratio.
        pnn50: Percentage of successive RR intervals > 50ms.
        total_power: Total spectral power (ms²).
        sample_entropy: Sample entropy.
        hrv_score: Composite HRV score (0-100).
        recovery_status: Recovery status string.
        quality_ok: Whether data quality was sufficient.
        notes: Optional notes for the day.
    """

    date: date
    rmssd: float = 0.0
    sdnn: float = 0.0
    mean_hr: float = 0.0
    lf_power: float = 0.0
    hf_power: float = 0.0
    lf_hf_ratio: float = 0.0
    pnn50: float = 0.0
    total_power: float = 0.0
    sample_entropy: float = 0.0
    hrv_score: float = 0.0
    recovery_status: str = "unknown"
    quality_ok: bool = True
    notes: str = ""


@dataclass(frozen=True, slots=True)
class DailySleepRecord:
    """Single day sleep record.

    Attributes:
        date: Sleep date (night starting).
        tst_minutes: Total sleep time (minutes).
        sleep_efficiency: Sleep efficiency (%).
        deep_sleep_pct: Deep sleep percentage.
        rem_sleep_pct: REM sleep percentage.
        light_sleep_pct: Light sleep percentage.
        awakenings: Number of awakenings.
        sleep_score: Composite sleep score (0-100).
        bedtime: Bedtime timestamp.
        wake_time: Wake time timestamp.
        quality_ok: Whether data quality was sufficient.
    """

    date: date
    tst_minutes: float = 0.0
    sleep_efficiency: float = 0.0
    deep_sleep_pct: float = 0.0
    rem_sleep_pct: float = 0.0
    light_sleep_pct: float = 0.0
    awakenings: int = 0
    sleep_score: float = 0.0
    bedtime: datetime | None = None
    wake_time: datetime | None = None
    quality_ok: bool = True


@dataclass(frozen=True, slots=True)
class DailyActivityRecord:
    """Single day activity record.

    Attributes:
        date: Activity date.
        steps: Total steps.
        active_minutes: Active minutes.
        calories: Calories burned.
        distance_km: Distance in kilometers.
        floors: Floors climbed.
        intensity_minutes: Intensity minutes.
        resting_hr: Resting heart rate.
        max_hr: Maximum heart rate.
        stress_score: Stress score (0-100).
        body_battery: Body battery level.
        quality_ok: Whether data quality was sufficient.
    """

    date: date
    steps: int = 0
    active_minutes: int = 0
    calories: int = 0
    distance_km: float = 0.0
    floors: int = 0
    intensity_minutes: int = 0
    resting_hr: float = 0.0
    max_hr: float = 0.0
    stress_score: float = 0.0
    body_battery: float = 0.0
    quality_ok: bool = True


@dataclass(frozen=True, slots=True)
class TrendAnalysis:
    """Trend analysis result for a metric.

    Attributes:
        metric_name: Name of the metric.
        status: Trend status.
        slope: Slope of trend line.
        r_squared: R² of trend fit.
        p_value: P-value for slope significance.
        percent_change: Percent change over period.
        current_value: Most recent value.
        baseline_value: Baseline (rolling mean).
        cv: Coefficient of variation.
        alert_level: Alert level based on deviation.
        interpretation: Human-readable interpretation.
    """

    metric_name: str
    status: TrendStatus
    slope: float
    r_squared: float
    p_value: float
    percent_change: float
    current_value: float
    baseline_value: float
    cv: float
    alert_level: AlertLevel
    interpretation: str


@dataclass(slots=True)
class LongitudinalSummary:
    """Summary of longitudinal tracking.

    Attributes:
        start_date: First date in tracking period.
        end_date: Last date in tracking period.
        n_days: Number of days with data.
        hrv_trends: Dict of metric -> TrendAnalysis.
        sleep_trends: Dict of metric -> TrendAnalysis.
        activity_trends: Dict of metric -> TrendAnalysis.
        correlations: Dict of metric pairs -> correlation.
        alerts: List of active alerts.
        recommendations: List of recommendations.
    """

    start_date: date
    end_date: date
    n_days: int
    hrv_trends: dict[str, TrendAnalysis] = field(default_factory=dict)
    sleep_trends: dict[str, TrendAnalysis] = field(default_factory=dict)
    activity_trends: dict[str, TrendAnalysis] = field(default_factory=dict)
    correlations: dict[str, float] = field(default_factory=dict)
    alerts: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Tracker Class
# ---------------------------------------------------------------------------


class MultiDayTracker:
    """Tracker for longitudinal HRV, sleep, and activity data."""

    def __init__(self) -> None:
        """Initialize empty tracker."""
        self._hrv_records: list[DailyHRVRecord] = []
        self._sleep_records: list[DailySleepRecord] = []
        self._activity_records: list[DailyActivityRecord] = []

    # -----------------------------------------------------------------------
    # Data ingestion
    # -----------------------------------------------------------------------

    def add_hrv_record(self, record: DailyHRVRecord) -> None:
        """Add or update HRV record for a date."""
        # Remove existing record for same date
        self._hrv_records = [r for r in self._hrv_records if r.date != record.date]
        self._hrv_records.append(record)
        self._hrv_records.sort(key=lambda r: r.date)

    def add_sleep_record(self, record: DailySleepRecord) -> None:
        """Add or update sleep record for a date."""
        self._sleep_records = [r for r in self._sleep_records if r.date != record.date]
        self._sleep_records.append(record)
        self._sleep_records.sort(key=lambda r: r.date)

    def add_activity_record(self, record: DailyActivityRecord) -> None:
        """Add or update activity record for a date."""
        self._activity_records = [r for r in self._activity_records if r.date != record.date]
        self._activity_records.append(record)
        self._activity_records.sort(key=lambda r: r.date)

    def add_hrv_records_batch(self, records: list[DailyHRVRecord]) -> None:
        """Add multiple HRV records."""
        for record in records:
            self.add_hrv_record(record)

    def add_sleep_records_batch(self, records: list[DailySleepRecord]) -> None:
        """Add multiple sleep records."""
        for record in records:
            self.add_sleep_record(record)

    def add_activity_records_batch(self, records: list[DailyActivityRecord]) -> None:
        """Add multiple activity records."""
        for record in records:
            self.add_activity_record(record)

    # -----------------------------------------------------------------------
    # Data export
    # -----------------------------------------------------------------------

    def get_hrv_dataframe(self) -> pd.DataFrame:
        """Get HRV records as DataFrame."""
        if not self._hrv_records:
            return pd.DataFrame()

        rows = []
        for r in self._hrv_records:
            rows.append({
                "date": r.date,
                "rmssd": r.rmssd,
                "sdnn": r.sdnn,
                "mean_hr": r.mean_hr,
                "lf_power": r.lf_power,
                "hf_power": r.hf_power,
                "lf_hf_ratio": r.lf_hf_ratio,
                "pnn50": r.pnn50,
                "total_power": r.total_power,
                "sample_entropy": r.sample_entropy,
                "hrv_score": r.hrv_score,
                "quality_ok": r.quality_ok,
            })
        return pd.DataFrame(rows).set_index("date")

    def get_sleep_dataframe(self) -> pd.DataFrame:
        """Get sleep records as DataFrame."""
        if not self._sleep_records:
            return pd.DataFrame()

        rows = []
        for r in self._sleep_records:
            rows.append({
                "date": r.date,
                "tst_minutes": r.tst_minutes,
                "sleep_efficiency": r.sleep_efficiency,
                "deep_sleep_pct": r.deep_sleep_pct,
                "rem_sleep_pct": r.rem_sleep_pct,
                "light_sleep_pct": r.light_sleep_pct,
                "awakenings": r.awakenings,
                "sleep_score": r.sleep_score,
                "quality_ok": r.quality_ok,
            })
        return pd.DataFrame(rows).set_index("date")

    def get_activity_dataframe(self) -> pd.DataFrame:
        """Get activity records as DataFrame."""
        if not self._activity_records:
            return pd.DataFrame()

        rows = []
        for r in self._activity_records:
            rows.append({
                "date": r.date,
                "steps": r.steps,
                "active_minutes": r.active_minutes,
                "calories": r.calories,
                "distance_km": r.distance_km,
                "resting_hr": r.resting_hr,
                "stress_score": r.stress_score,
                "body_battery": r.body_battery,
                "quality_ok": r.quality_ok,
            })
        return pd.DataFrame(rows).set_index("date")

    def get_combined_dataframe(self) -> pd.DataFrame:
        """Get all data combined by date."""
        hrv_df = self.get_hrv_dataframe()
        sleep_df = self.get_sleep_dataframe()
        activity_df = self.get_activity_dataframe()

        # Rename columns to avoid conflicts
        if not hrv_df.empty:
            hrv_df = hrv_df.add_prefix("hrv_")
        if not sleep_df.empty:
            sleep_df = sleep_df.add_prefix("sleep_")
        if not activity_df.empty:
            activity_df = activity_df.add_prefix("activity_")

        # Combine
        combined = pd.concat([hrv_df, sleep_df, activity_df], axis=1)
        return combined.sort_index()

    # -----------------------------------------------------------------------
    # Rolling statistics
    # -----------------------------------------------------------------------

    def compute_rolling_stats(
        self,
        metric: str,
        window: int = _ROLLING_WINDOW_DEFAULT,
        data_type: str = "hrv",
    ) -> pd.DataFrame:
        """Compute rolling statistics for a metric.

        Args:
            metric: Metric column name.
            window: Rolling window size in days.
            data_type: "hrv", "sleep", or "activity".

        Returns:
            DataFrame with rolling mean, std, min, max.
        """
        if data_type == "hrv":
            df = self.get_hrv_dataframe()
        elif data_type == "sleep":
            df = self.get_sleep_dataframe()
        elif data_type == "activity":
            df = self.get_activity_dataframe()
        else:
            return pd.DataFrame()

        if df.empty or metric not in df.columns:
            return pd.DataFrame()

        result = pd.DataFrame(index=df.index)
        result["value"] = df[metric]
        result["rolling_mean"] = df[metric].rolling(window, min_periods=1).mean()
        result["rolling_std"] = df[metric].rolling(window, min_periods=1).std()
        result["rolling_min"] = df[metric].rolling(window, min_periods=1).min()
        result["rolling_max"] = df[metric].rolling(window, min_periods=1).max()
        result["z_score"] = (df[metric] - result["rolling_mean"]) / (result["rolling_std"] + 1e-9)

        return result

    # -----------------------------------------------------------------------
    # Trend analysis
    # -----------------------------------------------------------------------

    def analyze_trend(
        self,
        metric: str,
        data_type: str = "hrv",
        window: int = _ROLLING_WINDOW_DEFAULT,
        higher_is_better: bool = True,
    ) -> TrendAnalysis:
        """Analyze trend for a metric.

        Args:
            metric: Metric column name.
            data_type: "hrv", "sleep", or "activity".
            window: Window for baseline calculation.
            higher_is_better: Whether higher values indicate improvement.

        Returns:
            TrendAnalysis result.
        """
        if data_type == "hrv":
            df = self.get_hrv_dataframe()
        elif data_type == "sleep":
            df = self.get_sleep_dataframe()
        elif data_type == "activity":
            df = self.get_activity_dataframe()
        else:
            return TrendAnalysis(
                metric_name=metric,
                status=TrendStatus.INSUFFICIENT_DATA,
                slope=0.0,
                r_squared=0.0,
                p_value=1.0,
                percent_change=0.0,
                current_value=0.0,
                baseline_value=0.0,
                cv=0.0,
                alert_level=AlertLevel.NORMAL,
                interpretation="Data type not recognized.",
            )

        if df.empty or metric not in df.columns:
            return TrendAnalysis(
                metric_name=metric,
                status=TrendStatus.INSUFFICIENT_DATA,
                slope=0.0,
                r_squared=0.0,
                p_value=1.0,
                percent_change=0.0,
                current_value=0.0,
                baseline_value=0.0,
                cv=0.0,
                alert_level=AlertLevel.NORMAL,
                interpretation=f"No data available for {metric}.",
            )

        values = df[metric].dropna()
        n = len(values)

        if n < _MIN_DAYS_TREND:
            return TrendAnalysis(
                metric_name=metric,
                status=TrendStatus.INSUFFICIENT_DATA,
                slope=0.0,
                r_squared=0.0,
                p_value=1.0,
                percent_change=0.0,
                current_value=float(values.iloc[-1]) if n > 0 else 0.0,
                baseline_value=float(values.mean()) if n > 0 else 0.0,
                cv=0.0,
                alert_level=AlertLevel.NORMAL,
                interpretation=f"Need at least {_MIN_DAYS_TREND} days for trend analysis.",
            )

        # Linear regression for trend
        x = np.arange(n)
        y = values.values
        slope, intercept, r_value, p_value, _ = stats.linregress(x, y)

        # Statistics
        current_value = float(y[-1])
        baseline_value = float(np.mean(y[:window]))
        mean_val = float(np.mean(y))
        std_val = float(np.std(y, ddof=1))
        cv = std_val / mean_val if mean_val != 0 else 0.0

        # Percent change
        if baseline_value != 0:
            percent_change = (current_value - baseline_value) / baseline_value * 100
        else:
            percent_change = 0.0

        # Determine trend status
        if p_value > 0.05:
            if cv > 0.15:
                status = TrendStatus.VARIABLE
            else:
                status = TrendStatus.STABLE
        elif slope > 0:
            status = TrendStatus.IMPROVING if higher_is_better else TrendStatus.DECLINING
        else:
            status = TrendStatus.DECLINING if higher_is_better else TrendStatus.IMPROVING

        # Alert level based on deviation from baseline
        z_current = (current_value - baseline_value) / (std_val + 1e-9)
        if abs(z_current) < 1:
            alert_level = AlertLevel.NORMAL
        elif abs(z_current) < 2:
            alert_level = AlertLevel.ATTENTION
        elif abs(z_current) < 3:
            alert_level = AlertLevel.WARNING
        else:
            alert_level = AlertLevel.CRITICAL

        # Interpretation
        direction = "increasing" if slope > 0 else "decreasing"
        significance = "significantly" if p_value < 0.05 else "non-significantly"
        interpretation = (
            f"{metric} is {significance} {direction} "
            f"(slope: {slope:.3f}/day, p={p_value:.3f}). "
            f"Current value is {percent_change:+.1f}% from baseline."
        )

        return TrendAnalysis(
            metric_name=metric,
            status=status,
            slope=float(slope),
            r_squared=float(r_value**2),
            p_value=float(p_value),
            percent_change=percent_change,
            current_value=current_value,
            baseline_value=baseline_value,
            cv=cv,
            alert_level=alert_level,
            interpretation=interpretation,
        )

    # -----------------------------------------------------------------------
    # Comprehensive summary
    # -----------------------------------------------------------------------

    def generate_summary(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> LongitudinalSummary:
        """Generate comprehensive longitudinal summary.

        Args:
            start_date: Start of analysis period.
            end_date: End of analysis period.

        Returns:
            LongitudinalSummary with all analyses.
        """
        # Determine date range
        all_dates: list[date] = []
        all_dates.extend(r.date for r in self._hrv_records)
        all_dates.extend(r.date for r in self._sleep_records)
        all_dates.extend(r.date for r in self._activity_records)

        if not all_dates:
            return LongitudinalSummary(
                start_date=date.today(),
                end_date=date.today(),
                n_days=0,
            )

        actual_start = start_date or min(all_dates)
        actual_end = end_date or max(all_dates)
        n_days = len(set(all_dates))

        # HRV trends
        hrv_metrics = ["rmssd", "sdnn", "mean_hr", "lf_hf_ratio", "hrv_score"]
        hrv_higher_better = {"rmssd": True, "sdnn": True, "mean_hr": False, "lf_hf_ratio": False, "hrv_score": True}
        hrv_trends = {}
        for metric in hrv_metrics:
            hrv_trends[metric] = self.analyze_trend(
                metric, "hrv", higher_is_better=hrv_higher_better.get(metric, True)
            )

        # Sleep trends
        sleep_metrics = ["tst_minutes", "sleep_efficiency", "deep_sleep_pct", "sleep_score"]
        sleep_trends = {}
        for metric in sleep_metrics:
            sleep_trends[metric] = self.analyze_trend(metric, "sleep", higher_is_better=True)

        # Activity trends
        activity_metrics = ["steps", "active_minutes", "resting_hr", "stress_score"]
        activity_higher_better = {"steps": True, "active_minutes": True, "resting_hr": False, "stress_score": False}
        activity_trends = {}
        for metric in activity_metrics:
            activity_trends[metric] = self.analyze_trend(
                metric, "activity", higher_is_better=activity_higher_better.get(metric, True)
            )

        # Cross-domain correlations
        combined_df = self.get_combined_dataframe()
        correlations: dict[str, float] = {}
        if not combined_df.empty:
            # HRV-Sleep correlations
            if "hrv_rmssd" in combined_df.columns and "sleep_tst_minutes" in combined_df.columns:
                mask = combined_df[["hrv_rmssd", "sleep_tst_minutes"]].notna().all(axis=1)
                if mask.sum() >= 5:
                    r, _ = stats.spearmanr(
                        combined_df.loc[mask, "hrv_rmssd"],
                        combined_df.loc[mask, "sleep_tst_minutes"],
                    )
                    correlations["rmssd_vs_tst"] = float(r)

            # HRV-Activity correlations
            if "hrv_rmssd" in combined_df.columns and "activity_steps" in combined_df.columns:
                mask = combined_df[["hrv_rmssd", "activity_steps"]].notna().all(axis=1)
                if mask.sum() >= 5:
                    r, _ = stats.spearmanr(
                        combined_df.loc[mask, "hrv_rmssd"],
                        combined_df.loc[mask, "activity_steps"],
                    )
                    correlations["rmssd_vs_steps"] = float(r)

        # Generate alerts
        alerts: list[str] = []
        for metric, trend in {**hrv_trends, **sleep_trends, **activity_trends}.items():
            if trend.alert_level in (AlertLevel.WARNING, AlertLevel.CRITICAL):
                alerts.append(f"⚠️ {metric}: {trend.interpretation}")

        # Generate recommendations
        recommendations: list[str] = []
        if hrv_trends.get("rmssd") and hrv_trends["rmssd"].status == TrendStatus.DECLINING:
            recommendations.append("Consider reducing training load or improving recovery.")
        if sleep_trends.get("sleep_efficiency") and sleep_trends["sleep_efficiency"].current_value < 85:
            recommendations.append("Sleep efficiency is below optimal. Review sleep hygiene practices.")
        if activity_trends.get("stress_score") and activity_trends["stress_score"].status == TrendStatus.DECLINING:
            recommendations.append("Stress levels are increasing. Consider stress management techniques.")

        return LongitudinalSummary(
            start_date=actual_start,
            end_date=actual_end,
            n_days=n_days,
            hrv_trends=hrv_trends,
            sleep_trends=sleep_trends,
            activity_trends=activity_trends,
            correlations=correlations,
            alerts=alerts,
            recommendations=recommendations,
        )

    # -----------------------------------------------------------------------
    # Intervention analysis (pre/post)
    # -----------------------------------------------------------------------

    def analyze_intervention(
        self,
        intervention_date: date,
        metric: str,
        data_type: str = "hrv",
        pre_days: int = 14,
        post_days: int = 14,
    ) -> dict[str, Any]:
        """Analyze effect of an intervention.

        Args:
            intervention_date: Date of intervention.
            metric: Metric to analyze.
            data_type: "hrv", "sleep", or "activity".
            pre_days: Days before intervention.
            post_days: Days after intervention.

        Returns:
            Dict with pre/post statistics and effect size.
        """
        if data_type == "hrv":
            df = self.get_hrv_dataframe()
        elif data_type == "sleep":
            df = self.get_sleep_dataframe()
        elif data_type == "activity":
            df = self.get_activity_dataframe()
        else:
            return {"error": "Invalid data type"}

        if df.empty or metric not in df.columns:
            return {"error": f"No data for {metric}"}

        # Convert index to date if datetime
        df = df.copy()
        df.index = pd.to_datetime(df.index).date

        # Split pre/post
        pre_start = intervention_date - timedelta(days=pre_days)
        pre_end = intervention_date - timedelta(days=1)
        post_start = intervention_date
        post_end = intervention_date + timedelta(days=post_days - 1)

        pre_mask = (df.index >= pre_start) & (df.index <= pre_end)
        post_mask = (df.index >= post_start) & (df.index <= post_end)

        pre_values = df.loc[pre_mask, metric].dropna().values
        post_values = df.loc[post_mask, metric].dropna().values

        if len(pre_values) < 3 or len(post_values) < 3:
            return {"error": "Insufficient data for pre/post analysis"}

        # Statistics
        pre_mean = float(np.mean(pre_values))
        pre_std = float(np.std(pre_values, ddof=1))
        post_mean = float(np.mean(post_values))
        post_std = float(np.std(post_values, ddof=1))

        # Effect size (Cohen's d)
        pooled_std = np.sqrt(
            ((len(pre_values) - 1) * pre_std**2 + (len(post_values) - 1) * post_std**2)
            / (len(pre_values) + len(post_values) - 2)
        )
        cohens_d = (post_mean - pre_mean) / pooled_std if pooled_std > 0 else 0.0

        # Statistical test
        _, shapiro_pre = stats.shapiro(pre_values) if len(pre_values) >= 3 else (0, 1)
        _, shapiro_post = stats.shapiro(post_values) if len(post_values) >= 3 else (0, 1)

        if shapiro_pre > 0.05 and shapiro_post > 0.05:
            stat, p_value = stats.ttest_ind(pre_values, post_values)
            test_name = "Independent t-test"
        else:
            stat, p_value = stats.mannwhitneyu(pre_values, post_values, alternative="two-sided")
            test_name = "Mann-Whitney U"

        percent_change = (post_mean - pre_mean) / pre_mean * 100 if pre_mean != 0 else 0.0

        return {
            "metric": metric,
            "intervention_date": intervention_date.isoformat(),
            "pre_n": len(pre_values),
            "post_n": len(post_values),
            "pre_mean": pre_mean,
            "pre_std": pre_std,
            "post_mean": post_mean,
            "post_std": post_std,
            "percent_change": percent_change,
            "cohens_d": float(cohens_d),
            "test_name": test_name,
            "test_statistic": float(stat),
            "p_value": float(p_value),
            "significant": p_value < 0.05,
        }

    # -----------------------------------------------------------------------
    # Data quality
    # -----------------------------------------------------------------------

    def get_data_completeness(self) -> dict[str, Any]:
        """Get data completeness statistics."""
        hrv_df = self.get_hrv_dataframe()
        sleep_df = self.get_sleep_dataframe()
        activity_df = self.get_activity_dataframe()

        result: dict[str, Any] = {
            "hrv_days": len(hrv_df),
            "sleep_days": len(sleep_df),
            "activity_days": len(activity_df),
        }

        # Missing data analysis
        if not hrv_df.empty:
            date_range = pd.date_range(hrv_df.index.min(), hrv_df.index.max())
            result["hrv_missing_days"] = len(date_range) - len(hrv_df)

        if not sleep_df.empty:
            date_range = pd.date_range(sleep_df.index.min(), sleep_df.index.max())
            result["sleep_missing_days"] = len(date_range) - len(sleep_df)

        if not activity_df.empty:
            date_range = pd.date_range(activity_df.index.min(), activity_df.index.max())
            result["activity_missing_days"] = len(date_range) - len(activity_df)

        return result

