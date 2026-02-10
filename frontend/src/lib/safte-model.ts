// Author: Dr Diego Malpica MD
// ---------------------------------------------------------------------------
// Reservoir-Based SAFTE Model  (Hursh et al. 2004 / DRDC Peng & Bouak 2015)
// Shared module used by both Research and Operational tabs.
//
// Equations (matching backend safte_model.py):
//   E(t) = 100 * (homeo% + circ% + inertia%) / norm
//   homeo% = 100 * R_t / R_c
//   circ%  = (a1 + a2 * (1 - R_t/R_c)) * C_t
//   C_t    = cos(2π(t-p)/24) + β·cos(4π(t-p')/24)
//   R_t    = R_{t-1} - K·Δt          (wake)
//   R_t    = R_{t-1} + f·(R_c-R)·Δt  (sleep, simplified)
// ---------------------------------------------------------------------------

/** SAFTE parameters — identical to safte_model.py defaults */
export const SAFTE = {
  R_c: 2880.0,        // Reservoir capacity (units)
  K: 0.5,             // Wake depletion rate (units / min)
  f: 0.01,            // Sleep recovery rate constant (per min)
  a_s: 0.05,          // Circadian effect on recovery (per min)
  p: 18.0,            // 24 h circadian peak phase (hours)
  p_prime: 3.0,       // 12 h harmonic phase offset (hours)
  beta: 0.5,          // 12 h harmonic relative amplitude
  a1: 7.8,            // Base circadian contribution (%)
  a2: 5.0,            // Fatigue-dependent circadian (%)
  norm: 96.7,         // Normalization constant (%)
} as const;

export interface SAFTEForecast {
  hours: number[];
  effectiveness: number[];
  reservoir_pct: number[];   // R/R_c as percentage (Process S)
  circadian_drive: number[]; // Raw C_t (Process C)
  clockHours: number[];      // Absolute clock hours for each point
  isAsleep: boolean[];       // Whether subject is asleep at each point
}

/** Two-harmonic circadian drive — matches safte_model.py circadian() */
export function circadianDrive(clockHour: number): number {
  const phaseRel = (clockHour - SAFTE.p + 24) % 24;
  const c1 = Math.cos((2 * Math.PI * phaseRel) / 24);
  const c2 = Math.cos((4 * Math.PI * (phaseRel - SAFTE.p_prime)) / 24);
  return c1 + SAFTE.beta * c2;
}

/**
 * Derive initial reservoir level from effectiveness.
 * Inverts: E = 100 * (100*R/R_c + (a1 + a2*(1-R/R_c))*C_t) / norm
 */
export function reservoirFromEffectiveness(E_pct: number, C_t: number): number {
  const numerator = (E_pct * SAFTE.norm) / 100 - (SAFTE.a1 + SAFTE.a2) * C_t;
  const denominator = 100 - SAFTE.a2 * C_t;
  if (Math.abs(denominator) < 1e-6) return 0.9;
  const ratio = numerator / denominator;
  return Math.max(0, Math.min(1, ratio));
}

/**
 * Compute instantaneous effectiveness from reservoir and clock hour.
 * Used by operational tab for single-point queries.
 */
export function computeEffectiveness(R: number, clockHour: number): number {
  const C_t = circadianDrive(clockHour);
  const homeo_pct = 100 * (R / SAFTE.R_c);
  const circ_pct = (SAFTE.a1 + SAFTE.a2 * (1 - R / SAFTE.R_c)) * C_t;
  const E_pct = (100 * (homeo_pct + circ_pct)) / SAFTE.norm;
  return Math.max(30, Math.min(100, Math.round(E_pct * 10) / 10));
}

/**
 * Default sleep schedule: sleep from bedtime to bedtime + sleepDuration each night.
 * Returns a function that checks if a given clock hour is within a sleep period.
 */
