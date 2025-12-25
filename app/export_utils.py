from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Optional, Sequence

import numpy as np
import pandas as pd


class ExportScope(str, Enum):
	"""Enumeration describing the level of detail to include in the export."""

	SUMMARY = "summary"
	COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class ExportConfiguration:
	"""Configuration options controlling which sections appear in the export."""

	scope: ExportScope
	include_windowed: bool
	include_ml: bool
	max_rows_summary: int = 25


def _format_value(value: Any) -> str:
	"""Return a string representation with consistent formatting for numbers."""
	if value is None:
		return ""
	if isinstance(value, float):
		if not np.isfinite(value):
			return ""
		if abs(value) >= 1000.0 or abs(value) < 0.001:
			return f"{value:.3e}"
		return f"{value:.4f}".rstrip("0").rstrip(".")
	if isinstance(value, (bool, np.bool_)):
		return "True" if value else "False"
	if isinstance(value, (np.integer, int)):
		return str(int(value))
	return str(value)


def _dataframe_to_markdown(df: pd.DataFrame, *, max_rows: Optional[int]) -> str:
	"""Convert a DataFrame to GitHub-flavoured markdown without external deps."""
	if df.empty:
		return "_No data available._"
	display_df = df.copy()
	if max_rows is not None and max_rows > 0 and len(display_df.index) > max_rows:
		display_df = display_df.head(max_rows)
		footnote = f"\n> Showing the first {max_rows} of {len(df.index)} rows."
	else:
		footnote = ""
	columns = [str(col) for col in display_df.columns]
	header = "| " + " | ".join(columns) + " |"
	separator = "| " + " | ".join(["---"] * len(columns)) + " |"
	lines = [header, separator]
	for _, row in display_df.iterrows():
		values = [_format_value(row[col]) for col in display_df.columns]
		lines.append("| " + " | ".join(values) + " |")
	return "\n".join(lines) + footnote


def _filter_sources(df: pd.DataFrame, sources: Sequence[str]) -> pd.DataFrame:
	if df.empty or not sources:
		return df
	if "source" not in df.columns:
		return df
	return df[df["source"].isin(sources)].copy()


@dataclass(frozen=True, slots=True)
class CohortExportConfiguration:
	"""Configuration for cohort (group) summary exports."""

	scope: ExportScope = ExportScope.SUMMARY
	max_rows_individual: int = 50


def compute_cohort_summary_stats(
	cohort_df: pd.DataFrame,
	*,
	numeric_columns: Sequence[str],
) -> pd.DataFrame:
	"""Compute descriptive statistics across a cohort table.

	This helper is designed for cohort exports where each row is a user snapshot
	(e.g., latest HRV + latest clinical scales + latest medical record).

	Args:
		cohort_df: DataFrame containing per-user rows.
		numeric_columns: Column names to treat as numeric for aggregation.

	Returns:
		A DataFrame with one row per metric and columns:
		`metric`, `n`, `mean`, `std`, `median`, `min`, `max`.

	Raises:
		TypeError: If cohort_df is not a DataFrame.
	"""
	if not isinstance(cohort_df, pd.DataFrame):
		raise TypeError("cohort_df must be a pandas DataFrame.")
	if cohort_df.empty or not numeric_columns:
		return pd.DataFrame(
			columns=["metric", "n", "mean", "std", "median", "min", "max"]
		)

	rows: list[dict[str, Any]] = []
	for col in numeric_columns:
		if col not in cohort_df.columns:
			continue
		series = pd.to_numeric(cohort_df[col], errors="coerce").dropna()
		if series.empty:
			continue
		rows.append(
			{
				"metric": col,
				"n": int(series.shape[0]),
				"mean": float(series.mean()),
				"std": float(series.std(ddof=1)) if series.shape[0] > 1 else float("nan"),
				"median": float(series.median()),
				"min": float(series.min()),
				"max": float(series.max()),
			}
		)
	return pd.DataFrame(rows)


