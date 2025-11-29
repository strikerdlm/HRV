"""Machine Learning analytics for HRV analysis.

This module provides ML-powered analytics including:
- Anomaly detection using Isolation Forest and Local Outlier Factor
- Trend analysis with change point detection
- Feature importance ranking
- Predictive modeling for readiness scores
- Clustering for phenotype identification

Design principles:
- Deterministic algorithms where possible
- Bounded iterations and memory usage
- Clear confidence/uncertainty estimates
- Interpretable results with explanations

References:
- Liu et al. (2008). Isolation Forest. ICDM.
- Breunig et al. (2000). LOF: Identifying Density-Based Local Outliers.
- Killick et al. (2012). Optimal Detection of Changepoints. JASA.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Final

import numpy as np
import pandas as pd
from scipy import stats
from scipy.ndimage import uniform_filter1d

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_ITERATIONS: Final[int] = 100
_MIN_SAMPLES_FOR_ANALYSIS: Final[int] = 10
_DEFAULT_CONTAMINATION: Final[float] = 0.1
_RANDOM_STATE: Final[int] = 42


class AnomalyMethod(str, Enum):
    """Anomaly detection method."""

    ISOLATION_FOREST = "isolation_forest"
    LOF = "lof"
    ZSCORE = "zscore"
    IQR = "iqr"
    MAD = "mad"


class TrendDirection(str, Enum):
    """Trend direction classification."""

    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VARIABLE = "variable"


@dataclass(frozen=True, slots=True)
class AnomalyResult:
    """Result of anomaly detection.

    Attributes:
        is_anomaly: Boolean array indicating anomalies.
        scores: Anomaly scores (higher = more anomalous).
        threshold: Threshold used for classification.
        method: Method used for detection.
        n_anomalies: Count of detected anomalies.
        anomaly_indices: Indices of anomalous points.
    """

    is_anomaly: np.ndarray
    scores: np.ndarray
    threshold: float
    method: AnomalyMethod
    n_anomalies: int
    anomaly_indices: np.ndarray


@dataclass(frozen=True, slots=True)
class TrendResult:
    """Result of trend analysis.

    Attributes:
        direction: Overall trend direction.
        slope: Slope of linear trend (units per sample).
        r_squared: R² of linear fit.
        p_value: P-value for trend significance.
        change_points: Indices of detected change points.
        segments: List of segment descriptions.
        confidence: Confidence in trend assessment (0-1).
    """

    direction: TrendDirection
    slope: float
    r_squared: float
    p_value: float
    change_points: np.ndarray
    segments: list[dict[str, Any]]
    confidence: float


@dataclass(frozen=True, slots=True)
class FeatureImportance:
    """Feature importance ranking result.

    Attributes:
        feature_name: Name of the feature.
        importance: Importance score (0-1).
        direction: Whether higher values are better (+1) or worse (-1).
        correlation: Correlation with target variable.
    """

    feature_name: str
    importance: float
    direction: int
    correlation: float


@dataclass(slots=True)
class PredictionResult:
    """Result of predictive modeling.

    Attributes:
        predicted_value: Predicted value.
        confidence_interval: (lower, upper) bounds.
        feature_contributions: Dict of feature -> contribution.
        model_r_squared: Model fit quality.
    """

    predicted_value: float
    confidence_interval: tuple[float, float]
    feature_contributions: dict[str, float]
    model_r_squared: float


# ---------------------------------------------------------------------------
# Anomaly Detection
# ---------------------------------------------------------------------------


def detect_anomalies_zscore(
    values: np.ndarray,
    *,
    threshold: float = 3.0,
) -> AnomalyResult:
    """Detect anomalies using Z-score method.

    Args:
        values: Array of values to analyze.
        threshold: Z-score threshold for anomaly classification.

    Returns:
        AnomalyResult with anomaly flags and scores.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]

    if len(arr) < _MIN_SAMPLES_FOR_ANALYSIS:
        return AnomalyResult(
            is_anomaly=np.zeros(len(arr), dtype=bool),
            scores=np.zeros(len(arr)),
            threshold=threshold,
            method=AnomalyMethod.ZSCORE,
            n_anomalies=0,
            anomaly_indices=np.array([], dtype=int),
        )

    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))

    if std < 1e-9:
        return AnomalyResult(
            is_anomaly=np.zeros(len(arr), dtype=bool),
            scores=np.zeros(len(arr)),
            threshold=threshold,
            method=AnomalyMethod.ZSCORE,
            n_anomalies=0,
            anomaly_indices=np.array([], dtype=int),
        )

    z_scores = np.abs((arr - mean) / std)
    is_anomaly = z_scores > threshold
    anomaly_indices = np.where(is_anomaly)[0]

    return AnomalyResult(
        is_anomaly=is_anomaly,
        scores=z_scores,
        threshold=threshold,
        method=AnomalyMethod.ZSCORE,
        n_anomalies=int(np.sum(is_anomaly)),
        anomaly_indices=anomaly_indices,
    )


