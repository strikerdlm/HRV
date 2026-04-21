"""Tests for app/pvt_core.py — PVT scoring and gate logic.

Covers:
- Trial classification (valid, lapse, major lapse, false start, no response)
- Metric computation for PVT-B, PVT-5, PVT-10
- Scaling of pvt_lapses_3min across variants
- Operational gate thresholds against the scheduling_core integration point
- Edge cases: empty session, all lapses, all false starts

Author: Dr. Diego Leonel Malpica Hincapié, MD
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# Ensure app directory is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pvt_core import (
    FALSE_START_THRESHOLD_MS,
    MAJOR_LAPSE_THRESHOLD_MS,
    PVT_B_LAPSE_THRESHOLD_MS,
    PVT_5_LAPSE_THRESHOLD_MS,
    PVTTrial,
    PVTSession,
    PVTVariant,
    TrialKind,
    build_session_from_raw,
    classify_trial,
    generate_isi_schedule,
    operational_gate,
    score_session,
    score_trials,
    variant_defaults,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_trial(i: int, rt_ms, anticipatory=False) -> PVTTrial:
    return PVTTrial(
        index=i,
        isi_ms=2000.0,
        stimulus_onset_ms=float(i * 2500),
        rt_ms=rt_ms,
        anticipatory=anticipatory,
    )


def _alert_session(variant=PVTVariant.PVT_B) -> PVTSession:
    """80 alert trials with RT ~ 250 ms, no lapses, no false starts."""
    trials = tuple(_make_trial(i, 250.0 + (i % 5) * 10) for i in range(80))
    defaults = variant_defaults(variant)
    return PVTSession(variant=variant, duration_min=defaults["duration_min"], trials=trials)


def _fatigued_session_b(n_lapses=8) -> PVTSession:
    """PVT-B session with 80 trials, 8 lapses at 400 ms (above 355 ms threshold)."""
    alert = [_make_trial(i, 280.0 + (i % 3) * 10) for i in range(72)]
    lapses = [_make_trial(72 + i, 400.0) for i in range(n_lapses)]
    trials = tuple(alert + lapses)
    return PVTSession(variant=PVTVariant.PVT_B, duration_min=3.0, trials=trials)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

class TestClassification:
    def test_valid_trial(self):
        t = _make_trial(0, 280.0)
        assert classify_trial(t, PVT_B_LAPSE_THRESHOLD_MS) == TrialKind.VALID

    def test_lapse_at_threshold_pvt_b(self):
        t = _make_trial(0, PVT_B_LAPSE_THRESHOLD_MS)
        # Exactly at threshold counts as lapse
        assert classify_trial(t, PVT_B_LAPSE_THRESHOLD_MS) == TrialKind.LAPSE

    def test_lapse_above_threshold_pvt_5(self):
        t = _make_trial(0, 550.0)
        assert classify_trial(t, PVT_5_LAPSE_THRESHOLD_MS) == TrialKind.LAPSE

    def test_major_lapse(self):
        t = _make_trial(0, 1500.0)
        assert classify_trial(t, PVT_B_LAPSE_THRESHOLD_MS) == TrialKind.MAJOR_LAPSE
        assert classify_trial(t, PVT_5_LAPSE_THRESHOLD_MS) == TrialKind.MAJOR_LAPSE

    def test_false_start_by_rt(self):
        t = _make_trial(0, 50.0)   # sub-100 ms
        assert classify_trial(t, PVT_B_LAPSE_THRESHOLD_MS) == TrialKind.FALSE_START

    def test_false_start_by_anticipatory_flag(self):
        t = _make_trial(0, 200.0, anticipatory=True)
        assert classify_trial(t, PVT_B_LAPSE_THRESHOLD_MS) == TrialKind.FALSE_START

    def test_no_response(self):
        t = _make_trial(0, None)
        assert classify_trial(t, PVT_B_LAPSE_THRESHOLD_MS) == TrialKind.NO_RESPONSE


# ---------------------------------------------------------------------------
# Scoring — alert baseline session
# ---------------------------------------------------------------------------

class TestAlertSession:
    def test_no_lapses(self):
        m = score_session(_alert_session(PVTVariant.PVT_B))
        assert m["n_lapses"] == 0
        assert m["n_major_lapses"] == 0
        assert m["n_false_starts"] == 0
        assert m["n_no_response"] == 0
        assert m["pvt_lapses_3min"] == 0

    def test_mean_rt_within_alert_range(self):
        m = score_session(_alert_session(PVTVariant.PVT_B))
        # RT = 250..290 ms
        assert 250.0 <= m["mean_rt_ms"] <= 290.0
        assert 250.0 <= m["median_rt_ms"] <= 290.0

    def test_reciprocal_speed_positive(self):
        m = score_session(_alert_session(PVTVariant.PVT_B))
        assert m["mean_response_speed_per_s"] > 0
        # fastest 10% speed ≥ mean (by definition of "fastest")
        assert m["fastest_10pct_mean_speed_per_s"] >= m["mean_response_speed_per_s"]

    def test_transformed_lapses_zero(self):
        m = score_session(_alert_session(PVTVariant.PVT_B))
        # sqrt(0) + sqrt(0 + 1) = 1.0
        assert m["transformed_lapses"] == pytest.approx(1.0)

    def test_operational_gate_alert_go(self):
        m = score_session(_alert_session(PVTVariant.PVT_B))
        gate = operational_gate(m)
        assert gate["decision"] == "GO"


# ---------------------------------------------------------------------------
# Scoring — fatigued session
# ---------------------------------------------------------------------------

class TestFatiguedSession:
    def test_lapse_count_pvt_b(self):
        m = score_session(_fatigued_session_b(n_lapses=8))
        assert m["n_lapses"] == 8
        assert m["pvt_lapses_3min"] == 8

    def test_gate_caution_at_moderate_lapses(self):
        m = score_session(_fatigued_session_b(n_lapses=10))
        gate = operational_gate(m)
        assert gate["decision"] == "CAUTION"

    def test_gate_no_go_at_heavy_lapses(self):
        m = score_session(_fatigued_session_b(n_lapses=22))
        gate = operational_gate(m)
        assert gate["decision"] == "NO_GO"

    def test_transformed_lapses_basner_dinges(self):
        # Basner & Dinges 2011: sqrt(L) + sqrt(L + 1)
        m = score_session(_fatigued_session_b(n_lapses=4))
        expected = math.sqrt(4) + math.sqrt(5)
        assert m["transformed_lapses"] == pytest.approx(expected)


# ---------------------------------------------------------------------------
# PVT-5 scaling
# ---------------------------------------------------------------------------

class TestVariantScaling:
    def test_pvt_5_lapse_threshold_is_500(self):
        defaults = variant_defaults(PVTVariant.PVT_5)
        assert defaults["lapse_threshold_ms"] == PVT_5_LAPSE_THRESHOLD_MS == 500.0

    def test_pvt_b_lapse_threshold_is_355(self):
        defaults = variant_defaults(PVTVariant.PVT_B)
        assert defaults["lapse_threshold_ms"] == PVT_B_LAPSE_THRESHOLD_MS == 355.0

    def test_pvt_5_session_scales_lapses_to_3min_equivalent(self):
        # Build PVT-5 session with 10 lapses at 550 ms (above 500 ms threshold)
        alert = [_make_trial(i, 300.0) for i in range(90)]
        lapses = [_make_trial(90 + i, 550.0) for i in range(10)]
        sess = PVTSession(variant=PVTVariant.PVT_5, duration_min=5.0, trials=tuple(alert + lapses))
        m = score_session(sess)
        # 10 lapses in 5 min → scaled 6 lapses in 3 min (10 * 3/5)
        assert m["n_lapses"] == 10
        assert m["pvt_lapses_3min"] == 6


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_session(self):
        sess = PVTSession(variant=PVTVariant.PVT_B, duration_min=3.0, trials=())
        m = score_session(sess)
        assert m["n_trials"] == 0
        assert m["n_valid_trials"] == 0
        assert m["n_lapses"] == 0
        assert m["mean_rt_ms"] is None
        assert m["median_rt_ms"] is None
        assert m["pvt_lapses_3min"] == 0

    def test_all_false_starts(self):
        trials = tuple(_make_trial(i, 50.0) for i in range(20))
        sess = PVTSession(variant=PVTVariant.PVT_B, duration_min=3.0, trials=trials)
        m = score_session(sess)
        assert m["n_false_starts"] == 20
        assert m["n_valid_trials"] == 0
        assert m["n_lapses"] == 0

    def test_all_lapses(self):
        trials = tuple(_make_trial(i, 600.0) for i in range(25))
        sess = PVTSession(variant=PVTVariant.PVT_B, duration_min=3.0, trials=trials)
        m = score_session(sess)
        assert m["n_lapses"] == 25
        assert m["n_valid_trials"] == 25

    def test_no_response_counted(self):
        trials = (
            _make_trial(0, None),
            _make_trial(1, None),
            _make_trial(2, 300.0),
        )
        sess = PVTSession(variant=PVTVariant.PVT_B, duration_min=3.0, trials=trials)
        m = score_session(sess)
        assert m["n_no_response"] == 2
        assert m["n_valid_trials"] == 1


# ---------------------------------------------------------------------------
# Session builder + scoring convenience
# ---------------------------------------------------------------------------

class TestBuilders:
    def test_build_from_raw(self):
        raw = [
            {"index": 0, "isi_ms": 2000.0, "stimulus_onset_ms": 2000.0, "rt_ms": 280.0},
            {"index": 1, "isi_ms": 2500.0, "stimulus_onset_ms": 4800.0, "rt_ms": 310.0},
            {"index": 2, "isi_ms": 3000.0, "stimulus_onset_ms": 8100.0, "rt_ms": None},
            {"index": 3, "isi_ms": 1500.0, "stimulus_onset_ms": 10100.0, "rt_ms": 290.0,
             "anticipatory": False},
        ]
        sess = build_session_from_raw(raw, variant=PVTVariant.PVT_B, user_id="t1")
        assert len(sess.trials) == 4
        m = score_session(sess)
        assert m["n_valid_trials"] == 3
        assert m["n_no_response"] == 1

    def test_score_trials_convenience(self):
        trials = [_make_trial(i, 280.0) for i in range(20)]
        m = score_trials(trials, variant=PVTVariant.PVT_B)
        assert m["n_valid_trials"] == 20
        assert m["mean_rt_ms"] == pytest.approx(280.0)


# ---------------------------------------------------------------------------
# ISI schedule generator
# ---------------------------------------------------------------------------

class TestIsiSchedule:
    def test_pvt_b_schedule_within_range(self):
        schedule = generate_isi_schedule(PVTVariant.PVT_B, seed=42)
        for isi in schedule:
            assert 1000.0 <= isi <= 4000.0

    def test_pvt_5_schedule_within_range(self):
        schedule = generate_isi_schedule(PVTVariant.PVT_5, seed=42)
        for isi in schedule:
            assert 2000.0 <= isi <= 10000.0

    def test_schedule_reproducible_with_seed(self):
        s1 = generate_isi_schedule(PVTVariant.PVT_B, seed=123)
        s2 = generate_isi_schedule(PVTVariant.PVT_B, seed=123)
        assert s1 == s2
