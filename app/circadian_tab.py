"""
Circadian Physiology Tab for Mission Control - Flight Surgeon.

Provides interactive simulation and visualization of circadian rhythms using
mathematical models from the circadian research literature.

Models implemented:
- Forger99: Forger et al. (1999) - 3-state limit cycle pacemaker
- Jewett99: Kronauer et al. (1999) - Revised limit cycle oscillator
- Hannay19: Hannay et al. (2019) - Macroscopic amplitude-phase model
- Hannay19TP: Hannay et al. (2019) - Two-population variant

Original circadian package: Arcascope (Franco Tavella, Kevin Hannay, Olivia Walch)
UI integration: Dr. Diego L. Malpica, MD - Aerospace Medicine Specialist
"""

from __future__ import annotations

import json
import tempfile
import time as time_module
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Final, List, Optional, Tuple

import numpy as np
import streamlit as st
from numpy.typing import NDArray

# Try to import circadian module components - use multiple import strategies for portability
CIRCADIAN_AVAILABLE = False
_import_errors: List[str] = []

# Strategy 1: Try relative import (works when run as part of app package)
try:
    from .circadian.lights import LightSchedule
    from .circadian.models import Forger99, Hannay19, Hannay19TP, Jewett99
    from .circadian.metrics import esri
    CIRCADIAN_AVAILABLE = True
except Exception as _err1:
    _import_errors.append(f"Strategy 1 (relative): {type(_err1).__name__}: {_err1}")

# Strategy 2: Try absolute import (works when run from project root)
if not CIRCADIAN_AVAILABLE:
    try:
        from app.circadian.lights import LightSchedule
        from app.circadian.models import Forger99, Hannay19, Hannay19TP, Jewett99
        from app.circadian.metrics import esri
        CIRCADIAN_AVAILABLE = True
    except Exception as _err2:
        _import_errors.append(f"Strategy 2 (absolute): {type(_err2).__name__}: {_err2}")

# Strategy 3: Try direct import (works when circadian is in sys.path)
if not CIRCADIAN_AVAILABLE:
    try:
        from circadian.lights import LightSchedule
        from circadian.models import Forger99, Hannay19, Hannay19TP, Jewett99
        from circadian.metrics import esri
        CIRCADIAN_AVAILABLE = True
    except Exception as _err3:
        _import_errors.append(f"Strategy 3 (direct): {type(_err3).__name__}: {_err3}")

# Preserve all import errors for debugging
CIRCADIAN_IMPORT_ERROR: Optional[str] = "\n".join(_import_errors) if _import_errors and not CIRCADIAN_AVAILABLE else None

# Color scheme
PRIMARY_COLOR = "#667eea"
SECONDARY_COLOR = "#764ba2"
ACCENT_COLOR = "#20c997"
WARNING_COLOR = "#f093fb"

_MODEL_OPTIONS: Final[List[str]] = ["Forger99", "Jewett99", "Hannay19", "Hannay19TP"]
_SCHEDULE_OPTIONS: Final[List[str]] = [
    "Regular",
    "ShiftWork",
    "SlamShift",
    "SocialJetlag",
    "Custom Pulse",
]
_STATE_SETTINGS_KEY: Final[str] = "circadian_settings_state"
_STATE_PRESETS_KEY: Final[str] = "circadian_settings_presets"
_STATE_PRESET_ORDER_KEY: Final[str] = "circadian_preset_order"
_MAX_PRESETS: Final[int] = 5
_CONTEXT_USER_KEY: Final[str] = "circadian_context_user_id"


def _default_circadian_settings() -> Dict[str, Any]:
    """Return default circadian configuration."""
    return {
        "selected_models": ["Hannay19"],
        "schedule_type": "Regular",
        "lux": 500,
        "lights_on": 8,
        "lights_off": 22,
        "days_on": 3,
        "days_off": 2,
        "shift_hours": -6,
        "baseline_days": 7,
        "weekend_delay": 2.0,
        "pulse_start": 20,
        "pulse_duration": 2.0,
        "total_days": 30,
        "step_hours": 0.1,
        "equilibration_reps": 3,
        "show_dlmo": True,
        "show_cbt": False,
        "show_light_overlay": True,
    }


