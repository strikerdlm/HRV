"""ECG R-Peak Detection Module.

This module provides robust R-peak detection algorithms for true beat-to-beat
HRV analysis from raw ECG signals. Implements Pan-Tompkins algorithm and
template matching for artifact rejection.

Author: Dr. Diego Malpica, MD
        Aerospace Medicine Specialist
        National University of Colombia

References:
    - Pan, J., & Tompkins, W. J. (1985). A real-time QRS detection algorithm.
      IEEE transactions on biomedical engineering, (3), 230-236.
    - Hamilton, P. S., & Tompkins, W. J. (1986). Quantitative investigation of
      QRS detection rules using the MIT/BIH arrhythmia database.
      IEEE transactions on biomedical engineering, (12), 1157-1165.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray
import pandas as pd
from scipy import signal
from scipy.ndimage import uniform_filter1d

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Default ECG parameters
DEFAULT_SAMPLE_RATE: Final[float] = 250.0  # Hz
MIN_SAMPLE_RATE: Final[float] = 100.0  # Hz
MAX_SAMPLE_RATE: Final[float] = 2000.0  # Hz

# Physiological limits
MIN_HR_BPM: Final[float] = 30.0  # Minimum expected heart rate
MAX_HR_BPM: Final[float] = 220.0  # Maximum expected heart rate
MIN_RR_MS: Final[float] = 60000.0 / MAX_HR_BPM  # ~273 ms
MAX_RR_MS: Final[float] = 60000.0 / MIN_HR_BPM  # 2000 ms

# Pan-Tompkins filter parameters
PAN_TOMPKINS_LP_CUTOFF: Final[float] = 15.0  # Hz
PAN_TOMPKINS_HP_CUTOFF: Final[float] = 5.0  # Hz

# Refractory period (minimum time between beats)
REFRACTORY_PERIOD_MS: Final[float] = 200.0  # ms


class DetectionMethod(Enum):
    """Available R-peak detection methods."""
    
    PAN_TOMPKINS = "pan_tompkins"
    HAMILTON = "hamilton"
    CHRISTOV = "christov"
    ENGZEE = "engzee"
    GRADIENT = "gradient"
    WAVELET = "wavelet"


class QRSMorphology(Enum):
    """QRS complex morphology classification."""
    
    NORMAL = "normal"
    WIDE = "wide"
    NARROW = "narrow"
    ABERRANT = "aberrant"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RPeakResult:
    """Result of R-peak detection.
    
    Attributes:
        r_peak_indices: Array of R-peak sample indices.
        r_peak_times_ms: Array of R-peak times in milliseconds.
        rr_intervals_ms: Array of RR intervals in milliseconds.
        detection_confidence: Per-beat confidence scores (0-1).
        signal_quality: Overall signal quality score (0-100).
        artifacts_detected: Indices of detected artifact peaks.
        method_used: Detection method that was used.
        sample_rate: Sample rate of the input signal.
        metadata: Additional detection metadata.
    """
    
    r_peak_indices: NDArray[np.int64] = field(default_factory=lambda: np.array([], dtype=np.int64))
    r_peak_times_ms: NDArray[np.float64] = field(default_factory=lambda: np.array([], dtype=np.float64))
    rr_intervals_ms: NDArray[np.float64] = field(default_factory=lambda: np.array([], dtype=np.float64))
    detection_confidence: NDArray[np.float64] = field(default_factory=lambda: np.array([], dtype=np.float64))
    signal_quality: float = 0.0
    artifacts_detected: NDArray[np.int64] = field(default_factory=lambda: np.array([], dtype=np.int64))
    method_used: str = "unknown"
    sample_rate: float = DEFAULT_SAMPLE_RATE
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class QRSComplex:
    """Information about a single QRS complex.
    
    Attributes:
        r_peak_index: Index of the R-peak.
        q_onset_index: Index of Q-wave onset (optional).
        s_offset_index: Index of S-wave offset (optional).
        amplitude: R-peak amplitude.
        width_ms: QRS width in milliseconds.
        morphology: QRS morphology classification.
        is_artifact: Whether this complex is flagged as artifact.
        confidence: Detection confidence (0-1).
    """
    
    r_peak_index: int
    q_onset_index: int | None = None
    s_offset_index: int | None = None
    amplitude: float = 0.0
    width_ms: float = 0.0
    morphology: QRSMorphology = QRSMorphology.UNKNOWN
    is_artifact: bool = False
    confidence: float = 1.0


@dataclass(slots=True)
class ECGSignalInfo:
    """Information about the ECG signal.
    
    Attributes:
        sample_rate: Sampling rate in Hz.
        duration_seconds: Signal duration in seconds.
        n_samples: Number of samples.
        baseline_mv: Estimated baseline in mV.
        amplitude_range_mv: Signal amplitude range in mV.
        noise_level: Estimated noise level (0-1).
        has_baseline_wander: Whether baseline wander detected.
        has_powerline_noise: Whether 50/60 Hz noise detected.
    """
    
    sample_rate: float = DEFAULT_SAMPLE_RATE
    duration_seconds: float = 0.0
    n_samples: int = 0
    baseline_mv: float = 0.0
    amplitude_range_mv: float = 0.0
    noise_level: float = 0.0
    has_baseline_wander: bool = False
    has_powerline_noise: bool = False


class TemplateMatchResult(TypedDict):
    """Result of template matching."""
    
    correlation: float
    is_match: bool
    template_index: int


# ---------------------------------------------------------------------------
# Preprocessing Functions
# ---------------------------------------------------------------------------


def validate_ecg_signal(
    ecg: NDArray[np.float64],
    sample_rate: float,
) -> tuple[bool, list[str]]:
    """Validate ECG signal for R-peak detection.
    
    Args:
        ecg: Raw ECG signal array.
        sample_rate: Sampling rate in Hz.
        
    Returns:
        Tuple of (is_valid, list of warnings/errors).
    """
    warnings: list[str] = []
    is_valid = True
    
    # Check array type and shape
    if not isinstance(ecg, np.ndarray):
        warnings.append("ECG signal must be a numpy array")
        is_valid = False
        return is_valid, warnings
    
    if ecg.ndim != 1:
        warnings.append(f"ECG signal must be 1D, got {ecg.ndim}D")
        is_valid = False
        return is_valid, warnings
    
    # Check length
    if len(ecg) < sample_rate * 2:  # Minimum 2 seconds
        warnings.append("ECG signal too short (minimum 2 seconds required)")
        is_valid = False
    
    # Check sample rate
    if sample_rate < MIN_SAMPLE_RATE:
        warnings.append(f"Sample rate too low ({sample_rate} Hz), minimum {MIN_SAMPLE_RATE} Hz")
        is_valid = False
    elif sample_rate > MAX_SAMPLE_RATE:
        warnings.append(f"Sample rate too high ({sample_rate} Hz), maximum {MAX_SAMPLE_RATE} Hz")
    
    # Check for NaN/Inf values
    nan_count = np.sum(np.isnan(ecg))
    inf_count = np.sum(np.isinf(ecg))
    if nan_count > 0:
        warnings.append(f"Signal contains {nan_count} NaN values")
    if inf_count > 0:
        warnings.append(f"Signal contains {inf_count} Inf values")
        is_valid = False
    
    # Check signal variance
    if np.var(ecg[~np.isnan(ecg)]) < 1e-10:
        warnings.append("Signal has near-zero variance (possibly flat line)")
        is_valid = False
    
    return is_valid, warnings


def remove_baseline_wander(
    ecg: NDArray[np.float64],
    sample_rate: float,
    cutoff_hz: float = 0.5,
) -> NDArray[np.float64]:
    """Remove baseline wander using high-pass filter.
    
    Args:
        ecg: Raw ECG signal.
        sample_rate: Sampling rate in Hz.
        cutoff_hz: High-pass cutoff frequency.
        
    Returns:
        ECG signal with baseline wander removed.
    """
    # Design high-pass Butterworth filter
    nyquist = sample_rate / 2.0
    normalized_cutoff = cutoff_hz / nyquist
    
    if normalized_cutoff >= 1.0:
        _LOGGER.warning("Cutoff frequency too high for sample rate, skipping baseline removal")
        return ecg
    
    b, a = signal.butter(2, normalized_cutoff, btype='high')
    
    # Apply zero-phase filtering
    filtered = signal.filtfilt(b, a, ecg)
    
    return filtered


def remove_powerline_noise(
    ecg: NDArray[np.float64],
    sample_rate: float,
    powerline_freq: float = 60.0,
) -> NDArray[np.float64]:
    """Remove powerline interference using notch filter.
    
    Args:
        ecg: Raw ECG signal.
        sample_rate: Sampling rate in Hz.
        powerline_freq: Powerline frequency (50 or 60 Hz).
        
    Returns:
        ECG signal with powerline noise removed.
    """
    nyquist = sample_rate / 2.0
    
    if powerline_freq >= nyquist:
        _LOGGER.warning("Powerline frequency exceeds Nyquist, skipping noise removal")
        return ecg
    
    # Design notch filter
    q_factor = 30.0  # Quality factor
    b, a = signal.iirnotch(powerline_freq / nyquist, q_factor)
    
    # Apply zero-phase filtering
    filtered = signal.filtfilt(b, a, ecg)
    
    return filtered


def preprocess_ecg(
    ecg: NDArray[np.float64],
    sample_rate: float,
    remove_baseline: bool = True,
    remove_powerline: bool = True,
    powerline_freq: float = 60.0,
    normalize: bool = True,
) -> NDArray[np.float64]:
    """Preprocess ECG signal for R-peak detection.
    
    Args:
        ecg: Raw ECG signal.
        sample_rate: Sampling rate in Hz.
        remove_baseline: Whether to remove baseline wander.
        remove_powerline: Whether to remove powerline noise.
        powerline_freq: Powerline frequency (50 or 60 Hz).
        normalize: Whether to normalize the signal.
        
    Returns:
        Preprocessed ECG signal.
    """
    # Handle NaN values
    ecg_clean = np.copy(ecg)
    nan_mask = np.isnan(ecg_clean)
    if np.any(nan_mask):
        # Interpolate NaN values
        valid_indices = np.where(~nan_mask)[0]
        nan_indices = np.where(nan_mask)[0]
        if len(valid_indices) > 1:
            ecg_clean[nan_mask] = np.interp(nan_indices, valid_indices, ecg_clean[valid_indices])
        else:
            ecg_clean[nan_mask] = 0.0
    
    # Remove baseline wander
    if remove_baseline:
        ecg_clean = remove_baseline_wander(ecg_clean, sample_rate)
    
    # Remove powerline noise
    if remove_powerline:
        ecg_clean = remove_powerline_noise(ecg_clean, sample_rate, powerline_freq)
    
    # Normalize
    if normalize:
        std = np.std(ecg_clean)
        if std > 0:
            ecg_clean = (ecg_clean - np.mean(ecg_clean)) / std
    
    return ecg_clean


# ---------------------------------------------------------------------------
# Pan-Tompkins Algorithm
# ---------------------------------------------------------------------------


def pan_tompkins_detector(
    ecg: NDArray[np.float64],
    sample_rate: float,
) -> RPeakResult:
    """Detect R-peaks using the Pan-Tompkins algorithm.
    
    This is the reference implementation of the Pan-Tompkins QRS detection
    algorithm (1985). The algorithm consists of:
    1. Band-pass filtering (5-15 Hz)
    2. Differentiation
    3. Squaring
    4. Moving window integration
    5. Adaptive thresholding
    
    Args:
        ecg: Preprocessed ECG signal.
        sample_rate: Sampling rate in Hz.
        
    Returns:
        RPeakResult with detected R-peaks and metadata.
    """
    n_samples = len(ecg)
    
    # Step 1: Band-pass filter (5-15 Hz)
    nyquist = sample_rate / 2.0
    low_cut = PAN_TOMPKINS_HP_CUTOFF / nyquist
    high_cut = PAN_TOMPKINS_LP_CUTOFF / nyquist
    
    # Ensure valid filter parameters
    low_cut = max(0.01, min(low_cut, 0.99))
    high_cut = max(low_cut + 0.01, min(high_cut, 0.99))
    
    b, a = signal.butter(1, [low_cut, high_cut], btype='band')
    filtered = signal.filtfilt(b, a, ecg)
    
    # Step 2: Differentiation
    # 5-point derivative as per original algorithm
    diff = np.zeros_like(filtered)
    diff[2:-2] = (
        -filtered[:-4] 
        - 2 * filtered[1:-3] 
        + 2 * filtered[3:-1] 
        + filtered[4:]
    ) / 8.0
    
    # Step 3: Squaring
    squared = diff ** 2
    
    # Step 4: Moving window integration
    # Window width = 150ms as per original algorithm
    window_width = int(0.150 * sample_rate)
    if window_width < 1:
        window_width = 1
    
    integrated = uniform_filter1d(squared, size=window_width, mode='constant')
    
    # Step 5: Adaptive thresholding
    r_peaks = _adaptive_threshold_detection(integrated, sample_rate)
    
    # Refine peak locations to actual R-peaks in original signal
    r_peaks = _refine_peak_locations(ecg, r_peaks, sample_rate)
    
    # Compute RR intervals
    rr_intervals_ms = np.diff(r_peaks) / sample_rate * 1000.0
    
    # Compute detection confidence based on signal quality
    confidence = _compute_detection_confidence(ecg, r_peaks, sample_rate)
    
    # Compute signal quality
    signal_quality = _assess_signal_quality(ecg, sample_rate)
    
    # Detect artifacts
    artifacts = _detect_artifact_peaks(rr_intervals_ms)
    
    return RPeakResult(
        r_peak_indices=r_peaks,
        r_peak_times_ms=r_peaks / sample_rate * 1000.0,
        rr_intervals_ms=rr_intervals_ms,
        detection_confidence=confidence,
        signal_quality=signal_quality,
        artifacts_detected=np.array(artifacts, dtype=np.int64),
        method_used=DetectionMethod.PAN_TOMPKINS.value,
        sample_rate=sample_rate,
        metadata={
            "n_samples": n_samples,
            "duration_s": n_samples / sample_rate,
            "n_peaks_detected": len(r_peaks),
            "mean_hr_bpm": 60000.0 / np.mean(rr_intervals_ms) if len(rr_intervals_ms) > 0 else 0.0,
        },
    )


def _adaptive_threshold_detection(
    integrated: NDArray[np.float64],
    sample_rate: float,
) -> NDArray[np.int64]:
    """Adaptive threshold detection for Pan-Tompkins.
    
    Args:
        integrated: Integrated signal from Pan-Tompkins preprocessing.
        sample_rate: Sampling rate in Hz.
        
    Returns:
        Array of detected peak indices.
    """
    # Initialize thresholds
    spki = np.max(integrated[:int(2 * sample_rate)]) * 0.25  # Signal peak
    npki = np.mean(integrated[:int(2 * sample_rate)]) * 0.5  # Noise peak
    threshold1 = npki + 0.25 * (spki - npki)
    threshold2 = 0.5 * threshold1
    
    # Refractory period in samples
    refractory_samples = int(REFRACTORY_PERIOD_MS * sample_rate / 1000.0)
    
    # Find peaks above threshold
    peaks: list[int] = []
    last_peak = -refractory_samples
    
    # Use scipy to find all local maxima
    local_maxima, _ = signal.find_peaks(integrated, distance=refractory_samples)
    
    for peak in local_maxima:
        if peak - last_peak < refractory_samples:
            continue
            
        if integrated[peak] > threshold1:
            # Signal peak
            peaks.append(peak)
            spki = 0.125 * integrated[peak] + 0.875 * spki
            last_peak = peak
        elif integrated[peak] > threshold2:
            # Noise peak or missed beat - search back
            npki = 0.125 * integrated[peak] + 0.875 * npki
        
        # Update threshold
        threshold1 = npki + 0.25 * (spki - npki)
        threshold2 = 0.5 * threshold1
    
    return np.array(peaks, dtype=np.int64)


def _refine_peak_locations(
    ecg: NDArray[np.float64],
    peaks: NDArray[np.int64],
    sample_rate: float,
) -> NDArray[np.int64]:
    """Refine peak locations to actual R-peaks in original signal.
    
    Args:
        ecg: Original ECG signal.
        peaks: Initial peak estimates.
        sample_rate: Sampling rate in Hz.
        
    Returns:
        Refined peak indices.
    """
    if len(peaks) == 0:
        return peaks
    
    # Search window: ±75ms around each peak
    search_window = int(0.075 * sample_rate)
    refined_peaks: list[int] = []
    
    for peak in peaks:
        # Define search range
        start = max(0, peak - search_window)
        end = min(len(ecg), peak + search_window + 1)
        
        # Find maximum in search window
        local_segment = ecg[start:end]
        local_max_idx = np.argmax(np.abs(local_segment))
        
        refined_peaks.append(start + local_max_idx)
    
    return np.array(refined_peaks, dtype=np.int64)


# ---------------------------------------------------------------------------
# Hamilton Algorithm
# ---------------------------------------------------------------------------


def hamilton_detector(
    ecg: NDArray[np.float64],
    sample_rate: float,
) -> RPeakResult:
    """Detect R-peaks using the Hamilton-Tompkins algorithm.
    
    Enhanced version of Pan-Tompkins with additional search-back logic.
    
    Args:
        ecg: Preprocessed ECG signal.
        sample_rate: Sampling rate in Hz.
        
    Returns:
        RPeakResult with detected R-peaks and metadata.
    """
    # Use Pan-Tompkins as base
    result = pan_tompkins_detector(ecg, sample_rate)
    
    # Apply Hamilton's search-back enhancement
    r_peaks = result.r_peak_indices.copy()
    
    # Check for missed beats (RR interval > 1.5x median)
    if len(r_peaks) > 2:
        rr_intervals = np.diff(r_peaks)
        median_rr = np.median(rr_intervals)
        
        new_peaks: list[int] = [r_peaks[0]]
        
        for i in range(1, len(r_peaks)):
            rr = r_peaks[i] - new_peaks[-1]
            
            if rr > 1.5 * median_rr:
                # Search back for missed beat
                search_start = new_peaks[-1] + int(0.2 * median_rr)
                search_end = r_peaks[i] - int(0.2 * median_rr)
                
                if search_end > search_start:
                    segment = ecg[search_start:search_end]
                    local_peaks, _ = signal.find_peaks(np.abs(segment), distance=int(0.3 * median_rr))
                    
                    if len(local_peaks) > 0:
                        # Take the largest peak as missed beat
                        peak_heights = np.abs(segment[local_peaks])
                        best_peak = local_peaks[np.argmax(peak_heights)]
                        new_peaks.append(search_start + best_peak)
            
            new_peaks.append(r_peaks[i])
        
        r_peaks = np.array(sorted(new_peaks), dtype=np.int64)
    
    # Update result
    rr_intervals_ms = np.diff(r_peaks) / sample_rate * 1000.0
    
    return RPeakResult(
        r_peak_indices=r_peaks,
        r_peak_times_ms=r_peaks / sample_rate * 1000.0,
        rr_intervals_ms=rr_intervals_ms,
        detection_confidence=result.detection_confidence,
        signal_quality=result.signal_quality,
        artifacts_detected=_detect_artifact_peaks(rr_intervals_ms),
        method_used=DetectionMethod.HAMILTON.value,
        sample_rate=sample_rate,
        metadata={
            "n_samples": len(ecg),
            "duration_s": len(ecg) / sample_rate,
            "n_peaks_detected": len(r_peaks),
            "mean_hr_bpm": 60000.0 / np.mean(rr_intervals_ms) if len(rr_intervals_ms) > 0 else 0.0,
        },
    )


# ---------------------------------------------------------------------------
# Gradient-Based Detector
# ---------------------------------------------------------------------------


def gradient_detector(
    ecg: NDArray[np.float64],
    sample_rate: float,
) -> RPeakResult:
    """Detect R-peaks using gradient-based method.
    
    Simple but effective method based on finding steep gradients
    characteristic of QRS complexes.
    
    Args:
        ecg: Preprocessed ECG signal.
        sample_rate: Sampling rate in Hz.
        
    Returns:
        RPeakResult with detected R-peaks and metadata.
    """
    # Compute gradient
    gradient = np.gradient(ecg)
    
    # Square the gradient to emphasize steep slopes
    gradient_squared = gradient ** 2
    
    # Smooth with moving average
    window = int(0.05 * sample_rate)  # 50ms window
    if window < 1:
        window = 1
    smoothed = uniform_filter1d(gradient_squared, size=window)
    
    # Find peaks
    min_distance = int(REFRACTORY_PERIOD_MS * sample_rate / 1000.0)
    peaks, properties = signal.find_peaks(
        smoothed,
        distance=min_distance,
        height=np.percentile(smoothed, 80),
    )
    
    # Refine to actual R-peaks
    r_peaks = _refine_peak_locations(ecg, peaks, sample_rate)
    
    # Compute RR intervals
    rr_intervals_ms = np.diff(r_peaks) / sample_rate * 1000.0
    
    return RPeakResult(
        r_peak_indices=r_peaks,
        r_peak_times_ms=r_peaks / sample_rate * 1000.0,
        rr_intervals_ms=rr_intervals_ms,
        detection_confidence=_compute_detection_confidence(ecg, r_peaks, sample_rate),
        signal_quality=_assess_signal_quality(ecg, sample_rate),
        artifacts_detected=_detect_artifact_peaks(rr_intervals_ms),
        method_used=DetectionMethod.GRADIENT.value,
        sample_rate=sample_rate,
        metadata={
            "n_samples": len(ecg),
            "duration_s": len(ecg) / sample_rate,
            "n_peaks_detected": len(r_peaks),
            "mean_hr_bpm": 60000.0 / np.mean(rr_intervals_ms) if len(rr_intervals_ms) > 0 else 0.0,
        },
    )


# ---------------------------------------------------------------------------
# Template Matching
# ---------------------------------------------------------------------------


def create_qrs_template(
    ecg: NDArray[np.float64],
    r_peaks: NDArray[np.int64],
    sample_rate: float,
    template_width_ms: float = 200.0,
) -> NDArray[np.float64]:
    """Create QRS template from detected R-peaks.
    
    Creates an average QRS template by aligning and averaging
    multiple QRS complexes.
    
    Args:
        ecg: ECG signal.
        r_peaks: Detected R-peak indices.
        sample_rate: Sampling rate in Hz.
        template_width_ms: Template width in milliseconds.
        
    Returns:
        Average QRS template.
    """
    half_width = int(template_width_ms * sample_rate / 2000.0)
    templates: list[NDArray[np.float64]] = []
    
    for peak in r_peaks:
        start = peak - half_width
        end = peak + half_width
        
        if start >= 0 and end < len(ecg):
            template = ecg[start:end]
            # Normalize template
            template = (template - np.mean(template)) / (np.std(template) + 1e-10)
            templates.append(template)
    
    if not templates:
        return np.zeros(2 * half_width)
    
    # Average templates
    return np.mean(templates, axis=0)


def template_match_verification(
    ecg: NDArray[np.float64],
    r_peaks: NDArray[np.int64],
    template: NDArray[np.float64],
    sample_rate: float,
    threshold: float = 0.6,
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Verify R-peaks using template matching.
    
    Args:
        ecg: ECG signal.
        r_peaks: Detected R-peak indices.
        template: QRS template.
        sample_rate: Sampling rate in Hz.
        threshold: Correlation threshold for acceptance.
        
    Returns:
        Tuple of (verified_peaks, rejected_peaks).
    """
    half_width = len(template) // 2
    verified: list[int] = []
    rejected: list[int] = []
    
    for peak in r_peaks:
        start = peak - half_width
        end = peak + half_width
        
        if start >= 0 and end < len(ecg):
            segment = ecg[start:end]
            # Normalize segment
            segment_norm = (segment - np.mean(segment)) / (np.std(segment) + 1e-10)
            
            # Compute correlation
            correlation = np.corrcoef(segment_norm, template)[0, 1]
            
            if correlation >= threshold:
                verified.append(peak)
            else:
                rejected.append(peak)
        else:
            # Edge peaks - accept with lower confidence
            verified.append(peak)
    
    return np.array(verified, dtype=np.int64), np.array(rejected, dtype=np.int64)


