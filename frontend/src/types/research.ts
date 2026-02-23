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

export type ConfidenceLevel = "good" | "moderate" | "poor";

export interface StationarityAssessment {
  passed: boolean;
  reason: string;
}

export interface FrequencyValidityAssessment {
  method: string;
  valid: boolean;
  score: number; // 0-1
  min_duration_met: boolean;
  note: string;
}

export interface AnalysisContext {
  device_type: "ecg" | "ppg" | "unknown";
  posture: "supine" | "seated" | "standing" | "unknown";
  respiration_available: boolean;
  recording_window_sec: number | null;
  preprocessing: {
    artifact_filter_level: string;
    pct_flagged: number;
    pct_interpolated: number;
    pct_excluded: number;
  };
  stationarity: StationarityAssessment;
  frequency_validity: FrequencyValidityAssessment[];
  confidence: ConfidenceLevel;
  confidence_reasons: string[];
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
  context?: AnalysisContext;
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

// ---------------------------------------------------------------------------
// Time Series Types (Phase 1)
// ---------------------------------------------------------------------------

export interface DeviationZone {
  start_idx: number;
  end_idx: number;
  start_time: string | null;
  end_time: string | null;
  severity: "normal" | "mild" | "moderate" | "severe";
  direction: "high" | "low";
  mean_deviation_pct: number;
}

export interface RRTimeSeriesResponse {
  timestamps: string[];
  rr_ms: number[];
  hr_bpm: number[];
  deviation_zones: DeviationZone[];
  mean_rr: number | null;
  std_rr: number | null;
  min_rr: number | null;
  max_rr: number | null;
  total_beats: number;
  duration_seconds: number | null;
  percentiles: Record<string, number>;
  age_norm_mean: number | null;
  age_norm_low: number | null;
  age_norm_high: number | null;
}

// ---------------------------------------------------------------------------
// Frequency Domain Types (Phase 1)
// ---------------------------------------------------------------------------

export interface BandPower {
  power_ms2: number;
  power_pct: number;
  peak_hz: number | null;
  normalized_units: number | null;
}

export interface FrequencyDomainResponse {
  frequencies: number[];
  psd: number[];
  vlf: BandPower | null;
  lf: BandPower | null;
  hf: BandPower | null;
  total_power: number | null;
  lf_hf_ratio: number | null;
  lf_nu: number | null;
  hf_nu: number | null;
  method: string;
  window_length: number | null;
  autonomic_balance: "parasympathetic" | "balanced" | "sympathetic";
  clinical_notes: string[];
  frequency_validity_score?: number;
  method_validity_note?: string;
  context?: AnalysisContext;
}

// ---------------------------------------------------------------------------
// Nonlinear Analysis Types (Phase 1)
// ---------------------------------------------------------------------------

export interface EllipseParams {
  center_x: number;
  center_y: number;
  width: number;
  height: number;
  angle: number;
}

export interface NonlinearResponse {
  rr_n: number[];
  rr_n1: number[];
  sd1: number | null;
  sd2: number | null;
  sd1_sd2_ratio: number | null;
  ellipse: EllipseParams | null;
  dfa_alpha1: number | null;
  dfa_alpha2: number | null;
  dfa_alpha1_interpretation: string | null;
  sample_entropy: number | null;
  approximate_entropy: number | null;
  complexity_state: "reduced" | "normal" | "elevated";
  interpretation: string[];
  // Advanced cognitive discriminators (Phase 6)
  rcmse_tau?: number[];
  rcmse_curve?: number[];
  rcmse_ei?: number | null;
  mmdfa_scales?: number[];
  mmdfa_curve?: number[];
  mfi?: number | null;
  min_samples_required?: number;
  advanced_metrics_enabled?: boolean;
  context?: AnalysisContext;
}

// ---------------------------------------------------------------------------
// Windowed Analysis Types (Phase 1)
// ---------------------------------------------------------------------------

export interface TrendStatistic {
  metric: string;
  n_samples: number;
  slope_per_day?: number | null;
  robust_slope_per_day?: number | null;
  slope_ci_low?: number | null;
  slope_ci_high?: number | null;
  trend_method?: string;
  kendall_tau?: number | null;
  p_value?: number | null;
  q_value?: number | null;
  significance?: string;
  fdr_significance?: string;
  r_squared?: number | null;
  direction: "increasing" | "decreasing" | "stable" | "insufficient" | string;
  baseline_value?: number | null;
  latest_value?: number | null;
  delta_pct?: number | null;
  mean_value?: number | null;
  std_value?: number | null;
  cv_pct?: number | null;
}

export interface PhysiologicalCorrelation {
  anchor_metric: string;
  other_metric: string;
  method: string;
  r?: number | null;
  p_value?: number | null;
  q_value?: number | null;
  effect_size?: string;
  direction?: "positive" | "negative" | string;
  significance?: string;
  is_significant?: boolean;
  n_samples: number;
  interpretation?: string;
}

export interface LongTermTrendStatistic {
  metric_key: string;
  metric: string;
  n_samples: number;
  slope_per_day?: number | null;
  robust_slope_per_day?: number | null;
  slope_ci_low?: number | null;
  slope_ci_high?: number | null;
  trend_method?: string;
  kendall_tau?: number | null;
  p_value?: number | null;
  q_value?: number | null;
  significance?: string;
  fdr_significance?: string;
  r_squared?: number | null;
  direction: "increasing" | "decreasing" | "stable" | "insufficient" | string;
  baseline_value?: number | null;
  latest_value?: number | null;
  delta_pct?: number | null;
  mean_value?: number | null;
  std_value?: number | null;
  cv_pct?: number | null;
  horizon_days?: number;
}

export interface WindowedMetricsResponse {
  timestamps: string[];
  rmssd: (number | null)[];
  sdnn: (number | null)[];
  pnn50: (number | null)[];
  mean_hr: (number | null)[];
  lf_power: (number | null)[];
  hf_power: (number | null)[];
  lf_hf_ratio: (number | null)[];
  rmssd_ewma: (number | null)[];
  sdnn_ewma: (number | null)[];
  anomaly_indices: number[];
  cluster_labels: number[];
  window_size_seconds: number;
  step_size_seconds: number;
  n_windows: number;
  source_scope?: "all" | "selected" | string;
  n_sessions?: number;
  session_sources?: string[];
  trend_break_indices?: number[];
  trend_statistics?: TrendStatistic[];
  correlation_metric_labels?: string[];
  correlation_matrix?: (number | null)[][];
  correlation_p_values?: (number | null)[][];
  correlation_q_values?: (number | null)[][];
  physiological_timestamps?: string[];
  physiological_series?: Record<string, (number | null)[]>;
  physiological_correlations?: PhysiologicalCorrelation[];
  long_term_window_days?: number;
  long_term_timestamps?: string[];
  long_term_series?: Record<string, (number | null)[]>;
  long_term_trend_series?: Record<string, (number | null)[]>;
  long_term_metric_groups?: Record<string, string[]>;
  long_term_statistics?: LongTermTrendStatistic[];
  future_ml_insights?: string[];
  statistical_notes?: string[];
  context?: AnalysisContext;
}

// ---------------------------------------------------------------------------
// HRF Analysis Types (Phase 1)
// ---------------------------------------------------------------------------

export interface HRFResponse {
  pip: number | null;
  pip_hard: number | null;
  pip_soft: number | null;
  ials: number | null;
  pss: number | null;
  pas: number | null;
  pip_trend: number[];
  timestamps: string[];
  pip_rmssd_correlation: number | null;
  fragmentation_level: "low" | "normal" | "elevated" | "high";
  af_risk_indicator: string | null;
  clinical_notes: string[];
  quality_ok: boolean;
}

// ---------------------------------------------------------------------------
// Readiness Types (Phase 1)
// ---------------------------------------------------------------------------

export interface ReadinessComponent {
  name: string;
  value: number;
  weight: number;
  contribution: number;
  status: "good" | "warning" | "poor";
}

export interface ReadinessResponse {
  score: number | null;
  baseline: number | null;
  deviation_from_baseline: number | null;
  trend_direction: "improving" | "stable" | "declining";
  trend_7day: number[];
  trend_dates: string[];
  components: ReadinessComponent[];
  readiness_status: "ready" | "moderate" | "rest_recommended";
  recommendations: string[];
}

// ---------------------------------------------------------------------------
// Fatigue Types (Phase 1)
// ---------------------------------------------------------------------------

export interface FatigueResponse {
  effectiveness_pct: number | null;
  fatigue_level: "well_rested" | "normal" | "fatigued" | "severely_fatigued";
  forecast_hours: number[];
  forecast_effectiveness: number[];
  sleep_debt_hours: number | null;
  optimal_sleep_hours: number;
  risk_level: "low" | "moderate" | "high" | "critical";
  risk_color: "green" | "yellow" | "red";
  recommendations: string[];
  next_optimal_sleep: string | null;
  // Garmin-derived sleep schedule for SAFTE model input
  avg_sleep_duration_h: number | null;
  typical_bedtime_h: number | null;
  avg_sleep_efficiency: number | null;
  context?: AnalysisContext;
}

export interface WorkloadSegment {
  start_idx: number;
  end_idx: number;
  label: "baseline" | "task" | "recovery";
  task_name?: string;
  notes?: string;
}

export interface WorkloadResponse {
  delta_lnrmssd: number | null;
  delta_hf: number | null;
  delta_lf_hf: number | null;
  recovery_slope: number | null;
  threshold_flags: string[];
  high_workload_probability: number;
  confidence: ConfidenceLevel;
  context?: AnalysisContext;
}

export interface VigilanceWindowPrediction {
  start_seconds: number;
  end_seconds: number;
  state: "high" | "medium" | "low";
  confidence: number;
  rmssd: number | null;
  mean_hr: number | null;
  safte_effectiveness: number | null;
}

export interface VigilanceResponse {
  window_size_seconds: number;
  step_size_seconds: number;
  model_version: string;
  low_vigilance_windows: number;
  total_windows: number;
  predictions: VigilanceWindowPrediction[];
  context?: AnalysisContext;
}

export interface FlightFatigueResponse {
  risk_band: "low" | "moderate" | "high";
  model_version: string;
  probabilities: Record<"low" | "moderate" | "high", number>;
  rationale: string[];
  required_features: string[];
  missing_features: string[];
  context?: AnalysisContext;
}

export interface FusionFactor {
  value: number;
  confidence: ConfidenceLevel;
  note: string;
}

export interface FusionResponse {
  schedule_factor: FusionFactor;
  autonomic_factor: FusionFactor;
  workload_factor: FusionFactor;
  environment_factor: FusionFactor;
  performance_probability: number; // 0-1
  uncertainty_interval: [number, number];
  confidence: ConfidenceLevel;
  rationale: string[];
}

export interface CalibrationModelReport {
  key: string;
  model_id: string;
  model_version: string;
  trained_at_utc: string;
  source: string;
  feature_order: string[];
  class_labels?: string[];
  metrics: Record<string, number>;
  references: string[];
  notes: string;
  artifact_path: string;
  fallback_used: boolean;
  load_error?: string | null;
}

export interface CalibrationReportResponse {
  generated_at_utc: string;
  models: CalibrationModelReport[];
}

// ---------------------------------------------------------------------------
// Circadian Types (Phase 1)
// ---------------------------------------------------------------------------

export interface CircadianResponse {
  current_phase: "day" | "evening" | "night" | "morning";
  phase_angle_hours: number | null;
  optimal_performance_start: string | null;
  optimal_performance_end: string | null;
  optimal_sleep_start: string | null;
  hours: number[];
  alertness_level: number[];
  light_exposure_lux: number | null;
  light_recommendation: string | null;
  chronotype: "early" | "intermediate" | "late";
  notes: string[];
}

// ---------------------------------------------------------------------------
// Population Norms Types (Phase 1)
// ---------------------------------------------------------------------------

export interface AgeNorm {
  age_range: string;
  metric: string;
  mean: number;
  std: number;
  p5: number;
  p25: number;
  p50: number;
  p75: number;
  p95: number;
  source: string;
}

export interface PopulationNormsResponse {
  norms: AgeNorm[];
  user_age_group: string | null;
  user_percentiles: Record<string, number>;
  primary_source: string;
  additional_sources: string[];
}

// ---------------------------------------------------------------------------
// Export Types (Phase 1)
// ---------------------------------------------------------------------------

export interface ExportRequest {
  format: "csv" | "json" | "markdown" | "pdf";
  include_timeseries: boolean;
  include_frequency: boolean;
  include_nonlinear: boolean;
  include_hrf: boolean;
  date_range_days: number;
}

export interface ExportResponse {
  format: string;
  filename: string;
  content_type: string;
  data: string;
  records_exported: number;
  date_range: string;
}

// ---------------------------------------------------------------------------
// Comprehensive Metrics Types (Phase 3)
// ---------------------------------------------------------------------------

export interface ComprehensiveHRVMetrics {
  // Time domain
  mean_rr: number | null;
  sdnn: number | null;
  sdsd: number | null;
  rmssd: number | null;
  nn50: number | null;
  pnn50: number | null;
  nn20: number | null;
  pnn20: number | null;
  cvnn: number | null;
  cvsd: number | null;
  mean_hr: number | null;
  sd_hr: number | null;
  min_hr: number | null;
  max_hr: number | null;
  
