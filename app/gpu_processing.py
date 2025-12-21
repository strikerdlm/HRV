"""
GPU Processing Module for Mission Control - Flight Surgeon.

Provides NVIDIA CUDA-accelerated computation for CPU-intensive operations.
Automatically falls back to CPU when GPU is unavailable.

Supported GPUs: NVIDIA RTX series with CUDA support:
    - RTX 50xx (Blackwell, CC 12.0): CUDA 13.x
    - RTX 40xx (Ada Lovelace, CC 8.9): CUDA 12.x
    - RTX 30xx (Ampere, CC 8.6): CUDA 11.x/12.x
    - RTX 20xx (Turing, CC 7.5): CUDA 11.x

Author: AI Assistant
Version: 1.1.0

Requirements:
    - cupy-cuda13x (for RTX 50xx with CUDA 13.x)
    - cupy-cuda12x (for RTX 40xx/30xx with CUDA 12.x)
    - cupy-cuda11x (for RTX 20xx with CUDA 11.x)
    - Optional: cudf for GPU DataFrames
"""

from __future__ import annotations

import functools
import logging
import os
import platform
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Final, List, Optional, Tuple, TypeVar

import numpy as np

# Type variable for generic GPU operations
T = TypeVar("T")

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GPU Detection and Configuration
# ---------------------------------------------------------------------------


class GPUBackend(str, Enum):
    """Available GPU backends."""
    
    CUDA = "cuda"
    CPU = "cpu"
    AUTO = "auto"


@dataclass
class GPUInfo:
    """Information about detected GPU hardware."""
    
    available: bool = False
    device_name: str = "No GPU detected"
    device_id: int = -1
    total_memory_gb: float = 0.0
    free_memory_gb: float = 0.0
    cuda_version: str = "N/A"
    driver_version: str = "N/A"
    compute_capability: str = "N/A"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "available": self.available,
            "device_name": self.device_name,
            "device_id": self.device_id,
            "total_memory_gb": self.total_memory_gb,
            "free_memory_gb": self.free_memory_gb,
            "cuda_version": self.cuda_version,
            "driver_version": self.driver_version,
            "compute_capability": self.compute_capability,
        }


@dataclass
class GPUConfig:
    """GPU processing configuration."""
    
    enabled: bool = False
    backend: GPUBackend = GPUBackend.AUTO
    device_id: int = 0
    memory_limit_gb: Optional[float] = None
    fallback_to_cpu: bool = True
    log_operations: bool = False


# Global GPU state
_gpu_info: Optional[GPUInfo] = None
_gpu_config: Optional[GPUConfig] = None
_cupy_available: bool = False
_cp: Optional[Any] = None  # cupy module if available


