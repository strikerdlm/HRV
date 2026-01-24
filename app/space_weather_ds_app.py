# Author: Dr Diego Malpica MD
"""Single-user Space Weather Data Science Streamlit app (latest Streamlit).

This app provides a streamlined, performance-focused workflow for:
- Polar RR interval uploads and Garmin Connect imports
- HRV + HRF analytics with quality control
- Space weather data ingestion and impact summaries
- Correlations, event-aligned deltas, and ML pattern detection
- Lightweight or RTX 5070 GPU-accelerated workflows
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final, Optional, Sequence

import numpy as np
import pandas as pd
import streamlit as st

from echarts_component import render_echarts
from garmin_import import (
    GarminCredentials,
    check_garmin_data_quality,
    extract_rr_intervals_from_garmin,
    get_daily_physiology_summary,
    import_garmin_data,
)
from gpu_processing import (
    GPUBackend,
    GPUConfig,
    compute_band_powers_gpu,
    compute_fft_psd_gpu,
    compute_pnn50_gpu,
    compute_poincare_gpu,
    compute_rmssd_gpu,
    compute_sdnn_gpu,
    get_gpu_info,
    is_gpu_enabled,
    set_gpu_config,
)
from hrv_core import clean_rr_intervals, compute_comprehensive_hrv, load_rr_intervals_from_text
from hrv_fragmentation import compute_hrf_metrics
from logging_config import get_logger, log_exception
from ml_analytics import analyze_trend, compute_feature_importance, detect_anomalies_isolation_forest, detect_anomalies_mad
from ml_predictions import extract_hrv_features, predict_af_risk, predict_scd_risk, predict_sleep_apnea
from noaa_space import NOAA_SOURCES, NOAADataBundle, load_noaa_space_data
from space_analytics_events import ThresholdEventConfig, compute_baseline_vs_event_deltas, extract_threshold_events
from space_weather_impact import build_impact_summary_df, fetch_space_weather_snapshot, get_priority_recommendation
from spaceweatherlive_client import fetch_spaceweatherlive_snapshot

_LOGGER: Final = get_logger(__name__)

_APP_TITLE: Final[str] = "Space Weather Data Science (Single User)"
_ENV_APP_MODE: Final[str] = "HRV_APP_MODE"


@dataclass(frozen=True, slots=True)
class RRSession:
    filename: str
    timestamp_utc: datetime
    parsed_from_filename: bool
    rr_ms: np.ndarray


@dataclass(frozen=True, slots=True)
class ProfileSettings:
    name: str
    include_advanced: bool
    max_sessions: int
    max_noaa_sources: int
    include_lag_analysis: bool


@dataclass(frozen=True, slots=True)
class QCSettings:
    method: str
    max_deviation: float
    median_window: int


_PROFILES: Final[dict[str, ProfileSettings]] = {
    "Lightweight": ProfileSettings(
        name="Lightweight",
        include_advanced=False,
        max_sessions=20,
        max_noaa_sources=6,
        include_lag_analysis=False,
    ),
    "Balanced": ProfileSettings(
        name="Balanced",
        include_advanced=True,
        max_sessions=60,
        max_noaa_sources=10,
        include_lag_analysis=True,
    ),
    "RTX 5070 GPU": ProfileSettings(
        name="RTX 5070 GPU",
        include_advanced=True,
        max_sessions=120,
        max_noaa_sources=12,
        include_lag_analysis=True,
    ),
}


def _get_scientific_colors() -> dict[str, str]:
    from user_profile_tab import SCIENTIFIC_COLORS  # local import to avoid heavy import at startup

    return SCIENTIFIC_COLORS


def _auto_axis_bounds(
    *data_arrays: Optional[Sequence[Optional[float]]],
    padding_pct: float = 0.12,
    min_floor: Optional[float] = None,
    max_ceil: Optional[float] = None,
    nice_round: bool = True,
) -> tuple[float, float]:
    values: list[float] = []
    for arr in data_arrays:
        if arr is None:
            continue
        for val in arr:
            if val is None:
                continue
            if isinstance(val, float) and np.isnan(val):
                continue
            values.append(float(val))
    if not values:
        return (0.0, 1.0)
    data_min = min(values)
    data_max = max(values)
    data_range = data_max - data_min
    if data_range <= 0:
        data_range = abs(data_min) * 0.2 if data_min != 0 else 1.0
    padding = data_range * padding_pct
    calc_min = data_min - padding
    calc_max = data_max + padding
    if min_floor is not None:
        calc_min = max(calc_min, min_floor)
    if max_ceil is not None:
        calc_max = min(calc_max, max_ceil)
    if not nice_round:
        return (float(calc_min), float(calc_max))
    magnitude = 10 ** np.floor(np.log10(abs(calc_max - calc_min)))
    rounded_min = np.floor(calc_min / magnitude) * magnitude
    rounded_max = np.ceil(calc_max / magnitude) * magnitude
    return (float(rounded_min), float(rounded_max))


def _compute_ewma(values: Sequence[Optional[float]], span: int = 7) -> list[Optional[float]]:
    series = pd.Series(values, dtype="float64")
    if series.dropna().size < 2:
        return [v if v is not None else None for v in values]
    smoothed = series.ewm(span=span, adjust=False).mean()
    return [None if np.isnan(v) else float(v) for v in smoothed.to_numpy()]


def _compute_reference_band(values: Sequence[Optional[float]]) -> tuple[float, float]:
    arr = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    if arr.size == 0:
        return (0.0, 0.0)
    low = float(np.percentile(arr, 10))
    high = float(np.percentile(arr, 90))
    if low == high:
        high = low + max(1.0, abs(low) * 0.05)
    return (low, high)


def _build_time_series_chart(
    dates: Sequence[datetime],
    values: Sequence[Optional[float]],
    *,
    metric_label: str,
    unit: str,
    subtitle: str,
) -> dict[str, Any]:
    colors = _get_scientific_colors()
    labels = [d.strftime("%Y-%m-%d") for d in dates]
    ref_low, ref_high = _compute_reference_band(values)
    ref_low_series = [ref_low for _ in labels]
    ref_high_series = [ref_high for _ in labels]
    ref_band_series = [ref_high - ref_low for _ in labels]
    trend = _compute_ewma(values, span=7)
    y_min, y_max = _auto_axis_bounds(values, trend, ref_low_series, ref_high_series)
    return {
        "title": {
            "text": metric_label,
            "subtext": subtitle,
            "left": "center",
            "textStyle": {"fontSize": 16, "fontWeight": "bold", "color": "#1a1a1a"},
            "subtextStyle": {"color": "#2c3e50"},
        },
        "tooltip": {
            "trigger": "axis",
            "textStyle": {"color": "#1a1a1a"},
        },
        "legend": {
            "data": ["Daily mean", "EWMA (7-day)", "Reference band"],
            "top": 28,
            "textStyle": {"color": "#1a1a1a"},
        },
        "grid": {"left": "10%", "right": "6%", "top": "22%", "bottom": "16%"},
        "xAxis": {
            "type": "category",
            "data": labels,
            "name": "Date (UTC)",
            "nameLocation": "middle",
            "nameGap": 30,
            "axisLabel": {"color": "#1a1a1a"},
            "axisLine": {"lineStyle": {"color": "#2c3e50"}},
        },
        "yAxis": {
            "type": "value",
            "name": f"{metric_label} ({unit})" if unit else metric_label,
            "nameLocation": "middle",
            "nameGap": 45,
            "min": y_min,
            "max": y_max,
            "axisLabel": {"color": "#1a1a1a"},
            "axisLine": {"lineStyle": {"color": "#2c3e50"}},
            "splitLine": {"lineStyle": {"color": "rgba(44, 62, 80, 0.1)"}},
        },
        "series": [
            {
                "name": "Reference low",
                "type": "line",
                "data": ref_low_series,
                "stack": "ref",
                "symbol": "none",
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": colors["normal_band"], "opacity": 0.35},
            },
            {
                "name": "Reference band",
                "type": "line",
                "data": ref_band_series,
                "stack": "ref",
                "symbol": "none",
                "lineStyle": {"opacity": 0},
                "areaStyle": {"color": colors["normal_band"], "opacity": 0.35},
            },
            {
                "name": "Daily mean",
                "type": "line",
                "data": values,
                "symbol": "circle",
                "symbolSize": 6,
                "lineStyle": {"color": colors["primary"], "width": 2},
                "itemStyle": {"color": colors["primary"]},
            },
            {
                "name": "EWMA (7-day)",
                "type": "line",
                "data": trend,
                "symbol": "none",
                "lineStyle": {"color": colors["smoothed"], "width": 2.5},
            },
        ],
    }


def _parse_timestamp_from_filename(filename: str) -> tuple[datetime, bool]:
    patterns = [
        ("%Y-%m-%d %H-%M-%S", 19),
        ("%Y-%m-%d_%H-%M-%S", 19),
        ("%Y-%m-%d", 10),
    ]
    for pattern, length in patterns:
        try:
            parsed = datetime.strptime(filename[:length], pattern)
            local_tz = timezone(timedelta(hours=-5))
            return parsed.replace(tzinfo=local_tz).astimezone(timezone.utc), True
        except (ValueError, TypeError):
            continue
    return datetime.now(timezone.utc), False


def _collect_rr_sessions(files: Sequence[Any]) -> tuple[list[RRSession], list[str]]:
    sessions: list[RRSession] = []
    warnings: list[str] = []
    for uploaded in files:
        try:
            content = uploaded.getvalue().decode("utf-8", errors="ignore")
        except (UnicodeDecodeError, AttributeError):
            warnings.append(f"{uploaded.name}: unable to decode file content.")
            continue
        rr_ms = load_rr_intervals_from_text(uploaded.name, content)
        if rr_ms.size == 0:
            warnings.append(f"{uploaded.name}: no valid RR intervals (300-2000 ms).")
            continue
        timestamp_utc, parsed = _parse_timestamp_from_filename(uploaded.name)
        sessions.append(
            RRSession(
                filename=uploaded.name,
                timestamp_utc=timestamp_utc,
                parsed_from_filename=parsed,
                rr_ms=rr_ms,
            )
        )
    return sessions, warnings


def _apply_gpu_metrics(rr_ms: np.ndarray, metrics: dict[str, float]) -> dict[str, float]:
    if not is_gpu_enabled():
        return metrics
    updated = dict(metrics)
    updated["rmssd"] = compute_rmssd_gpu(rr_ms)
    updated["sdnn"] = compute_sdnn_gpu(rr_ms)
    updated["pnn50"] = compute_pnn50_gpu(rr_ms)
    freqs, psd = compute_fft_psd_gpu(rr_ms)
    if freqs.size > 0 and psd.size > 0:
        updated.update(compute_band_powers_gpu(freqs, psd))
    updated.update(compute_poincare_gpu(rr_ms))
    return updated


def _compute_single_session_metrics(
    session: RRSession,
    qc: QCSettings,
    include_advanced: bool,
) -> dict[str, Any]:
    cleaned, _, qc_summary = clean_rr_intervals(
        session.rr_ms,
        method=qc.method,
        max_deviation=qc.max_deviation,
        median_window=qc.median_window,
    )
    metrics = compute_comprehensive_hrv(cleaned, include_advanced=include_advanced)
    metrics = _apply_gpu_metrics(cleaned, metrics)
    hrf = compute_hrf_metrics(cleaned)
    metrics.update(
        {
            "hrf_pip": hrf.pip,
            "hrf_ials": hrf.ials,
            "hrf_w3": hrf.w3,
            "artifact_pct": qc_summary.get("flagged_pct", 0.0),
        }
    )
    metrics["session_start_utc"] = session.timestamp_utc
    metrics["session_name"] = session.filename
    metrics["parsed_timestamp"] = float(session.parsed_from_filename)
    metrics["n_rr_intervals"] = int(len(cleaned))
    metrics["quality_ok"] = float(hrf.quality_ok)
    return metrics


def _compute_session_metrics(
    sessions: Sequence[RRSession],
    qc: QCSettings,
    profile: ProfileSettings,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for session in sessions[: profile.max_sessions]:
        rows.append(_compute_single_session_metrics(session, qc, profile.include_advanced))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["session_start_utc"] = pd.to_datetime(df["session_start_utc"], utc=True)
    return df.sort_values("session_start_utc", ignore_index=True)


def _build_daily_metrics(session_df: pd.DataFrame) -> pd.DataFrame:
    if session_df.empty:
        return pd.DataFrame()
    df = session_df.copy()
    df["date"] = pd.to_datetime(df["session_start_utc"], utc=True).dt.date
    daily = df.groupby("date").mean(numeric_only=True)
    daily.index = pd.to_datetime(daily.index)
    return daily.sort_index()


def _merge_garmin_daily(session_daily: pd.DataFrame, garmin_daily: pd.DataFrame) -> pd.DataFrame:
    if session_daily.empty and garmin_daily.empty:
        return pd.DataFrame()
    if session_daily.empty:
        return garmin_daily.copy()
    if garmin_daily.empty:
        return session_daily.copy()
    return session_daily.join(garmin_daily, how="outer")


def _build_garmin_daily(garmin_daily_raw: pd.DataFrame) -> pd.DataFrame:
    if garmin_daily_raw.empty:
        return pd.DataFrame()
    df = garmin_daily_raw.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).set_index("date").sort_index()
    rename_map = {
        "avg_hrv_rmssd": "rmssd",
        "avg_hr": "mean_hr",
        "resting_hr_bpm": "resting_hr",
        "avg_stress": "stress_score",
        "avg_spo2": "spo2",
        "avg_respiration_awake": "respiration_rate",
    }
    return df.rename(columns=rename_map)


def _build_solar_daily_df(
    bundles: dict[str, NOAADataBundle],
    selected_keys: Sequence[str],
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for key in selected_keys:
        bundle = bundles.get(key)
        if bundle is None or bundle.frame.empty:
            continue
        df = bundle.frame[[bundle.time_column, *bundle.value_columns]].copy()
        df[bundle.time_column] = pd.to_datetime(df[bundle.time_column], utc=True, errors="coerce")
        df = df.dropna(subset=[bundle.time_column]).set_index(bundle.time_column)
        daily = df[bundle.value_columns].resample("D").mean()
        daily = daily.rename(columns={c: f"{key}:{c}" for c in bundle.value_columns})
        frames.append(daily)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=1).sort_index()


def _summarize_noaa_bundles(bundles: dict[str, NOAADataBundle]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, bundle in bundles.items():
        if bundle.frame.empty:
            continue
        time_col = bundle.time_column
        times = pd.to_datetime(bundle.frame[time_col], utc=True, errors="coerce").dropna()
        rows.append(
            {
                "key": key,
                "title": bundle.spec.title,
                "rows": len(bundle.frame),
                "start_utc": times.min() if not times.empty else None,
                "end_utc": times.max() if not times.empty else None,
                "value_columns": ", ".join(bundle.value_columns),
            }
        )
    return pd.DataFrame(rows)


def _init_state() -> None:
    defaults = {
        "rr_sessions": [],
        "session_metrics": pd.DataFrame(),
        "daily_metrics": pd.DataFrame(),
        "garmin_data": None,
        "garmin_daily": pd.DataFrame(),
        "noaa_bundles": {},
        "noaa_errors": {},
        "spaceweatherlive_snapshot": None,
        "impact_snapshot": None,
        "performance_profile": "Lightweight",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _render_sidebar() -> ProfileSettings:
    st.sidebar.title("Workflow")
    profile_name = st.sidebar.selectbox(
        "Performance profile",
        list(_PROFILES.keys()),
        index=list(_PROFILES.keys()).index(st.session_state.get("performance_profile", "Lightweight")),
    )
    st.session_state["performance_profile"] = profile_name
    profile = _PROFILES[profile_name]
    if profile.name == "RTX 5070 GPU":
        info = get_gpu_info()
        set_gpu_config(GPUConfig(enabled=info.available, backend=GPUBackend.AUTO, device_id=0))
        st.sidebar.write(f"GPU: {info.device_name}")
        if not info.available:
            st.sidebar.warning("GPU not available. Using CPU fallback.")
    else:
        set_gpu_config(GPUConfig(enabled=False, backend=GPUBackend.CPU, device_id=0))
    if st.sidebar.button("Reset session state"):
        for key in list(st.session_state.keys()):
            st.session_state.pop(key)
        st.rerun()
    return profile


def _render_ingest_section() -> None:
    st.header("Data ingest")
    st.caption("Single-user workflow. Data remains in session memory only.")
    rr_files = st.file_uploader(
        "Upload Polar RR interval files (TXT)",
        type=["txt", "csv"],
        accept_multiple_files=True,
    )
    if rr_files and st.button("Import RR files"):
        sessions, warnings = _collect_rr_sessions(rr_files)
        st.session_state["rr_sessions"] = sessions
        if warnings:
            for warn in warnings:
                st.warning(warn)
        st.success(f"Loaded {len(sessions)} RR session(s).")
    if st.session_state["rr_sessions"]:
        st.write(f"RR sessions loaded: {len(st.session_state['rr_sessions'])}")
    with st.expander("Garmin import (API, ZIP, FIT, JSON)", expanded=False):
        st.caption("Use GARMIN_EMAIL/GARMIN_PASSWORD in .env for API access.")
        source = st.radio("Source", ["API", "ZIP", "FIT", "JSON"], horizontal=True)
        uploaded = None
        if source in {"ZIP", "FIT", "JSON"}:
            uploaded = st.file_uploader(f"Upload Garmin {source} file", type=[source.lower()])
        email = st.text_input("Garmin email (optional)", value="")
        password = st.text_input("Garmin password (optional)", value="", type="password")
        if st.button("Import Garmin data"):
            try:
                credentials = None
                if source == "API":
                    email_val = email or os.getenv("GARMIN_EMAIL", "").strip()
                    password_val = password or os.getenv("GARMIN_PASSWORD", "").strip()
                    if not email_val or not password_val:
                        st.warning("Provide Garmin email/password or set them in .env.")
                        return
                    credentials = GarminCredentials(email=email_val, password=password_val)
                data = None
                if source == "API":
                    data = import_garmin_data(credentials=credentials)
                else:
                    if uploaded is None:
                        st.warning("Upload a Garmin file first.")
                    else:
                        with tempfile.TemporaryDirectory() as tmpdir:
                            path = os.path.join(tmpdir, uploaded.name)
                            with open(path, "wb") as f:
                                f.write(uploaded.getvalue())
                            file_path = Path(path)
                            if source == "ZIP":
                                data = import_garmin_data(zip_path=file_path)
                            elif source == "FIT":
                                data = import_garmin_data(fit_path=file_path)
                            else:
                                data = import_garmin_data(json_path=file_path)
                if data is None:
                    st.error("No Garmin data imported.")
                else:
                    st.session_state["garmin_data"] = data
                    garmin_daily_raw = get_daily_physiology_summary(data)
                    st.session_state["garmin_daily"] = _build_garmin_daily(garmin_daily_raw)
                    quality = check_garmin_data_quality(data)
                    st.write(quality)
                    st.success("Garmin data imported.")
            except Exception as exc:
                log_exception(_LOGGER, "Garmin import failed", exc)
                st.error(f"Garmin import failed: {exc}")
    if st.session_state.get("garmin_data") is not None:
        if st.button("Create RR session from Garmin RR intervals"):
            try:
                rr = extract_rr_intervals_from_garmin(st.session_state["garmin_data"])
                if rr.size == 0:
                    st.warning("No Garmin RR intervals found.")
                else:
                    ts = datetime.now(timezone.utc)
                    session = RRSession(
                        filename="garmin_rr",
                        timestamp_utc=ts,
                        parsed_from_filename=False,
                        rr_ms=rr,
                    )
                    st.session_state["rr_sessions"] = st.session_state["rr_sessions"] + [session]
                    st.success("Garmin RR session added.")
            except Exception as exc:
                log_exception(_LOGGER, "Garmin RR extraction failed", exc)
                st.error(f"Garmin RR extraction failed: {exc}")


def _render_hrv_section(profile: ProfileSettings) -> None:
    st.header("HRV + HRF analysis")
    sessions: list[RRSession] = st.session_state.get("rr_sessions", [])
    if not sessions:
        st.info("Upload RR sessions or import Garmin RR data first.")
        return
    method = st.selectbox("QC method", ["threshold_median", "threshold_prev"])
    max_dev = st.slider("Max deviation (fraction)", min_value=0.05, max_value=0.5, value=0.2, step=0.05)
    median_window = st.slider("Median window", min_value=5, max_value=31, value=11, step=2)
    qc = QCSettings(method=method, max_deviation=float(max_dev), median_window=int(median_window))
    if st.button("Run HRV analysis"):
        with st.spinner("Computing HRV and HRF metrics..."):
            df = _compute_session_metrics(sessions, qc, profile)
            st.session_state["session_metrics"] = df
            st.session_state["daily_metrics"] = _build_daily_metrics(df)
    metrics_df: pd.DataFrame = st.session_state.get("session_metrics", pd.DataFrame())
    if metrics_df.empty:
        st.info("Run HRV analysis to see results.")
        return
    st.subheader("Session metrics")
    show_cols = [
        "session_start_utc",
        "rmssd",
        "sdnn",
        "mean_hr",
        "pnn50",
        "hrf_pip",
        "hrf_ials",
        "hrf_w3",
        "artifact_pct",
        "n_rr_intervals",
    ]
    available = [c for c in show_cols if c in metrics_df.columns]
    st.dataframe(metrics_df[available], use_container_width=True)
    daily_df: pd.DataFrame = st.session_state.get("daily_metrics", pd.DataFrame())
    if daily_df.empty or daily_df.shape[0] < 3:
        st.info("Need at least 3 days of data for trend charts.")
        return
    metric_choice = st.selectbox("Daily trend metric", [c for c in daily_df.columns if daily_df[c].dtype != object])
    unit_map = {"rmssd": "ms", "sdnn": "ms", "mean_hr": "bpm", "pnn50": "%", "hrf_pip": "%"}
    unit = unit_map.get(metric_choice, "")
    option = _build_time_series_chart(
        list(daily_df.index),
        daily_df[metric_choice].replace({np.nan: None}).tolist(),
        metric_label=metric_choice,
        unit=unit,
        subtitle="Daily mean with 7-day EWMA and 10-90 percentile reference band.",
    )
    render_echarts(
        option,
        height_px=380,
        caption="Citations: Task Force ESC/NASPE 1996; Shaffer & Ginsberg 2017.",
        export_basename=f"hrv_trend_{metric_choice}",
    )


def _render_space_weather_section(profile: ProfileSettings) -> None:
    st.header("Space weather data")
    source_keys = list(NOAA_SOURCES.keys())
    default_keys = source_keys[: profile.max_noaa_sources]
    selected_keys = st.multiselect("NOAA datasets", source_keys, default=default_keys)
    if st.button("Fetch NOAA feeds"):
        with st.spinner("Fetching NOAA datasets..."):
            bundles, errors = load_noaa_space_data(keys=selected_keys, use_cache=True)
            st.session_state["noaa_bundles"] = bundles
            st.session_state["noaa_errors"] = errors
    bundles = st.session_state.get("noaa_bundles", {})
    errors = st.session_state.get("noaa_errors", {})
    if errors:
        for key, msg in errors.items():
            st.warning(f"{key}: {msg}")
    if bundles:
        summary_df = _summarize_noaa_bundles(bundles)
        if not summary_df.empty:
            st.subheader("NOAA dataset summary")
            st.dataframe(summary_df, use_container_width=True)
        plot_key = st.selectbox("Plot NOAA dataset", list(bundles.keys()))
        bundle = bundles.get(plot_key)
        if bundle is not None:
            value_col = st.selectbox("Value column", list(bundle.value_columns))
            df = bundle.frame[[bundle.time_column, value_col]].copy()
            df[bundle.time_column] = pd.to_datetime(df[bundle.time_column], utc=True, errors="coerce")
            df = df.dropna(subset=[bundle.time_column]).set_index(bundle.time_column)
            daily = df[value_col].resample("D").mean().dropna()
            if daily.size >= 3:
                unit = (bundle.units or {}).get(value_col, "")
                option = _build_time_series_chart(
                    list(daily.index),
                    daily.replace({np.nan: None}).tolist(),
                    metric_label=f"{bundle.spec.title} - {value_col}",
                    unit=unit,
                    subtitle="Daily mean with 7-day EWMA and 10-90 percentile reference band.",
                )
                render_echarts(
                    option,
                    height_px=380,
                    caption="Citation: NOAA SWPC JSON feeds (https://services.swpc.noaa.gov).",
                    export_basename=f"noaa_{plot_key}_{value_col}",
                )
            else:
                st.info("Not enough data points for NOAA trend chart.")
    if st.button("Fetch SpaceWeatherLive snapshot"):
        try:
            with st.spinner("Fetching SpaceWeatherLive snapshot..."):
                st.session_state["spaceweatherlive_snapshot"] = fetch_spaceweatherlive_snapshot()
        except Exception as exc:
            log_exception(_LOGGER, "SpaceWeatherLive fetch failed", exc)
            st.error(f"SpaceWeatherLive fetch failed: {exc}")
    snapshot = st.session_state.get("spaceweatherlive_snapshot")
    if snapshot is not None:
        st.subheader("SpaceWeatherLive snapshot")
        st.json(snapshot.to_dict())
    if st.button("Fetch impact snapshot (NOAA + DONKI)"):
        try:
            with st.spinner("Fetching impact snapshot..."):
                st.session_state["impact_snapshot"] = fetch_space_weather_snapshot(overall_timeout_s=20.0)
        except Exception as exc:
            log_exception(_LOGGER, "Impact snapshot fetch failed", exc)
            st.error(f"Impact snapshot fetch failed: {exc}")
    impact = st.session_state.get("impact_snapshot")
    if impact is not None:
        st.subheader("Space weather impact summary")
        st.dataframe(build_impact_summary_df(impact), use_container_width=True)
        st.info(get_priority_recommendation(impact))


def _render_space_analytics_section(profile: ProfileSettings) -> None:
    st.header("Space analytics")
    session_daily = st.session_state.get("daily_metrics", pd.DataFrame())
    garmin_daily = st.session_state.get("garmin_daily", pd.DataFrame())
    physio_daily = _merge_garmin_daily(session_daily, garmin_daily)
    bundles = st.session_state.get("noaa_bundles", {})
    if physio_daily.empty or not bundles:
        st.info("Load HRV daily metrics and NOAA data first.")
        return
    selected_keys = list(bundles.keys())
    solar_daily = _build_solar_daily_df(bundles, selected_keys)
    if solar_daily.empty:
        st.info("No solar daily data available for analytics.")
        return
    solar_cols = list(solar_daily.columns)
    physio_cols = [c for c in physio_daily.columns if physio_daily[c].dtype != object]
    if not physio_cols:
        st.info("No numeric physiology metrics available for analytics.")
        return
    solar_pick = st.multiselect("Solar metrics", solar_cols, default=solar_cols[:2])
    physio_pick = st.multiselect("Physio metrics", physio_cols, default=physio_cols[:2])
    if st.button("Run correlation analysis"):
        if not solar_pick or not physio_pick:
            st.warning("Select at least one solar and one physio metric.")
        else:
            from solar_physiology_correlation import SolarPhysiologyAnalyzer

            aligned_physio = physio_daily[physio_pick].copy()
            analyzer = SolarPhysiologyAnalyzer(solar_daily[solar_pick], aligned_physio)
            report = analyzer.compute_all_correlations(
                solar_metrics=solar_pick,
                physio_metrics=physio_pick,
                include_lags=profile.include_lag_analysis,
            )
            result_rows = [
                {
                    "solar": r.solar_metric,
                    "physio": r.physio_metric,
                    "r": r.r,
                    "p_value": r.p_value,
                    "n": r.n,
                    "lag_days": r.lag_days,
                    "interpretation": r.interpretation,
                }
                for r in report.significant_correlations
            ]
            st.subheader("Significant correlations")
            if result_rows:
                st.dataframe(pd.DataFrame(result_rows), use_container_width=True)
            else:
                st.info("No significant correlations detected.")
    st.subheader("Event-aligned deltas")
    event_metric = st.selectbox("Solar metric for event detection", solar_cols)
    threshold = st.number_input("Threshold value", value=0.0, step=0.1)
    direction = st.selectbox("Direction", ["ge", "le"])
    baseline_days = st.slider("Baseline window (days)", min_value=1, max_value=14, value=3)
    if st.button("Compute event deltas"):
        series = solar_daily[[event_metric]].copy()
        series = series.reset_index().rename(columns={"index": "timestamp"})
        cfg = ThresholdEventConfig(
            threshold=float(threshold),
            direction=direction,  # type: ignore[arg-type]
            max_gap=pd.Timedelta(days=1),
            min_duration=pd.Timedelta(days=1),
        )
        events = extract_threshold_events(series, time_col="timestamp", value_col=event_metric, cfg=cfg)
        if events.empty:
            st.info("No events detected for the selected threshold.")
        else:
            first_event = events.iloc[0]
            physio_df = physio_daily.copy()
            physio_df = physio_df.reset_index().rename(columns={"index": "timestamp"})
            deltas = compute_baseline_vs_event_deltas(
                physio_df,
                time_col="timestamp",
                metric_cols=physio_cols,
                event_start_utc=first_event["start_utc"],
                event_end_utc=first_event["end_utc"],
                baseline_pre=pd.Timedelta(days=int(baseline_days)),
            )
            st.dataframe(deltas, use_container_width=True)


def _render_ml_section(profile: ProfileSettings) -> None:
    st.header("ML and pattern recognition")
    daily_df = st.session_state.get("daily_metrics", pd.DataFrame())
    garmin_daily = st.session_state.get("garmin_daily", pd.DataFrame())
    physio_daily = _merge_garmin_daily(daily_df, garmin_daily)
    if physio_daily.empty:
        st.info("Run HRV analysis or import Garmin data to build daily metrics.")
        return
    numeric_cols = [c for c in physio_daily.columns if physio_daily[c].dtype != object]
    if not numeric_cols:
        st.info("No numeric metrics available for ML analysis.")
        return
    metric = st.selectbox("Target metric", numeric_cols)
    values = physio_daily[metric].to_numpy(dtype=float)
    trend = analyze_trend(values)
    st.write(
        {
            "direction": trend.direction.value,
            "slope": trend.slope,
            "r_squared": trend.r_squared,
            "p_value": trend.p_value,
            "confidence": trend.confidence,
        }
    )
    anomalies = detect_anomalies_mad(values)
    st.write({"anomalies_detected": anomalies.n_anomalies, "method": anomalies.method.value})
    if profile.include_advanced and len(numeric_cols) >= 3:
        lof = detect_anomalies_isolation_forest(physio_daily, features=numeric_cols[:5])
        st.write({"isolation_forest_anomalies": lof.n_anomalies})
    importance = compute_feature_importance(physio_daily, features=numeric_cols[:5], target=metric)
    if importance:
        st.subheader("Feature importance")
        rows = [
            {
                "feature": item.feature_name,
                "importance": item.importance,
                "direction": item.direction,
                "correlation": item.correlation,
            }
            for item in importance
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    st.subheader("Risk prediction (research only)")
    sessions: list[RRSession] = st.session_state.get("rr_sessions", [])
    if not sessions:
        st.info("Upload RR sessions to generate prediction inputs.")
        return
    rr = sessions[0].rr_ms
    features = extract_hrv_features(rr.astype(np.float64))
    af = predict_af_risk(features)
    scd = predict_scd_risk(features)
    apnea = predict_sleep_apnea(features)
    st.json(
        {
            "af_risk": af.risk_level.value,
            "af_score": af.risk_score,
            "scd_risk": scd.risk_level.value,
            "scd_score": scd.risk_score,
            "sleep_apnea": apnea.severity.value,
            "sleep_apnea_probability": apnea.probability_apnea,
        }
    )


def _render_export_section() -> None:
    st.header("Export")
    session_df = st.session_state.get("session_metrics", pd.DataFrame())
    daily_df = st.session_state.get("daily_metrics", pd.DataFrame())
    if session_df.empty and daily_df.empty:
        st.info("Run analyses to enable exports.")
        return
    if not session_df.empty:
        st.download_button(
            "Download session metrics CSV",
            data=session_df.to_csv(index=False).encode("utf-8"),
            file_name="session_metrics.csv",
        )
    if not daily_df.empty:
        st.download_button(
            "Download daily metrics CSV",
            data=daily_df.to_csv(index=True).encode("utf-8"),
            file_name="daily_metrics.csv",
        )


def main() -> None:
    os.environ[_ENV_APP_MODE] = "space_weather_ds"
    st.set_page_config(page_title=_APP_TITLE, layout="wide", page_icon="S")
    _init_state()
    profile = _render_sidebar()
    section = st.sidebar.radio(
        "Section",
        ["Ingest", "HRV + HRF", "Space Weather", "Space Analytics", "ML + Patterns", "Export"],
    )
    st.title(_APP_TITLE)
    if section == "Ingest":
        _render_ingest_section()
    elif section == "HRV + HRF":
        _render_hrv_section(profile)
    elif section == "Space Weather":
        _render_space_weather_section(profile)
    elif section == "Space Analytics":
        _render_space_analytics_section(profile)
    elif section == "ML + Patterns":
        _render_ml_section(profile)
    else:
        _render_export_section()


if __name__ == "__main__":
    main()