  // Frequency domain
  vlf_power: number | null;
  lf_power: number | null;
  hf_power: number | null;
  total_power: number | null;
  lf_nu: number | null;
  hf_nu: number | null;
  lf_hf_ratio: number | null;
  
  // Nonlinear
  sd1: number | null;
  sd2: number | null;
  sd1_sd2_ratio: number | null;
  csi: number | null;  // Cardiac Sympathetic Index
  cvi: number | null;  // Cardiac Vagal Index
  dfa_alpha1: number | null;
  dfa_alpha2: number | null;
  sample_entropy: number | null;
  approximate_entropy: number | null;
  
  // HRF
  pip: number | null;
  ials: number | null;
  pss: number | null;
  pas: number | null;
  
  // Geometric
  hrv_triangular_index: number | null;
  tinn: number | null;
  
  // Advanced
  baevsky_stress_index: number | null;
  prsa_ac: number | null;  // Phase-Rectified Signal Averaging - Acceleration
  prsa_dc: number | null;  // Phase-Rectified Signal Averaging - Deceleration
}

// ---------------------------------------------------------------------------
// ANS Function Test Types (Phase 4)
// ---------------------------------------------------------------------------

export interface ANSTestResult {
  test_name: string;
  value: number | null;
  normal_range: [number, number];
  unit: string;
  status: "normal" | "borderline" | "abnormal";
  interpretation: string;
}

export interface ANSFunctionResponse {
  ratio_30_15: ANSTestResult | null;
  valsalva_ratio: ANSTestResult | null;
  deep_breathing_ei: ANSTestResult | null;
  overall_autonomic_function: "normal" | "borderline" | "abnormal";
  summary: string[];
  recommendations: string[];
}

// ---------------------------------------------------------------------------
// Scientific References Types (Phase 5)
// ---------------------------------------------------------------------------

export interface ScientificReference {
  id: string;
  authors: string;
  year: number;
  title: string;
  journal: string;
  volume: string | null;
  pages: string | null;
  doi: string | null;
  pmid: string | null;
  category: string;
  summary: string;
}

export interface MethodologySection {
  id: string;
  title: string;
  content: string;
  references: string[];
  subsections: MethodologySection[];
}

// ---------------------------------------------------------------------------
// Color and Styling Constants
// ---------------------------------------------------------------------------

export const DEVIATION_COLORS: Record<DeviationZone["severity"], string> = {
  normal: "#27ae60",
  mild: "#f1c40f",
  moderate: "#e67e22",
  severe: "#e74c3c",
};

export const READINESS_COLORS: Record<ReadinessResponse["readiness_status"], string> = {
  ready: "#27ae60",
  moderate: "#f39c12",
  rest_recommended: "#e74c3c",
};

export const FATIGUE_COLORS: Record<FatigueResponse["fatigue_level"], string> = {
  well_rested: "#27ae60",
  normal: "#3498db",
  fatigued: "#f39c12",
  severely_fatigued: "#e74c3c",
};

export const COMPLEXITY_COLORS: Record<NonlinearResponse["complexity_state"], string> = {
  reduced: "#e74c3c",
  normal: "#27ae60",
  elevated: "#f39c12",
};

export const FRAGMENTATION_COLORS: Record<HRFResponse["fragmentation_level"], string> = {
  low: "#27ae60",
  normal: "#3498db",
  elevated: "#f39c12",
  high: "#e74c3c",
};

// ---------------------------------------------------------------------------
// Enhanced NOAA Data Types (Phase 6 - Correlations)
// ---------------------------------------------------------------------------

export interface NOAADatasetInfo {
  key: string;
  title: string;
  description: string;
  value_columns: string[];
  units: Record<string, string>;
  cadence_minutes: number | null;
  rows_available: number;
  latest_value: Record<string, unknown> | null;
  time_range: string | null;
}

export interface NOAADataResponse {
  fetched_at: string;
  sources: string[];
  datasets: Record<string, NOAADatasetInfo>;
  kp_data: Array<{ timestamp: string; kp: number | null }>;
  dst_data: Array<{ timestamp: string; dst: number | null }>;
  solar_wind_data: Array<{
    timestamp: string;
    speed?: number | null;
    density?: number | null;
    bz?: number | null;
    bt?: number | null;
    temperature?: number | null;
  }>;
  f107_data?: Array<{ timestamp: string; f107: number | null }>;
  xray_data?: Array<{ timestamp: string; flux: number | null; class: string | null }>;
  proton_data?: Array<{ timestamp: string; flux_10mev: number | null; flux_100mev: number | null }>;
  errors: Record<string, string>;
}

// ---------------------------------------------------------------------------
// RR Upload Types (Phase 6 - Correlations)
// ---------------------------------------------------------------------------

export interface RRUploadRequest {
  rr_intervals_ms: number[];
  recording_timestamp?: string;
  source?: string;
  user_id?: string;
  measurement_id?: string;
  file_hash?: string;
}

export interface RRUploadResponse {
  success: boolean;
  n_intervals: number;
  duration_minutes: number;
  mean_rr_ms: number;
  mean_hr_bpm: number;
  sdnn: number | null;
  rmssd: number | null;
  pnn50: number | null;
  artifact_percentage: number;
  quality_status: "good" | "moderate" | "poor";
  session_id: string;
  measurement_id?: string | null;
  file_hash?: string | null;
  cached?: boolean;
  message: string;
}

export interface StoredRRTracing {
  measurement_id: string;
  user_id: string;
  source_file?: string | null;
  file_hash?: string | null;
  measurement_date: string;
  recording_start_utc?: string | null;
  recording_duration_min?: number | null;
  n_intervals: number;
  artifact_percentage?: number | null;
  quality_status: "good" | "moderate" | "poor" | "unknown";
  created_at?: string | null;
  has_cached_analysis: boolean;
}

export interface RRTracingCatalogResponse {
  user_id: string;
  tracings: StoredRRTracing[];
}

export interface RRTracingDetailResponse {
  tracing: StoredRRTracing | null;
  rr_intervals_ms: number[];
  cached_analysis: HRVAnalysisResult | null;
}

// ---------------------------------------------------------------------------
// Enhanced Correlation Analysis Types (Phase 6)
// ---------------------------------------------------------------------------

export interface DetailedCorrelation {
  solar_metric: string;
  solar_metric_name: string;
  physio_metric: string;
  physio_metric_name: string;
  lag_hours: number;
  r: number;
  r_squared: number;
  p_value: number;
  n_samples: number;
  significance: SignificanceLevel;
  strength: CorrelationStrength;
  direction: "positive" | "negative";
  solar_values: number[];
  hrv_values: number[];
  ci_lower: number;
  ci_upper: number;
  interpretation: string;
}

export interface LagAnalysis {
  solar_metric: string;
  hrv_metric: string;
  lags: number[];
  correlations: number[];
  p_values: number[];
  optimal_lag: number;
  optimal_r: number;
  optimal_p: number;
}

export interface TimelineDataPoint {
  date: string;
  kp?: number;
  rmssd?: number;
  dst?: number;
  [key: string]: string | number | undefined;
}

export interface ComprehensiveCorrelationResponse {
  analysis_date: string;
  data_start: string;
  data_end: string;
  n_days: number;
  n_hrv_samples: number;
  n_solar_samples: number;
  
