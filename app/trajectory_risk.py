# Author: Dr Diego Malpica MD
"""
Physiological Trajectory Risk Module — Allostatic Load Alarm.

Detects multi-day physiological degradation patterns that the single-day
readiness snapshot misses. Computes EWMA-smoothed trends, Smallest
Worthwhile Change (SWC) exceedance, and a composite Physiological Strain
Index (PSI) to produce a bounded readiness modifier and alert flags.

This module implements the "missing longitudinal layer" identified in the
IRM v2.0 architecture, providing:

1. EWMA-smoothed 7-day trends for lnRMSSD, resting HR, and sleep quality
2. SWC threshold detection (Plews et al., 2013; Buchheit, 2014)
3. Composite Physiological Strain Index (PSI) for allostatic load
4. Overtraining / maladaptation risk classification
5. Bounded readiness modifier (±8 points) for fusion into the IRM

Scientific Basis:
    - Allostatic load theory: cumulative physiological "wear and tear"
      predicts functional decline independently of acute state
      (McEwen, 1998; Juster et al., 2010)
    - EWMA-based HRV monitoring detects overreaching before performance
      decline (Plews et al., 2013; Bellenger et al., 2016)
    - SWC = 0.5 × CV of lnRMSSD identifies meaningful vs. noise changes
      (Buchheit, 2014; Plews et al., 2013)
    - Multi-metric trajectory analysis outperforms single-metric snapshot
      for training readiness (Moreno-Gutiérrez et al., 2021, accuracy 73%)
    - Sleep-debt potentiation of HRV decline creates non-linear risk
      (Tobaldini et al., 2017; Farooq et al., 2025)

References:
    McEwen BS (1998). Protective and damaging effects of stress mediators.
        NEJM, 338, 171-179. doi: 10.1056/NEJM199801153380307
    Juster RP, et al. (2010). Allostatic load biomarkers.
        Neurosci Biobehav Rev, 35, 2-16. doi: 10.1016/j.neubiorev.2009.10.002
    Plews DJ, et al. (2013). Training adaptation and HRV in elite athletes.
        J Strength Cond Res, 27(12), 3159-3165.
    Buchheit M (2014). Monitoring training status with HR measures.
        Front Physiol, 5, 73. doi: 10.3389/fphys.2014.00073
    Bellenger CR, et al. (2016). Monitoring athletic training status through
        autonomic HRV. Sports Med, 46, 1461-1486. doi: 10.1007/s40279-016-0487-7
    Tobaldini E, et al. (2017). Sleep deprivation and autonomic nervous system.
        Sleep Med Rev, 35, 62-73. doi: 10.1016/j.smrv.2016.08.003
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Final, List, Optional, Tuple

import numpy as np

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# EWMA parameters (Plews et al., 2013)
EWMA_SPAN: Final[int] = 7  # 7-day exponential smoothing
EWMA_ALPHA: Final[float] = 2.0 / (EWMA_SPAN + 1)  # ≈ 0.25

# SWC = 0.5 × between-subject SD (conservative) or 0.5 × CV
# Buchheit (2014): SWC for lnRMSSD ≈ 0.5 × CV_lnRMSSD
SWC_MULTIPLIER: Final[float] = 0.5

# Minimum data points
MIN_DAYS_FOR_TREND: Final[int] = 5
MIN_DAYS_FOR_BASELINE: Final[int] = 7

# Trajectory risk thresholds
DECLINING_SLOPE_THRESHOLD: Final[float] = -0.02  # lnRMSSD units/day
SEVERE_DECLINE_THRESHOLD: Final[float] = -0.05
RHR_RISING_THRESHOLD: Final[float] = 0.5  # bpm/day
SLEEP_DECLINING_THRESHOLD: Final[float] = -0.03  # quality units/day

# PSI composite thresholds (0-100 scale)
PSI_LOW: Final[float] = 25.0
PSI_MODERATE: Final[float] = 50.0
PSI_HIGH: Final[float] = 70.0
PSI_CRITICAL: Final[float] = 85.0

# Readiness modifier bounds (points)
MAX_TRAJECTORY_BONUS: Final[float] = 5.0
MAX_TRAJECTORY_PENALTY: Final[float] = 8.0


class TrajectoryRisk(str, Enum):
    """Trajectory risk classification."""

    IMPROVING = "improving"  # Positive adaptation
    STABLE = "stable"  # Within normal variation
    WATCH = "watch"  # SWC exceedance, not yet alarming
    ELEVATED = "elevated"  # Multi-metric degradation
    CRITICAL = "critical"  # Severe sustained decline — likely overreaching


@dataclass(frozen=True, slots=True)
class DailyMetricPoint:
    """Single day of physiological data for trajectory analysis.

    Attributes:
        day_index: Day number (0 = oldest).
        ln_rmssd: Natural log of RMSSD (ms).
        resting_hr: Resting heart rate (bpm), or None.
        sleep_quality: Sleep quality (0-1), or None.
        dfa_alpha1: Resting DFA-α1, or None.
        confidence: Data quality (0-1).
    """

    day_index: int
    ln_rmssd: float
    resting_hr: Optional[float] = None
    sleep_quality: Optional[float] = None
    dfa_alpha1: Optional[float] = None
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class MetricTrend:
    """Trend analysis result for a single metric.

    Attributes:
        metric_name: Identifier (e.g., "ln_rmssd", "resting_hr").
        ewma_current: Current EWMA value.
        ewma_baseline: Baseline EWMA (first 7 days or provided).
        slope_per_day: Linear slope (units/day).
        pct_change_7d: Percentage change over last 7 days.
        swc_exceeded: Whether change exceeds Smallest Worthwhile Change.
        direction: 'improving', 'stable', or 'declining'.
        z_score: Z-score of current value vs. baseline.
    """

    metric_name: str
    ewma_current: float
    ewma_baseline: float
    slope_per_day: float
    pct_change_7d: float
    swc_exceeded: bool
    direction: str
    z_score: float


@dataclass(slots=True)
class TrajectoryAnalysis:
    """Complete trajectory risk assessment.

    Attributes:
        risk_level: Overall trajectory risk classification.
        psi_score: Physiological Strain Index (0-100).
        readiness_modifier: Bounded modifier for readiness fusion (±pts).
        trends: Per-metric trend analyses.
        n_declining: Number of metrics in decline.
        n_swc_exceeded: Number of metrics exceeding SWC.
        alerts: Alert messages.
        recommendations: Actionable recommendations.
        interpretation: Summary interpretation.
        data_days: Number of days of data used.
        confidence: Overall assessment confidence (0-1).
    """

    risk_level: TrajectoryRisk
    psi_score: float
    readiness_modifier: float
    trends: List[MetricTrend] = field(default_factory=list)
    n_declining: int = 0
    n_swc_exceeded: int = 0
    alerts: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    interpretation: str = ""
    data_days: int = 0
    confidence: float = 1.0


# ---------------------------------------------------------------------------
# EWMA computation
# ---------------------------------------------------------------------------


def _compute_ewma(values: List[float], alpha: float = EWMA_ALPHA) -> List[float]:
    """Compute Exponentially Weighted Moving Average.

    Args:
        values: Time series values (oldest first).
        alpha: Smoothing factor (2/(span+1) for span-day EWMA).

    Returns:
        EWMA-smoothed series (same length as input).
    """
    if not values:
        return []

    ewma: List[float] = [values[0]]
    for i in range(1, len(values)):
        smoothed = alpha * values[i] + (1.0 - alpha) * ewma[i - 1]
        ewma.append(smoothed)

    return ewma


def _compute_slope(values: List[float]) -> float:
    """Compute linear slope via least-squares regression.

    Args:
        values: Time series (oldest first, 1-unit spacing).

    Returns:
        Slope in units per step (day).
    """
    if len(values) < 2:
        return 0.0

    x = np.arange(len(values), dtype=np.float64)
    y = np.array(values, dtype=np.float64)

    # Mask NaN
    valid = np.isfinite(y)
    if np.sum(valid) < 2:
        return 0.0

    slope: float = float(np.polyfit(x[valid], y[valid], 1)[0])
    return slope


# ---------------------------------------------------------------------------
# Single-metric trend analysis
# ---------------------------------------------------------------------------


def _analyze_metric_trend(
    values: List[float],
    metric_name: str,
    higher_is_better: bool = True,
    swc_cv: Optional[float] = None,
) -> Optional[MetricTrend]:
    """Analyze trend for a single physiological metric.

    Args:
        values: Daily values (oldest first), may contain NaN.
        metric_name: Identifier string.
        higher_is_better: Whether higher values indicate better status.
        swc_cv: Coefficient of variation for SWC computation.
            If None, computed from data.

    Returns:
        MetricTrend, or None if insufficient data.
    """
    clean = [v for v in values if np.isfinite(v)]
    if len(clean) < MIN_DAYS_FOR_TREND:
        return None

    # EWMA
    ewma_series = _compute_ewma(clean)
    ewma_current = ewma_series[-1]

    # Baseline: first MIN_DAYS_FOR_BASELINE points or all if shorter
    baseline_n = min(MIN_DAYS_FOR_BASELINE, len(clean))
    ewma_baseline_vals = ewma_series[:baseline_n]
    ewma_baseline = float(np.mean(ewma_baseline_vals))

    # Slope (on EWMA-smoothed series for stability)
    slope = _compute_slope(ewma_series)

    # Percentage change over last 7 days
    lookback = min(7, len(ewma_series))
    if ewma_series[-lookback] != 0:
        pct_change = (ewma_current - ewma_series[-lookback]) / abs(ewma_series[-lookback]) * 100.0
    else:
        pct_change = 0.0

    # SWC exceedance (Buchheit 2014: SWC = 0.5 × CV)
    if swc_cv is not None and swc_cv > 0:
        swc = SWC_MULTIPLIER * swc_cv / 100.0 * abs(ewma_baseline)
    else:
        baseline_std = float(np.std(clean[:baseline_n], ddof=1)) if baseline_n > 1 else 0.0
        swc = SWC_MULTIPLIER * baseline_std

    change_from_baseline = abs(ewma_current - ewma_baseline)
    # SWC exceedance requires both absolute change AND meaningful slope
    swc_exceeded = (change_from_baseline > swc and abs(slope) > 1e-4) if swc > 0 else False

    # Z-score
    baseline_std_full = float(np.std(clean[:baseline_n], ddof=1)) if baseline_n > 1 else 1.0
    if baseline_std_full > 1e-10:
        z_score = (ewma_current - ewma_baseline) / baseline_std_full
    else:
        z_score = 0.0

    # Direction
    if higher_is_better:
        if slope > 0 and swc_exceeded:
            direction = "improving"
        elif slope < 0 and swc_exceeded:
            direction = "declining"
        else:
            direction = "stable"
    else:
        # Lower is better (e.g., resting HR)
        if slope < 0 and swc_exceeded:
            direction = "improving"
        elif slope > 0 and swc_exceeded:
            direction = "declining"
        else:
            direction = "stable"

    return MetricTrend(
        metric_name=metric_name,
        ewma_current=ewma_current,
        ewma_baseline=ewma_baseline,
        slope_per_day=slope,
        pct_change_7d=pct_change,
        swc_exceeded=swc_exceeded,
        direction=direction,
        z_score=z_score,
    )


# ---------------------------------------------------------------------------
# Physiological Strain Index (PSI)
# ---------------------------------------------------------------------------


def _compute_psi(trends: List[MetricTrend]) -> float:
    """Compute composite Physiological Strain Index (0-100).

    Higher PSI = more physiological strain / allostatic load.
    Each declining metric contributes proportionally based on
    its z-score magnitude and SWC exceedance.

    The PSI is inspired by the allostatic load index literature
    (Juster et al., 2010) adapted for wearable-derived metrics.

    Args:
        trends: List of per-metric trend analyses.

    Returns:
        PSI score [0, 100].
    """
    if not trends:
        return 0.0

    strain_components: List[float] = []

    for trend in trends:
        # Base strain from z-score (negative z for declining metrics)
        if trend.direction == "declining":
            z_magnitude = abs(trend.z_score)
            # Sigmoid mapping: z=0 -> 0, z=1 -> ~0.46, z=2 -> ~0.76, z=3 -> ~0.91
            strain = 1.0 / (1.0 + np.exp(-1.5 * (z_magnitude - 1.0)))

            # Amplify if SWC is exceeded
            if trend.swc_exceeded:
                strain *= 1.3

            strain_components.append(float(strain))
        elif trend.direction == "improving":
            # Improving metrics reduce strain (bounded)
            strain_components.append(-0.15)
        else:
            strain_components.append(0.0)

    # Aggregate: mean strain × 100, clamped
    if strain_components:
        raw_psi = float(np.mean(strain_components)) * 100.0
    else:
        raw_psi = 0.0

    return max(0.0, min(100.0, raw_psi))


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------


def _classify_risk(
    psi: float,
    n_declining: int,
    n_swc_exceeded: int,
    n_total: int,
) -> TrajectoryRisk:
    """Classify trajectory risk level.

    Uses a multi-gate approach: PSI score + number of declining metrics
    + SWC exceedance count determine the risk tier.

    Args:
        psi: Physiological Strain Index (0-100).
        n_declining: Count of metrics in decline.
        n_swc_exceeded: Count of metrics exceeding SWC.
        n_total: Total number of metrics analyzed.

    Returns:
        TrajectoryRisk classification.
    """
    # Critical: high PSI AND multiple metrics declining beyond SWC
    if psi >= PSI_CRITICAL or (n_swc_exceeded >= 3 and n_declining >= 3):
        return TrajectoryRisk.CRITICAL

    # Elevated: moderate PSI AND multiple declining
    if psi >= PSI_HIGH or (n_swc_exceeded >= 2 and n_declining >= 2):
        return TrajectoryRisk.ELEVATED

    # Watch: any SWC exceedance or moderate PSI
    if psi >= PSI_MODERATE or n_swc_exceeded >= 1:
        return TrajectoryRisk.WATCH

    # Improving: net positive trajectory
    if psi < PSI_LOW and n_declining == 0:
        return TrajectoryRisk.IMPROVING

    return TrajectoryRisk.STABLE


# ---------------------------------------------------------------------------
# Readiness modifier computation
# ---------------------------------------------------------------------------


def _compute_readiness_modifier(
    risk: TrajectoryRisk,
    psi: float,
) -> float:
    """Compute bounded readiness modifier from trajectory risk.

    Maps trajectory risk to a readiness score adjustment:
    - IMPROVING: +2 to +5 bonus
    - STABLE: 0 (neutral)
    - WATCH: -2 to -4 penalty
    - ELEVATED: -4 to -6 penalty
    - CRITICAL: -6 to -8 penalty

    Args:
        risk: Trajectory risk classification.
        psi: Physiological Strain Index.

    Returns:
        Readiness modifier (bounded ±8 points).
    """
    if risk == TrajectoryRisk.IMPROVING:
        # Scale bonus by how low PSI is (lower = more improving)
        bonus = MAX_TRAJECTORY_BONUS * (1.0 - psi / 100.0)
        return max(0.0, min(MAX_TRAJECTORY_BONUS, bonus))

    if risk == TrajectoryRisk.STABLE:
        return 0.0

    # Penalties scale with PSI
    psi_fraction = psi / 100.0

    if risk == TrajectoryRisk.WATCH:
        return -max(2.0, 4.0 * psi_fraction)

    if risk == TrajectoryRisk.ELEVATED:
        return -max(4.0, 6.0 * psi_fraction)

    # CRITICAL
    return -max(6.0, MAX_TRAJECTORY_PENALTY * psi_fraction)


# ---------------------------------------------------------------------------
# Main analysis function
# ---------------------------------------------------------------------------


def analyze_trajectory(
    daily_data: List[DailyMetricPoint],
) -> TrajectoryAnalysis:
    """Perform complete physiological trajectory risk assessment.

    Computes EWMA trends, SWC exceedance, PSI composite score,
    and produces a bounded readiness modifier with clinical interpretation.

    This is the primary entry point for the trajectory risk module.

    Args:
        daily_data: List of daily metric points (oldest first).
            Must contain at least MIN_DAYS_FOR_TREND days.

    Returns:
        TrajectoryAnalysis with risk level, PSI, modifier, and alerts.

    References:
        Plews DJ, et al. (2013). J Strength Cond Res, 27(12), 3159-3165.
        Buchheit M (2014). Front Physiol, 5, 73.
        McEwen BS (1998). NEJM, 338, 171-179.
    """
    if len(daily_data) < MIN_DAYS_FOR_TREND:
        return TrajectoryAnalysis(
            risk_level=TrajectoryRisk.STABLE,
            psi_score=0.0,
            readiness_modifier=0.0,
            interpretation=(
                f"Insufficient data ({len(daily_data)} days). "
                f"Need ≥{MIN_DAYS_FOR_TREND} days for trajectory analysis."
            ),
            data_days=len(daily_data),
            confidence=0.3,
        )

    trends: List[MetricTrend] = []
    alerts: List[str] = []
    recommendations: List[str] = []

    # Sort by day_index
    sorted_data = sorted(daily_data, key=lambda d: d.day_index)

    # -----------------------------------------------------------------------
    # Trend 1: lnRMSSD (primary autonomic marker)
    # -----------------------------------------------------------------------
    ln_rmssd_vals = [d.ln_rmssd for d in sorted_data]
    t_rmssd = _analyze_metric_trend(
        ln_rmssd_vals, "ln_rmssd", higher_is_better=True
    )
    if t_rmssd is not None:
        trends.append(t_rmssd)
        if t_rmssd.direction == "declining" and t_rmssd.swc_exceeded:
            alerts.append(
                f"lnRMSSD declining: {t_rmssd.pct_change_7d:+.1f}% over 7 days "
                f"(z = {t_rmssd.z_score:.1f}, exceeds SWC). "
                "Suggests autonomic fatigue accumulation."
            )

    # -----------------------------------------------------------------------
    # Trend 2: Resting HR (sympathetic marker)
    # -----------------------------------------------------------------------
    rhr_vals = [d.resting_hr for d in sorted_data if d.resting_hr is not None]
    if len(rhr_vals) >= MIN_DAYS_FOR_TREND:
        rhr_floats = [float(v) for v in rhr_vals]
        t_rhr = _analyze_metric_trend(
            rhr_floats, "resting_hr", higher_is_better=False
        )
        if t_rhr is not None:
            trends.append(t_rhr)
            if t_rhr.direction == "declining" and t_rhr.swc_exceeded:
                alerts.append(
                    f"Resting HR rising: {t_rhr.pct_change_7d:+.1f}% over 7 days "
                    f"(z = {t_rhr.z_score:.1f}). "
                    "Elevated sympathetic drive or incomplete recovery."
                )

    # -----------------------------------------------------------------------
    # Trend 3: Sleep quality
    # -----------------------------------------------------------------------
    sleep_vals = [d.sleep_quality for d in sorted_data if d.sleep_quality is not None]
    if len(sleep_vals) >= MIN_DAYS_FOR_TREND:
        sleep_floats = [float(v) for v in sleep_vals]
        t_sleep = _analyze_metric_trend(
            sleep_floats, "sleep_quality", higher_is_better=True
        )
        if t_sleep is not None:
            trends.append(t_sleep)
            if t_sleep.direction == "declining" and t_sleep.swc_exceeded:
                alerts.append(
                    f"Sleep quality declining: {t_sleep.pct_change_7d:+.1f}% over 7 days. "
                    "Sleep debt accumulation potentiates physiological strain "
                    "(Tobaldini et al., 2017)."
                )

    # -----------------------------------------------------------------------
    # Trend 4: Resting DFA-α1 (cardiac complexity)
    # -----------------------------------------------------------------------
    dfa_vals = [d.dfa_alpha1 for d in sorted_data if d.dfa_alpha1 is not None]
    if len(dfa_vals) >= MIN_DAYS_FOR_TREND:
        dfa_floats = [float(v) for v in dfa_vals]
        t_dfa = _analyze_metric_trend(
            dfa_floats, "dfa_alpha1_rest", higher_is_better=True
        )
        if t_dfa is not None:
            trends.append(t_dfa)
            if t_dfa.direction == "declining" and t_dfa.swc_exceeded:
                alerts.append(
                    f"Resting DFA-α1 declining: {t_dfa.pct_change_7d:+.1f}% over 7 days "
                    f"(z = {t_dfa.z_score:.1f}). "
                    "Reduced cardiac complexity — possible overtraining "
                    "(Bellenger et al., 2016)."
                )

    # -----------------------------------------------------------------------
    # Composite analysis
    # -----------------------------------------------------------------------
    n_declining = sum(1 for t in trends if t.direction == "declining")
    n_improving = sum(1 for t in trends if t.direction == "improving")
    n_swc = sum(1 for t in trends if t.swc_exceeded and t.direction == "declining")

    psi = _compute_psi(trends)
    risk = _classify_risk(psi, n_declining, n_swc, len(trends))
    modifier = _compute_readiness_modifier(risk, psi)

    # -----------------------------------------------------------------------
    # Recommendations
    # -----------------------------------------------------------------------
    if risk == TrajectoryRisk.CRITICAL:
        recommendations.extend([
            "Immediate workload reduction recommended.",
            "Consider 48-72h active recovery period.",
            "Validate with objective performance test (PVT or equivalent).",
            "Screen for Overtraining Syndrome (OTS) symptoms.",
        ])
    elif risk == TrajectoryRisk.ELEVATED:
        recommendations.extend([
            "Reduce training/operational intensity for 24-48h.",
            "Prioritize sleep hygiene and recovery protocols.",
            "Monitor trajectory daily — escalate if no improvement in 48h.",
        ])
    elif risk == TrajectoryRisk.WATCH:
        recommendations.extend([
            "Continue monitoring. Current trajectory warrants attention.",
            "Ensure adequate sleep (≥7h) and recovery between sessions.",
        ])
    elif risk == TrajectoryRisk.IMPROVING:
        recommendations.append(
            "Positive physiological trajectory. Current load/recovery balance is effective."
        )
    else:
        recommendations.append("Trajectory stable. No intervention needed.")

    # Handle sleep-HRV interaction (Fatigue-Hypoxia feedback loop equivalent)
    sleep_declining = any(
        t.metric_name == "sleep_quality" and t.direction == "declining"
        and t.swc_exceeded
        for t in trends
    )
    hrv_declining = any(
        t.metric_name == "ln_rmssd" and t.direction == "declining"
        and t.swc_exceeded
        for t in trends
    )
    if sleep_declining and hrv_declining:
        alerts.append(
            "COMPOUND RISK: Both sleep quality and HRV declining simultaneously. "
            "Sleep debt potentiates autonomic strain — non-linear risk elevation "
            "(McEwen, 1998; Tobaldini et al., 2017)."
        )
        # Amplify penalty (cap at -MAX_TRAJECTORY_PENALTY)
        modifier = max(-MAX_TRAJECTORY_PENALTY, modifier * 1.3)

    # -----------------------------------------------------------------------
    # Confidence
    # -----------------------------------------------------------------------
    data_confidence = min(1.0, len(daily_data) / 14.0)  # full confidence at 14+ days
    quality_mean = float(np.mean([d.confidence for d in sorted_data]))
    overall_confidence = data_confidence * quality_mean

    # -----------------------------------------------------------------------
    # Interpretation
    # -----------------------------------------------------------------------
    interpretation_parts: List[str] = [
        f"Trajectory risk: {risk.value.upper()} "
        f"(PSI: {psi:.0f}/100, modifier: {modifier:+.1f} pts).",
        f"Analyzed {len(daily_data)} days, {len(trends)} metrics tracked.",
        f"Declining: {n_declining}/{len(trends)}, "
        f"SWC exceeded: {n_swc}/{len(trends)}, "
        f"Improving: {n_improving}/{len(trends)}.",
    ]
    interpretation = " ".join(interpretation_parts)

    return TrajectoryAnalysis(
        risk_level=risk,
        psi_score=psi,
        readiness_modifier=modifier,
        trends=trends,
        n_declining=n_declining,
        n_swc_exceeded=n_swc,
        alerts=alerts,
        recommendations=recommendations,
        interpretation=interpretation,
        data_days=len(daily_data),
        confidence=overall_confidence,
    )


# ---------------------------------------------------------------------------
# Integration helper for readiness model
# ---------------------------------------------------------------------------


def compute_trajectory_readiness_modifier(
    daily_ln_rmssd: List[float],
    daily_resting_hr: Optional[List[float]] = None,
    daily_sleep_quality: Optional[List[float]] = None,
    daily_dfa_alpha1: Optional[List[float]] = None,
    daily_confidence: Optional[List[float]] = None,
) -> Tuple[float, TrajectoryRisk, List[str]]:
    """Convenience function for readiness model integration.

    Accepts parallel lists of daily metrics and returns the trajectory
    modifier, risk level, and alert messages for fusion into the IRM.

    Args:
        daily_ln_rmssd: lnRMSSD values (oldest first), minimum 5 days.
        daily_resting_hr: Optional resting HR values (bpm).
        daily_sleep_quality: Optional sleep quality (0-1).
        daily_dfa_alpha1: Optional resting DFA-α1 values.
        daily_confidence: Optional per-day data quality (0-1).

    Returns:
        Tuple of (readiness_modifier, risk_level, alerts).
    """
    n = len(daily_ln_rmssd)
    if n < MIN_DAYS_FOR_TREND:
        return 0.0, TrajectoryRisk.STABLE, []

    points: List[DailyMetricPoint] = []
    for i in range(n):
        rhr = daily_resting_hr[i] if daily_resting_hr and i < len(daily_resting_hr) else None
        sq = daily_sleep_quality[i] if daily_sleep_quality and i < len(daily_sleep_quality) else None
        dfa = daily_dfa_alpha1[i] if daily_dfa_alpha1 and i < len(daily_dfa_alpha1) else None
        conf = daily_confidence[i] if daily_confidence and i < len(daily_confidence) else 1.0

        points.append(DailyMetricPoint(
            day_index=i,
            ln_rmssd=daily_ln_rmssd[i],
            resting_hr=rhr,
            sleep_quality=sq,
            dfa_alpha1=dfa,
            confidence=conf,
        ))

    result = analyze_trajectory(points)
    return result.readiness_modifier, result.risk_level, result.alerts
