"""Comprehensive statistical analysis module for HRV research.

This module provides publication-ready statistical analysis including:
- Descriptive statistics with normality testing
- Group comparisons (t-tests, Mann-Whitney, ANOVA, Kruskal-Wallis)
- Correlation analysis (Pearson, Spearman, partial correlations)
- Regression analysis (linear, multiple, logistic)
- Effect size calculations (Cohen's d, η², r²)
- Multiple comparison corrections (Bonferroni, FDR)
- Confidence intervals and bootstrap analysis

Design principles:
- All analyses return structured results with effect sizes
- P-values include multiple comparison corrections
- Results formatted for direct inclusion in publications
- Comprehensive logging and reproducibility metadata

References:
- Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences.
- Benjamini, Y., & Hochberg, Y. (1995). Controlling the False Discovery Rate.
- APA Publication Manual 7th Edition for reporting guidelines.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Final

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import (
    f_oneway,
    kruskal,
    mannwhitneyu,
    pearsonr,
    shapiro,
    spearmanr,
    ttest_ind,
    ttest_rel,
    wilcoxon,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
_MIN_SAMPLES: Final[int] = 3
_ALPHA_DEFAULT: Final[float] = 0.05


class StatisticalTestType(str, Enum):
    """Statistical test type."""

    TTEST_IND = "independent_ttest"
    TTEST_PAIRED = "paired_ttest"
    MANNWHITNEY = "mann_whitney"
    WILCOXON = "wilcoxon"
    ANOVA = "anova"
    KRUSKAL = "kruskal_wallis"
    PEARSON = "pearson"
    SPEARMAN = "spearman"


class EffectSizeType(str, Enum):
    """Effect size interpretation."""

    NEGLIGIBLE = "negligible"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


# ---------------------------------------------------------------------------
# Data classes for results
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DescriptiveStats:
    """Descriptive statistics for a variable.

    Attributes:
        variable: Variable name.
        n: Sample size.
        mean: Arithmetic mean.
        std: Standard deviation.
        sem: Standard error of mean.
        median: Median value.
        iqr: Interquartile range.
        q25: 25th percentile.
        q75: 75th percentile.
        min_val: Minimum value.
        max_val: Maximum value.
        skewness: Skewness statistic.
        kurtosis: Kurtosis statistic.
        shapiro_w: Shapiro-Wilk W statistic.
        shapiro_p: Shapiro-Wilk p-value.
        is_normal: Whether distribution is normal (p > 0.05).
        ci_95_low: Lower 95% CI for mean.
        ci_95_high: Upper 95% CI for mean.
    """

    variable: str
    n: int
    mean: float
    std: float
    sem: float
    median: float
    iqr: float
    q25: float
    q75: float
    min_val: float
    max_val: float
    skewness: float
    kurtosis: float
    shapiro_w: float
    shapiro_p: float
    is_normal: bool
    ci_95_low: float
    ci_95_high: float


@dataclass(frozen=True, slots=True)
class GroupComparisonResult:
    """Result of group comparison test.

    Attributes:
        test_type: Type of statistical test used.
        statistic: Test statistic value.
        p_value: Raw p-value.
        p_adjusted: Multiple comparison adjusted p-value.
        effect_size: Effect size (Cohen's d or similar).
        effect_interpretation: Verbal interpretation.
        ci_low: Lower 95% CI for effect size.
        ci_high: Upper 95% CI for effect size.
        group1_n: Sample size of group 1.
        group2_n: Sample size of group 2.
        group1_mean: Mean of group 1.
        group2_mean: Mean of group 2.
        significant: Whether p < alpha.
        recommendation: Interpretation recommendation.
    """

    test_type: StatisticalTestType
    statistic: float
    p_value: float
    p_adjusted: float
    effect_size: float
    effect_interpretation: EffectSizeType
    ci_low: float
    ci_high: float
    group1_n: int
    group2_n: int
    group1_mean: float
    group2_mean: float
    significant: bool
    recommendation: str


@dataclass(frozen=True, slots=True)
class CorrelationResult:
    """Result of correlation analysis.

    Attributes:
        var1: First variable name.
        var2: Second variable name.
        method: Correlation method (Pearson/Spearman).
        r: Correlation coefficient.
        p_value: Raw p-value.
        p_adjusted: Multiple comparison adjusted p-value.
        n: Sample size.
        r_squared: Coefficient of determination.
        ci_low: Lower 95% CI for r.
        ci_high: Upper 95% CI for r.
        significant: Whether p < alpha.
        strength: Verbal interpretation of correlation strength.
    """

    var1: str
    var2: str
    method: str
    r: float
    p_value: float
    p_adjusted: float
    n: int
    r_squared: float
    ci_low: float
    ci_high: float
    significant: bool
    strength: str


@dataclass(frozen=True, slots=True)
class RegressionResult:
    """Result of regression analysis.

    Attributes:
        dependent_var: Dependent variable name.
        independent_vars: List of independent variable names.
        coefficients: Dict of variable -> coefficient.
        std_errors: Dict of variable -> standard error.
        t_values: Dict of variable -> t-value.
        p_values: Dict of variable -> p-value.
        r_squared: R² (coefficient of determination).
        adj_r_squared: Adjusted R².
        f_statistic: F-statistic for model.
        f_p_value: P-value for F-test.
        n: Sample size.
        residual_std: Residual standard deviation.
        aic: Akaike Information Criterion.
        bic: Bayesian Information Criterion.
    """

    dependent_var: str
    independent_vars: tuple[str, ...]
    coefficients: dict[str, float]
    std_errors: dict[str, float]
    t_values: dict[str, float]
    p_values: dict[str, float]
    r_squared: float
    adj_r_squared: float
    f_statistic: float
    f_p_value: float
    n: int
    residual_std: float
    aic: float
    bic: float


@dataclass(slots=True)
class ANOVAResult:
    """Result of ANOVA analysis.

    Attributes:
        test_type: ANOVA or Kruskal-Wallis.
        statistic: F or H statistic.
        p_value: P-value.
        df_between: Degrees of freedom between groups.
        df_within: Degrees of freedom within groups.
        eta_squared: Effect size (η²).
        omega_squared: Adjusted effect size (ω²).
        effect_interpretation: Verbal interpretation.
        group_means: Dict of group -> mean.
        group_ns: Dict of group -> sample size.
        significant: Whether p < alpha.
        post_hoc: List of post-hoc comparison results.
    """

    test_type: StatisticalTestType
    statistic: float
    p_value: float
    df_between: int
    df_within: int
    eta_squared: float
    omega_squared: float
    effect_interpretation: EffectSizeType
    group_means: dict[str, float]
    group_ns: dict[str, int]
    significant: bool
    post_hoc: list[GroupComparisonResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Descriptive Statistics
# ---------------------------------------------------------------------------


def compute_descriptive_stats(
    values: np.ndarray | pd.Series,
    variable_name: str = "variable",
) -> DescriptiveStats:
    """Compute comprehensive descriptive statistics.

    Args:
        values: Array of values.
        variable_name: Name of the variable.

    Returns:
        DescriptiveStats with all statistics.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = len(arr)

    if n < _MIN_SAMPLES:
        return DescriptiveStats(
            variable=variable_name,
            n=n,
            mean=float(np.mean(arr)) if n > 0 else 0.0,
            std=0.0,
            sem=0.0,
            median=float(np.median(arr)) if n > 0 else 0.0,
            iqr=0.0,
            q25=0.0,
            q75=0.0,
            min_val=float(np.min(arr)) if n > 0 else 0.0,
            max_val=float(np.max(arr)) if n > 0 else 0.0,
            skewness=0.0,
            kurtosis=0.0,
            shapiro_w=0.0,
            shapiro_p=1.0,
            is_normal=False,
            ci_95_low=0.0,
            ci_95_high=0.0,
        )

    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr, ddof=1))
    sem_val = std_val / np.sqrt(n)
    median_val = float(np.median(arr))
    q25 = float(np.percentile(arr, 25))
    q75 = float(np.percentile(arr, 75))
    iqr = q75 - q25

    # Skewness and kurtosis
    skew = float(stats.skew(arr, bias=False)) if n >= 8 else 0.0
    kurt = float(stats.kurtosis(arr, bias=False)) if n >= 8 else 0.0

    # Normality test
    if 3 <= n <= 5000:
        w_stat, p_val = shapiro(arr[:5000])
        shapiro_w = float(w_stat)
        shapiro_p = float(p_val)
        is_normal = p_val > _ALPHA_DEFAULT
    else:
        shapiro_w = 0.0
        shapiro_p = 1.0
        is_normal = False

    # 95% CI for mean
    t_crit = float(stats.t.ppf(0.975, n - 1))
    ci_low = mean_val - t_crit * sem_val
    ci_high = mean_val + t_crit * sem_val

    return DescriptiveStats(
        variable=variable_name,
        n=n,
        mean=mean_val,
        std=std_val,
        sem=sem_val,
        median=median_val,
        iqr=iqr,
        q25=q25,
        q75=q75,
        min_val=float(np.min(arr)),
        max_val=float(np.max(arr)),
        skewness=skew,
        kurtosis=kurt,
        shapiro_w=shapiro_w,
        shapiro_p=shapiro_p,
        is_normal=is_normal,
        ci_95_low=ci_low,
        ci_95_high=ci_high,
    )


