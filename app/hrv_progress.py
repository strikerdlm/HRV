"""
HRV Analysis Progress Tracker Module

Provides modern, visually striking progress indicators for HRV computations
throughout the application. Features detailed step-by-step tracking with
real-time updates, timing information, and physiological context.

Design principles:
- Modern dark gradient aesthetic matching space weather progress
- Step-by-step detail with descriptions of what's happening
- Real-time elapsed time tracking per step
- Substep updates for granular progress
- Color-coded status (pending/running/complete/error)
- Animated elements for active steps

Author: HRV Analysis Suite
Version: 1.0.0

References:
- Task Force ESC/NASPE (1996). HRV measurement standards.
- Shaffer & Ginsberg (2017). HRV metrics and norms. Front Public Health.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

import streamlit as st

try:
    from app.logging_config import get_logger, log_exception
except ImportError:
    from logging_config import get_logger, log_exception

_LOGGER = get_logger(__name__)

T = TypeVar("T")


class HRVStepStatus(Enum):
    """Status of an HRV processing step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class HRVProgressStep:
    """Represents a single step in HRV processing."""

    step_id: str
    label: str
    description: str
    icon: str = "⏳"
    status: HRVStepStatus = HRVStepStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: str = ""
    result: Any = None
    substeps: List[str] = field(default_factory=list)
    current_substep: str = ""
    items_total: int = 0
    items_complete: int = 0

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

    @property
    def progress_percent(self) -> float:
        """Return progress percentage for this step (0-100)."""
        if self.items_total <= 0:
            return 100.0 if self.status == HRVStepStatus.COMPLETE else 0.0
        return min(100.0, (self.items_complete / self.items_total) * 100.0)


@dataclass
class HRVProgressTracker:
    """Tracks progress of HRV analysis pipeline."""

    operation_name: str
    steps: Dict[str, HRVProgressStep] = field(default_factory=dict)
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
        items_total: int = 0,
    ) -> None:
        """Add a step to the tracker."""
        with self._lock:
            self.steps[step_id] = HRVProgressStep(
                step_id=step_id,
                label=label,
                description=description,
                icon=icon,
                substeps=list(substeps) if substeps else [],
                items_total=items_total,
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
                step.status = HRVStepStatus.RUNNING
                step.start_time = time.perf_counter()
                step.icon = "🔄"

    def update_substep(self, step_id: str, substep: str) -> None:
        """Update the current substep being processed."""
        with self._lock:
            if step_id in self.steps:
                self.steps[step_id].current_substep = substep

    def update_progress(self, step_id: str, items_complete: int) -> None:
        """Update progress count for a step."""
        with self._lock:
            if step_id in self.steps:
                self.steps[step_id].items_complete = items_complete

    def complete_step(self, step_id: str, result: Any = None) -> None:
        """Mark a step as complete."""
        with self._lock:
            if step_id in self.steps:
                step = self.steps[step_id]
                step.status = HRVStepStatus.COMPLETE
                step.end_time = time.perf_counter()
                step.icon = "✅"
                step.result = result
                step.current_substep = ""
                step.items_complete = step.items_total

    def fail_step(self, step_id: str, error: str) -> None:
        """Mark a step as failed."""
        with self._lock:
            if step_id in self.steps:
                step = self.steps[step_id]
                step.status = HRVStepStatus.ERROR
                step.end_time = time.perf_counter()
                step.icon = "❌"
                step.error_message = error
                step.current_substep = ""

    def skip_step(self, step_id: str, reason: str = "") -> None:
        """Mark a step as skipped."""
        with self._lock:
            if step_id in self.steps:
                step = self.steps[step_id]
                step.status = HRVStepStatus.SKIPPED
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
                if s.status in (HRVStepStatus.COMPLETE, HRVStepStatus.SKIPPED)
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
                s.status == HRVStepStatus.ERROR
                for s in self.steps.values()
            )

    @property
    def current_step(self) -> Optional[HRVProgressStep]:
        """Get the currently running step."""
        with self._lock:
            for step_id in self.step_order:
                if step_id in self.steps and self.steps[step_id].status == HRVStepStatus.RUNNING:
                    return self.steps[step_id]
            return None


