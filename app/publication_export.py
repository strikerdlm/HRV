"""Publication-ready export utilities for HRV analysis.

This module provides functions to generate exports suitable for Q1 journal
submissions, including:
- Statistical summaries with proper formatting (mean ± SD, median [IQR])
- Effect size calculations (Cohen's d, Hedges' g)
- Correlation matrices with significance indicators
- Reproducibility metadata and methods sections
- Multiple export formats (CSV, JSON, LaTeX tables)

Design principles:
- Follow APA 7th edition formatting guidelines
- Include all necessary statistical details for peer review
- Provide reproducibility information (software versions, parameters)
- Support both summary and detailed exports

References:
- APA Publication Manual 7th Edition
- STROBE guidelines for observational studies
- CONSORT guidelines for reporting
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Final, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VERSION: Final[str] = "1.0.0"
_SOFTWARE_NAME: Final[str] = "HRV Analysis App"


class ExportFormat(str, Enum):
    """Supported export formats."""

    CSV = "csv"
    JSON = "json"
    LATEX = "latex"
    MARKDOWN = "markdown"


@dataclass(frozen=True, slots=True)
class PublicationConfig:
    """Configuration for publication-ready exports.

    Attributes:
        include_methods: Include methods section with parameters.
        include_statistics: Include detailed statistical summaries.
        include_reproducibility: Include software/version metadata.
        decimal_places: Number of decimal places for values.
        p_value_threshold: Significance threshold for marking.
        confidence_level: Confidence level for intervals (0.95 = 95%).
    """

    include_methods: bool = True
    include_statistics: bool = True
    include_reproducibility: bool = True
    decimal_places: int = 3
    p_value_threshold: float = 0.05
    confidence_level: float = 0.95


@dataclass(frozen=True, slots=True)
class StatisticalSummary:
    """Statistical summary for a single metric.

    Attributes:
        metric_name: Name of the metric.
        n: Sample size.
        mean: Arithmetic mean.
        std: Standard deviation.
        median: Median value.
        iqr_low: 25th percentile.
        iqr_high: 75th percentile.
        min_val: Minimum value.
        max_val: Maximum value.
        ci_low: Lower confidence interval bound.
        ci_high: Upper confidence interval bound.
        skewness: Skewness statistic.
        kurtosis: Kurtosis statistic.
        normality_p: Shapiro-Wilk normality test p-value.
    """

    metric_name: str
    n: int
    mean: float
    std: float
    median: float
    iqr_low: float
    iqr_high: float
    min_val: float
    max_val: float
    ci_low: float
    ci_high: float
    skewness: float
    kurtosis: float
    normality_p: float


@dataclass(frozen=True, slots=True)
class EffectSize:
    """Effect size calculation results.

    Attributes:
        cohens_d: Cohen's d effect size.
        hedges_g: Hedges' g (bias-corrected).
        interpretation: Verbal interpretation (small/medium/large).
        ci_low: Lower 95% CI for effect size.
        ci_high: Upper 95% CI for effect size.
    """

    cohens_d: float
    hedges_g: float
    interpretation: str
    ci_low: float
    ci_high: float


@dataclass(slots=True)
class CorrelationResult:
    """Correlation analysis result.

    Attributes:
        var1: First variable name.
        var2: Second variable name.
        r: Pearson correlation coefficient.
        p_value: Two-tailed p-value.
        n: Sample size.
        significant: Whether p < threshold.
    """

    var1: str
    var2: str
    r: float
    p_value: float
    n: int
    significant: bool


# ---------------------------------------------------------------------------
# Statistical computation functions
# ---------------------------------------------------------------------------


def compute_statistical_summary(
    values: np.ndarray | pd.Series,
    metric_name: str,
    *,
    confidence_level: float = 0.95,
) -> StatisticalSummary:
    """Compute comprehensive statistical summary for a metric.

    Args:
        values: Array of metric values.
        metric_name: Name of the metric.
        confidence_level: Confidence level for CI calculation.

    Returns:
        StatisticalSummary with all statistics.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]

    n = len(arr)
    if n < 3:
        return StatisticalSummary(
            metric_name=metric_name,
            n=n,
            mean=float(np.mean(arr)) if n > 0 else 0.0,
            std=float(np.std(arr, ddof=1)) if n > 1 else 0.0,
            median=float(np.median(arr)) if n > 0 else 0.0,
            iqr_low=float(np.percentile(arr, 25)) if n > 0 else 0.0,
            iqr_high=float(np.percentile(arr, 75)) if n > 0 else 0.0,
            min_val=float(np.min(arr)) if n > 0 else 0.0,
            max_val=float(np.max(arr)) if n > 0 else 0.0,
            ci_low=0.0,
            ci_high=0.0,
            skewness=0.0,
            kurtosis=0.0,
            normality_p=1.0,
        )

    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr, ddof=1))
    median_val = float(np.median(arr))
    q25 = float(np.percentile(arr, 25))
    q75 = float(np.percentile(arr, 75))
    min_v = float(np.min(arr))
    max_v = float(np.max(arr))

    # Confidence interval for mean
    sem = std_val / np.sqrt(n)
    t_crit = float(stats.t.ppf((1 + confidence_level) / 2, n - 1))
    ci_low = mean_val - t_crit * sem
    ci_high = mean_val + t_crit * sem

    # Skewness and kurtosis
    skew = float(stats.skew(arr, bias=False)) if n >= 8 else 0.0
    kurt = float(stats.kurtosis(arr, bias=False)) if n >= 8 else 0.0

    # Normality test (Shapiro-Wilk, max 5000 samples)
    if 3 <= n <= 5000:
        _, norm_p = stats.shapiro(arr[:5000])
        norm_p = float(norm_p)
    else:
        norm_p = 1.0

    return StatisticalSummary(
        metric_name=metric_name,
        n=n,
        mean=mean_val,
        std=std_val,
        median=median_val,
        iqr_low=q25,
        iqr_high=q75,
        min_val=min_v,
        max_val=max_v,
        ci_low=ci_low,
        ci_high=ci_high,
        skewness=skew,
        kurtosis=kurt,
        normality_p=norm_p,
    )


