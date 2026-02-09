"""Comprehensive gauge builder for HRV metrics visualization.

This module provides functions to generate ECharts gauge configurations for
all HRV metric domains: time-domain, frequency-domain, nonlinear, entropy,
fragmentation, and sleep metrics. Gauges follow a consistent two-ring design
with reference bands from published literature.

Design principles:
- Modern two-ring gauge style with lowered center detail
- Color-coded zones (green/yellow/red) based on clinical thresholds
- Reference bands from peer-reviewed normative data
- Consistent styling across all metric types

References for normative values:
- Nunan D, et al. (2010). Normal values for short-term HRV. PubMed 20663071
- Shaffer F, Ginsberg JP. (2017). HRV metrics and norms. Front Public Health.
- Task Force ESC/NASPE (1996). HRV standards. Eur Heart J.
- PROOF-AF Study (2025). HRF reference values. EHJ Open.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Final

# ---------------------------------------------------------------------------
# Constants: normative reference values
# ---------------------------------------------------------------------------

# Time-domain (short-term, ~5 min, healthy adults)
_SDNN_LOW: Final[float] = 30.0
_SDNN_NORMAL: Final[float] = 50.0
_SDNN_HIGH: Final[float] = 100.0
_SDNN_MAX: Final[float] = 150.0

_RMSSD_LOW: Final[float] = 20.0
_RMSSD_NORMAL: Final[float] = 42.0
_RMSSD_HIGH: Final[float] = 80.0
_RMSSD_MAX: Final[float] = 120.0

_PNN50_LOW: Final[float] = 3.0
_PNN50_NORMAL: Final[float] = 10.0
_PNN50_HIGH: Final[float] = 30.0
_PNN50_MAX: Final[float] = 50.0

_MEAN_HR_LOW: Final[float] = 50.0
_MEAN_HR_NORMAL: Final[float] = 70.0
_MEAN_HR_HIGH: Final[float] = 90.0
_MEAN_HR_MAX: Final[float] = 120.0

# Frequency-domain
_LF_HF_LOW: Final[float] = 0.5
_LF_HF_NORMAL: Final[float] = 2.0
_LF_HF_HIGH: Final[float] = 4.0
_LF_HF_MAX: Final[float] = 8.0

_HF_POWER_LOW: Final[float] = 100.0
_HF_POWER_NORMAL: Final[float] = 500.0
_HF_POWER_HIGH: Final[float] = 1500.0
_HF_POWER_MAX: Final[float] = 3000.0

_LF_POWER_LOW: Final[float] = 200.0
_LF_POWER_NORMAL: Final[float] = 800.0
_LF_POWER_HIGH: Final[float] = 2000.0
_LF_POWER_MAX: Final[float] = 4000.0

_TOTAL_POWER_LOW: Final[float] = 500.0
_TOTAL_POWER_NORMAL: Final[float] = 2000.0
_TOTAL_POWER_HIGH: Final[float] = 5000.0
_TOTAL_POWER_MAX: Final[float] = 10000.0

# Nonlinear (Poincaré, DFA)
_SD1_LOW: Final[float] = 15.0
_SD1_NORMAL: Final[float] = 30.0
_SD1_HIGH: Final[float] = 60.0
_SD1_MAX: Final[float] = 100.0

_SD2_LOW: Final[float] = 30.0
_SD2_NORMAL: Final[float] = 70.0
_SD2_HIGH: Final[float] = 120.0
_SD2_MAX: Final[float] = 180.0

_DFA_ALPHA1_LOW: Final[float] = 0.5
_DFA_ALPHA1_NORMAL: Final[float] = 1.0
_DFA_ALPHA1_HIGH: Final[float] = 1.5
_DFA_ALPHA1_MAX: Final[float] = 2.0

# Entropy
_SAMPEN_LOW: Final[float] = 0.5
_SAMPEN_NORMAL: Final[float] = 1.5
_SAMPEN_HIGH: Final[float] = 2.5
_SAMPEN_MAX: Final[float] = 3.5

_APEN_LOW: Final[float] = 0.5
_APEN_NORMAL: Final[float] = 1.2
_APEN_HIGH: Final[float] = 2.0
_APEN_MAX: Final[float] = 3.0

# Heart Rate Fragmentation (PROOF-AF study)
_PIP_LOW: Final[float] = 30.0
_PIP_NORMAL: Final[float] = 50.0
_PIP_HIGH: Final[float] = 65.0
_PIP_MAX: Final[float] = 100.0

_IALS_LOW: Final[float] = 0.2
_IALS_NORMAL: Final[float] = 0.4
_IALS_HIGH: Final[float] = 0.6
_IALS_MAX: Final[float] = 1.0

# Stress Index (Baevsky)
_SI_LOW: Final[float] = 50.0
_SI_NORMAL: Final[float] = 150.0
_SI_HIGH: Final[float] = 300.0
_SI_MAX: Final[float] = 500.0

# Sleep metrics
_SE_POOR: Final[float] = 75.0
_SE_FAIR: Final[float] = 85.0
_SE_GOOD: Final[float] = 90.0
_SE_MAX: Final[float] = 100.0

_TST_LOW: Final[float] = 5.0
_TST_NORMAL: Final[float] = 7.0
_TST_HIGH: Final[float] = 9.0
_TST_MAX: Final[float] = 12.0

# Respiratory rate (breaths/min)
_RR_LOW: Final[float] = 8.0
_RR_NORMAL: Final[float] = 15.0
_RR_HIGH: Final[float] = 20.0
_RR_MAX: Final[float] = 30.0

# Garmin wellness / activity (Vivosmart 5) — daily summary thresholds
#
# NOTE: Keep Garmin thresholds in a distinct namespace to avoid accidental
# shadowing/overwrites (these constants are used by the Garmin gauges).
_GARMIN_STEPS_LOW: Final[float] = 4000.0
_GARMIN_STEPS_NORMAL: Final[float] = 8000.0
_GARMIN_STEPS_HIGH: Final[float] = 12000.0
_GARMIN_STEPS_MAX: Final[float] = 20000.0

_GARMIN_DISTANCE_KM_LOW: Final[float] = 3.0
_GARMIN_DISTANCE_KM_NORMAL: Final[float] = 5.0
_GARMIN_DISTANCE_KM_HIGH: Final[float] = 10.0
_GARMIN_DISTANCE_KM_MAX: Final[float] = 20.0

_GARMIN_CALORIES_KCAL_LOW: Final[float] = 1200.0
_GARMIN_CALORIES_KCAL_NORMAL: Final[float] = 2000.0
_GARMIN_CALORIES_KCAL_HIGH: Final[float] = 3200.0
_GARMIN_CALORIES_KCAL_MAX: Final[float] = 6000.0

_GARMIN_RESTING_HR_LOW: Final[float] = 45.0
_GARMIN_RESTING_HR_NORMAL: Final[float] = 60.0
_GARMIN_RESTING_HR_HIGH: Final[float] = 75.0
_GARMIN_RESTING_HR_MAX: Final[float] = 120.0

_GARMIN_STRESS_SCORE_LOW: Final[float] = 10.0
_GARMIN_STRESS_SCORE_NORMAL: Final[float] = 30.0
_GARMIN_STRESS_SCORE_HIGH: Final[float] = 50.0
_GARMIN_STRESS_SCORE_MAX: Final[float] = 100.0

_GARMIN_SPO2_LOW: Final[float] = 90.0
_GARMIN_SPO2_NORMAL: Final[float] = 95.0
_GARMIN_SPO2_HIGH: Final[float] = 98.0
_GARMIN_SPO2_MAX: Final[float] = 100.0

_RESP_AWAKE_LOW: Final[float] = 10.0
_RESP_AWAKE_NORMAL: Final[float] = 14.0
_RESP_AWAKE_HIGH: Final[float] = 20.0
_RESP_AWAKE_MAX: Final[float] = 30.0

_RESP_SLEEP_LOW: Final[float] = 10.0
_RESP_SLEEP_NORMAL: Final[float] = 13.0
_RESP_SLEEP_HIGH: Final[float] = 17.0
_RESP_SLEEP_MAX: Final[float] = 24.0

_BB_ENERGY_LOW: Final[float] = 10.0
_BB_ENERGY_NORMAL: Final[float] = 40.0
_BB_ENERGY_HIGH: Final[float] = 70.0
_BB_ENERGY_MAX: Final[float] = 100.0

_BB_LEVEL_LOW: Final[float] = 25.0
_BB_LEVEL_NORMAL: Final[float] = 50.0
_BB_LEVEL_HIGH: Final[float] = 75.0
_BB_LEVEL_MAX: Final[float] = 100.0

# Hydration / Thermoregulation
# Sweat rate (mL/h) — Sawka et al. (2007)
_SWEAT_RATE_LOW: Final[float] = 200.0
_SWEAT_RATE_NORMAL: Final[float] = 600.0
_SWEAT_RATE_HIGH: Final[float] = 1500.0
_SWEAT_RATE_MAX: Final[float] = 3000.0

# Dehydration (% body mass loss) — Cheuvront & Kenefick (2014)
_DEHY_LOW: Final[float] = 1.0
_DEHY_NORMAL: Final[float] = 2.0
_DEHY_HIGH: Final[float] = 4.0
_DEHY_MAX: Final[float] = 8.0

# Core temperature (C) — Gonzalez-Alonso et al. (1999)
_CORE_TEMP_LOW: Final[float] = 36.5
_CORE_TEMP_NORMAL: Final[float] = 37.5
_CORE_TEMP_HIGH: Final[float] = 39.0
_CORE_TEMP_MAX: Final[float] = 41.0

# Physiological Strain Index (0-10) — Moran et al. (1998)
_PHSI_LOW: Final[float] = 3.0
_PHSI_NORMAL: Final[float] = 5.0
_PHSI_HIGH: Final[float] = 7.0
_PHSI_MAX: Final[float] = 10.0

# Performance remaining (%) — Cheuvront & Kenefick (2014)
_PERF_LOW: Final[float] = 60.0
_PERF_NORMAL: Final[float] = 80.0
_PERF_HIGH: Final[float] = 95.0
_PERF_MAX: Final[float] = 100.0

# Fluid replacement recommendation (mL/h)
_FLUID_REC_LOW: Final[float] = 200.0
_FLUID_REC_NORMAL: Final[float] = 500.0
_FLUID_REC_HIGH: Final[float] = 900.0
_FLUID_REC_MAX: Final[float] = 1500.0


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GaugeThresholds:
    """Thresholds for gauge color zones.

    Attributes:
        low: Lower boundary (red zone below this).
        normal: Normal range center.
        high: Upper boundary (yellow zone above this).
        max_val: Maximum scale value.
        unit: Unit label for display.
        invert_colors: If True, high values are bad (red).
    """

    low: float
    normal: float
    high: float
    max_val: float
    unit: str = ""
    invert_colors: bool = False


# ---------------------------------------------------------------------------
# Threshold configurations for each metric
# ---------------------------------------------------------------------------

_GAUGE_THRESHOLDS: dict[str, GaugeThresholds] = {
    # Time-domain (standard)
    "sdnn": GaugeThresholds(_SDNN_LOW, _SDNN_NORMAL, _SDNN_HIGH, _SDNN_MAX, "ms"),
    "rmssd": GaugeThresholds(_RMSSD_LOW, _RMSSD_NORMAL, _RMSSD_HIGH, _RMSSD_MAX, "ms"),
    "pnn50": GaugeThresholds(_PNN50_LOW, _PNN50_NORMAL, _PNN50_HIGH, _PNN50_MAX, "%"),
    "mean_hr": GaugeThresholds(_MEAN_HR_LOW, _MEAN_HR_NORMAL, _MEAN_HR_HIGH, _MEAN_HR_MAX, "bpm", invert_colors=True),
    "mean_nni": GaugeThresholds(600, 857, 1000, 1200, "ms"),  # ~70 bpm center
    
    # Time-domain (extended)
    "ln_rmssd": GaugeThresholds(2.5, 3.5, 4.2, 5.0, ""),  # Natural log scale
    "pnn20": GaugeThresholds(10, 25, 45, 70, "%"),
    "pnn10": GaugeThresholds(25, 45, 65, 85, "%"),
    "pnn30": GaugeThresholds(5, 15, 30, 50, "%"),
    "hr_range": GaugeThresholds(10, 25, 45, 80, "bpm"),
    
    # Long-term HRV (24h recordings)
    "sdann": GaugeThresholds(80, 120, 160, 200, "ms"),
    "sdnni": GaugeThresholds(30, 50, 80, 120, "ms"),

    # Frequency-domain
    "lf_hf_ratio": GaugeThresholds(_LF_HF_LOW, _LF_HF_NORMAL, _LF_HF_HIGH, _LF_HF_MAX, ""),
    "hf_power": GaugeThresholds(_HF_POWER_LOW, _HF_POWER_NORMAL, _HF_POWER_HIGH, _HF_POWER_MAX, "ms²"),
    "lf_power": GaugeThresholds(_LF_POWER_LOW, _LF_POWER_NORMAL, _LF_POWER_HIGH, _LF_POWER_MAX, "ms²"),
    "total_power": GaugeThresholds(_TOTAL_POWER_LOW, _TOTAL_POWER_NORMAL, _TOTAL_POWER_HIGH, _TOTAL_POWER_MAX, "ms²"),
    "hf_nu": GaugeThresholds(20, 40, 60, 100, "%"),
    "lf_nu": GaugeThresholds(20, 50, 70, 100, "%"),

    # Nonlinear (Poincaré)
    "sd1": GaugeThresholds(_SD1_LOW, _SD1_NORMAL, _SD1_HIGH, _SD1_MAX, "ms"),
    "sd2": GaugeThresholds(_SD2_LOW, _SD2_NORMAL, _SD2_HIGH, _SD2_MAX, "ms"),
    "sd1_sd2_ratio": GaugeThresholds(0.15, 0.35, 0.55, 1.0, ""),
    "cvi": GaugeThresholds(2.5, 3.5, 4.5, 6.0, ""),  # Cardiac Vagal Index (log scale)
    "csi": GaugeThresholds(1.0, 2.5, 4.0, 8.0, "", invert_colors=True),  # Cardiac Sympathetic Index
    
    # Nonlinear (DFA)
    "dfa_alpha1": GaugeThresholds(_DFA_ALPHA1_LOW, _DFA_ALPHA1_NORMAL, _DFA_ALPHA1_HIGH, _DFA_ALPHA1_MAX, ""),
    "dfa_alpha2": GaugeThresholds(0.5, 0.9, 1.2, 1.5, ""),

    # Entropy
    "sample_entropy": GaugeThresholds(_SAMPEN_LOW, _SAMPEN_NORMAL, _SAMPEN_HIGH, _SAMPEN_MAX, ""),
    "approx_entropy": GaugeThresholds(_APEN_LOW, _APEN_NORMAL, _APEN_HIGH, _APEN_MAX, ""),

    # Fragmentation
    "hrf_pip": GaugeThresholds(_PIP_LOW, _PIP_NORMAL, _PIP_HIGH, _PIP_MAX, "%", invert_colors=True),
    "hrf_ials": GaugeThresholds(_IALS_LOW, _IALS_NORMAL, _IALS_HIGH, _IALS_MAX, "", invert_colors=True),
    "hrf_w3": GaugeThresholds(10, 20, 30, 100, "%", invert_colors=True),

    # Geometric
    "stress_index": GaugeThresholds(_SI_LOW, _SI_NORMAL, _SI_HIGH, _SI_MAX, "", invert_colors=True),
    "hrv_triangular_index": GaugeThresholds(5, 15, 30, 50, ""),

    # Autonomic indices
    "parasympathetic_index": GaugeThresholds(0.2, 0.5, 0.8, 1.0, ""),
    "sympathetic_index": GaugeThresholds(0.1, 0.3, 0.6, 1.0, "", invert_colors=True),
    "ans_balance": GaugeThresholds(-0.5, 0.0, 0.5, 1.0, ""),

    # Sleep
    "sleep_efficiency": GaugeThresholds(_SE_POOR, _SE_FAIR, _SE_GOOD, _SE_MAX, "%"),
    "tst_hours": GaugeThresholds(_TST_LOW, _TST_NORMAL, _TST_HIGH, _TST_MAX, "h"),
    "waso_minutes": GaugeThresholds(10, 20, 40, 60, "min", invert_colors=True),
    "sol_minutes": GaugeThresholds(5, 15, 30, 60, "min", invert_colors=True),

    # Respiratory
    "respiratory_rate_bpm": GaugeThresholds(_RR_LOW, _RR_NORMAL, _RR_HIGH, _RR_MAX, "br/min"),

    # Garmin wellness & activity
    "steps": GaugeThresholds(_GARMIN_STEPS_LOW, _GARMIN_STEPS_NORMAL, _GARMIN_STEPS_HIGH, _GARMIN_STEPS_MAX, ""),
    "distance_km": GaugeThresholds(
        _GARMIN_DISTANCE_KM_LOW,
        _GARMIN_DISTANCE_KM_NORMAL,
        _GARMIN_DISTANCE_KM_HIGH,
        _GARMIN_DISTANCE_KM_MAX,
        "km",
    ),
    "calories_kcal": GaugeThresholds(
        _GARMIN_CALORIES_KCAL_LOW,
        _GARMIN_CALORIES_KCAL_NORMAL,
        _GARMIN_CALORIES_KCAL_HIGH,
        _GARMIN_CALORIES_KCAL_MAX,
        "kcal",
    ),
    "resting_hr_bpm": GaugeThresholds(
        _GARMIN_RESTING_HR_LOW,
        _GARMIN_RESTING_HR_NORMAL,
        _GARMIN_RESTING_HR_HIGH,
        _GARMIN_RESTING_HR_MAX,
        "bpm",
        invert_colors=True,
    ),
    "avg_hr_bpm": GaugeThresholds(_MEAN_HR_LOW, _MEAN_HR_NORMAL, _MEAN_HR_HIGH, _MEAN_HR_MAX, "bpm", invert_colors=True),
    "stress_score": GaugeThresholds(
        _GARMIN_STRESS_SCORE_LOW,
        _GARMIN_STRESS_SCORE_NORMAL,
        _GARMIN_STRESS_SCORE_HIGH,
        _GARMIN_STRESS_SCORE_MAX,
        "",
        invert_colors=True,
    ),
    "sleep_score": GaugeThresholds(60.0, 80.0, 90.0, 100.0, ""),
    "sleep_duration_hours": GaugeThresholds(_TST_LOW, _TST_NORMAL, _TST_HIGH, _TST_MAX, "h"),
    "spo2_pct": GaugeThresholds(_GARMIN_SPO2_LOW, _GARMIN_SPO2_NORMAL, _GARMIN_SPO2_HIGH, _GARMIN_SPO2_MAX, "%"),
    "respiration_awake_bpm": GaugeThresholds(_RESP_AWAKE_LOW, _RESP_AWAKE_NORMAL, _RESP_AWAKE_HIGH, _RESP_AWAKE_MAX, "br/min"),
    "respiration_sleep_bpm": GaugeThresholds(_RESP_SLEEP_LOW, _RESP_SLEEP_NORMAL, _RESP_SLEEP_HIGH, _RESP_SLEEP_MAX, "br/min"),
    "body_battery_avg": GaugeThresholds(_BB_LEVEL_LOW, _BB_LEVEL_NORMAL, _BB_LEVEL_HIGH, _BB_LEVEL_MAX, ""),
    "body_battery_charge": GaugeThresholds(_BB_ENERGY_LOW, _BB_ENERGY_NORMAL, _BB_ENERGY_HIGH, _BB_ENERGY_MAX, "", invert_colors=False),
    "body_battery_drain": GaugeThresholds(_BB_ENERGY_LOW, _BB_ENERGY_NORMAL, _BB_ENERGY_HIGH, _BB_ENERGY_MAX, "", invert_colors=True),

    # Hydration / Thermoregulation gauges
    "sweat_rate_ml_h": GaugeThresholds(_SWEAT_RATE_LOW, _SWEAT_RATE_NORMAL, _SWEAT_RATE_HIGH, _SWEAT_RATE_MAX, "mL/h", invert_colors=True),
    "dehydration_pct": GaugeThresholds(_DEHY_LOW, _DEHY_NORMAL, _DEHY_HIGH, _DEHY_MAX, "%BM", invert_colors=True),
    "core_temp_c": GaugeThresholds(_CORE_TEMP_LOW, _CORE_TEMP_NORMAL, _CORE_TEMP_HIGH, _CORE_TEMP_MAX, "C", invert_colors=True),
    "phsi_value": GaugeThresholds(_PHSI_LOW, _PHSI_NORMAL, _PHSI_HIGH, _PHSI_MAX, "", invert_colors=True),
    "overall_performance_pct": GaugeThresholds(_PERF_LOW, _PERF_NORMAL, _PERF_HIGH, _PERF_MAX, "%"),
    "fluid_replacement_ml_h": GaugeThresholds(_FLUID_REC_LOW, _FLUID_REC_NORMAL, _FLUID_REC_HIGH, _FLUID_REC_MAX, "mL/h"),
}


# ---------------------------------------------------------------------------
# Gauge building functions
# ---------------------------------------------------------------------------


def _clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range [min_val, max_val]."""
    return max(min_val, min(value, max_val))