def build_cohort_markdown_report(
	*,
	cohort_df: pd.DataFrame,
	cohort_stats_df: pd.DataFrame,
	config: CohortExportConfiguration,
	additional_notes: str = "",
) -> str:
	"""Build a markdown report for cohort-level exports.

	Args:
		cohort_df: Per-user cohort snapshot table.
		cohort_stats_df: Cohort-level descriptive stats computed from cohort_df.
		config: CohortExportConfiguration controlling output shape.
		additional_notes: Optional analyst notes.

	Returns:
		A markdown string suitable for export/download.

	Raises:
		ValueError: If cohort_df is empty.
	"""
	if not isinstance(cohort_df, pd.DataFrame) or cohort_df.empty:
		raise ValueError("No cohort rows available to export.")

	lines: list[str] = []
	timestamp = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
	lines.append("# Cohort Summary Report")
	lines.append("")
	lines.append(f"- Generated: `{timestamp}`")
	lines.append(f"- Scope: `{config.scope.value}`")
	lines.append(f"- Subjects: `{int(cohort_df.shape[0])}`")
	lines.append("")

	lines.append("## Cohort roster (latest snapshot per subject)")
	lines.append("")
	lines.append(
		_dataframe_to_markdown(
			cohort_df,
			max_rows=(
				int(config.max_rows_individual)
				if config.scope == ExportScope.SUMMARY
				else None
			),
		)
	)
	lines.append("")

	if isinstance(cohort_stats_df, pd.DataFrame) and not cohort_stats_df.empty:
		lines.append("## Cohort descriptive statistics")
		lines.append("")
		lines.append(_dataframe_to_markdown(cohort_stats_df, max_rows=None))
		lines.append("")

	if additional_notes.strip():
		lines.append("## Analyst Notes")
		lines.append("")
		lines.append(additional_notes.strip())
		lines.append("")

	lines.append("_End of report._")
	return "\n".join(lines)


def build_cohort_longitudinal_delta_long_df(
	*,
	user_timepoint_tables: Mapping[str, pd.DataFrame],
	user_group_map: Mapping[str, str],
	metrics: Sequence[str],
) -> pd.DataFrame:
	"""Build a long-form (tidy) cohort table of per-user deltas by timepoint.

	This function consumes per-user timepoint summary tables produced by
	`UserDatabase.get_hrv_timepoint_change_table()` (or
	`build_timepoint_change_table_from_hrv_df()`).

	Each output row represents a single subject's delta value for one metric at one
	timepoint:
	- `delta` is computed as (timepoint_value - subject_baseline_value) per metric.

	Args:
		user_timepoint_tables: Mapping of user_id -> timepoint summary DataFrame.
		user_group_map: Mapping of user_id -> group label (e.g., "Control", "Intervention").
		metrics: Metric column names to include (e.g., "rmssd_ms", "sdnn_ms").

	Returns:
		DataFrame with columns:
		`user_id`, `group`, `timepoint_label`, `metric`, `value`, `baseline`, `delta`.
		Returns empty DataFrame if inputs are empty or no compatible columns exist.
	"""
	if not user_timepoint_tables or not user_group_map or not metrics:
		return pd.DataFrame(
			columns=["user_id", "group", "timepoint_label", "metric", "value", "baseline", "delta"]
		)

	rows: list[dict[str, Any]] = []
	for user_id, tp_df in user_timepoint_tables.items():
		if not isinstance(tp_df, pd.DataFrame) or tp_df.empty:
			continue
		group = str(user_group_map.get(str(user_id), "")).strip()
		if not group:
			continue

		if "timepoint_label" not in tp_df.columns:
			continue

		for metric in metrics:
			metric_name = str(metric).strip()
			if not metric_name:
				continue
			delta_col = f"delta_{metric_name}"
			baseline_col = f"baseline_{metric_name}"
			if metric_name not in tp_df.columns:
				continue
			if delta_col not in tp_df.columns or baseline_col not in tp_df.columns:
				continue

			# Bounded per-user loop: at most ~22 timepoints.
			for _, row in tp_df.iterrows():
				label = row.get("timepoint_label")
				if label is None:
					continue
				label_str = str(label).strip()
				if not label_str:
					continue
				rows.append(
					{
						"user_id": str(user_id),
						"group": group,
						"timepoint_label": label_str,
						"metric": metric_name,
						"value": row.get(metric_name),
						"baseline": row.get(baseline_col),
						"delta": row.get(delta_col),
					}
				)

	if not rows:
		return pd.DataFrame(
			columns=["user_id", "group", "timepoint_label", "metric", "value", "baseline", "delta"]
		)

	out = pd.DataFrame(rows)
	out["delta"] = pd.to_numeric(out["delta"], errors="coerce")
	out["value"] = pd.to_numeric(out["value"], errors="coerce")
	out["baseline"] = pd.to_numeric(out["baseline"], errors="coerce")
	return out


