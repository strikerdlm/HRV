// Author: Dr Diego Malpica MD
// ---------------------------------------------------------------------------
// Sleep metrics — TypeScript types + chart-axis helpers + thresholds.
//
// Canonical scoring and gate logic live in app/sleep_core.py and are
// exposed by the FastAPI router at /api/research/garmin/sleep-*. This
// module mirrors the *constants* and *type shapes* for the Next.js
// frontend to display them consistently; no metric calculations are
// duplicated client-side.
//
// Validation anchors (full list in docs/SLEEP.md):
//   • Lunsford-Avery et al. (2018). Validation of the Sleep Regularity
//     Index in Older Adults. Scientific Reports 8. DOI 10.1038/s41598-
//     018-32402-5.
//   • Lee YJ et al. (2025). Meta-analysis of consumer wrist-worn sleep
//     tracking devices vs polysomnography. J Clin Sleep Med 21(3):573-
//     582. DOI 10.5664/jcsm.11460. — Garmin validity bound used for
//     the chart disclosure.
//   • Task Force ESC/NASPE (1996) — HRV standards. PMID 8598068.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Readiness and screening enums (mirror app.sleep_core)
// ---------------------------------------------------------------------------

export type SleepReadinessBand = "GO" | "GO_MONITOR" | "CAUTION" | "NO_GO";

export type SpO2ScreeningBand =
  | "NORMAL"
  | "MILD_FLAG"
  | "ELEVATED_FLAG"
  | "HIGH_FLAG";

// ---------------------------------------------------------------------------
// Operational thresholds (mirror app.sleep_core)
// ---------------------------------------------------------------------------

export const SLEEP_THRESHOLDS = {
  typicalTargetHours: 7.5,
  minAcceptableHours: 6.0,
  hardFloorHours: 5.0,
  debtCautionHours7d: 4.0,
  debtNoGoHours7d: 8.0,
  efficiencyOptimal: 0.85,
  efficiencyPoor: 0.75,
  spo2LowThreshold: 92.0,
  spo2CautionNights7d: 2,
  spo2NoGoNights7d: 4,
  sriHighRegularity: 80.0,
  sriModerateRegularity: 60.0,
  sriIrregularCaution: 40.0,
  minNightsForStats: 14,
  deepPctHealthyLow: 0.10,
  deepPctHealthyHigh: 0.25,
  remPctHealthyLow: 0.15,
  remPctHealthyHigh: 0.30,
} as const;

// ---------------------------------------------------------------------------
// Response shapes from /api/research/garmin/sleep-*
// ---------------------------------------------------------------------------

export interface SleepDebt7d {
  window_nights: number;
  typical_target_hours: number;
  observed_mean_hours: number | null;
  observed_total_hours: number | null;
  target_total_hours: number;
  cumulative_debt_hours: number | null;
  nightly_deficits: Array<number | null>;
}

export interface Regularity14d {
  window_nights: number;
  n_pairs: number;
  sri_percent: number | null;
  bedtime_sd_minutes: number | null;
  waketime_sd_minutes: number | null;
  midpoint_sd_minutes: number | null;
}

export interface SpO2Screen7d {
  window_nights: number;
  n_valid_nights: number;
  low_spo2_nights: number;
  low_spo2_nights_7d: number;
  mean_spo2: number | null;
  band: SpO2ScreeningBand;
}

export interface SleepReadiness {
  decision: SleepReadinessBand;
  reasons: string[];
  inputs: Record<string, unknown>;
}

export interface StageBalance {
  total_minutes: number | null;
  deep_pct: number | null;
  rem_pct: number | null;
  light_pct: number | null;
  awake_pct: number | null;
  deep_plus_rem_pct: number | null;
  deep_plus_rem_minutes: number | null;
  deep_to_rem_ratio: number | null;
}

export interface SleepSummary {
  n_nights_total: number;
  n_nights_with_duration: number;
  latest_night_date: string | null;
  mean_sleep_duration_hours_30d: number | null;
  mean_sleep_efficiency_30d: number | null;
  mean_sleep_score_30d: number | null;
  debt_7d: SleepDebt7d;
  regularity_14d: Regularity14d;
  spo2_screen_7d: SpO2Screen7d;
  readiness: SleepReadiness;
  stage_balance_latest: StageBalance;
}

