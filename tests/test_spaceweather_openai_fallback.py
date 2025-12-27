from __future__ import annotations

import pytest

from app.spaceweather_openai_fallback import extract_spaceweather_with_openai


def test_extract_spaceweather_with_openai_timeout_must_be_positive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The OpenAI fallback should validate timeout bounds deterministically.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        _ = extract_spaceweather_with_openai({"home": "<html></html>"}, timeout_s=0.0)


def test_extract_spaceweather_with_openai_returns_none_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Without OPENAI_API_KEY configured, the fallback should be disabled and return None.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    out = extract_spaceweather_with_openai({"home": "<html></html>"}, timeout_s=5.0)
    assert out is None


