"""Comprehensive sleep analysis module with medical-grade visualizations.

This module provides functionality for:
- Hypnogram generation (PSG-style sleep staging visualization)
- Sleep architecture analysis
- Multi-night sleep trends
- Sleep quality metrics
- Integration with SAFTE fatigue model
- Device data fusion (Garmin, Actigraph, Somfit Pro)

Design principles:
- Medical-grade visualization matching PSG standards
- Graceful handling of missing data (no crashes)
- Multi-device support with automatic data fusion
- Strict scientific accuracy

References:
- AASM Manual for Scoring of Sleep (2020)
- Berry RB, et al. The AASM Manual for the Scoring of Sleep.
- Rechtschaffen & Kales (1968). A Manual of Standardized Terminology.

Author: Dr. Diego Malpica, MD - Aerospace Medicine Specialist
National University of Colombia | Colombian Aerospace Force
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta, timezone
from enum import IntEnum
from typing import Any, Final, TypedDict

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Standard epoch duration (seconds)
_EPOCH_SECONDS: Final[int] = 30

# Sleep stage definitions (AASM standard)
class SleepStage(IntEnum):
    """Sleep stage codes following AASM standard."""

    WAKE = 0
    N1 = 1
    N2 = 2
    N3 = 3  # Deep sleep / SWS
    REM = 4
    MOVEMENT = 5
    UNSCORED = -1


# Sleep stage display names
_STAGE_NAMES: Final[dict[int, str]] = {
    SleepStage.WAKE: "Wake",
    SleepStage.N1: "N1",
    SleepStage.N2: "N2",
    SleepStage.N3: "N3 (Deep)",
    SleepStage.REM: "REM",
    SleepStage.MOVEMENT: "Movement",
    SleepStage.UNSCORED: "Unscored",
}

# Sleep stage colors for visualization
_STAGE_COLORS: Final[dict[int, str]] = {
    SleepStage.WAKE: "#E74C3C",      # Red
    SleepStage.N1: "#3498DB",        # Light blue
    SleepStage.N2: "#2980B9",        # Blue
    SleepStage.N3: "#1A5276",        # Dark blue
    SleepStage.REM: "#9B59B6",       # Purple
    SleepStage.MOVEMENT: "#F39C12",  # Orange
    SleepStage.UNSCORED: "#7F8C8D",  # Gray
}

# Normal sleep architecture ranges (adults, percentage of TST)
_NORMAL_ARCHITECTURE: Final[dict[str, tuple[float, float]]] = {
    "n1_pct": (2.0, 8.0),
    "n2_pct": (40.0, 60.0),
    "n3_pct": (10.0, 25.0),
    "rem_pct": (18.0, 28.0),
    "sleep_efficiency": (85.0, 100.0),
    "sol_minutes": (0.0, 30.0),
    "waso_minutes": (0.0, 30.0),
    "tst_hours": (6.0, 9.0),
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SleepEpoch:
    """Single sleep epoch (30-second period).

    Attributes:
        epoch_number: Sequential epoch number (1-indexed).
        timestamp: Epoch start timestamp.
        stage: Sleep stage code.
        confidence: Classification confidence (0-1).
        heart_rate: Average heart rate during epoch (optional).
        spo2: Average SpO2 during epoch (optional).
        movement: Movement intensity (optional).
        source: Data source identifier.
    """

    epoch_number: int
    timestamp: datetime
    stage: int
    confidence: float = 1.0
    heart_rate: float | None = None
    spo2: float | None = None
    movement: float | None = None
    source: str = "unknown"


@dataclass(slots=True)
class SleepArchitecture:
    """Sleep architecture metrics for a single night.

    Attributes:
        recording_date: Date of sleep (night starting).
        lights_off: Lights-off timestamp.
        lights_on: Lights-on timestamp.
        trt_minutes: Total Recording Time (minutes).
        tst_minutes: Total Sleep Time (minutes).
        sleep_efficiency: TST/TRT * 100 (%).
        sol_minutes: Sleep Onset Latency (minutes).
        rem_latency_minutes: REM Onset Latency from sleep onset (minutes).
        waso_minutes: Wake After Sleep Onset (minutes).
        n_awakenings: Number of awakenings.
        wake_minutes: Total wake time (minutes).
        n1_minutes: N1 duration (minutes).
        n2_minutes: N2 duration (minutes).
        n3_minutes: N3/SWS duration (minutes).
        rem_minutes: REM duration (minutes).
        wake_pct: Wake percentage of TRT.
        n1_pct: N1 percentage of TST.
        n2_pct: N2 percentage of TST.
        n3_pct: N3 percentage of TST.
        rem_pct: REM percentage of TST.
        sleep_cycles: Number of sleep cycles.
        fragmentation_index: Sleep fragmentation index.
        quality_score: Overall quality score (0-100).
        source: Data source identifier.
    """

    recording_date: date
    lights_off: datetime | None = None
    lights_on: datetime | None = None
    trt_minutes: float = 0.0
    tst_minutes: float = 0.0
    sleep_efficiency: float = 0.0
    sol_minutes: float = 0.0
    rem_latency_minutes: float = 0.0
    waso_minutes: float = 0.0
    n_awakenings: int = 0
    wake_minutes: float = 0.0
    n1_minutes: float = 0.0
    n2_minutes: float = 0.0
    n3_minutes: float = 0.0
    rem_minutes: float = 0.0
    wake_pct: float = 0.0
    n1_pct: float = 0.0
    n2_pct: float = 0.0
    n3_pct: float = 0.0
    rem_pct: float = 0.0
    sleep_cycles: int = 0
    fragmentation_index: float = 0.0
    quality_score: float = 0.0
    source: str = "unknown"


@dataclass(slots=True)
class SleepNight:
    """Complete sleep data for a single night.

    Attributes:
        recording_date: Date of sleep (night starting).
        epochs: List of sleep epochs.
        architecture: Computed sleep architecture.
        heart_rate_series: Heart rate time series (optional).
        spo2_series: SpO2 time series (optional).
        respiration_series: Respiration rate series (optional).
        events: List of respiratory/movement events (optional).
        hrv_by_stage: HRV metrics by sleep stage (optional).
        source: Data source identifier.
        quality_ok: Whether data quality is sufficient.
        warnings: List of quality warnings.
    """

    recording_date: date
    epochs: list[SleepEpoch] = field(default_factory=list)
    architecture: SleepArchitecture | None = None
    heart_rate_series: pd.DataFrame = field(default_factory=pd.DataFrame)
    spo2_series: pd.DataFrame = field(default_factory=pd.DataFrame)
    respiration_series: pd.DataFrame = field(default_factory=pd.DataFrame)
    events: list[dict[str, Any]] = field(default_factory=list)
    hrv_by_stage: dict[str, dict[str, float]] = field(default_factory=dict)
    source: str = "unknown"
    quality_ok: bool = True
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MultiNightSummary:
    """Summary of multiple nights of sleep data.

    Attributes:
        nights: List of SleepNight objects.
        date_range_start: First night date.
        date_range_end: Last night date.
        n_nights: Number of nights.
        avg_tst_hours: Average TST (hours).
        avg_sleep_efficiency: Average sleep efficiency (%).
        avg_n3_pct: Average deep sleep percentage.
        avg_rem_pct: Average REM percentage.
        avg_sol_minutes: Average sleep latency (minutes).
        avg_waso_minutes: Average WASO (minutes).
        tst_trend: TST trend slope.
        efficiency_trend: Efficiency trend slope.
        sleep_debt_hours: Cumulative sleep debt (hours).
        quality_score: Overall quality score (0-100).
    """

    nights: list[SleepNight] = field(default_factory=list)
    date_range_start: date | None = None
    date_range_end: date | None = None
    n_nights: int = 0
    avg_tst_hours: float = 0.0
    avg_sleep_efficiency: float = 0.0
    avg_n3_pct: float = 0.0
    avg_rem_pct: float = 0.0
    avg_sol_minutes: float = 0.0
    avg_waso_minutes: float = 0.0
    tst_trend: float = 0.0
    efficiency_trend: float = 0.0
    sleep_debt_hours: float = 0.0
    quality_score: float = 0.0


class HypnogramData(TypedDict):
    """Data structure for hypnogram visualization."""

    timestamps: list[str]
    stages: list[int]
    stage_names: list[str]
    heart_rate: list[float | None]
    spo2: list[float | None]
    epoch_duration_sec: int


# ---------------------------------------------------------------------------
# Sleep stage conversion
# ---------------------------------------------------------------------------


def convert_stage_to_aasm(stage_value: Any, source: str = "unknown") -> int:
    """Convert various sleep stage formats to AASM standard.

    Args:
        stage_value: Stage value from different sources.
        source: Data source for format detection.

    Returns:
        AASM standard stage code.
    """
    if isinstance(stage_value, int):
        if stage_value in [0, 1, 2, 3, 4, 5, -1]:
            return stage_value
        # Garmin format: deep=0, light=1, rem=2, awake=3
        if source.lower() == "garmin":
            mapping = {0: SleepStage.N3, 1: SleepStage.N2, 2: SleepStage.REM, 3: SleepStage.WAKE}
            return mapping.get(stage_value, SleepStage.UNSCORED)
        return SleepStage.UNSCORED

    if isinstance(stage_value, str):
        stage_str = stage_value.upper().strip()
        # Map common stage names
        stage_map = {
            "WAKE": SleepStage.WAKE,
            "W": SleepStage.WAKE,
            "AWAKE": SleepStage.WAKE,
            "N1": SleepStage.N1,
            "STAGE1": SleepStage.N1,
            "STAGE 1": SleepStage.N1,
            "LIGHT": SleepStage.N1,  # Simplified from consumer devices
            "N2": SleepStage.N2,
            "STAGE2": SleepStage.N2,
            "STAGE 2": SleepStage.N2,
            "N3": SleepStage.N3,
            "STAGE3": SleepStage.N3,
            "STAGE 3": SleepStage.N3,
            "STAGE4": SleepStage.N3,  # Old R&K
            "DEEP": SleepStage.N3,
            "SWS": SleepStage.N3,
            "REM": SleepStage.REM,
            "R": SleepStage.REM,
            "MOVEMENT": SleepStage.MOVEMENT,
            "MT": SleepStage.MOVEMENT,
        }
        return stage_map.get(stage_str, SleepStage.UNSCORED)

    return SleepStage.UNSCORED


# ---------------------------------------------------------------------------
# Sleep architecture computation
# ---------------------------------------------------------------------------


def compute_sleep_architecture(
    epochs: list[SleepEpoch],
    recording_date: date,
    epoch_duration_sec: int = _EPOCH_SECONDS,
) -> SleepArchitecture:
    """Compute sleep architecture metrics from epochs.

    Args:
        epochs: List of sleep epochs.
        recording_date: Date of sleep.
        epoch_duration_sec: Duration of each epoch in seconds.

    Returns:
        SleepArchitecture with computed metrics.
    """
    if not epochs:
        return SleepArchitecture(recording_date=recording_date)

    arch = SleepArchitecture(recording_date=recording_date)
    epoch_minutes = epoch_duration_sec / 60.0
    n_epochs = len(epochs)

    # Timestamps
    arch.lights_off = epochs[0].timestamp
    arch.lights_on = epochs[-1].timestamp + timedelta(seconds=epoch_duration_sec)

    # Total recording time
    arch.trt_minutes = n_epochs * epoch_minutes

    # Extract stages array
    stages = np.array([e.stage for e in epochs])

    # Count epochs by stage
    wake_epochs = np.sum(stages == SleepStage.WAKE)
    n1_epochs = np.sum(stages == SleepStage.N1)
    n2_epochs = np.sum(stages == SleepStage.N2)
    n3_epochs = np.sum(stages == SleepStage.N3)
    rem_epochs = np.sum(stages == SleepStage.REM)
    movement_epochs = np.sum(stages == SleepStage.MOVEMENT)

    # Durations
    arch.wake_minutes = wake_epochs * epoch_minutes
    arch.n1_minutes = n1_epochs * epoch_minutes
    arch.n2_minutes = n2_epochs * epoch_minutes
    arch.n3_minutes = n3_epochs * epoch_minutes
    arch.rem_minutes = rem_epochs * epoch_minutes

    # Total sleep time (all non-wake epochs)
    sleep_epochs = n1_epochs + n2_epochs + n3_epochs + rem_epochs
    arch.tst_minutes = sleep_epochs * epoch_minutes

    # Sleep efficiency
    if arch.trt_minutes > 0:
        arch.sleep_efficiency = (arch.tst_minutes / arch.trt_minutes) * 100

    # Stage percentages (of TST)
    if arch.tst_minutes > 0:
        arch.n1_pct = (arch.n1_minutes / arch.tst_minutes) * 100
        arch.n2_pct = (arch.n2_minutes / arch.tst_minutes) * 100
        arch.n3_pct = (arch.n3_minutes / arch.tst_minutes) * 100
        arch.rem_pct = (arch.rem_minutes / arch.tst_minutes) * 100

    # Wake percentage (of TRT)
    if arch.trt_minutes > 0:
        arch.wake_pct = (arch.wake_minutes / arch.trt_minutes) * 100

    # Sleep onset latency (time to first sleep epoch)
    sleep_mask = stages > 0  # Any non-wake stage
    first_sleep_idx = np.argmax(sleep_mask) if sleep_mask.any() else n_epochs
    arch.sol_minutes = first_sleep_idx * epoch_minutes

    # REM latency (from sleep onset to first REM)
    if first_sleep_idx < n_epochs:
        rem_mask = stages[first_sleep_idx:] == SleepStage.REM
        first_rem_idx = np.argmax(rem_mask) if rem_mask.any() else (n_epochs - first_sleep_idx)
        arch.rem_latency_minutes = first_rem_idx * epoch_minutes
    else:
        arch.rem_latency_minutes = 0.0

    # WASO (wake time after sleep onset)
    if first_sleep_idx < n_epochs:
        # Find last sleep epoch
        last_sleep_idx = n_epochs - 1 - np.argmax(sleep_mask[::-1])
        if last_sleep_idx > first_sleep_idx:
            middle_stages = stages[first_sleep_idx:last_sleep_idx + 1]
            waso_epochs = np.sum(middle_stages == SleepStage.WAKE)
            arch.waso_minutes = waso_epochs * epoch_minutes

    # Number of awakenings (transitions from sleep to wake)
    n_awakenings = 0
    for i in range(first_sleep_idx, len(stages) - 1):
        if stages[i] > 0 and stages[i + 1] == SleepStage.WAKE:
            n_awakenings += 1
    arch.n_awakenings = n_awakenings

    # Sleep cycles (NREM-REM transitions)
    in_nrem = False
    cycles = 0
    for stage in stages[first_sleep_idx:]:
        if stage in [SleepStage.N1, SleepStage.N2, SleepStage.N3]:
            in_nrem = True
        elif stage == SleepStage.REM and in_nrem:
            cycles += 1
            in_nrem = False
    arch.sleep_cycles = cycles

    # Fragmentation index (transitions per hour)
    transitions = np.sum(np.diff(stages) != 0)
    hours = arch.trt_minutes / 60
    arch.fragmentation_index = transitions / hours if hours > 0 else 0.0

    # Quality score (0-100)
    arch.quality_score = _compute_quality_score(arch)

    # Source
    if epochs:
        arch.source = epochs[0].source

    return arch


def _compute_quality_score(arch: SleepArchitecture) -> float:
    """Compute overall sleep quality score.

    Based on multiple sleep metrics weighted by clinical importance.

    Args:
        arch: Sleep architecture metrics.

    Returns:
        Quality score (0-100).
    """
    score = 100.0

    # Sleep efficiency (weight: 25)
    if arch.sleep_efficiency < 85:
        score -= min(25, (85 - arch.sleep_efficiency) * 1.5)

    # Sleep duration (weight: 20)
    tst_hours = arch.tst_minutes / 60
    if tst_hours < 6:
        score -= min(20, (6 - tst_hours) * 5)
    elif tst_hours > 9:
        score -= min(10, (tst_hours - 9) * 3)

    # Deep sleep percentage (weight: 15)
    if arch.n3_pct < 10:
        score -= min(15, (10 - arch.n3_pct) * 1.5)

    # REM percentage (weight: 15)
    if arch.rem_pct < 15:
        score -= min(15, (15 - arch.rem_pct) * 1.0)

    # Sleep latency (weight: 10)
    if arch.sol_minutes > 30:
        score -= min(10, (arch.sol_minutes - 30) * 0.3)

    # WASO (weight: 10)
    if arch.waso_minutes > 30:
        score -= min(10, (arch.waso_minutes - 30) * 0.3)

    # Awakenings (weight: 5)
    if arch.n_awakenings > 3:
        score -= min(5, (arch.n_awakenings - 3) * 1.0)

    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# Hypnogram generation
# ---------------------------------------------------------------------------


def generate_hypnogram_data(night: SleepNight) -> HypnogramData:
    """Generate hypnogram data for visualization.

    Args:
        night: SleepNight with epoch data.

    Returns:
        HypnogramData for visualization.
    """
    if not night.epochs:
        return HypnogramData(
            timestamps=[],
            stages=[],
            stage_names=[],
            heart_rate=[],
            spo2=[],
            epoch_duration_sec=_EPOCH_SECONDS,
        )

    timestamps = [e.timestamp.isoformat() for e in night.epochs]
    stages = [e.stage for e in night.epochs]
    stage_names = [_STAGE_NAMES.get(e.stage, "Unknown") for e in night.epochs]
    heart_rate = [e.heart_rate for e in night.epochs]
    spo2 = [e.spo2 for e in night.epochs]

    return HypnogramData(
        timestamps=timestamps,
        stages=stages,
        stage_names=stage_names,
        heart_rate=heart_rate,
        spo2=spo2,
        epoch_duration_sec=_EPOCH_SECONDS,
    )


def build_hypnogram_echarts_option(
    hypnogram_data: HypnogramData,
    title: str = "Hypnogram",
    show_hr: bool = True,
    show_spo2: bool = True,
) -> dict[str, Any]:
    """Build ECharts option for hypnogram visualization.

    Creates a medical-grade PSG-style hypnogram with optional
    heart rate and SpO2 overlays.

    Args:
        hypnogram_data: Hypnogram data structure.
        title: Chart title.
        show_hr: Show heart rate subplot.
        show_spo2: Show SpO2 subplot.

    Returns:
        ECharts option dictionary.
    """
    if not hypnogram_data["timestamps"]:
        return {"title": {"text": "No sleep data available"}}

    # Calculate grid layout based on subplots
    grids = []
    y_axes = []
    series_list = []

    # Main hypnogram grid (larger)
    grid_idx = 0
    grids.append({
        "left": "10%",
        "right": "5%",
        "top": "10%",
        "height": "40%",
    })

    # Stage Y-axis (inverted for traditional PSG view)
    y_axes.append({
        "type": "category",
        "data": ["Wake", "REM", "N1", "N2", "N3"],
        "inverse": False,
        "gridIndex": grid_idx,
        "axisLabel": {"fontWeight": "bold"},
    })

    # Map stages to Y positions (Wake at top, N3 at bottom)
    stage_y_map = {
        SleepStage.WAKE: "Wake",
        SleepStage.REM: "REM",
        SleepStage.N1: "N1",
        SleepStage.N2: "N2",
        SleepStage.N3: "N3",
        SleepStage.MOVEMENT: "Wake",
        SleepStage.UNSCORED: "Wake",
    }

    # Create step data for hypnogram
    hypnogram_series_data = []
    for i, (ts, stage) in enumerate(zip(hypnogram_data["timestamps"], hypnogram_data["stages"], strict=False)):
        y_val = stage_y_map.get(stage, "Wake")
        color = _STAGE_COLORS.get(stage, "#7F8C8D")
        hypnogram_series_data.append({
            "value": [ts, y_val],
            "itemStyle": {"color": color},
        })

    series_list.append({
        "name": "Sleep Stage",
        "type": "line",
        "step": "end",
        "xAxisIndex": 0,
        "yAxisIndex": 0,
        "data": hypnogram_series_data,
        "lineStyle": {"width": 2},
        "areaStyle": {"opacity": 0.3},
        "showSymbol": False,
    })

    # Heart rate subplot
    hr_data = hypnogram_data.get("heart_rate", [])
    if show_hr and hr_data and any(v is not None for v in hr_data):
        grid_idx += 1
        grids.append({
            "left": "10%",
            "right": "5%",
            "top": "55%",
            "height": "15%",
        })
        y_axes.append({
            "type": "value",
            "name": "HR (bpm)",
            "min": 40,
            "max": 120,
            "gridIndex": grid_idx,
            "nameLocation": "middle",
            "nameGap": 30,
        })

        hr_series_data = [
            [ts, hr] for ts, hr in zip(hypnogram_data["timestamps"], hr_data, strict=False)
            if hr is not None
        ]
        series_list.append({
            "name": "Heart Rate",
            "type": "line",
            "xAxisIndex": grid_idx,
            "yAxisIndex": grid_idx,
            "data": hr_series_data,
            "lineStyle": {"color": "#E74C3C", "width": 1},
            "showSymbol": False,
            "smooth": True,
        })

    # SpO2 subplot
    spo2_data = hypnogram_data.get("spo2", [])
    if show_spo2 and spo2_data and any(v is not None for v in spo2_data):
        grid_idx += 1
        grids.append({
            "left": "10%",
            "right": "5%",
            "top": "75%",
            "height": "15%",
        })
        y_axes.append({
            "type": "value",
            "name": "SpO2 (%)",
            "min": 80,
            "max": 100,
            "gridIndex": grid_idx,
            "nameLocation": "middle",
            "nameGap": 30,
        })

        spo2_series_data = [
            [ts, spo2] for ts, spo2 in zip(hypnogram_data["timestamps"], spo2_data, strict=False)
            if spo2 is not None
        ]
        series_list.append({
            "name": "SpO2",
            "type": "line",
            "xAxisIndex": grid_idx,
            "yAxisIndex": grid_idx,
            "data": spo2_series_data,
            "lineStyle": {"color": "#3498DB", "width": 1},
            "showSymbol": False,
            "smooth": True,
        })

    # Build x-axes (one per grid)
    x_axes = []
    for i in range(len(grids)):
        x_axes.append({
            "type": "time",
            "gridIndex": i,
            "axisLabel": {"show": i == len(grids) - 1},  # Only show on bottom
            "axisTick": {"show": i == len(grids) - 1},
        })

    option = {
        "title": {
            "text": title,
            "left": "center",
            "textStyle": {"fontSize": 16, "fontWeight": "bold"},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
        },
        "legend": {
            "data": ["Sleep Stage", "Heart Rate", "SpO2"],
            "bottom": 0,
        },
        "grid": grids,
        "xAxis": x_axes,
        "yAxis": y_axes,
        "series": series_list,
        "dataZoom": [
            {"type": "inside", "xAxisIndex": list(range(len(grids)))},
            {"type": "slider", "xAxisIndex": list(range(len(grids))), "bottom": 30},
        ],
    }

    return option


# ---------------------------------------------------------------------------
# Multi-night analysis
# ---------------------------------------------------------------------------


def compute_multi_night_summary(nights: list[SleepNight]) -> MultiNightSummary:
    """Compute summary statistics across multiple nights.

    Args:
        nights: List of SleepNight objects.

    Returns:
        MultiNightSummary with aggregated statistics.
    """
    summary = MultiNightSummary()

    if not nights:
        return summary

    # Filter nights with architecture data
    valid_nights = [n for n in nights if n.architecture and n.architecture.tst_minutes > 0]

    if not valid_nights:
        summary.nights = nights
        summary.n_nights = len(nights)
        return summary

    summary.nights = valid_nights
    summary.n_nights = len(valid_nights)

    # Date range
    dates = [n.recording_date for n in valid_nights]
    summary.date_range_start = min(dates)
    summary.date_range_end = max(dates)

    # Average metrics
    tst_values = [n.architecture.tst_minutes / 60 for n in valid_nights if n.architecture]
    eff_values = [n.architecture.sleep_efficiency for n in valid_nights if n.architecture]
    n3_values = [n.architecture.n3_pct for n in valid_nights if n.architecture]
    rem_values = [n.architecture.rem_pct for n in valid_nights if n.architecture]
    sol_values = [n.architecture.sol_minutes for n in valid_nights if n.architecture]
    waso_values = [n.architecture.waso_minutes for n in valid_nights if n.architecture]

    if tst_values:
        summary.avg_tst_hours = float(np.mean(tst_values))
    if eff_values:
        summary.avg_sleep_efficiency = float(np.mean(eff_values))
    if n3_values:
        summary.avg_n3_pct = float(np.mean(n3_values))
    if rem_values:
        summary.avg_rem_pct = float(np.mean(rem_values))
    if sol_values:
        summary.avg_sol_minutes = float(np.mean(sol_values))
    if waso_values:
        summary.avg_waso_minutes = float(np.mean(waso_values))

    # Trends (linear regression)
    if len(tst_values) >= 3:
        x = np.arange(len(tst_values))
        slope, _ = np.polyfit(x, tst_values, 1)
        summary.tst_trend = float(slope)

    if len(eff_values) >= 3:
        x = np.arange(len(eff_values))
        slope, _ = np.polyfit(x, eff_values, 1)
        summary.efficiency_trend = float(slope)

    # Sleep debt (deviation from 8-hour target)
    target_hours = 8.0
    deficit_hours = [max(0, target_hours - tst) for tst in tst_values]
    summary.sleep_debt_hours = float(sum(deficit_hours))

    # Overall quality score
    quality_scores = [n.architecture.quality_score for n in valid_nights if n.architecture]
    if quality_scores:
        summary.quality_score = float(np.mean(quality_scores))

    return summary


# ---------------------------------------------------------------------------
# Device data fusion
# ---------------------------------------------------------------------------


def create_sleep_night_from_garmin(
    garmin_sleep_data: dict[str, Any],
    recording_date: date,
) -> SleepNight:
    """Create SleepNight from Garmin sleep data.

    Args:
        garmin_sleep_data: Garmin sleep data dictionary.
        recording_date: Date of sleep.

    Returns:
        SleepNight with converted data.
    """
    night = SleepNight(recording_date=recording_date, source="garmin")
    warnings: list[str] = []

    # Extract sleep levels (stages)
    sleep_levels = garmin_sleep_data.get("sleepLevels", [])
    if not sleep_levels:
        sleep_levels = garmin_sleep_data.get("levels", [])

    if sleep_levels:
        epochs: list[SleepEpoch] = []
        for i, level in enumerate(sleep_levels):
            # Parse timestamp
            ts_str = level.get("startGMT") or level.get("timestamp") or level.get("start")
            if ts_str:
                try:
                    if isinstance(ts_str, int):
                        ts = datetime.fromtimestamp(ts_str / 1000, tz=timezone.utc)
                    else:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except Exception:
                    ts = datetime.now(tz=timezone.utc)
            else:
                ts = datetime.now(tz=timezone.utc)

            # Convert stage (Garmin: deep=0, light=1, rem=2, awake=3)
            garmin_stage = level.get("level") or level.get("stage", 0)
            if isinstance(garmin_stage, str):
                garmin_stage = {"deep": 0, "light": 1, "rem": 2, "awake": 3}.get(garmin_stage.lower(), 0)

            aasm_stage = convert_stage_to_aasm(garmin_stage, source="garmin")

            epochs.append(SleepEpoch(
                epoch_number=i + 1,
                timestamp=ts,
                stage=aasm_stage,
                source="garmin",
            ))

        night.epochs = epochs

        # Compute architecture
        if epochs:
            night.architecture = compute_sleep_architecture(epochs, recording_date)
    else:
        warnings.append("No sleep staging data found in Garmin export")

    # Extract summary metrics if no staging
    if not night.epochs and garmin_sleep_data:
        tst_seconds = garmin_sleep_data.get("sleepTimeSeconds", 0)
        deep_seconds = garmin_sleep_data.get("deepSleepSeconds", 0)
        light_seconds = garmin_sleep_data.get("lightSleepSeconds", 0)
        rem_seconds = garmin_sleep_data.get("remSleepSeconds", 0)
        awake_seconds = garmin_sleep_data.get("awakeSleepSeconds", 0)

        if tst_seconds > 0:
            arch = SleepArchitecture(
                recording_date=recording_date,
                tst_minutes=tst_seconds / 60,
                n3_minutes=deep_seconds / 60,
                n2_minutes=light_seconds / 60,  # Garmin "light" maps to N2
                rem_minutes=rem_seconds / 60,
                wake_minutes=awake_seconds / 60,
                source="garmin_summary",
            )
            # Compute percentages
            if arch.tst_minutes > 0:
                arch.n3_pct = (arch.n3_minutes / arch.tst_minutes) * 100
                arch.n2_pct = (arch.n2_minutes / arch.tst_minutes) * 100
                arch.rem_pct = (arch.rem_minutes / arch.tst_minutes) * 100
            arch.quality_score = garmin_sleep_data.get("sleepScores", {}).get("overall", {}).get("value", 0)
            night.architecture = arch

    night.warnings = warnings
    night.quality_ok = len(warnings) == 0 or night.architecture is not None

    return night


def create_sleep_night_from_actigraph(
    actigraph_data: Any,
    recording_date: date,
) -> SleepNight:
    """Create SleepNight from ActiGraph data.

    Args:
        actigraph_data: ActigraphData object.
        recording_date: Date of sleep.

    Returns:
        SleepNight with converted data.
    """
    night = SleepNight(recording_date=recording_date, source="actigraph")
    warnings: list[str] = []

    # Check for sleep/wake data
    sleep_wake_df = getattr(actigraph_data, "sleep_wake", None)
    if sleep_wake_df is not None and not sleep_wake_df.empty:
        epochs: list[SleepEpoch] = []

        for i, row in sleep_wake_df.iterrows():
            ts = row.get("timestamp", datetime.now(tz=timezone.utc))
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)

            # Actigraphy: binary sleep/wake only
            stage = SleepStage.WAKE if row.get("sleep_wake", 1) == 1 else SleepStage.N2

            hr = row.get("heart_rate")

            epochs.append(SleepEpoch(
                epoch_number=i + 1,
                timestamp=ts,
                stage=stage,
                heart_rate=float(hr) if hr and not np.isnan(hr) else None,
                source="actigraph",
            ))

        night.epochs = epochs

        if epochs:
            night.architecture = compute_sleep_architecture(epochs, recording_date)
    else:
        warnings.append("No sleep/wake classification in ActiGraph data")

    # Extract heart rate if available
    hr_df = getattr(actigraph_data, "heart_rate", None)
    if hr_df is not None and not hr_df.empty:
        night.heart_rate_series = hr_df.copy()

    night.warnings = warnings
    night.quality_ok = len(warnings) == 0 or night.architecture is not None

    return night


def create_sleep_night_from_somfit(
    somfit_data: Any,
    recording_date: date,
) -> SleepNight:
    """Create SleepNight from Somfit Pro data.

    Args:
        somfit_data: SomfitData object.
        recording_date: Date of sleep.

    Returns:
        SleepNight with converted data.
    """
    night = SleepNight(recording_date=recording_date, source="somfit")
    warnings: list[str] = []

    # Get staging data
    staging = getattr(somfit_data, "staging", None)
    if staging and hasattr(staging, "epochs") and not staging.epochs.empty:
        epochs: list[SleepEpoch] = []
        start_time = getattr(somfit_data.metadata, "start_time", None)
        if start_time is None:
            start_time = datetime.now(tz=timezone.utc)

        for i, row in staging.epochs.iterrows():
            epoch_start = row.get("start_seconds", i * 30)
            ts = start_time + timedelta(seconds=epoch_start)

            stage_code = row.get("stage", SleepStage.UNSCORED)
            if isinstance(stage_code, str):
                stage_code = convert_stage_to_aasm(stage_code, source="somfit")

            epochs.append(SleepEpoch(
                epoch_number=i + 1,
                timestamp=ts,
                stage=stage_code,
                source="somfit",
            ))

        night.epochs = epochs

        if epochs:
            night.architecture = compute_sleep_architecture(epochs, recording_date)
    else:
        warnings.append("No sleep staging data in Somfit export")

    # Extract physiological data
    hr_df = getattr(somfit_data, "heart_rate", None)
    if hr_df is not None and not hr_df.empty:
        night.heart_rate_series = hr_df.copy()

    spo2_df = getattr(somfit_data, "spo2", None)
    if spo2_df is not None and not spo2_df.empty:
        night.spo2_series = spo2_df.copy()

    # Respiratory events
    respiratory = getattr(somfit_data, "respiratory", None)
    if respiratory and hasattr(respiratory, "ahi"):
        night.events.append({
            "type": "respiratory_summary",
            "ahi": respiratory.ahi,
            "odi": respiratory.odi,
            "apnea_count": respiratory.apnea_count,
            "hypopnea_count": respiratory.hypopnea_count,
            "min_spo2": respiratory.min_spo2,
        })

    night.warnings = warnings
    night.quality_ok = len(warnings) == 0 or night.architecture is not None

    return night


# ---------------------------------------------------------------------------
# Sleep quality assessment charts
# ---------------------------------------------------------------------------


def build_sleep_architecture_gauge(arch: SleepArchitecture) -> dict[str, Any]:
    """Build sleep architecture gauge visualization.

    Args:
        arch: Sleep architecture metrics.

    Returns:
        ECharts option for gauge chart.
    """
    return {
        "title": {"text": "Sleep Quality Score", "left": "center"},
        "series": [
            {
                "type": "gauge",
                "startAngle": 180,
                "endAngle": 0,
                "min": 0,
                "max": 100,
                "splitNumber": 5,
                "itemStyle": {"color": "#58D9F9"},
                "progress": {"show": True, "width": 18},
                "pointer": {"show": True},
                "axisLine": {
                    "lineStyle": {"width": 18},
                },
                "axisTick": {"show": False},
                "splitLine": {"length": 15, "lineStyle": {"width": 2}},
                "axisLabel": {"distance": 25, "fontSize": 12},
                "detail": {
                    "fontSize": 30,
                    "offsetCenter": [0, "40%"],
                    "formatter": "{value}",
                },
                "data": [{"value": round(arch.quality_score, 1), "name": "Quality"}],
            }
        ],
    }


def build_sleep_stages_pie(arch: SleepArchitecture) -> dict[str, Any]:
    """Build sleep stages pie chart.

    Args:
        arch: Sleep architecture metrics.

    Returns:
        ECharts option for pie chart.
    """
    data = [
        {"value": arch.wake_minutes, "name": "Wake", "itemStyle": {"color": _STAGE_COLORS[SleepStage.WAKE]}},
        {"value": arch.n1_minutes, "name": "N1", "itemStyle": {"color": _STAGE_COLORS[SleepStage.N1]}},
        {"value": arch.n2_minutes, "name": "N2", "itemStyle": {"color": _STAGE_COLORS[SleepStage.N2]}},
        {"value": arch.n3_minutes, "name": "N3 (Deep)", "itemStyle": {"color": _STAGE_COLORS[SleepStage.N3]}},
        {"value": arch.rem_minutes, "name": "REM", "itemStyle": {"color": _STAGE_COLORS[SleepStage.REM]}},
    ]

    # Filter out zero values
    data = [d for d in data if d["value"] > 0]

    return {
        "title": {"text": "Sleep Stage Distribution", "left": "center"},
        "tooltip": {
            "trigger": "item",
            "formatter": "{b}: {c} min ({d}%)",
        },
        "legend": {
            "orient": "vertical",
            "left": "left",
        },
        "series": [
            {
                "type": "pie",
                "radius": ["40%", "70%"],
                "avoidLabelOverlap": False,
                "itemStyle": {"borderRadius": 10, "borderWidth": 2},
                "label": {"show": True, "formatter": "{b}: {d}%"},
                "data": data,
            }
        ],
    }


def build_sleep_metrics_radar(arch: SleepArchitecture) -> dict[str, Any]:
    """Build sleep metrics radar chart.

    Args:
        arch: Sleep architecture metrics.

    Returns:
        ECharts option for radar chart.
    """
    # Normalize metrics to 0-100 scale
    tst_norm = min(100, (arch.tst_minutes / 60 / 8) * 100)  # 8h = 100%
    eff_norm = arch.sleep_efficiency
    deep_norm = min(100, arch.n3_pct * 5)  # 20% = 100
    rem_norm = min(100, arch.rem_pct * 4)  # 25% = 100
    sol_norm = max(0, 100 - arch.sol_minutes * 2)  # 0 min = 100, 50 min = 0
    waso_norm = max(0, 100 - arch.waso_minutes * 2)

    return {
        "title": {"text": "Sleep Quality Radar", "left": "center"},
        "radar": {
            "indicator": [
                {"name": "Duration", "max": 100},
                {"name": "Efficiency", "max": 100},
                {"name": "Deep Sleep", "max": 100},
                {"name": "REM Sleep", "max": 100},
                {"name": "Fast Onset", "max": 100},
                {"name": "Continuity", "max": 100},
            ],
        },
        "series": [
            {
                "type": "radar",
                "data": [
                    {
                        "value": [tst_norm, eff_norm, deep_norm, rem_norm, sol_norm, waso_norm],
                        "name": "Sleep Quality",
                        "areaStyle": {"opacity": 0.3},
                    }
                ],
            }
        ],
    }


def build_multi_night_trend_chart(
    summary: MultiNightSummary,
    metric: str = "tst_hours",
) -> dict[str, Any]:
    """Build multi-night trend line chart.

    Args:
        summary: MultiNightSummary with nights data.
        metric: Metric to plot (tst_hours, sleep_efficiency, n3_pct, rem_pct).

    Returns:
        ECharts option for line chart.
    """
    if not summary.nights:
        return {"title": {"text": "No data available"}}

    # Extract metric values
    dates = []
    values = []

    for night in summary.nights:
        if night.architecture:
            dates.append(night.recording_date.isoformat())
            if metric == "tst_hours":
                values.append(night.architecture.tst_minutes / 60)
            elif metric == "sleep_efficiency":
                values.append(night.architecture.sleep_efficiency)
            elif metric == "n3_pct":
                values.append(night.architecture.n3_pct)
            elif metric == "rem_pct":
                values.append(night.architecture.rem_pct)
            elif metric == "quality_score":
                values.append(night.architecture.quality_score)
            else:
                values.append(getattr(night.architecture, metric, 0))

    metric_labels = {
        "tst_hours": "Total Sleep Time (hours)",
        "sleep_efficiency": "Sleep Efficiency (%)",
        "n3_pct": "Deep Sleep (%)",
        "rem_pct": "REM Sleep (%)",
        "quality_score": "Quality Score",
    }

    return {
        "title": {"text": f"{metric_labels.get(metric, metric)} Trend", "left": "center"},
        "tooltip": {"trigger": "axis"},
        "xAxis": {
            "type": "category",
            "data": dates,
            "axisLabel": {"rotate": 45},
        },
        "yAxis": {"type": "value", "name": metric_labels.get(metric, metric)},
        "series": [
            {
                "type": "line",
                "data": values,
                "smooth": True,
                "markLine": {
                    "data": [{"type": "average", "name": "Average"}],
                },
                "areaStyle": {"opacity": 0.2},
            }
        ],
    }


# ---------------------------------------------------------------------------
# SAFTE integration helpers
# ---------------------------------------------------------------------------


def prepare_safte_sleep_schedule(
    nights: list[SleepNight],
) -> list[dict[str, Any]]:
    """Prepare sleep schedule for SAFTE model input.

    Args:
        nights: List of SleepNight objects.

    Returns:
        List of sleep schedule dictionaries for SAFTE.
    """
    schedule: list[dict[str, Any]] = []

    for night in nights:
        if not night.architecture:
            continue

        arch = night.architecture

        schedule.append({
            "date": night.recording_date.isoformat(),
            "bedtime_hour": arch.lights_off.hour if arch.lights_off else 23,
            "waketime_hour": arch.lights_on.hour if arch.lights_on else 7,
            "duration_hours": arch.tst_minutes / 60,
            "quality": arch.quality_score / 100,  # Normalize to 0-1
            "deep_pct": arch.n3_pct,
            "rem_pct": arch.rem_pct,
        })

    return schedule


def compute_sleep_debt_for_safte(
    nights: list[SleepNight],
    target_hours: float = 8.0,
) -> float:
    """Compute cumulative sleep debt for SAFTE model.

    Args:
        nights: List of SleepNight objects (recent to oldest).
        target_hours: Target sleep hours per night.

    Returns:
        Cumulative sleep debt in hours.
    """
    debt = 0.0

    for night in nights:
        if night.architecture:
            actual_hours = night.architecture.tst_minutes / 60
            deficit = max(0, target_hours - actual_hours)
            debt += deficit

    return debt

