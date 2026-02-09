# Author: Dr Diego Malpica MD
"""Tests for hydration_thermoregulation module.

Validates scientific equations against published reference values from:
- Sawka et al. (2007) ACSM Position Stand
- Cheuvront & Kenefick (2014) Comprehensive Physiology
- Moran et al. (1998) Physiological Strain Index
- Gonzalez-Alonso et al. (1999) Core temperature model
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# Ensure app/ is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from hydration_thermoregulation import (
    SweatRateEstimate,
    DehydrationEstimate,
    CoreTemperatureEstimate,
    PhysiologicalStrainIndex,
    PerformanceDecrement,
    HydrationThermoregulationAssessment,
    estimate_sweat_rate,
    estimate_dehydration,
    estimate_core_temperature,
    compute_physiological_strain_index,
    compute_performance_decrement,
    compute_hydration_thermoregulation_assessment,
)


# ---------------------------------------------------------------------------
# Sweat Rate Tests
# ---------------------------------------------------------------------------


class TestEstimateSweatRate:
    """Tests for estimate_sweat_rate function."""

    def test_sedentary_thermoneutral(self) -> None:
        """Sedentary at thermoneutral should have minimal sweat rate."""
        result = estimate_sweat_rate("sedentary", wbgt_c=22.0)
        assert isinstance(result, SweatRateEstimate)
        # Sedentary base = 100 mL/h, acclimatized * 1.12 = 112 mL/h
        assert 50 <= result.sweat_rate_ml_h <= 200
        assert result.activity_level == "sedentary"
        assert result.heat_adjustment_factor == 1.0

    def test_moderate_thermoneutral(self) -> None:
        """Moderate exercise at thermoneutral: ~600-700 mL/h."""
        result = estimate_sweat_rate("moderate", wbgt_c=22.0)
        assert 500 <= result.sweat_rate_ml_h <= 800

    def test_hard_exercise_hot(self) -> None:
        """Hard exercise in hot conditions: >1500 mL/h."""
        result = estimate_sweat_rate("hard", wbgt_c=35.0)
        assert result.sweat_rate_ml_h > 1500
        assert result.heat_adjustment_factor > 1.0

    def test_heat_factor_increases_with_wbgt(self) -> None:
        """Higher WBGT should increase sweat rate."""
        sr_cool = estimate_sweat_rate("moderate", wbgt_c=20.0)
        sr_hot = estimate_sweat_rate("moderate", wbgt_c=35.0)
        assert sr_hot.sweat_rate_ml_h > sr_cool.sweat_rate_ml_h

    def test_body_mass_scaling(self) -> None:
        """Heavier individuals should have higher sweat rate."""
        sr_light = estimate_sweat_rate("moderate", wbgt_c=28.0, body_mass_kg=50.0)
        sr_heavy = estimate_sweat_rate("moderate", wbgt_c=28.0, body_mass_kg=100.0)
        assert sr_heavy.sweat_rate_ml_h > sr_light.sweat_rate_ml_h

    def test_invalid_activity_raises(self) -> None:
        """Invalid activity level should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid activity_level"):
            estimate_sweat_rate("invalid_activity", wbgt_c=22.0)

    def test_invalid_wbgt_raises(self) -> None:
        """Non-finite WBGT should raise ValueError."""
        with pytest.raises(ValueError, match="wbgt_c must be"):
            estimate_sweat_rate("moderate", wbgt_c=float("nan"))

    def test_sweat_rate_capped(self) -> None:
        """Sweat rate should be capped at physiological ceiling."""
        result = estimate_sweat_rate("very_hard", wbgt_c=45.0, body_mass_kg=120.0)
        assert result.sweat_rate_ml_h <= 3500

    def test_all_activity_levels(self) -> None:
        """All activity levels should produce valid results."""
        for level in ["sedentary", "light", "moderate", "vigorous", "hard", "very_hard"]:
            result = estimate_sweat_rate(level, wbgt_c=28.0)
            assert result.sweat_rate_ml_h > 0
            assert result.sweat_rate_l_h > 0


