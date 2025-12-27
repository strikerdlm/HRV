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
    monkeypatch.setattr(impact, "fetch_cme_enlil_impact", _stub_ok)
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
    monkeypatch.setattr(impact, "fetch_cme_enlil_impact", _stub_ok)
    monkeypatch.setattr(impact, "fetch_geomagnetic_impact", _stub_ok)

    t0 = time.monotonic()
    snap = fetch_space_weather_snapshot(overall_timeout_s=0.05)
    dt = time.monotonic() - t0

    # Should not wait for the slow task to finish.
    assert dt < 0.20
    assert "photon" in snap.errors
    assert "Timed out" in snap.errors["photon"]


def test_fetch_sep_impact_selects_latest_p10_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure SEP classification uses the >=10 MeV channel (NOAA S-scale), not other energies."""

    sample = [
        {"time_tag": "2025-12-26T00:00:00Z", "satellite": 18, "flux": 0.1, "energy": ">=50 MeV"},
        {"time_tag": "2025-12-26T00:00:00Z", "satellite": 18, "flux": 12.0, "energy": ">=10 MeV"},
        {"time_tag": "2025-12-26T00:05:00Z", "satellite": 18, "flux": 999.0, "energy": ">=50 MeV"},
        {"time_tag": "2025-12-26T00:05:00Z", "satellite": 18, "flux": 15.0, "energy": ">=10 MeV"},
    ]

    class _Resp:
        def raise_for_status(self) -> None:  # noqa: D401
            return None

        def json(self) -> object:
            return sample

    class _Session:
        def get(self, url: str, timeout: float) -> _Resp:  # noqa: ARG002
            return _Resp()

    monkeypatch.setattr(impact, "_get_http_session", lambda: _Session())

    event, err = impact.fetch_sep_impact()
    assert err is None
    assert event is not None
    assert event.raw_value == pytest.approx(15.0)
    assert ">10 MeV" in event.source_description
    assert event.severity == impact.ImpactSeverity.MINOR


def test_classify_geomagnetic_noaa_g_scale_mapping() -> None:
    """Sanity-check NOAA G-scale mapping (Kp 5-9)."""
    _, sev5, _ = impact._classify_geomagnetic(5.0, float("nan"))
    _, sev6, _ = impact._classify_geomagnetic(6.0, float("nan"))
    _, sev7, _ = impact._classify_geomagnetic(7.0, float("nan"))
    _, sev8, _ = impact._classify_geomagnetic(8.0, float("nan"))
    _, sev9, _ = impact._classify_geomagnetic(9.0, float("nan"))

    assert sev5 == impact.ImpactSeverity.MINOR
    assert sev6 == impact.ImpactSeverity.MODERATE
    assert sev7 == impact.ImpactSeverity.STRONG
    assert sev8 == impact.ImpactSeverity.SEVERE
    assert sev9 == impact.ImpactSeverity.EXTREME


def test_build_cme_event_from_enlil_record_smoke() -> None:
    now = impact.datetime.datetime(2025, 1, 1, 0, 0, tzinfo=impact.datetime.timezone.utc)
    rec = {
        "simulationID": "WSA-ENLIL/TEST/1",
        "modelCompletionTime": "2024-12-31T00:00Z",
        "estimatedShockArrivalTime": "2025-01-03T12:00Z",
        "isEarthGB": True,
        "isEarthMinorImpact": False,
        "kp_18": 3,
        "kp_90": 4,
        "kp_135": 5,
        "kp_180": 7,
        "rmin_re": 7.2,
        "link": "https://example.invalid/enlil",
        "cmeInputs": [
            {
                "isMostAccurate": True,
                "cmeStartTime": "2025-01-01T00:00Z",
                "time21_5": "2025-01-01T06:00Z",
                "speed": 800.0,
                "latitude": 10.0,
                "longitude": 20.0,
            }
        ],
    }

    event = impact._build_cme_event_from_enlil_record(rec, now_utc=now)
    assert event is not None
    assert event.category == impact.EnergyCategory.CME_SHOCK
    assert event.severity == impact.ImpactSeverity.STRONG
    assert event.arrival_time_utc == impact.datetime.datetime(2025, 1, 3, 12, 0, tzinfo=impact.datetime.timezone.utc)
    assert "DONKI WSA+ENLIL" in event.source_description


