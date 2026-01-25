# Author: Dr Diego Malpica MD

"""ECharts option builders for Reflex v2 (JSON-serializable).

Design goals:
- Publication-grade defaults (titles, subtitle/method, tooltip, legend, axis labels/units)
- Dark text colors (never light gray)
- Dynamic y-axis bounds (never clip data)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Sequence

import numpy as np
import pandas as pd


def auto_axis_bounds(
    *data_arrays: Sequence[Optional[float]] | None,
    padding_pct: float = 0.12,
    min_floor: Optional[float] = None,
    max_ceil: Optional[float] = None,
    nice_round: bool = True,
) -> tuple[float, float]:
    """Compute safe y-axis bounds that never clip data."""

    values: list[float] = []
    for arr in data_arrays:
        if not arr:
            continue
        for v in arr:
            if v is None:
                continue
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if np.isfinite(fv):
                values.append(fv)

    if not values:
        return (0.0, 1.0)

    vmin = float(np.min(values))
    vmax = float(np.max(values))
    if vmin == vmax:
        pad = max(1.0, abs(vmin) * padding_pct)
        vmin -= pad
        vmax += pad
    else:
        span = vmax - vmin
        pad = span * padding_pct
        vmin -= pad
        vmax += pad

    if min_floor is not None:
        vmin = min(vmin, float(min_floor))
    if max_ceil is not None:
        vmax = max(vmax, float(max_ceil))

    if nice_round:
        # Simple "nice" rounding to 1/2/5 * 10^k.
        def _nice(x: float, up: bool) -> float:
            if x == 0:
                return 0.0
            sign = 1.0 if x >= 0 else -1.0
            ax = abs(x)
            exp = np.floor(np.log10(ax))
            base = 10 ** exp
            frac = ax / base
            steps = [1.0, 2.0, 5.0, 10.0]
            if up:
                step = next((s for s in steps if frac <= s), 10.0)
            else:
                step = next((s for s in reversed(steps) if frac >= s), 1.0)
            return sign * step * base

        vmin = _nice(vmin, up=False)
        vmax = _nice(vmax, up=True)

    return (float(vmin), float(vmax))


def compute_ewma(values: Sequence[Optional[float]], span: int = 7) -> list[Optional[float]]:
    series = pd.Series(values, dtype="float64")
    if series.dropna().size < 2:
        return [v if v is not None else None for v in values]
    smoothed = series.ewm(span=span, adjust=False).mean()
    return [None if np.isnan(v) else float(v) for v in smoothed.to_numpy()]


def compute_reference_band(values: Sequence[Optional[float]]) -> tuple[float, float]:
    arr = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    if arr.size == 0:
        return (0.0, 0.0)
    low = float(np.percentile(arr, 10))
    high = float(np.percentile(arr, 90))
    if low == high:
        high = low + max(1.0, abs(low) * 0.05)
    return (low, high)


def build_time_series_chart(
    dates: Sequence[datetime],
    values: Sequence[Optional[float]],
    *,
    metric_label: str,
    unit: str,
    subtitle: str,
    color_primary: str = "#3498db",
    color_trend: str = "#2c3e50",
    color_band: str = "#3498db",
) -> dict[str, Any]:
    labels = [d.strftime("%Y-%m-%d") for d in dates]
    ref_low, ref_high = compute_reference_band(values)
    ref_low_series = [ref_low for _ in labels]
    ref_band_series = [(ref_high - ref_low) for _ in labels]
    trend = compute_ewma(values, span=7)
    y_min, y_max = auto_axis_bounds(values, trend, ref_low_series)

    return {
        "title": {
            "text": metric_label,
            "subtext": subtitle,
            "left": "center",
            "textStyle": {"fontSize": 16, "fontWeight": "bold", "color": "#1a1a1a"},
            "subtextStyle": {"color": "#2c3e50"},
        },
        "tooltip": {"trigger": "axis", "textStyle": {"color": "#1a1a1a"}},
        "legend": {
            "data": ["Daily mean", "EWMA (7-day)", "Reference band"],
            "top": 28,
            "textStyle": {"color": "#1a1a1a"},
        },
        "grid": {"left": "10%", "right": "6%", "top": "22%", "bottom": "16%"},
        "xAxis": {
            "type": "category",
            "data": labels,
            "name": "Date (UTC)",
            "nameLocation": "middle",
            "nameGap": 30,
            "axisLabel": {"color": "#1a1a1a"},
            "axisLine": {"lineStyle": {"color": "#2c3e50"}},
        },
        "yAxis": {
            "type": "value",
            "name": f"{metric_label} ({unit})" if unit else metric_label,
            "nameLocation": "middle",
            "nameGap": 45,
            "min": y_min,
            "max": y_max,
            "axisLabel": {"color": "#1a1a1a"},
            "axisLine": {"lineStyle": {"color": "#2c3e50"}},
            "splitLine": {"lineStyle": {"color": "rgba(44, 62, 80, 0.1)"}},
        },
        "series": [
            {
                "name": "Reference low",
                "type": "line",
                "data": ref_low_series,
                "stack": "ref",
                "symbol": "none",
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": color_band, "opacity": 0.25},
            },
            {
                "name": "Reference band",
                "type": "line",
                "data": ref_band_series,
                "stack": "ref",
                "symbol": "none",
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": color_band, "opacity": 0.25},
            },
            {
                "name": "Daily mean",
                "type": "line",
                "data": values,
                "symbol": "circle",
                "symbolSize": 6,
                "lineStyle": {"color": color_primary, "width": 2},
                "itemStyle": {"color": color_primary},
            },
            {
                "name": "EWMA (7-day)",
                "type": "line",
                "data": trend,
                "symbol": "none",
                "lineStyle": {"color": color_trend, "width": 2.5},
            },
        ],
    }

