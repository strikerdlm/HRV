// Author: Dr Diego Malpica MD
/**
 * API functions for Research features
 * - Space Weather data retrieval
 * - HRV Analysis (time, frequency, nonlinear, windowed, HRF)
 * - HRV-Space Weather correlations
 * - Readiness, Fatigue, Circadian
 * - Population Norms
 * - Export
 */

import type {
  SpaceWeatherSnapshot,
  SpaceWeatherData,
  ImpactPrediction,
  CorrelationAnalysisResult,
  RRTimeSeriesResponse,
  FrequencyDomainResponse,
  NonlinearResponse,
  WindowedMetricsResponse,
  HRFResponse,
  ReadinessResponse,
  FatigueResponse,
  CircadianResponse,
  PopulationNormsResponse,
  ExportRequest,
  ExportResponse,
  HRVAnalysisResult,
  GarminMetrics,
  AnalysisContext,
  WorkloadResponse,
  WorkloadSegment,
  VigilanceResponse,
  FlightFatigueResponse,
  FusionResponse,
  CalibrationReportResponse,
} from "@/types/research";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8180";

function buildFallbackContext(): AnalysisContext {
  return {
    device_type: "unknown",
    posture: "unknown",
    respiration_available: false,
    recording_window_sec: null,
    preprocessing: {
      artifact_filter_level: "unknown",
      pct_flagged: 0,
      pct_interpolated: 0,
      pct_excluded: 0,
    },
    stationarity: { passed: false, reason: "No valid recording loaded" },
    frequency_validity: [],
    confidence: "poor",
    confidence_reasons: ["Data unavailable"],
  };
}

/**
 * Get current space weather data and impact predictions
 */
