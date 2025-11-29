-- Space Weather Data Schema
-- Stores NOAA/NASA space weather data for correlation analysis
-- with physiological measurements

-- Enable TimescaleDB extension for time-series optimization
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ===========================================================================
-- Space Weather Records Table
-- ===========================================================================
CREATE TABLE IF NOT EXISTS space_weather_records (
    id SERIAL,
    timestamp TIMESTAMPTZ NOT NULL,
    source VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(20),
    quality_flag VARCHAR(20) DEFAULT 'normal',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Composite primary key for time-series
    PRIMARY KEY (timestamp, source, metric_name)
);

-- Convert to TimescaleDB hypertable for efficient time-series queries
SELECT create_hypertable(
    'space_weather_records', 
    'timestamp',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '7 days'
);

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_sw_source ON space_weather_records(source);
CREATE INDEX IF NOT EXISTS idx_sw_metric ON space_weather_records(metric_name);
CREATE INDEX IF NOT EXISTS idx_sw_source_metric ON space_weather_records(source, metric_name);
CREATE INDEX IF NOT EXISTS idx_sw_created ON space_weather_records(created_at);

-- ===========================================================================
-- Space Weather Fetch Log
-- ===========================================================================
CREATE TABLE IF NOT EXISTS space_weather_fetch_log (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    fetch_time TIMESTAMPTZ NOT NULL,
    records_count INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    
    -- Index for last update queries
    CONSTRAINT valid_status CHECK (status IN ('pending', 'success', 'error'))
);

CREATE INDEX IF NOT EXISTS idx_sw_fetch_source ON space_weather_fetch_log(source);
CREATE INDEX IF NOT EXISTS idx_sw_fetch_time ON space_weather_fetch_log(fetch_time);
CREATE INDEX IF NOT EXISTS idx_sw_fetch_status ON space_weather_fetch_log(status);

-- ===========================================================================
-- HRV-Space Weather Correlation Results
-- ===========================================================================
CREATE TABLE IF NOT EXISTS hrv_sw_correlations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES user_profiles(user_id),
    
    -- HRV information
    hrv_metric VARCHAR(100) NOT NULL,
    hrv_start_time TIMESTAMPTZ NOT NULL,
    hrv_end_time TIMESTAMPTZ NOT NULL,
    hrv_sample_count INTEGER,
    
    -- Space weather information
    sw_source VARCHAR(50) NOT NULL,
    sw_metric VARCHAR(100) NOT NULL,
    
    -- Correlation results
    lag_hours INTEGER NOT NULL,
    pearson_r DOUBLE PRECISION,
    p_value DOUBLE PRECISION,
    n_samples INTEGER,
    
    -- Metadata
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    model_version VARCHAR(20) DEFAULT '1.0',
    
    -- Index for user queries
    CONSTRAINT unique_correlation UNIQUE (user_id, hrv_metric, sw_source, sw_metric, lag_hours, hrv_start_time)
);

CREATE INDEX IF NOT EXISTS idx_corr_user ON hrv_sw_correlations(user_id);
CREATE INDEX IF NOT EXISTS idx_corr_hrv ON hrv_sw_correlations(hrv_metric);
CREATE INDEX IF NOT EXISTS idx_corr_sw ON hrv_sw_correlations(sw_source, sw_metric);
CREATE INDEX IF NOT EXISTS idx_corr_computed ON hrv_sw_correlations(computed_at);

-- ===========================================================================
-- ML Model Predictions Cache
-- ===========================================================================
CREATE TABLE IF NOT EXISTS ml_predictions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES user_profiles(user_id),
    
    -- Prediction information
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    prediction_type VARCHAR(50) NOT NULL,
    
    -- Input features summary
    input_features JSONB NOT NULL,
    input_start_time TIMESTAMPTZ,
    input_end_time TIMESTAMPTZ,
    
    -- Prediction results
    prediction_value DOUBLE PRECISION,
    prediction_class VARCHAR(50),
    confidence DOUBLE PRECISION,
    feature_importance JSONB,
    
    -- Metadata
    predicted_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_prediction_type CHECK (
        prediction_type IN ('af_risk', 'scd_risk', 'sleep_apnea', 'readiness', 'fatigue', 'custom')
    )
);