def _clone_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Create a shallow copy that preserves list fields."""
    clone = dict(settings)
    clone["selected_models"] = list(settings.get("selected_models", []))
    return clone


def _get_circadian_settings() -> Dict[str, Any]:
    """Load persisted circadian settings from session state."""
    stored = st.session_state.get(_STATE_SETTINGS_KEY)
    if stored is None:
        stored = _default_circadian_settings()
        st.session_state[_STATE_SETTINGS_KEY] = _clone_settings(stored)
    defaults = _default_circadian_settings()
    defaults.update(stored)
    models = [
        model for model in defaults.get("selected_models", []) if model in _MODEL_OPTIONS
    ]
    defaults["selected_models"] = models or _default_circadian_settings()[
        "selected_models"
    ]
    return _clone_settings(defaults)


def _update_circadian_settings(settings: Dict[str, Any]) -> None:
    """Persist circadian settings back to session state."""
    defaults = _default_circadian_settings()
    merged = {**defaults, **settings}
    merged["selected_models"] = [
        model for model in merged.get("selected_models", []) if model in _MODEL_OPTIONS
    ] or defaults["selected_models"]
    st.session_state[_STATE_SETTINGS_KEY] = _clone_settings(merged)


def _reset_circadian_settings() -> Dict[str, Any]:
    """Reset stored settings to defaults."""
    defaults = _default_circadian_settings()
    _update_circadian_settings(defaults)
    return defaults


def _ensure_preset_state() -> None:
    """Initialize preset storage in session state."""
    st.session_state.setdefault(_STATE_PRESETS_KEY, {})
    st.session_state.setdefault(_STATE_PRESET_ORDER_KEY, [])


def _get_circadian_presets() -> Dict[str, Dict[str, Any]]:
    """Return preset dictionary from session state."""
    _ensure_preset_state()
    return st.session_state[_STATE_PRESETS_KEY]


def _save_circadian_preset(name: str, settings: Dict[str, Any]) -> None:
    """Save (or overwrite) a preset and enforce the preset limit."""
    trimmed = name.strip()
    if not trimmed:
        return
    _ensure_preset_state()
    presets = st.session_state[_STATE_PRESETS_KEY]
    order: List[str] = st.session_state[_STATE_PRESET_ORDER_KEY]
    presets[trimmed] = _clone_settings(settings)
    if trimmed in order:
        order.remove(trimmed)
    order.insert(0, trimmed)
    while len(order) > _MAX_PRESETS:
        removed = order.pop()
        presets.pop(removed, None)


def _load_circadian_preset(name: str) -> Optional[Dict[str, Any]]:
    """Load a preset by name."""
    presets = _get_circadian_presets()
    preset = presets.get(name)
    if preset is None:
        return None
    return _clone_settings(preset)


def _render_preset_controls(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Render preset management controls and return possibly updated settings."""
    presets = _get_circadian_presets()
    preset_names = ["(none)"] + sorted(presets.keys())
    col_load, col_save, col_reset = st.columns([2, 2, 1])

    with col_load:
        selected = st.selectbox(
            "Saved scenarios",
            options=preset_names,
            index=0,
            key="circadian_preset_select",
            help="Load a previously saved configuration.",
        )
        load_clicked = st.button("Load preset", use_container_width=True)
    with col_save:
        preset_name = st.text_input(
            "Preset name",
            value="",
            key="circadian_preset_name",
            help="Save the current scenario for later reuse.",
        )
        save_clicked = st.button("Save preset", use_container_width=True)
    with col_reset:
        reset_clicked = st.button(
            "Reset defaults",
            use_container_width=True,
            help="Restore NASA default scenario parameters.",
        )

    updated_settings = settings
    if load_clicked and selected != "(none)":
        loaded = _load_circadian_preset(selected)
        if loaded:
            _update_circadian_settings(loaded)
            updated_settings = loaded
            st.success(f"Loaded circadian preset: {selected}")
        else:
            st.warning("Preset not found. It may have been removed.")

    if save_clicked:
        trimmed_name = preset_name.strip()
        if not trimmed_name:
            st.warning("Enter a preset name before saving.")
        else:
            _save_circadian_preset(trimmed_name, settings)
            st.success(f"Saved preset '{trimmed_name}'. Latest scenarios stay on top.")

    if reset_clicked:
        updated_settings = _reset_circadian_settings()
        st.info("Circadian settings reset to mission defaults.")

    return updated_settings


