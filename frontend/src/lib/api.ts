// Author: Dr Diego Malpica MD
/**
 * API client for Mission Control - Flight Surgeon backend
 */

import type {
  UserProfile,
  CreateUserRequest,
  UsersListResponse,
  SpaceWeatherSnapshot,
  Experiment,
  CreateExperimentRequest,
  ExperimentsListResponse,
  ScheduleResponse,
  HealthResponse,
  Mission,
} from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8180";

/**
 * Generic fetch wrapper with error handling
 */
async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `API error: ${response.status} ${response.statusText}`
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown API error");
  }
}

// ---------------------------------------------------------------------------
// Health Check
// ---------------------------------------------------------------------------

export async function checkHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/health");
}

// ---------------------------------------------------------------------------
// Mission Management
// ---------------------------------------------------------------------------

export async function getMission(): Promise<Mission> {
  return apiFetch<Mission>("/api/missions");
}

export async function setMission(mission: string): Promise<Mission> {
  return apiFetch<Mission>("/api/missions", {
    method: "POST",
    body: JSON.stringify({ mission }),
  });
}

// ---------------------------------------------------------------------------
// User Management
// ---------------------------------------------------------------------------

export async function listUsers(): Promise<UsersListResponse> {
  return apiFetch<UsersListResponse>("/api/users");
}

export async function getUser(userId: string): Promise<UserProfile> {
  return apiFetch<UserProfile>(`/api/users/${userId}`);
}

export async function createUser(
  userData: CreateUserRequest
): Promise<UserProfile> {
  return apiFetch<UserProfile>("/api/users", {
    method: "POST",
    body: JSON.stringify(userData),
  });
}

export async function updateUser(
  userId: string,
  userData: Partial<UserProfile>
): Promise<UserProfile> {
  return apiFetch<UserProfile>(`/api/users/${userId}`, {
    method: "PUT",
    body: JSON.stringify(userData),
  });
}

export async function deleteUser(userId: string): Promise<void> {
  return apiFetch<void>(`/api/users/${userId}`, {
    method: "DELETE",
  });
}

// ---------------------------------------------------------------------------
// Experiment Management
// ---------------------------------------------------------------------------

export async function listExperiments(): Promise<ExperimentsListResponse> {
  return apiFetch<ExperimentsListResponse>("/api/experiments");
}

export async function getExperiment(experimentId: string): Promise<Experiment> {
  return apiFetch<Experiment>(`/api/experiments/${experimentId}`);
}

export async function createExperiment(
  experimentData: CreateExperimentRequest
): Promise<Experiment> {
  return apiFetch<Experiment>("/api/experiments", {
    method: "POST",
    body: JSON.stringify(experimentData),
  });
}

export async function updateExperiment(
  experimentId: string,
  experimentData: Partial<Experiment>
): Promise<Experiment> {
  return apiFetch<Experiment>(`/api/experiments/${experimentId}`, {
    method: "PUT",
    body: JSON.stringify(experimentData),
  });
}

export async function deleteExperiment(experimentId: string): Promise<void> {
  return apiFetch<void>(`/api/experiments/${experimentId}`, {
    method: "DELETE",
  });
}

// ---------------------------------------------------------------------------
// Scheduling
// ---------------------------------------------------------------------------

export async function getSchedule(): Promise<ScheduleResponse> {
  return apiFetch<ScheduleResponse>("/api/scheduling");
}

// ---------------------------------------------------------------------------
// Space Weather
// ---------------------------------------------------------------------------

export async function getSpaceWeather(): Promise<SpaceWeatherSnapshot> {
  return apiFetch<SpaceWeatherSnapshot>("/api/space-weather");
}
