// Author: Dr Diego Malpica MD
// ---------------------------------------------------------------------------
// PVT scoring — TypeScript mirror of app/pvt_core.py (canonical Python).
// Shared by the React PVT test component (operational and research routes).
//
// Validation anchors:
//   • Dinges DF et al. (1997). Sleep 20(4):267-277. DOI 10.1093/sleep/20.4.267
//   • Basner M, Dinges DF (2011). Sleep 34(5):581-591. DOI 10.1093/sleep/34.5.581
//   • Grant DA et al. (2017). Behav Res Methods 49(3):1020-1029.
//       DOI 10.3758/s13428-016-0763-8 — PVT-B on smartphone/tablet.
//   • Anwyl-Irvine A et al. (2020). Behav Res Methods 53:1407-1425.
//       DOI 10.3758/s13428-020-01501-5 — web-browser RT precision.
//
// Canonical Python scoring lives at app/pvt_core.py.
// This mirror is used for client-side preview before round-tripping
// to POST /api/pvt/score or /api/pvt/sessions; the server remains
// authoritative.
// ---------------------------------------------------------------------------

export type PVTVariant = "PVT-B" | "PVT-5" | "PVT-10";

export interface PVTVariantDefaults {
  duration_min: number;
  isi_min_s: number;
  isi_max_s: number;
  lapse_threshold_ms: number;
}

export const PVT_VARIANT_DEFAULTS: Record<PVTVariant, PVTVariantDefaults> = {
  "PVT-B": {
    duration_min: 3.0,
    isi_min_s: 1.0,
    isi_max_s: 4.0,
    lapse_threshold_ms: 355.0, // Basner & Dinges 2011
  },
  "PVT-5": {
    duration_min: 5.0,
    isi_min_s: 2.0,
    isi_max_s: 10.0,
    lapse_threshold_ms: 500.0,
  },
  "PVT-10": {
    duration_min: 10.0,
    isi_min_s: 2.0,
    isi_max_s: 10.0,
    lapse_threshold_ms: 500.0,
  },
};

export const MAJOR_LAPSE_THRESHOLD_MS = 1000.0;
export const FALSE_START_THRESHOLD_MS = 100.0;
export const VALID_RT_MAX_MS = 30_000.0;
export const RESPONSE_WINDOW_MS = 30_000.0;
const MS_PER_S = 1000.0;

export type PVTTrialKind =
  | "valid"
  | "lapse"
  | "major_lapse"
  | "false_start"
  | "no_response";

export interface PVTTrial {
  /** 0-based trial index */
  index: number;
  /** Inter-stimulus interval (ms) */
  isi_ms: number;
  /** Time from session start to stimulus (ms) */
  stimulus_onset_ms: number;
  /** Reaction time (ms); null if no response within the response window */
  rt_ms: number | null;
  /** True if response fired before stimulus */
  anticipatory?: boolean;
}

export interface PVTMetrics {
  variant: PVTVariant;
  duration_min: number;
  lapse_threshold_ms: number;
  started_at?: string | null;
  ended_at?: string | null;
  user_id?: string | null;
  device_label?: string | null;
  software_version?: string | null;
  // Trial counts
  n_trials: number;
  n_valid_trials: number;
  n_false_starts: number;
  n_no_response: number;
  n_lapses: number;
  n_major_lapses: number;
  // Core RT (ms)
  mean_rt_ms: number | null;
  median_rt_ms: number | null;
  sd_rt_ms: number | null;
  min_rt_ms: number | null;
  max_rt_ms: number | null;
  p10_rt_ms: number | null;
  p90_rt_ms: number | null;
  cv_rt: number | null;
  fastest_10pct_mean_rt_ms: number | null;
  slowest_10pct_mean_rt_ms: number | null;
  // Response speed (1/s)
  mean_response_speed_per_s: number | null;
  median_response_speed_per_s: number | null;
  fastest_10pct_mean_speed_per_s: number | null;
  slowest_10pct_mean_speed_per_s: number | null;
  // Derived
  transformed_lapses: number;
  response_speed_index: number | null;
  // Operational gate input
  pvt_lapses_3min: number;
}

export type GateDecision = "GO" | "GO_MONITOR" | "CAUTION" | "NO_GO";

export interface PVTGateResult {
  decision: GateDecision;
  pvt_lapses_3min: number;
  n_valid_trials: number;
  n_false_starts: number;
  reasons: string[];
}

