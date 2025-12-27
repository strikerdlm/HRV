"""
Space Weather Progress Tracker Module

Provides modern, real-time progress indicators for space weather data fetching
operations. This module creates a visually appealing, informative progress
display that shows exactly what's happening behind the scenes.

Author: HRV Analysis Suite
Version: 1.0.0
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

import streamlit as st

try:
    from app.logging_config import get_logger, log_exception
except ImportError:
    from logging_config import get_logger, log_exception

_LOGGER = get_logger(__name__)

# Type variable for generic return types
T = TypeVar("T")


class StepStatus(Enum):
    """Status of a progress step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class ProgressStep:
    """Represents a single step in a multi-step operation."""

    step_id: str
    label: str
    description: str
    icon: str = "⏳"
    status: StepStatus = StepStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: str = ""
    result: Any = None
    substeps: List[str] = field(default_factory=list)
    current_substep: str = ""

    @property
    def elapsed_ms(self) -> Optional[float]:
        """Return elapsed time in milliseconds."""
        if self.start_time is None:
            return None
        end = self.end_time if self.end_time is not None else time.perf_counter()
        return (end - self.start_time) * 1000.0

    @property
    def elapsed_display(self) -> str:
        """Return human-readable elapsed time."""
        elapsed = self.elapsed_ms
        if elapsed is None:
            return ""
        if elapsed < 1000:
            return f"{elapsed:.0f}ms"
        return f"{elapsed / 1000:.1f}s"


@dataclass
class ProgressTracker:
    """Tracks progress of multiple steps in a space weather operation."""

    operation_name: str
    steps: Dict[str, ProgressStep] = field(default_factory=dict)
    step_order: List[str] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def add_step(
        self,
        step_id: str,
        label: str,
        description: str,
        icon: str = "⏳",
        substeps: Optional[List[str]] = None,
    ) -> None:
        """Add a step to the tracker."""
        with self._lock:
            self.steps[step_id] = ProgressStep(
                step_id=step_id,
                label=label,
                description=description,
                icon=icon,
                substeps=list(substeps) if substeps else [],
            )
            if step_id not in self.step_order:
                self.step_order.append(step_id)

    def start_operation(self) -> None:
        """Mark the operation as started."""
        with self._lock:
            self.start_time = time.perf_counter()

    def end_operation(self) -> None:
        """Mark the operation as ended."""
        with self._lock:
            self.end_time = time.perf_counter()

    def start_step(self, step_id: str) -> None:
        """Mark a step as running."""
        with self._lock:
            if step_id in self.steps:
                step = self.steps[step_id]
                step.status = StepStatus.RUNNING
                step.start_time = time.perf_counter()
                step.icon = "🔄"

    def update_substep(self, step_id: str, substep: str) -> None:
        """Update the current substep being processed."""
        with self._lock:
            if step_id in self.steps:
                self.steps[step_id].current_substep = substep

    def complete_step(self, step_id: str, result: Any = None) -> None:
        """Mark a step as complete."""
        with self._lock:
            if step_id in self.steps:
                step = self.steps[step_id]
                step.status = StepStatus.COMPLETE
                step.end_time = time.perf_counter()
                step.icon = "✅"
                step.result = result
                step.current_substep = ""

    def fail_step(self, step_id: str, error: str) -> None:
        """Mark a step as failed."""
        with self._lock:
            if step_id in self.steps:
                step = self.steps[step_id]
                step.status = StepStatus.ERROR
                step.end_time = time.perf_counter()
                step.icon = "❌"
                step.error_message = error
                step.current_substep = ""

    def timeout_step(self, step_id: str) -> None:
        """Mark a step as timed out."""
        with self._lock:
            if step_id in self.steps:
                step = self.steps[step_id]
                step.status = StepStatus.TIMEOUT
                step.end_time = time.perf_counter()
                step.icon = "⏰"
                step.error_message = "Operation timed out"
                step.current_substep = ""

    def skip_step(self, step_id: str, reason: str = "") -> None:
        """Mark a step as skipped."""
        with self._lock:
            if step_id in self.steps:
                step = self.steps[step_id]
                step.status = StepStatus.SKIPPED
                step.icon = "⏭️"
                step.error_message = reason or "Skipped"

    @property
    def total_elapsed_ms(self) -> Optional[float]:
        """Total elapsed time for the operation."""
        if self.start_time is None:
            return None
        end = self.end_time if self.end_time is not None else time.perf_counter()
        return (end - self.start_time) * 1000.0

    @property
    def completed_count(self) -> int:
        """Number of completed steps."""
        with self._lock:
            return sum(
                1
                for s in self.steps.values()
                if s.status in (StepStatus.COMPLETE, StepStatus.SKIPPED)
            )

    @property
    def total_count(self) -> int:
        """Total number of steps."""
        with self._lock:
            return len(self.steps)

    @property
    def progress_percent(self) -> float:
        """Progress percentage (0-100)."""
        total = self.total_count
        if total == 0:
            return 0.0
        return (self.completed_count / total) * 100.0

    @property
    def has_errors(self) -> bool:
        """Check if any step has errors."""
        with self._lock:
            return any(
                s.status in (StepStatus.ERROR, StepStatus.TIMEOUT)
                for s in self.steps.values()
            )