def _format_value(value: float, decimals: int = 1) -> str:
    """Format value for display."""
    if abs(value) >= 1000:
        return f"{value:.0f}"
    if abs(value) >= 100:
        return f"{value:.0f}"
    if abs(value) >= 10:
        return f"{value:.1f}"
    return f"{value:.{decimals}f}"


def build_two_ring_gauge(
    metric_name: str,
    value: float,
    *,
    title: str | None = None,
    thresholds: GaugeThresholds | None = None,
    show_reference_band: bool = True,
) -> dict[str, Any]:
    """Build a modern two-ring gauge for a single HRV metric.

    The gauge uses:
    - Outer ring: colored progress arc showing current value
    - Inner ring: reference band with normal range highlighted
    - Center: large value display with unit

    Args:
        metric_name: Key for looking up default thresholds.
        value: Current metric value.
        title: Optional title override.
        thresholds: Optional custom thresholds.
        show_reference_band: Whether to show the inner reference ring.

    Returns:
        ECharts option dictionary.
    """
    # Get thresholds
    thresh = thresholds or _GAUGE_THRESHOLDS.get(
        metric_name,
        GaugeThresholds(0, 50, 75, 100, ""),
    )

    # Clamp value to scale
    display_value = _clamp(value, 0, thresh.max_val)

    # Determine color based on value and zones
    if thresh.invert_colors:
        # High is bad
        if value <= thresh.low:
            value_color = "#52c41a"  # Green
        elif value <= thresh.normal:
            value_color = "#73d13d"  # Light green
        elif value <= thresh.high:
            value_color = "#faad14"  # Yellow
        else:
            value_color = "#ff4d4f"  # Red
    else:
        # Low is bad
        if value < thresh.low:
            value_color = "#ff4d4f"  # Red
        elif value < thresh.normal:
            value_color = "#faad14"  # Yellow
        elif value <= thresh.high:
            value_color = "#52c41a"  # Green
        else:
            value_color = "#73d13d"  # Light green (very high)

    # Build axis line color stops for outer ring
    if thresh.invert_colors:
        axis_line_color = [
            [thresh.low / thresh.max_val, "#52c41a"],
            [thresh.normal / thresh.max_val, "#73d13d"],
            [thresh.high / thresh.max_val, "#faad14"],
            [1, "#ff4d4f"],
        ]
    else:
        axis_line_color = [
            [thresh.low / thresh.max_val, "#ff4d4f"],
            [thresh.normal / thresh.max_val, "#faad14"],
            [thresh.high / thresh.max_val, "#52c41a"],
            [1, "#73d13d"],
        ]

    # Title (shown outside the gauge by the ECharts renderer)
    display_title = title or metric_name.replace("_", " ").title()

    # Build gauge series
    series: list[dict[str, Any]] = []

    # Outer progress ring
    series.append({
        "type": "gauge",
        "center": ["50%", "60%"],
        "radius": "85%",
        "startAngle": 200,
        "endAngle": -20,
        "min": 0,
        "max": thresh.max_val,
        "splitNumber": 5,
        "itemStyle": {
            "color": value_color,
        },
        "progress": {
            "show": True,
            "width": 8,
            "roundCap": True,
        },
        "pointer": {
            "show": True,
            "length": "60%",
            "width": 6,
            "itemStyle": {
                "color": value_color,
            },
        },
        "axisLine": {
            "lineStyle": {
                "width": 8,
                "color": axis_line_color,
            },
        },
        "axisTick": {
            "show": True,
            "distance": -25,
            "length": 6,
            "lineStyle": {
                "color": "#999",
                "width": 1,
            },
        },
        "splitLine": {
            "show": True,
            "distance": -30,
            "length": 12,
            "lineStyle": {
                "color": "#999",
                "width": 2,
            },
        },
        "axisLabel": {
            "show": True,
            "distance": 35,
            "color": "#666",
            "fontSize": 11,
            "formatter": "{value}",
        },
        "anchor": {
            "show": True,
            "size": 12,
            "itemStyle": {
                "borderColor": value_color,
                "borderWidth": 2,
            },
        },
        # Hide the in-gauge title; the app shows titles outside the plot area.
        "title": {"show": False},
        "detail": {
            "show": True,
            "offsetCenter": [0, "35%"],
            "fontSize": 32,
            "fontWeight": "bold",
            "color": value_color,
            "formatter": f"{{value}} {thresh.unit}",
            "valueAnimation": False,
        },
        "data": [
            {
                "value": round(display_value, 2),
                "name": display_title,
            },
        ],
    })

    # Inner reference ring (optional)
    if show_reference_band:
        # Reference band showing normal range
        ref_series: dict[str, Any] = {
            "type": "gauge",
            "center": ["50%", "60%"],
            "radius": "55%",
            "startAngle": 200,
            "endAngle": -20,
            "min": 0,
            "max": thresh.max_val,
            "itemStyle": {
                "color": "transparent",
            },
            "progress": {
                "show": False,
            },
            "pointer": {
                "show": False,
            },
            "axisLine": {
                "lineStyle": {
                    "width": 8,
                    "color": [
                        [thresh.low / thresh.max_val, "rgba(255, 77, 79, 0.3)"],
                        [thresh.high / thresh.max_val, "rgba(82, 196, 26, 0.3)"],
                        [1, "rgba(250, 173, 20, 0.3)"],
                    ] if not thresh.invert_colors else [
                        [thresh.low / thresh.max_val, "rgba(82, 196, 26, 0.3)"],
                        [thresh.high / thresh.max_val, "rgba(250, 173, 20, 0.3)"],
                        [1, "rgba(255, 77, 79, 0.3)"],
                    ],
                },
            },
            "axisTick": {"show": False},
            "splitLine": {"show": False},
            "axisLabel": {"show": False},
            "detail": {"show": False},
            "data": [],
        }
        series.append(ref_series)

    return {
        # Provide a chart-level title so the renderer can display it outside the plot.
        "title": {"text": display_title, "show": True},
        "series": series,
        "backgroundColor": "transparent",
    }