# ---------------------------------------------------------------------------
# Quality Assessment
# ---------------------------------------------------------------------------


def _compute_detection_confidence(
    ecg: NDArray[np.float64],
    r_peaks: NDArray[np.int64],
    sample_rate: float,
) -> NDArray[np.float64]:
    """Compute per-beat detection confidence.
    
    Args:
        ecg: ECG signal.
        r_peaks: Detected R-peak indices.
        sample_rate: Sampling rate in Hz.
        
    Returns:
        Array of confidence scores (0-1) for each beat.
    """
    if len(r_peaks) == 0:
        return np.array([], dtype=np.float64)
    
    confidence = np.ones(len(r_peaks), dtype=np.float64)
    
    if len(r_peaks) < 2:
        return confidence
    
    # Compute RR intervals
    rr_intervals = np.diff(r_peaks)
    median_rr = np.median(rr_intervals)
    
    # Reduce confidence for unusual RR intervals
    for i in range(len(r_peaks)):
        if i == 0:
            rr = rr_intervals[0]
        elif i == len(r_peaks) - 1:
            rr = rr_intervals[-1]
        else:
            rr = (rr_intervals[i-1] + rr_intervals[i]) / 2
        
        # Penalize RR intervals far from median
        rr_ratio = rr / median_rr
        if rr_ratio < 0.6 or rr_ratio > 1.8:
            confidence[i] *= 0.5
        elif rr_ratio < 0.8 or rr_ratio > 1.3:
            confidence[i] *= 0.8
    
    # Reduce confidence for low-amplitude peaks
    if len(r_peaks) > 0:
        peak_amplitudes = np.abs(ecg[r_peaks])
        median_amplitude = np.median(peak_amplitudes)
        
        for i, amp in enumerate(peak_amplitudes):
            if amp < 0.5 * median_amplitude:
                confidence[i] *= 0.6
    
    return confidence