def compute_effect_size(
    group1: np.ndarray | pd.Series,
    group2: np.ndarray | pd.Series,
) -> EffectSize:
    """Compute Cohen's d and Hedges' g effect sizes.

    Args:
        group1: First group values.
        group2: Second group values.

    Returns:
        EffectSize with Cohen's d, Hedges' g, and interpretation.
    """
    arr1 = np.asarray(group1, dtype=float)
    arr2 = np.asarray(group2, dtype=float)
    arr1 = arr1[np.isfinite(arr1)]
    arr2 = arr2[np.isfinite(arr2)]

    n1, n2 = len(arr1), len(arr2)
    if n1 < 2 or n2 < 2:
        return EffectSize(
            cohens_d=0.0,
            hedges_g=0.0,
            interpretation="insufficient data",
            ci_low=0.0,
            ci_high=0.0,
        )

    m1, m2 = float(np.mean(arr1)), float(np.mean(arr2))
    s1, s2 = float(np.std(arr1, ddof=1)), float(np.std(arr2, ddof=1))

    # Pooled standard deviation
    s_pooled = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
    if s_pooled < 1e-9:
        return EffectSize(
            cohens_d=0.0,
            hedges_g=0.0,
            interpretation="no variance",
            ci_low=0.0,
            ci_high=0.0,
        )

    # Cohen's d
    d = (m1 - m2) / s_pooled

    # Hedges' g (bias correction)
    df = n1 + n2 - 2
    correction = 1 - (3 / (4 * df - 1))
    g = d * correction

    # Interpretation (Cohen's conventions)
    abs_d = abs(d)
    if abs_d < 0.2:
        interp = "negligible"
    elif abs_d < 0.5:
        interp = "small"
    elif abs_d < 0.8:
        interp = "medium"
    else:
        interp = "large"

    # Approximate 95% CI for d
    se_d = np.sqrt((n1 + n2) / (n1 * n2) + d**2 / (2 * (n1 + n2)))
    ci_low = d - 1.96 * se_d
    ci_high = d + 1.96 * se_d

    return EffectSize(
        cohens_d=d,
        hedges_g=g,
        interpretation=interp,
        ci_low=ci_low,
        ci_high=ci_high,
    )


def compute_correlation_matrix(
    df: pd.DataFrame,
    columns: list[str],
    *,
    p_threshold: float = 0.05,
) -> tuple[pd.DataFrame, list[CorrelationResult]]:
    """Compute correlation matrix with p-values.

    Args:
        df: DataFrame with metric columns.
        columns: List of column names to correlate.
        p_threshold: Significance threshold.

    Returns:
        Tuple of (correlation matrix DataFrame, list of CorrelationResult).
    """
    valid_cols = [c for c in columns if c in df.columns]
    if len(valid_cols) < 2:
        return pd.DataFrame(), []

    subset = df[valid_cols].dropna()
    n = len(subset)
    if n < 3:
        return pd.DataFrame(), []

    # Compute correlation matrix
    corr_matrix = subset.corr(method="pearson")

    # Compute p-values for each pair
    results: list[CorrelationResult] = []
    for i, col1 in enumerate(valid_cols):
        for j, col2 in enumerate(valid_cols):
            if i >= j:
                continue
            arr1 = subset[col1].values
            arr2 = subset[col2].values
            r, p = stats.pearsonr(arr1, arr2)
            results.append(
                CorrelationResult(
                    var1=col1,
                    var2=col2,
                    r=float(r),
                    p_value=float(p),
                    n=n,
                    significant=p < p_threshold,
                )
            )

    return corr_matrix, results


