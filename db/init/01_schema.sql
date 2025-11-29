-- HRV Analysis Platform - Database Schema
-- Author: Dr. Diego Malpica, MD - Aerospace Medicine Specialist
--
-- This script initializes the database schema for PostgreSQL with TimescaleDB.
-- It creates tables for:
--   - User profiles with biometric data
--   - Clinical assessment scales (ESS, Samn-Perelli, KSS, PSQI, etc.)
--   - HRV measurements and time-series data
--   - Sleep and activity records
--
-- Execute order: 01_schema.sql -> 02_functions.sql -> 03_seed.sql

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- ENUMS
-- =============================================================================

CREATE TYPE sex_type AS ENUM ('male', 'female', 'other');
CREATE TYPE activity_level_type AS ENUM ('sedentary', 'lightly_active', 'moderately_active', 'very_active', 'extremely_active');
CREATE TYPE chronotype_type AS ENUM ('definite_morning', 'moderate_morning', 'neither', 'moderate_evening', 'definite_evening');
CREATE TYPE occupation_type AS ENUM ('pilot', 'atc', 'flight_crew', 'medical', 'shift_worker', 'military', 'driver', 'researcher', 'office', 'other');
CREATE TYPE risk_level_type AS ENUM ('LOW', 'MODERATE', 'HIGH', 'CRITICAL', 'UNKNOWN');
CREATE TYPE data_source_type AS ENUM ('garmin', 'oura', 'whoop', 'apple_health', 'fitbit', 'polar', 'somfit', 'kubios', 'manual', 'unknown');

-- =============================================================================
-- USER PROFILES
-- =============================================================================

CREATE TABLE users (
    user_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    date_of_birth DATE,
    sex sex_type DEFAULT 'other',
    occupation occupation_type DEFAULT 'other',
    
    -- Anthropometrics
    height_cm NUMERIC(5,1),
    weight_kg NUMERIC(5,1),
    
    -- Fitness metrics
    resting_heart_rate_bpm NUMERIC(5,1),
    measured_vo2max NUMERIC(5,1),
    activity_level activity_level_type DEFAULT 'moderately_active',
    
    -- Chronotype
    chronotype chronotype_type DEFAULT 'neither',
    chronotype_offset_hours NUMERIC(4,2) DEFAULT 0,
    
    -- Health conditions
    has_hypertension BOOLEAN DEFAULT FALSE,
    has_diabetes BOOLEAN DEFAULT FALSE,
    has_cardiac_condition BOOLEAN DEFAULT FALSE,
    takes_beta_blockers BOOLEAN DEFAULT FALSE,
    is_smoker BOOLEAN DEFAULT FALSE,
    caffeine_intake_cups_per_day SMALLINT DEFAULT 0,
    
    -- Notes
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_access TIMESTAMPTZ DEFAULT NOW()
);

-- Index for email lookups
CREATE INDEX idx_users_email ON users(email) WHERE email IS NOT NULL;

-- =============================================================================
-- CLINICAL ASSESSMENTS
-- =============================================================================