def build_metric_gauges_grid(
    metrics: dict[str, float],
    *,
    metric_keys: list[str] | None = None,
    columns: int = 3,
) -> list[dict[str, Any]]:
    """Build a grid of gauges for multiple metrics.

    Args:
        metrics: Dictionary of metric name -> value.
        metric_keys: Optional list of keys to include (in order).
        columns: Number of columns in the grid.

    Returns:
        List of ECharts option dictionaries, one per metric.
    """
    keys = metric_keys or list(metrics.keys())
    gauges: list[dict[str, Any]] = []

    for key in keys:
        if key in metrics and key in _GAUGE_THRESHOLDS:
            value = metrics[key]
            if value is not None and not math.isnan(value):
                gauge = build_two_ring_gauge(key, value)
                gauges.append(gauge)

    return gauges


def build_summary_gauge_panel(
    metrics: dict[str, float],
) -> dict[str, list[dict[str, Any]]]:
    """Build gauge panels organized by domain.

    Args:
        metrics: Dictionary of all computed metrics.

    Returns:
        Dictionary with domain keys and lists of gauge options.
    """
    panels: dict[str, list[dict[str, Any]]] = {
        "time_domain": [],
        "frequency_domain": [],
        "nonlinear": [],
        "entropy": [],
        "fragmentation": [],
        "autonomic": [],
        "geometric": [],
        "sleep": [],
    }

    # Time-domain
    for key in ["sdnn", "rmssd", "pnn50", "mean_hr", "mean_nni"]:
        if key in metrics and metrics[key] is not None:
            panels["time_domain"].append(build_two_ring_gauge(key, metrics[key]))

    # Frequency-domain
    for key in ["lf_hf_ratio", "hf_power", "lf_power", "total_power", "hf_nu", "lf_nu"]:
        if key in metrics and metrics[key] is not None:
            panels["frequency_domain"].append(build_two_ring_gauge(key, metrics[key]))

    # Nonlinear
    for key in ["sd1", "sd2", "dfa_alpha1", "dfa_alpha2"]:
        if key in metrics and metrics[key] is not None:
            panels["nonlinear"].append(build_two_ring_gauge(key, metrics[key]))

    # Entropy
    for key in ["sample_entropy", "approx_entropy"]:
        if key in metrics and metrics[key] is not None:
            panels["entropy"].append(build_two_ring_gauge(key, metrics[key]))

    # Fragmentation
    for key in ["hrf_pip", "hrf_ials", "hrf_w3"]:
        if key in metrics and metrics[key] is not None:
            panels["fragmentation"].append(build_two_ring_gauge(key, metrics[key]))

    # Autonomic indices
    for key in ["parasympathetic_index", "sympathetic_index", "ans_balance", "stress_index"]:
        if key in metrics and metrics[key] is not None:
            panels["autonomic"].append(build_two_ring_gauge(key, metrics[key]))

    # Geometric
    for key in ["hrv_triangular_index"]:
        if key in metrics and metrics[key] is not None:
            panels["geometric"].append(build_two_ring_gauge(key, metrics[key]))

    # Sleep (if available)
    for key in ["sleep_efficiency", "tst_hours", "waso_minutes", "sol_minutes"]:
        if key in metrics and metrics[key] is not None:
            panels["sleep"].append(build_two_ring_gauge(key, metrics[key]))

    return panels


