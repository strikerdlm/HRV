"""
GPU Acceleration Module for HRV Computations.

Provides transparent GPU acceleration using CuPy (CUDA) when available,
with automatic fallback to NumPy/SciPy on CPU.

Requirements:
    - NVIDIA GPU with CUDA support
    - cupy-cuda12x (for CUDA 12.x) or cupy-cuda11x (for CUDA 11.x)
    
Install with: pip install cupy-cuda12x  # For RTX 5070 (CUDA 12)

Original Author: Dr. Diego Leonel Malpica Hincapié, MD
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple, Union

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    import cupy as cp  # type: ignore[import-untyped]

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GPU Detection and Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class GPUInfo:
    """Information about available GPU."""
    
    available: bool
    device_name: str
    compute_capability: Tuple[int, int]
    total_memory_gb: float
    free_memory_gb: float
    cuda_version: str
    cupy_version: str


@lru_cache(maxsize=1)
def detect_gpu() -> GPUInfo:
    """Detect NVIDIA GPU and CuPy availability.
    
    Returns:
        GPUInfo with GPU details or unavailable status.
    """
    try:
        import cupy as cp  # type: ignore[import-untyped]
        
        device = cp.cuda.Device(0)
        props = cp.cuda.runtime.getDeviceProperties(0)
        mem_info = device.mem_info
        
        return GPUInfo(
            available=True,
            device_name=props["name"].decode() if isinstance(props["name"], bytes) else str(props["name"]),
            compute_capability=(props["major"], props["minor"]),
            total_memory_gb=mem_info[1] / (1024**3),
            free_memory_gb=mem_info[0] / (1024**3),
            cuda_version=".".join(map(str, cp.cuda.runtime.runtimeGetVersion())),
            cupy_version=cp.__version__,
        )
    except ImportError:
        _LOGGER.info("CuPy not installed. GPU acceleration unavailable.")
        return GPUInfo(
            available=False,
            device_name="N/A",
            compute_capability=(0, 0),
            total_memory_gb=0.0,
            free_memory_gb=0.0,
            cuda_version="N/A",
            cupy_version="N/A",
        )
    except Exception as e:
        _LOGGER.warning("GPU detection failed: %s", e)
        return GPUInfo(
            available=False,
            device_name="N/A",
            compute_capability=(0, 0),
            total_memory_gb=0.0,
            free_memory_gb=0.0,
            cuda_version="N/A",
            cupy_version="N/A",
        )


def is_gpu_available() -> bool:
    """Check if GPU acceleration is available."""
    return detect_gpu().available


def get_array_module() -> Any:
    """Get the appropriate array module (CuPy or NumPy).
    
    Returns:
        cupy if GPU available, else numpy.
    """
    if is_gpu_available():
        import cupy as cp  # type: ignore[import-untyped]
        return cp
    return np


def to_gpu(arr: NDArray) -> Any:
    """Transfer array to GPU if available.
    
    Args:
        arr: NumPy array to transfer.
        
    Returns:
        CuPy array on GPU or original NumPy array.
    """
    if is_gpu_available():
        import cupy as cp  # type: ignore[import-untyped]
        return cp.asarray(arr)
    return arr


def to_cpu(arr: Any) -> NDArray:
    """Transfer array to CPU.
    
    Args:
        arr: CuPy or NumPy array.
        
    Returns:
        NumPy array on CPU.
    """
    if is_gpu_available():
        import cupy as cp  # type: ignore[import-untyped]
        if isinstance(arr, cp.ndarray):
            return cp.asnumpy(arr)
    return np.asarray(arr)


# ---------------------------------------------------------------------------
# GPU-Accelerated HRV Computations
# ---------------------------------------------------------------------------

def gpu_fft_psd(
    signal: NDArray[np.float64],
    fs: float = 4.0,
    nfft: Optional[int] = None,
) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Compute FFT-based power spectral density with GPU acceleration.
    
    Args:
        signal: Input signal (detrended RR intervals).
        fs: Sampling frequency in Hz.
        nfft: FFT length (default: next power of 2).
        
    Returns:
        Tuple of (frequencies, PSD).
    """
    xp = get_array_module()
    
    if nfft is None:
        nfft = max(256, 2 ** int(np.ceil(np.log2(len(signal)))))
    
    # Transfer to GPU if available
    sig_gpu = to_gpu(signal.astype(np.float64))
    
    # Apply Hanning window
    window = xp.hanning(len(sig_gpu))
    sig_windowed = sig_gpu * window
    
    # FFT
    fft_result = xp.fft.rfft(sig_windowed, n=nfft)
    psd = xp.abs(fft_result) ** 2 / len(sig_windowed)
    freqs = xp.fft.rfftfreq(nfft, 1.0 / fs)
    
    # Transfer back to CPU
    return to_cpu(freqs), to_cpu(psd)


