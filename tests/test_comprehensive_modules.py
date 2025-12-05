"""Comprehensive tests for statistical analysis, multi-day tracking,
solar-physiology correlation, and scientific charts modules.

Tests cover:
- Statistical analysis functions
- Multi-day longitudinal tracking
- Solar-physiology correlation analysis
- Scientific chart generation
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.multiday_tracker import (
    AlertLevel,
    DailyActivityRecord,
    DailyHRVRecord,
    DailySleepRecord,
    MultiDayTracker,
    TrendStatus,
)
from app.scientific_charts import (
    COLORS,
    ChartConfig,
    build_activity_trend_chart,
    build_ans_balance_gauge,
    build_correlation_scatter_chart,
    build_frequency_domain_chart,
    build_hrv_time_series_chart,
    build_hypnogram_chart,
    build_multiday_trend_chart,
    build_poincare_plot,
    build_sleep_architecture_chart,
)
from app.solar_physiology_correlation import (
    CorrelationResult as SolarCorrelationResult,
    CorrelationStrength,
    SignificanceLevel,
    SolarPhysiologyAnalyzer,
    _classify_significance,
    _classify_strength,
    build_correlation_heatmap_chart,
    build_lag_analysis_chart,
    build_significant_results_table,
)
from app.statistical_analysis import (
    ANOVAResult,
    CorrelationResult,
    DescriptiveStats,
    EffectSizeType,
    GroupComparisonResult,
    StatisticalTestType,
    bonferroni_correction,
    compare_multiple_groups,
    compare_two_groups,
    compute_cohens_d,
    compute_correlation,
    compute_correlation_matrix,
    compute_descriptive_stats,
    compute_descriptive_table,
    compute_linear_regression,
    fdr_correction,
    format_apa_anova,
    format_apa_correlation,
    format_apa_ttest,
)


# ---------------------------------------------------------------------------
# Statistical Analysis Tests
# ---------------------------------------------------------------------------


class TestDescriptiveStats:
    """Tests for descriptive statistics computation."""

    def test_basic_descriptive_stats(self) -> None:
        """Test basic descriptive statistics."""
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        result = compute_descriptive_stats(data, "test_var")

        assert result.variable == "test_var"
        assert result.n == 10
        assert result.mean == pytest.approx(5.5, rel=0.01)
        assert result.median == pytest.approx(5.5, rel=0.01)
        assert result.min_val == 1.0
        assert result.max_val == 10.0

    def test_descriptive_stats_with_nan(self) -> None:
        """Test descriptive stats handles NaN values."""
        data = np.array([1, 2, np.nan, 4, 5])
        result = compute_descriptive_stats(data, "test")

        assert result.n == 4  # NaN excluded

    def test_insufficient_data(self) -> None:
        """Test handling of insufficient data."""
        data = np.array([1, 2])
        result = compute_descriptive_stats(data, "test")

        assert result.n == 2
        assert result.is_normal is False  # Can't test normality


class TestGroupComparisons:
    """Tests for group comparison functions."""

    def test_independent_ttest(self) -> None:
        """Test independent t-test."""
        np.random.seed(42)
        group1 = np.random.normal(100, 10, 30)
        group2 = np.random.normal(110, 10, 30)

        result = compare_two_groups(group1, group2, paired=False)

        assert isinstance(result, GroupComparisonResult)
        assert result.group1_n == 30
        assert result.group2_n == 30
        assert result.p_value < 0.05  # Should be significant

    def test_paired_test(self) -> None:
        """Test paired t-test."""
        np.random.seed(42)
        before = np.random.normal(100, 10, 20)
        after = before + np.random.normal(5, 3, 20)

        result = compare_two_groups(before, after, paired=True)

        assert isinstance(result, GroupComparisonResult)
        assert result.test_type in (
            StatisticalTestType.TTEST_PAIRED,
            StatisticalTestType.WILCOXON,
        )

    def test_anova(self) -> None:
        """Test ANOVA comparison."""
        np.random.seed(42)
        groups = {
            "A": np.random.normal(100, 10, 20),
            "B": np.random.normal(105, 10, 20),
            "C": np.random.normal(115, 10, 20),
        }

        result = compare_multiple_groups(groups, post_hoc=True)

        assert isinstance(result, ANOVAResult)
        assert len(result.group_means) == 3
        assert result.df_between == 2


class TestCorrelation:
    """Tests for correlation analysis."""

    def test_pearson_correlation(self) -> None:
        """Test Pearson correlation."""
        np.random.seed(42)
        x = np.linspace(0, 10, 50)
        y = 2 * x + np.random.normal(0, 2, 50)

        result = compute_correlation(x, y, method="pearson")

        assert isinstance(result, CorrelationResult)
        assert result.r > 0.8  # Strong positive correlation
        assert result.p_value < 0.05

    def test_spearman_correlation(self) -> None:
        """Test Spearman correlation."""
        np.random.seed(42)
        x = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        y = np.array([1, 3, 2, 5, 4, 7, 6, 9, 8, 10])

        result = compute_correlation(x, y, method="spearman")

        assert isinstance(result, CorrelationResult)
        assert result.method == "spearman"

    def test_correlation_matrix(self) -> None:
        """Test correlation matrix computation."""
        np.random.seed(42)
        df = pd.DataFrame({
            "a": np.random.normal(0, 1, 50),
            "b": np.random.normal(0, 1, 50),
            "c": np.random.normal(0, 1, 50),
        })

        corr_matrix, p_matrix, results = compute_correlation_matrix(
            df, ["a", "b", "c"]
        )

        assert corr_matrix.shape == (3, 3)
        assert p_matrix.shape == (3, 3)
        assert len(results) == 3  # 3 unique pairs


class TestEffectSizes:
    """Tests for effect size calculations."""

    def test_cohens_d(self) -> None:
        """Test Cohen's d calculation."""
        group1 = np.array([100, 102, 98, 105, 103])
        group2 = np.array([110, 108, 112, 109, 111])

        d, ci_low, ci_high = compute_cohens_d(group1, group2)

        assert d < 0  # group2 > group1
        assert ci_low < d < ci_high


