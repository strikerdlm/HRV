"""Sleep Analysis Tab for Streamlit HRV Application.

This module provides the Streamlit UI components for:
- User session management (ID and name)
- Multi-day sleep data visualization
- Hypnogram display (PSG-style)
- Sleep quality metrics and trends
- SAFTE model integration
- Device data import and fusion

Design principles:
- Graceful degradation when data is missing
- Medical-grade visualization quality
- Multi-night longitudinal tracking
- Strict scientific accuracy

Author: Dr. Diego Malpica, MD - Aerospace Medicine Specialist
National University of Colombia | Colombian Aerospace Force
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd
import streamlit as st

# Local imports
try:
    from sleep_analysis import (
        SleepNight,
        SleepArchitecture,
        MultiNightSummary,
        HypnogramData,
        generate_hypnogram_data,
        build_hypnogram_echarts_option,
        build_sleep_architecture_gauge,
        build_sleep_stages_pie,
        build_sleep_metrics_radar,
        build_multi_night_trend_chart,
        compute_multi_night_summary,
        create_sleep_night_from_garmin,
        create_sleep_night_from_actigraph,
        create_sleep_night_from_somfit,
        prepare_safte_sleep_schedule,
        compute_sleep_debt_for_safte,
    )
    from user_data_manager import (
        UserDataManager,
        UserInfo,
        UserDataSummary,
        create_user_manager,
        get_or_create_user,
    )
    from echarts_component import st_echarts
    from fatigue_integration import (
        run_integrated_fatigue_analysis,
        UserProfile,
        SleepScheduleInput,
        WorkScheduleInput,
        FatigueAnalysisResult,
    )
    IMPORTS_OK = True
except ImportError as e:
    IMPORTS_OK = False
    IMPORT_ERROR = str(e)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Session state keys
_SESSION_USER_MANAGER = "sleep_user_manager"
_SESSION_CURRENT_USER = "sleep_current_user"
_SESSION_SLEEP_NIGHTS = "sleep_nights"
_SESSION_MULTI_SUMMARY = "sleep_multi_summary"


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _get_user_manager() -> UserDataManager:
    """Get or create UserDataManager from session state."""
    if _SESSION_USER_MANAGER not in st.session_state:
        st.session_state[_SESSION_USER_MANAGER] = create_user_manager()
    return st.session_state[_SESSION_USER_MANAGER]


def _render_user_login_section() -> UserInfo | None:
    """Render user login/registration section.

    Returns:
        UserInfo if user is logged in, None otherwise.
    """
    st.sidebar.markdown("---")
    st.sidebar.header("👤 User Session")

    # Check if already logged in
    if _SESSION_CURRENT_USER in st.session_state and st.session_state[_SESSION_CURRENT_USER]:
        user = st.session_state[_SESSION_CURRENT_USER]
        st.sidebar.success(f"✅ Logged in: **{user.name}**")
        st.sidebar.caption(f"ID: {user.user_id}")

        if st.sidebar.button("🚪 Logout", key="logout_btn"):
            st.session_state[_SESSION_CURRENT_USER] = None
            st.session_state[_SESSION_SLEEP_NIGHTS] = []
            st.rerun()

        return user

    # Login/Register form with debounced submission
    login_expander = st.sidebar.expander("🔐 Login / Register", expanded=True)
    with login_expander:
        with st.form("sleep_login_form", clear_on_submit=False):
            user_id = st.text_input(
                "Identification Number (Cedula/ID)",
                key="user_id_input",
                help="Enter your unique identification number",
            )
            user_name = st.text_input(
                "Full Name",
                key="user_name_input",
                help="Enter your full name",
            )

            col1, col2 = st.columns(2)
            with col1:
                user_age = st.number_input(
                    "Age",
                    min_value=1,
                    max_value=120,
                    value=30,
                    key="user_age_input",
                )
            with col2:
                user_sex = st.selectbox(
                    "Sex",
                    options=["Male", "Female", "Other"],
                    key="user_sex_input",
                )

            login_submitted = st.form_submit_button(
                "🔑 Login / Create Account",
            )

        if login_submitted:
            if user_id and user_name:
                try:
                    manager = _get_user_manager()
                    user = get_or_create_user(
                        manager=manager,
                        user_id=user_id,
                        name=user_name,
                        age=int(user_age),
                        sex=user_sex,
                    )
                    st.session_state[_SESSION_CURRENT_USER] = user
                    st.success(f"Welcome, {user.name}!")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Login failed: {exc}")
            else:
                st.warning("Please enter both ID and name")

    return None


def _render_data_management_section(user: UserInfo) -> None:
    """Render data management section in sidebar.

    Args:
        user: Current logged-in user.
    """
    st.sidebar.markdown("---")
    st.sidebar.header("📂 Data Management")

    manager = _get_user_manager()
    manager.set_current_user(user.user_id, user.name)

    # Show data summary
    with st.sidebar.expander("📊 Data Summary"):
        try:
            data_bundle = manager.load_all_user_data()
            rr_count = len(data_bundle.get("rr_files", {}))
            sleep_count = len(data_bundle.get("sleep_data", []))
            activity_count = len(data_bundle.get("activity_data", []))

            st.metric("RR Files", rr_count)
            st.metric("Sleep Records", sleep_count)
            st.metric("Activity Records", activity_count)

            if data_bundle.get("warnings"):
                for warn in data_bundle["warnings"][:3]:
                    st.warning(warn)

        except Exception as e:
            st.error(f"Error loading data: {e}")

    # Load stored data button
    if st.sidebar.button("📥 Load All Stored Data", key="load_data_btn"):
        try:
            _load_user_sleep_data(user)
            st.sidebar.success("Data loaded successfully!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error: {e}")


def _load_user_sleep_data(user: UserInfo) -> None:
    """Load all sleep data for the current user.

    Args:
        user: Current user.
    """
    manager = _get_user_manager()
    manager.set_current_user(user.user_id, user.name)

    nights: list[SleepNight] = []
    data_bundle = manager.load_all_user_data()

    # Load sleep data records
    for sleep_record in data_bundle.get("sleep_data", []):
        try:
            rec_date_str = sleep_record.get("_recording_date")
            if rec_date_str:
                rec_date = date.fromisoformat(rec_date_str)
            else:
                continue

            source = sleep_record.get("_source", "unknown")

            if source == "garmin" or "garmin" in sleep_record.get("_filename", "").lower():
                night = create_sleep_night_from_garmin(sleep_record, rec_date)
            else:
                # Try to parse as generic sleep data
                night = SleepNight(recording_date=rec_date, source=source)
                # Extract metrics if available
                if "tst_minutes" in sleep_record or "sleepTimeSeconds" in sleep_record:
                    tst_min = sleep_record.get("tst_minutes", sleep_record.get("sleepTimeSeconds", 0) / 60)
                    arch = SleepArchitecture(
                        recording_date=rec_date,
                        tst_minutes=float(tst_min),
                        sleep_efficiency=float(sleep_record.get("sleep_efficiency", sleep_record.get("sleepEfficiency", 0))),
                        n3_pct=float(sleep_record.get("n3_pct", sleep_record.get("deepSleepPercentage", 0))),
                        rem_pct=float(sleep_record.get("rem_pct", sleep_record.get("remSleepPercentage", 0))),
                        source=source,
                    )
                    arch.quality_score = float(sleep_record.get("quality_score", sleep_record.get("sleepScore", 0)))
                    night.architecture = arch

            if night.architecture:
                nights.append(night)

        except Exception as e:
            _LOGGER.warning("Failed to parse sleep record: %s", e)

    # Sort by date
    nights.sort(key=lambda n: n.recording_date)

    # Store in session state
    st.session_state[_SESSION_SLEEP_NIGHTS] = nights

    # Compute multi-night summary
    if nights:
        st.session_state[_SESSION_MULTI_SUMMARY] = compute_multi_night_summary(nights)


def _render_device_import_section(user: UserInfo) -> None:
    """Render device data import section.

    Args:
        user: Current user.
    """
    st.sidebar.markdown("---")
    st.sidebar.header("📱 Import Device Data")

    manager = _get_user_manager()
    manager.set_current_user(user.user_id, user.name)

    # Garmin import
    garmin_expander = st.sidebar.expander("Garmin Data")
    with garmin_expander:
        with st.form("garmin_import_form", clear_on_submit=True):
            garmin_file = st.file_uploader(
                "Upload Garmin Sleep JSON/ZIP",
                type=["json", "zip"],
                key="garmin_sleep_upload",
                help="Upload Garmin Connect sleep JSON or full ZIP exports.",
            )
            garmin_submit = st.form_submit_button("📥 Import Garmin Sleep Data")

        if garmin_submit:
            if garmin_file is None:
                st.warning("Please select a Garmin JSON or ZIP file before importing.")
            else:
                with st.spinner("Processing Garmin data..."):
                    try:
                        content = garmin_file.getvalue()
                        filename = garmin_file.name.lower()

                        if filename.endswith(".json"):
                            sleep_data = json.loads(content.decode("utf-8"))
                            rec_date = date.today()
                            if "calendarDate" in sleep_data:
                                rec_date = date.fromisoformat(sleep_data["calendarDate"])

                            manager.store_sleep_data(sleep_data, rec_date, source="garmin")
                            manager.store_device_file(content, garmin_file.name, device_type="garmin")
                            st.success(f"Stored Garmin sleep data for {rec_date}")

                        elif filename.endswith(".zip"):
                            manager.store_device_file(content, garmin_file.name, device_type="garmin")
                            st.success("Stored Garmin ZIP file for processing")
                        else:
                            st.warning("Unsupported Garmin file type. Please upload .json or .zip.")
                    except json.JSONDecodeError as exc:
                        st.error(f"Invalid Garmin JSON file: {exc}")
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Error processing Garmin data: {exc}")
                    finally:
                        st.session_state.pop("garmin_sleep_upload", None)

    # ActiGraph import
    actigraph_expander = st.sidebar.expander("ActiGraph Data")
    with actigraph_expander:
        with st.form("actigraph_import_form", clear_on_submit=True):
            actigraph_file = st.file_uploader(
                "Upload ActiGraph File",
                type=["gt3x", "agd", "csv"],
                key="actigraph_sleep_upload",
                help="Supports GT3X, AGD, or CSV exports.",
            )
            actigraph_submit = st.form_submit_button("📥 Import ActiGraph Data")

        if actigraph_submit:
            if actigraph_file is None:
                st.warning("Select an ActiGraph file before importing.")
            else:
                with st.spinner("Storing ActiGraph file..."):
                    try:
                        content = actigraph_file.getvalue()
                        manager.store_device_file(content, actigraph_file.name, device_type="actigraph")
                        st.success("Stored ActiGraph file.")
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Error storing ActiGraph file: {exc}")
                    finally:
                        st.session_state.pop("actigraph_sleep_upload", None)

    # Somfit Pro import
    somfit_expander = st.sidebar.expander("Somfit Pro Data")
    with somfit_expander:
        with st.form("somfit_import_form", clear_on_submit=True):
            somfit_file = st.file_uploader(
                "Upload Somfit EDF/CSV",
                type=["edf", "csv"],
                key="somfit_sleep_upload",
                help="Upload EDF or CSV exports from Somfit Pro.",
            )
            somfit_submit = st.form_submit_button("📥 Import Somfit Data")

        if somfit_submit:
            if somfit_file is None:
                st.warning("Select a Somfit file before importing.")
            else:
                with st.spinner("Storing Somfit file..."):
                    try:
                        content = somfit_file.getvalue()
                        manager.store_device_file(content, somfit_file.name, device_type="somfit")
                        st.success("Stored Somfit file.")
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Error storing Somfit file: {exc}")
                    finally:
                        st.session_state.pop("somfit_sleep_upload", None)


# ---------------------------------------------------------------------------
# Main tab rendering functions
# ---------------------------------------------------------------------------


def render_sleep_overview(nights: list[SleepNight], summary: MultiNightSummary | None) -> None:
    """Render sleep overview section.

    Args:
        nights: List of sleep nights.
        summary: Multi-night summary.
    """
    st.header("🌙 Sleep Overview")

    if not nights:
        st.info("""
        **No sleep data available yet.**

        To analyze your sleep:
        1. Log in using the sidebar
        2. Import sleep data from your devices (Garmin, ActiGraph, Somfit)
        3. Click "Load All Stored Data" to load previous data

        **Supported Data Sources:**
        - Garmin Connect sleep exports (JSON/ZIP)
        - ActiGraph GT3X/GT3X+ files
        - Compumedics Somfit Pro EDF files
        - Manual sleep logs
        """)
        return

    # Summary metrics
    if summary:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Nights Recorded",
                summary.n_nights,
                help="Total nights with sleep data",
            )
        with col2:
            st.metric(
                "Avg Sleep Time",
                f"{summary.avg_tst_hours:.1f}h",
                delta=f"{summary.tst_trend:+.2f}h/day" if summary.tst_trend != 0 else None,
                help="Average total sleep time",
            )
        with col3:
            st.metric(
                "Avg Efficiency",
                f"{summary.avg_sleep_efficiency:.1f}%",
                delta=f"{summary.efficiency_trend:+.1f}%/day" if summary.efficiency_trend != 0 else None,
                help="Average sleep efficiency",
            )
        with col4:
            st.metric(
                "Sleep Debt",
                f"{summary.sleep_debt_hours:.1f}h",
                delta=f"vs 8h target",
                delta_color="inverse",
                help="Cumulative sleep debt (target: 8h/night)",
            )

    # Recent nights table
    st.subheader("📅 Recent Nights")

    nights_data = []
    for night in reversed(nights[-14:]):  # Last 14 nights
        if night.architecture:
            arch = night.architecture
            nights_data.append({
                "Date": night.recording_date.strftime("%Y-%m-%d"),
                "TST (h)": f"{arch.tst_minutes / 60:.1f}",
                "Efficiency": f"{arch.sleep_efficiency:.0f}%",
                "Deep": f"{arch.n3_pct:.0f}%",
                "REM": f"{arch.rem_pct:.0f}%",
                "Quality": f"{arch.quality_score:.0f}",
                "Source": night.source,
            })

    if nights_data:
        st.dataframe(pd.DataFrame(nights_data), width="stretch")


def render_hypnogram_section(nights: list[SleepNight]) -> None:
    """Render hypnogram visualization section.

    Args:
        nights: List of sleep nights.
    """
    st.header("📊 Hypnogram")

    if not nights:
        st.info("No sleep staging data available. Import data from Somfit Pro or other PSG sources for hypnogram visualization.")
        return

    # Night selector
    night_options = {
        f"{n.recording_date.strftime('%Y-%m-%d')} ({n.source})": i
        for i, n in enumerate(reversed(nights))
        if n.epochs
    }

    if not night_options:
        st.warning("No nights with epoch-level staging data. Consumer wearables may only provide summary metrics.")

        # Show summary visualization instead
        st.subheader("Sleep Stage Distribution (Summary)")

        for night in reversed(nights[-3:]):
            if night.architecture:
                with st.expander(f"📅 {night.recording_date.strftime('%Y-%m-%d')} - {night.source}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        pie_option = build_sleep_stages_pie(night.architecture)
                        st_echarts(pie_option, height="300px")
                    with col2:
                        radar_option = build_sleep_metrics_radar(night.architecture)
                        st_echarts(radar_option, height="300px")
        return

    selected = st.selectbox(
        "Select Night",
        options=list(night_options.keys()),
        key="hypnogram_night_select",
    )

    if selected:
        night_idx = night_options[selected]
        night = list(reversed(nights))[night_idx]

        # Generate hypnogram data
        hypnogram_data = generate_hypnogram_data(night)

        # Visualization options
        col1, col2 = st.columns(2)
        with col1:
            show_hr = st.checkbox("Show Heart Rate", value=True, key="hyp_show_hr")
        with col2:
            show_spo2 = st.checkbox("Show SpO2", value=True, key="hyp_show_spo2")

        # Render hypnogram
        hypnogram_option = build_hypnogram_echarts_option(
            hypnogram_data,
            title=f"Hypnogram - {night.recording_date}",
            show_hr=show_hr,
            show_spo2=show_spo2,
        )
        st_echarts(hypnogram_option, height="500px")

        # Sleep architecture details
        if night.architecture:
            st.subheader("Sleep Architecture")
            arch = night.architecture

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Sleep Time", f"{arch.tst_minutes / 60:.1f} hours")
                st.metric("Sleep Efficiency", f"{arch.sleep_efficiency:.1f}%")
                st.metric("Sleep Cycles", arch.sleep_cycles)
            with col2:
                st.metric("Sleep Latency", f"{arch.sol_minutes:.0f} min")
                st.metric("REM Latency", f"{arch.rem_latency_minutes:.0f} min")
                st.metric("WASO", f"{arch.waso_minutes:.0f} min")
            with col3:
                st.metric("Deep Sleep (N3)", f"{arch.n3_pct:.1f}%")
                st.metric("REM Sleep", f"{arch.rem_pct:.1f}%")
                st.metric("Awakenings", arch.n_awakenings)


def render_sleep_trends(summary: MultiNightSummary) -> None:
    """Render sleep trends visualization.

    Args:
        summary: Multi-night summary.
    """
    st.header("📈 Sleep Trends")

    if not summary or summary.n_nights < 3:
        st.info("Need at least 3 nights of data to show trends. Continue recording sleep data.")
        return

    # Metric selector
    metric = st.selectbox(
        "Select Metric",
        options=[
            ("tst_hours", "Total Sleep Time"),
            ("sleep_efficiency", "Sleep Efficiency"),
            ("n3_pct", "Deep Sleep %"),
            ("rem_pct", "REM Sleep %"),
            ("quality_score", "Quality Score"),
        ],
        format_func=lambda x: x[1],
        key="trend_metric_select",
    )

    # Render trend chart
    trend_option = build_multi_night_trend_chart(summary, metric=metric[0])
    st_echarts(trend_option, height="400px")

    # Trend interpretation
    if summary.n_nights >= 7:
        st.subheader("📊 Trend Analysis")

        col1, col2 = st.columns(2)
        with col1:
            if summary.tst_trend > 0.1:
                st.success("✅ Sleep duration is **increasing** - positive trend")
            elif summary.tst_trend < -0.1:
                st.warning("⚠️ Sleep duration is **decreasing** - consider sleep hygiene")
            else:
                st.info("➡️ Sleep duration is **stable**")

        with col2:
            if summary.efficiency_trend > 0.5:
                st.success("✅ Sleep efficiency is **improving**")
            elif summary.efficiency_trend < -0.5:
                st.warning("⚠️ Sleep efficiency is **declining**")
            else:
                st.info("➡️ Sleep efficiency is **stable**")


def render_safte_integration(nights: list[SleepNight], user: UserInfo | None) -> None:
    """Render SAFTE fatigue model integration.

    Args:
        nights: List of sleep nights.
        user: Current user info.
    """
    st.header("⚡ Fatigue Prediction (SAFTE Model)")

    if len(nights) < 3:
        st.info("""
        **Need at least 3 nights of sleep data for fatigue prediction.**

        The SAFTE (Sleep, Activity, Fatigue, and Task Effectiveness) model uses your
        sleep history to predict cognitive performance and fatigue levels throughout the day.
        """)
        return

    st.markdown("""
    The SAFTE model predicts cognitive effectiveness based on:
    - **Homeostatic process**: Sleep pressure accumulation during wakefulness
    - **Circadian process**: 24-hour biological rhythm
    - **Sleep inertia**: Grogginess after waking
    """)

    # Prepare sleep schedule
    sleep_schedule = prepare_safte_sleep_schedule(nights[-7:])  # Last 7 nights
    sleep_debt = compute_sleep_debt_for_safte(nights[-7:])

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Sleep Input Summary")
        if sleep_schedule:
            recent = sleep_schedule[-1]
            st.metric("Last Night Duration", f"{recent['duration_hours']:.1f}h")
            st.metric("Last Night Quality", f"{recent['quality']*100:.0f}%")
            st.metric("Cumulative Sleep Debt", f"{sleep_debt:.1f}h")

    with col2:
        st.subheader("Work Schedule")
        has_work = st.checkbox("Has work today", value=True, key="safte_has_work")
        if has_work:
            work_start = st.slider("Work Start", 0, 23, 8, key="safte_work_start")
            work_hours = st.slider("Work Duration (hours)", 1, 16, 8, key="safte_work_hours")
            cognitive_load = st.select_slider(
                "Cognitive Demand",
                options=["Low", "Medium", "High", "Critical"],
                value="Medium",
                key="safte_cognitive",
            )
            load_map = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
        else:
            work_start = 9
            work_hours = 0
            cognitive_load = "Low"
            load_map = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}

    # Run SAFTE prediction
    if st.button("🔮 Predict Fatigue", type="primary", key="run_safte"):
        with st.spinner("Running SAFTE model..."):
            try:
                # Build inputs
                user_profile = UserProfile(
                    age=user.age if user and user.age else 30,
                    sex=user.sex.lower() if user and user.sex else "other",
                )

                recent_sleep = sleep_schedule[-1] if sleep_schedule else {}
                sleep_input = SleepScheduleInput(
                    quality=recent_sleep.get("quality", 0.8),
                    duration=recent_sleep.get("duration_hours", 7.0),
                    bedtime=recent_sleep.get("bedtime_hour", 23),
                    waketime=recent_sleep.get("waketime_hour", 7),
                    total_sleep_debt=sleep_debt,
                )

                work_input = WorkScheduleInput(
                    has_work=has_work,
                    work_start=work_start,
                    work_end=(work_start + work_hours) % 24,
                    work_hours=work_hours,
                    cognitive_load=load_map.get(cognitive_load, 1),
                )

                result = run_integrated_fatigue_analysis(
                    user_profile=user_profile,
                    sleep_schedule=sleep_input,
                    work_schedule=work_input,
                    prediction_days=1,
                )

                # Display results
                st.subheader("📊 Fatigue Prediction Results")

                col1, col2 = st.columns(2)
                with col1:
                    analysis = result.analysis
                    st.metric("Average Performance", f"{analysis.get('avg', 0):.0f}%")
                    st.metric("Minimum Performance", f"{analysis.get('min', 0):.0f}%")
                    st.metric("Risk Level", result.risk_assessment.get("risk_level", "Unknown"))

                with col2:
                    zones = analysis.get("zones", [0, 0, 0, 0])
                    st.metric("Optimal Hours", f"{zones[0]}h", help=">80% effectiveness")
                    st.metric("Moderate Hours", f"{zones[1]}h", help="60-80% effectiveness")
                    st.metric("Impaired Hours", f"{zones[2] + zones[3]}h", help="<60% effectiveness")

                # Recommendations
                st.subheader("💡 Recommendations")
                for rec in result.recommendations:
                    st.markdown(f"- {rec}")

                # Performance chart
                if result.time_points and result.performances:
                    perf_df = pd.DataFrame({
                        "Hour": [t / 60 for t in result.time_points],
                        "Performance": result.performances,
                    })

                    perf_option = {
                        "title": {"text": "Predicted Cognitive Performance", "left": "center"},
                        "tooltip": {"trigger": "axis"},
                        "xAxis": {"type": "value", "name": "Hours from now"},
                        "yAxis": {"type": "value", "name": "Performance (%)", "min": 0, "max": 100},
                        "series": [{
                            "type": "line",
                            "data": [[row["Hour"], row["Performance"]] for _, row in perf_df.iterrows()],
                            "smooth": True,
                            "areaStyle": {"opacity": 0.3},
                            "markLine": {
                                "data": [
                                    {"yAxis": 80, "label": {"formatter": "Optimal"}},
                                    {"yAxis": 60, "label": {"formatter": "Moderate"}},
                                ],
                            },
                        }],
                    }
                    st_echarts(perf_option, height="400px")

            except Exception as e:
                st.error(f"Error running SAFTE model: {e}")
                _LOGGER.exception("SAFTE model error")


def render_quality_assessment(nights: list[SleepNight]) -> None:
    """Render sleep quality assessment section.

    Args:
        nights: List of sleep nights.
    """
    st.header("🎯 Quality Assessment")

    if not nights:
        st.info("No sleep data available for quality assessment.")
        return

    # Latest night quality
    latest = nights[-1] if nights else None
    if latest and latest.architecture:
        arch = latest.architecture

        st.subheader(f"Latest Night: {latest.recording_date}")

        col1, col2 = st.columns(2)

        with col1:
            # Quality gauge
            gauge_option = build_sleep_architecture_gauge(arch)
            st_echarts(gauge_option, height="250px")

        with col2:
            # Radar chart
            radar_option = build_sleep_metrics_radar(arch)
            st_echarts(radar_option, height="250px")

        # Quality interpretation
        st.subheader("📋 Quality Interpretation")

        interpretations = []

        # TST
        tst_hours = arch.tst_minutes / 60
        if tst_hours < 6:
            interpretations.append(("🔴", f"Short sleep ({tst_hours:.1f}h) - below recommended 7-9h"))
        elif tst_hours < 7:
            interpretations.append(("🟡", f"Borderline sleep ({tst_hours:.1f}h) - aim for 7+ hours"))
        elif tst_hours <= 9:
            interpretations.append(("🟢", f"Good sleep duration ({tst_hours:.1f}h)"))
        else:
            interpretations.append(("🟡", f"Long sleep ({tst_hours:.1f}h) - may indicate sleep issues"))

        # Efficiency
        if arch.sleep_efficiency >= 90:
            interpretations.append(("🟢", f"Excellent efficiency ({arch.sleep_efficiency:.0f}%)"))
        elif arch.sleep_efficiency >= 85:
            interpretations.append(("🟢", f"Good efficiency ({arch.sleep_efficiency:.0f}%)"))
        elif arch.sleep_efficiency >= 75:
            interpretations.append(("🟡", f"Fair efficiency ({arch.sleep_efficiency:.0f}%) - some fragmentation"))
        else:
            interpretations.append(("🔴", f"Low efficiency ({arch.sleep_efficiency:.0f}%) - significant fragmentation"))

        # Deep sleep
        if arch.n3_pct >= 15:
            interpretations.append(("🟢", f"Good deep sleep ({arch.n3_pct:.0f}%)"))
        elif arch.n3_pct >= 10:
            interpretations.append(("🟡", f"Borderline deep sleep ({arch.n3_pct:.0f}%)"))
        else:
            interpretations.append(("🔴", f"Low deep sleep ({arch.n3_pct:.0f}%) - recovery may be impaired"))

        # REM
        if arch.rem_pct >= 20:
            interpretations.append(("🟢", f"Good REM sleep ({arch.rem_pct:.0f}%)"))
        elif arch.rem_pct >= 15:
            interpretations.append(("🟡", f"Borderline REM ({arch.rem_pct:.0f}%)"))
        else:
            interpretations.append(("🔴", f"Low REM ({arch.rem_pct:.0f}%) - memory consolidation may be affected"))

        for icon, text in interpretations:
            st.markdown(f"{icon} {text}")


# ---------------------------------------------------------------------------
# Main tab function
# ---------------------------------------------------------------------------


def render_sleep_tab() -> None:
    """Render the complete Sleep Analysis tab."""
    if not IMPORTS_OK:
        st.error(f"Sleep analysis module not available: {IMPORT_ERROR}")
        return

    st.title("😴 Sleep Analysis")

    st.markdown("""
    **Comprehensive sleep analysis with medical-grade visualizations.**

    This module integrates data from multiple sources (Garmin, ActiGraph, Somfit Pro)
    to provide PSG-style hypnograms, sleep architecture metrics, and fatigue predictions.

    > ⚠️ **Note**: Some features require specific data sources. Consumer wearables provide
    > summary metrics, while PSG/EDF files enable full hypnogram visualization.
    """)

    # User login section (sidebar)
    user = _render_user_login_section()

    if not user:
        st.warning("👆 **Please log in using the sidebar to access your sleep data.**")

        st.markdown("""
        ### Getting Started

        1. **Create an account** using your ID number and name
        2. **Import sleep data** from your devices:
           - Garmin Connect wellness exports
           - ActiGraph accelerometer files
           - Somfit Pro EDF recordings
        3. **Analyze your sleep** with medical-grade visualizations

        Your data is stored locally in the `data/` folder for longitudinal tracking.
        """)
        return

    # Data management (sidebar)
    _render_data_management_section(user)
    _render_device_import_section(user)

    # Load nights from session state
    nights: list[SleepNight] = st.session_state.get(_SESSION_SLEEP_NIGHTS, [])
    summary: MultiNightSummary | None = st.session_state.get(_SESSION_MULTI_SUMMARY)

    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview",
        "🌙 Hypnogram",
        "📈 Trends",
        "⚡ Fatigue",
        "🎯 Quality",
    ])

    with tab1:
        render_sleep_overview(nights, summary)

    with tab2:
        render_hypnogram_section(nights)

    with tab3:
        render_sleep_trends(summary)

    with tab4:
        render_safte_integration(nights, user)

    with tab5:
        render_quality_assessment(nights)


# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------


def render_sleep_disclaimer() -> None:
    """Render sleep analysis disclaimer."""
    st.markdown("""
    ---
    ### ⚕️ Important Disclaimer

    This sleep analysis tool is intended for **research and educational purposes**.
    It is not a substitute for professional medical diagnosis.

    **Limitations:**
    - Consumer wearables provide estimates, not clinical measurements
    - Hypnogram visualization requires PSG-quality data (EDF files)
    - SAFTE model predictions are approximations

    **For clinical sleep assessment, consult a sleep medicine specialist.**

    ---
    *Developed by Dr. Diego Malpica, MD - Aerospace Medicine Specialist*
    *National University of Colombia | Colombian Aerospace Force*
    """)

