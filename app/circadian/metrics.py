"""
Metrics for quantifying circadian rhythm regularity and disruption.

Implements the Entrainment Signal Regularity Index (ESRI) and related
utilities for assessing circadian health from wearable data.

Original implementation: Arcascope (https://github.com/Arcascope/circadian)
"""

from __future__ import annotations

import warnings
from typing import Tuple

import numpy as np
from numpy.typing import NDArray


def esri(
    time: NDArray,
    light_schedule: NDArray,
    analysis_days: int = 4,
    esri_dt: float = 1.0,
    initial_amplitude: float = 0.1,
    phase_at_midnight: float = 1.65238233,
) -> Tuple[NDArray, NDArray]:
    """Calculate the Entrainment Signal Regularity Index (ESRI).
    
    ESRI quantifies the temporal regularity of a light/activity schedule
    by simulating an amplitude-phase oscillator and measuring how well
    the signal maintains circadian entrainment.
    
    Higher ESRI values indicate more regular, entrainment-promoting schedules.
    
    Reference:
        Moreno et al. (2023) "Validation of the Entrainment Signal Regularity
        Index and associations with children's changes in BMI"
    
    Args:
        time: Time array in hours.
        light_schedule: Light intensity (lux) or activity proxy at each time point.
        analysis_days: Window length for ESRI calculation (days).
        esri_dt: Time resolution for ESRI output (hours).
        initial_amplitude: Starting amplitude (equals ESRI in constant darkness).
        phase_at_midnight: Initial phase at midnight (radians). Default corresponds
            to 8h dark / 16h light schedule with wake at 8 AM.
    
    Returns:
        Tuple of (esri_time, esri_values):
        - esri_time: Time points where ESRI was calculated (hours).
        - esri_values: ESRI values at each time point. Negative values are NaN.
        
    Raises:
        TypeError: If inputs are not numpy arrays or correct types.
        ValueError: If inputs are invalid (length mismatch, non-uniform time, etc.).
    """
    # Input validation
    if not isinstance(time, np.ndarray):
        raise TypeError(f"time must be a numpy array, not {type(time)}")
    if not isinstance(light_schedule, np.ndarray):
        raise TypeError(f"light_schedule must be a numpy array, not {type(light_schedule)}")
    if len(time) != len(light_schedule):
        raise ValueError("time and light_schedule must have the same length")
    
    # Check for uniform time spacing
    time_diffs = np.diff(time)
    if len(time_diffs) > 0 and not np.allclose(time_diffs, time_diffs[0], rtol=1e-5):
        raise ValueError("time must have uniform spacing (constant dt)")
    
    if not isinstance(analysis_days, int):
        raise TypeError(f"analysis_days must be an integer, not {type(analysis_days)}")
    if analysis_days < 1:
        raise ValueError("analysis_days must be at least 1")
    if not isinstance(esri_dt, (int, float)):
        raise TypeError(f"esri_dt must be numeric, not {type(esri_dt)}")
    if esri_dt <= 0:
        raise ValueError("esri_dt must be positive")
    if not isinstance(initial_amplitude, (int, float)):
        raise TypeError(f"initial_amplitude must be numeric, not {type(initial_amplitude)}")
    if initial_amplitude < 0:
        raise ValueError("initial_amplitude must be non-negative")
    
    # Lazy import to avoid circular dependency
    from .models import Hannay19
    
    # Create model with K=0, gamma=0 so amplitude is constant in darkness
    model = Hannay19(params={"K": 0.0, "gamma": 0.0})
    
    simulation_dt = float(time_diffs[0]) if len(time_diffs) > 0 else 0.1
    
    # Calculate ESRI at each time point
    max_start_time = time[-1] - analysis_days * 24
    if max_start_time <= time[0]:
        raise ValueError(
            f"Time series too short for {analysis_days}-day analysis. "
            f"Need at least {analysis_days * 24} hours of data."
        )
    
    esri_time = np.arange(time[0], max_start_time, esri_dt)
    esri_array = np.zeros(len(esri_time), dtype=np.float64)
    
    max_iterations = len(esri_time)
    for idx in range(max_iterations):
        t = esri_time[idx]
        
        # Initial phase based on time of day
        initial_phase = phase_at_midnight + np.mod(t, 24.0) * np.pi / 12.0
        initial_condition = np.array([initial_amplitude, initial_phase, 0.0])
        
        # Simulation window
        sim_time = np.arange(t, t + analysis_days * 24, simulation_dt)
        sim_light = np.interp(sim_time, time, light_schedule)
        
        # Run model
        trajectory = model(sim_time, initial_condition, sim_light)
        
        # ESRI is the final amplitude
        esri_array[idx] = trajectory.states[-1, 0]
    
    # Clean up negative values (numerical artifacts)
    esri_array[esri_array < 0] = np.nan
    
    # Warn if there are NaN values
    if np.any(np.isnan(esri_array)):
        warnings.warn(
            "ESRI calculation produced NaN values for some timepoints. "
            "Consider using finer time resolution for input data.",
            UserWarning,
        )
    
    return esri_time, esri_array