class TestMultipleComparisons:
    """Tests for multiple comparison corrections."""

    def test_bonferroni(self) -> None:
        """Test Bonferroni correction."""
        p_values = [0.01, 0.02, 0.03, 0.04, 0.05]
        adjusted = bonferroni_correction(p_values)

        assert adjusted[0] == 0.05  # 0.01 * 5
        assert all(a >= p for a, p in zip(adjusted, p_values))

    def test_fdr(self) -> None:
        """Test FDR correction."""
        p_values = [0.001, 0.01, 0.03, 0.04, 0.05]
        adjusted = fdr_correction(p_values)

        assert adjusted[0] < adjusted[-1]
        assert all(a <= 1.0 for a in adjusted)


class TestRegression:
    """Tests for regression analysis."""

    def test_linear_regression(self) -> None:
        """Test linear regression."""
        np.random.seed(42)
        df = pd.DataFrame({
            "y": np.random.normal(100, 10, 50),
            "x1": np.random.normal(50, 5, 50),
            "x2": np.random.normal(30, 3, 50),
        })
        df["y"] = df["y"] + 0.5 * df["x1"] + 0.3 * df["x2"]

        result = compute_linear_regression(df, "y", ["x1", "x2"])

        assert result is not None
        assert result.n == 50
        assert "intercept" in result.coefficients
        assert "x1" in result.coefficients


class TestAPAFormatting:
    """Tests for APA formatting functions."""

    def test_format_correlation(self) -> None:
        """Test APA correlation formatting."""
        result = CorrelationResult(
            var1="x",
            var2="y",
            method="pearson",
            r=0.65,
            p_value=0.001,
            p_adjusted=0.001,
            n=50,
            r_squared=0.4225,
            ci_low=0.45,
            ci_high=0.80,
            significant=True,
            strength="strong",
        )

        formatted = format_apa_correlation(result)
        assert "r(48)" in formatted
        assert "0.65" in formatted

    def test_format_ttest(self) -> None:
        """Test APA t-test formatting."""
        result = GroupComparisonResult(
            test_type=StatisticalTestType.TTEST_IND,
            statistic=2.5,
            p_value=0.015,
            p_adjusted=0.015,
            effect_size=0.65,
            effect_interpretation=EffectSizeType.MEDIUM,
            ci_low=0.2,
            ci_high=1.1,
            group1_n=30,
            group2_n=30,
            group1_mean=100,
            group2_mean=110,
            significant=True,
            recommendation="Significant difference.",
        )

        formatted = format_apa_ttest(result)
        assert "t(58)" in formatted
        assert "2.50" in formatted


# ---------------------------------------------------------------------------
# Multi-day Tracker Tests
# ---------------------------------------------------------------------------


