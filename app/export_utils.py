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


def build_markdown_report(
	*,
	meta_rows: Sequence[Mapping[str, Any]],
	multi_results_df: pd.DataFrame,
	windowed_df: pd.DataFrame,
	episodes_df: pd.DataFrame,
	ml_summary_df: Optional[pd.DataFrame],
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
	timestamp = _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
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

	if additional_notes.strip():
		lines.append("## Analyst Notes")
		lines.append("")
		lines.append(additional_notes.strip())
		lines.append("")

	lines.append("_End of report._")
	return "\n".join(lines)

