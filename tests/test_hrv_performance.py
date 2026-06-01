"""Performance + correctness guards for HRV nonlinear metrics.

History:
- Entropy (SampEn/ApEn) and RQA were O(n^2) and uncapped -> advanced analysis of
  a multi-hour recording took 30+ minutes (or OOM). These tests assert the heavy
  nonlinear methods stay bounded regardless of recording length.
- ApEn and SampEn previously collapsed to the same value (a latent correctness
  bug). These tests pin both to their standard definitions (cross-checked against
  neurokit2) and assert they are distinct.
- MFDFA used a linear scale set whose size grew with n (O(n * scales)); these
  tests assert it stays bounded for very long recordings.
"""

from __future__ import annotations

import signal
import time

import numpy as np
import pytest

import app.hrv_core as hc


def _synth(n: int) -> np.ndarray:
    """Deterministic synthetic RR series (ms) with realistic variability."""
    rng = np.random.RandomState(0)
    base = 850.0 + 40.0 * np.sin(np.linspace(0, 12 * np.pi, n))
    return np.clip(base + rng.normal(0, 25, n), 400.0, 1400.0).astype(float)


class _Timeout(Exception):
    pass


def _run_with_timeout(fn, seconds: float):
    """Run fn, raising _Timeout if it exceeds `seconds` (main-thread Unix only)."""
    def _handler(signum, frame):
        raise _Timeout()

    old = signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return fn()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def _naive_standard_entropy(x: np.ndarray, m: int = 2, r_ratio: float = 0.2):
    """Reference implementation of the *standard* ApEn (Pincus) and SampEn
    (Richman & Moorman) definitions. Validated to match neurokit2 exactly.
    Returns (apen, sampen)."""
    x = np.asarray(x, dtype=float)
    n = x.size
    r = max(1e-9, r_ratio * float(np.std(x, ddof=0)))

    def _win(dim):
        return np.lib.stride_tricks.sliding_window_view(x, dim)

    # ApEn: self-matches included, mean of log of match densities.
    def _phi(dim):
        T = _win(dim)
        M = T.shape[0]
        total = 0.0
        for i in range(M):
            d = np.max(np.abs(T - T[i]), axis=1)
            c = int(np.count_nonzero(d <= r))  # includes self
            total += np.log(c / M)
        return total / M

    apen = float(_phi(m) - _phi(m + 1))

    # SampEn: no self-matches, matched template count (n - m) for both m and m+1.
    use = n - m

    def _pairs(dim):
        T = _win(dim)[:use]
        M = T.shape[0]
        cnt = 0
        for i in range(M - 1):
            d = np.max(np.abs(T[i + 1 :] - T[i]), axis=1)
            cnt += int(np.count_nonzero(d <= r))
        return cnt

    B = _pairs(m)
    A = _pairs(m + 1)
    sampen = float(-np.log(A / B)) if (A > 0 and B > 0) else 0.0
    return apen, sampen


# --------------------------------------------------------------------------- #
# Performance guards
# --------------------------------------------------------------------------- #


def test_entropy_metrics_bounded_for_long_series():
    """SampEn/ApEn must not blow up on long recordings (was O(n^2), pure Python).

    Bounded runtime is ~1 s; the regression took minutes, so a 10 s budget is a
    robust guard that is not sensitive to machine load.
    """
    rr = _synth(20000)  # ~4.7 h recording
    res = _run_with_timeout(lambda: hc.compute_entropy_metrics(rr, m=2, r_ratio=0.2), 10)
    assert np.isfinite(res["sampen"])
    assert np.isfinite(res["apen"])


def test_rqa_metrics_bounded_for_long_series():
    """RQA must not allocate an n x n matrix for large n (was O(n^2) memory).

    The internal cap keeps this ~3 s regardless of input size; uncapped at 50k it
    would need a ~40 GB matrix (OOM). A 10 s budget robustly proves the cap holds.
    """
    rr = _synth(50000)
    res = _run_with_timeout(lambda: hc.compute_rqa_metrics(rr), 10)
    assert np.isfinite(res["rqa_rr"])


