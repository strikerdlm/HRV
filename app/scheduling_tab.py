"""
Crew Scheduling and Human Performance Management - Streamlit UI Tab.

This module implements the Streamlit UI for crew scheduling with:
- Live Status Grid: 6-crew status cards with color-coded IHPI
- Timeline View: 24-hour Gantt chart with activity assignments
- Risk Heatmap: Real-time risk levels per crew member
- Scheduling Controls: Activity assignment and optimization

Publication-Quality Charts:
- All visualizations use Apache ECharts following Nature Research guidelines
- Dynamic axis scaling with _auto_axis_bounds()
- Evidence-based color semantics (green=good, red=poor)

Author: Dr. Diego Leonel Malpica Hincapié, MD
Version: 1.0.0
"""

from __future__ import annotations

import json
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

try:
    from echarts_component import render_echarts
except ImportError:
    render_echarts = None  # type: ignore[assignment]

try:
    from scheduling_core import (
        ActivityCategory,
        ActivityDefinition,
        ALL_ACTIVITIES,
        FIXED_ACTIVITIES,
        VARIABLE_ACTIVITIES,
        CrewMember,
        CrewPhysiologicalStatus,
        RiskLevel,
        GONOGOStatus,
        compute_ihpi,
        IHPISubscores,
        DEFAULT_IHPI_WEIGHTS,
        SAFTE_LOW_RISK_MIN,
        SAFTE_CAUTION_MIN,
        SAFTE_HIGH_RISK_MIN,
        NASA_EVA_VO2MAX_MIN_ML_KG_MIN,
        # Advanced features
        simulate_safte_24h,
        PerformanceForecast,
        WhatIfScenario,
        analyze_what_if,
        compute_workload_balance,
        WorkloadMetrics,
    )
    from scheduling_engine import (
        SchedulingEngine,
        ScheduledActivity,
        DailySchedule,
        create_sample_crew,
        MAX_CREW_SIZE,
    )
    SCHEDULING_AVAILABLE = True
    ADVANCED_FEATURES_AVAILABLE = True
except ImportError:
    SCHEDULING_AVAILABLE = False
    ADVANCED_FEATURES_AVAILABLE = False

try:
    from logging_config import get_logger
except ImportError:
    import logging
    get_logger = logging.getLogger

_LOGGER = get_logger(__name__)


# ---------------------------------------------------------------------------
# Color Constants (Scientific Standards)
# ---------------------------------------------------------------------------

COLORS = {
    "good": "#27ae60",      # Green - Low risk
    "normal": "#3498db",    # Blue - Normal
    "caution": "#f39c12",   # Yellow/Orange - Caution
    "poor": "#e74c3c",      # Red - High risk
    "trend": "#2c3e50",     # Dark gray - Trend lines
    "background": "#1a1a2e", # Dark background
    "text": "#e0e0e0",      # Light text
    "grid": "#3a3a5c",      # Grid lines
}

RISK_COLORS = {
    RiskLevel.LOW: "#27ae60",
    RiskLevel.MODERATE: "#f39c12",
    RiskLevel.HIGH: "#e67e22",
    RiskLevel.VERY_HIGH: "#e74c3c",
}

GONOGO_COLORS = {
    GONOGOStatus.GO: "#27ae60",
    GONOGOStatus.GO_WITH_MITIGATION: "#f39c12",
    GONOGOStatus.HOLD: "#e67e22",
    GONOGOStatus.NOGO: "#e74c3c",
}


# ---------------------------------------------------------------------------
# Session State Management
# ---------------------------------------------------------------------------

def _init_scheduling_session_state() -> None:
    """Initialize scheduling-related session state."""
    if "scheduling_engine" not in st.session_state:
        crew = create_sample_crew()
        engine = SchedulingEngine(crew_members=crew)
        st.session_state["scheduling_engine"] = engine
    
    if "selected_schedule_date" not in st.session_state:
        st.session_state["selected_schedule_date"] = date.today()
    
    if "selected_crew_id" not in st.session_state:
        st.session_state["selected_crew_id"] = None


def _get_engine() -> SchedulingEngine:
    """Get the scheduling engine from session state."""
    _init_scheduling_session_state()
    return st.session_state["scheduling_engine"]


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def _auto_axis_bounds(
    *values: float,
    padding_pct: float = 0.15,
    min_floor: float = 0.0,
    max_ceil: Optional[float] = None,
) -> Tuple[float, float]:
    """
    Calculate dynamic axis bounds to ensure all data points are visible.
    
    CRITICAL: Never use hardcoded axis limits that might clip data!
    
    Args:
        *values: Data values to bound
        padding_pct: Padding as fraction of range
        min_floor: Minimum allowed lower bound
        max_ceil: Maximum allowed upper bound
        
    Returns:
        Tuple of (min_bound, max_bound)
    """
    valid_values = [v for v in values if v is not None and np.isfinite(v)]
    if not valid_values:
        return (min_floor, max_ceil or 100.0)
    
    v_min = min(valid_values)
    v_max = max(valid_values)
    v_range = max(v_max - v_min, 1.0)
    padding = v_range * padding_pct
    
    lower = max(min_floor, v_min - padding)
    upper = v_max + padding
    if max_ceil is not None:
        upper = min(max_ceil, upper)
    
    return (lower, upper)


