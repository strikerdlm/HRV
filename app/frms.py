"""Fatigue Risk Management System (FRMS) helpers for the SAFTE tab.

This module provides deterministic, testable helpers to:
- derive FRMS-style exposure metrics from a SAFTE effectiveness time series,
- classify fatigue risk using an SMS-style risk matrix, and
- check USAF crew rest compliance (AFMAN 11-202V3).

Design goals
- Pure functions (easy to test, no Streamlit dependencies).
- Bounded execution (finite loops, finite inputs).
- Explicit validation and error modes.

Primary references (see in-app References tab for APA links):
- ICAO Doc 9966 (2016): Manual for the Oversight of Fatigue Management Approaches.
- Department of the Air Force. AFMAN 11-202V3: General Flight Rules (crew rest).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True, slots=True)
class FRMSThresholds:
    """Operational thresholds for SAFTE effectiveness (%).

    Defaults align with commonly cited SAFTE/FAST operational thresholds:
    - >= 90%: low fatigue risk
    - <= 77%: high fatigue risk (often compared to ~0.05% BAC impairment)
    - <= 70%: severe impairment (often compared to ~0.08% BAC impairment)
    """

    low_risk_min_effectiveness: float = 90.0
    high_risk_max_effectiveness: float = 77.0
    severe_impairment_max_effectiveness: float = 70.0

    # Window of Circadian Low (WOCL) is commonly treated as ~02:00–06:00 local.
    wocl_start_hour: int = 2
    wocl_end_hour: int = 6


@dataclass(frozen=True, slots=True)
class FRMSExposureMetrics:
    """Computed exposure metrics for an effectiveness time series."""

    samples_total: int
    samples_in_scope: int
    hours_in_scope: float
    hours_in_wocl: float

    min_effectiveness: float | None
    mean_effectiveness: float | None

    hours_below_90: float
    hours_at_or_below_77: float
    hours_at_or_below_70: float

    pct_hours_in_wocl: float
    pct_hours_at_or_below_77: float


@dataclass(frozen=True, slots=True)
class FRMSRiskClassification:
    """Risk classification suitable for an FRMS dashboard."""

    severity: str
    likelihood: str
    risk_level: str
    rationale: str


@dataclass(frozen=True, slots=True)
class USAFCrewRestPolicy:
    """USAF crew rest policy parameters (AFMAN 11-202V3 baseline)."""

    standard_crew_rest_hours: float = 12.0
    reduced_crew_rest_hours: float = 10.0
    min_uninterrupted_sleep_hours: float = 8.0


@dataclass(frozen=True, slots=True)
class USAFCrewRestAssessment:
    """Assessment of crew rest compliance for a planned FDP."""

    crew_rest_hours: float
    required_crew_rest_hours: float
    planned_sleep_opportunity_hours: float
    required_sleep_opportunity_hours: float
    compliant: bool
    notes: str


@dataclass(frozen=True, slots=True)
class FRMSAlert:
    """A rule-based FRMS alert suitable for mission dashboards."""

    level: str  # "info" | "warning" | "critical"
    code: str
    message: str
    rationale: str


def _validate_thresholds(th: FRMSThresholds) -> None:
    if not np.isfinite(th.low_risk_min_effectiveness):
        raise ValueError("low_risk_min_effectiveness must be finite")
    if not np.isfinite(th.high_risk_max_effectiveness):
        raise ValueError("high_risk_max_effectiveness must be finite")
    if not np.isfinite(th.severe_impairment_max_effectiveness):
        raise ValueError("severe_impairment_max_effectiveness must be finite")
    if th.low_risk_min_effectiveness <= th.high_risk_max_effectiveness:
        raise ValueError("low_risk_min_effectiveness must be > high_risk_max_effectiveness")
    if th.high_risk_max_effectiveness <= th.severe_impairment_max_effectiveness:
        raise ValueError("high_risk_max_effectiveness must be > severe_impairment_max_effectiveness")
    if not (0 <= th.wocl_start_hour <= 23) or not (0 <= th.wocl_end_hour <= 23):
        raise ValueError("wocl_start_hour and wocl_end_hour must be in 0..23")


def compute_wocl_mask(
    datetimes: Sequence[_dt.datetime],
    *,
    wocl_start_hour: int = 2,
    wocl_end_hour: int = 6,
) -> list[bool]:
    """Return a boolean mask for WOCL membership for each datetime.

    WOCL is treated as an hour-of-day window in local time:
    - inclusive of start hour
    - exclusive of end hour

    Args:
        datetimes: Sequence of datetimes (local time).
        wocl_start_hour: Start hour (0..23).
        wocl_end_hour: End hour (0..23).

    Returns:
        List[bool] of same length as datetimes.
    """
    if not (0 <= wocl_start_hour <= 23) or not (0 <= wocl_end_hour <= 23):
        raise ValueError("wocl_start_hour and wocl_end_hour must be in 0..23")

    mask: list[bool] = []
    if wocl_start_hour == wocl_end_hour:
        # Degenerate: whole day or empty; treat as empty to be safe.
        return [False for _ in datetimes]

    crosses_midnight = wocl_start_hour > wocl_end_hour
    for dt in datetimes:
        hour = int(dt.hour)
        in_window = (
            (hour >= wocl_start_hour or hour < wocl_end_hour)
            if crosses_midnight
            else (wocl_start_hour <= hour < wocl_end_hour)
        )
        mask.append(bool(in_window))
    return mask


def compute_duty_mask(
    datetimes: Sequence[_dt.datetime],
    *,
    has_work_schedule: bool,
    work_start_hour: int,
    work_end_hour: int,
    include_weekends: bool = False,
) -> list[bool]:
    """Return a boolean mask for duty membership for each datetime.

    The SAFTE tab models a repeating daily schedule. We interpret "work schedule"
    as an on-duty window in local time (hour-of-day), optionally excluding weekends.

    Args:
        datetimes: Sequence of datetimes (local time).
        has_work_schedule: If False, returns all True (risk computed for whole timeline).
        work_start_hour: Duty start hour (0..23).
        work_end_hour: Duty end hour (0..23). May be < start for overnight duty.
        include_weekends: If False, mask weekends (Sat/Sun) as off-duty.

    Returns:
        List[bool] mask.
    """
    if not (0 <= work_start_hour <= 23) or not (0 <= work_end_hour <= 23):
        raise ValueError("work_start_hour and work_end_hour must be in 0..23")

    if not has_work_schedule:
        return [True for _ in datetimes]

    crosses_midnight = work_start_hour > work_end_hour
    mask: list[bool] = []
    for dt in datetimes:
        if not include_weekends and dt.weekday() >= 5:
            mask.append(False)
            continue
        hour = int(dt.hour)
        in_window = (
            (hour >= work_start_hour or hour < work_end_hour)
            if crosses_midnight
            else (work_start_hour <= hour < work_end_hour)
        )
        mask.append(bool(in_window))
    return mask


def compute_frms_exposure_metrics(
    *,
    datetimes: Sequence[_dt.datetime],
    effectiveness: Sequence[float],
    scope_mask: Sequence[bool],
    wocl_mask: Sequence[bool],
    thresholds: FRMSThresholds = FRMSThresholds(),
    hours_per_sample: float = 1.0,
) -> FRMSExposureMetrics:
    """Compute FRMS-style exposure metrics for a (datetime, effectiveness) series.

    Args:
        datetimes: Datetimes aligned to effectiveness samples.
        effectiveness: SAFTE effectiveness (%), may include NaN.
        scope_mask: Mask defining the "in-scope" period (e.g., duty hours).
        wocl_mask: Mask defining WOCL membership.
        thresholds: Threshold configuration.
        hours_per_sample: Sampling interval in hours (default 1.0 for hourly series).

    Returns:
        FRMSExposureMetrics.
    """
    _validate_thresholds(thresholds)
    if hours_per_sample <= 0 or not np.isfinite(hours_per_sample):
        raise ValueError("hours_per_sample must be a positive finite number")
    if len(datetimes) != len(effectiveness):
        raise ValueError("datetimes and effectiveness must have the same length")
    if len(scope_mask) != len(effectiveness) or len(wocl_mask) != len(effectiveness):
        raise ValueError("scope_mask/wocl_mask must match effectiveness length")

    eff = np.asarray(list(effectiveness), dtype=float)
    finite = np.isfinite(eff)
    scope = np.asarray(list(scope_mask), dtype=bool)
    wocl = np.asarray(list(wocl_mask), dtype=bool)

    in_scope = finite & scope
    samples_total = int(len(eff))
    samples_in_scope = int(np.sum(in_scope))
    hours_in_scope = float(samples_in_scope) * float(hours_per_sample)
    hours_in_wocl = float(np.sum(in_scope & wocl)) * float(hours_per_sample)

    if samples_in_scope == 0:
        return FRMSExposureMetrics(
            samples_total=samples_total,
            samples_in_scope=0,
            hours_in_scope=0.0,
            hours_in_wocl=0.0,
            min_effectiveness=None,
            mean_effectiveness=None,
            hours_below_90=0.0,
            hours_at_or_below_77=0.0,
            hours_at_or_below_70=0.0,
            pct_hours_in_wocl=0.0,
            pct_hours_at_or_below_77=0.0,
        )

    eff_scope = eff[in_scope]
    min_eff = float(np.min(eff_scope))
    mean_eff = float(np.mean(eff_scope))

    hours_below_90 = float(np.sum(eff_scope < thresholds.low_risk_min_effectiveness)) * float(hours_per_sample)
    hours_at_or_below_77 = float(np.sum(eff_scope <= thresholds.high_risk_max_effectiveness)) * float(hours_per_sample)
    hours_at_or_below_70 = float(np.sum(eff_scope <= thresholds.severe_impairment_max_effectiveness)) * float(hours_per_sample)

    pct_hours_in_wocl = float(hours_in_wocl / hours_in_scope * 100.0) if hours_in_scope > 0 else 0.0
    pct_hours_at_or_below_77 = float(hours_at_or_below_77 / hours_in_scope * 100.0) if hours_in_scope > 0 else 0.0

    return FRMSExposureMetrics(
        samples_total=samples_total,
        samples_in_scope=samples_in_scope,
        hours_in_scope=hours_in_scope,
        hours_in_wocl=hours_in_wocl,
        min_effectiveness=min_eff,
        mean_effectiveness=mean_eff,
        hours_below_90=hours_below_90,
        hours_at_or_below_77=hours_at_or_below_77,
        hours_at_or_below_70=hours_at_or_below_70,
        pct_hours_in_wocl=pct_hours_in_wocl,
        pct_hours_at_or_below_77=pct_hours_at_or_below_77,
    )


def classify_frms_risk(
    exposure: FRMSExposureMetrics,
    *,
    thresholds: FRMSThresholds = FRMSThresholds(),
) -> FRMSRiskClassification:
    """Classify FRMS risk using a simple 5×5 SMS-style matrix.

    The matrix is intentionally conservative and meant to be *adjustable* at the UI layer.
    """
    _validate_thresholds(thresholds)

    if exposure.hours_in_scope <= 0 or exposure.min_effectiveness is None:
        return FRMSRiskClassification(
            severity="Unknown",
            likelihood="Unknown",
            risk_level="Unknown",
            rationale="No in-scope effectiveness samples available for classification.",
        )

    min_eff = float(exposure.min_effectiveness)
    pct_hi = float(exposure.pct_hours_at_or_below_77)

    # Severity bins (based on worst-case effectiveness in-scope)
    if min_eff >= thresholds.low_risk_min_effectiveness:
        severity = "Negligible"
    elif min_eff >= 85.0:
        severity = "Minor"
    elif min_eff > thresholds.high_risk_max_effectiveness:
        severity = "Major"
    elif min_eff > thresholds.severe_impairment_max_effectiveness:
        severity = "Hazardous"
    else:
        severity = "Catastrophic"

    # Likelihood bins (based on % of in-scope time at/under the high-risk threshold)
    if pct_hi <= 0.0:
        likelihood = "Rare"
    elif pct_hi <= 5.0:
        likelihood = "Unlikely"
    elif pct_hi <= 15.0:
        likelihood = "Possible"
    elif pct_hi <= 30.0:
        likelihood = "Likely"
    else:
        likelihood = "Almost certain"

    likelihood_order = ["Rare", "Unlikely", "Possible", "Likely", "Almost certain"]
    idx = likelihood_order.index(likelihood)

    # Conservative 5×5 risk matrix
    matrix: dict[str, list[str]] = {
        "Negligible": ["Low", "Low", "Low", "Medium", "Medium"],
        "Minor": ["Low", "Low", "Medium", "High", "High"],
        "Major": ["Low", "Medium", "High", "High", "Extreme"],
        "Hazardous": ["Medium", "High", "High", "Extreme", "Extreme"],
        "Catastrophic": ["High", "High", "Extreme", "Extreme", "Extreme"],
    }
    risk_level = matrix[severity][idx]

    rationale = (
        f"Min effectiveness={min_eff:.1f}%; "
        f"time ≤{thresholds.high_risk_max_effectiveness:.0f}% = {pct_hi:.1f}% of in-scope hours; "
        f"WOCL exposure={exposure.pct_hours_in_wocl:.1f}%."
    )
    return FRMSRiskClassification(
        severity=severity,
        likelihood=likelihood,
        risk_level=risk_level,
        rationale=rationale,
    )


def assess_usaf_crew_rest(
    *,
    crew_rest_start_local: _dt.datetime,
    fdp_start_local: _dt.datetime,
    planned_sleep_opportunity_hours: float,
    continuous_ops_reduced_rest: bool = False,
    policy: USAFCrewRestPolicy = USAFCrewRestPolicy(),
) -> USAFCrewRestAssessment:
    """Assess USAF crew rest compliance for the next Flight Duty Period (FDP).

    This function implements a simplified check based on AFMAN 11-202V3:
    - Standard crew rest: minimum 12 non-duty hours before FDP.
    - Continuous ops exception: may reduce crew rest to minimum 10 hours (with constraints).
    - Crew rest should include opportunity for ≥8 hours uninterrupted sleep.

    Args:
        crew_rest_start_local: Time when all official duties completed and crew rest begins.
        fdp_start_local: Planned start time of the FDP.
        planned_sleep_opportunity_hours: Planned uninterrupted sleep opportunity within crew rest.
        continuous_ops_reduced_rest: Whether the continuous-ops reduced rest allowance applies.
        policy: Policy parameters.

    Returns:
        USAFCrewRestAssessment.
    """
    if fdp_start_local <= crew_rest_start_local:
        raise ValueError("fdp_start_local must be after crew_rest_start_local")
    if planned_sleep_opportunity_hours < 0 or not np.isfinite(planned_sleep_opportunity_hours):
        raise ValueError("planned_sleep_opportunity_hours must be a non-negative finite number")

    required_rest = (
        float(policy.reduced_crew_rest_hours)
        if continuous_ops_reduced_rest
        else float(policy.standard_crew_rest_hours)
    )
    required_sleep = float(policy.min_uninterrupted_sleep_hours)

    rest_hours = float((fdp_start_local - crew_rest_start_local).total_seconds() / 3600.0)
    rest_ok = rest_hours >= required_rest
    sleep_ok = planned_sleep_opportunity_hours >= required_sleep

    compliant = bool(rest_ok and sleep_ok)
    notes_parts: list[str] = []
    if continuous_ops_reduced_rest:
        notes_parts.append("Reduced crew rest selected (continuous operations allowance).")
    if not rest_ok:
        notes_parts.append(f"Crew rest shortfall: {required_rest:.1f}h required, {rest_hours:.1f}h provided.")
    if not sleep_ok:
        notes_parts.append(
            f"Sleep opportunity shortfall: {required_sleep:.1f}h uninterrupted required, "
            f"{planned_sleep_opportunity_hours:.1f}h planned."
        )
    if not notes_parts:
        notes_parts.append("Crew rest and sleep opportunity meet baseline AFMAN 11-202V3 thresholds.")

    return USAFCrewRestAssessment(
        crew_rest_hours=rest_hours,
        required_crew_rest_hours=required_rest,
        planned_sleep_opportunity_hours=float(planned_sleep_opportunity_hours),
        required_sleep_opportunity_hours=required_sleep,
        compliant=compliant,
        notes=" ".join(notes_parts),
    )


def compute_frms_alerts(
    *,
    exposure: FRMSExposureMetrics,
    classification: FRMSRiskClassification,
    crew_rest: USAFCrewRestAssessment | None,
    thresholds: FRMSThresholds = FRMSThresholds(),
) -> list[FRMSAlert]:
    """Compute a small set of deterministic, rule-based FRMS alerts.

    This complements the FRMS dashboard by providing a "why it triggered" list
    suitable for operational briefings and exports.

    Args:
        exposure: Exposure metrics from `compute_frms_exposure_metrics`.
        classification: Risk classification from `classify_frms_risk`.
        crew_rest: Optional crew rest assessment from `assess_usaf_crew_rest`.
        thresholds: Threshold settings.

    Returns:
        List of alerts, highest priority first.
    """
    _validate_thresholds(thresholds)

    alerts: list[FRMSAlert] = []

    # Classification-level alerts
    risk = str(classification.risk_level or "Unknown")
    if risk in {"Extreme"}:
        alerts.append(
            FRMSAlert(
                level="critical",
                code="risk_extreme",
                message="FRMS risk matrix classifies this scenario as EXTREME.",
                rationale=classification.rationale,
            )
        )
    elif risk in {"High"}:
        alerts.append(
            FRMSAlert(
                level="warning",
                code="risk_high",
                message="FRMS risk matrix classifies this scenario as HIGH.",
                rationale=classification.rationale,
            )
        )

    # Exposure threshold alerts
    if exposure.min_effectiveness is not None:
        if exposure.min_effectiveness <= thresholds.severe_impairment_max_effectiveness:
            alerts.append(
                FRMSAlert(
                    level="critical",
                    code="min_eff_severe",
                    message=f"Min in-scope effectiveness ≤{thresholds.severe_impairment_max_effectiveness:.0f}%.",
                    rationale=f"Min effectiveness was {exposure.min_effectiveness:.1f}% during in-scope hours.",
                )
            )
        elif exposure.min_effectiveness <= thresholds.high_risk_max_effectiveness:
            alerts.append(
                FRMSAlert(
                    level="warning",
                    code="min_eff_high_risk",
                    message=f"Min in-scope effectiveness ≤{thresholds.high_risk_max_effectiveness:.0f}%.",
                    rationale=f"Min effectiveness was {exposure.min_effectiveness:.1f}% during in-scope hours.",
                )
            )

    if exposure.hours_at_or_below_77 > 0:
        lvl = "critical" if exposure.pct_hours_at_or_below_77 >= 30.0 else "warning"
        alerts.append(
            FRMSAlert(
                level=lvl,
                code="time_below_77",
                message=f"Time at/under {thresholds.high_risk_max_effectiveness:.0f}% effectiveness detected.",
                rationale=(
                    f"{exposure.hours_at_or_below_77:.1f} h "
                    f"({exposure.pct_hours_at_or_below_77:.1f}% of in-scope time) at/under "
                    f"{thresholds.high_risk_max_effectiveness:.0f}%."
                ),
            )
        )

    if exposure.pct_hours_in_wocl >= 25.0 and exposure.hours_in_scope > 0:
        alerts.append(
            FRMSAlert(
                level="warning",
                code="wocl_exposure",
                message="High WOCL exposure during in-scope hours.",
                rationale=f"WOCL exposure was {exposure.pct_hours_in_wocl:.1f}% of in-scope time.",
            )
        )

    # Crew rest compliance alerts
    if crew_rest is not None and not crew_rest.compliant:
        alerts.append(
            FRMSAlert(
                level="critical",
                code="crew_rest_noncompliant",
                message="USAF crew rest check is NOT compliant (AFMAN 11-202V3 baseline).",
                rationale=crew_rest.notes,
            )
        )

    # Sort by severity order (critical > warning > info) and keep deterministic ordering.
    order = {"critical": 0, "warning": 1, "info": 2}
    alerts = sorted(alerts, key=lambda a: (order.get(a.level, 9), a.code))
    return alerts