def _assess_signal_quality(
    ecg: NDArray[np.float64],
    sample_rate: float,
) -> float:
    """Assess overall ECG signal quality.
    
    Args:
        ecg: ECG signal.
        sample_rate: Sampling rate in Hz.
        
    Returns:
        Quality score from 0 to 100.
    """
    quality = 100.0
    
    # Check for saturation
    max_val = np.max(np.abs(ecg))
    if max_val > 5.0:  # Assuming normalized signal
        quality -= 20
    
    # Check for baseline stability
    # Use median filter to estimate baseline
    window = int(0.6 * sample_rate)  # 600ms window
    if window > 1:
        baseline = signal.medfilt(ecg, kernel_size=window if window % 2 == 1 else window + 1)
        baseline_variation = np.std(baseline)
        if baseline_variation > 0.5:
            quality -= 15
    
    # Check for high-frequency noise
    # Estimate noise in 150-250 Hz band (should be minimal)
    nyquist = sample_rate / 2.0
    if nyquist > 150:
        b, a = signal.butter(2, [min(150, nyquist - 1) / nyquist, min(250, nyquist - 1) / nyquist], btype='band')
        try:
            high_freq = signal.filtfilt(b, a, ecg)
            noise_power = np.var(high_freq)
            signal_power = np.var(ecg)
            if signal_power > 0:
                snr = 10 * np.log10(signal_power / (noise_power + 1e-10))
                if snr < 10:
                    quality -= 20
                elif snr < 20:
                    quality -= 10
        except Exception:
            pass  # Filter may fail for some signals
    
    # Check for flat segments
    diff_signal = np.abs(np.diff(ecg))
    flat_ratio = np.sum(diff_signal < 0.001) / len(diff_signal)
    if flat_ratio > 0.1:
        quality -= 15
    
    return max(0.0, min(100.0, quality))