def _format_duration(minutes: int) -> str:
    """Format minutes as HH:MM or human-readable string."""
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
    return f"{mins}m"


# ---------------------------------------------------------------------------
# Crew Status Cards
# ---------------------------------------------------------------------------

def _render_crew_status_card(
    crew: CrewMember,
    col: Any,
) -> None:
    """Render a single crew member status card."""
    with col:
        ihpi = crew.get_ihpi()
        risk = crew.get_risk_level()
        color = RISK_COLORS.get(risk, COLORS["normal"])
        
        # Status indicator
        status_emoji = {
            RiskLevel.LOW: "🟢",
            RiskLevel.MODERATE: "🟡",
            RiskLevel.HIGH: "🟠",
            RiskLevel.VERY_HIGH: "🔴",
        }.get(risk, "⚪")
        
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, {color}22, {color}11);
                border: 2px solid {color};
                border-radius: 12px;
                padding: 16px;
                margin: 4px 0;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 1.1em; font-weight: 600;">{crew.name}</span>
                    <span style="font-size: 1.5em;">{status_emoji}</span>
                </div>
                <div style="color: #888; font-size: 0.85em; margin: 4px 0;">{crew.role}</div>
                <div style="margin-top: 12px;">
                    <span style="font-size: 2em; font-weight: 700; color: {color};">{ihpi:.0f}</span>
                    <span style="color: #888; font-size: 0.9em;"> IHPI</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        # Detailed metrics expander
        if crew.status:
            with st.expander("📊 Details", expanded=False):
                st.markdown(f"**SAFTE:** {crew.status.safte_effectiveness:.1f}%")
                st.markdown(f"**Hours Awake:** {crew.status.hours_awake:.1f}h")
                st.markdown(f"**KSS:** {crew.status.kss_score:.0f}/9")
                st.markdown(f"**lnRMSSD z:** {crew.status.lnrmssd_zscore:+.2f}")
                st.markdown(f"**EA:** {crew.status.energy_availability:.1f} kcal/kg FFM")
                
                # EVA status if eligible
                if crew.vo2max_ml_kg_min >= NASA_EVA_VO2MAX_MIN_ML_KG_MIN:
                    eva_result = crew.status.eva_go_nogo()
                    eva_color = GONOGO_COLORS.get(eva_result.status, "#888")
                    st.markdown(
                        f"**EVA Status:** <span style='color: {eva_color}; font-weight: bold;'>"
                        f"{eva_result.status.value.upper()}</span>",
                        unsafe_allow_html=True,
                    )


def _render_crew_status_grid(engine: SchedulingEngine) -> None:
    """Render the 6-crew status grid."""
    st.markdown("### 👥 Crew Status Overview")
    
    crew_list = list(engine.crew_members.values())
    
    # Create 3x2 grid for 6 crew members
    cols = st.columns(3)
    for idx, crew in enumerate(crew_list[:6]):
        _render_crew_status_card(crew, cols[idx % 3])


# ---------------------------------------------------------------------------
# Timeline Visualization (Gantt Chart)
# ---------------------------------------------------------------------------

