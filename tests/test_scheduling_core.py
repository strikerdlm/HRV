"""
Tests for scheduling_core.py - Crew Scheduling Science Layer.

Tests the evidence-based scoring functions, IHPI computation, and GO/NO-GO
decision logic against known thresholds from peer-reviewed literature.

Author: Dr. Diego Leonel Malpica Hincapié, MD
"""

from __future__ import annotations

import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import numpy as np

# Ensure app directory is on path
app_dir = Path(__file__).resolve().parents[1] / "app"
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

from scheduling_core import (
    # Constants
    SAFTE_LOW_RISK_MIN,
    SAFTE_CAUTION_MIN,
    SAFTE_HIGH_RISK_MIN,
    NASA_EVA_VO2MAX_MIN_ML_KG_MIN,
    EA_OPTIMAL_KCAL_KG_FFM,
    EA_LOW_THRESHOLD_KCAL_KG_FFM,
    # Utilities
    clamp,
    kcal_per_hour_from_met,
    watts_from_kcal_per_hour,
    kcal_from_met_duration,
    # Scoring functions
    score_safte,
    score_kss,
    score_pvt_lapses_3min,
    score_hrv_z,
    score_hydration,
    score_energy_availability,
    score_circadian_alignment,
    score_task_specific,
    # IHPI
    IHPISubscores,
    compute_ihpi,
    DEFAULT_IHPI_WEIGHTS,
    # GO/NO-GO
    GONOGOStatus,
    eva_go_nogo,
    # Activity definitions
    ALL_ACTIVITIES,
    FIXED_ACTIVITIES,
    VARIABLE_ACTIVITIES,
    # Crew
    CrewPhysiologicalStatus,
    CrewMember,
    RiskLevel,
    # Forecast helpers
    SAFTEForecastPoint,
    PerformanceForecast,
    build_hourly_safte_series,
)


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_clamp_within_bounds(self):
        """Test clamp returns value when within bounds."""
        assert clamp(5.0, 0.0, 10.0) == 5.0

    def test_clamp_below_min(self):
        """Test clamp returns min when value is below."""
        assert clamp(-5.0, 0.0, 10.0) == 0.0

    def test_clamp_above_max(self):
        """Test clamp returns max when value is above."""
        assert clamp(15.0, 0.0, 10.0) == 10.0

    def test_kcal_per_hour_from_met(self):
        """Test MET to kcal/hr conversion."""
        # 1 MET = 1 kcal/kg/hour
        result = kcal_per_hour_from_met(met=1.0, mass_kg=70.0)
        assert result == 70.0
        
        # 7 METs (moderate cycling) for 70 kg person
        result = kcal_per_hour_from_met(met=7.0, mass_kg=70.0)
        assert result == 490.0

    def test_watts_from_kcal_per_hour(self):
        """Test kcal/hr to Watts conversion."""
        # 1 kcal = 4184 J; 1 hour = 3600 s
        # 100 kcal/hr = 100 * 4184 / 3600 = 116.22 W
        result = watts_from_kcal_per_hour(100.0)
        assert abs(result - 116.22) < 0.1

    def test_kcal_from_met_duration(self):
        """Test total kcal calculation from MET and duration."""
        # 7 METs, 70 kg, 60 minutes = 490 kcal
        result = kcal_from_met_duration(met=7.0, mass_kg=70.0, minutes=60.0)
        assert result == 490.0
        
        # 30 minutes = 245 kcal
        result = kcal_from_met_duration(met=7.0, mass_kg=70.0, minutes=30.0)
        assert result == 245.0


class TestSAFTEScoring:
    """Tests for SAFTE effectiveness scoring."""

    def test_score_safte_optimal(self):
        """Test SAFTE score at optimal level (≥90%)."""
        assert score_safte(100.0) == 1.0
        assert score_safte(95.0) == 1.0
        assert score_safte(90.0) == 1.0

    def test_score_safte_critical(self):
        """Test SAFTE score at critical level (≤70%)."""
        assert score_safte(70.0) == 0.0
        assert score_safte(60.0) == 0.0
        assert score_safte(50.0) == 0.0

    def test_score_safte_intermediate(self):
        """Test SAFTE score in intermediate range (70-90%)."""
        # 80% should be midpoint = 0.5
        assert abs(score_safte(80.0) - 0.5) < 0.01
        
        # 85% should be 0.75
        assert abs(score_safte(85.0) - 0.75) < 0.01


