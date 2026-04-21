"""Tests for app/sleep_core.py — Sleep metrics, readiness gate, correlations.

Covers:
- Stage balance derivation (partial/complete data, zero-total guards)
- Sleep debt (window scaling, partial nulls)
- Sleep Regularity Index (Lunsford-Avery 2018) — identical consecutive
  nights → SRI ~100; shifted nights → lower SRI
- SpO2 screening bands (NORMAL / MILD / ELEVATED / HIGH_FLAG)
- Operational gate (GO / GO_MONITOR / CAUTION / NO_GO)
- Correlation engine (Pearson, Spearman) with and without scipy
- BH FDR adjustment

Author: Dr. Diego Leonel Malpica Hincapié, MD
"""

from __future__ import annotations

import math
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.sleep_core import (  # noqa: E402
    MIN_NIGHTS_FOR_STATS,
    SLEEP_EFFICIENCY_OPTIMAL,
    SPO2_LOW_NIGHT_THRESHOLD,
    NightlyRecord,
    SleepReadinessBand,
    SpO2ScreeningBand,
    _bh_fdr,
    _rank,
    build_records_from_raw,
    compute_correlations,
    compute_sleep_debt,
    compute_sleep_regularity,
    compute_spo2_screening,
    compute_stage_balance,
    operational_sleep_gate,
    summarise,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _night(
    d: date,
    hours: float = 7.5,
    efficiency: float = 0.88,
    score: float = 80.0,
    deep: int | None = 90,
    rem: int | None = 100,
    light: int | None = 220,
    awake: int | None = 20,
    rmssd: float = 42.0,
    rhr: float = 58.0,
    spo2: float = 96.0,
    resp_sleep: float = 14.0,
    start_hour: int = 23,
    start_minute: int = 0,
) -> NightlyRecord:
    sleep_start = datetime(d.year, d.month, d.day, start_hour, start_minute, tzinfo=timezone.utc)
    # Compute end from hours
    sleep_end = sleep_start + timedelta(hours=hours)
    return NightlyRecord(
        metric_date=d,
        sleep_duration_hours=hours,
        sleep_efficiency=efficiency,
        sleep_score=score,
        sleep_start_utc=sleep_start,
        sleep_end_utc=sleep_end,
        sleep_deep_minutes=deep,
        sleep_rem_minutes=rem,
        sleep_light_minutes=light,
        sleep_awake_minutes=awake,
        hrv_rmssd_ms=rmssd,
        resting_hr_bpm=rhr,
        avg_spo2=spo2,
        avg_respiration_sleep=resp_sleep,
    )


def _series(n: int = 14, **common) -> list[NightlyRecord]:
    base = date(2026, 4, 1)
    return [_night(base + timedelta(days=i), **common) for i in range(n)]


# ---------------------------------------------------------------------------
# Stage balance
# ---------------------------------------------------------------------------

class TestStageBalance:
    def test_complete_night_pct(self):
        n = _night(date(2026, 4, 1), deep=90, rem=100, light=200, awake=30)  # total 420 min
        sb = compute_stage_balance(n)
        assert sb.total_minutes == 420
        assert sb.deep_pct == pytest.approx(90 / 420)
        assert sb.rem_pct == pytest.approx(100 / 420)
        assert sb.deep_plus_rem_minutes == 190
        assert sb.deep_plus_rem_pct == pytest.approx(190 / 420)
        assert sb.deep_to_rem_ratio == pytest.approx(0.9, rel=1e-6)

    def test_missing_stages_return_none_total(self):
        n = _night(date(2026, 4, 1), deep=None, rem=None, light=None, awake=None)
        sb = compute_stage_balance(n)
        assert sb.total_minutes is None
        assert sb.deep_pct is None

    def test_partial_stages(self):
        n = _night(date(2026, 4, 1), deep=80, rem=None, light=220, awake=20)
        sb = compute_stage_balance(n)
        assert sb.total_minutes == 320
        assert sb.deep_pct == pytest.approx(80 / 320)
        assert sb.rem_pct is None


# ---------------------------------------------------------------------------
# Sleep debt
# ---------------------------------------------------------------------------

class TestSleepDebt:
    def test_zero_debt_when_meeting_target(self):
        records = _series(7, hours=7.5)
        d = compute_sleep_debt(records, typical_target_hours=7.5, window_nights=7)
        assert d.cumulative_debt_hours == pytest.approx(0.0)
        assert d.observed_mean_hours == pytest.approx(7.5)
        assert d.target_total_hours == pytest.approx(52.5)

    def test_linear_debt_accumulation(self):
        records = _series(7, hours=6.0)
        d = compute_sleep_debt(records, typical_target_hours=8.0, window_nights=7)
        assert d.cumulative_debt_hours == pytest.approx(7 * 2.0)

    def test_window_clipping_to_recent_nights(self):
        records = _series(30, hours=7.5)
        d = compute_sleep_debt(records, window_nights=7)
        assert d.window_nights == 7
        assert len(d.nightly_deficits) == 7

    def test_nulls_skipped(self):
        # 3 nights null, 4 nights at 6.0 h vs 8 h target → debt = 4 * 2 = 8
        base = date(2026, 4, 1)
        rs = []
        for i in range(3):
            r = _night(base + timedelta(days=i))
            r = NightlyRecord(**{**r.__dict__, "sleep_duration_hours": None})
            rs.append(r)
        for i in range(4):
            rs.append(_night(base + timedelta(days=3 + i), hours=6.0))
        d = compute_sleep_debt(rs, typical_target_hours=8.0, window_nights=7)
        assert d.cumulative_debt_hours == pytest.approx(8.0)


# ---------------------------------------------------------------------------
# Sleep regularity (Lunsford-Avery 2018)
# ---------------------------------------------------------------------------

class TestRegularity:
    def test_identical_schedule_gives_high_sri(self):
        records = _series(14, hours=8.0, start_hour=23, start_minute=0)
        reg = compute_sleep_regularity(records, window_nights=14)
        # Identical bed/wake → SRI ~100; allow minor epoch boundary rounding
        assert reg.sri_percent is not None
        assert reg.sri_percent > 95.0
        assert reg.bedtime_sd_minutes == pytest.approx(0.0, abs=0.001)
        assert reg.waketime_sd_minutes == pytest.approx(0.0, abs=0.001)

    def test_alternating_schedule_lowers_sri(self):
        base = date(2026, 4, 1)
        rs: list[NightlyRecord] = []
        for i in range(14):
            # Alternate 23:00→07:00 and 03:00→11:00 (4-hour shift)
            if i % 2 == 0:
                rs.append(_night(base + timedelta(days=i), hours=8.0, start_hour=23, start_minute=0))
            else:
                rs.append(_night(base + timedelta(days=i), hours=8.0, start_hour=3, start_minute=0))
        reg = compute_sleep_regularity(rs, window_nights=14)
        assert reg.sri_percent is not None
        assert reg.sri_percent < 70.0
        assert reg.bedtime_sd_minutes is not None
        assert reg.bedtime_sd_minutes > 30.0

    def test_missing_bedtimes_skipped(self):
        base = date(2026, 4, 1)
        rs = _series(10, hours=8.0)
        # Null out one start_utc
        mid = 5
        rs[mid] = NightlyRecord(**{**rs[mid].__dict__, "sleep_start_utc": None})
        reg = compute_sleep_regularity(rs, window_nights=10)
        assert reg.n_pairs >= 1
        assert reg.sri_percent is not None


# ---------------------------------------------------------------------------
# SpO2 screening
# ---------------------------------------------------------------------------

class TestSpO2Screening:
    def test_normal_all_high_spo2(self):
        records = _series(7, spo2=97.0)
        s = compute_spo2_screening(records)
        assert s.band == SpO2ScreeningBand.NORMAL
        assert s.low_spo2_nights == 0

    def test_mild_flag_one_low_night(self):
        base = date(2026, 4, 1)
        rs = [_night(base + timedelta(days=i), spo2=97.0) for i in range(7)]
        rs[3] = NightlyRecord(**{**rs[3].__dict__, "avg_spo2": 91.5})
        s = compute_spo2_screening(rs)
        assert s.band == SpO2ScreeningBand.MILD_FLAG
        assert s.low_spo2_nights == 1

    def test_elevated_flag_two_low_nights(self):
        base = date(2026, 4, 1)
        rs = [_night(base + timedelta(days=i), spo2=97.0) for i in range(7)]
        rs[2] = NightlyRecord(**{**rs[2].__dict__, "avg_spo2": 90.0})
        rs[5] = NightlyRecord(**{**rs[5].__dict__, "avg_spo2": 91.0})
        s = compute_spo2_screening(rs)
        assert s.band == SpO2ScreeningBand.ELEVATED_FLAG

    def test_high_flag_four_plus(self):
        base = date(2026, 4, 1)
        rs = [_night(base + timedelta(days=i), spo2=91.0) for i in range(7)]
        s = compute_spo2_screening(rs)
        assert s.band == SpO2ScreeningBand.HIGH_FLAG


# ---------------------------------------------------------------------------
# Operational gate
# ---------------------------------------------------------------------------

class TestOperationalGate:
    def test_go_when_all_normal(self):
        records = _series(14, hours=7.5, spo2=97.0, start_hour=23, start_minute=0)
        g = operational_sleep_gate(records)
        assert g.decision == SleepReadinessBand.GO

    def test_caution_moderate_debt(self):
        records = _series(14, hours=6.5, spo2=97.0)  # 1 h deficit/night × 7 = 7 h debt
        g = operational_sleep_gate(records)
        assert g.decision in (SleepReadinessBand.CAUTION, SleepReadinessBand.GO_MONITOR)

    def test_no_go_hard_floor_last_night(self):
        base = date(2026, 4, 1)
        rs = _series(6, hours=7.5)
        rs.append(_night(base + timedelta(days=6), hours=4.0))  # last night too short
        g = operational_sleep_gate(rs)
        assert g.decision == SleepReadinessBand.NO_GO

    def test_caution_escalated_by_low_sri(self):
        # Dramatically shifting schedule (12h flipped) pushes SRI below the
        # 40% CAUTION threshold. A 3-hour shift alone produces SRI ~50%,
        # which is low regularity but does not cross the operational gate.
        base = date(2026, 4, 1)
        rs = []
        for i in range(14):
            rs.append(_night(
                base + timedelta(days=i),
                hours=7.0,
                spo2=97.0,
                start_hour=23 if i % 2 == 0 else 11,  # 12h flip
            ))
        g = operational_sleep_gate(rs)
        assert g.decision in (
            SleepReadinessBand.CAUTION,
            SleepReadinessBand.GO_MONITOR,
            SleepReadinessBand.NO_GO,
        )
        assert any("Regularity" in r or "regular" in r.lower() for r in g.reasons)


# ---------------------------------------------------------------------------
# Correlation engine + BH FDR
# ---------------------------------------------------------------------------

class TestCorrelations:
    def test_perfect_positive_pearson(self):
        base = date(2026, 4, 1)
        rs = []
        for i in range(20):
            rs.append(_night(base + timedelta(days=i), hours=6.0 + i * 0.1, rmssd=30 + i * 2))
        out = compute_correlations(rs, pairs=[("sleep_duration_hours", "hrv_rmssd_ms")])
        assert out[0].n_nights == 20
        assert out[0].r is not None and out[0].r > 0.99
        assert out[0].p_value is not None and out[0].p_value < 0.001

    def test_default_pair_set_runs(self):
        rs = _series(20)
        out = compute_correlations(rs)
        assert len(out) == 8
        # Every pair should have q after FDR
        for c in out:
            if c.p_value is not None:
                assert c.fdr_q is not None

    def test_underpowered_flag(self):
        rs = _series(5)
        out = compute_correlations(rs, pairs=[("sleep_duration_hours", "hrv_rmssd_ms")])
        assert out[0].note is not None
        assert "Underpowered" in out[0].note

    def test_bh_fdr_monotonicity(self):
        ps = [0.001, 0.01, 0.04, 0.20, 0.30]
        qs = _bh_fdr(ps)
        # All qs finite, monotonic when sorted by raw p
        vals = [q for q in qs if q is not None]
        assert len(vals) == 5
        sorted_by_p = sorted(zip(ps, qs), key=lambda t: t[0])
        qs_sorted = [q for _, q in sorted_by_p]
        assert all(qs_sorted[i] <= qs_sorted[i + 1] + 1e-9 for i in range(len(qs_sorted) - 1))


# ---------------------------------------------------------------------------
# Builder + summary
# ---------------------------------------------------------------------------

class TestBuilderAndSummary:
    def test_build_from_raw_dicts(self):
        raw = [
            {
                "metric_date": "2026-04-01",
                "sleep_duration_hours": 7.5,
                "sleep_score": 82,
                "sleep_efficiency": 0.88,
                "sleep_start_utc": "2026-04-01T23:00:00Z",
                "sleep_end_utc": "2026-04-02T06:30:00Z",
                "sleep_deep_minutes": 90,
                "sleep_rem_minutes": 100,
                "sleep_light_minutes": 220,
                "sleep_awake_minutes": 20,
                "hrv_rmssd_ms": 44.0,
                "avg_spo2": 96.5,
            },
            {
                "metric_date": "2026-04-02",
                "sleep_duration_hours": 6.0,
                "sleep_score": 65,
                "hrv_rmssd_ms": 36.0,
            },
        ]
        rs = build_records_from_raw(raw)
        assert len(rs) == 2
        assert rs[0].metric_date == date(2026, 4, 1)
        assert rs[1].sleep_duration_hours == 6.0

    def test_summarise_happy_path(self):
        records = _series(14)
        s = summarise(records)
        assert s.n_nights_total == 14
        assert s.n_nights_with_duration == 14
        assert s.debt_7d.cumulative_debt_hours == pytest.approx(0.0)
        assert s.regularity_14d.sri_percent is not None
        assert s.readiness.decision == SleepReadinessBand.GO

    def test_summarise_empty(self):
        s = summarise([])
        assert s.n_nights_total == 0
        assert s.readiness.decision == SleepReadinessBand.CAUTION


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class TestInternals:
    def test_rank_handles_ties(self):
        ranks = _rank([1.0, 2.0, 2.0, 3.0])
        assert ranks == [1.0, 2.5, 2.5, 4.0]

    def test_bh_fdr_all_none(self):
        assert _bh_fdr([None, None, None]) == [None, None, None]
