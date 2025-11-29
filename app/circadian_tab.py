"""
Circadian Physiology Tab for HRV Analysis Suite.

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
from typing import Any, Dict, List, Optional, Tuple

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


def render_circadian_tab(user_profile: Optional[Dict] = None) -> None:
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
    
    # Sidebar configuration
    with st.sidebar:
        st.markdown("### 🌙 Circadian Settings")
        
        # Model selection
        model_options = ["Forger99", "Jewett99", "Hannay19", "Hannay19TP"]
        selected_models = st.multiselect(
            "Select Models",
            model_options,
            default=["Hannay19"],
            help="Choose circadian oscillator models to simulate",
        )
        
        # Light schedule
        st.markdown("#### 💡 Light Schedule")
        schedule_type = st.selectbox(
            "Schedule Type",
            ["Regular", "ShiftWork", "SlamShift", "SocialJetlag", "Custom Pulse"],
            help="Select a predefined light schedule pattern",
        )
        
        # Schedule parameters
        lux = st.slider("Light Intensity (lux)", 50, 1000, 500, 50)
        
        if schedule_type == "Regular":
            lights_on = st.slider("Lights On (hour)", 0, 23, 8)
            lights_off = st.slider("Lights Off (hour)", 0, 23, 22)
        elif schedule_type == "ShiftWork":
            days_on = st.slider("Night Shifts (days)", 1, 7, 3)
            days_off = st.slider("Days Off", 1, 7, 2)
        elif schedule_type == "SlamShift":
            shift_hours = st.slider("Phase Shift (hours)", -12, 12, -6)
            baseline_days = st.slider("Baseline Days", 3, 14, 7)
        elif schedule_type == "SocialJetlag":
            weekend_delay = st.slider("Weekend Delay (hours)", 0.0, 6.0, 2.0, 0.5)
        else:  # Custom Pulse
            pulse_start = st.slider("Pulse Start (hour)", 0, 23, 20)
            pulse_duration = st.slider("Pulse Duration (hours)", 0.5, 6.0, 2.0, 0.5)
        
        # Simulation parameters
        st.markdown("#### ⚙️ Simulation")
        total_days = st.slider("Simulation Days", 7, 90, 30)
        step_hours = st.select_slider("Time Step (hours)", [0.05, 0.1, 0.25, 0.5], 0.1)
        equilibration_reps = st.slider("Equilibration Reps", 0, 10, 3)
        
        # Visualization options
        st.markdown("#### 📊 Visualization")
        show_dlmo = st.checkbox("Show DLMO Markers", True)
        show_cbt = st.checkbox("Show CBTmin Markers", False)
        show_light_overlay = st.checkbox("Light Overlay", True)
    
    # Create time array
    time_arr = np.arange(0, 24 * total_days, step_hours)
    
    # Create light schedule
    if schedule_type == "Regular":
        light_schedule = LightSchedule.Regular(lux=lux, lights_on=lights_on, lights_off=lights_off)
    elif schedule_type == "ShiftWork":
        light_schedule = LightSchedule.ShiftWork(lux=lux, days_on=days_on, days_off=days_off)
    elif schedule_type == "SlamShift":
        light_schedule = LightSchedule.SlamShift(lux=lux, shift_hours=shift_hours, baseline_days=baseline_days)
    elif schedule_type == "SocialJetlag":
        light_schedule = LightSchedule.SocialJetlag(lux=lux, weekend_delay=weekend_delay)
    else:  # Custom Pulse
        light_schedule = LightSchedule.from_pulse(
            pulse_lux=lux, pulse_start=pulse_start, pulse_duration=pulse_duration
        )
    
    light_arr = light_schedule(time_arr)
    
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
            dlmo_all = []
            cbt_all = []
            
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
            st.info("👆 Select at least one model from the sidebar to run simulations.")
    
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