# -----------------------------------------------------------------------------
# CSS Styles for Modern Progress Display
# -----------------------------------------------------------------------------

PROGRESS_CSS = """
<style>
/* Progress Container */
.sw-progress-container {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Header */
.sw-progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.sw-progress-title {
    color: #e94560;
    font-size: 1.1em;
    font-weight: 600;
    letter-spacing: 0.5px;
}

.sw-progress-timer {
    color: #7ec8e3;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.95em;
    background: rgba(126, 200, 227, 0.1);
    padding: 4px 10px;
    border-radius: 6px;
}

/* Progress Bar */
.sw-progress-bar-container {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    height: 8px;
    margin-bottom: 20px;
    overflow: hidden;
}

.sw-progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #e94560 0%, #ff6b6b 50%, #feca57 100%);
    border-radius: 8px;
    transition: width 0.3s ease-out;
    animation: progress-pulse 1.5s ease-in-out infinite;
}

@keyframes progress-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.85; }
}

/* Step List */
.sw-step-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

/* Step Item */
.sw-step {
    display: flex;
    align-items: flex-start;
    padding: 12px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 8px;
    border-left: 3px solid transparent;
    transition: all 0.2s ease;
}

.sw-step-pending {
    border-left-color: #4a4a6a;
    opacity: 0.6;
}

.sw-step-running {
    border-left-color: #7ec8e3;
    background: rgba(126, 200, 227, 0.08);
    animation: step-glow 1s ease-in-out infinite alternate;
}

@keyframes step-glow {
    from { box-shadow: 0 0 5px rgba(126, 200, 227, 0.2); }
    to { box-shadow: 0 0 15px rgba(126, 200, 227, 0.4); }
}

.sw-step-complete {
    border-left-color: #2ed573;
}

.sw-step-error {
    border-left-color: #ff4757;
    background: rgba(255, 71, 87, 0.08);
}

.sw-step-timeout {
    border-left-color: #ffa502;
    background: rgba(255, 165, 2, 0.08);
}

.sw-step-skipped {
    border-left-color: #747d8c;
    opacity: 0.5;
}

/* Step Icon */
.sw-step-icon {
    font-size: 1.2em;
    margin-right: 12px;
    min-width: 28px;
    text-align: center;
}

.sw-step-running .sw-step-icon {
    animation: spin 1s linear infinite;
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

/* Step Content */
.sw-step-content {
    flex: 1;
}

.sw-step-label {
    color: #ffffff;
    font-weight: 500;
    font-size: 0.95em;
    margin-bottom: 2px;
}

.sw-step-description {
    color: #a4b0be;
    font-size: 0.8em;
    margin-bottom: 4px;
}

.sw-step-substep {
    color: #7ec8e3;
    font-size: 0.75em;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    padding: 4px 8px;
    background: rgba(126, 200, 227, 0.1);
    border-radius: 4px;
    margin-top: 6px;
    animation: substep-pulse 0.8s ease-in-out infinite alternate;
}

@keyframes substep-pulse {
    from { opacity: 0.7; }
    to { opacity: 1; }
}

.sw-step-error-msg {
    color: #ff6b81;
    font-size: 0.75em;
    margin-top: 4px;
    padding: 4px 8px;
    background: rgba(255, 71, 87, 0.1);
    border-radius: 4px;
}

/* Step Timer */
.sw-step-timer {
    color: #7ec8e3;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.75em;
    margin-left: 12px;
    white-space: nowrap;
}

/* Summary Footer */
.sw-progress-footer {
    margin-top: 16px;
    padding-top: 12px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.sw-progress-stats {
    display: flex;
    gap: 20px;
}

.sw-stat {
    text-align: center;
}

.sw-stat-value {
    color: #ffffff;
    font-size: 1.2em;
    font-weight: 600;
}

.sw-stat-label {
    color: #a4b0be;
    font-size: 0.7em;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.sw-stat-success .sw-stat-value { color: #2ed573; }
.sw-stat-error .sw-stat-value { color: #ff4757; }
.sw-stat-time .sw-stat-value { color: #7ec8e3; }

/* Live Indicator */
.sw-live-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    color: #2ed573;
    font-size: 0.8em;
}

.sw-live-dot {
    width: 8px;
    height: 8px;
    background: #2ed573;
    border-radius: 50%;
    animation: live-pulse 1s ease-in-out infinite;
}

@keyframes live-pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.3); opacity: 0.7; }
}
</style>
"""


