# Author: Dr Diego Malpica MD
"""Tests for app/environment_calculators.py.

Covers wind chill (NWS 2001), frostbite time, WBGT (ISO 7243),
heat index, cold/heat risk classification, and jet lag model.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_APP_DIR = Path(__file__).resolve().parents[1] / "app"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from environment_calculators import (
    compute_wind_chill,
    estimate_frostbite_time_minutes,
    classify_cold_risk,
    compute_wind_chill_full,
    compute_wbgt_simplified,
    compute_heat_index,
    classify_heat_risk,
    compute_wbgt_full,
    compute_jet_lag_performance,
    generate_ice_station_data,
)


class TestWindChill:
    def test_no_effect_above_10c(self) -> None:
        assert compute_wind_chill(15.0, 30.0) == 15.0

    def test_no_effect_low_wind(self) -> None:
        assert compute_wind_chill(-5.0, 3.0) == -5.0

    def test_standard_case(self) -> None:
        wc = compute_wind_chill(-10.0, 30.0)
        assert -25.0 < wc < -10.0  # Should be colder than air temp

    def test_extreme_cold(self) -> None:
        wc = compute_wind_chill(-40.0, 60.0)
        assert wc < -55.0

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            compute_wind_chill(float("nan"), 30.0)


class TestFrostbiteTime:
    def test_warm_no_frostbite(self) -> None:
        assert estimate_frostbite_time_minutes(-10.0) is None

    def test_thirty_minutes(self) -> None:
        assert estimate_frostbite_time_minutes(-20.0) == 30.0

    def test_extreme(self) -> None:
        assert estimate_frostbite_time_minutes(-60.0) == 2.0


class TestColdRisk:
    def test_low(self) -> None:
        assert classify_cold_risk(0.0) == "Low"

    def test_moderate(self) -> None:
        assert classify_cold_risk(-15.0) == "Moderate"

    def test_high(self) -> None:
        assert classify_cold_risk(-35.0) == "High"

    def test_extreme(self) -> None:
        assert classify_cold_risk(-60.0) == "Extreme"


class TestWindChillFull:
    def test_returns_all_fields(self) -> None:
        r = compute_wind_chill_full(-20.0, 40.0)
        assert r.wind_chill_c < -20.0
        assert r.frostbite_minutes is not None
        assert r.risk_category in ("Low", "Moderate", "High", "Very High", "Extreme")
        assert len(r.description) > 0


class TestWBGT:
    def test_mild_conditions(self) -> None:
        wbgt = compute_wbgt_simplified(20.0, 50.0)
        assert 15.0 < wbgt < 25.0

    def test_hot_humid(self) -> None:
        wbgt = compute_wbgt_simplified(38.0, 85.0)
        assert wbgt > 30.0

    def test_cold_dry(self) -> None:
        wbgt = compute_wbgt_simplified(-10.0, 30.0)
        assert wbgt < 5.0

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            compute_wbgt_simplified(float("nan"), 50.0)


class TestHeatIndex:
    def test_below_threshold(self) -> None:
        assert compute_heat_index(20.0, 50.0) == 20.0

    def test_hot_humid(self) -> None:
        hi = compute_heat_index(35.0, 70.0)
        assert hi > 35.0  # Heat index should exceed air temp


class TestHeatRisk:
    def test_low(self) -> None:
        assert classify_heat_risk(22.0) == "Low"

    def test_extreme(self) -> None:
        assert classify_heat_risk(35.0) == "Extreme"


class TestWBGTFull:
    def test_returns_all_fields(self) -> None:
        r = compute_wbgt_full(35.0, 80.0)
        assert r.wbgt_c > 25.0
        assert r.risk_category in ("Low", "Moderate", "High", "Very High", "Extreme")
        assert len(r.work_rest_guidance) > 0


class TestJetLag:
    def test_zero_zones(self) -> None:
        r = compute_jet_lag_performance(0, "east", 0)
        assert r.performance_factor == 1.0
        assert r.readiness_modifier == 0.0
        assert r.phase == "recovered"

    def test_acute_phase(self) -> None:
        r = compute_jet_lag_performance(8, "east", 0)
        assert r.phase == "acute"
        assert r.performance_factor < 1.0
        assert r.readiness_modifier < 0

    def test_recovering_phase(self) -> None:
        r = compute_jet_lag_performance(6, "west", 3)
        assert r.phase == "recovering"
        assert 0.7 < r.performance_factor < 1.0

    def test_fully_recovered(self) -> None:
        r = compute_jet_lag_performance(3, "west", 10)
        assert r.phase == "recovered"
        assert r.performance_factor == 1.0

    def test_eastward_harder(self) -> None:
        east = compute_jet_lag_performance(6, "east", 2)
        west = compute_jet_lag_performance(6, "west", 2)
        assert east.performance_factor <= west.performance_factor
        assert east.days_to_full_resync > west.days_to_full_resync

    def test_invalid_direction(self) -> None:
        with pytest.raises(ValueError):
            compute_jet_lag_performance(5, "north", 1)

    def test_bounded_modifier(self) -> None:
        r = compute_jet_lag_performance(12, "east", 0)
        assert r.readiness_modifier >= -6.0


class TestICEStation:
    def test_generates_data(self) -> None:
        r = generate_ice_station_data(12)
        assert 15.0 < r.temperature_c < 30.0
        assert 10.0 < r.humidity_pct < 90.0
        assert r.co2_ppm > 300
        assert r.o2_pct > 18.0
        assert r.light_lux >= 0

    def test_night_vs_day(self) -> None:
        day = generate_ice_station_data(14)
        night = generate_ice_station_data(3)
        assert day.light_lux > night.light_lux  # Day should have more light
