from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class KMeansResult:
	"""Return value containing enriched windowed data and per-cluster summary."""

	windowed_with_clusters: pd.DataFrame
	cluster_summary: pd.DataFrame


def _select_feature_columns(windowed_df: pd.DataFrame, metrics: Sequence[str]) -> Sequence[str]:
	candidates = list(dict.fromkeys(metrics))
	if "dev_index" not in candidates and "dev_index" in windowed_df.columns:
		candidates = ["dev_index"] + candidates
	features = [col for col in candidates if col in windowed_df.columns]
	if not features:
		raise ValueError("No overlap between requested metrics and windowed dataframe columns.")
	return features


def _standardize_features(values: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
	means = np.mean(values, axis=0)
	stds = np.std(values, axis=0)
	stds = np.where(stds < 1e-9, 1.0, stds)
	return (values - means) / stds, means, stds


def _initialise_centers(data: np.ndarray, n_clusters: int) -> np.ndarray:
	indices = np.linspace(0, data.shape[0] - 1, num=n_clusters, dtype=int)
	return data[indices].copy()


def _assign_clusters(data: np.ndarray, centers: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
	distances = np.linalg.norm(data[:, None, :] - centers[None, :, :], axis=2)
	labels = np.argmin(distances, axis=1)
	min_distances = distances[np.arange(distances.shape[0]), labels]
	return labels, min_distances


def _update_centers(data: np.ndarray, labels: np.ndarray, n_clusters: int) -> np.ndarray:
	centers = np.zeros((n_clusters, data.shape[1]), dtype=float)
	for cluster_idx in range(n_clusters):
		mask = labels == cluster_idx
		if np.any(mask):
			centers[cluster_idx] = np.mean(data[mask], axis=0)
		else:
			# Reuse farthest point to avoid empty cluster.
			distances = np.linalg.norm(data, axis=1)
			far_point = data[np.argmax(distances)]
			centers[cluster_idx] = far_point
	return centers


def _cluster_names(high_risk_cluster: int, cluster_idx: int) -> str:
	return "High deviation cluster" if cluster_idx == high_risk_cluster else "Baseline cluster"


def _compute_cluster_summary(
	raw_values: np.ndarray,
	labels: np.ndarray,
	score_lookup: np.ndarray,
	features: Sequence[str],
	high_risk_cluster: int,
) -> pd.DataFrame:
	rows = []
	for cluster_idx in np.unique(labels):
		mask = labels == cluster_idx
		cluster_values = raw_values[mask]
		row = {
			"cluster_label": int(cluster_idx),
			"cluster_name": _cluster_names(high_risk_cluster, int(cluster_idx)),
			"windows": int(cluster_values.shape[0]),
			"mean_cluster_score": float(np.mean(score_lookup[mask])),
		}
		for feature_idx, feature_name in enumerate(features):
			row[f"mean_{feature_name}"] = float(np.mean(cluster_values[:, feature_idx]))
		rows.append(row)
	return pd.DataFrame(rows)


def run_windowed_kmeans(
	windowed_df: pd.DataFrame,
	metrics: Sequence[str],
	*,
	n_clusters: int = 2,
	max_iterations: int = 50,
) -> KMeansResult:
	"""Cluster windowed HRV metrics to identify higher-risk deviation segments.

	This routine performs a small-footprint k-means clustering on selected
	features. The algorithm is deterministic (no random sampling) and bounded
	by `max_iterations`. When the result converges early, the loop exits.

	Args:
		windowed_df: DataFrame containing windowed metrics.
		metrics: Sequence of metric column names to include in the feature set.
		n_clusters: Number of clusters; defaults to 2 (baseline vs deviation).
		max_iterations: Maximum number of k-means iterations to execute.

	Returns:
		KMeansResult with the enriched windowed dataframe and a cluster summary.

	Raises:
		ValueError: If there are insufficient windows or features for clustering.
	"""
	if windowed_df.empty:
		raise ValueError("Windowed dataframe is empty; cannot perform clustering.")
	if n_clusters < 2:
		raise ValueError("n_clusters must be at least 2.")
	features = _select_feature_columns(windowed_df, metrics)
	feature_frame = windowed_df[features].dropna()
	if feature_frame.shape[0] < n_clusters:
		raise ValueError("Not enough windowed samples to form the requested clusters.")
	raw_values = feature_frame.to_numpy(dtype=float)
	standardised, _, _ = _standardize_features(raw_values)
	centers = _initialise_centers(standardised, n_clusters)
	labels = np.zeros(standardised.shape[0], dtype=int)
	for iteration in range(max_iterations):
		new_labels, _ = _assign_clusters(standardised, centers)
		if np.array_equal(new_labels, labels) and iteration > 0:
			break
		labels = new_labels
		centers = _update_centers(standardised, labels, n_clusters)
	cluster_means_raw = []
	for cluster_idx in range(n_clusters):
		mask = labels == cluster_idx
		if np.any(mask):
			cluster_means_raw.append(np.mean(raw_values[mask], axis=0))
		else:
			cluster_means_raw.append(np.zeros(raw_values.shape[1]))
	cluster_means = np.vstack(cluster_means_raw)
	if "dev_index" in features:
		dev_idx = features.index("dev_index")
		risk_scores = cluster_means[:, dev_idx]
	else:
		risk_scores = np.mean(cluster_means, axis=1)
	high_risk_cluster = int(np.argmax(risk_scores))
	score_values = risk_scores[labels]
	score_min = float(np.min(risk_scores))
	score_max = float(np.max(risk_scores))
	if score_max - score_min > 1e-9:
		normalised_scores = (score_values - score_min) / (score_max - score_min)
	else:
		normalised_scores = np.zeros_like(score_values)
	windowed_enriched = windowed_df.copy()
	windowed_enriched["ml_cluster_label"] = -1
	windowed_enriched["ml_cluster_score"] = np.nan
	windowed_enriched["ml_cluster_name"] = "Unassigned"
	windowed_enriched["ml_flagged_high_deviation"] = False
	for row_index, original_idx in enumerate(feature_frame.index):
		label = int(labels[row_index])
		windowed_enriched.at[original_idx, "ml_cluster_label"] = label
		windowed_enriched.at[original_idx, "ml_cluster_score"] = float(normalised_scores[row_index])
		windowed_enriched.at[original_idx, "ml_cluster_name"] = _cluster_names(high_risk_cluster, label)
		windowed_enriched.at[original_idx, "ml_flagged_high_deviation"] = bool(label == high_risk_cluster)
	windowed_enriched["ml_cluster_label"] = windowed_enriched["ml_cluster_label"].astype(int)
	cluster_summary = _compute_cluster_summary(raw_values, labels, normalised_scores, features, high_risk_cluster)
	return KMeansResult(windowed_with_clusters=windowed_enriched, cluster_summary=cluster_summary)

