"""Heart Rate Fragmentation (HRF) metrics module.

This module implements HRF metrics that capture non-autonomic components of
short-term heart rate variability. These metrics have been shown to predict
atrial fibrillation and other cardiovascular outcomes independently of
traditional HRV measures.

References:
- Costa MD, et al. (2017). Heart Rate Fragmentation: A New Approach to the
  Analysis of Cardiac Interbeat Interval Dynamics. Front Physiol. 8:255.
  DOI: 10.3389/fphys.2017.00255
- Guichard JB, et al. (2025). PROOF-AF Study: Assessing heart rate fragmentation
  to predict atrial fibrillation. EHJ Open. DOI: 10.1093/ehjopen/oeaf030

Metrics implemented:
- PIP: Percentage of Inflection Points
- PIP_H: Percentage of Hard Inflection Points
- PIP_S: Percentage of Soft Inflection Points
- IALS: Inverse Average Length of Acceleration/Deceleration Segments
- PSS: Percentage of Short Segments
- PAS: Percentage of Alternating Segments
- W0-W3: Word distributions (4-beat sequences by inflection count)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Default threshold for hard vs soft inflection points (ms)
# Hard inflection: direction change with ΔRR > threshold
# Soft inflection: direction change with ΔRR <= threshold
_DEFAULT_HARD_THRESHOLD_MS: Final[float] = 10.0

# Minimum number of RR intervals required for reliable HRF computation
_MIN_RR_COUNT: Final[int] = 30


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HRFMetrics:
    """Container for Heart Rate Fragmentation metrics.

    Attributes:
        pip: Percentage of Inflection Points (0-100).
        pip_h: Percentage of Hard Inflection Points (0-100).
        pip_s: Percentage of Soft Inflection Points (0-100).
        ials: Inverse Average Length of Segments.
        pss: Percentage of Short Segments (length <= 3).
        pas: Percentage of Alternating Segments.
        w0: Percentage of 4-beat words with 0 inflection points.
        w1: Percentage of 4-beat words with 1 inflection point.
        w2: Percentage of 4-beat words with 2 inflection points.
        w3: Percentage of 4-beat words with 3 inflection points.
        n_intervals: Number of RR intervals used in computation.
        quality_ok: Whether data quality was sufficient for reliable metrics.
    """

    pip: float
    pip_h: float
    pip_s: float
    ials: float
    pss: float
    pas: float
    w0: float
    w1: float
    w2: float
    w3: float
    n_intervals: int
    quality_ok: bool


# ---------------------------------------------------------------------------
# Core HRF computation functions
# ---------------------------------------------------------------------------


def _compute_differences(rr_intervals: np.ndarray) -> np.ndarray:
    """Compute successive differences between RR intervals.

    Args:
        rr_intervals: Array of RR intervals in milliseconds.

    Returns:
        Array of successive differences (ΔRR = RR[i+1] - RR[i]).
    """
    return np.diff(rr_intervals)


def _identify_inflection_points(
    differences: np.ndarray,
    hard_threshold_ms: float = _DEFAULT_HARD_THRESHOLD_MS,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Identify inflection points in the RR interval series.

    An inflection point occurs when the sign of successive differences changes
    (i.e., acceleration changes to deceleration or vice versa).

    Args:
        differences: Array of successive RR differences.
        hard_threshold_ms: Threshold for hard vs soft inflection points.

    Returns:
        Tuple of (inflection_mask, hard_mask, soft_mask).
        Each mask is a boolean array of length len(differences) - 1.
    """
    if len(differences) < 2:
        empty = np.array([], dtype=bool)
        return empty, empty, empty

    # Sign of each difference: +1 (acceleration), -1 (deceleration), 0 (no change)
    signs = np.sign(differences)

    # Inflection occurs when sign changes (excluding zero transitions)
    sign_changes = signs[:-1] * signs[1:]
    inflection_mask = sign_changes < 0  # Sign change: + to - or - to +

    # Magnitude of the difference at inflection points
    magnitudes = np.abs(differences[1:])

    # Hard inflection: magnitude > threshold
    hard_mask = inflection_mask & (magnitudes > hard_threshold_ms)

    # Soft inflection: magnitude <= threshold
    soft_mask = inflection_mask & (magnitudes <= hard_threshold_ms)

    return inflection_mask, hard_mask, soft_mask


def _compute_segment_lengths(differences: np.ndarray) -> list[int]:
    """Compute lengths of acceleration/deceleration segments.

    A segment is a consecutive run of positive or negative differences.

    Args:
        differences: Array of successive RR differences.

    Returns:
        List of segment lengths.
    """
    if len(differences) == 0:
        return []

    signs = np.sign(differences)
    segment_lengths: list[int] = []
    current_length = 1

    for i in range(1, len(signs)):
        if signs[i] == signs[i - 1] and signs[i] != 0:
            current_length += 1
        else:
            if current_length > 0:
                segment_lengths.append(current_length)
            current_length = 1

    # Add final segment
    if current_length > 0:
        segment_lengths.append(current_length)

    return segment_lengths