  // Matrix data for heatmap
  correlation_matrix: number[][];
  p_value_matrix: number[][];
  solar_labels: string[];
  hrv_labels: string[];
  
  // Detailed results
  significant_correlations: DetailedCorrelation[];
  all_correlations: DetailedCorrelation[];
  
  // Lag analysis
  lag_analyses: LagAnalysis[];
  optimal_lag_hours: number | null;
  
  // Timeline for overlay plot
  timeline_data: TimelineDataPoint[];
  
  // Insights
  pattern_insights: string[];
  recommendations: string[];
  methodology_notes: string[];
}

export interface CorrelationRequest {
  session_id?: string;
  user_id?: string;
  start_date?: string;
  end_date?: string;
  max_lag_hours?: number;
  solar_metrics?: string[];
  hrv_metrics?: string[];
}

// ---------------------------------------------------------------------------
// Significance Color Map
// ---------------------------------------------------------------------------

export const SIGNIFICANCE_COLORS: Record<SignificanceLevel, string> = {
  not_significant: "#64748b",
  marginal: "#f59e0b",
  significant: "#22c55e",
  highly_significant: "#3b82f6",
  very_highly_significant: "#8b5cf6",
};

export const STRENGTH_COLORS: Record<CorrelationStrength, string> = {
  negligible: "#94a3b8",
  weak: "#60a5fa",
  moderate: "#fbbf24",
  strong: "#22c55e",
  very_strong: "#ef4444",
};

// ---------------------------------------------------------------------------
// Ventilatory Threshold Types (Experimental)
// ---------------------------------------------------------------------------

export interface VTThresholdData {
  time_seconds: number;
  heart_rate_bpm: number;
  dfa_alpha1: number;
  hr_relative: number;
  confidence: number;
  index: number;
}

export interface VTIntensityZone {
  zone: string;
  zone_label: string;
  zone_description: string;
  hr_min: number;
  hr_max: number;
  dfa_range: string;
  training_guidance: string;
}

export interface VTQualityData {
  artifact_percentage: number;
  total_beats: number;
  clean_beats: number;
  n_windows: number;
  min_dfa: number;
  max_dfa: number;
  dfa_range: number;
  monotonic_decrease: boolean;
}

export interface VTAnalysisResponse {
  vt1: VTThresholdData | null;
  vt2: VTThresholdData | null;
  timeseries_time: number[];
  timeseries_dfa: number[];
  timeseries_hr: number[];
  timeseries_hr_mean: number[];
  timeseries_integrated_score: number[];
  respiratory_frequency_hz: number | null;
  quality: VTQualityData | null;
  method: string;
  intensity_zones: VTIntensityZone[];
  interpretation: string[];
  warnings: string[];
}

export const VT_ZONE_COLORS: Record<string, string> = {
  zone_1: "#27ae60",  // Green - aerobic
  zone_2: "#f39c12",  // Orange - threshold
  zone_3: "#e74c3c",  // Red - high intensity
};

export const DFA_ZONE_COLORS = {
  belowVT1: "rgba(39, 174, 96, 0.12)",   // Green zone
  vt1ToVT2: "rgba(243, 156, 18, 0.12)",  // Orange zone
  aboveVT2: "rgba(231, 76, 60, 0.12)",   // Red zone
};

// ---------------------------------------------------------------------------
// Physiological SMS Risk Assessment Types
// ---------------------------------------------------------------------------

export interface VitalsInput {
  sbp_mmhg: number | null;
  dbp_mmhg: number | null;
  temperature_c: number | null;
}

export interface SMSClassificationResponse {
  severity: string;
  likelihood: string;
  risk_level: string;
  rationale: string;
  disqualifiers: string[];
  activity_type: string;
}

export interface ModifierDetail {
  name: string;
  value: number;
  category: string;
  rationale: string;
}

export interface SMSMatrixData {
  severity_labels: string[];
  likelihood_labels: string[];
  data: number[][];
  risk_levels: string[];
  risk_colors: string[];
}

export interface EnhancedReadinessResponse {
  readiness_score: number;
  readiness_label: string;
  bp_classification: string | null;
  bp_modifier: number | null;
  bp_rationale: string | null;
  temp_classification: string | null;
  temp_modifier: number | null;
  temp_rationale: string | null;
  modifiers: ModifierDetail[];
  triggers: string[];
  eva_sms: SMSClassificationResponse | null;
  flight_sms: SMSClassificationResponse | null;
  eva_matrix: SMSMatrixData | null;
  flight_matrix: SMSMatrixData | null;
  nasa_hrp_matrix: SMSMatrixData | null;
}

export interface SMSMatrixEndpointResponse {
  classification: {
    severity: string;
    likelihood: string;
    risk_level: string;
    rationale: string;
    disqualifiers: string[];
  };
  matrix: SMSMatrixData;
  position: {
    severity_index: number;
    likelihood_index: number;
  };
}

export const SMS_RISK_COLORS: Record<string, string> = {
  // EVA (ICAO Doc 9859)
  Acceptable: "#27ae60",
  Tolerable: "#f39c12",
  Undesirable: "#e67e22",
  Intolerable: "#e74c3c",
  // Flight (MIL-STD-882E)
  Low: "#27ae60",
  Medium: "#f39c12",
  Serious: "#e67e22",
  High: "#e74c3c",
  // NASA HRP (LxC)
  Accepted: "#27ae60",
  Controlled: "#3498db",
  Watched: "#f39c12",
  Uncontrolled: "#e74c3c",
};

export const READINESS_LABEL_COLORS: Record<string, string> = {
  GO: "#27ae60",
  CAUTION: "#f39c12",
  MARGINAL: "#e67e22",
  "NO-GO": "#e74c3c",
};

// ---------------------------------------------------------------------------
// METAR / Weather / Environment Types
// ---------------------------------------------------------------------------

export interface METARResponse {
  icao: string;
  metar: Record<string, unknown> | null;
  error: string | null;
}

export interface WeatherIndices {
  wind_chill_c: number;
  frostbite_minutes: number | null;
  cold_risk: string;
  cold_description: string;
  wbgt_c: number;
  heat_index_c: number;
  heat_risk: string;
  heat_description: string;
  work_rest_guidance: string;
}

export interface WeatherResponse {
  city: string;
  weather: Record<string, unknown> | null;
  indices: WeatherIndices | null;
  error: string | null;
}

export interface ICEStationReadings {
  temperature_c: number;
  humidity_pct: number;
  co2_ppm: number;
  pressure_hpa: number;
  pm25_ugm3: number;
  noise_db: number;
  light_lux: number;
  o2_pct: number;
}

export interface ICEStationResponse {
  station: string;
  timestamp: string;
  readings: ICEStationReadings;
  thresholds: Record<string, Record<string, number | string>>;
}

export interface JetLagResponse {
  time_zones: number;
  direction: string;
  days_since: number;
  resync_rate: number;
  days_to_resync: number;
  performance_pct: number;
  readiness_modifier: number;
  phase: string;
  description: string;
  recovery_curve: Array<{ day: number; performance: number }>;
}

export const RISK_LEVEL_COLORS: Record<string, string> = {
  Low: "#27ae60",
  Moderate: "#f39c12",
  High: "#e67e22",
  "Very High": "#e74c3c",
  Extreme: "#8e44ad",
};