# -----------------------------------------------------------------------------
# CSS Styles for Modern HRV Progress Display
# -----------------------------------------------------------------------------

HRV_PROGRESS_CSS = """
<style>
/* HRV Progress Container */
.hrv-progress-container {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #0d1b2a 100%);
    border-radius: 16px;
    padding: 24px;
    margin: 16px 0;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 
                0 0 1px rgba(255, 255, 255, 0.1),
                inset 0 1px 0 rgba(255, 255, 255, 0.05);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    border: 1px solid rgba(255, 255, 255, 0.08);
}

/* Header */
.hrv-progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.hrv-progress-title {
    color: #ff6b6b;
    font-size: 1.2em;
    font-weight: 700;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.hrv-progress-title-icon {
    font-size: 1.4em;
    animation: pulse-heart 1s ease-in-out infinite;
}

@keyframes pulse-heart {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.1); }
}

.hrv-progress-timer {
    color: #4ecdc4;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.95em;
    background: rgba(78, 205, 196, 0.1);
    padding: 6px 14px;
    border-radius: 8px;
    border: 1px solid rgba(78, 205, 196, 0.2);
}

/* Main Progress Bar */
.hrv-main-progress-container {
    background: rgba(255, 255, 255, 0.03);
    border-radius: 12px;
    height: 12px;
    margin-bottom: 24px;
    overflow: hidden;
    position: relative;
}

.hrv-main-progress-bar {
    height: 100%;
    background: linear-gradient(90deg, 
        #ff6b6b 0%, 
        #ff9f43 25%, 
        #4ecdc4 50%, 
        #45b7d1 75%, 
        #a8e063 100%);
    border-radius: 12px;
    transition: width 0.4s ease-out;
    position: relative;
    overflow: hidden;
}

.hrv-main-progress-bar::after {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, 
        transparent, 
        rgba(255, 255, 255, 0.3), 
        transparent);
    animation: shimmer 2s infinite;
}

@keyframes shimmer {
    0% { left: -100%; }
    100% { left: 100%; }
}

/* Step List */
.hrv-step-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

/* Step Item */
.hrv-step {
    display: flex;
    align-items: flex-start;
    padding: 14px 16px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 12px;
    border-left: 4px solid transparent;
    transition: all 0.3s ease;
}

.hrv-step-pending {
    border-left-color: #3a3a5c;
    opacity: 0.5;
}

.hrv-step-running {
    border-left-color: #4ecdc4;
    background: rgba(78, 205, 196, 0.08);
    animation: step-glow 1.2s ease-in-out infinite alternate;
    opacity: 1;
}

@keyframes step-glow {
    from { box-shadow: 0 0 8px rgba(78, 205, 196, 0.2); }
    to { box-shadow: 0 0 20px rgba(78, 205, 196, 0.4); }
}

.hrv-step-complete {
    border-left-color: #a8e063;
    opacity: 1;
}

.hrv-step-error {
    border-left-color: #ff6b6b;
    background: rgba(255, 107, 107, 0.08);
}

.hrv-step-skipped {
    border-left-color: #747d8c;
    opacity: 0.4;
}

/* Step Icon */
.hrv-step-icon {
    font-size: 1.3em;
    margin-right: 14px;
    min-width: 32px;
    text-align: center;
}

.hrv-step-running .hrv-step-icon {
    animation: spin 1.2s linear infinite;
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

/* Step Content */
.hrv-step-content {
    flex: 1;
    min-width: 0;
}

.hrv-step-label {
    color: #ffffff;
    font-weight: 600;
    font-size: 0.95em;
    margin-bottom: 4px;
}

.hrv-step-description {
    color: #8892a0;
    font-size: 0.82em;
    margin-bottom: 6px;
    line-height: 1.4;
}

/* Step Progress Bar */
.hrv-step-progress-container {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 6px;
    height: 6px;
    margin-top: 8px;
    overflow: hidden;
}

.hrv-step-progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #4ecdc4 0%, #a8e063 100%);
    border-radius: 6px;
    transition: width 0.3s ease-out;
}

/* Substep */
.hrv-step-substep {
    color: #4ecdc4;
    font-size: 0.75em;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    padding: 6px 10px;
    background: rgba(78, 205, 196, 0.1);
    border-radius: 6px;
    margin-top: 8px;
    animation: substep-pulse 1s ease-in-out infinite alternate;
    display: flex;
    align-items: center;
    gap: 6px;
}

.hrv-substep-dot {
    width: 6px;
    height: 6px;
    background: #4ecdc4;
    border-radius: 50%;
    animation: dot-pulse 0.8s ease-in-out infinite;
}

@keyframes dot-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.8); }
}

@keyframes substep-pulse {
    from { opacity: 0.8; }
    to { opacity: 1; }
}

.hrv-step-error-msg {
    color: #ff6b6b;
    font-size: 0.75em;
    margin-top: 6px;
    padding: 6px 10px;
    background: rgba(255, 107, 107, 0.1);
    border-radius: 6px;
}

/* Step Timer */
.hrv-step-timer {
    color: #4ecdc4;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.75em;
    margin-left: 14px;
    white-space: nowrap;
    background: rgba(78, 205, 196, 0.1);
    padding: 4px 8px;
    border-radius: 4px;
}

/* Summary Footer */
.hrv-progress-footer {
    margin-top: 20px;
    padding-top: 16px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
}

.hrv-progress-stats {
    display: flex;
    gap: 24px;
}

.hrv-stat {
    text-align: center;
}

.hrv-stat-value {
    color: #ffffff;
    font-size: 1.3em;
    font-weight: 700;
}

.hrv-stat-label {
    color: #8892a0;
    font-size: 0.7em;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 2px;
}

.hrv-stat-success .hrv-stat-value { color: #a8e063; }
.hrv-stat-error .hrv-stat-value { color: #ff6b6b; }
.hrv-stat-time .hrv-stat-value { color: #4ecdc4; }
.hrv-stat-metrics .hrv-stat-value { color: #45b7d1; }

/* Live Indicator */
.hrv-live-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #a8e063;
    font-size: 0.85em;
    font-weight: 500;
}

.hrv-live-dot {
    width: 10px;
    height: 10px;
    background: #a8e063;
    border-radius: 50%;
    animation: live-pulse 1.2s ease-in-out infinite;
    box-shadow: 0 0 10px rgba(168, 224, 99, 0.5);
}

@keyframes live-pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.2); opacity: 0.7; }
}

/* Metric Categories */
.hrv-metrics-preview {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
}

.hrv-metric-badge {
    font-size: 0.7em;
    padding: 4px 10px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.05);
    color: #8892a0;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.hrv-metric-badge.time-domain { 
    background: rgba(255, 107, 107, 0.1); 
    color: #ff6b6b;
    border-color: rgba(255, 107, 107, 0.2);
}

.hrv-metric-badge.frequency { 
    background: rgba(78, 205, 196, 0.1); 
    color: #4ecdc4;
    border-color: rgba(78, 205, 196, 0.2);
}

.hrv-metric-badge.nonlinear { 
    background: rgba(168, 224, 99, 0.1); 
    color: #a8e063;
    border-color: rgba(168, 224, 99, 0.2);
}

.hrv-metric-badge.entropy { 
    background: rgba(69, 183, 209, 0.1); 
    color: #45b7d1;
    border-color: rgba(69, 183, 209, 0.2);
}

.hrv-metric-badge.fragmentation { 
    background: rgba(255, 159, 67, 0.1); 
    color: #ff9f43;
    border-color: rgba(255, 159, 67, 0.2);
}
</style>
"""


