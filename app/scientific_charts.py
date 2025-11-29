"""Scientific charts module for publication-ready visualizations.

This module provides ECharts-based visualizations for:
- HRV analysis (time series, frequency domain, Poincaré plots)
- Sleep analysis (hypnograms, sleep architecture)
- Activity analysis (daily patterns, trends)
- ANS balance (sympathovagal balance, circadian patterns)
- Multi-day longitudinal tracking
- Solar-physiology correlations
- Statistical results visualization

All charts are designed for:
- Publication quality (Q1 journal standards)
- Interactive exploration
- Responsive design
- Consistent styling

Color palette based on scientific visualization best practices.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Final

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants and color schemes
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Scientific color palette (colorblind-friendly)
COLORS: Final[dict[str, str]] = {
    "primary": "#2E86AB",      # Steel blue
    "secondary": "#A23B72",    # Raspberry
    "success": "#28965A",      # Forest green
    "warning": "#F18F01",      # Orange
    "danger": "#C73E1D",       # Red
    "info": "#3B8EA5",         # Teal
    "light": "#F5F5F5",        # Light gray
    "dark": "#1A1A2E",         # Dark blue-black
    "hrv": "#2E86AB",          # HRV metrics
    "sleep": "#7B68EE",        # Sleep metrics (medium slate blue)
    "activity": "#28965A",     # Activity metrics
    "solar": "#F18F01",        # Solar activity
    "ans_parasympathetic": "#28965A",  # Vagal/parasympathetic
    "ans_sympathetic": "#C73E1D",      # Sympathetic
}

# Gradient color scales
GRADIENT_BLUE: Final[list[str]] = ["#E3F2FD", "#90CAF9", "#42A5F5", "#1E88E5", "#1565C0"]
GRADIENT_GREEN: Final[list[str]] = ["#E8F5E9", "#A5D6A7", "#66BB6A", "#43A047", "#2E7D32"]
GRADIENT_DIVERGING: Final[list[str]] = ["#D32F2F", "#EF5350", "#FFCDD2", "#E8F5E9", "#66BB6A", "#2E7D32"]


# ---------------------------------------------------------------------------
# Chart configuration dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ChartConfig:
    """Configuration for chart appearance.

    Attributes:
        width: Chart width in pixels or percentage.
        height: Chart height in pixels.
        title_font_size: Title font size.
        label_font_size: Axis label font size.
        show_legend: Whether to show legend.
        animation: Whether to enable animations.
        theme: Chart theme (light/dark).
    """

    width: str = "100%"
    height: int = 400
    title_font_size: int = 16
    label_font_size: int = 12
    show_legend: bool = True
    animation: bool = True
    theme: str = "light"


DEFAULT_CONFIG: Final[ChartConfig] = ChartConfig()


# ---------------------------------------------------------------------------
# Base chart builders
# ---------------------------------------------------------------------------


def _base_chart_options(
    title: str,
    subtitle: str = "",
    config: ChartConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Create base chart options."""
    return {
        "title": {
            "text": title,
            "subtext": subtitle,
            "left": "center",
            "textStyle": {
                "fontSize": config.title_font_size,
                "fontWeight": "bold",
                "color": COLORS["dark"] if config.theme == "light" else COLORS["light"],
            },
            "subtextStyle": {
                "fontSize": config.label_font_size,
                "color": "#666",
            },
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
        },
        "grid": {
            "left": "10%",
            "right": "10%",
            "top": "15%",
            "bottom": "15%",
            "containLabel": True,
        },
        "animation": config.animation,
    }


# ---------------------------------------------------------------------------
# HRV Charts
# ---------------------------------------------------------------------------