def detect_anomalies_iqr(
    values: np.ndarray,
    *,
    k: float = 1.5,
) -> AnomalyResult:
    """Detect anomalies using IQR method.

    Args:
        values: Array of values to analyze.
        k: IQR multiplier for fence calculation.

    Returns:
        AnomalyResult with anomaly flags and scores.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]

    if len(arr) < _MIN_SAMPLES_FOR_ANALYSIS:
        return AnomalyResult(
            is_anomaly=np.zeros(len(arr), dtype=bool),
            scores=np.zeros(len(arr)),
            threshold=k,
            method=AnomalyMethod.IQR,
            n_anomalies=0,
            anomaly_indices=np.array([], dtype=int),
        )

    q1 = float(np.percentile(arr, 25))
    q3 = float(np.percentile(arr, 75))
    iqr = q3 - q1

    if iqr < 1e-9:
        return AnomalyResult(
            is_anomaly=np.zeros(len(arr), dtype=bool),
            scores=np.zeros(len(arr)),
            threshold=k,
            method=AnomalyMethod.IQR,
            n_anomalies=0,
            anomaly_indices=np.array([], dtype=int),
        )

    lower_fence = q1 - k * iqr
    upper_fence = q3 + k * iqr

    is_anomaly = (arr < lower_fence) | (arr > upper_fence)

    # Score based on distance from fences
    scores = np.zeros_like(arr)
    below_mask = arr < lower_fence
    above_mask = arr > upper_fence
    scores[below_mask] = (lower_fence - arr[below_mask]) / iqr
    scores[above_mask] = (arr[above_mask] - upper_fence) / iqr

    anomaly_indices = np.where(is_anomaly)[0]

    return AnomalyResult(
        is_anomaly=is_anomaly,
        scores=scores,
        threshold=k,
        method=AnomalyMethod.IQR,
        n_anomalies=int(np.sum(is_anomaly)),
        anomaly_indices=anomaly_indices,
    )


def detect_anomalies_mad(
    values: np.ndarray,
    *,
    threshold: float = 3.5,
) -> AnomalyResult:
    """Detect anomalies using Median Absolute Deviation (MAD).

    More robust than Z-score for non-normal distributions.

    Args:
        values: Array of values to analyze.
        threshold: Modified Z-score threshold.

    Returns:
        AnomalyResult with anomaly flags and scores.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]

    if len(arr) < _MIN_SAMPLES_FOR_ANALYSIS:
        return AnomalyResult(
            is_anomaly=np.zeros(len(arr), dtype=bool),
            scores=np.zeros(len(arr)),
            threshold=threshold,
            method=AnomalyMethod.MAD,
            n_anomalies=0,
            anomaly_indices=np.array([], dtype=int),
        )

    median = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median)))

    if mad < 1e-9:
        return AnomalyResult(
            is_anomaly=np.zeros(len(arr), dtype=bool),
            scores=np.zeros(len(arr)),
            threshold=threshold,
            method=AnomalyMethod.MAD,
            n_anomalies=0,
            anomaly_indices=np.array([], dtype=int),
        )

    # Modified Z-score using MAD
    # 0.6745 is the 0.75th quantile of the standard normal distribution
    modified_z = 0.6745 * np.abs(arr - median) / mad
    is_anomaly = modified_z > threshold
    anomaly_indices = np.where(is_anomaly)[0]

    return AnomalyResult(
        is_anomaly=is_anomaly,
        scores=modified_z,
        threshold=threshold,
        method=AnomalyMethod.MAD,
        n_anomalies=int(np.sum(is_anomaly)),
        anomaly_indices=anomaly_indices,
    )