def _detect_gpu() -> GPUInfo:
    """Detect available GPU hardware."""
    global _cupy_available, _cp
    
    info = GPUInfo()
    
    # Try to import cupy
    try:
        import cupy as cp
        _cp = cp
        _cupy_available = True
        
        device_count = max(0, int(cp.cuda.runtime.getDeviceCount()))
        if device_count == 0:
            info.device_name = "No CUDA devices found"
            return info

        preferred_env = os.getenv("HRV_GPU_DEVICE")
        preferred_id = int(preferred_env) if preferred_env and preferred_env.isdigit() else 0
        preferred_id = preferred_id % device_count

        # Try preferred device first, then fall back to others
        for offset in range(device_count):
            device_id = (preferred_id + offset) % device_count
            try:
                device = cp.cuda.Device(device_id)
                device.use()

                props = cp.cuda.runtime.getDeviceProperties(device_id)
                name = props["name"]
                info.device_id = device_id
                info.device_name = name.decode() if isinstance(name, bytes) else str(name)

                # Memory info
                total_mem = device.mem_info[1]
                free_mem = device.mem_info[0]
                info.total_memory_gb = total_mem / (1024 ** 3)
                info.free_memory_gb = free_mem / (1024 ** 3)

                # CUDA version
                cuda_ver = cp.cuda.runtime.runtimeGetVersion()
                info.cuda_version = f"{cuda_ver // 1000}.{(cuda_ver % 1000) // 10}"

                # Driver version
                driver_ver = cp.cuda.runtime.driverGetVersion()
                info.driver_version = f"{driver_ver // 1000}.{(driver_ver % 1000) // 10}"

                # Compute capability
                cc_major = props["major"]
                cc_minor = props["minor"]
                info.compute_capability = f"{cc_major}.{cc_minor}"

                # Validate GPU can actually run kernels (Blackwell sm_120 needs CUDA 12.8+)
                # Test with a simple kernel to ensure JIT compilation works
                try:
                    test_arr = cp.array([1.0, 2.0, 3.0])
                    _ = float(cp.mean(test_arr))  # This requires kernel compilation
                    info.available = True
                except Exception as kernel_exc:
                    # Kernel compilation failed - likely sm_120 without CUDA 12.8+ toolkit
                    if cc_major >= 12:
                        _LOGGER.warning(
                            "GPU %s detected (CC %s) but kernel compilation failed. "
                            "RTX 50xx (Blackwell) requires CUDA Toolkit 12.8+. "
                            "Current toolkit: %s. Error: %s",
                            info.device_name,
                            info.compute_capability,
                            info.cuda_version,
                            kernel_exc,
                        )
                        info.device_name = f"{info.device_name} (needs CUDA 12.8+)"
                        info.available = False
                    else:
                        _LOGGER.warning(
                            "GPU kernel compilation failed: %s", kernel_exc
                        )
                        info.available = False
                    break

                _LOGGER.info(
                    "GPU detected: %s (device %d, %.1f GB, CUDA %s, CC %s)",
                    info.device_name,
                    info.device_id,
                    info.total_memory_gb,
                    info.cuda_version,
                    info.compute_capability,
                )
                break
            except Exception as exc:  # bounded by device_count attempts
                _LOGGER.debug("GPU device %d unusable: %s", device_id, exc)

        if not info.available and "needs CUDA" not in info.device_name:
            info.device_name = "No usable CUDA device"
        
    except ImportError as exc:
        # Capture environment details for debugging mis-detected installs
        import sys
        import importlib.util

        spec = importlib.util.find_spec("cupy")
        hint = (
            "Module spec found at {0}".format(spec.origin)
            if spec and spec.origin
            else "Module spec not found"
        )
        _LOGGER.info(
            "CuPy not installed or not importable - GPU acceleration unavailable (%s). "
            "sys.executable=%s; %s",
            exc,
            sys.executable,
            hint,
        )
        info.device_name = "CuPy not installed"
        if os.getenv("HRV_GPU_REQUIRED", "").strip():
            raise
        
    except Exception as exc:
        _LOGGER.warning("GPU detection failed: %s", exc)
        info.device_name = f"Detection failed: {exc}"
    
    return info


def get_gpu_info(refresh: bool = False) -> GPUInfo:
    """
    Get GPU hardware information.
    
    Args:
        refresh: Force re-detection of GPU.
        
    Returns:
        GPUInfo with hardware details.
    """
    global _gpu_info
    
    if _gpu_info is None or refresh:
        _gpu_info = _detect_gpu()
    
    return _gpu_info


def get_gpu_config() -> GPUConfig:
    """Get current GPU configuration."""
    global _gpu_config
    if _gpu_config is None:
        # Probe GPU first so the default reflects real availability
        info = get_gpu_info()
        _gpu_config = GPUConfig(enabled=info.available and _cupy_available)
    
    return _gpu_config


def set_gpu_config(config: GPUConfig) -> None:
    """
    Set GPU configuration.
    
    Args:
        config: GPU configuration to apply.
    """
    global _gpu_config
    _gpu_config = config
    
    if config.enabled and _cupy_available:
        try:
            _cp.cuda.Device(config.device_id).use()
            _LOGGER.info("GPU processing enabled on device %d", config.device_id)
        except Exception as exc:
            _LOGGER.warning("Failed to enable GPU: %s", exc)