def render_progress_html(tracker: ProgressTracker, is_running: bool = True) -> str:
    """Render the progress tracker as HTML."""
    steps_html = ""

    for step_id in tracker.step_order:
        if step_id not in tracker.steps:
            continue
        step = tracker.steps[step_id]

        status_class = f"sw-step-{step.status.value}"
        timer_html = ""
        if step.elapsed_ms is not None:
            timer_html = f'<span class="sw-step-timer">{step.elapsed_display}</span>'

        substep_html = ""
        if step.status == StepStatus.RUNNING and step.current_substep:
            substep_html = f'<div class="sw-step-substep">⟩ {step.current_substep}</div>'

        error_html = ""
        if step.status in (StepStatus.ERROR, StepStatus.TIMEOUT) and step.error_message:
            error_msg = step.error_message[:100] + "..." if len(step.error_message) > 100 else step.error_message
            error_html = f'<div class="sw-step-error-msg">⚠️ {error_msg}</div>'

        steps_html += f"""
        <div class="sw-step {status_class}">
            <span class="sw-step-icon">{step.icon}</span>
            <div class="sw-step-content">
                <div class="sw-step-label">{step.label}</div>
                <div class="sw-step-description">{step.description}</div>
                {substep_html}
                {error_html}
            </div>
            {timer_html}
        </div>
        """

    # Calculate stats
    success_count = sum(1 for s in tracker.steps.values() if s.status == StepStatus.COMPLETE)
    error_count = sum(1 for s in tracker.steps.values() if s.status in (StepStatus.ERROR, StepStatus.TIMEOUT))
    total_time = tracker.total_elapsed_ms
    time_display = f"{total_time / 1000:.1f}s" if total_time else "0.0s"

    progress_pct = min(100, max(0, tracker.progress_percent))

    live_indicator = ""
    if is_running:
        live_indicator = """
        <div class="sw-live-indicator">
            <span class="sw-live-dot"></span>
            <span>LIVE</span>
        </div>
        """

    html = f"""
    {PROGRESS_CSS}
    <div class="sw-progress-container">
        <div class="sw-progress-header">
            <span class="sw-progress-title">🛰️ {tracker.operation_name}</span>
            <span class="sw-progress-timer">⏱️ {time_display}</span>
        </div>
        <div class="sw-progress-bar-container">
            <div class="sw-progress-bar" style="width: {progress_pct}%;"></div>
        </div>
        <div class="sw-step-list">
            {steps_html}
        </div>
        <div class="sw-progress-footer">
            <div class="sw-progress-stats">
                <div class="sw-stat sw-stat-success">
                    <div class="sw-stat-value">{success_count}</div>
                    <div class="sw-stat-label">Complete</div>
                </div>
                <div class="sw-stat sw-stat-error">
                    <div class="sw-stat-value">{error_count}</div>
                    <div class="sw-stat-label">Errors</div>
                </div>
                <div class="sw-stat sw-stat-time">
                    <div class="sw-stat-value">{time_display}</div>
                    <div class="sw-stat-label">Elapsed</div>
                </div>
            </div>
            {live_indicator}
        </div>
    </div>
    """
    return html