def compute_cohort_longitudinal_group_summary(
	cohort_long_df: pd.DataFrame,
	*,
	agg: str = "mean",
) -> pd.DataFrame:
	"""Aggregate longitudinal deltas by group × timepoint × metric.

	Args:
		cohort_long_df: Output of `build_cohort_longitudinal_delta_long_df()`.
		agg: Central tendency to emphasize: "mean" or "median".

	Returns:
		DataFrame with one row per (group, timepoint_label, metric) with:
		`n`, `mean_delta`, `std_delta`, `median_delta`, `min_delta`, `max_delta`.
	"""
	if not isinstance(cohort_long_df, pd.DataFrame) or cohort_long_df.empty:
		return pd.DataFrame(
			columns=[
				"group",
				"timepoint_label",
				"metric",
				"n",
				"mean_delta",
				"std_delta",
				"median_delta",
				"min_delta",
				"max_delta",
			]
		)
	mode = str(agg or "").strip().lower()
	if mode not in {"mean", "median"}:
		raise ValueError("agg must be 'mean' or 'median'")

	df = cohort_long_df.copy()
	for col in ("group", "timepoint_label", "metric"):
		if col not in df.columns:
			return pd.DataFrame(
				columns=[
					"group",
					"timepoint_label",
					"metric",
					"n",
					"mean_delta",
					"std_delta",
					"median_delta",
					"min_delta",
					"max_delta",
				]
			)

	df["delta"] = pd.to_numeric(df.get("delta"), errors="coerce")
	df = df.dropna(subset=["delta"])
	if df.empty:
		return pd.DataFrame(
			columns=[
				"group",
				"timepoint_label",
				"metric",
				"n",
				"mean_delta",
				"std_delta",
				"median_delta",
				"min_delta",
				"max_delta",
			]
		)

	rows: list[dict[str, Any]] = []
	for (group, label, metric), g in df.groupby(["group", "timepoint_label", "metric"], sort=False):
		series = pd.to_numeric(g["delta"], errors="coerce").dropna()
		if series.empty:
			continue
		rows.append(
			{
				"group": str(group),
				"timepoint_label": str(label),
				"metric": str(metric),
				"n": int(series.shape[0]),
				"mean_delta": float(series.mean()),
				"std_delta": float(series.std(ddof=1)) if series.shape[0] > 1 else float("nan"),
				"median_delta": float(series.median()),
				"min_delta": float(series.min()),
				"max_delta": float(series.max()),
			}
		)

	out = pd.DataFrame(rows)
	if out.empty:
		return out

	# Optional ordering: T0, T1, ... then other labels.
	def _tp_num(val: Any) -> int:
		s = str(val)
		if s.startswith("T0"):
			return 0
		if s.startswith("T") and s[1:].isdigit():
			return int(s[1:])
		return 10_000

	out["timepoint_number"] = out["timepoint_label"].apply(_tp_num)
	out = out.sort_values(["metric", "group", "timepoint_number", "timepoint_label"]).drop(columns=["timepoint_number"])
	if mode == "median":
		# Keep the same output schema; caller can decide which column to focus on.
		_ = mode  # explicit: mode is currently informational only
	return out.reset_index(drop=True)


