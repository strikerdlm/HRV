"""Utilities for synchronizing space weather predictors to HRV timelines."""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
import pandas as pd


def _prepare_reference_series(reference_times: Sequence[object]) -> pd.Series:
    """Convert input timestamps to a pandas Series of UTC timestamps."""
    if isinstance(reference_times, pd.Series):
        raw = reference_times.copy()
    else:
        raw = pd.Series(reference_times)
    return pd.to_datetime(raw, errors="coerce", utc=True)


def _prepare_predictor_series(
    predictor_df: pd.DataFrame,
    *,
    predictor_time_col: str,
    predictor_value_col: str,
    lag_hours: int,
) -> pd.Series:
    """Return a sorted Series indexed by predictor timestamps with optional lag."""
    predictor = predictor_df[[predictor_time_col, predictor_value_col]].copy()
    predictor[predictor_time_col] = pd.to_datetime(
        predictor[predictor_time_col], errors="coerce", utc=True
    )
    predictor[predictor_value_col] = pd.to_numeric(
        predictor[predictor_value_col], errors="coerce"
    )
    predictor = predictor.dropna(subset=[predictor_time_col, predictor_value_col])
    if predictor.empty:
        return pd.Series(dtype=float)
    if lag_hours:
        predictor[predictor_time_col] = predictor[predictor_time_col] + pd.to_timedelta(
            int(lag_hours), unit="h"
        )
    series = pd.Series(
        predictor[predictor_value_col].to_numpy(dtype=float),
        index=pd.DatetimeIndex(predictor[predictor_time_col]),
        dtype=float,
        name=predictor_value_col,
    )
    series = series[~series.index.duplicated(keep="last")].sort_index()
    return series


def align_space_weather_series(
    reference_times: Sequence[object],
    predictor_df: pd.DataFrame,
    *,
    predictor_time_col: str,
    predictor_value_col: str,
    lag_hours: int = 0,
    max_gap_minutes: int = 90,
    interpolation: str = "time",
) -> pd.Series:
    """
    Align a predictor column to an HRV reference timeline with identical timestamps.

    Parameters
    ----------
    reference_times : Sequence[object]
        Collection of HRV timestamps (string, datetime, pandas Series, etc.).
    predictor_df : pd.DataFrame
        DataFrame containing the predictor time/value columns.
    predictor_time_col : str
        Name of the datetime column in predictor_df.
    predictor_value_col : str
        Name of the numeric predictor column.
    lag_hours : int, optional
        Shift (in hours) applied to the predictor before alignment.
    max_gap_minutes : int, optional
        Maximum tolerated gap between the predictor sample and HRV timestamp.
        Values beyond this threshold are treated as missing.
    interpolation : str, optional
        Interpolation method passed to pandas (`"time"` or `"nearest"`).

    Returns
    -------
    pd.Series
        Series indexed by the valid HRV timestamps (UTC) with predictor values.
    """
    if max_gap_minutes < 0:
        raise ValueError("max_gap_minutes must be non-negative.")
    reference_series = _prepare_reference_series(reference_times)
    valid_mask = reference_series.notna()
    ref_valid = reference_series[valid_mask]
    if ref_valid.empty:
        return pd.Series(dtype=float)
    ref_index = pd.DatetimeIndex(ref_valid.to_list())
    predictor_series = _prepare_predictor_series(
        predictor_df,
        predictor_time_col=predictor_time_col,
        predictor_value_col=predictor_value_col,
        lag_hours=lag_hours,
    )
    if predictor_series.empty:
        return pd.Series(dtype=float)
    unique_ref = pd.DatetimeIndex(sorted(set(ref_index)))
    if unique_ref.empty:
        return pd.Series(dtype=float)
    union_index = predictor_series.index.union(unique_ref)
    interpolated = predictor_series.reindex(union_index)
    if interpolation == "time":
        interpolated = interpolated.interpolate(method="time", limit_direction="both")
    elif interpolation == "nearest":
        interpolated = interpolated.interpolate(method="nearest", limit_direction="both")
    else:
        raise ValueError(f"Unsupported interpolation method: {interpolation}")
    aligned = interpolated.reindex(ref_index)
    min_time = predictor_series.index.min()
    max_time = predictor_series.index.max()
    outside_range = (ref_index < min_time) | (ref_index > max_time)
    tolerance = pd.Timedelta(minutes=max_gap_minutes)
    if max_gap_minutes == 0:
        allowed_mask = ref_index.isin(predictor_series.index)
    else:
        nearest_positions = predictor_series.index.get_indexer(
            ref_index, method="nearest"
        )
        diffs: list[pd.Timedelta] = []
        for pos, ref_time in zip(nearest_positions, ref_index):
            if pos == -1:
                diffs.append(pd.Timedelta.max)
            else:
                diffs.append(abs(ref_time - predictor_series.index[pos]))
        allowed_mask = np.array([delta <= tolerance for delta in diffs])
    combined_mask = (~outside_range) & allowed_mask
    aligned = aligned.where(combined_mask)
    aligned.name = predictor_value_col
    return aligned


def align_space_weather_columns(
    reference_times: Sequence[object],
    predictor_df: pd.DataFrame,
    *,
    predictor_time_col: str,
    value_columns: Iterable[str],
    lag_hours: int = 0,
    max_gap_minutes: int = 90,
    interpolation: str = "time",
) -> pd.DataFrame:
    """
    Align multiple predictor columns to the HRV reference timeline.

    Returns
    -------
    pd.DataFrame
        DataFrame indexed by HRV timestamps with aligned predictor columns.
    """
    frames: list[pd.Series] = []
    for column in value_columns:
        if column not in predictor_df.columns:
            continue
        aligned = align_space_weather_series(
            reference_times,
            predictor_df[[predictor_time_col, column]],
            predictor_time_col=predictor_time_col,
            predictor_value_col=column,
            lag_hours=lag_hours,
            max_gap_minutes=max_gap_minutes,
            interpolation=interpolation,
        )
        if aligned.empty:
            continue
        aligned.name = column
        frames.append(aligned)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=1)