export interface SleepCorrelation {
  metric_x: string;
  metric_y: string;
  method: string;
  n_nights: number;
  r: number | null;
  p_value: number | null;
  fdr_q: number | null;
  note: string | null;
}

export interface SleepCorrelationsResponse {
  user_id: string;
  method: string;
  n_nights_window: number;
  min_nights_for_stats: number;
  results: SleepCorrelation[];
}

export interface SleepDebtTrendPoint {
  metric_date: string;
  sleep_duration_hours: number | null;
  deficit_hours: number | null;
  rolling_debt_7d_hours: number | null;
}

export interface SleepDebtTrendResponse {
  user_id: string;
  typical_target_hours: number;
  series: SleepDebtTrendPoint[];
}

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

export function formatHours(h: number | null | undefined, digits = 1): string {
  return h == null || !Number.isFinite(h) ? "—" : `${h.toFixed(digits)} h`;
}

export function formatMinutes(m: number | null | undefined): string {
  if (m == null || !Number.isFinite(m)) return "—";
  const h = Math.floor(m / 60);
  const mm = Math.round(m % 60);
  return h > 0 ? `${h}h ${mm}m` : `${mm}m`;
}

export function formatPercent(v: number | null | undefined, digits = 0): string {
  return v == null || !Number.isFinite(v) ? "—" : `${(v * 100).toFixed(digits)}%`;
}

export function formatSpO2(v: number | null | undefined): string {
  return v == null || !Number.isFinite(v) ? "—" : `${v.toFixed(1)}%`;
}

export function formatRInline(c: SleepCorrelation): string {
  if (c.r == null) return `r = — (n=${c.n_nights})`;
  const p = c.p_value != null ? `, p=${formatP(c.p_value)}` : "";
  const q = c.fdr_q != null ? `, q=${formatP(c.fdr_q)}` : "";
  return `r = ${c.r.toFixed(2)} (n=${c.n_nights}${p}${q})`;
}

export function formatP(p: number): string {
  if (p < 0.001) return "<0.001";
  if (p < 0.01) return p.toFixed(3);
  return p.toFixed(2);
}

export function decisionColour(d: SleepReadinessBand): string {
  switch (d) {
    case "GO":
      return "#27ae60";
    case "GO_MONITOR":
      return "#8BC34A";
    case "CAUTION":
      return "#f39c12";
    case "NO_GO":
      return "#e74c3c";
  }
}

export function screeningColour(b: SpO2ScreeningBand): string {
  switch (b) {
    case "NORMAL":
      return "#27ae60";
    case "MILD_FLAG":
      return "#8BC34A";
    case "ELEVATED_FLAG":
      return "#f39c12";
    case "HIGH_FLAG":
      return "#e74c3c";
  }
}

// ---------------------------------------------------------------------------
// Human-readable labels for the Tier A metric pair set
// ---------------------------------------------------------------------------

export const METRIC_LABELS: Record<string, string> = {
  sleep_duration_hours: "Sleep duration (h)",
  sleep_score: "Sleep score",
  sleep_efficiency: "Sleep efficiency",
  sleep_deep_minutes: "Deep sleep (min)",
  sleep_rem_minutes: "REM sleep (min)",
  resting_hr_bpm: "Resting HR (bpm)",
  avg_spo2: "Avg SpO₂ (%)",
  avg_respiration_sleep: "Sleep respiration (bpm)",
  hrv_rmssd_ms: "Overnight HRV RMSSD (ms)",
};

export function metricLabel(key: string): string {
  return METRIC_LABELS[key] ?? key;
}

// ---------------------------------------------------------------------------
// Significance colour for correlation matrices
// ---------------------------------------------------------------------------

export function correlationSignificanceColour(c: SleepCorrelation): string {
  // Grey if underpowered or missing
  if (c.note != null || c.r == null || c.p_value == null) return "#bdc3c7";
  // Use FDR-adjusted q when available, else raw p
  const p = c.fdr_q ?? c.p_value;
  if (p >= 0.05) return "#bdc3c7";
  if (c.r > 0) return "#3498db";
  return "#e74c3c";
}

export function correlationAlpha(c: SleepCorrelation): number {
  if (c.note != null || c.r == null) return 0.3;
  return Math.min(1.0, Math.max(0.25, Math.abs(c.r)));
}
