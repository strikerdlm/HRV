"""Tests for cohort (group) export utilities."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.export_utils import (  # pylint: disable=wrong-import-position
    CohortExportConfiguration,
    ExportScope,
    build_cohort_markdown_report,
    compute_cohort_summary_stats,
)


def test_compute_cohort_summary_stats_skips_missing_columns() -> None:
    df = pd.DataFrame(
        [
            {"user_id": "u1", "rmssd_ms": 40.0, "sdnn_ms": 50.0},
            {"user_id": "u2", "rmssd_ms": 30.0, "sdnn_ms": 60.0},
        ]
    )
    stats = compute_cohort_summary_stats(
        df,
        numeric_columns=["rmssd_ms", "sdnn_ms", "hf_power_ms2"],  # hf_power_ms2 absent
    )
    assert "metric" in stats.columns
    assert set(stats["metric"].tolist()) == {"rmssd_ms", "sdnn_ms"}


def test_compute_cohort_summary_stats_basic_numbers() -> None:
    df = pd.DataFrame(
        [
            {"rmssd_ms": 40.0, "sdnn_ms": 50.0},
            {"rmssd_ms": 30.0, "sdnn_ms": 60.0},
            {"rmssd_ms": 50.0, "sdnn_ms": 40.0},
        ]
    )
    stats = compute_cohort_summary_stats(
        df,
        numeric_columns=["rmssd_ms", "sdnn_ms"],
    )
    rmssd = stats[stats["metric"] == "rmssd_ms"].iloc[0].to_dict()
    assert rmssd["n"] == 3
    assert rmssd["min"] == 30.0
    assert rmssd["max"] == 50.0


def test_build_cohort_markdown_report_contains_sections() -> None:
    cohort_df = pd.DataFrame(
        [
            {"user_id": "u1", "full_name": "A", "rmssd_ms": 40.0},
            {"user_id": "u2", "full_name": "B", "rmssd_ms": 30.0},
        ]
    )
    stats_df = compute_cohort_summary_stats(
        cohort_df,
        numeric_columns=["rmssd_ms"],
    )
    md = build_cohort_markdown_report(
        cohort_df=cohort_df,
        cohort_stats_df=stats_df,
        config=CohortExportConfiguration(scope=ExportScope.SUMMARY, max_rows_individual=25),
        additional_notes="Protocol: supine, 5 min.",
    )
    assert "# Cohort Summary Report" in md
    assert "## Cohort roster" in md
    assert "## Cohort descriptive statistics" in md
    assert "## Analyst Notes" in md

