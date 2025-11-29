"""
Circadian rhythm simulation and analysis module.

This module provides mathematical models for simulating human circadian rhythms,
tools for creating light schedules, and utilities for analyzing circadian phase
and amplitude from wearable data.

Original package by Arcascope (Franco Tavella, Kevin Hannay, Olivia Walch)
https://github.com/Arcascope/circadian

UI updates and integration by Dr. Diego L. Malpica.

Citation:
    @software{franco_tavella_2023_8206871,
      author       = {Franco Tavella and Kevin Hannay and Olivia Walch},
      title        = {Arcascope/circadian},
      year         = 2023,
      publisher    = {Zenodo},
      doi          = {10.5281/zenodo.8206871}
    }
"""

__version__ = "1.1.0"

# Core model classes
from .models import (
    CircadianModel,
    DynamicalTrajectory,
    Forger99,
    Hannay19,
    Hannay19TP,
    Jewett99,
)

# Light schedule utilities
from .lights import LightSchedule

# Metrics and analysis
from .metrics import (
    esri,
    circadian_phase_coherence,
    phase_deviation,
    social_jetlag_index,
)

# Wearable data readers
from .readers import (
    WearableData,
    load_json,
    load_csv,
    load_actiwatch,
    combine_wearable_dataframes,
)

# Utility functions
from .utils import (
    phase_difference,
    amplitude_percent_change,
    sleep_midpoint_and_duration,
    phase_coherence,
    phase_coherence_clock,
    times_to_angle,
    convert_binary,
)

# Phase extraction tools
from .phasetools import (
    cosinor,
    cosinor_phase,
    cosinor_goals,
    cosinor_amplitude,
    cosinor_fit,
)

# Phase Response Curve tools
from .prc import (
    make_pulse,
    get_pulse,
    heaviside,
    PRCFinder,
    PhaseResponseCurveLight,
    IntensityResponseCurveLight,
    DosageResponseCurve,
    compute_prc,
)

# Sleep regulation models
from .sleep import (
    TwoProcessModel,
    sleep_midpoint,
    cluster_sleep_periods,
    detect_sleep_periods,
    sleep_efficiency,
    total_sleep_time,
)

# Synthetic data generation
from .synthetic_data import (
    generate_activity_from_light,
    generate_synthetic_wearable_data,
    generate_heart_rate_from_activity,
    generate_sleep_wake,
    add_missing_data,
)

__all__ = [
    # Version
    "__version__",
    # Models
    "CircadianModel",
    "DynamicalTrajectory",
    "Forger99",
    "Hannay19",
    "Hannay19TP",
    "Jewett99",
    # Lights
    "LightSchedule",
    # Metrics
    "esri",
    "circadian_phase_coherence",
    "phase_deviation",
    "social_jetlag_index",
    # Readers
    "WearableData",
    "load_json",
    "load_csv",
    "load_actiwatch",
    "combine_wearable_dataframes",
    # Utils
    "phase_difference",
    "amplitude_percent_change",
    "sleep_midpoint_and_duration",
    "phase_coherence",
    "phase_coherence_clock",
    "times_to_angle",
    "convert_binary",
    # Phase tools
    "cosinor",
    "cosinor_phase",
    "cosinor_goals",
    "cosinor_amplitude",
    "cosinor_fit",
    # PRC tools
    "make_pulse",
    "get_pulse",
    "heaviside",
    "PRCFinder",
    "PhaseResponseCurveLight",
    "IntensityResponseCurveLight",
    "DosageResponseCurve",
    "compute_prc",
    # Sleep models
    "TwoProcessModel",
    "sleep_midpoint",
    "cluster_sleep_periods",
    "detect_sleep_periods",
    "sleep_efficiency",
    "total_sleep_time",
    # Synthetic data
    "generate_activity_from_light",
    "generate_synthetic_wearable_data",
    "generate_heart_rate_from_activity",
    "generate_sleep_wake",
    "add_missing_data",
]
