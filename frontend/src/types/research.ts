// Author: Dr Diego Malpica MD
/**
 * TypeScript interfaces for Research features:
 * - Space Weather
 * - HRV Analysis
 * - Correlations
 * - Garmin Integration
 */

// ---------------------------------------------------------------------------
// Space Weather Types
// ---------------------------------------------------------------------------

export interface SpaceWeatherData {
  kp_index: number | null;
  kp_status: string | null;
  dst_index: number | null;
  f10_7_flux: number | null;
  f10_7_status: string | null;
  solar_wind_speed: number | null;
  solar_wind_density: number | null;
  solar_wind_bz: number | null;
  xray_flux: string | null;
  xray_class: string | null;
  proton_flux_10mev: number | null;
  proton_flux_100mev: number | null;
  sep_event_active: boolean;
  geomagnetic_status: string | null;
  radiation_status: string | null;
  fetched_at: string | null;
}

export type ImpactSeverity =
  | "quiet"
  | "minor"
  | "moderate"
  | "strong"
  | "severe"
  | "extreme";

export type EnergyCategory =
  | "photon"
  | "sep"
  | "plasma_l1"
  | "cme_shock"
  | "hss"
  | "geomagnetic";

export interface ImpactPrediction {
  category: EnergyCategory;
  severity: ImpactSeverity;
  observation_time: string | null;
  arrival_time: string | null;
  travel_time_minutes: number | null;
  biological_effect: string | null;
  polar_h10_recommendation: string | null;
  raw_value: number | null;
  unit: string | null;
  confidence: number;
}

export interface SpaceWeatherSnapshot {
  data: SpaceWeatherData;
  predictions: ImpactPrediction[];
  next_impact: ImpactPrediction | null;
  most_severe: ImpactPrediction | null;
  errors: Record<string, string>;
}

// ---------------------------------------------------------------------------
// HRV Analysis Types
// ---------------------------------------------------------------------------

export interface HRVTimeDomain {
  mean_hr: number | null;
  sdnn: number | null;
  rmssd: number | null;
  pnn50: number | null;
  pnn20: number | null;
  cvnn: number | null;
  mean_rr: number | null;
  sdsd: number | null;
  nn50: number | null;
  nn20: number | null;
}

export interface HRVFrequencyDomain {
  vlf_power: number | null;
  lf_power: number | null;
  hf_power: number | null;
  total_power: number | null;
  lf_nu: number | null;
  hf_nu: number | null;
  lf_hf_ratio: number | null;
  vlf_peak: number | null;
  lf_peak: number | null;
  hf_peak: number | null;
}

export interface HRVNonlinear {
  sd1: number | null;
  sd2: number | null;
  sd1_sd2_ratio: number | null;
  dfa_alpha1: number | null;
  dfa_alpha2: number | null;
  sample_entropy: number | null;
  approximate_entropy: number | null;
}

export interface HRFMetrics {
  pip: number | null; // Percentage of Inflection Points
  pip_h: number | null; // Hard inflection
  pip_s: number | null; // Soft inflection
  ials: number | null; // Inverse Average Length of Segments
  pss: number | null; // Percentage of Short Segments
  pas: number | null; // Percentage of Alternating Segments
  quality_ok: boolean;
}

export interface HRVAnalysisResult {
  recording_time: string | null;
  duration_minutes: number | null;
  total_beats: number | null;
  artifact_percentage: number | null;
  time_domain: HRVTimeDomain;
  frequency_domain: HRVFrequencyDomain;
  nonlinear: HRVNonlinear;
  hrf: HRFMetrics;
  quality_score: number | null;
  analysis_method: string;
}

// ---------------------------------------------------------------------------
// Correlation Types
// ---------------------------------------------------------------------------

export type SignificanceLevel =
  | "not_significant"
  | "marginal"
  | "significant"
  | "highly_significant"
  | "very_highly_significant";

export type CorrelationStrength =
  | "negligible"
  | "weak"
  | "moderate"
  | "strong"
  | "very_strong";

export interface CorrelationResult {
  solar_metric: string;
  physio_metric: string;
  lag_hours: number;
  r: number;
  r_squared: number;
  p_value: number;
  n_samples: number;
  significance: SignificanceLevel;
  strength: CorrelationStrength;
  interpretation: string | null;
}

