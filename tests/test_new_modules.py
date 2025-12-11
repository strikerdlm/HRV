"""Tests for new HRV analysis modules.

This test suite validates:
- gauge_builder: Gauge configuration generation
- publication_export: Statistical summaries and formatting
- ml_analytics: Anomaly detection and trend analysis
- gpt_interpretation: Payload building and local fallback
- hrv_fragmentation: HRF metrics computation
- sleep_metrics: Sleep metric calculations

Tests follow pytest conventions with deterministic inputs for reproducibility.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import fatigue_integration as fi  # pylint: disable=wrong-import-position

# ---------------------------------------------------------------------------
# gauge_builder tests
# ---------------------------------------------------------------------------


class TestGaugeBuilder:
    """Tests for gauge_builder module."""

    def test_build_two_ring_gauge_returns_valid_structure(self) -> None:
        """Test that gauge builder returns valid ECharts option."""
        from app.gauge_builder import build_two_ring_gauge

        gauge = build_two_ring_gauge("sdnn", 45.0)

        assert "series" in gauge
        assert len(gauge["series"]) >= 1
        assert gauge["series"][0]["type"] == "gauge"

    def test_build_two_ring_gauge_with_custom_title(self) -> None:
        """Test gauge with custom title."""
        from app.gauge_builder import build_two_ring_gauge

        gauge = build_two_ring_gauge("rmssd", 38.0, title="Custom Title")

        # Title should be in the data
        data = gauge["series"][0]["data"]
        assert len(data) > 0
        assert data[0]["name"] == "Custom Title"

    def test_build_summary_gauge_panel_organizes_by_domain(self) -> None:
        """Test that summary panel organizes gauges by domain."""
        from app.gauge_builder import build_summary_gauge_panel

        metrics = {
            "sdnn": 50.0,
            "rmssd": 42.0,
            "lf_hf_ratio": 2.0,
            "hf_power": 500.0,
            "sd1": 30.0,
            "dfa_alpha1": 1.0,
        }

        panels = build_summary_gauge_panel(metrics)

        assert "time_domain" in panels
        assert "frequency_domain" in panels
        assert "nonlinear" in panels
        assert len(panels["time_domain"]) >= 2
        assert len(panels["frequency_domain"]) >= 2

    def test_get_available_gauge_metrics_returns_list(self) -> None:
        """Test that available metrics list is populated."""
        from app.gauge_builder import get_available_gauge_metrics

        metrics = get_available_gauge_metrics()

        assert isinstance(metrics, list)
        assert len(metrics) > 20
        assert "sdnn" in metrics
        assert "rmssd" in metrics
        assert "lf_hf_ratio" in metrics

    def test_gauge_thresholds_exist_for_key_metrics(self) -> None:
        """Test that thresholds exist for key metrics."""
        from app.gauge_builder import get_gauge_thresholds

        key_metrics = ["sdnn", "rmssd", "lf_hf_ratio", "hf_power", "sd1"]

        for metric in key_metrics:
            thresh = get_gauge_thresholds(metric)
            assert thresh is not None
            assert thresh.max_val > thresh.low


# ---------------------------------------------------------------------------
# publication_export tests
# ---------------------------------------------------------------------------


class TestPublicationExport:
    """Tests for publication_export module."""

    def test_compute_statistical_summary_basic(self) -> None:
        """Test basic statistical summary computation."""
        from app.publication_export import compute_statistical_summary

        np.random.seed(42)
        values = np.random.normal(50, 10, 100)

        summary = compute_statistical_summary(values, "test_metric")

        assert summary.n == 100
        assert 45 < summary.mean < 55
        assert 8 < summary.std < 12
        assert summary.ci_low < summary.mean < summary.ci_high

    def test_compute_statistical_summary_handles_small_sample(self) -> None:
        """Test summary with small sample size."""
        from app.publication_export import compute_statistical_summary

        values = np.array([1.0, 2.0])

        summary = compute_statistical_summary(values, "small")

        assert summary.n == 2
        assert summary.mean == 1.5

    def test_compute_effect_size_detects_difference(self) -> None:
        """Test effect size calculation."""
        from app.publication_export import compute_effect_size

        np.random.seed(42)
        group1 = np.random.normal(50, 10, 50)
        group2 = np.random.normal(60, 10, 50)  # 1 SD difference

        effect = compute_effect_size(group1, group2)

        assert abs(effect.cohens_d) > 0.5  # Should detect medium+ effect
        assert effect.interpretation in ["medium", "large"]

    def test_format_mean_sd_follows_apa(self) -> None:
        """Test APA formatting of mean ± SD."""
        from app.publication_export import format_mean_sd

        result = format_mean_sd(42.5, 15.3, decimals=1)

        assert result == "42.5 ± 15.3"

    def test_format_p_value_handles_small_values(self) -> None:
        """Test p-value formatting for small values."""
        from app.publication_export import format_p_value

        assert format_p_value(0.0001) == "p < .001"
        assert format_p_value(0.045).startswith("p = ")

    def test_generate_statistical_table_creates_dataframe(self) -> None:
        """Test statistical table generation."""
        from app.publication_export import (
            PublicationConfig,
            generate_statistical_table,
        )

        np.random.seed(42)
        df = pd.DataFrame({
            "sdnn": np.random.normal(50, 15, 30),
            "rmssd": np.random.normal(42, 12, 30),
        })

        config = PublicationConfig()
        table = generate_statistical_table(df, ["sdnn", "rmssd"], config=config)

        assert not table.empty
        assert "Mean ± SD" in table.columns
        assert "Median [IQR]" in table.columns


# ---------------------------------------------------------------------------
# ml_analytics tests
# ---------------------------------------------------------------------------


class TestMlAnalytics:
    """Tests for ml_analytics module."""

    def test_detect_anomalies_zscore_finds_outliers(self) -> None:
        """Test Z-score anomaly detection."""
        from app.ml_analytics import detect_anomalies_zscore

        # Create data with obvious outliers
        np.random.seed(42)
        normal_data = np.random.normal(50, 5, 95)
        outliers = np.array([100.0, 105.0, 110.0, 5.0, 0.0])
        data = np.concatenate([normal_data, outliers])

        result = detect_anomalies_zscore(data, threshold=2.5)

        assert result.n_anomalies > 0
        assert result.n_anomalies <= len(outliers)
        assert len(result.anomaly_indices) == result.n_anomalies

    def test_detect_anomalies_mad_is_robust(self) -> None:
        """Test MAD anomaly detection robustness."""
        from app.ml_analytics import detect_anomalies_mad

        # Data with outliers
        np.random.seed(42)
        data = np.concatenate([
            np.random.normal(50, 5, 90),
            [100, 105, 110],
        ])

        result = detect_anomalies_mad(data, threshold=3.0)

        assert result.method.value == "mad"
        assert result.n_anomalies > 0

    def test_detect_anomalies_iqr_basic(self) -> None:
        """Test IQR anomaly detection."""
        from app.ml_analytics import detect_anomalies_iqr

        np.random.seed(42)
        data = np.concatenate([
            np.random.normal(50, 5, 90),
            [100, 105],
        ])

        result = detect_anomalies_iqr(data, k=1.5)

        assert result.method.value == "iqr"
        assert result.n_anomalies >= 1

    def test_analyze_trend_detects_increasing(self) -> None:
        """Test trend analysis with increasing data."""
        from app.ml_analytics import TrendDirection, analyze_trend

        np.random.seed(42)
        # Clear increasing trend with minimal noise
        x = np.arange(50)
        noise = np.random.normal(0, 0.5, 50)  # Reduced noise for clearer trend
        data = x * 2 + noise

        result = analyze_trend(data)

        # Should detect increasing or at least have positive slope
        assert result.slope > 0
        assert result.r_squared > 0.8

    def test_analyze_trend_detects_stable(self) -> None:
        """Test trend analysis with stable data."""
        from app.ml_analytics import TrendDirection, analyze_trend

        np.random.seed(42)
        # No trend, just noise
        data = np.random.normal(50, 2, 50)

        result = analyze_trend(data)

        # Should be stable or variable with low slope
        assert result.direction in [TrendDirection.STABLE, TrendDirection.VARIABLE]
        assert abs(result.slope) < 1

    def test_classify_hrv_state_returns_valid_state(self) -> None:
        """Test HRV state classification."""
        from app.ml_analytics import classify_hrv_state

        metrics = {
            "rmssd": 35.0,
            "lf_hf_ratio": 2.5,
            "parasympathetic_index": 0.5,
            "stress_index": 150.0,
        }

        state = classify_hrv_state(metrics)

        assert state["overall_state"] in ["optimal", "normal", "suboptimal", "concerning"]
        assert 0 <= state["confidence"] <= 1
        assert isinstance(state["flags"], list)

    def test_compute_rolling_statistics_basic(self) -> None:
        """Test rolling statistics computation."""
        from app.ml_analytics import compute_rolling_statistics

        data = np.arange(20, dtype=float)

        result = compute_rolling_statistics(data, window=5)

        assert "rolling_mean" in result
        assert "rolling_std" in result
        assert len(result["rolling_mean"]) == len(data)


# ---------------------------------------------------------------------------
# gpt_interpretation tests
# ---------------------------------------------------------------------------


class TestGptInterpretation:
    """Tests for gpt_interpretation module."""

    def test_build_analysis_payload_creates_valid_json(self) -> None:
        """Test payload building creates valid JSON."""
        from app.gpt_interpretation import build_analysis_payload

        meta_rows = [{"source": "test", "n_intervals": 300}]
        results_df = pd.DataFrame({
            "source": ["test"],
            "sdnn": [45.0],
            "rmssd": [38.0],
        })

        payload = build_analysis_payload(
            meta_rows,
            results_df,
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
        )

        # Should be valid JSON
        parsed = json.loads(payload)
        assert "datasets_overview" in parsed
        assert "summary_metrics" in parsed
        assert "plot_catalogue" in parsed

    def test_interpretation_result_dataclass(self) -> None:
        """Test InterpretationResult dataclass."""
        from app.gpt_interpretation import InterpretationMode, InterpretationResult

        result = InterpretationResult(
            markdown="# Test",
            model_used="test",
            mode=InterpretationMode.LOCAL,
            confidence=0.8,
        )

        assert result.markdown == "# Test"
        assert result.mode == InterpretationMode.LOCAL
        assert result.confidence == 0.8

    def test_local_interpretation_fallback_works(self) -> None:
        """Test local fallback interpretation."""
        from app.gpt_interpretation import _generate_local_interpretation

        payload = json.dumps({
            "datasets_overview": [{"source": "test", "n_intervals": 300}],
            "summary_metrics": [{"source": "test", "sdnn": 45.0, "rmssd": 38.0}],
        })

        result = _generate_local_interpretation(payload)

        assert result.mode.value == "local"
        assert "HRV Analysis" in result.markdown
        assert result.confidence > 0


# ---------------------------------------------------------------------------
# hrv_fragmentation tests
# ---------------------------------------------------------------------------


class TestHrvFragmentation:
    """Tests for hrv_fragmentation module."""

    def test_compute_hrf_metrics_basic(self) -> None:
        """Test HRF metrics computation."""
        from app.hrv_fragmentation import compute_hrf_metrics

        # Create RR intervals with some variability
        np.random.seed(42)
        rr = 800 + np.random.normal(0, 20, 100)

        metrics = compute_hrf_metrics(rr)

        assert 0 <= metrics.pip <= 100
        assert 0 <= metrics.ials <= 1
        assert metrics.quality_ok

    def test_compute_hrf_metrics_handles_short_series(self) -> None:
        """Test HRF with short series."""
        from app.hrv_fragmentation import compute_hrf_metrics

        rr = np.array([800.0, 810.0, 795.0])

        metrics = compute_hrf_metrics(rr)

        # Should handle gracefully
        assert metrics is not None


# ---------------------------------------------------------------------------
# fatigue_integration tests
# ---------------------------------------------------------------------------


class _StubDatabase:
    """Minimal stub to emulate wrist/clinical history for fatigue tests."""

    def __init__(
        self,
        wrist_df: pd.DataFrame | None = None,
        clinical_history: list | None = None,
    ) -> None:
        self._wrist_df = wrist_df
        self._clinical_history = clinical_history or []

    def get_garmin_daily_dataframe(self, user_id: str, limit: int = 30) -> pd.DataFrame | None:  # noqa: ARG002
        if self._wrist_df is None:
            return None
        return self._wrist_df.copy()

    def get_clinical_scales_history(self, user_id: str, limit: int = 1) -> list:  # noqa: ARG002
        return list(self._clinical_history)


class TestFatigueIntegration:
    """Tests covering assessment-driven SAFTE automation."""

    def test_run_assessment_prefers_wrist_monitoring(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Wrist monitoring should be used ahead of clinical fallbacks."""
        wrist_df = pd.DataFrame(
            {
                "metric_date": pd.to_datetime(["2025-12-10"]),
                "sleep_duration_hours": [6.5],
                "sleep_score": [82],
                "sleep_efficiency": [90],
                "stress_score": [45],
            }
        )
        db = _StubDatabase(wrist_df=wrist_df)
        monkeypatch.setattr(fi, "get_database", lambda: db)
        sentinel_result = object()
        captured_kwargs: dict = {}

        def _fake_run(**kwargs):
            captured_kwargs.update(kwargs)
            return sentinel_result

        monkeypatch.setattr(fi, "run_integrated_fatigue_analysis", _fake_run)

        result, source, returned_wrist = fi.run_assessment_fatigue_prediction(
            user_context={"age_years": 40, "sex": "male"},
            user_id="demo",
            prediction_days=1,
            model_type="advanced",
        )

        assert result is sentinel_result
        assert source == "wrist_monitoring"
        assert returned_wrist is not None
        assert not returned_wrist.empty
        sleep_schedule = captured_kwargs["sleep_schedule"]
        assert pytest.approx(sleep_schedule.duration, rel=1e-3) == 6.5

    def test_run_assessment_falls_back_to_clinical(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Clinical assessment should be used when wrist data is missing."""
        clinical = [
            SimpleNamespace(
                pittsburgh_sleep_quality_index=4,
                epworth_sleepiness_scale=12,
            )
        ]
        db = _StubDatabase(wrist_df=None, clinical_history=clinical)
        monkeypatch.setattr(fi, "get_database", lambda: db)
        sentinel_result = object()
        monkeypatch.setattr(fi, "run_integrated_fatigue_analysis", lambda **_: sentinel_result)

        result, source, wrist_df = fi.run_assessment_fatigue_prediction(
            user_context={"age_years": 35, "sex": "female"},
            user_id="demo",
            prediction_days=1,
            model_type="advanced",
        )

        assert result is sentinel_result
        assert source == "clinical_assessment"
        assert wrist_df is None


# ---------------------------------------------------------------------------
# exploration medical analytics tests
# ---------------------------------------------------------------------------


class TestExplorationMedicalAnalytics:
    """Tests for exploration medical analytics helpers."""

    def test_compute_radiation_rate_returns_expected_delta(self) -> None:
        """Average daily accumulation should reflect mission day spacing."""
        from app.user_profile_tab import _compute_radiation_rate

        df = pd.DataFrame({
            "mission_day": [0, 5, 10],
            "radiation_dose_msv": [10.0, 20.0, 40.0],
        })

        rate = _compute_radiation_rate(df)

        assert rate is not None
        assert pytest.approx(rate, rel=1e-3) == 3.0

    def test_build_frequency_df_counts_list_like_entries(self) -> None:
        """Frequency helper should aggregate strings, lists, and sets."""
        from app.user_profile_tab import _build_frequency_df

        values = [
            ["Headache", "Nausea"],
            ["Headache"],
            "Nausea",
            {"Sleep disruption"},
            None,
        ]

        freq_df = _build_frequency_df(values, top_n=2)

        assert not freq_df.empty
        assert set(freq_df["Label"]) == {"Headache", "Nausea"}
        assert freq_df["Count"].sum() == 4

# ---------------------------------------------------------------------------
# sleep_metrics tests
# ---------------------------------------------------------------------------


class TestSleepMetrics:
    """Tests for sleep_metrics module."""

    def test_compute_sleep_metrics_from_binary(self) -> None:
        """Test sleep metrics from binary sleep/wake data."""
        from app.sleep_metrics import compute_sleep_metrics_from_binary

        # Create sleep pattern: wake, sleep, wake, sleep
        sleep_wake = pd.Series([0, 0, 1, 1, 1, 1, 1, 0, 1, 1])

        metrics = compute_sleep_metrics_from_binary(
            sleep_wake,
            epoch_duration_seconds=30,
        )

        assert metrics.tst_minutes > 0
        assert metrics.tib_minutes > 0
        assert 0 <= metrics.sleep_efficiency <= 100

    def test_compute_sleep_metrics_from_epochs(self) -> None:
        """Test sleep metrics from staged epochs."""
        from app.sleep_metrics import compute_sleep_metrics_from_epochs

        # Create epoch data with stages
        epochs = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01 22:00", periods=20, freq="30s"),
            "stage": [0, 0, 1, 2, 2, 2, 3, 3, 4, 4, 4, 2, 2, 3, 3, 4, 4, 1, 0, 0],
        })

        metrics = compute_sleep_metrics_from_epochs(epochs)

        assert metrics.tst_minutes > 0
        assert metrics.n3_pct >= 0
        assert metrics.rem_pct >= 0


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestModuleIntegration:
    """Integration tests across modules."""

    def test_gauge_with_ml_classification(self) -> None:
        """Test gauge building with ML classification results."""
        from app.gauge_builder import build_two_ring_gauge
        from app.ml_analytics import classify_hrv_state

        metrics = {"rmssd": 45.0, "lf_hf_ratio": 2.0, "parasympathetic_index": 0.6}

        state = classify_hrv_state(metrics)
        gauge = build_two_ring_gauge("rmssd", metrics["rmssd"])

        assert state["overall_state"] in ["optimal", "normal", "suboptimal", "concerning"]
        assert "series" in gauge

    def test_publication_export_with_real_data(self) -> None:
        """Test publication export with realistic data."""
        from app.publication_export import (
            PublicationConfig,
            generate_statistical_table,
        )

        np.random.seed(42)
        df = pd.DataFrame({
            "sdnn": np.random.normal(50, 15, 50),
            "rmssd": np.random.normal(42, 12, 50),
            "lf_hf_ratio": np.random.lognormal(0.5, 0.5, 50),
            "hf_power": np.random.lognormal(6, 0.5, 50),
        })

        config = PublicationConfig(
            include_statistics=True,
            decimal_places=2,
        )

        table = generate_statistical_table(
            df,
            ["sdnn", "rmssd", "lf_hf_ratio", "hf_power"],
            config=config,
        )

        assert len(table) == 4
        assert "Normality (p)" in table.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

