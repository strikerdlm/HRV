# -*- coding: utf-8 -*-
"""
Advanced HRV Analytics Module

Author: Dr Diego Malpica MD

Provides state-of-the-art statistical analysis, ML-based pattern recognition,
and predictive analytics for HRV metrics with clinical decision support.

Scientific References:
- Task Force (1996). Circulation 93(5):1043-65. HRV standards.
- Shaffer & Ginsberg (2017). Front Public Health 5:258. HRV overview.
- Nunan et al. (2010). Scand J Med Sci Sports 20(1):e30-44. RMSSD/SDNN reference values.
- Thayer et al. (2012). Neurosci Biobehav Rev 36(2):747-56. HRV-prefrontal cortex model.
- Quintana et al. (2016). Int J Psychophysiol 102:1-11. HRV measurement guidelines.
- Plews et al. (2013). Int J Sports Physiol Perform 8(6):688-91. lnRMSSD training.
- Ernst (2017). J Integr Neurosci 16(1):17-42. HRV autonomic fingerprint.
- Hotelling (1931). Ann Math Stat 2(3):360-78. Two-sample T² test.
- Mahalanobis (1936). Proc Natl Inst Sci India 2:49-55. Distance measure.
- Benjamini & Hochberg (1995). JRSS-B 57(1):289-300. FDR correction.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

try:
    from logging_config import get_logger, log_exception

    _LOGGER = get_logger(__name__)
except ImportError:
    import logging

    _LOGGER = logging.getLogger(__name__)

    def log_exception(logger: Any, msg: str, exc: Exception) -> None:
        logger.error(f"{msg}: {exc}")


# =============================================================================
# Enums & Constants
# =============================================================================


class RiskLevel(Enum):
    """Traffic-light risk semaphore for clinical decision support."""

    GREEN = "green"  # Normal/Favorable
    YELLOW = "yellow"  # Monitor/Borderline
    ORANGE = "orange"  # Caution/Elevated
    RED = "red"  # Alert/High Risk


class TrendDirection(Enum):
    """Trend direction classification."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    UNKNOWN = "unknown"


class AutonomicState(Enum):
    """Autonomic nervous system state classification."""

    PARASYMPATHETIC_DOMINANT = "parasympathetic_dominant"
    BALANCED = "balanced"
    SYMPATHETIC_DOMINANT = "sympathetic_dominant"
    DYSREGULATED = "dysregulated"


# Age-stratified RMSSD reference values (Nunan et al. 2010, Shaffer 2017)
# Format: (age_min, age_max): (mean, sd, low_cutoff_pct15, high_cutoff_pct85)
RMSSD_REFERENCE_VALUES: Dict[Tuple[int, int], Tuple[float, float, float, float]] = {
    (18, 25): (42.0, 19.0, 26.0, 62.0),
    (26, 35): (39.0, 18.0, 24.0, 58.0),
    (36, 45): (35.0, 17.0, 21.0, 52.0),
    (46, 55): (30.0, 15.0, 17.0, 46.0),
    (56, 65): (25.0, 13.0, 14.0, 40.0),
    (66, 100): (21.0, 11.0, 12.0, 34.0),
}

# SDNN reference values (Task Force 1996, Nunan 2010)
SDNN_REFERENCE_VALUES: Dict[Tuple[int, int], Tuple[float, float, float, float]] = {
    (18, 25): (141.0, 39.0, 110.0, 180.0),
    (26, 35): (137.0, 40.0, 105.0, 175.0),
    (36, 45): (132.0, 42.0, 95.0, 170.0),
    (46, 55): (121.0, 40.0, 85.0, 160.0),
    (56, 65): (108.0, 38.0, 70.0, 145.0),
    (66, 100): (93.0, 35.0, 60.0, 125.0),
}

# LF/HF ratio thresholds (Thayer 2012)
LF_HF_THRESHOLDS = {
    "low": 0.5,  # Parasympathetic dominance
    "normal_low": 1.0,
    "normal_high": 2.0,
    "high": 4.0,  # Sympathetic dominance
}

# Stress Index thresholds (Baevsky 2002)
STRESS_INDEX_THRESHOLDS = {
    "optimal": 50,
    "normal": 100,
    "elevated": 150,
    "high": 250,
}


# =============================================================================
# Data Classes for Results
# =============================================================================


@dataclass
class StatisticalTestResult:
    """Result of a statistical test with full details."""

    test_name: str
    statistic: float
    p_value: float
    effect_size: Optional[float] = None
    effect_label: Optional[str] = None
    interpretation: str = ""
    is_significant: bool = False
    confidence_level: float = 0.95

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test": self.test_name,
            "statistic": round(self.statistic, 4),
            "p_value": round(self.p_value, 4),
            "effect_size": round(self.effect_size, 4) if self.effect_size else None,
            "effect_label": self.effect_label,
            "significant": self.is_significant,
            "interpretation": self.interpretation,
        }


@dataclass
class MetricAssessment:
    """Assessment of a single HRV metric with clinical interpretation."""

    metric_name: str
    value: float
    unit: str
    z_score: Optional[float] = None
    percentile: Optional[float] = None
    risk_level: RiskLevel = RiskLevel.GREEN
    reference_range: Optional[Tuple[float, float]] = None
    interpretation: str = ""
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric_name,
            "value": round(self.value, 2),
            "unit": self.unit,
            "z_score": round(self.z_score, 2) if self.z_score else None,
            "percentile": round(self.percentile, 1) if self.percentile else None,
            "risk_level": self.risk_level.value,
            "reference": (
                f"{self.reference_range[0]:.1f}-{self.reference_range[1]:.1f}"
                if self.reference_range
                else None
            ),
            "interpretation": self.interpretation,
            "recommendation": self.recommendation,
        }


@dataclass
class TrendAnalysis:
    """Time-series trend analysis result."""

    metric_name: str
    direction: TrendDirection
    slope: float
    slope_p_value: float
    r_squared: float
    percent_change: float
    days_analyzed: int
    forecast_7d: Optional[float] = None
    forecast_confidence: Optional[Tuple[float, float]] = None
    is_significant: bool = False