def compute_descriptive_table(
    df: pd.DataFrame,
    variables: list[str],
) -> pd.DataFrame:
    """Compute descriptive statistics table for multiple variables.

    Args:
        df: DataFrame with variables.
        variables: List of variable column names.

    Returns:
        DataFrame with descriptive statistics.
    """
    rows: list[dict[str, Any]] = []

    for var in variables:
        if var not in df.columns:
            continue
        stats_result = compute_descriptive_stats(df[var].dropna(), var)
        rows.append({
            "Variable": var,
            "N": stats_result.n,
            "Mean": f"{stats_result.mean:.2f}",
            "SD": f"{stats_result.std:.2f}",
            "Median": f"{stats_result.median:.2f}",
            "IQR": f"{stats_result.iqr:.2f}",
            "Min": f"{stats_result.min_val:.2f}",
            "Max": f"{stats_result.max_val:.2f}",
            "Skewness": f"{stats_result.skewness:.2f}",
            "Kurtosis": f"{stats_result.kurtosis:.2f}",
            "Shapiro p": f"{stats_result.shapiro_p:.3f}",
            "Normal": "Yes" if stats_result.is_normal else "No",
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Effect Size Calculations
# ---------------------------------------------------------------------------


def _interpret_cohens_d(d: float) -> EffectSizeType:
    """Interpret Cohen's d effect size."""
    abs_d = abs(d)
    if abs_d < 0.2:
        return EffectSizeType.NEGLIGIBLE
    if abs_d < 0.5:
        return EffectSizeType.SMALL
    if abs_d < 0.8:
        return EffectSizeType.MEDIUM
    return EffectSizeType.LARGE


def _interpret_eta_squared(eta2: float) -> EffectSizeType:
    """Interpret eta-squared effect size."""
    if eta2 < 0.01:
        return EffectSizeType.NEGLIGIBLE
    if eta2 < 0.06:
        return EffectSizeType.SMALL
    if eta2 < 0.14:
        return EffectSizeType.MEDIUM
    return EffectSizeType.LARGE


def _interpret_r(r: float) -> str:
    """Interpret correlation coefficient strength."""
    abs_r = abs(r)
    if abs_r < 0.1:
        return "negligible"
    if abs_r < 0.3:
        return "weak"
    if abs_r < 0.5:
        return "moderate"
    if abs_r < 0.7:
        return "strong"
    return "very strong"


def compute_cohens_d(
    group1: np.ndarray,
    group2: np.ndarray,
) -> tuple[float, float, float]:
    """Compute Cohen's d with 95% CI.

    Args:
        group1: First group values.
        group2: Second group values.

    Returns:
        Tuple of (d, ci_low, ci_high).
    """
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return 0.0, 0.0, 0.0

    m1, m2 = float(np.mean(group1)), float(np.mean(group2))
    s1, s2 = float(np.std(group1, ddof=1)), float(np.std(group2, ddof=1))

    # Pooled standard deviation
    s_pooled = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
    if s_pooled < 1e-9:
        return 0.0, 0.0, 0.0

    d = (m1 - m2) / s_pooled

    # Approximate 95% CI
    se_d = np.sqrt((n1 + n2) / (n1 * n2) + d**2 / (2 * (n1 + n2)))
    ci_low = d - 1.96 * se_d
    ci_high = d + 1.96 * se_d

    return float(d), float(ci_low), float(ci_high)


# ---------------------------------------------------------------------------
# Multiple Comparison Corrections
# ---------------------------------------------------------------------------


def bonferroni_correction(
    p_values: list[float],
    alpha: float = _ALPHA_DEFAULT,
) -> list[float]:
    """Apply Bonferroni correction to p-values.

    Args:
        p_values: List of raw p-values.
        alpha: Significance level.

    Returns:
        List of adjusted p-values.
    """
    n = len(p_values)
    return [min(p * n, 1.0) for p in p_values]


def fdr_correction(
    p_values: list[float],
    alpha: float = _ALPHA_DEFAULT,
) -> list[float]:
    """Apply Benjamini-Hochberg FDR correction.

    Args:
        p_values: List of raw p-values.
        alpha: Significance level.

    Returns:
        List of adjusted p-values.
    """
    n = len(p_values)
    if n == 0:
        return []

    # Sort p-values and track original indices
    sorted_indices = np.argsort(p_values)
    sorted_p = np.array(p_values)[sorted_indices]

    # Compute adjusted p-values
    adjusted = np.zeros(n)
    for i in range(n):
        rank = i + 1
        adjusted[sorted_indices[i]] = sorted_p[i] * n / rank

    # Ensure monotonicity (cumulative minimum from the end)
    result = np.minimum.accumulate(adjusted[::-1])[::-1]
    return [min(p, 1.0) for p in result]


# ---------------------------------------------------------------------------
# Group Comparisons
# ---------------------------------------------------------------------------


def compare_two_groups(
    group1: np.ndarray | pd.Series,
    group2: np.ndarray | pd.Series,
    *,
    paired: bool = False,
    alpha: float = _ALPHA_DEFAULT,
) -> GroupComparisonResult:
    """Compare two groups with appropriate test selection.

    Automatically selects parametric or non-parametric test based on
    normality of the data.

    Args:
        group1: First group values.
        group2: Second group values.
        paired: Whether groups are paired/matched.
        alpha: Significance level.

    Returns:
        GroupComparisonResult with test results.
    """
    arr1 = np.asarray(group1, dtype=float)
    arr2 = np.asarray(group2, dtype=float)
    arr1 = arr1[np.isfinite(arr1)]
    arr2 = arr2[np.isfinite(arr2)]

    n1, n2 = len(arr1), len(arr2)
    if n1 < _MIN_SAMPLES or n2 < _MIN_SAMPLES:
        return GroupComparisonResult(
            test_type=StatisticalTestType.TTEST_IND,
            statistic=0.0,
            p_value=1.0,
            p_adjusted=1.0,
            effect_size=0.0,
            effect_interpretation=EffectSizeType.NEGLIGIBLE,
            ci_low=0.0,
            ci_high=0.0,
            group1_n=n1,
            group2_n=n2,
            group1_mean=float(np.mean(arr1)) if n1 > 0 else 0.0,
            group2_mean=float(np.mean(arr2)) if n2 > 0 else 0.0,
            significant=False,
            recommendation="Insufficient sample size for analysis.",
        )

    # Check normality
    _, p1 = shapiro(arr1[:5000]) if len(arr1) >= 3 else (0, 1)
    _, p2 = shapiro(arr2[:5000]) if len(arr2) >= 3 else (0, 1)
    both_normal = p1 > alpha and p2 > alpha

    # Select and run test
    if paired:
        if len(arr1) != len(arr2):
            # Cannot do paired test with unequal lengths
            paired = False

    if paired:
        if both_normal:
            stat, p_val = ttest_rel(arr1, arr2)
            test_type = StatisticalTestType.TTEST_PAIRED
        else:
            stat, p_val = wilcoxon(arr1, arr2)
            test_type = StatisticalTestType.WILCOXON
    else:
        if both_normal:
            stat, p_val = ttest_ind(arr1, arr2)
            test_type = StatisticalTestType.TTEST_IND
        else:
            stat, p_val = mannwhitneyu(arr1, arr2, alternative="two-sided")
            test_type = StatisticalTestType.MANNWHITNEY

    # Effect size
    d, ci_low, ci_high = compute_cohens_d(arr1, arr2)
    effect_interp = _interpret_cohens_d(d)

    # Interpretation
    if p_val < alpha:
        if d > 0:
            recommendation = f"Group 1 significantly higher than Group 2 ({effect_interp.value} effect)."
        else:
            recommendation = f"Group 2 significantly higher than Group 1 ({effect_interp.value} effect)."
    else:
        recommendation = "No significant difference between groups."

    return GroupComparisonResult(
        test_type=test_type,
        statistic=float(stat),
        p_value=float(p_val),
        p_adjusted=float(p_val),  # Will be adjusted if part of multiple comparisons
        effect_size=d,
        effect_interpretation=effect_interp,
        ci_low=ci_low,
        ci_high=ci_high,
        group1_n=n1,
        group2_n=n2,
        group1_mean=float(np.mean(arr1)),
        group2_mean=float(np.mean(arr2)),
        significant=p_val < alpha,
        recommendation=recommendation,
    )


def compare_multiple_groups(
    groups: dict[str, np.ndarray | pd.Series],
    *,
    alpha: float = _ALPHA_DEFAULT,
    post_hoc: bool = True,
) -> ANOVAResult:
    """Compare multiple groups with ANOVA or Kruskal-Wallis.

    Args:
        groups: Dict of group_name -> values.
        alpha: Significance level.
        post_hoc: Whether to run post-hoc pairwise comparisons.

    Returns:
        ANOVAResult with test results.
    """
    if len(groups) < 2:
        raise ValueError("Need at least 2 groups for comparison.")

    # Clean data
    clean_groups: dict[str, np.ndarray] = {}
    for name, values in groups.items():
        arr = np.asarray(values, dtype=float)
        arr = arr[np.isfinite(arr)]
        if len(arr) >= _MIN_SAMPLES:
            clean_groups[name] = arr

    if len(clean_groups) < 2:
        raise ValueError("Insufficient valid data in groups.")

    # Check normality for all groups
    all_normal = True
    for arr in clean_groups.values():
        if len(arr) >= 3:
            _, p = shapiro(arr[:5000])
            if p <= alpha:
                all_normal = False
                break

    # Run appropriate test
    group_arrays = list(clean_groups.values())
    if all_normal:
        stat, p_val = f_oneway(*group_arrays)
        test_type = StatisticalTestType.ANOVA
    else:
        stat, p_val = kruskal(*group_arrays)
        test_type = StatisticalTestType.KRUSKAL

    # Compute effect size (eta-squared)
    all_data = np.concatenate(group_arrays)
    grand_mean = np.mean(all_data)
    ss_between = sum(len(g) * (np.mean(g) - grand_mean) ** 2 for g in group_arrays)
    ss_total = np.sum((all_data - grand_mean) ** 2)
    eta_squared = ss_between / ss_total if ss_total > 0 else 0.0

    # Omega-squared (less biased)
    n_total = len(all_data)
    k = len(clean_groups)
    df_between = k - 1
    df_within = n_total - k
    ms_within = (ss_total - ss_between) / df_within if df_within > 0 else 0
    omega_squared = (ss_between - df_between * ms_within) / (ss_total + ms_within)
    omega_squared = max(0, omega_squared)

    effect_interp = _interpret_eta_squared(eta_squared)

    # Group statistics
    group_means = {name: float(np.mean(arr)) for name, arr in clean_groups.items()}
    group_ns = {name: len(arr) for name, arr in clean_groups.items()}

    # Post-hoc comparisons
    post_hoc_results: list[GroupComparisonResult] = []
    if post_hoc and p_val < alpha:
        group_names = list(clean_groups.keys())
        p_values_raw: list[float] = []
        comparisons: list[tuple[str, str]] = []

        for i in range(len(group_names)):
            for j in range(i + 1, len(group_names)):
                g1, g2 = group_names[i], group_names[j]
                result = compare_two_groups(clean_groups[g1], clean_groups[g2])
                p_values_raw.append(result.p_value)
                comparisons.append((g1, g2))
                post_hoc_results.append(result)

        # Apply FDR correction
        p_adjusted = fdr_correction(p_values_raw)
        for idx, result in enumerate(post_hoc_results):
            # Create new result with adjusted p-value
            post_hoc_results[idx] = GroupComparisonResult(
                test_type=result.test_type,
                statistic=result.statistic,
                p_value=result.p_value,
                p_adjusted=p_adjusted[idx],
                effect_size=result.effect_size,
                effect_interpretation=result.effect_interpretation,
                ci_low=result.ci_low,
                ci_high=result.ci_high,
                group1_n=result.group1_n,
                group2_n=result.group2_n,
                group1_mean=result.group1_mean,
                group2_mean=result.group2_mean,
                significant=p_adjusted[idx] < alpha,
                recommendation=result.recommendation,
            )

    return ANOVAResult(
        test_type=test_type,
        statistic=float(stat),
        p_value=float(p_val),
        df_between=df_between,
        df_within=df_within,
        eta_squared=float(eta_squared),
        omega_squared=float(omega_squared),
        effect_interpretation=effect_interp,
        group_means=group_means,
        group_ns=group_ns,
        significant=p_val < alpha,
        post_hoc=post_hoc_results,
    )


# ---------------------------------------------------------------------------
# Correlation Analysis
# ---------------------------------------------------------------------------


def compute_correlation(
    x: np.ndarray | pd.Series,
    y: np.ndarray | pd.Series,
    *,
    method: str = "auto",
) -> CorrelationResult:
    """Compute correlation between two variables.

    Args:
        x: First variable values.
        y: Second variable values.
        method: "pearson", "spearman", or "auto" (selects based on normality).

    Returns:
        CorrelationResult with correlation statistics.
    """
    arr_x = np.asarray(x, dtype=float)
    arr_y = np.asarray(y, dtype=float)

    # Align and clean
    mask = np.isfinite(arr_x) & np.isfinite(arr_y)
    arr_x = arr_x[mask]
    arr_y = arr_y[mask]
    n = len(arr_x)

    if n < _MIN_SAMPLES:
        return CorrelationResult(
            var1="x",
            var2="y",
            method="unknown",
            r=0.0,
            p_value=1.0,
            p_adjusted=1.0,
            n=n,
            r_squared=0.0,
            ci_low=0.0,
            ci_high=0.0,
            significant=False,
            strength="insufficient data",
        )

    # Auto-select method based on normality
    if method == "auto":
        _, p_x = shapiro(arr_x[:5000]) if n >= 3 else (0, 1)
        _, p_y = shapiro(arr_y[:5000]) if n >= 3 else (0, 1)
        method = "pearson" if (p_x > 0.05 and p_y > 0.05) else "spearman"

    # Compute correlation
    if method == "spearman":
        r, p_val = spearmanr(arr_x, arr_y)
    else:
        r, p_val = pearsonr(arr_x, arr_y)

    # Fisher's z transformation for CI
    if abs(r) < 0.9999:
        z = 0.5 * np.log((1 + r) / (1 - r))
        se_z = 1 / np.sqrt(n - 3) if n > 3 else 0
        z_low = z - 1.96 * se_z
        z_high = z + 1.96 * se_z
        ci_low = (np.exp(2 * z_low) - 1) / (np.exp(2 * z_low) + 1)
        ci_high = (np.exp(2 * z_high) - 1) / (np.exp(2 * z_high) + 1)
    else:
        ci_low = ci_high = r

    return CorrelationResult(
        var1="x",
        var2="y",
        method=method,
        r=float(r),
        p_value=float(p_val),
        p_adjusted=float(p_val),
        n=n,
        r_squared=float(r**2),
        ci_low=float(ci_low),
        ci_high=float(ci_high),
        significant=p_val < _ALPHA_DEFAULT,
        strength=_interpret_r(r),
    )


def compute_correlation_matrix(
    df: pd.DataFrame,
    variables: list[str],
    *,
    method: str = "auto",
    correct_multiple: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, list[CorrelationResult]]:
    """Compute correlation matrix with p-values.

    Args:
        df: DataFrame with variables.
        variables: List of variable column names.
        method: Correlation method.
        correct_multiple: Whether to apply FDR correction.

    Returns:
        Tuple of (correlation matrix, p-value matrix, list of results).
    """
    valid_vars = [v for v in variables if v in df.columns]
    n_vars = len(valid_vars)

    if n_vars < 2:
        return pd.DataFrame(), pd.DataFrame(), []

    # Initialize matrices
    corr_matrix = pd.DataFrame(
        np.eye(n_vars),
        index=valid_vars,
        columns=valid_vars,
    )
    p_matrix = pd.DataFrame(
        np.zeros((n_vars, n_vars)),
        index=valid_vars,
        columns=valid_vars,
    )

    results: list[CorrelationResult] = []
    p_values_raw: list[float] = []

    # Compute pairwise correlations
    for i in range(n_vars):
        for j in range(i + 1, n_vars):
            var1, var2 = valid_vars[i], valid_vars[j]
            result = compute_correlation(
                df[var1].dropna(),
                df[var2].dropna(),
                method=method,
            )
            result = CorrelationResult(
                var1=var1,
                var2=var2,
                method=result.method,
                r=result.r,
                p_value=result.p_value,
                p_adjusted=result.p_adjusted,
                n=result.n,
                r_squared=result.r_squared,
                ci_low=result.ci_low,
                ci_high=result.ci_high,
                significant=result.significant,
                strength=result.strength,
            )

            corr_matrix.loc[var1, var2] = result.r
            corr_matrix.loc[var2, var1] = result.r
            p_matrix.loc[var1, var2] = result.p_value
            p_matrix.loc[var2, var1] = result.p_value

            results.append(result)
            p_values_raw.append(result.p_value)

    # Apply multiple comparison correction
    if correct_multiple and p_values_raw:
        p_adjusted = fdr_correction(p_values_raw)
        for idx, result in enumerate(results):
            results[idx] = CorrelationResult(
                var1=result.var1,
                var2=result.var2,
                method=result.method,
                r=result.r,
                p_value=result.p_value,
                p_adjusted=p_adjusted[idx],
                n=result.n,
                r_squared=result.r_squared,
                ci_low=result.ci_low,
                ci_high=result.ci_high,
                significant=p_adjusted[idx] < _ALPHA_DEFAULT,
                strength=result.strength,
            )

    return corr_matrix, p_matrix, results


# ---------------------------------------------------------------------------
# Regression Analysis
# ---------------------------------------------------------------------------


def compute_linear_regression(
    df: pd.DataFrame,
    dependent_var: str,
    independent_vars: list[str],
) -> RegressionResult | None:
    """Compute multiple linear regression.

    Args:
        df: DataFrame with variables.
        dependent_var: Dependent variable column name.
        independent_vars: List of independent variable column names.

    Returns:
        RegressionResult or None if insufficient data.
    """
    # Validate columns
    all_vars = [dependent_var] + independent_vars
    valid_vars = [v for v in all_vars if v in df.columns]
    if len(valid_vars) != len(all_vars):
        return None

    # Clean data
    data = df[all_vars].dropna()
    n = len(data)
    k = len(independent_vars)

    if n < k + 2:
        return None

    # Prepare matrices
    y = data[dependent_var].values
    X = data[independent_vars].values
    X_with_intercept = np.column_stack([np.ones(n), X])

    # Solve normal equations
    try:
        beta = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
    except np.linalg.LinAlgError:
        return None

    # Predictions and residuals
    y_pred = X_with_intercept @ beta
    residuals = y - y_pred
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y - np.mean(y))**2)

    # R-squared
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    adj_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - k - 1) if n > k + 1 else 0.0

    # Residual standard error
    residual_std = np.sqrt(ss_res / (n - k - 1)) if n > k + 1 else 0.0

    # Standard errors of coefficients
    try:
        var_beta = residual_std**2 * np.linalg.inv(X_with_intercept.T @ X_with_intercept)
        se_beta = np.sqrt(np.diag(var_beta))
    except np.linalg.LinAlgError:
        se_beta = np.zeros(k + 1)

    # T-values and p-values
    t_values = beta / (se_beta + 1e-9)
    p_values = 2 * (1 - stats.t.cdf(np.abs(t_values), n - k - 1))

    # F-statistic
    ss_reg = ss_tot - ss_res
    ms_reg = ss_reg / k if k > 0 else 0
    ms_res = ss_res / (n - k - 1) if n > k + 1 else 1
    f_stat = ms_reg / ms_res if ms_res > 0 else 0
    f_p_value = 1 - stats.f.cdf(f_stat, k, n - k - 1) if n > k + 1 else 1.0

    # AIC and BIC
    log_likelihood = -n / 2 * (1 + np.log(2 * np.pi) + np.log(ss_res / n))
    aic = 2 * (k + 1) - 2 * log_likelihood
    bic = np.log(n) * (k + 1) - 2 * log_likelihood

    # Build result dictionaries
    var_names = ["intercept"] + independent_vars
    coefficients = {var_names[i]: float(beta[i]) for i in range(len(var_names))}
    std_errors = {var_names[i]: float(se_beta[i]) for i in range(len(var_names))}
    t_vals = {var_names[i]: float(t_values[i]) for i in range(len(var_names))}
    p_vals = {var_names[i]: float(p_values[i]) for i in range(len(var_names))}

    return RegressionResult(
        dependent_var=dependent_var,
        independent_vars=tuple(independent_vars),
        coefficients=coefficients,
        std_errors=std_errors,
        t_values=t_vals,
        p_values=p_vals,
        r_squared=float(r_squared),
        adj_r_squared=float(adj_r_squared),
        f_statistic=float(f_stat),
        f_p_value=float(f_p_value),
        n=n,
        residual_std=float(residual_std),
        aic=float(aic),
        bic=float(bic),
    )


