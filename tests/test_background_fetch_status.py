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