def _detect_artifact_peaks(
    rr_intervals_ms: NDArray[np.float64],
) -> list[int]:
    """Detect artifact peaks based on RR interval analysis.
    
    Args:
        rr_intervals_ms: RR intervals in milliseconds.
        
    Returns:
        List of artifact peak indices.
    """
    if len(rr_intervals_ms) < 3:
        return []
    
    artifacts: list[int] = []
    median_rr = np.median(rr_intervals_ms)
    
    for i, rr in enumerate(rr_intervals_ms):
        # Flag physiologically impossible intervals
        if rr < MIN_RR_MS or rr > MAX_RR_MS:
            artifacts.append(i)
            continue
        
        # Flag intervals far from median
        if rr < 0.4 * median_rr or rr > 2.2 * median_rr:
            artifacts.append(i)
    
    return artifacts


# ---------------------------------------------------------------------------
# Main Detection Function
# ---------------------------------------------------------------------------


def detect_r_peaks(
    ecg: NDArray[np.float64],
    sample_rate: float,
    method: DetectionMethod = DetectionMethod.PAN_TOMPKINS,
    preprocess: bool = True,
    use_template_matching: bool = True,
    template_threshold: float = 0.6,
) -> RPeakResult:
    """Detect R-peaks in ECG signal.
    
    Main entry point for R-peak detection. Supports multiple detection
    algorithms and optional template matching verification.
    
    Args:
        ecg: Raw ECG signal.
        sample_rate: Sampling rate in Hz.
        method: Detection method to use.
        preprocess: Whether to preprocess the signal.
        use_template_matching: Whether to verify peaks with template matching.
        template_threshold: Correlation threshold for template matching.
        
    Returns:
        RPeakResult with detected R-peaks and metadata.
        
    Raises:
        ValueError: If signal validation fails.
    """
    # Validate input
    is_valid, warnings = validate_ecg_signal(ecg, sample_rate)
    if not is_valid:
        raise ValueError(f"Invalid ECG signal: {', '.join(warnings)}")
    
    for warning in warnings:
        _LOGGER.warning(warning)
    
    # Preprocess if requested
    if preprocess:
        ecg_processed = preprocess_ecg(ecg, sample_rate)
    else:
        ecg_processed = np.copy(ecg)
    
    # Run detection
    if method == DetectionMethod.PAN_TOMPKINS:
        result = pan_tompkins_detector(ecg_processed, sample_rate)
    elif method == DetectionMethod.HAMILTON:
        result = hamilton_detector(ecg_processed, sample_rate)
    elif method == DetectionMethod.GRADIENT:
        result = gradient_detector(ecg_processed, sample_rate)
    else:
        # Default to Pan-Tompkins
        result = pan_tompkins_detector(ecg_processed, sample_rate)
    
    # Template matching verification
    if use_template_matching and len(result.r_peak_indices) > 5:
        template = create_qrs_template(ecg_processed, result.r_peak_indices, sample_rate)
        verified, rejected = template_match_verification(
            ecg_processed,
            result.r_peak_indices,
            template,
            sample_rate,
            threshold=template_threshold,
        )
        
        # Update result with verified peaks
        if len(verified) > 0:
            rr_intervals_ms = np.diff(verified) / sample_rate * 1000.0
            
            # Combine artifacts: original artifacts + template-rejected peaks
            all_artifacts = list(result.artifacts_detected)
            for rej_idx in rejected:
                # Find index in original array
                for i, orig_idx in enumerate(result.r_peak_indices):
                    if orig_idx == rej_idx and i not in all_artifacts:
                        all_artifacts.append(i)
            
            result = RPeakResult(
                r_peak_indices=verified,
                r_peak_times_ms=verified / sample_rate * 1000.0,
                rr_intervals_ms=rr_intervals_ms,
                detection_confidence=_compute_detection_confidence(ecg_processed, verified, sample_rate),
                signal_quality=result.signal_quality,
                artifacts_detected=np.array(sorted(set(all_artifacts)), dtype=np.int64),
                method_used=result.method_used,
                sample_rate=sample_rate,
                metadata={
                    **result.metadata,
                    "template_matching_applied": True,
                    "template_rejected_count": len(rejected),
                },
            )
    
    return result