def _render_timeline_chart(
    engine: SchedulingEngine,
    schedule_date: date,
) -> None:
    """Render a 24-hour Gantt chart timeline using ECharts."""
    st.markdown("### 📅 Daily Timeline")
    
    if render_echarts is None:
        st.warning("ECharts component not available. Install with `pip install streamlit-echarts`")
        return
    
    daily = engine.get_or_create_daily_schedule(schedule_date)
    
    # Prepare data for Gantt chart
    crew_names = [c.name for c in engine.crew_members.values()]
    categories = [{"name": name} for name in crew_names]
    
    # Convert activities to series data
    data = []
    for activity in daily.activities:
        crew = engine.crew_members.get(activity.crew_id)
        if not crew:
            continue
        
        crew_idx = crew_names.index(crew.name) if crew.name in crew_names else 0
        
        # Convert to hour-based values for the chart
        start_hour = activity.start_time.hour + activity.start_time.minute / 60
        end_hour = activity.end_time.hour + activity.end_time.minute / 60
        if end_hour < start_hour:  # Crosses midnight
            end_hour += 24
        
        # Color based on activity type
        activity_colors = {
            "briefing": "#3498db",
            "breakfast": "#f1c40f",
            "lunch": "#f39c12",
            "dinner": "#e67e22",
            "exercise": "#27ae60",
            "recreation": "#9b59b6",
            "hygiene": "#1abc9c",
            "sleep": "#2c3e50",
            "lab_work": "#2980b9",
            "eva": "#c0392b",
        }
        color = activity_colors.get(activity.activity_id, "#7f8c8d")
        
        data.append({
            "name": activity.activity_name,
            "value": [crew_idx, start_hour, end_hour, activity.duration_minutes],
            "itemStyle": {"normal": {"color": color}},
        })
    
    # ECharts option
    option = {
        "backgroundColor": "transparent",
        "tooltip": {
            "formatter": """function(params) {
                var start = Math.floor(params.value[1]) + ':' + String(Math.round((params.value[1] % 1) * 60)).padStart(2, '0');
                var end = Math.floor(params.value[2] % 24) + ':' + String(Math.round((params.value[2] % 1) * 60)).padStart(2, '0');
                return params.name + '<br/>Time: ' + start + ' - ' + end + '<br/>Duration: ' + params.value[3] + ' min';
            }""",
        },
        "grid": {
            "left": "15%",
            "right": "5%",
            "top": "10%",
            "bottom": "15%",
        },
        "xAxis": {
            "type": "value",
            "min": 0,
            "max": 24,
            "interval": 2,
            "axisLabel": {
                "formatter": "{value}:00",
                "color": "#888",
            },
            "axisLine": {"lineStyle": {"color": "#444"}},
            "splitLine": {"lineStyle": {"color": "#333", "type": "dashed"}},
        },
        "yAxis": {
            "type": "category",
            "data": crew_names,
            "axisLabel": {"color": "#ddd"},
            "axisLine": {"lineStyle": {"color": "#444"}},
        },
        "series": [
            {
                "type": "custom",
                "renderItem": """function(params, api) {
                    var categoryIndex = api.value(0);
                    var start = api.coord([api.value(1), categoryIndex]);
                    var end = api.coord([api.value(2), categoryIndex]);
                    var height = api.size([0, 1])[1] * 0.6;
                    
                    var rectShape = echarts.graphic.clipRectByRect({
                        x: start[0],
                        y: start[1] - height / 2,
                        width: end[0] - start[0],
                        height: height
                    }, {
                        x: params.coordSys.x,
                        y: params.coordSys.y,
                        width: params.coordSys.width,
                        height: params.coordSys.height
                    });
                    
                    return rectShape && {
                        type: 'rect',
                        shape: rectShape,
                        style: api.style()
                    };
                }""",
                "encode": {
                    "x": [1, 2],
                    "y": 0,
                },
                "data": data,
            }
        ],
    }
    
    render_echarts(option, height_px=380)
    
    # Activity legend
    st.markdown(
        """
        <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-top: 10px; font-size: 0.85em;">
            <span>🔵 Briefing</span>
            <span>🟡 Meals</span>
            <span>🟢 Exercise</span>
            <span>🟣 Recreation</span>
            <span>🔷 Hygiene</span>
            <span>⬛ Sleep</span>
            <span>🔵 Lab Work</span>
            <span>🔴 EVA</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Risk Matrix Visualization
# ---------------------------------------------------------------------------

def _render_risk_heatmap(engine: SchedulingEngine) -> None:
    """Render a risk heatmap for all crew members."""
    st.markdown("### 🎯 Risk Matrix")
    
    if render_echarts is None:
        st.warning("ECharts component not available")
        return
    
    crew_list = list(engine.crew_members.values())
    crew_names = [c.name for c in crew_list]
    
    # Risk dimensions
    dimensions = ["SAFTE", "HRV", "Hydration", "EA", "Circadian", "Overall"]
    
    # Build heatmap data
    data = []
    for crew_idx, crew in enumerate(crew_list):
        if crew.status:
            subscores = crew.status.compute_subscores()
            scores = [
                subscores.safte * 100,
                subscores.hrv * 100,
                subscores.hydration * 100,
                subscores.energy_availability * 100,
                subscores.circadian * 100,
                crew.get_ihpi(),
            ]
        else:
            scores = [75.0] * 6
        
        for dim_idx, score in enumerate(scores):
            data.append([dim_idx, crew_idx, round(score, 1)])
    
    option = {
        "backgroundColor": "transparent",
        "tooltip": {
            "position": "top",
            "formatter": """function(params) {
                return params.value[2] + '%';
            }""",
        },
        "grid": {
            "left": "20%",
            "right": "10%",
            "top": "5%",
            "bottom": "15%",
        },
        "xAxis": {
            "type": "category",
            "data": dimensions,
            "axisLabel": {"color": "#888", "rotate": 30},
            "axisLine": {"lineStyle": {"color": "#444"}},
            "splitArea": {"show": True},
        },
        "yAxis": {
            "type": "category",
            "data": crew_names,
            "axisLabel": {"color": "#ddd"},
            "axisLine": {"lineStyle": {"color": "#444"}},
            "splitArea": {"show": True},
        },
        "visualMap": {
            "min": 0,
            "max": 100,
            "calculable": True,
            "orient": "horizontal",
            "left": "center",
            "bottom": "0%",
            "inRange": {
                "color": ["#e74c3c", "#f39c12", "#f1c40f", "#27ae60"],
            },
            "textStyle": {"color": "#888"},
        },
        "series": [
            {
                "type": "heatmap",
                "data": data,
                "label": {
                    "show": True,
                    "formatter": "{@[2]}%",
                    "color": "#fff",
                    "fontSize": 10,
                },
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowColor": "rgba(0, 0, 0, 0.5)",
                    },
                },
            }
        ],
    }
    
    render_echarts(option, height_px=280)


# ---------------------------------------------------------------------------
# IHPI Gauge
# ---------------------------------------------------------------------------

def _render_ihpi_gauge(
    crew: CrewMember,
    height: int = 220,
) -> None:
    """Render an IHPI gauge for a crew member."""
    if render_echarts is None:
        st.metric(f"{crew.name} IHPI", f"{crew.get_ihpi():.0f}")
        return
    
    ihpi = crew.get_ihpi()
    risk = crew.get_risk_level()
    
    # Gauge color based on risk
    gauge_color = RISK_COLORS.get(risk, "#3498db")
    
    option = {
        "backgroundColor": "transparent",
        "series": [
            {
                "type": "gauge",
                "startAngle": 180,
                "endAngle": 0,
                "min": 0,
                "max": 100,
                "center": ["50%", "75%"],
                "radius": "90%",
                "progress": {
                    "show": True,
                    "width": 18,
                    "itemStyle": {"color": gauge_color},
                },
                "pointer": {"show": False},
                "axisLine": {
                    "lineStyle": {
                        "width": 18,
                        "color": [[1, "#333"]],
                    },
                },
                "axisTick": {"show": False},
                "splitLine": {"show": False},
                "axisLabel": {"show": False},
                "title": {
                    "offsetCenter": [0, "-10%"],
                    "fontSize": 14,
                    "color": "#888",
                },
                "detail": {
                    "valueAnimation": True,
                    "formatter": "{value}",
                    "fontSize": 28,
                    "fontWeight": "bold",
                    "offsetCenter": [0, "20%"],
                    "color": gauge_color,
                },
                "data": [{"value": round(ihpi, 0), "name": crew.name}],
            }
        ],
    }
    
    render_echarts(option, height_px=height)


# ---------------------------------------------------------------------------
# Activity Scheduling Controls
# ---------------------------------------------------------------------------

def _render_scheduling_controls(
    engine: SchedulingEngine,
    schedule_date: date,
) -> None:
    """Render activity scheduling controls."""
    st.markdown("### ➕ Schedule Activity")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        crew_options = {c.crew_id: c.name for c in engine.crew_members.values()}
        selected_crew = st.selectbox(
            "Crew Member",
            options=list(crew_options.keys()),
            format_func=lambda x: crew_options[x],
            key="schedule_crew_select",
        )
    
    with col2:
        activity_options = {a.id: a.name for a in list(FIXED_ACTIVITIES) + list(VARIABLE_ACTIVITIES)}
        selected_activity = st.selectbox(
            "Activity",
            options=list(activity_options.keys()),
            format_func=lambda x: activity_options[x],
            key="schedule_activity_select",
        )
    
    with col3:
        start_time = st.time_input(
            "Start Time",
            value=datetime.now().replace(hour=9, minute=0, second=0).time(),
            key="schedule_start_time",
        )
    
    col4, col5, col6 = st.columns(3)
    
    with col4:
        activity_def = ALL_ACTIVITIES.get(selected_activity)
        default_duration = activity_def.duration_min if activity_def else 60
        duration = st.number_input(
            "Duration (minutes)",
            min_value=15,
            max_value=480,
            value=default_duration,
            step=15,
            key="schedule_duration",
        )
    
    with col5:
        priority = st.slider(
            "Priority",
            min_value=1,
            max_value=10,
            value=5,
            key="schedule_priority",
        )
    
    with col6:
        notes = st.text_input(
            "Notes",
            value="",
            key="schedule_notes",
        )
    
    if st.button("📌 Schedule Activity", type="primary", key="schedule_btn"):
        start_datetime = datetime.combine(schedule_date, start_time)
        scheduled, conflicts = engine.schedule_activity(
            crew_id=selected_crew,
            activity_id=selected_activity,
            start_time=start_datetime,
            duration_minutes=duration,
            priority=priority,
            notes=notes,
        )
        
        if scheduled:
            st.success(f"✅ Scheduled {activity_options[selected_activity]} for {crew_options[selected_crew]}")
        else:
            st.error("❌ Could not schedule activity due to conflicts:")
        
        for conflict in conflicts:
            severity_icon = {"warning": "⚠️", "error": "❌", "critical": "🚫"}.get(conflict.severity, "ℹ️")
            st.warning(f"{severity_icon} {conflict.description} - {conflict.suggested_resolution}")


# ---------------------------------------------------------------------------
# Optimization Panel
# ---------------------------------------------------------------------------

def _render_optimization_panel(
    engine: SchedulingEngine,
    schedule_date: date,
) -> None:
    """Render schedule optimization panel."""
    st.markdown("### ⚡ Schedule Optimization")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        objective = st.selectbox(
            "Optimization Objective",
            options=["balanced", "safety_first", "mission_value"],
            format_func=lambda x: {
                "balanced": "⚖️ Balanced (Safety + Mission)",
                "safety_first": "🛡️ Safety First (Minimize Fatigue Risk)",
                "mission_value": "🎯 Mission Value (Maximize Completion)",
            }[x],
            key="opt_objective",
        )
    
    with col2:
        if st.button("🔄 Optimize Schedule", type="secondary", key="optimize_btn"):
            with st.spinner("Optimizing schedule..."):
                daily, score = engine.optimize_schedule(schedule_date, objective)
                st.success(f"✅ Optimization complete! Score: {score:.1f}/100")
    
    with col3:
        if st.button("📋 Generate Template", key="template_btn"):
            with st.spinner("Generating daily template..."):
                engine.generate_daily_template(schedule_date)
                st.success("✅ Daily template generated!")
    
    # Show current optimization score
    daily = engine.get_or_create_daily_schedule(schedule_date)
    if daily.is_optimized:
        st.metric("Optimization Score", f"{daily.optimization_score:.1f}/100")


# ---------------------------------------------------------------------------
# Performance Forecast Chart (Advanced)
# ---------------------------------------------------------------------------

def _render_performance_forecast(
    engine: SchedulingEngine,
    schedule_date: date,
) -> None:
    """Render 24-hour SAFTE effectiveness forecast for selected crew."""
    st.markdown("### 📈 24-Hour Performance Forecast")
    
    if not ADVANCED_FEATURES_AVAILABLE:
        st.warning("Advanced forecasting not available")
        return
    
    if render_echarts is None:
        st.warning("ECharts component not available")
        return
    
    # Crew selector
    crew_list = list(engine.crew_members.values())
    crew_names = [c.name for c in crew_list]
    
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_crew_name = st.selectbox(
            "Select Crew Member",
            options=crew_names,
            key="forecast_crew_select",
        )
    
    selected_crew = next((c for c in crew_list if c.name == selected_crew_name), None)
    if not selected_crew or not selected_crew.status:
        st.info("No status data available for selected crew member")
        return
    
    with col2:
        sleep_start_hour = st.number_input(
            "Planned Sleep Start (hour)",
            min_value=18,
            max_value=24,
            value=22,
            key="forecast_sleep_hour",
        )
    
    # Generate forecast
    from datetime import datetime, timedelta
    sleep_start = datetime.combine(
        schedule_date,
        datetime.min.time().replace(hour=sleep_start_hour),
    )
    
    forecast = simulate_safte_24h(
        current_status=selected_crew.status,
        planned_sleep_start=sleep_start,
        planned_sleep_duration_hours=8.0,
        chronotype_offset_hours=0.0,
        resolution_minutes=15,
    )
    
    # Build chart data
    times = [p.timestamp.strftime("%H:%M") for p in forecast.forecast_points]
    effectivenesses = [p.effectiveness for p in forecast.forecast_points]
    
    # Zone boundaries
    zone_90 = [90.0] * len(times)
    zone_80 = [80.0] * len(times)
    zone_70 = [70.0] * len(times)
    
    option = {
        "backgroundColor": "transparent",
        "title": {
            "text": f"SAFTE Effectiveness Forecast: {selected_crew_name}",
            "subtext": f"Min: {forecast.min_effectiveness:.1f}% | Avg: {forecast.avg_effectiveness:.1f}% | Below 90: {forecast.time_below_90_minutes}min",
            "left": "center",
            "textStyle": {"color": "#ddd", "fontSize": 14},
            "subtextStyle": {"color": "#888", "fontSize": 11},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
        },
        "legend": {
            "data": ["Effectiveness", "Low Risk (90%)", "Caution (80%)", "High Risk (70%)"],
            "bottom": 10,
            "textStyle": {"color": "#888"},
        },
        "grid": {
            "left": "10%",
            "right": "5%",
            "top": "20%",
            "bottom": "15%",
        },
        "xAxis": {
            "type": "category",
            "data": times,
            "axisLabel": {"color": "#888", "interval": 7},
            "axisLine": {"lineStyle": {"color": "#444"}},
        },
        "yAxis": {
            "type": "value",
            "min": 50,
            "max": 105,
            "axisLabel": {"color": "#888", "formatter": "{value}%"},
            "axisLine": {"lineStyle": {"color": "#444"}},
            "splitLine": {"lineStyle": {"color": "#333"}},
        },
        "series": [
            {
                "name": "Effectiveness",
                "type": "line",
                "data": effectivenesses,
                "smooth": True,
                "lineStyle": {"width": 3, "color": "#3498db"},
                "areaStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "rgba(52, 152, 219, 0.4)"},
                            {"offset": 1, "color": "rgba(52, 152, 219, 0.05)"},
                        ],
                    },
                },
                "symbol": "none",
            },
            {
                "name": "Low Risk (90%)",
                "type": "line",
                "data": zone_90,
                "lineStyle": {"type": "dashed", "color": "#27ae60", "width": 1},
                "symbol": "none",
            },
            {
                "name": "Caution (80%)",
                "type": "line",
                "data": zone_80,
                "lineStyle": {"type": "dashed", "color": "#f39c12", "width": 1},
                "symbol": "none",
            },
            {
                "name": "High Risk (70%)",
                "type": "line",
                "data": zone_70,
                "lineStyle": {"type": "dashed", "color": "#e74c3c", "width": 1},
                "symbol": "none",
            },
        ],
    }
    
    render_echarts(option, height_px=380)
    
    # Summary cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Min Effectiveness", f"{forecast.min_effectiveness:.1f}%")
    with col2:
        st.metric("Avg Effectiveness", f"{forecast.avg_effectiveness:.1f}%")
    with col3:
        st.metric("Time Below 90%", f"{forecast.time_below_90_minutes} min")
    with col4:
        st.metric("Time Below 70%", f"{forecast.time_below_70_minutes} min")
    
    # Optimal windows
    if forecast.optimal_work_windows:
        st.markdown("**🟢 Optimal Work Windows:**")
        windows = ", ".join([
            f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"
            for start, end in forecast.optimal_work_windows[:3]
        ])
        st.markdown(windows)


# ---------------------------------------------------------------------------
# What-If Analysis Panel (Advanced)
# ---------------------------------------------------------------------------

def _render_what_if_analysis(
    engine: SchedulingEngine,
) -> None:
    """Render what-if scenario analysis controls."""
    st.markdown("### 🔮 What-If Analysis")
    
    if not ADVANCED_FEATURES_AVAILABLE:
        st.warning("What-if analysis not available")
        return
    
    # Select crew member
    crew_list = list(engine.crew_members.values())
    crew_names = [c.name for c in crew_list]
    
    selected_name = st.selectbox(
        "Select Crew Member",
        options=crew_names,
        key="whatif_crew_select",
    )
    
    selected_crew = next((c for c in crew_list if c.name == selected_name), None)
    if not selected_crew or not selected_crew.status:
        st.info("No status data available")
        return
    
    # Current baseline
    current_ihpi = selected_crew.get_ihpi()
    current_eff = selected_crew.status.safte_effectiveness
    
    st.markdown(f"**Current Status:** IHPI = {current_ihpi:.1f} | SAFTE = {current_eff:.1f}%")
    
    st.markdown("---")
    
    # Scenario inputs
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sleep_change = st.slider(
            "Sleep Duration Change (hours)",
            min_value=-2.0,
            max_value=3.0,
            value=0.0,
            step=0.5,
            key="whatif_sleep",
        )
    
    with col2:
        nap_minutes = st.slider(
            "Add Nap (minutes)",
            min_value=0,
            max_value=60,
            value=0,
            step=10,
            key="whatif_nap",
        )
    
    with col3:
        wake_shift = st.slider(
            "Wake Time Shift (hours)",
            min_value=-2.0,
            max_value=2.0,
            value=0.0,
            step=0.5,
            key="whatif_wake",
        )
    
    # Create and analyze scenario
    scenario = WhatIfScenario(
        scenario_id="user_scenario",
        name="Custom Scenario",
        description="User-defined what-if scenario",
        sleep_change_hours=sleep_change,
        nap_added_minutes=nap_minutes,
        wake_time_shift_hours=wake_shift,
    )
    
    result = analyze_what_if(selected_crew.status, scenario)
    
    # Display results
    st.markdown("---")
    st.markdown("#### 📊 Projected Outcomes")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        delta_ihpi = result.projected_ihpi - current_ihpi
        st.metric(
            "Projected IHPI",
            f"{result.projected_ihpi:.1f}",
            delta=f"{delta_ihpi:+.1f}",
            delta_color="normal" if delta_ihpi >= 0 else "inverse",
        )
    
    with col2:
        risk_color = RISK_COLORS.get(result.projected_risk, "#888")
        st.markdown(
            f"**Projected Risk:** "
            f"<span style='color: {risk_color}; font-weight: bold;'>{result.projected_risk.value.upper()}</span>",
            unsafe_allow_html=True,
        )
    
    with col3:
        st.markdown(f"**Effectiveness Δ:** {result.effectiveness_delta:+.1f}%")
    
    # Recommendation
    st.info(result.recommendation)
    
    # Quick scenarios
    st.markdown("#### 🚀 Quick Scenarios")
    
    quick_cols = st.columns(4)
    
    quick_scenarios = [
        ("💤 +1h Sleep", 1.0, 0, 0.0),
        ("😴 20min Nap", 0.0, 20, 0.0),
        ("⏰ Wake 1h Earlier", 0.0, 0, -1.0),
        ("🌙 +2h Sleep", 2.0, 0, 0.0),
    ]
    
    for idx, (label, sleep, nap, wake) in enumerate(quick_scenarios):
        with quick_cols[idx]:
            quick_scenario = WhatIfScenario(
                scenario_id=f"quick_{idx}",
                name=label,
                description="",
                sleep_change_hours=sleep,
                nap_added_minutes=nap,
                wake_time_shift_hours=wake,
            )
            quick_result = analyze_what_if(selected_crew.status, quick_scenario)
            
            delta = quick_result.projected_ihpi - current_ihpi
            color = COLORS["good"] if delta > 0 else COLORS["poor"] if delta < -2 else COLORS["normal"]
            
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, {color}22, {color}11);
                    border: 1px solid {color};
                    border-radius: 8px;
                    padding: 12px;
                    text-align: center;
                ">
                    <div style="font-size: 0.9em;">{label}</div>
                    <div style="font-size: 1.4em; font-weight: 700; color: {color};">
                        {quick_result.projected_ihpi:.1f}
                    </div>
                    <div style="font-size: 0.8em; color: #888;">
                        {delta:+.1f} IHPI
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Workload Balance Visualization (Advanced)
# ---------------------------------------------------------------------------

def _render_workload_balance(
    engine: SchedulingEngine,
    schedule_date: date,
) -> None:
    """Render workload balance chart for all crew members."""
    st.markdown("### ⚖️ Workload Balance")
    
    if render_echarts is None:
        st.warning("ECharts component not available")
        return
    
    crew_list = list(engine.crew_members.values())
    
    # Get schedule for the day
    schedule = engine.get_schedule(schedule_date)
    
    # Calculate workload for each crew member
    workload_data = []
    for crew in crew_list:
        crew_activities = schedule.get_crew_activities(crew.crew_id) if schedule else []
        
        # Calculate metrics
        total_work = 0
        total_rest = 0
        high_intensity = 0
        cognitive = 0
        total_kcal = 0.0
        
        for activity in crew_activities:
            duration = activity.duration_minutes
            met = activity.met_value
            
            if activity.activity_id in ('sleep', 'recreation'):
                total_rest += duration
            else:
                total_work += duration
            
            if met > 4.0:
                high_intensity += duration
            
            if activity.activity_id in ('lab_work', 'briefing', 'eva'):
                cognitive += duration
            
            total_kcal += activity.estimated_kcal
        
        workload_data.append({
            "name": crew.name,
            "work": total_work,
            "rest": total_rest,
            "high_intensity": high_intensity,
            "cognitive": cognitive,
            "kcal": total_kcal,
            "ihpi": crew.get_ihpi(),
        })
    
    # Build stacked bar chart
    crew_names = [d["name"] for d in workload_data]
    work_minutes = [d["work"] for d in workload_data]
    rest_minutes = [d["rest"] for d in workload_data]
    
    option = {
        "backgroundColor": "transparent",
        "title": {
            "text": "Work vs Rest Balance",
            "left": "center",
            "textStyle": {"color": "#ddd", "fontSize": 14},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": """function(params) {
                var work = params[0].value;
                var rest = params[1].value;
                var ratio = (work / Math.max(1, rest)).toFixed(2);
                return params[0].name + '<br/>' +
                       'Work: ' + work + ' min<br/>' +
                       'Rest: ' + rest + ' min<br/>' +
                       'Ratio: ' + ratio;
            }""",
        },
        "legend": {
            "data": ["Work", "Rest"],
            "bottom": 10,
            "textStyle": {"color": "#888"},
        },
        "grid": {
            "left": "15%",
            "right": "5%",
            "top": "15%",
            "bottom": "20%",
        },
        "xAxis": {
            "type": "category",
            "data": crew_names,
            "axisLabel": {"color": "#888", "rotate": 30},
            "axisLine": {"lineStyle": {"color": "#444"}},
        },
        "yAxis": {
            "type": "value",
            "name": "Minutes",
            "nameTextStyle": {"color": "#888"},
            "axisLabel": {"color": "#888"},
            "axisLine": {"lineStyle": {"color": "#444"}},
            "splitLine": {"lineStyle": {"color": "#333"}},
        },
        "series": [
            {
                "name": "Work",
                "type": "bar",
                "stack": "total",
                "data": work_minutes,
                "itemStyle": {"color": "#3498db"},
            },
            {
                "name": "Rest",
                "type": "bar",
                "stack": "total",
                "data": rest_minutes,
                "itemStyle": {"color": "#27ae60"},
            },
        ],
    }
    
    render_echarts(option, height_px=320)
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    avg_work = sum(work_minutes) / len(work_minutes) if work_minutes else 0
    avg_rest = sum(rest_minutes) / len(rest_minutes) if rest_minutes else 0
    total_kcal = sum(d["kcal"] for d in workload_data)
    
    with col1:
        st.metric("Avg Work Time", f"{avg_work:.0f} min")
    with col2:
        st.metric("Avg Rest Time", f"{avg_rest:.0f} min")
    with col3:
        st.metric("Total Energy", f"{total_kcal:.0f} kcal")


# ---------------------------------------------------------------------------
# Alerts Panel
# ---------------------------------------------------------------------------

def _render_alerts_panel(
    engine: SchedulingEngine,
    schedule_date: date,
) -> None:
    """Render rescheduling triggers and alerts."""
    triggers = engine.check_rescheduling_triggers(schedule_date)
    
    if triggers:
        st.markdown("### ⚠️ Alerts & Triggers")
        
        for trigger in triggers:
            crew = engine.crew_members.get(trigger["crew_id"])
            crew_name = crew.name if crew else trigger["crew_id"]
            
            severity_styles = {
                "warning": ("⚠️", "orange"),
                "critical": ("🚨", "red"),
                "info": ("ℹ️", "blue"),
            }
            icon, color = severity_styles.get(trigger["severity"], ("ℹ️", "gray"))
            
            st.markdown(
                f"""
                <div style="
                    border-left: 4px solid {color};
                    padding: 10px 15px;
                    margin: 8px 0;
                    background: rgba(255,255,255,0.05);
                    border-radius: 0 8px 8px 0;
                ">
                    <div style="font-weight: 600;">{icon} {crew_name}</div>
                    <div style="color: #888; font-size: 0.9em;">{trigger['description']}</div>
                    <div style="color: #aaa; font-size: 0.85em; margin-top: 4px;">
                        💡 {trigger['recommended_action']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("✅ No active alerts or rescheduling triggers")


# ---------------------------------------------------------------------------
# Crew Summary Table
# ---------------------------------------------------------------------------

def _render_crew_summary_table(
    engine: SchedulingEngine,
    schedule_date: date,
) -> None:
    """Render a summary table of crew status and activities."""
    st.markdown("### 📊 Crew Summary")
    
    summaries = engine.get_crew_summary(schedule_date)
    
    if not summaries:
        st.info("No crew data available")
        return
    
    # Convert to DataFrame for display
    df = pd.DataFrame(summaries)
    
    # Select and rename columns for display
    display_cols = {
        "name": "Name",
        "role": "Role",
        "ihpi": "IHPI",
        "risk_level": "Risk",
        "activities_count": "Activities",
        "total_scheduled_minutes": "Time (min)",
        "total_kcal": "kcal",
    }
    
    if "safte_effectiveness" in df.columns:
        display_cols["safte_effectiveness"] = "SAFTE %"
    if "eva_status" in df.columns:
        display_cols["eva_status"] = "EVA Status"
    
    available_cols = [c for c in display_cols.keys() if c in df.columns]
    df_display = df[available_cols].rename(columns={c: display_cols[c] for c in available_cols})
    
    # Format numeric columns
    if "IHPI" in df_display.columns:
        df_display["IHPI"] = df_display["IHPI"].round(1)
    if "SAFTE %" in df_display.columns:
        df_display["SAFTE %"] = df_display["SAFTE %"].round(1)
    if "kcal" in df_display.columns:
        df_display["kcal"] = df_display["kcal"].round(0).astype(int)
    
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------------------------
# Export Panel
# ---------------------------------------------------------------------------

def _render_export_panel(
    engine: SchedulingEngine,
    schedule_date: date,
) -> None:
    """Render schedule export options."""
    st.markdown("### 📤 Export Schedule")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 Export as JSON", key="export_json_btn"):
            json_data = engine.export_schedule_json(schedule_date)
            st.download_button(
                label="⬇️ Download JSON",
                data=json_data,
                file_name=f"schedule_{schedule_date.isoformat()}.json",
                mime="application/json",
                key="download_json_btn",
            )
    
    with col2:
        summaries = engine.get_crew_summary(schedule_date)
        if summaries:
            df = pd.DataFrame(summaries)
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_data,
                file_name=f"crew_summary_{schedule_date.isoformat()}.csv",
                mime="text/csv",
                key="download_csv_btn",
            )


# ---------------------------------------------------------------------------
# Main Tab Renderer
# ---------------------------------------------------------------------------

def render_scheduling_tab() -> None:
    """Render the complete scheduling tab."""
    if not SCHEDULING_AVAILABLE:
        st.error(
            "Scheduling module not available. "
            "Please ensure `scheduling_core.py` and `scheduling_engine.py` are present."
        )
        return
    
    _init_scheduling_session_state()
    engine = _get_engine()
    
    # Header
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 20px 24px;
            border-radius: 12px;
            margin-bottom: 20px;
            border: 1px solid #2a2a4a;
        ">
            <h2 style="margin: 0; color: #fff;">🗓️ Crew Scheduling & Human Performance</h2>
            <p style="margin: 8px 0 0 0; color: #888; font-size: 0.95em;">
                Evidence-based scheduling with SAFTE-FAST integration • IHPI composite scoring • GO/NO-GO decision support
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Date selector
    col_date, col_spacer = st.columns([1, 3])
    with col_date:
        schedule_date = st.date_input(
            "📅 Schedule Date",
            value=st.session_state.get("selected_schedule_date", date.today()),
            key="schedule_date_picker",
        )
        st.session_state["selected_schedule_date"] = schedule_date
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👥 Status Dashboard",
        "📅 Timeline & Scheduling",
        "📈 Performance Forecast",
        "🎯 Risk Analysis",
        "📊 Summary & Export",
    ])
    
    with tab1:
        _render_crew_status_grid(engine)
        st.markdown("---")
        _render_alerts_panel(engine, schedule_date)
    
    with tab2:
        _render_timeline_chart(engine, schedule_date)
        st.markdown("---")
        _render_scheduling_controls(engine, schedule_date)
        st.markdown("---")
        _render_optimization_panel(engine, schedule_date)
    
    with tab3:
        # Performance Forecast (Advanced)
        _render_performance_forecast(engine, schedule_date)
        st.markdown("---")
        _render_what_if_analysis(engine)
        st.markdown("---")
        _render_workload_balance(engine, schedule_date)
    
    with tab4:
        _render_risk_heatmap(engine)
        st.markdown("---")
        
        # Individual IHPI gauges
        st.markdown("### 📈 Individual Performance Indicators")
        crew_list = list(engine.crew_members.values())
        gauge_cols = st.columns(3)
        for idx, crew in enumerate(crew_list[:6]):
            with gauge_cols[idx % 3]:
                _render_ihpi_gauge(crew)
    
    with tab5:
        _render_crew_summary_table(engine, schedule_date)
        st.markdown("---")
        _render_export_panel(engine, schedule_date)
    
    # References footer
    with st.expander("📚 Scientific References", expanded=False):
        st.markdown(
            """
            **SAFTE-FAST Model:**
            - Hursh SR, et al. (2004). Fatigue models for applied research in warfighting. *Aviat Space Environ Med.* 75(3 Suppl):A44-53.
            
            **EVA Metabolic Requirements:**
            - NASA-STD-3001: Human Performance Capabilities - VO₂max ≥32.9 ml/kg/min for microgravity EVA
            - Skylab EVA mean: ~238 kcal/hr; Shuttle EVA average: ~194 kcal/hr (NASA NTRS)
            
            **HRV & Recovery:**
            - Plews DJ, et al. (2013). Training adaptation and heart rate variability. *Int J Sports Physiol Perform.* 8(6):688-91.
            - Task Force ESC/NASPE (1996). *Eur Heart J.* 17:354-381.
            
            **Energy Availability:**
            - IOC Consensus Statement (2018). Relative Energy Deficiency in Sport (RED-S). *Br J Sports Med.* 52:687-697.
            
            **MET Values:**
            - Ainsworth BE, et al. (2024). 2024 Adult Compendium of Physical Activities.
            """
        )


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    "render_scheduling_tab",
    "SCHEDULING_AVAILABLE",
]