def compare_cohort_longitudinal_groups(
	cohort_long_df: pd.DataFrame,
	*,
	group_a: str,
	group_b: str,
	alpha: float = 0.05,
	apply_fdr: bool = True,
) -> pd.DataFrame:
	"""Compare two groups' longitudinal deltas per timepoint × metric.

	This performs a between-groups comparison on subject-level deltas, i.e.,
	it compares Δ(timepoint - baseline) between groups rather than raw values.

	Args:
		cohort_long_df: Output of `build_cohort_longitudinal_delta_long_df()`.
		group_a: First group label.
		group_b: Second group label.
		alpha: Significance threshold.
		apply_fdr: Whether to apply Benjamini-Hochberg FDR across all comparisons.

	Returns:
		DataFrame with one row per (timepoint_label, metric) and columns including:
		`group_a_n`, `group_b_n`, `group_a_mean_delta`, `group_b_mean_delta`,
		`test_type`, `p_value`, `p_adjusted`, `effect_size_d`, `effect_interpretation`.
	"""
	if not isinstance(cohort_long_df, pd.DataFrame) or cohort_long_df.empty:
		return pd.DataFrame(
			columns=[
				"timepoint_label",
				"metric",
				"group_a",
				"group_b",
				"group_a_n",
				"group_b_n",
				"group_a_mean_delta",
				"group_b_mean_delta",
				"test_type",
				"p_value",
				"p_adjusted",
				"effect_size_d",
				"effect_interpretation",
				"recommendation",
			]
		)

	a = str(group_a or "").strip()
	b = str(group_b or "").strip()
	if not a or not b:
		raise ValueError("group_a and group_b are required")
	if a == b:
		raise ValueError("group_a and group_b must be different")

	df = cohort_long_df.copy()
	if "group" not in df.columns or "timepoint_label" not in df.columns or "metric" not in df.columns:
		return pd.DataFrame(
			columns=[
				"timepoint_label",
				"metric",
				"group_a",
				"group_b",
				"group_a_n",
				"group_b_n",
				"group_a_mean_delta",
				"group_b_mean_delta",
				"test_type",
				"p_value",
				"p_adjusted",
				"effect_size_d",
				"effect_interpretation",
				"recommendation",
			]
		)
	df["delta"] = pd.to_numeric(df.get("delta"), errors="coerce")
	df = df.dropna(subset=["delta"])
	df = df[df["group"].isin([a, b])]
	if df.empty:
		return pd.DataFrame(
			columns=[
				"timepoint_label",
				"metric",
				"group_a",
				"group_b",
				"group_a_n",
				"group_b_n",
				"group_a_mean_delta",
				"group_b_mean_delta",
				"test_type",
				"p_value",
				"p_adjusted",
				"effect_size_d",
				"effect_interpretation",
				"recommendation",
			]
		)

	# Local import to keep export_utils lightweight at import time.
	# Support both execution contexts:
	# - Streamlit runs `app/app.py` with `/workspace/app` on sys.path (imports `statistical_analysis`)
	# - Tests import the package as `app.*` (imports `app.statistical_analysis`)
	try:  # pragma: no cover - exercised in Streamlit runtime
		from statistical_analysis import compare_two_groups, fdr_correction  # type: ignore
	except Exception:  # pragma: no cover - exercised in pytest/package context
		from app.statistical_analysis import compare_two_groups, fdr_correction  # type: ignore

	rows: list[dict[str, Any]] = []
	p_values: list[float] = []
	for (label, metric), g in df.groupby(["timepoint_label", "metric"], sort=False):
		# Baseline deltas at T0 are always 0 by construction and are not meaningful to compare.
		label_str = str(label)
		if label_str.startswith("T0"):
			continue
		g_a = g[g["group"] == a]["delta"].to_numpy(dtype=float, copy=False)
		g_b = g[g["group"] == b]["delta"].to_numpy(dtype=float, copy=False)
		result = compare_two_groups(g_a, g_b, paired=False, alpha=float(alpha))
		p_values.append(float(result.p_value))
		rows.append(
			{
				"timepoint_label": label_str,
				"metric": str(metric),
				"group_a": a,
				"group_b": b,
				"group_a_n": int(result.group1_n),
				"group_b_n": int(result.group2_n),
				"group_a_mean_delta": float(result.group1_mean),
				"group_b_mean_delta": float(result.group2_mean),
				"test_type": str(result.test_type.value),
				"p_value": float(result.p_value),
				"p_adjusted": float(result.p_adjusted),
				"effect_size_d": float(result.effect_size),
				"effect_interpretation": str(result.effect_interpretation.value),
				"recommendation": str(result.recommendation),
			}
		)

	out = pd.DataFrame(rows)
	if out.empty:
		return out

	if apply_fdr:
		adj = fdr_correction(p_values, alpha=float(alpha))
		out["p_adjusted"] = adj
	return out