# -----------------------------------------------------------------------------
# Step Configurations with Scientific Context
# -----------------------------------------------------------------------------

HRV_STEP_CONFIGS = {
    "validate": {
        "label": "📋 Validating Input Data",
        "description": "Checking RR interval physiological bounds (300-2000 ms)",
        "icon": "📋",
        "substeps": ["Parsing file format", "Validating timestamps", "Checking RR bounds"],
    },
    "artifact_detect": {
        "label": "🔍 Artifact Detection",
        "description": "Identifying ectopic beats and motion artifacts using adaptive threshold",
        "icon": "🔍",
        "substeps": ["Computing moving median", "Calculating deviations", "Flagging artifacts"],
    },
    "artifact_correct": {
        "label": "🔧 Artifact Correction",
        "description": "Interpolating flagged intervals to preserve signal continuity",
        "icon": "🔧",
        "substeps": ["Linear interpolation", "Preserving signal length", "Quality metrics"],
    },
    "time_domain": {
        "label": "⏱️ Time-Domain Metrics",
        "description": "SDNN, RMSSD, pNN50 — statistical measures of NN interval variability",
        "icon": "⏱️",
        "substeps": ["Mean & SDNN", "RMSSD & pNN50", "NN20 & NN50 counts"],
    },
    "frequency_domain": {
        "label": "📊 Frequency-Domain Metrics",
        "description": "VLF, LF, HF power bands — spectral analysis of autonomic rhythms",
        "icon": "📊",
        "substeps": ["Interpolating RR series", "Welch PSD estimation", "Band power integration"],
    },
    "poincare": {
        "label": "⭕ Poincaré Analysis",
        "description": "SD1/SD2 ellipse metrics — short-term vs long-term variability",
        "icon": "⭕",
        "substeps": ["Computing scatter plot", "Fitting ellipse", "SD1/SD2 ratio"],
    },
    "dfa": {
        "label": "📈 Detrended Fluctuation Analysis",
        "description": "DFA α1/α2 — fractal scaling behavior of heart rate dynamics",
        "icon": "📈",
        "substeps": ["Cumulative sum profile", "Short-term scales (4-16)", "Long-term scales (16-64)"],
    },
    "entropy": {
        "label": "🔬 Entropy Metrics",
        "description": "ApEn, SampEn — complexity and regularity of RR time series",
        "icon": "🔬",
        "substeps": ["Template matching", "Approximate entropy", "Sample entropy"],
    },
    "fragmentation": {
        "label": "💔 Heart Rate Fragmentation",
        "description": "PIP, IALS, PSS — measures of HR acceleration/deceleration patterns",
        "icon": "💔",
        "substeps": ["Inflection point detection", "Segment analysis", "PIP & IALS computation"],
    },
    "geometric": {
        "label": "📐 Geometric Indices",
        "description": "HRV triangular index, TINN, Baevsky Stress Index",
        "icon": "📐",
        "substeps": ["Building histogram", "Triangular index", "Stress index"],
    },
    "advanced": {
        "label": "🧪 Advanced Nonlinear",
        "description": "RQA, MFDFA, permutation entropy — complexity science metrics",
        "icon": "🧪",
        "substeps": ["Recurrence analysis", "Multifractal DFA", "Symbolic dynamics"],
    },
    "autonomic": {
        "label": "🫀 Autonomic Indices",
        "description": "PNS/SNS balance, readiness score — integrated autonomic assessment",
        "icon": "🫀",
        "substeps": ["Parasympathetic index", "Sympathetic index", "ANS balance"],
    },
    "windowed": {
        "label": "📊 Windowed Analysis",
        "description": "Sliding window HRV computation for temporal dynamics",
        "icon": "📊",
        "substeps": ["Creating windows", "Computing per-window metrics", "Aggregating results"],
    },
    "covariate": {
        "label": "👤 Covariate Adjustment",
        "description": "Age/sex/BMI normalization using reference population data",
        "icon": "👤",
        "substeps": ["Loading norms", "Z-score computation", "Percentile ranking"],
    },
    "finalize": {
        "label": "✨ Finalizing Results",
        "description": "Assembling comprehensive HRV report with interpretations",
        "icon": "✨",
        "substeps": ["Merging metrics", "Quality assessment", "Ready for visualization"],
    },
}


