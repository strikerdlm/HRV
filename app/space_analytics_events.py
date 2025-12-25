"""Event-aligned analysis utilities for Space Analytics (HRV/HRF ↔ space weather).

This module is intentionally **Streamlit-free** and provides deterministic helper
functions for:

- Extracting threshold-defined space-weather events (explicit start/end)
- Computing baseline-vs-event deltas for HRV/HRF windowed metrics

All functions are bounded (linear in input size) and fully typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, Sequence

import numpy as np
import pandas as pd

from app.logging_config import get_logger

_LOGGER: Final = get_logger(__name__)

ThresholdDirection = Literal["ge", "le"]


@dataclass(frozen=True, slots=True)
class ThresholdEventConfig:
    """Configuration for threshold-based event extraction.

    Attributes:
        threshold: Threshold value used to define event samples.
        direction: "ge" means values >= threshold are "in event"; "le" means values <= threshold.
        max_gap: Maximum tolerated gap between consecutive in-event samples before splitting events.
        min_duration: Minimum duration for an event to be retained.
        pad_start: Optional padding applied before the detected event start.
        pad_end: Optional padding applied after the detected event end.
    """

    threshold: float
    direction: ThresholdDirection
    max_gap: pd.Timedelta
    min_duration: pd.Timedelta
    pad_start: pd.Timedelta = pd.Timedelta(0)
    pad_end: pd.Timedelta = pd.Timedelta(0)


def _coerce_time_series(
    df: pd.DataFrame,
    *,
    time_col: str,
    value_col: str,
) -> pd.DataFrame:
    """Return a clean, sorted (UTC) time/value DataFrame."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")
    if not time_col or not isinstance(time_col, str):
        raise TypeError("time_col must be a non-empty string.")
    if not value_col or not isinstance(value_col, str):
        raise TypeError("value_col must be a non-empty string.")
    missing = [c for c in (time_col, value_col) if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    out = df[[time_col, value_col]].copy()
    out[time_col] = pd.to_datetime(out[time_col], errors="coerce", utc=True)
    out[value_col] = pd.to_numeric(out[value_col], errors="coerce")
    out = out.dropna(subset=[time_col, value_col]).sort_values(time_col)
    return out


def extract_threshold_events(
    df: pd.DataFrame,
    *,
    time_col: str,
    value_col: str,
    cfg: ThresholdEventConfig,
) -> pd.DataFrame:
    """Extract contiguous threshold-defined events from a predictor time series.

    Events are defined by samples that satisfy a threshold condition, grouped
    into contiguous blocks where the time gap between successive in-event samples
    is <= cfg.max_gap.

    Args:
        df: Predictor time series DataFrame.
        time_col: Timestamp column name.
        value_col: Numeric value column name.
        cfg: Threshold event configuration.

    Returns:
        DataFrame with columns:
            - event_id (int)
            - start_utc (datetime64[ns, UTC])
            - end_utc (datetime64[ns, UTC])
            - duration_hours (float)
            - n_samples (int)
            - peak_value (float)
            - threshold (float)
            - direction (str: "ge"|"le")
    """
    if not isinstance(cfg, ThresholdEventConfig):
        raise TypeError("cfg must be a ThresholdEventConfig.")
    if cfg.max_gap < pd.Timedelta(0):
        raise ValueError("cfg.max_gap must be non-negative.")
    if cfg.min_duration < pd.Timedelta(0):
        raise ValueError("cfg.min_duration must be non-negative.")
    if cfg.pad_start < pd.Timedelta(0) or cfg.pad_end < pd.Timedelta(0):
        raise ValueError("cfg.pad_start/pad_end must be non-negative.")

    series = _coerce_time_series(df, time_col=time_col, value_col=value_col)
    if series.empty:
        return pd.DataFrame(
            columns=[
                "event_id",
                "start_utc",
                "end_utc",
                "duration_hours",
                "n_samples",
                "peak_value",
                "threshold",
                "direction",
            ]
        )

    if cfg.direction == "ge":
        mask = series[value_col].to_numpy(dtype=float) >= float(cfg.threshold)
        peak_func = np.nanmax
    elif cfg.direction == "le":
        mask = series[value_col].to_numpy(dtype=float) <= float(cfg.threshold)
        peak_func = np.nanmin
    else:  # pragma: no cover - defensive
        raise ValueError(f"Unsupported direction: {cfg.direction}")

    in_event = series.loc[mask, [time_col, value_col]].copy()
    if in_event.empty:
        return pd.DataFrame(
            columns=[
                "event_id",
                "start_utc",
                "end_utc",
                "duration_hours",
                "n_samples",
                "peak_value",
                "threshold",
                "direction",
            ]
        )

    times = pd.DatetimeIndex(in_event[time_col].to_list())
    values = in_event[value_col].to_numpy(dtype=float)
    if times.size != values.size:
        raise ValueError("Time/value length mismatch after filtering.")

    events: list[dict[str, object]] = []
    event_id = 0

    start_time = times[0]
    end_time = times[0]
    start_idx = 0

    for i in range(1, times.size):
        gap = times[i] - times[i - 1]
        if gap > cfg.max_gap:
            # close current event
            raw_start = start_time
            raw_end = end_time
            duration = raw_end - raw_start
            if duration >= cfg.min_duration:
                event_id += 1
                peak_value = peak_func(values[start_idx:i])
                events.append(
                    {
                        "event_id": event_id,
                        "start_utc": raw_start - cfg.pad_start,
                        "end_utc": raw_end + cfg.pad_end,
                        "duration_hours": float(duration.total_seconds() / 3600.0),
                        "n_samples": int(i - start_idx),
                        "peak_value": float(peak_value),
                        "threshold": float(cfg.threshold),
                        "direction": str(cfg.direction),
                    }
                )
            # start new
            start_time = times[i]
            end_time = times[i]
            start_idx = i
        else:
            end_time = times[i]

    # close final event
    duration = end_time - start_time
    if duration >= cfg.min_duration:
        event_id += 1
        peak_value = peak_func(values[start_idx:times.size])
        events.append(
            {
                "event_id": event_id,
                "start_utc": start_time - cfg.pad_start,
                "end_utc": end_time + cfg.pad_end,
                "duration_hours": float(duration.total_seconds() / 3600.0),
                "n_samples": int(times.size - start_idx),
                "peak_value": float(peak_value),
                "threshold": float(cfg.threshold),
                "direction": str(cfg.direction),
            }
        )

    if not events:
        return pd.DataFrame(
            columns=[
                "event_id",
                "start_utc",
                "end_utc",
                "duration_hours",
                "n_samples",
                "peak_value",
                "threshold",
                "direction",
            ]
        )

    out = pd.DataFrame(events)
    out["start_utc"] = pd.to_datetime(out["start_utc"], utc=True)
    out["end_utc"] = pd.to_datetime(out["end_utc"], utc=True)
    out = out.sort_values(["start_utc", "end_utc"], ignore_index=True)
    return out


def compute_baseline_vs_event_deltas(
    windowed_df: pd.DataFrame,
    *,
    time_col: str,
    metric_cols: Sequence[str],
    event_start_utc: pd.Timestamp,
    event_end_utc: pd.Timestamp,
    baseline_pre: pd.Timedelta,
    min_samples_per_phase: int = 3,
) -> pd.DataFrame:
    """Compute baseline vs during-event deltas for selected HRV/HRF metrics.

    Baseline windows are those with timestamps in [event_start - baseline_pre, event_start).
    Event windows are those with timestamps in [event_start, event_end].

    Args:
        windowed_df: HRV/HRF windowed metrics (must include time_col).
        time_col: Timestamp column name (e.g., "start").
        metric_cols: Metric column names to analyze (must be numeric coercible).
        event_start_utc: Event start (UTC).
        event_end_utc: Event end (UTC).
        baseline_pre: Duration before event start to use as baseline.
        min_samples_per_phase: Minimum rows required in baseline and event phases.

    Returns:
        DataFrame with one row per metric:
            metric, n_baseline, baseline_mean, baseline_std,
            n_event, event_mean, event_std,
            delta, pct_change, cohen_d
    """
    if not isinstance(windowed_df, pd.DataFrame):
        raise TypeError("windowed_df must be a pandas DataFrame.")
    if time_col not in windowed_df.columns:
        raise ValueError(f"windowed_df is missing required time column: {time_col}")
    if baseline_pre < pd.Timedelta(0):
        raise ValueError("baseline_pre must be non-negative.")
    if min_samples_per_phase < 2:
        raise ValueError("min_samples_per_phase must be >= 2.")
    if not isinstance(event_start_utc, pd.Timestamp) or not isinstance(event_end_utc, pd.Timestamp):
        raise TypeError("event_start_utc and event_end_utc must be pandas Timestamps.")

    event_start = pd.to_datetime(event_start_utc, utc=True)
    event_end = pd.to_datetime(event_end_utc, utc=True)
    if event_end < event_start:
        raise ValueError("event_end_utc must be >= event_start_utc.")

    df = windowed_df.copy()
    df[time_col] = pd.to_datetime(df[time_col], errors="coerce", utc=True)
    df = df.dropna(subset=[time_col]).sort_values(time_col)
    if df.empty:
        return pd.DataFrame()

    use_metrics: list[str] = []
    for col in metric_cols:
        if col in df.columns:
            use_metrics.append(col)
    if not use_metrics:
        return pd.DataFrame()

    baseline_start = event_start - baseline_pre
    baseline_mask = (df[time_col] >= baseline_start) & (df[time_col] < event_start)
    event_mask = (df[time_col] >= event_start) & (df[time_col] <= event_end)

    rows: list[dict[str, object]] = []
    for metric in use_metrics:
        base_vals = pd.to_numeric(df.loc[baseline_mask, metric], errors="coerce").dropna()
        evt_vals = pd.to_numeric(df.loc[event_mask, metric], errors="coerce").dropna()
        n_base = int(base_vals.size)
        n_evt = int(evt_vals.size)
        if n_base < min_samples_per_phase or n_evt < min_samples_per_phase:
            continue

        base_mean = float(base_vals.mean())
        evt_mean = float(evt_vals.mean())
        base_std = float(base_vals.std(ddof=1)) if n_base >= 2 else float("nan")
        evt_std = float(evt_vals.std(ddof=1)) if n_evt >= 2 else float("nan")
        delta = float(evt_mean - base_mean)

        pct_change = float("nan")
        if np.isfinite(base_mean) and abs(base_mean) > 1e-12:
            pct_change = float(delta / base_mean * 100.0)

        pooled = float("nan")
        if np.isfinite(base_std) and np.isfinite(evt_std):
            pooled = float(np.sqrt((base_std * base_std + evt_std * evt_std) / 2.0))
        cohen_d = float(delta / pooled) if np.isfinite(pooled) and pooled > 0 else float("nan")

        rows.append(
            {
                "metric": metric,
                "n_baseline": n_base,
                "baseline_mean": base_mean,
                "baseline_std": base_std,
                "n_event": n_evt,
                "event_mean": evt_mean,
                "event_std": evt_std,
                "delta": delta,
                "pct_change": pct_change,
                "cohen_d": cohen_d,
            }
        )

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows)
    out["abs_delta"] = out["delta"].abs()
    out["abs_d"] = pd.to_numeric(out["cohen_d"], errors="coerce").abs()
    out = out.sort_values(["abs_d", "abs_delta"], ascending=[False, False], ignore_index=True)
    return out


