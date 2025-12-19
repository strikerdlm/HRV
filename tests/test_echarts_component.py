"""Tests for the ECharts component."""
from __future__ import annotations

import types
from typing import Any, Dict

import pytest

import app.echarts_component as echarts_component


def test_render_echarts_does_not_nameerror_on_css_braces(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression test for f-string brace escaping.

    The ECharts HTML template includes CSS/JS blocks that contain curly braces.
    Those braces must be escaped in the *Python* f-string ({{ / }}) so we do not
    accidentally trigger f-string interpolation (e.g., `{height:...}` -> NameError).
    """
    captured: Dict[str, Any] = {}

    def fake_components_html(html: str, **kwargs: Any) -> None:
        captured["html"] = html
        captured.update(kwargs)

    monkeypatch.setattr(
        echarts_component,
        "components",
        types.SimpleNamespace(html=fake_components_html),
    )
    monkeypatch.setattr(
        echarts_component,
        "st",
        types.SimpleNamespace(caption=lambda *_args, **_kwargs: None),
    )

    option = {
        "title": {"text": "Test"},
        "xAxis": {"type": "category", "data": ["a"]},
        "yAxis": {"type": "value"},
        "series": [{"type": "line", "data": [1]}],
    }

    # Use CDN-only config (no local bundle) to keep test fast and small.
    cfg = echarts_component.EChartsConfig(
        local_echarts_path=None,
        embed_inline=False,  # Use CDN script tag, not inline embedding
    )

    echarts_component.render_echarts(
        option,
        enable_export=False,
        config=cfg,
    )

    html = str(captured.get("html", ""))
    
    # Check that CSS with braces is properly rendered (not causing f-string errors).
    assert "margin: 0" in html  # From the CSS reset
    assert "height:" in html  # Chart container height
    
    # Check that the standalone HTML generator has proper CSS.
    assert "html,body{height:100%;margin:0}" in html  # In buildStandaloneHtml
    assert "#chart{width:100%;height:100vh}" in html  # In buildStandaloneHtml
    
    # Check that CDN script tag is present when not embedding inline.
    assert "cdn.jsdelivr.net" in html
    
    # When not embedding inline, HTML should be reasonably small.
    assert len(html) < 50_000


def test_render_echarts_with_inline_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that inline embedding works when local bundle is available."""
    captured: Dict[str, Any] = {}

    def fake_components_html(html: str, **kwargs: Any) -> None:
        captured["html"] = html
        captured.update(kwargs)

    monkeypatch.setattr(
        echarts_component,
        "components",
        types.SimpleNamespace(html=fake_components_html),
    )
    monkeypatch.setattr(
        echarts_component,
        "st",
        types.SimpleNamespace(caption=lambda *_args, **_kwargs: None),
    )

    option = {
        "title": {"text": "Test Inline"},
        "xAxis": {"type": "category", "data": ["x"]},
        "yAxis": {"type": "value"},
        "series": [{"type": "bar", "data": [42]}],
    }

    # Default config uses inline embedding if local bundle exists.
    cfg = echarts_component.EChartsConfig()

    echarts_component.render_echarts(
        option,
        enable_export=True,
        config=cfg,
    )

    html = str(captured.get("html", ""))
    
    # Check that the chart was generated.
    assert "Test Inline" in html
    assert "42" in html  # The data value
    
    # Check export buttons are present.
    assert "data-action" in html
    assert "PNG" in html or "png" in html.lower()


def test_st_echarts_compatibility() -> None:
    """Test that st_echarts API is compatible."""
    # Just test that the function exists and has the right signature.
    assert callable(echarts_component.st_echarts)
    
    # Test height parsing.
    with pytest.raises(ValueError, match="options must be provided"):
        echarts_component.st_echarts(options=None)


def test_echarts_config_defaults() -> None:
    """Test EChartsConfig default values."""
    cfg = echarts_component.EChartsConfig()
    
    assert cfg.cdn_url == "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"
    assert cfg.embed_inline is True
    # local_echarts_path should point to node_modules
    assert cfg.local_echarts_path is not None
    assert "echarts" in str(cfg.local_echarts_path)
