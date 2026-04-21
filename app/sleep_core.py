"""
Sleep module — canonical Python scoring for Mission Control.

Single source of truth for all sleep-derived metrics consumed by the
FastAPI backend, the Next.js research dashboard (`/research/sleep`), and
the operational sleep readiness gate (`/scheduling/sleep`). The TypeScript
frontend helpers in `frontend/src/lib/sleep-metrics.ts` mirror a subset of
this module for client-side preview; the authoritative calculations are
always done server-side.

Scope of this module (Pending.md §4 Tier A only):
- Sleep duration, efficiency, and score aggregates from Garmin daily
  summaries (per-user, per-date).
- Stage-balance derivations (deep+REM proportion, deep:REM ratio).
- Sleep debt (cumulative deficit vs typical target).
- Sleep regularity index (Lunsford-Avery 2018) computed from Garmin
  `sleep_start_utc` / `sleep_end_utc` across a rolling window.
- Bedtime and waketime standard deviation (practical regularity proxies).
- Low-SpO2 night flagging (Tier C — screening proxy, explicitly NOT an
  AHI or apnea diagnosis).
- Nightly readiness index and 3-/7-night operational gate.

Explicitly out of scope for this module (would need Tier B ingestion):
- Hypnograms, arousal indices, fragmentation indices, WASO/latency —
  require per-epoch / per-event data not present in Garmin daily
  summaries.
- Polysomnography equivalence — no claim of PSG-grade validity.

Scientific References (with DOI/PMID for verification):
─────────────────────────────────────────────────────────────────────────────
SLEEP STAGES × AUTONOMIC PHYSIOLOGY:
  • Liao D, et al. Sleep-disordered breathing in children — sleep stage-
    specific autonomic modulation. *J Sleep Res.*
    PMID 20337904
  • Kesek M, et al. HRV during sleep and sleep apnoea — population women.
    PMID 19453563

SLEEP DEPRIVATION / FRAGMENTATION × ANS:
  • Zhang S, et al. Sleep deprivation and HRV — systematic review &
    meta-analysis. PMID 40895095
  • Zhu L, et al. Circadian types and 24-hour HRV — fragmented sleep
    patterns. PMID 40768960

WAKE HRV × SLEEP APNEA / SPO2:
  • Balali P, et al. Wake HRV vs sleep apnea indicators / SpO₂
    (clinical + altitude cohort). PMID 41953462

SLEEP REGULARITY INDEX (SRI):
  • Lunsford-Avery JR, Engelhard MM, Navar AM, Kollins SH. (2018).
    Validation of the Sleep Regularity Index in Older Adults and
    Associations with Cardiometabolic Risk. *Scientific Reports* 8.
    DOI 10.1038/s41598-018-32402-5 — SRI as % of epochs matching
    between consecutive 24-hour cycles.

CONSUMER WEARABLE vs PSG VALIDATION:
  • Lee YJ, et al. (2025). Performance of consumer wrist-worn sleep
    tracking devices compared to polysomnography: a meta-analysis.
    *J Clin Sleep Med* 21(3):573-582. DOI 10.5664/jcsm.11460
  • Schyvens AM, et al. (2024). Accuracy of Fitbit Charge 4, Garmin
    Vivosmart 4, and WHOOP Versus Polysomnography: Systematic Review.
    DOI 10.2196/52192

HRV STANDARDS:
  • Task Force of the European Society of Cardiology and the North
    American Society of Pacing and Electrophysiology. (1996). Heart
    rate variability: standards of measurement, physiological
    interpretation and clinical use. *Circulation* 93(5):1043-1065.
    DOI 10.1161/01.cir.93.5.1043 / PMID 8598068

INTEGRATION POINT (this platform):
  • Shares `garmin_daily_metrics` schema defined in app/user_database.py
  • Sleep-debt output feeds the existing readiness pipeline alongside
    SAFTE effectiveness and `pvt_lapses_3min`.
  • Low-SpO2 night flagging is **strictly screening language**; AHI,
    RDI, or any apnea-diagnosis wording is forbidden in the UI.

Author: Dr. Diego Leonel Malpica Hincapié, MD
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Iterable, Optional


# =============================================================================
# Constants — operational thresholds and typical targets
# =============================================================================

# ------ Operational sleep duration targets ----------------------------------
TYPICAL_SLEEP_DURATION_H: float = 7.5       # default operator target (hours)
MIN_ACCEPTABLE_SLEEP_H: float = 6.0          # below this → CAUTION
HARD_FLOOR_SLEEP_H: float = 5.0              # below this → NO-GO single-night
OPERATIONAL_SLEEP_DEBT_CAUTION_H: float = 4.0    # 7-night debt → CAUTION
OPERATIONAL_SLEEP_DEBT_NOGO_H: float = 8.0       # 7-night debt → NO-GO

# ------ Sleep efficiency thresholds (0-1 decimal; mirrors Garmin/AASM) -----
SLEEP_EFFICIENCY_OPTIMAL: float = 0.85
SLEEP_EFFICIENCY_POOR: float = 0.75

# ------ Stage-balance heuristics (informational, not diagnostic) ------------
# Percent-of-total-sleep-time ranges commonly referenced in sleep literature
# for healthy adults. Used only for relative band colouring in plots.
DEEP_PCT_HEALTHY_LOW: float = 0.10
DEEP_PCT_HEALTHY_HIGH: float = 0.25
REM_PCT_HEALTHY_LOW: float = 0.15
REM_PCT_HEALTHY_HIGH: float = 0.30

# ------ SpO2 screening-proxy thresholds (Tier C — NEVER clinical) -----------
SPO2_LOW_NIGHT_THRESHOLD: float = 92.0       # average SpO2 < 92% = flagged
SPO2_LOW_NIGHT_CAUTION_7D: int = 2           # 2+ low nights / 7 → CAUTION
SPO2_LOW_NIGHT_NOGO_7D: int = 4              # 4+ low nights / 7 → NO-GO (screen)

# ------ Sleep Regularity Index bands (Lunsford-Avery 2018) ------------------
SRI_HIGH_REGULARITY: float = 80.0            # SRI ≥ 80 → highly regular
SRI_MODERATE_REGULARITY: float = 60.0        # 60-79 → moderate
SRI_IRREGULAR_CAUTION: float = 40.0          # < 40 → CAUTION for operations

# ------ Window sizes for rolling statistics ---------------------------------
ROLLING_7D_WINDOW_DAYS: int = 7
ROLLING_14D_WINDOW_DAYS: int = 14
ROLLING_30D_WINDOW_DAYS: int = 30
MIN_NIGHTS_FOR_STATS: int = 14               # Pending.md §5 underpowered below


# =============================================================================
# Enums
# =============================================================================

class SleepReadinessBand(str, Enum):
    """Operational sleep readiness decision bands."""
    GO = "GO"                           # sleep debt < 4 h and no red flags
    GO_MONITOR = "GO_MONITOR"          # minor deficits
    CAUTION = "CAUTION"                # meaningful deficits; CRM awareness
    NO_GO = "NO_GO"                    # hard gate — do not fly / operate


class SpO2ScreeningBand(str, Enum):
    """Low-SpO2 screening proxy — NOT apnea diagnosis."""
    NORMAL = "NORMAL"
    MILD_FLAG = "MILD_FLAG"            # ≥1 low night in 7
    ELEVATED_FLAG = "ELEVATED_FLAG"    # ≥2 low nights in 7
    HIGH_FLAG = "HIGH_FLAG"            # ≥4 low nights in 7


# =============================================================================
# Input dataclass (subset of GarminDailyMetrics used by this module)
# =============================================================================

@dataclass(frozen=True)
class NightlyRecord:
    """One night of Garmin-derived sleep and autonomic metrics.

    All fields are Optional[] because Garmin can return partial rows.
    `metric_date` is the calendar date on which the night ended.
    """
    metric_date: date
    # Duration + quality
    sleep_duration_hours: Optional[float] = None
    sleep_efficiency: Optional[float] = None          # 0-1 decimal
    sleep_score: Optional[float] = None               # Garmin scale 0-100
    sleep_start_utc: Optional[datetime] = None
    sleep_end_utc: Optional[datetime] = None
    # Stage minutes
    sleep_deep_minutes: Optional[int] = None
    sleep_rem_minutes: Optional[int] = None
    sleep_light_minutes: Optional[int] = None
    sleep_awake_minutes: Optional[int] = None
    # Autonomic + respiration
    hrv_rmssd_ms: Optional[float] = None
    hrv_sdnn_ms: Optional[float] = None
    resting_hr_bpm: Optional[float] = None
    avg_spo2: Optional[float] = None
    avg_respiration_awake: Optional[float] = None
    avg_respiration_sleep: Optional[float] = None
    # Body battery
    body_battery_avg: Optional[float] = None
    stress_score: Optional[float] = None


# =============================================================================
# Helpers
# =============================================================================

def _finite(x: Optional[float]) -> bool:
    return x is not None and math.isfinite(x)


def _drop_nones(xs: Iterable[Optional[float]]) -> list[float]:
    return [x for x in xs if _finite(x)]


def _mean(xs: Iterable[Optional[float]]) -> Optional[float]:
    vs = _drop_nones(xs)
    return statistics.fmean(vs) if vs else None


def _pstdev(xs: Iterable[Optional[float]]) -> Optional[float]:
    vs = _drop_nones(xs)
    return statistics.pstdev(vs) if len(vs) >= 2 else None


def _parse_iso_time_of_day_minutes(dt: datetime) -> float:
    """Minutes since local midnight (0-1440). Assumes UTC datetimes; for
    Garmin the start/end UTC fields are converted consistently, so local
    variability across nights is preserved."""
    return dt.hour * 60.0 + dt.minute + dt.second / 60.0


# =============================================================================
# Stage-balance derivations (Tier A)
# =============================================================================

@dataclass(frozen=True)
class StageBalance:
    """Derived stage balance for one night."""
    total_minutes: Optional[int]
    deep_pct: Optional[float]        # deep / total
    rem_pct: Optional[float]
    light_pct: Optional[float]
    awake_pct: Optional[float]
    deep_plus_rem_pct: Optional[float]
    deep_plus_rem_minutes: Optional[int]
    deep_to_rem_ratio: Optional[float]


def compute_stage_balance(r: NightlyRecord) -> StageBalance:
    """Compute stage-balance derivations from Garmin stage-minute summaries."""
    d = r.sleep_deep_minutes
    rem = r.sleep_rem_minutes
    lt = r.sleep_light_minutes
    aw = r.sleep_awake_minutes
    parts = [v for v in (d, rem, lt, aw) if v is not None]
    total = sum(parts) if parts else None
    if not total or total <= 0:
        return StageBalance(None, None, None, None, None, None, None, None)

    def pct(x: Optional[int]) -> Optional[float]:
        return (x / total) if x is not None else None

    deep_rem_min: Optional[int] = None
    if d is not None or rem is not None:
        deep_rem_min = (d or 0) + (rem or 0)
    deep_rem_pct = (deep_rem_min / total) if deep_rem_min is not None else None
    ratio: Optional[float] = None
    if d and rem and rem > 0:
        ratio = d / rem

    return StageBalance(
        total_minutes=total,
        deep_pct=pct(d),
        rem_pct=pct(rem),
        light_pct=pct(lt),
        awake_pct=pct(aw),
        deep_plus_rem_pct=deep_rem_pct,
        deep_plus_rem_minutes=deep_rem_min,
        deep_to_rem_ratio=ratio,
    )


# =============================================================================
# Sleep debt — cumulative deficit vs typical target
# =============================================================================

@dataclass(frozen=True)
class SleepDebtResult:
    window_nights: int
    typical_target_hours: float
    observed_mean_hours: Optional[float]
    observed_total_hours: Optional[float]
    target_total_hours: float
    cumulative_debt_hours: Optional[float]  # positive = owed
    nightly_deficits: list[Optional[float]]


def compute_sleep_debt(
    records: list[NightlyRecord],
    *,
    typical_target_hours: float = TYPICAL_SLEEP_DURATION_H,
    window_nights: int = ROLLING_7D_WINDOW_DAYS,
) -> SleepDebtResult:
    """Cumulative deficit = sum_i max(0, target - observed_i) over window."""
    recent = records[-window_nights:] if records else []
    nightly_deficits: list[Optional[float]] = []
    observed_total = 0.0
    observed_count = 0
    debt_total = 0.0
    for r in recent:
        h = r.sleep_duration_hours
        if h is None or not math.isfinite(h):
            nightly_deficits.append(None)
            continue
        observed_total += h
        observed_count += 1
        deficit = max(0.0, typical_target_hours - h)
        nightly_deficits.append(deficit)
        debt_total += deficit

    return SleepDebtResult(
        window_nights=window_nights,
        typical_target_hours=typical_target_hours,
        observed_mean_hours=(observed_total / observed_count) if observed_count else None,
        observed_total_hours=observed_total if observed_count else None,
        target_total_hours=typical_target_hours * window_nights,
        cumulative_debt_hours=debt_total if observed_count else None,
        nightly_deficits=nightly_deficits,
    )


# =============================================================================
# Sleep regularity index (Lunsford-Avery 2018)
# =============================================================================

@dataclass(frozen=True)
class RegularityResult:
    window_nights: int
    n_pairs: int
    sri_percent: Optional[float]          # 0-100 per Lunsford-Avery
    bedtime_sd_minutes: Optional[float]
    waketime_sd_minutes: Optional[float]
    midpoint_sd_minutes: Optional[float]


def compute_sleep_regularity(
    records: list[NightlyRecord],
    *,
    window_nights: int = ROLLING_14D_WINDOW_DAYS,
    epoch_minutes: int = 5,
) -> RegularityResult:
    """Lunsford-Avery 2018 Sleep Regularity Index (SRI).

    SRI = 2 * (P_match - 0.5) * 100 where P_match is the probability that,
    at a given minute of day, the participant is in the same state
    (asleep / awake) on two consecutive days. A fully regular schedule
    → SRI ~100; a uniformly random schedule → SRI ~0.

    This implementation compares all consecutive night pairs in the window
    using 5-minute epochs by default. If sleep_start_utc / sleep_end_utc
    are missing for either night of a pair, that pair is skipped.
    """
    recent = records[-window_nights:] if records else []

    # Convert each night into a boolean "asleep" vector over a 24-h day,
    # indexed by minutes from local midnight of the SLEEP-END date. For
    # nightly summaries this approximates the Lunsford-Avery minute
    # resolution well enough for a 5-minute epoch comparison.
    n_mins_per_day = 24 * 60
    asleep_series: list[Optional[list[bool]]] = []
    bedtime_mins: list[Optional[float]] = []
    waketime_mins: list[Optional[float]] = []
    midpoint_mins: list[Optional[float]] = []

    for r in recent:
        if r.sleep_start_utc is None or r.sleep_end_utc is None:
            asleep_series.append(None)
            bedtime_mins.append(None)
            waketime_mins.append(None)
            midpoint_mins.append(None)
            continue
        bed_min = _parse_iso_time_of_day_minutes(r.sleep_start_utc)
        wake_min = _parse_iso_time_of_day_minutes(r.sleep_end_utc)
        # Handle overnight wrap
        if wake_min <= bed_min:
            wake_min += n_mins_per_day
        mid = (bed_min + wake_min) / 2.0
        bedtime_mins.append(bed_min % n_mins_per_day)
        waketime_mins.append(wake_min % n_mins_per_day)
        midpoint_mins.append(mid % n_mins_per_day)
        # Build asleep vector over the night
        flags = [False] * n_mins_per_day
        start_i = int(round(bed_min)) % n_mins_per_day
        end_i = int(round(wake_min))
        for i in range(start_i, end_i):
            flags[i % n_mins_per_day] = True
        asleep_series.append(flags)

    # Pair-wise SRI computation
    matches = 0
    total = 0
    for i in range(len(asleep_series) - 1):
        a = asleep_series[i]
        b = asleep_series[i + 1]
        if a is None or b is None:
            continue
        for m in range(0, n_mins_per_day, epoch_minutes):
            total += 1
            if a[m] == b[m]:
                matches += 1
    sri: Optional[float] = None
    n_pairs = sum(
        1 for i in range(len(asleep_series) - 1)
        if asleep_series[i] is not None and asleep_series[i + 1] is not None
    )
    if total > 0:
        p_match = matches / total
        sri = (2 * (p_match - 0.5)) * 100.0
        sri = max(0.0, min(100.0, sri))

    return RegularityResult(
        window_nights=window_nights,
        n_pairs=n_pairs,
        sri_percent=sri,
        bedtime_sd_minutes=_pstdev(bedtime_mins),
        waketime_sd_minutes=_pstdev(waketime_mins),
        midpoint_sd_minutes=_pstdev(midpoint_mins),
    )


# =============================================================================
# SpO2 screening proxy (Tier C — strictly screening)
# =============================================================================

@dataclass(frozen=True)
class SpO2ScreeningResult:
    window_nights: int
    n_valid_nights: int
    low_spo2_nights: int
    low_spo2_nights_7d: int
    mean_spo2: Optional[float]
    band: SpO2ScreeningBand


def compute_spo2_screening(
    records: list[NightlyRecord],
    *,
    low_threshold: float = SPO2_LOW_NIGHT_THRESHOLD,
    window_nights: int = ROLLING_7D_WINDOW_DAYS,
) -> SpO2ScreeningResult:
    """Flag low-SpO2 nights as a **screening proxy**. NOT apnea diagnosis.

    Any UI surfacing these results must label them 'screening' and must
    never use AHI/RDI/apnea-diagnosis language.
    """
    recent = records[-window_nights:] if records else []
    valid = [r.avg_spo2 for r in recent if _finite(r.avg_spo2)]
    low_count = sum(1 for v in valid if v < low_threshold)
    mean = _mean(valid)

    if low_count >= SPO2_LOW_NIGHT_NOGO_7D:
        band = SpO2ScreeningBand.HIGH_FLAG
    elif low_count >= SPO2_LOW_NIGHT_CAUTION_7D:
        band = SpO2ScreeningBand.ELEVATED_FLAG
    elif low_count >= 1:
        band = SpO2ScreeningBand.MILD_FLAG
    else:
        band = SpO2ScreeningBand.NORMAL

    return SpO2ScreeningResult(
        window_nights=window_nights,
        n_valid_nights=len(valid),
        low_spo2_nights=low_count,
        low_spo2_nights_7d=low_count,
        mean_spo2=mean,
        band=band,
    )


# =============================================================================
# Nightly readiness index + operational gate
# =============================================================================

@dataclass(frozen=True)
class SleepReadinessResult:
    decision: SleepReadinessBand
    reasons: list[str]
    inputs: dict[str, Any]


def operational_sleep_gate(
    records: list[NightlyRecord],
    *,
    typical_target_hours: float = TYPICAL_SLEEP_DURATION_H,
) -> SleepReadinessResult:
    """Return the operational sleep-readiness band and human-readable reasons.

    Logic (conservative; mirrors the PVT gate shape):
      • last night duration is a hard gate (< 5 h → NO-GO)
      • 7-night cumulative debt drives degrees of CAUTION / NO-GO
      • SRI < 40 contributes CAUTION
      • SpO2 screening HIGH_FLAG contributes CAUTION (never NO-GO alone —
        it's a screen, not a diagnosis)
    """
    if not records:
        return SleepReadinessResult(
            decision=SleepReadinessBand.CAUTION,
            reasons=["No sleep data available; retest required."],
            inputs={},
        )

    last = records[-1]
    debt = compute_sleep_debt(records, typical_target_hours=typical_target_hours)
    regularity = compute_sleep_regularity(records)
    spo2 = compute_spo2_screening(records)

    reasons: list[str] = []
    decision = SleepReadinessBand.GO

    def escalate(new: SleepReadinessBand) -> None:
        nonlocal decision
        order = {
            SleepReadinessBand.GO: 0,
            SleepReadinessBand.GO_MONITOR: 1,
            SleepReadinessBand.CAUTION: 2,
            SleepReadinessBand.NO_GO: 3,
        }
        if order[new] > order[decision]:
            decision = new

    # --- Hard gate: last night duration -------------------------------------
    if last.sleep_duration_hours is not None and last.sleep_duration_hours < HARD_FLOOR_SLEEP_H:
        escalate(SleepReadinessBand.NO_GO)
        reasons.append(
            f"Last-night sleep {last.sleep_duration_hours:.1f} h < "
            f"{HARD_FLOOR_SLEEP_H:.0f} h floor."
        )
    elif last.sleep_duration_hours is not None and last.sleep_duration_hours < MIN_ACCEPTABLE_SLEEP_H:
        escalate(SleepReadinessBand.CAUTION)
        reasons.append(
            f"Last-night sleep {last.sleep_duration_hours:.1f} h below "
            f"{MIN_ACCEPTABLE_SLEEP_H:.0f} h acceptable threshold."
        )

    # --- Cumulative debt ----------------------------------------------------
    if debt.cumulative_debt_hours is not None:
        if debt.cumulative_debt_hours >= OPERATIONAL_SLEEP_DEBT_NOGO_H:
            escalate(SleepReadinessBand.NO_GO)
            reasons.append(
                f"7-night sleep debt {debt.cumulative_debt_hours:.1f} h "
                f"≥ {OPERATIONAL_SLEEP_DEBT_NOGO_H:.0f} h hard gate."
            )
        elif debt.cumulative_debt_hours >= OPERATIONAL_SLEEP_DEBT_CAUTION_H:
            escalate(SleepReadinessBand.CAUTION)
            reasons.append(
                f"7-night sleep debt {debt.cumulative_debt_hours:.1f} h "
                f"in CAUTION band ({OPERATIONAL_SLEEP_DEBT_CAUTION_H:.0f}-"
                f"{OPERATIONAL_SLEEP_DEBT_NOGO_H:.0f} h)."
            )
        elif debt.cumulative_debt_hours >= 2.0:
            escalate(SleepReadinessBand.GO_MONITOR)
            reasons.append(
                f"7-night sleep debt {debt.cumulative_debt_hours:.1f} h "
                f"(monitor; CRM awareness)."
            )

    # --- Regularity ---------------------------------------------------------
    if regularity.sri_percent is not None and regularity.sri_percent < SRI_IRREGULAR_CAUTION:
        escalate(SleepReadinessBand.CAUTION)
        reasons.append(
            f"Sleep Regularity Index {regularity.sri_percent:.0f}% < "
            f"{SRI_IRREGULAR_CAUTION:.0f}% (irregular schedule; Lunsford-Avery 2018)."
        )

    # --- SpO2 screening proxy (never NO-GO alone) ---------------------------
    if spo2.band == SpO2ScreeningBand.HIGH_FLAG:
        escalate(SleepReadinessBand.CAUTION)
        reasons.append(
            f"Low-SpO₂ screening flag: {spo2.low_spo2_nights_7d} nights < "
            f"{SPO2_LOW_NIGHT_THRESHOLD:.0f}% in the last 7 (screening only; not apnea)."
        )
    elif spo2.band == SpO2ScreeningBand.ELEVATED_FLAG:
        escalate(SleepReadinessBand.GO_MONITOR)
        reasons.append(
            f"Low-SpO₂ screening flag: {spo2.low_spo2_nights_7d} nights < "
            f"{SPO2_LOW_NIGHT_THRESHOLD:.0f}% in the last 7 (screening only)."
        )

    inputs = {
        "last_sleep_hours": last.sleep_duration_hours,
        "cumulative_debt_hours_7d": debt.cumulative_debt_hours,
        "sleep_regularity_index": regularity.sri_percent,
        "bedtime_sd_minutes": regularity.bedtime_sd_minutes,
        "low_spo2_nights_7d": spo2.low_spo2_nights_7d,
        "mean_spo2_7d": spo2.mean_spo2,
    }

    return SleepReadinessResult(decision=decision, reasons=reasons, inputs=inputs)


# =============================================================================
# Session / bulk aggregator for API use
# =============================================================================

@dataclass(frozen=True)
class SleepSummary:
    """Everything the frontend dashboards need in one payload."""
    n_nights_total: int
    n_nights_with_duration: int
    latest_night_date: Optional[str]

    mean_sleep_duration_hours_30d: Optional[float]
    mean_sleep_efficiency_30d: Optional[float]
    mean_sleep_score_30d: Optional[float]

    debt_7d: SleepDebtResult
    regularity_14d: RegularityResult
    spo2_screen_7d: SpO2ScreeningResult
    readiness: SleepReadinessResult
    stage_balance_latest: StageBalance


def summarise(records: list[NightlyRecord]) -> SleepSummary:
    """Full aggregate for `/api/research/garmin/sleep-summary/{user_id}`."""
    with_duration = [r for r in records if _finite(r.sleep_duration_hours)]
    last30 = records[-30:] if records else []

    mean_dur = _mean([r.sleep_duration_hours for r in last30])
    mean_eff = _mean([r.sleep_efficiency for r in last30])
    mean_score = _mean([r.sleep_score for r in last30])

    latest_date = records[-1].metric_date.isoformat() if records else None
    latest_stage = compute_stage_balance(records[-1]) if records else StageBalance(
        None, None, None, None, None, None, None, None,
    )

    debt = compute_sleep_debt(records)
    reg = compute_sleep_regularity(records)
    spo2 = compute_spo2_screening(records)
    readiness = operational_sleep_gate(records)

    return SleepSummary(
        n_nights_total=len(records),
        n_nights_with_duration=len(with_duration),
        latest_night_date=latest_date,
        mean_sleep_duration_hours_30d=mean_dur,
        mean_sleep_efficiency_30d=mean_eff,
        mean_sleep_score_30d=mean_score,
        debt_7d=debt,
        regularity_14d=reg,
        spo2_screen_7d=spo2,
        readiness=readiness,
        stage_balance_latest=latest_stage,
    )


# =============================================================================
# Correlation engine (Pending.md §5) — Pearson / Spearman + FDR
# =============================================================================

@dataclass(frozen=True)
class CorrelationResult:
    metric_x: str
    metric_y: str
    method: str
    n_nights: int
    r: Optional[float]
    p_value: Optional[float]
    fdr_q: Optional[float] = None
    note: Optional[str] = None


def _extract(records: list[NightlyRecord], key: str) -> list[Optional[float]]:
    return [getattr(r, key, None) for r in records]


def _pair(
    records: list[NightlyRecord], key_x: str, key_y: str,
) -> tuple[list[float], list[float]]:
    xs, ys = _extract(records, key_x), _extract(records, key_y)
    paired_x: list[float] = []
    paired_y: list[float] = []
    for x, y in zip(xs, ys):
        if _finite(x) and _finite(y):
            paired_x.append(float(x))
            paired_y.append(float(y))
    return paired_x, paired_y


def _pearson(xs: list[float], ys: list[float]) -> tuple[Optional[float], Optional[float]]:
    """Pearson r with two-sided p. Uses scipy if available, else a pure-Python
    fallback with the standard normal approximation for p."""
    n = len(xs)
    if n < 3:
        return None, None
    try:
        from scipy import stats as _stats  # type: ignore
        r, p = _stats.pearsonr(xs, ys)
        return float(r), float(p)
    except ImportError:
        pass

    # Pure-Python fallback
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sx = sum((x - mean_x) ** 2 for x in xs)
    sy = sum((y - mean_y) ** 2 for y in ys)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    if sx <= 0 or sy <= 0:
        return None, None
    r = sxy / math.sqrt(sx * sy)
    r = max(-1.0, min(1.0, r))
    if abs(r) >= 1.0:
        return r, 0.0
    t = r * math.sqrt((n - 2) / max(1e-12, (1 - r * r)))
    # Two-sided p via Student t asymptotic (reasonable for n ≥ 14)
    # Use an asymptotic Normal approximation to avoid depending on scipy.
    p = 2.0 * (1.0 - _phi(abs(t)))
    return r, max(0.0, min(1.0, p))


def _phi(x: float) -> float:
    """Standard-normal CDF via erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _spearman(xs: list[float], ys: list[float]) -> tuple[Optional[float], Optional[float]]:
    if len(xs) < 3:
        return None, None
    try:
        from scipy import stats as _stats  # type: ignore
        r, p = _stats.spearmanr(xs, ys)
        return float(r), float(p)
    except ImportError:
        pass
    rx = _rank(xs)
    ry = _rank(ys)
    return _pearson(rx, ry)


def _rank(xs: list[float]) -> list[float]:
    """Average rank for ties (mirrors scipy.stats.rankdata 'average')."""
    indexed = sorted(enumerate(xs), key=lambda kv: kv[1])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg
        i = j + 1
    return ranks


def _bh_fdr(ps: list[Optional[float]]) -> list[Optional[float]]:
    """Benjamini-Hochberg FDR adjustment; None-safe."""
    valid = [(i, p) for i, p in enumerate(ps) if p is not None]
    if not valid:
        return [None] * len(ps)
    m = len(valid)
    sorted_by_p = sorted(valid, key=lambda ip: ip[1])
    qs = [None] * len(ps)
    prev = 1.0
    for rank_pos, (orig_i, p) in enumerate(reversed(sorted_by_p), start=1):
        k = m - rank_pos + 1
        q = p * m / k
        q = min(q, prev)
        prev = q
        qs[orig_i] = float(max(0.0, min(1.0, q)))
    return qs


def compute_correlations(
    records: list[NightlyRecord],
    *,
    method: str = "pearson",
    pairs: Optional[list[tuple[str, str]]] = None,
    min_n: int = MIN_NIGHTS_FOR_STATS,
) -> list[CorrelationResult]:
    """Compute Tier A scatter correlations listed in Pending.md §4 Tier A.

    Returns list with r, two-sided p, FDR-adjusted q across the batch, and
    n_nights. When n < min_n the result is flagged underpowered via `note`.
    """
    if pairs is None:
        pairs = [
            ("sleep_duration_hours", "hrv_rmssd_ms"),
            ("sleep_score", "hrv_rmssd_ms"),
            ("sleep_efficiency", "hrv_rmssd_ms"),
            ("sleep_deep_minutes", "hrv_rmssd_ms"),
            ("sleep_rem_minutes", "hrv_rmssd_ms"),
            ("resting_hr_bpm", "hrv_rmssd_ms"),
            ("avg_spo2", "hrv_rmssd_ms"),
            ("avg_respiration_sleep", "hrv_rmssd_ms"),
        ]
    corr_fn = _spearman if method.lower() == "spearman" else _pearson

    raw_results: list[CorrelationResult] = []
    ps: list[Optional[float]] = []
    for key_x, key_y in pairs:
        xs, ys = _pair(records, key_x, key_y)
        r, p = corr_fn(xs, ys)
        note = None if len(xs) >= min_n else f"Underpowered (n={len(xs)} < {min_n})"
        raw_results.append(CorrelationResult(
            metric_x=key_x, metric_y=key_y, method=method.lower(),
            n_nights=len(xs), r=r, p_value=p, note=note,
        ))
        ps.append(p)

    qs = _bh_fdr(ps)
    # Attach q values
    out: list[CorrelationResult] = []
    for base, q in zip(raw_results, qs):
        out.append(CorrelationResult(
            metric_x=base.metric_x, metric_y=base.metric_y, method=base.method,
            n_nights=base.n_nights, r=base.r, p_value=base.p_value,
            fdr_q=q, note=base.note,
        ))
    return out


# =============================================================================
# Builders
# =============================================================================

def build_records_from_raw(rows: Iterable[dict]) -> list[NightlyRecord]:
    """Build NightlyRecord list from raw Garmin-daily dict rows.

    `metric_date` accepts ISO-date strings or `datetime.date` objects.
    `sleep_start_utc` / `sleep_end_utc` accept ISO-8601 strings.
    """
    out: list[NightlyRecord] = []
    for row in rows:
        md = row.get("metric_date")
        if isinstance(md, str):
            md_parsed = date.fromisoformat(md[:10])
        elif isinstance(md, date):
            md_parsed = md
        else:
            continue

        def _dt(s: Any) -> Optional[datetime]:
            if s is None:
                return None
            if isinstance(s, datetime):
                return s
            if isinstance(s, str):
                try:
                    return datetime.fromisoformat(s.replace("Z", "+00:00"))
                except ValueError:
                    return None
            return None

        def _f(v: Any) -> Optional[float]:
            try:
                if v is None:
                    return None
                return float(v)
            except (TypeError, ValueError):
                return None

        def _i(v: Any) -> Optional[int]:
            try:
                if v is None:
                    return None
                return int(v)
            except (TypeError, ValueError):
                return None

        out.append(NightlyRecord(
            metric_date=md_parsed,
            sleep_duration_hours=_f(row.get("sleep_duration_hours")),
            sleep_efficiency=_f(row.get("sleep_efficiency")),
            sleep_score=_f(row.get("sleep_score")),
            sleep_start_utc=_dt(row.get("sleep_start_utc")),
            sleep_end_utc=_dt(row.get("sleep_end_utc")),
            sleep_deep_minutes=_i(row.get("sleep_deep_minutes")),
            sleep_rem_minutes=_i(row.get("sleep_rem_minutes")),
            sleep_light_minutes=_i(row.get("sleep_light_minutes")),
            sleep_awake_minutes=_i(row.get("sleep_awake_minutes")),
            hrv_rmssd_ms=_f(row.get("hrv_rmssd_ms")),
            hrv_sdnn_ms=_f(row.get("hrv_sdnn_ms")),
            resting_hr_bpm=_f(row.get("resting_hr_bpm")),
            avg_spo2=_f(row.get("avg_spo2")),
            avg_respiration_awake=_f(row.get("avg_respiration_awake")),
            avg_respiration_sleep=_f(row.get("avg_respiration_sleep")),
            body_battery_avg=_f(row.get("body_battery_avg")),
            stress_score=_f(row.get("stress_score")),
        ))
    # Ensure chronological order
    out.sort(key=lambda r: r.metric_date)
    return out


__all__ = [
    # Constants
    "TYPICAL_SLEEP_DURATION_H", "MIN_ACCEPTABLE_SLEEP_H", "HARD_FLOOR_SLEEP_H",
    "OPERATIONAL_SLEEP_DEBT_CAUTION_H", "OPERATIONAL_SLEEP_DEBT_NOGO_H",
    "SLEEP_EFFICIENCY_OPTIMAL", "SLEEP_EFFICIENCY_POOR",
    "DEEP_PCT_HEALTHY_LOW", "DEEP_PCT_HEALTHY_HIGH",
    "REM_PCT_HEALTHY_LOW", "REM_PCT_HEALTHY_HIGH",
    "SPO2_LOW_NIGHT_THRESHOLD", "SPO2_LOW_NIGHT_CAUTION_7D", "SPO2_LOW_NIGHT_NOGO_7D",
    "SRI_HIGH_REGULARITY", "SRI_MODERATE_REGULARITY", "SRI_IRREGULAR_CAUTION",
    "ROLLING_7D_WINDOW_DAYS", "ROLLING_14D_WINDOW_DAYS", "ROLLING_30D_WINDOW_DAYS",
    "MIN_NIGHTS_FOR_STATS",
    # Enums
    "SleepReadinessBand", "SpO2ScreeningBand",
    # Dataclasses
    "NightlyRecord", "StageBalance", "SleepDebtResult", "RegularityResult",
    "SpO2ScreeningResult", "SleepReadinessResult", "SleepSummary",
    "CorrelationResult",
    # Functions
    "compute_stage_balance", "compute_sleep_debt", "compute_sleep_regularity",
    "compute_spo2_screening", "operational_sleep_gate", "summarise",
    "compute_correlations", "build_records_from_raw",
]
