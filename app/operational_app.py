from __future__ import annotations

# Operational Streamlit entrypoint (fast UI).
#
# Run:
#   streamlit run app/operational_app.py

import logging
import os
import sys
from pathlib import Path
from typing import Any, Set

import streamlit as st

from logging_config import (
    enable_streamlit_debug,
    get_logger,
    log_rerun_trigger,
    setup_logging,
)

# Safe rerun utility with debouncing and circuit breaker
try:
    from rerun_utils import safe_rerun
except ImportError:  # pragma: no cover
    def safe_rerun(reason: str = "") -> None:  # type: ignore[misc]
        st.rerun()

_LOGGER = get_logger(__name__)


def _ensure_app_dir_on_path() -> None:
    """Ensure `app/` is on sys.path for intra-app absolute imports.

    Streamlit typically adds the script directory to `sys.path`, but this keeps
    behavior consistent when imported in tests/tools.
    """

    app_dir = Path(__file__).resolve().parent
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))


def _inject_sessioninfo_suppressor() -> None:
    """Hide only known Streamlit error toasts (safety net)."""

    st.markdown(
        """
        <style>
        div[data-testid="stToast"]:has([data-testid="stNotificationContentError"]),
        div[data-testid="stToastContainer"]:has([data-testid="stNotificationContentError"]) {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_crew_workspace_sidebar() -> None:
    """Render the mission-scoped workspace selector and enforce clean switching."""

    crew_root = Path(__file__).resolve().parents[1] / "crew"
    for mission_name in ("Mission 1", "Mission 2"):
        (crew_root / mission_name / "db").mkdir(parents=True, exist_ok=True)
        (crew_root / mission_name / "subjects").mkdir(parents=True, exist_ok=True)

    st.sidebar.subheader("🧑‍🚀 Crew workspace")
    active_mission = st.sidebar.selectbox(
        "Active mission",
        options=["Mission 1", "Mission 2"],
        index=0,
        key="crew_active_mission",
        help="Each mission uses its own DB and subject folders under the `crew/` directory.",
    )
    previous_mission = st.session_state.get("_crew_previous_mission")
    st.session_state["_crew_previous_mission"] = active_mission
    os.environ["HRV_ACTIVE_MISSION"] = str(active_mission)

    if previous_mission and previous_mission != active_mission:
        keep_keys: Set[str] = {"crew_active_mission", "_crew_previous_mission", "_debug_mode_enabled"}
        for key in list(st.session_state.keys()):
            if key not in keep_keys:
                st.session_state.pop(key, None)
        try:
            st.cache_data.clear()
            st.cache_resource.clear()
        except Exception:
            pass
        log_rerun_trigger("mission_switch", from_mission=previous_mission, to_mission=active_mission)
        safe_rerun("operational_app: mission_switch")


def _render_developer_tools_sidebar() -> None:
    st.sidebar.markdown("---")
    with st.sidebar.expander("🔧 Developer Tools", expanded=False):
        debug_mode = st.checkbox(
            "Enable Debug Logging",
            value=st.session_state.get("_debug_mode_enabled", False),
            key="_debug_mode_checkbox",
            help="Enable verbose Streamlit debugging. Logs written to logs/streamlit.log",
        )
        if debug_mode and not st.session_state.get("_debug_mode_enabled", False):
            st.session_state["_debug_mode_enabled"] = True
            enable_streamlit_debug(verbose=True)
            st.success("Debug logging enabled. Check `logs/streamlit.log`")
        elif not debug_mode and st.session_state.get("_debug_mode_enabled", False):
            st.session_state["_debug_mode_enabled"] = False
            st.info("Debug logging disabled (takes effect on next restart)")


def main() -> None:
    _ensure_app_dir_on_path()
    setup_logging(log_level_console=logging.DEBUG)
    enable_streamlit_debug(verbose=True)

    # Set app mode early for any downstream policy checks (no UI side effects).
    os.environ["HRV_APP_MODE"] = "operational"

    # MUST be the first Streamlit command (before importing modules that use Streamlit).
    try:
        st.set_page_config(page_title="HRV Analysis — Operational", layout="wide")
    except Exception:
        # Never crash the operational app due to page config ordering.
        pass

    # Mode badge (shared philosophy)
    try:
        from app_mode import AppMode, render_app_mode_badge, set_app_mode  # noqa: PLC0415

        set_app_mode(AppMode.OPERATIONAL)
        render_app_mode_badge(AppMode.OPERATIONAL)
    except Exception:
        # Badge is non-critical; keep operational flow stable.
        pass

    # Keep developer debug flag in sync (debug is always on by default).
    if "_debug_mode_enabled" not in st.session_state:
        st.session_state["_debug_mode_enabled"] = True

    # Delay-import UI modules until after page config to avoid StreamlitAPIException.
    try:
        from welcome_header import render_welcome_header  # noqa: PLC0415

        welcome_header_available = True
    except ImportError:  # pragma: no cover
        welcome_header_available = False
        render_welcome_header = None  # type: ignore[assignment]

    try:
        from user_profile_tab import render_user_profile_tab  # noqa: PLC0415

        user_profile_available = True
    except ImportError:  # pragma: no cover
        user_profile_available = False
        render_user_profile_tab = None  # type: ignore[assignment]

    try:
        from about_tab import render_about_tab  # noqa: PLC0415

        about_available = True
    except ImportError:  # pragma: no cover
        about_available = False
        render_about_tab = None  # type: ignore[assignment]

    try:
        from scheduling_tab import render_scheduling_tab, SCHEDULING_AVAILABLE  # noqa: PLC0415

        scheduling_available = SCHEDULING_AVAILABLE
    except ImportError:  # pragma: no cover
        scheduling_available = False
        render_scheduling_tab = None  # type: ignore[assignment]

    try:
        from experiments_tab import render_experiments_tab, EXPERIMENTS_TAB_AVAILABLE  # noqa: PLC0415

        experiments_available = EXPERIMENTS_TAB_AVAILABLE
    except ImportError:  # pragma: no cover
        experiments_available = False
        render_experiments_tab = None  # type: ignore[assignment]

    if "_app_session_ready" not in st.session_state:
        st.session_state["_app_session_ready"] = True

    _inject_sessioninfo_suppressor()
    st.set_option("client.showErrorDetails", True)

    _render_crew_workspace_sidebar()
    _render_developer_tools_sidebar()

    # Header (shared aesthetic)
    if welcome_header_available and render_welcome_header is not None:
        render_welcome_header()  # type: ignore[misc]
    else:
        st.title("🧬 Mission Control - Flight Surgeon")

    st.markdown("---")

    # Build navigation options dynamically based on available modules
    nav_options: list[str] = []
    if scheduling_available:
        nav_options.append("🗓️ Crew Scheduling")
    if experiments_available:
        nav_options.append("🔬 Experiments")
    if user_profile_available:
        nav_options.append("👤 User Profile")
    if about_available:
        nav_options.append("ℹ️ About")

    # Fallback if no modules available (shouldn't happen in practice)
    if not nav_options:
        st.error("No navigation modules available. Check application installation.")
        return

    page = st.sidebar.radio(
        "Navigation",
        options=nav_options,
        index=0,
        key="operational_nav",
    )

    if page == "🗓️ Crew Scheduling":
        if scheduling_available and render_scheduling_tab is not None:
            render_scheduling_tab()  # type: ignore[misc]
        else:
            st.error("Scheduling module unavailable (`scheduling_tab.py`).")
        return

    if page == "🔬 Experiments":
        if experiments_available and render_experiments_tab is not None:
            render_experiments_tab()  # type: ignore[misc]
        else:
            st.error("Experiments module unavailable (`experiments_tab.py`).")
        return

    if page == "👤 User Profile":
        if not user_profile_available or render_user_profile_tab is None:
            st.error("User Profile module unavailable (`user_profile_tab.py`).")
            return
        render_user_profile_tab()  # type: ignore[misc]
        return

    if page == "ℹ️ About":
        if about_available and render_about_tab is not None:
            render_about_tab()  # type: ignore[misc]
        else:
            st.info("About module unavailable (`about_tab.py`).")
        return

    st.info("Select a page from the sidebar.")


if __name__ == "__main__":
    main()


