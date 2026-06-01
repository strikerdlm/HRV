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

Author: Dr Diego Malpica MD
Version: 1.1.0
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
import io
import os
from dataclasses import asdict, is_dataclass, replace
from collections import Counter
from datetime import datetime, date, timezone, timedelta, tzinfo
from zoneinfo import ZoneInfo
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Final, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import streamlit as st

try:
    from logging_config import get_logger, log_exception
except ImportError:  # pragma: no cover - fallback if logging_config missing
    get_logger = None  # type: ignore[assignment]
    log_exception = None  # type: ignore[assignment]

# Safe rerun utility with debouncing and circuit breaker
try:
    from rerun_utils import safe_rerun
except ImportError:  # pragma: no cover - fallback if rerun_utils missing
    def safe_rerun(reason: str = "") -> None:  # type: ignore[misc]
        st.rerun()

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
        login_and_get_display_name,
        summarize_garmin_daily,
    )
except ImportError:  # pragma: no cover - optional
    GARMIN_LIB_AVAILABLE = False  # type: ignore[assignment]
    class GarminAuthError(RuntimeError):  # type: ignore[override]
        pass
    def fetch_garmin_daily_metrics(user_id: str, days: int = 14, *, email=None, password=None):  # type: ignore[misc]
        raise GarminAuthError("Garmin connect service unavailable.")
    def login_and_get_display_name(email: str, password: str) -> str:  # type: ignore[misc]
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
    from noaa_space import load_noaa_space_cache, load_noaa_space_data
    NOAA_SPACE_AVAILABLE = True
except ImportError:
    NOAA_SPACE_AVAILABLE = False
    load_noaa_space_data = None  # type: ignore[assignment]

# Radiation exposure module (evidence-based dose models)
try:
    from radiation_exposure import (
        RadiationEnvironment,
        RadiationDoseRate,
        RadiationLimits,
        EVARadiationStatus,
        EVARadiationAssessment,
        DOSE_RATE_DATABASE,
        NASA_RADIATION_LIMITS,
        assess_eva_radiation_risk,
        build_radiation_timeline,
        timeline_to_dataframe,
        compare_environments,
        get_environment_by_name,
        get_dose_rate_info,
        get_radiation_gauge_thresholds,
        cumulative_to_status,
    )
    RADIATION_MODULE_AVAILABLE = True
except ImportError:
    RADIATION_MODULE_AVAILABLE = False

# Advanced wearable analytics module
try:
    from wearable_analytics import (
        generate_wearable_insights,
        forecast_body_battery,
        calculate_allostatic_load,
        analyze_circadian_rhythm,
        predict_stress,
        analyze_recovery,
        calculate_metric_statistics,
        WearableInsights,
        BodyBatteryForecast,
        AllostasticLoadScore,
        CircadianAnalysis,
        StressPrediction,
        RecoveryAnalysis,
        RecoveryState,
        Chronotype,
        TrendDirection,
        RiskLevel,
    )
    WEARABLE_ANALYTICS_AVAILABLE = True
except ImportError:
    WEARABLE_ANALYTICS_AVAILABLE = False

# Advanced HRV Analytics module (ML, statistical tests, clinical decision support)
try:
    from advanced_hrv_analytics import (
        run_advanced_hrv_analysis,
        AdvancedHRVAnalysisResult,
        ClinicalDecisionSupport,
        MetricAssessment,
        StatisticalTestResult,
        TrendAnalysis,
        AnomalyDetection,
        PatternRecognition,
        HRVGarminIntegration,
        RiskLevel as HRVRiskLevel,
        TrendDirection as HRVTrendDirection,
        AutonomicState,
    )
    ADVANCED_HRV_ANALYTICS_AVAILABLE = True
except ImportError:
    ADVANCED_HRV_ANALYTICS_AVAILABLE = False

# Visualization helpers
from echarts_component import EChartsConfig, render_echarts as _render_echarts_base
from gauge_builder import GaugeThresholds, build_two_ring_gauge, get_gauge_thresholds

# Profile charts: disable animations to reduce rerender jitter and CPU usage
_PROFILE_ECHARTS_CONFIG: Final[EChartsConfig] = EChartsConfig(disable_animation=True)


def render_echarts(  # type: ignore[override]
    option: Dict[str, Any],
    *,
    height_px: int = 420,
    width: str = "100%",
    theme: Optional[str] = None,
    config: Optional[EChartsConfig] = None,
    renderer: str = "svg",
    enable_export: bool = True,
    export_basename: str = "echarts_chart",
    caption: Optional[str] = None,
) -> None:
    """Render ECharts in the profile tab with animations disabled by default."""
    cfg = config or _PROFILE_ECHARTS_CONFIG
    if cfg is not None and not cfg.disable_animation:
        cfg = replace(cfg, disable_animation=True)
    _render_echarts_base(
        option,
        height_px=height_px,
        width=width,
        theme=theme,
        config=cfg,
        renderer=renderer,
        enable_export=enable_export,
        export_basename=export_basename,
        caption=caption,
    )

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
from hrv_core import (
    build_readiness_baseline,
    load_rr_intervals_from_text,
    readiness_from_pns,
    compute_baevsky_stress_index,
    compute_parasympathetic_index,
)

# Polar H10 BLE Recorder
try:
    from polar_h10_recorder import (
        PolarH10RecorderSync,
        RecorderState,
        RecordingStats,
        ScannedDevice,
        get_output_directory,
        is_bleak_available,
        list_recordings,
    )
    POLAR_RECORDER_AVAILABLE = True
except ImportError:
    POLAR_RECORDER_AVAILABLE = False
    is_bleak_available = lambda: False  # type: ignore[misc]

# ---------------------------------------------------------------------------
# Scientific Visualization Constants (Age-Stratified HRV Normative Data)
# Reference: Nunan et al. (2010), Shaffer & Ginsberg (2017)
# ---------------------------------------------------------------------------

# Age-stratified RMSSD reference values: (mean, sd, p5, p25, p50, p75, p95)
# Source: Meta-analysis of Nunan et al. 2010, WHOOP population data, Shaffer 2017
AGE_RMSSD_NORMS: Dict[Tuple[int, int], Dict[str, float]] = {
    (18, 25): {"mean": 42.0, "sd": 19.0, "p5": 19.0, "p25": 30.0, "p50": 40.0, "p75": 55.0, "p95": 75.0},
    (26, 35): {"mean": 39.0, "sd": 18.0, "p5": 17.0, "p25": 27.0, "p50": 37.0, "p75": 50.0, "p95": 70.0},
    (36, 45): {"mean": 35.0, "sd": 17.0, "p5": 15.0, "p25": 23.0, "p50": 33.0, "p75": 45.0, "p95": 63.0},
    (46, 55): {"mean": 30.0, "sd": 15.0, "p5": 12.0, "p25": 19.0, "p50": 28.0, "p75": 40.0, "p95": 55.0},
    (56, 65): {"mean": 25.0, "sd": 13.0, "p5": 10.0, "p25": 16.0, "p50": 24.0, "p75": 34.0, "p95": 48.0},
    (66, 100): {"mean": 21.0, "sd": 11.0, "p5": 8.0, "p25": 13.0, "p50": 20.0, "p75": 28.0, "p95": 40.0},
}

# Age-stratified SDNN reference values (24-hour recordings extrapolated to short-term)
# Source: Task Force (1996), Nunan et al. (2010), Umetani et al. (1998)
AGE_SDNN_NORMS: Dict[Tuple[int, int], Dict[str, float]] = {
    (18, 25): {"mean": 55.0, "sd": 20.0, "p5": 28.0, "p25": 42.0, "p50": 53.0, "p75": 68.0, "p95": 90.0},
    (26, 35): {"mean": 50.0, "sd": 19.0, "p5": 25.0, "p25": 38.0, "p50": 48.0, "p75": 62.0, "p95": 85.0},
    (36, 45): {"mean": 45.0, "sd": 18.0, "p5": 22.0, "p25": 33.0, "p50": 43.0, "p75": 56.0, "p95": 78.0},
    (46, 55): {"mean": 40.0, "sd": 16.0, "p5": 18.0, "p25": 29.0, "p50": 38.0, "p75": 50.0, "p95": 68.0},
    (56, 65): {"mean": 35.0, "sd": 14.0, "p5": 15.0, "p25": 25.0, "p50": 33.0, "p75": 44.0, "p95": 60.0},
    (66, 100): {"mean": 30.0, "sd": 12.0, "p5": 12.0, "p25": 21.0, "p50": 28.0, "p75": 38.0, "p95": 52.0},
}

# Age-stratified LF/HF ratio reference values (indicative of sympathovagal balance)
# Source: Nunan et al. (2010), Shaffer & Ginsberg (2017)
AGE_LF_HF_NORMS: Dict[Tuple[int, int], Dict[str, float]] = {
    (18, 25): {"mean": 1.5, "sd": 1.0, "p5": 0.5, "p25": 0.9, "p50": 1.4, "p75": 2.0, "p95": 3.5},
    (26, 35): {"mean": 1.8, "sd": 1.2, "p5": 0.6, "p25": 1.0, "p50": 1.6, "p75": 2.4, "p95": 4.0},
    (36, 45): {"mean": 2.0, "sd": 1.3, "p5": 0.7, "p25": 1.1, "p50": 1.8, "p75": 2.7, "p95": 4.5},
    (46, 55): {"mean": 2.2, "sd": 1.4, "p5": 0.8, "p25": 1.2, "p50": 2.0, "p75": 3.0, "p95": 5.0},
    (56, 65): {"mean": 2.5, "sd": 1.5, "p5": 0.9, "p25": 1.4, "p50": 2.3, "p75": 3.4, "p95": 5.5},
    (66, 100): {"mean": 2.8, "sd": 1.6, "p5": 1.0, "p25": 1.6, "p50": 2.6, "p75": 3.8, "p95": 6.0},
}

# Resting heart rate age-stratified norms (seated/supine)
# Source: Tanaka et al. (2001), AHA guidelines
AGE_HR_NORMS: Dict[Tuple[int, int], Dict[str, float]] = {
    (18, 25): {"mean": 70.0, "sd": 10.0, "p5": 52.0, "p25": 62.0, "p50": 70.0, "p75": 78.0, "p95": 88.0},
    (26, 35): {"mean": 72.0, "sd": 10.0, "p5": 54.0, "p25": 64.0, "p50": 72.0, "p75": 80.0, "p95": 90.0},
    (36, 45): {"mean": 73.0, "sd": 10.0, "p5": 55.0, "p25": 65.0, "p50": 73.0, "p75": 81.0, "p95": 91.0},
    (46, 55): {"mean": 74.0, "sd": 10.0, "p5": 56.0, "p25": 66.0, "p50": 74.0, "p75": 82.0, "p95": 92.0},
    (56, 65): {"mean": 74.0, "sd": 10.0, "p5": 56.0, "p25": 66.0, "p50": 74.0, "p75": 82.0, "p95": 92.0},
    (66, 100): {"mean": 72.0, "sd": 10.0, "p5": 54.0, "p25": 64.0, "p50": 72.0, "p75": 80.0, "p95": 90.0},
}

# Scientific color palette (colorblind-friendly)
SCIENTIFIC_COLORS = {
    "primary": "#1f77b4",      # Blue - main data
    "smoothed": "#2ca02c",     # Green - smoothed trend
    "normal_band": "#d4e6f1",  # Light blue - normal range
    "optimal_band": "#d5f5e3", # Light green - optimal range
    "warning": "#f39c12",      # Orange - caution
    "alert": "#e74c3c",        # Red - alert
    "grid": "#ecf0f1",         # Light gray - grid
    "text": "#2c3e50",         # Dark gray - text
    "lf_band": "#e74c3c",      # Red - LF power
    "hf_band": "#3498db",      # Blue - HF power
    "vlf_band": "#9b59b6",     # Purple - VLF power
}


def _get_age_rmssd_norms(age: int) -> Dict[str, float]:
    """Get RMSSD normative values for a given age.
    
    Args:
        age: Subject's age in years.
        
    Returns:
        Dictionary with mean, sd, and percentile values.
    """
    for (age_min, age_max), norms in AGE_RMSSD_NORMS.items():
        if age_min <= age <= age_max:
            return norms
    # Default to middle-aged norms if age out of range
    return AGE_RMSSD_NORMS[(36, 45)]


def _get_age_sdnn_norms(age: int) -> Dict[str, float]:
    """Get SDNN normative values for a given age.
    
    SDNN reflects total autonomic variability including both sympathetic 
    and parasympathetic contributions. It decreases with age due to
    reduced cardiac autonomic modulation.
    
    Args:
        age: Subject's age in years.
        
    Returns:
        Dictionary with mean, sd, and percentile values.
    """
    for (age_min, age_max), norms in AGE_SDNN_NORMS.items():
        if age_min <= age <= age_max:
            return norms
    return AGE_SDNN_NORMS[(36, 45)]


def _get_age_lf_hf_norms(age: int) -> Dict[str, float]:
    """Get LF/HF ratio normative values for a given age.
    
    LF/HF ratio is an indicator of sympathovagal balance, though its
    interpretation is debated. Higher values typically suggest sympathetic
    dominance; ratio tends to increase with age as parasympathetic tone declines.
    
    Args:
        age: Subject's age in years.
        
    Returns:
        Dictionary with mean, sd, and percentile values.
    """
    for (age_min, age_max), norms in AGE_LF_HF_NORMS.items():
        if age_min <= age <= age_max:
            return norms
    return AGE_LF_HF_NORMS[(36, 45)]


def _get_age_hr_norms(age: int) -> Dict[str, float]:
    """Get resting heart rate normative values for a given age.
    
    Resting HR reflects basal autonomic tone. Lower resting HR is generally
    associated with better cardiovascular fitness and higher vagal tone.
    
    Args:
        age: Subject's age in years.
        
    Returns:
        Dictionary with mean, sd, and percentile values.
    """
    for (age_min, age_max), norms in AGE_HR_NORMS.items():
        if age_min <= age <= age_max:
            return norms
    return AGE_HR_NORMS[(36, 45)]


def _get_age_group_label(age: int) -> str:
    """Get descriptive age group label."""
    for (age_min, age_max) in AGE_RMSSD_NORMS.keys():
        if age_min <= age <= age_max:
            return f"{age_min}-{age_max} years"
    return "36-45 years"


def _ewma_smooth(data: np.ndarray, span: int = 7) -> np.ndarray:
    """Apply exponentially weighted moving average smoothing with NaN handling.
    
    NaN values are skipped during computation - the smoothed value carries forward
    from the previous valid observation. This prevents a single NaN from propagating
    through the entire output array.
    
    Args:
        data: Input time series (may contain NaN values).
        span: Decay span (higher = more smoothing).
        
    Returns:
        Smoothed time series with NaN preserved at positions where no prior
        valid data exists.
    """
    if len(data) == 0:
        return np.array([], dtype=float)
    
    alpha = 2.0 / (span + 1)
    result = np.full_like(data, np.nan, dtype=float)
    
    # Find first non-NaN value to initialize
    first_valid_idx = -1
    for i in range(len(data)):
        if not np.isnan(data[i]):
            first_valid_idx = i
            result[i] = data[i]
            break
    
    # If no valid data, return all NaN
    if first_valid_idx == -1:
        return result
    
    # Apply EWMA, skipping NaN values
    last_valid = result[first_valid_idx]
    for i in range(first_valid_idx + 1, len(data)):
        if np.isnan(data[i]):
            # Carry forward the last valid smoothed value
            result[i] = last_valid
        else:
            result[i] = alpha * data[i] + (1 - alpha) * last_valid
            last_valid = result[i]
    
    return result


def _auto_axis_bounds(
    *data_arrays: Optional[List[Optional[float]]],
    padding_pct: float = 0.10,
    min_floor: Optional[float] = None,
    max_ceil: Optional[float] = None,
    nice_round: bool = True,
) -> Tuple[float, float]:
    """Calculate dynamic axis bounds that fit all data with padding.
    
    This ensures all data points are visible within the chart frame,
    with appropriate padding for visual clarity.
    
    Args:
        *data_arrays: Variable number of data arrays to consider.
        padding_pct: Padding as percentage of data range (default 10%).
        min_floor: Optional minimum floor value (e.g., 0 for non-negative data).
        max_ceil: Optional maximum ceiling value (e.g., 100 for percentages).
        nice_round: If True, round to "nice" values for cleaner axis labels.
        
    Returns:
        Tuple of (min_value, max_value) for axis configuration.
        
    Example:
        >>> hr_min, hr_max = _auto_axis_bounds(resting_hr, avg_hr, padding_pct=0.15)
        >>> y_axis = {"type": "value", "min": hr_min, "max": hr_max}
    """
    # Collect all valid (non-None, non-NaN) values
    all_values: List[float] = []
    for arr in data_arrays:
        if arr is None:
            continue
        for v in arr:
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                all_values.append(float(v))
    
    # If no valid data, return sensible defaults
    if not all_values:
        return (0.0, 100.0)
    
    data_min = min(all_values)
    data_max = max(all_values)
    data_range = data_max - data_min
    
    # Handle edge case where all values are the same
    if data_range == 0:
        data_range = abs(data_min) * 0.2 if data_min != 0 else 10.0
    
    # Apply padding
    padding = data_range * padding_pct
    calc_min = data_min - padding
    calc_max = data_max + padding
    
    # Apply floor/ceiling constraints
    if min_floor is not None:
        calc_min = max(calc_min, min_floor)
    if max_ceil is not None:
        calc_max = min(calc_max, max_ceil)
    
    # Round to "nice" values for cleaner axis labels
    if nice_round:
        # Determine appropriate rounding based on magnitude
        magnitude = 10 ** np.floor(np.log10(max(abs(calc_max - calc_min), 1)))
        round_to = magnitude / 2  # Round to half the magnitude
        
        # For small ranges (like percentages), use smaller rounding
        if data_range < 20:
            round_to = 5
        elif data_range < 100:
            round_to = 10
        else:
            round_to = max(10, round_to)
        
        calc_min = np.floor(calc_min / round_to) * round_to
        calc_max = np.ceil(calc_max / round_to) * round_to
        
        # Re-apply constraints after rounding
        if min_floor is not None:
            calc_min = max(calc_min, min_floor)
        if max_ceil is not None:
            calc_max = min(calc_max, max_ceil)
    
    return (float(calc_min), float(calc_max))


# ---------------------------------------------------------------------------
# Physiological Interpretation Constants for Graduate-Level Documentation
# References: Shaffer & Ginsberg (2017), Thayer et al. (2012), Porges (2007)
# ---------------------------------------------------------------------------

HRV_PHYSIOLOGICAL_INTERPRETATIONS = {
    "rmssd": """
**RMSSD (Root Mean Square of Successive Differences)**

RMSSD quantifies beat-to-beat variability and is the primary index of **parasympathetic 
(vagal) cardiac modulation**. It reflects the efferent vagal tone transmitted via the 
vagus nerve to the sinoatrial node.

**Physiological Basis:**
- Vagal efferent activity causes rapid, beat-to-beat adjustments in heart rate through 
  muscarinic receptor activation on pacemaker cells
- The short time constants of vagal effects (~200 ms) are captured by successive difference metrics
- RMSSD correlates strongly with respiratory sinus arrhythmia (RSA) and high-frequency (HF) power

**Clinical Significance:**
- Higher RMSSD indicates greater parasympathetic capacity and autonomic flexibility
- Low RMSSD is associated with reduced vagal tone, chronic stress, and cardiovascular risk
- Age-related decline: ~6% decrease per decade after age 20 (Umetani et al., 1998)
- Training effect: Endurance athletes typically show RMSSD 30-50% above age-matched controls

**References:** Shaffer & Ginsberg (2017), Thayer et al. (2012), Task Force (1996)
    """,
    
    "sdnn": """
**SDNN (Standard Deviation of NN Intervals)**

SDNN reflects the **total autonomic variability** encompassing both sympathetic and 
parasympathetic contributions over the recording period.

**Physiological Basis:**
- SDNN captures all cyclic components of variability including circadian rhythms, 
  thermoregulation, and baroreflex activity
- In short-term recordings (5 min), parasympathetic influences predominate
- In 24-hour recordings, SDNN reflects circadian HRV patterns and overall autonomic reserve

**Clinical Significance:**
- SDNN < 50 ms (24-hr) is associated with 2.5× increased mortality risk (Kleiger et al., 1987)
- SDNN correlates with cardiovascular prognosis across multiple disease states
- Reflects "autonomic reserve" – the system's capacity to respond to physiological demands
- Age-related decline: ~3-4 ms per decade (Umetani et al., 1998)

**References:** Task Force (1996), Kleiger et al. (1987), Shaffer & Ginsberg (2017)
    """,
    
    "lf_hf_ratio": """
**LF/HF Ratio (Low Frequency / High Frequency Power Ratio)**

The LF/HF ratio has traditionally been interpreted as an index of **sympathovagal balance**, 
though this interpretation is now considered oversimplified.

**Physiological Basis:**
- HF power (0.15-0.40 Hz) reflects parasympathetic activity modulated by respiration
- LF power (0.04-0.15 Hz) reflects a mixture of sympathetic and parasympathetic activity, 
  particularly baroreflex-mediated oscillations
- The ratio increases with sympathetic activation (stress, standing, exercise)

**Clinical Considerations:**
- Higher ratios suggest relative sympathetic dominance
- The ratio increases with age due to declining parasympathetic tone
- Interpretation limitations: LF is not purely sympathetic; respiratory frequency affects HF
- Modern consensus: LF may better reflect baroreflex function than sympathetic activity

**Age-Related Changes:**
- LF/HF typically increases 10-15% per decade after age 30
- This reflects declining vagal modulation rather than increased sympathetic activity

**References:** Shaffer & Ginsberg (2017), Billman (2013), Reyes del Paso et al. (2013)
    """,
    
    "heart_rate": """
**Resting Heart Rate**

Resting heart rate reflects the net balance of sympathetic and parasympathetic 
influences on the sinoatrial node at rest.

**Physiological Basis:**
- The intrinsic rate of the sinoatrial node is ~100-120 bpm
- At rest, vagal tone predominates, reducing rate to ~60-80 bpm
- Lower resting HR indicates greater parasympathetic ("vagal brake") influence
- Sympathetic activity increases HR through β-adrenergic receptor activation

**Clinical Significance:**
- Resting HR > 80 bpm is associated with increased cardiovascular mortality
- Each 10 bpm increase is associated with ~20% higher all-cause mortality risk
- Trained individuals often exhibit resting HR of 40-60 bpm (vagal adaptation)
- HR recovery after exercise (HRR) is a powerful prognostic indicator

**Autonomic Context:**
- HR and HRV are inversely related: lower HR typically correlates with higher HRV
- This relationship reflects the mathematical constraint of beat-to-beat timing
- Pharmacological vagal blockade increases HR to ~90-100 bpm

**References:** Fox et al. (2007), Cooney et al. (2010), Shaffer & Ginsberg (2017)
    """,
    
    "stress_recovery": """
**HRV and the Stress-Recovery Paradigm**

Heart rate variability provides a window into the **allostatic load** – the cumulative 
wear from chronic stress adaptation.

**The Polyvagal Perspective (Porges, 2007):**
- High vagal tone supports social engagement, rest, and restoration
- Stress triggers vagal withdrawal, shifting autonomic balance toward sympathetic dominance
- Chronic stress impairs vagal recovery, reducing HRV chronically

**Recovery Indicators:**
- Morning RMSSD: Reflects overnight recovery; low values suggest incomplete restoration
- Day-to-day variability: High variability with recovering trend indicates healthy adaptation
- Training response: HRV suppression following intense exercise is normal; 
  sustained suppression (>48 hr) suggests inadequate recovery

**Practical Interpretation:**
- Baseline establishment: 2-4 weeks of daily measurements establish individual norms
- Coefficient of variation (CV) of RMSSD: ~10-20% is typical for healthy individuals
- CV > 30% may indicate significant allostatic instability or measurement inconsistency

**References:** Porges (2007), Thayer & Lane (2000), Plews et al. (2013)
    """
}


def _build_hrv_history_dual_axis_chart(
    dates: List[str],
    rmssd_values: List[float],
    sdnn_values: Optional[List[float]],
    age: int = 35,
    title: str = "HRV Time-Domain Metrics with Age-Adjusted Reference Ranges",
) -> Dict[str, Any]:
    """Build publication-quality dual-axis HRV chart with RMSSD and SDNN.
    
    Scientific design principles (Nature, Science guidelines):
    - Clean typography with adequate whitespace
    - Colorblind-friendly palette
    - Age-stratified reference bands for clinical context
    - EWMA smoothing for trend visualization
    - Interactive data exploration with zoom/pan
    
    Args:
        dates: List of date strings.
        rmssd_values: RMSSD values in ms.
        sdnn_values: Optional SDNN values in ms.
        age: Subject age for normative ranges.
        title: Chart title.
        
    Returns:
        ECharts option dictionary.
    """
    rmssd_norms = _get_age_rmssd_norms(age)
    sdnn_norms = _get_age_sdnn_norms(age) if sdnn_values else None
    age_label = _get_age_group_label(age)
    
    rmssd_arr = np.array(rmssd_values, dtype=float)
    rmssd_ewma = _ewma_smooth(rmssd_arr, span=7).tolist()
    
    # 7-day rolling average
    rmssd_ma7 = []
    for i in range(len(rmssd_values)):
        start_idx = max(0, i - 6)
        rmssd_ma7.append(float(np.mean(rmssd_arr[start_idx:i + 1])))
    
    date_labels = [str(d)[:10] if len(str(d)) > 10 else str(d) for d in dates]
    
    series: List[Dict[str, Any]] = []
    
    # RMSSD normal range band (5th-95th percentile)
    series.extend([
        {
            "name": f"RMSSD Normal Range (5th-95th %ile, age {age_label})",
            "type": "line",
            "data": [rmssd_norms["p95"]] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "rgba(52, 152, 219, 0.15)", "opacity": 0.5},
            "stack": "rmssd_band",
            "symbol": "none",
            "silent": True,
            "yAxisIndex": 0,
        },
        {
            "name": "_rmssd_lower",
            "type": "line",
            "data": [rmssd_norms["p5"]] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "#fff", "opacity": 1},
            "stack": "rmssd_band",
            "symbol": "none",
            "silent": True,
            "yAxisIndex": 0,
        },
    ])
    
    # RMSSD population mean reference
    series.append({
        "name": f"RMSSD Population Mean ({rmssd_norms['mean']:.0f} ms)",
        "type": "line",
        "data": [rmssd_norms["mean"]] * len(dates),
        "lineStyle": {"color": "#95a5a6", "width": 2, "type": "dotted"},
        "symbol": "none",
        "silent": True,
        "yAxisIndex": 0,
    })
    
    # RMSSD data series
    series.extend([
        {
            "name": "RMSSD",
            "type": "line",
            "data": rmssd_values,
            "symbol": "circle",
            "symbolSize": 7,
            "itemStyle": {"color": SCIENTIFIC_COLORS["primary"]},
            "lineStyle": {"color": SCIENTIFIC_COLORS["primary"], "width": 2},
            "emphasis": {"itemStyle": {"borderWidth": 2, "borderColor": "#fff"}},
            "yAxisIndex": 0,
        },
        {
            "name": "RMSSD 7-Day MA",
            "type": "line",
            "data": rmssd_ma7,
            "symbol": "none",
            "lineStyle": {"color": SCIENTIFIC_COLORS["smoothed"], "width": 2.5},
            "smooth": True,
            "yAxisIndex": 0,
        },
        {
            "name": "RMSSD EWMA Trend",
            "type": "line",
            "data": rmssd_ewma,
            "symbol": "none",
            "lineStyle": {"color": "#e67e22", "width": 2, "type": "dashed"},
            "smooth": True,
            "yAxisIndex": 0,
        },
    ])
    
    # Add SDNN series if available
    y_axes = [
        {
            "type": "value",
            "name": "RMSSD (ms)",
            "nameLocation": "middle",
            "nameGap": 50,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["primary"]},
            "min": 0,
            "max": max(max(rmssd_values) * 1.3, rmssd_norms["p95"] * 1.15),
            "axisLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["primary"]}},
            "axisLabel": {"color": SCIENTIFIC_COLORS["primary"]},
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        }
    ]
    
    if sdnn_values and sdnn_norms:
        sdnn_arr = np.array(sdnn_values, dtype=float)
        sdnn_ewma = _ewma_smooth(sdnn_arr, span=7).tolist()
        
        # SDNN normal range band
        series.extend([
            {
                "name": f"SDNN Normal Range (5th-95th %ile)",
                "type": "line",
                "data": [sdnn_norms["p95"]] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(155, 89, 182, 0.15)", "opacity": 0.5},
                "stack": "sdnn_band",
                "symbol": "none",
                "silent": True,
                "yAxisIndex": 1,
            },
            {
                "name": "_sdnn_lower",
                "type": "line",
                "data": [sdnn_norms["p5"]] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff", "opacity": 1},
                "stack": "sdnn_band",
                "symbol": "none",
                "silent": True,
                "yAxisIndex": 1,
            },
        ])
        
        # SDNN data
        series.extend([
            {
                "name": "SDNN",
                "type": "line",
                "data": sdnn_values,
                "symbol": "diamond",
                "symbolSize": 6,
                "itemStyle": {"color": "#9b59b6"},
                "lineStyle": {"color": "#9b59b6", "width": 2},
                "yAxisIndex": 1,
            },
            {
                "name": "SDNN EWMA",
                "type": "line",
                "data": sdnn_ewma,
                "symbol": "none",
                "lineStyle": {"color": "#8e44ad", "width": 2, "type": "dashed"},
                "smooth": True,
                "yAxisIndex": 1,
            },
        ])
        
        y_axes.append({
            "type": "value",
            "name": "SDNN (ms)",
            "nameLocation": "middle",
            "nameGap": 50,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold", "color": "#9b59b6"},
            "min": 0,
            "max": max(max(sdnn_values) * 1.3, sdnn_norms["p95"] * 1.15),
            "position": "right",
            "axisLine": {"lineStyle": {"color": "#9b59b6"}},
            "axisLabel": {"color": "#9b59b6"},
            "splitLine": {"show": False},
        })
    
    legend_data = ["RMSSD", "RMSSD 7-Day MA", "RMSSD EWMA Trend"]
    if sdnn_values:
        legend_data.extend(["SDNN", "SDNN EWMA"])
    
    return {
        "title": {
            "text": title,
            "subtext": f"Age: {age} years (reference group: {age_label}) | "
                       f"N = {len(dates)} measurements | "
                       f"Ref: Nunan et al. (2010), Shaffer & Ginsberg (2017)",
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "backgroundColor": "rgba(255,255,255,0.95)",
            "borderColor": "#ccc",
            "textStyle": {"color": SCIENTIFIC_COLORS["text"], "fontSize": 11},
        },
        "legend": {
            "data": legend_data,
            "bottom": 5,
            "textStyle": {"fontSize": 10},
        },
        "grid": {
            "left": "10%",
            "right": "10%" if sdnn_values else "5%",
            "top": "15%",
            "bottom": "18%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": date_labels,
            "name": "Measurement Date",
            "nameLocation": "middle",
            "nameGap": 35,
            "nameTextStyle": {"fontSize": 11, "fontWeight": "bold"},
            "axisLabel": {"rotate": 45, "fontSize": 9},
            "axisLine": {"lineStyle": {"color": "#bdc3c7"}},
        },
        "yAxis": y_axes,
        "series": series,
        "dataZoom": [
            {"type": "inside", "start": 0, "end": 100},
            {"type": "slider", "start": 0, "end": 100, "height": 18, "bottom": 30},
        ],
    }


def _build_hr_trend_chart(
    dates: List[str],
    hr_values: List[float],
    age: int = 35,
    title: str = "Resting Heart Rate Trend with Age-Based Reference",
) -> Dict[str, Any]:
    """Build publication-quality heart rate trend chart.
    
    Lower resting HR generally indicates better cardiovascular fitness
    and higher vagal tone. Chart includes age-adjusted normal range.
    
    Args:
        dates: Date labels.
        hr_values: Heart rate values in bpm.
        age: Subject age for normative context.
        title: Chart title.
        
    Returns:
        ECharts option dictionary.
    """
    hr_norms = _get_age_hr_norms(age)
    age_label = _get_age_group_label(age)
    
    hr_arr = np.array(hr_values, dtype=float)
    hr_ewma = _ewma_smooth(hr_arr, span=7).tolist()
    
    date_labels = [str(d)[:10] for d in dates]
    
    return {
        "title": {
            "text": title,
            "subtext": f"Age group: {age_label} | Population mean: {hr_norms['mean']:.0f} bpm | "
                       f"Optimal: <{hr_norms['p25']:.0f} bpm",
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": """function(params) {
                var date = params[0].axisValue;
                var result = '<b>' + date + '</b><br/>';
                params.forEach(function(p) {
                    if (p.value !== null && p.value !== undefined) {
                        result += p.marker + ' ' + p.seriesName + ': <b>' + p.value.toFixed(0) + ' bpm</b><br/>';
                    }
                });
                return result;
            }""",
        },
        "legend": {
            "data": ["Heart Rate", "7-Day Trend"],
            "bottom": 5,
            "textStyle": {"fontSize": 10},
        },
        "grid": {
            "left": "8%",
            "right": "5%",
            "top": "15%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": date_labels,
            "name": "Date",
            "nameLocation": "middle",
            "nameGap": 30,
            "axisLabel": {"rotate": 45, "fontSize": 9},
        },
        "yAxis": {
            "type": "value",
            "name": "Heart Rate (bpm)",
            "nameLocation": "middle",
            "nameGap": 45,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": max(40, min(hr_values) * 0.85),
            "max": min(120, max(hr_values) * 1.15),
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        },
        "visualMap": {
            "show": False,
            "dimension": 1,
            "pieces": [
                {"lt": 60, "color": "#27ae60"},           # Athletic/excellent
                {"gte": 60, "lt": 70, "color": "#3498db"},  # Good
                {"gte": 70, "lt": 80, "color": "#f39c12"},  # Normal
                {"gte": 80, "lt": 90, "color": "#e67e22"},  # Elevated
                {"gte": 90, "color": "#e74c3c"},           # High
            ],
        },
        "series": [
            # Normal range band
            {
                "name": f"Normal Range ({hr_norms['p25']:.0f}-{hr_norms['p75']:.0f} bpm)",
                "type": "line",
                "data": [hr_norms["p75"]] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(46, 204, 113, 0.15)"},
                "stack": "hr_band",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "_hr_lower",
                "type": "line",
                "data": [hr_norms["p25"]] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "hr_band",
                "symbol": "none",
                "silent": True,
            },
            # Population mean
            {
                "name": "Population Mean",
                "type": "line",
                "data": [hr_norms["mean"]] * len(dates),
                "lineStyle": {"color": "#95a5a6", "width": 2, "type": "dotted"},
                "symbol": "none",
            },
            # HR data
            {
                "name": "Heart Rate",
                "type": "line",
                "data": [[d, v] for d, v in zip(date_labels, hr_values)],
                "symbol": "circle",
                "symbolSize": 7,
                "lineStyle": {"width": 2},
            },
            # EWMA trend
            {
                "name": "7-Day Trend",
                "type": "line",
                "data": hr_ewma,
                "symbol": "none",
                "lineStyle": {"color": "#2c3e50", "width": 2.5},
                "smooth": True,
            },
        ],
        "dataZoom": [
            {"type": "inside", "start": 0, "end": 100},
        ],
    }


def _build_lf_hf_trend_chart(
    dates: List[str],
    lf_hf_values: List[float],
    age: int = 35,
    title: str = "Sympathovagal Balance (LF/HF Ratio) Trend",
) -> Dict[str, Any]:
    """Build LF/HF ratio trend chart with physiological context.
    
    LF/HF ratio indicates relative sympathetic vs parasympathetic influence.
    Higher values suggest sympathetic dominance (stress, arousal).
    
    Args:
        dates: Date labels.
        lf_hf_values: LF/HF ratio values.
        age: Subject age for normative reference.
        title: Chart title.
        
    Returns:
        ECharts option dictionary.
    """
    lf_hf_norms = _get_age_lf_hf_norms(age)
    age_label = _get_age_group_label(age)
    
    lf_hf_arr = np.array(lf_hf_values, dtype=float)
    lf_hf_ewma = _ewma_smooth(lf_hf_arr, span=7).tolist()
    
    date_labels = [str(d)[:10] for d in dates]
    
    return {
        "title": {
            "text": title,
            "subtext": f"Age group: {age_label} | Higher ratio = sympathetic dominance | "
                       f"Lower ratio = parasympathetic dominance",
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
        },
        "legend": {
            "data": ["LF/HF Ratio", "7-Day Trend"],
            "bottom": 5,
        },
        "grid": {
            "left": "8%",
            "right": "5%",
            "top": "15%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": date_labels,
            "axisLabel": {"rotate": 45, "fontSize": 9},
        },
        "yAxis": {
            "type": "value",
            "name": "LF/HF Ratio",
            "nameLocation": "middle",
            "nameGap": 45,
            "min": 0,
            "max": max(max(lf_hf_values) * 1.3, lf_hf_norms["p95"] * 1.1),
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        },
        "visualMap": {
            "show": False,
            "dimension": 1,
            "pieces": [
                {"lt": 1.0, "color": "#3498db"},          # Parasympathetic dominant
                {"gte": 1.0, "lt": 2.0, "color": "#27ae60"},  # Balanced
                {"gte": 2.0, "lt": 3.5, "color": "#f39c12"},  # Mild sympathetic
                {"gte": 3.5, "color": "#e74c3c"},         # High sympathetic
            ],
        },
        "series": [
            # Normal range band
            {
                "name": f"Typical Range ({lf_hf_norms['p25']:.1f}-{lf_hf_norms['p75']:.1f})",
                "type": "line",
                "data": [lf_hf_norms["p75"]] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(46, 204, 113, 0.12)"},
                "stack": "lf_hf_band",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "_lf_hf_lower",
                "type": "line",
                "data": [lf_hf_norms["p25"]] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "lf_hf_band",
                "symbol": "none",
                "silent": True,
            },
            # Balance line (1.0)
            {
                "name": "Balance (1.0)",
                "type": "line",
                "data": [1.0] * len(dates),
                "lineStyle": {"color": "#2ecc71", "width": 2, "type": "dashed"},
                "symbol": "none",
            },
            # LF/HF data
            {
                "name": "LF/HF Ratio",
                "type": "line",
                "data": [[d, v] for d, v in zip(date_labels, lf_hf_values)],
                "symbol": "circle",
                "symbolSize": 7,
                "lineStyle": {"width": 2},
            },
            # EWMA trend
            {
                "name": "7-Day Trend",
                "type": "line",
                "data": lf_hf_ewma,
                "symbol": "none",
                "lineStyle": {"color": "#2c3e50", "width": 2.5},
                "smooth": True,
            },
        ],
        "dataZoom": [{"type": "inside", "start": 0, "end": 100}],
    }


def _build_autonomic_indices_chart(
    dates: List[str],
    stress_index: Optional[List[float]] = None,
    parasympathetic_index: Optional[List[float]] = None,
    hrv_score: Optional[List[float]] = None,
    title: str = "Autonomic Function Indices",
) -> Dict[str, Any]:
    """Build composite autonomic indices chart.
    
    Args:
        dates: Date labels.
        stress_index: Baevsky stress index values.
        parasympathetic_index: PNS index values.
        hrv_score: Composite HRV score.
        title: Chart title.
        
    Returns:
        ECharts option dictionary.
    """
    date_labels = [str(d)[:10] for d in dates]
    series = []
    legend_data = []
    
    if stress_index:
        series.append({
            "name": "Stress Index (Baevsky)",
            "type": "line",
            "data": stress_index,
            "symbol": "circle",
            "symbolSize": 5,
            "itemStyle": {"color": "#e74c3c"},
            "lineStyle": {"color": "#e74c3c", "width": 2},
        })
        legend_data.append("Stress Index (Baevsky)")
        
        # Reference line for elevated stress
        series.append({
            "name": "Elevated Stress Threshold",
            "type": "line",
            "data": [150] * len(dates),
            "lineStyle": {"color": "#e74c3c", "width": 1, "type": "dashed"},
            "symbol": "none",
            "silent": True,
        })
    
    if parasympathetic_index:
        series.append({
            "name": "Parasympathetic Index",
            "type": "line",
            "data": parasympathetic_index,
            "symbol": "diamond",
            "symbolSize": 5,
            "itemStyle": {"color": "#3498db"},
            "lineStyle": {"color": "#3498db", "width": 2},
            "yAxisIndex": 1 if stress_index else 0,
        })
        legend_data.append("Parasympathetic Index")
    
    if hrv_score:
        series.append({
            "name": "HRV Score",
            "type": "line",
            "data": hrv_score,
            "symbol": "triangle",
            "symbolSize": 5,
            "itemStyle": {"color": "#27ae60"},
            "lineStyle": {"color": "#27ae60", "width": 2},
            "yAxisIndex": 1 if stress_index else 0,
        })
        legend_data.append("HRV Score")
    
    y_axes = [
        {
            "type": "value",
            "name": "Stress Index",
            "nameLocation": "middle",
            "nameGap": 50,
            "min": 0,
            "axisLine": {"lineStyle": {"color": "#e74c3c"}},
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        }
    ]
    
    if parasympathetic_index or hrv_score:
        y_axes.append({
            "type": "value",
            "name": "PNS Index / HRV Score",
            "nameLocation": "middle",
            "nameGap": 50,
            "position": "right",
            "axisLine": {"lineStyle": {"color": "#3498db"}},
            "splitLine": {"show": False},
        })
    
    return {
        "title": {
            "text": title,
            "subtext": "Stress Index (Baevsky): >150 indicates elevated sympathetic activation | "
                       "Higher PNS Index indicates greater vagal tone",
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
        },
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
        "legend": {"data": legend_data, "bottom": 5},
        "grid": {
            "left": "10%",
            "right": "10%",
            "top": "15%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": date_labels,
            "axisLabel": {"rotate": 45, "fontSize": 9},
        },
        "yAxis": y_axes,
        "series": series,
        "dataZoom": [{"type": "inside", "start": 0, "end": 100}],
    }


def _build_rmssd_trend_chart(
    dates: List[str],
    values: List[float],
    age: int = 35,
    title: str = "RMSSD Trend with Age-Adjusted Normal Range",
) -> Dict[str, Any]:
    """Build publication-quality RMSSD trend chart with ECharts.
    
    Scientific features:
    - Age-stratified normal range shading (5th-95th percentile)
    - Optimal range shading (25th-75th percentile)
    - EWMA smoothed trend line
    - 7-day rolling average
    - Data points with hover details
    - Clean axis labels with units
    
    Args:
        dates: List of date strings (YYYY-MM-DD or datetime).
        values: List of RMSSD values in ms.
        age: Subject's age for normative ranges.
        title: Chart title.
        
    Returns:
        ECharts option dictionary.
    """
    norms = _get_age_rmssd_norms(age)
    values_arr = np.array(values, dtype=float)
    
    # Calculate smoothed trends
    ewma_values = _ewma_smooth(values_arr, span=7).tolist()
    
    # 7-day rolling average (with min_periods=1)
    ma7_values = []
    for i in range(len(values)):
        start_idx = max(0, i - 6)
        ma7_values.append(float(np.mean(values_arr[start_idx:i + 1])))
    
    # Format dates for display
    date_labels = [str(d)[:10] if len(str(d)) > 10 else str(d) for d in dates]
    
    # Age group label
    age_group = f"{age} years"
    for (age_min, age_max) in AGE_RMSSD_NORMS.keys():
        if age_min <= age <= age_max:
            age_group = f"{age_min}-{age_max} years"
            break
    
    return {
        "title": {
            "text": title,
            "subtext": f"Age group: {age_group} | Reference: Nunan et al. (2010), Shaffer & Ginsberg (2017)",
            "left": "center",
            "textStyle": {"fontSize": 16, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 11, "color": "#7f8c8d"},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "backgroundColor": "rgba(255,255,255,0.95)",
            "borderColor": "#ccc",
            "textStyle": {"color": SCIENTIFIC_COLORS["text"]},
            "formatter": """function(params) {
                var date = params[0].axisValue;
                var result = '<b>' + date + '</b><br/>';
                params.forEach(function(p) {
                    if (p.value !== null && p.value !== undefined) {
                        result += p.marker + ' ' + p.seriesName + ': <b>' + p.value.toFixed(1) + ' ms</b><br/>';
                    }
                });
                return result;
            }""",
        },
        "legend": {
            "data": ["RMSSD", "7-Day MA", "EWMA Trend"],
            "bottom": 10,
            "textStyle": {"fontSize": 11},
        },
        "grid": {
            "left": "8%",
            "right": "5%",
            "top": "18%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": date_labels,
            "name": "Date",
            "nameLocation": "middle",
            "nameGap": 30,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "axisLabel": {"rotate": 45, "fontSize": 10},
            "axisLine": {"lineStyle": {"color": "#bdc3c7"}},
        },
        "yAxis": {
            "type": "value",
            "name": "RMSSD (ms)",
            "nameLocation": "middle",
            "nameGap": 45,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": 0,
            "max": max(max(values) * 1.2, norms["p95"] * 1.1),
            "axisLine": {"lineStyle": {"color": "#bdc3c7"}},
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        },
        "series": [
            # Normal range band (5th-95th percentile)
            {
                "name": "Normal Range (5th-95th %ile)",
                "type": "line",
                "data": [norms["p95"]] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": SCIENTIFIC_COLORS["normal_band"], "opacity": 0.5},
                "stack": "confidence",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "_normal_lower",
                "type": "line",
                "data": [norms["p5"]] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff", "opacity": 1},
                "stack": "confidence",
                "symbol": "none",
                "silent": True,
            },
            # Optimal range band (25th-75th percentile)
            {
                "name": "Optimal Range (25th-75th %ile)",
                "type": "line",
                "data": [norms["p75"]] * len(dates),
                "lineStyle": {"color": "#27ae60", "width": 1, "type": "dashed", "opacity": 0.5},
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "_optimal_lower",
                "type": "line",
                "data": [norms["p25"]] * len(dates),
                "lineStyle": {"color": "#27ae60", "width": 1, "type": "dashed", "opacity": 0.5},
                "symbol": "none",
                "silent": True,
            },
            # Mean reference line
            {
                "name": "Population Mean",
                "type": "line",
                "data": [norms["mean"]] * len(dates),
                "lineStyle": {"color": "#95a5a6", "width": 2, "type": "dotted"},
                "symbol": "none",
                "silent": True,
            },
            # Actual RMSSD data points
            {
                "name": "RMSSD",
                "type": "line",
                "data": values,
                "symbol": "circle",
                "symbolSize": 8,
                "itemStyle": {"color": SCIENTIFIC_COLORS["primary"]},
                "lineStyle": {"color": SCIENTIFIC_COLORS["primary"], "width": 2},
                "emphasis": {"itemStyle": {"borderWidth": 2, "borderColor": "#fff"}},
            },
            # 7-day moving average
            {
                "name": "7-Day MA",
                "type": "line",
                "data": ma7_values,
                "symbol": "none",
                "lineStyle": {"color": SCIENTIFIC_COLORS["smoothed"], "width": 2.5},
                "smooth": True,
            },
            # EWMA trend
            {
                "name": "EWMA Trend",
                "type": "line",
                "data": ewma_values,
                "symbol": "none",
                "lineStyle": {"color": "#e67e22", "width": 2, "type": "dashed"},
                "smooth": True,
            },
        ],
        "dataZoom": [
            {"type": "inside", "start": 0, "end": 100},
            {"type": "slider", "start": 0, "end": 100, "height": 20, "bottom": 35},
        ],
    }


def _build_rr_tachogram_chart(
    time_s: List[float],
    rr_ms: List[float],
    title: str = "RR Interval Tachogram",
) -> Dict[str, Any]:
    """Build publication-quality RR interval tachogram with ECharts.
    
    Scientific features:
    - Continuous line with data points
    - Normal RR range shading (600-1000 ms)
    - Statistical annotations (mean, SD)
    - Pan/zoom for large datasets
    
    Args:
        time_s: Time axis in seconds.
        rr_ms: RR intervals in milliseconds.
        
    Returns:
        ECharts option dictionary.
    """
    rr_arr = np.array(rr_ms)
    mean_rr = float(np.mean(rr_arr))
    sd_rr = float(np.std(rr_arr))
    mean_hr = 60000.0 / mean_rr if mean_rr > 0 else 0
    
    # Downsample for rendering if needed
    max_points = 5000
    if len(time_s) > max_points:
        step = len(time_s) // max_points
        time_s = time_s[::step]
        rr_ms = rr_ms[::step]
    
    return {
        "title": {
            "text": title,
            "subtext": f"Mean: {mean_rr:.1f} ms (SD: {sd_rr:.1f} ms) | HR: {mean_hr:.1f} bpm | N = {len(rr_arr):,}",
            "left": "center",
            "textStyle": {"fontSize": 16, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 11, "color": "#7f8c8d"},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": """function(params) {
                var t = params[0].data[0].toFixed(1);
                var rr = params[0].data[1].toFixed(1);
                var hr = (60000 / rr).toFixed(1);
                return 'Time: <b>' + t + ' s</b><br/>RR: <b>' + rr + ' ms</b><br/>HR: <b>' + hr + ' bpm</b>';
            }""",
        },
        "grid": {
            "left": "8%",
            "right": "5%",
            "top": "15%",
            "bottom": "18%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "value",
            "name": "Time (s)",
            "nameLocation": "middle",
            "nameGap": 30,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "axisLine": {"lineStyle": {"color": "#bdc3c7"}},
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        },
        "yAxis": {
            "type": "value",
            "name": "RR Interval (ms)",
            "nameLocation": "middle",
            "nameGap": 50,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": max(200, min(rr_ms) * 0.85),
            "max": min(2000, max(rr_ms) * 1.15),
            "axisLine": {"lineStyle": {"color": "#bdc3c7"}},
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        },
        "visualMap": {
            "show": False,
            "dimension": 1,
            "pieces": [
                {"lt": 500, "color": SCIENTIFIC_COLORS["alert"]},      # Tachycardia
                {"gte": 500, "lt": 600, "color": SCIENTIFIC_COLORS["warning"]},
                {"gte": 600, "lte": 1000, "color": SCIENTIFIC_COLORS["primary"]},  # Normal
                {"gt": 1000, "lt": 1200, "color": SCIENTIFIC_COLORS["warning"]},
                {"gte": 1200, "color": SCIENTIFIC_COLORS["alert"]},   # Bradycardia
            ],
        },
        "series": [
            {
                "name": "RR Interval",
                "type": "line",
                "data": [[t, rr] for t, rr in zip(time_s, rr_ms)],
                "symbol": "none",
                "lineStyle": {"width": 1.5},
                "sampling": "lttb",
                "large": True,
                "largeThreshold": 3000,
            },
            # Mean reference line
            {
                "name": "Mean",
                "type": "line",
                "data": [[time_s[0], mean_rr], [time_s[-1], mean_rr]],
                "symbol": "none",
                "lineStyle": {"color": "#27ae60", "width": 2, "type": "dashed"},
            },
            # ±1 SD bands
            {
                "name": "+1 SD",
                "type": "line",
                "data": [[time_s[0], mean_rr + sd_rr], [time_s[-1], mean_rr + sd_rr]],
                "symbol": "none",
                "lineStyle": {"color": "#95a5a6", "width": 1, "type": "dotted"},
            },
            {
                "name": "-1 SD",
                "type": "line",
                "data": [[time_s[0], mean_rr - sd_rr], [time_s[-1], mean_rr - sd_rr]],
                "symbol": "none",
                "lineStyle": {"color": "#95a5a6", "width": 1, "type": "dotted"},
            },
        ],
        "dataZoom": [
            {"type": "inside", "xAxisIndex": 0, "start": 0, "end": 100},
            {"type": "slider", "xAxisIndex": 0, "start": 0, "end": 100, "height": 20, "bottom": 25},
        ],
    }


def _build_psd_chart(
    freqs: List[float],
    psd: List[float],
    title: str = "Power Spectral Density",
) -> Dict[str, Any]:
    """Build publication-quality PSD chart with frequency band annotations.
    
    Scientific features:
    - VLF, LF, HF band shading with labels
    - Logarithmic Y-axis option
    - Peak frequency annotation
    - Band power values in legend
    
    Args:
        freqs: Frequency axis in Hz.
        psd: Power spectral density values.
        
    Returns:
        ECharts option dictionary.
    """
    freqs_arr = np.array(freqs)
    psd_arr = np.array(psd)
    
    # Calculate band powers
    vlf_mask = (freqs_arr >= 0.003) & (freqs_arr < 0.04)
    lf_mask = (freqs_arr >= 0.04) & (freqs_arr < 0.15)
    hf_mask = (freqs_arr >= 0.15) & (freqs_arr <= 0.4)
    
    vlf_power = float(np.trapz(psd_arr[vlf_mask], freqs_arr[vlf_mask])) if np.any(vlf_mask) else 0
    lf_power = float(np.trapz(psd_arr[lf_mask], freqs_arr[lf_mask])) if np.any(lf_mask) else 0
    hf_power = float(np.trapz(psd_arr[hf_mask], freqs_arr[hf_mask])) if np.any(hf_mask) else 0
    total_power = vlf_power + lf_power + hf_power
    
    lf_hf_ratio = lf_power / hf_power if hf_power > 0 else 0
    
    # Find peak frequency in LF-HF range
    lf_hf_combined = (freqs_arr >= 0.04) & (freqs_arr <= 0.4)
    if np.any(lf_hf_combined):
        peak_idx = np.argmax(psd_arr[lf_hf_combined])
        peak_freq = freqs_arr[lf_hf_combined][peak_idx]
    else:
        peak_freq = 0.1
    
    # Limit frequency range for display
    display_mask = freqs_arr <= 0.5
    freqs_display = freqs_arr[display_mask].tolist()
    psd_display = psd_arr[display_mask].tolist()
    
    return {
        "title": {
            "text": title,
            "subtext": f"LF/HF: {lf_hf_ratio:.2f} | Peak: {peak_freq:.3f} Hz | Total Power: {total_power:.0f} ms²",
            "left": "center",
            "textStyle": {"fontSize": 16, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 11, "color": "#7f8c8d"},
        },
        "tooltip": {
            "trigger": "axis",
            "formatter": """function(params) {
                var f = params[0].data[0].toFixed(3);
                var p = params[0].data[1].toFixed(1);
                return 'Frequency: <b>' + f + ' Hz</b><br/>Power: <b>' + p + ' ms²/Hz</b>';
            }""",
        },
        "legend": {
            "data": [
                f"VLF ({vlf_power:.0f} ms²)",
                f"LF ({lf_power:.0f} ms²)", 
                f"HF ({hf_power:.0f} ms²)",
            ],
            "bottom": 10,
            "textStyle": {"fontSize": 11},
        },
        "grid": {
            "left": "10%",
            "right": "5%",
            "top": "15%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "value",
            "name": "Frequency (Hz)",
            "nameLocation": "middle",
            "nameGap": 30,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": 0,
            "max": 0.5,
            "axisLine": {"lineStyle": {"color": "#bdc3c7"}},
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        },
        "yAxis": {
            "type": "value",
            "name": "PSD (ms²/Hz)",
            "nameLocation": "middle",
            "nameGap": 55,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "axisLine": {"lineStyle": {"color": "#bdc3c7"}},
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        },
        "series": [
            # VLF band
            {
                "name": f"VLF ({vlf_power:.0f} ms²)",
                "type": "line",
                "data": [[f, p] for f, p in zip(freqs_display, psd_display) if 0.003 <= f < 0.04],
                "areaStyle": {"color": SCIENTIFIC_COLORS["vlf_band"], "opacity": 0.4},
                "lineStyle": {"color": SCIENTIFIC_COLORS["vlf_band"], "width": 0},
                "symbol": "none",
            },
            # LF band
            {
                "name": f"LF ({lf_power:.0f} ms²)",
                "type": "line",
                "data": [[f, p] for f, p in zip(freqs_display, psd_display) if 0.04 <= f < 0.15],
                "areaStyle": {"color": SCIENTIFIC_COLORS["lf_band"], "opacity": 0.4},
                "lineStyle": {"color": SCIENTIFIC_COLORS["lf_band"], "width": 0},
                "symbol": "none",
            },
            # HF band
            {
                "name": f"HF ({hf_power:.0f} ms²)",
                "type": "line",
                "data": [[f, p] for f, p in zip(freqs_display, psd_display) if 0.15 <= f <= 0.4],
                "areaStyle": {"color": SCIENTIFIC_COLORS["hf_band"], "opacity": 0.4},
                "lineStyle": {"color": SCIENTIFIC_COLORS["hf_band"], "width": 0},
                "symbol": "none",
            },
            # Full PSD line
            {
                "name": "PSD",
                "type": "line",
                "data": [[f, p] for f, p in zip(freqs_display, psd_display)],
                "lineStyle": {"color": SCIENTIFIC_COLORS["text"], "width": 2},
                "symbol": "none",
                "smooth": True,
                "z": 10,
            },
        ],
        "markLine": {
            "silent": True,
            "data": [
                {"xAxis": 0.04, "label": {"show": False}, "lineStyle": {"color": "#95a5a6", "type": "dashed"}},
                {"xAxis": 0.15, "label": {"show": False}, "lineStyle": {"color": "#95a5a6", "type": "dashed"}},
                {"xAxis": 0.4, "label": {"show": False}, "lineStyle": {"color": "#95a5a6", "type": "dashed"}},
            ],
        },
    }


def _build_rr_histogram_chart(
    rr_ms: List[float],
    bins: int = 30,
    title: str = "RR Interval Distribution",
) -> Dict[str, Any]:
    """Build publication-quality RR interval histogram with normal fit overlay.
    
    Scientific features:
    - Kernel density estimate overlay
    - Normal distribution fit
    - Statistical annotations (mean, SD, skewness, kurtosis)
    - Percentile markers
    
    Args:
        rr_ms: RR intervals in milliseconds.
        bins: Number of histogram bins.
        
    Returns:
        ECharts option dictionary.
    """
    rr_arr = np.array(rr_ms)
    mean_rr = float(np.mean(rr_arr))
    sd_rr = float(np.std(rr_arr))
    median_rr = float(np.median(rr_arr))
    
    # Calculate skewness and kurtosis
    try:
        from scipy.stats import skew, kurtosis
        skewness = float(skew(rr_arr))
        kurt = float(kurtosis(rr_arr))
    except ImportError:
        skewness = 0.0
        kurt = 0.0
    
    # Create histogram
    hist_vals, bin_edges = np.histogram(rr_arr, bins=bins)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    bin_width = bin_edges[1] - bin_edges[0]
    
    # Normalize histogram for density
    hist_density = hist_vals / (len(rr_arr) * bin_width)
    
    # Create normal distribution overlay
    x_norm = np.linspace(bin_edges[0], bin_edges[-1], 100)
    y_norm = (1 / (sd_rr * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x_norm - mean_rr) / sd_rr) ** 2)
    
    return {
        "title": {
            "text": title,
            "subtext": f"Mean: {mean_rr:.1f} ms | SD: {sd_rr:.1f} ms | Median: {median_rr:.1f} ms | Skew: {skewness:.2f} | Kurt: {kurt:.2f}",
            "left": "center",
            "textStyle": {"fontSize": 16, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 11, "color": "#7f8c8d"},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
        },
        "legend": {
            "data": ["Observed", "Normal Fit"],
            "bottom": 10,
            "textStyle": {"fontSize": 11},
        },
        "grid": {
            "left": "10%",
            "right": "5%",
            "top": "15%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": [f"{int(bc)}" for bc in bin_centers],
            "name": "RR Interval (ms)",
            "nameLocation": "middle",
            "nameGap": 30,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "axisLine": {"lineStyle": {"color": "#bdc3c7"}},
            "axisLabel": {"rotate": 45, "fontSize": 9},
        },
        "yAxis": {
            "type": "value",
            "name": "Frequency",
            "nameLocation": "middle",
            "nameGap": 45,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "axisLine": {"lineStyle": {"color": "#bdc3c7"}},
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        },
        "series": [
            # Histogram bars
            {
                "name": "Observed",
                "type": "bar",
                "data": hist_vals.tolist(),
                "itemStyle": {"color": SCIENTIFIC_COLORS["primary"], "opacity": 0.7},
                "barWidth": "90%",
            },
            # Normal distribution overlay (scaled to histogram)
            {
                "name": "Normal Fit",
                "type": "line",
                "data": (y_norm * len(rr_arr) * bin_width).tolist(),
                "smooth": True,
                "symbol": "none",
                "lineStyle": {"color": SCIENTIFIC_COLORS["alert"], "width": 2, "type": "dashed"},
            },
        ],
        "markLine": {
            "silent": True,
            "symbol": "none",
            "data": [
                {
                    "xAxis": int(np.searchsorted(bin_centers, mean_rr)),
                    "label": {"formatter": "Mean", "position": "end"},
                    "lineStyle": {"color": "#27ae60", "width": 2},
                },
                {
                    "xAxis": int(np.searchsorted(bin_centers, median_rr)),
                    "label": {"formatter": "Median", "position": "end"},
                    "lineStyle": {"color": "#e67e22", "width": 2, "type": "dashed"},
                },
            ],
        },
    }


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
    """Guard for session readiness - always returns True.
    
    Previously this returned False on first call to delay rendering,
    but that caused blank UI on first render. Now it's a no-op that
    always returns True since session state is ready by the time
    render functions are called.
    """
    # Always ready - Streamlit session is initialized before render
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


# =============================================================================
# PUBLICATION-QUALITY WEARABLE MONITORING CHARTS
# =============================================================================


def _build_activity_movement_chart(
    dates: List[str],
    steps: Optional[List[float]] = None,
    distance_km: Optional[List[float]] = None,
    calories: Optional[List[float]] = None,
    title: str = "Activity & Movement Trends",
) -> Dict[str, Any]:
    """Build publication-quality activity/movement chart with physiological context.
    
    Guidelines: WHO recommends 8,000-10,000 steps/day for adults.
    Reference: Tudor-Locke C et al. (2011). Int J Behav Nutr Phys Act, 8:79.
    
    Returns:
        ECharts option dictionary.
    """
    date_labels = [str(d)[:10] for d in dates]
    series = []
    legend_data = []
    y_axes = []
    
    # Steps axis (primary)
    if steps and any(v is not None for v in steps):
        legend_data.append("Steps")
        steps_clean = [v if v is not None else None for v in steps]
        steps_ewma = _ewma_smooth(np.array([v if v else 0 for v in steps], dtype=float), span=7).tolist()
        
        series.extend([
            # WHO target zone (8k-10k)
            {
                "name": "Optimal Zone",
                "type": "line",
                "data": [10000] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(46, 204, 113, 0.12)"},
                "stack": "steps_zone",
                "symbol": "none",
                "silent": True,
                "yAxisIndex": 0,
            },
            {
                "name": "_zone_base",
                "type": "line",
                "data": [8000] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "steps_zone",
                "symbol": "none",
                "silent": True,
                "yAxisIndex": 0,
            },
            # 10k target line
            {
                "name": "10k Target",
                "type": "line",
                "data": [10000] * len(dates),
                "lineStyle": {"color": "#27ae60", "width": 2, "type": "dashed"},
                "symbol": "none",
                "yAxisIndex": 0,
            },
            # Steps data
            {
                "name": "Steps",
                "type": "bar",
                "data": steps_clean,
                "itemStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#3498db"},
                            {"offset": 1, "color": "#2980b9"},
                        ],
                    },
                    "borderRadius": [4, 4, 0, 0],
                },
                "barMaxWidth": 25,
                "yAxisIndex": 0,
            },
            {
                "name": "7-Day Trend",
                "type": "line",
                "data": steps_ewma,
                "symbol": "none",
                "lineStyle": {"color": "#2c3e50", "width": 2.5},
                "smooth": True,
                "yAxisIndex": 0,
            },
        ])
        legend_data.extend(["7-Day Trend", "10k Target"])
        
        y_axes.append({
            "type": "value",
            "name": "Steps",
            "nameLocation": "middle",
            "nameGap": 55,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": 0,
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        })
    
    # Calories axis (secondary)
    if calories and any(v is not None for v in calories):
        legend_data.append("Calories")
        cals_clean = [v if v is not None else None for v in calories]
        
        series.append({
            "name": "Calories",
            "type": "line",
            "data": cals_clean,
            "symbol": "circle",
            "symbolSize": 6,
            "lineStyle": {"color": "#e74c3c", "width": 2},
            "itemStyle": {"color": "#e74c3c"},
            "yAxisIndex": 1 if steps else 0,
        })
        
        if steps:
            y_axes.append({
                "type": "value",
                "name": "Calories (kcal)",
                "nameLocation": "middle",
                "nameGap": 50,
                "position": "right",
                "axisLine": {"lineStyle": {"color": "#e74c3c"}},
                "splitLine": {"show": False},
            })
        else:
            y_axes.append({
                "type": "value",
                "name": "Calories (kcal)",
                "nameLocation": "middle",
                "nameGap": 50,
                "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
            })
    
    return {
        "title": {
            "text": title,
            "subtext": "WHO Guidelines: 8,000-10,000 steps/day for optimal health | "
                       "Shaded zone indicates target range",
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
        },
        "legend": {"data": legend_data, "bottom": 5, "textStyle": {"fontSize": 10}},
        "grid": {
            "left": "10%",
            "right": "10%" if len(y_axes) > 1 else "5%",
            "top": "18%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": date_labels,
            "axisLabel": {"rotate": 45, "fontSize": 9},
        },
        "yAxis": y_axes if y_axes else [{"type": "value"}],
        "series": series,
        "dataZoom": [{"type": "inside", "start": 0, "end": 100}],
    }


def _build_hr_stress_chart(
    dates: List[str],
    avg_hr: Optional[List[float]] = None,
    resting_hr: Optional[List[float]] = None,
    stress_score: Optional[List[float]] = None,
    title: str = "Heart Rate & Stress Trends",
) -> Dict[str, Any]:
    """Build publication-quality HR and stress chart with dynamic axis scaling.
    
    Resting HR <60 bpm indicates athletic conditioning.
    Garmin stress score: 0-25 (rest), 26-50 (low), 51-75 (medium), 76-100 (high).
    """
    date_labels = [str(d)[:10] for d in dates]
    series = []
    legend_data = []
    y_axes = []
    
    # HR data (primary axis)
    has_hr = (avg_hr and any(v is not None for v in avg_hr)) or \
             (resting_hr and any(v is not None for v in resting_hr))
    
    if has_hr:
        # Calculate dynamic HR axis bounds to fit all data
        hr_min, hr_max = _auto_axis_bounds(
            avg_hr, resting_hr,
            padding_pct=0.15,
            min_floor=30,  # HR won't go below 30 in normal circumstances
        )
        # Ensure reference zones (60, 80, 100) are visible if relevant
        hr_max = max(hr_max, 105)  # Always show elevated zone marker
        
        # HR zones (use dynamic max)
        series.extend([
            {
                "name": "Elevated HR Zone",
                "type": "line",
                "data": [hr_max] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(231, 76, 60, 0.1)"},
                "stack": "hr_zone_high",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "_hr_zone_mid",
                "type": "line",
                "data": [80] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "hr_zone_high",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "Athletic Zone",
                "type": "line",
                "data": [60] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(46, 204, 113, 0.1)"},
                "symbol": "none",
                "silent": True,
            },
        ])
        
        if resting_hr and any(v is not None for v in resting_hr):
            legend_data.append("Resting HR")
            rhr_clean = [v if v is not None else None for v in resting_hr]
            rhr_ewma = _ewma_smooth(np.array([v if v else 60 for v in resting_hr], dtype=float), span=7).tolist()
            series.extend([
                {
                    "name": "Resting HR",
                    "type": "line",
                    "data": rhr_clean,
                    "symbol": "circle",
                    "symbolSize": 6,
                    "lineStyle": {"color": "#e74c3c", "width": 2},
                    "itemStyle": {"color": "#e74c3c"},
                },
                {
                    "name": "RHR Trend",
                    "type": "line",
                    "data": rhr_ewma,
                    "symbol": "none",
                    "lineStyle": {"color": "#c0392b", "width": 2.5},
                    "smooth": True,
                },
            ])
            legend_data.append("RHR Trend")
        
        if avg_hr and any(v is not None for v in avg_hr):
            legend_data.append("Avg HR")
            ahr_clean = [v if v is not None else None for v in avg_hr]
            series.append({
                "name": "Avg HR",
                "type": "line",
                "data": ahr_clean,
                "symbol": "diamond",
                "symbolSize": 5,
                "lineStyle": {"color": "#9b59b6", "width": 1.5, "type": "dashed"},
                "itemStyle": {"color": "#9b59b6"},
            })
        
        y_axes.append({
            "type": "value",
            "name": "Heart Rate (bpm)",
            "nameLocation": "middle",
            "nameGap": 50,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": hr_min,
            "max": hr_max,
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        })
    
    # Stress score (secondary axis)
    if stress_score and any(v is not None for v in stress_score):
        legend_data.append("Stress Score")
        stress_clean = [v if v is not None else None for v in stress_score]
        stress_ewma = _ewma_smooth(np.array([v if v else 25 for v in stress_score], dtype=float), span=7).tolist()
        
        series.extend([
            {
                "name": "Stress Score",
                "type": "bar",
                "data": stress_clean,
                "itemStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#f39c12"},
                            {"offset": 1, "color": "#e67e22"},
                        ],
                    },
                    "borderRadius": [2, 2, 0, 0],
                },
                "barMaxWidth": 15,
                "yAxisIndex": 1 if has_hr else 0,
            },
            {
                "name": "Stress Trend",
                "type": "line",
                "data": stress_ewma,
                "symbol": "none",
                "lineStyle": {"color": "#d35400", "width": 2},
                "smooth": True,
                "yAxisIndex": 1 if has_hr else 0,
            },
        ])
        legend_data.append("Stress Trend")
        
        y_axes.append({
            "type": "value",
            "name": "Stress Score",
            "nameLocation": "middle",
            "nameGap": 45,
            "position": "right" if has_hr else "left",
            "min": 0,
            "max": 100,
            "axisLine": {"lineStyle": {"color": "#f39c12"}},
            "splitLine": {"show": False},
        })
    
    return {
        "title": {
            "text": title,
            "subtext": "Resting HR <60 bpm = athletic | Stress: 0-25 rest, 26-50 low, 51-75 med, 76-100 high",
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
        },
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
        "legend": {"data": legend_data, "bottom": 5, "textStyle": {"fontSize": 10}},
        "grid": {
            "left": "10%",
            "right": "10%",
            "top": "18%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": date_labels,
            "axisLabel": {"rotate": 45, "fontSize": 9},
        },
        "yAxis": y_axes if y_axes else [{"type": "value"}],
        "series": series,
        "dataZoom": [{"type": "inside", "start": 0, "end": 100}],
    }


def _build_sleep_recovery_chart(
    dates: List[str],
    sleep_score: Optional[List[float]] = None,
    sleep_efficiency: Optional[List[float]] = None,
    sleep_duration: Optional[List[float]] = None,
    title: str = "Sleep & Recovery Trends",
) -> Dict[str, Any]:
    """Build publication-quality sleep chart with clinical thresholds.
    
    References:
    - Sleep efficiency ≥85% is clinically normal (Ohayon et al., 2017).
    - 7-9 hours sleep recommended for adults (NSF, 2015).
    """
    date_labels = [str(d)[:10] for d in dates]
    series = []
    legend_data = []
    y_axes = []
    
    # Sleep score/efficiency (primary axis - percentage)
    has_pct = (sleep_score and any(v is not None for v in sleep_score)) or \
              (sleep_efficiency and any(v is not None for v in sleep_efficiency))
    
    if has_pct:
        # Good sleep zone (70-100)
        series.extend([
            {
                "name": "Good Sleep Zone",
                "type": "line",
                "data": [100] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(155, 89, 182, 0.1)"},
                "stack": "sleep_zone",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "_sleep_zone_base",
                "type": "line",
                "data": [70] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "sleep_zone",
                "symbol": "none",
                "silent": True,
            },
            # 85% efficiency threshold
            {
                "name": "85% Threshold",
                "type": "line",
                "data": [85] * len(dates),
                "lineStyle": {"color": "#9b59b6", "width": 2, "type": "dashed"},
                "symbol": "none",
            },
        ])
        legend_data.append("85% Threshold")
        
        if sleep_score and any(v is not None for v in sleep_score):
            legend_data.append("Sleep Score")
            score_clean = [v if v is not None else None for v in sleep_score]
            series.append({
                "name": "Sleep Score",
                "type": "line",
                "data": score_clean,
                "symbol": "circle",
                "symbolSize": 7,
                "lineStyle": {"color": "#8e44ad", "width": 2.5},
                "itemStyle": {"color": "#8e44ad"},
            })
        
        if sleep_efficiency and any(v is not None for v in sleep_efficiency):
            legend_data.append("Sleep Efficiency")
            eff_clean = [v if v is not None else None for v in sleep_efficiency]
            series.append({
                "name": "Sleep Efficiency",
                "type": "line",
                "data": eff_clean,
                "symbol": "triangle",
                "symbolSize": 6,
                "lineStyle": {"color": "#1abc9c", "width": 2},
                "itemStyle": {"color": "#1abc9c"},
            })
        
        y_axes.append({
            "type": "value",
            "name": "Score / Efficiency (%)",
            "nameLocation": "middle",
            "nameGap": 50,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": 0,
            "max": 100,
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        })
    
    # Sleep duration (secondary axis - hours)
    if sleep_duration and any(v is not None for v in sleep_duration):
        legend_data.append("Sleep Duration")
        dur_clean = [v if v is not None else None for v in sleep_duration]
        
        series.extend([
            # Optimal sleep band (7-9 hours)
            {
                "name": "Optimal (7-9h)",
                "type": "line",
                "data": [9] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(52, 152, 219, 0.15)"},
                "stack": "dur_zone",
                "symbol": "none",
                "silent": True,
                "yAxisIndex": 1 if has_pct else 0,
            },
            {
                "name": "_dur_zone_base",
                "type": "line",
                "data": [7] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "dur_zone",
                "symbol": "none",
                "silent": True,
                "yAxisIndex": 1 if has_pct else 0,
            },
            {
                "name": "Sleep Duration",
                "type": "bar",
                "data": dur_clean,
                "itemStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#3498db"},
                            {"offset": 1, "color": "#2980b9"},
                        ],
                    },
                    "borderRadius": [3, 3, 0, 0],
                },
                "barMaxWidth": 20,
                "yAxisIndex": 1 if has_pct else 0,
            },
        ])
        legend_data.append("Optimal (7-9h)")
        
        y_axes.append({
            "type": "value",
            "name": "Sleep Duration (h)",
            "nameLocation": "middle",
            "nameGap": 40,
            "position": "right" if has_pct else "left",
            "min": 0,
            "max": 12,
            "axisLine": {"lineStyle": {"color": "#3498db"}},
            "splitLine": {"show": False},
        })
    
    return {
        "title": {
            "text": title,
            "subtext": "NSF Guidelines: 7-9h optimal for adults | Sleep efficiency ≥85% is clinically normal",
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
        },
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
        "legend": {"data": legend_data, "bottom": 5, "textStyle": {"fontSize": 10}},
        "grid": {
            "left": "10%",
            "right": "10%",
            "top": "18%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": date_labels,
            "axisLabel": {"rotate": 45, "fontSize": 9},
        },
        "yAxis": y_axes if y_axes else [{"type": "value"}],
        "series": series,
        "dataZoom": [{"type": "inside", "start": 0, "end": 100}],
    }


def _build_respiration_spo2_chart(
    dates: List[str],
    spo2: Optional[List[float]] = None,
    resp_awake: Optional[List[float]] = None,
    resp_sleep: Optional[List[float]] = None,
    title: str = "Respiration & SpO₂ Trends",
) -> Dict[str, Any]:
    """Build publication-quality respiration/SpO2 chart with dynamic axis scaling.
    
    References:
    - Normal SpO₂: 95-100% (WHO, 2022).
    - Normal adult respiratory rate: 12-20 breaths/min (awake).
    - Sleep respiratory rate typically lower: 10-16 breaths/min.
    """
    date_labels = [str(d)[:10] for d in dates]
    series = []
    legend_data = []
    y_axes = []
    
    # SpO2 (primary axis)
    if spo2 and any(v is not None for v in spo2):
        legend_data.append("SpO₂")
        spo2_clean = [v if v is not None else None for v in spo2]
        
        # Dynamic SpO2 axis bounds - ensure 95% threshold and data are visible
        spo2_min, spo2_max = _auto_axis_bounds(
            spo2,
            padding_pct=0.05,
            min_floor=80,   # SpO2 below 80 is severe hypoxemia
            max_ceil=100,   # SpO2 can't exceed 100%
        )
        # Ensure 95% threshold is visible
        spo2_min = min(spo2_min, 93)
        
        series.extend([
            # Normal SpO2 zone (95-100)
            {
                "name": "Normal SpO₂",
                "type": "line",
                "data": [100] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(46, 204, 113, 0.15)"},
                "stack": "spo2_zone",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "_spo2_zone_base",
                "type": "line",
                "data": [95] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "spo2_zone",
                "symbol": "none",
                "silent": True,
            },
            # 95% threshold
            {
                "name": "95% Threshold",
                "type": "line",
                "data": [95] * len(dates),
                "lineStyle": {"color": "#e74c3c", "width": 2, "type": "dashed"},
                "symbol": "none",
            },
            # SpO2 data
            {
                "name": "SpO₂",
                "type": "line",
                "data": spo2_clean,
                "symbol": "circle",
                "symbolSize": 8,
                "lineStyle": {"color": "#27ae60", "width": 2.5},
                "itemStyle": {"color": "#27ae60"},
            },
        ])
        legend_data.append("95% Threshold")
        
        y_axes.append({
            "type": "value",
            "name": "SpO₂ (%)",
            "nameLocation": "middle",
            "nameGap": 45,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": spo2_min,
            "max": spo2_max,
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        })
    
    # Respiration rates (secondary axis)
    has_resp = (resp_awake and any(v is not None for v in resp_awake)) or \
               (resp_sleep and any(v is not None for v in resp_sleep))
    
    if has_resp:
        # Dynamic respiration axis bounds
        resp_min, resp_max = _auto_axis_bounds(
            resp_awake, resp_sleep,
            padding_pct=0.15,
            min_floor=5,   # Respiratory rate below 5 is critical
        )
        # Ensure normal zone (12-20) markers are visible
        resp_min = min(resp_min, 10)
        resp_max = max(resp_max, 22)
        
        # Normal respiration zone (12-20)
        series.extend([
            {
                "name": "Normal Resp Zone",
                "type": "line",
                "data": [20] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(52, 152, 219, 0.1)"},
                "stack": "resp_zone",
                "symbol": "none",
                "silent": True,
                "yAxisIndex": 1 if spo2 else 0,
            },
            {
                "name": "_resp_zone_base",
                "type": "line",
                "data": [12] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "resp_zone",
                "symbol": "none",
                "silent": True,
                "yAxisIndex": 1 if spo2 else 0,
            },
        ])
        
        if resp_awake and any(v is not None for v in resp_awake):
            legend_data.append("Resp (Awake)")
            resp_a_clean = [v if v is not None else None for v in resp_awake]
            series.append({
                "name": "Resp (Awake)",
                "type": "line",
                "data": resp_a_clean,
                "symbol": "triangle",
                "symbolSize": 6,
                "lineStyle": {"color": "#3498db", "width": 2},
                "itemStyle": {"color": "#3498db"},
                "yAxisIndex": 1 if spo2 else 0,
            })
        
        if resp_sleep and any(v is not None for v in resp_sleep):
            legend_data.append("Resp (Sleep)")
            resp_s_clean = [v if v is not None else None for v in resp_sleep]
            series.append({
                "name": "Resp (Sleep)",
                "type": "line",
                "data": resp_s_clean,
                "symbol": "diamond",
                "symbolSize": 6,
                "lineStyle": {"color": "#9b59b6", "width": 2},
                "itemStyle": {"color": "#9b59b6"},
                "yAxisIndex": 1 if spo2 else 0,
            })
        
        y_axes.append({
            "type": "value",
            "name": "Respiration (rpm)",
            "nameLocation": "middle",
            "nameGap": 40,
            "position": "right" if spo2 else "left",
            "min": resp_min,
            "max": resp_max,
            "axisLine": {"lineStyle": {"color": "#3498db"}},
            "splitLine": {"show": False},
        })
    
    return {
        "title": {
            "text": title,
            "subtext": "WHO: SpO₂ ≥95% normal | Adult respiratory rate: 12-20 rpm (awake), 10-16 rpm (sleep)",
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
        },
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
        "legend": {"data": legend_data, "bottom": 5, "textStyle": {"fontSize": 10}},
        "grid": {
            "left": "10%",
            "right": "10%",
            "top": "18%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": date_labels,
            "axisLabel": {"rotate": 45, "fontSize": 9},
        },
        "yAxis": y_axes if y_axes else [{"type": "value"}],
        "series": series,
        "dataZoom": [{"type": "inside", "start": 0, "end": 100}],
    }


def _build_body_battery_chart(
    dates: List[str],
    bb_avg: Optional[List[float]] = None,
    bb_charge: Optional[List[float]] = None,
    bb_drain: Optional[List[float]] = None,
    title: str = "Body Battery Trends",
) -> Dict[str, Any]:
    """Build publication-quality Body Battery chart with physiological zones.
    
    Garmin Body Battery: 0-100 scale based on HRV, stress, sleep, and activity.
    - 75-100: High energy reserve
    - 50-74: Moderate energy
    - 25-49: Low energy
    - 0-24: Very low (rest recommended)
    """
    date_labels = [str(d)[:10] for d in dates]
    series = []
    legend_data = []
    
    # Energy zones
    series.extend([
        # High energy zone (75-100)
        {
            "name": "High Energy",
            "type": "line",
            "data": [100] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "rgba(46, 204, 113, 0.15)"},
            "stack": "bb_zone_high",
            "symbol": "none",
            "silent": True,
        },
        {
            "name": "_bb_high_base",
            "type": "line",
            "data": [75] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "#fff"},
            "stack": "bb_zone_high",
            "symbol": "none",
            "silent": True,
        },
        # Moderate energy zone (50-74)
        {
            "name": "Moderate Energy",
            "type": "line",
            "data": [74] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "rgba(52, 152, 219, 0.12)"},
            "stack": "bb_zone_mod",
            "symbol": "none",
            "silent": True,
        },
        {
            "name": "_bb_mod_base",
            "type": "line",
            "data": [50] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "#fff"},
            "stack": "bb_zone_mod",
            "symbol": "none",
            "silent": True,
        },
        # Low energy zone (25-49)
        {
            "name": "Low Energy",
            "type": "line",
            "data": [49] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "rgba(243, 156, 18, 0.12)"},
            "stack": "bb_zone_low",
            "symbol": "none",
            "silent": True,
        },
        {
            "name": "_bb_low_base",
            "type": "line",
            "data": [25] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "#fff"},
            "stack": "bb_zone_low",
            "symbol": "none",
            "silent": True,
        },
        # Critical zone marker
        {
            "name": "25% Threshold",
            "type": "line",
            "data": [25] * len(dates),
            "lineStyle": {"color": "#e74c3c", "width": 2, "type": "dashed"},
            "symbol": "none",
        },
    ])
    legend_data.append("25% Threshold")
    
    # Body Battery average
    if bb_avg and any(v is not None for v in bb_avg):
        legend_data.append("Body Battery")
        bb_clean = [v if v is not None else None for v in bb_avg]
        bb_ewma = _ewma_smooth(np.array([v if v else 50 for v in bb_avg], dtype=float), span=7).tolist()
        
        series.extend([
            {
                "name": "Body Battery",
                "type": "line",
                "data": bb_clean,
                "symbol": "circle",
                "symbolSize": 8,
                "lineStyle": {"color": "#27ae60", "width": 2.5},
                "itemStyle": {"color": "#27ae60"},
            },
            {
                "name": "7-Day Trend",
                "type": "line",
                "data": bb_ewma,
                "symbol": "none",
                "lineStyle": {"color": "#2c3e50", "width": 3},
                "smooth": True,
            },
        ])
        legend_data.append("7-Day Trend")
    
    # Charge/Drain as bars (secondary visualization)
    if bb_charge and any(v is not None for v in bb_charge):
        legend_data.append("Charged (+)")
        charge_clean = [v if v is not None else None for v in bb_charge]
        series.append({
            "name": "Charged (+)",
            "type": "bar",
            "data": charge_clean,
            "itemStyle": {"color": "#2ecc71", "borderRadius": [2, 2, 0, 0]},
            "barMaxWidth": 12,
            "yAxisIndex": 1,
        })
    
    if bb_drain and any(v is not None for v in bb_drain):
        legend_data.append("Drained (−)")
        # Drain is positive number, show as negative for visual effect
        drain_clean = [(-v if v is not None else None) for v in bb_drain]
        series.append({
            "name": "Drained (−)",
            "type": "bar",
            "data": drain_clean,
            "itemStyle": {"color": "#e74c3c", "borderRadius": [0, 0, 2, 2]},
            "barMaxWidth": 12,
            "yAxisIndex": 1,
        })
    
    y_axes = [
        {
            "type": "value",
            "name": "Body Battery",
            "nameLocation": "middle",
            "nameGap": 45,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": 0,
            "max": 100,
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        },
    ]
    
    if (bb_charge and any(v is not None for v in bb_charge)) or \
       (bb_drain and any(v is not None for v in bb_drain)):
        y_axes.append({
            "type": "value",
            "name": "Charge/Drain",
            "nameLocation": "middle",
            "nameGap": 40,
            "position": "right",
            "axisLine": {"lineStyle": {"color": "#95a5a6"}},
            "splitLine": {"show": False},
        })
    
    return {
        "title": {
            "text": title,
            "subtext": "Energy Zones: 75-100 High | 50-74 Moderate | 25-49 Low | <25 Rest Recommended",
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
        },
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
        "legend": {"data": legend_data, "bottom": 5, "textStyle": {"fontSize": 10}},
        "grid": {
            "left": "10%",
            "right": "10%",
            "top": "18%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": date_labels,
            "axisLabel": {"rotate": 45, "fontSize": 9},
        },
        "yAxis": y_axes,
        "series": series,
        "dataZoom": [{"type": "inside", "start": 0, "end": 100}],
    }


def _build_stress_pns_chart(
    dates: List[str],
    stress_index: Optional[List[float]] = None,
    pns_index: Optional[List[float]] = None,
    title: str = "HRV Stress & Parasympathetic Index Trends",
) -> Dict[str, Any]:
    """Build publication-quality Stress Index and PNS chart with dynamic axis scaling.
    
    Stress Index (Baevsky): Reflects sympathetic activation.
    - <50: Low stress (parasympathetic dominant)
    - 50-100: Moderate stress (balanced ANS)
    - 100-150: Elevated stress (sympathetic activation)
    - >150: High stress (significant sympathetic dominance)
    
    Parasympathetic Index (PNS): Higher values indicate greater vagal tone.
    - >1.0: High vagal activity (good recovery capacity)
    - 0.0-1.0: Normal vagal tone
    - <0.0: Reduced vagal activity (stress/fatigue)
    
    References:
    - Baevsky RM et al. (2002). J Am Coll Cardiol.
    - Shaffer & Ginsberg (2017). Front Public Health.
    """
    date_labels = [str(d)[:10] for d in dates]
    series = []
    legend_data = []
    y_axes = []
    
    # Stress Index (primary axis)
    if stress_index and any(v is not None for v in stress_index):
        # Dynamic axis bounds for stress index
        stress_min, stress_max = _auto_axis_bounds(
            stress_index,
            padding_pct=0.15,
            min_floor=0,
        )
        # Ensure stress threshold zones are visible
        stress_max = max(stress_max, 200)
        
        legend_data.append("Stress Index")
        stress_clean = [v if v is not None else None for v in stress_index]
        stress_ewma = _ewma_smooth(
            np.array([v if v else 75 for v in stress_index], dtype=float), span=7
        ).tolist()
        
        # Reference zones for stress index
        series.extend([
            # High stress zone (>150)
            {
                "name": "High Stress Zone",
                "type": "line",
                "data": [stress_max] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(231, 76, 60, 0.12)"},
                "stack": "stress_zone_high",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "_stress_high_base",
                "type": "line",
                "data": [150] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "stress_zone_high",
                "symbol": "none",
                "silent": True,
            },
            # Elevated stress zone (100-150)
            {
                "name": "Elevated Stress",
                "type": "line",
                "data": [150] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(243, 156, 18, 0.12)"},
                "stack": "stress_zone_elevated",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "_stress_elev_base",
                "type": "line",
                "data": [100] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "stress_zone_elevated",
                "symbol": "none",
                "silent": True,
            },
            # Normal zone (50-100)
            {
                "name": "Normal Range",
                "type": "line",
                "data": [100] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(52, 152, 219, 0.10)"},
                "stack": "stress_zone_normal",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "_stress_normal_base",
                "type": "line",
                "data": [50] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "stress_zone_normal",
                "symbol": "none",
                "silent": True,
            },
            # Low stress zone (<50) - green
            {
                "name": "Low Stress",
                "type": "line",
                "data": [50] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(46, 204, 113, 0.10)"},
                "symbol": "none",
                "silent": True,
            },
            # Threshold markers
            {
                "name": "150 Threshold",
                "type": "line",
                "data": [150] * len(dates),
                "lineStyle": {"color": "#e74c3c", "width": 1.5, "type": "dashed"},
                "symbol": "none",
            },
            {
                "name": "100 Threshold",
                "type": "line",
                "data": [100] * len(dates),
                "lineStyle": {"color": "#f39c12", "width": 1.5, "type": "dotted"},
                "symbol": "none",
            },
            # Stress Index data
            {
                "name": "Stress Index",
                "type": "line",
                "data": stress_clean,
                "symbol": "circle",
                "symbolSize": 7,
                "lineStyle": {"color": "#e74c3c", "width": 2.5},
                "itemStyle": {"color": "#e74c3c"},
            },
            {
                "name": "Stress Trend",
                "type": "line",
                "data": stress_ewma,
                "symbol": "none",
                "lineStyle": {"color": "#c0392b", "width": 2.5},
                "smooth": True,
            },
        ])
        legend_data.extend(["Stress Trend", "150 Threshold", "100 Threshold"])
        
        y_axes.append({
            "type": "value",
            "name": "Stress Index (Baevsky)",
            "nameLocation": "middle",
            "nameGap": 55,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": stress_min,
            "max": stress_max,
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        })
    
    # PNS Index (secondary axis)
    if pns_index and any(v is not None for v in pns_index):
        # Dynamic axis bounds for PNS
        pns_min, pns_max = _auto_axis_bounds(
            pns_index,
            padding_pct=0.20,
        )
        # Ensure 0 line is visible as reference
        pns_min = min(pns_min, -0.5)
        pns_max = max(pns_max, 1.5)
        
        legend_data.append("PNS Index")
        pns_clean = [v if v is not None else None for v in pns_index]
        pns_ewma = _ewma_smooth(
            np.array([v if v else 0.5 for v in pns_index], dtype=float), span=7
        ).tolist()
        
        series.extend([
            # Zero reference line for PNS
            {
                "name": "PNS Baseline",
                "type": "line",
                "data": [0] * len(dates),
                "lineStyle": {"color": "#95a5a6", "width": 1.5, "type": "dashed"},
                "symbol": "none",
                "yAxisIndex": 1 if stress_index else 0,
            },
            # PNS data
            {
                "name": "PNS Index",
                "type": "line",
                "data": pns_clean,
                "symbol": "diamond",
                "symbolSize": 6,
                "lineStyle": {"color": "#27ae60", "width": 2},
                "itemStyle": {"color": "#27ae60"},
                "yAxisIndex": 1 if stress_index else 0,
            },
            {
                "name": "PNS Trend",
                "type": "line",
                "data": pns_ewma,
                "symbol": "none",
                "lineStyle": {"color": "#1e8449", "width": 2.5},
                "smooth": True,
                "yAxisIndex": 1 if stress_index else 0,
            },
        ])
        legend_data.extend(["PNS Trend", "PNS Baseline"])
        
        y_axes.append({
            "type": "value",
            "name": "PNS Index",
            "nameLocation": "middle",
            "nameGap": 45,
            "position": "right" if stress_index else "left",
            "min": pns_min,
            "max": pns_max,
            "axisLine": {"lineStyle": {"color": "#27ae60"}},
            "splitLine": {"show": False},
        })
    
    return {
        "title": {
            "text": title,
            "subtext": "Stress Index: <50 low | 50-100 normal | 100-150 elevated | >150 high | "
                       "PNS: >1.0 high vagal | <0 reduced",
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": """function(params) {
                var date = params[0].axisValue;
                var result = '<b>' + date + '</b><br/>';
                params.forEach(function(p) {
                    if (p.seriesName && p.seriesName.indexOf('_') !== 0 && 
                        p.seriesName.indexOf('Zone') === -1 && 
                        p.seriesName.indexOf('Threshold') === -1 &&
                        p.seriesName.indexOf('Baseline') === -1 &&
                        p.value !== null && p.value !== undefined) {
                        var val = typeof p.value === 'number' ? p.value.toFixed(1) : p.value;
                        result += p.marker + ' ' + p.seriesName + ': <b>' + val + '</b><br/>';
                    }
                });
                return result;
            }""",
        },
        "legend": {"data": legend_data, "bottom": 5, "textStyle": {"fontSize": 10}},
        "grid": {
            "left": "10%",
            "right": "10%",
            "top": "18%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": date_labels,
            "name": "Date",
            "nameLocation": "middle",
            "nameGap": 30,
            "axisLabel": {"rotate": 45, "fontSize": 9},
        },
        "yAxis": y_axes if y_axes else [{"type": "value"}],
        "series": series,
        "dataZoom": [{"type": "inside", "start": 0, "end": 100}],
    }


def _build_radiation_dose_chart(
    mission_days: List[int],
    radiation_msv: List[float],
    career_limit_msv: float = 600.0,
    title: str = "Cumulative Radiation Dose vs. Mission Day",
) -> Dict[str, Any]:
    """Build publication-quality radiation dose chart with dynamic axis scaling.
    
    Guidelines (NASA-STD-3001 Vol 1 Rev B, 2022):
    - Career effective dose limit: 600 mSv (design limit)
    - Legacy limit (pre-2022): 1000 mSv
    - ALARA principle: As Low As Reasonably Achievable
    
    Risk Zones (% of 600 mSv limit):
    - <30% (0-180 mSv): GO — Nominal operations
    - 30-60% (180-360 mSv): MONITOR — Enhanced monitoring
    - 60-80% (360-480 mSv): CAUTION — Mission planning review
    - >80% (>480 mSv): NO-GO — Operational restrictions
    
    References:
    - NASA-STD-3001 Vol 1 Rev B (2022). Crew Health Standard.
    - ICRP Publication 123 (2013). Assessment of radiation exposure of astronauts.
    - Cucinotta et al. (2017). Space radiation risks for astronauts on multiple ISS missions.
    """
    day_labels = [f"Day {d}" for d in mission_days]
    series = []
    legend_data = []
    
    if not radiation_msv or not any(v is not None for v in radiation_msv):
        return {"series": [], "title": {"text": title}}
    
    # Calculate threshold values
    threshold_30 = career_limit_msv * 0.30  # 180 mSv
    threshold_60 = career_limit_msv * 0.60  # 360 mSv
    threshold_80 = career_limit_msv * 0.80  # 480 mSv
    
    # Dynamic axis bounds — ensure all data + reference zones visible
    rad_min, rad_max = _auto_axis_bounds(
        radiation_msv,
        padding_pct=0.15,
        min_floor=0,
    )
    # Ensure at least the MONITOR threshold (30%) is visible for context
    rad_max = max(rad_max, threshold_30 * 1.2)
    
    legend_data.append("Cumulative Dose")
    rad_clean = [v if v is not None else None for v in radiation_msv]
    
    # Calculate EWMA trend if enough data points
    rad_ewma = None
    if len([v for v in radiation_msv if v is not None]) >= 3:
        rad_ewma = _ewma_smooth(
            np.array([v if v else 0 for v in radiation_msv], dtype=float), span=5
        ).tolist()
    
    # Reference zones (only show zones within visible range)
    zone_series = []
    
    # GO zone (0-30% = 0-180 mSv)
    if rad_max > 0:
        zone_upper = min(threshold_30, rad_max)
        zone_series.extend([
            {
                "name": "GO Zone (<30%)",
                "type": "line",
                "data": [zone_upper] * len(mission_days),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(40, 167, 69, 0.12)"},
                "symbol": "none",
                "silent": True,
            },
        ])
    
    # MONITOR zone (30-60% = 180-360 mSv)
    if rad_max > threshold_30:
        zone_upper = min(threshold_60, rad_max)
        zone_series.extend([
            {
                "name": "MONITOR Zone (30-60%)",
                "type": "line",
                "data": [zone_upper] * len(mission_days),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(255, 193, 7, 0.12)"},
                "stack": "zone_monitor",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "_monitor_base",
                "type": "line",
                "data": [threshold_30] * len(mission_days),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "zone_monitor",
                "symbol": "none",
                "silent": True,
            },
        ])
    
    # CAUTION zone (60-80% = 360-480 mSv)
    if rad_max > threshold_60:
        zone_upper = min(threshold_80, rad_max)
        zone_series.extend([
            {
                "name": "CAUTION Zone (60-80%)",
                "type": "line",
                "data": [zone_upper] * len(mission_days),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(253, 126, 20, 0.12)"},
                "stack": "zone_caution",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "_caution_base",
                "type": "line",
                "data": [threshold_60] * len(mission_days),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "zone_caution",
                "symbol": "none",
                "silent": True,
            },
        ])
    
    # NO-GO zone (>80% = >480 mSv)
    if rad_max > threshold_80:
        zone_series.extend([
            {
                "name": "NO-GO Zone (>80%)",
                "type": "line",
                "data": [rad_max] * len(mission_days),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(220, 53, 69, 0.12)"},
                "stack": "zone_nogo",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "_nogo_base",
                "type": "line",
                "data": [threshold_80] * len(mission_days),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "zone_nogo",
                "symbol": "none",
                "silent": True,
            },
        ])
    
    series.extend(zone_series)
    
    # Threshold lines (only if within visible range)
    threshold_lines = []
    if rad_max >= threshold_30 * 0.8:  # Show if approaching
        threshold_lines.append({
            "name": "30% Limit (180 mSv)",
            "type": "line",
            "data": [threshold_30] * len(mission_days),
            "lineStyle": {"color": "#ffc107", "width": 2, "type": "dashed"},
            "symbol": "none",
        })
        legend_data.append("30% Limit (180 mSv)")
    
    if rad_max >= threshold_60 * 0.9:
        threshold_lines.append({
            "name": "60% Limit (360 mSv)",
            "type": "line",
            "data": [threshold_60] * len(mission_days),
            "lineStyle": {"color": "#fd7e14", "width": 2, "type": "dashed"},
            "symbol": "none",
        })
        legend_data.append("60% Limit (360 mSv)")
    
    if rad_max >= threshold_80 * 0.95:
        threshold_lines.append({
            "name": "80% Limit (480 mSv)",
            "type": "line",
            "data": [threshold_80] * len(mission_days),
            "lineStyle": {"color": "#dc3545", "width": 2, "type": "dashed"},
            "symbol": "none",
        })
        legend_data.append("80% Limit (480 mSv)")
    
    series.extend(threshold_lines)
    
    # Main data series
    series.append({
        "name": "Cumulative Dose",
        "type": "line",
        "data": rad_clean,
        "symbol": "circle",
        "symbolSize": 8,
        "lineStyle": {"color": "#8e44ad", "width": 3},
        "itemStyle": {"color": "#8e44ad"},
        "areaStyle": {"color": "rgba(142, 68, 173, 0.08)"},
    })
    
    # Trend line
    if rad_ewma:
        series.append({
            "name": "5-Day Trend",
            "type": "line",
            "data": rad_ewma,
            "symbol": "none",
            "lineStyle": {"color": "#2c3e50", "width": 2.5},
            "smooth": True,
        })
        legend_data.append("5-Day Trend")
    
    return {
        "title": {
            "text": title,
            "subtext": f"NASA Career Limit: {career_limit_msv:.0f} mSv | "
                       "Zones: <30% GO | 30-60% MONITOR | 60-80% CAUTION | >80% NO-GO",
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": """function(params) {
                var day = params[0].axisValue;
                var result = '<b>' + day + '</b><br/>';
                params.forEach(function(p) {
                    if (p.seriesName && p.seriesName.indexOf('_') !== 0 && 
                        p.seriesName.indexOf('Zone') === -1 &&
                        p.value !== null && p.value !== undefined) {
                        var val = typeof p.value === 'number' ? p.value.toFixed(2) : p.value;
                        var unit = p.seriesName.indexOf('Limit') >= 0 ? '' : ' mSv';
                        result += p.marker + ' ' + p.seriesName + ': <b>' + val + unit + '</b><br/>';
                    }
                });
                return result;
            }""",
        },
        "legend": {"data": legend_data, "bottom": 5, "textStyle": {"fontSize": 10}},
        "grid": {
            "left": "10%",
            "right": "5%",
            "top": "18%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": day_labels,
            "name": "Mission Day",
            "nameLocation": "middle",
            "nameGap": 30,
            "axisLabel": {"rotate": 45, "fontSize": 9},
        },
        "yAxis": {
            "type": "value",
            "name": "Cumulative Dose (mSv)",
            "nameLocation": "middle",
            "nameGap": 55,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": rad_min,
            "max": rad_max,
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        },
        "series": series,
        "dataZoom": [{"type": "inside", "start": 0, "end": 100}],
    }


def _build_fatigue_sleepiness_chart(
    dates: List[str],
    samn_perelli: Optional[List[float]] = None,
    karolinska: Optional[List[float]] = None,
    title: str = "Fatigue & Sleepiness Trends",
) -> Dict[str, Any]:
    """Build publication-quality Fatigue & Sleepiness trends chart.
    
    Scales:
    - Samn-Perelli Fatigue Scale (SP): 1-7
      1 = Fully alert, wide awake
      2 = Very lively, responsive
      3 = Okay, somewhat fresh
      4 = A little tired, less than fresh
      5 = Moderately tired, let down
      6 = Extremely tired, very difficult to concentrate
      7 = Completely exhausted, unable to function
      
    - Karolinska Sleepiness Scale (KSS): 1-9
      1 = Extremely alert
      3 = Alert
      5 = Neither alert nor sleepy
      7 = Sleepy, but no effort to stay awake
      9 = Extremely sleepy, fighting sleep
    
    References:
    - Samn & Perelli (1982). USAF School of Aerospace Medicine.
    - Åkerstedt & Gillberg (1990). Int J Neurosci, 52(1-2), 29-37.
    """
    date_labels = [str(d)[:10] for d in dates]
    series = []
    legend_data = []
    
    has_sp = samn_perelli and any(v is not None for v in samn_perelli)
    has_kss = karolinska and any(v is not None for v in karolinska)
    
    if not has_sp and not has_kss:
        return {"series": [], "title": {"text": title}}
    
    # Reference zones for both scales
    # SP: 1-3 Alert, 4-5 Tired, 6-7 Exhausted
    # KSS: 1-4 Alert, 5-6 Neutral, 7-9 Sleepy
    
    # Reference zone: Alert/Good (SP 1-3, KSS 1-4)
    series.extend([
        {
            "name": "Alert Zone",
            "type": "line",
            "data": [3.5] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "rgba(46, 204, 113, 0.12)"},
            "symbol": "none",
            "silent": True,
        },
        # Tired/Neutral zone (SP 3.5-5.5, KSS 4-7)
        {
            "name": "Tired Zone",
            "type": "line",
            "data": [5.5] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "rgba(243, 156, 18, 0.12)"},
            "stack": "zone_tired",
            "symbol": "none",
            "silent": True,
        },
        {
            "name": "_tired_base",
            "type": "line",
            "data": [3.5] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "#fff"},
            "stack": "zone_tired",
            "symbol": "none",
            "silent": True,
        },
        # Exhausted/Sleepy zone (SP 5.5-7, KSS 7-9)
        {
            "name": "Exhausted Zone",
            "type": "line",
            "data": [9] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "rgba(231, 76, 60, 0.12)"},
            "stack": "zone_exhausted",
            "symbol": "none",
            "silent": True,
        },
        {
            "name": "_exhausted_base",
            "type": "line",
            "data": [5.5] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "#fff"},
            "stack": "zone_exhausted",
            "symbol": "none",
            "silent": True,
        },
    ])
    
    # Threshold lines
    series.extend([
        {
            "name": "Alert Threshold",
            "type": "line",
            "data": [3.5] * len(dates),
            "lineStyle": {"color": "#27ae60", "width": 1.5, "type": "dashed"},
            "symbol": "none",
        },
        {
            "name": "Fatigue Threshold",
            "type": "line",
            "data": [5.5] * len(dates),
            "lineStyle": {"color": "#e74c3c", "width": 1.5, "type": "dashed"},
            "symbol": "none",
        },
    ])
    legend_data.extend(["Alert Threshold", "Fatigue Threshold"])
    
    # Samn-Perelli data
    if has_sp:
        sp_clean = [v if v is not None else None for v in samn_perelli]
        sp_ewma = _ewma_smooth(
            np.array([v if v else 3 for v in samn_perelli], dtype=float), span=5
        ).tolist()
        
        series.extend([
            {
                "name": "Samn-Perelli (SP)",
                "type": "line",
                "data": sp_clean,
                "symbol": "circle",
                "symbolSize": 8,
                "lineStyle": {"color": "#e74c3c", "width": 2.5},
                "itemStyle": {"color": "#e74c3c"},
            },
            {
                "name": "SP Trend",
                "type": "line",
                "data": sp_ewma,
                "symbol": "none",
                "lineStyle": {"color": "#c0392b", "width": 2},
                "smooth": True,
            },
        ])
        legend_data.extend(["Samn-Perelli (SP)", "SP Trend"])
    
    # Karolinska data
    if has_kss:
        kss_clean = [v if v is not None else None for v in karolinska]
        kss_ewma = _ewma_smooth(
            np.array([v if v else 5 for v in karolinska], dtype=float), span=5
        ).tolist()
        
        series.extend([
            {
                "name": "Karolinska (KSS)",
                "type": "line",
                "data": kss_clean,
                "symbol": "diamond",
                "symbolSize": 7,
                "lineStyle": {"color": "#3498db", "width": 2.5},
                "itemStyle": {"color": "#3498db"},
            },
            {
                "name": "KSS Trend",
                "type": "line",
                "data": kss_ewma,
                "symbol": "none",
                "lineStyle": {"color": "#2980b9", "width": 2},
                "smooth": True,
            },
        ])
        legend_data.extend(["Karolinska (KSS)", "KSS Trend"])
    
    # Dynamic y-axis bounds
    all_values = []
    if has_sp:
        all_values.extend([v for v in samn_perelli if v is not None])
    if has_kss:
        all_values.extend([v for v in karolinska if v is not None])
    
    y_min, y_max = _auto_axis_bounds(
        all_values,
        padding_pct=0.10,
        min_floor=1,
        max_ceil=9,
    )
    
    return {
        "title": {
            "text": title,
            "subtext": "SP: 1-7 (1=alert, 7=exhausted) | KSS: 1-9 (1=extremely alert, 9=fighting sleep)",
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": """function(params) {
                var date = params[0].axisValue;
                var result = '<b>' + date + '</b><br/>';
                params.forEach(function(p) {
                    if (p.seriesName && p.seriesName.indexOf('_') !== 0 && 
                        p.seriesName.indexOf('Zone') === -1 && 
                        p.seriesName.indexOf('Threshold') === -1 &&
                        p.value !== null && p.value !== undefined) {
                        var val = typeof p.value === 'number' ? p.value.toFixed(1) : p.value;
                        result += p.marker + ' ' + p.seriesName + ': <b>' + val + '</b><br/>';
                    }
                });
                return result;
            }""",
        },
        "legend": {"data": legend_data, "bottom": 5, "textStyle": {"fontSize": 10}},
        "grid": {
            "left": "8%",
            "right": "5%",
            "top": "18%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": date_labels,
            "name": "Assessment Date",
            "nameLocation": "middle",
            "nameGap": 30,
            "axisLabel": {"rotate": 45, "fontSize": 9},
        },
        "yAxis": {
            "type": "value",
            "name": "Fatigue/Sleepiness Score",
            "nameLocation": "middle",
            "nameGap": 45,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": y_min,
            "max": y_max,
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        },
        "series": series,
        "dataZoom": [{"type": "inside", "start": 0, "end": 100}],
    }


def _build_hrv_activity_timeseries_chart(
    dates: List[str],
    steps: Optional[List[float]] = None,
    rmssd_ms: Optional[List[float]] = None,
    title: str = "HRV × Activity Time Series",
) -> Dict[str, Any]:
    """Build publication-quality dual-axis chart for HRV and Activity metrics.
    
    This chart displays daily steps (activity/load) alongside RMSSD (recovery)
    to visualize the relationship between physical activity and autonomic recovery.
    
    Interpretation:
    - High steps + High RMSSD: Good fitness, adequate recovery
    - High steps + Low RMSSD: Possible overtraining, insufficient recovery
    - Low steps + High RMSSD: Good recovery, potential for increased load
    - Low steps + Low RMSSD: Low activity but poor recovery (stress/illness?)
    
    References:
    - Plews et al. (2013). Training adaptation and HRV in elite endurance athletes.
    - Stanley et al. (2013). Cardiac parasympathetic reactivation following exercise.
    """
    date_labels = [str(d)[:10] for d in dates]
    series = []
    legend_data = []
    y_axes = []
    
    has_steps = steps and any(v is not None for v in steps)
    has_rmssd = rmssd_ms and any(v is not None for v in rmssd_ms)
    
    if not has_steps and not has_rmssd:
        return {"series": [], "title": {"text": title}}
    
    # Steps (primary axis - bars)
    if has_steps:
        steps_min, steps_max = _auto_axis_bounds(
            steps,
            padding_pct=0.15,
            min_floor=0,
        )
        # Ensure 10k step goal marker is visible
        steps_max = max(steps_max, 12000)
        
        legend_data.append("Daily Steps")
        steps_clean = [v if v is not None else None for v in steps]
        steps_ewma = _ewma_smooth(
            np.array([v if v else 5000 for v in steps], dtype=float), span=7
        ).tolist()
        
        # WHO target zone (8k-10k steps)
        series.extend([
            {
                "name": "WHO Target Zone",
                "type": "line",
                "data": [10000] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(46, 204, 113, 0.12)"},
                "stack": "steps_zone",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "_steps_zone_base",
                "type": "line",
                "data": [8000] * len(dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "steps_zone",
                "symbol": "none",
                "silent": True,
            },
            # 10k goal line
            {
                "name": "10k Goal",
                "type": "line",
                "data": [10000] * len(dates),
                "lineStyle": {"color": "#27ae60", "width": 2, "type": "dashed"},
                "symbol": "none",
            },
            # Steps bars
            {
                "name": "Daily Steps",
                "type": "bar",
                "data": steps_clean,
                "itemStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#3498db"},
                            {"offset": 1, "color": "#2980b9"},
                        ],
                    },
                    "borderRadius": [3, 3, 0, 0],
                },
                "barMaxWidth": 20,
            },
            # 7-day steps trend
            {
                "name": "Steps Trend",
                "type": "line",
                "data": steps_ewma,
                "symbol": "none",
                "lineStyle": {"color": "#1a5276", "width": 2.5},
                "smooth": True,
            },
        ])
        legend_data.extend(["Steps Trend", "10k Goal"])
        
        y_axes.append({
            "type": "value",
            "name": "Daily Steps",
            "nameLocation": "middle",
            "nameGap": 55,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": steps_min,
            "max": steps_max,
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        })
    
    # RMSSD (secondary axis - line)
    if has_rmssd:
        rmssd_min, rmssd_max = _auto_axis_bounds(
            rmssd_ms,
            padding_pct=0.20,
            min_floor=0,
        )
        
        legend_data.append("RMSSD (ms)")
        rmssd_clean = [v if v is not None else None for v in rmssd_ms]
        rmssd_ewma = _ewma_smooth(
            np.array([v if v else 40 for v in rmssd_ms], dtype=float), span=7
        ).tolist()
        
        series.extend([
            # RMSSD line
            {
                "name": "RMSSD (ms)",
                "type": "line",
                "data": rmssd_clean,
                "symbol": "circle",
                "symbolSize": 7,
                "lineStyle": {"color": "#e74c3c", "width": 2.5},
                "itemStyle": {"color": "#e74c3c"},
                "yAxisIndex": 1 if has_steps else 0,
            },
            # RMSSD trend
            {
                "name": "RMSSD Trend",
                "type": "line",
                "data": rmssd_ewma,
                "symbol": "none",
                "lineStyle": {"color": "#922b21", "width": 2.5},
                "smooth": True,
                "yAxisIndex": 1 if has_steps else 0,
            },
        ])
        legend_data.append("RMSSD Trend")
        
        y_axes.append({
            "type": "value",
            "name": "RMSSD (ms)",
            "nameLocation": "middle",
            "nameGap": 45,
            "position": "right" if has_steps else "left",
            "min": rmssd_min,
            "max": rmssd_max,
            "axisLine": {"lineStyle": {"color": "#e74c3c"}},
            "splitLine": {"show": False},
        })
    
    return {
        "title": {
            "text": title,
            "subtext": "Steps (activity load) vs RMSSD (parasympathetic recovery) | WHO: 8k-10k steps/day",
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": """function(params) {
                var date = params[0].axisValue;
                var result = '<b>' + date + '</b><br/>';
                params.forEach(function(p) {
                    if (p.seriesName && p.seriesName.indexOf('_') !== 0 && 
                        p.seriesName.indexOf('Zone') === -1 && 
                        p.seriesName.indexOf('Goal') === -1 &&
                        p.value !== null && p.value !== undefined) {
                        var val = typeof p.value === 'number' ? p.value.toFixed(0) : p.value;
                        var unit = p.seriesName.indexOf('RMSSD') >= 0 ? ' ms' : '';
                        result += p.marker + ' ' + p.seriesName + ': <b>' + val + unit + '</b><br/>';
                    }
                });
                return result;
            }""",
        },
        "legend": {"data": legend_data, "bottom": 5, "textStyle": {"fontSize": 10}},
        "grid": {
            "left": "10%",
            "right": "10%",
            "top": "18%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": date_labels,
            "name": "Date",
            "nameLocation": "middle",
            "nameGap": 30,
            "axisLabel": {"rotate": 45, "fontSize": 9},
        },
        "yAxis": y_axes if y_axes else [{"type": "value"}],
        "series": series,
        "dataZoom": [{"type": "inside", "start": 0, "end": 100}],
    }


def _build_hrv_activity_scatter_chart(
    x_values: List[float],
    y_values: List[float],
    x_label: str,
    y_label: str,
    title: str,
    correlation: Optional[float] = None,
    n_samples: Optional[int] = None,
) -> Dict[str, Any]:
    """Build publication-quality scatter plot with regression line for HRV × Activity.
    
    Features:
    - Scatter points with semi-transparent fill
    - Linear regression line with confidence band
    - Correlation coefficient display
    - Dynamic axis scaling
    
    References:
    - Plews et al. (2013). Training adaptation and HRV in elite endurance athletes.
    - Buchheit (2014). Monitoring training status with HR measures.
    """
    if not x_values or not y_values:
        return {"series": [], "title": {"text": title}}
    
    # Prepare scatter data
    scatter_data = [
        [x, y] for x, y in zip(x_values, y_values)
        if x is not None and y is not None and not np.isnan(x) and not np.isnan(y)
    ]
    
    if len(scatter_data) < 3:
        return {"series": [], "title": {"text": title}}
    
    # Extract clean x, y for regression
    x_clean = [p[0] for p in scatter_data]
    y_clean = [p[1] for p in scatter_data]
    
    # Calculate regression line
    x_arr = np.array(x_clean)
    y_arr = np.array(y_clean)
    
    # Simple linear regression
    slope, intercept = np.polyfit(x_arr, y_arr, 1)
    x_line = np.linspace(min(x_arr), max(x_arr), 50)
    y_line = slope * x_line + intercept
    regression_data = [[float(x), float(y)] for x, y in zip(x_line, y_line)]
    
    # Dynamic axis bounds
    x_min, x_max = _auto_axis_bounds(x_clean, padding_pct=0.10, min_floor=0)
    y_min, y_max = _auto_axis_bounds(y_clean, padding_pct=0.10, min_floor=0)
    
    # Correlation interpretation
    corr_text = ""
    corr_color = "#7f8c8d"
    if correlation is not None and not np.isnan(correlation):
        abs_corr = abs(correlation)
        if abs_corr >= 0.7:
            corr_text = "Strong"
            corr_color = "#27ae60" if correlation > 0 else "#e74c3c"
        elif abs_corr >= 0.4:
            corr_text = "Moderate"
            corr_color = "#f39c12"
        elif abs_corr >= 0.2:
            corr_text = "Weak"
            corr_color = "#95a5a6"
        else:
            corr_text = "Negligible"
            corr_color = "#bdc3c7"
    
    # Build subtitle
    subtitle_parts = []
    if correlation is not None and not np.isnan(correlation):
        subtitle_parts.append(f"Pearson r = {correlation:.3f} ({corr_text})")
    if n_samples is not None:
        subtitle_parts.append(f"n = {n_samples}")
    subtitle = " | ".join(subtitle_parts) if subtitle_parts else "Correlation analysis"
    
    series = [
        # Scatter points
        {
            "name": "Data Points",
            "type": "scatter",
            "data": scatter_data,
            "symbolSize": 10,
            "itemStyle": {
                "color": "rgba(52, 152, 219, 0.7)",
                "borderColor": "#2980b9",
                "borderWidth": 1,
            },
        },
        # Regression line
        {
            "name": "Regression Line",
            "type": "line",
            "data": regression_data,
            "symbol": "none",
            "lineStyle": {"color": "#e74c3c", "width": 2.5, "type": "solid"},
            "smooth": False,
        },
    ]
    
    return {
        "title": {
            "text": title,
            "subtext": subtitle,
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 11, "color": corr_color, "fontWeight": "bold"},
        },
        "tooltip": {
            "trigger": "item",
            "formatter": """function(params) {
                if (params.seriesType === 'scatter') {
                    return '<b>""" + x_label + """</b>: ' + params.value[0].toFixed(1) + 
                           '<br/><b>""" + y_label + """</b>: ' + params.value[1].toFixed(1) + ' ms';
                }
                return '';
            }""",
        },
        "legend": {"data": ["Data Points", "Regression Line"], "bottom": 5, "textStyle": {"fontSize": 10}},
        "grid": {
            "left": "12%",
            "right": "8%",
            "top": "18%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "value",
            "name": x_label,
            "nameLocation": "middle",
            "nameGap": 35,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": x_min,
            "max": x_max,
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        },
        "yAxis": {
            "type": "value",
            "name": y_label,
            "nameLocation": "middle",
            "nameGap": 50,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": y_min,
            "max": y_max,
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        },
        "series": series,
    }


def _build_panas_affect_chart(
    dates: List[str],
    positive_affect: Optional[List[float]] = None,
    negative_affect: Optional[List[float]] = None,
    title: str = "PANAS Affect Trends",
) -> Dict[str, Any]:
    """Build publication-quality PANAS Positive/Negative Affect chart.
    
    PANAS (Positive and Negative Affect Schedule):
    - Each scale consists of 10 items rated 1-5 (total range: 10-50)
    - Positive Affect (PA): enthusiasm, interest, determination, excitement, inspiration
    - Negative Affect (NA): distress, upset, guilt, scared, hostile
    
    Interpretation:
    - PA: Higher scores = more positive affect (desirable)
    - NA: Lower scores = less negative affect (desirable)
    
    Population norms (Watson et al., 1988):
    - PA mean: ~31-35, SD ~7-8
    - NA mean: ~16-19, SD ~6-7
    
    References:
    - Watson, Clark, & Tellegen (1988). Development and validation of brief measures
      of positive and negative affect: The PANAS scales. J Pers Soc Psychol, 54(6), 1063-1070.
    - Crawford & Henry (2004). The Positive and Negative Affect Schedule (PANAS):
      Construct validity, measurement properties and normative data. Br J Clin Psychol, 43, 245-265.
    """
    date_labels = [str(d)[:10] for d in dates]
    series = []
    legend_data = []
    
    has_pa = positive_affect and any(v is not None for v in positive_affect)
    has_na = negative_affect and any(v is not None for v in negative_affect)
    
    if not has_pa and not has_na:
        return {"series": [], "title": {"text": title}}
    
    # Reference zones based on population norms
    # PA: High >38, Moderate 25-38, Low <25
    # NA: Low <15 (good), Moderate 15-25, High >25 (concerning)
    
    series.extend([
        # Healthy PA zone (high PA > 35)
        {
            "name": "High PA Zone",
            "type": "line",
            "data": [50] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "rgba(46, 204, 113, 0.10)"},
            "stack": "pa_zone_high",
            "symbol": "none",
            "silent": True,
        },
        {
            "name": "_pa_high_base",
            "type": "line",
            "data": [35] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "#fff"},
            "stack": "pa_zone_high",
            "symbol": "none",
            "silent": True,
        },
        # Concerning NA zone (>25)
        {
            "name": "High NA Zone",
            "type": "line",
            "data": [50] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "rgba(231, 76, 60, 0.08)"},
            "stack": "na_zone_high",
            "symbol": "none",
            "silent": True,
        },
        {
            "name": "_na_high_base",
            "type": "line",
            "data": [25] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "#fff"},
            "stack": "na_zone_high",
            "symbol": "none",
            "silent": True,
        },
    ])
    
    # Reference lines
    series.extend([
        {
            "name": "PA Mean (~33)",
            "type": "line",
            "data": [33] * len(dates),
            "lineStyle": {"color": "#27ae60", "width": 1.5, "type": "dotted"},
            "symbol": "none",
        },
        {
            "name": "NA Mean (~17)",
            "type": "line",
            "data": [17] * len(dates),
            "lineStyle": {"color": "#e74c3c", "width": 1.5, "type": "dotted"},
            "symbol": "none",
        },
    ])
    legend_data.extend(["PA Mean (~33)", "NA Mean (~17)"])
    
    # Positive Affect data
    if has_pa:
        pa_clean = [v if v is not None else None for v in positive_affect]
        pa_ewma = _ewma_smooth(
            np.array([v if v else 30 for v in positive_affect], dtype=float), span=5
        ).tolist()
        
        series.extend([
            {
                "name": "Positive Affect",
                "type": "line",
                "data": pa_clean,
                "symbol": "circle",
                "symbolSize": 8,
                "lineStyle": {"color": "#27ae60", "width": 2.5},
                "itemStyle": {"color": "#27ae60"},
            },
            {
                "name": "PA Trend",
                "type": "line",
                "data": pa_ewma,
                "symbol": "none",
                "lineStyle": {"color": "#1e8449", "width": 2},
                "smooth": True,
            },
        ])
        legend_data.extend(["Positive Affect", "PA Trend"])
    
    # Negative Affect data
    if has_na:
        na_clean = [v if v is not None else None for v in negative_affect]
        na_ewma = _ewma_smooth(
            np.array([v if v else 20 for v in negative_affect], dtype=float), span=5
        ).tolist()
        
        series.extend([
            {
                "name": "Negative Affect",
                "type": "line",
                "data": na_clean,
                "symbol": "triangle",
                "symbolSize": 7,
                "lineStyle": {"color": "#e74c3c", "width": 2.5},
                "itemStyle": {"color": "#e74c3c"},
            },
            {
                "name": "NA Trend",
                "type": "line",
                "data": na_ewma,
                "symbol": "none",
                "lineStyle": {"color": "#c0392b", "width": 2},
                "smooth": True,
            },
        ])
        legend_data.extend(["Negative Affect", "NA Trend"])
    
    # Dynamic y-axis bounds
    all_values = []
    if has_pa:
        all_values.extend([v for v in positive_affect if v is not None])
    if has_na:
        all_values.extend([v for v in negative_affect if v is not None])
    
    y_min, y_max = _auto_axis_bounds(
        all_values,
        padding_pct=0.10,
        min_floor=10,
        max_ceil=50,
    )
    
    return {
        "title": {
            "text": title,
            "subtext": "PA: Higher=better (goal >35) | NA: Lower=better (goal <17) | Range: 10-50",
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": """function(params) {
                var date = params[0].axisValue;
                var result = '<b>' + date + '</b><br/>';
                params.forEach(function(p) {
                    if (p.seriesName && p.seriesName.indexOf('_') !== 0 && 
                        p.seriesName.indexOf('Zone') === -1 && 
                        p.seriesName.indexOf('Mean') === -1 &&
                        p.value !== null && p.value !== undefined) {
                        var val = typeof p.value === 'number' ? p.value.toFixed(0) : p.value;
                        result += p.marker + ' ' + p.seriesName + ': <b>' + val + '/50</b><br/>';
                    }
                });
                return result;
            }""",
        },
        "legend": {"data": legend_data, "bottom": 5, "textStyle": {"fontSize": 10}},
        "grid": {
            "left": "8%",
            "right": "5%",
            "top": "18%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": date_labels,
            "name": "Assessment Date",
            "nameLocation": "middle",
            "nameGap": 30,
            "axisLabel": {"rotate": 45, "fontSize": 9},
        },
        "yAxis": {
            "type": "value",
            "name": "Affect Score (10-50)",
            "nameLocation": "middle",
            "nameGap": 45,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": y_min,
            "max": y_max,
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        },
        "series": series,
        "dataZoom": [{"type": "inside", "start": 0, "end": 100}],
    }


def _build_sleep_duration_chart(
    dates: List[str],
    sleep_hours: Optional[List[float]] = None,
    title: str = "Sleep Duration Trends",
) -> Dict[str, Any]:
    """Build publication-quality sleep duration chart with dynamic axis scaling.
    
    Guidelines:
    - NSF (2015): Adults need 7-9 hours of sleep
    - <6 hours: Sleep deprivation, cognitive impairment risk
    - >9 hours: May indicate health issues or recovery needs
    
    References:
    - Hirshkowitz et al. (2015). Sleep Health, 1(1), 40-43.
    - Watson et al. (2015). Sleep, 38(6), 843-844.
    """
    date_labels = [str(d)[:10] for d in dates]
    series = []
    legend_data = []
    
    if not sleep_hours or not any(v is not None for v in sleep_hours):
        return {"series": [], "title": {"text": title}}
    
    # Dynamic axis bounds for sleep
    sleep_min, sleep_max = _auto_axis_bounds(
        sleep_hours,
        padding_pct=0.15,
        min_floor=0,
    )
    # Ensure optimal zone (7-9) is visible
    sleep_min = min(sleep_min, 4)
    sleep_max = max(sleep_max, 11)
    
    legend_data.append("Sleep Duration")
    sleep_clean = [v if v is not None else None for v in sleep_hours]
    sleep_ewma = _ewma_smooth(
        np.array([v if v else 7 for v in sleep_hours], dtype=float), span=7
    ).tolist()
    
    # Reference zones
    series.extend([
        # Optimal sleep zone (7-9 hours)
        {
            "name": "Optimal Zone",
            "type": "line",
            "data": [9] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "rgba(46, 204, 113, 0.15)"},
            "stack": "sleep_zone_optimal",
            "symbol": "none",
            "silent": True,
        },
        {
            "name": "_sleep_opt_base",
            "type": "line",
            "data": [7] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "#fff"},
            "stack": "sleep_zone_optimal",
            "symbol": "none",
            "silent": True,
        },
        # Sleep deprivation warning zone (<6 hours)
        {
            "name": "Deprivation Risk",
            "type": "line",
            "data": [6] * len(dates),
            "lineStyle": {"opacity": 0},
            "areaStyle": {"color": "rgba(231, 76, 60, 0.10)"},
            "symbol": "none",
            "silent": True,
        },
        # 7-hour threshold line (minimum recommended)
        {
            "name": "7h Minimum",
            "type": "line",
            "data": [7] * len(dates),
            "lineStyle": {"color": "#27ae60", "width": 2, "type": "dashed"},
            "symbol": "none",
        },
        # 6-hour warning line
        {
            "name": "6h Warning",
            "type": "line",
            "data": [6] * len(dates),
            "lineStyle": {"color": "#e74c3c", "width": 1.5, "type": "dotted"},
            "symbol": "none",
        },
        # Sleep data as bars
        {
            "name": "Sleep Duration",
            "type": "bar",
            "data": sleep_clean,
            "itemStyle": {
                "color": {
                    "type": "linear",
                    "x": 0, "y": 0, "x2": 0, "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": "#9b59b6"},
                        {"offset": 1, "color": "#8e44ad"},
                    ],
                },
                "borderRadius": [4, 4, 0, 0],
            },
            "barMaxWidth": 25,
        },
        # 7-day trend line
        {
            "name": "7-Day Trend",
            "type": "line",
            "data": sleep_ewma,
            "symbol": "none",
            "lineStyle": {"color": "#2c3e50", "width": 2.5},
            "smooth": True,
        },
    ])
    legend_data.extend(["7-Day Trend", "7h Minimum", "6h Warning"])
    
    return {
        "title": {
            "text": title,
            "subtext": "NSF Guidelines: 7-9h optimal for adults | <6h increases cognitive impairment risk",
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": """function(params) {
                var date = params[0].axisValue;
                var result = '<b>' + date + '</b><br/>';
                params.forEach(function(p) {
                    if (p.seriesName && p.seriesName.indexOf('_') !== 0 && 
                        p.seriesName.indexOf('Zone') === -1 && 
                        p.seriesName.indexOf('Risk') === -1 &&
                        p.value !== null && p.value !== undefined) {
                        var val = typeof p.value === 'number' ? p.value.toFixed(1) : p.value;
                        result += p.marker + ' ' + p.seriesName + ': <b>' + val + ' h</b><br/>';
                    }
                });
                return result;
            }""",
        },
        "legend": {"data": legend_data, "bottom": 5, "textStyle": {"fontSize": 10}},
        "grid": {
            "left": "8%",
            "right": "5%",
            "top": "18%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": date_labels,
            "name": "Date",
            "nameLocation": "middle",
            "nameGap": 30,
            "axisLabel": {"rotate": 45, "fontSize": 9},
        },
        "yAxis": {
            "type": "value",
            "name": "Sleep Duration (hours)",
            "nameLocation": "middle",
            "nameGap": 45,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": sleep_min,
            "max": sleep_max,
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        },
        "series": series,
        "dataZoom": [{"type": "inside", "start": 0, "end": 100}],
    }


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


def _compute_joint_eva_decision(
    *,
    flight_surgeon_clearance: str,
    radiation_status: Optional[str] = None,
    s_scale: int = 0,
    g_scale: int = 0,
) -> tuple[str, str, List[str]]:
    """Compute joint EVA clearance decision from multiple inputs.
    
    The decision follows a conservative (most restrictive) approach:
    - Flight Surgeon decision is authoritative and can override all other inputs
    - Radiation status and Space Weather contribute to the final decision
    - The most restrictive status wins (NO-GO > CAUTION > MONITOR > GO)
    
    Args:
        flight_surgeon_clearance: Flight surgeon's EVA clearance decision.
        radiation_status: EVA radiation risk assessment status (GO, GO_WITH_MONITORING, CAUTION, NO_GO).
        s_scale: NOAA S-scale (0-5) for radiation storms.
        g_scale: NOAA G-scale (0-5) for geomagnetic storms.
        
    Returns:
        Tuple of (final_decision, rationale, contributing_factors).
        
    References:
        - NASA STD-3001 Space Flight Human-System Standard
        - NOAA Space Weather Scales (https://www.swpc.noaa.gov/noaa-scales-explanation)
    """
    # Priority mapping (higher = more restrictive)
    PRIORITY: Dict[str, int] = {
        "GO": 1,
        "MONITOR": 2,
        "CAUTION": 3,
        "NO-GO": 4,
    }
    
    decisions: List[tuple[str, str]] = []  # (decision, source)
    factors: List[str] = []
    
    # 1. Flight Surgeon Decision (authoritative)
    fs_norm = str(flight_surgeon_clearance).strip().lower()
    if fs_norm in {"cleared", "go", "1", "yes", "approved", "green"}:
        decisions.append(("GO", "Flight Surgeon"))
        factors.append("✅ Flight Surgeon: CLEARED")
    elif fs_norm in {"cleared with restriction", "monitor", "caution", "yellow"}:
        decisions.append(("MONITOR", "Flight Surgeon"))
        factors.append("⚠️ Flight Surgeon: CLEARED WITH RESTRICTION")
    elif fs_norm in {"no eva", "no-go", "nogo", "0", "no", "red", "hold", "denied"}:
        decisions.append(("NO-GO", "Flight Surgeon"))
        factors.append("🚫 Flight Surgeon: NO EVA")
    elif fs_norm in {"post-eva recovery", "recovery"}:
        decisions.append(("MONITOR", "Flight Surgeon"))
        factors.append("🔄 Flight Surgeon: POST-EVA RECOVERY")
    else:
        decisions.append(("MONITOR", "Flight Surgeon"))
        factors.append(f"⚠️ Flight Surgeon: {flight_surgeon_clearance}")
    
    # 2. Radiation Status
    if radiation_status:
        rad_norm = str(radiation_status).strip().upper().replace("_", " ")
        if rad_norm in {"GO", "GO"}:
            decisions.append(("GO", "Radiation"))
            factors.append("✅ Radiation: GO")
        elif rad_norm in {"GO WITH MONITORING", "GO_WITH_MONITORING"}:
            decisions.append(("MONITOR", "Radiation"))
            factors.append("⚠️ Radiation: GO WITH MONITORING")
        elif rad_norm in {"CAUTION"}:
            decisions.append(("CAUTION", "Radiation"))
            factors.append("⚠️ Radiation: CAUTION")
        elif rad_norm in {"NO GO", "NO_GO"}:
            decisions.append(("NO-GO", "Radiation"))
            factors.append("🚫 Radiation: NO-GO")
    
    # 3. Space Weather (S-Scale)
    if s_scale >= 4:
        decisions.append(("NO-GO", "S-Scale"))
        factors.append(f"🚫 S{s_scale} Radiation Storm: NO-GO (Extreme SPE hazard)")
    elif s_scale >= 3:
        decisions.append(("CAUTION", "S-Scale"))
        factors.append(f"⚠️ S{s_scale} Radiation Storm: CAUTION (Strong)")
    elif s_scale >= 2:
        decisions.append(("MONITOR", "S-Scale"))
        factors.append(f"⚠️ S{s_scale} Radiation Storm: MONITOR (Moderate)")
    elif s_scale >= 1:
        decisions.append(("MONITOR", "S-Scale"))
        factors.append(f"📡 S{s_scale} Radiation Storm: Active (Minor)")
    
    # 4. Space Weather (G-Scale)
    if g_scale >= 4:
        decisions.append(("CAUTION", "G-Scale"))
        factors.append(f"⚠️ G{g_scale} Geomagnetic Storm: CAUTION (Severe/Extreme)")
    elif g_scale >= 3:
        decisions.append(("MONITOR", "G-Scale"))
        factors.append(f"📡 G{g_scale} Geomagnetic Storm: MONITOR (Strong)")
    elif g_scale >= 1:
        factors.append(f"📡 G{g_scale} Geomagnetic Activity: Active")
    
    # Determine final decision (most restrictive wins)
    final_decision = "GO"
    final_priority = PRIORITY["GO"]
    for dec, source in decisions:
        if PRIORITY.get(dec, 1) > final_priority:
            final_decision = dec
            final_priority = PRIORITY[dec]
    
    # Build rationale
    if final_decision == "NO-GO":
        rationale = "EVA NOT CLEARED — Flight Surgeon or critical safety factor override"
    elif final_decision == "CAUTION":
        rationale = "EVA with CAUTION — Elevated risk, limit duration and tasks"
    elif final_decision == "MONITOR":
        rationale = "EVA with MONITORING — Enhanced oversight required"
    else:
        rationale = "EVA CLEARED — Nominal conditions"
    
    return final_decision, rationale, factors


def _render_eva_semaphore(
    eva_counts: pd.Series,
    *,
    joint_decision: Optional[str] = None,
    radiation_status: Optional[str] = None,
    s_scale: int = 0,
    g_scale: int = 0,
    flight_surgeon_clearance: Optional[str] = None,
    show_factors: bool = True,
) -> None:
    """Render a traffic-light semaphore for EVA clearance states.

    The semaphore reflects the joint decision from:
    - Flight Surgeon's clearance decision (authoritative)
    - EVA Radiation Risk Matrix assessment
    - Current Space Weather conditions (NOAA S/G scales)

    Args:
        eva_counts: Series indexed by ["GO", "MONITOR", "NO-GO"] with integer counts.
        joint_decision: Pre-computed joint decision override.
        radiation_status: EVA radiation assessment status.
        s_scale: NOAA S-scale (0-5).
        g_scale: NOAA G-scale (0-5).
        flight_surgeon_clearance: Flight surgeon's current EVA clearance.
        show_factors: Whether to show contributing factors breakdown.
    """
    # Extract counts from historical data (used for fallback logic)
    _go_count = int(eva_counts.get("GO", 0))
    monitor_count = int(eva_counts.get("MONITOR", 0))
    nogo_count = int(eva_counts.get("NO-GO", 0))

    # Compute joint decision if inputs are provided
    if joint_decision is None and flight_surgeon_clearance is not None:
        joint_decision, rationale, factors = _compute_joint_eva_decision(
            flight_surgeon_clearance=flight_surgeon_clearance,
            radiation_status=radiation_status,
            s_scale=s_scale,
            g_scale=g_scale,
        )
    else:
        # Fallback to historical counts-based dominant status
        if nogo_count > 0:
            joint_decision = "NO-GO"
        elif monitor_count > 0:
            joint_decision = "MONITOR"
        else:
            joint_decision = "GO"
        rationale = "Based on historical EVA status records"
        factors = []
    
    # Color mapping
    color_map = {
        "GO": "#16a34a",      # green-600
        "MONITOR": "#f59e0b", # amber-500
        "CAUTION": "#f97316", # orange-500
        "NO-GO": "#dc2626",   # red-600
    }
    dominant_color = color_map.get(joint_decision, "#6b7280")
    
    # Icon mapping
    icon_map = {
        "GO": "✅",
        "MONITOR": "⚠️",
        "CAUTION": "⚠️",
        "NO-GO": "🚫",
    }
    icon = icon_map.get(joint_decision, "❓")

    st.markdown("##### 🚦 EVA Clearance Semaphore")

    # Use columns to create a horizontal semaphore layout
    col_go, col_mon, col_caution, col_nogo = st.columns([1, 1, 1, 1])

    # Color logic: bright when active, dim when inactive
    go_active = joint_decision == "GO"
    mon_active = joint_decision == "MONITOR"
    caution_active = joint_decision == "CAUTION"
    nogo_active = joint_decision == "NO-GO"

    with col_go:
        bg = "#16a34a" if go_active else "#e5e7eb"
        text_color = "white" if go_active else "#9ca3af"
        st.markdown(
            f"""
            <div style="
                background: {bg};
                color: {text_color};
                border-radius: 50%;
                width: 70px;
                height: 70px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 800;
                font-size: 12px;
                letter-spacing: 0.5px;
                margin: auto;
                text-transform: uppercase;
                box-shadow: {'0 0 12px #16a34a' if go_active else 'none'};
            ">GO</div>
            """,
            unsafe_allow_html=True,
        )

    with col_mon:
        bg = "#f59e0b" if mon_active else "#e5e7eb"
        text_color = "white" if mon_active else "#9ca3af"
        st.markdown(
            f"""
            <div style="
                background: {bg};
                color: {text_color};
                border-radius: 50%;
                width: 70px;
                height: 70px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 800;
                font-size: 10px;
                letter-spacing: 0.5px;
                margin: auto;
                text-transform: uppercase;
                box-shadow: {'0 0 12px #f59e0b' if mon_active else 'none'};
            ">MONITOR</div>
            """,
            unsafe_allow_html=True,
        )

    with col_caution:
        bg = "#f97316" if caution_active else "#e5e7eb"
        text_color = "white" if caution_active else "#9ca3af"
        st.markdown(
            f"""
            <div style="
                background: {bg};
                color: {text_color};
                border-radius: 50%;
                width: 70px;
                height: 70px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 800;
                font-size: 10px;
                letter-spacing: 0.5px;
                margin: auto;
                text-transform: uppercase;
                box-shadow: {'0 0 12px #f97316' if caution_active else 'none'};
            ">CAUTION</div>
            """,
            unsafe_allow_html=True,
        )

    with col_nogo:
        bg = "#dc2626" if nogo_active else "#e5e7eb"
        text_color = "white" if nogo_active else "#9ca3af"
        st.markdown(
            f"""
            <div style="
                background: {bg};
                color: {text_color};
                border-radius: 50%;
                width: 70px;
                height: 70px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 800;
                font-size: 10px;
                letter-spacing: 0.5px;
                margin: auto;
                text-transform: uppercase;
                box-shadow: {'0 0 12px #dc2626' if nogo_active else 'none'};
            ">NO-GO</div>
            """,
            unsafe_allow_html=True,
        )

    # Joint Decision Summary (prominent display)
        st.markdown(
            f"""
            <div style="
            padding: 16px 20px;
            background: linear-gradient(135deg, {dominant_color}22 0%, {dominant_color}11 100%);
            border: 2px solid {dominant_color};
            border-radius: 12px;
                text-align: center;
            margin-top: 12px;
        ">
            <div style="
                font-size: 2rem;
                font-weight: 900;
                letter-spacing: 1px;
                text-transform: uppercase;
                color: {dominant_color};
                margin-bottom: 4px;
            ">{icon} {joint_decision}</div>
            <div style="
                font-size: 0.9rem;
                color: #4b5563;
            ">{rationale}</div>
            </div>
            """,
        unsafe_allow_html=True,
    )
    
    # Show contributing factors if available (using caption/markdown to avoid nested expanders)
    if show_factors and factors:
        st.markdown(
            """
            <details style="margin-top: 8px; padding: 8px; background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0;">
            <summary style="cursor: pointer; font-weight: 600; color: #475569;">📋 Contributing Factors</summary>
            <div style="padding-top: 8px;">
            """
            + "".join(f"<div style='padding: 2px 0; color: #374151;'>{factor}</div>" for factor in factors)
            + "</div></details>",
            unsafe_allow_html=True,
        )


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
    # Only clear the explicit logout flag on successful login.
    # Do NOT clear it when setting user=None, otherwise unrelated flows (e.g.,
    # profile deletion) can accidentally re-enable auto-profile selection.
    if user is not None:
        st.session_state["user_logged_out"] = False
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


def _logout_and_preserve() -> None:
    """Logout helper that preserves saved data and resets to guest view."""
    # Data is already persisted at save-time; no additional flush required here.
    
    # Clear user profile and user ID from session state
    current_id = st.session_state.get(_SESSION_USER_ID)
    st.session_state[_SESSION_CURRENT_USER] = None
    st.session_state.pop(_SESSION_USER_ID, None)
    st.session_state["user_logged_out"] = True
    
    # Clear UI mode flags
    st.session_state.pop("edit_profile_mode", None)
    
    # Set label to Guest
    st.session_state["active_profile_label"] = "Guest"
    
    # Clear any cached user-specific data
    st.session_state.pop("login_username", None)
    st.session_state.pop("login_password", None)
    st.session_state.pop("_persisted_uploads", None)
    st.session_state.pop("hrv_analysis_signature", None)
    st.session_state.pop("hrv_analysis_complete_signature", None)
    
    # Remove from multi-user session manager if present
    if MULTI_USER_AVAILABLE and current_id:
        try:
            manager = get_multi_user_manager()
            manager.remove_user_session(str(current_id))
        except Exception:
            pass  # best effort; do not block logout


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


def _parse_iso_utc(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse an ISO timestamp string into a timezone-aware UTC datetime."""
    if not dt_str:
        return None
    try:
        if dt_str.endswith("Z"):
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        parsed = datetime.fromisoformat(dt_str)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


def _compute_hours_since_wake(
    wake_dt: datetime, reference_dt: Optional[datetime] = None
) -> float:
    """Compute bounded hours since wake_dt relative to reference_dt (default now)."""
    ref_dt = reference_dt
    if ref_dt is None:
        ref_dt = datetime.now(timezone.utc) if wake_dt.tzinfo else datetime.now()
    if wake_dt.tzinfo and ref_dt.tzinfo:
        delta_seconds = (
            ref_dt.astimezone(timezone.utc) - wake_dt.astimezone(timezone.utc)
        ).total_seconds()
    else:
        if ref_dt.tzinfo and wake_dt.tzinfo is None:
            ref_dt = ref_dt.replace(tzinfo=None)
        delta_seconds = (ref_dt - wake_dt).total_seconds()
    if delta_seconds < 0:
        return 0.0
    hours = delta_seconds / 3600.0
    return float(round(max(0.0, min(48.0, hours)), 1))


def _get_bogota_tz() -> tzinfo:
    """Return Bogotá timezone (UTC-5) with ZoneInfo fallback."""
    try:
        return ZoneInfo("America/Bogota")
    except Exception:
        return timezone(timedelta(hours=-5))


def _format_tz_display(tz_value: tzinfo) -> str:
    """Return readable timezone name with UTC offset."""
    now_with_tz = datetime.now(tz_value)
    offset = now_with_tz.utcoffset() or timedelta(0)
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    hours, minutes = divmod(abs(total_minutes), 60)
    name = getattr(tz_value, "key", None) or now_with_tz.tzname() or "Local"
    return f"{name} (UTC{sign}{hours:02d}:{minutes:02d})"


def _coerce_garmin_record_dict(record: Any) -> Dict[str, Any]:
    """Coerce a Garmin daily metrics record into a dict."""
    if isinstance(record, dict):
        return dict(record)
    if is_dataclass(record):
        return asdict(record)
    if hasattr(record, "to_dict"):
        try:
            return record.to_dict()  # type: ignore[no-any-return]
        except Exception:
            return {}
    try:
        return dict(vars(record))
    except Exception:
        return {}


def _normalize_datetime_value(value: Any) -> Optional[str]:
    """Normalize datetime-like values to ISO strings for parsing."""
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime().isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return None


def _get_latest_garmin_daily_from_db(user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch the latest Garmin daily metrics row from the local database."""
    if not user_id:
        return None
    try:
        db = get_database()
    except Exception as exc:
        if log_exception:
            log_exception(_LOGGER, "Garmin DB lookup failed", exc)
        return None
    row: Optional[Dict[str, Any]] = None
    if hasattr(db, "get_garmin_daily_dataframe"):
        try:
            df = db.get_garmin_daily_dataframe(user_id, limit=1)  # type: ignore[attr-defined]
            if df is not None and not df.empty:
                row = df.iloc[0].to_dict()
        except Exception as exc:
            if log_exception:
                log_exception(_LOGGER, "Garmin DB dataframe lookup failed", exc)
    if row is None and hasattr(db, "get_garmin_daily_metrics"):
        try:
            rows = db.get_garmin_daily_metrics(user_id, limit=1)  # type: ignore[attr-defined]
            if rows:
                row = _coerce_garmin_record_dict(rows[0])
        except Exception as exc:
            if log_exception:
                log_exception(_LOGGER, "Garmin DB row lookup failed", exc)
    if not row:
        return None
    for key in ("metric_date", "sleep_start_utc", "sleep_end_utc", "created_at"):
        normalized = _normalize_datetime_value(row.get(key))
        if normalized is not None:
            row[key] = normalized
    return row


def _garmin_record_value(record: Any, key: str) -> Any:
    """Return a Garmin record field from dicts or dataclasses."""
    if isinstance(record, dict):
        return record.get(key)
    return getattr(record, key, None)


def _build_garmin_sleep_payload(
    record: Any,
    now_dt: datetime,
) -> Optional[Dict[str, float]]:
    """Build a sleep payload from a Garmin daily record."""
    sleep_hours_val = _safe_float(_garmin_record_value(record, "sleep_duration_hours"))
    if sleep_hours_val is None or sleep_hours_val <= 0.0:
        return None
    sleep_quality = None
    eff_val = _safe_float(_garmin_record_value(record, "sleep_efficiency"))
    if eff_val is not None:
        sleep_quality = eff_val if 0.0 <= eff_val <= 1.2 else eff_val / 100.0
    if sleep_quality is None:
        score_val = _safe_float(_garmin_record_value(record, "sleep_score"))
        if score_val is not None:
            sleep_quality = score_val / 100.0
    if sleep_quality is None:
        sleep_quality = 0.7
    sleep_quality = max(0.0, min(1.0, float(sleep_quality)))

    hours_awake = float(now_dt.hour - 7 if now_dt.hour >= 7 else now_dt.hour + 17)
    end_dt_raw = _garmin_record_value(record, "sleep_end_utc")
    end_dt = _parse_iso_utc(str(end_dt_raw)) if end_dt_raw else None
    if end_dt:
        hours_awake = _compute_hours_since_wake(end_dt, now_dt)

    rmssd_val = _safe_float(_garmin_record_value(record, "hrv_rmssd_ms"))
    resting_hr_val = _safe_float(_garmin_record_value(record, "resting_hr_bpm"))
    if resting_hr_val is None:
        resting_hr_val = _safe_float(_garmin_record_value(record, "avg_hr_bpm"))

    payload: Dict[str, float] = {
        "sleep_hours": round(float(sleep_hours_val), 2),
        "sleep_quality": round(float(sleep_quality), 2),
        "hours_awake": round(float(hours_awake), 2),
    }
    if rmssd_val is not None:
        payload["rmssd_ms"] = float(rmssd_val)
    if resting_hr_val is not None:
        payload["resting_hr"] = float(resting_hr_val)
    return payload


# ---------------------------------------------------------------------------
# Garmin Connect credentials (session-only; never written to disk)
# ---------------------------------------------------------------------------


def _session_garmin_credentials(user_id: str) -> Tuple[Optional[str], Optional[str]]:
    """Return UI-entered Garmin credentials held for this session, if present."""
    email = st.session_state.get(f"garmin_cred_email_{user_id}")
    password = st.session_state.get(f"garmin_cred_password_{user_id}")
    if email and password:
        return str(email), str(password)
    return None, None


def _fetch_garmin_daily_metrics_ui(user_id: str, days: int = 14):
    """fetch_garmin_daily_metrics with UI-entered (session) credentials injected.

    Falls back to env/.env inside the service when no session credentials exist,
    so the .env workflow keeps working unchanged. This is the single fetch entry
    point every Streamlit caller should use.
    """
    email, password = _session_garmin_credentials(user_id)
    return fetch_garmin_daily_metrics(user_id, days=days, email=email, password=password)


def _render_garmin_login_form(user_id: str) -> None:
    """Render the session-only Garmin Connect credential entry form.

    Credentials are validated immediately via login_and_get_display_name and
    stored only in st.session_state (never written to disk). A login token is
    cached by garth at ~/.garminconnect so the account stays connected without
    re-entering the password next time.
    """
    st.caption(
        "Enter your Garmin Connect credentials to sync. They are kept only for "
        "this session (never written to disk); a local login token is cached so "
        "you won't need to re-enter them next time."
    )
    with st.form(f"garmin_login_form_{user_id}", clear_on_submit=True):
        in_email = st.text_input("Garmin email", key=f"garmin_login_email_{user_id}")
        in_password = st.text_input(
            "Garmin password", type="password", key=f"garmin_login_password_{user_id}"
        )
        connect = st.form_submit_button("Connect", type="primary")
    if not connect:
        return
    email_clean = (in_email or "").strip()
    if not email_clean or not in_password:
        st.error("Enter both your Garmin email and password.")
        return
    try:
        with st.spinner("Connecting to Garmin Connect…"):
            display_name = login_and_get_display_name(email_clean, in_password)
    except GarminAuthError as exc:
        st.error(str(exc))
        return
    except Exception as exc:  # noqa: BLE001
        if log_exception is not None:
            log_exception(_LOGGER, "Garmin Connect login failed", exc)
        st.error(f"Garmin login failed: {exc}")
        return
    st.session_state[f"garmin_cred_email_{user_id}"] = email_clean
    st.session_state[f"garmin_cred_password_{user_id}"] = in_password
    st.session_state[f"garmin_connected_name_{user_id}"] = display_name or "Garmin user"
    st.success(f"Connected as {display_name or 'Garmin user'}.")
    st.rerun()


def _get_latest_garmin_sleep_payload(user: UserProfile, now_dt: datetime) -> Optional[Dict[str, float]]:
    """Fetch latest Garmin Vivosmart sleep metrics to feed SAFTE/HRV inputs."""
    if not user or not user.user_id:
        return None
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=_get_bogota_tz())
    else:
        now_dt = now_dt.astimezone(_get_bogota_tz())

    # Prefer locally stored Garmin daily metrics if available
    cached_row = _get_latest_garmin_daily_from_db(user.user_id)
    if cached_row:
        cached_payload = _build_garmin_sleep_payload(cached_row, now_dt)
        if cached_payload is not None:
            return cached_payload

    if fetch_garmin_daily_metrics is None:
        return None
    try:
        records = _fetch_garmin_daily_metrics_ui(user.user_id, days=7)
    except Exception as exc:  # pragma: no cover - defensive
        if log_exception:
            log_exception(_LOGGER, "Garmin autofill failed", exc)
        return None
    if not records:
        return None

    chosen = None
    for rec in sorted(records, key=lambda r: r.metric_date, reverse=True):
        if _safe_float(getattr(rec, "sleep_duration_hours", None)):
            chosen = rec
            break
    if chosen is None:
        return None

    return _build_garmin_sleep_payload(chosen, now_dt)


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
    error_state_key = "user_profile_login_error"
    selection_state_key = "user_profile_login_selected_username"
    
    with col_select:
        # Build options from cached data (avoiding full DB query)
        user_options = {
            str(u.get("username")): u
            for u in cached_users
            if isinstance(u, dict) and u.get("username")
        }
        usernames = list(user_options.keys())
        if not usernames:
            st.info("No users registered. Create a new profile below.")
            return None

        def _clear_login_error() -> None:
            st.session_state.pop(error_state_key, None)

        st.selectbox(
            "Select User",
            options=usernames,
            format_func=lambda x: f"{(user_options.get(x, {}).get('full_name') or x)} (@{x})",
            key=selection_state_key,
            on_change=_clear_login_error,
        )
    
    with col_action:
        st.write("")  # Spacing

        def _login_selected_user() -> None:
            """Login callback for the selected username (runs before rerun)."""
            raw_username = st.session_state.get(selection_state_key)
            username = str(raw_username).strip() if raw_username is not None else ""
            if not username:
                st.session_state[error_state_key] = "Select a user first."
                return

            try:
                db = get_database()
                user = db.get_user_by_username(username)
            except Exception as exc:  # pragma: no cover - defensive
                if log_exception is not None:
                    log_exception(_LOGGER, "User login failed", exc)
                else:
                    _LOGGER.exception("User login failed")
                st.session_state[error_state_key] = "Login failed. Check `logs/errors.log`."
                return

            if user is None:
                st.session_state[error_state_key] = (
                    f"User '@{username}' not found in the active mission database."
                )
                return

            _set_current_user(user)
            st.session_state.pop(error_state_key, None)

        st.button(
            "✅ Select User",
            key="user_profile_login_select_user_btn",
            use_container_width=True,
            on_click=_login_selected_user,
        )

    login_error = st.session_state.get(error_state_key)
    if login_error:
        st.error(str(login_error))
    
    return None


# ---------------------------------------------------------------------------
# BLE RR Interval Recorder
# ---------------------------------------------------------------------------


def _render_ble_rr_recorder(user: UserProfile) -> None:
    """Render BLE RR interval recording interface for Polar H10.
    
    This allows users to connect to a Polar H10 chest strap via Bluetooth
    and record RR intervals to a text file in the user's data directory.
    
    Args:
        user: Current user profile.
    """
    if not POLAR_RECORDER_AVAILABLE:
        return
    
    with st.expander("📡 BLE Heart Rate Recording (Polar H10)", expanded=False):
        # Check if bleak is available
        if not is_bleak_available():
            st.warning(
                "🔌 Bluetooth support requires the `bleak` library. "
                "Install with: `pip install bleak`"
            )
            st.code("pip install bleak", language="bash")
            return
        
        # Initialize session state for recorder
        recorder_key = f"ble_recorder_{user.user_id}"
        if recorder_key not in st.session_state:
            # Get output directory for user (based on full name)
            output_dir = get_output_directory(user.full_name or user.username)
            st.session_state[recorder_key] = {
                "recorder": None,
                "output_dir": str(output_dir),
                "devices": [],
                "selected_device_idx": 0,
                "is_scanning": False,
                "is_connecting": False,
                "is_recording": False,
                "last_hr": 0.0,
                "last_rr": 0.0,
                "rr_count": 0,
                "duration": 0.0,
                "file_path": None,
                "error_msg": None,
            }
        
        state = st.session_state[recorder_key]
        
        # Output directory info
        st.caption(f"📁 Recording directory: `{state['output_dir']}`")
        
        # Get or create recorder instance
        recorder: PolarH10RecorderSync | None = state.get("recorder")
        if recorder is None:
            recorder = PolarH10RecorderSync(output_dir=state["output_dir"])
            state["recorder"] = recorder
        
        # Connection status
        status_col, action_col = st.columns([2, 1])
        
        with status_col:
            if recorder.is_recording:
                st.success("🔴 Recording in progress")
            elif recorder.is_connected:
                st.success("🟢 Connected")
            else:
                st.info("⚪ Not connected")
        
        # Error display
        if state.get("error_msg"):
            st.error(state["error_msg"])
            if st.button("Clear Error", key=f"clear_ble_error_{user.user_id}"):
                state["error_msg"] = None
                safe_rerun("profile_tab_rerun")
        
        # --- Scan Section ---
        if not recorder.is_connected and not state.get("is_scanning"):
            st.markdown("#### 1️⃣ Scan for Devices")
            st.caption("Make sure your Polar H10 is worn and in range.")
            
            scan_col1, scan_col2 = st.columns([1, 2])
            with scan_col1:
                if st.button("🔍 Scan", key=f"ble_scan_{user.user_id}", use_container_width=True):
                    state["is_scanning"] = True
                    state["error_msg"] = None
                    safe_rerun("profile_tab_rerun")
            
            # Show previously found devices
            if state["devices"]:
                device_names = [f"{d.name} ({d.rssi} dBm)" for d in state["devices"]]
                selected_idx = st.selectbox(
                    "Select Device",
                    options=range(len(device_names)),
                    format_func=lambda i: device_names[i],
                    key=f"ble_device_select_{user.user_id}",
                )
                state["selected_device_idx"] = selected_idx
                
                if st.button("🔗 Connect", key=f"ble_connect_{user.user_id}", use_container_width=True):
                    state["is_connecting"] = True
                    safe_rerun("profile_tab_rerun")
        
        # Handle scanning (separate from UI)
        if state.get("is_scanning"):
            with st.spinner("Scanning for BLE devices..."):
                try:
                    devices = recorder.scan_devices(timeout=10.0)
                    state["devices"] = devices
                    state["is_scanning"] = False
                    if not devices:
                        state["error_msg"] = "No heart rate monitors found. Ensure device is active."
                except Exception as exc:
                    state["error_msg"] = f"Scan failed: {exc}"
                    state["is_scanning"] = False
                safe_rerun("profile_tab_rerun")
        
        # Handle connection (separate from UI)
        if state.get("is_connecting"):
            with st.spinner("Connecting..."):
                try:
                    idx = state.get("selected_device_idx", 0)
                    if state["devices"] and 0 <= idx < len(state["devices"]):
                        device = state["devices"][idx]
                        success = recorder.connect(device)
                        if success:
                            state["error_msg"] = None
                        else:
                            state["error_msg"] = "Connection failed. Try again."
                    state["is_connecting"] = False
                except Exception as exc:
                    state["error_msg"] = f"Connection error: {exc}"
                    state["is_connecting"] = False
                safe_rerun("profile_tab_rerun")
        
        # --- Connected Section ---
        if recorder.is_connected:
            # Device info
            st.markdown("#### 2️⃣ Record RR Intervals")
            
            # Battery level (optional)
            try:
                battery = recorder.get_battery_level()
                if battery is not None:
                    st.caption(f"🔋 Battery: {battery}%")
            except Exception:
                pass
            
            # Recording controls
            rec_col1, rec_col2 = st.columns(2)
            
            with rec_col1:
                if not recorder.is_recording:
                    if st.button(
                        "▶️ Start Recording",
                        key=f"ble_start_rec_{user.user_id}",
                        use_container_width=True,
                        type="primary",
                    ):
                        try:
                            success = recorder.start_recording()
                            if success:
                                state["is_recording"] = True
                                state["error_msg"] = None
                            else:
                                state["error_msg"] = "Failed to start recording"
                        except Exception as exc:
                            state["error_msg"] = f"Start error: {exc}"
                        safe_rerun("profile_tab_rerun")
                else:
                    if st.button(
                        "⏹️ Stop Recording",
                        key=f"ble_stop_rec_{user.user_id}",
                        use_container_width=True,
                        type="primary",
                    ):
                        try:
                            filepath = recorder.stop_recording()
                            state["is_recording"] = False
                            state["file_path"] = filepath
                            state["error_msg"] = None
                            st.success(f"✅ Recording saved: `{filepath}`")
                        except Exception as exc:
                            state["error_msg"] = f"Stop error: {exc}"
                        safe_rerun("profile_tab_rerun")
            
            with rec_col2:
                if st.button(
                    "🔌 Disconnect",
                    key=f"ble_disconnect_{user.user_id}",
                    use_container_width=True,
                ):
                    try:
                        recorder.disconnect()
                        state["is_recording"] = False
                    except Exception as exc:
                        state["error_msg"] = f"Disconnect error: {exc}"
                    safe_rerun("profile_tab_rerun")
            
            # Recording stats
            if recorder.is_recording:
                stats = recorder.stats
                
                # Metrics display
                m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                with m_col1:
                    st.metric("RR Count", f"{stats.rr_count:,}")
                with m_col2:
                    st.metric("Last HR", f"{stats.last_hr:.0f} bpm")
                with m_col3:
                    st.metric("Last RR", f"{stats.last_rr:.0f} ms")
                with m_col4:
                    mins = stats.duration_sec / 60
                    st.metric("Duration", f"{mins:.1f} min")
                
                # Refresh button for live updates
                if st.button("🔄 Refresh Stats", key=f"ble_refresh_{user.user_id}"):
                    safe_rerun("profile_tab_rerun")
                
                st.caption(f"📁 Saving to: `{stats.file_path}`")
        
        # --- Recent Recordings ---
        st.markdown("---")
        st.markdown("#### 📚 Recent Recordings")
        
        recordings = list_recordings(state["output_dir"])
        if recordings:
            # Show last 5 recordings
            for rec in recordings[:5]:
                rec_size = rec.stat().st_size
                rec_lines = rec_size // 4  # Approximate line count
                st.caption(f"• `{rec.name}` ({rec_lines:,} RR intervals)")
        else:
            st.caption("No recordings yet.")


def _render_ble_rr_recorder_guest() -> None:
    """Render BLE RR interval recording interface for Guest users.
    
    This allows guests to connect to a Polar H10 chest strap and record
    RR intervals without needing to create a user profile first.
    
    Files are saved to a 'Guest' directory.
    """
    if not POLAR_RECORDER_AVAILABLE:
        return
    
    with st.expander("📡 BLE Heart Rate Recording (Polar H10)", expanded=False):
        # Check if bleak is available
        if not is_bleak_available():
            st.warning(
                "🔌 Bluetooth support requires the `bleak` library. "
                "Install with: `pip install bleak`"
            )
            st.code("pip install bleak", language="bash")
            return
        
        # Initialize session state for guest recorder
        recorder_key = "ble_recorder_guest"
        if recorder_key not in st.session_state:
            # Guest output directory
            output_dir = get_output_directory("Guest")
            st.session_state[recorder_key] = {
                "recorder": None,
                "output_dir": str(output_dir),
                "devices": [],
                "selected_device_idx": 0,
                "is_scanning": False,
                "is_connecting": False,
                "is_recording": False,
                "last_hr": 0.0,
                "last_rr": 0.0,
                "rr_count": 0,
                "duration": 0.0,
                "file_path": None,
                "error_msg": None,
            }
        
        state = st.session_state[recorder_key]
        
        # Output directory info
        st.caption(f"📁 Recording directory: `{state['output_dir']}`")
        st.caption("💡 Tip: Log in or register to save recordings to your personal folder.")
        
        # Get or create recorder instance
        recorder: PolarH10RecorderSync | None = state.get("recorder")
        if recorder is None:
            recorder = PolarH10RecorderSync(output_dir=state["output_dir"])
            state["recorder"] = recorder
        
        # Connection status
        status_col, _ = st.columns([2, 1])
        
        with status_col:
            if recorder.is_recording:
                st.success("🔴 Recording in progress")
            elif recorder.is_connected:
                st.success("🟢 Connected")
            else:
                st.info("⚪ Not connected")
        
        # Error display
        if state.get("error_msg"):
            st.error(state["error_msg"])
            if st.button("Clear Error", key="clear_ble_error_guest"):
                state["error_msg"] = None
                safe_rerun("profile_tab_rerun")
        
        # --- Scan Section ---
        if not recorder.is_connected and not state.get("is_scanning"):
            st.markdown("#### 1️⃣ Scan for Devices")
            st.caption("Make sure your Polar H10 is worn and in range.")
            
            scan_col1, scan_col2 = st.columns([1, 2])
            with scan_col1:
                if st.button("🔍 Scan", key="ble_scan_guest", use_container_width=True):
                    state["is_scanning"] = True
                    state["error_msg"] = None
                    safe_rerun("profile_tab_rerun")
            
            # Show previously found devices
            if state["devices"]:
                device_names = [f"{d.name} ({d.rssi} dBm)" for d in state["devices"]]
                selected_idx = st.selectbox(
                    "Select Device",
                    options=range(len(device_names)),
                    format_func=lambda i: device_names[i],
                    key="ble_device_select_guest",
                )
                state["selected_device_idx"] = selected_idx
                
                if st.button("🔗 Connect", key="ble_connect_guest", use_container_width=True):
                    state["is_connecting"] = True
                    safe_rerun("profile_tab_rerun")
        
        # Handle scanning (separate from UI)
        if state.get("is_scanning"):
            with st.spinner("Scanning for BLE devices..."):
                try:
                    devices = recorder.scan_devices(timeout=10.0)
                    state["devices"] = devices
                    state["is_scanning"] = False
                    if not devices:
                        state["error_msg"] = "No heart rate monitors found. Ensure device is active."
                except Exception as exc:
                    state["error_msg"] = f"Scan failed: {exc}"
                    state["is_scanning"] = False
                safe_rerun("profile_tab_rerun")
        
        # Handle connection (separate from UI)
        if state.get("is_connecting"):
            with st.spinner("Connecting..."):
                try:
                    idx = state.get("selected_device_idx", 0)
                    if state["devices"] and 0 <= idx < len(state["devices"]):
                        device = state["devices"][idx]
                        success = recorder.connect(device)
                        if success:
                            state["error_msg"] = None
                        else:
                            state["error_msg"] = "Connection failed. Try again."
                    state["is_connecting"] = False
                except Exception as exc:
                    state["error_msg"] = f"Connection error: {exc}"
                    state["is_connecting"] = False
                safe_rerun("profile_tab_rerun")
        
        # --- Connected Section ---
        if recorder.is_connected:
            # Device info
            st.markdown("#### 2️⃣ Record RR Intervals")
            
            # Battery level (optional)
            try:
                battery = recorder.get_battery_level()
                if battery is not None:
                    st.caption(f"🔋 Battery: {battery}%")
            except Exception:
                pass
            
            # Recording controls
            rec_col1, rec_col2 = st.columns(2)
            
            with rec_col1:
                if not recorder.is_recording:
                    if st.button(
                        "▶️ Start Recording",
                        key="ble_start_rec_guest",
                        use_container_width=True,
                        type="primary",
                    ):
                        try:
                            success = recorder.start_recording()
                            if success:
                                state["is_recording"] = True
                                state["error_msg"] = None
                            else:
                                state["error_msg"] = "Failed to start recording"
                        except Exception as exc:
                            state["error_msg"] = f"Start error: {exc}"
                        safe_rerun("profile_tab_rerun")
                else:
                    if st.button(
                        "⏹️ Stop Recording",
                        key="ble_stop_rec_guest",
                        use_container_width=True,
                        type="primary",
                    ):
                        try:
                            filepath = recorder.stop_recording()
                            state["is_recording"] = False
                            state["file_path"] = filepath
                            state["error_msg"] = None
                            st.success(f"✅ Recording saved: `{filepath}`")
                        except Exception as exc:
                            state["error_msg"] = f"Stop error: {exc}"
                        safe_rerun("profile_tab_rerun")
            
            with rec_col2:
                if st.button(
                    "🔌 Disconnect",
                    key="ble_disconnect_guest",
                    use_container_width=True,
                ):
                    try:
                        recorder.disconnect()
                        state["is_recording"] = False
                    except Exception as exc:
                        state["error_msg"] = f"Disconnect error: {exc}"
                    safe_rerun("profile_tab_rerun")
            
            # Recording stats
            if recorder.is_recording:
                stats = recorder.stats
                
                # Metrics display
                m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                with m_col1:
                    st.metric("RR Count", f"{stats.rr_count:,}")
                with m_col2:
                    st.metric("Last HR", f"{stats.last_hr:.0f} bpm")
                with m_col3:
                    st.metric("Last RR", f"{stats.last_rr:.0f} ms")
                with m_col4:
                    mins = stats.duration_sec / 60
                    st.metric("Duration", f"{mins:.1f} min")
                
                # Refresh button for live updates
                if st.button("🔄 Refresh Stats", key="ble_refresh_guest"):
                    safe_rerun("profile_tab_rerun")
                
                st.caption(f"📁 Saving to: `{stats.file_path}`")
        
        # --- Recent Recordings ---
        st.markdown("---")
        st.markdown("#### 📚 Recent Recordings")
        
        recordings = list_recordings(state["output_dir"])
        if recordings:
            # Show last 5 recordings
            for rec in recordings[:5]:
                rec_size = rec.stat().st_size
                rec_lines = rec_size // 4  # Approximate line count
                st.caption(f"• `{rec.name}` ({rec_lines:,} RR intervals)")
        else:
            st.caption("No recordings yet.")


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
        safe_rerun("profile_tab_rerun")
    
    # BLE RR Interval Recording Section
    _render_ble_rr_recorder(user)


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
                    safe_rerun("profile_tab_rerun")
                except Exception as exc:
                    st.error(f"Failed to update: {exc}")
        
        with col_cancel:
            if st.form_submit_button("❌ Cancel"):
                st.session_state["edit_profile_mode"] = False
                safe_rerun("profile_tab_rerun")


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
    
    # Session state keys for context inputs (used by both Garmin autofill and form widgets)
    # IMPORTANT: These keys are used directly by the st.number_input widgets
    ctx_hours_wake_key = f"clinical_hours_wake_{user.user_id}"
    ctx_hours_sleep_key = f"clinical_hours_sleep_{user.user_id}"
    ctx_caffeine_key = f"clinical_caffeine_{user.user_id}"
    ctx_wake_time_key = f"clinical_wake_dt_{user.user_id}"
    ctx_wake_time_input_key = f"clinical_wake_time_input_{user.user_id}"
    local_tz = _get_bogota_tz()
    
    # Initialize defaults only if keys don't exist
    if ctx_hours_wake_key not in st.session_state:
        st.session_state[ctx_hours_wake_key] = 8.0
    if ctx_hours_sleep_key not in st.session_state:
        st.session_state[ctx_hours_sleep_key] = 7.0
    if ctx_caffeine_key not in st.session_state:
        st.session_state[ctx_caffeine_key] = 1
    if ctx_wake_time_key not in st.session_state:
        default_wake_dt = datetime.now(tz=local_tz) - timedelta(
            hours=float(st.session_state[ctx_hours_wake_key])
        )
        st.session_state[ctx_wake_time_key] = default_wake_dt
    wake_dt_val = st.session_state.get(ctx_wake_time_key)
    if isinstance(wake_dt_val, datetime):
        wake_dt_local = (
            wake_dt_val.astimezone(local_tz)
            if wake_dt_val.tzinfo
            else wake_dt_val.replace(tzinfo=local_tz)
        )
        st.session_state[ctx_wake_time_key] = wake_dt_local
    
    # Garmin autofill section (outside form)
    st.markdown("#### 📊 Assessment Context")
    col_garmin_btn, col_garmin_status = st.columns([1, 2])
    with col_garmin_btn:
        fetch_garmin_context = st.button(
            "📡 Fetch from Garmin",
            key=f"clinical_fetch_garmin_{user.user_id}",
            help="Pull sleep duration and wake time from your latest Garmin daily metrics.",
        )
    
    if fetch_garmin_context:
        try:
            db = get_database()
            garmin_rows = db.get_garmin_daily_metrics(user.user_id, limit=1)
            if garmin_rows:
                latest_entry = garmin_rows[0]
                latest: Dict[str, Any]
                if isinstance(latest_entry, dict):
                    latest = latest_entry
                elif is_dataclass(latest_entry):
                    latest = asdict(latest_entry)
                elif hasattr(latest_entry, "to_dict"):
                    latest = latest_entry.to_dict()  # type: ignore[assignment]
                else:
                    try:
                        latest = vars(latest_entry)
                    except TypeError:
                        latest = {}
                updated_fields = []
                
                # Sleep duration
                sleep_dur = latest.get("sleep_duration_hours")
                if sleep_dur is not None and isinstance(sleep_dur, (int, float)):
                    st.session_state[ctx_hours_sleep_key] = float(max(0.0, min(24.0, round(float(sleep_dur), 1))))
                    updated_fields.append(f"Sleep: {st.session_state[ctx_hours_sleep_key]:.1f}h")
                
                # Calculate hours since waking from sleep end time
                sleep_end_utc = latest.get("sleep_end_utc")
                if sleep_end_utc:
                    parsed_end = _parse_iso_utc(str(sleep_end_utc))
                    if parsed_end is not None:
                        parsed_local_end = parsed_end.astimezone(local_tz)
                        st.session_state[ctx_wake_time_key] = parsed_local_end
                        computed_hours = _compute_hours_since_wake(
                            parsed_local_end, datetime.now(tz=local_tz)
                        )
                        st.session_state[ctx_hours_wake_key] = computed_hours
                        updated_fields.append(
                            f"Wake: {parsed_local_end.strftime('%H:%M %Z')}"
                        )
                        updated_fields.append(
                            f"Awake: {st.session_state[ctx_hours_wake_key]:.1f}h"
                        )
                
                if updated_fields:
                    with col_garmin_status:
                        st.success(f"✅ Garmin data loaded: {', '.join(updated_fields)}")
                else:
                    with col_garmin_status:
                        st.warning("⚠️ No sleep data found in latest Garmin metrics.")
            else:
                with col_garmin_status:
                    st.info("ℹ️ No Garmin daily metrics stored. Sync Garmin data first in the Garmin Integration section.")
        except Exception as exc:
            if log_exception is not None:
                log_exception(_LOGGER, "Clinical assessment Garmin fetch failed", exc)
            with col_garmin_status:
                st.error(f"❌ Failed to fetch Garmin data: {exc}")
    
    st.caption("💡 Click 'Fetch from Garmin' to auto-populate sleep context, or enter values manually below.")
    
    form_key = f"clinical_assessment_form_{user.user_id}"
    results: Dict[str, Any] = {}
    context_data: Dict[str, Any] = {}
    notes_text = ""
    
    with st.form(form_key, clear_on_submit=False):
        with st.expander(t('assessment_context'), expanded=True):
            stored_wake_dt = st.session_state.get(ctx_wake_time_key)
            now_local = datetime.now(tz=local_tz)
            st.caption(f"Timezone detected: {_format_tz_display(local_tz)}")
            if isinstance(stored_wake_dt, datetime):
                stored_wake_local = (
                    stored_wake_dt.astimezone(local_tz)
                    if stored_wake_dt.tzinfo
                    else stored_wake_dt.replace(tzinfo=local_tz)
                )
            else:
                stored_wake_local = now_local - timedelta(
                    hours=float(st.session_state[ctx_hours_wake_key])
                )
                st.session_state[ctx_wake_time_key] = stored_wake_local
            wake_time_value = stored_wake_local.time()
            wake_time_today = st.time_input(
                "Wake time today",
                value=wake_time_value,
                key=ctx_wake_time_input_key,
                help="Used to compute hours awake (current time minus wake time).",
            )
            wake_dt_today = datetime.combine(
                date.today(), wake_time_today, tzinfo=local_tz
            )
            st.session_state[ctx_wake_time_key] = wake_dt_today
            hours_since_wake_val = _compute_hours_since_wake(
                wake_dt_today, datetime.now(tz=local_tz)
            )
            
            col1, col2, col3 = st.columns(3)
            with col1:
                hours_since_wake = float(hours_since_wake_val)
                st.metric(t('hours_since_waking'), f"{hours_since_wake:.1f} h")
                st.caption("Calculated from wake time and current clock time.")
            with col2:
                hours_sleep = st.number_input(
                    t('hours_slept'),
                    min_value=0.0,
                    max_value=24.0,
                    value=float(st.session_state[ctx_hours_sleep_key]),
                    step=0.5,
                    key=ctx_hours_sleep_key,
                )
            with col3:
                caffeine_cups = st.number_input(
                    t('caffeine_today'),
                    min_value=0,
                    max_value=20,
                    value=int(st.session_state[ctx_caffeine_key]),
                    step=1,
                    key=ctx_caffeine_key,
                )
            st.caption(
                f"Hours awake ({hours_since_wake:.1f}h) "
                f"= now ({datetime.now(tz=local_tz).strftime('%H:%M')}) minus wake "
                f"time ({wake_time_today.strftime('%H:%M')})."
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
    # Note: _session_ready_guard() was previously here but now always returns True
    # so no early return is needed.
    st.markdown("## 📈 Assessment History")
    
    # Use module-level cached loader (defined at top of file) for stable caching
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
        
        # Publication-quality Fatigue & Sleepiness trends chart
        if len(df) > 1:
            chart_cols = ["samn_perelli_fatigue", "karolinska_sleepiness_scale"]
            available_cols = [c for c in chart_cols if c in df.columns]
            if available_cols:
                chart_data = df[["assessment_date"] + available_cols].dropna(how="all", subset=available_cols)
                if not chart_data.empty:
                    chart_data = chart_data.sort_values("assessment_date")
                    dates_list = [str(d)[:10] for d in chart_data["assessment_date"].tolist()]
                    sp_data = (
                        chart_data["samn_perelli_fatigue"].tolist()
                        if "samn_perelli_fatigue" in chart_data.columns
                        else None
                    )
                    kss_data = (
                        chart_data["karolinska_sleepiness_scale"].tolist()
                        if "karolinska_sleepiness_scale" in chart_data.columns
                        else None
                    )
                    fatigue_chart = _build_fatigue_sleepiness_chart(
                        dates=dates_list,
                        samn_perelli=sp_data,
                        karolinska=kss_data,
                        title="Fatigue & Sleepiness Trends",
                    )
                    render_echarts(fatigue_chart, height_px=380)
                    st.markdown(
                        "*Samn-Perelli (SP): 1-7 fatigue scale used in aviation medicine. "
                        "Karolinska (KSS): 1-9 sleepiness scale. Scores >5.5 suggest "
                        "fatigue-related performance impairment.* "
                        "*(Samn & Perelli, 1982; Åkerstedt & Gillberg, 1990)*"
                    )
            
            # Publication-quality PANAS Affect trends chart
            panas_cols = ["panas_positive_affect", "panas_negative_affect"]
            available_panas = [c for c in panas_cols if c in df.columns]
            if available_panas and df[available_panas].notna().any().any():
                panas_data = df[["assessment_date"] + available_panas].dropna(how="all", subset=available_panas)
                if not panas_data.empty:
                    panas_data = panas_data.sort_values("assessment_date")
                    panas_dates = [str(d)[:10] for d in panas_data["assessment_date"].tolist()]
                    pa_data = (
                        panas_data["panas_positive_affect"].tolist()
                        if "panas_positive_affect" in panas_data.columns
                        else None
                    )
                    na_data = (
                        panas_data["panas_negative_affect"].tolist()
                        if "panas_negative_affect" in panas_data.columns
                        else None
                    )
                    panas_chart = _build_panas_affect_chart(
                        dates=panas_dates,
                        positive_affect=pa_data,
                        negative_affect=na_data,
                        title="PANAS Affect Trends",
                    )
                    render_echarts(panas_chart, height_px=380)
                    st.markdown(
                        "*PANAS measures Positive Affect (PA: enthusiasm, interest) and "
                        "Negative Affect (NA: distress, hostility). Goal: PA >35, NA <17. "
                        "Persistent low PA or high NA may indicate mood concerns.* "
                        "*(Watson et al., 1988; Crawford & Henry, 2004)*"
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


# Module-level cached loader for Garmin history (moved outside render function for stable caching)
@st.cache_data(ttl=300, max_entries=64, show_spinner=False)
def _load_garmin_history_cached(uid: str, limit: int, refresh: int) -> pd.DataFrame:
    """Load Garmin daily metrics DataFrame from database with caching.
    
    This function is intentionally at module level (not inside a render function)
    to ensure the cache decorator works correctly across reruns.
    
    Args:
        uid: User ID.
        limit: Maximum number of days to load.
        refresh: Cache-busting token (increment to force refresh).
        
    Returns:
        DataFrame with Garmin daily metrics.
    """
    _ = refresh  # Used only to bust cache when explicitly requested
    db = get_database()
    if hasattr(db, "get_garmin_daily_dataframe"):
        return db.get_garmin_daily_dataframe(uid, limit=int(limit))  # type: ignore[attr-defined]
    if hasattr(db, "get_garmin_daily_metrics"):
        metrics = db.get_garmin_daily_metrics(uid, limit=int(limit))  # type: ignore[attr-defined]
        if not metrics:
            return pd.DataFrame()
        return pd.DataFrame([m.to_dict() for m in metrics])
    return pd.DataFrame()


@_fragment_if_available
def _render_garmin_metrics_history(user: UserProfile) -> None:
    """Render wrist-wearable wellness/activity history with gauges."""
    st.markdown("## ⌚ Wrist Monitoring")

    # Cache-busting token for wrist monitoring history.
    # This avoids stale charts after new Garmin imports without clearing *all* cache_data.
    refresh_state_key = f"garmin_history_refresh_token:{user.user_id}"
    refresh_token_raw = st.session_state.get(refresh_state_key, 0)
    try:
        refresh_token = int(refresh_token_raw) if refresh_token_raw is not None else 0
    except (TypeError, ValueError):
        refresh_token = 0
    
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
                    # Note: Don't increment refresh_token here to avoid session state
                    # changes during render. The user can click "Refresh" if needed.
                    # The data is saved to DB and will be visible on next explicit refresh.
                    st.toast(f"Saved {len(entries)} Garmin metric(s). Click Refresh to update charts.")
        except Exception as exc:  # noqa: BLE001
            if log_exception is not None:
                log_exception(_LOGGER, "Failed to persist sidebar Garmin metrics", exc)

    # Live Garmin Connect fetch (manual button; requires the garminconnect library).
    # Credentials come from the UI session (entered below) or, as a fallback,
    # from GARMIN_EMAIL / GARMIN_PASSWORD in the environment / .env.
    session_email, session_password = _session_garmin_credentials(user.user_id)
    env_creds_ready = bool(os.getenv("GARMIN_EMAIL")) and bool(os.getenv("GARMIN_PASSWORD"))
    api_creds_ready = GARMIN_LIB_AVAILABLE and (
        env_creds_ready or bool(session_email and session_password)
    )
    with st.expander("🔄 Import from Garmin Connect (Vivosmart 5)", expanded=False):
        if not GARMIN_LIB_AVAILABLE:
            st.info("Install `garminconnect` to enable live Garmin imports (see requirements.txt).")
        elif not api_creds_ready:
            _render_garmin_login_form(user.user_id)
        else:
            if session_email and session_password:
                connected_name = st.session_state.get(
                    f"garmin_connected_name_{user.user_id}", "Garmin user"
                )
                status_col, disconnect_col = st.columns([3, 1])
                with status_col:
                    st.success(f"✅ Connected as {connected_name}")
                with disconnect_col:
                    if st.button("Disconnect", key=f"garmin_disconnect_{user.user_id}"):
                        for _suffix in (
                            "garmin_cred_email_",
                            "garmin_cred_password_",
                            "garmin_connected_name_",
                        ):
                            st.session_state.pop(f"{_suffix}{user.user_id}", None)
                        st.rerun()
            else:
                st.caption("Using Garmin credentials from the environment (.env).")

            latest_metric_date: Optional[date] = None
            missing_days: Optional[int] = None
            try:
                db = get_database()
                if hasattr(db, "get_garmin_daily_metrics"):
                    latest_metrics = db.get_garmin_daily_metrics(user.user_id, limit=1)
                    if latest_metrics:
                        parsed = pd.to_datetime(latest_metrics[0].metric_date, errors="coerce")
                        if parsed is not None and not pd.isna(parsed):
                            latest_metric_date = parsed.date()
            except Exception:
                latest_metric_date = None

            if latest_metric_date is not None:
                today = date.today()
                missing_days = max(0, (today - latest_metric_date).days)
                if missing_days == 0:
                    st.caption(f"Latest stored date: {latest_metric_date} (up to date).")
                else:
                    st.caption(
                        f"Latest stored date: {latest_metric_date} "
                        f"({missing_days} day(s) behind today)."
                    )

            fetch_options = [7, 14, 30, 60, 90]
            default_days = 14
            if missing_days is not None and missing_days > 0:
                for opt in fetch_options:
                    if opt >= missing_days:
                        default_days = opt
                        break
                else:
                    default_days = fetch_options[-1]

            days_to_fetch = st.select_slider(
                "Days to fetch (includes today)",
                options=fetch_options,
                value=default_days,
                key=f"garmin_api_days_{user.user_id}",
            )

            def _run_garmin_fetch(days_requested: int) -> None:
                nonlocal refresh_token
                try:
                    with st.spinner(f"Fetching last {days_requested} day(s) from Garmin Connect…"):
                        records = _fetch_garmin_daily_metrics_ui(user.user_id, days=int(days_requested))
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
                        refresh_token += 1
                        st.session_state[refresh_state_key] = refresh_token
                        summary = summarize_garmin_daily(records)
                        label = summary.get("dates", "")
                        st.success(
                            f"Imported {summary.get('count', len(records))} day(s) from Garmin Connect. {label}"
                        )

            col_fetch, col_catchup = st.columns(2)
            with col_fetch:
                if st.button(
                    "Fetch from Garmin Connect",
                    key=f"garmin_api_fetch_{user.user_id}",
                    type="primary",
                ):
                    _run_garmin_fetch(int(days_to_fetch))
            with col_catchup:
                catchup_disabled = missing_days is None or missing_days <= 0
                catchup_help = (
                    "No missing days detected."
                    if catchup_disabled
                    else f"Fetch the last {min(missing_days, 90)} day(s) to catch up."
                )
                if st.button(
                    "Fetch missing days",
                    key=f"garmin_api_fetch_missing_{user.user_id}",
                    disabled=catchup_disabled,
                    help=catchup_help,
                ):
                    _run_garmin_fetch(int(min(missing_days or 0, 90)))

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

    col_refresh, col_meta = st.columns([1, 3])
    with col_refresh:
        if st.button(
            "🔄 Refresh wrist metrics",
            key=f"garmin_history_refresh_{user.user_id}",
            help="Reload stored Garmin daily metrics from the mission database.",
        ):
            refresh_token += 1
            st.session_state[refresh_state_key] = refresh_token
    with col_meta:
        st.caption("If values look stale after a sync/import, click refresh.")

    # Use module-level cached function instead of defining inside render
    try:
        df = _load_garmin_history_cached(user.user_id, int(history_limit), refresh_token)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Unable to load Garmin history: {exc}")
        return

    # Derive sleep efficiency when missing by computing (sleep_duration / time_in_bed)*100
    def _compute_sleep_efficiency(row: pd.Series) -> float | None:
        """Compute sleep efficiency as (sleep duration / time in bed) * 100."""
        duration_h = _safe_float(row.get("sleep_duration_hours"))
        start_ts = row.get("sleep_start_utc")
        end_ts = row.get("sleep_end_utc")
        if duration_h is None or start_ts is None or end_ts is None:
            return None
        try:
            start_dt = pd.to_datetime(start_ts, utc=True, errors="coerce")
            end_dt = pd.to_datetime(end_ts, utc=True, errors="coerce")
        except Exception:
            return None
        if start_dt is None or end_dt is None or pd.isna(start_dt) or pd.isna(end_dt):
            return None
        time_in_bed_hours = (end_dt - start_dt).total_seconds() / 3600.0
        if time_in_bed_hours <= 0:
            return None
        efficiency = (duration_h / time_in_bed_hours) * 100.0
        # Clamp to a reasonable range
        return float(max(0.0, min(100.0, efficiency)))

    if "sleep_efficiency" not in df.columns:
        df["sleep_efficiency"] = pd.NA
    missing_eff = df["sleep_efficiency"].isna()
    if bool(missing_eff.any()):
        df.loc[missing_eff, "sleep_efficiency"] = (
            df.loc[missing_eff].apply(_compute_sleep_efficiency, axis=1)
        )

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
    show_gauges = True
    show_trends = True
    show_stats = True
    show_table = True
    show_advanced = True

    # Render gauges in organized sections
    if show_gauges:
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
    if show_stats or show_trends:
        st.markdown("### 📊 Statistical Analysis")
    
    # Summary statistics (computed from DB history; includes all supported Garmin fields)
    if show_stats:
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
    # Publication-quality charts with physiological context
    if show_trends:
        # Build a time-indexed view for charts (ascending time)
        df_ts = df.copy()
        if "metric_date" in df_ts.columns:
            df_ts = df_ts.sort_values("metric_date", ascending=True).set_index("metric_date")

        if len(df_ts) > 1 and isinstance(df_ts.index, pd.DatetimeIndex):
            st.markdown("#### Trends Over Time")
            st.caption(
                "**Scientific Background:** These visualizations follow guidelines from Nature Research and "
                "incorporate evidence-based reference ranges for clinical interpretation. Each category provides "
                "insight into different aspects of physiological function and recovery capacity."
            )
            
            # Convert dates to string list for chart builders
            date_labels = [d.strftime("%Y-%m-%d") for d in df_ts.index]
            
            def _get_series(col: str) -> Optional[List[float]]:
                """Extract series as list, or None if insufficient data."""
                if col not in df_ts.columns:
                    return None
                series = df_ts[col].tolist()
                if sum(1 for v in series if v is not None and not pd.isna(v)) < 2:
                    return None
                return [v if not pd.isna(v) else None for v in series]
            
            rendered_any = False
            
            # 1. Activity & Movement
            steps = _get_series("steps")
            calories = _get_series("calories_kcal")
            if steps or calories:
                rendered_any = True
                with st.expander("🏃 Activity & Movement", expanded=True):
                    chart_opt = _build_activity_movement_chart(
                        dates=date_labels,
                        steps=steps,
                        calories=calories,
                        title="Activity & Movement Trends",
                    )
                    render_echarts(chart_opt, height_px=380)
                    st.markdown(
                        "*Daily step count is a validated predictor of mortality risk. "
                        "WHO recommends 8,000-10,000 steps/day for optimal cardiometabolic health.* "
                        "*(Tudor-Locke et al., 2011)*"
                    )
            
            # 2. Heart Rate & Stress
            avg_hr = _get_series("avg_hr_bpm")
            resting_hr = _get_series("resting_hr_bpm")
            stress_score = _get_series("stress_score")
            if avg_hr or resting_hr or stress_score:
                rendered_any = True
                with st.expander("❤️ Heart Rate & Stress", expanded=True):
                    chart_opt = _build_hr_stress_chart(
                        dates=date_labels,
                        avg_hr=avg_hr,
                        resting_hr=resting_hr,
                        stress_score=stress_score,
                        title="Heart Rate & Stress Trends",
                    )
                    render_echarts(chart_opt, height_px=380)
                    st.markdown(
                        "*Lower resting heart rate (<60 bpm) indicates athletic conditioning and "
                        "higher cardiac efficiency. Garmin stress score derives from HRV analysis—"
                        "scores 26-50 indicate low stress, while 76-100 suggest high sympathetic activation.* "
                        "*(Shaffer & Ginsberg, 2017)*"
                    )
            
            # 3. Sleep & Recovery
            sleep_score = _get_series("sleep_score")
            sleep_efficiency = _get_series("sleep_efficiency")
            sleep_duration = _get_series("sleep_duration_hours")
            if sleep_score or sleep_efficiency or sleep_duration:
                rendered_any = True
                with st.expander("😴 Sleep & Recovery", expanded=True):
                    chart_opt = _build_sleep_recovery_chart(
                        dates=date_labels,
                        sleep_score=sleep_score,
                        sleep_efficiency=sleep_efficiency,
                        sleep_duration=sleep_duration,
                        title="Sleep & Recovery Trends",
                    )
                    render_echarts(chart_opt, height_px=380)
                    st.markdown(
                        "*Sleep efficiency ≥85% is considered clinically normal. The National Sleep Foundation "
                        "recommends 7-9 hours for adults. Chronic sleep debt accumulates and impairs "
                        "cognitive function, immune response, and cardiovascular health.* "
                        "*(Ohayon et al., 2017; NSF, 2015)*"
                    )
            
            # 4. Respiration & SpO₂
            spo2 = _get_series("avg_spo2")
            resp_awake = _get_series("avg_respiration_awake")
            resp_sleep = _get_series("avg_respiration_sleep")
            if spo2 or resp_awake or resp_sleep:
                rendered_any = True
                with st.expander("🫁 Respiration & SpO₂", expanded=True):
                    chart_opt = _build_respiration_spo2_chart(
                        dates=date_labels,
                        spo2=spo2,
                        resp_awake=resp_awake,
                        resp_sleep=resp_sleep,
                        title="Respiration & SpO₂ Trends",
                    )
                    render_echarts(chart_opt, height_px=380)
                    st.markdown(
                        "*SpO₂ ≥95% is considered normal at sea level. Sustained readings below 94% "
                        "warrant clinical evaluation. Normal adult respiratory rate is 12-20 breaths/min "
                        "when awake, typically lower (10-16) during sleep.* "
                        "*(WHO Pulse Oximetry Training Manual, 2011)*"
                    )
        
            # 5. Body Battery
            bb_avg = _get_series("body_battery_avg")
            bb_charge = _get_series("body_battery_charge")
            bb_drain = _get_series("body_battery_drain")
            if bb_avg or bb_charge or bb_drain:
                rendered_any = True
                with st.expander("🔋 Body Battery", expanded=True):
                    chart_opt = _build_body_battery_chart(
                        dates=date_labels,
                        bb_avg=bb_avg,
                        bb_charge=bb_charge,
                        bb_drain=bb_drain,
                        title="Body Battery Trends",
                    )
                    render_echarts(chart_opt, height_px=380)
                    st.markdown(
                        "*Body Battery combines HRV, stress, sleep quality, and activity data into a "
                        "0-100 energy reserve estimate. Values 75-100 indicate high energy reserves; "
                        "<25 suggests rest is needed. This metric correlates with subjective fatigue "
                        "and next-day performance capacity.* "
                        "*(Firstbeat Technologies, 2014)*"
                    )
            
            if not rendered_any:
                st.caption("Not enough repeated daily values to render trend charts yet.")
    
    if show_table:
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
    
    # Advanced Analytics Section
    if show_advanced and WEARABLE_ANALYTICS_AVAILABLE and len(df) >= 7:
        st.markdown("---")
        st.markdown("### 🧠 Advanced Predictive Analytics")
        st.caption(
            "**Scientific Background:** These predictive models follow guidelines from Nature Research and "
            "incorporate validated physiological frameworks. Each analysis provides insight into different "
            "aspects of allostatic load, circadian regulation, and recovery capacity."
        )
        
        _render_advanced_wearable_analytics(df, user.user_id)


_WEARABLE_CACHE_TTL_SECONDS: Final[int] = 1800
_WEARABLE_MAX_HASH_ROWS: Final[int] = 2000
_WEARABLE_HASH_COLUMNS: Final[tuple[str, ...]] = (
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
    "hrv_rmssd_ms",
    "hrv_sdnn_ms",
)


def _hash_dataframe_for_wearable(
    df: pd.DataFrame,
    *,
    columns: Sequence[str] | None = None,
    max_rows: int = _WEARABLE_MAX_HASH_ROWS,
) -> str:
    """Return a stable hash for wearable analytics inputs (bounded, deterministic)."""
    if df is None or df.empty:
        return "empty"
    working = df
    if columns:
        existing = [col for col in columns if col in working.columns]
        if existing:
            working = working[existing]
    if max_rows <= 0:
        max_rows = _WEARABLE_MAX_HASH_ROWS
    if len(working) > max_rows:
        working = working.tail(int(max_rows))
    try:
        working = working.copy()
    except Exception:
        pass
    try:
        working = working.sort_index(axis=1)
    except Exception:
        pass
    try:
        hashes = pd.util.hash_pandas_object(working, index=True)
        return hashlib.sha256(hashes.values.tobytes()).hexdigest()
    except Exception:
        payload = working.to_json(orient="table", date_format="iso", default_handler=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _wearable_insights_signature(df: pd.DataFrame, user_id: str) -> str:
    """Build a deterministic signature for wearable analytics inputs."""
    wearable_hash = _hash_dataframe_for_wearable(df, columns=_WEARABLE_HASH_COLUMNS)
    seed = f"user={user_id}|wearable={wearable_hash}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


@st.cache_data(ttl=_WEARABLE_CACHE_TTL_SECONDS, max_entries=16, show_spinner=False)
def _cached_wearable_insights(
    signature: str,
    df: pd.DataFrame,
) -> Optional["WearableInsights"]:
    """Cache wrapper for wearable analytics (signature-guarded)."""
    _ = signature  # part of cache key; do not remove
    return generate_wearable_insights(df)


def _render_advanced_wearable_analytics(df: pd.DataFrame, user_id: str) -> None:
    """Render advanced wearable analytics with predictive models and insights."""
    if not WEARABLE_ANALYTICS_AVAILABLE:
        st.info("Advanced analytics module not available.")
        return
    
    # Generate comprehensive insights
    try:
        signature = _wearable_insights_signature(df, user_id)
        insights = _cached_wearable_insights(signature, df)
    except Exception as exc:
        _LOGGER.warning("Failed to generate wearable insights: %s", exc)
        st.warning("Unable to generate advanced analytics. Insufficient data or analysis error.")
        return
    
    if insights is None:
        st.info("Need at least 7 days of data for advanced analytics.")
        return
    
    # Data quality indicator
    quality_color = "#28a745" if insights.data_quality_score >= 70 else "#ffc107" if insights.data_quality_score >= 40 else "#dc3545"
    st.markdown(
        f"**Data Quality:** <span style='color: {quality_color}; font-weight: bold;'>{insights.data_quality_score:.0f}%</span>",
        unsafe_allow_html=True,
    )
    
    # Create tabs for different analyses
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔋 Body Battery Forecast",
        "⚡ Allostatic Load",
        "🌙 Circadian Analysis",
        "😰 Stress Prediction",
        "💪 Recovery Status",
    ])
    
    with tab1:
        _render_body_battery_forecast(insights.body_battery_forecast, df)
    
    with tab2:
        _render_allostatic_load(insights.allostatic_load)
    
    with tab3:
        _render_circadian_analysis(insights.circadian_analysis)
    
    with tab4:
        _render_stress_prediction(insights.stress_prediction)
    
    with tab5:
        _render_recovery_analysis(insights.recovery_analysis)
    
    # Correlations section
    if insights.correlations:
        st.markdown("#### 🔗 Key Metric Correlations")
        corr_data = []
        for corr in insights.correlations[:5]:
            corr_data.append({
                "Metric A": corr.metric_a.replace("_", " ").title(),
                "Metric B": corr.metric_b.replace("_", " ").title(),
                "Correlation": f"{corr.pearson_r:+.2f}",
                "P-value": f"{corr.p_value:.4f}",
                "Interpretation": corr.interpretation,
            })
        st.dataframe(pd.DataFrame(corr_data), use_container_width=True, hide_index=True)


def _render_body_battery_forecast(
    forecast: Optional[BodyBatteryForecast],
    df: pd.DataFrame,
) -> None:
    """Render Body Battery forecast with confidence intervals - publication quality."""
    st.markdown("##### 🔮 7-Day Body Battery Prediction")
    
    if forecast is None:
        st.info("Need at least 14 days of Body Battery data for forecasting.")
        return
    
    # Trend indicator
    trend_icons = {
        TrendDirection.IMPROVING: "📈",
        TrendDirection.STABLE: "➡️",
        TrendDirection.DECLINING: "📉",
        TrendDirection.VARIABLE: "📊",
    }
    trend_colors = {
        TrendDirection.IMPROVING: "#27ae60",
        TrendDirection.STABLE: "#7f8c8d",
        TrendDirection.DECLINING: "#e74c3c",
        TrendDirection.VARIABLE: "#f39c12",
    }
    trend_color = trend_colors.get(forecast.trend, "#7f8c8d")
    
    # Summary metrics in styled cards
    col1, col2, col3 = st.columns(3)
    with col1:
        trend_icon = trend_icons.get(forecast.trend, "➡️")
        st.markdown(
            f"""<div style="text-align: center; padding: 15px; background: {trend_color}15; 
                border-radius: 10px; border-left: 4px solid {trend_color};">
                <div style="font-size: 28px;">{trend_icon}</div>
                <div style="font-size: 16px; font-weight: bold; color: {trend_color};">
                    {forecast.trend.value.title()}
                </div>
                <div style="font-size: 11px; color: #666;">Energy Trend</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col2:
        acc_color = "#27ae60" if forecast.model_accuracy >= 80 else "#f39c12" if forecast.model_accuracy >= 60 else "#e74c3c"
        st.markdown(
            f"""<div style="text-align: center; padding: 15px; background: {acc_color}15; 
                border-radius: 10px; border-left: 4px solid {acc_color};">
                <div style="font-size: 28px; font-weight: bold; color: {acc_color};">
                    {forecast.model_accuracy:.0f}%
                </div>
                <div style="font-size: 11px; color: #666;">Model Accuracy</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col3:
        if forecast.recovery_hours is not None:
            rec_color = "#e74c3c" if forecast.recovery_hours > 24 else "#f39c12" if forecast.recovery_hours > 8 else "#27ae60"
            st.markdown(
                f"""<div style="text-align: center; padding: 15px; background: {rec_color}15; 
                    border-radius: 10px; border-left: 4px solid {rec_color};">
                    <div style="font-size: 28px; font-weight: bold; color: {rec_color};">
                        {forecast.recovery_hours:.1f}h
                    </div>
                    <div style="font-size: 11px; color: #666;">Est. Recovery Time</div>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """<div style="text-align: center; padding: 15px; background: #27ae6015; 
                    border-radius: 10px; border-left: 4px solid #27ae60;">
                    <div style="font-size: 28px;">✅</div>
                    <div style="font-size: 16px; font-weight: bold; color: #27ae60;">Optimal</div>
                    <div style="font-size: 11px; color: #666;">Recovery Status</div>
                </div>""",
                unsafe_allow_html=True,
            )
    
    st.markdown("")  # Spacer
    
    # Build forecast chart
    hist_dates: List[str] = []
    hist_values: List[float] = []
    if "metric_date" in df.columns and "body_battery_avg" in df.columns:
        df_hist = df[["metric_date", "body_battery_avg"]].dropna().tail(14)
        if not df_hist.empty:
            df_hist = df_hist.sort_values("metric_date")
            hist_dates = [pd.to_datetime(d).strftime("%Y-%m-%d") for d in df_hist["metric_date"]]
            hist_values = df_hist["body_battery_avg"].tolist()
    
    forecast_dates = [d.strftime("%Y-%m-%d") for d in forecast.forecast_dates]
    all_dates = hist_dates + forecast_dates
    
    # Build series data
    hist_series = hist_values + [None] * len(forecast_dates)
    forecast_series = [None] * len(hist_dates) + forecast.predicted_values
    lower_series = [None] * len(hist_dates) + forecast.confidence_lower
    upper_series = [None] * len(hist_dates) + forecast.confidence_upper
    
    upper_diff_series: List[Optional[float]] = []
    for lo, up in zip(lower_series, upper_series):
        if lo is not None and up is not None:
            upper_diff_series.append(up - lo)
        else:
            upper_diff_series.append(None)
    
    # Publication-quality chart
    chart_option = {
        "title": {
            "text": "Body Battery: Historical + 7-Day Forecast",
            "subtext": "Holt-Winters exponential smoothing | 95% confidence interval | "
                       "Zones: 75-100 High, 50-74 Moderate, <50 Low",
            "left": "center",
            "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": """function(params) {
                var date = params[0].axisValue;
                var result = '<b>' + date + '</b><br/>';
                params.forEach(function(p) {
                    if (p.seriesName && p.seriesName.indexOf('_') !== 0 && 
                        p.seriesName !== 'CI Lower' && p.value !== null && p.value !== undefined) {
                        result += p.marker + ' ' + p.seriesName + ': <b>' + 
                            (typeof p.value === 'number' ? p.value.toFixed(0) : p.value) + '</b><br/>';
                    }
                });
                return result;
            }""",
        },
        "legend": {
            "data": ["Historical", "Forecast", "95% CI", "75% Threshold"],
            "bottom": 5,
            "textStyle": {"fontSize": 10},
        },
        "grid": {
            "left": "8%",
            "right": "5%",
            "top": "18%",
            "bottom": "15%",
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": all_dates,
            "name": "Date",
            "nameLocation": "middle",
            "nameGap": 30,
            "axisLabel": {"rotate": 45, "fontSize": 9},
            "splitLine": {"show": False},
        },
        "yAxis": {
            "type": "value",
            "name": "Body Battery",
            "nameLocation": "middle",
            "nameGap": 45,
            "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
            "min": 0,
            "max": 100,
            "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
        },
        "series": [
            # Energy zones
            {
                "name": "High Energy",
                "type": "line",
                "data": [100] * len(all_dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(46, 204, 113, 0.1)"},
                "stack": "zone_high",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "_zone_high_base",
                "type": "line",
                "data": [75] * len(all_dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "zone_high",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "Moderate Energy",
                "type": "line",
                "data": [74] * len(all_dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(52, 152, 219, 0.08)"},
                "stack": "zone_mod",
                "symbol": "none",
                "silent": True,
            },
            {
                "name": "_zone_mod_base",
                "type": "line",
                "data": [50] * len(all_dates),
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "#fff"},
                "stack": "zone_mod",
                "symbol": "none",
                "silent": True,
            },
            # 75% threshold line
            {
                "name": "75% Threshold",
                "type": "line",
                "data": [75] * len(all_dates),
                "lineStyle": {"color": "#27ae60", "width": 1.5, "type": "dashed"},
                "symbol": "none",
            },
            # Confidence interval
            {
                "name": "CI Lower",
                "type": "line",
                "data": lower_series,
                "lineStyle": {"opacity": 0},
                "areaStyle": {"opacity": 0},
                "symbol": "none",
                "stack": "confidence",
            },
            {
                "name": "95% CI",
                "type": "line",
                "data": upper_diff_series,
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": "rgba(46, 204, 113, 0.25)"},
                "symbol": "none",
                "stack": "confidence",
            },
            # Historical data
            {
                "name": "Historical",
                "type": "line",
                "data": hist_series,
                "lineStyle": {"color": "#3498db", "width": 2.5},
                "itemStyle": {"color": "#3498db"},
                "symbol": "circle",
                "symbolSize": 7,
            },
            # Forecast data
            {
                "name": "Forecast",
                "type": "line",
                "data": forecast_series,
                "lineStyle": {"color": "#27ae60", "width": 2.5, "type": "dashed"},
                "itemStyle": {"color": "#27ae60"},
                "symbol": "diamond",
                "symbolSize": 8,
            },
        ],
        "dataZoom": [{"type": "inside", "start": 0, "end": 100}],
    }
    render_echarts(chart_option, height_px=380)
    
    st.markdown(
        "*Forecast uses Holt-Winters double exponential smoothing to predict energy reserve trends. "
        "Shaded area represents 95% confidence interval. Energy levels >75 indicate high reserve "
        "capacity suitable for demanding activities.* *(Firstbeat Technologies, 2014)*"
    )


def _render_allostatic_load(load: Optional[AllostasticLoadScore]) -> None:
    """Render allostatic load assessment - publication quality."""
    st.markdown("##### 📊 Allostatic Load Index")
    
    if load is None:
        st.info("Need at least 7 days of stress, sleep, and heart rate data.")
        return
    
    # Risk level colors
    risk_colors = {
        RiskLevel.LOW: "#27ae60",
        RiskLevel.MODERATE: "#f39c12",
        RiskLevel.HIGH: "#e67e22",
        RiskLevel.VERY_HIGH: "#e74c3c",
    }
    risk_color = risk_colors.get(load.risk_level, "#7f8c8d")
    
    # Main score display with gauge
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Semi-circular gauge for allostatic load
        gauge_option = {
            "title": {
                "text": "Cumulative Stress Burden",
                "subtext": "Based on McEwen (1998) allostatic load framework",
                "left": "center",
                "top": 0,
                "textStyle": {"fontSize": 14, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
                "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
            },
            "series": [
                {
                    "type": "gauge",
                    "startAngle": 180,
                    "endAngle": 0,
                    "min": 0,
                    "max": 10,
                    "splitNumber": 5,
                    "radius": "90%",
                    "center": ["50%", "70%"],
                    "axisLine": {
                        "lineStyle": {
                            "width": 25,
                            "color": [
                                [0.3, "#27ae60"],  # Low (0-3)
                                [0.5, "#f39c12"],  # Moderate (3-5)
                                [0.7, "#e67e22"],  # High (5-7)
                                [1.0, "#e74c3c"],  # Very High (7-10)
                            ],
                        },
                    },
                    "pointer": {
                        "length": "55%",
                        "width": 8,
                        "itemStyle": {"color": "#2c3e50"},
                    },
                    "axisTick": {
                        "length": 8,
                        "lineStyle": {"color": "auto", "width": 2},
                    },
                    "splitLine": {
                        "length": 15,
                        "lineStyle": {"color": "auto", "width": 3},
                    },
                    "axisLabel": {
                        "color": "#666",
                        "fontSize": 11,
                        "distance": -45,
                        "formatter": "{value}",
                    },
                    "detail": {
                        "valueAnimation": True,
                        "formatter": "{value}",
                        "fontSize": 28,
                        "fontWeight": "bold",
                        "color": risk_color,
                        "offsetCenter": [0, "20%"],
                    },
                    "title": {
                        "offsetCenter": [0, "45%"],
                        "fontSize": 14,
                        "fontWeight": "bold",
                        "color": risk_color,
                    },
                    "data": [
                        {
                            "value": round(load.total_score, 1),
                            "name": load.risk_level.value.upper(),
                        }
                    ],
                }
            ],
        }
        render_echarts(gauge_option, height_px=280)
    
    with col2:
        # Trend and recovery metrics
        trend_7d_icon = "📈" if load.trend_7d == TrendDirection.IMPROVING else "📉" if load.trend_7d == TrendDirection.DECLINING else "➡️"
        trend_30d_icon = "📈" if load.trend_30d == TrendDirection.IMPROVING else "📉" if load.trend_30d == TrendDirection.DECLINING else "➡️"
        trend_7d_color = "#27ae60" if load.trend_7d == TrendDirection.IMPROVING else "#e74c3c" if load.trend_7d == TrendDirection.DECLINING else "#7f8c8d"
        trend_30d_color = "#27ae60" if load.trend_30d == TrendDirection.IMPROVING else "#e74c3c" if load.trend_30d == TrendDirection.DECLINING else "#7f8c8d"
        
        st.markdown(
            f"""<div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                <div style="font-size: 12px; color: #666; margin-bottom: 5px;">7-Day Trend</div>
                <div style="font-size: 20px; color: {trend_7d_color};">
                    {trend_7d_icon} {load.trend_7d.value.title()}
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""<div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                <div style="font-size: 12px; color: #666; margin-bottom: 5px;">30-Day Trend</div>
                <div style="font-size: 20px; color: {trend_30d_color};">
                    {trend_30d_icon} {load.trend_30d.value.title()}
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        debt_color = "#e74c3c" if load.recovery_debt_hours > 16 else "#f39c12" if load.recovery_debt_hours > 8 else "#27ae60"
        st.markdown(
            f"""<div style="background: #f8f9fa; padding: 15px; border-radius: 10px;">
                <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Recovery Debt</div>
                <div style="font-size: 20px; color: {debt_color};">
                    {load.recovery_debt_hours:.1f}h
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
    
    # Component breakdown with radar chart
    if load.component_scores and len(load.component_scores) >= 3:
        st.markdown("**System Component Breakdown:**")
        
        col_radar, col_table = st.columns([3, 2])
        
        with col_radar:
            # Radar chart for component visualization
            indicators = []
            values = []
            for comp, score in load.component_scores.items():
                indicators.append({"name": comp.replace("_", " ").title(), "max": 10})
                values.append(round(score, 1))
            
            radar_option = {
                "tooltip": {"trigger": "item"},
                "radar": {
                    "indicator": indicators,
                    "shape": "polygon",
                    "splitNumber": 5,
                    "axisName": {"color": "#666", "fontSize": 10},
                    "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"]}},
                    "splitArea": {
                        "show": True,
                        "areaStyle": {
                            "color": ["rgba(39, 174, 96, 0.1)", "rgba(243, 156, 18, 0.1)", 
                                      "rgba(230, 126, 34, 0.1)", "rgba(231, 76, 60, 0.1)", 
                                      "rgba(231, 76, 60, 0.15)"],
                        },
                    },
                },
                "series": [
                    {
                        "type": "radar",
                        "data": [
                            {
                                "value": values,
                                "name": "Load Score",
                                "areaStyle": {"color": "rgba(52, 152, 219, 0.3)"},
                                "lineStyle": {"color": "#3498db", "width": 2},
                                "itemStyle": {"color": "#3498db"},
                            }
                        ],
                    }
                ],
            }
            render_echarts(radar_option, height_px=280)
        
        with col_table:
            comp_data = []
            for comp, score in load.component_scores.items():
                status = "🟢 Low" if score < 3 else "🟡 Moderate" if score < 5 else "🟠 High" if score < 7 else "🔴 Very High"
                comp_data.append({
                    "System": comp.replace("_", " ").title(),
                    "Score": f"{score:.1f}",
                    "Status": status,
                })
            st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)
    
    # Interpretation and recommendations in styled container
    st.markdown(
        f"""<div style="background: {risk_color}10; border-left: 4px solid {risk_color}; 
            padding: 15px; border-radius: 8px; margin: 15px 0;">
            <div style="font-weight: bold; color: {risk_color}; margin-bottom: 8px;">
                📋 Clinical Interpretation
            </div>
            <div style="color: #444;">{load.interpretation}</div>
        </div>""",
        unsafe_allow_html=True,
    )
    
    if load.recommendations:
        st.markdown("**Evidence-Based Recommendations:**")
        for i, rec in enumerate(load.recommendations, 1):
            st.markdown(f"**{i}.** {rec}")
    
    st.markdown(
        "*Allostatic load represents cumulative 'wear and tear' on body systems from chronic stress. "
        "Elevated scores predict increased cardiovascular risk and accelerated biological aging.* "
        "*(McEwen, 1998; Seeman et al., 2001)*"
    )


def _render_circadian_analysis(analysis: Optional[CircadianAnalysis]) -> None:
    """Render circadian rhythm analysis - publication quality."""
    st.markdown("##### 🕐 Circadian Rhythm Profile")
    
    if analysis is None:
        st.info("Need at least 7 days of heart rate and stress data for circadian analysis.")
        return
    
    # Chronotype config
    chronotype_config = {
        Chronotype.EARLY_BIRD: {
            "icon": "🌅",
            "color": "#f39c12",
            "desc": "Morning type — Peak alertness in early hours (6-10 AM)",
            "gradient": ["#f39c12", "#e67e22"],
        },
        Chronotype.INTERMEDIATE: {
            "icon": "☀️",
            "color": "#3498db",
            "desc": "Intermediate — Balanced energy distribution throughout day",
            "gradient": ["#3498db", "#2980b9"],
        },
        Chronotype.NIGHT_OWL: {
            "icon": "🌙",
            "color": "#9b59b6",
            "desc": "Evening type — Peak performance in afternoon/evening",
            "gradient": ["#9b59b6", "#8e44ad"],
        },
        Chronotype.UNDEFINED: {
            "icon": "❓",
            "color": "#7f8c8d",
            "desc": "Insufficient data to determine chronotype",
            "gradient": ["#7f8c8d", "#6c757d"],
        },
    }
    config = chronotype_config.get(analysis.chronotype, chronotype_config[Chronotype.UNDEFINED])
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # 24-hour clock visualization for circadian rhythm
        # Build polar chart showing activity/performance curve
        hours = list(range(24))
        hour_labels = [f"{h:02d}:00" for h in hours]
        
        # Create simulated circadian curve based on chronotype
        peak_hour = int(analysis.rhythm_acrophase)
        values = []
        for h in hours:
            # Cosine-based circadian curve centered on peak
            diff = min(abs(h - peak_hour), 24 - abs(h - peak_hour))
            val = 50 + 50 * np.cos(diff * np.pi / 12)  # Peak at acrophase
            values.append(round(val, 1))
        
        # Highlight peak performance hours
        peak_hours_set = set(analysis.peak_performance_hours)
        series_data = []
        for i, (h, v) in enumerate(zip(hours, values)):
            if h in peak_hours_set:
                series_data.append({
                    "value": v,
                    "itemStyle": {"color": "#27ae60"},
                })
            else:
                series_data.append(v)
        
        polar_option = {
            "title": {
                "text": "24-Hour Performance Curve",
                "subtext": f"Chronotype: {analysis.chronotype.value.replace('_', ' ').title()} | "
                           f"Peak: {peak_hour:02d}:00 | Regularity: {analysis.regularity_score:.0f}%",
                "left": "center",
                "textStyle": {"fontSize": 14, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
                "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
            },
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "shadow"},
            },
            "angleAxis": {
                "type": "category",
                "data": hour_labels,
                "startAngle": 90,
                "axisLabel": {"fontSize": 8, "interval": 2},
            },
            "radiusAxis": {
                "min": 0,
                "max": 100,
                "axisLabel": {"show": False},
                "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"]}},
            },
            "polar": {"radius": ["20%", "75%"]},
            "series": [
                {
                    "type": "bar",
                    "data": series_data,
                    "coordinateSystem": "polar",
                    "itemStyle": {
                        "color": {
                            "type": "linear",
                            "x": 0, "y": 0, "x2": 0, "y2": 1,
                            "colorStops": [
                                {"offset": 0, "color": config["gradient"][0]},
                                {"offset": 1, "color": config["gradient"][1]},
                            ],
                        },
                    },
                }
            ],
        }
        render_echarts(polar_option, height_px=320)
    
    with col2:
        # Chronotype card
        st.markdown(
            f"""<div style="text-align: center; padding: 20px; background: {config['color']}15; 
                border-radius: 10px; border-left: 4px solid {config['color']}; margin-bottom: 15px;">
                <div style="font-size: 48px;">{config['icon']}</div>
                <div style="font-size: 18px; font-weight: bold; color: {config['color']};">
                    {analysis.chronotype.value.replace('_', ' ').title()}
                </div>
                <div style="font-size: 11px; color: #666; margin-top: 5px;">{config['desc']}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    
        # Key metrics
        reg_color = "#27ae60" if analysis.regularity_score >= 70 else "#f39c12" if analysis.regularity_score >= 50 else "#e74c3c"
        st.markdown(
            f"""<div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 8px;">
                <div style="font-size: 11px; color: #666;">Rhythm Regularity</div>
                <div style="font-size: 20px; font-weight: bold; color: {reg_color};">
                    {analysis.regularity_score:.0f}%
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        
        sleep_start, sleep_end = analysis.optimal_sleep_window
        st.markdown(
            f"""<div style="background: #f8f9fa; padding: 12px; border-radius: 8px;">
                <div style="font-size: 11px; color: #666;">Optimal Sleep Window</div>
                <div style="font-size: 18px; font-weight: bold; color: #3498db;">
                    {sleep_start:02d}:00 - {sleep_end:02d}:00
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
    
    # Peak performance hours highlight
    peak_hours_str = ", ".join([f"{h:02d}:00" for h in analysis.peak_performance_hours])
    st.markdown(
        f"""<div style="background: #27ae6015; border-left: 4px solid #27ae60; 
            padding: 15px; border-radius: 8px; margin: 15px 0;">
            <span style="font-weight: bold; color: #27ae60;">🎯 Peak Performance Hours:</span> 
            <span style="color: #333;">{peak_hours_str}</span>
        </div>""",
        unsafe_allow_html=True,
    )
    
    # Chronotype-specific optimization tips
    if analysis.chronotype == Chronotype.EARLY_BIRD:
        tips = [
            "Schedule cognitively demanding tasks for morning hours (8-11 AM)",
            "Avoid late-night activities that delay sleep onset",
            "Morning light exposure (15-30 min) reinforces your rhythm",
            "Plan easier tasks for afternoon when alertness naturally dips",
        ]
    elif analysis.chronotype == Chronotype.NIGHT_OWL:
        tips = [
            "Reserve complex analytical tasks for late afternoon/evening",
            "If early wake is required, use bright light therapy (10,000 lux)",
            "Avoid morning high-stakes meetings when cognitive performance is lower",
            "Consider strategic caffeine timing (not before 10 AM)",
        ]
    else:
        tips = [
            "Maintain consistent sleep-wake times to strengthen circadian alignment",
            "Expose yourself to bright light within 1 hour of waking",
            "Avoid blue light 2 hours before intended sleep time",
        ]
    
    st.markdown("**Evidence-Based Optimization Tips:**")
    for tip in tips:
        st.markdown(f"• {tip}")
    
    st.markdown(
        "*Circadian rhythm analysis based on Horne-Östberg chronotype framework. "
        "Rhythm regularity >70% indicates stable circadian entrainment.* "
        "*(Roenneberg et al., 2003)*"
    )


def _render_stress_prediction(prediction: Optional[StressPrediction]) -> None:
    """Render stress prediction - publication quality."""
    st.markdown("##### 😰 Next-Day Stress Prediction")
    
    if prediction is None:
        st.info("Need at least 5 days of stress data for prediction.")
        return
    
    # Risk colors
    risk_colors = {
        RiskLevel.LOW: "#27ae60",
        RiskLevel.MODERATE: "#f39c12",
        RiskLevel.HIGH: "#e67e22",
        RiskLevel.VERY_HIGH: "#e74c3c",
    }
    color = risk_colors.get(prediction.risk_level, "#7f8c8d")
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Stress gauge with prediction
        ci_low, ci_high = prediction.confidence_interval
        
        gauge_option = {
            "title": {
                "text": "Predicted Stress Level",
                "subtext": f"95% CI: {ci_low:.0f} - {ci_high:.0f} | Based on recent patterns",
                "left": "center",
                "textStyle": {"fontSize": 14, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
                "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
            },
            "series": [
                {
                    "type": "gauge",
                    "startAngle": 180,
                    "endAngle": 0,
                    "min": 0,
                    "max": 100,
                    "splitNumber": 4,
                    "radius": "90%",
                    "center": ["50%", "70%"],
                    "axisLine": {
                        "lineStyle": {
                            "width": 25,
                            "color": [
                                [0.25, "#27ae60"],  # Rest (0-25)
                                [0.50, "#3498db"],  # Low (25-50)
                                [0.75, "#f39c12"],  # Medium (50-75)
                                [1.0, "#e74c3c"],   # High (75-100)
                            ],
                        },
                    },
                    "pointer": {
                        "length": "55%",
                        "width": 8,
                        "itemStyle": {"color": "#2c3e50"},
                    },
                    "axisTick": {
                        "length": 8,
                        "lineStyle": {"color": "auto", "width": 2},
                    },
                    "splitLine": {
                        "length": 15,
                        "lineStyle": {"color": "auto", "width": 3},
                    },
                    "axisLabel": {
                        "color": "#666",
                        "fontSize": 11,
                        "distance": -45,
                        "formatter": "{value}",
                    },
                    "detail": {
                        "valueAnimation": True,
                        "formatter": "{value}",
                        "fontSize": 32,
                        "fontWeight": "bold",
                        "color": color,
                        "offsetCenter": [0, "20%"],
                    },
                    "title": {
                        "offsetCenter": [0, "45%"],
                        "fontSize": 14,
                        "fontWeight": "bold",
                        "color": color,
                    },
                    "data": [
                        {
                            "value": round(prediction.predicted_stress, 0),
                            "name": prediction.risk_level.value.upper(),
                        }
                    ],
                }
            ],
        }
        render_echarts(gauge_option, height_px=280)
    
    with col2:
        # Risk level card
        risk_icons = {
            RiskLevel.LOW: "✅",
            RiskLevel.MODERATE: "⚠️",
            RiskLevel.HIGH: "🔶",
            RiskLevel.VERY_HIGH: "🚨",
        }
        risk_icon = risk_icons.get(prediction.risk_level, "❓")
        
        st.markdown(
            f"""<div style="text-align: center; padding: 20px; background: {color}15; 
                border-radius: 10px; border-left: 4px solid {color}; margin-bottom: 15px;">
                <div style="font-size: 32px;">{risk_icon}</div>
                <div style="font-size: 16px; font-weight: bold; color: {color};">
                    {prediction.risk_level.value.upper()} RISK
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
    
        # Contributing factors
        if prediction.contributing_factors:
            st.markdown("**Contributing Factors:**")
            for factor in prediction.contributing_factors[:4]:
                factor_color = "#e74c3c" if "high" in factor.lower() or "poor" in factor.lower() else "#7f8c8d"
                st.markdown(f"<span style='color: {factor_color};'>• {factor}</span>", unsafe_allow_html=True)
    
    # Recommendations in styled container
    if prediction.recommendations:
        st.markdown(
            f"""<div style="background: {color}10; border-left: 4px solid {color}; 
                padding: 15px; border-radius: 8px; margin: 15px 0;">
                <div style="font-weight: bold; color: {color}; margin-bottom: 10px;">
                    📋 Stress Management Recommendations
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        for i, rec in enumerate(prediction.recommendations, 1):
            st.markdown(f"**{i}.** {rec}")
    
    st.markdown(
        "*Stress prediction uses autoregressive modeling on recent stress patterns, "
        "accounting for sleep quality, activity levels, and circadian phase.* "
        "*(Cohen et al., 1983; McEwen, 2008)*"
    )


def _render_recovery_analysis(recovery: Optional[RecoveryAnalysis]) -> None:
    """Render recovery status analysis - publication quality."""
    st.markdown("##### 💪 Recovery Status")
    
    if recovery is None:
        st.info("Need Body Battery, sleep, and stress data for recovery analysis.")
        return
    
    # State colors and icons
    state_config = {
        RecoveryState.EXCELLENT: ("#27ae60", "🌟", "Fully recovered, ready for high-intensity activity"),
        RecoveryState.GOOD: ("#3498db", "✅", "Well recovered, suitable for normal training"),
        RecoveryState.FAIR: ("#f39c12", "⚠️", "Partially recovered, consider lighter activity"),
        RecoveryState.POOR: ("#e67e22", "🔶", "Under-recovered, prioritize rest"),
        RecoveryState.CRITICAL: ("#e74c3c", "🚨", "Significant recovery deficit, rest essential"),
    }
    color, icon, desc = state_config.get(recovery.current_state, ("#7f8c8d", "❓", "Unknown"))
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Recovery score gauge
        gauge_option = {
            "title": {
                "text": "Recovery Score",
                "subtext": desc,
                "left": "center",
                "textStyle": {"fontSize": 14, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
                "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
            },
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
                            "width": 25,
                            "color": [
                                [0.3, "#e74c3c"],   # Critical/Poor (0-30)
                                [0.5, "#f39c12"],   # Fair (30-50)
                                [0.7, "#3498db"],   # Good (50-70)
                                [1.0, "#27ae60"],   # Excellent (70-100)
                            ],
                        },
                    },
                    "pointer": {
                        "length": "55%",
                        "width": 8,
                        "itemStyle": {"color": "#2c3e50"},
                    },
                    "axisTick": {
                        "length": 8,
                        "lineStyle": {"color": "auto", "width": 2},
                    },
                    "splitLine": {
                        "length": 15,
                        "lineStyle": {"color": "auto", "width": 3},
                    },
                    "axisLabel": {
                        "color": "#666",
                        "fontSize": 11,
                        "distance": -45,
                        "formatter": "{value}",
                    },
                    "detail": {
                        "valueAnimation": True,
                        "formatter": "{value}",
                        "fontSize": 32,
                        "fontWeight": "bold",
                        "color": color,
                        "offsetCenter": [0, "20%"],
                    },
                    "title": {
                        "offsetCenter": [0, "45%"],
                        "fontSize": 14,
                        "fontWeight": "bold",
                        "color": color,
                    },
                    "data": [
                        {
                            "value": round(recovery.recovery_score, 0),
                            "name": recovery.current_state.value.upper(),
                        }
                    ],
                }
            ],
        }
        render_echarts(gauge_option, height_px=280)
    
    with col2:
        # Status card
        st.markdown(
            f"""<div style="text-align: center; padding: 20px; background: {color}15; 
                border-radius: 10px; border-left: 4px solid {color}; margin-bottom: 15px;">
                <div style="font-size: 36px;">{icon}</div>
                <div style="font-size: 18px; font-weight: bold; color: {color};">
                    {recovery.current_state.value.upper()}
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        
        # Key metrics
        debt_color = "#e74c3c" if recovery.sleep_debt_hours > 8 else "#f39c12" if recovery.sleep_debt_hours > 4 else "#27ae60"
        st.markdown(
            f"""<div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 8px;">
                <div style="font-size: 11px; color: #666;">Sleep Debt</div>
                <div style="font-size: 18px; font-weight: bold; color: {debt_color};">
                    {recovery.sleep_debt_hours:.1f} hours
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        
        stress_color = "#e74c3c" if recovery.stress_accumulation > 150 else "#f39c12" if recovery.stress_accumulation > 100 else "#27ae60"
        st.markdown(
            f"""<div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 8px;">
                <div style="font-size: 11px; color: #666;">Stress Accumulation</div>
                <div style="font-size: 18px; font-weight: bold; color: {stress_color};">
                    {recovery.stress_accumulation:.0f}
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        
        if recovery.days_to_full_recovery == 0:
            st.markdown(
                """<div style="background: #27ae6015; padding: 12px; border-radius: 8px;">
                    <div style="font-size: 11px; color: #666;">Recovery Timeline</div>
                    <div style="font-size: 18px; font-weight: bold; color: #27ae60;">
                        ✅ Fully Recovered
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            days_color = "#e74c3c" if recovery.days_to_full_recovery > 3 else "#f39c12" if recovery.days_to_full_recovery > 1 else "#27ae60"
            st.markdown(
                f"""<div style="background: #f8f9fa; padding: 12px; border-radius: 8px;">
                    <div style="font-size: 11px; color: #666;">Days to Full Recovery</div>
                    <div style="font-size: 18px; font-weight: bold; color: {days_color};">
                        ~{recovery.days_to_full_recovery} day(s)
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )
    
    # Recovery protocol in styled container
    if recovery.optimal_rest_protocol:
        st.markdown(
            f"""<div style="background: {color}10; border-left: 4px solid {color}; 
                padding: 15px; border-radius: 8px; margin: 15px 0;">
                <div style="font-weight: bold; color: {color}; margin-bottom: 10px;">
                    📋 Optimal Recovery Protocol
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        for i, step in enumerate(recovery.optimal_rest_protocol, 1):
            st.markdown(f"**{i}.** {step}")
    
    st.markdown(
        "*Recovery analysis integrates Body Battery trends, sleep debt accumulation, and stress load. "
        "Optimal recovery requires adequate sleep duration, low stress, and appropriate activity levels.* "
        "*(Kellmann, 2010; Meeusen et al., 2013)*"
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

    queued_paths: list[dict[str, Any]] = st.session_state.get("queued_rr_filepaths", [])
    # Track already-queued items to avoid unbounded growth on reruns.
    existing_paths = {
        (str(item.get("path")), str(item.get("recording_start")))
        for item in queued_paths
        if isinstance(item, dict)
    }
    processed_key = f"_profile_rr_upload_processed_{user.user_id}"
    if processed_key not in st.session_state:
        st.session_state[processed_key] = set()
    processed_hashes: set[str] = st.session_state[processed_key]

    stored_any = False
    preview_rr_ms: Optional[np.ndarray] = None
    for uploaded in uploaded_files:
        try:
            file_bytes = uploaded.getvalue()
            file_hash = hashlib.sha256(file_bytes).hexdigest()
            if file_hash in processed_hashes:
                continue
            content = file_bytes.decode("utf-8", errors="ignore")

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
            stored_path: Optional[Path] = None
            try:
                stored_path = manager.store_rr_intervals(
                    rr_ms,
                    filename=uploaded.name,
                    recording_date=start_date,
                    overwrite=True,
                )
            except FileExistsError:
                # Already stored; continue to queue for analysis
                stored_path = None
            record_start = start_ts.isoformat()
            if stored_path is not None:
                queue_key = (str(stored_path), record_start)
                if queue_key not in existing_paths:
                    queued_paths.append(
                        {
                            "path": str(stored_path),
                            "name": uploaded.name,
                            "recording_start": record_start,
                        }
                    )
                    existing_paths.add(queue_key)
            processed_hashes.add(file_hash)
            stored_any = True
        except Exception as exc:  # pragma: no cover - defensive
            st.error(f"Failed to store {uploaded.name}: {exc}")
    if queued_paths:
        st.session_state["queued_rr_filepaths"] = queued_paths
    if stored_any:
        st.success("Files stored under this profile and queued for analysis.")
        # Inline quick-look plots for the first uploaded file to avoid blank UI
        if preview_rr_ms is not None and preview_rr_ms.size >= 10:
            with st.spinner("Preparing quick RR preview..."):
                st.markdown("### 🔎 Quick RR Preview")
                st.caption(
                    "Publication-quality visualizations for scientific analysis. "
                    "Reference: Task Force (1996), Shaffer & Ginsberg (2017)."
                )
                
                # Downsample for responsiveness (keep up to 8k samples)
                rr_ms = preview_rr_ms
                if rr_ms.size > 8000:
                    step = int(np.ceil(rr_ms.size / 8000))
                    rr_ms = rr_ms[::step]
                rr_s = rr_ms / 1000.0
                t_s = np.cumsum(rr_s)
                
                # 1. RR Tachogram with scientific formatting
                st.markdown("##### 📈 RR Interval Tachogram")
                tachogram_option = _build_rr_tachogram_chart(
                    time_s=t_s.tolist(),
                    rr_ms=rr_ms.tolist(),
                    title="RR Interval Time Series",
                )
                render_echarts(tachogram_option, height_px=350)

                # 2. PSD via Welch with frequency band annotations
                try:
                    from scipy.signal import welch  # type: ignore

                    fs = 1.0 / np.median(rr_s) if np.median(rr_s) > 0 else 1.0
                    # Limit segment length to keep computation fast
                    freqs, psd = welch(rr_ms, fs=fs, nperseg=min(1024, rr_ms.size))
                    
                    st.markdown("##### 📊 Power Spectral Density")
                    psd_option = _build_psd_chart(
                        freqs=freqs.tolist(),
                        psd=psd.tolist(),
                        title="HRV Frequency Domain Analysis",
                    )
                    render_echarts(psd_option, height_px=350)
                except Exception:
                    st.info("PSD preview unavailable (scipy.signal not available).")

                # 3. Histogram with normal distribution overlay
                st.markdown("##### 📊 RR Interval Distribution")
                hist_option = _build_rr_histogram_chart(
                    rr_ms=rr_ms.tolist(),
                    bins=30,
                    title="RR Interval Distribution",
                )
                render_echarts(hist_option, height_px=320)

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
    manual_processing_only = bool(st.session_state.get("manual_processing_only", True))

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
            safe_rerun("profile_tab_rerun")
    with col_b:
        if st.button(
            "🚀 Load + run HRV analysis",
            key=f"profile_rr_library_load_run_{user.user_id}",
            type="primary",
            use_container_width=True,
            disabled=manual_processing_only,
            help=(
                "Enable auto-run in Processing Mode to use this button."
                if manual_processing_only
                else "Loads recordings and starts HRV analysis."
            ),
        ):
            st.session_state["queued_rr_filepaths"] = _build_queue_payload()
            st.session_state["auto_run_hrv_analysis"] = True
            _set_current_user(user)
            st.success("Queued recordings and starting HRV analysis…")
            safe_rerun("profile_tab_rerun")


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
                safe_rerun("profile_tab_rerun")

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
            safe_rerun("profile_tab_rerun")


# =============================================================================
# Advanced HRV Analytics UI
# =============================================================================

_ADV_HRV_CACHE_TTL_SECONDS: Final[int] = 3600
_ADV_HRV_MAX_HASH_ROWS: Final[int] = 2000
_ADV_HRV_HASH_COLUMNS: Final[tuple[str, ...]] = (
    "measurement_date",
    "rmssd_ms",
    "sdnn_ms",
    "mean_hr_bpm",
    "lf_hf_ratio",
    "stress_index",
    "pnn50_pct",
    "hf_power_ms2",
    "lf_power_ms2",
)


def _hash_dataframe_for_advanced_hrv(
    df: pd.DataFrame,
    *,
    columns: Sequence[str] | None = None,
    max_rows: int = _ADV_HRV_MAX_HASH_ROWS,
) -> str:
    """Return a stable hash for advanced HRV inputs (bounded, deterministic)."""
    if df is None or df.empty:
        return "empty"
    working = df
    if columns:
        existing = [col for col in columns if col in working.columns]
        if existing:
            working = working[existing]
    if max_rows <= 0:
        max_rows = _ADV_HRV_MAX_HASH_ROWS
    if len(working) > max_rows:
        working = working.tail(int(max_rows))
    try:
        working = working.copy()
    except Exception:
        # If copy fails, fall back to the original object.
        pass
    try:
        working = working.sort_index(axis=1)
    except Exception:
        pass
    try:
        hashes = pd.util.hash_pandas_object(working, index=True)
        return hashlib.sha256(hashes.values.tobytes()).hexdigest()
    except Exception:
        # Defensive fallback for unexpected dtypes
        payload = working.to_json(orient="table", date_format="iso", default_handler=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _advanced_hrv_signature(
    *,
    hrv_df: pd.DataFrame,
    garmin_df: Optional[pd.DataFrame],
    user_age: int,
    user_sex: str,
) -> str:
    """Build a deterministic signature for advanced HRV analysis inputs."""
    hrv_hash = _hash_dataframe_for_advanced_hrv(
        hrv_df, columns=_ADV_HRV_HASH_COLUMNS
    )
    garmin_hash = (
        _hash_dataframe_for_advanced_hrv(garmin_df) if garmin_df is not None else "none"
    )
    seed = f"age={int(user_age)}|sex={str(user_sex)}|hrv={hrv_hash}|garmin={garmin_hash}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


@st.cache_data(ttl=_ADV_HRV_CACHE_TTL_SECONDS, max_entries=16, show_spinner=False)
def _cached_advanced_hrv_analysis(
    signature: str,
    hrv_df: pd.DataFrame,
    garmin_df: Optional[pd.DataFrame],
    user_age: int,
    user_sex: str,
) -> "AdvancedHRVAnalysisResult":
    """Cache wrapper for advanced HRV analysis (signature-guarded)."""
    _ = signature  # part of cache key; do not remove
    return run_advanced_hrv_analysis(
        hrv_df=hrv_df,
        garmin_df=garmin_df,
        user_age=user_age,
        user_sex=user_sex,
    )


def _render_advanced_hrv_analytics(
    user: UserProfile, hrv_df: pd.DataFrame, garmin_df: Optional[pd.DataFrame] = None
) -> None:
    """Render advanced HRV analytics with ML, statistics, and clinical decision support.
    
    Provides:
    - Statistical tests with p-values (Shapiro-Wilk, t-tests, Mann-Whitney)
    - ML pattern recognition and anomaly detection
    - Predictive trend analysis with forecasting
    - HRV + Garmin integration analysis
    - Semaphored clinical recommendations with gauges
    """
    st.markdown("### 🧬 Advanced HRV Analytics Platform")
    st.caption(
        "State-of-the-art statistical analysis, ML pattern recognition, and clinical decision support. "
        "Based on the Neurovisceral Integration Model (Thayer & Lane, 2009)."
    )
    
    # Educational intro checkbox
    if st.checkbox("📖 What is this? (Scientific Background)", value=False, key="adv_hrv_intro"):
        st.info("""
        **The Neurovisceral Integration Model**
        
        Heart rate variability (HRV) reflects the dynamic interplay between sympathetic and parasympathetic 
        branches of the autonomic nervous system (ANS). The **neurovisceral integration model** 
        (Thayer & Lane, 2000, 2009) proposes that HRV serves as an index of the functional integrity 
        of a central autonomic network (CAN) linking prefrontal cortex with brainstem cardiac control centers.
        
        **Why HRV Matters:**
        - **Higher HRV** = Greater physiological flexibility, better stress adaptation, healthy vagal tone
        - **Lower HRV** = Reduced adaptive capacity, chronic stress, elevated cardiovascular risk
        
        **Clinical Significance:**
        Low HRV independently predicts all-cause mortality, cardiovascular events, and mental health disorders. 
        This platform applies evidence-based statistical methods to help interpret your HRV patterns.
        
        **Key References:**
        - Task Force (1996). *Circulation, 93*(5), 1043-1065 — Gold standard HRV guidelines
        - Thayer et al. (2012). *Neurosci Biobehav Rev, 36*(2), 747-756 — Neurovisceral integration
        - Nunan et al. (2010). *PACE, 33*(11), 1407-1417 — Age-stratified reference values
        """)
    
    if not ADVANCED_HRV_ANALYTICS_AVAILABLE:
        st.warning(
            "Advanced HRV Analytics module not available. "
            "Ensure `advanced_hrv_analytics.py` is in the app directory."
        )
        return
    
    if hrv_df.empty or len(hrv_df) < 3:
        st.info(
            "At least 3 HRV recordings are required for advanced analytics. "
            "Current recordings: " + str(len(hrv_df) if not hrv_df.empty else 0)
        )
        return
    
    # Get user age and sex for reference-based analysis
    user_age = _calculate_age(user.date_of_birth) or 40
    user_sex = user.sex if user.sex else "unknown"
    
    signature = _advanced_hrv_signature(
        hrv_df=hrv_df,
        garmin_df=garmin_df,
        user_age=user_age,
        user_sex=user_sex,
    )
    state_key = f"_advanced_hrv_state_{user.user_id}"
    state = st.session_state.setdefault(
        state_key,
        {"signature": "", "result": None, "last_error": ""},
    )
    if state.get("signature") != signature:
        state["signature"] = signature
        state["result"] = None
        state["last_error"] = ""

    st.info(
        "Advanced analytics are paused by default to prevent repeated recomputation. "
        "Click **Run advanced analysis** to execute once for the current data."
    )
    run_label = (
        "🚀 Run advanced analysis"
        if state.get("result") is None
        else "🔄 Recompute advanced analysis"
    )
    if st.button(run_label, key=f"adv_hrv_run_{user.user_id}", use_container_width=True):
        try:
            with st.spinner("Running advanced analysis..."):
                result = _cached_advanced_hrv_analysis(
                    signature,
                    hrv_df,
                    garmin_df,
                    int(user_age),
                    str(user_sex),
                )
        except Exception as exc:
            state["last_error"] = str(exc)
            state["result"] = None
            st.error(f"Analysis failed: {exc}")
            _LOGGER.error("Advanced HRV analysis failed: %s", exc)
            return
        else:
            state["result"] = result
            state["last_error"] = ""

    result = state.get("result")
    if result is None:
        if state.get("last_error"):
            st.warning("Advanced analysis is unavailable due to the last error above.")
        else:
            st.caption("No advanced analysis computed yet for this dataset.")
        return
    
    # Create tabs for different analysis sections
    adv_tab1, adv_tab2, adv_tab3, adv_tab4, adv_tab5 = st.tabs([
        "🎯 Clinical Decision",
        "📊 Statistical Tests",
        "📈 Trends & Forecast",
        "🔍 Anomalies & Patterns",
        "🔗 HRV + Garmin",
    ])
    
    with adv_tab1:
        _render_clinical_decision_tab(result)
    
    with adv_tab2:
        _render_statistical_tests_tab(result)
    
    with adv_tab3:
        _render_trends_forecast_tab(result, hrv_df)
    
    with adv_tab4:
        _render_anomalies_patterns_tab(result)
    
    with adv_tab5:
        _render_hrv_garmin_integration_tab(result, garmin_df is not None)


def _risk_level_to_color(risk: "HRVRiskLevel") -> str:
    """Convert risk level to color for display."""
    return {
        HRVRiskLevel.GREEN: "#28a745",
        HRVRiskLevel.YELLOW: "#ffc107",
        HRVRiskLevel.ORANGE: "#fd7e14",
        HRVRiskLevel.RED: "#dc3545",
    }.get(risk, "#6c757d")


def _risk_level_to_emoji(risk: "HRVRiskLevel") -> str:
    """Convert risk level to emoji."""
    return {
        HRVRiskLevel.GREEN: "🟢",
        HRVRiskLevel.YELLOW: "🟡",
        HRVRiskLevel.ORANGE: "🟠",
        HRVRiskLevel.RED: "🔴",
    }.get(risk, "⚪")


def _render_clinical_decision_tab(result: "AdvancedHRVAnalysisResult") -> None:
    """Render clinical decision support with gauges and semaphored recommendations."""
    cds = result.clinical_decision
    
    # Educational intro for Clinical Decision tab
    if st.checkbox("📖 Understanding Clinical Decision Support", value=False, key="cds_edu"):
        st.info("""
        **What This Tab Shows**
        
        This tab synthesizes your HRV data into actionable clinical insights using evidence-based thresholds.
        
        **Autonomic Balance Score (0-100):**
        - Combines RMSSD deviation from age norms, Stress Index (Baevsky), and LF/HF considerations
        - **Score >70**: Parasympathetic dominant — rest-and-digest physiology, good recovery
        - **Score 50-70**: Balanced — healthy autonomic regulation, adaptive stress response
        - **Score 30-50**: Sympathetic shift — elevated stress response, monitor closely
        - **Score <30**: Dysregulated — consider lifestyle factors or medical consultation
        
        **Autonomic States (LF/HF Ratio):**
        - **Parasympathetic** (<0.8): High vagal tone; typical during deep relaxation or in trained athletes
        - **Balanced** (0.8-2.0): Homeostatic equilibrium; optimal for adaptive function
        - **Sympathetic** (>3.0): Fight-or-flight activation; may indicate stress or physical exertion
        
        **Z-Scores:** Standardized comparison to population norms. |Z| > 2.0 indicates clinically significant deviation.
        
        *Reference: Thayer & Lane (2009). Neurosci Biobehav Rev, 33(2), 81-88*
        """)
    
    # Overall Status Header with colored badge
    status_color = _risk_level_to_color(cds.overall_status)
    status_emoji = _risk_level_to_emoji(cds.overall_status)
    
    st.markdown(
        f"""<div style="background: linear-gradient(135deg, {status_color}22, {status_color}11); 
            border-left: 4px solid {status_color}; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <span style="font-size: 28px; font-weight: bold; color: {status_color};">
                {status_emoji} {cds.status_label}
            </span>
            <br/>
            <span style="color: #666; font-size: 14px;">{cds.summary.replace(chr(10), '<br/>')}</span>
        </div>""",
        unsafe_allow_html=True,
    )
    
    # Autonomic Balance Gauge
    st.markdown("#### ⚖️ Autonomic Balance Score")
    balance_score = result.autonomic_balance_score
    
    # Build gauge using ECharts
    gauge_option = {
        "series": [
            {
                "type": "gauge",
                "startAngle": 180,
                "endAngle": 0,
                "min": 0,
                "max": 100,
                "splitNumber": 5,
                "radius": "100%",
                "center": ["50%", "75%"],
                "axisLine": {
                    "lineStyle": {
                        "width": 20,
                        "color": [
                            [0.3, "#dc3545"],  # 0-30: Red (Dysregulated)
                            [0.5, "#fd7e14"],  # 30-50: Orange (Sympathetic)
                            [0.7, "#28a745"],  # 50-70: Green (Balanced)
                            [1.0, "#17a2b8"],  # 70-100: Blue (Parasympathetic)
                        ],
                    },
                },
                "pointer": {
                    "length": "60%",
                    "width": 6,
                    "itemStyle": {"color": "#333"},
                },
                "axisTick": {"show": False},
                "splitLine": {"show": False},
                "axisLabel": {"show": False},
                "detail": {"show": False},
                "title": {"show": False},
                "data": [{"value": round(balance_score, 1)}],
            }
        ],
    }
    render_echarts(gauge_option, height_px=180)
    
    # Status text below gauge
    state_label = cds.autonomic_state.value.replace("_", " ").title()
    st.markdown(
        f"""<div style="text-align: center; margin-top: -10px;">
            <span style="font-size: 24px; font-weight: bold; color: {status_color};">
                {balance_score:.0f}/100
            </span><br/>
            <span style="font-size: 14px; color: #666;">
                Autonomic State: {state_label}
            </span>
        </div>""",
        unsafe_allow_html=True,
    )
    
    # Metric Assessments Table
    st.markdown("#### 📋 Metric Assessments")
    if cds.metric_assessments:
        assess_rows = []
        for ma in cds.metric_assessments:
            emoji = _risk_level_to_emoji(ma.risk_level)
            assess_rows.append({
                "Status": emoji,
                "Metric": ma.metric_name.replace("_", " ").upper(),
                "Value": f"{ma.value:.2f} {ma.unit}",
                "Z-Score": f"{ma.z_score:.2f}" if ma.z_score else "—",
                "Percentile": f"{ma.percentile:.1f}th" if ma.percentile else "—",
                "Reference": f"{ma.reference_range[0]:.1f}–{ma.reference_range[1]:.1f}" if ma.reference_range else "—",
                "Interpretation": ma.interpretation,
            })
        st.dataframe(pd.DataFrame(assess_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No metric assessments available.")
    
    # Alerts
    if cds.alerts:
        st.markdown("#### ⚠️ Alerts")
        for alert in cds.alerts:
            st.warning(alert)
    
    # Recommendations with semaphore colors
    st.markdown("#### 💡 Recommendations")
    if cds.recommendations:
        for rec in cds.recommendations:
            # Color-code based on content
            if any(w in rec.lower() for w in ["red", "alert", "consult", "immediate"]):
                st.error(rec)
            elif any(w in rec.lower() for w in ["orange", "caution", "monitor", "elevated"]):
                st.warning(rec)
            elif any(w in rec.lower() for w in ["yellow", "consider", "track"]):
                st.info(rec)
            else:
                st.success(rec)
    else:
        st.success("✅ No specific recommendations at this time. Maintain current practices.")


def _render_statistical_tests_tab(result: "AdvancedHRVAnalysisResult") -> None:
    """Render statistical tests results with p-values."""
    st.markdown("#### 📊 Statistical Analysis Results")
    
    # Educational intro for Statistical Tests tab
    if st.checkbox("📖 Understanding Statistical Tests", value=False, key="stat_edu"):
        st.info("""
        **Why Statistical Tests Matter**
        
        Statistical tests determine whether your HRV values differ significantly from healthy reference populations, 
        accounting for natural biological variability. This helps distinguish genuine physiological differences 
        from random fluctuation.
        
        **Descriptive Statistics:**
        - **Mean/Median**: Central tendency of your HRV distribution
        - **SD (Standard Deviation)**: Total variability — reflects overall ANS flexibility
        - **CV% (Coefficient of Variation)**: Normalized variability allowing cross-metric comparison
        - **Skewness**: Distribution asymmetry (HRV data often shows positive skew)
        - **Kurtosis**: Tail heaviness — excess kurtosis indicates outlier-prone measurements
        
        **Normality Testing (Shapiro-Wilk):**
        Tests whether your data follows a Gaussian distribution. HRV metrics often require 
        log-transformation (lnRMSSD) for parametric analysis due to inherent positive skewness.
        - p > 0.05: Data approximately normal → parametric tests appropriate
        - p ≤ 0.05: Non-normal → consider non-parametric alternatives
        
        **Reference Comparison (t-test vs Mann-Whitney):**
        Compares your mean against age-stratified population values (Nunan et al., 2010).
        - **p < 0.05**: Your HRV differs significantly from age-matched healthy population
        - **Effect size (Cohen's d)**: Practical significance — d > 0.8 is clinically meaningful
        
        *References: Task Force (1996), Shapiro & Wilk (1965), Cohen (1988)*
        """)
    
    st.caption(
        "p-values < 0.05 indicate statistically significant differences from reference populations."
    )
    
    # Descriptive Statistics
    st.markdown("##### 📈 Descriptive Statistics")
    if result.descriptive_stats:
        desc_rows = []
        for metric, stats in result.descriptive_stats.items():
            desc_rows.append({
                "Metric": metric.replace("_", " ").upper(),
                "N": int(stats.get("n", 0)),
                "Mean": f"{stats.get('mean', 0):.2f}",
                "SD": f"{stats.get('std', 0):.2f}",
                "Median": f"{stats.get('median', 0):.2f}",
                "CV%": f"{stats.get('cv_pct', 0):.1f}",
                "IQR": f"{stats.get('iqr', 0):.2f}",
                "Skewness": f"{stats.get('skewness', 0):.3f}",
                "Kurtosis": f"{stats.get('kurtosis', 0):.3f}",
            })
        if desc_rows:
            st.dataframe(pd.DataFrame(desc_rows), use_container_width=True, hide_index=True)
    
    # Normality Tests
    st.markdown("##### 🔔 Normality Tests (Shapiro-Wilk)")
    if result.normality_tests:
        norm_rows = []
        for metric, test in result.normality_tests.items():
            norm_rows.append({
                "Metric": metric.replace("_", " ").upper(),
                "Test": test.test_name,
                "W-Statistic": f"{test.statistic:.4f}" if not np.isnan(test.statistic) else "—",
                "p-value": f"{test.p_value:.4f}" if not np.isnan(test.p_value) else "—",
                "Significant": "Yes ⚠️" if test.is_significant else "No ✓",
                "Interpretation": test.interpretation,
            })
        if norm_rows:
            st.dataframe(pd.DataFrame(norm_rows), use_container_width=True, hide_index=True)
    
    # Comparison Tests
    st.markdown("##### 🆚 Comparison Tests (vs Reference)")
    if result.comparison_tests:
        comp_rows = []
        for test_name, test in result.comparison_tests.items():
            if "Shapiro" in test_name:  # Skip normality tests here
                continue
            comp_rows.append({
                "Test": test_name,
                "Statistic": f"{test.statistic:.4f}" if not np.isnan(test.statistic) else "—",
                "p-value": f"{test.p_value:.4f}" if not np.isnan(test.p_value) else "—",
                "Effect Size": f"{test.effect_size:.4f}" if test.effect_size else "—",
                "Effect Label": test.effect_label or "—",
                "Significant": "Yes ⚠️" if test.is_significant else "No ✓",
                "Interpretation": test.interpretation,
            })
        if comp_rows:
            st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No comparison tests available. More data may be needed.")
    
    # Statistical Interpretation Guide (using checkbox to avoid nested expanders)
    if st.checkbox("📚 Statistical Test Interpretation Guide", value=False, key="stat_test_guide"):
        st.markdown("""
        **Shapiro-Wilk Test (Normality)**
        - Tests if data follows a normal (Gaussian) distribution
        - p > 0.05: Data appears normally distributed
        - p ≤ 0.05: Data significantly deviates from normality
        
        **One-Sample t-Test**
        - Compares your mean to a reference population mean
        - Uses age-stratified reference values (Nunan et al. 2010)
        - Effect size (Cohen's d): |d| < 0.2 negligible, 0.2-0.5 small, 0.5-0.8 medium, > 0.8 large
        
        **Mann-Whitney U Test**
        - Non-parametric alternative when normality is violated
        - Compares median ranks rather than means
        
        **Significance Level (α = 0.05)**
        - p < 0.05: Statistically significant (reject null hypothesis)
        - p ≥ 0.05: Not statistically significant
        
        **References:**
        - Task Force (1996). Circulation 93(5):1043-65
        - Nunan et al. (2010). Scand J Med Sci Sports 20(1):e30-44
        - Cohen (1988). Statistical Power Analysis
        """)


def _render_trends_forecast_tab(result: "AdvancedHRVAnalysisResult", hrv_df: pd.DataFrame) -> None:
    """Render trend analysis and forecasting."""
    st.markdown("#### 📈 Trend Analysis & Forecasting")
    
    # Educational intro for Trends tab
    if st.checkbox("📖 Understanding HRV Trends", value=False, key="trend_edu"):
        st.info("""
        **Why Track HRV Trends?**
        
        Day-to-day HRV fluctuations reflect the integration of multiple physiological inputs:
        
        **Factors That Reduce HRV:**
        - Poor sleep quality or duration (Tobaldini et al., 2013)
        - Overtraining or inadequate recovery (Plews et al., 2013)
        - Psychological stress — acute or chronic (Lennartsson et al., 2016)
        - Illness and systemic inflammation (Thayer & Sternberg, 2006)
        - Alcohol consumption within 24 hours
        
        **Factors That Increase HRV:**
        - Quality sleep (7-9 hours)
        - Appropriate physical training with recovery
        - Stress management and relaxation practices
        - Consistent measurement conditions
        
        **Interpreting the Trend:**
        - **Slope (β₁)**: Rate of change per day. Positive = improving, negative = declining
        - **R²**: How well the linear model fits your data (>0.5 = moderate-good fit)
        - **p-value**: Statistical significance of the trend (p < 0.05 = genuine trend)
        - **% Change**: Total change over the analysis period
        
        **7-Day Forecast:**
        Linear extrapolation with 95% confidence intervals. Wide intervals indicate variable HRV patterns.
        
        ⚠️ **Caution**: Forecasts assume trend continuation. Sudden stressors can invalidate predictions.
        
        *Reference: Plews et al. (2013). Sports Medicine, 43(9), 773-781*
        """)
    
    if not result.trend_analyses:
        st.info("Not enough temporal data for trend analysis. At least 5 recordings with dates required.")
        return
    
    # Trend Summary Table
    trend_rows = []
    for metric, trend in result.trend_analyses.items():
        direction_emoji = {
            HRVTrendDirection.IMPROVING: "📈",
            HRVTrendDirection.STABLE: "➡️",
            HRVTrendDirection.DECLINING: "📉",
            HRVTrendDirection.UNKNOWN: "❓",
        }.get(trend.direction, "❓")
        
        trend_rows.append({
            "Metric": metric.replace("_", " ").upper(),
            "Trend": f"{direction_emoji} {trend.direction.value.title()}",
            "Slope": f"{trend.slope:.4f}/day",
            "p-value": f"{trend.slope_p_value:.4f}",
            "R²": f"{trend.r_squared:.4f}",
            "% Change": f"{trend.percent_change:+.1f}%",
            "Days Analyzed": trend.days_analyzed,
            "Significant": "Yes ⚠️" if trend.is_significant else "No",
        })
    
    st.dataframe(pd.DataFrame(trend_rows), use_container_width=True, hide_index=True)
    
    # 7-Day Forecast
    st.markdown("##### 🔮 7-Day Forecast")
    if result.forecasts:
        for metric, forecast in result.forecasts.items():
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    f"{metric.replace('_', ' ').upper()} (Forecast)",
                    f"{forecast['forecast_7d']:.2f}",
                )
            with col2:
                st.metric("Lower 95% CI", f"{forecast['lower_ci']:.2f}")
            with col3:
                st.metric("Upper 95% CI", f"{forecast['upper_ci']:.2f}")
    else:
        st.info("Forecasts not available.")
    
    # Trend Visualization (if RMSSD available)
    if "rmssd_ms" in hrv_df.columns and "measurement_date" in hrv_df.columns:
        st.markdown("##### 📊 RMSSD Trend Visualization")
        st.caption(
            "Publication-quality trend analysis with age-adjusted normal ranges. "
            "Reference: Nunan et al. (2010), Shaffer & Ginsberg (2017)."
        )
        
        trend_df = hrv_df[["measurement_date", "rmssd_ms"]].dropna()
        if len(trend_df) >= 5:
            trend_df = trend_df.sort_values("measurement_date")
            
            # Get user age for normative ranges (default to 35 if not available)
            user_age = 35
            try:
                user_context = get_active_user_context()
                user_age = user_context.get("age_years", 35) or 35
            except Exception:
                pass
            
            # Build publication-quality trend chart
            dates = trend_df["measurement_date"].astype(str).tolist()
            values = trend_df["rmssd_ms"].tolist()
            
            trend_option = _build_rmssd_trend_chart(
                dates=dates,
                values=values,
                age=int(user_age),
                title="RMSSD Longitudinal Trend with Age-Adjusted Normal Range",
            )
            render_echarts(trend_option, height_px=420)
            
            # Summary statistics
            norms = _get_age_rmssd_norms(int(user_age))
            rmssd_mean = np.mean(values)
            rmssd_sd = np.std(values)
            pct_in_normal = sum(1 for v in values if norms["p5"] <= v <= norms["p95"]) / len(values) * 100
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Your Mean RMSSD", f"{rmssd_mean:.1f} ms")
            with col2:
                st.metric("Your SD", f"{rmssd_sd:.1f} ms")
            with col3:
                st.metric("Population Mean", f"{norms['mean']:.1f} ms")
            with col4:
                delta_color = "normal" if pct_in_normal >= 70 else "inverse"
                st.metric("% in Normal Range", f"{pct_in_normal:.0f}%", delta_color=delta_color)


def _render_anomalies_patterns_tab(result: "AdvancedHRVAnalysisResult") -> None:
    """Render anomaly detection and pattern recognition results."""
    cds = result.clinical_decision
    
    # Educational intro for Anomalies tab
    if st.checkbox("📖 Understanding Anomalies & Patterns", value=False, key="anomaly_edu"):
        st.info("""
        **Anomaly Detection Methods**
        
        Anomalies are recordings that deviate significantly from your typical pattern. Two methods are used:
        
        **Z-Score Method:**
        Flags recordings where |Z| > 2.5 standard deviations from your personal mean.
        - **Unusually LOW RMSSD**: May indicate acute illness, severe stress, cardiac arrhythmia, or measurement artifact
        - **Unusually HIGH RMSSD**: May indicate post-exercise parasympathetic rebound or measurement error
        
        **IQR Method (Robust):**
        Flags values outside Q₁ - 1.5×IQR or Q₃ + 1.5×IQR. Resistant to non-normal distributions.
        
        **Pattern Recognition**
        
        The platform identifies recurring patterns in your data:
        
        **RMSSD Variability (CV%):**
        - CV < 15%: Very stable — excellent for trend detection
        - CV 15-40%: Normal day-to-day variation
        - CV > 40%: High variability — consider standardizing measurement protocol
        
        **Chronic Stress Pattern:**
        Detected when >50% of recordings show Stress Index > 150. Sustained sympathetic dominance 
        is associated with increased cardiovascular risk and impaired cognitive performance.
        
        **What to Do with Anomalies:**
        1. Review measurement conditions on flagged dates
        2. Check for confounders (illness, travel, poor sleep, alcohol)
        3. If genuine, investigate underlying cause
        
        *References: Thayer et al. (2012), Plews et al. (2013)*
        """)
    
    # Anomaly Detection
    st.markdown("#### 🔍 Anomaly Detection")
    if cds.anomaly_detection:
        ad = cds.anomaly_detection
        if ad.n_anomalies > 0:
            st.warning(f"**{ad.n_anomalies} anomalous recording(s) detected** using {ad.method} method (threshold: {ad.threshold_used})")
            
            anomaly_rows = []
            for i, idx in enumerate(ad.anomaly_indices):
                anomaly_rows.append({
                    "Index": idx,
                    "Date": str(ad.anomaly_dates[i]) if i < len(ad.anomaly_dates) else "—",
                    "Anomaly Score": f"{ad.anomaly_scores[i]:.2f}" if i < len(ad.anomaly_scores) else "—",
                })
            if anomaly_rows:
                st.dataframe(pd.DataFrame(anomaly_rows), use_container_width=True, hide_index=True)
            
            st.info(ad.interpretation)
        else:
            st.success("✅ No anomalies detected in your HRV recordings.")
    else:
        st.info("Anomaly detection requires at least 5 recordings.")
    
    # Pattern Recognition
    st.markdown("#### 🧩 Pattern Recognition")
    if cds.pattern_recognition:
        pr = cds.pattern_recognition
        
        if pr.dominant_pattern:
            confidence_pct = (pr.pattern_confidence or 0.5) * 100
            st.info(f"**Dominant Pattern:** {pr.dominant_pattern} (Confidence: {confidence_pct:.0f}%)")
        
        if pr.detected_patterns:
            st.markdown("**Detected Patterns:**")
            for pattern in pr.detected_patterns:
                if "improving" in pattern.lower() or "excellent" in pattern.lower():
                    st.success(f"✓ {pattern}")
                elif "declining" in pattern.lower() or "chronic" in pattern.lower():
                    st.warning(f"⚠ {pattern}")
                else:
                    st.info(f"• {pattern}")
        
        if pr.silhouette_score:
            st.metric("Cluster Quality (Silhouette)", f"{pr.silhouette_score:.3f}")
    else:
        st.info("Pattern recognition requires at least 5 recordings.")
    
    # Pattern Interpretation Guide (using checkbox to avoid nested expanders)
    if st.checkbox("📚 Pattern Interpretation Guide", value=False, key="pattern_guide"):
        st.markdown("""
        **RMSSD Variability (CV%)**
        - CV > 40%: High day-to-day variability - may indicate inconsistent recovery or measurement conditions
        - CV 15-40%: Normal variability
        - CV < 15%: Very stable pattern - good for trend detection
        
        **Autonomic Balance Patterns**
        - Parasympathetic dominant (LF/HF < 0.8): Rest & digest mode, good recovery
        - Balanced (LF/HF 0.8-2.0): Healthy autonomic regulation
        - Sympathetic dominant (LF/HF > 3.0): Fight-or-flight mode, stress response
        
        **Chronic Stress Pattern**
        - >50% of recordings with Stress Index > 150 suggests sustained physiological stress
        - Consider lifestyle factors: sleep, exercise, mental stress, diet
        
        **References:**
        - Thayer et al. (2012). Neurosci Biobehav Rev 36(2):747-56
        - Ernst (2017). J Integr Neurosci 16(1):17-42
        """)


def _render_hrv_garmin_integration_tab(
    result: "AdvancedHRVAnalysisResult", has_garmin: bool
) -> None:
    """Render HRV + Garmin integration analysis."""
    st.markdown("#### 🔗 HRV + Garmin Wearable Integration")
    
    # Educational intro for Integration tab
    if st.checkbox("📖 Understanding Multi-Device Integration", value=False, key="integration_edu"):
        st.info("""
        **Why Cross-Validate HRV with Wearables?**
        
        Consumer wearables (Garmin, Oura, Whoop) provide continuous physiological monitoring but with 
        varying accuracy compared to research-grade ECG (Polar H10). Cross-validation identifies:
        
        **Concordance (Agreement):**
        Agreement between sources strengthens confidence in the data. High concordance (>70%) indicates 
        reliable measurements.
        
        **Discordance (Disagreement):**
        Disagreement warrants investigation:
        - **Timing mismatch**: Garmin averages overnight; Polar captures a morning snapshot
        - **Algorithm differences**: Proprietary Garmin algorithms weight factors differently
        - **Measurement artifact**: Wrist-based PPG is susceptible to motion artifact
        
        **Device Validation Evidence:**
        | Device | RMSSD Accuracy (CCC) | Source |
        |--------|---------------------|--------|
        | Polar H10 | 0.97-0.99 | Gold standard |
        | Oura Ring | 0.97-0.99 | Dial et al. (2025) |
        | Garmin (wrist) | 0.87 | Dial et al. (2025) |
        | Whoop 4.0 | 0.94 | Dial et al. (2025) |
        
        **Expected Correlations:**
        - RMSSD ↔ Body Battery: Moderate positive (r ≈ 0.3-0.5)
        - Stress Index ↔ Garmin Stress: Moderate positive (r ≈ 0.4-0.6)
        - SDNN ↔ Sleep Score: Moderate positive (r ≈ 0.3-0.5)
        
        **Spearman ρ Interpretation:**
        - |ρ| > 0.7: Strong correlation
        - |ρ| 0.4-0.7: Moderate correlation
        - |ρ| < 0.4: Weak correlation
        
        *References: Miller et al. (2022). Sensors, 22(16), 6317; Dial et al. (2025). Physiol Rep, 13(2)*
        """)
    
    if not has_garmin:
        st.info(
            "No Garmin daily metrics available for integration analysis. "
            "Import Garmin data from the 📦 Data section to enable this feature."
        )
        return
    
    cds = result.clinical_decision
    if not cds.garmin_integration:
        st.info(
            "Not enough overlapping data between HRV and Garmin metrics. "
            "Ensure HRV measurements and Garmin data are from the same time period."
        )
        return
    
    gi = cds.garmin_integration
    
    # Concordance Score
    st.markdown("##### 📐 Data Concordance")
    concordance_pct = gi.concordance_score * 100
    
    col1, col2 = st.columns(2)
    with col1:
        if concordance_pct >= 70:
            st.success(f"**Concordance Score:** {concordance_pct:.0f}%")
            st.caption("High agreement between HRV measurements and wearable metrics.")
        elif concordance_pct >= 50:
            st.warning(f"**Concordance Score:** {concordance_pct:.0f}%")
            st.caption("Moderate agreement. Some metrics may differ.")
        else:
            st.error(f"**Concordance Score:** {concordance_pct:.0f}%")
            st.caption("Low agreement. Review measurement conditions.")
    
    with col2:
        st.metric("Integrated Recovery Score", f"{gi.integrated_recovery_score:.0f}/100")
        st.metric("Integrated Stress Score", f"{gi.integrated_stress_score:.0f}/100")
    
    # Discordance Flags
    if gi.discordance_flags:
        st.markdown("##### ⚠️ Discordance Flags")
        for flag in gi.discordance_flags:
            st.warning(flag)
    
    # Correlation Matrix
    st.markdown("##### 📊 Cross-Correlation Analysis")
    if gi.correlation_matrix:
        # Flatten to table
        corr_rows = []
        for hrv_metric, garmin_corrs in gi.correlation_matrix.items():
            for garmin_metric, r in garmin_corrs.items():
                corr_rows.append({
                    "HRV Metric": hrv_metric.replace("_", " ").upper(),
                    "Garmin Metric": garmin_metric.replace("_", " ").title(),
                    "Spearman ρ": f"{r:.3f}",
                    "Strength": "Strong" if abs(r) > 0.7 else "Moderate" if abs(r) > 0.4 else "Weak",
                })
        if corr_rows:
            st.dataframe(pd.DataFrame(corr_rows), use_container_width=True, hide_index=True)
    
    # Significant Correlations
    if gi.significant_correlations:
        st.markdown("##### ✨ Statistically Significant Correlations (p < 0.05)")
        for hrv_m, garmin_m, r, p in gi.significant_correlations:
            direction = "positive" if r > 0 else "negative"
            st.info(f"**{hrv_m}** ↔ **{garmin_m}**: ρ = {r:.3f} (p = {p:.4f}) — {direction.title()} correlation")
    
    # Integration Recommendations
    if gi.recommendations:
        st.markdown("##### 💡 Integration Insights")
        for rec in gi.recommendations:
            if "⚠️" in rec or "low agreement" in rec.lower():
                st.warning(rec)
            elif "🔴" in rec or "elevated" in rec.lower():
                st.error(rec)
            elif "🟡" in rec or "below" in rec.lower():
                st.info(rec)
            else:
                st.success(rec)


# Module-level cached loader for HRV history (moved outside render function for stable caching)
@st.cache_data(ttl=300, max_entries=64, show_spinner=False)
def _load_hrv_history_dataframe_cached(
    uid: str,
    limit: int,
    refresh_token: int,
) -> pd.DataFrame:
    """Load HRV history DataFrame from database with caching.
    
    This function is intentionally at module level (not inside a render function)
    to ensure the cache decorator works correctly across reruns.
    
    Args:
        uid: User ID.
        limit: Maximum number of records to load.
        refresh_token: Cache-busting token (increment to force refresh).
        
    Returns:
        DataFrame with HRV measurements.
    """
    _ = refresh_token  # Used only to bust cache when explicitly requested
    db = get_database()
    return db.get_hrv_dataframe(uid, limit=limit, include_rr=False)


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
            safe_rerun("profile_tab_rerun")
    with col_meta:
        st.caption("If charts look stale after new uploads/analysis, regenerate to refresh them.")
    
    try:
        with st.spinner("Loading HRV measurements..."):
            df = _load_hrv_history_dataframe_cached(user.user_id, 500, refresh_token)
        
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

        show_hrv_charts = True
        show_baseline = True
        show_advanced = True
        show_table = True

        # Get user age for normative reference
        user_age = 35
        if show_hrv_charts:
            try:
                user_context = get_active_user_context()
                user_age = user_context.get("age_years", 35) or 35
            except Exception:
                pass
        
        # === PUBLICATION-QUALITY HRV TIME-DOMAIN TREND CHART ===
        if show_hrv_charts and len(df) > 1 and "measurement_date" in df.columns and "rmssd_ms" in df.columns:
            st.markdown("##### 📈 HRV Time-Domain Metrics with Age-Adjusted Reference Ranges")
            st.caption(
                "Publication-quality visualization showing RMSSD and SDNN trends with age-stratified "
                "normative bands. Shaded regions indicate 5th-95th percentile population ranges. "
                "Reference: Nunan et al. (2010), Shaffer & Ginsberg (2017)."
            )
            
            trend_df = df[["measurement_date", "rmssd_ms"]].dropna()
            trend_df = trend_df.sort_values("measurement_date")
            
            if len(trend_df) >= 3:
                dates = trend_df["measurement_date"].astype(str).tolist()
                rmssd_values = trend_df["rmssd_ms"].tolist()
                
                # Include SDNN if available
                sdnn_values = None
                if "sdnn_ms" in df.columns:
                    sdnn_df = df[["measurement_date", "sdnn_ms"]].dropna()
                    if len(sdnn_df) >= 3:
                        sdnn_merged = trend_df.merge(
                            sdnn_df, on="measurement_date", how="left"
                        )
                        sdnn_values = sdnn_merged["sdnn_ms"].tolist()
                
                hrv_chart = _build_hrv_history_dual_axis_chart(
                    dates=dates,
                    rmssd_values=rmssd_values,
                    sdnn_values=sdnn_values,
                    age=int(user_age),
                    title="HRV Time-Domain Metrics with Age-Adjusted Reference Ranges",
                )
                render_echarts(hrv_chart, height_px=420)
                
                # Summary statistics with percentile interpretation
                norms = _get_age_rmssd_norms(int(user_age))
                rmssd_mean = float(np.mean(rmssd_values))
                rmssd_latest = rmssd_values[-1] if rmssd_values else 0
                pct_in_normal = sum(
                    1 for v in rmssd_values if norms["p5"] <= v <= norms["p95"]
                ) / len(rmssd_values) * 100
                
                # Calculate percentile position of latest value
                if rmssd_latest <= norms["p5"]:
                    percentile_desc = "below 5th percentile (low)"
                elif rmssd_latest <= norms["p25"]:
                    percentile_desc = "5th-25th percentile (below average)"
                elif rmssd_latest <= norms["p50"]:
                    percentile_desc = "25th-50th percentile (average)"
                elif rmssd_latest <= norms["p75"]:
                    percentile_desc = "50th-75th percentile (above average)"
                elif rmssd_latest <= norms["p95"]:
                    percentile_desc = "75th-95th percentile (high)"
                else:
                    percentile_desc = "above 95th percentile (very high)"
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Your Mean RMSSD", f"{rmssd_mean:.1f} ms")
                with col2:
                    st.metric("Latest RMSSD", f"{rmssd_latest:.1f} ms")
                with col3:
                    st.metric("Population Mean", f"{norms['mean']:.1f} ms")
                with col4:
                    delta_color = "normal" if pct_in_normal >= 70 else "inverse"
                    st.metric("% in Normal Range", f"{pct_in_normal:.0f}%", delta_color=delta_color)
                
                st.caption(f"Your latest RMSSD ({rmssd_latest:.1f} ms) is in the **{percentile_desc}** "
                          f"for your age group ({_get_age_group_label(int(user_age))}).")
                
                # Physiological interpretation expandables
                col_interp1, col_interp2 = st.columns(2)
                with col_interp1:
                    with st.expander("📖 What is RMSSD? (Physiological Interpretation)", expanded=False):
                        st.markdown(HRV_PHYSIOLOGICAL_INTERPRETATIONS["rmssd"])
                with col_interp2:
                    with st.expander("📖 What is SDNN? (Physiological Interpretation)", expanded=False):
                        st.markdown(HRV_PHYSIOLOGICAL_INTERPRETATIONS["sdnn"])

        # Longitudinal baseline/change analytics (T0–T21)
        with st.expander("🧪 Baseline / Δ by timepoint (T0–T21)", expanded=False):
            if not show_baseline:
                st.info("Enable **Show baseline/timepoint analysis** to render this section.")
            else:
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

        # Additional performance & recovery visuals with publication-quality charts
        with st.expander("🏃 Performance & Recovery Plots (Publication Quality)", expanded=False):
            if not show_hrv_charts:
                st.info("Enable **Show HRV charts** to render this section.")
            else:
                st.markdown("""
                **Scientific Background:** These visualizations follow guidelines from Nature Research 
                and incorporate age-stratified normative data for clinical interpretation. 
                Each metric provides insight into different aspects of autonomic function and recovery capacity.
                """)
                
                # === Heart Rate Trend with Age-Based Reference ===
                if "mean_hr_bpm" in df.columns and df["mean_hr_bpm"].notna().any():
                    hr_df = df[["measurement_date", "mean_hr_bpm"]].dropna()
                    hr_df = hr_df.sort_values("measurement_date")
                    if len(hr_df) >= 3:
                        st.markdown("##### ❤️ Resting Heart Rate Trend")
                        hr_chart = _build_hr_trend_chart(
                            dates=hr_df["measurement_date"].astype(str).tolist(),
                            hr_values=hr_df["mean_hr_bpm"].tolist(),
                            age=int(user_age),
                            title="Resting Heart Rate with Physiological Zones",
                        )
                        render_echarts(hr_chart, height_px=350)
                
                # === LF/HF Ratio (Sympathovagal Balance) ===
                if "lf_hf_ratio" in df.columns and df["lf_hf_ratio"].notna().any():
                    lf_hf_df = df[["measurement_date", "lf_hf_ratio"]].dropna()
                    lf_hf_df = lf_hf_df.sort_values("measurement_date")
                    if len(lf_hf_df) >= 3:
                        st.markdown("##### ⚖️ Sympathovagal Balance (LF/HF Ratio)")
                        lf_hf_chart = _build_lf_hf_trend_chart(
                            dates=lf_hf_df["measurement_date"].astype(str).tolist(),
                            lf_hf_values=lf_hf_df["lf_hf_ratio"].tolist(),
                            age=int(user_age),
                            title="LF/HF Ratio Trend with Autonomic Interpretation",
                        )
                        render_echarts(lf_hf_chart, height_px=350)
                
                # === Autonomic Indices (Stress, PNS, HRV Score) ===
                stress_vals = None
                pns_vals = None
                hrv_score_vals = None
                idx_dates = None
                
                if "stress_index" in df.columns and df["stress_index"].notna().any():
                    stress_df = df[["measurement_date", "stress_index"]].dropna()
                    if len(stress_df) >= 3:
                        stress_df = stress_df.sort_values("measurement_date")
                        idx_dates = stress_df["measurement_date"].astype(str).tolist()
                        stress_vals = stress_df["stress_index"].tolist()
                
                if "parasympathetic_index" in df.columns and df["parasympathetic_index"].notna().any():
                    pns_df = df[["measurement_date", "parasympathetic_index"]].dropna()
                    if len(pns_df) >= 3:
                        pns_df = pns_df.sort_values("measurement_date")
                        if idx_dates is None:
                            idx_dates = pns_df["measurement_date"].astype(str).tolist()
                        pns_vals = pns_df["parasympathetic_index"].tolist()
                
                if "hrv_score" in df.columns and df["hrv_score"].notna().any():
                    score_df = df[["measurement_date", "hrv_score"]].dropna()
                    if len(score_df) >= 3:
                        score_df = score_df.sort_values("measurement_date")
                        if idx_dates is None:
                            idx_dates = score_df["measurement_date"].astype(str).tolist()
                        hrv_score_vals = score_df["hrv_score"].tolist()
                
                if idx_dates and (stress_vals or pns_vals or hrv_score_vals):
                    st.markdown("##### 📊 Autonomic Function Indices")
                    idx_chart = _build_autonomic_indices_chart(
                        dates=idx_dates,
                        stress_index=stress_vals,
                        parasympathetic_index=pns_vals,
                        hrv_score=hrv_score_vals,
                        title="Autonomic Function Indices Over Time",
                    )
                    render_echarts(idx_chart, height_px=380)
                
                # === lnRMSSD Trend (Athletic Performance Tracking) ===
                if "rmssd_ms" in df.columns and df["rmssd_ms"].notna().any():
                    ln_df = df[["measurement_date", "rmssd_ms"]].copy()
                    ln_df = ln_df[(ln_df["rmssd_ms"].notna()) & (ln_df["rmssd_ms"] > 0)]
                    if len(ln_df) >= 5:
                        ln_df = ln_df.sort_values("measurement_date")
                        ln_rmssd_values = np.log(ln_df["rmssd_ms"].astype(float)).tolist()
                        dates_ln = ln_df["measurement_date"].astype(str).tolist()
                        
                        st.markdown("##### 📐 lnRMSSD Trend (Log-Transformed)")
                        st.caption(
                            "lnRMSSD is commonly used in athletic monitoring to track recovery. "
                            "Log transformation normalizes the distribution and reduces the influence "
                            "of outliers. Coefficient of Variation (CV) < 10% indicates stable baseline."
                        )
                        
                        # Calculate CV
                        ln_arr = np.array(ln_rmssd_values)
                        ln_mean = float(np.mean(ln_arr))
                        ln_sd = float(np.std(ln_arr))
                        ln_cv = (ln_sd / ln_mean * 100) if ln_mean > 0 else 0
                        
                        ln_ewma = _ewma_smooth(ln_arr, span=7).tolist()
                    
                    ln_chart = {
                        "title": {
                            "text": "lnRMSSD Trend for Recovery Monitoring",
                            "subtext": f"Mean: {ln_mean:.2f} | SD: {ln_sd:.2f} | CV: {ln_cv:.1f}% | "
                                      f"{'✓ Stable baseline' if ln_cv < 10 else '⚠ High variability'}",
                            "left": "center",
                            "textStyle": {"fontSize": 15, "fontWeight": "bold"},
                            "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
                        },
                        "tooltip": {"trigger": "axis"},
                        "legend": {"data": ["lnRMSSD", "EWMA Trend", "Mean ± 1 SD"], "bottom": 5},
                        "grid": {"left": "8%", "right": "5%", "top": "15%", "bottom": "15%"},
                        "xAxis": {
                            "type": "category",
                            "data": dates_ln,
                            "axisLabel": {"rotate": 45, "fontSize": 9},
                        },
                        "yAxis": {
                            "type": "value",
                            "name": "lnRMSSD",
                            "nameLocation": "middle",
                            "nameGap": 40,
                            "min": max(2.0, ln_mean - 3 * ln_sd),
                            "max": ln_mean + 3 * ln_sd,
                        },
                        "series": [
                            # Mean ± 1 SD band
                            {
                                "name": "Mean ± 1 SD",
                                "type": "line",
                                "data": [ln_mean + ln_sd] * len(dates_ln),
                                "lineStyle": {"opacity": 0},
                                "areaStyle": {"color": "rgba(52, 152, 219, 0.15)"},
                                "stack": "ln_band",
                                "symbol": "none",
                            },
                            {
                                "name": "_ln_lower",
                                "type": "line",
                                "data": [ln_mean - ln_sd] * len(dates_ln),
                                "lineStyle": {"opacity": 0},
                                "areaStyle": {"color": "#fff"},
                                "stack": "ln_band",
                                "symbol": "none",
                            },
                            # Mean line
                            {
                                "name": "Baseline Mean",
                                "type": "line",
                                "data": [ln_mean] * len(dates_ln),
                                "lineStyle": {"color": "#27ae60", "width": 2, "type": "dashed"},
                                "symbol": "none",
                            },
                            # lnRMSSD data
                            {
                                "name": "lnRMSSD",
                                "type": "line",
                                "data": ln_rmssd_values,
                                "symbol": "circle",
                                "symbolSize": 6,
                                "itemStyle": {"color": SCIENTIFIC_COLORS["primary"]},
                                "lineStyle": {"color": SCIENTIFIC_COLORS["primary"], "width": 2},
                            },
                            # EWMA trend
                            {
                                "name": "EWMA Trend",
                                "type": "line",
                                "data": ln_ewma,
                                "symbol": "none",
                                "lineStyle": {"color": "#e67e22", "width": 2.5},
                                "smooth": True,
                            },
                        ],
                        "dataZoom": [{"type": "inside"}],
                    }
                    render_echarts(ln_chart, height_px=350)
            
            # === Data Quality Trend ===
            qual_cols = [
                c for c in ["artifact_percentage", "quality_score"]
                if c in df.columns and df[c].notna().any()
            ]
            if qual_cols:
                qual_df = df.set_index("measurement_date")[qual_cols].dropna(how="all")
                if not qual_df.empty:
                    st.markdown("##### 🔍 Data Quality Trend")
                    _render_profile_line_chart(
                        qual_df,
                        title="Recording Quality Over Time",
                        y_axis_label="% / score",
                    )
                    st.caption(
                        "High artifact percentage (>5%) or low quality score may indicate "
                        "movement artifacts, poor electrode contact, or arrhythmias."
                    )

        # Physiological Interpretations (separate section, not nested)
        with st.expander("📖 Physiological Interpretations (Graduate-Level)", expanded=False):
            st.markdown("""
            **Reference Guide:** Click each topic below for detailed physiological background 
            and clinical interpretation guidelines. Content is based on peer-reviewed literature.
            """)
            
            interp_col1, interp_col2 = st.columns(2)
            with interp_col1:
                st.markdown("##### ❤️ Resting Heart Rate")
                st.markdown(HRV_PHYSIOLOGICAL_INTERPRETATIONS["heart_rate"])
                
                st.markdown("---")
                st.markdown("##### 📊 RMSSD")
                st.markdown(HRV_PHYSIOLOGICAL_INTERPRETATIONS["rmssd"])
            
            with interp_col2:
                st.markdown("##### ⚖️ LF/HF Ratio")
                st.markdown(HRV_PHYSIOLOGICAL_INTERPRETATIONS["lf_hf_ratio"])
                
                st.markdown("---")
                st.markdown("##### 📈 SDNN")
                st.markdown(HRV_PHYSIOLOGICAL_INTERPRETATIONS["sdnn"])
            
            st.markdown("---")
            st.markdown("##### 🧘 Stress & Recovery")
            st.markdown(HRV_PHYSIOLOGICAL_INTERPRETATIONS["stress_recovery"])

        # HRV × wearable/activity relationships (when daily metrics exist)
        with st.expander("🔗 HRV × Activity (Garmin daily metrics)", expanded=False):
            if not show_hrv_charts:
                st.info("Enable **Show HRV charts** to render this section.")
            else:
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
                                    # Publication-quality HRV × Activity time series
                                    has_steps = "steps" in merged.columns and merged["steps"].notna().any()
                                    has_rmssd = "rmssd_ms" in merged.columns and merged["rmssd_ms"].notna().any()
                                    
                                    if has_steps or has_rmssd:
                                        merged_sorted = merged.sort_index()
                                        dates_list = [str(d)[:10] for d in merged_sorted.index.tolist()]
                                        steps_data = merged_sorted["steps"].tolist() if has_steps else None
                                        rmssd_data = merged_sorted["rmssd_ms"].tolist() if has_rmssd else None
                                        
                                        activity_chart = _build_hrv_activity_timeseries_chart(
                                            dates=dates_list,
                                            steps=steps_data,
                                            rmssd_ms=rmssd_data,
                                            title="HRV × Activity Time Series",
                                        )
                                        render_echarts(activity_chart, height_px=400)
                                        st.markdown(
                                            "*Daily steps (activity load) plotted with RMSSD (parasympathetic recovery). "
                                            "High activity + high RMSSD indicates good fitness and recovery. "
                                            "High activity + low RMSSD may suggest overtraining.* "
                                            "*(Plews et al., 2013; Stanley et al., 2013)*"
                                        )

                                    # Publication-quality scatter plots with regression
                                    st.markdown("##### 📊 HRV × Activity Correlations")
                                    scatter_pairs = [
                                        ("steps", "rmssd_ms", "RMSSD vs Steps", "Steps", "RMSSD (ms)"),
                                        ("distance_km", "rmssd_ms", "RMSSD vs Distance", "Distance (km)", "RMSSD (ms)"),
                                        ("calories_kcal", "rmssd_ms", "RMSSD vs Calories", "Calories (kcal)", "RMSSD (ms)"),
                                        ("sleep_score", "rmssd_ms", "RMSSD vs Sleep Score", "Sleep Score", "RMSSD (ms)"),
                                        ("stress_score", "rmssd_ms", "RMSSD vs Stress Score", "Stress Score", "RMSSD (ms)"),
                                        ("body_battery_avg", "rmssd_ms", "RMSSD vs Body Battery", "Body Battery (avg)", "RMSSD (ms)"),
                                    ]
                                    
                                    scatter_cols = st.columns(2)
                                    scatter_idx = 0
                                    
                                    for x_col, y_col, chart_title, xlab, ylab in scatter_pairs:
                                        if x_col not in merged.columns or y_col not in merged.columns:
                                            continue
                                        paired = merged[[x_col, y_col]].dropna()
                                        if len(paired) < 3:
                                            continue
                                        
                                        corr = paired[x_col].corr(paired[y_col])
                                        x_vals = paired[x_col].tolist()
                                        y_vals = paired[y_col].tolist()
                                        
                                        scatter_chart = _build_hrv_activity_scatter_chart(
                                            x_values=x_vals,
                                            y_values=y_vals,
                                            x_label=xlab,
                                            y_label=ylab,
                                            title=chart_title,
                                            correlation=corr,
                                            n_samples=len(paired),
                                        )
                                        
                                        with scatter_cols[scatter_idx % 2]:
                                            render_echarts(scatter_chart, height_px=320)
                                        scatter_idx += 1
                                    
                                    if scatter_idx > 0:
                                        st.markdown(
                                            "*Scatter plots show relationships between activity metrics and RMSSD. "
                                            "Regression lines indicate trend direction. Correlation strength: "
                                            "|r| ≥0.7 strong, 0.4-0.7 moderate, 0.2-0.4 weak, <0.2 negligible.* "
                                            "*(Buchheit, 2014)*"
                                        )
        
        # Advanced HRV Analytics Platform
        if show_advanced:
            with st.expander("🧬 Advanced HRV Analytics (ML, Statistics, Clinical Decision Support)", expanded=False):
                # Get Garmin data for integration analysis
                try:
                    garmin_analytics_df = pd.DataFrame()
                    if hasattr(db, "get_garmin_daily_dataframe"):
                        garmin_analytics_df = db.get_garmin_daily_dataframe(user.user_id, limit=365)
                    elif hasattr(db, "get_garmin_daily_metrics"):
                        garmin_rows = db.get_garmin_daily_metrics(user.user_id, limit=365)
                        if garmin_rows:
                            garmin_analytics_df = pd.DataFrame([r.to_dict() for r in garmin_rows])
                except Exception:
                    garmin_analytics_df = pd.DataFrame()
                
                _render_advanced_hrv_analytics(
                    user=user,
                    hrv_df=df,
                    garmin_df=garmin_analytics_df if not garmin_analytics_df.empty else None,
                )
        
        # Full data table
        if show_table:
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

    @st.cache_data(ttl=300, max_entries=64, show_spinner=False)
    def _load_readiness_dataframe(uid: str) -> pd.DataFrame:
        db = get_database()
        return db.get_hrv_dataframe(
            uid,
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

    try:
        df = _load_readiness_dataframe(user.user_id)
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

    @st.cache_data(ttl=60, show_spinner=False)
    def _build_export_blob(user_id: str, username: str) -> tuple[str, bytes]:
        import json

        db = get_database()
        export_data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "user_profile": db.get_user(user_id).to_dict() if db.get_user(user_id) else {},
            "clinical_scales": [s.to_dict() for s in db.get_clinical_scales_history(user_id)],
            "hrv_measurements": [m.to_dict() for m in db.get_hrv_history(user_id)],
            "garmin_daily_metrics": [g.to_dict() for g in db.get_garmin_daily_metrics(user_id)],
            "body_composition": [b.to_dict() for b in db.get_body_composition_history(user_id)],
            "exploration_medical_history": db.get_medical_history(user_id, limit=500),
        }
        json_bytes = json.dumps(export_data, indent=2, default=str).encode("utf-8")
        fname = f"{username}_data_export.json"
        return fname, json_bytes

    @st.cache_data(ttl=60, show_spinner=False)
    def _build_export_csv_blob(user_id: str, username: str) -> tuple[str, bytes]:
        """Flatten export data into a single CSV with section + JSON payload rows."""
        import json
        import pandas as pd

        db = get_database()
        export_data = {
            "user_profile": [db.get_user(user_id).to_dict() if db.get_user(user_id) else {}],
            "clinical_scales": [s.to_dict() for s in db.get_clinical_scales_history(user_id)],
            "hrv_measurements": [m.to_dict() for m in db.get_hrv_history(user_id)],
            "garmin_daily_metrics": [g.to_dict() for g in db.get_garmin_daily_metrics(user_id)],
            "body_composition": [b.to_dict() for b in db.get_body_composition_history(user_id)],
            "exploration_medical_history": db.get_medical_history(user_id, limit=500),
        }

        rows: list[dict[str, str]] = []
        for section, items in export_data.items():
            if isinstance(items, list):
                for idx, rec in enumerate(items):
                    rows.append(
                        {
                            "section": section,
                            "index": idx,
                            "data_json": json.dumps(rec, default=str),
                        }
                    )
            else:
                rows.append(
                    {
                        "section": section,
                        "index": 0,
                        "data_json": json.dumps(items, default=str),
                    }
                )

        df = pd.DataFrame(rows)
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        fname = f"{username}_data_export.csv"
        return fname, csv_bytes

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Export Data")
        try:
            fname, blob = _build_export_blob(user.user_id, user.username or "user")
            st.download_button(
                "💾 Download JSON",
                data=blob,
                file_name=fname,
                mime="application/json",
                use_container_width=True,
            )
            fname_csv, csv_blob = _build_export_csv_blob(user.user_id, user.username or "user")
            st.download_button(
                "📄 Download CSV",
                data=csv_blob,
                file_name=fname_csv,
                mime="text/csv",
                use_container_width=True,
            )
        except Exception as exc:
            st.error(f"Export failed: {exc}")

    with col2:
        st.markdown("### Account Actions")

        # Use an on_click callback so logout happens BEFORE the rest of the app
        # executes on rerun (prevents "logout takes forever" when other tabs are heavy).
        st.button(
            "🚪 Logout",
            key=f"profile_logout_{user.user_id}",
            use_container_width=True,
            on_click=_logout_and_preserve,
        )

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
                            safe_rerun("profile_tab_rerun")
                        except Exception as exc:
                            st.error(f"Delete failed: {exc}")
                with col_no:
                    if st.button("Cancel"):
                        st.session_state.pop("confirm_delete", None)
                        safe_rerun("profile_tab_rerun")


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
    st.caption(f"Timezone detected: {_format_tz_display(_get_bogota_tz())}")
    
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
    current_hour = datetime.now(tz=_get_bogota_tz()).hour
    current_dt = datetime.now(tz=_get_bogota_tz())
    
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
    st.caption(
        "Fatigue Prediction (SAFTE) uses sleep quantity/quality + hours awake. "
        "Operational Performance (HRV+SAFTE) fuses SAFTE sleep drivers with HRV markers "
        "(RMSSD, resting HR) for a combined readiness view."
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
    
    autofill_col, _ = st.columns([1, 2])
    with autofill_col:
        if st.button(
            "📡 Autofill sleep from Garmin",
            key=f"garmin_autofill_tools_{user.user_id}",
            help="Pull latest Garmin Vivosmart sleep to fill SAFTE inputs (sleep hours, quality, hours awake, RMSSD, resting HR). Note: Chronotype is NOT changed by Garmin autofill - it is saved to your profile and persists across sessions.",
        ):
            with st.spinner("Fetching Garmin sleep..."):
                payload = _get_latest_garmin_sleep_payload(user, current_dt)
            if payload is None:
                st.warning("No recent Garmin sleep data found or Garmin API unavailable.")
            else:
                st.session_state[f"tools_sleep_hours_{user.user_id}"] = payload["sleep_hours"]
                st.session_state[f"tools_sleep_quality_{user.user_id}"] = payload["sleep_quality"]
                st.session_state[f"tools_hours_awake_{user.user_id}"] = payload["hours_awake"]
                if "rmssd_ms" in payload:
                    st.session_state[f"tools_rmssd_{user.user_id}"] = payload["rmssd_ms"]
                if "resting_hr" in payload:
                    st.session_state[f"tools_resting_hr_{user.user_id}"] = payload["resting_hr"]
                
                # Persist to user profile
                try:
                    db = get_database()
                    if "resting_hr" in payload:
                        db.update_user_sleep_chronotype(
                            user.user_id,
                            resting_hr_bpm=float(payload["resting_hr"]),
                        )
                        user.resting_hr_bpm = float(payload["resting_hr"])
                    st.success(
                        f"Garmin sleep synced and saved to profile: {payload['sleep_hours']:.2f}h, "
                        f"quality {payload['sleep_quality']:.2f}, hours awake {payload['hours_awake']:.1f}"
                    )
                except Exception as exc:
                    _LOGGER.warning("Failed to persist Garmin autofill to profile: %s", exc)
                    st.success(
                        f"Garmin sleep synced (session only): {payload['sleep_hours']:.2f}h, "
                        f"quality {payload['sleep_quality']:.2f}, hours awake {payload['hours_awake']:.1f}"
                    )
    
    if show_parameters:
        col1, col2, col3 = st.columns(3)
        sleep_hours_preview = _safe_float(st.session_state.get(f"tools_sleep_hours_{user.user_id}")) or 7.0
        sleep_quality_preview = _safe_float(st.session_state.get(f"tools_sleep_quality_{user.user_id}")) or 0.7
        hours_awake_preview = _safe_float(st.session_state.get(f"tools_hours_awake_{user.user_id}")) or float(
            current_hour - 7 if current_hour >= 7 else current_hour + 17
        )
        profile_chrono_offset = _safe_float(getattr(user, "chronotype_offset_hours", None)) or 0.0
        chrono_index = 2
        if profile_chrono_offset <= -1.5:
            chrono_index = 0
        elif profile_chrono_offset <= -0.5:
            chrono_index = 1
        elif profile_chrono_offset >= 1.5:
            chrono_index = 4
        elif profile_chrono_offset >= 0.5:
            chrono_index = 3
        chrono_labels = [
            "Morning (-2h)",
            "Slight morning (-1h)",
            "Neutral (0h)",
            "Slight evening (+1h)",
            "Evening (+2h)",
        ]
        chronotype_preview = (
            str(st.session_state.get(f"tools_chronotype_{user.user_id}"))
            if st.session_state.get(f"tools_chronotype_{user.user_id}")
            else chrono_labels[chrono_index]
        )
        rmssd_preview = _safe_float(st.session_state.get(f"tools_rmssd_{user.user_id}")) or 35.0
        resting_hr_preview = _safe_float(st.session_state.get(f"tools_resting_hr_{user.user_id}")) or float(
            user.resting_hr_bpm or 65
        )

        with col1:
            st.metric("Sleep hours (last night)", f"{sleep_hours_preview:.1f} h")
            st.metric("Sleep quality (0-1)", f"{sleep_quality_preview:.2f}")

        with col2:
            st.metric("Hours awake", f"{hours_awake_preview:.1f}")
            st.metric("Chronotype", chronotype_preview)

        with col3:
            st.metric("RMSSD (ms)", f"{rmssd_preview:.1f}")
            st.metric("Resting HR (bpm)", f"{resting_hr_preview:.0f}")

        st.caption(
            "Edit these inputs in the NASA Nutrition Calculator to keep a single shared set of values."
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
    # Load chronotype from user profile (persistent) first, then session state, then from chronotype selectbox
    # Handle case where attribute might not exist (older UserProfile instances)
    chronotype_offset_override = (
        _safe_float(getattr(user, 'chronotype_offset_hours', None)) or
        _safe_float(st.session_state.get(f"tools_chronotype_offset_{user.user_id}"))
    )
    chronotype_offset = (
        float(chronotype_offset_override)
        if chronotype_offset_override is not None
        else float(chronotype_map.get(chronotype, 0.0))
    )

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
    st.caption(
        "Uses only SAFTE sleep drivers: sleep hours, sleep quality, hours awake, and chronotype. "
        "No HRV metrics are mixed into this prediction."
    )
    
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
        # `EChartsConfig` controls how ECharts is loaded (CDN/local/inline), not chart options.
        # Pass the ECharts option dict directly and set chart height via `height_px`.
        render_echarts(options, height_px=320)
    
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
        "Combines SAFTE sleep/circadian effectiveness with HRV (RMSSD, recovery) and autonomic markers. "
        "This is distinct from the SAFTE-only fatigue prediction above."
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
                # STOP-BANG components (correct field names)
                snoring = latest_med.get("snoring")  # S: Loud snoring
                tiredness = latest_med.get("tiredness")  # T: Daytime tiredness
                observed_apnea = latest_med.get("observed_apnea")  # O: Witnessed apnea (NOT sleep_apnea diagnosis!)
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
        
    st.markdown("##### 😴 Sleep & Chronotype Inputs (feeds SAFTE/Readiness)")

    # Session keys shared with Profile Tools Engine for cross-section consistency
    # Use unique widget keys (nasa_ prefix) but sync to shared session state
    sleep_hours_key = f"tools_sleep_hours_{user.user_id}"
    sleep_quality_key = f"tools_sleep_quality_{user.user_id}"
    hours_awake_key = f"tools_hours_awake_{user.user_id}"
    chrono_key = f"tools_chronotype_offset_{user.user_id}"
    rmssd_key = f"tools_rmssd_{user.user_id}"
    resting_hr_key = f"tools_resting_hr_{user.user_id}"
    vo2_key = f"tools_vo2_{user.user_id}"

    fetch_col, _ = st.columns([1, 2])
    with fetch_col:
        if st.button(
            "📡 Autofill from Garmin",
            key=f"garmin_autofill_sleep_section_{user.user_id}",
            help="Pull latest Garmin Vivosmart sleep to fill sleep inputs (sleep hours, quality, hours awake, RMSSD, resting HR). Note: Chronotype is NOT changed by Garmin autofill - it is saved to your profile and persists across sessions.",
        ):
            with st.spinner("Fetching Garmin sleep..."):
                payload = _get_latest_garmin_sleep_payload(user, datetime.now(tz=_get_bogota_tz()))
            if payload is None:
                st.warning("No recent Garmin sleep data found or Garmin API unavailable.")
            else:
                st.session_state[sleep_hours_key] = payload["sleep_hours"]
                st.session_state[sleep_quality_key] = payload["sleep_quality"]
                st.session_state[hours_awake_key] = payload["hours_awake"]
                if "rmssd_ms" in payload:
                    st.session_state[rmssd_key] = payload["rmssd_ms"]
                if "resting_hr" in payload:
                    st.session_state[resting_hr_key] = payload["resting_hr"]
                
                # Persist to user profile
                try:
                    db = get_database()
                    if "resting_hr" in payload:
                        db.update_user_sleep_chronotype(
                            user.user_id,
                            resting_hr_bpm=float(payload["resting_hr"]),
                        )
                    # Update user profile resting_hr_bpm if available
                    if "resting_hr" in payload:
                        user.resting_hr_bpm = float(payload["resting_hr"])
                    st.success(
                        f"Garmin sleep synced and saved to profile: {payload['sleep_hours']:.2f}h, "
                        f"quality {payload['sleep_quality']:.2f}, hours awake {payload['hours_awake']:.1f}"
                    )
                except Exception as exc:
                    _LOGGER.warning("Failed to persist Garmin autofill to profile: %s", exc)
                    st.success(
                        f"Garmin sleep synced (session only): {payload['sleep_hours']:.2f}h, "
                        f"quality {payload['sleep_quality']:.2f}, hours awake {payload['hours_awake']:.1f}"
                    )
    
    sleep_col1, sleep_col2, sleep_col3 = st.columns(3)
    
    # Display read-only summary instead of duplicate editable widgets
    # (The Profile Tools Engine section below provides the editable inputs)
    st.info(
        "💡 **Tip:** Edit sleep/fatigue parameters in the **Profile Tools Engine** section below. "
        "Values entered there will be used here automatically."
    )
    
    # Show current values as read-only metrics
    with sleep_col1:
        current_sleep_h = st.session_state.get(sleep_hours_key, 7.0)
        current_sleep_q = st.session_state.get(sleep_quality_key, 0.7)
        st.metric("Sleep hours", f"{float(current_sleep_h):.1f} h")
        st.metric("Sleep quality", f"{float(current_sleep_q):.0%}")
    
    with sleep_col2:
        current_awake = st.session_state.get(hours_awake_key, 12.0)
        current_chrono = st.session_state.get(chrono_key, 0.0)
        st.metric("Hours awake", f"{float(current_awake):.1f} h")
        chrono_label = "morning" if float(current_chrono) < 0 else ("evening" if float(current_chrono) > 0 else "neutral")
        st.metric("Chronotype", f"{float(current_chrono):+.1f}h ({chrono_label})")
    
    with sleep_col3:
        current_rmssd = st.session_state.get(rmssd_key, 35.0)
        current_rhr = st.session_state.get(resting_hr_key, user.resting_hr_bpm or 65)
        st.metric("RMSSD", f"{float(current_rmssd):.0f} ms")
        st.metric("Resting HR", f"{int(current_rhr)} bpm")
    
    # VO2 summary (read-only here to avoid duplicate widget keys)
    st.markdown("###### VO₂ for performance context (read-only here)")
    vo2_sync_col, _ = st.columns([1, 3])
    with vo2_sync_col:
        current_vo2 = float(st.session_state.get(vo2_key, vo2_manual))
        st.metric("VO₂max", f"{current_vo2:.1f} mL·kg⁻¹·min⁻¹")
    st.caption(
        "Edit VO₂ in the Profile Tools Engine (or the NASA sync form below) — "
        "the value is shared automatically."
    )
    
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

        st.markdown("---")
        st.markdown("##### 😴 Sleep & Chronotype Inputs (SAFTE / Operational)")
        st.caption(
            "Enter sleep and chronotype values to feed SAFTE fatigue prediction and the Operational Performance (HRV+SAFTE) tool. "
            "These values sync with the Profile Tools Engine below."
        )

        # Defaults pulled from shared session keys so UI stays consistent
        # Chronotype is loaded from user profile (persistent), not from session state
        sleep_key = f"tools_sleep_hours_{user.user_id}"
        sleep_quality_key = f"tools_sleep_quality_{user.user_id}"
        hours_awake_key = f"tools_hours_awake_{user.user_id}"
        chrono_key = f"tools_chronotype_offset_{user.user_id}"
        rmssd_key = f"tools_rmssd_{user.user_id}"
        resting_hr_key = f"tools_resting_hr_{user.user_id}"
        vo2_key = f"tools_vo2_{user.user_id}"

        sleep_hours_val = float(_safe_float(st.session_state.get(sleep_key)) or 7.0)
        sleep_quality_val = float(_safe_float(st.session_state.get(sleep_quality_key)) or 0.7)
        hours_awake_val = float(_safe_float(st.session_state.get(hours_awake_key)) or 12.0)
        # Load chronotype from user profile (persistent), fallback to session state, then default to 0.0
        # Handle case where attribute might not exist (older UserProfile instances)
        chronotype_offset_val = float(
            _safe_float(getattr(user, 'chronotype_offset_hours', None)) or
            _safe_float(st.session_state.get(chrono_key)) or
            0.0
        )
        rmssd_val = float(_safe_float(st.session_state.get(rmssd_key)) or 35.0)
        resting_hr_val = float(_safe_float(st.session_state.get(resting_hr_key)) or (user.resting_hr_bpm or 65))
        vo2_val = float(_safe_float(st.session_state.get(vo2_key)) or (user.vo2max_ml_kg_min or 38.0))

        col_sleep_a, col_sleep_b, col_sleep_c = st.columns(3)
        with col_sleep_a:
            sleep_hours_val = st.number_input(
                "Sleep hours (last night)",
                min_value=0.0,
                max_value=14.0,
                step=0.5,
                value=sleep_hours_val,
                key=sleep_key,
            )
            sleep_quality_val = st.slider(
                "Sleep quality (0-1)",
                min_value=0.0,
                max_value=1.0,
                step=0.05,
                value=sleep_quality_val,
                key=sleep_quality_key,
            )
        with col_sleep_b:
            hours_awake_val = st.number_input(
                "Hours awake",
                min_value=0.0,
                max_value=48.0,
                step=0.5,
                value=hours_awake_val,
                key=hours_awake_key,
            )
            chronotype_offset_val = st.slider(
                "Chronotype offset (hours)",
                min_value=-2.5,
                max_value=2.5,
                step=0.25,
                value=chronotype_offset_val,
                help="Morning type negative; evening type positive.",
                key=chrono_key,
            )
        with col_sleep_c:
            rmssd_val = st.number_input(
                "RMSSD (ms)",
                min_value=0.0,
                max_value=200.0,
                step=1.0,
                value=rmssd_val,
                key=rmssd_key,
            )
            resting_hr_val = st.number_input(
                "Resting HR (bpm)",
                min_value=30,
                max_value=120,
                step=1,
                value=int(resting_hr_val),
                key=resting_hr_key,
            )

        col_vo2_sync, col_sleep_sync = st.columns([1, 1])
        with col_vo2_sync:
            vo2_val = st.number_input(
                "VO₂ max (mL·kg⁻¹·min⁻¹)",
                min_value=10.0,
                max_value=90.0,
                step=0.5,
                value=vo2_val,
                key=vo2_key,
            )

        with col_sleep_sync:
            if st.button(
                "🔄 Sync to Profile Tools Engine",
                key=f"sync_sleep_to_tools_{user.user_id}",
                help="Push these sleep/chronotype/HRV values into the Profile Tools Engine (SAFTE + Operational Performance) and save to profile.",
            ):
                # Persist to user profile
                try:
                    db = get_database()
                    db.update_user_sleep_chronotype(
                        user.user_id,
                        resting_hr_bpm=float(resting_hr_val),
                        chronotype_offset_hours=float(chronotype_offset_val),
                    )
                    # Update user profile object
                    user.resting_hr_bpm = float(resting_hr_val)
                    # Set chronotype_offset_hours (use setattr to handle cases where attribute might not exist yet)
                    setattr(user, 'chronotype_offset_hours', float(chronotype_offset_val))
                    st.success("Synced sleep/chronotype/HRV inputs to Profile Tools Engine and saved to profile.")
                except Exception as exc:
                    _LOGGER.warning("Failed to persist sync to profile: %s", exc)
                    st.success("Synced sleep/chronotype/HRV inputs to Profile Tools Engine (session only).")
        
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
                safe_rerun("profile_tab_rerun")


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


def _s_scale_severity_label(s_level: int) -> str:
    """Return human-readable severity label for NOAA S-Scale.
    
    Reference: NOAA Space Weather Scales (https://www.swpc.noaa.gov/noaa-scales-explanation)
    """
    labels = {
        0: "None",
        1: "Minor",
        2: "Moderate",
        3: "Strong",
        4: "Severe",
        5: "Extreme",
    }
    return labels.get(int(s_level), "Unknown")


def _g_scale_severity_label(g_level: int) -> str:
    """Return human-readable severity label for NOAA G-Scale.
    
    Reference: NOAA Space Weather Scales (https://www.swpc.noaa.gov/noaa-scales-explanation)
    """
    labels = {
        0: "None",
        1: "Minor",
        2: "Moderate",
        3: "Strong",
        4: "Severe",
        5: "Extreme",
    }
    return labels.get(int(g_level), "Unknown")


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
    """Load a small subset of NOAA datasets used for profile alert estimation.

    Important:
        This must NEVER hit the network during normal profile rendering. It loads
        cache-only copies so the UI stays responsive. Users can refresh NOAA data
        explicitly from the dedicated NOAA Space tab.
    """
    if not NOAA_SPACE_AVAILABLE:
        return {}, {"__global__": "NOAA space module unavailable."}
    bundles, errors = load_noaa_space_cache(
        keys=("planetary_k_index_1m", "goes_integral_protons"),
        allow_stale_cache=True,
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
    """Load daily-median objective HRV indices (stress/PNS) for a user.
    
    CRITICAL: Only uses Polar device measurements (device_name contains 'Polar' or 'polar').
    Calculates indices from RR-intervals if stored measurements are unavailable.
    
    References:
    - Baevsky RM, Chernikova AG (2017). Heart rate variability analysis: physiological foundations.
      Cardiometry 10:66-76.
    - Nunan D, Sandercock GR, Brodie DA (2010). A quantitative systematic review of normal values.
      Pacing Clin Electrophysiol 33(11):1407-1417.
    """
    if not uid:
        return pd.DataFrame()
    db = get_database()
    
    # Load HRV data with device_name and source_file to filter for Polar only
    df = db.get_hrv_dataframe(
        uid,
        limit=500,
        include_rr=True,  # Need RR intervals to recalculate if needed
        columns=(
            "measurement_date",
            "device_name",
            "source_file",
            "stress_index",
            "parasympathetic_index",
            "hrv_score",
            "mean_hr_bpm",
            "rmssd_ms",
            "sdnn_ms",
            "pnn50_pct",
            "rr_intervals_json",
        ),
    )
    if df.empty or "measurement_date" not in df.columns:
        return pd.DataFrame()
    
    # Filter to only Polar devices
    # Polar devices typically have device_name containing "Polar" or source_file containing "polar"
    polar_mask = (
        df["device_name"].astype(str).str.contains("Polar|polar", case=False, na=False) |
        df["source_file"].astype(str).str.contains("polar|Polar", case=False, na=False)
    )
    df_polar = df[polar_mask].copy()
    
    if df_polar.empty:
        return pd.DataFrame()
    
    # Get user age for parasympathetic index calculation
    user = _get_current_user()
    age = None
    if user and user.date_of_birth:
        age = _calculate_age(user.date_of_birth)
    
    # CRITICAL: Always recalculate indices from RR-intervals for Polar measurements
    # This ensures accuracy and uses the proper scientific formulas
    import json
    
    for idx, row in df_polar.iterrows():
        rr_json = row.get("rr_intervals_json")
        if not rr_json:
            continue  # Skip if no RR intervals available
        
        try:
            rr_data = json.loads(rr_json) if isinstance(rr_json, str) else rr_json
            if not isinstance(rr_data, list) or len(rr_data) < 10:
                continue
            
            rr_array = np.array(rr_data, dtype=float)
            
            # Always recalculate Baevsky Stress Index from RR-intervals
            # Using proper 50ms bin width per scientific literature
            stress_idx = compute_baevsky_stress_index(rr_array, bin_width_ms=50.0)
            df_polar.at[idx, "stress_index"] = stress_idx
            
            # Always recalculate Parasympathetic Index from RR-intervals
            # Using age-adjusted norms (Nunan et al. 2010, Shaffer & Ginsberg 2017)
            if age is not None:
                rmssd = row.get("rmssd_ms")
                pnn50 = row.get("pnn50_pct")
                pns_idx = compute_parasympathetic_index(
                    rr_array,
                    age,
                    rmssd_ms=float(rmssd) if pd.notna(rmssd) and rmssd > 0 else None,
                    pnn50_pct=float(pnn50) if pd.notna(pnn50) and pnn50 > 0 else None,
                )
                df_polar.at[idx, "parasympathetic_index"] = pns_idx
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as exc:
            _LOGGER.debug("Failed to recalculate HRV indices from RR-intervals: %s", exc)
            continue
    
    tmp = df_polar.copy()
    tmp["measurement_date"] = pd.to_datetime(tmp["measurement_date"], errors="coerce")
    tmp = tmp.dropna(subset=["measurement_date"])
    if tmp.empty:
        return pd.DataFrame()
    tmp["day"] = tmp["measurement_date"].dt.normalize()
    cols = [c for c in tmp.columns if c not in {"measurement_date", "device_name", "source_file", "rr_intervals_json"}]
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

def _should_render_profile_section(section_id: str, label: str) -> bool:
    """Return True if a profile sub-section should render in manual-only mode."""
    if not isinstance(section_id, str):
        raise TypeError("section_id must be a string.")
    if not section_id.strip():
        raise ValueError("section_id must be a non-empty string.")
    if not isinstance(label, str):
        raise TypeError("label must be a string.")
    if not label.strip():
        raise ValueError("label must be a non-empty string.")

    manual_only = bool(st.session_state.get("manual_processing_only", True))
    if not manual_only:
        return True

    state_key = f"_profile_section_loaded_{section_id.strip()}"
    if state_key not in st.session_state:
        st.session_state[state_key] = False
    if bool(st.session_state.get(state_key, False)):
        return True

    st.info(
        f"**{label}** is paused to prevent automatic processing. "
        "Click **Load section** to render it."
    )
    col_load, col_hint = st.columns([1, 3])
    with col_load:
        if st.button(
            f"▶️ Load {label}",
            key=f"{state_key}_load",
            use_container_width=True,
        ):
            st.session_state[state_key] = True
            safe_rerun("profile_tab_rerun")
    with col_hint:
        st.caption(
            "Manual-only processing is enabled in **Processing Mode** (sidebar). "
            "Disable it to auto-load sections."
        )
    return False


def _render_radiation_exposure_section(
    user: UserProfile,
    history_df: pd.DataFrame,
    latest_entry: Dict[str, Any],
) -> None:
    """Render enhanced radiation exposure section with day-by-day tracking and EVA Go/No-Go matrix.
    
    Uses evidence-based dose rate models from radiation_exposure module.
    """
    st.markdown("##### ☢️ Radiation Exposure")
    
    rad_limit = 600.0  # NASA STD-3001B (career effective dose design limit)
    rad_limit_legacy = 1000.0  # Legacy planning guideline (kept for comparison)
    
    # Get mission profile from latest entry or default
    # Note: latest_entry is a pandas Series from iloc[-1], so use .get() directly
    mission_profile = str(latest_entry.get("mission_profile", "") or "")
    habitat = str(latest_entry.get("habitat", "") or "")
    try:
        mission_day = int(latest_entry.get("mission_day", 1) or 1)
    except (ValueError, TypeError):
        mission_day = 1
    
    # Determine current environment from mission profile
    current_env = None
    if RADIATION_MODULE_AVAILABLE:
        current_env = get_environment_by_name(mission_profile) or get_environment_by_name(habitat)
        if current_env is None:
            # Default based on common mission profiles
            if "lunar" in mission_profile.lower() or "moon" in mission_profile.lower():
                current_env = RadiationEnvironment.LUNAR_SURFACE_NOMINAL
            elif "gateway" in mission_profile.lower():
                current_env = RadiationEnvironment.LUNAR_GATEWAY
            elif "iss" in mission_profile.lower() or "leo" in mission_profile.lower():
                current_env = RadiationEnvironment.LEO_ISS
            elif "mars" in mission_profile.lower():
                if "surface" in mission_profile.lower():
                    current_env = RadiationEnvironment.MARS_SURFACE
                else:
                    current_env = RadiationEnvironment.MARS_TRANSIT
            elif "analog" in mission_profile.lower() or "hera" in mission_profile.lower():
                current_env = RadiationEnvironment.EARTH_SURFACE
            elif "antarctica" in mission_profile.lower():
                current_env = RadiationEnvironment.ANTARCTICA
    
    # Tabs for different views
    rad_tab1, rad_tab2, rad_tab3, rad_tab4 = st.tabs([
        "📊 Current Status",
        "📈 Day-by-Day Timeline",
        "🌍 Environment Comparison",
        "🚀 EVA Go/No-Go Matrix",
    ])
    
    with rad_tab1:
        _render_radiation_current_status(
            history_df, rad_limit, rad_limit_legacy, current_env, mission_day
        )
    
    with rad_tab2:
        if _should_render_profile_section("radiation_timeline", "Radiation Timeline"):
            _render_radiation_timeline(user, current_env, mission_day, rad_limit)
    
    with rad_tab3:
        if _should_render_profile_section("radiation_environment_compare", "Environment Comparison"):
            _render_radiation_environment_comparison(mission_day)
    
    with rad_tab4:
        if _should_render_profile_section("radiation_eva_matrix", "EVA Go/No-Go Matrix"):
            _render_radiation_eva_matrix(user, history_df, latest_entry, current_env)


def _render_radiation_current_status(
    history_df: pd.DataFrame,
    rad_limit: float,
    rad_limit_legacy: float,
    current_env: Optional[Any],
    mission_day: int,
) -> None:
    """Render current radiation status with gauges and metrics."""
    rad_sources: Dict[str, str] = {}
    if "radiation_dose_msv" in history_df.columns and not history_df["radiation_dose_msv"].dropna().empty:
        rad_sources["Recorded cumulative dose"] = "radiation_dose_msv"
    if (
        "radiation_estimated_cumulative_msv" in history_df.columns
        and not history_df["radiation_estimated_cumulative_msv"].dropna().empty
    ):
        rad_sources["Estimated cumulative dose"] = "radiation_estimated_cumulative_msv"

    if not rad_sources:
        # If no recorded data, show modeled estimate based on environment
        if RADIATION_MODULE_AVAILABLE and current_env is not None:
            dose_info = get_dose_rate_info(current_env)
            daily_rate = dose_info.get("nominal_msv_per_day", 0.5)
            estimated_dose = daily_rate * mission_day
            
            st.info(f"📡 **Modeled estimate** for {current_env.value.replace('_', ' ').title()}: "
                    f"~{estimated_dose:.1f} mSv cumulative (Day {mission_day})")
            
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Daily dose rate", f"{daily_rate:.3f} mSv/day", help=dose_info.get("reference", ""))
            with col_m2:
                st.metric("Estimated cumulative", f"{estimated_dose:.1f} mSv", 
                          delta=f"{rad_limit - estimated_dose:.1f} mSv remaining")
            with col_m3:
                career_pct = (estimated_dose / rad_limit) * 100.0
                status, color, label = cumulative_to_status(estimated_dose, rad_limit)
                st.metric("Career % used", f"{career_pct:.1f}%")
                st.markdown(f"**Status:** <span style='color:{color};font-weight:bold;'>{label}</span>", 
                            unsafe_allow_html=True)
            
            # Render gauge
            _render_radiation_gauge(estimated_dose, rad_limit, current_env.value if current_env else "Unknown")
        else:
            st.warning("No radiation dose entries recorded yet. Log an exploration medical record to track exposure.")
        return
    
    selected_label = st.radio("Dose source", list(rad_sources.keys()), horizontal=True, key="rad_source_selector")
    rad_col = rad_sources[selected_label]
    rad_series = pd.to_numeric(history_df[rad_col], errors="coerce").dropna()

    if rad_series.empty:
        st.warning("No radiation dose entries recorded yet.")
        return
    
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
    
    # Render gauge
    _render_radiation_gauge(max_rad, rad_limit, current_env.value if current_env else "Unknown")
    
    progress_value = min(max_rad / rad_limit, 1.0)
    st.progress(progress_value)
    legacy_pct = min(max_rad / rad_limit_legacy, 1.0) * 100.0
    st.caption(
        f"{progress_value * 100:.1f}% of NASA 600 mSv career effective dose design limit "
        f"(legacy 1000 mSv: {legacy_pct:.1f}%)."
    )
    
    # Publication-quality radiation dose chart
    if {"mission_day"}.issubset(history_df.columns):
        chart_df = history_df.dropna(subset=["mission_day", rad_col] if rad_col else ["mission_day"]).copy()
        if not chart_df.empty:
            chart_df = chart_df.sort_values("mission_day")
            chart_df["radiation_dose_msv"] = pd.to_numeric(chart_df[rad_col], errors="coerce")
            
            # Extract data for publication-quality chart
            mission_days_list = chart_df["mission_day"].astype(int).tolist()
            radiation_values = chart_df["radiation_dose_msv"].tolist()
            
            rad_chart = _build_radiation_dose_chart(
                mission_days=mission_days_list,
                radiation_msv=radiation_values,
                career_limit_msv=rad_limit,
                title="Cumulative Radiation Dose vs. Mission Day",
            )
            render_echarts(rad_chart, height_px=380)
            st.markdown(
                "*Cumulative radiation dose tracked per mission day. NASA-STD-3001 Rev B (2022) "
                "sets a 600 mSv career effective dose design limit. ALARA principle: maintain "
                "exposure As Low As Reasonably Achievable.* "
                "*(ICRP Publication 123, 2013; Cucinotta et al., 2017)*"
            )


def _render_radiation_gauge(
    cumulative_msv: float,
    career_limit_msv: float,
    environment_label: str,
) -> None:
    """Render a clean gauge for radiation exposure."""
    career_pct = min((cumulative_msv / career_limit_msv) * 100.0, 100.0)
    
    # Determine zone
    if career_pct < 30.0:
        zone_color = "#28a745"
        zone_label = "GO"
    elif career_pct < 60.0:
        zone_color = "#ffc107"
        zone_label = "MONITOR"
    elif career_pct < 80.0:
        zone_color = "#fd7e14"
        zone_label = "CAUTION"
    else:
        zone_color = "#dc3545"
        zone_label = "NO-GO"
    
    gauge_option = {
        "series": [
            {
                "type": "gauge",
                "startAngle": 200,
                "endAngle": -20,
                "min": 0,
                "max": 100,
                "splitNumber": 4,
                "axisLine": {
                    "lineStyle": {
                        "width": 25,
                        "color": [
                            [0.30, "#28a745"],
                            [0.60, "#ffc107"],
                            [0.80, "#fd7e14"],
                            [1.00, "#dc3545"],
                        ],
                    }
                },
                "pointer": {
                    "itemStyle": {"color": "#333"},
                    "length": "55%",
                    "width": 6,
                },
                "axisTick": {"show": False},
                "splitLine": {"show": False},
                "axisLabel": {"show": False},
                "detail": {"show": False},
                "title": {"show": False},
                "data": [{"value": round(career_pct, 1)}],
            }
        ],
    }
    
    render_echarts(gauge_option, height_px=180)
    
    # Status display below gauge
    st.markdown(
        f"""<div style="text-align: center;">
            <span style="font-size: 32px; font-weight: bold; color: {zone_color};">{zone_label}</span><br/>
            <span style="font-size: 18px; color: #555;">{career_pct:.1f}% of career limit</span><br/>
            <span style="font-size: 14px; color: #888;">{cumulative_msv:.1f} / {career_limit_msv:.0f} mSv</span>
        </div>""",
        unsafe_allow_html=True,
    )
    st.caption(f"Environment: {environment_label.replace('_', ' ').title()}")


def _render_radiation_timeline(
    user: UserProfile,
    current_env: Optional[Any],
    current_mission_day: int,
    career_limit_msv: float,
) -> None:
    """Render day-by-day radiation exposure timeline with projections."""
    st.markdown("**📅 Day-by-Day Radiation Accumulation**")
    
    if not RADIATION_MODULE_AVAILABLE:
        st.warning("Radiation exposure module not available.")
        return
    
    manual_only = bool(st.session_state.get("manual_processing_only", True))
    
    # Environment selector for projection
    env_options = [
        ("Earth Surface", RadiationEnvironment.EARTH_SURFACE),
        ("Antarctica", RadiationEnvironment.ANTARCTICA),
        ("Low Earth Orbit (ISS)", RadiationEnvironment.LEO_ISS),
        ("Lunar Gateway", RadiationEnvironment.LUNAR_GATEWAY),
        ("Lunar Surface", RadiationEnvironment.LUNAR_SURFACE_NOMINAL),
        ("Mars Transit", RadiationEnvironment.MARS_TRANSIT),
        ("Mars Surface", RadiationEnvironment.MARS_SURFACE),
    ]
    
    col_env, col_days, col_eva = st.columns(3)
    with col_env:
        env_labels = [e[0] for e in env_options]
        default_idx = 0
        if current_env:
            for i, (_, env) in enumerate(env_options):
                if env == current_env:
                    default_idx = i
                    break
        selected_env_label = st.selectbox(
            "Environment",
            env_labels,
            index=default_idx,
            key="rad_timeline_env",
        )
        selected_env = next((e[1] for e in env_options if e[0] == selected_env_label), RadiationEnvironment.LEO_ISS)
    
    with col_days:
        projection_days = st.number_input(
            "Projection days",
            min_value=7,
            max_value=1000,
            value=min(max(current_mission_day, 30), 365),
            step=7,
            key="rad_timeline_days",
        )
    
    with col_eva:
        total_eva_hours = st.number_input(
            "Planned EVA hours (total)",
            min_value=0.0,
            max_value=500.0,
            value=0.0,
            step=6.0,
            key="rad_timeline_eva",
        )
    
    # Auto-detect solar cycle phase from NOAA (manual-only aware)
    from radiation_exposure import detect_solar_cycle_phase_from_noaa
    
    user_key = str(getattr(user, "user_id", "") or "guest")
    auto_phase_key = f"rad_timeline_auto_phase_{user_key}"
    auto_detected_phase = st.session_state.get(auto_phase_key)
    
    if manual_only:
        if st.button(
            "🔍 Detect solar cycle phase from NOAA",
            key=f"rad_timeline_detect_phase_{user_key}",
            help="Explicitly fetch the latest NOAA F10.7-derived solar cycle phase.",
            use_container_width=True,
        ):
            try:
                auto_detected_phase = detect_solar_cycle_phase_from_noaa(target_date=date.today())
                st.session_state[auto_phase_key] = auto_detected_phase
            except Exception as exc:
                _LOGGER.warning("Solar cycle auto-detect failed: %s", exc)
                st.warning(f"Auto-detect failed: {exc}")
    else:
        if auto_detected_phase is None:
            try:
                auto_detected_phase = detect_solar_cycle_phase_from_noaa(target_date=date.today())
                st.session_state[auto_phase_key] = auto_detected_phase
            except Exception as exc:
                _LOGGER.debug("Solar cycle auto-detect failed: %s", exc)
    
    phase_index_map = {"minimum": 0, "ascending": 1, "maximum": 2, "declining": 3}
    default_phase_idx = phase_index_map.get(auto_detected_phase, 2)  # Default to maximum
    
    if auto_detected_phase:
        st.info(f"🌞 **Auto-detected Solar Cycle Phase:** {auto_detected_phase.upper()} (from NOAA F10.7 data)")
    elif manual_only:
        st.caption("Auto-detect is disabled in manual-only mode. Click the button above to fetch it.")
    
    # Allow manual override if needed
    auto_toggle_key = f"rad_timeline_auto_solar_{user_key}"
    if auto_toggle_key not in st.session_state:
        st.session_state[auto_toggle_key] = bool(auto_detected_phase) and not manual_only
    if auto_detected_phase is None:
        st.session_state[auto_toggle_key] = False
    use_auto_detect = st.checkbox(
        "Use auto-detected solar cycle phase",
        key=auto_toggle_key,
        disabled=auto_detected_phase is None,
        help="Automatically detect from NOAA F10.7 flux data. Uncheck to manually select.",
    )
    
    if use_auto_detect and auto_detected_phase:
        solar_phase = auto_detected_phase
    else:
        solar_phase = st.radio(
            "Solar cycle phase (manual)",
            ["minimum", "ascending", "maximum", "declining"],
            index=default_phase_idx,
            horizontal=True,
            key="rad_timeline_solar_manual",
            help="Solar minimum = higher GCR dose; Solar maximum = lower GCR but more SPE risk",
        )
    
    # Career limit selector (NASA vs ESA)
    career_limit_standard = st.selectbox(
        "Career limit standard",
        ["NASA (600 mSv)", "ESA (1000 mSv)"],
        index=0,
        key="rad_timeline_career_standard",
        help="NASA STD-3001 Vol 1 Rev B (2022): 600 mSv. ESA/ICRP: 1000 mSv.",
    )
    actual_career_limit = 600.0 if "NASA" in career_limit_standard else 1000.0
    
    # Build timeline
    start_date = date.today() - timedelta(days=current_mission_day - 1)
    end_date = start_date + timedelta(days=int(projection_days) - 1)
    
    # Simple EVA schedule (spread evenly)
    eva_schedule: Dict[date, float] = {}
    if total_eva_hours > 0:
        eva_days = max(1, int(projection_days // 14))  # One EVA every 2 weeks
        eva_per_day = total_eva_hours / eva_days
        for i in range(eva_days):
            eva_date = start_date + timedelta(days=14 * (i + 1))
            if eva_date <= end_date:
                eva_schedule[eva_date] = min(eva_per_day, 8.0)  # Max 8h EVA per day
    
    # Use real space weather data
    real_sw_key = "rad_timeline_real_sw"
    if real_sw_key not in st.session_state:
        st.session_state[real_sw_key] = not manual_only
    use_real_sw = st.checkbox(
        "Use real NOAA space weather data",
        key=real_sw_key,
        help="Apply daily adjustments based on real Kp index and proton flux from NOAA",
    )
    
    env_value = selected_env.value if hasattr(selected_env, "value") else str(selected_env)
    phase_to_use = str(solar_phase)
    eva_items = tuple(sorted((d.isoformat(), float(h)) for d, h in eva_schedule.items()))
    cache_key = f"_rad_timeline_cache_{user_key}"
    cache_sig = {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "env": env_value,
        "eva": eva_items,
        "phase": phase_to_use,
        "career": float(actual_career_limit),
        "real_sw": bool(use_real_sw),
    }
    cached = st.session_state.get(cache_key)
    if isinstance(cached, dict) and cached.get("sig") == cache_sig:
        timeline = cached.get("timeline", [])
    else:
        timeline = build_radiation_timeline(
            start_date=start_date,
            end_date=end_date,
            environment=selected_env,
            initial_cumulative_msv=0.0,
            eva_schedule=eva_schedule,
            solar_cycle_phase=phase_to_use,
            career_limit_msv=actual_career_limit,
            use_real_space_weather=use_real_sw,
        )
        st.session_state[cache_key] = {"sig": cache_sig, "timeline": timeline}
    
    if not timeline:
        st.warning("Unable to build radiation timeline.")
        return
    
    # Convert to DataFrame
    timeline_df = timeline_to_dataframe(timeline)
    
    # Plot cumulative dose over time with proper zones
    st.markdown("##### Radiation Exposure Projection")
    
    # Calculate thresholds per NASA/ESA standards
    threshold_30 = actual_career_limit * 0.30  # MONITOR zone start
    threshold_60 = actual_career_limit * 0.60  # CAUTION zone start
    threshold_80 = actual_career_limit * 0.80  # NO-GO zone start
    
    # ECharts multi-series chart with shaded zones
    x_labels = [d.strftime("%Y-%m-%d") for d in timeline_df["date"]]
    cumulative_values = timeline_df["cumulative_dose_msv"].tolist()
    
    # Dynamic axis bounds
    rad_min, rad_max = _auto_axis_bounds(
        cumulative_values,
        padding_pct=0.15,
        min_floor=0,
    )
    # Ensure career limit is visible
    rad_max = max(rad_max, actual_career_limit * 1.1)
    
    # Build series with shaded zones using stacked areas
    series_list = []
    
    # Zone 1: GO (0-30%) - Green (stacked from 0 to threshold_30)
    series_list.append({
        "name": "GO Zone (0-30%)",
        "type": "line",
        "data": [threshold_30] * len(x_labels),
        "lineStyle": {"width": 0},
        "stack": "zones",
        "areaStyle": {"color": "rgba(39, 174, 96, 0.15)"},  # Green
        "symbol": "none",
        "silent": True,
    })
    
    # Zone 2: MONITOR (30-60%) - Yellow (stacked from threshold_30 to threshold_60)
    series_list.append({
        "name": "MONITOR Zone (30-60%)",
        "type": "line",
        "data": [threshold_60 - threshold_30] * len(x_labels),
        "lineStyle": {"width": 0},
        "stack": "zones",
        "areaStyle": {"color": "rgba(255, 193, 7, 0.15)"},  # Yellow
        "symbol": "none",
        "silent": True,
    })
    
    # Zone 3: CAUTION (60-80%) - Orange (stacked from threshold_60 to threshold_80)
    series_list.append({
        "name": "CAUTION Zone (60-80%)",
        "type": "line",
        "data": [threshold_80 - threshold_60] * len(x_labels),
        "lineStyle": {"width": 0},
        "stack": "zones",
        "areaStyle": {"color": "rgba(253, 126, 20, 0.15)"},  # Orange
        "symbol": "none",
        "silent": True,
    })
    
    # Zone 4: NO-GO (80-100%) - Red (stacked from threshold_80 to career_limit)
    series_list.append({
        "name": "NO-GO Zone (80-100%)",
        "type": "line",
        "data": [actual_career_limit - threshold_80] * len(x_labels),
        "lineStyle": {"width": 0},
        "stack": "zones",
        "areaStyle": {"color": "rgba(220, 53, 69, 0.15)"},  # Red
        "symbol": "none",
        "silent": True,
    })
    
    # Actual cumulative dose line
    series_list.append({
        "name": "Cumulative Dose",
        "type": "line",
        "data": cumulative_values,
        "smooth": True,
        "lineStyle": {"width": 3, "color": "#1a1a1a"},
        "symbol": "circle",
        "symbolSize": 4,
        "z": 10,  # Above zones
    })
    
    # Career limit line
    series_list.append({
        "name": f"Career Limit ({actual_career_limit:.0f} mSv)",
        "type": "line",
        "data": [actual_career_limit] * len(x_labels),
        "lineStyle": {"type": "dashed", "color": "#2c3e50", "width": 2},
        "symbol": "none",
        "z": 5,
    })
    
    # Threshold lines
    series_list.append({
        "name": "MONITOR (30%)",
        "type": "line",
        "data": [threshold_30] * len(x_labels),
        "lineStyle": {"type": "dotted", "color": "#ffc107", "width": 1},
        "symbol": "none",
        "z": 5,
    })
    
    series_list.append({
        "name": "CAUTION (60%)",
        "type": "line",
        "data": [threshold_60] * len(x_labels),
        "lineStyle": {"type": "dotted", "color": "#fd7e14", "width": 1},
        "symbol": "none",
        "z": 5,
    })
    
    series_list.append({
        "name": "NO-GO (80%)",
        "type": "line",
        "data": [threshold_80] * len(x_labels),
        "lineStyle": {"type": "dotted", "color": "#dc3545", "width": 1},
        "symbol": "none",
        "z": 5,
    })
    
    chart_option = {
        "title": {
            "text": f"Radiation Exposure Projection ({selected_env_label})",
            "left": "center",
            "textStyle": {"color": "#1a1a1a", "fontWeight": "bold"},
        },
        "subtitle": {
            "text": f"Career Limit: {actual_career_limit:.0f} mSv ({career_limit_standard}) | Solar Cycle: {solar_phase.upper()}",
            "left": "center",
            "top": 35,
            "textStyle": {"color": "#2c3e50", "fontSize": 12},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": "{b}<br/>{a0}: {c0} mSv<br/>{a1}: {c1} mSv",
        },
        "legend": {
            "data": ["Cumulative Dose", f"Career Limit ({actual_career_limit:.0f} mSv)", "MONITOR (30%)", "CAUTION (60%)", "NO-GO (80%)"],
            "top": 50,
            "textStyle": {"color": "#1a1a1a"},
        },
        "grid": {"left": 60, "right": 40, "top": 120, "bottom": 60},
        "xAxis": {
            "type": "category",
            "data": x_labels,
            "boundaryGap": False,
            "axisLabel": {"rotate": 45, "interval": max(1, len(x_labels) // 10), "color": "#1a1a1a"},
            "axisLine": {"lineStyle": {"color": "#2c3e50"}},
        },
        "yAxis": {
            "type": "value",
            "name": "Cumulative Dose (mSv)",
            "min": rad_min,
            "max": rad_max,
            "nameTextStyle": {"color": "#1a1a1a"},
            "axisLabel": {"color": "#1a1a1a"},
            "axisLine": {"lineStyle": {"color": "#2c3e50"}},
            "splitLine": {"lineStyle": {"color": "#ecf0f1"}},
        },
        "dataZoom": [{"type": "inside"}, {"type": "slider", "bottom": 10}],
        "series": series_list,
    }
    render_echarts(chart_option, height_px=400)
    
    # Add reference note
    st.caption(
        "📚 **References**: NASA-STD-3001 Vol 1 Rev B (2022) - Career effective dose limit: 600 mSv. "
        "ESA/ICRP Publication 123 (2013) - Career limit: 1000 mSv. "
        "Zones: GO (<30%), MONITOR (30-60%), CAUTION (60-80%), NO-GO (>80%). "
        "Data from NOAA SWPC space weather feeds."
    )
    
    # Summary metrics
    final_dose = timeline[-1].cumulative_dose_msv
    final_pct = timeline[-1].career_pct_used
    days_to_30pct = next((t.mission_day for t in timeline if t.career_pct_used >= 30.0), None)
    days_to_60pct = next((t.mission_day for t in timeline if t.career_pct_used >= 60.0), None)
    days_to_80pct = next((t.mission_day for t in timeline if t.career_pct_used >= 80.0), None)
    days_to_limit = next((t.mission_day for t in timeline if t.career_pct_used >= 100.0), None)
    
    # Determine current zone
    if final_pct < 30:
        current_zone = "GO"
        zone_color = "#27ae60"
    elif final_pct < 60:
        current_zone = "MONITOR"
        zone_color = "#ffc107"
    elif final_pct < 80:
        current_zone = "CAUTION"
        zone_color = "#fd7e14"
    else:
        current_zone = "NO-GO"
        zone_color = "#dc3545"
    
    col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
    with col_s1:
        st.metric("Final dose", f"{final_dose:.1f} mSv")
    with col_s2:
        st.metric("Career % used", f"{final_pct:.1f}%")
    with col_s3:
        st.markdown(f"**Current Zone:** <span style='color: {zone_color}; font-weight: bold;'>{current_zone}</span>", unsafe_allow_html=True)
    with col_s4:
        st.metric("Days to MONITOR (30%)", f"{days_to_30pct or '> projection'}")
    with col_s5:
        st.metric("Days to LIMIT (100%)", f"{days_to_limit or '> projection'}")
    
    # Show dose rate info
    dose_info = get_dose_rate_info(selected_env)
    st.caption(
        f"**Dose rate:** {dose_info.get('nominal_msv_per_day', 0):.3f} mSv/day "
        f"(range: {dose_info.get('range_low_msv_per_day', 0):.3f}–{dose_info.get('range_high_msv_per_day', 0):.3f}) | "
        f"**Reference:** {dose_info.get('reference', 'N/A')}"
    )
    
    # Data table - using checkbox instead of expander (cannot nest expanders)
    if st.checkbox("📋 Show Timeline Data Table", value=False, key="rad_timeline_data_toggle"):
        display_df = timeline_df[["date", "mission_day", "daily_dose_msv", "eva_hours", "total_dose_msv", "cumulative_dose_msv", "career_pct_used"]].copy()
        display_df.columns = ["Date", "Mission Day", "Daily Dose (mSv)", "EVA Hours", "Total Daily (mSv)", "Cumulative (mSv)", "Career %"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)


def _render_radiation_environment_comparison(mission_days: int) -> None:
    """Render comparison of dose rates across all environments."""
    st.markdown("**🌍 Environment Dose Rate Comparison**")
    
    if not RADIATION_MODULE_AVAILABLE:
        st.warning("Radiation exposure module not available.")
        return
    
    # Get comparison data
    col_dur, col_eva = st.columns(2)
    with col_dur:
        duration = st.number_input(
            "Mission duration (days)",
            min_value=1,
            max_value=1000,
            value=max(30, mission_days),
            step=30,
            key="rad_env_duration",
        )
    with col_eva:
        eva_total = st.number_input(
            "Total EVA hours",
            min_value=0.0,
            max_value=500.0,
            value=0.0,
            step=10.0,
            key="rad_env_eva",
        )
    
    comparison_df = compare_environments(
        mission_duration_days=int(duration),
        eva_hours_total=float(eva_total),
        initial_dose_msv=0.0,
    )
    
    # Display as bar chart
    chart_option = {
        "title": {"text": f"Projected Dose for {duration}-day Mission", "left": "center"},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "grid": {"left": 150, "right": 40, "top": 60, "bottom": 40},
        "xAxis": {"type": "value", "name": "Cumulative Dose (mSv)"},
        "yAxis": {
            "type": "category",
            "data": comparison_df["environment"].tolist(),
            "axisLabel": {"fontSize": 11},
        },
        "series": [
            {
                "type": "bar",
                "data": [
                    {
                        "value": round(val, 2),
                        "itemStyle": {
                            "color": "#28a745" if pct < 30 else "#ffc107" if pct < 60 else "#fd7e14" if pct < 80 else "#dc3545"
                        },
                    }
                    for val, pct in zip(comparison_df["projected_dose_msv"], comparison_df["career_pct"])
                ],
                "label": {"show": True, "position": "right", "formatter": "{c} mSv"},
            }
        ],
        "visualMap": {
            "show": False,
            "min": 0,
            "max": 600,
            "inRange": {"color": ["#28a745", "#ffc107", "#fd7e14", "#dc3545"]},
        },
    }
    render_echarts(chart_option, height_px=400)
    
    # Table with details
    st.dataframe(
        comparison_df[["environment", "nominal_rate_msv_day", "projected_dose_msv", "career_pct", "reference"]],
        use_container_width=True,
        hide_index=True,
    )
    
    st.caption(
        "**Career %** is the percentage of NASA's 600 mSv career effective dose limit. "
        "Colors: Green (<30%), Yellow (30-60%), Orange (60-80%), Red (>80%)."
    )


def _render_radiation_eva_matrix(
    user: UserProfile,
    history_df: pd.DataFrame,
    latest_entry: Dict[str, Any],
    current_env: Optional[Any],
) -> None:
    """Render EVA Go/No-Go decision matrix for radiation exposure."""
    st.markdown("**🚀 EVA Radiation Risk Assessment (Go/No-Go)**")
    
    if not RADIATION_MODULE_AVAILABLE:
        st.warning("Radiation exposure module not available.")
        return
    
    # Get current cumulative dose
    cumulative_dose = 0.0
    if "radiation_dose_msv" in history_df.columns:
        dose_series = pd.to_numeric(history_df["radiation_dose_msv"], errors="coerce").dropna()
        if not dose_series.empty:
            cumulative_dose = float(dose_series.max())
    
    # Environment selection
    env_options = [
        ("Low Earth Orbit (ISS)", RadiationEnvironment.LEO_ISS),
        ("Lunar Gateway", RadiationEnvironment.LUNAR_GATEWAY),
        ("Lunar Surface", RadiationEnvironment.LUNAR_SURFACE_NOMINAL),
        ("Mars Surface", RadiationEnvironment.MARS_SURFACE),
    ]
    
    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        env_labels = [e[0] for e in env_options]
        default_idx = 0
        if current_env:
            for i, (_, env) in enumerate(env_options):
                if env == current_env:
                    default_idx = i
                    break
        selected_env_label = st.selectbox(
            "EVA Environment",
            env_labels,
            index=default_idx,
            key="eva_matrix_env",
        )
        selected_env = next((e[1] for e in env_options if e[0] == selected_env_label), RadiationEnvironment.LEO_ISS)
    
    with col_e2:
        eva_duration = st.number_input(
            "EVA Duration (hours)",
            min_value=1.0,
            max_value=12.0,
            value=6.0,
            step=0.5,
            key="eva_matrix_duration",
        )
    
    with col_e3:
        cumulative_dose = st.number_input(
            "Current Cumulative Dose (mSv)",
            min_value=0.0,
            max_value=1000.0,
            value=cumulative_dose,
            step=10.0,
            key="eva_matrix_cumulative",
        )
    
    # Space Weather Conditions with Auto-Fetch Option
    st.markdown("##### 🌞 Space Weather Conditions")
    
    manual_only = bool(st.session_state.get("manual_processing_only", True))
    
    # Auto-fetch toggle and button
    col_auto, col_fetch = st.columns([2, 1])
    with col_auto:
        auto_fetch_key = f"eva_auto_fetch_sw_{user.user_id}"
        if auto_fetch_key not in st.session_state:
            st.session_state[auto_fetch_key] = not manual_only
        auto_fetch_sw = st.checkbox(
            "🛰️ Auto-fetch from NOAA SWPC",
            key=auto_fetch_key,
            help=(
                "Automatically retrieve current space weather conditions from NOAA Space Weather "
                "Prediction Center. S-Scale (Solar Radiation Storm) is based on >10 MeV proton flux. "
                "G-Scale (Geomagnetic Storm) is based on planetary Kp index."
            ),
        )
    
    # Fetch and display real-time space weather data
    noaa_s_scale: int = 0
    noaa_g_scale: int = 0
    noaa_kp_max: Optional[float] = None
    noaa_proton_max: Optional[float] = None
    fetch_timestamp: Optional[str] = None
    
    if auto_fetch_sw:
        # Get today's space weather summary
        target_date = date.today()
        space_summary = _space_weather_summary_for_date(target_date)
        noaa_s_scale = int(space_summary.get("proton_s_level", 0))
        noaa_g_scale = int(space_summary.get("kp_g_level", 0))
        noaa_kp_max = space_summary.get("kp_max")
        noaa_proton_max = space_summary.get("proton_max_pfu")
        
        # Show real-time data metrics
        col_sw_m1, col_sw_m2, col_sw_m3, col_sw_m4 = st.columns(4)
        with col_sw_m1:
            kp_display = f"{noaa_kp_max:.1f}" if noaa_kp_max is not None and np.isfinite(float(noaa_kp_max)) else "—"
            st.metric("Kp Index (max)", kp_display, delta=space_summary.get("kp_g_scale", "G0"))
        with col_sw_m2:
            proton_display = f"{noaa_proton_max:.0f} pfu" if noaa_proton_max is not None and np.isfinite(float(noaa_proton_max)) else "—"
            st.metric(">10 MeV Protons", proton_display, delta=space_summary.get("proton_s_scale", "S0"))
        with col_sw_m3:
            st.metric("S-Scale", f"S{noaa_s_scale}", delta=_s_scale_severity_label(noaa_s_scale))
        with col_sw_m4:
            st.metric("G-Scale", f"G{noaa_g_scale}", delta=_g_scale_severity_label(noaa_g_scale))
        
        # Alert if data is unavailable or stale
        errors = space_summary.get("errors", {})
        if errors:
            st.caption(f"⚠️ NOAA data may be stale or unavailable. Use manual override if needed.")
    
    with col_fetch:
        if st.button(
            "🔄 Refresh",
            key=f"eva_refresh_sw_{user.user_id}",
            help="Force refresh space weather data from NOAA SWPC",
            use_container_width=True,
        ):
            if NOAA_SPACE_AVAILABLE and load_noaa_space_data is not None:
                with st.spinner("Fetching NOAA data..."):
                    try:
                        _bundles, _errors = load_noaa_space_data(
                            keys=("planetary_k_index_1m", "goes_integral_protons"),
                            use_cache=False,
                            max_workers=2,
                            overall_timeout_s=15.0,
                        )
                        _load_noaa_profile_bundles.clear()
                        if not _errors:
                            st.success("✅ Space weather data refreshed")
                        else:
                            st.warning(f"Partial fetch: {', '.join(_errors.values())}")
                        safe_rerun("profile_tab_rerun")
                    except Exception as exc:
                        _LOGGER.warning("EVA matrix space weather refresh failed: %s", exc)
                        st.error(f"Refresh failed: {exc}")
            else:
                st.warning("NOAA space module not available.")
    
    # Manual override or fallback inputs
    col_sw1, col_sw2 = st.columns(2)
    with col_sw1:
        default_s = noaa_s_scale if auto_fetch_sw else 0
        s_scale = st.selectbox(
            "NOAA S-Scale (Radiation Storm)",
            options=[0, 1, 2, 3, 4, 5],
            index=default_s,
            format_func=lambda x: f"S{x}" + (" - None" if x == 0 else f" - {_s_scale_severity_label(x)}"),
            key="eva_s_scale",
            disabled=False,  # Always allow override
            help="S-Scale: S0=None, S1=Minor, S2=Moderate, S3=Strong, S4=Severe, S5=Extreme. Based on >10 MeV proton flux (pfu).",
        )
    with col_sw2:
        default_g = noaa_g_scale if auto_fetch_sw else 0
        g_scale = st.selectbox(
            "NOAA G-Scale (Geomagnetic Storm)",
            options=[0, 1, 2, 3, 4, 5],
            index=default_g,
            format_func=lambda x: f"G{x}" + (" - None" if x == 0 else f" - {_g_scale_severity_label(x)}"),
            key="eva_g_scale",
            disabled=False,  # Always allow override
            help="G-Scale: G0=None, G1=Minor, G2=Moderate, G3=Strong, G4=Severe, G5=Extreme. Based on Kp index.",
        )
    
    if auto_fetch_sw and (s_scale != noaa_s_scale or g_scale != noaa_g_scale):
        st.caption("ℹ️ Manual override active — using selected values instead of NOAA data.")
    
    # Perform assessment
    assessment = assess_eva_radiation_risk(
        cumulative_dose_msv=cumulative_dose,
        environment=selected_env,
        eva_duration_hours=eva_duration,
        space_weather_s_scale=s_scale,
        space_weather_g_scale=g_scale,
    )
    
    # Display result as large status indicator
    status_colors = {
        EVARadiationStatus.GO: ("#28a745", "✅"),
        EVARadiationStatus.GO_WITH_MONITORING: ("#ffc107", "⚠️"),
        EVARadiationStatus.CAUTION: ("#fd7e14", "⚠️"),
        EVARadiationStatus.NO_GO: ("#dc3545", "🚫"),
    }
    
    color, icon = status_colors.get(assessment.status, ("#6c757d", "❓"))
    
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, {color}22 0%, {color}11 100%);
                    padding: 1.5rem; border-radius: 12px; border-left: 6px solid {color};
                    margin: 1rem 0; text-align: center;">
            <h2 style="margin: 0; color: {color}; font-size: 2.5rem;">{icon} {assessment.status.value.replace('_', ' ')}</h2>
            <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem; color: #333;">{assessment.rationale}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Detail metrics
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    with col_d1:
        st.metric("Post-EVA Cumulative", f"{assessment.cumulative_dose_msv:.1f} mSv")
    with col_d2:
        st.metric("Career % Used", f"{assessment.career_pct_used:.1f}%")
    with col_d3:
        st.metric("Remaining Career", f"{assessment.remaining_career_msv:.1f} mSv")
    with col_d4:
        st.metric("Max EVA Today", f"{assessment.max_eva_hours_today:.1f} h")
    
    # Recommendations
    if assessment.recommendations:
        st.markdown("##### 📋 Recommendations")
        for rec in assessment.recommendations:
            st.markdown(f"- {rec}")
    
    # Space weather alert
    if assessment.space_weather_alert != "None":
        st.warning(f"🌞 **Space Weather Alert:** {assessment.space_weather_alert}")
    
    # Risk matrix visualization
    st.markdown("##### 🎯 EVA Radiation Risk Matrix")
    
    # Build risk matrix similar to SAFTE/FRMS
    likelihood_order = ["Low", "Moderate", "High", "Very High"]
    severity_order = ["Negligible", "Minor", "Major", "Severe"]
    
    risk_matrix = [
        ["GO", "GO", "MONITOR", "CAUTION"],
        ["GO", "MONITOR", "CAUTION", "NO-GO"],
        ["MONITOR", "CAUTION", "NO-GO", "NO-GO"],
        ["CAUTION", "NO-GO", "NO-GO", "NO-GO"],
    ]
    
    risk_color_map = {"GO": 1, "MONITOR": 2, "CAUTION": 3, "NO-GO": 4}
    
    heatmap_data = []
    for y_idx, sev in enumerate(severity_order):
        for x_idx, lik in enumerate(likelihood_order):
            risk_label = risk_matrix[y_idx][x_idx]
            heatmap_data.append([x_idx, y_idx, risk_color_map[risk_label]])
    
    # Determine current position
    career_pct = assessment.career_pct_used
    if career_pct < 30:
        sev_idx = 0
    elif career_pct < 60:
        sev_idx = 1
    elif career_pct < 80:
        sev_idx = 2
    else:
        sev_idx = 3
    
    if s_scale == 0 and g_scale == 0:
        lik_idx = 0
    elif s_scale <= 1 and g_scale <= 1:
        lik_idx = 1
    elif s_scale <= 2 or g_scale <= 2:
        lik_idx = 2
    else:
        lik_idx = 3
    
    matrix_option = {
        "tooltip": {"position": "top"},
        "grid": {"left": 120, "right": 50, "top": 30, "bottom": 120},
        "xAxis": {
            "type": "category",
            "data": likelihood_order,
            "name": "Likelihood (Space Weather)",
            "nameLocation": "middle",
            "nameGap": 35,
            "axisLabel": {"fontSize": 13},
            "nameTextStyle": {"fontSize": 14, "fontWeight": "bold"},
        },
        "yAxis": {
            "type": "category",
            "data": severity_order,
            "name": "Severity (Career Dose)",
            "nameTextStyle": {"fontSize": 14, "fontWeight": "bold"},
            "axisLabel": {"fontSize": 13},
        },
        "visualMap": {
            "show": False,
            "type": "piecewise",
            "pieces": [
                {"value": 1, "label": "GO", "color": "#28a745"},
                {"value": 2, "label": "MONITOR", "color": "#ffc107"},
                {"value": 3, "label": "CAUTION", "color": "#fd7e14"},
                {"value": 4, "label": "NO-GO", "color": "#dc3545"},
            ],
        },
        "series": [
            {
                "name": "Risk Matrix",
                "type": "heatmap",
                "data": heatmap_data,
                "label": {"show": False},
            },
            {
                "name": "Current Assessment",
                "type": "scatter",
                "data": [[lik_idx, sev_idx, 5]],
                "symbolSize": 35,
                "itemStyle": {
                    "color": "rgba(0,0,0,0)",
                    "borderColor": "#000",
                    "borderWidth": 3,
                },
            },
        ],
    }
    render_echarts(matrix_option, height_px=380)
    
    # Legend displayed separately below chart to avoid clutter
    st.markdown(
        """<div style="text-align: center; margin-top: 5px;">
            <span style="display: inline-block; margin: 0 15px;">
                <span style="background: #28a745; padding: 4px 12px; border-radius: 4px; color: white; font-weight: bold;">GO</span>
            </span>
            <span style="display: inline-block; margin: 0 15px;">
                <span style="background: #ffc107; padding: 4px 12px; border-radius: 4px; color: #333; font-weight: bold;">MONITOR</span>
            </span>
            <span style="display: inline-block; margin: 0 15px;">
                <span style="background: #fd7e14; padding: 4px 12px; border-radius: 4px; color: white; font-weight: bold;">CAUTION</span>
            </span>
            <span style="display: inline-block; margin: 0 15px;">
                <span style="background: #dc3545; padding: 4px 12px; border-radius: 4px; color: white; font-weight: bold;">NO-GO</span>
            </span>
        </div>""",
        unsafe_allow_html=True,
    )
    
    st.caption(
        "**Matrix interpretation:** Likelihood is based on current space weather conditions (S/G scale). "
        "Severity is based on cumulative career dose. The black circle shows your current assessment position."
    )
    
    # Scientific references - using checkbox instead of expander (cannot nest expanders)
    if st.checkbox("📚 Show Scientific References", value=False, key="rad_eva_refs_toggle"):
        st.markdown("""
**Radiation Dose Rates & Limits:**
- NASA-STD-3001 Vol 1 Rev B (2022). Crew Health Standard. Career limit: 600 mSv.
- Zhang et al. (2020). First measurements of the radiation dose on the lunar surface. *Science Advances*, 6(39), eaaz1334. [DOI: 10.1126/sciadv.aaz1334](https://doi.org/10.1126/sciadv.aaz1334)
- Simonsen et al. (2025). Moon to Mars Space Radiation Protection. NASA ASCEND Technical Report.
- ICRP Publication 123 (2013). Assessment of radiation exposure of astronauts in space.

**ISS Measurements:**
- Berger et al. (2020). MATROSHKA-R experiment. ~0.3-0.7 mSv/day effective dose.
- NASA LSAH Newsletter (2023). ISS dose rates: 0.2-0.5 mSv/day.

**Mars Measurements:**
- Zeitlin et al. (2013). Mars cruise: ~1.84 mSv/day (MSL RAD).
- Hassler et al. (2014). Mars surface: ~0.64 mSv/day (MSL RAD).
        """)


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

    # Radiation exposure - Enhanced with evidence-based dose models
    _render_radiation_exposure_section(user, history_df, latest_entry)

    # EVA workload
    st.markdown("##### 🧑‍🚀 EVA Workload & Clearance Status")
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
    
    # Get current space weather for semaphore
    space_summary = _space_weather_summary_for_date(date.today())
    current_s_scale = int(space_summary.get("proton_s_level", 0))
    current_g_scale = int(space_summary.get("kp_g_level", 0))
    
    # Get Flight Surgeon's latest EVA clearance decision
    flight_surgeon_clearance = str(latest_entry.get("eva_status", "")) if latest_entry is not None else ""
    
    # Get radiation assessment status if available (from latest entry or compute)
    radiation_status: Optional[str] = None
    if RADIATION_MODULE_AVAILABLE:
        # Try to get cumulative dose for radiation assessment
        cumulative_dose_msv = 0.0
        if "radiation_dose_msv" in history_df.columns:
            dose_series = pd.to_numeric(history_df["radiation_dose_msv"], errors="coerce").dropna()
            if not dose_series.empty:
                cumulative_dose_msv = float(dose_series.max())
        
        # Perform quick radiation assessment for semaphore
        try:
            from radiation_exposure import assess_eva_radiation_risk, RadiationEnvironment
            rad_assessment = assess_eva_radiation_risk(
                cumulative_dose_msv=cumulative_dose_msv,
                environment=RadiationEnvironment.LEO_ISS,  # Default for quick check
                eva_duration_hours=6.0,
                space_weather_s_scale=current_s_scale,
                space_weather_g_scale=current_g_scale,
            )
            radiation_status = rad_assessment.status.value
        except Exception as exc:
            _LOGGER.debug("Radiation assessment for semaphore failed: %s", exc)
    
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
        if eva_status_counts.sum() > 0 or flight_surgeon_clearance:
            # Render enhanced semaphore with joint decision
            _render_eva_semaphore(
                eva_status_counts,
                flight_surgeon_clearance=flight_surgeon_clearance,
                radiation_status=radiation_status,
                s_scale=current_s_scale,
                g_scale=current_g_scale,
                show_factors=True,
            )
            st.caption(
                "EVA clearance based on joint decision: Flight Surgeon clearance (authoritative), "
                "Radiation Risk Matrix assessment, and Space Weather conditions (NOAA S/G scales). "
                "The most restrictive status determines the final decision."
            )
    else:
        # No eva_status column, but still show semaphore based on space weather + radiation
        if flight_surgeon_clearance or current_s_scale > 0 or current_g_scale > 0:
            empty_counts = pd.Series({"GO": 0, "MONITOR": 0, "NO-GO": 0})
            _render_eva_semaphore(
                empty_counts,
                flight_surgeon_clearance=flight_surgeon_clearance or "Cleared",
                radiation_status=radiation_status,
                s_scale=current_s_scale,
                g_scale=current_g_scale,
                show_factors=True,
            )
            st.caption(
                "EVA clearance based on current Space Weather (NOAA S/G scales) and Radiation Risk. "
                "Log medical records with EVA status for historical tracking."
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

    # Publication-quality Stress Index & PNS chart
    if not hrv_daily.empty:
        has_stress = "stress_index" in hrv_daily.columns and hrv_daily["stress_index"].dropna().any()
        has_pns = "parasympathetic_index" in hrv_daily.columns and hrv_daily["parasympathetic_index"].dropna().any()
        if has_stress or has_pns:
            # Extract data with index as dates
            hrv_sorted = hrv_daily.sort_index()
            dates_list = [str(d) for d in hrv_sorted.index.tolist()]
            stress_data = (
                hrv_sorted["stress_index"].tolist() if has_stress else None
            )
            pns_data = (
                hrv_sorted["parasympathetic_index"].tolist() if has_pns else None
            )
            stress_pns_chart = _build_stress_pns_chart(
                dates=dates_list,
                stress_index=stress_data,
                pns_index=pns_data,
                title="HRV Stress Index & Parasympathetic Index (Daily Medians)",
            )
            render_echarts(stress_pns_chart, height_px=380)
            st.markdown(
                "**📊 Data Source:** Only Polar device measurements (RR-intervals) are used for these calculations. "
                "Garmin data is excluded to ensure accuracy.\n\n"
                "*Stress Index (Baevsky) reflects sympathetic activation; elevated values "
                "(>100) indicate sustained stress. PNS Index measures parasympathetic "
                "(vagal) activity; values >1.0 suggest good recovery capacity.* "
                "**References:** Baevsky & Chernikova (2017), Nunan et al. (2010), Shaffer & Ginsberg (2017)."
                "*(Baevsky et al., 2002; Shaffer & Ginsberg, 2017)*"
            )
    
    # Publication-quality Sleep Duration chart
    if not garmin_daily.empty and "sleep_duration_hours" in garmin_daily.columns:
        sleep_col = garmin_daily["sleep_duration_hours"].dropna()
        if not sleep_col.empty:
            garmin_sorted = garmin_daily.sort_index()
            sleep_dates = [str(d) for d in garmin_sorted.index.tolist()]
            sleep_values = garmin_sorted["sleep_duration_hours"].tolist()
            sleep_chart = _build_sleep_duration_chart(
                dates=sleep_dates,
                sleep_hours=sleep_values,
                title="Objective Sleep Duration (Garmin Wearable)",
            )
            render_echarts(sleep_chart, height_px=380)
            st.markdown(
                "*NSF guidelines recommend 7-9 hours of sleep for adults. "
                "Sleep <6 hours is associated with cognitive impairment and "
                "increased accident risk in operational settings.* "
                "*(Hirshkowitz et al., 2015; Watson et al., 2015)*"
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
    
    # ─────────────────────────────────────────────────────────────────────
    # Space Weather Refresh Button (outside form to allow immediate action)
    # ─────────────────────────────────────────────────────────────────────
    sw_refresh_col1, sw_refresh_col2 = st.columns([3, 1])
    with sw_refresh_col1:
        st.caption(
            "☢️ **Space Weather Data** — Real-time Kp index, proton flux, and storm scales "
            "from NOAA SWPC ([swpc.noaa.gov](https://www.swpc.noaa.gov/)). "
            "Scales: G0–G5 (geomagnetic), S0–S5 (solar radiation). "
            "References: NOAA Space Weather Scales (2011); Pulkkinen et al. (2017) Space Weather."
        )
    with sw_refresh_col2:
        refresh_key = f"refresh_space_weather_{user.user_id}"
        if st.button(
            "🔄 Fetch Space Weather",
            key=refresh_key,
            help=(
                "Fetch latest NOAA space weather data (Kp index, >10 MeV proton flux). "
                "Sources: NOAA SWPC Planetary K-index (1-min), GOES Integral Protons. "
                "Data used for G-scale (geomagnetic) and S-scale (radiation storm) classification."
            ),
            use_container_width=True,
        ):
            if NOAA_SPACE_AVAILABLE and load_noaa_space_data is not None:
                with st.spinner("Fetching NOAA space weather data..."):
                    try:
                        # Force fresh fetch from NOAA SWPC
                        _bundles, _errors = load_noaa_space_data(
                            keys=("planetary_k_index_1m", "goes_integral_protons"),
                            use_cache=False,  # Force network fetch
                            max_workers=2,
                            overall_timeout_s=15.0,
                        )
                        # Clear the profile cache so it reloads with fresh data
                        _load_noaa_profile_bundles.clear()
                        if _errors:
                            _LOGGER.warning("Space weather partial fetch: %s", _errors)
                            st.warning(f"Partial fetch: {', '.join(_errors.values())}")
                        else:
                            _LOGGER.info("Space weather data refreshed for user %s", user.user_id)
                            st.success("✅ Space weather data updated from NOAA SWPC")
                        # Mark that space weather was refreshed so metrics recompute
                        st.session_state[f"_sw_refreshed_{user.user_id}"] = True
                        safe_rerun("profile_tab_rerun")
                    except Exception as exc:
                        _LOGGER.warning("Space weather refresh failed: %s", exc)
                        st.error(f"Refresh failed: {exc}")
            else:
                st.warning("NOAA space module not available.")
    
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
        # Check if space weather was just refreshed - if so, ensure cache is cleared
        if st.session_state.get(f"_sw_refreshed_{user.user_id}", False):
            # Clear cache to force fresh computation with newly fetched data
            _load_noaa_profile_bundles.clear()
            # Reset flag after clearing
            st.session_state[f"_sw_refreshed_{user.user_id}"] = False
        # Compute space weather summary (will use fresh data if cache was cleared)
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
        
        # STOP-BANG Sleep Apnea Screening Components
        st.markdown("**😴 STOP-BANG Sleep Apnea Screening**")
        st.caption(
            "STOP-BANG components for sleep apnea risk assessment. "
            "Reference: Chung F et al. Anesthesiology 2008;108:812-21"
        )
        col_stop1, col_stop2, col_stop3 = st.columns(3)
        with col_stop1:
            snoring = st.checkbox(
                "S: Loud snoring (heard through closed doors)",
                value=bool(latest.get("snoring", False)),
                help="STOP-BANG 'S' component: Loud snoring",
            )
        with col_stop2:
            tiredness = st.checkbox(
                "T: Daytime tiredness/fatigue",
                value=bool(latest.get("tiredness", False)),
                help="STOP-BANG 'T' component: Daytime tiredness or sleepiness",
            )
        with col_stop3:
            observed_apnea = st.checkbox(
                "O: Observed apnea (witnessed breathing stops)",
                value=bool(latest.get("observed_apnea", False)),
                help="STOP-BANG 'O' component: Has someone witnessed you stop breathing during sleep?",
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
                # STOP-BANG Sleep Apnea Screening Components
                "snoring": snoring,
                "tiredness": tiredness,
                "observed_apnea": observed_apnea,
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
                    safe_rerun("profile_tab_rerun")
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
        st.info("Active Profile for Analysis: Guest")
        
        # BLE RR Interval Recording available for guests too
        _render_ble_rr_recorder_guest()
        
        st.markdown("---")
        
        # Show login/registration
        tab_login, tab_register = st.tabs(["🔑 Login", "📝 Register"])
        
        with tab_login:
            _render_login_section()
        
        with tab_register:
            new_user = _render_registration_form()
            if new_user:
                _set_current_user(new_user)
                safe_rerun("profile_tab_rerun")
    else:
        # Top banner with login state and logout button (visible on all sections)
        banner_col1, banner_col2 = st.columns([3, 1])
        with banner_col1:
            st.success(f"✅ Active Profile for Analysis: **{current_user.full_name}**")
        with banner_col2:
            st.button(
                "🚪 Logout",
                key=f"top_logout_{current_user.user_id}",
                use_container_width=True,
                on_click=_logout_and_preserve,
            )

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