// ---------------------------------------------------------------------------
// Trial classification
// ---------------------------------------------------------------------------

export function classifyTrial(trial: PVTTrial, lapseThresholdMs: number): PVTTrialKind {
  if (trial.anticipatory) return "false_start";
  if (trial.rt_ms === null || trial.rt_ms === undefined) return "no_response";
  if (trial.rt_ms < FALSE_START_THRESHOLD_MS) return "false_start";
  if (trial.rt_ms > VALID_RT_MAX_MS) return "no_response";
  if (trial.rt_ms >= MAJOR_LAPSE_THRESHOLD_MS) return "major_lapse";
  if (trial.rt_ms >= lapseThresholdMs) return "lapse";
  return "valid";
}

// ---------------------------------------------------------------------------
// Descriptive stats helpers (match Python statistics module semantics)
// ---------------------------------------------------------------------------

function mean(xs: number[]): number | null {
  if (xs.length === 0) return null;
  return xs.reduce((s, x) => s + x, 0) / xs.length;
}

function median(xs: number[]): number | null {
  if (xs.length === 0) return null;
  const sorted = [...xs].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2
    ? sorted[mid]
    : (sorted[mid - 1] + sorted[mid]) / 2;
}

function pstdev(xs: number[]): number | null {
  if (xs.length < 2) return null;
  const m = mean(xs) as number;
  const variance =
    xs.reduce((s, x) => s + (x - m) ** 2, 0) / xs.length;
  return Math.sqrt(variance);
}

function percentile(xs: number[], p: number): number | null {
  if (xs.length === 0) return null;
  const sorted = [...xs].sort((a, b) => a - b);
  if (sorted.length === 1) return sorted[0];
  const k = (sorted.length - 1) * (p / 100);
  const lo = Math.floor(k);
  const hi = Math.ceil(k);
  if (lo === hi) return sorted[lo];
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (k - lo);
}