class TestMultiDayTracker:
    """Tests for multi-day longitudinal tracking."""

    @pytest.fixture
    def tracker_with_data(self) -> MultiDayTracker:
        """Create tracker with sample data."""
        tracker = MultiDayTracker()

        # Add 14 days of HRV data
        base_date = date(2025, 1, 1)
        for i in range(14):
            current_date = base_date + timedelta(days=i)
            tracker.add_hrv_record(DailyHRVRecord(
                date=current_date,
                rmssd=40 + i * 2 + np.random.normal(0, 3),
                sdnn=50 + i * 1.5 + np.random.normal(0, 4),
                mean_hr=65 - i * 0.3 + np.random.normal(0, 2),
                hrv_score=70 + i * 1.5,
            ))
            tracker.add_sleep_record(DailySleepRecord(
                date=current_date,
                tst_minutes=420 + np.random.normal(0, 30),
                sleep_efficiency=85 + np.random.normal(0, 5),
                deep_sleep_pct=20 + np.random.normal(0, 3),
            ))
            tracker.add_activity_record(DailyActivityRecord(
                date=current_date,
                steps=8000 + int(np.random.normal(0, 1000)),
                active_minutes=45 + int(np.random.normal(0, 10)),
                resting_hr=60 + np.random.normal(0, 3),
            ))

        return tracker

    def test_add_records(self, tracker_with_data: MultiDayTracker) -> None:
        """Test adding records to tracker."""
        hrv_df = tracker_with_data.get_hrv_dataframe()
        assert len(hrv_df) == 14

        sleep_df = tracker_with_data.get_sleep_dataframe()
        assert len(sleep_df) == 14

    def test_rolling_stats(self, tracker_with_data: MultiDayTracker) -> None:
        """Test rolling statistics computation."""
        rolling = tracker_with_data.compute_rolling_stats("rmssd", window=7, data_type="hrv")

        assert "rolling_mean" in rolling.columns
        assert "rolling_std" in rolling.columns
        assert "z_score" in rolling.columns

    def test_trend_analysis(self, tracker_with_data: MultiDayTracker) -> None:
        """Test trend analysis."""
        trend = tracker_with_data.analyze_trend("rmssd", data_type="hrv")

        assert trend.metric_name == "rmssd"
        assert trend.status in TrendStatus
        assert trend.alert_level in AlertLevel

    def test_generate_summary(self, tracker_with_data: MultiDayTracker) -> None:
        """Test comprehensive summary generation."""
        summary = tracker_with_data.generate_summary()

        assert summary.n_days == 14
        assert "rmssd" in summary.hrv_trends
        assert "tst_minutes" in summary.sleep_trends

    def test_intervention_analysis(self, tracker_with_data: MultiDayTracker) -> None:
        """Test intervention analysis."""
        intervention_date = date(2025, 1, 8)
        result = tracker_with_data.analyze_intervention(
            intervention_date=intervention_date,
            metric="rmssd",
            data_type="hrv",
            pre_days=7,
            post_days=7,
        )

        assert "pre_mean" in result
        assert "post_mean" in result
        assert "cohens_d" in result


# ---------------------------------------------------------------------------
# Solar-Physiology Correlation Tests
# ---------------------------------------------------------------------------