function defaultSleepCheck(
  bedtimeHour: number,
  sleepDurationH: number,
): (clockHour: number) => boolean {
  return (clockHour: number) => {
    // Normalize to bedtime-relative hours
    const rel = (clockHour - bedtimeHour + 24) % 24;
    return rel < sleepDurationH;
  };
}

/**
 * Multi-day SAFTE forecast generator.
 *
 * @param baseEffectiveness  Current effectiveness % from backend
 * @param sleepDebtHours     Current accumulated sleep debt (hours)
 * @param predictionDays     Number of days to forecast (1–7)
 * @param bedtimeHour        Usual bedtime in 24 h format (default 23)
 * @param sleepDurationH     Usual sleep duration in hours (default 7)
 */
export function generateSAFTEForecast(
  baseEffectiveness: number,
  sleepDebtHours: number,
  predictionDays: number = 1,
  bedtimeHour: number = 23,
  sleepDurationH: number = 7,
): SAFTEForecast {
  const now = new Date();
  const currentHour = now.getHours() + now.getMinutes() / 60;
  const dt_min = 30;
  const numPoints = predictionDays * 48; // 48 per day (30-min steps)

  // Initialize reservoir from backend effectiveness
  const C_now = circadianDrive(currentHour);
  let R = reservoirFromEffectiveness(baseEffectiveness, C_now) * SAFTE.R_c;

  // If sleep debt is significant, ensure reservoir reflects it
  const debtDepletion = SAFTE.K * 60 * Math.max(0, sleepDebtHours);
  const R_from_debt = SAFTE.R_c - debtDepletion;
  R = Math.min(R, Math.max(0, R_from_debt));

  const isAsleepFn = defaultSleepCheck(bedtimeHour, sleepDurationH);

  const hours: number[] = [];
  const effectiveness: number[] = [];
  const reservoir_pct: number[] = [];
  const circadian_values: number[] = [];
  const clockHours: number[] = [];
  const isAsleep: boolean[] = [];

  for (let i = 0; i < numPoints; i++) {
    const h = i * 0.5;
    hours.push(h);

    const clockHour = (currentHour + h) % 24;
    clockHours.push(clockHour);
    const C_t = circadianDrive(clockHour);
    const sleeping = isAsleepFn(clockHour);
    isAsleep.push(sleeping);

    // --- Reservoir dynamics ---
    if (i > 0) {
      if (sleeping) {
        // Exponential recovery during sleep (matching safte_model.py line 247)
        const dR = SAFTE.f * (SAFTE.R_c - R) * dt_min - SAFTE.a_s * C_t * dt_min;
        R = Math.min(SAFTE.R_c, Math.max(0, R + dR));
      } else {
        // Linear depletion during wakefulness
        R = Math.max(0, R - SAFTE.K * dt_min);
      }
    }

    // --- Effectiveness (safte_model.py lines 259-276) ---
    const homeo_pct = 100 * (R / SAFTE.R_c);
    const circ_pct = (SAFTE.a1 + SAFTE.a2 * (1 - R / SAFTE.R_c)) * C_t;
    const E_pct = (100 * (homeo_pct + circ_pct)) / SAFTE.norm;

    effectiveness.push(Math.max(30, Math.min(100, Math.round(E_pct * 10) / 10)));
    reservoir_pct.push(Math.round((R / SAFTE.R_c) * 1000) / 10);
    circadian_values.push(Math.round(C_t * 100) / 100);
  }

  return { hours, effectiveness, reservoir_pct, circadian_drive: circadian_values, clockHours, isAsleep };
}

/** Quick current-effectiveness for operational tab (avoids full simulation) */
export function currentSAFTEEffectiveness(sleepDebtHours: number = 0): number {
  const now = new Date();
  const clockHour = now.getHours() + now.getMinutes() / 60;
  const debtDepletion = SAFTE.K * 60 * Math.max(0, sleepDebtHours);
  const R = Math.max(0, SAFTE.R_c - debtDepletion);
  return computeEffectiveness(R, clockHour);
}
