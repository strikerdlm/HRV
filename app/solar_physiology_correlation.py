"""Solar-Physiology Correlation Analysis Module.

This module provides comprehensive analysis of correlations between:
- Solar activity (Kp index, Dst, solar wind, X-ray flux, etc.)
- Physiological variables (HRV, sleep, activity, ANS balance)

Features:
- Time-aligned correlation analysis
- Lag analysis (solar activity effects may be delayed)
- ML-based pattern detection
- Significant result highlighting
- Publication-ready visualizations

Scientific background:
- Geomagnetic activity affects ANS balance (Otsuka et al., 2001)
- Solar activity correlates with cardiovascular events (Stoupel et al., 2008)
- Kp index associated with HRV changes (Alabdulgader et al., 2018)

References:
- Alabdulgader, A. et al. (2018). Human Heart Rhythm Sensitivity to Earth Local
  Magnetic Field Fluctuations. J Vibroeng.
- Stoupel, E. et al. (2008). Space proton flux and the temporal distribution of
  cardiovascular deaths. Int J Biometeorol.
- Otsuka, K. et al. (2001). Geomagnetic disturbance associated with decrease in
  heart rate variability in a subarctic area. Biomed Pharmacother.
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
from scipy.signal import correlate

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
_MIN_SAMPLES_CORRELATION: Final[int] = 10
_MAX_LAG_DAYS: Final[int] = 7
_SIGNIFICANCE_LEVEL: Final[float] = 0.05


class SignificanceLevel(str, Enum):
    """Significance level for highlighting."""

    NOT_SIGNIFICANT = "not_significant"
    MARGINAL = "marginal"  # p < 0.10
    SIGNIFICANT = "significant"  # p < 0.05
    HIGHLY_SIGNIFICANT = "highly_significant"  # p < 0.01
    VERY_HIGHLY_SIGNIFICANT = "very_highly_significant"  # p < 0.001


class CorrelationStrength(str, Enum):
    """Correlation strength classification."""

    NEGLIGIBLE = "negligible"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SolarMetric:
    """Solar activity metric definition.

    Attributes:
        key: Unique identifier.
        name: Human-readable name.
        unit: Measurement unit.
        description: Brief description.
        higher_is_more_active: Whether higher values indicate more activity.
    """

    key: str
    name: str
    unit: str
    description: str
    higher_is_more_active: bool = True


@dataclass(frozen=True, slots=True)
class PhysiologicalMetric:
    """Physiological metric definition.

    Attributes:
        key: Unique identifier.
        name: Human-readable name.
        unit: Measurement unit.
        category: Category (hrv, sleep, activity, ans).
        higher_is_better: Whether higher values indicate better health.
    """

    key: str
    name: str
    unit: str
    category: str
    higher_is_better: bool = True


@dataclass(frozen=True, slots=True)
class CorrelationResult:
    """Result of correlation analysis.

    Attributes:
        solar_metric: Solar metric key.
        physio_metric: Physiological metric key.
        lag_days: Lag in days (positive = solar leads).
        r: Correlation coefficient.
        p_value: P-value.
        n: Sample size.
        r_squared: R-squared.
        ci_low: Lower 95% CI.
        ci_high: Upper 95% CI.
        significance: Significance level.
        strength: Correlation strength.
        interpretation: Human-readable interpretation.
    """

    solar_metric: str
    physio_metric: str
    lag_days: int
    r: float
    p_value: float
    n: int
    r_squared: float
    ci_low: float
    ci_high: float
    significance: SignificanceLevel
    strength: CorrelationStrength
    interpretation: str


@dataclass(frozen=True, slots=True)
class LagAnalysisResult:
    """Result of lag analysis.

    Attributes:
        solar_metric: Solar metric key.
        physio_metric: Physiological metric key.
        optimal_lag: Lag with strongest correlation.
        correlations_by_lag: Dict of lag -> correlation.
        p_values_by_lag: Dict of lag -> p-value.
        best_r: Best correlation coefficient.
        best_p: P-value at optimal lag.
        interpretation: Human-readable interpretation.
    """

    solar_metric: str
    physio_metric: str
    optimal_lag: int
    correlations_by_lag: dict[int, float]
    p_values_by_lag: dict[int, float]
    best_r: float
    best_p: float
    interpretation: str


@dataclass(slots=True)
class ComprehensiveCorrelationReport:
    """Comprehensive correlation report.

    Attributes:
        analysis_date: Date of analysis.
        data_start: Start of data period.
        data_end: End of data period.
        n_days: Number of days analyzed.
        significant_correlations: List of significant correlations.
        all_correlations: All correlation results.
        lag_analyses: Lag analysis results.
        pattern_insights: ML-detected patterns.
        summary_statistics: Summary statistics.
        recommendations: Health recommendations.
    """

    analysis_date: datetime
    data_start: date
    data_end: date
    n_days: int
    significant_correlations: list[CorrelationResult] = field(default_factory=list)
    all_correlations: list[CorrelationResult] = field(default_factory=list)
    lag_analyses: list[LagAnalysisResult] = field(default_factory=list)
    pattern_insights: list[str] = field(default_factory=list)
    summary_statistics: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

SOLAR_METRICS: dict[str, SolarMetric] = {
    "kp_index": SolarMetric(
        key="kp_index",
        name="Planetary Kp Index",
        unit="Kp",
        description="Global geomagnetic activity index (0-9)",
        higher_is_more_active=True,
    ),
    "dst": SolarMetric(
        key="dst",
        name="Dst Index",
        unit="nT",
        description="Disturbance storm-time index (negative = storm)",
        higher_is_more_active=False,  # More negative = more active
    ),
    "proton_speed": SolarMetric(
        key="proton_speed",
        name="Solar Wind Speed",
        unit="km/s",
        description="Solar wind proton speed",
        higher_is_more_active=True,
    ),
    "proton_density": SolarMetric(
        key="proton_density",
        name="Solar Wind Density",
        unit="1/cm³",
        description="Solar wind proton density",
        higher_is_more_active=True,
    ),
    "bt": SolarMetric(
        key="bt",
        name="IMF Total Field (Bt)",
        unit="nT",
        description="Interplanetary magnetic field total magnitude",
        higher_is_more_active=True,
    ),
    "bz_gsm": SolarMetric(
        key="bz_gsm",
        name="IMF Bz (GSM)",
        unit="nT",
        description="IMF north-south component (negative = geoeffective)",
        higher_is_more_active=False,
    ),
    "f107_flux": SolarMetric(
        key="f107_flux",
        name="F10.7 Solar Radio Flux",
        unit="sfu",
        description="10.7 cm solar radio flux",
        higher_is_more_active=True,
    ),
    "xray_flux": SolarMetric(
        key="xray_flux",
        name="X-ray Flux",
        unit="W/m²",
        description="Solar X-ray flux",
        higher_is_more_active=True,
    ),
}

PHYSIO_METRICS: dict[str, PhysiologicalMetric] = {
    # HRV metrics
    "rmssd": PhysiologicalMetric(
        key="rmssd",
        name="RMSSD",
        unit="ms",
        category="hrv",
        higher_is_better=True,
    ),
    "sdnn": PhysiologicalMetric(
        key="sdnn",
        name="SDNN",
        unit="ms",
        category="hrv",
        higher_is_better=True,
    ),
    "mean_hr": PhysiologicalMetric(
        key="mean_hr",
        name="Mean Heart Rate",
        unit="bpm",
        category="hrv",
        higher_is_better=False,
    ),
    "lf_hf_ratio": PhysiologicalMetric(
        key="lf_hf_ratio",
        name="LF/HF Ratio",
        unit="ratio",
        category="ans",
        higher_is_better=False,
    ),
    "hf_power": PhysiologicalMetric(
        key="hf_power",
        name="HF Power",
        unit="ms²",
        category="ans",
        higher_is_better=True,
    ),
    "lf_power": PhysiologicalMetric(
        key="lf_power",
        name="LF Power",
        unit="ms²",
        category="ans",
        higher_is_better=True,
    ),
    # Sleep metrics
    "tst_minutes": PhysiologicalMetric(
        key="tst_minutes",
        name="Total Sleep Time",
        unit="min",
        category="sleep",
        higher_is_better=True,
    ),
    "sleep_efficiency": PhysiologicalMetric(
        key="sleep_efficiency",
        name="Sleep Efficiency",
        unit="%",
        category="sleep",
        higher_is_better=True,
    ),
    "deep_sleep_pct": PhysiologicalMetric(
        key="deep_sleep_pct",
        name="Deep Sleep %",
        unit="%",
        category="sleep",
        higher_is_better=True,
    ),
    # Activity metrics
    "resting_hr": PhysiologicalMetric(
        key="resting_hr",
        name="Resting Heart Rate",
        unit="bpm",
        category="activity",
        higher_is_better=False,
    ),
    "stress_score": PhysiologicalMetric(
        key="stress_score",
        name="Stress Score",
        unit="score",
        category="activity",
        higher_is_better=False,
    ),
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _classify_significance(p_value: float) -> SignificanceLevel:
    """Classify p-value into significance level."""
    if p_value < 0.001:
        return SignificanceLevel.VERY_HIGHLY_SIGNIFICANT
    if p_value < 0.01:
        return SignificanceLevel.HIGHLY_SIGNIFICANT
    if p_value < 0.05:
        return SignificanceLevel.SIGNIFICANT
    if p_value < 0.10:
        return SignificanceLevel.MARGINAL
    return SignificanceLevel.NOT_SIGNIFICANT


def _classify_strength(r: float) -> CorrelationStrength:
    """Classify correlation coefficient strength."""
    abs_r = abs(r)
    if abs_r < 0.1:
        return CorrelationStrength.NEGLIGIBLE
    if abs_r < 0.3:
        return CorrelationStrength.WEAK
    if abs_r < 0.5:
        return CorrelationStrength.MODERATE
    if abs_r < 0.7:
        return CorrelationStrength.STRONG
    return CorrelationStrength.VERY_STRONG


def _compute_correlation_ci(r: float, n: int) -> tuple[float, float]:
    """Compute 95% CI for correlation using Fisher's z."""
    if n <= 3 or abs(r) >= 0.9999:
        return r, r

    z = 0.5 * np.log((1 + r) / (1 - r))
    se_z = 1 / np.sqrt(n - 3)
    z_low = z - 1.96 * se_z
    z_high = z + 1.96 * se_z

    ci_low = (np.exp(2 * z_low) - 1) / (np.exp(2 * z_low) + 1)
    ci_high = (np.exp(2 * z_high) - 1) / (np.exp(2 * z_high) + 1)

    return float(ci_low), float(ci_high)