# ---------------------------------------------------------------------------
# Dehydration Tests
# ---------------------------------------------------------------------------


class TestEstimateDehydration:
    """Tests for estimate_dehydration function."""

    def test_no_activity(self) -> None:
        """Zero duration should produce no dehydration."""
        result = estimate_dehydration(600, 0.0, 70.0)
        assert result.body_mass_loss_pct == 0.0
        assert result.dehydration_category == "Euhydrated"

    def test_moderate_exercise_1h(self) -> None:
        """1h moderate exercise without fluid intake: ~0.86% loss."""
        result = estimate_dehydration(600, 1.0, 70.0)
        expected_pct = (600 / 70000) * 100  # = 0.857%
        assert abs(result.body_mass_loss_pct - expected_pct) < 0.1
        assert result.dehydration_category == "Euhydrated"

    def test_hard_exercise_2h_no_fluids(self) -> None:
        """2h hard exercise without fluids: significant dehydration."""
        result = estimate_dehydration(1500, 2.0, 70.0)
        # 3000 mL / 70000 g = 4.29% BM loss
        assert result.body_mass_loss_pct > 4.0
        assert result.dehydration_category == "Significant Dehydration"
        assert result.risk_level in ("High", "Very High")

    def test_fluid_replacement_reduces_deficit(self) -> None:
        """Adequate fluid intake should reduce dehydration."""
        no_fluid = estimate_dehydration(1000, 2.0, 70.0)
        with_fluid = estimate_dehydration(1000, 2.0, 70.0, fluid_intake_ml_h=800.0)
        assert with_fluid.body_mass_loss_pct < no_fluid.body_mass_loss_pct

    def test_full_replacement(self) -> None:
        """Full fluid replacement should yield euhydrated state."""
        result = estimate_dehydration(600, 1.0, 70.0, fluid_intake_ml_h=600.0)
        assert result.body_mass_loss_pct == 0.0
        assert result.dehydration_category == "Euhydrated"

    def test_invalid_negative_duration(self) -> None:
        """Negative duration should raise ValueError."""
        with pytest.raises(ValueError, match="duration_hours"):
            estimate_dehydration(600, -1.0, 70.0)


# ---------------------------------------------------------------------------
# Core Temperature Tests
# ---------------------------------------------------------------------------


class TestEstimateCoreTemperature:
    """Tests for estimate_core_temperature function."""

    def test_sedentary_thermoneutral(self) -> None:
        """Sedentary at thermoneutral should stay near baseline."""
        result = estimate_core_temperature("sedentary", 1.0, wbgt_c=22.0)
        assert abs(result.core_temp_c - 37.0) < 0.3

    def test_exercise_raises_temp(self) -> None:
        """Vigorous exercise should raise core temperature."""
        result = estimate_core_temperature("vigorous", 1.0, wbgt_c=22.0)
        assert result.core_temp_c > 37.5

    def test_heat_stress_raises_temp(self) -> None:
        """Hot WBGT should contribute to temperature rise."""
        cool = estimate_core_temperature("moderate", 1.0, wbgt_c=22.0)
        hot = estimate_core_temperature("moderate", 1.0, wbgt_c=40.0)
        assert hot.core_temp_c > cool.core_temp_c

    def test_dehydration_raises_temp(self) -> None:
        """Dehydration should increase core temperature."""
        hydrated = estimate_core_temperature("moderate", 1.0, wbgt_c=28.0, dehydration_pct=0.0)
        dehydrated = estimate_core_temperature("moderate", 1.0, wbgt_c=28.0, dehydration_pct=4.0)
        assert dehydrated.core_temp_c > hydrated.core_temp_c
        # 4% dehydration should add ~0.72 C (0.18 * 4)
        delta = dehydrated.core_temp_c - hydrated.core_temp_c
        assert abs(delta - 0.72) < 0.1

    def test_risk_classification(self) -> None:
        """Appropriate risk categories for different temperatures."""
        normal = estimate_core_temperature("sedentary", 0.5, wbgt_c=22.0)
        assert normal.risk_category == "Normal"

        hot_exercise = estimate_core_temperature("hard", 1.5, wbgt_c=38.0, dehydration_pct=3.0)
        assert hot_exercise.risk_category in (
            "Mild Hyperthermia",
            "Moderate Hyperthermia",
            "Severe Hyperthermia",
        )