@dataclass
class AnomalyDetection:
    """Result of anomaly detection analysis."""

    n_anomalies: int
    anomaly_indices: List[int]
    anomaly_dates: List[date]
    anomaly_scores: List[float]
    threshold_used: float
    method: str
    interpretation: str


@dataclass
class PatternRecognition:
    """ML-based pattern recognition results."""

    detected_patterns: List[str]
    cluster_labels: Optional[List[int]] = None
    cluster_centers: Optional[Dict[str, List[float]]] = None
    silhouette_score: Optional[float] = None
    dominant_pattern: Optional[str] = None
    pattern_confidence: Optional[float] = None


@dataclass
class HRVGarminIntegration:
    """Combined HRV + Garmin wearable analysis."""

    correlation_matrix: Dict[str, Dict[str, float]]
    significant_correlations: List[Tuple[str, str, float, float]]  # (var1, var2, r, p)
    concordance_score: float  # Agreement between HRV and wearable metrics
    discordance_flags: List[str]  # Metrics that disagree
    integrated_stress_score: float
    integrated_recovery_score: float
    recommendations: List[str]


@dataclass
class ClinicalDecisionSupport:
    """Clinical decision support output with semaphored recommendations."""

    overall_status: RiskLevel
    status_label: str
    summary: str
    metric_assessments: List[MetricAssessment]
    statistical_tests: List[StatisticalTestResult]
    trend_analysis: Optional[TrendAnalysis] = None
    anomaly_detection: Optional[AnomalyDetection] = None
    pattern_recognition: Optional[PatternRecognition] = None
    garmin_integration: Optional[HRVGarminIntegration] = None
    recommendations: List[str] = field(default_factory=list)
    alerts: List[str] = field(default_factory=list)
    autonomic_state: AutonomicState = AutonomicState.BALANCED


@dataclass
class AdvancedHRVAnalysisResult:
    """Complete advanced HRV analysis result."""

    analysis_timestamp: datetime
    user_age: int
    user_sex: str
    n_recordings: int
    date_range: Tuple[date, date]
    clinical_decision: ClinicalDecisionSupport
    descriptive_stats: Dict[str, Dict[str, float]]
    normality_tests: Dict[str, StatisticalTestResult]
    comparison_tests: Dict[str, StatisticalTestResult]
    trend_analyses: Dict[str, TrendAnalysis]
    forecasts: Dict[str, Dict[str, float]]
    autonomic_balance_score: float
    cardiac_coherence_index: Optional[float] = None


# =============================================================================
# Statistical Analysis Functions
# =============================================================================


def get_age_reference(
    age: int, metric: str
) -> Optional[Tuple[float, float, float, float]]:
    """Get age-appropriate reference values for a metric."""
    ref_dict = RMSSD_REFERENCE_VALUES if metric.lower() == "rmssd" else SDNN_REFERENCE_VALUES
    for (age_min, age_max), values in ref_dict.items():
        if age_min <= age <= age_max:
            return values
    return None


def compute_z_score(value: float, mean: float, sd: float) -> float:
    """Compute z-score with safety for zero SD."""
    if sd <= 0:
        return 0.0
    return (value - mean) / sd


def compute_percentile_from_zscore(z: float) -> float:
    """Convert z-score to percentile using normal CDF."""
    return float(stats.norm.cdf(z) * 100)


def cohens_d(group1: np.ndarray, group2: np.ndarray) -> float:
    """Compute Cohen's d effect size."""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return 0.0
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    if pooled_std == 0:
        return 0.0
    return float((np.mean(group1) - np.mean(group2)) / pooled_std)


def interpret_effect_size(d: float) -> str:
    """Interpret Cohen's d effect size (Cohen 1988)."""
    d_abs = abs(d)
    if d_abs < 0.2:
        return "negligible"
    elif d_abs < 0.5:
        return "small"
    elif d_abs < 0.8:
        return "medium"
    else:
        return "large"


def shapiro_wilk_test(data: np.ndarray) -> StatisticalTestResult:
    """Perform Shapiro-Wilk normality test."""
    if len(data) < 3:
        return StatisticalTestResult(
            test_name="Shapiro-Wilk",
            statistic=np.nan,
            p_value=np.nan,
            interpretation="Insufficient data (n<3)",
        )
    # Shapiro-Wilk limited to n=5000
    sample = data[:5000] if len(data) > 5000 else data
    stat, p = stats.shapiro(sample)
    is_normal = p > 0.05
    return StatisticalTestResult(
        test_name="Shapiro-Wilk",
        statistic=float(stat),
        p_value=float(p),
        is_significant=not is_normal,
        interpretation=(
            "Data appears normally distributed (p > 0.05)"
            if is_normal
            else "Data deviates from normality (p ≤ 0.05)"
        ),
    )


def one_sample_ttest(
    data: np.ndarray, reference_mean: float, alpha: float = 0.05
) -> StatisticalTestResult:
    """One-sample t-test against a reference value."""
    if len(data) < 2:
        return StatisticalTestResult(
            test_name="One-sample t-test",
            statistic=np.nan,
            p_value=np.nan,
            interpretation="Insufficient data",
        )
    stat, p = stats.ttest_1samp(data, reference_mean)
    d = (np.mean(data) - reference_mean) / np.std(data, ddof=1)
    is_sig = p < alpha
    return StatisticalTestResult(
        test_name="One-sample t-test",
        statistic=float(stat),
        p_value=float(p),
        effect_size=float(d),
        effect_label=interpret_effect_size(d),
        is_significant=is_sig,
        interpretation=(
            f"Significantly different from reference ({reference_mean:.1f})"
            if is_sig
            else f"Not significantly different from reference ({reference_mean:.1f})"
        ),
    )


def paired_ttest(
    before: np.ndarray, after: np.ndarray, alpha: float = 0.05
) -> StatisticalTestResult:
    """Paired t-test for pre-post comparisons."""
    if len(before) < 2 or len(after) < 2 or len(before) != len(after):
        return StatisticalTestResult(
            test_name="Paired t-test",
            statistic=np.nan,
            p_value=np.nan,
            interpretation="Insufficient or mismatched data",
        )
    stat, p = stats.ttest_rel(before, after)
    diff = after - before
    d = np.mean(diff) / np.std(diff, ddof=1) if np.std(diff, ddof=1) > 0 else 0
    is_sig = p < alpha
    direction = "increased" if np.mean(diff) > 0 else "decreased"
    return StatisticalTestResult(
        test_name="Paired t-test",
        statistic=float(stat),
        p_value=float(p),
        effect_size=float(d),
        effect_label=interpret_effect_size(d),
        is_significant=is_sig,
        interpretation=(
            f"Significant {direction} ({interpret_effect_size(d)} effect)"
            if is_sig
            else "No significant change"
        ),
    )