# ---------------------------------------------------------------------------
# Specialized gauges
# ---------------------------------------------------------------------------


def build_readiness_gauge(
    readiness_percentile: float,
    category: str,
) -> dict[str, Any]:
    """Build a readiness gauge with Kubios-style categories.

    Args:
        readiness_percentile: Percentile value (0-100).
        category: Category string (VERY LOW/LOW/NORMAL/HIGH).

    Returns:
        ECharts option dictionary.
    """
    # Color by category
    category_colors = {
        "VERY LOW": "#ff4d4f",
        "LOW": "#faad14",
        "NORMAL": "#52c41a",
        "HIGH": "#1890ff",
    }
    color = category_colors.get(category.upper(), "#666")

    return {
        "series": [
            {
                "type": "gauge",
                "center": ["50%", "60%"],
                "radius": "85%",
                "startAngle": 200,
                "endAngle": -20,
                "min": 0,
                "max": 100,
                "splitNumber": 5,
                "itemStyle": {"color": color},
                "progress": {
                    "show": True,
                    "width": 20,
                    "roundCap": True,
                },
                "pointer": {
                    "show": True,
                    "length": "60%",
                    "width": 6,
                    "itemStyle": {"color": color},
                },
                "axisLine": {
                    "lineStyle": {
                        "width": 20,
                        "color": [
                            [0.20, "#ff4d4f"],  # Very Low
                            [0.40, "#faad14"],  # Low
                            [0.70, "#52c41a"],  # Normal
                            [1.00, "#1890ff"],  # High
                        ],
                    },
                },
                "axisTick": {"show": True, "distance": -25, "length": 6},
                "splitLine": {"show": True, "distance": -30, "length": 12},
                "axisLabel": {
                    "show": True,
                    "distance": 35,
                    "fontSize": 11,
                    "formatter": "{value}%",
                },
                "title": {
                    "show": True,
                    "offsetCenter": [0, "75%"],
                    "fontSize": 14,
                    "fontWeight": "bold",
                },
                "detail": {
                    "show": True,
                    "offsetCenter": [0, "40%"],
                    "fontSize": 24,
                    "fontWeight": "bold",
                    "color": color,
                    "formatter": f"{{value}}%\n{category}",
                },
                "data": [{"value": round(readiness_percentile, 1), "name": "Readiness"}],
            },
        ],
    }