class TestSolarPhysiologyCorrelation:
    """Tests for solar-physiology correlation analysis."""

    @pytest.fixture
    def sample_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Create sample solar and physio data."""
        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=30, freq="D")

        # Solar data with some correlation to physio
        kp_index = np.random.uniform(1, 5, 30)

        solar_df = pd.DataFrame({
            "kp_index": kp_index,
            "dst": -20 - kp_index * 10 + np.random.normal(0, 10, 30),
            "proton_speed": 400 + kp_index * 50 + np.random.normal(0, 30, 30),
        }, index=dates)

        # Physio data with inverse correlation to Kp
        rmssd = 50 - kp_index * 3 + np.random.normal(0, 5, 30)

        physio_df = pd.DataFrame({
            "rmssd": rmssd,
            "sdnn": rmssd * 1.2 + np.random.normal(0, 5, 30),
            "mean_hr": 65 + kp_index * 2 + np.random.normal(0, 3, 30),
        }, index=dates)

        return solar_df, physio_df

    def test_correlation_computation(
        self,
        sample_data: tuple[pd.DataFrame, pd.DataFrame],
    ) -> None:
        """Test correlation computation."""
        solar_df, physio_df = sample_data
        analyzer = SolarPhysiologyAnalyzer(solar_df, physio_df)

        result = analyzer.compute_correlation("kp_index", "rmssd")

        assert result.n >= 10
        assert result.r < 0  # Should be negative correlation
        assert result.significance in SignificanceLevel

    def test_lag_analysis(
        self,
        sample_data: tuple[pd.DataFrame, pd.DataFrame],
    ) -> None:
        """Test lag analysis."""
        solar_df, physio_df = sample_data
        analyzer = SolarPhysiologyAnalyzer(solar_df, physio_df)

        result = analyzer.analyze_lag("kp_index", "rmssd", max_lag=3)

        assert len(result.correlations_by_lag) == 7  # -3 to +3
        assert result.optimal_lag in range(-3, 4)

    def test_comprehensive_report(
        self,
        sample_data: tuple[pd.DataFrame, pd.DataFrame],
    ) -> None:
        """Test comprehensive correlation report."""
        solar_df, physio_df = sample_data
        analyzer = SolarPhysiologyAnalyzer(solar_df, physio_df)

        report = analyzer.compute_all_correlations(
            solar_metrics=["kp_index"],
            physio_metrics=["rmssd", "mean_hr"],
            include_lags=True,
        )

        assert report.n_days > 0
        assert len(report.all_correlations) > 0

    def test_correlation_matrix(
        self,
        sample_data: tuple[pd.DataFrame, pd.DataFrame],
    ) -> None:
        """Test correlation matrix generation."""
        solar_df, physio_df = sample_data
        analyzer = SolarPhysiologyAnalyzer(solar_df, physio_df)

        corr_matrix, p_matrix = analyzer.get_correlation_matrix(
            solar_metrics=["kp_index", "dst"],
            physio_metrics=["rmssd", "mean_hr"],
        )

        assert corr_matrix.shape == (2, 2)
        assert p_matrix.shape == (2, 2)


class TestSignificanceClassification:
    """Tests for significance classification helpers."""

    def test_classify_significance(self) -> None:
        """Test significance level classification."""
        assert _classify_significance(0.0005) == SignificanceLevel.VERY_HIGHLY_SIGNIFICANT
        assert _classify_significance(0.005) == SignificanceLevel.HIGHLY_SIGNIFICANT
        assert _classify_significance(0.03) == SignificanceLevel.SIGNIFICANT
        assert _classify_significance(0.08) == SignificanceLevel.MARGINAL
        assert _classify_significance(0.15) == SignificanceLevel.NOT_SIGNIFICANT

    def test_classify_strength(self) -> None:
        """Test correlation strength classification."""
        assert _classify_strength(0.05) == CorrelationStrength.NEGLIGIBLE
        assert _classify_strength(0.2) == CorrelationStrength.WEAK
        assert _classify_strength(0.4) == CorrelationStrength.MODERATE
        assert _classify_strength(0.6) == CorrelationStrength.STRONG
        assert _classify_strength(0.85) == CorrelationStrength.VERY_STRONG


# ---------------------------------------------------------------------------
# Scientific Charts Tests
# ---------------------------------------------------------------------------


class TestScientificCharts:
    """Tests for scientific chart generation."""

    def test_hrv_time_series_chart(self) -> None:
        """Test HRV time series chart generation."""
        timestamps = [datetime(2025, 1, 1, h) for h in range(24)]
        rmssd = np.random.uniform(30, 60, 24)
        sdnn = np.random.uniform(40, 80, 24)

        chart = build_hrv_time_series_chart(
            timestamps=timestamps,
            rmssd=rmssd,
            sdnn=sdnn,
        )

        assert "title" in chart
        assert "series" in chart
        assert len(chart["series"]) >= 2  # RMSSD and SDNN

    def test_frequency_domain_chart(self) -> None:
        """Test frequency domain chart generation."""
        frequencies = np.linspace(0, 0.5, 100)
        psd = np.random.uniform(0, 1000, 100)

        chart = build_frequency_domain_chart(
            frequencies=frequencies,
            psd=psd,
        )

        assert "xAxis" in chart
        assert "yAxis" in chart
        assert "series" in chart

    def test_poincare_plot(self) -> None:
        """Test Poincaré plot generation."""
        rr_intervals = np.random.normal(800, 50, 100)

        chart = build_poincare_plot(
            rr_intervals=rr_intervals,
            sd1=30.0,
            sd2=45.0,
        )

        assert "series" in chart
        assert any(s["type"] == "scatter" for s in chart["series"])

    def test_hypnogram_chart(self) -> None:
        """Test hypnogram chart generation."""
        timestamps = [datetime(2025, 1, 1, 22) + timedelta(minutes=30 * i) for i in range(16)]
        stages = [0, 1, 2, 2, 3, 3, 2, 4, 4, 2, 3, 2, 1, 0, 0, 0]

        chart = build_hypnogram_chart(
            timestamps=timestamps,
            stages=stages,
        )

        assert "yAxis" in chart
        assert chart["yAxis"]["type"] == "category"

    def test_sleep_architecture_chart(self) -> None:
        """Test sleep architecture pie chart."""
        chart = build_sleep_architecture_chart(
            wake_pct=5,
            n1_pct=10,
            n2_pct=50,
            n3_pct=15,
            rem_pct=20,
        )

        assert "series" in chart
        assert chart["series"][0]["type"] == "pie"

    def test_ans_balance_gauge(self) -> None:
        """Test ANS balance gauge generation."""
        chart = build_ans_balance_gauge(lf_hf_ratio=1.5)

        assert "series" in chart
        assert chart["series"][0]["type"] == "gauge"

    def test_activity_trend_chart(self) -> None:
        """Test activity trend chart."""
        dates = [date(2025, 1, d) for d in range(1, 8)]
        steps = [8000, 9500, 7200, 10000, 8500, 6000, 9000]

        chart = build_activity_trend_chart(
            dates=dates,
            steps=steps,
        )

        assert "series" in chart
        assert any(s["type"] == "bar" for s in chart["series"])

    def test_multiday_trend_chart(self) -> None:
        """Test multi-day trend chart."""
        dates = [date(2025, 1, d) for d in range(1, 15)]
        values = np.random.uniform(40, 60, 14)
        rolling_mean = pd.Series(values).rolling(7, min_periods=1).mean().values

        chart = build_multiday_trend_chart(
            dates=dates,
            values=values,
            rolling_mean=rolling_mean,
            metric_name="RMSSD",
        )

        assert "series" in chart
        assert len(chart["series"]) >= 2

    def test_correlation_scatter_chart(self) -> None:
        """Test correlation scatter chart."""
        x = np.random.uniform(0, 10, 30)
        y = 2 * x + np.random.normal(0, 2, 30)

        chart = build_correlation_scatter_chart(
            x_values=x,
            y_values=y,
            x_label="Kp Index",
            y_label="RMSSD",
            r=0.85,
            p_value=0.001,
        )

        assert "graphic" in chart  # Statistics annotation
        assert any(s["type"] == "scatter" for s in chart["series"])


class TestCorrelationCharts:
    """Tests for correlation visualization charts."""

    def test_heatmap_chart(self) -> None:
        """Test correlation heatmap chart."""
        corr_matrix = pd.DataFrame(
            [[1.0, -0.5], [-0.5, 1.0]],
            index=["kp_index", "dst"],
            columns=["rmssd", "sdnn"],
        )
        p_matrix = pd.DataFrame(
            [[0.0, 0.01], [0.01, 0.0]],
            index=["kp_index", "dst"],
            columns=["rmssd", "sdnn"],
        )

        chart = build_correlation_heatmap_chart(corr_matrix, p_matrix)

        assert "visualMap" in chart
        assert chart["series"][0]["type"] == "heatmap"

    def test_significant_results_table(self) -> None:
        """Test significant results table generation."""
        correlations = [
            SolarCorrelationResult(
                solar_metric="kp_index",
                physio_metric="rmssd",
                lag_days=0,
                r=-0.65,
                p_value=0.001,
                n=30,
                r_squared=0.42,
                ci_low=-0.80,
                ci_high=-0.45,
                significance=SignificanceLevel.HIGHLY_SIGNIFICANT,
                strength=CorrelationStrength.STRONG,
                interpretation="Significant negative correlation.",
            ),
        ]

        table = build_significant_results_table(correlations)

        assert "columns" in table
        assert "rows" in table
        assert len(table["rows"]) == 1


class TestChartConfig:
    """Tests for chart configuration."""

    def test_default_config(self) -> None:
        """Test default chart configuration."""
        config = ChartConfig()

        assert config.width == "100%"
        assert config.height == 400
        assert config.animation is True

    def test_custom_config(self) -> None:
        """Test custom chart configuration."""
        config = ChartConfig(
            width="800px",
            height=600,
            animation=False,
            theme="dark",
        )

        assert config.width == "800px"
        assert config.height == 600
        assert config.animation is False
        assert config.theme == "dark"

    def test_colors_defined(self) -> None:
        """Test color palette is properly defined."""
        assert "primary" in COLORS
        assert "hrv" in COLORS
        assert "sleep" in COLORS
        assert "solar" in COLORS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