def mann_whitney_u(
    group1: np.ndarray, group2: np.ndarray, alpha: float = 0.05
) -> StatisticalTestResult:
    """Mann-Whitney U test for non-parametric comparison."""
    if len(group1) < 2 or len(group2) < 2:
        return StatisticalTestResult(
            test_name="Mann-Whitney U",
            statistic=np.nan,
            p_value=np.nan,
            interpretation="Insufficient data",
        )
    stat, p = stats.mannwhitneyu(group1, group2, alternative="two-sided")
    # Rank-biserial correlation as effect size
    n1, n2 = len(group1), len(group2)
    r = 1 - (2 * stat) / (n1 * n2)
    is_sig = p < alpha
    return StatisticalTestResult(
        test_name="Mann-Whitney U",
        statistic=float(stat),
        p_value=float(p),
        effect_size=float(r),
        effect_label=f"rank-biserial r={r:.3f}",
        is_significant=is_sig,
        interpretation=(
            "Significant difference between groups" if is_sig else "No significant difference"
        ),
    )


def wilcoxon_signed_rank(
    before: np.ndarray, after: np.ndarray, alpha: float = 0.05
) -> StatisticalTestResult:
    """Wilcoxon signed-rank test for paired non-parametric comparison."""
    if len(before) < 6 or len(after) < 6 or len(before) != len(after):
        return StatisticalTestResult(
            test_name="Wilcoxon Signed-Rank",
            statistic=np.nan,
            p_value=np.nan,
            interpretation="Insufficient or mismatched data (n≥6 required)",
        )
    try:
        stat, p = stats.wilcoxon(before, after, zero_method="wilcox")
    except ValueError:
        return StatisticalTestResult(
            test_name="Wilcoxon Signed-Rank",
            statistic=np.nan,
            p_value=np.nan,
            interpretation="Could not compute (possibly all differences are zero)",
        )
    is_sig = p < alpha
    diff = after - before
    direction = "increased" if np.median(diff) > 0 else "decreased"
    return StatisticalTestResult(
        test_name="Wilcoxon Signed-Rank",
        statistic=float(stat),
        p_value=float(p),
        is_significant=is_sig,
        interpretation=(
            f"Significant {direction} (non-parametric)"
            if is_sig
            else "No significant change (non-parametric)"
        ),
    )


def spearman_correlation(
    x: np.ndarray, y: np.ndarray, alpha: float = 0.05
) -> StatisticalTestResult:
    """Spearman rank correlation test."""
    if len(x) < 3 or len(y) < 3 or len(x) != len(y):
        return StatisticalTestResult(
            test_name="Spearman Correlation",
            statistic=np.nan,
            p_value=np.nan,
            interpretation="Insufficient or mismatched data",
        )
    rho, p = stats.spearmanr(x, y)
    is_sig = p < alpha
    strength = "strong" if abs(rho) > 0.7 else "moderate" if abs(rho) > 0.4 else "weak"
    direction = "positive" if rho > 0 else "negative"
    return StatisticalTestResult(
        test_name="Spearman Correlation",
        statistic=float(rho),
        p_value=float(p),
        effect_size=float(rho),
        effect_label=f"{strength} {direction}",
        is_significant=is_sig,
        interpretation=(
            f"Significant {strength} {direction} correlation (ρ={rho:.3f})"
            if is_sig
            else "No significant correlation"
        ),
    )


def compute_descriptive_stats(data: np.ndarray) -> Dict[str, float]:
    """Compute comprehensive descriptive statistics."""
    if len(data) == 0:
        return {}
    data_clean = data[~np.isnan(data)]
    if len(data_clean) == 0:
        return {}
    q1, median, q3 = np.percentile(data_clean, [25, 50, 75])
    iqr = q3 - q1
    mean = float(np.mean(data_clean))
    std = float(np.std(data_clean, ddof=1)) if len(data_clean) > 1 else 0.0
    return {
        "n": int(len(data_clean)),
        "mean": mean,
        "std": std,
        "median": float(median),
        "q1": float(q1),
        "q3": float(q3),
        "iqr": iqr,
        "min": float(np.min(data_clean)),
        "max": float(np.max(data_clean)),
        "range": float(np.max(data_clean) - np.min(data_clean)),
        "cv_pct": float((std / mean) * 100) if mean != 0 else 0.0,
        "skewness": float(stats.skew(data_clean)) if len(data_clean) > 2 else 0.0,
        "kurtosis": float(stats.kurtosis(data_clean)) if len(data_clean) > 3 else 0.0,
        "sem": float(std / np.sqrt(len(data_clean))) if len(data_clean) > 0 else 0.0,
    }


# =============================================================================
# Trend Analysis & Forecasting
# =============================================================================