# ---------------------------------------------------------------------------
# Formatting functions
# ---------------------------------------------------------------------------


def format_mean_sd(
    mean: float,
    std: float,
    *,
    decimals: int = 2,
) -> str:
    """Format as 'mean ± SD' (APA style).

    Args:
        mean: Mean value.
        std: Standard deviation.
        decimals: Number of decimal places.

    Returns:
        Formatted string like '42.5 ± 15.3'.
    """
    return f"{mean:.{decimals}f} ± {std:.{decimals}f}"


def format_median_iqr(
    median: float,
    q25: float,
    q75: float,
    *,
    decimals: int = 2,
) -> str:
    """Format as 'median [Q1, Q3]' (APA style).

    Args:
        median: Median value.
        q25: 25th percentile.
        q75: 75th percentile.
        decimals: Number of decimal places.

    Returns:
        Formatted string like '40.0 [25.0, 55.0]'.
    """
    return f"{median:.{decimals}f} [{q25:.{decimals}f}, {q75:.{decimals}f}]"


def format_p_value(p: float) -> str:
    """Format p-value according to APA guidelines.

    Args:
        p: P-value.

    Returns:
        Formatted string like 'p < .001' or 'p = .045'.
    """
    if p < 0.001:
        return "p < .001"
    if p < 0.01:
        return f"p = {p:.3f}"
    return f"p = {p:.2f}"


def format_ci(
    low: float,
    high: float,
    *,
    decimals: int = 2,
    level: int = 95,
) -> str:
    """Format confidence interval.

    Args:
        low: Lower bound.
        high: Upper bound.
        decimals: Number of decimal places.
        level: Confidence level percentage.

    Returns:
        Formatted string like '95% CI [35.2, 49.8]'.
    """
    return f"{level}% CI [{low:.{decimals}f}, {high:.{decimals}f}]"


def format_effect_size(effect: EffectSize, *, decimals: int = 2) -> str:
    """Format effect size with interpretation.

    Args:
        effect: EffectSize object.
        decimals: Number of decimal places.

    Returns:
        Formatted string like "d = 0.75 ({interpretation})".
    """
    return f"d = {effect.cohens_d:.{decimals}f} ({effect.interpretation})"


# ---------------------------------------------------------------------------
# Export generation functions
# ---------------------------------------------------------------------------


def generate_methods_section(
    *,
    n_datasets: int,
    total_beats: int,
    analysis_params: dict[str, Any],
) -> str:
    """Generate a methods section for publication.

    Args:
        n_datasets: Number of datasets analyzed.
        total_beats: Total number of RR intervals.
        analysis_params: Dictionary of analysis parameters.

    Returns:
        Markdown-formatted methods section.
    """
    lines = [
        "## Methods",
        "",
        "### Data Acquisition",
        f"Heart rate variability was analyzed from {n_datasets} dataset(s) "
        f"comprising {total_beats:,} RR intervals. "
        "RR intervals were extracted from Polar-format text files with values "
        "constrained to physiological bounds (300–2000 ms).",
        "",
        "### Signal Processing",
    ]

    qc_method = analysis_params.get("qc_method", "threshold_median")
    max_dev = analysis_params.get("max_deviation", 0.2)
    lines.append(
        f"Artifact detection used the '{qc_method}' method with a maximum "
        f"deviation threshold of {max_dev:.0%}. Flagged beats were replaced "
        "by linear interpolation."
    )

    psd_method = analysis_params.get("psd_method", "welch")
    sampling_rate = analysis_params.get("sampling_rate", 4.0)
    lines.append(
        f"\nPower spectral density was estimated using the {psd_method.title()} "
        f"method with cubic interpolation at {sampling_rate} Hz. "
        "Frequency bands were defined as VLF (0.0033–0.04 Hz), "
        "LF (0.04–0.15 Hz), and HF (0.15–0.40 Hz) per Task Force guidelines."
    )

    lines.extend([
        "",
        "### Statistical Analysis",
        "Time-domain metrics (SDNN, RMSSD, pNN50) and frequency-domain metrics "
        "(LF, HF, LF/HF ratio) were computed following ESC/NASPE Task Force "
        "recommendations (1996). Nonlinear metrics included Poincaré plot "
        "descriptors (SD1, SD2) and detrended fluctuation analysis (DFA α1, α2).",
        "",
        "Entropy metrics (Sample Entropy, Approximate Entropy) used embedding "
        "dimension m=2 and tolerance r=0.2×SD. Heart rate fragmentation metrics "
        "(PIP, IALS) were computed per Costa et al. (2017).",
        "",
    ])

    return "\n".join(lines)


