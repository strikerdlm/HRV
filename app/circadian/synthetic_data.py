"""
Synthetic data generation for circadian analysis.

Provides functions to generate realistic synthetic wearable data for
testing and validation of circadian analysis algorithms.

Original implementation: Arcascope (https://github.com/Arcascope/circadian)
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from numpy.typing import NDArray

from .lights import LightSchedule


__all__ = [
    "generate_activity_from_light",
    "generate_synthetic_wearable_data",
    "generate_heart_rate_from_activity",
    "generate_sleep_wake",
]


def generate_activity_from_light(
    time: NDArray,
    light: LightSchedule,
    mu_l: float = 5.0,
    mu_h: float = 25.0,
    mu_s: float = 0.0,
    sigma_l: float = 7.5,
    sigma_h: float = 30.0,
    sigma_s: float = 2.0,
    active_level: float = 0.5,
) -> NDArray:
    """Generate an activity schedule from a light schedule.
    
    Creates a realistic activity time series based on a light schedule,
    with random variations modeling real-world behavior.
    
    Args:
        time: Time points (hours).
        light: LightSchedule object defining light exposure.
        mu_l: Mean of low activity levels (steps/min).
        mu_h: Mean of high activity levels (steps/min).
        mu_s: Mean of sleep activity levels.
        sigma_l: Std of low activity levels.
        sigma_h: Std of high activity levels.
        sigma_s: Std of sleep activity levels.
        active_level: Activity level (0-1). Higher values increase
            probability of high activity during wake.
            
    Returns:
        Activity array (same length as time).
        
    Raises:
        TypeError: If inputs are not correct types.
        ValueError: If parameters are out of valid ranges.
        
    Example:
        >>> light = LightSchedule.Regular(lux=500, lights_on=8, lights_off=22)
        >>> time = np.arange(0, 72, 0.1)
        >>> activity = generate_activity_from_light(time, light)
    """
    # Input validation
    if not isinstance(time, np.ndarray):
        raise TypeError("`time` must be a numpy array")
    if not isinstance(light, LightSchedule):
        raise TypeError("`light` must be a LightSchedule object")
    if not isinstance(mu_l, (float, int)) or mu_l < 0.0:
        raise ValueError("mu_l must be a non-negative number")
    if not isinstance(mu_h, (float, int)) or mu_h < 0.0:
        raise ValueError("mu_h must be a non-negative number")
    if not isinstance(mu_s, (float, int)) or mu_s < 0.0:
        raise ValueError("mu_s must be a non-negative number")
    if not isinstance(sigma_l, (float, int)) or sigma_l < 0.0:
        raise ValueError("sigma_l must be a non-negative number")
    if not isinstance(sigma_h, (float, int)) or sigma_h < 0.0:
        raise ValueError("sigma_h must be a non-negative number")
    if not isinstance(sigma_s, (float, int)) or sigma_s < 0.0:
        raise ValueError("sigma_s must be a non-negative number")
    if not isinstance(active_level, (float, int)) or not 0.0 <= active_level <= 1.0:
        raise ValueError("active_level must be between 0.0 and 1.0")
    
    activity = np.zeros(time.shape)
    
    for t_idx in range(len(time)):
        light_val = light(time[t_idx])
        
        if light_val == 0:
            # Sleep - low activity
            activity[t_idx] = np.abs(np.random.normal(mu_s, sigma_s))
        else:
            # Wake - choose between high and low activity
            high_activity = np.random.uniform() <= active_level
            if high_activity:
                activity[t_idx] = np.abs(np.random.normal(mu_h, sigma_h))
            else:
                activity[t_idx] = np.abs(np.random.normal(mu_l, sigma_l))
    
    return activity


def generate_heart_rate_from_activity(
    activity: NDArray,
    hr_rest: float = 60.0,
    hr_max: float = 180.0,
    activity_max: float = 100.0,
    noise_std: float = 5.0,
    sleep_hr: float = 50.0,
    sleep_threshold: float = 2.0,
) -> NDArray:
    """Generate heart rate data from activity levels.
    
    Creates a realistic heart rate time series that responds to activity
    with physiologically plausible dynamics.
    
    Args:
        activity: Activity array (e.g., steps per minute).
        hr_rest: Resting heart rate (bpm).
        hr_max: Maximum heart rate (bpm).
        activity_max: Activity level corresponding to hr_max.
        noise_std: Standard deviation of HR noise.
        sleep_hr: Heart rate during sleep.
        sleep_threshold: Activity below this is considered sleep.
        
    Returns:
        Heart rate array (same length as activity).
    """
    hr = np.zeros(len(activity))
    
    for i, act in enumerate(activity):
        if act <= sleep_threshold:
            # Sleep state
            base_hr = sleep_hr
        else:
            # Activity-dependent HR
            normalized_act = min(act / activity_max, 1.0)
            base_hr = hr_rest + (hr_max - hr_rest) * normalized_act ** 0.5
        
        # Add noise
        hr[i] = base_hr + np.random.normal(0, noise_std)
    
    # Ensure physiological bounds
    hr = np.clip(hr, 40, 220)
    
    return hr


def generate_sleep_wake(
    time: NDArray,
    sleep_onset: float = 23.0,
    wake_time: float = 7.0,
    variability_hours: float = 0.5,
) -> NDArray:
    """Generate a binary sleep/wake schedule.
    
    Args:
        time: Time array (hours).
        sleep_onset: Typical bedtime (hour of day, 0-24).
        wake_time: Typical wake time (hour of day, 0-24).
        variability_hours: Day-to-day variability (std).
        
    Returns:
        Binary wake array (1 = awake, 0 = asleep).
    """
    wake = np.ones(len(time))
    
    # Get day boundaries
    start_day = int(time[0] // 24)
    end_day = int(time[-1] // 24) + 1
    
    for day in range(start_day, end_day + 1):
        # Add variability to sleep/wake times
        actual_onset = sleep_onset + np.random.normal(0, variability_hours)
        actual_wake = wake_time + np.random.normal(0, variability_hours)
        
        # Handle wraparound (onset > 24 or wake < 0)
        onset_time = day * 24 + actual_onset
        if actual_onset > 24:
            onset_time = day * 24 + (actual_onset - 24)
        
        wake_time_abs = (day + 1) * 24 + actual_wake
        if actual_wake < 0:
            wake_time_abs = day * 24 + 24 + actual_wake
        
        # Set sleep period
        sleep_mask = (time >= onset_time) & (time < wake_time_abs)
        wake[sleep_mask] = 0.0
    
    return wake


def generate_synthetic_wearable_data(
    days: int = 7,
    dt_minutes: float = 1.0,
    light_schedule: Optional[LightSchedule] = None,
    sleep_onset: float = 23.0,
    wake_time: float = 7.0,
    active_level: float = 0.5,
    add_noise: bool = True,
) -> dict:
    """Generate a complete synthetic wearable dataset.
    
    Creates time-matched arrays of time, light, activity, heart rate,
    and sleep/wake state for testing circadian analysis algorithms.
    
    Args:
        days: Number of days to generate.
        dt_minutes: Time resolution in minutes.
        light_schedule: Custom light schedule. If None, uses Regular schedule.
        sleep_onset: Typical bedtime (hour of day).
        wake_time: Typical wake time (hour of day).
        active_level: Activity level parameter (0-1).
        add_noise: Whether to add realistic noise.
        
    Returns:
        Dictionary with keys:
        - 'time': Time array (hours from start)
        - 'light': Light intensity (lux)
        - 'steps': Activity/steps
        - 'heartrate': Heart rate (bpm)
        - 'wake': Binary wake state (1=awake, 0=asleep)
        - 'datetime': Simulated datetime array
        
    Example:
        >>> data = generate_synthetic_wearable_data(days=14)
        >>> from app.circadian.metrics import esri
        >>> esri_time, esri_values = esri(data['time'], data['light'])
    """
    import datetime as dt
    
    # Generate time array
    dt_hours = dt_minutes / 60.0
    time = np.arange(0, days * 24, dt_hours)
    
    # Create light schedule if not provided
    if light_schedule is None:
        light_schedule = LightSchedule.Regular(
            lux=500.0,
            lights_on=int(wake_time),
            lights_off=int(sleep_onset),
        )
    
    # Generate light values
    light = np.array([light_schedule(t) for t in time])
    
    # Generate sleep/wake
    wake = generate_sleep_wake(time, sleep_onset, wake_time)
    
    # Generate activity based on light
    steps = generate_activity_from_light(
        time, light_schedule, active_level=active_level
    )
    
    # Modulate activity by sleep state
    steps = steps * wake
    
    # Generate heart rate from activity
    heartrate = generate_heart_rate_from_activity(steps)
    
    # Generate datetime array
    start_date = dt.datetime(2024, 1, 1, 0, 0, 0)
    datetime_arr = [
        start_date + dt.timedelta(hours=float(t))
        for t in time
    ]
    
    return {
        'time': time,
        'light': light,
        'steps': steps,
        'heartrate': heartrate,
        'wake': wake,
        'datetime': np.array(datetime_arr),
    }


def add_missing_data(
    data: dict,
    missing_fraction: float = 0.05,
    gap_duration_hours: float = 2.0,
) -> dict:
    """Add realistic missing data gaps to synthetic wearable data.
    
    Simulates device non-wear periods by inserting NaN values.
    
    Args:
        data: Dictionary from generate_synthetic_wearable_data().
        missing_fraction: Approximate fraction of data to remove.
        gap_duration_hours: Typical gap duration.
        
    Returns:
        Modified data dictionary with NaN gaps.
    """
    data = data.copy()
    time = data['time']
    dt_hours = np.median(np.diff(time))
    
    # Calculate gap parameters
    samples_per_gap = int(gap_duration_hours / dt_hours)
    n_gaps = int(missing_fraction * len(time) / samples_per_gap)
    
    # Insert gaps at random locations
    for _ in range(n_gaps):
        gap_start = np.random.randint(0, len(time) - samples_per_gap)
        gap_end = gap_start + samples_per_gap
        
        for key in ['light', 'steps', 'heartrate']:
            if key in data:
                data[key][gap_start:gap_end] = np.nan
    
    return data

