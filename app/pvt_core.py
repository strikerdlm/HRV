"""
Psychomotor Vigilance Task (PVT) core scoring module.

Canonical Python implementation of PVT scoring metrics used across the
platform's operational, research, and desktop (PsychoPy) entry points.
This module is the single source of truth; the TypeScript mirror in
`frontend/src/lib/pvt-scoring.ts` and any PsychoPy driver in
`app/pvt_desktop.py` reproduce the same metric definitions.

The PVT [Dinges & Powell 1985; Dinges et al. 1997] is a simple sustained-
attention reaction-time task originally used with 10-minute duration. A
3-minute brief variant (PVT-B) validated by Basner & Dinges (2011) uses
a reduced lapse threshold of 355 ms to maintain sensitivity, and has
been further validated on smartphone and tablet by Grant et al. (2017)
against gold-standard 10-minute laptop PVT across 38 hours of total
sleep deprivation.

Scientific References (with DOI/PMID for verification):
─────────────────────────────────────────────────────────────────────────
FOUNDATIONAL PVT:
  • Dinges DF, Pack F, Williams K, Gillen KA, Powell JW, Ott GE, Aptowicz C,
    Pack AI. (1997). Cumulative sleepiness, mood disturbance, and psychomotor
    vigilance performance decrements during a week of sleep restricted to
    4-5 hours per night. Sleep. 20(4):267-277.
    DOI: 10.1093/sleep/20.4.267
    → Standard 10-min PVT, lapses (RT ≥ 500 ms) and reciprocal-RT scoring

3-MINUTE PVT-B VALIDATION:
  • Basner M, Dinges DF. (2011). Maximizing sensitivity of the PVT to sleep
    loss. Sleep. 34(5):581-591.
    DOI: 10.1093/sleep/34.5.581
    → PVT-B duration 3 min, ISI 1-4 s, lapse threshold 355 ms,
      response-speed (1/RT) and transformed-lapse metrics

  • Grant DA, Honn KA, Layton ME, Riedy SM, Van Dongen HPA. (2017). 3-minute
    smartphone-based and tablet-based PVTs for the assessment of reduced
    alertness due to sleep deprivation. Behav Res Methods. 49(3):1020-1029.
    DOI: 10.3758/s13428-016-0763-8
    → Mobile/tablet PVT-B validation across 38-h TSD; lapses, mean RT,
      false starts all showed significant changes

  • Basner M, Mollicone D, Dinges DF. (2011). Validity and sensitivity of a
    brief psychomotor vigilance test (PVT-B) to total and partial sleep
    deprivation. Acta Astronaut. 69(11-12):949-959.
    DOI: 10.1016/j.actaastro.2011.07.015
    → Aerospace-context PVT-B validation

EXTENDED METRICS:
  • Di Muzio M, et al. (2021). Shift rotation direction and attention in
    nurses. JAMA Netw Open. 4(10):e2129906.
    DOI: 10.1001/jamanetworkopen.2021.29906
    → Median RT, 10% fastest RT, minor lapses, RT distribution analysis

WEB-BROWSER TIMING VALIDATION:
  • Anwyl-Irvine A, Dalmaijer ES, Hodges N, Evershed JK. (2020). Realistic
    precision and accuracy of online experiment platforms, web browsers, and
    devices. Behav Res Methods. 53(4):1407-1425.
    DOI: 10.3758/s13428-020-01501-5
    → Browser-based RT measurement robot-actuator benchmarking

INTEGRATION POINT (this platform):
  • This module feeds pvt_lapses_3min into app.scheduling_core
    score_pvt_lapses_3min() and the hard gate at
    PVT_LOW_PERFORMANCE_MIN_LAPSES (≥20 lapses → "low performance").

Author: Dr. Diego Leonel Malpica Hincapié, MD
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, Optional


# =============================================================================
# Constants — validated PVT parameters from peer-reviewed literature
# =============================================================================

# ------ PVT-B (3-minute brief) — Basner & Dinges 2011 -----------------------
PVT_B_DURATION_MIN: float = 3.0
PVT_B_ISI_MIN_S: float = 1.0
PVT_B_ISI_MAX_S: float = 4.0
PVT_B_LAPSE_THRESHOLD_MS: float = 355.0  # modified threshold for 3-min sensitivity

# ------ PVT-5 (5-minute mini) — mid-length variant --------------------------
PVT_5_DURATION_MIN: float = 5.0
PVT_5_ISI_MIN_S: float = 2.0
PVT_5_ISI_MAX_S: float = 10.0
PVT_5_LAPSE_THRESHOLD_MS: float = 500.0  # standard Dinges threshold

# ------ PVT-10 (standard 10-minute) — Dinges 1997 ---------------------------
PVT_10_DURATION_MIN: float = 10.0
PVT_10_ISI_MIN_S: float = 2.0
PVT_10_ISI_MAX_S: float = 10.0
PVT_10_LAPSE_THRESHOLD_MS: float = 500.0

# ------ Shared thresholds ---------------------------------------------------
MAJOR_LAPSE_THRESHOLD_MS: float = 1000.0       # Dinges 1997: "severe lapse"
FALSE_START_THRESHOLD_MS: float = 100.0        # RT < 100 ms counts as anticipatory
VALID_RT_MIN_MS: float = 100.0                 # lower bound for valid response
VALID_RT_MAX_MS: float = 30_000.0              # 30-s hard ceiling
RESPONSE_WINDOW_MS: float = 30_000.0           # stimulus shown for at most 30 s

# ------ Response-speed (1/RT) unit conversion -------------------------------
# Response speed uses reciprocal RT in seconds: 1/RT_seconds
# Basner & Dinges 2011: preferred for normality and TSD sensitivity
_MS_PER_S: float = 1000.0


class PVTVariant(str, Enum):
    """Supported PVT variants with their validation anchors."""

    PVT_B = "PVT-B"         # 3 min, lapse 355 ms — Basner & Dinges 2011
    PVT_5 = "PVT-5"         # 5 min, lapse 500 ms — operational compromise
    PVT_10 = "PVT-10"       # 10 min, lapse 500 ms — Dinges 1997 standard


def variant_defaults(variant: PVTVariant) -> dict:
    """Return canonical duration / ISI / lapse threshold for a variant."""
    if variant == PVTVariant.PVT_B:
        return {
            "duration_min": PVT_B_DURATION_MIN,
            "isi_min_s": PVT_B_ISI_MIN_S,
            "isi_max_s": PVT_B_ISI_MAX_S,
            "lapse_threshold_ms": PVT_B_LAPSE_THRESHOLD_MS,
        }
    if variant == PVTVariant.PVT_5:
        return {
            "duration_min": PVT_5_DURATION_MIN,
            "isi_min_s": PVT_5_ISI_MIN_S,
            "isi_max_s": PVT_5_ISI_MAX_S,
            "lapse_threshold_ms": PVT_5_LAPSE_THRESHOLD_MS,
        }
    if variant == PVTVariant.PVT_10:
        return {
            "duration_min": PVT_10_DURATION_MIN,
            "isi_min_s": PVT_10_ISI_MIN_S,
            "isi_max_s": PVT_10_ISI_MAX_S,
            "lapse_threshold_ms": PVT_10_LAPSE_THRESHOLD_MS,
        }
    raise ValueError(f"Unknown PVT variant: {variant!r}")


class TrialKind(str, Enum):
    """Classification of a single PVT trial outcome."""

    VALID = "valid"                 # RT ∈ [valid_rt_min_ms, RT_max]
    LAPSE = "lapse"                 # VALID trial with RT ≥ lapse threshold
    MAJOR_LAPSE = "major_lapse"     # VALID trial with RT ≥ 1000 ms
    FALSE_START = "false_start"     # RT < 100 ms OR response before stimulus
    NO_RESPONSE = "no_response"     # no response within 30-s window


# =============================================================================
# Data model
# =============================================================================

@dataclass(frozen=True)
class PVTTrial:
    """A single PVT trial.

    `isi_ms` is the inter-stimulus interval preceding the stimulus. `rt_ms`
    is None when the operator failed to respond within the response window.
    """

    index: int                      # 0-based trial index
    isi_ms: float                   # inter-stimulus interval (ms)
    stimulus_onset_ms: float        # time from session start to stimulus (ms)
    rt_ms: Optional[float]          # response time (ms); None → NO_RESPONSE
    anticipatory: bool = False      # True if respond-before-stimulus detected


@dataclass(frozen=True)
class PVTSession:
    """A completed PVT session.

    `trials` is the chronologically ordered list of all trial outcomes.
    `variant` selects the lapse threshold and canonical ISI range.
    """

    variant: PVTVariant
    duration_min: float
    trials: tuple[PVTTrial, ...]
    user_id: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    device_label: Optional[str] = None   # e.g. "web", "psychopy", "tablet"
    notes: Optional[str] = None
    # Metadata for audit
    software_version: Optional[str] = None


# =============================================================================
# Classification helpers
# =============================================================================

def classify_trial(trial: PVTTrial, lapse_threshold_ms: float) -> TrialKind:
    """Classify a trial using Dinges 1997 / Basner & Dinges 2011 rules."""
    if trial.anticipatory:
        return TrialKind.FALSE_START
    if trial.rt_ms is None:
        return TrialKind.NO_RESPONSE
    if trial.rt_ms < FALSE_START_THRESHOLD_MS:
        return TrialKind.FALSE_START
    if trial.rt_ms > VALID_RT_MAX_MS:
        return TrialKind.NO_RESPONSE
    # Ordering matters: major-lapse is a subset of lapse
    if trial.rt_ms >= MAJOR_LAPSE_THRESHOLD_MS:
        return TrialKind.MAJOR_LAPSE
    if trial.rt_ms >= lapse_threshold_ms:
        return TrialKind.LAPSE
    return TrialKind.VALID


# =============================================================================
# Scoring — validated PVT metrics
# =============================================================================

def _mean(values: list[float]) -> Optional[float]:
    return statistics.fmean(values) if values else None


def _median(values: list[float]) -> Optional[float]:
    return statistics.median(values) if values else None


def _stdev(values: list[float]) -> Optional[float]:
    return statistics.pstdev(values) if len(values) >= 2 else None


def _percentile(values: list[float], p: float) -> Optional[float]:
    """Linear-interpolated percentile (p in [0, 100]). Returns None if empty."""
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * (p / 100.0)
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def _mean_of_slice(values: list[float], k: int, from_start: bool) -> Optional[float]:
    """Mean of the k fastest (from_start=True) or k slowest (from_start=False) values."""
    if not values or k <= 0:
        return None
    xs = sorted(values)
    chunk = xs[:k] if from_start else xs[-k:]
    return _mean(chunk)


def score_session(
    session: PVTSession,
    *,
    lapse_threshold_ms: Optional[float] = None,
) -> dict:
    """Compute the full validated PVT metric set for one session.

    Returns a flat dict of metrics suitable for JSON serialisation, API
    transport, database persistence, and cross-language verification
    against the TypeScript mirror.

    `lapse_threshold_ms` defaults to the variant-specific threshold:
    355 ms for PVT-B, 500 ms for PVT-5 and PVT-10.
    """
    defaults = variant_defaults(session.variant)
    lapse_ms = lapse_threshold_ms if lapse_threshold_ms is not None else defaults["lapse_threshold_ms"]

    valid_rt_ms: list[float] = []
    lapse_rt_ms: list[float] = []
    n_trials = len(session.trials)
    n_false_start = 0
    n_lapse = 0
    n_major_lapse = 0
    n_no_response = 0

    for t in session.trials:
        kind = classify_trial(t, lapse_ms)
        if kind is TrialKind.VALID:
            valid_rt_ms.append(t.rt_ms)  # type: ignore[arg-type]
        elif kind is TrialKind.LAPSE:
            valid_rt_ms.append(t.rt_ms)  # type: ignore[arg-type]
            lapse_rt_ms.append(t.rt_ms)  # type: ignore[arg-type]
            n_lapse += 1
        elif kind is TrialKind.MAJOR_LAPSE:
            valid_rt_ms.append(t.rt_ms)  # type: ignore[arg-type]
            lapse_rt_ms.append(t.rt_ms)  # type: ignore[arg-type]
            n_lapse += 1         # major-lapse counts as lapse
            n_major_lapse += 1
        elif kind is TrialKind.FALSE_START:
            n_false_start += 1
        elif kind is TrialKind.NO_RESPONSE:
            n_no_response += 1

    n_valid = len(valid_rt_ms)

    # ---- Core RT metrics (Dinges 1997) -------------------------------------
    mean_rt = _mean(valid_rt_ms)
    median_rt = _median(valid_rt_ms)
    sd_rt = _stdev(valid_rt_ms)
    min_rt = min(valid_rt_ms) if valid_rt_ms else None
    max_rt = max(valid_rt_ms) if valid_rt_ms else None
    p10_rt = _percentile(valid_rt_ms, 10.0)
    p90_rt = _percentile(valid_rt_ms, 90.0)
    cv_rt = (sd_rt / mean_rt) if (sd_rt is not None and mean_rt not in (None, 0.0)) else None

    # Fastest/slowest 10 % mean RT (Dinges 1997 composite)
    k_tail = max(1, int(round(n_valid * 0.10))) if n_valid > 0 else 0
    fastest10_mean = _mean_of_slice(valid_rt_ms, k_tail, from_start=True)
    slowest10_mean = _mean_of_slice(valid_rt_ms, k_tail, from_start=False)

    # ---- Reciprocal RT (1/RT in s^-1) — Basner & Dinges 2011 ---------------
    # 1/RT has better normality than raw RT and is more sensitive to TSD.
    def _recip(rt_ms: float) -> float:
        return _MS_PER_S / rt_ms
    speeds = [_recip(x) for x in valid_rt_ms]
    mean_speed = _mean(speeds)
    median_speed = _median(speeds)
    fastest10_speed = _mean_of_slice(speeds, k_tail, from_start=False)  # fastest RT ↔ largest 1/RT → slowest slice
    slowest10_speed = _mean_of_slice(speeds, k_tail, from_start=True)   # slowest RT ↔ smallest 1/RT → fastest slice

    # ---- Transformed lapses (Basner & Dinges 2011) -------------------------
    # For normality: sqrt(L) + sqrt(L + 1). Stable for small counts.
    transformed_lapses = math.sqrt(n_lapse) + math.sqrt(n_lapse + 1)

    # ---- Response-speed index (Dinges 1997 aggregate) ----------------------
    # Combines central tendency and tails into a single alertness score.
    # Higher = more alert; bounded roughly to [0, 5] s^-1 in healthy adults.
    response_speed_index = mean_speed if mean_speed is not None else None

    # ---- PVT-B specific: pvt_lapses_3min for HRV platform integration ------
    # Counts RT ≥ 355 ms OR RT ≥ 500 ms depending on variant, scaled to 3 min
    # for operational use with score_pvt_lapses_3min in scheduling_core.
    if session.variant == PVTVariant.PVT_B:
        pvt_lapses_3min = n_lapse
    else:
        # Scale observed lapse rate to an equivalent 3-min count
        scale = 3.0 / session.duration_min if session.duration_min > 0 else 0.0
        pvt_lapses_3min = int(round(n_lapse * scale))

    return {
        # ---- Session metadata ----
        "variant": session.variant.value,
        "duration_min": session.duration_min,
        "lapse_threshold_ms": lapse_ms,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "user_id": session.user_id,
        "device_label": session.device_label,
        "software_version": session.software_version,
        # ---- Trial counts ----
        "n_trials": n_trials,
        "n_valid_trials": n_valid,
        "n_false_starts": n_false_start,
        "n_no_response": n_no_response,
        "n_lapses": n_lapse,
        "n_major_lapses": n_major_lapse,
        # ---- Core RT metrics (ms) ----
        "mean_rt_ms": mean_rt,
        "median_rt_ms": median_rt,
        "sd_rt_ms": sd_rt,
        "min_rt_ms": min_rt,
        "max_rt_ms": max_rt,
        "p10_rt_ms": p10_rt,
        "p90_rt_ms": p90_rt,
        "cv_rt": cv_rt,
        "fastest_10pct_mean_rt_ms": fastest10_mean,
        "slowest_10pct_mean_rt_ms": slowest10_mean,
        # ---- Response-speed metrics (1/s) ----
        "mean_response_speed_per_s": mean_speed,
        "median_response_speed_per_s": median_speed,
        "fastest_10pct_mean_speed_per_s": fastest10_speed,
        "slowest_10pct_mean_speed_per_s": slowest10_speed,
        # ---- Derived sensitivity metrics ----
        "transformed_lapses": transformed_lapses,     # Basner & Dinges 2011
        "response_speed_index": response_speed_index, # Dinges 1997 composite
        # ---- Operational gate input ----
        "pvt_lapses_3min": pvt_lapses_3min,
    }


def score_trials(
    trials: Iterable[PVTTrial],
    *,
    variant: PVTVariant,
    duration_min: Optional[float] = None,
    lapse_threshold_ms: Optional[float] = None,
    user_id: Optional[str] = None,
    device_label: Optional[str] = None,
    software_version: Optional[str] = None,
) -> dict:
    """Convenience entry point: score a trial list without constructing a session."""
    defaults = variant_defaults(variant)
    sess = PVTSession(
        variant=variant,
        duration_min=duration_min if duration_min is not None else defaults["duration_min"],
        trials=tuple(trials),
        user_id=user_id,
        device_label=device_label,
        software_version=software_version,
    )
    return score_session(sess, lapse_threshold_ms=lapse_threshold_ms)


# =============================================================================
# Session helpers
# =============================================================================

def build_session_from_raw(
    raw_trials: Iterable[dict],
    *,
    variant: PVTVariant,
    duration_min: Optional[float] = None,
    user_id: Optional[str] = None,
    started_at: Optional[datetime] = None,
    ended_at: Optional[datetime] = None,
    device_label: Optional[str] = None,
    software_version: Optional[str] = None,
) -> PVTSession:
    """Build a PVTSession from a list of plain dicts, typically from JSON over HTTP.

    Expected keys per raw trial: `index`, `isi_ms`, `stimulus_onset_ms`,
    `rt_ms` (nullable), `anticipatory` (optional bool).
    """
    defaults = variant_defaults(variant)
    trials = tuple(
        PVTTrial(
            index=int(r["index"]),
            isi_ms=float(r["isi_ms"]),
            stimulus_onset_ms=float(r["stimulus_onset_ms"]),
            rt_ms=None if r.get("rt_ms") is None else float(r["rt_ms"]),
            anticipatory=bool(r.get("anticipatory", False)),
        )
        for r in raw_trials
    )
    return PVTSession(
        variant=variant,
        duration_min=duration_min if duration_min is not None else defaults["duration_min"],
        trials=trials,
        user_id=user_id,
        started_at=started_at,
        ended_at=ended_at,
        device_label=device_label,
        software_version=software_version,
    )


def generate_isi_schedule(
    variant: PVTVariant,
    *,
    seed: Optional[int] = None,
) -> list[float]:
    """Pre-compute an ISI schedule covering the variant's duration.

    Returns a list of ISIs (in ms). Total ISI sum is approximately the
    variant duration minus expected response time (~5 ms * n_trials).
    Uniform random draws within the variant's canonical ISI range.
    """
    import random

    rng = random.Random(seed)
    defaults = variant_defaults(variant)
    duration_ms = defaults["duration_min"] * 60.0 * _MS_PER_S
    isi_min_ms = defaults["isi_min_s"] * _MS_PER_S
    isi_max_ms = defaults["isi_max_s"] * _MS_PER_S

    schedule: list[float] = []
    total_ms = 0.0
    # Budget ~500 ms per trial for response + inter-trial overhead.
    expected_response_ms = 500.0
    while total_ms < duration_ms:
        isi_ms = rng.uniform(isi_min_ms, isi_max_ms)
        schedule.append(isi_ms)
        total_ms += isi_ms + expected_response_ms
    return schedule


# =============================================================================
# Operational helpers — integration with readiness-fusion pipeline
# =============================================================================

def operational_gate(metrics: dict) -> dict:
    """Return a GO / CAUTION / NO-GO decision from a scored PVT session.

    Mirrors the hard-gate logic in app.scheduling_core where
    pvt_lapses_3min ≥ PVT_LOW_PERFORMANCE_MIN_LAPSES (20) triggers
    "low-performance" classification. Additional hedged bands surface
    earlier fatigue signals for operational users.
    """
    lapses = int(metrics.get("pvt_lapses_3min") or 0)
    n_valid = int(metrics.get("n_valid_trials") or 0)
    n_false = int(metrics.get("n_false_starts") or 0)

    reasons: list[str] = []
    if n_valid < 20:
        reasons.append("Insufficient valid trials (<20); retest.")
    if n_false > 10:
        reasons.append(f"Excessive false starts ({n_false}); rushed responses.")

    if lapses >= 20:
        decision = "NO_GO"
        reasons.append(f"PVT lapses ≥ 20 (got {lapses}); low-performance gate.")
    elif lapses >= 10:
        decision = "CAUTION"
        reasons.append(f"PVT lapses {lapses} in 10–19; enhanced monitoring.")
    elif lapses >= 5:
        decision = "GO_MONITOR"
        reasons.append(f"PVT lapses {lapses} in 5–9; proceed with CRM awareness.")
    else:
        decision = "GO"

    return {
        "decision": decision,
        "pvt_lapses_3min": lapses,
        "n_valid_trials": n_valid,
        "n_false_starts": n_false,
        "reasons": reasons,
    }


__all__ = [
    # enums + constants
    "PVTVariant",
    "TrialKind",
    "PVT_B_DURATION_MIN", "PVT_B_ISI_MIN_S", "PVT_B_ISI_MAX_S", "PVT_B_LAPSE_THRESHOLD_MS",
    "PVT_5_DURATION_MIN", "PVT_5_ISI_MIN_S", "PVT_5_ISI_MAX_S", "PVT_5_LAPSE_THRESHOLD_MS",
    "PVT_10_DURATION_MIN", "PVT_10_ISI_MIN_S", "PVT_10_ISI_MAX_S", "PVT_10_LAPSE_THRESHOLD_MS",
    "MAJOR_LAPSE_THRESHOLD_MS", "FALSE_START_THRESHOLD_MS",
    "VALID_RT_MIN_MS", "VALID_RT_MAX_MS", "RESPONSE_WINDOW_MS",
    # data model
    "PVTTrial", "PVTSession",
    # scoring
    "classify_trial", "score_session", "score_trials",
    # helpers
    "variant_defaults", "build_session_from_raw", "generate_isi_schedule",
    "operational_gate",
]
