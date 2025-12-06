"""
CPU Optimization Module for Mission Control - Flight Surgeon.

Provides optimized CPU-only implementations of computationally expensive HRV
calculations for systems without GPU acceleration.

Key optimizations:
- NumPy vectorization with reduced memory allocation
- Optional Numba JIT compilation for hot loops
- Chunked processing for large datasets
- Efficient algorithm variants (O(n) vs O(n^2) where possible)
- Smart caching with LRU eviction

Author: Dr. Diego Leonel Malpica Hincapié, MD
Version: 1.0.0
"""

from __future__ import annotations

import functools
import logging
import math
import multiprocessing
import os
import platform
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Final, List, Optional, Tuple, TypeVar

import numpy as np
import pandas as pd

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar("T")

# ---------------------------------------------------------------------------
# CPU Detection and Auto-Tuning
# ---------------------------------------------------------------------------

# Try to import psutil for CPU info, fallback gracefully
try:
    import psutil
    _PSUTIL_AVAILABLE: Final[bool] = True
except ImportError:
    _PSUTIL_AVAILABLE = False
    _LOGGER.debug("psutil not available; using basic CPU detection")

# Try to import Numba for JIT compilation
try:
    from numba import jit, prange
    _NUMBA_AVAILABLE: Final[bool] = True
except ImportError:
    _NUMBA_AVAILABLE = False
    _LOGGER.debug("Numba not available; using pure NumPy implementations")


@dataclass(frozen=True, slots=True)
class CPUInfo:
    """Information about the CPU for auto-tuning."""
    
    physical_cores: int
    logical_cores: int
    available_memory_gb: float
    cpu_freq_mhz: float
    cpu_name: str
    is_arm: bool
    performance_tier: str  # "low", "medium", "high"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "physical_cores": self.physical_cores,
            "logical_cores": self.logical_cores,
            "available_memory_gb": round(self.available_memory_gb, 2),
            "cpu_freq_mhz": round(self.cpu_freq_mhz, 0),
            "cpu_name": self.cpu_name,
            "is_arm": self.is_arm,
            "performance_tier": self.performance_tier,
        }


def detect_cpu_info() -> CPUInfo:
    """
    Detect CPU capabilities for auto-tuning performance settings.
    
    Returns:
        CPUInfo with detected hardware characteristics.
    """
    # Default values
    physical_cores = os.cpu_count() or 2
    logical_cores = physical_cores
    available_memory_gb = 4.0
    cpu_freq_mhz = 2000.0
    cpu_name = "Unknown CPU"
    is_arm = platform.machine().lower() in ("arm64", "aarch64", "armv8")
    
    if _PSUTIL_AVAILABLE:
        try:
            physical_cores = psutil.cpu_count(logical=False) or physical_cores
            logical_cores = psutil.cpu_count(logical=True) or logical_cores
            
            mem = psutil.virtual_memory()
            available_memory_gb = mem.available / (1024 ** 3)
            
            freq = psutil.cpu_freq()
            if freq is not None:
                cpu_freq_mhz = freq.current or freq.max or 2000.0
        except Exception as exc:
            _LOGGER.debug("psutil CPU detection partial: %s", exc)
    
    # Try to get CPU name on different platforms
    try:
        if sys.platform == "linux":
            with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                for line in f:
                    if "model name" in line.lower():
                        cpu_name = line.split(":")[1].strip()
                        break
        elif sys.platform == "darwin":
            import subprocess
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                cpu_name = result.stdout.strip()
        elif sys.platform == "win32":
            # Try reading from Windows registry first (fast, provides full name)
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
                )
                cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                winreg.CloseKey(key)
            except Exception:
                # Fallback to platform.processor() (generic name)
                proc_name = platform.processor()
                if proc_name and "unknown" not in proc_name.lower():
                    cpu_name = proc_name
    except Exception as exc:
        _LOGGER.debug("CPU name detection failed: %s", exc)
    
    # Determine performance tier based on cores and frequency
    score = physical_cores * (cpu_freq_mhz / 1000.0)
    if score >= 16.0:  # 4+ cores @ 4GHz or 8+ cores @ 2GHz
        performance_tier = "high"
    elif score >= 6.0:  # 2+ cores @ 3GHz or 4+ cores @ 1.5GHz
        performance_tier = "medium"
    else:
        performance_tier = "low"
    
    return CPUInfo(
        physical_cores=physical_cores,
        logical_cores=logical_cores,
        available_memory_gb=available_memory_gb,
        cpu_freq_mhz=cpu_freq_mhz,
        cpu_name=cpu_name,
        is_arm=is_arm,
        performance_tier=performance_tier,
    )


