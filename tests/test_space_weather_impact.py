from __future__ import annotations

import time
from typing import Optional, Tuple

import pytest

from app.space_weather_impact import ImpactEvent, fetch_space_weather_snapshot
import app.space_weather_impact as impact


def _stub_ok() -> Tuple[Optional[ImpactEvent], Optional[str]]:
    return None, None


def test_fetch_space_weather_snapshot_validates_timeout() -> None:
    with pytest.raises(ValueError):
        fetch_space_weather_snapshot(overall_timeout_s=0)


def test_fetch_space_weather_snapshot_returns_quickly_when_all_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(impact, "fetch_xray_impact", _stub_ok)
    monkeypatch.setattr(impact, "fetch_sep_impact", _stub_ok)
    monkeypatch.setattr(impact, "fetch_plasma_impact", _stub_ok)
    monkeypatch.setattr(impact, "fetch_geomagnetic_impact", _stub_ok)

    snap = fetch_space_weather_snapshot(overall_timeout_s=1.0)
    assert snap.errors == {}
    assert snap.timestamp_utc.tzinfo is not None


def test_fetch_space_weather_snapshot_marks_timed_out_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    def slow() -> Tuple[Optional[ImpactEvent], Optional[str]]:
        time.sleep(0.25)
        return None, None

    monkeypatch.setattr(impact, "fetch_xray_impact", slow)
    monkeypatch.setattr(impact, "fetch_sep_impact", _stub_ok)
    monkeypatch.setattr(impact, "fetch_plasma_impact", _stub_ok)
    monkeypatch.setattr(impact, "fetch_geomagnetic_impact", _stub_ok)

    t0 = time.monotonic()
    snap = fetch_space_weather_snapshot(overall_timeout_s=0.05)
    dt = time.monotonic() - t0

    # Should not wait for the slow task to finish.
    assert dt < 0.20
    assert "photon" in snap.errors
    assert "Timed out" in snap.errors["photon"]


