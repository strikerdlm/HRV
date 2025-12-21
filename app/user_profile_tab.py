"""
User Profile Tab for Mission Control - Flight Surgeon.

Provides a centralized interface for:
- User registration and profile management
- Biometric data collection (age, weight, height, BMI)
- Clinical scale assessments (ESS, Samn-Perelli, KSS, PSQI, etc.)
- Historical data viewing and trends
- Data export/import

All data is stored in SQLite database with timestamped entries.
Supports English and Spanish (Colombian validated scales).

Author: AI Assistant
Version: 1.1.0
"""

from __future__ import annotations

import logging
import time
import uuid
import io
import os
from collections import Counter
from datetime import datetime, date, timezone, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Final, List, Optional, Sequence

import numpy as np
import pandas as pd
import streamlit as st

try:
    from logging_config import get_logger, log_exception
except ImportError:  # pragma: no cover - fallback if logging_config missing
    get_logger = None  # type: ignore[assignment]
    log_exception = None  # type: ignore[assignment]

# Import database module
try:
    from user_database import (
        UserProfile,
        ClinicalScales,
        HRVMeasurement,
        GarminDailyMetrics,
        BodyCompositionMeasurement,
        MeasurementTimepoint,
        UserDatabase,
        get_database,
        get_database_path,
        is_sqlite_database_corruption_error,
        list_database_backups,
        reset_database_file,
        restore_database_from_backup,
        sqlite_quick_check,
        get_cached_user_list,
        clear_user_cache,
    )
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    # Fallbacks for missing functions
    def get_cached_user_list() -> list:  # type: ignore[misc]
        return []
    def clear_user_cache() -> None:  # type: ignore[misc]
        pass

# Garmin Connect live import (optional)
try:
    from garmin_connect_service import (  # type: ignore
        GARMIN_LIB_AVAILABLE,
        GarminAuthError,
        fetch_garmin_daily_metrics,
        summarize_garmin_daily,
    )
except ImportError:  # pragma: no cover - optional
    GARMIN_LIB_AVAILABLE = False  # type: ignore[assignment]
    class GarminAuthError(RuntimeError):  # type: ignore[override]
        pass
    def fetch_garmin_daily_metrics(user_id: str, days: int = 14):  # type: ignore[misc]
        raise GarminAuthError("Garmin connect service unavailable.")
    def summarize_garmin_daily(records):  # type: ignore[misc]
        return {"count": 0}

# Import i18n module for translations
try:
    from i18n import (
        Language,
        get_current_language,
        set_language,
        t,
        get_epworth_translations,
        get_karolinska_translations,
        get_samn_perelli_translations,
        get_vas_translations,
        get_panas_translations,
        render_language_selector,
    )
    I18N_AVAILABLE = True
except ImportError:
    I18N_AVAILABLE = False
    # Fallback function if i18n not available
    def t(key: str, **kwargs: Any) -> str:  # type: ignore[misc]
        return key
    def get_panas_translations() -> dict:  # type: ignore[misc]
        return {}

# Cached loaders
@st.cache_data(ttl=60, max_entries=64, show_spinner=False)
def _load_clinical_history_cached(uid: str, limit: int) -> list:
    db = get_database()
    if not hasattr(db, "get_clinical_scales_history"):
        return []
    return [h.to_dict() for h in db.get_clinical_scales_history(uid, limit=limit)]

# Import multi-user session manager
try:
    from multi_user_session import (
        get_multi_user_manager,
        render_user_switcher,
        render_user_session_manager,
        MAX_CONCURRENT_USERS,
    )
    MULTI_USER_AVAILABLE = True
except ImportError:
    MULTI_USER_AVAILABLE = False
    def get_current_language() -> str:  # type: ignore[misc]
        return "en"

# Garmin wellness import (FIT/ZIP)
try:
    from garmin_import import (
        get_daily_physiology_summary,
        import_garmin_data,
        convert_fit_to_csv,
    )
    GARMIN_IMPORT_AVAILABLE = True
except ImportError:
    GARMIN_IMPORT_AVAILABLE = False

# NOAA / space-weather datasets (used for profile radiation + alert enrichment)
try:
    from noaa_space import load_noaa_space_data
    NOAA_SPACE_AVAILABLE = True
except ImportError:
    NOAA_SPACE_AVAILABLE = False

# Visualization helpers
from echarts_component import EChartsConfig, render_echarts
from gauge_builder import GaugeThresholds, build_two_ring_gauge, get_gauge_thresholds

# Import profile module
try:
    from user_profile import (
        EpworthSleepinessScale,
        SamnPerelliFatigueScale,
        KarolinskaSleeipinessScale,
        StanfordSleepinessScale,
        FatigueSeverityScale,
        PittsburghSleepQualityIndex,
        UserBiometricProfile,
        ClinicalAssessmentSession,
        Sex,
        ActivityLevel,
        ChronotypeCategory,
        OccupationType,
    )
    PROFILE_MODULE_AVAILABLE = True
except ImportError:
    PROFILE_MODULE_AVAILABLE = False

from user_data_manager import create_user_manager, get_user_data_path, parse_filename_date
from hrv_core import build_readiness_baseline, load_rr_intervals_from_text, readiness_from_pns

_LOGGER: Final[logging.Logger] = (
    get_logger(__name__) if get_logger is not None else logging.getLogger(__name__)
)

# Check for @st.fragment support (Streamlit 1.37+)
# NOTE: We disable fragments because they cause "SessionInfo before initialized"
# errors when used inside tabs or other conditional UI contexts.
# See: https://github.com/streamlit/streamlit/issues/8321
_HAS_FRAGMENT = False  # Disabled - fragments cause stability issues in this app


def _fragment_if_available(func: Any) -> Any:
    """Decorator that was intended to apply @st.fragment if available.
    
    DISABLED: Fragments cause "Bad message format: Tried to use SessionInfo 
    before it was initialized" errors when decorated functions are called 
    inside tabs or conditional UI blocks. This decorator is now a no-op.
    
    The performance benefit of partial reruns is not worth the stability cost
    in complex applications with nested UI contexts.
    """
    # Always return the function unchanged - fragments are disabled
    return func
def _session_ready_guard() -> bool:
    """Prevent render work before Streamlit session is fully initialized."""
    ready = st.session_state.get("_app_session_ready")
    if ready is None:
        st.session_state["_app_session_ready"] = True
        return False
    return True


_TIMEPOINT_ID_SESSION_PREFIX: Final[str] = "longitudinal_timepoint_id:"
_TIMEPOINT_LABEL_SESSION_PREFIX: Final[str] = "longitudinal_timepoint_label:"


def _timepoint_id_key(user_id: str) -> str:
    """Session-state key for the active longitudinal timepoint id."""
    return f"{_TIMEPOINT_ID_SESSION_PREFIX}{user_id}"


def _timepoint_label_key(user_id: str) -> str:
    """Session-state key for the active longitudinal timepoint label."""
    return f"{_TIMEPOINT_LABEL_SESSION_PREFIX}{user_id}"


def _build_timepoint_label_options() -> list[str]:
    """Return the bounded list of longitudinal timepoint labels."""
    options = ["— (Unassigned)", "T0_baseline"]
    options.extend([f"T{i}" for i in range(1, 22)])
    return options


def _render_longitudinal_timepoint_controls(user_id: str) -> Optional[str]:
    """Render longitudinal timepoint selection + persistence and return timepoint_id.

    Stores the selected timepoint id in Streamlit session state so other tabs
    (and the main analysis pipeline) can tag saved records consistently.
    """
    if not user_id:
        return None

    st.markdown("### 🧪 Longitudinal timepoint (T0–T21)")
    st.caption(
        "Select the study timepoint for new entries in this tab. "
        "Saved HRV measurements and assessments can be tagged to enable baseline/Δ analytics."
    )

    options = _build_timepoint_label_options()
    default_label = st.session_state.get(_timepoint_label_key(user_id), "— (Unassigned)")
    if default_label not in options:
        default_label = "— (Unassigned)"

    with st.form(f"longitudinal_timepoint_form_{user_id}"):
        label = st.selectbox(
            "Timepoint label",
            options=options,
            index=options.index(default_label),
            key=f"longitudinal_timepoint_label_select_{user_id}",
        )

        if label == "— (Unassigned)":
            st.info("New entries will not be linked to a study timepoint.")
            submitted = st.form_submit_button("Apply")
            if submitted:
                st.session_state[_timepoint_id_key(user_id)] = None
                st.session_state[_timepoint_label_key(user_id)] = label
            return st.session_state.get(_timepoint_id_key(user_id))

        # Load existing timepoint (if present) to prefill date/notes.
        try:
            db = get_database()
            existing = db.get_measurement_timepoint_by_label(user_id, label)
        except Exception:
            existing = None

        existing_date = None
        if existing is not None:
            try:
                existing_date = datetime.fromisoformat(existing.measurement_date).date()
            except ValueError:
                existing_date = None

        measurement_date = st.date_input(
            "Measurement date",
            value=existing_date or date.today(),
            key=f"longitudinal_timepoint_date_{user_id}",
        )
        notes = st.text_area(
            "Timepoint notes (optional)",
            value=existing.notes if existing is not None and existing.notes else "",
            max_chars=500,
            key=f"longitudinal_timepoint_notes_{user_id}",
        )
        is_baseline_default = label.startswith("T0")
        is_baseline = st.checkbox(
            "Mark as baseline (T0)",
            value=bool(existing.is_baseline) if existing is not None else is_baseline_default,
            key=f"longitudinal_timepoint_is_baseline_{user_id}",
        )

        submitted = st.form_submit_button("💾 Save / Apply timepoint", type="primary")
        if submitted:
            try:
                timepoint = MeasurementTimepoint(
                    timepoint_id=existing.timepoint_id if existing is not None else str(uuid.uuid4()),
                    user_id=user_id,
                    timepoint_label=label,
                    measurement_date=measurement_date.isoformat(),
                    measurement_number=0 if label.startswith("T0") else int(label[1:]) if label.startswith("T") and label[1:].isdigit() else None,
                    is_baseline=is_baseline,
                    notes=notes.strip() or None,
                )
                db.upsert_measurement_timepoint(timepoint)
                st.session_state[_timepoint_id_key(user_id)] = timepoint.timepoint_id
                st.session_state[_timepoint_label_key(user_id)] = label
                st.success(f"Timepoint applied: {label}")
            except Exception as exc:
                st.error(f"Failed to save timepoint: {exc}")

    return st.session_state.get(_timepoint_id_key(user_id))


def _format_series_label(name: str) -> str:
    """Convert internal column names to human-readable legend labels."""
    label = name.replace("_", " ").strip().title()
    replacements = {
        "Rmssd": "RMSSD",
        "Sdnn": "SDNN",
        "Pnn50": "pNN50",
        "Pnn20": "pNN20",
        "Hr": "HR",
        "Spo2": "SpO₂",
    }
    for key, value in replacements.items():
        label = label.replace(key, value)
    return label


def _format_axis_label(value: object, date_format: str) -> str:
    """Format timestamps or categorical values for ECharts axes."""
    if isinstance(value, pd.Timestamp):
        ts = value.tz_convert(timezone.utc) if value.tzinfo else value.tz_localize(timezone.utc)
        return ts.strftime(date_format)
    if isinstance(value, datetime):
        ts = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return ts.strftime(date_format)
    if isinstance(value, np.datetime64):
        ts = pd.Timestamp(value).tz_localize(timezone.utc)
        return ts.strftime(date_format)
    return str(value)


def _render_profile_line_chart(
    df: pd.DataFrame,
    *,
    title: str,
    y_axis_label: str,
    height_px: int = 320,
    date_format: str = "%Y-%m-%d",
) -> None:
    """Render a multi-series line chart with ECharts."""
    if df.empty:
        st.info("No data to visualize yet.")
        return
    chart_df = df.dropna(how="all")
    if chart_df.empty:
        st.info("No valid rows to plot.")
        return
    try:
        chart_df = chart_df.sort_index()
    except TypeError:
        pass  # Leave as-is when index types are mixed
    numeric_columns = [
        col for col in chart_df.columns if pd.api.types.is_numeric_dtype(chart_df[col])
    ]
    if not numeric_columns:
        st.info("No numeric series available for visualization.")
        return
    chart_df = chart_df[numeric_columns]
    x_labels = [_format_axis_label(val, date_format) for val in chart_df.index]
    series_payload = []
    for col in chart_df.columns:
        values = [
            None if pd.isna(val) else float(val)
            for val in chart_df[col].to_list()
        ]
        series_payload.append(
            {
                "name": _format_series_label(col),
                "type": "line",
                "smooth": True,
                "showSymbol": False,
                "connectNulls": False,
                "lineStyle": {"width": 2},
                "emphasis": {"focus": "series"},
                "data": values,
            }
        )
    legend_names = [s["name"] for s in series_payload if isinstance(s, dict) and "name" in s]
    y_label = str(y_axis_label or "Value")
    option = {
        # Title is intentionally omitted: Streamlit headings already carry the chart title,
        # and duplicating it inside ECharts is visually noisy in the app layout.
        "backgroundColor": "transparent",
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "confine": True,
        },
        "legend": {"type": "scroll", "top": 0, "left": 0, "right": 0},
        "grid": {"left": 60, "right": 20, "top": 30, "bottom": 60, "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": x_labels,
            "boundaryGap": False,
            "axisLabel": {"rotate": 0, "hideOverlap": True},
        },
        "yAxis": {"type": "value", "name": y_label, "scale": True, "nameGap": 45},
        "dataZoom": [
            {"type": "inside", "xAxisIndex": 0, "filterMode": "none"},
            {"type": "slider", "xAxisIndex": 0, "height": 22, "bottom": 10},
        ],
        "toolbox": {
            "right": 8,
            "top": 2,
            "feature": {
                "dataZoom": {"yAxisIndex": "none"},
                "restore": {},
                "saveAsImage": {"pixelRatio": 4, "name": title or "chart"},
            },
        },
        "series": series_payload,
        "aria": {
            "enabled": True,
            "label": {
                "description": (
                    f"{title}. X-axis shows {date_format} time labels. "
                    f"Y-axis shows {y_label}. Series: {', '.join(legend_names)}."
                )
            },
        },
    }
    render_echarts(option, height_px=height_px)
    st.caption(
        f"**What you're seeing:** A time series chart of **{', '.join(legend_names)}** over the x-axis (dates). "
        f"The y-axis shows **{y_label}** (units are indicated in the legend when mixed). "
        "Hover to inspect values; use the bottom slider (or scroll/drag) to zoom; use the toolbar to export a high-resolution image."
    )


def _render_profile_bar_chart(
    series: pd.Series,
    *,
    title: str,
    x_axis_label: str = "",
    y_axis_label: str = "Count",
    height_px: int = 320,
) -> None:
    """Render a categorical bar chart for frequency distributions."""
    if series.empty:
        st.info("No categorical data to display.")
        return
    counts = series.dropna()
    if counts.empty:
        st.info("No categorical data to display.")
        return
    x_labels = [str(idx) for idx in counts.index]
    y_values = [float(val) for val in counts.to_numpy(dtype=float)]
    option = {
        "title": {"text": title},
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 60, "right": 20, "top": 40, "bottom": 40},
        "xAxis": {"type": "category", "data": x_labels, "name": x_axis_label},
        "yAxis": {"type": "value", "name": y_axis_label},
        "series": [
            {
                "name": title,
                "type": "bar",
                "data": y_values,
                "itemStyle": {"color": "#2563eb"},
            }
        ],
    }
    render_echarts(option, height_px=height_px)


def _render_profile_scatter_chart(
    df: pd.DataFrame,
    *,
    x_col: str,
    y_col: str,
    title: str,
    x_axis_label: str,
    y_axis_label: str,
    height_px: int = 320,
    point_color: str = "#2563eb",
) -> None:
    """Render a numeric scatter chart with ECharts.

    Args:
        df: Input dataframe containing `x_col` and `y_col`.
        x_col: Column name for x-axis values.
        y_col: Column name for y-axis values.
        title: Chart title.
        x_axis_label: X-axis label.
        y_axis_label: Y-axis label.
        height_px: Height in pixels.
        point_color: Hex color string for points.
    """
    if df.empty:
        st.info("No data to visualize yet.")
        return
    if x_col not in df.columns or y_col not in df.columns:
        st.info("Required data not available for this chart.")
        return

    subset = df[[x_col, y_col]].copy()
    if not pd.api.types.is_numeric_dtype(subset[x_col]):
        subset[x_col] = pd.to_numeric(subset[x_col], errors="coerce")
    if not pd.api.types.is_numeric_dtype(subset[y_col]):
        subset[y_col] = pd.to_numeric(subset[y_col], errors="coerce")
    subset = subset.dropna()
    if subset.empty:
        st.info("No paired observations available yet.")
        return

    points = [[float(x), float(y)] for x, y in subset.to_numpy()]
    option = {
        "title": {"text": title},
        "tooltip": {"trigger": "item"},
        "grid": {"left": 70, "right": 20, "top": 50, "bottom": 55},
        "xAxis": {
            "type": "value",
            "name": x_axis_label,
            "nameLocation": "middle",
            "nameGap": 35,
            "scale": True,
        },
        "yAxis": {
            "type": "value",
            "name": y_axis_label,
            "nameLocation": "middle",
            "nameGap": 45,
            "scale": True,
        },
        "series": [
            {
                "type": "scatter",
                "data": points,
                "symbolSize": 7,
                "itemStyle": {"color": point_color},
            }
        ],
    }
    render_echarts(option, height_px=height_px)


def _profile_gauge_option(
    title: str,
    value: float,
    mu: float,
    sigma: float,
    vmin: float,
    vmax: float,
    unit: str,
) -> Dict[str, Any]:
    """Build an ECharts gauge option with Kubios-style color zones."""
    # Compute band thresholds
    lo = max(float(vmin), float(mu - sigma))
    hi = min(float(vmax), float(mu + sigma))
    span = max(1e-9, float(vmax - vmin))
    lo_r = max(0.0, min(1.0, (lo - float(vmin)) / span))
    hi_r = max(0.0, min(1.0, (hi - float(vmin)) / span))

    axis_colors = [[lo_r, "#e53935"], [hi_r, "#43a047"], [1.0, "#fb8c00"]]
    is_valid = bool(np.isfinite(value))
    plot_value = float(value) if is_valid else float(vmin)
    detail = f"{plot_value:.1f} {unit}".strip() if is_valid else f"n/a {unit}".strip()

    return {
        "title": {"text": title, "left": "center"},
        "series": [
            {
                "type": "gauge",
                "min": float(vmin),
                "max": float(vmax),
                "axisLine": {"lineStyle": {"width": 14, "color": axis_colors}},
                "pointer": {"width": 4},
                "splitNumber": 8,
                "progress": {"show": False},
                "detail": {"formatter": detail, "fontSize": 14},
                "data": [{"value": plot_value}],
            }
        ],
    }


def _render_profile_hrv_metric_gauges(
    row: pd.Series,
    *,
    key_suffix: str,
) -> None:
    """Render the same HRV metric gauges used in the main analysis tab."""
    # Anchors from Normative.md (short-term ~5 min)
    sdnn_mu, sdnn_sigma = 50.0, 16.0
    rmssd_mu, rmssd_sigma = 42.0, 15.0
    lfhf_mu, lfhf_sigma = 2.8, 2.6
    hf_mu, hf_sigma = 657.0, 777.0

    # Values (profile DB uses *_ms and *_ms2 naming)
    sdnn = float(row.get("sdnn_ms", np.nan))
    rmssd = float(row.get("rmssd_ms", np.nan))
    lfhf = float(row.get("lf_hf_ratio", np.nan))
    hf_power = float(row.get("hf_power_ms2", np.nan))

    sdnn_vmin, sdnn_vmax = 0.0, 120.0
    rmssd_vmin, rmssd_vmax = 0.0, 100.0
    lfhf_vmin, lfhf_vmax = 0.0, 12.0
    hf_vmin, hf_vmax = 0.0, float(
        max(
            hf_mu + 3 * hf_sigma,
            (hf_power if np.isfinite(hf_power) else 0.0) * 1.5,
            3000.0,
        )
    )

    cols = st.columns(2)
    with cols[0]:
        render_echarts(
            _profile_gauge_option(
                "SDNN (ms)",
                sdnn,
                sdnn_mu,
                sdnn_sigma,
                sdnn_vmin,
                sdnn_vmax,
                "ms",
            ),
            height_px=300,
            config=EChartsConfig(),
        )
    with cols[1]:
        render_echarts(
            _profile_gauge_option(
                "RMSSD (ms)",
                rmssd,
                rmssd_mu,
                rmssd_sigma,
                rmssd_vmin,
                rmssd_vmax,
                "ms",
            ),
            height_px=300,
            config=EChartsConfig(),
        )

    cols2 = st.columns(2)
    with cols2[0]:
        render_echarts(
            _profile_gauge_option(
                "LF/HF (ratio)",
                lfhf,
                lfhf_mu,
                lfhf_sigma,
                lfhf_vmin,
                lfhf_vmax,
                "",
            ),
            height_px=300,
            config=EChartsConfig(),
        )
    with cols2[1]:
        render_echarts(
            _profile_gauge_option(
                "HF Power (ms²)",
                hf_power,
                hf_mu,
                hf_sigma,
                hf_vmin,
                hf_vmax,
                "ms²",
            ),
            height_px=300,
            config=EChartsConfig(),
        )

    st.caption(
        "Bands reflect mean ± SD from short-term (∼5 min) references; see Normative.md for details and caveats."
    )


# ---------------------------------------------------------------------------
# Session State Keys
# ---------------------------------------------------------------------------

_SESSION_CURRENT_USER = "current_user_profile"
_SESSION_USER_ID = "current_user_id"
_SESSION_SHOW_REGISTRATION = "show_registration_form"
_FORM_DEBOUNCE_PREFIX: Final[str] = "form_debounce_key_"
_FORM_DEBOUNCE_SECONDS: Final[float] = 0.8


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _get_current_user() -> Optional[UserProfile]:
    """Get currently logged-in user from session state."""
    return st.session_state.get(_SESSION_CURRENT_USER)


def _set_current_user(user: Optional[UserProfile]) -> None:
    """Set current user in session state, sync language, and register in multi-user manager."""
    st.session_state[_SESSION_CURRENT_USER] = user
    if user:
        st.session_state[_SESSION_USER_ID] = user.user_id
        # Sync language preference from user profile
        if I18N_AVAILABLE and hasattr(user, 'language') and user.language:
            try:
                from i18n import Language, set_language
                lang = Language(user.language)
                set_language(lang)
            except (ValueError, ImportError):
                pass  # Keep current language if invalid
        
        # Register in multi-user session manager
        if MULTI_USER_AVAILABLE:
            try:
                manager = get_multi_user_manager()
                manager.add_user_session(
                    user_id=user.user_id,
                    username=user.username,
                    full_name=user.full_name or user.username,
                    make_active=True,
                )
            except Exception:
                pass  # Continue even if multi-user registration fails


def _should_process_form_submission(form_key: str, debounce_seconds: float = _FORM_DEBOUNCE_SECONDS) -> bool:
    """Prevent duplicate form submissions within a short interval."""
    state_key = f"{_FORM_DEBOUNCE_PREFIX}{form_key}"
    now = time.monotonic()
    last_submission = st.session_state.get(state_key, 0.0)
    if now - last_submission < debounce_seconds:
        return False
    st.session_state[state_key] = now
    return True


def _calculate_age(dob_str: Optional[str]) -> Optional[int]:
    """Calculate age from date of birth string (YYYY-MM-DD)."""
    if not dob_str:
        return None
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        today = date.today()
        age = today.year - dob.year
        if (today.month, today.day) < (dob.month, dob.day):
            age -= 1
        return age
    except ValueError:
        return None


def _calculate_bmi(height_cm: Optional[float], weight_kg: Optional[float]) -> Optional[float]:
    """Calculate BMI from height and weight."""
    if not height_cm or not weight_kg or height_cm <= 0:
        return None
    height_m = height_cm / 100.0
    return weight_kg / (height_m ** 2)


def _bmi_category(bmi: Optional[float]) -> str:
    """Get BMI category according to WHO classification."""
    if bmi is None:
        return "Unknown"
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25.0:
        return "Normal"
    if bmi < 30.0:
        return "Overweight"
    if bmi < 35.0:
        return "Obese I"
    if bmi < 40.0:
        return "Obese II"
    return "Obese III"


def _safe_float(value: Any) -> Optional[float]:
    """Convert to float if valid, otherwise None."""
    if value is None:
        return None
    try:
        if isinstance(value, (float, int)) and (pd.isna(value)):
            return None
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> Optional[int]:
    """Convert to int if valid, otherwise None."""
    if value is None:
        return None
    try:
        if isinstance(value, (float, int)) and (pd.isna(value)):
            return None
        return int(value)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# User Registration Form
# ---------------------------------------------------------------------------


def _render_registration_form() -> Optional[UserProfile]:
    """Render new user registration form."""
    st.markdown("### 📝 New User Registration")
    
    with st.form("registration_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input(
                "Username *",
                max_chars=50,
                help="Unique identifier for login",
            )
            full_name = st.text_input(
                "Full Name *",
                max_chars=100,
            )
            email = st.text_input(
                "Email",
                max_chars=100,
            )
            password = st.text_input(
                "Password",
                type="password",
                help="Optional - for multi-user setups",
            )
        
        with col2:
            date_of_birth = st.date_input(
                "Date of Birth",
                value=date(1990, 1, 1),
                min_value=date(1920, 1, 1),
                max_value=date.today(),
            )
            sex = st.selectbox(
                "Biological Sex",
                options=["male", "female", "other"],
                index=0,
            )
            occupation = st.selectbox(
                "Occupation Type",
                options=[
                    "pilot", "atc", "flight_crew", "medical",
                    "shift_worker", "military", "driver", "researcher",
                    "office", "other"
                ],
                index=9,
                format_func=lambda x: x.replace("_", " ").title(),
            )
        
        st.markdown("#### 📏 Anthropometrics")
        col_h, col_w = st.columns(2)
        with col_h:
            height_cm = st.number_input(
                "Height (cm)",
                min_value=100.0,
                max_value=250.0,
                value=170.0,
                step=0.5,
            )
        with col_w:
            weight_kg = st.number_input(
                "Weight (kg)",
                min_value=30.0,
                max_value=300.0,
                value=70.0,
                step=0.5,
            )
        
        # Show calculated BMI
        bmi = _calculate_bmi(height_cm, weight_kg)
        if bmi:
            st.caption(f"**BMI**: {bmi:.1f} kg/m² ({_bmi_category(bmi)})")
        
        st.markdown("#### 💪 Fitness & Lifestyle")
        col_hr, col_vo2 = st.columns(2)
        with col_hr:
            resting_hr = st.number_input(
                "Resting Heart Rate (bpm)",
                min_value=30,
                max_value=120,
                value=65,
                step=1,
            )
        with col_vo2:
            vo2max = st.number_input(
                "VO2max (ml/kg/min)",
                min_value=0.0,
                max_value=90.0,
                value=0.0,
                step=0.5,
                help="Leave 0 if unknown - will be estimated",
            )
        
        activity_level = st.select_slider(
            "Activity Level",
            options=["Sedentary", "Light", "Moderate", "Active", "Very Active"],
            value="Moderate",
        )
        
        submit = st.form_submit_button("✅ Create Profile")
        
        if submit:
            if not username or not full_name:
                st.error("Username and Full Name are required.")
                return None
            
            # Create profile
            profile = UserProfile(
                user_id=str(uuid.uuid4()),
                username=username.lower().strip(),
                full_name=full_name.strip(),
                email=email.strip() if email else None,
                date_of_birth=date_of_birth.isoformat() if date_of_birth else None,
                sex=sex,
                height_cm=float(height_cm),
                weight_kg=float(weight_kg),
                resting_hr_bpm=float(resting_hr),
                max_hr_bpm=None,
                vo2max_ml_kg_min=float(vo2max) if vo2max > 0 else None,
                occupation=occupation,
                activity_level=activity_level.lower().replace(" ", "_"),
            )
            
            try:
                db = get_database()
                # Optimized: check and create in single transaction
                user_id, created = db.create_user_if_not_exists(
                    profile,
                    password if password else None,
                )
                
                if not created:
                    st.error(f"Username '{profile.username}' already exists.")
                    return None
                
                # Clear user cache after successful creation
                clear_user_cache()
                
                st.success(f"✅ Profile created for {full_name}!")
                return profile
                
            except Exception as exc:
                st.error(f"Failed to create profile: {exc}")
                return None
    
    return None


# ---------------------------------------------------------------------------
# User Login
# ---------------------------------------------------------------------------


def _render_login_section() -> Optional[UserProfile]:
    """Render user login/selection section."""
    # Use cached user list for better performance
    cached_users = get_cached_user_list()
    
    if not cached_users:
        st.info("No users registered. Create a new profile below.")
        return None
    
    st.markdown("### 🔑 Select or Login")
    
    col_select, col_action = st.columns([3, 1])
    
    with col_select:
        # Build options from cached data (avoiding full DB query)
        user_options = {u["username"]: u for u in cached_users}
        selected_username = st.selectbox(
            "Select User",
            options=list(user_options.keys()),
            format_func=lambda x: f"{user_options[x]['full_name']} (@{x})",
        )
    
    with col_action:
        st.write("")  # Spacing
        if st.button("✅ Select User", use_container_width=True):
            selected_data = user_options.get(selected_username)
            if selected_data:
                # Fetch full user profile only when needed
                db = get_database()
                user = db.get_user(selected_data["user_id"])
                if user:
                    _set_current_user(user)
                    st.success(f"Logged in as {user.full_name}")
                    st.rerun()
    
    return None


# ---------------------------------------------------------------------------
# Profile Display & Edit
# ---------------------------------------------------------------------------


def _render_profile_view(user: UserProfile) -> None:
    """Render user profile view with edit option."""
    
    st.markdown(f"### 👤 {user.full_name}")
    st.caption(f"@{user.username} • User ID: {user.user_id[:8]}...")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    age = _calculate_age(user.date_of_birth)
    with col1:
        st.metric("Age", f"{age} years" if age else "—")
    
    bmi = _calculate_bmi(user.height_cm, user.weight_kg)
    with col2:
        st.metric("BMI", f"{bmi:.1f}" if bmi else "—", _bmi_category(bmi) if bmi else None)
    
    with col3:
        st.metric("Resting HR", f"{user.resting_hr_bpm:.0f} bpm" if user.resting_hr_bpm else "—")
    
    with col4:
        # Estimated max HR using Tanaka formula
        max_hr = 208 - (0.7 * age) if age else None
        st.metric("Est. Max HR", f"{max_hr:.0f} bpm" if max_hr else "—")
    
    # Details expander
    with st.expander("📋 Full Profile Details"):
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("**Personal Information**")
            st.write(f"- **Sex**: {user.sex or '—'}")
            st.write(f"- **Date of Birth**: {user.date_of_birth or '—'}")
            st.write(f"- **Email**: {user.email or '—'}")
            st.write(f"- **Occupation**: {user.occupation or '—'}")
            
        with col_b:
            st.markdown("**Anthropometrics**")
            st.write(f"- **Height**: {user.height_cm:.1f} cm" if user.height_cm else "- **Height**: —")
            st.write(f"- **Weight**: {user.weight_kg:.1f} kg" if user.weight_kg else "- **Weight**: —")
            st.write(f"- **Activity Level**: {user.activity_level or '—'}")
            st.write(f"- **VO2max**: {user.vo2max_ml_kg_min:.1f} ml/kg/min" if user.vo2max_ml_kg_min else "- **VO2max**: —")
        
        st.markdown("---")
        st.caption(f"Created: {user.created_at[:10] if user.created_at else '—'} | Updated: {user.updated_at[:10] if user.updated_at else '—'}")
    
    # Edit profile button
    if st.button("✏️ Edit Profile"):
        st.session_state["edit_profile_mode"] = True
        st.rerun()


