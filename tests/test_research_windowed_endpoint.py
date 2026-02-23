# Author: Dr Diego Malpica MD
from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_APP_DIR = _PROJECT_ROOT / "app"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import api.research_endpoints as research_endpoints
import hrv_core
import user_database


@dataclass
class _FakeMeasurement:
    measurement_id: str
    source_file: str
    recording_start_utc: str
    measurement_date: str
    created_at: str
    artifact_percentage: float
    rr_intervals_json: str
    lf_power_ms2: Optional[float] = 220.0
    hf_power_ms2: Optional[float] = 180.0
    lf_hf_ratio: Optional[float] = 1.2
    pnn50_pct: Optional[float] = 24.0
    rmssd_ms: Optional[float] = 42.0
    sdnn_ms: Optional[float] = 58.0
    mean_hr_bpm: Optional[float] = 67.0


def _make_measurement(measurement_id: str, start_iso: str, source: str) -> _FakeMeasurement:
    rr_values = [800.0 + float((idx % 5) - 2) * 4.0 for idx in range(900)]
    return _FakeMeasurement(
        measurement_id=measurement_id,
        source_file=source,
        recording_start_utc=start_iso,
        measurement_date=start_iso,
        created_at=start_iso,
        artifact_percentage=1.5,
        rr_intervals_json=json.dumps(rr_values),
    )


