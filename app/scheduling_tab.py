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
        # EVA Procedures
        EVAChecklistItem,
        ISLE_PROTOCOL_TIMELINE,
        MCC_EVA_CHECKLIST,
        EVA_OFFICER_CHECKLIST,
        ANALOG_EVA_TIMELINE,
        EXPERIMENT_IDS,
        # Radiation Assessment
        RadiationRiskLevel,
        RadiationAssessment,
        assess_radiation_for_eva,
        NASA_CAREER_DOSE_LIMIT_MSV,
        SPE_ALERT_THRESHOLD_PFU,
        SPE_WARNING_THRESHOLD_PFU,
        # NASA Scheduling Factors
        NOMINAL_WORKDAY_HOURS,
        MAX_WORKDAY_HOURS,
        MAX_CONTINUOUS_WORK_HOURS,
        COGNITIVE_WORKLOAD_LOW,
        COGNITIVE_WORKLOAD_MEDIUM,
        COGNITIVE_WORKLOAD_HIGH,
        PHYSICAL_WORKLOAD_TARGET,
        ISS_SCHEDULING_CONSTRAINTS,
        TASK_CATEGORIES,
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

# Activity color palette (consistent with scientific standards)
ACTIVITY_COLORS: Dict[str, str] = {
    "briefing": "#3498db",    # Blue
    "breakfast": "#f1c40f",   # Yellow
    "lunch": "#f39c12",       # Orange
    "dinner": "#e67e22",      # Dark orange
    "exercise": "#27ae60",    # Green
    "recreation": "#9b59b6",  # Purple
    "hygiene": "#1abc9c",     # Teal
    "sleep": "#34495e",       # Dark gray
    "lab_work": "#2980b9",    # Blue
    "eva": "#e74c3c",         # Red
    "nap": "#5d6d7e",         # Gray-blue
    "medical": "#e91e63",     # Pink
    "communication": "#00bcd4",  # Cyan
}