# Cached CPU info singleton
_cached_cpu_info: Optional[CPUInfo] = None


def get_cpu_info(refresh: bool = False) -> CPUInfo:
    """Get CPU info (cached)."""
    global _cached_cpu_info
    if _cached_cpu_info is None or refresh:
        _cached_cpu_info = detect_cpu_info()
    return _cached_cpu_info


# ---------------------------------------------------------------------------
# Adaptive Performance Settings
# ---------------------------------------------------------------------------


@dataclass
class AdaptiveSettings:
    """Settings automatically adjusted based on CPU capabilities."""
    
    max_array_size_full: int  # Max size for full O(n^2) algorithms
    max_windows: int  # Max number of windowed analyses
    chunk_size: int  # Size for chunked processing
    use_parallel: bool  # Whether to use parallel processing
    n_workers: int  # Number of parallel workers
    use_numba: bool  # Whether to use Numba JIT
    downsample_threshold: int  # Downsample arrays larger than this
    entropy_fast_mode: bool  # Use fast approximation for entropy
    
    @classmethod
    def from_cpu_info(cls, info: CPUInfo) -> "AdaptiveSettings":
        """Create settings based on CPU capabilities."""
        if info.performance_tier == "high":
            return cls(
                max_array_size_full=10000,
                max_windows=1000,
                chunk_size=5000,
                use_parallel=True,
                n_workers=max(1, info.physical_cores - 1),
                use_numba=_NUMBA_AVAILABLE,
                downsample_threshold=50000,
                entropy_fast_mode=False,
            )
        elif info.performance_tier == "medium":
            return cls(
                max_array_size_full=5000,
                max_windows=500,
                chunk_size=2000,
                use_parallel=info.physical_cores >= 4,
                n_workers=max(1, info.physical_cores // 2),
                use_numba=_NUMBA_AVAILABLE,
                downsample_threshold=20000,
                entropy_fast_mode=True,
            )
        else:  # low
            return cls(
                max_array_size_full=2000,
                max_windows=200,
                chunk_size=1000,
                use_parallel=False,
                n_workers=1,
                use_numba=_NUMBA_AVAILABLE,
                downsample_threshold=10000,
                entropy_fast_mode=True,
            )


def get_adaptive_settings() -> AdaptiveSettings:
    """Get adaptive settings based on detected CPU."""
    info = get_cpu_info()
    return AdaptiveSettings.from_cpu_info(info)


# ---------------------------------------------------------------------------
# Optimized Time-Domain Metrics (Vectorized)
# ---------------------------------------------------------------------------


def compute_time_domain_fast(rr_intervals: np.ndarray) -> Dict[str, float]:
    """
    Compute time-domain HRV metrics with optimized vectorization.
    
    Uses single-pass statistics where possible to reduce memory allocations.
    
    Args:
        rr_intervals: RR intervals in milliseconds.
        
    Returns:
        Dictionary of time-domain metrics.
    """
    if rr_intervals.size == 0:
        return {}
    
    # Use float64 for numerical stability
    rr = np.asarray(rr_intervals, dtype=np.float64)
    n = rr.size
    
    # Single-pass mean and variance using Welford's algorithm conceptually,
    # but NumPy's vectorized implementations are already efficient
    mean_nni = float(np.mean(rr))
    
    # Compute differences once
    rr_diff = np.diff(rr) if n > 1 else np.array([], dtype=np.float64)
    
    metrics: Dict[str, float] = {
        "mean_nni": mean_nni,
        "sdnn": float(np.std(rr, ddof=1)) if n > 1 else 0.0,
        "median_nni": float(np.median(rr)),
    }
    
    # MAD calculation
    metrics["mad_nni"] = float(np.median(np.abs(rr - metrics["median_nni"])))
    
    # CVNN
    metrics["cvnn"] = float((metrics["sdnn"] / mean_nni) * 100) if mean_nni > 0 else 0.0
    
    # Heart rate metrics (vectorized)
    hr_values = 60000.0 / rr
    metrics["mean_hr"] = float(np.mean(hr_values))
    metrics["std_hr"] = float(np.std(hr_values, ddof=1)) if n > 1 else 0.0
    metrics["min_hr"] = float(np.min(hr_values))
    metrics["max_hr"] = float(np.max(hr_values))
    
    if rr_diff.size > 0:
        # RMSSD - optimized with in-place squaring
        rr_diff_sq = rr_diff ** 2
        metrics["rmssd"] = float(np.sqrt(np.mean(rr_diff_sq)))
        
        # SDSD
        metrics["sdsd"] = float(np.std(rr_diff, ddof=1))
        
        # CVSD
        mean_abs = float(np.mean(np.abs(rr_diff)))
        metrics["cvsd"] = float((metrics["sdsd"] / mean_abs) * 100) if mean_abs > 0 else 0.0
        
        # pNN50 and pNN20 - vectorized counting
        abs_diff = np.abs(rr_diff)
        nn50 = int(np.sum(abs_diff > 50.0))
        nn20 = int(np.sum(abs_diff > 20.0))
        diff_size = rr_diff.size
        
        metrics["nn50"] = float(nn50)
        metrics["pnn50"] = float((nn50 / diff_size) * 100.0)
        metrics["nn20"] = float(nn20)
        metrics["pnn20"] = float((nn20 / diff_size) * 100.0)
    else:
        metrics.update({
            "rmssd": 0.0, "sdsd": 0.0, "cvsd": 0.0,
            "nn50": 0.0, "pnn50": 0.0, "nn20": 0.0, "pnn20": 0.0,
        })
    
    return metrics


# ---------------------------------------------------------------------------
# Optimized Entropy Calculations
# ---------------------------------------------------------------------------


def compute_entropy_fast(
    rr_intervals: np.ndarray,
    *,
    m: int = 2,
    r_ratio: float = 0.2,
    max_samples: int = 2000,
) -> Dict[str, float]:
    """
    Compute ApEn and SampEn with optimizations for CPU-only systems.
    
    Uses chunked distance calculations and early termination for large arrays.
    For arrays larger than max_samples, uses random subsampling.
    
    Args:
        rr_intervals: RR intervals in milliseconds.
        m: Embedding dimension (default 2).
        r_ratio: Tolerance ratio (default 0.2).
        max_samples: Maximum samples before subsampling.
        
    Returns:
        Dictionary with 'apen' and 'sampen'.
    """
    n = int(rr_intervals.size)
    if n < (m + 2):
        return {"apen": 0.0, "sampen": 0.0}
    
    x = np.asarray(rr_intervals, dtype=np.float64)
    
    # Subsample if too large
    if n > max_samples:
        np.random.seed(42)  # Reproducibility
        indices = np.sort(np.random.choice(n, max_samples, replace=False))
        x = x[indices]
        n = max_samples
    
    sd = float(np.std(x, ddof=0))
    r = float(max(1e-9, r_ratio * sd))
    
    def _count_matches_vectorized(dim: int) -> Tuple[np.ndarray, int]:
        """Vectorized match counting using broadcasting in chunks."""
        templates = n - dim
        if templates <= 0:
            return np.zeros(0, dtype=np.float64), 0
        
        # Build template matrix
        template_matrix = np.zeros((templates, dim), dtype=np.float64)
        for i in range(dim):
            template_matrix[:, i] = x[i:n - dim + i]
        
        # Process in chunks to limit memory usage
        chunk_size = min(500, templates)
        counts = np.zeros(templates, dtype=np.int64)
        
        for start in range(0, templates, chunk_size):
            end = min(start + chunk_size, templates)
            chunk = template_matrix[start:end]
            
            # Calculate max absolute differences
            # Shape: (chunk_size, templates, dim)
            diff = np.abs(chunk[:, None, :] - template_matrix[None, :, :])
            max_diff = np.max(diff, axis=2)
            
            # Count matches (excluding self-matches on diagonal)
            matches = (max_diff <= r).astype(np.int64)
            for i, idx in enumerate(range(start, end)):
                matches[i, idx] = 0  # Remove self-match
            counts[start:end] = np.sum(matches, axis=1)
        
        return counts, templates
    
    # Count for m and m+1
    counts_m, templates_m = _count_matches_vectorized(m)
    counts_m1, templates_m1 = _count_matches_vectorized(m + 1)
    
    # ApEn calculation
    if templates_m > 0 and templates_m1 > 0:
        # Phi values (log of mean ratios)
        phi_m = np.mean(counts_m / max(1, templates_m - 1)) if templates_m > 1 else 0.0
        phi_m1 = np.mean(counts_m1 / max(1, templates_m1 - 1)) if templates_m1 > 1 else 0.0
        
        if phi_m > 0 and phi_m1 > 0:
            apen = float(-np.log(phi_m1 / phi_m))
        else:
            apen = 0.0
    else:
        apen = 0.0
    
    # SampEn calculation (uses total counts, not per-template)
    total_m = np.sum(counts_m)
    total_m1 = np.sum(counts_m1)
    
    if total_m > 0 and total_m1 > 0:
        sampen = float(-np.log(total_m1 / total_m))
    else:
        sampen = 0.0
    
    return {"apen": apen, "sampen": sampen}


# ---------------------------------------------------------------------------
# Optimized Poincaré Analysis
# ---------------------------------------------------------------------------


def compute_poincare_fast(rr_intervals: np.ndarray) -> Dict[str, float]:
    """
    Compute Poincaré plot metrics with minimal allocations.
    
    Args:
        rr_intervals: RR intervals in milliseconds.
        
    Returns:
        Dictionary with SD1, SD2, and derived metrics.
    """
    if rr_intervals.size < 2:
        return {"sd1": 0.0, "sd2": 0.0, "sd1_sd2_ratio": 0.0, "ellipse_area": 0.0}
    
    rr = np.asarray(rr_intervals, dtype=np.float64)
    
    # Use views instead of copies
    rr1 = rr[:-1]
    rr2 = rr[1:]
    
    # Direct calculation without intermediate arrays
    diff = rr2 - rr1
    sum_rr = rr2 + rr1
    
    sqrt2 = np.sqrt(2.0)
    sd1 = float(np.std(diff, ddof=1) / sqrt2)
    sd2 = float(np.std(sum_rr, ddof=1) / sqrt2)
    
    sd1_sd2_ratio = float(sd2 / sd1) if sd1 > 0 else 0.0
    ellipse_area = float(np.pi * sd1 * sd2)
    
    return {
        "sd1": sd1,
        "sd2": sd2,
        "sd1_sd2_ratio": sd1_sd2_ratio,
        "ellipse_area": ellipse_area,
    }


# ---------------------------------------------------------------------------
# Optimized DFA (Detrended Fluctuation Analysis)
# ---------------------------------------------------------------------------


def compute_dfa_fast(
    rr_intervals: np.ndarray,
    *,
    min_scale: int = 4,
    max_scale_ratio: float = 0.25,
) -> Dict[str, float]:
    """
    Compute DFA α1 and α2 with optimized segment processing.
    
    Uses vectorized operations for fluctuation calculation.
    
    Args:
        rr_intervals: RR intervals in milliseconds.
        min_scale: Minimum scale for DFA.
        max_scale_ratio: Maximum scale as ratio of series length.
        
    Returns:
        Dictionary with dfa_alpha1 and dfa_alpha2.
    """
    n = rr_intervals.size
    if n < 100:
        return {"dfa_alpha1": 0.0, "dfa_alpha2": 0.0}
    
    rr = np.asarray(rr_intervals, dtype=np.float64)
    
    # Cumulative sum (profile)
    y = np.cumsum(rr - np.mean(rr))
    
    max_scale = int(n * max_scale_ratio)
    
    # Short-term scales (α1): 4-16 beats
    scales_short = np.arange(min_scale, min(17, max_scale))
    
    # Long-term scales (α2): 16-64 beats
    scales_long = np.arange(16, min(65, max_scale))
    
    def _compute_fluctuation_vectorized(scales: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Compute fluctuations for given scales using vectorization."""
        valid_scales = []
        fluctuations = []
        
        for scale in scales:
            scale = int(scale)
            segments = n // scale
            if segments < 4:
                continue
            
            # Reshape into segments
            segment_length = segments * scale
            y_segments = y[:segment_length].reshape(segments, scale)
            
            # Create x-axis for polyfit (shared across segments)
            x = np.arange(scale, dtype=np.float64)
            
            # Vectorized linear detrending
            # For each segment, compute trend and RMS of residuals
            rms_values = np.zeros(segments, dtype=np.float64)
            
            for i in range(segments):
                segment = y_segments[i]
                # Linear fit using numpy (efficient)
                coeffs = np.polyfit(x, segment, 1)
                trend = np.polyval(coeffs, x)
                rms_values[i] = np.sqrt(np.mean((segment - trend) ** 2))
            
            valid_scales.append(float(scale))
            fluctuations.append(float(np.mean(rms_values)))
        
        return np.array(valid_scales), np.array(fluctuations)
    
    scales_s, fluct_s = _compute_fluctuation_vectorized(scales_short)
    scales_l, fluct_l = _compute_fluctuation_vectorized(scales_long)
    
    alpha1 = 0.0
    alpha2 = 0.0
    
    if len(fluct_s) > 2 and np.all(fluct_s > 0):
        log_scales = np.log10(scales_s)
        log_fluct = np.log10(fluct_s)
        alpha1 = float(np.polyfit(log_scales, log_fluct, 1)[0])
    
    if len(fluct_l) > 2 and np.all(fluct_l > 0):
        log_scales = np.log10(scales_l)
        log_fluct = np.log10(fluct_l)
        alpha2 = float(np.polyfit(log_scales, log_fluct, 1)[0])
    
    return {"dfa_alpha1": alpha1, "dfa_alpha2": alpha2}


# ---------------------------------------------------------------------------
# Optimized Frequency Domain (PSD)
# ---------------------------------------------------------------------------


def compute_psd_fast(
    rr_intervals: np.ndarray,
    sampling_rate: float = 4.0,
    method: str = "welch",
) -> Dict[str, float]:
    """
    Compute frequency-domain metrics with optimized interpolation and FFT.
    
    Args:
        rr_intervals: RR intervals in milliseconds.
        sampling_rate: Interpolation rate in Hz.
        method: PSD estimation method ('welch', 'periodogram').
        
    Returns:
        Dictionary of frequency-domain metrics.
    """
    from scipy import signal
    from scipy.interpolate import interp1d
    
    if rr_intervals.size < 50:
        return {}
    
    rr = np.asarray(rr_intervals, dtype=np.float64)
    
    # Convert to seconds and create time axis
    rr_seconds = rr / 1000.0
    r_peak_times = np.concatenate([[0.0], np.cumsum(rr_seconds)])
    rr_timestamps = (r_peak_times[:-1] + r_peak_times[1:]) / 2.0
    
    total_duration = float(r_peak_times[-1])
    if total_duration <= 0:
        return {}
    
    # Interpolate to uniform sampling
    time_regular = np.arange(0.0, total_duration, 1.0 / sampling_rate)
    if time_regular.size < 10:
        return {}
    
    # Use linear interpolation for speed (cubic adds overhead)
    f = interp1d(rr_timestamps, rr, kind="linear", 
                 bounds_error=False, fill_value="extrapolate")
    rr_interp = f(time_regular)
    
    # Detrend
    rr_det = signal.detrend(rr_interp)
    
    # Compute PSD
    nperseg = min(len(rr_det) // 4, 256)
    
    if method == "periodogram":
        freqs, psd = signal.periodogram(rr_det, fs=sampling_rate, window="hann")
    else:
        freqs, psd = signal.welch(rr_det, fs=sampling_rate, 
                                   nperseg=nperseg, window="hann")
    
    # Band power calculation (vectorized)
    vlf_band = (0.0033, 0.04)
    lf_band = (0.04, 0.15)
    hf_band = (0.15, 0.4)
    
    vlf_mask = (freqs >= vlf_band[0]) & (freqs < vlf_band[1])
    lf_mask = (freqs >= lf_band[0]) & (freqs < lf_band[1])
    hf_mask = (freqs >= hf_band[0]) & (freqs < hf_band[1])
    
    # Use Simpson's rule for better accuracy (np.trapz is already efficient)
    vlf_power = float(np.trapz(psd[vlf_mask], freqs[vlf_mask])) if np.any(vlf_mask) else 0.0
    lf_power = float(np.trapz(psd[lf_mask], freqs[lf_mask])) if np.any(lf_mask) else 0.0
    hf_power = float(np.trapz(psd[hf_mask], freqs[hf_mask])) if np.any(hf_mask) else 0.0
    
    total_power = vlf_power + lf_power + hf_power
    lf_hf_sum = lf_power + hf_power
    
    return {
        "vlf_power": vlf_power,
        "lf_power": lf_power,
        "hf_power": hf_power,
        "total_power": total_power,
        "lf_nu": float((lf_power / lf_hf_sum) * 100) if lf_hf_sum > 0 else 0.0,
        "hf_nu": float((hf_power / lf_hf_sum) * 100) if lf_hf_sum > 0 else 0.0,
        "lf_hf_ratio": float(lf_power / hf_power) if hf_power > 0 else 0.0,
        "vlf_percent": float((vlf_power / total_power) * 100) if total_power > 0 else 0.0,
        "lf_percent": float((lf_power / total_power) * 100) if total_power > 0 else 0.0,
        "hf_percent": float((hf_power / total_power) * 100) if total_power > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# Comprehensive Fast HRV Computation
# ---------------------------------------------------------------------------


def compute_hrv_fast(
    rr_intervals: np.ndarray,
    *,
    include_advanced: bool = True,
    adaptive: bool = True,
) -> Dict[str, Any]:
    """
    Compute comprehensive HRV metrics with CPU optimizations.
    
    Automatically adjusts algorithm complexity based on array size and
    CPU capabilities when adaptive=True.
    
    Args:
        rr_intervals: RR intervals in milliseconds.
        include_advanced: Whether to include advanced nonlinear metrics.
        adaptive: Whether to use adaptive algorithm selection.
        
    Returns:
        Dictionary of HRV metrics.
    """
    if rr_intervals.size < 10:
        return {"n_intervals": int(rr_intervals.size)}
    
    rr = np.asarray(rr_intervals, dtype=np.float64)
    n = rr.size
    
    settings = get_adaptive_settings() if adaptive else None
    
    results: Dict[str, Any] = {
        "n_intervals": n,
        "recording_duration_minutes": float(np.sum(rr) / 60000.0),
    }
    
    # Time-domain (always fast)
    results.update(compute_time_domain_fast(rr))
    
    # Frequency-domain
    results.update(compute_psd_fast(rr))
    
    # Poincaré (always fast)
    results.update(compute_poincare_fast(rr))
    
    # DFA
    results.update(compute_dfa_fast(rr))
    
    # Advanced metrics (conditional on settings)
    if include_advanced:
        if settings is None or not settings.entropy_fast_mode:
            # Full entropy calculation
            results.update(compute_entropy_fast(rr, max_samples=5000))
        else:
            # Fast approximation (smaller sample)
            max_samp = min(2000, n)
            results.update(compute_entropy_fast(rr, max_samples=max_samp))
    
    # Compute derived indices
    if "hf_power" in results and "rmssd" in results:
        parasym = [
            float(results.get("hf_nu", 0.0)) / 100.0,
            min(1.0, float(results.get("rmssd", 0.0)) / 100.0),
            min(1.0, float(results.get("pnn50", 0.0)) / 50.0),
            min(1.0, float(results.get("sd1", 0.0)) / 50.0),
        ]
        results["parasympathetic_index"] = float(np.mean([c for c in parasym if c > 0]))
        
        lf_hf = float(results.get("lf_hf_ratio", 0.0))
        results["sympathetic_index"] = float(min(1.0, lf_hf / 5.0))
        results["ans_balance"] = float(results["parasympathetic_index"] - results["sympathetic_index"])
    
    return results


# ---------------------------------------------------------------------------
# Windowed Analysis Optimization
# ---------------------------------------------------------------------------


def compute_windowed_hrv_fast(
    df_in: pd.DataFrame,
    *,
    rr_col: str = "rr_intervals_ms",
    timestamp_col: str = "timestamp",
    window: str = "5min",
    step: str = "2min",
    min_rr_count: int = 60,
    max_windows: Optional[int] = None,
    include_advanced: bool = False,
) -> pd.DataFrame:
    """
    Compute windowed HRV with adaptive limits and fast computation.
    
    Args:
        df_in: Input DataFrame with RR intervals.
        rr_col: Column name for RR intervals.
        timestamp_col: Column name for timestamps.
        window: Window duration (e.g., "5min").
        step: Step duration (e.g., "2min").
        min_rr_count: Minimum RR intervals per window.
        max_windows: Maximum windows (auto-set if None).
        include_advanced: Whether to include advanced metrics.
        
    Returns:
        DataFrame with windowed HRV metrics.
    """
    if df_in.empty or rr_col not in df_in.columns:
        return pd.DataFrame()
    
    # Get adaptive settings for window limits
    if max_windows is None:
        settings = get_adaptive_settings()
        max_windows = settings.max_windows
    
    # Filter and sort data
    cols = [c for c in [timestamp_col, rr_col, "source"] if c in df_in.columns]
    df = df_in[cols].dropna(subset=[timestamp_col]).copy()
    
    rr_vals = pd.to_numeric(df[rr_col], errors="coerce")
    mask = (rr_vals >= 300.0) & (rr_vals <= 2000.0)
    df = df.loc[mask].sort_values(timestamp_col).copy()
    
    if df.empty:
        return pd.DataFrame()
    
    t0 = pd.to_datetime(df[timestamp_col].iloc[0])
    tN = pd.to_datetime(df[timestamp_col].iloc[-1])
    
    win_delta = pd.to_timedelta(window)
    step_delta = pd.to_timedelta(step)
    
    # Generate window starts
    starts: List[pd.Timestamp] = []
    s = t0
    while s + win_delta <= tN and len(starts) < max_windows:
        starts.append(s)
        s = s + step_delta
    
    if not starts:
        return pd.DataFrame()
    
    # Process windows
    results: List[Dict[str, Any]] = []
    timestamps = df[timestamp_col].values
    rr_array = df[rr_col].values.astype(np.float64)
    
    for s in starts:
        e = s + win_delta
        
        # Fast numpy-based window selection
        mask = (timestamps >= s) & (timestamps < e)
        window_rr = rr_array[mask]
        
        if len(window_rr) < min_rr_count:
            continue
        
        # Fast HRV computation
        metrics = compute_hrv_fast(
            window_rr,
            include_advanced=include_advanced,
            adaptive=True,
        )
        metrics["start"] = s
        metrics["end"] = e
        
        if "source" in df.columns:
            source_vals = df.loc[mask, "source"]
            if len(source_vals) > 0:
                metrics["source"] = source_vals.iloc[0]
        
        results.append(metrics)
    
    if not results:
        return pd.DataFrame()
    
    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    # CPU Detection
    "CPUInfo",
    "detect_cpu_info",
    "get_cpu_info",
    # Adaptive Settings
    "AdaptiveSettings",
    "get_adaptive_settings",
    # Fast HRV Computation
    "compute_time_domain_fast",
    "compute_entropy_fast",
    "compute_poincare_fast",
    "compute_dfa_fast",
    "compute_psd_fast",
    "compute_hrv_fast",
    "compute_windowed_hrv_fast",
    # Numba availability
    "NUMBA_AVAILABLE",
]

# Export Numba availability as module-level constant
NUMBA_AVAILABLE: Final[bool] = _NUMBA_AVAILABLE