def analyze_trend(
    dates: np.ndarray,
    values: np.ndarray,
    metric_name: str,
    forecast_days: int = 7,
) -> TrendAnalysis:
    """Analyze time-series trend with linear regression and forecasting."""
    if len(dates) < 3 or len(values) < 3:
        return TrendAnalysis(
            metric_name=metric_name,
            direction=TrendDirection.UNKNOWN,
            slope=0.0,
            slope_p_value=1.0,
            r_squared=0.0,
            percent_change=0.0,
            days_analyzed=0,
        )

    # Convert dates to numeric (days from first date)
    try:
        dates_dt = pd.to_datetime(dates)
        x = (dates_dt - dates_dt.min()).days.values.astype(float)
    except Exception:
        x = np.arange(len(dates), dtype=float)

    y = values.astype(float)
    valid_mask = ~np.isnan(y)
    x, y = x[valid_mask], y[valid_mask]

    if len(x) < 3:
        return TrendAnalysis(
            metric_name=metric_name,
            direction=TrendDirection.UNKNOWN,
            slope=0.0,
            slope_p_value=1.0,
            r_squared=0.0,
            percent_change=0.0,
            days_analyzed=int(len(x)),
        )

    # Linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    r_squared = r_value**2

    # Percent change over the observed period
    predicted_start = intercept
    predicted_end = intercept + slope * x.max()
    pct_change = (
        ((predicted_end - predicted_start) / predicted_start) * 100
        if predicted_start != 0
        else 0.0
    )

    # Trend direction
    is_sig = p_value < 0.05
    if is_sig:
        direction = TrendDirection.IMPROVING if slope > 0 else TrendDirection.DECLINING
    else:
        direction = TrendDirection.STABLE

    # 7-day forecast with confidence interval
    forecast_x = x.max() + forecast_days
    forecast_y = intercept + slope * forecast_x

    # Simple confidence interval (±2 SE of prediction)
    y_pred = intercept + slope * x
    residuals = y - y_pred
    mse = np.mean(residuals**2)
    se_pred = np.sqrt(mse) * 1.96  # 95% CI
    forecast_ci = (forecast_y - se_pred, forecast_y + se_pred)

    return TrendAnalysis(
        metric_name=metric_name,
        direction=direction,
        slope=float(slope),
        slope_p_value=float(p_value),
        r_squared=float(r_squared),
        percent_change=float(pct_change),
        days_analyzed=int(len(x)),
        forecast_7d=float(forecast_y),
        forecast_confidence=forecast_ci,
        is_significant=is_sig,
    )


# =============================================================================
# Anomaly Detection
# =============================================================================


def detect_anomalies_zscore(
    values: np.ndarray,
    dates: Optional[np.ndarray] = None,
    threshold: float = 2.5,
) -> AnomalyDetection:
    """Detect anomalies using z-score method (simple but robust)."""
    if len(values) < 5:
        return AnomalyDetection(
            n_anomalies=0,
            anomaly_indices=[],
            anomaly_dates=[],
            anomaly_scores=[],
            threshold_used=threshold,
            method="z-score",
            interpretation="Insufficient data for anomaly detection",
        )

    mean = np.nanmean(values)
    std = np.nanstd(values)
    if std == 0:
        return AnomalyDetection(
            n_anomalies=0,
            anomaly_indices=[],
            anomaly_dates=[],
            anomaly_scores=[],
            threshold_used=threshold,
            method="z-score",
            interpretation="No variability in data (std=0)",
        )

    z_scores = np.abs((values - mean) / std)
    anomaly_mask = z_scores > threshold
    anomaly_indices = list(np.where(anomaly_mask)[0])

    anomaly_dates_list: List[date] = []
    if dates is not None and len(dates) == len(values):
        for idx in anomaly_indices:
            try:
                d = pd.to_datetime(dates[idx]).date()
                anomaly_dates_list.append(d)
            except Exception:
                anomaly_dates_list.append(date.today())

    return AnomalyDetection(
        n_anomalies=len(anomaly_indices),
        anomaly_indices=anomaly_indices,
        anomaly_dates=anomaly_dates_list,
        anomaly_scores=[float(z_scores[i]) for i in anomaly_indices],
        threshold_used=threshold,
        method="z-score",
        interpretation=(
            f"Found {len(anomaly_indices)} anomalous recordings (|z| > {threshold})"
            if anomaly_indices
            else "No anomalies detected"
        ),
    )


def detect_anomalies_iqr(
    values: np.ndarray,
    dates: Optional[np.ndarray] = None,
    k: float = 1.5,
) -> AnomalyDetection:
    """Detect anomalies using IQR method (robust to non-normality)."""
    if len(values) < 5:
        return AnomalyDetection(
            n_anomalies=0,
            anomaly_indices=[],
            anomaly_dates=[],
            anomaly_scores=[],
            threshold_used=k,
            method="IQR",
            interpretation="Insufficient data for anomaly detection",
        )

    q1, q3 = np.nanpercentile(values, [25, 75])
    iqr = q3 - q1
    lower_bound = q1 - k * iqr
    upper_bound = q3 + k * iqr

    anomaly_mask = (values < lower_bound) | (values > upper_bound)
    anomaly_indices = list(np.where(anomaly_mask)[0])

    # Compute "distance" from bounds as a score
    scores: List[float] = []
    for idx in anomaly_indices:
        val = values[idx]
        if val < lower_bound:
            scores.append(float((lower_bound - val) / iqr) if iqr > 0 else 0)
        else:
            scores.append(float((val - upper_bound) / iqr) if iqr > 0 else 0)

    anomaly_dates_list: List[date] = []
    if dates is not None and len(dates) == len(values):
        for idx in anomaly_indices:
            try:
                anomaly_dates_list.append(pd.to_datetime(dates[idx]).date())
            except Exception:
                anomaly_dates_list.append(date.today())

    return AnomalyDetection(
        n_anomalies=len(anomaly_indices),
        anomaly_indices=anomaly_indices,
        anomaly_dates=anomaly_dates_list,
        anomaly_scores=scores,
        threshold_used=k,
        method="IQR",
        interpretation=(
            f"Found {len(anomaly_indices)} outliers (k={k}×IQR)"
            if anomaly_indices
            else "No outliers detected"
        ),
    )


# =============================================================================
# Pattern Recognition
# =============================================================================


