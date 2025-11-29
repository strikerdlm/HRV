# SPDX-License-Identifier: GPL-3.0-or-later
"""Top-level package for *fatigue_calculator*.

Public API is re-exported for user convenience so that the common entry points
can be imported directly from the package, e.g.::

    from fatigue_calculator import simulate_cognitive_performance
    from fatigue_calculator import optimise_ml_enhancement

The heavy-lifting routines live in the :pymod:`fatigue_calculator.core` module.
"""

from __future__ import annotations

from importlib import metadata as _metadata

from .core import (
    simulate_cognitive_performance,  # legacy name
    enhanced_simulate_cognitive_performance,
    enhanced_cognitive_performance,
)
from .calibration import optimise_ml_enhancement

__all__ = [
    # simulation helpers
    "simulate_cognitive_performance",
    "enhanced_simulate_cognitive_performance",
    "enhanced_cognitive_performance",
    # calibration helper
    "optimise_ml_enhancement",
    # misc
    "__version__",
]

try:
    __version__ = _metadata.version(__name__)
except _metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0+dev" 