def extract_rr_intervals_from_ecg(
    ecg: NDArray[np.float64],
    sample_rate: float,
    method: DetectionMethod = DetectionMethod.PAN_TOMPKINS,
) -> tuple[NDArray[np.float64], RPeakResult]:
    """Extract RR intervals from raw ECG signal.
    
    Convenience function that returns just the RR intervals and
    the full detection result.
    
    Args:
        ecg: Raw ECG signal.
        sample_rate: Sampling rate in Hz.
        method: Detection method to use.
        
    Returns:
        Tuple of (RR intervals in ms, RPeakResult).
    """
    result = detect_r_peaks(ecg, sample_rate, method)
    return result.rr_intervals_ms, result


# ---------------------------------------------------------------------------
# QRS Morphology Analysis
# ---------------------------------------------------------------------------


def analyze_qrs_morphology(
    ecg: NDArray[np.float64],
    r_peak: int,
    sample_rate: float,
) -> QRSComplex:
    """Analyze QRS complex morphology at a given R-peak.
    
    Args:
        ecg: ECG signal.
        r_peak: R-peak index.
        sample_rate: Sampling rate in Hz.
        
    Returns:
        QRSComplex with morphology information.
    """
    # Search windows
    q_search_ms = 50  # Search Q wave up to 50ms before R
    s_search_ms = 80  # Search S wave up to 80ms after R
    
    q_search_samples = int(q_search_ms * sample_rate / 1000)
    s_search_samples = int(s_search_ms * sample_rate / 1000)
    
    # Find Q onset
    q_start = max(0, r_peak - q_search_samples)
    q_segment = ecg[q_start:r_peak]
    if len(q_segment) > 0:
        # Find minimum (Q wave trough) before R
        q_min_idx = np.argmin(q_segment)
        q_onset = q_start + q_min_idx
    else:
        q_onset = None
    
    # Find S offset
    s_end = min(len(ecg), r_peak + s_search_samples)
    s_segment = ecg[r_peak:s_end]
    if len(s_segment) > 0:
        # Find where signal returns to baseline after S wave
        baseline = np.mean(ecg[max(0, r_peak - int(0.3 * sample_rate)):r_peak - q_search_samples])
        
        # Find S wave trough
        s_min_idx = np.argmin(s_segment)
        
        # Find return to baseline after S
        for i in range(s_min_idx, len(s_segment)):
            if s_segment[i] >= baseline:
                s_offset = r_peak + i
                break
        else:
            s_offset = r_peak + len(s_segment) - 1
    else:
        s_offset = None
    
    # Compute QRS width
    if q_onset is not None and s_offset is not None:
        width_samples = s_offset - q_onset
        width_ms = width_samples / sample_rate * 1000
    else:
        width_ms = 0.0
    
    # Classify morphology
    if width_ms < 80:
        morphology = QRSMorphology.NARROW
    elif width_ms > 120:
        morphology = QRSMorphology.WIDE
    elif 80 <= width_ms <= 120:
        morphology = QRSMorphology.NORMAL
    else:
        morphology = QRSMorphology.UNKNOWN
    
    return QRSComplex(
        r_peak_index=r_peak,
        q_onset_index=q_onset,
        s_offset_index=s_offset,
        amplitude=float(ecg[r_peak]),
        width_ms=width_ms,
        morphology=morphology,
        is_artifact=False,
        confidence=1.0,
    )


