"""Shared Streamlit rerun utilities with debouncing and circuit breaker.

This module provides a centralized, safe way to trigger Streamlit reruns
with built-in protections against rerun loops:

1. **Debouncing**: Minimum interval between reruns (default 0.5s)
2. **Circuit breaker**: Maximum reruns per time window (default 5 per 2s)
3. **Diagnostic logging**: Tracks rerun reasons for debugging

Usage:
    from rerun_utils import safe_rerun
    
    # In button handlers or state change callbacks:
    safe_rerun("user clicked refresh button")

All modules should use safe_rerun() instead of st.rerun() directly.
"""

from __future__ import annotations

import logging
import time
import traceback
from typing import Final, Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_RERUN_DEBOUNCE_KEY: Final[str] = "_last_rerun_time_mono"
_RERUN_DEBOUNCE_MIN_INTERVAL_SEC: Final[float] = 0.5

# Circuit breaker: prevent more than N reruns within a time window
_RERUN_CIRCUIT_BREAKER_KEY: Final[str] = "_rerun_circuit_breaker"
_RERUN_CIRCUIT_BREAKER_WINDOW_SEC: Final[float] = 2.0
_RERUN_CIRCUIT_BREAKER_MAX_RERUNS: Final[int] = 5

# Logging
_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def safe_rerun(reason: str = "") -> None:
    """Trigger st.rerun() with debouncing and circuit breaker protection.

    This function prevents rapid consecutive reruns that can cause UI loops.
    It implements two layers of protection:

    1. **Debounce**: If a rerun was triggered less than 0.5s ago, skip this call.
    2. **Circuit breaker**: If more than 5 reruns occurred in the last 2s, skip.

    Args:
        reason: Optional string describing why rerun was requested (for logging).
                Providing a reason helps debug rerun loops.

    Returns:
        None. If the rerun is allowed, st.rerun() is called (which raises
        a RerunException internally). If debounced or circuit-broken, returns
        silently without triggering a rerun.

    Example:
        >>> if st.button("Refresh"):
        ...     st.session_state["data"] = fetch_new_data()
        ...     safe_rerun("user clicked refresh")
    """
    now = time.monotonic()

    # Layer 1: Debounce - skip if too soon after last rerun
    last_rerun = st.session_state.get(_RERUN_DEBOUNCE_KEY, 0.0)
    if now - last_rerun < _RERUN_DEBOUNCE_MIN_INTERVAL_SEC:
        if reason:
            _LOGGER.debug(
                "Rerun debounced (reason=%s, delta=%.3fs)",
                reason,
                now - last_rerun,
            )
        return

    # Layer 2: Circuit breaker - prevent runaway rerun loops
    circuit_state = st.session_state.get(_RERUN_CIRCUIT_BREAKER_KEY, None)
    if circuit_state is None:
        circuit_state = {"timestamps": [], "tripped": False, "trip_time": None}
        st.session_state[_RERUN_CIRCUIT_BREAKER_KEY] = circuit_state

    # Check if circuit breaker is tripped (cooldown period)
    if circuit_state.get("tripped", False):
        trip_time = circuit_state.get("trip_time", 0.0)
        # Allow recovery after the window period
        if now - trip_time < _RERUN_CIRCUIT_BREAKER_WINDOW_SEC * 2:
            _LOGGER.warning(
                "Circuit breaker tripped - rerun blocked (reason=%s, trip_time=%.1fs ago)",
                reason,
                now - trip_time,
            )
            return
        else:
            # Reset circuit breaker
            circuit_state["tripped"] = False
            circuit_state["trip_time"] = None
            circuit_state["timestamps"] = []
            _LOGGER.info("Circuit breaker reset after cooldown")

    # Clean old timestamps outside the window
    cutoff = now - _RERUN_CIRCUIT_BREAKER_WINDOW_SEC
    timestamps = [t for t in circuit_state.get("timestamps", []) if t > cutoff]

    # Check if too many reruns in window
    if len(timestamps) >= _RERUN_CIRCUIT_BREAKER_MAX_RERUNS:
        circuit_state["tripped"] = True
        circuit_state["trip_time"] = now
        circuit_state["timestamps"] = timestamps
        st.session_state[_RERUN_CIRCUIT_BREAKER_KEY] = circuit_state
        _LOGGER.error(
            "Circuit breaker TRIPPED: %d reruns in %.1fs window (reason=%s)",
            len(timestamps),
            _RERUN_CIRCUIT_BREAKER_WINDOW_SEC,
            reason,
        )
        _log_rerun_stack_trace(reason)
        return

    # Record this rerun attempt
    timestamps.append(now)
    circuit_state["timestamps"] = timestamps
    st.session_state[_RERUN_CIRCUIT_BREAKER_KEY] = circuit_state
    st.session_state[_RERUN_DEBOUNCE_KEY] = now

    # Log the rerun
    if reason:
        _LOGGER.info("Rerun triggered: %s (count=%d/%d)", reason, len(timestamps), _RERUN_CIRCUIT_BREAKER_MAX_RERUNS)
        try:
            _log_rerun_trigger_external(reason)
        except Exception:  # pragma: no cover - logging should never crash app
            pass

    # Perform the actual rerun
    st.rerun()