def render_hrv_progress_html(
    tracker: HRVProgressTracker,
    is_running: bool = True,
    metrics_computed: int = 0,
) -> str:
    """Render the HRV progress tracker as HTML."""
    steps_html = ""

    for step_id in tracker.step_order:
        if step_id not in tracker.steps:
            continue
        step = tracker.steps[step_id]

        status_class = f"hrv-step-{step.status.value}"
        timer_html = ""
        if step.elapsed_ms is not None and step.status != HRVStepStatus.PENDING:
            timer_html = f'<span class="hrv-step-timer">{step.elapsed_display}</span>'

        substep_html = ""
        if step.status == HRVStepStatus.RUNNING and step.current_substep:
            substep_html = f'''
            <div class="hrv-step-substep">
                <span class="hrv-substep-dot"></span>
                {step.current_substep}
            </div>
            '''

        error_html = ""
        if step.status == HRVStepStatus.ERROR and step.error_message:
            error_msg = (
                step.error_message[:100] + "..."
                if len(step.error_message) > 100
                else step.error_message
            )
            error_html = f'<div class="hrv-step-error-msg">⚠️ {error_msg}</div>'

        # Step progress bar for running steps with item counts
        step_progress_html = ""
        if (
            step.status == HRVStepStatus.RUNNING
            and step.items_total > 0
        ):
            pct = step.progress_percent
            step_progress_html = f'''
            <div class="hrv-step-progress-container">
                <div class="hrv-step-progress-bar" style="width: {pct:.1f}%;"></div>
            </div>
            '''

        steps_html += f"""
        <div class="hrv-step {status_class}">
            <span class="hrv-step-icon">{step.icon}</span>
            <div class="hrv-step-content">
                <div class="hrv-step-label">{step.label}</div>
                <div class="hrv-step-description">{step.description}</div>
                {substep_html}
                {step_progress_html}
                {error_html}
            </div>
            {timer_html}
        </div>
        """

    # Calculate stats
    success_count = sum(
        1 for s in tracker.steps.values() if s.status == HRVStepStatus.COMPLETE
    )
    error_count = sum(
        1 for s in tracker.steps.values() if s.status == HRVStepStatus.ERROR
    )
    total_time = tracker.total_elapsed_ms
    time_display = f"{total_time / 1000:.1f}s" if total_time else "0.0s"

    progress_pct = min(100, max(0, tracker.progress_percent))

    live_indicator = ""
    if is_running:
        live_indicator = """
        <div class="hrv-live-indicator">
            <span class="hrv-live-dot"></span>
            <span>COMPUTING</span>
        </div>
        """

    html = f"""
    {HRV_PROGRESS_CSS}
    <div class="hrv-progress-container">
        <div class="hrv-progress-header">
            <span class="hrv-progress-title">
                <span class="hrv-progress-title-icon">🫀</span>
                {tracker.operation_name}
            </span>
            <span class="hrv-progress-timer">⏱️ {time_display}</span>
        </div>
        <div class="hrv-main-progress-container">
            <div class="hrv-main-progress-bar" style="width: {progress_pct}%;"></div>
        </div>
        <div class="hrv-step-list">
            {steps_html}
        </div>
        <div class="hrv-progress-footer">
            <div class="hrv-progress-stats">
                <div class="hrv-stat hrv-stat-success">
                    <div class="hrv-stat-value">{success_count}</div>
                    <div class="hrv-stat-label">Complete</div>
                </div>
                <div class="hrv-stat hrv-stat-error">
                    <div class="hrv-stat-value">{error_count}</div>
                    <div class="hrv-stat-label">Errors</div>
                </div>
                <div class="hrv-stat hrv-stat-metrics">
                    <div class="hrv-stat-value">{metrics_computed}</div>
                    <div class="hrv-stat-label">Metrics</div>
                </div>
                <div class="hrv-stat hrv-stat-time">
                    <div class="hrv-stat-value">{time_display}</div>
                    <div class="hrv-stat-label">Elapsed</div>
                </div>
            </div>
            {live_indicator}
        </div>
    </div>
    """
    return html