def render_progress(tracker: ProgressTracker, container: Any, is_running: bool = True) -> None:
    """Render the progress tracker in a Streamlit container."""
    html = render_progress_html(tracker, is_running)
    container.markdown(html, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Pre-configured Progress Trackers for Space Weather Operations
# -----------------------------------------------------------------------------


def create_impact_prediction_tracker() -> ProgressTracker:
    """Create a progress tracker for impact predictions."""
    tracker = ProgressTracker(operation_name="Space Weather Impact Predictions")
    tracker.add_step(
        "photon",
        "☀️ X-ray / Photon Impact",
        "Fetching GOES X-ray flux data...",
        icon="⏳",
        substeps=["Connecting to SWPC", "Parsing X-ray data", "Classifying flare"],
    )
    tracker.add_step(
        "sep",
        "⚡ SEP / Proton Impact",
        "Fetching integral proton flux (≥10 MeV)...",
        icon="⏳",
        substeps=["Connecting to GOES", "Parsing proton data", "Classifying SEP event"],
    )
    tracker.add_step(
        "plasma",
        "🌊 Solar Wind Plasma",
        "Fetching L1 solar wind data...",
        icon="⏳",
        substeps=["Fetching plasma data", "Fetching magnetic field", "Computing arrival time"],
    )
    tracker.add_step(
        "cme",
        "💥 CME / Shock Forecast",
        "Querying NASA DONKI WSA+ENLIL...",
        icon="⏳",
        substeps=["Connecting to DONKI", "Processing simulations", "Computing arrival window"],
    )
    tracker.add_step(
        "geomagnetic",
        "🧲 Geomagnetic Activity",
        "Fetching Kp and Dst indices...",
        icon="⏳",
        substeps=["Fetching Kp index", "Fetching Dst index", "Classifying activity"],
    )
    return tracker


def create_donki_tracker(endpoints: List[str]) -> ProgressTracker:
    """Create a progress tracker for DONKI fetch."""
    tracker = ProgressTracker(operation_name="NASA DONKI Event Catalogs")

    endpoint_info = {
        "CME": ("💥 Coronal Mass Ejections", "Fetching CME catalog from NASA DONKI..."),
        "CMEAnalysis": ("📊 CME Analysis", "Fetching CME analysis data..."),
        "GST": ("🌐 Geomagnetic Storms", "Fetching geomagnetic storm reports..."),
        "IPS": ("📡 Interplanetary Shocks", "Fetching interplanetary shock data..."),
        "FLR": ("🔥 Solar Flares", "Fetching solar flare reports..."),
        "SEP": ("⚡ Solar Energetic Particles", "Fetching SEP event data..."),
        "MPC": ("🎯 Magnetopause Crossings", "Fetching magnetopause crossing data..."),
        "RBE": ("💫 Radiation Belt Enhancement", "Fetching radiation belt data..."),
        "HSS": ("💨 High Speed Streams", "Fetching high speed stream data..."),
        "WSAEnlilSimulations": ("🖥️ WSA+ENLIL Simulations", "Fetching CME propagation models..."),
    }

    for ep in endpoints:
        info = endpoint_info.get(ep, (f"📦 {ep}", f"Fetching {ep} data..."))
        tracker.add_step(ep, info[0], info[1], icon="⏳")

    return tracker


def create_noaa_tracker(dataset_keys: List[str]) -> ProgressTracker:
    """Create a progress tracker for NOAA space weather fetch."""
    tracker = ProgressTracker(operation_name="NOAA Space Weather Data")

    dataset_info = {
        "planetary_k_index_3h": ("🌍 Planetary Kp (3h)", "Fetching 3-hour Kp index..."),
        "planetary_k_index_1m": ("🌍 Planetary Kp (1m)", "Fetching 1-minute Kp index..."),
        "f107_flux": ("📻 F10.7 Flux", "Fetching solar radio flux (2.8 GHz)..."),
        "solar_wind_wind": ("🌊 Solar Wind Plasma", "Fetching solar wind speed/density..."),
        "solar_wind_mag": ("🧲 IMF", "Fetching interplanetary magnetic field..."),
        "goes_xray_flux": ("☀️ GOES X-ray", "Fetching X-ray flux (1-day)..."),
        "goes_integral_protons": ("⚡ GOES Protons", "Fetching integral proton flux..."),
        "geospace_dst": ("📉 Dst Index", "Fetching Dst storm-time index..."),
        "geospace_dst_7d": ("📉 Dst (7-day)", "Fetching 7-day Dst index..."),
        "geospace_pred_kp": ("🔮 Predicted Kp", "Fetching Kp forecast..."),
        "boulder_k_1m": ("🏔️ Boulder K", "Fetching Boulder local K index..."),
        "sunspots_monthly": ("🔵 Sunspots", "Fetching monthly sunspot number..."),
        "f107_smoothed": ("📻 F10.7 Smoothed", "Fetching smoothed F10.7..."),
        "predicted_f107": ("🔮 Predicted F10.7", "Fetching F10.7 forecast..."),
        "predicted_fredericksburg": ("🔮 Fredericksburg a-index", "Fetching a-index forecast..."),
        "predicted_monthly_ssn": ("🔮 Predicted SSN", "Fetching sunspot forecast..."),
        "solar_probabilities": ("📊 Flare Probabilities", "Fetching flare/proton probabilities..."),
        "solar_radio_multifrequency": ("📻 Multi-frequency Radio", "Fetching RSTN radio flux..."),
    }

    # Add SWPC Kp+F10.7 step first
    tracker.add_step(
        "swpc_kp_flux",
        "🛰️ SWPC Kp + F10.7",
        "Fetching primary SWPC datasets...",
        icon="⏳",
        substeps=["Fetching Kp index (30 days)", "Fetching solar radio flux"],
    )

    # Add individual NOAA datasets
    for key in dataset_keys:
        info = dataset_info.get(key, (f"📦 {key}", f"Fetching {key}..."))
        tracker.add_step(key, info[0], info[1], icon="⏳")

    return tracker


# -----------------------------------------------------------------------------
# Execution Helpers with Progress Tracking
# -----------------------------------------------------------------------------


def run_with_progress(
    tracker: ProgressTracker,
    step_id: str,
    fn: Callable[[], T],
    container: Any,
    *,
    timeout_s: float = 30.0,
    update_interval_s: float = 0.2,
) -> Tuple[Optional[T], Optional[str]]:
    """
    Run a function with live progress updates.

    Args:
        tracker: The progress tracker instance.
        step_id: The step ID to update.
        fn: The function to execute.
        container: Streamlit container for rendering.
        timeout_s: Maximum time to wait (seconds).
        update_interval_s: How often to update the display (seconds).

    Returns:
        (result, error) tuple. If successful, result is the return value and error is None.
        If failed, result is None and error contains the error message.
    """
    import concurrent.futures

    tracker.start_step(step_id)
    render_progress(tracker, container, is_running=True)

    result: Optional[T] = None
    error: Optional[str] = None

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn)

    try:
        start_time = time.perf_counter()
        while not future.done():
            elapsed = time.perf_counter() - start_time
            if elapsed >= timeout_s:
                tracker.timeout_step(step_id)
                error = f"Operation timed out after {timeout_s:.0f}s"
                break

            # Update display periodically
            time.sleep(min(update_interval_s, timeout_s - elapsed))
            render_progress(tracker, container, is_running=True)

        if error is None:
            try:
                result = future.result(timeout=max(0.1, timeout_s - (time.perf_counter() - start_time)))
                tracker.complete_step(step_id, result)
            except concurrent.futures.TimeoutError:
                tracker.timeout_step(step_id)
                error = f"Operation timed out after {timeout_s:.0f}s"
            except Exception as exc:
                tracker.fail_step(step_id, str(exc))
                error = str(exc)
                log_exception(_LOGGER, f"Step {step_id} failed", exc)

    finally:
        future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)

    render_progress(tracker, container, is_running=False)
    return result, error