def _compute_word_distribution(
    inflection_mask: np.ndarray,
) -> tuple[float, float, float, float]:
    """Compute word distribution (W0-W3) from inflection mask.

    Words are 4-beat sequences (3 consecutive inflection decisions).
    W_k is the percentage of words with exactly k inflection points.

    Args:
        inflection_mask: Boolean array indicating inflection points.

    Returns:
        Tuple of (w0, w1, w2, w3) percentages.
    """
    if len(inflection_mask) < 3:
        return 0.0, 0.0, 0.0, 0.0

    # Count inflection points in each 3-element window
    n_words = len(inflection_mask) - 2
    counts = [0, 0, 0, 0]

    for i in range(n_words):
        n_inflections = int(inflection_mask[i]) + int(inflection_mask[i + 1]) + int(inflection_mask[i + 2])
        counts[n_inflections] += 1

    total = sum(counts)
    if total == 0:
        return 0.0, 0.0, 0.0, 0.0

    return (
        counts[0] / total * 100.0,
        counts[1] / total * 100.0,
        counts[2] / total * 100.0,
        counts[3] / total * 100.0,
    )


def compute_hrf_metrics(
    rr_intervals: np.ndarray | pd.Series | list[float],
    hard_threshold_ms: float = _DEFAULT_HARD_THRESHOLD_MS,
) -> HRFMetrics:
    """Compute Heart Rate Fragmentation metrics from RR intervals.

    Args:
        rr_intervals: RR intervals in milliseconds.
        hard_threshold_ms: Threshold for hard vs soft inflection points.

    Returns:
        HRFMetrics dataclass with all computed metrics.
    """
    # Convert to numpy array and validate
    if isinstance(rr_intervals, pd.Series):
        rr = rr_intervals.dropna().to_numpy()
    elif isinstance(rr_intervals, list):
        rr = np.array([x for x in rr_intervals if x is not None and not np.isnan(x)])
    else:
        rr = np.asarray(rr_intervals)
        rr = rr[~np.isnan(rr)]

    n_intervals = len(rr)
    quality_ok = n_intervals >= _MIN_RR_COUNT

    if n_intervals < 3:
        _LOGGER.warning(
            "Insufficient RR intervals for HRF computation: %d (min %d)",
            n_intervals,
            _MIN_RR_COUNT,
        )
        return HRFMetrics(
            pip=0.0, pip_h=0.0, pip_s=0.0, ials=0.0, pss=0.0, pas=0.0,
            w0=0.0, w1=0.0, w2=0.0, w3=0.0,
            n_intervals=n_intervals, quality_ok=False,
        )

    # Compute successive differences
    differences = _compute_differences(rr)

    # Identify inflection points
    inflection_mask, hard_mask, soft_mask = _identify_inflection_points(
        differences, hard_threshold_ms
    )

    # PIP: Percentage of Inflection Points
    n_possible = len(inflection_mask)
    pip = np.sum(inflection_mask) / n_possible * 100.0 if n_possible > 0 else 0.0
    pip_h = np.sum(hard_mask) / n_possible * 100.0 if n_possible > 0 else 0.0
    pip_s = np.sum(soft_mask) / n_possible * 100.0 if n_possible > 0 else 0.0

    # Segment analysis
    segment_lengths = _compute_segment_lengths(differences)

    if segment_lengths:
        # IALS: Inverse Average Length of Segments
        avg_length = np.mean(segment_lengths)
        ials = 1.0 / avg_length if avg_length > 0 else 0.0

        # PSS: Percentage of Short Segments (length <= 3)
        short_segments = sum(1 for s in segment_lengths if s <= 3)
        pss = short_segments / len(segment_lengths) * 100.0

        # PAS: Percentage of Alternating Segments (length == 1)
        alternating = sum(1 for s in segment_lengths if s == 1)
        pas = alternating / len(segment_lengths) * 100.0
    else:
        ials = 0.0
        pss = 0.0
        pas = 0.0

    # Word distribution
    w0, w1, w2, w3 = _compute_word_distribution(inflection_mask)

    return HRFMetrics(
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
        n_intervals=n_intervals,
        quality_ok=quality_ok,
    )