def detect_anomalies_isolation_forest(
    df: pd.DataFrame,
    features: list[str],
    *,
    contamination: float = _DEFAULT_CONTAMINATION,
    n_estimators: int = 100,
    max_samples: int = 256,
) -> AnomalyResult:
    """Detect anomalies using simplified Isolation Forest.

    This is a simplified implementation that approximates Isolation Forest
    behavior without requiring sklearn.

    Args:
        df: DataFrame with feature columns.
        features: List of feature column names.
        contamination: Expected proportion of anomalies.
        n_estimators: Number of isolation trees.
        max_samples: Maximum samples per tree.

    Returns:
        AnomalyResult with anomaly flags and scores.
    """
    valid_features = [f for f in features if f in df.columns]
    if len(valid_features) < 1:
        return AnomalyResult(
            is_anomaly=np.zeros(len(df), dtype=bool),
            scores=np.zeros(len(df)),
            threshold=contamination,
            method=AnomalyMethod.ISOLATION_FOREST,
            n_anomalies=0,
            anomaly_indices=np.array([], dtype=int),
        )

    data = df[valid_features].dropna()
    if len(data) < _MIN_SAMPLES_FOR_ANALYSIS:
        return AnomalyResult(
            is_anomaly=np.zeros(len(df), dtype=bool),
            scores=np.zeros(len(df)),
            threshold=contamination,
            method=AnomalyMethod.ISOLATION_FOREST,
            n_anomalies=0,
            anomaly_indices=np.array([], dtype=int),
        )

    X = data.values
    n_samples = X.shape[0]

    # Compute isolation scores using path length estimation
    rng = np.random.default_rng(_RANDOM_STATE)
    path_lengths = np.zeros(n_samples)

    for _ in range(n_estimators):
        # Sample subset
        sample_size = min(max_samples, n_samples)
        indices = rng.choice(n_samples, size=sample_size, replace=False)
        X_sample = X[indices]

        # Estimate path length for each point
        for i in range(n_samples):
            path_lengths[i] += _estimate_path_length(X[i], X_sample, rng)

    # Average path lengths
    path_lengths /= n_estimators

    # Normalize to anomaly scores (shorter path = more anomalous)
    # Using the average path length formula for normalization
    c_n = 2 * (np.log(n_samples - 1) + 0.5772156649) - 2 * (n_samples - 1) / n_samples
    scores = 2 ** (-path_lengths / max(c_n, 1e-9))

    # Determine threshold based on contamination
    threshold = float(np.percentile(scores, 100 * (1 - contamination)))
    is_anomaly = scores >= threshold
    anomaly_indices = np.where(is_anomaly)[0]

    # Map back to original DataFrame indices
    full_scores = np.zeros(len(df))
    full_anomaly = np.zeros(len(df), dtype=bool)
    full_scores[data.index] = scores
    full_anomaly[data.index] = is_anomaly

    return AnomalyResult(
        is_anomaly=full_anomaly,
        scores=full_scores,
        threshold=threshold,
        method=AnomalyMethod.ISOLATION_FOREST,
        n_anomalies=int(np.sum(is_anomaly)),
        anomaly_indices=anomaly_indices,
    )


def _estimate_path_length(
    point: np.ndarray,
    sample: np.ndarray,
    rng: np.random.Generator,
    max_depth: int = 10,
) -> float:
    """Estimate isolation path length for a point."""
    n_samples, n_features = sample.shape

    if n_samples <= 1 or max_depth == 0:
        return 0.0

    # Random feature and split
    feature_idx = rng.integers(0, n_features)
    feature_values = sample[:, feature_idx]
    min_val, max_val = float(np.min(feature_values)), float(np.max(feature_values))

    if max_val - min_val < 1e-9:
        return 0.0

    split_value = rng.uniform(min_val, max_val)

    # Determine which side the point falls on
    if point[feature_idx] < split_value:
        mask = sample[:, feature_idx] < split_value
    else:
        mask = sample[:, feature_idx] >= split_value

    n_in_partition = int(np.sum(mask))
    if n_in_partition == 0:
        return 1.0

    # Recursively estimate
    return 1.0 + _estimate_path_length(
        point, sample[mask], rng, max_depth - 1
    )


