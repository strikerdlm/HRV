# flake8: noqa
from __future__ import annotations
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
from export_utils import ExportConfiguration, ExportScope, build_markdown_report
from echarts_component import EChartsConfig, render_echarts
from noaa_space import NOAADataBundle, load_noaa_space_data, get_noaa_metric_explanations, explain_noaa_metric

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

from dataclasses import asdict, dataclass
from datetime import timezone, timedelta
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
import time

import numpy as np
import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path

# Load .env variables early (e.g., NASA_API_KEY, ACCUWEATHER_API_KEY)
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
NASA_API_KEY = os.getenv("NASA_API_KEY", "")
ACCUWEATHER_API_KEY = os.getenv("ACCUWEATHER_API_KEY", "")

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
        build_fatigue_dataframe,
        compute_fatigue_analysis,
        compute_risk_assessment,
        generate_recommendations,
        enhanced_circadian_process,
    )
    FATIGUE_AVAILABLE = True
except ImportError:
    FATIGUE_AVAILABLE = False

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


def setup_console_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Configure an application logger that writes to stderr with a stable format.
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
    app_logger = logging.getLogger("hrv_app")
    app_logger.propagate = False
    # Clear existing handlers to prevent duplicates after Streamlit reruns
    for handler in list(app_logger.handlers):
        app_logger.removeHandler(handler)

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


SWPC_BASE_URL = "https://services.swpc.noaa.gov/json/"
SWPC_TIMEOUT = 15
SWPC_EXTRA_DATASETS = {
    "Solar Regions": "solar_regions.json",
    "Solar Flare Probabilities": "solar_probabilities.json",
    "Electron Fluence Forecast": "electron_fluence_forecast.json",
}
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


@st.cache_data(ttl=300)
def _fetch_swpc_dataset(path: str) -> pd.DataFrame:
    url = f"{SWPC_BASE_URL}{path}"
    response = requests.get(url, timeout=SWPC_TIMEOUT)
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
        df = df.apply(pd.to_numeric, errors="ignore")
    return df


def get_swpc_kp_index(days: int = 14) -> pd.DataFrame:
    if days is None or int(days) <= 0:
        raise ValueError("days must be a positive integer")
    cache_file = SPACE_WEATHER_CACHE_DIR / f"kp_index_{int(days)}.json"
    cached_df = _read_dataframe_cache(
        cache_file, max_age=SPACE_WEATHER_CACHE_TTL)
    if cached_df is not None:
        return cached_df
    url = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
    response = requests.get(url, timeout=SWPC_TIMEOUT)
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
    # Ensure a unified time column name
    time_cols = [
        col for col in df.columns if np.issubdtype(
            df[col].dtype,
            np.datetime64)]
    if time_cols:
        main_time = time_cols[0]
        df = df.dropna(subset=[main_time]).sort_values(main_time)
        if "time_tag" not in df.columns:
            df = df.rename(columns={main_time: "time_tag"})
    else:
        df["time_tag"] = pd.to_datetime(
            df.iloc[:, 0], errors="coerce", utc=True)
        df = df.dropna(subset=["time_tag"]).sort_values("time_tag")
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


def get_swpc_solar_probabilities() -> pd.DataFrame:
    df = _fetch_swpc_dataset("solar_probabilities.json")
    if "time_tag" in df.columns:
        df = df.dropna(subset=["time_tag"])
        df = df.sort_values("time_tag")
    return df


@st.cache_data(show_spinner=False)
def _cached_comprehensive(
        rr: np.ndarray, include_advanced: bool) -> Dict[str, Any]:
    return compute_comprehensive_hrv(rr, include_advanced=include_advanced)


@st.cache_data(show_spinner=False)
def _cached_psd(rr: np.ndarray, method: str) -> Tuple[np.ndarray, np.ndarray]:
    return psd_curve(rr, sampling_rate=4.0, method=method)


@st.cache_data(show_spinner=False)
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


@st.cache_data(show_spinner=False)
def _cached_spectrogram(
        rr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    return spectrogram_rr(rr, sampling_rate=4.0)


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
            "correlations": {},
            "corr_params": {},
            "global_corr": pd.DataFrame(),
            "global_corr_labels": {},
        },
    )
    return state