def render_hrv_progress(
    tracker: HRVProgressTracker,
    container: Any,
    is_running: bool = True,
    metrics_computed: int = 0,
) -> None:
    """Render the HRV progress tracker in a Streamlit container."""
    html = render_hrv_progress_html(tracker, is_running, metrics_computed)
    container.markdown(html, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Pre-configured HRV Progress Trackers
# -----------------------------------------------------------------------------


def create_hrv_analysis_tracker(
    *,
    include_cleaning: bool = True,
    include_frequency: bool = True,
    include_nonlinear: bool = True,
    include_advanced: bool = False,
    include_windowed: bool = True,
    include_covariate: bool = False,
    dataset_count: int = 1,
) -> HRVProgressTracker:
    """Create a progress tracker for full HRV analysis pipeline.

    Args:
        include_cleaning: Include artifact detection/correction steps.
        include_frequency: Include frequency-domain analysis.
        include_nonlinear: Include Poincaré and DFA.
        include_advanced: Include entropy, RQA, MFDFA.
        include_windowed: Include windowed analysis.
        include_covariate: Include covariate adjustment.
        dataset_count: Number of datasets being processed.

    Returns:
        Configured HRVProgressTracker.
    """
    tracker = HRVProgressTracker(operation_name="HRV Analysis Pipeline")

    # Input validation
    config = HRV_STEP_CONFIGS["validate"]
    tracker.add_step(
        "validate",
        config["label"],
        config["description"],
        config["icon"],
        config["substeps"],
        items_total=dataset_count,
    )

    # Artifact detection and correction
    if include_cleaning:
        config = HRV_STEP_CONFIGS["artifact_detect"]
        tracker.add_step(
            "artifact_detect",
            config["label"],
            config["description"],
            config["icon"],
            config["substeps"],
            items_total=dataset_count,
        )

        config = HRV_STEP_CONFIGS["artifact_correct"]
        tracker.add_step(
            "artifact_correct",
            config["label"],
            config["description"],
            config["icon"],
            config["substeps"],
            items_total=dataset_count,
        )

    # Time-domain
    config = HRV_STEP_CONFIGS["time_domain"]
    tracker.add_step(
        "time_domain",
        config["label"],
        config["description"],
        config["icon"],
        config["substeps"],
        items_total=dataset_count,
    )

    # Frequency-domain
    if include_frequency:
        config = HRV_STEP_CONFIGS["frequency_domain"]
        tracker.add_step(
            "frequency_domain",
            config["label"],
            config["description"],
            config["icon"],
            config["substeps"],
            items_total=dataset_count,
        )

    # Nonlinear
    if include_nonlinear:
        config = HRV_STEP_CONFIGS["poincare"]
        tracker.add_step(
            "poincare",
            config["label"],
            config["description"],
            config["icon"],
            config["substeps"],
            items_total=dataset_count,
        )

        config = HRV_STEP_CONFIGS["dfa"]
        tracker.add_step(
            "dfa",
            config["label"],
            config["description"],
            config["icon"],
            config["substeps"],
            items_total=dataset_count,
        )

    # Advanced (entropy, RQA, etc.)
    if include_advanced:
        config = HRV_STEP_CONFIGS["entropy"]
        tracker.add_step(
            "entropy",
            config["label"],
            config["description"],
            config["icon"],
            config["substeps"],
            items_total=dataset_count,
        )

        config = HRV_STEP_CONFIGS["fragmentation"]
        tracker.add_step(
            "fragmentation",
            config["label"],
            config["description"],
            config["icon"],
            config["substeps"],
            items_total=dataset_count,
        )

        config = HRV_STEP_CONFIGS["geometric"]
        tracker.add_step(
            "geometric",
            config["label"],
            config["description"],
            config["icon"],
            config["substeps"],
            items_total=dataset_count,
        )

        config = HRV_STEP_CONFIGS["advanced"]
        tracker.add_step(
            "advanced",
            config["label"],
            config["description"],
            config["icon"],
            config["substeps"],
            items_total=dataset_count,
        )

    # Autonomic indices
    config = HRV_STEP_CONFIGS["autonomic"]
    tracker.add_step(
        "autonomic",
        config["label"],
        config["description"],
        config["icon"],
        config["substeps"],
        items_total=dataset_count,
    )

    # Windowed analysis
    if include_windowed:
        config = HRV_STEP_CONFIGS["windowed"]
        tracker.add_step(
            "windowed",
            config["label"],
            config["description"],
            config["icon"],
            config["substeps"],
            items_total=dataset_count,
        )

    # Covariate adjustment
    if include_covariate:
        config = HRV_STEP_CONFIGS["covariate"]
        tracker.add_step(
            "covariate",
            config["label"],
            config["description"],
            config["icon"],
            config["substeps"],
            items_total=dataset_count,
        )

    # Finalize
    config = HRV_STEP_CONFIGS["finalize"]
    tracker.add_step(
        "finalize",
        config["label"],
        config["description"],
        config["icon"],
        config["substeps"],
        items_total=1,
    )

    return tracker


def create_windowed_analysis_tracker(window_count: int) -> HRVProgressTracker:
    """Create a tracker for windowed HRV analysis.

    Args:
        window_count: Number of windows to process.

    Returns:
        Configured HRVProgressTracker.
    """
    tracker = HRVProgressTracker(operation_name="Windowed HRV Analysis")

    tracker.add_step(
        "prepare",
        "📋 Preparing Windows",
        f"Creating {window_count} sliding windows for temporal analysis",
        "📋",
        ["Parsing timestamps", "Calculating boundaries", "Allocating memory"],
        items_total=1,
    )

    tracker.add_step(
        "compute",
        "⚡ Computing Window Metrics",
        "Processing each window for time-domain statistics",
        "⚡",
        ["Time-domain per window", "Optional frequency", "Progress tracking"],
        items_total=window_count,
    )

    tracker.add_step(
        "aggregate",
        "📊 Aggregating Results",
        "Combining window metrics into temporal DataFrame",
        "📊",
        ["Merging DataFrames", "Adding timestamps", "Quality checks"],
        items_total=1,
    )

    return tracker


def create_cleaning_tracker(dataset_count: int) -> HRVProgressTracker:
    """Create a tracker specifically for cleaning operations.

    Args:
        dataset_count: Number of datasets to clean.

    Returns:
        Configured HRVProgressTracker.
    """
    tracker = HRVProgressTracker(operation_name="RR Interval Cleaning")

    tracker.add_step(
        "validate",
        "📋 Input Validation",
        "Checking physiological bounds (300-2000 ms) and data integrity",
        "📋",
        ["File format check", "Timestamp validation", "Bounds filtering"],
        items_total=dataset_count,
    )

    tracker.add_step(
        "detect",
        "🔍 Artifact Detection",
        "Identifying ectopic beats using adaptive threshold method",
        "🔍",
        ["Moving median computation", "Deviation calculation", "Flagging outliers"],
        items_total=dataset_count,
    )

    tracker.add_step(
        "correct",
        "🔧 Artifact Correction",
        "Interpolating flagged intervals to preserve signal continuity",
        "🔧",
        ["Linear interpolation", "Edge handling", "Quality metrics"],
        items_total=dataset_count,
    )

    tracker.add_step(
        "summary",
        "✅ Quality Summary",
        "Generating cleaning statistics and QC report",
        "✅",
        ["Computing % flagged", "Artifact distribution", "Ready for analysis"],
        items_total=1,
    )

    return tracker


def create_comprehensive_metrics_tracker() -> HRVProgressTracker:
    """Create a tracker for comprehensive HRV metrics computation.

    Returns:
        Configured HRVProgressTracker with all metric categories.
    """
    tracker = HRVProgressTracker(operation_name="Comprehensive HRV Metrics")

    # Time-domain
    tracker.add_step(
        "time_domain",
        "⏱️ Time-Domain Metrics",
        "SDNN, RMSSD, pNN50, NN50, Mean HR — statistical NN variability",
        "⏱️",
        ["Mean & SD computations", "Successive differences", "Threshold crossings"],
    )

    # Frequency-domain
    tracker.add_step(
        "frequency",
        "📊 Frequency-Domain Metrics",
        "VLF (0.003-0.04 Hz), LF (0.04-0.15 Hz), HF (0.15-0.4 Hz) power bands",
        "📊",
        ["RR interpolation @ 4 Hz", "Welch periodogram", "Band power integration"],
    )

    # Poincaré
    tracker.add_step(
        "poincare",
        "⭕ Poincaré Nonlinear",
        "SD1 (short-term), SD2 (long-term), SD1/SD2 ratio, ellipse area",
        "⭕",
        ["Lag-1 scatter plot", "Ellipse fitting", "SD metrics extraction"],
    )

    # DFA
    tracker.add_step(
        "dfa",
        "📈 Detrended Fluctuation",
        "DFA α1 (4-16 beats), α2 (16-64 beats) — fractal scaling exponents",
        "📈",
        ["Profile integration", "Box detrending", "Log-log regression"],
    )

    # Geometric
    tracker.add_step(
        "geometric",
        "📐 Geometric Indices",
        "HRV triangular index, TINN, Baevsky Stress Index",
        "📐",
        ["Histogram construction", "Baseline triangular fit", "Stress formula"],
    )

    # Entropy
    tracker.add_step(
        "entropy",
        "🔬 Entropy Metrics",
        "Approximate Entropy (ApEn), Sample Entropy (SampEn) — m=2, r=0.2×SD",
        "🔬",
        ["Template embedding", "Distance matrix", "Conditional probability"],
    )

    # Fragmentation
    tracker.add_step(
        "fragmentation",
        "💔 Heart Rate Fragmentation",
        "PIP, IALS, PSS, W metrics — acceleration/deceleration patterns",
        "💔",
        ["Sign change detection", "Segment length analysis", "W3 classification"],
    )

    # Advanced nonlinear
    tracker.add_step(
        "advanced",
        "🧪 Advanced Nonlinear",
        "RQA, PRSA, MFDFA, Permutation Entropy, Symbolic Dynamics",
        "🧪",
        ["Recurrence plot", "Phase-rectified averaging", "Multifractal spectrum"],
    )

    # Autonomic indices
    tracker.add_step(
        "autonomic",
        "🫀 Autonomic Indices",
        "PNS index, SNS index, ANS balance — integrated assessment",
        "🫀",
        ["Vagal markers aggregation", "Sympathetic estimation", "Balance computation"],
    )

    return tracker


# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------


def estimate_computation_time(
    n_intervals: int,
    include_frequency: bool = True,
    include_advanced: bool = False,
) -> float:
    """Estimate computation time in seconds based on data size.

    Args:
        n_intervals: Number of RR intervals.
        include_frequency: Whether frequency analysis is enabled.
        include_advanced: Whether advanced metrics are enabled.

    Returns:
        Estimated time in seconds.
    """
    # Base time for time-domain (very fast)
    base_time = 0.1

    # Frequency adds O(n log n) for FFT
    if include_frequency:
        base_time += 0.2 + (n_intervals / 10000) * 0.1

    # Advanced metrics are O(n²) for entropy
    if include_advanced:
        base_time += 0.5 + (n_intervals / 5000) ** 2 * 0.5

    return min(base_time, 60.0)  # Cap at 60s


def format_metric_count(metrics: Dict[str, Any]) -> int:
    """Count the number of computed metrics."""
    count = 0
    for key, value in metrics.items():
        if value is not None and not (isinstance(value, float) and str(value) == "nan"):
            count += 1
    return count

