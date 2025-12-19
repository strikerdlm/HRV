from __future__ import annotations

import json
import shutil
import textwrap
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

import streamlit as st
import streamlit.components.v1 as components


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_LOCAL_ECHARTS_BUNDLE = _PROJECT_ROOT / "node_modules" / "echarts" / "dist" / "echarts.min.js"
# Streamlit serves static files from .streamlit/static/ relative to the working directory.
# We also maintain a fallback in app/static/ for backwards compatibility.
_STREAMLIT_STATIC_DIR = _PROJECT_ROOT / ".streamlit" / "static"
_APP_STATIC_DIR = Path(__file__).resolve().parent / "static"
_STATIC_ECHARTS_FILENAME = "echarts.min.js"


@dataclass(slots=True, frozen=True)
class EChartsConfig:
	"""Configuration for embedding Apache ECharts within Streamlit.

	Attributes:
		cdn_url: Optional CDN URL for echarts.min.js. If None, tries local fallback.
		local_echarts_path: Optional local path to echarts.min.js (e.g., node_modules/echarts/dist/echarts.min.js).
	"""
	cdn_url: Optional[str] = "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"
	local_echarts_path: Optional[Path] = _DEFAULT_LOCAL_ECHARTS_BUNDLE


def _get_base_url_prefix() -> str:
	"""Best-effort Streamlit baseUrlPath prefix ('' or '/<base>').

	Notes:
	- In unit tests, `st` may be monkeypatched; this function must be tolerant.
	"""
	get_opt = getattr(st, "get_option", None)
	if not callable(get_opt):
		return ""
	try:
		raw = get_opt("server.baseUrlPath")
	except Exception:
		return ""
	if not raw:
		return ""
	text = str(raw).strip().strip("/")
	return f"/{text}" if text else ""


def _static_url(filename: str) -> str:
	"""URL for Streamlit static serving: /app/static/<filename> (with baseUrlPath)."""
	return f"{_get_base_url_prefix()}/app/static/{filename}"


def _ensure_echarts_available_via_static(
	*,
	source_path: Optional[Path],
) -> Optional[str]:
	"""Ensure ECharts bundle exists under .streamlit/static/ and return its URL.

	Streamlit serves files from `.streamlit/static/` when `server.enableStaticServing=true`.
	The URL is `/app/static/<filename>`. However, `.js` is served as `text/plain` (nosniff)
	and can't be executed via a `<script src=...>` tag. We fetch it and inject it as an
	inline script in the iframe. That still enables browser caching and avoids embedding
	~1MB into every chart HTML.
	"""
	if source_path is None:
		return None
	src = Path(source_path)
	if not src.exists() or not src.is_file():
		return None
	try:
		# Primary: Streamlit's static directory (.streamlit/static/)
		_STREAMLIT_STATIC_DIR.mkdir(parents=True, exist_ok=True)
		dst_streamlit = _STREAMLIT_STATIC_DIR / _STATIC_ECHARTS_FILENAME
		if (not dst_streamlit.exists()) or (dst_streamlit.stat().st_size != src.stat().st_size):
			shutil.copy2(src, dst_streamlit)

		# Fallback: also copy to app/static/ for backwards compatibility
		_APP_STATIC_DIR.mkdir(parents=True, exist_ok=True)
		dst_app = _APP_STATIC_DIR / _STATIC_ECHARTS_FILENAME
		if (not dst_app.exists()) or (dst_app.stat().st_size != src.stat().st_size):
			shutil.copy2(src, dst_app)

		return _static_url(_STATIC_ECHARTS_FILENAME)
	except Exception:
		return None


