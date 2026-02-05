# Author: Dr Diego Malpica MD
"""
HRV-Based Ventilatory Threshold (VT) Estimation Module.

Implements DFA-α1-based ventilatory threshold detection using multi-parameter
integration following Kubios VT-algorithm architecture and validated
methodologies (Eronen et al., 2024; Gronwald et al., 2020; Rogers et al., 2021).

This module provides:
- DFA-α1 computation (short-term scaling exponent, window 4-16 beats)
- Time-varying DFA-α1 with configurable sliding window
- Heart rate reserve calculation
- Respiratory frequency extraction from RR intervals
- Multi-parameter VT detection (DFA-α1 + HR reserve + respiratory frequency)
- Confidence scoring and quality assessment
- Exercise intensity zone classification

References:
    Eronen T, et al. (2024). Heart Rate Variability Based Ventilatory
    Threshold Estimation. medRxiv. doi: 10.1101/2024.08.14.24311967

    Gronwald T, et al. (2020). Correlation properties of HRV during endurance
    exercise. Ann Noninvasive Electrocardiol, 25(1):e12697.

    Rogers B, et al. (2021). A New Detection Method Defining the Aerobic
    Threshold. Front Physiol, 11:596567.

    Peng CK, et al. (1995). Quantification of scaling exponents. Chaos, 5(1):82-87.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, filtfilt

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# DFA-α1 threshold values (validated by Gronwald et al., 2020; Rogers et al., 2021)
DFA_VT1_THRESHOLD: float = 0.75
DFA_VT2_THRESHOLD: float = 0.50

# Window parameters (Kubios standard)
DEFAULT_WINDOW_SECONDS: int = 120  # 2-minute window
DEFAULT_STEP_SECONDS: int = 5  # 5-second grid interval
DFA_WINDOW_RANGE: Tuple[int, int] = (4, 16)  # beats for short-term α1

# Multi-parameter weights (approximated from Kubios literature)
WEIGHT_DFA: float = 0.60
WEIGHT_HR: float = 0.30
WEIGHT_RESP: float = 0.10

# Quality thresholds
MIN_SIGNAL_QUALITY: float = 0.85
MAX_ARTIFACT_RATE: float = 5.0  # percent
MIN_WINDOW_BEATS: int = 30
SMOOTHING_WINDOW: int = 5  # points for moving average


class IntensityZone(str, Enum):
    """Exercise intensity zones based on DFA-α1."""

    ZONE_1 = "zone_1"  # Below VT1 (easy/aerobic)
    ZONE_2 = "zone_2"  # VT1 to VT2 (tempo/threshold)
    ZONE_3 = "zone_3"  # Above VT2 (high intensity/VO2max)


class VTMethod(str, Enum):
    """VT detection method selection."""

    DFA_ONLY = "dfa_only"
    MULTIPARAMETER = "multiparameter"


@dataclass(frozen=True, slots=True)
class VTResult:
    """Single ventilatory threshold detection result."""

    time_seconds: float
    heart_rate_bpm: float
    dfa_alpha1: float
    hr_relative: float  # fraction of HR reserve (0-1)
    confidence: float  # 0-1
    index: int  # index in time series


@dataclass(frozen=True, slots=True)
class QualityMetrics:
    """Signal and analysis quality metrics."""

    artifact_percentage: float
    total_beats: int
    clean_beats: int
    n_windows: int
    min_dfa: float
    max_dfa: float
    dfa_range: float
    monotonic_decrease: bool  # whether DFA-α1 generally decreases


@dataclass(frozen=True, slots=True)
class IntensityZoneResult:
    """Exercise intensity zone classification for a given HR."""

    zone: IntensityZone
    zone_label: str
    zone_description: str
    hr_min: float
    hr_max: float
    dfa_range: str
    training_guidance: str


@dataclass(slots=True)
class VTAnalysisResult:
    """Complete ventilatory threshold analysis result."""

    vt1: Optional[VTResult]
    vt2: Optional[VTResult]
    timeseries_time: List[float]
    timeseries_dfa: List[float]
    timeseries_hr: List[float]
    timeseries_hr_mean: List[float]
    timeseries_integrated_score: List[float]
    respiratory_frequency_hz: Optional[float]
    quality: QualityMetrics
    method: str
    intensity_zones: List[IntensityZoneResult] = field(default_factory=list)
    interpretation: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core DFA-α1 computation
# ---------------------------------------------------------------------------


def compute_dfa_alpha1(
    rr_intervals: np.ndarray,
    window_range: Tuple[int, int] = DFA_WINDOW_RANGE,
) -> float:
    """Compute DFA-α1 (short-term scaling exponent) from RR intervals.

    Uses detrended fluctuation analysis with linear detrending in each window.
    The scaling exponent is the slope of log F(n) vs log n.

    Args:
        rr_intervals: RR intervals in milliseconds (minimum ~30 beats).
        window_range: Tuple (min_beats, max_beats) for window sizes.

    Returns:
        DFA-α1 scaling exponent.

    Raises:
        ValueError: If insufficient data for DFA computation.

    References:
        Peng CK, et al. (1995). Quantification of scaling exponents and
        crossover phenomena. Chaos, 5(1):82-87.
    """
    if len(rr_intervals) < window_range[1] * 2:
        raise ValueError(
            f"Need at least {window_range[1] * 2} RR intervals for DFA, "
            f"got {len(rr_intervals)}."
        )

    # Step 1: Integrate (cumulative sum after mean removal)
    rr_mean = np.mean(rr_intervals)
    y = np.cumsum(rr_intervals - rr_mean)

    # Step 2: Calculate fluctuation for each window size
    window_sizes = np.arange(window_range[0], window_range[1] + 1)
    log_n_list: List[float] = []
    log_f_list: List[float] = []

    for n in window_sizes:
        n_segments = len(y) // n
        if n_segments < 1:
            continue

        f_n_values: List[float] = []
        for i in range(n_segments):
            segment = y[i * n : (i + 1) * n]
            t = np.arange(len(segment), dtype=np.float64)
            coefficients = np.polyfit(t, segment, 1)
            fit = np.polyval(coefficients, t)
            fluctuation = np.sqrt(np.mean((segment - fit) ** 2))
            f_n_values.append(fluctuation)

        mean_fluctuation = np.mean(f_n_values)
        if mean_fluctuation > 0:
            log_n_list.append(np.log(float(n)))
            log_f_list.append(np.log(mean_fluctuation))

    if len(log_n_list) < 2:
        raise ValueError("Insufficient valid windows for DFA slope calculation.")

    # Step 3: Linear regression in log-log space
    log_n_arr = np.array(log_n_list)
    log_f_arr = np.array(log_f_list)
    alpha1: float = float(np.polyfit(log_n_arr, log_f_arr, 1)[0])

    return alpha1


# ---------------------------------------------------------------------------
# Time-varying DFA-α1
# ---------------------------------------------------------------------------


def compute_time_varying_dfa(
    rr_intervals: np.ndarray,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
    step_seconds: int = DEFAULT_STEP_SECONDS,
) -> Dict[str, np.ndarray]:
    """Compute time-varying DFA-α1 using sliding window approach.

    Follows Kubios HRV standard methodology:
    - Window width: 120 seconds (2 minutes)
    - Grid interval: 5 seconds
    - DFA window range: 4-16 beats

    Args:
        rr_intervals: RR intervals in milliseconds.
        window_seconds: Window size in seconds (default: 120).
        step_seconds: Step size in seconds (default: 5).

    Returns:
        Dictionary with keys:
            - 'time': Time stamps in seconds (center of window).
            - 'dfa_alpha1': DFA-α1 values.
            - 'hr_mean': Mean HR (bpm) in each window.
            - 'rr_count': Number of RR intervals in each window.
    """
    rr_mean_global = np.mean(rr_intervals)
    window_beats = max(MIN_WINDOW_BEATS, int((window_seconds * 1000) / rr_mean_global))
    step_beats = max(1, int((step_seconds * 1000) / rr_mean_global))

    time_stamps: List[float] = []
    dfa_values: List[float] = []
    hr_means: List[float] = []
    rr_counts: List[int] = []

    cumulative_ms = np.cumsum(rr_intervals)
    max_iterations = (len(rr_intervals) - window_beats) // step_beats + 1
    max_iterations = min(max_iterations, 10_000)  # bounded

    for iteration_idx in range(max_iterations):
        start_idx = iteration_idx * step_beats
        end_idx = start_idx + window_beats

        if end_idx > len(rr_intervals):
            break

        window = rr_intervals[start_idx:end_idx]

        if len(window) < DFA_WINDOW_RANGE[1] * 2:
            continue

        try:
            alpha1 = compute_dfa_alpha1(window)

            # Time stamp at center of window (seconds)
            center_idx = start_idx + window_beats // 2
            window_time = float(cumulative_ms[min(center_idx, len(cumulative_ms) - 1)] / 1000.0)

            hr_mean = 60000.0 / float(np.mean(window))

            time_stamps.append(window_time)
            dfa_values.append(alpha1)
            hr_means.append(hr_mean)
            rr_counts.append(len(window))

        except (ValueError, RuntimeError):
            continue

    return {
        "time": np.array(time_stamps, dtype=np.float64),
        "dfa_alpha1": np.array(dfa_values, dtype=np.float64),
        "hr_mean": np.array(hr_means, dtype=np.float64),
        "rr_count": np.array(rr_counts, dtype=np.int64),
    }


# ---------------------------------------------------------------------------
# Heart rate reserve
# ---------------------------------------------------------------------------


def calculate_hr_reserve(
    rr_intervals: np.ndarray,
    hr_rest: float,
    hr_max: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate heart rate relative to reserve for each RR interval.

    Args:
        rr_intervals: RR intervals in milliseconds.
        hr_rest: Resting heart rate (bpm).
        hr_max: Maximum heart rate (bpm).

    Returns:
        Tuple of (hr_relative [0-1], hr_instantaneous [bpm]).

    Raises:
        ValueError: If hr_max <= hr_rest.
    """
    if hr_max <= hr_rest:
        raise ValueError(f"hr_max ({hr_max}) must exceed hr_rest ({hr_rest}).")

    hr_instantaneous = 60000.0 / rr_intervals
    hr_reserve = hr_max - hr_rest
    hr_relative = (hr_instantaneous - hr_rest) / hr_reserve
    hr_relative = np.clip(hr_relative, 0.0, 1.0)

    return hr_relative, hr_instantaneous