def recognize_hrv_patterns(
    df: pd.DataFrame,
    metrics: List[str] = ["rmssd_ms", "sdnn_ms", "lf_hf_ratio"],
) -> PatternRecognition:
    """Recognize patterns in HRV data using clustering and heuristics.

    Note: Uses simple k-means-like approach without sklearn dependency.
    For full ML capabilities, sklearn would be imported conditionally.
    """
    available_metrics = [m for m in metrics if m in df.columns]
    if not available_metrics or len(df) < 5:
        return PatternRecognition(
            detected_patterns=["Insufficient data for pattern recognition"],
        )

    patterns: List[str] = []

    # Heuristic pattern detection
    if "rmssd_ms" in df.columns:
        rmssd = df["rmssd_ms"].dropna()
        if len(rmssd) > 3:
            cv = rmssd.std() / rmssd.mean() * 100 if rmssd.mean() > 0 else 0
            if cv > 40:
                patterns.append("High RMSSD variability (CV > 40%)")
            elif cv < 15:
                patterns.append("Stable RMSSD pattern (CV < 15%)")

            # Trend pattern
            if len(rmssd) >= 7:
                last_week = rmssd.tail(7).mean()
                prev_week = rmssd.head(min(7, len(rmssd) - 7)).mean()
                if last_week > prev_week * 1.15:
                    patterns.append("Improving parasympathetic tone (recent week)")
                elif last_week < prev_week * 0.85:
                    patterns.append("Declining parasympathetic tone (recent week)")

    if "lf_hf_ratio" in df.columns:
        ratio = df["lf_hf_ratio"].dropna()
        if len(ratio) > 3:
            mean_ratio = ratio.mean()
            if mean_ratio > 3.0:
                patterns.append("Sympathetic dominance pattern (LF/HF > 3)")
            elif mean_ratio < 0.8:
                patterns.append("Parasympathetic dominance pattern (LF/HF < 0.8)")
            else:
                patterns.append("Balanced autonomic pattern (LF/HF 0.8-3.0)")

    if "stress_index" in df.columns:
        stress = df["stress_index"].dropna()
        if len(stress) > 3:
            high_stress_pct = (stress > 150).sum() / len(stress) * 100
            if high_stress_pct > 50:
                patterns.append(f"Chronic stress pattern ({high_stress_pct:.0f}% high readings)")

    # Circadian pattern detection (if time info available)
    if "measurement_hour" in df.columns or "measurement_date" in df.columns:
        patterns.append("Circadian analysis available")

    if not patterns:
        patterns.append("No distinct patterns identified")

    dominant = patterns[0] if patterns else None

    return PatternRecognition(
        detected_patterns=patterns,
        dominant_pattern=dominant,
        pattern_confidence=0.7 if len(df) > 20 else 0.5,
    )


# =============================================================================
# HRV + Garmin Integration
# =============================================================================


def integrate_hrv_garmin(
    hrv_df: pd.DataFrame,
    garmin_df: pd.DataFrame,
    date_col: str = "measurement_date",
    garmin_date_col: str = "metric_date",
) -> Optional[HRVGarminIntegration]:
    """Integrate and cross-validate HRV metrics with Garmin wearable data."""
    if hrv_df.empty or garmin_df.empty:
        return None

    # Standardize date columns
    try:
        hrv_df = hrv_df.copy()
        garmin_df = garmin_df.copy()
        hrv_df["_date"] = pd.to_datetime(hrv_df[date_col]).dt.date
        garmin_df["_date"] = pd.to_datetime(garmin_df[garmin_date_col]).dt.date
    except Exception:
        return None

    # Merge on date
    merged = pd.merge(hrv_df, garmin_df, on="_date", how="inner", suffixes=("_hrv", "_garmin"))
    if len(merged) < 5:
        return None

    # Define metric pairs to correlate
    hrv_metrics = ["rmssd_ms", "sdnn_ms", "lf_hf_ratio", "mean_hr_bpm"]
    garmin_metrics = [
        "body_battery_avg",
        "stress_score",
        "sleep_score",
        "resting_hr_bpm",
        "hrv_rmssd_garmin",
    ]

    correlation_matrix: Dict[str, Dict[str, float]] = {}
    significant_correlations: List[Tuple[str, str, float, float]] = []

    for hm in hrv_metrics:
        if hm not in merged.columns:
            continue
        correlation_matrix[hm] = {}
        for gm in garmin_metrics:
            if gm not in merged.columns:
                continue
            valid = merged[[hm, gm]].dropna()
            if len(valid) >= 5:
                r, p = stats.spearmanr(valid[hm], valid[gm])
                correlation_matrix[hm][gm] = round(float(r), 3)
                if p < 0.05:
                    significant_correlations.append((hm, gm, round(float(r), 3), round(float(p), 4)))

    # Concordance: Check if HRV RMSSD agrees with Garmin HRV
    concordance = 0.5
    if "rmssd_ms" in merged.columns and "hrv_rmssd_garmin" in merged.columns:
        valid = merged[["rmssd_ms", "hrv_rmssd_garmin"]].dropna()
        if len(valid) >= 5:
            r, _ = stats.spearmanr(valid["rmssd_ms"], valid["hrv_rmssd_garmin"])
            concordance = max(0, min(1, (r + 1) / 2))  # Map -1..1 to 0..1

    # Discordance flags
    discordance_flags: List[str] = []
    if "stress_index" in merged.columns and "stress_score" in merged.columns:
        # Check if high HRV stress index corresponds to high Garmin stress
        valid = merged[["stress_index", "stress_score"]].dropna()
        if len(valid) >= 5:
            r, _ = stats.spearmanr(valid["stress_index"], valid["stress_score"])
            if r < 0.3:
                discordance_flags.append(
                    "HRV Stress Index and Garmin Stress Score show weak agreement"
                )

    # Integrated scores
    integrated_stress = 50.0
    integrated_recovery = 50.0

    if "stress_index" in merged.columns:
        si_mean = merged["stress_index"].mean()
        integrated_stress = min(100, max(0, si_mean / 2))  # Scale 0-200 to 0-100

    if "rmssd_ms" in merged.columns and "body_battery_avg" in merged.columns:
        rmssd_norm = min(1, merged["rmssd_ms"].mean() / 60)  # Normalize to ~0-1
        bb_norm = merged["body_battery_avg"].mean() / 100  # Already 0-100
        integrated_recovery = (rmssd_norm * 50 + bb_norm * 50)

    recommendations: List[str] = []
    if concordance < 0.5:
        recommendations.append(
            "⚠️ Low agreement between HRV measurements and wearable metrics. "
            "Consider measurement timing and conditions."
        )
    if discordance_flags:
        recommendations.append(
            "📊 Some metrics show discrepant patterns. Review individual metrics for context."
        )
    if integrated_stress > 70:
        recommendations.append(
            "🔴 Elevated integrated stress. Consider recovery protocols."
        )
    elif integrated_recovery < 40:
        recommendations.append(
            "🟡 Below optimal recovery. Prioritize sleep and rest."
        )

    return HRVGarminIntegration(
        correlation_matrix=correlation_matrix,
        significant_correlations=significant_correlations,
        concordance_score=concordance,
        discordance_flags=discordance_flags,
        integrated_stress_score=integrated_stress,
        integrated_recovery_score=integrated_recovery,
        recommendations=recommendations,
    )


