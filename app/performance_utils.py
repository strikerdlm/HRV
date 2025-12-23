"""
Performance Utilities for Mission Control - Flight Surgeon

Provides CPU-optimized caching, lazy loading, and computation management
to improve Streamlit app responsiveness.

Features (v1.1.0):
- Smart CPU detection and auto-tuning
- Adaptive performance presets based on hardware
- Session-state caching with TTL
- DataFrame optimization utilities
- Integration with cpu_optimization module

Author: AI Assistant
Version: 1.1.0
"""

from __future__ import annotations

import functools
import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Final, Optional, TypeVar

import numpy as np
import pandas as pd
import streamlit as st

# Type variable for generic caching
T = TypeVar("T")

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
_ENV_APP_MODE: Final[str] = "HRV_APP_MODE"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_CACHE_TTL_SECONDS: Final[int] = 300  # 5 minutes
HEAVY_COMPUTE_TTL_SECONDS: Final[int] = 600  # 10 minutes for heavy ops
NETWORK_CACHE_TTL_SECONDS: Final[int] = 180  # 3 minutes for network calls

# ---------------------------------------------------------------------------
# CPU Detection Integration
# ---------------------------------------------------------------------------
try:
    from app.cpu_optimization import (
        CPUInfo,
        get_cpu_info,
        get_adaptive_settings,
        AdaptiveSettings,
    )
    _CPU_OPTIMIZATION_AVAILABLE: Final[bool] = True
except ImportError:
    _CPU_OPTIMIZATION_AVAILABLE = False
    _LOGGER.debug("cpu_optimization module not available")


# ---------------------------------------------------------------------------
# Performance Metrics Tracking
# ---------------------------------------------------------------------------
@dataclass
class PerformanceMetrics:
    """Track app performance metrics."""
    
    compute_times: Dict[str, float] = field(default_factory=dict)
    cache_hits: int = 0
    cache_misses: int = 0
    last_full_rerun: Optional[datetime] = None
    
    def record_compute(self, operation: str, duration: float) -> None:
        """Record computation time for an operation."""
        self.compute_times[operation] = duration
    
    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self.cache_hits += 1
    
    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        self.cache_misses += 1
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        return {
            "cache_hit_rate": f"{self.cache_hit_rate:.1%}",
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "slowest_operations": sorted(
                self.compute_times.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:5],
        }


def get_performance_metrics() -> PerformanceMetrics:
    """Get or create performance metrics in session state."""
    if "performance_metrics" not in st.session_state:
        st.session_state["performance_metrics"] = PerformanceMetrics()
    return st.session_state["performance_metrics"]


# ---------------------------------------------------------------------------
# Smart Caching Utilities
# ---------------------------------------------------------------------------
def compute_hash(data: Any) -> str:
    """
    Compute a stable hash for any data structure.
    
    Args:
        data: Any hashable or array-like data
        
    Returns:
        MD5 hash string
    """
    if isinstance(data, np.ndarray):
        return hashlib.md5(data.tobytes()).hexdigest()[:16]
    if isinstance(data, pd.DataFrame):
        return hashlib.md5(
            pd.util.hash_pandas_object(data).values.tobytes()
        ).hexdigest()[:16]
    if isinstance(data, (list, tuple)):
        return hashlib.md5(str(data).encode()).hexdigest()[:16]
    return hashlib.md5(str(data).encode()).hexdigest()[:16]