CREATE INDEX IF NOT EXISTS idx_pred_user ON ml_predictions(user_id);
CREATE INDEX IF NOT EXISTS idx_pred_model ON ml_predictions(model_name);
CREATE INDEX IF NOT EXISTS idx_pred_type ON ml_predictions(prediction_type);
CREATE INDEX IF NOT EXISTS idx_pred_time ON ml_predictions(predicted_at);

-- ===========================================================================
-- Continuous Aggregates for Space Weather (optional optimization)
-- ===========================================================================
-- Hourly averages of Kp index
CREATE MATERIALIZED VIEW IF NOT EXISTS sw_kp_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS bucket,
    AVG(value) AS kp_avg,
    MAX(value) AS kp_max,
    MIN(value) AS kp_min,
    COUNT(*) AS sample_count
FROM space_weather_records
WHERE source = 'NOAA_KP' AND metric_name = 'Kp'
GROUP BY bucket
WITH NO DATA;

-- Daily averages of F10.7 solar flux
CREATE MATERIALIZED VIEW IF NOT EXISTS sw_f107_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS bucket,
    AVG(value) AS f107_avg,
    MAX(value) AS f107_max,
    MIN(value) AS f107_min,
    COUNT(*) AS sample_count
FROM space_weather_records
WHERE source = 'NOAA_F107' AND metric_name = 'F10.7'
GROUP BY bucket
WITH NO DATA;

-- Refresh policies for continuous aggregates
SELECT add_continuous_aggregate_policy('sw_kp_hourly',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

SELECT add_continuous_aggregate_policy('sw_f107_daily',
    start_offset => INTERVAL '30 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ===========================================================================
-- Data Retention Policy (optional - keeps last 2 years of data)
-- ===========================================================================
SELECT add_retention_policy('space_weather_records', 
    INTERVAL '2 years',
    if_not_exists => TRUE
);

-- ===========================================================================
-- Helper Functions
-- ===========================================================================

-- Function to get last N days of Kp data
CREATE OR REPLACE FUNCTION get_kp_last_n_days(days_back INTEGER DEFAULT 30)
RETURNS TABLE (
    timestamp TIMESTAMPTZ,
    kp_value DOUBLE PRECISION,
    quality_flag VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        swr.timestamp,
        swr.value,
        swr.quality_flag
    FROM space_weather_records swr
    WHERE swr.source = 'NOAA_KP' 
      AND swr.metric_name = 'Kp'
      AND swr.timestamp >= NOW() - (days_back || ' days')::INTERVAL
    ORDER BY swr.timestamp;
END;
$$ LANGUAGE plpgsql;

-- Function to get space weather at specific time (for HRV correlation)
CREATE OR REPLACE FUNCTION get_sw_at_time(
    target_time TIMESTAMPTZ,
    sw_source VARCHAR,
    sw_metric VARCHAR,
    tolerance_hours INTEGER DEFAULT 3
)
RETURNS DOUBLE PRECISION AS $$
DECLARE
    result DOUBLE PRECISION;
BEGIN
    SELECT value INTO result
    FROM space_weather_records
    WHERE source = sw_source
      AND metric_name = sw_metric
      AND timestamp >= target_time - (tolerance_hours || ' hours')::INTERVAL
      AND timestamp <= target_time + (tolerance_hours || ' hours')::INTERVAL
    ORDER BY ABS(EXTRACT(EPOCH FROM (timestamp - target_time)))
    LIMIT 1;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (for Docker non-root user)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hrv_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO hrv_admin;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO hrv_admin;

