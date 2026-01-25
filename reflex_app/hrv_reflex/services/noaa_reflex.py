# Author: Dr Diego Malpica MD

"""NOAA ingestion helpers for Reflex v2 (Phase 1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import numpy as np
import pandas as pd

from .echarts_builders import build_time_series_chart


@dataclass(frozen=True, slots=True)
class NOAADailySeries:
    dates: list[datetime]
    values: list[Optional[float]]
    title: str
    unit: str


def get_noaa_source_keys() -> list[str]:
    """Return available NOAA dataset keys from the legacy ingestion module."""
    try:
        from app.noaa_space import NOAA_SOURCES  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "Cannot import legacy NOAA sources. Ensure PYTHONPATH points to repo root so `import app` works."
        ) from exc
    return list(NOAA_SOURCES.keys())


def fetch_noaa_bundles(
    keys: list[str],
    *,
    use_cache: bool = True,
    overall_timeout_s: float = 30.0,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Fetch NOAA bundles using the legacy ingestion module.

    Returns raw bundles as dicts (not stored directly in Reflex state).
    """
    try:
        from app.noaa_space import load_noaa_space_data  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "Cannot import legacy NOAA ingestion. Ensure PYTHONPATH points to repo root so `import app` works."
        ) from exc
    bundles, errors = load_noaa_space_data(
        keys=keys,
        use_cache=use_cache,
        overall_timeout_s=float(overall_timeout_s),
    )
    return bundles, errors


def summarize_noaa_bundle(key: str, bundle: Any) -> dict[str, Any]:
    """Create a small JSON-friendly summary for display."""
    frame = getattr(bundle, "frame", None)
    spec = getattr(bundle, "spec", None)
    title = getattr(spec, "title", key) if spec is not None else key
    value_cols = list(getattr(bundle, "value_columns", ()) or ())
    time_col = str(getattr(bundle, "time_column", "time_tag"))
    rows = 0
    start_utc = None
    end_utc = None
    if isinstance(frame, pd.DataFrame) and not frame.empty and time_col in frame.columns:
        rows = int(len(frame))
        times = pd.to_datetime(frame[time_col], utc=True, errors="coerce").dropna()
        if not times.empty:
            start_utc = str(times.min())
            end_utc = str(times.max())
    return {
        "key": key,
        "title": title,
        "rows": rows,
        "start_utc": start_utc,
        "end_utc": end_utc,
        "value_columns": value_cols,
        "time_column": time_col,
    }


def build_noaa_daily_series(
    *,
    bundle: Any,
    value_column: str,
) -> NOAADailySeries:
    frame = getattr(bundle, "frame", None)
    spec = getattr(bundle, "spec", None)
    units = getattr(bundle, "units", {}) or {}
    time_col = str(getattr(bundle, "time_column", "time_tag"))
    title = getattr(spec, "title", "NOAA") if spec is not None else "NOAA"
    unit = str(units.get(value_column, "")) if isinstance(units, dict) else ""

    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return NOAADailySeries(dates=[], values=[], title=title, unit=unit)
    if time_col not in frame.columns or value_column not in frame.columns:
        return NOAADailySeries(dates=[], values=[], title=title, unit=unit)

    df = frame[[time_col, value_column]].copy()
    df[time_col] = pd.to_datetime(df[time_col], utc=True, errors="coerce")
    df[value_column] = pd.to_numeric(df[value_column], errors="coerce")
    df = df.dropna(subset=[time_col]).set_index(time_col)
    if df.empty:
        return NOAADailySeries(dates=[], values=[], title=title, unit=unit)

    daily = df[value_column].resample("D").mean().dropna()
    dates = [d.to_pydatetime() for d in daily.index.to_pydatetime()]
    values: list[Optional[float]] = [
        None if not np.isfinite(v) else float(v) for v in daily.to_numpy(dtype=float)
    ]
    return NOAADailySeries(dates=dates, values=values, title=title, unit=unit)


def build_noaa_chart_option(
    *,
    series: NOAADailySeries,
    value_column: str,
) -> dict[str, Any]:
    return build_time_series_chart(
        series.dates,
        series.values,
        metric_label=f"{series.title} — {value_column}",
        unit=series.unit,
        subtitle="Daily mean with 7-day EWMA and 10–90 percentile reference band. Source: NOAA SWPC JSON.",
    )

