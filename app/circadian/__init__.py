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

__version__ = "1.0.2"

from .models import (
    CircadianModel,
    DynamicalTrajectory,
    Forger99,
    Hannay19,
    Hannay19TP,
    Jewett99,
)
from .lights import LightSchedule
from .metrics import esri
from .plots import Actogram

__all__ = [
    "CircadianModel",
    "DynamicalTrajectory",
    "Forger99",
    "Hannay19",
    "Hannay19TP",
    "Jewett99",
    "LightSchedule",
    "esri",
    "Actogram",
] esri
from .plots import Actogram, plot_actogram, plot_mae, plot_torus, Stroboscopic
from .readers import load_csv, load_json, load_actiwatch, WearableData
from .utils import (
    phase_difference,
    amplitude_percent_change,
    sleep_midpoint_and_duration,
    phase_ic_guess,
    phase_coherence,
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
    # Plots
    "Actogram",
    "plot_actogram",
    "plot_mae",
    "plot_torus",
    "Stroboscopic",
    # Readers
    "load_csv",
    "load_json",
    "load_actiwatch",
    "WearableData",
    # Utils
    "phase_difference",
    "amplitude_percent_change",
    "sleep_midpoint_and_duration",
    "phase_ic_guess",
    "phase_coherence",
]