-- Epworth Sleepiness Scale (ESS)
CREATE TABLE assessments_ess (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    assessment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- 8 items, each 0-3
    sitting_reading SMALLINT CHECK (sitting_reading BETWEEN 0 AND 3),
    watching_tv SMALLINT CHECK (watching_tv BETWEEN 0 AND 3),
    sitting_inactive_public SMALLINT CHECK (sitting_inactive_public BETWEEN 0 AND 3),
    passenger_car_hour SMALLINT CHECK (passenger_car_hour BETWEEN 0 AND 3),
    lying_down_afternoon SMALLINT CHECK (lying_down_afternoon BETWEEN 0 AND 3),
    sitting_talking SMALLINT CHECK (sitting_talking BETWEEN 0 AND 3),
    sitting_quietly_after_lunch SMALLINT CHECK (sitting_quietly_after_lunch BETWEEN 0 AND 3),
    car_stopped_traffic SMALLINT CHECK (car_stopped_traffic BETWEEN 0 AND 3),
    
    -- Computed fields (stored for query efficiency)
    total_score SMALLINT GENERATED ALWAYS AS (
        COALESCE(sitting_reading, 0) + COALESCE(watching_tv, 0) + 
        COALESCE(sitting_inactive_public, 0) + COALESCE(passenger_car_hour, 0) +
        COALESCE(lying_down_afternoon, 0) + COALESCE(sitting_talking, 0) +
        COALESCE(sitting_quietly_after_lunch, 0) + COALESCE(car_stopped_traffic, 0)
    ) STORED,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ess_user_date ON assessments_ess(user_id, assessment_date DESC);

-- Samn-Perelli Fatigue Scale
CREATE TABLE assessments_samn_perelli (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    assessment_datetime TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 7),
    
    -- Context
    hours_since_wake NUMERIC(4,1),
    hours_of_sleep_last_night NUMERIC(4,1),
    caffeine_intake_today SMALLINT DEFAULT 0,
    notes TEXT,
    
    -- Risk level (computed in application, stored for queries)
    risk_level risk_level_type,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_samn_perelli_user_time ON assessments_samn_perelli(user_id, assessment_datetime DESC);

-- Karolinska Sleepiness Scale (KSS)
CREATE TABLE assessments_kss (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    assessment_datetime TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 9),
    
    -- Context
    hours_since_wake NUMERIC(4,1),
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_kss_user_time ON assessments_kss(user_id, assessment_datetime DESC);

-- Pittsburgh Sleep Quality Index (PSQI)
CREATE TABLE assessments_psqi (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    assessment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Component scores (0-3 each)
    subjective_quality SMALLINT CHECK (subjective_quality BETWEEN 0 AND 3),
    sleep_latency_minutes INTEGER,
    cannot_sleep_30min_frequency SMALLINT CHECK (cannot_sleep_30min_frequency BETWEEN 0 AND 3),
    hours_of_sleep NUMERIC(4,1),
    bedtime_hour SMALLINT,
    wake_time_hour SMALLINT,
    
    -- Sleep disturbances (each 0-3)
    wake_middle_night SMALLINT DEFAULT 0,
    bathroom_frequency SMALLINT DEFAULT 0,
    breathing_difficulty SMALLINT DEFAULT 0,
    cough_snore SMALLINT DEFAULT 0,
    feel_cold SMALLINT DEFAULT 0,
    feel_hot SMALLINT DEFAULT 0,
    bad_dreams SMALLINT DEFAULT 0,
    pain SMALLINT DEFAULT 0,
    other_reasons SMALLINT DEFAULT 0,
    
    -- Medication and dysfunction
    sleep_medication_frequency SMALLINT CHECK (sleep_medication_frequency BETWEEN 0 AND 3),
    trouble_staying_awake SMALLINT CHECK (trouble_staying_awake BETWEEN 0 AND 3),
    enthusiasm_problem SMALLINT CHECK (enthusiasm_problem BETWEEN 0 AND 3),
    
    -- Global score (computed in application, 0-21)
    global_score SMALLINT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_psqi_user_date ON assessments_psqi(user_id, assessment_date DESC);

-- Fatigue Severity Scale (FSS)
CREATE TABLE assessments_fss (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    assessment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- 9 items, each 1-7
    item1_motivation SMALLINT CHECK (item1_motivation BETWEEN 1 AND 7),
    item2_exercise SMALLINT CHECK (item2_exercise BETWEEN 1 AND 7),
    item3_easily_fatigued SMALLINT CHECK (item3_easily_fatigued BETWEEN 1 AND 7),
    item4_physical_functioning SMALLINT CHECK (item4_physical_functioning BETWEEN 1 AND 7),
    item5_frequent_problems SMALLINT CHECK (item5_frequent_problems BETWEEN 1 AND 7),
    item6_physical_activities SMALLINT CHECK (item6_physical_activities BETWEEN 1 AND 7),
    item7_work_duties SMALLINT CHECK (item7_work_duties BETWEEN 1 AND 7),
    item8_most_disabling SMALLINT CHECK (item8_most_disabling BETWEEN 1 AND 7),
    item9_interferes_life SMALLINT CHECK (item9_interferes_life BETWEEN 1 AND 7),
    
    -- Computed
    total_score SMALLINT,
    mean_score NUMERIC(3,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fss_user_date ON assessments_fss(user_id, assessment_date DESC);

-- Composite Assessment Sessions (links multiple scales)
CREATE TABLE assessment_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    assessment_datetime TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- References to individual assessments (nullable)
    ess_id UUID REFERENCES assessments_ess(id),
    samn_perelli_id UUID REFERENCES assessments_samn_perelli(id),
    kss_id UUID REFERENCES assessments_kss(id),
    psqi_id UUID REFERENCES assessments_psqi(id),
    fss_id UUID REFERENCES assessments_fss(id),
    
    -- Context
    hours_since_wake NUMERIC(4,1),
    hours_of_sleep_last_night NUMERIC(4,1),
    caffeine_intake_today SMALLINT DEFAULT 0,
    notes TEXT,
    
    -- Computed composite scores
    composite_fatigue_score NUMERIC(5,2),
    operational_risk_level risk_level_type,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_user_time ON assessment_sessions(user_id, assessment_datetime DESC);

-- =============================================================================
-- HRV DATA (Time-series with TimescaleDB)
-- =============================================================================

-- HRV Measurements (summary metrics per recording)
CREATE TABLE hrv_measurements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    recording_datetime TIMESTAMPTZ NOT NULL,
    
    -- Time-domain metrics
    mean_rr_ms NUMERIC(8,2),
    sdnn_ms NUMERIC(8,2),
    rmssd_ms NUMERIC(8,2),
    pnn50 NUMERIC(5,2),
    mean_hr_bpm NUMERIC(5,1),
    sdhr_bpm NUMERIC(5,2),
    
    -- Frequency-domain metrics
    vlf_power NUMERIC(12,2),
    lf_power NUMERIC(12,2),
    hf_power NUMERIC(12,2),
    lf_hf_ratio NUMERIC(6,3),
    total_power NUMERIC(12,2),
    
    -- Nonlinear metrics
    sd1 NUMERIC(8,2),
    sd2 NUMERIC(8,2),
    sd_ratio NUMERIC(6,3),
    sample_entropy NUMERIC(8,4),
    dfa_alpha1 NUMERIC(6,3),
    dfa_alpha2 NUMERIC(6,3),
    
    -- Recording info
    duration_seconds INTEGER,
    total_beats INTEGER,
    artifact_percent NUMERIC(5,2),
    data_source data_source_type DEFAULT 'unknown',
    source_filename VARCHAR(255),
    
    -- Interpretation context
    position VARCHAR(50),  -- supine, sitting, standing
    is_morning_reading BOOLEAN,
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to TimescaleDB hypertable for efficient time-series queries
SELECT create_hypertable('hrv_measurements', 'recording_datetime', if_not_exists => TRUE);

CREATE INDEX idx_hrv_user_time ON hrv_measurements(user_id, recording_datetime DESC);

-- Raw RR intervals (for detailed analysis)
CREATE TABLE rr_intervals (
    id BIGSERIAL,
    measurement_id UUID NOT NULL REFERENCES hrv_measurements(id) ON DELETE CASCADE,
    timestamp_ms BIGINT NOT NULL,  -- Milliseconds since recording start
    rr_ms INTEGER NOT NULL,
    is_artifact BOOLEAN DEFAULT FALSE,
    
    PRIMARY KEY (measurement_id, timestamp_ms)
);

-- =============================================================================
-- SLEEP DATA
-- =============================================================================

CREATE TABLE sleep_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    sleep_date DATE NOT NULL,
    
    -- Timing
    bedtime TIMESTAMPTZ,
    wake_time TIMESTAMPTZ,
    
    -- Duration metrics (in minutes)
    total_sleep_minutes INTEGER,
    time_in_bed_minutes INTEGER,
    sleep_onset_latency_minutes INTEGER,
    wake_after_sleep_onset_minutes INTEGER,
    
    -- Sleep stages (in minutes)
    light_sleep_minutes INTEGER,
    deep_sleep_minutes INTEGER,
    rem_sleep_minutes INTEGER,
    awake_minutes INTEGER,
    
    -- Quality metrics
    sleep_efficiency NUMERIC(5,2),
    sleep_score INTEGER,
    hrv_during_sleep NUMERIC(8,2),
    rhr_during_sleep NUMERIC(5,1),
    respiratory_rate NUMERIC(5,2),
    spo2_average NUMERIC(5,2),
    spo2_minimum NUMERIC(5,2),
    
    -- Source
    data_source data_source_type DEFAULT 'unknown',
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sleep_user_date ON sleep_records(user_id, sleep_date DESC);

-- =============================================================================
-- ACTIVITY DATA
-- =============================================================================

CREATE TABLE activity_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(64) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    activity_date DATE NOT NULL,
    
    -- Daily totals
    steps INTEGER,
    active_minutes INTEGER,
    calories_burned INTEGER,
    distance_km NUMERIC(6,2),
    floors_climbed INTEGER,
    
    -- Heart rate zones (minutes)
    hr_zone_1_minutes INTEGER,  -- 50-60% HRmax
    hr_zone_2_minutes INTEGER,  -- 60-70% HRmax
    hr_zone_3_minutes INTEGER,  -- 70-80% HRmax
    hr_zone_4_minutes INTEGER,  -- 80-90% HRmax
    hr_zone_5_minutes INTEGER,  -- 90-100% HRmax
    
    -- Training metrics
    training_load NUMERIC(8,2),
    recovery_time_hours INTEGER,
    
    -- Source
    data_source data_source_type DEFAULT 'unknown',
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_activity_user_date ON activity_records(user_id, activity_date DESC);

-- =============================================================================
-- TRIGGERS FOR UPDATED_AT
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- VIEWS FOR COMMON QUERIES
-- =============================================================================

-- User profile with computed fields
CREATE VIEW v_user_profiles AS
SELECT 
    u.*,
    EXTRACT(YEAR FROM AGE(u.date_of_birth)) AS age_years,
    CASE 
        WHEN u.height_cm > 0 THEN 
            ROUND((u.weight_kg / POWER(u.height_cm / 100.0, 2))::NUMERIC, 1)
        ELSE NULL 
    END AS bmi,
    CASE 
        WHEN u.date_of_birth IS NOT NULL THEN
            208 - (0.7 * EXTRACT(YEAR FROM AGE(u.date_of_birth)))
        ELSE NULL
    END AS predicted_hr_max
FROM users u;

-- Latest fatigue assessment per user
CREATE VIEW v_latest_fatigue AS
SELECT DISTINCT ON (user_id)
    sp.user_id,
    sp.assessment_datetime,
    sp.rating AS samn_perelli_rating,
    sp.risk_level,
    sp.hours_since_wake,
    sp.hours_of_sleep_last_night
FROM assessments_samn_perelli sp
ORDER BY user_id, assessment_datetime DESC;

-- Latest HRV metrics per user
CREATE VIEW v_latest_hrv AS
SELECT DISTINCT ON (user_id)
    h.user_id,
    h.recording_datetime,
    h.rmssd_ms,
    h.sdnn_ms,
    h.mean_hr_bpm,
    h.lf_hf_ratio,
    h.data_source
FROM hrv_measurements h
ORDER BY user_id, recording_datetime DESC;

-- User dashboard summary
CREATE VIEW v_user_dashboard AS
SELECT 
    u.user_id,
    u.name,
    vp.age_years,
    vp.bmi,
    vf.samn_perelli_rating AS latest_fatigue_rating,
    vf.risk_level AS latest_risk_level,
    vh.rmssd_ms AS latest_rmssd,
    vh.recording_datetime AS last_hrv_recording,
    (SELECT COUNT(*) FROM hrv_measurements WHERE user_id = u.user_id) AS total_hrv_recordings,
    (SELECT COUNT(*) FROM sleep_records WHERE user_id = u.user_id) AS total_sleep_records
FROM users u
LEFT JOIN v_user_profiles vp ON u.user_id = vp.user_id
LEFT JOIN v_latest_fatigue vf ON u.user_id = vf.user_id
LEFT JOIN v_latest_hrv vh ON u.user_id = vh.user_id;

-- =============================================================================
-- COMMENTS FOR DOCUMENTATION
-- =============================================================================

COMMENT ON TABLE users IS 'User profiles with biometric data for physiological calculations';
COMMENT ON TABLE assessments_ess IS 'Epworth Sleepiness Scale assessments (Johns MW, Sleep 1991)';
COMMENT ON TABLE assessments_samn_perelli IS 'Samn-Perelli Fatigue Scale assessments (aviation fatigue)';
COMMENT ON TABLE assessments_kss IS 'Karolinska Sleepiness Scale assessments';
COMMENT ON TABLE assessments_psqi IS 'Pittsburgh Sleep Quality Index assessments';
COMMENT ON TABLE hrv_measurements IS 'HRV measurement summaries with time/frequency/nonlinear metrics';
COMMENT ON TABLE sleep_records IS 'Sleep records from wearables and PSG';
COMMENT ON TABLE activity_records IS 'Daily activity summaries';