def _render_profile_edit(user: UserProfile) -> None:
    """Render profile edit form."""
    st.markdown("### ✏️ Edit Profile")
    
    with st.form("edit_profile_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input("Full Name", value=user.full_name or "")
            email = st.text_input("Email", value=user.email or "")
            
            # Parse date
            dob_value = date(1990, 1, 1)
            if user.date_of_birth:
                try:
                    dob_value = datetime.strptime(user.date_of_birth, "%Y-%m-%d").date()
                except ValueError:
                    pass
            
            date_of_birth = st.date_input("Date of Birth", value=dob_value)
            sex = st.selectbox(
                "Sex",
                options=["male", "female", "other"],
                index=["male", "female", "other"].index(user.sex) if user.sex in ["male", "female", "other"] else 0,
            )
        
        with col2:
            height_cm = st.number_input("Height (cm)", value=user.height_cm or 170.0, min_value=100.0, max_value=250.0)
            weight_kg = st.number_input("Weight (kg)", value=user.weight_kg or 70.0, min_value=30.0, max_value=300.0)
            resting_hr = st.number_input("Resting HR (bpm)", value=int(user.resting_hr_bpm or 65), min_value=30, max_value=120)
            vo2max = st.number_input(
                "VO2max (ml/kg/min)",
                value=user.vo2max_ml_kg_min or 0.0,
                min_value=0.0,
                max_value=90.0,
            )
        
        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.form_submit_button("💾 Save Changes"):
                user.full_name = full_name
                user.email = email
                user.date_of_birth = date_of_birth.isoformat()
                user.sex = sex
                user.height_cm = height_cm
                user.weight_kg = weight_kg
                user.resting_hr_bpm = resting_hr
                user.vo2max_ml_kg_min = vo2max if vo2max > 0 else None
                
                try:
                    db = get_database()
                    db.update_user(user)
                    st.session_state["edit_profile_mode"] = False
                    st.success("Profile updated!")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Failed to update: {exc}")
        
        with col_cancel:
            if st.form_submit_button("❌ Cancel"):
                st.session_state["edit_profile_mode"] = False
                st.rerun()


# ---------------------------------------------------------------------------
# Clinical Scales Forms
# ---------------------------------------------------------------------------


def _render_epworth_form(user_id: str) -> Optional[int]:
    """Render Epworth Sleepiness Scale form with i18n support.
    
    Uses st.session_state to aggregate slider values without triggering full reruns.
    """
    # Get translations for current language
    if I18N_AVAILABLE:
        tr = get_epworth_translations()
    else:
        tr = {
            "title": "Epworth Sleepiness Scale (ESS)",
            "subtitle": "Rate your chance of dozing off in each situation (0-3)",
            "help": "0 = Never doze, 3 = High chance of dozing",
            "situations": [
                ("sitting_reading", "Sitting and reading"),
                ("watching_tv", "Watching TV"),
                ("sitting_inactive_public", "Sitting inactive in a public place"),
                ("passenger_car_hour", "As a passenger in a car for an hour"),
                ("lying_down_afternoon", "Lying down to rest in the afternoon"),
                ("sitting_talking", "Sitting and talking to someone"),
                ("sitting_quietly_after_lunch", "Sitting quietly after lunch (no alcohol)"),
                ("car_stopped_traffic", "In a car, while stopped in traffic"),
            ],
            "interpretation": {
                "normal": "Normal daytime sleepiness",
                "mild": "Mild excessive daytime sleepiness",
                "moderate": "Moderate excessive daytime sleepiness",
                "severe": "Severe excessive daytime sleepiness",
            },
            "warning": "Score >10 suggests excessive daytime sleepiness. Consider sleep evaluation.",
        }
    
    st.markdown(f"#### {tr['title']}")
    st.caption(tr['subtitle'])
    
    situations = tr['situations']
    
    # Use select_slider for smoother interaction (fewer DOM updates)
    scores: Dict[str, int] = {}
    
    cols_per_row = 2
    for i in range(0, len(situations), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, (key, label) in enumerate(situations[i:i + cols_per_row]):
            with cols[j]:
                slider_key = f"ess_{key}"
                # Pre-initialize session state for smoother behavior
                if slider_key not in st.session_state:
                    st.session_state[slider_key] = 0
                scores[key] = st.select_slider(
                    label,
                    options=[0, 1, 2, 3],
                    value=st.session_state.get(slider_key, 0),
                    key=slider_key,
                    help=tr['help'],
                )
    
    total = sum(scores.values())
    
    # Interpretation using translations
    interp_labels = tr.get('interpretation', {})
    if total <= 5:
        interp = interp_labels.get("normal", "Normal daytime sleepiness")
        color = "green"
    elif total <= 10:
        interp = interp_labels.get("normal", "Normal daytime sleepiness")
        color = "green"
    elif total <= 12:
        interp = interp_labels.get("mild", "Mild excessive daytime sleepiness")
        color = "orange"
    elif total <= 15:
        interp = interp_labels.get("moderate", "Moderate excessive daytime sleepiness")
        color = "orange"
    else:
        interp = interp_labels.get("severe", "Severe excessive daytime sleepiness")
        color = "red"
    
    total_label = tr.get('total_score', 'Total Score')
    st.markdown(f"**{total_label}: {total}/24** — :{color}[{interp}]")
    
    if total > 10:
        st.warning(f"⚠️ {tr.get('warning', 'Score >10 suggests excessive daytime sleepiness.')}")
    
    return total


def _render_samn_perelli_form(user_id: str) -> Optional[int]:
    """Render Samn-Perelli Fatigue Scale form with i18n support."""
    # Get translations for current language
    if I18N_AVAILABLE:
        tr = get_samn_perelli_translations()
    else:
        tr = {
            "title": "Samn-Perelli Fatigue Scale",
            "subtitle": "Select the statement that best describes your current state",
            "current_state": "Current fatigue state:",
            "options": {
                1: "1 - Fully alert, wide awake",
                2: "2 - Very lively, responsive, but not at peak",
                3: "3 - Okay, somewhat fresh",
                4: "4 - A little tired, less than fresh",
                5: "5 - Moderately tired, let down",
                6: "6 - Extremely tired, very difficult to concentrate",
                7: "7 - Completely exhausted, unable to function effectively",
            },
            "risk_level": "Operational Risk Level",
            "risk_levels": {"LOW": "LOW", "MODERATE": "MODERATE", "HIGH": "HIGH", "CRITICAL": "CRITICAL"},
            "warning": "Fatigue level may impair performance. Consider rest before safety-critical tasks.",
        }
    
    st.markdown(f"#### {tr['title']}")
    st.caption(tr['subtitle'])
    
    options = tr['options']
    
    rating = st.radio(
        tr['current_state'],
        options=list(options.keys()),
        format_func=lambda x: options[x],
        horizontal=False,
        key="samn_perelli_rating",
    )
    
    # Risk level with translations
    risk_labels = tr.get('risk_levels', {})
    if rating <= 2:
        risk_key = "LOW"
        color = "green"
    elif rating <= 4:
        risk_key = "MODERATE"
        color = "orange"
    elif rating <= 5:
        risk_key = "HIGH"
        color = "red"
    else:
        risk_key = "CRITICAL"
        color = "red"
    
    risk_display = risk_labels.get(risk_key, risk_key)
    risk_label = tr.get('risk_level', 'Operational Risk Level')
    st.markdown(f"**{risk_label}: :{color}[{risk_display}]**")
    
    if rating >= 5:
        st.error(f"⚠️ {tr.get('warning', 'Fatigue level may impair performance.')}")
    
    return rating


def _render_kss_form(user_id: str) -> Optional[int]:
    """Render Karolinska Sleepiness Scale form with i18n support."""
    # Get translations for current language
    if I18N_AVAILABLE:
        tr = get_karolinska_translations()
    else:
        tr = {
            "title": "Karolinska Sleepiness Scale (KSS)",
            "subtitle": "Rate your current sleepiness level",
            "current_sleepiness": "Current sleepiness:",
            "options": {
                1: "1 - Extremely alert",
                2: "2 - Very alert",
                3: "3 - Alert",
                4: "4 - Fairly alert",
                5: "5 - Neither alert nor sleepy",
                6: "6 - Some signs of sleepiness",
                7: "7 - Sleepy, but no effort to stay awake",
                8: "8 - Sleepy, some effort to stay awake",
                9: "9 - Extremely sleepy, fighting sleep",
            },
            "warning": "KSS ≥7 indicates significant sleepiness that may impair performance.",
        }
    
    st.markdown(f"#### {tr['title']}")
    st.caption(tr['subtitle'])
    
    options = tr['options']
    
    rating = st.radio(
        tr['current_sleepiness'],
        options=list(options.keys()),
        format_func=lambda x: options[x],
        horizontal=False,
        key="kss_rating",
    )
    
    if rating >= 7:
        st.warning(f"⚠️ {tr.get('warning', 'KSS ≥7 indicates significant sleepiness.')}")
    
    return rating


def _render_vas_scales(user_id: str) -> Dict[str, float]:
    """Render Visual Analog Scale assessments with i18n support."""
    # Get translations for current language
    if I18N_AVAILABLE:
        tr = get_vas_translations()
    else:
        tr = {
            "title": "Visual Analog Scales (VAS)",
            "subtitle": "Rate your current state on a 0-10 scale",
            "fatigue": "Fatigue (0 = None, 10 = Extreme)",
            "pain": "Pain (0 = None, 10 = Worst imaginable)",
        }
    
    st.markdown(f"#### {tr['title']}")
    st.caption(tr['subtitle'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        vas_fatigue = st.slider(
            tr['fatigue'],
            min_value=0.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
            key="vas_fatigue",
        )
    
    with col2:
        vas_pain = st.slider(
            tr['pain'],
            min_value=0.0,
            max_value=10.0,
            value=0.0,
            step=0.5,
            key="vas_pain",
        )
    
    return {"vas_fatigue": vas_fatigue, "vas_pain": vas_pain}


def _render_panas_form(user_id: str) -> Dict[str, Optional[int]]:
    """Render PANAS (Positive and Negative Affect Schedule) form with i18n support.
    
    Returns PA and NA scores (10-50 each) based on Watson, Clark & Tellegen (1988).
    Spanish validation: Sandín et al. (1999), Psicothema.
    """
    # Get translations for current language
    if I18N_AVAILABLE:
        tr = get_panas_translations()
    else:
        tr = {
            "title": "Positive and Negative Affect Schedule (PANAS)",
            "subtitle": "Indicate to what extent you feel this way right now",
            "response_options": {1: "Very slightly", 2: "A little", 3: "Moderately", 4: "Quite a bit", 5: "Extremely"},
            "pa_items": [
                ("interested", "Interested"), ("excited", "Excited"), ("strong", "Strong"),
                ("enthusiastic", "Enthusiastic"), ("proud", "Proud"), ("alert", "Alert"),
                ("inspired", "Inspired"), ("determined", "Determined"), ("attentive", "Attentive"),
                ("active", "Active"),
            ],
            "na_items": [
                ("distressed", "Distressed"), ("upset", "Upset"), ("guilty", "Guilty"),
                ("scared", "Scared"), ("hostile", "Hostile"), ("irritable", "Irritable"),
                ("ashamed", "Ashamed"), ("nervous", "Nervous"), ("jittery", "Jittery"),
                ("afraid", "Afraid"),
            ],
            "pa_label": "Positive Affect (PA)",
            "na_label": "Negative Affect (NA)",
            "score_range": "Score range: 10–50",
            "interpretation": {
                "pa_high": "High positive affect",
                "pa_moderate": "Moderate positive affect",
                "pa_low": "Low positive affect",
                "na_high": "High negative affect",
                "na_moderate": "Moderate negative affect",
                "na_low": "Low negative affect",
            },
            "reference": "Watson, Clark, & Tellegen (1988)",
            "clinical_note": (
                "PA and NA are largely independent dimensions. "
                "High NA is associated with anxiety/depression; low PA is specifically linked to depression "
                "(Watson, Clark, & Tellegen, 1988)."
            ),
        }
    
    st.markdown(f"#### {tr['title']}")
    st.caption(tr['subtitle'])
    
    response_opts = tr['response_options']
    pa_items = tr['pa_items']
    na_items = tr['na_items']
    
    # Pre-initialize session state for smoother behavior
    for key, _ in pa_items + na_items:
        state_key = f"panas_{key}"
        if state_key not in st.session_state:
            st.session_state[state_key] = 3  # Default to "Moderately"
    
    # Create two columns for PA and NA
    col_pa, col_na = st.columns(2)
    
    pa_scores: Dict[str, int] = {}
    na_scores: Dict[str, int] = {}
    
    with col_pa:
        st.markdown(f"**{tr['pa_label']}** 🌟")
        for key, label in pa_items:
            state_key = f"panas_{key}"
            pa_scores[key] = st.select_slider(
                label,
                options=list(response_opts.keys()),
                value=st.session_state.get(state_key, 3),
                format_func=lambda x: f"{x}",
                key=state_key,
                help=response_opts.get(st.session_state.get(state_key, 3), ""),
            )
    
    with col_na:
        st.markdown(f"**{tr['na_label']}** ⚡")
        for key, label in na_items:
            state_key = f"panas_{key}"
            na_scores[key] = st.select_slider(
                label,
                options=list(response_opts.keys()),
                value=st.session_state.get(state_key, 3),
                format_func=lambda x: f"{x}",
                key=state_key,
                help=response_opts.get(st.session_state.get(state_key, 3), ""),
            )
    
    # Calculate totals
    pa_total = sum(pa_scores.values())
    na_total = sum(na_scores.values())
    
    # Interpretation thresholds (based on normative data from Crawford & Henry, 2004)
    # PA: Mean ~31, SD ~8 → Low <23, Moderate 23-39, High >39
    # NA: Mean ~16, SD ~6 → Low <10, Moderate 10-22, High >22
    interp = tr.get('interpretation', {})
    
    if pa_total >= 40:
        pa_interp = interp.get("pa_high", "High positive affect")
        pa_color = "green"
    elif pa_total >= 23:
        pa_interp = interp.get("pa_moderate", "Moderate positive affect")
        pa_color = "blue"
    else:
        pa_interp = interp.get("pa_low", "Low positive affect")
        pa_color = "orange"
    
    if na_total >= 23:
        na_interp = interp.get("na_high", "High negative affect")
        na_color = "red"
    elif na_total >= 10:
        na_interp = interp.get("na_moderate", "Moderate negative affect")
        na_color = "orange"
    else:
        na_interp = interp.get("na_low", "Low negative affect")
        na_color = "green"
    
    st.markdown("---")
    
    # Display results with gauges using ECharts
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        _render_panas_gauge(
            value=pa_total,
            title=tr['pa_label'],
            min_val=10,
            max_val=50,
            color_zones=[
                (23, "#ff9800"),  # Low (orange)
                (40, "#2196f3"),  # Moderate (blue)
                (50, "#4caf50"),  # High (green)
            ],
            key_suffix="pa",
        )
        st.markdown(f"**PA: {pa_total}/50** — :{pa_color}[{pa_interp}]")
    
    with col_g2:
        _render_panas_gauge(
            value=na_total,
            title=tr['na_label'],
            min_val=10,
            max_val=50,
            color_zones=[
                (10, "#4caf50"),  # Low (green)
                (23, "#ff9800"),  # Moderate (orange)
                (50, "#f44336"),  # High (red)
            ],
            key_suffix="na",
        )
        st.markdown(f"**NA: {na_total}/50** — :{na_color}[{na_interp}]")
    
    # Clinical note
    st.caption(f"💡 {tr.get('clinical_note', '')}")
    st.caption(f"📚 {tr.get('reference', '')}")
    
    return {"panas_pa": pa_total, "panas_na": na_total}


def _render_panas_gauge(
    value: int,
    title: str,
    min_val: int,
    max_val: int,
    color_zones: list,
    key_suffix: str,
) -> None:
    """Render a modern ECharts gauge for PANAS scores.
    
    Args:
        value: Current score value.
        title: Gauge title.
        min_val: Minimum scale value.
        max_val: Maximum scale value.
        color_zones: List of (threshold, color) tuples for gauge zones.
        key_suffix: Unique key suffix for the component.
    """
    import json
    
    # Build color zone config for ECharts
    zones = []
    prev_threshold = min_val
    for threshold, color in color_zones:
        zones.append([
            (threshold - min_val) / (max_val - min_val),
            color
        ])
        prev_threshold = threshold
    
    # ECharts gauge option - modern two-ring style
    option = {
        "series": [
            {
                "type": "gauge",
                "center": ["50%", "60%"],
                "startAngle": 200,
                "endAngle": -20,
                "min": min_val,
                "max": max_val,
                "splitNumber": 8,
                "itemStyle": {"color": "#2196f3"},
                "progress": {
                    "show": True,
                    "width": 20,
                    "itemStyle": {
                        "color": {
                            "type": "linear",
                            "x": 0, "y": 0, "x2": 1, "y2": 0,
                            "colorStops": [
                                {"offset": 0, "color": color_zones[0][1]},
                                {"offset": 0.5, "color": color_zones[1][1] if len(color_zones) > 1 else color_zones[0][1]},
                                {"offset": 1, "color": color_zones[-1][1]},
                            ],
                        }
                    }
                },
                "pointer": {
                    "icon": "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z",
                    "length": "12%",
                    "width": 20,
                    "offsetCenter": [0, "-60%"],
                    "itemStyle": {"color": "auto"},
                },
                "axisLine": {
                    "lineStyle": {
                        "width": 20,
                        "color": zones,
                    }
                },
                "axisTick": {
                    "distance": -30,
                    "splitNumber": 5,
                    "lineStyle": {"width": 2, "color": "#999"},
                },
                "splitLine": {
                    "distance": -35,
                    "length": 14,
                    "lineStyle": {"width": 3, "color": "#999"},
                },
                "axisLabel": {
                    "distance": -20,
                    "color": "#999",
                    "fontSize": 12,
                },
                "anchor": {
                    "show": False,
                },
                "title": {"show": False},
                "detail": {
                    "valueAnimation": True,
                    "width": "60%",
                    "lineHeight": 40,
                    "borderRadius": 8,
                    "offsetCenter": [0, "-15%"],
                    "fontSize": 28,
                    "fontWeight": "bold",
                    "formatter": "{value}",
                    "color": "inherit",
                },
                "data": [{"value": value}],
            }
        ],
    }
    
    # Render with the in-repo ECharts component to avoid optional dependencies.
    render_echarts(option, height_px=220)


# ---------------------------------------------------------------------------
# Clinical Assessment Session
# ---------------------------------------------------------------------------


def _render_clinical_assessment(user: UserProfile) -> None:
    """Render comprehensive clinical assessment section with batched submissions."""
    st.markdown(f"## {t('clinical_assessment')}")
    st.caption(t('clinical_assessment_subtitle'))
    
    if I18N_AVAILABLE:
        with st.expander(f"🌐 {t('language')}", expanded=False):
            render_language_selector(location="main", key_suffix="clinical")
    
    available_scales = {
        "ESS": t('ess_description'),
        "SP": t('sp_description'),
        "KSS": t('kss_description'),
        "VAS": t('vas_description'),
        "PANAS": "Positive and Negative Affect Schedule (mood/affect)",
    }
    
    st.caption("⚡ Inputs are batched — use Preview or Save to refresh scores without full reruns.")

    # Timepoint selector is rendered once above tabs (avoid duplicate keys).
    active_timepoint_id = st.session_state.get(_timepoint_id_key(user.user_id))
    
    selected_scales = st.multiselect(
        t('select_scales'),
        options=list(available_scales.keys()),
        default=["SP", "KSS"],
        format_func=lambda x: f"{x}: {available_scales[x]}",
    )
    
    form_key = f"clinical_assessment_form_{user.user_id}"
    results: Dict[str, Any] = {}
    context_data: Dict[str, Any] = {}
    notes_text = ""
    
    with st.form(form_key, clear_on_submit=False):
        with st.expander(t('assessment_context'), expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                hours_since_wake = st.number_input(
                    t('hours_since_waking'),
                    min_value=0.0,
                    max_value=48.0,
                    value=8.0,
                    step=0.5,
                )
            with col2:
                hours_sleep = st.number_input(
                    t('hours_slept'),
                    min_value=0.0,
                    max_value=24.0,
                    value=7.0,
                    step=0.5,
                )
            with col3:
                caffeine_cups = st.number_input(
                    t('caffeine_today'),
                    min_value=0,
                    max_value=20,
                    value=1,
                    step=1,
                )
        context_data = {
            "hours_since_wake": hours_since_wake,
            "hours_sleep": hours_sleep,
            "caffeine_cups": caffeine_cups,
        }
        
        if "ESS" in selected_scales:
            with st.expander("📋 Epworth Sleepiness Scale", expanded=True):
                results["ess"] = _render_epworth_form(user.user_id)
        
        if "SP" in selected_scales:
            with st.expander("📋 Samn-Perelli Fatigue Scale", expanded=True):
                results["samn_perelli"] = _render_samn_perelli_form(user.user_id)
        
        if "KSS" in selected_scales:
            with st.expander("📋 Karolinska Sleepiness Scale", expanded=True):
                results["kss"] = _render_kss_form(user.user_id)
        
        if "VAS" in selected_scales:
            with st.expander("📋 Visual Analog Scales", expanded=True):
                results.update(_render_vas_scales(user.user_id))
        
        if "PANAS" in selected_scales:
            with st.expander("📋 PANAS - Positive & Negative Affect", expanded=True):
                panas_result = _render_panas_form(user.user_id)
                results["panas_pa"] = panas_result.get("panas_pa")
                results["panas_na"] = panas_result.get("panas_na")
        
        notes_text = st.text_area(
            t('assessment_notes'),
            placeholder=t('assessment_notes_placeholder'),
            max_chars=500,
        )
        
        col_save, col_preview = st.columns([3, 1])
        save_clicked = col_save.form_submit_button(
            t('save_assessment'),
            type="primary",
        )
        preview_clicked = col_preview.form_submit_button(
            "🔁 Preview Scores",
        )
    
    if preview_clicked or save_clicked:
        _render_assessment_preview(results, context_data, notes_text)
    
    if save_clicked:
        if not _should_process_form_submission(form_key):
            st.info("Processing previous submission... please wait.")
            return
        try:
            db = get_database()
            context_note = (
                f"Wake: {context_data.get('hours_since_wake', 0)}h, "
                f"Sleep: {context_data.get('hours_sleep', 0)}h, "
                f"Caffeine: {context_data.get('caffeine_cups', 0)} cups. "
                f"{notes_text}"
            )
            scales = ClinicalScales(
                assessment_id=str(uuid.uuid4()),
                user_id=user.user_id,
                assessment_date=datetime.now(timezone.utc).isoformat(),
                timepoint_id=active_timepoint_id,
                epworth_sleepiness_scale=results.get("ess"),
                karolinska_sleepiness_scale=results.get("kss"),
                samn_perelli_fatigue=results.get("samn_perelli"),
                panas_positive_affect=results.get("panas_pa"),
                panas_negative_affect=results.get("panas_na"),
                vas_fatigue=results.get("vas_fatigue"),
                vas_pain=results.get("vas_pain"),
                notes=context_note,
            )
            db.save_clinical_scales(scales)
            try:
                _load_clinical_history_cached.clear()  # type: ignore[attr-defined]
            except Exception:
                pass
            st.success(t('assessment_saved'))
            st.balloons()
        except Exception as exc:
            st.error(f"Failed to save assessment: {exc}")


def _render_assessment_preview(
    results: Dict[str, Any],
    context_data: Dict[str, Any],
    notes_text: str,
) -> None:
    """Display a summary panel for previewed assessments."""
    if not results:
        st.info("Select at least one scale to preview.")
        return
    
    st.markdown("### 📊 Assessment Preview")
    col1, col2, col3 = st.columns(3)
    with col1:
        value = results.get("samn_perelli")
        st.metric("Samn-Perelli", f"{value:.1f}" if value is not None else "—")
    with col2:
        value = results.get("kss")
        st.metric("KSS", f"{value:.1f}" if value is not None else "—")
    with col3:
        value = results.get("ess")
        st.metric("ESS", f"{value:.0f}" if value is not None else "—")
    
    # PANAS preview
    panas_pa = results.get("panas_pa")
    panas_na = results.get("panas_na")
    if panas_pa is not None or panas_na is not None:
        col_pa, col_na = st.columns(2)
        with col_pa:
            if panas_pa is not None:
                pa_color = "green" if panas_pa >= 40 else ("blue" if panas_pa >= 23 else "orange")
                st.metric("PANAS PA", f"{panas_pa}/50", help="Positive Affect")
        with col_na:
            if panas_na is not None:
                na_color = "red" if panas_na >= 23 else ("orange" if panas_na >= 10 else "green")
                st.metric("PANAS NA", f"{panas_na}/50", help="Negative Affect")
    
    vas_fatigue = results.get("vas_fatigue")
    vas_pain = results.get("vas_pain")
    if vas_fatigue is not None or vas_pain is not None:
        st.caption(
            f"VAS — Fatigue: {vas_fatigue if vas_fatigue is not None else '—'}/10 · "
            f"Pain: {vas_pain if vas_pain is not None else '—'}/10"
        )
    
    st.caption(
        "Context: Wake "
        f"{context_data.get('hours_since_wake', '—')}h | Sleep "
        f"{context_data.get('hours_sleep', '—')}h | Caffeine "
        f"{context_data.get('caffeine_cups', '—')} cups"
    )
    if notes_text.strip():
        st.caption(f"Notes: {notes_text.strip()}")


# ---------------------------------------------------------------------------
# Assessment History
# ---------------------------------------------------------------------------


@_fragment_if_available
def _render_assessment_history(user: UserProfile) -> None:
    """Render clinical assessment history."""
    if not _session_ready_guard():
        st.info("Initializing session…")
        return
    st.markdown("## 📈 Assessment History")
    
    # Use cached loader for fast repeated views
    @st.cache_data(ttl=60, max_entries=64, show_spinner=False)
    def _load_clinical_history_cached(uid: str, limit: int) -> list:
        db = get_database()
        return [h.to_dict() for h in db.get_clinical_scales_history(uid, limit=limit)]

    history_limit = st.selectbox(
        "History window (assessments)",
        options=[50, 90, 180, 365, 730],
        index=2,
        key=f"clinical_history_limit_{user.user_id}",
        help="Load the most recent assessments only (reduces render time).",
    )

    try:
        history_dicts = _load_clinical_history_cached(user.user_id, int(history_limit))
        
        if not history_dicts:
            st.info("No assessment history found. Complete a clinical assessment to start tracking.")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(history_dicts)
        df["assessment_date"] = pd.to_datetime(df["assessment_date"])
        df = df.sort_values("assessment_date", ascending=False)
        
        # Summary metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Assessments", len(df))
        with col2:
            if "samn_perelli_fatigue" in df.columns:
                mean_sp = df["samn_perelli_fatigue"].mean()
                st.metric("Avg SP", f"{mean_sp:.1f}" if pd.notna(mean_sp) else "—")
        with col3:
            if "karolinska_sleepiness_scale" in df.columns:
                mean_kss = df["karolinska_sleepiness_scale"].mean()
                st.metric("Avg KSS", f"{mean_kss:.1f}" if pd.notna(mean_kss) else "—")
        with col4:
            if "panas_positive_affect" in df.columns:
                mean_pa = df["panas_positive_affect"].mean()
                st.metric("Avg PA", f"{mean_pa:.0f}" if pd.notna(mean_pa) else "—", help="PANAS Positive Affect")
        with col5:
            if "panas_negative_affect" in df.columns:
                mean_na = df["panas_negative_affect"].mean()
                st.metric("Avg NA", f"{mean_na:.0f}" if pd.notna(mean_na) else "—", help="PANAS Negative Affect")
        
        # Trend charts - Fatigue scales
        if len(df) > 1:
            st.markdown("##### 📈 Fatigue & Sleepiness Trends")
            chart_cols = ["samn_perelli_fatigue", "karolinska_sleepiness_scale"]
            available_cols = [c for c in chart_cols if c in df.columns]
            if available_cols:
                chart_data = df[["assessment_date"] + available_cols].dropna(how="all", subset=available_cols)
                if not chart_data.empty:
                    chart_data = chart_data.set_index("assessment_date")
                    _render_profile_line_chart(
                        chart_data,
                        title="Fatigue & Sleepiness Trends",
                        y_axis_label="Score",
                    )
            
            # PANAS Trend chart
            panas_cols = ["panas_positive_affect", "panas_negative_affect"]
            available_panas = [c for c in panas_cols if c in df.columns]
            if available_panas and df[available_panas].notna().any().any():
                st.markdown("##### 🎭 PANAS Affect Trends")
                panas_data = df[["assessment_date"] + available_panas].dropna(how="all", subset=available_panas)
                if not panas_data.empty:
                    panas_data = panas_data.set_index("assessment_date")
                    _render_profile_line_chart(
                        panas_data,
                        title="PANAS Affect Trends",
                        y_axis_label="Score",
                    )
        
        # Data table
        with st.expander("📊 All Assessment Data"):
            display_cols = [
                "assessment_date",
                "epworth_sleepiness_scale",
                "samn_perelli_fatigue",
                "karolinska_sleepiness_scale",
                "panas_positive_affect",
                "panas_negative_affect",
                "vas_fatigue",
                "vas_pain",
                "notes",
            ]
            display_df = df[[c for c in display_cols if c in df.columns]]
            st.dataframe(display_df, use_container_width=True)
        
    except Exception as exc:
        st.error(f"Failed to load history: {exc}")


@_fragment_if_available
def _render_garmin_metrics_history(user: UserProfile) -> None:
    """Render wrist-wearable wellness/activity history with gauges."""
    st.markdown("## ⌚ Wrist Monitoring")
    
    # Help section for complete data export
    with st.expander("ℹ️ Missing sleep/stress/body battery data? Click here", expanded=False):
        st.markdown("""
        **Your current upload shows:** Steps, Distance, Calories ✅  
        **Missing:** Sleep, Stress, Body Battery, SpO₂, Respiration ❌
        
        **Why?** Your ZIP only contains FIT files (activity tracking), not wellness JSON files.
        
        **To get ALL wellness metrics:**
        
        1. **Go to Garmin Connect Web** (not mobile app): https://connect.garmin.com
        2. Click your profile icon → **Account Settings**
        3. Go to **Account Information** → **Export Your Data**
        4. Click **"Request Data Export"**
        5. Wait for email (usually 24 hours)
        6. Download the ZIP file from the email link
        7. Upload that complete ZIP here
        
        **What the complete export includes:**
        - `DI_CONNECT/DI-Connect-Wellness/YYYY-MM-DD_sleepData.json` → Sleep score, stages, duration
        - `DI_CONNECT/DI-Connect-Wellness/YYYY-MM-DD_stressData.json` → Stress levels
        - `DI_CONNECT/DI-Connect-Wellness/YYYY-MM-DD_bodyBatteryData.json` → Body Battery
        - `DI_CONNECT/DI-Connect-Wellness/YYYY-MM-DD_spo2Data.json` → Pulse oximeter
        - `DI_CONNECT/DI-Connect-Wellness/YYYY-MM-DD_respirationData.json` → Breathing rate
        
        📚 **Reference:** [Garmin Data Export Guide](https://support.garmin.com/en-US/?faq=W1TvTPW8JZ6LfJSfK512Q8)
        """)

    # If sidebar ingestion placed pending metrics, persist them now
    pending_sidebar = st.session_state.pop("garmin_daily_pending", None)
    if pending_sidebar:
        try:
            pending_df = pd.DataFrame(pending_sidebar)
            if not pending_df.empty:
                entries: List[GarminDailyMetrics] = []
                now_iso = datetime.now(timezone.utc).isoformat()
                for _, row in pending_df.iterrows():
                    day_val = row.get("date")
                    if pd.isna(day_val):
                        continue
                    metric_date = pd.to_datetime(day_val).date().isoformat()
                    avg_hr = _safe_float(row.get("avg_hr_session")) or _safe_float(row.get("avg_hr"))
                    resting_hr = _safe_float(row.get("resting_hr_bpm")) or _safe_float(row.get("min_hr"))
                    entries.append(
                        GarminDailyMetrics(
                            entry_id=str(uuid.uuid4()),
                            user_id=user.user_id,
                            metric_date=metric_date,
                            steps=_safe_int(row.get("steps")),
                            distance_km=_safe_float(row.get("distance_km")),
                            calories_kcal=_safe_float(row.get("calories_kcal")),
                            avg_hr_bpm=avg_hr,
                            resting_hr_bpm=resting_hr,
                            stress_score=_safe_float(row.get("avg_stress")),
                            sleep_score=_safe_float(row.get("sleep_score")),
                            sleep_efficiency=_safe_float(row.get("sleep_efficiency")),
                            sleep_duration_hours=_safe_float(row.get("sleep_duration_hours")),
                            avg_spo2=_safe_float(row.get("avg_sleep_spo2")) or _safe_float(row.get("avg_spo2")),
                            avg_respiration_awake=_safe_float(row.get("avg_respiration_awake")),
                            avg_respiration_sleep=_safe_float(row.get("avg_sleep_respiration")),
                            body_battery_avg=_safe_float(row.get("body_battery_avg")) or _safe_float(row.get("avg_body_battery")),
                            body_battery_charge=_safe_float(row.get("body_battery_charge")),
                            body_battery_drain=_safe_float(row.get("body_battery_drain")),
                            source="garmin_import_sidebar",
                            created_at=now_iso,
                        )
                    )
                if entries:
                    db = get_database()
                    db.save_garmin_daily_metrics(entries)
        except Exception as exc:  # noqa: BLE001
            if log_exception is not None:
                log_exception(_LOGGER, "Failed to persist sidebar Garmin metrics", exc)

    # Live Garmin Connect fetch (manual button; requires env + library)
    api_env_ready = (
        GARMIN_LIB_AVAILABLE
        and bool(os.getenv("GARMIN_EMAIL"))
        and bool(os.getenv("GARMIN_PASSWORD"))
    )
    with st.expander("🔄 Import from Garmin Connect (Vivosmart 5)", expanded=False):
        if not GARMIN_LIB_AVAILABLE:
            st.info("Install `garminconnect` to enable live Garmin imports (see requirements.txt).")
        elif not api_env_ready:
            st.info("Set GARMIN_EMAIL and GARMIN_PASSWORD in your .env to enable Garmin Connect import.")
        else:
            days_to_fetch = st.select_slider(
                "Days to fetch (includes today)",
                options=[7, 14, 30],
                value=14,
                key=f"garmin_api_days_{user.user_id}",
            )
            if st.button(
                "Fetch from Garmin Connect",
                key=f"garmin_api_fetch_{user.user_id}",
                type="primary",
            ):
                try:
                    with st.spinner(f"Fetching last {days_to_fetch} day(s) from Garmin Connect…"):
                        records = fetch_garmin_daily_metrics(user.user_id, days=int(days_to_fetch))
                except GarminAuthError as exc:
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001
                    if log_exception is not None:
                        log_exception(_LOGGER, "Garmin Connect fetch failed", exc)
                    st.error(f"Garmin fetch failed: {exc}")
                else:
                    if not records:
                        st.info("No Garmin data returned for the selected window.")
                    else:
                        db = get_database()
                        db.save_garmin_daily_metrics(records)
                        summary = summarize_garmin_daily(records)
                        label = summary.get("dates", "")
                        st.success(f"Imported {summary.get('count', len(records))} day(s) from Garmin Connect. {label}")
                        st.experimental_rerun()

    if not GARMIN_IMPORT_AVAILABLE:
        st.info("Garmin import module unavailable. Install fitparse and rerun.")
        return

    # Load window control (how many days to pull from DB for stats/trends)
    history_limit = st.selectbox(
        "History window (days)",
        options=[30, 90, 180, 365, 730, 1095, 1825],
        index=3,  # 365
        key=f"garmin_history_limit_{user.user_id}",
        help="Loads the most recent N days stored in your profile database.",
    )

    @st.cache_data(ttl=30, max_entries=64, show_spinner=False)
    def _load_history(uid: str, limit: int) -> pd.DataFrame:
        db = get_database()
        if hasattr(db, "get_garmin_daily_dataframe"):
            return db.get_garmin_daily_dataframe(uid, limit=int(limit))  # type: ignore[attr-defined]
        if hasattr(db, "get_garmin_daily_metrics"):
            metrics = db.get_garmin_daily_metrics(uid, limit=int(limit))  # type: ignore[attr-defined]
            if not metrics:
                return pd.DataFrame()
            return pd.DataFrame([m.to_dict() for m in metrics])
        return pd.DataFrame()

    try:
        df = _load_history(user.user_id, int(history_limit))
    except Exception as exc:  # noqa: BLE001
        st.error(f"Unable to load Garmin history: {exc}")
        return

    if df.empty and not hasattr(get_database(), "get_garmin_daily_metrics"):
        st.warning(
            "Wrist monitoring history requires the updated database methods. "
            "Please restart the app to reload the updated code, or run a fresh session."
        )
        return

    if df.empty:
        st.info("No Garmin wellness metrics stored yet. Upload a FIT/ZIP/JSON file in the Data tab.")
        return

    if "metric_date" in df.columns:
        df["metric_date"] = pd.to_datetime(df["metric_date"], errors="coerce")
        df = df.dropna(subset=["metric_date"])
        df.sort_values("metric_date", ascending=False, inplace=True)

    latest = df.iloc[0]

    def _latest_non_null(metric_col: str) -> tuple[Optional[float], Optional[pd.Timestamp]]:
        """Return (value, metric_date) for the latest non-null metric value.

        We intentionally use the latest *available* value per metric (not just the latest
        day row) because Garmin imports can arrive in parts (UDS daily summary vs sleep),
        and the most recent day may be incomplete.
        """
        if metric_col not in df.columns or "metric_date" not in df.columns:
            return None, None
        series = pd.to_numeric(df[metric_col], errors="coerce")
        non_null_mask = series.notna()
        if not bool(non_null_mask.any()):
            return None, None
        # IMPORTANT: df is sorted latest-first, but its index may not be reset (and may
        # not be unique). Avoid relying on label-based selection via idxmax/loc.
        try:
            val_any = series.loc[non_null_mask].iloc[0]
            dt_any = df.loc[non_null_mask, "metric_date"].iloc[0]
        except (IndexError, KeyError, TypeError, ValueError):
            return None, None

        try:
            val = float(val_any)
        except (TypeError, ValueError):
            return None, None

        dt = pd.to_datetime(dt_any, errors="coerce")
        if dt is None or pd.isna(dt):
            return val, None
        return val, dt

    def _date_label(dt_val: Any) -> str:
        if dt_val is None or pd.isna(dt_val):
            return "—"
        try:
            return pd.to_datetime(dt_val).date().isoformat()
        except Exception:
            return str(dt_val)

    no_data_hints: dict[str, str] = {
        # Activity + physiology summaries
        "steps": "Import a Garmin FIT/ZIP/JSON with daily activity summaries (e.g., `UDSFile_*.json`).",
        "distance_km": "Import a Garmin FIT/ZIP/JSON with daily activity summaries (e.g., `UDSFile_*.json`).",
        "calories_kcal": "Import a Garmin FIT/ZIP/JSON with daily activity summaries (e.g., `UDSFile_*.json`).",
        "avg_hr_bpm": "Import a Garmin FIT file or `UDSFile_*.json` daily summary (then re-import to populate Avg HR).",
        "resting_hr_bpm": "Import a Garmin FIT/ZIP/JSON that includes resting HR (often present in `UDSFile_*.json`).",
        "stress_score": "Import `UDSFile_*.json` (daily stress summary) or a wellness ZIP export.",
        "avg_spo2": "Import `UDSFile_*.json` (daily SpO₂ summary) or `*_spo2Data.json` / wellness ZIP if available.",
        "avg_respiration_awake": "Import `UDSFile_*.json` (daily respiration summary) or `*_respirationData.json` / wellness ZIP if available.",
        # Sleep-derived metrics
        "sleep_score": "Import `*_sleepData.json` (sleep export) or a wellness ZIP export (sleep scores live there).",
        "sleep_efficiency": "Import `*_sleepData.json` (sleep start/end required); efficiency is computed by the app.",
        "sleep_duration_hours": "Import `*_sleepData.json` (sleep duration/stages).",
        "avg_respiration_sleep": "Import `*_sleepData.json` (contains sleep respiration in many Garmin exports).",
        # Body battery
        "body_battery_avg": "Import `UDSFile_*.json` or a wellness ZIP export containing body battery.",
        "body_battery_charge": "Import `UDSFile_*.json` or a wellness ZIP export containing body battery charge/drain.",
        "body_battery_drain": "Import `UDSFile_*.json` or a wellness ZIP export containing body battery charge/drain.",
    }
    
    # Debug: show what values we have (DEBUG level to avoid log noise on every rerender)
    _LOGGER.debug(
        "Wrist monitoring latest day: steps=%s, distance_km=%s, calories=%s, sleep_score=%s, stress=%s",
        latest.get("steps"), latest.get("distance_km"), latest.get("calories_kcal"),
        latest.get("sleep_score"), latest.get("stress_score"),
    )
    
    # Show latest day values prominently
    latest_day_val = latest.get("metric_date")
    latest_day_label = "—"
    if latest_day_val is not None and not pd.isna(latest_day_val):
        try:
            latest_day_label = pd.to_datetime(latest_day_val).date().isoformat()
        except Exception:
            latest_day_label = str(latest_day_val)
    st.markdown(f"### 📅 Latest Day: {latest_day_label}")
    col_a, col_b, col_c, col_d, col_e = st.columns(5)
    with col_a:
        steps_val = _safe_float(latest.get("steps"))
        st.metric("Steps", f"{steps_val:,.0f}" if steps_val else "—")
    with col_b:
        dist_val = _safe_float(latest.get("distance_km"))
        st.metric("Distance", f"{dist_val:.1f} km" if dist_val else "—")
    with col_c:
        cal_val = _safe_float(latest.get("calories_kcal"))
        st.metric("Calories", f"{cal_val:,.0f} kcal" if cal_val else "—")
    with col_d:
        sleep_val = _safe_float(latest.get("sleep_score"))
        st.metric("Sleep Score", f"{sleep_val:.0f}" if sleep_val else "—")
    with col_e:
        stress_val = _safe_float(latest.get("stress_score"))
        st.metric("Stress", f"{stress_val:.0f}" if stress_val else "—")
    
    st.markdown("---")

    # Summary indicators
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Days logged", f"{len(df)}")
    with col2:
        if "steps" in df.columns:
            steps_mean = df['steps'].mean()
            st.metric("Avg steps", f"{steps_mean:,.0f}" if pd.notna(steps_mean) else "—")
    with col3:
        if "sleep_score" in df.columns:
            sleep_mean = df['sleep_score'].mean()
            st.metric("Avg sleep score", f"{sleep_mean:.1f}" if pd.notna(sleep_mean) else "—")
    with col4:
        if "stress_score" in df.columns:
            stress_mean = df['stress_score'].mean()
            st.metric("Avg stress", f"{stress_mean:.1f}" if pd.notna(stress_mean) else "—")

    # Render gauges in organized sections
    st.markdown("### 🏃 Activity & Movement")
    cols = st.columns(3)
    activity_gauges = [
        ("steps", "Steps", "steps"),
        ("distance_km", "Distance", "distance_km"),
        ("calories_kcal", "Calories", "calories_kcal"),
    ]
    for col, (metric_col, title, threshold_key) in zip(cols, activity_gauges):
        val, val_date = _latest_non_null(metric_col)
        if val is None or pd.isna(val):
            with col:
                hint = no_data_hints.get(metric_col, "")
                st.info(f"No {title} data. {hint}".strip())
            continue
        thresholds = get_gauge_thresholds(threshold_key)
        if not thresholds:
            continue
        option = build_two_ring_gauge(threshold_key, val, title=title, thresholds=thresholds)
        with col:
            render_echarts(option, height_px=280)
            st.caption(f"Latest available: {_date_label(val_date)}")
    
    st.markdown("### ❤️ Heart Rate & Stress")
    cols = st.columns(3)
    hr_gauges = [
        ("avg_hr_bpm", "Avg HR", "avg_hr_bpm"),
        ("resting_hr_bpm", "Resting HR", "resting_hr_bpm"),
        ("stress_score", "Stress", "stress_score"),
    ]
    for col, (metric_col, title, threshold_key) in zip(cols, hr_gauges):
        val, val_date = _latest_non_null(metric_col)
        if val is None or pd.isna(val):
            with col:
                hint = no_data_hints.get(metric_col, "")
                st.info(f"No {title} data. {hint}".strip())
            continue
        thresholds = get_gauge_thresholds(threshold_key)
        if not thresholds:
            continue
        option = build_two_ring_gauge(threshold_key, val, title=title, thresholds=thresholds)
        with col:
            render_echarts(option, height_px=280)
            st.caption(f"Latest available: {_date_label(val_date)}")
    
    st.markdown("### 😴 Sleep & Recovery")
    cols = st.columns(3)
    sleep_gauges = [
        ("sleep_score", "Sleep Score", "sleep_score"),
        ("sleep_efficiency", "Sleep Efficiency", "sleep_efficiency"),
        ("sleep_duration_hours", "Sleep Duration", "sleep_duration_hours"),
    ]
    for col, (metric_col, title, threshold_key) in zip(cols, sleep_gauges):
        val, val_date = _latest_non_null(metric_col)
        if val is None or pd.isna(val):
            with col:
                hint = no_data_hints.get(metric_col, "")
                st.info(f"No {title} data. {hint}".strip())
            continue
        thresholds = get_gauge_thresholds(threshold_key)
        if not thresholds:
            continue
        option = build_two_ring_gauge(threshold_key, val, title=title, thresholds=thresholds)
        with col:
            render_echarts(option, height_px=280)
            st.caption(f"Latest available: {_date_label(val_date)}")
    
    st.markdown("### 🫁 Respiration & SpO₂")
    cols = st.columns(3)
    resp_gauges = [
        ("avg_spo2", "SpO₂", "spo2_pct"),
        ("avg_respiration_awake", "Resp Awake", "respiration_awake_bpm"),
        ("avg_respiration_sleep", "Resp Sleep", "respiration_sleep_bpm"),
    ]
    for col, (metric_col, title, threshold_key) in zip(cols, resp_gauges):
        val, val_date = _latest_non_null(metric_col)
        if val is None or pd.isna(val):
            with col:
                hint = no_data_hints.get(metric_col, "")
                st.info(f"No {title} data. {hint}".strip())
            continue
        thresholds = get_gauge_thresholds(threshold_key)
        if not thresholds:
            continue
        option = build_two_ring_gauge(threshold_key, val, title=title, thresholds=thresholds)
        with col:
            render_echarts(option, height_px=280)
            st.caption(f"Latest available: {_date_label(val_date)}")
    
    st.markdown("### 🔋 Body Battery")
    cols = st.columns(3)
    bb_gauges = [
        ("body_battery_avg", "Avg Level", "body_battery_avg"),
        ("body_battery_charge", "Charged", "body_battery_charge"),
        ("body_battery_drain", "Drained", "body_battery_drain"),
    ]
    for col, (metric_col, title, threshold_key) in zip(cols, bb_gauges):
        val, val_date = _latest_non_null(metric_col)
        if val is None or pd.isna(val):
            with col:
                hint = no_data_hints.get(metric_col, "")
                st.info(f"No {title} data. {hint}".strip())
            continue
        thresholds = get_gauge_thresholds(threshold_key)
        if not thresholds:
            continue
        option = build_two_ring_gauge(threshold_key, val, title=title, thresholds=thresholds)
        with col:
            render_echarts(option, height_px=280)
            st.caption(f"Latest available: {_date_label(val_date)}")

    st.markdown("---")
    st.markdown("---")
    st.markdown("### 📊 Statistical Analysis")
    
    # Build a time-indexed view for charts (ascending time)
    df_ts = df.copy()
    if "metric_date" in df_ts.columns:
        df_ts = df_ts.sort_values("metric_date", ascending=True).set_index("metric_date")

    # Summary statistics (computed from DB history; includes all supported Garmin fields)
    numeric_cols = [
        c
        for c in df.columns
        if c
        not in {
            "entry_id",
            "user_id",
            "metric_date",
            "source",
            "created_at",
        }
        and pd.api.types.is_numeric_dtype(df[c])
    ]
    if numeric_cols:
        stats_rows: list[dict[str, Any]] = []
        for col in numeric_cols:
            series = pd.to_numeric(df[col], errors="coerce")
            non_null = series.dropna()
            latest_non_null: Any = None
            if not non_null.empty:
                # df is sorted latest-first; pick first non-null for "latest"
                latest_non_null = non_null.iloc[0]
            stats_rows.append(
                {
                    "Metric": col,
                    "N": int(series.notna().sum()),
                    "Mean": float(series.mean()) if series.notna().any() else None,
                    "Median": float(series.median()) if series.notna().any() else None,
                    "Min": float(series.min()) if series.notna().any() else None,
                    "Max": float(series.max()) if series.notna().any() else None,
                    "Latest": latest_non_null,
                }
            )
        stats_df = pd.DataFrame(stats_rows)
        if not stats_df.empty:
            st.markdown("#### Summary statistics (stored Garmin daily metrics)")
            st.dataframe(stats_df, use_container_width=True, hide_index=True)

    # Trends (grouped so all Garmin fields can be visualized)
    if len(df_ts) > 1 and isinstance(df_ts.index, pd.DatetimeIndex):
        st.markdown("#### Trends Over Time")
        groups: list[tuple[str, dict[str, str]]] = [
            (
                "🏃 Activity & Movement",
                {
                    "steps": "Steps",
                    "distance_km": "Distance (km)",
                    "calories_kcal": "Calories (kcal)",
                },
            ),
            (
                "❤️ Heart Rate & Stress",
                {
                    "avg_hr_bpm": "Avg HR (bpm)",
                    "resting_hr_bpm": "Resting HR (bpm)",
                    "stress_score": "Stress score",
                },
            ),
            (
                "😴 Sleep & Recovery",
                {
                    "sleep_score": "Sleep score",
                    "sleep_efficiency": "Sleep efficiency (%)",
                    "sleep_duration_hours": "Sleep duration (h)",
                },
            ),
            (
                "🫁 Respiration & SpO₂",
                {
                    "avg_spo2": "SpO₂ (%)",
                    "avg_respiration_awake": "Resp awake (rpm)",
                    "avg_respiration_sleep": "Resp sleep (rpm)",
                },
            ),
            (
                "🔋 Body Battery",
                {
                    "body_battery_avg": "Body battery avg",
                    "body_battery_charge": "Body battery charge (+)",
                    "body_battery_drain": "Body battery drain (–)",
                },
            ),
        ]
        rendered_any = False
        for title, rename_map in groups:
            cols = [c for c in rename_map.keys() if c in df_ts.columns and df_ts[c].notna().sum() > 1]
            if not cols:
                continue
            rendered_any = True
            st.markdown(f"##### {title}")
            plot_df = df_ts[cols].copy().rename(columns=rename_map)
            _render_profile_line_chart(
                plot_df,
                title=f"{title} trends",
                y_axis_label="Value (see legend units)",
            )
        if not rendered_any:
            st.caption("Not enough repeated daily values to render trend charts yet.")
    
    with st.expander("📋 View all daily metrics", expanded=False):
        preview_cols = [
            "metric_date",
            "steps",
            "distance_km",
            "calories_kcal",
            "avg_hr_bpm",
            "resting_hr_bpm",
            "stress_score",
            "sleep_score",
            "sleep_efficiency",
            "sleep_duration_hours",
            "avg_spo2",
            "avg_respiration_awake",
            "avg_respiration_sleep",
            "body_battery_avg",
            "body_battery_charge",
            "body_battery_drain",
        ]
        existing_cols = [c for c in preview_cols if c in df.columns]
        display_df = df[existing_cols].copy()
        
        # Format for better display
        if "metric_date" in display_df.columns:
            display_df["metric_date"] = display_df["metric_date"].dt.strftime("%Y-%m-%d")
        st.caption(f"Showing {len(display_df)} day(s) loaded from the database.")
        
        st.dataframe(
            display_df.reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )

# ---------------------------------------------------------------------------
# HRV History Section
# ---------------------------------------------------------------------------


def _render_profile_rr_uploads(user: UserProfile) -> None:
    """Allow uploading RR files directly from the profile tab."""
    st.markdown("## 📂 HRV File Uploads")
    st.caption(
        "Upload RR interval files (Polar H10/Flow exports .txt or .csv) to store them under this profile. "
        "They will be queued for analysis without needing the sidebar uploader."
    )
    uploaded_files = st.file_uploader(
        "Upload RR (.txt or .csv)",
        type=["txt", "csv"],
        accept_multiple_files=True,
        key=f"profile_rr_upload_{user.user_id}",
    )
    if not uploaded_files:
        return
    try:
        manager = create_user_manager()
        manager.set_current_user(
            user_id=user.user_id,
            name=user.full_name or user.username or "User",
            create_if_missing=True,
        )
        _set_current_user(user)
    except Exception as exc:  # pragma: no cover - defensive
        st.error(f"Unable to prepare storage for uploads: {exc}")
        return

    queued: list[dict[str, Any]] = st.session_state.get("queued_rr_uploads", [])
    stored_any = False
    preview_rr_ms: Optional[np.ndarray] = None
    for uploaded in uploaded_files:
        try:
            content = uploaded.read().decode("utf-8", errors="ignore")

            if uploaded.name.lower().endswith(".csv"):
                # Polar Flow/H10 CSV: first column of RR values (ms); drop headers/non-numeric
                df_csv = pd.read_csv(io.StringIO(content), header=None, sep=None, engine="python")
                rr_series = pd.to_numeric(df_csv.stack(), errors="coerce").dropna()
                rr_ms = rr_series.to_numpy(dtype=float)
            else:
                rr_ms = load_rr_intervals_from_text(uploaded.name, content)

            if rr_ms.size < 10:
                st.warning(f"{uploaded.name}: not enough RR intervals to store.")
                continue
            if preview_rr_ms is None:
                preview_rr_ms = rr_ms
            start_date = parse_filename_date(uploaded.name) or date.today()
            start_ts = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
            try:
                manager.store_rr_intervals(
                    rr_ms,
                    filename=uploaded.name,
                    recording_date=start_date,
                    overwrite=True,
                )
            except FileExistsError:
                # Already stored; continue to queue for analysis
                pass
            queued.append(
                {
                    "name": uploaded.name,
                    "rr_ms": rr_ms,
                    "recording_start": start_ts.isoformat(),
                }
            )
            stored_any = True
        except Exception as exc:  # pragma: no cover - defensive
            st.error(f"Failed to store {uploaded.name}: {exc}")
    st.session_state["queued_rr_uploads"] = queued
    if stored_any:
        st.success("Files stored under this profile and queued for analysis.")
        # Inline quick-look plots for the first uploaded file to avoid blank UI
        if preview_rr_ms is not None and preview_rr_ms.size >= 10:
            with st.spinner("Preparing quick RR preview..."):
                # Downsample for responsiveness (keep up to 8k samples)
                rr_ms = preview_rr_ms
                if rr_ms.size > 8000:
                    step = int(np.ceil(rr_ms.size / 8000))
                    rr_ms = rr_ms[::step]
                rr_s = rr_ms / 1000.0
                t_s = np.cumsum(rr_s)
                ts_df = pd.DataFrame({"Time (s)": t_s, "RR (ms)": rr_ms})
                st.markdown("### 🔎 Quick RR Preview")
                st.line_chart(ts_df.set_index("Time (s)"))

                # PSD via Welch (optional)
                try:
                    from scipy.signal import welch  # type: ignore

                    fs = 1.0 / np.median(rr_s) if np.median(rr_s) > 0 else 1.0
                    # Limit segment length to keep computation fast
                    freqs, psd = welch(rr_ms, fs=fs, nperseg=min(1024, rr_ms.size))
                    psd_df = pd.DataFrame({"Frequency (Hz)": freqs, "PSD": psd})
                    st.markdown("##### Power Spectral Density")
                    st.area_chart(psd_df.set_index("Frequency (Hz)"))
                except Exception:
                    st.info("PSD preview unavailable (scipy.signal not available).")

                # Histogram
                hist_vals, bin_edges = np.histogram(rr_ms, bins=30)
                hist_df = pd.DataFrame({"RR bin (ms)": bin_edges[:-1], "Count": hist_vals})
                st.markdown("##### RR Distribution")
                st.bar_chart(hist_df.set_index("RR bin (ms)"))

                st.caption(
                    "For full time-domain, frequency-domain, nonlinear metrics, and spectrograms, "
                    "open the main HRV analysis with these queued recordings."
                )


@_fragment_if_available
def _render_profile_rr_library(user: UserProfile) -> None:
    """Load RR recordings already stored under this profile into the main analysis workspace."""
    st.markdown("## 📚 Stored RR Library")
    st.caption(
        "Load RR interval recordings already saved under this profile into the main analysis workspace "
        "(no re-upload needed)."
    )

    # Mission-scoped storage (default): crew/<Mission>/subjects/<user_id>/rr_intervals
    primary_user_path = get_user_data_path(user.user_id, base_path=None)
    primary_rr_dir = primary_user_path / "rr_intervals"

    # Legacy fallback: <project_root>/data/<user_id>/rr_intervals (copied into crew on first use)
    legacy_root = Path(__file__).resolve().parents[1] / "data"
    legacy_user_path = get_user_data_path(user.user_id, base_path=legacy_root)
    legacy_rr_dir = legacy_user_path / "rr_intervals"

    option_to_path: dict[str, Path] = {}
    primary_files: list[Path] = []
    legacy_files: list[Path] = []

    if primary_rr_dir.exists():
        primary_files = sorted(primary_rr_dir.glob("*.txt"), key=lambda p: p.name, reverse=True)
        for p in primary_files:
            option_to_path[p.name] = p

    if legacy_rr_dir.exists():
        legacy_files = sorted(legacy_rr_dir.glob("*.txt"), key=lambda p: p.name, reverse=True)
        for p in legacy_files:
            label = p.name if p.name not in option_to_path else f"{p.name} [legacy]"
            option_to_path[label] = p

    if not option_to_path:
        st.info("No stored RR recordings found yet for this profile.")
        st.caption(f"Checked: {primary_rr_dir}")
        if legacy_rr_dir != primary_rr_dir:
            st.caption(f"Checked (legacy): {legacy_rr_dir}")
        return

    st.caption(
        "Storage: "
        f"{len(primary_files)} file(s) in mission library"
        + (f", {len(legacy_files)} file(s) in legacy library" if legacy_files else "")
    )
    options = list(option_to_path.keys())
    options.sort(reverse=True)

    default_count = min(2, len(options))
    selected = st.multiselect(
        "Select recordings to load",
        options=options,
        default=options[:default_count],
        key=f"profile_rr_library_select_{user.user_id}",
        help="These recordings will be loaded into the main analysis workspace for this active profile.",
    )

    if not selected:
        return

    def _build_queue_payload() -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for name in selected:
            p = option_to_path.get(name)
            if p is None:
                continue
            start_date = parse_filename_date(p.name) or date.today()
            start_ts = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
            payload.append(
                {
                    "path": str(p),
                    "name": p.name,
                    "recording_start": start_ts.isoformat(),
                }
            )
        return payload

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button(
            "📥 Load into Analysis workspace",
            key=f"profile_rr_library_load_{user.user_id}",
            use_container_width=True,
        ):
            st.session_state["queued_rr_filepaths"] = _build_queue_payload()
            _set_current_user(user)
            st.success("Queued stored RR recordings for the analysis workspace.")
            st.rerun()
    with col_b:
        if st.button(
            "🚀 Load + run HRV analysis",
            key=f"profile_rr_library_load_run_{user.user_id}",
            type="primary",
            use_container_width=True,
        ):
            st.session_state["queued_rr_filepaths"] = _build_queue_payload()
            st.session_state["auto_run_hrv_analysis"] = True
            _set_current_user(user)
            st.success("Queued recordings and starting HRV analysis…")
            st.rerun()


@_fragment_if_available
def _render_sqlite_corruption_recovery_ui(*, context_label: str, user_id: str, exc: BaseException) -> None:
    """Render recovery UI when the mission SQLite database is corrupted."""
    st.error(
        "The mission database appears corrupted (SQLite). "
        "This is usually fixable by restoring a timestamped backup."
    )
    if not DATABASE_AVAILABLE:
        st.caption("Database module is unavailable in this environment.")
        return

    db_path = get_database_path()
    st.caption(f"Context: {context_label}")
    st.caption(f"Database file: {db_path}")
    st.caption(f"Error: {exc}")

    ok, msg = sqlite_quick_check(db_path)
    if ok:
        st.info("SQLite quick_check reports OK, but a query still failed. Try restoring a backup anyway.")
    else:
        st.warning(f"SQLite quick_check indicates corruption: {msg}")

    st.markdown("### Restore from backup")
    backups = list_database_backups(db_path=db_path, max_backups=25)
    if not backups:
        st.info("No timestamped backups were found next to the mission database.")
    else:
        backup_names = [p.name for p in backups]
        selected_name = st.selectbox(
            "Select a backup to restore",
            options=backup_names,
            index=0,
            key=f"db_restore_select_{user_id}",
            help="Newest backups are listed first.",
        )
        selected_backup = backups[backup_names.index(selected_name)]
        bak_ok, bak_msg = sqlite_quick_check(selected_backup)
        if bak_ok:
            st.caption("Selected backup integrity: ok")
        else:
            st.warning(f"Selected backup integrity check: {bak_msg}")

        confirm_restore = st.checkbox(
            "I understand this will overwrite the active DB file (a corrupt copy will be preserved).",
            key=f"db_restore_confirm_{user_id}",
        )
        if st.button(
            "🛟 Restore selected backup",
            type="primary",
            disabled=not confirm_restore,
            key=f"db_restore_btn_{user_id}",
        ):
            try:
                preserved = restore_database_from_backup(backup_path=selected_backup, db_path=db_path)
            except Exception as restore_exc:  # noqa: BLE001
                st.error(f"Restore failed: {restore_exc}")
                st.info(
                    "If the file is locked, stop Streamlit (Ctrl+C), wait a few seconds, and try again."
                )
            else:
                st.success(f"Backup restored. Previous DB preserved as: {preserved.name}")
                try:
                    st.cache_data.clear()
                except Exception:  # pragma: no cover
                    pass
                st.rerun()

    st.markdown("### Create a new empty database (last resort)")
    st.caption(
        "This keeps a copy of the corrupted DB file, but you may lose stored history until you re-import/recompute it."
    )
    confirm_reset = st.checkbox(
        "I understand this creates a new empty mission database.",
        key=f"db_reset_confirm_{user_id}",
    )
    if st.button(
        "🧯 Reset database (create new empty)",
        disabled=not confirm_reset,
        key=f"db_reset_btn_{user_id}",
    ):
        try:
            moved = reset_database_file(db_path=db_path)
        except Exception as reset_exc:  # noqa: BLE001
            st.error(f"Reset failed: {reset_exc}")
            st.info("If the file is locked, stop Streamlit (Ctrl+C) and try again.")
        else:
            moved_names = ", ".join(p.name for p in moved) if moved else "(nothing moved)"
            st.success(f"Database reset. Preserved files: {moved_names}")
            try:
                st.cache_data.clear()
            except Exception:  # pragma: no cover
                pass
            st.rerun()


@_fragment_if_available
def _render_hrv_history(user: UserProfile) -> None:
    """Render HRV measurement history."""
    st.markdown("## 💓 HRV Measurement History")

    refresh_state_key = f"hrv_history_refresh_token:{user.user_id}"
    refresh_token_raw = st.session_state.get(refresh_state_key, 0)
    try:
        refresh_token = int(refresh_token_raw) if refresh_token_raw is not None else 0
    except (TypeError, ValueError):
        refresh_token = 0

    col_refresh, col_meta = st.columns([1, 3])
    with col_refresh:
        if st.button(
            "🔄 Regenerate plots",
            key=f"hrv_history_regen_{user.user_id}",
            help="Reload HRV measurements from the database and redraw all charts.",
        ):
            st.session_state[refresh_state_key] = refresh_token + 1
            try:
                st.cache_data.clear()
            except Exception:  # pragma: no cover - cache may be unavailable in some contexts
                pass
            st.rerun()
    with col_meta:
        st.caption("If charts look stale after new uploads/analysis, regenerate to refresh them.")
    
    try:
        with st.spinner("Loading HRV measurements..."):
            db = get_database()
            df = db.get_hrv_dataframe(user.user_id, limit=500, include_rr=False)
        
        if df.empty:
            st.info("No HRV measurements recorded. Import HRV data from the main analysis to populate this section.")
            return
        
        df = df.sort_values("measurement_date")
        if len(df) >= 500:
            st.caption("Showing the 500 most recent HRV measurements for faster loading.")

        # Optional: last update marker (helps verify refreshes)
        if "created_at" in df.columns:
            try:
                last_created = pd.to_datetime(df["created_at"], errors="coerce").max()
            except Exception:
                last_created = None
            if last_created is not None and not pd.isna(last_created):
                st.caption(f"Last saved measurement: {last_created} (UTC)")
    
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Recordings", len(df))
        with col2:
            if "rmssd_ms" in df.columns:
                st.metric("Avg RMSSD", f"{df['rmssd_ms'].mean():.1f} ms")
        with col3:
            if "sdnn_ms" in df.columns:
                st.metric("Avg SDNN", f"{df['sdnn_ms'].mean():.1f} ms")
        with col4:
            if "mean_hr_bpm" in df.columns:
                st.metric("Avg HR", f"{df['mean_hr_bpm'].mean():.0f} bpm")
        
        # Trend chart
        if len(df) > 1 and "measurement_date" in df.columns:
            chart_cols = ["rmssd_ms", "sdnn_ms"]
            available_cols = [c for c in chart_cols if c in df.columns]
            if available_cols:
                chart_data = df.set_index("measurement_date")[available_cols]
                _render_profile_line_chart(
                    chart_data,
                    title="HRV History",
                    y_axis_label="ms",
                )

        # Longitudinal baseline/change analytics (T0–T21)
        with st.expander("🧪 Baseline / Δ by timepoint (T0–T21)", expanded=False):
            st.caption(
                "Groups HRV sessions by your saved longitudinal timepoints (T0…T21), "
                "computes a baseline from T0, and reports Δ (delta) per timepoint. "
                "This requires that your saved HRV measurements are tagged with a timepoint."
            )

            if "timepoint_id" not in df.columns or df["timepoint_id"].isna().all():
                st.info(
                    "No timepoint-tagged HRV measurements were found yet. "
                    "Use the **Longitudinal timepoint (T0–T21)** selector when saving new entries."
                )
            else:
                available_metric_candidates = [
                    "rmssd_ms",
                    "sdnn_ms",
                    "mean_hr_bpm",
                    "hf_power_ms2",
                    "lf_hf_ratio",
                    "parasympathetic_index",
                    "stress_index",
                    "artifact_percentage",
                    "quality_score",
                ]
                available_metrics = [
                    m for m in available_metric_candidates if m in df.columns and df[m].notna().any()
                ]
                if not available_metrics:
                    st.info("Timepoints are present, but no numeric HRV metrics are available to summarize yet.")
                else:
                    col_a, col_b = st.columns([2, 1])
                    with col_a:
                        selected_metrics = st.multiselect(
                            "Metrics to summarize",
                            options=available_metrics,
                            default=[m for m in ["rmssd_ms", "sdnn_ms", "mean_hr_bpm"] if m in available_metrics],
                            key=f"profile_timepoint_metrics_{user.user_id}",
                            help="These metrics will be aggregated per timepoint, then compared vs the baseline timepoint.",
                        )
                    with col_b:
                        agg_mode = st.selectbox(
                            "Aggregation",
                            options=["median", "mean"],
                            index=0,
                            key=f"profile_timepoint_agg_{user.user_id}",
                            help="How to combine multiple sessions within the same timepoint.",
                        )

                    try:
                        # If the user unselects everything, fall back to the default metric list inside the DB helper.
                        metrics_arg = selected_metrics if selected_metrics else None
                        tp_table = db.get_hrv_timepoint_change_table(
                            user.user_id,
                            metrics=metrics_arg,
                            agg=str(agg_mode),
                            limit=500,
                        )
                    except Exception as exc:  # noqa: BLE001
                        tp_table = pd.DataFrame()
                        st.error(f"Unable to compute timepoint baseline/Δ table: {exc}")

                    if tp_table.empty:
                        st.info(
                            "No timepoint summaries could be produced yet. "
                            "Ensure your HRV measurements are saved with a timepoint label (T0…T21)."
                        )
                    else:
                        st.dataframe(tp_table, use_container_width=True)
                        st.caption(
                            "Columns prefixed with `baseline_` are the baseline values (T0), and `delta_` columns are "
                            "computed as (timepoint_value − baseline_value)."
                        )

        # Additional performance & recovery visuals
        with st.expander("🏃 Performance & Recovery plots", expanded=False):
            # lnRMSSD is commonly used for daily recovery tracking; we plot it without
            # attaching thresholds/interpretation here.
            if "rmssd_ms" in df.columns and df["rmssd_ms"].notna().any():
                ln_df = df[["measurement_date", "rmssd_ms"]].copy()
                ln_df = ln_df[(ln_df["rmssd_ms"].notna()) & (ln_df["rmssd_ms"] > 0)]
                if not ln_df.empty:
                    ln_df = ln_df.set_index("measurement_date").sort_index()
                    ln_df["ln_rmssd"] = np.log(ln_df["rmssd_ms"].astype(float))
                    _render_profile_line_chart(
                        ln_df[["ln_rmssd"]],
                        title="lnRMSSD trend",
                        y_axis_label="ln(ms)",
                    )

            hr_cols = [c for c in ["mean_hr_bpm", "sdhr_bpm"] if c in df.columns and df[c].notna().any()]
            if hr_cols:
                hr_df = df.set_index("measurement_date")[hr_cols]
                _render_profile_line_chart(
                    hr_df,
                    title="Heart rate trend",
                    y_axis_label="bpm",
                )

            idx_cols = [
                c
                for c in ["stress_index", "parasympathetic_index", "hrv_score"]
                if c in df.columns and df[c].notna().any()
            ]
            if idx_cols:
                idx_df = df.set_index("measurement_date")[idx_cols]
                _render_profile_line_chart(
                    idx_df,
                    title="Autonomic / recovery indices",
                    y_axis_label="index",
                )

            qual_cols = [
                c
                for c in ["artifact_percentage", "quality_score"]
                if c in df.columns and df[c].notna().any()
            ]
            if qual_cols:
                qual_df = df.set_index("measurement_date")[qual_cols]
                _render_profile_line_chart(
                    qual_df,
                    title="Data quality trend",
                    y_axis_label="% / score",
                )

        # HRV × wearable/activity relationships (when daily metrics exist)
        with st.expander("🔗 HRV × Activity (Garmin daily metrics)", expanded=False):
            try:
                garmin_df = pd.DataFrame()
                if hasattr(db, "get_garmin_daily_dataframe"):
                    garmin_df = db.get_garmin_daily_dataframe(user.user_id, limit=365)  # type: ignore[attr-defined]
                elif hasattr(db, "get_garmin_daily_metrics"):
                    rows = db.get_garmin_daily_metrics(user.user_id, limit=365)  # type: ignore[attr-defined]
                    if rows:
                        garmin_df = pd.DataFrame([r.to_dict() for r in rows])
            except Exception:
                garmin_df = pd.DataFrame()

            if garmin_df.empty or "metric_date" not in garmin_df.columns:
                st.info("No Garmin daily metrics available yet for activity/recovery overlays.")
            else:
                garmin_df = garmin_df.copy()
                garmin_df["metric_date"] = pd.to_datetime(garmin_df["metric_date"], errors="coerce")
                garmin_df = garmin_df.dropna(subset=["metric_date"])
                if garmin_df.empty:
                    st.info("No usable Garmin dates found yet.")
                else:
                    garmin_daily_cols = [
                        c
                            for c in [
                                "steps",
                                "distance_km",
                                "calories_kcal",
                                "sleep_score",
                                "sleep_efficiency",
                                "sleep_duration_hours",
                                "resting_hr_bpm",
                                "hrv_rmssd_ms",
                                "stress_score",
                                "avg_spo2",
                                "avg_respiration_sleep",
                                "body_battery_avg",
                            ]
                        if c in garmin_df.columns and garmin_df[c].notna().any()
                    ]
                    if not garmin_daily_cols:
                        st.info("Garmin metrics found, but no activity/recovery fields are populated yet.")
                    else:
                        garmin_daily = garmin_df.set_index("metric_date")[garmin_daily_cols].sort_index()

                        # Aggregate HRV to daily medians for fair alignment with daily Garmin metrics.
                        hrv_daily_cols = [
                            c
                            for c in ["rmssd_ms", "sdnn_ms", "mean_hr_bpm"]
                            if c in df.columns and df[c].notna().any()
                        ]
                        hrv_daily = pd.DataFrame()
                        if hrv_daily_cols and "measurement_date" in df.columns:
                            hrv_tmp = df[["measurement_date"] + hrv_daily_cols].copy()
                            hrv_tmp["measurement_date"] = pd.to_datetime(hrv_tmp["measurement_date"], errors="coerce")
                            hrv_tmp = hrv_tmp.dropna(subset=["measurement_date"])
                            if not hrv_tmp.empty:
                                hrv_tmp["day"] = hrv_tmp["measurement_date"].dt.normalize()
                                hrv_daily = (
                                    hrv_tmp.groupby("day", as_index=True)[hrv_daily_cols]
                                    .median()
                                    .sort_index()
                                )

                        if hrv_daily.empty:
                            st.info("HRV history is available, but not enough daily values to align with Garmin yet.")
                        else:
                            merged = hrv_daily.join(garmin_daily, how="inner")
                            if merged.empty:
                                st.info("No overlapping days between HRV measurements and Garmin daily metrics yet.")
                            else:
                                # Time series: activity alongside HRV (separate charts for units)
                                if "steps" in merged.columns and merged["steps"].notna().any():
                                    _render_profile_line_chart(
                                        merged[["steps"]],
                                        title="Daily steps",
                                        y_axis_label="steps",
                                    )
                                if "rmssd_ms" in merged.columns and merged["rmssd_ms"].notna().any():
                                    _render_profile_line_chart(
                                        merged[["rmssd_ms"]],
                                        title="Daily median RMSSD",
                                        y_axis_label="ms",
                                    )

                                # Scatter relationships (shown only when both sides exist)
                                scatter_pairs = [
                                    ("steps", "rmssd_ms", "RMSSD vs Steps", "Steps", "RMSSD (ms)"),
                                    ("distance_km", "rmssd_ms", "RMSSD vs Distance", "Distance (km)", "RMSSD (ms)"),
                                    ("calories_kcal", "rmssd_ms", "RMSSD vs Calories", "Calories (kcal)", "RMSSD (ms)"),
                                    ("sleep_score", "rmssd_ms", "RMSSD vs Sleep Score", "Sleep Score", "RMSSD (ms)"),
                                    ("stress_score", "rmssd_ms", "RMSSD vs Stress Score", "Stress Score", "RMSSD (ms)"),
                                    ("body_battery_avg", "rmssd_ms", "RMSSD vs Body Battery", "Body Battery (avg)", "RMSSD (ms)"),
                                ]
                                for x_col, y_col, title, xlab, ylab in scatter_pairs:
                                    if x_col not in merged.columns or y_col not in merged.columns:
                                        continue
                                    paired = merged[[x_col, y_col]].dropna()
                                    if len(paired) < 3:
                                        continue
                                    _render_profile_scatter_chart(
                                        merged,
                                        x_col=x_col,
                                        y_col=y_col,
                                        title=title,
                                        x_axis_label=xlab,
                                        y_axis_label=ylab,
                                    )
                                    corr = paired[x_col].corr(paired[y_col])
                                    if corr is not None and not pd.isna(corr):
                                        st.caption(f"{title}: Pearson r = {corr:.2f} (n={len(paired)})")
        
        # Full data table
        with st.expander("📊 All HRV Measurements"):
            st.dataframe(df, use_container_width=True)
        
    except Exception as exc:
        if DATABASE_AVAILABLE and is_sqlite_database_corruption_error(exc):
            _render_sqlite_corruption_recovery_ui(
                context_label="HRV measurement history",
                user_id=str(user.user_id),
                exc=exc,
            )
            return
        st.error(f"Failed to load HRV history: {exc}")


@_fragment_if_available
def _render_profile_readiness(user: UserProfile) -> None:
    """Render readiness & recovery assessment from stored profile history."""
    st.markdown("## 🏃 Readiness & Recovery Assessment")
    st.caption(
        "Uses the **Parasympathetic Index** saved with your HRV measurements to compare your current state "
        "against a selectable personal baseline."
    )

    try:
        db = get_database()
        df = db.get_hrv_dataframe(
            user.user_id,
            limit=365,
            include_rr=False,
            columns=(
                "measurement_id",
                "measurement_date",
                "source_file",
                "file_hash",
                "parasympathetic_index",
                "sdnn_ms",
                "rmssd_ms",
                "lf_hf_ratio",
                "hf_power_ms2",
                "created_at",
            ),
        )
    except Exception as exc:  # noqa: BLE001
        st.error(f"Unable to load readiness history: {exc}")
        return

    if df.empty:
        st.info("No stored HRV measurements found yet. Run an HRV analysis to populate readiness history.")
        return

    df = df.copy()
    df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce")
    df["created_at"] = pd.to_datetime(df.get("created_at"), errors="coerce")
    df = df.dropna(subset=["measurement_date"])
    df = df.sort_values(["measurement_date", "created_at"], ascending=True)

    labels: List[str] = []
    pns_map: Dict[str, float] = {}
    row_map: Dict[str, pd.Series] = {}
    collision_counter: Dict[str, int] = {}

    for _, row in df.iterrows():
        try:
            pns_val = float(row.get("parasympathetic_index", np.nan))
        except (TypeError, ValueError):
            pns_val = float("nan")
        if not np.isfinite(pns_val):
            continue
        ts = row.get("measurement_date")
        date_label = (
            pd.to_datetime(ts).date().isoformat() if ts is not None else "unknown-date"
        )
        src = str(row.get("source_file") or "HRV session")
        suffix = str(row.get("file_hash") or "").strip()
        suffix = suffix[:8] if suffix else str(row.get("measurement_id") or "")[:8]
        base_label = f"{date_label} · {src}"
        if suffix:
            base_label = f"{base_label} · {suffix}"
        count = collision_counter.get(base_label, 0)
        collision_counter[base_label] = count + 1
        label = base_label if count == 0 else f"{base_label} ({count + 1})"

        labels.append(label)
        pns_map[label] = pns_val
        row_map[label] = row

    if not labels:
        st.info(
            "No parasympathetic index values were found in your stored measurements yet. "
            "Run HRV analysis with readiness metrics enabled."
        )
        return

    default_idx = max(len(labels) - 1, 0)
    current_sel = st.selectbox(
        "Current measurement",
        options=labels,
        index=default_idx,
        key=f"profile_readiness_current_{user.user_id}",
    )
    default_baseline = [name for name in labels if name != current_sel]
    baseline_sel = st.multiselect(
        "Historical baseline datasets (oldest to newest)",
        options=labels,
        default=default_baseline,
        key=f"profile_readiness_baseline_{user.user_id}",
    )
    include_current = st.checkbox(
        "Include current measurement in baseline",
        value=False,
        key=f"profile_readiness_include_current_{user.user_id}",
    )
    min_hist = int(
        st.number_input(
            "Minimum historical samples",
            min_value=3,
            max_value=30,
            value=7,
            step=1,
            key=f"profile_readiness_min_hist_{user.user_id}",
        )
    )
    max_default = int(max(min_hist, min(30, len(labels))))
    max_hist = int(
        st.slider(
            "Historical window (max records retained)",
            min_value=min_hist,
            max_value=90,
            value=max_default,
            step=1,
            key=f"profile_readiness_max_hist_{user.user_id}",
        )
    )

    history_names: List[str] = []
    for name in labels:
        if name in baseline_sel and (include_current or name != current_sel):
            history_names.append(name)
    if include_current and current_sel not in history_names:
        history_names.append(current_sel)

    if not history_names:
        st.warning("Select at least one baseline record to build readiness baseline.")
        return

    history_values = [pns_map[name] for name in labels if name in history_names]
    if len(history_values) < int(min_hist):
        st.info(
            f"Readiness baseline needs at least {int(min_hist)} samples; currently {len(history_values)}."
        )
        return

    try:
        baseline = build_readiness_baseline(
            history_values,
            min_samples=min_hist,
            max_samples=max_hist,
        )
    except ValueError as exc:
        st.warning(f"Baseline configuration issue: {exc}")
        return

    current_pns = float(pns_map.get(current_sel, np.nan))
    if not np.isfinite(current_pns):
        st.warning("Current measurement lacks a valid parasympathetic index.")
        return

    readiness = readiness_from_pns(current_pns, baseline)
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Readiness score (percentile)", f"{readiness['readiness_score']:.1f}")
    col_b.metric("Category", readiness["readiness_category"])
    col_c.metric("PNS index", f"{readiness['pns_index']:.3f}")

    # Baseline chart (ECharts)
    history_labels = history_names.copy()
    if current_sel not in history_labels:
        history_labels.append(current_sel)
    line_series = {
        "name": "Baseline PNS history",
        "type": "line",
        "showSymbol": True,
        "smooth": True,
        "data": [[label, float(pns_map[label])] for label in history_names],
    }
    current_series = {
        "name": f"{current_sel} (current)",
        "type": "scatter",
        "symbolSize": 12,
        "itemStyle": {"color": "#1e88e5"},
        "data": [[current_sel, readiness["pns_index"]]],
    }
    opt = {
        "title": {"text": "Parasympathetic index baseline", "left": "center"},
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 32, "right": 16, "containLabel": True},
        "xAxis": {"type": "category", "name": "Session", "data": history_labels, "boundaryGap": False},
        "yAxis": {"type": "value", "name": "PNS index"},
        "legend": {"top": 24},
        "series": [line_series, current_series],
    }
    mark_lines = [
        {"yAxis": readiness["very_low_cut"], "name": "Very low cut"},
        {"yAxis": readiness["low_cut"], "name": "Low cut"},
        {"yAxis": readiness["high_cut"], "name": "High cut"},
    ]
    line_series["markLine"] = {"symbol": "none", "data": mark_lines}
    render_echarts(opt, height_px=360, width="100%", config=EChartsConfig())

    with st.expander("🎯 HRV Metric Gauges (selected session)", expanded=False):
        row = row_map.get(current_sel)
        if row is None:
            st.info("Selected session details unavailable for gauges.")
        else:
            _render_profile_hrv_metric_gauges(row, key_suffix=user.user_id)


# ---------------------------------------------------------------------------
# Data Export/Import
# ---------------------------------------------------------------------------


def _render_data_management(user: UserProfile) -> None:
    """Render data export/import section."""
    st.markdown("## 📦 Data Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Export Data")
        if st.button("📥 Export All User Data", use_container_width=True):
            try:
                import json
                db = get_database()
                
                export_data = {
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "user_profile": user.to_dict(),
                    "clinical_scales": [s.to_dict() for s in db.get_clinical_scales_history(user.user_id)],
                    "hrv_measurements": [m.to_dict() for m in db.get_hrv_history(user.user_id)],
                    "garmin_daily_metrics": [g.to_dict() for g in db.get_garmin_daily_metrics(user.user_id)],
                    "body_composition": [b.to_dict() for b in db.get_body_composition_history(user.user_id)],
                    "exploration_medical_history": db.get_medical_history(user.user_id, limit=500),
                }
                
                json_str = json.dumps(export_data, indent=2, default=str)
                st.download_button(
                    "💾 Download JSON",
                    data=json_str,
                    file_name=f"{user.username}_data_export.json",
                    mime="application/json",
                )
                
            except Exception as exc:
                st.error(f"Export failed: {exc}")
    
    with col2:
        st.markdown("### Account Actions")
        
        if st.button("🚪 Logout", use_container_width=True):
            _set_current_user(None)
            st.session_state.pop("edit_profile_mode", None)
            st.rerun()
        
        st.markdown("---")
        
        with st.expander("⚠️ Danger Zone"):
            st.warning("Deleting your account will remove all data permanently.")
            if st.button("🗑️ Delete Account", type="secondary"):
                st.session_state["confirm_delete"] = True
            
            if st.session_state.get("confirm_delete"):
                st.error("Are you sure? This cannot be undone.")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("Yes, Delete", type="primary"):
                        try:
                            db = get_database()
                            db.delete_user(user.user_id)
                            _set_current_user(None)
                            st.session_state.pop("confirm_delete", None)
                            st.success("Account deleted.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Delete failed: {exc}")
                with col_no:
                    if st.button("Cancel"):
                        st.session_state.pop("confirm_delete", None)
                        st.rerun()


def _render_fit_csv_tools(user: UserProfile) -> None:
    """Provide FIT→CSV conversion and CSV ingestion within the Data tab."""
    st.markdown("## 🗂️ FIT ↔ CSV Tools")
    st.caption(
        "Convert Garmin FIT to CSV for quick sharing, and ingest existing Garmin CSVs into this profile."
    )

    if not GARMIN_IMPORT_AVAILABLE:
        st.info(
            "FIT conversion requires the Garmin import module and fitparse. "
            "Install `fitparse` to enable this feature."
        )
        return

    try:
        manager = create_user_manager()
        manager.set_current_user(
            user_id=user.user_id,
            name=user.full_name or user.username or "User",
            create_if_missing=True,
        )
    except Exception as exc:  # pragma: no cover - defensive
        st.error(f"Unable to prepare storage for this profile: {exc}")
        return

    col_conv, col_csv = st.columns(2)

    with col_conv:
        st.subheader("Convert FIT to CSV")
        fit_file = st.file_uploader(
            "Upload FIT",
            type=["fit"],
            key=f"fit_to_csv_{user.user_id}",
            accept_multiple_files=False,
        )
        if fit_file is not None:
            tmp_path: Optional[Path] = None
            fit_bytes = fit_file.read()
            try:
                with NamedTemporaryFile(delete=False, suffix=".fit") as tmp:
                    tmp.write(fit_bytes)
                    tmp_path = Path(tmp.name)
                df, csv_bytes = convert_fit_to_csv(tmp_path)
            except Exception as exc:  # noqa: BLE001
                if log_exception is not None:
                    log_exception(_LOGGER, "FIT→CSV conversion failed", exc)
                st.error(f"Conversion failed: {exc}")
                if tmp_path is not None and tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
            else:
                if tmp_path is not None and tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
                csv_name = f"{Path(fit_file.name).stem}.csv"
                preview = df.head(10) if not df.empty else pd.DataFrame()
                if not preview.empty:
                    st.dataframe(preview, use_container_width=True)
                st.download_button(
                    "⬇️ Download CSV",
                    data=csv_bytes,
                    file_name=csv_name,
                    mime="text/csv",
                    use_container_width=True,
                )
                try:
                    manager.store_device_file(
                        fit_bytes, fit_file.name, device_type="garmin_fit"
                    )
                    manager.store_device_file(
                        csv_bytes, csv_name, device_type="garmin_csv"
                    )
                    st.success("FIT and converted CSV saved to this profile.")
                except Exception as exc:  # pragma: no cover - defensive
                    _LOGGER.warning("Failed to store converted files: %s", exc)
                    st.warning(
                        "Conversion succeeded, but saving to profile storage failed."
                    )

    with col_csv:
        st.subheader("Import Garmin CSV")
        csv_file = st.file_uploader(
            "Upload Garmin CSV",
            type=["csv"],
            key=f"garmin_csv_import_{user.user_id}",
            accept_multiple_files=False,
        )
        if csv_file is not None:
            csv_bytes = csv_file.read()
            try:
                preview_df = pd.read_csv(
                    io.BytesIO(csv_bytes),
                    nrows=200,
                    low_memory=False,
                )
                if not preview_df.empty:
                    st.dataframe(preview_df.head(10), use_container_width=True)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Unable to read CSV: {exc}")
                preview_df = None
            try:
                manager.store_device_file(
                    csv_bytes, csv_file.name, device_type="garmin_csv"
                )
                st.success("CSV stored under this profile.")
            except Exception as exc:  # pragma: no cover - defensive
                _LOGGER.warning("Failed to store CSV import: %s", exc)
                st.warning("Stored preview only; saving to disk failed.")


def _render_garmin_ingest(user: UserProfile) -> None:
    """Render Garmin Vivosmart 5 ingest to populate clinical gauges."""
    st.markdown("## ⌚ Wrist Monitoring (Vivosmart 5)")
    st.caption(
        "Upload a Garmin Vivosmart 5 FIT file or wellness ZIP export. "
        "Steps, distance, sleep score/efficiency, respiration (awake/sleep), "
        "SpO₂, stress, calories, and body battery will be stored in your profile history."
    )
    
    # Help section for complete data
    with st.expander("ℹ️ How to get complete wellness data (sleep, stress, body battery)", expanded=False):
        st.markdown("""
        **To export ALL wellness metrics from Garmin Connect:**
        
        1. Log into **Garmin Connect Web**: https://connect.garmin.com
        2. Go to **Account Settings** → **Account Information**
        3. Click **"Export Your Data"**
        4. Select **"Request Data Export"**
        5. Wait for email (usually 24 hours)
        6. Download the ZIP from the email link
        7. Upload here
        
        **Complete export includes:** `DI_CONNECT/DI-Connect-Wellness/` folder with:
        - `YYYY-MM-DD_sleepData.json` → Sleep score, stages, duration
        - `YYYY-MM-DD_stressData.json` → Stress levels
        - `YYYY-MM-DD_bodyBatteryData.json` → Body Battery
        - `YYYY-MM-DD_spo2Data.json` → Pulse oximeter
        - `YYYY-MM-DD_respirationData.json` → Breathing rate
        
        **Note:** Individual activity FIT files only contain steps/distance/calories.
        """)

    if not GARMIN_IMPORT_AVAILABLE:
        st.info("Garmin import module unavailable. Ensure fitparse is installed and garmin_import.py is present.")
        return

    uploaded = st.file_uploader(
        "Select FIT, Garmin wellness ZIP, or Garmin export JSON",
        type=["fit", "zip", "json"],
        key=f"garmin_ingest_{user.user_id}",
        accept_multiple_files=False,
    )

    if uploaded is None:
        return

    suffix = Path(uploaded.name).suffix.lower()
    if suffix not in {".fit", ".zip", ".json"}:
        st.error("Unsupported file type. Please upload a .fit, Garmin wellness .zip export, or a Garmin export .json file.")
        return

    with st.spinner("Parsing Garmin data..."):
        temp_path: Optional[Path] = None
        try:
            with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded.read())
                temp_path = Path(tmp.name)

            data = import_garmin_data(
                fit_path=temp_path if suffix == ".fit" else None,
                zip_path=temp_path if suffix == ".zip" else None,
                json_path=temp_path if suffix == ".json" else None,
            )
            daily_df = get_daily_physiology_summary(data)
        except Exception as exc:  # noqa: BLE001
            if log_exception is not None:
                log_exception(_LOGGER, "Garmin ingest failed", exc)
            st.error(f"Failed to parse Garmin file: {exc}")
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)
            return
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    if daily_df.empty:
        st.warning("No usable Garmin wellness metrics were found in the file.")
        return

    entries: List[GarminDailyMetrics] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # Also persist any pending sidebar ingestion if present
    pending_sidebar = st.session_state.pop("garmin_daily_pending", None)
    if pending_sidebar:
        pending_df = pd.DataFrame(pending_sidebar)
        if not pending_df.empty:
            daily_df = pd.concat([daily_df, pending_df], ignore_index=True)

    for _, row in daily_df.iterrows():
        day_val = row.get("date")
        if pd.isna(day_val):
            continue
        metric_date = pd.to_datetime(day_val).date().isoformat()
        avg_hr = _safe_float(row.get("avg_hr_session")) or _safe_float(row.get("avg_hr"))
        resting_hr = _safe_float(row.get("resting_hr_bpm")) or _safe_float(row.get("min_hr"))
        entries.append(
            GarminDailyMetrics(
                entry_id=str(uuid.uuid4()),
                user_id=user.user_id,
                metric_date=metric_date,
                steps=_safe_int(row.get("steps")),
                distance_km=_safe_float(row.get("distance_km")),
                calories_kcal=_safe_float(row.get("calories_kcal")),
                avg_hr_bpm=avg_hr,
                resting_hr_bpm=resting_hr,
                stress_score=_safe_float(row.get("avg_stress")),
                sleep_score=_safe_float(row.get("sleep_score")),
                sleep_efficiency=_safe_float(row.get("sleep_efficiency")),
                sleep_duration_hours=_safe_float(row.get("sleep_duration_hours")),
                avg_spo2=_safe_float(row.get("avg_sleep_spo2")) or _safe_float(row.get("avg_spo2")),
                avg_respiration_awake=_safe_float(row.get("avg_respiration_awake")),
                avg_respiration_sleep=_safe_float(row.get("avg_sleep_respiration")),
                body_battery_avg=_safe_float(row.get("body_battery_avg")) or _safe_float(row.get("avg_body_battery")),
                body_battery_charge=_safe_float(row.get("body_battery_charge")),
                body_battery_drain=_safe_float(row.get("body_battery_drain")),
                source=data.source,
                created_at=now_iso,
            )
        )

    try:
        db = get_database()
        db.save_garmin_daily_metrics(entries)
        st.cache_data.clear()
        st.success(f"Saved {len(entries)} day(s) of Garmin wellness metrics to the profile.")
        
        # Check what data was captured
        has_sleep = not data.sleep_df.empty
        has_stress = not data.stress_df.empty
        has_body_battery = not data.body_battery_df.empty
        has_spo2 = not data.spo2_df.empty
        has_respiration = not data.respiration_df.empty
        
        if not (has_sleep or has_stress or has_body_battery or has_spo2 or has_respiration):
            st.warning(
                "⚠️ **Only steps/distance/calories were extracted.** "
                "To get sleep, stress, body battery, SpO₂, and respiration data, "
                "request a complete 'Export Your Data' from Garmin Connect (not individual activity files). "
                "See the help section above for instructions."
            )
        
        st.dataframe(
            daily_df.sort_values("date", ascending=False).head(5),
            use_container_width=True,
        )
    except Exception as exc:  # noqa: BLE001
        if log_exception is not None:
            log_exception(_LOGGER, "Failed to persist Garmin daily metrics", exc)
        st.error(f"Unable to save Garmin metrics: {exc}")


# ---------------------------------------------------------------------------
# Clinical Profile Section (NASA Nutrition, Body Composition)
# ---------------------------------------------------------------------------

# Import clinical profile module if available
try:
    from clinical_profile import (
        BiologicalSex,
        ActivityLevel,
        calculate_comprehensive_requirements,
        calculate_nasa_water_requirement,
        PAL_MULTIPLIERS,
        EXERCISE_METS,
    )
    CLINICAL_PROFILE_AVAILABLE = True
except ImportError:
    CLINICAL_PROFILE_AVAILABLE = False

# Import personalized computations module if available
try:
    from personalized_computations import (
        calculate_body_fat_navy,
        calculate_sleep_apnea_risk,
        get_personalized_hrv_norms,
        interpret_hrv_metric_personalized,
        classify_fitness_by_vo2max,
        calculate_personalized_hydration,
        assess_cardiovascular_risk,
        calculate_all_personalized_metrics,
        RiskLevel,
        FitnessCategory,
        BodyFatCategory,
    )
    PERSONALIZED_COMPUTATIONS_AVAILABLE = True
except ImportError:
    PERSONALIZED_COMPUTATIONS_AVAILABLE = False

# Import Profile Tools Engine for SAFTE, recovery, and readiness calculations
try:
    from profile_tools_engine import (
        calculate_recovery_score,
        calculate_training_readiness,
        predict_fatigue,
        analyze_hrv_personalized,
        generate_performance_forecast,
        predict_operational_performance,
        run_all_profile_tools,
        RecoveryStatus,
        ReadinessLevel,
        FatigueRisk,
        OperationalReadinessLevel,
    )
    PROFILE_TOOLS_ENGINE_AVAILABLE = True
except ImportError:
    PROFILE_TOOLS_ENGINE_AVAILABLE = False

# Import Polar AccessLink module if available
try:
    from polar_accesslink import (
        PolarAccessLinkClient,
        polar_accesslink_available,
        fetch_polar_vo2max,
        save_manual_vo2max,
    )
    POLAR_MODULE_AVAILABLE = True
except ImportError:
    POLAR_MODULE_AVAILABLE = False
    def polar_accesslink_available() -> bool:  # type: ignore[misc]
        return False
    def fetch_polar_vo2max() -> None:  # type: ignore[misc]
        return None


def _render_clinical_profile(user: UserProfile) -> None:
    """Render comprehensive clinical profile with NASA calculations."""
    st.markdown("## 🏥 Comprehensive Clinical Profile")
    
    if not CLINICAL_PROFILE_AVAILABLE:
        st.warning(
            "Clinical profile module not available. "
            "Ensure `clinical_profile.py` is in the app directory."
        )
        return
    
    # Data completeness check
    _render_data_completeness(user)
    
    st.markdown("---")
    
    # NASA Nutrition Calculator
    with st.expander("🚀 NASA Nutrition Calculator", expanded=True):
        _render_nasa_calculator(user)
    
    # Body Composition
    with st.expander("📏 Body Composition", expanded=False):
        _render_body_composition_form(user)
    
    # Medical History Summary
    with st.expander("📋 Medical History", expanded=False):
        _render_medical_history_summary(user)
    
    with st.expander("🧾 Exploration Medical Record", expanded=False):
        _render_medical_record_form(user)
    
    with st.expander("📊 Exploration Medical Analytics", expanded=False):
        _render_exploration_medical_analytics(user)
    
    # Personalized Health Metrics (NEW)
    with st.expander("🎯 Personalized Health Metrics", expanded=False):
        _render_personalized_health_metrics(user)
    
    # Profile Tools Engine - SAFTE, Recovery, Readiness
    with st.expander("🛠️ Profile Tools Engine", expanded=False):
        _render_profile_tools_engine(user)


@_fragment_if_available
def _render_profile_tools_engine(user: UserProfile) -> None:
    """Render Profile Tools Engine for SAFTE, recovery, and readiness calculations.
    
    Provides comprehensive calculation engines accessible per user profile:
    - SAFTE fatigue prediction using profile data
    - HRV analysis with personalized interpretation
    - Recovery score calculations
    - Training readiness assessment
    - Performance forecasting
    """
    st.markdown("#### 🛠️ Profile Tools Engine")
    st.caption(
        "Comprehensive calculation engines using your profile data. "
        "Run SAFTE fatigue models, recovery analysis, and readiness assessments."
    )
    
    if not PROFILE_TOOLS_ENGINE_AVAILABLE:
        st.warning(
            "Profile Tools Engine not available. "
            "Ensure `profile_tools_engine.py` is in the app directory."
        )
        return
    
    # Check for required data
    if not all([user.height_cm, user.weight_kg, user.date_of_birth, user.sex]):
        st.info(
            "Complete your profile (height, weight, age, sex) to use the Profile Tools Engine. "
            "Click 'Edit Profile' above."
        )
        return
    
    age = _calculate_age(user.date_of_birth)
    if age is None:
        st.error("Could not calculate age from date of birth.")
        return
    
    sex = user.sex or "other"
    current_hour = datetime.now().hour
    
    # Tool selector
    st.markdown("##### 🔧 Select Tool")
    tool_options = [
        "📊 All Tools Summary",
        "🔋 Recovery Score",
        "🏃 Training Readiness",
        "😴 Fatigue Prediction (SAFTE)",
        "🧠 Operational Performance (HRV+SAFTE)",
        "💓 Personalized HRV Analysis",
        "📈 Performance Forecast",
    ]
    selected_tool = st.selectbox(
        "Choose a calculation tool",
        options=tool_options,
        key=f"profile_tool_select_{user.user_id}",
    )
    
    st.markdown("---")
    
    # Input parameters for calculations
    # NOTE: Streamlit expanders cannot be nested. This section is rendered inside an
    # outer expander ("🛠️ Profile Tools Engine"), so we use a checkbox to collapse.
    chronotype_map = {
        "Morning (-2h)": -2.0,
        "Slight morning (-1h)": -1.0,
        "Neutral (0h)": 0.0,
        "Slight evening (+1h)": 1.0,
        "Evening (+2h)": 2.0,
    }
    show_parameters = st.checkbox(
        "⚙️ Show calculation parameters",
        value=True,
        key=f"profile_tools_show_params_{user.user_id}",
        help="Hide to reduce clutter; values are preserved in session state.",
    )
    if show_parameters:
        col1, col2, col3 = st.columns(3)

        with col1:
            _ = st.number_input(  # widget persists to session_state via key
                "Sleep hours (last night)",
                min_value=0.0,
                max_value=14.0,
                value=7.0,
                step=0.5,
                key=f"tools_sleep_hours_{user.user_id}",
            )
            _ = st.slider(  # widget persists to session_state via key
                "Sleep quality (0-1)",
                min_value=0.0,
                max_value=1.0,
                value=0.7,
                step=0.1,
                key=f"tools_sleep_quality_{user.user_id}",
            )

        with col2:
            _ = st.number_input(  # widget persists to session_state via key
                "Hours awake",
                min_value=0.0,
                max_value=48.0,
                value=float(current_hour - 7 if current_hour >= 7 else current_hour + 17),
                step=0.5,
                key=f"tools_hours_awake_{user.user_id}",
            )
            _ = st.selectbox(  # widget persists to session_state via key
                "Chronotype",
                options=[
                    "Morning (-2h)",
                    "Slight morning (-1h)",
                    "Neutral (0h)",
                    "Slight evening (+1h)",
                    "Evening (+2h)",
                ],
                index=2,
                key=f"tools_chronotype_{user.user_id}",
            )

        with col3:
            _ = st.number_input(  # widget persists to session_state via key
                "RMSSD (ms) - from HRV",
                min_value=0.0,
                max_value=200.0,
                value=35.0,
                step=1.0,
                help="Enter your latest RMSSD value from HRV analysis",
                key=f"tools_rmssd_{user.user_id}",
            )
            _ = st.number_input(  # widget persists to session_state via key
                "Resting HR (bpm)",
                min_value=30,
                max_value=120,
                value=int(user.resting_hr_bpm or 65),
                step=1,
                key=f"tools_resting_hr_{user.user_id}",
            )

    # Ensure variables exist even when parameter widgets are hidden.
    sleep_hours_raw = _safe_float(st.session_state.get(f"tools_sleep_hours_{user.user_id}"))
    sleep_hours = float(sleep_hours_raw) if sleep_hours_raw is not None else 7.0

    sleep_quality_raw = _safe_float(st.session_state.get(f"tools_sleep_quality_{user.user_id}"))
    sleep_quality = float(sleep_quality_raw) if sleep_quality_raw is not None else 0.7

    hours_awake_default = float(current_hour - 7 if current_hour >= 7 else current_hour + 17)
    hours_awake_raw = _safe_float(st.session_state.get(f"tools_hours_awake_{user.user_id}"))
    hours_awake = float(hours_awake_raw) if hours_awake_raw is not None else hours_awake_default

    chronotype = str(st.session_state.get(f"tools_chronotype_{user.user_id}") or "Neutral (0h)")
    chronotype_offset = float(chronotype_map.get(chronotype, 0.0))

    rmssd_default = 35.0
    rmssd_raw = _safe_float(st.session_state.get(f"tools_rmssd_{user.user_id}"))
    rmssd_input = float(rmssd_raw) if rmssd_raw is not None else rmssd_default

    resting_hr_default = int(user.resting_hr_bpm or 65)
    resting_hr_raw = _safe_float(st.session_state.get(f"tools_resting_hr_{user.user_id}"))
    resting_hr = float(resting_hr_raw) if resting_hr_raw is not None else float(resting_hr_default)
    
    # Run calculations button
    if st.button("🚀 Run Calculations", type="primary", key=f"run_tools_{user.user_id}"):
        st.markdown("---")
        
        # Prepare HRV metrics dict for analysis
        hrv_metrics = {
            "rmssd_ms": rmssd_input,
            "resting_hr": resting_hr,
        }
        
        # Load additional HRV metrics from database if available
        try:
            db = get_database()
            hrv_history = db.get_hrv_measurement_history(user.user_id, limit=1)
            if hrv_history:
                latest_hrv = hrv_history[0]
                if hasattr(latest_hrv, 'metrics_json') and latest_hrv.metrics_json:
                    import json
                    stored_metrics = json.loads(latest_hrv.metrics_json) if isinstance(latest_hrv.metrics_json, str) else latest_hrv.metrics_json
                    hrv_metrics.update({
                        "sdnn_ms": stored_metrics.get("sdnn_ms", stored_metrics.get("sdnn")),
                        "pnn50": stored_metrics.get("pnn50_pct", stored_metrics.get("pnn50")),
                        "hf_power": stored_metrics.get("hf_power_ms2", stored_metrics.get("hf_power")),
                        "lf_power": stored_metrics.get("lf_power_ms2", stored_metrics.get("lf_power")),
                        "lf_hf_ratio": stored_metrics.get("lf_hf_ratio"),
                        "mean_rr_ms": stored_metrics.get("mean_rr_ms", stored_metrics.get("mean_rr")),
                    })
        except Exception:
            pass
        
        if selected_tool == "📊 All Tools Summary":
            _render_all_tools_summary(
                age, sex, user.weight_kg, user.height_cm,
                rmssd_input, hrv_metrics, sleep_hours, sleep_quality,
                hours_awake, current_hour, chronotype_offset, resting_hr,
                user.vo2max_ml_kg_min, user.activity_level or "moderate",
                user.user_id,
            )
        
        elif selected_tool == "🔋 Recovery Score":
            _render_recovery_score_tool(
                rmssd_input, age, sleep_hours, sleep_quality, resting_hr
            )
        
        elif selected_tool == "🏃 Training Readiness":
            _render_training_readiness_tool(
                rmssd_input, age, sleep_hours, sleep_quality, chronotype_offset
            )
        
        elif selected_tool == "😴 Fatigue Prediction (SAFTE)":
            _render_fatigue_prediction_tool(
                sleep_hours, sleep_quality, hours_awake, current_hour, chronotype_offset
            )
        
        elif selected_tool == "🧠 Operational Performance (HRV+SAFTE)":
            _render_operational_performance_tool(
                age=age,
                sex=sex,
                rmssd_ms=rmssd_input,
                hrv_metrics=hrv_metrics,
                sleep_hours=sleep_hours,
                sleep_quality=sleep_quality,
                hours_awake=hours_awake,
                current_hour=current_hour,
                chronotype_offset=chronotype_offset,
                resting_hr=resting_hr,
                user_id=user.user_id,
            )

        elif selected_tool == "💓 Personalized HRV Analysis":
            _render_hrv_analysis_tool(
                hrv_metrics, age, sex, resting_hr, user.activity_level or "moderate"
            )
        
        elif selected_tool == "📈 Performance Forecast":
            _render_performance_forecast_tool(
                current_hour, sleep_hours, chronotype_offset
            )


def _render_all_tools_summary(
    age: int, sex: str, weight_kg: float, height_cm: float,
    rmssd_ms: float, hrv_metrics: Dict[str, Any], sleep_hours: float,
    sleep_quality: float, hours_awake: float, current_hour: int,
    chronotype_offset: float, resting_hr: float, vo2max: Optional[float],
    activity_level: str, user_id: str
) -> None:
    """Render summary of all profile tools."""
    st.markdown("### 📊 Profile Tools Summary")
    
    with st.spinner("Computing profile tools (SAFTE, HRV, readiness)..."):
        results = run_all_profile_tools(
            age=age,
            sex=sex,
            weight_kg=weight_kg,
            height_cm=height_cm,
            rmssd_ms=rmssd_ms,
            hrv_metrics=hrv_metrics,
            sleep_hours=sleep_hours,
            sleep_quality=sleep_quality,
            hours_awake=hours_awake,
            current_hour=current_hour,
            chronotype_offset=chronotype_offset,
            resting_hr=resting_hr,
            vo2max=vo2max,
            activity_level=activity_level,
        )
    
    # Display summary cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if "recovery_score" in results:
            rec = results["recovery_score"]
            score = rec.get("score", 0)
            status = rec.get("status_label", "Unknown")
            if score >= 65:
                st.success(f"🔋 **Recovery**: {score:.0f}/100")
            elif score >= 50:
                st.warning(f"🔋 **Recovery**: {score:.0f}/100")
            else:
                st.error(f"🔋 **Recovery**: {score:.0f}/100")
            st.caption(status)
    
    with col2:
        if "training_readiness" in results:
            tr = results["training_readiness"]
            score = tr.get("readiness_score", 0)
            level = tr.get("level_label", "Unknown")
            if score >= 70:
                st.success(f"🏃 **Readiness**: {score:.0f}/100")
            elif score >= 50:
                st.warning(f"🏃 **Readiness**: {score:.0f}/100")
            else:
                st.error(f"🏃 **Readiness**: {score:.0f}/100")
            st.caption(level)
    
    with col3:
        if "fatigue_prediction" in results:
            fp = results["fatigue_prediction"]
            eff = fp.get("current_effectiveness", 0)
            risk = fp.get("risk_label", "Unknown")
            if eff >= 75:
                st.success(f"😴 **Effectiveness**: {eff:.0f}%")
            elif eff >= 65:
                st.warning(f"😴 **Effectiveness**: {eff:.0f}%")
            else:
                st.error(f"😴 **Effectiveness**: {eff:.0f}%")
            st.caption(risk)
    
    # HRV Analysis
    if "hrv_analysis" in results:
        st.markdown("---")
        st.markdown("##### 💓 Personalized HRV Status")
        hrv = results["hrv_analysis"]
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Parasympathetic Index", f"{hrv.get('parasympathetic_index', 0):.1f}/10")
            st.caption(hrv.get("autonomic_balance", ""))
        with col2:
            st.metric("Stress Index", f"{hrv.get('stress_index', 0):.0f}")
            st.caption(hrv.get("overall_status", ""))
    
    # Performance Forecast
    if "performance_forecast" in results:
        st.markdown("---")
        st.markdown("##### 📈 Performance Forecast")
        pf = results["performance_forecast"]
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Peak Performance", pf.get("peak_performance_time", "--:--"))
        with col2:
            st.metric("Low Point", pf.get("low_performance_time", "--:--"))
        
        # Show recommendations
        recs = pf.get("recommendations", [])
        if recs:
            show_recs = st.checkbox(
                "💡 Show recommendations",
                value=False,
                key=f"profile_tools_summary_show_recs_{user_id}",
            )
            if show_recs:
                for rec in recs:
                    st.markdown(f"- {rec}")

    # Operational performance (HRV + SAFTE)
    if "operational_performance" in results:
        st.markdown("---")
        st.markdown("##### 🧠 Operational Performance (HRV + SAFTE)")
        op = results["operational_performance"]
        score = float(op.get("readiness_score", 0.0) or 0.0)
        label = str(op.get("readiness_label", ""))
        if score >= 70:
            st.success(f"🧠 **Operational readiness**: {score:.0f}/100")
        elif score >= 55:
            st.warning(f"🧠 **Operational readiness**: {score:.0f}/100")
        else:
            st.error(f"🧠 **Operational readiness**: {score:.0f}/100")
        st.caption(label)
        drivers = op.get("drivers", {}) if isinstance(op.get("drivers"), dict) else {}
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("SAFTE effectiveness", f"{float(drivers.get('safte_effectiveness', 0.0) or 0.0):.0f}%")
        with col2:
            rec_val = drivers.get("recovery_score")
            st.metric("Recovery score", f"{float(rec_val or 0.0):.0f}/100" if rec_val is not None else "N/A")
        with col3:
            si_val = drivers.get("stress_index")
            st.metric("Stress index", f"{float(si_val or 0.0):.0f}" if si_val is not None else "N/A")
    
    # Export option
    st.markdown("---")
    if st.button("📥 Export Summary (Markdown)", key="export_tools_summary"):
        export_text = f"""# Profile Tools Summary
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## User Context
- Age: {age} years
- Sex: {sex}
- Current Hour: {current_hour}:00

## Recovery Score
- Score: {results.get('recovery_score', {}).get('score', 'N/A')}/100
- Status: {results.get('recovery_score', {}).get('status_label', 'N/A')}

## Training Readiness
- Score: {results.get('training_readiness', {}).get('readiness_score', 'N/A')}/100
- Level: {results.get('training_readiness', {}).get('level_label', 'N/A')}

## Fatigue Prediction
- Current Effectiveness: {results.get('fatigue_prediction', {}).get('current_effectiveness', 'N/A')}%
- Risk: {results.get('fatigue_prediction', {}).get('risk_label', 'N/A')}

## HRV Analysis
- Parasympathetic Index: {results.get('hrv_analysis', {}).get('parasympathetic_index', 'N/A')}/10
- Stress Index: {results.get('hrv_analysis', {}).get('stress_index', 'N/A')}
 
## Operational Performance (HRV + SAFTE)
- Operational readiness: {results.get('operational_performance', {}).get('readiness_score', 'N/A')}/100
- Category: {results.get('operational_performance', {}).get('readiness_label', 'N/A')}
"""
        st.code(export_text, language="markdown")


def _render_recovery_score_tool(
    rmssd_ms: float, age: int, sleep_hours: float,
    sleep_quality: float, resting_hr: float
) -> None:
    """Render recovery score calculation results."""
    st.markdown("### 🔋 Recovery Score")
    
    recovery = calculate_recovery_score(
        rmssd_ms=rmssd_ms,
        age=age,
        sleep_hours=sleep_hours,
        sleep_quality=sleep_quality,
        resting_hr=resting_hr,
    )
    
    # Main score display
    score = recovery.score
    if score >= 80:
        st.success(f"## {score:.0f}/100 — {recovery.status_label}")
    elif score >= 65:
        st.info(f"## {score:.0f}/100 — {recovery.status_label}")
    elif score >= 50:
        st.warning(f"## {score:.0f}/100 — {recovery.status_label}")
    else:
        st.error(f"## {score:.0f}/100 — {recovery.status_label}")
    
    # Component breakdown
    st.markdown("##### Component Breakdown")
    components = recovery.components
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("HRV Component", f"{components.get('hrv', 0):.1f}/50")
    with col2:
        st.metric("Sleep Component", f"{components.get('sleep', 0):.1f}/30")
    with col3:
        st.metric("Resting HR Component", f"{components.get('resting_hr', 0):.1f}/20")
    
    # lnRMSSD details
    if recovery.ln_rmssd:
        st.markdown("##### HRV Details")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("lnRMSSD", f"{recovery.ln_rmssd:.3f}")
        with col2:
            if recovery.ln_rmssd_baseline:
                st.metric("Baseline lnRMSSD", f"{recovery.ln_rmssd_baseline:.3f}")
    
    # Interpretation
    st.markdown("##### Interpretation")
    st.info(recovery.interpretation)
    
    # Recommendations
    st.markdown("##### Recommendations")
    for rec in recovery.recommendations:
        st.markdown(f"- {rec}")


def _render_training_readiness_tool(
    rmssd_ms: float, age: int, sleep_hours: float,
    sleep_quality: float, chronotype_offset: float
) -> None:
    """Render training readiness calculation results."""
    st.markdown("### 🏃 Training Readiness")
    
    readiness = calculate_training_readiness(
        rmssd_ms=rmssd_ms,
        age=age,
        sleep_hours=sleep_hours,
        sleep_quality=sleep_quality,
        chronotype_offset=chronotype_offset,
    )
    
    # Main score display
    score = readiness.readiness_score
    if score >= 85:
        st.success(f"## {score:.0f}/100 — {readiness.level_label}")
    elif score >= 70:
        st.info(f"## {score:.0f}/100 — {readiness.level_label}")
    elif score >= 50:
        st.warning(f"## {score:.0f}/100 — {readiness.level_label}")
    else:
        st.error(f"## {score:.0f}/100 — {readiness.level_label}")
    
    # Component breakdown
    st.markdown("##### Component Breakdown")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("HRV", f"{readiness.hrv_component:.1f}/35")
    with col2:
        st.metric("Sleep", f"{readiness.sleep_component:.1f}/25")
    with col3:
        st.metric("Fatigue", f"{readiness.fatigue_component:.1f}/20")
    with col4:
        st.metric("Strain", f"{readiness.strain_component:.1f}/20")
    
    # Interpretation
    st.markdown("##### Interpretation")
    st.info(readiness.interpretation)
    
    # Training recommendations
    st.markdown("##### Training Recommendations")
    for rec in readiness.training_recommendations:
        st.markdown(f"- {rec}")
    
    # Workout suggestions
    st.markdown("##### Suggested Workouts")
    for workout in readiness.workout_suggestions:
        st.markdown(f"- {workout}")


def _render_fatigue_prediction_tool(
    sleep_hours: float, sleep_quality: float, hours_awake: float,
    current_hour: int, chronotype_offset: float
) -> None:
    """Render SAFTE fatigue prediction results."""
    st.markdown("### 😴 Fatigue Prediction (SAFTE Model)")
    
    fatigue = predict_fatigue(
        sleep_hours_last_night=sleep_hours,
        sleep_quality=sleep_quality,
        hours_awake=hours_awake,
        current_hour=current_hour,
        chronotype_offset=chronotype_offset,
    )
    
    # Current effectiveness
    eff = fatigue.current_effectiveness
    if eff >= 85:
        st.success(f"## Current Effectiveness: {eff:.0f}%")
    elif eff >= 75:
        st.info(f"## Current Effectiveness: {eff:.0f}%")
    elif eff >= 65:
        st.warning(f"## Current Effectiveness: {eff:.0f}%")
    else:
        st.error(f"## Current Effectiveness: {eff:.0f}%")
    
    st.caption(f"Risk Level: {fatigue.risk_label}")
    
    # Predictions
    st.markdown("##### Effectiveness Forecast")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("In 4 hours", f"{fatigue.predicted_effectiveness_4h:.0f}%")
    with col2:
        st.metric("In 8 hours", f"{fatigue.predicted_effectiveness_8h:.0f}%")
    with col3:
        st.metric("In 24 hours", f"{fatigue.predicted_effectiveness_24h:.0f}%")
    
    # Sleep debt and circadian
    st.markdown("##### Status")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Sleep Debt", f"{fatigue.sleep_debt_hours:.1f}h")
    with col2:
        st.metric("Circadian Phase", fatigue.circadian_phase)
    with col3:
        st.metric("Optimal Bedtime", fatigue.optimal_sleep_time)
    
    # Performance curve visualization
    st.markdown("##### 24-Hour Performance Curve")
    if fatigue.performance_curve:
        curve_df = pd.DataFrame(fatigue.performance_curve, columns=["Hour", "Effectiveness"]).sort_values("Hour")
        hours = curve_df["Hour"].tolist()
        vals = curve_df["Effectiveness"].tolist()

        # Markers for current/4h/8h/24h if available
        markers: list[dict[str, Any]] = []
        key_points = {0: "Now", 4: "4h", 8: "8h", 24: "24h"}
        for h, label in key_points.items():
            if h in hours:
                idx = hours.index(h)
                markers.append({"name": label, "coord": [hours[idx], vals[idx]], "value": f"{vals[idx]:.0f}%"})

        options = {
            "tooltip": {"trigger": "axis", "formatter": "{b}h : {c}%"},
            "xAxis": {"type": "category", "data": hours, "name": "Hour", "boundaryGap": False},
            "yAxis": {"type": "value", "min": 40, "max": 100, "name": "Effectiveness (%)"},
            "series": [
                {
                    "name": "Effectiveness",
                    "type": "line",
                    "smooth": True,
                    "data": vals,
                    "areaStyle": {"opacity": 0.15},
                    "lineStyle": {"width": 3},
                    "markLine": {
                        "symbol": "none",
                        "data": [
                            {"yAxis": 85, "name": "GO"},
                            {"yAxis": 70, "name": "Monitor"},
                            {"yAxis": 55, "name": "Caution"},
                        ],
                        "label": {"formatter": "{b}"},
                    },
                    "markPoint": {"data": markers},
                }
            ],
            "legend": {"show": False},
            "grid": {"left": "10%", "right": "8%", "bottom": "12%", "top": "8%"},
        }
        render_echarts(EChartsConfig(options=options, height="320px"))
    
    # Recommendations
    if fatigue.recommendations:
        st.markdown("##### Recommendations")
        for rec in fatigue.recommendations:
            st.markdown(f"- {rec}")


def _render_hrv_analysis_tool(
    hrv_metrics: Dict[str, Any], age: int, sex: str,
    resting_hr: float, activity_level: str
) -> None:
    """Render personalized HRV analysis results."""
    st.markdown("### 💓 Personalized HRV Analysis")
    
    analysis = analyze_hrv_personalized(
        hrv_metrics=hrv_metrics,
        age=age,
        sex=sex,
        resting_hr=resting_hr,
        activity_level=activity_level,
    )
    
    # Main indices
    col1, col2 = st.columns(2)
    with col1:
        pns = analysis.parasympathetic_index
        if pns >= 7:
            st.success(f"## Parasympathetic Index: {pns:.1f}/10")
        elif pns >= 4:
            st.info(f"## Parasympathetic Index: {pns:.1f}/10")
        else:
            st.warning(f"## Parasympathetic Index: {pns:.1f}/10")
    
    with col2:
        stress = analysis.stress_index
        if stress < 100:
            st.success(f"## Stress Index: {stress:.0f}")
        elif stress < 200:
            st.info(f"## Stress Index: {stress:.0f}")
        else:
            st.warning(f"## Stress Index: {stress:.0f}")
    
    # Status
    st.markdown("##### Overall Status")
    st.info(f"**{analysis.overall_status}**\n\nAutonomic Balance: {analysis.autonomic_balance}")
    
    # Interpreted metrics table
    st.markdown("##### Metric Analysis")
    if analysis.metrics:
        metric_rows = []
        for name, data in analysis.metrics.items():
            if isinstance(data, dict):
                metric_rows.append({
                    "Metric": name.upper().replace("_MS", " (ms)").replace("_PCT", " (%)"),
                    "Value": f"{data.get('value', 'N/A')}",
                    "Status": data.get("status", "N/A").replace("_", " ").title(),
                    "Percentile": f"~{data.get('percentile_estimate', 'N/A')}th" if data.get('percentile_estimate') else "N/A",
                })
        if metric_rows:
            st.dataframe(pd.DataFrame(metric_rows), use_container_width=True, hide_index=True)
    
    # Clinical significance
    if analysis.clinical_significance:
        st.markdown("##### Clinical Significance")
        for sig in analysis.clinical_significance:
            st.markdown(f"- {sig}")
    
    # Recommendations
    if analysis.recommendations:
        st.markdown("##### Recommendations")
        for rec in analysis.recommendations:
            st.markdown(f"- {rec}")


def _render_performance_forecast_tool(
    current_hour: int, sleep_hours: float, chronotype_offset: float
) -> None:
    """Render 24-hour performance forecast results."""
    st.markdown("### 📈 Performance Forecast")
    
    forecast = generate_performance_forecast(
        current_hour=current_hour,
        sleep_hours_last_night=sleep_hours,
        chronotype_offset=chronotype_offset,
    )
    
    # Current performance
    st.metric("Current Performance", f"{forecast.current_performance:.0f}%")
    
    # Peak and low times
    col1, col2 = st.columns(2)
    with col1:
        st.success(f"🔝 **Peak Performance**: {forecast.peak_performance_time}")
    with col2:
        st.warning(f"📉 **Low Point**: {forecast.low_performance_time}")
    
    # Hourly forecast chart
    st.markdown("##### 24-Hour Forecast")
    if forecast.hourly_forecast:
        df = pd.DataFrame(forecast.hourly_forecast)
        df = df.rename(columns={"hour_str": "Time", "effectiveness": "Effectiveness %"})
        if "Time" in df.columns and "Effectiveness %" in df.columns:
            st.line_chart(df.set_index("Time")["Effectiveness %"])
    
    # Critical windows
    if forecast.critical_windows:
        st.markdown("##### ⚠️ Critical Windows")
        for cw in forecast.critical_windows:
            st.warning(f"**{cw.get('period', '')}**: {cw.get('warning', '')}")
    
    # Recommendations
    if forecast.recommendations:
        st.markdown("##### Recommendations")
        for rec in forecast.recommendations:
            st.markdown(f"- {rec}")


def _render_operational_performance_tool(
    *,
    age: int,
    sex: str,
    rmssd_ms: float,
    hrv_metrics: Dict[str, Any],
    sleep_hours: float,
    sleep_quality: float,
    hours_awake: float,
    current_hour: int,
    chronotype_offset: float,
    resting_hr: float,
    user_id: str,
) -> None:
    """Render fused operational performance predictor (HRV + SAFTE)."""
    st.markdown("### 🧠 Operational Performance (HRV + SAFTE)")
    st.caption(
        "Fuses SAFTE-style cognitive effectiveness (sleep/circadian) with HRV-derived recovery and autonomic markers. "
        "Use for task scheduling and risk awareness (not a diagnosis)."
    )

    op = predict_operational_performance(
        age=age,
        sex=sex,
        rmssd_ms=rmssd_ms if rmssd_ms > 0 else None,
        hrv_metrics={k: v for k, v in hrv_metrics.items() if isinstance(v, (int, float)) and v is not None},
        sleep_hours_last_night=sleep_hours,
        sleep_quality=sleep_quality,
        hours_awake=hours_awake,
        current_hour=current_hour,
        chronotype_offset=chronotype_offset,
        resting_hr=resting_hr,
    )

    score = op.readiness_score
    if score >= 85:
        st.success(f"## {score:.0f}/100 — {op.readiness_label}")
    elif score >= 70:
        st.info(f"## {score:.0f}/100 — {op.readiness_label}")
    elif score >= 55:
        st.warning(f"## {score:.0f}/100 — {op.readiness_label}")
    else:
        st.error(f"## {score:.0f}/100 — {op.readiness_label}")

    st.markdown("##### Drivers (explainability)")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("SAFTE effectiveness", f"{op.safte_effectiveness:.0f}%")
    with col2:
        st.metric("Recovery score", f"{op.recovery_score:.0f}/100" if op.recovery_score is not None else "N/A")
    with col3:
        st.metric("PNS index", f"{op.parasympathetic_index:.1f}/10" if op.parasympathetic_index is not None else "N/A")
    with col4:
        st.metric("Stress index", f"{op.stress_index:.0f}" if op.stress_index is not None else "N/A")

    st.markdown("##### Task scheduling guidance")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Best 2h window (start)", op.best_2h_window_start or "N/A")
    with col2:
        st.metric("Worst 2h window (start)", op.worst_2h_window_start or "N/A")

    if op.next_12h_alert_windows:
        st.markdown("##### ⚠️ Next 12h alert windows")
        for aw in op.next_12h_alert_windows:
            st.warning(f"**{aw.get('hour', '--:--')}** — {aw.get('reason', '')}")

    if op.triggers:
        show_triggers = st.checkbox(
            "Show triggers (why it scored this way)",
            value=True,
            key=f"op_perf_show_triggers_{user_id}",
        )
        if show_triggers:
            for t in op.triggers:
                st.markdown(f"- {t}")

    if op.recommendations:
        st.markdown("##### Recommendations")
        for rec in op.recommendations:
            st.markdown(f"- {rec}")


@_fragment_if_available
def _render_personalized_health_metrics(user: UserProfile) -> None:
    """Render personalized health metrics based on user profile data.
    
    This section uses the user's specific measurements (weight, neck circumference,
    waist, etc.) to calculate personalized health metrics including:
    - Body fat estimation (US Navy method)
    - Sleep apnea risk (STOP-BANG score)
    - Age-adjusted HRV reference ranges
    - Fitness classification based on VO2max
    - Cardiovascular risk profile
    - Personalized hydration requirements
    """
    st.markdown("#### 🎯 Personalized Health Metrics")
    st.caption(
        "Profile-specific calculations using your measurements. "
        "Update Body Composition data for more accurate estimates."
    )
    
    if not PERSONALIZED_COMPUTATIONS_AVAILABLE:
        st.warning(
            "Personalized computations module not available. "
            "Ensure `personalized_computations.py` is in the app directory."
        )
        return
    
    # Check for required data
    if not all([user.height_cm, user.weight_kg, user.date_of_birth, user.sex]):
        st.info(
            "Complete your profile (height, weight, age, sex) to view personalized health metrics. "
            "Click 'Edit Profile' above."
        )
        return
    
    age = _calculate_age(user.date_of_birth)
    if age is None:
        st.error("Could not calculate age from date of birth.")
        return
    
    sex = user.sex or "other"
    
    # Load body composition data for circumferences
    neck_cm = None
    waist_cm = None
    hip_cm = None
    
    try:
        db = get_database()
        if hasattr(db, "get_body_composition_history"):
            comp_history = db.get_body_composition_history(user.user_id, limit=1)
            if comp_history:
                latest_comp = comp_history[0]
                neck_cm = getattr(latest_comp, 'neck_cm', None)
                waist_cm = getattr(latest_comp, 'waist_cm', None)
                hip_cm = getattr(latest_comp, 'hip_cm', None)
    except Exception:
        pass
    
    # Load medical history for risk factors
    smoker = False
    diabetes = False
    hypertension = False
    family_history_cvd = False
    snoring = None
    tiredness = None
    observed_apnea = None
    
    try:
        if hasattr(db, "get_medical_history"):
            med_history = db.get_medical_history(user.user_id, limit=1)
            if med_history:
                latest_med = med_history[0]
                smoker = latest_med.get("tobacco_use") == "current"
                diabetes = latest_med.get("diabetes_type") is not None
                hypertension = latest_med.get("hypertension", False)
                family_history_cvd = latest_med.get("family_heart_disease", False)
                snoring = latest_med.get("snoring")
                observed_apnea = latest_med.get("sleep_apnea")
    except Exception:
        pass
    
    # Calculate all personalized metrics
    results = calculate_all_personalized_metrics(
        weight_kg=user.weight_kg,
        height_cm=user.height_cm,
        age=age,
        sex=sex,
        neck_cm=neck_cm,
        waist_cm=waist_cm,
        hip_cm=hip_cm,
        vo2max=user.vo2max_ml_kg_min,
        resting_hr=user.resting_hr_bpm,
        systolic_bp=None,  # Could load from medical history
        total_cholesterol=None,
        hdl_cholesterol=None,
        smoker=smoker,
        diabetes=diabetes,
        hypertension_treated=hypertension,
        family_history_cvd=family_history_cvd,
        snoring=snoring,
        tiredness=tiredness,
        observed_apnea=observed_apnea,
        activity_level=user.activity_level or "moderate",
    )
    
    # --- BMI Section ---
    st.markdown("##### 📊 Body Mass Index")
    bmi_data = results.get("bmi", {})
    col1, col2 = st.columns(2)
    with col1:
        st.metric("BMI", f"{bmi_data.get('value', 0):.1f} kg/m²")
    with col2:
        category = bmi_data.get('category', 'Unknown')
        if category == "Normal":
            st.success(f"Category: {category}")
        elif category in ["Overweight", "Underweight"]:
            st.warning(f"Category: {category}")
        else:
            st.error(f"Category: {category}")
    
    # --- Body Fat Section (if circumferences available) ---
    if "body_fat" in results.get("calculations_available", []):
        st.markdown("##### 🏋️ Body Fat (US Navy Method)")
        bf_data = results.get("body_fat", {})
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Body Fat %", f"{bf_data.get('body_fat_pct', 0):.1f}%")
        with col2:
            st.metric("Fat Mass", f"{bf_data.get('fat_mass_kg', 0):.1f} kg")
        with col3:
            st.metric("Lean Mass", f"{bf_data.get('lean_mass_kg', 0):.1f} kg")
        
        bf_category = bf_data.get('category_label', 'Unknown')
        if "Fitness" in bf_category or "Athletes" in bf_category:
            st.success(f"Classification: {bf_category}")
        elif "Average" in bf_category:
            st.info(f"Classification: {bf_category}")
        elif "Obese" in bf_category:
            st.error(f"Classification: {bf_category}")
        else:
            st.warning(f"Classification: {bf_category}")
        
        st.caption(f"Method: {bf_data.get('method', 'US Navy')}")
    else:
        st.info(
            "📏 **Add circumference measurements** (neck, waist, hip) in Body Composition "
            "to calculate body fat using the US Navy method."
        )
    
    # --- Sleep Apnea Risk ---
    st.markdown("##### 😴 Sleep Apnea Risk (STOP-BANG)")
    apnea_data = results.get("sleep_apnea_risk", {})
    score = apnea_data.get("total_score", 0)
    risk_label = apnea_data.get("risk_label", "Unknown")
    risk_level = apnea_data.get("risk_level", "unknown")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("STOP-BANG Score", f"{score}/8")
    with col2:
        if risk_level == "low":
            st.success(risk_label)
        elif risk_level == "moderate":
            st.warning(risk_label)
        else:
            st.error(risk_label)
    
    risk_factors = apnea_data.get("risk_factors", [])
    if risk_factors:
        st.markdown("**Risk factors identified:**")
        for factor in risk_factors:
            st.markdown(f"- {factor}")
    
    if score >= 3:
        show_apnea_recs = st.checkbox(
            "💡 Show sleep apnea recommendations",
            value=False,
            key=f"personalized_sleep_apnea_recs_{user.user_id}",
        )
        if show_apnea_recs:
            for rec in apnea_data.get("recommendations", []):
                st.markdown(f"- {rec}")
    
    # --- Personalized HRV Norms ---
    st.markdown("##### 💓 Personalized HRV Reference Ranges")
    hrv_norms = results.get("hrv_norms", {})
    age_group = hrv_norms.get("age_group", "Unknown")
    st.caption(f"Reference ranges for age group {age_group} ({hrv_norms.get('reference', '')})")
    
    metrics = hrv_norms.get("metrics", {})
    if metrics:
        norm_df_data = []
        for metric_name, values in metrics.items():
            norm_df_data.append({
                "Metric": metric_name.upper().replace("_MS", " (ms)").replace("_PCT", " (%)").replace("_MS2", " (ms²)"),
                "Mean": f"{values['mean']:.1f}",
                "SD": f"{values['sd']:.1f}",
                "Normal Range": f"{values['percentile_5']:.1f} - {values['percentile_95']:.1f}",
            })
        st.dataframe(pd.DataFrame(norm_df_data), use_container_width=True, hide_index=True)
    
    # --- Fitness Classification (if VO2max available) ---
    if "fitness_classification" in results.get("calculations_available", []):
        st.markdown("##### 🏃 Fitness Classification (VO2max)")
        fitness_data = results.get("fitness_classification", {})
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("VO2max", f"{fitness_data.get('vo2max_ml_kg_min', 0):.1f} mL/kg/min")
        with col2:
            category = fitness_data.get("category_label", "Unknown")
            if category in ["Excellent", "Superior"]:
                st.success(f"Category: {category}")
            elif category == "Good":
                st.info(f"Category: {category}")
            elif category == "Fair":
                st.warning(f"Category: {category}")
            else:
                st.error(f"Category: {category}")
        with col3:
            st.metric("Percentile", f"~{fitness_data.get('percentile_estimate', 50)}th")
        st.caption(f"Age group: {fitness_data.get('age_group')} | Sex: {fitness_data.get('sex')}")
    
    # --- Cardiovascular Risk ---
    st.markdown("##### ❤️ Cardiovascular Risk Profile")
    cv_data = results.get("cardiovascular_risk", {})
    cv_risk_level = cv_data.get("risk_level", "unknown")
    
    col1, col2 = st.columns(2)
    with col1:
        if cv_risk_level == "low":
            st.success("Risk Level: LOW")
        elif cv_risk_level == "moderate":
            st.warning("Risk Level: MODERATE")
        elif cv_risk_level == "high":
            st.error("Risk Level: HIGH")
        else:
            st.error("Risk Level: VERY HIGH")
    
    with col2:
        num_risk = len(cv_data.get("risk_factors", []))
        num_protective = len(cv_data.get("protective_factors", []))
        st.metric("Risk / Protective Factors", f"{num_risk} / {num_protective}")
    
    col_r, col_p = st.columns(2)
    with col_r:
        risk_factors = cv_data.get("risk_factors", [])
        if risk_factors:
            st.markdown("**⚠️ Risk Factors:**")
            for factor in risk_factors[:5]:  # Limit display
                st.markdown(f"- {factor}")
    
    with col_p:
        protective = cv_data.get("protective_factors", [])
        if protective:
            st.markdown("**✅ Protective Factors:**")
            for factor in protective[:5]:
                st.markdown(f"- {factor}")
    
    cv_recommendations = cv_data.get("recommendations", [])
    if cv_recommendations:
        show_cv_recs = st.checkbox(
            "💡 Show cardiovascular recommendations",
            value=False,
            key=f"personalized_cv_recs_{user.user_id}",
        )
        if show_cv_recs:
            for rec in cv_recommendations:
                st.markdown(f"- {rec}")
    
    # --- Hydration Requirements ---
    st.markdown("##### 💧 Personalized Hydration")
    hydration_data = results.get("hydration_requirements", {})
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Base Requirement", f"{hydration_data.get('base_ml', 0):.0f} mL")
    with col2:
        st.metric("Daily Target", f"{hydration_data.get('total_ml', 0):.0f} mL")
    with col3:
        st.metric("~Glasses (8oz)", f"{hydration_data.get('glasses_8oz', 0)}")
    
    st.caption(
        f"Based on {user.weight_kg:.1f} kg body weight at "
        f"{user.activity_level or 'moderate'} activity level."
    )
    
    # --- Summary Export ---
    st.markdown("---")
    st.markdown("##### 📥 Export Personalized Metrics")
    
    if st.button("📋 Copy Summary to Clipboard", key=f"copy_personalized_{user.user_id}"):
        summary_text = f"""# Personalized Health Metrics for {user.full_name}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Demographics
- Age: {age} years
- Sex: {sex}
- Height: {user.height_cm:.1f} cm
- Weight: {user.weight_kg:.1f} kg
- BMI: {bmi_data.get('value', 0):.1f} kg/m² ({bmi_data.get('category', 'Unknown')})

## Body Composition
"""
        if "body_fat" in results.get("calculations_available", []):
            bf = results.get("body_fat", {})
            summary_text += f"""- Body Fat: {bf.get('body_fat_pct', 0):.1f}%
- Fat Mass: {bf.get('fat_mass_kg', 0):.1f} kg
- Lean Mass: {bf.get('lean_mass_kg', 0):.1f} kg
- Classification: {bf.get('category_label', 'Unknown')}
"""
        
        summary_text += f"""
## Sleep Apnea Risk
- STOP-BANG Score: {score}/8
- Risk Level: {risk_label}

## Cardiovascular Risk
- Risk Level: {cv_risk_level.upper()}
- Risk Factors: {', '.join(cv_data.get('risk_factors', ['None'])[:3])}

## Hydration
- Daily Target: {hydration_data.get('total_ml', 0):.0f} mL ({hydration_data.get('liters', 0):.1f} L)

---
Reference: Personalized computations based on user profile data.
See docs/Manual.md for scientific references.
"""
        st.code(summary_text, language="markdown")
        st.success("Summary generated! Copy the text above.")


def _render_data_completeness(user: UserProfile) -> None:
    """Show data completeness indicators."""
    st.markdown("### 📊 Profile Completeness")
    
    # Check required fields
    required_fields = {
        "Height": user.height_cm is not None,
        "Weight": user.weight_kg is not None,
        "Date of Birth": user.date_of_birth is not None,
        "Sex": user.sex is not None,
        "Activity Level": user.activity_level is not None,
    }
    
    optional_fields = {
        "Resting HR": user.resting_hr_bpm is not None,
        "VO2max": user.vo2max_ml_kg_min is not None,
        "Max HR": user.max_hr_bpm is not None,
        "Occupation": user.occupation is not None,
    }
    
    # Calculate completeness
    required_complete = sum(required_fields.values())
    required_total = len(required_fields)
    optional_complete = sum(optional_fields.values())
    optional_total = len(optional_fields)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        pct = int(required_complete / required_total * 100)
        color = "green" if pct == 100 else "orange" if pct >= 60 else "red"
        st.metric("Required Fields", f"{required_complete}/{required_total}")
        if pct < 100:
            missing = [k for k, v in required_fields.items() if not v]
            st.caption(f"⚠️ Missing: {', '.join(missing)}")
    
    with col2:
        st.metric("Optional Fields", f"{optional_complete}/{optional_total}")
    
    with col3:
        overall = int((required_complete + optional_complete) / (required_total + optional_total) * 100)
        st.metric("Overall", f"{overall}%")
    
    # Show warning if required fields missing
    if required_complete < required_total:
        st.warning(
            "⚠️ **Required fields missing!** "
            "NASA nutrition calculations require: Height, Weight, Age, Sex, Activity Level. "
            "Click 'Edit Profile' above to complete your profile."
        )


@_fragment_if_available
def _render_nasa_calculator(user: UserProfile) -> None:
    """Render NASA-based nutrition calculator."""
    st.markdown("#### 🧮 Energy & Nutrition Requirements")
    st.caption(
        "Calculations based on NASA JSC67378 standards and Mifflin-St Jeor equation. "
        "[View References](docs/Manual.md#scientific-references)"
    )
    
    # Check if we have required data
    if not all([user.height_cm, user.weight_kg, user.date_of_birth, user.sex]):
        st.info("Complete your profile (height, weight, age, sex) to calculate nutrition requirements.")
        return
    
    # Calculate age
    age = _calculate_age(user.date_of_birth)
    if age is None:
        st.error("Could not calculate age from date of birth.")
        return
    
    # Map sex to BiologicalSex enum
    sex_map = {
        "male": BiologicalSex.MALE,
        "female": BiologicalSex.FEMALE,
        "other": BiologicalSex.FEMALE,  # Conservative estimate
    }
    sex = sex_map.get(user.sex, BiologicalSex.FEMALE)
    
    # Activity level mapping
    activity_map = {
        "sedentary": ActivityLevel.SEDENTARY,
        "light": ActivityLevel.LIGHTLY_ACTIVE,
        "lightly_active": ActivityLevel.LIGHTLY_ACTIVE,
        "moderate": ActivityLevel.MODERATELY_ACTIVE,
        "moderately_active": ActivityLevel.MODERATELY_ACTIVE,
        "active": ActivityLevel.VERY_ACTIVE,
        "very_active": ActivityLevel.VERY_ACTIVE,
        "extra_active": ActivityLevel.EXTRA_ACTIVE,
    }
    activity_level = activity_map.get(
        user.activity_level or "moderate",
        ActivityLevel.MODERATELY_ACTIVE
    )
    
    # VO2max handling (manual + optional Polar AccessLink with history)
    vo2_default = float(user.vo2max_ml_kg_min or 38.0)
    st.markdown("##### 🫁 VO2max Source")
    
    # Check for latest VO2max from history
    latest_vo2_entry = None
    polar_client = None
    if POLAR_MODULE_AVAILABLE and DATABASE_AVAILABLE:
        try:
            polar_client = PolarAccessLinkClient(user.user_id)
            latest_vo2_entry = polar_client.get_latest_vo2max()
            if latest_vo2_entry:
                vo2_default = latest_vo2_entry.vo2max_ml_kg_min
        except Exception:
            pass  # Continue with default
    
    col_vo2_a, col_vo2_b = st.columns([2, 1])
    with col_vo2_a:
        vo2_manual = st.number_input(
            "Manual VO2max (mL·kg⁻¹·min⁻¹)",
            min_value=10.0,
            max_value=90.0,
            value=vo2_default,
            step=0.5,
            help="Enter lab VO2max or estimation from field test.",
        )
    
    polar_cache_key = f"polar_vo2_cache_{user.user_id}"
    polar_cached = st.session_state.get(polar_cache_key)
    use_polar_override = False
    
    with col_vo2_b:
        # Check if Polar is configured (env vars or stored credentials)
        has_polar = polar_accesslink_available()
        has_stored_creds = polar_client.has_credentials() if polar_client else False
        
        if has_polar or has_stored_creds:
            st.caption("✅ Polar AccessLink configured")
            if st.button("🔄 Sync from Polar", key=f"sync_polar_vo2_{user.user_id}"):
                if polar_client:
                    with st.spinner("Syncing from Polar Flow..."):
                        result = polar_client.sync_vo2max()
                    if result.success and result.vo2max:
                        st.session_state[polar_cache_key] = result.vo2max
                        polar_cached = result.vo2max
                        st.success(
                            f"VO2max: **{result.vo2max:.1f}** mL/kg/min "
                            f"({result.fitness_class or 'N/A'})"
                        )
                    elif result.success:
                        st.info(result.message)
                    else:
                        st.warning(f"Sync failed: {result.error or 'Unknown error'}")
                else:
                    # Fallback to simple fetch
                    polar_value = fetch_polar_vo2max()
                    if polar_value:
                        st.session_state[polar_cache_key] = polar_value
                        polar_cached = polar_value
                        st.success(f"Retrieved VO2max {polar_value:.1f} mL/kg/min")
                    else:
                        st.warning("Polar AccessLink did not return a VO2max value.")
            
            use_polar_override = st.checkbox(
                "Use synced value",
                value=bool(polar_cached or latest_vo2_entry),
                help="Use the most recent synced or stored VO2max value.",
                key=f"use_polar_vo2_{user.user_id}",
            )
        else:
            st.caption("ℹ️ Set POLAR_ACCESSLINK_TOKEN & POLAR_ACCESSLINK_USER_ID to enable.")
        
        # Save manual entry button
        if st.button("💾 Save Manual Entry", key=f"save_manual_vo2_{user.user_id}"):
            if POLAR_MODULE_AVAILABLE:
                try:
                    save_manual_vo2max(
                        user_id=user.user_id,
                        vo2max=vo2_manual,
                        notes="Manual entry from NASA Nutrition Calculator",
                    )
                    st.success(f"Saved VO2max {vo2_manual:.1f} mL/kg/min to history")
                except Exception as e:
                    st.error(f"Failed to save: {e}")
    
    # Determine effective VO2max
    effective_vo2 = vo2_manual
    if use_polar_override:
        if polar_cached:
            effective_vo2 = float(polar_cached)
        elif latest_vo2_entry:
            effective_vo2 = latest_vo2_entry.vo2max_ml_kg_min
    
    # Show VO2max history if available
    if polar_client and POLAR_MODULE_AVAILABLE:
        vo2_history = polar_client.get_vo2max_history(limit=10)
        if len(vo2_history) > 1:
            show_vo2_history = st.checkbox(
                "📈 Show VO2max history",
                value=False,
                key=f"nasa_vo2_history_{user.user_id}",
            )
            if show_vo2_history:
                history_data = [
                    {
                        "Date": entry.measurement_date[:10] if entry.measurement_date else "N/A",
                        "VO2max": f"{entry.vo2max_ml_kg_min:.1f}",
                        "Source": entry.source.title(),
                        "Class": entry.polar_fitness_class or "—",
                    }
                    for entry in vo2_history
                ]
                st.dataframe(history_data, use_container_width=True, hide_index=True)
    
    # Exercise settings
    col1, col2 = st.columns(2)
    with col1:
        exercise_type = st.selectbox(
            "Exercise Type",
            options=list(EXERCISE_METS.keys()),
            index=list(EXERCISE_METS.keys()).index("cycling_moderate"),
            format_func=lambda x: x.replace("_", " ").title(),
            key="nasa_exercise_type",
        )
    with col2:
        exercise_duration = st.slider(
            "Exercise Duration (min)",
            min_value=0,
            max_value=240,
            value=120,  # Default 2 hours as requested
            step=15,
            key="nasa_exercise_duration",
        )
    
    # Calculate requirements
    try:
        results = calculate_comprehensive_requirements(
            weight_kg=user.weight_kg,
            height_cm=user.height_cm,
            age_years=age,
            sex=sex,
            activity_level=activity_level,
            exercise_type=exercise_type,
            exercise_duration_min=exercise_duration,
            vo2max_ml_kg_min=effective_vo2,
            lean_mass_kg=None,  # Would come from body composition
        )
        
        # Display results
        st.markdown("##### ⚡ Energy Requirements")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "BMR",
                f"{results['bmr']['adjusted_kcal']:.0f} kcal",
                help=f"Method: {results['bmr']['method']}"
            )
        with col2:
            st.metric(
                "TDEE",
                f"{results['energy']['tdee_kcal']:.0f} kcal",
                help=f"PAL: {results['energy']['pal_multiplier']:.2f}"
            )
        with col3:
            st.metric(
                "Exercise",
                f"+{results['energy']['exercise_kcal']:.0f} kcal",
                help=f"{exercise_duration} min {exercise_type}"
            )
        with col4:
            st.metric(
                "Total Daily",
                f"{results['energy']['total_daily_kcal']:.0f} kcal",
                delta=f"+{results['energy']['exercise_kcal']:.0f}" if exercise_duration > 0 else None,
            )
        
        st.markdown("##### 🫁 VO2max Compensation")
        exercise_details = results["energy"].get("exercise_details", {})
        # Determine source description
        if use_polar_override and polar_cached:
            vo2_source = "Polar AccessLink sync"
        elif use_polar_override and latest_vo2_entry:
            vo2_source = f"History ({latest_vo2_entry.source.title()})"
        else:
            vo2_source = "Manual entry"
        st.metric(
            "VO2max used",
            f"{effective_vo2:.1f} mL/kg/min",
            help=vo2_source,
        )
        if exercise_details:
            st.caption(
                f"Exercise MET base {exercise_details.get('base_met', 0)} → "
                f"{exercise_details.get('adjusted_met', 0)} after VO2 factor "
                f"{exercise_details.get('vo2_factor', 1.0)}."
            )
        
        st.markdown("##### 💧 Hydration (NASA Standard)")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Base Requirement",
                f"{results['hydration']['base_ml']:.0f} mL",
                help="32 mL/kg body weight (NASA-STD-3001)"
            )
        with col2:
            st.metric(
                "With Activity",
                f"{results['hydration']['total_ml']:.0f} mL",
            )
        with col3:
            st.metric(
                "Daily Target",
                f"{results['hydration']['total_liters']:.1f} L",
                help=f"~{results['hydration']['minimum_glasses_8oz']} glasses (8 oz each)"
            )
        
        st.markdown("##### 🥗 Macronutrients (NASA JSC67378)")
        col1, col2, col3, col4 = st.columns(4)
        
        macros = results['macronutrients']
        with col1:
            st.metric(
                "Protein",
                f"{macros['protein_g']:.0f} g",
                help=f"{macros['protein_g_per_kg']:.1f} g/kg ({macros['protein_pct']:.0f}%)"
            )
        with col2:
            st.metric(
                "Carbohydrates",
                f"{macros['carbohydrate_g']:.0f} g",
                help=f"{macros['carbohydrate_pct']:.0f}%"
            )
        with col3:
            st.metric(
                "Fat",
                f"{macros['fat_g']:.0f} g",
                help=f"{macros['fat_pct']:.0f}%"
            )
        with col4:
            st.metric(
                "Fiber",
                f"{macros['fiber_g']:.0f} g",
                help="14g per 1000 kcal (IOM)"
            )
        
        # Reference note
        st.caption(
            "📚 **References**: Mifflin et al. (1990), NASA JSC67378 (2020), "
            "Scott et al. (2020). See Manual for full citations."
        )
        
    except Exception as exc:
        st.error(f"Calculation error: {exc}")