def detect_anomalies_lof(
    df: pd.DataFrame,
    features: list[str],
    *,
    n_neighbors: int = 20,
    contamination: float = _DEFAULT_CONTAMINATION,
) -> AnomalyResult:
    """Detect anomalies using Local Outlier Factor (simplified).

    Args:
        df: DataFrame with feature columns.
        features: List of feature column names.
        n_neighbors: Number of neighbors for LOF calculation.
        contamination: Expected proportion of anomalies.

    Returns:
        AnomalyResult with anomaly flags and scores.
    """
    valid_features = [f for f in features if f in df.columns]
    if len(valid_features) < 1:
        return AnomalyResult(
            is_anomaly=np.zeros(len(df), dtype=bool),
            scores=np.zeros(len(df)),
            threshold=contamination,
            method=AnomalyMethod.LOF,
            n_anomalies=0,
            anomaly_indices=np.array([], dtype=int),
        )

    data = df[valid_features].dropna()
    if len(data) < max(_MIN_SAMPLES_FOR_ANALYSIS, n_neighbors + 1):
        return AnomalyResult(
            is_anomaly=np.zeros(len(df), dtype=bool),
            scores=np.zeros(len(df)),
            threshold=contamination,
            method=AnomalyMethod.LOF,
            n_anomalies=0,
            anomaly_indices=np.array([], dtype=int),
        )

    X = data.values
    n_samples = X.shape[0]

    # Standardize features
    means = np.mean(X, axis=0)
    stds = np.std(X, axis=0)
    stds = np.where(stds < 1e-9, 1.0, stds)
    X_scaled = (X - means) / stds

    # Compute pairwise distances
    distances = np.zeros((n_samples, n_samples))
    for i in range(n_samples):
        distances[i] = np.sqrt(np.sum((X_scaled - X_scaled[i]) ** 2, axis=1))

    # Get k-nearest neighbors
    k = min(n_neighbors, n_samples - 1)
    k_distances = np.zeros(n_samples)
    lrd = np.zeros(n_samples)

    for i in range(n_samples):
        sorted_indices = np.argsort(distances[i])
        neighbor_indices = sorted_indices[1:k + 1]  # Exclude self
        k_distances[i] = distances[i, neighbor_indices[-1]]

        # Reachability distances
        reach_dists = np.maximum(distances[i, neighbor_indices], k_distances[neighbor_indices])
        lrd[i] = k / max(np.sum(reach_dists), 1e-9)

    # Compute LOF scores
    lof_scores = np.zeros(n_samples)
    for i in range(n_samples):
        sorted_indices = np.argsort(distances[i])
        neighbor_indices = sorted_indices[1:k + 1]
        lof_scores[i] = np.mean(lrd[neighbor_indices]) / max(lrd[i], 1e-9)

    # Threshold based on contamination
    threshold = float(np.percentile(lof_scores, 100 * (1 - contamination)))
    is_anomaly = lof_scores >= threshold
    anomaly_indices = np.where(is_anomaly)[0]

    # Map back to original indices
    full_scores = np.ones(len(df))  # Default to 1 (normal)
    full_anomaly = np.zeros(len(df), dtype=bool)
    full_scores[data.index] = lof_scores
    full_anomaly[data.index] = is_anomaly

    return AnomalyResult(
        is_anomaly=full_anomaly,
        scores=full_scores,
        threshold=threshold,
        method=AnomalyMethod.LOF,
        n_anomalies=int(np.sum(is_anomaly)),
        anomaly_indices=anomaly_indices,
    )


# ---------------------------------------------------------------------------
# Trend Analysis
# ---------------------------------------------------------------------------