def render_echarts(
	option: Dict[str, Any],
	*,
	height_px: int = 420,
	width: str = "100%",
	theme: Optional[str] = None,
	config: Optional[EChartsConfig] = None,
	renderer: str = "svg",
	enable_export: bool = True,
	export_basename: str = "echarts_chart",
	caption: Optional[str] = None,
) -> None:
	"""Render an ECharts option dict inside Streamlit using an HTML component.

	Args:
		option: ECharts option dictionary (must be JSON-serializable).
		height_px: Container height in pixels.
		width: CSS width value for the container (e.g., '100%', '800px').
		theme: Optional ECharts theme name.
		config: Optional EChartsConfig to select CDN or local embedding.
		renderer: ECharts renderer ('canvas' or 'svg'). Defaults to 'svg' for vector export.
		enable_export: If True, show client-side export buttons (PNG/SVG/HTML/JSON/spec).
		export_basename: Base filename (no extension) for client-side exports.
		caption: Optional short caption paragraph rendered below the chart.
	"""
	if height_px < 100 or height_px > 4000:
		raise ValueError("height_px must be between 100 and 4000")
	if renderer not in {"canvas", "svg"}:
		raise ValueError("renderer must be 'canvas' or 'svg'")
	if not export_basename.strip():
		raise ValueError("export_basename must be a non-empty string")

	cfg = config or EChartsConfig(
		local_echarts_path=_DEFAULT_LOCAL_ECHARTS_BUNDLE
	)

	container_id = f"echarts-{uuid.uuid4().hex}"
	status_id = f"{container_id}-status"
	toolbar_id = f"echarts-toolbar-{uuid.uuid4().hex}"
	option_json = json.dumps(option, separators=(",", ":"), ensure_ascii=False)

	cdn = cfg.cdn_url or "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"
	local_static_url = _ensure_echarts_available_via_static(source_path=cfg.local_echarts_path)
	# Primary: CDN (most reliable). Fallback: local static bundle (for offline scenarios).
	# The CDN approach uses a <script> tag which respects proper MIME types and caching.
	# The local approach uses fetch+inject because Streamlit serves .js as text/plain.
	echarts_lib_source = cdn  # Always prefer CDN for reliability
	# Fallback sources: local static bundle if available
	fallback_sources: list[str] = []
	if local_static_url:
		fallback_sources.append(local_static_url)

	theme_snippet = f'"{theme}"' if theme else "null"

	# Simple client-side export helpers (no Streamlit roundtrip).
	# - PNG: always available
	# - SVG: available only when renderer='svg'
	# - HTML: portable minimal HTML including option JSON
	# - JSON: option JSON spec export
	export_toolbar_html = ""
	if enable_export:
		export_toolbar_html = textwrap.dedent(
			f"""
			<div id="{toolbar_id}" style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:6px 0 10px 0;">
			  <button type="button" data-action="png" style="padding:6px 10px;border:1px solid #d0d7de;border-radius:6px;background:#fff;cursor:pointer;">Download PNG</button>
			  <button type="button" data-action="svg" style="padding:6px 10px;border:1px solid #d0d7de;border-radius:6px;background:#fff;cursor:pointer;">Download SVG</button>
			  <button type="button" data-action="pdf" style="padding:6px 10px;border:1px solid #d0d7de;border-radius:6px;background:#fff;cursor:pointer;">Print / Save PDF</button>
			  <button type="button" data-action="html" style="padding:6px 10px;border:1px solid #d0d7de;border-radius:6px;background:#fff;cursor:pointer;">Download HTML</button>
			  <button type="button" data-action="json" style="padding:6px 10px;border:1px solid #d0d7de;border-radius:6px;background:#fff;cursor:pointer;">Download spec JSON</button>
			  <span style="color:#6b7280;font-size:12px;">Exports are generated in your browser (no server upload).</span>
			</div>
			"""
		).strip()

	html = textwrap.dedent(
		f"""
		{export_toolbar_html}
		<div id="{status_id}" style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;font-size:12px;color:#6b7280;margin:4px 0;">
		  Loading chart...
		</div>
		<div id="{container_id}" style="width:{width};height:{height_px}px;margin:0 auto;"></div>
		<script>
		(function() {{
			const EXPORT_BASENAME = {json.dumps(export_basename)};
			const ECHARTS_OPTION = {option_json};
			const ECHARTS_THEME = {theme_snippet};
			const ECHARTS_RENDERER = {json.dumps(renderer)};
			const ECHARTS_LIB_SOURCE = {json.dumps(echarts_lib_source)};
			const ECHARTS_FALLBACK_SOURCES = {json.dumps(fallback_sources)};

			const statusEl = document.getElementById("{status_id}");
			function setStatus(message, isError) {{
				if (!statusEl) return;
				statusEl.textContent = message;
				statusEl.style.color = isError ? "#b91c1c" : "#6b7280";
				statusEl.style.display = message ? "block" : "none";
			}}

			function loadScript(src) {{
				return new Promise((resolve, reject) => {{
					const s = document.createElement("script");
					s.src = src;
					s.onload = () => resolve(true);
					s.onerror = () => reject(new Error("Failed to load script: " + src));
					document.head.appendChild(s);
				}});
			}}

			async function fetchAndInjectScript(url) {{
				const resp = await fetch(url, {{ cache: "force-cache" }});
				if (!resp.ok) {{
					throw new Error("Failed to fetch ECharts bundle: HTTP " + resp.status);
				}}
				const jsText = await resp.text();
				const s = document.createElement("script");
				s.textContent = jsText;
				document.head.appendChild(s);
			}}

			function downloadDataUrl(dataUrl, filename) {{
				const a = document.createElement('a');
				a.href = dataUrl;
				a.download = filename;
				document.body.appendChild(a);
				a.click();
				document.body.removeChild(a);
			}}

			function downloadText(text, filename, mimeType) {{
				const blob = new Blob([text], {{ type: mimeType }});
				const url = URL.createObjectURL(blob);
				const a = document.createElement('a');
				a.href = url;
				a.download = filename;
				document.body.appendChild(a);
				a.click();
				document.body.removeChild(a);
				URL.revokeObjectURL(url);
			}}

			function buildPortableHtml(option, theme) {{
				const cdn = "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js";
				const opt = JSON.stringify(option, null, 2);
				const th = theme ? JSON.stringify(theme) : "null";
				return [
					"<!doctype html>",
					"<html>",
					"<head>",
					'  <meta charset="utf-8" />',
					"  <meta name=\\"viewport\\" content=\\"width=device-width, initial-scale=1\\" />",
					"  <title>ECharts export</title>",
					"  <style>html,body{{height:100%;margin:0}} #chart{{width:100%;height:100vh;}}</style>",
					`  <script src="${{cdn}}"></script>`,
					"</head>",
					"<body>",
					'  <div id="chart"></div>',
					"  <script>",
					"    const el = document.getElementById('chart');",
					`    const inst = echarts.init(el, ${{th}}, {{ renderer: 'svg' }});`,
					`    const option = ${{opt}};`,
					"    inst.setOption(option, true);",
					"    window.addEventListener('resize', () => inst.resize());",
					"  </script>",
					"</body>",
					"</html>",
				].join("\\n");
			}}

			function openPrintWindow(htmlText) {{
				const blob = new Blob([htmlText], {{ type: "text/html" }});
				const url = URL.createObjectURL(blob);
				const win = window.open(url, "_blank");
				if (!win) {{
					window.alert("Popup blocked. Please allow popups for PDF export.");
					return;
				}}
				const tryPrint = () => {{
					try {{
						win.focus();
						win.print();
					}} catch (e) {{
						console.error("Print failed:", e);
					}}
				}};
				// best-effort: print after load
				win.addEventListener("load", () => setTimeout(tryPrint, 250));
			}}

		async function mountChart() {{
			setStatus("Loading ECharts...", false);
			try {{
				// Primary: Load from CDN via script tag (most reliable, proper MIME type).
				if (!window.echarts && ECHARTS_LIB_SOURCE && !String(ECHARTS_LIB_SOURCE).startsWith("/")) {{
					try {{
						setStatus("Loading ECharts from CDN...", false);
						await loadScript(ECHARTS_LIB_SOURCE);
					}} catch (e) {{
						console.warn("CDN ECharts load failed:", e);
					}}
				}}
				// Fallback 1: Local static bundle via fetch+inject (for offline or CDN issues).
				if (!window.echarts && Array.isArray(ECHARTS_FALLBACK_SOURCES) && ECHARTS_FALLBACK_SOURCES.length) {{
					for (let i = 0; i < ECHARTS_FALLBACK_SOURCES.length; i++) {{
						const src = ECHARTS_FALLBACK_SOURCES[i];
						if (!src) continue;
						setStatus("Loading ECharts fallback (" + (i + 1) + "/" + ECHARTS_FALLBACK_SOURCES.length + ")...", false);
						try {{
							if (String(src).startsWith("/")) {{
								await fetchAndInjectScript(src);
							}} else {{
								await loadScript(src);
							}}
						}} catch (e) {{
							console.warn("ECharts fallback failed:", src, e);
						}}
						if (window.echarts) break;
					}}
				}}
				// Fallback 2: If primary source was local and failed, try CDN directly.
				if (!window.echarts && ECHARTS_LIB_SOURCE && String(ECHARTS_LIB_SOURCE).startsWith("/")) {{
					try {{
						setStatus("Loading ECharts from CDN (final fallback)...", false);
						await loadScript("https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js");
					}} catch (e) {{
						console.warn("Final CDN fallback failed:", e);
					}}
				}}
				if (!window.echarts) {{
					console.error("ECharts not loaded.");
					setStatus("ECharts failed to load. Check your internet connection or try refreshing.", true);
					return;
				}}
				const el = document.getElementById("{container_id}");
				if (!el) {{
					setStatus("Chart container element was not found.", true);
					return;
				}}
				setStatus("", false);
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
				const inst = echarts.init(el, ECHARTS_THEME, {{ renderer: ECHARTS_RENDERER }});
				inst.setOption(ECHARTS_OPTION, true);
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
					const fallback = () => inst.resize();
					el.__fallbackInterval = window.setInterval(fallback, 500);
				}}
				requestAnimationFrame(() => inst.resize());
				el.__echartsInstance = inst;
				// Wire export toolbar (optional)
				const toolbar = document.getElementById("{toolbar_id}");
				if (toolbar) {{
					toolbar.addEventListener("click", (evt) => {{
						const target = evt.target;
						if (!target || !target.getAttribute) return;
						const action = target.getAttribute("data-action");
						if (!action) return;
						try {{
							if (action === "png") {{
								const url = inst.getDataURL({{ type: "png", pixelRatio: 3, backgroundColor: "#ffffff" }});
								downloadDataUrl(url, `${{EXPORT_BASENAME}}.png`);
								return;
							}}
							if (action === "svg") {{
								if (ECHARTS_RENDERER !== "svg") {{
									window.alert("SVG export requires renderer='svg'.");
									return;
								}}
								const url = inst.getDataURL({{ type: "svg" }});
								downloadDataUrl(url, `${{EXPORT_BASENAME}}.svg`);
								return;
							}}
							if (action === "json") {{
								downloadText(JSON.stringify(ECHARTS_OPTION, null, 2), `${{EXPORT_BASENAME}}.json`, "application/json");
								return;
							}}
							if (action === "html") {{
								const htmlText = buildPortableHtml(ECHARTS_OPTION, ECHARTS_THEME);
								downloadText(htmlText, `${{EXPORT_BASENAME}}.html`, "text/html");
								return;
							}}
							if (action === "pdf") {{
								const htmlText = buildPortableHtml(ECHARTS_OPTION, ECHARTS_THEME);
								openPrintWindow(htmlText);
								return;
							}}
						}} catch (e) {{
							console.error("Export failed:", e);
							window.alert("Export failed. See browser console for details.");
						}}
					}});
				}}
			}} catch (e) {{
				console.error("Chart render failed:", e);
				const msg = (e && e.message) ? e.message : String(e);
				setStatus("Chart render failed: " + msg, true);
			}}
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
	components.html(html, height=height_px + (50 if enable_export else 20), scrolling=False)

	if caption is not None:
		st.caption(caption)


def st_echarts(
	options: Optional[Dict[str, Any]] = None,
	*,
	height: Union[str, int] = "400px",
	key: Optional[str] = None,  # kept for compatibility; not used (component is stateless)
	renderer: str = "svg",
	enable_export: bool = True,
	export_basename: str = "echarts_chart",
	caption: Optional[str] = None,
	**_: Any,
) -> None:
	"""Compatibility wrapper matching the common `streamlit-echarts` API.

	This project historically used `st_echarts(...)` in a few modules.
	We provide it here as a thin wrapper over `render_echarts` to avoid
	import-time failures and keep the UI functional.

	Args:
		options: ECharts option dictionary.
		height: Height as 'NNNpx' string or integer pixels.
		key: Ignored (present for API compatibility).
		renderer: ECharts renderer ('canvas' or 'svg').
		enable_export: If True, show client-side export buttons.
		export_basename: Base filename for exports.
		caption: Optional caption rendered below the chart.
		**_: Ignored extra keyword arguments for compatibility.
	"""
	if options is None:
		raise ValueError("options must be provided")
	height_px: int
	if isinstance(height, int):
		height_px = height
	else:
		text = str(height).strip().lower()
		if text.endswith("px"):
			text = text[:-2].strip()
		try:
			height_px = int(float(text))
		except ValueError as exc:
			raise ValueError("height must be an int or a 'NNNpx' string") from exc

	_ = key  # intentionally unused (compat)
	render_echarts(
		options,
		height_px=height_px,
		width="100%",
		renderer=renderer,
		enable_export=enable_export,
		export_basename=export_basename,
		caption=caption,
	)