export interface CorrelationAnalysisResult {
  analysis_date: string;
  data_start: string;
  data_end: string;
  n_days: number;
  significant_correlations: CorrelationResult[];
  all_correlations: CorrelationResult[];
  strongest_correlation: CorrelationResult | null;
  optimal_lag_hours: number | null;
  pattern_insights: string[];
  recommendations: string[];
}

// ---------------------------------------------------------------------------
// Garmin Types
// ---------------------------------------------------------------------------

export interface GarminMetrics {
  // SpO2
  spo2_avg: number | null;
  spo2_min: number | null;
  spo2_max: number | null;

  // Respiration
  respiration_awake: number | null;
  respiration_sleep: number | null;

  // VO2max
  vo2max: number | null;
  vo2max_fitness_age: number | null;

  // Sleep
  sleep_duration_hours: number | null;
  sleep_deep_minutes: number | null;
  sleep_rem_minutes: number | null;
  sleep_light_minutes: number | null;
  sleep_awake_minutes: number | null;
  sleep_efficiency: number | null;
  sleep_score: number | null;

  // Body Battery
  body_battery_high: number | null;
  body_battery_low: number | null;
  body_battery_charged: number | null;
  body_battery_drained: number | null;

  // Stress
  stress_avg: number | null;
  stress_max: number | null;
  stress_high_duration_minutes: number | null;

  // Activity
  steps: number | null;
  distance_km: number | null;
  calories_total: number | null;
  active_calories: number | null;

  // HRV from device
  hrv_overnight: number | null;
  resting_hr: number | null;

  date: string | null;
}

// ---------------------------------------------------------------------------
// Scientific Constants
// ---------------------------------------------------------------------------

export const SOLAR_METRIC_INFO: Record<
  string,
  { name: string; unit: string; description: string }
> = {
  kp_index: {
    name: "Kp Index",
    unit: "",
    description: "Planetary geomagnetic activity (0-9 scale)",
  },
  dst_index: {
    name: "Dst Index",
    unit: "nT",
    description: "Disturbance Storm Time - ring current strength",
  },
  f10_7_flux: {
    name: "F10.7 Flux",
    unit: "SFU",
    description: "Solar radio flux at 10.7 cm wavelength",
  },
  solar_wind_speed: {
    name: "Solar Wind Speed",
    unit: "km/s",
    description: "Bulk velocity of solar wind plasma",
  },
  solar_wind_density: {
    name: "Solar Wind Density",
    unit: "p/cm³",
    description: "Proton density in solar wind",
  },
};

export const HRV_METRIC_INFO: Record<
  string,
  { name: string; unit: string; description: string; higherIsBetter: boolean }
> = {
  sdnn: {
    name: "SDNN",
    unit: "ms",
    description: "Standard deviation of NN intervals - overall HRV",
    higherIsBetter: true,
  },
  rmssd: {
    name: "RMSSD",
    unit: "ms",
    description: "Root mean square of successive differences - parasympathetic",
    higherIsBetter: true,
  },
  pnn50: {
    name: "pNN50",
    unit: "%",
    description: "% of intervals differing >50ms - vagal tone",
    higherIsBetter: true,
  },
  lf_hf_ratio: {
    name: "LF/HF Ratio",
    unit: "",
    description: "Sympathovagal balance indicator",
    higherIsBetter: false,
  },
  hf_power: {
    name: "HF Power",
    unit: "ms²",
    description: "High frequency power - respiratory sinus arrhythmia",
    higherIsBetter: true,
  },
  dfa_alpha1: {
    name: "DFA α1",
    unit: "",
    description: "Short-term fractal scaling exponent",
    higherIsBetter: false, // ~1.0 is healthy
  },
  pip: {
    name: "PIP",
    unit: "%",
    description: "Percentage of Inflection Points - fragmentation",
    higherIsBetter: false,
  },
};

export const SEVERITY_COLORS: Record<ImpactSeverity, string> = {
  quiet: "#27ae60",
  minor: "#3498db",
  moderate: "#f39c12",
  strong: "#e67e22",
  severe: "#e74c3c",
  extreme: "#8e44ad",
};

export const CATEGORY_ICONS: Record<EnergyCategory, string> = {
  photon: "☀️",
  sep: "⚡",
  plasma_l1: "🌊",
  cme_shock: "💥",
  hss: "🌬️",
  geomagnetic: "🧭",
};