# ---------------------------------------------------------------------------
# Main correlation analyzer
# ---------------------------------------------------------------------------


class SolarPhysiologyAnalyzer:
    """Analyzer for solar-physiology correlations."""

    def __init__(
        self,
        solar_data: pd.DataFrame,
        physio_data: pd.DataFrame,
    ) -> None:
        """Initialize analyzer.

        Args:
            solar_data: DataFrame with solar metrics indexed by datetime.
            physio_data: DataFrame with physiological metrics indexed by date.
        """
        self._solar_data = solar_data.copy()
        self._physio_data = physio_data.copy()
        self._aligned_data: pd.DataFrame | None = None

    def _align_data(self) -> pd.DataFrame:
        """Align solar and physiological data by date."""
        if self._aligned_data is not None:
            return self._aligned_data

        # Ensure datetime index for solar data
        if not isinstance(self._solar_data.index, pd.DatetimeIndex):
            self._solar_data.index = pd.to_datetime(self._solar_data.index)

        # Resample solar data to daily (mean)
        solar_daily = self._solar_data.resample("D").mean()

        # Ensure date index for physio data
        if not isinstance(self._physio_data.index, pd.DatetimeIndex):
            self._physio_data.index = pd.to_datetime(self._physio_data.index)

        # Align on date
        aligned = solar_daily.join(self._physio_data, how="inner", rsuffix="_physio")
        self._aligned_data = aligned

        return aligned

    def compute_correlation(
        self,
        solar_metric: str,
        physio_metric: str,
        lag_days: int = 0,
    ) -> CorrelationResult:
        """Compute correlation between solar and physiological metric.

        Args:
            solar_metric: Solar metric column name.
            physio_metric: Physiological metric column name.
            lag_days: Lag in days (positive = solar leads).

        Returns:
            CorrelationResult with statistics.
        """
        aligned = self._align_data()

        if solar_metric not in aligned.columns or physio_metric not in aligned.columns:
            return CorrelationResult(
                solar_metric=solar_metric,
                physio_metric=physio_metric,
                lag_days=lag_days,
                r=0.0,
                p_value=1.0,
                n=0,
                r_squared=0.0,
                ci_low=0.0,
                ci_high=0.0,
                significance=SignificanceLevel.NOT_SIGNIFICANT,
                strength=CorrelationStrength.NEGLIGIBLE,
                interpretation="Data not available.",
            )

        # Apply lag
        if lag_days != 0:
            solar_values = aligned[solar_metric].shift(lag_days)
        else:
            solar_values = aligned[solar_metric]

        physio_values = aligned[physio_metric]

        # Clean data
        mask = solar_values.notna() & physio_values.notna()
        x = solar_values[mask].values
        y = physio_values[mask].values
        n = len(x)

        if n < _MIN_SAMPLES_CORRELATION:
            return CorrelationResult(
                solar_metric=solar_metric,
                physio_metric=physio_metric,
                lag_days=lag_days,
                r=0.0,
                p_value=1.0,
                n=n,
                r_squared=0.0,
                ci_low=0.0,
                ci_high=0.0,
                significance=SignificanceLevel.NOT_SIGNIFICANT,
                strength=CorrelationStrength.NEGLIGIBLE,
                interpretation=f"Insufficient data (n={n}, need {_MIN_SAMPLES_CORRELATION}).",
            )

        # Compute Spearman correlation (robust to non-normality)
        r, p_value = stats.spearmanr(x, y)
        r = float(r)
        p_value = float(p_value)

        # Confidence interval
        ci_low, ci_high = _compute_correlation_ci(r, n)

        # Classifications
        significance = _classify_significance(p_value)
        strength = _classify_strength(r)

        # Interpretation
        solar_name = SOLAR_METRICS.get(solar_metric, SolarMetric(solar_metric, solar_metric, "", "", True)).name
        physio_name = PHYSIO_METRICS.get(physio_metric, PhysiologicalMetric(physio_metric, physio_metric, "", "", True)).name

        direction = "positive" if r > 0 else "negative"
        lag_text = f" with {lag_days}-day lag" if lag_days != 0 else ""

        if significance in (SignificanceLevel.SIGNIFICANT, SignificanceLevel.HIGHLY_SIGNIFICANT, SignificanceLevel.VERY_HIGHLY_SIGNIFICANT):
            interpretation = (
                f"Significant {strength.value} {direction} correlation "
                f"between {solar_name} and {physio_name}{lag_text} "
                f"(r={r:.3f}, p={p_value:.4f})."
            )
        else:
            interpretation = (
                f"No significant correlation between {solar_name} and "
                f"{physio_name}{lag_text} (r={r:.3f}, p={p_value:.4f})."
            )

        return CorrelationResult(
            solar_metric=solar_metric,
            physio_metric=physio_metric,
            lag_days=lag_days,
            r=r,
            p_value=p_value,
            n=n,
            r_squared=r**2,
            ci_low=ci_low,
            ci_high=ci_high,
            significance=significance,
            strength=strength,
            interpretation=interpretation,
        )

    def analyze_lag(
        self,
        solar_metric: str,
        physio_metric: str,
        max_lag: int = _MAX_LAG_DAYS,
    ) -> LagAnalysisResult:
        """Analyze correlation at different lags.

        Args:
            solar_metric: Solar metric column name.
            physio_metric: Physiological metric column name.
            max_lag: Maximum lag to test (days).

        Returns:
            LagAnalysisResult with optimal lag.
        """
        correlations_by_lag: dict[int, float] = {}
        p_values_by_lag: dict[int, float] = {}

        best_abs_r = 0.0
        optimal_lag = 0
        best_r = 0.0
        best_p = 1.0

        for lag in range(-max_lag, max_lag + 1):
            result = self.compute_correlation(solar_metric, physio_metric, lag_days=lag)
            correlations_by_lag[lag] = result.r
            p_values_by_lag[lag] = result.p_value

            if abs(result.r) > best_abs_r and result.p_value < 0.10:
                best_abs_r = abs(result.r)
                optimal_lag = lag
                best_r = result.r
                best_p = result.p_value

        # Interpretation
        solar_name = SOLAR_METRICS.get(solar_metric, SolarMetric(solar_metric, solar_metric, "", "", True)).name
        physio_name = PHYSIO_METRICS.get(physio_metric, PhysiologicalMetric(physio_metric, physio_metric, "", "", True)).name

        if best_p < 0.05:
            if optimal_lag > 0:
                interpretation = (
                    f"{solar_name} leads {physio_name} by {optimal_lag} day(s) "
                    f"with r={best_r:.3f} (p={best_p:.4f})."
                )
            elif optimal_lag < 0:
                interpretation = (
                    f"{physio_name} leads {solar_name} by {abs(optimal_lag)} day(s) "
                    f"with r={best_r:.3f} (p={best_p:.4f})."
                )
            else:
                interpretation = (
                    f"Same-day correlation between {solar_name} and {physio_name} "
                    f"with r={best_r:.3f} (p={best_p:.4f})."
                )
        else:
            interpretation = (
                f"No significant lag relationship between {solar_name} and {physio_name}."
            )

        return LagAnalysisResult(
            solar_metric=solar_metric,
            physio_metric=physio_metric,
            optimal_lag=optimal_lag,
            correlations_by_lag=correlations_by_lag,
            p_values_by_lag=p_values_by_lag,
            best_r=best_r,
            best_p=best_p,
            interpretation=interpretation,
        )

    def compute_all_correlations(
        self,
        solar_metrics: list[str] | None = None,
        physio_metrics: list[str] | None = None,
        include_lags: bool = True,
    ) -> ComprehensiveCorrelationReport:
        """Compute all correlations between solar and physio metrics.

        Args:
            solar_metrics: List of solar metrics (None = all available).
            physio_metrics: List of physio metrics (None = all available).
            include_lags: Whether to include lag analysis.

        Returns:
            ComprehensiveCorrelationReport with all results.
        """
        aligned = self._align_data()

        # Determine available metrics
        if solar_metrics is None:
            solar_metrics = [c for c in aligned.columns if c in SOLAR_METRICS]
        if physio_metrics is None:
            physio_metrics = [c for c in aligned.columns if c in PHYSIO_METRICS or c.endswith("_physio")]

        all_correlations: list[CorrelationResult] = []
        significant_correlations: list[CorrelationResult] = []
        lag_analyses: list[LagAnalysisResult] = []

        # Compute correlations
        for solar_m in solar_metrics:
            for physio_m in physio_metrics:
                # Same-day correlation
                result = self.compute_correlation(solar_m, physio_m, lag_days=0)
                all_correlations.append(result)

                if result.significance in (
                    SignificanceLevel.SIGNIFICANT,
                    SignificanceLevel.HIGHLY_SIGNIFICANT,
                    SignificanceLevel.VERY_HIGHLY_SIGNIFICANT,
                ):
                    significant_correlations.append(result)

                # Lag analysis
                if include_lags:
                    lag_result = self.analyze_lag(solar_m, physio_m)
                    lag_analyses.append(lag_result)

                    # Check if lagged correlation is significant
                    if lag_result.best_p < 0.05 and lag_result.optimal_lag != 0:
                        lagged_corr = self.compute_correlation(
                            solar_m, physio_m, lag_days=lag_result.optimal_lag
                        )
                        if lagged_corr not in significant_correlations:
                            significant_correlations.append(lagged_corr)

        # Sort significant correlations by effect size
        significant_correlations.sort(key=lambda x: abs(x.r), reverse=True)

        # Generate pattern insights
        pattern_insights = self._generate_pattern_insights(significant_correlations)

        # Generate recommendations
        recommendations = self._generate_recommendations(significant_correlations)

        # Summary statistics
        summary_statistics = {
            "total_correlations_tested": len(all_correlations),
            "significant_correlations": len(significant_correlations),
            "significance_rate": len(significant_correlations) / max(len(all_correlations), 1),
            "strongest_correlation": max((abs(c.r) for c in all_correlations), default=0),
        }

        # Date range
        if not aligned.empty:
            data_start = aligned.index.min().date()
            data_end = aligned.index.max().date()
            n_days = len(aligned)
        else:
            data_start = date.today()
            data_end = date.today()
            n_days = 0

        return ComprehensiveCorrelationReport(
            analysis_date=datetime.now(),
            data_start=data_start,
            data_end=data_end,
            n_days=n_days,
            significant_correlations=significant_correlations,
            all_correlations=all_correlations,
            lag_analyses=lag_analyses,
            pattern_insights=pattern_insights,
            summary_statistics=summary_statistics,
            recommendations=recommendations,
        )

    def _generate_pattern_insights(
        self,
        significant_correlations: list[CorrelationResult],
    ) -> list[str]:
        """Generate insights from significant correlations."""
        insights: list[str] = []

        # Group by solar metric
        solar_effects: dict[str, list[CorrelationResult]] = {}
        for corr in significant_correlations:
            if corr.solar_metric not in solar_effects:
                solar_effects[corr.solar_metric] = []
            solar_effects[corr.solar_metric].append(corr)

        # Analyze patterns
        for solar_m, correlations in solar_effects.items():
            solar_name = SOLAR_METRICS.get(solar_m, SolarMetric(solar_m, solar_m, "", "", True)).name
            n_effects = len(correlations)

            if n_effects >= 3:
                insights.append(
                    f"🔬 {solar_name} shows broad physiological influence "
                    f"({n_effects} significant correlations)."
                )

            # Check for ANS effects
            ans_effects = [c for c in correlations if PHYSIO_METRICS.get(c.physio_metric, PhysiologicalMetric("", "", "", "other", True)).category == "ans"]
            if len(ans_effects) >= 2:
                insights.append(
                    f"⚡ {solar_name} significantly affects autonomic nervous system balance."
                )

            # Check for sleep effects
            sleep_effects = [c for c in correlations if PHYSIO_METRICS.get(c.physio_metric, PhysiologicalMetric("", "", "", "other", True)).category == "sleep"]
            if sleep_effects:
                insights.append(
                    f"😴 {solar_name} correlates with sleep quality metrics."
                )

        # Overall pattern
        if len(significant_correlations) > 5:
            insights.append(
                "📊 Strong evidence of solar-physiology coupling in this dataset."
            )
        elif len(significant_correlations) > 0:
            insights.append(
                "📊 Some evidence of solar-physiology relationships detected."
            )
        else:
            insights.append(
                "📊 No significant solar-physiology correlations detected in this period."
            )

        return insights

    def _generate_recommendations(
        self,
        significant_correlations: list[CorrelationResult],
    ) -> list[str]:
        """Generate health recommendations based on correlations."""
        recommendations: list[str] = []

        # Check for Kp effects on HRV
        kp_hrv = [c for c in significant_correlations if c.solar_metric == "kp_index" and c.physio_metric in ("rmssd", "sdnn")]
        if kp_hrv:
            recommendations.append(
                "🌍 Your HRV appears sensitive to geomagnetic activity. "
                "Consider monitoring space weather forecasts during periods of high Kp."
            )

        # Check for sleep effects
        sleep_correlations = [c for c in significant_correlations if "sleep" in c.physio_metric or "tst" in c.physio_metric]
        if sleep_correlations:
            recommendations.append(
                "😴 Solar activity correlates with your sleep patterns. "
                "Prioritize sleep hygiene during geomagnetic storms."
            )

        # Check for stress effects
        stress_correlations = [c for c in significant_correlations if "stress" in c.physio_metric]
        if stress_correlations:
            recommendations.append(
                "🧘 Consider additional stress management during high solar activity periods."
            )

        # General recommendation
        if len(significant_correlations) > 3:
            recommendations.append(
                "📱 Your physiology shows notable sensitivity to space weather. "
                "Consider using space weather apps for advance notice of geomagnetic storms."
            )

        return recommendations

    def get_correlation_matrix(
        self,
        solar_metrics: list[str] | None = None,
        physio_metrics: list[str] | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Get correlation and p-value matrices.

        Args:
            solar_metrics: List of solar metrics.
            physio_metrics: List of physio metrics.

        Returns:
            Tuple of (correlation matrix, p-value matrix).
        """
        aligned = self._align_data()

        if solar_metrics is None:
            solar_metrics = [c for c in aligned.columns if c in SOLAR_METRICS]
        if physio_metrics is None:
            physio_metrics = [c for c in aligned.columns if c in PHYSIO_METRICS]

        corr_matrix = pd.DataFrame(
            index=solar_metrics,
            columns=physio_metrics,
            dtype=float,
        )
        p_matrix = pd.DataFrame(
            index=solar_metrics,
            columns=physio_metrics,
            dtype=float,
        )

        for solar_m in solar_metrics:
            for physio_m in physio_metrics:
                result = self.compute_correlation(solar_m, physio_m)
                corr_matrix.loc[solar_m, physio_m] = result.r
                p_matrix.loc[solar_m, physio_m] = result.p_value

        return corr_matrix, p_matrix


# ---------------------------------------------------------------------------
# ECharts visualization builders
# ---------------------------------------------------------------------------


def build_correlation_heatmap_chart(
    corr_matrix: pd.DataFrame,
    p_matrix: pd.DataFrame,
    title: str = "Solar-Physiology Correlations",
) -> dict[str, Any]:
    """Build ECharts heatmap for correlation matrix.

    Args:
        corr_matrix: Correlation matrix.
        p_matrix: P-value matrix.
        title: Chart title.

    Returns:
        ECharts option dict.
    """
    solar_labels = list(corr_matrix.index)
    physio_labels = list(corr_matrix.columns)

    # Prepare data
    data: list[list[Any]] = []
    for i, solar_m in enumerate(solar_labels):
        for j, physio_m in enumerate(physio_labels):
            r = corr_matrix.loc[solar_m, physio_m]
            p = p_matrix.loc[solar_m, physio_m]
            data.append([i, j, float(r), float(p)])

    # Get display names
    solar_display = [SOLAR_METRICS.get(m, SolarMetric(m, m, "", "", True)).name for m in solar_labels]
    physio_display = [PHYSIO_METRICS.get(m, PhysiologicalMetric(m, m, "", "", True)).name for m in physio_labels]

    return {
        "title": {
            "text": title,
            "left": "center",
            "textStyle": {"fontSize": 16, "fontWeight": "bold"},
        },
        "tooltip": {
            "position": "top",
            "formatter": """function(params) {
                var r = params.data[2].toFixed(3);
                var p = params.data[3].toFixed(4);
                var sig = p < 0.05 ? ' ★' : '';
                return params.name + '<br/>r = ' + r + '<br/>p = ' + p + sig;
            }""",
        },
        "grid": {
            "left": "15%",
            "right": "10%",
            "top": "15%",
            "bottom": "20%",
        },
        "xAxis": {
            "type": "category",
            "data": physio_display,
            "axisLabel": {"rotate": 45, "fontSize": 10},
            "splitArea": {"show": True},
        },
        "yAxis": {
            "type": "category",
            "data": solar_display,
            "axisLabel": {"fontSize": 10},
            "splitArea": {"show": True},
        },
        "visualMap": {
            "min": -1,
            "max": 1,
            "calculable": True,
            "orient": "horizontal",
            "left": "center",
            "bottom": "0%",
            "inRange": {
                "color": ["#313695", "#4575b4", "#74add1", "#abd9e9", "#e0f3f8", "#ffffbf", "#fee090", "#fdae61", "#f46d43", "#d73027", "#a50026"],
            },
        },
        "series": [{
            "name": "Correlation",
            "type": "heatmap",
            "data": data,
            "label": {
                "show": True,
                "formatter": """function(params) {
                    var r = params.data[2];
                    var p = params.data[3];
                    var text = r.toFixed(2);
                    if (p < 0.001) return text + '***';
                    if (p < 0.01) return text + '**';
                    if (p < 0.05) return text + '*';
                    return text;
                }""",
                "fontSize": 9,
            },
            "emphasis": {
                "itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0,0,0,0.5)"},
            },
        }],
    }


def build_lag_analysis_chart(
    lag_result: LagAnalysisResult,
) -> dict[str, Any]:
    """Build ECharts chart for lag analysis.

    Args:
        lag_result: Lag analysis result.

    Returns:
        ECharts option dict.
    """
    lags = sorted(lag_result.correlations_by_lag.keys())
    correlations = [lag_result.correlations_by_lag[lag] for lag in lags]
    p_values = [lag_result.p_values_by_lag[lag] for lag in lags]

    # Mark significant points
    significant_data = []
    for i, (lag, r, p) in enumerate(zip(lags, correlations, p_values)):
        if p < 0.05:
            significant_data.append({
                "coord": [lag, r],
                "symbol": "circle",
                "symbolSize": 12,
            })

    solar_name = SOLAR_METRICS.get(
        lag_result.solar_metric,
        SolarMetric(lag_result.solar_metric, lag_result.solar_metric, "", "", True),
    ).name
    physio_name = PHYSIO_METRICS.get(
        lag_result.physio_metric,
        PhysiologicalMetric(lag_result.physio_metric, lag_result.physio_metric, "", "", True),
    ).name

    return {
        "title": {
            "text": f"Lag Analysis: {solar_name} → {physio_name}",
            "subtext": lag_result.interpretation,
            "left": "center",
            "textStyle": {"fontSize": 14, "fontWeight": "bold"},
        },
        "tooltip": {
            "trigger": "axis",
            "formatter": """function(params) {
                var lag = params[0].axisValue;
                var r = params[0].data.toFixed(3);
                return 'Lag: ' + lag + ' days<br/>r = ' + r;
            }""",
        },
        "xAxis": {
            "type": "category",
            "data": lags,
            "name": "Lag (days)",
            "nameLocation": "middle",
            "nameGap": 30,
        },
        "yAxis": {
            "type": "value",
            "name": "Correlation (r)",
            "min": -1,
            "max": 1,
        },
        "series": [
            {
                "name": "Correlation",
                "type": "line",
                "data": correlations,
                "smooth": True,
                "markPoint": {
                    "data": [
                        {"type": "max", "name": "Max"},
                        {"type": "min", "name": "Min"},
                    ],
                },
                "markLine": {
                    "data": [
                        {"yAxis": 0, "lineStyle": {"type": "dashed", "color": "#999"}},
                    ],
                },
            },
        ],
    }


def build_significant_results_table(
    correlations: list[CorrelationResult],
) -> dict[str, Any]:
    """Build ECharts table visualization for significant results.

    Args:
        correlations: List of significant correlations.

    Returns:
        Dict with table data for rendering.
    """
    rows = []
    for corr in correlations:
        solar_name = SOLAR_METRICS.get(
            corr.solar_metric,
            SolarMetric(corr.solar_metric, corr.solar_metric, "", "", True),
        ).name
        physio_name = PHYSIO_METRICS.get(
            corr.physio_metric,
            PhysiologicalMetric(corr.physio_metric, corr.physio_metric, "", "", True),
        ).name

        # Significance stars
        if corr.p_value < 0.001:
            sig_stars = "***"
        elif corr.p_value < 0.01:
            sig_stars = "**"
        elif corr.p_value < 0.05:
            sig_stars = "*"
        else:
            sig_stars = ""

        rows.append({
            "solar_metric": solar_name,
            "physio_metric": physio_name,
            "lag": corr.lag_days,
            "r": f"{corr.r:.3f}{sig_stars}",
            "p_value": f"{corr.p_value:.4f}",
            "r_squared": f"{corr.r_squared:.3f}",
            "ci": f"[{corr.ci_low:.3f}, {corr.ci_high:.3f}]",
            "strength": corr.strength.value,
            "interpretation": corr.interpretation,
        })

    return {
        "columns": [
            {"key": "solar_metric", "label": "Solar Metric"},
            {"key": "physio_metric", "label": "Physio Metric"},
            {"key": "lag", "label": "Lag (days)"},
            {"key": "r", "label": "r"},
            {"key": "p_value", "label": "p-value"},
            {"key": "r_squared", "label": "R²"},
            {"key": "ci", "label": "95% CI"},
            {"key": "strength", "label": "Strength"},
        ],
        "rows": rows,
    }