def _load_noaa_space_datasets(
    state: Dict[str, Any],
    *,
    keys: Optional[Sequence[str]] = None,
    use_cache: bool = True,
) -> None:
    """
    Populate the NOAA space datasets in session state.
    """

    state["loading"] = True
    try:
        bundles, errors = load_noaa_space_data(keys=keys, use_cache=use_cache)
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
        raise RuntimeError("NASA_API_KEY is not set.")
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
    response = requests.get(url, params=query, timeout=DONKI_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if not data:
        return pd.DataFrame()
    if isinstance(data, dict):
        rows: List[Dict[str, Any]] = [data]
    else:
        rows = list(data)
    df = pd.json_normalize(rows)
    time_columns = _get_donki_time_columns(endpoint)
    for col in time_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    df = df.apply(pd.to_numeric, errors="ignore")
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
    freq: str = "H",
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
    base_sorted = base_times[["window_start"]].sort_values("window_start")
    tolerance = pd.Timedelta(minutes=int(tolerance_minutes))
    feature_frames: Dict[str, pd.Series] = {}
    for lag in lags_hours:
        shifted = series.copy()
        if lag:
            shift_delta = pd.Timedelta(hours=int(lag))
            shifted[time_col] = shifted[time_col] + shift_delta
        merged = pd.merge_asof(
            base_sorted,
            shifted,
            left_on="window_start",
            right_on=time_col,
            direction="nearest",
            tolerance=tolerance,
        )
        col_name = _safe_feature_name(f"{prefix}_lag_{lag:+d}h")
        feature_frames[col_name] = merged[value_col]
    feature_df = pd.DataFrame(feature_frames, index=base_sorted.index)
    return feature_df.reindex(base_times.index)


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
    try:
        state["kp_df"] = get_swpc_kp_index(days=SPACE_WEATHER_MAX_DAYS)
    except (requests.RequestException, ValueError) as exc:
        state["kp_error"] = f"Failed to retrieve K-index data: {exc}"
    try:
        state["flux_df"] = get_swpc_solar_radio_flux()
    except (requests.RequestException, ValueError) as exc:
        state["flux_error"] = f"Failed to retrieve solar radio flux: {exc}"
    state["last_updated"] = pd.Timestamp.utcnow()
    state["loaded"] = True


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
    regenerate = body_container.button(
        "Regenerate interpretation", key="gpt5_high_regenerate"
    )
    should_request = regenerate or state["payload_hash"] != payload_hash
    if should_request:
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
    if not state["markdown"]:
        body_container.info(
            "GPT-5 interpretation will appear here once generated.")
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


def _upload_section() -> Dict[str, UploadedRR]:
    st.sidebar.header("Upload RR (.txt)")
    files = st.sidebar.file_uploader(
        "Select one or more Polar-like RR .txt files (one ms value per line)",
        type=["txt"],
        accept_multiple_files=True,
    )
    out: Dict[str, UploadedRR] = {}
    if not files:
        return out
    for f in files:
        content = f.getvalue().decode("utf-8", errors="ignore")
        rr = load_rr_intervals_from_text(f.name, content)
        start_ts, precise = _infer_recording_start(f.name)
        df = _to_dataframe(f.name, rr, start_ts=start_ts)
        out[f.name] = UploadedRR(
            name=f.name,
            rr_ms=rr,
            df=df,
            recording_start_utc=start_ts,
        )
        if not precise:
            st.sidebar.warning(
                f"'{f.name}' does not encode a recording start timestamp. "
                f"Defaulting to {start_ts.strftime('%Y-%m-%d %H:%M UTC')}."
            )
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
        ts_ser = pd.to_datetime(up.df["timestamp"], errors="coerce").dropna()
        if not ts_ser.empty:
            cur_min = ts_ser.iloc[0]
            cur_max = ts_ser.iloc[-1]
            x_min = cur_min if (x_min is None or cur_min < x_min) else x_min
            x_max = cur_max if (x_max is None or cur_max > x_max) else x_max
        x_vals = up.df["timestamp"].astype(str).tolist()
        y_vals = up.df["rr_intervals_ms"].astype(float).tolist()
        if max_points is not None and len(y_vals) > max_points:
            idx = np.linspace(0, len(y_vals) - 1, max_points).astype(int)
            x = [x_vals[i] for i in idx]
            y = [y_vals[i] for i in idx]
        else:
            x = x_vals
            y = y_vals
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
            y_cl_vals = up.df["rr_intervals_ms_clean"].astype(float).tolist()
            if max_points is not None and len(y_cl_vals) > max_points:
                y_cl = [y_cl_vals[i] for i in idx]
            else:
                y_cl = y_cl_vals
            series.append(
                {
                    **_echarts_line_series(f"{name} (cleaned)", x, y_cl),
                    "lineStyle": {"width": 2, "color": "#43a047"},
                }
            )
        if "artifact_flag" in up.df.columns:
            mask_series = up.df["artifact_flag"].fillna(False)
            mask = mask_series.astype(bool).to_numpy()
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


def _plot_hr_timeseries(datasets: Dict[str, UploadedRR]) -> None:
    series = []
    x_min: Optional[pd.Timestamp] = None
    x_max: Optional[pd.Timestamp] = None
    for name, up in datasets.items():
        if up.df.empty:
            continue
        ts_ser = pd.to_datetime(up.df["timestamp"], errors="coerce").dropna()
        if not ts_ser.empty:
            cur_min = ts_ser.iloc[0]
            cur_max = ts_ser.iloc[-1]
            x_min = cur_min if (x_min is None or cur_min < x_min) else x_min
            x_max = cur_max if (x_max is None or cur_max > x_max) else x_max
        x = up.df["timestamp"].astype(str).tolist()
        y = up.df["heart_rate [bpm]"].astype(float).tolist()
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


def _plot_psd_overlay(datasets: Dict[str, UploadedRR], *, method: str) -> None:
    series = []
    for name, up in datasets.items():
        rr = up.rr_ms_clean if (up.rr_ms_clean is not None) else up.rr_ms
        f, p = _cached_psd(rr, method=str(method))
        if f.size == 0:
            continue
        series.append(
            {
                "name": f"{name}{' (cleaned)' if (up.rr_ms_clean is not None) else ''}",
                "type": "line",
                "showSymbol": False,
                "data": [[float(fi), float(pi)] for fi, pi in zip(f, p)],
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
    fxx, txx, Sxx = spectrogram_rr(rr, sampling_rate=4.0)
    if fxx.size == 0:
        st.info("Insufficient RR for spectrogram.")
        return
    # Convert to [x,y,value] triplets for ECharts heatmap
    points = []
    for j, fy in enumerate(fxx):
        # Restrict to 0–0.5 Hz for readability
        if fy > 0.5:
            continue
        for i, tx in enumerate(txx):
            points.append([float(tx), float(fy), float(Sxx[j, i])])
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
            "min": float(np.percentile(Sxx, 5)),
            "max": float(np.percentile(Sxx, 95)),
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

    tolerance = pd.Timedelta(minutes=int(merge_tolerance_minutes))
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

        for lag in lag_values:
            lag_int = int(lag)
            shifted = predictor.copy()
            shifted[bundle.time_column] = shifted[bundle.time_column] + pd.to_timedelta(
                lag_int, unit="h"
            )
            merged = pd.merge_asof(
                hrv.sort_values("start"),
                shifted[[bundle.time_column, value_column]].sort_values(
                    bundle.time_column
                ),
                left_on="start",
                right_on=bundle.time_column,
                direction="nearest",
                tolerance=tolerance,
            )
            merged = merged.dropna(subset=[value_column])
            if merged.empty:
                continue

            corr_df = _corr_table(merged, value_column, list(metric_columns))
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
    merged: pd.DataFrame, predictor_col: str, target_cols: List[str]
) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for col in target_cols:
        if col == predictor_col:
            continue
        if col not in merged.columns:
            continue
        r, p, n = _pearson_r_p(
            merged[predictor_col].to_numpy(dtype=float),
            merged[col].to_numpy(dtype=float),
        )
        rows.append({"metric": col, "pearson_r": r, "p_value": p, "n": n})
    return pd.DataFrame(rows)


def _scan_lag_correlations(
    windowed_df: pd.DataFrame,
    kp_df: pd.DataFrame,
    metrics: List[str],
    lags_hours: List[int],
    merge_tolerance_minutes: int = 90,
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
        k_shift = k.copy()
        time_idx = pd.DatetimeIndex(k_shift["time_tag"].to_list())
        time_idx = time_idx + pd.to_timedelta(int(lag), unit="h")
        k_shift["time_tag"] = time_idx
        merged = pd.merge_asof(
            w.sort_values("start"),
            k_shift[["time_tag", "kp_index"]].sort_values("time_tag"),
            left_on="start",
            right_on="time_tag",
            direction="nearest",
            tolerance=pd.Timedelta(minutes=int(merge_tolerance_minutes)),
        )
        merged = merged.dropna(subset=["kp_index"])
        if merged.empty:
            continue
        corr_df = _corr_table(merged, "kp_index", metrics)
        corr_df["lag_hours"] = int(lag)
        results.append(corr_df)
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()


OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/era5"
BOGOTA = {"latitude": 4.7110, "longitude": -74.0721}


@st.cache_data(ttl=1800)
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


def main() -> None:
    logger: logging.Logger = setup_console_logging(logging.INFO)
    # Streamlit detailed tracebacks in the UI and console
    st.set_option("client.showErrorDetails", True)
    st.set_page_config(
        page_title="HRV Analysis — Streamlit + ECharts",
        layout="wide")
    # Apply neutral layout refinements (responsive margins, full-width
    # components)
    st.markdown(
        """
		<style>
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
		</style>
		""",
        unsafe_allow_html=True,
    )
    st.title("Heart Rate Variability Analysis")
    st.caption("Developed by Dr Diego Malpica")

    uploads = _upload_section()
    if not uploads:
        st.info("👋 **Welcome to the HRV Analysis Suite!**")
        st.markdown("""
        ### Getting Started
        
        To begin your analysis, please upload your RR interval data files using the sidebar.
        
        #### Supported File Formats:
        - **Polar H10/H9 RR Export** (.txt) - One RR interval (ms) per line
        - **Kubios HRV Export** (.txt) - Standard RR interval format
        - **Elite HRV Export** (.txt) - Compatible RR format
        
        #### How to Export Your Data:
        
        1. **From Polar Sensor Logger App:**
           - Record a session with your Polar H10/H9 chest strap
           - Export the RR data as a .txt file
           - Upload the file here
        
        2. **From Garmin Devices (Vivosmart 5, etc.):**
           - Export your wellness data from Garmin Connect
           - Download the ZIP file from Account Settings → Export Your Data
           - Extract and upload the relevant .txt files
        
        3. **From Other HRV Apps:**
           - Export RR intervals in milliseconds
           - Ensure one value per line in the .txt file
        
        #### File Naming Convention (Recommended):
        Name your files with the recording timestamp for automatic time alignment:
        ```
        YYYY-MM-DD HH-MM-SS.txt
        Example: 2025-01-15 08-30-00.txt
        ```
        
        #### What You'll Get:
        - 📊 **Time-domain metrics** (SDNN, RMSSD, pNN50)
        - 📈 **Frequency-domain analysis** (LF, HF, LF/HF ratio)
        - 🔬 **Nonlinear analysis** (Poincaré, DFA, Entropy)
        - 🌡️ **Autonomic function tests** (Valsalva, deep breathing)
        - 🌍 **Space weather correlation** (Solar activity vs HRV)
        - 🤖 **AI-powered interpretation** (GPT-5.1 analysis)
        - 📑 **Publication-ready exports** (Tables, statistics)
        
        ---
        
        💡 **Tip:** For best results, record 5-minute sessions in a relaxed, seated position 
        at the same time each day (e.g., morning upon waking).
        """)
        
        # Show sample data format
        with st.expander("📄 Sample RR Data Format"):
            st.code("""
# Example RR interval file content (one value per line in milliseconds):
823
845
812
867
834
821
856
...
            """, language="text")
        
        return

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
    minimal_mode = st.sidebar.checkbox("Minimal mode (fastest)", value=True)
    max_datasets = st.sidebar.number_input(
        "Process first N datasets", min_value=1, value=3, step=1
    )
    rr_plot_cap = st.sidebar.selectbox(
        "RR plot point cap per dataset", [
            "500", "2000", "10000", "No limit"], index=1)
    skip_freq = st.sidebar.checkbox("Skip Frequency overlay plot", value=True)
    skip_poincare = st.sidebar.checkbox("Skip Poincaré plot", value=True)
    skip_spectrogram = st.sidebar.checkbox("Skip Spectrogram", value=True)
    skip_gauges = st.sidebar.checkbox("Skip Gauges", value=False)
    show_debug = st.sidebar.checkbox(
        "Show detailed progress logs", value=False)
    # Adjust runtime log verbosity from sidebar preference
    logger.setLevel(logging.DEBUG if show_debug else logging.INFO)
    for _handler in logger.handlers:
        _handler.setLevel(logger.level)

    st.sidebar.subheader("ML enhancements")
    enable_ml = st.sidebar.checkbox(
        "Enable ML-assisted deviation clustering", value=False
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("AI interpretation")
    gpt_high_enabled = st.sidebar.toggle(
        "GPT-5.1 High Reasoning Interpretation",
        value=False,
        help="Send analysis outputs to OpenAI GPT-5.1 with high reasoning effort to obtain a doctoral-level markdown report. Requires OPENAI_API_KEY in the .env file.",
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Patient profile (covariate adjustment)")
    enable_cov = st.sidebar.checkbox(
        "Enable covariate adjustment (RMSSD/SDNN)", value=False
    )
    age_years = st.sidebar.number_input(
        "Age (years)", min_value=10, max_value=100, value=45, step=1
    )
    sex = st.sidebar.selectbox("Sex", ["Female", "Male"], index=1)
    bmi = st.sidebar.number_input(
        "BMI (kg/m²)", min_value=10.0, max_value=60.0, value=29.0, step=0.5
    )
    exercise = st.sidebar.selectbox(
        "Exercise regularity", ["Sedentary", "Moderate", "Athlete"], index=0
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

    # Prepare dataset dict (limit number of datasets for performance)
    datasets_all = uploads
    dataset_items = list(datasets_all.items())
    datasets = dict(dataset_items[: int(max_datasets)])

    # Cleaning + metadata with immediate percentage updates (no progress bars)
    total = max(1, len(datasets))
    txt_clean = st.empty()
    txt_clean.text(
        ("Cleaning datasets... " if apply_clean else "Preparing datasets... ") +
        "0%")
    logger.info(
        "Starting %s of %d dataset(s)",
        "cleaning" if apply_clean else "preparation",
        total,
    )
    meta_rows = []
    completed = 0
    for name, up in datasets.items():
        if up.rr_ms.size == 0:
            completed += 1
            txt_clean.text(
                ("Cleaning datasets... " if apply_clean else "Preparing datasets... ")
                + f"{min(100, int(completed * 100 / total))}%"
            )
            continue
        if apply_clean:
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
        txt_clean.text(
            ("Cleaning datasets... " if apply_clean else "Preparing datasets... ")
            + f"{min(100, int(completed * 100 / total))}%"
        )
    logger.info(
        "Finished %s of %d dataset(s)",
        "cleaning" if apply_clean else "preparation",
        total,
    )
    txt_clean.text(
        ("Cleaning complete." if apply_clean else "Preparation complete.") +
        " 100%")

    windowed_all: List[pd.DataFrame] = []
    txt_win = st.empty()
    txt_win.text("Computing windowed metrics... 0%")
    total_win = max(1, len(datasets))
    done_win = 0
    for name, up in datasets.items():
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
        txt_win.text(
            "Computing windowed metrics... "
            + f"{min(100, int(done_win * 100 / total_win))}%"
        )
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
    else:
        windowed_df = pd.DataFrame()
    txt_win.text("Computing windowed metrics... 100%")

    ml_summary_df = pd.DataFrame()
    ml_error_message = ""
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
        out = []
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
                        out.append(
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
                out.append(
                    {
                        "source": src,
                        "level": cur_level,
                        "start": cur_start,
                        "end": cur_end,
                        "n_windows": cur_count,
                        "max_dev_index": cur_max,
                    }
                )
        return pd.DataFrame(out)

    episodes_df = (
        _episodes(windowed_df, int(min_sustain))
        if (apply_dev and not windowed_df.empty and "dev_level" in windowed_df.columns)
        else pd.DataFrame()
    )

    # Full-recording metrics
    multi_results: List[Dict] = []
    ordered_sources: List[str] = []
    txt_full = st.empty()
    txt_full.text("Computing full-recording metrics... 0%")

    total_full = max(1, len(datasets))
    done_full = 0
    for name, up in datasets.items():
        if up.rr_ms.size >= 10:
            use_rr = (
                up.rr_ms_clean
                if (apply_clean and up.rr_ms_clean is not None)
                else up.rr_ms
            )
            m = _cached_comprehensive(
                use_rr, include_advanced=bool(high_compute))
            m["source"] = name
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
            txt_full.text(
                "Computing full-recording metrics... "
                + f"{min(100, int(done_full * 100 / total_full))}%"
            )
    txt_full.text("Computing full-recording metrics... 100%")
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

    ai_section = st.container()
    _render_gpt_high_interpretation(
        ai_section,
        enabled=gpt_high_enabled,
        meta_rows=meta_rows_for_context,
        multi_results_df=multi_results_df,
        windowed_df=windowed_df,
        episodes_df=episodes_df,
        ml_summary_df=ml_summary_df,
    )

    metric_list: List[str] = _select_hrv_metric_columns(
        windowed_df,
        exclude=("kp_index",),
    )

    # Tabs
    (
        tab_overview,
        tab_ts,
        tab_freq,
        tab_nl,
        tab_tfr,
        tab_window,
        tab_metrics,
        tab_ans,
        tab_readiness,
        tab_gauges,
        tab_unified,
        tab_biofeedback,
        tab_fatigue,
        tab_science,
        tab_space_weather,
        tab_noaa_space,
        tab_export,
        tab_refs,
        tab_about,
    ) = st.tabs(
        [
            "Overview",
            "Time Series",
            "Frequency",
            "Nonlinear",
            "Spectrogram",
            "Windowed",
            "Metrics",
            "ANS Function Tests",
            "Readiness",
            "Gauges",
            "📈 Unified Timeline",
            "🧠 Fatigue",
            "Science",
            "🫀 Biofeedback",
            "Space Weather",
            "NOAA Space",
            "Export",
            "References",
            "About",
        ]
    )
    with tab_overview:
        st.markdown("### 📊 Analysis Overview")
        st.markdown("*Summary of uploaded datasets and computed metrics*")
        
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
    with tab_ts:
        max_pts = None if rr_plot_cap == "No limit" else int(rr_plot_cap)
        _plot_rr_timeseries(
            datasets,
            dev_windows=(
                windowed_df
                if (apply_dev and "dev_level" in windowed_df.columns)
                else None
            ),
            max_points=max_pts,
        )
        _plot_hr_timeseries(datasets)
        st.markdown(
            "**Scientific notes (time series)**  \n"
            "- RR intervals (ms) are beat-to-beat times; healthy resting dynamics are irregular and complex.  \n"
            "- Heart rate (bpm) is the inverse of RR; variability in RR reflects autonomic modulation.  \n"
            "Short-term norms and physiological context summarized by "
            "[Task Force 1996](https://www.escardio.org/static-file/Escardio/Guidelines/Scientific-Statements/guidelines-Heart-Rate-Variability-FT-1996.pdf) "
            "and updated in [Shaffer & Ginsberg, 2017](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full).")
    with tab_freq:
        if skip_freq:
            st.info("Frequency overlay disabled (Performance & display).")
        else:
            _plot_psd_overlay(datasets, method=psd_method)
        st.markdown(
            "**Scientific notes (frequency domain)**  \n"
            "- Bands: VLF 0.0033–0.04 Hz, LF 0.04–0.15 Hz, HF 0.15–0.40 Hz.  \n"
            "- HF indexes respiratory sinus arrhythmia (parasympathetic activity); LF reflects baroreflex and mixed influences; LF/HF has limited validity as a 'balance' index and should be interpreted with breathing context.  \n"
            "References: [Task Force 1996](https://www.escardio.org/static-file/Escardio/Guidelines/Scientific-Statements/guidelines-Heart-Rate-Variability-FT-1996.pdf); "
            "[Nunan et al., 2010](https://pubmed.ncbi.nlm.nih.gov/20663071/); "
            "[Shaffer & Ginsberg, 2017](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full).")
    with tab_nl:
        if skip_poincare:
            st.info("Poincaré plot disabled (Performance & display).")
        else:
            _plot_poincare(datasets)
        st.markdown(
            "**Scientific notes (nonlinear)**  \n"
            "- Poincaré SD1 ≈ RMSSD (short-term vagal modulation); SD2 relates to longer-term variability.  \n"
            "- DFA α1 ≈ 0.75–1.25 at rest reflects healthy fractal-like regulation; lower values can indicate exercise intensity near the aerobic threshold in exertional contexts.  \n"
            "References: [Shaffer & Ginsberg, 2017](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full).")
    with tab_tfr:
        if skip_spectrogram:
            st.info("Spectrogram disabled (Performance & display).")
        else:
            _plot_spectrogram(datasets)
        st.markdown(
            "**Scientific notes (time–frequency)**  \n"
            "- Spectrogram visualizes how spectral power evolves; HF tracks respiration; LF reflects slower autonomic rhythms.  \n"
            "- Stationarity assumptions matter; windowed PSD improves interpretability for long, varying recordings.")
    with tab_window:
        st.markdown(
            "**Scientific notes (windowed metrics)**  \n"
            "- Sliding windows (e.g., 5 min, step 1 min) estimate locally stationary segments to track trends over time.  \n"
            "- Minimum RR count safeguards metric stability; interpretation should consider protocol and respiration.")
        if not windowed_df.empty:
            st.dataframe(
                windowed_df[
                    ["start", "source"]
                    + [c for c in windowed_df.columns if c not in ("start", "source")]
                ].head(50)
            )
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
        
        if not multi_results_df.empty:
            st.dataframe(multi_results_df)
            novel_columns = [
                "hrf_pip_pct",
                "hrf_ials",
                "hrf_pss_pct",
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
        else:
            st.info("No metrics to display.")
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
        if not pns_mapping:
            st.info(
                "Upload multiple sessions with successful metric computation to enable readiness analysis."
            )
        else:
            ordered_names = [
                name for name in ordered_sources if name in pns_mapping]
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
                        pns_mapping[name]
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
                            pns_mapping.get(
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
                                    [label, float(pns_mapping[label])]
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
        
        if skip_gauges:
            st.info("Gauges disabled (Performance & display).")
        else:
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
                
                # Correlation Matrix
                st.markdown("---")
                st.markdown("#### 🔗 Metric Correlations")
                
                if STATISTICAL_ANALYSIS_AVAILABLE and len(selected_metrics) >= 2:
                    # Validate that selected metrics exist in the dataframe
                    available_metrics = [m for m in selected_metrics if m in multi_results_df.columns]
                    
                    if len(available_metrics) < 2:
                        st.warning("Not enough valid metrics available for correlation analysis.")
                    else:
                        try:
                            # Compute correlation matrix only with available metrics
                            corr_df = multi_results_df[available_metrics].corr()
                            
                            # Validate correlation computation succeeded
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
                                
                                # Highlight significant correlations
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
                elif len(selected_metrics) < 2:
                    st.info("Select at least 2 metrics to compute correlations.")
            elif not selected_metrics:
                st.info("Select at least one metric to display the timeline.")
        
        st.caption(
            "**Scientific basis:** Multi-metric analysis enables detection of autonomic patterns that "
            "single-metric analysis may miss. Cross-domain correlations can reveal compensatory mechanisms "
            "and early warning signs of physiological stress."
        )

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
            
            if st.session_state.get("biofeedback_running", False):
                st.markdown("#### 🟢 Session Active")
                
                # Breathing guide visualization
                st.markdown("##### 🌬️ Breathing Guide")
                
                cycle_duration = 60.0 / breathing_rate
                inhale_duration = cycle_duration * inhale_ratio
                exhale_duration = cycle_duration * (1 - inhale_ratio)
                
                # Create breathing animation data
                breath_phases = []
                phase_time = 0
                for i in range(int(breathing_rate * 2)):  # Show 2 minutes
                    breath_phases.append({"phase": "Inhale", "start": phase_time, "duration": inhale_duration})
                    phase_time += inhale_duration
                    breath_phases.append({"phase": "Exhale", "start": phase_time, "duration": exhale_duration})
                    phase_time += exhale_duration
                
                # Display current breathing instruction
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
                    unsafe_allow_html=True
                )
                
                # Simulate data in simulation mode
                if biofeedback_mode == "Simulation":
                    # Generate simulated RR intervals
                    import random
                    for _ in range(3):  # Add a few samples
                        base_rr = 857  # ~70 bpm
                        # Add respiratory modulation
                        rsa_amplitude = 50
                        rsa = rsa_amplitude * np.sin(2 * np.pi * (breathing_rate / 60) * time_module.time())
                        noise = random.gauss(0, 15)
                        rr_ms = int(base_rr + rsa + noise)
                        engine.add_rr_sample(rr_ms)
                
                # Compute current HRV
                metrics = engine.compute_hrv()
                
                if metrics:
                    # Store in history
                    st.session_state["biofeedback_coherence_history"].append(metrics.coherence)
                    st.session_state["biofeedback_hrv_history"].append({
                        "rmssd": metrics.rmssd,
                        "coherence": metrics.coherence,
                        "hr": metrics.mean_hr,
                    })
                    
                    # Display metrics
                    st.markdown("##### 📊 Real-time Metrics")
                    
                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    
                    with col_m1:
                        coherence_color = "#28a745" if metrics.coherence >= 70 else "#ffc107" if metrics.coherence >= 40 else "#dc3545"
                        st.metric(
                            "Coherence",
                            f"{metrics.coherence:.0f}%",
                            help="Target: 70%+ for high coherence"
                        )
                    
                    with col_m2:
                        st.metric(
                            "RMSSD",
                            f"{metrics.rmssd:.1f} ms",
                            help="Higher = better vagal tone"
                        )
                    
                    with col_m3:
                        st.metric(
                            "Heart Rate",
                            f"{metrics.mean_hr:.0f} bpm"
                        )
                    
                    with col_m4:
                        st.metric(
                            "Resp Rate",
                            f"{metrics.respiratory_rate:.1f} br/min" if metrics.respiratory_rate > 0 else "—"
                        )
                    
                    # Coherence gauge
                    coherence_gauge = {
                        "series": [{
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
                                        [1, "#28a745"]
                                    ]
                                }
                            },
                            "pointer": {"length": "60%", "width": 6},
                            "axisTick": {"show": False},
                            "splitLine": {"show": False},
                            "axisLabel": {"show": False},
                            "title": {"show": True, "offsetCenter": [0, "30%"], "fontSize": 14},
                            "detail": {
                                "valueAnimation": True,
                                "fontSize": 28,
                                "offsetCenter": [0, "0%"],
                                "formatter": "{value}%"
                            },
                            "data": [{"value": round(metrics.coherence), "name": "Coherence"}]
                        }]
                    }
                    
                    render_echarts(
                        coherence_gauge,
                        height_px=250,
                        config=EChartsConfig()
                    )
                    
                    # Coherence history chart
                    if len(st.session_state["biofeedback_coherence_history"]) > 5:
                        history = st.session_state["biofeedback_coherence_history"][-60:]  # Last 60 samples
                        
                        history_chart = {
                            "xAxis": {"type": "category", "data": list(range(len(history)))},
                            "yAxis": {"type": "value", "min": 0, "max": 100, "name": "Coherence %"},
                            "series": [{
                                "type": "line",
                                "data": history,
                                "smooth": True,
                                "areaStyle": {"opacity": 0.3},
                                "markLine": {
                                    "data": [
                                        {"yAxis": 70, "name": "High", "lineStyle": {"color": "#28a745", "type": "dashed"}},
                                        {"yAxis": 40, "name": "Medium", "lineStyle": {"color": "#ffc107", "type": "dashed"}},
                                    ]
                                }
                            }],
                            "visualMap": {
                                "show": False,
                                "pieces": [
                                    {"gt": 70, "lte": 100, "color": "#28a745"},
                                    {"gt": 40, "lte": 70, "color": "#ffc107"},
                                    {"gt": 0, "lte": 40, "color": "#dc3545"},
                                ]
                            }
                        }
                        
                        render_echarts(
                            history_chart,
                            height_px=200,
                            config=EChartsConfig()
                        )
                
                # Auto-refresh
                import time as time_module
                time_module.sleep(1)
                st.rerun()
            
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
        
        if not FATIGUE_AVAILABLE:
            st.error(
                "⚠️ Fatigue module not available. Please ensure `fatigue_integration.py` "
                "and the `fatigue_calculator` package are properly installed."
            )
        else:
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

**Performance Zones:**
- 🟢 **Optimal (≥80%):** Full cognitive capacity
- 🟡 **Moderate (60-79%):** Reduced but functional
- 🟠 **Poor (50-59%):** Significant impairment
- 🔴 **Critical (<50%):** High accident risk

**Scientific References:**
- Hursh et al. (2004). Fatigue models for applied research. *Aviation, Space, and Environmental Medicine*
- Van Dongen et al. (2003). Cumulative cost of additional wakefulness. *Sleep*
- Borbély (1982). Two-process model of sleep regulation. *Human Neurobiology*
                """)
            
            st.markdown("---")
            
            # Fatigue simulation settings in columns
            col_profile, col_sleep, col_work = st.columns(3)
            
            with col_profile:
                st.markdown("#### 👤 User Profile")
                fatigue_age = st.number_input(
                    "Age (years)", min_value=16, max_value=90, value=30, step=1,
                    key="fatigue_age"
                )
                fatigue_sex = st.selectbox(
                    "Sex", options=["male", "female", "other"], index=2,
                    key="fatigue_sex"
                )
                fatigue_chronotype = st.slider(
                    "Chronotype offset (hours)",
                    min_value=-2.5, max_value=2.5, value=0.0, step=0.5,
                    help="Negative = morning person, Positive = evening person",
                    key="fatigue_chronotype"
                )
            
            with col_sleep:
                st.markdown("#### 😴 Sleep Schedule")
                fatigue_sleep_quality = st.slider(
                    "Sleep quality (0-1)",
                    min_value=0.0, max_value=1.0, value=0.8, step=0.05,
                    key="fatigue_sleep_quality"
                )
                fatigue_sleep_duration = st.slider(
                    "Sleep duration (hours)",
                    min_value=4.0, max_value=10.0, value=7.0, step=0.5,
                    key="fatigue_sleep_duration"
                )
                fatigue_bedtime = st.slider(
                    "Bedtime (hour)", min_value=0, max_value=23, value=23,
                    key="fatigue_bedtime"
                )
                fatigue_waketime = st.slider(
                    "Wake time (hour)", min_value=0, max_value=23, value=7,
                    key="fatigue_waketime"
                )
                fatigue_sleep_debt = st.slider(
                    "Current sleep debt (hours)",
                    min_value=0.0, max_value=50.0, value=0.0, step=0.5,
                    key="fatigue_sleep_debt"
                )
            
            with col_work:
                st.markdown("#### 💼 Work Schedule")
                fatigue_has_work = st.checkbox(
                    "Include work schedule", value=True,
                    key="fatigue_has_work"
                )
                fatigue_work_start = st.slider(
                    "Work start (hour)", min_value=0, max_value=23, value=9,
                    disabled=not fatigue_has_work,
                    key="fatigue_work_start"
                )
                fatigue_work_end = st.slider(
                    "Work end (hour)", min_value=0, max_value=23, value=17,
                    disabled=not fatigue_has_work,
                    key="fatigue_work_end"
                )
                fatigue_cognitive_load = st.slider(
                    "Cognitive load (0-3)",
                    min_value=0, max_value=3, value=1,
                    disabled=not fatigue_has_work,
                    help="0=low, 1=moderate, 2=high, 3=very high",
                    key="fatigue_cognitive_load"
                )
            
            # Simulation settings
            st.markdown("---")
            col_sim1, col_sim2, col_sim3 = st.columns([1, 1, 2])
            
            with col_sim1:
                fatigue_days = st.number_input(
                    "Prediction days", min_value=1, max_value=14, value=3, step=1,
                    key="fatigue_days"
                )
            
            with col_sim2:
                fatigue_model = st.selectbox(
                    "Model type",
                    options=["Advanced SAFTE", "Classic SAFTE"],
                    index=0,
                    key="fatigue_model"
                )
            
            with col_sim3:
                run_fatigue = st.button(
                    "🚀 Run Fatigue Prediction",
                    type="primary",
                    key="run_fatigue_btn"
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
                        st.success("✅ Fatigue prediction completed!")
                        
                    except Exception as e:
                        st.error(f"Error running fatigue simulation: {e}")
                        _LOGGER.exception("Fatigue simulation failed")
            
            # Display results if available
            if "fatigue_result" in st.session_state:
                result = st.session_state["fatigue_result"]
                
                st.markdown("---")
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
                        "xAxis": {
                            "type": "category",
                            "data": x_data,
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
                                {"gt": 80, "lte": 100, "color": "#28a745"},
                                {"gt": 60, "lte": 80, "color": "#ffc107"},
                                {"gt": 50, "lte": 60, "color": "#fd7e14"},
                                {"gt": 0, "lte": 50, "color": "#dc3545"},
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
                                    {"yAxis": 80, "name": "Optimal", "lineStyle": {"color": "#28a745", "type": "dashed"}},
                                    {"yAxis": 60, "name": "Moderate", "lineStyle": {"color": "#ffc107", "type": "dashed"}},
                                    {"yAxis": 50, "name": "Poor", "lineStyle": {"color": "#fd7e14", "type": "dashed"}},
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
                        help="Percentage of time in poor/critical zones"
                    )
                
                # Performance zone distribution
                st.markdown("#### 🎯 Performance Zone Distribution")
                
                zones = analysis["zones"]
                zone_labels = ["Optimal (≥80%)", "Moderate (60-79%)", "Poor (50-59%)", "Critical (<50%)"]
                zone_colors = ["#28a745", "#ffc107", "#fd7e14", "#dc3545"]
                
                # ECharts pie chart for zones
                zone_chart_config = {
                    "tooltip": {"trigger": "item", "formatter": "{b}: {c} hours ({d}%)"},
                    "legend": {"orient": "horizontal", "bottom": "0%"},
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
                
                # Risk assessment
                st.markdown("#### ⚠️ Risk Assessment")
                
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
                            "xAxis": {
                                "type": "category",
                                "data": x_circ,
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
                
                st.caption(
                    f"Model: {result.model_used.upper()} SAFTE | "
                    f"Generated: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                )

    with tab_science:
        st.markdown("## 📚 Scientific Reference Guide")
        st.markdown("*Comprehensive explanations of HRV metrics and their physiological significance*")
        
        # Time-domain metrics
        with st.expander("🕐 **Time-Domain Metrics** — Beat-to-beat variability measures", expanded=True):
            st.markdown("""
| Metric | Definition | Physiology | Clinical Interpretation |
|--------|------------|------------|------------------------|
| **SDNN** | Standard deviation of all NN intervals | Reflects **total variability** from all cyclic components | Normal: 50±16 ms (5-min). ↓ with age, stress, disease. Overall autonomic health marker |
| **RMSSD** | Root mean square of successive differences | **Vagal (parasympathetic) modulation** — rapid beat-to-beat changes | Normal: 42±15 ms. ↑ = good vagal tone. ↓ = stress, fatigue, illness |
| **pNN50** | % of successive differences >50 ms | High-frequency vagal activity | Normal: 5-25%. ↑ = strong vagal influence. Very sensitive to artifacts |
| **Mean HR** | Average heart rate (bpm) | Sympathovagal balance at sinoatrial node | 60-100 bpm normal. <60 = bradycardia (may be athletic). >100 = tachycardia |
| **CVNN** | Coefficient of variation (SDNN/Mean NN) | Normalized variability independent of HR | Unitless. Useful for comparing across different heart rates |

**Key insight:** RMSSD is the most reliable short-term vagal marker. Use it for recovery monitoring and stress assessment.
            """)
        
        # Frequency-domain metrics
        with st.expander("📊 **Frequency-Domain Metrics** — Spectral power analysis", expanded=False):
            st.markdown("""
| Metric | Frequency Band | Physiology | Clinical Interpretation |
|--------|---------------|------------|------------------------|
| **VLF** | 0.0033–0.04 Hz | Thermoregulation, RAAS, slow metabolic rhythms | Requires long recordings (>5 min). ↓ predicts mortality in some cohorts |
| **LF Power** | 0.04–0.15 Hz | **Baroreflex activity** + mixed sympathetic/vagal | NOT purely sympathetic! Reflects blood pressure regulation |
| **HF Power** | 0.15–0.40 Hz | **Respiratory sinus arrhythmia** — pure vagal | ↑ with slow deep breathing. Best parasympathetic marker in frequency domain |
| **LF/HF Ratio** | LF ÷ HF | Historically "sympathovagal balance" | ⚠️ **Controversial!** Highly breathing-dependent. Use with caution |
| **LF nu / HF nu** | Normalized units | Relative contributions within LF+HF | Useful for within-subject comparisons; less affected by total power |

**Critical note:** LF/HF ratio is NOT a reliable "stress index." Slow breathing (6/min) dramatically increases LF without sympathetic activation.
            """)
        
        # Nonlinear metrics
        with st.expander("🔄 **Nonlinear Metrics** — Complexity and fractal dynamics", expanded=False):
            st.markdown("""
| Metric | Definition | Physiology | Clinical Interpretation |
|--------|------------|------------|------------------------|
| **SD1** | Poincaré plot short-axis | Short-term vagal modulation (≈ RMSSD/√2) | Reflects beat-to-beat parasympathetic control |
| **SD2** | Poincaré plot long-axis | Long-term variability + sympathetic influences | Combined autonomic and non-autonomic factors |
| **SD1/SD2** | Ratio of axes | Balance of short vs long-term dynamics | ↓ ratio may indicate reduced vagal relative to overall variability |
| **DFA α1** | Detrended fluctuation (4-16 beats) | **Fractal correlation** in short-term | 0.75–1.25 = healthy. <0.75 = uncorrelated (exercise). >1.25 = rigid control |
| **DFA α2** | Detrended fluctuation (16-64 beats) | Long-range fractal correlations | Less studied; reflects longer-term regulatory dynamics |
| **SampEn** | Sample entropy | **Complexity/irregularity** of RR series | ↓ entropy = more regular (rigid, less adaptive). ↑ = healthy complexity |
| **ApEn** | Approximate entropy | Similar to SampEn, less bias-corrected | Sensitive to data length and parameters |

**Key insight:** DFA α1 near 1.0 indicates healthy, fractal-like heart rate dynamics. Loss of complexity (↓ entropy, extreme α1) is associated with disease and aging.
            """)
        
        # Heart Rate Fragmentation
        with st.expander("⚡ **Heart Rate Fragmentation (HRF)** — Arrhythmia risk markers", expanded=False):
            st.markdown("""
| Metric | Definition | Physiology | Clinical Interpretation |
|--------|------------|------------|------------------------|
| **PIP** | % of inflection points | Frequency of direction changes | ↑ PIP = more fragmented rhythm. PROOF-AF: predicts atrial fibrillation |
| **PIP_H / PIP_S** | Hard/soft inflection points | Abrupt vs gradual direction changes | Distinguishes sudden vs smooth rhythm alterations |
| **IALS** | Inverse average length of segments | How often acceleration/deceleration runs are interrupted | ↑ IALS = shorter runs = more fragmentation |
| **W0–W3** | Word distributions (4-beat patterns) | Count of patterns by inflection count | ↑ W3 = highly fragmented. ↑ W0 = very regular |
| **PSS / PAS** | Short/alternating segment % | Rhythm pattern classification | Elevated values indicate ANS disorganization |

**Research evidence:** The PROOF-AF study (n=1011, 18-year follow-up) found PIP and reduced DFA α1 independently predicted atrial fibrillation in adults ≥65.
            """)
        
        # Autonomic Function Tests
        with st.expander("🫀 **Autonomic Function Tests** — Clinical assessment ratios", expanded=False):
            st.markdown("""
| Test | Protocol | Normal Values | Clinical Significance |
|------|----------|---------------|----------------------|
| **Valsalva Ratio** | Strain for 15s → release | ≥1.2 (age-dependent) | ↓ ratio = impaired parasympathetic response. Sensitive to autonomic neuropathy |
| **Deep Breathing E:I** | 6 breaths/min, 5s in/5s out | E:I diff ≥15 bpm (young) | ↓ response = reduced vagal modulation. Declines with age |
| **30:15 Ratio** | Stand from supine | ≥1.04 | ↓ ratio = impaired reflex tachycardia. Tests baroreceptor function |

**Clinical context:** These bedside tests are gold standards for diagnosing autonomic neuropathy (diabetic, Parkinson's, etc.). Requires standardized protocols.
            """)
        
        # Solar-Physiology correlations
        with st.expander("🌞 **Solar Activity & HRV** — Space weather correlations", expanded=False):
            st.markdown("""
| Solar Metric | Definition | Physiological Link | Evidence Level |
|--------------|------------|-------------------|----------------|
| **Kp Index** | Global geomagnetic disturbance (0-9) | ↑ Kp → ↓ HRV, ↑ HR | **Moderate** — Multiple cohort studies show reduced vagal tone during storms |
| **Dst Index** | Ring current intensity (nT) | More negative = stronger storm | **Moderate** — Correlates with Kp; similar HRV associations |
| **Solar Wind Speed** | km/s from ACE/DSCOVR | Drives magnetospheric coupling | **Emerging** — Higher speeds associated with ↑ HR, stress responses |
| **IMF Bz** | Interplanetary magnetic field z-component | Southward (<0) enhances coupling | **Emerging** — Precedes geomagnetic activity by hours |
| **F10.7 Flux** | 10.7 cm solar radio emission (sfu) | Solar cycle proxy | **Weak** — Long-term associations; confounded by seasonality |

**Key studies:**
- Vieira et al. 2022: Geomagnetic disturbances reduced HRV in older men (Normative Aging Study)
- Alabdulgader et al. 2018: Long-term HR/HRV changes with solar activity (Sci Rep)
- Gaisenok et al. 2025: Systematic review — MI/stroke risk ↑ during storms (RR ≈1.3–1.6)

⚠️ **Caution:** Effect sizes are small. Always control for time-of-day, season, temperature, and behavior. Treat as exploratory.
            """)
        
        # Reference values table
        with st.expander("📋 **Reference Values** — Short-term (5-min) healthy adult norms", expanded=False):
            st.markdown("""
| Metric | Mean ± SD | Typical Range | Age Effect | Source |
|--------|-----------|---------------|------------|--------|
| SDNN | 50 ± 16 ms | 32–93 ms | ↓ with age | Nunan 2010 |
| RMSSD | 42 ± 15 ms | 19–75 ms | ↓ with age | Nunan 2010 |
| pNN50 | 15 ± 12% | 1–50% | ↓ with age | Shaffer 2017 |
| LF Power | 519 ± 291 ms² | 193–1009 ms² | ↓ with age | Nunan 2010 |
| HF Power | 657 ± 777 ms² | 83–3630 ms² | ↓ with age | Nunan 2010 |
| LF/HF | 2.8 ± 2.6 | 0.5–11.6 | Variable | Nunan 2010 |
| DFA α1 | 1.0 ± 0.15 | 0.75–1.25 | Slight ↓ | Shaffer 2017 |
| SampEn | 1.5 ± 0.3 | 0.8–2.2 | ↓ with age | Literature |

**Important:** These are population averages. Individual baselines vary widely. **Always prioritize within-subject trends over absolute comparisons.**
            """)
        
        st.markdown("---")
        st.markdown("""
**📖 Key References:**
- [Task Force 1996](https://www.escardio.org/static-file/Escardio/Guidelines/Scientific-Statements/guidelines-Heart-Rate-Variability-FT-1996.pdf) — Original HRV standards
- [Shaffer & Ginsberg 2017](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full) — Comprehensive HRV overview
- [Nunan et al. 2010](https://pubmed.ncbi.nlm.nih.gov/20663071/) — Short-term normative values
- [Laborde et al. 2017](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2017.00213/full) — HRV guidelines for psychophysiology
- [Quigley et al. 2024](https://onlinelibrary.wiley.com/doi/10.1111/psyp.14604) — Updated publication guidelines
        """)
    with tab_space_weather:
        st.subheader("Space Weather (NOAA SWPC)")
        space_state = _space_weather_state()
        donki_state = _donki_state()
        col_fetch_sw, col_fetch_donki = st.columns(2)
        with col_fetch_sw:
            fetch_sw_clicked = st.button(
                "Fetch space weather data", key="fetch_space_weather"
            )
        with col_fetch_donki:
            fetch_donki_clicked = st.button(
                "Fetch NASA DONKI events",
                key="fetch_donki",
                disabled=not NASA_API_KEY,
                help="Requires NASA_API_KEY in your .env file.",
            )
        donki_window_days = st.slider(
            "DONKI window (days)",
            min_value=7,
            max_value=30,
            value=30,
            step=1,
            key="donki_window_days",
        )
        if fetch_sw_clicked:
            with st.spinner("Fetching NOAA SWPC datasets..."):
                _fetch_space_weather_datasets(space_state)
            last_fetch = space_state.get("last_updated")
            if isinstance(last_fetch, pd.Timestamp):
                st.success(
                    f"Space weather datasets updated at {last_fetch.strftime('%Y-%m-%d %H:%M UTC')}.")
            else:
                st.success("Space weather datasets updated.")
        if fetch_donki_clicked:
            if not NASA_API_KEY:
                st.warning(
                    "Set NASA_API_KEY in your .env file to query NASA DONKI APIs."
                )
            else:
                start_donki, end_donki = _donki_default_range(
                    int(donki_window_days))
                with st.spinner("Fetching NASA DONKI datasets..."):
                    _fetch_donki_datasets(donki_state, start_donki, end_donki)
                last_donki = donki_state.get("last_updated")
                if isinstance(last_donki, pd.Timestamp):
                    st.success(
                        f"DONKI datasets updated at {last_donki.strftime('%Y-%m-%d %H:%M UTC')}.")
                else:
                    st.success("DONKI datasets updated.")

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
            st.info("Click 'Fetch space weather data' to populate NOAA SWPC metrics.")
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

            with st.container():
                st.markdown("#### Solar Radio Flux (F10.7 cm)")
                flux_history_days = st.slider(
                    "F10.7 history (days)",
                    min_value=7,
                    max_value=90,
                    value=30,
                    step=1,
                    key="flux_days",
                )
                if flux_error_msg:
                    st.error(flux_error_msg)
                else:
                    flux_df = flux_df_full.copy()
                    if not flux_df.empty and "time_tag" in flux_df.columns:
                        time_series = pd.to_datetime(
                            flux_df["time_tag"], utc=True, errors="coerce"
                        )
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
                kp_history_days = st.slider(
                    "Kp history (days)",
                    min_value=3,
                    max_value=30,
                    value=14,
                    step=1,
                    key="kp_days",
                )
                if kp_error_msg:
                    st.error(kp_error_msg)
                else:
                    kp_df = kp_df_full.copy()
                    if not kp_df.empty and "time_tag" in kp_df.columns:
                        time_series = pd.to_datetime(
                            kp_df["time_tag"], errors="coerce", utc=True
                        )
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
            st.markdown("#### Inspect an additional NOAA dataset")
            selected_dataset = st.selectbox(
                "NOAA endpoint", list(SWPC_EXTRA_DATASETS.keys())
            )
            if selected_dataset:
                with st.expander(f"{selected_dataset} (latest rows)"):
                    try:
                        extra_df = _fetch_swpc_dataset(
                            SWPC_EXTRA_DATASETS[selected_dataset]
                        )
                    except requests.RequestException as exc:
                        st.error(
                            f"Failed to retrieve {selected_dataset.lower()}: {exc}"
                        )
                    except ValueError as exc:
                        st.error(
                            f"Unexpected response for {selected_dataset.lower()}: {exc}"
                        )
                    else:
                        if extra_df.empty:
                            st.info("No data returned for this feed.")
                        else:
                            st.dataframe(extra_df.tail(100))

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

        st.markdown("### HRV window metrics vs. planetary K-index")
        st.caption(
            "Align HRV windows to expected arrival by applying a time lag before merging."
        )
        lag_min, lag_max = st.slider(
            "Lag range (hours, applied to Kp times)", -48, 48, (-12, 12), step=1)
        lag_step = st.number_input(
            "Lag step (hours)", min_value=1, max_value=12, value=3, step=1
        )
        merge_tol = st.number_input(
            "Merge tolerance (minutes)",
            min_value=15,
            max_value=360,
            value=90,
            step=15)
        cedula = st.text_input(
            "Cedula (identification number)",
            value="",
            placeholder="e.g., 12345678")
        use_weather = st.checkbox(
            "Include weather covariates (Bogotá) for partial correlations",
            value=True)

        lags = list(range(int(lag_min), int(lag_max) + 1, int(lag_step)))
        if not lags:
            lags = [0]

        if windowed_df.empty:
            st.info("Windowed HRV metrics are not available. Run an analysis first.")
        elif "start" not in windowed_df.columns:
            st.info("Windowed HRV data does not include start timestamps.")
        elif not metric_list:
            st.info("No numeric HRV metrics available for correlation.")
        elif kp_error or kp_df.empty or "kp_index" not in kp_df.columns:
            st.info("Planetary K-index data not available for correlation.")
        else:
            # optional weather covariates fetched for time span of HRV windows
            cov_df = pd.DataFrame()
            if use_weather:
                start_dt = pd.to_datetime(
                    windowed_df["start"], errors="coerce", utc=True
                ).dropna()
                if not start_dt.empty:
                    span_min = start_dt.min().date().isoformat()
                    span_max = start_dt.max().date().isoformat()
                    try:
                        cov_df = fetch_open_meteo_hourly(span_min, span_max)
                    except requests.RequestException as exc:
                        st.warning(f"Weather API error: {exc}")
                if not cov_df.empty:
                    # align covariates to HRV window starts (ensure
                    # timezone-aware)
                    align_df = windowed_df[["start"]].copy()
                    align_df["align_time"] = pd.to_datetime(
                        align_df["start"], errors="coerce"
                    )
                    if align_df["align_time"].dt.tz is None:
                        align_df["align_time"] = align_df["align_time"].dt.tz_localize(
                            "UTC")
                    else:
                        align_df["align_time"] = align_df["align_time"].dt.tz_convert(
                            "UTC")
                    align_df = align_df.drop(columns=["start"]).dropna(
                        subset=["align_time"]
                    )

                    cov_df = cov_df.copy()
                    if cov_df["weather_time"].dt.tz is None:
                        cov_df["weather_time"] = cov_df["weather_time"].dt.tz_localize(
                            "UTC")
                    else:
                        cov_df["weather_time"] = cov_df["weather_time"].dt.tz_convert(
                            "UTC")

                    cov_cols_available = [
                        c
                        for c in [
                            "weather_time",
                            "temp_c",
                            "rh_pct",
                            "pressure_hpa",
                            "wind_ms",
                            "precip_mm",
                            "cloudcover_pct",
                        ]
                        if c in cov_df.columns
                    ]
                    cov_aligned = pd.merge_asof(
                        align_df.sort_values("align_time"),
                        cov_df.sort_values("weather_time")[cov_cols_available],
                        left_on="align_time",
                        right_on="weather_time",
                        direction="nearest",
                        tolerance=pd.Timedelta(minutes=int(merge_tol)),
                    )
                    cov_aligned = cov_aligned.drop(
                        columns=["align_time", "weather_time"], errors="ignore"
                    )
                    windowed_df = pd.concat(
                        [
                            windowed_df.reset_index(drop=True),
                            cov_aligned.reset_index(drop=True),
                        ],
                        axis=1,
                    )

            lag_results = _scan_lag_correlations(
                windowed_df,
                kp_df,
                metric_list,
                lags,
                merge_tolerance_minutes=int(merge_tol),
            )
            if lag_results.empty:
                st.info(
                    "No lagged correlations could be computed with current data.")
            else:
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

        st.markdown("#### Database summary")
        db_df = _load_jsonl()
        if db_df.empty:
            st.caption("No records saved yet.")
        else:
            st.dataframe(
                db_df.sort_values(
                    "created_utc",
                    ascending=False).head(200))

    with tab_noaa_space:
        st.markdown("### 🌍 NOAA Space Weather Dashboard")
        st.markdown("*Real-time solar and geomagnetic data for physiology correlation analysis*")
        
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
        col_fetch_noaa, col_refresh_noaa = st.columns(2)
        with col_fetch_noaa:
            fetch_noaa_clicked = st.button(
                "Fetch NOAA feeds", key="fetch_noaa_space_data"
            )
        with col_refresh_noaa:
            refresh_noaa_clicked = st.button(
                "Force refresh NOAA feeds", key="refresh_noaa_space_data"
            )
        if fetch_noaa_clicked:
            with st.spinner("Fetching NOAA JSON feeds…"):
                _load_noaa_space_datasets(noaa_state)
        if refresh_noaa_clicked:
            with st.spinner("Refreshing NOAA JSON feeds…"):
                _load_noaa_space_datasets(noaa_state, use_cache=False)
        if (
            not noaa_state.get("bundles")
            and not noaa_state.get("loading")
            and not fetch_noaa_clicked
            and not refresh_noaa_clicked
            and not noaa_state.get("errors")
        ):
            with st.spinner("Loading NOAA JSON feeds…"):
                _load_noaa_space_datasets(noaa_state)
        if noaa_state.get("loading"):
            st.info("NOAA feeds are loading…")
        errors = noaa_state.get("errors", {})
        for key, message in errors.items():
            label = "General" if key == "__global__" else key
            st.error(f"{label}: {message}")
        bundles = noaa_state.get("bundles", {})
        option_labels: Dict[str, str] = {}
        dataset_options: List[str] = []
        metrics_available: List[str] = []
        if not windowed_df.empty:
            metrics_available = [
                metric
                for metric in metric_list
                if metric in windowed_df.columns
                and pd.api.types.is_numeric_dtype(windowed_df[metric])
            ]
        if not bundles:
            st.info("Click “Fetch NOAA feeds” to populate the NOAA Space dashboard.")
        else:
            option_labels = {
                key: bundle.spec.title for key, bundle in bundles.items()
            }
            dataset_options = sorted(option_labels.keys(), key=lambda k: option_labels[k])
            selected_dataset = st.selectbox(
                "Dataset",
                options=dataset_options,
                format_func=lambda k: option_labels.get(k, k),
                key="noaa_dataset_select",
            )
            bundle: NOAADataBundle = bundles[selected_dataset]
            if bundle.spec.description:
                st.caption(bundle.spec.description)
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
            history_hours = st.slider(
                "History window (hours)",
                min_value=int(min_hours),
                max_value=int(max_hours),
                value=int(default_hours),
                step=int(step_hours),
                key=f"noaa_history_{selected_dataset}",
            )
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
            st.markdown("##### HRV correlation analysis")
            if windowed_df.empty:
                st.info("Run the HRV window analysis to enable correlations.")
            else:
                metrics_available = [
                    metric
                    for metric in metric_list
                    if metric in windowed_df.columns
                    and pd.api.types.is_numeric_dtype(windowed_df[metric])
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
                                            windowed_df,
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
        if windowed_df.empty:
            st.info("Run the HRV window analysis to enable batch correlations.")
        elif not metrics_available:
            st.info("No numeric HRV metrics available for correlation.")
        elif not dataset_options:
            st.info("Fetch NOAA feeds to enable batch correlations.")
        else:
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

    with tab_export:
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
            # Compose NOAA notes block for export (explanations + top correlations if available)
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
            # Add top batch correlations if computed
            global_corr_df = st.session_state.get("noaa_space_state", {}).get("global_corr", pd.DataFrame())
            label_lookup: Dict[Tuple[str, str], str] = st.session_state.get("noaa_space_state", {}).get(
                "global_corr_labels", {}
            )
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
                    noaa_notes_lines.append(
                        f"- {row.metric} vs {row.predictor_title} — {label}: "
                        f"r={row.pearson_r:.3f}, p={row.p_value if np.isfinite(row.p_value) else 'n/a'}, "
                        f"CI95% [{row.ci_low:.3f}, {row.ci_high:.3f}], lag {int(row.lag_hours)} h (n={int(row.n)})."
                    )
            notes_text = notes_input
            if noaa_notes_lines:
                notes_text = (notes_text + "\n\n" if notes_text.strip() else "") + "\n".join(noaa_notes_lines)
            export_config = ExportConfiguration(
                scope=scope_choice,
                include_windowed=include_windowed_opt,
                include_ml=include_ml_opt,
            )
            try:
                report_markdown = build_markdown_report(
                    meta_rows=meta_rows,
                    multi_results_df=multi_results_df,
                    windowed_df=windowed_df,
                    episodes_df=episodes_df,
                    ml_summary_df=ml_summary_df if include_ml_opt else None,
                    config=export_config,
                    selected_sources=selected_sources,
                    additional_notes=notes_text,
                )
            except ValueError as exc:
                logger.warning(
                    "Report generation failed: %s",
                    exc,
                    exc_info=True)
                st.warning(str(exc))
            else:
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
                if (
                    include_ml_opt
                    and ml_summary_df.empty
                    and enable_ml
                    and ml_error_message
                ):
                    st.info(
                        f"ML section included but no clusters were generated: {ml_error_message}")
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
        elif gpt_high_enabled:
            st.info(
                "GPT-5 interpretation is enabled; trigger the analysis to populate this section."
            )
    with tab_about:
        st.markdown(
            "### About the Author\n"
            "**Dr. Diego Leonel Malpica Hincapié** — Aerospace Medicine (Colombia)\n\n"
            "- Professional service within Colombian Military Health / Fuerza Aérea Colombiana (public record).\n"
            "- Focus areas: aerospace medicine, operational performance, fatigue, psychophysiology, and HRV.\n"
            "- This app and analysis workflow were authored and curated by Dr. Malpica.\n\n"
            "Professional Profiles & Academic References:\n"
            "- **CVLAC** (Colciencias Research Profile): "
            "[https://scienti.minciencias.gov.co/cvlac/](https://scienti.minciencias.gov.co/cvlac/)\n"
            "- **LinkedIn**: [linkedin.com/in/diegoleonelmalpica](https://www.linkedin.com/in/diegoleonelmalpica)\n"
            "- **Universidad Nacional de Colombia** (Academic Reference): "
            "[UNAL Profile](https://medicina.bogota.unal.edu.co/formacion/especialidades-medicas/medicina-aeroespacial)\n\n"
            "Project links:\n"
            "- GitHub repository: https://github.com/strikerdlm/HRV\n"
            "- HRV Normative review in this project: `docs/Normative.md`\n"
            "- Charting: [Apache ECharts](https://echarts.apache.org/handbook/en/get-started/)\n\n"
            "Notes:\n"
            "- HRV interpretation is protocol- and cohort-dependent. Use within-subject trends and documented context "
            "(posture, time-of-day, respiration) for decisions.\n")
    with tab_refs:
        st.markdown(
            "**Selected references (APA format)**  \n"
            "- Malik, M., Bigger, J. T., Camm, A. J., Kleiger, R. E., Malliani, A., Moss, A. J., & Schwartz, P. J. (1996). Heart rate variability: Standards of measurement, physiological interpretation, and clinical use. European Heart Journal, 17(3), 354–381. "
            "https://www.escardio.org/static-file/Escardio/Guidelines/Scientific-Statements/guidelines-Heart-Rate-Variability-FT-1996.pdf  \n"
            "- Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability metrics and norms. Frontiers in Public Health, 5, 258. "
            "https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full  \n"
            "- Nunan, D., Sandercock, G. R. H., & Brodie, D. A. (2010). A quantitative systematic review of normal values for short-term heart rate variability in healthy adults. Pacing and Clinical Electrophysiology, 33(11), 1407–1417. https://pubmed.ncbi.nlm.nih.gov/20663071/  \n"
            "- Quigley, K. S., Berntson, G. G., Gianaros, P. J., Jennings, J. R., Norman, G. J., Thayer, J. F., & de Geus, E. (2024). Publication guidelines for human heart rate and heart rate variability studies in psychophysiology—Part 1: Physiological underpinnings and foundations of measurement. Psychophysiology. https://onlinelibrary.wiley.com/doi/10.1111/psyp.14604  \n"
            "- Laborde, S., Mosley, E., & Thayer, J. F. (2017). Heart rate variability and cardiac vagal tone in psychophysiological research—Recommendations for experiment planning, data analysis, and data reporting. Frontiers in Psychology, 8, 213. "
            "https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2017.00213/full  \n"
            "- Sammito, S., & Böckelmann, I. (2016). Reference values for time- and frequency-domain heart rate variability measures. Heart Rhythm, 13(6), 1309–1316. https://pubmed.ncbi.nlm.nih.gov/27986557/  \n"
            "- Berkoff, D. J., Cairns, C. B., Sanchez, L. D., & Moorman, C. T. (2007). Heart rate variability in elite American track-and-field athletes. Journal of Strength and Conditioning Research, 21(1), 227–231. https://pubmed.ncbi.nlm.nih.gov/17313294/")
        st.markdown("### NASA DONKI events")
        if not NASA_API_KEY:
            st.info("Set NASA_API_KEY in your environment to enable DONKI events.")
        else:
            span = pd.to_datetime(
                windowed_df["start"], errors="coerce", utc=True
            ).dropna()
            if span.empty:
                st.info("Load HRV data to define the date range for DONKI queries.")
            else:
                start_date = span.min().date().isoformat()
                end_date = span.max().date().isoformat()
                st.caption(f"DONKI query window: {start_date} to {end_date}")
                choices = [
                    "FLR (Solar Flares)",
                    "CME",
                    "GST (Geomagnetic Storm)",
                    "IPS",
                    "HSS",
                    "RBE",
                    "SEP",
                ]
                selected = st.multiselect(
                    "DONKI predictors", choices, default=[
                        "FLR (Solar Flares)", "CME", "GST (Geomagnetic Storm)"], )
                predictor_series: List[Tuple[str, pd.DataFrame, str, str]] = []
                if not donki_state.get("loaded"):
                    st.info("Fetch NASA DONKI events to enable DONKI correlations.")
                else:
                    window_times = pd.to_datetime(
                        windowed_df["start"], errors="coerce", utc=True
                    ).dropna()
                    window_min = window_times.min() if not window_times.empty else None
                    window_max = window_times.max() if not window_times.empty else None
                    donki_datasets = donki_state.get("datasets", {})
                    donki_errors = donki_state.get("errors", {})
                    for label in selected:
                        code = DONKI_LABEL_TO_CODE.get(label)
                        if not code:
                            continue
                        df_code = donki_datasets.get(code, pd.DataFrame())
                        if df_code.empty:
                            if code in donki_errors:
                                title = DONKI_ENDPOINTS.get(
                                    code, {}).get("title", code)
                                st.warning(f"{title}: {donki_errors[code]}")
                            else:
                                st.info(f"No records available for {label}.")
                            continue
                        time_columns = _get_donki_time_columns(code)
                        series_df = donki_event_series(df_code, time_columns)
                        if series_df.empty:
                            st.info(
                                f"No time-stamped entries found for {label}.")
                            continue
                        if window_min is not None and window_max is not None:
                            margin = pd.Timedelta(days=2)
                            series_df = series_df[
                                (series_df["time_tag"] >= window_min - margin)
                                & (series_df["time_tag"] <= window_max + margin)
                            ]
                        if series_df.empty:
                            st.info(
                                f"{label}: no events overlapping the HRV window.")
                            continue
                        title = DONKI_ENDPOINTS.get(
                            code, {}).get("title", label)
                        value_col = f"donki_{code.lower()}_count"
                        predictor_series.append(
                            (title,
                             series_df.rename(
                                 columns={
                                     "event_count": value_col}),
                                "time_tag",
                                value_col,
                             ))

                if predictor_series:
                    if not metric_list:
                        st.info(
                            "Run the HRV window analysis to expose metrics before scanning DONKI correlations."
                        )
                    else:
                        st.markdown("#### DONKI correlations (lag scan)")
                        for title, s_df, tcol, vcol in predictor_series:
                            res = _scan_lag_correlations_generic(
                                windowed_df,
                                s_df.rename(columns={tcol: "time_tag"}),
                                "time_tag",
                                vcol,
                                metric_list,
                                lags,
                                merge_tolerance_minutes=int(merge_tol),
                            )
                            _render_lag_scan_summary(title, res, lags=lags)

                cme_predictors: List[Tuple[str, pd.DataFrame, str, str]] = []
                cme_df_state = space_state.get("swl_cme_df", pd.DataFrame())
                if cme_df_state.empty:
                    st.info(
                        "Fetch SpaceWeatherLive data to enable CME correlations.")
                else:
                    if not metric_list:
                        st.info(
                            "Run the HRV window analysis to expose metrics before scanning CME correlations."
                        )
                    else:
                        cme_predictors = _build_cme_predictor_series(
                            cme_df_state)
                        if not cme_predictors:
                            st.info(
                                "No numeric CME predictors available for correlation (insufficient data)."
                            )
                        else:
                            st.markdown(
                                "#### SpaceWeatherLive CME correlations (lag scan)"
                            )
                            for title, s_df, tcol, vcol in cme_predictors:
                                res = _scan_lag_correlations_generic(
                                    windowed_df,
                                    s_df.rename(columns={tcol: "time_tag"}),
                                    "time_tag",
                                    vcol,
                                    metric_list,
                                    lags,
                                    merge_tolerance_minutes=int(merge_tol),
                                )
                                _render_lag_scan_summary(title, res, lags=lags)

                all_predictors = predictor_series + cme_predictors
                with st.expander("Build HRV ↔ space-weather feature matrix (beta)"):
                    if windowed_df.empty or "start" not in windowed_df.columns:
                        st.caption(
                            "Load HRV data with window timestamps to build the feature matrix."
                        )
                    elif not metric_list:
                        st.caption(
                            "Run the HRV metrics analysis to expose numeric metrics used as targets."
                        )
                    elif not all_predictors:
                        st.caption(
                            "Fetch DONKI or SpaceWeatherLive datasets first to provide predictor series."
                        )
                    else:
                        feature_lags = sorted({int(lag) for lag in lags}) or [0]
                        st.caption(
                            f"Lags applied to each predictor: {', '.join(str(lag) for lag in feature_lags)} hour(s); "
                            f"merge tolerance {int(merge_tol)} minutes."
                        )
                        if st.button(
                            "Generate feature matrix",
                            key="btn_build_spaceweather_matrix",
                        ):
                            try:
                                feature_df = _build_space_weather_feature_matrix(
                                    windowed_df,
                                    all_predictors,
                                    lags_hours=feature_lags,
                                    tolerance_minutes=int(merge_tol),
                                    metric_columns=metric_list,
                                )
                            except ValueError as exc:
                                st.warning(str(exc))
                            else:
                                space_state["swl_feature_matrix"] = feature_df
                                st.dataframe(feature_df.head(120))
                                st.caption(
                                    f"Feature matrix shape: {feature_df.shape[0]} rows × {feature_df.shape[1]} columns. "
                                    "Rows correspond to HRV windows; predictor columns include lagged DONKI and CME metrics."
                                )
                                csv_bytes = feature_df.to_csv(
                                    index=False).encode("utf-8")
                                st.download_button(
                                    "Download feature matrix (CSV)",
                                    data=csv_bytes,
                                    file_name=f"hrv_spaceweather_features_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv",
                                    mime="text/csv",
                                    key="btn_download_spaceweather_matrix",
                                )
                    feature_matrix_cached = space_state.get(
                        "swl_feature_matrix", pd.DataFrame()
                    )
                    if not feature_matrix_cached.empty:
                        preview_cols = min(12, feature_matrix_cached.shape[1])
                        st.markdown("##### Current feature matrix preview")
                        st.dataframe(feature_matrix_cached.head(
                            80).iloc[:, :preview_cols])
                        current_metrics = [
                            col
                            for col in metric_list
                            if col in feature_matrix_cached.columns
                        ]
                        available_features = [
                            col
                            for col in feature_matrix_cached.columns
                            if col not in {"window_start", *current_metrics}
                        ]
                        if current_metrics and available_features:
                            default_features = available_features[
                                : min(12, len(available_features))
                            ]
                            selected_corr_features = st.multiselect(
                                "Predictor columns for correlation scan",
                                options=available_features,
                                default=default_features,
                                key="corr_feature_selector",
                            )
                            if st.button(
                                "Compute feature ↔ metric correlations",
                                key="btn_compute_feature_corr",
                            ):
                                try:
                                    corr_df = _compute_feature_correlations(
                                        feature_matrix_cached,
                                        current_metrics,
                                        (
                                            selected_corr_features
                                            if selected_corr_features
                                            else available_features
                                        ),
                                    )
                                except ValueError as exc:
                                    st.warning(str(exc))
                                else:
                                    st.dataframe(corr_df.head(150))
                                    corr_csv = corr_df.to_csv(
                                        index=False).encode("utf-8")
                                    st.download_button(
                                        "Download correlations (CSV)",
                                        data=corr_csv,
                                        file_name=f"hrv_spaceweather_correlations_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv",
                                        mime="text/csv",
                                        key="btn_download_feature_corr",
                                    )
                            rank_tab, model_tab = st.tabs(
                                [
                                    "Auto-rank top predictors",
                                    "Train linear response model (experimental)",
                                ]
                            )
                            with rank_tab:
                                top_k = st.slider(
                                    "Top predictors per metric",
                                    min_value=1,
                                    max_value=10,
                                    value=5,
                                    step=1,
                                    key="rank_top_k",
                                )
                                min_samples = st.slider(
                                    "Minimum overlapping samples",
                                    min_value=6,
                                    max_value=60,
                                    value=18,
                                    step=2,
                                    key="rank_min_samples",
                                )
                                if st.button(
                                    "Rank predictors",
                                    key="btn_rank_predictors",
                                ):
                                    try:
                                        rank_df = _rank_top_predictors(
                                            feature_matrix_cached,
                                            current_metrics,
                                            (
                                                selected_corr_features
                                                if selected_corr_features
                                                else available_features
                                            ),
                                            min_samples=int(min_samples),
                                            top_n=int(top_k),
                                        )
                                    except ValueError as exc:
                                        st.warning(str(exc))
                                    else:
                                        st.dataframe(rank_df)
                                        rank_csv = rank_df.to_csv(
                                            index=False).encode("utf-8")
                                        st.download_button(
                                            "Download predictor rankings (CSV)",
                                            data=rank_csv,
                                            file_name=f"hrv_spaceweather_rankings_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv",
                                            mime="text/csv",
                                            key="btn_download_rankings",
                                        )
                            with model_tab:
                                target_metric = st.selectbox(
                                    "Target HRV metric",
                                    options=current_metrics,
                                    index=0,
                                    key="model_target_metric",
                                )
                                default_model_features = available_features[
                                    : min(10, len(available_features))
                                ]
                                selected_model_features = st.multiselect(
                                    "Predictor features",
                                    options=available_features,
                                    default=default_model_features,
                                    key="model_feature_selector",
                                )
                                train_fraction = st.slider(
                                    "Training fraction",
                                    min_value=0.6,
                                    max_value=0.9,
                                    value=0.75,
                                    step=0.05,
                                    key="model_train_fraction",
                                )
                                if st.button(
                                    "Fit linear model",
                                    key="btn_fit_linear_model",
                                ):
                                    try:
                                        model_out = _fit_linear_response_model(
                                            feature_matrix_cached,
                                            target_metric,
                                            (
                                                selected_model_features
                                                if selected_model_features
                                                else available_features
                                            ),
                                            train_fraction=float(train_fraction),
                                        )
                                    except ValueError as exc:
                                        st.warning(str(exc))
                                    else:
                                        metrics_view = model_out["metrics"]
                                        col_metrics = st.columns(3)
                                        col_metrics[0].metric(
                                            "Train R²",
                                            f"{metrics_view['train_r2']:.3f}",
                                        )
                                        col_metrics[1].metric(
                                            "Test R²", f"{metrics_view['test_r2']:.3f}"
                                        )
                                        col_metrics[2].metric(
                                            "Test RMSE",
                                            f"{metrics_view['test_rmse']:.3f}",
                                        )
                                        st.caption(
                                            f"Train samples: {metrics_view['train_samples']} • "
                                            f"Test samples: {metrics_view['test_samples']} • "
                                            f"Test MAE: {metrics_view['test_mae']:.3f}"
                                        )
                                        coef_df = model_out["coefficients"]
                                        st.dataframe(coef_df)
                                        coef_csv = coef_df.to_csv(
                                            index=False).encode("utf-8")
                                        st.download_button(
                                            "Download coefficients (CSV)",
                                            data=coef_csv,
                                            file_name=f"hrv_linear_model_coefficients_{pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv",
                                            mime="text/csv",
                                            key="btn_download_model_coeffs",
                                        )
                        else:
                            st.caption(
                                "Add HRV metrics and predictor columns to compute correlations and train models."
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
    display_df = subset[
        [
            "test_name",
            "metric",
            "pearson_r",
            "p_value",
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
    formatted["ci95_low"] = formatted["ci95_low"].apply(
        lambda v: _format_with_precision(float(v), 3)
    )
    formatted["ci95_high"] = formatted["ci95_high"].apply(
        lambda v: _format_with_precision(float(v), 3)
    )
    formatted["lag_hours"] = formatted["lag_hours"].astype(int)
    formatted["n"] = formatted["n"].astype(int)
    st.dataframe(formatted, use_container_width=True)
    commentary_lines: List[str] = []
    for row in subset.itertuples():
        test_name = getattr(row, "test_name", "Pearson r")
        metric = getattr(row, "metric", "")
        r_val = getattr(row, "pearson_r", float("nan"))
        p_val = getattr(row, "p_value", float("nan"))
        ci_low = getattr(row, "ci_low", float("nan"))
        ci_high = getattr(row, "ci_high", float("nan"))
        direction = getattr(row, "direction", "neutral")
        lag = getattr(row, "lag_hours", 0)
        sample_n = getattr(row, "n", 0)
        if np.isfinite(r_val):
            r_text = f"r = {r_val:.3f}"
        else:
            r_text = "r undefined"
        commentary_lines.append(
            f"- **{metric}** ({test_name}, {friendly_name}) shows a {direction} association at lag {lag} h: "
            f"{r_text}, {_format_p_value(p_val)}, {_format_ci_text(ci_low, ci_high)}, n = {sample_n}."
        )
    st.markdown("\n".join(commentary_lines))



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
    rows: List[pd.DataFrame] = []
    for lag in lags_hours:
        shifted = pred.copy()
        time_idx = pd.DatetimeIndex(shifted[predictor_time_col].to_list())
        time_idx = time_idx + pd.to_timedelta(int(lag), unit="h")
        shifted[predictor_time_col] = time_idx
        merged = pd.merge_asof(
            w,
            shifted[[predictor_time_col, predictor_value_col]].sort_values(
                predictor_time_col
            ),
            left_on="start",
            right_on=predictor_time_col,
            direction="nearest",
            tolerance=pd.Timedelta(minutes=int(merge_tolerance_minutes)),
        )
        merged = merged.dropna(subset=[predictor_value_col])
        if merged.empty:
            continue
        corr_df = _corr_table(merged, predictor_value_col, metrics)
        corr_df["lag_hours"] = int(lag)
        rows.append(corr_df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


if __name__ == "__main__":
    main()
