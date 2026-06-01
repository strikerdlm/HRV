"""Performance regression guards for HRV nonlinear metrics.

These tests exist because the entropy (SampEn/ApEn) and RQA computations were
O(n^2) and uncapped, so advanced analysis of a multi-hour recording could take
30+ minutes (or OOM). They assert the heavy nonlinear methods stay bounded
regardless of recording length, and that the vectorized entropy is numerically
identical to the naive O(n^2) definition (no change to the science).
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


def test_entropy_metrics_bounded_for_long_series():
    """SampEn/ApEn must not blow up on long recordings (was O(n^2), pure Python)."""
    rr = _synth(20000)  # ~4.7 h recording
    res = _run_with_timeout(lambda: hc.compute_entropy_metrics(rr, m=2, r_ratio=0.2), 5)
    assert np.isfinite(res["sampen"])
    assert np.isfinite(res["apen"])


def test_rqa_metrics_bounded_for_long_series():
    """RQA must not allocate an n x n matrix for large n (was O(n^2) memory)."""
    rr = _synth(8000)  # bench: ~27 s unfixed
    t0 = time.perf_counter()
    res = hc.compute_rqa_metrics(rr)
    assert (time.perf_counter() - t0) < 5.0
    assert np.isfinite(res["rqa_rr"])


def test_comprehensive_advanced_bounded_for_long_series():
    """End-to-end advanced analysis must finish quickly even for multi-hour data."""
    rr = _synth(20000)
    res = _run_with_timeout(
        lambda: hc.compute_comprehensive_hrv(rr, include_advanced=True), 20
    )
    assert res["n_intervals"] == 20000  # full length still reported
    assert "sampen" in res and np.isfinite(res["sampen"])


def test_entropy_vectorization_matches_naive_reference():
    """Vectorized entropy must equal the original naive O(n^2) definition exactly.

    Uses a short series (below the internal cap) so the full series is used and
    the comparison is apples-to-apples.
    """
    rr = _synth(150)
    res = hc.compute_entropy_metrics(rr, m=2, r_ratio=0.2)

    x = rr.astype(float)
    n = x.size
    r = float(max(1e-9, 0.2 * float(np.std(x, ddof=0))))

    def _phi(dim: int) -> float:
        counts = []
        for i in range(0, n - dim + 1):
            ref = x[i : i + dim]
            c = 0
            for j in range(0, n - dim + 1):
                if i == j:
                    continue
                if np.max(np.abs(ref - x[j : j + dim])) <= r:
                    c += 1
            counts.append(c)
        return float(np.mean(np.array(counts, dtype=float) / max(1, (n - dim))))

    def _match_count(dim: int):
        Cm = 0
        for i in range(0, n - dim):
            ref = x[i : i + dim]
            for j in range(i + 1, n - dim + 1):
                if np.max(np.abs(ref - x[j : j + dim])) <= r:
                    Cm += 1
        return Cm, (n - dim) * (n - dim + 1) // 2

    phi_m, phi_m1 = _phi(2), _phi(3)
    apen_ref = (
        float(-np.log(phi_m1 / max(1e-12, phi_m))) if (phi_m > 0 and phi_m1 > 0) else 0.0
    )
    Cm, tm = _match_count(2)
    Cm1, tm1 = _match_count(3)
    p_m = Cm / max(1, tm)
    p_m1 = Cm1 / max(1, tm1)
    sampen_ref = (
        float(-np.log(p_m1 / max(1e-12, p_m))) if (p_m > 0 and p_m1 > 0) else 0.0
    )

    assert res["apen"] == pytest.approx(apen_ref, abs=1e-9)
    assert res["sampen"] == pytest.approx(sampen_ref, abs=1e-9)
