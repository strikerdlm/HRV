"""Machine Learning Predictions Module.

This module provides ML-based prediction models for clinical outcomes
based on HRV and physiological data, including atrial fibrillation risk,
sudden cardiac death risk stratification, and sleep apnea screening.

Author: Dr. Diego Malpica, MD
        Aerospace Medicine Specialist
        National University of Colombia

References:
    - Gilon, C., et al. (2024). Machine learning-based atrial fibrillation onset
      prediction using heart rate variability geometric analysis.
    - Chen, W., et al. (2024). Achieving real-time prediction of paroxysmal
      atrial fibrillation onset by CNN on R-R interval sequences.
    - Alreshidi, F., et al. (2024). Fed-CL - atrial fibrillation prediction
      system using ECG signals employing federated learning.
    - Costa, M. D., et al. (2017). Heart rate fragmentation: A new approach
      to the analysis of cardiac interbeat interval dynamics.
    - PROOF-AF Study. (2025). Heart rate fragmentation and DFA α1 predict
      atrial fibrillation. European Heart Journal Open.

DISCLAIMER: These models are for research and educational purposes only.
They should NOT be used for clinical diagnosis without validation by
healthcare professionals. Always consult a qualified physician for
medical decisions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from enum import Enum
from typing import Any, Final

import numpy as np
from numpy.typing import NDArray
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Risk thresholds (based on published literature)
AF_RISK_LOW_THRESHOLD: Final[float] = 0.3
AF_RISK_MODERATE_THRESHOLD: Final[float] = 0.6
AF_RISK_HIGH_THRESHOLD: Final[float] = 0.8

SCD_RISK_LOW_THRESHOLD: Final[float] = 0.2
SCD_RISK_MODERATE_THRESHOLD: Final[float] = 0.5

APNEA_AHI_MILD_THRESHOLD: Final[float] = 5.0
APNEA_AHI_MODERATE_THRESHOLD: Final[float] = 15.0
APNEA_AHI_SEVERE_THRESHOLD: Final[float] = 30.0


class RiskLevel(Enum):
    """Risk level classification."""
    
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
    UNKNOWN = "unknown"


class AFType(Enum):
    """Atrial fibrillation type."""
    
    PAROXYSMAL = "paroxysmal"
    PERSISTENT = "persistent"
    PERMANENT = "permanent"
    UNKNOWN = "unknown"


class ApneaSeverity(Enum):
    """Sleep apnea severity classification."""
    
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class HRVFeatures:
    """HRV features for ML prediction.
    
    Attributes:
        rmssd_ms: RMSSD in milliseconds.
        sdnn_ms: SDNN in milliseconds.
        pnn50: pNN50 percentage.
        mean_hr_bpm: Mean heart rate.
        sdsd_ms: SDSD in milliseconds.
        cv_rr: Coefficient of variation of RR intervals.
        lf_power: LF power (ms²).
        hf_power: HF power (ms²).
        lf_hf_ratio: LF/HF ratio.
        vlf_power: VLF power (ms²).
        total_power: Total power (ms²).
        sd1: Poincaré SD1.
        sd2: Poincaré SD2.
        sd1_sd2_ratio: SD1/SD2 ratio.
        dfa_alpha1: DFA short-term scaling exponent.
        dfa_alpha2: DFA long-term scaling exponent.
        sample_entropy: Sample entropy.
        approximate_entropy: Approximate entropy.
        pip: Percentage of inflection points (fragmentation).
        ials: Inverse average segment length.
        pss: Percentage of short segments.
        w3: 3-variation word frequency.
        tinn: Triangular interpolation of NN histogram.
        hrv_triangular_index: HRV triangular index.
    """
    
    rmssd_ms: float = 0.0
    sdnn_ms: float = 0.0
    pnn50: float = 0.0
    mean_hr_bpm: float = 0.0
    sdsd_ms: float = 0.0
    cv_rr: float = 0.0
    lf_power: float = 0.0
    hf_power: float = 0.0
    lf_hf_ratio: float = 0.0
    vlf_power: float = 0.0
    total_power: float = 0.0
    sd1: float = 0.0
    sd2: float = 0.0
    sd1_sd2_ratio: float = 0.0
    dfa_alpha1: float = 0.0
    dfa_alpha2: float = 0.0
    sample_entropy: float = 0.0
    approximate_entropy: float = 0.0
    pip: float = 0.0
    ials: float = 0.0
    pss: float = 0.0
    w3: float = 0.0
    tinn: float = 0.0
    hrv_triangular_index: float = 0.0


@dataclass(slots=True)
class AFRiskPrediction:
    """Atrial fibrillation risk prediction.
    
    Attributes:
        risk_score: Risk score (0-1).
        risk_level: Risk level classification.
        af_type_predicted: Predicted AF type if at risk.
        key_risk_factors: List of key risk factors.
        protective_factors: List of protective factors.
        confidence: Prediction confidence (0-1).
        recommendations: List of recommendations.
        model_version: Model version used.
        timestamp: Prediction timestamp.
    """
    
    risk_score: float
    risk_level: RiskLevel
    af_type_predicted: AFType = AFType.UNKNOWN
    key_risk_factors: list[str] = field(default_factory=list)
    protective_factors: list[str] = field(default_factory=list)
    confidence: float = 0.0
    recommendations: list[str] = field(default_factory=list)
    model_version: str = "1.0.0"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class SCDRiskPrediction:
    """Sudden cardiac death risk prediction.
    
    Attributes:
        risk_score: Risk score (0-1).
        risk_level: Risk level classification.
        key_risk_factors: List of key risk factors.
        autonomic_dysfunction_score: Autonomic dysfunction severity.
        confidence: Prediction confidence (0-1).
        recommendations: List of recommendations.
        model_version: Model version used.
        timestamp: Prediction timestamp.
    """
    
    risk_score: float
    risk_level: RiskLevel
    key_risk_factors: list[str] = field(default_factory=list)
    autonomic_dysfunction_score: float = 0.0
    confidence: float = 0.0
    recommendations: list[str] = field(default_factory=list)
    model_version: str = "1.0.0"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class SleepApneaPrediction:
    """Sleep apnea screening prediction.
    
    Attributes:
        predicted_ahi: Predicted AHI.
        severity: Predicted severity.
        probability_apnea: Probability of sleep apnea.
        key_indicators: List of key indicators.
        confidence: Prediction confidence (0-1).
        recommendations: List of recommendations.
        model_version: Model version used.
        timestamp: Prediction timestamp.
    """
    
    predicted_ahi: float
    severity: ApneaSeverity
    probability_apnea: float
    key_indicators: list[str] = field(default_factory=list)
    confidence: float = 0.0
    recommendations: list[str] = field(default_factory=list)
    model_version: str = "1.0.0"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class StressDetection:
    """Stress detection from HRV.
    
    Attributes:
        stress_score: Stress score (0-100).
        stress_level: Stress level classification.
        autonomic_balance: Sympathovagal balance indicator.
        key_indicators: List of key stress indicators.
        recommendations: List of recommendations.
        confidence: Detection confidence (0-1).
    """
    
    stress_score: float
    stress_level: str
    autonomic_balance: str
    key_indicators: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# Feature Extraction
# ---------------------------------------------------------------------------


def extract_hrv_features(
    rr_intervals_ms: NDArray[np.float64],
    sample_rate: float = 4.0,
) -> HRVFeatures:
    """Extract HRV features from RR intervals.
    
    Args:
        rr_intervals_ms: RR intervals in milliseconds.
        sample_rate: Resampling rate for frequency analysis.
        
    Returns:
        HRVFeatures with computed metrics.
    """
    if len(rr_intervals_ms) < 30:
        return HRVFeatures()
    
    rr = np.array(rr_intervals_ms, dtype=np.float64)
    
    # Time-domain metrics
    mean_rr = np.mean(rr)
    mean_hr = 60000.0 / mean_rr if mean_rr > 0 else 0
    sdnn = np.std(rr, ddof=1)
    
    diff_rr = np.diff(rr)
    rmssd = np.sqrt(np.mean(diff_rr ** 2))
    sdsd = np.std(diff_rr, ddof=1)
    pnn50 = np.sum(np.abs(diff_rr) > 50) / len(diff_rr) * 100 if len(diff_rr) > 0 else 0
    cv_rr = sdnn / mean_rr * 100 if mean_rr > 0 else 0
    
    # Poincaré metrics
    sd1 = np.std(diff_rr / np.sqrt(2), ddof=1)
    sd2 = np.sqrt(2 * sdnn ** 2 - sd1 ** 2) if sdnn > sd1 else 0
    sd1_sd2_ratio = sd1 / sd2 if sd2 > 0 else 0
    
    # Geometric metrics
    hrv_tri_index = _calculate_triangular_index(rr)
    tinn = _calculate_tinn(rr)
    
    # Fragmentation metrics
    pip, ials, pss, w3 = _calculate_fragmentation_metrics(rr)
    
    # DFA (simplified)
    dfa_alpha1 = _calculate_dfa_alpha1(rr)
    dfa_alpha2 = _calculate_dfa_alpha2(rr)
    
    # Entropy (simplified)
    sample_entropy = _calculate_sample_entropy(rr)
    approx_entropy = _calculate_approximate_entropy(rr)
    
    # Frequency domain (simplified)
    lf_power, hf_power, vlf_power, total_power = _calculate_frequency_metrics(rr, sample_rate)
    lf_hf_ratio = lf_power / hf_power if hf_power > 0 else 0
    
    return HRVFeatures(
        rmssd_ms=float(rmssd),
        sdnn_ms=float(sdnn),
        pnn50=float(pnn50),
        mean_hr_bpm=float(mean_hr),
        sdsd_ms=float(sdsd),
        cv_rr=float(cv_rr),
        lf_power=float(lf_power),
        hf_power=float(hf_power),
        lf_hf_ratio=float(lf_hf_ratio),
        vlf_power=float(vlf_power),
        total_power=float(total_power),
        sd1=float(sd1),
        sd2=float(sd2),
        sd1_sd2_ratio=float(sd1_sd2_ratio),
        dfa_alpha1=float(dfa_alpha1),
        dfa_alpha2=float(dfa_alpha2),
        sample_entropy=float(sample_entropy),
        approximate_entropy=float(approx_entropy),
        pip=float(pip),
        ials=float(ials),
        pss=float(pss),
        w3=float(w3),
        tinn=float(tinn),
        hrv_triangular_index=float(hrv_tri_index),
    )


def _calculate_triangular_index(rr: NDArray) -> float:
    """Calculate HRV triangular index."""
    if len(rr) < 10:
        return 0.0
    
    # Create histogram with 1/128 second bins
    bin_width = 1000 / 128  # ~7.8ms
    bins = np.arange(np.min(rr), np.max(rr) + bin_width, bin_width)
    
    if len(bins) < 2:
        return 0.0
    
    hist, _ = np.histogram(rr, bins=bins)
    max_count = np.max(hist)
    
    return len(rr) / max_count if max_count > 0 else 0.0


def _calculate_tinn(rr: NDArray) -> float:
    """Calculate TINN (triangular interpolation of NN histogram)."""
    if len(rr) < 10:
        return 0.0
    
    bin_width = 1000 / 128
    bins = np.arange(np.min(rr), np.max(rr) + bin_width, bin_width)
    
    if len(bins) < 3:
        return 0.0
    
    hist, bin_edges = np.histogram(rr, bins=bins)
    
    # Find mode
    mode_idx = np.argmax(hist)
    
    # Find N and M (base of triangle)
    # Simplified: use 10% of max as threshold
    threshold = np.max(hist) * 0.1
    
    n_idx = 0
    for i in range(mode_idx, -1, -1):
        if hist[i] < threshold:
            n_idx = i
            break
    
    m_idx = len(hist) - 1
    for i in range(mode_idx, len(hist)):
        if hist[i] < threshold:
            m_idx = i
            break
    
    tinn = (bin_edges[m_idx] - bin_edges[n_idx])
    return float(tinn)


def _calculate_fragmentation_metrics(rr: NDArray) -> tuple[float, float, float, float]:
    """Calculate fragmentation metrics (Costa et al., 2017)."""
    if len(rr) < 10:
        return 0.0, 0.0, 0.0, 0.0
    
    diff = np.diff(rr)
    signs = np.sign(diff)
    
    # Remove zeros (no change)
    signs = signs[signs != 0]
    
    if len(signs) < 2:
        return 0.0, 0.0, 0.0, 0.0
    
    # PIP: Percentage of inflection points
    sign_changes = np.sum(np.diff(signs) != 0)
    pip = sign_changes / (len(signs) - 1) * 100 if len(signs) > 1 else 0
    
    # IALS: Inverse average segment length
    # Find segment lengths (consecutive same signs)
    segment_lengths: list[int] = []
    current_length = 1
    
    for i in range(1, len(signs)):
        if signs[i] == signs[i-1]:
            current_length += 1
        else:
            segment_lengths.append(current_length)
            current_length = 1
    segment_lengths.append(current_length)
    
    avg_segment = np.mean(segment_lengths) if segment_lengths else 1
    ials = 1 / avg_segment
    
    # PSS: Percentage of short segments (length 1)
    short_segments = sum(1 for s in segment_lengths if s == 1)
    pss = short_segments / len(segment_lengths) * 100 if segment_lengths else 0
    
    # W3: 3-variation word frequency (simplified)
    # Count patterns of 3 consecutive acceleration/deceleration
    w3_count = 0
    for i in range(len(signs) - 2):
        pattern = tuple(signs[i:i+3])
        # W3 is alternating pattern: +,-,+ or -,+,-
        if pattern == (1, -1, 1) or pattern == (-1, 1, -1):
            w3_count += 1
    
    w3 = w3_count / (len(signs) - 2) * 100 if len(signs) > 2 else 0
    
    return float(pip), float(ials), float(pss), float(w3)


def _calculate_dfa_alpha1(rr: NDArray) -> float:
    """Calculate DFA alpha1 (short-term scaling exponent)."""
    if len(rr) < 50:
        return 1.0
    
    # Integrate the time series
    y = np.cumsum(rr - np.mean(rr))
    
    # Box sizes for alpha1 (4-16 beats)
    scales = np.arange(4, min(17, len(rr) // 4))
    
    if len(scales) < 2:
        return 1.0
    
    fluctuations: list[float] = []
    
    for scale in scales:
        n_boxes = len(y) // scale
        if n_boxes < 1:
            continue
        
        # Calculate local trends
        rms_values: list[float] = []
        for i in range(n_boxes):
            segment = y[i * scale:(i + 1) * scale]
            x = np.arange(len(segment))
            
            # Linear fit
            coeffs = np.polyfit(x, segment, 1)
            trend = np.polyval(coeffs, x)
            
            rms = np.sqrt(np.mean((segment - trend) ** 2))
            rms_values.append(rms)
        
        fluctuations.append(np.mean(rms_values))
    
    if len(fluctuations) < 2:
        return 1.0
    
    # Log-log regression
    log_scales = np.log(scales[:len(fluctuations)])
    log_fluct = np.log(np.array(fluctuations) + 1e-10)
    
    slope, _, _, _, _ = stats.linregress(log_scales, log_fluct)
    
    return float(slope)


def _calculate_dfa_alpha2(rr: NDArray) -> float:
    """Calculate DFA alpha2 (long-term scaling exponent)."""
    if len(rr) < 200:
        return 1.0
    
    y = np.cumsum(rr - np.mean(rr))
    
    # Box sizes for alpha2 (16-64 beats)
    scales = np.arange(16, min(65, len(rr) // 4))
    
    if len(scales) < 2:
        return 1.0
    
    fluctuations: list[float] = []
    
    for scale in scales:
        n_boxes = len(y) // scale
        if n_boxes < 1:
            continue
        
        rms_values: list[float] = []
        for i in range(n_boxes):
            segment = y[i * scale:(i + 1) * scale]
            x = np.arange(len(segment))
            coeffs = np.polyfit(x, segment, 1)
            trend = np.polyval(coeffs, x)
            rms = np.sqrt(np.mean((segment - trend) ** 2))
            rms_values.append(rms)
        
        fluctuations.append(np.mean(rms_values))
    
    if len(fluctuations) < 2:
        return 1.0
    
    log_scales = np.log(scales[:len(fluctuations)])
    log_fluct = np.log(np.array(fluctuations) + 1e-10)
    
    slope, _, _, _, _ = stats.linregress(log_scales, log_fluct)
    
    return float(slope)


def _calculate_sample_entropy(rr: NDArray, m: int = 2, r_factor: float = 0.2) -> float:
    """Calculate sample entropy."""
    if len(rr) < 50:
        return 0.0
    
    n = len(rr)
    r = r_factor * np.std(rr)
    
    def count_matches(template_length: int) -> int:
        count = 0
        for i in range(n - template_length + 1):
            for j in range(i + 1, n - template_length + 1):
                # Check if templates match within tolerance r
                template_i = rr[i:i + template_length]
                template_j = rr[j:j + template_length]
                if np.max(np.abs(template_i - template_j)) < r:
                    count += 1
        return count
    
    a = count_matches(m + 1)
    b = count_matches(m)
    
    if b == 0:
        return 0.0
    
    return float(-np.log(a / b)) if a > 0 else 0.0


def _calculate_approximate_entropy(rr: NDArray, m: int = 2, r_factor: float = 0.2) -> float:
    """Calculate approximate entropy."""
    if len(rr) < 50:
        return 0.0
    
    n = len(rr)
    r = r_factor * np.std(rr)
    
    def phi(template_length: int) -> float:
        patterns: list[NDArray] = []
        for i in range(n - template_length + 1):
            patterns.append(rr[i:i + template_length])
        
        counts: list[float] = []
        for i, pattern_i in enumerate(patterns):
            count = 0
            for pattern_j in patterns:
                if np.max(np.abs(pattern_i - pattern_j)) < r:
                    count += 1
            counts.append(count / len(patterns))
        
        return np.mean(np.log(counts))
    
    return float(phi(m) - phi(m + 1))


def _calculate_frequency_metrics(
    rr: NDArray,
    sample_rate: float = 4.0,
) -> tuple[float, float, float, float]:
    """Calculate frequency domain metrics (simplified)."""
    from scipy import signal as sig
    from scipy import interpolate
    
    if len(rr) < 60:
        return 0.0, 0.0, 0.0, 0.0
    
    # Create time vector
    time = np.cumsum(rr) / 1000  # Convert to seconds
    time = time - time[0]  # Start from 0
    
    # Resample to uniform rate
    duration = time[-1]
    n_samples = int(duration * sample_rate)
    
    if n_samples < 10:
        return 0.0, 0.0, 0.0, 0.0
    
    uniform_time = np.linspace(0, duration, n_samples)
    
    # Interpolate
    f = interpolate.interp1d(time, rr, kind='cubic', fill_value='extrapolate')
    rr_resampled = f(uniform_time)
    
    # Detrend
    rr_detrended = sig.detrend(rr_resampled)
    
    # Welch PSD
    freqs, psd = sig.welch(rr_detrended, fs=sample_rate, nperseg=min(256, len(rr_detrended)))
    
    # Calculate band powers
    vlf_mask = (freqs >= 0.003) & (freqs < 0.04)
    lf_mask = (freqs >= 0.04) & (freqs < 0.15)
    hf_mask = (freqs >= 0.15) & (freqs < 0.4)
    
    vlf_power = np.trapz(psd[vlf_mask], freqs[vlf_mask]) if np.any(vlf_mask) else 0
    lf_power = np.trapz(psd[lf_mask], freqs[lf_mask]) if np.any(lf_mask) else 0
    hf_power = np.trapz(psd[hf_mask], freqs[hf_mask]) if np.any(hf_mask) else 0
    total_power = vlf_power + lf_power + hf_power
    
    return float(lf_power), float(hf_power), float(vlf_power), float(total_power)


# ---------------------------------------------------------------------------
# Atrial Fibrillation Risk Prediction
# ---------------------------------------------------------------------------


def predict_af_risk(
    features: HRVFeatures,
    age: int | None = None,
    has_hypertension: bool = False,
    has_diabetes: bool = False,
    has_heart_disease: bool = False,
) -> AFRiskPrediction:
    """Predict atrial fibrillation risk.
    
    Based on HRV features and clinical risk factors.
    Uses a rule-based model derived from published research.
    
    Args:
        features: HRV features.
        age: Patient age (optional).
        has_hypertension: History of hypertension.
        has_diabetes: History of diabetes.
        has_heart_disease: History of heart disease.
        
    Returns:
        AFRiskPrediction with risk assessment.
    """
    risk_score = 0.0
    risk_factors: list[str] = []
    protective_factors: list[str] = []
    
    # HRV-based risk factors (based on Gilon et al., 2024; PROOF-AF Study, 2025)
    
    # DFA alpha1 < 0.75 indicates increased fragmentation (strong predictor)
    if features.dfa_alpha1 < 0.75:
        risk_score += 0.25
        risk_factors.append(f"Low DFA α1 ({features.dfa_alpha1:.2f} < 0.75)")
    elif features.dfa_alpha1 > 1.0:
        protective_factors.append(f"Normal DFA α1 ({features.dfa_alpha1:.2f})")
    
    # High PIP (fragmentation) indicates AF risk
    if features.pip > 50:
        risk_score += 0.15
        risk_factors.append(f"High fragmentation (PIP {features.pip:.1f}%)")
    
    # Low RMSSD indicates reduced vagal tone
    if features.rmssd_ms < 20:
        risk_score += 0.1
        risk_factors.append(f"Low RMSSD ({features.rmssd_ms:.1f} ms)")
    elif features.rmssd_ms > 40:
        protective_factors.append(f"Good vagal tone (RMSSD {features.rmssd_ms:.1f} ms)")
    
    # High LF/HF ratio indicates sympathetic dominance
    if features.lf_hf_ratio > 3.0:
        risk_score += 0.1
        risk_factors.append(f"Sympathetic dominance (LF/HF {features.lf_hf_ratio:.2f})")
    
    # Low HRV triangular index
    if features.hrv_triangular_index < 10:
        risk_score += 0.1
        risk_factors.append(f"Low HRV triangular index ({features.hrv_triangular_index:.1f})")
    
    # Low sample entropy indicates reduced complexity
    if features.sample_entropy < 1.0:
        risk_score += 0.1
        risk_factors.append(f"Reduced HRV complexity (SampEn {features.sample_entropy:.2f})")
    
    # Clinical risk factors
    if age and age >= 65:
        risk_score += 0.15
        risk_factors.append(f"Age ≥65 years ({age})")
    
    if has_hypertension:
        risk_score += 0.1
        risk_factors.append("Hypertension")
    
    if has_diabetes:
        risk_score += 0.05
        risk_factors.append("Diabetes")
    
    if has_heart_disease:
        risk_score += 0.15
        risk_factors.append("Heart disease history")
    
    # Normalize score
    risk_score = min(1.0, risk_score)
    
    # Determine risk level
    if risk_score < AF_RISK_LOW_THRESHOLD:
        risk_level = RiskLevel.LOW
    elif risk_score < AF_RISK_MODERATE_THRESHOLD:
        risk_level = RiskLevel.MODERATE
    elif risk_score < AF_RISK_HIGH_THRESHOLD:
        risk_level = RiskLevel.HIGH
    else:
        risk_level = RiskLevel.VERY_HIGH
    
    # Predict AF type if at risk
    af_type = AFType.UNKNOWN
    if risk_score >= AF_RISK_MODERATE_THRESHOLD:
        if features.dfa_alpha1 < 0.65:
            af_type = AFType.PAROXYSMAL
        elif features.pip > 60:
            af_type = AFType.PERSISTENT
    
    # Calculate confidence
    confidence = min(0.9, 0.5 + len(risk_factors) * 0.05 + len(protective_factors) * 0.05)
    
    # Generate recommendations
    recommendations = _generate_af_recommendations(risk_level, risk_factors)
    
    return AFRiskPrediction(
        risk_score=risk_score,
        risk_level=risk_level,
        af_type_predicted=af_type,
        key_risk_factors=risk_factors,
        protective_factors=protective_factors,
        confidence=confidence,
        recommendations=recommendations,
    )


def _generate_af_recommendations(risk_level: RiskLevel, risk_factors: list[str]) -> list[str]:
    """Generate AF risk recommendations."""
    recommendations: list[str] = []
    
    if risk_level == RiskLevel.LOW:
        recommendations.append("Continue regular HRV monitoring for baseline tracking.")
        recommendations.append("Maintain healthy lifestyle habits.")
    
    elif risk_level == RiskLevel.MODERATE:
        recommendations.append("Consider more frequent HRV monitoring.")
        recommendations.append("Discuss AF risk with your healthcare provider.")
        recommendations.append("Monitor for symptoms: palpitations, fatigue, shortness of breath.")
    
    elif risk_level in (RiskLevel.HIGH, RiskLevel.VERY_HIGH):
        recommendations.append("Consult a cardiologist for comprehensive evaluation.")
        recommendations.append("Consider ECG monitoring (Holter or event monitor).")
        recommendations.append("Discuss anticoagulation if AF is confirmed.")
        recommendations.append("Address modifiable risk factors (hypertension, obesity, alcohol).")
    
    return recommendations


# ---------------------------------------------------------------------------
# Sudden Cardiac Death Risk Prediction
# ---------------------------------------------------------------------------


def predict_scd_risk(
    features: HRVFeatures,
    age: int | None = None,
    lvef: float | None = None,  # Left ventricular ejection fraction
    has_prior_mi: bool = False,
    has_heart_failure: bool = False,
) -> SCDRiskPrediction:
    """Predict sudden cardiac death risk.
    
    Based on HRV markers of autonomic dysfunction.
    
    IMPORTANT: This is a screening tool only. Clinical decisions
    should be made by qualified healthcare providers.
    
    Args:
        features: HRV features.
        age: Patient age (optional).
        lvef: Left ventricular ejection fraction (optional).
        has_prior_mi: History of myocardial infarction.
        has_heart_failure: History of heart failure.
        
    Returns:
        SCDRiskPrediction with risk assessment.
    """
    risk_score = 0.0
    risk_factors: list[str] = []
    
    # HRV-based risk factors (based on Task Force 1996, La Rovere et al.)
    
    # Very low SDNN is a strong predictor
    if features.sdnn_ms < 50:
        risk_score += 0.2
        risk_factors.append(f"Very low SDNN ({features.sdnn_ms:.1f} ms < 50)")
    elif features.sdnn_ms < 70:
        risk_score += 0.1
        risk_factors.append(f"Low SDNN ({features.sdnn_ms:.1f} ms < 70)")
    
    # Low RMSSD indicates vagal withdrawal
    if features.rmssd_ms < 15:
        risk_score += 0.15
        risk_factors.append(f"Very low RMSSD ({features.rmssd_ms:.1f} ms)")
    
    # Abnormal DFA alpha1
    if features.dfa_alpha1 < 0.65 or features.dfa_alpha1 > 1.5:
        risk_score += 0.15
        risk_factors.append(f"Abnormal DFA α1 ({features.dfa_alpha1:.2f})")
    
    # Low total power
    if features.total_power < 500:
        risk_score += 0.1
        risk_factors.append(f"Low total HRV power ({features.total_power:.0f} ms²)")
    
    # Clinical risk factors
    if age and age >= 70:
        risk_score += 0.1
        risk_factors.append(f"Age ≥70 years ({age})")
    
    if lvef is not None and lvef < 35:
        risk_score += 0.25
        risk_factors.append(f"Low LVEF ({lvef:.0f}% < 35%)")
    
    if has_prior_mi:
        risk_score += 0.15
        risk_factors.append("Prior myocardial infarction")
    
    if has_heart_failure:
        risk_score += 0.2
        risk_factors.append("Heart failure")
    
    # Normalize
    risk_score = min(1.0, risk_score)
    
    # Determine risk level
    if risk_score < SCD_RISK_LOW_THRESHOLD:
        risk_level = RiskLevel.LOW
    elif risk_score < SCD_RISK_MODERATE_THRESHOLD:
        risk_level = RiskLevel.MODERATE
    else:
        risk_level = RiskLevel.HIGH
    
    # Autonomic dysfunction score
    autonomic_score = 0.0
    if features.sdnn_ms < 100:
        autonomic_score += (100 - features.sdnn_ms) / 100
    if features.rmssd_ms < 40:
        autonomic_score += (40 - features.rmssd_ms) / 40
    autonomic_score = min(1.0, autonomic_score / 2)
    
    # Confidence
    confidence = min(0.85, 0.4 + len(risk_factors) * 0.05)
    
    # Recommendations
    recommendations = _generate_scd_recommendations(risk_level, risk_factors)
    
    return SCDRiskPrediction(
        risk_score=risk_score,
        risk_level=risk_level,
        key_risk_factors=risk_factors,
        autonomic_dysfunction_score=autonomic_score,
        confidence=confidence,
        recommendations=recommendations,
    )


def _generate_scd_recommendations(risk_level: RiskLevel, risk_factors: list[str]) -> list[str]:
    """Generate SCD risk recommendations."""
    recommendations: list[str] = []
    
    if risk_level == RiskLevel.LOW:
        recommendations.append("Continue regular cardiovascular health monitoring.")
        recommendations.append("Maintain heart-healthy lifestyle.")
    
    elif risk_level == RiskLevel.MODERATE:
        recommendations.append("Discuss findings with a cardiologist.")
        recommendations.append("Consider comprehensive cardiac evaluation.")
        recommendations.append("Optimize management of cardiovascular risk factors.")
    
    else:  # HIGH
        recommendations.append("Urgent cardiology consultation recommended.")
        recommendations.append("Comprehensive risk stratification needed.")
        recommendations.append("Discuss potential need for ICD evaluation.")
        recommendations.append("Optimize heart failure therapy if applicable.")
    
    return recommendations


# ---------------------------------------------------------------------------
# Sleep Apnea Screening
# ---------------------------------------------------------------------------


def screen_sleep_apnea(
    features: HRVFeatures,
    overnight_data: bool = True,
    bmi: float | None = None,
    age: int | None = None,
    sex: str = "unknown",
    neck_circumference_cm: float | None = None,
) -> SleepApneaPrediction:
    """Screen for sleep apnea using HRV features.
    
    Based on overnight HRV patterns that indicate
    cyclic variation in heart rate associated with apnea events.
    
    Args:
        features: HRV features (ideally from overnight recording).
        overnight_data: Whether data is from overnight recording.
        bmi: Body mass index (optional).
        age: Patient age (optional).
        sex: Patient sex.
        neck_circumference_cm: Neck circumference (optional).
        
    Returns:
        SleepApneaPrediction with screening results.
    """
    indicators: list[str] = []
    probability = 0.0
    
    # HRV indicators of sleep apnea
    
    # High LF/HF ratio during sleep indicates sympathetic activation
    if features.lf_hf_ratio > 2.0:
        probability += 0.15
        indicators.append(f"Elevated LF/HF ratio ({features.lf_hf_ratio:.2f})")
    
    # High SDNN can indicate cyclic variation
    if features.sdnn_ms > 100:
        probability += 0.1
        indicators.append(f"High SDNN ({features.sdnn_ms:.1f} ms)")
    
    # Low HRV triangular index
    if features.hrv_triangular_index < 15:
        probability += 0.1
        indicators.append(f"Low HRV triangular index ({features.hrv_triangular_index:.1f})")
    
    # High fragmentation (PIP)
    if features.pip > 45:
        probability += 0.1
        indicators.append(f"Elevated fragmentation (PIP {features.pip:.1f}%)")
    
    # Clinical risk factors (STOP-BANG criteria components)
    if bmi and bmi >= 35:
        probability += 0.2
        indicators.append(f"Obesity (BMI {bmi:.1f})")
    elif bmi and bmi >= 30:
        probability += 0.1
        indicators.append(f"Overweight (BMI {bmi:.1f})")
    
    if age and age >= 50:
        probability += 0.1
        indicators.append(f"Age ≥50 ({age})")
    
    if neck_circumference_cm and neck_circumference_cm > 40:
        probability += 0.1
        indicators.append(f"Large neck circumference ({neck_circumference_cm} cm)")
    
    if sex.lower() == "male":
        probability += 0.1
        indicators.append("Male sex")
    
    # Reduce confidence if not overnight data
    if not overnight_data:
        probability *= 0.7
    
    # Normalize
    probability = min(1.0, probability)
    
    # Estimate AHI (rough approximation)
    predicted_ahi = probability * 40  # Scale to 0-40 range
    
    # Determine severity
    if predicted_ahi < APNEA_AHI_MILD_THRESHOLD:
        severity = ApneaSeverity.NONE
    elif predicted_ahi < APNEA_AHI_MODERATE_THRESHOLD:
        severity = ApneaSeverity.MILD
    elif predicted_ahi < APNEA_AHI_SEVERE_THRESHOLD:
        severity = ApneaSeverity.MODERATE
    else:
        severity = ApneaSeverity.SEVERE
    
    # Confidence
    confidence = 0.5 if overnight_data else 0.3
    confidence += len(indicators) * 0.03
    confidence = min(0.8, confidence)
    
    # Recommendations
    recommendations = _generate_apnea_recommendations(severity, probability)
    
    return SleepApneaPrediction(
        predicted_ahi=predicted_ahi,
        severity=severity,
        probability_apnea=probability,
        key_indicators=indicators,
        confidence=confidence,
        recommendations=recommendations,
    )


def _generate_apnea_recommendations(severity: ApneaSeverity, probability: float) -> list[str]:
    """Generate sleep apnea recommendations."""
    recommendations: list[str] = []
    
    if severity == ApneaSeverity.NONE:
        recommendations.append("Low probability of significant sleep apnea.")
        if probability > 0.2:
            recommendations.append("Consider home sleep test if symptoms present.")
    
    elif severity == ApneaSeverity.MILD:
        recommendations.append("Moderate probability of mild sleep apnea.")
        recommendations.append("Consider home sleep apnea test (HSAT).")
        recommendations.append("Weight loss if overweight may help.")
    
    elif severity == ApneaSeverity.MODERATE:
        recommendations.append("High probability of moderate sleep apnea.")
        recommendations.append("Polysomnography (sleep study) recommended.")
        recommendations.append("Discuss CPAP therapy with sleep specialist.")
    
    else:  # SEVERE
        recommendations.append("High probability of severe sleep apnea.")
        recommendations.append("Urgent sleep medicine consultation recommended.")
        recommendations.append("Polysomnography and treatment initiation advised.")
        recommendations.append("Avoid driving or operating machinery if excessively sleepy.")
    
    return recommendations


# ---------------------------------------------------------------------------
# Stress Detection
# ---------------------------------------------------------------------------


def detect_stress(features: HRVFeatures) -> StressDetection:
    """Detect stress level from HRV features.
    
    Args:
        features: HRV features.
        
    Returns:
        StressDetection with stress assessment.
    """
    indicators: list[str] = []
    stress_score = 50.0  # Baseline
    
    # Low RMSSD indicates stress/sympathetic activation
    if features.rmssd_ms < 20:
        stress_score += 25
        indicators.append("Very low vagal activity")
    elif features.rmssd_ms < 35:
        stress_score += 15
        indicators.append("Reduced vagal activity")
    elif features.rmssd_ms > 60:
        stress_score -= 15
        indicators.append("Good vagal tone")
    
    # High LF/HF ratio indicates sympathetic dominance
    if features.lf_hf_ratio > 3.0:
        stress_score += 15
        indicators.append("Sympathetic dominance")
    elif features.lf_hf_ratio < 0.8:
        stress_score -= 10
        indicators.append("Parasympathetic dominance")
    
    # Low pNN50 indicates reduced vagal activity
    if features.pnn50 < 5:
        stress_score += 10
        indicators.append("Very low pNN50")
    elif features.pnn50 > 20:
        stress_score -= 10
        indicators.append("Good pNN50")
    
    # High mean HR indicates stress
    if features.mean_hr_bpm > 80:
        stress_score += 10
        indicators.append("Elevated heart rate")
    elif features.mean_hr_bpm < 60:
        stress_score -= 5
        indicators.append("Low resting heart rate")
    
    # Normalize score
    stress_score = max(0, min(100, stress_score))
    
    # Determine stress level
    if stress_score < 30:
        stress_level = "low"
    elif stress_score < 50:
        stress_level = "moderate"
    elif stress_score < 70:
        stress_level = "elevated"
    else:
        stress_level = "high"
    
    # Autonomic balance
    if features.lf_hf_ratio > 2.0:
        balance = "sympathetic_dominant"
    elif features.lf_hf_ratio < 0.5:
        balance = "parasympathetic_dominant"
    else:
        balance = "balanced"
    
    # Recommendations
    recommendations: list[str] = []
    if stress_level in ("elevated", "high"):
        recommendations.append("Consider stress reduction techniques (breathing, meditation).")
        recommendations.append("Ensure adequate sleep and recovery.")
        recommendations.append("Reduce caffeine and stimulant intake.")
    else:
        recommendations.append("Stress levels appear manageable.")
        recommendations.append("Continue current wellness practices.")
    
    return StressDetection(
        stress_score=stress_score,
        stress_level=stress_level,
        autonomic_balance=balance,
        key_indicators=indicators,
        recommendations=recommendations,
        confidence=0.7,
    )


# ---------------------------------------------------------------------------
# Comprehensive Risk Report
# ---------------------------------------------------------------------------


def generate_comprehensive_risk_report(
    rr_intervals_ms: NDArray[np.float64],
    age: int | None = None,
    sex: str = "unknown",
    bmi: float | None = None,
    clinical_history: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Generate comprehensive ML-based risk report.
    
    Args:
        rr_intervals_ms: RR intervals in milliseconds.
        age: Patient age (optional).
        sex: Patient sex.
        bmi: Body mass index (optional).
        clinical_history: Dict of clinical conditions (optional).
        
    Returns:
        Dictionary with all risk assessments.
    """
    # Extract features
    features = extract_hrv_features(rr_intervals_ms)
    
    # Default clinical history
    if clinical_history is None:
        clinical_history = {}
    
    # Generate predictions
    af_risk = predict_af_risk(
        features,
        age=age,
        has_hypertension=clinical_history.get("hypertension", False),
        has_diabetes=clinical_history.get("diabetes", False),
        has_heart_disease=clinical_history.get("heart_disease", False),
    )
    
    scd_risk = predict_scd_risk(
        features,
        age=age,
        has_prior_mi=clinical_history.get("prior_mi", False),
        has_heart_failure=clinical_history.get("heart_failure", False),
    )
    
    apnea_screen = screen_sleep_apnea(
        features,
        bmi=bmi,
        age=age,
        sex=sex,
    )
    
    stress = detect_stress(features)
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "features": {
            "rmssd_ms": features.rmssd_ms,
            "sdnn_ms": features.sdnn_ms,
            "pnn50": features.pnn50,
            "mean_hr_bpm": features.mean_hr_bpm,
            "lf_hf_ratio": features.lf_hf_ratio,
            "dfa_alpha1": features.dfa_alpha1,
            "sample_entropy": features.sample_entropy,
            "pip": features.pip,
        },
        "af_risk": {
            "score": af_risk.risk_score,
            "level": af_risk.risk_level.value,
            "risk_factors": af_risk.key_risk_factors,
            "recommendations": af_risk.recommendations,
        },
        "scd_risk": {
            "score": scd_risk.risk_score,
            "level": scd_risk.risk_level.value,
            "risk_factors": scd_risk.key_risk_factors,
            "recommendations": scd_risk.recommendations,
        },
        "sleep_apnea": {
            "predicted_ahi": apnea_screen.predicted_ahi,
            "severity": apnea_screen.severity.value,
            "probability": apnea_screen.probability_apnea,
            "indicators": apnea_screen.key_indicators,
            "recommendations": apnea_screen.recommendations,
        },
        "stress": {
            "score": stress.stress_score,
            "level": stress.stress_level,
            "balance": stress.autonomic_balance,
            "recommendations": stress.recommendations,
        },
        "disclaimer": (
            "These predictions are for research and educational purposes only. "
            "They should NOT be used for clinical diagnosis. "
            "Always consult a qualified healthcare provider for medical decisions."
        ),
    }