class TestKSSScoring:
    """Tests for Karolinska Sleepiness Scale scoring."""

    def test_score_kss_alert(self):
        """Test KSS score for alert states (1-5)."""
        assert score_kss(1.0) == 1.0
        assert score_kss(3.0) == 1.0
        assert score_kss(5.0) == 1.0

    def test_score_kss_nogo(self):
        """Test KSS score for NO-GO states (8-9)."""
        assert score_kss(8.0) == 0.0
        assert score_kss(9.0) == 0.0

    def test_score_kss_caution(self):
        """Test KSS score for caution states (6-7)."""
        # Linear interpolation between 5→8 maps to 1→0
        # KSS 6 should be ~0.67, KSS 7 should be ~0.33
        assert 0.6 < score_kss(6.0) < 0.7
        assert 0.3 < score_kss(7.0) < 0.4


class TestPVTScoring:
    """Tests for Psychomotor Vigilance Task scoring."""

    def test_score_pvt_high_performance(self):
        """Test PVT score for high-performance band (≤10 lapses)."""
        assert score_pvt_lapses_3min(0) == 1.0
        assert score_pvt_lapses_3min(5) == 1.0
        assert score_pvt_lapses_3min(10) == 1.0

    def test_score_pvt_low_performance(self):
        """Test PVT score for low-performance band (≥20 lapses)."""
        assert score_pvt_lapses_3min(20) == 0.0
        assert score_pvt_lapses_3min(25) == 0.0

    def test_score_pvt_intermediate(self):
        """Test PVT score for intermediate performance."""
        # 15 lapses should be midpoint = 0.5
        assert abs(score_pvt_lapses_3min(15) - 0.5) < 0.01


class TestHRVScoring:
    """Tests for HRV lnRMSSD z-score scoring."""

    def test_score_hrv_normal(self):
        """Test HRV score for normal z-scores (≥-0.5)."""
        assert score_hrv_z(0.0) == 1.0
        assert score_hrv_z(1.0) == 1.0
        assert score_hrv_z(-0.5) == 1.0

    def test_score_hrv_poor(self):
        """Test HRV score for poor z-scores (≤-2.0)."""
        assert score_hrv_z(-2.0) == 0.0
        assert score_hrv_z(-3.0) == 0.0

    def test_score_hrv_caution(self):
        """Test HRV score for caution z-scores (-0.5 to -2.0)."""
        # -1.25 should be midpoint ≈ 0.5
        assert 0.4 < score_hrv_z(-1.25) < 0.6


class TestHydrationScoring:
    """Tests for hydration status scoring."""

    def test_score_hydration_euhydrated(self):
        """Test hydration score for euhydrated state."""
        # 0% body mass loss, USG < 1.020
        assert score_hydration(0.0, 1.010) == 1.0
        
        # 0.5% loss, still okay
        assert score_hydration(-0.5, 1.015) == 1.0

    def test_score_hydration_dehydrated(self):
        """Test hydration score for dehydrated state."""
        # >2% body mass loss
        assert score_hydration(-2.5, None) == 0.0
        
        # USG ≥ 1.030
        assert score_hydration(0.0, 1.035) == 0.0

    def test_score_hydration_conservative(self):
        """Test hydration uses conservative (min) of both metrics."""
        # Body mass OK but USG high
        result = score_hydration(-0.5, 1.028)
        assert result < 1.0  # Should use lower USG score


class TestEnergyAvailabilityScoring:
    """Tests for Energy Availability scoring."""

    def test_score_ea_optimal(self):
        """Test EA score at optimal level (≥45)."""
        assert score_energy_availability(45.0) == 1.0
        assert score_energy_availability(50.0) == 1.0

    def test_score_ea_low(self):
        """Test EA score at low level (≤30)."""
        assert score_energy_availability(30.0) == 0.0
        assert score_energy_availability(25.0) == 0.0

    def test_score_ea_intermediate(self):
        """Test EA score at intermediate level."""
        # 37.5 should be midpoint = 0.5
        assert abs(score_energy_availability(37.5) - 0.5) < 0.01