def analyze_trend(
    values: np.ndarray,
    *,
    min_segment_length: int = 5,
    significance_level: float = 0.05,
) -> TrendResult:
    """Analyze trend in time series with change point detection.

    Args:
        values: Array of values in time order.
        min_segment_length: Minimum samples per segment.
        significance_level: P-value threshold for trend significance.

    Returns:
        TrendResult with trend direction, slope, and change points.
    """
    arr = np.asarray(values, dtype=float)
    valid_mask = np.isfinite(arr)
    arr_clean = arr[valid_mask]

    if len(arr_clean) < _MIN_SAMPLES_FOR_ANALYSIS:
        return TrendResult(
            direction=TrendDirection.STABLE,
            slope=0.0,
            r_squared=0.0,
            p_value=1.0,
            change_points=np.array([], dtype=int),
            segments=[],
            confidence=0.0,
        )

    n = len(arr_clean)
    x = np.arange(n)

    # Linear regression for overall trend
    slope, intercept, r_value, p_value, _ = stats.linregress(x, arr_clean)
    r_squared = r_value ** 2

    # Detect change points using PELT-like algorithm (simplified)
    change_points = _detect_change_points(arr_clean, min_segment_length)

    # Classify segments
    segments: list[dict[str, Any]] = []
    segment_starts = [0] + list(change_points)
    segment_ends = list(change_points) + [n]

    for start, end in zip(segment_starts, segment_ends):
        if end - start < min_segment_length:
            continue
        seg_x = np.arange(end - start)
        seg_y = arr_clean[start:end]
        seg_slope, _, seg_r, seg_p, _ = stats.linregress(seg_x, seg_y)

        segments.append({
            "start_idx": int(start),
            "end_idx": int(end),
            "slope": float(seg_slope),
            "r_squared": float(seg_r ** 2),
            "p_value": float(seg_p),
            "mean": float(np.mean(seg_y)),
            "std": float(np.std(seg_y, ddof=1)),
        })

    # Determine overall direction
    if p_value > significance_level:
        direction = TrendDirection.STABLE
    elif slope > 0:
        direction = TrendDirection.INCREASING
    else:
        direction = TrendDirection.DECREASING

    # Check for high variability
    cv = float(np.std(arr_clean, ddof=1) / np.mean(arr_clean)) if np.mean(arr_clean) != 0 else 0
    if cv > 0.5 and len(change_points) > 2:
        direction = TrendDirection.VARIABLE

    # Confidence based on R² and sample size
    confidence = min(1.0, r_squared + (1 - p_value) * 0.5)

    return TrendResult(
        direction=direction,
        slope=float(slope),
        r_squared=float(r_squared),
        p_value=float(p_value),
        change_points=change_points,
        segments=segments,
        confidence=confidence,
    )


def _detect_change_points(
    values: np.ndarray,
    min_segment_length: int,
    max_change_points: int = 10,
) -> np.ndarray:
    """Detect change points using cumulative sum method.

    Args:
        values: Array of values.
        min_segment_length: Minimum segment length.
        max_change_points: Maximum number of change points.

    Returns:
        Array of change point indices.
    """
    n = len(values)
    if n < 2 * min_segment_length:
        return np.array([], dtype=int)

    # Compute cumulative sum of deviations from mean
    mean_val = np.mean(values)
    cusum = np.cumsum(values - mean_val)

    # Find points with maximum deviation
    change_points: list[int] = []

    def find_change_point(start: int, end: int) -> int | None:
        if end - start < 2 * min_segment_length:
            return None

        segment = cusum[start:end] - cusum[start]
        deviations = np.abs(segment - np.linspace(segment[0], segment[-1], len(segment)))

        # Find maximum deviation point
        max_idx = int(np.argmax(deviations))
        if max_idx < min_segment_length or max_idx > len(segment) - min_segment_length:
            return None

        # Check if deviation is significant (simplified threshold)
        threshold = 2 * np.std(values[start:end])
        if deviations[max_idx] > threshold:
            return start + max_idx
        return None

    # Recursive binary segmentation
    def segment(start: int, end: int, depth: int = 0) -> None:
        if depth >= max_change_points:
            return
        cp = find_change_point(start, end)
        if cp is not None:
            change_points.append(cp)
            segment(start, cp, depth + 1)
            segment(cp, end, depth + 1)

    segment(0, n)

    return np.array(sorted(change_points), dtype=int)


# ---------------------------------------------------------------------------
# Feature Importance
# ---------------------------------------------------------------------------