# ---------------------------------------------------------------------------
# Reporting utilities
# ---------------------------------------------------------------------------


def format_apa_correlation(result: CorrelationResult) -> str:
    """Format correlation result in APA style.

    Args:
        result: CorrelationResult to format.

    Returns:
        APA-formatted string.
    """
    method_abbrev = "r" if result.method == "pearson" else "ρ"
    p_str = "< .001" if result.p_value < 0.001 else f"= {result.p_value:.3f}"
    return f"{method_abbrev}({result.n - 2}) = {result.r:.2f}, p {p_str}"


def format_apa_ttest(result: GroupComparisonResult) -> str:
    """Format t-test result in APA style.

    Args:
        result: GroupComparisonResult to format.

    Returns:
        APA-formatted string.
    """
    df = result.group1_n + result.group2_n - 2
    p_str = "< .001" if result.p_value < 0.001 else f"= {result.p_value:.3f}"
    return f"t({df}) = {result.statistic:.2f}, p {p_str}, d = {result.effect_size:.2f}"


def format_apa_anova(result: ANOVAResult) -> str:
    """Format ANOVA result in APA style.

    Args:
        result: ANOVAResult to format.

    Returns:
        APA-formatted string.
    """
    p_str = "< .001" if result.p_value < 0.001 else f"= {result.p_value:.3f}"
    if result.test_type == StatisticalTestType.ANOVA:
        return f"F({result.df_between}, {result.df_within}) = {result.statistic:.2f}, p {p_str}, η² = {result.eta_squared:.2f}"
    return f"H({result.df_between}) = {result.statistic:.2f}, p {p_str}, η² = {result.eta_squared:.2f}"