function meanOfSlice(xs: number[], k: number, fromStart: boolean): number | null {
  if (xs.length === 0 || k <= 0) return null;
  const sorted = [...xs].sort((a, b) => a - b);
  const slice = fromStart ? sorted.slice(0, k) : sorted.slice(-k);
  return mean(slice);
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

export interface ScoreOptions {
  variant: PVTVariant;
  duration_min?: number;
  lapse_threshold_ms?: number;
  user_id?: string | null;
  device_label?: string | null;
  software_version?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
}

export function scoreTrials(trials: PVTTrial[], opts: ScoreOptions): PVTMetrics {
  const defaults = PVT_VARIANT_DEFAULTS[opts.variant];
  const duration = opts.duration_min ?? defaults.duration_min;
  const lapseMs = opts.lapse_threshold_ms ?? defaults.lapse_threshold_ms;

  const validRt: number[] = [];
  let nLapse = 0;
  let nMajor = 0;
  let nFalse = 0;
  let nNoResp = 0;

  for (const t of trials) {
    const kind = classifyTrial(t, lapseMs);
    if (kind === "valid" && t.rt_ms !== null) {
      validRt.push(t.rt_ms);
    } else if (kind === "lapse" && t.rt_ms !== null) {
      validRt.push(t.rt_ms);
      nLapse += 1;
    } else if (kind === "major_lapse" && t.rt_ms !== null) {
      validRt.push(t.rt_ms);
      nLapse += 1;
      nMajor += 1;
    } else if (kind === "false_start") {
      nFalse += 1;
    } else if (kind === "no_response") {
      nNoResp += 1;
    }
  }

  const nValid = validRt.length;
  const meanRt = mean(validRt);
  const medRt = median(validRt);
  const sdRt = pstdev(validRt);
  const minRt = nValid > 0 ? Math.min(...validRt) : null;
  const maxRt = nValid > 0 ? Math.max(...validRt) : null;
  const p10 = percentile(validRt, 10);
  const p90 = percentile(validRt, 90);
  const cv = sdRt !== null && meanRt !== null && meanRt !== 0 ? sdRt / meanRt : null;

  const kTail = nValid > 0 ? Math.max(1, Math.round(nValid * 0.1)) : 0;
  const fastest10Rt = meanOfSlice(validRt, kTail, true);
  const slowest10Rt = meanOfSlice(validRt, kTail, false);

  const speeds = validRt.map((rt) => MS_PER_S / rt);
  const meanSpeed = mean(speeds);
  const medianSpeed = median(speeds);
  // fastest RT → largest 1/RT → slice from END of sorted speeds
  const fastest10Speed = meanOfSlice(speeds, kTail, false);
  const slowest10Speed = meanOfSlice(speeds, kTail, true);

  const transformedLapses = Math.sqrt(nLapse) + Math.sqrt(nLapse + 1);

  const pvtLapses3min =
    opts.variant === "PVT-B"
      ? nLapse
      : Math.round(nLapse * (3.0 / (duration || 1)));

  return {
    variant: opts.variant,
    duration_min: duration,
    lapse_threshold_ms: lapseMs,
    started_at: opts.started_at ?? null,
    ended_at: opts.ended_at ?? null,
    user_id: opts.user_id ?? null,
    device_label: opts.device_label ?? null,
    software_version: opts.software_version ?? null,
    n_trials: trials.length,
    n_valid_trials: nValid,
    n_false_starts: nFalse,
    n_no_response: nNoResp,
    n_lapses: nLapse,
    n_major_lapses: nMajor,
    mean_rt_ms: meanRt,
    median_rt_ms: medRt,
    sd_rt_ms: sdRt,
    min_rt_ms: minRt,
    max_rt_ms: maxRt,
    p10_rt_ms: p10,
    p90_rt_ms: p90,
    cv_rt: cv,
    fastest_10pct_mean_rt_ms: fastest10Rt,
    slowest_10pct_mean_rt_ms: slowest10Rt,
    mean_response_speed_per_s: meanSpeed,
    median_response_speed_per_s: medianSpeed,
    fastest_10pct_mean_speed_per_s: fastest10Speed,
    slowest_10pct_mean_speed_per_s: slowest10Speed,
    transformed_lapses: transformedLapses,
    response_speed_index: meanSpeed,
    pvt_lapses_3min: pvtLapses3min,
  };
}

// ---------------------------------------------------------------------------
// Operational gate (mirrors app.pvt_core.operational_gate)
// ---------------------------------------------------------------------------

export function operationalGate(metrics: PVTMetrics): PVTGateResult {
  const lapses = metrics.pvt_lapses_3min ?? 0;
  const nValid = metrics.n_valid_trials ?? 0;
  const nFalse = metrics.n_false_starts ?? 0;
  const reasons: string[] = [];

  if (nValid < 20) reasons.push("Insufficient valid trials (<20); retest.");
  if (nFalse > 10)
    reasons.push(`Excessive false starts (${nFalse}); rushed responses.`);

  let decision: GateDecision;
  if (lapses >= 20) {
    decision = "NO_GO";
    reasons.push(`PVT lapses ≥ 20 (got ${lapses}); low-performance gate.`);
  } else if (lapses >= 10) {
    decision = "CAUTION";
    reasons.push(`PVT lapses ${lapses} in 10–19; enhanced monitoring.`);
  } else if (lapses >= 5) {
    decision = "GO_MONITOR";
    reasons.push(`PVT lapses ${lapses} in 5–9; proceed with CRM awareness.`);
  } else {
    decision = "GO";
  }

  return {
    decision,
    pvt_lapses_3min: lapses,
    n_valid_trials: nValid,
    n_false_starts: nFalse,
    reasons,
  };
}

// ---------------------------------------------------------------------------
// ISI schedule generator (mirrors app.pvt_core.generate_isi_schedule)
// ---------------------------------------------------------------------------

export function generateIsiSchedule(variant: PVTVariant, rng: () => number = Math.random): number[] {
  const d = PVT_VARIANT_DEFAULTS[variant];
  const durationMs = d.duration_min * 60 * MS_PER_S;
  const isiMinMs = d.isi_min_s * MS_PER_S;
  const isiMaxMs = d.isi_max_s * MS_PER_S;

  const schedule: number[] = [];
  let totalMs = 0;
  const expectedResponseMs = 500;
  while (totalMs < durationMs) {
    const isiMs = isiMinMs + rng() * (isiMaxMs - isiMinMs);
    schedule.push(isiMs);
    totalMs += isiMs + expectedResponseMs;
  }
  return schedule;
}

// ---------------------------------------------------------------------------
// Utility: seed-based RNG for reproducible schedules
// ---------------------------------------------------------------------------

/** Mulberry32 — compact, deterministic 32-bit RNG, sufficient for ISI shuffling. */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4_294_967_296;
  };
}