def is_gpu_enabled() -> bool:
    """Check if GPU processing is currently enabled and available."""
    config = get_gpu_config()
    info = get_gpu_info()
    return config.enabled and info.available and _cupy_available


# ---------------------------------------------------------------------------
# GPU-Accelerated Array Operations
# ---------------------------------------------------------------------------


def to_gpu(arr: np.ndarray) -> Any:
    """
    Transfer NumPy array to GPU.
    
    Args:
        arr: NumPy array to transfer.
        
    Returns:
        CuPy array on GPU, or original array if GPU unavailable.
    """
    if is_gpu_enabled() and _cp is not None:
        return _cp.asarray(arr)
    return arr


def to_cpu(arr: Any) -> np.ndarray:
    """
    Transfer array from GPU to CPU.
    
    Args:
        arr: Array (CuPy or NumPy) to transfer.
        
    Returns:
        NumPy array on CPU.
    """
    if _cupy_available and _cp is not None:
        if isinstance(arr, _cp.ndarray):
            return _cp.asnumpy(arr)
    return np.asarray(arr)


def get_array_module(arr: Any) -> Any:
    """
    Get the appropriate array module (numpy or cupy) for an array.
    
    Args:
        arr: Array to check.
        
    Returns:
        numpy or cupy module.
    """
    if _cupy_available and _cp is not None:
        return _cp.get_array_module(arr)
    return np


# ---------------------------------------------------------------------------
# GPU-Accelerated HRV Computations
# ---------------------------------------------------------------------------


def compute_rmssd_gpu(rr_intervals: np.ndarray) -> float:
    """
    Compute RMSSD using GPU acceleration if available.
    
    RMSSD = sqrt(mean(diff(RR)^2))
    
    Args:
        rr_intervals: RR intervals in milliseconds.
        
    Returns:
        RMSSD value in milliseconds.
    """
    if len(rr_intervals) < 2:
        return 0.0
    
    if is_gpu_enabled() and _cp is not None:
        try:
            rr_gpu = _cp.asarray(rr_intervals)
            diff_rr = _cp.diff(rr_gpu)
            rmssd = float(_cp.sqrt(_cp.mean(diff_rr ** 2)))
            return rmssd
        except Exception as exc:
            _LOGGER.debug("GPU RMSSD failed, using CPU: %s", exc)
    
    # CPU fallback
    diff_rr = np.diff(rr_intervals)
    return float(np.sqrt(np.mean(diff_rr ** 2)))


def compute_sdnn_gpu(rr_intervals: np.ndarray) -> float:
    """
    Compute SDNN using GPU acceleration if available.
    
    SDNN = std(RR)
    
    Args:
        rr_intervals: RR intervals in milliseconds.
        
    Returns:
        SDNN value in milliseconds.
    """
    if len(rr_intervals) < 2:
        return 0.0
    
    if is_gpu_enabled() and _cp is not None:
        try:
            rr_gpu = _cp.asarray(rr_intervals)
            sdnn = float(_cp.std(rr_gpu))
            return sdnn
        except Exception as exc:
            _LOGGER.debug("GPU SDNN failed, using CPU: %s", exc)
    
    return float(np.std(rr_intervals))


def compute_pnn50_gpu(rr_intervals: np.ndarray) -> float:
    """
    Compute pNN50 using GPU acceleration if available.
    
    pNN50 = (count where |diff(RR)| > 50) / (N-1) * 100
    
    Args:
        rr_intervals: RR intervals in milliseconds.
        
    Returns:
        pNN50 percentage.
    """
    if len(rr_intervals) < 2:
        return 0.0
    
    if is_gpu_enabled() and _cp is not None:
        try:
            rr_gpu = _cp.asarray(rr_intervals)
            diff_rr = _cp.diff(rr_gpu)
            count_above_50 = _cp.sum(_cp.abs(diff_rr) > 50)
            pnn50 = float(count_above_50 / len(diff_rr) * 100)
            return pnn50
        except Exception as exc:
            _LOGGER.debug("GPU pNN50 failed, using CPU: %s", exc)
    
    diff_rr = np.diff(rr_intervals)
    count_above_50 = np.sum(np.abs(diff_rr) > 50)
    return float(count_above_50 / len(diff_rr) * 100)