def cached_in_session(
    key_prefix: str,
    ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to cache function results in session state with TTL.
    
    More efficient than st.cache_data for frequently-changing parameters
    because it avoids the global cache serialization overhead.
    
    Args:
        key_prefix: Prefix for the session state key
        ttl_seconds: Time-to-live in seconds
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            metrics = get_performance_metrics()
            
            # Build cache key from arguments
            args_hash = compute_hash((args, tuple(sorted(kwargs.items()))))
            cache_key = f"{key_prefix}_{args_hash}"
            timestamp_key = f"{cache_key}_timestamp"
            
            # Check if cached value exists and is valid
            if cache_key in st.session_state:
                cached_time = st.session_state.get(timestamp_key, datetime.min)
                if datetime.now() - cached_time < timedelta(seconds=ttl_seconds):
                    metrics.record_cache_hit()
                    return st.session_state[cache_key]
            
            # Compute and cache
            metrics.record_cache_miss()
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start_time
            
            metrics.record_compute(func.__name__, duration)
            
            st.session_state[cache_key] = result
            st.session_state[timestamp_key] = datetime.now()
            
            return result
        
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Lazy Loading Utilities
# ---------------------------------------------------------------------------
def lazy_load_tab_content(
    tab_name: str,
    render_func: Callable[[], None],
    *,
    heavy: bool = False,
) -> None:
    """
    Lazily load tab content only when the tab is active.
    
    Uses session state to track which tabs have been rendered
    and avoids re-rendering on every Streamlit rerun.
    
    Args:
        tab_name: Name of the tab (for state tracking)
        render_func: Function to render the tab content
        heavy: If True, show a loading message before rendering
    """
    state_key = f"tab_rendered_{tab_name}"
    
    if heavy:
        with st.spinner(f"Loading {tab_name}..."):
            render_func()
    else:
        render_func()
    
    st.session_state[state_key] = True


# ---------------------------------------------------------------------------
# Computation Throttling
# ---------------------------------------------------------------------------
class ComputeThrottler:
    """
    Throttle expensive computations to prevent CPU overload.
    
    Useful for operations that might be triggered rapidly by user input.
    """
    
    def __init__(self, min_interval_seconds: float = 0.5):
        """
        Initialize throttler.
        
        Args:
            min_interval_seconds: Minimum time between computations
        """
        self.min_interval = min_interval_seconds
        self._last_compute: Dict[str, float] = {}
    
    def should_compute(self, operation_id: str) -> bool:
        """
        Check if enough time has passed to allow computation.
        
        Args:
            operation_id: Unique identifier for the operation
            
        Returns:
            True if computation should proceed
        """
        now = time.time()
        last = self._last_compute.get(operation_id, 0)
        
        if now - last >= self.min_interval:
            self._last_compute[operation_id] = now
            return True
        return False
    
    def throttled(
        self, operation_id: str
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        Decorator to throttle function execution.
        
        Args:
            operation_id: Unique identifier for the operation
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
                if self.should_compute(operation_id):
                    return func(*args, **kwargs)
                return None
            return wrapper
        return decorator


def get_throttler() -> ComputeThrottler:
    """Get or create compute throttler in session state."""
    if "compute_throttler" not in st.session_state:
        st.session_state["compute_throttler"] = ComputeThrottler()
    return st.session_state["compute_throttler"]


# ---------------------------------------------------------------------------
# DataFrame Optimization
# ---------------------------------------------------------------------------
def optimize_dataframe(df: pd.DataFrame, *, copy: bool = True) -> pd.DataFrame:
    """
    Optimize DataFrame memory usage by downcasting dtypes.
    
    Args:
        df: Input DataFrame
        copy: Whether to copy the DataFrame first
        
    Returns:
        Memory-optimized DataFrame
    """
    if df.empty:
        return df
    
    result = df.copy() if copy else df
    
    for col in result.columns:
        col_type = result[col].dtype
        
        if col_type == "float64":
            result[col] = pd.to_numeric(result[col], downcast="float")
        elif col_type == "int64":
            result[col] = pd.to_numeric(result[col], downcast="integer")
        elif col_type == "object":
            # Try to convert to category if low cardinality
            if result[col].nunique() / len(result) < 0.5:
                result[col] = result[col].astype("category")
    
    return result


def sample_large_dataframe(
    df: pd.DataFrame,
    max_rows: int = 10000,
    *,
    preserve_edges: bool = True,
) -> pd.DataFrame:
    """
    Sample a large DataFrame for display/plotting while preserving structure.
    
    Args:
        df: Input DataFrame
        max_rows: Maximum number of rows to return
        preserve_edges: Keep first and last rows for time series
        
    Returns:
        Sampled DataFrame
    """
    if len(df) <= max_rows:
        return df
    
    if preserve_edges:
        edge_rows = max(10, max_rows // 20)
        middle_rows = max_rows - (2 * edge_rows)
        
        head = df.head(edge_rows)
        tail = df.tail(edge_rows)
        
        # Sample from middle
        middle_start = edge_rows
        middle_end = len(df) - edge_rows
        middle_indices = np.linspace(
            middle_start, middle_end - 1, middle_rows, dtype=int
        )
        middle = df.iloc[middle_indices]
        
        return pd.concat([head, middle, tail], ignore_index=True)
    
    # Simple random sample
    return df.sample(n=max_rows, random_state=42)


# ---------------------------------------------------------------------------
# Array Optimization
# ---------------------------------------------------------------------------
def downsample_array(
    arr: np.ndarray,
    max_points: int = 5000,
    method: str = "lttb",
) -> np.ndarray:
    """
    Downsample an array for efficient plotting.
    
    Args:
        arr: Input array
        max_points: Maximum number of points
        method: Downsampling method ('lttb' or 'uniform')
        
    Returns:
        Downsampled array
    """
    if len(arr) <= max_points:
        return arr
    
    if method == "uniform":
        indices = np.linspace(0, len(arr) - 1, max_points, dtype=int)
        return arr[indices]
    
    # LTTB (Largest Triangle Three Buckets) for better visual preservation
    # Simplified implementation
    bucket_size = len(arr) / max_points
    result = [arr[0]]  # Always keep first point
    
    for i in range(1, max_points - 1):
        bucket_start = int(i * bucket_size)
        bucket_end = int((i + 1) * bucket_size)
        bucket = arr[bucket_start:bucket_end]
        
        if len(bucket) > 0:
            # Pick point that creates largest triangle with neighbors
            result.append(bucket[len(bucket) // 2])
    
    result.append(arr[-1])  # Always keep last point
    return np.array(result)


# ---------------------------------------------------------------------------
# Performance Mode Settings
# ---------------------------------------------------------------------------

# Heavy computation categories for low-end computer optimization
HEAVY_COMPUTATIONS: Final[Dict[str, str]] = {
    "spectrogram": "Spectrogram Analysis (FFT over sliding windows)",
    "nonlinear": "Nonlinear Metrics (DFA, entropy, Poincaré)",
    "ml_clustering": "ML Pattern Detection (K-means clustering)",
    "windowed_hrv": "Windowed HRV Analysis (time-varying metrics)",
    "frequency_domain": "Frequency Domain Analysis (PSD, band powers)",
}

# Heavy download categories for low-bandwidth/metered connections
HEAVY_DOWNLOADS: Final[Dict[str, str]] = {
    "noaa_space": "NOAA Space Weather Data (multiple feeds)",
    "space_weather_live": "SpaceWeatherLive Data (web scraping)",
    "nasa_donki": "NASA DONKI Events (CME, SEP, flares)",
    "space_weather_impact": "Space Weather Impact Predictions",
    "gpt_interpretation": "GPT AI Interpretation (API call)",
}


def get_performance_settings() -> Dict[str, Any]:
    """
    Get performance settings from session state with auto-tuned defaults.
    
    Uses CPU detection to automatically select appropriate defaults
    for the current hardware.
    
    Returns:
        Dictionary of performance settings
    """
    # Auto-detect defaults based on CPU
    if _CPU_OPTIMIZATION_AVAILABLE:
        try:
            cpu_info = get_cpu_info()
            adaptive = get_adaptive_settings()
            
            # Set defaults based on CPU performance tier
            if cpu_info.performance_tier == "high":
                defaults = {
                    "enable_heavy_plots": True,
                    # Default to ultra-fast plotting for rapid identification demos.
                    # Users can raise this via Performance Preset / Custom sliders.
                    "max_plot_points": 500,
                    "max_dataframe_rows": 500,
                    "cache_ttl_seconds": DEFAULT_CACHE_TTL_SECONDS,
                    "throttle_interval": 0.3,
                    "optimize_memory": False,
                    "max_windows": adaptive.max_windows,
                    "use_fast_entropy": False,
                    "detected_tier": "high",
                    # Heavy computations enabled by default on high-end systems
                    "enable_spectrogram": True,
                    "enable_nonlinear": True,
                    "enable_ml_clustering": True,
                    "enable_windowed_hrv": True,
                    "enable_frequency_domain": True,
                    # Heavy downloads enabled by default
                    "enable_noaa_space": True,
                    "enable_space_weather_live": True,
                    "enable_nasa_donki": True,
                    "enable_space_weather_impact": True,
                    "enable_gpt_interpretation": True,
                }
            elif cpu_info.performance_tier == "medium":
                defaults = {
                    "enable_heavy_plots": False,
                    "max_plot_points": 500,
                    "max_dataframe_rows": 300,
                    "cache_ttl_seconds": DEFAULT_CACHE_TTL_SECONDS,
                    "throttle_interval": 0.5,
                    "optimize_memory": True,
                    "max_windows": adaptive.max_windows,
                    "use_fast_entropy": True,
                    "detected_tier": "medium",
                    # Some heavy computations disabled on medium systems
                    "enable_spectrogram": True,
                    "enable_nonlinear": True,
                    "enable_ml_clustering": False,
                    "enable_windowed_hrv": True,
                    "enable_frequency_domain": True,
                    # Heavy downloads enabled but can be toggled
                    "enable_noaa_space": True,
                    "enable_space_weather_live": True,
                    "enable_nasa_donki": False,
                    "enable_space_weather_impact": True,
                    "enable_gpt_interpretation": True,
                }
            else:  # low
                defaults = {
                    "enable_heavy_plots": False,
                    "max_plot_points": 500,
                    "max_dataframe_rows": 150,
                    "cache_ttl_seconds": DEFAULT_CACHE_TTL_SECONDS,
                    "throttle_interval": 0.8,
                    "optimize_memory": True,
                    "max_windows": adaptive.max_windows,
                    "use_fast_entropy": True,
                    "detected_tier": "low",
                    # Heavy computations disabled by default on low-end systems
                    "enable_spectrogram": False,
                    "enable_nonlinear": False,
                    "enable_ml_clustering": False,
                    "enable_windowed_hrv": False,
                    "enable_frequency_domain": True,
                    # Heavy downloads disabled by default
                    "enable_noaa_space": False,
                    "enable_space_weather_live": False,
                    "enable_nasa_donki": False,
                    "enable_space_weather_impact": False,
                    "enable_gpt_interpretation": False,
                }
        except Exception as exc:
            _LOGGER.debug("CPU auto-detection failed: %s", exc)
            defaults = _get_fallback_defaults()
    else:
        defaults = _get_fallback_defaults()
    
    if "performance_settings" not in st.session_state:
        st.session_state["performance_settings"] = defaults.copy()
    
    return st.session_state["performance_settings"]


def _get_fallback_defaults() -> Dict[str, Any]:
    """Get conservative fallback defaults when CPU detection is unavailable."""
    return {
        "enable_heavy_plots": False,
        "max_plot_points": 500,
        "max_dataframe_rows": 200,
        "cache_ttl_seconds": DEFAULT_CACHE_TTL_SECONDS,
        "throttle_interval": 0.5,
        "optimize_memory": True,
        "max_windows": 500,
        "use_fast_entropy": True,
        "detected_tier": "unknown",
        # Conservative defaults for heavy computations
        "enable_spectrogram": False,
        "enable_nonlinear": True,
        "enable_ml_clustering": False,
        "enable_windowed_hrv": True,
        "enable_frequency_domain": True,
        # Conservative defaults for heavy downloads
        "enable_noaa_space": True,
        "enable_space_weather_live": False,
        "enable_nasa_donki": False,
        "enable_space_weather_impact": True,
        "enable_gpt_interpretation": False,
    }


def is_computation_enabled(computation_key: str) -> bool:
    """
    Check if a heavy computation is enabled.
    
    Args:
        computation_key: Key from HEAVY_COMPUTATIONS dict
        
    Returns:
        True if the computation is enabled
    """
    # Operational mode: block research-grade heavy computations by policy.
    if os.environ.get(_ENV_APP_MODE, "").strip().lower() == "operational":
        return False
    settings = get_performance_settings()
    return settings.get(f"enable_{computation_key}", True)


def is_download_enabled(download_key: str) -> bool:
    """
    Check if a heavy download is enabled.
    
    Args:
        download_key: Key from HEAVY_DOWNLOADS dict
        
    Returns:
        True if the download is enabled
    """
    # Operational mode: block heavy downloads by policy (keep UI responsive).
    if os.environ.get(_ENV_APP_MODE, "").strip().lower() == "operational":
        return False
    settings = get_performance_settings()
    return settings.get(f"enable_{download_key}", True)


def render_performance_settings_sidebar() -> Dict[str, Any]:
    """
    Render performance settings in the sidebar with CPU auto-detection.
    
    Returns:
        Current performance settings
    """
    settings = get_performance_settings()
    
    with st.sidebar.expander("⚡ Performance Settings", expanded=False):
        # Show detected CPU tier
        tier = settings.get("detected_tier", "unknown")
        if tier != "unknown":
            tier_colors = {"high": "🟢", "medium": "🟡", "low": "🔴"}
            st.caption(f"{tier_colors.get(tier, '⚪')} Detected: {tier.upper()} performance CPU")
            
            if _CPU_OPTIMIZATION_AVAILABLE:
                cpu_info = get_cpu_info()
                st.caption(f"📍 {cpu_info.cpu_name[:40]}...")
        
        # Preset options - Auto is now the default
        presets = ["Auto (Recommended)", "Fast (Low CPU)", "Balanced", "Quality (High CPU)", "Custom"]
        
        # Determine current preset based on settings
        current_idx = 0  # Default to Auto
        
        preset = st.selectbox(
            "Performance Preset",
            options=presets,
            index=current_idx,
            help="Auto adjusts based on detected CPU capabilities",
        )
        
        if preset == "Auto (Recommended)":
            # Re-apply auto-detected settings
            new_settings = get_performance_settings()
            settings.update(new_settings)
            st.caption("✓ Using auto-detected optimal settings")
        elif preset == "Fast (Low CPU)":
            # Ultra-fast preset for rapid identification / demo use.
            settings["max_plot_points"] = 500
            settings["max_dataframe_rows"] = 150
            settings["max_windows"] = 200
            settings["enable_heavy_plots"] = False
            settings["optimize_memory"] = True
            settings["use_fast_entropy"] = True
            # Disable heavy computations for low-end systems
            settings["enable_spectrogram"] = False
            settings["enable_nonlinear"] = False
            settings["enable_ml_clustering"] = False
            settings["enable_windowed_hrv"] = False
            settings["enable_frequency_domain"] = True
            # Disable heavy downloads
            settings["enable_noaa_space"] = False
            settings["enable_space_weather_live"] = False
            settings["enable_nasa_donki"] = False
            settings["enable_space_weather_impact"] = False
            settings["enable_gpt_interpretation"] = False
        elif preset == "Quality (High CPU)":
            settings["max_plot_points"] = 5000
            settings["max_dataframe_rows"] = 1000
            settings["max_windows"] = 1000
            settings["enable_heavy_plots"] = True
            settings["optimize_memory"] = False
            settings["use_fast_entropy"] = False
            # Enable all heavy computations
            settings["enable_spectrogram"] = True
            settings["enable_nonlinear"] = True
            settings["enable_ml_clustering"] = True
            settings["enable_windowed_hrv"] = True
            settings["enable_frequency_domain"] = True
            # Enable all heavy downloads
            settings["enable_noaa_space"] = True
            settings["enable_space_weather_live"] = True
            settings["enable_nasa_donki"] = True
            settings["enable_space_weather_impact"] = True
            settings["enable_gpt_interpretation"] = True
        elif preset == "Balanced":
            settings["max_plot_points"] = 2000
            settings["max_dataframe_rows"] = 500
            settings["max_windows"] = 500
            settings["enable_heavy_plots"] = False
            settings["optimize_memory"] = True
            settings["use_fast_entropy"] = True
            # Some heavy computations enabled
            settings["enable_spectrogram"] = True
            settings["enable_nonlinear"] = True
            settings["enable_ml_clustering"] = False
            settings["enable_windowed_hrv"] = True
            settings["enable_frequency_domain"] = True
            # Some heavy downloads enabled
            settings["enable_noaa_space"] = True
            settings["enable_space_weather_live"] = True
            settings["enable_nasa_donki"] = False
            settings["enable_space_weather_impact"] = True
            settings["enable_gpt_interpretation"] = True
        
        # Only show sliders if Custom
        if preset == "Custom":
            settings["max_plot_points"] = st.slider(
                "Max plot points",
                min_value=500,
                max_value=10000,
                value=settings.get("max_plot_points", 1000),
                step=500,
                help="Reduce for faster rendering on slower CPUs",
            )
            
            settings["max_dataframe_rows"] = st.slider(
                "Max DataFrame rows to display",
                min_value=100,
                max_value=2000,
                value=settings.get("max_dataframe_rows", 200),
                step=100,
                help="Limit rows shown in data tables",
            )
            
            settings["max_windows"] = st.slider(
                "Max analysis windows",
                min_value=100,
                max_value=2000,
                value=settings.get("max_windows", 500),
                step=100,
                help="Limit windowed analysis iterations",
            )
            
            settings["enable_heavy_plots"] = st.checkbox(
                "Enable heavy visualizations",
                value=settings.get("enable_heavy_plots", False),
                help="Spectrograms, 3D plots, etc.",
            )
            
            settings["optimize_memory"] = st.checkbox(
                "Optimize memory usage",
                value=settings.get("optimize_memory", True),
                help="Downcast DataFrames to save memory",
            )
            
            settings["use_fast_entropy"] = st.checkbox(
                "Fast entropy mode",
                value=settings.get("use_fast_entropy", True),
                help="Use faster entropy approximations",
            )
            
            # Heavy computations section
            st.markdown("**🔬 Heavy Computations**")
            st.caption("Disable to improve performance on low-end systems")
            
            settings["enable_spectrogram"] = st.checkbox(
                "Spectrogram Analysis",
                value=settings.get("enable_spectrogram", True),
                help="FFT over sliding windows - CPU intensive",
                key="perf_spectrogram",
            )
            
            settings["enable_nonlinear"] = st.checkbox(
                "Nonlinear Metrics",
                value=settings.get("enable_nonlinear", True),
                help="DFA, entropy, Poincaré - CPU intensive",
                key="perf_nonlinear",
            )
            
            settings["enable_ml_clustering"] = st.checkbox(
                "ML Pattern Detection",
                value=settings.get("enable_ml_clustering", False),
                help="K-means clustering - CPU intensive",
                key="perf_ml_clustering",
            )
            
            settings["enable_windowed_hrv"] = st.checkbox(
                "Windowed HRV Analysis",
                value=settings.get("enable_windowed_hrv", True),
                help="Time-varying HRV metrics",
                key="perf_windowed_hrv",
            )
            
            settings["enable_frequency_domain"] = st.checkbox(
                "Frequency Domain Analysis",
                value=settings.get("enable_frequency_domain", True),
                help="PSD and band powers",
                key="perf_frequency_domain",
            )
            
            # Heavy downloads section
            st.markdown("**🌐 Network Downloads**")
            st.caption("Disable for offline use or slow connections")
            
            settings["enable_noaa_space"] = st.checkbox(
                "NOAA Space Weather",
                value=settings.get("enable_noaa_space", True),
                help="Multiple NOAA feeds - bandwidth intensive",
                key="perf_noaa_space",
            )
            
            settings["enable_space_weather_live"] = st.checkbox(
                "SpaceWeatherLive",
                value=settings.get("enable_space_weather_live", True),
                help="Web scraping - moderate bandwidth",
                key="perf_swl",
            )
            
            settings["enable_nasa_donki"] = st.checkbox(
                "NASA DONKI Events",
                value=settings.get("enable_nasa_donki", False),
                help="CME, SEP, flares - moderate bandwidth",
                key="perf_donki",
            )
            
            settings["enable_space_weather_impact"] = st.checkbox(
                "Space Weather Impact",
                value=settings.get("enable_space_weather_impact", True),
                help="Impact predictions - moderate bandwidth",
                key="perf_sw_impact",
            )
            
            settings["enable_gpt_interpretation"] = st.checkbox(
                "GPT AI Interpretation",
                value=settings.get("enable_gpt_interpretation", True),
                help="OpenAI API calls - requires API key",
                key="perf_gpt",
            )
        else:
            # Show current values as info
            st.caption(
                f"📊 Points: {settings.get('max_plot_points', 1000)} | "
                f"Rows: {settings.get('max_dataframe_rows', 200)} | "
                f"Windows: {settings.get('max_windows', 500)}"
            )
            
            # Show computation/download status
            enabled_comp = sum(1 for k in HEAVY_COMPUTATIONS if settings.get(f"enable_{k}", True))
            enabled_dl = sum(1 for k in HEAVY_DOWNLOADS if settings.get(f"enable_{k}", True))
            st.caption(f"🔬 Computations: {enabled_comp}/{len(HEAVY_COMPUTATIONS)} | 🌐 Downloads: {enabled_dl}/{len(HEAVY_DOWNLOADS)}")
        
        # Show current performance metrics
        if st.button("📈 Show Performance Stats", key="perf_stats_btn"):
            metrics = get_performance_metrics()
            summary = metrics.get_summary()
            st.caption(f"Cache hit rate: {summary['cache_hit_rate']}")
            if summary["slowest_operations"]:
                st.caption("Slowest operations:")
                for op, dur in summary["slowest_operations"][:3]:
                    st.caption(f"  • {op}: {dur:.2f}s")
    
    st.session_state["performance_settings"] = settings
    return settings


# ---------------------------------------------------------------------------
# Timed Execution Context Manager
# ---------------------------------------------------------------------------
class TimedExecution:
    """
    Context manager to time code execution and report to performance metrics.
    
    Example:
        with TimedExecution("heavy_computation"):
            result = expensive_function()
    """
    
    def __init__(self, operation_name: str, *, log: bool = False):
        """
        Initialize timed execution.
        
        Args:
            operation_name: Name of the operation for logging
            log: Whether to log timing to console
        """
        self.operation_name = operation_name
        self.log = log
        self.start_time: float = 0
        self.duration: float = 0
    
    def __enter__(self) -> "TimedExecution":
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args: Any) -> None:
        self.duration = time.perf_counter() - self.start_time
        metrics = get_performance_metrics()
        metrics.record_compute(self.operation_name, self.duration)
        
        if self.log:
            print(f"[PERF] {self.operation_name}: {self.duration:.3f}s")