def _render_body_composition_form(user: UserProfile) -> None:
    """Render body composition entry form."""
    st.markdown("#### 📐 Body Composition Measurements")
    st.caption("Enter values from bioimpedance scale, DEXA, or caliper measurements.")

    @st.cache_data(ttl=30, max_entries=128, show_spinner=False)
    def _load_body_comp(uid: str) -> pd.DataFrame:
        db = get_database()
        if hasattr(db, "get_body_composition_dataframe"):
            return db.get_body_composition_dataframe(uid, limit=180)  # type: ignore[attr-defined]
        if hasattr(db, "get_body_composition_history"):
            rows = db.get_body_composition_history(uid, limit=180)  # type: ignore[attr-defined]
            return pd.DataFrame([r.to_dict() for r in rows]) if rows else pd.DataFrame()
        return pd.DataFrame()

    try:
        history_df = _load_body_comp(user.user_id)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Unable to load body composition history: {exc}")
        history_df = pd.DataFrame()

    latest: Dict[str, Any] = {}
    if not history_df.empty:
        tmp = history_df.copy()
        if "measurement_date" in tmp.columns:
            tmp["measurement_date"] = pd.to_datetime(tmp["measurement_date"], errors="coerce")
            tmp = tmp.dropna(subset=["measurement_date"]).sort_values("measurement_date", ascending=False)
        latest = tmp.iloc[0].to_dict() if not tmp.empty else {}

        # Quick snapshot + trends
        st.markdown("##### 📈 Latest & Trends")
        last_date = latest.get("measurement_date")
        if isinstance(last_date, pd.Timestamp) and not pd.isna(last_date):
            st.caption(f"Latest entry: {last_date.date().isoformat()}")
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Body fat", f"{_safe_float(latest.get('body_fat_pct')):.1f}%" if _safe_float(latest.get("body_fat_pct")) is not None else "—")
        col_b.metric("Waist", f"{_safe_float(latest.get('waist_cm')):.1f} cm" if _safe_float(latest.get("waist_cm")) is not None else "—")
        col_c.metric("Hip", f"{_safe_float(latest.get('hip_cm')):.1f} cm" if _safe_float(latest.get("hip_cm")) is not None else "—")
        col_d.metric("Lean mass", f"{_safe_float(latest.get('lean_mass_kg')):.1f} kg" if _safe_float(latest.get("lean_mass_kg")) is not None else "—")

        if "measurement_date" in tmp.columns and len(tmp) > 1:
            trend_cols = [
                c
                for c in ["body_fat_pct", "waist_cm", "hip_cm", "lean_mass_kg", "muscle_mass_kg", "water_pct"]
                if c in tmp.columns and tmp[c].notna().sum() > 1
            ]
            if trend_cols:
                chart_df = tmp.set_index("measurement_date")[trend_cols].sort_index()
                _render_profile_line_chart(
                    chart_df,
                    title="Body composition trends",
                    y_axis_label="value",
                )

        show_history = st.checkbox(
            "📊 Show body composition history",
            value=False,
            key=f"body_comp_show_history_{user.user_id}",
        )
        if show_history:
            display_cols = [
                "measurement_date",
                "body_fat_pct",
                "weight_kg",
                "waist_cm",
                "hip_cm",
                "neck_cm",
                "lean_mass_kg",
                "muscle_mass_kg",
                "water_pct",
                "visceral_fat_level",
                "measurement_method",
            ]
            display_df = tmp[[c for c in display_cols if c in tmp.columns]].copy()
            if "measurement_date" in display_df.columns:
                display_df["measurement_date"] = pd.to_datetime(display_df["measurement_date"], errors="coerce").dt.date
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    def _default_float(val: Any, fallback: float) -> float:
        parsed = _safe_float(val)
        return float(parsed) if parsed is not None else float(fallback)

    def _default_int(val: Any, fallback: int) -> int:
        parsed = _safe_int(val)
        return int(parsed) if parsed is not None else int(fallback)

    method_options = ["bioimpedance", "dexa", "calipers", "tape_measure", "estimated"]
    stored_method = str(latest.get("measurement_method") or "") if latest else ""
    method_index = method_options.index(stored_method) if stored_method in method_options else 0

    form_key = f"body_composition_form_{user.user_id}"
    with st.form(form_key, clear_on_submit=False):
        active_timepoint_id = st.session_state.get(_timepoint_id_key(user.user_id))
        default_date = date.today()
        if latest:
            latest_date = latest.get("measurement_date")
            if isinstance(latest_date, pd.Timestamp) and not pd.isna(latest_date):
                default_date = latest_date.date()

        measurement_date = st.date_input(
            "Measurement date",
            value=default_date,
            key=f"body_comp_date_{user.user_id}",
        )

        st.markdown("##### 📏 Height & Weight")
        col_hw1, col_hw2 = st.columns(2)
        with col_hw1:
            height_cm = st.number_input(
                "Height (cm)",
                min_value=100.0,
                max_value=230.0,
                value=_default_float(latest.get("height_cm") if latest else None, _default_float(user.height_cm, 170.0)),
                step=0.5,
                key=f"body_comp_height_{user.user_id}",
            )
        with col_hw2:
            weight_kg = st.number_input(
                "Weight (kg)",
                min_value=30.0,
                max_value=250.0,
                value=_default_float(latest.get("weight_kg") if latest else None, _default_float(user.weight_kg, 70.0)),
                step=0.1,
                key=f"body_comp_weight_{user.user_id}",
            )

        col1, col2 = st.columns(2)
        with col1:
            body_fat_pct = st.number_input(
                "Body Fat %",
                min_value=1.0,
                max_value=60.0,
                value=_default_float(latest.get("body_fat_pct") if latest else None, 20.0),
                step=0.5,
                help="From bioimpedance scale, DEXA, or calipers",
                key=f"body_comp_bf_{user.user_id}",
            )
            lean_mass_kg = st.number_input(
                "Lean Mass (kg)",
                min_value=20.0,
                max_value=120.0,
                value=_default_float(latest.get("lean_mass_kg") if latest else None, float(weight_kg) * 0.8),
                step=0.5,
                key=f"body_comp_lean_{user.user_id}",
            )
            muscle_mass_kg = st.number_input(
                "Muscle Mass (kg)",
                min_value=10.0,
                max_value=80.0,
                value=_default_float(latest.get("muscle_mass_kg") if latest else None, float(weight_kg) * 0.4),
                step=0.5,
                key=f"body_comp_muscle_{user.user_id}",
            )
        with col2:
            bone_mass_kg = st.number_input(
                "Bone Mass (kg)",
                min_value=1.0,
                max_value=10.0,
                value=_default_float(latest.get("bone_mass_kg") if latest else None, 3.0),
                step=0.1,
                key=f"body_comp_bone_{user.user_id}",
            )
            water_pct = st.number_input(
                "Water %",
                min_value=30.0,
                max_value=80.0,
                value=_default_float(latest.get("water_pct") if latest else None, 55.0),
                step=0.5,
                key=f"body_comp_water_{user.user_id}",
            )
            visceral_fat = st.number_input(
                "Visceral Fat Level",
                min_value=1,
                max_value=59,
                value=_default_int(latest.get("visceral_fat_level") if latest else None, 8),
                step=1,
                help="1-12 healthy, 13-59 excess",
                key=f"body_comp_visceral_{user.user_id}",
            )

        st.markdown("##### 📏 Circumferences (cm)")
        col1, col2, col3 = st.columns(3)
        with col1:
            waist_cm = st.number_input(
                "Waist",
                min_value=40.0,
                max_value=200.0,
                value=_default_float(latest.get("waist_cm") if latest else None, 80.0),
                step=0.5,
                key=f"body_comp_waist_{user.user_id}",
            )
            hip_cm = st.number_input(
                "Hip",
                min_value=50.0,
                max_value=200.0,
                value=_default_float(latest.get("hip_cm") if latest else None, 95.0),
                step=0.5,
                key=f"body_comp_hip_{user.user_id}",
            )
        with col2:
            neck_cm = st.number_input(
                "Neck",
                min_value=20.0,
                max_value=60.0,
                value=_default_float(latest.get("neck_cm") if latest else None, 38.0),
                step=0.5,
                key=f"body_comp_neck_{user.user_id}",
            )
            chest_cm = st.number_input(
                "Chest",
                min_value=50.0,
                max_value=150.0,
                value=_default_float(latest.get("chest_cm") if latest else None, 95.0),
                step=0.5,
                key=f"body_comp_chest_{user.user_id}",
            )
        with col3:
            arm_cm = st.number_input(
                "Arm (relaxed)",
                min_value=15.0,
                max_value=60.0,
                value=_default_float(latest.get("arm_cm") if latest else None, 32.0),
                step=0.5,
                key=f"body_comp_arm_{user.user_id}",
            )
            thigh_cm = st.number_input(
                "Thigh",
                min_value=30.0,
                max_value=90.0,
                value=_default_float(latest.get("thigh_cm") if latest else None, 55.0),
                step=0.5,
                key=f"body_comp_thigh_{user.user_id}",
            )

        calf_cm = st.number_input(
            "Calf",
            min_value=20.0,
            max_value=70.0,
            value=_default_float(latest.get("calf_cm") if latest else None, 38.0),
            step=0.5,
            key=f"body_comp_calf_{user.user_id}",
        )

        measurement_method = st.selectbox(
            "Measurement Method",
            options=method_options,
            index=method_index,
            format_func=lambda x: x.replace("_", " ").title(),
            key=f"body_comp_method_{user.user_id}",
        )
        notes = st.text_area(
            "Notes (optional)",
            value=str(latest.get("notes") or "") if latest else "",
            key=f"body_comp_notes_{user.user_id}",
        )

        submitted = st.form_submit_button(
            "💾 Save Body Composition",
        )

        if submitted:
            try:
                db = get_database()
                measurement = BodyCompositionMeasurement(
                    composition_id=str(uuid.uuid4()),
                    user_id=user.user_id,
                    measurement_date=measurement_date.isoformat(),
                    timepoint_id=active_timepoint_id,
                    height_cm=float(height_cm),
                    weight_kg=float(weight_kg),
                    body_fat_pct=float(body_fat_pct),
                    lean_mass_kg=float(lean_mass_kg),
                    muscle_mass_kg=float(muscle_mass_kg),
                    bone_mass_kg=float(bone_mass_kg),
                    water_pct=float(water_pct),
                    visceral_fat_level=int(visceral_fat),
                    waist_cm=float(waist_cm),
                    hip_cm=float(hip_cm),
                    neck_cm=float(neck_cm),
                    chest_cm=float(chest_cm),
                    arm_cm=float(arm_cm),
                    thigh_cm=float(thigh_cm),
                    calf_cm=float(calf_cm),
                    measurement_method=str(measurement_method),
                    notes=notes.strip() or None,
                )
                if hasattr(db, "save_body_composition"):
                    db.save_body_composition(measurement)  # type: ignore[attr-defined]
                else:
                    raise AttributeError("Database does not support body composition storage yet.")
            except Exception as exc:  # noqa: BLE001
                if log_exception is not None:
                    log_exception(_LOGGER, "Failed to save body composition", exc)
                st.error(f"Failed to save body composition: {exc}")
            else:
                try:
                    _load_body_comp.clear()  # type: ignore[attr-defined]
                except Exception:
                    pass
                st.success("✅ Body composition saved to your profile.")
                st.rerun()