def _derive_contextual_settings(user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build circadian settings tailored to the active user context."""
    settings = _default_circadian_settings()
    if not user_context or not user_context.get("has_user"):
        return settings

    chronotype = float(user_context.get("chronotype_offset") or 0.0)
    if chronotype > 0.75:
        settings["schedule_type"] = "SocialJetlag"
        settings["weekend_delay"] = min(6.0, round(abs(chronotype) * 3.0, 1))
    elif chronotype < -0.75:
        settings["schedule_type"] = "Regular"
        settings["lights_on"] = 6
        settings["lights_off"] = 20
    else:
        settings["lights_on"] = 7
        settings["lights_off"] = 23

    medical_record = user_context.get("medical_record") or {}
    mission_profile = medical_record.get("mission_profile")
    if mission_profile in {"GATEWAY-30", "MARS-ANALOG-45", "CHAPEA-378"}:
        settings["schedule_type"] = "ShiftWork"
        settings["days_on"] = 4 if mission_profile != "CHAPEA-378" else 6
        settings["days_off"] = 2
        settings["lux"] = 750
    elif mission_profile == "LUNAR-22":
        settings["schedule_type"] = "SlamShift"
        settings["shift_hours"] = -6 if chronotype <= 0 else -3
        settings["baseline_days"] = 9

    sleep_hours = medical_record.get("sleep_hours")
    if isinstance(sleep_hours, (int, float)):
        lights_on = settings.get("lights_on", 8)
        settings["lights_off"] = int((lights_on + float(sleep_hours)) % 24)

    if medical_record.get("space_weather_alert") in {"Watch", "Warning"}:
        settings["pulse_start"] = 18
        settings["pulse_duration"] = 3.0

    crew_role = (medical_record.get("crew_role") or "").lower()
    if "commander" in crew_role or "pilot" in crew_role:
        settings["selected_models"] = ["Jewett99", "Hannay19"]
    elif "flight surgeon" in crew_role:
        settings["selected_models"] = ["Hannay19TP"]

    if mission_profile in {"MARS-ANALOG-45", "CHAPEA-378"}:
        settings["total_days"] = 45 if mission_profile == "MARS-ANALOG-45" else 60

    return settings


def _sync_settings_with_context(
    user_context: Optional[Dict[str, Any]], *, force: bool = False
) -> None:
    """Persist personalized circadian settings when the active user changes."""
    target_user = (
        user_context.get("user_id") if user_context and user_context.get("has_user") else None
    )
    stored_user = st.session_state.get(_CONTEXT_USER_KEY)
    if not force and stored_user == target_user:
        return

    if user_context and user_context.get("has_user"):
        personalized = _derive_contextual_settings(user_context)
        _update_circadian_settings(personalized)
        st.session_state[_CONTEXT_USER_KEY] = target_user
    elif force:
        defaults = _default_circadian_settings()
        _update_circadian_settings(defaults)
        st.session_state[_CONTEXT_USER_KEY] = None


def _render_schedule_section(schedule_type: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Render schedule-specific controls and return their values."""
    if schedule_type == "Regular":
        col_on, col_off = st.columns(2)
        return {
            "lights_on": col_on.slider(
                "Lights on (hour)",
                min_value=0,
                max_value=23,
                value=int(settings.get("lights_on", 8)),
            ),
            "lights_off": col_off.slider(
                "Lights off (hour)",
                min_value=0,
                max_value=23,
                value=int(settings.get("lights_off", 22)),
            ),
        }
    if schedule_type == "ShiftWork":
        col_days_on, col_days_off = st.columns(2)
        return {
            "days_on": col_days_on.slider(
                "Night shifts (days)",
                min_value=1,
                max_value=7,
                value=int(settings.get("days_on", 3)),
            ),
            "days_off": col_days_off.slider(
                "Days off",
                min_value=1,
                max_value=7,
                value=int(settings.get("days_off", 2)),
            ),
        }
    if schedule_type == "SlamShift":
        col_shift, col_baseline = st.columns(2)
        return {
            "shift_hours": col_shift.slider(
                "Phase shift (hours)",
                min_value=-12,
                max_value=12,
                value=int(settings.get("shift_hours", -6)),
            ),
            "baseline_days": col_baseline.slider(
                "Baseline days",
                min_value=3,
                max_value=14,
                value=int(settings.get("baseline_days", 7)),
            ),
        }
    if schedule_type == "SocialJetlag":
        return {
            "weekend_delay": st.slider(
                "Weekend delay (hours)",
                min_value=0.0,
                max_value=6.0,
                value=float(settings.get("weekend_delay", 2.0)),
                step=0.5,
            )
        }
    col_start, col_duration = st.columns(2)
    return {
        "pulse_start": col_start.slider(
            "Pulse start (hour)",
            min_value=0,
            max_value=23,
            value=int(settings.get("pulse_start", 20)),
        ),
        "pulse_duration": col_duration.slider(
            "Pulse duration (hours)",
            min_value=0.5,
            max_value=6.0,
            value=float(settings.get("pulse_duration", 2.0)),
            step=0.5,
        ),
    }


def _render_simulation_section(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Render simulation window controls."""
    st.markdown("#### ⏱️ Simulation window")
    total_days = st.slider(
        "Simulation days",
        min_value=7,
        max_value=90,
        value=int(settings.get("total_days", 30)),
    )
    step_hours = st.select_slider(
        "Time step (hours)",
        options=[0.05, 0.1, 0.25, 0.5],
        value=float(settings.get("step_hours", 0.1)),
    )
    equilibration_reps = st.slider(
        "Equilibration repetitions",
        min_value=0,
        max_value=10,
        value=int(settings.get("equilibration_reps", 3)),
    )
    return {
        "total_days": total_days,
        "step_hours": step_hours,
        "equilibration_reps": equilibration_reps,
    }


def _render_visualization_section(settings: Dict[str, Any]) -> Dict[str, bool]:
    """Render visualization flags and return their values."""
    st.markdown("#### 📊 Visualization options")
    col_dlmo, col_cbt, col_overlay = st.columns(3)
    return {
        "show_dlmo": col_dlmo.checkbox(
            "Show DLMO markers",
            value=bool(settings.get("show_dlmo", True)),
        ),
        "show_cbt": col_cbt.checkbox(
            "Show CBTmin markers",
            value=bool(settings.get("show_cbt", False)),
        ),
        "show_light_overlay": col_overlay.checkbox(
            "Overlay light on amplitude plot",
            value=bool(settings.get("show_light_overlay", True)),
        ),
    }


def _render_settings_form(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Render the scenario builder form and return updated settings."""
    with st.form("circadian_settings_form"):
        st.markdown("#### 🧪 Scenario Builder")
        st.caption("Adjust parameters, then click **Apply scenario** to refresh simulations.")

        selected_models = st.multiselect(
            "Select models",
            _MODEL_OPTIONS,
            default=settings.get("selected_models", ["Hannay19"]),
            help="Run multiple oscillators to compare predictions.",
        )

        schedule_type = st.selectbox(
            "Schedule type",
            _SCHEDULE_OPTIONS,
            index=_SCHEDULE_OPTIONS.index(settings.get("schedule_type", "Regular")),
            help="Defines the zeitgeber (light) pattern for the simulation.",
        )

        lux = st.slider(
            "Light intensity (lux)",
            min_value=50,
            max_value=1000,
            value=int(settings.get("lux", 500)),
            step=50,
        )

        schedule_values = _render_schedule_section(schedule_type, settings)
        simulation_values = _render_simulation_section(settings)
        visualization_flags = _render_visualization_section(settings)

        apply_clicked = st.form_submit_button(
            "Apply scenario",
            type="primary",
            use_container_width=True,
        )

    updated_settings = settings
    if apply_clicked:
        updated_settings = dict(settings)
        updated_settings.update(
            {
                "selected_models": selected_models or settings.get(
                    "selected_models", ["Hannay19"]
                ),
                "schedule_type": schedule_type,
                "lux": lux,
                **simulation_values,
                **visualization_flags,
            }
        )

        updated_settings.update(schedule_values)

        _update_circadian_settings(updated_settings)
        st.success("Circadian scenario updated. Visualizations refreshed below.")

    return updated_settings


def _get_echarts_config(
    title: str,
    series: List[Dict],
    x_axis_name: str = "Time (hours)",
    y_axis_name: str = "Value",
    height: int = 400,
    show_legend: bool = True,
    y_axis_config: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """Generate ECharts configuration for circadian visualizations."""
    config = {
        "title": {
            "text": title,
            "left": "center",
            "top": 10,
            "textStyle": {
                "color": "#e0e0e0",
                "fontSize": 16,
                "fontWeight": "bold",
            },
        },
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(30, 30, 50, 0.9)",
            "borderColor": PRIMARY_COLOR,
            "textStyle": {"color": "#e0e0e0"},
            "axisPointer": {"type": "cross"},
        },
        "legend": {
            "show": show_legend,
            "top": 40,
            "textStyle": {"color": "#a0a0a0"},
        },
        "grid": {
            "left": "8%",
            "right": "8%",
            "bottom": "15%",
            "top": 80 if show_legend else 60,
            "containLabel": True,
        },
        "xAxis": {
            "type": "value",
            "name": x_axis_name,
            "nameLocation": "center",
            "nameGap": 30,
            "nameTextStyle": {"color": "#888"},
            "axisLine": {"lineStyle": {"color": "#444"}},
            "axisLabel": {"color": "#888"},
            "splitLine": {"lineStyle": {"color": "#333", "type": "dashed"}},
        },
        "series": series,
    }
    
    if y_axis_config:
        config["yAxis"] = y_axis_config
    else:
        config["yAxis"] = {
            "type": "value",
            "name": y_axis_name,
            "nameLocation": "center",
            "nameGap": 45,
            "nameTextStyle": {"color": "#888"},
            "axisLine": {"lineStyle": {"color": "#444"}},
            "axisLabel": {"color": "#888"},
            "splitLine": {"lineStyle": {"color": "#333", "type": "dashed"}},
        }
    
    return config


def _render_echarts(option: Dict, height: int = 400, key: Optional[str] = None) -> None:
    """Render an ECharts chart with explanation panel."""
    container_id = f"echarts-circadian-{int(time_module.time() * 1000)}"
    if key:
        container_id = f"{container_id}-{key}"
    
    html_content = f"""
    <div id="{container_id}" style="width: 100%; height: {height}px; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 12px; border: 1px solid rgba(102, 126, 234, 0.2);"></div>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <script>
        (function() {{
            var chart = echarts.init(document.getElementById('{container_id}'), 'dark');
            var option = {json.dumps(option)};
            chart.setOption(option);
            window.addEventListener('resize', function() {{ chart.resize(); }});
        }})();
    </script>
    """
    st.components.v1.html(html_content, height=height + 20)


def _create_light_schedule_chart(time_arr: NDArray, light_arr: NDArray) -> Dict:
    """Create ECharts config for light schedule visualization."""
    # Downsample for performance
    step = max(1, len(time_arr) // 2000)
    time_plot = time_arr[::step]
    light_plot = light_arr[::step]
    
    data = [[float(t), float(l)] for t, l in zip(time_plot, light_plot)]
    
    return _get_echarts_config(
        title="💡 Light Schedule (Zeitgeber)",
        series=[{
            "name": "Light Intensity",
            "type": "line",
            "data": data,
            "smooth": True,
            "areaStyle": {
                "color": {
                    "type": "linear",
                    "x": 0, "y": 0, "x2": 0, "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": f"{PRIMARY_COLOR}80"},
                        {"offset": 1, "color": f"{PRIMARY_COLOR}10"},
                    ],
                },
            },
            "lineStyle": {"color": PRIMARY_COLOR, "width": 2},
            "itemStyle": {"color": PRIMARY_COLOR},
            "showSymbol": False,
        }],
        y_axis_name="Lux",
        height=300,
        show_legend=False,
    )


def _create_amplitude_phase_chart(
    time_arr: NDArray,
    trajectories: Dict[str, Tuple[NDArray, NDArray]],
    light_arr: Optional[NDArray] = None,
) -> Dict:
    """Create dual-axis chart for amplitude and phase over time."""
    series = []
    colors = [PRIMARY_COLOR, ACCENT_COLOR, WARNING_COLOR, "#4facfe"]
    
    step = max(1, len(time_arr) // 1500)
    time_plot = time_arr[::step]
    
    for idx, (model_name, (amplitude, phase)) in enumerate(trajectories.items()):
        color = colors[idx % len(colors)]
        amp_plot = amplitude[::step]
        phase_hours = (np.mod(phase, 2 * np.pi) * 12 / np.pi)[::step]
        
        # Amplitude series
        series.append({
            "name": f"{model_name} Amplitude",
            "type": "line",
            "yAxisIndex": 0,
            "data": [[float(t), float(a)] for t, a in zip(time_plot, amp_plot)],
            "smooth": True,
            "lineStyle": {"color": color, "width": 2},
            "itemStyle": {"color": color},
            "showSymbol": False,
        })
        
        # Phase series
        series.append({
            "name": f"{model_name} Phase",
            "type": "line",
            "yAxisIndex": 1,
            "data": [[float(t), float(p)] for t, p in zip(time_plot, phase_hours)],
            "smooth": True,
            "lineStyle": {"color": color, "width": 1, "type": "dashed"},
            "itemStyle": {"color": color},
            "showSymbol": False,
        })
    
    # Light overlay if provided
    if light_arr is not None:
        light_plot = light_arr[::step]
        log_light = np.log10(1 + light_plot)
        series.append({
            "name": "Light (log)",
            "type": "line",
            "yAxisIndex": 0,
            "data": [[float(t), float(l)] for t, l in zip(time_plot, log_light)],
            "smooth": True,
            "lineStyle": {"color": "#ffffff30", "width": 1},
            "areaStyle": {"color": "#ffffff10"},
            "showSymbol": False,
        })
    
    y_axis_config = [
        {
            "type": "value",
            "name": "Amplitude (R)",
            "position": "left",
            "nameTextStyle": {"color": "#888"},
            "axisLine": {"lineStyle": {"color": PRIMARY_COLOR}},
            "axisLabel": {"color": "#888"},
            "splitLine": {"lineStyle": {"color": "#333", "type": "dashed"}},
        },
        {
            "type": "value",
            "name": "Phase (hours)",
            "position": "right",
            "min": 0,
            "max": 24,
            "nameTextStyle": {"color": "#888"},
            "axisLine": {"lineStyle": {"color": ACCENT_COLOR}},
            "axisLabel": {"color": "#888"},
            "splitLine": {"show": False},
        },
    ]
    
    return _get_echarts_config(
        title="🧠 Circadian Amplitude & Phase",
        series=series,
        y_axis_config=y_axis_config,
        height=450,
    )


def _create_actogram_heatmap(
    time_arr: NDArray,
    light_arr: NDArray,
    dlmo_times: Optional[NDArray] = None,
    cbt_times: Optional[NDArray] = None,
    bin_hours: float = 0.5,
) -> Dict:
    """Create actogram heatmap visualization."""
    # Calculate number of days
    total_hours = time_arr[-1] - time_arr[0]
    num_days = int(np.ceil(total_hours / 24))
    
    # Create heatmap data
    bins_per_day = int(48 / bin_hours)  # Double-plotted
    heatmap_data = []
    
    for day in range(num_days):
        day_start = time_arr[0] + day * 24
        for bin_idx in range(bins_per_day):
            hour = (bin_idx * bin_hours) % 48
            bin_start = day_start + (bin_idx * bin_hours) % 24
            bin_end = bin_start + bin_hours
            
            # Get light values in this bin
            mask = (time_arr >= bin_start) & (time_arr < bin_end)
            if np.any(mask):
                value = float(np.log10(1 + np.mean(light_arr[mask])))
            else:
                value = 0
            
            heatmap_data.append([hour, day, round(value, 2)])
    
    # Add phase markers
    mark_points = []
    if dlmo_times is not None:
        for dlmo in dlmo_times:
            day = int((dlmo - time_arr[0]) / 24)
            hour = float(dlmo % 24)
            if 0 <= day < num_days:
                mark_points.append({
                    "coord": [hour, day],
                    "symbol": "circle",
                    "symbolSize": 8,
                    "itemStyle": {"color": PRIMARY_COLOR},
                })
                # Double plot
                mark_points.append({
                    "coord": [hour + 24, day],
                    "symbol": "circle",
                    "symbolSize": 8,
                    "itemStyle": {"color": PRIMARY_COLOR},
                })
    
    if cbt_times is not None:
        for cbt in cbt_times:
            day = int((cbt - time_arr[0]) / 24)
            hour = float(cbt % 24)
            if 0 <= day < num_days:
                mark_points.append({
                    "coord": [hour, day],
                    "symbol": "triangle",
                    "symbolSize": 8,
                    "itemStyle": {"color": ACCENT_COLOR},
                })
                mark_points.append({
                    "coord": [hour + 24, day],
                    "symbol": "triangle",
                    "symbolSize": 8,
                    "itemStyle": {"color": ACCENT_COLOR},
                })
    
    config = {
        "title": {
            "text": "📊 Actogram Heatmap",
            "left": "center",
            "textStyle": {"color": "#e0e0e0", "fontSize": 16},
        },
        "tooltip": {
            "position": "top",
            "formatter": "Day {c[1]}, Hour {c[0]}: {c[2]}",
        },
        "grid": {
            "left": "10%",
            "right": "10%",
            "bottom": "15%",
            "top": 60,
        },
        "xAxis": {
            "type": "category",
            "data": [f"{h:.1f}" for h in np.arange(0, 48, bin_hours)],
            "name": "Hour (Double-plotted)",
            "nameLocation": "center",
            "nameGap": 30,
            "nameTextStyle": {"color": "#888"},
            "axisLine": {"lineStyle": {"color": "#444"}},
            "axisLabel": {"color": "#888", "interval": int(4 / bin_hours)},
            "splitArea": {"show": True, "areaStyle": {"color": ["#00000010", "#00000020"]}},
        },
        "yAxis": {
            "type": "category",
            "data": [str(d) for d in range(num_days)],
            "name": "Day",
            "nameTextStyle": {"color": "#888"},
            "axisLine": {"lineStyle": {"color": "#444"}},
            "axisLabel": {"color": "#888"},
            "inverse": True,
        },
        "visualMap": {
            "min": 0,
            "max": 3,
            "calculable": True,
            "orient": "horizontal",
            "left": "center",
            "bottom": 0,
            "inRange": {
                "color": ["#1a1a2e", "#16213e", "#667eea", "#f093fb"],
            },
            "textStyle": {"color": "#888"},
        },
        "series": [{
            "name": "Light",
            "type": "heatmap",
            "data": heatmap_data,
            "label": {"show": False},
            "emphasis": {
                "itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0, 0, 0, 0.5)"},
            },
            "markPoint": {"data": mark_points} if mark_points else None,
        }],
    }
    
    return config


def _create_esri_chart(esri_time: NDArray, esri_values: NDArray) -> Dict:
    """Create ESRI metric visualization."""
    # Remove NaN values for plotting
    valid_mask = ~np.isnan(esri_values)
    time_plot = esri_time[valid_mask]
    values_plot = esri_values[valid_mask]
    
    data = [[float(t), float(v)] for t, v in zip(time_plot, values_plot)]
    
    return _get_echarts_config(
        title="📈 Entrainment Signal Regularity Index (ESRI)",
        series=[{
            "name": "ESRI",
            "type": "line",
            "data": data,
            "smooth": True,
            "areaStyle": {
                "color": {
                    "type": "linear",
                    "x": 0, "y": 0, "x2": 0, "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": f"{ACCENT_COLOR}60"},
                        {"offset": 1, "color": f"{ACCENT_COLOR}10"},
                    ],
                },
            },
            "lineStyle": {"color": ACCENT_COLOR, "width": 2},
            "itemStyle": {"color": ACCENT_COLOR},
            "showSymbol": False,
        }],
        y_axis_name="ESRI Score",
        height=350,
        show_legend=False,
    )


