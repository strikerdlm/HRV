"""Unit tests for the space weather ↔ HRV alignment helpers."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.app import _corr_table
from app.space_weather_alignment import (
    align_space_weather_series,
    align_space_weather_columns,
)


def _ts(hours: int) -> datetime:
    """Convenience helper to build UTC timestamps."""
    return datetime(2025, 1, 1, hours, 0, 0, tzinfo=timezone.utc)


def test_align_space_weather_series_interpolates_linearly() -> None:
    """Interpolated predictor values should align to each HRV timestamp."""
    reference_times = pd.Series([_ts(0), _ts(1), _ts(2)])
    predictor_df = pd.DataFrame(
        {
            "timestamp": [_ts(0), _ts(2)],
            "value": [10.0, 30.0],
        }
    )
    aligned = align_space_weather_series(
        reference_times,
        predictor_df,
        predictor_time_col="timestamp",
        predictor_value_col="value",
        max_gap_minutes=180,
    )
    assert list(aligned.index) == list(reference_times)
    assert aligned.iloc[0] == 10.0
    assert aligned.iloc[2] == 30.0
    assert aligned.iloc[1] == 20.0  # linear interpolation midway


def test_align_space_weather_series_respects_max_gap() -> None:
    """Values outside the tolerance window are flagged as missing."""
    reference_times = pd.Series([_ts(0), _ts(5)])
    predictor_df = pd.DataFrame(
        {
            "timestamp": [_ts(0)],
            "value": [5.0],
        }
    )
    aligned = align_space_weather_series(
        reference_times,
        predictor_df,
        predictor_time_col="timestamp",
        predictor_value_col="value",
        max_gap_minutes=60,
    )
    assert aligned.iloc[0] == 5.0
    assert pd.isna(aligned.iloc[1])


def test_align_space_weather_columns_returns_multiple_series() -> None:
    """Aligning multiple predictor columns should retain shared timestamps."""
    reference_times = pd.Series([_ts(0), _ts(1), _ts(2)])
    predictor_df = pd.DataFrame(
        {
            "time": [_ts(0), _ts(2)],
            "a": [1.0, 3.0],
            "b": [10.0, 30.0],
        }
    )
    aligned = align_space_weather_columns(
        reference_times,
        predictor_df,
        predictor_time_col="time",
        value_columns=["a", "b"],
        max_gap_minutes=180,
    )
    assert list(aligned.columns) == ["a", "b"]
    assert aligned.iloc[1]["a"] == 2.0
    assert aligned.iloc[1]["b"] == 20.0


def test_corr_table_uses_partial_correlation_when_covariates_present() -> None:
    """Partial correlations should remove shared weather covariance."""
    rng = np.random.default_rng(42)
    base = rng.normal(loc=0.0, scale=1.0, size=500)
    predictor = base + rng.normal(scale=0.05, size=500)
    target = base + rng.normal(scale=0.05, size=500)
    weather = base + rng.normal(scale=0.02, size=500)
    df = pd.DataFrame(
        {
            "predictor": predictor,
            "target": target,
            "temp_c": weather,
        }
    )
    no_cov = _corr_table(df, "predictor", ["target"])
    with_cov = _corr_table(
        df,
        "predictor",
        ["target"],
        covariate_cols=["temp_c"],
    )
    assert no_cov.iloc[0]["pearson_r"] > 0.8
    assert abs(with_cov.iloc[0]["pearson_r"]) < 0.2
