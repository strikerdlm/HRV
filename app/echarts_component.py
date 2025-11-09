from __future__ import annotations

import json
import textwrap
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st
import streamlit.components.v1 as components


@dataclass(slots=True, frozen=True)
class EChartsConfig:
	"""Configuration for embedding Apache ECharts within Streamlit.

	Attributes:
		cdn_url: Optional CDN URL for echarts.min.js. If None, tries local fallback.
		local_echarts_path: Optional local path to echarts.min.js (e.g., node_modules/echarts/dist/echarts.min.js).
	"""
	cdn_url: Optional[str] = "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"
	local_echarts_path: Optional[Path] = None


def _read_local_echarts(local_path: Optional[Path]) -> Optional[str]:
	if local_path is None:
		return None
	try:
		return Path(local_path).read_text(encoding="utf-8")
	except Exception:
		return None


def render_echarts(
	option: Dict[str, Any],
	*,
	height_px: int = 420,
	width: str = "100%",
	theme: Optional[str] = None,
	config: Optional[EChartsConfig] = None,
) -> None:
	"""Render an ECharts option dict inside Streamlit using an HTML component.

	Args:
		option: ECharts option dictionary (must be JSON-serializable).
		height_px: Container height in pixels.
		width: CSS width value for the container (e.g., '100%', '800px').
		theme: Optional ECharts theme name.
		config: Optional EChartsConfig to select CDN or local embedding.
	"""
	if height_px < 100 or height_px > 4000:
		raise ValueError("height_px must be between 100 and 4000")

	cfg = config or EChartsConfig(
		local_echarts_path=Path("node_modules/echarts/dist/echarts.min.js")
	)

	container_id = f"echarts-{uuid.uuid4().hex}"
	option_json = json.dumps(option, separators=(",", ":"), ensure_ascii=False)
	local_js = _read_local_echarts(cfg.local_echarts_path)

	# If local JS is available, inline it; otherwise load from CDN (defer)
	if local_js:
		script_loader = f"<script>{local_js}</script>"
	else:
		cdn = cfg.cdn_url or "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"
		script_loader = f'<script src="{cdn}"></script>'

	theme_snippet = f'"{theme}"' if theme else "null"

	html = textwrap.dedent(
		f"""
		<div id="{container_id}" style="width:{width};height:{height_px}px;"></div>
		{script_loader}
		<script>
		(function() {{
			function mountChart() {{
				if (!window.echarts) {{
					console.error("ECharts not loaded.");
					return;
				}}
				const el = document.getElementById("{container_id}");
				if (!el) return;
				const inst = echarts.init(el, {theme_snippet});
				const option = {option_json};
				inst.setOption(option, true);
				window.addEventListener('resize', () => inst.resize());
			}}
			if (document.readyState === 'loading') {{
				document.addEventListener('DOMContentLoaded', mountChart);
			}} else {{
				mountChart();
			}}
		}})();
		</script>
		"""
	).strip()

	# Extra 20px to accommodate padding
	if isinstance(width, (int, float)):
		iframe_width = int(width)
	elif isinstance(width, str):
		width = width.strip()
		if width.endswith("px") and width[:-2].isdigit():
			iframe_width = int(float(width[:-2]))
		elif width.endswith("%"):
			iframe_width = 0  # let Streamlit auto-expand
		else:
			iframe_width = 0
	else:
		iframe_width = 0
	components.html(html, height=height_px + 20, width=iframe_width, scrolling=False)


