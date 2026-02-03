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
} from "@/types/research";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8180";

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
  method: "welch" | "periodogram" | "ar" = "welch"
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