def build_respiratory_gauge(
    respiratory_rate: float,
) -> dict[str, Any]:
    """Build a respiratory rate gauge.

    Args:
        respiratory_rate: Breaths per minute.

    Returns:
        ECharts option dictionary.
    """
    return build_two_ring_gauge(
        "respiratory_rate_bpm",
        respiratory_rate,
        title="Respiratory Rate",
    )


def build_ans_balance_gauge(
    parasympathetic: float,
    sympathetic: float,
) -> dict[str, Any]:
    """Build an ANS balance gauge showing PNS vs SNS.

    Args:
        parasympathetic: Parasympathetic index (0-1).
        sympathetic: Sympathetic index (0-1).

    Returns:
        ECharts option dictionary.
    """
    balance = parasympathetic - sympathetic
    
    # Color based on balance
    if balance > 0.2:
        color = "#52c41a"  # Parasympathetic dominant
    elif balance < -0.2:
        color = "#ff4d4f"  # Sympathetic dominant
    else:
        color = "#faad14"  # Balanced

    return {
        "series": [
            {
                "type": "gauge",
                "center": ["50%", "60%"],
                "radius": "85%",
                "startAngle": 180,
                "endAngle": 0,
                "min": -1,
                "max": 1,
                "splitNumber": 4,
                "itemStyle": {"color": color},
                "progress": {
                    "show": True,
                    "width": 20,
                    "roundCap": True,
                },
                "pointer": {
                    "show": True,
                    "length": "60%",
                    "width": 6,
                    "itemStyle": {"color": color},
                },
                "axisLine": {
                    "lineStyle": {
                        "width": 20,
                        "color": [
                            [0.3, "#ff4d4f"],   # SNS dominant
                            [0.5, "#faad14"],   # Balanced
                            [0.7, "#faad14"],   # Balanced
                            [1.0, "#52c41a"],   # PNS dominant
                        ],
                    },
                },
                "axisTick": {"show": True, "distance": -25, "length": 6},
                "splitLine": {"show": True, "distance": -30, "length": 12},
                "axisLabel": {
                    "show": True,
                    "distance": 35,
                    "fontSize": 10,
                    # JavaScript function as string for ECharts serialization
                    "formatter": "{value}",
                },
                "title": {
                    "show": True,
                    "offsetCenter": [0, "75%"],
                    "fontSize": 14,
                    "fontWeight": "bold",
                },
                "detail": {
                    "show": True,
                    "offsetCenter": [0, "40%"],
                    "fontSize": 24,
                    "fontWeight": "bold",
                    "color": color,
                    "formatter": f"{{value:.2f}}",
                },
                "data": [{"value": round(balance, 2), "name": "ANS Balance"}],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Export all available metrics with their thresholds
# ---------------------------------------------------------------------------


def get_available_gauge_metrics() -> list[str]:
    """Return list of all metrics that have gauge configurations."""
    return list(_GAUGE_THRESHOLDS.keys())


def get_gauge_thresholds(metric_name: str) -> GaugeThresholds | None:
    """Get thresholds for a specific metric."""
    return _GAUGE_THRESHOLDS.get(metric_name)