def compute_hrf_windowed(
    rr_intervals: np.ndarray | pd.Series,
    window_size: int = 300,
    step_size: int = 60,
    hard_threshold_ms: float = _DEFAULT_HARD_THRESHOLD_MS,
) -> pd.DataFrame:
    """Compute HRF metrics over sliding windows.

    Args:
        rr_intervals: RR intervals in milliseconds.
        window_size: Number of RR intervals per window.
        step_size: Step size between windows.
        hard_threshold_ms: Threshold for hard vs soft inflection points.

    Returns:
        DataFrame with HRF metrics for each window.
        Columns: window_start, window_end, pip, pip_h, pip_s, ials, pss, pas,
                 w0, w1, w2, w3, n_intervals, quality_ok.
    """
    if isinstance(rr_intervals, pd.Series):
        rr = rr_intervals.dropna().to_numpy()
    else:
        rr = np.asarray(rr_intervals)
        rr = rr[~np.isnan(rr)]

    n_total = len(rr)
    records: list[dict[str, float | int | bool]] = []

    start = 0
    while start + window_size <= n_total:
        window = rr[start:start + window_size]
        metrics = compute_hrf_metrics(window, hard_threshold_ms)

        records.append({
            "window_start": start,
            "window_end": start + window_size,
            "pip": metrics.pip,
            "pip_h": metrics.pip_h,
            "pip_s": metrics.pip_s,
            "ials": metrics.ials,
            "pss": metrics.pss,
            "pas": metrics.pas,
            "w0": metrics.w0,
            "w1": metrics.w1,
            "w2": metrics.w2,
            "w3": metrics.w3,
            "n_intervals": metrics.n_intervals,
            "quality_ok": metrics.quality_ok,
        })
        start += step_size

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Reference values and interpretation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HRFReferenceRange:
    """Reference range for HRF metrics.

    Based on PROOF cohort (healthy adults aged 65).
    """

    pip_low: float = 40.0
    pip_high: float = 60.0
    pip_elevated: float = 65.0  # Elevated AF risk threshold

    ials_low: float = 0.3
    ials_high: float = 0.5

    w3_low: float = 10.0
    w3_high: float = 25.0
    w3_elevated: float = 30.0  # Elevated AF risk threshold


def interpret_hrf_metrics(
    metrics: HRFMetrics,
    reference: HRFReferenceRange | None = None,
) -> dict[str, str]:
    """Interpret HRF metrics against reference values.

    Args:
        metrics: Computed HRF metrics.
        reference: Reference range (default: PROOF cohort values).

    Returns:
        Dictionary with interpretation strings for each metric.
    """
    if reference is None:
        reference = HRFReferenceRange()

    interpretations: dict[str, str] = {}

    # PIP interpretation
    if metrics.pip < reference.pip_low:
        interpretations["pip"] = "Low fragmentation (smooth HR dynamics)"
    elif metrics.pip <= reference.pip_high:
        interpretations["pip"] = "Normal fragmentation"
    elif metrics.pip <= reference.pip_elevated:
        interpretations["pip"] = "Moderately elevated fragmentation"
    else:
        interpretations["pip"] = (
            "Elevated fragmentation (may indicate ANS dysfunction; "
            "consider clinical evaluation if persistent)"
        )

    # W3 interpretation
    if metrics.w3 < reference.w3_low:
        interpretations["w3"] = "Low alternating patterns"
    elif metrics.w3 <= reference.w3_high:
        interpretations["w3"] = "Normal alternating patterns"
    elif metrics.w3 <= reference.w3_elevated:
        interpretations["w3"] = "Moderately elevated alternating patterns"
    else:
        interpretations["w3"] = (
            "Elevated W3 (frequent direction changes; "
            "associated with increased AF risk in PROOF study)"
        )

    # IALS interpretation
    if metrics.ials < reference.ials_low:
        interpretations["ials"] = "Long acceleration/deceleration runs (low fragmentation)"
    elif metrics.ials <= reference.ials_high:
        interpretations["ials"] = "Normal segment lengths"
    else:
        interpretations["ials"] = "Short segments (high fragmentation)"

    # Quality note
    if not metrics.quality_ok:
        interpretations["quality"] = (
            f"Warning: Only {metrics.n_intervals} RR intervals; "
            f"minimum {_MIN_RR_COUNT} recommended for reliable metrics"
        )

    return interpretations


# ---------------------------------------------------------------------------
# Integration with HRV analysis
# ---------------------------------------------------------------------------


def add_hrf_to_hrv_results(
    hrv_results: dict[str, float],
    rr_intervals: np.ndarray | pd.Series,
    hard_threshold_ms: float = _DEFAULT_HARD_THRESHOLD_MS,
) -> dict[str, float]:
    """Add HRF metrics to existing HRV results dictionary.

    Args:
        hrv_results: Dictionary of HRV metrics (e.g., from hrv_core.py).
        rr_intervals: RR intervals in milliseconds.
        hard_threshold_ms: Threshold for hard vs soft inflection points.

    Returns:
        Updated dictionary with HRF metrics added.
    """
    hrf = compute_hrf_metrics(rr_intervals, hard_threshold_ms)

    hrv_results["hrf_pip"] = hrf.pip
    hrv_results["hrf_pip_h"] = hrf.pip_h
    hrv_results["hrf_pip_s"] = hrf.pip_s
    hrv_results["hrf_ials"] = hrf.ials
    hrv_results["hrf_pss"] = hrf.pss
    hrv_results["hrf_pas"] = hrf.pas
    hrv_results["hrf_w0"] = hrf.w0
    hrv_results["hrf_w1"] = hrf.w1
    hrv_results["hrf_w2"] = hrf.w2
    hrv_results["hrf_w3"] = hrf.w3
    hrv_results["hrf_quality_ok"] = float(hrf.quality_ok)

    return hrv_results