def run_parallel_with_progress(
    tracker: ProgressTracker,
    step_functions: Dict[str, Callable[[], Any]],
    container: Any,
    *,
    overall_timeout_s: float = 60.0,
    update_interval_s: float = 0.3,
) -> Dict[str, Tuple[Any, Optional[str]]]:
    """
    Run multiple functions in parallel with live progress updates.

    Args:
        tracker: The progress tracker instance.
        step_functions: Mapping of step_id to function to execute.
        container: Streamlit container for rendering.
        overall_timeout_s: Maximum total time to wait (seconds).
        update_interval_s: How often to update the display (seconds).

    Returns:
        Dict mapping step_id to (result, error) tuple.
    """
    import concurrent.futures

    results: Dict[str, Tuple[Any, Optional[str]]] = {}
    tracker.start_operation()

    # Mark all steps as running
    for step_id in step_functions:
        tracker.start_step(step_id)

    render_progress(tracker, container, is_running=True)

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(step_functions))
    future_to_step: Dict[concurrent.futures.Future[Any], str] = {}

    for step_id, fn in step_functions.items():
        future = executor.submit(fn)
        future_to_step[future] = step_id

    try:
        start_time = time.perf_counter()

        while future_to_step:
            elapsed = time.perf_counter() - start_time
            remaining_timeout = max(0.1, overall_timeout_s - elapsed)

            if elapsed >= overall_timeout_s:
                # Timeout all remaining steps
                for future, step_id in list(future_to_step.items()):
                    if not future.done():
                        tracker.timeout_step(step_id)
                        results[step_id] = (None, f"Timed out after {overall_timeout_s:.0f}s")
                        future.cancel()
                break

            # Wait for any future to complete
            done, _ = concurrent.futures.wait(
                set(future_to_step.keys()),
                timeout=min(update_interval_s, remaining_timeout),
                return_when=concurrent.futures.FIRST_COMPLETED,
            )

            for future in done:
                step_id = future_to_step.pop(future)
                try:
                    result = future.result(timeout=0.1)
                    tracker.complete_step(step_id, result)
                    results[step_id] = (result, None)
                except concurrent.futures.TimeoutError:
                    tracker.timeout_step(step_id)
                    results[step_id] = (None, "Operation timed out")
                except Exception as exc:
                    tracker.fail_step(step_id, str(exc))
                    results[step_id] = (None, str(exc))
                    log_exception(_LOGGER, f"Parallel step {step_id} failed", exc)

            # Update display
            render_progress(tracker, container, is_running=bool(future_to_step))

    finally:
        tracker.end_operation()
        for future in future_to_step:
            future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)

    render_progress(tracker, container, is_running=False)
    return results


# -----------------------------------------------------------------------------
# Streamlit Session State Helpers
# -----------------------------------------------------------------------------


def get_progress_state(key: str = "sw_progress") -> Dict[str, Any]:
    """Get or create progress tracking state in session."""
    return st.session_state.setdefault(
        key,
        {
            "tracker": None,
            "is_running": False,
            "last_update": None,
        },
    )


def create_compact_progress_display(
    operation_name: str,
    steps: List[Dict[str, str]],
    container: Any,
) -> ProgressTracker:
    """
    Create and display a compact progress tracker.

    Args:
        operation_name: Name of the operation.
        steps: List of dicts with 'id', 'label', 'description' keys.
        container: Streamlit container for display.

    Returns:
        The created ProgressTracker.
    """
    tracker = ProgressTracker(operation_name=operation_name)
    for step in steps:
        tracker.add_step(
            step_id=step["id"],
            label=step["label"],
            description=step.get("description", ""),
            icon=step.get("icon", "⏳"),
        )
    render_progress(tracker, container, is_running=True)
    return tracker