def reset_circuit_breaker() -> None:
    """Manually reset the circuit breaker state.

    Call this when you know a batch of reruns is expected (e.g., after
    loading a new profile) to prevent false circuit breaker trips.
    """
    if _RERUN_CIRCUIT_BREAKER_KEY in st.session_state:
        st.session_state[_RERUN_CIRCUIT_BREAKER_KEY] = {
            "timestamps": [],
            "tripped": False,
            "trip_time": None,
        }
        _LOGGER.debug("Circuit breaker manually reset")


def get_rerun_stats() -> dict:
    """Get current rerun statistics for debugging.

    Returns:
        Dict with keys:
            - recent_count: Number of reruns in current window
            - is_tripped: Whether circuit breaker is tripped
            - last_rerun_ago: Seconds since last rerun
    """
    now = time.monotonic()
    last_rerun = st.session_state.get(_RERUN_DEBOUNCE_KEY, 0.0)
    circuit_state = st.session_state.get(_RERUN_CIRCUIT_BREAKER_KEY, {})

    cutoff = now - _RERUN_CIRCUIT_BREAKER_WINDOW_SEC
    recent = [t for t in circuit_state.get("timestamps", []) if t > cutoff]

    return {
        "recent_count": len(recent),
        "max_allowed": _RERUN_CIRCUIT_BREAKER_MAX_RERUNS,
        "is_tripped": circuit_state.get("tripped", False),
        "last_rerun_ago": now - last_rerun if last_rerun > 0 else None,
        "debounce_interval": _RERUN_DEBOUNCE_MIN_INTERVAL_SEC,
        "window_seconds": _RERUN_CIRCUIT_BREAKER_WINDOW_SEC,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _log_rerun_stack_trace(reason: str) -> None:
    """Log stack trace when circuit breaker trips to help identify the source."""
    stack = traceback.format_stack()
    # Filter out internal frames
    relevant_frames = [
        frame for frame in stack
        if "rerun_utils.py" not in frame
        and "streamlit" not in frame.lower()
        and "runpy.py" not in frame
    ]
    if relevant_frames:
        _LOGGER.error(
            "Rerun loop detected (reason=%s). Call stack:\n%s",
            reason,
            "".join(relevant_frames[-5:]),  # Last 5 relevant frames
        )


def _log_rerun_trigger_external(reason: str) -> None:
    """Call external logging function if available (from logging_config.py)."""
    try:
        from logging_config import log_rerun_trigger
        log_rerun_trigger(reason)
    except ImportError:
        pass  # logging_config not available
    except Exception:
        pass  # Don't crash on logging errors


# ---------------------------------------------------------------------------
# Compatibility alias
# ---------------------------------------------------------------------------

# Alias for backward compatibility with existing code that uses _safe_rerun
_safe_rerun = safe_rerun
