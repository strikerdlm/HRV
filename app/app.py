# flake8: noqa
from __future__ import annotations

# NOTE:
# This file is both a Streamlit entrypoint (`streamlit run app/app.py`) and is
# imported by the unit tests as a module (`import app.app`). Streamlit execution
# typically adds the script directory to `sys.path`, but importing as `app.app`
# does not. We insert the local `app/` directory onto `sys.path` so the existing
# intra-app absolute imports (e.g., `import hrv_core`) remain resolvable in both
# contexts.
#
# This is deterministic, bounded, and required for testability.
#
# STREAMLIT VERSION:
# This app uses Streamlit 1.36.0 (pinned in requirements.txt).
# This is the last stable release BEFORE the @st.fragment changes in 1.37+
# that caused "SessionInfo" and "Bad setIn index" race condition errors.
# Version 1.35.0 was tested but caused tabs not to load properly.
# Error suppressor is kept active as a safety net (see _inject_sessioninfo_suppressor).
import sys
from pathlib import Path
from functools import lru_cache

_APP_DIR = Path(__file__).resolve().parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

# Pytest environments sometimes place `app/` on `sys.path` directly, causing
# `import app` to resolve to this file (`app/app.py`) instead of the package
# (`app/__init__.py`). In that case, make this module behave like a package so
# imports like `from app import noaa_space` and `from app.multiday_tracker import ...`
# continue to work, and alias `app.app` to this module for compatibility.
if __name__ == "app":
    __path__ = [str(_APP_DIR)]  # type: ignore[name-defined]
    sys.modules.setdefault("app.app", sys.modules[__name__])

# -------------------------------------------------------------------------
# Streamlit page config MUST be the first Streamlit command
# -------------------------------------------------------------------------
# NOTE: This module imports many submodules that themselves use Streamlit
# (e.g., cache decorators). We must set page config *before* importing them.
import os

import streamlit as st

def _safe_set_page_config() -> None:
    """Best-effort page config without crashing the app.

    Streamlit requires `st.set_page_config()` be the first Streamlit command. In
    complex apps, import-time decorators (e.g., `@st.cache_data`) or other
    modules may enqueue a delta before this module is imported, making page
    config illegal and raising StreamlitAPIException.

    We fail closed on *crashes* (never crash the app due to page config), and
    skip setting page config if Streamlit already disallowed it.
    """

    if os.environ.get("HRV_SKIP_STREAMLIT_PAGE_CONFIG") == "1":
        return

    try:
        from streamlit.runtime.scriptrunner.script_run_context import (  # noqa: PLC0415
            get_script_run_ctx,
        )
    except Exception:
        get_script_run_ctx = None  # type: ignore[assignment]

    if get_script_run_ctx is not None:
        ctx = get_script_run_ctx()
        if ctx is not None and not getattr(ctx, "_set_page_config_allowed", True):
            return

    try:
        st.set_page_config(
            page_title="HRV Analysis — Streamlit + ECharts",
            layout="wide",
        )
    except Exception:
        # Do not crash the app for cosmetic configuration.
        return


_safe_set_page_config()

from gpt_interpretation import (
    GPT5InterpretationError,
    InterpretationResult,
    build_analysis_payload,
    request_interpretation,
)
from hrv_core import (
    build_readiness_baseline,
    clean_rr_intervals,
    compute_30_15_ratio,
    compute_comprehensive_hrv,
    compute_deep_breathing_response,
    compute_valsalva_ratio,
    compute_windowed_hrv,
    load_rr_intervals_from_text,
    psd_curve,
    readiness_from_pns,
    spectrogram_rr,
)
from ml_enhancements import run_windowed_kmeans
from export_utils import (
    CohortExportConfiguration,
    ExportConfiguration,
    ExportScope,
    build_cohort_markdown_report,
    build_cohort_longitudinal_delta_long_df,
    build_cohort_longitudinal_markdown_report,
    build_markdown_report,
    compare_cohort_longitudinal_groups,
    compute_cohort_longitudinal_group_summary,
    compute_cohort_summary_stats,
    fit_cohort_longitudinal_mixed_effects,
)
from echarts_component import EChartsConfig, render_echarts
from space_weather_alignment import (
    align_space_weather_series,
    align_space_weather_columns,
)
from space_weather_influence import (
    InfluenceHorizonRecommendation,
    build_donki_cme_influence_windows,
    recommend_influence_horizons_from_hrv,
)
from noaa_space import (
    NOAADataBundle,
    load_noaa_space_data,
    load_noaa_space_cache,
    slice_noaa_bundle_time_range,
    get_noaa_metric_explanations,
    explain_noaa_metric,
)

# Scientific charts for unified timeline and ML pattern visualization
try:
    from scientific_charts import (
        build_unified_physiology_timeline,
        build_physiology_correlation_matrix,
        build_ml_pattern_chart,
        COLORS as SCIENTIFIC_COLORS,
    )
    SCIENTIFIC_CHARTS_AVAILABLE = True
except ImportError:
    SCIENTIFIC_CHARTS_AVAILABLE = False

# About tab module
try:
    from about_tab import render_about_tab, get_app_version, get_app_metadata
    ABOUT_TAB_AVAILABLE = True
except ImportError:
    ABOUT_TAB_AVAILABLE = False

# Circadian physiology module
try:
    from circadian_tab import render_circadian_tab
    CIRCADIAN_TAB_AVAILABLE = True
except ImportError:
    CIRCADIAN_TAB_AVAILABLE = False

# Welcome header module
try:
    from welcome_header import render_welcome_header, render_device_import_header
    WELCOME_HEADER_AVAILABLE = True
except ImportError:
    WELCOME_HEADER_AVAILABLE = False

# Device imports module
try:
    from device_imports import (
        render_primary_import_section,
        render_all_device_imports,
        render_polar_import_section,
        render_garmin_import_section,
        ImportedRRData,
    )
    DEVICE_IMPORTS_AVAILABLE = True
except ImportError:
    DEVICE_IMPORTS_AVAILABLE = False

# Space weather persistence module
try:
    from space_weather_persistence import (
        get_space_weather_store,
        fetch_and_store_kp_index,
        fetch_and_store_solar_wind,
        fetch_and_store_f107,
        align_space_weather_with_hrv,
        compute_hrv_space_weather_correlation,
    )
    SPACE_WEATHER_PERSISTENCE_AVAILABLE = True
except ImportError:
    SPACE_WEATHER_PERSISTENCE_AVAILABLE = False

# Performance utilities for CPU optimization
try:
    from performance_utils import (
        get_performance_settings,
        render_performance_settings_sidebar,
        downsample_array,
        sample_large_dataframe,
        optimize_dataframe,
        cached_in_session,
        TimedExecution,
        get_performance_metrics,
        is_computation_enabled,
        is_download_enabled,
        HEAVY_COMPUTATIONS,
        HEAVY_DOWNLOADS,
    )
    PERFORMANCE_UTILS_AVAILABLE = True
except ImportError:
    PERFORMANCE_UTILS_AVAILABLE = False
    
    # Fallback functions when performance_utils is not available
    def is_computation_enabled(key: str) -> bool:
        return True
    
    def is_download_enabled(key: str) -> bool:
        return True
    
    HEAVY_COMPUTATIONS: Dict[str, str] = {}
    HEAVY_DOWNLOADS: Dict[str, str] = {}

# GPU processing module for NVIDIA CUDA acceleration
try:
    from gpu_processing import (
        get_gpu_info,
        get_gpu_config,
        set_gpu_config,
        is_gpu_enabled,
        render_gpu_settings_sidebar,
        compute_rmssd_gpu,
        compute_sdnn_gpu,
        compute_pnn50_gpu,
        benchmark_gpu,
        GPUConfig,
    )
    GPU_PROCESSING_AVAILABLE = True
except ImportError:
    GPU_PROCESSING_AVAILABLE = False

# User profile tab for centralized user data management
try:
    from user_profile_tab import (
        render_user_profile_tab,
        get_current_user_data,
        get_active_user_context,
        get_all_active_users,
    )
    USER_PROFILE_TAB_AVAILABLE = True
except ImportError:
    USER_PROFILE_TAB_AVAILABLE = False

    def get_active_user_context() -> Dict[str, Any]:
        """Fallback user context when profile tab is unavailable."""
        return _guest_user_context()

# Space weather impact prediction module
try:
    from space_weather_impact import (
        SpaceWeatherSnapshot,
        ImpactEvent,
        ImpactSeverity,
        EnergyCategory,
        fetch_space_weather_snapshot,
        build_impact_summary_df,
        get_priority_recommendation,
        get_severity_color,
        get_category_icon,
        format_datetime_bogota,
        format_countdown,
        BOGOTA_TZ_NAME,
    )
    SPACE_WEATHER_IMPACT_AVAILABLE = True
except ImportError:
    SPACE_WEATHER_IMPACT_AVAILABLE = False

# Population norms for comparison
try:
    from population_norms import (
        compare_to_population,
        generate_population_comparison_report,
        render_population_comparison_ui,
        get_hrv_norm,
        get_age_group,
        get_available_metrics,
        get_metric_info,
        AgeGroup,
        Sex,
    )
    POPULATION_NORMS_AVAILABLE = True
except ImportError:
    POPULATION_NORMS_AVAILABLE = False

# UI State Manager for conditional buttons
try:
    from ui_state_manager import (
        UIStateManager,
        DataType,
        get_state_manager,
        get_tab_settings_manager,
        get_cross_tab_broker,
        render_data_status_badge,
        render_conditional_compute_button,
        render_tab_header,
        update_data_status_from_session,
    )
    UI_STATE_MANAGER_AVAILABLE = True
except ImportError:
    UI_STATE_MANAGER_AVAILABLE = False

# ML analytics for pattern detection
try:
    from ml_analytics import (
        detect_anomalies_zscore,
        detect_anomalies_mad,
        detect_anomalies_iqr,
        analyze_trend,
        TrendDirection,
    )
    ML_ANALYTICS_AVAILABLE = True
except ImportError:
    ML_ANALYTICS_AVAILABLE = False

# Statistical analysis for correlations
try:
    from statistical_analysis import (
        compute_descriptive_stats,
        compute_correlation,
        compute_correlation_matrix,
    )
    STATISTICAL_ANALYSIS_AVAILABLE = True
except ImportError:
    STATISTICAL_ANALYSIS_AVAILABLE = False

# HRV Results Caching System for performance optimization
try:
    from hrv_cache import (
        get_cache_manager,
        get_cached_clean_rr,
        should_skip_computation,
        compute_rr_hash,
        compute_settings_hash,
    )
    HRV_CACHE_AVAILABLE = True
except ImportError:
    HRV_CACHE_AVAILABLE = False

from dataclasses import asdict, dataclass
from datetime import timezone, timedelta, datetime, date, time as dt_time
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

import concurrent.futures
import io
import hashlib
import json
import logging
import os
import re
import sys
import threading
import time
import uuid

import numpy as np
import pandas as pd
import requests
import streamlit as st

# Core ML primitives (lazy-loaded to speed startup)
RandomForestRegressor = None  # type: ignore
GradientBoostingRegressor = None  # type: ignore
ElasticNetCV = None  # type: ignore
LassoCV = None  # type: ignore
TimeSeriesSplit = None  # type: ignore
permutation_importance = None  # type: ignore
mean_absolute_error = None  # type: ignore
r2_score = None  # type: ignore
_SKLEARN_LOADED = False


def _ensure_sklearn() -> None:
    """Lazy-load sklearn to avoid slowing the welcome page startup."""
    global RandomForestRegressor
    global GradientBoostingRegressor
    global ElasticNetCV
    global LassoCV
    global TimeSeriesSplit
    global permutation_importance
    global mean_absolute_error
    global r2_score
    global _SKLEARN_LOADED
    if _SKLEARN_LOADED:
        return

    from sklearn.ensemble import RandomForestRegressor as _RF, GradientBoostingRegressor as _GB
    from sklearn.inspection import permutation_importance as _perm
    from sklearn.linear_model import ElasticNetCV as _EN, LassoCV as _Lasso
    from sklearn.metrics import mean_absolute_error as _mae, r2_score as _r2
    from sklearn.model_selection import TimeSeriesSplit as _TSCV

    RandomForestRegressor = _RF
    GradientBoostingRegressor = _GB
    ElasticNetCV = _EN
    LassoCV = _Lasso
    TimeSeriesSplit = _TSCV
    permutation_importance = _perm
    mean_absolute_error = _mae
    r2_score = _r2
    _SKLEARN_LOADED = True


# Optional advanced ML libraries (lazy-loaded for faster startup)
XGBRegressor = None  # type: ignore
LGBMRegressor = None  # type: ignore
shap = None  # type: ignore
XGBOOST_AVAILABLE = False
LIGHTGBM_AVAILABLE = False
SHAP_AVAILABLE = False
_ML_LIBS_LOADED = False


def _ensure_ml_libs() -> None:
    """Lazy-load optional ML libs (XGBoost, LightGBM, SHAP) to speed startup."""
    global XGBRegressor, LGBMRegressor, shap
    global XGBOOST_AVAILABLE, LIGHTGBM_AVAILABLE, SHAP_AVAILABLE, _ML_LIBS_LOADED
    if _ML_LIBS_LOADED:
        return

    # XGBoost
    try:
        from xgboost import XGBRegressor as _XGBRegressor  # type: ignore

        XGBRegressor = _XGBRegressor
        XGBOOST_AVAILABLE = True
    except ImportError:
        XGBRegressor = None  # type: ignore
        XGBOOST_AVAILABLE = False

    # LightGBM
    try:
        from lightgbm import LGBMRegressor as _LGBMRegressor  # type: ignore

        LGBMRegressor = _LGBMRegressor
        LIGHTGBM_AVAILABLE = True
    except ImportError:
        LGBMRegressor = None  # type: ignore
        LIGHTGBM_AVAILABLE = False

    # SHAP
    try:
        import shap as _shap  # type: ignore

        shap = _shap  # type: ignore
        SHAP_AVAILABLE = True
    except ImportError:
        shap = None  # type: ignore
        SHAP_AVAILABLE = False

    _ML_LIBS_LOADED = True
from dotenv import load_dotenv
from pathlib import Path
from pandas.api.types import is_datetime64_any_dtype
from user_database import FatigueProfileSettings, HRVMeasurement, StudyGroup, get_database
from user_data_manager import create_user_manager, parse_filename_date

try:
    # Package import (tests, package mode)
    from app.logging_config import (
        get_logger,
        log_exception,
        enable_streamlit_debug,
        log_rerun_trigger,
        StreamlitDebugContext,
    )
except ImportError:  # pragma: no cover - fallback for Streamlit script execution
    from logging_config import (
        get_logger,
        log_exception,
        enable_streamlit_debug,
        log_rerun_trigger,
        StreamlitDebugContext,
    )

try:
    from app.agent_insights import AgentInsightManager
except ImportError:  # pragma: no cover - Streamlit execution fallback
    from agent_insights import AgentInsightManager  # type: ignore

try:
    from app.agent_audio import synthesize_agent_speech
except ImportError:  # pragma: no cover - Streamlit execution fallback
    from agent_audio import synthesize_agent_speech  # type: ignore

# Default active-user context used when user profile data is unavailable
def _guest_user_context() -> Dict[str, Any]:
    return {
        "has_user": False,
        "user_id": None,
        "username": "Guest",
        "age_years": 35,
        "sex": "other",
        "weight_kg": 70.0,
        "height_cm": 170.0,
        "bmi": 24.2,
        "resting_hr_bpm": 70,
        "max_hr_bpm": 185,
        "vo2max_ml_kg_min": 35.0,
        "activity_level": "moderately_active",
        "chronotype_offset": 0.0,
        "occupation": None,
        "medical_conditions": [],
        "medications": [],
        "medical_record": {},
        "is_guest": True,
    }

# Load .env variables early (e.g., NASA_API_KEY, ACCUWEATHER_API_KEY)
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
_LOGGER = get_logger(__name__)
NASA_API_KEY = os.getenv("NASA_API_KEY", "")
ACCUWEATHER_API_KEY = os.getenv("ACCUWEATHER_API_KEY", "")


def _agent_debug_log(
    hypothesis_id: str,
    location: str,
    message: str,
    data: Mapping[str, Any],
) -> None:
    """Emit structured debug instrumentation to the main logger.

    This is disabled by default to avoid triggering Streamlit file-watcher reruns
    on Windows/OneDrive deployments. Enable via `HRV_AGENT_DEBUG_LOG=1` or the
    Developer Tools debug toggle.
    """

    enabled = False
    if os.environ.get("HRV_AGENT_DEBUG_LOG", "").strip() == "1":
        enabled = True
    else:
        try:
            enabled = bool(
                st.session_state.get("_debug_mode_checkbox", False)
                or st.session_state.get("_debug_mode_enabled", False)
            )
        except Exception:
            enabled = False

    if not enabled:
        return

    payload = {
        "sessionId": "debug-session",
        "runId": "pre-fix",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    try:
        _LOGGER.debug("agent_debug_event=%s", json.dumps(payload, default=str))
    except Exception:
        # Never crash the UI due to debug instrumentation.
        return


@lru_cache(maxsize=1)
def _load_text_file(path: Path) -> str:
    """Load text content from a file with caching and error logging."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover - defensive logging
        log_exception(_LOGGER, f"Failed to read text file: {path}", exc)
        return ""


@lru_cache(maxsize=1)
def _load_lit_review_references() -> str:
    """Return the references section from docs/lit_review.md (cached)."""
    lit_review_path = Path(__file__).resolve().parents[1] / "docs" / "lit_review.md"
    content = _load_text_file(lit_review_path)
    if not content:
        return ""
    parts = content.split("## References", maxsplit=1)
    if len(parts) == 2:
        return parts[1].strip()
    return content

# Windows console safety to mitigate Colorama/Click re-entrancy during shutdown
if os.name == "nt":
    try:
        # Disable colored console to avoid nested writes on shutdown
        os.environ.setdefault("CLICOLOR", "0")
        os.environ.setdefault("NO_COLOR", "1")
        import colorama  # type: ignore

        colorama.just_fix_windows_console()
    except Exception:
        pass


try:
    from spaceweatherlive_client import fetch_spaceweatherlive_snapshot
except ImportError:
    from .spaceweatherlive_client import fetch_spaceweatherlive_snapshot  # type: ignore

try:
    from spaceweather_openai_fallback import extract_spaceweather_with_openai
except ImportError:
    from .spaceweather_openai_fallback import (
        extract_spaceweather_with_openai,
    )  # type: ignore

# Fatigue Calculator Integration (SAFTE model)
try:
    from fatigue_integration import (
        UserProfile as FatigueUserProfile,
        SleepScheduleInput,
        WorkScheduleInput,
        FatigueAnalysisResult,
        run_integrated_fatigue_analysis,
        run_garmin_fatigue_prediction,
        run_assessment_fatigue_prediction,
        build_fatigue_dataframe,
        compute_fatigue_analysis,
        compute_risk_assessment,
        generate_recommendations,
        enhanced_circadian_process,
    )
    FATIGUE_AVAILABLE = True
except ImportError:
    FATIGUE_AVAILABLE = False

# FRMS / USAF crew rest helpers (used in SAFTE tab)
try:
    from frms import (
        FRMSThresholds,
        FRMSExposureMetrics,
        FRMSRiskClassification,
        FRMSAlert,
        USAFCrewRestAssessment,
        USAFCrewRestPolicy,
        assess_usaf_crew_rest,
        classify_frms_risk,
        compute_frms_alerts,
        compute_duty_mask,
        compute_frms_exposure_metrics,
        compute_wocl_mask,
    )
    FRMS_AVAILABLE = True
except ImportError:
    FRMS_AVAILABLE = False

# Mission-level FRMS v2 helpers (crew risk board)
try:
    from frms_v2 import (
        CrewMemberFRMS,
        build_crew_risk_board,
        build_decision_log_entry,
        crew_risk_board_to_payload,
    )
    FRMS_V2_AVAILABLE = True
except ImportError:
    FRMS_V2_AVAILABLE = False

# Real-time HRV and Biofeedback
try:
    from realtime_hrv import (
        RealtimeHRVEngine,
        BiofeedbackSession,
        PacedBreathingGuide,
        SimulatedHRGenerator,
        CoherenceLevel,
        SessionState,
    )
    REALTIME_HRV_AVAILABLE = True
except ImportError:
    REALTIME_HRV_AVAILABLE = False

# Wearable Data Fusion
try:
    from wearable_fusion import (
        WearableDataFusion,
        WearablePlatform,
        SignalSource,
        QualityLevel,
        assess_signal_quality,
        import_oura_data,
        import_whoop_data,
        import_apple_health_data,
        import_fitbit_data,
    )
    WEARABLE_FUSION_AVAILABLE = True
except ImportError:
    WEARABLE_FUSION_AVAILABLE = False

# ActiGraph GT3X/GT3X+ Accelerometer Import
try:
    from actigraph_import import (
        ActigraphData,
        GT3XMetadata,
        import_actigraph_data,
        read_gt3x_file,
        read_agd_file,
        read_actigraph_csv,
        compute_activity_counts,
        classify_activity_intensity,
        classify_sleep_wake,
        extract_sleep_periods,
        synchronize_with_hrv,
        check_actigraph_data_quality,
    )
    ACTIGRAPH_AVAILABLE = True
except ImportError:
    ACTIGRAPH_AVAILABLE = False

# Compumedics Somfit/Somfit Pro Sleep Study Import
try:
    from somfit_import import (
        SomfitData,
        SomfitMetadata,
        SleepStaging,
        RespiratoryEvents,
        import_somfit_data,
        read_edf_file,
        read_profusion_xml,
        read_somfit_csv,
        extract_rr_from_hr,
        extract_rr_from_ecg,
        extract_sleep_hrv_windows,
        get_stage_specific_hrv,
        check_somfit_data_quality,
    )
    SOMFIT_AVAILABLE = True
except ImportError:
    SOMFIT_AVAILABLE = False


def setup_console_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Configure an application logger with both console and file output.
    
    Writes to:
    - Console (stderr) for real-time feedback
    - logs/app.log for persistent debugging
    - logs/errors.log for error-only tracking
    
    This function is idempotent across Streamlit reruns: it clears
    existing handlers on the application logger to avoid duplicate
    messages.

    Parameters
    ----------
    level : int
            Logging level to apply (e.g., logging.INFO, logging.DEBUG).

    Returns
    -------
    logging.Logger
            Configured logger instance for the application.

    Raises
    ------
    TypeError
            If 'level' is not an int logging level.
    """
    if not isinstance(level, int):
        raise TypeError("level must be an int logging level")
    
    # Initialize centralized file logging (idempotent)
    try:
        from logging_config import setup_logging
        setup_logging(log_level_console=level)
    except ImportError:
        pass  # Fall back to console-only if logging_config unavailable
    
    app_logger = logging.getLogger("hrv_app")
    app_logger.propagate = True  # Allow logs to reach root handlers (file)
    
    # Clear existing handlers to prevent duplicates after Streamlit reruns
    for handler in list(app_logger.handlers):
        app_logger.removeHandler(handler)

    # Console handler for app-specific logs
    stream_handler = logging.StreamHandler(stream=sys.stderr)
    stream_handler.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    stream_handler.setFormatter(formatter)

    app_logger.addHandler(stream_handler)
    app_logger.setLevel(level)

    # Route Python warnings to logging so they appear in the console too
    logging.captureWarnings(True)

    return app_logger


_FATIGUE_WIDGET_STATE_KEY = "fatigue_widget_defaults"
_FATIGUE_WIDGET_USER_KEY = "fatigue_widget_user_id"
_DEFAULT_FATIGUE_WIDGET_STATE: Dict[str, Any] = {
    "fatigue_age": 30,
    "fatigue_sex": "other",
    "fatigue_chronotype": 0.0,
    "fatigue_sleep_quality": 0.8,
    "fatigue_sleep_duration": 7.0,
    "fatigue_bedtime": 23,
    "fatigue_waketime": 7,
    "fatigue_sleep_debt": 0.0,
    "fatigue_has_work": True,
    "fatigue_work_start": 9,
    "fatigue_work_end": 17,
    "fatigue_include_weekends": False,
    "fatigue_cognitive_load": 1,
    "fatigue_days": 3,
    "fatigue_model": "Advanced SAFTE",
}
_FATIGUE_SETTING_KEYS: Tuple[str, ...] = tuple(_DEFAULT_FATIGUE_WIDGET_STATE.keys())


def _derive_fatigue_widget_state(user_context: Dict[str, Any]) -> Dict[str, Any]:
    """Derive fatigue widget defaults from the active user context."""
    state = dict(_DEFAULT_FATIGUE_WIDGET_STATE)
    if not user_context.get("has_user"):
        return state

    # Prefer explicit per-user fatigue profile defaults when present.
    user_id = user_context.get("user_id")
    if isinstance(user_id, str) and user_id:
        prof = _cached_fatigue_profile_settings(user_id)
    else:
        prof = {}
    if prof:
        try:
            dur = float(prof.get("typical_sleep_duration_hours", state["fatigue_sleep_duration"]))
            if np.isfinite(dur):
                state["fatigue_sleep_duration"] = float(max(4.0, min(10.0, round(dur, 1))))
        except Exception:
            pass
        try:
            q = float(prof.get("typical_sleep_quality", state["fatigue_sleep_quality"]))
            if np.isfinite(q):
                state["fatigue_sleep_quality"] = float(max(0.0, min(1.0, round(q, 2))))
        except Exception:
            pass
        for key, src in (
            ("fatigue_bedtime", "typical_bedtime_hour"),
            ("fatigue_waketime", "typical_waketime_hour"),
            ("fatigue_work_start", "duty_start_hour"),
            ("fatigue_work_end", "duty_end_hour"),
        ):
            try:
                h = int(prof.get(src, state[key]))
                state[key] = int(max(0, min(23, h)))
            except Exception:
                pass
        state["fatigue_include_weekends"] = bool(prof.get("include_weekends", False))

    age = user_context.get("age_years")
    if isinstance(age, (int, float)):
        state["fatigue_age"] = int(max(16, min(90, round(age))))

    sex = (user_context.get("sex") or "other").lower()
    state["fatigue_sex"] = sex if sex in {"male", "female", "other"} else "other"

    chronotype = float(user_context.get("chronotype_offset") or 0.0)
    state["fatigue_chronotype"] = float(max(-2.5, min(2.5, chronotype)))

    medical_record = user_context.get("medical_record") or {}
    sleep_hours = medical_record.get("sleep_hours")
    if isinstance(sleep_hours, (int, float)):
        state["fatigue_sleep_duration"] = float(
            max(4.0, min(10.0, round(float(sleep_hours), 1)))
        )

    stress = medical_record.get("confinement_stress")
    if isinstance(stress, (int, float)):
        state["fatigue_sleep_quality"] = float(
            max(0.4, min(0.95, 1.0 - (float(stress) - 1.0) * 0.06))
        )

    state["fatigue_sleep_debt"] = float(
        max(0.0, round(7.5 - state["fatigue_sleep_duration"], 1))
    )

    # Approximate bed/wake windows from chronotype and sleep duration
    bedtime = 23
    if chronotype > 0.75:
        bedtime = 1
    elif chronotype < -0.75:
        bedtime = 21
    state["fatigue_bedtime"] = int(bedtime % 24)
    state["fatigue_waketime"] = int(
        (state["fatigue_bedtime"] + round(state["fatigue_sleep_duration"])) % 24
    )

    occupation = (user_context.get("occupation") or "").lower()
    crew_role = (medical_record.get("crew_role") or "").lower()
    has_work = bool(occupation or crew_role)
    state["fatigue_has_work"] = has_work

    work_start, work_end = 9, 17
    if any(tag in occupation for tag in ["night", "shift"]):
        work_start, work_end = 20, 6
    elif "pilot" in crew_role or "commander" in crew_role:
        work_start, work_end = 8, 16
    elif "flight surgeon" in crew_role:
        work_start, work_end = 10, 20
    state["fatigue_work_start"] = int(max(0, min(23, work_start)))
    state["fatigue_work_end"] = int(max(0, min(23, work_end)))

    behavioral_flags = medical_record.get("behavioral_flags") or []
    acute_symptoms = medical_record.get("acute_symptoms") or []
    cognitive_load = 1
    if "Cognitive slowing" in behavioral_flags:
        cognitive_load = 2
    if "Sleep disruption" in acute_symptoms:
        cognitive_load = max(cognitive_load, 2)
    if "Restricted" in str(medical_record.get("eva_status", "")):
        cognitive_load = max(cognitive_load, 3)
    state["fatigue_cognitive_load"] = int(min(3, cognitive_load))

    mission_profile = medical_record.get("mission_profile")
    if mission_profile == "CHAPEA-378":
        state["fatigue_days"] = 14
        state["fatigue_model"] = "Classic SAFTE"
    elif mission_profile == "MARS-ANALOG-45":
        state["fatigue_days"] = 10
    elif mission_profile == "GATEWAY-30":
        state["fatigue_days"] = 7
    elif mission_profile == "LUNAR-22":
        state["fatigue_days"] = 5

    return state


def _sync_fatigue_widgets(
    user_context: Dict[str, Any], *, force: bool = False
) -> Dict[str, Any]:
    """
    Ensure fatigue widgets mirror the active user context.

    Returns the state dictionary that should be considered the latest defaults.
    """
    target_user = user_context.get("user_id") if user_context.get("has_user") else None
    stored_user = st.session_state.get(_FATIGUE_WIDGET_USER_KEY)
    if not force and stored_user == target_user:
        return st.session_state.get(
            _FATIGUE_WIDGET_STATE_KEY, dict(_DEFAULT_FATIGUE_WIDGET_STATE)
        )

    state = _derive_fatigue_widget_state(user_context)
    for key, value in state.items():
        st.session_state[key] = value
    st.session_state[_FATIGUE_WIDGET_STATE_KEY] = state
    st.session_state[_FATIGUE_WIDGET_USER_KEY] = target_user
    return state


SWPC_BASE_URL = "https://services.swpc.noaa.gov/json/"
# Fast-fail SWPC fetches to avoid UI stalls on slow networks.
SWPC_TIMEOUT = 4
SWPC_EXTRA_DATASETS = {
    "Solar Regions": "solar_regions.json",
    "Solar Flare Probabilities": "solar_probabilities.json",
    "Electron Fluence Forecast": "electron_fluence_forecast.json",
}

_HTTP_SESSION_LOCAL = threading.local()


def _get_http_session() -> requests.Session:
    """Return a thread-local HTTP session configured for connection pooling.

    Streamlit reruns can trigger many SWPC/DONKI requests (and NOAA Space can
    fan out to 10+ feeds). Pooling reduces repeated TLS handshakes and improves
    responsiveness while keeping session state isolated per thread.
    """

    session = getattr(_HTTP_SESSION_LOCAL, "session", None)
    if session is None:
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=16,
            pool_maxsize=16,
            max_retries=0,
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        _HTTP_SESSION_LOCAL.session = session
    return session
_KP_SUFFIX_OFFSETS: Dict[str, float] = {
    "-": -1.0 / 3.0, "o": 0.0, "+": 1.0 / 3.0}

_RR_FILENAME_TS_PATTERN = re.compile(
    r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})[ _T-]"
    r"(?P<hour>\d{2})[-_:](?P<minute>\d{2})[-_:](?P<second>\d{2})"
)
_RR_FILENAME_TZ = timezone(timedelta(hours=-5))


def _infer_recording_start(name: str) -> Tuple[pd.Timestamp, bool]:
    """
    Infer the start timestamp of an RR recording from its filename.

    The expected filename format is `YYYY-MM-DD HH-MM-SS.ext`, where the
    separators between time components may be `-` or `:` and the separator
    between date and time may be a space, underscore, hyphen, or `T`. Filenames
    are interpreted as GMT-5 (UTC-5) and converted to UTC for downstream work.

    Returns
    -------
    Tuple[pd.Timestamp, bool]
        The inferred timezone-aware UTC timestamp and a flag indicating whether
        the value was parsed from the filename (True) or generated as a fallback
        (False).
    """

    fallback = pd.Timestamp.now(tz=timezone.utc).normalize()
    stem = Path(name).stem
    match = _RR_FILENAME_TS_PATTERN.search(stem)
    if not match:
        return fallback, False
    try:
        start_ts = pd.Timestamp(
            year=int(match.group("year")),
            month=int(match.group("month")),
            day=int(match.group("day")),
            hour=int(match.group("hour")),
            minute=int(match.group("minute")),
            second=int(match.group("second")),
            tz=_RR_FILENAME_TZ,
        )
    except (TypeError, ValueError):
        return fallback, False
    return start_ts.tz_convert(timezone.utc), True


def _kp_to_numeric(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and np.isfinite(value):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    suffix = text[-1].lower()
    base_text = text[:-
                     1] if (suffix in _KP_SUFFIX_OFFSETS and text[:-
                                                                  1]) else text
    try:
        base = float(base_text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return None
    offset = _KP_SUFFIX_OFFSETS.get(suffix, 0.0)
    return float(round(base + offset, 2))


DONKI_API_BASE = "https://api.nasa.gov/DONKI"
DONKI_TIMEOUT = 20
DONKI_ENDPOINTS: Dict[str, Dict[str, Any]] = {
    "FLR": {
        "path": "FLR",
        "default_days": 30,
        "default_params": {},
        "time_columns": ["beginTime", "peakTime", "endTime"],
        "title": "Flare count",
    },
    "CME": {
        "path": "CME",
        "default_days": 30,
        "default_params": {},
        "time_columns": ["startTime", "time21_5"],
        "title": "CME count",
    },
    "CMEAnalysis": {
        "path": "CMEAnalysis",
        "default_days": 30,
        "default_params": {
            "mostAccurateOnly": "true",
            "completeEntryOnly": "true",
            "speed": "0",
            "halfAngle": "0",
            "catalog": "ALL",
            "keyword": "NONE",
        },
        "time_columns": ["time21_5", "time18_4"],
        "title": "CME analysis entries",
    },
    "GST": {
        "path": "GST",
        "default_days": 30,
        "default_params": {},
        "time_columns": ["startTime", "allKpIndex[].observedTime"],
        "title": "Geomagnetic storms",
    },
    "IPS": {
        "path": "IPS",
        "default_days": 30,
        "default_params": {"location": "ALL", "catalog": "ALL"},
        "time_columns": ["eventTime", "shockArrivalTime", "time"],
        "title": "Interplanetary shocks",
    },
    "HSS": {
        "path": "HSS",
        "default_days": 30,
        "default_params": {},
        "time_columns": ["startTime", "linkTime"],
        "title": "High speed streams",
    },
    "RBE": {
        "path": "RBE",
        "default_days": 30,
        "default_params": {},
        "time_columns": ["eventStartTime", "eventEndTime"],
        "title": "Radiation belt enhancements",
    },
    "SEP": {
        "path": "SEP",
        "default_days": 30,
        "default_params": {},
        "time_columns": ["eventTime", "startTime"],
        "title": "SEP events",
    },
    "MPC": {
        "path": "MPC",
        "default_days": 30,
        "default_params": {},
        "time_columns": ["eventTime"],
        "title": "Magnetopause crossings",
    },
    "WSAEnlilSimulations": {
        "path": "WSAEnlilSimulations",
        "default_days": 7,
        "default_params": {},
        "time_columns": ["modelCompletionTime"],
        "title": "WSA+Enlil simulations",
    },
    "notifications": {
        "path": "notifications",
        "default_days": 7,
        "default_params": {"type": "all"},
        "time_columns": ["messageIssueTime"],
        "title": "Notifications",
    },
}
DONKI_LABEL_TO_CODE: Dict[str, str] = {
    "FLR (Solar Flares)": "FLR",
    "CME": "CME",
    "GST (Geomagnetic Storm)": "GST",
    "IPS": "IPS",
    "HSS": "HSS",
    "RBE": "RBE",
    "SEP": "SEP",
}

CACHE_BASE_DIR = Path(__file__).resolve().parent / "data_cache"
SPACE_WEATHER_CACHE_DIR = CACHE_BASE_DIR / "space_weather"
DONKI_CACHE_DIR = CACHE_BASE_DIR / "donki"
SPACE_WEATHER_CACHE_TTL = pd.Timedelta(hours=6)
DONKI_CACHE_TTL = pd.Timedelta(hours=24)


def _ensure_cache_dir(path: Path) -> None:
    """
    Create the cache directory if it does not exist.

    Parameters
    ----------
    path : Path
            Target directory path.
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # pragma: no cover - defensive
        logging.getLogger("hrv_app").warning(
            "Unable to ensure cache directory %s: %s", path, exc, exc_info=True
        )


def _clear_cache_dir(cache_dir: Path, *, max_files: int = 5000) -> Tuple[int, Optional[str]]:
    """Delete cached files under `cache_dir` (keeps the directory).

    This is intentionally bounded to avoid accidental large deletions.

    Returns:
        (deleted_file_count, error_message_or_None)
    """
    if max_files <= 0:
        return 0, "Invalid max_files bound."
    if not cache_dir.exists():
        return 0, None
    deleted = 0
    try:
        # Delete files first (bounded).
        for entry in cache_dir.rglob("*"):
            if entry.is_file():
                try:
                    if deleted >= max_files:
                        return (
                            deleted,
                            f"Refusing to delete more than {max_files} files.",
                        )
                    entry.unlink()
                    deleted += 1
                except OSError as exc:
                    return deleted, f"Failed to delete {entry.name}: {exc}"
        # Best-effort: remove empty subdirectories (reverse depth order).
        for entry in sorted(cache_dir.rglob("*"), reverse=True):
            if entry.is_dir():
                try:
                    entry.rmdir()
                except OSError:
                    pass
        return deleted, None
    except OSError as exc:
        return deleted, f"Cache clear failed: {exc}"


def _read_dataframe_cache(
    cache_path: Path, *, max_age: Optional[pd.Timedelta]
) -> Optional[pd.DataFrame]:
    """
    Load a cached pandas DataFrame saved in JSON format.

    Parameters
    ----------
    cache_path : Path
            Path to the JSON cache file.
    max_age : Optional[pd.Timedelta]
            Maximum allowed age for the cached data. If None, no age check is performed.

    Returns
    -------
    Optional[pd.DataFrame]
            Loaded DataFrame if the cache exists, is valid, and not expired; otherwise None.
    """
    if not cache_path.exists():
        return None
    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None

    stored_at_raw = payload.get("stored_at")
    stored_at = pd.to_datetime(stored_at_raw, utc=True, errors="coerce")
    if max_age is not None:
        if pd.isna(stored_at):
            return None
        if stored_at + max_age < pd.Timestamp.now(tz=timezone.utc):
            return None

    data_json = payload.get("data")
    if not isinstance(data_json, str):
        return None
    try:
        df = pd.read_json(io.StringIO(data_json), orient="table", convert_dates=True)
    except ValueError:
        return None
    return df


def _write_dataframe_cache(cache_path: Path, df: pd.DataFrame) -> None:
    """
    Persist a pandas DataFrame to disk using a JSON payload (orient='table').

    Parameters
    ----------
    cache_path : Path
            Target cache file path.
    df : pd.DataFrame
            DataFrame to serialize. Empty frames are allowed.
    """
    payload = {
        "stored_at": pd.Timestamp.now(tz=timezone.utc).isoformat(),
        "data": df.to_json(orient="table", date_format="iso"),
    }
    try:
        _ensure_cache_dir(cache_path.parent)
        with cache_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle)
    except OSError as exc:  # pragma: no cover - defensive
        logging.getLogger("hrv_app").warning(
            "Failed to write cache %s: %s", cache_path, exc, exc_info=True
        )


def _safe_to_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convert DataFrame columns to numeric where possible without deprecation warnings.
    
    Replaces df.apply(pd.to_numeric, errors='ignore') which is deprecated.
    """
    if df.empty:
        return df
    
    result = df.copy()
    for col in result.columns:
        # Skip already numeric columns and datetime columns
        if result[col].dtype.kind in "iufcmM":  # int, uint, float, complex, timedelta, datetime
            continue
        # Try to convert object columns to numeric
        if result[col].dtype == object:
            try:
                converted = pd.to_numeric(result[col], errors="coerce")
                # Only keep conversion if it didn't produce all NaNs
                if not converted.isna().all():
                    result[col] = converted
            except (ValueError, TypeError):
                pass
    return result


@st.cache_data(ttl=300, max_entries=32, show_spinner=False)
def _fetch_swpc_dataset(path: str) -> pd.DataFrame:
    url = f"{SWPC_BASE_URL}{path}"
    response = _get_http_session().get(url, timeout=SWPC_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        records = (payload.get("data") or payload.get(
            "series") or payload.get("observations"))
        if records is None:
            records = [payload]
        elif not isinstance(records, list):
            records = [records]
    elif isinstance(payload, list):
        records = payload
    else:
        records = []
    df = pd.json_normalize(records)
    if not df.empty:
        for col in df.columns:
            if df[col].dtype == object:
                lowered = col.lower()
                if "time" in lowered or "date" in lowered or "tag" in lowered:
                    df[col] = pd.to_datetime(
                        df[col], errors="coerce", utc=True)
        df = _safe_to_numeric_columns(df)
    return df


def get_swpc_kp_index(days: int = 14) -> pd.DataFrame:
    if days is None or int(days) <= 0:
        raise ValueError("days must be a positive integer")
    cache_file = SPACE_WEATHER_CACHE_DIR / f"kp_index_{int(days)}.json"
    cached_df = _read_dataframe_cache(
        cache_file, max_age=SPACE_WEATHER_CACHE_TTL)
    if cached_df is not None:
        return cached_df
    try:
        url = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
        response = _get_http_session().get(url, timeout=SWPC_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        if not payload:
            return pd.DataFrame()
        if isinstance(payload, list) and payload and isinstance(payload[0], list):
            header = payload[0]
            rows = payload[1:]
            df = pd.DataFrame(rows, columns=header)
        else:
            df = pd.json_normalize(payload)
        if "time_tag" in df.columns:
            df["time_tag"] = pd.to_datetime(
                df["time_tag"], errors="coerce", utc=True)
            if days is not None:
                cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=int(days))
                df = df[df["time_tag"] >= cutoff]
        if "kp_index" in df.columns:
            df["kp_index"] = df["kp_index"].apply(_kp_to_numeric)
            df["kp_index"] = pd.to_numeric(df["kp_index"], errors="coerce")
        df = df.sort_values("time_tag") if "time_tag" in df.columns else df
        _write_dataframe_cache(cache_file, df)
        return df
    except (requests.RequestException, ValueError) as exc:
        stale_df = _read_dataframe_cache(cache_file, max_age=None)
        if stale_df is not None:
            log_exception(
                _LOGGER,
                "Failed to refresh SWPC Kp index; using last cached copy",
                exc,
            )
            return stale_df
        log_exception(_LOGGER, "Failed to refresh SWPC Kp index", exc)
        raise


def get_swpc_solar_radio_flux() -> pd.DataFrame:
    cache_file = SPACE_WEATHER_CACHE_DIR / "solar_radio_flux.json"
    cached_df = _read_dataframe_cache(
        cache_file, max_age=SPACE_WEATHER_CACHE_TTL)
    if cached_df is not None:
        return cached_df
    candidates = [
        "f107_cm_flux.json",
        "solar_radio_flux.json",
        "predicted_f107cm_flux.json",
    ]
    try:
        df = pd.DataFrame()
        for path in candidates:
            try:
                df_candidate = _fetch_swpc_dataset(path)
            except requests.HTTPError as exc:
                status = getattr(exc.response, "status_code", None)
                if status == 404:
                    continue
                raise
            if not df_candidate.empty:
                df = df_candidate
                break
        if df.empty:
            return df
        # Ensure a unified time column name (robust to tz-aware dtypes)
        time_cols: List[str] = []
        dtype_summary = {col: str(df[col].dtype) for col in df.columns}
        for col in df.columns:
            try:
                if is_datetime64_any_dtype(df[col]):
                    time_cols.append(col)
            except TypeError as exc:
                # Some pandas/numpy builds raise on tz-aware extension dtypes; log and ignore
                #region agent log
                _agent_debug_log(
                    "H1",
                    "app.py:get_swpc_solar_radio_flux",
                    "time_col_detection_type_error",
                    {
                        "column": col,
                        "dtype": str(df[col].dtype),
                        "error": str(exc),
                    },
                )
                #endregion
                continue
        main_time: Optional[str] = None
        if time_cols:
            main_time = time_cols[0]
            df = df.dropna(subset=[main_time]).sort_values(main_time)
            if "time_tag" not in df.columns:
                df = df.rename(columns={main_time: "time_tag"})
        else:
            df["time_tag"] = pd.to_datetime(
                df.iloc[:, 0], errors="coerce", utc=True)
            df = df.dropna(subset=["time_tag"]).sort_values("time_tag")
        #region agent log
        _agent_debug_log(
            "H1",
            "app.py:get_swpc_solar_radio_flux",
            "time_columns_processed",
            {
                "time_cols": time_cols,
                "main_time": main_time,
                "dtype_summary": dtype_summary,
                "row_count": int(df.shape[0]),
                "col_count": int(df.shape[1]),
            },
        )
        #endregion
        # Identify numeric flux columns
        numeric_cols = [col for col in df.columns if df[col].dtype.kind in "fcid"]
        flux_candidates = [
            col
            for col in numeric_cols
            if any(
                keyword in col.lower()
                for keyword in ("flux", "value", "observed", "adjusted")
            )
        ]
        if flux_candidates:
            for col in flux_candidates:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        _write_dataframe_cache(cache_file, df)
        return df
    except (requests.RequestException, ValueError) as exc:
        stale_df = _read_dataframe_cache(cache_file, max_age=None)
        if stale_df is not None:
            log_exception(
                _LOGGER,
                "Failed to refresh solar radio flux; using last cached copy",
                exc,
            )
            return stale_df
        log_exception(_LOGGER, "Failed to refresh solar radio flux", exc)
        raise


def get_swpc_solar_probabilities() -> pd.DataFrame:
    df = _fetch_swpc_dataset("solar_probabilities.json")
    if "time_tag" in df.columns:
        df = df.dropna(subset=["time_tag"])
        df = df.sort_values("time_tag")
    return df


@st.cache_data(ttl=600, max_entries=64, show_spinner=False)
def _cached_comprehensive(
        rr: np.ndarray, include_advanced: bool) -> Dict[str, Any]:
    start_time = time.perf_counter()
    result = compute_comprehensive_hrv(
        rr, include_advanced=include_advanced)
    duration_ms = (time.perf_counter() - start_time) * 1000.0
    #region agent log
    _agent_debug_log(
        "H4",
        "app.py:_cached_comprehensive",
        "hrv_cached_compute",
        {
            "rr_count": int(len(rr)),
            "include_advanced": bool(include_advanced),
            "duration_ms": duration_ms,
        },
    )
    #endregion
    return result


@st.cache_data(ttl=600, max_entries=128, show_spinner=False)
def _cached_psd(rr: np.ndarray, method: str) -> Tuple[np.ndarray, np.ndarray]:
    return psd_curve(rr, sampling_rate=4.0, method=method)


@st.cache_data(ttl=600, max_entries=32, show_spinner=False)
def _cached_windowed(
    df: pd.DataFrame,
    rr_col: str,
    window: str,
    step: str,
    min_rr_count: int,
    max_windows: int,
    include_advanced: bool,
) -> pd.DataFrame:
    try:
        return compute_windowed_hrv(
            df,
            rr_col=rr_col,
            window=window,
            step=step,
            min_rr_count=min_rr_count,
            max_windows=max_windows,
            include_advanced=include_advanced,
        )
    except TypeError:
        # Backward-compat fallback if the imported function does not accept
        # include_advanced
        return compute_windowed_hrv(
            df,
            rr_col=rr_col,
            window=window,
            step=step,
            min_rr_count=min_rr_count,
            max_windows=max_windows,
        )


@st.cache_data(ttl=600, max_entries=64, show_spinner=False)
def _cached_spectrogram(
        rr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    return spectrogram_rr(rr, sampling_rate=4.0)


@st.cache_data(ttl=30, max_entries=128, show_spinner=False)
def _cached_pns_history(
    user_id: str,
    *,
    limit: int = 365,
) -> pd.DataFrame:
    """Load recent parasympathetic index history for readiness scoring.

    Returns a small DataFrame containing the fields needed for readiness UI.
    """
    if not user_id:
        return pd.DataFrame()
    db = get_database()
    # Restrict columns to keep the query + cache payload lightweight.
    return db.get_hrv_dataframe(
        user_id,
        limit=limit,
        include_rr=False,
        columns=(
            "measurement_id",
            "measurement_date",
            "source_file",
            "file_hash",
            "parasympathetic_index",
            "created_at",
        ),
    )


@st.cache_data(ttl=60, max_entries=256, show_spinner=False)
def _cached_rr_from_path(path: str, mtime_ns: int) -> np.ndarray:
    """Load RR intervals from a stored path with cache invalidation.

    Args:
        path: Absolute path to a text/CSV file containing one RR value per line.
        mtime_ns: File modification time in nanoseconds (cache-busting).
    """
    _ = mtime_ns  # used only to invalidate the cache when the file changes
    if not path:
        return np.array([], dtype=float)
    p = Path(path)
    if not p.exists():
        return np.array([], dtype=float)
    rr = np.loadtxt(p, dtype=float)
    rr = rr[(rr >= 300) & (rr <= 2000)]
    return rr


@st.cache_data(ttl=60, max_entries=128, show_spinner=False)
def _cached_latest_garmin_daily(user_id: str) -> Dict[str, Any]:
    """Return the latest Garmin daily metrics row for a user (if present)."""
    if not user_id:
        return {}
    db = get_database()
    if not hasattr(db, "get_garmin_daily_dataframe"):
        return {}
    try:
        df = db.get_garmin_daily_dataframe(user_id, limit=1)  # type: ignore[attr-defined]
    except Exception:
        return {}
    if df is None or df.empty:
        return {}
    row = df.iloc[0].to_dict()
    metric_date = row.get("metric_date")
    if isinstance(metric_date, pd.Timestamp):
        row["metric_date"] = metric_date.date().isoformat()
    return row


@st.cache_data(ttl=60, max_entries=128, show_spinner=False)
def _cached_fatigue_profile_settings(user_id: str) -> Dict[str, Any]:
    """Return stored per-user SAFTE/FRMS default inputs (if present)."""
    if not user_id:
        return {}
    db = get_database()
    if not hasattr(db, "get_fatigue_profile_settings"):
        return {}
    try:
        prof = db.get_fatigue_profile_settings(user_id)  # type: ignore[attr-defined]
    except Exception:
        return {}
    if prof is None:
        return {}
    try:
        return dict(prof.to_dict())
    except Exception:
        # Defensive fallback in case dataclass changes.
        return {
            "user_id": getattr(prof, "user_id", user_id),
            "typical_sleep_duration_hours": getattr(prof, "typical_sleep_duration_hours", 7.5),
            "typical_sleep_quality": getattr(prof, "typical_sleep_quality", 0.8),
            "typical_bedtime_hour": getattr(prof, "typical_bedtime_hour", 23),
            "typical_waketime_hour": getattr(prof, "typical_waketime_hour", 7),
            "duty_start_hour": getattr(prof, "duty_start_hour", 9),
            "duty_end_hour": getattr(prof, "duty_end_hour", 17),
            "include_weekends": getattr(prof, "include_weekends", False),
            "updated_at": getattr(prof, "updated_at", None),
        }


SPACE_WEATHER_MAX_DAYS = 30


def _space_weather_state() -> Dict[str, Any]:
    state = st.session_state.setdefault(
        "space_weather_state",
        {
            "loaded": False,
            "kp_df": pd.DataFrame(),
            "kp_error": "",
            "flux_df": pd.DataFrame(),
            "flux_error": "",
            "last_updated": None,
            "swl_loaded": False,
            "swl_cme_df": pd.DataFrame(),
            "swl_snapshots": [],
            "swl_last_updated": None,
            "swl_cme_daily": pd.DataFrame(),
            "swl_feature_matrix": pd.DataFrame(),
            "auto_loading": False,
            "auto_attempted": False,
        },
    )
    return state


def _noaa_space_state() -> Dict[str, Any]:
    """
    Persist NOAA datasets for the dedicated NOAA Space tab.
    """

    state = st.session_state.setdefault(
        "noaa_space_state",
        {
            "bundles": {},
            "errors": {},
            "last_updated": None,
            "loading": False,
            "auto_loading": False,
            "auto_attempted": False,
            "correlations": {},
            "corr_params": {},
            "global_corr": pd.DataFrame(),
            "global_corr_labels": {},
        },
    )
    return state


NOAA_CORE_KEYS: tuple[str, ...] = (
    "planetary_k_index_3h",
    "f107_flux",
    "solar_wind_wind",
    "solar_wind_mag",
    "goes_xray_flux",
    "goes_integral_protons",
    "geospace_dst",
)

# Fast, minimal keys for instant "today" context panels (cache-first, on-demand refresh).
NOAA_FAST_KEYS: tuple[str, ...] = (
    "planetary_k_index_3h",
    "f107_flux",
)


def _load_noaa_space_datasets(
    state: Dict[str, Any],
    *,
    keys: Optional[Sequence[str]] = None,
    use_cache: bool = True,
    allow_stale_cache: bool = False,
) -> None:
    """
    Populate the NOAA space datasets in session state.
    """

    state["loading"] = True
    try:
        # Full scope can be expensive; keep concurrency conservative to
        # avoid Streamlit WebSocket disconnects on Windows/OneDrive setups.
        max_workers = 4 if keys is not None else 2
        bundles, errors = load_noaa_space_data(
            keys=keys,
            use_cache=use_cache,
            max_workers=max_workers,
            allow_stale_cache=allow_stale_cache,
        )
    except requests.RequestException as exc:
        state["bundles"] = {}
        state["errors"] = {"__global__": str(exc)}
        state["last_updated"] = pd.Timestamp.utcnow()
        state["correlations"] = {}
        state["corr_params"] = {}
        state["global_corr"] = pd.DataFrame()
        state["global_corr_labels"] = {}
    else:
        state["bundles"] = bundles
        state["errors"] = errors
        state["last_updated"] = pd.Timestamp.utcnow()
        state["correlations"] = {}
        state["corr_params"] = {}
        state["global_corr"] = pd.DataFrame()
        state["global_corr_labels"] = {}
    finally:
        state["loading"] = False


def _load_noaa_space_cache_only(
    state: Dict[str, Any],
    *,
    keys: Optional[Sequence[str]] = None,
) -> None:
    """Populate NOAA datasets from local cache only (no network).

    This is used to keep the NOAA tab instant: show cached "today" context
    immediately, then let users click to refresh explicitly.
    """
    state["loading"] = True
    try:
        bundles, errors = load_noaa_space_cache(
            keys=list(keys) if keys is not None else None,
            allow_stale_cache=True,
        )
        state["bundles"] = bundles
        state["errors"] = errors
        state["last_updated"] = pd.Timestamp.utcnow()
        state["correlations"] = {}
        state["corr_params"] = {}
        state["global_corr"] = pd.DataFrame()
        state["global_corr_labels"] = {}
    except Exception as exc:  # pragma: no cover - defensive
        log_exception(_LOGGER, "NOAA cache-only load failed", exc)
        state["bundles"] = {}
        state["errors"] = {"__global__": str(exc)}
        state["last_updated"] = pd.Timestamp.utcnow()
        state["correlations"] = {}
        state["corr_params"] = {}
        state["global_corr"] = pd.DataFrame()
        state["global_corr_labels"] = {}
    finally:
        state["loading"] = False


def _load_space_weather_cache_only(state: Dict[str, Any]) -> None:
    """Populate SWPC datasets from local cache only (no network)."""
    # Keep existing errors unless we successfully load something.
    kp_df = pd.DataFrame()
    flux_df = pd.DataFrame()
    try:
        kp_cache = SPACE_WEATHER_CACHE_DIR / f"kp_index_{int(SPACE_WEATHER_MAX_DAYS)}.json"
        flux_cache = SPACE_WEATHER_CACHE_DIR / "solar_radio_flux.json"
        cached_kp = _read_dataframe_cache(kp_cache, max_age=None)
        cached_flux = _read_dataframe_cache(flux_cache, max_age=None)
        if isinstance(cached_kp, pd.DataFrame):
            kp_df = cached_kp
        if isinstance(cached_flux, pd.DataFrame):
            flux_df = cached_flux
    except Exception as exc:  # pragma: no cover - defensive
        log_exception(_LOGGER, "Space weather cache-only load failed", exc)

    if isinstance(kp_df, pd.DataFrame) and not kp_df.empty:
        state["kp_df"] = kp_df
        state["kp_error"] = ""
    if isinstance(flux_df, pd.DataFrame) and not flux_df.empty:
        state["flux_df"] = flux_df
        state["flux_error"] = ""

    state["loaded"] = bool(
        (isinstance(state.get("kp_df"), pd.DataFrame) and not state["kp_df"].empty)
        or (isinstance(state.get("flux_df"), pd.DataFrame) and not state["flux_df"].empty)
    )
    if state["loaded"] and state.get("last_updated") is None:
        state["last_updated"] = pd.Timestamp.utcnow()

def _auto_fetch_space_weather_if_needed(state: Dict[str, Any]) -> None:
    """
    Ensure the basic space weather datasets are available without user clicks.
    
    Respects performance settings - disabled on low-end systems or when
    downloads are disabled to conserve bandwidth/resources.
    """
    # Check if downloads are enabled in performance settings
    if not is_download_enabled("space_weather_live"):
        state["auto_attempted"] = True
        state["download_disabled"] = True
        return

    if state.get("loaded") or state.get("auto_loading") or state.get("auto_attempted"):
        return
    state["auto_loading"] = True
    success = False
    try:
        _fetch_space_weather_datasets(state)
        success = True
    except Exception as exc:  # pragma: no cover - defensive
        log_exception(_LOGGER, "Automatic space weather bootstrap failed", exc)
        # Bounded single retry with short backoff to tolerate transient network issues
        try:
            time.sleep(0.5)
            _fetch_space_weather_datasets(state)
            success = True
        except Exception as retry_exc:  # pragma: no cover - defensive
            log_exception(_LOGGER, "Space weather bootstrap retry failed", retry_exc)
    finally:
        state["auto_loading"] = False
        if success:
            state["auto_attempted"] = True


def _auto_fetch_noaa_space_if_needed(state: Dict[str, Any]) -> None:
    """
    Preload NOAA feeds using cache-first retrieval so the tab is always populated.
    
    Respects performance settings - disabled when NOAA downloads are disabled.
    """
    # Check if NOAA downloads are enabled in performance settings
    if not is_download_enabled("noaa_space"):
        state["auto_attempted"] = True
        state["download_disabled"] = True
        return

    if state.get("bundles") or state.get("loading") or state.get("auto_loading") or state.get("auto_attempted"):
        return
    state["auto_loading"] = True
    success = False
    try:
        _load_noaa_space_datasets(state, use_cache=True)
        success = True
    except Exception as exc:  # pragma: no cover - defensive
        log_exception(_LOGGER, "Automatic NOAA preload failed", exc)
        try:
            time.sleep(0.5)
            _load_noaa_space_datasets(state, use_cache=True)
            success = True
        except Exception as retry_exc:  # pragma: no cover - defensive
            log_exception(_LOGGER, "NOAA preload retry failed", retry_exc)
    finally:
        state["auto_loading"] = False
        if success:
            state["auto_attempted"] = True


# ---------------------------------------------------------------------------
# BACKGROUND SPACE WEATHER FETCH (Non-blocking, 12-hour auto-refresh)
# ---------------------------------------------------------------------------
# These globals hold results from the background thread and allow the main
# UI thread to poll for completion without blocking.
# Auto-refresh interval: 12 hours (43200 seconds)
_BG_FETCH_INTERVAL_SECONDS = 43200  # 12 hours

_bg_fetch_lock = threading.Lock()
_bg_fetch_results: Dict[str, Any] = {
    "space_weather": {"done": False, "error": None, "data": {}, "fetch_time": None},
    "noaa": {"done": False, "error": None, "data": {}, "fetch_time": None},
    "donki": {"done": False, "error": None, "data": {}, "fetch_time": None},
}
_bg_fetch_thread: Optional[threading.Thread] = None


def _bg_fetch_all_space_data() -> None:
    """
    Background thread worker: fetch space weather, NOAA, and DONKI data.

    Results are stored in _bg_fetch_results with lock protection.
    The main UI thread polls these results via _poll_background_fetch().
    """
    global _bg_fetch_results
    fetch_time = time.time()

    # 1. Space Weather (Kp + Flux)
    try:
        kp_df = get_swpc_kp_index(days=SPACE_WEATHER_MAX_DAYS)
        flux_df = get_swpc_solar_radio_flux()
        with _bg_fetch_lock:
            _bg_fetch_results["space_weather"]["data"] = {
                "kp_df": kp_df,
                "flux_df": flux_df,
                "last_updated": pd.Timestamp.utcnow(),
            }
            _bg_fetch_results["space_weather"]["done"] = True
            _bg_fetch_results["space_weather"]["error"] = None
            _bg_fetch_results["space_weather"]["fetch_time"] = fetch_time
            _bg_fetch_results["space_weather"]["_applied"] = False
    except Exception as exc:
        log_exception(_LOGGER, "Background fetch failed: space weather", exc)
        with _bg_fetch_lock:
            _bg_fetch_results["space_weather"]["error"] = str(exc)
            _bg_fetch_results["space_weather"]["done"] = True
            _bg_fetch_results["space_weather"]["fetch_time"] = fetch_time

    # 2. NOAA feeds (Core scope by default to keep UI responsive)
    try:
        # Core feeds are sufficient for most HRV correlations and keep the
        # background thread lightweight (prevents UI/WebSocket disconnects).
        bundles, errors = load_noaa_space_data(
            keys=list(NOAA_CORE_KEYS),
            use_cache=True,
            max_workers=4,
        )
        with _bg_fetch_lock:
            _bg_fetch_results["noaa"]["data"] = {
                "bundles": bundles,
                "errors": errors,
                "last_updated": pd.Timestamp.utcnow(),
            }
            _bg_fetch_results["noaa"]["done"] = True
            _bg_fetch_results["noaa"]["error"] = None
            _bg_fetch_results["noaa"]["fetch_time"] = fetch_time
            _bg_fetch_results["noaa"]["_applied"] = False
    except Exception as exc:
        log_exception(_LOGGER, "Background fetch failed: NOAA feeds", exc)
        with _bg_fetch_lock:
            _bg_fetch_results["noaa"]["error"] = str(exc)
            _bg_fetch_results["noaa"]["done"] = True
            _bg_fetch_results["noaa"]["fetch_time"] = fetch_time

    # 3. DONKI (last 14 days by default; users can expand window manually)
    try:
        end_dt = pd.Timestamp.utcnow()
        start_dt = end_dt - pd.Timedelta(days=14)
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")

        # Use existing DONKI fetch helper; run on a temporary state dict
        donki_tmp_state: Dict[str, Any] = {
            "loaded": False,
            "datasets": {},
            "errors": {},
            "start_date": start_str,
            "end_date": end_str,
            "last_updated": None,
        }
        _fetch_donki_datasets(donki_tmp_state, start_str, end_str, endpoints=None)

        with _bg_fetch_lock:
            _bg_fetch_results["donki"]["data"] = {
                "datasets": donki_tmp_state.get("datasets", {}),
                "errors": donki_tmp_state.get("errors", {}),
                "start_date": donki_tmp_state.get("start_date", start_str),
                "end_date": donki_tmp_state.get("end_date", end_str),
                "last_updated": donki_tmp_state.get("last_updated", pd.Timestamp.utcnow()),
            }
            _bg_fetch_results["donki"]["done"] = True
            _bg_fetch_results["donki"]["error"] = None
            _bg_fetch_results["donki"]["fetch_time"] = fetch_time
            _bg_fetch_results["donki"]["_applied"] = False
    except Exception as exc:
        log_exception(_LOGGER, "Background fetch failed: NASA DONKI", exc)
        with _bg_fetch_lock:
            _bg_fetch_results["donki"]["error"] = str(exc)
            _bg_fetch_results["donki"]["done"] = True
            _bg_fetch_results["donki"]["fetch_time"] = fetch_time


def _is_bg_fetch_stale() -> bool:
    """
    Check if the background fetch data is stale (older than 12 hours).

    Returns True if any data source is stale or never fetched.
    """
    with _bg_fetch_lock:
        fetch_times = {
            key: _bg_fetch_results[key].get("fetch_time")
            for key in ("space_weather", "noaa", "donki")
        }
    return _are_fetch_times_stale(fetch_times)


def _are_fetch_times_stale(fetch_times: Dict[str, Optional[float]]) -> bool:
    """Helper to evaluate staleness without acquiring locks."""
    now = time.time()
    for fetch_time in fetch_times.values():
        if fetch_time is None:
            return True  # Never fetched
        if (now - fetch_time) >= _BG_FETCH_INTERVAL_SECONDS:
            return True  # Stale
    return False


def _reset_bg_fetch_for_refresh() -> None:
    """
    Reset the background fetch state to allow a fresh fetch cycle.

    Call this before starting a new background fetch to ensure data is refreshed.
    """
    with _bg_fetch_lock:
        for key in ("space_weather", "noaa", "donki"):
            _bg_fetch_results[key]["done"] = False
            _bg_fetch_results[key]["_applied"] = False


def _start_background_fetch(force: bool = False) -> bool:
    """
    Spawn a background thread to fetch all space weather data.

    Args:
        force: If True, reset state and start a new fetch even if data exists.

    Returns True if a new thread was started, False if already running or
    data is fresh (unless force=True).
    """
    global _bg_fetch_thread

    with _bg_fetch_lock:
        # Don't start if already running
        if _bg_fetch_thread is not None and _bg_fetch_thread.is_alive():
            return False

        # Snapshot current fetch times to evaluate staleness without re-locking
        fetch_times_snapshot = {
            key: _bg_fetch_results[key].get("fetch_time")
            for key in ("space_weather", "noaa", "donki")
        }

        # If not forcing, check if data is still fresh
        if not force:
            all_done = all(
                _bg_fetch_results[k]["done"]
                for k in ("space_weather", "noaa", "donki")
            )
            stale = _are_fetch_times_stale(fetch_times_snapshot)
            if all_done and not stale:
                return False  # Data is fresh, no need to refetch

        # Reset state for fresh fetch if forcing or if stale
        if force or _are_fetch_times_stale(fetch_times_snapshot):
            _reset_bg_fetch_for_refresh()

        # Start a new daemon thread while holding the lock to avoid races
        _bg_fetch_thread = threading.Thread(
            target=_bg_fetch_all_space_data,
            name="SpaceWeatherBgFetch",
            daemon=True,
        )
        _bg_fetch_thread.start()
        return True


def _get_bg_fetch_age_str() -> str:
    """
    Get a human-readable string showing how old the background fetch data is.

    Returns a string like "2h 15m ago" or "Just now" or "Not fetched".
    """
    with _bg_fetch_lock:
        # Get the oldest fetch time among all sources
        fetch_times = [
            _bg_fetch_results[k].get("fetch_time")
            for k in ("space_weather", "noaa", "donki")
        ]
        valid_times = [t for t in fetch_times if t is not None]
        if not valid_times:
            return "Not fetched"
        oldest = min(valid_times)

    age_seconds = time.time() - oldest
    if age_seconds < 60:
        return "Just now"
    if age_seconds < 3600:
        return f"{int(age_seconds // 60)}m ago"
    hours = age_seconds / 3600
    if hours < 24:
        return f"{hours:.1f}h ago"
    return f"{hours / 24:.1f}d ago"


def _poll_background_fetch() -> Dict[str, Any]:
    """
    Check the status of background fetch without blocking.

    Returns a dict with status for each category:
      {"space_weather": {"done": bool, "error": str|None, "stale": bool}, ...}
    """
    now = time.time()
    with _bg_fetch_lock:
        result = {}
        for k, v in _bg_fetch_results.items():
            fetch_time = v.get("fetch_time")
            is_stale = (
                fetch_time is None
                or (now - fetch_time) >= _BG_FETCH_INTERVAL_SECONDS
            )
            result[k] = {
                "done": v["done"],
                "error": v["error"],
                "stale": is_stale,
            }
        return result


def _apply_background_fetch_to_state() -> Tuple[bool, List[str]]:
    """
    Transfer completed background fetch data to Streamlit session state.

    Returns (any_applied, list_of_errors).
    This function is safe to call multiple times; it only applies data once.
    """
    applied = False
    errors: List[str] = []

    with _bg_fetch_lock:
        # Space Weather
        sw = _bg_fetch_results["space_weather"]
        if sw["done"] and sw["data"] and not sw.get("_applied"):
            state = _space_weather_state()
            state["kp_df"] = sw["data"].get("kp_df", pd.DataFrame())
            state["flux_df"] = sw["data"].get("flux_df", pd.DataFrame())
            state["last_updated"] = sw["data"].get("last_updated")
            state["loaded"] = bool(
                (not state["kp_df"].empty) or (not state["flux_df"].empty)
            )
            state["auto_attempted"] = True
            sw["_applied"] = True
            applied = True
        if sw["done"] and sw["error"]:
            errors.append(f"Space Weather: {sw['error']}")

        # NOAA
        noaa = _bg_fetch_results["noaa"]
        if noaa["done"] and noaa["data"] and not noaa.get("_applied"):
            state = _noaa_space_state()
            state["bundles"] = noaa["data"].get("bundles", {})
            state["errors"] = noaa["data"].get("errors", {})
            state["last_updated"] = noaa["data"].get("last_updated")
            state["auto_attempted"] = True
            noaa["_applied"] = True
            applied = True
        if noaa["done"] and noaa["error"]:
            errors.append(f"NOAA: {noaa['error']}")

        # DONKI
        donki = _bg_fetch_results["donki"]
        if donki["done"] and donki["data"] and not donki.get("_applied"):
            state = _donki_state()
            state["datasets"] = donki["data"].get("datasets", {})
            state["errors"] = donki["data"].get("errors", {})
            state["start_date"] = donki["data"].get("start_date", "")
            state["end_date"] = donki["data"].get("end_date", "")
            state["last_updated"] = donki["data"].get("last_updated")
            state["loaded"] = bool(donki["data"].get("datasets"))
            donki["_applied"] = True
            applied = True
        if donki["done"] and donki["error"]:
            errors.append(f"DONKI: {donki['error']}")

    return applied, errors


def _check_and_trigger_auto_refresh() -> bool:
    """
    Check if data is stale (>12h) and trigger a background refresh if needed.

    Returns True if a refresh was triggered.
    This is called on each page load to ensure data stays current.
    """
    if _is_bg_fetch_stale():
        return _start_background_fetch(force=False)
    return False


def _ensure_background_fetch_for_space_tabs() -> None:
    """
    Lazy-start background space weather fetch when space-weather/NOAA tabs are used.

    This avoids any startup delay on the welcome page while keeping data fresh
    once the relevant tabs are opened. It also triggers auto-refresh if stale.
    """
    if "_bg_fetch_started" not in st.session_state:
        started = _start_background_fetch()
        st.session_state["_bg_fetch_started"] = True
        if started:
            _LOGGER.info("Background space weather fetch started (lazy)")
    else:
        _check_and_trigger_auto_refresh()
    _apply_background_fetch_to_state()


def _donki_state() -> Dict[str, Any]:
    state = st.session_state.setdefault(
        "donki_state",
        {
            "loaded": False,
            "datasets": {},
            "errors": {},
            "start_date": "",
            "end_date": "",
            "last_updated": None,
            "summary": pd.DataFrame(),
            "daily_counts": {},
        },
    )
    return state


def _donki_default_range(days: int) -> Tuple[str, str]:
    if days <= 0:
        raise ValueError("days must be positive")
    end_dt = pd.Timestamp.utcnow().normalize()
    start_dt = end_dt - pd.Timedelta(days=int(days))
    return start_dt.date().isoformat(), end_dt.date().isoformat()


def _get_donki_time_columns(endpoint: str) -> List[str]:
    config = DONKI_ENDPOINTS.get(endpoint, {})
    return list(config.get("time_columns", []))


def fetch_donki(
    endpoint: str,
    start_date: str,
    end_date: str,
    params: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    if not NASA_API_KEY:
        _LOGGER.warning("NASA_API_KEY is not set; skipping DONKI fetch for %s", endpoint)
        return pd.DataFrame()
    config = DONKI_ENDPOINTS.get(endpoint)
    if config is None:
        raise ValueError(f"Unsupported DONKI endpoint '{endpoint}'.")
    query: Dict[str, Any] = dict(config.get("default_params", {}))
    query.update({"startDate": start_date, "endDate": end_date})
    if params:
        query.update(params)
    query["api_key"] = NASA_API_KEY
    path = config.get("path", endpoint)
    url = f"{DONKI_API_BASE}/{path}"
    try:
        response = _get_http_session().get(url, params=query, timeout=DONKI_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        log_exception(_LOGGER, f"DONKI request failed for {endpoint}", exc)
        return pd.DataFrame()
    if not data:
        return pd.DataFrame()
    rows: List[Dict[str, Any]] = [data] if isinstance(data, dict) else list(data)
    df = pd.json_normalize(rows)
    time_columns = _get_donki_time_columns(endpoint)
    for col in time_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    df = _safe_to_numeric_columns(df)
    return df


def _extract_datetime_values(value: Any) -> List[pd.Timestamp]:
    collected: List[pd.Timestamp] = []
    stack: List[Any] = [value]
    while stack:
        current = stack.pop()
        if current is None:
            continue
        if isinstance(current, (str, bytes)):
            ts = pd.to_datetime(current, errors="coerce", utc=True)
            if pd.notna(ts):
                collected.append(ts)
            continue
        if isinstance(current, (list, tuple, set)):
            stack.extend(list(current))
            continue
        if isinstance(current, dict):
            stack.extend(list(current.values()))
            continue
        if isinstance(current, (int, float, bool)):
            continue
        try:
            ts = pd.to_datetime(current, errors="coerce", utc=True)
        except Exception:
            ts = pd.NaT
        if pd.notna(ts):
            collected.append(ts)
    return collected


def _safe_feature_name(text: str) -> str:
    """
    Convert an arbitrary label into a safe, snake_case feature name suitable for column names.
    """
    if not isinstance(text, str) or not text:
        return "feature"
    lowered = text.lower()
    normalised = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")
    return normalised or "feature"


def _collect_donki_times(df: pd.DataFrame, columns: List[str]) -> pd.Series:
    values: List[pd.Timestamp] = []
    for col in columns:
        if col not in df.columns:
            continue
        column = df[col]
        if column.dtype == object:
            for item in column:
                values.extend(_extract_datetime_values(item))
        else:
            series = pd.to_datetime(column, errors="coerce", utc=True)
            values.extend(series.dropna().tolist())
    if not values:
        return pd.Series(dtype="datetime64[ns, UTC]")
    timestamps = pd.Series(values, dtype="datetime64[ns, UTC]")
    return timestamps.dropna().sort_values(ignore_index=True)


def donki_event_series(
    df: pd.DataFrame,
    time_columns: List[str],
    *,
    freq: str = "h",
) -> pd.DataFrame:
    timestamps = _collect_donki_times(df, time_columns)
    if timestamps.empty:
        return pd.DataFrame()
    floored = timestamps.dt.floor(freq)
    counts = floored.value_counts().sort_index()
    out = pd.DataFrame(
        {"time_tag": counts.index.to_pydatetime(), "event_count": counts.values}
    )
    out["time_tag"] = pd.to_datetime(out["time_tag"], utc=True)
    return out.sort_values("time_tag")


def _build_donki_summary(datasets: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for code, df in datasets.items():
        title = DONKI_ENDPOINTS.get(code, {}).get("title", code)
        time_columns = _get_donki_time_columns(code)
        timestamps = _collect_donki_times(df, time_columns)
        if timestamps.empty:
            rows.append(
                {
                    "event_type": title,
                    "events": 0,
                    "first_event": None,
                    "latest_event": None,
                }
            )
            continue
        rows.append(
            {
                "event_type": title,
                "events": int(len(timestamps)),
                "first_event": timestamps.iloc[0],
                "latest_event": timestamps.iloc[-1],
            }
        )
    summary_df = pd.DataFrame(rows)
    if not summary_df.empty:
        if "first_event" in summary_df.columns:
            summary_df["first_event"] = pd.to_datetime(
                summary_df["first_event"], utc=True
            )
        if "latest_event" in summary_df.columns:
            summary_df["latest_event"] = pd.to_datetime(
                summary_df["latest_event"], utc=True
            )
    return summary_df.sort_values(
        "event_type") if not summary_df.empty else summary_df


def _donki_daily_counts(
        datasets: Mapping[str, pd.DataFrame]) -> Dict[str, pd.Series]:
    out: Dict[str, pd.Series] = {}
    for code, df in datasets.items():
        time_columns = _get_donki_time_columns(code)
        ts_df = donki_event_series(df, time_columns, freq="D")
        if ts_df.empty:
            continue
        series = ts_df.set_index("time_tag")["event_count"].astype(float)
        out[DONKI_ENDPOINTS.get(code, {}).get("title", code)] = series
    return out


def _update_spaceweatherlive_state(
        state: Dict[str, Any], snapshot: Any) -> None:
    if snapshot is None:
        return
    snapshots: List[Dict[str, Any]] = state.setdefault("swl_snapshots", [])
    snapshot_payload: Dict[str, Any] = {}
    if hasattr(snapshot, "to_dict"):
        try:
            snapshot_payload = snapshot.to_dict()
        except Exception:
            snapshot_payload = {}
    if snapshot_payload:
        snapshots.append(snapshot_payload)
        if len(snapshots) > 200:
            del snapshots[:-200]

    cme_records = getattr(snapshot, "cme_records", []) or []
    cme_rows: List[Dict[str, Any]] = []
    for record in cme_records:
        cactus_id = str(getattr(record, "cactus_id", "") or "").strip()
        if not cactus_id:
            continue
        time_val = getattr(record, "onset_time_utc", None)
        time_tag = pd.to_datetime(time_val, errors="coerce", utc=True)
        if pd.isna(time_tag):
            continue
        row = {
            "cactus_id": cactus_id,
            "time_tag": time_tag,
            "duration_hours": getattr(record, "duration_hours", None),
            "position_angle_deg": getattr(record, "position_angle_deg", None),
            "angular_width_deg": getattr(record, "angular_width_deg", None),
            "velocity_kms": getattr(record, "velocity_kms", None),
            "velocity_variation_kms": getattr(record, "velocity_variation_kms", None),
            "velocity_min_kms": getattr(record, "velocity_min_kms", None),
            "velocity_max_kms": getattr(record, "velocity_max_kms", None),
            "halo_class": (getattr(record, "halo_class", None) or None),
            "snapshot_timestamp": pd.to_datetime(
                getattr(snapshot, "timestamp_utc", None), errors="coerce", utc=True
            ),
        }
        row["halo_flag"] = float(1.0 if row["halo_class"] else 0.0)
        cme_rows.append(row)

    if cme_rows:
        new_df = pd.DataFrame(cme_rows)
        numeric_cols = [
            "duration_hours",
            "position_angle_deg",
            "angular_width_deg",
            "velocity_kms",
            "velocity_variation_kms",
            "velocity_min_kms",
            "velocity_max_kms",
            "halo_flag",
        ]
        for col in numeric_cols:
            if col in new_df.columns:
                new_df[col] = pd.to_numeric(new_df[col], errors="coerce")
        existing = state.get("swl_cme_df", pd.DataFrame())
        combined = (
            pd.concat([existing, new_df], ignore_index=True)
            if not existing.empty
            else new_df.copy()
        )
        if not combined.empty:
            combined["time_tag"] = pd.to_datetime(
                combined["time_tag"], errors="coerce", utc=True
            )
            combined = combined.dropna(subset=["time_tag"])
            combined = combined.drop_duplicates(
                subset=["cactus_id"], keep="last")
            combined = combined.sort_values("time_tag").reset_index(drop=True)
            state["swl_cme_df"] = combined
            indexed = combined.set_index("time_tag").sort_index()
            agg_spec: Dict[str, str] = {"cactus_id": "count"}
            if "velocity_kms" in indexed.columns:
                agg_spec["velocity_kms"] = "median"
            if "velocity_max_kms" in indexed.columns:
                agg_spec["velocity_max_kms"] = "max"
            if "angular_width_deg" in indexed.columns:
                agg_spec["angular_width_deg"] = "median"
            if "halo_flag" in indexed.columns:
                agg_spec["halo_flag"] = "mean"
            if "duration_hours" in indexed.columns:
                agg_spec["duration_hours"] = "median"
            daily_features = indexed.resample("D").agg(agg_spec)
            rename_map = {
                "cactus_id": "cme_daily_count",
                "velocity_kms": "cme_velocity_median",
                "velocity_max_kms": "cme_velocity_max",
                "angular_width_deg": "cme_width_median",
                "halo_flag": "cme_halo_rate",
                "duration_hours": "cme_duration_median",
            }
            daily_features = daily_features.rename(
                columns={
                    k: v for k,
                    v in rename_map.items() if k in daily_features.columns})
            state["swl_cme_daily"] = daily_features.reset_index()
        else:
            state["swl_cme_df"] = pd.DataFrame(columns=new_df.columns)

    stats_payload: Dict[str, Any] = {}
    if hasattr(snapshot, "cme_velocity_stats"):
        try:
            stats_payload = snapshot.cme_velocity_stats()
        except Exception:
            stats_payload = {}
    if stats_payload:
        state["swl_velocity_stats"] = stats_payload

    last_updated = pd.to_datetime(
        getattr(snapshot, "timestamp_utc", None), errors="coerce", utc=True
    )
    if pd.notna(last_updated):
        state["swl_last_updated"] = last_updated
    state["swl_loaded"] = True


def _build_cme_predictor_series(
    cme_df: pd.DataFrame,
) -> List[Tuple[str, pd.DataFrame, str, str]]:
    """
    Construct predictor time series derived from CACTus CME detections.
    """
    if cme_df.empty or "time_tag" not in cme_df.columns:
        return []
    df = cme_df.copy()
    df["time_tag"] = pd.to_datetime(df["time_tag"], errors="coerce", utc=True)
    df = df.dropna(subset=["time_tag"])
    if df.empty:
        return []

    predictors: List[Tuple[str, pd.DataFrame, str, str]] = []
    numeric_event_columns: List[Tuple[str, str]] = [
        ("velocity_kms", "CME velocity (km/s)"),
        ("velocity_max_kms", "CME peak velocity (km/s)"),
        ("angular_width_deg", "CME angular width (°)"),
        ("duration_hours", "CME duration (h)"),
        ("position_angle_deg", "CME position angle (°)"),
        ("halo_flag", "CME halo rate (event-level)"),
    ]
    for column, title in numeric_event_columns:
        if column not in df.columns:
            continue
        event_subset = df[["time_tag", column]].dropna()
        if event_subset.empty:
            continue
        predictors.append((title, event_subset, "time_tag", column))

    indexed = df.set_index("time_tag").sort_index()
    daily_resampled = indexed.resample("D")

    daily_count = daily_resampled["cactus_id"].count().rename(
        "cme_daily_count")
    if not daily_count.empty:
        predictors.append(
            (
                "Daily CME count",
                daily_count.reset_index(),
                "time_tag",
                "cme_daily_count",
            )
        )

    if "velocity_kms" in indexed.columns:
        daily_velocity_median = (
            daily_resampled["velocity_kms"]
            .median()
            .dropna()
            .rename("cme_velocity_median")
        )
        if not daily_velocity_median.empty:
            predictors.append(
                (
                    "Daily median CME velocity (km/s)",
                    daily_velocity_median.reset_index(),
                    "time_tag",
                    "cme_velocity_median",
                )
            )

    if "velocity_max_kms" in indexed.columns:
        daily_velocity_max = (
            daily_resampled["velocity_max_kms"]
            .max()
            .dropna()
            .rename("cme_velocity_max")
        )
        if not daily_velocity_max.empty:
            predictors.append(
                (
                    "Daily max CME velocity (km/s)",
                    daily_velocity_max.reset_index(),
                    "time_tag",
                    "cme_velocity_max",
                )
            )

    if "angular_width_deg" in indexed.columns:
        daily_width = (
            daily_resampled["angular_width_deg"]
            .median()
            .dropna()
            .rename("cme_width_median")
        )
        if not daily_width.empty:
            predictors.append(
                (
                    "Daily median CME width (°)",
                    daily_width.reset_index(),
                    "time_tag",
                    "cme_width_median",
                )
            )

    if "halo_flag" in indexed.columns:
        daily_halo_rate = (
            daily_resampled["halo_flag"].mean().dropna().rename("cme_halo_rate"))
        if not daily_halo_rate.empty:
            predictors.append(
                (
                    "Daily halo CME rate",
                    daily_halo_rate.reset_index(),
                    "time_tag",
                    "cme_halo_rate",
                )
            )

    return predictors


def _merge_series_with_lags(
    base_times: pd.DataFrame,
    series_df: pd.DataFrame,
    time_col: str,
    value_col: str,
    lags_hours: Sequence[int],
    tolerance_minutes: int,
    prefix: str,
) -> pd.DataFrame:
    """
    Align a predictor series to HRV window start times across multiple lags.
    """
    if series_df.empty or value_col not in series_df.columns:
        return pd.DataFrame(index=base_times.index)
    series = (series_df[[time_col, value_col]].dropna(
        subset=[time_col, value_col]).copy())
    if series.empty:
        return pd.DataFrame(index=base_times.index)
    series[time_col] = pd.to_datetime(
        series[time_col], errors="coerce", utc=True)
    series = series.dropna(subset=[time_col]).sort_values(time_col)
    if series.empty:
        return pd.DataFrame(index=base_times.index)
    window_index = pd.to_datetime(
        base_times["window_start"], errors="coerce", utc=True
    )
    valid_mask = window_index.notna()
    feature_frames: Dict[str, pd.Series] = {}
    for lag in lags_hours:
        aligned = align_space_weather_series(
            reference_times=window_index,
            predictor_df=series,
            predictor_time_col=time_col,
            predictor_value_col=value_col,
            lag_hours=int(lag),
            max_gap_minutes=int(tolerance_minutes),
        )
        col_name = _safe_feature_name(f"{prefix}_lag_{lag:+d}h")
        if aligned.empty or not valid_mask.any():
            feature_frames[col_name] = pd.Series(
                np.nan, index=base_times.index, dtype=float
            )
            continue
        ordered_aligned = aligned.reindex(window_index[valid_mask])
        values = pd.Series(np.nan, index=base_times.index, dtype=float)
        values.loc[valid_mask] = ordered_aligned.to_numpy()
        feature_frames[col_name] = values
    if not feature_frames:
        return pd.DataFrame(index=base_times.index)
    return pd.DataFrame(feature_frames, index=base_times.index)


def _build_space_weather_feature_matrix(
    windowed_df: pd.DataFrame,
    predictors: Sequence[Tuple[str, pd.DataFrame, str, str]],
    *,
    lags_hours: Sequence[int],
    tolerance_minutes: int,
    metric_columns: Sequence[str],
) -> pd.DataFrame:
    """
    Build a feature matrix aligning HRV window metrics with lagged space-weather predictors.
    """
    if windowed_df.empty:
        raise ValueError("HRV windowed dataframe is empty.")
    if "start" not in windowed_df.columns:
        raise ValueError(
            "HRV windowed dataframe lacks a 'start' timestamp column.")
    if not predictors:
        raise ValueError("No predictor series supplied.")
    use_metrics = [
        col
        for col in metric_columns
        if col in windowed_df.columns
        and pd.api.types.is_numeric_dtype(windowed_df[col])
    ]
    if not use_metrics:
        raise ValueError(
            "No numeric HRV metric columns available for feature construction."
        )
    base = windowed_df[["start"] + use_metrics].copy()
    base["window_start"] = pd.to_datetime(
        base["start"], errors="coerce", utc=True)
    base = base.dropna(subset=["window_start"]).reset_index(drop=True)
    if base.empty:
        raise ValueError(
            "All HRV windows have invalid timestamps; cannot align predictors."
        )
    base_times = base[["window_start"]]
    feature_blocks: List[pd.DataFrame] = []
    used_names: Set[str] = set()
    unique_lags = sorted({int(lag) for lag in lags_hours}) or [0]
    for title, s_df, tcol, vcol in predictors:
        prefix_raw = f"{title}_{vcol}"
        prefix = _safe_feature_name(prefix_raw)
        aligned_block = _merge_series_with_lags(
            base_times,
            s_df,
            tcol,
            vcol,
            unique_lags,
            int(tolerance_minutes),
            prefix,
        )
        if aligned_block.empty:
            continue
        rename_map: Dict[str, str] = {}
        for column in aligned_block.columns:
            candidate = column
            if candidate in used_names:
                suffix = 1
                while f"{candidate}_{suffix}" in used_names:
                    suffix += 1
                candidate = f"{candidate}_{suffix}"
            rename_map[column] = candidate
            used_names.add(candidate)
        feature_blocks.append(aligned_block.rename(columns=rename_map))
    features = (
        pd.concat(feature_blocks, axis=1, sort=False).reset_index(drop=True)
        if feature_blocks
        else pd.DataFrame(index=base.index)
    )
    result = pd.concat(
        [
            base[["window_start"] + use_metrics].reset_index(drop=True),
            features,
        ],
        axis=1,
    )
    return result


def _compute_feature_correlations(
    matrix_df: pd.DataFrame,
    metric_columns: Sequence[str],
    feature_columns: Sequence[str],
) -> pd.DataFrame:
    """
    Compute Pearson correlations between HRV metrics and predictor features.
    """
    if matrix_df.empty:
        raise ValueError("Feature matrix is empty.")
    common_metrics = [
        col for col in metric_columns if col in matrix_df.columns]
    if not common_metrics:
        raise ValueError(
            "None of the specified metric columns are present in the feature matrix."
        )
    common_features = [
        col for col in feature_columns if col in matrix_df.columns]
    if not common_features:
        raise ValueError(
            "No predictor features available for correlation analysis.")
    rows: List[Dict[str, Any]] = []
    for metric in common_metrics:
        for feature in common_features:
            pair = matrix_df[[metric, feature]].dropna()
            n_samples = int(pair.shape[0])
            if n_samples < 3:
                continue
            r_val = float(pair[metric].corr(pair[feature]))
            rows.append(
                {
                    "metric": metric,
                    "feature": feature,
                    "pearson_r": r_val,
                    "samples": n_samples,
                }
            )
    if not rows:
        raise ValueError(
            "No overlapping samples found to compute correlations.")
    result_df = pd.DataFrame(rows)
    result_df["abs_r"] = result_df["pearson_r"].abs()
    return result_df.sort_values("abs_r", ascending=False, ignore_index=True)


def _rank_top_predictors(
    matrix_df: pd.DataFrame,
    metric_columns: Sequence[str],
    feature_columns: Sequence[str],
    *,
    min_samples: int = 12,
    top_n: int = 5,
) -> pd.DataFrame:
    """
    Return the strongest predictors per HRV metric based on Pearson correlation.
    """
    if top_n < 1:
        raise ValueError("top_n must be at least 1.")
    corr_df = _compute_feature_correlations(
        matrix_df, metric_columns, feature_columns)
    corr_df = corr_df[corr_df["samples"] >= int(min_samples)]
    if corr_df.empty:
        raise ValueError(
            "No metric-feature pairs met the minimum sample requirement.")
    top_rows: List[pd.DataFrame] = []
    for metric, group in corr_df.groupby("metric", sort=False):
        top_rows.append(group.head(top_n))
    if not top_rows:
        raise ValueError(
            "Unable to compute predictor rankings; check input data.")
    return pd.concat(top_rows, ignore_index=True).sort_values(
        ["metric", "abs_r"], ascending=[True, False]
    )


def _fit_linear_response_model(
    matrix_df: pd.DataFrame,
    target_column: str,
    feature_columns: Sequence[str],
    train_fraction: float = 0.75,
) -> Dict[str, Any]:
    """
    Train a simple linear regression model (OLS) predicting a HRV metric from space-weather predictors.
    """
    if not 0.1 <= train_fraction <= 0.95:
        raise ValueError("train_fraction must be between 0.1 and 0.95.")
    columns_needed = [target_column] + list(feature_columns)
    missing_cols = [
        col for col in columns_needed if col not in matrix_df.columns]
    if missing_cols:
        raise ValueError(
            f"Missing columns in feature matrix: {', '.join(missing_cols)}"
        )
    data = matrix_df[columns_needed].dropna().reset_index(drop=True)
    if data.empty:
        raise ValueError("No complete rows available after dropping NaNs.")
    n_rows = data.shape[0]
    n_features = len(feature_columns)
    if n_rows <= n_features + 1:
        raise ValueError(
            "Not enough samples to train the model; add more windows or reduce feature count."
        )
    rng = np.random.default_rng(941)
    indices = np.arange(n_rows)
    rng.shuffle(indices)
    data = data.iloc[indices].reset_index(drop=True)
    split_idx = max(int(n_rows * float(train_fraction)), n_features + 1)
    if split_idx >= n_rows:
        split_idx = n_rows - 1
    X_all = data[feature_columns].to_numpy(dtype=float)
    y_all = data[target_column].to_numpy(dtype=float)
    feature_mean = np.nanmean(X_all, axis=0)
    feature_std = np.nanstd(X_all, axis=0)
    feature_std[feature_std == 0.0] = 1.0
    X_all = (X_all - feature_mean) / feature_std
    X_train = X_all[:split_idx, :]
    y_train = y_all[:split_idx]
    X_test = X_all[split_idx:, :]
    y_test = y_all[split_idx:]
    X_train_design = np.hstack([np.ones((X_train.shape[0], 1)), X_train])
    coef, _, _, _ = np.linalg.lstsq(X_train_design, y_train, rcond=None)

    def _predict(x_matrix: np.ndarray) -> np.ndarray:
        design = np.hstack([np.ones((x_matrix.shape[0], 1)), x_matrix])
        return design @ coef

    y_train_pred = _predict(X_train)
    y_test_pred = _predict(X_test)

    def _r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        if y_true.size == 0:
            return float("nan")
        ss_tot = float(np.square(y_true - y_true.mean()).sum())
        if ss_tot == 0.0:
            return float("nan")
        ss_res = float(np.square(y_true - y_pred).sum())
        return 1.0 - (ss_res / ss_tot)

    def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        if y_true.size == 0:
            return float("nan")
        return float(np.sqrt(np.square(y_true - y_pred).mean()))

    def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        if y_true.size == 0:
            return float("nan")
        return float(np.abs(y_true - y_pred).mean())

    metrics = {
        "train_samples": int(y_train.size),
        "test_samples": int(y_test.size),
        "train_r2": _r_squared(y_train, y_train_pred),
        "test_r2": _r_squared(y_test, y_test_pred),
        "train_rmse": _rmse(y_train, y_train_pred),
        "test_rmse": _rmse(y_test, y_test_pred),
        "train_mae": _mae(y_train, y_train_pred),
        "test_mae": _mae(y_test, y_test_pred),
    }
    coef_table = pd.DataFrame(
        {
            "feature": ["intercept"] + list(feature_columns),
            "coefficient": coef.astype(float),
        }
    )
    return {
        "metrics": metrics,
        "coefficients": coef_table,
        "feature_mean": feature_mean,
        "feature_std": feature_std,
    }


def _render_lag_scan_summary(
    title: str, res: pd.DataFrame, *, lags: Sequence[int]
) -> None:
    if res.empty:
        st.info(f"No aligned samples for {title}.")
        return
    result_table = res.copy()
    if "p_value" in result_table.columns and result_table["p_value"].notna(
    ).any():
        result_table["q_value"], _ = fdr_bh(
            result_table["p_value"].fillna(1.0).to_numpy(), alpha=0.05
        )
    res_sorted = result_table.sort_values(
        "pearson_r", key=lambda s: s.abs(), ascending=False
    )
    st.write(title)
    st.dataframe(res_sorted.head(20))
    best_res = res_sorted.iloc[0]
    r_val = float(best_res.get("pearson_r", 0.0))
    abs_r_val = float(abs(r_val))
    lag_best = int(best_res.get("lag_hours", 0))
    n_best = int(best_res.get("n", 0))
    p_best = (
        float(best_res.get("p_value", np.nan))
        if "p_value" in best_res
        else float("nan")
    )
    q_best = (
        float(best_res.get("q_value", np.nan))
        if "q_value" in best_res
        else float("nan")
    )
    metric_best = str(best_res.get("metric", "HRV metric"))
    if "lag_hours" in res_sorted.columns and res_sorted["lag_hours"].notna(
    ).any():
        lag_span_ds = float(
            np.nanmax(np.abs(res_sorted["lag_hours"].to_numpy(dtype=float)))
        )
    else:
        lag_span_ds = float(max(abs(val) for val in lags)) if lags else 1.0
    if lag_best > 0:
        lag_desc = "Predictor changes lead HRV changes"
    elif lag_best < 0:
        lag_desc = "HRV changes lead the predictor metric"
    else:
        lag_desc = "Simultaneous variability"
    col_1, col_2, col_3, col_4 = st.columns(4)
    with col_1:
        _echarts_gauge(
            abs_r_val,
            min_val=0.0,
            max_val=1.0,
            title=f"|r| — {metric_best}",
            formatter="{value:.2f}",
            thresholds=[
                (0.2, "#f97316"),
                (0.4, "#facc15"),
                (0.6, "#4ade80"),
                (1.0, "#16a34a"),
            ],
        )
    with col_2:
        if np.isfinite(q_best):
            _echarts_gauge(
                q_best,
                min_val=0.0,
                max_val=0.1,
                title="FDR q-value",
                formatter="{value:.3f}",
                thresholds=[
                    (0.01, "#22c55e"),
                    (0.05, "#facc15"),
                    (0.1, "#ef4444"),
                ],
            )
        elif np.isfinite(p_best):
            _echarts_gauge(
                p_best,
                min_val=0.0,
                max_val=0.1,
                title="p-value",
                formatter="{value:.3f}",
                thresholds=[
                    (0.01, "#22c55e"),
                    (0.05, "#facc15"),
                    (0.1, "#ef4444"),
                ],
            )
        else:
            st.info("Significance metrics unavailable.")
    with col_3:
        _echarts_gauge(
            float(abs(lag_best)),
            min_val=0.0,
            max_val=max(1.0, lag_span_ds),
            title="Lag (h)",
            formatter="{value:.0f}",
            thresholds=[
                (max(1.0, lag_span_ds * 0.25), "#38bdf8"),
                (max(3.0, lag_span_ds * 0.5), "#2563eb"),
                (max(6.0, lag_span_ds), "#1d4ed8"),
            ],
        )
    with col_4:
        max_n_ds = float(max(n_best, 10)) * 1.1
        _echarts_gauge(
            float(n_best),
            min_val=0.0,
            max_val=max_n_ds,
            title="Samples (n)",
            formatter="{value:.0f}",
            thresholds=[
                (max_n_ds * 0.25, "#f87171"),
                (max_n_ds * 0.5, "#facc15"),
                (max_n_ds * 0.75, "#22c55e"),
            ],
        )
    sig_line: str
    if np.isfinite(q_best):
        sig_line = f"- q = {q_best:.3f} after FDR control."
    elif np.isfinite(p_best):
        sig_line = f"- p = {p_best:.3f}."
    else:
        sig_line = "- Significance metric unavailable."
    st.markdown(
        f"**{title} insight**\n"
        f"- Metric `{metric_best}` correlates with HRV at |r| = {abs_r_val:.2f} ({'positive' if r_val >= 0 else 'negative'}).\n"
        f"- Optimal lag: {lag_best} h ({lag_desc}).\n"
        f"{sig_line}\n"
        f"- Samples contributing to this correlation: n = {n_best}."
    )
    st.caption(
        "Interpret these lagged correlations as exploratory evidence linking external space-weather drivers to HRV dynamics. "
        "Use them to prioritise further analysis, physiological validation, or mechanistic modelling.")


def _fetch_donki_datasets(
    state: Dict[str, Any],
    start_date: str,
    end_date: str,
    endpoints: Optional[List[str]] = None,
) -> None:
    if not NASA_API_KEY:
        state["loaded"] = False
        state["errors"] = {"auth": "NASA_API_KEY is not set."}
        return
    targets = endpoints or list(DONKI_ENDPOINTS.keys())
    datasets: Dict[str, pd.DataFrame] = {}
    errors: Dict[str, str] = {}
    for code in targets:
        try:
            config = DONKI_ENDPOINTS.get(code, {})
            default_days = int(config.get("default_days", 30))
            start_to_use = start_date
            end_to_use = end_date
            if default_days == 7:
                adjust_start, adjust_end = _donki_default_range(7)
                start_to_use = max(adjust_start, start_date)
                end_to_use = end_date if end_date else adjust_end
            cache_file = (
                DONKI_CACHE_DIR
                / f"{code}_{start_to_use}_{end_to_use or 'auto'}.json"
            )
            cached_df = _read_dataframe_cache(
                cache_file, max_age=DONKI_CACHE_TTL)
            if cached_df is not None:
                datasets[code] = cached_df
                continue
            df = fetch_donki(code, start_to_use, end_to_use)
            _write_dataframe_cache(cache_file, df)
            datasets[code] = df
        except requests.HTTPError as exc:
            errors[code] = (
                f"{exc.response.status_code if exc.response else 'HTTP'} error"
            )
        except Exception as exc:
            errors[code] = str(exc)
    state["datasets"] = datasets
    state["errors"] = errors
    state["start_date"] = start_date
    state["end_date"] = end_date
    state["last_updated"] = pd.Timestamp.utcnow()
    state["summary"] = _build_donki_summary(datasets)
    state["daily_counts"] = _donki_daily_counts(datasets)
    state["loaded"] = True if datasets else False


def _fetch_space_weather_datasets(state: Dict[str, Any]) -> None:
    state["loaded"] = False
    state["kp_df"] = pd.DataFrame()
    state["kp_error"] = ""
    state["flux_df"] = pd.DataFrame()
    state["flux_error"] = ""
    kp_duration_ms: Optional[float] = None
    flux_duration_ms: Optional[float] = None

    def _timed_call(fn) -> Tuple[pd.DataFrame, float]:
        start = time.perf_counter()
        df = fn()
        return df, (time.perf_counter() - start) * 1000.0

    import concurrent.futures

    # Fetch Kp + F10.7 in parallel to reduce wall-clock latency on slow networks.
    overall_timeout_s = 8.0  # hard bound total wait time for UI responsiveness
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    future_kp = executor.submit(
        _timed_call, lambda: get_swpc_kp_index(days=SPACE_WEATHER_MAX_DAYS)
    )
    future_flux = executor.submit(_timed_call, get_swpc_solar_radio_flux)
    futures = {"kp": future_kp, "flux": future_flux}

    try:
        done, not_done = concurrent.futures.wait(
            set(futures.values()),
            timeout=overall_timeout_s,
            return_when=concurrent.futures.ALL_COMPLETED,
        )

        # Kp
        if future_kp in done:
            try:
                kp_df, kp_duration_ms = future_kp.result()
                state["kp_df"] = kp_df
            except (requests.RequestException, ValueError) as exc:
                log_exception(_LOGGER, "Failed to fetch SWPC K-index", exc)
                state["kp_error"] = f"Failed to retrieve K-index data: {exc}"
            except Exception as exc:  # pragma: no cover - defensive
                log_exception(_LOGGER, "Unexpected SWPC K-index error", exc)
                state["kp_error"] = f"Unexpected error fetching Kp: {exc}"
        else:
            state["kp_error"] = f"Kp fetch timed out (>{overall_timeout_s:.0f}s). Try again or use cached data."

        # F10.7
        if future_flux in done:
            try:
                flux_df, flux_duration_ms = future_flux.result()
                state["flux_df"] = flux_df
            except (requests.RequestException, ValueError) as exc:
                log_exception(_LOGGER, "Failed to fetch SWPC solar radio flux", exc)
                state["flux_error"] = f"Failed to retrieve solar radio flux: {exc}"
            except Exception as exc:  # pragma: no cover - defensive
                log_exception(_LOGGER, "Unexpected SWPC solar radio flux error", exc)
                state["flux_error"] = f"Unexpected error fetching F10.7: {exc}"
        else:
            state["flux_error"] = f"F10.7 fetch timed out (>{overall_timeout_s:.0f}s). Try again or use cached data."

        # Best-effort cancel any remaining work (threads may still be stuck in DNS/TLS).
        for pending in not_done:
            _ = pending.cancel()
    finally:
        # Do not block Streamlit waiting for worker threads to finish.
        executor.shutdown(wait=False, cancel_futures=True)
    state["last_updated"] = pd.Timestamp.utcnow()
    state["loaded"] = bool(
        (isinstance(state.get("kp_df"), pd.DataFrame) and not state["kp_df"].empty)
        or (isinstance(state.get("flux_df"), pd.DataFrame) and not state["flux_df"].empty)
    )
    #region agent log
    _agent_debug_log(
        "H1",
        "app.py:_fetch_space_weather_datasets",
        "space_weather_fetch_complete",
        {
            "kp_rows": int(state["kp_df"].shape[0]) if isinstance(state.get("kp_df"), pd.DataFrame) else 0,
            "flux_rows": int(state["flux_df"].shape[0]) if isinstance(state.get("flux_df"), pd.DataFrame) else 0,
            "kp_error": state.get("kp_error", ""),
            "flux_error": state.get("flux_error", ""),
            "kp_duration_ms": kp_duration_ms,
            "flux_duration_ms": flux_duration_ms,
        },
    )
    #endregion


def _request_interpretation_with_progress(
    container: st.delta_generator.DeltaGenerator,
    analysis_payload: str,
    timeout: float = 300.0,
) -> InterpretationResult:
    progress_slot = container.container()
    progress_bar = progress_slot.progress(
        0, text="Preparing GPT-5 interpretation (0%)")
    checkpoints = [12, 28, 44, 60, 76, 92]
    step_delay = min(1.0, timeout / max(len(checkpoints) + 1, 2))
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                request_interpretation, analysis_payload, timeout=timeout
            )
            for percent in checkpoints:
                if future.done():
                    break
                progress_bar.progress(
                    percent, text=f"Generating GPT-5 interpretation ({percent}%)")
                time.sleep(step_delay)
            result = future.result(
                timeout=max(1.0, timeout - step_delay * len(checkpoints))
            )
    except concurrent.futures.TimeoutError as exc:
        progress_slot.empty()
        raise GPT5InterpretationError(
            "GPT-5 interpretation timed out.") from exc
    except GPT5InterpretationError:
        progress_slot.empty()
        raise
    except Exception as exc:  # pragma: no cover - defensive
        progress_slot.empty()
        raise GPT5InterpretationError(
            f"Unexpected GPT-5 error: {exc}") from exc
    progress_bar.progress(100, text="GPT-5 interpretation ready (100%)")
    time.sleep(0.25)
    progress_slot.empty()
    return result


def _render_gpt_high_interpretation(
    container: st.delta_generator.DeltaGenerator,
    *,
    enabled: bool,
    meta_rows: List[Dict[str, Any]],
    multi_results_df: pd.DataFrame,
    windowed_df: pd.DataFrame,
    episodes_df: pd.DataFrame,
    ml_summary_df: pd.DataFrame,
    report_markdown: Optional[str] = None,
) -> None:
    state = st.session_state.setdefault(
        "gpt5_high_state",
        {
            "payload_hash": "",
            "markdown": "",
            "sources": [],
            "reasoning_encrypted": None,
        },
    )
    if not enabled:
        container.empty()
        st.session_state["gpt5_export_markdown"] = ""
        return
    title_container = container.container()
    body_container = container.container()
    title_container.markdown("### GPT-5 High Interpretation")
    if not meta_rows and multi_results_df.empty and windowed_df.empty:
        body_container.info(
            "Run the analysis to enable the GPT-5 interpretation.")
        st.session_state["gpt5_export_markdown"] = ""
        return
    try:
        analysis_payload = build_analysis_payload(
            meta_rows,
            multi_results_df,
            windowed_df,
            episodes_df,
            ml_summary_df,
            space_analytics_corr=(
                st.session_state.get("space_analytics_corr_results")
                if isinstance(st.session_state.get("space_analytics_corr_results"), dict)
                else None
            ),
            space_analytics_ml=(
                st.session_state.get("space_analytics_ml_results")
                if isinstance(st.session_state.get("space_analytics_ml_results"), dict)
                else None
            ),
            report_markdown=report_markdown,
        )
    except (GPT5InterpretationError, ValueError, TypeError) as exc:
        body_container.error(str(exc))
        st.session_state["gpt5_export_markdown"] = ""
        return
    except Exception as exc:  # pragma: no cover - defensive
        body_container.error(f"Failed to build analysis payload: {exc}")
        st.session_state["gpt5_export_markdown"] = ""
        return
    payload_hash = hashlib.sha256(analysis_payload.encode("utf-8")).hexdigest()
    # Load any previously stored report for this exact payload hash (no API call).
    if state.get("payload_hash") != payload_hash and not state.get("markdown"):
        try:
            ctx = get_active_user_context()
        except Exception:
            ctx = _guest_user_context()
        if ctx.get("has_user") and ctx.get("user_id"):
            try:
                db = get_database()
                stored = db.get_ai_report(
                    user_id=str(ctx.get("user_id")),
                    report_type="hrv_gpt5_high",
                    context_hash=payload_hash,
                )
            except Exception as exc:  # pragma: no cover - defensive
                log_exception(_LOGGER, "Failed to load stored GPT-5 report", exc)
            else:
                if stored is not None and getattr(stored, "markdown", "").strip():
                    state["payload_hash"] = payload_hash
                    state["markdown"] = stored.markdown
                    sources = getattr(stored, "sources", None)
                    if isinstance(sources, list):
                        state["sources"] = sources
                    state["reasoning_encrypted"] = getattr(
                        stored, "reasoning_encrypted", None
                    )
                    st.session_state["gpt5_export_markdown"] = stored.markdown

    payload_changed = bool(state.get("payload_hash")) and state["payload_hash"] != payload_hash
    if payload_changed and state.get("markdown"):
        body_container.warning(
            "The analysis inputs changed since the last GPT-5 run. "
            "Click **Generate** to refresh the interpretation."
        )

    run_label = (
        "Generate GPT-5.2 interpretation (code interpreter)"
        if not state.get("markdown")
        else "Regenerate GPT-5.2 interpretation"
    )
    run_now = body_container.button(
        run_label,
        key="gpt5_high_generate",
        type="primary",
        help="Runs OpenAI GPT-5.2 high reasoning with code interpreter. Only runs when you click this button.",
    )
    if run_now:
        try:
            result = _request_interpretation_with_progress(
                body_container, analysis_payload
            )
        except GPT5InterpretationError as exc:
            if "OPENAI_API_KEY" in str(exc).upper():
                body_container.warning(
                    "Set OPENAI_API_KEY in your .env file before committing to version control."
                )
            else:
                body_container.error(str(exc))
            st.session_state["gpt5_export_markdown"] = ""
            return
        state["payload_hash"] = payload_hash
        state["markdown"] = result.markdown
        state["sources"] = result.sources
        state["reasoning_encrypted"] = result.reasoning_encrypted
        st.session_state["gpt5_tts_audio"] = b""
        # Persist the rendered markdown (not raw reasoning) per active user for exports.
        try:
            ctx = get_active_user_context()
        except Exception:
            ctx = _guest_user_context()
        if ctx.get("has_user") and ctx.get("user_id"):
            try:
                db = get_database()
                db.save_ai_report(
                    user_id=str(ctx.get("user_id")),
                    report_type="hrv_gpt5_high",
                    context_hash=payload_hash,
                    markdown=result.markdown,
                    sources=result.sources,
                    model_used=getattr(result, "model_used", None),
                    mode=getattr(getattr(result, "mode", None), "value", None),
                    confidence=getattr(result, "confidence", None),
                )
            except Exception as exc:  # pragma: no cover - defensive
                _LOGGER.debug("Unable to persist GPT report to DB: %s", exc)
    if not state["markdown"]:
        body_container.info(
            "Click **Generate** to run GPT-5.2 and produce an on-demand interpretation."
        )
        st.session_state["gpt5_export_markdown"] = ""
        return
    body_container.markdown(state["markdown"])
    if state["sources"]:
        body_container.caption("Sources: " + ", ".join(state["sources"]))
    st.session_state["gpt5_export_markdown"] = state["markdown"]


@dataclass(slots=True)
class UploadedRR:
    name: str
    rr_ms: np.ndarray
    df: pd.DataFrame
    recording_start_utc: Optional[pd.Timestamp] = None
    rr_ms_clean: Optional[np.ndarray] = None
    artifact_valid_mask: Optional[np.ndarray] = None
    qc_summary: Optional[Dict] = None


def _get_uploaded_rr_time_bounds() -> Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
    """Return the (min_utc, max_utc) timestamps across currently uploaded RR files.

    This is used to "sync" space-weather views/queries to the RR timeline. It is
    intentionally defensive: any malformed/missing timestamps are ignored.
    """
    cache = st.session_state.get("uploaded_rr_cache", {})
    if not isinstance(cache, dict) or not cache:
        return None, None

    mins: list[pd.Timestamp] = []
    maxs: list[pd.Timestamp] = []
    for item in cache.values():
        if not isinstance(item, UploadedRR):
            continue
        df = item.df
        if not isinstance(df, pd.DataFrame) or df.empty or "timestamp" not in df.columns:
            continue
        ts = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        ts = ts.dropna()
        if ts.empty:
            continue
        mins.append(ts.min())
        maxs.append(ts.max())

    if not mins or not maxs:
        return None, None
    return min(mins), max(maxs)


def _to_dataframe(
    name: str, rr_ms: np.ndarray, *, start_ts: Optional[pd.Timestamp] = None
) -> pd.DataFrame:
    if rr_ms.size == 0:
        return pd.DataFrame()
    if start_ts is None:
        start_ts, _ = _infer_recording_start(name)
    if not isinstance(start_ts, pd.Timestamp):
        raise TypeError("start_ts must be a pandas.Timestamp when provided.")
    if start_ts.tzinfo is None or start_ts.tzinfo.utcoffset(start_ts) is None:
        start_ts = start_ts.tz_localize(timezone.utc)
    else:
        start_ts = start_ts.tz_convert(timezone.utc)
    hr = 60000.0 / rr_ms
    rr_cum_s = np.cumsum(rr_ms) / 1000.0
    timestamps = start_ts + pd.to_timedelta(rr_cum_s, unit="s")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "rr_intervals_ms": rr_ms,
            "heart_rate [bpm]": hr,
            "beat_index": np.arange(rr_ms.size, dtype=int),
            "source": name,
        }
    )
    return df


def _compute_file_hash(content: bytes) -> str:
    """Compute hash of file content for cache key."""
    return hashlib.md5(content).hexdigest()[:16]


def _get_user_identity(profile: Any) -> Tuple[Optional[str], str]:
    """Return (user_id, display_name) from a profile object or dict."""
    if profile is None:
        return None, "Guest"
    if isinstance(profile, dict):
        user_id = profile.get("user_id")
        display = profile.get("full_name") or profile.get("username") or "Unknown User"
        return user_id, display
    user_id = getattr(profile, "user_id", None)
    display = (
        getattr(profile, "full_name", None)
        or getattr(profile, "username", None)
        or "Unknown User"
    )
    return user_id, display


def _resolve_active_profile(logger: logging.Logger) -> Any:
    """Resolve the active user profile.

    Important:
        This must never silently "log in" a profile after a user has logged out.
        Auto-selecting a default profile can make logout appear broken.
    """
    if st.session_state.get("user_logged_out"):
        return None
    existing = st.session_state.get("current_user_profile")
    if existing:
        return existing

    # Opt-in only: allow auto-selecting a default profile for demo/test setups.
    # Default is OFF to keep logout semantics correct and predictable.
    if os.environ.get("HRV_AUTO_SELECT_DEFAULT_PROFILE", "0").strip() == "1":
        try:
            db = get_database()
            users = db.list_users()
            if not users:
                return None
            for user in users:
                full_name = (user.full_name or "").lower()
                username = (user.username or "").lower()
                if "malpica" in full_name or "diego" in full_name or "diego" in username:
                    st.session_state["current_user_profile"] = user
                    st.session_state["current_user_id"] = user.user_id
                    return user
            if len(users) == 1:
                st.session_state["current_user_profile"] = users[0]
                st.session_state["current_user_id"] = users[0].user_id
                return users[0]
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Unable to resolve active profile: %s", exc)
    return None


def _build_analysis_settings(
    *,
    window: str,
    step: str,
    min_rr: int,
    max_windows: int,
    apply_clean: bool,
    method: str,
    max_dev: float,
    median_win: int,
    psd_method: str,
    fast_windowing: bool,
    high_compute: bool,
    apply_dev: bool,
    dev_metrics: Sequence[str],
    covariate_enabled: bool,
    covariate_age: Optional[int],
    covariate_sex: Optional[str],
    covariate_bmi: Optional[float],
    covariate_exercise: Optional[str],
) -> Dict[str, Any]:
    """Build a serializable settings payload for persistence."""
    return {
        "window": window,
        "step": step,
        "min_rr": int(min_rr),
        "max_windows": int(max_windows),
        "apply_clean": bool(apply_clean),
        "method": str(method),
        "max_dev": float(max_dev),
        "median_win": int(median_win),
        "psd_method": str(psd_method),
        "fast_windowing": bool(fast_windowing),
        "high_compute": bool(high_compute),
        "apply_dev": bool(apply_dev),
        "dev_metrics": list(dev_metrics),
        "covariate_enabled": bool(covariate_enabled),
        "covariate_age": int(covariate_age) if covariate_age is not None else None,
        "covariate_sex": str(covariate_sex) if covariate_sex is not None else None,
        "covariate_bmi": float(covariate_bmi) if covariate_bmi is not None else None,
        "covariate_exercise": (
            str(covariate_exercise) if covariate_exercise is not None else None
        ),
    }


def _analysis_settings_match(
    stored: Mapping[str, Any], current: Mapping[str, Any]
) -> bool:
    """Return True when stored analysis settings are compatible with current ones."""
    try:
        for key, cur_val in current.items():
            if key not in stored:
                return False
            stored_val = stored[key]
            if isinstance(cur_val, float):
                if not np.isclose(float(stored_val), float(cur_val), rtol=1e-6, atol=1e-6):
                    return False
            else:
                if str(stored_val) != str(cur_val):
                    return False
        return True
    except Exception:
        return False


def _persist_raw_uploads(
    logger: logging.Logger, profile: Any, uploads: Dict[str, UploadedRR]
) -> None:
    """Persist raw RR uploads immediately for the active profile."""
    user_id, display_name = _get_user_identity(profile)
    if user_id is None or not uploads:
        return
    try:
        manager = create_user_manager()
        manager.set_current_user(
            user_id=user_id, name=display_name or "User", create_if_missing=True
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Skipping raw RR persistence; user manager unavailable: %s", exc)
        return

    for name, up in uploads.items():
        try:
            rec_date = (
                up.recording_start_utc.date()
                if isinstance(up.recording_start_utc, pd.Timestamp)
                else parse_filename_date(name)
            )
            manager.store_rr_intervals(
                up.rr_ms,
                filename=name,
                recording_date=rec_date or date.today(),
                overwrite=False,
            )
        except FileExistsError:
            continue
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Unable to store RR file %s: %s", name, exc)


def _persist_analysis_results(
    logger: logging.Logger,
    profile: Any,
    uploads: Dict[str, UploadedRR],
    file_hash_map: Dict[str, str],
    multi_results_df: pd.DataFrame,
    windowed_df: pd.DataFrame,
    analysis_settings: Dict[str, Any],
) -> None:
    """Persist raw uploads and computed metrics for the active user."""
    user_id, display_name = _get_user_identity(profile)
    if user_id is None or multi_results_df.empty:
        return
    try:
        db = get_database()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Skipping persistence; database unavailable: %s", exc)
        return
    try:
        manager = create_user_manager()
        manager.set_current_user(user_id=user_id, name=display_name or "User", create_if_missing=True)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Skipping file persistence; user manager unavailable: %s", exc)
        manager = None

    settings_json = json.dumps(analysis_settings, default=str)

    for _, row in multi_results_df.iterrows():
        source = str(row.get("source", "unknown"))
        up = uploads.get(source)
        file_hash = file_hash_map.get(source)
        timepoint_id = st.session_state.get(f"longitudinal_timepoint_id:{user_id}")
        recording_start_iso = None
        recording_date_iso = datetime.now(timezone.utc).date().isoformat()
        recording_duration_min = float(row.get("recording_duration_minutes", 0.0)) if "recording_duration_minutes" in row else None
        artifact_pct = None
        if up is not None and up.qc_summary:
            artifact_pct = float(up.qc_summary.get("flagged_pct", 0.0))
        if up is not None and isinstance(up.recording_start_utc, pd.Timestamp):
            ts = up.recording_start_utc
            if ts.tzinfo is None or ts.tzinfo.utcoffset(ts) is None:
                ts = ts.tz_localize(timezone.utc)
            else:
                ts = ts.tz_convert(timezone.utc)
            recording_start_iso = ts.isoformat()
            recording_date_iso = ts.date().isoformat()

        measurement = HRVMeasurement(
            measurement_id=str(uuid.uuid4()),
            user_id=user_id,
            measurement_date=recording_date_iso,
            timepoint_id=timepoint_id,
            device_name="RR Upload",
            source_file=source,
            file_hash=file_hash,
            recording_start_utc=recording_start_iso,
            recording_duration_min=recording_duration_min,
            recording_context=None,
            body_position=None,
            mean_rr_ms=float(row.get("mean_nni", np.nan)) if "mean_nni" in row else None,
            sdnn_ms=float(row.get("sdnn", np.nan)) if "sdnn" in row else None,
            rmssd_ms=float(row.get("rmssd", np.nan)) if "rmssd" in row else None,
            pnn50_pct=float(row.get("pnn50", np.nan)) if "pnn50" in row else None,
            mean_hr_bpm=float(row.get("mean_hr", np.nan)) if "mean_hr" in row else None,
            sdhr_bpm=float(row.get("std_hr", np.nan)) if "std_hr" in row else None,
            vlf_power_ms2=float(row.get("vlf_power", np.nan)) if "vlf_power" in row else None,
            lf_power_ms2=float(row.get("lf_power", np.nan)) if "lf_power" in row else None,
            hf_power_ms2=float(row.get("hf_power", np.nan)) if "hf_power" in row else None,
            lf_hf_ratio=float(row.get("lf_hf_ratio", np.nan)) if "lf_hf_ratio" in row else None,
            total_power_ms2=float(row.get("total_power", np.nan)) if "total_power" in row else None,
            sd1_ms=float(row.get("sd1", np.nan)) if "sd1" in row else None,
            sd2_ms=float(row.get("sd2", np.nan)) if "sd2" in row else None,
            dfa_alpha1=float(row.get("dfa_alpha1", np.nan)) if "dfa_alpha1" in row else None,
            dfa_alpha2=float(row.get("dfa_alpha2", np.nan)) if "dfa_alpha2" in row else None,
            sample_entropy=float(row.get("sampen", np.nan)) if "sampen" in row else None,
            stress_index=float(row.get("baevsky_stress_index", np.nan)) if "baevsky_stress_index" in row else None,
            parasympathetic_index=float(row.get("parasympathetic_index", np.nan)) if "parasympathetic_index" in row else None,
            hrv_score=float(row.get("hrv_score", np.nan)) if "hrv_score" in row else None,
            rr_intervals_json=json.dumps(up.rr_ms.tolist()) if up is not None else None,
            artifact_percentage=artifact_pct,
            quality_score=None,
            notes=None,
            analysis_settings_json=settings_json,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            db.save_hrv_measurement(measurement)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to persist HRV measurement for %s: %s", source, exc)
        if manager is not None and up is not None:
            try:
                rec_date_obj = datetime.fromisoformat(recording_date_iso).date()
            except ValueError:
                rec_date_obj = date.today()
            try:
                manager.store_rr_intervals(
                    up.rr_ms,
                    filename=source,
                    recording_date=rec_date_obj,
                    overwrite=True,
                )
            except FileExistsError:
                pass
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Unable to store RR file for %s: %s", source, exc)
            # Persist analysis payload for reuse
            try:
                source_windowed = windowed_df[windowed_df["source"] == source] if not windowed_df.empty else pd.DataFrame()
                payload = {
                    "source": source,
                    "file_hash": file_hash,
                    "analysis_settings": analysis_settings,
                    "multi_results": json.loads(pd.DataFrame([row]).to_json(orient="records"))[0],
                    "windowed_df": source_windowed.to_dict(orient="list") if not source_windowed.empty else {},
                    "recording_start_utc": recording_start_iso,
                }
                manager.store_hrv_results(
                    payload,
                    recording_date=rec_date_obj,
                    source_file=source,
                    file_hash=file_hash or "",
                )
                # Mirror cached payload into SQLite for per-user availability across sessions.
                try:
                    db.save_hrv_analysis_cache(
                        user_id=user_id,
                        file_hash=str(file_hash or ""),
                        analysis_settings=analysis_settings,
                        payload=payload,
                        source_file=source,
                        recording_date=rec_date_obj.isoformat(),
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    logger.debug("Unable to persist HRV analysis cache to DB for %s: %s", source, exc)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Unable to store analysis payload for %s: %s", source, exc)

@st.cache_data(ttl=30, max_entries=2, show_spinner=False)
def _list_library_rr_files() -> Dict[str, List[Dict[str, Any]]]:
    """List all stored RR files from all user profiles.
    
    Returns:
        Dictionary mapping user display names to lists of file info dicts.
        Each file info contains: name, path, date, size_kb.
    """
    from user_data_manager import parse_filename_date
    
    result: Dict[str, List[Dict[str, Any]]] = {}

    # Mission-scoped storage: crew/<Mission>/subjects/<user_id>/rr_intervals
    from user_data_manager import get_default_data_root

    project_root = Path(__file__).resolve().parents[1]
    legacy_root = project_root / "data"
    base_paths = [get_default_data_root()]
    if legacy_root.exists():
        base_paths.append(legacy_root)

    max_users = 2000
    scanned_users = 0

    for base_path in base_paths:
        if not base_path.exists():
            continue

        # Get all user directories
        try:
            user_dirs = [d for d in base_path.iterdir() if d.is_dir()]
        except OSError:
            continue

        for user_dir in user_dirs:
            scanned_users += 1
            if scanned_users > max_users:
                break

            rr_dir = user_dir / "rr_intervals"
            if not rr_dir.exists():
                continue

            try:
                files = sorted(
                    rr_dir.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True
                )
            except OSError:
                continue

            if not files:
                continue

            # Try to get display name from user_info.json
            user_info_file = user_dir / "user_info.json"
            display_name = user_dir.name  # Default to folder name
            try:
                if user_info_file.exists():
                    import json

                    with open(user_info_file, "r", encoding="utf-8") as f:
                        info = json.load(f)
                        display_name = (
                            info.get("full_name")
                            or info.get("username")
                            or user_dir.name
                        )
            except Exception:
                pass

            file_list: List[Dict[str, Any]] = []
            for f in files:
                try:
                    stat = f.stat()
                    parsed_date = parse_filename_date(f.name)
                    file_list.append(
                        {
                            "name": f.name,
                            "path": str(f),
                            "date": parsed_date.isoformat() if parsed_date else None,
                            "size_kb": stat.st_size / 1024,
                            "mtime": stat.st_mtime,
                            "user_id": user_dir.name,
                        }
                    )
                except OSError:
                    continue

            if file_list:
                if display_name in result:
                    result[display_name].extend(file_list)
                else:
                    result[display_name] = file_list
    
    return result


def _render_library_loader() -> Dict[str, UploadedRR]:
    """Render the 'Load from Library' expander in the sidebar.
    
    Returns:
        Dictionary of loaded RR data from library files.
    """
    out: Dict[str, UploadedRR] = {}
    
    # Pre-check if library has files (avoid rendering expander if empty)
    library_files = _list_library_rr_files()
    if not library_files:
        # Show collapsed hint instead of full expander
        st.sidebar.caption("📚 *Library empty — upload files to save them*")
        return out
    
    with st.sidebar.expander("📚 Load from Library", expanded=False):
        st.caption(
            "Load previously saved RR recordings from user profiles. "
            "These files are already stored and can be used for analysis without re-uploading."
        )
        
        # Build flat list of all files with user context
        all_files: List[Dict[str, Any]] = []
        for user_name, files in library_files.items():
            for f in files:
                f["user_display"] = user_name
                all_files.append(f)
        
        # Sort by modification time (most recent first)
        all_files.sort(key=lambda x: x.get("mtime", 0), reverse=True)
        
        # Create display options
        options = [
            f"{f['name']} ({f['user_display']})" for f in all_files
        ]
        
        if not options:
            st.info("No RR files available in the library.")
            return out
        
        st.markdown(f"**{len(options)} file(s) available**")
        
        # Multi-select for files - use session state key with stable prefix
        select_key = "library_file_select_v2"
        
        # Ensure default doesn't exceed available options
        current_selection = st.session_state.get(select_key, [])
        valid_selection = [s for s in current_selection if s in options]
        if current_selection != valid_selection:
            st.session_state[select_key] = valid_selection
        
        selected = st.multiselect(
            "Select files to load",
            options=options,
            default=None,  # Use None instead of [] to avoid index issues
            key=select_key,
            help="Select one or more files to load into the analysis workspace.",
        )
        
        if not selected:
            st.info("👆 Select files above, then click Load.")
            return out
        
        # Map selections back to file info safely
        selected_files = []
        for s in selected:
            try:
                idx = options.index(s)
                selected_files.append(all_files[idx])
            except (ValueError, IndexError):
                continue
        
        if not selected_files:
            return out
        
        col1, col2 = st.columns(2)
        with col1:
            load_clicked = st.button(
                "📥 Load files",
                key="library_load_btn",
                use_container_width=True,
            )
        with col2:
            load_run_clicked = st.button(
                "🚀 Load + Analyze",
                key="library_load_run_btn",
                type="primary",
                use_container_width=True,
            )
        
        if load_clicked or load_run_clicked:
            # Clear previous state to ensure fresh load
            st.session_state.pop("_persisted_uploads", None)
            st.session_state.pop("_hrv_cached_datasets", None)
            st.session_state.pop("_hrv_cached_windowed_df", None)
            st.session_state.pop("_hrv_cached_multi_results_df", None)
            st.session_state.pop("_hrv_cached_meta_rows", None)
            st.session_state.pop("_hrv_cached_meta_rows_for_context", None)
            st.session_state.pop("_hrv_cached_ml_summary_df", None)
            st.session_state.pop("_hrv_cached_episodes_df", None)
            st.session_state.pop("hrv_analysis_complete_signature", None)
            st.session_state.pop("hrv_analysis_signature", None)
            
            # Queue files for loading via session state
            queue_payload: List[Dict[str, Any]] = []
            for f in selected_files:
                parsed_date = None
                if f.get("date"):
                    try:
                        parsed_date = date.fromisoformat(f["date"])
                    except (ValueError, TypeError):
                        parsed_date = date.today()
                else:
                    parsed_date = date.today()
                
                start_ts = datetime.combine(
                    parsed_date, datetime.min.time(), tzinfo=timezone.utc
                )
                queue_payload.append({
                    "path": f["path"],
                    "name": f["name"],
                    "recording_start": start_ts.isoformat(),
                })
            
            st.session_state["queued_rr_filepaths"] = queue_payload
            
            if load_run_clicked:
                st.session_state["auto_run_hrv_analysis"] = True
                st.success(f"Loading {len(selected_files)} file(s) and starting analysis...")
            else:
                st.success(f"Loaded {len(selected_files)} file(s) into workspace.")
            
            st.rerun()
    
    return out


def _save_uploaded_files_to_library(
    files_to_save: Dict[str, UploadedRR],
    user_id: str,
) -> int:
    """Save uploaded RR files to the user's library.
    
    Args:
        files_to_save: Dictionary of UploadedRR objects to save.
        user_id: User ID to save files under.
        
    Returns:
        Number of files successfully saved.
    """
    saved_count = 0
    from user_data_manager import create_user_manager, parse_filename_date

    try:
        manager = create_user_manager()
        manager.set_current_user(user_id=user_id, name="User", create_if_missing=True)
    except Exception:
        return 0

    for name, uploaded in files_to_save.items():
        if uploaded.rr_ms is None or len(uploaded.rr_ms) < 10:
            continue

        rec_date = None
        if uploaded.recording_start_utc is not None and isinstance(
            uploaded.recording_start_utc, pd.Timestamp
        ):
            rec_date = uploaded.recording_start_utc.date()
        if rec_date is None:
            rec_date = parse_filename_date(name)
        if rec_date is None:
            rec_date = date.today()

        try:
            manager.store_rr_intervals(
                uploaded.rr_ms,
                filename=name,
                recording_date=rec_date,
                overwrite=False,
            )
            saved_count += 1
        except FileExistsError:
            continue
        except Exception:
            continue
    
    return saved_count


def _upload_section() -> Dict[str, UploadedRR]:
    """
    Handle RR interval file uploads with session state caching.
    
    Uses hash-based caching to avoid re-parsing files on every Streamlit rerun.
    Files are only re-parsed if their content changes.
    
    Returns:
        Dictionary mapping filename to UploadedRR objects.
    """
    st.sidebar.header("Upload RR (.txt)")
    files = st.sidebar.file_uploader(
        "Select one or more Polar-like RR .txt files (one ms value per line)",
        type=["txt"],
        accept_multiple_files=True,
    )
    out: Dict[str, UploadedRR] = {}
    if not files:
        # Clear cached uploads if no files selected
        if "uploaded_rr_cache" in st.session_state:
            st.session_state["uploaded_rr_cache"] = {}
        return out
    
    # Initialize upload cache in session state
    if "uploaded_rr_cache" not in st.session_state:
        st.session_state["uploaded_rr_cache"] = {}
    
    upload_cache = st.session_state["uploaded_rr_cache"]

    # PERF: Track active cache keys without re-reading file bytes twice.
    current_keys: set[str] = set()

    for f in files:
        # Compute hash of file content for cache invalidation
        file_content = f.getvalue()
        file_hash = _compute_file_hash(file_content)
        cache_key = f"{f.name}_{file_hash}"
        current_keys.add(cache_key)

        # Check if we have a valid cached entry
        cached = upload_cache.get(cache_key)
        if isinstance(cached, UploadedRR):
            # Use cached object (fast path; avoids DataFrame reconstruction)
            out[f.name] = cached
            continue

        if isinstance(cached, dict):
            # Legacy cache format: convert once, then overwrite with fast object cache.
            out[f.name] = UploadedRR(
                name=f.name,
                rr_ms=np.array(cached.get("rr_ms", [])),
                df=pd.DataFrame(cached.get("df_dict", {})),
                recording_start_utc=(
                    pd.Timestamp(cached["recording_start_utc"])
                    if cached.get("recording_start_utc")
                    else None
                ),
            )
            # Restore timestamp column as datetime
            if "timestamp" in out[f.name].df.columns:
                out[f.name].df["timestamp"] = pd.to_datetime(
                    out[f.name].df["timestamp"], utc=True
                )
            upload_cache[cache_key] = out[f.name]
            continue

        # Parse file (cache miss)
        content = file_content.decode("utf-8", errors="ignore")
        rr = load_rr_intervals_from_text(f.name, content)
        start_ts, precise = _infer_recording_start(f.name)
        df = _to_dataframe(f.name, rr, start_ts=start_ts)

        out[f.name] = UploadedRR(
            name=f.name,
            rr_ms=rr,
            df=df,
            recording_start_utc=start_ts,
        )

        # Store in cache as the object to avoid expensive DataFrame rebuilds
        upload_cache[cache_key] = out[f.name]

        if not precise:
            st.sidebar.warning(
                f"'{f.name}' does not encode a recording start timestamp. "
                f"Defaulting to {start_ts.strftime('%Y-%m-%d %H:%M UTC')}."
            )

    # Clean up old cache entries (files no longer uploaded)
    stale_keys = [k for k in upload_cache if k not in current_keys]
    for k in stale_keys:
        del upload_cache[k]
    
    # =========================================================================
    # SAVE FOR LATER - Allow users to save uploaded files to their library
    # =========================================================================
    if out:
        st.sidebar.markdown("---")
        
        # Check if user is logged in
        active_user = st.session_state.get("current_user_profile")
        user_id = None
        user_display = None
        
        if active_user:
            if hasattr(active_user, "user_id"):
                user_id = active_user.user_id
                user_display = getattr(active_user, "full_name", None) or getattr(active_user, "username", user_id)
            elif isinstance(active_user, dict):
                user_id = active_user.get("user_id")
                user_display = active_user.get("full_name") or active_user.get("username") or user_id
        
        if user_id:
            # Track which files have been saved in this session
            saved_files_key = "_sidebar_saved_files"
            if saved_files_key not in st.session_state:
                st.session_state[saved_files_key] = set()
            
            # Filter out files already saved
            unsaved_files = {
                name: uploaded for name, uploaded in out.items()
                if name not in st.session_state[saved_files_key]
            }
            
            if unsaved_files:
                # Use a button instead of checkbox to avoid rapid state changes
                if st.sidebar.button(
                    f"💾 Save {len(unsaved_files)} file(s) to library",
                    key="sidebar_save_to_library_btn",
                    help=f"Save uploaded files to {user_display}'s profile for future analysis.",
                ):
                    saved_count = _save_uploaded_files_to_library(unsaved_files, user_id)
                    if saved_count > 0:
                        st.sidebar.success(f"✅ Saved {saved_count} file(s) to library!")
                        # Track saved files
                        st.session_state[saved_files_key].update(unsaved_files.keys())
                        # Refresh cached library listing so the sidebar loader updates immediately.
                        try:
                            _list_library_rr_files.clear()  # type: ignore[attr-defined]
                        except Exception:  # pragma: no cover - defensive
                            pass
                    else:
                        st.sidebar.info("Files already exist in library or could not be saved.")
            else:
                st.sidebar.caption("✅ All files saved to library.")
        else:
            st.sidebar.caption(
                "💡 Log in to a profile to save files for later."
            )
    
    return out


def _device_import_section() -> Dict[str, UploadedRR]:
    """Handle imports from ActiGraph GT3X and Somfit Pro devices.
    
    Returns:
        Dictionary of uploaded RR data from device imports.
    """
    out: Dict[str, UploadedRR] = {}
    
    # ActiGraph GT3X Import Section
    if ACTIGRAPH_AVAILABLE:
        with st.sidebar.expander("📊 ActiGraph GT3X Import", expanded=False):
            st.caption("Import accelerometer data from ActiGraph GT3X/GT3X+ devices")
            actigraph_file = st.file_uploader(
                "Select ActiGraph file (.gt3x, .agd, .csv)",
                type=["gt3x", "agd", "csv"],
                key="actigraph_uploader",
            )
            import_actigraph_clicked = st.button(
                "Import ActiGraph data",
                key="actigraph_import_button",
                disabled=actigraph_file is None,
                help="Runs once when clicked (prevents re-processing on every rerun).",
            )
            if import_actigraph_clicked and actigraph_file is not None:
                with st.spinner("Importing ActiGraph data..."):
                    tmp_path: Optional[Path] = None
                    try:
                        import tempfile
                        with tempfile.NamedTemporaryFile(
                            delete=False,
                            suffix=f".{actigraph_file.name.split('.')[-1]}",
                        ) as tmp:
                            tmp.write(actigraph_file.getvalue())
                            tmp_path = Path(tmp.name)

                        actigraph_data = import_actigraph_data(
                            tmp_path,
                            use_pygt3x=True,
                            compute_counts=True,
                            classify_intensity=True,
                            classify_sleep=True,
                        )

                        # Store in session state for use in other tabs
                        st.session_state["actigraph_data"] = actigraph_data

                        # Quality check
                        quality = check_actigraph_data_quality(actigraph_data)

                        st.success(
                            f"✅ Loaded ActiGraph data: {quality['raw_samples']:,} samples"
                        )
                        st.caption(
                            f"Device: {quality['device_type']} @ {quality['sample_rate']} Hz"
                        )

                        if quality["warnings"]:
                            for warn in quality["warnings"]:
                                st.warning(warn)

                        # If heart rate data available, convert to RR intervals (approximation)
                        if not actigraph_data.heart_rate.empty:
                            hr_df = actigraph_data.heart_rate
                            rr_ms = (60000.0 / hr_df["heart_rate"].values).astype(float)
                            valid_mask = (rr_ms >= 300) & (rr_ms <= 2000)
                            rr_ms = rr_ms[valid_mask]

                            if len(rr_ms) > 0:
                                start_ts = pd.Timestamp(hr_df["timestamp"].iloc[0])
                                if start_ts.tzinfo is None or start_ts.tzinfo.utcoffset(start_ts) is None:
                                    start_ts = start_ts.tz_localize("UTC")
                                else:
                                    start_ts = start_ts.tz_convert("UTC")
                                df = _to_dataframe(
                                    f"actigraph_{actigraph_file.name}",
                                    rr_ms,
                                    start_ts=start_ts,
                                )
                                out[f"actigraph_{actigraph_file.name}"] = UploadedRR(
                                    name=f"actigraph_{actigraph_file.name}",
                                    rr_ms=rr_ms,
                                    df=df,
                                    recording_start_utc=start_ts,
                                )
                                st.info(
                                    f"📈 Extracted {len(rr_ms):,} RR intervals from HR data"
                                )
                        else:
                            st.info("No heart-rate channel found; RR extraction skipped.")
                    except Exception as exc:  # pragma: no cover - UI defensive
                        log_exception(_LOGGER, "Failed to import ActiGraph data", exc)
                        st.error(f"Failed to import ActiGraph data: {exc}")
                    finally:
                        if tmp_path is not None:
                            try:
                                tmp_path.unlink(missing_ok=True)
                            except OSError as exc:
                                _LOGGER.debug(
                                    "Unable to delete temp ActiGraph file %s: %s",
                                    tmp_path,
                                    exc,
                                )
            elif actigraph_file is not None:
                st.caption("Ready to import. Click **Import ActiGraph data** to process once.")
    else:
        with st.sidebar.expander("📊 ActiGraph GT3X Import", expanded=False):
            st.warning("ActiGraph import not available. Install pygt3x: `pip install pygt3x`")
    
    # Somfit Pro Import Section
    if SOMFIT_AVAILABLE:
        with st.sidebar.expander("😴 Somfit Pro Import", expanded=False):
            st.caption("Import sleep study data from Compumedics Somfit/Somfit Pro")
            somfit_file = st.file_uploader(
                "Select Somfit file (.edf, .csv)",
                type=["edf", "csv"],
                key="somfit_uploader",
            )
            somfit_xml = st.file_uploader(
                "Optional: Scoring annotations (.xml)",
                type=["xml"],
                key="somfit_xml_uploader",
            )
            
            import_somfit_clicked = st.button(
                "Import Somfit data",
                key="somfit_import_button",
                disabled=somfit_file is None,
                help="Runs once when clicked (prevents re-processing on every rerun).",
            )
            if import_somfit_clicked and somfit_file is not None:
                with st.spinner("Importing Somfit data..."):
                    tmp_path = None
                    xml_path = None
                    try:
                        import tempfile
                        with tempfile.NamedTemporaryFile(
                            delete=False,
                            suffix=f".{somfit_file.name.split('.')[-1]}",
                        ) as tmp:
                            tmp.write(somfit_file.getvalue())
                            tmp_path = Path(tmp.name)

                        if somfit_xml is not None:
                            with tempfile.NamedTemporaryFile(
                                delete=False,
                                suffix=".xml",
                            ) as tmp_xml:
                                tmp_xml.write(somfit_xml.getvalue())
                                xml_path = Path(tmp_xml.name)

                        somfit_data = import_somfit_data(
                            tmp_path,
                            annotation_path=xml_path,
                            use_pyedflib=True,
                            extract_rr=True,
                        )

                        # Store in session state
                        st.session_state["somfit_data"] = somfit_data

                        quality = check_somfit_data_quality(somfit_data)

                        st.success(
                            f"✅ Loaded Somfit data: {quality['recording_duration_hours']:.1f} hours"
                        )
                        st.caption(f"Signals: {quality['num_signals']}")

                        if not somfit_data.staging.epochs.empty:
                            staging = somfit_data.staging
                            st.markdown(
                                f"""
                        **Sleep Architecture:**
                        - TST: {staging.total_sleep_time:.0f} min
                        - Efficiency: {staging.sleep_efficiency:.1f}%
                        - WASO: {staging.waso:.0f} min
                        """
                            )

                        if quality["warnings"]:
                            for warn in quality["warnings"]:
                                if "Note:" in warn:
                                    st.info(warn)
                                else:
                                    st.warning(warn)

                        # Extract RR intervals for HRV analysis
                        if not somfit_data.rr_intervals.empty:
                            rr_df = somfit_data.rr_intervals
                            rr_ms = rr_df["rr_interval_ms"].values.astype(float)

                            if len(rr_ms) > 0:
                                if "timestamp" in rr_df.columns:
                                    start_ts = pd.Timestamp(rr_df["timestamp"].iloc[0])
                                else:
                                    start_ts = (
                                        pd.Timestamp(somfit_data.metadata.start_time)
                                        if somfit_data.metadata.start_time
                                        else pd.Timestamp.now(tz=timezone.utc)
                                    )
                                if start_ts.tzinfo is None or start_ts.tzinfo.utcoffset(start_ts) is None:
                                    start_ts = start_ts.tz_localize("UTC")
                                else:
                                    start_ts = start_ts.tz_convert("UTC")

                                df = _to_dataframe(
                                    f"somfit_{somfit_file.name}",
                                    rr_ms,
                                    start_ts=start_ts,
                                )
                                out[f"somfit_{somfit_file.name}"] = UploadedRR(
                                    name=f"somfit_{somfit_file.name}",
                                    rr_ms=rr_ms,
                                    df=df,
                                    recording_start_utc=start_ts,
                                )
                                st.info(f"📈 Extracted {len(rr_ms):,} RR intervals")
                        else:
                            st.info("No RR interval channel found; RR extraction skipped.")
                    except Exception as exc:  # pragma: no cover - UI defensive
                        log_exception(_LOGGER, "Failed to import Somfit data", exc)
                        st.error(f"Failed to import Somfit data: {exc}")
                    finally:
                        if tmp_path is not None:
                            try:
                                tmp_path.unlink(missing_ok=True)
                            except OSError as exc:
                                _LOGGER.debug(
                                    "Unable to delete temp Somfit file %s: %s",
                                    tmp_path,
                                    exc,
                                )
                        if xml_path is not None:
                            try:
                                xml_path.unlink(missing_ok=True)
                            except OSError as exc:
                                _LOGGER.debug(
                                    "Unable to delete temp Somfit XML %s: %s",
                                    xml_path,
                                    exc,
                                )
            elif somfit_file is not None:
                st.caption("Ready to import. Click **Import Somfit data** to process once.")
    else:
        with st.sidebar.expander("😴 Somfit Pro Import", expanded=False):
            st.warning("Somfit import not available. Install pyedflib: `pip install pyedflib`")
    
    return out


def _echarts_line_series(
    name: str, x_vals: List, y_vals: List, smooth: bool = True
) -> Dict:
    return {
        "name": name,
        "type": "line",
        "showSymbol": False,
        "smooth": smooth,
        "data": [[x, y] for x, y in zip(x_vals, y_vals)],
    }


def _echarts_scatter_series(
        name: str,
        x_vals: np.ndarray,
        y_vals: np.ndarray) -> Dict:
    points: List[List[Any]] = []
    for x, y in zip(x_vals, y_vals):
        if isinstance(x, (int, float, np.number)):
            x_value: Any = float(x)
        else:
            x_value = str(x)
        points.append([x_value, float(y)])
    return {
        "name": name,
        "type": "scatter",
        "symbolSize": 4,
        "data": points,
    }


def _prepare_rr_series(
    upload: UploadedRR, use_clean: bool
) -> Tuple[pd.Series, pd.Series]:
    """Return aligned timestamp and RR interval series for a dataset."""
    if upload.df.empty:
        raise ValueError(f"Dataset '{upload.name}' contains no RR samples.")
    column = (
        "rr_intervals_ms_clean"
        if (use_clean and "rr_intervals_ms_clean" in upload.df.columns)
        else "rr_intervals_ms"
    )
    if column not in upload.df.columns:
        raise ValueError(
            f"Column '{column}' not available for dataset '{upload.name}'."
        )
    timestamps = pd.to_datetime(upload.df["timestamp"], errors="coerce")
    rr_ms = pd.to_numeric(upload.df[column], errors="coerce")
    mask = timestamps.notna() & rr_ms.notna()
    if not mask.any():
        raise ValueError(
            f"No valid RR samples found for dataset '{upload.name}'."
        )
    return timestamps.loc[mask], rr_ms.loc[mask]


def _parse_window_seconds(raw_value: str, label: str) -> Tuple[float, float]:
    """Parse a window definition string into a (start, end) tuple of seconds."""
    if not raw_value.strip():
        raise ValueError(f"{label} cannot be empty.")
    clean = raw_value.strip()
    for sep in (",", ";"):
        clean = clean.replace(sep, " ")
    parts: List[str] = []
    for token in clean.split():
        if "-" in token:
            subparts = [segment for segment in token.split("-") if segment]
            parts.extend(subparts)
        else:
            parts.append(token)
    if len(parts) != 2:
        raise ValueError(
            f"{label} must specify exactly two numbers (start and end seconds).")
    try:
        start = float(parts[0])
        end = float(parts[1])
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"{label} must contain numeric values.") from exc
    if not np.isfinite(start) or not np.isfinite(end):
        raise ValueError(f"{label} must contain finite values.")
    if end <= start:
        raise ValueError(f"{label} end must be greater than start.")
    return start, end


def _parse_float(raw_value: float | int | str, label: str) -> float:
    """Parse a float input ensuring finiteness."""
    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError(f"{label} must be a number.") from exc
    if not np.isfinite(value):
        raise ValueError(f"{label} must be finite.")
    return value


def _render_dataset_info_header(
    datasets: Dict[str, "UploadedRR"],
    *,
    title: str = "Files Being Analyzed",
) -> None:
    """Display a prominent header showing which files are being analyzed with dates."""
    if not datasets:
        return
    items: List[str] = []
    for name, up in datasets.items():
        ts = up.recording_start_utc
        if ts is not None and isinstance(ts, pd.Timestamp):
            date_str = ts.strftime("%Y-%m-%d %H:%M")
        else:
            date_str = "Unknown date"
        duration_min = len(up.rr_ms) * (np.mean(up.rr_ms) / 60000.0) if up.rr_ms is not None and len(up.rr_ms) > 0 else 0
        items.append(f"**{name}** — {date_str} ({duration_min:.1f} min, {len(up.rr_ms):,} beats)")
    with st.expander(f"📂 {title} ({len(datasets)} file{'s' if len(datasets) != 1 else ''})", expanded=True):
        for item in items:
            st.markdown(f"• {item}")


def _select_rr_files_for_tab(
    datasets: Dict[str, UploadedRR],
    *,
    tab_key: str,
    label: str,
) -> Dict[str, UploadedRR]:
    """Return the subset of datasets selected for a visualization tab."""
    if not datasets:
        return {}
    options = list(datasets.keys())
    active_key = f"{tab_key}_active_files"
    picker_key = f"{tab_key}_file_picker"
    # Initialize selected lists and drop files no longer present
    current_active = [
        name for name in st.session_state.get(active_key, options) if name in options
    ]
    if not current_active:
        current_active = options
    picker_selection = st.session_state.get(picker_key)
    if picker_selection is None:
        st.session_state[picker_key] = current_active
    else:
        filtered = [name for name in picker_selection if name in options]
        st.session_state[picker_key] = filtered or current_active
    with st.expander(f"📂 Load RR files for {label}", expanded=False):
        st.caption(
            "Select which uploaded recordings to load into this analysis tab. "
            "This does not modify the sidebar uploads; it only filters the "
            "visualizations shown below."
        )
        selection = st.multiselect(
            "RR files ready for analysis",
            options=options,
            key=picker_key,
        )
        if st.button("Load selected files", key=f"{tab_key}_load_button"):
            st.session_state[active_key] = selection or []
            if selection:
                st.success(f"Loaded {len(selection)} file(s) for {label}.")
            else:
                st.warning("Select at least one file to analyze.")
    active_names = [
        name for name in st.session_state.get(active_key, current_active) if name in datasets
    ]
    if not active_names:
        return {}
    return {name: datasets[name] for name in active_names}


def _plot_rr_timeseries(
    datasets: Dict[str, UploadedRR],
    dev_windows: Optional[pd.DataFrame] = None,
    *,
    max_points: Optional[int] = None,
) -> None:
    series = []
    x_min: Optional[pd.Timestamp] = None
    x_max: Optional[pd.Timestamp] = None
    for name, up in datasets.items():
        if up.df.empty:
            continue
        # PERF: Avoid converting full columns to Python lists before downsampling.
        # For long recordings, list conversion dominates CPU time and can make the
        # Streamlit UI appear "faded / always running".
        ts_ser = up.df["timestamp"]
        if not ts_ser.empty:
            cur_min_raw = ts_ser.iloc[0]
            cur_max_raw = ts_ser.iloc[-1]
            cur_min = pd.to_datetime(cur_min_raw, errors="coerce")
            cur_max = pd.to_datetime(cur_max_raw, errors="coerce")
            if isinstance(cur_min, pd.Timestamp) and not pd.isna(cur_min):
                x_min = cur_min if (x_min is None or cur_min < x_min) else x_min
            if isinstance(cur_max, pd.Timestamp) and not pd.isna(cur_max):
                x_max = cur_max if (x_max is None or cur_max > x_max) else x_max

        n_rows = int(len(up.df))
        if max_points is not None and n_rows > max_points:
            idx = np.linspace(0, n_rows - 1, int(max_points), dtype=int)
            df_plot = up.df.iloc[idx]
        else:
            df_plot = up.df

        x = df_plot["timestamp"].astype(str).tolist()
        y = df_plot["rr_intervals_ms"].astype(float).tolist()
        ser = _echarts_line_series(f"{name} (raw)", x, y)
        # Add deviation markAreas per dataset if available
        if (
            dev_windows is not None
            and not dev_windows.empty
            and "dev_level" in dev_windows.columns
        ):
            sub = dev_windows[dev_windows["source"] == name]
            if not sub.empty:
                items = []
                for _, row in sub.iterrows():
                    start = row.get("start", None)
                    end = row.get("end", None)
                    level = str(row.get("dev_level", ""))
                    if pd.isna(start) or pd.isna(
                            end) or level not in ("yellow", "red"):
                        continue
                    color = (
                        "rgba(251,140,0,0.12)"
                        if level == "yellow"
                        else "rgba(229,57,53,0.12)"
                    )
                    items.append(
                        [
                            {
                                "xAxis": str(pd.to_datetime(start)),
                                "itemStyle": {"color": color},
                            },
                            {
                                "xAxis": str(pd.to_datetime(end)),
                                "itemStyle": {"color": color},
                            },
                        ]
                    )
                if items:
                    ser["markArea"] = {"silent": True, "data": items}
        series.append(ser)
        if "rr_intervals_ms_clean" in up.df.columns:
            # Use the same downsampling as the raw series to keep alignment.
            y_cl = df_plot["rr_intervals_ms_clean"].astype(float).tolist()
            series.append(
                {
                    **_echarts_line_series(f"{name} (cleaned)", x, y_cl),
                    "lineStyle": {"width": 2, "color": "#43a047"},
                }
            )
        if "artifact_flag" in up.df.columns:
            # Fix FutureWarning: convert to bool dtype first, then fill NaN with False
            mask = up.df["artifact_flag"].astype("boolean").fillna(False).to_numpy()
            if mask.any():
                timestamps_masked = up.df.loc[mask, "timestamp"]
                rr_masked = pd.to_numeric(
                    up.df.loc[mask, "rr_intervals_ms"], errors="coerce"
                )
                valid_mask = rr_masked.notna()
                if valid_mask.any():
                    xf = timestamps_masked.loc[valid_mask].astype(
                        str).to_numpy()
                    yf = rr_masked.loc[valid_mask].to_numpy(dtype=float)
                    series.append(
                        {
                            **_echarts_scatter_series(f"{name} artifacts", xf, yf),
                            "itemStyle": {"color": "#e53935"},
                            "symbolSize": 5,
                        }
                    )
    opt = {
        "title": {"text": "RR Intervals over Time", "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"top": 24},
        "grid": {"left": 32, "right": 16, "containLabel": True},
        "xAxis": {
            "type": "time",
            "boundaryGap": False,
            **({"min": str(x_min)} if x_min is not None else {}),
            **({"max": str(x_max)} if x_max is not None else {}),
        },
        "yAxis": {"type": "value", "name": "RR (ms)"},
        "dataZoom": [{"type": "inside"}, {"type": "slider", "left": 32, "right": 16}],
        "series": series,
    }
    render_echarts(opt, height_px=420, width="100%", config=EChartsConfig())


def _plot_hr_timeseries(
    datasets: Dict[str, UploadedRR],
    *,
    max_points: Optional[int] = None,
) -> None:
    """Plot heart rate time series with optional downsampling for performance."""
    series = []
    x_min: Optional[pd.Timestamp] = None
    x_max: Optional[pd.Timestamp] = None
    
    # Get max_points from performance settings if not specified
    if max_points is None and PERFORMANCE_UTILS_AVAILABLE:
        perf = get_performance_settings()
        max_points = perf.get("max_plot_points", 2000)
    
    for name, up in datasets.items():
        if up.df.empty:
            continue
        ts_ser = up.df["timestamp"]
        if not ts_ser.empty:
            cur_min_raw = ts_ser.iloc[0]
            cur_max_raw = ts_ser.iloc[-1]
            cur_min = pd.to_datetime(cur_min_raw, errors="coerce")
            cur_max = pd.to_datetime(cur_max_raw, errors="coerce")
            if isinstance(cur_min, pd.Timestamp) and not pd.isna(cur_min):
                x_min = cur_min if (x_min is None or cur_min < x_min) else x_min
            if isinstance(cur_max, pd.Timestamp) and not pd.isna(cur_max):
                x_max = cur_max if (x_max is None or cur_max > x_max) else x_max

        # PERF: Downsample BEFORE converting to Python lists.
        n_rows = int(len(up.df))
        if max_points is not None and n_rows > max_points:
            idx = np.linspace(0, n_rows - 1, int(max_points), dtype=int)
            df_plot = up.df.iloc[idx]
        else:
            df_plot = up.df

        x = df_plot["timestamp"].astype(str).tolist()
        y = df_plot["heart_rate [bpm]"].astype(float).tolist()
        
        series.append(_echarts_line_series(name, x, y))
    opt = {
        "title": {"text": "Heart Rate over Time", "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"top": 24},
        "grid": {"left": 32, "right": 16, "containLabel": True},
        "xAxis": {
            "type": "time",
            "boundaryGap": False,
            **({"min": str(x_min)} if x_min is not None else {}),
            **({"max": str(x_max)} if x_max is not None else {}),
        },
        "yAxis": {"type": "value", "name": "HR (bpm)"},
        "dataZoom": [{"type": "inside"}, {"type": "slider", "left": 32, "right": 16}],
        "series": series,
    }
    render_echarts(opt, height_px=420, width="100%", config=EChartsConfig())


def _plot_psd_overlay(
    datasets: Dict[str, UploadedRR],
    *,
    method: str,
    max_points: Optional[int] = None,
) -> None:
    """Plot PSD overlay with optional downsampling for performance."""
    series = []
    
    # Get max_points from performance settings if not specified
    if max_points is None and PERFORMANCE_UTILS_AVAILABLE:
        perf = get_performance_settings()
        max_points = perf.get("max_plot_points", 2000)
    
    for name, up in datasets.items():
        rr = up.rr_ms_clean if (up.rr_ms_clean is not None) else up.rr_ms
        f, p = _cached_psd(rr, method=str(method))
        if f.size == 0:
            continue
        
        # Downsample PSD if needed
        if max_points is not None and len(f) > max_points:
            idx = np.linspace(0, len(f) - 1, max_points).astype(int)
            f_ds = f[idx]
            p_ds = p[idx]
        else:
            f_ds = f
            p_ds = p
        
        series.append(
            {
                "name": f"{name}{' (cleaned)' if (up.rr_ms_clean is not None) else ''}",
                "type": "line",
                "showSymbol": False,
                "data": [[float(fi), float(pi)] for fi, pi in zip(f_ds, p_ds)],
            }
        )
    opt = {
        "title": {"text": f"PSD Overlay ({method.title()})", "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"top": 24},
        "grid": {"left": 32, "right": 16, "containLabel": True},
        "xAxis": {"type": "value", "name": "Frequency (Hz)", "boundaryGap": False},
        "yAxis": {"type": "log", "name": "PSD (ms²/Hz)"},
        "dataZoom": [{"type": "inside"}, {"type": "slider", "left": 32, "right": 16}],
        "series": series,
        "visualMap": [
            {
                "show": False,
                "type": "continuous",
                "seriesIndex": 0,
                "min": 0.0,
                "max": 0.4,
            }
        ],
        "graphic": [{"type": "group", "children": []}],
    }
    # Band overlays using dataZoom or markArea
    bands = {"VLF": (0.0033, 0.04), "LF": (0.04, 0.15), "HF": (0.15, 0.4)}
    mark_areas = []
    for label, (x0, x1) in bands.items():
        mark_areas.append(
            {
                "name": label,
                "itemStyle": {
                    "color": (
                        "rgba(180,180,180,0.15)"
                        if label == "VLF"
                        else (
                            "rgba(255,99,132,0.12)"
                            if label == "LF"
                            else "rgba(99,201,255,0.12)"
                        )
                    )
                },
                "label": {"show": True, "position": "insideTopLeft"},
                "data": [[{"xAxis": x0}, {"xAxis": x1}]],
            }
        )
    for s in series:
        s["markArea"] = {
            "silent": True,
            "data": [],
            "itemStyle": {
                "opacity": 1.0}}
    opt["series"] = series
    opt["markArea"] = mark_areas
    render_echarts(opt, height_px=420, width="100%", config=EChartsConfig())


def _plot_poincare(datasets: Dict[str, UploadedRR],
                   max_points: int = 5000) -> None:
    series = []
    for name, up in datasets.items():
        rr = up.rr_ms_clean if (up.rr_ms_clean is not None) else up.rr_ms
        if rr.size < 2:
            continue
        rr = rr[(rr >= 300.0) & (rr <= 2000.0)]
        if rr.size < 2:
            continue
        x = rr[:-1]
        y = rr[1:]
        if x.size > max_points:
            idx = np.linspace(0, x.size - 1, max_points).astype(int)
            x = x[idx]
            y = y[idx]
        series.append(_echarts_scatter_series(name, x, y))
    opt = {
        "title": {"text": "Poincaré Plot (RRₙ vs RRₙ₊₁)", "left": "center"},
        "tooltip": {"trigger": "item"},
        "legend": {"top": 24},
        "grid": {"left": 32, "right": 16, "containLabel": True},
        "xAxis": {"type": "value", "name": "RRₙ (ms)", "boundaryGap": False},
        "yAxis": {"type": "value", "name": "RRₙ₊₁ (ms)"},
        "series": series,
    }
    render_echarts(opt, height_px=520, width="100%", config=EChartsConfig())


def _plot_spectrogram(datasets: Dict[str, UploadedRR]) -> None:
    # Show one spectrogram at a time (select box)
    names = list(datasets.keys())
    if not names:
        return
    sel = st.selectbox("Spectrogram dataset", names, index=0)
    up = datasets[sel]
    rr = up.rr_ms_clean if (up.rr_ms_clean is not None) else up.rr_ms
    # PERF: spectrogram is expensive; use cached computation and downsample before
    # building ECharts triplets to avoid "faded / always running" UI on long data.
    fxx, txx, Sxx = _cached_spectrogram(rr)
    if fxx.size == 0:
        st.info("Insufficient RR for spectrogram.")
        return
    # Restrict to 0–0.5 Hz for readability
    f_mask = fxx <= 0.5
    if not np.any(f_mask):
        st.info("Spectrogram has no content below 0.5 Hz for this dataset.")
        return
    fxx = fxx[f_mask]
    Sxx = Sxx[f_mask, :]

    # Downsample heatmap resolution (bounded) for browser performance
    max_f_bins = 128
    max_t_bins = 256
    if PERFORMANCE_UTILS_AVAILABLE:
        try:
            perf = get_performance_settings()
            # Reuse max_plot_points as a rough cap, split across axes.
            max_plot_points = int(perf.get("max_plot_points", 2000))
            max_f_bins = max(32, min(256, int(np.sqrt(max_plot_points) * 2)))
            max_t_bins = max(64, min(512, int(np.sqrt(max_plot_points) * 4)))
        except Exception:
            pass

    if fxx.size > max_f_bins:
        f_idx = np.linspace(0, fxx.size - 1, max_f_bins, dtype=int)
    else:
        f_idx = np.arange(fxx.size, dtype=int)

    if txx.size > max_t_bins:
        t_idx = np.linspace(0, txx.size - 1, max_t_bins, dtype=int)
    else:
        t_idx = np.arange(txx.size, dtype=int)

    f_ds = fxx[f_idx]
    t_ds = txx[t_idx]
    Sxx_ds = Sxx[np.ix_(f_idx, t_idx)]

    # Convert to [x,y,value] triplets for ECharts heatmap (vectorized)
    T, F = np.meshgrid(t_ds, f_ds)
    points = (
        np.column_stack((T.ravel(), F.ravel(), Sxx_ds.ravel()))
        .astype(float)
        .tolist()
    )
    opt = {
        "title": {"text": f"RR Spectrogram — {sel}", "left": "center"},
        "tooltip": {"position": "top"},
        "grid": {
            "height": "70%",
            "top": "10%",
            "left": 32,
            "right": 16,
            "containLabel": True,
        },
        "xAxis": {"type": "value", "name": "Time (s)"},
        "yAxis": {"type": "value", "name": "Frequency (Hz)"},
        "visualMap": {
            "min": float(np.percentile(Sxx_ds, 5)),
            "max": float(np.percentile(Sxx_ds, 95)),
            "calculable": True,
            "orient": "horizontal",
            "left": "center",
            "bottom": 0,
        },
        "series": [
            {
                "name": "PSD",
                "type": "heatmap",
                "data": points,
                "emphasis": {"itemStyle": {"shadowBlur": 10}},
            }
        ],
    }
    render_echarts(opt, height_px=520, width="100%", config=EChartsConfig())


def _compute_deviation_scores(
    windowed_df: pd.DataFrame,
    *,
    metrics: List[str],
    z_warn: float = 1.0,
    z_alert: float = 2.0,
) -> pd.DataFrame:
    """Compute robust deviation per window by source using median/MAD (vectorized)."""
    if windowed_df.empty or not metrics:
        return windowed_df
    df = windowed_df.copy()
    if "source" not in df.columns or "start" not in df.columns:
        return df
    metrics_present = [m for m in metrics if m in df.columns]
    if not metrics_present:
        df["dev_index"] = 0.0
        df["dev_level"] = "green"
        return df

    # Vectorized robust z for each metric
    z_cols: List[str] = []
    for mname in metrics_present:
        val = pd.to_numeric(df[mname], errors="coerce")
        med = df.groupby("source")[mname].transform(lambda x: float(
            np.median(pd.to_numeric(x, errors="coerce").dropna())))
        mad = df.groupby("source")[mname].transform(
            lambda x: float(
                np.median(
                    np.abs(
                        pd.to_numeric(x, errors="coerce").dropna()
                        - np.median(pd.to_numeric(x, errors="coerce").dropna())
                    )
                )
            )
        )
        # Avoid division by zero; if MAD=0 treat as zero deviation around
        # median
        mad_safe = mad.replace(0, np.nan)
        z = 0.6745 * (val - med) / mad_safe
        z_abs = z.abs().fillna(0.0)
        col = f"__z_{mname}"
        df[col] = z_abs
        z_cols.append(col)

    df["dev_index"] = df[z_cols].max(axis=1) if z_cols else 0.0
    df.drop(columns=z_cols, inplace=True, errors="ignore")
    df["dev_level"] = np.where(
        df["dev_index"] < float(z_warn),
        "green",
        np.where(df["dev_index"] < float(z_alert), "yellow", "red"),
    )
    return df


def _plot_deviation_timeline(windowed_df: pd.DataFrame) -> None:
    if (
        windowed_df.empty
        or "start" not in windowed_df.columns
        or "dev_level" not in windowed_df.columns
    ):
        st.info("No deviation data to display.")
        return
    series = []
    colors = {"green": "#43a047", "yellow": "#fb8c00", "red": "#e53935"}
    for src, sub in windowed_df.groupby("source"):
        for level in ["green", "yellow", "red"]:
            ss = sub[sub["dev_level"] == level]
            if ss.empty:
                continue
            data = [
                [str(x), float(y)]
                for x, y in zip(ss["start"].astype(str), ss["dev_index"].astype(float))
            ]
            series.append(
                {
                    "name": f"{src} — {level}",
                    "type": "scatter",
                    "symbolSize": 8,
                    "itemStyle": {"color": colors[level]},
                    "data": data,
                }
            )
    opt = {
        "title": {
            "text": "Deviation Timeline (max |robust z| across metrics)",
            "left": "center",
        },
        "tooltip": {"trigger": "item"},
        "legend": {"top": 24},
        "grid": {"left": 32, "right": 16, "containLabel": True},
        "xAxis": {"type": "time", "name": "Window start", "boundaryGap": False},
        "yAxis": {"type": "value", "name": "Deviation index"},
        "dataZoom": [{"type": "inside"}, {"type": "slider", "left": 32, "right": 16}],
        "series": series,
        "markLine": {
            "silent": True,
            "data": [
                {"yAxis": 1.0, "lineStyle": {"type": "dashed", "color": "#fb8c00"}},
                {"yAxis": 2.0, "lineStyle": {"type": "dashed", "color": "#e53935"}},
            ],
        },
    }
    render_echarts(opt, height_px=360, width="100%", config=EChartsConfig())


def _gauge_option(
    title: str,
    value: float,
    mu: float,
    sigma: float,
    vmin: float,
    vmax: float,
    unit: str,
) -> Dict:
    # Compute band thresholds
    lo = max(vmin, mu - sigma)
    hi = min(vmax, mu + sigma)
    span = max(1e-9, vmax - vmin)
    lo_r = max(0.0, min(1.0, (lo - vmin) / span))
    hi_r = max(0.0, min(1.0, (hi - vmin) / span))
    # Axis line colors: [0..lo]=red, (lo..hi]=green, (hi..1]=orange
    axis_colors = [[lo_r, "#e53935"], [hi_r, "#43a047"], [1.0, "#fb8c00"]]
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
                "detail": {"formatter": f"{value:.1f} {unit}", "fontSize": 14},
                "data": [{"value": float(value)}],
            }
        ],
    }


def _render_normogram_gauges(multi_results_df: pd.DataFrame) -> None:
    if multi_results_df.empty:
        st.info("No metrics available for gauges.")
        return
    names = (
        multi_results_df["source"].astype(str).tolist()
        if "source" in multi_results_df.columns
        else ["Current"]
    )
    sel = st.selectbox("Select dataset for gauges", names, index=0)
    row = (
        multi_results_df[multi_results_df["source"] == sel].iloc[0]
        if "source" in multi_results_df.columns
        else multi_results_df.iloc[0]
    )
    # Anchors from Normative.md (short-term ~5 min)
    sdnn_mu, sdnn_sigma = 50.0, 16.0
    rmssd_mu, rmssd_sigma = 42.0, 15.0
    lfhf_mu, lfhf_sigma = 2.8, 2.6
    hf_mu, hf_sigma = 657.0, 777.0
    # Values
    sdnn = float(row.get("sdnn", np.nan))
    rmssd = float(row.get("rmssd", np.nan))
    lfhf = float(row.get("lf_hf_ratio", np.nan))
    hf_power = float(row.get("hf_power", np.nan))
    # Gauge ranges
    sdnn_vmin, sdnn_vmax = 0.0, 120.0
    rmssd_vmin, rmssd_vmax = 0.0, 100.0
    lfhf_vmin, lfhf_vmax = 0.0, 12.0
    # For HF power, choose a dynamic max to keep needle in range
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
            _gauge_option(
                "SDNN (ms)",
                sdnn,
                sdnn_mu,
                sdnn_sigma,
                sdnn_vmin,
                sdnn_vmax,
                "ms"),
            height_px=300,
            config=EChartsConfig(),
        )
    with cols[1]:
        render_echarts(
            _gauge_option(
                "RMSSD (ms)",
                rmssd,
                rmssd_mu,
                rmssd_sigma,
                rmssd_vmin,
                rmssd_vmax,
                "ms"),
            height_px=300,
            config=EChartsConfig(),
        )
    cols2 = st.columns(2)
    with cols2[0]:
        render_echarts(
            _gauge_option(
                "LF/HF (ratio)",
                lfhf,
                lfhf_mu,
                lfhf_sigma,
                lfhf_vmin,
                lfhf_vmax,
                ""),
            height_px=300,
            config=EChartsConfig(),
        )
    with cols2[1]:
        render_echarts(
            _gauge_option(
                "HF Power (ms²)",
                hf_power,
                hf_mu,
                hf_sigma,
                hf_vmin,
                hf_vmax,
                "ms²"),
            height_px=300,
            config=EChartsConfig(),
        )
    # Respiratory rate gauge (derived from HF peak when RSA present)
    resp_bpm = float(row.get("respiratory_rate_bpm", np.nan))
    cols3 = st.columns(1)
    with cols3[0]:
        render_echarts(
            _gauge_option(
                "Respiratory rate (breaths/min)",
                resp_bpm,
                16.0,
                4.0,
                6.0,
                30.0,
                "breaths/min",
            ),
            height_px=300,
            config=EChartsConfig(),
        )
    st.caption(
        "Bands reflect mean ± SD from short-term (∼5 min) references; see Normative.md for details and caveats."
    )


def _interpretation(
    multi_results: pd.DataFrame, windowed: Optional[pd.DataFrame]
) -> None:
    if multi_results.empty:
        return
    st.subheader("Interpretation")
    # Short-term, commonly cited anchors
    rmssd_mu, rmssd_sigma = 42.0, 15.0
    sdnn_mu, sdnn_sigma = 50.0, 16.0
    lfhf_mu, lfhf_sigma = 2.8, 2.6

    def pos(value: float, mu: float, sigma: float) -> str:
        if not np.isfinite(value):
            return "n/a"
        lo, hi = mu - sigma, mu + sigma
        return "below" if value < lo else ("above" if value > hi else "within")

    lines: List[str] = []
    for _, row in multi_results.iterrows():
        src = str(row.get("source", "N/A"))
        sdnn = float(row.get("sdnn", np.nan))
        rmssd = float(row.get("rmssd", np.nan))
        lfhf = float(row.get("lf_hf_ratio", np.nan))
        lines.append(
            f"- {src}: SDNN {sdnn:.1f} ms ({pos(sdnn, sdnn_mu, sdnn_sigma)}), "
            f"RMSSD {rmssd:.1f} ms ({pos(rmssd, rmssd_mu, rmssd_sigma)}), "
            f"LF/HF {lfhf:.2f} ({pos(lfhf, lfhf_mu, lfhf_sigma)})"
        )
    st.markdown("\n".join(lines))
    st.caption(
        "References: Task Force 1996; short-term time-domain and spectral anchors are cohort-dependent. "
        "See project Normative.md for more detail.")


def _project_data_dir() -> Path:
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


DB_JSONL = "hrv_solar_db.jsonl"


def _append_jsonl(record: Dict[str, Any]) -> None:
    path = _project_data_dir() / DB_JSONL
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load_jsonl() -> pd.DataFrame:
    path = _project_data_dir() / DB_JSONL
    if not path.exists():
        return pd.DataFrame()
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return pd.json_normalize(rows)


try:
    from scipy import stats as _scipy_stats  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    _scipy_stats = None


def _pearson_r_p(x: np.ndarray, y: np.ndarray) -> Tuple[float, float, int]:
    mask = np.isfinite(x) & np.isfinite(y)
    xv = x[mask]
    yv = y[mask]
    n = int(min(xv.size, yv.size))
    if n < 3:
        return float("nan"), float("nan"), n
    # Check for constant arrays (std=0) to avoid ConstantInputWarning
    if np.std(xv) == 0 or np.std(yv) == 0:
        return float("nan"), float("nan"), n
    if _scipy_stats is not None:
        r, p = _scipy_stats.pearsonr(xv, yv)
        return float(r), float(p), n
    # Fallback: only r, approximate p as NaN
    r = float(np.corrcoef(xv, yv)[0, 1])
    return r, float("nan"), n


FISHER_Z_CRIT = 1.959963984540054


@dataclass(frozen=True, slots=True)
class NOAACorrelationSummary:
    """
    Summary statistics for a NOAA predictor ↔ HRV metric correlation.

    Attributes
    ----------
    predictor_key :
        Identifier of the NOAA dataset (e.g., 'solar_wind_wind').
    predictor_title :
        Human-readable dataset title.
    value_column :
        Predictor column used in the correlation.
    unit :
        Unit string for the predictor value (if available).
    metric :
        HRV metric column name.
    lag_hours :
        Lag applied to the predictor prior to merging (hours).
    pearson_r :
        Pearson correlation coefficient.
    p_value :
        Two-tailed p-value associated with the correlation.
    ci_low :
        Lower bound of the 95% confidence interval for r.
    ci_high :
        Upper bound of the 95% confidence interval for r.
    n :
        Sample count contributing to the correlation.
    direction :
        Qualitative direction ('positive', 'negative', 'neutral', or 'insufficient').
    test_name :
        Name of the statistical test. Defaults to 'Pearson r'.
    """

    predictor_key: str
    predictor_title: str
    value_column: str
    unit: Optional[str]
    metric: str
    lag_hours: int
    pearson_r: float
    p_value: float
    ci_low: float
    ci_high: float
    n: int
    direction: str
    test_name: str = "Pearson r"


def _pearson_ci95(r: float, n: int) -> Tuple[float, float]:
    """
    Compute the 95% confidence interval for a Pearson correlation coefficient.
    """

    if not np.isfinite(r) or n < 4:
        return float("nan"), float("nan")
    r_clamped = float(np.clip(r, -0.999999, 0.999999))
    z_score = float(np.arctanh(r_clamped))
    se = 1.0 / float(np.sqrt(max(n - 3, 1)))
    delta = FISHER_Z_CRIT * se
    low = float(np.tanh(z_score - delta))
    high = float(np.tanh(z_score + delta))
    if low > high:
        low, high = high, low
    return low, high


def _correlation_direction(r: float, n: int) -> str:
    """
    Determine qualitative directionality for a Pearson correlation.
    """

    if not np.isfinite(r) or n < 3:
        return "insufficient"
    if abs(r) < 1e-9:
        return "neutral"
    return "positive" if r > 0 else "negative"


def _compute_noaa_correlations(
    windowed_df: pd.DataFrame,
    bundle: NOAADataBundle,
    metrics: Sequence[str],
    lags_hours: Sequence[int],
    *,
    merge_tolerance_minutes: int = 90,
) -> List[NOAACorrelationSummary]:
    """
    Compute Pearson correlations between HRV metrics and a NOAA predictor bundle.
    """

    if merge_tolerance_minutes <= 0:
        raise ValueError("merge_tolerance_minutes must be positive.")
    if windowed_df.empty or not metrics:
        return []
    if not bundle.value_columns:
        return []
    if "start" not in windowed_df.columns:
        return []

    hrv = windowed_df.copy()
    hrv["start"] = pd.to_datetime(hrv["start"], errors="coerce", utc=True)
    hrv = hrv.dropna(subset=["start"]).sort_values("start")
    if hrv.empty:
        return []

    metric_columns = [
        col
        for col in metrics
        if col in hrv.columns and pd.api.types.is_numeric_dtype(hrv[col])
    ]
    if not metric_columns:
        return []

    lag_values = list(lags_hours) if lags_hours else [0]
    results: List[NOAACorrelationSummary] = []

    for value_column in bundle.value_columns:
        if value_column not in bundle.frame.columns:
            continue
        predictor = bundle.frame[[bundle.time_column, value_column]].copy()
        predictor[bundle.time_column] = pd.to_datetime(
            predictor[bundle.time_column], errors="coerce", utc=True
        )
        predictor[value_column] = pd.to_numeric(
            predictor[value_column], errors="coerce"
        )
        predictor = predictor.dropna(subset=[bundle.time_column, value_column])
        predictor = predictor.sort_values(bundle.time_column)
        if predictor.empty:
            continue

        use_daily_alignment = False
        cadence_minutes = bundle.spec.cadence_minutes
        if isinstance(cadence_minutes, int) and cadence_minutes >= 1440:
            use_daily_alignment = True

        for lag in lag_values:
            lag_int = int(lag)
            if use_daily_alignment:
                # For daily cadence predictors, align on UTC date rather than
                # sub-hour timestamps. This avoids empty joins when HRV windows
                # occur far from midnight and avoids unintuitive day-shifts for
                # small negative hour lags on midnight-based daily series.
                lag_days = int(lag_int / 24)
                hrv_dates = hrv["start"].dt.normalize()
                pred_dates = pd.to_datetime(
                    predictor[bundle.time_column], errors="coerce", utc=True
                ).dt.normalize() + pd.to_timedelta(lag_days, unit="D")
                pred_vals = pd.to_numeric(
                    predictor[value_column], errors="coerce"
                ).astype(float)
                pred_by_date = (
                    pd.DataFrame({"date": pred_dates, "value": pred_vals})
                    .dropna(subset=["date", "value"])
                    .groupby("date", sort=True)["value"]
                    .mean()
                )
                if pred_by_date.empty:
                    continue
                aligned_values = hrv_dates.map(pred_by_date)
                merged = hrv.copy()
                merged[value_column] = aligned_values.to_numpy(dtype=float)
                merged = merged.dropna(subset=[value_column])
            else:
                aligned = align_space_weather_series(
                    reference_times=hrv["start"],
                    predictor_df=predictor,
                    predictor_time_col=bundle.time_column,
                    predictor_value_col=value_column,
                    lag_hours=lag_int,
                    max_gap_minutes=int(merge_tolerance_minutes),
                )
                if aligned.empty:
                    continue
                merged = (
                    hrv.set_index("start")
                    .join(aligned.rename(value_column), how="inner")
                    .dropna(subset=[value_column])
                )
            if merged.empty:
                continue
            corr_df = _corr_table(
                merged.reset_index(drop=True), value_column, list(metric_columns)
            )
            if corr_df.empty:
                continue

            unit = bundle.units.get(value_column) if bundle.units else None
            for row in corr_df.to_dict(orient="records"):
                r = float(row.get("pearson_r", float("nan")))
                p = float(row.get("p_value", float("nan")))
                n = int(row.get("n", 0))
                ci_low, ci_high = _pearson_ci95(r, n)
                results.append(
                    NOAACorrelationSummary(
                        predictor_key=bundle.spec.key,
                        predictor_title=bundle.spec.title,
                        value_column=value_column,
                        unit=unit,
                        metric=str(row.get("metric", "")),
                        lag_hours=lag_int,
                        pearson_r=r,
                        p_value=p,
                        ci_low=ci_low,
                        ci_high=ci_high,
                        n=n,
                        direction=_correlation_direction(r, n),
                    )
                )
    return results


def _noaa_correlations_to_frame(
    results: Sequence[NOAACorrelationSummary],
) -> pd.DataFrame:
    """
    Convert NOAA correlation summaries into a DataFrame for downstream use.
    """

    if not results:
        return pd.DataFrame(
            columns=[
                "predictor_key",
                "predictor_title",
                "value_column",
                "unit",
                "metric",
                "lag_hours",
                "pearson_r",
                "p_value",
                "ci_low",
                "ci_high",
                "n",
                "direction",
                "test_name",
            ]
        )
    return pd.DataFrame([asdict(item) for item in results])


def _build_noaa_correlations(
    windowed_df: pd.DataFrame,
    bundles: Mapping[str, NOAADataBundle],
    metrics: Sequence[str],
    lags_hours: Sequence[int],
    *,
    merge_tolerance_minutes: int = 90,
) -> pd.DataFrame:
    """
    Compute correlations for multiple NOAA bundles and aggregate the results.
    """

    summaries: List[NOAACorrelationSummary] = []
    for bundle in bundles.values():
        summaries.extend(
            _compute_noaa_correlations(
                windowed_df,
                bundle,
                metrics,
                lags_hours,
                merge_tolerance_minutes=merge_tolerance_minutes,
            )
        )
    return _noaa_correlations_to_frame(summaries)


def _corr_table(
    merged: pd.DataFrame,
    predictor_col: str,
    target_cols: List[str],
    covariate_cols: Optional[Sequence[str]] = None,
) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    covariate_list: List[str] = []
    if covariate_cols:
        for column in covariate_cols:
            if (
                column in merged.columns
                and pd.api.types.is_numeric_dtype(merged[column])
            ):
                covariate_list.append(column)
    cov_matrix = (
        merged[covariate_list].to_numpy(dtype=float)
        if covariate_list
        else None
    )
    for col in target_cols:
        if col == predictor_col:
            continue
        if col not in merged.columns:
            continue
        predictor_values = merged[predictor_col].to_numpy(dtype=float)
        target_values = merged[col].to_numpy(dtype=float)
        if cov_matrix is not None:
            r, p, n = partial_pearson_r_p(
                predictor_values,
                target_values,
                cov_matrix,
            )
        else:
            r, p, n = _pearson_r_p(
                predictor_values,
                target_values,
            )
        # 95% CI for Pearson r using Fisher z (guard for |r| ~ 1 and n < 4)
        ci_low = float("nan")
        ci_high = float("nan")
        if n > 3 and np.isfinite(r) and abs(r) < 0.9999:
            try:
                z = np.arctanh(r)
                se = 1.0 / np.sqrt(n - 3)
                z_crit = 1.96
                ci_low = float(np.tanh(z - z_crit * se))
                ci_high = float(np.tanh(z + z_crit * se))
            except Exception:
                ci_low = float("nan")
                ci_high = float("nan")
        # Spearman rho (nonparametric robustness)
        try:
            from scipy.stats import spearmanr  # type: ignore

            rho, p_s = spearmanr(predictor_values, target_values, nan_policy="omit")
        except Exception:
            rho, p_s = float("nan"), float("nan")

        # HAC-robust regression (OLS with HAC covariance) if statsmodels is available
        hac_p = float("nan")
        hac_ci_low = float("nan")
        hac_ci_high = float("nan")
        try:
            import statsmodels.api as sm  # type: ignore

            X = sm.add_constant(predictor_values)
            model = sm.OLS(target_values, X)
            res = model.fit(cov_type="HAC", cov_kwds={"maxlags": 4})
            beta = res.params[1]
            se = res.bse[1]
            hac_p = float(res.pvalues[1])
            z_crit = 1.96
            hac_ci_low = float(beta - z_crit * se)
            hac_ci_high = float(beta + z_crit * se)
        except Exception:
            pass

        rows.append(
            {
                "metric": col,
                "pearson_r": r,
                "p_value": p,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "spearman_r": rho,
                "spearman_p": p_s,
                "hac_p": hac_p,
                "hac_ci_low": hac_ci_low,
                "hac_ci_high": hac_ci_high,
                "n": n,
            }
        )
    return pd.DataFrame(rows)


def _scan_lag_correlations(
    windowed_df: pd.DataFrame,
    kp_df: pd.DataFrame,
    metrics: List[str],
    lags_hours: List[int],
    merge_tolerance_minutes: int = 90,
    covariate_cols: Optional[Sequence[str]] = None,
) -> pd.DataFrame:
    results: List[Dict[str, Any]] = []
    if (
        "start" not in windowed_df.columns
        or "kp_index" not in kp_df.columns
        or "time_tag" not in kp_df.columns
    ):
        return pd.DataFrame()
    w = windowed_df.copy()
    w["start"] = pd.to_datetime(w["start"], errors="coerce", utc=True)
    w = w.dropna(subset=["start"]).sort_values("start")
    if w.empty:
        return pd.DataFrame()
    k = kp_df.copy()
    k["time_tag"] = pd.to_datetime(k["time_tag"], errors="coerce", utc=True)
    k = k.dropna(subset=["time_tag", "kp_index"]).sort_values("time_tag")
    if k.empty:
        return pd.DataFrame()
    for lag in lags_hours:
        aligned = align_space_weather_series(
            reference_times=w["start"],
            predictor_df=k,
            predictor_time_col="time_tag",
            predictor_value_col="kp_index",
            lag_hours=int(lag),
            max_gap_minutes=int(merge_tolerance_minutes),
        )
        if aligned.empty:
            continue
        merged = (
            w.set_index("start")
            .join(aligned.rename("kp_index"), how="inner")
            .dropna(subset=["kp_index"])
        )
        if merged.empty:
            continue
        corr_df = _corr_table(
            merged.reset_index(drop=True),
            "kp_index",
            metrics,
            covariate_cols=covariate_cols,
        )
        corr_df["lag_hours"] = int(lag)
        results.append(corr_df)
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()


def _phase_correlation_table(
    windowed_df: pd.DataFrame,
    predictor_df: pd.DataFrame,
    *,
    time_col: str,
    predictor_time_col: str,
    predictor_value_col: str,
    metric_cols: Sequence[str],
    phase_label: str,
    phase_start_utc: pd.Timestamp,
    phase_end_utc: pd.Timestamp,
    merge_tolerance_minutes: int = 90,
) -> pd.DataFrame:
    """Compute a per-metric correlation table for a specific phase window.

    This aligns the predictor series to `windowed_df[time_col]` using
    `align_space_weather_series` (lag=0) and computes Pearson correlations
    (and additional stats provided by `_corr_table`) within the phase window.
    """
    if not isinstance(windowed_df, pd.DataFrame) or windowed_df.empty:
        return pd.DataFrame()
    if not isinstance(predictor_df, pd.DataFrame) or predictor_df.empty:
        return pd.DataFrame()
    if not time_col or time_col not in windowed_df.columns:
        return pd.DataFrame()
    if not predictor_time_col or predictor_time_col not in predictor_df.columns:
        return pd.DataFrame()
    if not predictor_value_col or predictor_value_col not in predictor_df.columns:
        return pd.DataFrame()
    if not metric_cols:
        return pd.DataFrame()

    w = windowed_df.copy()
    w[time_col] = pd.to_datetime(w[time_col], errors="coerce", utc=True)
    w = w.dropna(subset=[time_col]).sort_values(time_col)
    if w.empty:
        return pd.DataFrame()

    start_utc = pd.to_datetime(phase_start_utc, utc=True, errors="coerce")
    end_utc = pd.to_datetime(phase_end_utc, utc=True, errors="coerce")
    if pd.isna(start_utc) or pd.isna(end_utc) or end_utc < start_utc:
        return pd.DataFrame()

    w_phase = w.loc[(w[time_col] >= start_utc) & (w[time_col] <= end_utc)].copy()
    if w_phase.empty:
        return pd.DataFrame()

    aligned = align_space_weather_series(
        reference_times=w_phase[time_col],
        predictor_df=predictor_df,
        predictor_time_col=str(predictor_time_col),
        predictor_value_col=str(predictor_value_col),
        lag_hours=0,
        max_gap_minutes=int(merge_tolerance_minutes),
    )
    if aligned.empty:
        return pd.DataFrame()

    merged = (
        w_phase.set_index(time_col)
        .join(aligned.rename("predictor"), how="inner")
        .dropna(subset=["predictor"])
    )
    if merged.empty:
        return pd.DataFrame()

    usable_metrics = [
        m
        for m in metric_cols
        if m in merged.columns and pd.api.types.is_numeric_dtype(merged[m])
    ]
    if not usable_metrics:
        return pd.DataFrame()

    corr_df = _corr_table(
        merged.reset_index(drop=True),
        "predictor",
        list(usable_metrics),
        covariate_cols=None,
    )
    if corr_df.empty:
        return pd.DataFrame()
    corr_df.insert(0, "phase", str(phase_label))
    corr_df.insert(1, "predictor", str(predictor_value_col))
    return corr_df


def _block_bootstrap_corr(
    x: np.ndarray,
    y: np.ndarray,
    *,
    block_size: int = 8,
    n_boot: int = 200,
) -> Tuple[float, float]:
    """Block bootstrap CI for Pearson r (basic percentile)."""
    n = len(x)
    if n < 4:
        return float("nan"), float("nan")
    rng = np.random.default_rng(42)
    r_boot: List[float] = []
    for _ in range(n_boot):
        starts = rng.integers(0, max(1, n - block_size + 1), size=max(1, n // block_size))
        idx: List[int] = []
        for s in starts:
            idx.extend(range(s, min(s + block_size, n)))
            if len(idx) >= n:
                break
        idx = idx[:n]
        xb = x[idx]
        yb = y[idx]
        if np.std(xb) == 0 or np.std(yb) == 0:
            continue
        r_boot.append(float(np.corrcoef(xb, yb)[0, 1]))
    if not r_boot:
        return float("nan"), float("nan")
    r_sorted = np.sort(r_boot)
    low = float(np.percentile(r_sorted, 2.5))
    high = float(np.percentile(r_sorted, 97.5))
    return low, high


def _perm_test_corr(
    x: np.ndarray,
    y: np.ndarray,
    *,
    n_perm: int = 200,
) -> float:
    """Permutation p-value for Pearson r (two-sided)."""
    n = len(x)
    if n < 4:
        return float("nan")
    rng = np.random.default_rng(123)
    obs = float(np.corrcoef(x, y)[0, 1]) if np.std(x) > 0 and np.std(y) > 0 else float("nan")
    if not np.isfinite(obs):
        return float("nan")
    greater = 0
    for _ in range(n_perm):
        y_perm = rng.permutation(y)
        r = float(np.corrcoef(x, y_perm)[0, 1]) if np.std(y_perm) > 0 else 0.0
        if abs(r) >= abs(obs):
            greater += 1
    return float((greater + 1) / (n_perm + 1))


def _compute_bootstrap_perm_for_best(
    windowed_df: pd.DataFrame,
    predictor_df: pd.DataFrame,
    predictor_time_col: str,
    predictor_value_col: str,
    metric: str,
    lag_hours: int,
    *,
    merge_tolerance_minutes: int = 90,
) -> Dict[str, float]:
    """Re-align a single metric/predictor/lag and compute block bootstrap CI + permutation p."""
    aligned = align_space_weather_series(
        reference_times=pd.to_datetime(windowed_df["start"], errors="coerce", utc=True),
        predictor_df=predictor_df,
        predictor_time_col=predictor_time_col,
        predictor_value_col=predictor_value_col,
        lag_hours=int(lag_hours),
        max_gap_minutes=int(merge_tolerance_minutes),
    )
    merged = (
        windowed_df.set_index("start")
        .join(aligned.rename(predictor_value_col), how="inner")
        .dropna(subset=[predictor_value_col, metric])
    )
    if merged.empty:
        return {"boot_low": float("nan"), "boot_high": float("nan"), "perm_p": float("nan")}
    x = merged[predictor_value_col].to_numpy(dtype=float)
    y = merged[metric].to_numpy(dtype=float)
    boot_low, boot_high = _block_bootstrap_corr(x, y)
    perm_p = _perm_test_corr(x, y)
    return {"boot_low": boot_low, "boot_high": boot_high, "perm_p": perm_p}


def _build_kp_feature_matrix(
    windowed_df: pd.DataFrame,
    kp_df: pd.DataFrame,
    lags_hours: List[int],
    merge_tolerance_minutes: int = 90,
) -> pd.DataFrame:
    """Construct a wide feature matrix of Kp lag features aligned to HRV windows."""
    if windowed_df.empty or kp_df.empty:
        return pd.DataFrame()
    w = windowed_df.copy()
    w["start"] = pd.to_datetime(w["start"], errors="coerce", utc=True)
    w = w.dropna(subset=["start"]).sort_values("start")
    if w.empty:
        return pd.DataFrame()
    k = kp_df.copy()
    k["time_tag"] = pd.to_datetime(k["time_tag"], errors="coerce", utc=True)
    k = k.dropna(subset=["time_tag", "kp_index"]).sort_values("time_tag")
    if k.empty:
        return pd.DataFrame()
    base = w.set_index("start")
    for lag in lags_hours:
        aligned = align_space_weather_series(
            reference_times=w["start"],
            predictor_df=k,
            predictor_time_col="time_tag",
            predictor_value_col="kp_index",
            lag_hours=int(lag),
            max_gap_minutes=int(merge_tolerance_minutes),
        )
        if aligned.empty:
            continue
        base[f"kp_lag_{int(lag)}h"] = aligned
    return base.reset_index()


def _run_ml_models_on_kp(
    windowed_df: pd.DataFrame,
    kp_df: pd.DataFrame,
    target_metric: str,
    lags_hours: List[int],
    merge_tolerance_minutes: int = 90,
) -> Dict[str, Any]:
    """Train ElasticNet and RandomForest models predicting an HRV metric from Kp lags."""
    _ensure_sklearn()
    feature_df = _build_kp_feature_matrix(
        windowed_df, kp_df, lags_hours, merge_tolerance_minutes=merge_tolerance_minutes
    )
    if feature_df.empty or target_metric not in feature_df.columns:
        raise ValueError("Insufficient data to train ML models.")
    y = pd.to_numeric(feature_df[target_metric], errors="coerce")
    X = feature_df[[c for c in feature_df.columns if c.startswith("kp_lag_")]]
    X = X.apply(pd.to_numeric, errors="coerce")
    df = pd.concat([y, X], axis=1).dropna()
    if df.shape[0] < 30:
        raise ValueError("Not enough samples for ML (need ≥30 rows).")
    y = df[target_metric].to_numpy(dtype=float)
    X = df[[c for c in df.columns if c.startswith("kp_lag_")]].to_numpy(dtype=float)
    n = X.shape[0]
    split = int(max(10, n * 0.8))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    results: Dict[str, Any] = {"samples": n, "features": X.shape[1]}

    # ElasticNetCV for linear sparse patterns
    enet = ElasticNetCV(
        l1_ratio=[0.1, 0.5, 0.9],
        alphas=None,
        cv=3,
        max_iter=5000,
        n_jobs=None,
        fit_intercept=True,
    )
    enet.fit(X_train, y_train)
    y_pred_en = enet.predict(X_test)
    results["elastic_net"] = {
        "r2": float(r2_score(y_test, y_pred_en)) if y_test.size > 0 else float("nan"),
        "mae": float(mean_absolute_error(y_test, y_pred_en))
        if y_test.size > 0
        else float("nan"),
        "alpha": float(enet.alpha_),
        "l1_ratio": float(enet.l1_ratio_),
    }

    # RandomForest for nonlinear patterns
    rf = RandomForestRegressor(
        n_estimators=160,
        max_depth=6,
        random_state=42,
        n_jobs=-1,
        min_samples_leaf=2,
    )
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    results["random_forest"] = {
        "r2": float(r2_score(y_test, y_pred_rf)) if y_test.size > 0 else float("nan"),
        "mae": float(mean_absolute_error(y_test, y_pred_rf))
        if y_test.size > 0
        else float("nan"),
    }
    try:
        perm = permutation_importance(
            rf, X_test, y_test, n_repeats=8, random_state=42, n_jobs=-1
        )
        importances = [
            {"feature": name, "importance": float(val)}
            for name, val in sorted(
                zip([c for c in feature_df.columns if c.startswith("kp_lag_")], perm.importances_mean),
                key=lambda t: t[1],
                reverse=True,
            )
        ]
        results["feature_importances"] = importances
    except Exception:
        results["feature_importances"] = []

    return results


def _build_space_weather_feature_matrix(
    windowed_df: pd.DataFrame,
    bundles: Mapping[str, NOAADataBundle],
    predictors: Sequence[str],
    lags_hours: List[int],
    merge_tolerance_minutes: int = 90,
) -> pd.DataFrame:
    """Construct a wide feature matrix across selected NOAA predictors."""
    if windowed_df.empty:
        return pd.DataFrame()
    w = windowed_df.copy()
    w["start"] = pd.to_datetime(w["start"], errors="coerce", utc=True)
    w = w.dropna(subset=["start"]).sort_values("start")
    if w.empty:
        return pd.DataFrame()
    base = w.set_index("start")
    for key in predictors:
        bundle = bundles.get(key)
        if not bundle or bundle.frame.empty:
            continue
        df = bundle.frame.copy()
        df_time_col = bundle.time_column
        df[df_time_col] = pd.to_datetime(df[df_time_col], errors="coerce", utc=True)
        for value_col in bundle.value_columns or []:
            if value_col not in df.columns:
                continue
            pred = df[[df_time_col, value_col]].dropna()
            pred = pred.sort_values(df_time_col)
            if pred.empty:
                continue
            for lag in lags_hours:
                aligned = align_space_weather_series(
                    reference_times=w["start"],
                    predictor_df=pred,
                    predictor_time_col=df_time_col,
                    predictor_value_col=value_col,
                    lag_hours=int(lag),
                    max_gap_minutes=int(merge_tolerance_minutes),
                )
                if aligned.empty:
                    continue
                base[f"{key}_{value_col}_lag_{int(lag)}h"] = aligned
    return base.reset_index()


def _run_ml_models_space_weather(
    feature_df: pd.DataFrame,
    target_metric: str,
) -> Dict[str, Any]:
    """Train ElasticNet + RandomForest + XGBoost/LightGBM on a pre-built space-weather feature matrix.
    
    Also computes SHAP values for model interpretability if available.
    """
    _ensure_sklearn()
    _ensure_ml_libs()
    if feature_df.empty or target_metric not in feature_df.columns:
        raise ValueError("No data for ML.")
    y = pd.to_numeric(feature_df[target_metric], errors="coerce")
    X_cols = [c for c in feature_df.columns if c != target_metric and c != "start"]
    X = feature_df[X_cols].apply(pd.to_numeric, errors="coerce")
    df = pd.concat([y, X], axis=1).dropna()
    if df.shape[0] < 30 or len(X_cols) == 0:
        raise ValueError("Not enough samples or predictors for ML (need ≥30 rows).")
    y = df[target_metric].to_numpy(dtype=float)
    X = df[X_cols].to_numpy(dtype=float)
    n = X.shape[0]
    # Walk-forward split: first 70% train, next 15% val, final 15% test
    train_end = int(max(10, n * 0.7))
    val_end = int(max(train_end + 5, n * 0.85))
    X_train, X_val, X_test = X[:train_end], X[train_end:val_end], X[val_end:]
    y_train, y_val, y_test = y[:train_end], y[train_end:val_end], y[val_end:]

    results: Dict[str, Any] = {"samples": n, "features": X.shape[1]}

    enet = ElasticNetCV(
        l1_ratio=[0.1, 0.5, 0.9],
        alphas=None,
        cv=3,
        max_iter=5000,
        n_jobs=None,
        fit_intercept=True,
    )
    enet.fit(X_train, y_train)
    y_pred_en = enet.predict(X_test) if X_test.size else np.array([])
    results["elastic_net"] = {
        "r2": float(r2_score(y_test, y_pred_en)) if y_test.size else float("nan"),
        "mae": float(mean_absolute_error(y_test, y_pred_en)) if y_test.size else float("nan"),
        "alpha": float(enet.alpha_),
        "l1_ratio": float(enet.l1_ratio_),
    }

    rf = RandomForestRegressor(
        n_estimators=200,
        max_depth=8,
        random_state=42,
        n_jobs=-1,
        min_samples_leaf=2,
    )
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test) if X_test.size else np.array([])
    results["random_forest"] = {
        "r2": float(r2_score(y_test, y_pred_rf)) if y_test.size else float("nan"),
        "mae": float(mean_absolute_error(y_test, y_pred_rf)) if y_test.size else float("nan"),
    }
    
    # Store trained models for SHAP analysis
    trained_models: Dict[str, Any] = {"random_forest": rf}
    
    try:
        perm = permutation_importance(
            rf, X_test, y_test, n_repeats=8, random_state=42, n_jobs=-1
        )
        importances = [
            {"feature": name, "importance": float(val)}
            for name, val in sorted(
                zip(X_cols, perm.importances_mean),
                key=lambda t: t[1],
                reverse=True,
            )
        ]
        results["feature_importances"] = importances
    except Exception:
        results["feature_importances"] = []

    # Gradient Boosting as an additional nonlinear baseline
    gb = GradientBoostingRegressor(random_state=42)
    gb.fit(X_train, y_train)
    y_pred_gb = gb.predict(X_test) if X_test.size else np.array([])
    results["gradient_boosting"] = {
        "r2": float(r2_score(y_test, y_pred_gb)) if y_test.size else float("nan"),
        "mae": float(mean_absolute_error(y_test, y_pred_gb)) if y_test.size else float("nan"),
    }

    # LassoCV for sparsity encouragement
    lasso = LassoCV(cv=3, max_iter=5000, n_jobs=None)
    lasso.fit(X_train, y_train)
    y_pred_lasso = lasso.predict(X_test) if X_test.size else np.array([])
    results["lasso"] = {
        "r2": float(r2_score(y_test, y_pred_lasso)) if y_test.size else float("nan"),
        "mae": float(mean_absolute_error(y_test, y_pred_lasso)) if y_test.size else float("nan"),
        "alpha": float(lasso.alpha_),
    }
    
    # XGBoost (if available) - often outperforms RandomForest
    if XGBOOST_AVAILABLE and XGBRegressor is not None:
        try:
            # Prefer GPU acceleration when enabled (safe CPU fallback on any error).
            xgb_params: Dict[str, Any] = {
                "n_estimators": 200,
                "max_depth": 6,
                "learning_rate": 0.1,
                "random_state": 42,
                "n_jobs": -1,
                "verbosity": 0,
            }
            if GPU_PROCESSING_AVAILABLE and is_gpu_enabled():
                # XGBoost GPU parameters (will raise if build lacks GPU support).
                xgb_params.update(
                    {
                        "tree_method": "gpu_hist",
                        "predictor": "gpu_predictor",
                        "gpu_id": 0,
                    }
                )
            xgb = XGBRegressor(
                **xgb_params,
            )
            xgb.fit(X_train, y_train)
            y_pred_xgb = xgb.predict(X_test) if X_test.size else np.array([])
            results["xgboost"] = {
                "r2": float(r2_score(y_test, y_pred_xgb)) if y_test.size else float("nan"),
                "mae": float(mean_absolute_error(y_test, y_pred_xgb)) if y_test.size else float("nan"),
            }
            trained_models["xgboost"] = xgb
        except Exception as exc:
            results["xgboost"] = {"error": str(exc)}
    
    # LightGBM (if available) - fast gradient boosting
    if LIGHTGBM_AVAILABLE and LGBMRegressor is not None:
        try:
            lgbm_params: Dict[str, Any] = {
                "n_estimators": 200,
                "max_depth": 6,
                "learning_rate": 0.1,
                "random_state": 42,
                "n_jobs": -1,
                "verbosity": -1,
            }
            if GPU_PROCESSING_AVAILABLE and is_gpu_enabled():
                # LightGBM GPU support depends on how the wheel was built.
                lgbm_params.update({"device": "gpu"})
            lgbm = LGBMRegressor(
                **lgbm_params,
            )
            lgbm.fit(X_train, y_train)
            y_pred_lgbm = lgbm.predict(X_test) if X_test.size else np.array([])
            results["lightgbm"] = {
                "r2": float(r2_score(y_test, y_pred_lgbm)) if y_test.size else float("nan"),
                "mae": float(mean_absolute_error(y_test, y_pred_lgbm)) if y_test.size else float("nan"),
            }
            trained_models["lightgbm"] = lgbm
        except Exception as exc:
            results["lightgbm"] = {"error": str(exc)}
    
    # SHAP interpretability (if available)
    if SHAP_AVAILABLE and shap is not None and X_test.size > 0:
        try:
            # Use RandomForest for SHAP (most interpretable tree model)
            explainer = shap.TreeExplainer(rf)
            shap_values = explainer.shap_values(X_test[:min(100, len(X_test))])  # Limit to 100 samples for performance
            
            # Compute mean absolute SHAP values for global importance
            if isinstance(shap_values, np.ndarray):
                mean_abs_shap = np.abs(shap_values).mean(axis=0)
                shap_importances = [
                    {"feature": name, "shap_importance": float(val)}
                    for name, val in sorted(
                        zip(X_cols, mean_abs_shap),
                        key=lambda t: t[1],
                        reverse=True,
                    )
                ]
                results["shap_importances"] = shap_importances
                results["shap_available"] = True
                results["shap_base_value"] = float(explainer.expected_value)
        except Exception as exc:
            results["shap_importances"] = []
            results["shap_available"] = False
            results["shap_error"] = str(exc)
    else:
        results["shap_available"] = False

    # TimeSeriesSplit CV for ElasticNet and RF
    try:
        tscv = TimeSeriesSplit(n_splits=3)
        enet_cv_scores = []
        rf_cv_scores = []
        for train_idx, test_idx in tscv.split(X):
            X_tr, X_te = X[train_idx], X[test_idx]
            y_tr, y_te = y[train_idx], y[test_idx]
            enet_cv = ElasticNetCV(
                l1_ratio=[0.1, 0.5, 0.9],
                alphas=None,
                cv=3,
                max_iter=5000,
                n_jobs=None,
                fit_intercept=True,
            )
            enet_cv.fit(X_tr, y_tr)
            enet_cv_scores.append(r2_score(y_te, enet_cv.predict(X_te)))
            rf_cv = RandomForestRegressor(
                n_estimators=120,
                max_depth=6,
                random_state=42,
                n_jobs=-1,
                min_samples_leaf=2,
            )
            rf_cv.fit(X_tr, y_tr)
            rf_cv_scores.append(r2_score(y_te, rf_cv.predict(X_te)))
        if enet_cv_scores:
            results["elastic_net"]["cv_r2_mean"] = float(np.nanmean(enet_cv_scores))
        if rf_cv_scores:
            results["random_forest"]["cv_r2_mean"] = float(np.nanmean(rf_cv_scores))
    except Exception:
        pass

    return results


OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/era5"
BOGOTA = {"latitude": 4.7110, "longitude": -74.0721}


@st.cache_data(ttl=1800, max_entries=16, show_spinner=False)
def fetch_open_meteo_hourly(
    start_date: str,
    end_date: str,
    *,
    latitude: float = BOGOTA["latitude"],
    longitude: float = BOGOTA["longitude"],
) -> pd.DataFrame:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "surface_pressure",
                "windspeed_10m",
                "precipitation",
                "cloudcover",
            ]
        ),
        "timezone": "UTC",
    }
    r = requests.get(OPEN_METEO_ARCHIVE, params=params, timeout=20)
    r.raise_for_status()
    payload = r.json()
    hourly = payload.get("hourly", {})
    if not hourly:
        return pd.DataFrame()
    df = pd.DataFrame(hourly)
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
        df = df.rename(
            columns={
                "time": "weather_time",
                "temperature_2m": "temp_c",
                "relative_humidity_2m": "rh_pct",
                "surface_pressure": "pressure_hpa",
                "windspeed_10m": "wind_ms",
                "precipitation": "precip_mm",
                "cloudcover": "cloudcover_pct",
            }
        )
    return df


def fdr_bh(pvals: np.ndarray, alpha: float = 0.05) -> Tuple[np.ndarray, float]:
    p = np.asarray(pvals, dtype=float)
    m = p.size
    if m == 0:
        return p, alpha
    order = np.argsort(p)
    ordered = p[order]
    thresholds = alpha * (np.arange(1, m + 1) / m)
    reject = ordered <= thresholds
    if not reject.any():
        q = np.full_like(p, fill_value=np.nan, dtype=float)
        return q, alpha
    kmax = np.where(reject)[0].max()
    crit_p = ordered[kmax]
    # q-values (Benjamini–Hochberg adjusted p) monotone
    q = np.empty_like(ordered)
    min_coeff = 1.0
    for i in range(m - 1, -1, -1):
        min_coeff = min(min_coeff, m * ordered[i] / (i + 1))
        q[i] = min_coeff
    q = np.minimum(1.0, q)
    # revert to original order
    q_full = np.empty_like(q)
    q_full[order] = q
    return q_full, crit_p


def partial_pearson_r_p(
    x: np.ndarray, y: np.ndarray, cov: Optional[np.ndarray]
) -> Tuple[float, float, int]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if cov is not None and cov.size > 0:
        cov = np.asarray(cov, dtype=float)
        mask = mask & np.all(np.isfinite(cov), axis=1)
    x = x[mask]
    y = y[mask]
    if cov is not None and cov.size > 0:
        Z = cov[mask]
        Z = np.column_stack([np.ones(Z.shape[0]), Z])  # add intercept
        # residualize x and y on covariates (including intercept)
        beta_x, *_ = np.linalg.lstsq(Z, x, rcond=None)
        x_res = x - Z @ beta_x
        beta_y, *_ = np.linalg.lstsq(Z, y, rcond=None)
        y_res = y - Z @ beta_y
        return _pearson_r_p(x_res, y_res)
    else:
        return _pearson_r_p(x, y)


def _set_process_priority() -> None:
    """
    Set high priority for Python process to improve performance.
    
    Only works on Windows. On Linux/Mac, requires appropriate permissions.
    """
    try:
        import psutil
        p = psutil.Process(os.getpid())
        if os.name == "nt":  # Windows
            try:
                p.nice(psutil.HIGH_PRIORITY_CLASS)
                logger = logging.getLogger(__name__)
                logger.debug("Set process priority to HIGH_PRIORITY_CLASS")
            except (psutil.AccessDenied, AttributeError):
                pass  # Requires admin or not available
        else:  # Linux/Mac
            try:
                p.nice(-10)  # Higher priority (requires appropriate permissions)
                logger = logging.getLogger(__name__)
                logger.debug("Set process nice value to -10")
            except (psutil.AccessDenied, AttributeError):
                pass
    except ImportError:
        pass  # psutil not available


def _inject_sessioninfo_suppressor() -> None:
    """Minimal safety net for Streamlit error suppression.
    
    With Streamlit 1.36.0, most errors are avoided. This is a lightweight
    fallback that only targets known error modals without affecting
    legitimate UI elements like file uploaders or tabs.
    """
    # Minimal CSS - only hide error-specific toast containers
    st.markdown(
        """
        <style>
        /* Hide only error toast containers - not all alerts */
        div[data-testid="stToast"]:has([data-testid="stNotificationContentError"]),
        div[data-testid="stToastContainer"]:has([data-testid="stNotificationContentError"]) {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    logger: logging.Logger = setup_console_logging(logging.INFO)
    
    # Set high process priority for better performance (if available)
    _set_process_priority()
    
    # -------------------------------------------------------------------------
    # Initialize session state early to prevent race conditions
    # This helps prevent "Tried to use SessionInfo before initialized" errors
    # -------------------------------------------------------------------------
    if "_app_session_ready" not in st.session_state:
        st.session_state["_app_session_ready"] = True
    
    _inject_sessioninfo_suppressor()

    # Show error details in UI
    st.set_option("client.showErrorDetails", True)

    # ----------------------------------------------------------------------
    # Crew / Mission workspace selection (affects DB + per-subject file storage)
    # ----------------------------------------------------------------------
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
        # Prevent cross-mission user/session leakage.
        keep_keys = {"crew_active_mission", "_crew_previous_mission", "_debug_mode_enabled"}
        for key in list(st.session_state.keys()):
            if key not in keep_keys:
                st.session_state.pop(key, None)
        # Clear Streamlit caches so mission switching never reuses stale DB/data.
        try:
            st.cache_data.clear()
            st.cache_resource.clear()
        except Exception:
            pass
        log_rerun_trigger("mission_switch", from_mission=previous_mission, to_mission=active_mission)
        st.rerun()

    # ----------------------------------------------------------------------
    # Debug Mode Toggle (sidebar)
    # ----------------------------------------------------------------------
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
        
        if st.button("📋 Generate Debug Report", key="_generate_debug_report"):
            try:
                from logging_config import dump_debug_report
                report_path = dump_debug_report()
                st.success(f"Debug report saved: `{report_path}`")
            except Exception as exc:
                st.error(f"Failed to generate report: {exc}")
        
        st.caption("Debug logs: `logs/app.log`, `logs/errors.log`, `logs/streamlit.log`")

    # Apply neutral layout refinements (responsive margins, full-width
    # components) + suppress known Streamlit toast errors
    st.markdown(
        """
		<style>
		/* ================================================================
		   WORKAROUND: Hide "Bad message format" toast notifications
		   This is a known Streamlit issue with session initialization
		   that appears intermittently and is harmless but annoying.
		   See: https://github.com/streamlit/streamlit/issues/11500
		   ================================================================ */
		/* Hide all toast notifications - we use st.success/st.error instead */
		div[data-testid="stToast"],
		div[data-testid="stToastContainer"],
		div[data-baseweb="toast"],
		div[data-baseweb="toaster"],
		[class*="Toast"],
		[class*="toast"] {
			display: none !important;
			visibility: hidden !important;
			opacity: 0 !important;
			pointer-events: none !important;
			height: 0 !important;
			overflow: hidden !important;
			position: absolute !important;
			left: -9999px !important;
		}
		/* Target the toaster container at root level */
		.stToast, .element-container .stToast,
		div[role="alert"][data-baseweb="toast"] {
			display: none !important;
		}
		
		.stApp > main {
			padding-top: clamp(1rem, 4vh, 2rem);
			padding-bottom: clamp(2rem, 6vh, 3rem);
		}
		.block-container {
			max-width: min(1180px, 95vw) !important;
			margin: 0 auto !important;
			padding-left: clamp(1rem, 4vw, 2.5rem) !important;
			padding-right: clamp(1rem, 4vw, 2.5rem) !important;
			padding-top: clamp(1.25rem, 4vh, 2.5rem) !important;
			padding-bottom: clamp(1.8rem, 5vh, 3rem) !important;
		}
		@media (max-width: 960px) {
			.block-container {
				padding-left: 1.4rem !important;
				padding-right: 1.4rem !important;
			}
		}
		div[data-testid="stIFrame"],
		div[data-testid="stIFrame"] > iframe,
		[title~="st.iframe"] {
			width: 100% !important;
			min-width: 100% !important;
			border: none !important;
		}
		div[data-testid="stIFrame"] {
			display: block;
			flex: 1 1 auto;
		}
		[data-testid="stSidebar"] > div:first-child {
			padding: 2rem 1.25rem 2.2rem;
		}
		.stTabs [data-baseweb="tab-list"] {
			display: flex;
			flex-wrap: wrap;
			justify-content: center;
			gap: 0.5rem 0.65rem;
			padding: 0.75rem 0;
			overflow: visible !important;
		}
		.stTabs [data-baseweb="tab"] {
			border-radius: 999px;
			padding: 0.5rem 1.15rem;
			border: 1px solid rgba(17, 24, 39, 0.08);
			background: rgba(255, 255, 255, 0.72);
			box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
			transition: all 0.2s ease;
			flex: 0 0 auto;
		}
		.stTabs [data-baseweb="tab"]:hover {
			background: rgba(37, 99, 235, 0.12);
			border-color: rgba(37, 99, 235, 0.35);
		}
		.stTabs [data-baseweb="tab"][aria-selected="true"] {
			background: linear-gradient(135deg, rgba(37, 99, 235, 0.18), rgba(14, 165, 233, 0.18));
			border-color: rgba(37, 99, 235, 0.4);
			color: #0f172a !important;
			box-shadow: 0 4px 12px rgba(37, 99, 235, 0.18);
		}
		@media (max-width: 640px) {
			.stTabs [data-baseweb="tab-list"] {
				flex-wrap: nowrap;
				overflow-x: auto !important;
				justify-content: flex-start;
				scrollbar-width: thin;
			}
			.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
				height: 6px;
			}
			.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-thumb {
				background: rgba(15, 23, 42, 0.25);
				border-radius: 999px;
			}
		}

		/* -----------------------------------------------------------------
		   HRV custom palette (applies ONLY to our custom HTML boxes)
		   Palette:
		     - #F2F1EF  (paper)
		     - #D8CFD0  (mist)
		     - #B1A6A4  (stone)
		     - #697184  (slate)
		     - #413F3D  (ink)
		----------------------------------------------------------------- */
		.hrv-palette-banner {
			display: flex;
			align-items: center;
			gap: 12px;
			padding: 10px 14px;
			border-radius: 14px;
			background: linear-gradient(135deg, #F2F1EF 0%, #D8CFD0 100%);
			border: 1px solid #B1A6A4;
			border-left: 6px solid #697184;
			box-shadow: 0 8px 18px rgba(65, 63, 61, 0.08);
			color: #413F3D;
		}
		.hrv-palette-banner__dot {
			width: 10px;
			height: 10px;
			border-radius: 999px;
			background: #697184;
			box-shadow: 0 0 10px rgba(105, 113, 132, 0.55);
			flex: 0 0 auto;
		}
		.hrv-palette-banner__title {
			font-weight: 800;
			line-height: 1.2;
			color: #413F3D;
		}
		.hrv-palette-banner__subtitle {
			color: rgba(65, 63, 61, 0.82);
			font-size: 0.9rem;
		}
		.hrv-palette-card {
			display: flex;
			align-items: center;
			gap: 12px;
			padding: 12px 16px;
			border-radius: 14px;
			background: linear-gradient(135deg, #F2F1EF 0%, #D8CFD0 100%);
			border: 1px solid #B1A6A4;
			box-shadow: 0 8px 18px rgba(65, 63, 61, 0.08);
			color: #413F3D;
		}
		.hrv-palette-card__title {
			font-weight: 700;
			color: #413F3D;
		}
		.hrv-palette-card__value {
			font-size: 16px;
			color: #413F3D;
		}
		</style>
		<script>
		// ================================================================
		// JavaScript: Actively hide toast notifications as they appear
		// This catches toasts that CSS might miss due to timing
		// ================================================================
		(function() {
			'use strict';
			
			function hideToasts() {
				// Target all possible toast selectors
				var selectors = [
					'div[data-testid="stToast"]',
					'div[data-testid="stToastContainer"]',
					'div[data-baseweb="toast"]',
					'div[data-baseweb="toaster"]',
					'div[role="alert"]'
				];
				
				selectors.forEach(function(selector) {
					var elements = document.querySelectorAll(selector);
					elements.forEach(function(el) {
						// Check if it contains "Bad message" or "SessionInfo"
						var text = el.textContent || el.innerText || '';
						if (text.includes('Bad message') || text.includes('SessionInfo')) {
							el.style.display = 'none';
							el.style.visibility = 'hidden';
							el.style.opacity = '0';
							el.remove();
						}
					});
				});
			}
			
			// Run immediately
			hideToasts();
			
			// Set up MutationObserver to catch new toasts
			var observer = new MutationObserver(function(mutations) {
				hideToasts();
			});
			
			// Start observing when DOM is ready
			if (document.body) {
				observer.observe(document.body, { childList: true, subtree: true });
			} else {
				document.addEventListener('DOMContentLoaded', function() {
					observer.observe(document.body, { childList: true, subtree: true });
				});
			}
			
			// Also run periodically as a fallback
			setInterval(hideToasts, 500);
		})();
		</script>
		""",
        unsafe_allow_html=True,
    )
    # Professional welcome header
    if WELCOME_HEADER_AVAILABLE:
        render_welcome_header()
    else:
        st.title("🧬 Mission Control - Flight Surgeon")
        st.caption("Dr. Diego L. Malpica, MD — Aerospace Medicine Specialist")
        st.caption("Contributing to AsterPhysiology Research Initiative")

    # ---------------------------------------------------------------------
    # App mode banner + enforcement (Operational vs Research philosophy)
    # ---------------------------------------------------------------------
    try:
        from app_mode import AppMode, get_app_mode, render_app_mode_badge, set_app_mode  # noqa: PLC0415

        current_mode = get_app_mode(default=AppMode.RESEARCH)
        if current_mode != AppMode.RESEARCH:
            # Enforce "fast operational app" philosophy by blocking research dashboards.
            set_app_mode(current_mode)
            render_app_mode_badge(current_mode)
            st.error(
                "This interface is **Research** (full dashboards: correlations/ML/NOAA/Space Weather). "
                "Operational mode locks these features to keep the clinical UI fast and stable."
            )
            st.code("streamlit run app/operational_app.py")
            st.stop()

        # Default: research mode.
        set_app_mode(AppMode.RESEARCH)
        render_app_mode_badge(AppMode.RESEARCH)
        # Red warning box directly below the mode badge (user-requested placement).
        st.markdown(
            """
            <div class="hrv-palette-banner" style="margin:0 0 14px 0;">
                <div class="hrv-palette-banner__dot"></div>
                <div>
                    <div class="hrv-palette-banner__title">
                        ⚠️ Heavy Computations
                    </div>
                    <div class="hrv-palette-banner__subtitle">
                        Space Weather/NOAA correlations and ML take time. Let fetches complete—results appear when ready.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        # Mode banner is non-critical; never block the research UI if it fails.
        pass
    
    # Initialize UI state manager for tracking data availability
    if UI_STATE_MANAGER_AVAILABLE:
        update_data_status_from_session()
    
    # Hard logout guard: if the user explicitly logged out, ensure we do not
    # accidentally keep/restore any profile in this run.
    if st.session_state.get("user_logged_out"):
        st.session_state.pop("current_user_profile", None)
        st.session_state.pop("current_user_id", None)

    active_profile = _resolve_active_profile(logger)
    active_user_id, active_display_name = _get_user_identity(active_profile)
    st.markdown(
        f"""
        <div class="hrv-palette-card" style="margin-bottom:12px;">
            <span style="font-size:32px;color:#697184;">💡</span>
            <div>
                <div class="hrv-palette-card__title">Active Profile for Analysis</div>
                <div class="hrv-palette-card__value">{active_display_name}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Initialize uploads dictionary
    uploads: Dict[str, UploadedRR] = {}

    # =========================================================================
    # LIBRARY LOADER - Load previously saved RR files from user profiles
    # =========================================================================
    # Render library loader in sidebar (before upload section)
    _render_library_loader()

    # PRIMARY: Device imports (Polar, Garmin, etc.) - in sidebar
    if DEVICE_IMPORTS_AVAILABLE:
        imported_devices = render_primary_import_section()
        # Convert ImportedRRData to UploadedRR format for compatibility
        for device_name, data in imported_devices.items():
            if data.sample_count > 0:
                # Convert datetime to pd.Timestamp if needed
                if data.recording_start is not None:
                    start_ts = pd.Timestamp(data.recording_start)
                else:
                    start_ts = pd.Timestamp.now(tz=timezone.utc)
                df = _to_dataframe(
                    device_name,
                    data.rr_intervals_ms,
                    start_ts=start_ts,
                )
                uploads[device_name] = UploadedRR(
                    name=device_name,
                    rr_ms=data.rr_intervals_ms,
                    df=df,
                    recording_start_utc=start_ts,
                )
        # Note: render_primary_import_section already handles ActiGraph and Somfit
    else:
        # Fallback to legacy upload section if device imports unavailable
        uploads = _upload_section()

        # Legacy device-specific imports (ActiGraph GT3X, Somfit Pro)
        device_uploads = _device_import_section()
        uploads.update(device_uploads)

    # Include queued uploads from the profile tab (stored in session state)
    queued_profile_uploads = st.session_state.pop("queued_rr_uploads", [])
    for queued in queued_profile_uploads:
        try:
            rr_ms = np.array(queued.get("rr_ms", []), dtype=float)
            if rr_ms.size < 10:
                continue
            start_raw = queued.get("recording_start")
            start_ts = pd.to_datetime(start_raw, errors="coerce")
            if isinstance(start_ts, pd.Timestamp) and not pd.isna(start_ts):
                if start_ts.tzinfo is None or start_ts.tzinfo.utcoffset(start_ts) is None:
                    start_ts = start_ts.tz_localize(timezone.utc)
                else:
                    start_ts = start_ts.tz_convert(timezone.utc)
            else:
                start_ts = pd.Timestamp.now(tz=timezone.utc)
            name = queued.get("name") or f"queued_{len(uploads)+1}"
            df = _to_dataframe(name, rr_ms, start_ts=start_ts)
            uploads[name] = UploadedRR(
                name=name,
                rr_ms=rr_ms,
                df=df,
                recording_start_utc=start_ts,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Skipped queued upload due to error: %s", exc)

    # Include queued RR file paths from profile storage (avoid large arrays in session state)
    queued_profile_paths = st.session_state.pop("queued_rr_filepaths", [])
    for queued in queued_profile_paths:
        try:
            path_str = str(queued.get("path") or "")
            if not path_str:
                continue
            p = Path(path_str)
            if not p.exists():
                continue
            try:
                mtime_ns = int(p.stat().st_mtime_ns)
            except OSError:
                continue
            rr_ms = _cached_rr_from_path(str(p), mtime_ns)
            if rr_ms.size < 10:
                continue

            start_raw = queued.get("recording_start")
            start_ts = pd.to_datetime(start_raw, errors="coerce")
            if isinstance(start_ts, pd.Timestamp) and not pd.isna(start_ts):
                if start_ts.tzinfo is None or start_ts.tzinfo.utcoffset(start_ts) is None:
                    start_ts = start_ts.tz_localize(timezone.utc)
                else:
                    start_ts = start_ts.tz_convert(timezone.utc)
            else:
                parsed_date = parse_filename_date(p.name) or date.today()
                start_ts = pd.Timestamp(
                    datetime.combine(parsed_date, datetime.min.time(), tzinfo=timezone.utc)
                )

            name = str(queued.get("name") or p.name)
            # Ensure unique name within this run
            base = name
            idx = 2
            while name in uploads:
                name = f"{base} ({idx})"
                idx += 1

            df = _to_dataframe(name, rr_ms, start_ts=start_ts)
            uploads[name] = UploadedRR(
                name=name,
                rr_ms=rr_ms,
                df=df,
                recording_start_utc=start_ts,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Skipped queued RR path due to error: %s", exc)
    
    _persist_raw_uploads(logger, active_profile, uploads)
    
    file_hash_map: Dict[str, str] = {}
    duplicate_measurements: Dict[str, HRVMeasurement] = {}
    stored_payloads: Dict[str, Dict[str, Any]] = {}
    mismatched_cached: List[str] = []
    reuse_cached_results = False
    db_instance: Optional[Any] = None
    if active_user_id:
        try:
            db_instance = get_database()
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Database not available for duplicate detection: %s", exc)
    for name, up in uploads.items():
        try:
            rr_hash = compute_rr_hash(up.rr_ms)
        except Exception:
            rr_hash = _compute_file_hash(up.rr_ms.tobytes())
        file_hash_map[name] = rr_hash
        if db_instance is not None and active_user_id:
            try:
                existing_meas = db_instance.get_measurement_by_hash(active_user_id, rr_hash)
                if existing_meas is not None:
                    duplicate_measurements[name] = existing_meas
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Hash lookup failed for %s: %s", name, exc)

    # =========================================================================
    # PERSIST UPLOADS - Keep uploads in session state across reruns
    # =========================================================================
    # Store current uploads for persistence (so they survive after queue is popped)
    if uploads:
        st.session_state["_persisted_uploads"] = uploads
    elif "_persisted_uploads" in st.session_state:
        # Restore from persisted uploads if current run has none
        # (This happens after queue is popped on subsequent reruns)
        uploads = st.session_state["_persisted_uploads"]
    
    # Initialize flag for data availability - used throughout for conditional rendering
    has_hrv_data_uploaded = bool(uploads)

    # ==========================================================================
    # SIDEBAR CONTROLS - Show HRV settings only when data is available
    # ==========================================================================
    if has_hrv_data_uploaded:
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚙️ Analysis Settings")
        
        # Controls
        col_a, col_b, col_c = st.sidebar.columns(3)
        with col_a:
            win = st.text_input("Window", "5min")
        with col_b:
            step = st.text_input("Step", "1min")
        with col_c:
            min_rr = st.number_input(
                "Min RR per window",
                min_value=30,
                max_value=1000,
                value=60,
                step=10)
        max_windows = st.sidebar.number_input(
            "Max windows (for long tracings)",
            min_value=200,
            max_value=20000,
            value=1500,
            step=100,
        )

        # QC controls
        st.sidebar.markdown("---")
        st.sidebar.subheader("Data Quality")
        apply_clean = st.sidebar.checkbox("Apply artifact correction", value=True)
        method = st.sidebar.selectbox(
            "QC method", ["threshold_median", "threshold_prev"], index=0
        )
        max_dev = st.sidebar.slider(
            "Deviation threshold",
            min_value=0.05,
            max_value=0.5,
            value=0.2,
            step=0.05)
        median_win = st.sidebar.number_input(
            "Median window (odd)", min_value=3, max_value=99, value=11, step=2
        )
        psd_method = st.sidebar.selectbox(
            "PSD method", ["welch", "periodogram", "ar"], index=0
        )
        fast_windowing = st.sidebar.checkbox(
            "Fast time-domain windowing (skip spectral/nonlinear in windows)", value=True)
        high_compute = st.sidebar.checkbox(
            "Advanced analysis (high compute for full-recording metrics)",
            value=False)
        st.sidebar.markdown("---")
        st.sidebar.subheader("Deviation detection")
        apply_dev = st.sidebar.checkbox(
            "Detect deviations in windowed metrics", value=True)
        dev_metrics = st.sidebar.multiselect(
            "Metrics to monitor",
            options=["rmssd", "sdnn", "lf_hf_ratio", "hf_power"],
            default=["rmssd", "sdnn", "lf_hf_ratio", "hf_power"],
        )
        z_warn = st.sidebar.slider(
            "Warn threshold (|z|)",
            min_value=0.5,
            max_value=3.0,
            value=1.0,
            step=0.1)
        z_alert = st.sidebar.slider(
            "Alert threshold (|z|)",
            min_value=1.0,
            max_value=5.0,
            value=2.0,
            step=0.1)
        min_sustain = st.sidebar.number_input(
            "Min windows to define an episode",
            min_value=1,
            max_value=60,
            value=3,
            step=1)
        st.sidebar.markdown("---")
        st.sidebar.subheader("Performance & display")
        minimal_mode = st.sidebar.checkbox("Minimal mode (fastest)", value=False)
        max_datasets = st.sidebar.number_input(
            "Process first N datasets (cap 30)",
            min_value=1,
            max_value=30,
            value=30,
            step=1,
        )
        rr_plot_cap = st.sidebar.selectbox(
            "RR plot point cap per dataset", [
                "500", "2000", "10000", "No limit"], index=0)
        # Check performance settings for heavy computations
        freq_enabled = is_computation_enabled("frequency_domain")
        nonlinear_enabled = is_computation_enabled("nonlinear")
        spectrogram_enabled = is_computation_enabled("spectrogram")
        
        skip_freq = st.sidebar.checkbox(
            "Skip Frequency overlay plot",
            value=not freq_enabled,
            help="Disabled in low-end mode" if not freq_enabled else None,
        )
        skip_poincare = st.sidebar.checkbox(
            "Skip Poincaré plot",
            value=not nonlinear_enabled,
            help="Disabled in low-end mode" if not nonlinear_enabled else None,
        )
        skip_spectrogram = st.sidebar.checkbox(
            "Skip Spectrogram",
            value=not spectrogram_enabled,
            help="Disabled in low-end mode (CPU-intensive)" if not spectrogram_enabled else None,
        )
        skip_gauges = st.sidebar.checkbox("Skip Gauges", value=False)
        show_debug = st.sidebar.checkbox(
            "Show detailed progress logs", value=False)
        # Adjust runtime log verbosity from sidebar preference
        logger.setLevel(logging.DEBUG if show_debug else logging.INFO)
        for _handler in logger.handlers:
            _handler.setLevel(logger.level)

        st.sidebar.subheader("ML enhancements")
        # Check performance settings for ML clustering
        ml_enabled_by_perf = is_computation_enabled("ml_clustering")
        enable_ml = st.sidebar.checkbox(
            "Enable ML-assisted deviation clustering",
            value=ml_enabled_by_perf,
            disabled=not ml_enabled_by_perf,
            help="Disabled in low-end performance mode. Enable in Performance Settings → Custom." if not ml_enabled_by_perf else "K-means clustering for HRV pattern detection",
        )
        
        # Performance settings (CPU optimization)
        if PERFORMANCE_UTILS_AVAILABLE:
            perf_settings = render_performance_settings_sidebar()
        else:
            perf_settings = {
                "max_plot_points": 2000,
                "max_dataframe_rows": 500,
                "enable_heavy_plots": False,
                "optimize_memory": True,
            }
        
        # GPU processing settings (NVIDIA CUDA)
        if GPU_PROCESSING_AVAILABLE:
            gpu_config = render_gpu_settings_sidebar()
        else:
            gpu_config = None

        st.sidebar.markdown("---")
        st.sidebar.subheader("AI interpretation")
        st.sidebar.caption(
            "OpenAI/Agents analysis is **on-demand** and only runs from the **Export & Download** tab."
        )

        st.sidebar.markdown("---")
        st.sidebar.subheader("Patient profile (covariate adjustment)")
        # Default to active user profile context when available.
        try:
            _sidebar_user_ctx = get_active_user_context()
        except Exception:
            _sidebar_user_ctx = _guest_user_context()
        _sidebar_uid = (
            str(_sidebar_user_ctx.get("user_id"))
            if _sidebar_user_ctx.get("has_user") and _sidebar_user_ctx.get("user_id")
            else "guest"
        )
        enable_cov = st.sidebar.checkbox(
            "Enable covariate adjustment (RMSSD/SDNN)",
            value=False,
            key=f"cov_enable_{_sidebar_uid}",
        )
        use_profile_cov = st.sidebar.toggle(
            "Use active profile defaults",
            value=bool(_sidebar_user_ctx.get("has_user")),
            key=f"cov_use_profile_{_sidebar_uid}",
            help="When enabled, age/sex/BMI/activity default to the active user profile.",
        )
        _default_age = int(_sidebar_user_ctx.get("age_years") or 45)
        _default_bmi = float(_sidebar_user_ctx.get("bmi") or 25.0)
        _sex_ctx = str(_sidebar_user_ctx.get("sex") or "other").lower()
        if _sex_ctx.startswith("m"):
            _default_sex = "Male"
        elif _sex_ctx.startswith("f"):
            _default_sex = "Female"
        else:
            _default_sex = "Other"
        _activity_ctx = str(_sidebar_user_ctx.get("activity_level") or "").lower()
        if "athlete" in _activity_ctx or "very" in _activity_ctx or "extreme" in _activity_ctx:
            _default_exercise = "Athlete"
        elif "sedentary" in _activity_ctx:
            _default_exercise = "Sedentary"
        else:
            _default_exercise = "Moderate"

        age_years = st.sidebar.number_input(
            "Age (years)",
            min_value=10,
            max_value=100,
            value=_default_age,
            step=1,
            key=f"cov_age_{_sidebar_uid}",
            disabled=bool(use_profile_cov and _sidebar_user_ctx.get("has_user")),
        )
        sex = st.sidebar.selectbox(
            "Sex",
            ["Female", "Male", "Other"],
            index=["Female", "Male", "Other"].index(_default_sex),
            key=f"cov_sex_{_sidebar_uid}",
            disabled=bool(use_profile_cov and _sidebar_user_ctx.get("has_user")),
        )
        bmi = st.sidebar.number_input(
            "BMI (kg/m²)",
            min_value=10.0,
            max_value=60.0,
            value=_default_bmi,
            step=0.5,
            key=f"cov_bmi_{_sidebar_uid}",
            disabled=bool(use_profile_cov and _sidebar_user_ctx.get("has_user")),
        )
        exercise = st.sidebar.selectbox(
            "Exercise regularity",
            ["Sedentary", "Moderate", "Athlete"],
            index=["Sedentary", "Moderate", "Athlete"].index(_default_exercise),
            key=f"cov_exercise_{_sidebar_uid}",
            disabled=bool(use_profile_cov and _sidebar_user_ctx.get("has_user")),
        )

        # Apply minimal mode overrides to ensure fastest behavior by default
        if minimal_mode:
            max_datasets = 1
            rr_plot_cap = "500"
            skip_freq = True
            skip_poincare = True
            skip_spectrogram = True
            skip_gauges = True
            fast_windowing = True
            high_compute = False
            max_windows = min(int(max_windows), 800)
            enable_ml = False
            st.sidebar.caption(
                "Minimal mode: processing 1 dataset, fast time-domain windowing, heavy plots/tabs skipped."
            )

        analysis_settings = _build_analysis_settings(
            window=win,
            step=step,
            min_rr=int(min_rr),
            max_windows=int(max_windows),
            apply_clean=bool(apply_clean),
            method=str(method),
            max_dev=float(max_dev),
            median_win=int(median_win),
            psd_method=str(psd_method),
            fast_windowing=bool(fast_windowing),
            high_compute=bool(high_compute),
            apply_dev=bool(apply_dev),
            dev_metrics=dev_metrics,
            covariate_enabled=bool(enable_cov),
            covariate_age=int(age_years),
            covariate_sex=str(sex),
            covariate_bmi=float(bmi),
            covariate_exercise=str(exercise),
        )
        if duplicate_measurements:
            st.sidebar.warning(
                "These files were already analyzed for the active profile. "
                "You can still recompute or proceed to reuse stored results."
            )
            for dup_name, dup_meas in duplicate_measurements.items():
                st.sidebar.caption(
                    f"• {dup_name} (analyzed {dup_meas.measurement_date})"
                )
            reuse_cached_results = st.sidebar.checkbox(
                "Reuse stored HRV results when the file hash matches",
                value=True,
                help="If enabled, previously computed HRV results with the same file hash and settings are reloaded instead of recomputed.",
            )
            if reuse_cached_results and active_user_id:
                # Prefer SQLite-backed cache (user_database) before filesystem cache.
                analysis_settings_hash = ""
                try:
                    _db = get_database()
                    analysis_settings_hash = _db.compute_settings_hash(analysis_settings)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.debug("Unable to compute settings hash for DB cache: %s", exc)
                    analysis_settings_hash = ""
                try:
                    reuse_manager = create_user_manager()
                    reuse_manager.set_current_user(
                        user_id=active_user_id,
                        name=active_display_name or "User",
                        create_if_missing=True,
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    logger.debug("Unable to load cached HRV results: %s", exc)
                    reuse_cached_results = False
                    reuse_manager = None
                if reuse_cached_results and reuse_manager is not None:
                    for dup_name in duplicate_measurements:
                        file_hash = file_hash_map.get(dup_name)
                        if not file_hash:
                            continue
                        try:
                            payload = None
                            if analysis_settings_hash:
                                payload = _db.get_hrv_analysis_cache_payload(
                                    user_id=active_user_id,
                                    file_hash=file_hash,
                                    analysis_settings_hash=analysis_settings_hash,
                                )
                            if payload is None:
                                payload = reuse_manager.load_hrv_results_by_hash(file_hash)
                        except Exception as exc:  # pragma: no cover - defensive
                            logger.debug(
                                "Failed to read cached results for %s: %s", dup_name, exc
                            )
                            continue
                        if payload and _analysis_settings_match(
                            payload.get("analysis_settings", {}), analysis_settings
                        ):
                            stored_payloads[dup_name] = payload
                        elif payload:
                            mismatched_cached.append(dup_name)
            if stored_payloads:
                st.sidebar.info(
                    f"Reusing stored analysis for: {', '.join(sorted(stored_payloads))}"
                )
            if mismatched_cached:
                st.sidebar.warning(
                    "Stored results exist but analysis settings changed; those files will be recomputed."
                )
    else:
        # Default values when no data uploaded - needed for tab rendering
        # All defaults set for FAST MODE to maximize performance
        win = "5min"
        step = "2min"  # Faster: larger step = fewer windows
        min_rr = 60
        max_windows = 500  # Fast mode: reduced from 1500
        apply_clean = True
        method = "threshold_median"
        max_dev = 0.2
        median_win = 11
        psd_method = "welch"
        fast_windowing = True  # Fast mode: skip spectral in windows
        high_compute = False  # Fast mode: no advanced analysis
        apply_dev = True
        dev_metrics = ["rmssd", "sdnn", "lf_hf_ratio", "hf_power"]
        z_warn = 1.0
        z_alert = 2.0
        min_sustain = 3
        minimal_mode = True  # Fast mode: always start minimal
        max_datasets = 1  # Fast mode: process only 1 dataset
        rr_plot_cap = "500"  # Fast mode: limit plot points
        skip_freq = True  # Fast mode: skip heavy plots
        skip_poincare = True  # Fast mode: skip heavy plots
        skip_spectrogram = True  # Fast mode: skip heavy plots
        skip_gauges = True  # Fast mode: skip gauges
        show_debug = False
        enable_ml = False  # Fast mode: no ML clustering
        enable_cov = False  # Fast mode: no covariate adjustment
        age_years = 45
        sex = "Male"
        bmi = 29.0
        exercise = "Sedentary"
        
        # Performance settings (CPU optimization) - available even without data
        if PERFORMANCE_UTILS_AVAILABLE:
            perf_settings = render_performance_settings_sidebar()
        else:
            perf_settings = {
                "max_plot_points": 2000,
                "max_dataframe_rows": 500,
                "enable_heavy_plots": False,
                "optimize_memory": True,
            }
        
        # GPU processing settings (NVIDIA CUDA) - available even without data
        if GPU_PROCESSING_AVAILABLE:
            gpu_config = render_gpu_settings_sidebar()
        else:
            gpu_config = None
        
        # Show exploration callout in sidebar
        st.sidebar.markdown("---")
        st.sidebar.info(
            "📖 **Explore the App**\n\n"
            "No data required to explore:\n"
            "- 👤 User Profile\n"
            "- 🌍 Space Weather\n"
            "- ☀️ Circadian Models\n"
            "- 😴 SAFTE/Fatigue\n"
            "- 🫀 Biofeedback Demo\n\n"
            "Upload HRV data to unlock all analysis tabs."
        )

    # ==========================================================================
    # DATA PROCESSING - Only when uploads exist
    # ==========================================================================
    # Initialize defaults for all data-dependent variables
    datasets: Dict[str, UploadedRR] = {}
    meta_rows: List[Dict[str, Any]] = []
    windowed_df = pd.DataFrame()
    multi_results_df = pd.DataFrame()
    ml_summary_df = pd.DataFrame()
    ml_error_message = ""
    episodes_df = pd.DataFrame()
    meta_rows_for_context: List[Dict[str, Any]] = []

    # Require explicit user action to run HRV analysis
    auto_run_requested = bool(st.session_state.pop("auto_run_hrv_analysis", False))
    hrv_analysis_ready = st.session_state.get("hrv_analysis_ready", False)
    hrv_complete_sig = st.session_state.get("hrv_analysis_complete_signature")
    upload_signature = tuple(sorted(uploads.keys())) if has_hrv_data_uploaded else tuple()
    if st.session_state.get("hrv_analysis_signature") != upload_signature:
        st.session_state["hrv_analysis_signature"] = upload_signature
        hrv_analysis_ready = False
        st.session_state["hrv_analysis_ready"] = False
        # Clear cached results when uploads change
        st.session_state.pop("_hrv_cached_datasets", None)
        st.session_state.pop("_hrv_cached_windowed_df", None)
        st.session_state.pop("_hrv_cached_multi_results_df", None)
        st.session_state.pop("_hrv_cached_meta_rows", None)
        st.session_state.pop("_hrv_cached_meta_rows_for_context", None)
        st.session_state.pop("_hrv_cached_ml_summary_df", None)
        st.session_state.pop("_hrv_cached_episodes_df", None)
        # Clear completion signature to allow new analysis
        st.session_state.pop("hrv_analysis_complete_signature", None)
    # Prevent repeated runs for the same upload set once completed
    analysis_already_completed = bool(
        has_hrv_data_uploaded and hrv_complete_sig == upload_signature
    )
    if analysis_already_completed:
        hrv_analysis_ready = False
        st.session_state["hrv_analysis_ready"] = False
        # CRITICAL FIX: Restore datasets from cache when analysis already completed
        # Without this, tabs try to render with empty datasets causing infinite loading
        cached_datasets = st.session_state.get("_hrv_cached_datasets")
        if cached_datasets:
            datasets = cached_datasets
        cached_windowed = st.session_state.get("_hrv_cached_windowed_df")
        if cached_windowed is not None and not cached_windowed.empty:
            windowed_df = cached_windowed
        cached_multi = st.session_state.get("_hrv_cached_multi_results_df")
        if isinstance(cached_multi, pd.DataFrame) and not cached_multi.empty:
            multi_results_df = cached_multi
        cached_meta = st.session_state.get("_hrv_cached_meta_rows")
        if isinstance(cached_meta, list) and cached_meta:
            meta_rows = cached_meta
        cached_meta_context = st.session_state.get("_hrv_cached_meta_rows_for_context")
        if isinstance(cached_meta_context, list) and cached_meta_context:
            meta_rows_for_context = cached_meta_context
        cached_ml_summary = st.session_state.get("_hrv_cached_ml_summary_df")
        if isinstance(cached_ml_summary, pd.DataFrame) and not cached_ml_summary.empty:
            ml_summary_df = cached_ml_summary
        cached_episodes = st.session_state.get("_hrv_cached_episodes_df")
        if isinstance(cached_episodes, pd.DataFrame) and not cached_episodes.empty:
            episodes_df = cached_episodes
        #region agent log
        _agent_debug_log(
            "H6",
            "app.py:hrv_analysis",
            "skip_already_completed",
            {
                "upload_signature": upload_signature,
                "hrv_complete_sig": hrv_complete_sig,
            },
        )
        #endregion

    # Optional: allow other panels (e.g., User Profile) to trigger a one-shot run.
    if auto_run_requested and has_hrv_data_uploaded:
        st.session_state["hrv_analysis_complete_signature"] = None
        st.session_state["hrv_analysis_ready"] = True
        hrv_analysis_ready = True
        analysis_already_completed = False
    
    # Always show the button when data is uploaded, regardless of analysis state
    # This prevents the button from blanking out and ensures it's always accessible
    if has_hrv_data_uploaded:
        if not hrv_analysis_ready:
            if analysis_already_completed:
                st.info(
                    "HRV analysis already completed for this upload set. "
                    "You can switch tabs (e.g., **User Profile**) or click **Recompute HRV Analysis** to rerun."
                )
            else:
                st.info("HRV data uploaded. Click **Run HRV Analysis** to start processing.")
        
        # Show button with consistent text based on completion state
        button_text = "🔁 Recompute HRV Analysis" if analysis_already_completed else "🚀 Run HRV Analysis"
        if st.button(
            button_text,
            key="run_hrv_analysis",
            type="primary",
            help="Runs HRV cleaning, windowing, and metric computation for uploaded datasets.",
        ):
            hrv_analysis_ready = True
            st.session_state["hrv_analysis_ready"] = True
            # Clear completion signature to allow recomputation
            if analysis_already_completed:
                st.session_state.pop("hrv_analysis_complete_signature", None)
                # Clear cached results to force recomputation
                st.session_state.pop("_hrv_cached_datasets", None)
                st.session_state.pop("_hrv_cached_windowed_df", None)
                st.session_state.pop("_hrv_cached_multi_results_df", None)
                st.session_state.pop("_hrv_cached_meta_rows", None)
                st.session_state.pop("_hrv_cached_meta_rows_for_context", None)
                st.session_state.pop("_hrv_cached_ml_summary_df", None)
                st.session_state.pop("_hrv_cached_episodes_df", None)
    
    if has_hrv_data_uploaded and hrv_analysis_ready:
        # Prepare dataset dict (limit number of datasets for performance)
        datasets_all = uploads
        dataset_items = list(datasets_all.items())
        datasets = dict(dataset_items[: int(max_datasets)])

        # ===================================================================
        # PERFORMANCE OPTIMIZATION: Use cached cleaning results when available
        # ===================================================================
        # Bind cache to selected user profile to avoid cross-user mixing
        profile_id = None
        if st.session_state.get("current_user_profile"):
            prof = st.session_state["current_user_profile"]
            # Support both dict and dataclass/object with user_id attribute
            if isinstance(prof, dict):
                profile_id = prof.get("user_id")
            else:
                profile_id = getattr(prof, "user_id", None)

        # Check if we can skip computation entirely (same data + settings + profile)
        _skip_compute = False
        if HRV_CACHE_AVAILABLE:
            _skip_compute = should_skip_computation(
                datasets,
                str(method),
                float(max_dev),
                int(median_win),
                win,
                step,
                profile_id=profile_id,
            )
            if _skip_compute:
                logger.debug("Skipping cleaning - results already cached with same settings/profile")
        
        # Cleaning + metadata with immediate percentage updates (no progress bars)
        total = max(1, len(datasets))
        txt_clean = st.empty()
        prog_clean = st.progress(0)
        # Only show progress if not using cached results
        if not _skip_compute:
            txt_clean.markdown(
                f"### {'Cleaning' if apply_clean else 'Preparing'} datasets... 0%"
            )
            logger.info(
                "Starting %s of %d dataset(s)",
                "cleaning" if apply_clean else "preparation",
                total,
            )
        else:
            txt_clean.markdown("### Loading cached results... 100%")
            prog_clean.progress(100)
        #region agent log
        _agent_debug_log(
            "H6",
            "app.py:hrv_analysis",
            "clean_phase_start",
            {
                "dataset_count": len(datasets),
                "skip_compute": bool(_skip_compute),
                "apply_clean": bool(apply_clean),
                "win": win,
                "step": step,
                "max_datasets": int(max_datasets),
            },
        )
        #endregion
        
        completed = 0
        for name, up in datasets.items():
            if up.rr_ms.size == 0:
                completed += 1
                if not _skip_compute:
                    percent = min(100, int(completed * 100 / total))
                    txt_clean.markdown(
                        f"### {'Cleaning' if apply_clean else 'Preparing'} datasets... {percent}%"
                    )
                    prog_clean.progress(percent)
                continue
            if apply_clean:
                # Use cached cleaning when available for performance
                if HRV_CACHE_AVAILABLE:
                    cleaned, valid_mask, summary = get_cached_clean_rr(
                        name,
                        up.rr_ms,
                        str(method),
                        float(max_dev),
                        int(median_win),
                        clean_rr_intervals,  # Pass the function for cache misses
                    )
                else:
                    # Fallback to direct call if caching unavailable
                    cleaned, valid_mask, summary = clean_rr_intervals(
                        up.rr_ms,
                        method=str(method),
                        max_deviation=float(max_dev),
                        median_window=int(median_win),
                    )
                up.rr_ms_clean = cleaned
                up.artifact_valid_mask = valid_mask
                up.qc_summary = summary
                if not up.df.empty:
                    n = min(len(up.df), cleaned.size)
                    up.df.loc[: n - 1, "rr_intervals_ms_clean"] = cleaned[:n]
                    if valid_mask.size >= n:
                        up.df.loc[: n - 1, "artifact_flag"] = ~valid_mask[:n]
                    else:
                        up.df["artifact_flag"] = False
            start_iso = ""
            if isinstance(up.recording_start_utc, pd.Timestamp):
                start_ts = up.recording_start_utc
                if start_ts.tzinfo is None or start_ts.tzinfo.utcoffset(start_ts) is None:
                    start_ts = start_ts.tz_localize(timezone.utc)
                else:
                    start_ts = start_ts.tz_convert(timezone.utc)
                start_iso = start_ts.isoformat()
            meta_entry = {
                "source": name,
                "beats": int(up.rr_ms.size),
                "duration_min": float(up.rr_ms.sum() / (1000.0 * 60.0)),
                "mean_hr": float(np.mean(60000.0 / up.rr_ms)),
                "flagged_pct": (
                    float(up.qc_summary.get("flagged_pct", 0.0))
                    if (apply_clean and up.qc_summary)
                    else 0.0
                ),
            }
            if start_iso:
                meta_entry["recording_start_utc"] = start_iso
            meta_rows.append(meta_entry)
            completed += 1
            if not _skip_compute:
                percent = min(100, int(completed * 100 / total))
                txt_clean.markdown(
                    f"### {'Cleaning' if apply_clean else 'Preparing'} datasets... {percent}%"
                )
                prog_clean.progress(percent)
        
        if not _skip_compute:
            logger.info(
                "Finished %s of %d dataset(s)",
                "cleaning" if apply_clean else "preparation",
                total,
            )
        txt_clean.markdown(
            f"### {'Cleaning' if apply_clean else 'Preparation'} complete. 100%"
        )
        prog_clean.progress(100)
        
        # Update computation state for next rerun
        if HRV_CACHE_AVAILABLE:
            cache_mgr = get_cache_manager()
            state = cache_mgr.get_computation_state()
            try:
                files_hash = cache_mgr.compute_all_uploads_hash(datasets, profile_id=profile_id)
            except TypeError:
                files_hash = cache_mgr.compute_all_uploads_hash(datasets)
            settings_hash = compute_settings_hash(
                str(method), float(max_dev), int(median_win), win, step
            )
            state.mark_complete(files_hash, settings_hash, cleaning=True)
            cache_mgr.update_computation_state(state)

        # Windowed metrics computation with optional parallel processing
        windowed_all: List[pd.DataFrame] = []
        txt_win = st.empty()
        prog_win = st.progress(0)
        txt_win.markdown("### Computing windowed metrics... 0%")
        total_win = max(1, len(datasets))
        
        # Check if parallel processing should be enabled
        use_parallel = False
        max_workers = 1
        if PERFORMANCE_UTILS_AVAILABLE:
            try:
                from cpu_optimization import get_adaptive_settings
                adaptive = get_adaptive_settings()
                use_parallel = adaptive.use_parallel and len(datasets) > 1
                max_workers = min(adaptive.n_workers, len(datasets), os.cpu_count() or 2)
            except Exception:
                pass
        if stored_payloads:
            use_parallel = False
        
        if use_parallel and max_workers > 1:
            # Parallel processing for multiple datasets
            def compute_windowed_for_dataset(item: Tuple[str, Any]) -> Tuple[str, Optional[pd.DataFrame]]:
                name, up = item
                try:
                    wdf = _cached_windowed(
                        up.df,
                        rr_col=(
                            "rr_intervals_ms_clean"
                            if (apply_clean and "rr_intervals_ms_clean" in up.df.columns)
                            else "rr_intervals_ms"
                        ),
                        window=win,
                        step=step,
                        min_rr_count=int(min_rr),
                        max_windows=int(max_windows),
                        include_advanced=not bool(fast_windowing),
                    )
                    return (name, wdf if not wdf.empty else None)
                except Exception as exc:
                    logger.warning("Windowed computation failed for %s: %s", name, exc)
                    return (name, None)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(compute_windowed_for_dataset, item): item[0]
                    for item in datasets.items()
                }
                done_win = 0
                for future in concurrent.futures.as_completed(futures):
                    name, wdf = future.result()
                    if wdf is not None:
                        windowed_all.append(wdf.assign(source=name))
                    done_win += 1
                    percent = min(100, int(done_win * 100 / total_win))
                    txt_win.markdown(f"### Computing windowed metrics... {percent}%")
                    prog_win.progress(percent)
        else:
            # Sequential processing (original code path)
            done_win = 0
            for name, up in datasets.items():
                reuse_success = False
                if reuse_cached_results and name in stored_payloads:
                    cached_windowed = stored_payloads[name].get("windowed_df", {})
                    if cached_windowed:
                        try:
                            wdf = pd.DataFrame(cached_windowed)
                            if not wdf.empty:
                                windowed_all.append(wdf.assign(source=name))
                                reuse_success = True
                        except Exception as exc:  # pragma: no cover - defensive
                            logger.debug(
                                "Cached windowed results invalid for %s: %s", name, exc
                            )
                if reuse_success:
                    done_win += 1
                    percent = min(100, int(done_win * 100 / total_win))
                    txt_win.markdown(f"### Computing windowed metrics... {percent}%")
                    prog_win.progress(percent)
                    continue

                wdf = _cached_windowed(
                    up.df,
                    rr_col=(
                        "rr_intervals_ms_clean"
                        if (apply_clean and "rr_intervals_ms_clean" in up.df.columns)
                        else "rr_intervals_ms"
                    ),
                    window=win,
                    step=step,
                    min_rr_count=int(min_rr),
                    max_windows=int(max_windows),
                    include_advanced=not bool(fast_windowing),
                )
                if not wdf.empty:
                    windowed_all.append(wdf.assign(source=name))
                done_win += 1
                percent = min(100, int(done_win * 100 / total_win))
                txt_win.markdown(f"### Computing windowed metrics... {percent}%")
                prog_win.progress(percent)
        
        if windowed_all:
            windowed_df = pd.concat(windowed_all, ignore_index=True)
            if not windowed_df.empty:
                windowed_df["start"] = pd.to_datetime(
                    windowed_df["start"], errors="coerce", utc=True
                )
                if "end" in windowed_df.columns:
                    windowed_df["end"] = pd.to_datetime(
                        windowed_df["end"], errors="coerce", utc=True
                    )
                windowed_df = windowed_df.dropna(subset=["start"])
            if apply_dev:
                windowed_df = _compute_deviation_scores(
                    windowed_df,
                    metrics=dev_metrics,
                    z_warn=float(z_warn),
                    z_alert=float(z_alert),
                )
            # Mark windowed stage complete for caching
            if HRV_CACHE_AVAILABLE:
                cache_mgr = get_cache_manager()
                state = cache_mgr.get_computation_state()
                try:
                    files_hash = cache_mgr.compute_all_uploads_hash(datasets, profile_id=profile_id)
                except TypeError:
                    files_hash = cache_mgr.compute_all_uploads_hash(datasets)
                settings_hash = compute_settings_hash(
                    str(method), float(max_dev), int(median_win), win, step
                )
                state.mark_complete(files_hash, settings_hash, windowed=True)
                cache_mgr.update_computation_state(state)
        txt_win.markdown("### Computing windowed metrics... 100%")
        prog_win.progress(100)

        # ML clustering
        if enable_ml and not windowed_df.empty:
            ml_metrics = (
                list(dev_metrics)
                if dev_metrics
                else ["rmssd", "sdnn", "lf_hf_ratio", "hf_power"]
            )
            try:
                ml_result = run_windowed_kmeans(
                    windowed_df,
                    ml_metrics,
                    n_clusters=2,
                    max_iterations=50,
                )
            except ValueError as exc:
                logger.warning("ML clustering failed: %s", exc, exc_info=True)
                ml_error_message = str(exc)
            else:
                windowed_df = ml_result.windowed_with_clusters
                ml_summary_df = ml_result.cluster_summary

        if not windowed_df.empty:
            windowed_df["start"] = pd.to_datetime(
                windowed_df["start"], errors="coerce", utc=True
            )
            if "end" in windowed_df.columns:
                windowed_df["end"] = pd.to_datetime(
                    windowed_df["end"], errors="coerce", utc=True
                )
            windowed_df = windowed_df.dropna(subset=["start"])

        # Aggregate anomaly episodes (contiguous yellow/red windows)
        def _episodes(df: pd.DataFrame, min_len: int) -> pd.DataFrame:
            if df.empty or "dev_level" not in df.columns:
                return pd.DataFrame()
            out_eps: List[Dict[str, Any]] = []
            step_td = pd.to_timedelta(step)
            for src, sub in df.sort_values(["source", "start"]).groupby("source"):
                cur_level = None
                cur_start = None
                cur_end = None
                cur_count = 0
                cur_max = 0.0
                prev_start = None
                for _, r in sub.iterrows():
                    level = str(r.get("dev_level", "green"))
                    if level == "green":
                        level = None
                    start_ts = pd.to_datetime(r.get("start"))
                    end_ts = pd.to_datetime(r.get("end"))
                    if cur_level is None and level is not None:
                        cur_level = level
                        cur_start = start_ts
                        cur_end = end_ts
                        cur_count = 1
                        cur_max = float(r.get("dev_index", 0.0))
                    elif cur_level is not None:
                        # continue if same level and contiguous
                        if (
                            level == cur_level
                            and prev_start is not None
                            and (start_ts - prev_start) <= step_td * 1.5
                        ):
                            cur_end = end_ts
                            cur_count += 1
                            cur_max = max(cur_max, float(r.get("dev_index", 0.0)))
                    else:
                        if cur_count >= int(min_len):
                            out_eps.append(
                                {
                                    "source": src,
                                    "level": cur_level,
                                    "start": cur_start,
                                    "end": cur_end,
                                    "n_windows": cur_count,
                                    "max_dev_index": cur_max,
                                }
                            )
                        cur_level = level
                        cur_start = start_ts if level is not None else None
                        cur_end = end_ts if level is not None else None
                        cur_count = 1 if level is not None else 0
                        cur_max = (float(r.get("dev_index", 0.0))
                                   if level is not None else 0.0)
                    prev_start = start_ts
                if cur_level is not None and cur_count >= int(min_len):
                    out_eps.append(
                        {
                            "source": src,
                            "level": cur_level,
                            "start": cur_start,
                            "end": cur_end,
                            "n_windows": cur_count,
                            "max_dev_index": cur_max,
                        }
                    )
            return pd.DataFrame(out_eps)

        episodes_df = (
            _episodes(windowed_df, int(min_sustain))
            if (apply_dev and not windowed_df.empty and "dev_level" in windowed_df.columns)
            else pd.DataFrame()
        )

        # Full-recording metrics
        multi_results: List[Dict[str, Any]] = []
        ordered_sources: List[str] = []
        txt_full = st.empty()
        prog_full = st.progress(0)
        txt_full.markdown("### Computing full-recording metrics... 0%")

        total_full = max(1, len(datasets))
        done_full = 0
        #region agent log
        _agent_debug_log(
            "H6",
            "app.py:hrv_analysis",
            "full_metrics_start",
            {
                "dataset_count": len(datasets),
                "apply_clean": bool(apply_clean),
                "high_compute": bool(high_compute),
                "reuse_cached_results": bool(reuse_cached_results),
            },
        )
        #endregion
        for name, up in datasets.items():
            _dataset_start = time.perf_counter()
            if up.rr_ms.size >= 10:
                if reuse_cached_results and name in stored_payloads:
                    cached_multi = stored_payloads[name].get("multi_results")
                    if cached_multi:
                        m = dict(cached_multi)
                        m["source"] = name
                        start_ts: Optional[pd.Timestamp] = (
                            up.recording_start_utc
                            if isinstance(up.recording_start_utc, pd.Timestamp)
                            else None
                        )
                        if start_ts is None:
                            start_ts, _ = _infer_recording_start(name)
                        if isinstance(start_ts, pd.Timestamp):
                            m["timestamp"] = start_ts.isoformat()
                        multi_results.append(m)
                        ordered_sources.append(name)
                        done_full += 1
                        percent = min(100, int(done_full * 100 / total_full))
                        txt_full.markdown(
                            f"### Computing full-recording metrics... {percent}%"
                        )
                        prog_full.progress(percent)
                        continue
                use_rr = (
                    up.rr_ms_clean
                    if (apply_clean and up.rr_ms_clean is not None)
                    else up.rr_ms
                )
                _compute_start = time.perf_counter()
                m = _cached_comprehensive(
                    use_rr, include_advanced=bool(high_compute))
                _compute_ms = (time.perf_counter() - _compute_start) * 1000.0
                m["source"] = name
                start_ts = (
                    up.recording_start_utc
                    if isinstance(up.recording_start_utc, pd.Timestamp)
                    else None
                )
                if start_ts is None:
                    start_ts, _ = _infer_recording_start(name)
                if isinstance(start_ts, pd.Timestamp):
                    m["timestamp"] = start_ts.isoformat()
                if apply_clean and up.qc_summary:
                    m["qc_flagged_pct"] = float(
                        up.qc_summary.get("flagged_pct", 0.0))
                    m["qc_method"] = str(up.qc_summary.get("qc_method", {}))
                if enable_cov:
                    from hrv_core import covariate_adjust_short_term as _cov

                    adj = _cov(
                        age_years=int(age_years),
                        sex=str(sex),
                        bmi=float(bmi),
                        exercise_level=str(exercise),
                        rmssd=float(m.get("rmssd", np.nan)),
                        sdnn=float(m.get("sdnn", np.nan)),
                    )
                    m.update(adj)
                multi_results.append(m)
                ordered_sources.append(name)
                done_full += 1
                percent = min(100, int(done_full * 100 / total_full))
                txt_full.markdown(f"### Computing full-recording metrics... {percent}%")
                prog_full.progress(percent)
                #region agent log
                _agent_debug_log(
                    "H6",
                    "app.py:hrv_analysis",
                    "full_metrics_done",
                    {
                        "source": name,
                        "rr_count": int(use_rr.size),
                        "compute_ms": _compute_ms,
                        "elapsed_ms": (time.perf_counter() - _dataset_start) * 1000.0,
                        "cached": False,
                    },
                )
                #endregion
            else:
                #region agent log
                _agent_debug_log(
                    "H6",
                    "app.py:hrv_analysis",
                    "skip_dataset_too_short",
                    {
                        "source": name,
                        "rr_count": int(up.rr_ms.size),
                    },
                )
                #endregion
        txt_full.markdown("### Computing full-recording metrics... 100%")
        prog_full.progress(100)
        multi_results_df = pd.DataFrame(
            multi_results) if multi_results else pd.DataFrame()

        # Long-term summaries (5-min windows): SDANN (std of mean_nni), SDNNIDX
        # (mean of window SDNN)
        if (
            not windowed_df.empty
            and "mean_nni" in windowed_df.columns
            and "sdnn" in windowed_df.columns
        ):
            lts = (
                windowed_df.groupby("source")
                .agg(
                    sdann_5min=(
                        "mean_nni",
                        lambda x: float(
                            np.std(pd.to_numeric(x, errors="coerce").dropna(), ddof=1)
                        ),
                    ),
                    sdnnidx_5min=(
                        "sdnn",
                        lambda x: float(
                            np.mean(pd.to_numeric(x, errors="coerce").dropna())
                        ),
                    ),
                )
                .reset_index()
            )
            if not multi_results_df.empty:
                # Drop existing long-term columns to avoid merge duplication errors
                for col in ("sdann_5min", "sdnnidx_5min"):
                    if col in multi_results_df.columns:
                        multi_results_df = multi_results_df.drop(columns=[col])
                multi_results_df = multi_results_df.merge(
                    lts, on="source", how="left")

        pns_mapping: Dict[str, float] = {}
        if (
            not multi_results_df.empty
            and "parasympathetic_index" in multi_results_df.columns
        ):
            for src in ordered_sources:
                row = multi_results_df[multi_results_df["source"] == src]
                if row.empty:
                    continue
                val = float(row["parasympathetic_index"].iloc[0])
                if np.isfinite(val):
                    pns_mapping[src] = val

        # Enrich meta_rows with NOAA explanations so GPT/export can include them
        try:
            _noaa_rows = get_noaa_metric_explanations()
        except Exception:
            _noaa_rows = []
        meta_rows_for_context = meta_rows + _noaa_rows if _noaa_rows else meta_rows

        # Persist analysis outputs for reuse per active user
        try:
            _persist_analysis_results(
                logger,
                active_profile,
                datasets,
                file_hash_map,
                multi_results_df,
                windowed_df,
                analysis_settings,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Persistence skipped: %s", exc)
        
        # CRITICAL: Cache datasets for tab rendering after rerun
        # Without this, tabs get empty datasets and show infinite loading
        st.session_state["_hrv_cached_datasets"] = datasets
        st.session_state["_hrv_cached_windowed_df"] = windowed_df
        st.session_state["_hrv_cached_multi_results_df"] = multi_results_df
        st.session_state["_hrv_cached_meta_rows"] = meta_rows
        st.session_state["_hrv_cached_meta_rows_for_context"] = meta_rows_for_context
        st.session_state["_hrv_cached_ml_summary_df"] = ml_summary_df
        st.session_state["_hrv_cached_episodes_df"] = episodes_df
        
        # Mark comprehensive stage complete to avoid auto-reruns on the same upload set
        st.session_state["hrv_analysis_ready"] = False
        st.session_state["hrv_analysis_complete_signature"] = upload_signature
        # Refresh readiness/DB-backed panels immediately after new measurements are saved.
        try:
            _cached_pns_history.clear()  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - cache may be unavailable
            pass
        #region agent log
        _agent_debug_log(
            "H6",
            "app.py:hrv_analysis",
            "analysis_completed",
            {
                "upload_signature": upload_signature,
                "dataset_count": len(datasets),
                "multi_results_rows": int(multi_results_df.shape[0]),
                "windowed_rows": int(windowed_df.shape[0]),
            },
        )
        #endregion

        # Mark comprehensive stage complete for caching
        if HRV_CACHE_AVAILABLE:
            cache_mgr = get_cache_manager()
            state = cache_mgr.get_computation_state()
            try:
                files_hash = cache_mgr.compute_all_uploads_hash(datasets, profile_id=profile_id)
            except TypeError:
                files_hash = cache_mgr.compute_all_uploads_hash(datasets)
            settings_hash = compute_settings_hash(
                str(method), float(max_dev), int(median_win), win, step
            )
            state.mark_complete(files_hash, settings_hash, comprehensive=True, windowed=True, cleaning=True)
            cache_mgr.update_computation_state(state)
    else:
        # No data uploaded - set remaining defaults
        pns_mapping = {}
        ordered_sources = []

    metric_list: List[str] = _select_hrv_metric_columns(
        windowed_df,
        exclude=("kp_index",),
    )

    # Track data availability for conditional UI elements
    _rr_sources = uploads if uploads else datasets
    has_hrv_data = bool(_rr_sources) and any(
        u.rr_ms is not None and len(u.rr_ms) > 0 for u in _rr_sources.values()
    )
    total_rr_count = sum(
        len(u.rr_ms) for u in _rr_sources.values() if u.rr_ms is not None
    )
    
    # Update state manager if available
    if UI_STATE_MANAGER_AVAILABLE and has_hrv_data:
        state_mgr = get_state_manager()
        state_mgr.set_data_available(
            DataType.RR_INTERVALS,
            is_available=True,
            record_count=total_rr_count,
            source="Uploaded Files",
        )
    
    # Active user context for cross-tab personalization
    try:
        active_user_context = get_active_user_context()
    except Exception:
        active_user_context = _guest_user_context()

    # Tabs
    (
        tab_overview,
        tab_user_profile,
        tab_ts,
        tab_freq,
        tab_nl,
        tab_tfr,
        tab_window,
        tab_metrics,
        tab_hrf_hrv,
        tab_ans,
        tab_readiness,
        tab_gauges,
        tab_unified,
        tab_pop_norms,
        tab_biofeedback,
        tab_fatigue,
        tab_circadian,
        tab_space_data,
        tab_space_analytics,
        tab_export,
        tab_science,
        tab_refs,
        tab_about,
    ) = st.tabs(
        [
            "Overview",
            "👤 User Profile",
            "Time Series",
            "Frequency",
            "Nonlinear",
            "Spectrogram",
            "Windowed",
            "Metrics",
            "🧩 HRF ↔ HRV",
            "ANS Function Tests",
            "Readiness",
            "Gauges",
            "📈 Unified Timeline",
            "📊 Population Norms",
            "🫀 Biofeedback",
            "😴 SAFTE/Fatigue",
            "☀️ Circadian",
            "🌐 Space Data",
            "🔬 Space Analytics",
            "📄 Export",
            "Science",
            "📚 References",
            "ℹ️ About",
        ]
    )
    _sw_loading_msg: Optional[st.delta_generator.DeltaGenerator] = None
    # Debug breadcrumbs: when the UI appears "blank", it's often because a rerun
    # was triggered mid-render or execution stopped before later tabs were
    # populated. Gate logs behind the explicit Developer Tools toggle to avoid
    # log spam during normal use.
    if st.session_state.get("_debug_mode_checkbox", False) or st.session_state.get("_debug_mode_enabled", False):
        try:
            _LOGGER.info(
                "UI: main_result_tabs_created | has_hrv_data=%s | uploads=%d | profile=%s",
                has_hrv_data,
                len(uploads),
                active_display_name,
            )
        except Exception:
            pass
    with tab_overview:
        if st.session_state.get("_debug_mode_checkbox", False) or st.session_state.get("_debug_mode_enabled", False):
            try:
                _LOGGER.info("UI: render_tab_overview:start")
            except Exception:
                pass
        st.markdown("### 📊 Analysis Overview")
        st.markdown("*Summary of uploaded datasets and computed metrics*")
        
        # Data status panel
        if WELCOME_HEADER_AVAILABLE:
            from welcome_header import render_data_status_panel, render_getting_started_guide, render_quick_access_grid
            render_data_status_panel(
                has_rr_data=has_hrv_data,
                rr_count=total_rr_count,
                has_profile="current_user_profile" in st.session_state and st.session_state.get("current_user_profile"),
                has_space_weather="space_weather_data" in st.session_state and st.session_state.get("space_weather_data"),
            )
        
        # Quick start guide for new users
        if not has_hrv_data:
            if WELCOME_HEADER_AVAILABLE:
                render_getting_started_guide()
                st.divider()
                render_quick_access_grid(has_data=False)
            else:
                st.info(
                    "👋 **Welcome!** Upload RR interval data using the sidebar to begin HRV analysis.\n\n"
                    "**Available without data:**\n"
                    "- ☀️ Circadian Physiology - Simulate circadian rhythms\n"
                    "- 🌍 Space Weather - View current solar activity\n"
                    "- 😴 SAFTE Model - Model fatigue scenarios"
                )
        
        if meta_rows:
            st.dataframe(pd.DataFrame(meta_rows))
        # Deviation summary per dataset
        if apply_dev and not windowed_df.empty and "dev_level" in windowed_df.columns:
            summary = (
                windowed_df.groupby("source")["dev_level"]
                .value_counts()
                .unstack(fill_value=0)
                .reindex(columns=["green", "yellow", "red"], fill_value=0)
                .reset_index()
            )
            # Add max deviation index per source for quick scan
            max_dev = (windowed_df.groupby("source")[
                "dev_index"].max().rename("max_dev_index"))
            summary = summary.merge(max_dev, on="source", how="left")
            st.dataframe(
                summary.rename(
                    columns={
                        "green": "windows_green",
                        "yellow": "windows_yellow",
                        "red": "windows_red",
                    }
                )
            )
        # Show derived respiratory rate when available
        if (
            not multi_results_df.empty
            and "respiratory_rate_bpm" in multi_results_df.columns
        ):
            st.dataframe(multi_results_df[["source", "respiratory_rate_bpm"]].rename(
                columns={"respiratory_rate_bpm": "respiratory_rate [breaths/min]"}))
        if st.session_state.get("_debug_mode_checkbox", False) or st.session_state.get("_debug_mode_enabled", False):
            try:
                _LOGGER.info("UI: render_tab_overview:end")
            except Exception:
                pass
    
    # =========================================================================
    # USER PROFILE TAB - Centralized user data and clinical assessments
    # =========================================================================
    with tab_user_profile:
        if st.session_state.get("_debug_mode_checkbox", False) or st.session_state.get("_debug_mode_enabled", False):
            try:
                _LOGGER.info("UI: render_tab_user_profile:start")
            except Exception:
                pass
        if USER_PROFILE_TAB_AVAILABLE:
            try:
                render_user_profile_tab()
            except Exception as exc:  # pragma: no cover - UI safety net
                log_exception(_LOGGER, "User Profile tab crashed (skipping)", exc)
                st.error(
                    "User Profile encountered an error and was skipped so the rest of the app can continue. "
                    "Check `logs/errors.log` for details."
                )
                with st.expander("Error details", expanded=False):
                    st.code(str(exc))
        else:
            st.markdown("### 👤 User Profile")
            st.warning(
                "User Profile module not available.\n\n"
                "This tab provides:\n"
                "- **Personal data management** (age, weight, height, BMI)\n"
                "- **Clinical scales** (ESS, Samn-Perelli, KSS, PSQI)\n"
                "- **Assessment history** with timestamps\n"
                "- **HRV measurement tracking**\n\n"
                "Please ensure `user_profile_tab.py` is in the app directory."
            )
        if st.session_state.get("_debug_mode_checkbox", False) or st.session_state.get("_debug_mode_enabled", False):
            try:
                _LOGGER.info("UI: render_tab_user_profile:end")
            except Exception:
                pass
    
    with tab_ts:
        if st.session_state.get("_debug_mode_checkbox", False) or st.session_state.get("_debug_mode_enabled", False):
            try:
                _LOGGER.info("UI: render_tab_time_series:start")
            except Exception:
                pass
        if not has_hrv_data:
            st.info(
                "📈 **Time Series Analysis**\n\n"
                "This tab displays your RR interval and heart rate time series plots.\n\n"
                "**What you'll see:**\n"
                "- Beat-to-beat RR intervals (milliseconds)\n"
                "- Heart rate derived from RR intervals (bpm)\n"
                "- Deviation zones highlighting anomalies\n\n"
                "👈 **Upload HRV data using the sidebar to begin.**"
            )
            with st.expander("📊 Example: What RR Interval Data Looks Like"):
                st.markdown("""
                A healthy resting recording typically shows:
                - **RR intervals**: 800-1200 ms (corresponding to 50-75 bpm)
                - **Natural variability**: Irregular pattern reflecting autonomic modulation
                - **Respiratory influence**: ~0.15-0.4 Hz oscillation from breathing
                
                ```
                Example RR values (ms): 823, 845, 812, 867, 834, 821, 856, 891, 878, 803
                Mean HR: ~70 bpm | RMSSD: ~45 ms | SDNN: ~55 ms
                ```
                """)
        else:
            ts_datasets = _select_rr_files_for_tab(
                datasets, tab_key="tab_ts", label="Time Series Analysis"
            )
            if not ts_datasets:
                st.warning("Select at least one RR file to load into the Time Series tab.")
            else:
                st.markdown("### 📈 Time Series Analysis")
                _render_dataset_info_header(ts_datasets, title="Recordings Displayed")
                with st.expander(
                    "How to read these plots (axes + what you’re seeing)", expanded=False
                ):
                    st.markdown(
                        "- **X-axis (time)**: Timestamp in UTC derived from the recording start + cumulative RR.\n"
                        "- **RR plot (ms)**: Beat-to-beat interval duration. **Higher RR = slower HR**, **lower RR = faster HR**.\n"
                        "- **HR plot (bpm)**: Derived from RR via **HR ≈ 60,000 / RR(ms)**. Spikes in HR typically correspond to drops in RR.\n"
                        "- **Overlays**: If artifact correction is enabled, you may see **raw vs cleaned** traces; **red points** mark flagged artifacts.\n"
                        "- **Shaded regions**: Deviation zones (yellow/red) appear when deviation detection is enabled and indicate windows flagged as unusual.\n"
                        "- **Navigation**: Drag to pan; use the slider/scroll to zoom; double‑click the chart to reset zoom.\n"
                        "- **Performance note**: Very long recordings may be downsampled for plotting; computations use the full-resolution RR series."
                    )
                max_pts = None if rr_plot_cap == "No limit" else int(rr_plot_cap)
                _plot_rr_timeseries(
                    ts_datasets,
                    dev_windows=(
                        windowed_df
                        if (apply_dev and "dev_level" in windowed_df.columns)
                        else None
                    ),
                    max_points=max_pts,
                )
                _plot_hr_timeseries(ts_datasets)
        st.markdown(
            "**Scientific notes (time series)**  \n"
            "- RR intervals (ms) are beat-to-beat times; healthy resting dynamics are irregular and complex.  \n"
            "- Heart rate (bpm) is the inverse of RR; variability in RR reflects autonomic modulation.  \n"
            "Short-term norms and physiological context summarized by "
            "[Task Force 1996](https://www.escardio.org/static-file/Escardio/Guidelines/Scientific-Statements/guidelines-Heart-Rate-Variability-FT-1996.pdf) "
            "and updated in [Shaffer & Ginsberg, 2017](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full).")
        if st.session_state.get("_debug_mode_checkbox", False) or st.session_state.get("_debug_mode_enabled", False):
            try:
                _LOGGER.info("UI: render_tab_time_series:end")
            except Exception:
                pass
    with tab_freq:
        if not has_hrv_data:
            st.info(
                "🌊 **Frequency Domain Analysis**\n\n"
                "This tab shows power spectral density (PSD) analysis of your HRV data.\n\n"
                "**Frequency Bands:**\n"
                "- **VLF** (0.0033–0.04 Hz): Thermoregulation, hormonal rhythms\n"
                "- **LF** (0.04–0.15 Hz): Baroreflex, sympathetic + parasympathetic\n"
                "- **HF** (0.15–0.40 Hz): Respiratory sinus arrhythmia (vagal)\n\n"
                "👈 **Upload HRV data to see your frequency analysis.**"
            )
            with st.expander("📊 Example: Typical Resting Frequency Analysis"):
                st.markdown("""
                **Healthy Adult at Rest:**
                | Band | Power (ms²) | Interpretation |
                |------|-------------|----------------|
                | VLF | 500-1500 | Thermoregulation |
                | LF | 300-1000 | Baroreflex activity |
                | HF | 200-800 | Vagal (parasympathetic) |
                | LF/HF | 0.5-2.0 | Autonomic balance (interpret with caution) |
                
                *Note: LF/HF ratio has limited validity as a sympathetic/parasympathetic "balance" index.*
                """)
        elif skip_freq:
            st.info("Frequency overlay disabled (Performance & display).")
        else:
            freq_datasets = _select_rr_files_for_tab(
                datasets, tab_key="tab_freq", label="Frequency Domain"
            )
            if not freq_datasets:
                st.warning("Select at least one RR file to load into the Frequency tab.")
            else:
                st.markdown("### 🌊 Frequency Domain Analysis")
                _render_dataset_info_header(freq_datasets, title="Recordings Analyzed")
                with st.expander(
                    "How to read the PSD plot (axes + bands)", expanded=False
                ):
                    st.markdown(
                        "- **X-axis (Frequency, Hz)**: How fast the oscillation is.\n"
                        "- **Y-axis (PSD, ms²/Hz)**: Power at each frequency on a **log scale** (equal vertical spacing means multiplicative changes).\n"
                        "- **Shaded bands**: **VLF** 0.0033–0.04 Hz, **LF** 0.04–0.15 Hz, **HF** 0.15–0.40 Hz.\n"
                        "- **What to look for**: A **peak in HF** often tracks breathing-related modulation; **LF** reflects slower baroreflex/autonomic rhythms.\n"
                        "- **Tip**: Compare the **shape and peak locations** across recordings more than absolute power when posture/conditions differ.\n"
                        "- **Navigation**: Drag to pan; use the slider/scroll to zoom; double‑click to reset."
                    )
                _plot_psd_overlay(freq_datasets, method=psd_method)
        st.markdown(
            "**Scientific notes (frequency domain)**  \n"
            "- Bands: VLF 0.0033–0.04 Hz, LF 0.04–0.15 Hz, HF 0.15–0.40 Hz.  \n"
            "- HF indexes respiratory sinus arrhythmia (parasympathetic activity); LF reflects baroreflex and mixed influences; LF/HF has limited validity as a 'balance' index and should be interpreted with breathing context.  \n"
            "References: [Task Force 1996](https://www.escardio.org/static-file/Escardio/Guidelines/Scientific-Statements/guidelines-Heart-Rate-Variability-FT-1996.pdf); "
            "[Nunan et al., 2010](https://pubmed.ncbi.nlm.nih.gov/20663071/); "
            "[Shaffer & Ginsberg, 2017](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full).")
    with tab_nl:
        if not has_hrv_data:
            st.info(
                "🔀 **Nonlinear Analysis**\n\n"
                "This tab shows Poincaré plots, entropy measures, and fractal analysis.\n\n"
                "**Key Metrics:**\n"
                "- **Poincaré SD1/SD2**: Short-term vs long-term variability\n"
                "- **DFA α1**: Fractal scaling exponent (0.75-1.25 at healthy rest)\n"
                "- **Sample Entropy**: Signal complexity/regularity\n\n"
                "👈 **Upload HRV data to see nonlinear dynamics.**"
            )
            with st.expander("📊 Example: Poincaré Plot Interpretation"):
                st.markdown("""
                **The Poincaré plot** graphs each RR interval against the next (RR[n] vs RR[n+1]).
                
                **Healthy Pattern:**
                - Ellipse shape with SD1 (short-term) < SD2 (long-term)
                - SD1 ≈ 30-60 ms (vagal modulation)
                - SD2 ≈ 60-120 ms (overall variability)
                
                **Abnormal Patterns:**
                - *Torpedo shape*: Reduced short-term variability → parasympathetic dysfunction
                - *Wide scatter*: Arrhythmias or artifacts
                - *Tight cluster*: Very low HRV → reduced autonomic flexibility
                """)
        elif skip_poincare:
            st.info("Poincaré plot disabled (Performance & display).")
        else:
            nl_datasets = _select_rr_files_for_tab(
                datasets, tab_key="tab_nl", label="Nonlinear Dynamics"
            )
            if not nl_datasets:
                st.warning("Select at least one RR file to load into the Nonlinear tab.")
            else:
                st.markdown("### 🔀 Nonlinear Dynamics")
                _render_dataset_info_header(nl_datasets, title="Recordings Analyzed")
                with st.expander(
                    "How to read the Poincaré plot (RRₙ vs RRₙ₊₁)", expanded=False
                ):
                    st.markdown(
                        "- **Each point**: A pair of consecutive intervals **(RRₙ, RRₙ₊₁)** in **milliseconds**.\n"
                        "- **Axes**: X is RRₙ (ms); Y is RRₙ₊₁ (ms). Points near the diagonal mean consecutive beats are similar.\n"
                        "- **Width (SD1)**: Spread *perpendicular* to the diagonal ≈ short‑term beat‑to‑beat variability (often vagal).\n"
                        "- **Length (SD2)**: Spread *along* the diagonal reflects longer‑term variability.\n"
                        "- **Outliers/stripes**: Often artifacts or ectopic beats—review cleaning settings if the cloud looks “broken.”\n"
                        "- **Performance note**: The plot may downsample points for rendering; summary metrics use the full series."
                    )
                _plot_poincare(nl_datasets)
        st.markdown(
            "**Scientific notes (nonlinear)**  \n"
            "- Poincaré SD1 ≈ RMSSD (short-term vagal modulation); SD2 relates to longer-term variability.  \n"
            "- DFA α1 ≈ 0.75–1.25 at rest reflects healthy fractal-like regulation; lower values can indicate exercise intensity near the aerobic threshold in exertional contexts.  \n"
            "References: [Shaffer & Ginsberg, 2017](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full).")
    with tab_tfr:
        if not has_hrv_data:
            st.info(
                "📉 **Time-Frequency Analysis (Spectrogram)**\n\n"
                "This tab visualizes how spectral power changes over time.\n\n"
                "**What you'll see:**\n"
                "- X-axis: Time (seconds or minutes)\n"
                "- Y-axis: Frequency (Hz)\n"
                "- Color intensity: Power (ms²/Hz)\n\n"
                "👈 **Upload HRV data to see time-frequency dynamics.**"
            )
        elif skip_spectrogram:
            st.info("Spectrogram disabled (Performance & display).")
        else:
            st.markdown("### 📉 Spectrogram (Time-Frequency)")
            _render_dataset_info_header(datasets, title="Recordings Analyzed")
            with st.expander(
                "How to read the spectrogram (time–frequency heatmap)", expanded=False
            ):
                st.markdown(
                    "- **X-axis (Time, s)**: Seconds since the recording start.\n"
                    "- **Y-axis (Frequency, Hz)**: Oscillation frequency (how fast rhythms occur).\n"
                    "- **Color**: Relative power (auto‑scaled to the 5th–95th percentile for readability).\n"
                    "- **HF band (0.15–0.40 Hz)**: Often breathing-related; a bright ridge that moves suggests changing breathing rate.\n"
                    "- **LF band (0.04–0.15 Hz)**: Slower autonomic/baroreflex rhythms; patches may reflect transient changes (posture, workload, arousal).\n"
                    "- **Note**: This view is limited to ≤0.5 Hz to focus on HRV-relevant bands."
                )
            _plot_spectrogram(datasets)
        st.markdown(
            "**Scientific notes (time–frequency)**  \n"
            "- Spectrogram visualizes how spectral power evolves; HF tracks respiration; LF reflects slower autonomic rhythms.  \n"
            "- Stationarity assumptions matter; windowed PSD improves interpretability for long, varying recordings.")
    with tab_window:
        if not has_hrv_data:
            st.info(
                "🪟 **Windowed Analysis**\n\n"
                "This tab shows HRV metrics computed over sliding time windows.\n\n"
                "**Purpose:**\n"
                "- Track HRV trends over time\n"
                "- Identify deviation episodes\n"
                "- Detect anomalous periods for further investigation\n\n"
                "👈 **Upload HRV data to see windowed metrics.**"
            )
        st.markdown(
            "**Scientific notes (windowed metrics)**  \n"
            "- Sliding windows (e.g., 5 min, step 1 min) estimate locally stationary segments to track trends over time.  \n"
            "- Minimum RR count safeguards metric stability; interpretation should consider protocol and respiration.")
        if has_hrv_data and not windowed_df.empty:
            # Use performance settings for row limit
            max_display_rows = 50
            if PERFORMANCE_UTILS_AVAILABLE:
                perf = get_performance_settings()
                max_display_rows = min(perf.get("max_dataframe_rows", 500), len(windowed_df))
            
            display_df = windowed_df[
                ["start", "source"]
                + [c for c in windowed_df.columns if c not in ("start", "source")]
            ].head(max_display_rows)
            
            st.dataframe(display_df)
            if len(windowed_df) > max_display_rows:
                st.caption(f"Showing {max_display_rows} of {len(windowed_df)} windows. Adjust in ⚡ Performance Settings.")
            if apply_dev and "dev_level" in windowed_df.columns:
                st.markdown(
                    "Deviation timeline across selected metrics (green < warn, yellow ≥ warn, red ≥ alert):"
                )
                _plot_deviation_timeline(windowed_df)
                if not episodes_df.empty:
                    st.markdown(
                        "Anomaly episodes (contiguous yellow/red windows):")
                    st.dataframe(episodes_df.sort_values(["source", "start"]))
            if enable_ml:
                if ml_summary_df.empty:
                    if ml_error_message:
                        st.warning(
                            f"ML clustering unavailable: {ml_error_message}")
                else:
                    st.markdown(
                        "ML-assisted deviation clusters (unsupervised k-means):"
                    )
                    st.dataframe(ml_summary_df)
        else:
            st.info("No windowed metrics to display.")
    with tab_metrics:
        st.markdown("### 📋 Comprehensive Metrics Table")
        st.markdown("*All computed HRV metrics across time, frequency, nonlinear, and advanced domains*")
        
        if not has_hrv_data:
            st.info(
                "📋 **Metrics Dashboard**\n\n"
                "This tab displays a comprehensive table of all computed HRV metrics.\n\n"
                "**Metric Categories:**\n"
                "- **Time Domain**: SDNN, RMSSD, pNN50, Mean HR\n"
                "- **Frequency Domain**: VLF, LF, HF, LF/HF ratio\n"
                "- **Nonlinear**: SD1, SD2, DFA α1, Sample Entropy\n"
                "- **Advanced**: Deceleration capacity, symbolic dynamics, recurrence\n\n"
                "👈 **Upload HRV data to compute metrics.**"
            )
            with st.expander("📊 Example: HRV Reference Values (Healthy Adult at Rest)"):
                st.markdown("""
                | Metric | Typical Range | Unit | Interpretation |
                |--------|---------------|------|----------------|
                | SDNN | 50-100 | ms | Overall variability |
                | RMSSD | 25-60 | ms | Vagal tone |
                | pNN50 | 5-25 | % | Parasympathetic marker |
                | LF power | 300-1000 | ms² | Baroreflex activity |
                | HF power | 200-800 | ms² | Respiratory sinus arrhythmia |
                | DFA α1 | 0.75-1.25 | - | Fractal complexity |
                
                *Values from Shaffer & Ginsberg (2017), Task Force (1996)*
                """)
        elif not multi_results_df.empty:
            st.dataframe(multi_results_df)
            novel_columns = [
                "hrf_pip_pct",
                "hrf_pip_h_pct",
                "hrf_pip_s_pct",
                "hrf_ials",
                "hrf_pss_pct",
                "hrf_pas_pct",
                "hrf_w0_pct",
                "hrf_w1_pct",
                "hrf_w2_pct",
                "hrf_w3_pct",
                "hrf_quality_ok",
                "deceleration_capacity",
                "acceleration_capacity",
                "permutation_entropy",
                "permutation_entropy_norm",
                "symbolic_0v_pct",
                "symbolic_2uv_pct",
                "mfdfa_width",
                "rqa_rr",
                "rqa_det",
                "entropy_lf",
                "entropy_hf",
                "entropy_lf_hf_ratio",
                "rmssd_master_ratio",
            ]
            available_novel = [
                col for col in novel_columns if col in multi_results_df.columns
            ]
            if available_novel:
                st.markdown("Novel metrics (advanced signal analytics):")
                st.dataframe(multi_results_df[["source"] + available_novel])
            if enable_cov and "rmssd_z_cov" in multi_results_df.columns:
                st.markdown(
                    "Covariate-adjusted (patient profile) expectations and z-scores:"
                )
                cols_to_show = ["source"]
                for c in [
                    "rmssd",
                    "rmssd_expected",
                    "rmssd_z_cov",
                    "sdnn",
                    "sdnn_expected",
                    "sdnn_z_cov",
                ]:
                    if c in multi_results_df.columns:
                        cols_to_show.append(c)
                st.dataframe(multi_results_df[cols_to_show])
            st.divider()
            st.markdown("### 🔍 AI metric explanations")
            st.info(
                "OpenAI/Agents-based explanations are generated **on-demand** from the "
                "**Export & Download** tab to keep analysis tabs responsive. "
                "Go to **Export & Download → AI analysis** when you want the AI appendix."
            )
        else:
            st.info("No metrics to display.")
    with tab_hrf_hrv:
        st.markdown("### 🧩 HRF ↔ HRV (Fragmentation + Correlations)")
        st.markdown(
            "*Offline analysis of **Heart Rate Fragmentation (HRF)** metrics and their relationships to HRV metrics.*"
        )
        st.caption(
            "This tab is intentionally **decoupled** from NOAA/SWPC/DONKI fetch pipelines. "
            "It uses only your uploaded HRV recordings and computed metrics."
        )

        if not has_hrv_data:
            if has_hrv_data_uploaded:
                st.info(
                    "HRV data is uploaded. Click **Run HRV Analysis** (top of page) to compute metrics, then return here."
                )
            else:
                st.info("Upload HRV RR data to compute HRF/HRV metrics and correlations.")
        else:
            # Prefer in-memory analysis outputs; fall back to session-cached frames.
            base_results = (
                multi_results_df
                if isinstance(multi_results_df, pd.DataFrame) and not multi_results_df.empty
                else st.session_state.get("_hrv_cached_multi_results_df", pd.DataFrame())
            )
            if not isinstance(base_results, pd.DataFrame) or base_results.empty:
                st.info("Run HRV analysis to generate per-recording metrics for HRF/HRV correlations.")
            elif "source" not in base_results.columns:
                st.warning(
                    "Metrics table is missing the `source` column; cannot build per-recording HRF summaries."
                )
            else:
                use_clean_for_hrf = st.checkbox(
                    "Use cleaned RR series (if available) for HRF computations",
                    value=bool(apply_clean),
                    key="hrf_tab_use_clean_rr",
                    help="If enabled, HRF metrics are computed from the cleaned RR series when present.",
                )

                # If cached results were computed before HRF metrics were added (or if fast mode skipped them),
                # compute HRF metrics quickly (O(n)) from the RR series and merge them into the per-recording frame.
                need_hrf_cols = (
                    "hrf_pip_pct",
                    "hrf_ials",
                    "hrf_pss_pct",
                    "hrf_pip_h_pct",
                    "hrf_pip_s_pct",
                    "hrf_pas_pct",
                    "hrf_w0_pct",
                    "hrf_w1_pct",
                    "hrf_w2_pct",
                    "hrf_w3_pct",
                    "hrf_quality_ok",
                    "hrf_pip",
                    "hrf_w3",
                )
                missing_any_hrf = any(col not in base_results.columns for col in need_hrf_cols)
                merged_results = base_results.copy()

                if missing_any_hrf:
                    cache_key = "hrf_hrv_tab_hrf_cache"
                    cache_payload = st.session_state.get(cache_key, {})
                    sig = {
                        "upload_signature": list(upload_signature),
                        "use_clean": bool(use_clean_for_hrf),
                    }
                    cached_df = cache_payload.get("df")
                    if cache_payload.get("sig") == sig and isinstance(cached_df, pd.DataFrame):
                        hrf_df = cached_df
                    else:
                        from hrv_core import compute_heart_rate_fragmentation  # noqa: PLC0415

                        try:
                            from hrv_fragmentation import compute_hrf_metrics  # noqa: PLC0415
                        except Exception:
                            compute_hrf_metrics = None  # type: ignore[assignment]

                        rr_sources = datasets if datasets else uploads
                        rows: List[Dict[str, Any]] = []
                        for src_name, up in rr_sources.items():
                            rr_arr = getattr(up, "rr_ms", None)
                            if use_clean_for_hrf:
                                rr_clean = getattr(up, "rr_ms_clean", None)
                                if isinstance(rr_clean, np.ndarray) and rr_clean.size >= 10:
                                    rr_arr = rr_clean
                            if not isinstance(rr_arr, np.ndarray) or rr_arr.size < 10:
                                continue
                            row: Dict[str, Any] = {"source": str(src_name)}
                            row.update(compute_heart_rate_fragmentation(rr_arr))
                            if compute_hrf_metrics is not None:
                                hrf = compute_hrf_metrics(rr_arr)
                                row["hrf_pip_h_pct"] = float(hrf.pip_h)
                                row["hrf_pip_s_pct"] = float(hrf.pip_s)
                                row["hrf_pas_pct"] = float(hrf.pas)
                                row["hrf_w0_pct"] = float(hrf.w0)
                                row["hrf_w1_pct"] = float(hrf.w1)
                                row["hrf_w2_pct"] = float(hrf.w2)
                                row["hrf_w3_pct"] = float(hrf.w3)
                                row["hrf_w3"] = float(hrf.w3)
                                row["hrf_quality_ok"] = bool(hrf.quality_ok)
                            if "hrf_pip_pct" in row:
                                row["hrf_pip"] = float(row["hrf_pip_pct"])
                            rows.append(row)
                        hrf_df = pd.DataFrame(rows)
                        st.session_state[cache_key] = {"sig": sig, "df": hrf_df}

                    if isinstance(hrf_df, pd.DataFrame) and not hrf_df.empty:
                        merged_results = merged_results.merge(
                            hrf_df, on="source", how="left", suffixes=("", "_calc")
                        )
                        for col in hrf_df.columns:
                            if col == "source":
                                continue
                            calc_col = f"{col}_calc"
                            if calc_col in merged_results.columns:
                                if col in merged_results.columns:
                                    merged_results[col] = pd.to_numeric(
                                        merged_results[col], errors="coerce"
                                    )
                                    merged_results[calc_col] = pd.to_numeric(
                                        merged_results[calc_col], errors="coerce"
                                    )
                                    merged_results[col] = merged_results[col].fillna(
                                        merged_results[calc_col]
                                    )
                                    merged_results = merged_results.drop(columns=[calc_col])
                                else:
                                    merged_results = merged_results.rename(
                                        columns={calc_col: col}
                                    )
                        # Persist into session cache so other tabs can reuse after rerun.
                        st.session_state["_hrv_cached_multi_results_df"] = merged_results

                st.markdown("#### HRF summary (selected recording)")
                sources = merged_results["source"].astype(str).tolist()
                if not sources:
                    st.info("No per-recording summaries available.")
                else:
                    selected_source = st.selectbox(
                        "Recording",
                        options=sources,
                        index=0,
                        key="hrf_tab_selected_recording",
                        help="Select a recording to view HRF gauges and details.",
                    )
                    sel_row = merged_results[merged_results["source"] == selected_source].iloc[0]

                    pip_val = float(sel_row.get("hrf_pip", sel_row.get("hrf_pip_pct", np.nan)))
                    ials_val = float(sel_row.get("hrf_ials", np.nan))
                    w3_val = float(sel_row.get("hrf_w3", sel_row.get("hrf_w3_pct", np.nan)))

                    g1, g2, g3 = st.columns(3)
                    with g1:
                        _echarts_gauge(
                            pip_val,
                            min_val=0.0,
                            max_val=100.0,
                            title="PIP (fragmentation)",
                            unit="%",
                            precision=1,
                            thresholds=[(50.0, "#22c55e"), (65.0, "#facc15"), (100.0, "#ef4444")],
                            height_px=300,
                        )
                    with g2:
                        _echarts_gauge(
                            ials_val,
                            min_val=0.0,
                            max_val=1.0,
                            title="IALS",
                            unit="",
                            precision=3,
                            thresholds=[(0.4, "#22c55e"), (0.6, "#facc15"), (1.0, "#ef4444")],
                            height_px=300,
                        )
                    with g3:
                        _echarts_gauge(
                            w3_val,
                            min_val=0.0,
                            max_val=100.0,
                            title="W3 (fragmentation word)",
                            unit="%",
                            precision=1,
                            thresholds=[(20.0, "#22c55e"), (30.0, "#facc15"), (100.0, "#ef4444")],
                            height_px=300,
                        )

                    with st.expander("What these HRF metrics mean (quick guide)", expanded=False):
                        st.markdown(
                            "**Heart Rate Fragmentation (HRF)** captures *beat-to-beat “jerkiness”* — frequent switches between "
                            "RR-interval acceleration and deceleration — even when the ECG appears sinus rhythm.  \n\n"
                            "- **PIP**: % of inflection points (direction changes) in successive RR differences (↑ = more fragmented dynamics).  \n"
                            "- **IALS**: inverse average length of monotonic RR segments (↑ = shorter runs = more fragmentation).  \n"
                            "- **W3**: frequency of 4-beat “words” with 3 inflections (a maximally fragmented pattern; ↑ = more fragmentation).  \n\n"
                            "**Interpretation note:** HRF can inflate short‑term/high‑frequency variability, so a “high HRV” reading may not "
                            "always reflect higher vagal modulation when fragmentation is elevated."
                        )
                        st.caption(
                            "Key references: Costa et al. (2017) https://doi.org/10.3389/fphys.2017.00255; "
                            "Hayano et al. (2020) https://doi.org/10.3390/app10093314."
                        )

                    # ------------------------------------------------------------
                    # HRF ↔ HRV correlations (per-recording)
                    # ------------------------------------------------------------
                    st.markdown("---")
                    st.markdown("#### 🔗 HRF ↔ HRV correlations (per-recording)")
                    numeric_cols = [
                        c
                        for c in merged_results.columns
                        if c not in {"source"}
                        and pd.api.types.is_numeric_dtype(merged_results[c])
                    ]
                    hrf_candidates = [
                        c
                        for c in [
                            "hrf_pip",
                            "hrf_ials",
                            "hrf_w3",
                            "hrf_pss_pct",
                            "hrf_pip_h_pct",
                            "hrf_pip_s_pct",
                            "hrf_pas_pct",
                            "hrf_w0_pct",
                            "hrf_w1_pct",
                            "hrf_w2_pct",
                        ]
                        if c in numeric_cols
                    ]
                    hrv_candidates = [
                        c
                        for c in [
                            "rmssd",
                            "sdnn",
                            "mean_hr",
                            "lf_hf_ratio",
                            "hf_power",
                            "lf_power",
                            "total_power",
                            "pnn50",
                            "sd1",
                            "sd2",
                            "dfa_alpha1",
                            "sampen",
                            "stress_index",
                            "parasympathetic_index",
                            "sympathetic_index",
                            "ans_balance",
                        ]
                        if c in numeric_cols
                    ]
                    if len(hrf_candidates) < 1 or len(hrv_candidates) < 1:
                        st.info(
                            "Not enough HRF/HRV numeric metrics are available yet. "
                            "If you just upgraded, click **Recompute HRV Analysis** once to populate the full metric set."
                        )
                    else:
                        col_sel_a, col_sel_b = st.columns(2)
                        with col_sel_a:
                            selected_hrf = st.multiselect(
                                "HRF metrics",
                                options=hrf_candidates,
                                default=hrf_candidates[: min(3, len(hrf_candidates))],
                                key="hrf_corr_hrf_metrics",
                            )
                        with col_sel_b:
                            selected_hrv = st.multiselect(
                                "HRV metrics",
                                options=hrv_candidates,
                                default=hrv_candidates[: min(4, len(hrv_candidates))],
                                key="hrf_corr_hrv_metrics",
                            )
                        selected_metrics = [*selected_hrf, *selected_hrv]
                        if len(selected_metrics) < 2:
                            st.info("Select at least 2 metrics to compute correlations.")
                        else:
                            st.info(
                                "Correlations run only when you click **Compute HRF↔HRV correlations**. "
                                "Results are cached in-session so they persist across tab switches."
                            )
                            cache_key = "hrf_hrv_corr_cache"
                            if st.button(
                                "Compute HRF↔HRV correlations",
                                key="hrf_corr_compute_btn",
                                help="Compute a Pearson correlation matrix across recordings (per-recording metrics).",
                            ):
                                corr_input = merged_results[selected_metrics].apply(
                                    pd.to_numeric, errors="coerce"
                                )
                                corr_df = corr_input.corr()
                                # Pairwise HRF↔HRV statistics (Pearson r, two-sided p).
                                # Keep bounded by user-selected metrics (finite lists).
                                pair_stats_rows: List[Dict[str, Any]] = []
                                for hrf_m in selected_hrf:
                                    for hrv_m in selected_hrv:
                                        if hrf_m not in corr_input.columns or hrv_m not in corr_input.columns:
                                            continue
                                        x_vals = pd.to_numeric(corr_input[hrf_m], errors="coerce").to_numpy(dtype=float)
                                        y_vals = pd.to_numeric(corr_input[hrv_m], errors="coerce").to_numpy(dtype=float)
                                        r_val, p_val, n_val = _pearson_r_p(x_vals, y_vals)
                                        if n_val < 3 or not np.isfinite(r_val):
                                            continue
                                        abs_r = float(abs(r_val))
                                        # Interpret strength + significance (simple, standard thresholds)
                                        if abs_r < 0.10:
                                            strength = "negligible"
                                        elif abs_r < 0.30:
                                            strength = "weak"
                                        elif abs_r < 0.50:
                                            strength = "moderate"
                                        elif abs_r < 0.70:
                                            strength = "strong"
                                        else:
                                            strength = "very strong"
                                        if abs(r_val) < 1e-9:
                                            direction = "neutral"
                                        else:
                                            direction = "positive" if r_val > 0 else "negative"
                                        if np.isfinite(p_val):
                                            sig = "significant" if float(p_val) < 0.05 else "not significant"
                                        else:
                                            sig = "p unavailable"
                                        meaning = f"{strength} {direction} ({sig})"
                                        pair_stats_rows.append(
                                            {
                                                "hrf_metric": str(hrf_m),
                                                "hrv_metric": str(hrv_m),
                                                "test": "Pearson r",
                                                "result": float(r_val),
                                                "p_value": float(p_val) if np.isfinite(p_val) else np.nan,
                                                "n": int(n_val),
                                                "meaning": meaning,
                                                "abs_r": abs_r,
                                            }
                                        )
                                pair_stats_df = pd.DataFrame(pair_stats_rows)
                                if not pair_stats_df.empty:
                                    pair_stats_df = pair_stats_df.sort_values(
                                        "abs_r", ascending=False, ignore_index=True
                                    )
                                st.session_state[cache_key] = {
                                    "upload_signature": list(upload_signature),
                                    "metrics": list(selected_metrics),
                                    "corr": corr_df,
                                    "pair_stats": pair_stats_df,
                                }
                            cached = st.session_state.get(cache_key, {})
                            cached_corr = cached.get("corr")
                            if (
                                isinstance(cached, dict)
                                and cached.get("upload_signature") == list(upload_signature)
                                and cached.get("metrics") == list(selected_metrics)
                                and isinstance(cached_corr, pd.DataFrame)
                                and not cached_corr.empty
                            ):
                                if SCIENTIFIC_CHARTS_AVAILABLE:
                                    corr_chart = build_physiology_correlation_matrix(
                                        correlation_df=cached_corr,
                                        title="HRF ↔ HRV Correlation Matrix (Pearson r)",
                                    )
                                    render_echarts(
                                        corr_chart,
                                        height_px=420,
                                        config=EChartsConfig(),
                                    )
                                else:
                                    st.dataframe(
                                        cached_corr.style.background_gradient(
                                            cmap="RdYlGn", vmin=-1, vmax=1
                                        )
                                    )

                                # Pairwise stats table requested: test, result, p-value, meaning per HRF↔HRV pair.
                                pair_stats = cached.get("pair_stats")
                                if isinstance(pair_stats, pd.DataFrame) and not pair_stats.empty:
                                    st.markdown("**HRF↔HRV pairwise statistics (per pair)**")
                                    st.caption("p-values are shown with **4 decimals** (two-sided Pearson test).")
                                    display_df = pair_stats.copy()
                                    # Ensure the required columns exist (older cache can be missing fields).
                                    for col in ("hrf_metric", "hrv_metric", "test", "result", "p_value", "meaning", "n"):
                                        if col not in display_df.columns:
                                            display_df[col] = np.nan
                                    display_df["result"] = display_df["result"].apply(
                                        lambda v: f"{float(v):.3f}" if np.isfinite(v) else "n/a"
                                    )
                                    display_df["p_value"] = display_df["p_value"].apply(
                                        lambda v: f"{float(v):.4f}" if np.isfinite(v) else "n/a"
                                    )
                                    display_df["n"] = display_df["n"].apply(
                                        lambda v: int(v) if pd.notna(v) else 0
                                    )
                                    display_df = display_df[
                                        ["hrf_metric", "hrv_metric", "test", "result", "p_value", "meaning", "n"]
                                    ]
                                    st.dataframe(
                                        display_df,
                                        use_container_width=True,
                                        hide_index=True,
                                    )

                                    # Top HRF↔HRV pair scatter (by |r|) using the cached stats.
                                    top_row = pair_stats.iloc[0].to_dict()
                                    x_name = str(top_row.get("hrf_metric", ""))
                                    y_name = str(top_row.get("hrv_metric", ""))
                                    if x_name in merged_results.columns and y_name in merged_results.columns:
                                        x = pd.to_numeric(merged_results[x_name], errors="coerce")
                                        y = pd.to_numeric(merged_results[y_name], errors="coerce")
                                        mask = x.notna() & y.notna()
                                        if int(mask.sum()) >= 3:
                                            opt = {
                                                "title": {"text": f"{x_name} vs {y_name}", "left": "center"},
                                                "tooltip": {"trigger": "item"},
                                                "grid": {"left": 48, "right": 18, "containLabel": True},
                                                "xAxis": {"type": "value", "name": x_name},
                                                "yAxis": {"type": "value", "name": y_name},
                                                "series": [
                                                    _echarts_scatter_series(
                                                        "points",
                                                        x_vals=x[mask].to_numpy(),
                                                        y_vals=y[mask].to_numpy(),
                                                    )
                                                ],
                                            }
                                            render_echarts(
                                                opt,
                                                height_px=360,
                                                width="100%",
                                                config=EChartsConfig(),
                                            )
                                            r_disp = top_row.get("result", float("nan"))
                                            p_disp = top_row.get("p_value", float("nan"))
                                            n_disp = int(top_row.get("n", int(mask.sum())))
                                            if np.isfinite(r_disp) and np.isfinite(p_disp):
                                                caption = f"Top pair: r = {float(r_disp):.3f}, p = {float(p_disp):.4f} (n={n_disp})."
                                            elif np.isfinite(r_disp):
                                                caption = f"Top pair: r = {float(r_disp):.3f} (n={n_disp})."
                                            else:
                                                caption = f"Top pair: n={n_disp}."
                                            st.caption(
                                                caption
                                                + " Use this as exploratory association; interpret alongside protocol, posture, and breathing context."
                                            )
                                else:
                                    st.info(
                                        "Not enough overlapping samples to compute HRF↔HRV pairwise tests (need ≥3 recordings per pair)."
                                    )
    with tab_ans:
        st.markdown("### 🫀 Autonomic Function Tests")
        st.markdown("*Clinical-grade autonomic reflex assessments*")
        
        with st.expander("📖 **Understanding Autonomic Tests**", expanded=False):
            st.markdown("""
**These bedside tests evaluate autonomic nervous system integrity:**

**1. Valsalva Maneuver Ratio**
- **Protocol:** Exhale against closed glottis for 15s (strain), then release
- **Physiology:** Tests baroreflex-mediated vagal response
- **Normal:** Ratio ≥1.2 (longest RR after release ÷ shortest RR during strain)
- **Abnormal:** <1.2 suggests impaired parasympathetic response

**2. Deep Breathing (E:I Ratio)**
- **Protocol:** 6 breaths/min (5s inhale, 5s exhale) for 1 minute
- **Physiology:** Maximal respiratory sinus arrhythmia
- **Normal:** E:I difference ≥15 bpm (young adults), ≥10 bpm (elderly)
- **Abnormal:** Reduced difference indicates vagal impairment

**3. 30:15 Ratio (Orthostatic Test)**
- **Protocol:** Stand from supine position
- **Physiology:** Tests initial tachycardia and subsequent bradycardia
- **Normal:** Ratio ≥1.04 (RR at beat 30 ÷ RR at beat 15)
- **Abnormal:** <1.04 suggests impaired baroreceptor function

**Clinical Applications:**
- Diabetic autonomic neuropathy screening
- Parkinson's disease assessment
- Postural orthostatic tachycardia syndrome (POTS)
- Medication effects on autonomic function
            """)
        
        st.markdown(
            "*Configure time windows relative to recording start. "
            "Windows specified in seconds as `start end` (e.g., `15 25`).*")
        if not datasets:
            st.info("Upload a dataset to compute autonomic function metrics.")
        else:
            names = list(datasets.keys())
            selected_dataset_name = st.selectbox("Dataset", names, index=0)
            selected_dataset = datasets[selected_dataset_name]
            use_clean_for_ans = st.checkbox(
                "Use cleaned RR series (if available)",
                value=bool(apply_clean),
                key="ans_use_clean_checkbox",
            )
            try:
                ts_series, rr_series = _prepare_rr_series(
                    selected_dataset, use_clean_for_ans
                )
            except ValueError as exc:
                logger.warning(
                    "Preparing RR series failed: %s",
                    exc,
                    exc_info=True)
                st.warning(str(exc))
            else:
                with st.form(f"ans-form-{selected_dataset_name}"):
                    col_a, col_b = st.columns(2)
                    vals_phase_ii_input = col_a.text_input(
                        "Valsalva phase II window (s)", "15 25"
                    )
                    vals_phase_iv_input = col_b.text_input(
                        "Valsalva phase IV window (s)", "25 35"
                    )
                    deep_start_input = col_a.number_input(
                        "Deep breathing start (s)", min_value=0.0, value=0.0, step=1.0)
                    deep_cycle_input = col_b.number_input(
                        "Deep breathing cycle length (s)",
                        min_value=1.0,
                        value=10.0,
                        step=0.5,
                    )
                    deep_cycles_input = col_a.number_input(
                        "Number of breathing cycles",
                        min_value=1,
                        max_value=12,
                        value=6,
                        step=1,
                    )
                    stand_time_input = col_b.number_input(
                        "Stand event time (s)", min_value=0.0, value=60.0, step=1.0)
                    ratio15_window_input = col_a.text_input(
                        "30:15 ratio – 15th-beat window (s)", "5 20"
                    )
                    ratio30_window_input = col_b.text_input(
                        "30:15 ratio – 30th-beat window (s)", "20 40"
                    )
                    submit_ans = st.form_submit_button("Compute ANS metrics")
                if submit_ans:
                    errors: List[str] = []
                    valsalva_result: Optional[Dict[str, float]] = None
                    deep_breathing_result: Optional[Dict[str, Any]] = None
                    ratio_30_15_result: Optional[Dict[str, float]] = None
                    try:
                        phase_ii_window = _parse_window_seconds(
                            vals_phase_ii_input, "Valsalva phase II window"
                        )
                        phase_iv_window = _parse_window_seconds(
                            vals_phase_iv_input, "Valsalva phase IV window"
                        )
                        valsalva_result = compute_valsalva_ratio(
                            ts_series, rr_series, phase_ii_window, phase_iv_window)
                    except ValueError as exc:
                        logger.warning(
                            "Valsalva ratio computation inputs invalid: %s",
                            exc,
                            exc_info=True,
                        )
                        errors.append(f"Valsalva ratio: {exc}")
                    try:
                        start_time_s = _parse_float(
                            deep_start_input, "Deep breathing start (s)"
                        )
                        cycle_length_s = _parse_float(
                            deep_cycle_input, "Deep breathing cycle length (s)"
                        )
                        deep_breathing_result = compute_deep_breathing_response(
                            ts_series,
                            rr_series,
                            start_time_s=start_time_s,
                            cycle_length_s=cycle_length_s,
                            n_cycles=int(deep_cycles_input),
                        )
                    except ValueError as exc:
                        logger.warning(
                            "Deep breathing response inputs invalid: %s",
                            exc,
                            exc_info=True,
                        )
                        errors.append(f"Deep breathing response: {exc}")
                    try:
                        window_15_s = _parse_window_seconds(
                            ratio15_window_input, "30:15 ratio (15th-beat window)")
                        window_30_s = _parse_window_seconds(
                            ratio30_window_input, "30:15 ratio (30th-beat window)")
                        stand_time_s = _parse_float(
                            stand_time_input, "Stand event time (s)"
                        )
                        ratio_30_15_result = compute_30_15_ratio(
                            ts_series,
                            rr_series,
                            stand_time_s=stand_time_s,
                            window_15_s=window_15_s,
                            window_30_s=window_30_s,
                        )
                    except ValueError as exc:
                        logger.warning(
                            "30:15 ratio inputs invalid: %s", exc, exc_info=True)
                        errors.append(f"30:15 ratio: {exc}")
                    if errors:
                        for err in errors:
                            st.warning(err)
                    if valsalva_result is not None:
                        st.markdown("### Valsalva Ratio")
                        cols = st.columns(3)
                        cols[0].metric(
                            "Valsalva ratio",
                            f"{valsalva_result['valsalva_ratio']:.2f}",
                        )
                        cols[1].metric(
                            "Phase II min RR (ms)",
                            f"{valsalva_result['phase_ii_min_rr_ms']:.1f}",
                        )
                        cols[2].metric(
                            "Phase IV max RR (ms)",
                            f"{valsalva_result['phase_iv_max_rr_ms']:.1f}",
                        )
                    if deep_breathing_result is not None:
                        st.markdown("### Deep Breathing (E:I Response)")
                        col_db1, col_db2, col_db3 = st.columns(3)
                        col_db1.metric(
                            "Mean E–I difference (ms)",
                            f"{deep_breathing_result['ei_mean_difference_ms']:.1f}",
                        )
                        col_db2.metric(
                            "Mean E–I ratio",
                            f"{deep_breathing_result['ei_mean_ratio']:.3f}",
                        )
                        col_db3.metric(
                            "Mean HR difference (bpm)",
                            f"{deep_breathing_result['hr_mean_difference_bpm']:.1f}",
                        )
                        details_df = pd.DataFrame(
                            list(deep_breathing_result["cycle_details"])
                        )
                    if ratio_30_15_result is not None:
                        st.markdown("### 30:15 Ratio")
                        col_30a, col_30b, col_30c = st.columns(3)
                        col_30a.metric(
                            "30:15 ratio",
                            f"{ratio_30_15_result['ratio_30_15']:.2f}",
                        )
                        col_30b.metric(
                            "15th-beat min RR (ms)",
                            f"{ratio_30_15_result['rr_15_min_ms']:.1f}",
                        )
                        col_30c.metric(
                            "30th-beat max RR (ms)",
                            f"{ratio_30_15_result['rr_30_max_ms']:.1f}",
                        )
    with tab_readiness:
        st.markdown("### 🏃 Readiness & Recovery Assessment")
        st.markdown("*Parasympathetic index compared to your personal baseline*")
        
        if not has_hrv_data:
            st.info(
                "🏃 **Readiness Assessment**\n\n"
                "This tab evaluates your autonomic recovery state based on HRV metrics.\n\n"
                "**Readiness Scoring considers:**\n"
                "- Parasympathetic index (HF, RMSSD, pNN50, SD1)\n"
                "- Comparison to your personal baseline\n"
                "- Day-to-day variability patterns\n\n"
                "👈 **Upload HRV data to see your readiness score.**"
            )
        
        with st.expander("📖 **Understanding Readiness Scoring**", expanded=False):
            st.markdown("""
**What is Readiness?**
Readiness reflects your autonomic nervous system's recovery state, primarily driven by **parasympathetic (vagal) activity**. Higher vagal tone generally indicates better recovery and adaptation capacity.

**The Parasympathetic Index (PNS) combines:**
- **HF Power** — Respiratory-linked vagal activity
- **RMSSD** — Beat-to-beat vagal modulation
- **pNN50** — High-frequency variability percentage
- **SD1** — Poincaré short-term dispersion

**Readiness Categories (Kubios-style):**
| Category | Percentile | Interpretation |
|----------|------------|----------------|
| 🔴 **VERY LOW** | <10th | Poor recovery; consider rest |
| 🟠 **LOW** | 10–30th | Below baseline; moderate activity |
| 🟢 **NORMAL** | 30–70th | Typical state; proceed as planned |
| 🔵 **HIGH** | >70th | Excellent recovery; ready for intensity |

**Best Practices:**
- Record at the **same time daily** (morning, upon waking)
- Use **consistent posture** (seated or supine)
- Allow **5+ minutes** of quiet rest before recording
- Build baseline from **≥7 comparable sessions**
            """)
        
        st.markdown(
            "*Compares current parasympathetic index with your historical baseline. "
            "Categories follow Kubios readiness definitions.*")

        # ------------------------------------------------------------------
        # HRF (Heart Rate Fragmentation) panel for performance-oriented review
        # ------------------------------------------------------------------
        if has_hrv_data and "multi_results_df" in locals() and not multi_results_df.empty:
            with st.expander("⚡ HRF (Heart Rate Fragmentation) — Rhythm stability markers", expanded=False):
                st.markdown(
                    "**What is Heart Rate Fragmentation (HRF)?**  \n"
                    "HRF quantifies how often the beat‑to‑beat RR interval dynamics *switch direction* (acceleration ↔ deceleration), "
                    "creating short, alternating runs in the RR time series — a pattern described as **sinoatrial instability** that can "
                    "be present even when the ECG appears sinus rhythm.  \n\n"
                    "**Medical / physiology meaning (high‑level)**  \n"
                    "- HRF reflects a *breakdown of smooth, organized beat‑to‑beat regulation* and may represent components of short‑term "
                    "variability that are **not purely parasympathetic (vagal) modulation**.  \n"
                    "- Because of this, elevated HRF can **confound interpretation** of short‑term HRV magnitude (e.g., HF power / RMSSD) "
                    "as “more vagal tone” in some cases.  \n"
                    "- In older cohorts, HRF markers (e.g., PIP) have been studied as predictors of long‑term incident atrial fibrillation "
                    "(PROOF‑AF).  \n\n"
                    "**Operational interpretation (research / crew context)**  \n"
                    "- **High HRF + low quality / many artifacts** → treat as a *data-quality and ectopy* flag first (motion, poor contact, "
                    "or uncorrected ectopic beats can raise fragmentation).  \n"
                    "- **High HRF + good quality + persistent vs your baseline** → may indicate reduced autonomic stability/recovery or a "
                    "subclinical stressor; interpret alongside mean HR, RMSSD/HF, sleep, symptoms, illness, and training/load context.  \n\n"
                    "**How to decrease / increase HRF (practical levers)**  \n"
                    "- To **decrease measured HRF**: record at true rest (quiet breathing, no talking/movement), ensure good sensor contact, "
                    "and prefer the app’s cleaned RR series when available.  \n"
                    "- Factors that can **increase HRF (or the appearance of HRF)** include irregular breathing, acute stress, sleep loss, "
                    "alcohol, illness/inflammation, stimulants, and ectopic beats/arrhythmia. Treat single-session spikes cautiously and "
                    "focus on trends.  \n\n"
                    "*HRF is an adjunct biomarker and not a standalone diagnosis.*"
                )
                st.caption(
                    "Key references: Costa et al. (2017) https://doi.org/10.3389/fphys.2017.00255; "
                    "Costa et al. (2017) https://doi.org/10.3389/fphys.2017.00827; "
                    "Hayano et al. (2020) https://doi.org/10.3390/app10093314; "
                    "Guichard et al. (2025, PROOF‑AF) https://doi.org/10.1093/ehjopen/oeaf030."
                )
                try:
                    from hrv_fragmentation import HRFMetrics, interpret_hrf_metrics  # noqa: PLC0415
                except Exception:
                    HRFMetrics = None  # type: ignore[assignment]
                    interpret_hrf_metrics = None  # type: ignore[assignment]

                if HRFMetrics is None or interpret_hrf_metrics is None:
                    st.info("HRF module not available.")
                else:
                    src_names = (
                        multi_results_df["source"].astype(str).tolist()
                        if "source" in multi_results_df.columns
                        else ["Current"]
                    )
                    sel_src = st.selectbox(
                        "Dataset",
                        options=src_names,
                        index=max(len(src_names) - 1, 0),
                        key="readiness_hrf_source",
                    )
                    row_hrf = (
                        multi_results_df[multi_results_df["source"] == sel_src].iloc[0]
                        if "source" in multi_results_df.columns
                        else multi_results_df.iloc[0]
                    )
                    pip = float(row_hrf.get("hrf_pip_pct", np.nan))
                    pip_h = float(row_hrf.get("hrf_pip_h_pct", np.nan))
                    pip_s = float(row_hrf.get("hrf_pip_s_pct", np.nan))
                    ials = float(row_hrf.get("hrf_ials", np.nan))
                    pss = float(row_hrf.get("hrf_pss_pct", np.nan))
                    pas = float(row_hrf.get("hrf_pas_pct", np.nan))
                    w0 = float(row_hrf.get("hrf_w0_pct", np.nan))
                    w1 = float(row_hrf.get("hrf_w1_pct", np.nan))
                    w2 = float(row_hrf.get("hrf_w2_pct", np.nan))
                    w3 = float(
                        row_hrf.get(
                            "hrf_w3_pct",
                            row_hrf.get("hrf_w3", np.nan),
                        )
                    )
                    n_int = int(row_hrf.get("n_intervals", 0) or 0)
                    quality_ok = bool(row_hrf.get("hrf_quality_ok", True))

                    cols_hrf_1 = st.columns(4)
                    cols_hrf_1[0].metric("PIP", f"{pip:.1f}%" if np.isfinite(pip) else "n/a")
                    cols_hrf_1[1].metric("PIP_H", f"{pip_h:.1f}%" if np.isfinite(pip_h) else "n/a")
                    cols_hrf_1[2].metric("PIP_S", f"{pip_s:.1f}%" if np.isfinite(pip_s) else "n/a")
                    cols_hrf_1[3].metric("IALS", f"{ials:.3f}" if np.isfinite(ials) else "n/a")

                    cols_hrf_2 = st.columns(4)
                    cols_hrf_2[0].metric("PSS", f"{pss:.1f}%" if np.isfinite(pss) else "n/a")
                    cols_hrf_2[1].metric("PAS", f"{pas:.1f}%" if np.isfinite(pas) else "n/a")
                    cols_hrf_2[2].metric("W3", f"{w3:.1f}%" if np.isfinite(w3) else "n/a")
                    cols_hrf_2[3].metric("Quality", "OK" if quality_ok else "Low")

                    if all(
                        np.isfinite(v)
                        for v in (pip, pip_h, pip_s, ials, pss, pas, w0, w1, w2, w3)
                    ):
                        hrf_obj = HRFMetrics(
                            pip=pip,
                            pip_h=pip_h,
                            pip_s=pip_s,
                            ials=ials,
                            pss=pss,
                            pas=pas,
                            w0=w0,
                            w1=w1,
                            w2=w2,
                            w3=w3,
                            n_intervals=n_int,
                            quality_ok=quality_ok,
                        )
                        interp = interpret_hrf_metrics(hrf_obj)
                        st.markdown(
                            f"- **PIP**: {interp.get('pip', 'n/a')}\n"
                            f"- **W3**: {interp.get('w3', 'n/a')}\n"
                            f"- **IALS**: {interp.get('ials', 'n/a')}"
                        )
                        if "quality" in interp:
                            st.warning(interp["quality"])
                    else:
                        st.info("HRF metrics will appear after you run HRV analysis with advanced metrics enabled.")

                    st.caption(
                        "Interpretation is based on published HRF cohorts and may not generalize to younger/athletic cohorts "
                        "or recordings with substantial ectopy/artifacts. Use trends and clinical/operational context."
                    )
        pns_display_mapping: Dict[str, float] = {}
        ordered_names: List[str] = []
        if active_user_id:
            try:
                hist_df = _cached_pns_history(active_user_id, limit=365)
            except Exception:  # pragma: no cover - defensive
                hist_df = pd.DataFrame()
            if not hist_df.empty and "parasympathetic_index" in hist_df.columns:
                hist_df = hist_df.copy()
                # Ensure chronological ordering (oldest→newest) for baseline building.
                hist_df["measurement_date"] = pd.to_datetime(
                    hist_df["measurement_date"], errors="coerce"
                )
                hist_df["created_at"] = pd.to_datetime(
                    hist_df.get("created_at"), errors="coerce"
                )
                hist_df = hist_df.dropna(subset=["measurement_date"])
                hist_df = hist_df.sort_values(
                    ["measurement_date", "created_at"], ascending=True
                )
                collision_counter: Dict[str, int] = {}
                for _, row in hist_df.iterrows():
                    pns = row.get("parasympathetic_index")
                    try:
                        pns_val = float(pns) if pns is not None else float("nan")
                    except (TypeError, ValueError):
                        pns_val = float("nan")
                    if not np.isfinite(pns_val):
                        continue
                    date_ts = row.get("measurement_date")
                    date_label = (
                        pd.to_datetime(date_ts).date().isoformat()
                        if date_ts is not None
                        else "unknown-date"
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
                    pns_display_mapping[label] = pns_val
                    ordered_names.append(label)

        # Fall back to current-session computed mapping when DB history is unavailable.
        if not pns_display_mapping and pns_mapping:
            pns_display_mapping = dict(pns_mapping)
            ordered_names = [name for name in ordered_sources if name in pns_display_mapping]

        if not pns_display_mapping:
            st.info(
                "No readiness history available yet. Run HRV analysis (or save HRV measurements) "
                "to build a parasympathetic baseline."
            )
        else:
            if not ordered_names:
                st.info(
                    "Ready metrics unavailable; ensure parasympathetic index was computed."
                )
            else:
                default_idx = max(len(ordered_names) - 1, 0)
                current_sel = st.selectbox(
                    "Current measurement", ordered_names, index=default_idx
                )
                default_baseline = [
                    name for name in ordered_names if name != current_sel
                ]
                baseline_sel = st.multiselect(
                    "Historical baseline datasets (oldest to newest)",
                    options=ordered_names,
                    default=default_baseline,
                )
                include_current = st.checkbox(
                    "Include current measurement in baseline", value=False
                )
                min_hist = int(
                    st.number_input(
                        "Minimum historical samples",
                        min_value=3,
                        max_value=30,
                        value=7,
                        step=1,
                    )
                )
                max_default = int(max(min_hist, min(30, len(ordered_names))))
                max_hist = int(
                    st.slider(
                        "Historical window (max records retained)",
                        min_value=min_hist,
                        max_value=90,
                        value=max_default,
                        step=1,
                    )
                )
                history_names: List[str] = []
                for name in ordered_names:
                    if name in baseline_sel and (
                        include_current or name != current_sel
                    ):
                        history_names.append(name)
                if include_current and current_sel not in history_names:
                    history_names.append(current_sel)
                if not history_names:
                    st.warning(
                        "Select at least one baseline record to build readiness baseline."
                    )
                else:
                    history_values = [
                        pns_display_mapping[name]
                        for name in ordered_names
                        if name in history_names
                    ]
                    # Avoid raising errors when insufficient history is
                    # available
                    if len(history_values) < int(min_hist):
                        st.info(
                            f"Readiness baseline needs at least {int(min_hist)} samples; currently {len(history_values)}."
                        )
                        baseline = None
                    else:
                        try:
                            baseline = build_readiness_baseline(
                                history_values,
                                min_samples=min_hist,
                                max_samples=max_hist,
                            )
                        except ValueError as exc:
                            logger.warning(
                                "Readiness baseline configuration issue: %s",
                                exc,
                                exc_info=True,
                            )
                            st.warning(f"Baseline configuration issue: {exc}")
                            baseline = None
                    if baseline is not None:
                        current_pns = float(
                            pns_display_mapping.get(
                                current_sel, np.nan))
                        if not np.isfinite(current_pns):
                            st.warning(
                                "Current measurement lacks a valid parasympathetic index."
                            )
                        else:
                            readiness = readiness_from_pns(
                                current_pns, baseline)
                            col_a, col_b, col_c = st.columns(3)
                            col_a.metric(
                                "Readiness score (percentile)",
                                f"{readiness['readiness_score']:.1f}",
                            )
                            col_b.metric(
                                "Category", readiness["readiness_category"])
                            col_c.metric(
                                "PNS index",
                                f"{readiness['pns_index']:.3f}",
                            )
                            details_df = pd.DataFrame(
                                {
                                    "baseline_mean": [
                                        readiness["baseline_mean"]], "baseline_std": [
                                        readiness["baseline_std"]], "very_low_cut": [
                                        readiness["very_low_cut"]], "low_cut": [
                                        readiness["low_cut"]], "high_cut": [
                                        readiness["high_cut"]], "baseline_samples": [
                                        readiness["baseline_count"]], "z_score": [
                                        readiness["z_score"]], })
                            st.dataframe(details_df)
                            history_labels = history_names.copy()
                            if current_sel not in history_labels:
                                history_labels.append(current_sel)
                            line_series = {
                                "name": "Baseline PNS history",
                                "type": "line",
                                "showSymbol": True,
                                "smooth": True,
                                "data": [
                                    [label, float(pns_display_mapping[label])]
                                    for label in history_names
                                ],
                            }
                            current_series = {
                                "name": f"{current_sel} (current)",
                                "type": "scatter",
                                "symbolSize": 12,
                                "itemStyle": {"color": "#1e88e5"},
                                "data": [[current_sel, readiness["pns_index"]]],
                            }
                            opt = {
                                "title": {
                                    "text": "Parasympathetic index baseline",
                                    "left": "center",
                                },
                                "tooltip": {"trigger": "axis"},
                                "grid": {"left": 32, "right": 16, "containLabel": True},
                                "xAxis": {
                                    "type": "category",
                                    "name": "Session",
                                    "data": history_labels,
                                    "boundaryGap": False,
                                },
                                "yAxis": {"type": "value", "name": "PNS index"},
                                "legend": {"top": 24},
                                "series": [line_series, current_series],
                            }
                            mark_lines = [
                                {
                                    "yAxis": readiness["very_low_cut"], "name": "Very low cut", }, {
                                    "yAxis": readiness["low_cut"], "name": "Low cut"}, {
                                    "yAxis": readiness["high_cut"], "name": "High cut"}, ]
                            line_series["markLine"] = {
                                "symbol": "none",
                                "data": mark_lines,
                            }
                            render_echarts(
                                opt, height_px=360, width="100%", config=EChartsConfig())
                            st.markdown(
                                "- **VERY LOW**: below ~3% of historical PNS values; indicative of high stress or limited recovery.  \n"
                                "- **LOW**: between ~3% and 17%, often aligned with moderate stress or incomplete rest.  \n"
                                "- **NORMAL**: within ~17–84% of history, reflecting typical readiness.  \n"
                                "- **HIGH**: above ~84%, often seen with strong recovery and parasympathetic dominance.")
                            st.caption(
                                "Baseline uses the selected historical sessions (last-in-first-out capped at the chosen window). "
                                "Consistent daily morning recordings (1–5 minutes, relaxed breathing) improve reliability.")
    with tab_gauges:
        st.markdown("### 🎯 HRV Metric Gauges")
        st.markdown("*Visual comparison against population reference ranges*")
        
        if not has_hrv_data:
            st.info(
                "🎯 **HRV Gauges**\n\n"
                "This tab shows visual gauges comparing your metrics to reference ranges.\n\n"
                "**Gauge Interpretation:**\n"
                "- 🟢 Green: Within normal range\n"
                "- 🟡 Yellow: Borderline (1-2 SD)\n"
                "- 🔴 Red: Outside typical range (>2 SD)\n\n"
                "👈 **Upload HRV data to see your gauges.**"
            )
        elif skip_gauges:
            st.info("Gauges disabled (Performance & display).")
        else:
            _render_dataset_info_header(datasets, title="Recordings Available")
            _render_normogram_gauges(multi_results_df)
        
        with st.expander("📖 **Understanding the Gauges**", expanded=False):
            st.markdown("""
**Color Zones:**
- 🟢 **Green zone:** Within normal range (mean ± 1 SD)
- 🟡 **Yellow zone:** Borderline (1-2 SD from mean)
- 🔴 **Red zone:** Outside typical range (>2 SD from mean)

**Key Metrics Displayed:**
| Gauge | What it measures | Optimal direction |
|-------|------------------|-------------------|
| **SDNN** | Total variability | ↑ Higher is generally better |
| **RMSSD** | Vagal (parasympathetic) tone | ↑ Higher indicates good recovery |
| **LF/HF** | Autonomic "balance" | → Context-dependent (breathing matters) |
| **HF Power** | Parasympathetic activity | ↑ Higher during rest/recovery |

⚠️ **Important:** Reference ranges are population averages. Your personal baseline may differ. Track **trends over time** rather than single readings.
            """)
        
        st.caption(
            "References: [Nunan et al., 2010](https://pubmed.ncbi.nlm.nih.gov/20663071/); "
            "[Sammito & Böckelmann, 2016](https://pubmed.ncbi.nlm.nih.gov/27986557/).")

    # =========================================================================
    # UNIFIED TIMELINE TAB - Multi-metric synchronized visualization
    # =========================================================================
    with tab_unified:
        st.markdown("### 📈 Unified Physiological Timeline")
        st.markdown("*Time-synchronized view of all physiological metrics with ML pattern detection*")
        
        if not has_hrv_data:
            st.info(
                "📈 **Unified Timeline**\n\n"
                "This tab provides a synchronized view of multiple physiological metrics.\n\n"
                "**Features:**\n"
                "- Cross-domain metric visualization\n"
                "- ML-based pattern detection\n"
                "- Temporal relationship analysis\n\n"
                "👈 **Upload HRV data to see your unified timeline.**"
            )
        
        with st.expander("📖 **Understanding the Unified Timeline**", expanded=False):
            st.markdown("""
**Purpose:**
The Unified Timeline provides a synchronized view of multiple physiological metrics, enabling:
- **Cross-domain analysis** — See how HRV, HR, stress, and other metrics co-vary
- **Pattern detection** — ML algorithms identify anomalies and trends
- **Temporal relationships** — Observe how changes in one metric precede/follow others

**Available Metrics:**
| Domain | Metrics | Physiological Significance |
|--------|---------|---------------------------|
| **HRV** | RMSSD, SDNN, LF/HF | Autonomic nervous system balance |
| **Cardiac** | Mean HR, Resting HR | Cardiovascular load and recovery |
| **Respiratory** | SpO2, Respiration Rate | Oxygenation and breathing patterns |
| **Stress/Energy** | Stress Score, Body Battery | Allostatic load and recovery capacity |

**ML Features:**
- **Anomaly Detection** — Z-score, MAD, IQR methods to flag unusual values
- **Trend Analysis** — Linear regression with change point detection
- **Correlation Matrix** — Identify relationships between metrics
            """)
        
        if not SCIENTIFIC_CHARTS_AVAILABLE:
            st.warning("Scientific charts module not available. Some visualizations disabled.")
        
        # Check if we have data to display
        if multi_results_df.empty:
            st.info("📁 Upload HRV data files to see the unified timeline visualization.")
        else:
            st.markdown("---")
            if active_user_context.get("has_user"):
                sync_col, info_col = st.columns([1, 3])
                with sync_col:
                    if st.button(
                        "Sync with active profile",
                        key="fatigue_sync_profile",
                        help="Refresh all fatigue inputs from the latest active user context.",
                    ):
                        fatigue_defaults = _sync_fatigue_widgets(
                            active_user_context, force=True
                        )
                        st.success(
                            f"Inputs synced for {active_user_context.get('full_name') or active_user_context.get('username') or 'active user'}."
                        )
                with info_col:
                    st.caption(
                        "Profile-linked defaults use the latest exploration medical record "
                        "to seed age, chronotype, sleep debt, and work cadence."
                    )
            else:
                st.caption(
                    "No active user selected — using mission-generic defaults for fatigue modelling."
                )
            
            # Metric selection
            st.markdown("#### 📊 Select Metrics to Display")
            
            # Get available numeric columns from results
            available_metrics = [
                col for col in multi_results_df.columns
                if col not in ["source", "timestamp", "start", "end", "label"]
                and pd.api.types.is_numeric_dtype(multi_results_df[col])
            ]
            
            # Group metrics by domain
            hrv_metrics = [m for m in available_metrics if any(x in m.lower() for x in ["rmssd", "sdnn", "pnn", "lf", "hf", "entropy"])]
            cardiac_metrics = [m for m in available_metrics if any(x in m.lower() for x in ["hr", "heart", "bpm"])]
            other_metrics = [m for m in available_metrics if m not in hrv_metrics and m not in cardiac_metrics]
            
            col_hrv, col_cardiac, col_other = st.columns(3)
            
            with col_hrv:
                st.markdown("**HRV Metrics**")
                selected_hrv = st.multiselect(
                    "Select HRV metrics",
                    options=hrv_metrics,
                    default=hrv_metrics[:3] if len(hrv_metrics) >= 3 else hrv_metrics,
                    key="unified_hrv_metrics",
                    label_visibility="collapsed"
                )
            
            with col_cardiac:
                st.markdown("**Cardiac Metrics**")
                selected_cardiac = st.multiselect(
                    "Select Cardiac metrics",
                    options=cardiac_metrics,
                    default=cardiac_metrics[:2] if len(cardiac_metrics) >= 2 else cardiac_metrics,
                    key="unified_cardiac_metrics",
                    label_visibility="collapsed"
                )
            
            with col_other:
                st.markdown("**Other Metrics**")
                selected_other = st.multiselect(
                    "Select Other metrics",
                    options=other_metrics,
                    default=[],
                    key="unified_other_metrics",
                    label_visibility="collapsed"
                )
            
            selected_metrics = selected_hrv + selected_cardiac + selected_other
            
            if selected_metrics and SCIENTIFIC_CHARTS_AVAILABLE:
                st.markdown("---")
                st.markdown("#### 📈 Synchronized Timeline")
                
                # Prepare data for unified timeline
                # Use timestamp if available, otherwise use index
                if "timestamp" in multi_results_df.columns:
                    timestamps = pd.to_datetime(multi_results_df["timestamp"])
                elif "start" in multi_results_df.columns:
                    timestamps = pd.to_datetime(multi_results_df["start"])
                else:
                    timestamps = pd.to_datetime(multi_results_df.index)
                
                # Build metrics dict
                metrics_dict = {}
                for metric in selected_metrics:
                    if metric in multi_results_df.columns:
                        values = multi_results_df[metric].values
                        metrics_dict[metric] = values
                
                if metrics_dict:
                    # Build unified timeline chart
                    unified_chart = build_unified_physiology_timeline(
                        timestamps=list(timestamps),
                        metrics=metrics_dict,
                        title="Unified Physiological Timeline",
                    )
                    
                    render_echarts(
                        unified_chart,
                        height_px=500,
                        config=EChartsConfig()
                    )
                
                # ML Pattern Detection
                st.markdown("---")
                st.markdown("#### 🔍 ML Pattern Detection")
                
                if ML_ANALYTICS_AVAILABLE:
                    col_ml1, col_ml2 = st.columns([1, 2])
                    
                    with col_ml1:
                        ml_metric = st.selectbox(
                            "Select metric for analysis",
                            options=selected_metrics,
                            key="ml_pattern_metric"
                        )
                        
                        anomaly_method = st.selectbox(
                            "Anomaly detection method",
                            options=["Z-score", "MAD (Robust)", "IQR"],
                            key="ml_anomaly_method"
                        )
                        
                        run_ml = st.button("🔬 Run ML Analysis", key="run_ml_btn")
                    
                    if run_ml and ml_metric in multi_results_df.columns:
                        with st.spinner("Running ML analysis..."):
                            # Get non-NaN mask and values while preserving index alignment
                            metric_series = multi_results_df[ml_metric]
                            valid_mask = metric_series.notna()
                            values = metric_series[valid_mask].values
                            # Store the valid indices for timestamp alignment
                            valid_indices = np.where(valid_mask)[0]
                            
                            if len(values) < 5:
                                st.warning("Insufficient data points for ML analysis (need at least 5).")
                            else:
                                # Anomaly detection
                                if anomaly_method == "Z-score":
                                    anomaly_result = detect_anomalies_zscore(values, threshold=2.5)
                                elif anomaly_method == "MAD (Robust)":
                                    anomaly_result = detect_anomalies_mad(values, threshold=3.0)
                                else:
                                    anomaly_result = detect_anomalies_iqr(values, k=1.5)
                                
                                # Trend analysis
                                trend_result = analyze_trend(values)
                                
                                # Store results along with valid indices for proper alignment
                                st.session_state["ml_anomaly_result"] = anomaly_result
                                st.session_state["ml_trend_result"] = trend_result
                                st.session_state["ml_metric_name"] = ml_metric
                                st.session_state["ml_valid_indices"] = valid_indices
                    
                    # Display ML results
                    if "ml_anomaly_result" in st.session_state:
                        anomaly_result = st.session_state["ml_anomaly_result"]
                        trend_result = st.session_state["ml_trend_result"]
                        ml_metric_name = st.session_state.get("ml_metric_name", "Metric")
                        valid_indices = st.session_state.get("ml_valid_indices", None)
                        
                        with col_ml2:
                            # Summary metrics
                            col_a, col_b, col_c, col_d = st.columns(4)
                            with col_a:
                                st.metric("Anomalies", f"{anomaly_result.n_anomalies}")
                            with col_b:
                                st.metric("Trend", trend_result.direction.value.title())
                            with col_c:
                                st.metric("Slope", f"{trend_result.slope:.4f}")
                            with col_d:
                                st.metric("R²", f"{trend_result.r_squared:.3f}")
                        
                        # ML Pattern chart
                        if ml_metric_name in multi_results_df.columns and valid_indices is not None:
                            # Get values using valid indices for proper alignment
                            metric_series = multi_results_df[ml_metric_name]
                            valid_mask = metric_series.notna()
                            values = metric_series[valid_mask].values
                            
                            # Use valid indices to get correctly aligned timestamps
                            aligned_timestamps = [timestamps[i] for i in valid_indices if i < len(timestamps)]
                            
                            # Ensure lengths match
                            min_len = min(len(aligned_timestamps), len(values))
                            aligned_timestamps = aligned_timestamps[:min_len]
                            values = values[:min_len]
                            
                            # Compute trend line
                            x = np.arange(len(values))
                            trend_line = trend_result.slope * x + (np.mean(values) - trend_result.slope * np.mean(x))
                            
                            # Ensure anomaly mask matches
                            anomaly_mask = anomaly_result.is_anomaly[:min_len] if len(anomaly_result.is_anomaly) > min_len else anomaly_result.is_anomaly
                            
                            ml_chart = build_ml_pattern_chart(
                                timestamps=list(aligned_timestamps),
                                values=values,
                                anomaly_mask=anomaly_mask,
                                trend_line=trend_line[:min_len],
                                change_points=list(trend_result.change_points) if len(trend_result.change_points) > 0 else None,
                                title=f"ML Pattern Analysis: {ml_metric_name}",
                                metric_name=ml_metric_name,
                            )
                            
                            render_echarts(
                                ml_chart,
                                height_px=400,
                                config=EChartsConfig()
                            )
                        
                        # Interpretation
                        st.markdown("**Interpretation:**")
                        interp_parts = []
                        
                        if anomaly_result.n_anomalies > 0:
                            pct = 100 * anomaly_result.n_anomalies / len(anomaly_result.is_anomaly)
                            interp_parts.append(f"- **{anomaly_result.n_anomalies} anomalies** detected ({pct:.1f}% of data)")
                        else:
                            interp_parts.append("- No significant anomalies detected")
                        
                        if trend_result.p_value < 0.05:
                            direction = "increasing" if trend_result.slope > 0 else "decreasing"
                            interp_parts.append(f"- **Significant {direction} trend** (p={trend_result.p_value:.4f})")
                        else:
                            interp_parts.append("- No significant trend detected")
                        
                        if len(trend_result.change_points) > 0:
                            interp_parts.append(f"- **{len(trend_result.change_points)} change points** detected")
                        
                        st.markdown("\n".join(interp_parts))
                else:
                    st.info("ML analytics module not available.")
                
                # Correlation Matrix (explicitly on-demand)
                st.markdown("---")
                st.markdown("#### 🔗 Metric Correlations")

                if len(selected_metrics) < 2:
                    st.info("Select at least 2 metrics to compute correlations.")
                else:
                    st.info(
                        "Correlations run only when you click **Run correlations**. "
                        "A spinner will appear during computation; large selections may take a few seconds."
                    )
                    run_metric_corr = st.button(
                        "Run correlations",
                        key="metric_corr_run",
                        help="Compute the correlation matrix for the selected metrics.",
                    )
                    if not run_metric_corr:
                        st.info("Click **Run correlations** to compute the correlation matrix.")
                    elif not STATISTICAL_ANALYSIS_AVAILABLE:
                        st.warning("Statistical analysis module not available.")
                    else:
                        available_metrics = [m for m in selected_metrics if m in multi_results_df.columns]

                        if len(available_metrics) < 2:
                            st.warning("Not enough valid metrics available for correlation analysis.")
                        else:
                            try:
                                with st.spinner("Computing correlations..."):
                                    corr_df = multi_results_df[available_metrics].corr()

                                if corr_df.empty or corr_df.isnull().all().all():
                                    st.warning("Could not compute correlations - insufficient data.")
                                else:
                                    if SCIENTIFIC_CHARTS_AVAILABLE:
                                        corr_chart = build_physiology_correlation_matrix(
                                            correlation_df=corr_df,
                                            title="Physiological Metrics Correlation Matrix",
                                        )

                                        render_echarts(
                                            corr_chart,
                                            height_px=400,
                                            config=EChartsConfig()
                                        )
                                    else:
                                        st.dataframe(corr_df.style.background_gradient(cmap="RdYlGn", vmin=-1, vmax=1))

                                    st.markdown("**Significant Correlations (|r| > 0.5):**")
                                    sig_corrs = []
                                    for i, m1 in enumerate(available_metrics):
                                        for j, m2 in enumerate(available_metrics):
                                            if i < j and m1 in corr_df.index and m2 in corr_df.columns:
                                                r = corr_df.loc[m1, m2]
                                                if pd.notna(r) and abs(r) > 0.5:
                                                    direction = "positive" if r > 0 else "negative"
                                                    strength = "strong" if abs(r) > 0.7 else "moderate"
                                                    sig_corrs.append(f"- **{m1}** ↔ **{m2}**: r = {r:.3f} ({strength} {direction})")

                                    if sig_corrs:
                                        st.markdown("\n".join(sig_corrs))
                                    else:
                                        st.info("No correlations with |r| > 0.5 found among selected metrics.")
                            except Exception as e:
                                logger.warning(f"Correlation computation failed: {e}")
                                st.warning(f"Could not compute correlations: {e}")
            elif not selected_metrics:
                st.info("Select at least one metric to display the timeline.")
        
        st.caption(
            "**Scientific basis:** Multi-metric analysis enables detection of autonomic patterns that "
            "single-metric analysis may miss. Cross-domain correlations can reveal compensatory mechanisms "
            "and early warning signs of physiological stress."
        )

    # =========================================================================
    # POPULATION NORMS TAB - Compare against reference values
    # =========================================================================
    with tab_pop_norms:
        st.markdown("### 📊 Population Norms Comparison")
        st.markdown("*Compare your HRV metrics against scientifically validated reference values*")
        
        if not POPULATION_NORMS_AVAILABLE:
            st.error("Population norms module not available. Please check installation.")
        else:
            # Explanation section
            with st.expander("📖 **Understanding Population Norms**", expanded=False):
                st.markdown("""
**Why Compare to Population Norms?**

Heart Rate Variability (HRV) metrics vary significantly across individuals based on:
- **Age**: HRV naturally decreases with aging
- **Sex**: Women typically have higher RMSSD (vagal tone)
- **Fitness**: Athletes often have higher HRV
- **Health status**: Various conditions affect HRV

**Data Sources:**

| Source | Sample Size | Population |
|--------|-------------|------------|
| Nunan et al. 2010 | n=21,438 | Meta-analysis of 44 studies |
| Ortega et al. 2024 | n=2,143 | Singapore (ages 10-89) |
| O'Neal et al. 2016 (MESA) | n=5,966 | Multi-ethnic US population |
| Task Force 1996 | Guidelines | European/NA consensus |

**Interpretation:**
- **Percentile < 5%**: Significantly below norms - consider clinical evaluation
- **Percentile 5-25%**: Below average - may warrant attention
- **Percentile 25-75%**: Normal range
- **Percentile 75-95%**: Above average - typically favorable
- **Percentile > 95%**: Significantly above norms

*Note: Population norms are reference guides, not diagnostic criteria. 
Context (posture, time of day, medications) strongly affects interpretation.*
                """)
            
            st.divider()
            
            # User input for demographics (prefill from selected profile if available)
            prof = st.session_state.get("current_user_profile") or {}
            profile_age_default = st.session_state.get("user_age", 35)
            profile_sex_default = st.session_state.get("user_sex", "All (combined)")
            if isinstance(prof, dict):
                if prof.get("age_years") is not None:
                    profile_age_default = int(prof["age_years"])
                elif prof.get("date_of_birth"):
                    try:
                        dob = pd.to_datetime(prof["date_of_birth"]).date()
                        today = pd.Timestamp.utcnow().date()
                        age_calc = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                        profile_age_default = max(10, min(100, age_calc))
                    except Exception:
                        pass
                if prof.get("sex"):
                    sex_val = str(prof.get("sex", "")).lower()
                    if sex_val in ("male", "m"):
                        profile_sex_default = "Male"
                    elif sex_val in ("female", "f"):
                        profile_sex_default = "Female"

            col_demo1, col_demo2 = st.columns(2)
            with col_demo1:
                user_age = st.number_input(
                    "Your Age (years)",
                    min_value=10,
                    max_value=100,
                    value=profile_age_default,
                    help="Age affects normative ranges - HRV typically decreases with age"
                )
                st.session_state["user_age"] = user_age
            
            with col_demo2:
                user_sex = st.selectbox(
                    "Biological Sex",
                    options=["All (combined)", "Male", "Female"],
                    index=["All (combined)", "Male", "Female"].index(profile_sex_default),
                    help="Sex affects some HRV norms, particularly vagal metrics"
                )
                sex_value = None if user_sex == "All (combined)" else user_sex.lower()
            
            # Show age group
            age_group = get_age_group(user_age)
            st.info(f"**Reference Group**: Age {age_group.value}, Sex: {user_sex}")
            
            st.divider()
            
            # -----------------------------------------------------------------
            # HRV metrics source selection
            # -----------------------------------------------------------------
            metric_mapping = {
                "sdnn": "sdnn",
                "rmssd": "rmssd",
                "pnn50": "pnn50",
                "lf_power": "lf_power",
                "hf_power": "hf_power",
                "lf_hf_ratio": "lf_hf_ratio",
                "sd1": "sd1",
                "sd2": "sd2",
                "mean_hr": "mean_hr",
            }
            # Prefer processed sources when available; otherwise fall back to uploads.
            source_options: List[str] = []
            if (
                isinstance(multi_results_df, pd.DataFrame)
                and not multi_results_df.empty
                and "source" in multi_results_df.columns
            ):
                source_options = [
                    str(s)
                    for s in multi_results_df["source"].dropna().astype(str).tolist()
                ]
            elif _rr_sources:
                source_options = [str(s) for s in _rr_sources.keys()]
            if ordered_sources:
                source_options = (
                    [s for s in ordered_sources if s in source_options]
                    + [s for s in source_options if s not in ordered_sources]
                )
            # De-duplicate while preserving order
            source_options = [s for s in dict.fromkeys(source_options)]
            selected_source: Optional[str] = None
            if source_options:
                selected_source = st.selectbox(
                    "Recording to compare",
                    options=source_options,
                    index=0,
                    key="pop_norms_source_select",
                )

            # -----------------------------------------------------------------
            # Compute or reuse metrics for comparison
            # -----------------------------------------------------------------
            if not has_hrv_data:
                st.warning(
                    "⚠️ **No RR data loaded**\n\n"
                    "Upload RR interval data using the sidebar to compare your metrics against population norms.\n\n"
                    "**Available metrics for comparison:**\n"
                    "- Time domain: SDNN, RMSSD, pNN50\n"
                    "- Frequency domain: LF Power, HF Power, LF/HF Ratio\n"
                    "- Nonlinear: SD1, SD2\n"
                    "- Heart rate: Mean HR"
                )

                # Show example with simulated data - use checkbox instead of expander
                # (render_population_comparison_ui uses expanders internally, can't nest)
                st.markdown("---")
                show_example = st.checkbox(
                    "📋 Show Example Comparison (Simulated Data)",
                    value=False,
                    key="pop_norms_example_checkbox",
                )
                if show_example:
                    example_metrics = {
                        "sdnn": 45.2,
                        "rmssd": 38.5,
                        "pnn50": 15.3,
                        "lf_power": 980.0,
                        "hf_power": 720.0,
                        "lf_hf_ratio": 1.36,
                        "mean_hr": 68.0,
                    }
                    st.markdown("**Example metrics for a 35-year-old:**")
                    render_population_comparison_ui(
                        hrv_metrics=example_metrics,
                        age=35,
                        sex=None,
                    )
            else:
                st.success(f"✓ RR data available ({total_rr_count:,} RR intervals)")
                if selected_source is None:
                    st.info("Select a recording above to compare against norms.")
                else:
                    selected_up = _rr_sources.get(selected_source) if _rr_sources else None
                    duration_min: Optional[float] = None
                    if (
                        selected_up is not None
                        and isinstance(selected_up.rr_ms, np.ndarray)
                        and selected_up.rr_ms.size > 0
                    ):
                        duration_min = float(
                            selected_up.rr_ms.size
                            * float(np.mean(selected_up.rr_ms))
                            / 60000.0
                        )
                        st.caption(
                            f"Selected recording duration ≈ {duration_min:.1f} min. "
                            "Most published population norms are for ~5-minute short-term HRV."
                        )

                    hrv_metrics_for_comparison: Dict[str, float] = {}
                    comparison_basis = ""

                    # 1) Preferred: mean of windowed metrics for the selected source (aligns with 5-min norms)
                    if (
                        isinstance(windowed_df, pd.DataFrame)
                        and not windowed_df.empty
                        and "source" in windowed_df.columns
                    ):
                        sub_df = windowed_df[windowed_df["source"] == selected_source]
                        if not sub_df.empty:
                            for col, norm_name in metric_mapping.items():
                                if col not in sub_df.columns:
                                    continue
                                vals = pd.to_numeric(sub_df[col], errors="coerce").dropna()
                                if len(vals) > 0:
                                    hrv_metrics_for_comparison[norm_name] = float(vals.mean())
                            if hrv_metrics_for_comparison:
                                comparison_basis = "windowed_mean"

                    # 2) Fallback: full-recording summary metrics (available after "Run HRV Analysis")
                    if (
                        not hrv_metrics_for_comparison
                        and isinstance(multi_results_df, pd.DataFrame)
                        and not multi_results_df.empty
                        and "source" in multi_results_df.columns
                    ):
                        row_df = multi_results_df[multi_results_df["source"] == selected_source]
                        if not row_df.empty:
                            row = row_df.iloc[0]
                            for col, norm_name in metric_mapping.items():
                                if col not in row_df.columns:
                                    continue
                                try:
                                    val = float(row[col])
                                except (TypeError, ValueError):
                                    continue
                                if np.isfinite(val):
                                    hrv_metrics_for_comparison[norm_name] = float(val)
                            if hrv_metrics_for_comparison:
                                comparison_basis = "full_recording"

                    # 3) Final fallback: compute a quick summary directly from the RR series (no full analysis)
                    if not hrv_metrics_for_comparison and selected_up is not None:
                        rr = (
                            selected_up.rr_ms_clean
                            if (apply_clean and selected_up.rr_ms_clean is not None)
                            else selected_up.rr_ms
                        )
                        if isinstance(rr, np.ndarray) and rr.size > 0:
                            if rr.size > 200_000:
                                st.info(
                                    "This recording is very long. For stability and caching, "
                                    "run **Run HRV Analysis** and then return to this tab."
                                )
                            else:
                                include_freq_quick = st.checkbox(
                                    "Include frequency-domain metrics (LF/HF) in quick comparison",
                                    value=False,
                                    key="pop_norms_quick_freq",
                                    help="Computes LF/HF from interpolated PSD; slower than time-domain.",
                                )
                                from hrv_core import (
                                    compute_frequency_domain_metrics as _fd,
                                    compute_poincare_metrics as _pc,
                                    compute_time_domain_metrics as _td,
                                )

                                td = _td(rr)
                                pc = _pc(rr)
                                for key in ("sdnn", "rmssd", "pnn50", "mean_hr"):
                                    val = td.get(key)
                                    if val is not None and np.isfinite(val):
                                        hrv_metrics_for_comparison[key] = float(val)
                                for key in ("sd1", "sd2"):
                                    val = pc.get(key)
                                    if val is not None and np.isfinite(val):
                                        hrv_metrics_for_comparison[key] = float(val)
                                if include_freq_quick:
                                    freq = _fd(rr, method=str(psd_method))
                                    for key in ("lf_power", "hf_power", "lf_hf_ratio"):
                                        val = freq.get(key)
                                        if val is not None and np.isfinite(val):
                                            hrv_metrics_for_comparison[key] = float(val)
                                if hrv_metrics_for_comparison:
                                    comparison_basis = "quick_metrics"

                    if hrv_metrics_for_comparison:
                        basis_label = {
                            "windowed_mean": "Windowed mean (recommended for ~5-min norms)",
                            "full_recording": "Full-recording summary (may differ vs ~5-min norms)",
                            "quick_metrics": "Quick RR-derived summary (may differ vs ~5-min norms)",
                        }.get(comparison_basis, "Computed metrics")
                        st.info(f"**Comparison basis**: {basis_label}")
                        if duration_min is not None and duration_min < 5.0:
                            st.warning(
                                "Recording appears shorter than 5 minutes. "
                                "Population percentiles shown are primarily derived from ~5-minute recordings, "
                                "so interpret cautiously."
                            )
                        render_population_comparison_ui(
                            hrv_metrics=hrv_metrics_for_comparison,
                            age=user_age,
                            sex=sex_value,
                        )

                        # Additional export option
                        st.divider()
                        if st.button("📥 Export Comparison Report", key="export_pop_norms"):
                            report = generate_population_comparison_report(
                                hrv_metrics=hrv_metrics_for_comparison,
                                age=user_age,
                                sex=sex_value,
                            )
                            st.json(report)
                            st.download_button(
                                label="Download JSON Report",
                                data=json.dumps(report, indent=2),
                                file_name="hrv_population_comparison.json",
                                mime="application/json",
                            )
                    else:
                        st.warning(
                            "Could not extract HRV metrics for comparison yet. "
                            "Click **Run HRV Analysis** (sidebar) or adjust window settings for longer recordings."
                        )
            
            # Reference information
            st.divider()
            with st.expander("📚 **References and Citations**"):
                st.markdown("""
**Primary References for Normative Data:**

1. **Nunan D, Sandercock GR, Brodie DA** (2010). A quantitative systematic review of 
   normal values for short-term heart rate variability in healthy adults. 
   *Pacing Clin Electrophysiol*, 33(11):1407-17. [PMID: 20663071](https://pubmed.ncbi.nlm.nih.gov/20663071/)

2. **Ortega E, Bryan CYX, Christine NSC** (2024). The Pulse of Singapore: Short-Term 
   HRV Norms. *Appl Psychophysiol Biofeedback*, 49(1):31-40. 
   [PMID: 37755550](https://pubmed.ncbi.nlm.nih.gov/37755550/)

3. **O'Neal WT, Chen LY, Nazarian S, Soliman EZ** (2016). Reference ranges for short-term 
   heart rate variability measures in individuals free of cardiovascular disease: 
   The Multi-Ethnic Study of Atherosclerosis (MESA). *J Electrocardiol*, 49(5):686-90. 
   [PMID: 27396499](https://pubmed.ncbi.nlm.nih.gov/27396499/)

4. **Task Force of ESC and NASPE** (1996). Heart rate variability: standards of measurement, 
   physiological interpretation and clinical use. *Circulation*, 93(5):1043-65. 
   [PMID: 8598068](https://pubmed.ncbi.nlm.nih.gov/8598068/)

5. **Shaffer F, Ginsberg JP** (2017). An Overview of Heart Rate Variability Metrics and Norms. 
   *Front Public Health*, 5:258. [PMID: 29034226](https://pubmed.ncbi.nlm.nih.gov/29034226/)
                """)

    # =========================================================================
    # BIOFEEDBACK TAB - Real-time HRV and Coherence Training
    # =========================================================================
    with tab_biofeedback:
        st.markdown("### 🫀 HRV Biofeedback & Coherence Training")
        st.markdown("*Real-time heart rate variability monitoring with paced breathing guidance*")
        
        with st.expander("📖 **Understanding HRV Biofeedback**", expanded=False):
            st.markdown("""
**What is HRV Biofeedback?**

HRV biofeedback is a technique that trains you to increase heart rate variability through 
controlled breathing, typically at your "resonance frequency" (~6 breaths/min for most adults).

| Concept | Description | Benefit |
|---------|-------------|---------|
| **Coherence** | Synchronization between heart rhythm and breathing | Reflects autonomic balance |
| **Resonance Frequency** | Breathing rate that maximizes HRV amplitude | Individual-specific (4-7 br/min) |
| **RSA** | Respiratory Sinus Arrhythmia | Natural HR increase on inhale |

**Scientific Evidence:**
- 10×20 min sessions significantly increase resting vmHRV [Appl Psychophysiol Biofeedback 2024]
- Effects strongest in those with higher baseline RMSSD
- Improves stress resilience and emotional regulation

**How to Use:**
1. Connect a heart rate monitor (or use simulation mode)
2. Set your target breathing rate (default: 6 breaths/min)
3. Follow the breathing guide while watching coherence score
4. Aim for 70%+ time in "high coherence" zone
            """)
        
        if not REALTIME_HRV_AVAILABLE:
            st.warning(
                "⚠️ Real-time HRV module not available. Install dependencies: `pip install bleak`"
            )
        else:
            st.markdown("---")
            
            # Session settings
            col_mode, col_settings = st.columns([1, 2])
            
            with col_mode:
                st.markdown("#### 🎯 Mode Selection")
                biofeedback_mode = st.radio(
                    "Data source",
                    options=["Simulation", "BLE Heart Rate Monitor"],
                    index=0,
                    key="biofeedback_mode",
                    help="Simulation mode generates realistic HRV data for testing"
                )
                
                if biofeedback_mode == "BLE Heart Rate Monitor":
                    st.info(
                        "🔵 Bluetooth support requires the `bleak` library and a compatible "
                        "heart rate monitor (Polar H10, etc.)"
                    )
            
            with col_settings:
                st.markdown("#### ⚙️ Session Settings")
                
                col_s1, col_s2, col_s3 = st.columns(3)
                
                with col_s1:
                    breathing_rate = st.slider(
                        "Breathing rate (br/min)",
                        min_value=4.0, max_value=10.0, value=6.0, step=0.5,
                        key="biofeedback_breathing_rate",
                        help="6 breaths/min is the typical resonance frequency"
                    )
                
                with col_s2:
                    session_duration = st.selectbox(
                        "Session duration",
                        options=[5, 10, 15, 20, 30],
                        index=1,
                        key="biofeedback_duration",
                        format_func=lambda x: f"{x} minutes"
                    )
                
                with col_s3:
                    inhale_ratio = st.slider(
                        "Inhale ratio",
                        min_value=0.3, max_value=0.5, value=0.4, step=0.05,
                        key="biofeedback_inhale_ratio",
                        help="Fraction of breath cycle for inhale"
                    )
            
            st.markdown("---")
            
            # Session control
            col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1, 1, 2])
            
            with col_ctrl1:
                start_session = st.button(
                    "▶️ Start Session",
                    type="primary",
                    key="start_biofeedback",
                    disabled="biofeedback_running" in st.session_state and st.session_state.get("biofeedback_running", False)
                )
            
            with col_ctrl2:
                stop_session = st.button(
                    "⏹️ Stop Session",
                    key="stop_biofeedback",
                    disabled="biofeedback_running" not in st.session_state or not st.session_state.get("biofeedback_running", False)
                )
            
            # Initialize session state
            if "biofeedback_engine" not in st.session_state:
                st.session_state["biofeedback_engine"] = RealtimeHRVEngine(window_size_sec=60)
                st.session_state["biofeedback_running"] = False
                st.session_state["biofeedback_coherence_history"] = []
                st.session_state["biofeedback_hrv_history"] = []
            
            engine = st.session_state["biofeedback_engine"]
            
            # Handle session start
            if start_session:
                st.session_state["biofeedback_running"] = True
                st.session_state["biofeedback_coherence_history"] = []
                st.session_state["biofeedback_hrv_history"] = []
                engine.clear_buffer()
                engine.start_session(
                    duration_sec=session_duration * 60,
                    breathing_rate=breathing_rate,
                )
                st.rerun()
            
            # Handle session stop
            if stop_session:
                st.session_state["biofeedback_running"] = False
                session_result = engine.end_session()
                if session_result:
                    st.session_state["biofeedback_last_session"] = session_result
                st.rerun()
            
            # Display area
            st.markdown("---")
            
            # NOTE: We removed @st.fragment(run_every=N) because it causes
            # "SessionInfo before initialized" errors when defined inside tabs.
            # Instead, we use a manual refresh button for the live view.
            def _render_biofeedback_live_view(
                engine_local: RealtimeHRVEngine,
                breathing_rate_local: float,
                session_duration_local: int,
                inhale_ratio_local: float,
                biofeedback_mode_local: str,
            ) -> None:
                """Render the live biofeedback view (called on each page render)."""
                # Defensive check: if biofeedback stopped, don't render.
                if not st.session_state.get("biofeedback_running", False):
                    return

                # Check if session should auto-stop (duration elapsed).
                current_session = engine_local.current_session
                if current_session is not None:
                    try:
                        elapsed_sec = (
                            datetime.now(timezone.utc) - current_session.start_time
                        ).total_seconds()
                    except Exception:
                        elapsed_sec = 0.0
                    try:
                        target_sec = float(current_session.target_duration_sec)
                    except Exception:
                        target_sec = float(session_duration_local * 60)

                    if elapsed_sec >= target_sec:
                        # Session complete - show message and set flag for handling.
                        st.session_state["biofeedback_session_needs_stop"] = True
                        st.success("✅ Session complete! Click 'Stop Session' to view summary.")
                        return

                    remaining_sec = max(0.0, target_sec - elapsed_sec)
                    st.caption(f"⏱️ Time remaining: {remaining_sec / 60:.1f} min")

                st.markdown("#### 🟢 Session Active")

                # Breathing guide visualization
                st.markdown("##### 🌬️ Breathing Guide")

                cycle_duration = 60.0 / breathing_rate_local
                inhale_duration = cycle_duration * inhale_ratio_local
                exhale_duration = cycle_duration * (1 - inhale_ratio_local)

                # Create breathing animation data
                import time as time_module

                current_time = time_module.time() % cycle_duration
                if current_time < inhale_duration:
                    phase = "INHALE"
                    progress = current_time / inhale_duration
                    color = "#28a745"
                else:
                    phase = "EXHALE"
                    progress = (current_time - inhale_duration) / exhale_duration
                    color = "#17a2b8"

                st.markdown(
                    f"""
                    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, {color}22 0%, {color}11 100%); 
                                border-radius: 15px; margin: 1rem 0;">
                        <h1 style="color: {color}; margin: 0; font-size: 3rem;">{phase}</h1>
                        <div style="width: 100%; height: 20px; background: #e0e0e0; border-radius: 10px; margin-top: 1rem;">
                            <div style="width: {progress * 100}%; height: 100%; background: {color}; border-radius: 10px; transition: width 0.1s;"></div>
                        </div>
                        <p style="margin-top: 1rem; font-size: 1.2rem;">Cycle: {inhale_duration:.1f}s in / {exhale_duration:.1f}s out</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Simulate data in simulation mode
                if biofeedback_mode_local == "Simulation":
                    import random
                    import numpy as np

                    for _ in range(3):  # Add a few samples
                        base_rr = 857  # ~70 bpm
                        rsa_amplitude = 50
                        rsa = rsa_amplitude * np.sin(
                            2 * np.pi * (breathing_rate_local / 60) * time_module.time()
                        )
                        noise = random.gauss(0, 15)
                        rr_ms = int(base_rr + rsa + noise)
                        engine_local.add_rr_sample(rr_ms)

                # Compute current HRV
                metrics = engine_local.compute_hrv()

                if metrics:
                    # Store in history (bounded growth)
                    if "biofeedback_coherence_history" not in st.session_state:
                        st.session_state["biofeedback_coherence_history"] = []
                    if "biofeedback_hrv_history" not in st.session_state:
                        st.session_state["biofeedback_hrv_history"] = []

                    st.session_state["biofeedback_coherence_history"].append(metrics.coherence)
                    st.session_state["biofeedback_hrv_history"].append(
                        {
                            "rmssd": metrics.rmssd,
                            "coherence": metrics.coherence,
                            "hr": metrics.mean_hr,
                        }
                    )
                    max_points = max(300, int(session_duration_local * 60) + 120)
                    if len(st.session_state["biofeedback_coherence_history"]) > max_points:
                        del st.session_state["biofeedback_coherence_history"][:-max_points]
                    if len(st.session_state["biofeedback_hrv_history"]) > max_points:
                        del st.session_state["biofeedback_hrv_history"][:-max_points]

                    # Display metrics
                    st.markdown("##### 📊 Real-time Metrics")
                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    with col_m1:
                        st.metric(
                            "Coherence",
                            f"{metrics.coherence:.0f}%",
                            help="Target: 70%+ for high coherence",
                        )
                    with col_m2:
                        st.metric(
                            "RMSSD",
                            f"{metrics.rmssd:.1f} ms",
                            help="Higher = better vagal tone",
                        )
                    with col_m3:
                        st.metric("Heart Rate", f"{metrics.mean_hr:.0f} bpm")
                    with col_m4:
                        st.metric(
                            "Resp Rate",
                            f"{metrics.respiratory_rate:.1f} br/min"
                            if metrics.respiratory_rate > 0
                            else "—",
                        )

                    # Coherence gauge
                    coherence_gauge = {
                        "series": [
                            {
                                "type": "gauge",
                                "startAngle": 180,
                                "endAngle": 0,
                                "min": 0,
                                "max": 100,
                                "splitNumber": 5,
                                "radius": "90%",
                                "center": ["50%", "70%"],
                                "axisLine": {
                                    "lineStyle": {
                                        "width": 20,
                                        "color": [
                                            [0.4, "#dc3545"],
                                            [0.7, "#ffc107"],
                                            [1, "#28a745"],
                                        ],
                                    }
                                },
                                "pointer": {"length": "60%", "width": 6},
                                "axisTick": {"show": False},
                                "splitLine": {"show": False},
                                "axisLabel": {"show": False},
                                "title": {
                                    "show": True,
                                    "offsetCenter": [0, "30%"],
                                    "fontSize": 14,
                                },
                                "detail": {
                                    "valueAnimation": True,
                                    "fontSize": 28,
                                    "offsetCenter": [0, "0%"],
                                    "formatter": "{value}%",
                                },
                                "data": [
                                    {
                                        "value": round(metrics.coherence),
                                        "name": "Coherence",
                                    }
                                ],
                            }
                        ]
                    }

                    render_echarts(
                        coherence_gauge,
                        height_px=250,
                        config=EChartsConfig(),
                    )

                    # Coherence history chart
                    if len(st.session_state["biofeedback_coherence_history"]) > 5:
                        history = st.session_state["biofeedback_coherence_history"][-60:]
                        history_chart = {
                            "xAxis": {
                                "type": "category",
                                "data": list(range(len(history))),
                            },
                            "yAxis": {
                                "type": "value",
                                "min": 0,
                                "max": 100,
                                "name": "Coherence %",
                            },
                            "series": [
                                {
                                    "type": "line",
                                    "data": history,
                                    "smooth": True,
                                    "areaStyle": {"opacity": 0.3},
                                    "markLine": {
                                        "data": [
                                            {
                                                "yAxis": 70,
                                                "name": "High",
                                                "lineStyle": {"color": "#28a745", "type": "dashed"},
                                            },
                                            {
                                                "yAxis": 40,
                                                "name": "Medium",
                                                "lineStyle": {"color": "#ffc107", "type": "dashed"},
                                            },
                                        ]
                                    },
                                }
                            ],
                            "visualMap": {
                                "show": False,
                                "pieces": [
                                    {"gt": 70, "lte": 100, "color": "#28a745"},
                                    {"gt": 40, "lte": 70, "color": "#ffc107"},
                                    {"gt": 0, "lte": 40, "color": "#dc3545"},
                                ],
                            },
                        }
                        render_echarts(
                            history_chart,
                            height_px=200,
                            config=EChartsConfig(),
                        )

            # Handle session auto-stop flag (set when duration elapses).
            if st.session_state.pop("biofeedback_session_needs_stop", False):
                st.session_state["biofeedback_running"] = False
                session_result = engine.end_session()
                if session_result:
                    st.session_state["biofeedback_last_session"] = session_result
                st.rerun()

            if st.session_state.get("biofeedback_running", False):
                # Add a refresh button for manual updates during the session.
                col_refresh, col_spacer = st.columns([1, 3])
                with col_refresh:
                    if st.button("🔄 Refresh", key="biofeedback_refresh", help="Update the live view"):
                        st.rerun()
                
                _render_biofeedback_live_view(
                    engine,
                    breathing_rate,
                    session_duration,
                    inhale_ratio,
                    biofeedback_mode,
                )
            
            else:
                # Show session summary if available
                if "biofeedback_last_session" in st.session_state:
                    session = st.session_state["biofeedback_last_session"]
                    
                    st.markdown("#### 📋 Last Session Summary")
                    
                    col_sum1, col_sum2, col_sum3 = st.columns(3)
                    
                    with col_sum1:
                        duration = (session.end_time - session.start_time).total_seconds() / 60
                        st.metric("Duration", f"{duration:.1f} min")
                    
                    with col_sum2:
                        st.metric("Achievement", f"{session.achievement_pct:.1f}%", help="Time in high coherence")
                    
                    with col_sum3:
                        st.metric("Total Beats", f"{len(session.rr_samples)}")
                    
                    if session.coherence_scores:
                        scores = [s[1] for s in session.coherence_scores]
                        
                        st.markdown("**Coherence Distribution:**")
                        high_pct = 100 * sum(1 for s in scores if s >= 70) / len(scores)
                        med_pct = 100 * sum(1 for s in scores if 40 <= s < 70) / len(scores)
                        low_pct = 100 * sum(1 for s in scores if s < 40) / len(scores)
                        
                        zone_chart = {
                            "tooltip": {"trigger": "item"},
                            "series": [{
                                "type": "pie",
                                "radius": ["40%", "70%"],
                                "data": [
                                    {"value": high_pct, "name": "High (≥70%)", "itemStyle": {"color": "#28a745"}},
                                    {"value": med_pct, "name": "Medium (40-69%)", "itemStyle": {"color": "#ffc107"}},
                                    {"value": low_pct, "name": "Low (<40%)", "itemStyle": {"color": "#dc3545"}},
                                ],
                                "label": {"formatter": "{b}: {d}%"}
                            }]
                        }
                        
                        render_echarts(
                            zone_chart,
                            height_px=250,
                            config=EChartsConfig()
                        )
                else:
                    st.info(
                        "👆 Click **Start Session** to begin HRV biofeedback training. "
                        "Follow the breathing guide and watch your coherence score increase!"
                    )
        
        st.caption(
            "**Scientific references:** Lehrer & Gevirtz (2014). Heart rate variability biofeedback. "
            "Front Public Health; Applied Psychophysiology & Biofeedback 2024."
        )

    # =========================================================================
    # FATIGUE TAB - SAFTE Model Integration
    # =========================================================================
    with tab_fatigue:
        st.markdown("### 🧠 SAFTE Fatigue & Performance Prediction")
        st.markdown("*Biomathematical model for cognitive performance and fatigue risk assessment*")
        st.markdown(
            "#### ✅ Guided workflow (recommended)\n"
            "1) **Sync context** (optional): Apply Circadian sleep window (bed/wake) + chronotype.\n"
            "2) **Confirm inputs**: Sleep window, sleep quality/duration, duty window, cognitive load.\n"
            "3) **Run SAFTE**: Manual scenario or Auto-run (wrist → clinical → Garmin → defaults).\n"
            "4) **Review FRMS**: WOCL exposure, time ≤77%, risk matrix, and USAF crew-rest compliance.\n"
            "5) **Export**: Download the forecast CSV + FRMS JSON evidence packet.\n"
        )
        
        if not FATIGUE_AVAILABLE:
            st.error(
                "⚠️ Fatigue module not available. Please ensure `fatigue_integration.py` "
                "and the `fatigue_calculator` package are properly installed."
            )
        else:
            tab_settings_manager = get_tab_settings_manager()
            cross_tab_broker = get_cross_tab_broker()
            fatigue_user_id = (
                active_user_context.get("user_id")
                if active_user_context.get("has_user")
                else None
            )
            stored_fatigue_settings = tab_settings_manager.get_settings(
                "fatigue", fatigue_user_id
            )

            fatigue_defaults = _sync_fatigue_widgets(active_user_context)
            # Only apply stored settings on first load (don't overwrite user changes)
            fatigue_settings_applied_key = f"_fatigue_settings_applied_{fatigue_user_id}"
            if stored_fatigue_settings and not st.session_state.get(fatigue_settings_applied_key):
                for skey, sval in stored_fatigue_settings.items():
                    if skey not in st.session_state:
                        st.session_state[skey] = sval
                fatigue_defaults.update(stored_fatigue_settings)
                st.session_state[fatigue_settings_applied_key] = True

            if fatigue_user_id and active_user_context.get("has_user") and not stored_fatigue_settings:
                prof_defaults = _cached_fatigue_profile_settings(str(fatigue_user_id))
                if prof_defaults:
                    updated_at = prof_defaults.get("updated_at")
                    label = f"Profile defaults loaded (updated {updated_at})" if updated_at else "Profile defaults loaded"
                    try:
                        bed_h = int(prof_defaults.get("typical_bedtime_hour", 23))
                        bed_lab = f"{max(0, min(23, bed_h)):02d}"
                    except Exception:
                        bed_lab = "—"
                    try:
                        wake_h = int(prof_defaults.get("typical_waketime_hour", 7))
                        wake_lab = f"{max(0, min(23, wake_h)):02d}"
                    except Exception:
                        wake_lab = "—"
                    try:
                        duty_s = int(prof_defaults.get("duty_start_hour", 9))
                        duty_s_lab = f"{max(0, min(23, duty_s)):02d}"
                    except Exception:
                        duty_s_lab = "—"
                    try:
                        duty_e = int(prof_defaults.get("duty_end_hour", 17))
                        duty_e_lab = f"{max(0, min(23, duty_e)):02d}"
                    except Exception:
                        duty_e_lab = "—"
                    st.info(
                        f"{label}: sleep {bed_lab}:00→{wake_lab}:00, duty {duty_s_lab}:00→{duty_e_lab}:00."
                    )

            # Optional: auto-fill sleep inputs from latest Garmin daily metrics.
            # Applies only when (a) a profile is active, (b) the user has not
            # explicitly saved fatigue settings for this tab, and (c) new Garmin
            # data arrives (one-shot per signature).
            auto_fill_garmin = st.checkbox(
                "Auto-fill sleep inputs from Garmin (when available)",
                value=True,
                key="fatigue_autofill_garmin",
                help="Uses the latest stored Garmin daily sleep metrics to seed sleep duration and quality once per new day.",
            )
            if fatigue_user_id and auto_fill_garmin and not stored_fatigue_settings:
                latest_garmin = _cached_latest_garmin_daily(fatigue_user_id)
                if latest_garmin:
                    sig = (
                        str(latest_garmin.get("metric_date") or ""),
                        str(latest_garmin.get("created_at") or ""),
                    )
                    prev_sig = tuple(st.session_state.get("fatigue_autofill_garmin_sig", ("", "")))
                    if sig != prev_sig:
                        updated_any = False
                        sleep_dur = latest_garmin.get("sleep_duration_hours")
                        if isinstance(sleep_dur, (int, float)) and np.isfinite(float(sleep_dur)):
                            new_dur = float(max(4.0, min(10.0, round(float(sleep_dur), 1))))
                            st.session_state["fatigue_sleep_duration"] = new_dur
                            fatigue_defaults["fatigue_sleep_duration"] = new_dur
                            new_debt = float(max(0.0, round(7.5 - new_dur, 1)))
                            st.session_state["fatigue_sleep_debt"] = new_debt
                            fatigue_defaults["fatigue_sleep_debt"] = new_debt
                            updated_any = True

                        quality_val: Optional[float] = None
                        eff = latest_garmin.get("sleep_efficiency")
                        if isinstance(eff, (int, float)) and np.isfinite(float(eff)):
                            eff_f = float(eff)
                            if eff_f > 1.2:
                                eff_f = eff_f / 100.0
                            quality_val = eff_f
                        score = latest_garmin.get("sleep_score")
                        if quality_val is None and isinstance(score, (int, float)) and np.isfinite(float(score)):
                            quality_val = float(score) / 100.0
                        if quality_val is not None and np.isfinite(float(quality_val)):
                            new_q = float(max(0.4, min(0.95, float(quality_val))))
                            st.session_state["fatigue_sleep_quality"] = new_q
                            fatigue_defaults["fatigue_sleep_quality"] = new_q
                            updated_any = True

                        if updated_any:
                            st.session_state["fatigue_autofill_garmin_sig"] = sig
                            date_label = str(latest_garmin.get("metric_date") or "latest day")
                            st.caption(f"Auto-filled fatigue sleep inputs from Garmin ({date_label}).")

                        # Seed bedtime/waketime when sleep timestamps are available
                        sleep_start_iso = latest_garmin.get("sleep_start_utc")
                        sleep_end_iso = latest_garmin.get("sleep_end_utc")
                        try:
                            start_dt = pd.to_datetime(sleep_start_iso, utc=True, errors="coerce")
                            end_dt = pd.to_datetime(sleep_end_iso, utc=True, errors="coerce")
                        except Exception:
                            start_dt = None
                            end_dt = None
                        if start_dt is not None and not pd.isna(start_dt):
                            if start_dt.tzinfo is None:
                                start_dt = start_dt.tz_localize(timezone.utc)
                            # Convert to Python datetime for astimezone() compatibility
                            local_start = start_dt.to_pydatetime().astimezone()
                            st.session_state["fatigue_bedtime"] = int(local_start.hour)
                            fatigue_defaults["fatigue_bedtime"] = int(local_start.hour)
                        if end_dt is not None and not pd.isna(end_dt):
                            if end_dt.tzinfo is None:
                                end_dt = end_dt.tz_localize(timezone.utc)
                            # Convert to Python datetime for astimezone() compatibility
                            local_end = end_dt.to_pydatetime().astimezone()
                            st.session_state["fatigue_waketime"] = int(local_end.hour)
                            fatigue_defaults["fatigue_waketime"] = int(local_end.hour)

            st.markdown("#### 🔄 Cross-tab correlation: Circadian ➜ Fatigue")
            circadian_entry = cross_tab_broker.get_latest("circadian", fatigue_user_id)
            # Extract payload from the entry structure (data is nested under "payload")
            circadian_context = circadian_entry.get("payload", {}) if circadian_entry else {}
            if circadian_context:
                sleep_window = circadian_context.get("sleep_window", {})
                bedtime_hour = int(
                    sleep_window.get("bedtime_hour", fatigue_defaults["fatigue_bedtime"])
                )
                waketime_hour = int(
                    sleep_window.get("waketime_hour", fatigue_defaults["fatigue_waketime"])
                )
                models = circadian_context.get("models") or []
                esri_info = circadian_context.get("esri", {})
                esri_mean = esri_info.get("mean")
                chronotype_offset = float(circadian_context.get("chronotype_offset", 0.0))
                
                # Display schedule type for context
                schedule_info = circadian_context.get("schedule", {})
                schedule_type = schedule_info.get("type", "Regular")

                col_ctx1, col_ctx2, col_ctx3, col_ctx4 = st.columns(4)
                with col_ctx1:
                    st.metric(
                        "Models",
                        ", ".join(models) if models else "—",
                        help="Latest circadian models executed in the Circadian tab",
                    )
                with col_ctx2:
                    st.metric(
                        "Sleep window",
                        f"{bedtime_hour:02d}:00 → {waketime_hour:02d}:00",
                        help=f"From Circadian tab ({schedule_type} schedule)",
                    )
                with col_ctx3:
                    st.metric(
                        "Chronotype Δ",
                        f"{chronotype_offset:+.1f} h",
                        help="Chronotype offset from active user profile",
                    )
                with col_ctx4:
                    st.metric(
                        "ESRI",
                        f"{esri_mean:.3f}" if esri_mean is not None else "—",
                        help="Entrainment Signal Regularity Index (run ESRI tab in Circadian to compute)",
                    )

                if st.button(
                    "Apply circadian window to fatigue inputs",
                    key="fatigue_apply_circadian_window",
                    type="secondary",
                    help="Uses the latest circadian scenario to seed bedtime/waketime and chronotype.",
                ):
                    st.session_state["fatigue_bedtime"] = bedtime_hour
                    st.session_state["fatigue_waketime"] = waketime_hour
                    st.session_state["fatigue_chronotype"] = chronotype_offset
                    st.success(
                        f"Fatigue inputs updated from Circadian tab: "
                        f"Bed {bedtime_hour:02d}:00, Wake {waketime_hour:02d}:00, Chrono {chronotype_offset:+.1f}h"
                    )
            else:
                st.caption(
                    "No circadian scenario shared yet. Run the Circadian tab (📈 Amplitude & Phase) to sync cues for fatigue planning."
                )
            # Scientific explanation expander
            with st.expander("📖 **Understanding the SAFTE Model**", expanded=False):
                st.markdown("""
**SAFTE (Sleep, Activity, Fatigue, and Task Effectiveness)** is a validated biomathematical model
that predicts cognitive performance based on:

| Component | Description | Impact on Performance |
|-----------|-------------|----------------------|
| **Homeostatic Process (S)** | Sleep pressure accumulation during wake | ↓ Performance as wake extends |
| **Circadian Process (C)** | 24h + 12h biological rhythms | Peak ~14:00-18:00, trough ~02:00-06:00 |
| **Sleep Inertia** | Post-sleep grogginess | ↓ 5-15% for 15-60 min after waking |
| **Sleep Debt** | Cumulative sleep deficit | ↓ 0.56% accuracy per hour of debt |

**Operational Effectiveness Zones (SAFTE/FAST-style):**
- 🟢 **Low risk (≥90%):** Well-rested baseline
- 🟡 **Caution (>77–<90%):** Transitional range; monitor fatigue and protect safety-critical tasks
- 🟠 **High risk (>70–≤77%):** Impairment often compared to ~0.05% BAC
- 🔴 **Severe (≤70%):** Impairment often compared to ~0.08% BAC

**Scientific References:**
- Hursh et al. (2004). Fatigue models for applied research. *Aviation, Space, and Environmental Medicine*
- Van Dongen et al. (2003). Cumulative cost of additional wakefulness. *Sleep*
- Borbély (1982). Two-process model of sleep regulation. *Human Neurobiology*
 - ICAO (2016). *Doc 9966: Manual for the Oversight of Fatigue Management Approaches*
                """)
            
            st.markdown("---")
            
            # Fatigue simulation settings in columns
            col_profile, col_sleep, col_work = st.columns(3)
            
            with col_profile:
                st.markdown("#### 👤 User Profile")
                fatigue_age = st.number_input(
                    "Age (years)",
                    min_value=16,
                    max_value=90,
                    value=int(fatigue_defaults["fatigue_age"]),
                    step=1,
                    key="fatigue_age",
                )
                sex_options = ["male", "female", "other"]
                default_sex = fatigue_defaults["fatigue_sex"]
                sex_index = (
                    sex_options.index(default_sex)
                    if default_sex in sex_options
                    else 2
                )
                fatigue_sex = st.selectbox(
                    "Sex",
                    options=sex_options,
                    index=sex_index,
                    key="fatigue_sex",
                )
                fatigue_chronotype = st.slider(
                    "Chronotype offset (hours)",
                    min_value=-2.5,
                    max_value=2.5,
                    value=float(fatigue_defaults["fatigue_chronotype"]),
                    step=0.5,
                    help="Negative = morning person, Positive = evening person",
                    key="fatigue_chronotype",
                )
            
            with col_sleep:
                st.markdown("#### 😴 Sleep Schedule")
                fatigue_sleep_quality = st.slider(
                    "Sleep quality (0-1)",
                    min_value=0.0,
                    max_value=1.0,
                    value=float(fatigue_defaults["fatigue_sleep_quality"]),
                    step=0.05,
                    key="fatigue_sleep_quality",
                )
                fatigue_sleep_duration = st.slider(
                    "Sleep duration (hours)",
                    min_value=4.0,
                    max_value=10.0,
                    value=float(fatigue_defaults["fatigue_sleep_duration"]),
                    step=0.5,
                    key="fatigue_sleep_duration",
                )
                fatigue_bedtime = st.slider(
                    "Bedtime (hour)",
                    min_value=0,
                    max_value=23,
                    value=int(fatigue_defaults["fatigue_bedtime"]),
                    key="fatigue_bedtime",
                )
                fatigue_waketime = st.slider(
                    "Wake time (hour)",
                    min_value=0,
                    max_value=23,
                    value=int(fatigue_defaults["fatigue_waketime"]),
                    key="fatigue_waketime",
                )
                fatigue_sleep_debt = st.slider(
                    "Current sleep debt (hours)",
                    min_value=0.0,
                    max_value=50.0,
                    value=float(fatigue_defaults["fatigue_sleep_debt"]),
                    step=0.5,
                    key="fatigue_sleep_debt",
                )
            
            with col_work:
                st.markdown("#### 💼 Work Schedule")
                fatigue_has_work = st.checkbox(
                    "Include work schedule",
                    value=bool(fatigue_defaults["fatigue_has_work"]),
                    key="fatigue_has_work",
                )
                fatigue_work_start = st.slider(
                    "Work start (hour)",
                    min_value=0,
                    max_value=23,
                    value=int(fatigue_defaults["fatigue_work_start"]),
                    disabled=not fatigue_has_work,
                    key="fatigue_work_start",
                )
                fatigue_work_end = st.slider(
                    "Work end (hour)",
                    min_value=0,
                    max_value=23,
                    value=int(fatigue_defaults["fatigue_work_end"]),
                    disabled=not fatigue_has_work,
                    key="fatigue_work_end",
                )
                fatigue_include_weekends = st.checkbox(
                    "Include weekends (Sat/Sun) as duty",
                    value=bool(fatigue_defaults.get("fatigue_include_weekends", False)),
                    disabled=not fatigue_has_work,
                    key="fatigue_include_weekends",
                    help="If unchecked, Saturday/Sunday are treated as off-duty for FRMS in-scope calculations.",
                )
                fatigue_cognitive_load = st.slider(
                    "Cognitive load (0-3)",
                    min_value=0,
                    max_value=3,
                    value=int(fatigue_defaults["fatigue_cognitive_load"]),
                    disabled=not fatigue_has_work,
                    help="0=low, 1=moderate, 2=high, 3=very high",
                    key="fatigue_cognitive_load",
                )
            
            # Simulation settings
            st.markdown("---")
            col_sim1, col_sim2, col_sim3 = st.columns([1, 1, 2])
            
            with col_sim1:
                fatigue_days = st.number_input(
                    "Prediction days",
                    min_value=1,
                    max_value=14,
                    value=int(fatigue_defaults["fatigue_days"]),
                    step=1,
                    key="fatigue_days",
                )
            
            with col_sim2:
                model_options = ["Advanced SAFTE", "Classic SAFTE"]
                model_default = fatigue_defaults["fatigue_model"]
                model_index = (
                    model_options.index(model_default)
                    if model_default in model_options
                    else 0
                )
                fatigue_model = st.selectbox(
                    "Model type",
                    options=model_options,
                    index=model_index,
                    key="fatigue_model",
                )
            
            with col_sim3:
                run_fatigue = st.button(
                    "🚀 Run Fatigue Prediction",
                    type="primary",
                    key="run_fatigue_btn"
                )
                auto_run_garmin = st.button(
                    "⌚ Auto-run (wrist/clinical/Garmin) (5-day forecast)",
                    type="secondary",
                    key="run_fatigue_garmin_btn",
                    help=(
                        "Runs a 5-day performance forecast with the active user profile, using "
                        "wrist monitoring history if available, then clinical sleep scales, then "
                        "Garmin Connect (GARMIN_EMAIL/GARMIN_PASSWORD) if configured."
                    ),
                )
                save_profile_defaults = st.button(
                    "💾 Save as profile defaults (SAFTE/FRMS)",
                    type="secondary",
                    key="fatigue_save_profile_defaults",
                    help="Stores these typical sleep/duty inputs in SQLite for one-click reuse in future SAFTE/FRMS runs.",
                )

            if save_profile_defaults:
                if not active_user_context.get("has_user") or not fatigue_user_id:
                    st.warning("Please select/log in a user profile before saving defaults.")
                else:
                    try:
                        db = get_database()
                        db.upsert_fatigue_profile_settings(
                            FatigueProfileSettings(
                                user_id=str(fatigue_user_id),
                                typical_sleep_duration_hours=float(fatigue_sleep_duration),
                                typical_sleep_quality=float(fatigue_sleep_quality),
                                typical_bedtime_hour=int(fatigue_bedtime),
                                typical_waketime_hour=int(fatigue_waketime),
                                duty_start_hour=int(fatigue_work_start),
                                duty_end_hour=int(fatigue_work_end),
                                include_weekends=bool(fatigue_include_weekends),
                                updated_at=datetime.now(timezone.utc).isoformat(),
                            )
                        )
                        try:
                            _cached_fatigue_profile_settings.clear()  # type: ignore[attr-defined]
                        except Exception:
                            pass
                        st.success("Saved SAFTE/FRMS defaults to the active profile.")
                    except Exception as exc:
                        st.error(f"Unable to save fatigue defaults: {exc}")
                        log_exception(_LOGGER, "Saving fatigue profile defaults failed", exc)

            current_fatigue_settings: Dict[str, Any] = {
                "fatigue_age": int(fatigue_age),
                "fatigue_sex": str(fatigue_sex),
                "fatigue_chronotype": float(fatigue_chronotype),
                "fatigue_sleep_quality": float(fatigue_sleep_quality),
                "fatigue_sleep_duration": float(fatigue_sleep_duration),
                "fatigue_bedtime": int(fatigue_bedtime),
                "fatigue_waketime": int(fatigue_waketime),
                "fatigue_sleep_debt": float(fatigue_sleep_debt),
                "fatigue_has_work": bool(fatigue_has_work),
                "fatigue_work_start": int(fatigue_work_start),
                "fatigue_work_end": int(fatigue_work_end),
                "fatigue_include_weekends": bool(fatigue_include_weekends),
                "fatigue_cognitive_load": int(fatigue_cognitive_load),
                "fatigue_days": int(fatigue_days),
                "fatigue_model": str(fatigue_model),
            }
            # Only save settings when user explicitly triggers an action (not on every rerun)
            if run_fatigue or auto_run_garmin or save_profile_defaults:
                tab_settings_manager.save_settings(
                    "fatigue",
                    fatigue_user_id,
                    current_fatigue_settings,
                    allowed_keys=_FATIGUE_SETTING_KEYS,
                )
            
            # Run simulation
            if run_fatigue:
                with st.spinner("Running SAFTE simulation..."):
                    try:
                        # Build inputs
                        user_profile = FatigueUserProfile(
                            age=int(fatigue_age),
                            sex=str(fatigue_sex),
                            chronotype_offset=float(fatigue_chronotype),
                            genetic_profile=tuple(),
                        )
                        
                        sleep_schedule = SleepScheduleInput(
                            quality=float(fatigue_sleep_quality),
                            duration=float(fatigue_sleep_duration),
                            bedtime=int(fatigue_bedtime),
                            waketime=int(fatigue_waketime),
                            total_sleep_debt=float(fatigue_sleep_debt),
                        )
                        
                        # Calculate work hours
                        if fatigue_has_work:
                            if fatigue_work_start <= fatigue_work_end:
                                work_hours = fatigue_work_end - fatigue_work_start
                            else:
                                work_hours = (24 - fatigue_work_start) + fatigue_work_end
                        else:
                            work_hours = 0
                        
                        work_schedule = WorkScheduleInput(
                            has_work=bool(fatigue_has_work),
                            work_start=int(fatigue_work_start),
                            work_end=int(fatigue_work_end),
                            work_hours=int(work_hours),
                            cognitive_load=int(fatigue_cognitive_load),
                        )
                        
                        # Run analysis
                        model_type = "classic" if "Classic" in fatigue_model else "advanced"
                        result = run_integrated_fatigue_analysis(
                            user_profile=user_profile,
                            sleep_schedule=sleep_schedule,
                            work_schedule=work_schedule,
                            prediction_days=int(fatigue_days),
                            model_type=model_type,
                        )
                        
                        # Store in session state
                        st.session_state["fatigue_result"] = result
                        st.session_state.pop("fatigue_assessment_df", None)
                        st.session_state.pop("fatigue_source_label", None)
                        st.success("✅ Fatigue prediction completed!")

                        cross_tab_broker.publish(
                            "fatigue",
                            fatigue_user_id,
                            "fatigue_prediction",
                            {
                                "analysis": dict(result.analysis),
                                "risk_assessment": dict(result.risk_assessment),
                                "recommendations": list(result.recommendations)[:3],
                                "model": model_type,
                                "prediction_days": int(fatigue_days),
                                "timestamp": pd.Timestamp.utcnow().isoformat(),
                            },
                            metadata={"source": "fatigue_tab"},
                        )
                        
                    except Exception as e:
                        st.error(f"Error running fatigue simulation: {e}")
                        _LOGGER.exception("Fatigue simulation failed")
            
            if auto_run_garmin:
                if not active_user_context.get("has_user"):
                    st.warning("Please select or log in a user to run auto fatigue forecast.")
                else:
                    # Mark that we're running to avoid double-runs
                    if st.session_state.get("_fatigue_auto_running"):
                        st.info("⏳ Auto-run already in progress...")
                    else:
                        st.session_state["_fatigue_auto_running"] = True
                        with st.spinner("Running auto fatigue forecast (wrist → clinical → Garmin)..."):
                            try:
                                auto_result, source_label, wrist_df = run_assessment_fatigue_prediction(
                                    user_context=active_user_context,
                                    user_id=active_user_context.get("user_id"),
                                    prediction_days=5,
                                    model_type="advanced",
                                )
                                st.session_state["fatigue_result"] = auto_result
                                st.session_state["fatigue_source_label"] = source_label
                                if wrist_df is not None and not wrist_df.empty:
                                    st.session_state["fatigue_assessment_df"] = wrist_df.sort_values(
                                        "metric_date", ascending=False
                                    ).head(5)
                                else:
                                    st.session_state.pop("fatigue_assessment_df", None)
                                st.success(
                                    f"✅ 5-day forecast completed using {source_label.replace('_', ' ')} data."
                                )
                            except Exception as exc:
                                st.error(f"Assessment-based fatigue automation failed: {exc}")
                                log_exception(_LOGGER, "Assessment-based fatigue automation failed", exc)
                            finally:
                                st.session_state.pop("_fatigue_auto_running", None)
            
            # Display results if available
            if "fatigue_result" in st.session_state:
                result = st.session_state["fatigue_result"]
                
                st.markdown("---")
                # Show data source if available (from auto-run)
                source_label = st.session_state.get("fatigue_source_label")
                if source_label:
                    source_display = source_label.replace("_", " ").title()
                    st.info(f"📊 **Data Source:** {source_display}")
                st.markdown("### 📊 Fatigue Prediction Results")
                
                # Build DataFrame for plotting
                df_fatigue = build_fatigue_dataframe(
                    result.time_points,
                    result.performances,
                    result.circadian_values,
                )
                
                # Performance chart using ECharts
                st.markdown("#### 📈 Cognitive Performance Prediction")
                
                # Prepare data for ECharts
                perf_data = df_fatigue[["DateTime", "Performance"]].dropna()
                if not perf_data.empty:
                    x_data = [dt.strftime("%Y-%m-%d %H:%M") for dt in perf_data["DateTime"]]
                    y_data = [round(float(p), 1) for p in perf_data["Performance"]]
                    
                    # Create ECharts config for performance chart
                    perf_chart_config = {
                        "tooltip": {
                            "trigger": "axis",
                            "formatter": "{b}<br/>Performance: {c}%"
                        },
                        "toolbox": {
                            "show": True,
                            "right": 10,
                            "feature": {
                                "saveAsImage": {
                                    "show": True,
                                    "title": "Save (PNG)",
                                    "pixelRatio": 4,
                                },
                                "restore": {"show": True, "title": "Reset"},
                                "dataZoom": {"show": True, "title": {"zoom": "Zoom", "back": "Reset zoom"}},
                            },
                        },
                        "xAxis": {
                            "type": "category",
                            "data": x_data,
                            "name": "Local time",
                            "nameLocation": "middle",
                            "nameGap": 35,
                            "axisLabel": {"rotate": 45, "fontSize": 10}
                        },
                        "yAxis": {
                            "type": "value",
                            "min": 0,
                            "max": 100,
                            "name": "Effectiveness (%)",
                            "axisLabel": {"formatter": "{value}%"}
                        },
                        "visualMap": {
                            "show": False,
                            "pieces": [
                                {"gte": 90, "lte": 100, "color": "#28a745"},
                                {"gt": 77, "lt": 90, "color": "#ffc107"},
                                {"gt": 70, "lte": 77, "color": "#fd7e14"},
                                {"lte": 70, "color": "#dc3545"},
                            ]
                        },
                        "series": [{
                            "type": "line",
                            "data": y_data,
                            "smooth": True,
                            "lineStyle": {"width": 3},
                            "areaStyle": {"opacity": 0.3},
                            "markLine": {
                                "data": [
                                    {"yAxis": 90, "name": "Low risk (≥90%)", "lineStyle": {"color": "#28a745", "type": "dashed"}},
                                    {"yAxis": 77, "name": "High risk (>70–≤77%)", "lineStyle": {"color": "#fd7e14", "type": "dashed"}},
                                    {"yAxis": 70, "name": "Severe (≤70%)", "lineStyle": {"color": "#dc3545", "type": "dashed"}},
                                ]
                            }
                        }],
                        "grid": {"left": "10%", "right": "5%", "bottom": "15%", "top": "10%"},
                        "dataZoom": [{"type": "inside"}, {"type": "slider"}]
                    }
                    
                    render_echarts(
                        perf_chart_config,
                        height_px=400,
                        config=EChartsConfig()
                    )
                    st.caption(
                        "This plot shows predicted SAFTE cognitive effectiveness (y-axis, %) over local time (x-axis). "
                        "Dashed lines mark common operational thresholds (90%, 77%, 70%) and colors indicate the "
                        "corresponding fatigue risk zone (green: ≥90%; yellow: >77–<90%; orange: >70–≤77%; red: ≤70%). "
                        "Note: exactly 90.0% is classified and colored as low risk (≥90%)."
                    )
                
                # Analysis metrics
                st.markdown("#### 📋 Performance Analysis")
                
                col_metrics1, col_metrics2, col_metrics3, col_metrics4 = st.columns(4)
                
                analysis = result.analysis
                with col_metrics1:
                    st.metric(
                        "Average Performance",
                        f"{analysis['avg']:.1f}%",
                        help="Mean cognitive effectiveness across prediction period"
                    )
                with col_metrics2:
                    st.metric(
                        "Minimum",
                        f"{analysis['min']:.1f}%",
                        help="Lowest predicted performance"
                    )
                with col_metrics3:
                    st.metric(
                        "Maximum",
                        f"{analysis['max']:.1f}%",
                        help="Highest predicted performance"
                    )
                with col_metrics4:
                    st.metric(
                        "Risk Score",
                        f"{analysis['risk']:.1f}%",
                        help="Percentage of time at/under 77% effectiveness (high-risk threshold)"
                    )
                
                source_label = st.session_state.get("fatigue_source_label")
                assessment_df = st.session_state.get("fatigue_assessment_df")
                if source_label is not None:
                    st.info(f"Source used for auto forecast: {source_label.replace('_', ' ')}")
                if assessment_df is not None and not assessment_df.empty:
                    st.markdown("#### ⌚ Latest wrist monitoring summary used")
                    display_cols = [
                        col
                        for col in assessment_df.columns
                        if col
                        in {
                            "metric_date",
                            "sleep_score",
                            "sleep_efficiency",
                            "sleep_duration_hours",
                            "avg_spo2",
                        }
                    ]
                    st.dataframe(
                        assessment_df[display_cols],
                        use_container_width=True,
                    )
                
                # Performance zone distribution
                st.markdown("#### 🎯 Performance Zone Distribution")
                
                zones = analysis["zones"]
                zone_labels = [
                    "Low risk (≥90%)",
                    "Caution (>77–<90%)",
                    "High risk (>70–≤77%)",
                    "Severe (≤70%)",
                ]
                zone_colors = ["#28a745", "#ffc107", "#fd7e14", "#dc3545"]
                
                # ECharts pie chart for zones
                zone_chart_config = {
                    "tooltip": {"trigger": "item", "formatter": "{b}: {c} hours ({d}%)"},
                    "legend": {"orient": "horizontal", "bottom": "0%"},
                    "toolbox": {
                        "show": True,
                        "right": 10,
                        "feature": {
                            "saveAsImage": {"show": True, "title": "Save (PNG)", "pixelRatio": 4},
                            "restore": {"show": True, "title": "Reset"},
                        },
                    },
                    "series": [{
                        "type": "pie",
                        "radius": ["40%", "70%"],
                        "avoidLabelOverlap": True,
                        "itemStyle": {"borderRadius": 10, "borderColor": "#fff", "borderWidth": 2},
                        "label": {"show": True, "formatter": "{b}: {c}h"},
                        "emphasis": {"label": {"show": True, "fontSize": 14, "fontWeight": "bold"}},
                        "data": [
                            {"value": zones[0], "name": zone_labels[0], "itemStyle": {"color": zone_colors[0]}},
                            {"value": zones[1], "name": zone_labels[1], "itemStyle": {"color": zone_colors[1]}},
                            {"value": zones[2], "name": zone_labels[2], "itemStyle": {"color": zone_colors[2]}},
                            {"value": zones[3], "name": zone_labels[3], "itemStyle": {"color": zone_colors[3]}},
                        ]
                    }]
                }
                
                render_echarts(
                    zone_chart_config,
                    height_px=350,
                    config=EChartsConfig()
                )
                st.caption(
                    "This distribution summarizes the number of predicted hours spent in each operational "
                    "effectiveness zone (≥90%, >77–<90%, >70–≤77%, ≤70%)."
                )
                
                # Risk assessment (heuristic)
                st.markdown("#### ⚠️ Quick Risk Factor Assessment (heuristic)")
                
                risk = result.risk_assessment
                risk_level = risk["risk_level"]
                total_risk = risk["total_risk"]
                
                # Risk level indicator
                risk_colors = {
                    "Very Low": "#28a745",
                    "Low": "#17a2b8",
                    "Moderate": "#ffc107",
                    "High": "#fd7e14",
                    "Critical": "#dc3545",
                }
                risk_color = risk_colors.get(risk_level, "#6c757d")
                
                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, {risk_color}22 0%, {risk_color}11 100%); 
                                padding: 1.5rem; border-radius: 10px; border-left: 5px solid {risk_color};
                                margin: 1rem 0;">
                        <h3 style="margin: 0; color: {risk_color};">Risk Level: {risk_level}</h3>
                        <p style="font-size: 2rem; margin: 0.5rem 0; font-weight: bold;">{total_risk:.1f}/100</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Risk factors breakdown
                factors = risk["factors"]
                risk_factor_data = [
                    {"Factor": "Sleep Debt", "Score": factors.get("sleep_debt", 0)},
                    {"Factor": "Sleep Quality", "Score": factors.get("sleep_quality", 0)},
                    {"Factor": "Circadian Misalignment", "Score": factors.get("circadian_misalignment", 0)},
                    {"Factor": "Work Hours", "Score": factors.get("work_hours", 0)},
                    {"Factor": "Cognitive Load", "Score": factors.get("cognitive_load", 0)},
                    {"Factor": "Age", "Score": factors.get("age", 0)},
                ]
                
                # ECharts bar chart for risk factors
                risk_bar_config = {
                    "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
                    "toolbox": {
                        "show": True,
                        "right": 10,
                        "feature": {
                            "saveAsImage": {"show": True, "title": "Save (PNG)", "pixelRatio": 4},
                            "restore": {"show": True, "title": "Reset"},
                        },
                    },
                    "xAxis": {"type": "value", "max": 25, "name": "Risk Score"},
                    "yAxis": {
                        "type": "category",
                        "data": [d["Factor"] for d in risk_factor_data],
                        "axisLabel": {"fontSize": 11}
                    },
                    "series": [{
                        "type": "bar",
                        "data": [
                            {
                                "value": round(d["Score"], 1),
                                "itemStyle": {
                                    "color": "#28a745" if d["Score"] < 5 else 
                                             "#ffc107" if d["Score"] < 10 else 
                                             "#fd7e14" if d["Score"] < 15 else "#dc3545"
                                }
                            }
                            for d in risk_factor_data
                        ],
                        "label": {"show": True, "position": "right", "formatter": "{c}"}
                    }],
                    "grid": {"left": "25%", "right": "15%", "top": "5%", "bottom": "5%"}
                }
                
                render_echarts(
                    risk_bar_config,
                    height_px=250,
                    config=EChartsConfig()
                )
                st.caption(
                    "This bar chart breaks down the heuristic risk-factor score used for quick triage "
                    "(sleep debt/quality, circadian misalignment, work hours/load, age)."
                )

                # -------------------------------------------------------------------------
                # FRMS dashboard (ICAO-aligned) + USAF crew rest checks
                # -------------------------------------------------------------------------
                st.markdown("#### 🛡️ FRMS Dashboard (ICAO-aligned)")
                st.caption(
                    "This section summarizes *predictive* fatigue risk using SAFTE effectiveness plus "
                    "FRMS-style exposure indicators (WOCL, time at/under high-risk thresholds) and a "
                    "conservative SMS-style risk matrix."
                )

                frms_exposure: Optional[FRMSExposureMetrics] = None
                frms_class: Optional[FRMSRiskClassification] = None
                cr_assessment: Optional[USAFCrewRestAssessment] = None
                frms_thresholds = FRMSThresholds() if FRMS_AVAILABLE else None

                if not FRMS_AVAILABLE:
                    st.info("FRMS helpers are unavailable in this environment.")
                else:
                    try:
                        dt_list = list(df_fatigue["DateTime"])
                        eff_list = [float(x) for x in df_fatigue["Performance"].astype(float).tolist()]

                        hours_per_sample = 1.0
                        if len(dt_list) >= 2:
                            try:
                                delta_sec = float((dt_list[1] - dt_list[0]).total_seconds())
                                if delta_sec > 0:
                                    hours_per_sample = max(1.0 / 60.0, min(24.0, delta_sec / 3600.0))
                            except Exception:
                                hours_per_sample = 1.0

                        wocl_mask = compute_wocl_mask(
                            dt_list,
                            wocl_start_hour=int(frms_thresholds.wocl_start_hour),
                            wocl_end_hour=int(frms_thresholds.wocl_end_hour),
                        )
                        duty_mask = compute_duty_mask(
                            dt_list,
                            has_work_schedule=bool(fatigue_has_work),
                            work_start_hour=int(fatigue_work_start),
                            work_end_hour=int(fatigue_work_end),
                            include_weekends=bool(fatigue_include_weekends),
                        )

                        frms_exposure = compute_frms_exposure_metrics(
                            datetimes=dt_list,
                            effectiveness=eff_list,
                            scope_mask=duty_mask,
                            wocl_mask=wocl_mask,
                            thresholds=frms_thresholds,
                            hours_per_sample=float(hours_per_sample),
                        )
                        frms_class = classify_frms_risk(frms_exposure, thresholds=frms_thresholds)
                    except Exception as exc:
                        st.error(f"Unable to compute FRMS dashboard metrics: {exc}")
                        log_exception(_LOGGER, "FRMS dashboard metrics failed", exc)

                if frms_exposure is not None and frms_class is not None:
                    frms_color_map = {
                        "Low": "#28a745",
                        "Medium": "#ffc107",
                        "High": "#fd7e14",
                        "Extreme": "#dc3545",
                        "Unknown": "#6c757d",
                    }
                    frms_risk_color = frms_color_map.get(frms_class.risk_level, "#6c757d")

                    st.markdown(
                        f"""
                        <div style="background: linear-gradient(135deg, {frms_risk_color}22 0%, {frms_risk_color}11 100%);
                                    padding: 1.25rem; border-radius: 10px; border-left: 5px solid {frms_risk_color};
                                    margin: 0.75rem 0;">
                            <h3 style="margin: 0; color: {frms_risk_color};">FRMS Risk Level: {frms_class.risk_level}</h3>
                            <p style="margin: 0.25rem 0 0 0;">Severity: <b>{frms_class.severity}</b> | Likelihood: <b>{frms_class.likelihood}</b></p>
                            <p style="margin: 0.25rem 0 0 0; color: #444;">{frms_class.rationale}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    col_frms_a, col_frms_b, col_frms_c, col_frms_d = st.columns(4)
                    with col_frms_a:
                        st.metric(
                            "Min effectiveness (in-scope)",
                            f"{frms_exposure.min_effectiveness:.1f}%"
                            if frms_exposure.min_effectiveness is not None
                            else "—",
                            help="Worst predicted SAFTE effectiveness during in-scope hours (duty if provided).",
                        )
                    with col_frms_b:
                        st.metric(
                            "Hours ≤77% (in-scope)",
                            f"{frms_exposure.hours_at_or_below_77:.1f} h",
                            help="High-risk threshold often compared to ~0.05% BAC impairment.",
                        )
                    with col_frms_c:
                        st.metric(
                            "Hours ≤70% (in-scope)",
                            f"{frms_exposure.hours_at_or_below_70:.1f} h",
                            help="Severe impairment threshold often compared to ~0.08% BAC impairment.",
                        )
                    with col_frms_d:
                        st.metric(
                            "WOCL exposure (in-scope)",
                            f"{frms_exposure.pct_hours_in_wocl:.1f}%",
                            help="Percent of in-scope time during the Window of Circadian Low (~02:00–06:00 local).",
                        )

                    # Critical Job Time Input (shared by ICAO and USAF matrices)
                    st.markdown("#### ⏰ Critical Job Window")
                    st.caption(
                        "Enter the scheduled time for safety-critical tasks. Both ICAO and USAF risk matrices "
                        "will evaluate effectiveness during this window."
                    )
                    
                    col_job_date, col_job_time, col_job_dur = st.columns(3)
                    with col_job_date:
                        critical_job_date = st.date_input(
                            "Critical job date",
                            value=date.today(),
                            key="frms_critical_job_date",
                        )
                    with col_job_time:
                        critical_job_time = st.time_input(
                            "Critical job start time (local)",
                            value=dt_time(8, 0),
                            key="frms_critical_job_time",
                        )
                    with col_job_dur:
                        critical_job_duration = st.number_input(
                            "Duration (hours)",
                            min_value=0.5,
                            max_value=24.0,
                            value=4.0,
                            step=0.5,
                            key="frms_critical_job_duration",
                        )
                    
                    # Calculate effectiveness at critical job time from SAFTE curve
                    critical_job_start_dt = datetime.combine(critical_job_date, critical_job_time)
                    critical_job_end_dt = critical_job_start_dt + timedelta(hours=float(critical_job_duration))
                    
                    # Find effectiveness values during critical job window
                    job_effectiveness_values: list[float] = []
                    job_in_wocl_count = 0
                    if dt_list and eff_list:
                        for i, dt_val in enumerate(dt_list):
                            if critical_job_start_dt <= dt_val <= critical_job_end_dt:
                                job_effectiveness_values.append(eff_list[i])
                                # Check if in WOCL (02:00-06:00)
                                if 2 <= dt_val.hour < 6:
                                    job_in_wocl_count += 1
                    
                    if job_effectiveness_values:
                        job_min_eff = min(job_effectiveness_values)
                        job_mean_eff = sum(job_effectiveness_values) / len(job_effectiveness_values)
                        job_pct_below_77 = 100.0 * sum(1 for e in job_effectiveness_values if e <= 77) / len(job_effectiveness_values)
                        job_pct_in_wocl = 100.0 * job_in_wocl_count / len(job_effectiveness_values)
                    else:
                        # Fallback to overall metrics if no points in window
                        job_min_eff = frms_exposure.min_effectiveness or 70.0
                        job_mean_eff = frms_exposure.mean_effectiveness or 75.0
                        job_pct_below_77 = frms_exposure.pct_hours_at_or_below_77
                        job_pct_in_wocl = frms_exposure.pct_hours_in_wocl
                    
                    # Display critical job metrics
                    col_job_a, col_job_b, col_job_c, col_job_d = st.columns(4)
                    with col_job_a:
                        st.metric(
                            "Min Effectiveness",
                            f"{job_min_eff:.0f}%",
                            help="Minimum predicted effectiveness during critical job window.",
                        )
                    with col_job_b:
                        st.metric(
                            "Mean Effectiveness",
                            f"{job_mean_eff:.0f}%",
                            help="Average predicted effectiveness during critical job window.",
                        )
                    with col_job_c:
                        st.metric(
                            "Time ≤77%",
                            f"{job_pct_below_77:.0f}%",
                            help="Percent of critical job window with effectiveness ≤77%.",
                        )
                    with col_job_d:
                        st.metric(
                            "WOCL Exposure",
                            f"{job_pct_in_wocl:.0f}%",
                            help="Percent of critical job window in Window of Circadian Low (02:00-06:00).",
                        )

                    # ══════════════════════════════════════════════════════════════════════════════
                    # ICAO Doc 9859 Safety Management Manual - Risk Matrix Definitions
                    # Reference: https://store.icao.int/en/safety-management-manual-doc-9859
                    # ══════════════════════════════════════════════════════════════════════════════
                    
                    # ICAO probability levels (Doc 9859, Table 2-12)
                    icao_likelihood_order = [
                        "Extremely Improbable",  # Almost inconceivable
                        "Improbable",            # Very unlikely to occur
                        "Remote",                # Unlikely but possible
                        "Occasional",            # Likely to occur sometimes
                        "Frequent",              # Likely to occur many times
                    ]
                    
                    # ICAO severity levels (Doc 9859, Table 2-11)
                    icao_severity_order = ["Negligible", "Minor", "Major", "Hazardous", "Catastrophic"]
                    
                    # Risk tolerability: Acceptable, Tolerable (review required), Intolerable
                    icao_risk_value_map = {"Acceptable": 1, "Tolerable": 2, "Undesirable": 3, "Intolerable": 4}
                    
                    # ICAO severity based on min effectiveness during critical job
                    def icao_severity_from_effectiveness(eff: float) -> str:
                        """Map SAFTE effectiveness to ICAO severity per Doc 9859."""
                        if eff >= 85:
                            return "Negligible"  # E: Few consequences
                        elif eff >= 77:
                            return "Minor"       # D: Operating limitations, minor incident
                        elif eff >= 70:
                            return "Major"       # C: Significant reduction in safety margins
                        elif eff >= 60:
                            return "Hazardous"   # B: Large reduction in safety margins
                        else:
                            return "Catastrophic"  # A: Equipment destroyed, multiple deaths
                    
                    # ICAO likelihood based on % time below 77% during critical job
                    def icao_likelihood_from_exposure(pct_below_77: float) -> str:
                        """Map degraded effectiveness exposure to ICAO probability per Doc 9859."""
                        if pct_below_77 >= 50:
                            return "Frequent"              # 5: Likely to occur many times
                        elif pct_below_77 >= 30:
                            return "Occasional"            # 4: Likely to occur sometimes
                        elif pct_below_77 >= 15:
                            return "Remote"                # 3: Unlikely but possible
                        elif pct_below_77 >= 5:
                            return "Improbable"            # 2: Very unlikely to occur
                        else:
                            return "Extremely Improbable"  # 1: Almost inconceivable
                    
                    icao_sev = icao_severity_from_effectiveness(job_min_eff)
                    icao_lik = icao_likelihood_from_exposure(job_pct_below_77)
                    
                    # ICAO SMS matrix (Doc 9859, Table 2-13 adapted)
                    # Rows: Severity, Columns: Probability (Extremely Improbable → Frequent)
                    icao_sms_matrix = {
                        "Negligible":   ["Acceptable", "Acceptable", "Acceptable", "Tolerable", "Tolerable"],
                        "Minor":        ["Acceptable", "Acceptable", "Tolerable", "Undesirable", "Undesirable"],
                        "Major":        ["Acceptable", "Tolerable", "Undesirable", "Undesirable", "Intolerable"],
                        "Hazardous":    ["Tolerable", "Undesirable", "Undesirable", "Intolerable", "Intolerable"],
                        "Catastrophic": ["Undesirable", "Undesirable", "Intolerable", "Intolerable", "Intolerable"],
                    }
                    icao_heatmap_data: list[list[int]] = []
                    for y_idx, sev in enumerate(icao_severity_order):
                        row = icao_sms_matrix.get(sev, ["Acceptable"] * 5)
                        for x_idx, rlab in enumerate(row):
                            icao_heatmap_data.append([x_idx, y_idx, int(icao_risk_value_map.get(rlab, 1))])

                    try:
                        icao_sel_x = icao_likelihood_order.index(icao_lik)
                        icao_sel_y = icao_severity_order.index(icao_sev)
                        icao_risk_level = icao_sms_matrix[icao_sev][icao_sel_x]
                    except (ValueError, KeyError):
                        icao_sel_x, icao_sel_y = 0, 0
                        icao_risk_level = "Acceptable"

                    # ICAO Risk Matrix
                    st.markdown("#### 🌍 ICAO FRMS Risk Matrix (Doc 9859)")
                    icao_risk_color = {
                        "Acceptable": "#28a745",
                        "Tolerable": "#ffc107",
                        "Undesirable": "#fd7e14",
                        "Intolerable": "#dc3545",
                    }.get(icao_risk_level, "#6c757d")
                    st.markdown(
                        f"**ICAO Risk Level:** <span style='color:{icao_risk_color};font-weight:700;'>{icao_risk_level}</span> "
                        f"(Severity: {icao_sev}, Probability: {icao_lik})",
                        unsafe_allow_html=True,
                    )
                    
                    icao_risk_matrix_config = {
                        "tooltip": {
                            "position": "top",
                            "formatter": "Risk: {c} (1=Acceptable, 2=Tolerable, 3=Undesirable, 4=Intolerable)",
                        },
                        "toolbox": {
                            "show": True,
                            "right": 10,
                            "feature": {
                                "saveAsImage": {"show": True, "title": "Save (PNG)", "pixelRatio": 4},
                                "restore": {"show": True, "title": "Reset"},
                            },
                        },
                        "grid": {"left": "22%", "right": "8%", "top": "8%", "bottom": "32%"},
                        "xAxis": {
                            "type": "category",
                            "data": icao_likelihood_order,
                            "name": "Probability (ICAO Doc 9859)",
                            "nameLocation": "middle",
                            "nameGap": 55,
                            "axisLabel": {"rotate": 20, "fontSize": 9, "interval": 0},
                        },
                        "yAxis": {
                            "type": "category",
                            "data": icao_severity_order,
                            "name": "Severity",
                            "axisLabel": {"fontSize": 10},
                        },
                        "visualMap": {
                            "type": "piecewise",
                            "orient": "horizontal",
                            "left": "center",
                            "bottom": 5,
                            "itemGap": 12,
                            "textStyle": {"fontSize": 10},
                            "pieces": [
                                {"value": 1, "label": "Acceptable", "color": "#28a745"},
                                {"value": 2, "label": "Tolerable", "color": "#ffc107"},
                                {"value": 3, "label": "Undesirable", "color": "#fd7e14"},
                                {"value": 4, "label": "Intolerable", "color": "#dc3545"},
                            ],
                        },
                        "series": [
                            {
                                "name": "ICAO risk matrix",
                                "type": "heatmap",
                                "data": icao_heatmap_data,
                                "label": {"show": False},
                                "emphasis": {
                                    "itemStyle": {
                                        "shadowBlur": 10,
                                        "shadowColor": "rgba(0,0,0,0.35)",
                                    }
                                },
                            },
                            {
                                "name": "Current classification",
                                "type": "scatter",
                                "data": [[icao_sel_x, icao_sel_y, 5]],
                                "symbolSize": 26,
                                "itemStyle": {
                                    "color": "rgba(0,0,0,0)",
                                    "borderColor": "#111",
                                    "borderWidth": 3,
                                },
                                "tooltip": {"show": False},
                            },
                        ],
                    }
                    render_echarts(icao_risk_matrix_config, height_px=400, config=EChartsConfig())
                    
                    # ICAO probability definitions with reference
                    st.markdown(
                        f"""
                        <div style="font-size:0.85em; color:#555; margin-top:8px;">
                        <strong>ICAO Doc 9859 Probability Definitions:</strong><br>
                        • <b>Extremely Improbable</b> (<5%): Almost inconceivable the event will occur<br>
                        • <b>Improbable</b> (5–15%): Very unlikely to occur; not known to have occurred<br>
                        • <b>Remote</b> (15–30%): Unlikely but possible; has occurred rarely<br>
                        • <b>Occasional</b> (30–50%): Likely to occur sometimes; has occurred infrequently<br>
                        • <b>Frequent</b> (>50%): Likely to occur many times; has occurred frequently<br>
                        <a href="https://store.icao.int/en/safety-management-manual-doc-9859" target="_blank" style="color:#0066cc;">
                        📄 ICAO Doc 9859 Safety Management Manual</a>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # ══════════════════════════════════════════════════════════════════════════════
                    # USAF/DoD MIL-STD-882E Risk Matrix Definitions
                    # Reference: https://safety.army.mil/Portals/0/Documents/ON-DUTY/SYSTEMSAFETY/Standard/MIL-STD-882E-change-1.pdf
                    # USAF FRMS: https://www.usafe.af.mil/News/Article-Display/Article/809251/fatigue-risk-management-system-what-its-all-about
                    # ══════════════════════════════════════════════════════════════════════════════
                    
                    st.markdown("#### 🇺🇸 USAF/DoD FRMS Risk Matrix (MIL-STD-882E)")
                    
                    # MIL-STD-882E probability levels (Table II)
                    usaf_likelihood_order = [
                        "Improbable",   # E: So unlikely, can be assumed not to occur
                        "Remote",       # D: Unlikely, but possible to occur
                        "Occasional",   # C: Likely to occur sometime in life of item
                        "Probable",     # B: Will occur several times
                        "Frequent",     # A: Likely to occur often
                    ]
                    
                    # MIL-STD-882E severity categories (Table I)
                    usaf_severity_order = ["Negligible", "Marginal", "Critical", "Catastrophic"]
                    
                    # MIL-STD-882E risk levels (Table III)
                    usaf_risk_value_map = {"Low": 1, "Medium": 2, "Serious": 3, "High": 4}
                    
                    # USAF effectiveness-based severity (stricter thresholds per SAFTE guidance)
                    # USAF targets 70% minimum effectiveness (AvORM guidance)
                    def usaf_severity_from_effectiveness(eff: float) -> str:
                        """Map SAFTE effectiveness to MIL-STD-882E severity."""
                        if eff >= 90:
                            return "Negligible"   # IV: Less than minor injury/damage
                        elif eff >= 77:
                            return "Marginal"     # III: Minor injury, minor damage
                        elif eff >= 70:
                            return "Critical"     # II: Severe injury, major damage
                        else:
                            return "Catastrophic" # I: Death, system loss
                    
                    # USAF likelihood based on sleep debt, WOCL, and effectiveness exposure
                    sleep_debt_hrs = max(0.0, 8.0 - float(fatigue_sleep_duration))
                    in_wocl = 2 <= critical_job_time.hour < 6
                    
                    def usaf_likelihood_from_factors(sleep_debt: float, wocl: bool, pct_below_77: float) -> str:
                        """Map fatigue factors to MIL-STD-882E probability per Table II."""
                        risk_score = 0
                        # Sleep debt contribution
                        if sleep_debt >= 4:
                            risk_score += 3  # Severe cumulative fatigue
                        elif sleep_debt >= 2:
                            risk_score += 2  # Moderate cumulative fatigue
                        elif sleep_debt >= 1:
                            risk_score += 1  # Mild sleep restriction
                        # WOCL contribution (circadian low)
                        if wocl:
                            risk_score += 2  # Operating during biological low
                        # Effectiveness exposure contribution
                        if pct_below_77 >= 30:
                            risk_score += 2  # Significant degraded time
                        elif pct_below_77 >= 15:
                            risk_score += 1  # Some degraded time
                        
                        # Map to MIL-STD-882E probability levels
                        if risk_score >= 5:
                            return "Frequent"    # A: Likely to occur often
                        elif risk_score >= 4:
                            return "Probable"    # B: Will occur several times
                        elif risk_score >= 2:
                            return "Occasional"  # C: Likely to occur sometime
                        elif risk_score >= 1:
                            return "Remote"      # D: Unlikely, but possible
                        else:
                            return "Improbable"  # E: So unlikely, assumed not to occur
                    
                    usaf_sev = usaf_severity_from_effectiveness(job_min_eff)
                    usaf_lik = usaf_likelihood_from_factors(
                        sleep_debt_hrs, in_wocl, job_pct_below_77
                    )
                    
                    # MIL-STD-882E Risk Assessment Matrix (Table III)
                    # Rows: Severity (Negligible → Catastrophic)
                    # Columns: Probability (Improbable → Frequent)
                    usaf_sms_matrix = {
                        "Negligible":   ["Low", "Low", "Low", "Low", "Medium"],
                        "Marginal":     ["Low", "Low", "Medium", "Medium", "Serious"],
                        "Critical":     ["Low", "Medium", "Medium", "Serious", "High"],
                        "Catastrophic": ["Medium", "Medium", "Serious", "High", "High"],
                    }
                    
                    try:
                        usaf_sel_x = usaf_likelihood_order.index(usaf_lik)
                        usaf_sel_y = usaf_severity_order.index(usaf_sev)
                        usaf_risk_level = usaf_sms_matrix[usaf_sev][usaf_sel_x]
                    except (ValueError, KeyError):
                        usaf_sel_x, usaf_sel_y = 0, 0
                        usaf_risk_level = "Low"
                    
                    # Build USAF heatmap data
                    usaf_heatmap_data: list[list[int]] = []
                    for y_idx, sev in enumerate(usaf_severity_order):
                        row = usaf_sms_matrix.get(sev, ["Low"] * 5)
                        for x_idx, rlab in enumerate(row):
                            usaf_heatmap_data.append([x_idx, y_idx, int(usaf_risk_value_map.get(rlab, 1))])
                    
                    # Display USAF-specific metrics
                    usaf_risk_color = {
                        "Low": "#28a745",
                        "Medium": "#ffc107",
                        "Serious": "#fd7e14",
                        "High": "#dc3545",
                    }.get(usaf_risk_level, "#6c757d")
                    col_usaf_a, col_usaf_b = st.columns(2)
                    with col_usaf_a:
                        st.markdown(
                            f"**USAF Risk Level:** <span style='color:{usaf_risk_color};font-weight:700;'>{usaf_risk_level}</span> "
                            f"(Severity: {usaf_sev}, Probability: {usaf_lik})",
                            unsafe_allow_html=True,
                        )
                    with col_usaf_b:
                        st.metric(
                            "Sleep Debt",
                            f"{sleep_debt_hrs:.1f}h",
                            help="Estimated sleep debt (8h baseline - actual sleep).",
                        )
                    
                    usaf_risk_matrix_config = {
                        "tooltip": {
                            "position": "top",
                            "formatter": "Risk: {c} (1=Low, 2=Medium, 3=Serious, 4=High)",
                        },
                        "toolbox": {
                            "show": True,
                            "right": 10,
                            "feature": {
                                "saveAsImage": {"show": True, "title": "Save (PNG)", "pixelRatio": 4},
                                "restore": {"show": True, "title": "Reset"},
                            },
                        },
                        "grid": {"left": "18%", "right": "8%", "top": "8%", "bottom": "32%"},
                        "xAxis": {
                            "type": "category",
                            "data": usaf_likelihood_order,
                            "name": "Probability (MIL-STD-882E)",
                            "nameLocation": "middle",
                            "nameGap": 50,
                            "axisLabel": {"rotate": 0, "fontSize": 10, "interval": 0},
                        },
                        "yAxis": {
                            "type": "category",
                            "data": usaf_severity_order,
                            "name": "Severity",
                            "axisLabel": {"fontSize": 10},
                        },
                        "visualMap": {
                            "type": "piecewise",
                            "orient": "horizontal",
                            "left": "center",
                            "bottom": 5,
                            "itemGap": 18,
                            "textStyle": {"fontSize": 10},
                            "pieces": [
                                {"value": 1, "label": "Low", "color": "#28a745"},
                                {"value": 2, "label": "Medium", "color": "#ffc107"},
                                {"value": 3, "label": "Serious", "color": "#fd7e14"},
                                {"value": 4, "label": "High", "color": "#dc3545"},
                            ],
                        },
                        "series": [
                            {
                                "name": "USAF FRMS risk matrix",
                                "type": "heatmap",
                                "data": usaf_heatmap_data,
                                "label": {"show": False},
                                "emphasis": {
                                    "itemStyle": {
                                        "shadowBlur": 10,
                                        "shadowColor": "rgba(0,0,0,0.35)",
                                    }
                                },
                            },
                            {
                                "name": "Current classification",
                                "type": "scatter",
                                "data": [[usaf_sel_x, usaf_sel_y, 5]],
                                "symbolSize": 26,
                                "itemStyle": {
                                    "color": "rgba(0,0,0,0)",
                                    "borderColor": "#111",
                                    "borderWidth": 3,
                                },
                                "tooltip": {"show": False},
                            },
                        ],
                    }
                    render_echarts(usaf_risk_matrix_config, height_px=400, config=EChartsConfig())
                    
                    # MIL-STD-882E probability definitions with references
                    st.markdown(
                        f"""
                        <div style="font-size:0.85em; color:#555; margin-top:8px;">
                        <strong>MIL-STD-882E Probability Definitions (Table II):</strong><br>
                        • <b>Improbable</b> (E): So unlikely, can be assumed occurrence may not be experienced<br>
                        • <b>Remote</b> (D): Unlikely, but possible to occur in the life of an item<br>
                        • <b>Occasional</b> (C): Likely to occur sometime in the life of an item<br>
                        • <b>Probable</b> (B): Will occur several times in the life of an item<br>
                        • <b>Frequent</b> (A): Likely to occur often in the life of an item<br>
                        <a href="https://safety.army.mil/Portals/0/Documents/ON-DUTY/SYSTEMSAFETY/Standard/MIL-STD-882E-change-1.pdf" target="_blank" style="color:#0066cc;">
                        📄 MIL-STD-882E Standard Practice for System Safety</a> |
                        <a href="https://www.usafe.af.mil/News/Article-Display/Article/809251/fatigue-risk-management-system-what-its-all-about" target="_blank" style="color:#0066cc;">
                        📄 USAF FRMS Overview</a> |
                        <a href="https://corescholar.libraries.wright.edu/cgi/viewcontent.cgi?article=1000&context=isap_2017" target="_blank" style="color:#0066cc;">
                        📄 SAFTE in USAF AvORM</a>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # USAF crew rest checker (AFMAN 11-202V3)
                    st.markdown("#### ✈️ USAF Crew Rest Check (AFMAN 11-202V3)")
                    st.caption(
                        "Crew rest is typically **≥12 hours non-duty** before FDP with **≥8 hours uninterrupted sleep opportunity**. "
                        "Any official interruption resets crew rest; set the start time below to the *true* crew rest start."
                    )

                    col_cr_1, col_cr_2, col_cr_3 = st.columns(3)
                    with col_cr_1:
                        cr_start_date = st.date_input(
                            "Crew rest start (local date)",
                            value=date.today(),
                            key="usaf_crew_rest_start_date",
                        )
                        cr_start_time = st.time_input(
                            "Crew rest start (local time)",
                            value=dt_time(20, 0),
                            key="usaf_crew_rest_start_time",
                        )
                    with col_cr_2:
                        fdp_start_date = st.date_input(
                            "FDP start (local date)",
                            value=date.today() + timedelta(days=1),
                            key="usaf_fdp_start_date",
                        )
                        fdp_start_time = st.time_input(
                            "FDP start (local time)",
                            value=dt_time(8, 0),
                            key="usaf_fdp_start_time",
                        )
                    with col_cr_3:
                        continuous_ops = st.checkbox(
                            "Continuous ops (allow reduced crew rest ≥10h)",
                            value=False,
                            key="usaf_continuous_ops",
                            help="Use only when the operational continuous-ops condition applies per AFMAN 11-202V3.",
                        )
                        planned_sleep_opp = st.number_input(
                            "Planned uninterrupted sleep opportunity (hours)",
                            min_value=0.0,
                            max_value=14.0,
                            value=float(fatigue_sleep_duration),
                            step=0.25,
                            key="usaf_sleep_opportunity_hours",
                        )

                    crew_rest_start_dt = datetime.combine(cr_start_date, cr_start_time)
                    fdp_start_dt = datetime.combine(fdp_start_date, fdp_start_time)
                    try:
                        cr_assessment = assess_usaf_crew_rest(
                            crew_rest_start_local=crew_rest_start_dt,
                            fdp_start_local=fdp_start_dt,
                            planned_sleep_opportunity_hours=float(planned_sleep_opp),
                            continuous_ops_reduced_rest=bool(continuous_ops),
                            policy=USAFCrewRestPolicy(),
                        )
                        cr_color = "#28a745" if cr_assessment.compliant else "#dc3545"
                        st.markdown(
                            f"""
                            <div style="background: linear-gradient(135deg, {cr_color}22 0%, {cr_color}11 100%);
                                        padding: 1.1rem; border-radius: 10px; border-left: 5px solid {cr_color};
                                        margin: 0.75rem 0;">
                                <h4 style="margin: 0; color: {cr_color};">Crew Rest: {"COMPLIANT" if cr_assessment.compliant else "NOT COMPLIANT"}</h4>
                                <p style="margin: 0.25rem 0 0 0;">
                                    Crew rest: <b>{cr_assessment.crew_rest_hours:.1f}h</b> (required ≥{cr_assessment.required_crew_rest_hours:.1f}h) |
                                    Sleep opportunity: <b>{cr_assessment.planned_sleep_opportunity_hours:.1f}h</b> (required ≥{cr_assessment.required_sleep_opportunity_hours:.1f}h)
                                </p>
                                <p style="margin: 0.25rem 0 0 0; color: #444;">{cr_assessment.notes}</p>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    except Exception as exc:
                        st.warning(f"Unable to assess crew rest with provided times: {exc}")

                # Rule-based alerts (FRMS "why it triggered")
                if (
                    FRMS_AVAILABLE
                    and frms_exposure is not None
                    and frms_class is not None
                    and frms_thresholds is not None
                ):
                    try:
                        alerts: list[FRMSAlert] = compute_frms_alerts(
                            exposure=frms_exposure,
                            classification=frms_class,
                            crew_rest=cr_assessment,
                            thresholds=frms_thresholds,
                        )
                    except Exception as exc:
                        alerts = []
                        log_exception(_LOGGER, "FRMS alerts computation failed", exc)
                    if alerts:
                        st.markdown("#### 🚨 FRMS Alerts (Rule-Based Triggers)")
                        
                        # Group alerts by level for organized display
                        critical_alerts = [a for a in alerts if a.level == "critical"]
                        warning_alerts = [a for a in alerts if a.level == "warning"]
                        info_alerts = [a for a in alerts if a.level not in ("critical", "warning")]
                        
                        # Light theme alert styling
                        alert_styles = {
                            "critical": {
                                "bg": "#fff5f5",
                                "border": "#e53e3e",
                                "icon": "🚨",
                                "label": "CRITICAL",
                                "label_bg": "#e53e3e",
                                "text_color": "#c53030",
                            },
                            "warning": {
                                "bg": "#fffaf0",
                                "border": "#dd6b20",
                                "icon": "⚠️",
                                "label": "CAUTION",
                                "label_bg": "#dd6b20",
                                "text_color": "#c05621",
                            },
                            "info": {
                                "bg": "#e6fffa",
                                "border": "#319795",
                                "icon": "ℹ️",
                                "label": "ADVISORY",
                                "label_bg": "#319795",
                                "text_color": "#285e61",
                            },
                        }
                        
                        def render_alert_card(alert: FRMSAlert) -> str:
                            style = alert_styles.get(alert.level, alert_styles["info"])
                            return f"""
                            <div style="
                                background: {style['bg']};
                                border-left: 4px solid {style['border']};
                                border-radius: 8px;
                                padding: 14px 18px;
                                margin-bottom: 12px;
                                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
                            ">
                                <div style="display: flex; align-items: flex-start; gap: 14px;">
                                    <div style="font-size: 1.4em; line-height: 1; margin-top: 2px;">{style['icon']}</div>
                                    <div style="flex: 1;">
                                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                                            <span style="
                                                background: {style['label_bg']};
                                                color: white;
                                                font-size: 0.65em;
                                                font-weight: 700;
                                                padding: 3px 10px;
                                                border-radius: 4px;
                                                letter-spacing: 0.8px;
                                                text-transform: uppercase;
                                            ">{style['label']}</span>
                                            <code style="
                                                background: rgba(0,0,0,0.06);
                                                padding: 3px 8px;
                                                border-radius: 4px;
                                                font-size: 0.72em;
                                                color: #666;
                                                font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
                                            ">{alert.code}</code>
                                        </div>
                                        <div style="font-weight: 600; color: {style['text_color']}; margin-bottom: 6px; font-size: 0.95em;">
                                            {alert.message}
                                        </div>
                                        <div style="font-size: 0.85em; color: #4a5568; line-height: 1.5;">
                                            {alert.rationale}
                                        </div>
                                    </div>
                                </div>
                            </div>
                            """
                        
                        # Render alerts by priority
                        all_alert_html = ""
                        for a in critical_alerts + warning_alerts + info_alerts:
                            all_alert_html += render_alert_card(a)
                        
                        # Summary header with light theme
                        summary_parts = []
                        if critical_alerts:
                            summary_parts.append(f"<span style='color:#e53e3e;font-weight:600;'>{len(critical_alerts)} Critical</span>")
                        if warning_alerts:
                            summary_parts.append(f"<span style='color:#dd6b20;font-weight:600;'>{len(warning_alerts)} Caution</span>")
                        if info_alerts:
                            summary_parts.append(f"<span style='color:#319795;font-weight:600;'>{len(info_alerts)} Advisory</span>")
                        
                        st.markdown(
                            f"""
                            <div style="
                                background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
                                border: 1px solid #e2e8f0;
                                border-radius: 12px;
                                padding: 18px;
                                margin-bottom: 16px;
                            ">
                                <div style="
                                    display: flex;
                                    justify-content: space-between;
                                    align-items: center;
                                    margin-bottom: 14px;
                                    padding-bottom: 12px;
                                    border-bottom: 1px solid #e2e8f0;
                                ">
                                    <span style="color: #718096; font-size: 0.9em; font-weight: 500;">
                                        {len(alerts)} alert{'s' if len(alerts) != 1 else ''} triggered
                                    </span>
                                    <span style="font-size: 0.85em;">
                                        {' · '.join(summary_parts)}
                                    </span>
                                </div>
                                {all_alert_html}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                
                # Recommendations
                st.markdown("#### 💡 Recommendations")
                
                for i, rec in enumerate(result.recommendations, 1):
                    st.markdown(f"{i}. {rec}")
                
                # Circadian rhythm visualization
                if result.circadian_values:
                    st.markdown("#### 🌙 Circadian Rhythm Pattern")
                    
                    circ_data = df_fatigue[["DateTime", "Circadian"]].dropna()
                    if not circ_data.empty:
                        x_circ = [dt.strftime("%Y-%m-%d %H:%M") for dt in circ_data["DateTime"]]
                        y_circ = [round(float(c), 3) for c in circ_data["Circadian"]]
                        
                        circ_chart_config = {
                            "tooltip": {"trigger": "axis"},
                            "toolbox": {
                                "show": True,
                                "right": 10,
                                "feature": {
                                    "saveAsImage": {"show": True, "title": "Save (PNG)", "pixelRatio": 4},
                                    "restore": {"show": True, "title": "Reset"},
                                    "dataZoom": {"show": True, "title": {"zoom": "Zoom", "back": "Reset zoom"}},
                                },
                            },
                            "xAxis": {
                                "type": "category",
                                "data": x_circ,
                                "name": "Local time",
                                "nameLocation": "middle",
                                "nameGap": 35,
                                "axisLabel": {"rotate": 45, "fontSize": 10}
                            },
                            "yAxis": {
                                "type": "value",
                                "name": "Circadian Drive",
                            },
                            "series": [{
                                "type": "line",
                                "data": y_circ,
                                "smooth": True,
                                "lineStyle": {"color": "#8A2BE2", "width": 2},
                                "areaStyle": {"color": "#8A2BE222"},
                            }],
                            "grid": {"left": "10%", "right": "5%", "bottom": "15%", "top": "10%"},
                            "dataZoom": [{"type": "inside"}, {"type": "slider"}]
                        }
                        
                        render_echarts(
                            circ_chart_config,
                            height_px=300,
                            config=EChartsConfig()
                        )
                        st.caption(
                            "Circadian drive (y-axis, unitless) over local time (x-axis). "
                            "This curve helps interpret when the model expects circadian peaks and troughs "
                            "(WOCL typically ~02:00–06:00)."
                        )
                
                # Export option
                st.markdown("---")
                st.markdown("#### 📥 Export Results")
                
                csv_export = df_fatigue.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download Fatigue Predictions (CSV)",
                    csv_export,
                    file_name="fatigue_predictions.csv",
                    mime="text/csv",
                    key="fatigue_csv_download"
                )

                # FRMS exports (metrics + classification + crew rest)
                if frms_exposure is not None and frms_class is not None:
                    frms_summary_rows = [
                        {"field": "hours_in_scope", "value": frms_exposure.hours_in_scope, "unit": "h"},
                        {"field": "hours_in_wocl", "value": frms_exposure.hours_in_wocl, "unit": "h"},
                        {"field": "pct_hours_in_wocl", "value": frms_exposure.pct_hours_in_wocl, "unit": "%"},
                        {"field": "min_effectiveness", "value": frms_exposure.min_effectiveness, "unit": "%"},
                        {"field": "mean_effectiveness", "value": frms_exposure.mean_effectiveness, "unit": "%"},
                        {"field": "hours_below_90", "value": frms_exposure.hours_below_90, "unit": "h"},
                        {"field": "hours_at_or_below_77", "value": frms_exposure.hours_at_or_below_77, "unit": "h"},
                        {"field": "hours_at_or_below_70", "value": frms_exposure.hours_at_or_below_70, "unit": "h"},
                        {"field": "pct_hours_at_or_below_77", "value": frms_exposure.pct_hours_at_or_below_77, "unit": "%"},
                        {"field": "risk_level", "value": frms_class.risk_level, "unit": ""},
                        {"field": "severity", "value": frms_class.severity, "unit": ""},
                        {"field": "likelihood", "value": frms_class.likelihood, "unit": ""},
                        {"field": "rationale", "value": frms_class.rationale, "unit": ""},
                    ]
                    frms_csv = pd.DataFrame(frms_summary_rows).to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Download FRMS Summary (CSV)",
                        frms_csv,
                        file_name="frms_summary.csv",
                        mime="text/csv",
                        key="frms_summary_csv_download",
                    )

                    frms_payload = {
                        "thresholds": {
                            "low_risk_min_effectiveness": float(frms_thresholds.low_risk_min_effectiveness)
                            if frms_thresholds is not None
                            else 90.0,
                            "high_risk_max_effectiveness": float(frms_thresholds.high_risk_max_effectiveness)
                            if frms_thresholds is not None
                            else 77.0,
                            "severe_impairment_max_effectiveness": float(frms_thresholds.severe_impairment_max_effectiveness)
                            if frms_thresholds is not None
                            else 70.0,
                            "wocl_start_hour": int(frms_thresholds.wocl_start_hour) if frms_thresholds is not None else 2,
                            "wocl_end_hour": int(frms_thresholds.wocl_end_hour) if frms_thresholds is not None else 6,
                        },
                        "exposure": {
                            "samples_total": frms_exposure.samples_total,
                            "samples_in_scope": frms_exposure.samples_in_scope,
                            "hours_in_scope": frms_exposure.hours_in_scope,
                            "hours_in_wocl": frms_exposure.hours_in_wocl,
                            "min_effectiveness": frms_exposure.min_effectiveness,
                            "mean_effectiveness": frms_exposure.mean_effectiveness,
                            "hours_below_90": frms_exposure.hours_below_90,
                            "hours_at_or_below_77": frms_exposure.hours_at_or_below_77,
                            "hours_at_or_below_70": frms_exposure.hours_at_or_below_70,
                            "pct_hours_in_wocl": frms_exposure.pct_hours_in_wocl,
                            "pct_hours_at_or_below_77": frms_exposure.pct_hours_at_or_below_77,
                        },
                        "classification": {
                            "severity": frms_class.severity,
                            "likelihood": frms_class.likelihood,
                            "risk_level": frms_class.risk_level,
                            "rationale": frms_class.rationale,
                        },
                    }
                    if cr_assessment is not None:
                        frms_payload["usaf_crew_rest"] = {
                            "crew_rest_hours": cr_assessment.crew_rest_hours,
                            "required_crew_rest_hours": cr_assessment.required_crew_rest_hours,
                            "planned_sleep_opportunity_hours": cr_assessment.planned_sleep_opportunity_hours,
                            "required_sleep_opportunity_hours": cr_assessment.required_sleep_opportunity_hours,
                            "compliant": cr_assessment.compliant,
                            "notes": cr_assessment.notes,
                        }
                    if (
                        FRMS_AVAILABLE
                        and frms_thresholds is not None
                        and frms_exposure is not None
                        and frms_class is not None
                    ):
                        try:
                            payload_alerts = compute_frms_alerts(
                                exposure=frms_exposure,
                                classification=frms_class,
                                crew_rest=cr_assessment,
                                thresholds=frms_thresholds,
                            )
                        except Exception:
                            payload_alerts = []
                        frms_payload["alerts"] = [
                            {
                                "level": a.level,
                                "code": a.code,
                                "message": a.message,
                                "rationale": a.rationale,
                            }
                            for a in payload_alerts
                        ]
                    st.download_button(
                        "Download FRMS + Crew Rest Payload (JSON)",
                        json.dumps(frms_payload, ensure_ascii=False, default=str, indent=2).encode("utf-8"),
                        file_name="frms_dashboard.json",
                        mime="application/json",
                        key="frms_payload_json_download",
                    )

                st.info(
                    "For publication exports of the SAFTE/FRMS charts, use the **export toolbar above each ECharts plot** "
                    "(PNG high-DPI, SVG vector, HTML, spec JSON, or Print/Save PDF). Exports are generated locally in your browser."
                )
                
                st.caption(
                    f"Model: {result.model_used.upper()} SAFTE | "
                    f"Generated: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                )

    with tab_science:
        st.markdown("## 📚 Science (fast)")
        st.caption(
            "This tab is intentionally **lightweight** so switching tabs stays responsive. "
            "Pick one section to render at a time. Full citations live in **📚 References**."
        )

        science_sections: Dict[str, str] = {
            "Overview": (
                "**What you’ll find here**\n"
                "- Concise definitions and interpretation tips for key HRV/HRF metrics\n"
                "- Practical clinical cautions (e.g., LF/HF limitations)\n"
                "- A brief space-weather physiology framing\n\n"
                "**Tip:** Use the tabs **📚 References** (APA 7) and `docs/Manual.md` for the full manual."
            ),
            "Time-Domain HRV": (
                "| Metric | Definition | Physiology | Interpretation |\n"
                "|---|---|---|---|\n"
                "| **SDNN** | Std dev of NN intervals | Total variability | ↓ with age/stress/disease |\n"
                "| **RMSSD** | RMS of successive differences | Vagal modulation | Best short-term vagal marker |\n"
                "| **pNN50** | % successive diffs > 50 ms | Vagal activity | Artifact-sensitive |\n"
                "| **Mean HR** | Avg HR (bpm) | Net autonomic balance | Context-dependent |\n"
                "\n**Key insight:** RMSSD is typically the most reliable short-term recovery metric."
            ),
            "Frequency-Domain HRV": (
                "| Metric | Band | Interpretation |\n"
                "|---|---:|---|\n"
                "| **HF** | 0.15–0.40 Hz | Respiratory sinus arrhythmia (vagal) |\n"
                "| **LF** | 0.04–0.15 Hz | Baroreflex + mixed influences |\n"
                "| **LF/HF** | — | ⚠️ Breathing-dependent; not a pure stress index |\n"
                "\n**Caution:** Slow breathing can inflate LF without sympathetic activation."
            ),
            "Nonlinear / Complexity": (
                "| Metric | Meaning | Interpretation |\n"
                "|---|---|---|\n"
                "| **SD1/SD2** | Poincaré ratio | Short vs long dynamics |\n"
                "| **DFA α1** | Short-range fractal scaling | Near ~1.0 often healthy; extremes can reflect dysregulation |\n"
                "| **SampEn** | Irregularity/complexity | ↓ = more regular/rigid control |\n"
            ),
            "Heart Rate Fragmentation (HRF)": (
                "**What HRF is**  \n"
                "Heart Rate Fragmentation (HRF) describes frequent beat‑to‑beat direction changes in RR‑interval dynamics "
                "(acceleration ↔ deceleration) — a pattern sometimes described as *sinoatrial instability* that can occur even when "
                "the ECG appears sinus rhythm (Costa et al., 2017; Hayano et al., 2020).  \n\n"
                "**Why it matters**  \n"
                "- HRF captures a component of short‑term variability that may not reflect pure vagal modulation, and can therefore "
                "confound interpretation of HF/RMSSD‑driven “high HRV” in some cases (Costa et al., 2017; Hayano et al., 2020).  \n"
                "- HRF markers have been studied in older cohorts for long‑term incident atrial fibrillation prediction (Guichard et al., 2025).  \n\n"
                "**Operational note**  \n"
                "If HRF is high, first verify recording quality (motion/contact/ectopy). If quality is good and HRF is persistently "
                "elevated versus your baseline, treat it as a *rhythm stability* flag and interpret alongside mean HR, RMSSD/HF, sleep, and symptoms.  \n\n"
                "| Metric | Meaning |\n"
                "|---|---|\n"
                "| **PIP** | % inflection points (direction changes) |\n"
                "| **IALS** | Inverse avg segment length (run interruption) |\n"
                "| **W0–W3** | 4-beat “word” patterns by inflection count |\n"
                "\n**Use:** HRF can reflect rhythm fragmentation beyond classic HRV magnitude measures."
            ),
            "Autonomic Function Tests": (
                "| Test | Normal-ish | Notes |\n"
                "|---|---:|---|\n"
                "| **Valsalva ratio** | ≥ ~1.2 | Age-dependent |\n"
                "| **Deep breathing E:I** | Higher in youth | Declines with age |\n"
                "| **30:15 ratio** | ≥ ~1.04 | Baroreflex screening |\n"
            ),
            "Solar Activity & HRV (overview)": (
                "| Solar metric | Concept | Typical analysis |\n"
                "|---|---|---|\n"
                "| **Kp / Dst** | Geomagnetic disturbance | Lagged correlations (hours–days) |\n"
                "| **F10.7** | Solar-cycle proxy | Long-horizon / confounded |\n"
                "\n**Caution:** Effects are often small; control for time-of-day, season, and behavior."
            ),
            "Reference Values (5-min norms)": (
                "| Metric | Typical reference |\n"
                "|---|---|\n"
                "| **SDNN** | ~50 ± 16 ms |\n"
                "| **RMSSD** | ~42 ± 15 ms |\n"
                "\n**Important:** Population norms vary; within-subject baselines are usually more actionable."
            ),
        }

        selected_section = st.selectbox(
            "Section",
            options=list(science_sections.keys()),
            index=0,
            key="science_section_select",
        )
        st.markdown(science_sections.get(selected_section, science_sections["Overview"]))
        st.markdown("---")
        st.info("References are consolidated in the **📚 References** tab (APA 7 format).")

    # ==================== CIRCADIAN PHYSIOLOGY TAB ====================
    with tab_circadian:
        if CIRCADIAN_TAB_AVAILABLE:
            # Pass user profile if available for personalized simulations
            user_profile_data = None
            if "current_user_id" in st.session_state:
                user_profile_data = {"user_id": st.session_state.get("current_user_id")}
            render_circadian_tab(
                user_profile=user_profile_data,
                user_context=active_user_context,
            )
        else:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                border-radius: 16px;
                padding: 2rem;
                text-align: center;
                border: 1px solid rgba(102, 126, 234, 0.2);
            ">
                <h2 style="color: #667eea; margin-bottom: 1rem;">🌙 Circadian Physiology</h2>
                <p style="color: #a0a0a0;">
                    The Circadian Physiology module provides simulation and visualization of
                    circadian rhythm dynamics using validated mathematical models.
                </p>
                <p style="color: #888; margin-top: 1rem;">
                    ⚠️ Module not available. Please ensure <code>app/circadian/</code> package is installed.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Show brief documentation even if module unavailable
            with st.expander("📖 About Circadian Models"):
                st.markdown("""
                **Available Models:**
                - **Forger99**: 3-state limit cycle pacemaker (Forger et al., 1999)
                - **Jewett99**: Revised limit cycle oscillator (Kronauer et al., 1999)
                - **Hannay19**: Macroscopic amplitude-phase model (Hannay et al., 2019)
                - **Hannay19TP**: Two-population SCN model
                
                **Features:**
                - Light schedule simulation (Regular, ShiftWork, SlamShift, SocialJetlag)
                - Phase response curve analysis
                - DLMO and CBT marker prediction
                - ESRI (Entrainment Signal Regularity Index) computation
                - Double-plotted actogram visualization
                
                **Original Package:** [Arcascope/circadian](https://github.com/Arcascope/circadian)
                """)

    with tab_space_data:
        st.subheader("🌐 Space Data Dashboard (SWPC + NOAA + DONKI)")
        # UX: Streamlit can visually "restart" (stale-element fade/dim) during reruns and
        # long fetches. Space Data is a data dashboard; keep the page visually stable.
        st.markdown(
            """
            <style>
            .stApp .stale,
            .stApp [data-stale="true"],
            div[data-testid="stAppViewContainer"] .stale,
            div[data-testid="stAppViewContainer"] [data-stale="true"] {
                opacity: 1 !important;
                filter: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        
        # Dashboard renders immediately - no blocking background fetch
        _sw_loading_msg = st.empty()

        # NOTE: Content always loads - no lazy loading gate.
        _sw_content_loaded = True
        st.session_state["_space_data_tab_loaded"] = True
        
        # =====================================================================
        # IMPACT PREDICTION SECTION - Expected hit times for Bogotá, Colombia
        # =====================================================================
        if _sw_content_loaded:
            if not is_download_enabled("space_weather_impact"):
                st.markdown("---")
                st.info(
                    "Impact predictions are disabled by **⚡ Performance Settings → Downloads**. "
                    "Enable **Space Weather Impact Predictions** to use this section."
                )
                st.markdown("---")
            elif SPACE_WEATHER_IMPACT_AVAILABLE:
                st.markdown("---")
                st.markdown("### 🎯 Space Weather Impact Predictions")
                st.markdown(f"*All times in Bogotá, Colombia ({BOGOTA_TZ_NAME})*")
                with st.expander("🔎 Method & Accuracy (astrophysics-first)", expanded=False):
                    st.markdown(
                        """
**What this panel reports (arrival at Earth):**

- **☀️ Photons / X-rays (GOES)**: Observed at Earth (arrival ≈ observation time). Flare class uses the 0.1–0.8 nm band.
- **⚡ SEPs / Protons (GOES)**: Uses the **integral proton flux ≥10 MeV (pfu)**, which defines NOAA’s **S-scale** (radiation storms).
- **🌊 Solar wind plasma (DSCOVR/ACE at L1)**: Uses the current L1 solar-wind speed and a ballistic time-of-flight over ~1.5 million km (typical **30–60 min** lead time).
- **💥 CME / Shock (NASA DONKI WSA+ENLIL)**: Uses DONKI’s **WSA+ENLIL** simulation output `estimatedShockArrivalTime` when available.
  - The row includes the model’s **Kp scenario range** (multiple Kp values are provided because **CME magnetic field orientation (IMF Bz)** is not deterministically predicted from coronagraph data).
  - A **DBM (drag-based model) range** is shown as an independent physics cross-check (when CME speed + `time21_5` are available).

**Critical limitations (accuracy honesty):**

- **CME/shock timing is forecast, not a measurement**; typical errors can be many hours. Always validate near arrival with **real-time solar wind**, **Kp**, and **Dst**.
- **Geomagnetic intensity depends on IMF Bz** (southward Bz couples strongly to Earth). ENLIL timing can be good, but storm strength remains uncertain without Bz.

**References / official definitions:**

- NOAA Space Weather Scales (R/S/G): [NOAA SWPC](https://www.swpc.noaa.gov/noaa-scales-explanation)
- NASA DONKI (WSA+ENLIL simulation catalog): [NASA DONKI](https://api.nasa.gov/)
- ENLIL model: Odstrčil, D. (2003). *Advances in Space Research, 32*(4), 497–506. ([doi:10.1016/S0273-1177(03)00332-6](https://doi.org/10.1016/S0273-1177(03)00332-6))
- Drag-based CME propagation (DBM): Dumbović, M., et al. (2021). *Frontiers in Astronomy and Space Sciences, 8*, 58. ([doi:10.3389/fspas.2021.639986](https://doi.org/10.3389/fspas.2021.639986))
                        """
                    )

                # Session state for impact snapshot
                if "impact_snapshot" not in st.session_state:
                    st.session_state["impact_snapshot"] = None
                if "impact_snapshot_error" not in st.session_state:
                    st.session_state["impact_snapshot_error"] = ""
                if "impact_snapshot_loading" not in st.session_state:
                    st.session_state["impact_snapshot_loading"] = False

                col_fetch_impact, col_refresh_info = st.columns([1, 2])
                with col_fetch_impact:
                    if st.button("🔄 Fetch Impact Predictions", key="fetch_impact_predictions"):
                        st.session_state["impact_snapshot_loading"] = True
                        try:
                            with st.spinner("Calculating arrival times..."):
                                snapshot = fetch_space_weather_snapshot()
                            st.session_state["impact_snapshot"] = snapshot
                            st.session_state["impact_snapshot_error"] = ""
                        except Exception as exc:
                            log_exception(_LOGGER, "Manual impact prediction fetch failed", exc)
                            st.session_state["impact_snapshot_error"] = str(exc)
                            st.error(f"Failed to fetch impact predictions: {exc}")
                        finally:
                            st.session_state["impact_snapshot_loading"] = False
                with col_refresh_info:
                    if st.session_state.get("impact_snapshot"):
                        snap = st.session_state["impact_snapshot"]
                        st.caption(f"Last updated: {format_datetime_bogota(snap.timestamp_utc)}")

                snapshot = st.session_state.get("impact_snapshot")
                if snapshot is not None:
                    # Priority recommendation banner
                    recommendation = get_priority_recommendation(snapshot)
                    most_severe = snapshot.most_severe()

                    if most_severe:
                        severity_color = get_severity_color(most_severe.severity)
                        st.markdown(
                            f"""
                            <div style="
                                background: linear-gradient(135deg, {severity_color}20, {severity_color}10);
                                border-left: 4px solid {severity_color};
                                padding: 1rem;
                                border-radius: 0.5rem;
                                margin-bottom: 1rem;
                            ">
                                <h4 style="margin: 0 0 0.5rem 0; color: {severity_color};">
                                    {get_category_icon(most_severe.category)} POLAR H10 MONITORING RECOMMENDATION
                                </h4>
                                <div style="font-size: 0.95rem;">{recommendation}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    # Impact arrival times table
                    st.markdown("#### ⏰ Expected Impact Times (Bogotá)")
                    impact_df = build_impact_summary_df(snapshot)

                    if not impact_df.empty:
                        # Highlight styling for severity
                        def style_severity(val: str) -> str:
                            colors = {
                                "EXTREME": "background-color: #dc262620; color: #dc2626; font-weight: bold",
                                "SEVERE": "background-color: #ea580c20; color: #ea580c; font-weight: bold",
                                "STRONG": "background-color: #f9731620; color: #f97316; font-weight: bold",
                                "MODERATE": "background-color: #facc1520; color: #ca8a04",
                                "MINOR": "background-color: #22c55e20; color: #22c55e",
                                "QUIET": "background-color: #64748b20; color: #64748b",
                            }
                            return colors.get(val, "")

                        # Use map for pandas >= 2.1, fallback to applymap for older versions
                        try:
                            styled_df = impact_df.style.map(style_severity, subset=["Severity"])
                        except AttributeError:
                            styled_df = impact_df.style.applymap(style_severity, subset=["Severity"])
                        st.dataframe(styled_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("No impact events detected. Click 'Fetch Impact Predictions' to update.")

                    # Individual event cards with detailed info
                    with st.expander("📋 Detailed Event Information & Polar H10 Instructions", expanded=True):
                        events = snapshot.all_events()
                        if events:
                            for event in events:
                                icon = get_category_icon(event.category)
                                severity_color = get_severity_color(event.severity)

                                st.markdown(
                                    f"""
                                    <div style="
                                        border: 1px solid {severity_color}40;
                                        border-radius: 0.5rem;
                                        padding: 1rem;
                                        margin-bottom: 0.75rem;
                                        background: {severity_color}08;
                                    ">
                                        <h5 style="margin: 0 0 0.5rem 0;">
                                            {icon} {event.category.value.upper()} - {event.severity.value.upper()}
                                        </h5>
                                        <p style="margin: 0.25rem 0;"><strong>Arrival:</strong> {format_datetime_bogota(event.arrival_time_utc)}</p>
                                        <p style="margin: 0.25rem 0;"><strong>Confidence:</strong> {event.confidence * 100:.0f}%</p>
                                        <p style="margin: 0.25rem 0;"><strong>Source:</strong> {event.source_description}</p>
                                        <p style="margin: 0.25rem 0;"><strong>Biological Effect:</strong> {event.biological_effect}</p>
                                        <hr style="margin: 0.5rem 0; border-color: {severity_color}30;">
                                        <p style="margin: 0.25rem 0;"><strong>🎽 Polar H10 Action:</strong> {event.polar_h10_recommendation}</p>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )
                        else:
                            st.info("No significant events detected.")

                    # Show any errors
                    if snapshot.errors:
                        with st.expander("⚠️ Data Fetch Warnings"):
                            for key, msg in snapshot.errors.items():
                                st.warning(f"**{key}**: {msg}")
                else:
                    error_msg = st.session_state.get("impact_snapshot_error")
                    if error_msg:
                        st.warning(
                            "Impact predictions are temporarily unavailable; using last known data when possible. "
                            f"Details: {error_msg}"
                        )
                    else:
                        st.info(
                            "Click **'Fetch Impact Predictions'** to calculate expected arrival times "
                            "for space weather events and get Polar H10 monitoring recommendations."
                        )

                st.markdown("---")
            else:
                st.markdown("---")
                st.info(
                    "Impact prediction module (`space_weather_impact.py`) is unavailable; "
                    "continuing with the SWPC dashboard below."
                )
                st.markdown("---")
        
            # =====================================================================
            # Space weather state initialization
            # =====================================================================
            space_state = _space_weather_state()
            donki_state = _donki_state()

            # Background prefetch disabled: keep UI deterministic and instant.
            bg_status = {
                "space_weather": {"done": True, "error": None, "stale": False},
                "noaa": {"done": True, "error": None, "stale": False},
                "donki": {"done": True, "error": None, "stale": False},
            }
            data_age = "manual (click Fetch)"

            # NOTE: Do not auto-load or auto-fetch any space-weather data on tab open.
            # This tab must remain fully on-demand (click Load cached / Fetch).

            rr_min_utc, rr_max_utc = _get_uploaded_rr_time_bounds()
            # -----------------------------------------------------------------
            # Fetch controls (use a form to avoid reruns while editing settings)
            # -----------------------------------------------------------------
            with st.form("space_data_fetch_controls", clear_on_submit=False):
                col_load_cache, col_fetch_sw, col_fetch_donki, col_bg_info = st.columns(
                    [1, 1, 1, 2]
                )
                with col_load_cache:
                    load_cache_clicked = st.form_submit_button(
                        "⚡ Load cached copy",
                    )
                with col_fetch_sw:
                    fetch_sw_clicked = st.form_submit_button(
                        "📥 Fetch space weather",
                    )
                with col_fetch_donki:
                    fetch_donki_clicked = st.form_submit_button(
                        "🌐 Fetch NASA DONKI",
                        disabled=not NASA_API_KEY,
                    )
                with col_bg_info:
                    cache_hint = "loaded" if space_state.get("loaded") else "not loaded"
                    st.caption(
                        "⏸️ Background prefetch disabled | "
                        f"SWPC data: {cache_hint} | Click Load cached / Fetch"
                    )

                st.caption(
                    "Tip: adjust the settings below, then click a fetch button (prevents rerun flicker)."
                )
                donki_window_days = st.slider(
                    "DONKI window (days)",
                    min_value=7,
                    max_value=30,
                    value=14,  # smaller default for faster queries
                    step=1,
                    key="donki_window_days",
                )
                donki_sync_rr = False
                donki_pad_days = 0
                if rr_min_utc is not None and rr_max_utc is not None:
                    # Auto-default influence horizons once per session (do not override user edits).
                    if "donki_sync_rr_pad_days" not in st.session_state:
                        try:
                            rec: InfluenceHorizonRecommendation = recommend_influence_horizons_from_hrv(
                                rr_min_utc,
                                rr_max_utc,
                                assumed_earth_influence_hours=72,
                            )
                            st.session_state["donki_sync_rr_pad_days"] = int(rec.recommended_donki_pad_days)
                            st.session_state.setdefault(
                                "swpc_sync_rr_pad_hours", int(rec.recommended_rr_pad_hours)
                            )
                            st.session_state.setdefault(
                                "noaa_sync_rr_pad_hours", int(rec.recommended_rr_pad_hours)
                            )
                            st.session_state["space_influence_horizon_rec"] = {
                                "computed_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                                "solar_to_earth_max_hours": float(rec.solar_to_earth_max_hours),
                                "donki_pad_days": int(rec.recommended_donki_pad_days),
                                "rr_pad_hours": int(rec.recommended_rr_pad_hours),
                            }
                        except Exception as exc:
                            # Defensive: never crash Space Data for a recommendation helper.
                            log_exception(_LOGGER, "Influence horizon recommendation failed", exc)

                    st.caption(
                        f"Uploaded RR timeline (UTC): {rr_min_utc.strftime('%Y-%m-%d %H:%M')} → {rr_max_utc.strftime('%Y-%m-%d %H:%M')}"
                    )
                    donki_sync_rr = st.checkbox(
                        "Sync DONKI query to uploaded RR timeline",
                        value=True,
                        key="donki_sync_rr_window",
                        help=(
                            "Uses your RR recording date range for DONKI queries (plus optional padding). "
                            "This avoids downloading unrelated events and keeps queries fast."
                        ),
                    )
                    donki_pad_days = int(
                        st.number_input(
                            "DONKI padding (days)",
                            min_value=0,
                            max_value=30,
                            value=3,
                            step=1,
                            key="donki_sync_rr_pad_days",
                            help=(
                                "Extra days before/after the RR range when querying DONKI "
                                "(helps capture CME/SEP arrivals around the recording)."
                            ),
                        )
                    )

            # Cache maintenance (explicit user action; never automatic deletion)
            with st.expander("🧹 Cache maintenance", expanded=False):
                confirm_clear = st.checkbox(
                    "Enable cache reset actions (deletes local cached files)",
                    value=False,
                    key="cache_reset_confirm_space_weather",
                    help=(
                        "Use only if caches are corrupted or you want a clean refetch. "
                        "First load after clearing will be slower."
                    ),
                )
                if st.button(
                    "🧹 Clear Space Weather + NOAA + DONKI caches",
                    key="cache_reset_all_space",
                    disabled=not confirm_clear,
                ):
                    deleted_sw, err_sw = _clear_cache_dir(SPACE_WEATHER_CACHE_DIR)
                    deleted_noaa, err_noaa = _clear_cache_dir(CACHE_BASE_DIR / "noaa_space")
                    deleted_donki, err_donki = _clear_cache_dir(DONKI_CACHE_DIR)

                    # Clear Streamlit in-memory caches (best-effort).
                    try:
                        st.cache_data.clear()
                        st.cache_resource.clear()
                    except Exception:
                        pass

                    # Reset session-state data holders so UI doesn't show stale values.
                    space_state["loaded"] = False
                    space_state["kp_df"] = pd.DataFrame()
                    space_state["flux_df"] = pd.DataFrame()
                    space_state["kp_error"] = ""
                    space_state["flux_error"] = ""
                    space_state["last_updated"] = None

                    donki_state["loaded"] = False
                    donki_state["datasets"] = {}
                    donki_state["errors"] = {}
                    donki_state["last_updated"] = None

                    noaa_state = _noaa_space_state()
                    noaa_state["bundles"] = {}
                    noaa_state["errors"] = {}
                    noaa_state["last_updated"] = None

                    # Reset background fetch status so a fresh fetch can run.
                    with _bg_fetch_lock:
                        for k in ("space_weather", "noaa", "donki"):
                            _bg_fetch_results[k]["done"] = False
                            _bg_fetch_results[k]["error"] = None
                            _bg_fetch_results[k]["data"] = {}
                            _bg_fetch_results[k]["fetch_time"] = None
                            _bg_fetch_results[k]["_applied"] = False

                    errors_local = [e for e in (err_sw, err_noaa, err_donki) if e]
                    if errors_local:
                        st.error("Cache reset completed with errors: " + " | ".join(errors_local))
                    else:
                        st.success(
                            f"Cleared caches: SWPC={deleted_sw} file(s), NOAA={deleted_noaa} file(s), DONKI={deleted_donki} file(s)."
                        )
            if load_cache_clicked:
                with st.spinner("Loading cached space weather…"):
                    _load_space_weather_cache_only(space_state)
                st.success("Loaded cached space weather data (no network).")

            if fetch_sw_clicked:
                _sw_fetch_success = False
                with st.status(
                    "Fetching NOAA SWPC datasets…", state="running", expanded=True
                ) as status:
                    try:
                        _fetch_space_weather_datasets(space_state)
                        last_fetch = space_state.get("last_updated")
                        if isinstance(last_fetch, pd.Timestamp):
                            label = (
                                f"Space weather datasets updated at "
                                f"{last_fetch.strftime('%Y-%m-%d %H:%M UTC')}."
                            )
                        else:
                            label = "Space weather datasets updated."
                        status.update(label=label, state="complete", expanded=False)
                        _sw_fetch_success = True
                    except Exception as exc:
                        log_exception(_LOGGER, "NOAA SWPC fetch failed", exc)
                        status.update(
                            label=f"Fetch failed: {exc}", state="error", expanded=True
                        )
                        st.error(f"Failed to fetch NOAA SWPC datasets: {exc}")
                if _sw_fetch_success:
                    # Results are already in session state; avoid extra rerun/flicker.
                    pass
            if fetch_donki_clicked:
                if not NASA_API_KEY:
                    st.warning(
                        "Set NASA_API_KEY in your .env file to query NASA DONKI APIs."
                    )
                else:
                    _donki_fetch_success = False
                    if donki_sync_rr and rr_min_utc is not None and rr_max_utc is not None:
                        start_dt = (rr_min_utc - pd.Timedelta(days=int(donki_pad_days))).date()
                        end_dt = (rr_max_utc + pd.Timedelta(days=int(donki_pad_days))).date()
                        # Hard bound: prevent accidentally huge DONKI payloads (JSON normalization can be slow).
                        max_days = 30
                        if (pd.Timestamp(end_dt) - pd.Timestamp(start_dt)) > pd.Timedelta(days=max_days):
                            st.warning(
                                f"RR-aligned DONKI window exceeds {max_days} days; limiting to the most recent {max_days} days for performance."
                            )
                            start_dt = (pd.Timestamp(end_dt) - pd.Timedelta(days=max_days)).date()
                        start_donki, end_donki = start_dt.isoformat(), end_dt.isoformat()
                    else:
                        start_donki, end_donki = _donki_default_range(
                            int(donki_window_days)
                        )
                    with st.status(
                        "Fetching NASA DONKI datasets…", state="running", expanded=True
                    ) as status:
                        try:
                            _fetch_donki_datasets(donki_state, start_donki, end_donki)
                            last_donki = donki_state.get("last_updated")
                            if isinstance(last_donki, pd.Timestamp):
                                label = (
                                    f"DONKI datasets updated at "
                                    f"{last_donki.strftime('%Y-%m-%d %H:%M UTC')}."
                                )
                            else:
                                label = "DONKI datasets updated."
                            status.update(label=label, state="complete", expanded=False)
                            _donki_fetch_success = True
                        except Exception as exc:
                            log_exception(_LOGGER, "NASA DONKI fetch failed", exc)
                            status.update(
                                label=f"DONKI fetch failed: {exc}",
                                state="error",
                                expanded=True,
                            )
                            st.error(f"Failed to fetch NASA DONKI datasets: {exc}")
                    if _donki_fetch_success:
                        # Results are already in session state; avoid extra rerun/flicker.
                        pass

            if space_state.get("swl_loaded"):
                last_swl = space_state.get("swl_last_updated")
                if isinstance(last_swl, pd.Timestamp):
                    st.caption(
                        f"Latest SpaceWeatherLive CME snapshot: {last_swl.strftime('%Y-%m-%d %H:%M UTC')}")
                else:
                    st.caption("SpaceWeatherLive CME snapshot: loaded.")

            kp_df = pd.DataFrame()
            flux_df = pd.DataFrame()
            kp_error = False
            if not space_state.get("loaded"):
                if not bg_status.get("space_weather", {}).get("done", False):
                    st.info("Fetching space weather in the background… (you can also click **Fetch space weather**).")
                else:
                    st.info("Click **Fetch space weather** to populate NOAA SWPC metrics.")
            else:
                last_fetch = space_state.get("last_updated")
                if isinstance(last_fetch, pd.Timestamp):
                    st.caption(
                        f"Last fetched: {last_fetch.strftime('%Y-%m-%d %H:%M UTC')}")
                kp_df_full = space_state.get("kp_df", pd.DataFrame())
                kp_error_msg = space_state.get("kp_error", "")
                flux_df_full = space_state.get("flux_df", pd.DataFrame())
                flux_error_msg = space_state.get("flux_error", "")
                kp_error = bool(kp_error_msg)
                # View controls: wrap in a form to avoid reruns while adjusting sliders.
                # This reduces the "app restart" feel when exploring Space Data.
                with st.form("space_data_swpc_view_controls", clear_on_submit=False):
                    swpc_sync_rr = False
                    swpc_pad_hours = 0
                    if rr_min_utc is not None and rr_max_utc is not None:
                        swpc_sync_rr = st.checkbox(
                            "Sync SWPC plots to uploaded RR timeline",
                            value=True,
                            key="swpc_sync_rr_window",
                            help=(
                                "Filters SWPC time-series plots (Kp/F10.7) to your RR recording window "
                                "(plus optional padding) to keep renders fast and aligned."
                            ),
                        )
                        swpc_pad_hours = int(
                            st.number_input(
                                "SWPC plot padding (hours)",
                                min_value=0,
                                max_value=24 * 14,
                                value=6,
                                step=1,
                                key="swpc_sync_rr_pad_hours",
                            )
                        )
                    flux_history_days = st.slider(
                        "F10.7 history (days)",
                        min_value=7,
                        max_value=90,
                        value=14,
                        step=1,
                        key="flux_days",
                    )
                    kp_history_days = st.slider(
                        "Kp history (days)",
                        min_value=3,
                        max_value=30,
                        value=14,
                        step=1,
                        key="kp_days",
                    )
                    _ = st.form_submit_button("Apply SWPC view settings")

                with st.container():
                    st.markdown("#### Solar Radio Flux (F10.7 cm)")
                    if flux_error_msg:
                        st.error(flux_error_msg)
                    else:
                        flux_df = flux_df_full.copy()
                        if not flux_df.empty and "time_tag" in flux_df.columns:
                            time_series = pd.to_datetime(
                                flux_df["time_tag"], utc=True, errors="coerce"
                            )
                            if swpc_sync_rr and rr_min_utc is not None and rr_max_utc is not None:
                                window_start = rr_min_utc - pd.Timedelta(hours=int(swpc_pad_hours))
                                window_end = rr_max_utc + pd.Timedelta(hours=int(swpc_pad_hours))
                                mask = (time_series >= window_start) & (time_series <= window_end)
                            else:
                                cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(
                                    days=int(flux_history_days)
                                )
                                mask = time_series >= cutoff
                            flux_df = flux_df.loc[mask].copy()
                            flux_df["time_tag"] = time_series[mask]
                        if not flux_df.empty:
                            numeric_flux_cols = [
                                col
                                for col in flux_df.columns
                                if flux_df[col].dtype.kind in "fcid"
                            ]
                            value_candidates = [
                                col
                                for col in numeric_flux_cols
                                if any(
                                    keyword in col.lower()
                                    for keyword in (
                                        "flux",
                                        "observed",
                                        "adjusted",
                                        "predicted",
                                        "value",
                                    )
                                )
                            ]
                            value_col = (
                                value_candidates[0] if value_candidates else (
                                    numeric_flux_cols[0] if numeric_flux_cols else None))
                            if value_col:
                                flux_numeric = flux_df.dropna(
                                    subset=[value_col]
                                ).sort_values("time_tag")
                                if not flux_numeric.empty:
                                    latest_flux = float(
                                        flux_numeric[value_col].iloc[-1])
                                    latest_time = (
                                        flux_numeric["time_tag"].iloc[-1]
                                        if "time_tag" in flux_numeric.columns
                                        else None
                                    )
                                    prev_flux = (
                                        float(flux_numeric[value_col].iloc[-2])
                                        if flux_numeric.shape[0] >= 2
                                        else latest_flux
                                    )
                                    delta_flux = latest_flux - prev_flux
                                    col_flux_gauge, col_flux_chart = st.columns([1, 2])
                                    with col_flux_gauge:
                                        _echarts_gauge(
                                            latest_flux,
                                            min_val=60.0,
                                            max_val=260.0,
                                            title="F10.7 now",
                                            unit="sfu",
                                            precision=1,
                                            thresholds=[
                                                (90.0, "#22c55e"),
                                                (130.0, "#facc15"),
                                                (180.0, "#ef4444"),
                                            ],
                                            height_px=260,
                                        )
                                        if latest_time is not None:
                                            st.caption(
                                                f"UTC timestamp: {latest_time.strftime('%Y-%m-%d %H:%M')}"
                                            )
                                        st.caption(
                                            "Quiet solar output ≲90 sfu • enhanced 90–130 sfu • high ≥180 sfu."
                                        )
                                    with col_flux_chart:
                                        flux_recent = flux_numeric.tail(
                                            min(160, flux_numeric.shape[0])
                                        )
                                        _echarts_sparkline(
                                            flux_recent["time_tag"].tolist(),
                                            flux_recent[value_col].astype(float).tolist(),
                                            title="F10.7 trend (selected window)",
                                            color_primary="#f97316",
                                            area_colors=(
                                                "rgba(249,115,22,0.28)",
                                                "rgba(249,115,22,0.05)",
                                            ),
                                        )
                                        st.metric(
                                            "Δ since previous point",
                                            f"{delta_flux:+.1f}",
                                        )
                                        st.caption(
                                            "Three-hour cadence view of F10.7 solar radio flux over the selected history window."
                                        )
                                    flux_numeric = flux_numeric.sort_values(
                                        "time_tag")
                                    stats_cols = st.columns(3)
                                    last_week_mask = flux_numeric[
                                        "time_tag"
                                    ] >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)
                                    weekly_mean = (
                                        flux_numeric.loc[last_week_mask, value_col].mean()
                                        if last_week_mask.any()
                                        else flux_numeric[value_col].mean()
                                    )
                                    stats_cols[0].metric(
                                        "7 d mean", f"{weekly_mean:.1f}")
                                    stats_cols[1].metric(
                                        "Max (window)",
                                        f"{flux_numeric[value_col].max():.1f}",
                                    )
                                    stats_cols[2].metric(
                                        "Std dev",
                                        f"{flux_numeric[value_col].std(ddof=1):.1f}",
                                    )
                                    chart_df = (
                                        flux_numeric.set_index("time_tag")
                                        .sort_index()
                                    )
                                    if chart_df.empty:
                                        st.info(
                                            "F10.7 component comparison unavailable."
                                        )
                                    else:
                                        observed_series = pd.to_numeric(
                                            chart_df[value_col],
                                            errors="coerce",
                                        )
                                        ninety_series_list: Optional[
                                            List[Optional[float]]
                                        ] = None
                                        ninety_col = next(
                                            (
                                                col
                                                for col in numeric_flux_cols
                                                if "ninety" in col.lower()
                                            ),
                                            None,
                                        )
                                        if (
                                            ninety_col
                                            and ninety_col in chart_df.columns
                                        ):
                                            ninety_series = pd.to_numeric(
                                                chart_df[ninety_col],
                                                errors="coerce",
                                            )
                                            if ninety_series.notna().any():
                                                ninety_filled = (
                                                    ninety_series.ffill().bfill()
                                                )
                                                ninety_series_list = []
                                                for val in ninety_filled.tolist():
                                                    if val is None:
                                                        ninety_series_list.append(
                                                            None
                                                        )
                                                        continue
                                                    val_float = float(val)
                                                    ninety_series_list.append(
                                                        val_float
                                                        if np.isfinite(val_float)
                                                        else None
                                                    )
                                        _echarts_flux_component_comparison(
                                            list(chart_df.index),
                                            observed_series.tolist(),
                                            ninety_series_list,
                                            title="F10.7 component comparison",
                                        )
                                        st.caption(
                                            "Observed F10.7 flux (orange) with the dashed 90-day mean and bars indicating deviations."
                                        )
                                    if (
                                        "time_tag" in flux_numeric.columns
                                        and flux_numeric.shape[0] >= 5
                                    ):
                                        st.markdown(
                                            "##### Rolling confidence interval")
                                        f_win = st.number_input(
                                            "Rolling CI window (points)",
                                            min_value=5,
                                            max_value=int(max(10, flux_numeric.shape[0])),
                                            value=int(min(24, flux_numeric.shape[0])),
                                            step=1,
                                            key="f107_win",
                                        )
                                        vals = (
                                            flux_numeric[value_col]
                                            .astype(float)
                                            .reset_index(drop=True)
                                        )
                                        minp = max(3, int(f_win // 2))
                                        roll_mean = vals.rolling(
                                            int(f_win), min_periods=minp
                                        ).mean()
                                        roll_std = vals.rolling(
                                            int(f_win), min_periods=minp
                                        ).std(ddof=1)
                                        roll_n = vals.rolling(
                                            int(f_win), min_periods=minp
                                        ).count()
                                        se = roll_std / np.sqrt(roll_n)
                                        low = roll_mean - 1.96 * se
                                        high = roll_mean + 1.96 * se
                                        _echarts_time_with_ci(
                                            flux_numeric["time_tag"].tolist(),
                                            vals.tolist(),
                                            low.tolist(),
                                            high.tolist(),
                                            title="F10.7 rolling 95% confidence interval",
                                            y_name="sfu",
                                            series_name="F10.7",
                                        )
                                        st.caption(
                                            "Rolling mean ±1.96·SE highlights medium-term swings in solar radio flux relevant to ionospheric conditions."
                                        )
                                    else:
                                        st.info(
                                            "Not enough F10.7 samples to build a rolling confidence interval."
                                        )
                                else:
                                    st.info(
                                        "Solar radio flux values are not available in the NOAA feed."
                                    )
                            else:
                                st.info(
                                    "Solar radio flux dataset does not contain numeric values to display."
                                )
                        else:
                            st.info("Solar radio flux data currently unavailable.")

                with st.container():
                    st.markdown("#### Planetary K-index (3-hour cadence)")
                    if kp_error_msg:
                        st.error(kp_error_msg)
                    else:
                        kp_df = kp_df_full.copy()
                        if not kp_df.empty and "time_tag" in kp_df.columns:
                            time_series = pd.to_datetime(
                                kp_df["time_tag"], errors="coerce", utc=True
                            )
                            if swpc_sync_rr and rr_min_utc is not None and rr_max_utc is not None:
                                window_start = rr_min_utc - pd.Timedelta(hours=int(swpc_pad_hours))
                                window_end = rr_max_utc + pd.Timedelta(hours=int(swpc_pad_hours))
                                mask = (time_series >= window_start) & (time_series <= window_end)
                            else:
                                cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(
                                    days=int(kp_history_days)
                                )
                                mask = time_series >= cutoff
                            kp_df = kp_df.loc[mask].copy()
                            kp_df["time_tag"] = time_series[mask]
                        if not kp_df.empty and "kp_index" in kp_df.columns:
                            kp_df["kp_index"] = pd.to_numeric(
                                kp_df["kp_index"], errors="coerce"
                            )
                            kp_numeric = kp_df.dropna(
                                subset=["kp_index"]).sort_values("time_tag")
                            if not kp_numeric.empty:
                                kp_df = kp_numeric
                                latest_kp = float(kp_numeric["kp_index"].iloc[-1])
                                latest_time = (
                                    kp_numeric["time_tag"].iloc[-1]
                                    if "time_tag" in kp_numeric.columns
                                    else None
                                )
                                prev_value = (
                                    float(kp_numeric["kp_index"].iloc[-2])
                                    if kp_numeric.shape[0] >= 2
                                    else latest_kp
                                )
                                delta_kp = latest_kp - prev_value
                                col_kp_gauge, col_kp_chart = st.columns([1, 2])
                                with col_kp_gauge:
                                    _echarts_gauge(
                                        latest_kp,
                                        min_val=0.0,
                                        max_val=9.0,
                                        title="Kp now",
                                        unit="Kp",
                                        precision=2,
                                        thresholds=[
                                            (3.0, "#22c55e"),
                                            (5.0, "#f97316"),
                                            (7.0, "#ef4444"),
                                        ],
                                        height_px=260,
                                    )
                                    if latest_time is not None:
                                        st.caption(
                                            f"UTC timestamp: {latest_time.strftime('%Y-%m-%d %H:%M')}"
                                        )
                                    st.caption(
                                        "Geomagnetic categories: quiet ≤3 • unsettled 4 • storm ≥5.")
                                with col_kp_chart:
                                    kp_recent = kp_numeric.tail(
                                        min(120, kp_numeric.shape[0])
                                    )
                                    _echarts_sparkline(
                                        kp_recent["time_tag"].tolist(),
                                        kp_recent["kp_index"].astype(float).tolist(),
                                        title="Kp trend (selected window)",
                                        color_primary="#0ea5e9",
                                        area_colors=(
                                            "rgba(14,165,233,0.32)",
                                            "rgba(14,165,233,0.06)",
                                        ),
                                    )
                                    st.metric(
                                        "Δ since previous point",
                                        f"{delta_kp:+.2f}",
                                    )
                                    st.caption(
                                        "Recent 3-hour cadence progression of Kp highlighting short-term geomagnetic swings."
                                    )
                                stats_cols = st.columns(3)
                                now_utc = pd.Timestamp.now(tz="UTC")
                                last_24_mask = kp_numeric[
                                    "time_tag"
                                ] >= now_utc - pd.Timedelta(hours=24)
                                mean_24h = (
                                    kp_numeric.loc[last_24_mask, "kp_index"].mean()
                                    if last_24_mask.any()
                                    else kp_numeric["kp_index"]
                                    .tail(min(8, kp_numeric.shape[0]))
                                    .mean()
                                )
                                stats_cols[0].metric(
                                    "24 h mean", f"{mean_24h:.2f}")
                                stats_cols[1].metric(
                                    "Peak (window)",
                                    f"{kp_numeric['kp_index'].max():.2f}",
                                )
                                stats_cols[2].metric(
                                    "Storm counts (Kp≥5)",
                                    f"{int((kp_numeric['kp_index'] >= 5.0).sum())}",
                                )
                                daily_mean = (
                                    kp_numeric.set_index("time_tag")["kp_index"]
                                    .resample("D")
                                    .mean()
                                    .dropna()
                                )
                                if not daily_mean.empty:
                                    _echarts_multi_time_series(
                                        {"Daily mean Kp": daily_mean},
                                        title="Daily mean Kp",
                                        y_name="Kp",
                                        height_px=300,
                                    )
                                    st.caption(
                                        "Daily mean Kp derived from NOAA's 3-hour cadence values."
                                    )
                                if kp_numeric.shape[0] >= 4:
                                    st.markdown(
                                        "##### Rolling confidence interval")
                                    default_win = min(
                                        18, max(4, int(kp_numeric.shape[0] // 8))
                                    )
                                    kp_win = st.number_input(
                                        "Rolling CI window (points)",
                                        min_value=4,
                                        max_value=int(max(8, kp_numeric.shape[0])),
                                        value=int(default_win),
                                        step=1,
                                        key="kp_win",
                                    )
                                    vals = (
                                        kp_numeric["kp_index"]
                                        .astype(float)
                                        .reset_index(drop=True)
                                    )
                                    minp = max(3, int(kp_win // 2))
                                    roll_mean = vals.rolling(
                                        int(kp_win), min_periods=minp
                                    ).mean()
                                    roll_std = vals.rolling(
                                        int(kp_win), min_periods=minp
                                    ).std(ddof=1)
                                    roll_n = vals.rolling(
                                        int(kp_win), min_periods=minp
                                    ).count()
                                    se = roll_std / np.sqrt(roll_n)
                                    low = roll_mean - 1.96 * se
                                    high = roll_mean + 1.96 * se
                                    _echarts_time_with_ci(
                                        kp_numeric["time_tag"].tolist(),
                                        vals.tolist(),
                                        low.tolist(),
                                        high.tolist(),
                                        title="Kp rolling 95% confidence interval",
                                        y_name="Kp",
                                        series_name="Kp",
                                    )
                                    st.caption(
                                        "Shaded band shows rolling mean ±1.96·SE, contextualising Kp variability around the moving average."
                                    )
                                else:
                                    st.info(
                                        "Not enough Kp samples to build a rolling confidence interval."
                                    )
                            else:
                                st.info(
                                    "Kp values are not available in the NOAA feed.")
                        else:
                            st.info("Kp data currently unavailable.")

            if donki_state.get("loaded"):
                start_cov = donki_state.get("start_date", "")
                end_cov = donki_state.get("end_date", "")
                st.markdown("#### NASA DONKI event summary")
                if start_cov and end_cov:
                    st.caption(f"DONKI coverage: {start_cov} → {end_cov} (UTC)")
                errors = donki_state.get("errors", {})
                for code, msg in errors.items():
                    title = DONKI_ENDPOINTS.get(code, {}).get("title", code)
                    st.warning(f"{title}: {msg}")
                donki_summary = donki_state.get("summary", pd.DataFrame())
                if donki_summary.empty:
                    st.info("No DONKI events returned for the selected window.")
                else:
                    st.dataframe(donki_summary)
                    if "events" in donki_summary.columns:
                        st.markdown("##### DONKI event gauges")
                        max_events = float(
                            max(1, int(donki_summary["events"].max())))
                        gauge_cols = st.columns(3)
                        for idx, row in donki_summary.iterrows():
                            with gauge_cols[idx % 3]:
                                event_title = str(row.get("event_type", "Event"))
                                event_count = float(row.get("events", 0.0))
                                _echarts_gauge(
                                    event_count,
                                    min_val=0.0,
                                    max_val=max_events * 1.2,
                                    title=event_title,
                                    formatter="{value:.0f}",
                                    thresholds=[
                                        (max_events * 0.33, "#22c55e"),
                                        (max_events * 0.66, "#facc15"),
                                        (max_events * 1.0, "#ef4444"),
                                    ],
                                )
                                st.caption(
                                    f"{event_title}: {int(event_count)} events in the selected DONKI period."
                                )
                daily_counts = donki_state.get("daily_counts", {})
                if daily_counts:
                    _echarts_multi_time_series(
                        daily_counts,
                        title="DONKI events per day",
                        y_name="events",
                    )
                    st.caption(
                        "Aggregated daily DONKI events grouped by endpoint for the selected window."
                    )
                with st.expander("View raw NASA DONKI datasets"):
                    for code, df in donki_state.get("datasets", {}).items():
                        title = DONKI_ENDPOINTS.get(code, {}).get("title", code)
                        st.markdown(f"**{title}** — {df.shape[0]} rows")
                        st.dataframe(df.head(200))
                        time_columns = _get_donki_time_columns(code)
                        timestamps = _collect_donki_times(df, time_columns)
                        if not timestamps.empty:
                            daily_series = (
                                timestamps.dt.floor("D").value_counts().sort_index())
                            daily_series.index = pd.to_datetime(
                                daily_series.index, utc=True, errors="coerce"
                            )
                            daily_series = daily_series[daily_series.index.notna()]
                            if not daily_series.empty:
                                _echarts_multi_time_series(
                                    {title: daily_series},
                                    title=f"{title} events per day",
                                    y_name="events",
                                    height_px=260,
                                )
                                st.caption(
                                    f"{title}: daily event counts over the cached DONKI window.")
                        else:
                            st.caption(
                                "No timestamped entries available for plotting.")
            elif NASA_API_KEY:
                st.info(
                    "Click 'Fetch NASA DONKI events' to populate NASA space weather datasets."
                )
            else:
                st.info(
                    "Set NASA_API_KEY in your environment to enable NASA DONKI analytics."
                )

            if space_state.get("loaded"):
                st.markdown("#### Inspect an additional SWPC feed (on-demand)")
                selected_dataset = st.selectbox(
                    "SWPC endpoint",
                    list(SWPC_EXTRA_DATASETS.keys()),
                    key="space_data_swpc_extra_select",
                    help="This does not fetch automatically. Click Fetch to load the selected feed.",
                )
                extra_state = st.session_state.setdefault(
                    "space_data_swpc_extra_state",
                    {
                        "selected_dataset": "",
                        "fetched_at_utc": "",
                        "row_count": 0,
                        "col_count": 0,
                        "df_tail": pd.DataFrame(),
                        "error": "",
                    },
                )
                col_fetch_extra, col_meta_extra = st.columns([1, 3])
                with col_fetch_extra:
                    fetch_extra_clicked = st.button(
                        "📥 Fetch selected feed",
                        key="space_data_swpc_extra_fetch",
                        help="Fetches only when clicked (cached for 5 min).",
                    )
                with col_meta_extra:
                    st.caption("No auto-fetch on tab switch. Fetch is on-demand.")

                if fetch_extra_clicked and selected_dataset:
                    try:
                        with st.spinner(f"Fetching {selected_dataset}…"):
                            extra_df = _fetch_swpc_dataset(
                                SWPC_EXTRA_DATASETS[selected_dataset]
                            )
                        extra_state["selected_dataset"] = str(selected_dataset)
                        extra_state["fetched_at_utc"] = pd.Timestamp.utcnow().strftime(
                            "%Y-%m-%d %H:%M UTC"
                        )
                        extra_state["row_count"] = int(extra_df.shape[0])
                        extra_state["col_count"] = int(extra_df.shape[1])
                        # Keep session state bounded: store only a tail slice.
                        extra_state["df_tail"] = extra_df.tail(200).copy()
                        extra_state["error"] = ""
                    except requests.RequestException as exc:
                        extra_state["selected_dataset"] = str(selected_dataset)
                        extra_state["fetched_at_utc"] = pd.Timestamp.utcnow().strftime(
                            "%Y-%m-%d %H:%M UTC"
                        )
                        extra_state["row_count"] = 0
                        extra_state["col_count"] = 0
                        extra_state["df_tail"] = pd.DataFrame()
                        extra_state["error"] = f"Failed to retrieve feed: {exc}"
                    except ValueError as exc:
                        extra_state["selected_dataset"] = str(selected_dataset)
                        extra_state["fetched_at_utc"] = pd.Timestamp.utcnow().strftime(
                            "%Y-%m-%d %H:%M UTC"
                        )
                        extra_state["row_count"] = 0
                        extra_state["col_count"] = 0
                        extra_state["df_tail"] = pd.DataFrame()
                        extra_state["error"] = f"Unexpected response: {exc}"

                with st.expander("Latest fetched feed (session)", expanded=False):
                    clear_extra_clicked = st.button(
                        "🧹 Clear fetched feed",
                        key="space_data_swpc_extra_clear",
                        help="Clears the stored tail slice (does not delete on-disk caches).",
                    )
                    if clear_extra_clicked:
                        extra_state["selected_dataset"] = ""
                        extra_state["fetched_at_utc"] = ""
                        extra_state["row_count"] = 0
                        extra_state["col_count"] = 0
                        extra_state["df_tail"] = pd.DataFrame()
                        extra_state["error"] = ""
                        st.success("Cleared fetched feed from session.")

                    if (
                        extra_state.get("selected_dataset") != str(selected_dataset)
                        or (
                            isinstance(extra_state.get("df_tail"), pd.DataFrame)
                            and extra_state.get("df_tail", pd.DataFrame()).empty
                            and not str(extra_state.get("error") or "").strip()
                        )
                    ):
                        st.info("Click **Fetch selected feed** to load the selected SWPC dataset.")
                    else:
                        if str(extra_state.get("error") or "").strip():
                            st.error(str(extra_state.get("error")))
                        else:
                            df_tail = extra_state.get("df_tail", pd.DataFrame())
                            st.caption(
                                f"Fetched: {extra_state.get('fetched_at_utc','')} | "
                                f"Rows: {int(extra_state.get('row_count', 0))} | "
                                f"Cols: {int(extra_state.get('col_count', 0))} | "
                                f"Showing last {int(df_tail.shape[0])} rows"
                            )
                            st.dataframe(df_tail, use_container_width=True, hide_index=True)

                with st.expander("SpaceWeatherLive snapshot (scrape + OpenAI fallback)"):
                    if st.button(
                        "Fetch SpaceWeatherLive data",
                            key="btn_fetch_swl"):
                        snap = None
                        try:
                            snap = fetch_spaceweatherlive_snapshot()
                        except Exception as exc:
                            st.warning(
                                f"Direct scrape failed ({exc}); attempting OpenAI fallback…")
                            try:
                                home_html = requests.get(
                                    "https://www.spaceweatherlive.com/", timeout=12
                                ).text
                                solar_html = requests.get(
                                    "https://www.spaceweatherlive.com/en/solar-activity.html", timeout=12, ).text
                                cme_html = requests.get(
                                    "https://www.spaceweatherlive.com/en/solar-activity/latest-cmes.html",
                                    timeout=12,
                                ).text
                                ursigram_html = requests.get(
                                    "https://www.spaceweatherlive.com/en/reports/sidc-ursigram.html",
                                    timeout=12,
                                ).text
                                snap = extract_spaceweather_with_openai(
                                    {
                                        "home": home_html,
                                        "solar_activity": solar_html,
                                        "latest_cmes": cme_html,
                                        "sidc_ursigram": ursigram_html,
                                    }
                                )
                            except Exception as e2:
                                snap = None
                                st.error(f"OpenAI fallback failed: {e2}")
                        if snap:
                            _update_spaceweatherlive_state(space_state, snap)
                            st.caption(
                                "SpaceWeatherLive snapshot stored for correlation and modeling pipelines."
                            )
                            col_a, col_b, col_c, col_d = st.columns(4)
                            with col_a:
                                val = snap.solar_wind_speed_kms
                                if val is not None:
                                    st.metric(
                                        "Solar wind speed",
                                        f"{val:.0f} km/s",
                                    )
                                else:
                                    st.caption("Solar wind speed: n/a")
                            with col_b:
                                val = snap.solar_wind_density_pcc
                                if val is not None:
                                    st.metric(
                                        "Solar wind density",
                                        f"{val:.1f} p/cm³",
                                    )
                                else:
                                    st.caption("Solar wind density: n/a")
                            with col_c:
                                val = snap.imf_bt_nt
                                if val is not None:
                                    st.metric("IMF Bt", f"{val:.1f} nT")
                                else:
                                    st.caption("IMF Bt: n/a")
                            with col_d:
                                val = snap.imf_bz_nt
                                if val is not None:
                                    st.metric("IMF Bz", f"{val:.1f} nT")
                                else:
                                    st.caption("IMF Bz: n/a")

                            col_e, col_f, col_g = st.columns(3)
                            with col_e:
                                if snap.sunspot_number is not None:
                                    st.metric("Sunspot number",
                                              f"{int(snap.sunspot_number)}")
                                else:
                                    st.caption("Sunspot number: n/a")
                            with col_f:
                                if snap.f107_flux is not None:
                                    st.metric(
                                        "F10.7 cm flux",
                                        f"{snap.f107_flux:.1f} sfu",
                                    )
                                else:
                                    st.caption("F10.7 cm flux: n/a")
                            with col_g:
                                fp = snap.flare_probabilities
                                if any(
                                    val is not None
                                    for val in (
                                        fp.c_class_pct,
                                        fp.m_class_pct,
                                        fp.x_class_pct,
                                    )
                                ):
                                    st.metric(
                                        "Flare probability (C/M/X)",
                                        f"{(fp.c_class_pct or 0):.0f}% / {(fp.m_class_pct or 0):.0f}% / {(fp.x_class_pct or 0):.0f}%",
                                    )
                                else:
                                    st.caption("Flare probabilities: n/a")

                            if snap.cme_records:
                                cme_stats = snap.cme_velocity_stats()
                                count_val = float(cme_stats.get("count") or 0)
                                count_max = max(5.0, count_val * 1.4 + 1.0)
                                median_val = cme_stats.get("median")
                                max_val = cme_stats.get("max")
                                velocity_ceiling = 400.0
                                if isinstance(max_val, (int, float)):
                                    velocity_ceiling = max(
                                        velocity_ceiling, float(max_val) * 1.1 + 50.0)
                                elif isinstance(median_val, (int, float)):
                                    velocity_ceiling = max(
                                        velocity_ceiling, float(median_val) * 1.5 + 50.0)
                                cme_cols = st.columns(3)
                                with cme_cols[0]:
                                    _echarts_gauge(
                                        count_val,
                                        min_val=0.0,
                                        max_val=count_max,
                                        title="CACTus CME count",
                                        formatter="{value:.0f}",
                                        thresholds=[
                                            (count_max * 0.33, "#22c55e"),
                                            (count_max * 0.66, "#facc15"),
                                            (count_max, "#ef4444"),
                                        ],
                                    )
                                    st.caption(
                                        f"Detections parsed: {int(count_val)} (latest table)."
                                    )
                                with cme_cols[1]:
                                    if isinstance(median_val, (int, float)):
                                        _echarts_gauge(
                                            float(median_val),
                                            min_val=0.0,
                                            max_val=velocity_ceiling,
                                            title="Median CME speed (km/s)",
                                            formatter="{value:.0f}",
                                            thresholds=[
                                                (velocity_ceiling * 0.33, "#22c55e"),
                                                (velocity_ceiling * 0.66, "#facc15"),
                                                (velocity_ceiling, "#ef4444"),
                                            ],
                                        )
                                        st.caption(
                                            f"Median speed across detections: {median_val:.0f} km/s."
                                        )
                                    else:
                                        st.caption("Median CME speed: n/a")
                                with cme_cols[2]:
                                    if isinstance(max_val, (int, float)):
                                        _echarts_gauge(
                                            float(max_val),
                                            min_val=0.0,
                                            max_val=velocity_ceiling,
                                            title="Fastest CME (km/s)",
                                            formatter="{value:.0f}",
                                            thresholds=[
                                                (velocity_ceiling * 0.33, "#22c55e"),
                                                (velocity_ceiling * 0.66, "#facc15"),
                                                (velocity_ceiling, "#ef4444"),
                                            ],
                                        )
                                        st.caption(
                                            f"Peak speed among listed CMEs: {max_val:.0f} km/s."
                                        )
                                    else:
                                        st.caption("Peak CME speed: n/a")
                                cme_rows: List[Dict[str, object]] = []
                                for entry in snap.cme_records[:15]:
                                    cme_rows.append(
                                        {
                                            "CME ID": entry.cactus_id,
                                            "Onset (UTC)": (
                                                entry.onset_time_utc.isoformat().replace(
                                                    "+00:00",
                                                    "Z") if entry.onset_time_utc else None),
                                            "Duration (h)": entry.duration_hours,
                                            "Position angle (°)": entry.position_angle_deg,
                                            "Angular width (°)": entry.angular_width_deg,
                                            "Velocity (km/s)": entry.velocity_kms,
                                            "Velocity variation": entry.velocity_variation_kms,
                                            "Velocity min": entry.velocity_min_kms,
                                            "Velocity max": entry.velocity_max_kms,
                                            "Halo": entry.halo_class,
                                        })
                                if cme_rows:
                                    st.dataframe(pd.DataFrame(cme_rows))
                            else:
                                st.caption("CACTus CME detections: n/a")

                            if snap.sidc_report and (
                                snap.sidc_report.bulletin_excerpt
                                or snap.sidc_report.cme_highlights
                            ):
                                with st.expander("SIDC Ursigram highlights (CME context)"):
                                    if snap.sidc_report.issued_utc:
                                        st.caption(
                                            f"Issued: {snap.sidc_report.issued_utc.strftime('%Y-%m-%d %H:%M UTC')}"
                                        )
                                    if snap.sidc_report.cme_highlights:
                                        st.markdown(
                                            f"**CME highlights:** {snap.sidc_report.cme_highlights}"
                                        )
                                    if snap.sidc_report.bulletin_excerpt:
                                        st.write(snap.sidc_report.bulletin_excerpt)

                            if snap.kp_forecast:
                                kp_rows = [
                                    {
                                        "Day": k.day_label,
                                        "Min Kp": k.min_kp,
                                        "Max Kp": k.max_kp,
                                    }
                                    for k in snap.kp_forecast
                                ]
                                kp_df_view = pd.DataFrame(kp_rows)
                                st.dataframe(kp_df_view)
                            st.caption(
                                "Source: SpaceWeatherLive — scraped UI snapshot; if scraping failed, values were extracted by OpenAI from the page HTML."
                            )
                        else:
                            st.info("No SpaceWeatherLive data available.")

            st.markdown("### Correlations (disabled in Space Data)")
            st.info(
                "This Space Data dashboard is intentionally **data-only**. "
                "HRV↔space-weather correlations/ML have been decommissioned to keep this tab stable and independent."
            )
            _DECOMMISSIONED_SPACE_WEATHER_CORR_BLOCK = '''
            st.markdown("### HRV window metrics vs. planetary K-index")
            st.caption(
                "Align HRV windows to expected arrival by applying a time lag before merging."
            )
            lag_min, lag_max = st.slider(
                "Lag range (hours, applied to Kp times)",
                -48,
                48,
                (-12, 12),
                step=1,
                key="sw_kp_lag_range_hours",
            )
            lag_step = st.number_input(
                "Lag step (hours)",
                min_value=1,
                max_value=12,
                value=3,
                step=1,
                key="sw_kp_lag_step_hours",
            )
            merge_tol = st.number_input(
                "Merge tolerance (minutes)",
                min_value=15,
                max_value=360,
                value=90,
                step=15,
                key="sw_kp_merge_tolerance_min",
            )
            cedula = st.text_input(
                "Cedula (identification number)",
                value="",
                placeholder="e.g., 12345678",
                key="sw_kp_cedula",
            )
            use_weather = st.checkbox(
                "Include weather covariates (Bogotá) for partial correlations",
                value=False,
                help="Fetches weather data from Open-Meteo API. Uncheck for faster loading.",
                key="sw_kp_include_weather_covariates",
            )

            lags = list(range(int(lag_min), int(lag_max) + 1, int(lag_step)))
            if not lags:
                lags = [0]

            # Use cached HRV windowed results if a rerun cleared the in-memory frame.
            corr_windowed_df = (
                windowed_df
                if not windowed_df.empty
                else st.session_state.get("_hrv_cached_windowed_df", pd.DataFrame())
            )
            corr_metric_list: List[str] = _select_hrv_metric_columns(
                corr_windowed_df, exclude=("kp_index",)
            )

            # Ensure Kp data is available (cache-only; never auto-fetch network on tab render)
            if (kp_df.empty or "kp_index" not in kp_df.columns) and not kp_error:
                cached_kp = _read_dataframe_cache(
                    SPACE_WEATHER_CACHE_DIR / f"kp_index_{int(SPACE_WEATHER_MAX_DAYS)}.json",
                    max_age=None,
                )
                if isinstance(cached_kp, pd.DataFrame) and not cached_kp.empty:
                    kp_df = cached_kp
                else:
                    kp_error = (
                        "No cached Kp data available. Click '📥 Fetch space weather' above to download."
                    )
                    kp_df = pd.DataFrame()

            # Check prerequisites before showing compute button
            can_compute_corr = (
                not corr_windowed_df.empty
                and "start" in corr_windowed_df.columns
                and bool(corr_metric_list)
                and not kp_error
                and not kp_df.empty
                and "kp_index" in kp_df.columns
            )

            # Show cached results (persist across tab switches/reruns).
            _stored_kp_corr = st.session_state.get("space_weather_kp_corr_cache")
            try:
                _stored_sig = tuple((_stored_kp_corr or {}).get("scope_upload_signature", []))
            except Exception:
                _stored_sig = tuple()
            _stored_user = str((_stored_kp_corr or {}).get("scope_user_id", "") or "")
            _current_user = str(active_user_id or "")
            _has_stored = (
                isinstance(_stored_kp_corr, dict)
                and _stored_user == _current_user
                and _stored_sig == upload_signature
                and isinstance(_stored_kp_corr.get("corr_best"), pd.DataFrame)
                and isinstance(_stored_kp_corr.get("corr_full"), pd.DataFrame)
            )
            if _has_stored:
                with st.expander("✅ Last computed HRV ↔ Kp correlations (saved for this session)", expanded=True):
                    st.caption(
                        f"Computed: {_stored_kp_corr.get('computed_at_utc', 'unknown')} | "
                        f"Merge tolerance: {_stored_kp_corr.get('params', {}).get('merge_tol_minutes', '?')} min | "
                        f"Weather covariates: {_stored_kp_corr.get('params', {}).get('use_weather', False)}"
                    )
                    if _stored_kp_corr["corr_full"].empty:
                        st.info("Last run produced no lagged correlations for the current configuration.")
                    else:
                        st.subheader("Best correlation per metric (by |r|)")
                        st.dataframe(_stored_kp_corr["corr_best"])
                        st.download_button(
                            "⬇️ Download full correlation table (CSV)",
                            data=_stored_kp_corr["corr_full"].to_csv(index=False).encode("utf-8"),
                            file_name="hrv_kp_correlations.csv",
                            mime="text/csv",
                            key="download_kp_corr_full_cached",
                        )
                        st.download_button(
                            "⬇️ Download top correlations (CSV)",
                            data=_stored_kp_corr["corr_best"].to_csv(index=False).encode("utf-8"),
                            file_name="hrv_kp_correlations_top.csv",
                            mime="text/csv",
                            key="download_kp_corr_best_cached",
                        )
                    if st.button(
                        "🧹 Clear saved correlation results",
                        key="clear_kp_corr_cache",
                        help="Removes saved results so the panel is cleared on the next rerun.",
                    ):
                        st.session_state.pop("space_weather_kp_corr_cache", None)
                        export_store = st.session_state.get("space_weather_export", {})
                        if isinstance(export_store, dict):
                            export_store.pop("corr_full", None)
                            export_store.pop("corr_best", None)
                            st.session_state["space_weather_export"] = export_store
                        st.rerun()

            if corr_windowed_df.empty:
                info_col, action_col = st.columns([0.65, 0.35])
                with info_col:
                    st.info("Run the HRV window analysis to enable correlations.")
                with action_col:
                    trigger_hrv_corr = st.button(
                        "Run HRV window analysis",
                        key="sw_trigger_hrv_kp_corr",
                        help="Compute HRV windowed metrics to unlock Space Weather correlations.",
                    )
                if trigger_hrv_corr:
                    if not has_hrv_data_uploaded:
                        st.warning("Upload HRV data first, then run the HRV analysis.")
                    else:
                        st.session_state["auto_run_hrv_analysis"] = True
                        st.session_state.pop("hrv_analysis_complete_signature", None)
                        st.rerun()
            elif "start" not in corr_windowed_df.columns:
                st.info("Windowed HRV data does not include start timestamps.")
            elif not corr_metric_list:
                st.info("No numeric HRV metrics available for correlation.")
            elif kp_error or kp_df.empty or "kp_index" not in kp_df.columns:
                st.info("Planetary K-index data not available for correlation. Click 'Fetch space weather data' first.")
        
            # Add explicit button to compute correlations (avoids automatic computation on tab render)
            compute_corr_clicked = st.button(
                "🔬 Compute HRV-Kp Correlations",
                key="compute_hrv_kp_corr",
                disabled=not can_compute_corr,
                help="Calculates lagged correlations between HRV metrics and planetary K-index",
            )
        
            if can_compute_corr and compute_corr_clicked:
                gpu_info = get_gpu_info()
                st.caption(
                    f"Compute context — GPU available: **{gpu_info.available}** ({gpu_info.device_name}); "
                    f"compute runs on CPU; CuPy used only for CUDA-ready array ops."
                )
                windowed_for_corr = corr_windowed_df.copy()
                # optional weather covariates fetched for time span of HRV windows
                cov_df = pd.DataFrame()
                covariate_cols: List[str] = []
                if use_weather:
                    start_dt = pd.to_datetime(
                        windowed_for_corr["start"], errors="coerce", utc=True
                    ).dropna()
                    if not start_dt.empty:
                        span_min = start_dt.min().date().isoformat()
                        span_max = start_dt.max().date().isoformat()
                        try:
                            with st.spinner("Fetching weather data..."):
                                cov_df = fetch_open_meteo_hourly(span_min, span_max)
                        except requests.RequestException as exc:
                            st.warning(f"Weather API error: {exc}")
                    if not cov_df.empty:
                        start_index = pd.to_datetime(
                            windowed_for_corr["start"], errors="coerce", utc=True
                        )
                        cov_df = cov_df.copy()
                        if cov_df["weather_time"].dt.tz is None:
                            cov_df["weather_time"] = cov_df["weather_time"].dt.tz_localize(
                                "UTC"
                            )
                        else:
                            cov_df["weather_time"] = cov_df["weather_time"].dt.tz_convert(
                                "UTC"
                            )

                        value_columns = [
                            c
                            for c in [
                                "temp_c",
                                "rh_pct",
                                "pressure_hpa",
                                "wind_ms",
                                "precip_mm",
                                "cloudcover_pct",
                            ]
                            if c in cov_df.columns
                        ]
                        cov_aligned = align_space_weather_columns(
                            reference_times=start_index,
                            predictor_df=cov_df,
                            predictor_time_col="weather_time",
                            value_columns=value_columns,
                            max_gap_minutes=int(merge_tol),
                        )
                        if not cov_aligned.empty:
                            cov_aligned = cov_aligned.rename_axis("_align_time")
                            covariate_cols = list(cov_aligned.columns)
                            windowed_for_corr = (
                                windowed_for_corr.assign(_align_time=start_index)
                                .set_index("_align_time")
                                .join(cov_aligned, how="left")
                                .reset_index(drop=True)
                            )

                with st.spinner("Computing correlations..."):
                    corr_start = time.perf_counter()
                    lag_results = _scan_lag_correlations(
                        windowed_for_corr,
                        kp_df,
                        corr_metric_list,
                        lags,
                        merge_tolerance_minutes=int(merge_tol),
                        covariate_cols=covariate_cols or None,
                    )
                    corr_duration = (time.perf_counter() - corr_start) * 1000.0
                if covariate_cols:
                    st.caption(
                        "Weather covariates (%s) were included via partial correlations."
                        % ", ".join(covariate_cols)
                    )
                if lag_results.empty:
                    st.info(
                        "No lagged correlations could be computed with current data.")
                    st.session_state["space_weather_kp_corr_cache"] = {
                        "scope_user_id": str(active_user_id or ""),
                        "scope_upload_signature": list(upload_signature),
                        "computed_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                        "params": {
                            "lags": list(lags),
                            "merge_tol_minutes": int(merge_tol),
                            "use_weather": bool(use_weather),
                            "metrics": list(corr_metric_list),
                        },
                        "corr_full": lag_results.copy(),
                        "corr_best": pd.DataFrame(),
                    }
                else:
                    st.caption(f"Correlation computation time: {corr_duration:.0f} ms")
                    if (
                        "p_value" in lag_results.columns
                        and lag_results["p_value"].notna().any()
                    ):
                        qvals, crit = fdr_bh(
                            lag_results["p_value"].fillna(1.0).to_numpy(), alpha=0.05)
                        lag_results["q_value"] = qvals
                    else:
                        lag_results["q_value"] = np.nan

                    if "pearson_r" in lag_results.columns:
                        idx = lag_results.groupby("metric")["pearson_r"].apply(
                            lambda s: s.abs().idxmax()
                        )
                        if isinstance(idx, pd.Series):
                            best_rows = lag_results.loc[idx.values].copy()
                        else:
                            best_rows = lag_results.copy()
                        best_rows = best_rows.sort_values(
                            "pearson_r",
                            key=lambda s: s.abs(),
                            ascending=False,
                            ignore_index=True,
                        )
                    else:
                        best_rows = lag_results.copy()

                    st.subheader("Best correlation per metric (by |r|)")
                    st.dataframe(
                        best_rows.sort_values(
                            "pearson_r", key=lambda s: s.abs(), ascending=False
                        )
                    )
                    # Persist for exports (merge to preserve prior ML results)
                    export_store = st.session_state.get("space_weather_export", {})
                    export_store["corr_full"] = lag_results.copy()
                    export_store["corr_best"] = best_rows.copy()
                    st.session_state["space_weather_export"] = export_store
                    st.session_state["space_weather_kp_corr_cache"] = {
                        "scope_user_id": str(active_user_id or ""),
                        "scope_upload_signature": list(upload_signature),
                        "computed_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                        "params": {
                            "lags": list(lags),
                            "merge_tol_minutes": int(merge_tol),
                            "use_weather": bool(use_weather),
                            "metrics": list(corr_metric_list),
                        },
                        "corr_full": lag_results.copy(),
                        "corr_best": best_rows.copy(),
                    }
                    # Export correlation tables
                    st.download_button(
                        "⬇️ Download full correlation table (CSV)",
                        data=lag_results.to_csv(index=False).encode("utf-8"),
                        file_name="hrv_kp_correlations.csv",
                        mime="text/csv",
                        key="download_kp_corr_full",
                    )
                    st.download_button(
                        "⬇️ Download top correlations (CSV)",
                        data=best_rows.to_csv(index=False).encode("utf-8"),
                        file_name="hrv_kp_correlations_top.csv",
                        mime="text/csv",
                        key="download_kp_corr_best",
                    )
                    # Optional bootstrap/permutation for strongest finding
                    with st.expander("Advanced inference (bootstrap/permutation)", expanded=False):
                        do_boot_perm = st.checkbox(
                            "Compute block bootstrap CI and permutation p for top finding",
                            value=False,
                            help="Block bootstrap (8-sample blocks, 200 reps) and permutation p (200 reps) on the top |r| row.",
                        )
                        if do_boot_perm and not best_rows.empty:
                            top = best_rows.iloc[0]
                            boot = _compute_bootstrap_perm_for_best(
                                windowed_df,
                                kp_df,
                                predictor_time_col="time_tag",
                                predictor_value_col="kp_index",
                                metric=str(top.get("metric", "")),
                                lag_hours=int(top.get("lag_hours", 0)),
                                merge_tolerance_minutes=int(merge_tol),
                            )
                            st.markdown(
                                f"- Block bootstrap CI95: [{boot.get('boot_low', float('nan')):.3f}, "
                                f"{boot.get('boot_high', float('nan')):.3f}]"
                            )
                            st.markdown(
                                f"- Permutation p (two-sided): {_format_p_value(boot.get('perm_p', float('nan')))}"
                            )
                    # ML pattern recognition block
                    st.subheader("ML pattern recognition (HRV ~ space-weather lags)")
                    target_metric = st.selectbox(
                        "Select HRV metric to model",
                        options=metric_list,
                        key="kp_ml_target_metric",
                    )
                    predictor_choices = list(bundles.keys()) if bundles else []
                    default_predictors = [
                        key
                        for key in predictor_choices
                        if key in ("planetary_k_index_3h", "dst_index", "f10_7_cm_flux")
                    ]
                    predictors_selected = st.multiselect(
                        "Predictors (NOAA feeds)",
                        options=predictor_choices,
                        default=default_predictors if default_predictors else predictor_choices[:1],
                        format_func=lambda k: option_labels.get(k, k),
                        help="Builds lagged feature matrix across selected predictors (e.g., Kp, Dst, F10.7, solar wind).",
                        key="space_weather_predictors_ml",
                    )
                    _ensure_ml_libs()
                    ml_button_text = "Run ML models (ElasticNet + RandomForest"
                    if XGBOOST_AVAILABLE:
                        ml_button_text += " + XGBoost"
                    if LIGHTGBM_AVAILABLE:
                        ml_button_text += " + LightGBM"
                    ml_button_text += ")"
                    if st.button(ml_button_text, key="run_ml_space_weather"):
                        try:
                            with st.spinner("Training ML models..."):
                                ml_start = time.perf_counter()
                                feature_df = _build_space_weather_feature_matrix(
                                    windowed_df,
                                    bundles,
                                    predictors_selected,
                                    lags,
                                    merge_tolerance_minutes=int(merge_tol),
                                )
                                feature_df[target_metric] = windowed_df[target_metric]
                                ml_results = _run_ml_models_space_weather(
                                    feature_df,
                                    target_metric=target_metric,
                                )
                                ml_duration = (time.perf_counter() - ml_start) * 1000.0
                            st.markdown(
                                f"- Samples used: **{ml_results.get('samples', 0)}** | "
                                f"Features: **{ml_results.get('features', 0)}**"
                            )
                            st.caption(f"ML training time: {ml_duration:.0f} ms (CPU)")
                        
                            # Display model metrics in columns
                            enet = ml_results.get("elastic_net", {})
                            rf = ml_results.get("random_forest", {})
                            xgb = ml_results.get("xgboost", {})
                            lgbm = ml_results.get("lightgbm", {})
                            gb = ml_results.get("gradient_boosting", {})
                            lasso = ml_results.get("lasso", {})
                        
                            # Show available models
                            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                            with col_m1:
                                st.metric(
                                    "ElasticNet R²",
                                    f"{enet.get('r2', float('nan')):.3f}",
                                    help=f"MAE = {enet.get('mae', float('nan')):.3f}; "
                                    f"alpha={enet.get('alpha','n/a')}, l1={enet.get('l1_ratio','n/a')}",
                                )
                            with col_m2:
                                st.metric(
                                    "RandomForest R²",
                                    f"{rf.get('r2', float('nan')):.3f}",
                                    help=f"MAE = {rf.get('mae', float('nan')):.3f}",
                                )
                            with col_m3:
                                if xgb and "r2" in xgb:
                                    st.metric(
                                        "XGBoost R²",
                                        f"{xgb.get('r2', float('nan')):.3f}",
                                        help=f"MAE = {xgb.get('mae', float('nan')):.3f}",
                                    )
                                else:
                                    st.metric("XGBoost R²", "N/A", help="Install: pip install xgboost")
                            with col_m4:
                                if lgbm and "r2" in lgbm:
                                    st.metric(
                                        "LightGBM R²",
                                        f"{lgbm.get('r2', float('nan')):.3f}",
                                        help=f"MAE = {lgbm.get('mae', float('nan')):.3f}",
                                    )
                                else:
                                    st.metric("LightGBM R²", "N/A", help="Install: pip install lightgbm")
                        
                            imps = ml_results.get("feature_importances", [])
                            shap_imps = ml_results.get("shap_importances", [])
                            if "space_weather_export" not in st.session_state:
                                st.session_state["space_weather_export"] = {}
                        
                            # Feature importances tabs
                            if imps or shap_imps:
                                tab1, tab2 = st.tabs(["Permutation Importance", "SHAP Values"])
                                with tab1:
                                    if imps:
                                        imp_df = pd.DataFrame(imps).head(8)
                                        st.markdown("Top feature importances (RandomForest, permutation)")
                                        st.dataframe(imp_df, use_container_width=True)
                                        st.session_state["space_weather_export"]["ml_importances"] = imp_df.copy()
                                    else:
                                        st.info("Permutation importance not available")
                                with tab2:
                                    if shap_imps:
                                        shap_df = pd.DataFrame(shap_imps).head(8)
                                        st.markdown("Top feature importances (SHAP - mean |SHAP value|)")
                                        st.dataframe(shap_df, use_container_width=True)
                                        st.caption(
                                            f"SHAP base value (expected prediction): {ml_results.get('shap_base_value', 'N/A'):.3f}"
                                        )
                                        st.session_state["space_weather_export"]["shap_importances"] = shap_df.copy()
                                    else:
                                        if ml_results.get("shap_available", False):
                                            st.info("SHAP computation completed but no importances available")
                                        else:
                                            st.info("SHAP not available. Install: pip install shap")
                            else:
                                st.info("Feature importances not available")
                        
                            # Export ML summaries
                            model_rows = [
                                {"model": "elastic_net", **enet},
                                {"model": "random_forest", **rf},
                                {"model": "lasso", **lasso},
                                {"model": "gradient_boosting", **gb},
                            ]
                            if xgb and "r2" in xgb:
                                model_rows.append({"model": "xgboost", **xgb})
                            if lgbm and "r2" in lgbm:
                                model_rows.append({"model": "lightgbm", **lgbm})
                            models_df = pd.DataFrame(model_rows)
                            st.download_button(
                                "⬇️ Download ML metrics (CSV)",
                                data=models_df.to_csv(index=False).encode("utf-8"),
                                file_name="hrv_space_weather_ml_metrics.csv",
                                mime="text/csv",
                                key="download_ml_metrics",
                            )
                            if imps:
                                st.download_button(
                                    "⬇️ Download feature importances (CSV)",
                                    data=imp_df.to_csv(index=False).encode("utf-8"),
                                    file_name="hrv_space_weather_feature_importances.csv",
                                    mime="text/csv",
                                    key="download_ml_importances",
                                )
                            st.session_state["space_weather_export"]["ml_metrics"] = models_df.copy()
                        except Exception as exc:  # noqa: BLE001
                            st.warning(f"ML run skipped: {exc}")
                    if not best_rows.empty and "pearson_r" in best_rows.columns:
                        top_row = best_rows.iloc[0]
                        abs_r = float(abs(top_row.get("pearson_r", 0.0)))
                        lag_hours_top = int(top_row.get("lag_hours", 0))
                        p_val_top = (
                            float(top_row.get("p_value", np.nan))
                            if "p_value" in top_row
                            else float("nan")
                        )
                        q_val_top = (
                            float(top_row.get("q_value", np.nan))
                            if "q_value" in top_row
                            else float("nan")
                        )
                        n_top = int(top_row.get("n", 0))
                        metric_name = str(top_row.get("metric", ""))
                        sign_dir = (
                            "positive"
                            if float(top_row.get("pearson_r", 0.0)) >= 0
                            else "negative"
                        )
                        lag_description = (
                            "Geomagnetic activity (Kp) precedes HRV changes"
                            if lag_hours_top > 0
                            else (
                                "HRV changes precede geomagnetic activity"
                                if lag_hours_top < 0
                                else "Simultaneous relationship"
                            )
                        )
                        lag_span = max(1.0, float(max(abs(val)
                                                      for val in lags)) if lags else 1.0)
                        col_g1, col_g2, col_g3, col_g4 = st.columns(4)
                        with col_g1:
                            _echarts_gauge(
                                abs_r,
                                min_val=0.0,
                                max_val=1.0,
                                title=f"|r| — {metric_name}",
                                formatter="{value:.2f}",
                                thresholds=[
                                    (0.2, "#f97316"),
                                    (0.4, "#facc15"),
                                    (0.6, "#4ade80"),
                                    (1.0, "#16a34a"),
                                ],
                            )
                        with col_g2:
                            if np.isfinite(q_val_top):
                                _echarts_gauge(
                                    q_val_top,
                                    min_val=0.0,
                                    max_val=0.1,
                                    title="FDR-adjusted q-value",
                                    formatter="{value:.3f}",
                                    thresholds=[
                                        (0.01, "#22c55e"),
                                        (0.05, "#facc15"),
                                        (0.1, "#ef4444"),
                                    ],
                                )
                            elif np.isfinite(p_val_top):
                                _echarts_gauge(
                                    p_val_top,
                                    min_val=0.0,
                                    max_val=0.1,
                                    title="p-value",
                                    formatter="{value:.3f}",
                                    thresholds=[
                                        (0.01, "#22c55e"),
                                        (0.05, "#facc15"),
                                        (0.1, "#ef4444"),
                                    ],
                                )
                            else:
                                st.info(
                                    "Significance metrics unavailable for this correlation."
                                )
                        with col_g3:
                            _echarts_gauge(
                                float(abs(lag_hours_top)),
                                min_val=0.0,
                                max_val=lag_span,
                                title="Lag magnitude (h)",
                                formatter="{value:.0f}",
                                thresholds=[
                                    (max(1.0, lag_span * 0.25), "#38bdf8"),
                                    (max(3.0, lag_span * 0.5), "#2563eb"),
                                    (lag_span, "#1d4ed8"),
                                ],
                            )
                        with col_g4:
                            max_n = float(max(n_top, 10)) * 1.1
                            _echarts_gauge(
                                float(n_top),
                                min_val=0.0,
                                max_val=max_n,
                                title="Sample size (n)",
                                formatter="{value:.0f}",
                                thresholds=[
                                    (max_n * 0.25, "#f87171"),
                                    (max_n * 0.5, "#facc15"),
                                    (max_n * 0.75, "#22c55e"),
                                ],
                            )
                        if lag_hours_top != 0:
                            activity_trend = (
                                "rises" if sign_dir == "positive" else "falls"
                            )
                            metric_trend = (
                                "increase" if sign_dir == "positive" else "decrease"
                            )
                            clinical_text = (
                                f"- **Clinical takeaway:** When geomagnetic activity {activity_trend}, "
                                f"`{metric_name}` tends to {metric_trend} about {lag_hours_top} hour(s) later."
                            )
                        else:
                            clinical_text = (
                                f"- **Clinical takeaway:** `{metric_name}` shifts in step with geomagnetic activity."
                            )
                        st.markdown(
                            "**Interpretation summary**"
                            "\n"
                            f"- **Metric:** `{metric_name}` shows a {sign_dir} Pearson correlation with Kp (|r| = {abs_r:.2f}).\n"
                            f"- **Lag interpretation:** {lag_description}; the maximum |lag| tested was ±{int(lag_span)} h.\n"
                            f"- **Significance:** "
                            + (
                                f"q = {q_val_top:.3f} (FDR-adjusted){' ✔' if np.isfinite(q_val_top) and q_val_top <= 0.05 else ''}"
                                if np.isfinite(q_val_top)
                                else (
                                    f"p = {p_val_top:.3f}{' ✔' if np.isfinite(p_val_top) and p_val_top <= 0.05 else ''}"
                                    if np.isfinite(p_val_top)
                                    else "No significance estimate available."
                                )
                            )
                            + "\n"
                            f"- **Sample size:** n = {n_top} contributing HRV windows.\n"
                            + clinical_text
                        )
                        st.caption(
                            "Interpret DONKI correlations as exploratory links between specific solar/geomagnetic drivers and HRV metrics; the lag points to the most likely propagation delay from solar activity to physiological response."
                        )

            '''
            st.markdown("#### Database summary")
            db_df = _load_jsonl()
            if db_df.empty:
                st.caption("No records saved yet.")
            else:
                st.dataframe(
                    db_df.sort_values(
                        "created_utc",
                        ascending=False).head(200))
            if _sw_loading_msg is not None:
                _sw_loading_msg.empty()

    with tab_space_data:
        st.markdown("---")
        st.markdown("### 🛰️ NOAA Space Weather Dashboard")
        
        # Dashboard loads instantly - no blocking background fetch
        # User clicks "Fetch NOAA feeds" button to load data
        _noaa_loading_msg = st.empty()
        st.markdown("*Real-time solar and geomagnetic data (data-only; correlations removed)*")

        with st.expander("🌞 **Understanding Space Weather Metrics**", expanded=False):
            st.markdown("""
**Solar Activity Indices:**
| Metric | Definition | HRV Relevance |
|--------|------------|---------------|
| **Kp Index** | Global geomagnetic disturbance (0-9 scale) | ↑ Kp associated with ↓ HRV in multiple studies |
| **Dst Index** | Ring current strength (nT) | More negative = stronger storm; similar HRV effects as Kp |
| **F10.7 Flux** | 10.7 cm solar radio emission (sfu) | Proxy for overall solar activity; long-term associations |

**Solar Wind Parameters:**
| Metric | Definition | Physiological Link |
|--------|------------|-------------------|
| **Speed** | Solar wind velocity (km/s) | Higher speeds may increase stress responses |
| **Density** | Proton density (cm⁻³) | Contributes to magnetospheric pressure |
| **IMF Bz** | Interplanetary magnetic field z-component | Southward (negative) enhances geomagnetic coupling |

**Interpretation Tips:**
- Correlations are typically **small** (r ≈ 0.1–0.3) but consistent across studies
- Test **multiple lag times** (0–72 hours) — effects may be delayed
- Always control for **time-of-day, season, and behavior**
- Treat findings as **exploratory** unless replicated
            """)
        
        noaa_state = _noaa_space_state()
        # Background prefetch disabled: keep UI deterministic and instant.
        bg_status = {"noaa": {"done": True, "error": None, "stale": False}}
        data_age = "manual (click Fetch)"

        # NOTE: Do not auto-load or auto-fetch NOAA datasets on tab open.
        # This tab must remain fully on-demand (click Load cached / Fetch / Force refresh).

        # Wrap controls in a form so tweaking scope doesn't constantly rerun/flicker.
        with st.form("space_data_noaa_fetch_controls", clear_on_submit=False):
            col_load_cache, col_scope, col_fetch_noaa, col_refresh_noaa, col_bg_status = st.columns(
                [1, 1, 1, 1, 2]
            )
            with col_scope:
                fetch_scope = st.selectbox(
                    "Scope",
                    options=["Today (fast)", "Core", "Full"],
                    index=0,
                    key="noaa_fetch_scope",
                    help=(
                        "Today (fast) loads only Kp + F10.7 (very fast). "
                        "Core loads the most useful geomagnetic/solar-wind feeds (fast). "
                        "Full loads the entire NOAA feed library (slowest)."
                    ),
                )
            keys_to_fetch: Optional[Sequence[str]] = (
                NOAA_FAST_KEYS
                if fetch_scope == "Today (fast)"
                else (NOAA_CORE_KEYS if fetch_scope == "Core" else None)
            )
            with col_load_cache:
                load_noaa_cache_clicked = st.form_submit_button(
                    "⚡ Load cached NOAA",
                    help="Load last saved NOAA feeds from disk (no network).",
                )
            with col_fetch_noaa:
                fetch_noaa_clicked = st.form_submit_button(
                    "📥 Fetch NOAA feeds",
                    help="Load NOAA feeds for the selected scope (uses cache if available).",
                )
            with col_refresh_noaa:
                refresh_noaa_clicked = st.form_submit_button(
                    "🔄 Force refresh",
                    help="Bypass cache and fetch fresh data from NOAA servers for the selected scope.",
                )
            with col_bg_status:
                cache_hint = "loaded" if bool(noaa_state.get("bundles")) else "not loaded"
                st.caption(
                    "⏸️ Background prefetch disabled | "
                    f"NOAA data: {cache_hint} | Click Load cached / Fetch"
                )

        with st.expander("🧹 Cache maintenance", expanded=False):
            confirm_clear_noaa = st.checkbox(
                "Enable NOAA cache reset (deletes local cached files)",
                value=False,
                key="cache_reset_confirm_noaa",
                help=(
                    "Use only if NOAA caches are corrupted or you want a clean refetch. "
                    "First load after clearing will be slower."
                ),
            )
            if st.button(
                "🧹 Clear NOAA cache",
                key="cache_reset_noaa_only",
                disabled=not confirm_clear_noaa,
            ):
                deleted_noaa, err_noaa = _clear_cache_dir(CACHE_BASE_DIR / "noaa_space")
                try:
                    st.cache_data.clear()
                    st.cache_resource.clear()
                except Exception:
                    pass
                noaa_state["bundles"] = {}
                noaa_state["errors"] = {}
                noaa_state["last_updated"] = None
                with _bg_fetch_lock:
                    _bg_fetch_results["noaa"]["done"] = False
                    _bg_fetch_results["noaa"]["error"] = None
                    _bg_fetch_results["noaa"]["data"] = {}
                    _bg_fetch_results["noaa"]["fetch_time"] = None
                    _bg_fetch_results["noaa"]["_applied"] = False
                if err_noaa:
                    st.error(f"NOAA cache reset completed with errors: {err_noaa}")
                else:
                    st.success(f"Cleared NOAA cache: {deleted_noaa} file(s).")

        if load_noaa_cache_clicked:
            with st.spinner("Loading cached NOAA feeds…"):
                _load_noaa_space_cache_only(noaa_state, keys=keys_to_fetch)
            st.success("Loaded cached NOAA feeds (no network).")

        if fetch_noaa_clicked:
            with st.spinner("Fetching NOAA JSON feeds…"):
                _load_noaa_space_datasets(noaa_state, keys=keys_to_fetch)
        if refresh_noaa_clicked:
            with st.spinner("Refreshing NOAA JSON feeds…"):
                _load_noaa_space_datasets(noaa_state, keys=keys_to_fetch, use_cache=False)
        # Auto-load uses cache-first; buttons remain for manual refresh/force refresh
        if noaa_state.get("loading"):
            st.info("NOAA feeds are loading…")
        errors = noaa_state.get("errors", {})
        for key, message in errors.items():
            label = "General" if key == "__global__" else key
            st.error(f"{label}: {message}")
        bundles = noaa_state.get("bundles", {})
        option_labels: Dict[str, str] = {}
        dataset_options: List[str] = []
        # Data-only dashboard: correlations are decommissioned, so HRV windowed metrics
        # are intentionally not referenced here.
        noaa_windowed_df = pd.DataFrame()
        metrics_available: List[str] = []
        if not bundles:
            if not bg_status.get("noaa", {}).get("done", False):
                st.info("📡 Fetching NOAA feeds in the background… (you can also click **Fetch NOAA feeds**).")
            else:
                st.info("📡 Click **Fetch NOAA feeds** above to load solar/geomagnetic data.")
        else:
            option_labels = {
                key: bundle.spec.title for key, bundle in bundles.items()
            }
            dataset_options = sorted(option_labels.keys(), key=lambda k: option_labels[k])
            default_dataset_key = (
                "planetary_k_index_3h"
                if "planetary_k_index_3h" in dataset_options
                else (dataset_options[0] if dataset_options else "")
            )
            default_dataset_index = (
                dataset_options.index(default_dataset_key)
                if default_dataset_key in dataset_options
                else 0
            )
            selected_dataset = st.selectbox(
                "Dataset",
                options=dataset_options,
                format_func=lambda k: option_labels.get(k, k),
                index=default_dataset_index,
                key="noaa_dataset_select",
            )
            bundle: NOAADataBundle = bundles[selected_dataset]
            if bundle.spec.description:
                st.caption(bundle.spec.description)
            # Quick sanity check: warn when the selected NOAA dataset does not
            # cover the HRV windowed timeline (common for short-horizon feeds).
            if (
                not noaa_windowed_df.empty
                and bundle.time_column in bundle.frame.columns
            ):
                try:
                    hrv_start = pd.to_datetime(noaa_windowed_df.get("start"), utc=True, errors="coerce")
                    pred_times = pd.to_datetime(bundle.frame[bundle.time_column], utc=True, errors="coerce")
                    hrv_min = hrv_start.min()
                    hrv_max = hrv_start.max()
                    pred_min = pred_times.min()
                    pred_max = pred_times.max()
                    if (
                        pd.notna(hrv_min)
                        and pd.notna(hrv_max)
                        and pd.notna(pred_min)
                        and pd.notna(pred_max)
                        and (hrv_max < pred_min or hrv_min > pred_max)
                    ):
                        extra_hint = ""
                        if selected_dataset == "planetary_k_index_1m":
                            extra_hint = (
                                " The 1-minute Kp nowcast feed typically only spans the most recent hours."
                            )
                        st.warning(
                            "Selected NOAA dataset does not overlap your HRV timestamps; correlation results will be empty."
                            + extra_hint
                            + " Try a longer-horizon dataset (e.g., **Planetary K index (3 h)**) or refresh NOAA feeds."
                        )
                except Exception:
                    pass
            cadence_minutes = bundle.spec.cadence_minutes or 60
            if cadence_minutes <= 60:
                min_hours = 6
                max_hours = 720
                step_hours = 6
                default_hours = 72
            elif cadence_minutes <= 1440:
                min_hours = 24
                max_hours = 24 * 365 * 2  # up to two years
                step_hours = 24
                default_hours = 24 * 90
            else:
                min_hours = 24 * 30
                max_hours = min(24 * 30 * 60, 24 * 365 * 30)  # up to ~30 years
                step_hours = 24 * 30
                default_hours = 24 * 30 * 12
            default_hours = int(np.clip(default_hours, min_hours, max_hours))
            rr_min_utc, rr_max_utc = _get_uploaded_rr_time_bounds()
            sync_rr_available = rr_min_utc is not None and rr_max_utc is not None
            # View controls: wrap RR sync + history slicer in a form so exploring doesn't
            # constantly rerun (which can feel like an app restart).
            with st.form("space_data_noaa_view_controls", clear_on_submit=False):
                sync_to_rr = False
                rr_pad_hours = 0
                if sync_rr_available:
                    st.caption(
                        f"Uploaded RR timeline (UTC): {rr_min_utc.strftime('%Y-%m-%d %H:%M')} → {rr_max_utc.strftime('%Y-%m-%d %H:%M')}"
                    )
                    sync_to_rr = st.checkbox(
                        "Sync NOAA history to uploaded RR timeline",
                        value=True,
                        key="noaa_sync_rr_window",
                        help=(
                            "Filters NOAA datasets to the RR timestamp range (plus optional padding). "
                            "This keeps charts responsive and makes the NOAA tab consistent with your recording window."
                        ),
                    )
                    rr_pad_hours = int(
                        st.number_input(
                            "RR window padding (hours)",
                            min_value=0,
                            max_value=24 * 14,
                            value=6,
                            step=1,
                            key="noaa_sync_rr_pad_hours",
                            help="Extra hours to include before/after the RR timeline when slicing NOAA data.",
                        )
                    )

                # Note: we don't dynamically disable this slider inside the form because
                # forms don't rerun on widget edits. If RR sync is enabled, the history
                # slider is ignored.
                history_hours = st.slider(
                    "History window (hours) (ignored when RR sync is enabled)",
                    min_value=int(min_hours),
                    max_value=int(max_hours),
                    value=int(default_hours),
                    step=int(step_hours),
                    key=f"noaa_history_{selected_dataset}",
                )
                _ = st.form_submit_button("Apply NOAA view settings")

            if sync_to_rr and rr_min_utc is not None and rr_max_utc is not None:
                window_start = rr_min_utc - pd.Timedelta(hours=int(rr_pad_hours))
                window_end = rr_max_utc + pd.Timedelta(hours=int(rr_pad_hours))
                # Hard bound to keep UI work deterministic even for long multi-day uploads.
                max_span_days = 90
                if (window_end - window_start) > pd.Timedelta(days=max_span_days):
                    st.warning(
                        f"RR window spans >{max_span_days} days; limiting NOAA view to the most recent {max_span_days} days to keep the UI fast."
                    )
                    window_start = window_end - pd.Timedelta(days=max_span_days)
                sliced_bundle = slice_noaa_bundle_time_range(
                    bundle, start_utc=window_start, end_utc=window_end
                )
                history_df = sliced_bundle.frame
                if history_df.empty:
                    st.info(
                        "This NOAA dataset has no samples inside the RR window. "
                        "Try a different dataset (e.g., **Planetary K index (3 h)**) or disable RR syncing."
                    )
            else:
                history_df = _prepare_noaa_history(bundle, int(history_hours))
            selected_value_column: Optional[str] = None
            current_label_map: Dict[str, str] = {}
            if bundle.spec.key == "solar_radio_multifrequency":
                _render_noaa_multifrequency_panel(bundle, history_df)
                if "flux_sfu" in history_df.columns:
                    selected_value_column = "flux_sfu"
                    current_label_map = {"flux_sfu": "Flux (sfu)"}
            else:
                value_columns = list(bundle.value_columns)
                if not value_columns:
                    value_columns = [
                        col
                        for col in history_df.columns
                        if col != bundle.time_column
                        and pd.api.types.is_numeric_dtype(history_df[col])
                    ]
                if not value_columns:
                    st.info("No numeric columns available for this dataset.")
                else:
                    default_index = 0
                    if bundle.spec.key == "f107_flux" and "flux" in value_columns:
                        default_index = value_columns.index("flux")
                    label_map = {
                        col: bundle.split_labels.get(
                            col, col.replace("_", " ").title()
                        )
                        for col in value_columns
                    }
                    value_column = st.selectbox(
                        "Primary metric",
                        options=value_columns,
                        index=default_index,
                        format_func=lambda col: label_map.get(col, col),
                        key=f"noaa_value_column_{selected_dataset}",
                    )
                    selected_value_column = value_column
                    current_label_map = label_map
                    overlay_candidates = [
                        col for col in value_columns if col != value_column
                    ]
                    default_overlays: List[str]
                    if (
                        bundle.spec.key == "f107_flux"
                        and "ninety_day_mean" in overlay_candidates
                    ):
                        default_overlays = ["ninety_day_mean"]
                    else:
                        default_overlays = overlay_candidates[: min(4, len(overlay_candidates))]
                    overlay_selection = st.multiselect(
                        "Additional overlays",
                        options=overlay_candidates,
                        default=default_overlays,
                        format_func=lambda col: label_map.get(col, col),
                        key=f"noaa_overlay_{selected_dataset}",
                    )
                    y_label = bundle.units.get(value_column) if bundle.units else None
                    _render_noaa_metric_panel(
                        bundle,
                        history_df,
                        value_column,
                        overlay_columns=overlay_selection,
                        line_title=f"{bundle.spec.title} trends",
                        y_label=y_label or "Value",
                    )
            # Show concise scientific interpretation for the selected metric
            try:
                if selected_dataset and selected_value_column:
                    info = explain_noaa_metric(selected_dataset, selected_value_column)
                    if info:
                        with st.expander("What this metric means (science-based)", expanded=True):
                            st.markdown(
                                f"**{info.get('title','')}**  \n"
                                f"- **What it measures**: {info.get('what','')}  \n"
                                f"- **Why it matters for space weather**: {info.get('why','')}  \n"
                                f"- **What studies suggest for physiology/HRV**: {info.get('physiology','')}  \n"
                                f"- **Most probable HRV relationship**: {info.get('likely_effect','')}  \n"
                                f"- **Key references**: {info.get('refs','')}"
                            )
            except Exception:
                pass
            st.divider()
            st.markdown("##### Correlations (decommissioned)")
            st.info(
                "Correlation workflows were intentionally removed from this unified Space Data dashboard. "
                "This keeps external data fetch/render stable and independent from HRV processing."
            )
            _DECOMMISSIONED_NOAA_CORR_BLOCK = '''
            st.markdown("##### HRV correlation analysis")
            if noaa_windowed_df.empty:
                info_col, action_col = st.columns([0.65, 0.35])
                with info_col:
                    st.info("Run the HRV window analysis to enable correlations.")
                with action_col:
                    trigger_hrv_corr = st.button(
                        "Run HRV window analysis",
                        key="noaa_trigger_hrv_corr",
                        help="Compute HRV windowed metrics to unlock NOAA correlations.",
                    )
                if trigger_hrv_corr:
                    if not has_hrv_data_uploaded:
                        st.warning("Upload HRV data first, then run the HRV analysis.")
                    else:
                        st.session_state["auto_run_hrv_analysis"] = True
                        st.session_state.pop("hrv_analysis_complete_signature", None)
                        st.rerun()
            else:
                st.info(
                    "Correlations run only when you click **Compute correlations**. "
                    "This may take several seconds depending on window length; a spinner will show progress."
                )
                metrics_available = [
                    metric
                    for metric in metric_list
                    if metric in noaa_windowed_df.columns
                    and pd.api.types.is_numeric_dtype(noaa_windowed_df[metric])
                ]
                if not metrics_available:
                    st.info("No numeric HRV metrics available for correlation.")
                else:
                    default_metrics = metrics_available[: min(4, len(metrics_available))]
                    selected_metrics = st.multiselect(
                        "HRV metrics",
                        options=metrics_available,
                        default=default_metrics,
                        key=f"noaa_metric_select_{selected_dataset}",
                    )
                    lag_min, lag_max = st.slider(
                        "Lag window (hours)",
                        min_value=-72,
                        max_value=72,
                        value=(-24, 24),
                        step=1,
                        key=f"noaa_lag_range_{selected_dataset}",
                    )
                    lag_step = st.number_input(
                        "Lag step (hours)",
                        min_value=1,
                        max_value=24,
                        value=3,
                        step=1,
                        key=f"noaa_lag_step_{selected_dataset}",
                    )
                    merge_tolerance = st.number_input(
                        "Merge tolerance (minutes)",
                        min_value=15,
                        max_value=240,
                        value=90,
                        step=15,
                        key=f"noaa_merge_tolerance_{selected_dataset}",
                    )
                    compute_corr = st.button(
                        "Compute correlations",
                        key=f"noaa_compute_corr_{selected_dataset}",
                    )
                    if compute_corr:
                        if not selected_metrics:
                            st.warning("Select at least one HRV metric to continue.")
                        else:
                            lag_start, lag_end = int(lag_min), int(lag_max)
                            lag_step_int = max(int(lag_step), 1)
                            if lag_start > lag_end:
                                st.warning(
                                    "Lag start must be less than or equal to lag end."
                                )
                            else:
                                lags = list(range(lag_start, lag_end + 1, lag_step_int))
                                if not lags:
                                    st.warning(
                                        "Lag configuration results in an empty set."
                                    )
                                else:
                                    with st.spinner("Computing Pearson correlations…"):
                                        corr_df = _build_noaa_correlations(
                        noaa_windowed_df,
                                            {selected_dataset: bundle},
                                            selected_metrics,
                                            lags,
                                            merge_tolerance_minutes=int(
                                                merge_tolerance
                                            ),
                                        )
                                    noaa_state["correlations"][selected_dataset] = corr_df
                                    noaa_state["corr_params"][selected_dataset] = {
                                        "metrics": selected_metrics,
                                        "lags": lags,
                                        "merge_tolerance": int(merge_tolerance),
                                    }
                                    if corr_df.empty:
                                        st.info(
                                            "No correlations satisfied the selected configuration."
                                        )
                                    else:
                                        st.success("Correlation scan completed.")
                    corr_df = noaa_state["correlations"].get(selected_dataset)
                    if selected_value_column is None:
                        st.info(
                            "Select a primary NOAA metric above to view correlation results."
                        )
                    else:
                        _render_noaa_correlation_summary(
                            corr_df,
                            selected_dataset,
                            selected_value_column,
                            label_map=current_label_map,
                        )
            st.divider()
            st.markdown("##### Batch NOAA correlation scan")
            if noaa_windowed_df.empty:
                info_col, action_col = st.columns([0.65, 0.35])
                with info_col:
                    st.info("Run the HRV window analysis to enable batch correlations.")
                with action_col:
                    trigger_hrv_batch = st.button(
                        "Run HRV window analysis",
                        key="noaa_trigger_hrv_batch",
                        help="Compute HRV windowed metrics to unlock batch NOAA correlations.",
                    )
                if trigger_hrv_batch:
                    if not has_hrv_data_uploaded:
                        st.warning("Upload HRV data first, then run the HRV analysis.")
                    else:
                        st.session_state["auto_run_hrv_analysis"] = True
                        st.session_state.pop("hrv_analysis_complete_signature", None)
                        st.rerun()
            elif not metrics_available:
                st.info("No numeric HRV metrics available for correlation.")
            elif not dataset_options:
                st.info("Fetch NOAA feeds to enable batch correlations.")
            else:
                st.info(
                    "Batch correlations run only when you click **Run NOAA batch correlation**. "
                    "Processing multiple feeds can take time; a spinner will be shown."
                )
                default_batch_metrics = metrics_available[: min(6, len(metrics_available))]
                batch_metrics = st.multiselect(
                    "HRV metrics (batch)",
                    options=metrics_available,
                    default=default_batch_metrics,
                    key="noaa_batch_metrics",
                )
                batch_dataset_selection = st.multiselect(
                    "NOAA datasets",
                    options=dataset_options,
                    default=dataset_options,
                    format_func=lambda k: option_labels.get(k, k),
                    key="noaa_batch_datasets",
                )
                batch_lag_min, batch_lag_max = st.slider(
                    "Lag window (hours) — batch",
                    min_value=-72,
                    max_value=72,
                    value=(-24, 24),
                    step=1,
                    key="noaa_batch_lag_range",
                )
                batch_lag_step = st.number_input(
                    "Lag step (hours) — batch",
                    min_value=1,
                    max_value=24,
                    value=3,
                    step=1,
                    key="noaa_batch_lag_step",
                )
                batch_merge_tol = st.number_input(
                    "Merge tolerance (minutes) — batch",
                    min_value=15,
                    max_value=240,
                    value=90,
                    step=15,
                    key="noaa_batch_merge_tol",
                )
                if st.button("Run NOAA batch correlation", key="noaa_run_batch_corr"):
                    if not batch_metrics:
                        st.warning("Select at least one HRV metric for the batch scan.")
                    elif not batch_dataset_selection:
                        st.warning("Select at least one NOAA dataset for the batch scan.")
                    else:
                        lag_start, lag_end = int(batch_lag_min), int(batch_lag_max)
                        lag_step_int = max(int(batch_lag_step), 1)
                        if lag_start > lag_end:
                            st.warning("Lag start must be less than or equal to lag end.")
                        else:
                            lag_values = list(range(lag_start, lag_end + 1, lag_step_int))
                            if not lag_values:
                                st.warning("Lag configuration results in an empty set.")
                            else:
                                subset_bundles = {
                                    key: bundles[key]
                                    for key in batch_dataset_selection
                                    if key in bundles
                                }
                                if not subset_bundles:
                                    st.warning("Selected NOAA datasets are unavailable.")
                                else:
                                    label_lookup: Dict[Tuple[str, str], str] = {}
                                    for key, bundle in subset_bundles.items():
                                        for column in bundle.value_columns:
                                            label_lookup[(key, column)] = bundle.split_labels.get(
                                                column, column.replace("_", " ").title()
                                            )
                                    with st.spinner("Computing NOAA batch correlations…"):
                                        batch_corr_df = _build_noaa_correlations(
                                            windowed_df,
                                            subset_bundles,
                                            batch_metrics,
                                            lag_values,
                                            merge_tolerance_minutes=int(batch_merge_tol),
                                        )
                                    noaa_state["global_corr"] = batch_corr_df
                                    noaa_state["global_corr_labels"] = label_lookup
                                    if batch_corr_df.empty:
                                        st.info(
                                            "No correlations satisfied the selected batch configuration."
                                        )
                                    else:
                                        st.success("Batch correlation scan completed.")
                global_corr_df = noaa_state.get("global_corr", pd.DataFrame())
                if global_corr_df is not None and not global_corr_df.empty:
                    label_lookup: Dict[Tuple[str, str], str] = noaa_state.get(
                        "global_corr_labels", {}
                    )
                    display_df = global_corr_df.copy()
                    display_df["abs_r"] = display_df["pearson_r"].abs()
                    display_df = display_df.sort_values("abs_r", ascending=False)
                    display_df["predictor_metric"] = [
                        f"{row.predictor_title} — {label_lookup.get((row.predictor_key, row.value_column), row.value_column.replace('_', ' ').title())}"
                        for row in display_df.itertuples()
                    ]
                    formatted = display_df[
                        [
                            "predictor_metric",
                            "metric",
                            "pearson_r",
                            "p_value",
                            "ci_low",
                            "ci_high",
                            "direction",
                            "lag_hours",
                            "n",
                        ]
                    ].copy()
                    formatted["pearson_r"] = formatted["pearson_r"].apply(
                        lambda v: _format_with_precision(float(v), 3)
                    )
                    formatted["p_value"] = formatted["p_value"].apply(
                        lambda v: f"{float(v):.2e}" if np.isfinite(v) else "n/a"
                    )
                    formatted["ci_low"] = formatted["ci_low"].apply(
                        lambda v: _format_with_precision(float(v), 3)
                    )
                    formatted["ci_high"] = formatted["ci_high"].apply(
                        lambda v: _format_with_precision(float(v), 3)
                    )
                    formatted["lag_hours"] = formatted["lag_hours"].astype(int)
                    formatted["n"] = formatted["n"].astype(int)
                    top_n = min(25, formatted.shape[0])
                    st.dataframe(formatted.head(top_n), use_container_width=True)
                    csv_bytes = display_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Download batch correlations (CSV)",
                        data=csv_bytes,
                        file_name=f"noaa_batch_correlations_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv",
                        mime="text/csv",
                        key="download_noaa_batch_csv",
                    )
                    summary_lines = []
                    for row in display_df.head(5).itertuples():
                        predictor_label = label_lookup.get(
                            (row.predictor_key, row.value_column),
                            row.value_column.replace("_", " ").title(),
                        )
                        msg = (
                            f"- **{row.metric}** vs {row.predictor_title} — {predictor_label}: "
                            f"r = {row.pearson_r:.3f}, {_format_p_value(row.p_value)}, "
                            f"{_format_ci_text(row.ci_low, row.ci_high)}, lag {int(row.lag_hours)} h "
                            f"(n = {int(row.n)})."
                        )
                        summary_lines.append(msg)
                    if summary_lines:
                        st.markdown("\n".join(summary_lines))
            '''
            _noaa_loading_msg.empty()

    with tab_space_analytics:
        st.markdown("### 🔬 Space Analytics (Correlations + ML)")
        st.caption(
            "On-demand statistical analysis and machine learning linking **space-data predictors** "
            "to **HRV + HRF metrics**. Nothing runs automatically — use the buttons below."
        )
        # UX: Streamlit dims ("stale" fades) existing elements during reruns, which
        # can make long computations feel like the page lost state. Space Analytics
        # provides explicit progress consoles, so we disable the stale opacity.
        st.markdown(
            """
            <style>
            .stApp .stale,
            .stApp [data-stale="true"],
            div[data-testid="stAppViewContainer"] .stale,
            div[data-testid="stAppViewContainer"] [data-stale="true"] {
                opacity: 1 !important;
                filter: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # ------------------------------------------------------------------
        # Computation Console (no page fading / no spinners)
        # ------------------------------------------------------------------
        # Streamlit spinners can make the UI feel "dimmed/faded" on long runs.
        # This console keeps the page fully visible and provides a detailed,
        # continuously-updated execution trace inside a framed code box.
        def _space_analytics_console_state() -> Dict[str, object]:
            state = st.session_state.setdefault(
                "space_analytics_console",
                {
                    "phase": "idle",
                    "label": "Idle",
                    "progress": 0.0,
                    "started_at_utc": "",
                    "ended_at_utc": "",
                    "lines": [],
                },
            )
            if not isinstance(state, dict):
                st.session_state["space_analytics_console"] = {
                    "phase": "idle",
                    "label": "Idle",
                    "progress": 0.0,
                    "started_at_utc": "",
                    "ended_at_utc": "",
                    "lines": [],
                }
                state = st.session_state["space_analytics_console"]
            # Enforce bounded memory (keep last N lines).
            lines = state.get("lines")
            if not isinstance(lines, list):
                state["lines"] = []
            else:
                max_lines = 500
                if len(lines) > max_lines:
                    state["lines"] = lines[-max_lines:]
            return state

        _sa_console_state = _space_analytics_console_state()
        _sa_console_progress_ph = st.empty()
        _sa_console_status_ph = st.empty()
        _sa_console_code_ph = st.empty()

        def _sa_console_render() -> None:
            state = _space_analytics_console_state()
            try:
                progress = float(state.get("progress", 0.0))
            except (TypeError, ValueError):
                progress = 0.0
            progress = float(np.clip(progress, 0.0, 1.0))
            label = str(state.get("label", ""))
            phase = str(state.get("phase", ""))
            started = str(state.get("started_at_utc", "")).strip()
            ended = str(state.get("ended_at_utc", "")).strip()
            header_bits: List[str] = []
            if label:
                header_bits.append(f"**{label}**")
            if phase:
                header_bits.append(f"`{phase}`")
            if started:
                header_bits.append(f"started: {started}")
            if ended and phase in ("done", "error", "cancelled"):
                header_bits.append(f"ended: {ended}")
            header = " | ".join(header_bits) if header_bits else "**Computation Console**"
            _sa_console_progress_ph.progress(progress)
            _sa_console_status_ph.markdown(header)
            lines = _space_analytics_console_state().get("lines", [])
            if isinstance(lines, list) and lines:
                _sa_console_code_ph.code("\n".join([str(x) for x in lines]), language="text")
            else:
                _sa_console_code_ph.code(
                    "Console is ready.\n"
                    "- Click any Space Analytics action button to stream detailed compute logs here.\n"
                    "- This avoids UI fading/dimming during long computations.\n",
                    language="text",
                )

        def _sa_console_reset(label: str) -> None:
            state = _space_analytics_console_state()
            state["phase"] = "running"
            state["label"] = str(label)
            state["progress"] = 0.0
            state["started_at_utc"] = pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            state["ended_at_utc"] = ""
            state["lines"] = []
            _sa_console_render()

        def _sa_console_set_progress(progress: float) -> None:
            state = _space_analytics_console_state()
            try:
                p = float(progress)
            except (TypeError, ValueError):
                p = 0.0
            state["progress"] = float(np.clip(p, 0.0, 1.0))
            _sa_console_render()

        def _sa_console_log(message: str) -> None:
            state = _space_analytics_console_state()
            lines = state.get("lines")
            if not isinstance(lines, list):
                lines = []
                state["lines"] = lines
            ts = pd.Timestamp.utcnow().strftime("%H:%M:%S")
            lines.append(f"[{ts}Z] {str(message)}")
            # Bound memory.
            max_lines = 500
            if len(lines) > max_lines:
                state["lines"] = lines[-max_lines:]
            _sa_console_render()

        def _sa_console_done(label: str) -> None:
            state = _space_analytics_console_state()
            state["phase"] = "done"
            state["label"] = str(label)
            state["progress"] = 1.0
            state["ended_at_utc"] = pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            _sa_console_render()

        def _sa_console_error(label: str, exc: Exception) -> None:
            state = _space_analytics_console_state()
            state["phase"] = "error"
            state["label"] = str(label)
            state["ended_at_utc"] = pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            _sa_console_log(f"ERROR: {type(exc).__name__}: {exc}")
            _sa_console_render()

        st.markdown("#### 🧾 Computation Console")
        st.caption("Live, detailed compute trace (no dimming/overlay).")
        _sa_console_render()

        # ------------------------------------------------------------------
        # Data prerequisites (no network calls on render)
        # ------------------------------------------------------------------
        space_state = _space_weather_state()
        noaa_state = _noaa_space_state()
        donki_state = _donki_state()

        # HRV windowed metrics (cache-first fallback)
        analytics_windowed_df = (
            windowed_df
            if isinstance(windowed_df, pd.DataFrame) and not windowed_df.empty
            else st.session_state.get("_hrv_cached_windowed_df", pd.DataFrame())
        )

        has_windowed = isinstance(analytics_windowed_df, pd.DataFrame) and not analytics_windowed_df.empty
        has_noaa = bool(noaa_state.get("bundles"))
        has_swpc = (
            isinstance(space_state.get("kp_df"), pd.DataFrame)
            and not space_state.get("kp_df", pd.DataFrame()).empty
        ) or (
            isinstance(space_state.get("flux_df"), pd.DataFrame)
            and not space_state.get("flux_df", pd.DataFrame()).empty
        )
        has_donki = bool(donki_state.get("loaded"))

        def _space_analytics_build_windows(
            *,
            window: str,
            step: str,
            min_rr_count: int,
            max_windows_cap: int,
            fast_time_domain_only: bool,
        ) -> pd.DataFrame:
            """
            Build windowed HRV/HRF metrics for Space Analytics without forcing a full HRV recomputation.

            This is intentionally button-driven and bounded:
            - Iterates over uploaded datasets only
            - Uses existing `_cached_windowed()` for stable caching
            """
            if not isinstance(window, str) or not window.strip():
                raise ValueError("window must be a non-empty string (e.g., '5min').")
            if not isinstance(step, str) or not step.strip():
                raise ValueError("step must be a non-empty string (e.g., '1min').")
            if int(min_rr_count) <= 0:
                raise ValueError("min_rr_count must be > 0.")
            if int(max_windows_cap) <= 0:
                raise ValueError("max_windows_cap must be > 0.")

            # Validate parseability early (helps users catch typos like '5 mins')
            _ = pd.to_timedelta(window)
            _ = pd.to_timedelta(step)

            rr_sources: Dict[str, UploadedRR] = {}
            if isinstance(uploads, dict) and uploads:
                rr_sources = uploads
            elif isinstance(datasets, dict) and datasets:
                rr_sources = datasets
            else:
                cached = st.session_state.get("_hrv_cached_datasets", {})
                if isinstance(cached, dict):
                    rr_sources = cached  # type: ignore[assignment]

            windowed_all: List[pd.DataFrame] = []
            for name, up in rr_sources.items():
                if not isinstance(up, UploadedRR):
                    continue
                if not isinstance(up.df, pd.DataFrame) or up.df.empty:
                    continue
                rr_col = "rr_intervals_ms"
                if bool(apply_clean) and "rr_intervals_ms_clean" in up.df.columns:
                    rr_col = "rr_intervals_ms_clean"
                wdf = _cached_windowed(
                    up.df,
                    rr_col=rr_col,
                    window=str(window),
                    step=str(step),
                    min_rr_count=int(min_rr_count),
                    max_windows=int(max_windows_cap),
                    include_advanced=not bool(fast_time_domain_only),
                )
                if not wdf.empty:
                    windowed_all.append(wdf.assign(source=str(name)))

            if not windowed_all:
                return pd.DataFrame()

            out = pd.concat(windowed_all, ignore_index=True)
            if "start" in out.columns:
                out["start"] = pd.to_datetime(out["start"], errors="coerce", utc=True)
                out = out.dropna(subset=["start"]).sort_values("start").reset_index(drop=True)
            if "end" in out.columns:
                out["end"] = pd.to_datetime(out["end"], errors="coerce", utc=True)
            return out

        with st.expander("📦 Data status", expanded=True):
            cols = st.columns(4)
            with cols[0]:
                st.metric("HRV windows", "✅" if has_windowed else "—")
                if has_windowed:
                    st.caption(f"Rows: {int(analytics_windowed_df.shape[0])}")
            with cols[1]:
                st.metric("NOAA bundles", "✅" if has_noaa else "—")
                if has_noaa:
                    st.caption(f"Datasets: {len(noaa_state.get('bundles', {}))}")
            with cols[2]:
                st.metric("SWPC cache", "✅" if has_swpc else "—")
                last_sw = space_state.get("last_updated")
                if last_sw is not None:
                    st.caption(f"Updated: {last_sw}")
            with cols[3]:
                st.metric("DONKI", "✅" if has_donki else "—")
                last_dk = donki_state.get("last_updated")
                if last_dk is not None:
                    st.caption(f"Updated: {last_dk}")

            # ------------------------------------------------------------------
            # Make prerequisites explicit (users often confuse "no results" with "broken")
            # ------------------------------------------------------------------
            rr_sources_diag = uploads if isinstance(uploads, dict) and uploads else datasets
            dur_min_list: List[float] = []
            beats_list: List[int] = []
            if isinstance(rr_sources_diag, dict):
                for up in rr_sources_diag.values():
                    if not isinstance(up, UploadedRR):
                        continue
                    if up.rr_ms is None or int(up.rr_ms.size) <= 0:
                        continue
                    beats_list.append(int(up.rr_ms.size))
                    dur_min_list.append(float(up.rr_ms.sum() / 60000.0))
            window_td_min = float("nan")
            try:
                window_td_min = float(pd.to_timedelta(str(win)).total_seconds() / 60.0)
            except Exception:
                window_td_min = float("nan")
            if dur_min_list:
                dur_min = float(np.nanmin(dur_min_list))
                dur_max = float(np.nanmax(dur_min_list))
                st.caption(
                    f"HRV uploads: {len(dur_min_list)} file(s) | "
                    f"Duration: {dur_min:.2f}–{dur_max:.2f} min | "
                    f"Beats: {int(np.sum(beats_list))}"
                )
            st.caption(
                f"Window settings: window=`{str(win)}` step=`{str(step)}` min_rr={int(min_rr)} "
                f"(fast windows={bool(fast_windowing)})."
            )
            if not has_windowed and dur_min_list and np.isfinite(window_td_min):
                if float(np.nanmax(dur_min_list)) < window_td_min:
                    st.warning(
                        "No HRV windows were generated because your recording(s) are **shorter than the selected window**. "
                        f"Max duration ≈ {float(np.nanmax(dur_min_list)):.2f} min, but window = {window_td_min:.2f} min. "
                        "Reduce the window/step or upload a longer recording."
                    )

            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("⚡ Load cached SWPC", key="space_analytics_load_swpc_cache"):
                    before = bool(space_state.get("loaded"))
                    _load_space_weather_cache_only(space_state)
                    after = bool(space_state.get("loaded"))
                    if after and not before:
                        st.success("Loaded cached SWPC datasets (no network).")
                    elif after:
                        st.info("SWPC cache is already loaded for this session.")
                    else:
                        st.warning("No cached SWPC datasets found on disk (nothing loaded).")
            with c2:
                if st.button("⚡ Load cached NOAA", key="space_analytics_load_noaa_cache"):
                    before_n = len(noaa_state.get("bundles", {}) or {})
                    _load_noaa_space_cache_only(noaa_state, keys=NOAA_FAST_KEYS)
                    after_n = len(noaa_state.get("bundles", {}) or {})
                    errs = noaa_state.get("errors", {}) if isinstance(noaa_state.get("errors"), dict) else {}
                    if after_n == 0:
                        st.warning(
                            "No cached NOAA datasets were loaded. "
                            "If this is your first run on this machine, click **Fetch NOAA (Core)**."
                        )
                        if errs:
                            st.caption("NOAA cache errors: " + " | ".join(list(errs.values())[:3]))
                    elif errs:
                        st.warning(f"Loaded {after_n} cached NOAA dataset(s), with {len(errs)} warning(s).")
                    elif after_n > before_n:
                        st.success(f"Loaded {after_n} cached NOAA dataset(s) (no network).")
                    else:
                        st.info(f"NOAA cache already loaded ({after_n} dataset(s)).")
            with c3:
                if st.button("📥 Fetch NOAA (Core)", key="space_analytics_fetch_noaa_core"):
                    _sa_console_reset("Fetch NOAA (Core)")
                    try:
                        _sa_console_log(f"Keys: {list(NOAA_CORE_KEYS)}")
                        _sa_console_log("Starting NOAA fetch (network)…")
                        _load_noaa_space_datasets(noaa_state, keys=NOAA_CORE_KEYS)
                        _sa_console_log("NOAA fetch completed.")
                        _sa_console_done("Fetch NOAA (Core)")
                    except Exception as exc:
                        log_exception(_LOGGER, "Space Analytics NOAA fetch failed", exc)
                        _sa_console_error("Fetch NOAA (Core) failed", exc)
                    after_n = len(noaa_state.get("bundles", {}) or {})
                    errs = noaa_state.get("errors", {}) if isinstance(noaa_state.get("errors"), dict) else {}
                    if after_n == 0:
                        st.error("No NOAA datasets loaded. Check network access and try **Force refresh NOAA (Core)**.")
                        if errs:
                            st.caption("NOAA errors: " + " | ".join(list(errs.values())[:3]))
                    elif errs:
                        st.warning(f"Fetched {after_n} NOAA Core dataset(s), with {len(errs)} warning(s).")
                    else:
                        st.success(f"Fetched {after_n} NOAA Core dataset(s).")
            with c4:
                if st.button("🔄 Force refresh NOAA (Core)", key="space_analytics_refresh_noaa_core"):
                    _sa_console_reset("Force refresh NOAA (Core)")
                    try:
                        _sa_console_log(f"Keys: {list(NOAA_CORE_KEYS)}")
                        _sa_console_log("Starting NOAA refresh (network, bypass cache)…")
                        _load_noaa_space_datasets(noaa_state, keys=NOAA_CORE_KEYS, use_cache=False)
                        _sa_console_log("NOAA refresh completed.")
                        _sa_console_done("Force refresh NOAA (Core)")
                    except Exception as exc:
                        log_exception(_LOGGER, "Space Analytics NOAA refresh failed", exc)
                        _sa_console_error("Force refresh NOAA (Core) failed", exc)
                    after_n = len(noaa_state.get("bundles", {}) or {})
                    errs = noaa_state.get("errors", {}) if isinstance(noaa_state.get("errors"), dict) else {}
                    if after_n == 0:
                        st.error("No NOAA datasets loaded after refresh. Check network/DNS/firewall and try again.")
                        if errs:
                            st.caption("NOAA errors: " + " | ".join(list(errs.values())[:3]))
                    elif errs:
                        st.warning(f"Refreshed {after_n} NOAA Core dataset(s), with {len(errs)} warning(s).")
                    else:
                        st.success(f"Refreshed {after_n} NOAA Core dataset(s).")

            # Show any NOAA load/fetch errors explicitly (no nested expanders).
            noaa_errs = noaa_state.get("errors", {}) if isinstance(noaa_state.get("errors"), dict) else {}
            if noaa_errs:
                st.warning(
                    "NOAA feed warnings/errors (first few):\n"
                    + "\n".join([f"- {k}: {v}" for k, v in list(noaa_errs.items())[:6]])
                )

            st.markdown("---")
            st.markdown("##### 🪟 Windowed HRV/HRF (required for correlations + ML)")
            st.caption(
                "If **HRV windows** above show '—', correlations/ML will be disabled. "
                "Build windows here (no network; bounded)."
            )
            sa_ui_locked = str(_space_analytics_console_state().get("phase", "")) == "running"
            if sa_ui_locked:
                st.info(
                    "Space Analytics computation is running. Controls are temporarily locked to prevent rerun interruptions."
                )

            with st.form("space_analytics_window_form", clear_on_submit=False):
                col_wcfg, col_wrun = st.columns([0.72, 0.28])
                with col_wcfg:
                    sa_win = st.text_input(
                        "Window (Space Analytics override)",
                        value=str(win),
                        key="space_analytics_window_override",
                        help="Examples: 5min, 2min, 60s. Must be shorter than your recording.",
                        disabled=bool(sa_ui_locked),
                    )
                    sa_step = st.text_input(
                        "Step (Space Analytics override)",
                        value=str(step),
                        key="space_analytics_step_override",
                        help="Examples: 1min, 30s. Smaller step → more windows.",
                        disabled=bool(sa_ui_locked),
                    )
                    sa_min_rr = st.number_input(
                        "Min RR per window (override)",
                        min_value=10,
                        max_value=2000,
                        value=int(min_rr),
                        step=10,
                        key="space_analytics_min_rr_override",
                        disabled=bool(sa_ui_locked),
                    )
                    sa_fast = st.checkbox(
                        "Fast time-domain only (override)",
                        value=bool(fast_windowing),
                        help="Recommended for short windows; skips spectral/nonlinear per-window computations.",
                        key="space_analytics_fast_window_override",
                        disabled=bool(sa_ui_locked),
                    )
                with col_wrun:
                    compute_windows_clicked = st.form_submit_button(
                        "🪟 Compute windows",
                        disabled=(not bool(has_hrv_data_uploaded)) or bool(sa_ui_locked),
                    )

            if compute_windows_clicked:
                _sa_console_reset("Compute HRV/HRF windows (Space Analytics override)")
                try:
                    _sa_console_log(
                        f"window={str(sa_win)} step={str(sa_step)} min_rr={int(sa_min_rr)}"
                    )
                    _sa_console_log(
                        f"max_windows_cap={int(max_windows)} fast_time_domain_only={bool(sa_fast)}"
                    )
                    new_windowed = _space_analytics_build_windows(
                        window=str(sa_win),
                        step=str(sa_step),
                        min_rr_count=int(sa_min_rr),
                        max_windows_cap=int(max_windows),
                        fast_time_domain_only=bool(sa_fast),
                    )
                    st.session_state["_hrv_cached_windowed_df"] = new_windowed
                    # Update local state so the rest of this tab can use the new windows
                    analytics_windowed_df = new_windowed
                    has_windowed = bool(isinstance(new_windowed, pd.DataFrame) and not new_windowed.empty)

                    _sa_console_log(
                        f"Windows built: rows={int(new_windowed.shape[0]) if isinstance(new_windowed, pd.DataFrame) else 0}"
                    )
                    _sa_console_done("Compute windows completed")
                    st.session_state["space_analytics_last_window_build"] = {
                        "computed_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                        "rows": int(new_windowed.shape[0]) if isinstance(new_windowed, pd.DataFrame) else 0,
                        "window": str(sa_win),
                        "step": str(sa_step),
                        "min_rr": int(sa_min_rr),
                        "fast": bool(sa_fast),
                    }
                except Exception as exc:
                    log_exception(_LOGGER, "Space Analytics window build failed", exc)
                    _sa_console_error("Compute windows failed", exc)
                    st.session_state["space_analytics_last_window_build"] = {
                        "computed_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                        "rows": 0,
                        "error": str(exc),
                    }

            last_build = st.session_state.get("space_analytics_last_window_build")
            if isinstance(last_build, dict):
                if str(last_build.get("error") or "").strip():
                    st.error(f"Last window build failed: {last_build.get('error')}")
                else:
                    st.caption(
                        f"Last window build: {last_build.get('computed_at_utc','unknown')} | "
                        f"rows={int(last_build.get('rows', 0))} | "
                        f"window={last_build.get('window','?')} step={last_build.get('step','?')}"
                    )

        # GPU context (display only; actual acceleration depends on backend)
        gpu_info = get_gpu_info() if GPU_PROCESSING_AVAILABLE else None
        gpu_enabled = bool(GPU_PROCESSING_AVAILABLE and is_gpu_enabled())
        if gpu_info is not None:
            st.caption(
                f"GPU: **{gpu_info.available}** ({gpu_info.device_name}) | "
                f"GPU processing enabled: **{gpu_enabled}**"
            )

        st.markdown("---")

        # ------------------------------------------------------------------
        # Event-aligned analysis (prototype; button-driven)
        # ------------------------------------------------------------------
        st.markdown("#### 🧭 Event-aligned analysis (prototype)")
        with st.expander("What Space Analytics is for (event-aligned plan)", expanded=False):
            st.markdown(
                "- **Goal**: discover whether **HRV**, **HRF**, or **both** change during a space-weather event, "
                "and whether one tends to change **before** the other.\n"
                "- **Event window**: define an event with an explicit **start → end** (e.g., Kp/Dst threshold or DONKI), "
                "then compare **baseline vs during-event** HRV/HRF windows.\n"
                "- **Outputs**: (1) which metrics changed, (2) direction/magnitude, (3) what those changes mean physiologically, "
                "and (4) which space predictors are most associated (lags).\n"
                "- **Guardrails**: this is an association tool (not causation) and must be interpreted with sleep/activity/circadian context."
            )

        if not has_windowed:
            st.info("Event-aligned analysis requires **windowed HRV/HRF metrics** (run HRV window analysis first).")
        elif not has_noaa:
            st.info("Event-aligned analysis requires **NOAA datasets** (load cached NOAA or fetch NOAA Core above).")
        else:
            try:
                from space_analytics_events import (  # noqa: PLC0415
                    ThresholdEventConfig,
                    compute_baseline_event_recovery_deltas,
                    compute_baseline_vs_event_deltas,
                    detect_first_sustained_deviation,
                    extract_threshold_events,
                )
            except Exception as exc:
                log_exception(_LOGGER, "Failed to import space_analytics_events", exc)
                ThresholdEventConfig = None  # type: ignore[assignment]
                extract_threshold_events = None  # type: ignore[assignment]
                compute_baseline_vs_event_deltas = None  # type: ignore[assignment]
                compute_baseline_event_recovery_deltas = None  # type: ignore[assignment]
                detect_first_sustained_deviation = None  # type: ignore[assignment]

            bundles: Dict[str, NOAADataBundle] = dict(noaa_state.get("bundles", {}))
            dataset_options = sorted(bundles.keys())

            # Metric meanings (short operational + physiology hints)
            metric_meanings: Dict[str, str] = {
                # HRV (common)
                "rmssd": "Short-term vagal modulation proxy (ms). Often ↓ with strain/stress/illness; interpret with breathing/posture.",
                "sdnn": "Total variability within the window (ms). Often ↓ with stress/illness; depends on window length/context.",
                "mean_hr": "Average HR (bpm). Often ↑ with load/stress/illness; interpret with activity and posture.",
                "hf_power": "HF power (ms²): RSA/vagal-linked; strongly breathing-dependent.",
                "lf_power": "LF power (ms²): mixed influences (baroreflex + autonomic); context-dependent.",
                "lf_hf_ratio": "LF/HF ratio: not a pure sympathovagal balance index; breathing confounds.",
                "pnn50": "pNN50 (%): vagal-linked but artifact/ectopy sensitive.",
                "dfa_alpha1": "DFA α1: short-range fractal scaling; extremes may reflect dysregulation/fragmentation.",
                "stress_index": "Baevsky stress index: autonomic 'centralization'/strain proxy; context-dependent.",
                # HRF (fragmentation)
                "hrf_pip": "HRF PIP (%): inflection-point rate; ↑ = more fragmentation (direction changes).",
                "hrf_pip_pct": "HRF PIP (%): inflection-point rate; ↑ = more fragmentation (direction changes).",
                "hrf_ials": "HRF IALS: inverse run length; ↑ = shorter monotonic runs = more fragmentation.",
                "hrf_w3": "HRF W3 (%): maximally fragmented 4-beat word frequency; ↑ = more fragmentation.",
                "hrf_w3_pct": "HRF W3 (%): maximally fragmented 4-beat word frequency; ↑ = more fragmentation.",
                "hrf_pss_pct": "HRF PSS (%): short segment prevalence; ↑ = more fragmented dynamics.",
                "hrf_pas_pct": "HRF PAS (%): alternating segment prevalence; ↑ = more alternation/fragmentation.",
            }

            with st.expander("Run event-aligned delta analysis", expanded=False):
                # Event definition source (start with deterministic threshold events)
                event_source_options: List[Tuple[str, str]] = []
                if "planetary_k_index_3h" in dataset_options:
                    event_source_options.append(("Kp threshold (NOAA planetary_k_index_3h)", "planetary_k_index_3h"))
                if "geospace_dst" in dataset_options:
                    event_source_options.append(("Dst threshold (NOAA geospace_dst)", "geospace_dst"))
                # Optional: DONKI event windows (solar-origin events → predicted Earth-arrival windows).
                donki_datasets: Dict[str, pd.DataFrame] = {}
                if has_donki:
                    raw_donki = donki_state.get("datasets", {})
                    if isinstance(raw_donki, dict):
                        for k, v in raw_donki.items():
                            if isinstance(k, str) and isinstance(v, pd.DataFrame):
                                donki_datasets[k] = v
                if "CMEAnalysis" in donki_datasets and not donki_datasets["CMEAnalysis"].empty:
                    event_source_options.append(("DONKI CME (DBM arrival window; CMEAnalysis speed)", "__donki_cme__"))

                if not event_source_options:
                    st.info(
                        "No suitable event-source datasets are loaded yet. Fetch NOAA Core (or load cached NOAA) "
                        "so Kp and/or Dst are available."
                    )
                elif ThresholdEventConfig is None or extract_threshold_events is None or compute_baseline_vs_event_deltas is None:
                    st.warning("Event-aligned module unavailable (import failed). Check logs/errors.log.")
                else:
                    label_to_key = {label: key for label, key in event_source_options}
                    source_label = st.selectbox(
                        "Event definition source",
                        options=[label for label, _ in event_source_options],
                        index=0,
                        key="space_analytics_event_source",
                    )
                    source_key = label_to_key.get(source_label, event_source_options[0][1])
                    if source_key == "__donki_cme__":
                        cme_df = donki_datasets.get("CMEAnalysis", pd.DataFrame())
                        if cme_df.empty:
                            st.warning("DONKI CMEAnalysis is not loaded (or contains no rows). Fetch DONKI in Space Data first.")
                        else:
                            influence_h = int(
                                st.number_input(
                                    "Assumed post-arrival influence duration (hours)",
                                    min_value=6,
                                    max_value=24 * 14,
                                    value=72,
                                    step=6,
                                    key="space_analytics_donki_cme_influence_h",
                                    help=(
                                        "This extends the predicted Earth-arrival window to capture storm + recovery. "
                                        "Use a larger value (e.g., 72–120h) when you want longer recovery coverage."
                                    ),
                                )
                            )
                            max_events = int(
                                st.number_input(
                                    "Max DONKI CME events to include",
                                    min_value=1,
                                    max_value=500,
                                    value=200,
                                    step=10,
                                    key="space_analytics_donki_cme_max_events",
                                    help="Hard bound for deterministic runtime.",
                                )
                            )
                            filter_to_hrv = st.checkbox(
                                "Filter to events overlapping the HRV windowed timeline",
                                value=True,
                                key="space_analytics_donki_cme_filter_hrv",
                                help="Keeps the catalog focused on your recording window.",
                            )
                            detect_events = st.button(
                                "🔎 Build DONKI CME influence windows",
                                key="space_analytics_detect_donki_cme_events",
                                help="Uses CMEAnalysis speed + a DBM transit-time estimate to build Earth-arrival influence windows.",
                            )
                            if detect_events:
                                try:
                                    ev_df = build_donki_cme_influence_windows(
                                        cme_df,
                                        influence_hours=int(influence_h),
                                        max_events=int(max_events),
                                    )
                                    if filter_to_hrv and not ev_df.empty and has_windowed:
                                        w_min = pd.to_datetime(analytics_windowed_df.get("start"), utc=True, errors="coerce").min()
                                        w_max = pd.to_datetime(analytics_windowed_df.get("start"), utc=True, errors="coerce").max()
                                        if pd.notna(w_min) and pd.notna(w_max):
                                            ev_df = ev_df.loc[
                                                (ev_df["end_utc"] >= w_min) & (ev_df["start_utc"] <= w_max)
                                            ].copy()
                                    st.session_state["space_analytics_event_catalog"] = {
                                        "computed_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                                        "params": {
                                            "source_key": str(source_key),
                                            "influence_h": int(influence_h),
                                            "max_events": int(max_events),
                                            "filtered_to_hrv": bool(filter_to_hrv),
                                        },
                                        "events": ev_df,
                                    }
                                    if ev_df.empty:
                                        st.info("No DONKI CME influence windows found for the current configuration.")
                                    else:
                                        st.success(f"Built {int(ev_df.shape[0])} DONKI CME influence window(s).")
                                except Exception as exc:
                                    log_exception(_LOGGER, "Space Analytics DONKI CME window build failed", exc)
                                    st.error(f"DONKI CME window build failed: {exc}")
                    else:
                        bundle = bundles.get(source_key)
                        if bundle is None or bundle.frame.empty:
                            st.warning("Selected event source has no data loaded yet.")
                        else:
                            value_cols = list(bundle.value_columns or [])
                            if not value_cols:
                                st.warning("Selected dataset has no numeric value columns.")
                            else:
                                default_val_col = value_cols[0]
                                val_col = st.selectbox(
                                    "Value column",
                                    options=value_cols,
                                    index=value_cols.index(default_val_col) if default_val_col in value_cols else 0,
                                    key="space_analytics_event_value_col",
                                )

                                # Sensible defaults by event type
                                default_threshold = 5.0 if source_key == "planetary_k_index_3h" else -50.0
                                default_dir = "ge" if source_key == "planetary_k_index_3h" else "le"
                                threshold = float(
                                    st.number_input(
                                        "Threshold",
                                        value=float(default_threshold),
                                        step=0.1,
                                        key="space_analytics_event_threshold",
                                    )
                                )
                                direction_label = st.selectbox(
                                    "Condition",
                                    options=["≥ threshold", "≤ threshold"],
                                    index=0 if default_dir == "ge" else 1,
                                    key="space_analytics_event_direction",
                                )
                                direction = "ge" if direction_label.startswith("≥") else "le"

                                # Gap/duration controls (bounded)
                                default_gap_h = 6 if source_key == "planetary_k_index_3h" else 3
                                max_gap_h = int(
                                    st.number_input(
                                        "Max gap between in-event samples (hours)",
                                        min_value=1,
                                        max_value=48,
                                        value=int(default_gap_h),
                                        step=1,
                                        key="space_analytics_event_max_gap_h",
                                    )
                                )
                                min_duration_h = int(
                                    st.number_input(
                                        "Minimum event duration (hours)",
                                        min_value=0,
                                        max_value=168,
                                        value=3 if source_key == "planetary_k_index_3h" else 2,
                                        step=1,
                                        key="space_analytics_event_min_dur_h",
                                    )
                                )
                                pad_end_h = int(
                                    st.number_input(
                                        "Pad event end (hours)",
                                        min_value=0,
                                        max_value=48,
                                        value=0,
                                        step=1,
                                        key="space_analytics_event_pad_end_h",
                                    )
                                )

                                detect_events = st.button(
                                    "🔎 Detect events",
                                    key="space_analytics_detect_events",
                                    help="Extracts start/end windows where the selected predictor crosses the threshold.",
                                )

                                # Store events in session for stability across reruns
                                if detect_events:
                                    try:
                                        cfg = ThresholdEventConfig(
                                            threshold=float(threshold),
                                            direction=direction,  # type: ignore[arg-type]
                                            max_gap=pd.Timedelta(hours=int(max_gap_h)),
                                            min_duration=pd.Timedelta(hours=int(min_duration_h)),
                                            pad_end=pd.Timedelta(hours=int(pad_end_h)),
                                        )
                                        ev_df = extract_threshold_events(
                                            bundle.frame,
                                            time_col=str(bundle.time_column),
                                            value_col=str(val_col),
                                            cfg=cfg,
                                        )
                                        st.session_state["space_analytics_event_catalog"] = {
                                            "computed_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                                            "params": {
                                                "source_key": str(source_key),
                                                "value_col": str(val_col),
                                                "threshold": float(threshold),
                                                "direction": str(direction),
                                                "max_gap_h": int(max_gap_h),
                                                "min_duration_h": int(min_duration_h),
                                                "pad_end_h": int(pad_end_h),
                                            },
                                            "events": ev_df,
                                        }
                                        if ev_df.empty:
                                            st.info("No events detected for the selected threshold/configuration.")
                                        else:
                                            st.success(f"Detected {int(ev_df.shape[0])} event(s).")
                                    except Exception as exc:
                                        log_exception(_LOGGER, "Space Analytics event detection failed", exc)
                                        st.error(f"Event detection failed: {exc}")

                            stored_events = st.session_state.get("space_analytics_event_catalog")
                            if isinstance(stored_events, dict) and isinstance(stored_events.get("events"), pd.DataFrame):
                                ev_df = stored_events["events"]
                                if not ev_df.empty:
                                    with st.expander("✅ Detected events (saved for this session)", expanded=True):
                                        st.caption(f"Computed: {stored_events.get('computed_at_utc', 'unknown')}")
                                        st.dataframe(ev_df, use_container_width=True)

                                    # Event selection
                                    event_labels: List[str] = []
                                    event_lookup: Dict[str, Tuple[pd.Timestamp, pd.Timestamp]] = {}
                                    for row in ev_df.itertuples(index=False):
                                        start = getattr(row, "start_utc")
                                        end = getattr(row, "end_utc")
                                        label = f"Event {getattr(row, 'event_id')}: {pd.to_datetime(start).strftime('%Y-%m-%d %H:%M')} → {pd.to_datetime(end).strftime('%Y-%m-%d %H:%M')} UTC"
                                        event_labels.append(label)
                                        event_lookup[label] = (pd.to_datetime(start, utc=True), pd.to_datetime(end, utc=True))

                                    selected_event = st.selectbox(
                                        "Select event to analyze",
                                        options=event_labels,
                                        index=0,
                                        key="space_analytics_selected_event",
                                    )
                                    event_start, event_end = event_lookup.get(selected_event, (None, None))

                                    # Baseline config
                                    baseline_pre_h = int(
                                        st.number_input(
                                            "Baseline window before event start (hours)",
                                            min_value=1,
                                            max_value=168,
                                            value=24,
                                            step=1,
                                            key="space_analytics_event_baseline_pre_h",
                                        )
                                    )
                                    include_recovery = st.checkbox(
                                        "Include recovery phase (post-event)",
                                        value=True,
                                        help="If enabled, compute baseline vs recovery deltas in addition to baseline vs event.",
                                        key="space_analytics_event_include_recovery",
                                    )
                                    recovery_post_h = int(
                                        st.number_input(
                                            "Recovery window after event end (hours)",
                                            min_value=1,
                                            max_value=168,
                                            value=24,
                                            step=1,
                                            disabled=not include_recovery,
                                            key="space_analytics_event_recovery_post_h",
                                        )
                                    )
                                    require_hrf_quality = st.checkbox(
                                        "Require HRF quality OK (if available)",
                                        value=True,
                                        help="If hrf_quality_ok exists, filter to True to reduce artifact/ectopy confounding.",
                                        key="space_analytics_event_require_hrf_quality",
                                    )

                                    # Metric selection
                                    w0 = analytics_windowed_df.copy()
                                    w0["start"] = pd.to_datetime(w0.get("start"), errors="coerce", utc=True)
                                    numeric_cols = [
                                        c
                                        for c in w0.columns
                                        if c not in ("start", "end")
                                        and pd.api.types.is_numeric_dtype(w0[c])
                                    ]
                                    hrf_preferred = [
                                        "hrf_pip_pct",
                                        "hrf_ials",
                                        "hrf_w3_pct",
                                        "hrf_pss_pct",
                                        "hrf_pas_pct",
                                    ]
                                    default_targets = [
                                        c for c in ("rmssd", "sdnn", "hf_power", "lf_hf_ratio", "mean_hr") if c in numeric_cols
                                    ] + [c for c in hrf_preferred if c in numeric_cols]
                                    default_targets = default_targets[: min(12, len(default_targets))]
                                    target_metrics = st.multiselect(
                                        "HRV/HRF metrics to compare (baseline vs event)",
                                        options=sorted(numeric_cols),
                                        default=default_targets,
                                        key="space_analytics_event_targets",
                                    )

                                    st.markdown("---")
                                    st.markdown("##### 📈 Correlations within timeframes (baseline/event/recovery)")
                                    st.caption(
                                        "Computes Pearson correlations between a selected space-weather predictor and your chosen HRV/HRF metrics "
                                        "inside each timeframe. This helps quantify *association* during baseline vs impact vs recovery."
                                    )
                                    predictor_candidates: List[str] = []
                                    for candidate in ("planetary_k_index_3h", "geospace_dst"):
                                        if candidate in dataset_options:
                                            predictor_candidates.append(candidate)
                                    predictor_candidates = predictor_candidates or dataset_options[:1]
                                    predictor_key = st.selectbox(
                                        "Predictor dataset (Earth-side index)",
                                        options=predictor_candidates,
                                        index=0,
                                        format_func=lambda k: bundles.get(k).spec.title if k in bundles else k,
                                        key="space_analytics_phase_corr_predictor_key",
                                    )
                                    pred_bundle = bundles.get(str(predictor_key))
                                    pred_value_cols = (
                                        list(pred_bundle.value_columns or [])
                                        if pred_bundle is not None
                                        else []
                                    )
                                    if pred_bundle is None or pred_bundle.frame.empty or not pred_value_cols:
                                        st.info("Selected predictor dataset is not available for correlations.")
                                    else:
                                        pred_val_col = st.selectbox(
                                            "Predictor value column",
                                            options=pred_value_cols,
                                            index=0,
                                            key="space_analytics_phase_corr_predictor_val_col",
                                        )
                                        merge_tol_min = int(
                                            st.number_input(
                                                "Time alignment tolerance (minutes)",
                                                min_value=15,
                                                max_value=360,
                                                value=90,
                                                step=15,
                                                key="space_analytics_phase_corr_merge_tol_min",
                                                help="Max allowed gap when aligning predictor samples to HRV windows.",
                                            )
                                        )
                                        compute_phase_corr = st.button(
                                            "📈 Compute correlations for baseline / event / recovery",
                                            key="space_analytics_compute_phase_corr",
                                            disabled=(not bool(target_metrics)) or (event_start is None) or (event_end is None),
                                        )
                                        if compute_phase_corr:
                                            try:
                                                w = analytics_windowed_df.copy()
                                                w["start"] = pd.to_datetime(w["start"], errors="coerce", utc=True)
                                                w = w.dropna(subset=["start"]).sort_values("start")
                                                if require_hrf_quality and "hrf_quality_ok" in w.columns:
                                                    q = w["hrf_quality_ok"].astype("boolean").fillna(False)
                                                    w = w.loc[q.to_numpy()]
                                                if w.empty:
                                                    st.error("No valid HRV/HRF windows available after filtering.")
                                                else:
                                                    assert event_start is not None and event_end is not None  # invariant
                                                    baseline_start = event_start - pd.Timedelta(hours=int(baseline_pre_h))
                                                    baseline_end = event_start
                                                    phases: List[Tuple[str, pd.Timestamp, pd.Timestamp]] = [
                                                        ("baseline", baseline_start, baseline_end),
                                                        ("event", event_start, event_end),
                                                    ]
                                                    if include_recovery:
                                                        phases.append(
                                                            (
                                                                "recovery",
                                                                event_end,
                                                                event_end + pd.Timedelta(hours=int(recovery_post_h)),
                                                            )
                                                        )

                                                    corr_parts: List[pd.DataFrame] = []
                                                    for phase_label, p_start, p_end in phases:
                                                        part = _phase_correlation_table(
                                                            w,
                                                            pred_bundle.frame,
                                                            time_col="start",
                                                            predictor_time_col=str(pred_bundle.time_column),
                                                            predictor_value_col=str(pred_val_col),
                                                            metric_cols=list(target_metrics),
                                                            phase_label=str(phase_label),
                                                            phase_start_utc=p_start,
                                                            phase_end_utc=p_end,
                                                            merge_tolerance_minutes=int(merge_tol_min),
                                                        )
                                                        if not part.empty:
                                                            corr_parts.append(part)
                                                    corr_df = (
                                                        pd.concat(corr_parts, ignore_index=True)
                                                        if corr_parts
                                                        else pd.DataFrame()
                                                    )
                                                    st.session_state["space_analytics_phase_corr_results"] = {
                                                        "computed_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                                                        "params": {
                                                            "predictor_key": str(predictor_key),
                                                            "predictor_value_col": str(pred_val_col),
                                                            "merge_tol_min": int(merge_tol_min),
                                                            "baseline_pre_h": int(baseline_pre_h),
                                                            "include_recovery": bool(include_recovery),
                                                            "recovery_post_h": int(recovery_post_h) if include_recovery else 0,
                                                            "metrics": list(target_metrics),
                                                        },
                                                        "results": corr_df,
                                                    }
                                                    if corr_df.empty:
                                                        st.info("No correlations could be computed in the selected phase windows.")
                                                    else:
                                                        st.success("Phase correlation tables computed.")
                                            except Exception as exc:
                                                log_exception(_LOGGER, "Space Analytics phase correlations failed", exc)
                                                st.error(f"Phase correlations failed: {exc}")

                                        stored_corr = st.session_state.get("space_analytics_phase_corr_results")
                                        if isinstance(stored_corr, dict) and isinstance(stored_corr.get("results"), pd.DataFrame):
                                            corr_df = stored_corr["results"]
                                            if not corr_df.empty:
                                                with st.expander("✅ Phase correlations (saved for this session)", expanded=True):
                                                    st.caption(f"Computed: {stored_corr.get('computed_at_utc', 'unknown')}")
                                                    st.dataframe(corr_df, use_container_width=True)
                                                    # Highlight top correlations per phase
                                                    if "pearson_r" in corr_df.columns and "phase" in corr_df.columns:
                                                        try:
                                                            top_rows = (
                                                                corr_df.assign(_abs_r=corr_df["pearson_r"].abs())
                                                                .sort_values(["phase", "_abs_r"], ascending=[True, False])
                                                                .groupby("phase", as_index=False)
                                                                .head(5)
                                                                .drop(columns=["_abs_r"], errors="ignore")
                                                            )
                                                            st.markdown("**Top |r| rows per phase:**")
                                                            st.dataframe(top_rows, use_container_width=True)
                                                        except Exception:
                                                            pass

                                    run_event_delta = st.button(
                                        "🧪 Run baseline vs event delta table",
                                        key="space_analytics_run_event_delta",
                                        disabled=not bool(target_metrics),
                                        help="Computes per-metric baseline vs event deltas (mean/SD + Cohen's d).",
                                    )

                                    if run_event_delta:
                                        try:
                                            w = analytics_windowed_df.copy()
                                            w["start"] = pd.to_datetime(w["start"], errors="coerce", utc=True)
                                            w = w.dropna(subset=["start"]).sort_values("start")
                                            if require_hrf_quality and "hrf_quality_ok" in w.columns:
                                                q = w["hrf_quality_ok"].astype("boolean").fillna(False)
                                                w = w.loc[q.to_numpy()]
                                            if w.empty:
                                                st.error("No valid HRV/HRF windows available after filtering.")
                                            elif event_start is None or event_end is None:
                                                st.error("Invalid event selection.")
                                            else:
                                                if include_recovery and compute_baseline_event_recovery_deltas is not None:
                                                    delta_df = compute_baseline_event_recovery_deltas(
                                                        w,
                                                        time_col="start",
                                                        metric_cols=list(target_metrics),
                                                        event_start_utc=event_start,
                                                        event_end_utc=event_end,
                                                        baseline_pre=pd.Timedelta(hours=int(baseline_pre_h)),
                                                        recovery_post=pd.Timedelta(hours=int(recovery_post_h)),
                                                        min_samples_per_phase=3,
                                                    )
                                                else:
                                                    delta_df = compute_baseline_vs_event_deltas(
                                                        w,
                                                        time_col="start",
                                                        metric_cols=list(target_metrics),
                                                        event_start_utc=event_start,
                                                        event_end_utc=event_end,
                                                        baseline_pre=pd.Timedelta(hours=int(baseline_pre_h)),
                                                        min_samples_per_phase=3,
                                                    )
                                                if delta_df.empty:
                                                    st.info(
                                                        "No delta rows computed (likely insufficient baseline/event windows). "
                                                        "Try increasing baseline hours or ensure more windows overlap the event."
                                                    )
                                                else:
                                                    # Attach meaning strings
                                                    delta_df = delta_df.copy()
                                                    delta_df["meaning"] = [
                                                        metric_meanings.get(str(m), "") for m in delta_df["metric"].astype(str).tolist()
                                                    ]
                                                    st.session_state["space_analytics_event_delta_results"] = {
                                                        "computed_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                                                        "params": {
                                                            "event_start_utc": str(event_start),
                                                            "event_end_utc": str(event_end),
                                                            "baseline_pre_h": int(baseline_pre_h),
                                                            "include_recovery": bool(include_recovery),
                                                            "recovery_post_h": int(recovery_post_h) if include_recovery else 0,
                                                            "require_hrf_quality": bool(require_hrf_quality),
                                                            "metrics": list(target_metrics),
                                                        },
                                                        "results": delta_df,
                                                    }
                                                    st.success("Event-aligned delta table computed.")
                                        except Exception as exc:
                                            log_exception(_LOGGER, "Space Analytics delta computation failed", exc)
                                            st.error(f"Delta computation failed: {exc}")

                                    stored_delta = st.session_state.get("space_analytics_event_delta_results")
                                    if isinstance(stored_delta, dict) and isinstance(stored_delta.get("results"), pd.DataFrame):
                                        out_df = stored_delta["results"]
                                        with st.expander("✅ Baseline vs event deltas (saved for this session)", expanded=True):
                                            st.caption(f"Computed: {stored_delta.get('computed_at_utc', 'unknown')}")
                                            st.dataframe(out_df, use_container_width=True)
                                            st.download_button(
                                                "⬇️ Download event deltas (CSV)",
                                                data=out_df.to_csv(index=False).encode("utf-8"),
                                                file_name="space_analytics_event_deltas.csv",
                                                mime="text/csv",
                                                key="space_analytics_event_deltas_download",
                                            )

                                            # High-signal textual summary (top 5 by |d|)
                                            top = out_df.head(5)
                                            summary_lines = []
                                            for row in top.itertuples(index=False):
                                                metric = getattr(row, "metric")
                                                d = getattr(row, "cohen_d")
                                                delta = getattr(row, "delta")
                                                n_b = getattr(row, "n_baseline")
                                                n_e = getattr(row, "n_event")
                                                summary_lines.append(
                                                    f"- **{metric}**: Δ={delta:.4g}, d={d:.3g} (baseline n={int(n_b)}, event n={int(n_e)})"
                                                )
                                            if summary_lines:
                                                st.markdown("**Top changes (ranked by |effect size|):**\n" + "\n".join(summary_lines))

                                    # --------------------------------------------------------
                                    # Onset / sequencing (button-driven)
                                    # --------------------------------------------------------
                                    st.markdown("---")
                                    st.markdown("##### ⏱️ Sequencing: which changes first? (prototype)")
                                    st.caption(
                                        "Detects the first sustained deviation from baseline using a simple z-score rule. "
                                        "This is a heuristic for lead/lag exploration, not a diagnostic."
                                    )
                                    z_thresh = float(
                                        st.number_input(
                                            "Deviation threshold (|z|)",
                                            min_value=0.5,
                                            max_value=5.0,
                                            value=1.0,
                                            step=0.1,
                                            key="space_analytics_onset_z",
                                        )
                                    )
                                    sustain_w = int(
                                        st.number_input(
                                            "Sustained windows required",
                                            min_value=1,
                                            max_value=12,
                                            value=2,
                                            step=1,
                                            key="space_analytics_onset_sustain",
                                        )
                                    )
                                    include_recovery_in_search = st.checkbox(
                                        "Search includes recovery window (if enabled)",
                                        value=True,
                                        key="space_analytics_onset_include_recovery",
                                    )

                                    # Build metric group choices from available columns
                                    hrv_defaults = [c for c in ("rmssd", "mean_hr", "hf_power") if c in numeric_cols]
                                    hrf_defaults = [c for c in ("hrf_pip_pct", "hrf_ials", "hrf_w3_pct") if c in numeric_cols]
                                    hrv_metrics = st.multiselect(
                                        "HRV metrics to scan for onset",
                                        options=sorted(numeric_cols),
                                        default=hrv_defaults,
                                        key="space_analytics_onset_hrv_metrics",
                                    )
                                    hrf_metrics = st.multiselect(
                                        "HRF metrics to scan for onset",
                                        options=sorted(numeric_cols),
                                        default=hrf_defaults,
                                        key="space_analytics_onset_hrf_metrics",
                                    )

                                    run_onset = st.button(
                                        "⏱️ Run onset detection",
                                        key="space_analytics_run_onset",
                                        disabled=not bool(hrv_metrics or hrf_metrics) or detect_first_sustained_deviation is None,
                                        help="Computes first sustained deviation times for selected metrics (cached in-session).",
                                    )
                                    if run_onset:
                                        try:
                                            w = analytics_windowed_df.copy()
                                            w["start"] = pd.to_datetime(w["start"], errors="coerce", utc=True)
                                            w = w.dropna(subset=["start"]).sort_values("start")
                                            if require_hrf_quality and "hrf_quality_ok" in w.columns:
                                                q = w["hrf_quality_ok"].astype("boolean").fillna(False)
                                                w = w.loc[q.to_numpy()]
                                            if w.empty:
                                                st.error("No valid HRV/HRF windows available after filtering.")
                                            elif event_start is None or event_end is None:
                                                st.error("Invalid event selection.")
                                            else:
                                                baseline_start = event_start - pd.Timedelta(hours=int(baseline_pre_h))
                                                baseline_end = event_start
                                                search_end = event_end
                                                if include_recovery and include_recovery_in_search:
                                                    search_end = event_end + pd.Timedelta(hours=int(recovery_post_h))
                                                metrics_all = list(dict.fromkeys(list(hrv_metrics) + list(hrf_metrics)))
                                                onset_df = detect_first_sustained_deviation(
                                                    w,
                                                    time_col="start",
                                                    metric_cols=metrics_all,
                                                    baseline_start_utc=baseline_start,
                                                    baseline_end_utc=baseline_end,
                                                    search_start_utc=event_start,
                                                    search_end_utc=search_end,
                                                    z_threshold=float(z_thresh),
                                                    sustain_windows=int(sustain_w),
                                                    min_baseline_samples=5,
                                                )
                                                if onset_df.empty:
                                                    st.info("No sustained deviations detected for the selected metrics/threshold.")
                                                else:
                                                    onset_df = onset_df.copy()
                                                    onset_df["meaning"] = [
                                                        metric_meanings.get(str(m), "") for m in onset_df["metric"].astype(str).tolist()
                                                    ]
                                                    onset_df["group"] = [
                                                        "HRF" if str(m) in set(hrf_metrics) else "HRV" for m in onset_df["metric"].astype(str).tolist()
                                                    ]
                                                    st.session_state["space_analytics_event_onset_results"] = {
                                                        "computed_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                                                        "params": {
                                                            "event_start_utc": str(event_start),
                                                            "event_end_utc": str(event_end),
                                                            "baseline_pre_h": int(baseline_pre_h),
                                                            "include_recovery_in_search": bool(include_recovery_in_search),
                                                            "z_threshold": float(z_thresh),
                                                            "sustain_windows": int(sustain_w),
                                                            "hrv_metrics": list(hrv_metrics),
                                                            "hrf_metrics": list(hrf_metrics),
                                                        },
                                                        "results": onset_df,
                                                    }
                                                    st.success("Onset detection completed.")
                                        except Exception as exc:
                                            log_exception(_LOGGER, "Space Analytics onset detection failed", exc)
                                            st.error(f"Onset detection failed: {exc}")

                                    stored_onset = st.session_state.get("space_analytics_event_onset_results")
                                    if isinstance(stored_onset, dict) and isinstance(stored_onset.get("results"), pd.DataFrame):
                                        onset_df = stored_onset["results"]
                                        with st.expander("✅ Onset detection results (saved for this session)", expanded=True):
                                            clear_event_clicked = st.button(
                                                "🧹 Clear event results",
                                                key="space_analytics_clear_event_results",
                                                help="Clears the detected events, delta table, and onset results saved for this session.",
                                            )
                                            if clear_event_clicked:
                                                st.session_state.pop("space_analytics_event_catalog", None)
                                                st.session_state.pop("space_analytics_event_delta_results", None)
                                                st.session_state.pop("space_analytics_event_onset_results", None)
                                                st.success("Event-aligned results cleared.")
                                            else:
                                                st.caption(f"Computed: {stored_onset.get('computed_at_utc', 'unknown')}")
                                                st.dataframe(onset_df, use_container_width=True)
                                                # Group-level summary (earliest onset in HRV vs HRF)
                                                try:
                                                    hrv_min = onset_df.loc[
                                                        onset_df["group"] == "HRV", "onset_offset_hours"
                                                    ].min()
                                                    hrf_min = onset_df.loc[
                                                        onset_df["group"] == "HRF", "onset_offset_hours"
                                                    ].min()
                                                except Exception:
                                                    hrv_min = float("nan")
                                                    hrf_min = float("nan")
                                                if pd.notna(hrv_min) or pd.notna(hrf_min):
                                                    st.markdown(
                                                        f"**Earliest onset (hours from event start)**: "
                                                        f"HRV = {hrv_min:.2f} h | HRF = {hrf_min:.2f} h"
                                                    )
                                                st.download_button(
                                                    "⬇️ Download onset results (CSV)",
                                                    data=onset_df.to_csv(index=False).encode("utf-8"),
                                                    file_name="space_analytics_event_onset.csv",
                                                    mime="text/csv",
                                                    key="space_analytics_onset_download",
                                                )

        # ------------------------------------------------------------------
        # Correlation suite (button-driven)
        # ------------------------------------------------------------------
        st.markdown("#### 📈 Correlation Suite (HRV/HRF ↔ NOAA)")
        if not has_windowed:
            st.warning(
                "Windowed HRV/HRF metrics are not available. Run HRV window analysis first, "
                "then return here."
            )
            if st.button("Run HRV window analysis", key="space_analytics_trigger_hrv_window"):
                if not has_hrv_data_uploaded:
                    st.warning("Upload HRV data first, then run the HRV analysis.")
                else:
                    st.session_state["auto_run_hrv_analysis"] = True
                    st.session_state.pop("hrv_analysis_complete_signature", None)
                    st.rerun()
        elif not has_noaa:
            st.info("Load cached NOAA or fetch NOAA feeds above to enable correlations.")
        else:
            bundles: Dict[str, NOAADataBundle] = dict(noaa_state.get("bundles", {}))
            dataset_options = sorted(bundles.keys())

            # Targets: include HRF metrics by default when present
            numeric_cols = [
                c
                for c in analytics_windowed_df.columns
                if c not in ("start", "end")
                and pd.api.types.is_numeric_dtype(analytics_windowed_df[c])
            ]
            hrf_preferred = [
                "hrf_pip_pct",
                "hrf_ials",
                "hrf_pss_pct",
                "hrf_pip_h_pct",
                "hrf_pip_s_pct",
                "hrf_pas_pct",
                "hrf_w0_pct",
                "hrf_w1_pct",
                "hrf_w2_pct",
                "hrf_w3_pct",
                "hrf_w3",
            ]
            default_targets = [
                c for c in ("rmssd", "sdnn", "hf_power", "lf_hf_ratio", "mean_hr") if c in numeric_cols
            ] + [c for c in hrf_preferred if c in numeric_cols]
            default_targets = default_targets[: min(10, len(default_targets))]

            sa_ui_locked = str(_space_analytics_console_state().get("phase", "")) == "running"
            with st.form("space_analytics_corr_form", clear_on_submit=False):
                col_sel1, col_sel2 = st.columns(2)
                with col_sel1:
                    predictors_selected = st.multiselect(
                        "NOAA predictors (datasets)",
                        options=dataset_options,
                        default=[
                            k
                            for k in ("planetary_k_index_3h", "geospace_dst", "f107_flux")
                            if k in dataset_options
                        ],
                        key="space_analytics_predictors",
                        disabled=bool(sa_ui_locked),
                    )
                with col_sel2:
                    target_metrics = st.multiselect(
                        "HRV/HRF target metrics",
                        options=sorted(numeric_cols),
                        default=default_targets,
                        key="space_analytics_targets",
                        disabled=bool(sa_ui_locked),
                    )

                lag_min, lag_max = st.slider(
                    "Lag window (hours, applied to predictor timestamps)",
                    min_value=-72,
                    max_value=72,
                    value=(-24, 24),
                    step=1,
                    key="space_analytics_lag_range",
                    disabled=bool(sa_ui_locked),
                )
                lag_step = st.number_input(
                    "Lag step (hours)",
                    min_value=1,
                    max_value=24,
                    value=3,
                    step=1,
                    key="space_analytics_lag_step",
                    disabled=bool(sa_ui_locked),
                )
                merge_tolerance = st.number_input(
                    "Merge tolerance (minutes)",
                    min_value=15,
                    max_value=240,
                    value=90,
                    step=15,
                    key="space_analytics_merge_tol",
                    disabled=bool(sa_ui_locked),
                )
                use_all_value_cols = st.checkbox(
                    "Use all value columns per dataset (slower)",
                    value=False,
                    help="Some datasets expose multiple numeric columns; enable to scan all.",
                    key="space_analytics_all_value_cols",
                    disabled=bool(sa_ui_locked),
                )

                # Bounds / complexity guardrails (computed on submit)
                lags = list(
                    range(int(lag_min), int(lag_max) + 1, int(max(int(lag_step), 1)))
                )
                if len(lags) > 97:
                    st.warning(
                        "Lag configuration is too large; reduce the lag window or increase the step."
                    )
                    lags = lags[:97]

                est_value_cols = 0
                for k in predictors_selected:
                    b = bundles.get(k)
                    if not b:
                        continue
                    est_value_cols += (
                        len(b.value_columns)
                        if bool(use_all_value_cols)
                        else min(1, len(b.value_columns))
                    )
                est_tests = int(len(lags) * est_value_cols * max(len(target_metrics), 1))
                st.caption(f"Estimated tests: **{est_tests}** (lags × value cols × targets).")

                run_corr = st.form_submit_button(
                    "🔬 Run correlation scan",
                    disabled=(not predictors_selected) or (not target_metrics) or bool(sa_ui_locked),
                )

            if run_corr:
                if "start" not in analytics_windowed_df.columns:
                    st.error("Windowed metrics are missing the required 'start' timestamp column.")
                else:
                    # Build correlations (robust table) without network calls.
                    w = analytics_windowed_df.copy()
                    w["start"] = pd.to_datetime(w["start"], errors="coerce", utc=True)
                    w = w.dropna(subset=["start"]).sort_values("start")
                    if w.empty:
                        st.error("Windowed metrics contain no valid timestamps.")
                    else:
                        max_tests = 12000
                        if est_tests > max_tests:
                            st.error(
                                f"Requested scan is too large ({est_tests} tests). "
                                f"Reduce predictors/targets/lag range (max {max_tests})."
                            )
                        else:
                            rows: List[pd.DataFrame] = []
                            _sa_console_reset("Correlation scan")
                            try:
                                t0 = time.monotonic()
                                _sa_console_log(f"predictors={list(predictors_selected)}")
                                _sa_console_log(f"targets={list(target_metrics)}")
                                _sa_console_log(f"lags={list(lags)} merge_tol_minutes={int(merge_tolerance)}")
                                _sa_console_log(f"use_all_value_cols={bool(use_all_value_cols)} est_tests={int(est_tests)}")

                                # Progress is based on alignment attempts (predictor/value_col/lag).
                                total_align_steps = 0
                                for pred_key in predictors_selected:
                                    b = bundles.get(pred_key)
                                    if not b or not b.value_columns:
                                        continue
                                    total_align_steps += (
                                        len(b.value_columns) if bool(use_all_value_cols) else 1
                                    ) * len(lags)
                                total_align_steps = max(int(total_align_steps), 1)
                                align_step = 0
                                rows_built = 0

                                for pred_key in predictors_selected:
                                    bundle = bundles.get(pred_key)
                                    if not bundle or bundle.frame.empty:
                                        _sa_console_log(f"SKIP predictor={pred_key}: empty/unavailable frame")
                                        continue
                                    df = bundle.frame.copy()
                                    tcol = bundle.time_column
                                    df[tcol] = pd.to_datetime(df[tcol], errors="coerce", utc=True)
                                    if not bundle.value_columns:
                                        _sa_console_log(f"SKIP predictor={pred_key}: no value_columns")
                                        continue
                                    value_cols = (
                                        list(bundle.value_columns)
                                        if bool(use_all_value_cols)
                                        else [bundle.value_columns[0]]
                                    )
                                    _sa_console_log(
                                        f"Predictor={pred_key} title='{bundle.spec.title}' "
                                        f"time_col='{tcol}' value_cols={value_cols}"
                                    )

                                    for value_col in value_cols:
                                        if value_col not in df.columns:
                                            _sa_console_log(f"SKIP value_col='{value_col}': missing in frame")
                                            continue
                                        pred = df[[tcol, value_col]].dropna().sort_values(tcol)
                                        if pred.empty:
                                            _sa_console_log(f"SKIP value_col='{value_col}': empty after dropna")
                                            continue
                                        _sa_console_log(
                                            f"Value column='{value_col}' rows={int(pred.shape[0])} "
                                            f"range=[{pred[tcol].min()} → {pred[tcol].max()}]"
                                        )

                                        for lag in lags:
                                            align_step += 1
                                            if align_step % 5 == 0 or align_step == 1:
                                                _sa_console_set_progress(float(align_step) / float(total_align_steps))
                                            aligned = align_space_weather_series(
                                                reference_times=w["start"],
                                                predictor_df=pred,
                                                predictor_time_col=tcol,
                                                predictor_value_col=value_col,
                                                lag_hours=int(lag),
                                                max_gap_minutes=int(merge_tolerance),
                                            )
                                            if aligned.empty:
                                                if align_step % 25 == 0:
                                                    _sa_console_log(
                                                        f"lag={int(lag)}h: alignment empty (no overlap within tolerance)"
                                                    )
                                                continue
                                            merged = (
                                                w.set_index("start")
                                                .join(aligned.rename("predictor"), how="inner")
                                                .dropna(subset=["predictor"])
                                            )
                                            n = int(merged.shape[0])
                                            if n == 0:
                                                continue
                                            corr_df = _corr_table(
                                                merged.reset_index(drop=True),
                                                "predictor",
                                                list(target_metrics),
                                            )
                                            if corr_df.empty:
                                                continue
                                            corr_df["predictor_key"] = pred_key
                                            corr_df["predictor_title"] = bundle.spec.title
                                            corr_df["value_column"] = value_col
                                            corr_df["unit"] = (
                                                bundle.units.get(value_col) if bundle.units else None
                                            )
                                            corr_df["lag_hours"] = int(lag)
                                            rows.append(corr_df)
                                            rows_built += int(corr_df.shape[0])
                                            if rows_built % 100 == 0:
                                                _sa_console_log(
                                                    f"progress: align_steps={align_step}/{total_align_steps} "
                                                    f"result_rows={rows_built} (last merge n={n}, lag={int(lag)}h)"
                                                )

                                dt_ms = (time.monotonic() - t0) * 1000.0
                                _sa_console_log(
                                    f"Correlation scan loop finished in {dt_ms:.0f} ms. "
                                    f"Built result rows={rows_built} (pre-FDR)."
                                )
                                _sa_console_done("Correlation scan completed")
                            except Exception as exc:
                                log_exception(_LOGGER, "Space Analytics correlation scan failed", exc)
                                _sa_console_error("Correlation scan failed", exc)
                                st.error(f"Correlation scan failed: {exc}")
                                rows = []

                            result_df = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
                            if result_df.empty:
                                st.info("No correlations could be computed for the selected configuration.")
                            else:
                                # Multiple-comparisons correction
                                pvals = pd.to_numeric(result_df["p_value"], errors="coerce").fillna(1.0).to_numpy(dtype=float)
                                qvals, _ = fdr_bh(pvals, alpha=0.05)
                                result_df["q_value"] = qvals
                                result_df["abs_r"] = result_df["pearson_r"].abs()
                                result_df = result_df.sort_values(
                                    ["abs_r", "q_value"],
                                    ascending=[False, True],
                                    ignore_index=True,
                                )

                                st.session_state["space_analytics_corr_results"] = {
                                    "computed_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                                    "params": {
                                        "predictors": list(predictors_selected),
                                        "targets": list(target_metrics),
                                        "lags": list(lags),
                                        "merge_tol_minutes": int(merge_tolerance),
                                        "all_value_cols": bool(use_all_value_cols),
                                    },
                                    "results": result_df,
                                }
                                st.success("Correlation scan completed.")

            stored = st.session_state.get("space_analytics_corr_results")
            if isinstance(stored, dict) and isinstance(stored.get("results"), pd.DataFrame):
                out_df = stored["results"]
                with st.expander("✅ Correlation results (saved for this session)", expanded=True):
                    clear_corr_clicked = st.button(
                        "🧹 Clear correlation results",
                        key="space_analytics_clear_corr",
                        help="Removes the currently saved correlation table for this session.",
                    )
                    if clear_corr_clicked:
                        st.session_state.pop("space_analytics_corr_results", None)
                        st.success("Correlation results cleared.")
                    else:
                        st.caption(f"Computed: {stored.get('computed_at_utc', 'unknown')}")
                        st.dataframe(out_df.head(250), use_container_width=True)
                        st.download_button(
                            "⬇️ Download correlations (CSV)",
                            data=out_df.to_csv(index=False).encode("utf-8"),
                            file_name="space_analytics_correlations.csv",
                            mime="text/csv",
                            key="space_analytics_corr_download",
                        )

        st.markdown("---")

        # ------------------------------------------------------------------
        # ML suite (button-driven; GPU boosting when available)
        # ------------------------------------------------------------------
        st.markdown("#### 🤖 ML Suite (Predict HRV/HRF from lagged space-data features)")
        if not has_windowed or not has_noaa:
            st.info("Load windowed HRV/HRF metrics and NOAA datasets to enable ML.")
        else:
            bundles = dict(noaa_state.get("bundles", {}))
            dataset_options = sorted(bundles.keys())
            default_ml_predictors = [
                k for k in ("planetary_k_index_3h", "geospace_dst", "f107_flux", "solar_wind_wind", "solar_wind_mag") if k in dataset_options
            ]
            sa_ui_locked = str(_space_analytics_console_state().get("phase", "")) == "running"

            # ML target choices: numeric columns only
            ml_numeric_cols = [
                c
                for c in analytics_windowed_df.columns
                if c not in ("start", "end")
                and pd.api.types.is_numeric_dtype(analytics_windowed_df[c])
            ]
            if not ml_numeric_cols:
                st.info("No numeric HRV/HRF metrics are available for ML on the current windows.")
                run_ml = False
                ml_predictors = []
                ml_target = ""
                ml_lag_min, ml_lag_max = -24, 24
                ml_lag_step = 6
                ml_merge_tol = 90
            else:
                with st.form("space_analytics_ml_form", clear_on_submit=False):
                    ml_predictors = st.multiselect(
                        "Predictors (NOAA datasets)",
                        options=dataset_options,
                        default=default_ml_predictors,
                        key="space_analytics_ml_predictors",
                        disabled=bool(sa_ui_locked),
                    )
                    ml_target = st.selectbox(
                        "Target metric (HRV or HRF)",
                        options=sorted(ml_numeric_cols),
                        index=0,
                        key="space_analytics_ml_target",
                        disabled=bool(sa_ui_locked),
                    )
                    ml_lag_min, ml_lag_max = st.slider(
                        "Lag window (hours) — ML features",
                        min_value=-72,
                        max_value=72,
                        value=(-24, 24),
                        step=1,
                        key="space_analytics_ml_lag_range",
                        disabled=bool(sa_ui_locked),
                    )
                    ml_lag_step = st.number_input(
                        "Lag step (hours) — ML",
                        min_value=1,
                        max_value=24,
                        value=6,
                        step=1,
                        key="space_analytics_ml_lag_step",
                        disabled=bool(sa_ui_locked),
                    )
                    ml_merge_tol = st.number_input(
                        "Merge tolerance (minutes) — ML",
                        min_value=15,
                        max_value=240,
                        value=90,
                        step=15,
                        key="space_analytics_ml_merge_tol",
                        disabled=bool(sa_ui_locked),
                    )
                    run_ml = st.form_submit_button(
                        "🚀 Train models (ElasticNet + RF + Boosting if available)",
                        disabled=(not bool(ml_predictors)) or (not bool(ml_target)) or bool(sa_ui_locked),
                    )

            if run_ml:
                if "start" not in analytics_windowed_df.columns:
                    st.error("Windowed metrics are missing the required 'start' timestamp column.")
                else:
                    lags_ml = list(
                        range(
                            int(ml_lag_min),
                            int(ml_lag_max) + 1,
                            int(max(int(ml_lag_step), 1)),
                        )
                    )
                    if len(lags_ml) > 97:
                        st.warning("Lag configuration is too large; reducing to the first 97 lags.")
                        lags_ml = lags_ml[:97]
                    _sa_console_reset("ML: build feature matrix + train models")
                    try:
                        t0 = time.monotonic()
                        _sa_console_log(f"predictors={list(ml_predictors)} target={str(ml_target)}")
                        _sa_console_log(f"lags={list(lags_ml)} merge_tol_minutes={int(ml_merge_tol)}")
                        _sa_console_set_progress(0.05)
                        _sa_console_log("Building feature matrix…")
                        full_matrix = _build_space_weather_feature_matrix(
                            analytics_windowed_df,
                            bundles,
                            ml_predictors,
                            lags_ml,
                            merge_tolerance_minutes=int(ml_merge_tol),
                        )
                        _sa_console_set_progress(0.45)
                        _sa_console_log(
                            f"Feature matrix built: rows={int(full_matrix.shape[0])} cols={int(full_matrix.shape[1])}"
                        )
                    except Exception as exc:
                        log_exception(_LOGGER, "Space Analytics feature matrix build failed", exc)
                        _sa_console_error("ML feature matrix build failed", exc)
                        st.error(f"Feature matrix build failed: {exc}")
                        full_matrix = pd.DataFrame()
                    if full_matrix.empty:
                        st.error("No feature matrix could be built (insufficient overlap with predictors).")
                    else:
                        # Keep only lagged predictor columns + target (+ start)
                        feature_cols = [
                            c
                            for c in full_matrix.columns
                            if c not in ("start", ml_target)
                            and c.startswith(tuple(f"{k}_" for k in ml_predictors))
                        ]
                        if not feature_cols:
                            st.error("No lagged predictor features were built. Try fewer predictors, smaller lag range, or larger merge tolerance.")
                        else:
                            ml_df = full_matrix[["start", ml_target] + feature_cols].copy()
                            usable_rows = int(ml_df.dropna().shape[0])
                            st.caption(
                                f"ML usable samples: **{usable_rows}** / {int(ml_df.shape[0])} windows | "
                                f"Features: **{len(feature_cols)}**"
                            )
                            _sa_console_log(f"Lagged features: {len(feature_cols)}")
                            _sa_console_log(f"Usable complete windows (dropna): {usable_rows}")
                            if usable_rows < 30:
                                st.error(
                                    "Not enough samples for ML. This ML suite requires **≥30** complete windows after "
                                    "merging predictors. Reduce window/step to create more windows, or upload a longer recording."
                                )
                                _sa_console_done("ML stopped (insufficient samples)")
                            else:
                                _sa_console_set_progress(0.55)
                                _sa_console_log("Training ML models (ElasticNet + RF + Boosting if available)…")
                                try:
                                    ml_results = _run_ml_models_space_weather(
                                        ml_df,
                                        target_metric=str(ml_target),
                                    )
                                    dt_ms = (time.monotonic() - t0) * 1000.0
                                    _sa_console_set_progress(0.98)
                                    _sa_console_log(f"Training completed in {dt_ms:.0f} ms.")
                                    st.session_state["space_analytics_ml_results"] = {
                                        "computed_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                                        "params": {
                                            "predictors": list(ml_predictors),
                                            "target": str(ml_target),
                                            "lags": list(lags_ml),
                                            "merge_tol_minutes": int(ml_merge_tol),
                                            "gpu_enabled": bool(gpu_enabled),
                                        },
                                        "results": ml_results,
                                    }
                                    _sa_console_done("ML training completed")
                                    st.success("ML training completed.")
                                except Exception as exc:
                                    log_exception(_LOGGER, "Space Analytics ML training failed", exc)
                                    _sa_console_error("ML training failed", exc)
                                    st.error(f"ML training failed: {exc}")

            stored_ml = st.session_state.get("space_analytics_ml_results")
            if isinstance(stored_ml, dict) and isinstance(stored_ml.get("results"), dict):
                with st.expander("✅ ML results (saved for this session)", expanded=True):
                    clear_ml_clicked = st.button(
                        "🧹 Clear ML results",
                        key="space_analytics_clear_ml",
                        help="Removes the currently saved ML training outputs for this session.",
                    )
                    if clear_ml_clicked:
                        st.session_state.pop("space_analytics_ml_results", None)
                        st.success("ML results cleared.")
                    else:
                        st.caption(f"Computed: {stored_ml.get('computed_at_utc', 'unknown')}")
                        st.json(stored_ml.get("results", {}))

    with tab_export:
        # ---------------------------------------------------------------------
        # EXPORT TAB — Always loads with basic options regardless of data state
        # ---------------------------------------------------------------------
        st.markdown("### 📄 Export & Download")
        st.caption("Export HRV analysis results, user profile data, and cohort summaries.")

        # Section 1: Current HRV Data Export (single-file)
        st.markdown("---")
        st.markdown("#### 📊 Current HRV Analysis")
        if has_hrv_data and not windowed_df.empty:
            st.success(f"✅ HRV data loaded: {len(windowed_df)} windows available for export.")
            # IMPORTANT: Do not build CSV/JSON payloads on every rerun. Streamlit tabs are not lazy;
            # expensive serialization would slow down *all* tabs. Prepare exports explicitly.
            export_hrv_state = st.session_state.setdefault(
                "export_current_hrv_state",
                {
                    "signature": "",
                    "csv_bytes": b"",
                    "json_bytes": b"",
                    "generated_at_utc": "",
                    "rows": 0,
                },
            )
            try:
                settings_hash = compute_settings_hash(
                    str(method), float(max_dev), int(median_win), win, step
                )
            except Exception:
                settings_hash = "unknown"
            export_sig_payload = {
                "uploads": list(upload_signature) if isinstance(upload_signature, tuple) else [],
                "settings_hash": str(settings_hash),
                "rows": int(windowed_df.shape[0]),
                "cols": int(windowed_df.shape[1]),
            }
            export_sig = hashlib.sha256(
                json.dumps(export_sig_payload, sort_keys=True).encode("utf-8", errors="ignore")
            ).hexdigest()

            col_prep, col_status = st.columns([1, 3])
            with col_prep:
                prepare_exports = st.button(
                    "🧾 Prepare HRV export files",
                    key="export_prepare_current_hrv",
                    type="primary",
                    help="Generates CSV + JSON payloads once (cached in-session) for download.",
                )
            with col_status:
                if export_hrv_state.get("signature") == export_sig and export_hrv_state.get("csv_bytes"):
                    st.caption(
                        f"Prepared: {export_hrv_state.get('rows', 0)} rows "
                        f"({export_hrv_state.get('generated_at_utc', 'unknown')})."
                    )
                else:
                    st.caption("Not prepared yet (keeps tab switches fast).")

            if prepare_exports:
                with st.spinner("Preparing CSV/JSON exports…"):
                    csv_bytes = windowed_df.to_csv(index=False).encode("utf-8")
                    json_bytes = windowed_df.to_json(
                        orient="records",
                        indent=2,
                    ).encode("utf-8")
                export_hrv_state["signature"] = export_sig
                export_hrv_state["csv_bytes"] = csv_bytes
                export_hrv_state["json_bytes"] = json_bytes
                export_hrv_state["generated_at_utc"] = pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                export_hrv_state["rows"] = int(windowed_df.shape[0])
                st.success("HRV export files prepared.")

            if export_hrv_state.get("signature") == export_sig and export_hrv_state.get("csv_bytes"):
                col_exp1, col_exp2 = st.columns(2)
                with col_exp1:
                    st.download_button(
                        "⬇️ Download HRV Metrics (CSV)",
                        data=export_hrv_state["csv_bytes"],
                        file_name=f"hrv_metrics_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv",
                        mime="text/csv",
                        key="export_tab_hrv_csv",
                        use_container_width=True,
                    )
                with col_exp2:
                    st.download_button(
                        "⬇️ Download HRV Metrics (JSON)",
                        data=export_hrv_state["json_bytes"],
                        file_name=f"hrv_metrics_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json",
                        mime="application/json",
                        key="export_tab_hrv_json",
                        use_container_width=True,
                    )
            else:
                st.info("Click **Prepare HRV export files** to enable downloads.")
        else:
            st.info("📤 Upload RR interval data to enable HRV export.")

        # Section 2: Cohort/Group Export
        st.markdown("---")
        st.subheader("👥 Group Summaries (Cohort Export)")
        if not USER_PROFILE_TAB_AVAILABLE:
            st.info("Cohort export requires the User Profile module.")
        else:
            try:
                active_users = get_all_active_users()
            except Exception as exc:
                log_exception(_LOGGER, "Failed to load active users for export tab", exc)
                active_users = []
            if not active_users:
                st.info(
                    "No active cohort detected. Open 2+ user sessions (User Profile tab) to enable cohort export."
                )
            else:
                # Build label map for selection UI
                user_label_map: Dict[str, str] = {}
                user_ids: List[str] = []
                for row in active_users:
                    uid = str(row.get("user_id", "")).strip()
                    if not uid:
                        continue
                    name = (
                        str(row.get("full_name") or row.get("username") or uid)
                        .strip()
                    )
                    user_label_map[uid] = name
                    user_ids.append(uid)
                user_ids = sorted(user_ids, key=lambda k: user_label_map.get(k, k))

                selected_user_ids = st.multiselect(
                    "Active users to include",
                    options=user_ids,
                    default=user_ids,
                    format_func=lambda uid: user_label_map.get(uid, uid),
                    key="cohort_export_user_select",
                )
                cohort_notes = st.text_area(
                    "Cohort notes (optional)",
                    placeholder="Protocol notes, cohort definition, inclusion/exclusion, etc.",
                    height=90,
                    key="cohort_export_notes",
                )

                generate_cohort = st.button(
                    "Generate cohort summary",
                    key="cohort_export_generate",
                )
                if generate_cohort:
                    try:
                        db = get_database()
                    except Exception as exc:  # pragma: no cover - defensive
                        log_exception(_LOGGER, "Failed to open database for cohort export", exc)
                        db = None

                    if not selected_user_ids:
                        st.warning("Select at least one user to continue.")
                    elif db is None:
                        st.error("Database unavailable. Check logs/errors.log for details.")
                    else:
                        cohort_rows: List[Dict[str, Any]] = []

                        # Use a bounded loop over selected users only
                        for uid in selected_user_ids:
                            try:
                                user = db.get_user(uid)
                            except Exception:
                                user = None
                            if user is None:
                                continue

                            # Latest HRV snapshot (no RR payload)
                            hrv_cols = [
                                "measurement_date",
                                "rmssd_ms",
                                "sdnn_ms",
                                "mean_hr_bpm",
                                "hf_power_ms2",
                                "lf_hf_ratio",
                                "parasympathetic_index",
                                "hrv_score",
                                "artifact_percentage",
                                "quality_score",
                            ]
                            try:
                                hrv_latest = db.get_hrv_dataframe(
                                    uid,
                                    limit=1,
                                    include_rr=False,
                                    columns=hrv_cols,
                                )
                            except Exception:
                                hrv_latest = pd.DataFrame()

                            hrv_row: Dict[str, Any] = {}
                            if isinstance(hrv_latest, pd.DataFrame) and not hrv_latest.empty:
                                hrv_row = (
                                    hrv_latest.iloc[0].to_dict()
                                    if len(hrv_latest.index) > 0
                                    else {}
                                )

                            # Latest clinical scales
                            try:
                                scales = db.get_clinical_scales_history(uid, limit=1)
                            except Exception:
                                scales = []
                            scales_row: Dict[str, Any] = {}
                            if scales:
                                scales_row = scales[0].to_dict()

                            # Latest medical record (Exploration Medical / ExMC)
                            try:
                                med_rows = db.get_medical_history(uid, limit=1)
                            except Exception:
                                med_rows = []
                            med_row: Dict[str, Any] = med_rows[0] if med_rows else {}

                            cohort_rows.append(
                                {
                                    "user_id": user.user_id,
                                    "username": user.username,
                                    "full_name": user.full_name,
                                    "sex": user.sex,
                                    "age_years": user.age_years,
                                    "bmi": user.bmi,
                                    # HRV (latest)
                                    "hrv_date": hrv_row.get("measurement_date"),
                                    "rmssd_ms": hrv_row.get("rmssd_ms"),
                                    "sdnn_ms": hrv_row.get("sdnn_ms"),
                                    "mean_hr_bpm": hrv_row.get("mean_hr_bpm"),
                                    "hf_power_ms2": hrv_row.get("hf_power_ms2"),
                                    "lf_hf_ratio": hrv_row.get("lf_hf_ratio"),
                                    "parasympathetic_index": hrv_row.get("parasympathetic_index"),
                                    "hrv_score": hrv_row.get("hrv_score"),
                                    "artifact_pct": hrv_row.get("artifact_percentage"),
                                    "quality_score": hrv_row.get("quality_score"),
                                    # Clinical scales (latest)
                                    "scales_date": scales_row.get("assessment_date"),
                                    "ess": scales_row.get("epworth_sleepiness_scale"),
                                    "kss": scales_row.get("karolinska_sleepiness_scale"),
                                    "samn_perelli": scales_row.get("samn_perelli_fatigue"),
                                    "vas_fatigue": scales_row.get("vas_fatigue"),
                                    "panas_pa": scales_row.get("panas_positive_affect"),
                                    "panas_na": scales_row.get("panas_negative_affect"),
                                    # Exploration medical record (latest)
                                    "medical_updated_at": med_row.get("updated_at"),
                                    "mission_day": med_row.get("mission_day"),
                                    "radiation_dose_msv": med_row.get("radiation_dose_msv"),
                                    "eva_hours_72h": med_row.get("eva_hours_72h"),
                                    "days_since_last_eva": med_row.get("days_since_last_eva"),
                                    "confinement_stress": med_row.get("confinement_stress"),
                                    "workload_rating": med_row.get("workload_rating"),
                                }
                            )

                        cohort_df = pd.DataFrame(cohort_rows)
                        if cohort_df.empty:
                            st.warning("No cohort rows could be assembled from the selected users.")
                        else:
                            stats_cols = [
                                "age_years",
                                "bmi",
                                "rmssd_ms",
                                "sdnn_ms",
                                "mean_hr_bpm",
                                "hf_power_ms2",
                                "lf_hf_ratio",
                                "parasympathetic_index",
                                "hrv_score",
                                "artifact_pct",
                                "quality_score",
                                "ess",
                                "kss",
                                "samn_perelli",
                                "vas_fatigue",
                                "panas_pa",
                                "panas_na",
                                "mission_day",
                                "radiation_dose_msv",
                                "eva_hours_72h",
                                "days_since_last_eva",
                                "confinement_stress",
                                "workload_rating",
                            ]
                            cohort_stats_df = compute_cohort_summary_stats(
                                cohort_df,
                                numeric_columns=stats_cols,
                            )

                            st.session_state["cohort_export_df"] = cohort_df
                            st.session_state["cohort_export_stats_df"] = cohort_stats_df
                            st.success("Cohort summary generated.")

                cohort_df = st.session_state.get("cohort_export_df")
                cohort_stats_df = st.session_state.get("cohort_export_stats_df")
                if isinstance(cohort_df, pd.DataFrame) and not cohort_df.empty:
                    st.markdown("##### Cohort roster preview")
                    st.dataframe(cohort_df, use_container_width=True)
                    csv_bytes = cohort_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Download cohort roster (CSV)",
                        data=csv_bytes,
                        file_name=f"cohort_roster_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv",
                        mime="text/csv",
                        key="download_cohort_roster_csv",
                    )
                if isinstance(cohort_stats_df, pd.DataFrame) and not cohort_stats_df.empty:
                    st.markdown("##### Cohort descriptive stats preview")
                    st.dataframe(cohort_stats_df, use_container_width=True)
                    csv_bytes = cohort_stats_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Download cohort stats (CSV)",
                        data=csv_bytes,
                        file_name=f"cohort_stats_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv",
                        mime="text/csv",
                        key="download_cohort_stats_csv",
                    )
                if isinstance(cohort_df, pd.DataFrame) and not cohort_df.empty:
                    cohort_md_config = CohortExportConfiguration(scope=ExportScope.SUMMARY)
                    try:
                        cohort_md = build_cohort_markdown_report(
                            cohort_df=cohort_df,
                            cohort_stats_df=(
                                cohort_stats_df
                                if isinstance(cohort_stats_df, pd.DataFrame)
                                else pd.DataFrame()
                            ),
                            config=cohort_md_config,
                            additional_notes=cohort_notes,
                        )
                    except Exception as exc:
                        st.warning(f"Cohort markdown export failed: {exc}")
                    else:
                        st.text_area("Cohort report preview", cohort_md, height=280)
                        st.download_button(
                            "Download cohort report (Markdown)",
                            data=cohort_md.encode("utf-8"),
                            file_name=f"cohort_report_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.md",
                            mime="text/markdown",
                            key="download_cohort_report_md",
                        )

                # ---------------------------------------------------------------------
                # Mission FRMS v2 (crew risk board) - prototype aggregation across roster
                # ---------------------------------------------------------------------
                with st.expander("🛡️ Mission FRMS v2 — Crew Risk Board (multi-profile)", expanded=False):
                    st.caption(
                        "Prototype mission-level FRMS aggregation across selected active users. "
                        "This runs a bounded SAFTE forecast per user (wrist → clinical → Garmin → defaults) "
                        "and computes FRMS exposure + risk matrix classification for a shared scope window."
                    )

                    if not (FATIGUE_AVAILABLE and FRMS_AVAILABLE and FRMS_V2_AVAILABLE):
                        st.info(
                            "Mission FRMS v2 requires the fatigue + FRMS modules. "
                            "If this environment is missing them, use the single-user SAFTE tab FRMS dashboard."
                        )
                    elif not selected_user_ids:
                        st.info("Select at least one active user above to build a crew risk board.")
                    else:
                        col_cfg_a, col_cfg_b, col_cfg_c = st.columns(3)
                        with col_cfg_a:
                            frms2_days = st.number_input(
                                "Forecast horizon (days)",
                                min_value=1,
                                max_value=7,
                                value=5,
                                step=1,
                                key="frms_v2_days",
                                help="Number of days simulated per crew member (bounded).",
                            )
                            frms2_model = st.selectbox(
                                "SAFTE model",
                                options=["advanced", "classic"],
                                index=0,
                                key="frms_v2_model",
                                help="Matches the SAFTE tab engine; use 'advanced' unless validating classic behavior.",
                            )
                        with col_cfg_b:
                            scope_mode = st.selectbox(
                                "Scope for FRMS exposure metrics",
                                options=["all_hours", "duty_window"],
                                index=1,
                                key="frms_v2_scope_mode",
                                help="Risk exposure can be computed for all forecast hours or only a duty window.",
                            )
                            duty_start = st.slider(
                                "Duty window start (hour, local)",
                                min_value=0,
                                max_value=23,
                                value=9,
                                step=1,
                                disabled=(scope_mode != "duty_window"),
                                key="frms_v2_duty_start",
                            )
                            duty_end = st.slider(
                                "Duty window end (hour, local)",
                                min_value=0,
                                max_value=23,
                                value=17,
                                step=1,
                                disabled=(scope_mode != "duty_window"),
                                key="frms_v2_duty_end",
                            )
                            include_weekends = st.checkbox(
                                "Include weekends in duty scope",
                                value=False,
                                disabled=(scope_mode != "duty_window"),
                                key="frms_v2_include_weekends",
                            )
                        with col_cfg_c:
                            wocl_start = st.slider(
                                "WOCL start (hour, local)",
                                min_value=0,
                                max_value=23,
                                value=2,
                                step=1,
                                key="frms_v2_wocl_start",
                            )
                            wocl_end = st.slider(
                                "WOCL end (hour, local)",
                                min_value=0,
                                max_value=23,
                                value=6,
                                step=1,
                                key="frms_v2_wocl_end",
                            )
                            th_low = st.number_input(
                                "Low-risk threshold (effectiveness, %)",
                                min_value=50.0,
                                max_value=100.0,
                                value=90.0,
                                step=1.0,
                                key="frms_v2_th_low",
                            )
                            th_high = st.number_input(
                                "High-risk threshold (effectiveness, %)",
                                min_value=50.0,
                                max_value=100.0,
                                value=77.0,
                                step=1.0,
                                key="frms_v2_th_high",
                            )
                            th_severe = st.number_input(
                                "Severe threshold (effectiveness, %)",
                                min_value=50.0,
                                max_value=100.0,
                                value=70.0,
                                step=1.0,
                                key="frms_v2_th_severe",
                            )

                        run_board = st.button(
                            "Run crew risk board (FRMS v2)",
                            type="primary",
                            key="frms_v2_run_board",
                        )

                        def _chronotype_offset_from_occupation(occupation: Any) -> float:
                            occ = str(occupation or "").lower()
                            if any(x in occ for x in ["night", "shift", "pilot", "flight"]):
                                return 1.0
                            if any(x in occ for x in ["early", "morning", "farmer"]):
                                return -1.0
                            return 0.0

                        if run_board:
                            db = get_database()
                            members: list[CrewMemberFRMS] = []
                            errors: list[str] = []

                            thresholds = FRMSThresholds(
                                low_risk_min_effectiveness=float(th_low),
                                high_risk_max_effectiveness=float(th_high),
                                severe_impairment_max_effectiveness=float(th_severe),
                                wocl_start_hour=int(wocl_start),
                                wocl_end_hour=int(wocl_end),
                            )

                            cfg = {
                                "prediction_days": int(frms2_days),
                                "safte_model": str(frms2_model),
                                "scope_mode": str(scope_mode),
                                "duty_window": {
                                    "start_hour": int(duty_start),
                                    "end_hour": int(duty_end),
                                    "include_weekends": bool(include_weekends),
                                },
                                "wocl": {"start_hour": int(wocl_start), "end_hour": int(wocl_end)},
                                "thresholds": {
                                    "low_risk_min_effectiveness": float(th_low),
                                    "high_risk_max_effectiveness": float(th_high),
                                    "severe_impairment_max_effectiveness": float(th_severe),
                                },
                            }

                            with st.spinner("Running bounded SAFTE forecasts and aggregating FRMS metrics…"):
                                for uid in list(selected_user_ids)[:13]:
                                    try:
                                        user = db.get_user(str(uid))
                                    except Exception:
                                        user = None
                                    if user is None:
                                        errors.append(f"User {uid} missing from database.")
                                        continue

                                    user_context = {
                                        "age_years": int(getattr(user, "age_years", 35) or 35),
                                        "sex": str(getattr(user, "sex", "other") or "other"),
                                        "chronotype_offset": _chronotype_offset_from_occupation(getattr(user, "occupation", None)),
                                        "genetic_profile": tuple(),
                                    }

                                    try:
                                        result, source_label, _wrist_df = run_assessment_fatigue_prediction(
                                            user_context=user_context,
                                            user_id=str(uid),
                                            prediction_days=int(frms2_days),
                                            model_type=str(frms2_model),
                                        )
                                    except Exception as exc:
                                        errors.append(f"{user.full_name or user.username or uid}: fatigue run failed ({exc}).")
                                        continue

                                    df_fatigue = build_fatigue_dataframe(
                                        result.time_points,
                                        result.performances,
                                        result.circadian_values,
                                    )
                                    try:
                                        dt_list = list(df_fatigue["DateTime"])
                                        eff_list = [float(x) for x in df_fatigue["Performance"].astype(float).tolist()]
                                    except Exception as exc:
                                        errors.append(f"{user.full_name or user.username or uid}: invalid fatigue series ({exc}).")
                                        continue

                                    hours_per_sample = 1.0
                                    if len(dt_list) >= 2:
                                        try:
                                            delta_sec = float((dt_list[1] - dt_list[0]).total_seconds())
                                            if delta_sec > 0:
                                                hours_per_sample = max(1.0 / 60.0, min(24.0, delta_sec / 3600.0))
                                        except Exception:
                                            hours_per_sample = 1.0

                                    wocl_mask = compute_wocl_mask(
                                        dt_list,
                                        wocl_start_hour=int(wocl_start),
                                        wocl_end_hour=int(wocl_end),
                                    )
                                    if scope_mode == "duty_window":
                                        scope_mask = compute_duty_mask(
                                            dt_list,
                                            has_work_schedule=True,
                                            work_start_hour=int(duty_start),
                                            work_end_hour=int(duty_end),
                                            include_weekends=bool(include_weekends),
                                        )
                                    else:
                                        scope_mask = [True for _ in dt_list]

                                    try:
                                        exposure = compute_frms_exposure_metrics(
                                            datetimes=dt_list,
                                            effectiveness=eff_list,
                                            scope_mask=scope_mask,
                                            wocl_mask=wocl_mask,
                                            thresholds=thresholds,
                                            hours_per_sample=float(hours_per_sample),
                                        )
                                        classification = classify_frms_risk(exposure, thresholds=thresholds)
                                        alerts = tuple(
                                            compute_frms_alerts(
                                                exposure=exposure,
                                                classification=classification,
                                                crew_rest=None,
                                                thresholds=thresholds,
                                            )
                                        )
                                    except Exception as exc:
                                        errors.append(f"{user.full_name or user.username or uid}: FRMS metrics failed ({exc}).")
                                        continue

                                    members.append(
                                        CrewMemberFRMS(
                                            user_id=str(uid),
                                            display_name=str(user.full_name or user.username or uid),
                                            data_source=str(source_label),
                                            exposure=exposure,
                                            classification=classification,
                                            alerts=alerts,
                                        )
                                    )

                            if errors:
                                st.warning("Some crew members could not be processed:\n" + "\n".join([f"- {e}" for e in errors[:8]]))

                            if not members:
                                st.error("No crew members were successfully processed. See warnings above.")
                            else:
                                board = build_crew_risk_board(members=members, config=cfg)
                                st.session_state["frms_v2_board"] = board
                                st.success("Crew risk board generated.")

                        board = st.session_state.get("frms_v2_board")
                        if board is not None:
                            try:
                                counts = dict(board.risk_level_counts)
                                col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                                with col_s1:
                                    st.metric("Crew size", str(len(board.members)))
                                with col_s2:
                                    st.metric("Worst risk level", str(board.worst_risk_level))
                                with col_s3:
                                    st.metric("High", str(int(counts.get("High", 0))))
                                with col_s4:
                                    st.metric("Extreme", str(int(counts.get("Extreme", 0))))

                                # Visualization: distribution of risk levels across crew
                                levels = ["Low", "Medium", "High", "Extreme", "Unknown"]
                                dist_values = [int(counts.get(k, 0)) for k in levels]
                                dist_chart = {
                                    "title": {
                                        "text": "Crew FRMS risk distribution",
                                        "left": "center",
                                        "textStyle": {"fontSize": 14},
                                    },
                                    "tooltip": {"trigger": "axis"},
                                    "toolbox": {
                                        "show": True,
                                        "right": 10,
                                        "feature": {
                                            "saveAsImage": {"show": True, "title": "Save (PNG)", "pixelRatio": 4},
                                            "restore": {"show": True, "title": "Reset"},
                                        },
                                    },
                                    "xAxis": {"type": "category", "data": levels, "name": "FRMS risk level"},
                                    "yAxis": {"type": "value", "name": "Crew members (count)", "minInterval": 1},
                                    "series": [
                                        {
                                            "type": "bar",
                                            "data": dist_values,
                                            "itemStyle": {
                                                "color": {
                                                    "type": "linear",
                                                    "x": 0,
                                                    "y": 0,
                                                    "x2": 0,
                                                    "y2": 1,
                                                    "colorStops": [
                                                        {"offset": 0, "color": "#2E86AB"},
                                                        {"offset": 1, "color": "#2E86AB55"},
                                                    ],
                                                }
                                            },
                                            "label": {"show": True, "position": "top"},
                                        }
                                    ],
                                    "grid": {"left": "10%", "right": "5%", "bottom": "15%", "top": "20%"},
                                }
                                render_echarts(dist_chart, height_px=320, config=EChartsConfig())
                                st.caption(
                                    "Bar chart of crew-member counts by FRMS risk level (x-axis) computed from SAFTE "
                                    "effectiveness forecasts. Y-axis is the number of crew members classified into each "
                                    "risk level for the selected scope window (all hours or duty window)."
                                )

                                # Table
                                rows = []
                                for m in board.members:
                                    rows.append(
                                        {
                                            "user_id": m.user_id,
                                            "name": m.display_name,
                                            "data_source": m.data_source,
                                            "risk_level": m.classification.risk_level,
                                            "severity": m.classification.severity,
                                            "likelihood": m.classification.likelihood,
                                            "min_effectiveness_pct": m.exposure.min_effectiveness,
                                            "hours_at_or_below_77_h": m.exposure.hours_at_or_below_77,
                                            "hours_at_or_below_70_h": m.exposure.hours_at_or_below_70,
                                            "pct_hours_in_wocl_pct": m.exposure.pct_hours_in_wocl,
                                            "alerts_n": len(m.alerts),
                                        }
                                    )
                                board_df = pd.DataFrame(rows)
                                st.dataframe(board_df, use_container_width=True)

                                # Data exports
                                csv_bytes = board_df.to_csv(index=False).encode("utf-8")
                                st.download_button(
                                    "Download crew risk board (CSV)",
                                    data=csv_bytes,
                                    file_name=f"frms_v2_crew_risk_board_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv",
                                    mime="text/csv",
                                    key="frms_v2_board_csv",
                                )
                                board_payload = crew_risk_board_to_payload(board)
                                st.download_button(
                                    "Download crew risk board payload (JSON)",
                                    data=json.dumps(board_payload, ensure_ascii=False, default=str, indent=2).encode("utf-8"),
                                    file_name=f"frms_v2_crew_risk_board_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json",
                                    mime="application/json",
                                    key="frms_v2_board_json",
                                )

                                # Decision log (audit trail)
                                st.markdown("##### Decision log (audit trail export)")
                                col_d1, col_d2 = st.columns(2)
                                with col_d1:
                                    decision_owner = st.text_input(
                                        "Decision owner",
                                        value=str(active_user_context.get("full_name") or active_user_context.get("username") or ""),
                                        key="frms_v2_decision_owner",
                                        help="Who is signing the operational decision (e.g., Flight Surgeon, Mission Director).",
                                    )
                                    decision = st.selectbox(
                                        "Decision",
                                        options=["GO", "GO_WITH_MITIGATIONS", "NO_GO"],
                                        index=1,
                                        key="frms_v2_decision",
                                    )
                                with col_d2:
                                    mitigations_text = st.text_area(
                                        "Mitigations (one per line)",
                                        placeholder="e.g.\n- 20-min controlled rest (if permitted)\n- Task reallocation during WOCL\n- Caffeine timing plan",
                                        height=120,
                                        key="frms_v2_mitigations",
                                    )
                                decision_notes = st.text_area(
                                    "Decision notes (optional)",
                                    placeholder="Constraints, waivers, operational context, residual risk acceptance, follow-up plan…",
                                    height=90,
                                    key="frms_v2_decision_notes",
                                )
                                mitigations = [
                                    ln.strip(" -\t")
                                    for ln in str(mitigations_text or "").splitlines()
                                    if ln.strip(" -\t")
                                ]
                                entry = build_decision_log_entry(
                                    board=board,
                                    decision=str(decision),
                                    decision_owner=str(decision_owner),
                                    mitigations=mitigations,
                                    notes=str(decision_notes),
                                )
                                st.download_button(
                                    "Download FRMS decision log entry (JSON)",
                                    data=json.dumps(entry.to_payload(), ensure_ascii=False, default=str, indent=2).encode("utf-8"),
                                    file_name=f"frms_v2_decision_log_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json",
                                    mime="application/json",
                                    key="frms_v2_decision_log_json",
                                )
                            except Exception as exc:
                                st.warning(f"Unable to render crew risk board: {exc}")

                with st.expander("🧪 Longitudinal cohort comparisons (T0–T21)", expanded=False):
                    st.markdown(
                        "Compare **within-subject changes** across groups using your saved longitudinal "
                        "timepoint tags (T0…T21). This computes each subject’s Δ vs their own baseline, "
                        "then compares Δ distributions between groups per timepoint and metric."
                    )

                    if not selected_user_ids:
                        st.info("Select at least one active user above to enable longitudinal comparisons.")
                    else:
                        # Persisted cohort grouping (roadmap "best next task"):
                        # store study groups + subject assignments in SQLite, then reuse for exports.
                        db = get_database()
                        study_id = st.text_input(
                            "Study ID (persisted)",
                            value=str(st.session_state.get("cohort_study_id", "default_study")),
                            key="cohort_study_id",
                            help="A short identifier for your cohort study (e.g., 'trial_2026_q1').",
                        ).strip()
                        if not study_id:
                            st.warning("Enter a Study ID to manage persisted group assignments.")
                            study_id = "default_study"

                        try:
                            groups = db.list_study_groups(study_id, limit=50)
                        except Exception as exc:
                            groups = []
                            st.warning(f"Unable to load study groups: {exc}")

                        group_name_to_id: Dict[str, str] = {
                            str(g.group_name): str(g.group_id) for g in groups
                        }
                        group_names = sorted([str(g.group_name) for g in groups if g.group_name])

                        col_groups_a, col_groups_b = st.columns([3, 2])
                        with col_groups_a:
                            st.caption(
                                "Persisted groups are stored in `hrv_users.db` (tables: `study_groups`, `study_assignments`). "
                                "Use the roster editor to assign active users to groups for this Study ID."
                            )
                        with col_groups_b:
                            init_default_groups = st.button(
                                "Initialize groups: Control / Intervention",
                                key="cohort_init_default_groups",
                                help="Creates two default groups under this Study ID if they do not exist.",
                            )
                        if init_default_groups:
                            try:
                                _ = db.upsert_study_group(
                                    StudyGroup(group_id="", study_id=study_id, group_name="Control", description="Control arm")
                                )
                                _ = db.upsert_study_group(
                                    StudyGroup(group_id="", study_id=study_id, group_name="Intervention", description="Intervention arm")
                                )
                                groups = db.list_study_groups(study_id, limit=50)
                                group_name_to_id = {str(g.group_name): str(g.group_id) for g in groups}
                                group_names = sorted([str(g.group_name) for g in groups if g.group_name])
                                st.success("Default study groups initialized.")
                            except Exception as exc:
                                st.warning(f"Unable to initialize default groups: {exc}")

                        if not group_names:
                            st.info("Create at least one study group to proceed (e.g., Control/Intervention).")
                            roster_editor_df = pd.DataFrame()
                        else:
                            try:
                                roster_df = db.get_study_roster_dataframe(study_id, limit=2000)
                            except Exception as exc:
                                roster_df = pd.DataFrame()
                                st.warning(f"Unable to load study roster: {exc}")

                            if roster_df.empty:
                                st.info("No users found to build a roster.")
                                roster_editor_df = pd.DataFrame()
                            else:
                                roster_editor_df = roster_df[roster_df["user_id"].isin(selected_user_ids)].copy()
                                roster_editor_df = roster_editor_df[
                                    ["user_id", "full_name", "username", "group_name"]
                                ].copy()
                                roster_editor_df["group_name"] = roster_editor_df["group_name"].fillna("").astype(str)

                                if roster_editor_df.empty:
                                    st.info("Select at least one user to edit roster assignments.")
                                else:
                                    roster_sig_source = roster_editor_df["user_id"].astype(str).str.cat(sep="|")
                                    roster_signature = hashlib.sha1(
                                        roster_sig_source.encode("utf-8", errors="ignore")
                                    ).hexdigest()[:8]
                                    roster_key = f"cohort_roster_editor_{len(roster_editor_df)}_{roster_signature}"

                                    st.markdown("##### Persisted roster editor (active users)")
                                    edited_roster = st.data_editor(
                                        roster_editor_df,
                                        hide_index=True,
                                        use_container_width=True,
                                        disabled=["user_id", "full_name", "username"],
                                        column_config={
                                            "group_name": st.column_config.SelectboxColumn(
                                                "Group",
                                                options=[""] + group_names,
                                                help="Assign each active user to a group for this Study ID (blank = unassigned).",
                                            )
                                        },
                                        key=roster_key,
                                    )

                                    save_assignments = st.button(
                                        "Save study assignments",
                                        key=f"cohort_save_assignments_{roster_signature}",
                                        type="secondary",
                                    )
                                    if save_assignments:
                                        for row in edited_roster.itertuples(index=False):
                                            uid = str(getattr(row, "user_id"))
                                            gname = str(getattr(row, "group_name", "") or "").strip()
                                            if not gname:
                                                db.set_user_study_assignment(
                                                    user_id=uid,
                                                    study_id=study_id,
                                                    group_id=None,
                                                )
                                                continue
                                            gid = group_name_to_id.get(gname)
                                            if not gid:
                                                continue
                                            db.set_user_study_assignment(
                                                user_id=uid,
                                                study_id=study_id,
                                                group_id=gid,
                                            )
                                        st.success("Study assignments saved.")

                        # ---- Longitudinal analysis controls ----
                        if group_names:
                            col_cmp_a, col_cmp_b = st.columns(2)
                            with col_cmp_a:
                                group_a = st.selectbox(
                                    "Group A",
                                    options=group_names,
                                    index=0,
                                    key="cohort_longitudinal_group_a",
                                )
                            with col_cmp_b:
                                remaining = [g for g in group_names if g != group_a]
                                group_b = st.selectbox(
                                    "Group B",
                                    options=remaining if remaining else group_names,
                                    index=0,
                                    key="cohort_longitudinal_group_b",
                                )
                        else:
                            group_a = "Control"
                            group_b = "Intervention"

                        metrics_default = ["rmssd_ms", "sdnn_ms", "mean_hr_bpm", "hf_power_ms2", "lf_hf_ratio"]
                        selected_metrics = st.multiselect(
                            "HRV metrics to compare (Δ vs baseline)",
                            options=metrics_default,
                            default=["rmssd_ms", "sdnn_ms"],
                            key="cohort_longitudinal_metrics",
                        )
                        agg_mode = st.selectbox(
                            "Within-timepoint aggregation (per subject)",
                            options=["median", "mean"],
                            index=0,
                            key="cohort_longitudinal_agg",
                            help="If a subject has multiple HRV sessions under the same timepoint label, "
                            "this determines how the timepoint value is summarized before Δ is computed.",
                        )
                        run_mixed = st.checkbox(
                            "Also fit mixed-effects model (random intercept per subject)",
                            value=True,
                            key="cohort_longitudinal_run_mixed",
                            help="Fits Δ ~ Group × Time with a random subject intercept (requires statsmodels).",
                        )
                        run_longitudinal = st.button(
                            "Compute longitudinal group comparisons",
                            key="cohort_longitudinal_run",
                            type="primary",
                        )
                        if run_longitudinal:
                            # Build group membership from persisted roster editor when available.
                            group_a_ids: list[str] = []
                            group_b_ids: list[str] = []
                            try:
                                edited = st.session_state.get("cohort_roster_editor")
                                edited_df = (
                                    pd.DataFrame(edited)
                                    if isinstance(edited, dict) and "edited_rows" in edited
                                    else None
                                )
                                _ = edited_df  # explicit: session-state schema may differ by Streamlit version
                            except Exception:
                                edited_df = None

                            # Prefer fresh DB roster (source of truth).
                            try:
                                roster_live = db.get_study_roster_dataframe(study_id, limit=2000)
                            except Exception:
                                roster_live = pd.DataFrame()
                            if not roster_live.empty:
                                roster_live = roster_live[roster_live["user_id"].isin(selected_user_ids)].copy()
                                roster_live["group_name"] = roster_live["group_name"].fillna("").astype(str)
                                group_a_ids = roster_live[roster_live["group_name"] == str(group_a)]["user_id"].astype(str).tolist()
                                group_b_ids = roster_live[roster_live["group_name"] == str(group_b)]["user_id"].astype(str).tolist()

                            overlap = set(group_a_ids).intersection(set(group_b_ids))
                            if overlap:
                                st.error("Group assignments overlap. Remove overlaps and retry.")
                            elif not group_a_ids or not group_b_ids:
                                st.error("Assign at least one user to each selected group to continue.")
                            elif not selected_metrics:
                                st.error("Select at least one metric to compare.")
                            else:
                                user_tables: Dict[str, pd.DataFrame] = {}
                                user_group_map: Dict[str, str] = {}
                                for uid in list(group_a_ids) + list(group_b_ids):
                                    if uid in user_tables:
                                        continue
                                    try:
                                        tp_table = db.get_hrv_timepoint_change_table(
                                            uid,
                                            metrics=selected_metrics,
                                            agg=str(agg_mode),
                                            limit=500,
                                        )
                                    except Exception as exc:
                                        st.warning(f"Unable to load timepoint table for {user_label_map.get(uid, uid)}: {exc}")
                                        tp_table = pd.DataFrame()
                                    user_tables[uid] = tp_table
                                    user_group_map[uid] = (
                                        str(group_a) if uid in group_a_ids else str(group_b)
                                    )

                                cohort_long_df = build_cohort_longitudinal_delta_long_df(
                                    user_timepoint_tables=user_tables,
                                    user_group_map=user_group_map,
                                    metrics=selected_metrics,
                                )
                                if cohort_long_df.empty:
                                    st.warning(
                                        "No longitudinal cohort deltas could be assembled. "
                                        "Ensure each subject has timepoint-tagged HRV measurements (T0…T21)."
                                    )
                                else:
                                    group_summary_df = compute_cohort_longitudinal_group_summary(
                                        cohort_long_df,
                                        agg="mean",
                                    )
                                    comparisons_df = compare_cohort_longitudinal_groups(
                                        cohort_long_df,
                                        group_a=str(group_a),
                                        group_b=str(group_b),
                                        alpha=0.05,
                                        apply_fdr=True,
                                    )
                                    mixed_df = pd.DataFrame()
                                    if bool(run_mixed):
                                        mixed_df = fit_cohort_longitudinal_mixed_effects(
                                            cohort_long_df,
                                            group_a=str(group_a),
                                            group_b=str(group_b),
                                            max_iter=200,
                                        )
                                    st.session_state["cohort_longitudinal_df"] = cohort_long_df
                                    st.session_state["cohort_longitudinal_summary_df"] = group_summary_df
                                    st.session_state["cohort_longitudinal_comparisons_df"] = comparisons_df
                                    st.session_state["cohort_longitudinal_mixed_df"] = mixed_df
                                    st.session_state["cohort_longitudinal_group_a"] = str(group_a)
                                    st.session_state["cohort_longitudinal_group_b"] = str(group_b)
                                    st.success("Longitudinal cohort comparisons computed.")

                        cohort_long_df = st.session_state.get("cohort_longitudinal_df")
                        group_summary_df = st.session_state.get("cohort_longitudinal_summary_df")
                        comparisons_df = st.session_state.get("cohort_longitudinal_comparisons_df")
                        mixed_df = st.session_state.get("cohort_longitudinal_mixed_df")
                        group_a_name = str(st.session_state.get("cohort_longitudinal_group_a", "Group A"))
                        group_b_name = str(st.session_state.get("cohort_longitudinal_group_b", "Group B"))

                        if isinstance(group_summary_df, pd.DataFrame) and not group_summary_df.empty:
                            st.markdown("##### Group × timepoint delta summary (preview)")
                            st.dataframe(group_summary_df, use_container_width=True)
                            csv_bytes = group_summary_df.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                "Download longitudinal group summary (CSV)",
                                data=csv_bytes,
                                file_name=f"cohort_longitudinal_summary_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv",
                                mime="text/csv",
                                key="download_cohort_longitudinal_summary_csv",
                            )

                        if isinstance(comparisons_df, pd.DataFrame) and not comparisons_df.empty:
                            st.markdown("##### Between-group comparisons (preview)")
                            st.dataframe(comparisons_df, use_container_width=True)
                            csv_bytes = comparisons_df.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                "Download longitudinal comparisons (CSV)",
                                data=csv_bytes,
                                file_name=f"cohort_longitudinal_comparisons_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv",
                                mime="text/csv",
                                key="download_cohort_longitudinal_comparisons_csv",
                            )

                        if isinstance(mixed_df, pd.DataFrame) and not mixed_df.empty:
                            st.markdown("##### Mixed-effects model (preview)")
                            st.dataframe(mixed_df, use_container_width=True)
                            csv_bytes = mixed_df.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                "Download mixed-effects results (CSV)",
                                data=csv_bytes,
                                file_name=f"cohort_longitudinal_mixed_effects_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv",
                                mime="text/csv",
                                key="download_cohort_longitudinal_mixed_csv",
                            )

                        if isinstance(cohort_long_df, pd.DataFrame) and not cohort_long_df.empty:
                            try:
                                longitudinal_md = build_cohort_longitudinal_markdown_report(
                                    cohort_long_df=cohort_long_df,
                                    group_summary_df=(
                                        group_summary_df
                                        if isinstance(group_summary_df, pd.DataFrame)
                                        else pd.DataFrame()
                                    ),
                                    comparisons_df=(
                                        comparisons_df
                                        if isinstance(comparisons_df, pd.DataFrame)
                                        else pd.DataFrame()
                                    ),
                                    mixed_effects_df=(
                                        mixed_df
                                        if isinstance(mixed_df, pd.DataFrame)
                                        else None
                                    ),
                                    group_a=group_a_name,
                                    group_b=group_b_name,
                                    additional_notes=cohort_notes,
                                )
                            except Exception as exc:
                                st.warning(f"Longitudinal cohort markdown export failed: {exc}")
                            else:
                                st.text_area("Longitudinal cohort report preview", longitudinal_md, height=280)
                                st.download_button(
                                    "Download longitudinal cohort report (Markdown)",
                                    data=longitudinal_md.encode("utf-8"),
                                    file_name=f"cohort_longitudinal_report_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.md",
                                    mime="text/markdown",
                                    key="download_cohort_longitudinal_report_md",
                                )

        st.divider()
        st.subheader("Export report")
        if not meta_rows and multi_results_df.empty:
            st.info("Run an analysis to enable export.")
        else:
            scope_choice = st.radio(
                "Report scope",
                options=[ExportScope.SUMMARY, ExportScope.COMPLETE],
                index=0,
                format_func=lambda scope: (
                    "Summary (partial)"
                    if scope == ExportScope.SUMMARY
                    else "Complete (full)"
                ),
            )
            include_windowed_opt = st.checkbox(
                "Include windowed metrics section",
                value=(scope_choice == ExportScope.COMPLETE),
                disabled=windowed_df.empty,
            )
            include_ml_opt = st.checkbox(
                "Include ML clustering summary",
                value=(enable_ml and not ml_summary_df.empty),
                disabled=ml_summary_df.empty,
            )
            available_sources: List[str] = []
            if ordered_sources:
                available_sources = ordered_sources
            elif meta_rows:
                meta_sources = {
                    str(row.get("source", row.get("name", "")))
                    for row in meta_rows
                    if row.get("source") or row.get("name")
                }
                available_sources = sorted(
                    [src for src in meta_sources if src])
            elif not multi_results_df.empty and "source" in multi_results_df.columns:
                available_sources = sorted(
                    multi_results_df["source"].astype(str).unique().tolist()
                )
            selected_sources = st.multiselect(
                "Datasets to include",
                options=available_sources,
                default=available_sources,
            )
            notes_input = st.text_area(
                "Additional notes (optional)",
                placeholder="Add protocol notes, observations, or follow-up actions.",
                height=120,
            )
            # -----------------------------------------------------------------
            # Export report (on-demand): building the markdown every rerun can
            # stall unrelated tabs because Streamlit tabs are not lazy.
            # -----------------------------------------------------------------
            export_report_state = st.session_state.setdefault(
                "export_report_state",
                {"signature": "", "markdown": "", "generated_at_utc": "", "params": {}},
            )
            try:
                analysis_settings_hash = compute_settings_hash(
                    str(method), float(max_dev), int(median_win), win, step
                )
            except Exception:
                analysis_settings_hash = "unknown"

            notes_text_base = str(notes_input or "")
            notes_hash = hashlib.sha256(
                notes_text_base.encode("utf-8", errors="ignore")
            ).hexdigest()[:16]

            _space_analytics_corr = st.session_state.get("space_analytics_corr_results")
            _space_analytics_ml = st.session_state.get("space_analytics_ml_results")
            space_analytics_export = None
            if isinstance(_space_analytics_corr, dict) or isinstance(_space_analytics_ml, dict):
                space_analytics_export = {
                    "corr": _space_analytics_corr if isinstance(_space_analytics_corr, dict) else None,
                    "ml": _space_analytics_ml if isinstance(_space_analytics_ml, dict) else None,
                }

            export_config = ExportConfiguration(
                scope=scope_choice,
                include_windowed=include_windowed_opt,
                include_ml=include_ml_opt,
            )

            export_params = {
                "upload_signature": list(upload_signature) if isinstance(upload_signature, tuple) else [],
                "analysis_settings_hash": str(analysis_settings_hash),
                "scope": str(scope_choice.value),
                "include_windowed": bool(include_windowed_opt),
                "include_ml": bool(include_ml_opt),
                "selected_sources": list(selected_sources),
                "notes_hash": str(notes_hash),
                "space_weather_export_present": bool(st.session_state.get("space_weather_export")),
                "space_analytics_export_present": bool(space_analytics_export),
            }
            export_signature = hashlib.sha256(
                json.dumps(export_params, sort_keys=True).encode("utf-8", errors="ignore")
            ).hexdigest()

            col_gen, col_clear, col_status = st.columns([1, 1, 2])
            with col_gen:
                generate_report = st.button(
                    "🧾 Generate report",
                    key="export_report_generate",
                    type="primary",
                    help="Builds the markdown report once and caches it in-session.",
                )
            with col_clear:
                clear_report = st.button(
                    "🧹 Clear report",
                    key="export_report_clear",
                    help="Clears the cached markdown report for this session.",
                )
            with col_status:
                if (
                    export_report_state.get("signature") == export_signature
                    and export_report_state.get("markdown")
                ):
                    st.caption(
                        f"Report ready ({export_report_state.get('generated_at_utc', 'unknown')})."
                    )
                elif export_report_state.get("markdown"):
                    st.caption(
                        "A report exists but inputs changed — click **Generate report** to refresh."
                    )
                else:
                    st.caption("No report generated yet.")

            if clear_report:
                export_report_state["signature"] = ""
                export_report_state["markdown"] = ""
                export_report_state["generated_at_utc"] = ""
                export_report_state["params"] = {}
                st.session_state.pop("last_export_report_markdown", None)
                st.success("Cleared cached export report.")

            if generate_report:
                # Compose NOAA notes only when the user explicitly generates a report.
                noaa_notes_lines: List[str] = []
                try:
                    exp_rows = get_noaa_metric_explanations()
                except Exception:
                    exp_rows = []
                if exp_rows:
                    noaa_notes_lines.append("### NOAA metric explanations (concise)")
                    for row in exp_rows:
                        title = row.get("title") or f"{row.get('dataset')}.{row.get('value_column')}"
                        noaa_notes_lines.append(
                            f"- **{title}** — {row.get('what','')}. "
                            f"Why it matters: {row.get('why','')}. "
                            f"Physiology: {row.get('physiology','')}. "
                            f"Likely HRV: {row.get('likely_effect','')} "
                            f"(Refs: {row.get('references','')})."
                        )
                global_corr_df = st.session_state.get("noaa_space_state", {}).get(
                    "global_corr", pd.DataFrame()
                )
                label_lookup: Dict[Tuple[str, str], str] = st.session_state.get(
                    "noaa_space_state", {}
                ).get("global_corr_labels", {})
                if isinstance(global_corr_df, pd.DataFrame) and not global_corr_df.empty:
                    top = global_corr_df.copy()
                    top["abs_r"] = top["pearson_r"].abs()
                    top = top.sort_values("abs_r", ascending=False).head(10)
                    noaa_notes_lines.append("### Top NOAA↔HRV correlations (session)")
                    for row in top.itertuples():
                        label = label_lookup.get(
                            (row.predictor_key, row.value_column),
                            row.value_column.replace("_", " ").title(),
                        )
                        p_text = (
                            f"{row.p_value:.4f}"
                            if np.isfinite(row.p_value)
                            else "n/a"
                        )
                        noaa_notes_lines.append(
                            f"- {row.metric} vs {row.predictor_title} — {label}: "
                            f"r={row.pearson_r:.3f}, p={p_text}, "
                            f"CI95% [{row.ci_low:.3f}, {row.ci_high:.3f}], lag {int(row.lag_hours)} h (n={int(row.n)})."
                        )

                notes_text = notes_text_base
                if noaa_notes_lines:
                    notes_text = (notes_text + "\n\n" if notes_text.strip() else "") + "\n".join(noaa_notes_lines)

                try:
                    report_markdown = build_markdown_report(
                        meta_rows=meta_rows,
                        multi_results_df=multi_results_df,
                        windowed_df=windowed_df,
                        episodes_df=episodes_df,
                        ml_summary_df=ml_summary_df if include_ml_opt else None,
                        space_weather_export=st.session_state.get("space_weather_export"),
                        space_analytics_export=space_analytics_export,
                        config=export_config,
                        selected_sources=selected_sources,
                        additional_notes=notes_text,
                    )
                except ValueError as exc:
                    logger.warning("Report generation failed: %s", exc, exc_info=True)
                    st.warning(str(exc))
                else:
                    export_report_state["signature"] = export_signature
                    export_report_state["markdown"] = report_markdown
                    export_report_state["generated_at_utc"] = pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                    export_report_state["params"] = export_params
                    st.session_state["last_export_report_markdown"] = report_markdown
                    st.success("Report generated.")

            report_markdown = ""
            if (
                export_report_state.get("signature") == export_signature
                and isinstance(export_report_state.get("markdown"), str)
            ):
                report_markdown = export_report_state.get("markdown", "")

            if report_markdown:
                st.text_area("Report preview", report_markdown, height=360)
                file_suffix = scope_choice.value
                timestamp_str = pd.Timestamp.utcnow().strftime("%Y%m%dT%H%M%SZ")
                file_name = f"hrv_report_{file_suffix}_{timestamp_str}.md"
                st.download_button(
                    label="Download markdown report",
                    data=report_markdown.encode("utf-8"),
                    file_name=file_name,
                    mime="text/markdown",
                )
                if include_ml_opt and ml_summary_df.empty and enable_ml and ml_error_message:
                    st.info(f"ML section included but no clusters were generated: {ml_error_message}")

                st.markdown("---")
                show_ai_tools = st.checkbox(
                    "Show AI tools (slower)",
                    value=False,
                    key="export_show_ai_tools",
                    help="Keeps Export tab fast by default; enable only when you need GPT/appendix tooling.",
                )
                if show_ai_tools:
                    st.subheader("AI analysis (on-demand)")

                    gpt_section = st.container()
                    _render_gpt_high_interpretation(
                        gpt_section,
                        enabled=True,
                        meta_rows=meta_rows_for_context,
                        multi_results_df=multi_results_df,
                        windowed_df=windowed_df,
                        episodes_df=episodes_df,
                        ml_summary_df=ml_summary_df,
                        report_markdown=report_markdown,
                    )

                    st.markdown("---")
                    st.subheader("Metric explanations appendix (on-demand)")
                    if multi_results_df.empty:
                        st.info("Run an analysis to enable metric explanations.")
                    else:
                        export_metric_state = st.session_state.setdefault(
                            "export_metric_explainer_state",
                            {
                                "signature": "",
                                "explanations": [],
                                "agent_markdown": "",
                                "agent_payload": None,
                                "agent_error": "",
                                "used_agent": False,
                                "markdown_appendix": "",
                            },
                        )
                        use_openai_agent = st.checkbox(
                            "Use OpenAI agent (requires OPENAI_API_KEY)",
                            value=False,
                            key="export_metric_explainer_use_openai",
                            help="When enabled, the agent uses code interpreter + file search for deeper analysis.",
                        )
                        run_metric_explainer = st.button(
                            "Generate metric explanations appendix",
                            key="export_metric_explainer_generate",
                            type="primary",
                        )
                        if run_metric_explainer:
                            metrics_signature = hashlib.sha256(
                                multi_results_df.to_json(
                                    orient="split",
                                    date_format="iso",
                                ).encode("utf-8")
                            ).hexdigest()
                            manager = AgentInsightManager()
                            result = manager.generate_metric_insights(
                                multi_results_df,
                                user_context=active_user_context,
                                run_agent=bool(use_openai_agent),
                            )
                            payload_display = None
                            if result.agent_payload is not None:
                                try:
                                    payload_display = json.loads(
                                        json.dumps(result.agent_payload, default=str)
                                    )
                                except (TypeError, ValueError):
                                    payload_display = result.agent_payload
                            export_metric_state["signature"] = metrics_signature
                            export_metric_state["explanations"] = [asdict(expl) for expl in result.explanations]
                            export_metric_state["agent_markdown"] = result.agent_markdown or ""
                            export_metric_state["agent_payload"] = payload_display
                            export_metric_state["agent_error"] = result.agent_error or ""
                            export_metric_state["used_agent"] = result.used_agent
                            export_metric_state["markdown_appendix"] = result.markdown_appendix

                        explanations = export_metric_state.get("explanations", [])
                        if explanations:
                            explanation_df = pd.DataFrame(explanations)
                            st.dataframe(
                                explanation_df[
                                    [
                                        "dataset",
                                        "display_name",
                                        "value",
                                        "unit",
                                        "status",
                                        "explanation",
                                        "citation",
                                    ]
                                ],
                                use_container_width=True,
                            )
                        else:
                            st.info("Click **Generate** to build the metric appendix.")

                        agent_md = export_metric_state.get("agent_markdown", "")
                        if agent_md:
                            st.markdown("#### GPT-5.2 agent narrative")
                            st.markdown(agent_md)
                        if export_metric_state.get("agent_error"):
                            st.warning(export_metric_state["agent_error"])

                        payload_preview = export_metric_state.get("agent_payload")
                        if payload_preview:
                            with st.expander("View request payload (debug)", expanded=False):
                                st.json(payload_preview)

                        appendix_markdown = export_metric_state.get("markdown_appendix", "")
                        if appendix_markdown:
                            st.text_area(
                                "Appendix (markdown preview)",
                                appendix_markdown,
                                height=240,
                                key="export_metric_explainer_markdown_preview",
                            )
                            appendix_file_name = (
                                "metric_explainability_"
                                + pd.Timestamp.utcnow().strftime("%Y%m%dT%H%M%SZ")
                                + ".md"
                            )
                            st.download_button(
                                "Download metric explanations appendix (Markdown)",
                                data=appendix_markdown.encode("utf-8"),
                                file_name=appendix_file_name,
                                mime="text/markdown",
                                key="export_metric_explainer_markdown_download",
                            )
            else:
                st.info("Click **Generate report** to build the markdown preview and download.")
        gpt_report_md = st.session_state.get("gpt5_export_markdown", "")
        if gpt_report_md:
            st.markdown("---")
            st.subheader("GPT-5 high interpretation")
            st.text_area(
                "GPT-5 interpretation preview",
                gpt_report_md,
                height=360)
            gpt_file_name = (
                f"hrv_gpt5_high_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.md"
            )
            st.download_button(
                label="Download GPT-5 interpretation",
                data=gpt_report_md.encode("utf-8"),
                file_name=gpt_file_name,
                mime="text/markdown",
            )
            base_report = st.session_state.get("last_export_report_markdown", "")
            if isinstance(base_report, str) and base_report.strip():
                combined_name = (
                    f"hrv_report_with_gpt5_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.md"
                )
                combined_md = (
                    base_report.rstrip()
                    + "\n\n---\n\n"
                    + "## GPT-5.2 High-Reasoning Interpretation\n\n"
                    + gpt_report_md.strip()
                    + "\n"
                )
                st.download_button(
                    label="Download combined report (HRV + GPT-5)",
                    data=combined_md.encode("utf-8"),
                    file_name=combined_name,
                    mime="text/markdown",
                )
            tts_button = st.button(
                "Generate GPT-5 audio playback (tts-hd)",
                key="gpt5_tts_button",
            )
            if tts_button:
                try:
                    audio_bytes = synthesize_agent_speech(gpt_report_md)
                except Exception as exc:
                    st.warning(f"TTS generation failed: {exc}")
                else:
                    st.session_state["gpt5_tts_audio"] = audio_bytes
                    st.success("GPT-5 interpretation audio ready.")
            audio_payload = st.session_state.get("gpt5_tts_audio")
            if isinstance(audio_payload, (bytes, bytearray)) and audio_payload:
                st.audio(audio_payload, format="audio/mp3")
    with tab_about:
        # -------------------------------------------------------------------
        # ABOUT TAB — Prefer dedicated renderer; fallback to lightweight preview
        # -------------------------------------------------------------------
        st.markdown("### ℹ️ About & Documentation")
        st.caption("Author credentials, changelog, and user manual for the HRV Analysis Suite.")

        # The dedicated About renderer can be slow because it renders full docs.
        # Default to a lightweight preview that always loads instantly; let users
        # opt into the full page explicitly.
        if "_about_show_full" not in st.session_state:
            st.session_state["_about_show_full"] = False
        show_full_about = bool(st.session_state.get("_about_show_full", False))

        col_mode, col_hint = st.columns([1, 2])
        with col_mode:
            if not show_full_about:
                if st.button("Load full About page", key="about_load_full"):
                    st.session_state["_about_show_full"] = True
                    st.rerun()
            else:
                if st.button("Show lightweight About (faster)", key="about_show_light"):
                    st.session_state["_about_show_full"] = False
                    st.rerun()
        with col_hint:
            st.caption(
                "Tip: the full About page renders large documentation and may take longer. "
                "Use lightweight mode for instant loading."
            )

        rendered = False
        if show_full_about and ABOUT_TAB_AVAILABLE and render_about_tab is not None:
            try:
                with st.spinner("Loading the full About page..."):
                    render_about_tab()
                rendered = True
            except Exception as exc:  # pragma: no cover - defensive
                log_exception(_LOGGER, "About tab render failed", exc)
                st.warning("About tab renderer failed; showing lightweight fallback.")

        if not rendered:
            # Lightweight fallback (no external module dependency)
            st.markdown("---")
            st.markdown("#### 👨‍⚕️ About the Author")
            st.markdown(
                "**Dr. Diego Leonel Malpica Hincapié** — Aerospace Medicine (Colombia)\n\n"
                "- Professional service within Colombian Military Health / Fuerza Aérea Colombiana (public record).\n"
                "- Focus areas: aerospace medicine, operational performance, fatigue, psychophysiology, and HRV.\n"
                "- This app and analysis workflow were authored and curated by Dr. Malpica.\n\n"
                "**Project Links:**\n"
                "- GitHub repository: https://github.com/strikerdlm/HRV\n"
                "- HRV Normative review in this project: `docs/Normative.md`\n"
            )

            st.markdown("---")
            st.markdown("#### 📜 Changelog (preview)")
            changelog_path = Path(__file__).resolve().parents[1] / "CHANGELOG.md"
            changelog_text = _load_text_file(changelog_path)
            if changelog_text:
                changelog_preview = "\n".join(changelog_text.splitlines()[:80])
                with st.expander("View CHANGELOG.md (preview)", expanded=False):
                    st.markdown(changelog_preview)
                st.download_button(
                    "Download CHANGELOG.md",
                    data=changelog_text.encode("utf-8"),
                    file_name="CHANGELOG.md",
                    mime="text/markdown",
                    key="download_changelog_md",
                )
                st.caption("Preview trimmed to keep the tab responsive; download for full history.")
            else:
                st.warning("Unable to load CHANGELOG.md — check that the file exists in the project root.")

            st.markdown("---")
            st.markdown("#### 📖 User Manual (preview)")
            manual_path = Path(__file__).resolve().parents[1] / "docs" / "Manual.md"
            manual_text = _load_text_file(manual_path)
            if manual_text:
                manual_preview = "\n".join(manual_text.splitlines()[:80])
                with st.expander("View User Manual (preview)", expanded=False):
                    st.markdown(manual_preview)
                st.download_button(
                    "Download docs/Manual.md",
                    data=manual_text.encode("utf-8"),
                    file_name="Manual.md",
                    mime="text/markdown",
                    key="download_manual_md",
                )
                st.caption("Full manual available via download; preview truncated for fast loading.")
            else:
                st.warning("Unable to load docs/Manual.md — check that the file exists in the docs folder.")
    with tab_refs:
        # ---------------------------------------------------------------------
        # REFERENCES TAB — Always loads immediately regardless of HRV data state
        # ---------------------------------------------------------------------
        st.markdown("### 📚 References")
        st.caption("Selected peer-reviewed citations and technical documents used across HRV, FRMS/SAFTE, circadian, and space-weather modules.")

        st.markdown("---")
        st.markdown("#### 📖 Complete references (docs/lit_review.md)")
        st.caption("Loads on-demand from docs/lit_review.md to keep this tab fast.")
        _show_full_refs = st.session_state.get("_show_full_references_lit_review", False)
        if not _show_full_refs:
            if st.button("Load full reference list", key="load_lit_review_refs"):
                st.session_state["_show_full_references_lit_review"] = True
                _show_full_refs = True
        if _show_full_refs:
            lit_refs = _load_lit_review_references()
            if lit_refs:
                with st.expander("Full reference list from docs/lit_review.md", expanded=False):
                    st.markdown(lit_refs)
                st.download_button(
                    "Download references (lit_review.md)",
                    data=lit_refs.encode("utf-8"),
                    file_name="lit_review_references.md",
                    mime="text/markdown",
                    key="download_lit_review_refs",
                )
            else:
                st.warning("Unable to load references from docs/lit_review.md.")

        # HRV Standards & Measurement
        st.markdown("---")
        st.markdown("#### 📊 HRV Standards & Measurement")
        st.markdown(
            "- Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology. (1996). "
            "Heart rate variability: Standards of measurement, physiological interpretation, and clinical use. *Circulation, 93*(5), 1043–1065. "
            "[https://doi.org/10.1161/01.CIR.93.5.1043](https://doi.org/10.1161/01.CIR.93.5.1043)  \n"
            "- Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability metrics and norms. *Frontiers in Public Health, 5*, 258. "
            "[https://doi.org/10.3389/fpubh.2017.00258](https://doi.org/10.3389/fpubh.2017.00258)  \n"
            "- Nunan, D., Sandercock, G. R. H., & Brodie, D. A. (2010). A quantitative systematic review of normal values for short-term heart rate variability in healthy adults. "
            "*Pacing and Clinical Electrophysiology, 33*(11), 1407–1417. [https://doi.org/10.1111/j.1540-8159.2010.02841.x](https://doi.org/10.1111/j.1540-8159.2010.02841.x)  \n"
            "- Laborde, S., Mosley, E., & Thayer, J. F. (2017). Heart rate variability and cardiac vagal tone in psychophysiological research—Recommendations. "
            "*Frontiers in Psychology, 8*, 213. [https://doi.org/10.3389/fpsyg.2017.00213](https://doi.org/10.3389/fpsyg.2017.00213)  \n"
            "- Billman, G. E. (2013). The LF/HF ratio does not accurately measure cardiac sympatho-vagal balance. *Frontiers in Physiology, 4*. "
            "[https://doi.org/10.3389/fphys.2013.00026](https://doi.org/10.3389/fphys.2013.00026)  \n"
        )

        # HRV Processing & Artifact Correction
        st.markdown("#### 🔧 HRV Processing & Artifact Correction")
        st.markdown(
            "- Tarvainen, M. P., Niskanen, J.-P., Lipponen, J. A., Ranta-aho, P. O., & Karjalainen, P. A. (2014). Kubios HRV – Heart rate variability analysis software. "
            "*Computer Methods and Programs in Biomedicine, 113*(1), 210–220. [https://doi.org/10.1016/j.cmpb.2013.07.024](https://doi.org/10.1016/j.cmpb.2013.07.024)  \n"
            "- Lipponen, J. A., & Tarvainen, M. P. (2019). A robust algorithm for heart rate variability time series artefact correction. "
            "*Journal of Medical Engineering & Technology, 43*(3), 173–181. [https://doi.org/10.1080/03091902.2019.1640306](https://doi.org/10.1080/03091902.2019.1640306)  \n"
            "- Pan, J., & Tompkins, W. J. (1985). A real-time QRS detection algorithm. *IEEE Transactions on Biomedical Engineering, BME-32*(3), 230–236. "
            "[https://doi.org/10.1109/TBME.1985.325532](https://doi.org/10.1109/TBME.1985.325532)  \n"
        )

        # Nonlinear HRV Analysis
        st.markdown("#### 🧮 Nonlinear HRV Analysis")
        st.markdown(
            "- Pincus, S. M. (1991). Approximate entropy as a measure of system complexity. *Proceedings of the National Academy of Sciences, 88*(6), 2297–2301. "
            "[https://doi.org/10.1073/pnas.88.6.2297](https://doi.org/10.1073/pnas.88.6.2297)  \n"
            "- Richman, J. S., & Moorman, J. R. (2000). Physiological time-series analysis using approximate entropy and sample entropy. "
            "*American Journal of Physiology-Heart and Circulatory Physiology, 278*(6), H2039–H2049. [https://doi.org/10.1152/ajpheart.2000.278.6.h2039](https://doi.org/10.1152/ajpheart.2000.278.6.h2039)  \n"
            "- Peng, C.-K., Havlin, S., Stanley, H. E., & Goldberger, A. L. (1995). Quantification of scaling exponents and crossover phenomena in nonstationary heartbeat time series. "
            "*Chaos, 5*(1), 82–87. [https://doi.org/10.1063/1.166141](https://doi.org/10.1063/1.166141)  \n"
        )

        # Heart Rate Fragmentation (HRF)
        st.markdown("#### 🧩 Heart Rate Fragmentation (HRF)")
        st.markdown(
            "- Costa, M. D., Davis, R. B., & Goldberger, A. L. (2017). Heart rate fragmentation: A new approach to the analysis of cardiac interbeat interval dynamics. "
            "*Frontiers in Physiology, 8*, 255. [https://doi.org/10.3389/fphys.2017.00255](https://doi.org/10.3389/fphys.2017.00255)  \n"
            "- Costa, M. D., Davis, R. B., & Goldberger, A. L. (2017). Heart rate fragmentation: A symbolic dynamical approach. "
            "*Frontiers in Physiology, 8*, 827. [https://doi.org/10.3389/fphys.2017.00827](https://doi.org/10.3389/fphys.2017.00827)  \n"
            "- Hayano, J., Kisohara, M., Ueda, N., & Yuda, E. (2020). Impact of heart rate fragmentation on the assessment of heart rate variability. "
            "*Applied Sciences, 10*(9), 3314. [https://doi.org/10.3390/app10093314](https://doi.org/10.3390/app10093314)  \n"
            "- Guichard, J.-B., Hupin, D., Pichot, V., Berger, M., Celle, S., Borràs, R., Roca-Luque, I., Mont, L., Da Costa, A., Barthélémy, J.-C., & Roche, F. (2025). "
            "Assessing heart rate fragmentation to predict atrial fibrillation in the general population aged 65: The PROOF-AF study. *European Heart Journal Open, 5*(3), oeaf030. "
            "[https://doi.org/10.1093/ehjopen/oeaf030](https://doi.org/10.1093/ehjopen/oeaf030)  \n"
        )

        # Circadian Biology & Modelling
        st.markdown("#### 🌙 Circadian Biology & Modelling")
        st.markdown(
            "- Forger, D. B., Jewett, M. E., & Kronauer, R. E. (1999). A simpler model of the human circadian pacemaker. *Journal of Biological Rhythms, 14*(6), 533–538. "
            "[https://doi.org/10.1177/074873099129000867](https://doi.org/10.1177/074873099129000867)  \n"
            "- Khalsa, S. B. S., Jewett, M. E., Cajochen, C., & Czeisler, C. A. (2003). A phase response curve to single bright light pulses in human subjects. "
            "*The Journal of Physiology, 549*(3), 945–952. [https://doi.org/10.1113/jphysiol.2003.040477](https://doi.org/10.1113/jphysiol.2003.040477)  \n"
            "- St Hilaire, M. A., Gooley, J. J., Khalsa, S. B. S., Kronauer, R. E., Czeisler, C. A., & Lockley, S. W. (2012). Human phase response curve to a 1 h pulse of bright white light. "
            "*The Journal of Physiology, 590*(13), 3035–3045. [https://doi.org/10.1113/jphysiol.2012.227892](https://doi.org/10.1113/jphysiol.2012.227892)  \n"
            "- Hannay, K. M., Booth, V., & Forger, D. B. (2019). Macroscopic models for human circadian rhythms. *Journal of Biological Rhythms, 34*(6), 658–671. "
            "[https://doi.org/10.1177/0748730419878298](https://doi.org/10.1177/0748730419878298)  \n"
        )

        # Fatigue Science & FRMS
        st.markdown("#### 😴 Fatigue Science & FRMS")
        st.markdown(
            "- Van Dongen, H. P. A., Maislin, G., Mullington, J. M., & Dinges, D. F. (2003). The cumulative cost of additional wakefulness: Dose-response effects on neurobehavioral functions. "
            "*Sleep, 26*(2), 117–126. [https://doi.org/10.1093/sleep/26.2.117](https://doi.org/10.1093/sleep/26.2.117)  \n"
            "- Belenky, G., Wesensten, N. J., Thorne, D. R., et al. (2003). Patterns of performance degradation and restoration during sleep restriction and subsequent recovery. "
            "*Journal of Sleep Research, 12*(1), 1–12. [https://doi.org/10.1046/j.1365-2869.2003.00337.x](https://doi.org/10.1046/j.1365-2869.2003.00337.x)  \n"
            "- Basner, M., Moore, T. M., Nasrini, J., Gur, R. C., & Dinges, D. F. (2021). Standardization of psychomotor vigilance testing methods and reporting. "
            "*Sleep, 44*(7). [https://doi.org/10.1093/sleep/zsab114](https://doi.org/10.1093/sleep/zsab114)  \n"
            "- Dawson, D., Ian Noy, Y., Härmä, M., Åkerstedt, T., & Belenky, G. (2011). Modelling fatigue and the use of fatigue models in work settings. "
            "*Accident Analysis & Prevention, 43*(2), 549–564. [https://doi.org/10.1016/j.aap.2009.12.030](https://doi.org/10.1016/j.aap.2009.12.030)  \n"
            "- Federal Aviation Administration. (2013). *Fatigue Risk Management Systems for Aviation Safety* (AC 120-103A). "
            "[https://www.faa.gov/documentlibrary/media/advisory_circular/ac_120-103a.pdf](https://www.faa.gov/documentlibrary/media/advisory_circular/ac_120-103a.pdf)  \n"
        )

        # Wearable Validation
        st.markdown("#### ⌚ Wearable Validation")
        st.markdown(
            "- Schaffarczyk, M., Rogers, B., Reer, R., & Gronwald, T. (2022). Validity of the Polar H10 sensor for heart rate variability analysis during resting state and incremental exercise. "
            "*Sensors, 22*(17), 6536. [https://doi.org/10.3390/s22176536](https://doi.org/10.3390/s22176536)  \n"
            "- Nunan, D., Donovan, G., Jakovljevic, D. G., et al. (2009). Validity and reliability of short-term heart-rate variability from the Polar S810. "
            "*Medicine & Science in Sports & Exercise, 41*(1), 243–250. [https://doi.org/10.1249/MSS.0b013e318184a4b1](https://doi.org/10.1249/MSS.0b013e318184a4b1)  \n"
            "- de Zambotti, M., Cellini, N., Goldstone, A., Colrain, I. M., & Baker, F. C. (2019). Wearable sleep technology in clinical and research settings. "
            "*Medicine & Science in Sports & Exercise, 51*(7), 1538–1557. [https://doi.org/10.1249/MSS.0000000000001947](https://doi.org/10.1249/MSS.0000000000001947)  \n"
            "- Schäfer, A., & Vagedes, J. (2013). How accurate is pulse rate variability as an estimate of heart rate variability? "
            "*International Journal of Cardiology, 166*(1), 15–29. [https://doi.org/10.1016/j.ijcard.2012.03.119](https://doi.org/10.1016/j.ijcard.2012.03.119)  \n"
        )

        # Space Weather & Geomagnetic Effects
        st.markdown("#### 🌍 Space Weather & Geomagnetic Effects")
        st.markdown(
            "- Alabdulgader, A., McCraty, R., Atkinson, M., et al. (2018). Long-term study of heart rate variability responses to changes in the solar and geomagnetic environment. "
            "*Scientific Reports, 8*(1). [https://doi.org/10.1038/s41598-018-20932-x](https://doi.org/10.1038/s41598-018-20932-x)  \n"
            "- Vieira, C. L. Z., Chen, K., Garshick, E., et al. (2022). Geomagnetic disturbances reduce heart rate variability in the Normative Aging Study. "
            "*Science of The Total Environment, 839*, 156235. [https://doi.org/10.1016/j.scitotenv.2022.156235](https://doi.org/10.1016/j.scitotenv.2022.156235)  \n"
            "- NOAA Space Weather Prediction Center. (n.d.). The K-index. [https://www.swpc.noaa.gov/sites/default/files/images/u2/TheK-index.pdf](https://www.swpc.noaa.gov/sites/default/files/images/u2/TheK-index.pdf)  \n"
            "- NOAA Space Weather Prediction Center. (n.d.). NOAA scales explanation. [https://www.swpc.noaa.gov/noaa-scales-explanation](https://www.swpc.noaa.gov/noaa-scales-explanation)  \n"
            "- NASA/CCMC. (n.d.). DONKI: Space Weather Database of Notifications, Knowledge, Information. "
            "[https://ccmc.gsfc.nasa.gov/tools/DONKI/](https://ccmc.gsfc.nasa.gov/tools/DONKI/)  \n"
        )

        # Governmental & Technical Standards
        st.markdown("#### 📋 Governmental & Technical Standards")
        st.markdown(
            "- National Aeronautics and Space Administration. (2022). *NASA-STD-3001, Volume 2, Revision B: Human factors, habitability, and environmental health.* "
            "[https://ntrs.nasa.gov/citations/20220001995](https://ntrs.nasa.gov/citations/20220001995)  \n"
            "- European Union Aviation Safety Agency. (2023). Easy Access Rules for Air Operations. "
            "[https://www.easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-air-operations](https://www.easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-air-operations)  \n"
            "- International Civil Aviation Organization. (2016). *Manual for the Oversight of Fatigue Management Approaches* (Doc 9966, 2nd ed.). "
            "[https://www.icao.int/safety/fatiguemanagement/](https://www.icao.int/safety/fatiguemanagement/)  \n"
            "- Department of the Air Force. *AFMAN 11-202V3: General Flight Rules.* "
            "[https://static.e-publishing.af.mil/production/1/af_a3/publication/afman11-202v3/afman11-202v3.pdf](https://static.e-publishing.af.mil/production/1/af_a3/publication/afman11-202v3/afman11-202v3.pdf)  \n"
        )

        # Blood Pressure Variability
        st.markdown("#### 💉 Blood Pressure Variability")
        st.markdown(
            "- Parati, G., Stergiou, G. S., Dolan, E., & Bilo, G. (2018). Blood pressure variability: Clinical relevance and application. "
            "*The Journal of Clinical Hypertension, 20*(7), 1133–1137. [https://doi.org/10.1111/jch.13304](https://doi.org/10.1111/jch.13304)  \n"
            "- Rothwell, P. M., Howard, S. C., Dolan, E., et al. (2010). Prognostic significance of visit-to-visit variability, maximum systolic blood pressure, and episodic hypertension. "
            "*The Lancet, 375*(9718), 895–905. [https://doi.org/10.1016/S0140-6736(10)60308-X](https://doi.org/10.1016/S0140-6736(10)60308-X)  \n"
        )

        # Statistical & ML Methods
        st.markdown("#### 📈 Statistical & Machine Learning Methods")
        st.markdown(
            "- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate: A practical and powerful approach to multiple testing. "
            "*Journal of the Royal Statistical Society Series B, 57*(1), 289–300. [https://doi.org/10.1111/j.2517-6161.1995.tb02031.x](https://doi.org/10.1111/j.2517-6161.1995.tb02031.x)  \n"
            "- Killick, R., Fearnhead, P., & Eckley, I. A. (2012). Optimal detection of changepoints with a linear computational cost. "
            "*Journal of the American Statistical Association, 107*(500), 1590–1598. [https://doi.org/10.1080/01621459.2012.737745](https://doi.org/10.1080/01621459.2012.737745)  \n"
            "- Lundberg, S. M., Erion, G., Chen, H., et al. (2020). From local explanations to global understanding with explainable AI for trees. "
            "*Nature Machine Intelligence, 2*(1), 56–67. [https://doi.org/10.1038/s42256-019-0138-9](https://doi.org/10.1038/s42256-019-0138-9)  \n"
        )

        st.markdown("---")
        st.caption("Full literature review available in `docs/lit_review.md`.")
        st.markdown("---")
        st.markdown("#### 🧭 Where to run Space Data + Analytics")
        st.info(
            "This tab is **references-only** and should load instantly.\n\n"
            "- Use **🌐 Space Data** for SWPC/NOAA/DONKI fetching and dashboards (data-only).\n"
            "- Use **🔬 Space Analytics** for correlations and ML (button-driven)."
        )


def _fisher_ci(r: float, n: int, alpha: float = 0.05) -> Tuple[float, float]:
    if not np.isfinite(r) or n <= 3:
        return (float("nan"), float("nan"))
    z = np.arctanh(np.clip(r, -0.999999, 0.999999))
    se = 1.0 / np.sqrt(n - 3)
    z_crit = 1.96  # ~95%
    zl, zu = z - z_crit * se, z + z_crit * se
    return (float(np.tanh(zl)), float(np.tanh(zu)))


def _echarts_timeseries(
    time_vals: List[pd.Timestamp],
    y_vals: List[float],
    *,
    title: str,
    y_name: str,
    series_name: str,
) -> None:
    data = [
        [str(t), float(v)]
        for t, v in zip(time_vals, y_vals)
        if pd.notna(t) and np.isfinite(v)
    ]
    opt = {
        "title": {"text": title, "left": "center"},
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "time"},
        "yAxis": {"type": "value", "name": y_name},
        "grid": {"left": 40, "right": 18, "containLabel": True},
        "series": [
            {
                "name": series_name,
                "type": "line",
                "showSymbol": False,
                "smooth": True,
                "data": data,
            }
        ],
    }
    render_echarts(opt, height_px=320, width="100%", config=EChartsConfig())


def _echarts_multi_series(
    x_vals: List[float],
    series_map: Dict[str, List[float]],
    *,
    title: str,
    x_name: str,
    y_name: str,
    absolute: bool = False,
) -> None:
    series = []
    for name, vals in series_map.items():
        pairs = [
            [float(x), float(abs(v) if absolute else v)]
            for x, v in zip(x_vals, vals)
            if np.isfinite(x) and np.isfinite(v)
        ]
        series.append(
            {
                "name": name,
                "type": "line",
                "smooth": True,
                "showSymbol": False,
                "data": pairs,
            }
        )
    opt = {
        "title": {"text": title, "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"top": 24},
        "xAxis": {"type": "value", "name": x_name},
        "yAxis": {"type": "value", "name": y_name},
        "grid": {"left": 40, "right": 18, "containLabel": True},
        "series": series,
    }
    render_echarts(opt, height_px=320, width="100%", config=EChartsConfig())


def _echarts_sparkline(
    time_vals: List[pd.Timestamp],
    values: List[float],
    *,
    title: str,
    color_primary: str,
    area_colors: Optional[Tuple[str, str]] = None,
    height_px: int = 260,
) -> None:
    data = []
    for ts, val in zip(time_vals, values):
        if pd.isna(ts) or not np.isfinite(val):
            continue
        data.append([str(pd.to_datetime(ts)), float(val)])
    if not data:
        st.info(f"{title}: no data to display.")
        return
    area_start, area_end = area_colors or (
        "rgba(59,130,246,0.32)",
        "rgba(59,130,246,0.04)",
    )
    opt = {
        "title": {"text": title, "left": "center"},
        "tooltip": {"trigger": "axis"},
        "grid": {
            "left": 36,
            "right": 16,
            "top": 48,
            "bottom": 36,
            "containLabel": True,
        },
        "xAxis": {
            "type": "time",
            "boundaryGap": False,
            "axisLabel": {"color": "#475569"},
            "axisLine": {"lineStyle": {"color": "#cbd5f5"}},
        },
        "yAxis": {
            "type": "value",
            "axisLabel": {"color": "#475569"},
            "splitLine": {"lineStyle": {"color": "rgba(148,163,184,0.25)"}},
        },
        "series": [
            {
                "type": "line",
                "showSymbol": False,
                "data": data,
                "smooth": True,
                "lineStyle": {"width": 3, "color": color_primary},
                "areaStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0,
                        "y": 0,
                        "x2": 0,
                        "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": area_start},
                            {"offset": 1, "color": area_end},
                        ],
                    },
                },
            }
        ],
    }
    render_echarts(
        opt,
        height_px=height_px,
        width="100%",
        config=EChartsConfig())


NOAA_GAUGE_PRESETS: Dict[Tuple[str, str], Dict[str, Any]] = {
    (
        "f107_flux",
        "flux",
    ): {
        "min": 60.0,
        "max": 260.0,
        "thresholds": [
            (90.0, "#22c55e"),
            (130.0, "#facc15"),
            (180.0, "#ef4444"),
        ],
    },
    (
        "f107_flux",
        "ninety_day_mean",
    ): {
        "min": 60.0,
        "max": 260.0,
        "thresholds": [
            (90.0, "#22c55e"),
            (130.0, "#facc15"),
            (180.0, "#ef4444"),
        ],
    },
    (
        "planetary_k_index_1m",
        "kp_index",
    ): {
        "min": 0.0,
        "max": 9.0,
        "thresholds": [
            (3.0, "#22c55e"),
            (5.0, "#f97316"),
            (7.0, "#ef4444"),
        ],
    },
    (
        "planetary_k_index_1m",
        "estimated_kp",
    ): {
        "min": 0.0,
        "max": 9.0,
        "thresholds": [
            (3.0, "#22c55e"),
            (5.0, "#f97316"),
            (7.0, "#ef4444"),
        ],
    },
    (
        "geospace_dst",
        "dst",
    ): {
        "min": -250.0,
        "max": 50.0,
        "thresholds": [
            (-100.0, "#22c55e"),
            (-150.0, "#f97316"),
            (-200.0, "#ef4444"),
        ],
    },
    (
        "solar_wind_wind",
        "proton_speed",
    ): {
        "min": 250.0,
        "max": 900.0,
        "thresholds": [
            (450.0, "#22c55e"),
            (650.0, "#facc15"),
            (900.0, "#ef4444"),
        ],
    },
    (
        "geospace_pred_kp",
        "k",
    ): {
        "min": 0.0,
        "max": 9.0,
        "thresholds": [
            (3.0, "#22c55e"),
            (5.0, "#f97316"),
            (7.0, "#ef4444"),
        ],
    },
}

for column in ("k_index",):
    NOAA_GAUGE_PRESETS.setdefault(
        ("boulder_k_1m", column),
        {
            "min": 0.0,
            "max": 9.0,
            "thresholds": [
                (3.0, "#22c55e"),
                (5.0, "#f97316"),
                (7.0, "#ef4444"),
            ],
        },
    )

for key in ("f107_smoothed",):
    for column in ("f10.7", "smoothed_f10.7"):
        NOAA_GAUGE_PRESETS.setdefault(
            (key, column),
            {
                "min": 60.0,
                "max": 260.0,
                "thresholds": [
                    (90.0, "#22c55e"),
                    (130.0, "#facc15"),
                    (180.0, "#ef4444"),
                ],
            },
        )

for column in ("tencmfcst_1_day", "tencmfcst_2_day", "tencmfcst_3_day"):
    NOAA_GAUGE_PRESETS.setdefault(
        ("predicted_f107", column),
        {
            "min": 60.0,
            "max": 260.0,
            "thresholds": [
                (90.0, "#22c55e"),
                (130.0, "#facc15"),
                (180.0, "#ef4444"),
            ],
        },
    )

NOAA_GAUGE_PRESETS.setdefault(
    ("geospace_dst_7d", "dst"),
    {
        "min": -250.0,
        "max": 50.0,
        "thresholds": [
            (-100.0, "#22c55e"),
            (-150.0, "#f97316"),
            (-200.0, "#ef4444"),
        ],
    },
)

NOAA_GAUGE_PRESETS.setdefault(
    ("sunspots_monthly", "ssn"),
    {
        "min": 0.0,
        "max": 350.0,
        "thresholds": [
            (100.0, "#22c55e"),
            (200.0, "#f97316"),
            (300.0, "#ef4444"),
        ],
    },
)

_SOLAR_PROB_COLUMNS = [
    "c_class_1_day",
    "c_class_2_day",
    "c_class_3_day",
    "m_class_1_day",
    "m_class_2_day",
    "m_class_3_day",
    "x_class_1_day",
    "x_class_2_day",
    "x_class_3_day",
    "10mev_protons_1_day",
    "10mev_protons_2_day",
    "10mev_protons_3_day",
]

for column in _SOLAR_PROB_COLUMNS:
    NOAA_GAUGE_PRESETS.setdefault(
        ("solar_probabilities", column),
        {
            "min": 0.0,
            "max": 100.0,
            "thresholds": [
                (20.0, "#22c55e"),
                (50.0, "#f97316"),
                (80.0, "#ef4444"),
            ],
        },
    )

for column in ("afred_1_day", "afred_2_day", "afred_3_day"):
    NOAA_GAUGE_PRESETS.setdefault(
        ("predicted_fredericksburg", column),
        {
            "min": 0.0,
            "max": 100.0,
            "thresholds": [
                (30.0, "#22c55e"),
                (50.0, "#f97316"),
                (70.0, "#ef4444"),
            ],
        },
    )

for column in (
    "ssn_predicted",
    "ssn_high",
    "ssn_low",
    "flux_predicted",
    "flux_high",
    "flux_low",
):
    NOAA_GAUGE_PRESETS.setdefault(
        ("predicted_monthly_ssn", column),
        {
            "min": 0.0,
            "max": 350.0 if column.startswith("ssn") else 260.0,
            "thresholds": [
                (100.0 if column.startswith("ssn") else 90.0, "#22c55e"),
                (200.0 if column.startswith("ssn") else 130.0, "#f97316"),
                (300.0 if column.startswith("ssn") else 180.0, "#ef4444"),
            ],
        },
    )


def _infer_precision(max_abs_value: float) -> int:
    """
    Infer a reasonable number of decimal places for numeric displays.
    """

    max_abs = float(abs(max_abs_value))
    if max_abs >= 1000.0:
        return 0
    if max_abs >= 100.0:
        return 1
    if max_abs >= 10.0:
        return 2
    return 3


def _format_with_precision(value: float, precision: int) -> str:
    """
    Format a numeric value respecting finite checks and precision bounds.
    """

    if not np.isfinite(value):
        return "n/a"
    bounded_precision = max(0, min(int(precision), 4))
    return f"{value:.{bounded_precision}f}"


def _resolve_noaa_gauge_config(
    dataset_key: str,
    value_column: str,
    values: np.ndarray,
) -> Tuple[float, float, List[Tuple[float, str]]]:
    """
    Determine gauge bounds and thresholds for a NOAA metric.
    """

    preset = NOAA_GAUGE_PRESETS.get((dataset_key, value_column))
    if preset is not None:
        thresholds = list(preset["thresholds"])
        return float(preset["min"]), float(preset["max"]), thresholds
    numeric = np.asarray(values, dtype=float)
    numeric = numeric[np.isfinite(numeric)]
    if numeric.size == 0:
        return 0.0, 1.0, [
            (0.33, "#22c55e"),
            (0.66, "#f97316"),
            (1.0, "#ef4444"),
        ]
    min_val = float(np.min(numeric))
    max_val = float(np.max(numeric))
    if not np.isfinite(min_val):
        min_val = 0.0
    if not np.isfinite(max_val):
        max_val = 1.0
    if np.isclose(min_val, max_val):
        padding = max(abs(max_val) * 0.2, 1.0)
        min_val -= padding
        max_val += padding
    if min_val > max_val:
        min_val, max_val = max_val, min_val
    span = max_val - min_val
    if span <= 0.0:
        span = max(abs(max_val), 1.0)
        min_val = max_val - span
    thresholds = [
        (min_val + span * 0.33, "#22c55e"),
        (min_val + span * 0.66, "#f97316"),
        (max_val, "#ef4444"),
    ]
    return min_val, max_val, thresholds


def _format_noaa_series_label(
    bundle: NOAADataBundle,
    value_column: str,
) -> str:
    """
    Construct a readable label for NOAA time-series lines.
    """

    base = bundle.split_labels.get(
        value_column, value_column.replace("_", " ").title()
    )
    unit = bundle.units.get(value_column)
    return f"{base} ({unit})" if unit else base


def _prepare_noaa_history(
    bundle: NOAADataBundle,
    history_hours: int,
) -> pd.DataFrame:
    """
    Slice a NOAA bundle to the requested trailing history window.
    """

    df = bundle.frame.copy()
    time_col = bundle.time_column
    if history_hours > 0:
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=int(history_hours))
        df = df[df[time_col] >= cutoff]
        if df.empty:
            tail_len = min(len(bundle.frame), max(120, int(history_hours)))
            df = bundle.frame.tail(tail_len).copy()
    return df


def _render_noaa_metric_panel(
    bundle: NOAADataBundle,
    df: pd.DataFrame,
    value_column: str,
    *,
    overlay_columns: Sequence[str] = (),
    line_title: Optional[str] = None,
    y_label: Optional[str] = None,
) -> None:
    """
    Render gauge and multi-series line chart for a NOAA metric.
    """

    time_col = bundle.time_column
    if value_column not in df.columns:
        st.info(f"No data available for `{value_column}`.")
        return
    panel_df = df[[time_col, value_column]].dropna()
    panel_df = panel_df.sort_values(time_col)
    panel_df[value_column] = pd.to_numeric(panel_df[value_column], errors="coerce")
    panel_df = panel_df.dropna(subset=[value_column])
    # Round series to one decimal for NOAA plots
    panel_df[value_column] = panel_df[value_column].astype(float).round(1)
    if panel_df.empty:
        st.info(f"No numeric samples available for `{value_column}` in the selected window.")
        return
    values = panel_df[value_column].to_numpy(dtype=float)
    min_val, max_val, thresholds = _resolve_noaa_gauge_config(
        bundle.spec.key, value_column, values
    )
    latest_value = float(values[-1])
    latest_time = panel_df[time_col].iloc[-1]
    max_abs = max(abs(min_val), abs(max_val), abs(latest_value))
    # NOAA request: single-decimal display across plots
    precision = 1
    unit = bundle.units.get(value_column) if bundle.units else None
    friendly_label = bundle.split_labels.get(
        value_column, value_column.replace("_", " ").title()
    )
    gauge_title = f"{bundle.spec.title} — {friendly_label}"
    col_gauge, col_chart = st.columns([1, 2])
    with col_gauge:
        _echarts_gauge(
            latest_value,
            min_val=min_val,
            max_val=max_val,
            title=gauge_title,
            unit=unit or "",
            precision=precision,
            thresholds=thresholds,
            height_px=280,
        )
        if isinstance(latest_time, pd.Timestamp):
            st.caption(f"UTC timestamp: {latest_time.strftime('%Y-%m-%d %H:%M')}")
        stats_cols = st.columns(3)
        stats_cols[0].metric(
            "Window mean",
            _format_with_precision(float(np.nanmean(values)), precision),
        )
        stats_cols[1].metric(
            "Window max",
            _format_with_precision(float(np.nanmax(values)), precision),
        )
        stats_cols[2].metric(
            "Window min",
            _format_with_precision(float(np.nanmin(values)), precision),
        )
    series_map: Dict[str, pd.Series] = {}
    core_series = panel_df.set_index(time_col)[value_column].astype(float)
    if core_series.shape[0] > 1500:
        core_series = core_series.iloc[-1500:]
    series_map[_format_noaa_series_label(bundle, value_column)] = core_series
    for column in overlay_columns:
        if column == value_column or column not in df.columns:
            continue
        overlay_df = df[[time_col, column]].dropna()
        overlay_df[column] = pd.to_numeric(overlay_df[column], errors="coerce")
        overlay_df = overlay_df.dropna(subset=[column]).sort_values(time_col)
        if overlay_df.empty:
            continue
        # Round overlay to one decimal as well
        overlay_series = overlay_df.set_index(time_col)[column].astype(float).round(1)
        if overlay_series.shape[0] > 1500:
            overlay_series = overlay_series.iloc[-1500:]
        series_map[_format_noaa_series_label(bundle, column)] = overlay_series
    with col_chart:
        if not series_map:
            st.info("No time-series data available for plotting.")
        else:
            _echarts_multi_time_series(
                series_map,
                title=line_title or bundle.spec.title,
                y_name=y_label or (unit or "Value"),
                height_px=340,
            )


def _render_noaa_multifrequency_panel(
    bundle: NOAADataBundle,
    df: pd.DataFrame,
) -> None:
    """
    Render a multifrequency solar radio flux view.
    """

    required_cols = {bundle.time_column, "frequency_mhz", "flux_sfu"}
    if not required_cols.issubset(df.columns):
        st.info("Multifrequency dataset missing required columns.")
        return
    filtered = df.dropna(subset=[bundle.time_column, "frequency_mhz", "flux_sfu"])
    if filtered.empty:
        st.info("No multifrequency samples available in the selected window.")
        return
    pivot = (
        filtered.pivot_table(
            index=bundle.time_column,
            columns="frequency_mhz",
            values="flux_sfu",
            aggfunc="mean",
        )
        .sort_index()
    )
    if pivot.empty:
        st.info("Unable to build multifrequency time series.")
        return
    series_map: Dict[str, pd.Series] = {}
    for freq in sorted(pivot.columns):
        series = pivot[freq].dropna().astype(float).round(1)
        if series.empty:
            continue
        if series.shape[0] > 1500:
            series = series.iloc[-1500:]
        label = f"{float(freq):g} MHz"
        series_map[label] = series.astype(float)
    if not series_map:
        st.info("Insufficient multifrequency data for plotting.")
        return
    _echarts_multi_time_series(
        series_map,
        title="Solar radio flux (multifrequency network)",
        y_name="Flux (sfu)",
        height_px=360,
    )
    latest_time = filtered[bundle.time_column].max()
    if isinstance(latest_time, pd.Timestamp):
        st.caption(f"Latest snapshot: {latest_time.strftime('%Y-%m-%d %H:%M UTC')}")
    snapshot = filtered[filtered[bundle.time_column] == latest_time]
    if not snapshot.empty:
        display_cols = [
            "frequency_mhz",
            "flux_sfu",
            "quality_flag",
            "common_name",
        ]
        available_cols = [col for col in display_cols if col in snapshot.columns]
        st.dataframe(
            snapshot[available_cols]
            .sort_values("frequency_mhz")
            .reset_index(drop=True),
            use_container_width=True,
        )


def _format_ci_text(low: float, high: float) -> str:
    """
    Format a confidence interval for display.
    """

    if not np.isfinite(low) or not np.isfinite(high):
        return "CI95% n/a"
    return f"CI95% [{low:.3f}, {high:.3f}]"


def _format_p_value(value: float) -> str:
    """
    Format a p-value for display with scientific notation fallback.
    """

    if not np.isfinite(value):
        return "p = n/a"
    if value < 1e-3:
        return f"p = {value:.2e}"
    return f"p = {value:.3f}"


def _bh_fdr(p_values: Sequence[float]) -> List[float]:
    """Benjamini–Hochberg FDR correction."""
    p_clean = [float(p) for p in p_values if np.isfinite(p)]
    m = len(p_clean)
    if m == 0:
        return [float("nan")] * len(p_values)
    sorted_idx = np.argsort(p_clean)
    q = [float("nan")] * m
    for rank, idx in enumerate(sorted_idx, start=1):
        q[idx] = p_clean[idx] * m / rank
    # monotonicity from largest to smallest
    for i in range(m - 2, -1, -1):
        q[i] = min(q[i], q[i + 1])
    # map back to original length (with non-finite preserved as nan)
    result = []
    j = 0
    for p in p_values:
        if np.isfinite(p):
            result.append(min(q[j], 1.0))
            j += 1
        else:
            result.append(float("nan"))
    return result


def _render_noaa_correlation_summary(
    corr_df: Optional[pd.DataFrame],
    dataset_key: str,
    value_column: str,
    *,
    label_map: Optional[Mapping[str, str]] = None,
) -> None:
    """
    Display correlation summaries for a NOAA dataset/value column pair.
    """

    if corr_df is None or corr_df.empty:
        st.info("Run the correlation scan to populate HRV ↔ NOAA metrics.")
        return
    subset = corr_df[
        (corr_df["predictor_key"] == dataset_key)
        & (corr_df["value_column"] == value_column)
    ].copy()
    if subset.empty:
        st.info("No correlations available for the selected metric yet.")
        return
    subset = subset.assign(abs_r=subset["pearson_r"].abs()).sort_values(
        "abs_r", ascending=False
    )
    subset = subset.drop(columns=["abs_r"])
    label_map = label_map or {}
    friendly_name = label_map.get(
        value_column, value_column.replace("_", " ").title()
    )
    # FDR (Benjamini–Hochberg) on Pearson p-values
    subset["q_value"] = _bh_fdr(subset["p_value"].tolist())
    display_df = subset[
        [
            "test_name",
            "metric",
            "pearson_r",
            "p_value",
            "q_value",
            "spearman_r",
            "spearman_p",
            "ci_low",
            "ci_high",
            "direction",
            "lag_hours",
            "n",
        ]
    ].rename(
        columns={
            "pearson_r": "test_result",
            "direction": "directionality",
            "ci_low": "ci95_low",
            "ci_high": "ci95_high",
            "spearman_r": "spearman_r",
            "spearman_p": "spearman_p",
            "q_value": "fdr_q",
        }
    )
    display_df.insert(0, "predictor", friendly_name)
    formatted = display_df.copy()
    formatted["test_result"] = formatted["test_result"].apply(
        lambda v: _format_with_precision(float(v), 3)
    )
    formatted["p_value"] = formatted["p_value"].apply(
        lambda v: f"{float(v):.2e}" if np.isfinite(v) else "n/a"
    )
    formatted["fdr_q"] = formatted["fdr_q"].apply(
        lambda v: f"{float(v):.2e}" if np.isfinite(v) else "n/a"
    )
    formatted["spearman_r"] = formatted["spearman_r"].apply(
        lambda v: _format_with_precision(float(v), 3)
    )
    formatted["spearman_p"] = formatted["spearman_p"].apply(
        lambda v: f"{float(v):.2e}" if np.isfinite(v) else "n/a"
    )
    formatted["ci95_low"] = formatted["ci95_low"].apply(
        lambda v: _format_with_precision(float(v), 3)
    )
    formatted["ci95_high"] = formatted["ci95_high"].apply(
        lambda v: _format_with_precision(float(v), 3)
    )
    formatted["lag_hours"] = formatted["lag_hours"].astype(int)
    formatted["n"] = formatted["n"].astype(int)
    st.dataframe(formatted, use_container_width=True)
    # Present top findings in a compact scientific table
    summary = subset.copy()
    summary["abs_r"] = summary["pearson_r"].abs()
    summary = summary.sort_values("abs_r", ascending=False).head(8)

    def _dir_icon(direction: str) -> str:
        if direction == "positive":
            return "↑"
        if direction == "negative":
            return "↓"
        return "→"

    table_rows = [
        "| Metric | Lag (h) | r | Spearman ρ | p (r) | q (FDR) | 95% CI | n |",
        "|:--|:--:|:--:|:--:|:--:|:--:|:--:|:--:|",
    ]
    for row in summary.itertuples():
        metric = getattr(row, "metric", "")
        lag = int(getattr(row, "lag_hours", 0))
        r_val = float(getattr(row, "pearson_r", float("nan")))
        p_val = float(getattr(row, "p_value", float("nan")))
        q_val = float(getattr(row, "q_value", float("nan")))
        rho = float(getattr(row, "spearman_r", float("nan")))
        ci_low = float(getattr(row, "ci_low", float("nan")))
        ci_high = float(getattr(row, "ci_high", float("nan")))
        direction = getattr(row, "direction", "neutral")
        n_val = int(getattr(row, "n", 0))
        table_rows.append(
            f"| **{metric}** | {lag:+d} | {_dir_icon(direction)} {r_val:.3f} | {rho:.3f} | "
            f"{_format_p_value(p_val)} | {_format_p_value(q_val)} | [{ci_low:.3f}, {ci_high:.3f}] | {n_val} |"
        )
    st.markdown("\n".join(table_rows))



def _echarts_multi_time_series(
    series_map: Dict[str, pd.Series],
    *,
    title: str,
    y_name: str,
    height_px: int = 320,
) -> None:
    palette = [
        "#38bdf8",
        "#f97316",
        "#22c55e",
        "#a855f7",
        "#e11d48",
        "#facc15",
        "#6366f1",
    ]
    series: List[Dict[str, Any]] = []
    for idx, (name, series_data) in enumerate(series_map.items()):
        if series_data.empty:
            continue
        points = [
            [str(pd.to_datetime(idx, utc=True)), float(val)]
            for idx, val in series_data.sort_index().items()
            if np.isfinite(val)
        ]
        if not points:
            continue
        series.append(
            {
                "name": name,
                "type": "line",
                "showSymbol": False,
                "smooth": True,
                "lineStyle": {"width": 3 if idx == 0 else 2},
                "areaStyle": {"opacity": 0.14} if idx == 0 else None,
                "data": points,
            }
        )
    if not series:
        st.info(f"{title}: no data to display.")
        return
    # Clean up None values for series options
    for item in series:
        if item.get("areaStyle") is None:
            item.pop("areaStyle", None)
    opt = {
        "title": {"text": title, "left": "center"},
        "color": palette,
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
        },
        "legend": {"top": 24},
        "grid": {
            "left": 36,
            "right": 20,
            "top": 56,
            "bottom": 36,
            "containLabel": True,
        },
        "xAxis": {"type": "time", "axisLabel": {"color": "#475569"}},
        "yAxis": {
            "type": "value",
            "name": y_name,
            "axisLabel": {"color": "#475569"},
            "splitLine": {"lineStyle": {"color": "rgba(148,163,184,0.25)"}},
        },
        "series": series,
    }
    render_echarts(
        opt,
        height_px=height_px,
        width="100%",
        config=EChartsConfig())


def _echarts_flux_component_comparison(
    timestamps: Sequence[pd.Timestamp],
    observed_flux: Sequence[float],
    ninety_day_mean: Optional[Sequence[Optional[float]]] = None,
    *,
    title: str,
    height_px: int = 360,
) -> None:
    """
    Render a dual-axis ECharts view highlighting deviations of observed
    F10.7 flux from its 90-day mean baseline.

    Parameters
    ----------
    timestamps :
            Sequence of timestamps corresponding to the flux samples.
    observed_flux :
            Sequence of observed F10.7 flux values in solar flux units (sfu).
    ninety_day_mean :
            Optional sequence with the same length as ``timestamps`` containing
            90-day mean flux baselines. When provided, an anomaly bar series is
            rendered on a secondary axis. Missing entries are tolerated.
    title :
            Title to display at the top of the chart.
    height_px :
            Height of the rendered chart container in pixels.

    Raises
    ------
    ValueError
            If ``timestamps`` and ``observed_flux`` lengths differ.
    """
    if len(timestamps) != len(observed_flux):
        raise ValueError("timestamps and observed_flux must have the same length")
    if len(timestamps) == 0:
        st.info(f"{title}: no data to display.")
        return

    coerced_times = [
        pd.to_datetime(ts, utc=True, errors="coerce") for ts in timestamps
    ]
    valid_indices = [
        idx for idx, ts in enumerate(coerced_times) if pd.notna(ts)
    ]
    if not valid_indices:
        st.info(f"{title}: no valid timestamps to display.")
        return

    obs_points: List[List[Optional[float]]] = []
    mean_points: List[List[Optional[float]]] = []
    anomaly_points: List[Dict[str, Any]] = []
    diff_values: List[float] = []

    for idx in valid_indices:
        ts = coerced_times[idx]
        iso_ts = ts.isoformat()

        obs_raw = observed_flux[idx]
        obs_numeric: Optional[float]
        if obs_raw is None:
            obs_numeric = None
        else:
            obs_val = float(obs_raw)
            obs_numeric = obs_val if np.isfinite(obs_val) else None
        obs_points.append([iso_ts, obs_numeric])

        mean_numeric: Optional[float] = None
        if ninety_day_mean is not None:
            mean_raw = ninety_day_mean[idx]
            if mean_raw is not None:
                mean_val = float(mean_raw)
                if np.isfinite(mean_val):
                    mean_numeric = mean_val
        mean_points.append([iso_ts, mean_numeric])

        if mean_numeric is not None and obs_numeric is not None:
            diff_val = obs_numeric - mean_numeric
            diff_values.append(diff_val)
            anomaly_points.append(
                {
                    "value": [iso_ts, diff_val],
                    "itemStyle": {
                        "color": "#dc2626" if diff_val >= 0.0 else "#16a34a"
                    },
                }
            )
        else:
            anomaly_points.append({"value": [iso_ts, None]})

    if not any(point[1] is not None for point in obs_points):
        st.info(f"{title}: no observed flux values to display.")
        return

    has_mean_series = any(point[1] is not None for point in mean_points)
    has_anomaly_series = bool(diff_values)

    anomaly_axis: Optional[Dict[str, Any]] = None
    if has_anomaly_series:
        diff_span = max(abs(val) for val in diff_values)
        padding = max(5.0, diff_span * 0.15)
        axis_extent = diff_span + padding
        anomaly_axis = {
            "type": "value",
            "name": "Δ vs 90d mean (sfu)",
            "position": "right",
            "axisLabel": {"color": "#475569"},
            "splitLine": {"show": False},
            "min": -axis_extent,
            "max": axis_extent,
        }

    series: List[Dict[str, Any]] = [
        {
            "name": "Observed flux",
            "type": "line",
            "showSymbol": False,
            "smooth": True,
            "yAxisIndex": 0,
            "lineStyle": {"width": 3, "color": "#f97316"},
            "data": obs_points,
        }
    ]

    if has_mean_series:
        series.append(
            {
                "name": "90-day mean",
                "type": "line",
                "showSymbol": False,
                "smooth": True,
                "yAxisIndex": 0,
                "lineStyle": {"width": 2, "type": "dashed", "color": "#6366f1"},
                "data": mean_points,
            }
        )

    if has_anomaly_series and anomaly_axis is not None:
        series.append(
            {
                "name": "Δ vs 90d mean",
                "type": "bar",
                "yAxisIndex": 1,
                "barWidth": "65%",
                "itemStyle": {"opacity": 0.8},
                "emphasis": {"focus": "series"},
                "data": anomaly_points,
            }
        )

    y_axes: List[Dict[str, Any]] = [
        {
            "type": "value",
            "name": "Flux (sfu)",
            "axisLabel": {"color": "#475569"},
            "splitLine": {"lineStyle": {"color": "rgba(148,163,184,0.25)"}},
        }
    ]
    if anomaly_axis is not None:
        y_axes.append(anomaly_axis)

    opt = {
        "title": {"text": title, "left": "center"},
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "valueFormatter": (
                "function(value){if(value===null||isNaN(value)){return'—';}"
                "return value.toFixed(1)+' sfu';}"
            ),
        },
        "legend": {"top": 24},
        "grid": {
            "left": 48,
            "right": 32,
            "top": 56,
            "bottom": 48,
            "containLabel": True,
        },
        "dataZoom": [
            {"type": "inside"},
            {"type": "slider", "bottom": 12, "height": 18},
        ],
        "xAxis": {
            "type": "time",
            "axisLabel": {"color": "#475569"},
            "axisLine": {"lineStyle": {"color": "#cbd5f5"}},
        },
        "yAxis": y_axes,
        "series": series,
    }

    render_echarts(
        opt,
        height_px=height_px,
        width="100%",
        config=EChartsConfig())


def _echarts_line_with_ci(
    x_vals: List[float],
    y_vals: List[float],
    ci_low: List[float],
    ci_high: List[float],
    sig_mask: List[bool],
    *,
    title: str,
    x_name: str,
    y_name: str,
) -> None:
    # Build stacked area for CI: lower and (upper-lower)
    lower = []
    band = []
    scat = []
    for x, yl, yh, y, sig in zip(x_vals, ci_low, ci_high, y_vals, sig_mask):
        if np.isfinite(x) and np.isfinite(yl) and np.isfinite(yh):
            lower.append([float(x), float(yl)])
            band.append([float(x), float(max(0.0, yh - yl))])
        else:
            lower.append([float(x), None])
            band.append([float(x), None])
        if np.isfinite(x) and np.isfinite(y):
            scat.append(
                {
                    "value": [float(x), float(y)],
                    "itemStyle": {"color": "#d32f2f" if sig else "#1e88e5"},
                    "symbolSize": 8 if sig else 5,
                }
            )
    opt = {
        "title": {"text": title, "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"top": 24},
        "xAxis": {"type": "value", "name": x_name},
        "yAxis": {"type": "value", "name": y_name},
        "grid": {"left": 48, "right": 18, "containLabel": True},
        "series": [
            {
                "name": "CI low",
                "type": "line",
                "showSymbol": False,
                "data": lower,
                "lineStyle": {"opacity": 0},
            },
            {
                "name": "CI band",
                "type": "line",
                "showSymbol": False,
                "data": band,
                "stack": "ci",
                "areaStyle": {"color": "rgba(30,136,229,0.18)"},
                "lineStyle": {"opacity": 0},
            },
            {"name": "r (points)", "type": "scatter", "data": scat},
        ],
    }
    render_echarts(opt, height_px=340, width="100%", config=EChartsConfig())


def _echarts_time_with_ci(
    time_vals: List[pd.Timestamp],
    y_vals: List[float],
    ci_low: List[float],
    ci_high: List[float],
    *,
    title: str,
    y_name: str,
    series_name: str,
) -> None:
    lower = []
    band = []
    main = []
    for t, yl, yh, y in zip(time_vals, ci_low, ci_high, y_vals):
        if pd.notna(t):
            ts = str(t)
            lower.append([ts, float(yl) if np.isfinite(yl) else None])
            band.append(
                [ts, float(yh - yl) if (np.isfinite(yl) and np.isfinite(yh)) else None]
            )
            main.append([ts, float(y) if np.isfinite(y) else None])
    opt = {
        "title": {"text": title, "left": "center"},
        "tooltip": {"trigger": "axis"},
        "legend": {"top": 24},
        "xAxis": {"type": "time"},
        "yAxis": {"type": "value", "name": y_name},
        "grid": {"left": 48, "right": 18, "containLabel": True},
        "series": [
            {
                "name": "CI low",
                "type": "line",
                "showSymbol": False,
                "data": lower,
                "lineStyle": {"opacity": 0},
            },
            {
                "name": "CI band",
                "type": "line",
                "showSymbol": False,
                "data": band,
                "stack": "ci",
                "areaStyle": {"color": "rgba(30,136,229,0.15)"},
                "lineStyle": {"opacity": 0},
            },
            {
                "name": series_name,
                "type": "line",
                "showSymbol": False,
                "smooth": True,
                "data": main,
                "lineStyle": {"color": "#1e88e5", "width": 2},
            },
        ],
    }
    render_echarts(opt, height_px=340, width="100%", config=EChartsConfig())


def _echarts_gauge(
    value: float,
    *,
    min_val: float,
    max_val: float,
    title: str,
    unit: str = "",
    precision: int = 2,
    thresholds: Optional[List[Tuple[float, str]]] = None,
    formatter: Optional[str] = None,
    height_px: int = 300,
) -> None:
    if not np.isfinite(value):
        st.info(f"{title}: value unavailable.")
        return
    if max_val <= min_val:
        max_val = min_val + 1.0
    span = max_val - min_val
    value_clamped = float(np.clip(value, min_val, max_val))
    if formatter is not None and not isinstance(formatter, str):
        raise TypeError("formatter must be a string or None.")
    if precision < 0:
        raise ValueError("precision must be non-negative.")
    if height_px <= 0:
        raise ValueError("height_px must be positive.")
    display_numeric = round(value_clamped, precision)
    segments = thresholds or []
    color_segments: List[List[Any]] = []
    if segments:
        segments_sorted = sorted(segments, key=lambda item: item[0])
        for boundary, color in segments_sorted:
            ratio = (boundary - min_val) / span
            ratio = float(np.clip(ratio, 0.0, 1.0))
            color_segments.append([ratio, color])
        if color_segments and color_segments[-1][0] < 1.0:
            color_segments.append([1.0, color_segments[-1][1]])
    else:
        color_segments = [
            [0.33, "#22c55e"],
            [0.66, "#facc15"],
            [1.0, "#ef4444"],
        ]
    unit_suffix = f" {unit}" if unit else ""
    if formatter is None:
        detail_text = f"{display_numeric}{unit_suffix}"
    else:
        try:
            python_formatted = formatter.format(value=value_clamped)
        except (KeyError, IndexError, ValueError) as exc:
            st.warning(
                f"{title} gauge formatter '{formatter}' failed; using default display. ({exc})")
            python_formatted = str(display_numeric)
        if unit_suffix and unit not in python_formatted:
            detail_text = f"{python_formatted}{unit_suffix}"
        else:
            detail_text = python_formatted
    detail_text = str(detail_text)
    opt = {
        "title": {
            "text": title,
            "left": "center",
            "top": "0%",
            "textStyle": {"fontSize": 17, "fontWeight": 700, "color": "#0f172a"},
        },
        "series": [
            {
                "type": "gauge",
                "startAngle": 215,
                "endAngle": -35,
                "min": float(min_val),
                "max": float(max_val),
                "center": ["50%", "68%"],
                "radius": "92%",
                "splitNumber": 8,
                "progress": {"show": False},
                "axisLine": {
                    "roundCap": True,
                    "lineStyle": {"width": 14, "color": color_segments},
                },
                "axisTick": {
                    "distance": -18,
                    "length": 10,
                    "lineStyle": {"color": "rgba(15,23,42,0.35)", "width": 1},
                },
                "splitLine": {
                    "distance": -26,
                    "length": 20,
                    "lineStyle": {"color": "rgba(15,23,42,0.45)", "width": 2},
                },
                "axisLabel": {"distance": -36, "color": "#475569", "fontSize": 12},
                "pointer": {
                    "show": True,
                    "length": "62%",
                    "width": 6,
                    "itemStyle": {"color": "#2563eb"},
                },
                "anchor": {
                    "show": True,
                    "size": 10,
                    "itemStyle": {"borderColor": "#2563eb", "borderWidth": 2},
                },
                "title": {"show": False},
                "detail": {
                    "show": True,
                    "valueAnimation": True,
                    "offsetCenter": [0, "58%"],
                    "formatter": detail_text,
                    "color": "#0f172a",
                    "fontSize": 24,
                    "fontWeight": 600,
                },
                "data": [{"value": value_clamped}],
            },
            {
                "type": "gauge",
                "startAngle": 215,
                "endAngle": -35,
                "min": float(min_val),
                "max": float(max_val),
                "radius": "78%",
                "center": ["50%", "68%"],
                "pointer": {"show": False},
                "progress": {"show": False},
                "axisLine": {"show": False},
                "axisTick": {
                    "distance": 0,
                    "length": 6,
                    "lineStyle": {"color": "rgba(148,163,184,0.35)", "width": 1},
                },
                "splitLine": {
                    "distance": 0,
                    "length": 10,
                    "lineStyle": {"color": "rgba(148,163,184,0.45)", "width": 1.5},
                },
                "axisLabel": {"show": False},
                "detail": {"show": False},
                "data": [{"value": value_clamped}],
            },
        ],
    }
    render_echarts(
        opt,
        height_px=height_px,
        width="100%",
        config=EChartsConfig())


def _select_hrv_metric_columns(
    windowed_df: pd.DataFrame,
    *,
    exclude: Iterable[str] = (),
    limit: int = 8,
    preferred: Optional[Sequence[str]] = None,
) -> List[str]:
    """
    Select HRV metric columns appropriate for correlation analyses.

    Parameters
    ----------
    windowed_df : pd.DataFrame
            DataFrame containing windowed HRV metrics. May be empty.
    exclude : Iterable[str], optional
            Exact column names to omit from the result.
    limit : int, optional
            Maximum number of fallback numeric columns to return when the
            preferred metrics are absent.
    preferred : Optional[Sequence[str]], optional
            Ordered collection of preferred metric names to use when present.

    Returns
    -------
    List[str]
            Ordered list of metric column names suitable for correlation work.

    Raises
    ------
    ValueError
            If 'limit' is less than 1.
    TypeError
            If 'exclude' contains a non-string element.
    """
    if limit < 1:
        raise ValueError("limit must be at least 1.")
    exclude_set: Set[str] = set()
    for col in exclude:
        if not isinstance(col, str):
            raise TypeError("exclude entries must be strings.")
        exclude_set.add(col)
    if windowed_df.empty:
        return []
    baseline_preferred: Sequence[str] = preferred or (
        "rmssd",
        "sdnn",
        "hf_power",
        "lf_hf_ratio",
        "mean_hr",
        "pnn50",
        "pnn20",
    )
    selected: List[str] = []
    for column in baseline_preferred:
        if (
            column in windowed_df.columns
            and column not in exclude_set
            and pd.api.types.is_numeric_dtype(windowed_df[column])
        ):
            selected.append(column)
    if selected:
        return selected
    numeric_candidates = [
        column
        for column in windowed_df.select_dtypes(include=[np.number]).columns
        if column not in exclude_set
    ]
    return numeric_candidates[:limit]


def _scan_lag_correlations_generic(
    windowed_df: pd.DataFrame,
    predictor_df: pd.DataFrame,
    predictor_time_col: str,
    predictor_value_col: str,
    metrics: List[str],
    lags_hours: List[int],
    merge_tolerance_minutes: int = 90,
) -> pd.DataFrame:
    if windowed_df.empty or predictor_df.empty:
        return pd.DataFrame()
    w = windowed_df.copy()
    w["start"] = pd.to_datetime(w.get("start"), errors="coerce", utc=True)
    w = w.dropna(subset=["start"]).sort_values("start")
    if w.empty:
        return pd.DataFrame()
    pred = predictor_df.copy()
    pred[predictor_time_col] = pd.to_datetime(
        pred[predictor_time_col], errors="coerce", utc=True
    )
    pred = pred.dropna(
        subset=[
            predictor_time_col,
            predictor_value_col]).sort_values(predictor_time_col)
    if pred.empty:
        return pd.DataFrame()

    def _looks_daily(series: pd.Series) -> bool:
        """Heuristic: treat predictor as daily when cadence ≳ 1 day."""
        ts = pd.to_datetime(series, errors="coerce", utc=True).dropna()
        if ts.shape[0] < 3:
            return False
        diffs = ts.sort_values().diff().dropna()
        if diffs.empty:
            return False
        median_diff = diffs.median()
        if not isinstance(median_diff, pd.Timedelta):
            return False
        median_minutes = float(median_diff.total_seconds() / 60.0)
        if not np.isfinite(median_minutes) or median_minutes < 1440.0:
            return False
        # Daily aggregates typically sit on (or very near) midnight UTC.
        normalized = ts.dt.normalize()
        near_midnight = (ts - normalized).abs() <= pd.Timedelta(minutes=10)
        near_ratio = float(near_midnight.mean())
        return near_ratio >= 0.8

    use_daily_alignment = _looks_daily(pred[predictor_time_col])
    rows: List[pd.DataFrame] = []
    for lag in lags_hours:
        lag_int = int(lag)
        if use_daily_alignment:
            lag_days = int(lag_int / 24)
            w_dates = w["start"].dt.normalize()
            pred_dates = pred[predictor_time_col].dt.normalize() + pd.to_timedelta(
                lag_days, unit="D"
            )
            pred_vals = pd.to_numeric(
                pred[predictor_value_col], errors="coerce"
            ).astype(float)
            pred_by_date = (
                pd.DataFrame({"date": pred_dates, "value": pred_vals})
                .dropna(subset=["date", "value"])
                .groupby("date", sort=True)["value"]
                .mean()
            )
            if pred_by_date.empty:
                continue
            aligned_values = w_dates.map(pred_by_date)
            merged = w.copy()
            merged[predictor_value_col] = aligned_values.to_numpy(dtype=float)
            merged = merged.dropna(subset=[predictor_value_col])
        else:
            aligned = align_space_weather_series(
                reference_times=w["start"],
                predictor_df=pred,
                predictor_time_col=predictor_time_col,
                predictor_value_col=predictor_value_col,
                lag_hours=lag_int,
                max_gap_minutes=int(merge_tolerance_minutes),
            )
            if aligned.empty:
                continue
            merged = (
                w.set_index("start")
                .join(aligned.rename(predictor_value_col), how="inner")
                .dropna(subset=[predictor_value_col])
            )
        if merged.empty:
            continue
        corr_df = _corr_table(
            merged.reset_index(drop=True), predictor_value_col, metrics
        )
        corr_df["lag_hours"] = int(lag)
        rows.append(corr_df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


if __name__ == "__main__":
    main()