def gpu_sample_entropy(
    data: NDArray[np.float64],
    m: int = 2,
    r_ratio: float = 0.2,
) -> float:
    """Compute sample entropy with GPU acceleration.
    
    This O(n²) algorithm benefits significantly from GPU parallelization.
    
    Args:
        data: Time series data.
        m: Embedding dimension.
        r_ratio: Tolerance ratio (r = r_ratio * std(data)).
        
    Returns:
        Sample entropy value.
    """
    if len(data) < m + 2:
        return 0.0
    
    xp = get_array_module()
    
    # Transfer to GPU
    x = to_gpu(data.astype(np.float64))
    n = len(x)
    r = r_ratio * float(xp.std(x))
    
    if r <= 0:
        return 0.0
    
    def count_matches(template_len: int) -> int:
        """Count template matches using GPU-accelerated distance matrix."""
        # Create all templates of length template_len
        num_templates = n - template_len
        if num_templates <= 1:
            return 0
        
        # Build template matrix (num_templates x template_len)
        templates = xp.zeros((num_templates, template_len), dtype=xp.float64)
        for i in range(template_len):
            templates[:, i] = x[i:i + num_templates]
        
        # Compute pairwise Chebyshev distances using broadcasting
        # This is the GPU-accelerated part
        count = 0
        batch_size = min(1000, num_templates)  # Process in batches for memory
        
        for i in range(0, num_templates, batch_size):
            end_i = min(i + batch_size, num_templates)
            batch = templates[i:end_i, :]
            
            # Compute distances from batch to all templates
            # Shape: (batch_size, num_templates, template_len)
            diff = xp.abs(batch[:, xp.newaxis, :] - templates[xp.newaxis, :, :])
            max_diff = xp.max(diff, axis=2)  # Chebyshev distance
            
            # Count matches (excluding self-matches on diagonal)
            matches = max_diff <= r
            # Zero out diagonal (self-matches) for the current batch
            for j in range(end_i - i):
                if i + j < num_templates:
                    matches[j, i + j] = False
            
            count += int(xp.sum(matches))
        
        return count // 2  # Each pair counted twice
    
    # Count matches for m and m+1
    b_count = count_matches(m)
    a_count = count_matches(m + 1)
    
    if b_count == 0:
        return 0.0
    
    # Sample entropy
    return float(-np.log(a_count / b_count)) if a_count > 0 else 0.0


def gpu_distance_matrix(
    data: NDArray[np.float64],
    embedding_dim: int = 2,
    delay: int = 1,
) -> NDArray[np.float64]:
    """Compute distance matrix for RQA with GPU acceleration.
    
    Args:
        data: Time series data.
        embedding_dim: Embedding dimension.
        delay: Time delay for embedding.
        
    Returns:
        Distance matrix (N x N).
    """
    xp = get_array_module()
    
    # Create embedded vectors
    n = len(data) - (embedding_dim - 1) * delay
    if n <= 0:
        return np.array([[]])
    
    x = to_gpu(data.astype(np.float64))
    
    # Build embedding matrix
    embedded = xp.zeros((n, embedding_dim), dtype=xp.float64)
    for i in range(embedding_dim):
        embedded[:, i] = x[i * delay:i * delay + n]
    
    # Compute pairwise Euclidean distances (GPU-accelerated)
    # Using broadcasting: ||a - b||² = ||a||² + ||b||² - 2*a·b
    sq_norms = xp.sum(embedded ** 2, axis=1)
    distances = xp.sqrt(
        xp.maximum(
            sq_norms[:, xp.newaxis] + sq_norms[xp.newaxis, :] - 2 * embedded @ embedded.T,
            0.0  # Numerical stability
        )
    )
    
    return to_cpu(distances)


