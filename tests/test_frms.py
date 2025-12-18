from __future__ import annotations

import datetime as dt

import pytest

from app.frms import (
    FRMSAlert,
    FRMSExposureMetrics,
    FRMSThresholds,
    USAFCrewRestPolicy,
    assess_usaf_crew_rest,
    classify_frms_risk,
    compute_frms_alerts,
    compute_duty_mask,
    compute_frms_exposure_metrics,
    compute_wocl_mask,
)


def test_compute_wocl_mask_simple_window() -> None:
    base = dt.datetime(2025, 1, 1, 0, 0, 0)
    dts = [base.replace(hour=h) for h in range(0, 8)]
    mask = compute_wocl_mask(dts, wocl_start_hour=2, wocl_end_hour=6)
    assert mask == [False, False, True, True, True, True, False, False]


def test_compute_duty_mask_weekday_only() -> None:
    # Friday (weekday=4) and Saturday (weekday=5)
    fri = dt.datetime(2025, 1, 3, 10, 0, 0)
    sat = dt.datetime(2025, 1, 4, 10, 0, 0)
    mask = compute_duty_mask(
        [fri, sat],
        has_work_schedule=True,
        work_start_hour=9,
        work_end_hour=17,
        include_weekends=False,
    )
    assert mask == [True, False]


def test_compute_frms_exposure_metrics_counts_hours() -> None:
    dts = [dt.datetime(2025, 1, 1, h, 0, 0) for h in range(6)]
    eff = [95.0, 92.0, 88.0, 76.0, 69.0, 91.0]
    scope = [True] * 6
    wocl = compute_wocl_mask(dts, wocl_start_hour=2, wocl_end_hour=6)
    metrics = compute_frms_exposure_metrics(
        datetimes=dts,
        effectiveness=eff,
        scope_mask=scope,
        wocl_mask=wocl,
        thresholds=FRMSThresholds(),
        hours_per_sample=1.0,
    )
    assert metrics.hours_in_scope == 6.0
    assert metrics.hours_in_wocl == 4.0  # hours 2,3,4,5
    assert metrics.hours_below_90 == 3.0  # 88, 76, 69
    assert metrics.hours_at_or_below_77 == 2.0  # 76, 69
    assert metrics.hours_at_or_below_70 == 1.0  # 69
    assert metrics.min_effectiveness == 69.0


def test_classify_frms_risk_nominal_low() -> None:
    exposure = FRMSExposureMetrics(
        samples_total=24,
        samples_in_scope=24,
        hours_in_scope=24.0,
        hours_in_wocl=4.0,
        min_effectiveness=92.0,
        mean_effectiveness=95.0,
        hours_below_90=0.0,
        hours_at_or_below_77=0.0,
        hours_at_or_below_70=0.0,
        pct_hours_in_wocl=16.7,
        pct_hours_at_or_below_77=0.0,
    )
    cls = classify_frms_risk(exposure, thresholds=FRMSThresholds())
    assert cls.risk_level in {"Low", "Medium"}
    assert cls.severity == "Negligible"
    assert cls.likelihood == "Rare"


def test_assess_usaf_crew_rest_compliant_standard() -> None:
    start = dt.datetime(2025, 1, 1, 20, 0, 0)
    fdp = dt.datetime(2025, 1, 2, 8, 0, 0)  # 12h later
    res = assess_usaf_crew_rest(
        crew_rest_start_local=start,
        fdp_start_local=fdp,
        planned_sleep_opportunity_hours=8.0,
        continuous_ops_reduced_rest=False,
        policy=USAFCrewRestPolicy(),
    )
    assert res.compliant is True
    assert pytest.approx(res.crew_rest_hours, rel=1e-6) == 12.0


def test_assess_usaf_crew_rest_not_compliant_short_rest() -> None:
    start = dt.datetime(2025, 1, 1, 22, 0, 0)
    fdp = dt.datetime(2025, 1, 2, 8, 0, 0)  # 10h later
    res = assess_usaf_crew_rest(
        crew_rest_start_local=start,
        fdp_start_local=fdp,
        planned_sleep_opportunity_hours=8.0,
        continuous_ops_reduced_rest=False,
        policy=USAFCrewRestPolicy(),
    )
    assert res.compliant is False
    assert res.required_crew_rest_hours == 12.0


def test_assess_usaf_crew_rest_continuous_ops_allows_10h() -> None:
    start = dt.datetime(2025, 1, 1, 22, 0, 0)
    fdp = dt.datetime(2025, 1, 2, 8, 0, 0)  # 10h later
    res = assess_usaf_crew_rest(
        crew_rest_start_local=start,
        fdp_start_local=fdp,
        planned_sleep_opportunity_hours=8.0,
        continuous_ops_reduced_rest=True,
        policy=USAFCrewRestPolicy(),
    )
    assert res.compliant is True
    assert res.required_crew_rest_hours == 10.0


def test_assess_usaf_crew_rest_invalid_order_raises() -> None:
    start = dt.datetime(2025, 1, 2, 8, 0, 0)
    fdp = dt.datetime(2025, 1, 1, 20, 0, 0)
    with pytest.raises(ValueError):
        _ = assess_usaf_crew_rest(
            crew_rest_start_local=start,
            fdp_start_local=fdp,
            planned_sleep_opportunity_hours=8.0,
        )


def test_compute_frms_alerts_flags_severe_exposure_and_crew_rest() -> None:
    exposure = FRMSExposureMetrics(
        samples_total=24,
        samples_in_scope=24,
        hours_in_scope=24.0,
        hours_in_wocl=8.0,
        min_effectiveness=68.0,
        mean_effectiveness=80.0,
        hours_below_90=12.0,
        hours_at_or_below_77=10.0,
        hours_at_or_below_70=3.0,
        pct_hours_in_wocl=33.3,
        pct_hours_at_or_below_77=41.7,
    )
    cls = classify_frms_risk(exposure, thresholds=FRMSThresholds())
    crew_rest = assess_usaf_crew_rest(
        crew_rest_start_local=dt.datetime(2025, 1, 1, 23, 0, 0),
        fdp_start_local=dt.datetime(2025, 1, 2, 8, 0, 0),  # 9h later
        planned_sleep_opportunity_hours=6.0,
        continuous_ops_reduced_rest=False,
        policy=USAFCrewRestPolicy(),
    )
    alerts = compute_frms_alerts(
        exposure=exposure,
        classification=cls,
        crew_rest=crew_rest,
        thresholds=FRMSThresholds(),
    )
    assert alerts
    assert all(isinstance(a, FRMSAlert) for a in alerts)
    codes = {a.code for a in alerts}
    assert "min_eff_severe" in codes
    assert "crew_rest_noncompliant" in codes