# ---------------------------------------------------------------------------
# Physiological Strain Index Tests
# ---------------------------------------------------------------------------


class TestPhysiologicalStrainIndex:
    """Tests for compute_physiological_strain_index function."""

    def test_resting_baseline(self) -> None:
        """At resting values, PhSI should be 0."""
        result = compute_physiological_strain_index(
            core_temp_c=37.0,
            heart_rate_bpm=70.0,
            resting_hr_bpm=70.0,
        )
        assert result.phsi_value == 0.0
        assert result.strain_category == "Low"

    def test_moderate_strain(self) -> None:
        """Elevated temp and HR should produce moderate PhSI."""
        result = compute_physiological_strain_index(
            core_temp_c=38.5,
            heart_rate_bpm=150.0,
        )
        assert 4.0 <= result.phsi_value <= 8.0

    def test_max_strain(self) -> None:
        """Extreme values should approach PhSI 10."""
        result = compute_physiological_strain_index(
            core_temp_c=40.5,
            heart_rate_bpm=200.0,
            max_hr_bpm=200.0,
        )
        assert result.phsi_value >= 9.0
        assert result.strain_category == "Very High"

    def test_phsi_bounded_0_10(self) -> None:
        """PhSI should always be in [0, 10]."""
        result = compute_physiological_strain_index(
            core_temp_c=42.0,
            heart_rate_bpm=250.0,
            max_hr_bpm=250.0,
        )
        assert 0.0 <= result.phsi_value <= 10.0


# ---------------------------------------------------------------------------
# Performance Decrement Tests
# ---------------------------------------------------------------------------


class TestPerformanceDecrement:
    """Tests for compute_performance_decrement function."""

    def test_euhydrated_no_decrement(self) -> None:
        """No dehydration should give 100% performance."""
        result = compute_performance_decrement(0.0)
        assert result.aerobic_performance_pct == 100.0
        assert result.cognitive_performance_pct >= 99.0
        assert result.overall_performance_pct >= 99.0
        assert result.readiness_modifier == 0.0

    def test_2pct_dehydration_decrement(self) -> None:
        """2% dehydration should show measurable performance loss."""
        result = compute_performance_decrement(2.0)
        assert result.aerobic_performance_pct < 100.0
        assert result.cognitive_performance_pct < 100.0
        assert result.readiness_modifier < 0.0

    def test_heat_stress_amplifies(self) -> None:
        """Heat stress should amplify performance decrement."""
        no_heat = compute_performance_decrement(3.0, heat_stress=False)
        with_heat = compute_performance_decrement(3.0, heat_stress=True)
        assert with_heat.overall_performance_pct < no_heat.overall_performance_pct

    def test_severe_dehydration(self) -> None:
        """Severe dehydration (5%) should have significant decrement."""
        result = compute_performance_decrement(5.0, heat_stress=True)
        # At 5% dehydration with heat stress, overall ~80% (aerobic ~77%, cognitive ~77%)
        assert result.overall_performance_pct < 85.0
        assert result.readiness_modifier <= -3.0
        assert result.risk_level == "Very High"

    def test_readiness_modifier_bounded(self) -> None:
        """Readiness modifier should be in [-10, 0]."""
        for d in [0.0, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0]:
            result = compute_performance_decrement(d)
            assert -10.0 <= result.readiness_modifier <= 0.0

    def test_recommendations_present(self) -> None:
        """All dehydration levels should produce recommendations."""
        for d in [0.0, 1.5, 2.5, 4.0]:
            result = compute_performance_decrement(d)
            assert len(result.recommendations) > 0