def fit_cohort_longitudinal_mixed_effects(
	cohort_long_df: pd.DataFrame,
	*,
	group_a: str,
	group_b: str,
	max_iter: int = 200,
) -> pd.DataFrame:
	"""Fit a mixed-effects model for Δ vs baseline with random subject intercepts.

	This implements a roadmap item: add mixed-effects models for Group × Time inference.

	Model (per metric):
		Δ ~ C(group) * C(timepoint_label) + (1 | user_id)

	Notes:
	- T0 deltas are excluded (always 0 by construction).
	- This is intended for small-to-moderate longitudinal cohorts (T0–T21).
	- The implementation is deterministic (bounded optimizer iterations) and fails closed
	  (returns an empty DataFrame or per-metric error rows).

	Args:
		cohort_long_df: Output of `build_cohort_longitudinal_delta_long_df()`.
		group_a: First group label (included).
		group_b: Second group label (included).
		max_iter: Maximum optimizer iterations (bounded).

	Returns:
		Tidy DataFrame of fixed-effects terms across metrics with columns:
		`metric`, `term`, `coef`, `std_err`, `z`, `p_value`, `ci_low`, `ci_high`,
		`n_obs`, `n_subjects`, `converged`, `aic`, `bic`.
	"""
	if not isinstance(cohort_long_df, pd.DataFrame) or cohort_long_df.empty:
		return pd.DataFrame(
			columns=[
				"metric",
				"term",
				"coef",
				"std_err",
				"z",
				"p_value",
				"ci_low",
				"ci_high",
				"n_obs",
				"n_subjects",
				"converged",
				"aic",
				"bic",
				"error",
			]
		)

	a = str(group_a or "").strip()
	b = str(group_b or "").strip()
	if not a or not b:
		raise ValueError("group_a and group_b are required")
	if a == b:
		raise ValueError("group_a and group_b must be different")
	if int(max_iter) <= 0:
		raise ValueError("max_iter must be positive")

	df = cohort_long_df.copy()
	required = {"user_id", "group", "timepoint_label", "metric", "delta"}
	if not required.issubset(set(df.columns)):
		return pd.DataFrame(
			columns=[
				"metric",
				"term",
				"coef",
				"std_err",
				"z",
				"p_value",
				"ci_low",
				"ci_high",
				"n_obs",
				"n_subjects",
				"converged",
				"aic",
				"bic",
				"error",
			]
		)

	df["group"] = df["group"].astype(str)
	df["timepoint_label"] = df["timepoint_label"].astype(str)
	df["metric"] = df["metric"].astype(str)
	df["user_id"] = df["user_id"].astype(str)
	df["delta"] = pd.to_numeric(df["delta"], errors="coerce")
	df = df.dropna(subset=["delta"])
	df = df[df["group"].isin([a, b])]
	df = df[~df["timepoint_label"].astype(str).str.startswith("T0")]
	if df.empty:
		return pd.DataFrame(
			columns=[
				"metric",
				"term",
				"coef",
				"std_err",
				"z",
				"p_value",
				"ci_low",
				"ci_high",
				"n_obs",
				"n_subjects",
				"converged",
				"aic",
				"bic",
				"error",
			]
		)

	# Local import (statsmodels is an optional-but-pinned dependency for this app).
	try:  # pragma: no cover - exercised in runtime; tests cover when installed
		import statsmodels.formula.api as smf  # type: ignore
	except Exception as exc:  # pragma: no cover
		return pd.DataFrame(
			[
				{
					"metric": "",
					"term": "",
					"coef": float("nan"),
					"std_err": float("nan"),
					"z": float("nan"),
					"p_value": float("nan"),
					"ci_low": float("nan"),
					"ci_high": float("nan"),
					"n_obs": int(df.shape[0]),
					"n_subjects": int(df["user_id"].nunique()),
					"converged": False,
					"aic": float("nan"),
					"bic": float("nan"),
					"error": f"statsmodels unavailable: {exc}",
				}
			]
		)

	rows: list[dict[str, Any]] = []
	for metric_name, g in df.groupby("metric", sort=False):
		sub = g.copy()
		n_obs = int(sub.shape[0])
		n_subjects = int(sub["user_id"].nunique())
		if n_obs < 6 or n_subjects < 2:
			rows.append(
				{
					"metric": str(metric_name),
					"term": "",
					"coef": float("nan"),
					"std_err": float("nan"),
					"z": float("nan"),
					"p_value": float("nan"),
					"ci_low": float("nan"),
					"ci_high": float("nan"),
					"n_obs": n_obs,
					"n_subjects": n_subjects,
					"converged": False,
					"aic": float("nan"),
					"bic": float("nan"),
					"error": "Insufficient observations/subjects for mixed-effects model.",
				}
			)
			continue

		# MixedLM expects categorical variables to be present as strings or categoricals.
		sub["group"] = sub["group"].astype("category")
		sub["timepoint_label"] = sub["timepoint_label"].astype("category")

		try:
			model = smf.mixedlm(
				"delta ~ C(group) * C(timepoint_label)",
				data=sub,
				groups=sub["user_id"],
			)
			res = model.fit(
				reml=False,
				method="lbfgs",
				maxiter=int(max_iter),
				disp=False,
			)
			params = res.params
			bse = res.bse
			pvals = getattr(res, "pvalues", None)
			ci = res.conf_int()
			converged = bool(getattr(res, "converged", True))
			aic = float(getattr(res, "aic", float("nan")))
			bic = float(getattr(res, "bic", float("nan")))

			for term in params.index:
				coef = float(params[term])
				std_err = float(bse[term]) if term in bse.index else float("nan")
				z = float(coef / std_err) if np.isfinite(std_err) and std_err != 0 else float("nan")
				p_value = float(pvals[term]) if pvals is not None and term in pvals.index else float("nan")
				ci_low = float(ci.loc[term, 0]) if term in ci.index else float("nan")
				ci_high = float(ci.loc[term, 1]) if term in ci.index else float("nan")
				rows.append(
					{
						"metric": str(metric_name),
						"term": str(term),
						"coef": coef,
						"std_err": std_err,
						"z": z,
						"p_value": p_value,
						"ci_low": ci_low,
						"ci_high": ci_high,
						"n_obs": n_obs,
						"n_subjects": n_subjects,
						"converged": converged,
						"aic": aic,
						"bic": bic,
						"error": "",
					}
				)
		except Exception as exc:
			rows.append(
				{
					"metric": str(metric_name),
					"term": "",
					"coef": float("nan"),
					"std_err": float("nan"),
					"z": float("nan"),
					"p_value": float("nan"),
					"ci_low": float("nan"),
					"ci_high": float("nan"),
					"n_obs": n_obs,
					"n_subjects": n_subjects,
					"converged": False,
					"aic": float("nan"),
					"bic": float("nan"),
					"error": f"{type(exc).__name__}: {exc}",
				}
			)

	out = pd.DataFrame(rows)
	if out.empty:
		return out
	# Present fixed effects first, then random effect variance terms.
	out["is_random"] = out["term"].astype(str).str.contains("Group Var", na=False)
	out = out.sort_values(["metric", "is_random", "term"]).drop(columns=["is_random"])
	return out.reset_index(drop=True)


