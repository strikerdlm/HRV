"""Sleep metrics computation module.

This module provides functions to compute standard sleep metrics from
actigraphy data, sleep staging, and wearable exports. It supports integration
with GGIR (R package), YASA (Python), and consumer wearable data.

Metrics implemented:
- Total Sleep Time (TST)
- Time in Bed (TIB)
- Sleep Efficiency (SE)
- Sleep Onset Latency (SOL)
- Wake After Sleep Onset (WASO)
- Number of Awakenings
- Sleep stage percentages (N1, N2, N3/SWS, REM)

References:
- Yuan H, et al. (2024). Systematic review of actigraphy sleep staging.
  J Sleep Res. DOI: 10.1111/jsr.14143
- GGIR: Migueles JH, et al. (2019). J Meas Phys Behav. DOI: 10.1123/jmpb.2018-0063
- YASA: Vallat R, Walker MP. (2021). Elife. DOI: 10.7554/eLife.70092
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Final

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Sleep efficiency thresholds
_SE_EXCELLENT: Final[float] = 90.0
_SE_GOOD: Final[float] = 85.0
_SE_POOR: Final[float] = 75.0

# Sleep onset latency thresholds (minutes)
_SOL_NORMAL: Final[float] = 20.0
_SOL_ELEVATED: Final[float] = 30.0

# WASO thresholds (minutes)
_WASO_NORMAL: Final[float] = 20.0
_WASO_ELEVATED: Final[float] = 40.0

# Minimum TST for valid night (hours)
_MIN_TST_HOURS: Final[float] = 4.0


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SleepMetrics:
    """Container for sleep metrics from a single night.

    Attributes:
        date: Sleep date (typically the night starting date).
        tst_minutes: Total Sleep Time in minutes.
        tib_minutes: Time in Bed in minutes.
        sleep_efficiency: TST / TIB * 100 (%).
        sol_minutes: Sleep Onset Latency in minutes.
        waso_minutes: Wake After Sleep Onset in minutes.
        n_awakenings: Number of awakenings during sleep period.
        n1_minutes: N1 (light sleep stage 1) duration.
        n2_minutes: N2 (light sleep stage 2) duration.
        n3_minutes: N3 (deep sleep / SWS) duration.
        rem_minutes: REM sleep duration.
        n1_pct: N1 percentage of TST.
        n2_pct: N2 percentage of TST.
        n3_pct: N3 percentage of TST.
        rem_pct: REM percentage of TST.
        sleep_start: Sleep onset timestamp.
        sleep_end: Final awakening timestamp.
        quality_ok: Whether data quality was sufficient.
        source: Data source identifier.
    """

    date: datetime | None = None
    tst_minutes: float = 0.0
    tib_minutes: float = 0.0
    sleep_efficiency: float = 0.0
    sol_minutes: float = 0.0
    waso_minutes: float = 0.0
    n_awakenings: int = 0
    n1_minutes: float = 0.0
    n2_minutes: float = 0.0
    n3_minutes: float = 0.0
    rem_minutes: float = 0.0
    n1_pct: float = 0.0
    n2_pct: float = 0.0
    n3_pct: float = 0.0
    rem_pct: float = 0.0
    sleep_start: datetime | None = None
    sleep_end: datetime | None = None
    quality_ok: bool = True
    source: str = "unknown"


@dataclass(slots=True)
class SleepDiary:
    """Sleep diary entry for subjective sleep data.

    Attributes:
        date: Date of sleep (night starting date).
        lights_off: Time lights were turned off.
        lights_on: Time of final awakening.
        perceived_sol_minutes: Perceived time to fall asleep.
        perceived_awakenings: Perceived number of awakenings.
        sleep_quality: Subjective sleep quality (1-5 scale).
        notes: Free-text notes.
    """

    date: datetime
    lights_off: datetime | None = None
    lights_on: datetime | None = None
    perceived_sol_minutes: float | None = None
    perceived_awakenings: int | None = None
    sleep_quality: int | None = None
    notes: str = ""


@dataclass(slots=True)
class SleepSummary:
    """Summary of sleep metrics over multiple nights.

    Attributes:
        nights: List of individual night metrics.
        avg_tst_minutes: Average TST across nights.
        avg_sleep_efficiency: Average sleep efficiency.
        avg_sol_minutes: Average SOL.
        avg_waso_minutes: Average WASO.
        avg_n3_pct: Average deep sleep percentage.
        avg_rem_pct: Average REM percentage.
        nights_with_short_sleep: Count of nights with TST < 4h.
        nights_with_poor_efficiency: Count of nights with SE < 75%.
    """

    nights: list[SleepMetrics] = field(default_factory=list)
    avg_tst_minutes: float = 0.0
    avg_sleep_efficiency: float = 0.0
    avg_sol_minutes: float = 0.0
    avg_waso_minutes: float = 0.0
    avg_n3_pct: float = 0.0
    avg_rem_pct: float = 0.0
    nights_with_short_sleep: int = 0
    nights_with_poor_efficiency: int = 0


# ---------------------------------------------------------------------------
# Core sleep metrics computation
# ---------------------------------------------------------------------------


def compute_sleep_metrics_from_epochs(
    epochs: pd.DataFrame,
    epoch_duration_seconds: int = 30,
    sleep_start: datetime | None = None,
    sleep_end: datetime | None = None,
    source: str = "epochs",
) -> SleepMetrics:
    """Compute sleep metrics from epoch-level sleep staging data.

    Args:
        epochs: DataFrame with columns:
            - timestamp: Epoch timestamp.
            - stage: Sleep stage (0=Wake, 1=N1, 2=N2, 3=N3, 4=REM).
        epoch_duration_seconds: Duration of each epoch in seconds.
        sleep_start: Optional override for sleep onset time.
        sleep_end: Optional override for final awakening time.
        source: Data source identifier.

    Returns:
        SleepMetrics for the night.
    """
    if epochs.empty:
        _LOGGER.warning("Empty epochs DataFrame provided")
        return SleepMetrics(quality_ok=False, source=source)

    # Ensure required columns
    if "stage" not in epochs.columns:
        _LOGGER.warning("Missing 'stage' column in epochs DataFrame")
        return SleepMetrics(quality_ok=False, source=source)

    # Convert epoch duration to minutes
    epoch_minutes = epoch_duration_seconds / 60.0

    # Count epochs by stage
    stage_counts = epochs["stage"].value_counts()
    wake_epochs = stage_counts.get(0, 0)
    n1_epochs = stage_counts.get(1, 0)
    n2_epochs = stage_counts.get(2, 0)
    n3_epochs = stage_counts.get(3, 0)
    rem_epochs = stage_counts.get(4, 0)

    # Sleep epochs (non-wake)
    sleep_epochs = n1_epochs + n2_epochs + n3_epochs + rem_epochs
    total_epochs = len(epochs)

    # Compute durations
    tst_minutes = sleep_epochs * epoch_minutes
    tib_minutes = total_epochs * epoch_minutes
    n1_minutes = n1_epochs * epoch_minutes
    n2_minutes = n2_epochs * epoch_minutes
    n3_minutes = n3_epochs * epoch_minutes
    rem_minutes = rem_epochs * epoch_minutes

    # Sleep efficiency
    sleep_efficiency = (tst_minutes / tib_minutes * 100.0) if tib_minutes > 0 else 0.0

    # Stage percentages
    if tst_minutes > 0:
        n1_pct = n1_minutes / tst_minutes * 100.0
        n2_pct = n2_minutes / tst_minutes * 100.0
        n3_pct = n3_minutes / tst_minutes * 100.0
        rem_pct = rem_minutes / tst_minutes * 100.0
    else:
        n1_pct = n2_pct = n3_pct = rem_pct = 0.0

    # Compute SOL (time from first epoch to first sleep epoch)
    sol_minutes = 0.0
    if "timestamp" in epochs.columns:
        epochs_sorted = epochs.sort_values("timestamp")
        first_sleep_idx = epochs_sorted[epochs_sorted["stage"] > 0].index
        if len(first_sleep_idx) > 0:
            first_sleep_pos = epochs_sorted.index.get_loc(first_sleep_idx[0])
            sol_minutes = first_sleep_pos * epoch_minutes

    # Compute WASO (wake time after first sleep, before last sleep)
    waso_minutes = 0.0
    n_awakenings = 0
    if "timestamp" in epochs.columns:
        epochs_sorted = epochs.sort_values("timestamp").reset_index(drop=True)
        stages = epochs_sorted["stage"].to_numpy()

        # Find first and last sleep epochs
        sleep_mask = stages > 0
        sleep_indices = np.where(sleep_mask)[0]

        if len(sleep_indices) >= 2:
            first_sleep = sleep_indices[0]
            last_sleep = sleep_indices[-1]

            # WASO: wake epochs between first and last sleep
            middle_epochs = stages[first_sleep:last_sleep + 1]
            waso_epochs = np.sum(middle_epochs == 0)
            waso_minutes = waso_epochs * epoch_minutes

            # Count awakenings (transitions from sleep to wake)
            for i in range(first_sleep, last_sleep):
                if stages[i] > 0 and stages[i + 1] == 0:
                    n_awakenings += 1

    # Determine sleep start/end from data if not provided
    if sleep_start is None and "timestamp" in epochs.columns:
        sleep_start = pd.to_datetime(epochs["timestamp"].min())
    if sleep_end is None and "timestamp" in epochs.columns:
        sleep_end = pd.to_datetime(epochs["timestamp"].max())

    # Quality check
    quality_ok = tst_minutes >= _MIN_TST_HOURS * 60

    # Extract date from sleep_start
    sleep_date = sleep_start if sleep_start is not None else None

    return SleepMetrics(
        date=sleep_date,
        tst_minutes=tst_minutes,
        tib_minutes=tib_minutes,
        sleep_efficiency=sleep_efficiency,
        sol_minutes=sol_minutes,
        waso_minutes=waso_minutes,
        n_awakenings=n_awakenings,
        n1_minutes=n1_minutes,
        n2_minutes=n2_minutes,
        n3_minutes=n3_minutes,
        rem_minutes=rem_minutes,
        n1_pct=n1_pct,
        n2_pct=n2_pct,
        n3_pct=n3_pct,
        rem_pct=rem_pct,
        sleep_start=sleep_start,
        sleep_end=sleep_end,
        quality_ok=quality_ok,
        source=source,
    )


def compute_sleep_metrics_from_binary(
    sleep_wake: np.ndarray | pd.Series,
    timestamps: pd.Series | np.ndarray | None = None,
    epoch_duration_seconds: int = 30,
    source: str = "binary",
) -> SleepMetrics:
    """Compute sleep metrics from binary sleep/wake classification.

    Args:
        sleep_wake: Binary array (0=Wake, 1=Sleep).
        timestamps: Optional timestamps for each epoch.
        epoch_duration_seconds: Duration of each epoch in seconds.
        source: Data source identifier.

    Returns:
        SleepMetrics for the night (without stage breakdown).
    """
    if isinstance(sleep_wake, pd.Series):
        sw = sleep_wake.to_numpy()
    else:
        sw = np.asarray(sleep_wake)

    if len(sw) == 0:
        return SleepMetrics(quality_ok=False, source=source)

    epoch_minutes = epoch_duration_seconds / 60.0

    # Count sleep and wake epochs
    sleep_epochs = np.sum(sw == 1)
    wake_epochs = np.sum(sw == 0)
    total_epochs = len(sw)

    tst_minutes = sleep_epochs * epoch_minutes
    tib_minutes = total_epochs * epoch_minutes
    sleep_efficiency = (tst_minutes / tib_minutes * 100.0) if tib_minutes > 0 else 0.0

    # SOL: epochs before first sleep
    first_sleep_indices = np.where(sw == 1)[0]
    sol_minutes = 0.0
    if len(first_sleep_indices) > 0:
        sol_minutes = first_sleep_indices[0] * epoch_minutes

    # WASO and awakenings
    waso_minutes = 0.0
    n_awakenings = 0
    if len(first_sleep_indices) >= 2:
        first_sleep = first_sleep_indices[0]
        last_sleep = first_sleep_indices[-1]

        # WASO: wake epochs between first and last sleep
        middle = sw[first_sleep:last_sleep + 1]
        waso_epochs = np.sum(middle == 0)
        waso_minutes = waso_epochs * epoch_minutes

        # Count awakenings
        for i in range(first_sleep, last_sleep):
            if sw[i] == 1 and sw[i + 1] == 0:
                n_awakenings += 1

    # Timestamps
    sleep_start = None
    sleep_end = None
    if timestamps is not None:
        ts = pd.to_datetime(timestamps)
        sleep_start = ts.min()
        sleep_end = ts.max()

    quality_ok = tst_minutes >= _MIN_TST_HOURS * 60

    return SleepMetrics(
        date=sleep_start,
        tst_minutes=tst_minutes,
        tib_minutes=tib_minutes,
        sleep_efficiency=sleep_efficiency,
        sol_minutes=sol_minutes,
        waso_minutes=waso_minutes,
        n_awakenings=n_awakenings,
        sleep_start=sleep_start,
        sleep_end=sleep_end,
        quality_ok=quality_ok,
        source=source,
    )


# ---------------------------------------------------------------------------
# Sleep summary computation
# ---------------------------------------------------------------------------


def compute_sleep_summary(nights: list[SleepMetrics]) -> SleepSummary:
    """Compute summary statistics across multiple nights.

    Args:
        nights: List of SleepMetrics for individual nights.

    Returns:
        SleepSummary with aggregated statistics.
    """
    if not nights:
        return SleepSummary()

    # Filter to quality-ok nights for averages
    valid_nights = [n for n in nights if n.quality_ok]

    if valid_nights:
        avg_tst = np.mean([n.tst_minutes for n in valid_nights])
        avg_se = np.mean([n.sleep_efficiency for n in valid_nights])
        avg_sol = np.mean([n.sol_minutes for n in valid_nights])
        avg_waso = np.mean([n.waso_minutes for n in valid_nights])
        avg_n3 = np.mean([n.n3_pct for n in valid_nights])
        avg_rem = np.mean([n.rem_pct for n in valid_nights])
    else:
        avg_tst = avg_se = avg_sol = avg_waso = avg_n3 = avg_rem = 0.0

    # Count problematic nights
    short_sleep = sum(1 for n in nights if n.tst_minutes < _MIN_TST_HOURS * 60)
    poor_efficiency = sum(1 for n in nights if n.sleep_efficiency < _SE_POOR)

    return SleepSummary(
        nights=nights,
        avg_tst_minutes=avg_tst,
        avg_sleep_efficiency=avg_se,
        avg_sol_minutes=avg_sol,
        avg_waso_minutes=avg_waso,
        avg_n3_pct=avg_n3,
        avg_rem_pct=avg_rem,
        nights_with_short_sleep=short_sleep,
        nights_with_poor_efficiency=poor_efficiency,
    )


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------


def interpret_sleep_metrics(metrics: SleepMetrics) -> dict[str, str]:
    """Interpret sleep metrics against clinical thresholds.

    Args:
        metrics: SleepMetrics for a single night.

    Returns:
        Dictionary with interpretation strings.
    """
    interpretations: dict[str, str] = {}

    # TST interpretation
    tst_hours = metrics.tst_minutes / 60.0
    if tst_hours < 5:
        interpretations["tst"] = f"Very short sleep ({tst_hours:.1f}h); consider sleep extension"
    elif tst_hours < 6:
        interpretations["tst"] = f"Short sleep ({tst_hours:.1f}h); below recommended 7-9h"
    elif tst_hours < 7:
        interpretations["tst"] = f"Adequate sleep ({tst_hours:.1f}h); approaching recommended range"
    elif tst_hours <= 9:
        interpretations["tst"] = f"Good sleep duration ({tst_hours:.1f}h)"
    else:
        interpretations["tst"] = f"Long sleep ({tst_hours:.1f}h); may indicate sleep disorder"

    # Sleep efficiency interpretation
    if metrics.sleep_efficiency >= _SE_EXCELLENT:
        interpretations["se"] = f"Excellent sleep efficiency ({metrics.sleep_efficiency:.1f}%)"
    elif metrics.sleep_efficiency >= _SE_GOOD:
        interpretations["se"] = f"Good sleep efficiency ({metrics.sleep_efficiency:.1f}%)"
    elif metrics.sleep_efficiency >= _SE_POOR:
        interpretations["se"] = f"Fair sleep efficiency ({metrics.sleep_efficiency:.1f}%)"
    else:
        interpretations["se"] = (
            f"Poor sleep efficiency ({metrics.sleep_efficiency:.1f}%); "
            "may indicate insomnia"
        )

    # SOL interpretation
    if metrics.sol_minutes <= _SOL_NORMAL:
        interpretations["sol"] = f"Normal sleep onset ({metrics.sol_minutes:.0f} min)"
    elif metrics.sol_minutes <= _SOL_ELEVATED:
        interpretations["sol"] = f"Slightly prolonged sleep onset ({metrics.sol_minutes:.0f} min)"
    else:
        interpretations["sol"] = (
            f"Prolonged sleep onset ({metrics.sol_minutes:.0f} min); "
            "may indicate sleep-onset insomnia"
        )

    # WASO interpretation
    if metrics.waso_minutes <= _WASO_NORMAL:
        interpretations["waso"] = f"Low wake time ({metrics.waso_minutes:.0f} min)"
    elif metrics.waso_minutes <= _WASO_ELEVATED:
        interpretations["waso"] = f"Moderate wake time ({metrics.waso_minutes:.0f} min)"
    else:
        interpretations["waso"] = (
            f"High wake time ({metrics.waso_minutes:.0f} min); "
            "may indicate sleep maintenance insomnia"
        )

    # Deep sleep interpretation
    if metrics.n3_pct > 0:
        if metrics.n3_pct < 10:
            interpretations["n3"] = f"Low deep sleep ({metrics.n3_pct:.1f}%)"
        elif metrics.n3_pct <= 25:
            interpretations["n3"] = f"Normal deep sleep ({metrics.n3_pct:.1f}%)"
        else:
            interpretations["n3"] = f"High deep sleep ({metrics.n3_pct:.1f}%)"

    # REM interpretation
    if metrics.rem_pct > 0:
        if metrics.rem_pct < 15:
            interpretations["rem"] = f"Low REM sleep ({metrics.rem_pct:.1f}%)"
        elif metrics.rem_pct <= 30:
            interpretations["rem"] = f"Normal REM sleep ({metrics.rem_pct:.1f}%)"
        else:
            interpretations["rem"] = f"High REM sleep ({metrics.rem_pct:.1f}%)"

    # Quality note
    if not metrics.quality_ok:
        interpretations["quality"] = (
            "Warning: Short sleep duration; metrics may be unreliable"
        )

    return interpretations


# ---------------------------------------------------------------------------
# DataFrame conversion utilities
# ---------------------------------------------------------------------------


def sleep_metrics_to_dataframe(metrics: SleepMetrics | list[SleepMetrics]) -> pd.DataFrame:
    """Convert SleepMetrics to DataFrame.

    Args:
        metrics: Single SleepMetrics or list of SleepMetrics.

    Returns:
        DataFrame with one row per night.
    """
    if isinstance(metrics, SleepMetrics):
        metrics = [metrics]

    records = []
    for m in metrics:
        records.append({
            "date": m.date,
            "tst_minutes": m.tst_minutes,
            "tst_hours": m.tst_minutes / 60.0,
            "tib_minutes": m.tib_minutes,
            "sleep_efficiency": m.sleep_efficiency,
            "sol_minutes": m.sol_minutes,
            "waso_minutes": m.waso_minutes,
            "n_awakenings": m.n_awakenings,
            "n1_minutes": m.n1_minutes,
            "n2_minutes": m.n2_minutes,
            "n3_minutes": m.n3_minutes,
            "rem_minutes": m.rem_minutes,
            "n1_pct": m.n1_pct,
            "n2_pct": m.n2_pct,
            "n3_pct": m.n3_pct,
            "rem_pct": m.rem_pct,
            "sleep_start": m.sleep_start,
            "sleep_end": m.sleep_end,
            "quality_ok": m.quality_ok,
            "source": m.source,
        })

    return pd.DataFrame(records)


def compare_objective_subjective(
    objective: SleepMetrics,
    subjective: SleepDiary,
) -> dict[str, Any]:
    """Compare objective sleep metrics with subjective diary.

    Args:
        objective: Objective sleep metrics from device.
        subjective: Subjective sleep diary entry.

    Returns:
        Dictionary with comparison metrics and discrepancies.
    """
    comparison: dict[str, Any] = {
        "date": objective.date,
        "objective_tst_minutes": objective.tst_minutes,
        "objective_sol_minutes": objective.sol_minutes,
        "objective_awakenings": objective.n_awakenings,
        "subjective_sol_minutes": subjective.perceived_sol_minutes,
        "subjective_awakenings": subjective.perceived_awakenings,
        "subjective_quality": subjective.sleep_quality,
    }

    # Compute discrepancies
    if subjective.perceived_sol_minutes is not None:
        comparison["sol_discrepancy"] = (
            objective.sol_minutes - subjective.perceived_sol_minutes
        )

    if subjective.perceived_awakenings is not None:
        comparison["awakening_discrepancy"] = (
            objective.n_awakenings - subjective.perceived_awakenings
        )

    return comparison

