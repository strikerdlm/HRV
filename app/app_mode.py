from __future__ import annotations

"""Operational vs Research app-mode helpers.

This module centralizes:
- How we determine the current app mode (env + session state).
- Rendering a consistent mode badge/banner.
- Guard helpers to block research-only actions in operational mode.

Design goals:
- No Streamlit commands at import time (safe to import early).
- Deterministic, bounded behavior.
"""

import os
from enum import Enum
from typing import Final, Optional

import streamlit as st


class AppMode(str, Enum):
    OPERATIONAL = "operational"
    RESEARCH = "research"


_ENV_APP_MODE: Final[str] = "HRV_APP_MODE"
_SESSION_APP_MODE: Final[str] = "_hrv_app_mode"


def set_app_mode(mode: AppMode) -> None:
    """Set the current app mode for this Streamlit process/session."""

    os.environ[_ENV_APP_MODE] = mode.value
    st.session_state[_SESSION_APP_MODE] = mode.value


def get_app_mode(*, default: AppMode = AppMode.RESEARCH) -> AppMode:
    """Get the current app mode from session state and environment.

    Args:
        default: Mode to return when no valid mode is configured.
    """

    raw: Optional[str] = None
    try:
        raw = st.session_state.get(_SESSION_APP_MODE)
    except Exception:
        raw = None
    if not raw:
        raw = os.environ.get(_ENV_APP_MODE)
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value == AppMode.OPERATIONAL.value:
            return AppMode.OPERATIONAL
        if value == AppMode.RESEARCH.value:
            return AppMode.RESEARCH
    return default


def render_app_mode_badge(mode: Optional[AppMode] = None) -> None:
    """Render a compact badge describing the current app mode."""

    mode_to_use = mode or get_app_mode()
    is_operational = mode_to_use == AppMode.OPERATIONAL
    title = "Operational" if is_operational else "Research"
    subtitle = (
        "Fast clinical workflow • research features locked"
        if is_operational
        else "Full dashboards • computations/correlations/ML enabled"
    )
    color = "#22c55e" if is_operational else "#a855f7"
    bg = "#052e16" if is_operational else "#2e1065"
    border = "#16a34a" if is_operational else "#7c3aed"

    st.markdown(
        f"""
        <div style="
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:12px;
            padding:10px 14px;
            border-radius:14px;
            background:{bg};
            border:1px solid {border};
            margin:10px 0 14px 0;
        ">
            <div style="display:flex;align-items:center;gap:10px;">
                <div style="
                    width:10px;height:10px;border-radius:999px;background:{color};
                    box-shadow:0 0 12px {color};
                "></div>
                <div>
                    <div style="font-weight:800;color:white;line-height:1.2;">
                        Mode: {title}
                    </div>
                    <div style="color:rgba(255,255,255,0.82);font-size:0.9rem;">
                        {subtitle}
                    </div>
                </div>
            </div>
            <div style="color:rgba(255,255,255,0.7);font-size:0.85rem;">
                {_ENV_APP_MODE}={mode_to_use.value}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def require_research(feature_name: str) -> bool:
    """Guard a research-only feature.

    Returns True if the feature is allowed (research mode). If called in
    operational mode, it renders a user-facing message and returns False.
    """

    mode = get_app_mode()
    if mode == AppMode.RESEARCH:
        return True

    st.error(
        f"🔒 **{feature_name}** is disabled in **Operational** mode to keep the UI fast and stable.\n\n"
        "Run the Research app for correlations/ML dashboards."
    )
    st.code("streamlit run app/research_app.py")
    return False