def generate_reproducibility_metadata(
    *,
    analysis_params: dict[str, Any],
    data_hash: str | None = None,
) -> dict[str, Any]:
    """Generate reproducibility metadata.

    Args:
        analysis_params: Dictionary of analysis parameters.
        data_hash: Optional hash of input data for verification.

    Returns:
        Dictionary with reproducibility information.
    """
    return {
        "software": {
            "name": _SOFTWARE_NAME,
            "version": _VERSION,
            "python_version": sys.version.split()[0],
        },
        "timestamp": _dt.datetime.utcnow().isoformat() + "Z",
        "parameters": analysis_params,
        "data_hash": data_hash,
    }


def generate_statistical_table(
    df: pd.DataFrame,
    metrics: list[str],
    *,
    config: PublicationConfig,
) -> pd.DataFrame:
    """Generate publication-ready statistical summary table.

    Args:
        df: DataFrame with metric values.
        metrics: List of metric column names.
        config: Publication configuration.

    Returns:
        DataFrame with formatted statistics.
    """
    rows: list[dict[str, Any]] = []
    dec = config.decimal_places

    for metric in metrics:
        if metric not in df.columns:
            continue

        values = df[metric].dropna()
        if len(values) < 2:
            continue

        summary = compute_statistical_summary(
            values,
            metric,
            confidence_level=config.confidence_level,
        )

        row = {
            "Metric": metric.replace("_", " ").title(),
            "N": summary.n,
            "Mean ± SD": format_mean_sd(summary.mean, summary.std, decimals=dec),
            "Median [IQR]": format_median_iqr(
                summary.median, summary.iqr_low, summary.iqr_high, decimals=dec
            ),
            "Range": f"{summary.min_val:.{dec}f}–{summary.max_val:.{dec}f}",
            f"{int(config.confidence_level * 100)}% CI": format_ci(
                summary.ci_low, summary.ci_high, decimals=dec,
                level=int(config.confidence_level * 100)
            ),
        }

        if config.include_statistics:
            row["Skewness"] = f"{summary.skewness:.{dec}f}"
            row["Kurtosis"] = f"{summary.kurtosis:.{dec}f}"
            row["Normality (p)"] = format_p_value(summary.normality_p)

        rows.append(row)

    return pd.DataFrame(rows)


def generate_latex_table(
    stat_df: pd.DataFrame,
    *,
    caption: str = "HRV Metrics Summary",
    label: str = "tab:hrv_summary",
) -> str:
    """Generate LaTeX table from statistical summary.

    Args:
        stat_df: DataFrame from generate_statistical_table.
        caption: Table caption.
        label: LaTeX label for referencing.

    Returns:
        LaTeX table code.
    """
    if stat_df.empty:
        return "% No data available for table"

    n_cols = len(stat_df.columns)
    col_format = "l" + "c" * (n_cols - 1)

    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{col_format}}}",
        r"\toprule",
    ]

    # Header
    header = " & ".join(stat_df.columns)
    lines.append(f"{header} \\\\")
    lines.append(r"\midrule")

    # Data rows
    for _, row in stat_df.iterrows():
        values = [str(v) for v in row.values]
        lines.append(" & ".join(values) + " \\\\")

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    return "\n".join(lines)


def export_to_json(
    *,
    meta_rows: Sequence[Mapping[str, Any]],
    metrics_df: pd.DataFrame,
    windowed_df: pd.DataFrame,
    config: PublicationConfig,
    analysis_params: dict[str, Any],
) -> str:
    """Export analysis results to JSON format.

    Args:
        meta_rows: Dataset metadata.
        metrics_df: Comprehensive metrics DataFrame.
        windowed_df: Windowed metrics DataFrame.
        config: Publication configuration.
        analysis_params: Analysis parameters.

    Returns:
        JSON string with all results.
    """
    # Compute data hash for reproducibility
    combined = metrics_df.to_json() + windowed_df.to_json()
    data_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]

    output: dict[str, Any] = {
        "metadata": generate_reproducibility_metadata(
            analysis_params=analysis_params,
            data_hash=data_hash,
        ),
        "datasets": list(meta_rows),
    }

    if not metrics_df.empty:
        output["metrics"] = metrics_df.to_dict(orient="records")

    if not windowed_df.empty and config.include_statistics:
        output["windowed_metrics"] = windowed_df.to_dict(orient="records")

    return json.dumps(output, indent=2, default=str)