class TestSAFTEPlotHelpers:
    """Tests for deterministic SAFTE plotting helpers (timebase correctness)."""

    def test_build_hourly_safte_series_aligns_to_next_hour(self) -> None:
        """Samples should start at the next whole-hour boundary after forecast_start."""
        start = datetime(2025, 1, 1, 12, 34, 0)
        p0 = SAFTEForecastPoint(
            timestamp=start,
            effectiveness=90.0,
            sleep_reservoir=0.0,
            circadian_phase=0.0,
            sleep_inertia=0.0,
            risk_level=RiskLevel.LOW,
        )
        p1 = SAFTEForecastPoint(
            timestamp=start + timedelta(hours=1),
            effectiveness=80.0,
            sleep_reservoir=0.0,
            circadian_phase=0.0,
            sleep_inertia=0.0,
            risk_level=RiskLevel.MODERATE,
        )
        p2 = SAFTEForecastPoint(
            timestamp=start + timedelta(hours=2),
            effectiveness=70.0,
            sleep_reservoir=0.0,
            circadian_phase=0.0,
            sleep_inertia=0.0,
            risk_level=RiskLevel.HIGH,
        )
        forecast = PerformanceForecast(
            crew_id="crew-x",
            forecast_start=start,
            forecast_points=[p0, p1, p2],
        )

        x_labels, y_vals, timestamps = build_hourly_safte_series(
            forecast,
            horizon_hours=2,
            align_to_next_hour=True,
            time_label_format="%Y-%m-%d %H:%M",
        )

        assert timestamps == [
            datetime(2025, 1, 1, 13, 0, 0),
            datetime(2025, 1, 1, 14, 0, 0),
        ]
        assert x_labels == ["2025-01-01 13:00", "2025-01-01 14:00"]
        # Interpolated at +26 minutes into each hour: expected 85.7 then 75.7
        assert y_vals == [85.7, 75.7]


class TestCircadianAlignment:
    """Tests for circadian alignment scoring."""

    def test_score_circadian_aligned(self):
        """Test circadian score when well-aligned (≤1h offset)."""
        assert score_circadian_alignment(0.0) == 1.0
        assert score_circadian_alignment(0.5) == 1.0
        assert score_circadian_alignment(1.0) == 1.0

    def test_score_circadian_misaligned(self):
        """Test circadian score when severely misaligned (≥6h offset)."""
        assert score_circadian_alignment(6.0) == 0.0
        assert score_circadian_alignment(8.0) == 0.0

    def test_score_circadian_intermediate(self):
        """Test circadian score at intermediate offset."""
        # 3.5h offset should be midpoint = 0.5
        assert abs(score_circadian_alignment(3.5) - 0.5) < 0.01


class TestTaskSpecificScoring:
    """Tests for task-specific readiness scoring."""

    def test_score_task_vo2max_met(self):
        """Test task score when VO2max requirement is met."""
        # VO2max ≥ 32.9 and full recovery
        assert score_task_specific(40.0, 72.0) == 1.0

    def test_score_task_vo2max_not_met(self):
        """Test task score when VO2max requirement is not met."""
        # VO2max < 32.9
        assert score_task_specific(30.0, 72.0) == 0.0

    def test_score_task_recovery_insufficient(self):
        """Test task score with insufficient EVA recovery time."""
        # Good VO2max but only 12h since last EVA
        result = score_task_specific(40.0, 12.0)
        assert result == 0.0

    def test_score_task_recovery_minimum(self):
        """Test task score at minimum recovery time (24h)."""
        result = score_task_specific(40.0, 24.0)
        assert result == 0.0  # At boundary, recovery score = 0


