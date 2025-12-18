"""Tests for Profile Tools Engine module.

Tests recovery score, training readiness, fatigue prediction,
personalized HRV analysis, and performance forecasting.
"""

from __future__ import annotations

import pytest

# Import from app module
import sys
sys.path.insert(0, "app")

from profile_tools_engine import (
    calculate_recovery_score,
    calculate_training_readiness,
    predict_fatigue,
    analyze_hrv_personalized,
    generate_performance_forecast,
    predict_operational_performance,
    run_all_profile_tools,
    RecoveryStatus,
    ReadinessLevel,
    FatigueRisk,
    OperationalReadinessLevel,
)


class TestRecoveryScore:
    """Tests for recovery score calculation."""

    def test_excellent_recovery_high_rmssd(self) -> None:
        """High RMSSD with good sleep should yield excellent recovery."""
        result = calculate_recovery_score(
            rmssd_ms=60.0,
            age=30,
            sleep_hours=8.5,
            sleep_quality=0.9,
            resting_hr=55.0,
        )
        assert result.score >= 70
        assert result.status in [RecoveryStatus.EXCELLENT, RecoveryStatus.GOOD]

    def test_poor_recovery_low_rmssd(self) -> None:
        """Very low RMSSD with poor sleep should yield poor recovery."""
        result = calculate_recovery_score(
            rmssd_ms=10.0,
            age=50,
            sleep_hours=4.0,
            sleep_quality=0.3,
            resting_hr=85.0,
        )
        assert result.score < 50
        assert result.status in [RecoveryStatus.LOW, RecoveryStatus.POOR]

    def test_recovery_score_has_components(self) -> None:
        """Recovery score should have HRV, sleep, and HR components."""
        result = calculate_recovery_score(
            rmssd_ms=35.0,
            age=40,
            sleep_hours=7.0,
            sleep_quality=0.7,
            resting_hr=65.0,
        )
        assert "hrv" in result.components
        assert "sleep" in result.components
        assert "resting_hr" in result.components
        assert result.ln_rmssd is not None
        assert result.ln_rmssd > 0

    def test_recovery_score_to_dict(self) -> None:
        """Recovery score should convert to dictionary."""
        result = calculate_recovery_score(
            rmssd_ms=35.0,
            age=40,
        )
        d = result.to_dict()
        assert "score" in d
        assert "status" in d
        assert "components" in d


class TestTrainingReadiness:
    """Tests for training readiness assessment."""

    def test_optimal_readiness_good_inputs(self) -> None:
        """Good inputs should yield high readiness."""
        result = calculate_training_readiness(
            rmssd_ms=50.0,
            age=30,
            sleep_hours=8.5,
            sleep_quality=0.95,
        )
        assert result.readiness_score >= 65
        assert result.level in [ReadinessLevel.HIGH, ReadinessLevel.OPTIMAL, ReadinessLevel.MODERATE]

    def test_low_readiness_poor_inputs(self) -> None:
        """Poor inputs should yield low readiness."""
        result = calculate_training_readiness(
            rmssd_ms=15.0,
            age=50,
            sleep_hours=4.0,
            sleep_quality=0.3,
            accumulated_strain=80.0,
        )
        assert result.readiness_score < 50
        assert result.level in [ReadinessLevel.LOW, ReadinessLevel.VERY_LOW, ReadinessLevel.MODERATE]

    def test_readiness_has_components(self) -> None:
        """Readiness should have all components."""
        result = calculate_training_readiness(
            rmssd_ms=35.0,
            age=40,
        )
        assert result.hrv_component >= 0
        assert result.sleep_component >= 0
        assert result.fatigue_component >= 0
        assert result.strain_component >= 0

    def test_readiness_has_recommendations(self) -> None:
        """Readiness should have training recommendations."""
        result = calculate_training_readiness(
            rmssd_ms=35.0,
            age=40,
        )
        assert len(result.training_recommendations) > 0
        assert len(result.workout_suggestions) > 0


class TestFatiguePrediction:
    """Tests for SAFTE fatigue prediction."""

    def test_good_sleep_high_effectiveness(self) -> None:
        """Good sleep should yield high effectiveness."""
        result = predict_fatigue(
            sleep_hours_last_night=8.0,
            sleep_quality=0.9,
            hours_awake=4.0,
            current_hour=11,
        )
        assert result.current_effectiveness >= 70
        assert result.risk_level in [FatigueRisk.MINIMAL, FatigueRisk.LOW]

    def test_poor_sleep_low_effectiveness(self) -> None:
        """Poor sleep should yield lower effectiveness."""
        result = predict_fatigue(
            sleep_hours_last_night=4.0,
            sleep_quality=0.4,
            hours_awake=16.0,
            current_hour=3,
        )
        assert result.current_effectiveness < 80
        assert result.sleep_debt_hours > 0

    def test_fatigue_has_predictions(self) -> None:
        """Fatigue should have 4h, 8h, 24h predictions."""
        result = predict_fatigue(
            sleep_hours_last_night=7.0,
            sleep_quality=0.7,
            hours_awake=8.0,
            current_hour=15,
        )
        assert result.predicted_effectiveness_4h > 0
        assert result.predicted_effectiveness_8h > 0
        assert result.predicted_effectiveness_24h > 0

    def test_fatigue_has_performance_curve(self) -> None:
        """Fatigue should have performance curve data."""
        result = predict_fatigue(
            sleep_hours_last_night=7.0,
            sleep_quality=0.7,
            hours_awake=8.0,
            current_hour=15,
        )
        assert len(result.performance_curve) > 0
        for hour, perf in result.performance_curve:
            assert 0 <= hour <= 24
            assert 0 < perf <= 100


