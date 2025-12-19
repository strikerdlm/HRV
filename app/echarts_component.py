"""ECharts component for Streamlit - Professional scientific visualization.

This module provides a robust ECharts integration for Streamlit that:
- Embeds ECharts library inline to avoid CORS/MIME issues
- Falls back to CDN if local bundle unavailable
- Supports SVG renderer for publication-quality vector exports
- Provides client-side export (PNG, SVG, PDF, HTML, JSON)

Usage:
    from echarts_component import render_echarts, EChartsConfig

    option = {
        "title": {"text": "My Chart"},
        "xAxis": {"type": "category", "data": ["A", "B", "C"]},
        "yAxis": {"type": "value"},
        "series": [{"type": "bar", "data": [10, 20, 30]}]
    }
    render_echarts(option, height_px=400)
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Union

import streamlit as st
import streamlit.components.v1 as components


# Path constants
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_LOCAL_ECHARTS_PATH = _PROJECT_ROOT / "node_modules" / "echarts" / "dist" / "echarts.min.js"
_CDN_URL = "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"


@dataclass(slots=True, frozen=True)
class EChartsConfig:
    """Configuration for ECharts rendering.

    Attributes:
        cdn_url: CDN URL for ECharts library (fallback if local unavailable).
        local_echarts_path: Path to local echarts.min.js bundle.
        embed_inline: If True, embed the library inline (avoids CORS issues).
    """
    cdn_url: str = _CDN_URL
    local_echarts_path: Optional[Path] = _LOCAL_ECHARTS_PATH
    embed_inline: bool = True


# Cache for loaded bundles keyed by path string
_BUNDLE_CACHE: Dict[str, str] = {}


def _load_echarts_bundle(path: Optional[Path] = None) -> Optional[str]:
    """Load and cache the ECharts bundle from a local path.

    Args:
        path: Path to the echarts.min.js file. Defaults to node_modules location.

    Returns:
        The minified ECharts JavaScript code, or None if unavailable.
    """
    bundle_path = path if path is not None else _LOCAL_ECHARTS_PATH
    
    if bundle_path is None:
        return None
    
    # Convert to string for cache key
    path_key = str(bundle_path)
    
    # Check cache first
    if path_key in _BUNDLE_CACHE:
        return _BUNDLE_CACHE[path_key]
    
    # Load from disk
    if not bundle_path.exists():
        return None
    try:
        content = bundle_path.read_text(encoding="utf-8")
        # Cache the result (bounded by realistic usage - typically 1-2 paths)
        if len(_BUNDLE_CACHE) < 5:  # Limit cache size
            _BUNDLE_CACHE[path_key] = content
        return content
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
    """Render an ECharts visualization in Streamlit.

    Args:
        option: ECharts option dictionary (must be JSON-serializable).
        height_px: Chart height in pixels (100-4000).
        width: CSS width (e.g., '100%', '800px').
        theme: ECharts theme name (e.g., 'dark').
        config: EChartsConfig for customization.
        renderer: 'svg' (vector, recommended) or 'canvas' (raster).
        enable_export: Show export buttons (PNG, SVG, PDF, HTML, JSON).
        export_basename: Base filename for exports.
        caption: Optional caption below the chart.

    Raises:
        ValueError: If parameters are invalid.
    """
    # Validate inputs
    if not isinstance(height_px, int) or height_px < 100 or height_px > 4000:
        raise ValueError("height_px must be an integer between 100 and 4000")
    if renderer not in {"canvas", "svg"}:
        raise ValueError("renderer must be 'canvas' or 'svg'")
    if not export_basename or not export_basename.strip():
        raise ValueError("export_basename must be a non-empty string")

    cfg = config or EChartsConfig()

    # Generate unique IDs
    uid = uuid.uuid4().hex[:12]
    container_id = f"ec-{uid}"
    toolbar_id = f"tb-{uid}"

    # Serialize option
    option_json = json.dumps(option, separators=(",", ":"), ensure_ascii=False)
    theme_js = f'"{theme}"' if theme else "null"

    # Determine how to load ECharts
    echarts_bundle = _load_echarts_bundle(cfg.local_echarts_path) if cfg.embed_inline else None
    use_inline = echarts_bundle is not None

    if use_inline:
        # Embed the library inline - most reliable approach
        echarts_script = f"<script>{echarts_bundle}</script>"
    else:
        # Fall back to CDN
        echarts_script = f'<script src="{cfg.cdn_url}"></script>'

    # Export toolbar HTML
    toolbar_html = ""
    if enable_export:
        toolbar_html = f'''
<div id="{toolbar_id}" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;font-family:system-ui,-apple-system,sans-serif;">
  <button data-action="png" style="padding:5px 12px;border:1px solid #e5e7eb;border-radius:6px;background:#fff;font-size:13px;cursor:pointer;transition:all 0.2s;">📷 PNG</button>
  <button data-action="svg" style="padding:5px 12px;border:1px solid #e5e7eb;border-radius:6px;background:#fff;font-size:13px;cursor:pointer;transition:all 0.2s;">📐 SVG</button>
  <button data-action="pdf" style="padding:5px 12px;border:1px solid #e5e7eb;border-radius:6px;background:#fff;font-size:13px;cursor:pointer;transition:all 0.2s;">📄 PDF</button>
  <button data-action="html" style="padding:5px 12px;border:1px solid #e5e7eb;border-radius:6px;background:#fff;font-size:13px;cursor:pointer;transition:all 0.2s;">🌐 HTML</button>
  <button data-action="json" style="padding:5px 12px;border:1px solid #e5e7eb;border-radius:6px;background:#fff;font-size:13px;cursor:pointer;transition:all 0.2s;">📋 JSON</button>
</div>'''

    # Build the complete HTML
    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: system-ui, -apple-system, sans-serif; background: transparent; }}
#chart {{ width: {width}; height: {height_px}px; }}
button:hover {{ background: #f3f4f6 !important; border-color: #d1d5db !important; }}
</style>
{echarts_script}
</head>
<body>
{toolbar_html}
<div id="{container_id}" style="width:{width};height:{height_px}px;"></div>
<script>
(function() {{
  "use strict";
  
  var OPTION = {option_json};
  var THEME = {theme_js};
  var RENDERER = "{renderer}";
  var BASENAME = {json.dumps(export_basename)};
  var CDN = "{cfg.cdn_url}";
  
  function initChart() {{
    if (typeof echarts === "undefined") {{
      // ECharts not loaded - try CDN as last resort
      var s = document.createElement("script");
      s.src = CDN;
      s.onload = function() {{ initChart(); }};
      s.onerror = function() {{
        document.getElementById("{container_id}").innerHTML = 
          '<div style="padding:20px;color:#dc2626;text-align:center;">Failed to load ECharts library</div>';
      }};
      document.head.appendChild(s);
      return;
    }}
    
    var el = document.getElementById("{container_id}");
    if (!el) return;
    
    // Dispose existing instance
    var existing = echarts.getInstanceByDom(el);
    if (existing) existing.dispose();
    
    // Initialize chart
    var chart = echarts.init(el, THEME, {{ renderer: RENDERER }});
    chart.setOption(OPTION);
    
    // Handle resize
    var resizeObserver = new ResizeObserver(function() {{ chart.resize(); }});
    resizeObserver.observe(el);
    window.addEventListener("resize", function() {{ chart.resize(); }});
    
    // Export handlers
    var toolbar = document.getElementById("{toolbar_id}");
    if (toolbar) {{
      toolbar.onclick = function(e) {{
        var action = e.target.getAttribute("data-action");
        if (!action) return;
        
        try {{
          if (action === "png") {{
            var url = chart.getDataURL({{ type: "png", pixelRatio: 3, backgroundColor: "#fff" }});
            downloadUrl(url, BASENAME + ".png");
          }}
          else if (action === "svg") {{
            if (RENDERER !== "svg") {{ alert("SVG export requires SVG renderer"); return; }}
            var url = chart.getDataURL({{ type: "svg" }});
            downloadUrl(url, BASENAME + ".svg");
          }}
          else if (action === "json") {{
            downloadText(JSON.stringify(OPTION, null, 2), BASENAME + ".json", "application/json");
          }}
          else if (action === "html") {{
            var html = buildStandaloneHtml(OPTION, THEME);
            downloadText(html, BASENAME + ".html", "text/html");
          }}
          else if (action === "pdf") {{
            var html = buildStandaloneHtml(OPTION, THEME);
            var blob = new Blob([html], {{ type: "text/html" }});
            var url = URL.createObjectURL(blob);
            var win = window.open(url, "_blank");
            if (win) {{
              win.onload = function() {{ setTimeout(function() {{ win.print(); }}, 300); }};
            }}
          }}
        }} catch (err) {{
          console.error("Export error:", err);
          alert("Export failed: " + err.message);
        }}
      }};
    }}
  }}
  
  function downloadUrl(dataUrl, filename) {{
    var a = document.createElement("a");
    a.href = dataUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }}
  
  function downloadText(text, filename, mime) {{
    var blob = new Blob([text], {{ type: mime }});
    var url = URL.createObjectURL(blob);
    downloadUrl(url, filename);
    URL.revokeObjectURL(url);
  }}
  
  function buildStandaloneHtml(opt, theme) {{
    return '<!DOCTYPE html>\\n<html>\\n<head>\\n' +
      '<meta charset="utf-8">\\n' +
      '<title>ECharts Export</title>\\n' +
      '<script src="' + CDN + '"><\\/script>\\n' +
      '<style>html,body{{height:100%;margin:0}}#chart{{width:100%;height:100vh}}</style>\\n' +
      '</head>\\n<body>\\n<div id="chart"></div>\\n<script>\\n' +
      'var chart = echarts.init(document.getElementById("chart"), ' + 
      (theme ? JSON.stringify(theme) : 'null') + ', {{renderer:"svg"}});\\n' +
      'chart.setOption(' + JSON.stringify(opt) + ');\\n' +
      'window.onresize = function(){{chart.resize();}};\\n' +
      '<\\/script>\\n</body>\\n</html>';
  }}
  
  // Initialize when DOM ready
  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", initChart);
  }} else {{
    initChart();
  }}
}})();
</script>
</body>
</html>'''

    # Render the component
    total_height = height_px + (45 if enable_export else 10)
    try:
        components.html(html, height=total_height, scrolling=False)
    except Exception as e:
        # Log all errors for debugging but only show non-cosmetic ones
        error_msg = str(e)
        import logging
        _logger = logging.getLogger(__name__)
        _logger.warning("ECharts render error: %s", error_msg)
        if "SessionInfo" in error_msg or "Bad message" in error_msg:
            # This is a known Streamlit race condition - show placeholder
            st.info("📊 Chart loading... (refresh if not visible)")
        else:
            # Show error in UI for debugging
            st.error(f"Chart render error: {error_msg[:200]}")
            raise

    # Optional caption
    if caption:
        st.caption(caption)


def st_echarts(
    options: Optional[Dict[str, Any]] = None,
    *,
    height: Union[str, int] = "400px",
    key: Optional[str] = None,
    renderer: str = "svg",
    enable_export: bool = True,
    export_basename: str = "echarts_chart",
    caption: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Compatibility wrapper for st_echarts API.

    This provides backwards compatibility with the streamlit-echarts package API.

    Args:
        options: ECharts option dictionary.
        height: Height as 'NNNpx' string or integer.
        key: Ignored (for API compatibility).
        renderer: 'svg' or 'canvas'.
        enable_export: Show export buttons.
        export_basename: Base filename for exports.
        caption: Optional caption.
        **kwargs: Ignored extra arguments.
    """
    if options is None:
        raise ValueError("options must be provided")

    # Parse height
    if isinstance(height, int):
        height_px = height
    else:
        h_str = str(height).strip().lower()
        if h_str.endswith("px"):
            h_str = h_str[:-2]
        try:
            height_px = int(float(h_str))
        except ValueError as e:
            raise ValueError(f"Invalid height: {height}") from e

    # Suppress unused variable warnings
    _ = key
    _ = kwargs

    render_echarts(
        options,
        height_px=height_px,
        renderer=renderer,
        enable_export=enable_export,
        export_basename=export_basename,
        caption=caption,
    )