export async function getCurrentSpaceWeather(): Promise<SpaceWeatherSnapshot> {
  try {
    const response = await fetch(`${API_BASE}/api/research/space-weather/current`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    return result;
  } catch (error) {
    console.error("Error fetching space weather:", error);
    
    // Return empty snapshot on error
    return {
      data: {
        kp_index: null,
        kp_status: null,
        dst_index: null,
        f10_7_flux: null,
        f10_7_status: null,
        solar_wind_speed: null,
        solar_wind_density: null,
        solar_wind_bz: null,
        xray_flux: null,
        xray_class: null,
        proton_flux_10mev: null,
        proton_flux_100mev: null,
        sep_event_active: false,
        geomagnetic_status: null,
        radiation_status: null,
        fetched_at: null,
      },
      predictions: [],
      next_impact: null,
      most_severe: null,
      errors: {
        fetch: error instanceof Error ? error.message : "Unknown error",
      },
    };
  }
}

/**
 * Get HRV-Space Weather correlations for a user
 */
export async function getHRVSpaceWeatherCorrelations(
  userId: string,
  params?: {
    startDate?: string;
    endDate?: string;
    minCorrelation?: number;
  }
): Promise<CorrelationAnalysisResult> {
  try {
    const queryParams = new URLSearchParams();
    if (params?.startDate) queryParams.set("start_date", params.startDate);
    if (params?.endDate) queryParams.set("end_date", params.endDate);
    if (params?.minCorrelation !== undefined) {
      queryParams.set("min_correlation", params.minCorrelation.toString());
    }

    const url = `${API_BASE}/api/research/correlations/${userId}${
      queryParams.toString() ? `?${queryParams.toString()}` : ""
    }`;

    const response = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    return result;
  } catch (error) {
    console.error("Error fetching correlations:", error);
    
    // Return empty result on error
    const now = new Date().toISOString();
    return {
      analysis_date: now,
      data_start: now,
      data_end: now,
      n_days: 0,
      significant_correlations: [],
      all_correlations: [],
      strongest_correlation: null,
      optimal_lag_hours: null,
      pattern_insights: [],
      recommendations: [
        "Error fetching correlation data. Please ensure you have HRV recordings and try again.",
      ],
    };
  }
}

/**
 * Compute fresh correlations for a user (may take time)
 */
export async function computeHRVSpaceWeatherCorrelations(
  userId: string,
  params?: {
    startDate?: string;
    endDate?: string;
    lagRange?: [number, number];
    minSamples?: number;
  }
): Promise<CorrelationAnalysisResult> {
  try {
    const response = await fetch(
      `${API_BASE}/api/research/correlations/${userId}/compute`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params || {}),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    return result;
  } catch (error) {
    console.error("Error computing correlations:", error);
    throw error;
  }
}

/**
 * Get historical space weather data for time range
 */
export async function getSpaceWeatherHistory(params: {
  startDate: string;
  endDate: string;
}): Promise<SpaceWeatherData[]> {
  try {
    const queryParams = new URLSearchParams({
      start_date: params.startDate,
      end_date: params.endDate,
    });

    const response = await fetch(
      `${API_BASE}/api/space-weather/history?${queryParams.toString()}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    return result;
  } catch (error) {
    console.error("Error fetching space weather history:", error);
    return [];
  }
}

/**
 * Force refresh space weather data from NOAA/NASA sources
 */
export async function refreshSpaceWeather(
  force: boolean = true
): Promise<SpaceWeatherSnapshot> {
  try {
    const response = await fetch(`${API_BASE}/api/research/space-weather/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    return result;
  } catch (error) {
    console.error("Error refreshing space weather:", error);

    // Return empty snapshot on error
    return {
      data: {
        kp_index: null,
        kp_status: null,
        dst_index: null,
        f10_7_flux: null,
        f10_7_status: null,
        solar_wind_speed: null,
        solar_wind_density: null,
        solar_wind_bz: null,
        xray_flux: null,
        xray_class: null,
        proton_flux_10mev: null,
        proton_flux_100mev: null,
        sep_event_active: false,
        geomagnetic_status: null,
        radiation_status: null,
        fetched_at: null,
      },
      predictions: [],
      next_impact: null,
      most_severe: null,
      errors: {
        refresh: error instanceof Error ? error.message : "Unknown error",
      },
    };
  }
}

/**
 * Sync Garmin Connect data for a user
 */
export async function syncGarminData(
  userId: string,
  days: number = 14
): Promise<{ success: boolean; records_synced: number; message: string; date_range?: string }> {
  try {
    const response = await fetch(`${API_BASE}/api/research/garmin/sync/${userId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ days }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      );
    }

    const result = await response.json();
    return result;
  } catch (error) {
    console.error("Error syncing Garmin data:", error);
    throw error;
  }
}

// ---------------------------------------------------------------------------
// HRV Time Series API
// ---------------------------------------------------------------------------

/**
 * Get RR interval time series with deviation zones
 */
export async function getHRVTimeSeries(
  userId: string,
  limit: number = 1000
): Promise<RRTimeSeriesResponse> {
  try {
    const response = await fetch(
      `${API_BASE}/api/research/hrv/timeseries/${userId}?limit=${limit}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching HRV time series:", error);
    return {
      timestamps: [],
      rr_ms: [],
      hr_bpm: [],
      deviation_zones: [],
      mean_rr: null,
      std_rr: null,
      min_rr: null,
      max_rr: null,
      total_beats: 0,
      duration_seconds: null,
      percentiles: {},
      age_norm_mean: null,
      age_norm_low: null,
      age_norm_high: null,
    };
  }
}

// ---------------------------------------------------------------------------
// Frequency Domain API
// ---------------------------------------------------------------------------

/**
 * Get frequency domain HRV analysis with PSD
 */
export async function getHRVFrequency(
  userId: string,
  method: "welch" | "periodogram" | "ar" | "lomb" = "welch"
): Promise<FrequencyDomainResponse> {
  try {
    const response = await fetch(
      `${API_BASE}/api/research/hrv/frequency/${userId}?method=${method}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching frequency domain:", error);
    return {
      frequencies: [],
      psd: [],
      vlf: null,
      lf: null,
      hf: null,
      total_power: null,
      lf_hf_ratio: null,
      lf_nu: null,
      hf_nu: null,
      method: "welch",
      window_length: null,
      autonomic_balance: "balanced",
      clinical_notes: ["Error fetching frequency domain data"],
      frequency_validity_score: 0,
      method_validity_note: "Frequency-domain unavailable",
      context: buildFallbackContext(),
    };
  }
}

// ---------------------------------------------------------------------------
// Nonlinear Analysis API
// ---------------------------------------------------------------------------

/**
 * Get nonlinear HRV analysis (Poincare, DFA, Entropy)
 */
export async function getHRVNonlinear(userId: string): Promise<NonlinearResponse> {
  try {
    const response = await fetch(
      `${API_BASE}/api/research/hrv/nonlinear/${userId}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching nonlinear metrics:", error);
    return {
      rr_n: [],
      rr_n1: [],
      sd1: null,
      sd2: null,
      sd1_sd2_ratio: null,
      ellipse: null,
      dfa_alpha1: null,
      dfa_alpha2: null,
      dfa_alpha1_interpretation: null,
      sample_entropy: null,
      approximate_entropy: null,
      complexity_state: "normal",
      interpretation: ["Error fetching nonlinear data"],
      rcmse_tau: [],
      rcmse_curve: [],
      rcmse_ei: null,
      mmdfa_scales: [],
      mmdfa_curve: [],
      mfi: null,
      min_samples_required: 400,
      advanced_metrics_enabled: false,
      context: buildFallbackContext(),
    };
  }
}

// ---------------------------------------------------------------------------
// Windowed Analysis API
// ---------------------------------------------------------------------------

/**
 * Get windowed HRV analysis over time
 */
export async function getHRVWindowed(
  userId: string,
  windowSize: number = 300,
  stepSize: number = 60
): Promise<WindowedMetricsResponse> {
  try {
    const response = await fetch(
      `${API_BASE}/api/research/hrv/windowed/${userId}?window_size=${windowSize}&step_size=${stepSize}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching windowed HRV:", error);
    return {
      timestamps: [],
      rmssd: [],
      sdnn: [],
      pnn50: [],
      mean_hr: [],
      lf_power: [],
      hf_power: [],
      lf_hf_ratio: [],
      rmssd_ewma: [],
      sdnn_ewma: [],
      anomaly_indices: [],
      cluster_labels: [],
      window_size_seconds: windowSize,
      step_size_seconds: stepSize,
      n_windows: 0,
      context: buildFallbackContext(),
    };
  }
}

// ---------------------------------------------------------------------------
// HRF Analysis API
// ---------------------------------------------------------------------------

/**
 * Get Heart Rate Fragmentation analysis
 */
export async function getHRVHRF(userId: string): Promise<HRFResponse> {
  try {
    const response = await fetch(
      `${API_BASE}/api/research/hrv/hrf/${userId}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching HRF:", error);
    return {
      pip: null,
      pip_hard: null,
      pip_soft: null,
      ials: null,
      pss: null,
      pas: null,
      pip_trend: [],
      timestamps: [],
      pip_rmssd_correlation: null,
      fragmentation_level: "normal",
      af_risk_indicator: null,
      clinical_notes: ["Error fetching HRF data"],
      quality_ok: false,
    };
  }
}

// ---------------------------------------------------------------------------
// Readiness API
// ---------------------------------------------------------------------------

/**
 * Get readiness score based on HRV baseline
 */
export async function getReadiness(userId: string): Promise<ReadinessResponse> {
  try {
    const response = await fetch(
      `${API_BASE}/api/research/hrv/readiness/${userId}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching readiness:", error);
    return {
      score: null,
      baseline: null,
      deviation_from_baseline: null,
      trend_direction: "stable",
      trend_7day: [],
      trend_dates: [],
      components: [],
      readiness_status: "moderate",
      recommendations: ["Error fetching readiness data"],
    };
  }
}

// ---------------------------------------------------------------------------
// Fatigue API
// ---------------------------------------------------------------------------

/**
 * Get SAFTE-based fatigue prediction
 */
export async function getFatiguePrediction(userId: string): Promise<FatigueResponse> {
  try {
    const response = await fetch(
      `${API_BASE}/api/research/fatigue/${userId}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching fatigue prediction:", error);
    return {
      effectiveness_pct: null,
      fatigue_level: "normal",
      forecast_hours: [],
      forecast_effectiveness: [],
      sleep_debt_hours: null,
      optimal_sleep_hours: 8,
      risk_level: "low",
      risk_color: "green",
      recommendations: ["Error fetching fatigue data"],
      next_optimal_sleep: null,
      avg_sleep_duration_h: null,
      typical_bedtime_h: null,
      avg_sleep_efficiency: null,
      context: buildFallbackContext(),
    };
  }
}

// ---------------------------------------------------------------------------
// Circadian API
// ---------------------------------------------------------------------------

/**
 * Get circadian rhythm analysis
 */
export async function getCircadianAnalysis(userId: string): Promise<CircadianResponse> {
  try {
    const response = await fetch(
      `${API_BASE}/api/research/circadian/${userId}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching circadian analysis:", error);
    return {
      current_phase: "day",
      phase_angle_hours: null,
      optimal_performance_start: null,
      optimal_performance_end: null,
      optimal_sleep_start: null,
      hours: [],
      alertness_level: [],
      light_exposure_lux: null,
      light_recommendation: null,
      chronotype: "intermediate",
      notes: ["Error fetching circadian data"],
    };
  }
}

// ---------------------------------------------------------------------------
// Population Norms API
// ---------------------------------------------------------------------------

/**
 * Get age-stratified population norms
 */
export async function getPopulationNorms(
  userId?: string,
  metric: string = "rmssd"
): Promise<PopulationNormsResponse> {
  try {
    const params = new URLSearchParams({ metric });
    if (userId) params.set("user_id", userId);

    const response = await fetch(
      `${API_BASE}/api/research/norms?${params.toString()}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching population norms:", error);
    return {
      norms: [],
      user_age_group: null,
      user_percentiles: {},
      primary_source: "Error fetching norms",
      additional_sources: [],
    };
  }
}

// ---------------------------------------------------------------------------
// Export API
// ---------------------------------------------------------------------------

/**
 * Export HRV data in various formats
 */
export async function exportHRVData(
  userId: string,
  options: Partial<ExportRequest> = {}
): Promise<ExportResponse> {
  try {
    const request: ExportRequest = {
      format: options.format || "csv",
      include_timeseries: options.include_timeseries ?? false,
      include_frequency: options.include_frequency ?? true,
      include_nonlinear: options.include_nonlinear ?? true,
      include_hrf: options.include_hrf ?? true,
      date_range_days: options.date_range_days || 30,
    };

    const response = await fetch(
      `${API_BASE}/api/research/export/${userId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error exporting HRV data:", error);
    throw error;
  }
}

// ---------------------------------------------------------------------------
// Latest HRV Analysis API
// ---------------------------------------------------------------------------

/**
 * Get latest comprehensive HRV analysis for a user
 */
export async function getLatestHRVAnalysis(userId: string): Promise<HRVAnalysisResult> {
  try {
    const response = await fetch(
      `${API_BASE}/api/research/hrv/latest/${userId}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching latest HRV:", error);
    return {
      recording_time: null,
      duration_minutes: null,
      total_beats: null,
      artifact_percentage: null,
      time_domain: {
        mean_hr: null,
        sdnn: null,
        rmssd: null,
        pnn50: null,
        pnn20: null,
        cvnn: null,
        mean_rr: null,
        sdsd: null,
        nn50: null,
        nn20: null,
      },
      frequency_domain: {
        vlf_power: null,
        lf_power: null,
        hf_power: null,
        total_power: null,
        lf_nu: null,
        hf_nu: null,
        lf_hf_ratio: null,
        vlf_peak: null,
        lf_peak: null,
        hf_peak: null,
      },
      nonlinear: {
        sd1: null,
        sd2: null,
        sd1_sd2_ratio: null,
        dfa_alpha1: null,
        dfa_alpha2: null,
        sample_entropy: null,
        approximate_entropy: null,
      },
      hrf: {
        pip: null,
        pip_h: null,
        pip_s: null,
        ials: null,
        pss: null,
        pas: null,
        quality_ok: false,
      },
      quality_score: null,
      analysis_method: "standard",
    };
  }
}

// ---------------------------------------------------------------------------
// Garmin Metrics API
// ---------------------------------------------------------------------------

/**
 * Get latest Garmin metrics for a user
 */
export async function getLatestGarminMetrics(userId: string): Promise<GarminMetrics> {
  try {
    const response = await fetch(
      `${API_BASE}/api/research/garmin/latest/${userId}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching Garmin metrics:", error);
    return {
      spo2_avg: null,
      spo2_min: null,
      spo2_max: null,
      respiration_awake: null,
      respiration_sleep: null,
      vo2max: null,
      vo2max_fitness_age: null,
      sleep_duration_hours: null,
      sleep_deep_minutes: null,
      sleep_rem_minutes: null,
      sleep_light_minutes: null,
      sleep_awake_minutes: null,
      sleep_efficiency: null,
      sleep_score: null,
      body_battery_high: null,
      body_battery_low: null,
      body_battery_charged: null,
      body_battery_drained: null,
      stress_avg: null,
      stress_max: null,
      stress_high_duration_minutes: null,
      steps: null,
      distance_km: null,
      calories_total: null,
      active_calories: null,
      hrv_overnight: null,
      resting_hr: null,
      date: null,
    };
  }
}

/**
 * Get Garmin metrics history for a user
 */
export async function getGarminHistory(
  userId: string,
  days: number = 30
): Promise<GarminMetrics[]> {
  try {
    const response = await fetch(
      `${API_BASE}/api/research/garmin/history/${userId}?days=${days}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching Garmin history:", error);
    return [];
  }
}

// ---------------------------------------------------------------------------
// Enhanced NOAA Data API (Phase 6)
// ---------------------------------------------------------------------------

import type {
  NOAADataResponse,
  RRUploadRequest,
  RRUploadResponse,
  ComprehensiveCorrelationResponse,
  CorrelationRequest,
} from "@/types/research";

/**
 * Get comprehensive NOAA space weather datasets for correlation analysis
 */
export async function getNOAADatasets(
  days: number = 30,
  sources: string = "planetary_k_index_3h,geospace_dst,solar_wind_wind,f107_flux"
): Promise<NOAADataResponse> {
  try {
    const params = new URLSearchParams({
      days: days.toString(),
      sources,
    });

    const response = await fetch(
      `${API_BASE}/api/research/space-weather/datasets?${params.toString()}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching NOAA datasets:", error);
    return {
      fetched_at: new Date().toISOString(),
      sources: [],
      datasets: {},
      kp_data: [],
      dst_data: [],
      solar_wind_data: [],
      errors: { fetch: error instanceof Error ? error.message : "Unknown error" },
    };
  }
}

// ---------------------------------------------------------------------------
// RR Upload API (Phase 6)
// ---------------------------------------------------------------------------

/**
 * Upload RR interval data for analysis
 */
export async function uploadRRData(data: RRUploadRequest): Promise<RRUploadResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/research/hrv/upload`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error uploading RR data:", error);
    throw error;
  }
}

/**
 * Run comprehensive HRV analysis from RR intervals.
 * Uses the same backend engine as stored analyses.
 */
export async function analyzeRRIntervals(
  rrIntervalsMs: number[],
  method: "welch" | "periodogram" | "ar" | "lomb" = "welch",
): Promise<HRVAnalysisResult> {
  try {
    const response = await fetch(
      `${API_BASE}/api/research/hrv/analyze?method=${method}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(rrIntervalsMs),
      },
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
      );
    }

    return await response.json();
  } catch (error) {
    console.error("Error analyzing RR intervals:", error);
    throw error;
  }
}

export async function computeWorkloadFeatures(payload: {
  rr_intervals_ms: number[];
  segments: WorkloadSegment[];
  task_name?: string;
}): Promise<WorkloadResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/research/workload/compute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error computing workload features:", error);
    return {
      delta_lnrmssd: null,
      delta_hf: null,
      delta_lf_hf: null,
      recovery_slope: null,
      threshold_flags: ["Unable to compute workload features"],
      high_workload_probability: 0.5,
      confidence: "poor",
      context: buildFallbackContext(),
    };
  }
}

export async function getVigilanceTracking(
  userId: string,
  windowSize: number = 30,
  stepSize: number = 10,
): Promise<VigilanceResponse> {
  try {
    const response = await fetch(
      `${API_BASE}/api/research/vigilance/${userId}?window_size=${windowSize}&step_size=${stepSize}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      },
    );
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching vigilance tracking:", error);
    return {
      window_size_seconds: windowSize,
      step_size_seconds: stepSize,
      model_version: "fallback",
      low_vigilance_windows: 0,
      total_windows: 0,
      predictions: [],
      context: buildFallbackContext(),
    };
  }
}

export async function getFlightFatigueClassification(
  userId: string,
): Promise<FlightFatigueResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/research/flight-fatigue/${userId}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching flight fatigue classification:", error);
    return {
      risk_band: "moderate",
      model_version: "fallback",
      probabilities: { low: 0.33, moderate: 0.34, high: 0.33 },
      rationale: ["Insufficient data for calibrated classifier; using neutral fallback"],
      required_features: ["rmssd", "sdnn", "mean_hr", "sleep_debt_hours", "effectiveness_pct"],
      missing_features: ["unknown"],
      context: buildFallbackContext(),
    };
  }
}

export async function getIntegratedFusion(
  userId: string,
): Promise<FusionResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/research/fusion/${userId}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching integrated fusion output:", error);
    return {
      schedule_factor: { value: 0.75, confidence: "moderate", note: "Fallback from SAFTE estimate" },
      autonomic_factor: { value: 1.0, confidence: "poor", note: "No autonomic input" },
      workload_factor: { value: 1.0, confidence: "poor", note: "No workload input" },
      environment_factor: { value: 1.0, confidence: "poor", note: "No environment input" },
      performance_probability: 0.6,
      uncertainty_interval: [0.4, 0.8],
      confidence: "poor",
      rationale: ["Fallback fusion response due to unavailable backend data"],
    };
  }
}

export async function getModelCalibrationReport(): Promise<CalibrationReportResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/research/models/calibration-report`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching model calibration report:", error);
    return {
      generated_at_utc: new Date().toISOString(),
      models: [],
    };
  }
}

/**
 * Parse RR intervals from a text file
 * Supports formats: one value per line, comma-separated, space-separated
 */
export function parseRRFile(content: string): number[] {
  // Remove BOM if present
  const cleaned = content.replace(/^\uFEFF/, "").trim();
  
  // Try different formats
  let values: number[] = [];
  
  // Try one value per line
  const lines = cleaned.split(/[\r\n]+/);
  if (lines.length > 10) {
    values = lines
      .map((line) => parseFloat(line.trim()))
      .filter((v) => !isNaN(v) && v > 0);
  }
  
  // If not enough values, try comma-separated
  if (values.length < 10) {
    values = cleaned
      .split(/[,;]+/)
      .map((v) => parseFloat(v.trim()))
      .filter((v) => !isNaN(v) && v > 0);
  }
  
  // If still not enough, try space-separated
  if (values.length < 10) {
    values = cleaned
      .split(/\s+/)
      .map((v) => parseFloat(v.trim()))
      .filter((v) => !isNaN(v) && v > 0);
  }
  
  return values;
}

// ---------------------------------------------------------------------------
// Comprehensive Correlation Analysis API (Phase 6)
// ---------------------------------------------------------------------------

/**
 * Run comprehensive Solar-HRV correlation analysis
 */
export async function runCorrelationAnalysis(
  request: CorrelationRequest
): Promise<ComprehensiveCorrelationResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/research/correlations/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error running correlation analysis:", error);
    
    // Return empty result
    const now = new Date().toISOString();
    return {
      analysis_date: now,
      data_start: now,
      data_end: now,
      n_days: 0,
      n_hrv_samples: 0,
      n_solar_samples: 0,
      correlation_matrix: [],
      p_value_matrix: [],
      solar_labels: [],
      hrv_labels: [],
      significant_correlations: [],
      all_correlations: [],
      lag_analyses: [],
      optimal_lag_hours: null,
      timeline_data: [],
      pattern_insights: ["Error running analysis: " + (error instanceof Error ? error.message : "Unknown error")],
      recommendations: [],
      methodology_notes: [],
    };
  }
}


// ---------------------------------------------------------------------------
// Ventilatory Threshold (VT) - Experimental
// ---------------------------------------------------------------------------

import type { VTAnalysisResponse } from "@/types/research";

/**
 * Run VT demo analysis with synthetic exercise data
 */
export async function getVTDemo(): Promise<VTAnalysisResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/research/vt/demo`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching VT demo:", error);
    return _emptyVTResponse();
  }
}

/**
 * Analyze VT from uploaded RR interval data
 */
export async function analyzeVT(
  rrIntervals: number[],
  hrRest: number = 60,
  hrMax: number = 185,
  method: string = "multiparameter",
): Promise<VTAnalysisResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/research/vt/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rr_intervals_ms: rrIntervals,
        hr_rest: hrRest,
        hr_max: hrMax,
        method,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error analyzing VT:", error);
    return _emptyVTResponse();
  }
}

function _emptyVTResponse(): VTAnalysisResponse {
  return {
    vt1: null,
    vt2: null,
    timeseries_time: [],
    timeseries_dfa: [],
    timeseries_hr: [],
    timeseries_hr_mean: [],
    timeseries_integrated_score: [],
    respiratory_frequency_hz: null,
    quality: null,
    method: "multiparameter",
    intensity_zones: [],
    interpretation: ["Unable to load data. API may be unavailable."],
    warnings: [],
  };
}

// ---------------------------------------------------------------------------
// Physiological SMS Risk Assessment API
// ---------------------------------------------------------------------------

import type {
  VitalsInput,
  EnhancedReadinessResponse,
  SMSMatrixEndpointResponse,
} from "@/types/research";

/**
 * Submit vitals (BP + temperature) and get enhanced readiness with SMS matrices.
 */
export async function submitVitalsAndAssess(
  userId: string,
  vitals: VitalsInput,
): Promise<EnhancedReadinessResponse> {
  try {
    const response = await fetch(
      `${API_BASE}/api/research/readiness/${userId}/vitals`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(vitals),
      },
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error submitting vitals:", error);
    return _emptyReadinessResponse();
  }
}

/**
 * Get EVA SMS risk classification and heatmap matrix.
 */
export async function getEVASMS(
  sbp?: number,
  dbp?: number,
  tempC?: number,
  readinessScore: number = 80,
): Promise<SMSMatrixEndpointResponse | null> {
  try {
    const params = new URLSearchParams();
    if (sbp != null) params.set("sbp", String(sbp));
    if (dbp != null) params.set("dbp", String(dbp));
    if (tempC != null) params.set("temp_c", String(tempC));
    params.set("readiness_score", String(readinessScore));

    const response = await fetch(
      `${API_BASE}/api/research/sms/eva?${params.toString()}`,
      { method: "GET", headers: { "Content-Type": "application/json" } },
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching EVA SMS:", error);
    return null;
  }
}

/**
 * Get Military Flight SMS risk classification and heatmap matrix.
 */
export async function getFlightSMS(
  sbp?: number,
  dbp?: number,
  tempC?: number,
  readinessScore: number = 80,
  crewRestCompliant?: boolean,
): Promise<SMSMatrixEndpointResponse | null> {
  try {
    const params = new URLSearchParams();
    if (sbp != null) params.set("sbp", String(sbp));
    if (dbp != null) params.set("dbp", String(dbp));
    if (tempC != null) params.set("temp_c", String(tempC));
    params.set("readiness_score", String(readinessScore));
    if (crewRestCompliant != null) {
      params.set("crew_rest_compliant", String(crewRestCompliant));
    }

    const response = await fetch(
      `${API_BASE}/api/research/sms/flight?${params.toString()}`,
      { method: "GET", headers: { "Content-Type": "application/json" } },
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching Flight SMS:", error);
    return null;
  }
}

function _emptyReadinessResponse(): EnhancedReadinessResponse {
  return {
    readiness_score: 0,
    readiness_label: "NO-GO",
    bp_classification: null,
    bp_modifier: null,
    bp_rationale: null,
    temp_classification: null,
    temp_modifier: null,
    temp_rationale: null,
    modifiers: [],
    triggers: ["Unable to connect to API. Check that the backend is running."],
    eva_sms: null,
    flight_sms: null,
    eva_matrix: null,
    flight_matrix: null,
    nasa_hrp_matrix: null,
  };
}

// ---------------------------------------------------------------------------
// Environment / METAR / Weather / Jet Lag API
// ---------------------------------------------------------------------------

import type {
  METARResponse,
  WeatherResponse,
  ICEStationResponse,
  JetLagResponse,
} from "@/types/research";

export async function fetchMETAR(icao: string): Promise<METARResponse> {
  try {
    const resp = await fetch(`${API_BASE}/api/research/metar/${icao}`, {
      headers: { "Content-Type": "application/json" },
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  } catch (error) {
    console.error("METAR fetch error:", error);
    return { icao, metar: null, error: String(error) };
  }
}

export async function fetchWeather(city: string): Promise<WeatherResponse> {
  try {
    const resp = await fetch(`${API_BASE}/api/research/weather/${city}`, {
      headers: { "Content-Type": "application/json" },
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  } catch (error) {
    console.error("Weather fetch error:", error);
    return { city, weather: null, indices: null, error: String(error) };
  }
}

export async function fetchICEStation(): Promise<ICEStationResponse | null> {
  try {
    const resp = await fetch(`${API_BASE}/api/research/environment/ice-station`, {
      headers: { "Content-Type": "application/json" },
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  } catch (error) {
    console.error("ICE station fetch error:", error);
    return null;
  }
}

export async function computeJetLag(
  timeZones: number,
  direction: string,
  daysSince: number,
): Promise<JetLagResponse | null> {
  try {
    const resp = await fetch(`${API_BASE}/api/research/performance/jetlag`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        time_zones: timeZones,
        direction,
        days_since: daysSince,
      }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  } catch (error) {
    console.error("Jet lag compute error:", error);
    return null;
  }
}