def test_mfdfa_metrics_bounded_for_long_series():
    """MFDFA scale set must stay bounded (was O(n * scales) with scales ~ n)."""
    rr = _synth(100000)  # ~24 h recording; thinned scales -> ~1 s
    res = _run_with_timeout(lambda: hc.compute_mfdfa_metrics(rr), 10)
    assert np.isfinite(res["mfdfa_width"])


def test_comprehensive_advanced_bounded_for_long_series():
    """End-to-end advanced analysis must finish quickly even for multi-hour data."""
    rr = _synth(20000)
    res = _run_with_timeout(
        lambda: hc.compute_comprehensive_hrv(rr, include_advanced=True), 30
    )
    assert res["n_intervals"] == 20000  # full length still reported
    assert "sampen" in res and np.isfinite(res["sampen"])


# --------------------------------------------------------------------------- #
# Correctness guards
# --------------------------------------------------------------------------- #


def test_entropy_matches_standard_definition():
    """Vectorized ApEn/SampEn must equal the standard naive definitions exactly."""
    rng = np.random.RandomState(3)
    x = np.clip(850 + rng.normal(0, 30, 300), 400, 1400).astype(float)
    res = hc.compute_entropy_metrics(x, m=2, r_ratio=0.2)
    apen_ref, sampen_ref = _naive_standard_entropy(x, m=2, r_ratio=0.2)
    assert res["apen"] == pytest.approx(apen_ref, abs=1e-9)
    assert res["sampen"] == pytest.approx(sampen_ref, abs=1e-9)


def test_entropy_apen_and_sampen_are_distinct():
    """ApEn and SampEn are different metrics; they must not collapse to one value."""
    rng = np.random.RandomState(3)
    x = np.clip(850 + rng.normal(0, 30, 300), 400, 1400).astype(float)
    res = hc.compute_entropy_metrics(x, m=2, r_ratio=0.2)
    assert abs(res["apen"] - res["sampen"]) > 0.1


def test_int_setting_parses_and_clamps(monkeypatch):
    """Env-tunable caps must parse, clamp to a safe range, and reject junk."""
    monkeypatch.delenv("HRV_TEST_X", raising=False)
    assert hc._int_setting("HRV_TEST_X", 4000, 256, 10000) == 4000  # unset -> default
    monkeypatch.setenv("HRV_TEST_X", "2500")
    assert hc._int_setting("HRV_TEST_X", 4000, 256, 10000) == 2500
    monkeypatch.setenv("HRV_TEST_X", "99999")
    assert hc._int_setting("HRV_TEST_X", 4000, 256, 10000) == 10000  # clamp high
    monkeypatch.setenv("HRV_TEST_X", "10")
    assert hc._int_setting("HRV_TEST_X", 4000, 256, 10000) == 256  # clamp low
    monkeypatch.setenv("HRV_TEST_X", "oops")
    assert hc._int_setting("HRV_TEST_X", 4000, 256, 10000) == 4000  # junk -> default


def test_settings_constants_in_safe_range():
    assert 256 <= hc.MAX_NONLINEAR_SAMPLES <= 10000
    assert 8 <= hc.MAX_MFDFA_SCALES <= 1000


def test_entropy_matches_neurokit2_reference():
    """Cross-validate against neurokit2 (skipped if not installed)."""
    nk = pytest.importorskip("neurokit2")
    rng = np.random.RandomState(3)
    x = np.clip(850 + rng.normal(0, 30, 300), 400, 1400).astype(float)
    r = 0.2 * float(np.std(x, ddof=0))
    res = hc.compute_entropy_metrics(x, m=2, r_ratio=0.2)
    se, _ = nk.entropy_sample(x, dimension=2, tolerance=r)
    ae, _ = nk.entropy_approximate(x, dimension=2, tolerance=r)
    assert res["sampen"] == pytest.approx(float(se), abs=1e-6)
    assert res["apen"] == pytest.approx(float(ae), abs=1e-6)
