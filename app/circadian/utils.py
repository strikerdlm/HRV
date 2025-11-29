"""
Utility functions for circadian rhythm analysis.

Provides helper functions for:
- Phase calculations and comparisons
- Sleep metrics (midpoint, duration)
- Time conversions
- Coherence metrics

Original implementation: Arcascope (https://github.com/Arcascope/circadian)
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
import scipy as sp
from numpy.typing import NDArray
from scipy.stats import circmean


__all__ = [
    "phase_difference",
    "amplitude_percent_change",
    "sleep_midpoint_and_duration",
    "utc_to_hrs",
    "phase_ic_guess",
    "abs_hour_diff",
    "cut_phases_12",
    "convert_binary",
    "cal_days_diff",
    "phase_coherence",
    "phase_coherence_clock",
    "angle_difference",
    "subtract_clock_times",
    "times_to_angle",
]


def phase_difference(phase_1: float, phase_2: float) -> float:
    """Calculate phase difference (phase_2 - phase_1).
    
    Args:
        phase_1: First phase value between [-π, π].
        phase_2: Second phase value between [-π, π].
        
    Returns:
        Phase difference. Negative values represent clockwise rotations.
    """
    diff = phase_2 - phase_1
    normalized_diff = (diff + np.pi) % (2 * np.pi) - np.pi
    return float(normalized_diff)


def amplitude_percent_change(amplitude_1: float, amplitude_2: float) -> float:
    """Calculate percent change between two amplitudes.
    
    Args:
        amplitude_1: Initial amplitude (positive).
        amplitude_2: Final amplitude (positive).
        
    Returns:
        Percent change from amplitude_1 to amplitude_2.
    """
    if amplitude_1 == 0:
        return float("inf") if amplitude_2 > 0 else 0.0
    return (amplitude_2 - amplitude_1) / amplitude_1 * 100


def sleep_midpoint_and_duration(
    time: NDArray,
    sleep_state: NDArray,
) -> Tuple[float, float]:
    """Calculate sleep duration and mid-sleep time from sleep state data.
    
    Args:
        time: Array of time values (hours).
        sleep_state: Array of sleep state values (0 = asleep, 1 = awake).
        
    Returns:
        Tuple of (mid_sleep_time, sleep_duration) in hours.
        
    Raises:
        ValueError: If arrays have different lengths.
    """
    if not isinstance(time, np.ndarray):
        time = np.array(time)
    if not isinstance(sleep_state, np.ndarray):
        sleep_state = np.array(sleep_state)
    if len(time) != len(sleep_state):
        raise ValueError("time and sleep_state must have the same length")
    
    sleep_start_idxs = np.where(np.diff(sleep_state) == 1)[0]
    sleep_end_idxs = np.where(np.diff(sleep_state) == -1)[0]
    
    # Handle edge cases
    if len(sleep_start_idxs) == 0 or len(sleep_end_idxs) == 0:
        return 0.0, 0.0
    
    # Trim incomplete sleep windows
    if sleep_start_idxs[0] > sleep_end_idxs[0]:
        sleep_end_idxs = sleep_end_idxs[1:]
    if len(sleep_start_idxs) > 0 and len(sleep_end_idxs) > 0:
        if sleep_start_idxs[-1] > sleep_end_idxs[-1]:
            sleep_start_idxs = sleep_start_idxs[:-1]
    
    if len(sleep_start_idxs) == 0 or len(sleep_end_idxs) == 0:
        return 0.0, 0.0
    
    sleep_duration = float(np.mean(time[sleep_end_idxs] - time[sleep_start_idxs]))
    sleep_midpoints = (time[sleep_start_idxs] + time[sleep_end_idxs]) / 2.0
    mid_sleep_time = float(circmean(np.mod(sleep_midpoints, 24.0), high=24.0))
    
    return mid_sleep_time, sleep_duration


def utc_to_hrs(timestamp) -> float:
    """Convert UTC timestamp to hours since midnight.
    
    Args:
        timestamp: Pandas Timestamp object.
        
    Returns:
        Hours since midnight (0-24).
    """
    return timestamp.hour + timestamp.minute / 60.0 + timestamp.second / 3600.0


def phase_ic_guess(time_of_day: float) -> float:
    """Estimate initial circadian phase based on time of day.
    
    Assumes wake at 8 AM after 8 hours of sleep as reference point.
    
    Args:
        time_of_day: Hour of day (0-24).
        
    Returns:
        Initial phase estimate in radians.
    """
    time_of_day = np.fmod(time_of_day, 24.0)
    
    # Wake at 8 am after 8 hours of sleep - state at 00:00
    psi = 1.65238233
    
    # Convert to radians, add to phase
    psi += time_of_day * np.pi / 12
    return psi


def abs_hour_diff(x: float, y: float) -> float:
    """Find the absolute difference in hours between two clock times (wrapped).
    
    Args:
        x: First clock time (0-24).
        y: Second clock time (0-24).
        
    Returns:
        Minimum hour difference accounting for wraparound.
    """
    a1 = min(x, y)
    a2 = max(x, y)
    s1 = a2 - a1
    s2 = 24.0 + a1 - a2
    return min(s1, s2)


def cut_phases_12(p: float) -> float:
    """Convert phase to range (-12, 12] hours instead of (0, 24].
    
    This is better because lots of DLMOs are near midnight, but many fewer
    are near noon, so this reduces discontinuities.
    
    Args:
        p: Phase in hours (any range).
        
    Returns:
        Phase wrapped to (-12, 12] hours.
    """
    while p < 0.0:
        p += 24.0
    
    p = np.fmod(p, 24.0)
    
    if p > 12:
        return p - 24.0
    else:
        return p


def convert_binary(x: NDArray, breakpoint: float = 0.50) -> NDArray:
    """Convert continuous values to binary based on threshold.
    
    Args:
        x: Array of continuous values.
        breakpoint: Threshold for binarization.
        
    Returns:
        Binary array (0.0 or 1.1).
    """
    result = x.copy()
    result[result <= breakpoint] = 0.0
    result[result > breakpoint] = 1.1
    return result


def cal_days_diff(a, b) -> int:
    """Get the calendar days between two datetimes.
    
    Args:
        a: First datetime.
        b: Second datetime.
        
    Returns:
        Number of calendar days (a - b).
    """
    A = a.replace(hour=0, minute=0, second=0, microsecond=0)
    B = b.replace(hour=0, minute=0, second=0, microsecond=0)
    return (A - B).days


def phase_coherence(series: NDArray) -> float:
    """Calculate phase coherence (mean resultant length) of a series of angles.
    
    Args:
        series: Array of phase values in radians.
        
    Returns:
        Phase coherence (0 = uniform distribution, 1 = all same angle).
    """
    Z = complex(0, 0)
    series = np.array(series)
    for i in range(len(series)):
        Z += np.exp(series[i] * complex(0, 1))
    
    Z = Z / float(len(series))
    return float(np.absolute(Z))


def phase_coherence_clock(series: NDArray) -> float:
    """Calculate phase coherence for clock times (0-24 hours).
    
    Args:
        series: Array of clock times in hours.
        
    Returns:
        Phase coherence (0 = random times, 1 = all same time).
    """
    angles = np.pi / 12.0 * series
    return phase_coherence(angles)


def angle_difference(c1: float, c2: float) -> float:
    """Find the signed angle difference between two angles in radians.
    
    Args:
        c1: First angle in radians.
        c2: Second angle in radians.
        
    Returns:
        Signed angle difference (c1 - c2), wrapped to (-π, π].
    """
    return float(np.angle(np.exp(complex(0, 1) * (c1 - c2))))


def subtract_clock_times(c1: float, c2: float) -> float:
    """Find the hour difference between two clock times.
    
    Args:
        c1: First clock time (0-24).
        c2: Second clock time (0-24).
        
    Returns:
        Signed hour difference wrapped to (-12, 12].
    """
    a1 = sp.pi / 12.0 * c1
    a2 = sp.pi / 12.0 * c2
    adiff = angle_difference(a1, a2)
    return 12.0 / sp.pi * adiff


def times_to_angle(time_vector: NDArray) -> Tuple[float, float]:
    """Convert array of times to mean angle and amplitude.
    
    Useful for calculating the mean and spread of circadian phase markers.
    
    Args:
        time_vector: Array of times in hours.
        
    Returns:
        Tuple of (R, psi) where R is the amplitude (0-1) and psi is the 
        mean angle in radians.
    """
    rad_vector = np.fmod(time_vector, 24.0) * np.pi / 12.0
    Z = np.sum(np.exp(rad_vector * 1j)) / len(rad_vector)
    return float(np.abs(Z)), float(np.angle(Z))

