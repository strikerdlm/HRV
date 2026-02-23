# Author: Dr Diego Malpica MD
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx
import pytest
from fastapi import HTTPException

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_APP_DIR = _PROJECT_ROOT / "app"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import api.research_endpoints as research_endpoints


def test_get_metar_uses_hours_window_and_returns_latest(monkeypatch: pytest.MonkeyPatch) -> None:
    called_urls: list[str] = []

    async def fake_get(self: httpx.AsyncClient, url: str, headers=None) -> httpx.Response:
        _ = headers
        called_urls.append(url)
        return httpx.Response(
            status_code=200,
            json=[
                {
                    "icaoId": "SKBO",
                    "reportTime": "2026-02-22T20:00:00.000Z",
                    "obsTime": 1771790400,
                    "rawOb": "METAR OLD",
                },
                {
                    "icaoId": "SKBO",
                    "reportTime": "2026-02-22T23:00:00.000Z",
                    "obsTime": 1771801200,
                    "rawOb": "METAR NEW",
                },
            ],
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    payload = asyncio.run(research_endpoints.get_metar("skbo"))
    assert payload["icao"] == "SKBO"
    assert payload["error"] is None
    assert isinstance(payload["metar"], dict)
    assert payload["metar"]["rawOb"] == "METAR NEW"

    assert called_urls
    assert "ids=SKBO" in called_urls[0]
    assert "hours=24" in called_urls[0]


def test_get_metar_handles_204_no_content(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(self: httpx.AsyncClient, url: str, headers=None) -> httpx.Response:
        _ = (self, url, headers)
        return httpx.Response(status_code=204, text="")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    payload = asyncio.run(research_endpoints.get_metar("KJFK"))
    assert payload["icao"] == "KJFK"
    assert payload["metar"] is None
    assert payload["error"] == "No METAR available for this station"


def test_get_metar_rejects_invalid_icao() -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(research_endpoints.get_metar("123"))

    assert exc_info.value.status_code == 400