def build_cohort_longitudinal_markdown_report(
	*,
	cohort_long_df: pd.DataFrame,
	group_summary_df: pd.DataFrame,
	comparisons_df: pd.DataFrame,
	mixed_effects_df: Optional[pd.DataFrame] = None,
	group_a: str,
	group_b: str,
	additional_notes: str = "",
) -> str:
	"""Build a markdown report for cohort longitudinal (T0–T21) comparisons."""
	if not isinstance(cohort_long_df, pd.DataFrame) or cohort_long_df.empty:
		raise ValueError("No longitudinal cohort rows available to export.")

	lines: list[str] = []
	timestamp = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
	lines.append("# Cohort Longitudinal Report (T0–T21)")
	lines.append("")
	lines.append(f"- Generated: `{timestamp}`")
	lines.append(f"- Groups: `{group_a}` vs `{group_b}`")
	lines.append("")

	lines.append("## Subject-level deltas (tidy format)")
	lines.append("")
	lines.append(_dataframe_to_markdown(cohort_long_df, max_rows=200))
	lines.append("")

	if isinstance(group_summary_df, pd.DataFrame) and not group_summary_df.empty:
		lines.append("## Group × timepoint delta summary")
		lines.append("")
		lines.append(_dataframe_to_markdown(group_summary_df, max_rows=None))
		lines.append("")

	if isinstance(comparisons_df, pd.DataFrame) and not comparisons_df.empty:
		lines.append("## Between-group comparisons (Δ vs baseline)")
		lines.append("")
		lines.append(_dataframe_to_markdown(comparisons_df, max_rows=None))
		lines.append("")

	if isinstance(mixed_effects_df, pd.DataFrame) and not mixed_effects_df.empty:
		lines.append("## Mixed-effects model (Group × Time)")
		lines.append("")
		lines.append(
			"Model: `delta ~ C(group) * C(timepoint_label) + (1 | user_id)` "
			"(random intercept per subject; T0 excluded)."
		)
		lines.append("")
		lines.append(_dataframe_to_markdown(mixed_effects_df, max_rows=None))
		lines.append("")

	if additional_notes.strip():
		lines.append("## Analyst Notes")
		lines.append("")
		lines.append(additional_notes.strip())
		lines.append("")

	lines.append("_End of report._")
	return "\n".join(lines)


