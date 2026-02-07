// Author: Dr Diego Malpica MD
/**
 * TypeScript interfaces for Mission Control - Flight Surgeon
 */

// Mission types
export interface Mission {
  active_mission: string;
  available_missions: string[];
}

// User types
export interface UserProfile {
  user_id: string;
  username: string;
  full_name: string | null;
  email: string | null;
  date_of_birth: string | null;
  sex: "male" | "female" | "other";
  height_cm: number | null;
  weight_kg: number | null;
  resting_hr_bpm: number | null;
  max_hr_bpm: number | null;
  vo2max_ml_kg_min: number | null;
  occupation: string | null;
  activity_level: string | null;
  smoking_status: string | null;
  alcohol_use: string | null;
  caffeine_intake_mg: number | null;
  medical_conditions: string[];
  medications: string[];
  language: string;
  crew_role: string | null;
  crew_status: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface CreateUserRequest {
  username: string;
  full_name?: string;
  sex?: "male" | "female" | "other";
  language?: string;
}

export interface UsersListResponse {
  users: UserProfile[];
  total: number;
}

// Experiment types
export type ExperimentStatus =
  | "draft"
  | "approved"
  | "in_progress"
  | "paused"
  | "completed"
  | "cancelled";

export type ExperimentPriority = "critical" | "high" | "medium" | "low";

export interface Experiment {
  experiment_id: string;
  title: string;
  description: string | null;
  status: ExperimentStatus;
  priority: ExperimentPriority;
  duration_minutes: number;
  required_crew: number;
  equipment: string[];
  assigned_crew: string[];
  created_at: string | null;
  updated_at: string | null;
}

export interface CreateExperimentRequest {
  title: string;
  description?: string;
  priority?: ExperimentPriority;
  duration_minutes?: number;
  required_crew?: number;
  equipment?: string[];
}

export interface ExperimentsListResponse {
  experiments: Experiment[];
  total: number;
}

// Schedule types
export type ActivityCategory =
  | "sleep"
  | "exercise"
  | "meal"
  | "work"
  | "experiment"
  | "maintenance"
  | "communication"
  | "personal"
  | "medical"
  | "emergency";

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface ScheduleEntry {
  entry_id: string;
  crew_member: string;
  activity: string;
  start_time: string;
  end_time: string;
  category: ActivityCategory;
  risk_level: RiskLevel;
}

export interface ScheduleResponse {
  schedule: ScheduleEntry[];
  mission: string;
  generated_at: string;
}

// Space weather types
export interface SpaceWeatherSnapshot {
  kp_index: number | null;
  dst_index: number | null;
  f10_7_flux: number | null;
  solar_wind_speed: number | null;
  solar_wind_density: number | null;
  xray_flux: string | null;
  proton_flux_10mev: number | null;
  fetched_at: string | null;
}

// HRV types
export interface HRVSummary {
  mean_hr: number | null;
  sdnn: number | null;
  rmssd: number | null;
  pnn50: number | null;
  lf_power: number | null;
  hf_power: number | null;
  lf_hf_ratio: number | null;
  total_beats: number | null;
  duration_minutes: number | null;
  artifact_percentage: number | null;
}

// Navigation types
export type NavPage =
  | "dashboard"
  | "scheduling"
  | "experiments"
  | "profile"
  | "about";

export interface NavItem {
  id: NavPage;
  label: string;
  icon: string;
  href: string;
}

// API Response types
export interface ApiError {
  detail: string;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
}
