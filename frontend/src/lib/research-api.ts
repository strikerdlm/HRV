// Author: Dr Diego Malpica MD
/**
 * API functions for Research features
 * - Space Weather data retrieval
 * - HRV-Space Weather correlations
 */

import type {
  SpaceWeatherSnapshot,
  SpaceWeatherData,
  ImpactPrediction,
  CorrelationAnalysisResult,
} from "@/types/research";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8180";

/**
 * Get current space weather data and impact predictions
 */
export async function getCurrentSpaceWeather(): Promise<SpaceWeatherSnapshot> {
  try {
    const response = await fetch(`${API_BASE}/api/space-weather/current`, {
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
