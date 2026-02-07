# Author: Dr Diego Malpica MD
"""Tests for app/physiological_sms.py — BP/temperature modifiers and SMS matrices.

Covers:
- Blood pressure classification (all categories + boundary values)
- Temperature classification (all categories + boundary values)
- EVA SMS risk classification
- Military flight SMS risk classification
- Heatmap data builders
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# Ensure app directory is on path
_APP_DIR = Path(__file__).resolve().parents[1] / "app"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from physiological_sms import (
    BPClassification,
    TemperatureClassification,
    SMSClassification,
    compute_bp_readiness_modifier,
    compute_temperature_readiness_modifier,
    classify_eva_risk,
    classify_flight_risk,
    build_eva_sms_heatmap_data,
    build_flight_sms_heatmap_data,
)


# ---------------------------------------------------------------------------
# Blood Pressure Modifier Tests
# ---------------------------------------------------------------------------


class TestBPModifier:
    """Tests for compute_bp_readiness_modifier."""

    def test_none_inputs(self) -> None:
        result = compute_bp_readiness_modifier(None, None)
        assert result.category == "Unknown"
        assert result.modifier == 0.0
        assert result.disqualifying is False

    def test_none_sbp_only(self) -> None:
        result = compute_bp_readiness_modifier(None, 80)
        assert result.category == "Unknown"

    def test_optimal(self) -> None:
        result = compute_bp_readiness_modifier(110, 70)
        assert result.category == "Optimal"
        assert result.modifier == 2.0
        assert result.disqualifying is False

    def test_elevated(self) -> None:
        result = compute_bp_readiness_modifier(125, 75)
        assert result.category == "Elevated"
        assert result.modifier == 0.0
        assert result.disqualifying is False

    def test_stage1_htn_by_sbp(self) -> None:
        result = compute_bp_readiness_modifier(135, 75)
        assert result.category == "Stage1_HTN"
        assert result.modifier == -2.0
        assert result.disqualifying is False

    def test_stage1_htn_by_dbp(self) -> None:
        result = compute_bp_readiness_modifier(125, 85)
        assert result.category == "Stage1_HTN"
        assert result.modifier == -2.0

    def test_stage2_htn_by_sbp(self) -> None:
        result = compute_bp_readiness_modifier(145, 80)
        assert result.category == "Stage2_HTN"
        assert result.modifier == -4.0
        assert result.disqualifying is True

    def test_stage2_htn_by_dbp(self) -> None:
        result = compute_bp_readiness_modifier(130, 95)
        assert result.category == "Stage2_HTN"
        assert result.modifier == -4.0
        assert result.disqualifying is True

    def test_hypotension_by_sbp(self) -> None:
        result = compute_bp_readiness_modifier(85, 70)
        assert result.category == "Hypotension"
        assert result.modifier == -3.0
        assert result.disqualifying is True

    def test_hypotension_by_dbp(self) -> None:
        result = compute_bp_readiness_modifier(100, 55)
        assert result.category == "Hypotension"
        assert result.modifier == -3.0
        assert result.disqualifying is True

    def test_boundary_optimal_elevated(self) -> None:
        # SBP=119 should be optimal
        result = compute_bp_readiness_modifier(119, 79)
        assert result.category == "Optimal"

        # SBP=120 should be elevated
        result2 = compute_bp_readiness_modifier(120, 79)
        assert result2.category == "Elevated"

    def test_invalid_sbp_raises(self) -> None:
        with pytest.raises(ValueError, match="physiological range"):
            compute_bp_readiness_modifier(20, 80)

    def test_invalid_nan_raises(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            compute_bp_readiness_modifier(float("nan"), 80)


# ---------------------------------------------------------------------------
# Temperature Modifier Tests
# ---------------------------------------------------------------------------


class TestTemperatureModifier:
    """Tests for compute_temperature_readiness_modifier."""

    def test_none_input(self) -> None:
        result = compute_temperature_readiness_modifier(None)
        assert result.category == "Unknown"
        assert result.modifier == 0.0
        assert result.disqualifying is False

    def test_normal(self) -> None:
        result = compute_temperature_readiness_modifier(36.6)
        assert result.category == "Normal"
        assert result.modifier == 0.0
        assert result.disqualifying is False

    def test_low_grade_elevation(self) -> None:
        result = compute_temperature_readiness_modifier(37.5)
        assert result.category == "LowGrade"
        assert result.modifier == -1.0
        assert result.disqualifying is False

    def test_mild_fever(self) -> None:
        result = compute_temperature_readiness_modifier(38.0)
        assert result.category == "MildFever"
        assert result.modifier == -2.0
        assert result.disqualifying is True

    def test_fever(self) -> None:
        result = compute_temperature_readiness_modifier(39.0)
        assert result.category == "Fever"
        assert result.modifier == -3.0
        assert result.disqualifying is True

    def test_mild_hypothermia(self) -> None:
        result = compute_temperature_readiness_modifier(35.5)
        assert result.category == "MildHypothermia"
        assert result.modifier == -1.0
        assert result.disqualifying is False

    def test_hypothermia(self) -> None:
        result = compute_temperature_readiness_modifier(34.5)
        assert result.category == "Hypothermia"
        assert result.modifier == -3.0
        assert result.disqualifying is True

    def test_boundary_normal_low_grade(self) -> None:
        result = compute_temperature_readiness_modifier(37.2)
        assert result.category == "Normal"

        result2 = compute_temperature_readiness_modifier(37.3)
        assert result2.category == "LowGrade"

    def test_invalid_range_raises(self) -> None:
        with pytest.raises(ValueError, match="physiological range"):
            compute_temperature_readiness_modifier(20.0)

    def test_invalid_nan_raises(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            compute_temperature_readiness_modifier(float("nan"))


# ---------------------------------------------------------------------------
# EVA SMS Classification Tests
# ---------------------------------------------------------------------------


class TestEVAClassification:
    """Tests for classify_eva_risk."""

    def _make_bp(self, cat: str = "Optimal", mod: float = 2.0, disq: bool = False) -> BPClassification:
        return BPClassification(category=cat, modifier=mod, rationale="test", disqualifying=disq)

    def _make_temp(self, cat: str = "Normal", mod: float = 0.0, disq: bool = False) -> TemperatureClassification:
        return TemperatureClassification(category=cat, modifier=mod, rationale="test", disqualifying=disq)

    def test_healthy_crew_member(self) -> None:
        result = classify_eva_risk(
            readiness_score=90,
            bp_class=self._make_bp(),
            temp_class=self._make_temp(),
        )
        assert result.activity_type == "EVA"
        assert result.severity == "Negligible"
        assert result.risk_level in ("Acceptable", "Tolerable")
        assert len(result.disqualifiers) == 0

    def test_bp_disqualifier_forces_intolerable(self) -> None:
        result = classify_eva_risk(
            readiness_score=90,
            bp_class=self._make_bp("Stage2_HTN", -4.0, True),
            temp_class=self._make_temp(),
        )
        assert result.risk_level == "Intolerable"
        assert len(result.disqualifiers) >= 1

    def test_temp_disqualifier_forces_intolerable(self) -> None:
        result = classify_eva_risk(
            readiness_score=90,
            bp_class=self._make_bp(),
            temp_class=self._make_temp("Fever", -3.0, True),
        )
        assert result.risk_level == "Intolerable"

    def test_low_readiness(self) -> None:
        result = classify_eva_risk(
            readiness_score=30,
            bp_class=self._make_bp(),
            temp_class=self._make_temp(),
        )
        assert result.severity == "Catastrophic"

    def test_high_psi_adds_risk(self) -> None:
        result = classify_eva_risk(
            readiness_score=80,
            bp_class=self._make_bp(),
            temp_class=self._make_temp(),
            psi_score=85.0,
        )
        assert len(result.disqualifiers) >= 1
        assert result.risk_level == "Intolerable"


# ---------------------------------------------------------------------------
# Flight SMS Classification Tests
# ---------------------------------------------------------------------------


class TestFlightClassification:
    """Tests for classify_flight_risk."""

    def _make_bp(self, cat: str = "Optimal", mod: float = 2.0, disq: bool = False) -> BPClassification:
        return BPClassification(category=cat, modifier=mod, rationale="test", disqualifying=disq)

    def _make_temp(self, cat: str = "Normal", mod: float = 0.0, disq: bool = False) -> TemperatureClassification:
        return TemperatureClassification(category=cat, modifier=mod, rationale="test", disqualifying=disq)

    def test_healthy_pilot(self) -> None:
        result = classify_flight_risk(
            readiness_score=90,
            bp_class=self._make_bp(),
            temp_class=self._make_temp(),
            crew_rest_compliant=True,
        )
        assert result.activity_type == "FLIGHT"
        assert result.severity == "Negligible"
        assert result.risk_level in ("Low", "Medium")
        assert len(result.disqualifiers) == 0

    def test_crew_rest_non_compliant(self) -> None:
        result = classify_flight_risk(
            readiness_score=90,
            bp_class=self._make_bp(),
            temp_class=self._make_temp(),
            crew_rest_compliant=False,
        )
        assert result.risk_level == "High"
        assert any("crew rest" in d.lower() for d in result.disqualifiers)

    def test_g_loc_risk_hypotension(self) -> None:
        result = classify_flight_risk(
            readiness_score=80,
            bp_class=self._make_bp("Hypotension", -3.0, True),
            temp_class=self._make_temp(),
            rmssd_ms=15.0,
        )
        assert result.risk_level == "High"
        assert any("G-LOC" in d for d in result.disqualifiers)

    def test_tachycardia_g_loc_risk(self) -> None:
        result = classify_flight_risk(
            readiness_score=80,
            bp_class=self._make_bp(),
            temp_class=self._make_temp(),
            resting_hr_bpm=110,
        )
        assert any("tachycardia" in d.lower() for d in result.disqualifiers)


# ---------------------------------------------------------------------------
# Heatmap Data Builder Tests
# ---------------------------------------------------------------------------


class TestHeatmapBuilders:
    """Tests for build_eva_sms_heatmap_data and build_flight_sms_heatmap_data."""

    def test_eva_matrix_shape(self) -> None:
        data = build_eva_sms_heatmap_data()
        assert len(data["severity_labels"]) == 5
        assert len(data["likelihood_labels"]) == 5
        assert len(data["data"]) == 25  # 5x5
        assert len(data["risk_levels"]) == 4
        assert len(data["risk_colors"]) == 4

    def test_flight_matrix_shape(self) -> None:
        data = build_flight_sms_heatmap_data()
        assert len(data["severity_labels"]) == 4
        assert len(data["likelihood_labels"]) == 5
        assert len(data["data"]) == 20  # 4x5
        assert len(data["risk_levels"]) == 4

    def test_eva_data_values_in_range(self) -> None:
        data = build_eva_sms_heatmap_data()
        for point in data["data"]:
            assert 0 <= point[2] <= 3

    def test_flight_data_values_in_range(self) -> None:
        data = build_flight_sms_heatmap_data()
        for point in data["data"]:
            assert 0 <= point[2] <= 3