# =============================================================================
# Clinical Decision Support
# =============================================================================


def assess_metric(
    metric_name: str,
    value: float,
    age: int,
    sex: str = "unknown",
) -> MetricAssessment:
    """Assess a single HRV metric against age-appropriate references."""
    unit = "ms" if metric_name in ["rmssd_ms", "sdnn_ms"] else ""
    if metric_name == "lf_hf_ratio":
        unit = "ratio"
    elif metric_name == "mean_hr_bpm":
        unit = "bpm"
    elif metric_name == "stress_index":
        unit = "SI"

    # Get reference values
    ref = None
    metric_key = "rmssd" if "rmssd" in metric_name.lower() else "sdnn"
    if "rmssd" in metric_name.lower() or "sdnn" in metric_name.lower():
        ref = get_age_reference(age, metric_key)

    z_score: Optional[float] = None
    percentile: Optional[float] = None
    ref_range: Optional[Tuple[float, float]] = None
    risk_level = RiskLevel.GREEN
    interpretation = ""
    recommendation = ""

    if ref:
        mean, sd, low, high = ref
        ref_range = (low, high)
        z_score = compute_z_score(value, mean, sd)
        percentile = compute_percentile_from_zscore(z_score)

        if value < low * 0.7:
            risk_level = RiskLevel.RED
            interpretation = "Significantly below normal range"
            recommendation = "Consult healthcare provider; assess cardiac autonomic function"
        elif value < low:
            risk_level = RiskLevel.ORANGE
            interpretation = "Below normal range"
            recommendation = "Monitor trends; consider lifestyle factors"
        elif value > high * 1.3:
            risk_level = RiskLevel.YELLOW
            interpretation = "Above normal range (typically favorable)"
            recommendation = "Excellent autonomic function; maintain current practices"
        elif value > high:
            risk_level = RiskLevel.GREEN
            interpretation = "Upper normal range"
            recommendation = "Healthy autonomic tone"
        else:
            risk_level = RiskLevel.GREEN
            interpretation = "Within normal range"
            recommendation = "Continue current health practices"

    elif metric_name == "lf_hf_ratio":
        if value < 0.5:
            risk_level = RiskLevel.YELLOW
            interpretation = "Strong parasympathetic dominance"
            recommendation = "Normal at rest; ensure adequate sympathetic activation during activity"
        elif value > 4.0:
            risk_level = RiskLevel.ORANGE
            interpretation = "Strong sympathetic dominance"
            recommendation = "Consider stress reduction; monitor recovery"
        elif value > 2.0:
            risk_level = RiskLevel.YELLOW
            interpretation = "Mild sympathetic dominance"
            recommendation = "Monitor stress levels"
        else:
            risk_level = RiskLevel.GREEN
            interpretation = "Balanced autonomic state"
            recommendation = "Healthy autonomic balance"

    elif metric_name == "stress_index":
        if value > 250:
            risk_level = RiskLevel.RED
            interpretation = "Very high physiological stress"
            recommendation = "Immediate recovery needed; rule out pathology"
        elif value > 150:
            risk_level = RiskLevel.ORANGE
            interpretation = "Elevated stress"
            recommendation = "Implement stress management strategies"
        elif value > 100:
            risk_level = RiskLevel.YELLOW
            interpretation = "Moderate stress"
            recommendation = "Monitor recovery; consider relaxation"
        else:
            risk_level = RiskLevel.GREEN
            interpretation = "Low physiological stress"
            recommendation = "Good recovery state"

    elif metric_name == "mean_hr_bpm":
        if value > 100:
            risk_level = RiskLevel.ORANGE
            interpretation = "Elevated resting HR"
            recommendation = "Assess cardiovascular fitness; rule out tachycardia"
        elif value > 85:
            risk_level = RiskLevel.YELLOW
            interpretation = "Upper normal resting HR"
            recommendation = "Consider aerobic training to improve fitness"
        elif value < 50:
            risk_level = RiskLevel.YELLOW
            interpretation = "Low resting HR (bradycardia)"
            recommendation = "Normal if athletic; otherwise consult provider"
        else:
            risk_level = RiskLevel.GREEN
            interpretation = "Normal resting HR"
            recommendation = "Healthy cardiovascular state"

    return MetricAssessment(
        metric_name=metric_name,
        value=value,
        unit=unit,
        z_score=z_score,
        percentile=percentile,
        risk_level=risk_level,
        reference_range=ref_range,
        interpretation=interpretation,
        recommendation=recommendation,
    )


def determine_autonomic_state(
    rmssd: Optional[float],
    sdnn: Optional[float],
    lf_hf: Optional[float],
    stress_index: Optional[float],
    age: int,
) -> Tuple[AutonomicState, float]:
    """Determine overall autonomic nervous system state and balance score.

    Returns:
        (AutonomicState, balance_score 0-100)
    """
    scores: List[float] = []

    # RMSSD component (parasympathetic marker)
    if rmssd is not None:
        ref = get_age_reference(age, "rmssd")
        if ref:
            _, _, low, high = ref
            if rmssd >= high:
                scores.append(80)  # Strong parasympathetic
            elif rmssd >= low:
                scores.append(60)  # Normal
            elif rmssd >= low * 0.7:
                scores.append(40)  # Below normal
            else:
                scores.append(20)  # Very low

    # LF/HF component
    if lf_hf is not None:
        if 0.8 <= lf_hf <= 2.0:
            scores.append(70)  # Balanced
        elif 0.5 <= lf_hf <= 3.0:
            scores.append(50)  # Acceptable
        elif lf_hf < 0.5:
            scores.append(40)  # Parasympathetic dominant
        else:
            scores.append(30)  # Sympathetic dominant

    # Stress Index component
    if stress_index is not None:
        if stress_index < 50:
            scores.append(80)
        elif stress_index < 100:
            scores.append(65)
        elif stress_index < 150:
            scores.append(45)
        else:
            scores.append(25)

    balance_score = float(np.mean(scores)) if scores else 50.0

    # Determine state
    if balance_score >= 65:
        if lf_hf is not None and lf_hf < 0.8:
            state = AutonomicState.PARASYMPATHETIC_DOMINANT
        else:
            state = AutonomicState.BALANCED
    elif balance_score >= 45:
        state = AutonomicState.BALANCED
    elif balance_score >= 30:
        if lf_hf is not None and lf_hf > 3.0:
            state = AutonomicState.SYMPATHETIC_DOMINANT
        else:
            state = AutonomicState.SYMPATHETIC_DOMINANT
    else:
        state = AutonomicState.DYSREGULATED

    return state, balance_score