# ---------------------------------------------------------------------------
# Comprehensive Assessment Tests
# ---------------------------------------------------------------------------


class TestComprehensiveAssessment:
    """Tests for compute_hydration_thermoregulation_assessment."""

    def test_returns_all_fields(self) -> None:
        """Assessment should return all required fields."""
        result = compute_hydration_thermoregulation_assessment()
        assert isinstance(result, HydrationThermoregulationAssessment)
        assert isinstance(result.sweat_rate, SweatRateEstimate)
        assert isinstance(result.dehydration, DehydrationEstimate)
        assert isinstance(result.core_temp, CoreTemperatureEstimate)
        assert isinstance(result.phsi, PhysiologicalStrainIndex)
        assert isinstance(result.performance, PerformanceDecrement)
        assert result.fluid_replacement_ml_h > 0
        assert -10.0 <= result.readiness_modifier <= 0.0

    def test_thermoneutral_low_risk(self) -> None:
        """Thermoneutral sedentary conditions should be low risk."""
        result = compute_hydration_thermoregulation_assessment(
            activity_level="sedentary",
            duration_hours=0.5,
            wbgt_c=22.0,
            fluid_intake_ml_h=200.0,
        )
        assert result.heat_stress_category == "Low"
        assert result.hydration_status == "Well Hydrated"
        assert result.readiness_modifier >= -2.0

    def test_hot_hard_exercise_high_risk(self) -> None:
        """Hard exercise in extreme heat should be high risk."""
        result = compute_hydration_thermoregulation_assessment(
            activity_level="hard",
            duration_hours=2.0,
            wbgt_c=38.0,
            body_mass_kg=70.0,
            fluid_intake_ml_h=0.0,
        )
        assert result.heat_stress_category in ("Very High", "Extreme")
        assert result.hydration_status in ("Significantly Dehydrated", "Severely Dehydrated")
        assert result.readiness_modifier < -3.0

    def test_fluid_replacement_recommendation(self) -> None:
        """Fluid replacement should be ~80% of sweat rate."""
        result = compute_hydration_thermoregulation_assessment(
            activity_level="moderate",
            wbgt_c=30.0,
        )
        expected_rec = min(result.sweat_rate.sweat_rate_ml_h * 0.8, 1200)
        assert abs(result.fluid_replacement_ml_h - expected_rec) < 10

    def test_invalid_duration_raises(self) -> None:
        """Negative duration should raise ValueError."""
        with pytest.raises(ValueError, match="duration_hours"):
            compute_hydration_thermoregulation_assessment(duration_hours=-1.0)

    def test_operational_guidance_not_empty(self) -> None:
        """Operational guidance should always be populated."""
        result = compute_hydration_thermoregulation_assessment()
        assert len(result.operational_guidance) > 0


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_zero_duration(self) -> None:
        """Zero duration should produce baseline values."""
        result = compute_hydration_thermoregulation_assessment(duration_hours=0.0)
        assert result.dehydration.body_mass_loss_pct == 0.0
        assert result.core_temp.core_temp_c <= 37.1

    def test_very_light_person(self) -> None:
        """Very light person should still get valid results."""
        result = estimate_sweat_rate("moderate", wbgt_c=28.0, body_mass_kg=40.0)
        assert result.sweat_rate_ml_h > 0

    def test_very_heavy_person(self) -> None:
        """Very heavy person should have higher sweat rate."""
        result = estimate_sweat_rate("moderate", wbgt_c=28.0, body_mass_kg=150.0)
        assert result.sweat_rate_ml_h > 1000

    def test_extreme_wbgt(self) -> None:
        """Extreme WBGT (50 C) should still produce bounded results."""
        result = compute_hydration_thermoregulation_assessment(
            activity_level="moderate",
            wbgt_c=50.0,
            duration_hours=1.0,
        )
        assert result.core_temp.core_temp_c <= 42.0
        assert result.sweat_rate.sweat_rate_ml_h <= 3500