def render_circadian_tab(
    user_profile: Optional[Dict[str, Any]] = None,
    user_context: Optional[Dict[str, Any]] = None,
) -> None:
    """Render the complete Circadian Physiology tab."""
    
    if not CIRCADIAN_AVAILABLE:
        st.error("⚠️ **Circadian Module Not Available**")
        st.warning(
            "The circadian simulation module could not be loaded. "
            "Please ensure the `app/circadian/` package is properly installed."
        )
        if CIRCADIAN_IMPORT_ERROR:
            st.code(CIRCADIAN_IMPORT_ERROR, language="text")
        return
    
    # Header
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(102, 126, 234, 0.2);
    ">
        <h2 style="margin: 0 0 0.5rem 0; color: #667eea;">🌙 Circadian Physiology Simulation</h2>
        <p style="margin: 0; color: #a0a0a0; font-size: 0.95rem;">
            Simulate and visualize circadian rhythm dynamics using validated mathematical models.
            Explore phase response curves, light schedule effects, and entrainment patterns.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    _sync_settings_with_context(user_context)
    settings = _get_circadian_settings()
    st.markdown("### ⚙️ Scenario Configuration")
    if user_context and user_context.get("has_user"):
        if st.button(
            "Align with active profile",
            key="circadian_sync_profile",
            help="Pull sleep/wake cues from the active user and re-run simulations.",
        ):
            _sync_settings_with_context(user_context, force=True)
            settings = _get_circadian_settings()
            st.success(
                f"Scenario synced with {user_context.get('full_name') or user_context.get('username') or 'active user'}."
            )
    settings = _render_preset_controls(settings)
    settings = _render_settings_form(settings)
    
    st.markdown("---")
    st.caption(
        f"Active scenario • Models: {', '.join(settings['selected_models'])} | "
        f"Schedule: {settings['schedule_type']} @ {int(settings['lux'])} lux | "
        f"Duration: {int(settings['total_days'])} days"
    )
    
    # Create time array and light schedule from persisted settings
    total_days = int(settings["total_days"])
    step_hours = float(settings["step_hours"])
    schedule_type = settings["schedule_type"]
    lux = int(settings["lux"])
    time_arr = np.arange(0, 24 * total_days, step_hours)
    
    if schedule_type == "Regular":
        light_schedule = LightSchedule.Regular(
            lux=lux,
            lights_on=int(settings["lights_on"]),
            lights_off=int(settings["lights_off"]),
        )
    elif schedule_type == "ShiftWork":
        light_schedule = LightSchedule.ShiftWork(
            lux=lux,
            days_on=int(settings["days_on"]),
            days_off=int(settings["days_off"]),
        )
    elif schedule_type == "SlamShift":
        light_schedule = LightSchedule.SlamShift(
            lux=lux,
            shift_hours=int(settings["shift_hours"]),
            baseline_days=int(settings["baseline_days"]),
        )
    elif schedule_type == "SocialJetlag":
        light_schedule = LightSchedule.SocialJetlag(
            lux=lux,
            weekend_delay=float(settings["weekend_delay"]),
        )
    else:
        light_schedule = LightSchedule.from_pulse(
            pulse_lux=lux,
            pulse_start=int(settings["pulse_start"]),
            pulse_duration=float(settings["pulse_duration"]),
        )
    
    light_arr = light_schedule(time_arr)
    selected_models = settings["selected_models"]
    equilibration_reps = int(settings["equilibration_reps"])
    show_dlmo = bool(settings["show_dlmo"])
    show_cbt = bool(settings["show_cbt"])
    show_light_overlay = bool(settings["show_light_overlay"])
    
    dlmo_all: List[float] = []
    cbt_all: List[float] = []
    
    # Tabs for different views
    sim_tab, actogram_tab, esri_tab, info_tab = st.tabs([
        "📈 Amplitude & Phase",
        "📊 Actogram",
        "📉 ESRI Metric",
        "ℹ️ Model Info",
    ])
    
    with sim_tab:
        # Light schedule visualization
        st.markdown("### 💡 Light Schedule")
        light_config = _create_light_schedule_chart(time_arr, light_arr)
        _render_echarts(light_config, height=300, key="light_schedule")
        
        st.markdown("""
        <div style="background: rgba(102, 126, 234, 0.1); border-radius: 8px; padding: 1rem; margin: 1rem 0;">
            <strong>💡 Interpretation:</strong> The light schedule (zeitgeber) drives circadian entrainment. 
            Higher lux during wake hours strengthens the entrainment signal. The models convert photopic 
            lux to retinal drive via a saturating nonlinearity simulating ipRGC phototransduction.
        </div>
        """, unsafe_allow_html=True)
        
        # Run simulations
        if selected_models:
            st.markdown("### 🧠 Model Trajectories")
            
            trajectories = {}
            
            model_classes = {
                "Forger99": Forger99,
                "Jewett99": Jewett99,
                "Hannay19": Hannay19,
                "Hannay19TP": Hannay19TP,
            }
            
            with st.spinner("Running circadian simulations..."):
                for model_name in selected_models:
                    if model_name in model_classes:
                        model = model_classes[model_name]()
                        
                        # Equilibrate
                        x0 = model.equilibrate(time_arr, light_arr, equilibration_reps)
                        
                        # Integrate
                        traj = model(time_arr, x0, light_arr)
                        
                        # Extract amplitude and phase
                        amplitude = model.amplitude(traj)
                        phase = model.phase(traj)
                        trajectories[model_name] = (amplitude, phase)
                        
                        # Get phase markers
                        if show_dlmo:
                            dlmo_all.extend(model.dlmos(traj))
                        if show_cbt:
                            cbt_all.extend(model.cbt(traj))
            
            # Amplitude & Phase chart
            amp_phase_config = _create_amplitude_phase_chart(
                time_arr, trajectories, light_arr if show_light_overlay else None
            )
            _render_echarts(amp_phase_config, height=450, key="amp_phase")
            
            st.markdown("""
            <div style="background: rgba(32, 201, 151, 0.1); border-radius: 8px; padding: 1rem; margin: 1rem 0;">
                <strong>🧠 Interpretation:</strong>
                <ul style="margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
                    <li><strong>Amplitude (R):</strong> Order parameter reflecting SCN synchrony. Higher = stronger circadian signal.</li>
                    <li><strong>Phase (hours):</strong> Current position in the 24h cycle. Phase shifts indicate entrainment dynamics.</li>
                    <li><strong>Solid lines:</strong> Amplitude; <strong>Dashed lines:</strong> Phase</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("👆 Select at least one model in the scenario panel to run simulations.")
    
    with actogram_tab:
        st.markdown("### 📊 Double-Plotted Actogram")
        
        dlmo_arr = np.array(dlmo_all) if dlmo_all else None
        cbt_arr = np.array(cbt_all) if cbt_all else None
        
        bin_hours = st.select_slider(
            "Bin Size (hours)", 
            options=[0.25, 0.5, 1.0, 2.0], 
            value=0.5,
            help="Time resolution for heatmap bins",
        )
        
        actogram_config = _create_actogram_heatmap(
            time_arr, light_arr, dlmo_arr, cbt_arr, bin_hours
        )
        _render_echarts(actogram_config, height=500, key="actogram")
        
        st.markdown("""
        <div style="background: rgba(240, 147, 251, 0.1); border-radius: 8px; padding: 1rem; margin: 1rem 0;">
            <strong>📊 Interpretation:</strong> The actogram shows light exposure patterns double-plotted 
            across consecutive days. This format reveals:
            <ul style="margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
                <li>Phase drifts (diagonal patterns indicate non-24h periods)</li>
                <li>Entrainment stability (vertical alignment = stable entrainment)</li>
                <li>Phase markers: <span style="color: #667eea;">●</span> DLMO, <span style="color: #20c997;">▲</span> CBTmin</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with esri_tab:
        st.markdown("### 📉 Entrainment Signal Regularity Index")
        
        col1, col2 = st.columns(2)
        with col1:
            analysis_days = st.slider("Analysis Window (days)", 2, 7, 4)
        with col2:
            esri_dt = st.slider("ESRI Resolution (hours)", 0.5, 4.0, 1.0, 0.5)
        
        try:
            with st.spinner("Computing ESRI..."):
                esri_time, esri_values = esri(
                    time_arr, light_arr, 
                    analysis_days=analysis_days, 
                    esri_dt=esri_dt
                )
            
            esri_config = _create_esri_chart(esri_time, esri_values)
            _render_echarts(esri_config, height=350, key="esri")
            
            # Statistics
            valid_esri = esri_values[~np.isnan(esri_values)]
            if len(valid_esri) > 0:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Mean ESRI", f"{np.mean(valid_esri):.3f}")
                with col2:
                    st.metric("Min ESRI", f"{np.min(valid_esri):.3f}")
                with col3:
                    st.metric("Max ESRI", f"{np.max(valid_esri):.3f}")
            
            st.markdown("""
            <div style="background: rgba(79, 172, 254, 0.1); border-radius: 8px; padding: 1rem; margin: 1rem 0;">
                <strong>📉 Interpretation:</strong> ESRI quantifies how well a light schedule promotes 
                stable circadian entrainment:
                <ul style="margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
                    <li><strong>Higher ESRI:</strong> More regular, entrainment-promoting schedule</li>
                    <li><strong>Lower ESRI:</strong> Irregular schedule that may disrupt circadian timing</li>
                    <li>Reference: Constant darkness yields baseline ESRI (~0.1)</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"ESRI calculation failed: {e}")
    
    with info_tab:
        st.markdown("### ℹ️ Model Documentation")
        
        st.markdown("""
        <div style="background: rgba(0,0,0,0.2); border-radius: 12px; padding: 1.5rem; margin: 1rem 0;">
            <h4 style="color: #667eea; margin-top: 0;">Mathematical Models</h4>
            
            <div style="margin-bottom: 1rem;">
                <strong>Forger99 / Jewett99</strong> (3-state limit cycle)
                <p style="color: #888; font-size: 0.9rem; margin: 0.25rem 0;">
                    State variables: (x, x<sub>c</sub>, n) where n is phototransduction adaptation.<br>
                    Phase: φ = arg(x, -x<sub>c</sub>); Amplitude: R = √(x² + x<sub>c</sub>²)
                </p>
            </div>
            
            <div style="margin-bottom: 1rem;">
                <strong>Hannay19</strong> (Amplitude-Phase)
                <p style="color: #888; font-size: 0.9rem; margin: 0.25rem 0;">
                    State variables: (R, Ψ, n) - macroscopic order parameter model.<br>
                    Direct amplitude (R) and phase (Ψ) representation.
                </p>
            </div>
            
            <div>
                <strong>Hannay19TP</strong> (Two-Population)
                <p style="color: #888; font-size: 0.9rem; margin: 0.25rem 0;">
                    State variables: (R<sub>v</sub>, R<sub>d</sub>, Ψ<sub>v</sub>, Ψ<sub>d</sub>, n)<br>
                    Models ventral/dorsal SCN coupling dynamics.
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        #### 📚 References
        
        1. **Forger et al. (1999)** - "Simpler model of the human circadian pacemaker"  
           *J Biol Rhythms* 14(6):532-537. [DOI: 10.1177/074873099129000867](https://doi.org/10.1177/074873099129000867)
        
        2. **Kronauer et al. (1999)** - "Quantifying human circadian pacemaker response to light"  
           *J Biol Rhythms* 14(6):500-515. [DOI: 10.1177/074873049901400608](https://doi.org/10.1177/074873049901400608)
        
        3. **Hannay et al. (2019)** - "Macroscopic models for human circadian rhythms"  
           *J Biol Rhythms* 34(6):658-671. [DOI: 10.1177/0748730419878298](https://doi.org/10.1177/0748730419878298)
        
        4. **Moreno et al. (2023)** - "Validation of the ESRI and associations with children's BMI"
        
        #### 🏷️ Citation
        
        ```bibtex
        @software{circadian_arcascope,
          author = {Franco Tavella and Kevin Hannay and Olivia Walch},
          title = {Arcascope/circadian},
          year = 2023,
          publisher = {Zenodo},
          doi = {10.5281/zenodo.8206871}
        }
        ```
        """)


if __name__ == "__main__":
    st.set_page_config(page_title="Circadian Physiology", layout="wide")
    render_circadian_tab()