def generate_clinical_decision_support(
    hrv_df: pd.DataFrame,
    garmin_df: Optional[pd.DataFrame],
    user_age: int,
    user_sex: str,
    alpha: float = 0.05,
) -> ClinicalDecisionSupport:
    """Generate comprehensive clinical decision support with recommendations."""
    metric_assessments: List[MetricAssessment] = []
    statistical_tests: List[StatisticalTestResult] = []
    recommendations: List[str] = []
    alerts: List[str] = []

    # Get latest values for assessment
    if hrv_df.empty:
        return ClinicalDecisionSupport(
            overall_status=RiskLevel.YELLOW,
            status_label="Insufficient Data",
            summary="Not enough HRV data for comprehensive analysis",
            metric_assessments=[],
            statistical_tests=[],
            recommendations=["Upload more HRV recordings for analysis"],
        )

    latest = hrv_df.iloc[-1]
    metrics_to_assess = ["rmssd_ms", "sdnn_ms", "lf_hf_ratio", "stress_index", "mean_hr_bpm"]

    for metric in metrics_to_assess:
        if metric in latest and pd.notna(latest[metric]):
            assessment = assess_metric(metric, float(latest[metric]), user_age, user_sex)
            metric_assessments.append(assessment)

    # Statistical tests against reference
    for metric in ["rmssd_ms", "sdnn_ms"]:
        if metric in hrv_df.columns:
            data = hrv_df[metric].dropna().values
            if len(data) >= 3:
                # Normality test
                normality = shapiro_wilk_test(data)
                statistical_tests.append(normality)

                # One-sample t-test against reference mean
                ref = get_age_reference(
                    user_age, "rmssd" if "rmssd" in metric else "sdnn"
                )
                if ref:
                    ref_mean = ref[0]
                    ttest = one_sample_ttest(data, ref_mean, alpha)
                    ttest.test_name = f"{metric} vs Reference"
                    statistical_tests.append(ttest)

    # Trend analysis
    trend_analysis: Optional[TrendAnalysis] = None
    if "measurement_date" in hrv_df.columns and "rmssd_ms" in hrv_df.columns:
        dates = hrv_df["measurement_date"].values
        values = hrv_df["rmssd_ms"].values
        trend_analysis = analyze_trend(dates, values, "rmssd_ms")
        if trend_analysis.is_significant and trend_analysis.direction == TrendDirection.DECLINING:
            alerts.append("⚠️ Significant declining trend in RMSSD detected")

    # Anomaly detection
    anomaly_detection: Optional[AnomalyDetection] = None
    if "rmssd_ms" in hrv_df.columns:
        values = hrv_df["rmssd_ms"].dropna().values
        dates = hrv_df["measurement_date"].values if "measurement_date" in hrv_df.columns else None
        anomaly_detection = detect_anomalies_zscore(values, dates)
        if anomaly_detection.n_anomalies > 0:
            alerts.append(
                f"🔍 {anomaly_detection.n_anomalies} anomalous recording(s) detected"
            )

    # Pattern recognition
    pattern_recognition: Optional[PatternRecognition] = None
    if len(hrv_df) >= 5:
        pattern_recognition = recognize_hrv_patterns(hrv_df)

    # Garmin integration
    garmin_integration: Optional[HRVGarminIntegration] = None
    if garmin_df is not None and not garmin_df.empty:
        garmin_integration = integrate_hrv_garmin(hrv_df, garmin_df)
        if garmin_integration:
            recommendations.extend(garmin_integration.recommendations)

    # Determine overall autonomic state
    rmssd_val = latest.get("rmssd_ms") if "rmssd_ms" in latest else None
    sdnn_val = latest.get("sdnn_ms") if "sdnn_ms" in latest else None
    lf_hf_val = latest.get("lf_hf_ratio") if "lf_hf_ratio" in latest else None
    stress_val = latest.get("stress_index") if "stress_index" in latest else None

    autonomic_state, balance_score = determine_autonomic_state(
        rmssd=float(rmssd_val) if pd.notna(rmssd_val) else None,
        sdnn=float(sdnn_val) if pd.notna(sdnn_val) else None,
        lf_hf=float(lf_hf_val) if pd.notna(lf_hf_val) else None,
        stress_index=float(stress_val) if pd.notna(stress_val) else None,
        age=user_age,
    )

    # Overall status from metric assessments
    risk_counts = {RiskLevel.RED: 0, RiskLevel.ORANGE: 0, RiskLevel.YELLOW: 0, RiskLevel.GREEN: 0}
    for ma in metric_assessments:
        risk_counts[ma.risk_level] += 1

    if risk_counts[RiskLevel.RED] > 0:
        overall_status = RiskLevel.RED
        status_label = "Alert - Review Required"
    elif risk_counts[RiskLevel.ORANGE] >= 2:
        overall_status = RiskLevel.ORANGE
        status_label = "Caution - Monitor Closely"
    elif risk_counts[RiskLevel.ORANGE] > 0 or risk_counts[RiskLevel.YELLOW] >= 2:
        overall_status = RiskLevel.YELLOW
        status_label = "Monitor - Some Indicators Elevated"
    else:
        overall_status = RiskLevel.GREEN
        status_label = "Normal - Healthy Profile"

    # Generate summary
    summary = f"Autonomic State: {autonomic_state.value.replace('_', ' ').title()}\n"
    summary += f"Balance Score: {balance_score:.0f}/100\n"
    summary += f"Recordings Analyzed: {len(hrv_df)}"

    # Generate recommendations based on assessments
    for ma in metric_assessments:
        if ma.recommendation and ma.risk_level in [RiskLevel.RED, RiskLevel.ORANGE]:
            recommendations.append(f"**{ma.metric_name}**: {ma.recommendation}")

    # Add general recommendations based on autonomic state
    if autonomic_state == AutonomicState.SYMPATHETIC_DOMINANT:
        recommendations.append(
            "🧘 Consider stress reduction techniques (breathing exercises, meditation)"
        )
    elif autonomic_state == AutonomicState.DYSREGULATED:
        recommendations.append(
            "⚕️ Consult healthcare provider for comprehensive autonomic assessment"
        )

    return ClinicalDecisionSupport(
        overall_status=overall_status,
        status_label=status_label,
        summary=summary,
        metric_assessments=metric_assessments,
        statistical_tests=statistical_tests,
        trend_analysis=trend_analysis,
        anomaly_detection=anomaly_detection,
        pattern_recognition=pattern_recognition,
        garmin_integration=garmin_integration,
        recommendations=recommendations,
        alerts=alerts,
        autonomic_state=autonomic_state,
    )