def build_publication_report(
    *,
    meta_rows: Sequence[Mapping[str, Any]],
    metrics_df: pd.DataFrame,
    windowed_df: pd.DataFrame,
    config: PublicationConfig,
    analysis_params: dict[str, Any],
    additional_notes: str = "",
) -> str:
    """Build comprehensive publication-ready markdown report.

    Args:
        meta_rows: Dataset metadata.
        metrics_df: Comprehensive metrics DataFrame.
        windowed_df: Windowed metrics DataFrame.
        config: Publication configuration.
        analysis_params: Analysis parameters.
        additional_notes: Optional analyst notes.

    Returns:
        Markdown string suitable for publication supplementary materials.
    """
    lines: list[str] = []
    timestamp = _dt.datetime.utcnow().isoformat() + "Z"

    # Title and metadata
    lines.extend([
        "# Heart Rate Variability Analysis Report",
        "",
        f"**Generated:** {timestamp}",
        f"**Software:** {_SOFTWARE_NAME} v{_VERSION}",
        "",
    ])

    # Methods section
    if config.include_methods:
        total_beats = sum(m.get("n_intervals", 0) for m in meta_rows)
        methods = generate_methods_section(
            n_datasets=len(meta_rows),
            total_beats=total_beats,
            analysis_params=analysis_params,
        )
        lines.append(methods)

    # Results section
    lines.extend(["## Results", ""])

    # Statistical summary table
    if not metrics_df.empty:
        priority_metrics = [
            "sdnn", "rmssd", "pnn50", "mean_hr",
            "lf_power", "hf_power", "lf_hf_ratio",
            "sd1", "sd2", "dfa_alpha1",
            "sample_entropy", "stress_index",
            "parasympathetic_index",
        ]
        available_metrics = [m for m in priority_metrics if m in metrics_df.columns]

        if available_metrics:
            stat_table = generate_statistical_table(
                metrics_df, available_metrics, config=config
            )
            lines.extend([
                "### Descriptive Statistics",
                "",
                stat_table.to_markdown(index=False),
                "",
            ])

    # Correlation matrix
    if not metrics_df.empty and config.include_statistics:
        corr_cols = ["sdnn", "rmssd", "hf_power", "lf_hf_ratio", "sd1"]
        corr_cols = [c for c in corr_cols if c in metrics_df.columns]
        if len(corr_cols) >= 2:
            corr_matrix, corr_results = compute_correlation_matrix(
                metrics_df, corr_cols, p_threshold=config.p_value_threshold
            )
            if not corr_matrix.empty:
                lines.extend([
                    "### Correlation Matrix",
                    "",
                    corr_matrix.round(config.decimal_places).to_markdown(),
                    "",
                ])

                # Significant correlations
                sig_corrs = [r for r in corr_results if r.significant]
                if sig_corrs:
                    lines.append("**Significant correlations:**")
                    for r in sig_corrs:
                        lines.append(
                            f"- {r.var1} × {r.var2}: r = {r.r:.3f}, {format_p_value(r.p_value)}"
                        )
                    lines.append("")

    # Reproducibility section
    if config.include_reproducibility:
        lines.extend([
            "## Reproducibility Information",
            "",
            "### Analysis Parameters",
            "",
            "```json",
            json.dumps(analysis_params, indent=2, default=str),
            "```",
            "",
        ])

    # Notes
    if additional_notes.strip():
        lines.extend([
            "## Analyst Notes",
            "",
            additional_notes.strip(),
            "",
        ])

    # References
    lines.extend([
        "## References",
        "",
        "- Task Force of the ESC/NASPE (1996). Heart rate variability: "
        "Standards of measurement, physiological interpretation and clinical use. "
        "European Heart Journal, 17(3), 354–381.",
        "",
        "- Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate "
        "variability metrics and norms. Frontiers in Public Health, 5, 258.",
        "",
        "- Costa, M. D., et al. (2017). Heart rate fragmentation: A new approach "
        "to the analysis of cardiac interbeat interval dynamics. Frontiers in "
        "Physiology, 8, 255.",
        "",
        "_End of report._",
    ])

    return "\n".join(lines)