# ---------------------------------------------------------------------------
# Batch Processing
# ---------------------------------------------------------------------------


def process_ecg_batch(
    ecg_signals: list[NDArray[np.float64]],
    sample_rates: list[float],
    method: DetectionMethod = DetectionMethod.PAN_TOMPKINS,
) -> list[RPeakResult]:
    """Process multiple ECG signals in batch.
    
    Args:
        ecg_signals: List of ECG signal arrays.
        sample_rates: List of sample rates corresponding to each signal.
        method: Detection method to use.
        
    Returns:
        List of RPeakResult for each signal.
    """
    if len(ecg_signals) != len(sample_rates):
        raise ValueError("Number of signals must match number of sample rates")
    
    results: list[RPeakResult] = []
    
    for i, (ecg, sr) in enumerate(zip(ecg_signals, sample_rates)):
        try:
            result = detect_r_peaks(ecg, sr, method)
            results.append(result)
        except Exception as exc:
            _LOGGER.error("Failed to process signal %d: %s", i, exc)
            # Return empty result for failed signals
            results.append(RPeakResult(
                method_used=method.value,
                sample_rate=sr,
                metadata={"error": str(exc)},
            ))
    
    return results


# ---------------------------------------------------------------------------
# Export Functions
# ---------------------------------------------------------------------------