class TestIHPIComputation:
    """Tests for Integrated Human Performance Indicator."""

    def test_compute_ihpi_optimal(self):
        """Test IHPI computation with all optimal subscores."""
        subscores = IHPISubscores(
            safte=1.0,
            pvt=1.0,
            circadian=1.0,
            hrv=1.0,
            hydration=1.0,
            energy_availability=1.0,
            subjective=1.0,
            task_specific=1.0,
        )
        ihpi = compute_ihpi(subscores)
        assert ihpi == 100.0

    def test_compute_ihpi_critical_zero(self):
        """Test IHPI with critical domain at zero triggers hard cap."""
        # SAFTE at zero should cap entire IHPI to 0
        subscores = IHPISubscores(
            safte=0.0,
            pvt=1.0,
            circadian=1.0,
            hrv=1.0,
            hydration=1.0,
            energy_availability=1.0,
            subjective=1.0,
            task_specific=1.0,
        )
        ihpi = compute_ihpi(subscores)
        assert ihpi == 0.0
        
        # PVT at zero should also cap
        subscores = IHPISubscores(
            safte=1.0,
            pvt=0.0,
            circadian=1.0,
            hrv=1.0,
            hydration=1.0,
            energy_availability=1.0,
            subjective=1.0,
            task_specific=1.0,
        )
        ihpi = compute_ihpi(subscores)
        assert ihpi == 0.0

    def test_compute_ihpi_weights_sum(self):
        """Test that default IHPI weights sum to 1.0."""
        total = sum(DEFAULT_IHPI_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001


class TestEVAGoNoGo:
    """Tests for EVA GO/NO-GO decision logic."""

    def test_eva_go_all_clear(self):
        """Test EVA GO when all gates pass and IHPI high."""
        result = eva_go_nogo(
            safte_eff=92.0,
            kss=3.0,
            sleep_last_24h_h=8.0,
            time_awake_h=10.0,
            body_mass_change_pct=-0.5,
            usg=1.015,
            pvt_lapses_3min=5,
            ihpi_value=88.0,
            vo2max=40.0,
            hours_since_last_eva=72.0,
            energy_availability=45.0,
        )
        assert result.status == GONOGOStatus.GO

    def test_eva_nogo_low_safte(self):
        """Test EVA NO-GO when SAFTE below critical threshold."""
        result = eva_go_nogo(
            safte_eff=65.0,  # Below 70% critical threshold
            kss=3.0,
            sleep_last_24h_h=8.0,
            time_awake_h=10.0,
            body_mass_change_pct=-0.5,
            usg=1.015,
            pvt_lapses_3min=5,
            ihpi_value=60.0,
            vo2max=40.0,
            hours_since_last_eva=72.0,
        )
        assert result.status == GONOGOStatus.NOGO
        assert any("SAFTE" in r for r in result.reasons)

    def test_eva_nogo_high_kss(self):
        """Test EVA NO-GO when KSS indicates severe sleepiness."""
        result = eva_go_nogo(
            safte_eff=92.0,
            kss=8.0,  # Severe sleepiness
            sleep_last_24h_h=8.0,
            time_awake_h=10.0,
            body_mass_change_pct=-0.5,
            usg=1.015,
            pvt_lapses_3min=5,
            ihpi_value=70.0,
            vo2max=40.0,
            hours_since_last_eva=72.0,
        )
        assert result.status == GONOGOStatus.NOGO
        assert any("KSS" in r for r in result.reasons)

    def test_eva_nogo_low_vo2max(self):
        """Test EVA NO-GO when VO2max below NASA requirement."""
        result = eva_go_nogo(
            safte_eff=92.0,
            kss=3.0,
            sleep_last_24h_h=8.0,
            time_awake_h=10.0,
            body_mass_change_pct=-0.5,
            usg=1.015,
            pvt_lapses_3min=5,
            ihpi_value=85.0,
            vo2max=30.0,  # Below 32.9 requirement
            hours_since_last_eva=72.0,
        )
        assert result.status == GONOGOStatus.NOGO
        assert any("VO2max" in r for r in result.reasons)

    def test_eva_go_with_mitigation(self):
        """Test EVA GO-with-mitigation when IHPI is 75-84."""
        result = eva_go_nogo(
            safte_eff=85.0,
            kss=4.0,
            sleep_last_24h_h=7.0,
            time_awake_h=12.0,
            body_mass_change_pct=-1.0,
            usg=1.020,
            pvt_lapses_3min=8,
            ihpi_value=78.0,  # 75-84 range
            vo2max=40.0,
            hours_since_last_eva=72.0,
        )
        assert result.status == GONOGOStatus.GO_WITH_MITIGATION


class TestActivityDefinitions:
    """Tests for activity definitions."""

    def test_fixed_activities_exist(self):
        """Test that required fixed activities are defined."""
        required = {"briefing", "breakfast", "lunch", "dinner", "exercise", "sleep", "hygiene"}
        fixed_ids = {a.id for a in FIXED_ACTIVITIES}
        assert required.issubset(fixed_ids)

    def test_variable_activities_exist(self):
        """Test that variable activities are defined."""
        required = {"lab_work", "eva"}
        variable_ids = {a.id for a in VARIABLE_ACTIVITIES}
        assert required.issubset(variable_ids)

    def test_all_activities_combined(self):
        """Test that ALL_ACTIVITIES contains all defined activities."""
        total = len(FIXED_ACTIVITIES) + len(VARIABLE_ACTIVITIES)
        assert len(ALL_ACTIVITIES) == total

    def test_eva_met_value_realistic(self):
        """Test EVA MET value is in realistic NASA range (2-7)."""
        eva = ALL_ACTIVITIES.get("eva")
        assert eva is not None
        assert 2.0 <= eva.met_value <= 7.0

    def test_met_sources_documented(self):
        """Test that all activities have documented MET sources."""
        for activity in ALL_ACTIVITIES.values():
            assert activity.met_source, f"{activity.id} missing MET source"


class TestCrewPhysiologicalStatus:
    """Tests for crew physiological status."""

    def test_lnrmssd_zscore_calculation(self):
        """Test lnRMSSD z-score calculation."""
        status = CrewPhysiologicalStatus(
            crew_id="test",
            timestamp=None,  # type: ignore
            lnrmssd_current=3.8,
            lnrmssd_baseline_mean=3.5,
            lnrmssd_baseline_sd=0.3,
        )
        # z = (3.8 - 3.5) / 0.3 = 1.0
        assert abs(status.lnrmssd_zscore - 1.0) < 0.001

    def test_lnrmssd_zscore_zero_sd(self):
        """Test lnRMSSD z-score with zero SD returns 0."""
        status = CrewPhysiologicalStatus(
            crew_id="test",
            timestamp=None,  # type: ignore
            lnrmssd_current=3.8,
            lnrmssd_baseline_mean=3.5,
            lnrmssd_baseline_sd=0.0,
        )
        assert status.lnrmssd_zscore == 0.0


class TestCrewMember:
    """Tests for crew member class."""

    def test_crew_risk_level_low(self):
        """Test crew risk level classification as LOW."""
        crew = CrewMember(
            crew_id="test",
            name="Test Crew",
            role="Test",
            age_years=35,
            sex="male",
            weight_kg=75,
            height_cm=175,
            vo2max_ml_kg_min=42.0,
        )
        # Default status returns 75 IHPI
        assert crew.get_risk_level() == RiskLevel.MODERATE

    def test_crew_with_optimal_status(self):
        """Test crew with optimal physiological status."""
        from datetime import datetime
        
        crew = CrewMember(
            crew_id="test",
            name="Test Crew",
            role="Test",
            age_years=35,
            sex="male",
            weight_kg=75,
            height_cm=175,
            vo2max_ml_kg_min=42.0,
        )
        crew.status = CrewPhysiologicalStatus(
            crew_id="test",
            timestamp=datetime.now(),
            safte_effectiveness=95.0,
            hours_awake=6.0,
            sleep_last_24h=8.0,
            kss_score=2.0,
            lnrmssd_current=3.8,
            lnrmssd_baseline_mean=3.5,
            lnrmssd_baseline_sd=0.3,
            body_mass_change_pct=-0.2,
            usg=1.012,
            energy_availability=48.0,
            pvt_lapses_3min=3,
            phase_offset_hours=0.5,
            vo2max=42.0,
            hours_since_last_eva=100.0,
        )
        
        ihpi = crew.get_ihpi()
        assert ihpi >= 85.0
        assert crew.get_risk_level() == RiskLevel.LOW