def _render_medical_history_summary(user: UserProfile) -> None:
    """Render medical history summary pulling from both profile and medical_history table."""
    st.markdown("#### 📋 Medical History Summary")
    
    # Load latest medical record from database for richer context
    @st.cache_data(ttl=30, max_entries=64, show_spinner=False)
    def _load_latest_record(uid: str) -> Dict[str, Any]:
        try:
            db = get_database()
            rows = db.get_medical_history(uid, limit=1)
            return rows[0] if rows else {}
        except Exception:
            return {}
    
    latest_record = _load_latest_record(user.user_id)
    
    # Show current conditions from user profile
    if user.medical_conditions:
        st.write("**Current Conditions:**")
        for condition in user.medical_conditions:
            st.write(f"• {condition}")
    
    if user.medications:
        st.write("**Current Medications:**")
        for med in user.medications:
            st.write(f"• {med}")
    
    # Show most recent exploration medical record summary
    if latest_record:
        st.markdown("---")
        st.markdown("**Latest Exploration Medical Record:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            mission = latest_record.get("mission_profile", "—")
            day = latest_record.get("mission_day", "—")
            st.metric("Mission", f"{mission} D{day}")
        with col2:
            eva_status = latest_record.get("eva_status", "—")
            st.metric("EVA Status", eva_status)
        with col3:
            rad = latest_record.get("radiation_dose_msv", 0.0)
            st.metric("Radiation (mSv)", f"{rad:.1f}")
        
        # Chronic/acute flags
        chronic_list = latest_record.get("chronic_conditions", [])
        acute_list = latest_record.get("acute_symptoms", [])
        if chronic_list:
            st.caption(f"🩺 Chronic: {', '.join(chronic_list)}")
        if acute_list:
            st.caption(f"⚠️ Acute (24h): {', '.join(acute_list)}")
        st.caption(f"_Updated: {latest_record.get('updated_at', '—')}_")
    else:
        if not user.medical_conditions and not user.medications:
            st.info("No medical history recorded. Edit your profile or use the Exploration Medical Record form.")


@st.cache_data(ttl=60, max_entries=64, show_spinner=False)
def _load_medical_history_dataframe(user_id: str) -> pd.DataFrame:
    """Load exploration medical history entries as a typed DataFrame."""
    if not user_id:
        return pd.DataFrame()
    try:
        db = get_database()
        records = db.get_medical_history(user_id, limit=180)
    except Exception as exc:
        _LOGGER.warning("Unable to load exploration medical history for %s: %s", user_id, exc)
        return pd.DataFrame()
    if not records:
        return pd.DataFrame()
    history_df = pd.DataFrame(records)
    numeric_columns = [
        "mission_day",
        "radiation_dose_msv",
        "eva_hours_72h",
        "days_since_last_eva",
        "confinement_stress",
        "workload_rating",
        "sleep_hours",
        "sleep_quality",
        "exercise_minutes",
        "hydration_liters",
        "caloric_intake",
        "comm_delay_min",
    ]
    for column in numeric_columns:
        if column in history_df.columns:
            history_df[column] = pd.to_numeric(history_df[column], errors="coerce")
    if "updated_at" in history_df.columns:
        history_df["updated_at"] = pd.to_datetime(history_df["updated_at"], errors="coerce")
        history_df.sort_values("updated_at", inplace=True)
    elif "mission_day" in history_df.columns:
        history_df.sort_values("mission_day", inplace=True)
    history_df.reset_index(drop=True, inplace=True)
    return history_df


def _compute_radiation_rate(history_df: pd.DataFrame) -> Optional[float]:
    """Compute average cumulative radiation increase per mission day."""
    if history_df.empty or not {"mission_day", "radiation_dose_msv"}.issubset(history_df.columns):
        return None
    valid = history_df.dropna(subset=["mission_day", "radiation_dose_msv"]).sort_values("mission_day")
    if len(valid) < 2:
        return None
    start_day = float(valid["mission_day"].iloc[0])
    end_day = float(valid["mission_day"].iloc[-1])
    if start_day == end_day:
        return None
    start_dose = float(valid["radiation_dose_msv"].iloc[0])
    end_dose = float(valid["radiation_dose_msv"].iloc[-1])
    return (end_dose - start_dose) / (end_day - start_day)


def _s_scale_from_pfu(max_pfu: Optional[float]) -> tuple[str, int]:
    """Return NOAA SWPC radiation storm scale label (S0–S5) from >10 MeV proton flux."""
    if max_pfu is None or not np.isfinite(float(max_pfu)):
        return "S0", 0
    pfu = float(max_pfu)
    if pfu >= 100_000:
        return "S5", 5
    if pfu >= 10_000:
        return "S4", 4
    if pfu >= 1_000:
        return "S3", 3
    if pfu >= 100:
        return "S2", 2
    if pfu >= 10:
        return "S1", 1
    return "S0", 0


def _g_scale_from_kp(max_kp: Optional[float]) -> tuple[str, int]:
    """Return NOAA geomagnetic storm scale label (G0–G5) from Kp."""
    if max_kp is None or not np.isfinite(float(max_kp)):
        return "G0", 0
    kp = float(max_kp)
    if kp >= 9:
        return "G5", 5
    if kp >= 8:
        return "G4", 4
    if kp >= 7:
        return "G3", 3
    if kp >= 6:
        return "G2", 2
    if kp >= 5:
        return "G1", 1
    return "G0", 0


def _space_weather_alert_category(g_level: int, s_level: int) -> str:
    """Map G/S storm levels into the profile alert taxonomy."""
    if max(g_level, s_level) >= 3:
        return "Storm In Progress"
    if max(g_level, s_level) >= 1:
        return "Warning"
    return "None"


def _estimate_baseline_radiation_msv_per_day(
    *, mission_profile: str, habitat: str
) -> tuple[float, str]:
    """Return a baseline effective dose rate estimate (mSv/day) for the selected environment.

    Notes:
        These are coarse, planning-level anchors; actual dose depends on shielding,
        solar cycle, trajectory, and storm events. The UI surfaces the assumptions.
    """
    mission_profile = (mission_profile or "").strip()
    habitat = (habitat or "").strip()

    # Earth analog baseline (~2.4 mSv/year background ≈ 0.0066 mSv/day).
    if mission_profile.startswith("ANALOG") or habitat in {"Mars Dune Alpha", "HERA", "NEEMO"}:
        return 2.4 / 365.0, "Earth background (~2.4 mSv/year)"

    # ISS / LEO.
    if mission_profile == "LEO-ISS" or habitat == "ISS":
        return 0.73, "ISS (order-of-magnitude, LEO effective dose)"

    # Gateway / cislunar.
    if mission_profile == "GATEWAY-30" or habitat == "Gateway":
        return 1.3, "Cislunar free-space design target (~1.3 mSv/day)"

    # Lunar surface.
    if mission_profile in {"LUNAR-SLS", "LUNAR-SURFACE-90"} or habitat in {"Lunar Hab", "Starship HLS"}:
        return 1.369, "Lunar surface (Chang'E-4 LND)"

    # Mars cruise / surface.
    if mission_profile == "MARS-TRANSIT-180":
        return 1.84, "Mars cruise (MSL/RAD cruise)"
    if mission_profile == "MARS-SURFACE-500":
        return 0.64, "Mars surface (MSL/RAD surface)"

    # Fallback.
    return 2.4 / 365.0, "Earth background (~2.4 mSv/year)"


@st.cache_data(ttl=1800, max_entries=16, show_spinner=False)
def _load_noaa_profile_bundles() -> tuple[Dict[str, Any], Dict[str, str]]:
    """Load a small subset of NOAA datasets used for profile alert estimation."""
    if not NOAA_SPACE_AVAILABLE:
        return {}, {"__global__": "NOAA space module unavailable."}
    bundles, errors = load_noaa_space_data(
        keys=("planetary_k_index_1m", "goes_integral_protons"),
        use_cache=True,
    )
    packed: Dict[str, Any] = {}
    for key, bundle in bundles.items():
        packed[key] = {
            "frame": bundle.frame,
            "time_column": bundle.time_column,
            "value_columns": bundle.value_columns,
            "split_labels": dict(bundle.split_labels),
        }
    return packed, errors


def _space_weather_summary_for_date(target_date: date) -> Dict[str, Any]:
    """Compute Kp + >10 MeV proton max and alert labels for a given UTC date."""
    packed, errors = _load_noaa_profile_bundles()

    out: Dict[str, Any] = {
        "kp_max": None,
        "kp_g_scale": "G0",
        "kp_g_level": 0,
        "proton_max_pfu": None,
        "proton_s_scale": "S0",
        "proton_s_level": 0,
        "alert_category": "None",
        "errors": errors,
    }

    # Kp max
    kp_payload = packed.get("planetary_k_index_1m")
    if isinstance(kp_payload, dict):
        kp_df = kp_payload.get("frame")
        time_col = kp_payload.get("time_column")
        if isinstance(kp_df, pd.DataFrame) and not kp_df.empty and isinstance(time_col, str) and time_col in kp_df.columns:
            series = pd.to_datetime(kp_df[time_col], errors="coerce", utc=True)
            day_mask = series.dt.date == target_date
            if "kp_index" in kp_df.columns:
                vals = pd.to_numeric(kp_df.loc[day_mask, "kp_index"], errors="coerce").dropna()
                if not vals.empty:
                    out["kp_max"] = float(vals.max())
                    g_scale, g_level = _g_scale_from_kp(out["kp_max"])
                    out["kp_g_scale"] = g_scale
                    out["kp_g_level"] = g_level

    # Proton flux max (>=10 MeV)
    proton_payload = packed.get("goes_integral_protons")
    if isinstance(proton_payload, dict):
        proton_df = proton_payload.get("frame")
        time_col = proton_payload.get("time_column")
        value_cols = proton_payload.get("value_columns") or ()
        split_labels = proton_payload.get("split_labels") or {}
        if (
            isinstance(proton_df, pd.DataFrame)
            and not proton_df.empty
            and isinstance(time_col, str)
            and time_col in proton_df.columns
        ):
            # Identify the >=10 MeV column.
            proton_col: Optional[str] = None
            for col in value_cols:
                label = str(split_labels.get(col, "")).lower()
                if "10" in label and "mev" in label:
                    proton_col = str(col)
                    break
            if proton_col is None:
                for col in value_cols:
                    col_lower = str(col).lower()
                    if "ge_10" in col_lower and "mev" in col_lower:
                        proton_col = str(col)
                        break

            if proton_col and proton_col in proton_df.columns:
                series = pd.to_datetime(proton_df[time_col], errors="coerce", utc=True)
                day_mask = series.dt.date == target_date
                vals = pd.to_numeric(proton_df.loc[day_mask, proton_col], errors="coerce").dropna()
                if not vals.empty:
                    out["proton_max_pfu"] = float(vals.max())
                    s_scale, s_level = _s_scale_from_pfu(out["proton_max_pfu"])
                    out["proton_s_scale"] = s_scale
                    out["proton_s_level"] = s_level

    out["alert_category"] = _space_weather_alert_category(
        int(out["kp_g_level"]), int(out["proton_s_level"])
    )
    return out


@st.cache_data(ttl=30, max_entries=128, show_spinner=False)
def _load_hrv_daily_objective(uid: str) -> pd.DataFrame:
    """Load daily-median objective HRV indices (stress/PNS) for a user."""
    if not uid:
        return pd.DataFrame()
    db = get_database()
    df = db.get_hrv_dataframe(
        uid,
        limit=500,
        include_rr=False,
        columns=(
            "measurement_date",
            "stress_index",
            "parasympathetic_index",
            "hrv_score",
            "mean_hr_bpm",
            "rmssd_ms",
            "sdnn_ms",
        ),
    )
    if df.empty or "measurement_date" not in df.columns:
        return pd.DataFrame()
    tmp = df.copy()
    tmp["measurement_date"] = pd.to_datetime(tmp["measurement_date"], errors="coerce")
    tmp = tmp.dropna(subset=["measurement_date"])
    if tmp.empty:
        return pd.DataFrame()
    tmp["day"] = tmp["measurement_date"].dt.normalize()
    cols = [c for c in tmp.columns if c not in {"measurement_date"}]
    numeric_cols = [c for c in cols if c in tmp.columns and pd.api.types.is_numeric_dtype(tmp[c])]
    if not numeric_cols:
        return pd.DataFrame()
    daily = tmp.groupby("day", as_index=True)[numeric_cols].median().sort_index()
    return daily


@st.cache_data(ttl=60, max_entries=128, show_spinner=False)
def _load_garmin_daily_objective(uid: str) -> pd.DataFrame:
    """Load Garmin daily metrics (sleep/stress/body battery) for a user."""
    if not uid:
        return pd.DataFrame()
    db = get_database()
    if not hasattr(db, "get_garmin_daily_dataframe"):
        return pd.DataFrame()
    df = db.get_garmin_daily_dataframe(uid, limit=365)  # type: ignore[attr-defined]
    if df.empty or "metric_date" not in df.columns:
        return pd.DataFrame()
    tmp = df.copy()
    tmp["metric_date"] = pd.to_datetime(tmp["metric_date"], errors="coerce")
    tmp = tmp.dropna(subset=["metric_date"]).sort_values("metric_date")
    if tmp.empty:
        return pd.DataFrame()
    tmp["day"] = tmp["metric_date"].dt.normalize()
    # Prefer latest entry per day (Garmin table is unique per date, but keep robust).
    tmp = tmp.drop_duplicates(subset=["day"], keep="last").set_index("day")
    return tmp


def _build_frequency_df(values: Sequence[Any], top_n: int = 5) -> pd.DataFrame:
    """Aggregate frequency counts for list-like history fields."""
    counts: Counter[str] = Counter()
    for entry in values:
        if entry is None or (isinstance(entry, float) and np.isnan(entry)):
            continue
        if isinstance(entry, (list, tuple, set)):
            for item in entry:
                text = str(item).strip()
                if text:
                    counts[text] += 1
        elif isinstance(entry, str):
            text = entry.strip()
            if text:
                counts[text] += 1
        else:
            text = str(entry).strip()
            if text:
                counts[text] += 1
    if not counts:
        return pd.DataFrame(columns=["Label", "Count"])
    most_common = counts.most_common(max(1, top_n))
    return pd.DataFrame(most_common, columns=["Label", "Count"])


def _render_exploration_medical_analytics(user: UserProfile) -> None:
    """Render exploration medical analytics dashboard with aggregate indicators."""
    st.markdown("#### 📊 Exploration Medical Analytics Dashboard")
    history_df = _load_medical_history_dataframe(user.user_id)
    if history_df.empty:
        st.info("Log at least one exploration medical record to unlock analytics.")
        return
    latest_entry = history_df.iloc[-1]

    # Radiation exposure
    st.markdown("##### ☢️ Radiation Exposure")
    rad_limit = 600.0  # NASA STD-3001B (career effective dose design limit)
    rad_limit_legacy = 1000.0  # Legacy planning guideline (kept for comparison)

    rad_sources: Dict[str, str] = {}
    if "radiation_dose_msv" in history_df.columns and not history_df["radiation_dose_msv"].dropna().empty:
        rad_sources["Recorded cumulative dose"] = "radiation_dose_msv"
    if (
        "radiation_estimated_cumulative_msv" in history_df.columns
        and not history_df["radiation_estimated_cumulative_msv"].dropna().empty
    ):
        rad_sources["Estimated cumulative dose"] = "radiation_estimated_cumulative_msv"

    if not rad_sources:
        st.warning("No radiation dose entries recorded yet (or no modelled dose available).")
    else:
        selected_label = st.radio("Dose source", list(rad_sources.keys()), horizontal=True, key="rad_source_selector")
        rad_col = rad_sources[selected_label]
        rad_series = pd.to_numeric(history_df[rad_col], errors="coerce").dropna()

        if rad_series.empty:
            st.warning("No radiation dose entries recorded yet (or no modelled dose available).")
        else:
            max_rad = float(rad_series.max())
            median_rad = float(rad_series.median())
            rate_df = history_df.copy()
            rate_df["radiation_dose_msv"] = pd.to_numeric(rate_df[rad_col], errors="coerce")
            rad_rate = _compute_radiation_rate(rate_df)
            remaining = max(rad_limit - max_rad, 0.0)
            col_r1, col_r2, col_r3 = st.columns(3)
            col_r1.metric(
                "Max cumulative dose",
                f"{max_rad:.1f} mSv",
                delta=f"{remaining:.1f} mSv below NASA limit",
            )
            col_r2.metric(
                "Median logged dose",
                f"{median_rad:.1f} mSv",
                delta=None,
            )
            col_r3.metric(
                "Daily accumulation",
                f"{rad_rate:.2f} mSv/day" if rad_rate is not None else "—",
                delta=None if rad_rate is None else "Avg change per mission day",
            )
            progress_value = min(max_rad / rad_limit, 1.0)
            st.progress(progress_value)
            legacy_pct = min(max_rad / rad_limit_legacy, 1.0) * 100.0
            st.caption(
                f"{progress_value * 100:.1f}% of NASA 600 mSv career effective dose design limit "
                f"(legacy 1000 mSv: {legacy_pct:.1f}%)."
            )
            if {"mission_day"}.issubset(history_df.columns):
                chart_df = history_df.dropna(subset=["mission_day", rad_col] if rad_col else ["mission_day"]).copy()
                if not chart_df.empty:
                    chart_df = chart_df.sort_values("mission_day").set_index("mission_day")
                    chart_df["radiation_dose_msv"] = pd.to_numeric(chart_df[rad_col], errors="coerce")
                    chart_df.rename(columns={"radiation_dose_msv": "Radiation (mSv)"}, inplace=True)
                    _render_profile_line_chart(
                        chart_df[["Radiation (mSv)"]],
                        title="Radiation Dose vs. Mission Day",
                        y_axis_label="mSv",
                    )

    # EVA workload
    st.markdown("##### 🧑‍🚀 EVA Workload")
    eva_series = history_df["eva_hours_72h"].dropna() if "eva_hours_72h" in history_df.columns else pd.Series(dtype=float)
    avg_eva = float(eva_series.mean()) if not eva_series.empty else None
    peak_eva = float(eva_series.max()) if not eva_series.empty else None
    days_since_last = latest_entry.get("days_since_last_eva")
    days_since_last_display = (
        f"{int(days_since_last)} d" if days_since_last is not None and not np.isnan(days_since_last) else "—"
    )
    col_e1, col_e2, col_e3 = st.columns(3)
    col_e1.metric("Avg EVA hrs (72h)", f"{avg_eva:.1f} h" if avg_eva is not None else "—")
    col_e2.metric("Peak EVA load", f"{peak_eva:.1f} h" if peak_eva is not None else "—", delta="Rolling 72h window")
    col_e3.metric("Days since last EVA", days_since_last_display)
    if "eva_status" in history_df.columns:
        def _normalize_eva_status(value: Any) -> str:
            text = str(value).strip().lower()
            if text in {"1", "go", "green", "clear", "cleared", "approved", "ok", "yes"}:
                return "GO"
            if text in {"0", "no-go", "nogo", "red", "hold", "fail", "denied", "no"}:
                return "NO-GO"
            return "MONITOR"

        eva_norm = history_df["eva_status"].dropna().map(_normalize_eva_status)
        eva_status_counts = eva_norm.value_counts().reindex(["GO", "MONITOR", "NO-GO"]).fillna(0).astype(int)
        if eva_status_counts.sum() > 0:
            _render_profile_bar_chart(
                eva_status_counts.rename("EVA Clearance States"),
                title="EVA Clearance States (standardized GO / MONITOR / NO-GO)",
                y_axis_label="Count",
            )
            st.caption(
                "EVA clearance standardized: GO (cleared), MONITOR (requires mitigation/flight surgeon review), "
                "NO-GO (not cleared)."
            )

    # Stress and behavioral indicators
    st.markdown("##### 🧠 Stress & Behavioral Indicators")
    # Objective physiology (preferred): HRV + Garmin
    hrv_daily = _load_hrv_daily_objective(user.user_id)
    garmin_daily = _load_garmin_daily_objective(user.user_id)
    hrv_stress_series = (
        pd.to_numeric(hrv_daily["stress_index"], errors="coerce").dropna()
        if not hrv_daily.empty and "stress_index" in hrv_daily.columns
        else pd.Series(dtype=float)
    )
    hrv_pns_series = (
        pd.to_numeric(hrv_daily["parasympathetic_index"], errors="coerce").dropna()
        if not hrv_daily.empty and "parasympathetic_index" in hrv_daily.columns
        else pd.Series(dtype=float)
    )
    garmin_sleep_series = (
        pd.to_numeric(garmin_daily["sleep_duration_hours"], errors="coerce").dropna()
        if not garmin_daily.empty and "sleep_duration_hours" in garmin_daily.columns
        else pd.Series(dtype=float)
    )

    def _recent_mean(series: pd.Series, n: int) -> Optional[float]:
        values = series.dropna().tail(max(1, int(n)))
        return float(values.mean()) if not values.empty else None

    def _baseline_mean(series: pd.Series) -> Optional[float]:
        values = series.dropna()
        return float(values.mean()) if not values.empty else None

    recent_hrv_stress = _recent_mean(hrv_stress_series, 5)
    recent_pns = _recent_mean(hrv_pns_series, 5)
    recent_sleep_obj = _recent_mean(garmin_sleep_series, 5)
    hrv_stress_delta = (
        None
        if recent_hrv_stress is None or _baseline_mean(hrv_stress_series) is None
        else recent_hrv_stress - float(_baseline_mean(hrv_stress_series))
    )

    col_s1, col_s2, col_s3 = st.columns(3)
    col_s1.metric(
        "HRV stress index (last 5)",
        f"{recent_hrv_stress:.0f}" if recent_hrv_stress is not None else "—",
        delta=f"{hrv_stress_delta:+.0f} vs avg" if hrv_stress_delta is not None else None,
    )
    col_s2.metric(
        "PNS index (last 5)",
        f"{recent_pns:.2f}" if recent_pns is not None else "—",
        delta=None,
    )
    col_s3.metric(
        "Sleep hours (Garmin, last 5)",
        f"{recent_sleep_obj:.1f} h" if recent_sleep_obj is not None else "—",
        delta=None,
    )

    if not hrv_daily.empty:
        plot_cols = [c for c in ["stress_index", "parasympathetic_index"] if c in hrv_daily.columns]
        if plot_cols:
            _render_profile_line_chart(
                hrv_daily[plot_cols],
                title="Objective HRV stress & PNS (daily medians)",
                y_axis_label="value",
            )
    if not garmin_daily.empty and "sleep_duration_hours" in garmin_daily.columns:
        _render_profile_line_chart(
            garmin_daily[["sleep_duration_hours"]].rename(columns={"sleep_duration_hours": "Sleep (h)"}),
            title="Objective sleep duration (Garmin)",
            y_axis_label="hours",
        )

    # Subjective logs (optional): stored exploration medical record fields.
    show_subjective = st.checkbox(
        "📝 Show logged (subjective) indicators",
        value=False,
        key=f"exploration_med_subjective_{user.user_id}",
    )
    if show_subjective:
        stress_series = history_df["confinement_stress"].dropna() if "confinement_stress" in history_df.columns else pd.Series(dtype=float)
        workload_series = history_df["workload_rating"].dropna() if "workload_rating" in history_df.columns else pd.Series(dtype=float)
        sleep_series = history_df["sleep_hours"].dropna() if "sleep_hours" in history_df.columns else pd.Series(dtype=float)
        recent_window = history_df.tail(min(len(history_df), 5))
        recent_stress = (
            float(recent_window["confinement_stress"].dropna().mean())
            if "confinement_stress" in recent_window.columns and not recent_window["confinement_stress"].dropna().empty
            else None
        )
        baseline_stress = float(stress_series.mean()) if not stress_series.empty else None
        stress_delta = (
            None if baseline_stress is None or recent_stress is None else recent_stress - baseline_stress
        )
        recent_workload = (
            float(recent_window["workload_rating"].dropna().mean())
            if "workload_rating" in recent_window.columns and not recent_window["workload_rating"].dropna().empty
            else None
        )
        workload_delta = (
            None
            if workload_series.empty or recent_workload is None
            else recent_workload - float(workload_series.mean())
        )
        recent_sleep = (
            float(recent_window["sleep_hours"].dropna().mean())
            if "sleep_hours" in recent_window.columns and not recent_window["sleep_hours"].dropna().empty
            else None
        )
        col_l1, col_l2, col_l3 = st.columns(3)
        col_l1.metric(
            "Confinement stress (last 5)",
            f"{recent_stress:.1f}/10" if recent_stress is not None else "—",
            delta=f"{stress_delta:+.1f} vs avg" if stress_delta is not None else None,
        )
        col_l2.metric(
            "Workload rating (last 5)",
            f"{recent_workload:.1f}/10" if recent_workload is not None else "—",
            delta=f"{workload_delta:+.1f} vs avg" if workload_delta is not None else None,
        )
        col_l3.metric(
            "Sleep hours (last 5)",
            f"{recent_sleep:.1f} h" if recent_sleep is not None else "—",
            delta=None,
        )
    symptom_df = _build_frequency_df(
        history_df["acute_symptoms"].tolist() if "acute_symptoms" in history_df.columns else [],
        top_n=5,
    )
    behavior_df = _build_frequency_df(
        history_df["behavioral_flags"].tolist() if "behavioral_flags" in history_df.columns else [],
        top_n=5,
    )
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if symptom_df.empty:
            st.caption("No acute symptom trends logged yet.")
        else:
            st.caption("Top acute symptoms (all-time)")
            st.dataframe(symptom_df, use_container_width=True, hide_index=True)
    with col_b2:
        if behavior_df.empty:
            st.caption("No behavioral flags logged yet.")
        else:
            st.caption("Behavioral health flags (frequency)")
            st.dataframe(behavior_df, use_container_width=True, hide_index=True)


@_fragment_if_available
def _render_medical_record_form(user: UserProfile) -> None:
    """Render NASA-style exploration medical record entry form.
    
    Structured per Exploration Medical Capability (ExMC) and Earth-Independent
    Medical Operations (EIMO) framework for autonomous deep-space missions.
    Reference: https://ntrs.nasa.gov/citations/20230015831 (ExMC AsMA 2024).
    """
    st.caption(
        "Structured per NASA Exploration Medical Capability (ExMC) and the "
        "Earth-Independent Medical Operations (EIMO) paradigm for deep-space "
        "autonomy. Reference: Lehnhardt et al., NASA Technical Reports Server, "
        "2023 (DOI: 10.1109/OJEMB.2023.3255513)."
    )
    
    # -------------------------------------------------------------------------
    # Helper: Safe index lookup for selectbox (resilient to schema changes)
    # -------------------------------------------------------------------------
    def _safe_selectbox_index(stored_value: Any, options: list, default_index: int = 0) -> int:
        """Return index of stored_value in options, or default_index if not found."""
        if stored_value in options:
            return options.index(stored_value)
        if stored_value is not None:
            _LOGGER.debug(
                "Selectbox schema migration: stored value %r not in options, using default index %d",
                stored_value,
                default_index,
            )
        return default_index
    
    try:
        db = get_database()
        history = db.get_medical_history(user.user_id, limit=25)
        _LOGGER.debug("Loaded %d medical history entries for user %s", len(history), user.user_id)
    except Exception as exc:
        _LOGGER.warning("Unable to load medical history for user %s: %s", user.user_id, exc)
        st.error(f"Unable to load medical history: {exc}")
        history = []
    latest = history[0] if history else {}
    
    # Mission profiles aligned with NASA EIMO planning horizons
    mission_options = {
        "LEO-ISS": "ISS / Low-Earth Orbit (continuous ground support)",
        "LUNAR-SLS": "Artemis lunar sortie (6–30 days, limited EIMO)",
        "GATEWAY-30": "Gateway cislunar (30-day increments)",
        "LUNAR-SURFACE-90": "Lunar surface sustained (up to 90 days)",
        "MARS-TRANSIT-180": "Mars transit (180+ days, high EIMO)",
        "MARS-SURFACE-500": "Mars surface (500+ days, full autonomy)",
        "ANALOG-CHAPEA": "CHAPEA / Mars Dune Alpha analog",
        "ANALOG-HERA": "HERA campaign (45-day isolation)",
        "CUSTOM": "Custom exploration profile",
    }
    habitats = ["ISS", "Gateway", "Starship HLS", "Mars Dune Alpha", "HERA", "NEEMO", "Lunar Hab", "Custom"]
    crew_roles = [
        "Flight Surgeon",
        "Crew Medical Officer (CMO)",
        "Commander",
        "Pilot",
        "Mission Specialist",
        "Payload Specialist",
        "Research Scientist",
    ]
    eva_status_options = ["Cleared", "Cleared with Restriction", "No EVA", "Post-EVA Recovery"]
    space_weather_alerts = ["None", "Watch", "Warning", "Storm In Progress", "Post-Event Monitoring"]
    # Chronic condition categories per HRP/ExMC risk taxonomy
    chronic_condition_options = [
        "Cardiovascular (SANS, arrhythmia)",
        "Respiratory (atelectasis, hypoxia history)",
        "Metabolic (glucose, bone loss)",
        "Neurological (vestibular, ICP)",
        "Psychological (anxiety, depression, adjustment)",
        "Musculoskeletal (muscle atrophy, back pain)",
        "Renal/Urologic (nephrolithiasis)",
        "Dermatologic (rash, infection)",
        "Ophthalmologic (SANS-related)",
        "Immunologic (allergy, infection susceptibility)",
    ]
    # Acute symptoms expanded per ExMC clinical decision support categories
    acute_symptom_options = [
        "Headache",
        "Dizziness / Vertigo",
        "Visual change (blur, scotoma)",
        "Nausea / Vomiting",
        "Abdominal pain",
        "Chest pain / Palpitations",
        "Dyspnea",
        "Musculoskeletal pain (specify)",
        "Skin lesion / Wound",
        "Sleep disruption (insomnia / hypersomnia)",
        "Cognitive change (attention, memory)",
        "Mood change (irritability, apathy)",
        "Fever / Chills",
        "Urinary symptoms",
    ]
    behavioral_flags = [
        "Confinement stress",
        "Team friction / Interpersonal conflict",
        "Mood dysregulation",
        "Cognitive slowing / Attention deficit",
        "Motivation dip / Amotivation",
        "Sleep-wake cycle disruption",
        "Isolation distress",
        "Homesickness / Nostalgia",
    ]
    # EIMO autonomy level (per Levin et al. 2023)
    autonomy_levels = [
        "Ground-Supported (real-time telemedicine)",
        "Delayed Support (2–20 min latency)",
        "Limited Autonomy (hours to days delay)",
        "Full EIMO (crew autonomous)",
    ]
    
    form_key = f"exploration_medical_record_form_{user.user_id}"
    with st.form(form_key, clear_on_submit=False):
        # ─────────────────────────────────────────────────────────────────────
        # Section 1: Mission Context (EIMO Phase & Habitat)
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("##### 🚀 Mission Context")
        col_a, col_b, col_c = st.columns(3)
        mission_keys = list(mission_options.keys())
        with col_a:
            mission_profile = st.selectbox(
                "Mission profile",
                options=mission_keys,
                format_func=lambda key: mission_options.get(key, key),
                index=_safe_selectbox_index(latest.get("mission_profile"), mission_keys, 0),
            )
            # Used to align Garmin/HRV and space-weather context for the log entry.
            default_record_date = date.today()
            stored_record_date = latest.get("record_date") if isinstance(latest, dict) else None
            if stored_record_date:
                parsed = pd.to_datetime(stored_record_date, errors="coerce", utc=True)
                if isinstance(parsed, pd.Timestamp) and not pd.isna(parsed):
                    default_record_date = parsed.date()
            elif latest.get("updated_at"):
                parsed = pd.to_datetime(latest.get("updated_at"), errors="coerce", utc=True)
                if isinstance(parsed, pd.Timestamp) and not pd.isna(parsed):
                    default_record_date = parsed.date()
            record_date = st.date_input(
                "Log date (UTC)",
                value=default_record_date,
                help="Used to align Garmin sleep/stress, HRV, and space-weather context to this record.",
            )
            mission_day = st.number_input(
                "Mission day",
                min_value=0,
                max_value=999,
                value=int(latest.get("mission_day", 1)),
                step=1,
            )
            habitat = st.selectbox(
                "Habitat / Analog site",
                options=habitats,
                index=_safe_selectbox_index(latest.get("habitat"), habitats, 0),
            )
        with col_b:
            crew_role = st.selectbox(
                "Crew role",
                options=crew_roles,
                index=_safe_selectbox_index(latest.get("crew_role"), crew_roles, 0),
            )
            autonomy_level = st.selectbox(
                "EIMO autonomy level",
                options=autonomy_levels,
                index=_safe_selectbox_index(latest.get("autonomy_level"), autonomy_levels, 0),
                help="Earth-Independent Medical Operations autonomy classification",
            )
            comm_delay_min = st.number_input(
                "Comm delay (min, one-way)",
                min_value=0.0,
                max_value=25.0,
                value=float(latest.get("comm_delay_min", 0.0)),
                step=0.5,
                help="Mars averages 3–22 min one-way; Gateway ~1.3 s",
            )
        with col_c:
            eva_status = st.selectbox(
                "EVA clearance",
                options=eva_status_options,
                index=_safe_selectbox_index(latest.get("eva_status"), eva_status_options, 0),
            )
            eva_hours = st.number_input(
                "EVA hours (last 72h)",
                min_value=0.0,
                max_value=36.0,
                value=float(latest.get("eva_hours_72h", 0.0)),
                step=0.5,
            )
            days_since_last_eva = st.number_input(
                "Days since last EVA",
                min_value=0,
                max_value=365,
                value=int(latest.get("days_since_last_eva", 0)),
                step=1,
            )
        
        # ─────────────────────────────────────────────────────────────────────
        # Section 2: Radiation & Space Weather (ExMC risk domain)
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("##### ☢️ Radiation & Space Weather")
        space_summary = _space_weather_summary_for_date(record_date)
        dose_rate_msv_day, dose_rate_ref = _estimate_baseline_radiation_msv_per_day(
            mission_profile=str(mission_profile),
            habitat=str(habitat),
        )
        # EVA increases exposure because shielding is reduced; we model this as a
        # bounded multiplier on the baseline dose rate during EVA hours.
        eva_multiplier = 1.2 if (str(habitat) == "ISS" or str(mission_profile) == "LEO-ISS") else 1.8
        eva_extra_msv = float(dose_rate_msv_day) * (float(eva_hours) / 24.0) * max(eva_multiplier - 1.0, 0.0)
        estimated_cumulative_msv = (float(dose_rate_msv_day) * float(mission_day)) + eva_extra_msv

        col_sw1, col_sw2, col_sw3, col_sw4 = st.columns(4)
        with col_sw1:
            kp_max = space_summary.get("kp_max")
            st.metric("Kp (max, day)", f"{kp_max:.1f}" if isinstance(kp_max, (int, float)) and np.isfinite(float(kp_max)) else "—")
        with col_sw2:
            st.metric("Geomagnetic", str(space_summary.get("kp_g_scale") or "G0"))
        with col_sw3:
            proton_max = space_summary.get("proton_max_pfu")
            st.metric(">10 MeV protons (max)", f"{proton_max:.0f} pfu" if isinstance(proton_max, (int, float)) and np.isfinite(float(proton_max)) else "—")
        with col_sw4:
            st.metric("Radiation storm", str(space_summary.get("proton_s_scale") or "S0"))

        st.caption(
            f"Baseline dose-rate anchor: ~{dose_rate_msv_day:.3f} mSv/day ({dose_rate_ref}). "
            f"EVA surcharge (approx): +{eva_extra_msv:.3f} mSv for {eva_hours:.1f} h/24h equivalent."
        )

        auto_radiation = st.checkbox(
            "Auto-estimate cumulative dose from mission + EVA",
            value=True,
            help="Uses published dose-rate anchors for the selected environment and a bounded EVA surcharge. "
            "Storm-time dose spikes are not modelled; treat space-weather S-scale as a hazard indicator.",
        )
        auto_space_weather = st.checkbox(
            "Auto-compute space-weather alert",
            value=True,
            help="Maps observed Kp (G-scale) and >10 MeV proton flux (S-scale) to the profile alert taxonomy.",
        )

        rad_limit_msv = 600.0  # NASA STD-3001B (career effective dose design limit)
        default_alert = str(space_summary.get("alert_category") or "None")
        if default_alert not in space_weather_alerts:
            default_alert = "None"

        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            radiation_dose = st.number_input(
                "Cumulative dose (mSv)",
                min_value=0.0,
                max_value=1200.0,
                value=float(estimated_cumulative_msv) if auto_radiation else float(latest.get("radiation_dose_msv", estimated_cumulative_msv)),
                step=0.5,
                help="NASA career effective dose design limit: 600 mSv (STD-3001).",
            )
            st.caption(f"Limit reference: {rad_limit_msv:.0f} mSv (career, effective dose)")
        with col_r2:
            space_weather = st.selectbox(
                "Space-weather alert level",
                options=space_weather_alerts,
                index=_safe_selectbox_index(default_alert if auto_space_weather else latest.get("space_weather_alert"), space_weather_alerts, 0),
            )
            st.caption(f"Computed: {space_summary.get('kp_g_scale','G0')} / {space_summary.get('proton_s_scale','S0')}")
        with col_r3:
            gcr_default = bool(latest.get("gcr_concern", False))
            if not gcr_default:
                gcr_default = str(mission_profile) not in {"LEO-ISS", "ANALOG-CHAPEA", "ANALOG-HERA"}
            galactic_cosmic_ray = st.checkbox(
                "GCR exposure concern",
                value=gcr_default,
                help="Galactic Cosmic Ray monitoring for deep-space missions",
            )
        
        # ─────────────────────────────────────────────────────────────────────
        # Section 3: Health Status (Chronic / Acute / Behavioral)
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("##### 🩺 Health Status")
        
        # Helper to filter stored defaults against current options (resilient to schema changes)
        def _safe_multiselect_default(stored: list, options: list) -> list:
            """Return only stored values that exist in current options."""
            if not stored:
                return []
            valid = [v for v in stored if v in options]
            # Log migration warnings for stale values
            stale = set(stored) - set(valid)
            if stale:
                _LOGGER.debug(
                    "Multiselect schema migration: dropped stale defaults %s",
                    stale,
                )
            return valid
        
        chronic_conditions = st.multiselect(
            "Chronic condition log (HRP risk categories)",
            options=chronic_condition_options,
            default=_safe_multiselect_default(
                latest.get("chronic_conditions", []),
                chronic_condition_options,
            ),
        )
        acute_symptoms = st.multiselect(
            "Acute symptoms (last 24h)",
            options=acute_symptom_options,
            default=_safe_multiselect_default(
                latest.get("acute_symptoms", []),
                acute_symptom_options,
            ),
        )
        behavioral_state = st.multiselect(
            "Behavioral health notes",
            options=behavioral_flags,
            default=_safe_multiselect_default(
                latest.get("behavioral_flags", []),
                behavioral_flags,
            ),
        )

        # Objective context (HRV + Garmin) aligned to the selected log date.
        target_day = pd.Timestamp(record_date).normalize()
        hrv_daily = _load_hrv_daily_objective(user.user_id)
        garmin_daily = _load_garmin_daily_objective(user.user_id)

        stress_index_day: Optional[float] = None
        stress_scale_obj: Optional[int] = None
        if not hrv_daily.empty and target_day in hrv_daily.index and "stress_index" in hrv_daily.columns:
            stress_index_day = _safe_float(hrv_daily.loc[target_day, "stress_index"])
            baseline = pd.to_numeric(hrv_daily["stress_index"], errors="coerce").dropna()
            if stress_index_day is not None and not baseline.empty:
                if len(baseline) >= 5:
                    percentile = float((baseline < float(stress_index_day)).mean())
                    stress_scale_obj = int(np.clip(int(round(1.0 + percentile * 9.0)), 1, 10))
                else:
                    stress_scale_obj = int(np.clip(int(round(np.log10(float(stress_index_day) + 1.0) * 2.5)), 1, 10))

        garmin_row: Optional[pd.Series] = None
        if not garmin_daily.empty and target_day in garmin_daily.index:
            garmin_row = garmin_daily.loc[target_day]

        sleep_hours_obj = _safe_float(garmin_row.get("sleep_duration_hours")) if garmin_row is not None else None
        sleep_quality_obj: Optional[int] = None
        if garmin_row is not None:
            eff = _safe_float(garmin_row.get("sleep_efficiency"))
            score = _safe_float(garmin_row.get("sleep_score"))
            quality_norm: Optional[float] = None
            if eff is not None:
                quality_norm = float(eff) / 100.0 if eff > 1.2 else float(eff)
            elif score is not None:
                quality_norm = float(score) / 100.0 if score > 1.2 else float(score)
            if quality_norm is not None and np.isfinite(quality_norm):
                sleep_quality_obj = int(np.clip(int(round(1.0 + quality_norm * 4.0)), 1, 5))

        col_seed1, col_seed2, col_seed3 = st.columns(3)
        with col_seed1:
            use_hrv_stress = st.checkbox(
                "Seed stress from HRV (objective)",
                value=stress_scale_obj is not None,
                help="Uses the daily-median Baevsky Stress Index (from HRV history) to seed the 1–10 stress slider.",
            )
        with col_seed2:
            use_garmin_sleep = st.checkbox(
                "Seed sleep from Garmin (objective)",
                value=sleep_hours_obj is not None,
                help="Uses Garmin daily sleep duration/efficiency (if available) to seed the sleep fields.",
            )
        with col_seed3:
            if stress_index_day is not None:
                st.metric("HRV stress index (day)", f"{float(stress_index_day):.0f}")
            elif garmin_row is not None and _safe_float(garmin_row.get("stress_score")) is not None:
                st.metric("Garmin stress (day)", f"{_safe_float(garmin_row.get('stress_score')):.0f}")
            else:
                st.metric("Objective context", "—")

        col_h1, col_h2 = st.columns(2)
        with col_h1:
            confinement_stress = st.slider(
                "Confinement stress (1–10)",
                min_value=1,
                max_value=10,
                value=int(stress_scale_obj) if use_hrv_stress and stress_scale_obj is not None else int(latest.get("confinement_stress", 3)),
            )
        with col_h2:
            workload_rating = st.slider(
                "Workload rating (1–10)",
                min_value=1,
                max_value=10,
                value=int(latest.get("workload_rating", 5)),
                help="NASA TLX-style subjective workload",
            )
        
        # ─────────────────────────────────────────────────────────────────────
        # Section 4: Countermeasures & Life Support
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("##### 🏋️ Countermeasures & Life Support")
        col_d, col_e, col_f = st.columns(3)
        with col_d:
            sleep_hours = st.number_input(
                "Sleep (last 24h, hours)",
                min_value=0.0,
                max_value=14.0,
                value=float(sleep_hours_obj) if use_garmin_sleep and sleep_hours_obj is not None else float(latest.get("sleep_hours", 7.0)),
                step=0.25,
            )
            sleep_quality = st.slider(
                "Sleep quality (1–5)",
                min_value=1,
                max_value=5,
                value=int(sleep_quality_obj) if use_garmin_sleep and sleep_quality_obj is not None else int(latest.get("sleep_quality", 3)),
            )
        with col_e:
            exercise_minutes = st.number_input(
                "Countermeasure exercise (min/day)",
                min_value=0.0,
                max_value=300.0,
                value=float(latest.get("exercise_minutes", 120.0)),
                step=5.0,
                help="ISS target ~2 h/day resistive + aerobic",
            )
            _exercise_modalities = ["ARED", "T2 / COLBERT", "CEVIS", "Combined", "Limited", "None"]
            exercise_type = st.selectbox(
                "Primary exercise modality",
                options=_exercise_modalities,
                index=_safe_selectbox_index(latest.get("exercise_type"), _exercise_modalities, 3),
            )
        with col_f:
            hydration_liters = st.number_input(
                "Water intake (L/day)",
                min_value=0.0,
                max_value=10.0,
                value=float(latest.get("hydration_liters", 3.8)),
                step=0.1,
            )
            caloric_intake = st.number_input(
                "Caloric intake (kcal/day)",
                min_value=0,
                max_value=5000,
                value=int(latest.get("caloric_intake", 2500)),
                step=50,
            )
        
        # ─────────────────────────────────────────────────────────────────────
        # Section 5: Medical Inventory & Logistics
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("##### 📦 Medical Inventory & Logistics")
        col_inv1, col_inv2 = st.columns(2)
        with col_inv1:
            _inventory_status_options = ["Nominal", "Monitor", "Low Stock", "Critical Shortage"]
            inventory_alert = st.selectbox(
                "Medical inventory status",
                options=_inventory_status_options,
                index=_safe_selectbox_index(latest.get("inventory_alert"), _inventory_status_options, 0),
            )
        with col_inv2:
            resupply_days = st.number_input(
                "Days until next resupply",
                min_value=0,
                max_value=999,
                value=int(latest.get("resupply_days", 0)),
                step=1,
                help="0 = N/A or continuous resupply (LEO)",
            )
        
        notes = st.text_area(
            "Operational / Clinical notes",
            value=str(latest.get("notes", "")),
            height=100,
        )
        update_latest = st.checkbox(
            "Update latest entry instead of creating a new record",
            value=False,
        )
        
        submitted = st.form_submit_button("💾 Save Exploration Medical Record")
        if submitted:
            if not _should_process_form_submission(form_key):
                st.info("Processing previous submission... please wait.")
                return
            radiation_dose_to_store = float(estimated_cumulative_msv) if auto_radiation else float(radiation_dose)
            space_weather_to_store = default_alert if auto_space_weather else str(space_weather)
            stress_source = "hrv" if (use_hrv_stress and stress_scale_obj is not None) else "manual"
            sleep_source = "garmin" if (use_garmin_sleep and sleep_hours_obj is not None) else "manual"
            record = {
                # Mission Context
                "mission_profile": mission_profile,
                "record_date": record_date.isoformat(),
                "mission_day": mission_day,
                "habitat": habitat,
                "crew_role": crew_role,
                "autonomy_level": autonomy_level,
                "comm_delay_min": comm_delay_min,
                "eva_status": eva_status,
                "eva_hours_72h": eva_hours,
                "days_since_last_eva": days_since_last_eva,
                # Radiation & Space Weather
                "radiation_dose_msv": radiation_dose_to_store,
                "radiation_limit_msv": float(rad_limit_msv),
                "radiation_baseline_msv_per_day": float(dose_rate_msv_day),
                "radiation_baseline_reference": str(dose_rate_ref),
                "radiation_eva_multiplier": float(eva_multiplier),
                "radiation_eva_extra_msv": float(eva_extra_msv),
                "radiation_estimated_cumulative_msv": float(estimated_cumulative_msv),
                "radiation_model": "baseline_rate_x_days_plus_eva_surcharge",
                "space_weather_alert": space_weather_to_store,
                "space_weather_auto": bool(auto_space_weather),
                "kp_max": space_summary.get("kp_max"),
                "kp_g_scale": space_summary.get("kp_g_scale"),
                "proton_max_pfu": space_summary.get("proton_max_pfu"),
                "proton_s_scale": space_summary.get("proton_s_scale"),
                "gcr_concern": galactic_cosmic_ray,
                # Health Status
                "chronic_conditions": chronic_conditions,
                "acute_symptoms": acute_symptoms,
                "behavioral_flags": behavioral_state,
                "confinement_stress": confinement_stress,
                "confinement_stress_source": stress_source,
                "confinement_stress_obj": int(stress_scale_obj) if stress_scale_obj is not None else None,
                "hrv_stress_index_obj": float(stress_index_day) if stress_index_day is not None else None,
                "workload_rating": workload_rating,
                # Countermeasures
                "sleep_hours": sleep_hours,
                "sleep_quality": sleep_quality,
                "sleep_source": sleep_source,
                "sleep_hours_obj": float(sleep_hours_obj) if sleep_hours_obj is not None else None,
                "sleep_quality_obj": int(sleep_quality_obj) if sleep_quality_obj is not None else None,
                "exercise_minutes": exercise_minutes,
                "exercise_type": exercise_type,
                "hydration_liters": hydration_liters,
                "caloric_intake": caloric_intake,
                # Inventory
                "inventory_alert": inventory_alert,
                "resupply_days": resupply_days,
                "notes": notes,
            }
            try:
                entry_id = db.save_medical_history_entry(
                    user.user_id,
                    record,
                    history_id=latest.get("history_id") if (update_latest and latest) else None,
                )
                st.success("Exploration medical record saved.")
                st.session_state["last_med_record_id"] = entry_id
            except Exception as exc:
                st.error(f"Failed to save medical record: {exc}")
    
    if history:
        st.markdown("#### 📚 Recent Medical Records")
        display_df = pd.DataFrame(history)
        # Flatten list columns for readability
        for col in ["chronic_conditions", "acute_symptoms", "behavioral_flags"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(
                    lambda val: ", ".join(val) if isinstance(val, list) else val
                )
        st.dataframe(
            display_df[
                [
                    "updated_at",
                    "mission_profile",
                    "mission_day",
                    "eva_status",
                    "space_weather_alert",
                    "radiation_dose_msv",
                    "sleep_hours",
                    "exercise_minutes",
                ]
            ],
            use_container_width=True,
        )
    else:
        st.info("No exploration medical records logged yet.")


# ---------------------------------------------------------------------------
# User Sessions Tab (Multi-User Support)
# ---------------------------------------------------------------------------


def _render_user_sessions_tab(current_user: UserProfile) -> None:
    """Render the user sessions management tab."""
    st.markdown("## 👥 User Sessions Management")
    
    if not MULTI_USER_AVAILABLE:
        st.info(
            "Multi-user sessions allow you to have up to 7 users open simultaneously. "
            "This feature enables quick switching between users for data entry and analysis."
        )
        st.warning("Multi-user module not available. Ensure `multi_user_session.py` is in the app directory.")
        return
    
    manager = get_multi_user_manager()
    
    # Display session count
    col1, col2 = st.columns([2, 1])
    with col1:
        st.metric("Active Sessions", f"{manager.session_count}/{MAX_CONCURRENT_USERS}")
    with col2:
        if manager.can_add_user:
            st.success("✓ Can add more users")
        else:
            st.warning("⚠️ Maximum reached")
    
    st.markdown("---")
    
    # Full session manager
    render_user_session_manager()
    
    st.markdown("---")
    
    # Quick add user section
    st.markdown("### ➕ Add Another User")
    st.caption("Log in with another existing account to add them to your active sessions.")
    
    try:
        db = get_database()
        all_users = db.list_users()
        
        # Filter out already active users
        active_ids = {s["user_id"] for s in manager.get_all_sessions_summary()}
        available_users = [u for u in all_users if u.user_id not in active_ids]
        
        if not available_users:
            if not all_users:
                st.info("No other users registered. Register new users from the Login tab.")
            else:
                st.info("All registered users are already in active sessions.")
        elif not manager.can_add_user:
            st.warning(f"Maximum {MAX_CONCURRENT_USERS} sessions reached. Close a session to add more users.")
        else:
            user_options = {u.username: u for u in available_users}
            selected = st.selectbox(
                "Select user to add",
                options=list(user_options.keys()),
                format_func=lambda x: f"{x} ({user_options[x].full_name or x})",
                key="add_user_session_select",
            )
            
            if st.button("➕ Add to Active Sessions", key="add_user_session_btn"):
                user_to_add = user_options[selected]
                if manager.add_user_session(
                    user_id=user_to_add.user_id,
                    username=user_to_add.username,
                    full_name=user_to_add.full_name or user_to_add.username,
                    make_active=False,  # Don't switch, just add
                ):
                    st.success(f"Added {user_to_add.username} to active sessions!")
                    st.rerun()
                else:
                    st.error("Failed to add user session.")
    
    except Exception as exc:
        st.error(f"Error loading users: {exc}")
    
    st.markdown("---")
    
    # Roadmap note
    st.info(
        "🚀 **Coming Soon**: Full multi-user analysis capabilities including:\n"
        "- Per-user correlation calculations\n"
        "- Group-based analysis (inter-subject)\n"
        "- Longitudinal tracking (baseline + 22 timepoints)\n"
        "- Comparative HRV metrics across users\n\n"
        "See [WARP.md](WARP.md) for the complete roadmap."
    )


# ---------------------------------------------------------------------------
# Main Tab Renderer
# ---------------------------------------------------------------------------


def render_user_profile_tab() -> None:
    """
    Render the complete User Profile tab.
    
    This is the main entry point for the tab.
    """
    st.header("👤 User Profile & Clinical Assessments")
    
    if not DATABASE_AVAILABLE:
        st.error(
            "User database module not available. "
            "Please ensure `user_database.py` is in the app directory."
        )
        return
    
    # Show multi-user session manager if available and users are active
    if MULTI_USER_AVAILABLE:
        manager = get_multi_user_manager()
        if manager.session_count > 1:
            with st.expander(f"👥 Active Sessions ({manager.session_count}/{MAX_CONCURRENT_USERS})", expanded=False):
                render_user_session_manager()
            st.divider()
    
    # Check current user
    current_user = _get_current_user()
    
    if current_user is None:
        # Show login/registration
        tab_login, tab_register = st.tabs(["🔑 Login", "📝 Register"])
        
        with tab_login:
            _render_login_section()
        
        with tab_register:
            new_user = _render_registration_form()
            if new_user:
                _set_current_user(new_user)
                st.rerun()
    else:
        # Show profile and assessments
        if st.session_state.get("edit_profile_mode"):
            _render_profile_edit(current_user)
        else:
            _render_profile_view(current_user)
        
        st.markdown("---")

        # Timepoint selector (shared across sub-tabs; avoids duplicate keys).
        _render_longitudinal_timepoint_controls(current_user.user_id)
        st.markdown("---")
        
        # PERFORMANCE FIX: Use selectbox navigation instead of nested tabs
        # Nested st.tabs renders ALL content on every rerun, causing severe slowdowns.
        # Selectbox with conditional rendering only processes the selected section.
        profile_sections = [
            "📋 Assessments",
            "🏥 Clinical Profile",
            "📈 History",
            "💓 HRV",
            "🏃 Readiness",
            "📦 Data",
            "👥 Sessions",
        ]
        
        selected_section = st.selectbox(
            "📂 Profile Section",
            options=profile_sections,
            index=0,
            key=f"profile_section_nav_{current_user.user_id}",
            help="Select a section to view. Only the selected section is loaded for better performance.",
        )
        
        st.markdown("---")
        
        # Render only the selected section (lazy loading)
        if selected_section == "📋 Assessments":
            _render_clinical_assessment(current_user)
        
        elif selected_section == "🏥 Clinical Profile":
            _render_clinical_profile(current_user)
        
        elif selected_section == "📈 History":
            _render_assessment_history(current_user)
            st.markdown("---")
            _render_garmin_metrics_history(current_user)
        
        elif selected_section == "💓 HRV":
            _render_profile_rr_uploads(current_user)
            st.markdown("---")
            _render_profile_rr_library(current_user)
            st.markdown("---")
            _render_hrv_history(current_user)

        elif selected_section == "🏃 Readiness":
            _render_profile_readiness(current_user)
        
        elif selected_section == "📦 Data":
            _render_fit_csv_tools(current_user)
            st.markdown("---")
            _render_garmin_ingest(current_user)
            st.markdown("---")
            _render_data_management(current_user)
        
        elif selected_section == "👥 Sessions":
            _render_user_sessions_tab(current_user)


# ---------------------------------------------------------------------------
# Convenience functions for getting current user data (for other modules)
# ---------------------------------------------------------------------------


def get_current_user_data() -> Optional[Dict[str, Any]]:
    """
    Get current user's data for use by other modules.
    
    Returns:
        Dictionary with user profile data or None if not logged in.
    """
    user = _get_current_user()
    if user is None:
        return None
    
    latest_medical_record: Dict[str, Any] = {}
    try:
        db = get_database()
        last_rows = db.get_medical_history(user.user_id, limit=1)
        if last_rows:
            latest_medical_record = last_rows[0]
    except Exception:
        latest_medical_record = {}
    
    return {
        "user_id": user.user_id,
        "username": user.username,
        "full_name": user.full_name,
        "age_years": _calculate_age(user.date_of_birth),
        "sex": user.sex,
        "height_cm": user.height_cm,
        "weight_kg": user.weight_kg,
        "bmi": _calculate_bmi(user.height_cm, user.weight_kg),
        "resting_hr_bpm": user.resting_hr_bpm,
        "max_hr_bpm": user.max_hr_bpm,
        "vo2max_ml_kg_min": user.vo2max_ml_kg_min,
        "activity_level": user.activity_level,
        "occupation": user.occupation,
        "language": getattr(user, 'language', 'en'),
        "medical_conditions": getattr(user, 'medical_conditions', []),
        "medications": getattr(user, 'medications', []),
        "medical_record": latest_medical_record,
    }


def get_active_user_context() -> Dict[str, Any]:
    """
    Get comprehensive user context for all tabs to use in calculations.
    
    This function provides all user-specific settings that affect computations:
    - Demographics for age-adjusted calculations
    - Physiological parameters (VO2max, resting HR, max HR)
    - Body composition for energy calculations
    - Activity level for metabolic adjustments
    - Medical history for risk considerations
    
    Returns:
        Dictionary with user context, or defaults if no user logged in.
    """
    user = _get_current_user()
    
    # Default context if no user
    if user is None:
        return {
            "has_user": False,
            "user_id": None,
            "username": "Guest",
            "age_years": 35,  # Default middle-aged adult
            "sex": "other",
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "bmi": 24.2,
            "resting_hr_bpm": 70,
            "max_hr_bpm": 185,
            "vo2max_ml_kg_min": 35.0,  # Average fitness
            "activity_level": "moderately_active",
            "chronotype_offset": 0.0,  # Neutral chronotype
            "occupation": None,
            "medical_conditions": [],
            "medications": [],
            "medical_record": {},
            "is_guest": True,
        }
    
    # Calculate derived values
    age = _calculate_age(user.date_of_birth)
    bmi = _calculate_bmi(user.height_cm, user.weight_kg)
    
    # Estimate max HR if not provided (using Fox formula)
    max_hr = user.max_hr_bpm
    if max_hr is None and age is not None:
        max_hr = 220 - age
    
    # Estimate chronotype offset from occupation (simplified)
    chronotype_offset = 0.0
    if user.occupation:
        occupation_lower = user.occupation.lower()
        if any(x in occupation_lower for x in ["night", "shift", "pilot", "flight"]):
            chronotype_offset = 1.0  # Slight evening tendency for shift workers
        elif any(x in occupation_lower for x in ["early", "morning", "farmer"]):
            chronotype_offset = -1.0  # Morning tendency
    
    latest_medical_record: Dict[str, Any] = {}
    body_composition: Dict[str, Any] = {}
    personalized_metrics: Dict[str, Any] = {}
    
    try:
        db = get_database()
        med_rows = db.get_medical_history(user.user_id, limit=1)
        if med_rows:
            latest_medical_record = med_rows[0]
        
        # Load body composition data
        if hasattr(db, "get_body_composition_history"):
            comp_rows = db.get_body_composition_history(user.user_id, limit=1)
            if comp_rows:
                latest_comp = comp_rows[0]
                body_composition = {
                    "neck_cm": getattr(latest_comp, 'neck_cm', None),
                    "waist_cm": getattr(latest_comp, 'waist_cm', None),
                    "hip_cm": getattr(latest_comp, 'hip_cm', None),
                    "body_fat_pct": getattr(latest_comp, 'body_fat_pct', None),
                    "lean_mass_kg": getattr(latest_comp, 'lean_mass_kg', None),
                    "muscle_mass_kg": getattr(latest_comp, 'muscle_mass_kg', None),
                    "chest_cm": getattr(latest_comp, 'chest_cm', None),
                    "measurement_date": getattr(latest_comp, 'measurement_date', None),
                }
        
        # Calculate personalized metrics if module available
        if PERSONALIZED_COMPUTATIONS_AVAILABLE and age is not None:
            try:
                personalized_metrics = calculate_all_personalized_metrics(
                    weight_kg=user.weight_kg or 70.0,
                    height_cm=user.height_cm or 170.0,
                    age=age,
                    sex=user.sex or "other",
                    neck_cm=body_composition.get("neck_cm"),
                    waist_cm=body_composition.get("waist_cm"),
                    hip_cm=body_composition.get("hip_cm"),
                    vo2max=user.vo2max_ml_kg_min,
                    resting_hr=user.resting_hr_bpm,
                    activity_level=user.activity_level or "moderate",
                )
            except Exception:
                personalized_metrics = {}
    except Exception:
        latest_medical_record = {}
        body_composition = {}
        personalized_metrics = {}
    
    return {
        "has_user": True,
        "user_id": user.user_id,
        "username": user.username,
        "full_name": user.full_name,
        "age_years": age or 35,
        "sex": user.sex or "other",
        "weight_kg": user.weight_kg or 70.0,
        "height_cm": user.height_cm or 170.0,
        "bmi": bmi or 24.2,
        "resting_hr_bpm": user.resting_hr_bpm or 70,
        "max_hr_bpm": max_hr or 185,
        "vo2max_ml_kg_min": user.vo2max_ml_kg_min or 35.0,
        "activity_level": user.activity_level or "moderately_active",
        "chronotype_offset": chronotype_offset,
        # Body composition data
        "neck_cm": body_composition.get("neck_cm"),
        "waist_cm": body_composition.get("waist_cm"),
        "hip_cm": body_composition.get("hip_cm"),
        "body_fat_pct": body_composition.get("body_fat_pct"),
        "lean_mass_kg": body_composition.get("lean_mass_kg"),
        "body_composition": body_composition,
        # Personalized calculations
        "personalized_metrics": personalized_metrics,
        "hrv_norms": personalized_metrics.get("hrv_norms", {}),
        "occupation": user.occupation,
        "medical_conditions": getattr(user, 'medical_conditions', []),
        "medications": getattr(user, 'medications', []),
        "language": getattr(user, 'language', 'en'),
        "is_guest": False,
        "medical_record": latest_medical_record,
    }


def get_all_active_users() -> List[Dict[str, Any]]:
    """
    Get data for all users in active sessions.
    
    Returns:
        List of user data dictionaries for all active users.
    """
    if not MULTI_USER_AVAILABLE:
        # Fall back to current user only
        current = get_current_user_data()
        return [current] if current else []
    
    try:
        manager = get_multi_user_manager()
        sessions = manager.get_all_sessions_summary()
        
        if not sessions:
            return []
        
        db = get_database()
        users_data = []
        
        for session in sessions:
            user = db.get_user(session["user_id"])
            if user:
                users_data.append({
                    "user_id": user.user_id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "age_years": _calculate_age(user.date_of_birth),
                    "sex": user.sex,
                    "weight_kg": user.weight_kg,
                    "height_cm": user.height_cm,
                    "is_active": session["is_active"],
                })
        
        return users_data
    
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    "render_user_profile_tab",
    "get_current_user_data",
    "get_active_user_context",
    "get_all_active_users",
]

