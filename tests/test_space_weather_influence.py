from __future__ import annotations

import math

import pandas as pd

from app.space_weather_influence import (
    AU_KM,
    build_donki_cme_influence_windows,
    dbm_transit_time_seconds,
    estimate_cme_arrival_range_utc,
    recommend_influence_horizons_from_hrv,
)


def test_dbm_transit_time_reasonable_baselines() -> None:
    # When v0 == w and gamma > 0, DBM reduces to constant-speed motion at w.
    w = 400.0
    gamma = 1.0e-8
    t = dbm_transit_time_seconds(AU_KM, v0_km_s=w, w_km_s=w, gamma_km_inv=gamma)
    expected = AU_KM / w
    assert math.isfinite(t)
    assert abs(t - expected) / expected < 1e-3


def test_dbm_transit_time_monotonic_in_speed() -> None:
    w = 400.0
    gamma = 1.0e-8
    t_slow = dbm_transit_time_seconds(AU_KM, v0_km_s=300.0, w_km_s=w, gamma_km_inv=gamma)
    t_fast = dbm_transit_time_seconds(AU_KM, v0_km_s=800.0, w_km_s=w, gamma_km_inv=gamma)
    assert t_fast < t_slow


def test_estimate_cme_arrival_range_returns_ordered_times() -> None:
    t0 = pd.Timestamp("2025-12-01T00:00:00Z")
    a_min, a_max = estimate_cme_arrival_range_utc(t0, v0_km_s=800.0)
    assert isinstance(a_min, pd.Timestamp)
    assert isinstance(a_max, pd.Timestamp)
    assert a_min.tzinfo is not None and a_max.tzinfo is not None
    assert a_max >= a_min


def test_recommend_influence_horizons_outputs_bounded_days() -> None:
    start = pd.Timestamp("2025-12-01T00:00:00Z")
    end = pd.Timestamp("2025-12-01T12:00:00Z")
    rec = recommend_influence_horizons_from_hrv(start, end, assumed_earth_influence_hours=72)
    assert rec.recommended_rr_pad_hours == 72
    assert 1 <= rec.recommended_donki_pad_days <= 30
    assert rec.solar_to_earth_max_hours > 0


def test_build_donki_cme_influence_windows_smoke() -> None:
    df = pd.DataFrame(
        {
            "associatedCMEstartTime": ["2025-12-10T00:00Z", "2025-12-10T12:00Z"],
            "speed": [600.0, 900.0],
        }
    )
    out = build_donki_cme_influence_windows(df, influence_hours=72, max_events=50)
    assert not out.empty
    for col in ("event_id", "start_utc", "end_utc", "arrival_min_utc", "arrival_max_utc"):
        assert col in out.columns
    assert (out["end_utc"] >= out["start_utc"]).all()