class TestPersonalizedHRVAnalysis:
    """Tests for personalized HRV analysis."""

    def test_hrv_analysis_basic(self) -> None:
        """Basic HRV analysis should return valid indices."""
        result = analyze_hrv_personalized(
            hrv_metrics={"rmssd_ms": 35.0, "sdnn_ms": 50.0, "pnn50": 15.0},
            age=40,
            sex="male",
        )
        assert 0 <= result.parasympathetic_index <= 10
        assert result.stress_index >= 0
        assert result.age_group is not None

    def test_hrv_analysis_female(self) -> None:
        """HRV analysis should work for female users."""
        result = analyze_hrv_personalized(
            hrv_metrics={"rmssd_ms": 40.0, "hf_power": 800.0},
            age=35,
            sex="female",
        )
        assert result.age_group == "30-39"
        assert result.overall_status is not None

    def test_hrv_analysis_has_interpretation(self) -> None:
        """HRV analysis should have interpretation text."""
        result = analyze_hrv_personalized(
            hrv_metrics={"rmssd_ms": 35.0},
            age=40,
            sex="male",
        )
        assert len(result.interpretation) > 0
        assert result.autonomic_balance is not None


class TestPerformanceForecast:
    """Tests for performance forecasting."""

    def test_forecast_has_hourly_data(self) -> None:
        """Forecast should have hourly predictions."""
        result = generate_performance_forecast(
            current_hour=10,
            sleep_hours_last_night=7.0,
        )
        assert len(result.hourly_forecast) > 0
        assert result.peak_performance_time is not None
        assert result.low_performance_time is not None

    def test_forecast_identifies_peak_low(self) -> None:
        """Forecast should identify peak and low performance times."""
        result = generate_performance_forecast(
            current_hour=8,
            sleep_hours_last_night=8.0,
        )
        # Peak and low should be different
        assert result.peak_performance_time != result.low_performance_time

    def test_forecast_has_recommendations(self) -> None:
        """Forecast should have recommendations."""
        result = generate_performance_forecast(
            current_hour=10,
            sleep_hours_last_night=7.0,
        )
        assert len(result.recommendations) > 0


class TestRunAllTools:
    """Tests for run_all_profile_tools convenience function."""

    def test_run_all_returns_all_tools(self) -> None:
        """Run all tools should return results for all available tools."""
        results = run_all_profile_tools(
            age=40,
            sex="male",
            weight_kg=80.0,
            height_cm=175.0,
            rmssd_ms=35.0,
            hrv_metrics={"rmssd_ms": 35.0, "sdnn_ms": 50.0},
            sleep_hours=7.0,
            sleep_quality=0.7,
            hours_awake=8.0,
            current_hour=15,
        )
        assert "recovery_score" in results
        assert "training_readiness" in results
        assert "fatigue_prediction" in results
        assert "hrv_analysis" in results
        assert "performance_forecast" in results
        assert "operational_performance" in results
        assert len(results.get("tools_available", [])) >= 4

    def test_run_all_without_hrv(self) -> None:
        """Run all tools should work without HRV metrics."""
        results = run_all_profile_tools(
            age=40,
            sex="male",
            weight_kg=80.0,
            height_cm=175.0,
            sleep_hours=7.0,
            current_hour=15,
        )
        # Should still have fatigue and forecast
        assert "fatigue_prediction" in results
        assert "performance_forecast" in results
        assert "operational_performance" in results

    def test_run_all_has_timestamp(self) -> None:
        """Results should have timestamp."""
        results = run_all_profile_tools(
            age=40,
            sex="male",
            weight_kg=80.0,
            height_cm=175.0,
        )
        assert "generated_at" in results
        assert "user_context" in results


class TestOperationalPerformance:
    """Tests for fused operational performance predictor."""

    def test_operational_performance_bounds(self) -> None:
        """Score should be bounded and provide scheduling fields."""
        result = predict_operational_performance(
            age=35,
            sex="male",
            rmssd_ms=35.0,
            hrv_metrics={"rmssd_ms": 35.0, "sdnn_ms": 50.0, "pnn50": 12.0},
            sleep_hours_last_night=7.0,
            sleep_quality=0.7,
            hours_awake=6.0,
            current_hour=10,
            chronotype_offset=0.0,
            resting_hr=60.0,
            workload_intensity=0.5,
        )
        assert 0.0 <= result.readiness_score <= 100.0
        assert isinstance(result.readiness_level, OperationalReadinessLevel)
        assert isinstance(result.readiness_label, str)
        # Scheduling fields may be None if curve is too short, but should exist
        assert hasattr(result, "best_2h_window_start")
        assert hasattr(result, "worst_2h_window_start")

    def test_operational_performance_degrades_with_poor_sleep(self) -> None:
        """Severe sleep restriction should reduce readiness vs good sleep (all else equal)."""
        good = predict_operational_performance(
            age=35,
            sex="male",
            rmssd_ms=35.0,
            hrv_metrics={"rmssd_ms": 35.0, "sdnn_ms": 50.0, "pnn50": 12.0},
            sleep_hours_last_night=8.0,
            sleep_quality=0.9,
            hours_awake=4.0,
            current_hour=11,
            chronotype_offset=0.0,
            resting_hr=60.0,
            workload_intensity=0.3,
        )
        poor = predict_operational_performance(
            age=35,
            sex="male",
            rmssd_ms=35.0,
            hrv_metrics={"rmssd_ms": 35.0, "sdnn_ms": 50.0, "pnn50": 12.0},
            sleep_hours_last_night=4.0,
            sleep_quality=0.4,
            hours_awake=14.0,
            current_hour=3,
            chronotype_offset=0.0,
            resting_hr=60.0,
            workload_intensity=0.3,
        )
        assert poor.readiness_score <= good.readiness_score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