def build_hrv_time_series_chart(
    timestamps: list[datetime] | pd.DatetimeIndex,
    rmssd: list[float] | np.ndarray,
    sdnn: list[float] | np.ndarray | None = None,
    mean_hr: list[float] | np.ndarray | None = None,
    title: str = "HRV Time Series",
    config: ChartConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Build HRV time series chart.

    Args:
        timestamps: Time points.
        rmssd: RMSSD values.
        sdnn: Optional SDNN values.
        mean_hr: Optional mean HR values.
        title: Chart title.
        config: Chart configuration.

    Returns:
        ECharts option dict.
    """
    options = _base_chart_options(title, config=config)

    # Format timestamps
    time_labels = [t.strftime("%Y-%m-%d %H:%M") if isinstance(t, datetime) else str(t) for t in timestamps]

    options["xAxis"] = {
        "type": "category",
        "data": time_labels,
        "axisLabel": {"rotate": 45, "fontSize": 10},
    }

    options["yAxis"] = [
        {
            "type": "value",
            "name": "HRV (ms)",
            "position": "left",
            "axisLine": {"lineStyle": {"color": COLORS["hrv"]}},
        },
    ]

    series = [
        {
            "name": "RMSSD",
            "type": "line",
            "data": list(rmssd),
            "smooth": True,
            "lineStyle": {"color": COLORS["hrv"], "width": 2},
            "itemStyle": {"color": COLORS["hrv"]},
            "areaStyle": {"color": COLORS["hrv"], "opacity": 0.1},
        },
    ]

    if sdnn is not None:
        series.append({
            "name": "SDNN",
            "type": "line",
            "data": list(sdnn),
            "smooth": True,
            "lineStyle": {"color": COLORS["secondary"], "width": 2},
            "itemStyle": {"color": COLORS["secondary"]},
        })

    if mean_hr is not None:
        options["yAxis"].append({
            "type": "value",
            "name": "HR (bpm)",
            "position": "right",
            "axisLine": {"lineStyle": {"color": COLORS["danger"]}},
        })
        series.append({
            "name": "Mean HR",
            "type": "line",
            "yAxisIndex": 1,
            "data": list(mean_hr),
            "smooth": True,
            "lineStyle": {"color": COLORS["danger"], "width": 2, "type": "dashed"},
            "itemStyle": {"color": COLORS["danger"]},
        })

    options["series"] = series
    options["legend"] = {
        "data": [s["name"] for s in series],
        "top": "5%",
    }

    return options


def build_frequency_domain_chart(
    frequencies: list[float] | np.ndarray,
    psd: list[float] | np.ndarray,
    vlf_band: tuple[float, float] = (0.003, 0.04),
    lf_band: tuple[float, float] = (0.04, 0.15),
    hf_band: tuple[float, float] = (0.15, 0.4),
    title: str = "HRV Frequency Domain Analysis",
    config: ChartConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Build frequency domain power spectral density chart.

    Args:
        frequencies: Frequency values (Hz).
        psd: Power spectral density values.
        vlf_band: VLF frequency band.
        lf_band: LF frequency band.
        hf_band: HF frequency band.
        title: Chart title.
        config: Chart configuration.

    Returns:
        ECharts option dict.
    """
    options = _base_chart_options(title, config=config)

    freq_list = list(frequencies)
    psd_list = list(psd)

    # Create band markers
    mark_areas = [
        {
            "label": {"show": True, "position": "top"},
            "itemStyle": {"color": "rgba(255, 193, 7, 0.2)"},
            "data": [[{"xAxis": vlf_band[0]}, {"xAxis": vlf_band[1]}]],
        },
        {
            "label": {"show": True, "position": "top"},
            "itemStyle": {"color": "rgba(255, 87, 34, 0.2)"},
            "data": [[{"xAxis": lf_band[0]}, {"xAxis": lf_band[1]}]],
        },
        {
            "label": {"show": True, "position": "top"},
            "itemStyle": {"color": "rgba(76, 175, 80, 0.2)"},
            "data": [[{"xAxis": hf_band[0]}, {"xAxis": hf_band[1]}]],
        },
    ]

    options["xAxis"] = {
        "type": "value",
        "name": "Frequency (Hz)",
        "nameLocation": "middle",
        "nameGap": 30,
        "min": 0,
        "max": 0.5,
    }

    options["yAxis"] = {
        "type": "value",
        "name": "PSD (ms²/Hz)",
        "nameLocation": "middle",
        "nameGap": 50,
    }

    options["series"] = [
        {
            "name": "PSD",
            "type": "line",
            "data": list(zip(freq_list, psd_list)),
            "smooth": True,
            "lineStyle": {"color": COLORS["hrv"], "width": 2},
            "areaStyle": {"color": COLORS["hrv"], "opacity": 0.3},
            "markArea": {"data": mark_areas},
        },
    ]

    # Add band labels
    options["graphic"] = [
        {
            "type": "text",
            "left": "20%",
            "top": "20%",
            "style": {"text": "VLF", "fontSize": 12, "fill": "#FFC107"},
        },
        {
            "type": "text",
            "left": "40%",
            "top": "20%",
            "style": {"text": "LF", "fontSize": 12, "fill": "#FF5722"},
        },
        {
            "type": "text",
            "left": "60%",
            "top": "20%",
            "style": {"text": "HF", "fontSize": 12, "fill": "#4CAF50"},
        },
    ]

    return options


def build_poincare_plot(
    rr_intervals: list[float] | np.ndarray,
    sd1: float | None = None,
    sd2: float | None = None,
    title: str = "Poincaré Plot",
    config: ChartConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Build Poincaré plot (RR[n] vs RR[n+1]).

    Args:
        rr_intervals: RR interval series.
        sd1: SD1 value for ellipse.
        sd2: SD2 value for ellipse.
        title: Chart title.
        config: Chart configuration.

    Returns:
        ECharts option dict.
    """
    rr = np.array(rr_intervals)
    rr_n = rr[:-1]
    rr_n1 = rr[1:]

    options = _base_chart_options(title, config=config)

    # Scatter data
    scatter_data = list(zip(rr_n.tolist(), rr_n1.tolist()))

    # Axis range
    min_val = float(min(rr_n.min(), rr_n1.min()) * 0.95)
    max_val = float(max(rr_n.max(), rr_n1.max()) * 1.05)

    options["xAxis"] = {
        "type": "value",
        "name": "RR[n] (ms)",
        "nameLocation": "middle",
        "nameGap": 30,
        "min": min_val,
        "max": max_val,
    }

    options["yAxis"] = {
        "type": "value",
        "name": "RR[n+1] (ms)",
        "nameLocation": "middle",
        "nameGap": 50,
        "min": min_val,
        "max": max_val,
    }

    series: list[dict[str, Any]] = [
        {
            "name": "RR intervals",
            "type": "scatter",
            "data": scatter_data,
            "symbolSize": 4,
            "itemStyle": {"color": COLORS["hrv"], "opacity": 0.6},
        },
    ]

    # Add identity line
    series.append({
        "name": "Identity line",
        "type": "line",
        "data": [[min_val, min_val], [max_val, max_val]],
        "lineStyle": {"color": "#999", "type": "dashed", "width": 1},
        "symbol": "none",
    })

    # Add SD1/SD2 annotation if provided
    if sd1 is not None and sd2 is not None:
        options["graphic"] = [
            {
                "type": "text",
                "left": "75%",
                "top": "15%",
                "style": {
                    "text": f"SD1: {sd1:.1f} ms\nSD2: {sd2:.1f} ms\nSD1/SD2: {sd1/sd2:.2f}",
                    "fontSize": 12,
                    "fill": COLORS["dark"],
                    "backgroundColor": "rgba(255,255,255,0.8)",
                    "padding": [5, 10],
                    "borderRadius": 5,
                },
            },
        ]

    options["series"] = series

    return options


# ---------------------------------------------------------------------------
# Sleep Charts
# ---------------------------------------------------------------------------


def build_hypnogram_chart(
    timestamps: list[datetime] | pd.DatetimeIndex,
    stages: list[int] | np.ndarray,
    stage_labels: dict[int, str] | None = None,
    title: str = "Sleep Hypnogram",
    config: ChartConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Build sleep hypnogram chart.

    Args:
        timestamps: Time points.
        stages: Sleep stage values (0=Wake, 1=N1, 2=N2, 3=N3, 4=REM).
        stage_labels: Optional custom stage labels.
        title: Chart title.
        config: Chart configuration.

    Returns:
        ECharts option dict.
    """
    if stage_labels is None:
        stage_labels = {0: "Wake", 1: "N1", 2: "N2", 3: "N3", 4: "REM"}

    options = _base_chart_options(title, config=config)

    time_labels = [t.strftime("%H:%M") if isinstance(t, datetime) else str(t) for t in timestamps]

    # Color mapping for stages
    stage_colors = {
        0: COLORS["warning"],      # Wake - orange
        1: "#90CAF9",              # N1 - light blue
        2: "#42A5F5",              # N2 - medium blue
        3: "#1565C0",              # N3 - dark blue
        4: COLORS["sleep"],        # REM - purple
    }

    options["xAxis"] = {
        "type": "category",
        "data": time_labels,
        "axisLabel": {"rotate": 45, "fontSize": 10},
        "name": "Time",
        "nameLocation": "middle",
        "nameGap": 50,
    }

    options["yAxis"] = {
        "type": "category",
        "data": ["Wake", "REM", "N1", "N2", "N3"],
        "inverse": True,
        "name": "Sleep Stage",
    }

    # Map stages to y-axis positions
    stage_to_y = {0: "Wake", 1: "N1", 2: "N2", 3: "N3", 4: "REM"}
    chart_data = []
    for i, stage in enumerate(stages):
        y_val = stage_to_y.get(int(stage), "Wake")
        color = stage_colors.get(int(stage), COLORS["dark"])
        chart_data.append({
            "value": [time_labels[i], y_val],
            "itemStyle": {"color": color},
        })

    options["series"] = [
        {
            "name": "Sleep Stage",
            "type": "line",
            "step": "middle",
            "data": chart_data,
            "lineStyle": {"width": 3},
            "symbol": "none",
        },
    ]

    return options


def build_sleep_architecture_chart(
    wake_pct: float,
    n1_pct: float,
    n2_pct: float,
    n3_pct: float,
    rem_pct: float,
    title: str = "Sleep Architecture",
    config: ChartConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Build sleep architecture pie chart.

    Args:
        wake_pct: Wake percentage.
        n1_pct: N1 percentage.
        n2_pct: N2 percentage.
        n3_pct: N3 percentage.
        rem_pct: REM percentage.
        title: Chart title.
        config: Chart configuration.

    Returns:
        ECharts option dict.
    """
    options = _base_chart_options(title, config=config)

    options["series"] = [
        {
            "name": "Sleep Stages",
            "type": "pie",
            "radius": ["40%", "70%"],
            "avoidLabelOverlap": True,
            "itemStyle": {
                "borderRadius": 10,
                "borderColor": "#fff",
                "borderWidth": 2,
            },
            "label": {
                "show": True,
                "formatter": "{b}: {d}%",
            },
            "emphasis": {
                "label": {"show": True, "fontSize": 14, "fontWeight": "bold"},
            },
            "data": [
                {"value": wake_pct, "name": "Wake", "itemStyle": {"color": COLORS["warning"]}},
                {"value": n1_pct, "name": "N1", "itemStyle": {"color": "#90CAF9"}},
                {"value": n2_pct, "name": "N2", "itemStyle": {"color": "#42A5F5"}},
                {"value": n3_pct, "name": "N3", "itemStyle": {"color": "#1565C0"}},
                {"value": rem_pct, "name": "REM", "itemStyle": {"color": COLORS["sleep"]}},
            ],
        },
    ]

    return options


# ---------------------------------------------------------------------------
# Activity Charts
# ---------------------------------------------------------------------------


def build_activity_trend_chart(
    dates: list[date] | pd.DatetimeIndex,
    steps: list[int] | np.ndarray,
    active_minutes: list[int] | np.ndarray | None = None,
    resting_hr: list[float] | np.ndarray | None = None,
    title: str = "Activity Trends",
    config: ChartConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Build activity trend chart.

    Args:
        dates: Date values.
        steps: Daily step counts.
        active_minutes: Optional active minutes.
        resting_hr: Optional resting heart rate.
        title: Chart title.
        config: Chart configuration.

    Returns:
        ECharts option dict.
    """
    options = _base_chart_options(title, config=config)

    date_labels = [d.strftime("%Y-%m-%d") if isinstance(d, date) else str(d) for d in dates]

    options["xAxis"] = {
        "type": "category",
        "data": date_labels,
        "axisLabel": {"rotate": 45, "fontSize": 10},
    }

    y_axes = [
        {
            "type": "value",
            "name": "Steps",
            "position": "left",
            "axisLine": {"lineStyle": {"color": COLORS["activity"]}},
        },
    ]

    series: list[dict[str, Any]] = [
        {
            "name": "Steps",
            "type": "bar",
            "data": list(steps),
            "itemStyle": {"color": COLORS["activity"]},
        },
    ]

    if active_minutes is not None:
        series.append({
            "name": "Active Minutes",
            "type": "line",
            "data": list(active_minutes),
            "smooth": True,
            "lineStyle": {"color": COLORS["info"], "width": 2},
            "itemStyle": {"color": COLORS["info"]},
        })

    if resting_hr is not None:
        y_axes.append({
            "type": "value",
            "name": "Resting HR (bpm)",
            "position": "right",
            "axisLine": {"lineStyle": {"color": COLORS["danger"]}},
        })
        series.append({
            "name": "Resting HR",
            "type": "line",
            "yAxisIndex": 1,
            "data": list(resting_hr),
            "smooth": True,
            "lineStyle": {"color": COLORS["danger"], "width": 2, "type": "dashed"},
            "itemStyle": {"color": COLORS["danger"]},
        })

    options["yAxis"] = y_axes
    options["series"] = series
    options["legend"] = {
        "data": [s["name"] for s in series],
        "top": "5%",
    }

    return options


# ---------------------------------------------------------------------------
# ANS Balance Charts
# ---------------------------------------------------------------------------


def build_ans_balance_gauge(
    lf_hf_ratio: float,
    title: str = "ANS Balance",
    config: ChartConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Build ANS balance gauge (sympathovagal balance).

    Args:
        lf_hf_ratio: LF/HF ratio value.
        title: Chart title.
        config: Chart configuration.

    Returns:
        ECharts option dict.
    """
    # Clamp ratio for display
    display_ratio = min(max(lf_hf_ratio, 0), 5)

    # Determine balance interpretation
    if lf_hf_ratio < 0.5:
        balance_text = "Parasympathetic Dominant"
        color = COLORS["ans_parasympathetic"]
    elif lf_hf_ratio > 2.0:
        balance_text = "Sympathetic Dominant"
        color = COLORS["ans_sympathetic"]
    else:
        balance_text = "Balanced"
        color = COLORS["primary"]

    return {
        "title": {
            "text": title,
            "subtext": balance_text,
            "left": "center",
            "textStyle": {"fontSize": config.title_font_size, "fontWeight": "bold"},
        },
        "series": [
            {
                "name": "ANS Balance",
                "type": "gauge",
                "min": 0,
                "max": 5,
                "splitNumber": 5,
                "radius": "80%",
                "axisLine": {
                    "lineStyle": {
                        "width": 20,
                        "color": [
                            [0.2, COLORS["ans_parasympathetic"]],
                            [0.6, COLORS["primary"]],
                            [1, COLORS["ans_sympathetic"]],
                        ],
                    },
                },
                "pointer": {
                    "itemStyle": {"color": "auto"},
                    "width": 5,
                },
                "axisTick": {"distance": -20, "length": 8, "lineStyle": {"color": "#fff", "width": 2}},
                "splitLine": {"distance": -20, "length": 20, "lineStyle": {"color": "#fff", "width": 3}},
                "axisLabel": {
                    "color": "inherit",
                    "distance": 30,
                    "fontSize": 12,
                    "formatter": "{value}",
                },
                "detail": {
                    "valueAnimation": True,
                    "formatter": "{value:.2f}",
                    "color": color,
                    "fontSize": 24,
                    "offsetCenter": [0, "70%"],
                },
                "data": [{"value": display_ratio, "name": "LF/HF"}],
            },
        ],
    }


def build_circadian_pattern_chart(
    hours: list[int],
    hrv_by_hour: list[float] | np.ndarray,
    hr_by_hour: list[float] | np.ndarray | None = None,
    title: str = "Circadian HRV Pattern",
    config: ChartConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Build circadian pattern radar chart.

    Args:
        hours: Hour labels (0-23).
        hrv_by_hour: HRV values by hour.
        hr_by_hour: Optional HR values by hour.
        title: Chart title.
        config: Chart configuration.

    Returns:
        ECharts option dict.
    """
    hour_labels = [f"{h:02d}:00" for h in hours]

    options = _base_chart_options(title, config=config)

    # Radar chart setup
    max_hrv = float(max(hrv_by_hour)) * 1.2
    max_hr = float(max(hr_by_hour)) * 1.2 if hr_by_hour is not None else 100

    options["radar"] = {
        "indicator": [{"name": label, "max": max_hrv} for label in hour_labels],
        "shape": "circle",
        "splitNumber": 4,
        "axisName": {"color": "#666"},
    }

    series_data = [
        {
            "value": list(hrv_by_hour),
            "name": "HRV",
            "areaStyle": {"color": COLORS["hrv"], "opacity": 0.3},
            "lineStyle": {"color": COLORS["hrv"], "width": 2},
        },
    ]

    if hr_by_hour is not None:
        # Normalize HR to same scale for visualization
        hr_normalized = [h * max_hrv / max_hr for h in hr_by_hour]
        series_data.append({
            "value": hr_normalized,
            "name": "HR (normalized)",
            "areaStyle": {"color": COLORS["danger"], "opacity": 0.2},
            "lineStyle": {"color": COLORS["danger"], "width": 2, "type": "dashed"},
        })

    options["series"] = [
        {
            "name": "Circadian Pattern",
            "type": "radar",
            "data": series_data,
        },
    ]

    options["legend"] = {
        "data": ["HRV"] + (["HR (normalized)"] if hr_by_hour is not None else []),
        "top": "5%",
    }

    return options


# ---------------------------------------------------------------------------
# Multi-day Longitudinal Charts
# ---------------------------------------------------------------------------


def build_multiday_trend_chart(
    dates: list[date] | pd.DatetimeIndex,
    values: list[float] | np.ndarray,
    rolling_mean: list[float] | np.ndarray | None = None,
    upper_bound: list[float] | np.ndarray | None = None,
    lower_bound: list[float] | np.ndarray | None = None,
    metric_name: str = "Metric",
    title: str = "Multi-day Trend",
    config: ChartConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Build multi-day trend chart with rolling statistics.

    Args:
        dates: Date values.
        values: Daily metric values.
        rolling_mean: Optional rolling mean.
        upper_bound: Optional upper bound (e.g., +1 SD).
        lower_bound: Optional lower bound (e.g., -1 SD).
        metric_name: Name of the metric.
        title: Chart title.
        config: Chart configuration.

    Returns:
        ECharts option dict.
    """
    options = _base_chart_options(title, config=config)

    date_labels = [d.strftime("%Y-%m-%d") if isinstance(d, date) else str(d) for d in dates]

    options["xAxis"] = {
        "type": "category",
        "data": date_labels,
        "axisLabel": {"rotate": 45, "fontSize": 10},
    }

    options["yAxis"] = {
        "type": "value",
        "name": metric_name,
    }

    series: list[dict[str, Any]] = [
        {
            "name": metric_name,
            "type": "scatter",
            "data": list(values),
            "symbolSize": 8,
            "itemStyle": {"color": COLORS["primary"]},
        },
    ]

    if rolling_mean is not None:
        series.append({
            "name": "7-day Mean",
            "type": "line",
            "data": list(rolling_mean),
            "smooth": True,
            "lineStyle": {"color": COLORS["secondary"], "width": 3},
            "symbol": "none",
        })

    if upper_bound is not None and lower_bound is not None:
        # Add confidence band
        band_data = [[float(lb), float(ub)] for lb, ub in zip(lower_bound, upper_bound)]
        series.append({
            "name": "Normal Range",
            "type": "line",
            "data": list(upper_bound),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": COLORS["primary"], "opacity": 0.1},
            "stack": "confidence",
            "symbol": "none",
        })
        series.append({
            "name": "_lower",
            "type": "line",
            "data": list(lower_bound),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "#fff", "opacity": 1},
            "stack": "confidence",
            "symbol": "none",
        })

    options["series"] = series
    options["legend"] = {
        "data": [s["name"] for s in series if not s["name"].startswith("_")],
        "top": "5%",
    }

    return options


def build_correlation_scatter_chart(
    x_values: list[float] | np.ndarray,
    y_values: list[float] | np.ndarray,
    x_label: str,
    y_label: str,
    r: float,
    p_value: float,
    title: str = "Correlation Analysis",
    config: ChartConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Build scatter plot with correlation statistics.

    Args:
        x_values: X-axis values.
        y_values: Y-axis values.
        x_label: X-axis label.
        y_label: Y-axis label.
        r: Correlation coefficient.
        p_value: P-value.
        title: Chart title.
        config: Chart configuration.

    Returns:
        ECharts option dict.
    """
    options = _base_chart_options(title, config=config)

    # Scatter data
    scatter_data = list(zip([float(x) for x in x_values], [float(y) for y in y_values]))

    # Regression line
    x_arr = np.array(x_values)
    y_arr = np.array(y_values)
    slope, intercept = np.polyfit(x_arr, y_arr, 1)
    x_line = [float(x_arr.min()), float(x_arr.max())]
    y_line = [slope * x_line[0] + intercept, slope * x_line[1] + intercept]

    # Significance
    sig_text = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else ""

    options["xAxis"] = {
        "type": "value",
        "name": x_label,
        "nameLocation": "middle",
        "nameGap": 30,
    }

    options["yAxis"] = {
        "type": "value",
        "name": y_label,
        "nameLocation": "middle",
        "nameGap": 50,
    }

    options["series"] = [
        {
            "name": "Data",
            "type": "scatter",
            "data": scatter_data,
            "symbolSize": 8,
            "itemStyle": {"color": COLORS["primary"], "opacity": 0.7},
        },
        {
            "name": "Regression",
            "type": "line",
            "data": [[x_line[0], y_line[0]], [x_line[1], y_line[1]]],
            "lineStyle": {"color": COLORS["danger"], "width": 2},
            "symbol": "none",
        },
    ]

    # Add statistics annotation
    options["graphic"] = [
        {
            "type": "text",
            "left": "75%",
            "top": "15%",
            "style": {
                "text": f"r = {r:.3f}{sig_text}\np = {p_value:.4f}\nn = {len(x_values)}",
                "fontSize": 12,
                "fill": COLORS["dark"],
                "backgroundColor": "rgba(255,255,255,0.9)",
                "padding": [8, 12],
                "borderRadius": 5,
                "borderWidth": 1,
                "borderColor": "#ddd",
            },
        },
    ]

    return options


# ---------------------------------------------------------------------------
# Statistical Results Charts
# ---------------------------------------------------------------------------


def build_effect_size_forest_plot(
    comparisons: list[dict[str, Any]],
    title: str = "Effect Sizes (Forest Plot)",
    config: ChartConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Build forest plot for effect sizes.

    Args:
        comparisons: List of dicts with keys: name, effect_size, ci_low, ci_high, significant.
        title: Chart title.
        config: Chart configuration.

    Returns:
        ECharts option dict.
    """
    options = _base_chart_options(title, config=config)

    names = [c["name"] for c in comparisons]
    effect_sizes = [c["effect_size"] for c in comparisons]
    ci_lows = [c["ci_low"] for c in comparisons]
    ci_highs = [c["ci_high"] for c in comparisons]
    significant = [c.get("significant", False) for c in comparisons]

    # Colors based on significance
    colors = [COLORS["success"] if sig else COLORS["dark"] for sig in significant]

    options["grid"] = {"left": "25%", "right": "15%", "top": "15%", "bottom": "10%"}

    options["xAxis"] = {
        "type": "value",
        "name": "Effect Size (Cohen's d)",
        "nameLocation": "middle",
        "nameGap": 30,
    }

    options["yAxis"] = {
        "type": "category",
        "data": names,
        "axisLabel": {"fontSize": 11},
    }

    # Error bars and points
    error_data = []
    for i, (es, low, high) in enumerate(zip(effect_sizes, ci_lows, ci_highs)):
        error_data.append({
            "value": [es, i],
            "itemStyle": {"color": colors[i]},
        })

    options["series"] = [
        {
            "name": "Effect Size",
            "type": "scatter",
            "data": [[es, i] for i, es in enumerate(effect_sizes)],
            "symbolSize": 12,
            "itemStyle": {"color": COLORS["primary"]},
        },
        {
            "name": "CI",
            "type": "custom",
            "renderItem": """function(params, api) {
                var categoryIndex = api.value(1);
                var low = api.coord([api.value(2), categoryIndex]);
                var high = api.coord([api.value(3), categoryIndex]);
                var height = api.size([0, 1])[1] * 0.1;
                return {
                    type: 'group',
                    children: [{
                        type: 'line',
                        shape: {x1: low[0], y1: low[1], x2: high[0], y2: high[1]},
                        style: {stroke: '#333', lineWidth: 2}
                    }]
                };
            }""",
            "data": [[es, i, low, high] for i, (es, low, high) in enumerate(zip(effect_sizes, ci_lows, ci_highs))],
        },
    ]

    # Add zero line
    options["series"].append({
        "name": "Zero",
        "type": "line",
        "markLine": {
            "data": [{"xAxis": 0}],
            "lineStyle": {"type": "dashed", "color": "#999"},
            "label": {"show": False},
        },
    })

    return options


def build_significance_table_chart(
    results: list[dict[str, Any]],
    title: str = "Statistical Results Summary",
) -> dict[str, Any]:
    """Build table visualization for statistical results.

    Args:
        results: List of result dicts with statistical values.
        title: Chart title.

    Returns:
        Dict with table configuration.
    """
    columns = [
        {"key": "comparison", "label": "Comparison", "width": "25%"},
        {"key": "statistic", "label": "Statistic", "width": "15%"},
        {"key": "p_value", "label": "p-value", "width": "15%"},
        {"key": "effect_size", "label": "Effect Size", "width": "15%"},
        {"key": "interpretation", "label": "Interpretation", "width": "30%"},
    ]

    rows = []
    for r in results:
        p = r.get("p_value", 1.0)
        sig_marker = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""

        rows.append({
            "comparison": r.get("name", ""),
            "statistic": f"{r.get('statistic', 0):.2f}",
            "p_value": f"{p:.4f}{sig_marker}",
            "effect_size": f"{r.get('effect_size', 0):.2f}",
            "interpretation": r.get("interpretation", ""),
            "_highlight": p < 0.05,
        })

    return {
        "title": title,
        "columns": columns,
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Unified Physiological Timeline
# ---------------------------------------------------------------------------


def build_unified_physiology_timeline(
    timestamps: list[datetime] | pd.DatetimeIndex,
    metrics: dict[str, list[float] | np.ndarray],
    metric_configs: dict[str, dict[str, Any]] | None = None,
    title: str = "Unified Physiological Timeline",
    config: ChartConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Build unified timeline showing multiple physiological metrics.

    This creates a synchronized multi-axis chart showing HRV, HR, SpO2, stress,
    and other metrics on aligned time axes for comprehensive analysis.

    Args:
        timestamps: Common time points for all metrics.
        metrics: Dict mapping metric names to value arrays.
            Example: {"RMSSD": [...], "HR": [...], "SpO2": [...]}
        metric_configs: Optional per-metric configuration.
            Example: {"RMSSD": {"unit": "ms", "color": "#2E86AB", "yAxisIndex": 0}}
        title: Chart title.
        config: Chart configuration.

    Returns:
        ECharts option dict.
    """
    options = _base_chart_options(title, subtitle="Time-synchronized physiology", config=config)

    # Format timestamps
    time_labels = [
        t.strftime("%Y-%m-%d %H:%M") if isinstance(t, datetime) else str(t)
        for t in timestamps
    ]

    # Default metric configurations
    default_configs: dict[str, dict[str, Any]] = {
        "RMSSD": {"unit": "ms", "color": COLORS["hrv"], "yAxisIndex": 0, "group": "HRV"},
        "SDNN": {"unit": "ms", "color": "#5DADE2", "yAxisIndex": 0, "group": "HRV"},
        "HR": {"unit": "bpm", "color": COLORS["danger"], "yAxisIndex": 1, "group": "Cardiac"},
        "Mean HR": {"unit": "bpm", "color": COLORS["danger"], "yAxisIndex": 1, "group": "Cardiac"},
        "SpO2": {"unit": "%", "color": "#9B59B6", "yAxisIndex": 2, "group": "Respiratory"},
        "Stress": {"unit": "", "color": COLORS["warning"], "yAxisIndex": 3, "group": "Stress"},
        "Body Battery": {"unit": "", "color": COLORS["success"], "yAxisIndex": 3, "group": "Energy"},
        "Respiration": {"unit": "br/min", "color": "#1ABC9C", "yAxisIndex": 2, "group": "Respiratory"},
        "LF/HF": {"unit": "", "color": COLORS["secondary"], "yAxisIndex": 0, "group": "HRV"},
        "HF Power": {"unit": "ms²", "color": COLORS["ans_parasympathetic"], "yAxisIndex": 0, "group": "HRV"},
        "LF Power": {"unit": "ms²", "color": COLORS["ans_sympathetic"], "yAxisIndex": 0, "group": "HRV"},
    }

    # Merge with provided configs
    final_configs = default_configs.copy()
    if metric_configs:
        for k, v in metric_configs.items():
            if k in final_configs:
                final_configs[k].update(v)
            else:
                final_configs[k] = v

    # X-axis configuration
    options["xAxis"] = {
        "type": "category",
        "data": time_labels,
        "axisLabel": {"rotate": 45, "fontSize": 10},
        "boundaryGap": False,
    }

    # Build Y-axes based on metric groups
    y_axes: list[dict[str, Any]] = []
    used_indices: set[int] = set()

    for metric_name in metrics:
        cfg = final_configs.get(metric_name, {"unit": "", "yAxisIndex": 0})
        idx = cfg.get("yAxisIndex", 0)
        if idx not in used_indices:
            used_indices.add(idx)
            y_axes.append({
                "type": "value",
                "position": "left" if idx % 2 == 0 else "right",
                "offset": (idx // 2) * 60,
                "axisLine": {"show": True, "lineStyle": {"color": cfg.get("color", "#333")}},
                "axisLabel": {"formatter": f"{{value}} {cfg.get('unit', '')}"},
                "splitLine": {"show": idx == 0},
            })

    # Sort y-axes by index
    y_axes_sorted = sorted(enumerate(y_axes), key=lambda x: list(used_indices)[x[0]] if x[0] < len(used_indices) else 999)
    options["yAxis"] = [ya for _, ya in y_axes_sorted] if y_axes else [{"type": "value"}]

    # Build series
    series: list[dict[str, Any]] = []
    for metric_name, values in metrics.items():
        cfg = final_configs.get(metric_name, {"color": "#333", "yAxisIndex": 0})
        color = cfg.get("color", "#333")
        y_idx = cfg.get("yAxisIndex", 0)

        # Convert values to list and handle NaN
        val_list = [float(v) if not np.isnan(v) else None for v in values]

        series.append({
            "name": metric_name,
            "type": "line",
            "data": val_list,
            "yAxisIndex": min(y_idx, len(options["yAxis"]) - 1),
            "smooth": True,
            "lineStyle": {"color": color, "width": 2},
            "itemStyle": {"color": color},
            "symbol": "circle",
            "symbolSize": 4,
            "connectNulls": True,
        })

    options["series"] = series

    # Legend
    options["legend"] = {
        "data": list(metrics.keys()),
        "top": "5%",
        "type": "scroll",
    }

    # Data zoom for interactivity
    options["dataZoom"] = [
        {"type": "inside", "xAxisIndex": 0},
        {"type": "slider", "xAxisIndex": 0, "bottom": "5%"},
    ]

    # Grid adjustment
    options["grid"] = {
        "left": "15%",
        "right": "15%",
        "top": "20%",
        "bottom": "20%",
        "containLabel": True,
    }

    return options


def build_physiology_correlation_matrix(
    correlation_df: pd.DataFrame,
    title: str = "Physiological Metrics Correlation Matrix",
    config: ChartConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Build correlation matrix heatmap for physiological metrics.

    Args:
        correlation_df: Square correlation matrix DataFrame.
        title: Chart title.
        config: Chart configuration.

    Returns:
        ECharts option dict.
    """
    variables = list(correlation_df.columns)
    n_vars = len(variables)

    # Build data array for heatmap
    data = []
    for i, row_name in enumerate(variables):
        for j, col_name in enumerate(variables):
            val = correlation_df.loc[row_name, col_name]
            data.append([j, i, round(float(val), 3) if not np.isnan(val) else None])

    options = _base_chart_options(title, config=config)

    options["tooltip"] = {
        "position": "top",
        "formatter": "{c}",
    }

    options["xAxis"] = {
        "type": "category",
        "data": variables,
        "splitArea": {"show": True},
        "axisLabel": {"rotate": 45, "fontSize": 10},
    }

    options["yAxis"] = {
        "type": "category",
        "data": variables,
        "splitArea": {"show": True},
    }

    options["visualMap"] = {
        "min": -1,
        "max": 1,
        "calculable": True,
        "orient": "horizontal",
        "left": "center",
        "bottom": "0%",
        "inRange": {
            "color": ["#D32F2F", "#FFCDD2", "#FFFFFF", "#C8E6C9", "#2E7D32"],
        },
    }

    options["series"] = [{
        "name": "Correlation",
        "type": "heatmap",
        "data": data,
        "label": {"show": n_vars <= 10, "fontSize": 10},
        "emphasis": {
            "itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0, 0, 0, 0.5)"},
        },
    }]

    options["grid"] = {
        "left": "15%",
        "right": "10%",
        "top": "10%",
        "bottom": "20%",
        "containLabel": True,
    }

    return options


def build_ml_pattern_chart(
    timestamps: list[datetime] | pd.DatetimeIndex,
    values: list[float] | np.ndarray,
    anomaly_mask: list[bool] | np.ndarray,
    trend_line: list[float] | np.ndarray | None = None,
    change_points: list[int] | None = None,
    title: str = "ML Pattern Detection",
    metric_name: str = "Metric",
    config: ChartConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Build chart showing ML-detected patterns, anomalies, and trends.

    Args:
        timestamps: Time points.
        values: Metric values.
        anomaly_mask: Boolean mask for anomalies.
        trend_line: Optional fitted trend line.
        change_points: Optional indices of change points.
        title: Chart title.
        metric_name: Name of the metric.
        config: Chart configuration.

    Returns:
        ECharts option dict.
    """
    options = _base_chart_options(title, subtitle="Anomalies, trends, and change points", config=config)

    time_labels = [
        t.strftime("%Y-%m-%d %H:%M") if isinstance(t, datetime) else str(t)
        for t in timestamps
    ]

    options["xAxis"] = {
        "type": "category",
        "data": time_labels,
        "axisLabel": {"rotate": 45, "fontSize": 10},
    }

    options["yAxis"] = {"type": "value", "name": metric_name}

    # Main series
    series: list[dict[str, Any]] = [{
        "name": metric_name,
        "type": "line",
        "data": list(values),
        "smooth": True,
        "lineStyle": {"color": COLORS["primary"], "width": 2},
        "itemStyle": {"color": COLORS["primary"]},
    }]

    # Anomaly markers
    anomaly_indices = np.where(anomaly_mask)[0]
    if len(anomaly_indices) > 0:
        anomaly_data = [
            {"value": [time_labels[i], float(values[i])], "symbol": "circle", "symbolSize": 12}
            for i in anomaly_indices
        ]
        series.append({
            "name": "Anomalies",
            "type": "scatter",
            "data": anomaly_data,
            "itemStyle": {"color": COLORS["danger"]},
            "symbolSize": 12,
            "z": 10,
        })

    # Trend line
    if trend_line is not None:
        series.append({
            "name": "Trend",
            "type": "line",
            "data": list(trend_line),
            "smooth": True,
            "lineStyle": {"color": COLORS["success"], "width": 2, "type": "dashed"},
            "itemStyle": {"color": COLORS["success"]},
            "symbol": "none",
        })

    # Change point markers
    if change_points:
        mark_lines = [{"xAxis": time_labels[cp]} for cp in change_points if cp < len(time_labels)]
        if mark_lines:
            series[0]["markLine"] = {
                "data": mark_lines,
                "lineStyle": {"color": COLORS["warning"], "type": "dashed", "width": 2},
                "label": {"formatter": "Change Point"},
            }

    options["series"] = series
    options["legend"] = {"data": [s["name"] for s in series], "top": "5%"}
    options["dataZoom"] = [{"type": "inside"}, {"type": "slider", "bottom": "5%"}]

    return options