def rpeak_result_to_dataframe(result: RPeakResult) -> pd.DataFrame:
    """Convert RPeakResult to pandas DataFrame.
    
    Args:
        result: R-peak detection result.
        
    Returns:
        DataFrame with peak information.
    """
    n_peaks = len(result.r_peak_indices)
    
    data = {
        "peak_index": result.r_peak_indices,
        "peak_time_ms": result.r_peak_times_ms,
        "confidence": result.detection_confidence if len(result.detection_confidence) == n_peaks else [1.0] * n_peaks,
        "is_artifact": [i in result.artifacts_detected for i in range(n_peaks)],
    }
    
    # Add RR intervals (shifted by 1 since RR is between consecutive beats)
    if len(result.rr_intervals_ms) == n_peaks - 1:
        data["rr_interval_ms"] = [np.nan] + list(result.rr_intervals_ms)
    
    return pd.DataFrame(data)


def export_rr_intervals(
    result: RPeakResult,
    output_path: str,
    format: str = "txt",
) -> None:
    """Export RR intervals to file.
    
    Args:
        result: R-peak detection result.
        output_path: Output file path.
        format: Output format ("txt", "csv", "json").
    """
    rr = result.rr_intervals_ms
    
    if format == "txt":
        np.savetxt(output_path, rr, fmt="%.1f")
    elif format == "csv":
        df = pd.DataFrame({"rr_interval_ms": rr})
        df.to_csv(output_path, index=False)
    elif format == "json":
        import json
        with open(output_path, "w") as f:
            json.dump({"rr_intervals_ms": rr.tolist()}, f)
    else:
        raise ValueError(f"Unknown format: {format}")
    
    _LOGGER.info("Exported %d RR intervals to %s", len(rr), output_path)

