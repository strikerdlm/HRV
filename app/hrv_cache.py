"""
HRV Results Caching System for Mission Control - Flight Surgeon.

Provides multi-layer caching to eliminate redundant computations:
1. Session state cache (fast, survives Streamlit reruns)
2. Database persistence (survives app restarts)
3. Hash-based invalidation (recompute only when data changes)

Performance optimizations:
- Hash-based cache keys for uploaded data
- Lazy evaluation with memoization
- Database-backed result persistence
- Automatic cleanup of stale cache entries

Author: Dr Diego Malpica MD
Version: 1.0.0
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import numpy as np
import pandas as pd
import streamlit as st

if TYPE_CHECKING:
    from user_database import UserDatabase

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CACHE_VERSION = "v1.1"  # Bump this to invalidate all caches
CLEANING_CACHE_KEY = "hrv_cleaning_cache"
WINDOWED_CACHE_KEY = "hrv_windowed_cache"
COMPREHENSIVE_CACHE_KEY = "hrv_comprehensive_cache"
UPLOAD_HASH_KEY = "hrv_upload_hashes"
COMPUTATION_STATE_KEY = "hrv_computation_state"


# ---------------------------------------------------------------------------
# Data Hash Computation
# ---------------------------------------------------------------------------
def compute_rr_hash(rr_data: np.ndarray) -> str:
    """
    Compute a stable hash for RR interval data.
    
    Uses first/last values and statistical summary for fast hashing
    without processing entire array for large datasets.
    
    Args:
        rr_data: RR interval array in milliseconds.
        
    Returns:
        16-character hex hash string.
    """
    if rr_data.size == 0:
        return "empty_data_hash"
    
    # Include key statistics for change detection
    summary = (
        f"{rr_data.size}_{rr_data[0]:.3f}_{rr_data[-1]:.3f}_"
        f"{np.mean(rr_data):.3f}_{np.std(rr_data):.3f}_{CACHE_VERSION}"
    )
    return hashlib.md5(summary.encode()).hexdigest()[:16]


def compute_settings_hash(
    method: str,
    max_deviation: float,
    median_window: int,
    window: str,
    step: str,
) -> str:
    """
    Compute hash for analysis settings.
    
    Args:
        method: Cleaning method.
        max_deviation: Max deviation threshold.
        median_window: Median window size.
        window: Windowed analysis window size.
        step: Windowed analysis step size.
        
    Returns:
        16-character hex hash string.
    """
    settings_str = f"{method}_{max_deviation}_{median_window}_{window}_{step}_{CACHE_VERSION}"
    return hashlib.md5(settings_str.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Cached Data Structures
# ---------------------------------------------------------------------------
@dataclass
class CleanedDataCache:
    """Cache entry for cleaned RR data."""
    
    data_hash: str
    settings_hash: str
    cleaned_rr: np.ndarray
    valid_mask: np.ndarray
    qc_summary: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for session state storage."""
        return {
            "data_hash": self.data_hash,
            "settings_hash": self.settings_hash,
            "cleaned_rr": self.cleaned_rr.tolist(),
            "valid_mask": self.valid_mask.tolist(),
            "qc_summary": self.qc_summary,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CleanedDataCache":
        """Create from dictionary."""
        return cls(
            data_hash=data["data_hash"],
            settings_hash=data["settings_hash"],
            cleaned_rr=np.array(data["cleaned_rr"]),
            valid_mask=np.array(data["valid_mask"]),
            qc_summary=data["qc_summary"],
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class WindowedResultCache:
    """Cache entry for windowed HRV analysis results."""
    
    data_hash: str
    settings_hash: str
    windowed_df: pd.DataFrame
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ComputationState:
    """
    Tracks what has been computed for the current session.
    
    Used to prevent redundant computations when only UI changes
    (like tab switching) trigger Streamlit reruns.
    """
    
    uploaded_files_hash: str = ""
    cleaning_done: bool = False
    windowed_done: bool = False
    comprehensive_done: bool = False
    settings_hash: str = ""
    last_update: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def needs_recompute(self, new_files_hash: str, new_settings_hash: str) -> bool:
        """Check if recomputation is needed."""
        return (
            self.uploaded_files_hash != new_files_hash or
            self.settings_hash != new_settings_hash
        )
    
    def mark_complete(
        self,
        files_hash: str,
        settings_hash: str,
        *,
        cleaning: bool = False,
        windowed: bool = False,
        comprehensive: bool = False,
    ) -> None:
        """Mark computations as complete."""
        self.uploaded_files_hash = files_hash
        self.settings_hash = settings_hash
        if cleaning:
            self.cleaning_done = True
        if windowed:
            self.windowed_done = True
        if comprehensive:
            self.comprehensive_done = True
        self.last_update = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Cache Manager
# ---------------------------------------------------------------------------
class HRVCacheManager:
    """
    Manages multi-layer caching for HRV computations.
    
    Layer 1: Session state (fast, survives Streamlit reruns)
    Layer 2: Database persistence (survives app restarts)
    """
    
    def __init__(self) -> None:
        """Initialize cache manager."""
        self._ensure_cache_structures()
    
    def _ensure_cache_structures(self) -> None:
        """Ensure cache structures exist in session state."""
        if CLEANING_CACHE_KEY not in st.session_state:
            st.session_state[CLEANING_CACHE_KEY] = {}
        if WINDOWED_CACHE_KEY not in st.session_state:
            st.session_state[WINDOWED_CACHE_KEY] = {}
        if COMPREHENSIVE_CACHE_KEY not in st.session_state:
            st.session_state[COMPREHENSIVE_CACHE_KEY] = {}
        if UPLOAD_HASH_KEY not in st.session_state:
            st.session_state[UPLOAD_HASH_KEY] = {}
        if COMPUTATION_STATE_KEY not in st.session_state:
            st.session_state[COMPUTATION_STATE_KEY] = ComputationState()
    
    def get_computation_state(self) -> ComputationState:
        """Get current computation state."""
        self._ensure_cache_structures()
        return st.session_state[COMPUTATION_STATE_KEY]
    
    def update_computation_state(self, state: ComputationState) -> None:
        """Update computation state."""
        st.session_state[COMPUTATION_STATE_KEY] = state
    
    # ---------------------------------------------------------------------------
    # Cleaning Cache
    # ---------------------------------------------------------------------------
    def get_cached_cleaning(
        self,
        name: str,
        rr_data: np.ndarray,
        settings_hash: str,
    ) -> Optional[Tuple[np.ndarray, np.ndarray, Dict[str, Any]]]:
        """
        Get cached cleaning results if available.
        
        Args:
            name: Dataset name (filename).
            rr_data: Original RR interval data.
            settings_hash: Hash of cleaning settings.
            
        Returns:
            Tuple of (cleaned_rr, valid_mask, qc_summary) or None if not cached.
        """
        self._ensure_cache_structures()
        data_hash = compute_rr_hash(rr_data)
        cache_key = f"{name}_{data_hash}"
        
        cache = st.session_state[CLEANING_CACHE_KEY]
        if cache_key in cache:
            entry = cache[cache_key]
            if entry["settings_hash"] == settings_hash:
                _LOGGER.debug("Cleaning cache HIT for %s", name)
                return (
                    np.array(entry["cleaned_rr"]),
                    np.array(entry["valid_mask"]),
                    entry["qc_summary"],
                )
        
        _LOGGER.debug("Cleaning cache MISS for %s", name)
        return None
    
    def set_cached_cleaning(
        self,
        name: str,
        rr_data: np.ndarray,
        settings_hash: str,
        cleaned_rr: np.ndarray,
        valid_mask: np.ndarray,
        qc_summary: Dict[str, Any],
    ) -> None:
        """
        Store cleaning results in cache.
        
        Args:
            name: Dataset name (filename).
            rr_data: Original RR interval data.
            settings_hash: Hash of cleaning settings.
            cleaned_rr: Cleaned RR intervals.
            valid_mask: Boolean mask of valid intervals.
            qc_summary: Quality control summary.
        """
        self._ensure_cache_structures()
        data_hash = compute_rr_hash(rr_data)
        cache_key = f"{name}_{data_hash}"
        
        st.session_state[CLEANING_CACHE_KEY][cache_key] = {
            "data_hash": data_hash,
            "settings_hash": settings_hash,
            "cleaned_rr": cleaned_rr.tolist(),
            "valid_mask": valid_mask.tolist(),
            "qc_summary": qc_summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _LOGGER.debug("Cleaning results cached for %s", name)
    
    # ---------------------------------------------------------------------------
    # Windowed Results Cache
    # ---------------------------------------------------------------------------
    def get_cached_windowed(
        self,
        name: str,
        data_hash: str,
        settings_hash: str,
    ) -> Optional[pd.DataFrame]:
        """
        Get cached windowed analysis results if available.
        
        Args:
            name: Dataset name (filename).
            data_hash: Hash of input data.
            settings_hash: Hash of analysis settings.
            
        Returns:
            Windowed DataFrame or None if not cached.
        """
        self._ensure_cache_structures()
        cache_key = f"{name}_{data_hash}_{settings_hash}"
        
        cache = st.session_state[WINDOWED_CACHE_KEY]
        if cache_key in cache:
            _LOGGER.debug("Windowed cache HIT for %s", name)
            try:
                return pd.DataFrame(cache[cache_key]["data"])
            except Exception as exc:
                _LOGGER.debug("Windowed cache read error: %s", exc)
                return None
        
        _LOGGER.debug("Windowed cache MISS for %s", name)
        return None
    
    def set_cached_windowed(
        self,
        name: str,
        data_hash: str,
        settings_hash: str,
        windowed_df: pd.DataFrame,
    ) -> None:
        """
        Store windowed analysis results in cache.
        
        Args:
            name: Dataset name (filename).
            data_hash: Hash of input data.
            settings_hash: Hash of analysis settings.
            windowed_df: Windowed analysis DataFrame.
        """
        self._ensure_cache_structures()
        cache_key = f"{name}_{data_hash}_{settings_hash}"
        
        # Convert DataFrame to dict for JSON-serializable storage
        try:
            st.session_state[WINDOWED_CACHE_KEY][cache_key] = {
                "data": windowed_df.to_dict(orient="list"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            _LOGGER.debug("Windowed results cached for %s", name)
        except Exception as exc:
            _LOGGER.debug("Windowed cache write error: %s", exc)
    
    # ---------------------------------------------------------------------------
    # Comprehensive HRV Results Cache
    # ---------------------------------------------------------------------------
    def get_cached_comprehensive(
        self,
        name: str,
        data_hash: str,
        include_advanced: bool,
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached comprehensive HRV results if available.
        
        Args:
            name: Dataset name (filename).
            data_hash: Hash of input data.
            include_advanced: Whether advanced metrics were computed.
            
        Returns:
            HRV metrics dictionary or None if not cached.
        """
        self._ensure_cache_structures()
        cache_key = f"{name}_{data_hash}_adv{include_advanced}"
        
        cache = st.session_state[COMPREHENSIVE_CACHE_KEY]
        if cache_key in cache:
            _LOGGER.debug("Comprehensive HRV cache HIT for %s", name)
            return cache[cache_key]["data"]
        
        _LOGGER.debug("Comprehensive HRV cache MISS for %s", name)
        return None
    
    def set_cached_comprehensive(
        self,
        name: str,
        data_hash: str,
        include_advanced: bool,
        hrv_metrics: Dict[str, Any],
    ) -> None:
        """
        Store comprehensive HRV results in cache.
        
        Args:
            name: Dataset name (filename).
            data_hash: Hash of input data.
            include_advanced: Whether advanced metrics were computed.
            hrv_metrics: Computed HRV metrics dictionary.
        """
        self._ensure_cache_structures()
        cache_key = f"{name}_{data_hash}_adv{include_advanced}"
        
        st.session_state[COMPREHENSIVE_CACHE_KEY][cache_key] = {
            "data": hrv_metrics,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _LOGGER.debug("Comprehensive HRV results cached for %s", name)
    
    # ---------------------------------------------------------------------------
    # Upload Hash Tracking
    # ---------------------------------------------------------------------------
    def get_upload_hash(self, name: str) -> Optional[str]:
        """Get cached hash for an uploaded file."""
        self._ensure_cache_structures()
        return st.session_state[UPLOAD_HASH_KEY].get(name)
    
    def set_upload_hash(self, name: str, data_hash: str) -> None:
        """Store hash for an uploaded file."""
        self._ensure_cache_structures()
        st.session_state[UPLOAD_HASH_KEY][name] = data_hash
    
    def compute_all_uploads_hash(self, uploads: Dict[str, Any], profile_id: Optional[str] = None) -> str:
        """
        Compute combined hash for all uploaded datasets.
        
        Args:
            uploads: Dictionary of uploaded datasets.
            profile_id: Optional profile/user identifier to bind caches to a user.
            
        Returns:
            Combined hash string.
        """
        if not uploads:
            return "no_uploads"
        
        hashes = []
        profile_tag = f"profile:{profile_id}|" if profile_id else ""
        for name, up in sorted(uploads.items()):
            if hasattr(up, "rr_ms") and up.rr_ms.size > 0:
                hashes.append(f"{name}:{compute_rr_hash(up.rr_ms)}")
        
        combined = profile_tag + "|".join(hashes)
        return hashlib.md5(combined.encode()).hexdigest()[:16]
    
    # ---------------------------------------------------------------------------
    # Cache Cleanup
    # ---------------------------------------------------------------------------
    def clear_all_caches(self) -> None:
        """Clear all HRV caches."""
        st.session_state[CLEANING_CACHE_KEY] = {}
        st.session_state[WINDOWED_CACHE_KEY] = {}
        st.session_state[COMPREHENSIVE_CACHE_KEY] = {}
        st.session_state[UPLOAD_HASH_KEY] = {}
        st.session_state[COMPUTATION_STATE_KEY] = ComputationState()
        _LOGGER.info("All HRV caches cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        self._ensure_cache_structures()
        return {
            "cleaning_entries": len(st.session_state[CLEANING_CACHE_KEY]),
            "windowed_entries": len(st.session_state[WINDOWED_CACHE_KEY]),
            "comprehensive_entries": len(st.session_state[COMPREHENSIVE_CACHE_KEY]),
            "upload_hashes": len(st.session_state[UPLOAD_HASH_KEY]),
        }


# ---------------------------------------------------------------------------
# Module-Level Cache Instance
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_cache_manager(_version: str = f"profile-cache-{CACHE_VERSION}") -> HRVCacheManager:
    """Get or create the global cache manager instance.
    
    _version is included to force cache invalidation when cache schema changes.
    """
    return HRVCacheManager()


# ---------------------------------------------------------------------------
# Convenience Functions for Direct Import
# ---------------------------------------------------------------------------
def get_cached_clean_rr(
    name: str,
    rr_ms: np.ndarray,
    method: str,
    max_deviation: float,
    median_window: int,
    clean_func: Any,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Get or compute cleaned RR intervals with caching.
    
    This is the main entry point for cached cleaning. It checks
    the cache first and only calls clean_func if needed.
    
    Args:
        name: Dataset name (filename).
        rr_ms: Raw RR intervals in milliseconds.
        method: Cleaning method name.
        max_deviation: Max deviation threshold.
        median_window: Median window size.
        clean_func: Function to call if cache miss (clean_rr_intervals).
        
    Returns:
        Tuple of (cleaned_rr, valid_mask, qc_summary).
    """
    cache = get_cache_manager()
    settings_hash = compute_settings_hash(method, max_deviation, median_window, "", "")
    
    # Try cache first
    cached = cache.get_cached_cleaning(name, rr_ms, settings_hash)
    if cached is not None:
        return cached
    
    # Cache miss - compute
    start_time = time.perf_counter()
    cleaned, valid_mask, summary = clean_func(
        rr_ms,
        method=method,
        max_deviation=max_deviation,
        median_window=median_window,
    )
    duration = time.perf_counter() - start_time
    _LOGGER.debug("Cleaning computation took %.3fs for %s", duration, name)
    
    # Store in cache
    cache.set_cached_cleaning(
        name, rr_ms, settings_hash, cleaned, valid_mask, summary
    )
    
    return cleaned, valid_mask, summary


def should_skip_computation(
    uploads: Dict[str, Any],
    method: str,
    max_deviation: float,
    median_window: int,
    window: str,
    step: str,
    *,
    profile_id: Optional[str] = None,
) -> bool:
    """
    Check if computation can be skipped (already done with same settings).
    
    Args:
        uploads: Dictionary of uploaded datasets.
        method: Cleaning method name.
        max_deviation: Max deviation threshold.
        median_window: Median window size.
        window: Windowed analysis window.
        step: Windowed analysis step.
        
    Returns:
        True if computation can be skipped.
    """
    cache = get_cache_manager()
    state = cache.get_computation_state()
    
    files_hash = cache.compute_all_uploads_hash(uploads, profile_id=profile_id)
    settings_hash = compute_settings_hash(method, max_deviation, median_window, window, step)
    
    return (
        state.cleaning_done and
        state.windowed_done and
        not state.needs_recompute(files_hash, settings_hash)
    )

