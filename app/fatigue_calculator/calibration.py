from __future__ import annotations

"""fatigue_calculator.calibration
==================================
Utility helpers to *calibrate* the deterministic fatigue model on a labelled
empirical data-set.

The current implementation in :pymod:`fatigue_calculator.core` exposes an
``ml_enhancement`` parameter that multiplicatively scales the final cognitive
performance prediction returned by
:pyfunc:`fatigue_calculator.core.enhanced_cognitive_performance`.

Until the full deep-learning pipeline (see ``CogPSGFormer`` placeholder) is
implemented, we can already achieve *significantly* better agreement with
observed performance scores by tuning this single scalar on historical data.

Typical usage
-------------
>>> import pandas as pd
>>> from fatigue_calculator.calibration import optimise_ml_enhancement
>>> df = pd.read_csv("my_labelling_study.csv")
>>> best_factor, rmse = optimise_ml_enhancement(df.predicted, df.actual)
>>> print(f"Calibrated factor: {best_factor:.3f} – RMSE: {rmse:.2f}")

After retrieving ``best_factor`` you can forward it to
``enhanced_cognitive_performance`` via its *ml_enhancement* argument or to
:pyfunc:`fatigue_calculator.core.cogpsgformer_prediction`.

No external heavy dependencies are required – only *numpy*, *pandas* and
*scikit-learn*, which are already part of ``requirements.txt``.
"""

from typing import Tuple

import numpy as np
import pandas as pd

__all__ = [
    "optimise_ml_enhancement",
]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def optimise_ml_enhancement(
    model_predictions: pd.Series | np.ndarray,
    ground_truth: pd.Series | np.ndarray,
    search_space: Tuple[float, float] = (0.5, 1.5),
    steps: int = 201,
) -> Tuple[float, float]:
    """Brute-force search for the *ml_enhancement* scaling factor.

    Parameters
    ----------
    model_predictions
        1-D array or :class:`pandas.Series` with the raw outputs coming from
        ``enhanced_cognitive_performance`` *before* any ``ml_enhancement`` is
        applied.
    ground_truth
        1-D array or :class:`pandas.Series` with the empirically observed
        performance scores that the model should match.
    search_space
        Tuple ``(low, high)`` describing the inclusive range of scaling factors
        that will be evaluated. Defaults to ``(0.5, 1.5)`` which allows for
        a ±50 % adjustment.
    steps
        Number of equally spaced values in *search_space* that will be tested.

    Returns
    -------
    best_factor, best_rmse
        The scaling factor that minimises the root-mean-squared-error (RMSE)
        between *model_predictions* × factor and *ground_truth*, together with
        the achieved RMSE.
    """

    # Convert to numpy once to speed up repeated operations
    y_pred = np.asarray(model_predictions, dtype=float)
    y_true = np.asarray(ground_truth, dtype=float)

    if y_pred.shape != y_true.shape:
        raise ValueError("model_predictions and ground_truth must have the same shape")

    low, high = search_space
    factors = np.linspace(low, high, steps)

    # Vectorised RMSE computation for all factors at once
    #   broadcast: (steps, 1) * (n,) → (steps, n)
    scaled_preds = factors[:, None] * y_pred[None, :]
    rmse_values = np.sqrt(((scaled_preds - y_true) ** 2).mean(axis=1))

    idx = rmse_values.argmin()
    return float(factors[idx]), float(rmse_values[idx])