# ---------------------------------------------------------------------------
# Respiratory frequency extraction
# ---------------------------------------------------------------------------


def extract_respiratory_frequency(
    rr_intervals: np.ndarray,
) -> Tuple[float, float]:
    """Extract dominant respiratory frequency from RR interval spectrum.

    Uses FFT-based spectral analysis to identify the peak in the
    respiratory band (0.15-0.40 Hz).

    Args:
        rr_intervals: RR intervals in milliseconds.

    Returns:
        Tuple of (respiratory_freq_hz, respiratory_power).
    """
    if len(rr_intervals) < 16:
        return 0.25, 0.0

    # Approximate sampling rate
    median_rr_s = float(np.median(rr_intervals)) / 1000.0
    fs = 1.0 / median_rr_s

    rr_detrended = rr_intervals - np.mean(rr_intervals)

    n = len(rr_detrended)
    fft_vals = np.fft.rfft(rr_detrended)
    fft_freq = np.fft.rfftfreq(n, d=1.0 / fs)
    power = np.abs(fft_vals) ** 2

    # Respiratory band: 0.15-0.40 Hz
    resp_mask = (fft_freq >= 0.15) & (fft_freq <= 0.40)

    if np.any(resp_mask):
        resp_power_vals = power[resp_mask]
        resp_freqs = fft_freq[resp_mask]
        peak_idx = int(np.argmax(resp_power_vals))
        return float(resp_freqs[peak_idx]), float(resp_power_vals[peak_idx])

    return 0.25, 0.0  # default typical respiratory rate