def gpu_dfa(
    data: NDArray[np.float64],
    scales: Optional[NDArray[np.int64]] = None,
    order: int = 1,
) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Compute Detrended Fluctuation Analysis with GPU acceleration.
    
    Args:
        data: Time series data.
        scales: Box sizes to use (default: log-spaced from 4 to N/4).
        order: Polynomial order for detrending.
        
    Returns:
        Tuple of (scales, fluctuation function F(n)).
    """
    xp = get_array_module()
    
    n = len(data)
    if n < 16:
        return np.array([]), np.array([])
    
    # Default scales
    if scales is None:
        min_scale = 4
        max_scale = n // 4
        if max_scale <= min_scale:
            return np.array([]), np.array([])
        num_scales = min(20, max_scale - min_scale)
        scales = np.unique(np.logspace(
            np.log10(min_scale),
            np.log10(max_scale),
            num_scales,
        ).astype(np.int64))
    
    # Transfer to GPU
    x = to_gpu(data.astype(np.float64))
    
    # Integrate the signal (cumulative sum of deviations from mean)
    y = xp.cumsum(x - xp.mean(x))
    
    fluctuations = []
    valid_scales = []
    
    for scale in scales:
        scale = int(scale)
        if scale < 4 or scale > n // 2:
            continue
        
        num_segments = n // scale
        if num_segments < 2:
            continue
        
        # Compute fluctuation for each segment
        segment_flucts = []
        for seg in range(num_segments):
            start = seg * scale
            end = start + scale
            segment = y[start:end]
            
            # Fit polynomial trend (on CPU for simplicity)
            t = xp.arange(scale, dtype=xp.float64)
            if xp == np:
                coeffs = np.polyfit(t, segment, order)
                trend = np.polyval(coeffs, t)
            else:
                # CuPy polyfit
                coeffs = xp.polyfit(t, segment, order)
                trend = xp.polyval(coeffs, t)
            
            # RMS of detrended segment
            detrended = segment - trend
            rms = xp.sqrt(xp.mean(detrended ** 2))
            segment_flucts.append(float(rms))
        
        if segment_flucts:
            fluctuations.append(np.mean(segment_flucts))
            valid_scales.append(scale)
    
    return np.array(valid_scales), np.array(fluctuations)


# ---------------------------------------------------------------------------
# Benchmark Utilities
# ---------------------------------------------------------------------------

def benchmark_gpu(
    data_size: int = 10000,
    iterations: int = 5,
) -> dict[str, dict[str, float]]:
    """Benchmark GPU vs CPU performance for HRV operations.
    
    Args:
        data_size: Size of test data.
        iterations: Number of iterations per test.
        
    Returns:
        Dictionary with timing results.
    """
    import time
    
    # Generate test data
    np.random.seed(42)
    test_data = np.random.randn(data_size).astype(np.float64)
    test_data = np.cumsum(test_data) + 800  # Simulate RR intervals
    
    results: dict[str, dict[str, float]] = {}
    
    # FFT benchmark
    def bench_fft_cpu() -> None:
        from scipy import signal
        signal.welch(test_data, fs=4.0, nperseg=256)
    
    def bench_fft_gpu() -> None:
        gpu_fft_psd(test_data, fs=4.0)
    
    # Time CPU
    start = time.perf_counter()
    for _ in range(iterations):
        bench_fft_cpu()
    cpu_time = (time.perf_counter() - start) / iterations
    
    # Time GPU
    if is_gpu_available():
        # Warmup
        gpu_fft_psd(test_data[:100], fs=4.0)
        
        start = time.perf_counter()
        for _ in range(iterations):
            bench_fft_gpu()
        gpu_time = (time.perf_counter() - start) / iterations
    else:
        gpu_time = float("inf")
    
    results["fft_psd"] = {
        "cpu_ms": cpu_time * 1000,
        "gpu_ms": gpu_time * 1000,
        "speedup": cpu_time / gpu_time if gpu_time > 0 else 0,
    }
    
    # Sample entropy benchmark (smaller data due to O(n²))
    small_data = test_data[:1000]
    
    def bench_entropy_cpu() -> None:
        # Simple CPU implementation
        n = len(small_data)
        r = 0.2 * np.std(small_data)
        _ = sum(1 for i in range(n - 2) for j in range(i + 1, n - 2)
                if np.max(np.abs(small_data[i:i+2] - small_data[j:j+2])) < r)
    
    # Time CPU (fewer iterations due to O(n²))
    start = time.perf_counter()
    bench_entropy_cpu()
    cpu_time = time.perf_counter() - start
    
    # Time GPU
    if is_gpu_available():
        start = time.perf_counter()
        gpu_sample_entropy(small_data, m=2, r_ratio=0.2)
        gpu_time = time.perf_counter() - start
    else:
        gpu_time = float("inf")
    
    results["sample_entropy"] = {
        "cpu_ms": cpu_time * 1000,
        "gpu_ms": gpu_time * 1000,
        "speedup": cpu_time / gpu_time if gpu_time > 0 else 0,
        "data_size": len(small_data),
    }
    
    return results


# ---------------------------------------------------------------------------
# Context Manager for GPU Operations
# ---------------------------------------------------------------------------

class GPUContext:
    """Context manager for GPU operations with automatic memory management.
    
    Example:
        with GPUContext() as gpu:
            if gpu.available:
                result = gpu_fft_psd(data)
    """
    
    def __init__(self, device_id: int = 0) -> None:
        self.device_id = device_id
        self.available = is_gpu_available()
        self._device: Any = None
    
    def __enter__(self) -> "GPUContext":
        if self.available:
            import cupy as cp  # type: ignore[import-untyped]
            self._device = cp.cuda.Device(self.device_id)
            self._device.use()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.available and self._device is not None:
            import cupy as cp  # type: ignore[import-untyped]
            # Clear GPU memory cache
            cp.get_default_memory_pool().free_all_blocks()
            cp.get_default_pinned_memory_pool().free_all_blocks()


# ---------------------------------------------------------------------------
# Streamlit Integration
# ---------------------------------------------------------------------------

def render_gpu_status() -> None:
    """Render GPU status in Streamlit sidebar."""
    import streamlit as st
    
    gpu_info = detect_gpu()
    
    with st.sidebar.expander("🖥️ GPU Status", expanded=False):
        if gpu_info.available:
            st.success(f"✅ **{gpu_info.device_name}**")
            st.caption(f"CUDA {gpu_info.cuda_version} | CuPy {gpu_info.cupy_version}")
            st.caption(f"Memory: {gpu_info.free_memory_gb:.1f} / {gpu_info.total_memory_gb:.1f} GB free")
            st.caption(f"Compute: SM {gpu_info.compute_capability[0]}.{gpu_info.compute_capability[1]}")
            
            if st.button("Run Benchmark", key="gpu_benchmark"):
                with st.spinner("Benchmarking..."):
                    results = benchmark_gpu(data_size=5000, iterations=3)
                
                for op, times in results.items():
                    st.write(f"**{op}**")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("CPU", f"{times['cpu_ms']:.1f}ms")
                    col2.metric("GPU", f"{times['gpu_ms']:.1f}ms")
                    col3.metric("Speedup", f"{times.get('speedup', 0):.1f}x")
        else:
            st.warning("⚠️ GPU not available")
            st.caption("Install CuPy for GPU acceleration:")
            st.code("pip install cupy-cuda12x", language="bash")


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    "GPUInfo",
    "detect_gpu",
    "is_gpu_available",
    "get_array_module",
    "to_gpu",
    "to_cpu",
    "gpu_fft_psd",
    "gpu_sample_entropy",
    "gpu_distance_matrix",
    "gpu_dfa",
    "benchmark_gpu",
    "GPUContext",
    "render_gpu_status",
]

