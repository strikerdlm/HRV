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
    build_cohort_longitudinal_delta_long_df,
    build_cohort_longitudinal_markdown_report,
    compare_cohort_longitudinal_groups,
    compute_cohort_longitudinal_group_summary,
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


def test_cohort_longitudinal_delta_and_group_comparison_tables() -> None:
    # Construct minimal per-user timepoint summary tables (as produced by the DB helpers).
    def _tp_df(delta_t1: float) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "timepoint_label": "T0_baseline",
                    "rmssd_ms": 40.0,
                    "baseline_rmssd_ms": 40.0,
                    "delta_rmssd_ms": 0.0,
                },
                {
                    "timepoint_label": "T1",
                    "rmssd_ms": 40.0 + float(delta_t1),
                    "baseline_rmssd_ms": 40.0,
                    "delta_rmssd_ms": float(delta_t1),
                },
            ]
        )

    user_tables = {
        "c1": _tp_df(1.0),
        "c2": _tp_df(2.0),
        "c3": _tp_df(3.0),
        "i1": _tp_df(4.0),
        "i2": _tp_df(5.0),
        "i3": _tp_df(6.0),
    }
    user_groups = {
        "c1": "Control",
        "c2": "Control",
        "c3": "Control",
        "i1": "Intervention",
        "i2": "Intervention",
        "i3": "Intervention",
    }

    long_df = build_cohort_longitudinal_delta_long_df(
        user_timepoint_tables=user_tables,
        user_group_map=user_groups,
        metrics=["rmssd_ms"],
    )
    assert not long_df.empty
    assert set(["user_id", "group", "timepoint_label", "metric", "delta"]).issubset(long_df.columns)

    summary_df = compute_cohort_longitudinal_group_summary(long_df, agg="mean")
    assert not summary_df.empty
    t1_control = summary_df[
        (summary_df["group"] == "Control")
        & (summary_df["timepoint_label"] == "T1")
        & (summary_df["metric"] == "rmssd_ms")
    ].iloc[0]
    assert t1_control["n"] == 3
    assert abs(float(t1_control["mean_delta"]) - 2.0) < 1e-9

    comparisons_df = compare_cohort_longitudinal_groups(
        long_df,
        group_a="Control",
        group_b="Intervention",
        alpha=0.05,
        apply_fdr=True,
    )
    assert not comparisons_df.empty
    assert "p_adjusted" in comparisons_df.columns
    t1_row = comparisons_df[
        (comparisons_df["timepoint_label"] == "T1") & (comparisons_df["metric"] == "rmssd_ms")
    ].iloc[0]
    assert int(t1_row["group_a_n"]) == 3
    assert int(t1_row["group_b_n"]) == 3
    assert float(t1_row["group_a_mean_delta"]) < float(t1_row["group_b_mean_delta"])
    assert float(t1_row["effect_size_d"]) < 0.0  # control mean < intervention mean

    md = build_cohort_longitudinal_markdown_report(
        cohort_long_df=long_df,
        group_summary_df=summary_df,
        comparisons_df=comparisons_df,
        group_a="Control",
        group_b="Intervention",
        additional_notes="Protocol: same posture/time-of-day.",
    )
    assert "# Cohort Longitudinal Report" in md
    assert "## Between-group comparisons" in md

