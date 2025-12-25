from __future__ import annotations

import pandas as pd

from app.space_analytics_events import (
    ThresholdEventConfig,
    compute_baseline_vs_event_deltas,
    extract_threshold_events,
)


def test_extract_threshold_events_splits_on_gap() -> None:
    df = pd.DataFrame(
        {
            "t": pd.to_datetime(
                [
                    "2025-01-01T00:00:00Z",
                    "2025-01-01T03:00:00Z",
                    "2025-01-01T06:00:00Z",
                    "2025-01-01T09:00:00Z",
                    "2025-01-01T12:00:00Z",
                    "2025-01-01T15:00:00Z",
                ],
                utc=True,
            ),
            "kp": [3.0, 5.0, 6.0, 4.0, 5.0, 5.0],
        }
    )
    cfg = ThresholdEventConfig(
        threshold=5.0,
        direction="ge",
        max_gap=pd.Timedelta(hours=4),
        min_duration=pd.Timedelta(hours=0),
    )
    events = extract_threshold_events(df, time_col="t", value_col="kp", cfg=cfg)
    assert events.shape[0] == 2
    assert events.loc[0, "start_utc"] == pd.Timestamp("2025-01-01T03:00:00Z")
    assert events.loc[0, "end_utc"] == pd.Timestamp("2025-01-01T06:00:00Z")
    assert events.loc[1, "start_utc"] == pd.Timestamp("2025-01-01T12:00:00Z")
    assert events.loc[1, "end_utc"] == pd.Timestamp("2025-01-01T15:00:00Z")


def test_extract_threshold_events_min_duration_filters() -> None:
    df = pd.DataFrame(
        {
            "t": pd.to_datetime(
                [
                    "2025-01-01T00:00:00Z",
                    "2025-01-01T03:00:00Z",
                ],
                utc=True,
            ),
            "kp": [5.0, 5.0],
        }
    )
    cfg = ThresholdEventConfig(
        threshold=5.0,
        direction="ge",
        max_gap=pd.Timedelta(hours=6),
        min_duration=pd.Timedelta(hours=4),
    )
    events = extract_threshold_events(df, time_col="t", value_col="kp", cfg=cfg)
    assert events.empty


def test_compute_baseline_vs_event_deltas_basic() -> None:
    w = pd.DataFrame(
        {
            "start": pd.to_datetime(
                [
                    "2025-01-01T00:00:00Z",
                    "2025-01-01T01:00:00Z",
                    "2025-01-01T02:00:00Z",
                    "2025-01-01T03:00:00Z",
                    "2025-01-01T04:00:00Z",
                    "2025-01-01T05:00:00Z",
                ],
                utc=True,
            ),
            "rmssd": [40.0, 42.0, 41.0, 30.0, 29.0, 31.0],
            "hrf_pip_pct": [45.0, 46.0, 44.0, 60.0, 62.0, 61.0],
        }
    )
    event_start = pd.Timestamp("2025-01-01T03:00:00Z")
    event_end = pd.Timestamp("2025-01-01T05:00:00Z")
    deltas = compute_baseline_vs_event_deltas(
        w,
        time_col="start",
        metric_cols=["rmssd", "hrf_pip_pct"],
        event_start_utc=event_start,
        event_end_utc=event_end,
        baseline_pre=pd.Timedelta(hours=3),
        min_samples_per_phase=3,
    )
    assert set(deltas["metric"].tolist()) == {"rmssd", "hrf_pip_pct"}
    rmssd_row = deltas[deltas["metric"] == "rmssd"].iloc[0]
    pip_row = deltas[deltas["metric"] == "hrf_pip_pct"].iloc[0]

    # Baseline rmssd ~ (40+42+41)/3 = 41; event rmssd ~ (30+29+31)/3 = 30
    assert abs(float(rmssd_row["baseline_mean"]) - 41.0) < 1e-9
    assert abs(float(rmssd_row["event_mean"]) - 30.0) < 1e-9
    assert abs(float(rmssd_row["delta"]) - (-11.0)) < 1e-9

    # Baseline pip ~ 45; event pip ~ 61
    assert abs(float(pip_row["baseline_mean"]) - 45.0) < 1e-9
    assert abs(float(pip_row["event_mean"]) - 61.0) < 1e-9
    assert abs(float(pip_row["delta"]) - 16.0) < 1e-9


