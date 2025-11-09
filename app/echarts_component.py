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
		<div id="{container_id}" style="width:{width};height:{height_px}px;margin:0 auto;"></div>
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
				if (window.frameElement) {{
					const frame = window.frameElement;
					frame.style.width = '100%';
					frame.style.minWidth = '100%';
					frame.style.border = 'none';
					const parent = frame.parentElement;
					if (parent) {{
						parent.style.width = '100%';
						parent.style.minWidth = '100%';
						parent.style.flex = '1 1 auto';
						parent.style.display = 'block';
					}}
				}}
				document.documentElement.style.width = '100%';
				document.body.style.width = '100%';
				document.body.style.margin = '0';
				if (el.__echartsInstance) {{
					if (typeof el.__echartsInstance.dispose === 'function') {{
						el.__echartsInstance.dispose();
					}}
					delete el.__echartsInstance;
				}}
				if (el.__resizeObserver && typeof el.__resizeObserver.disconnect === 'function') {{
					el.__resizeObserver.disconnect();
					delete el.__resizeObserver;
				}}
				if (el.__resizeHandler) {{
					window.removeEventListener('resize', el.__resizeHandler);
					delete el.__resizeHandler;
				}}
				if (el.__fallbackInterval) {{
					window.clearInterval(el.__fallbackInterval);
					delete el.__fallbackInterval;
				}}
				const inst = echarts.init(el, {theme_snippet});
				const option = {option_json};
				inst.setOption(option, true);
				const resizeHandler = () => inst.resize();
				el.__resizeHandler = resizeHandler;
				window.addEventListener('resize', resizeHandler);
				if (window.ResizeObserver) {{
					const observer = new ResizeObserver((entries) => {{
						for (const entry of entries) {{
							if (entry.target === el) {{
								inst.resize();
							}}
						}}
					}});
					observer.observe(el);
					el.__resizeObserver = observer;
				}} else {{
					// Fallback for browsers without ResizeObserver support
					const fallback = () => inst.resize();
					el.__fallbackInterval = window.setInterval(fallback, 500);
				}}
				requestAnimationFrame(() => inst.resize());
				el.__echartsInstance = inst;
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
	components.html(html, height=height_px + 20, scrolling=False)


