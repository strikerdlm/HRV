"""
Sleep regulation models and analysis tools.

Implements the Two-Process Model of sleep regulation (Borbély) and
utilities for analyzing sleep patterns from wearable data.

The Two-Process Model combines:
- Process S: Homeostatic sleep pressure (builds during wake, decreases during sleep)
- Process C: Circadian modulation of sleep propensity

Original implementation: Arcascope (https://github.com/Arcascope/circadian)
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from numpy.typing import NDArray

from .models import DynamicalTrajectory
from .utils import convert_binary


__all__ = [
    "TwoProcessModel",
    "sleep_midpoint",
    "cluster_sleep_periods",
    "detect_sleep_periods",
    "sleep_efficiency",
    "total_sleep_time",
]


class TwoProcessModel:
    """Implementation of the Two-Process Model of sleep regulation.
    
    Based on Borbély (1982) and subsequent refinements. The model predicts
    sleep/wake state based on the interaction between homeostatic sleep
    pressure and circadian phase.
    
    The homeostatic process (S) is governed by:
    - During wake: dS/dt = (μ_s - S) / τ_w  (S increases toward ceiling)
    - During sleep: dS/dt = -S / τ_s  (S decreases exponentially)
    
    Sleep occurs when S exceeds an upper threshold modulated by circadian phase,
    and wake occurs when S falls below a lower threshold.
    
    References:
        Borbély AA (1982). A two process model of sleep regulation.
        Human Neurobiology, 1(3), 195-204.
        
        Skeldon AC et al. (2017). Modelling changes in sleep timing and
        duration across the lifespan. Sleep Medicine Reviews, 33, 138-153.
    
    Example:
        >>> from app.circadian.models import Hannay19
        >>> model = TwoProcessModel(steps_wake_threshold=10.0)
        >>> # Simulate with circadian phase and activity data
        >>> trajectory = model(time, phase, steps)
    """
    
    def __init__(self, steps_wake_threshold: float = 10.0):
        """Initialize the Two-Process Model.
        
        Args:
            steps_wake_threshold: Activity threshold for inferring wake state.
                If steps > threshold, subject is assumed awake regardless
                of homeostatic pressure.
        """
        self.steps_wake_threshold = steps_wake_threshold
        self.awake = True
        
        # Model parameters (Skeldon et al. 2017)
        self.tau_s = 4.2   # Sleep time constant (hours)
        self.tau_w = 18.2  # Wake time constant (hours)
        self.mu_s = 1.0    # Upper asymptote
        self.H_minus = 0.17  # Lower threshold
        self.H_plus = 0.6    # Upper threshold
        self.homeostat_a = 0.10  # Circadian modulation amplitude
    
    def check_wake_status(
        self,
        awake: bool,
        h: float,
        phase: float,
    ) -> bool:
        """Determine wake status based on homeostatic pressure and circadian phase.
        
        Args:
            awake: Current wake status.
            h: Current homeostatic sleep pressure (0-1).
            phase: Current circadian phase (radians).
            
        Returns:
            New wake status.
        """
        c = np.cos(phase)
        upper = self.H_plus + self.homeostat_a * c
        lower = self.H_minus + self.homeostat_a * c
        
        above_threshold = h > upper
        below_threshold = h <= lower
        
        if above_threshold:
            return False  # Sleep onset
        elif below_threshold:
            return True   # Wake onset
        else:
            return awake  # No change
    
    def dhomeostat(
        self,
        homeostat: NDArray,
        steps: float,
        phase: float,
    ) -> NDArray:
        """Compute derivative of homeostatic sleep pressure.
        
        Args:
            homeostat: Current state [H].
            steps: Activity level.
            phase: Circadian phase (radians).
            
        Returns:
            Derivative [dH/dt].
        """
        h = homeostat[0]
        
        # Use activity to infer wake state
        step_awake = (steps > self.steps_wake_threshold) or self.awake
        
        if step_awake:
            dH = (self.mu_s - h) / self.tau_w
        else:
            dH = -h / self.tau_s
        
        # Update wake status based on thresholds
        self.awake = self.check_wake_status(self.awake, h, phase)
        
        return np.array([dH])
    
    def step_rk4(
        self,
        state: NDArray,
        steps: float,
        phase: float,
        dt: float = 0.10,
    ) -> NDArray:
        """Advance state using 4th-order Runge-Kutta integration.
        
        Args:
            state: Current state [H].
            steps: Activity level.
            phase: Circadian phase.
            dt: Time step (hours).
            
        Returns:
            New state after dt.
        """
        k1 = self.dhomeostat(state, steps, phase)
        k2 = self.dhomeostat(state + k1 * dt / 2.0, steps, phase)
        k3 = self.dhomeostat(state + k2 * dt / 2.0, steps, phase)
        k4 = self.dhomeostat(state + k3 * dt, steps, phase)
        
        return state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    
    def __call__(
        self,
        ts: NDArray,
        phase: NDArray,
        steps: NDArray,
        initial_value: Optional[NDArray] = None,
    ) -> DynamicalTrajectory:
        """Run the Two-Process Model simulation.
        
        Args:
            ts: Time array (hours).
            phase: Circadian phase at each time point (radians).
            steps: Activity/steps at each time point.
            initial_value: Initial homeostatic pressure [H]. Default [0.5].
            
        Returns:
            DynamicalTrajectory containing homeostatic pressure over time.
        """
        if initial_value is None:
            initial_value = np.array([0.50])
        
        sol = np.zeros((len(initial_value), len(ts)))
        current_state = initial_value.copy()
        sol[:, 0] = current_state
        
        for idx in range(1, len(ts)):
            current_state = self.step_rk4(current_state, steps[idx], phase[idx])
            sol[:, idx] = current_state
        
        return DynamicalTrajectory(ts, np.array(sol.T))


def sleep_midpoint(
    time_total: NDArray,
    wake: NDArray,
    return_durations: bool = True,
) -> Tuple[NDArray, NDArray] | NDArray:
    """Find sleep midpoints from a wake/sleep time series.
    
    Sleep midpoints are the median times of each sleep period, useful
    for estimating circadian phase from behavioral data.
    
    Args:
        time_total: Time array (hours from start).
        wake: Binary wake array (1 = awake, 0 = asleep).
        return_durations: If True, also return sleep durations.
        
    Returns:
        If return_durations=True: (midpoints, durations)
        Otherwise: midpoints only
        
        Both arrays have one entry per detected sleep period.
        
    Example:
        >>> midpoints, durations = sleep_midpoint(time, wake)
        >>> print(f"Average sleep midpoint: {np.mean(midpoints % 24):.1f} hours")
    """
    sleep_start = []
    sleep_end = []
    awake = wake[0] > 0.50
    
    # Start in sleep?
    if not awake:
        sleep_start.append(time_total[0])
    
    # Detect transitions
    for k in range(1, len(wake)):
        if wake[k] > 0.50 and not awake:
            # Sleep -> Wake transition
            awake = True
            sleep_end.append(time_total[k])
        
        if wake[k] <= 0.50 and awake:
            # Wake -> Sleep transition
            awake = False
            sleep_start.append(time_total[k])
    
    # End in sleep?
    if wake[-1] <= 0.50:
        sleep_end.append(time_total[-1])
    
    # Ensure matched pairs
    n_periods = min(len(sleep_start), len(sleep_end))
    sleep_start = sleep_start[:n_periods]
    sleep_end = sleep_end[:n_periods]
    
    # Calculate midpoints and durations
    midpoints = []
    durations = []
    for s1, s2 in zip(sleep_start, sleep_end):
        midpoints.append((s2 - s1) / 2 + s1)
        durations.append(s2 - s1)
    
    if return_durations:
        return np.array(midpoints), np.array(durations)
    else:
        return np.array(midpoints)


def cluster_sleep_periods(
    wake_data: NDArray,
    epsilon: float = 100.0,
    max_sleep_clusters: Optional[int] = None,
    min_sleep_clusters: Optional[int] = None,
) -> NDArray:
    """Smooth noisy wake/sleep predictions using regularization.
    
    Cleans up erroneous short sleep/wake periods that may interfere
    with circadian phase estimation.
    
    Args:
        wake_data: Binary wake array (1 = awake, 0 = asleep).
        epsilon: Regularization penalty for transitions (higher = smoother).
        max_sleep_clusters: Maximum number of sleep periods allowed.
        min_sleep_clusters: Minimum number of sleep periods required.
        
    Returns:
        Smoothed binary wake array.
        
    Note:
        This is a simplified version. For production use, consider
        scipy.optimize.minimize with SLSQP as in the original implementation.
    """
    # Handle NaN values
    wake_data = np.nan_to_num(wake_data, nan=0.50)
    
    # Simple smoothing using rolling window majority vote
    window_size = max(3, int(epsilon / 10))
    smoothed = np.copy(wake_data)
    
    for i in range(window_size, len(wake_data) - window_size):
        window = wake_data[i - window_size:i + window_size + 1]
        smoothed[i] = 1.0 if np.mean(window) > 0.5 else 0.0
    
    return convert_binary(smoothed)


def detect_sleep_periods(
    time: NDArray,
    wake: NDArray,
    min_duration_hours: float = 0.5,
) -> list[dict]:
    """Detect and characterize sleep periods.
    
    Args:
        time: Time array (hours).
        wake: Binary wake array (1 = awake, 0 = asleep).
        min_duration_hours: Minimum sleep duration to count as a period.
        
    Returns:
        List of dictionaries with sleep period details:
        - 'start': Start time (hours)
        - 'end': End time (hours)
        - 'duration': Duration (hours)
        - 'midpoint': Midpoint time (hours)
    """
    midpoints, durations = sleep_midpoint(time, wake, return_durations=True)
    
    periods = []
    for mp, dur in zip(midpoints, durations):
        if dur >= min_duration_hours:
            periods.append({
                'start': mp - dur / 2,
                'end': mp + dur / 2,
                'duration': dur,
                'midpoint': mp,
            })
    
    return periods


def sleep_efficiency(
    wake: NDArray,
    time_in_bed_hours: Optional[float] = None,
) -> float:
    """Calculate sleep efficiency percentage.
    
    Sleep efficiency = (Total Sleep Time / Time in Bed) × 100
    
    Args:
        wake: Binary wake array (1 = awake, 0 = asleep).
        time_in_bed_hours: Optional override for time in bed.
            If None, assumes entire array represents time in bed.
            
    Returns:
        Sleep efficiency percentage (0-100).
    """
    total_samples = len(wake)
    sleep_samples = np.sum(wake <= 0.5)
    
    if time_in_bed_hours is not None and total_samples > 0:
        # Assume uniform sampling
        time_resolution = time_in_bed_hours / total_samples
        tst = sleep_samples * time_resolution
        efficiency = (tst / time_in_bed_hours) * 100
    else:
        efficiency = (sleep_samples / total_samples) * 100 if total_samples > 0 else 0.0
    
    return float(np.clip(efficiency, 0, 100))


def total_sleep_time(
    time: NDArray,
    wake: NDArray,
) -> float:
    """Calculate total sleep time in hours.
    
    Args:
        time: Time array (hours).
        wake: Binary wake array (1 = awake, 0 = asleep).
        
    Returns:
        Total sleep time in hours.
    """
    if len(time) < 2:
        return 0.0
    
    dt = np.median(np.diff(time))  # Time resolution
    sleep_samples = np.sum(wake <= 0.5)
    
    return float(sleep_samples * dt)