def circadian_phase_coherence(
    phase_markers: NDArray,
    expected_period: float = 24.0,
) -> float:
    """Calculate phase coherence from a series of phase markers (e.g., DLMO times).
    
    Phase coherence measures how stable the circadian phase is across days.
    Perfect coherence (1.0) means phase markers occur at exactly the same
    time each day. Lower values indicate phase instability.
    
    Args:
        phase_markers: Array of phase marker times (hours).
        expected_period: Expected circadian period (hours), typically 24.
        
    Returns:
        Phase coherence value between 0 (random) and 1 (perfectly stable).
    """
    if len(phase_markers) < 2:
        return 1.0  # Not enough data, assume coherent
    
    # Convert times to phases (0 to 2π within each period)
    phases = 2 * np.pi * np.mod(phase_markers, expected_period) / expected_period
    
    # Compute mean resultant length (phase coherence)
    mean_cos = np.mean(np.cos(phases))
    mean_sin = np.mean(np.sin(phases))
    coherence = np.sqrt(mean_cos**2 + mean_sin**2)
    
    return float(coherence)


def phase_deviation(
    phase_markers: NDArray,
    target_phase: float,
    period: float = 24.0,
) -> NDArray:
    """Calculate deviation of phase markers from a target phase.
    
    Useful for quantifying how far circadian timing deviates from
    an ideal schedule (e.g., target DLMO time).
    
    Args:
        phase_markers: Array of phase marker times (hours).
        target_phase: Target phase time (hours, e.g., 21.0 for 9 PM DLMO).
        period: Circadian period (hours).
        
    Returns:
        Array of signed deviations from target (hours).
        Positive = delayed, Negative = advanced.
    """
    # Normalize to period
    markers_norm = np.mod(phase_markers, period)
    target_norm = np.mod(target_phase, period)
    
    # Calculate signed circular difference
    diff = markers_norm - target_norm
    
    # Wrap to [-period/2, period/2]
    diff = np.mod(diff + period / 2, period) - period / 2
    
    return diff


def social_jetlag_index(
    weekday_midpoints: NDArray,
    weekend_midpoints: NDArray,
) -> float:
    """Calculate social jetlag as difference between weekend and weekday sleep midpoints.
    
    Social jetlag quantifies the mismatch between biological and social clocks,
    typically manifesting as later sleep timing on weekends.
    
    Reference:
        Wittmann et al. (2006) "Social jetlag: misalignment of biological
        and social time"
    
    Args:
        weekday_midpoints: Sleep midpoint times on weekdays (hours, 0-24).
        weekend_midpoints: Sleep midpoint times on weekends (hours, 0-24).
        
    Returns:
        Social jetlag in hours (positive = weekend delayed relative to weekdays).
    """
    if len(weekday_midpoints) == 0 or len(weekend_midpoints) == 0:
        return 0.0
    
    mean_weekday = np.mean(weekday_midpoints)
    mean_weekend = np.mean(weekend_midpoints)
    
    # Handle wraparound (e.g., 23:00 vs 01:00)
    diff = mean_weekend - mean_weekday
    if diff > 12:
        diff -= 24
    elif diff < -12:
        diff += 24
    
    return float(diff)