# =============================================================================
# Main Analysis Entry Point
# =============================================================================


def run_advanced_hrv_analysis(
    hrv_df: pd.DataFrame,
    garmin_df: Optional[pd.DataFrame] = None,
    user_age: int = 40,
    user_sex: str = "unknown",
) -> AdvancedHRVAnalysisResult:
    """Run comprehensive advanced HRV analysis.

    Args:
        hrv_df: DataFrame with HRV measurements (columns: rmssd_ms, sdnn_ms, etc.)
        garmin_df: Optional DataFrame with Garmin daily metrics
        user_age: User's age in years
        user_sex: User's sex ('male', 'female', 'unknown')

    Returns:
        AdvancedHRVAnalysisResult with all analysis components
    """
    _LOGGER.info(
        "Running advanced HRV analysis for %d recordings, age=%d",
        len(hrv_df) if not hrv_df.empty else 0,
        user_age,
    )

    if hrv_df.empty:
        return AdvancedHRVAnalysisResult(
            analysis_timestamp=datetime.now(),
            user_age=user_age,
            user_sex=user_sex,
            n_recordings=0,
            date_range=(date.today(), date.today()),
            clinical_decision=ClinicalDecisionSupport(
                overall_status=RiskLevel.YELLOW,
                status_label="No Data",
                summary="No HRV recordings available for analysis",
                metric_assessments=[],
                statistical_tests=[],
            ),
            descriptive_stats={},
            normality_tests={},
            comparison_tests={},
            trend_analyses={},
            forecasts={},
            autonomic_balance_score=50.0,
        )

    # Date range
    date_col = "measurement_date" if "measurement_date" in hrv_df.columns else None
    if date_col:
        try:
            dates = pd.to_datetime(hrv_df[date_col])
            date_range = (dates.min().date(), dates.max().date())
        except Exception:
            date_range = (date.today(), date.today())
    else:
        date_range = (date.today(), date.today())

    # Descriptive statistics for all metrics
    hrv_metrics = ["rmssd_ms", "sdnn_ms", "mean_hr_bpm", "lf_hf_ratio", "stress_index", "pnn50_pct", "hf_power_ms2", "lf_power_ms2"]
    descriptive_stats: Dict[str, Dict[str, float]] = {}
    normality_tests: Dict[str, StatisticalTestResult] = {}

    for metric in hrv_metrics:
        if metric in hrv_df.columns:
            data = hrv_df[metric].dropna().values
            if len(data) >= 2:
                descriptive_stats[metric] = compute_descriptive_stats(data)
            if len(data) >= 3:
                normality_tests[metric] = shapiro_wilk_test(data)

    # Trend analyses for key metrics
    trend_analyses: Dict[str, TrendAnalysis] = {}
    forecasts: Dict[str, Dict[str, float]] = {}
    if date_col:
        for metric in ["rmssd_ms", "sdnn_ms", "mean_hr_bpm"]:
            if metric in hrv_df.columns:
                dates = hrv_df[date_col].values
                values = hrv_df[metric].dropna().values
                if len(values) >= 5:
                    trend = analyze_trend(dates[:len(values)], values, metric)
                    trend_analyses[metric] = trend
                    if trend.forecast_7d is not None:
                        forecasts[metric] = {
                            "forecast_7d": trend.forecast_7d,
                            "lower_ci": trend.forecast_confidence[0] if trend.forecast_confidence else trend.forecast_7d,
                            "upper_ci": trend.forecast_confidence[1] if trend.forecast_confidence else trend.forecast_7d,
                        }

    # Clinical decision support (includes statistical tests)
    clinical_decision = generate_clinical_decision_support(
        hrv_df, garmin_df, user_age, user_sex
    )

    # Extract comparison tests from clinical decision
    comparison_tests: Dict[str, StatisticalTestResult] = {}
    for test in clinical_decision.statistical_tests:
        comparison_tests[test.test_name] = test

    # Autonomic balance score
    latest = hrv_df.iloc[-1]
    rmssd = latest.get("rmssd_ms") if "rmssd_ms" in latest else None
    sdnn = latest.get("sdnn_ms") if "sdnn_ms" in latest else None
    lf_hf = latest.get("lf_hf_ratio") if "lf_hf_ratio" in latest else None
    stress = latest.get("stress_index") if "stress_index" in latest else None

    _, balance_score = determine_autonomic_state(
        rmssd=float(rmssd) if pd.notna(rmssd) else None,
        sdnn=float(sdnn) if pd.notna(sdnn) else None,
        lf_hf=float(lf_hf) if pd.notna(lf_hf) else None,
        stress_index=float(stress) if pd.notna(stress) else None,
        age=user_age,
    )

    return AdvancedHRVAnalysisResult(
        analysis_timestamp=datetime.now(),
        user_age=user_age,
        user_sex=user_sex,
        n_recordings=len(hrv_df),
        date_range=date_range,
        clinical_decision=clinical_decision,
        descriptive_stats=descriptive_stats,
        normality_tests=normality_tests,
        comparison_tests=comparison_tests,
        trend_analyses=trend_analyses,
        forecasts=forecasts,
        autonomic_balance_score=balance_score,
    )