def _install_windowed_mocks(
    monkeypatch: pytest.MonkeyPatch,
    *,
    history: list[_FakeMeasurement],
    garmin_df: pd.DataFrame,
    selected: Optional[_FakeMeasurement] = None,
    fake_windowed_func: Any,
) -> None:
    async def _noop_ensure_user_exists(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(research_endpoints, "_ensure_user_exists", _noop_ensure_user_exists)

    class _FakeDB:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        def get_hrv_history(self, _user_id: str, limit: int = 1000) -> list[_FakeMeasurement]:
            return list(history)[: int(limit)]

        def get_garmin_daily_dataframe(
            self,
            _user_id: str,
            *,
            limit: int = 120,
        ) -> pd.DataFrame:
            _ = limit
            return garmin_df.copy()

    monkeypatch.setattr(user_database, "UserDatabase", _FakeDB)
    monkeypatch.setattr(hrv_core, "compute_windowed_hrv", fake_windowed_func)

    if selected is not None:
        async def _fake_resolve_measurement(
            _user_id: str,
            *,
            measurement_id: Optional[str] = None,
            file_hash: Optional[str] = None,
        ) -> _FakeMeasurement:
            _ = (measurement_id, file_hash)
            return selected

        monkeypatch.setattr(research_endpoints, "_resolve_measurement_for_user", _fake_resolve_measurement)


def _fake_windowed_multiday(df_in: pd.DataFrame, **_kwargs: Any) -> pd.DataFrame:
    base = pd.to_datetime(df_in["timestamp"].iloc[0], utc=True).floor("D")
    rows = []
    for idx in range(6):
        t_start = base + pd.Timedelta(days=idx)
        rows.append(
            {
                "start": t_start,
                "end": t_start + pd.Timedelta(minutes=5),
                "rmssd": 35.0 + (idx * 2.5),
                "sdnn": 52.0 + (idx * 2.0),
                "pnn50": 18.0 + idx,
                "mean_hr": 72.0 - (idx * 0.8),
                "lf_power": 180.0 + (idx * 10.0),
                "hf_power": 160.0 + (idx * 8.0),
                "lf_hf_ratio": 1.15 + (idx * 0.04),
            }
        )
    return pd.DataFrame(rows)


def _fake_windowed_intraday(df_in: pd.DataFrame, **_kwargs: Any) -> pd.DataFrame:
    base = pd.to_datetime(df_in["timestamp"].iloc[0], utc=True).floor("D")
    rows = []
    for idx in range(6):
        t_start = base + pd.Timedelta(hours=idx)
        rows.append(
            {
                "start": t_start,
                "end": t_start + pd.Timedelta(minutes=5),
                "rmssd": 30.0 + (idx * 4.0),
                "sdnn": 45.0 + (idx * 3.0),
                "pnn50": 15.0 + idx,
                "mean_hr": 74.0 - idx,
                "lf_power": 150.0 + (idx * 6.0),
                "hf_power": 120.0 + (idx * 4.0),
                "lf_hf_ratio": 1.25 + (idx * 0.03),
            }
        )
    return pd.DataFrame(rows)


def test_benjamini_hochberg_expected_q_values() -> None:
    q_values = research_endpoints._benjamini_hochberg([0.01, 0.02, 0.2, None])
    assert q_values[0] == pytest.approx(0.03, abs=1e-9)
    assert q_values[1] == pytest.approx(0.03, abs=1e-9)
    assert q_values[2] == pytest.approx(0.2, abs=1e-9)
    assert q_values[3] is None


def test_get_hrv_windowed_scope_all_returns_enriched_statistics_and_q_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    history = [
        _make_measurement("m-001", "2026-01-01T00:00:00Z", "session-a.csv"),
        _make_measurement("m-002", "2026-02-01T00:00:00Z", "session-b.csv"),
    ]
    garmin_df = pd.DataFrame(
        {
            "metric_date": pd.date_range("2026-01-01", periods=70, freq="D", tz="UTC"),
            "resting_hr_bpm": [62.0 + (idx * 0.05) for idx in range(70)],
            "sleep_duration_hours": [7.5 - (idx * 0.01) for idx in range(70)],
            "avg_spo2": [97.5 - (idx * 0.01) for idx in range(70)],
            "stress_score": [30.0 + (idx * 0.2) for idx in range(70)],
            "body_battery_avg": [72.0 - (idx * 0.15) for idx in range(70)],
            "avg_respiration_awake": [14.0 + (idx * 0.02) for idx in range(70)],
            "avg_respiration_sleep": [12.0 + (idx * 0.01) for idx in range(70)],
        }
    )

    _install_windowed_mocks(
        monkeypatch,
        history=history,
        garmin_df=garmin_df,
        fake_windowed_func=_fake_windowed_multiday,
    )

    result = asyncio.run(
        research_endpoints.get_hrv_windowed(
            user_id="demo-user",
            window_size=300,
            step_size=60,
            scope="all",
            include_garmin=True,
            max_recordings=120,
            measurement_id=None,
            file_hash=None,
        )
    )

    payload = result.model_dump()
    assert payload["source_scope"] == "all"
    assert payload["n_sessions"] == 2
    assert payload["n_windows"] >= 12
    assert len(payload["trend_statistics"]) >= 3
    assert any(entry.get("q_value") is not None for entry in payload["trend_statistics"])

    assert payload["physiological_correlations"]
    assert any(entry.get("q_value") is not None for entry in payload["physiological_correlations"])
    assert payload["statistical_notes"]

    labels = payload.get("correlation_metric_labels", [])
    q_matrix = payload.get("correlation_q_values", [])
    if labels:
        assert len(q_matrix) == len(labels)
        assert all(len(row) == len(labels) for row in q_matrix)


def test_get_hrv_windowed_scope_selected_uses_window_fallback_for_trends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = _make_measurement("m-selected", "2026-03-01T00:00:00Z", "selected.csv")

    _install_windowed_mocks(
        monkeypatch,
        history=[selected],
        garmin_df=pd.DataFrame(),
        selected=selected,
        fake_windowed_func=_fake_windowed_intraday,
    )

    result = asyncio.run(
        research_endpoints.get_hrv_windowed(
            user_id="demo-user",
            window_size=300,
            step_size=60,
            scope="selected",
            include_garmin=False,
            max_recordings=10,
            measurement_id="m-selected",
            file_hash=None,
        )
    )

    payload = result.model_dump()
    assert payload["source_scope"] == "selected"
    assert payload["n_sessions"] == 1
    assert payload["n_windows"] == 6

    rmssd_trend = next(item for item in payload["trend_statistics"] if item["metric"] == "RMSSD")
    assert rmssd_trend["n_samples"] == 6
    assert rmssd_trend["slope_per_day"] is not None
    assert rmssd_trend["trend_method"] in {"theil-sen+kendall", "ols+kendall"}

    expected_keys = {
        "trend_statistics",
        "correlation_q_values",
        "physiological_correlations",
        "statistical_notes",
    }
    assert expected_keys.issubset(payload.keys())