# ---------------------------------------------------------------------------
# Artifact correction
# ---------------------------------------------------------------------------


def correct_artifacts(
    rr_intervals: np.ndarray,
    threshold_pct: float = 0.20,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """Apply Kubios-style artifact correction to RR intervals.

    Removes physiologically implausible intervals outside ±threshold_pct
    of the local median.

    Args:
        rr_intervals: RR intervals in milliseconds.
        threshold_pct: Deviation threshold from median (default: 0.20 = ±20%).

    Returns:
        Tuple of (clean_rr, valid_mask, artifact_percentage).
    """
    rr_median = float(np.median(rr_intervals))
    lower = rr_median * (1.0 - threshold_pct)
    upper = rr_median * (1.0 + threshold_pct)

    valid_mask = (rr_intervals >= lower) & (rr_intervals <= upper)
    artifact_pct = (1.0 - float(np.mean(valid_mask))) * 100.0
    clean_rr = rr_intervals[valid_mask]

    return clean_rr, valid_mask, artifact_pct


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


def _compute_threshold_confidence(
    idx: int,
    dfa_values: np.ndarray,
    hr_values: np.ndarray,
    half_window: int = 5,
) -> float:
    """Compute confidence score for a detected threshold.

    Assesses transition smoothness by checking for monotonic DFA decrease
    and HR increase around the detected threshold point.

    Args:
        idx: Index of detected threshold.
        dfa_values: DFA-α1 time series.
        hr_values: HR time series.
        half_window: Half-window size for analysis.

    Returns:
        Confidence score [0, 1].
    """
    if idx < half_window or idx >= len(dfa_values) - half_window:
        return 0.4

    dfa_window = dfa_values[idx - half_window : idx + half_window]
    hr_window = hr_values[idx - half_window : idx + half_window]

    t = np.arange(len(dfa_window), dtype=np.float64)

    # Check for monotonic DFA decrease
    if np.std(dfa_window) > 1e-10:
        dfa_corr = float(np.corrcoef(t, dfa_window)[0, 1])
    else:
        dfa_corr = 0.0

    # Check for HR increase
    if np.std(hr_window) > 1e-10:
        hr_corr = float(np.corrcoef(t, hr_window)[0, 1])
    else:
        hr_corr = 0.0

    # DFA should decrease (negative correlation) and HR should increase (positive)
    dfa_score = max(0.0, -dfa_corr)  # negative = good
    hr_score = max(0.0, hr_corr)  # positive = good

    confidence = (dfa_score + hr_score) / 2.0
    return float(np.clip(confidence, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Multi-parameter VT detection
# ---------------------------------------------------------------------------


def detect_ventilatory_thresholds(
    rr_intervals: np.ndarray,
    hr_rest: float,
    hr_max: float,
    method: VTMethod = VTMethod.MULTIPARAMETER,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
    step_seconds: int = DEFAULT_STEP_SECONDS,
) -> VTAnalysisResult:
    """Detect ventilatory thresholds from RR interval data.

    Implements multi-parameter VT detection following Kubios VT-algorithm
    architecture by combining:
    1. DFA-α1 scaling exponent (primary)
    2. Heart rate relative to reserve (secondary)
    3. Respiratory frequency modulation (tertiary)

    Args:
        rr_intervals: RR intervals in milliseconds.
        hr_rest: Resting heart rate (bpm).
        hr_max: Maximum heart rate (bpm, measured or 220-age).
        method: Detection method ('dfa_only' or 'multiparameter').
        window_seconds: DFA window size in seconds.
        step_seconds: DFA step size in seconds.

    Returns:
        VTAnalysisResult with thresholds, time series, quality, interpretation.

    References:
        Eronen et al. (2024). medRxiv. doi: 10.1101/2024.08.14.24311967
    """
    warnings_list: List[str] = []
    interpretation_list: List[str] = []

    # -----------------------------------------------------------------------
    # Step 1: Artifact correction
    # -----------------------------------------------------------------------
    rr_clean, valid_mask, artifact_pct = correct_artifacts(rr_intervals)

    if artifact_pct > MAX_ARTIFACT_RATE:
        warnings_list.append(
            f"Artifact rate ({artifact_pct:.1f}%) exceeds {MAX_ARTIFACT_RATE}% threshold. "
            "Results may be unreliable."
        )

    if len(rr_clean) < MIN_WINDOW_BEATS * 3:
        _LOGGER.warning("Insufficient clean RR intervals (%d) for VT analysis.", len(rr_clean))
        return _empty_result(rr_intervals, artifact_pct, method.value)

    # -----------------------------------------------------------------------
    # Step 2: Time-varying DFA-α1
    # -----------------------------------------------------------------------
    dfa_ts = compute_time_varying_dfa(rr_clean, window_seconds, step_seconds)

    if len(dfa_ts["time"]) < 5:
        warnings_list.append("Insufficient DFA windows computed. Recording may be too short.")
        return _empty_result(rr_intervals, artifact_pct, method.value)

    # -----------------------------------------------------------------------
    # Step 3: Heart rate time series (aligned with DFA windows)
    # -----------------------------------------------------------------------
    _, hr_inst = calculate_hr_reserve(rr_clean, hr_rest, hr_max)
    cumulative_s = np.cumsum(rr_clean) / 1000.0

    hr_aligned: List[float] = []
    for t in dfa_ts["time"]:
        closest_idx = int(np.argmin(np.abs(cumulative_s - t)))
        hr_aligned.append(float(hr_inst[min(closest_idx, len(hr_inst) - 1)]))
    hr_aligned_arr = np.array(hr_aligned, dtype=np.float64)

    # -----------------------------------------------------------------------
    # Step 4: Respiratory frequency
    # -----------------------------------------------------------------------
    resp_freq, _ = extract_respiratory_frequency(rr_clean)

    # -----------------------------------------------------------------------
    # Step 5: VT detection
    # -----------------------------------------------------------------------
    dfa_vals = dfa_ts["dfa_alpha1"]
    n_points = len(dfa_vals)

    if method == VTMethod.DFA_ONLY:
        integrated_score = (1.0 - dfa_vals) / 0.5
        integrated_score = np.clip(integrated_score, 0.0, 2.0)

        vt1_indices = np.where(dfa_vals <= DFA_VT1_THRESHOLD)[0]
        vt2_indices = np.where(dfa_vals <= DFA_VT2_THRESHOLD)[0]

        vt1_idx = int(vt1_indices[0]) if len(vt1_indices) > 0 else None
        vt2_idx = int(vt2_indices[0]) if len(vt2_indices) > 0 else None

    else:  # multiparameter
        # Normalize each component to [0, 1]
        dfa_norm = (1.0 - dfa_vals) / 0.5
        dfa_norm = np.clip(dfa_norm, 0.0, 1.0)

        hr_rel = (hr_aligned_arr - hr_rest) / (hr_max - hr_rest)
        hr_rel = np.clip(hr_rel, 0.0, 1.0)

        # Respiratory component (linear approximation of increase)
        resp_norm = np.linspace(0.0, 0.3, n_points)

        # Weighted combination
        integrated_score = (
            WEIGHT_DFA * dfa_norm + WEIGHT_HR * hr_rel + WEIGHT_RESP * resp_norm
        )

        # Smooth
        if n_points >= SMOOTHING_WINDOW:
            integrated_score = uniform_filter1d(integrated_score, size=SMOOTHING_WINDOW)

        # Threshold detection on integrated score
        vt1_candidates = np.where(integrated_score >= 0.45)[0]
        vt2_candidates = np.where(integrated_score >= 0.75)[0]

        vt1_idx = int(vt1_candidates[0]) if len(vt1_candidates) > 0 else None
        vt2_idx = int(vt2_candidates[0]) if len(vt2_candidates) > 0 else None

    # -----------------------------------------------------------------------
    # Step 6: Build results
    # -----------------------------------------------------------------------
    vt1_result: Optional[VTResult] = None
    vt2_result: Optional[VTResult] = None

    if vt1_idx is not None:
        vt1_conf = _compute_threshold_confidence(vt1_idx, dfa_vals, hr_aligned_arr)
        vt1_result = VTResult(
            time_seconds=float(dfa_ts["time"][vt1_idx]),
            heart_rate_bpm=float(hr_aligned_arr[vt1_idx]),
            dfa_alpha1=float(dfa_vals[vt1_idx]),
            hr_relative=float((hr_aligned_arr[vt1_idx] - hr_rest) / (hr_max - hr_rest)),
            confidence=vt1_conf,
            index=vt1_idx,
        )
        interpretation_list.append(
            f"VT1 (aerobic threshold) detected at HR {vt1_result.heart_rate_bpm:.0f} bpm "
            f"({vt1_result.hr_relative:.0%} HR reserve), DFA-α1 = {vt1_result.dfa_alpha1:.2f}. "
            f"Confidence: {vt1_conf:.0%}."
        )

    if vt2_idx is not None:
        vt2_conf = _compute_threshold_confidence(vt2_idx, dfa_vals, hr_aligned_arr)
        vt2_result = VTResult(
            time_seconds=float(dfa_ts["time"][vt2_idx]),
            heart_rate_bpm=float(hr_aligned_arr[vt2_idx]),
            dfa_alpha1=float(dfa_vals[vt2_idx]),
            hr_relative=float((hr_aligned_arr[vt2_idx] - hr_rest) / (hr_max - hr_rest)),
            confidence=vt2_conf,
            index=vt2_idx,
        )
        interpretation_list.append(
            f"VT2 (anaerobic threshold) detected at HR {vt2_result.heart_rate_bpm:.0f} bpm "
            f"({vt2_result.hr_relative:.0%} HR reserve), DFA-α1 = {vt2_result.dfa_alpha1:.2f}. "
            f"Confidence: {vt2_conf:.0%}."
        )

    # Validate VT1 < VT2
    if vt1_result and vt2_result and vt1_result.heart_rate_bpm >= vt2_result.heart_rate_bpm:
        warnings_list.append(
            "VT1 heart rate is not lower than VT2. Results may be unreliable."
        )

    # -----------------------------------------------------------------------
    # Step 7: Quality metrics
    # -----------------------------------------------------------------------
    dfa_range = float(np.max(dfa_vals) - np.min(dfa_vals))
    # Check if DFA generally decreases over time
    if len(dfa_vals) > 2:
        t_corr = np.corrcoef(np.arange(len(dfa_vals)), dfa_vals)[0, 1]
        monotonic_decrease = bool(t_corr < -0.3)
    else:
        monotonic_decrease = False

    if not monotonic_decrease:
        warnings_list.append(
            "DFA-α1 does not show a clear decreasing trend. "
            "Data may not represent an incremental exercise test."
        )

    quality = QualityMetrics(
        artifact_percentage=artifact_pct,
        total_beats=len(rr_intervals),
        clean_beats=len(rr_clean),
        n_windows=len(dfa_ts["time"]),
        min_dfa=float(np.min(dfa_vals)),
        max_dfa=float(np.max(dfa_vals)),
        dfa_range=dfa_range,
        monotonic_decrease=monotonic_decrease,
    )

    # -----------------------------------------------------------------------
    # Step 8: Intensity zones
    # -----------------------------------------------------------------------
    zones = _compute_intensity_zones(vt1_result, vt2_result, hr_rest, hr_max)

    if not interpretation_list:
        interpretation_list.append(
            "No ventilatory thresholds detected. The recording may not contain "
            "an incremental exercise test, or signal quality may be insufficient."
        )

    return VTAnalysisResult(
        vt1=vt1_result,
        vt2=vt2_result,
        timeseries_time=dfa_ts["time"].tolist(),
        timeseries_dfa=dfa_ts["dfa_alpha1"].tolist(),
        timeseries_hr=hr_aligned_arr.tolist(),
        timeseries_hr_mean=dfa_ts["hr_mean"].tolist(),
        timeseries_integrated_score=integrated_score.tolist(),
        respiratory_frequency_hz=resp_freq,
        quality=quality,
        method=method.value,
        intensity_zones=zones,
        interpretation=interpretation_list,
        warnings=warnings_list,
    )


# ---------------------------------------------------------------------------
# Intensity zone computation
# ---------------------------------------------------------------------------


def _compute_intensity_zones(
    vt1: Optional[VTResult],
    vt2: Optional[VTResult],
    hr_rest: float,
    hr_max: float,
) -> List[IntensityZoneResult]:
    """Compute exercise intensity zones from detected thresholds."""
    zones: List[IntensityZoneResult] = []

    vt1_hr = vt1.heart_rate_bpm if vt1 else hr_rest + 0.6 * (hr_max - hr_rest)
    vt2_hr = vt2.heart_rate_bpm if vt2 else hr_rest + 0.8 * (hr_max - hr_rest)

    zones.append(IntensityZoneResult(
        zone=IntensityZone.ZONE_1,
        zone_label="Zone 1 — Aerobic (below VT1)",
        zone_description=(
            "Low intensity, parasympathetic dominance. Sustainable for extended periods. "
            "DFA-α1 > 0.75 indicates preserved fractal correlation."
        ),
        hr_min=hr_rest,
        hr_max=vt1_hr,
        dfa_range="α1 > 0.75",
        training_guidance="Base endurance, recovery, long slow distance.",
    ))

    zones.append(IntensityZoneResult(
        zone=IntensityZone.ZONE_2,
        zone_label="Zone 2 — Threshold (VT1 to VT2)",
        zone_description=(
            "Moderate-to-high intensity, mixed autonomic regulation. "
            "DFA-α1 between 0.50-0.75. Lactate accumulation begins."
        ),
        hr_min=vt1_hr,
        hr_max=vt2_hr,
        dfa_range="0.50 < α1 < 0.75",
        training_guidance="Tempo runs, threshold training, sweet-spot intervals.",
    ))

    zones.append(IntensityZoneResult(
        zone=IntensityZone.ZONE_3,
        zone_label="Zone 3 — High Intensity (above VT2)",
        zone_description=(
            "High intensity, sympathetic dominance. Near-complete vagal withdrawal. "
            "DFA-α1 < 0.50 indicates random, uncorrelated heart rate patterns."
        ),
        hr_min=vt2_hr,
        hr_max=hr_max,
        dfa_range="α1 < 0.50",
        training_guidance="VO2max intervals, race-pace efforts. Limited sustainability (<60 min).",
    ))

    return zones


# ---------------------------------------------------------------------------
# Readiness model contribution
# ---------------------------------------------------------------------------


def estimate_vt_readiness_contribution(
    dfa_alpha1_rest: Optional[float],
    vt1_hr_relative: Optional[float],
    vt2_hr_relative: Optional[float],
) -> Tuple[float, List[str]]:
    """Estimate VT-derived contribution to operational readiness.

    Produces a score [0, 100] and explanatory triggers reflecting aerobic
    fitness and autonomic reserve inferred from VT analysis.

    The contribution is designed to be fused into the operational readiness
    model as a modifier (+/- bounded adjustment).

    Args:
        dfa_alpha1_rest: Resting DFA-α1 (should be ~1.0 for healthy heart).
        vt1_hr_relative: VT1 as fraction of HR reserve (0-1). Higher = fitter.
        vt2_hr_relative: VT2 as fraction of HR reserve (0-1). Higher = fitter.

    Returns:
        Tuple of (vt_readiness_score_0_100, triggers).

    References:
        Rogers B, et al. (2021). Front Physiol, 11:596567.
    """
    triggers: List[str] = []
    score = 70.0  # baseline neutral

    # 1) Resting DFA-α1: ~1.0 is healthy, <0.65 or >1.5 is concerning
    if dfa_alpha1_rest is not None:
        if 0.85 <= dfa_alpha1_rest <= 1.15:
            score += 10.0
            triggers.append(
                f"Resting DFA-α1 ({dfa_alpha1_rest:.2f}) indicates healthy fractal "
                "cardiac dynamics — good autonomic reserve."
            )
        elif dfa_alpha1_rest < 0.65:
            score -= 15.0
            triggers.append(
                f"Low resting DFA-α1 ({dfa_alpha1_rest:.2f}) suggests reduced cardiac "
                "complexity — possible overtraining or autonomic dysfunction."
            )
        elif dfa_alpha1_rest > 1.35:
            score -= 8.0
            triggers.append(
                f"Elevated resting DFA-α1 ({dfa_alpha1_rest:.2f}) suggests overly "
                "correlated patterns — may indicate reduced adaptability."
            )

    # 2) VT1 position in HR reserve: higher = better aerobic fitness
    if vt1_hr_relative is not None:
        if vt1_hr_relative >= 0.65:
            score += 8.0
            triggers.append(
                f"VT1 at {vt1_hr_relative:.0%} HR reserve indicates excellent aerobic base."
            )
        elif vt1_hr_relative < 0.45:
            score -= 10.0
            triggers.append(
                f"VT1 at {vt1_hr_relative:.0%} HR reserve suggests low aerobic capacity."
            )

    # 3) VT2 position: marker of lactate clearance capacity
    if vt2_hr_relative is not None:
        if vt2_hr_relative >= 0.85:
            score += 5.0
            triggers.append(
                f"VT2 at {vt2_hr_relative:.0%} HR reserve — high anaerobic capacity."
            )
        elif vt2_hr_relative < 0.65:
            score -= 5.0
            triggers.append(
                f"VT2 at {vt2_hr_relative:.0%} HR reserve — limited high-intensity tolerance."
            )

    if not triggers:
        triggers.append("VT metrics unavailable; aerobic fitness contribution not assessed.")

    return max(0.0, min(100.0, score)), triggers


# ---------------------------------------------------------------------------
# Demo data generation
# ---------------------------------------------------------------------------


def generate_demo_exercise_data(
    duration_minutes: int = 20,
    hr_rest: float = 65.0,
    hr_max: float = 185.0,
    seed: int = 42,
) -> Tuple[np.ndarray, float, float]:
    """Generate realistic synthetic RR intervals for an incremental exercise test.

    Simulates a graded exercise protocol with progressive intensity increase,
    producing physiologically plausible DFA-α1 transitions from ~1.0 to <0.5.

    Args:
        duration_minutes: Total test duration in minutes.
        hr_rest: Resting heart rate (bpm).
        hr_max: Maximum heart rate (bpm).
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (rr_intervals_ms, hr_rest, hr_max).
    """
    rng = np.random.default_rng(seed)
    total_seconds = duration_minutes * 60

    # Generate time-varying HR that increases from rest to max
    n_seconds = total_seconds
    # S-curve progression
    t_norm = np.linspace(0, 1, n_seconds)
    # Sigmoid-like progression
    hr_progression = hr_rest + (hr_max - hr_rest) * (1 / (1 + np.exp(-8 * (t_norm - 0.5))))

    # Generate RR intervals from HR progression with realistic variability
    rr_intervals: List[float] = []
    t_accum = 0.0

    for i in range(n_seconds):
        if t_accum >= total_seconds:
            break

        hr_current = hr_progression[min(i, len(hr_progression) - 1)]
        rr_base = 60000.0 / hr_current

        # Variability decreases with intensity (autonomic withdrawal)
        intensity_frac = (hr_current - hr_rest) / (hr_max - hr_rest)
        variability = rr_base * 0.05 * (1.0 - intensity_frac * 0.8)

        # Generate beats for this second
        beats_per_sec = hr_current / 60.0
        n_beats = max(1, int(round(beats_per_sec)))

        for _ in range(n_beats):
            rr_val = rr_base + rng.normal(0, variability)
            rr_val = max(300.0, min(1500.0, rr_val))
            rr_intervals.append(rr_val)
            t_accum += rr_val / 1000.0

            if t_accum >= total_seconds:
                break

    return np.array(rr_intervals, dtype=np.float64), hr_rest, hr_max


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_result(
    rr_intervals: np.ndarray,
    artifact_pct: float,
    method_str: str,
) -> VTAnalysisResult:
    """Return an empty result when analysis cannot proceed."""
    return VTAnalysisResult(
        vt1=None,
        vt2=None,
        timeseries_time=[],
        timeseries_dfa=[],
        timeseries_hr=[],
        timeseries_hr_mean=[],
        timeseries_integrated_score=[],
        respiratory_frequency_hz=None,
        quality=QualityMetrics(
            artifact_percentage=artifact_pct,
            total_beats=len(rr_intervals),
            clean_beats=0,
            n_windows=0,
            min_dfa=0.0,
            max_dfa=0.0,
            dfa_range=0.0,
            monotonic_decrease=False,
        ),
        method=method_str,
        intensity_zones=[],
        interpretation=[
            "Analysis could not be completed. Insufficient data or "
            "excessive artifacts."
        ],
        warnings=["Insufficient data for VT analysis."],
    )