def _render_gantt_timeline(
    engine: SchedulingEngine,
    schedule_date: date,
    height_px: int = 420,
) -> None:
    """Render a true Gantt chart timeline using ECharts custom series.
    
    This function embeds the JavaScript renderItem function directly in the HTML
    to bypass JSON serialization limitations. Based on the official ECharts
    custom-gantt-flight example.
    
    References:
        - https://echarts.apache.org/examples/en/editor.html?c=custom-gantt-flight
        - ECharts Custom Series documentation
    """
    daily = engine.get_daily_schedule(schedule_date)
    crew_list = list(engine.crew_members.values())
    crew_names = [c.name for c in crew_list]
    
    if not crew_names:
        st.info("No crew members configured. Add crew members in the sidebar.")
        return
    
    # Prepare activity data: [crew_index, start_hour, end_hour, activity_id, activity_name]
    gantt_data = []
    legend_items: Dict[str, str] = {}
    activities = daily.activities if daily else []
    
    for activity in activities:
        crew = engine.crew_members.get(activity.crew_id)
        if not crew or crew.name not in crew_names:
            continue
        
        crew_idx = crew_names.index(crew.name)
        start_hour = activity.start_time.hour + activity.start_time.minute / 60
        end_hour = activity.end_time.hour + activity.end_time.minute / 60
        
        # Handle midnight crossing
        if end_hour <= start_hour:
            end_hour += 24
        
        color = ACTIVITY_COLORS.get(activity.activity_id, "#7f8c8d")
        activity_def = ALL_ACTIVITIES.get(activity.activity_id)
        display_name = activity_def.name if activity_def else activity.activity_name
        
        gantt_data.append({
            "value": [crew_idx, start_hour, end_hour],
            "name": display_name,
            "itemStyle": {"color": color},
            "activity_id": activity.activity_id,
            "start_str": activity.start_time.strftime("%H:%M"),
            "end_str": activity.end_time.strftime("%H:%M"),
            "duration": activity.duration_minutes,
        })
        
        legend_items[display_name] = color
    
    # Convert data for JS
    data_js = json.dumps(gantt_data, ensure_ascii=False)
    crew_names_js = json.dumps(crew_names, ensure_ascii=False)
    legend_data_js = json.dumps(list(legend_items.keys()), ensure_ascii=False)
    title_text = f"Crew Schedule — {schedule_date.strftime('%A, %B %d, %Y')}"
    
    # Build complete HTML with embedded renderItem function
    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ background: transparent; font-family: system-ui, -apple-system, sans-serif; }}
            #chart {{ width: 100%; height: {height_px}px; }}
        </style>
    </head>
    <body>
        <div id="chart"></div>
        <script>
        (function() {{
            var chartDom = document.getElementById('chart');
            var myChart = echarts.init(chartDom, null, {{ renderer: 'canvas' }});
            
            var crewNames = {crew_names_js};
            var data = {data_js};
            var legendData = {legend_data_js};
            
            // Custom render function for Gantt bars
            function renderGanttItem(params, api) {{
                var categoryIndex = api.value(0);
                var startValue = api.value(1);
                var endValue = api.value(2);
                
                var start = api.coord([startValue, categoryIndex]);
                var end = api.coord([endValue, categoryIndex]);
                var height = api.size([0, 1])[1] * 0.6;
                
                var rectShape = echarts.graphic.clipRectByRect(
                    {{
                        x: start[0],
                        y: start[1] - height / 2,
                        width: Math.max(end[0] - start[0], 4),
                        height: height
                    }},
                    {{
                        x: params.coordSys.x,
                        y: params.coordSys.y,
                        width: params.coordSys.width,
                        height: params.coordSys.height
                    }}
                );
                
                return rectShape && {{
                    type: 'rect',
                    shape: rectShape,
                    style: api.style(),
                    emphasis: {{
                        style: {{
                            shadowBlur: 10,
                            shadowColor: 'rgba(0,0,0,0.3)'
                        }}
                    }}
                }};
            }}
            
            var option = {{
                backgroundColor: 'transparent',
                title: {{
                    text: '{title_text}',
                    subtext: '24-hour timeline • Hover for details • Scroll to zoom',
                    left: 'center',
                    textStyle: {{ fontSize: 16, fontWeight: 'bold', color: '#f0f0f0' }},
                    subtextStyle: {{ fontSize: 12, color: '#b0b0b0' }}
                }},
                tooltip: {{
                    trigger: 'item',
                    backgroundColor: 'rgba(20, 40, 70, 0.95)',
                    borderColor: '#3498db',
                    borderWidth: 1,
                    textStyle: {{ color: '#fff', fontSize: 13 }},
                    formatter: function(params) {{
                        var d = params.data;
                        return '<div style="font-weight:bold;margin-bottom:6px;color:#fff;font-size:14px;">' + d.name + '</div>' +
                               '<div style="color:#e0e0e0;">Crew: ' + crewNames[d.value[0]] + '</div>' +
                               '<div style="color:#e0e0e0;">Time: ' + d.start_str + ' – ' + d.end_str + '</div>' +
                               '<div style="color:#e0e0e0;">Duration: ' + d.duration + ' min</div>';
                    }}
                }},
                legend: {{
                    data: legendData,
                    bottom: 8,
                    textStyle: {{ color: '#d0d0d0', fontSize: 11, fontWeight: '500' }},
                    itemWidth: 16,
                    itemHeight: 12
                }},
                grid: {{
                    left: '14%',
                    right: '5%',
                    top: '15%',
                    bottom: '20%',
                    containLabel: true
                }},
                xAxis: {{
                    type: 'value',
                    name: 'Hour of Day',
                    nameLocation: 'middle',
                    nameGap: 32,
                    nameTextStyle: {{ color: '#c0c0c0', fontSize: 13, fontWeight: 'bold' }},
                    min: 0,
                    max: 24,
                    interval: 2,
                    axisLabel: {{
                        formatter: function(v) {{ return v + ':00'; }},
                        color: '#d0d0d0',
                        fontSize: 11,
                        fontWeight: '500'
                    }},
                    axisLine: {{ lineStyle: {{ color: '#5a5a7a', width: 2 }} }},
                    splitLine: {{ lineStyle: {{ color: '#3a3a5a', type: 'dashed' }} }}
                }},
                yAxis: {{
                    type: 'category',
                    data: crewNames,
                    inverse: true,
                    axisLabel: {{ color: '#f0f0f0', fontSize: 12, fontWeight: '500' }},
                    axisLine: {{ lineStyle: {{ color: '#5a5a7a', width: 2 }} }},
                    splitLine: {{ show: true, lineStyle: {{ color: '#3a3a5a', type: 'dashed' }} }}
                }},
                dataZoom: [
                    {{ type: 'inside', xAxisIndex: 0, filterMode: 'weakFilter' }},
                    {{ type: 'slider', xAxisIndex: 0, height: 22, bottom: 38, filterMode: 'weakFilter',
                       borderColor: '#5a5a7a', backgroundColor: '#1e2a3a',
                       fillerColor: 'rgba(52, 152, 219, 0.4)', handleStyle: {{ color: '#3498db' }},
                       textStyle: {{ color: '#d0d0d0' }} }}
                ],
                series: [{{
                    type: 'custom',
                    renderItem: renderGanttItem,
                    encode: {{
                        x: [1, 2],
                        y: 0
                    }},
                    data: data
                }}]
            }};
            
            myChart.setOption(option);
            
            // Handle resize
            window.addEventListener('resize', function() {{
                myChart.resize();
            }});
            
            // ResizeObserver for iframe resize
            var ro = new ResizeObserver(function() {{
                myChart.resize();
            }});
            ro.observe(chartDom);
        }})();
        </script>
    </body>
    </html>
    '''
    
    # Render using Streamlit's HTML component
    st.components.v1.html(html_content, height=height_px + 20, scrolling=False)


def _render_timeline_chart(
    engine: SchedulingEngine,
    schedule_date: date,
) -> None:
    """Render a 24-hour timeline using the Gantt chart visualization."""
    st.markdown("### 📅 Daily Timeline")
    
    daily = engine.get_daily_schedule(schedule_date)
    crew_list = list(engine.crew_members.values())
    
    if not crew_list:
        st.info("No crew members configured. Add crew members using the sidebar controls.")
        return
    
    if not daily or not daily.activities:
        st.info("No activities scheduled for this date. Use the scheduling controls below to add activities.")
        _render_empty_timeline([c.name for c in crew_list])
        return
    
    # Render the Gantt chart
    _render_gantt_timeline(engine, schedule_date, height_px=420)
    
    # Activity legend with colors
    st.markdown("---")
    _render_activity_legend()


def _render_empty_timeline(crew_names: List[str]) -> None:
    """Render an empty timeline placeholder."""
    if render_echarts is None:
        return
    
    option = {
        "title": {
            "text": "No Activities Scheduled",
            "subtext": "Add activities using the controls below",
            "left": "center",
            "top": "40%",
            "textStyle": {"fontSize": 16, "color": "#888"},
            "subtextStyle": {"fontSize": 12, "color": "#666"},
        },
        "grid": {
            "left": "12%",
            "right": "5%",
            "top": "18%",
            "bottom": "15%",
        },
        "xAxis": {
            "type": "value",
            "min": 0,
            "max": 24,
            "interval": 2,
            "axisLabel": {"formatter": "{value}:00", "color": "#666"},
            "axisLine": {"lineStyle": {"color": "#444"}},
            "splitLine": {"lineStyle": {"color": "#333", "type": "dashed"}},
        },
        "yAxis": {
            "type": "category",
            "data": crew_names,
            "inverse": True,
            "axisLabel": {"color": "#888"},
            "axisLine": {"lineStyle": {"color": "#444"}},
        },
        "series": [],
    }
    render_echarts(option, height_px=280)


def _render_activity_legend() -> None:
    """Render a visual activity legend with color boxes."""
    legend_items = [
        ("Briefing", ACTIVITY_COLORS["briefing"]),
        ("Breakfast", ACTIVITY_COLORS["breakfast"]),
        ("Lunch", ACTIVITY_COLORS["lunch"]),
        ("Dinner", ACTIVITY_COLORS["dinner"]),
        ("Exercise", ACTIVITY_COLORS["exercise"]),
        ("Recreation", ACTIVITY_COLORS["recreation"]),
        ("Hygiene", ACTIVITY_COLORS["hygiene"]),
        ("Sleep", ACTIVITY_COLORS["sleep"]),
        ("Lab Work", ACTIVITY_COLORS["lab_work"]),
        ("EVA", ACTIVITY_COLORS["eva"]),
    ]
    
    st.markdown("**Activity Types:**")
    cols = st.columns(5)
    for idx, (name, color) in enumerate(legend_items):
        with cols[idx % 5]:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0;">'
                f'<div style="width:16px;height:16px;background:{color};border-radius:3px;"></div>'
                f'<span style="font-size:0.85em;color:#ccc;">{name}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Weekly Overview Calendar
# ---------------------------------------------------------------------------

def _render_weekly_overview(
    engine: SchedulingEngine,
    schedule_date: date,
) -> None:
    """Render a weekly calendar heatmap showing activity density.
    
    Shows 7 days centered on the selected date, with color intensity
    indicating activity count per crew member per day.
    """
    st.markdown("### 📆 Weekly Overview")
    
    if render_echarts is None:
        st.warning("ECharts component not available")
        return
    
    # Get 7 days centered on selected date
    start_date = schedule_date - timedelta(days=3)
    days = [start_date + timedelta(days=i) for i in range(7)]
    day_labels = [d.strftime("%a\n%m/%d") for d in days]
    
    crew_list = list(engine.crew_members.values())
    crew_names = [c.name for c in crew_list]
    
    if not crew_names:
        st.info("No crew members configured.")
        return
    
    # Build heatmap data: [day_index, crew_index, activity_count]
    data = []
    max_activities = 1
    
    for day_idx, day in enumerate(days):
        daily = engine.get_daily_schedule(day)
        activities = daily.activities if daily else []
        
        # Count activities per crew member
        crew_counts: Dict[str, int] = {c.crew_id: 0 for c in crew_list}
        for activity in activities:
            if activity.crew_id in crew_counts:
                crew_counts[activity.crew_id] += 1
        
        for crew_idx, crew in enumerate(crew_list):
            count = crew_counts.get(crew.crew_id, 0)
            max_activities = max(max_activities, count)
            data.append([day_idx, crew_idx, count])
    
    # Highlight current day
    current_day_idx = days.index(schedule_date) if schedule_date in days else 3
    
    option = {
        "title": {
            "text": f"Activity Density — Week of {start_date.strftime('%B %d')}",
            "left": "center",
            "textStyle": {"fontSize": 14, "color": "#ddd"},
        },
        "tooltip": {
            "position": "top",
            "backgroundColor": "rgba(30, 30, 50, 0.95)",
            "borderColor": "#444",
            "textStyle": {"color": "#fff"},
        },
        "grid": {
            "left": "15%",
            "right": "8%",
            "top": "15%",
            "bottom": "10%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": day_labels,
            "axisLabel": {"color": "#888", "fontSize": 10},
            "axisLine": {"lineStyle": {"color": "#444"}},
            "splitArea": {"show": True, "areaStyle": {"color": ["rgba(0,0,0,0)", "rgba(255,255,255,0.02)"]}},
        },
        "yAxis": {
            "type": "category",
            "data": crew_names,
            "axisLabel": {"color": "#ddd", "fontSize": 11},
            "axisLine": {"lineStyle": {"color": "#444"}},
        },
        "visualMap": {
            "min": 0,
            "max": max(max_activities, 10),
            "calculable": True,
            "orient": "vertical",
            "right": "2%",
            "top": "center",
            "itemHeight": 100,
            "textStyle": {"color": "#888"},
            "inRange": {
                "color": ["#1a1a2e", "#2d4a3e", "#27ae60", "#f39c12", "#e74c3c"],
            },
        },
        "series": [{
            "name": "Activities",
            "type": "heatmap",
            "data": data,
            "label": {
                "show": True,
                "color": "#fff",
                "fontSize": 12,
                "fontWeight": "bold",
            },
            "emphasis": {
                "itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0,0,0,0.5)"},
            },
            "markLine": {
                "silent": True,
                "data": [{"xAxis": current_day_idx}],
                "lineStyle": {"color": "#3498db", "width": 2, "type": "solid"},
                "label": {"show": False},
                "symbol": "none",
            },
        }],
    }
    
    render_echarts(option, height_px=250)


# ---------------------------------------------------------------------------
# Activity List View
# ---------------------------------------------------------------------------

def _render_activity_list(
    engine: SchedulingEngine,
    schedule_date: date,
) -> None:
    """Render a tabular list of activities for the selected date.
    
    Provides an alternative view to the Gantt chart with edit/delete controls.
    """
    st.markdown("### 📋 Activity List")
    
    daily = engine.get_daily_schedule(schedule_date)
    
    if not daily or not daily.activities:
        st.info("No activities scheduled for this date.")
        return
    
    # Group activities by crew member
    crew_activities: Dict[str, List[ScheduledActivity]] = {}
    for activity in sorted(daily.activities, key=lambda a: a.start_time):
        if activity.crew_id not in crew_activities:
            crew_activities[activity.crew_id] = []
        crew_activities[activity.crew_id].append(activity)
    
    # Display by crew member
    for crew_id, activities in crew_activities.items():
        crew = engine.crew_members.get(crew_id)
        crew_name = crew.name if crew else crew_id
        
        with st.expander(f"👤 {crew_name} ({len(activities)} activities)", expanded=True):
            for activity in activities:
                color = ACTIVITY_COLORS.get(activity.activity_id, "#7f8c8d")
                
                col1, col2, col3, col4, col5 = st.columns([0.5, 2, 1.5, 1, 0.8])
                
                with col1:
                    st.markdown(
                        f'<div style="width:20px;height:20px;background:{color};border-radius:4px;margin-top:8px;"></div>',
                        unsafe_allow_html=True,
                    )
                
                with col2:
                    st.markdown(f"**{activity.activity_name}**")
                    if activity.notes:
                        st.caption(activity.notes)
                
                with col3:
                    st.markdown(
                        f"🕐 {activity.start_time.strftime('%H:%M')} – {activity.end_time.strftime('%H:%M')}"
                    )
                
                with col4:
                    st.markdown(f"⏱️ {activity.duration_minutes} min")
                
                with col5:
                    if st.button("🗑️", key=f"del_{activity.start_time}_{activity.activity_id}_{crew_id}"):
                        # Remove activity from schedule
                        daily.activities = [
                            a for a in daily.activities
                            if not (a.crew_id == crew_id and 
                                   a.activity_id == activity.activity_id and
                                   a.start_time == activity.start_time)
                        ]
                        st.rerun()
                
                st.markdown("---")


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
            "left": "18%",
            "right": "8%",
            "top": "8%",
            "bottom": "25%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": dimensions,
            "axisLabel": {
                "color": "#1a1a1a",
                "rotate": 0,
                "fontSize": 12,
                "fontWeight": "bold",
            },
            "axisLine": {"lineStyle": {"color": "#555"}},
            "splitArea": {"show": True},
        },
        "yAxis": {
            "type": "category",
            "data": crew_names,
            "axisLabel": {
                "color": "#1a1a1a",
                "fontSize": 11,
            },
            "axisLine": {"lineStyle": {"color": "#555"}},
            "splitArea": {"show": True},
        },
        "visualMap": {
            "min": 0,
            "max": 100,
            "calculable": True,
            "orient": "horizontal",
            "left": "center",
            "bottom": "2%",
            "itemWidth": 20,
            "itemHeight": 140,
            "inRange": {
                "color": ["#e74c3c", "#f39c12", "#f1c40f", "#27ae60"],
            },
            "textStyle": {"color": "#1a1a1a", "fontSize": 11},
            "text": ["100%", "0%"],
        },
        "series": [
            {
                "type": "heatmap",
                "data": data,
                "label": {
                    "show": True,
                    "formatter": "{@[2]}%",
                    "color": "#fff",
                    "fontSize": 11,
                    "fontWeight": "bold",
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
    
    render_echarts(option, height_px=420)


# ---------------------------------------------------------------------------
# IHPI Gauge
# ---------------------------------------------------------------------------

def _render_ihpi_gauge(
    crew: CrewMember,
    height: int = 280,
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
                "center": ["50%", "60%"],
                "radius": "85%",
                "progress": {
                    "show": True,
                    "width": 20,
                    "itemStyle": {"color": gauge_color},
                },
                "pointer": {"show": False},
                "axisLine": {
                    "lineStyle": {
                        "width": 20,
                        "color": [[1, "#333"]],
                    },
                },
                "axisTick": {"show": False},
                "splitLine": {"show": False},
                "axisLabel": {"show": False},
                "title": {
                    "offsetCenter": [0, "35%"],
                    "fontSize": 13,
                    "color": "#1a1a1a",
                    "fontWeight": "500",
                },
                "detail": {
                    "valueAnimation": True,
                    "formatter": "{value}",
                    "fontSize": 32,
                    "fontWeight": "bold",
                    "offsetCenter": [0, "0%"],
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
    
    # Show current optimization score (read-only display)
    daily = engine.get_daily_schedule(schedule_date)
    if daily and daily.is_optimized:
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
    """Render workload balance chart for all crew members.
    
    Note: This is a display-only function that does NOT create schedules.
    Uses read-only get_daily_schedule() to avoid side effects.
    """
    st.markdown("### ⚖️ Workload Balance")
    
    if render_echarts is None:
        st.warning("ECharts component not available")
        return
    
    crew_list = list(engine.crew_members.values())
    
    # Get schedule for the day (read-only, does not create if missing)
    schedule = engine.get_daily_schedule(schedule_date)
    
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
            "axisLabel": {"color": "#1a1a1a", "rotate": 0},
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
# EVA Procedures Panel
# ---------------------------------------------------------------------------

def _render_eva_procedures_panel(
    engine: SchedulingEngine,
    schedule_date: date,
) -> None:
    """Render EVA procedures, checklists, and scheduling panel.
    
    Includes:
    - ISLE Protocol timeline with verification checkboxes
    - Mission Control EVA checklist
    - EVA Officer checklist
    - Scientific references with verifiable links
    """
    st.markdown("### 🚀 EVA Procedures & Checklists")
    
    # EVA scheduling controls
    st.markdown("#### Schedule EVA")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    crew_list = list(engine.crew_members.values())
    crew_options = {c.crew_id: f"{c.name} ({c.role})" for c in crew_list}
    
    with col1:
        eva_crew_1 = st.selectbox(
            "EV1 (Primary)",
            options=list(crew_options.keys()),
            format_func=lambda x: crew_options.get(x, x),
            key="eva_crew_1_select",
        )
    
    with col2:
        remaining_crew = [k for k in crew_options.keys() if k != eva_crew_1]
        eva_crew_2 = st.selectbox(
            "EV2 (Secondary)",
            options=remaining_crew,
            format_func=lambda x: crew_options.get(x, x),
            key="eva_crew_2_select",
        )
    
    with col3:
        if st.button("📋 Generate Full Schedule", key="gen_full_schedule_btn", type="primary"):
            with st.spinner("Generating optimized schedule..."):
                engine.generate_full_daily_schedule(
                    schedule_date=schedule_date,
                    eva_day=True,
                    eva_crew_ids=[eva_crew_1, eva_crew_2],
                )
                st.success("✅ Full daily schedule generated with EVA!")
                st.rerun()
    
    # Sub-tabs for different checklists
    checklist_tab1, checklist_tab2, checklist_tab3, checklist_tab4, checklist_tab5 = st.tabs([
        "☢️ Radiation",
        "⏱️ ISLE Protocol",
        "🎛️ Mission Control",
        "👨‍🚀 EVA Officer",
        "📚 References",
    ])
    
    with checklist_tab1:
        _render_radiation_assessment_panel()
    
    with checklist_tab2:
        _render_isle_protocol_checklist()
    
    with checklist_tab3:
        _render_mcc_eva_checklist()
    
    with checklist_tab4:
        _render_eva_officer_checklist()
    
    with checklist_tab5:
        _render_eva_references()


def _render_space_weather_dashboard(realtime_data: Any) -> None:
    """Render beautiful ECharts dashboard for space weather real-time data.
    
    Displays F10.7 Flux, Active CMEs, Solar Wind parameters, IMF, and Flare Probabilities
    in an attractive, publication-quality visualization.
    
    References:
    - NOAA Space Weather Prediction Center Operational Thresholds
    - SpaceWeatherLive API Documentation
    
    Args:
        realtime_data: Real-time space weather data object
    """
    if render_echarts is None:
        return
    
    # Prepare flare probability data
    flare_probs = []
    flare_labels = []
    flare_colors = []
    
    if realtime_data.c_class_flare_prob:
        flare_probs.append(realtime_data.c_class_flare_prob)
        flare_labels.append("C-Class")
        flare_colors.append("#3498db")  # Blue for minor
    
    if realtime_data.m_class_flare_prob:
        flare_probs.append(realtime_data.m_class_flare_prob)
        flare_labels.append("M-Class")
        flare_colors.append("#f39c12")  # Orange for moderate
    
    if realtime_data.x_class_flare_prob:
        flare_probs.append(realtime_data.x_class_flare_prob)
        flare_labels.append("X-Class")
        flare_colors.append("#e74c3c")  # Red for extreme
    
    # Prepare other metrics for display
    metrics_data = []
    if realtime_data.f107_flux:
        metrics_data.append({
            "name": "F10.7 Flux",
            "value": realtime_data.f107_flux,
            "unit": " sfu",
            "color": "#3498db",
        })
    
    if realtime_data.active_cmes:
        cme_count = len(realtime_data.active_cmes)
        metrics_data.append({
            "name": "Active CMEs",
            "value": cme_count,
            "unit": "",
            "color": "#e74c3c" if cme_count > 3 else "#f39c12" if cme_count > 1 else "#27ae60",
        })
    
    if realtime_data.solar_wind_speed_kms:
        metrics_data.append({
            "name": "Solar Wind\nSpeed",
            "value": realtime_data.solar_wind_speed_kms,
            "unit": " km/s",
            "color": "#9b59b6",
        })
    
    if realtime_data.solar_wind_density_pcc:
        metrics_data.append({
            "name": "Solar Wind\nDensity",
            "value": realtime_data.solar_wind_density_pcc,
            "unit": " p/cm³",
            "color": "#16a085",
        })
    
    if realtime_data.imf_bt_nt:
        metrics_data.append({
            "name": "IMF Bt",
            "value": realtime_data.imf_bt_nt,
            "unit": " nT",
            "color": "#34495e",
        })
    
    if realtime_data.imf_bz_nt:
        metrics_data.append({
            "name": "IMF Bz",
            "value": realtime_data.imf_bz_nt,
            "unit": " nT",
            "color": "#2c3e50",
        })
    
    # Calculate dynamic axis bounds for metrics
    if metrics_data:
        metric_values = [m["value"] for m in metrics_data]
        metric_min, metric_max = _auto_axis_bounds(
            *metric_values,
            padding_pct=0.2,
            min_floor=0.0,
        )
    else:
        metric_min, metric_max = 0.0, 100.0
    
    # Create the dashboard visualization
    option = {
        "title": {
            "text": "Space Weather Real-Time Dashboard",
            "subtext": f"Source: {realtime_data.data_source} | Updated: {realtime_data.fetch_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') if realtime_data.fetch_timestamp else 'Unknown'}",
            "left": "center",
            "textStyle": {"fontSize": 16, "fontWeight": "bold", "color": "#1a1a1a"},
            "subtextStyle": {"fontSize": 11, "color": "#2c3e50"},
        },
        "backgroundColor": "transparent",
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
        },
        "legend": {
            "data": ["Flare Probability"] + ([m["name"].replace("\n", " ") for m in metrics_data] if metrics_data else []),
            "bottom": 5,
            "textStyle": {"fontSize": 10, "color": "#1a1a1a"},
            "type": "scroll",
        },
        "grid": [
            {
                "left": "10%",
                "right": "5%",
                "top": "20%",
                "bottom": "55%",
                "height": "35%",
                "containLabel": True,
            },
            {
                "left": "10%",
                "right": "5%",
                "top": "60%",
                "bottom": "10%",
                "height": "30%",
                "containLabel": True,
            },
        ],
        "xAxis": [
            {
                "type": "category",
                "gridIndex": 0,
                "data": flare_labels,
                "axisLabel": {"color": "#1a1a1a", "fontSize": 11, "fontWeight": "bold"},
                "axisLine": {"lineStyle": {"color": "#2c3e50"}},
            },
            {
                "type": "category",
                "gridIndex": 1,
                "data": [m["name"] for m in metrics_data] if metrics_data else [],
                "axisLabel": {
                    "color": "#1a1a1a",
                    "fontSize": 10,
                    "rotate": 0,
                    "interval": 0,
                },
                "axisLine": {"lineStyle": {"color": "#2c3e50"}},
            },
        ],
        "yAxis": [
            {
                "type": "value",
                "gridIndex": 0,
                "name": "Probability (%)",
                "nameLocation": "middle",
                "nameGap": 40,
                "nameTextStyle": {"fontSize": 11, "fontWeight": "bold", "color": "#1a1a1a"},
                "min": 0,
                "max": 100,
                "axisLabel": {
                    "formatter": "{value}%",
                    "color": "#1a1a1a",
                    "fontSize": 10,
                },
                "splitLine": {"show": True, "lineStyle": {"color": "#ecf0f1", "type": "dashed"}},
                "axisLine": {"lineStyle": {"color": "#2c3e50"}},
            },
            {
                "type": "value",
                "gridIndex": 1,
                "name": "Value",
                "nameLocation": "middle",
                "nameGap": 40,
                "nameTextStyle": {"fontSize": 11, "fontWeight": "bold", "color": "#1a1a1a"},
                "min": metric_min,
                "max": metric_max,
                "axisLabel": {
                    "formatter": "{value}",
                    "color": "#1a1a1a",
                    "fontSize": 10,
                },
                "splitLine": {"show": True, "lineStyle": {"color": "#ecf0f1", "type": "dashed"}},
                "axisLine": {"lineStyle": {"color": "#2c3e50"}},
            },
        ],
        "series": [
            # Flare Probabilities Bar Chart
            {
                "name": "Flare Probability",
                "type": "bar",
                "xAxisIndex": 0,
                "yAxisIndex": 0,
                "data": [
                    {
                        "value": prob,
                        "itemStyle": {"color": color},
                        "label": {
                            "show": True,
                            "position": "top",
                            "formatter": f"{prob:.0f}%",
                            "color": "#1a1a1a",
                            "fontSize": 11,
                            "fontWeight": "bold",
                        },
                    }
                    for prob, color in zip(flare_probs, flare_colors)
                ] if flare_probs else [],
            },
            # Other Metrics Bar Chart
            {
                "name": "Space Weather Metrics",
                "type": "bar",
                "xAxisIndex": 1,
                "yAxisIndex": 1,
                "data": [
                    {
                        "value": m["value"],
                        "itemStyle": {"color": m["color"]},
                        "label": {
                            "show": True,
                            "position": "top",
                            "formatter": (
                                f"{m['value']:.1f}{m['unit']}" if m["unit"] 
                                else f"{m['value']:.0f}"
                            ),
                            "color": "#1a1a1a",
                            "fontSize": 10,
                            "fontWeight": "bold",
                        },
                    }
                    for m in metrics_data
                ] if metrics_data else [],
            },
        ],
        "aria": {
            "enabled": True,
            "label": {
                "description": "Space Weather Real-Time Dashboard showing flare probabilities and space environment metrics.",
            },
        },
    }
    
    render_echarts(option, height_px=500)
    
    # Caption with interpretation
    st.caption(f"""
    **What you're seeing:** Real-time space weather dashboard showing solar flare probabilities and key space 
    environment parameters. **Flare Probabilities** indicate the likelihood of C-Class (minor), M-Class (moderate), 
    and X-Class (extreme) solar flares occurring in the next 24-48 hours. **F10.7 Flux** measures solar radio 
    emission at 10.7 cm wavelength, indicating solar activity levels. **Active CMEs** shows the number of 
    Coronal Mass Ejections currently propagating through space. **Solar Wind** parameters (speed and density) 
    and **Interplanetary Magnetic Field (IMF)** components (Bt, Bz) affect geomagnetic activity and radiation 
    environment. **Sources:** NOAA Space Weather Prediction Center, SpaceWeatherLive API, NASA Space Radiation 
    Analysis Group.
    """)


def _render_eva_radiation_metrics_plot(
    realtime_data: Any,
    selected_env: Any,
    eva_duration_hours: float,
    s_scale: int,
    g_scale: int,
) -> None:
    """Render comprehensive EVA radiation metrics plot for Mission Control.
    
    Displays the most critical radiation metrics used by Mission Control for EVA
    decision-making: Proton Flux (S-scale zones), Kp Index (G-scale zones), and
    estimated EVA dose rate with threshold references.
    
    References:
    - NOAA Space Weather Scales: S-Scale (Solar Radiation Storms) and G-Scale (Geomagnetic Storms)
    - NASA-STD-3001 Vol 1 Rev B (2022). Crew Health Standard.
    - Space Weather Prediction Center (SWPC) Operational Thresholds
    
    Args:
        realtime_data: Real-time space weather data object
        selected_env: Selected radiation environment
        eva_duration_hours: Planned EVA duration
        s_scale: NOAA S-scale value (0-5)
        g_scale: NOAA G-scale value (0-5)
    """
    if render_echarts is None:
        return
    
    # Extract current values
    proton_flux = realtime_data.proton_flux_pfu if realtime_data.proton_flux_pfu else 0.1
    kp_index = realtime_data.kp_index if realtime_data.kp_index else 2.0
    
    # Calculate estimated EVA dose rate
    from radiation_exposure import DOSE_RATE_DATABASE, get_environment_display_name
    dose_rate = DOSE_RATE_DATABASE.get(selected_env)
    if dose_rate:
        eva_rate_hr = (dose_rate.nominal_msv_per_day * dose_rate.eva_multiplier) / 24.0
        # Adjust for space weather
        if s_scale >= 3:
            eva_rate_hr *= (2.0 + s_scale)
        elif s_scale >= 1:
            eva_rate_hr *= (1.5 + 0.3 * s_scale)
    else:
        eva_rate_hr = 0.5  # Default LEO estimate
    
    # S-Scale thresholds (Proton Flux >10 MeV, pfu)
    s_scale_thresholds = [0.1, 10, 100, 1000, 10000, 100000]  # S0-S5
    s_scale_labels = ["S0", "S1", "S2", "S3", "S4", "S5"]
    s_scale_colors = ["#27ae60", "#3498db", "#f39c12", "#fd7e14", "#e74c3c", "#8b0000"]
    
    # G-Scale thresholds (Kp index)
    g_scale_thresholds = [0, 5, 6, 7, 8, 9]  # G0-G5
    g_scale_labels = ["G0", "G1", "G2", "G3", "G4", "G5"]
    g_scale_colors = ["#27ae60", "#3498db", "#f39c12", "#fd7e14", "#e74c3c", "#8b0000"]
    
    # EVA dose rate thresholds (mSv/hr)
    eva_normal_max = 0.8  # Normal LEO EVA
    eva_caution = 2.0      # Caution threshold
    eva_warning = 5.0      # Warning threshold
    eva_no_go = 10.0       # NO-GO threshold
    
    # Calculate dynamic axis bounds
    # Proton flux axis (log scale)
    proton_min, proton_max = _auto_axis_bounds(
        proton_flux,
        *s_scale_thresholds[1:],
        padding_pct=0.2,
        min_floor=0.01,
    )
    # Use log scale, so convert to linear for display
    proton_max = max(proton_max, proton_flux * 2, 1000)
    
    # Kp index axis
    kp_min, kp_max = _auto_axis_bounds(
        kp_index,
        *g_scale_thresholds,
        padding_pct=0.15,
        min_floor=0.0,
        max_ceil=9.0,
    )
    
    # EVA dose rate axis
    eva_min, eva_max = _auto_axis_bounds(
        eva_rate_hr,
        eva_normal_max,
        eva_caution,
        eva_warning,
        eva_no_go,
        padding_pct=0.2,
        min_floor=0.0,
    )
    
    # Build S-scale zones (stacked areas for visual reference)
    s_zone_data = []
    for i in range(len(s_scale_thresholds) - 1):
        zone_min = s_scale_thresholds[i]
        zone_max = s_scale_thresholds[i + 1]
        # Create a small range for visualization
        s_zone_data.append({
            "name": s_scale_labels[i],
            "value": [zone_min, zone_max],
            "itemStyle": {"color": s_scale_colors[i] + "40"},  # 40 = 25% opacity
        })
    
    # Build G-scale zones
    g_zone_data = []
    for i in range(len(g_scale_thresholds) - 1):
        zone_min = g_scale_thresholds[i]
        zone_max = g_scale_thresholds[i + 1]
        g_zone_data.append({
            "name": g_scale_labels[i],
            "value": [zone_min, zone_max],
            "itemStyle": {"color": g_scale_colors[i] + "40"},
        })
    
    # Determine current S-scale and G-scale levels
    current_s_scale = 0
    for i, threshold in enumerate(s_scale_thresholds[1:], start=1):
        if proton_flux >= threshold:
            current_s_scale = i
        else:
            break
    
    current_g_scale = 0
    for i, threshold in enumerate(g_scale_thresholds[1:], start=1):
        if kp_index >= threshold:
            current_g_scale = i
        else:
            break
    
    # Create a multi-metric bar chart with proper scaling
    # Use separate x-axis scales for each metric by using a grouped approach
    # For Mission Control, show current values with threshold reference lines
    
    # Normalize values to percentage of critical threshold for visual comparison
    # Proton flux: normalize to S3 threshold (1000 pfu) as critical
    proton_normalized = min((proton_flux / 1000.0) * 100, 200)  # Cap at 200% for display
    
    # Kp index: normalize to G3 threshold (7.0) as critical  
    kp_normalized = min((kp_index / 7.0) * 100, 150)  # Cap at 150% for display
    
    # EVA dose rate: normalize to NO-GO threshold (10.0 mSv/hr) as critical
    eva_normalized = min((eva_rate_hr / eva_no_go) * 100, 150)  # Cap at 150% for display
    
    option = {
        "title": {
            "text": "EVA Radiation Metrics Dashboard",
            "subtext": f"Real-time monitoring | Environment: {get_environment_display_name(selected_env)} | EVA Duration: {eva_duration_hours:.1f} hr",
            "left": "center",
            "textStyle": {"fontSize": 16, "fontWeight": "bold", "color": "#1a1a1a"},
            "subtextStyle": {"fontSize": 11, "color": "#2c3e50"},
        },
        "backgroundColor": "transparent",
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": (
                f"function(params) {{"
                f"  let result = '';"
                f"  params.forEach(function(item) {{"
                f"    if (item.seriesName === 'Proton Flux') {{"
                f"      result += item.marker + ' Proton Flux (>10 MeV): ' + {proton_flux:.2f} + ' pfu (S{current_s_scale})<br/>';"
                f"    }} else if (item.seriesName === 'Kp Index') {{"
                f"      result += item.marker + ' Kp Index: ' + {kp_index:.1f} + ' (G{current_g_scale})<br/>';"
                f"    }} else if (item.seriesName === 'EVA Dose Rate') {{"
                f"      result += item.marker + ' EVA Dose Rate: ' + {eva_rate_hr:.3f} + ' mSv/hr<br/>';"
                f"    }}"
                f"  }});"
                f"  return result;"
                f"}}"
            ),
        },
        "legend": {
            "data": ["Proton Flux (>10 MeV)", "Kp Index", "EVA Dose Rate", "Critical Threshold"],
            "bottom": 5,
            "textStyle": {"fontSize": 10, "color": "#1a1a1a"},
        },
        "grid": {
            "left": "15%",
            "right": "10%",
            "top": "20%",
            "bottom": "20%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "value",
            "name": "Normalized Value (% of Critical Threshold)",
            "nameLocation": "middle",
            "nameGap": 30,
            "nameTextStyle": {"fontSize": 11, "fontWeight": "bold", "color": "#1a1a1a"},
            "min": 0,
            "max": 200,
            "axisLabel": {
                "formatter": "{value}%",
                "color": "#1a1a1a",
                "fontSize": 10,
            },
            "axisLine": {"lineStyle": {"color": "#2c3e50"}},
            "splitLine": {"show": True, "lineStyle": {"color": "#ecf0f1", "type": "dashed"}},
        },
        "yAxis": {
            "type": "category",
            "data": [
                f"Proton Flux (>10 MeV, pfu)<br/><span style='font-size:10px;color:#666;'>Current: {proton_flux:.2f} pfu | S{current_s_scale}</span>",
                f"Kp Index<br/><span style='font-size:10px;color:#666;'>Current: {kp_index:.1f} | G{current_g_scale}</span>",
                f"EVA Dose Rate (mSv/hr)<br/><span style='font-size:10px;color:#666;'>Current: {eva_rate_hr:.3f} mSv/hr</span>",
            ],
            "axisLabel": {
                "color": "#1a1a1a",
                "fontSize": 11,
                "fontWeight": "bold",
                "rich": {
                    "normal": {"fontSize": 11, "fontWeight": "bold", "color": "#1a1a1a"},
                    "sub": {"fontSize": 10, "color": "#666"},
                },
            },
            "axisLine": {"lineStyle": {"color": "#2c3e50"}},
        },
        "series": [
            # Proton Flux bar
            {
                "name": "Proton Flux (>10 MeV)",
                "type": "bar",
                "data": [proton_normalized, None, None],
                "itemStyle": {
                    "color": s_scale_colors[min(current_s_scale, 5)],
                },
                "label": {
                    "show": True,
                    "position": "right",
                    "formatter": f"{proton_normalized:.1f}% ({proton_flux:.2f} pfu, S{current_s_scale})",
                    "color": "#1a1a1a",
                    "fontSize": 10,
                },
            },
            # Kp Index bar
            {
                "name": "Kp Index",
                "type": "bar",
                "data": [None, kp_normalized, None],
                "itemStyle": {
                    "color": g_scale_colors[min(current_g_scale, 5)],
                },
                "label": {
                    "show": True,
                    "position": "right",
                    "formatter": f"{kp_normalized:.1f}% ({kp_index:.1f}, G{current_g_scale})",
                    "color": "#1a1a1a",
                    "fontSize": 10,
                },
            },
            # EVA Dose Rate bar
            {
                "name": "EVA Dose Rate",
                "type": "bar",
                "data": [None, None, eva_normalized],
                "itemStyle": {
                    "color": (
                        "#e74c3c" if eva_rate_hr >= eva_no_go 
                        else "#fd7e14" if eva_rate_hr >= eva_warning 
                        else "#f39c12" if eva_rate_hr >= eva_caution 
                        else "#27ae60"
                    ),
                },
                "label": {
                    "show": True,
                    "position": "right",
                    "formatter": f"{eva_normalized:.1f}% ({eva_rate_hr:.3f} mSv/hr)",
                    "color": "#1a1a1a",
                    "fontSize": 10,
                },
            },
            # Critical threshold reference line (100%)
            {
                "name": "Critical Threshold",
                "type": "line",
                "data": [100, 100, 100],
                "lineStyle": {"type": "dashed", "color": "#e74c3c", "width": 2},
                "markLine": {
                    "silent": True,
                    "label": {
                        "show": True,
                        "formatter": "Critical (100%)",
                        "position": "end",
                        "color": "#e74c3c",
                        "fontSize": 9,
                        "fontWeight": "bold",
                    },
                    "lineStyle": {"type": "dashed", "color": "#e74c3c", "width": 2},
                    "data": [{"xAxis": 100}],
                },
            },
        ],
        "aria": {
            "enabled": True,
            "label": {
                "description": (
                    f"EVA Radiation Metrics Dashboard. "
                    f"Proton Flux: {proton_flux:.2f} pfu (S{current_s_scale} scale). "
                    f"Kp Index: {kp_index:.1f} (G{current_g_scale} scale). "
                    f"EVA Dose Rate: {eva_rate_hr:.3f} mSv/hr."
                ),
            },
        },
    }
    
    render_echarts(option, height_px=380)
    
    # Caption with interpretation
    st.caption(f"""
    **What you're seeing:** Real-time EVA radiation metrics dashboard showing the three most critical parameters 
    used by Mission Control for EVA decision-making. Values are normalized to percentage of critical threshold 
    for visual comparison. **Proton Flux (>10 MeV)** indicates solar particle event activity (S{current_s_scale} scale: 
    {s_scale_labels[min(current_s_scale, 5)]}). **Kp Index** reflects geomagnetic storm conditions (G{current_g_scale} scale: 
    {g_scale_labels[min(current_g_scale, 5)]}). **EVA Dose Rate** shows estimated radiation exposure during the planned EVA. 
    The red dashed line at 100% indicates the critical threshold for each metric. **Sources:** NOAA Space Weather 
    Prediction Center, NASA-STD-3001 Vol 1 Rev B (2022), Space Weather Prediction Center Operational Thresholds.
    """)


def _render_radiation_assessment_panel() -> None:
    """Render radiation environment assessment for EVA GO/NO-GO decision.
    
    Displays space weather data, radiation risk level, and recommendations
    based on real-time NOAA/NASA data and NASA-STD-3001 radiation protection requirements.
    
    References:
        - NASA-STD-3001 Vol 1 Rev B (2022): Radiation Protection
        - NOAA SWPC: https://www.swpc.noaa.gov/
        - NASA SRAG: https://srag.jsc.nasa.gov/
        - SpaceWeatherLive: https://www.spaceweatherlive.com/
    """
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #4a1942 0%, #6b2960 50%, #8b3a7a 100%);
        padding: 16px 20px;
        border-radius: 10px;
        margin-bottom: 16px;
        border-left: 4px solid #e879f9;
    ">
        <h4 style="margin: 0 0 8px 0; color: #fff;">
            ☢️ Space Radiation Assessment for EVA
        </h4>
        <p style="margin: 0; color: #f0abfc; font-size: 0.9em;">
            Real-time radiation environment evaluation per NASA-STD-3001 requirements<br/>
            <em>Data sources: NOAA SWPC, SpaceWeatherLive, NASA SRAG</em>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Import required modules
    try:
        from radiation_exposure import (
            RadiationEnvironment,
            assess_eva_radiation_risk,
            fetch_realtime_space_weather,
            get_environment_display_name,
            EVARadiationStatus,
        )
        RADIATION_AVAILABLE = True
    except ImportError:
        RADIATION_AVAILABLE = False
        st.error("Radiation exposure module not available.")
        return
    
    # Mission environment selection
    st.markdown("##### 🌍 Mission Environment")
    
    env_options = [
        (RadiationEnvironment.LEO_ISS, "Low Earth Orbit (ISS)"),
        (RadiationEnvironment.TRANSLUNAR_INJECTION, "Translunar Injection (TLI)"),
        (RadiationEnvironment.LUNAR_GATEWAY, "Lunar Gateway"),
        (RadiationEnvironment.LUNAR_SURFACE_NOMINAL, "Lunar Surface"),
        (RadiationEnvironment.TRANS_MARTIAN_INJECTION, "Trans-Martian Injection (TMI)"),
        (RadiationEnvironment.MARS_ORBIT, "Martian Orbit"),
        (RadiationEnvironment.MARS_SURFACE, "Martian Surface"),
    ]
    
    env_labels = [e[1] for e in env_options]
    selected_env_idx = st.selectbox(
        "Mission Environment",
        options=range(len(env_options)),
        format_func=lambda x: env_labels[x],
        index=0,
        key="eva_radiation_env",
        help="Select the current mission environment for accurate dose rate calculation",
    )
    selected_env = env_options[selected_env_idx][0]
    
    # Real-time data fetching
    st.markdown("---")
    st.markdown("##### 📡 Real-Time Space Weather Data")
    
    col_fetch1, col_fetch2 = st.columns([3, 1])
    
    with col_fetch1:
        auto_fetch = st.checkbox(
            "🛰️ Fetch Real-Time Data",
            value=True,
            key="eva_radiation_auto_fetch",
            help="Automatically fetch current space weather conditions from NOAA SWPC and SpaceWeatherLive",
        )
    
    with col_fetch2:
        if st.button("🔄 Refresh", key="eva_radiation_refresh"):
            st.cache_data.clear()
            st.rerun()
    
    # Fetch real-time data
    realtime_data = None
    if auto_fetch:
        with st.spinner("Fetching real-time space weather data..."):
            try:
                realtime_data = fetch_realtime_space_weather(
                    environment=selected_env,
                    use_noaa=True,
                    use_spaceweatherlive=True,
                    timeout_seconds=10.0,
                )
            except Exception as e:
                st.warning(f"⚠️ Real-time data fetch failed: {str(e)}. Using manual input.")
                realtime_data = None
    
    # Space weather input controls (with real-time defaults)
    st.markdown("##### 📊 Space Weather Parameters")
    
    col1, col2, col3 = st.columns(3)
    
    # Proton flux
    default_proton = realtime_data.proton_flux_pfu if realtime_data and realtime_data.proton_flux_pfu else 1.0
    with col1:
        proton_flux = st.number_input(
            "Proton Flux (>10 MeV pfu)",
            min_value=0.1,
            max_value=10000.0,
            value=float(default_proton),
            step=0.5,
            help="Solar proton flux in particle flux units. Normal: <1, Alert: >10, Warning: >100, Storm: >1000",
            key="radiation_proton_flux",
        )
        if realtime_data and realtime_data.proton_flux_pfu:
            st.caption(f"🛰️ Real-time: {realtime_data.proton_flux_pfu:.1f} pfu ({realtime_data.data_source})")
        else:
            st.caption("📝 Manual input")
    
    # Kp index
    default_kp = realtime_data.kp_index if realtime_data and realtime_data.kp_index else 2.0
    with col2:
        kp_index = st.slider(
            "Kp Index (Geomagnetic)",
            min_value=0.0,
            max_value=9.0,
            value=float(default_kp),
            step=0.5,
            help="Planetary K-index. Quiet: 0-2, Unsettled: 3-4, Storm: 5+",
            key="radiation_kp_index",
        )
        if realtime_data and realtime_data.kp_index:
            st.caption(f"🛰️ Real-time: {realtime_data.kp_index:.1f} ({realtime_data.data_source})")
        else:
            st.caption("📝 Manual input")
    
    # Solar cycle phase (not real-time, but can be inferred from sunspot number)
    with col3:
        solar_phase = st.selectbox(
            "Solar Cycle Phase",
            options=["minimum", "ascending", "maximum", "descending"],
            index=1,  # ascending (current ~2024-2025)
            help="Solar cycle phase affects GCR levels. Maximum = lower GCR, Minimum = higher GCR",
            key="radiation_solar_phase",
        )
        if realtime_data and realtime_data.sunspot_number:
            # Infer solar cycle phase from sunspot number
            if realtime_data.sunspot_number < 20:
                inferred_phase = "minimum"
            elif realtime_data.sunspot_number < 100:
                inferred_phase = "ascending"
            elif realtime_data.sunspot_number > 150:
                inferred_phase = "maximum"
            else:
                inferred_phase = "descending"
            st.caption(f"🛰️ Sunspot #: {realtime_data.sunspot_number} (suggests {inferred_phase})")
        else:
            st.caption("📝 Manual input")
    
    # Calculate S-scale and G-scale from real-time data or manual input
    # S-scale from proton flux
    if realtime_data and realtime_data.s_scale > 0:
        default_s_scale = realtime_data.s_scale
    else:
        # Calculate from proton flux
        if proton_flux >= 10000:
            default_s_scale = 5
        elif proton_flux >= 1000:
            default_s_scale = 4
        elif proton_flux >= 100:
            default_s_scale = 3
        elif proton_flux >= 10:
            default_s_scale = 2
        elif proton_flux >= 1:
            default_s_scale = 1
        else:
            default_s_scale = 0
    
    # G-scale from Kp
    if realtime_data and realtime_data.g_scale > 0:
        default_g_scale = realtime_data.g_scale
    else:
        # Calculate from Kp
        if kp_index >= 9.0:
            default_g_scale = 5
        elif kp_index >= 8.0:
            default_g_scale = 4
        elif kp_index >= 7.0:
            default_g_scale = 3
        elif kp_index >= 6.0:
            default_g_scale = 2
        elif kp_index >= 5.0:
            default_g_scale = 1
        else:
            default_g_scale = 0
    
    # Allow manual override
    st.markdown("---")
    st.markdown("##### 🎯 NOAA Space Weather Scales")
    
    col_s1, col_s2 = st.columns(2)
    
    with col_s1:
        s_scale = st.selectbox(
            "NOAA S-Scale (Radiation Storm)",
            options=[0, 1, 2, 3, 4, 5],
            index=default_s_scale,
            format_func=lambda x: f"S{x}" + (" - None" if x == 0 else f" - {['', 'Minor', 'Moderate', 'Strong', 'Severe', 'Extreme'][x]}"),
            key="eva_radiation_s_scale",
            help="Radiation storm scale. Can override real-time calculation.",
        )
        if realtime_data and realtime_data.s_scale > 0 and s_scale != realtime_data.s_scale:
            st.caption(f"⚠️ Override: Real-time was S{realtime_data.s_scale}")
        elif realtime_data and realtime_data.s_scale > 0:
            st.caption(f"🛰️ Real-time: S{realtime_data.s_scale} ({realtime_data.data_source})")
        else:
            st.caption(f"📝 Calculated from proton flux: S{default_s_scale}")
    
    with col_s2:
        g_scale = st.selectbox(
            "NOAA G-Scale (Geomagnetic Storm)",
            options=[0, 1, 2, 3, 4, 5],
            index=default_g_scale,
            format_func=lambda x: f"G{x}" + (" - None" if x == 0 else f" - {['', 'Minor', 'Moderate', 'Strong', 'Severe', 'Extreme'][x]}"),
            key="eva_radiation_g_scale",
            help="Geomagnetic storm scale. Can override real-time calculation.",
        )
        if realtime_data and realtime_data.g_scale > 0 and g_scale != realtime_data.g_scale:
            st.caption(f"⚠️ Override: Real-time was G{realtime_data.g_scale}")
        elif realtime_data and realtime_data.g_scale > 0:
            st.caption(f"🛰️ Real-time: G{realtime_data.g_scale} ({realtime_data.data_source})")
        else:
            st.caption(f"📝 Calculated from Kp: G{default_g_scale}")
    
    # Data source indicator
    if realtime_data and realtime_data.is_real_time:
        kp_display = f"{realtime_data.kp_index:.1f}" if realtime_data.kp_index else "N/A"
        proton_display = f"{realtime_data.proton_flux_pfu:.1f} pfu" if realtime_data.proton_flux_pfu else "N/A"
        timestamp_display = realtime_data.fetch_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') if realtime_data.fetch_timestamp else 'Unknown'
        
        st.info(f"""
        ✅ **Real-Time Data Active**
        - Source: {realtime_data.data_source}
        - Fetched: {timestamp_display}
        - Kp: {kp_display} | Proton Flux: {proton_display}
        """)
    else:
        st.warning("⚠️ **Manual Input Mode** - Using manually entered values. Enable real-time fetch for live data.")
    
    # EVA duration input
    st.markdown("---")
    st.markdown("##### ⏱️ EVA Parameters")
    
    col_eva1, col_eva2 = st.columns(2)
    
    with col_eva1:
        eva_duration = st.number_input(
            "Planned EVA Duration (hours)",
            min_value=0.5,
            max_value=12.0,
            value=6.0,
            step=0.5,
            key="eva_radiation_duration",
        )
    
    with col_eva2:
        cumulative_dose = st.number_input(
            "Cumulative Career Dose (mSv)",
            min_value=0.0,
            max_value=1000.0,
            value=0.0,
            step=10.0,
            key="eva_radiation_cumulative",
            help="Current cumulative career radiation dose",
        )
    
    # Perform radiation assessment using assess_eva_radiation_risk (more comprehensive)
    assessment = assess_eva_radiation_risk(
        cumulative_dose_msv=cumulative_dose,
        environment=selected_env,
        eva_duration_hours=eva_duration,
        space_weather_s_scale=s_scale,
        space_weather_g_scale=g_scale,
    )
    
    # Display EVA Go/No-Go status
    status_colors = {
        EVARadiationStatus.GO: ("#28a745", "#155724", "✅ GO"),
        EVARadiationStatus.GO_WITH_MONITORING: ("#ffc107", "#856404", "⚠️ GO WITH MONITORING"),
        EVARadiationStatus.CAUTION: ("#fd7e14", "#7c2d12", "🔶 CAUTION"),
        EVARadiationStatus.NO_GO: ("#dc3545", "#721c24", "🚫 NO-GO"),
    }
    
    color, bg_dark, label = status_colors.get(
        assessment.status,
        ("#6c757d", "#343a40", "UNKNOWN"),
    )
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {bg_dark} 0%, {color}30 100%);
        border: 2px solid {color};
        border-radius: 12px;
        padding: 20px;
        margin: 16px 0;
        text-align: center;
    ">
        <div style="font-size: 1.8em; font-weight: bold; color: {color}; margin-bottom: 8px;">
            {label}
        </div>
        <div style="color: #f0f0f0; font-size: 1.1em; font-weight: 500;">
            {assessment.rationale}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Calculate EVA dose rate
        from radiation_exposure import DOSE_RATE_DATABASE
        dose_rate = DOSE_RATE_DATABASE.get(selected_env)
        if dose_rate:
            eva_rate_hr = (dose_rate.nominal_msv_per_day * dose_rate.eva_multiplier) / 24.0
            # Adjust for space weather
            if s_scale >= 3:
                eva_rate_hr *= (2.0 + s_scale)
            elif s_scale >= 1:
                eva_rate_hr *= (1.5 + 0.3 * s_scale)
        else:
            eva_rate_hr = 0.0
        
        st.metric(
            "Est. EVA Dose Rate",
            f"{eva_rate_hr:.3f} mSv/hr",
            delta=None,
            help="Estimated radiation dose rate during EVA in this environment",
        )
    
    with col2:
        projected_dose = assessment.cumulative_dose_msv - cumulative_dose
        st.metric(
            "Projected EVA Dose",
            f"{projected_dose:.2f} mSv",
            delta=f"{assessment.career_pct_used:.1f}% of limit",
            help="Projected dose from this EVA",
        )
    
    with col3:
        st.metric(
            "Career Dose Used",
            f"{assessment.career_pct_used:.1f}%",
            delta=f"{assessment.remaining_career_msv:.1f} mSv remaining",
            help="Percentage of career limit used after this EVA",
        )
    
    with col4:
        space_alert_display = assessment.space_weather_alert if assessment.space_weather_alert != "None" else "None"
        st.metric(
            "Space Weather",
            space_alert_display,
            delta="Active" if s_scale > 0 or g_scale > 0 else None,
            delta_color="inverse" if s_scale > 0 or g_scale > 0 else "normal",
        )
    
    # Recommendations
    st.markdown("---")
    st.markdown("##### 📋 Recommendations")
    
    if assessment.recommendations:
        for rec in assessment.recommendations:
            st.markdown(f"• {rec}")
    else:
        st.info("No specific recommendations. Standard EVA protocols apply.")
    
    # Additional real-time data display
    if realtime_data and realtime_data.is_real_time:
        st.markdown("---")
        st.markdown("##### 📡 Additional Real-Time Data")
        
        # Render comprehensive radiation metrics plot
        if render_echarts is not None:
            _render_eva_radiation_metrics_plot(
                realtime_data=realtime_data,
                selected_env=selected_env,
                eva_duration_hours=eva_duration,
                s_scale=s_scale,
                g_scale=g_scale,
            )
        
        # Render beautiful space weather dashboard
        if render_echarts is not None:
            _render_space_weather_dashboard(realtime_data)
    
    # Dose limits reference
    with st.expander("📊 NASA Radiation Dose Limits Reference", expanded=False):
        st.markdown(f"""
        | Limit Type | Value | Notes |
        |----|----|-----|
        | **Career Limit** | {NASA_CAREER_DOSE_LIMIT_MSV:.0f} mSv | NASA-STD-3001 Vol 1 Rev B (2022) |
        | **30-Day BFO** | 250 mGy-Eq | Blood-forming organs |
        | **Annual Limit** | 50 mSv | Occupational standard |
        | **EVA Typical** | 0.3-0.8 mSv/hr | LEO, normal conditions |
        | **SPE Alert** | >{SPE_ALERT_THRESHOLD_PFU:.0f} pfu | Enhanced proton activity |
        | **SPE Warning** | >{SPE_WARNING_THRESHOLD_PFU:.0f} pfu | Significant event |
        
        **Sources:**
        - [NASA-STD-3001 Radiation Technical Brief](https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf)
        - [NOAA Space Weather Prediction Center](https://www.swpc.noaa.gov/)
        - [NASA Space Radiation Analysis Group](https://srag.jsc.nasa.gov/)
        """)
    
    # ALARA principle note
    st.info("""
    **ALARA Principle**: All radiation exposures should be kept As Low As Reasonably Achievable. 
    Mission planners should schedule EVAs during periods of low solar activity and avoid 
    operations during Solar Particle Events (SPEs).
    """)


def _render_isle_protocol_checklist() -> None:
    """Render the ISLE prebreathe protocol timeline with checkboxes."""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1a472a 0%, #2d5a3d 100%);
        padding: 16px 20px;
        border-radius: 10px;
        margin-bottom: 16px;
        border-left: 4px solid #4ade80;
    ">
        <h4 style="margin: 0 0 8px 0; color: #fff;">
            ⏱️ In-Suit Light Exercise (ISLE) Prebreathe Protocol
        </h4>
        <p style="margin: 0; color: #a7f3d0; font-size: 0.9em;">
            Total duration: ~100 minutes | Saves 2.5 kg O₂/EVA vs previous protocols<br/>
            <em>Reference: NASA NTRS 20110007150</em>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if advanced features available
    if not ADVANCED_FEATURES_AVAILABLE:
        st.warning("EVA checklist data not available")
        return
    
    # Initialize session state for checkboxes
    if "isle_checklist_state" not in st.session_state:
        st.session_state["isle_checklist_state"] = {}
    
    total_time = 0
    for item in ISLE_PROTOCOL_TIMELINE:
        total_time += item.duration_min
        
        # Checkbox for each item
        col1, col2, col3 = st.columns([0.5, 3, 1])
        
        with col1:
            checked = st.checkbox(
                "Complete",
                key=f"isle_{item.id}",
                value=st.session_state["isle_checklist_state"].get(item.id, False),
                label_visibility="collapsed",
            )
            st.session_state["isle_checklist_state"][item.id] = checked
        
        with col2:
            # Color based on critical status
            bg_color = "rgba(239, 68, 68, 0.15)" if item.critical else "rgba(59, 130, 246, 0.1)"
            border_color = "#ef4444" if item.critical else "#3b82f6"
            text_decoration = "line-through" if checked else "none"
            opacity = "0.6" if checked else "1"
            
            critical_badge = '<span style="background:#ef4444;color:#fff;padding:2px 6px;border-radius:4px;font-size:0.75em;margin-left:8px;">CRITICAL</span>' if item.critical else ''
            verify_badge = '<span style="background:#f59e0b;color:#fff;padding:2px 6px;border-radius:4px;font-size:0.75em;margin-left:8px;">VERIFY</span>' if item.verification_required else ''
            
            st.markdown(f"""
            <div style="
                background: {bg_color};
                border-left: 3px solid {border_color};
                padding: 10px 14px;
                border-radius: 0 8px 8px 0;
                opacity: {opacity};
            ">
                <div style="text-decoration: {text_decoration}; font-weight: 500;">
                    {item.description} {critical_badge} {verify_badge}
                </div>
                <div style="color: #888; font-size: 0.85em; margin-top: 4px;">
                    <strong>Responsible:</strong> {item.responsible} | 
                    <strong>Duration:</strong> {item.duration_min} min
                    {f' | <em>{item.notes}</em>' if item.notes else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"**T+{total_time} min**")
    
    # Progress indicator
    completed = sum(1 for item in ISLE_PROTOCOL_TIMELINE if st.session_state["isle_checklist_state"].get(item.id, False))
    total = len(ISLE_PROTOCOL_TIMELINE)
    progress = completed / total if total > 0 else 0
    
    st.progress(progress, text=f"Protocol Progress: {completed}/{total} steps completed")


def _render_mcc_eva_checklist() -> None:
    """Render Mission Control Center EVA checklist."""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1e3a5f 0%, #2d4a6f 100%);
        padding: 16px 20px;
        border-radius: 10px;
        margin-bottom: 16px;
        border-left: 4px solid #60a5fa;
    ">
        <h4 style="margin: 0 0 8px 0; color: #fff;">
            🎛️ Mission Control Center EVA Checklist
        </h4>
        <p style="margin: 0; color: #bfdbfe; font-size: 0.9em;">
            Flight Director and Flight Surgeon responsibilities<br/>
            <em>Based on NASA ISS EVA Operations procedures</em>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if not ADVANCED_FEATURES_AVAILABLE:
        st.warning("EVA checklist data not available")
        return
    
    # Initialize session state
    if "mcc_checklist_state" not in st.session_state:
        st.session_state["mcc_checklist_state"] = {}
    
    # Group by phase
    phases = {
        "T-24 Hours": ["mcc_01", "mcc_02", "mcc_03", "mcc_04"],
        "T-2 Hours (GO/NO-GO)": ["mcc_05", "mcc_06", "mcc_07"],
        "During EVA": ["mcc_08", "mcc_09", "mcc_10"],
    }
    
    for phase_name, item_ids in phases.items():
        with st.expander(f"📋 {phase_name}", expanded=True):
            for item in MCC_EVA_CHECKLIST:
                if item.id not in item_ids:
                    continue
                
                col1, col2 = st.columns([0.5, 5])
                
                with col1:
                    checked = st.checkbox(
                        "Complete",
                        key=f"mcc_{item.id}",
                        value=st.session_state["mcc_checklist_state"].get(item.id, False),
                        label_visibility="collapsed",
                    )
                    st.session_state["mcc_checklist_state"][item.id] = checked
                
                with col2:
                    opacity = "0.5" if checked else "1"
                    text_decoration = "line-through" if checked else "none"
                    
                    critical_badge = '🔴' if item.critical else ''
                    verify_badge = '✅' if item.verification_required else ''
                    
                    st.markdown(f"""
                    <div style="opacity: {opacity}; text-decoration: {text_decoration}; padding: 8px 0;">
                        {critical_badge} {verify_badge} <strong>{item.description}</strong>
                        <br/><span style="color: #888; font-size: 0.85em;">
                        Duration: {item.duration_min} min {f'| {item.notes}' if item.notes else ''}
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Progress
    completed = sum(1 for item in MCC_EVA_CHECKLIST if st.session_state["mcc_checklist_state"].get(item.id, False))
    total = len(MCC_EVA_CHECKLIST)
    st.progress(completed / total if total > 0 else 0, text=f"MCC Checklist: {completed}/{total}")


def _render_eva_officer_checklist() -> None:
    """Render EVA Officer detailed procedures checklist."""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #4a1d6e 0%, #5a2d7e 100%);
        padding: 16px 20px;
        border-radius: 10px;
        margin-bottom: 16px;
        border-left: 4px solid #c084fc;
    ">
        <h4 style="margin: 0 0 8px 0; color: #fff;">
            👨‍🚀 EVA Officer Procedures Checklist
        </h4>
        <p style="margin: 0; color: #e9d5ff; font-size: 0.9em;">
            Detailed EMU and airlock operations procedures<br/>
            <em>Based on NASA NTRS 20140009556 & EMU Data Book</em>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if not ADVANCED_FEATURES_AVAILABLE:
        st.warning("EVA checklist data not available")
        return
    
    # Initialize session state
    if "evo_checklist_state" not in st.session_state:
        st.session_state["evo_checklist_state"] = {}
    
    # Group by phase
    phases = {
        "T-48 Hours (Pre-EVA)": ["evo_01", "evo_02", "evo_03", "evo_04"],
        "T-4 Hours (Final Prep)": ["evo_05", "evo_06", "evo_07"],
        "ISLE Protocol Support": ["evo_08", "evo_09", "evo_10", "evo_11"],
        "EVA Egress": ["evo_12", "evo_13"],
        "Post-EVA": ["evo_14", "evo_15", "evo_16", "evo_17"],
    }
    
    for phase_name, item_ids in phases.items():
        with st.expander(f"📋 {phase_name}", expanded=False):
            for item in EVA_OFFICER_CHECKLIST:
                if item.id not in item_ids:
                    continue
                
                col1, col2 = st.columns([0.5, 5])
                
                with col1:
                    checked = st.checkbox(
                        "Complete",
                        key=f"evo_{item.id}",
                        value=st.session_state["evo_checklist_state"].get(item.id, False),
                        label_visibility="collapsed",
                    )
                    st.session_state["evo_checklist_state"][item.id] = checked
                
                with col2:
                    opacity = "0.5" if checked else "1"
                    text_decoration = "line-through" if checked else "none"
                    bg = "rgba(192, 132, 252, 0.1)" if item.critical else "transparent"
                    
                    critical_badge = '🔴 CRITICAL' if item.critical else ''
                    verify_badge = '✅ VERIFY' if item.verification_required else ''
                    
                    st.markdown(f"""
                    <div style="opacity: {opacity}; background: {bg}; padding: 10px; border-radius: 6px; margin: 4px 0;">
                        <div style="text-decoration: {text_decoration}; font-weight: 500;">
                            {item.description}
                        </div>
                        <div style="color: #888; font-size: 0.85em; margin-top: 4px;">
                            {critical_badge} {verify_badge} | Duration: {item.duration_min} min
                            {f'<br/><em>{item.notes}</em>' if item.notes else ''}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Progress
    completed = sum(1 for item in EVA_OFFICER_CHECKLIST if st.session_state["evo_checklist_state"].get(item.id, False))
    total = len(EVA_OFFICER_CHECKLIST)
    st.progress(completed / total if total > 0 else 0, text=f"EVA Officer Checklist: {completed}/{total}")


def _render_eva_references() -> None:
    """Render scientific references for EVA procedures with verifiable links."""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
        padding: 16px 20px;
        border-radius: 10px;
        margin-bottom: 16px;
        border-left: 4px solid #9ca3af;
    ">
        <h4 style="margin: 0 0 8px 0; color: #fff;">
            📚 EVA Scientific & Technical References
        </h4>
        <p style="margin: 0; color: #d1d5db; font-size: 0.9em;">
            Verified citations with links to original NASA and peer-reviewed sources
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if not ADVANCED_FEATURES_AVAILABLE:
        st.warning("Reference data not available")
        return
    
    # Display references from ANALOG_EVA_TIMELINE
    references = ANALOG_EVA_TIMELINE.get("references", [])
    
    for ref in references:
        citation = ref.get("citation", "")
        url = ref.get("url", "")
        key_finding = ref.get("key_finding", "")
        
        st.markdown(f"""
        <div style="
            background: rgba(255, 255, 255, 0.05);
            border-left: 3px solid #10b981;
            padding: 14px 18px;
            border-radius: 0 8px 8px 0;
            margin: 12px 0;
        ">
            <div style="font-size: 0.95em; line-height: 1.5;">
                {citation}
            </div>
            <div style="margin-top: 8px;">
                <a href="{url}" target="_blank" style="color: #3b82f6; text-decoration: none;">
                    🔗 {url}
                </a>
            </div>
            <div style="
                margin-top: 10px;
                padding: 8px 12px;
                background: rgba(16, 185, 129, 0.15);
                border-radius: 6px;
                font-size: 0.9em;
            ">
                <strong style="color: #10b981;">Key Finding:</strong>
                <span style="color: #f5f5f5;"> {key_finding}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Additional NASA technical resources
    st.markdown("### 🔗 Additional Technical Resources")
    
    additional_refs = [
        {
            "title": "NASA EVA Technical Library",
            "url": "https://eva.jsc.nasa.gov/",
            "description": "Official NASA EVA documentation repository",
        },
        {
            "title": "NASA-STD-3001 Technical Brief: Decompression Sickness",
            "url": "https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-037-decompression-sickness.pdf",
            "description": "NASA Human System Standard - DCS mitigation protocols",
        },
        {
            "title": "Human System Integration Requirements (HSIR)",
            "url": "https://msis.jsc.nasa.gov/sections/section14.htm",
            "description": "Section 14: EVA anthropometry, physiology, and operations",
        },
        {
            "title": "NTRS: EVA Hardware & Operations Overview",
            "url": "https://ntrs.nasa.gov/citations/20140009556",
            "description": "Comprehensive EMU, SAFER, and airlock documentation",
        },
        {
            "title": "Springer: EVA Prebreathe Protocols",
            "url": "https://link.springer.com/referenceworkentry/10.1007/978-3-319-09575-2_60-1",
            "description": "Academic reference on prebreathe protocol evolution",
        },
    ]
    
    cols = st.columns(2)
    for idx, ref in enumerate(additional_refs):
        with cols[idx % 2]:
            st.markdown(f"""
            <div style="
                background: rgba(59, 130, 246, 0.1);
                padding: 12px;
                border-radius: 8px;
                margin: 6px 0;
                border: 1px solid rgba(59, 130, 246, 0.3);
            ">
                <a href="{ref['url']}" target="_blank" style="color: #60a5fa; font-weight: 500; text-decoration: none;">
                    📄 {ref['title']}
                </a>
                <div style="color: #9ca3af; font-size: 0.85em; margin-top: 4px;">
                    {ref['description']}
                </div>
            </div>
            """, unsafe_allow_html=True)


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
            background: linear-gradient(135deg, #0d3b66 0%, #1d5a8a 50%, #2980b9 100%);
            padding: 20px 24px;
            border-radius: 12px;
            margin-bottom: 20px;
            border: 1px solid #3498db;
            box-shadow: 0 4px 15px rgba(52, 152, 219, 0.2);
        ">
            <h2 style="margin: 0; color: #fff;">🗓️ Crew Scheduling & Human Performance</h2>
            <p style="margin: 8px 0 0 0; color: #bde0fe; font-size: 0.95em;">
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
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "👥 Status Dashboard",
        "📅 Timeline & Scheduling",
        "📈 Performance Forecast",
        "🎯 Risk Analysis",
        "🚀 EVA Procedures",
        "📘 NASA Guidelines",
        "📊 Summary & Export",
    ])
    
    with tab1:
        _render_crew_status_grid(engine)
        st.markdown("---")
        _render_alerts_panel(engine, schedule_date)
    
    with tab2:
        # Sub-tabs for different views
        view_mode = st.radio(
            "View Mode",
            options=["📊 Gantt Timeline", "📋 Activity List", "📆 Weekly Overview"],
            horizontal=True,
            key="timeline_view_mode",
        )
        
        st.markdown("---")
        
        if view_mode == "📊 Gantt Timeline":
            _render_timeline_chart(engine, schedule_date)
        elif view_mode == "📋 Activity List":
            _render_activity_list(engine, schedule_date)
        else:  # Weekly Overview
            _render_weekly_overview(engine, schedule_date)
        
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
        
        # Individual IHPI gauges - use 2 columns for better visibility
        st.markdown("### 📈 Individual Performance Indicators")
        crew_list = list(engine.crew_members.values())
        
        # First row: 2 gauges
        gauge_cols_1 = st.columns(2)
        for idx, crew in enumerate(crew_list[:2]):
            with gauge_cols_1[idx]:
                _render_ihpi_gauge(crew)
        
        # Second row: 2 gauges
        if len(crew_list) > 2:
            gauge_cols_2 = st.columns(2)
            for idx, crew in enumerate(crew_list[2:4]):
                with gauge_cols_2[idx]:
                    _render_ihpi_gauge(crew)
        
        # Third row: 2 gauges
        if len(crew_list) > 4:
            gauge_cols_3 = st.columns(2)
            for idx, crew in enumerate(crew_list[4:6]):
                with gauge_cols_3[idx]:
                    _render_ihpi_gauge(crew)
    
    with tab5:
        _render_eva_procedures_panel(engine, schedule_date)
    
    with tab6:
        _render_nasa_scheduling_guidelines()
    
    with tab7:
        _render_crew_summary_table(engine, schedule_date)
        st.markdown("---")
        _render_export_panel(engine, schedule_date)
    
    # Scientific foundation panel
    _render_scientific_foundation_panel()


# ---------------------------------------------------------------------------
# NASA Scheduling Guidelines Panel
# ---------------------------------------------------------------------------

def _render_nasa_scheduling_guidelines() -> None:
    """Render NASA scheduling guidelines and constraints reference panel.
    
    Based on NASA-STD-3001, SPIFe/Playbook tools, and ISS operations procedures.
    """
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1a365d 0%, #234e82 50%, #2c5aa0 100%);
        padding: 20px 24px;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 1px solid #4299e1;
        box-shadow: 0 4px 15px rgba(66, 153, 225, 0.3);
    ">
        <h3 style="margin: 0 0 8px 0; color: #fff;">
            📘 NASA Scheduling Guidelines & Constraints
        </h3>
        <p style="margin: 0; color: #bee3f8; font-size: 0.95em;">
            Evidence-based scheduling parameters from NASA-STD-3001, SPIFe/Playbook tools, and ISS Operations
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Workday limits section
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### ⏰ Workday Limits")
        st.markdown(f"""
        | Parameter | Value | Source |
        |----|----|-----|
        | **Nominal Duty Hours** | {NOMINAL_WORKDAY_HOURS} hr/day | ISS Operations |
        | **Maximum Duty Hours** | {MAX_WORKDAY_HOURS} hr/day | NASA-STD-3001 |
        | **Max Continuous Work** | {MAX_CONTINUOUS_WORK_HOURS} hr | Before break |
        | **Minimum Sleep** | 6.0 hr | Hard requirement |
        | **Optimal Sleep** | 8.0 hr | Recommended |
        | **Rest Between Shifts** | 8.0 hr | Minimum |
        """)
        
        st.markdown("#### 🧠 Cognitive Workload (Bedford Scale)")
        st.markdown(f"""
        | Level | Rating | Description |
        |----|----|-----|
        | **Low** | 1-{COGNITIVE_WORKLOAD_LOW:.0f} | Routine tasks, monitoring |
        | **Medium** | {COGNITIVE_WORKLOAD_LOW:.0f}-{COGNITIVE_WORKLOAD_MEDIUM:.0f} | Complex science, nominal ops |
        | **High** | {COGNITIVE_WORKLOAD_MEDIUM:.0f}-{COGNITIVE_WORKLOAD_HIGH:.0f} | EVA, emergencies |
        | **Overload** | {COGNITIVE_WORKLOAD_HIGH:.0f}-9 | Task restructuring required |
        
        *Bedford Scale: 1-3 satisfactory, 4-6 tolerable, 7-9 unacceptable*
        """)
    
    with col2:
        st.markdown("#### 💪 Physical Workload (Borg CR-10)")
        st.markdown(f"""
        | Rating | Descriptor | Example |
        |----|----|-----|
        | **0** | Nothing | Rest |
        | **2** | Weak | Light tasks |
        | **{PHYSICAL_WORKLOAD_TARGET:.0f}** | Somewhat Strong | Target (3001 limit) |
        | **6** | Strong | Exercise |
        | **10** | Maximal | Emergency |
        
        *NASA-STD-3001: RPE ≤ 4 for crew interfaces*
        """)
        
        st.markdown("#### 🎯 Activity Priority Levels")
        st.markdown("""
        | Priority | Level | Examples |
        |----|-----|-----|
        | **1** | Emergency | Life-threatening |
        | **2** | Safety-Critical | Safety procedures |
        | **3** | Mission-Critical | EVA, key experiments |
        | **4** | Health Maintenance | Exercise, medical |
        | **5** | Routine Ops | Nominal activities |
        | **6** | Discretionary | Crew preference |
        
        *Based on ISS Flight Rules*
        """)
    
    # Scheduling constraints
    st.markdown("---")
    st.markdown("#### 📋 Habitat Constraints")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("##### ⏱️ Temporal")
        for constraint in ISS_SCHEDULING_CONSTRAINTS:
            if constraint.constraint_type == "temporal":
                value_str = ""
                if constraint.min_value is not None and constraint.max_value is not None:
                    value_str = f"{constraint.min_value:.0f}-{constraint.max_value:.0f}"
                elif constraint.min_value is not None:
                    value_str = f"≥{constraint.min_value:.0f}"
                elif constraint.max_value is not None:
                    value_str = f"≤{constraint.max_value:.0f}"
                st.markdown(
                    f"""
                    <div style="
                        background: linear-gradient(135deg, #2c3e5022, #34495e11);
                        border-left: 3px solid #3498db;
                        border-radius: 4px;
                        padding: 10px 12px;
                        margin: 6px 0;
                    ">
                        <div style="font-weight: 600; color: #1a1a1a; font-size: 0.95em; margin-bottom: 4px;">
                            {constraint.name}
                        </div>
                        <div style="font-size: 1.1em; font-weight: 700; color: #2c3e50;">
                            {value_str}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    
    with col2:
        st.markdown("##### 🔧 Resource")
        for constraint in ISS_SCHEDULING_CONSTRAINTS:
            if constraint.constraint_type == "resource":
                value_str = f"max {constraint.max_value:.0f}" if constraint.max_value else ""
                st.markdown(
                    f"""
                    <div style="
                        background: linear-gradient(135deg, #f39c1222, #e67e2211);
                        border-left: 3px solid #f39c12;
                        border-radius: 4px;
                        padding: 10px 12px;
                        margin: 6px 0;
                    ">
                        <div style="font-weight: 600; color: #1a1a1a; font-size: 0.95em; margin-bottom: 4px;">
                            {constraint.name}
                        </div>
                        <div style="font-size: 1.1em; font-weight: 700; color: #2c3e50;">
                            {value_str}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    
    with col3:
        st.markdown("##### 👥 Crew")
        for constraint in ISS_SCHEDULING_CONSTRAINTS:
            if constraint.constraint_type == "crew":
                value_str = ""
                if constraint.min_value is not None and constraint.max_value is not None:
                    value_str = f"{constraint.min_value:.0f}-{constraint.max_value:.0f}"
                elif constraint.min_value is not None:
                    value_str = f"≥{constraint.min_value:.0f}"
                elif constraint.max_value is not None:
                    value_str = f"≤{constraint.max_value:.0f}"
                st.markdown(
                    f"""
                    <div style="
                        background: linear-gradient(135deg, #27ae6022, #22995411);
                        border-left: 3px solid #27ae60;
                        border-radius: 4px;
                        padding: 10px 12px;
                        margin: 6px 0;
                    ">
                        <div style="font-weight: 600; color: #1a1a1a; font-size: 0.95em; margin-bottom: 4px;">
                            {constraint.name}
                        </div>
                        <div style="font-size: 1.1em; font-weight: 700; color: #2c3e50;">
                            {value_str}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    
    # Task categories
    st.markdown("---")
    st.markdown("#### 📊 Task Categories and Workload")
    
    task_data = []
    for task_id, task in TASK_CATEGORIES.items():
        task_data.append({
            "Task": task.name,
            "Cognitive (Bedford)": task.cognitive_load,
            "Physical (Borg)": task.physical_load,
            "Proficiency": task.min_crew_proficiency.title(),
            "Parallel OK": "✅" if task.parallel_allowed else "❌",
        })
    
    import pandas as pd
    df = pd.DataFrame(task_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # References
    with st.expander("📚 Scientific References", expanded=False):
        st.markdown("""
        **NASA Standards and Technical Documentation:**
        
        1. **NASA-STD-3001 Volume 2 Rev D** - Human Factors, Habitability, and Environmental Health
           - [NASA Standards Portal](https://standards.nasa.gov/standard/NASA/NASA-STD-3001_VOL_2)
        
        2. **OCHMO Cognitive Workload Technical Brief (2023)**
           - [PDF Download](https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-032-cognitive-workload.pdf)
        
        3. **SPIFe/Playbook Planning Tools**
           - [NASA Ames HCI Group](https://hci.arc.nasa.gov/work/playbook.html)
           - [OpenSPIFe on GitHub](https://github.com/nasa/OpenSPIFe)
        
        4. **ISS Crew Autonomous Scheduling Test (CAST)**
           - [NASA NTRS 20190027148](https://ntrs.nasa.gov/citations/20190027148)
        
        5. **Crew Scheduling Tools Research**
           - [Human Research Roadmap Task 820](https://humanresearchroadmap.nasa.gov/tasks/?i=820)
        
        **Key Findings:**
        - NASA nominal workday: 8.5 hours, max 10 hours (12 hours for critical ops only)
        - Maximum continuous work without break: 2 hours
        - Bedford workload scale 1-9: target ≤6 for nominal operations
        - Borg CR-10 physical workload: target ≤4 for crew interfaces
        - ISS uses "job jar" system for crew task selection within constraints
        """)


# ---------------------------------------------------------------------------
# Scientific Foundation Panel
# ---------------------------------------------------------------------------

# Verified scientific references with DOIs
SCIENTIFIC_REFERENCES = {
    "fatigue_models": {
        "title": "Fatigue & Performance Models",
        "icon": "🧠",
        "papers": [
            {
                "citation": "Hursh SR, Redmond DP, Johnson ML, et al. (2004). Fatigue models for applied research in warfighting.",
                "journal": "Aviation, Space, and Environmental Medicine",
                "volume": "75(3 Suppl):A44-A53",
                "doi": "PMID:15018265",
                "key_finding": "SAFTE model validated for predicting cognitive performance with effectiveness thresholds: ≥90% low-risk, 70-79% high-risk (~0.08 BAC equivalence)",
                "used_for": "SAFTE effectiveness scoring, fatigue risk zones",
            },
            {
                "citation": "Paul MA, Hursh SR, Love R. (2020). The Importance of Validating Sleep Behavior Models for Fatigue Management Software in Military Aviation.",
                "journal": "Military Medicine",
                "volume": "185(11-12):e1986-e1992",
                "doi": "10.1093/milmed/usaa210",
                "key_finding": "SAFTE-FAST validated in military aviation; harmonized sleep behavior model achieved near-perfect fatigue risk estimates",
                "used_for": "Military aviation fatigue risk management validation",
            },
            {
                "citation": "Veksler BZ, Morris MB, Krusmark M, Gunzelmann G. (2022). Integrated Modeling of Fatigue Impacts on C-17 Approach and Landing Performance.",
                "journal": "Journal of Cognitive Engineering and Decision Making",
                "volume": "17(2):123-145",
                "doi": "10.1080/24721840.2022.2149526",
                "key_finding": "Biomathematical fatigue models successfully predict performance degradations on specific aircraft operations",
                "used_for": "SAFTE integration with task performance models",
            },
        ],
    },
    "hrv_monitoring": {
        "title": "Heart Rate Variability & Recovery",
        "icon": "💓",
        "papers": [
            {
                "citation": "Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology. (1996). Heart rate variability: standards of measurement, physiological interpretation and clinical use.",
                "journal": "European Heart Journal",
                "volume": "17:354-381",
                "doi": "10.1093/oxfordjournals.eurheartj.a014868",
                "key_finding": "Gold-standard HRV measurement protocols: 5-min short-term recordings, RMSSD for vagal tone",
                "used_for": "HRV measurement standards, RMSSD interpretation",
            },
            {
                "citation": "Plews DJ, Laursen PB, Stanley J, Kilding AE, Buchheit M. (2013). Training adaptation and heart rate variability in elite endurance athletes: Opening the door to effective monitoring.",
                "journal": "Sports Medicine",
                "volume": "43(9):773-781",
                "doi": "10.1007/s40279-013-0071-8",
                "key_finding": "lnRMSSD z-score approach with rolling baseline (14-28 days) for individualized training monitoring; z < -1 indicates fatigue/overreaching",
                "used_for": "lnRMSSD z-score calculation, HRV-guided training",
            },
            {
                "citation": "Esco MA, Fields AD, Mohammadnabi MA, Kliszczewicz BM. (2025). Monitoring Training Adaptation and Recovery Status in Athletes Using Heart Rate Variability via Mobile Devices.",
                "journal": "Sensors",
                "volume": "26(1):3",
                "doi": "10.3390/s26010003",
                "key_finding": "Weekly RMSSD averages and coefficient of variation capture chronic adaptations and acute perturbations",
                "used_for": "Mobile HRV monitoring protocols, recovery assessment",
            },
        ],
    },
    "energy_availability": {
        "title": "Energy Availability & RED-S",
        "icon": "⚡",
        "papers": [
            {
                "citation": "Mountjoy M, Sundgot-Borgen JK, Burke LM, et al. (2018). International Olympic Committee (IOC) Consensus Statement on Relative Energy Deficiency in Sport (RED-S): 2018 Update.",
                "journal": "British Journal of Sports Medicine",
                "volume": "52(11):687-697",
                "doi": "10.1136/bjsports-2018-099193",
                "key_finding": "Energy Availability thresholds: ≥45 kcal/kg FFM/day optimal; <30 kcal/kg FFM/day triggers physiological impairments",
                "used_for": "EA scoring thresholds, RED-S risk assessment",
            },
            {
                "citation": "Mountjoy M, Ackerman KE, Bailey DM, et al. (2023). 2023 International Olympic Committee's (IOC) consensus statement on Relative Energy Deficiency in Sport (REDs).",
                "journal": "British Journal of Sports Medicine",
                "volume": "57(17):1073-1097",
                "doi": "10.1136/bjsports-2023-106994",
                "key_finding": "Updated REDs Clinical Assessment Tool-Version 2 with severity classification and sport participation recommendations",
                "used_for": "Updated EA assessment, clinical decision support",
            },
        ],
    },
    "vigilance_performance": {
        "title": "Vigilance & Psychomotor Performance",
        "icon": "👁️",
        "papers": [
            {
                "citation": "Basner M, Dinges DF. (2011). Maximizing sensitivity of the psychomotor vigilance test (PVT) to sleep loss.",
                "journal": "Sleep",
                "volume": "34(5):581-591",
                "doi": "10.1093/sleep/34.5.581",
                "key_finding": "3-minute PVT with 355ms lapse threshold highly sensitive to sleep loss; 10-minute PVT gold standard",
                "used_for": "PVT lapse scoring, vigilance assessment",
            },
            {
                "citation": "Åkerstedt T, Gillberg M. (1990). Subjective and objective sleepiness in the active individual.",
                "journal": "International Journal of Neuroscience",
                "volume": "52(1-2):29-37",
                "doi": "10.3109/00207459008994241",
                "key_finding": "Karolinska Sleepiness Scale (KSS) validated: 1-5 alert, 6-7 caution, 8-9 severe sleepiness requiring intervention",
                "used_for": "KSS scoring interpretation, subjective sleepiness assessment",
            },
        ],
    },
    "eva_physiology": {
        "title": "EVA & Space Physiology",
        "icon": "🚀",
        "papers": [
            {
                "citation": "NASA-STD-3001 Volume 1 Revision B. (2022). Human Performance Capabilities.",
                "journal": "NASA Technical Standard",
                "volume": "JSC-65044",
                "doi": "NASA-STD-3001",
                "key_finding": "EVA VO₂max requirement: ≥32.9 ml/kg/min for microgravity operations; derived from EVA metabolic demands",
                "used_for": "EVA GO/NO-GO VO₂max gate",
            },
            {
                "citation": "Waligora JM, Kumar KV. (1995). Energy utilization rates during shuttle extravehicular activities.",
                "journal": "NASA Technical Report",
                "volume": "NASA NTRS",
                "doi": "PMID:11540993",
                "key_finding": "Shuttle EVA average metabolic rate: 194 kcal/hr (significantly lower than Skylab 238 kcal/hr); peak rates below design levels",
                "used_for": "EVA energy expenditure planning, activity scheduling",
            },
            {
                "citation": "Greenleaf JE. (1989). Energy and thermal regulation during bed rest and spaceflight.",
                "journal": "Journal of Applied Physiology",
                "volume": "67(2):507-516",
                "doi": "PMID:2676944",
                "key_finding": "Long-duration space mission energy requirements ~3,100 kcal/day; 5-hr EVA sortie requires +529,250 kcal/year",
                "used_for": "Mission energy planning, EVA nutritional requirements",
            },
        ],
    },
    "met_compendium": {
        "title": "Metabolic Equivalents & Activity",
        "icon": "🏃",
        "papers": [
            {
                "citation": "Ainsworth BE, Haskell WL, Herrmann SD, et al. (2024). 2024 Compendium of Physical Activities: A Third Update of Activity Codes and MET Intensities.",
                "journal": "Medicine & Science in Sports & Exercise",
                "volume": "56(Suppl):S1-S152",
                "doi": "10.1249/MSS.0000000000003356",
                "key_finding": "Standardized MET values for 800+ activities; cycling moderate effort 7.0 METs, sleeping 1.0 MET, sitting meetings 1.5 METs",
                "used_for": "Activity MET values, energy expenditure calculations",
            },
        ],
    },
    "hydration": {
        "title": "Hydration & Cognitive Performance",
        "icon": "💧",
        "papers": [
            {
                "citation": "Armstrong LE, Casa DJ, Millard-Stafford M, et al. (2007). ACSM position stand: Exertional heat illness during training and competition.",
                "journal": "Medicine & Science in Sports & Exercise",
                "volume": "39(3):556-572",
                "doi": "10.1249/mss.0b013e31802fa199",
                "key_finding": "Body mass loss >2% impairs cognitive and physical performance; USG ≥1.030 indicates significant hypohydration",
                "used_for": "Hydration scoring thresholds, dehydration gates",
            },
        ],
    },
    "circadian": {
        "title": "Circadian Rhythms & Shift Work",
        "icon": "🌙",
        "papers": [
            {
                "citation": "ICAO Doc 9966. (2016). Manual for the Oversight of Fatigue Management Approaches.",
                "journal": "International Civil Aviation Organization",
                "volume": "2nd Edition",
                "doi": "ICAO-9966",
                "key_finding": "Circadian phase misalignment >6 hours severely degrades performance; optimal scheduling aligns with chronotype",
                "used_for": "Circadian alignment scoring, shift scheduling",
            },
            {
                "citation": "AFMAN 11-202V3. (2022). General Flight Rules.",
                "journal": "U.S. Air Force Manual",
                "volume": "AFI 11-202V3",
                "doi": "AFMAN-11-202V3",
                "key_finding": "Military crew rest requirements: minimum 8 hours rest opportunity, maximum 16 hours duty day",
                "used_for": "Crew rest planning, duty time limits",
            },
        ],
    },
}


def _render_citation_card(paper: dict, domain_color: str) -> None:
    """Render a single citation card with DOI link."""
    doi = paper.get("doi", "")
    
    # Build DOI link
    if doi.startswith("10."):
        doi_link = f"https://doi.org/{doi}"
        doi_display = f'<a href="{doi_link}" target="_blank" style="color: #3498db;">DOI: {doi}</a>'
    elif doi.startswith("PMID:"):
        pmid = doi.replace("PMID:", "")
        doi_link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        doi_display = f'<a href="{doi_link}" target="_blank" style="color: #3498db;">{doi}</a>'
    elif doi.startswith("NASA") or doi.startswith("ICAO") or doi.startswith("AFMAN"):
        doi_display = f'<span style="color: #2c3e50;">{doi}</span>'
    else:
        doi_display = f'<span style="color: #2c3e50;">{doi}</span>'
    
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {domain_color}15, {domain_color}08);
            border-left: 3px solid {domain_color};
            border-radius: 0 8px 8px 0;
            padding: 12px 16px;
            margin: 8px 0;
        ">
            <div style="font-size: 0.9em; line-height: 1.5;">
                {paper['citation']}
                <br/><span style="color: #2c3e50;">{paper['journal']}, {paper['volume']}</span>
                <br/>{doi_display}
            </div>
            <div style="
                margin-top: 10px;
                padding: 8px 12px;
                background: rgba(0,0,0,0.3);
                border-radius: 6px;
                font-size: 0.85em;
            ">
                <strong style="color: {domain_color};">Key Finding:</strong>
                <span style="color: #f5f5f5;"> {paper['key_finding']}</span>
            </div>
            <div style="
                margin-top: 6px;
                font-size: 0.8em;
                color: #2c3e50;
            ">
                <strong>Used in app:</strong> {paper['used_for']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_scientific_foundation_panel() -> None:
    """Render the comprehensive scientific foundation panel with verified citations."""
    st.markdown("---")
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #0d4d4d 0%, #1a6b6b 50%, #2d8a8a 100%);
            padding: 20px 24px;
            border-radius: 12px;
            margin: 20px 0;
            border: 1px solid #3db9b9;
            box-shadow: 0 4px 15px rgba(61, 185, 185, 0.2);
        ">
            <h3 style="margin: 0 0 8px 0; color: #fff;">
                📚 Scientific Foundation
            </h3>
            <p style="margin: 0; color: #b8e6e6; font-size: 0.9em;">
                This scheduling system is built on peer-reviewed research and validated standards from 
                space agencies, sports science, and aviation medicine. All thresholds and scoring 
                functions are evidence-based with verifiable citations.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Domain colors
    domain_colors = {
        "fatigue_models": "#e74c3c",
        "hrv_monitoring": "#e91e63",
        "energy_availability": "#f39c12",
        "vigilance_performance": "#9b59b6",
        "eva_physiology": "#2196f3",
        "met_compendium": "#27ae60",
        "hydration": "#00bcd4",
        "circadian": "#673ab7",
    }
    
    # Science summary cards
    st.markdown("### 🔬 How Science Informs Each Component")
    
    summary_cols = st.columns(4)
    summaries = [
        ("SAFTE Fatigue Model", "30% weight", "Predicts cognitive effectiveness from sleep history", "#e74c3c"),
        ("HRV lnRMSSD z-score", "10% weight", "Tracks autonomic recovery from personalized baseline", "#e91e63"),
        ("Energy Availability", "10% weight", "IOC thresholds prevent RED-S health consequences", "#f39c12"),
        ("PVT Vigilance", "20% weight", "3-min test sensitive to sleep loss effects", "#9b59b6"),
    ]
    
    for idx, (title, weight, desc, color) in enumerate(summaries):
        with summary_cols[idx]:
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, {color}22, {color}11);
                    border: 1px solid {color};
                    border-radius: 10px;
                    padding: 14px;
                    height: 140px;
                ">
                    <div style="font-weight: 600; color: {color}; font-size: 0.95em;">
                        {title}
                    </div>
                    <div style="color: #1a1a1a; font-size: 0.8em; margin: 4px 0; font-weight: 600;">
                        {weight}
                    </div>
                    <div style="color: #2c3e50; font-size: 0.85em; margin-top: 8px;">
                        {desc}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    
    st.markdown("---")
    
    # Full references by domain
    with st.expander("📖 Full Scientific References by Domain", expanded=False):
        for domain_id, domain_data in SCIENTIFIC_REFERENCES.items():
            color = domain_colors.get(domain_id, "#3498db")
            
            st.markdown(
                f"""
                <div style="
                    margin: 16px 0 8px 0;
                    padding-bottom: 4px;
                    border-bottom: 2px solid {color};
                ">
                    <span style="font-size: 1.2em;">{domain_data['icon']}</span>
                    <span style="font-size: 1.1em; font-weight: 600; color: #fff; margin-left: 8px;">
                        {domain_data['title']}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            for paper in domain_data["papers"]:
                _render_citation_card(paper, color)
    
    # IHPI methodology
    with st.expander("⚙️ IHPI Calculation Methodology", expanded=False):
        st.markdown(
            """
            ### Integrated Human Performance Indicator (IHPI)
            
            The IHPI is a weighted composite score (0-100) combining 8 evidence-based domains:
            
            | Component | Weight | Scoring Function | Evidence Source |
            |-----------|--------|------------------|-----------------|
            | **SAFTE Effectiveness** | 30% | Linear 70→90 maps to 0→1 | Hursh et al. (2004) |
            | **PVT Performance** | 20% | 10-20 lapses maps to 1→0 | Basner & Dinges (2011) |
            | **Circadian Alignment** | 10% | 1h→6h offset maps to 1→0 | ICAO Doc 9966 |
            | **HRV (lnRMSSD z)** | 10% | -0.5→-2.0 maps to 1→0 | Plews et al. (2013) |
            | **Hydration** | 10% | <0.5%→>2% loss maps to 1→0 | ACSM (2007) |
            | **Energy Availability** | 10% | 30→45 kcal/kg FFM maps to 0→1 | IOC (2018) |
            | **Subjective Sleepiness** | 5% | KSS 5→8 maps to 1→0 | Åkerstedt (1990) |
            | **Task-Specific** | 5% | VO₂max gate + recovery | NASA-STD-3001 |
            
            #### Hard-Cap Gating Logic
            
            If any **critical domain** scores 0, the entire IHPI is capped at 0:
            - SAFTE ≤70% → immediate fatigue concern
            - Hydration >2% loss → cognitive impairment
            - PVT ≥20 lapses → vigilance failure
            - KSS ≥8 → severe sleepiness
            
            This prevents high scores in some domains from masking critical deficits.
            """
        )
    
    # EVA decision matrix
    with st.expander("🚀 EVA GO/NO-GO Decision Matrix", expanded=False):
        st.markdown(
            """
            ### Hierarchical Gate Structure
            
            The EVA GO/NO-GO decision uses a guardrails-first approach where hard gates 
            are evaluated before the IHPI score:
            
            #### Hard NO-GO Gates (any triggers NO-GO)
            
            | Gate | Threshold | Evidence |
            |------|-----------|----------|
            | SAFTE Effectiveness | < 70% | ~0.08 BAC equivalence (Hursh et al.) |
            | KSS Score | ≥ 8 | Severe sleepiness requiring intervention |
            | Sleep in last 24h | < 6 hours | Minimum recovery requirement |
            | Time Awake | ≥ 21 hours | Extended wakefulness risk |
            | Body Mass Loss | > 2% | ACSM cognitive impairment threshold |
            | USG | ≥ 1.030 | Significant hypohydration |
            | PVT Lapses (3-min) | ≥ 20 | Low vigilance performance |
            | VO₂max | < 32.9 ml/kg/min | NASA EVA requirement |
            | Time Since Last EVA | < 24h | Minimum recovery period |
            
            #### Decision Levels
            
            | Status | Criteria | Action |
            |--------|----------|--------|
            | **GO** | All gates pass, IHPI ≥ 85 | Clear for EVA |
            | **GO-with-mitigation** | All gates pass, IHPI 75-84 | Add naps/breaks/task simplification |
            | **HOLD** | SAFTE 70-79% or IHPI < 75 | Optimize sleep, delay EVA |
            | **NO-GO** | Any hard gate fails | Activity restriction required |
            """
        )
    
    # Version and validation
    st.markdown(
        """
        <div style="
            margin-top: 20px;
            padding: 12px 16px;
            background: rgba(39, 174, 96, 0.1);
            border: 1px solid #27ae60;
            border-radius: 8px;
            font-size: 0.85em;
        ">
            <strong style="color: #27ae60;">✅ Evidence-Based Implementation</strong>
            <br/>
            <span style="color: #888;">
                All scoring functions, thresholds, and decision logic are derived from peer-reviewed 
                literature and validated standards. References include DOIs/PMIDs for verification.
                Last literature review: December 2025.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    "render_scheduling_tab",
    "SCHEDULING_AVAILABLE",
    "SCIENTIFIC_REFERENCES",
]

