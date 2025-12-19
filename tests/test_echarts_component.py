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

	# Avoid reading the large local JS bundle in unit tests.
	cfg = echarts_component.EChartsConfig(local_echarts_path=None)

	echarts_component.render_echarts(
		option,
		enable_export=False,
		config=cfg,
	)

	html = str(captured.get("html", ""))
	assert "html,body{height:100%;margin:0}" in html
	assert "#chart{width:100%;height:100vh;}" in html
	# Ensure we are not embedding the ~1MB ECharts runtime into every chart iframe.
	# (We rely on browser caching by fetching the bundle from a static URL instead.)
	assert len(html) < 250_000