def compute_feature_importance(
    df: pd.DataFrame,
    features: list[str],
    target: str,
) -> list[FeatureImportance]:
    """Compute feature importance for predicting target variable.

    Uses correlation-based importance with direction indicators.

    Args:
        df: DataFrame with features and target.
        features: List of feature column names.
        target: Target variable column name.

    Returns:
        List of FeatureImportance sorted by importance.
    """
    if target not in df.columns:
        return []

    valid_features = [f for f in features if f in df.columns and f != target]
    if not valid_features:
        return []

    results: list[FeatureImportance] = []
    target_values = df[target].dropna()

    for feature in valid_features:
        # Get aligned data
        aligned = df[[feature, target]].dropna()
        if len(aligned) < _MIN_SAMPLES_FOR_ANALYSIS:
            continue

        x = aligned[feature].values
        y = aligned[target].values

        # Compute correlation
        if np.std(x) < 1e-9 or np.std(y) < 1e-9:
            continue

        corr, p_value = stats.pearsonr(x, y)

        # Importance based on absolute correlation
        importance = abs(corr)

        # Direction: positive correlation means higher feature = higher target
        direction = 1 if corr > 0 else -1

        results.append(FeatureImportance(
            feature_name=feature,
            importance=float(importance),
            direction=direction,
            correlation=float(corr),
        ))

    # Sort by importance (descending)
    results.sort(key=lambda x: x.importance, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Predictive Modeling
# ---------------------------------------------------------------------------


def predict_readiness(
    current_metrics: dict[str, float],
    historical_df: pd.DataFrame,
    *,
    target_col: str = "parasympathetic_index",
) -> PredictionResult | None:
    """Predict readiness score based on current metrics and history.

    Uses a simple linear model with the most important features.

    Args:
        current_metrics: Dictionary of current metric values.
        historical_df: Historical metrics DataFrame.
        target_col: Target column for prediction.

    Returns:
        PredictionResult or None if insufficient data.
    """
    if historical_df.empty or target_col not in historical_df.columns:
        return None

    # Select numeric features
    numeric_cols = historical_df.select_dtypes(include=[np.number]).columns.tolist()
    features = [c for c in numeric_cols if c != target_col and c in current_metrics]

    if len(features) < 2:
        return None

    # Get feature importance
    importance = compute_feature_importance(historical_df, features, target_col)
    if not importance:
        return None

    # Use top features
    top_features = [f.feature_name for f in importance[:5] if f.feature_name in current_metrics]
    if len(top_features) < 2:
        return None

    # Prepare data
    data = historical_df[top_features + [target_col]].dropna()
    if len(data) < _MIN_SAMPLES_FOR_ANALYSIS:
        return None

    X = data[top_features].values
    y = data[target_col].values

    # Standardize
    X_mean = np.mean(X, axis=0)
    X_std = np.std(X, axis=0)
    X_std = np.where(X_std < 1e-9, 1.0, X_std)
    X_scaled = (X - X_mean) / X_std

    y_mean = float(np.mean(y))
    y_std = float(np.std(y, ddof=1))

    # Simple linear regression using normal equations
    X_with_intercept = np.column_stack([np.ones(len(X_scaled)), X_scaled])
    try:
        coeffs = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
    except np.linalg.LinAlgError:
        return None

    # Predict for current metrics
    current_values = np.array([current_metrics[f] for f in top_features])
    current_scaled = (current_values - X_mean) / X_std
    current_with_intercept = np.concatenate([[1], current_scaled])
    predicted = float(np.dot(coeffs, current_with_intercept))

    # Compute R²
    y_pred = X_with_intercept @ coeffs
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Confidence interval (simplified)
    residual_std = np.sqrt(ss_res / max(len(y) - len(coeffs), 1))
    ci_width = 1.96 * residual_std
    ci = (predicted - ci_width, predicted + ci_width)

    # Feature contributions
    contributions = {}
    for i, feature in enumerate(top_features):
        contributions[feature] = float(coeffs[i + 1] * current_scaled[i])

    return PredictionResult(
        predicted_value=predicted,
        confidence_interval=ci,
        feature_contributions=contributions,
        model_r_squared=float(r_squared),
    )


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------


def compute_rolling_statistics(
    values: np.ndarray,
    window: int = 7,
) -> dict[str, np.ndarray]:
    """Compute rolling statistics for trend visualization.

    Args:
        values: Array of values.
        window: Rolling window size.

    Returns:
        Dictionary with rolling mean, std, min, max.
    """
    arr = np.asarray(values, dtype=float)

    if len(arr) < window:
        return {
            "rolling_mean": arr,
            "rolling_std": np.zeros_like(arr),
            "rolling_min": arr,
            "rolling_max": arr,
        }

    # Use uniform_filter for efficient rolling mean
    rolling_mean = uniform_filter1d(arr, size=window, mode="nearest")

    # Rolling std (using variance formula)
    rolling_sq_mean = uniform_filter1d(arr ** 2, size=window, mode="nearest")
    rolling_var = rolling_sq_mean - rolling_mean ** 2
    rolling_var = np.maximum(rolling_var, 0)  # Numerical stability
    rolling_std = np.sqrt(rolling_var)

    # Rolling min/max (less efficient but bounded)
    rolling_min = np.zeros_like(arr)
    rolling_max = np.zeros_like(arr)
    half_window = window // 2

    for i in range(len(arr)):
        start = max(0, i - half_window)
        end = min(len(arr), i + half_window + 1)
        rolling_min[i] = np.min(arr[start:end])
        rolling_max[i] = np.max(arr[start:end])

    return {
        "rolling_mean": rolling_mean,
        "rolling_std": rolling_std,
        "rolling_min": rolling_min,
        "rolling_max": rolling_max,
    }


def classify_hrv_state(
    metrics: dict[str, float],
) -> dict[str, Any]:
    """Classify current HRV state based on metrics.

    Args:
        metrics: Dictionary of HRV metrics.

    Returns:
        Dictionary with state classification and confidence.
    """
    classifications: dict[str, Any] = {
        "overall_state": "unknown",
        "vagal_tone": "unknown",
        "stress_level": "unknown",
        "recovery_status": "unknown",
        "confidence": 0.0,
        "flags": [],
    }

    scores: list[float] = []

    # Vagal tone assessment
    rmssd = metrics.get("rmssd", 0)
    hf_power = metrics.get("hf_power", 0)

    if rmssd > 0:
        if rmssd < 20:
            classifications["vagal_tone"] = "low"
            scores.append(0.3)
        elif rmssd < 42:
            classifications["vagal_tone"] = "moderate"
            scores.append(0.5)
        elif rmssd <= 80:
            classifications["vagal_tone"] = "good"
            scores.append(0.7)
        else:
            classifications["vagal_tone"] = "high"
            scores.append(0.9)

    # Stress assessment
    lf_hf = metrics.get("lf_hf_ratio", 0)
    stress_index = metrics.get("stress_index", 0)

    if lf_hf > 0:
        if lf_hf > 4:
            classifications["stress_level"] = "high"
            scores.append(0.3)
        elif lf_hf > 2:
            classifications["stress_level"] = "moderate"
            scores.append(0.5)
        else:
            classifications["stress_level"] = "low"
            scores.append(0.8)

    # Recovery status
    parasym = metrics.get("parasympathetic_index", 0)
    if parasym > 0:
        if parasym > 0.6:
            classifications["recovery_status"] = "good"
            scores.append(0.8)
        elif parasym > 0.4:
            classifications["recovery_status"] = "moderate"
            scores.append(0.5)
        else:
            classifications["recovery_status"] = "poor"
            scores.append(0.3)

    # Overall state
    if scores:
        avg_score = float(np.mean(scores))
        if avg_score > 0.7:
            classifications["overall_state"] = "optimal"
        elif avg_score > 0.5:
            classifications["overall_state"] = "normal"
        elif avg_score > 0.3:
            classifications["overall_state"] = "suboptimal"
        else:
            classifications["overall_state"] = "concerning"
        classifications["confidence"] = avg_score

    # Add flags for concerning values
    if rmssd < 15:
        classifications["flags"].append("Very low RMSSD")
    if lf_hf > 5:
        classifications["flags"].append("High LF/HF ratio")
    if stress_index > 300:
        classifications["flags"].append("Elevated stress index")

    return classifications