def compute_fft_psd_gpu(
    rr_intervals: np.ndarray,
    sampling_rate: float = 4.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute FFT-based PSD using GPU acceleration if available.
    
    Args:
        rr_intervals: RR intervals in milliseconds.
        sampling_rate: Sampling rate in Hz after interpolation.
        
    Returns:
        Tuple of (frequencies, power spectral density).
    """
    if len(rr_intervals) < 16:
        return np.array([]), np.array([])
    
    # Interpolate to uniform sampling
    time_points = np.cumsum(rr_intervals) / 1000.0  # Convert to seconds
    time_uniform = np.arange(time_points[0], time_points[-1], 1.0 / sampling_rate)
    rr_interp = np.interp(time_uniform, time_points, rr_intervals)
    
    # Remove mean
    rr_interp = rr_interp - np.mean(rr_interp)
    
    n = len(rr_interp)
    
    if is_gpu_enabled() and _cp is not None:
        try:
            rr_gpu = _cp.asarray(rr_interp)
            
            # FFT on GPU
            fft_result = _cp.fft.fft(rr_gpu)
            psd_gpu = (_cp.abs(fft_result) ** 2) / (n * sampling_rate)
            
            # Only positive frequencies
            psd = _cp.asnumpy(psd_gpu[:n // 2])
            freqs = np.fft.fftfreq(n, 1.0 / sampling_rate)[:n // 2]
            
            return freqs, psd
            
        except Exception as exc:
            _LOGGER.debug("GPU FFT failed, using CPU: %s", exc)
    
    # CPU fallback
    fft_result = np.fft.fft(rr_interp)
    psd = (np.abs(fft_result) ** 2) / (n * sampling_rate)
    freqs = np.fft.fftfreq(n, 1.0 / sampling_rate)
    
    return freqs[:n // 2], psd[:n // 2]


def compute_band_powers_gpu(
    freqs: np.ndarray,
    psd: np.ndarray,
) -> Dict[str, float]:
    """
    Compute HRV frequency band powers using GPU if available.
    
    Args:
        freqs: Frequency array from PSD.
        psd: Power spectral density array.
        
    Returns:
        Dictionary with VLF, LF, HF, and total power.
    """
    # Frequency bands
    vlf_band = (0.0033, 0.04)
    lf_band = (0.04, 0.15)
    hf_band = (0.15, 0.40)
    
    if is_gpu_enabled() and _cp is not None:
        try:
            freqs_gpu = _cp.asarray(freqs)
            psd_gpu = _cp.asarray(psd)
            
            # Create masks on GPU
            vlf_mask = (freqs_gpu >= vlf_band[0]) & (freqs_gpu < vlf_band[1])
            lf_mask = (freqs_gpu >= lf_band[0]) & (freqs_gpu < lf_band[1])
            hf_mask = (freqs_gpu >= hf_band[0]) & (freqs_gpu < hf_band[1])
            
            vlf = float(_cp.trapz(psd_gpu[vlf_mask], freqs_gpu[vlf_mask]))
            lf = float(_cp.trapz(psd_gpu[lf_mask], freqs_gpu[lf_mask]))
            hf = float(_cp.trapz(psd_gpu[hf_mask], freqs_gpu[hf_mask]))
            
            return {
                "vlf_power": vlf,
                "lf_power": lf,
                "hf_power": hf,
                "total_power": vlf + lf + hf,
                "lf_hf_ratio": lf / hf if hf > 0 else 0.0,
            }
            
        except Exception as exc:
            _LOGGER.debug("GPU band powers failed, using CPU: %s", exc)
    
    # CPU fallback
    vlf_mask = (freqs >= vlf_band[0]) & (freqs < vlf_band[1])
    lf_mask = (freqs >= lf_band[0]) & (freqs < lf_band[1])
    hf_mask = (freqs >= hf_band[0]) & (freqs < hf_band[1])
    
    vlf = float(np.trapz(psd[vlf_mask], freqs[vlf_mask])) if vlf_mask.any() else 0.0
    lf = float(np.trapz(psd[lf_mask], freqs[lf_mask])) if lf_mask.any() else 0.0
    hf = float(np.trapz(psd[hf_mask], freqs[hf_mask])) if hf_mask.any() else 0.0
    
    return {
        "vlf_power": vlf,
        "lf_power": lf,
        "hf_power": hf,
        "total_power": vlf + lf + hf,
        "lf_hf_ratio": lf / hf if hf > 0 else 0.0,
    }


def compute_poincare_gpu(
    rr_intervals: np.ndarray,
) -> Dict[str, float]:
    """
    Compute Poincaré plot metrics (SD1, SD2) using GPU if available.
    
    Args:
        rr_intervals: RR intervals in milliseconds.
        
    Returns:
        Dictionary with SD1, SD2, and SD1/SD2 ratio.
    """
    if len(rr_intervals) < 3:
        return {"sd1": 0.0, "sd2": 0.0, "sd1_sd2_ratio": 0.0}
    
    if is_gpu_enabled() and _cp is not None:
        try:
            rr_gpu = _cp.asarray(rr_intervals)
            
            rr_n = rr_gpu[:-1]
            rr_n1 = rr_gpu[1:]
            
            # SD1 and SD2 calculations
            diff = rr_n1 - rr_n
            sum_vals = rr_n1 + rr_n
            
            sd1 = float(_cp.std(diff) / _cp.sqrt(2))
            sd2 = float(_cp.std(sum_vals) / _cp.sqrt(2))
            
            return {
                "sd1": sd1,
                "sd2": sd2,
                "sd1_sd2_ratio": sd1 / sd2 if sd2 > 0 else 0.0,
            }
            
        except Exception as exc:
            _LOGGER.debug("GPU Poincaré failed, using CPU: %s", exc)
    
    # CPU fallback
    rr_n = rr_intervals[:-1]
    rr_n1 = rr_intervals[1:]
    
    diff = rr_n1 - rr_n
    sum_vals = rr_n1 + rr_n
    
    sd1 = float(np.std(diff) / np.sqrt(2))
    sd2 = float(np.std(sum_vals) / np.sqrt(2))
    
    return {
        "sd1": sd1,
        "sd2": sd2,
        "sd1_sd2_ratio": sd1 / sd2 if sd2 > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# GPU Benchmark
# ---------------------------------------------------------------------------


def benchmark_gpu(
    array_sizes: Optional[List[int]] = None,
    iterations: int = 5,
) -> Dict[str, Any]:
    """
    Benchmark GPU vs CPU performance.
    
    Args:
        array_sizes: List of array sizes to test.
        iterations: Number of iterations per size.
        
    Returns:
        Dictionary with benchmark results.
    """
    import time
    
    if array_sizes is None:
        array_sizes = [1000, 5000, 10000, 50000, 100000]
    
    results: Dict[str, Any] = {
        "gpu_available": is_gpu_enabled(),
        "gpu_info": get_gpu_info().to_dict(),
        "benchmark_date": datetime.now(timezone.utc).isoformat(),
        "tests": [],
    }
    
    for size in array_sizes:
        # Generate test data (realistic RR intervals)
        np.random.seed(42)
        rr = np.random.normal(800, 50, size).astype(np.float64)
        rr = np.clip(rr, 300, 2000)
        
        test_result = {
            "array_size": size,
            "cpu_time_ms": 0.0,
            "gpu_time_ms": 0.0,
            "speedup": 0.0,
        }
        
        # CPU benchmark
        cpu_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            _ = compute_rmssd_gpu.__wrapped__(rr) if hasattr(compute_rmssd_gpu, '__wrapped__') else np.sqrt(np.mean(np.diff(rr) ** 2))
            cpu_times.append((time.perf_counter() - start) * 1000)
        test_result["cpu_time_ms"] = float(np.median(cpu_times))
        
        # GPU benchmark (if available)
        if is_gpu_enabled() and _cp is not None:
            gpu_times = []
            for _ in range(iterations):
                start = time.perf_counter()
                rr_gpu = _cp.asarray(rr)
                diff_rr = _cp.diff(rr_gpu)
                _ = float(_cp.sqrt(_cp.mean(diff_rr ** 2)))
                _cp.cuda.stream.get_current_stream().synchronize()
                gpu_times.append((time.perf_counter() - start) * 1000)
            test_result["gpu_time_ms"] = float(np.median(gpu_times))
            
            if test_result["gpu_time_ms"] > 0:
                test_result["speedup"] = test_result["cpu_time_ms"] / test_result["gpu_time_ms"]
        
        results["tests"].append(test_result)
    
    return results


# ---------------------------------------------------------------------------
# Streamlit Integration
# ---------------------------------------------------------------------------


def render_gpu_settings_sidebar() -> GPUConfig:
    """
    Render GPU settings in Streamlit sidebar.
    
    Returns:
        Current GPU configuration.
    """
    import streamlit as st
    
    config = get_gpu_config()
    info = get_gpu_info()
    
    with st.sidebar.expander("🖥️ GPU Processing", expanded=False):
        st.caption("Hardware Acceleration")
        
        if info.available:
            st.success(f"✓ {info.device_name}")
            st.caption(f"VRAM: {info.free_memory_gb:.1f}/{info.total_memory_gb:.1f} GB free")
            st.caption(f"CUDA {info.cuda_version} | CC {info.compute_capability}")
            
            config.enabled = st.checkbox(
                "Enable GPU Processing",
                value=config.enabled,
                help="Use NVIDIA GPU for HRV computations",
            )
            
            if config.enabled:
                st.caption("✓ GPU acceleration active")
            
            if st.button("🔬 Run Benchmark", key="gpu_benchmark_btn"):
                with st.spinner("Benchmarking..."):
                    results = benchmark_gpu(array_sizes=[1000, 10000, 50000])
                    
                    for test in results["tests"]:
                        cols = st.columns(3)
                        cols[0].metric("Array", f"{test['array_size']:,}")
                        cols[1].metric("CPU", f"{test['cpu_time_ms']:.2f}ms")
                        if test["gpu_time_ms"] > 0:
                            cols[2].metric("GPU", f"{test['gpu_time_ms']:.2f}ms", f"{test['speedup']:.1f}x")
                        else:
                            cols[2].metric("GPU", "N/A")
        else:
            st.warning("No GPU detected")
            st.caption(info.device_name)
            
            # Check if it's a Blackwell GPU needing toolkit upgrade
            if "needs CUDA 12.8" in info.device_name:
                st.markdown("""
                **RTX 50xx (Blackwell) requires CUDA Toolkit 12.8+:**
                1. Download from [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-downloads)
                2. Install CUDA Toolkit 12.8 or newer
                3. Restart the app
                
                *Your GPU is detected but needs a newer CUDA Toolkit.*
                """)
            else:
                st.markdown("""
                **To enable GPU:**
                1. Install latest NVIDIA drivers
                2. Install CuPy for your GPU:
                   - **RTX 50xx**: `pip install cupy-cuda12x` + CUDA Toolkit 12.8+
                   - **RTX 40xx/30xx**: `pip install cupy-cuda12x`
                   - **RTX 20xx**: `pip install cupy-cuda11x`
                3. Restart the app
                """)
    
    set_gpu_config(config)
    return config


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Enums and Data Classes
    "GPUBackend",
    "GPUInfo",
    "GPUConfig",
    # Detection and Configuration
    "get_gpu_info",
    "get_gpu_config",
    "set_gpu_config",
    "is_gpu_enabled",
    # Array Operations
    "to_gpu",
    "to_cpu",
    "get_array_module",
    # GPU-Accelerated Computations
    "compute_rmssd_gpu",
    "compute_sdnn_gpu",
    "compute_pnn50_gpu",
    "compute_fft_psd_gpu",
    "compute_band_powers_gpu",
    "compute_poincare_gpu",
    # Utilities
    "benchmark_gpu",
    "render_gpu_settings_sidebar",
]