def build_markdown_report(
	*,
	meta_rows: Sequence[Mapping[str, Any]],
	multi_results_df: pd.DataFrame,
	windowed_df: pd.DataFrame,
	episodes_df: pd.DataFrame,
	ml_summary_df: Optional[pd.DataFrame],
	space_weather_export: Optional[Mapping[str, Any]] = None,
	space_analytics_export: Optional[Mapping[str, Any]] = None,
	config: ExportConfiguration,
	selected_sources: Sequence[str],
	additional_notes: str = "",
) -> str:
	"""Build a markdown report describing the current HRV analysis session.

	Args:
		meta_rows: Sequence of per-file metadata dictionaries (beats, duration, etc.).
		multi_results_df: DataFrame with comprehensive metrics per dataset.
		windowed_df: DataFrame with windowed metrics.
		episodes_df: DataFrame with detected deviation episodes.
		ml_summary_df: DataFrame summarising ML-assisted clustering (may be None).
		space_analytics_export: Optional mapping containing Space Analytics correlation/ML outputs.
		config: ExportConfiguration describing scope and optional sections.
		selected_sources: Subset of dataset names to include (empty means all).
		additional_notes: Optional free-form notes from the user.

	Returns:
		A markdown string ready for download/export.

	Raises:
		ValueError: If no content is available to export.
	"""
	has_meta = len(meta_rows) > 0
	has_results = not multi_results_df.empty
	if not has_meta and not has_results:
		raise ValueError("No analysis results available to export.")

	lines: list[str] = []
	timestamp = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
	lines.append("# HRV Analysis Report")
	lines.append("")
	lines.append(f"- Generated: `{timestamp}`")
	lines.append(f"- Scope: `{config.scope.value}`")
	lines.append("")

	if has_meta:
		meta_df = pd.DataFrame(meta_rows)
		meta_df = _filter_sources(meta_df, selected_sources)
		if not meta_df.empty:
			lines.append("## Dataset Summary")
			lines.append("")
			lines.append(_dataframe_to_markdown(meta_df, max_rows=config.max_rows_summary if config.scope == ExportScope.SUMMARY else None))
			lines.append("")

	if has_results:
		results_df = multi_results_df.copy()
		results_df = _filter_sources(results_df, selected_sources)
		if not results_df.empty:
			lines.append("## Key Metrics")
			lines.append("")
			if config.scope == ExportScope.SUMMARY:
				priority_cols = [
					col for col in (
						"source",
						"sdnn",
						"rmssd",
						"lf_hf_ratio",
						"hf_power",
						"parasympathetic_index",
						"readiness_score",
					) if col in results_df.columns
				]
				if priority_cols:
					results_display = results_df[priority_cols]
				else:
					results_display = results_df
				lines.append(_dataframe_to_markdown(results_display, max_rows=config.max_rows_summary))
			else:
				lines.append(_dataframe_to_markdown(results_df, max_rows=None))
			lines.append("")

	if config.include_windowed and not windowed_df.empty:
		window_filtered = _filter_sources(windowed_df, selected_sources)
		if not window_filtered.empty:
			lines.append("## Windowed Metrics")
			lines.append("")
			if config.scope == ExportScope.SUMMARY:
				summary_candidates = [
					"start",
					"end",
					"source",
					"sdnn",
					"rmssd",
					"dev_index",
					"ml_cluster_name",
					"ml_cluster_score",
					"ml_flagged_high_deviation",
				]
				summary_columns = [col for col in summary_candidates if col in window_filtered.columns]
				window_slice = window_filtered[summary_columns] if summary_columns else window_filtered
				lines.append(_dataframe_to_markdown(window_slice, max_rows=config.max_rows_summary))
			else:
				lines.append(_dataframe_to_markdown(window_filtered, max_rows=None))
			lines.append("")

	if not episodes_df.empty:
		episodes_filtered = _filter_sources(episodes_df, selected_sources)
		if not episodes_filtered.empty:
			lines.append("## Deviation Episodes")
			lines.append("")
			lines.append(_dataframe_to_markdown(episodes_filtered, max_rows=config.max_rows_summary if config.scope == ExportScope.SUMMARY else None))
			lines.append("")

	if config.include_ml and ml_summary_df is not None and not ml_summary_df.empty:
		lines.append("## ML-Assisted Deviation Clusters")
		lines.append("")
		lines.append(_dataframe_to_markdown(ml_summary_df, max_rows=None if config.scope == ExportScope.COMPLETE else config.max_rows_summary))
		lines.append("")

	if space_weather_export:
		lines.append("## Space Weather Analysis (HRV ↔ Solar/Geomagnetic)")
		lines.append("")
		lines.append(
			"Robust stats: Pearson CI95, Spearman ρ, BH-FDR; HAC-robust p for autocorrelation; optional block bootstrap CI and permutation p for top findings."
		)
		lines.append(
			"ML: ElasticNet, Lasso, RandomForest, Gradient Boosting on lagged Kp/Dst/F10.7/solar wind with time-aware CV; permutation importances."
		)
		lines.append("")
		corr_best = space_weather_export.get("corr_best")
		corr_full = space_weather_export.get("corr_full")
		ml_metrics = space_weather_export.get("ml_metrics")
		ml_importances = space_weather_export.get("ml_importances")
		shap_importances = space_weather_export.get("shap_importances")
		if isinstance(corr_best, pd.DataFrame) and not corr_best.empty:
			lines.append("### Top correlations (by |r|)")
			lines.append(_dataframe_to_markdown(corr_best, max_rows=20))
			lines.append("")
		if config.scope == ExportScope.COMPLETE and isinstance(corr_full, pd.DataFrame) and not corr_full.empty:
			lines.append("### Full correlation table")
			lines.append(_dataframe_to_markdown(corr_full, max_rows=None))
			lines.append("")
		if isinstance(ml_metrics, pd.DataFrame) and not ml_metrics.empty:
			lines.append("### ML metrics (space-weather lag predictors)")
			lines.append(_dataframe_to_markdown(ml_metrics, max_rows=None))
			lines.append("")
		if isinstance(ml_importances, pd.DataFrame) and not ml_importances.empty:
			lines.append("### Feature importances (permutation, RandomForest)")
			lines.append(_dataframe_to_markdown(ml_importances, max_rows=30))
			lines.append("")
		if isinstance(shap_importances, pd.DataFrame) and not shap_importances.empty:
			lines.append("### Feature importances (SHAP)")
			lines.append("SHapley Additive exPlanations provide model-agnostic interpretability.")
			lines.append(_dataframe_to_markdown(shap_importances, max_rows=30))
			lines.append("")

	if space_analytics_export:
		corr_bundle = space_analytics_export.get("corr")
		ml_bundle = space_analytics_export.get("ml")
		corr_df = None
		ml_results = None
		corr_params = None
		ml_params = None
		if isinstance(corr_bundle, Mapping):
			corr_df = corr_bundle.get("results")
			corr_params = corr_bundle.get("params")
		if isinstance(ml_bundle, Mapping):
			ml_results = ml_bundle.get("results")
			ml_params = ml_bundle.get("params")
		has_corr = isinstance(corr_df, pd.DataFrame) and not corr_df.empty
		has_ml = isinstance(ml_results, Mapping) and bool(ml_results)
		if has_corr or has_ml:
			lines.append("## Space Analytics (NOAA predictors ↔ HRV/HRF)")
			lines.append("")
			lines.append(
				"Space Analytics is button-driven and uses cached NOAA/SWPC datasets plus windowed HRV/HRF metrics."
			)
			lines.append("")
			if isinstance(corr_params, Mapping) and corr_params:
				lines.append("### Correlation scan parameters")
				lines.append("")
				try:
					lines.append(
						"- Predictors: "
						+ ", ".join([str(x) for x in corr_params.get("predictors", [])])
					)
				except Exception:
					pass
				try:
					lines.append(
						"- Targets: "
						+ ", ".join([str(x) for x in corr_params.get("targets", [])])
					)
				except Exception:
					pass
				try:
					lines.append(
						"- Lags (hours): "
						+ ", ".join([str(x) for x in corr_params.get("lags", [])][:25])
						+ ("…" if len(corr_params.get("lags", [])) > 25 else "")
					)
				except Exception:
					pass
				if "merge_tol_minutes" in corr_params:
					lines.append(f"- Merge tolerance: {corr_params.get('merge_tol_minutes')} min")
				lines.append("")
			if has_corr:
				lines.append("### Top correlations (by |r|; BH-FDR q included when available)")
				lines.append("")
				view = corr_df.copy()
				if "abs_r" not in view.columns and "pearson_r" in view.columns:
					view["abs_r"] = view["pearson_r"].abs()
				if "abs_r" in view.columns:
					view = view.sort_values("abs_r", ascending=False)
				lines.append(_dataframe_to_markdown(view.head(30), max_rows=None))
				lines.append("")

			if isinstance(ml_params, Mapping) and ml_params:
				lines.append("### ML parameters")
				lines.append("")
				try:
					lines.append(
						"- Predictors: "
						+ ", ".join([str(x) for x in ml_params.get("predictors", [])])
					)
				except Exception:
					pass
				if "target" in ml_params:
					lines.append(f"- Target: {ml_params.get('target')}")
				if "gpu_enabled" in ml_params:
					lines.append(f"- GPU enabled: {ml_params.get('gpu_enabled')}")
				lines.append("")

			if has_ml:
				lines.append("### ML results (lagged NOAA predictors → HRV/HRF target)")
				lines.append("")
				try:
					samples = ml_results.get("samples")
					features = ml_results.get("features")
					if samples is not None or features is not None:
						lines.append(f"- Samples: {samples} | Features: {features}")
				except Exception:
					pass
				# Model scores table
				model_rows: list[dict[str, Any]] = []
				for model_key in ("elastic_net", "random_forest", "gradient_boosting", "lasso", "xgboost", "lightgbm"):
					model_val = ml_results.get(model_key)
					if isinstance(model_val, Mapping):
						row = {"model": model_key}
						for k in ("r2", "mae", "cv_r2_mean", "alpha", "l1_ratio"):
							if k in model_val:
								row[k] = model_val.get(k)
						model_rows.append(row)
				if model_rows:
					lines.append(_dataframe_to_markdown(pd.DataFrame(model_rows), max_rows=None))
					lines.append("")
				# Feature importances (top)
				feat_imp = ml_results.get("feature_importances")
				if isinstance(feat_imp, list) and feat_imp:
					try:
						lines.append("### Top feature importances (permutation; RandomForest)")
						lines.append("")
						lines.append(_dataframe_to_markdown(pd.DataFrame(feat_imp).head(25), max_rows=None))
						lines.append("")
					except Exception:
						pass
				shap_imp = ml_results.get("shap_importances")
				if isinstance(shap_imp, list) and shap_imp:
					try:
						lines.append("### Top feature importances (SHAP)")
						lines.append("")
						lines.append(_dataframe_to_markdown(pd.DataFrame(shap_imp).head(25), max_rows=None))
						lines.append("")
					except Exception:
						pass

	if additional_notes.strip():
		lines.append("## Analyst Notes")
		lines.append("")
		lines.append(additional_notes.strip())
		lines.append("")

	lines.append("_End of report._")
	return "\n".join(lines)

