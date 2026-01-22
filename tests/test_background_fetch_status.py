from __future__ import annotations

from typing import Any, Dict

import pytest

import app.app as app_module


class _DummyThread:
    def __init__(self, alive: bool) -> None:
        self._alive = alive

    def is_alive(self) -> bool:  # noqa: D401
        return self._alive


def _make_bg_results() -> Dict[str, Dict[str, Any]]:
    return {
        "space_weather": {"done": False, "error": None, "data": {}, "fetch_time": None},
        "noaa": {"done": False, "error": None, "data": {}, "fetch_time": None},
        "donki": {"done": False, "error": None, "data": {}, "fetch_time": None},
    }


def test_poll_background_fetch_idle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "_bg_fetch_results", _make_bg_results(), raising=False)
    monkeypatch.setattr(app_module, "_bg_fetch_thread", _DummyThread(False), raising=False)

    result = app_module._poll_background_fetch()
    assert all(info.get("idle", False) for info in result.values())
    assert not any(info.get("running", False) for info in result.values())


def test_poll_background_fetch_running(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "_bg_fetch_results", _make_bg_results(), raising=False)
    monkeypatch.setattr(app_module, "_bg_fetch_thread", _DummyThread(True), raising=False)

    result = app_module._poll_background_fetch()
    assert any(info.get("running", False) for info in result.values())


def test_bg_fetch_loop_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    app_module._reset_background_fetch_status()
    monkeypatch.setattr(app_module, "_BG_FETCH_LOOP_WINDOW_SECONDS", 10.0, raising=False)
    monkeypatch.setattr(app_module, "_BG_FETCH_LOOP_MAX_STARTS", 2, raising=False)

    now = 100.0
    assert app_module._record_bg_fetch_start(now) is False
    assert app_module._record_bg_fetch_start(now + 1) is False
    assert app_module._record_bg_fetch_start(now + 2) is True

    health = app_module._get_bg_fetch_health(now + 2)
    assert health.get("loop_detected") is True


def test_bg_fetch_timeout_health(monkeypatch: pytest.MonkeyPatch) -> None:
    app_module._reset_background_fetch_status()
    monkeypatch.setattr(app_module, "_BG_FETCH_MAX_RUNTIME_SECONDS", 10.0, raising=False)
    monkeypatch.setattr(app_module, "_bg_fetch_thread", _DummyThread(True), raising=False)
    with app_module._bg_fetch_lock:
        app_module._bg_fetch_meta["last_start"] = 50.0

    health = app_module._get_bg_fetch_health(100.0)
    assert health.get("timed_out") is True
