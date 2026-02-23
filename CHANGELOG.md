# Author: Dr Diego Malpica MD

# Changelog

All notable changes to the Mission Control - Flight Surgeon are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.17.0] - 2026-02-22

### Added
- **Flight-fatigue quality context propagation** (`api/research_endpoints.py`, `frontend/src/app/research/flight-fatigue/page.tsx`, `frontend/src/lib/research-api.ts`, `frontend/src/types/research.ts`):
  - `FlightFatigueResponse` now carries `AnalysisContext` metadata from the backend.
  - Flight Fatigue page now renders `QualityPanel` for protocol/confidence context and caveat messaging.
- **Persistent RR tracing catalog APIs** (`api/research_endpoints.py`, `frontend/src/lib/research-api.ts`, `frontend/src/types/research.ts`):
  - Added `/api/research/hrv/tracings/{user_id}` and `/api/research/hrv/tracings/{user_id}/{measurement_id}` for loading stored RR recordings and optional cached full analyses.
  - Added frontend client contracts and loaders for tracing catalog/detail retrieval.
- **Offline model artifacts + calibration registry** (`api/research_model_registry.py`, `api/model_artifacts/vigilance_model.json`, `api/model_artifacts/flight_fatigue_model.json`, `api/train_research_models.py`):
  - Introduced explicit train/infer split with runtime artifact loading for vigilance and flight-fatigue scoring.
  - Added reproducible offline training utility for artifact regeneration.
- **Calibration metadata endpoint** (`api/research_endpoints.py`, `frontend/src/lib/research-api.ts`, `frontend/src/types/research.ts`):
  - Added `/api/research/models/calibration-report` for model version/performance/reference traceability.

### Changed
- **Frontend gauge style compliance** (`frontend/src/app/research/frequency/page.tsx`, `frontend/src/app/research/nonlinear/page.tsx`, `frontend/src/app/research/fatigue/page.tsx`):
  - Replaced legacy speedometer-style ECharts gauges with two-ring SVG gauges in Frequency (LF/HF), Nonlinear (DFA α1), and Fatigue (effectiveness) views.
  - Aligns research pages with the project gauge policy used across the modern TypeScript frontend.
- **Research Hub coverage** (`frontend/src/app/research/page.tsx`):
  - Added a dedicated Flight Fatigue module card for direct navigation to classifier outputs.
- **In-app scientific explanation pass** (`frontend/src/app/research/workload/page.tsx`, `frontend/src/app/research/vigilance/page.tsx`, `frontend/src/app/research/flight-fatigue/page.tsx`):
  - Added explicit metric interpretation panels and scientific reference cards directly in the new cognition/fatigue modules.
  - Clarified proxy-model and screening-only caveats so interpretation does not rely solely on external docs.
- **Model calibration pass for cognition/fatigue endpoints** (`api/research_endpoints.py`):
  - Upgraded vigilance from static threshold logic to calibrated baseline-relative sliding-window scoring (`windowed_hrv_calibrated_v2`).
  - Upgraded flight-fatigue scoring to calibrated multifeature softmax probabilities (`multifeature_calibrated_v2`) using SAFTE + HRV features with optional LF/HF term.
  - Preserved transparent missing-feature behavior and rationale outputs for operational traceability.
- **Artifact-driven inference wiring** (`api/research_endpoints.py`):
  - Vigilance and flight-fatigue endpoints now read coefficients/thresholds from runtime artifacts instead of hardcoded endpoint constants.
- **Cross-page RR tracing selection** (`frontend/src/components/research/rr-tracing-loader.tsx`, `frontend/src/components/layout/header.tsx`, `frontend/src/lib/store.ts`, `frontend/src/lib/research-api.ts`):
  - Added a global research-header RR tracing loader and persisted selection state.
  - HRV research API calls now forward `measurement_id`/`file_hash` selectors so multiple pages analyze the same stored tracing.

### Fixed
- **Deterministic dashboard behavior** (`frontend/src/app/page.tsx`):
  - Replaced `Math.random()`-driven crew gauge placeholders with deterministic seeded values derived from user identity, preventing metric jitter across rerenders.
- **Poincaré rendering realism** (`frontend/src/app/research/hrv-analysis/page.tsx`):
  - Replaced random synthetic scatter generation with deterministic pairwise points derived from uploaded RR intervals when available.
- **Fatigue model schema cleanup** (`api/research_endpoints.py`):
  - Removed duplicate `next_optimal_sleep` field declaration in `FatigueResponse`.
- **RR persistence and dedupe in research API** (`api/research_endpoints.py`, `frontend/src/app/research/hrv-analysis/page.tsx`):
  - `/api/research/hrv/upload` now persists new RR recordings to SQLite, reuses existing records for duplicate hashes, and returns tracing metadata (`measurement_id`, `file_hash`, `cached`).
  - `/api/research/hrv/analyze` now persists computed analyses into DB cache and reuses cached outputs for identical tracing+settings requests.
  - HRV Analysis page now merges backend tracing catalog with local traces and can load database tracings/cached analysis on demand.
- **Frequency-domain PSD plotting across methods** (`api/research_endpoints.py`, `app/hrv_core.py`):
  - `/api/research/hrv/frequency/{user_id}` now returns `frequencies` and `psd` arrays for Welch, Periodogram, and AR methods (not only Lomb-Scargle), restoring PSD chart rendering for all selector options.
  - AR PSD curve generation is now explicitly supported in `psd_curve()` for consistent method-specific plotting.
- **Batch RR upload responsiveness + manual analysis flow** (`frontend/src/app/research/hrv-analysis/page.tsx`, `api/research_endpoints.py`):
  - Multi-file RR upload now completes without auto-triggering comprehensive analysis; users explicitly run analysis by clicking `Analyze` on a tracing.
  - `/api/research/hrv/upload` now uses a lightweight time-domain metric pass for faster ingestion while preserving persisted tracing IDs/hashes and deduplication.
- **Upload fetch error handling in dev UI** (`frontend/src/lib/research-api.ts`):
  - Removed noisy `console.error` emission for expected network upload failures and replaced it with a normalized thrown message so Turbopack does not surface a console TypeError overlay for caught upload failures.
- **Windowed longitudinal analytics across all ingested RR tracings** (`api/research_endpoints.py`, `frontend/src/lib/research-api.ts`, `frontend/src/types/research.ts`, `frontend/src/app/research/windowed/page.tsx`):
  - `/api/research/hrv/windowed/{user_id}` now supports `scope=all|selected`, computes merged multi-tracing windowed trajectories, and adds robust trend statistics (EWMA + Kendall slope metadata) plus change-point/anomaly detection.
  - Added physiological co-trend/correlation outputs (including Garmin wearable signals when available) and a publication-style frontend dashboard with longitudinal trend, standardized physiology overlays, and a significance-aware correlation heatmap.
  - Added statistical hardening for scientific review: Theil-Sen slope confidence intervals, Benjamini-Hochberg FDR (`q` values) for physiological correlation screening, and explicit methodology notes rendered in the Windowed page.

### Documentation
- Updated `README.md`, `frontend/README.md`, and `docs/Manual.md` to reflect:
  - HRV-cognition modules (workload, vigilance, flight fatigue, integrated fusion),
  - quality-context workflow (`AnalysisContext` + `QualityPanel`),
  - and current frontend research endpoint coverage.

## [1.16.0] - 2026-02-10

### Added
- **Reservoir-Based SAFTE Model** (`frontend/src/lib/safte-model.ts`):
  - Shared module implementing the correct SAFTE equations (Hursh et al. 2004 / DRDC Peng & Bouak 2015)
  - Reservoir dynamics: `R_t = R_{t-1} - K·Δt` (wake), `R_t += f·(R_c-R)·Δt` (sleep)
  - Fatigue-amplified circadian: `circ% = (a1 + a2·(1 - R/R_c)) × C_t`
  - Two-harmonic drive: `C_t = cos(2π(t-18)/24) + 0.5·cos(4π(t-3)/24)`
  - Multi-day predictions (1–7 days) with sleep/wake cycling from Garmin data
  - Used by both Research and Operational tabs
- **FAST-Style Multi-Day Forecast** (research fatigue page):
  - Day selector (1d, 2d, 3d, 5d, 7d) with instant re-computation
  - BAC equivalence thresholds: 90% Normal, 77% Elevated Risk (2.5× cost, FRA validation),
    60% Impairment (≈0.08% BAC, Dawson & Reid 1997), 50% Critical (+65% accident risk)
  - Sleep bands from Garmin-derived schedule, day/night shading
  - Color-coded effectiveness line via `visualMap` (green >90%, yellow 77–90%, red <77%)
  - Nadir/peak annotations, confidence band (±4%), DataZoom slider
- **FAST-Style Fatigue Risk Metrics Panel**:
  - Summary row: Min/Avg Effectiveness, Peak BAC Equiv., Risk Hours, Sleep Debt
  - Blood Alcohol Concentration Equivalence chart (Dawson & Reid 1997 mapping)
  - Cognitive Lapse Probability chart (Van Dongen et al. 2003 PVT adaptation)
- **SAFTE Process Decomposition Chart**: Dual-axis Process S (reservoir) and Process C (circadian)
- **Integrated Physiological Model Card**: Log-linear fusion display (SAFTE + HRV/HRF + Workload + Environment)
- **Garmin Sleep Schedule Integration**:
  - Backend extracts `sleep_start_utc`, `sleep_efficiency`, `sleep_score` from Garmin data
  - New `FatigueResponse` fields: `avg_sleep_duration_h`, `typical_bedtime_h`, `avg_sleep_efficiency`
  - Frontend SAFTE model uses Garmin-derived bedtime and sleep duration instead of defaults
  - Backend falls back to `default` user data when requested user has no Garmin records

### Changed
- **Plot Standards**: All ECharts titles removed from inside plots — titles are in Card headers
  per publication rules (Q1 scientific journal ready, no clutter)
- **Operational Dashboard**: Fatigue levels now computed via SAFTE model instead of random values
- **Scheduling Page**: Fatigue levels now use `currentSAFTEEffectiveness()` from shared SAFTE module
- **Y-Axis**: Forecast chart always includes 60% threshold so BAC/risk zones are visible

### Fixed
- **Wind Compass NaN**: Added `toFiniteNum()` helper to handle non-numeric METAR wind directions
  (e.g., "VRB" for variable wind) that caused `NaN` in SVG coordinates

### Documentation
- **TECHNICAL_DOCUMENTATION.md**: Complete rewrite (v1.0 → v2.0) with correct reservoir equations,
  all three SAFTE variants, architecture diagram, parameter tables, validation data, and references
- **BiomathematicalModel.md**: Cleaned 409 lines of OCR artifacts (page stamps, blank pages)

## [1.15.0] - 2026-02-09

### Added
- **NASA Flight Surgeon Console** (`frontend/src/components/flight-surgeon-console.tsx`):
  - Comprehensive crew health monitoring panel for analog missions (Antarctica,
    high altitude, extreme environments) based on NASA-STD-3001 Vol. 2, Rev B (2019)
  - **Nutrition Tab**: Mifflin-St Jeor BMR calculation (Frankenfield et al., 2005),
    Total Energy Expenditure (TEE) with environmental multipliers:
    - Physical Activity Level (PAL) per NASA JSC-63555 (5 levels: sedentary to very active)
    - Cold exposure metabolic factor per Castellani & Young (2007): 5 levels from
      thermoneutral (x1.0) to extreme cold < -25 C (x1.40)
    - Altitude metabolic factor per Butterfield et al. (1992): 6 levels from
      sea level (x1.0) to extreme >5500m (x1.30)
    - Macronutrient breakdown per NASA-STD-3001: Protein 12-15%, Carbs 50-55%, Fat 25-35%
    - Key micronutrient targets for analog missions (Vitamin D, Calcium, Iron,
      Potassium, Omega-3, etc.) per Smith & Zwart (2008)
  - **Water Requirements Tab**: Daily water calculator with 4 adjustment factors:
    - Baseline: ~33 mL/kg/day (IOM, 2004)
    - Activity: 0-1400 mL/h based on exercise intensity (Sawka et al., 2007)
    - Altitude: +250-1000 mL above 1500m (Butterfield, 1999)
    - Cold exposure: +200-800 mL (Freund & Sawka, 1996)
    - Electrolyte replacement guide (Na+, K+, Cl-, Mg2+)
  - **Altitude Physiology Tab**: SpO2 and resting HR estimation at altitude,
    VO2max reduction estimates, acclimatization timeline, AMS checklist using
    Lake Louise Score (Roach et al., 2018), cold injury prevention (WMS 2019)
  - **Overview Tab**: Flight Surgeon assessment summary with color-coded risk
    indicators, daily monitoring protocol (10-item checklist), crew-care
    thresholds for weight loss, urine SG, SpO2, HR, RMSSD, sleep
  - **5 Scientific ECharts Plots** in expandable floating panes:
    1. Energy Expenditure Breakdown (donut/pie chart)
    2. Macronutrient Radar (current targets vs NASA max ranges)
    3. Water Requirement Stacked Bar (baseline + activity + altitude + cold)
    4. Altitude Physiology dual-axis line (SpO2 + HR vs altitude 0-6000m)
    5. Environmental Stress Heatmap (6 stressors x 5 mission phases)
  - Floating panes with expand-to-fullscreen capability, smooth animations
  - All calculations with full scientific citations and references

### Fixed
- **ESLint 9.x Compatibility**: Added `eslint.config.mjs` flat config for
  `eslint-config-next@16` compatibility with ESLint 9.39
- **React Purity Violation**: Replaced `Math.random()` calls inside
  `CrewRadarChart` render with deterministic pseudo-variation function
  to prevent unstable re-renders
- **Unused Imports**: Cleaned up unused imports (Zap, ChevronDown,
  ImpactPrediction, SEVERITY_COLORS, formatDateTime) from main dashboard
- **Unescaped Entities**: Fixed unescaped double quotes in correlations
  page using proper HTML entities (&ldquo;/&rdquo;)

### Scientific References Added
- NASA. (2019). NASA-STD-3001 Vol. 2, Rev B. Human Factors, Habitability,
  and Environmental Health.
- Lane, H.W. & Schoeller, D.A. (2000). Nutrition in Spaceflight and
  Weightlessness Models. CRC Press.
- Smith, S.M. & Zwart, S.R. (2008). Nutritional Biochemistry of Spaceflight.
  Adv Clin Chem, 46, 87-130.
- Smith, S.M. et al. (2005). J Nutr, 135(3), 437-443.
- Castellani, J.W. & Young, A.J. (2007). J Appl Physiol, 99(4).
- Butterfield, G.E. et al. (1992). J Appl Physiol, 72(4), 1741-1748.
- Bartsch, P. & Saltin, B. (2008). Scand J Med Sci Sports, 18(S1), 1-10.
  DOI: 10.1111/j.1600-0838.2008.00827.x
- Mifflin, M.D. et al. (1990). Am J Clin Nutr, 51(2), 241-247.
- Roach, R.C. et al. (2018). High Alt Med Biol, 19(1), 4-6.
- Luks, A.M. et al. (2019). Wilderness Environ Med, 30(4S), S4-S14.
- IOM. (2004). Dietary Reference Intakes for Water.
- Freund, B.J. & Sawka, M.N. (1996). Arctic Med Res, 55(suppl 1).

## [1.14.0] - 2026-02-09

### Added
- **Hydration & Thermoregulation Physiology Module** (`app/hydration_thermoregulation.py`):
  - Sweat rate prediction across 6 activity levels (sedentary to very hard)
    based on Sawka et al. (2007) ACSM Position Stand and Shapiro et al. (1982)
  - WBGT-based heat stress adjustment factor (ISO 7243:2017)
  - Core body temperature estimation integrating exercise, heat stress, and
    dehydration contributions per Gonzalez-Alonso et al. (1999) and
    Montain & Coyle (1992) (~0.18 C rise per 1% body mass loss)
  - Physiological Strain Index (PhSI) per Moran et al. (1998), scale 0-10
  - Performance decrement model (aerobic, cognitive, strength) based on
    Cheuvront & Kenefick (2014) meta-analysis
  - Dehydration classification: Euhydrated / Mild / Moderate / Significant /
    Severe / Dangerous per body mass loss percentage
  - Integrated hydration-readiness modifier (bounded -10 to 0 pts) for
    IHPI fusion
  - Comprehensive assessment function combining all sub-models
- **Frontend Hydration & Thermoregulation Dashboard**
  (`frontend/src/components/hydration-thermoregulation.tsx`):
  - Interactive HydrationThermoregulationPanel with 6 SVG ring gauges
    (sweat rate, dehydration %, core temp, PhSI, performance, fluid target)
  - Activity level selector, WBGT, body mass, fluid intake, HR inputs
  - Expandable sections for dehydration details, core temperature & heat strain,
    performance impact bars, and fluid replacement guidance
  - Compact HydrationDashboardGauges widget for embedding
  - All gauges follow existing SVG ring gauge style (matching SWRingGauge/IHPI)
- **Operational Dashboard Integration** (main `page.tsx`):
  - Hydration & Thermoregulation panel added after ICE Station / Extreme
    Environment section
  - Heat Stress & Readiness Impact info card with physiological mechanisms,
    sweat rate reference table, and IHPI integration description
  - Hydration modifier integrated into crew IHPI gauge data
- **Readiness Dashboard Integration**:
  - Hydration gauges added to Scheduling Readiness page
  - Full HydrationThermoregulationPanel added to Research Physiological
    Readiness page with expanded scientific references
- **Gauge Builder Thresholds** (`app/gauge_builder.py`):
  - Added 6 new gauge threshold configurations: sweat_rate_ml_h,
    dehydration_pct, core_temp_c, phsi_value, overall_performance_pct,
    fluid_replacement_ml_h
- **Scientific References Added**:
  - Sawka, M.N., et al. (2007). ACSM position stand: Exercise and fluid
    replacement. Med Sci Sports Exerc, 39(2), 377-390.
    DOI: 10.1249/mss.0b013e31802ca597
  - Cheuvront, S.N., & Kenefick, R.W. (2014). Dehydration: Physiology,
    assessment, and performance effects. Compr Physiol, 4(1), 257-285.
    DOI: 10.1002/cphy.c130017
  - Gonzalez-Alonso, J., et al. (1999). Influence of body temperature on
    fatigue during prolonged exercise. J Appl Physiol, 86(3), 1032-1039.
    DOI: 10.1152/jappl.1999.86.3.1032
  - Moran, D.S., et al. (1998). A physiological strain index to evaluate
    heat stress. Am J Physiol, 275(1), R129-R134.
    DOI: 10.1152/ajpregu.1998.275.1.R129
  - Montain, S.J., & Coyle, E.F. (1992). Influence of graded dehydration
    on hyperthermia. J Appl Physiol, 73(4), 1340-1350.
    DOI: 10.1152/jappl.1992.73.4.1340
  - Sawka, M.N., et al. (2015). Hypohydration and human performance.
    Sports Med, 45(S1), S51-S60. DOI: 10.1007/s40279-015-0395-7
  - Shapiro, Y., et al. (1982). Predicting sweat loss response. Eur J Appl
    Physiol, 48(1), 83-96. DOI: 10.1007/BF00421168
  - Casa, D.J., et al. (2015). NATA position statement: Exertional heat
    illnesses. J Athl Train, 50(9), 986-1000.
    DOI: 10.4085/1062-6050-50.9.07
- **Test Suite** (`tests/test_hydration_thermoregulation.py`):
  - 40 pytest cases covering sweat rate, dehydration, core temperature,
    PhSI, performance decrement, comprehensive assessment, and edge cases

## [1.13.0] - 2026-02-07

### Added
- **Environmental Monitoring Dashboard**:
  - ICE Station Monitor with 8 simulated sensors (temp, humidity, CO2, pressure,
    PM2.5, noise, light, O2) for Antarctic/analog research station monitoring
  - ECharts gauge visualizations for CO2 and O2 with color-coded risk zones
  - Auto-refresh every 60 seconds
- **METAR Aviation Weather Dashboard**:
  - Real-time decoded METAR from any ICAO station via FAA AviationWeather.gov
    API (free, no API key required)
  - Station selector with default stations (SKBO Bogota, SAWE Marambio, SCRM
    King George Island Antarctica)
  - Wind compass gauge, decoded fields (temp, dewpoint, wind, visibility, altimeter)
  - Flight category badge (VFR/MVFR/IFR/LIFR)
  - Raw METAR text display
  - Auto-refresh every 10 minutes
- **Extreme Environment Calculators**:
  - Wind Chill Temperature (NWS 2001 formula, Osczevski & Bluestein 2005)
  - Frostbite Time estimation from NWS lookup table interpolation
  - WBGT Heat Stress Index (ISO 7243:2017 / Steadman 1979 simplified)
  - Heat Index (NWS/Rothfusz regression)
  - Cold risk classification: Low/Moderate/High/Very High/Extreme
  - Heat risk classification with work/rest guidance per NIOSH
  - OpenWeatherMap integration for auto-computed indices from real weather data
- **Jet Lag Performance Model**:
  - Circadian resynchronization model based on Waterhouse et al. (2007) and
    Arendt (2009)
  - Eastward (~0.67 h/day) vs westward (~1.0 h/day) asymmetry
  - Exponential recovery curve with configurable inputs
  - Performance factor (0-100%) with readiness modifier (bounded +/-6 pts)
  - Interactive recovery curve chart in crew performance modal
  - Integrated into operational readiness model
- **Dashboard Reorganization**:
  - Environmental monitoring and METAR sections added above alerts
  - Extreme weather calculator paired with crew radar chart
  - Space Weather gauges moved to bottom of dashboard
- **API Endpoints**:
  - `GET /api/research/metar/{icao}` -- Proxy to AviationWeather.gov
  - `GET /api/research/weather/{city}` -- OpenWeatherMap with computed indices
  - `GET /api/research/environment/ice-station` -- Simulated ICE station data
  - `POST /api/research/environment/calculators` -- Wind chill + WBGT from inputs
  - `POST /api/research/performance/jetlag` -- Jet lag impact with recovery curve

### Technical Notes
- Wind chill uses NWS 2001 formula: WC = 13.12 + 0.6215*Ta - 11.37*V^0.16 + 0.3965*Ta*V^0.16
- WBGT uses Steadman (1979) simplified: WBGT = 0.567*Ta + 0.393*e + 3.94
- Jet lag model: performance_factor = 1.0 - penalty * exp(-day / tau)
- 31 unit tests covering all calculators with boundary and edge cases
- httpx added for async API proxying (METAR + OpenWeatherMap)

## [1.12.0] - 2026-02-07

### Added
- **Physiological SMS Risk Assessment Module**:
  - New `physiological_sms.py` implementing BP and temperature readiness modifiers
  - Blood pressure modifier (bounded ±4 pts) per ACC/AHA 2017 guidelines:
    Optimal (+2), Elevated (0), Stage 1 HTN (-2), Stage 2 HTN (-4), Hypotension (-3)
  - Body temperature modifier (bounded ±3 pts):
    Normal (0), Low-grade (-1), Mild fever (-2), Fever (-3), Hypothermia (-3)
  - EVA Readiness SMS risk matrix (5×5, ICAO Doc 9859 adapted) with hard disqualifiers
  - Military Flight SMS risk matrix (4×5, MIL-STD-882E aligned) with G-LOC risk assessment
  - G-LOC risk detection: hypotension + low RMSSD or resting tachycardia
  - USAF crew rest compliance integration (AFMAN 11-202V3)
  - Heatmap data builders for ECharts visualization
- **Readiness Model Enhancement**:
  - `_fuse_operational_readiness_score()` now accepts `bp_modifier` and `temperature_modifier`
  - Backward compatible — new parameters are optional
- **User Profile Schema Extension**:
  - New columns: `baseline_sbp_mmhg`, `baseline_dbp_mmhg`, `basal_temperature_c`,
    `bp_measurement_time`, `temp_measurement_time` (safe additive SQLite migration)
- **API Endpoints**:
  - `POST /api/research/readiness/{user_id}/vitals` — Submit vitals, get enhanced readiness
  - `GET /api/research/sms/eva` — EVA SMS risk classification with heatmap data
  - `GET /api/research/sms/flight` — Flight SMS risk classification with heatmap data
- **TypeScript/Next.js Frontend Pages**:
  - Research page: `/research/physiological-readiness` — Vitals form, modifier waterfall chart,
    dual SMS heatmaps (EVA + Flight), scientific citations
  - Operational page: `/scheduling/readiness` — Go/No-Go decision panels for EVA and
    military flight, large readiness score banner, compact SMS matrices

### Technical Notes
- BP classification follows ACC/AHA 2017 Hypertension Clinical Practice Guidelines
- Temperature thresholds align with clinical fever definitions and circadian variation ranges
- SMS matrices follow ICAO Doc 9859 (4th ed.) and MIL-STD-882E (DoD System Safety)
- Scientific basis: Porta et al. (2012), Lucini et al. (2014), Zhang et al. (2020),
  Crowe et al. (2025), Kim & Lee (2017), Zhang et al. (2025)
- 36 unit tests covering all classification categories, boundaries, and matrix shapes

## [1.11.0] - 2026-02-05

### Added
- **Physiological Trajectory Risk Module (Allostatic Load Alarm)**:
  - New `trajectory_risk.py` implementing multi-day degradation detection
  - EWMA-smoothed 7-day trends for lnRMSSD, resting HR, sleep quality, and DFA-α1
  - Smallest Worthwhile Change (SWC) threshold detection (Plews et al., 2013; Buchheit, 2014)
  - Composite Physiological Strain Index (PSI, 0-100) for allostatic load quantification
  - 5-tier risk classification: IMPROVING → STABLE → WATCH → ELEVATED → CRITICAL
  - Compound risk detection: simultaneous sleep + HRV decline triggers amplified alarm
    (models the Fatigue-Hypoxia feedback loop from McEwen, 1998; Tobaldini et al., 2017)
  - Bounded readiness modifier (±8 pts) for fusion into operational readiness model
  - `compute_trajectory_readiness_modifier()` convenience function for direct model integration
  - Clinical recommendations per risk tier (PVT validation, OTS screening, recovery protocols)
- **Readiness Model Integration**:
  - `_fuse_operational_readiness_score()` now accepts `trajectory_modifier` parameter
  - `predict_operational_performance()` now accepts `trajectory_modifier` parameter
  - Longitudinal layer: catches multi-day degradation before the daily snapshot does
  - All existing tests pass — fully backward compatible (trajectory is optional)

### Technical Notes
- EWMA span=7 (α≈0.25) matches Plews et al. methodology for training adaptation monitoring
- SWC = 0.5 × CV_lnRMSSD (Buchheit, 2014) identifies meaningful vs. noise changes
- PSI uses sigmoid mapping of z-scores with SWC-amplification for declining metrics
- Compound risk (sleep + HRV co-decline) applies 1.3× penalty amplifier, capped at -8 pts
- This addresses Gap #5 (Missing Allostatic Load) from the IRM architecture review

## [1.10.0] - 2026-02-05

### Added
- **HRV-Based Ventilatory Threshold Estimation (Experimental)**:
  - New `vt_analysis.py` module implementing DFA-α1 based VT detection
  - Core DFA-α1 computation (short-term scaling exponent, window 4-16 beats)
  - Time-varying DFA-α1 with configurable 120s sliding window (Kubios standard)
  - Multi-parameter VT detection: 60% DFA-α1 + 30% HR Reserve + 10% Respiratory frequency
  - Confidence scoring and signal quality assessment
  - Exercise intensity zone classification (Zone 1/2/3)
  - Artifact correction with Kubios-style ±20% median threshold
  - Synthetic demo data generator for 20-min graded exercise test
- **Research Frontend Page** (`/research/ventilatory-threshold`):
  - Publication-quality DFA-α1 time series chart with intensity zone shading
  - Heart rate progression with VT1/VT2 vertical markers
  - DFA-α1 vs Heart Rate scatter plot (color-coded by zone)
  - Multi-parameter integrated score visualization
  - Personalized intensity zone cards with training guidance
  - Scientific explanation collapsible with methodology details
  - Full scientific references (Eronen et al., 2024; Gronwald et al., 2020; Rogers et al., 2021)
  - Client-side demo fallback when API is unavailable
- **Research API Endpoints**:
  - `GET /api/research/vt/demo` — Run VT analysis on synthetic exercise data
  - `POST /api/research/vt/analyze` — Analyze uploaded RR interval data
- **Integrated Physiological Model Enhancement**:
  - VT-derived fitness score integrated as bounded modifier (±5 pts) in readiness model
  - `estimate_vt_readiness_contribution()` function for aerobic capacity assessment
  - `predict_operational_performance()` now accepts `vt_fitness_score` parameter
- **Navigation**: VT Estimation added to Research sidebar and Research Hub page
- **Scientific Background**: New highlight card on Research Hub for DFA-α1 VT research

### Technical Notes
- DFA-α1 computed using pure NumPy (no external nolds dependency for core)
- All ECharts follow project publication rules: dark fonts, dynamic axis bounds, scientific colors
- VT analysis validated against Eronen et al. (2024) n=64 study parameters
- Readiness model VT contribution is experimental with explicit bounded constraints

## [1.9.17] - 2026-02-03

### Added
- **Enhanced Garmin Connect Integration** (TypeScript/Next.js frontend):
  - **Auto-load credentials**: Settings dialog with localStorage persistence for user ID, sync days (1-90), and auto-sync toggle
  - **Auto-sync on load**: Optional automatic data synchronization when page loads (configurable)
  - **Multi-day time series charts**: 30-day trends for HRV, RHR, Sleep, SpO2, Stress, and Respiration
  - **Correlation scatter plots**: HRV vs Sleep, HRV vs Stress, SpO2 vs Sleep, RHR vs HRV with Pearson r calculation
  - **Space Weather correlation panel**: Live Kp, Dst, and solar wind display with scientific context
  - **Publication-quality gauges**: Clean half-circle gauges for HRV, Body Battery, Sleep Score, SpO2
  - **Sleep architecture visualization**: Deep/REM/Light sleep breakdown with targets
  - **Tabbed interface**: Overview, Trends, Correlations, and Sleep analysis tabs
- **Scientific context for correlations**: References to McCraty et al. (2018), Shaffer & Ginsberg (2017), Thayer et al. (2012)

### Fixed
- **Garmin history API**: Now returns all physiological fields (respiration, efficiency, distance, calories) instead of subset

### Technical Notes
- Frontend uses `getCurrentSpaceWeather()` API for real-time geomagnetic data correlation
- All charts follow publication rules: no cluttered titles, dynamic axis scaling, dark font colors
- Settings persist in browser localStorage for seamless user experience

## [1.9.16] - 2026-02-02

### Added
- **Comprehensive Crew Scheduling & Human Performance** (TypeScript/Next.js frontend):
  - Complete operational app implementation at `/scheduling` with tabbed interface
  - **Status Dashboard Tab**: Real-time IHPI circular gauges for all crew members, active alerts panel, day summary card with task completion tracking
  - **Schedule Tab**: Full daily schedule with activity cards, date navigation, category filters (medical, exercise, experiment, work, meal, sleep, maintenance, communication, personal, emergency), activity status controls (start/complete)
  - **Crew Management Tab**: Full CRUD operations for crew members with card-based UI showing IHPI scores, fatigue levels, sleep debt, and readiness scores
  - **Performance Tab**: IHPI gauge grid with detailed metrics table including Go/No-Go status indicators
- **Comprehensive Admin Profile Editor**: 5-section tabbed dialog for editing all user profile fields:
  - Identity: Full name, email, sex, date of birth, language, user metadata
  - Operational: Crew role (CDR/PLT/MS1-4), status (on duty/off duty/rest/EVA/medical), occupation
  - Biometrics: Height, weight, resting HR, max HR, VO2max, activity level, auto-calculated BMI
  - Lifestyle: Smoking status, alcohol use frequency, daily caffeine intake with reference values
  - Medical: Conditions and medications lists with confidentiality notice
- **Mission Workspace Selector**: Switch between Mission 1 and Mission 2 with mission-scoped database configurations
- **ECharts Components**: Added PieChart and GraphicComponent to chart registry for gauge visualizations

### Fixed
- **lucide-react icon error**: Replaced non-existent `Scatter` icon with `ScatterChart` in correlations page
- **Badge variant error**: Added missing `danger` variant to badge component
- **NOAA aggregation error**: Added `numeric_only=True` to pandas resample mean() to prevent errors with non-numeric columns
- **Next.js cache corruption**: Documented fix for stale cache issues requiring `.next` and `node_modules/.cache` cleanup

### Changed
- **User Profile API**: Enhanced `PUT /api/users/{user_id}` endpoint to support all profile fields including medical conditions, medications, lifestyle factors
- **Sidebar UI components**: Added new Shadcn/ui components: Dialog, AlertDialog, Tabs, Progress, Label, Textarea

### Technical Notes
- Frontend scheduling page uses Zustand store for mission and user state management
- Framer Motion animations for smooth card transitions and tab switching
- All IHPI calculations follow SAFTE-FAST validation and NASA Human Performance standards
- Scientific references displayed in Performance tab (Hursh 2004, Samel 1997, Van Dongen 2003)

## [1.9.15] - 2026-02-01

### Added
- **Research frontend pages (TypeScript/Next.js)** under `frontend/src/app/research/`:
  - Time Series, Frequency, Nonlinear, HRF, Windowed, Readiness, ANS Tests, Fatigue, Circadian, Population Norms, Unified Timeline, Export Center, and Science/References — all with publication-grade ECharts and mock-data fallbacks.
- **Clinical tools**: New ANS Function Tests page (30:15 ratio, Valsalva ratio, deep breathing E:I) with gauge visuals and interpretation cards.
- **Unified Timeline**: Dual-axis HRV (RMSSD) + Kp index with linked zoom, lag-aware tooltip, and space-weather event callouts.

### Changed
- **Sidebar navigation**: Research navigation reorganized into HRV Analysis, Clinical Tools, and Tools sections with new Timeline and ANS Tests links for faster access.
- **Gauge styling**: Consistent elegant arc/needle style across new pages, adhering to scientific color palette and dark text rules.

### Technical Notes
- Frontend types and API client kept in sync with `/api/research` endpoints for HRV time series, frequency, nonlinear, windowed metrics, HRF, readiness, fatigue (SAFTE), circadian analysis, population norms, and export workflows.

## [1.9.14] - 2026-01-30

### Added
- **TypeScript/Next.js Frontend**: New modern frontend implementation under `frontend/` directory.
  - Complete API client library (`lib/api.ts`, `lib/research-api.ts`) for FastAPI backend communication
  - Utility functions (`lib/utils.ts`) with formatting helpers, debounce, and API configuration
  - Dashboard page with crew profiles, space weather widget, and quick actions
  - Research hub with four comprehensive modules:
    - Space Weather Dashboard: Real-time Kp, F10.7, solar wind gauges with impact predictions
    - HRV Analysis: Time/frequency/nonlinear domain analysis with Poincaré plots and HRF radar
    - Solar-HRV Correlations: Heatmap visualization, lag analysis, significance testing
    - Garmin Integration: Sleep architecture, SpO2, body battery, respiration metrics
  - Publication-quality ECharts components following project visualization standards
  - HRV gauge component with dual-ring design and color-coded risk zones
- **FastAPI Backend**: REST API under `api/` directory exposing Python HRV analysis modules.
  - `/api/health` - Health check endpoint
  - `/api/users` - User profile CRUD operations
  - `/api/experiments` - Experiment management (in-memory storage)
  - `/api/space-weather` - Basic space weather snapshot
  - `/api/research/*` - Comprehensive research endpoints:
    - `/api/research/space-weather/current` - Full space weather with impact predictions
    - `/api/research/hrv/analyze` - RR interval analysis with all HRV domains
    - `/api/research/correlations/hrv-space-weather` - Solar-physiological correlation analysis
    - `/api/research/garmin/*` - Garmin wearable data integration
- **Start Script** (`start-frontend.ps1`): PowerShell script to launch both FastAPI backend and Next.js frontend

### Technical Details
- Frontend runs on port 3100, API on port 8180
- CORS configured for localhost development
- ECharts integration with scientific color palette per project visualization rules
- Full TypeScript type definitions for all API models

### Deprecated
- **Reflex v2 removed**: The experimental Reflex framework has been deprecated in favor of the TypeScript/Next.js frontend. Files removed:
  - `reflex_app/` directory
  - `Dockerfile.reflex`
  - `requirements_reflex.txt`
  - `tests/test_reflex_space_weather_ds_core.py`

## [1.9.13] - 2026-01-25

### Changed
- **Modern UI overhaul**: Space Weather DS page completely redesigned with beautiful card-based layout.
  - Professional visual hierarchy using Radix theme system with sky accent colors
  - Card components for grouping related content (Upload, Configuration, Results, etc.)
  - Prominent status panel with spinner, progress bar, and percentage display during analysis
  - Metric badges with colored backgrounds for better visual feedback
  - Improved section headers with icons for better navigation
  - Responsive grid layouts that adapt to screen size

### Added
- **Toast notifications**: Real-time feedback for user actions:
  - Success toast when files are uploaded
  - Success/warning toasts when HRV analysis completes
  - Success/warning toasts when NOAA data is fetched
  - Success toast when export completes
  - Warning toast when export attempted without data
- Enhanced theme system with modern color palette (sky, slate, emerald, amber)
- Better progress indicator showing percentage complete during analysis

### Fixed
- Changed `check_circle` icon to `check` (valid Lucide icon name)
- Improved file count badge that shows actual number of loaded files

## [1.9.12] - 2026-01-25

### Changed
- **Major architecture overhaul**: Reflex Docker deployment now uses nginx reverse proxy for proper WebSocket handling.
  - `Dockerfile.reflex` now runs backend-only mode
  - New `web.Dockerfile` builds static frontend and serves via nginx
  - New `nginx.conf` proxies `/_event/` with proper WebSocket upgrade headers
  - This fixes the "buttons not working" issue caused by missing WebSocket upgrade headers

### Security
- **CORS hardening**: Reflex default CORS origins changed from `["*"]` to restrictive localhost list (`http://localhost:3000`, `http://localhost:3001`, `http://127.0.0.1:3000`, `http://127.0.0.1:3001`). Production deployments must explicitly set `CORS_ALLOWED_ORIGINS` env var.

### Fixed
- **Buttons not working**: Root cause was missing WebSocket upgrade headers in Docker deployment. Added nginx reverse proxy to properly handle `/_event/` WebSocket connections (reference: https://geniepy.com/blog/how-to-run-reflex-apps-in-production/).
- Defined explicit `@rx.event` setters for all state variables in `OperationalState`, `ResearchState`, and removed reliance on deprecated `state_auto_setters` feature.
- Reflex config now explicitly sets `state_auto_setters=True` to suppress deprecation warnings until migration to explicit setters is complete.
- Removed stale `# type: ignore[attr-defined]` comments from event handler bindings.

## [1.9.11] - 2026-01-25

### Added
- Reflex v2 scaffold under `reflex_app/` (keeps legacy Streamlit `app/` untouched).
- ECharts validation page in Reflex v2 (via `reflex-echarts`) to preserve ECharts-first visuals.
- New Reflex dependency manifest `requirements_reflex.txt`.

### Fixed
- Reflex Docker image now installs `unzip` to satisfy frontend dependency initialization.
- Reflex Space Weather DS slider now binds a sequence value to avoid startup crash.
- Reflex Space Weather DS uses `rx.input(type_="number")` to avoid missing `number_input`.
- Reflex Space Weather DS metrics preview now uses `rx.cond` to avoid Var bool errors.
- Reflex Space Weather DS metric rows now avoid Var boolean checks in `rx.foreach`.
- Reflex Operational users list now avoids Var boolean checks.
- Reflex Research metrics summary now avoids Var boolean checks.
- Reflex Docker defaults to `REFLEX_SSR=false` to avoid prerender crashes.
- Reflex Docker allows all CORS origins by default for local access.
- Reflex Docker defaults to a safe local API URL for event handling.


## [1.9.10] - 2026-01-24

### Added
- New single-user Space Weather Data Science app (`app/space_weather_ds_app.py`) with streamlined HRV/HRF, NOAA/Space Weather analytics, and ML pattern workflows.
- Separate requirements file (`requirements_streamlit_latest.txt`) pinned to Streamlit 1.53.1 for the new app.

### Changed
- README and Manual updated with new app launch instructions and performance profiles.

### Fixed
- Space Weather DS app: avoid double messaging when Garmin file uploads are missing.
- Space Weather DS app: event-aligned deltas now handle named indices when resetting timestamps.

## [1.9.9] - 2026-01-23

### Fixed
- Research UI: Sidebar-driven tab activation now fires only when the selection changes, avoiding redundant reruns.
- Research UI: Stable navigation bypasses manual tab gating for the active section so guest HRV/Space Analytics results render immediately.

## [1.9.8] - 2026-01-22

### Changed
- Research UI: Sidebar navigation now drives the active view (tabs hidden), so navigation happens only from the sidepanel selector.
- Research UI: Stable navigation is enforced in the Research app to keep inactive sections from driving reruns.
- Research UI: HRV processing and Space Weather correlations run in guest mode without requiring a selected profile.

## [1.9.7] - 2026-01-22

### Fixed
- Research UI: Removed experimental tab persistence to eliminate session_state mutation errors and reduce rerun loops.
- User Profile: NASA Nutrition sleep inputs now share the Profile Tools values, so Garmin autofill updates the visible NASA fields immediately.

### Changed
- Research UI: Stable navigation keeps heavy tab rendering gated to the active section via the shared render guard.

## [1.9.6] - 2026-01-22

### Changed
- Research UI: Added **Stable navigation (single section rendering)** with a sidebar selector to minimize rerun load and prevent inactive tabs from re-executing heavy plots.
- Research UI: Added rerun telemetry + an automatic **rerun storm guard** that switches to manual-only processing and disables heavy plots when rapid reruns are detected.

### Fixed
- Time Series: Artifact markers and deviation timelines now downsample using performance caps; Poincaré plots inherit `max_plot_points` for consistent payload size.
- Space Analytics: Manual analysis triggers now use `safe_rerun()` to avoid bypassing the rerun circuit breaker.

## [1.9.5] - 2026-01-22

### Fixed
- User Profile: Garmin autofill for sleep/chronotype inputs now prefers stored Garmin daily metrics and falls back to live Garmin Connect when needed, restoring the NASA Nutrition autofill behavior without forcing credentials.
- App runtime: Debug logging is now opt-in (default off), and file logging follows the debug toggle to reduce idle rerun loops and background overhead on Windows/OneDrive.

## [1.9.4] - 2026-01-20

### Changed
- Research UI: Added a **Processing Mode** sidebar with **Manual-only processing** (default) to prevent auto-run requests from triggering HRV analysis without explicit user action.
- Space Data: Added an **Allow background space-data auto-fetch** toggle (default off) so SWPC/NOAA/DONKI data is fetched only on demand unless explicitly enabled.

## [1.9.3] - 2026-01-06

### Changed
- Crew Scheduling (Operational): Risk Analysis Parameters (IHPI / EVA gates) now update IHPI/risk/EVA gates only on **Calculate** (with optional Auto-calculate toggle), reducing unnecessary recomputation during parameter tuning.
- Crew Scheduling (Operational): 24-Hour Performance Forecast (SAFTE) now runs only when **Calculate performance forecast** is pressed; the last computed forecast is cached per crew member and persists across reruns.

### Fixed
- Crew Scheduling (Operational): Garmin-derived sleep history is disabled by default and is only fetched/used for forecasting when explicitly enabled.

## [1.9.2] - 2025-12-31

### Fixed
- Git metadata lookup now backs off for 10 minutes after a timeout and skips probing when the `.git` folder is absent, reducing noisy Streamlit errors on slow or locked filesystems.
- Crew Scheduling SAFTE 24-hour forecast chart now uses explicit local-time x-axis labels and hourly interpolation, fixing misaligned hour-of-day effectiveness points (e.g., 01:00–06:00) in the operational app.
- Crew Scheduling Garmin sleep fetch now correctly auto-populates sleep duration/quality inputs by writing to Streamlit widget session state keys, and avoids swallowing Streamlit rerun signals (no more confusing `RerunException` errors).
- Crew Scheduling SAFTE prediction chart now uses the same multi-day cognitive performance pipeline and thresholds as the Research app (90/77/70), so circadian troughs (02:00–06:00) are visible and comparable across UIs.
- Crew Scheduling now automatically reuses Garmin daily metrics already imported for the active profile (stored in the mission DB), so you don’t need to re-enter Garmin credentials to generate SAFTE predictions.
- Crew Scheduling Cognitive Performance Prediction (SAFTE) chart now defaults to a zoomed Y-axis view (60–100%) with enhanced axis styling and a taller canvas for easier inspection of curve details (never clips values below 60 or above 100).

## [1.9.1] - 2025-12-30

### Added - Enhanced Space Weather & EVA Radiation Dashboards

#### New Visualizations

1. **EVA Radiation Metrics Dashboard** — Comprehensive real-time radiation monitoring plot:
   - Multi-metric horizontal bar chart showing Proton Flux (>10 MeV), Kp Index, and EVA Dose Rate
   - Values normalized to percentage of critical threshold for visual comparison
   - Color-coded risk zones (green/yellow/red) based on S-scale and G-scale classifications
   - Critical threshold reference line at 100% for operational decision-making
   - Dynamic axis bounds ensuring all data points are visible
   - Publication-quality ECharts visualization following Nature Research guidelines

2. **Space Weather Real-Time Dashboard** — Beautiful gauge-based visualization:
   - **Top Row (3 gauges)**: Flare probability gauges for C-Class, M-Class, and X-Class solar flares
   - **Bottom Row (2 gauges)**: F10.7 Flux gauge (with historic average and projected trend) and Active CMEs gauge
   - Modern two-ring gauge style with animated progress indicators
   - Color-coded zones for quick risk assessment (green=low, yellow=moderate, red=high)
   - Real-time data source and timestamp display
   - Larger gauge size (380px height) for improved visibility

#### UI Improvements

- **Dark Blue Font Colors**: Updated "Key Finding" text in EVA Scientific & Technical References section to dark blue (#1e40af) for better readability
- **References Section**: Updated font color in schedule EVA references section to dark blue
- **Link Verification**: Verified and validated all Additional Technical Resources links:
  - ✅ NASA EVA Technical Library (https://eva.jsc.nasa.gov/)
  - ✅ NASA-STD-3001 Technical Brief: Decompression Sickness (PDF)
  - ✅ NTRS: EVA Hardware & Operations Overview
  - ✅ Springer: EVA Prebreathe Protocols
  - Removed inaccessible HSIR link (https://msis.jsc.nasa.gov/sections/section14.htm)

#### Technical Details

- **EVA Radiation Metrics Plot**: Uses `_auto_axis_bounds()` helper for dynamic scaling
- **Space Weather Gauges**: Implements modern gauge visualization with color zones and progress rings
- **Real-Time Data Integration**: Fetches live space weather data from NOAA SWPC and SpaceWeatherLive APIs
- **Mission Control Ready**: Designed for operational use in mission control environments

### References

- NOAA Space Weather Prediction Center. (n.d.). *Space Weather Scales* (R, S, G). Retrieved from https://www.swpc.noaa.gov/noaa-scales-explanation
- NASA-STD-3001 Vol 1 Rev B. (2022). *Crew Health Standard*. NASA Johnson Space Center.
- Space Weather Prediction Center. (n.d.). *Operational Thresholds*. Retrieved from https://www.swpc.noaa.gov/
- SpaceWeatherLive. (n.d.). *API Documentation*. Retrieved from https://www.spaceweatherlive.com/

## [1.9.0] - 2025-12-29

### Added - Crew Scheduling & Human Performance Management System

Implemented a comprehensive **Crew Scheduling and Human Performance Management** tool for the operational app following the scientific specifications in `SchedulingTool.md`. This system supports mission planning, risk assessment, and GO/NO-GO decisions for up to 6 crew members.

#### New Modules

1. **`app/scheduling_core.py`** — Core Science Layer:
   - **MET/Energy Conversions**: kcal/hr from MET, Watts conversion, activity energy estimation
   - **Subscore Mappers (0-1 scale)**:
     - `score_safte()`: SAFTE effectiveness (70→0, 90→1)
     - `score_kss()`: Karolinska Sleepiness Scale (5→1, 8→0)
     - `score_pvt_lapses_3min()`: PVT performance (≤10→1, ≥20→0)
     - `score_hrv_z()`: lnRMSSD z-score (-0.5→1, -2.0→0)
     - `score_hydration()`: Body mass loss + USG combined
     - `score_energy_availability()`: IOC thresholds (30→0, 45→1)
     - `score_circadian_alignment()`: Phase offset (1h→1, 6h→0)
     - `score_task_specific()`: VO2max + recovery time
   - **IHPI Composite**: Weighted sum with hard-cap gating (critical=0 → IHPI=0)
   - **EVA GO/NO-GO**: Science-based decision tree with reasons
   - **Activity Definitions**: 12+ activity types with MET values from 2024 Compendium

2. **`app/scheduling_engine.py`** — Constraint-Based Optimization:
   - **Crew Management**: Up to 6 crew members with physiological status
   - **Schedule Generation**: Automatic fixed activity scheduling
   - **Conflict Detection**: Concurrent exercise limits, recovery requirements
   - **Risk Classification**: Per-activity risk assessment
   - **Optimization Algorithm**: Constraint satisfaction with soft optimization

3. **`app/scheduling_tab.py`** — Streamlit UI (4 Tabs):
   - **Status Dashboard**: Live crew status cards with IHPI gauges
   - **Timeline & Scheduling**: ECharts Gantt chart with drag-drop (planned)
   - **Risk Analysis**: Risk matrix heatmap + individual performance gauges
   - **Summary & Export**: Readiness metrics, alerts, JSON/CSV export

#### Scientific Foundations

- **SAFTE-FAST Validation**: Risk thresholds from U.S. Senate testimony (≥90 low-risk, <70 ≈0.08 BAC)
- **NASA Standards**: EVA VO2max ≥32.9 ml/kg/min (NASA-STD-3001)
- **IOC Consensus**: Energy Availability thresholds (45/30 kcal/kg FFM/day)
- **HRV Monitoring**: lnRMSSD z-score approach (Plews et al., 2013)
- **Hydration**: ACSM >2% body mass loss threshold; USG operational bins
- **PVT Anchors**: 3-min protocol with 355ms lapse threshold

#### Key Features

- **Integrated Human Performance Indicator (IHPI)**: 8-component weighted score with weights:
  - SAFTE effectiveness: 30%
  - PVT performance: 20%
  - Circadian alignment: 10%
  - HRV (lnRMSSD z): 10%
  - Hydration status: 10%
  - Energy availability: 10%
  - Subjective sleepiness: 5%
  - Task-specific readiness: 5%

- **EVA GO/NO-GO Decision Matrix**:
  - Hard NO-GO gates: SAFTE<70, KSS≥8, sleep<6h, awake≥21h, dehydration>2%, PVT≥20, VO2max<32.9
  - HOLD zone: SAFTE 70-79 (high-risk)
  - GO thresholds: IHPI≥85 (full GO), IHPI 75-84 (GO-with-mitigation)

- **Activity Scheduling**:
  - Fixed activities: Briefing (07:00), Meals, Sleep (8h blocks)
  - Variable activities: Lab Work, EVA (with recovery requirements)
  - Resource-limited: Exercise (max 2 concurrent)

#### References

- Hursh SR et al. (2004). Fatigue models for applied research. Aviat Space Environ Med.
- Plews DJ et al. (2013). Training adaptation and HRV. Int J Sports Physiol Perform.
- IOC Consensus Statement (2018). Relative Energy Deficiency. Br J Sports Med.
- NASA-STD-3001 Vol 1 Rev B (2022). Human Performance Capabilities.
- 2024 Adult Compendium of Physical Activities.

### Tests

- Added `tests/test_scheduling_core.py` with comprehensive unit tests for:
  - MET/energy conversions
  - All subscore mappers with boundary conditions
  - IHPI computation with hard-cap gating
  - EVA GO/NO-GO decision logic
  - Activity definitions and crew status

---

## [1.8.93] - 2025-12-29

### Added - Publication-Quality HRV × Activity Charts

Upgraded **HRV × Activity (Garmin daily metrics)** section with publication-quality visualizations
following `.cursor/rules/plots/RULE.md` standards.

**New Chart Builders:**

1. **HRV × Activity Time Series** (`_build_hrv_activity_timeseries_chart`):
   - Dual-axis chart: Steps (bars) + RMSSD (line)
   - **WHO Target Zone** (8k-10k steps) shaded in green
   - **10k Goal** dashed line marker
   - 7-day EWMA trend lines for both metrics
   - Dynamic axis scaling for both axes
   - Blue gradient bars for steps, red line for RMSSD
   - References: Plews et al. (2013), Stanley et al. (2013)

2. **HRV × Activity Scatter Plots** (`_build_hrv_activity_scatter_chart`):
   - Scatter points with semi-transparent blue fill
   - **Linear regression line** (red) showing trend
   - **Correlation strength** color-coded in subtitle:
     - 🟢 Strong (|r| ≥ 0.7)
     - 🟡 Moderate (0.4-0.7)
     - ⚪ Weak (0.2-0.4)
     - ⚫ Negligible (<0.2)
   - Dynamic axis bounds for all scatter plots
   - 2-column layout for correlation matrix
   - Reference: Buchheit (2014)

**Scatter Correlations Available:**
- RMSSD vs Steps
- RMSSD vs Distance (km)
- RMSSD vs Calories
- RMSSD vs Sleep Score
- RMSSD vs Stress Score
- RMSSD vs Body Battery

**Features per Plotting Rule:**
- Dynamic axis scaling (`_auto_axis_bounds()`)
- Evidence-based reference zones
- Interactive tooltips
- Scientific interpretation captions
- 400px height for time series, 320px for scatter plots

### Fixed

- Fixed indentation errors in `_render_eva_semaphore()` and `_render_allostatic_load()`

---

## [1.8.92] - 2025-12-29

### Added - Publication-Quality Assessment History Charts

Upgraded **Assessment History** section with publication-quality visualizations
following `.cursor/rules/plots/RULE.md` standards.

**New Chart Builders:**

1. **Fatigue & Sleepiness Trends** (`_build_fatigue_sleepiness_chart`):
   - Dual-series: Samn-Perelli (SP, 1-7) and Karolinska (KSS, 1-9)
   - **Color-coded zones:**
     - 🟢 Alert Zone (1-3.5): Optimal performance
     - 🟡 Tired Zone (3.5-5.5): Caution warranted
     - 🔴 Exhausted Zone (>5.5): Performance impairment risk
   - Threshold lines at 3.5 (alert) and 5.5 (fatigue)
   - 5-day EWMA trend lines for both scales
   - Dynamic axis bounds (1-9 range)
   - References: Samn & Perelli (1982), Åkerstedt & Gillberg (1990)

2. **PANAS Affect Trends** (`_build_panas_affect_chart`):
   - Dual-series: Positive Affect (PA) and Negative Affect (NA)
   - **Color-coded zones:**
     - 🟢 High PA Zone (>35): Optimal mood state
     - 🔴 High NA Zone (>25): Mood concern indicator
   - Population mean reference lines (PA ~33, NA ~17)
   - 5-day EWMA trend lines
   - Triangle markers for NA, circle for PA (visual distinction)
   - Dynamic axis bounds (10-50 scale)
   - References: Watson et al. (1988), Crawford & Henry (2004)

**Features per Plotting Rule:**
- Dynamic axis scaling (`_auto_axis_bounds()`)
- Evidence-based reference zones
- Interactive cross-hair tooltips
- Scientific interpretation captions
- 380px height, DataZoom enabled

---

## [1.8.91] - 2025-12-29

### Added - Publication-Quality Radiation Dose Chart

Upgraded the **Radiation Exposure** section in the Exploration Medical Analytics Dashboard
with a publication-quality radiation dose visualization following `.cursor/rules/plots/RULE.md`.

**New Chart Builder:** `_build_radiation_dose_chart()`

**Features:**
- **Mission Day x-axis** with clear labeling
- **Dynamic y-axis scaling** via `_auto_axis_bounds()` — ensures all data fits
- **Color-coded risk zones** based on NASA-STD-3001 Rev B (2022):
  - 🟢 **GO Zone** (<30% = 0-180 mSv): Nominal operations
  - 🟡 **MONITOR Zone** (30-60% = 180-360 mSv): Enhanced monitoring
  - 🟠 **CAUTION Zone** (60-80% = 360-480 mSv): Mission planning review
  - 🔴 **NO-GO Zone** (>80% = >480 mSv): Operational restrictions
- **Threshold lines** at 30%, 60%, 80% limits (dynamically shown when relevant)
- **5-day EWMA trend line** for dose accumulation trend
- **Purple gradient** for cumulative dose with subtle area fill
- **Interactive tooltip** showing mSv values and mission day
- **Scientific caption** citing NASA-STD-3001, ICRP Publication 123, Cucinotta et al.

**References:**
- NASA-STD-3001 Vol 1 Rev B (2022). Crew Health Standard.
- ICRP Publication 123 (2013). Assessment of radiation exposure of astronauts.
- Cucinotta et al. (2017). Space radiation risks for astronauts on multiple ISS missions.

---

## [1.8.90] - 2025-12-29

### Added - Publication-Quality Charts for Exploration Medical Analytics Dashboard

Upgraded the **Stress & Behavioral Indicators** section with publication-quality visualizations
following the `.cursor/rules/plots/RULE.md` standards.

**New Chart Builders:**

1. **Stress Index & Parasympathetic Index Chart** (`_build_stress_pns_chart`):
   - Dual-axis time series with dynamic axis scaling via `_auto_axis_bounds()`
   - Stress Index zones: <50 low (green) | 50-100 normal (blue) | 100-150 elevated (yellow) | >150 high (red)
   - Threshold lines at 100 and 150 for clinical interpretation
   - PNS Index on secondary axis with 0-baseline reference
   - 7-day EWMA trend lines for both metrics
   - Scientific citations: Baevsky et al. (2002), Shaffer & Ginsberg (2017)

2. **Sleep Duration Chart** (`_build_sleep_duration_chart`):
   - Bar chart with NSF-recommended 7-9 hour optimal zone (green shaded)
   - Sleep deprivation warning zone (<6 hours, red tint)
   - 7-hour minimum and 6-hour warning threshold lines
   - 7-day EWMA trend line overlay
   - Dynamic y-axis bounds ensuring all data fits
   - Scientific citations: Hirshkowitz et al. (2015), Watson et al. (2015)

**Features per Plotting Rule:**
- Dynamic axis scaling (`_auto_axis_bounds()`) — no data clipping
- Age-appropriate reference zones with color semantics
- Interactive tooltips with formatted values
- EWMA smoothing for trend visualization
- Scientific interpretation captions below each chart
- 380px height for optimal viewing

---

## [1.8.89] - 2025-12-29

### Fixed - Dynamic Axis Bounds for All Charts

**Problem:** Charts with hardcoded axis min/max values (e.g., `"min": 40, "max": 110`) would 
clip data points that fell outside these ranges, making them invisible or cut off at the edge.

**Solution:** Added `_auto_axis_bounds()` helper function that dynamically calculates axis 
bounds to fit ALL data with appropriate padding.

**Helper Function:**
```python
def _auto_axis_bounds(
    *data_arrays,           # Variable number of data arrays
    padding_pct=0.10,       # 10% padding by default
    min_floor=None,         # Optional minimum (e.g., 0 for non-negative)
    max_ceil=None,          # Optional maximum (e.g., 100 for percentages)
    nice_round=True,        # Round to "nice" axis labels
) -> Tuple[float, float]:
```

**Charts Updated:**
- `_build_hr_stress_chart()` — Now uses dynamic HR bounds (was 40-110)
- `_build_respiration_spo2_chart()` — Now uses dynamic SpO₂ and respiration bounds

**Plotting Rules Updated:**
- Added Section 3 "Dynamic Axis Bounds (CRITICAL)" to `.cursor/rules/plots/RULE.md`
- Updated checklist to include dynamic bounds verification
- Updated `.cursor/rules/plots.mdc` quick reference

---

## [1.8.88] - 2025-12-29

### Added - Publication-Quality Wearable Monitoring & Predictive Analytics Charts

**Scientific Background:** These visualizations follow guidelines from Nature Research and incorporate 
evidence-based reference ranges for clinical interpretation. Each metric provides insight into different 
aspects of physiological function and recovery capacity.

**New Publication-Quality Wearable Trend Charts:**

1. **Activity & Movement** (`_build_activity_movement_chart`):
   - Bar chart with 7-day EWMA trend line
   - WHO target zone (8,000-10,000 steps/day) shaded
   - 10k target line with dashed indicator
   - Calorie overlay on secondary axis
   - Reference: Tudor-Locke et al. (2011) Int J Behav Nutr Phys Act

2. **Heart Rate & Stress** (`_build_hr_stress_chart`):
   - Resting HR with athletic zone (<60 bpm) highlighted
   - 7-day HR trend line
   - Stress score bars with trend overlay
   - Garmin stress scale zones (0-25 rest, 26-50 low, 51-75 med, 76-100 high)
   - Reference: Shaffer & Ginsberg (2017)

3. **Sleep & Recovery** (`_build_sleep_recovery_chart`):
   - Sleep score and efficiency lines
   - 85% clinical threshold indicator
   - Sleep duration bars with optimal zone (7-9h) shaded
   - Reference: Ohayon et al. (2017), NSF (2015)

4. **Respiration & SpO₂** (`_build_respiration_spo2_chart`):
   - SpO₂ line with 95% clinical threshold
   - Normal respiration zone (12-20 rpm)
   - Separate awake/sleep respiration tracking
   - Reference: WHO Pulse Oximetry Training Manual (2011)

5. **Body Battery** (`_build_body_battery_chart`):
   - Energy zones color-coded (75-100 High, 50-74 Moderate, 25-49 Low, <25 Critical)
   - 7-day trend line
   - Charge/drain bars on secondary axis
   - 25% threshold warning line
   - Reference: Firstbeat Technologies (2014)

**Enhanced Advanced Predictive Analytics:**

1. **Body Battery Forecast** - Enhanced with:
   - Styled metric cards for trend/accuracy/recovery
   - Energy zones overlaid on forecast
   - 95% confidence interval band
   - Publication-quality axis labels and subtitles

2. **Allostatic Load Index** - Enhanced with:
   - Semi-circular gauge with 4 risk zones
   - Radar chart for component scores
   - Styled trend cards (7d/30d)
   - Reference: McEwen (1998), Seeman et al. (2001)

3. **Circadian Rhythm Profile** - New 24-hour polar chart:
   - Cosine-based performance curve centered on acrophase
   - Peak performance hours highlighted in green
   - Chronotype-specific optimization tips
   - Reference: Roenneberg et al. (2003)

4. **Stress Prediction** - Enhanced with:
   - Semi-circular stress gauge with 4 zones
   - Styled contributing factors list
   - Risk level card with icon
   - Reference: Cohen et al. (1983), McEwen (2008)

5. **Recovery Status** - Enhanced with:
   - Recovery score gauge (0-100)
   - Sleep debt and stress accumulation cards
   - Days to recovery estimation
   - Reference: Kellmann (2010), Meeusen et al. (2013)

**UI Improvements:**
- All trend charts now use expanders for better organization
- Scientific citations added to each visualization
- Consistent styling with SCIENTIFIC_COLORS palette
- Interactive data zoom on all charts

---

## [1.8.87] - 2025-12-29

### Added - EVA Clearance Semaphore & Space Weather Improvements

**EVA Clearance Semaphore Optimization (`_render_eva_semaphore`, `_compute_joint_eva_decision`):**
- Semaphore now reflects **joint decision** from multiple safety factors:
  - **Flight Surgeon's clearance** (authoritative - can override all other factors)
  - **EVA Radiation Risk Matrix** assessment (GO, GO_WITH_MONITORING, CAUTION, NO_GO)
  - **NOAA S-Scale** (Solar Radiation Storm, 0-5)
  - **NOAA G-Scale** (Geomagnetic Storm, 0-5)
- Uses **conservative (most restrictive) approach** - worst status determines final decision
- Added new **CAUTION** state between MONITOR and NO-GO for intermediate risk levels
- Prominent joint decision summary with icon and rationale
- Collapsible **Contributing Factors** breakdown showing each input's contribution
- If Flight Surgeon says "No EVA" → immediate NO-GO regardless of other factors

**Space Weather Auto-Fetch for EVA Radiation Risk Matrix:**
- New **"Auto-fetch from NOAA SWPC"** checkbox to retrieve real-time S/G scales
- Real-time metrics display when auto-fetch enabled:
  - Kp Index (max) with G-Scale delta
  - >10 MeV Proton flux (pfu) with S-Scale delta
  - S-Scale and G-Scale severity labels
- **Refresh button** to force-fetch latest data from NOAA SWPC
- **Manual override** always available - user can select different values
- Notification when manual override is active (different from NOAA data)

**Helper Functions:**
- `_compute_joint_eva_decision()`: Combines all safety inputs into unified GO/MONITOR/CAUTION/NO-GO
- `_s_scale_severity_label()`: Returns severity label (None/Minor/Moderate/Strong/Severe/Extreme)
- `_g_scale_severity_label()`: Returns severity label for G-Scale

### Fixed
- **Nested Expander Error**: Replaced `st.expander()` in EVA semaphore with HTML `<details>` element
  to avoid Streamlit's "Expanders may not be nested inside other expanders" error

### References
- NOAA Space Weather Scales: https://www.swpc.noaa.gov/noaa-scales-explanation
- NASA STD-3001 Space Flight Human-System Standard

---

## [1.8.86] - 2025-12-29

### Fixed
- **NaN Propagation in EWMA Smoothing** (`_ewma_smooth`): Fixed critical bug where NaN values 
  from incomplete SDNN data (via LEFT merge) would propagate through the entire EWMA output array.
  The function now properly skips NaN values and carries forward the last valid smoothed value,
  ensuring trend lines remain visible even with sparse data.

### Added - HRV Measurement History Publication-Quality Upgrade

**Comprehensive Age-Stratified Normative Data System:**
- `AGE_SDNN_NORMS`: SDNN reference values by age group (Task Force 1996, Umetani et al. 1998)
- `AGE_LF_HF_NORMS`: LF/HF ratio norms reflecting age-related sympathovagal balance shifts
- `AGE_HR_NORMS`: Resting heart rate reference ranges (Tanaka et al. 2001, AHA guidelines)
- Helper functions: `_get_age_sdnn_norms()`, `_get_age_lf_hf_norms()`, `_get_age_hr_norms()`

**Publication-Quality HRV History Visualizations (Nature/Science Guidelines):**
- **Dual-Axis RMSSD/SDNN Chart** (`_build_hrv_history_dual_axis_chart`):
  - Age-stratified 5th-95th percentile normal range bands
  - Population mean reference lines
  - EWMA smoothing trend (7-day span) for noise reduction
  - 7-day rolling average for trend identification
  - Interactive pan/zoom with data picker
  - Colorblind-friendly Scientific Color Palette

- **Heart Rate Trend Chart** (`_build_hr_trend_chart`):
  - Physiological zone coloring (athletic/good/normal/elevated/high)
  - Age-based normal range shading
  - Population mean reference line
  - Visual mapping: Green (<60 bpm) to Red (>90 bpm)

- **LF/HF Ratio Trend Chart** (`_build_lf_hf_trend_chart`):
  - Sympathovagal balance interpretation zones
  - Balance line (ratio = 1.0) reference
  - Age-adjusted typical range shading
  - Color coding: Blue (parasympathetic) → Red (sympathetic dominant)

- **Autonomic Indices Chart** (`_build_autonomic_indices_chart`):
  - Baevsky Stress Index with >150 threshold marker
  - Parasympathetic Index (PNS) on secondary axis
  - HRV Score composite tracking
  - Dual Y-axis for different scale metrics

- **lnRMSSD Athletic Monitoring Chart**:
  - Log-transformed RMSSD for recovery tracking
  - Coefficient of Variation (CV) calculation
  - Mean ± 1 SD band for baseline stability assessment
  - CV < 10% indicator for stable baseline

**Graduate-Level Physiological Interpretations (Expandable):**
- **RMSSD**: Vagal efferent tone, muscarinic receptor activation, RSA correlation
- **SDNN**: Total autonomic variability, cyclic components, mortality risk (Kleiger et al. 1987)
- **LF/HF Ratio**: Sympathovagal balance debate, baroreflex vs sympathetic interpretation
- **Heart Rate**: Intrinsic pacemaker rate, vagal brake, β-adrenergic modulation
- **Stress-Recovery**: Polyvagal theory (Porges 2007), allostatic load, training adaptation

**Summary Statistics with Clinical Interpretation:**
- Percentile position calculation (5th, 25th, 50th, 75th, 95th)
- Personal vs population mean comparison
- % of measurements within normal range
- Latest value interpretation ("below average", "above average", etc.)

### Scientific References (Newly Integrated)
- Umetani K et al. (1998). J Am Coll Cardiol 31(3):593-601 - Age-related HRV decline
- Kleiger RE et al. (1987). Am J Cardiol 59(4):256-262 - HRV mortality prediction
- Tanaka H et al. (2001). J Am Coll Cardiol 37(1):153-156 - Age-predicted max HR
- Porges SW (2007). Biol Psychol 74(2):116-143 - Polyvagal theory
- Thayer JF & Lane RD (2000). Neurosci Biobehav Rev 24(6):627-638 - Vagal tone model
- Billman GE (2013). Front Physiol 4:26 - LF/HF ratio critique
- Reyes del Paso GA et al. (2013). Biol Psychol 93(1):22-31 - LF component analysis
- Plews DJ et al. (2013). Int J Sports Physiol Perform 8(6):688-691 - HRV in athletes

### Design Principles Applied
- Nature Research Figure Guide compliance
- Colorblind-friendly palette (viridis-inspired)
- Clean typography with adequate whitespace
- Interactive exploration without compromising static readability
- Responsive design for various screen sizes
- SVG rendering support for publication export

## [1.8.85] - 2025-12-29

### Added
- **Publication-Quality HRV Visualizations** (`app/user_profile_tab.py`): Scientific-grade ECharts plots for Q1 journal publication:
  - **RMSSD Trend Visualization** with age-stratified normal ranges:
    - 5th-95th percentile shading (population normal range)
    - 25th-75th percentile markers (optimal range)
    - Population mean reference line
    - EWMA exponential smoothing trend
    - 7-day rolling average
    - Interactive pan/zoom with data picker
    - Age group label and scientific references
    - Summary statistics (% in normal range)
  - **RR Tachogram** with scientific annotations:
    - Color-coded RR intervals by physiological range (tachycardia/bradycardia)
    - Mean ± 1 SD reference lines
    - Statistical summary (mean, SD, HR, sample count)
    - LTTB downsampling for large datasets
    - Interactive crosshair tooltip
  - **Power Spectral Density** with frequency band analysis:
    - VLF (0.003-0.04 Hz), LF (0.04-0.15 Hz), HF (0.15-0.4 Hz) band shading
    - Band power values in legend (ms²)
    - LF/HF ratio and peak frequency annotations
    - Frequency band boundary markers
  - **RR Distribution Histogram** with statistical overlay:
    - Normal distribution fit overlay
    - Mean and median markers
    - Skewness and kurtosis values
    - Density normalization

- **Age-Stratified Normative Data** (`AGE_RMSSD_NORMS`):
  - Six age groups (18-25, 26-35, 36-45, 46-55, 56-65, 66+)
  - Mean, SD, and percentile values (p5, p25, p50, p75, p95)
  - Reference: Nunan et al. (2010), Shaffer & Ginsberg (2017), WHOOP population data

- **Scientific Color Palette** (`SCIENTIFIC_COLORS`):
  - Colorblind-friendly palette for accessibility
  - Consistent styling across all HRV visualizations

### Technical Details
- EWMA smoothing with configurable span (default: 7 days)
- Automatic age-based reference range lookup
- Interactive ECharts with data zoom/pan
- Responsive design for various screen sizes

### Scientific References
- Nunan D et al. (2010). PACE 33(11):1407-1417 - Short-term HRV normal values
- Shaffer F & Ginsberg JP (2017). Front Public Health 5:258 - HRV metrics overview
- Task Force (1996). Circulation 93(5):1043-65 - HRV measurement standards

## [1.8.84] - 2025-12-29

### Added
- **Polar H10 BLE RR Interval Recorder** (`app/polar_h10_recorder.py`): Real-time Bluetooth Low Energy connection to Polar H10 (and compatible) chest straps for HRV biofeedback and coherence training:
  - **Device Scanning**: Automatic discovery of BLE heart rate monitors (Polar H10/H9/OH1, Garmin HRM, Wahoo TICKR)
  - **RR Interval Recording**: Direct streaming of RR intervals via BLE Heart Rate Measurement characteristic (UUID: 0x2A37)
  - **File Format**: One RR interval (ms) per line, filename format: `YYYY-MM-DD HH-MM-SS.txt` (matches existing HRV analysis format)
  - **Real-Time Stats**: Live display of HR, RR interval, count, and duration during recording
  - **Battery Monitoring**: Device battery level display when available
  - **Session Management**: Async BLE operations with sync wrapper for Streamlit integration
  - **Output Directory**: Automatic directory creation based on user's full name (e.g., `Diego_Malpica/`)

- **BLE Recording UI** (`app/user_profile_tab.py`): New "📡 BLE Heart Rate Recording (Polar H10)" section in User Profile view:
  - **Available for both logged-in users and guests**
  - Scan for BLE devices with signal strength (RSSI)
  - Device selection dropdown with Polar devices prioritized
  - Connect/disconnect controls
  - Start/stop recording with live metrics
  - Recent recordings list with approximate RR counts
  - Guest recordings saved to `Guest/` directory

- **Dependencies**: Added `bleak>=0.21,<1.0` to `requirements.txt` for BLE communication

### Technical Details
- Follows Bluetooth SIG Heart Rate Service specification
- RR intervals are in 1/1024 second units, converted to milliseconds
- Validates RR intervals (200-2500 ms range, ~24-300 BPM)
- Parses HR format flags, energy expended, sensor contact status
- Thread-safe async wrapper for Streamlit's synchronous context

### Scientific References
- Bluetooth SIG Heart Rate Service Specification (UUID: 0x180D)
- Heart Rate Measurement Characteristic (UUID: 0x2A37)
- Schaffarczyk et al. (2022). RR interval accuracy of wearable sensors
- Schweizer & Gilgen-Ammann (2024). Polar H10 validation study

## [1.8.83] - 2025-12-28

### Added
- **Agentic Research Reports Module** (`app/agentic_reports.py`): Sophisticated AI-powered report generation using OpenAI's GPT-5.2 with full agentic capabilities:
  - **Graduate Level Report**: Comprehensive individual profile analysis with:
    - Executive summary with key findings
    - Subject profile (demographics, anthropometrics, fitness metrics)
    - Clinical assessment overview (ESS, Samn-Perelli, KSS, PSQI, FSS scales)
    - Body composition analysis with BMI interpretation
    - HRV analysis (time-domain, frequency-domain, nonlinear metrics)
    - Autonomic function assessment (parasympathetic index, stress markers)
    - Readiness and recovery status from Profile Tools Engine
    - Evidence-based clinical recommendations
    - APA-format citations from peer-reviewed literature
  - **Doctoral Level Report**: Comparative analysis following academic IMRaD structure:
    - Title page with abstract (Background, Methods, Results, Conclusions)
    - Introduction with research objectives and hypotheses
    - Methods with statistical analysis plan
    - Results with descriptive statistics, between-subject comparisons, effect sizes (Cohen's d, η²)
    - Discussion with literature comparison and clinical implications
    - Minimum 15 APA-format references
    - Suitable for peer-reviewed publication
  - **Agentic Capabilities**:
    - `code_interpreter`: Data analysis, statistical computations, visualization generation
    - `web_search`: Real-time literature search for evidence-based citations
    - `high reasoning effort`: Maximum analytical depth for doctoral-level interpretation
  - **Comprehensive Data Collection**: `collect_user_profile_data()` aggregates:
    - Demographics and fitness metrics
    - Clinical scales history
    - Medical history and body composition
    - HRV measurements with summary statistics
    - Sleep records and Garmin daily metrics
    - Profile Tools Engine results (recovery, readiness, fatigue)
  - **Graceful Degradation**: Local rule-based fallback reports when API unavailable

- **Agentic Reports UI** (`app/app.py`): New "📚 Agentic Research Reports" section in Export tab (under AI Tools):
  - Report type selector (Graduate vs Doctoral)
  - Comparison profile selector for Doctoral reports (multi-select from active sessions)
  - Generation status with timing and mode indicators
  - Preview text areas with expandable sections
  - Download buttons for markdown export

### Scientific References
- Task Force (1996). Circulation 93(5):1043-65 - HRV measurement standards
- Shaffer & Ginsberg (2017). Front Public Health 5:258 - HRV metrics and norms
- Nunan et al. (2010). PACE 33(11):1407-1417 - Short-term HRV normal values
- Plews et al. (2013). J Appl Physiol 114(6):736-745 - lnRMSSD recovery monitoring
- Kiviniemi et al. (2007). Eur J Appl Physiol 101(6):743-751 - HRV-guided training

## [1.8.82] - 2025-12-28

### Added
- **Advanced HRV Analytics Module** (`app/advanced_hrv_analytics.py`): State-of-the-art statistical analysis, ML pattern recognition, and clinical decision support:
  - **Descriptive Statistics**: N, Mean, SD, Median, Q1, Q3, IQR, Range, CV%, Skewness, Kurtosis, SEM
  - **Normality Tests**: Shapiro-Wilk test with p-values (Task Force 1996 standards)
  - **Comparison Tests**: One-sample t-test, paired t-test, Mann-Whitney U, Wilcoxon signed-rank with effect sizes (Cohen's d)
  - **Age-Stratified References**: RMSSD and SDNN reference values by age (Nunan et al. 2010, Shaffer 2017)
  - **Trend Analysis**: Linear regression with R², slope significance testing, 7-day forecasting with 95% CI
  - **Anomaly Detection**: Z-score and IQR methods for outlier identification
  - **Pattern Recognition**: Autonomic balance patterns, chronic stress detection, RMSSD variability analysis
  - **HRV + Garmin Integration**: Cross-correlation matrix, concordance scoring, integrated stress/recovery scores
  - **Clinical Decision Support**: Semaphored risk levels (Green/Yellow/Orange/Red), metric assessments, automated recommendations

- **Advanced HRV Analytics UI** (`app/user_profile_tab.py`): New "🧬 Advanced HRV Analytics" expander in HRV History:
  - **5-tab interface**: Clinical Decision, Statistical Tests, Trends & Forecast, Anomalies & Patterns, HRV + Garmin
  - **Autonomic Balance Gauge**: ECharts gauge showing balance score 0-100 with color-coded zones
  - **Metric Assessment Table**: Value, Z-score, Percentile, Reference Range, Risk Level, Interpretation
  - **Statistical Results Table**: Test name, Statistic, p-value (4 decimals), Effect Size, Significance
  - **Trend Visualization**: RMSSD trend with 7-day moving average
  - **Correlation Analysis**: HRV-Garmin cross-correlation with Spearman ρ and significance

### Scientific References
- Task Force (1996). Circulation 93(5):1043-65 - HRV measurement standards
- Shaffer & Ginsberg (2017). Front Public Health 5:258 - HRV overview
- Nunan et al. (2010). Scand J Med Sci Sports 20(1):e30-44 - RMSSD/SDNN reference values
- Thayer et al. (2012). Neurosci Biobehav Rev 36(2):747-56 - HRV-prefrontal cortex model
- Cohen (1988). Statistical Power Analysis - Effect size interpretation

## [1.8.81] - 2025-12-28

### Added
- **Advanced Wearable Analytics Module** (`app/wearable_analytics.py`): Sophisticated predictive modeling for Garmin metrics:
  - **Body Battery Forecasting**: Holt-Winters double exponential smoothing with 95% confidence intervals, recovery time estimation
  - **Allostatic Load Index**: Chronic stress assessment based on McEwen (1998) and Seeman (2001) - cardiovascular, autonomic, sleep, and energy components
  - **Circadian Rhythm Analysis**: Chronotype detection (Early Bird/Intermediate/Night Owl), peak performance hours, optimal sleep window
  - **Stress Prediction**: Next-day stress level forecasting with contributing factors and recommendations
  - **Recovery Analysis**: Recovery state classification, sleep debt calculation, optimal rest protocols
  - **Cross-Metric Correlations**: Pearson/Spearman correlations with significance testing

- **Advanced Predictive Analytics UI** (`app/user_profile_tab.py`): New "🧠 Advanced Predictive Analytics" section in Wrist Monitoring:
  - **5-tab interface**: Body Battery Forecast, Allostatic Load, Circadian Analysis, Stress Prediction, Recovery Status
  - **Body Battery forecast chart**: Historical + predicted values with confidence interval bands
  - **Allostatic load gauge**: 0-10 scale with component breakdown and recovery recommendations
  - **Chronotype profile**: Visual chronotype identification with optimal scheduling recommendations
  - **Stress prediction widget**: Risk level display with contributing factors
  - **Recovery dashboard**: Recovery score, sleep debt, days to full recovery estimation

### Improved
- **Radiation Exposure Gauge**: Simplified to clean arc + needle with status displayed below (no overlapping labels)
- **EVA Risk Matrix**: Larger chart (380px), bigger fonts, HTML legend below to avoid clutter

## [1.8.80] - 2025-12-28

### Added
- **Radiation Exposure Module** (`app/radiation_exposure.py`): New evidence-based module for space radiation dose estimation with:
  - **10 radiation environments**: Earth surface, Antarctica, flight altitude, LEO/ISS, Lunar Gateway, Lunar transit, Lunar surface (nominal + SPE), Mars transit, Mars surface
  - **Literature-derived dose rates**: Chang'E-4 LND (Zhang et al. 2020), MSL RAD (Zeitlin 2013, Hassler 2014), ISS MATROSHKA-R (Berger 2020)
  - **Day-by-day cumulative tracking**: `build_radiation_timeline()` with solar cycle phase adjustment and EVA schedule modeling
  - **EVA Go/No-Go assessment**: `assess_eva_radiation_risk()` with space weather integration (NOAA S/G scales)
  - **NASA STD-3001 limits**: Career 600 mSv, operational thresholds, alert zones (30/60/80% career)
  - **Environment comparison**: Side-by-side projected dose analysis across all environments

- **Enhanced Exploration Medical Analytics** (`app/user_profile_tab.py`): Complete overhaul of the Radiation Exposure section:
  - **4-tab interface**: Current Status, Day-by-Day Timeline, Environment Comparison, EVA Go/No-Go Matrix
  - **Radiation gauge**: Two-ring gauge visualization with career % and Go/No-Go status (styled like SAFTE gauges)
  - **Cumulative dose projection**: ECharts line chart with limit lines at 30%, 60%, 80%, 100% career
  - **Environment comparison bar chart**: All environments ranked by projected dose with color-coded risk levels
  - **EVA risk matrix**: Heatmap visualization similar to ICAO/USAF FRMS matrices with current position indicator
  - **Scientific references**: Inline citations to NASA STD-3001, ICRP 123, Zhang 2020, Simonsen 2025

### Fixed
- **Recording Timeline Summary** (`app/app.py`): Fixed issue where timeline showed "no RR intervals" despite data being loaded from user profiles. Now correctly merges data from:
  - `uploaded_rr_cache` (direct file uploads)
  - `_persisted_uploads` (persisted across reruns)
  - Current `uploads` variable (queued from profile storage)

## [1.8.79] - 2025-12-27

### Added
- **Enhanced Unified Timeline Tab** (`app/app.py`): Major overhaul of the Unified Timeline with:
  - **Recording Timeline Summary**: Table showing all uploaded RR files with their actual recording start times (extracted from filenames), duration, and mean HR. Timeline span displayed at bottom.
  - **Visual HR Trend Chart**: ECharts sparkline showing Mean HR trend across recordings with quick stats (average, range, CV%, trend direction).
  - **Isolation Forest Anomaly Detection**: Multivariate ML algorithm (Liu et al., 2008) for detecting unusual recordings based on multiple HRV metrics simultaneously. Includes configurable contamination rate, anomaly score display, and interpretive guidance.
  - **Anomaly Score Distribution Chart**: Bar chart visualization of anomaly scores with color-coded normal (green) vs anomaly (red) recordings.
  - **Garmin Wearable Triangulation**: Integration with Garmin daily metrics (Body Battery, Stress Score, Sleep Score, HRV RMSSD) for cross-validation with Polar H10 data. Includes 7-day rolling metrics with week-over-week comparisons.
  - **Statistical Summary Table**: Comprehensive descriptive statistics (N, Mean, SD, Median, CV%, IQR) for selected metrics with expandable interpretation guide.
  - **Graduate-Level Explanations**: Added peer-reviewed citations throughout (Liu 2008, Dalmeida 2021, Karasmanoglou 2023, Shaffer 2017, Task Force 1996, Plews 2013, Buitrago-Ricaurte 2025).

## [1.8.78] - 2025-12-27

### Fixed
- **Space Analytics Events Import** (`app/space_analytics_events.py`): Fixed import error for `logging_config` module by adding fallback import path. The module now works correctly when imported from both `app.app` and standalone contexts.
- **Nested Expander Error** (`app/app.py`): Fixed `StreamlitAPIException: Expanders may not be nested inside other expanders` by moving the "Understanding Windowed HRV Analysis" explanation expander outside the "Data status" expander.
- **Dataclass Module Registration** (`app/app.py`): Added safeguard to ensure module is registered in `sys.modules` before dataclass decorator runs. This prevents `AttributeError: 'NoneType' object has no attribute '__dict__'` when Streamlit reloads modules.
- **Space Analytics Nested Expander** (`app/app.py`): Fixed nested expander error in "Detected events" section by replacing `st.expander()` with `st.markdown()` heading for inline display.

### Added
- **Graduate-Level Space Analytics Explanations** (`app/app.py`): Added comprehensive scientific explanations with peer-reviewed citations throughout the Space Analytics tab:
  - **Scientific Foundation**: HRV-space weather hypothesis, evidence from Alabdulgader et al. (2018), Vencloviene et al. (2022), Papailiou et al. (2024), and methodological caveats from Mattoni et al. (2019)
  - **Windowed HRV Analysis**: Task Force 1996 guidelines, sliding window mathematics, Smith et al. (2013) 30-beat validation, window duration recommendations
  - **Event-Aligned Analysis**: Threshold-based event detection, baseline-event-recovery paradigm, Cohen's d effect sizes, statistical comparison methods
  - **Correlation Analysis**: Pearson r formula, Fisher Z-transformation for confidence intervals, temporal lag analysis theory, Olden & Neff (2001) cross-correlation bias, interpretation guidelines
  - **ML Suite**: ElasticNet (Zou & Hastie 2005), Random Forest (Breiman 2001, Qi 2012), Gradient Boosting (Friedman 2001, Chen & Guestrin 2016), feature importance methods, evaluation metrics, caveats for biological data

## [1.8.77] - 2025-12-27

### Added
- **Graduate-Level Space Data Explanations** (`app/app.py`): Added expandable scientific explanations below each major visualization in the Space Data tab:
  - **Kp Index**: Quasi-logarithmic geomagnetic disturbance scale, physiological relevance (HRV depression at Kp≥5), magnetoreceptor/melatonin mechanisms
  - **F10.7 Solar Radio Flux**: 10.7cm wavelength proxy for solar activity, EUV irradiance correlation, 11-year cycle context
  - **NASA DONKI**: Event catalog overview (FLR, CME, GST, SEP, IPS, RBE, HSS), WSA-ENLIL model predictions
  - **Impact Predictions**: Energy category travel times, NOAA G-Scale severity interpretation, Polar H10 monitoring strategy
  - **NOAA Space Weather Dashboard**: Data product descriptions (Kp, Dst, GOES flux, solar wind), scope options, HRV correlation guidance

## [1.8.76] - 2025-12-27

### Fixed
- **Space Weather Progress Display** (`app/app.py`): Fixed HTML rendering issue where progress tracker was displaying raw HTML tags instead of styled visual elements in Space Data tab. All three fetch operations (Impact Predictions, NASA DONKI, NOAA Space Weather) now use proper `st.status()` containers for HTML rendering:
  - Wrapped progress containers inside `st.status()` contexts (same pattern as HRV progress)
  - Added status container updates on completion/error states
  - Progress HTML now renders correctly with styled CSS elements

## [1.8.75] - 2025-12-27

### Added
- **Comprehensive Autonomic Function Tests Guide** (`docs/Manual.md`): Graduate-level step-by-step protocols for clinical autonomic reflex assessments with 14 peer-reviewed references:
  - **Deep Breathing Test (E:I Ratio)**: Respiratory sinus arrhythmia protocol, cardiovagal assessment, age-adjusted normal values
  - **Valsalva Maneuver**: Four-phase hemodynamic response, Phase II/IV analysis, ratio interpretation with age stratification
  - **30:15 Lying-to-Standing Ratio**: Orthostatic challenge protocol, beat identification, cardiovagal/adrenergic interpretation
  - **Isometric Handgrip Test**: MVC calculation, 30% sustained grip protocol, diastolic BP response criteria
  - **Orthostatic Blood Pressure Response**: Classical/initial/delayed OH classification, POTS criteria, tilt table protocols
  - **Ewing Composite Score**: 0-5 scoring system for autonomic dysfunction severity
  - Pre-test standardization requirements (fasting, caffeine, alcohol, temperature)
  - Physiological mechanisms with neuroanatomical pathways (NTS, RVLM, nucleus ambiguus)
  - Clinical application tables for diabetic neuropathy, Parkinson's, MSA, POTS, Long COVID
  - All references verifiable via PubMed IDs and DOIs

## [1.8.74] - 2025-12-27

### Added
- **Modern Readiness Dashboard** (`app/app.py`): Complete redesign of the Readiness tab inspired by Whoop, Oura, and Garmin recovery dashboards:
  - **Hero Recovery Gauge**: Large circular gauge (0-100%) with color-coded recovery status showing current readiness percentile
  - **Recovery Status Card**: Color-coded status card with category (VERY LOW/LOW/NORMAL/HIGH), contextual emoji, and personalized recommendation text
  - **Mini Metrics Cards**: PNS Index, Z-Score, and Baseline sample count in compact card format
  - **Recovery Trend Chart**: 14-session sparkline with gradient fill, showing PNS history with baseline thresholds (Very Low, Mean, High) as reference lines, plus min/max markers
  - **Recovery Breakdown Section**:
    - Radar chart showing baseline statistics (Mean PNS, Consistency, Sample Size, Current vs Mean)
    - Donut chart showing historical distribution across VERY LOW/LOW/NORMAL/HIGH categories
  - **Training Recommendation Cards**: 4-column cards showing Intensity, Volume, Suggested Activities, and What to Avoid based on current recovery category
  - **Detailed Baseline Statistics**: Expandable table with full baseline metrics (mean, std, cuts, z-score)
  - Color theming: Red (#F44336) for VERY LOW, Orange (#FF9800) for LOW, Green (#4CAF50) for NORMAL, Blue (#2196F3) for HIGH

### Fixed
- **Python 3.12 Dataclass Compatibility** (`app/app.py`): Removed `slots=True` from `UploadedRR` dataclass to fix `AttributeError: 'NoneType' object has no attribute '__dict__'` when using `from __future__ import annotations` with `@dataclass(slots=True)` in Python 3.12
- **SD1/SD2 Color Zone Logic** (`app/app.py`): Fixed missing upper bound checks in `_sd1_color` and `_sd2_color` variables that caused incorrect color assignments:
  - **SD1**: Values >70 ms now correctly show orange (previously incorrectly showed green for any value ≥30)
  - **SD2**: Values >140 ms now correctly show orange (previously incorrectly showed green for any value ≥60)
  - Updated interpretation messages to match the 4-zone color scheme (low/reduced/optimal/very high)
- **JSON Serialization Safety** (`app/app.py`): Added explicit `float()` conversions for Poincaré metrics and `int(round(..., 0))` wrappers to prevent "Object of type function is not JSON serializable" errors

## [1.8.73] - 2025-12-27

### Added
- **Enhanced Nonlinear Analysis Tab Gauges** (`app/app.py`): Added professional gauges matching Time Series tab style for all Poincaré and nonlinear metrics:
  - **SD1 Gauge**: Short-term variability (vagal modulation) with color zones: <20ms red, 20-30ms orange, 30-70ms green, >70ms orange
  - **SD2 Gauge**: Long-term variability with zones: <40ms red, 40-60ms orange, 60-140ms green, >140ms orange
  - **SD1/SD2 Balance Gauge**: Autonomic balance ratio with zones: <0.35 red (sympathetic), 0.35-0.5 orange, 0.5-0.8 green (balanced), >0.8 orange (vagal)
  - **Ellipse Area Gauge**: Complexity index (π×SD1×SD2) with zones: <2000ms² red, 2000-4000ms² orange, >4000ms² green
  - **DFA α1 Gauge**: Fractal scaling exponent with zones: <0.5 red, 0.5-0.75 orange, 0.75-1.25 green (optimal), 1.25-1.4 orange, >1.4 red
  - **Sample Entropy Gauge**: Signal complexity with zones: <0.5 red, 0.5-1.0 orange, 1.0-2.0 green, 2.0-2.5 orange, >2.5 red
  - Each gauge includes instant interpretation feedback (✅/⚠️/🔴) explaining the physiological significance
  - Summary metrics cards row at bottom showing SD1, SD2, SD1/SD2, and Ellipse Area

## [1.8.72] - 2025-12-27

### Changed
- **SAFTE Sleep Efficiency Metric** (`app/app.py`, `app/fatigue_integration.py`): `sleep_score` is now used as the primary "efficiency" metric for SAFTE fatigue calculations instead of raw `sleep_efficiency`:
  - `sleep_score` (0-100) is a composite Garmin metric that incorporates sleep stages, disturbances, and overall restorative quality — better proxy for SAFTE sleep effectiveness than simple TST/TIB ratio
  - Falls back to `sleep_efficiency` only if `sleep_score` is unavailable
  - Wrist monitoring summary now displays `sleep_score (efficiency)` with explanatory caption
  - Both `app.py` and `fatigue_integration.py` now use consistent priority ordering

## [1.8.71] - 2025-12-27

### Added
- **Enhanced Spectrogram (Time-Frequency) Tab** (`app/app.py`): Comprehensive scientific explanations with peer-reviewed citations:
  - **Physiological Interpretation Guide**: Detailed explanation of what the spectrogram shows — axes meaning, color intensity, frequency bands (VLF/LF/HF)
  - **Key Patterns to Recognize**: Respiratory ridge in HF band, LF bursts (baroreflex/sympathetic), power dropouts, frequency drift
  - **Wavelet vs. STFT Comparison**: Strengths and limitations of each method for time-frequency analysis
  - **Clinical & Research Applications**: Exercise onset/offset studies, sleep stage analysis, mental stress detection, orthostatic challenge, arrhythmia localization
  - **References**: de Boer & Karemaker (2019), Oliver et al. (2023), Pichot et al. (2016), Hayano & Yuda (2019), Botek et al. (2014)

- **Enhanced Windowed Metrics Tab** (`app/app.py`): Scientific explanations for sliding window HRV analysis:
  - **Why Use Sliding Windows**: Explanation of how windowed analysis reveals trends, episodes, and anomalies invisible in whole-recording averages
  - **Window Parameters Explained**: Window length, step size, overlap with typical values and effects
  - **The 5-Minute Standard**: Task Force (1996) guidelines and the science behind minimum recording duration
  - **Ultra-Short-Term HRV Validity**: Evidence summary from Schroeder et al. (2004), Munoz et al. (2015), Chen et al. (2020), Chapman et al. (2025)
  - **Deviation Detection & Episode Identification**: Statistical thresholds (Normal/Warning/Alert), episode grouping, clinical applications
  - **References**: Task Force (1996), Schroeder et al. (2004), Chen et al. (2020), Chapman et al. (2025), Plews et al. (2013)

- **Enhanced Readiness Tab** (`app/app.py`): Comprehensive HRV-based readiness assessment science:
  - **Physiological Basis**: Why HRV reflects readiness — vagal withdrawal as stress response, recovery requiring vagal restoration, morning HRV capturing overnight recovery
  - **The "Vagal Rebound" Phenomenon**: Recovery patterns (full, partial, incomplete, supercompensation) with training implications
  - **HRV-Guided Training Evidence**: Studies from Kiviniemi et al. (2007), Plews et al. (2013), Botek et al. (2014), Alfonso et al. (2025)
  - **Practical Training Rules**: When HRV is HIGH/NORMAL/LOW/VERY LOW with specific action recommendations
  - **Limitations & Pitfalls**: Single-day interpretation, breathing rate effects, hydration/alcohol, illness prodrome, measurement conditions
  - **References**: Plews et al. (2013), Botek et al. (2014), Alfonso et al. (2025), Thayer et al. (2012), Kiviniemi et al. (2007)

- **Enhanced Gauges Tab** (`app/app.py`): Comprehensive normative data and reference range explanations:
  - **Where Reference Ranges Come From**: Factors affecting HRV (age, sex, fitness, recording conditions), key normative studies
  - **Reference Ranges Table**: Poor/Borderline/Normal/Good/Excellent cutoffs for SDNN, RMSSD, pNN50, LF/HF power
  - **Age-Adjusted Interpretation**: Age-specific RMSSD percentiles (20-70+ years) from Nunan et al. (2010) and Ortega et al. (2024)
  - **Common Misinterpretations**: "Higher is always better" myth, LF/HF ratio limitations, single-reading pitfalls
  - **References**: Nunan et al. (2010), Sammito & Böckelmann (2016), Ziegler et al. (1999), Ortega et al. (2024), Billman (2013), Koenig & Thayer (2016)

- **Enhanced Unified Timeline Tab** (`app/app.py`): Multi-metric physiological integration science:
  - **Why Integrate Multiple Metrics**: Limitation of single-metric analysis, autonomic system integration across domains
  - **Physiological Coupling Principles**: RMSSD↔HR relationships, HRV↔SpO2 coupling, circadian patterns
  - **Circadian Patterns Table**: Expected HR/RMSSD/LF-HF patterns by time of day with physiological explanations
  - **Pattern Recognition & Anomaly Detection**: Statistical methods (Z-score, MAD, IQR, rolling window), interpreting flagged anomalies
  - **Practical Applications**: Overtraining detection, sleep quality assessment, stress load monitoring, recovery tracking, pre-competition tapering
  - **References**: Buitrago-Ricaurte et al. (2025), Rasouli et al. (2025), Weinschenk et al. (2025), Lee et al. (2025), To et al. (2025), Shaffer & Ginsberg (2017)

## [1.8.70] - 2025-12-27

### Added
- **Enhanced Time Series Analysis Tab** (`app/app.py`): Comprehensive improvements for graduate-level physiology education:
  - **Improved Gauge Visualizations**: Two side-by-side gauges for Median Heart Rate and RR Variability Spread with better spacing, clearer tick marks, and color-coded zones
  - **Instant Interpretation Feedback**: Color-coded success/warning/error messages below each gauge explaining the physiological significance of values
  - **RR Percentile Bar Chart**: Visual representation of p25/p50/p75 RR interval distribution
  - **Summary Metrics Row**: Quick-view metrics cards showing Median HR, HR IQR, and RR Spread
  - **Scientific Explanation Section**: Detailed physiological interpretation of time-domain metrics:
    - What HRV means and why it matters
    - RR interval vs Heart Rate relationship
    - What upward/downward deflections in the time series indicate
    - Why higher variability is generally healthier
  - **Age-Stratified Normal Ranges**: Reference tables by age decade for resting HR and HRV metrics (SDNN, RMSSD, RR Spread) based on Umetani et al. (1998) and Choi et al. (2020)
  - **Clinical Significance Section**: Post-MI mortality risk, overtraining detection, and multi-system implications (diabetes, obesity, depression, sleep apnea)
  - **Evidence-Based Improvement Strategies**: Five validated interventions with protocols:
    - Aerobic exercise training (Sandercock et al., 2005)
    - Slow breathing / resonance frequency training (Lehrer & Gevirtz, 2014)
    - Sleep optimization (Tobaldini et al., 2013)
    - Stress management (Thayer et al., 2012)
    - Nutrition & hydration (Christensen et al., 1999)
  - **Validated References Section**: 8 peer-reviewed citations with DOIs and PMIDs for verification

### Fixed
- **HRV Progress Tracker Rendering**: Fixed issue where progress tracker HTML was displaying as raw text instead of styled visual elements. The fix ensures:
  - `_hrv_progress_container` is created inside `with _status_container:` context
  - All 15 `render_hrv_progress()` calls are wrapped in `with _status_container:` to ensure proper rendering within the status container context
  - This follows Streamlit's container context management pattern where containers created inside a context manager should be updated within that same context

## [1.8.69] - 2025-12-27

### Added
- **Enhanced Frequency Domain Analysis Education** (`app/app.py`): Comprehensive physiological explanations for postgraduate students in the Frequency tab:
  - **PSD Plot Interpretation Guide**: Detailed explanation of axes, frequency bands (VLF/LF/HF), and what the plot shape tells you physiologically
  - **Age-Stratified Normative Values**: Reference tables showing LF/HF power by age group (20-70+ years) with citations (Nunan et al., 2010; Shaffer & Ginsberg, 2017)
  - **Clinical Significance Section**: When values are abnormal and associated conditions (heart failure, diabetes, depression, chronic stress)
  - **Evidence-Based Improvement Strategies**: Science-backed interventions to improve HRV metrics with peer-reviewed citations:
    - Slow-paced breathing (resonance frequency breathing) with protocol
    - Aerobic exercise training
    - Mindfulness meditation & yoga
    - Sleep optimization
    - Cold water face immersion (dive reflex)
  - **Common Misconceptions**: Clarification that LF/HF ratio is NOT a simple sympathetic/parasympathetic balance index

- **New ECharts Visualizations for Frequency Metrics** (`app/app.py`):
  - **Stacked Bar Chart**: Compares VLF/LF/HF absolute power across recordings with tooltips showing total power
  - **Pie Chart**: Normalized power distribution (LFnu vs HFnu) with donut style
  - **LF/HF Ratio Gauge**: Color-coded gauge (green→red) indicating autonomic balance state
  - **Automated Interpretation**: Personalized feedback on HF power, LF/HF ratio, and total power with actionable recommendations

## [1.8.68] - 2025-12-27

### Added
- **Tab Persistence Across Reruns** (`app/app.py`): Active tab is now preserved when clicking compute/analyze buttons or triggering other reruns. The app stays on the current tab instead of automatically returning to Overview, improving workflow continuity during analysis.

- **Modern HRV Progress Tracker** (`app/hrv_progress.py`): New module providing detailed, real-time progress tracking for all HRV computations. Features include:
  - **Visual step-by-step progress** with animated status indicators (pending, running, complete, error)
  - **Live elapsed time tracking** per step and per sub-step
  - **Progress bar** showing overall completion percentage
  - **Detailed sub-step messages** for each computation phase
  - **Modern dark-themed UI** with CSS animations matching Space Weather progress style
  - **Pre-configured 9-step workflow**: Validate RR → Artifact Detection → Artifact Correction → Windowed Metrics → Full-Recording Metrics → DFA Analysis → Frequency Analysis → ML Clustering → Episode Detection

- **Enhanced HRV Interpretation Module** (`app/hrv_interpretation.py`): New module providing context-aware, informed interpretations for HRV metrics with clinical and physiological context.

- **New HRV Metrics** (`app/hrv_core.py`): Added scientifically-validated metrics based on literature review:
  - **LnRMSSD**: Natural logarithm of RMSSD for better statistical properties (Buchheit 2014)
  - **CVI (Cardiac Vagal Index)**: ln(SD1²) for parasympathetic assessment (Toichi 1997)
  - **CSI (Cardiac Sympathetic Index)**: SD2/SD1 ratio for sympathovagal balance (Toichi 1997)
  - **Mean HRmax-HRmin**: Heart rate range metric for autonomic reactivity
  - **Generalized pNNx**: Configurable threshold (10ms, 30ms, 50ms) for pNN calculations
  - **SDANN**: Standard deviation of 5-min mean NNI for long-term variability (24h recordings)
  - **SDNNi**: Mean of 5-min SDNN values for short-term variability within segments
  - **Enhanced TINN**: More robust triangular interpolation algorithm

- **New Gauge Configurations** (`app/gauge_builder.py`): Added informed thresholds for all new metrics with clinical reference ranges and interpretations.

### Changed
- **HRV Processing now shows real-time progress** (`app/app.py`): All HRV computations (cleaning, windowed, full-recording, ML, episode detection) now display a detailed progress panel showing which step is active, elapsed time, and completion percentage.
- **Time-Series tab now shows computation progress** (`app/app.py`): Individual metric computations display their status during processing.
- **Frequency tab now shows analysis progress** (`app/app.py`): PSD and spectral analysis steps show real-time progress.

### Fixed
- **HRV computations no longer appear to hang** (`app/app.py`): The new progress indicators provide continuous feedback during computations, preventing the "blank page" experience during long analyses.

## [1.8.67] - 2025-12-27

### Added
- **Modern Space Weather Progress Indicators** (`app/space_weather_progress.py`): New module providing detailed, real-time progress tracking for all space weather fetch operations. Features include:
  - **Visual step-by-step progress** with animated status indicators (pending, running, complete, error, timeout)
  - **Live elapsed time tracking** per operation and per step
  - **Progress bar** showing overall completion percentage
  - **Error details** displayed inline with each step
  - **Modern dark-themed UI** with CSS animations for a professional appearance
  - **Pre-configured trackers** for Impact Predictions, NASA DONKI, and NOAA Space Weather operations

### Changed
- **Impact Predictions fetch now shows real-time progress** (`app/app.py`, `app/space_weather_impact.py`): Clicking "Fetch Prediction" now displays a detailed progress panel showing the status of each data source (X-ray, SEP, Plasma, CME, Geomagnetic) as they complete in parallel.
- **NASA DONKI fetch now shows step-by-step progress** (`app/app.py`): Each DONKI endpoint (CME, Flares, GST, etc.) displays its fetch status, timing, and any errors in real-time.
- **NOAA Space Weather fetch now shows granular progress** (`app/app.py`): The SWPC Kp/F10.7 fetch and each NOAA dataset fetch are tracked individually with live status updates.

### Fixed
- **Space weather operations no longer appear to hang** (`app/app.py`): The new progress indicators provide continuous feedback during network operations, preventing the "blank page" experience when fetching data takes longer than expected. Users can now see exactly which data source is being fetched and how long each operation takes.

## [1.8.66] - 2025-12-27

### Added
- **Space Data step log (debug)** (`app/app.py`): Added a **📋 Space Data step log** expander that records Space Data fetch steps with duration + error text so freezes/hangs can be attributed to a specific source.

### Changed
- **Metrics tab UI cleanup** (`app/app.py`, `app/app-Starflight.py`): Removed the “🔍 AI metric explanations” banner from the Metrics page.
- **Space Data copy cleanup** (`app/app.py`, `app/app-Starflight.py`): Removed “click fetch” guidance text and the disabled correlations notice from the Space Weather section to keep the dashboard visually clean.
- **Space Data top-of-page organization** (`app/app.py`): Added a **🚀 Quick actions** bar in the requested order (**Fetch Prediction → Fetch NASA DONKI → Fetch NOAA Space Weather**) and introduced a **Dashboard** section header directly below for the gauges/plots/explanations.
- **Space Data NOAA UI cleanup** (`app/app.py`): Removed the “Correlations (decommissioned)” notice from the NOAA section of Space Data.

### Fixed
- **Impact Predictions are now debuggable step-by-step** (`app/app.py`): Added a **🧪 Step-by-step (debug hangs)** expander with one button per Impact Predictions sub-step (X-rays, protons, solar wind, CME/ENLIL, Kp/Dst), persists per-step status + duration, and rebuilds the snapshot from the latest step results.
- **Impact step buttons no longer freeze/reset the session** (`app/app.py`): Step-by-step sub-steps now run with a hard per-step timeout so a stalled network/DNS call can’t block the Streamlit UI long enough to disconnect and “jump back” to the Overview tab.
- **Space Data no longer uses OpenAI for SpaceWeatherLive** (`app/app.py`): Removed the OpenAI-based SpaceWeatherLive fallback path so Space Data fetch is scrape-only (plus NOAA SWPC/NOAA/DONKI), per user preference.

## [1.8.60] - 2025-12-25

### Fixed
- **Space Data/Space Weather decommissioned code no longer renders** (`app/app.py`): Removed accidental Streamlit “magic” rendering of a decommissioned HRV↔Kp/ML block by converting the leftover triple-quoted block into a non-rendered assignment. Space Data stays **data-only**; correlations/ML live in **🔬 Space Analytics**.
- **Impact Predictions fetch no longer hangs indefinitely** (`app/space_weather_impact.py`): Added a hard overall timeout and non-blocking shutdown so “Fetch Impact Predictions” returns promptly even if one source stalls at DNS/TLS level; surfaces per-source timeout errors instead of freezing the UI.

## [1.8.65] - 2025-12-26

### Fixed
- **Space Data no longer feels like it “restarts” while exploring** (`app/app.py`): Wrapped Space Data fetch/scope/view controls in `st.form()` blocks (SWPC, DONKI, NOAA dashboard) and disabled stale-element dimming to reduce rerun flicker on Windows/OneDrive.
- **Impact Predictions SEP accuracy** (`app/space_weather_impact.py`): SEP classification now explicitly uses the **GOES integral proton flux ≥10 MeV** channel (NOAA S-scale) instead of accidentally grabbing another energy bin (e.g., ≥50/≥100 MeV).
- **Impact Predictions geomagnetic severity mapping** (`app/space_weather_impact.py`): Corrected NOAA G-scale mapping (**Kp 5–9 → G1–G5**) so storm severity labels match official thresholds.

### Added
- **HRV-informed influence horizons for Space Data** (`app/app.py`, `app/space_weather_influence.py`): When an RR timeline is available, the app auto-seeds conservative default padding for DONKI (days) and SWPC/NOAA RR-sync padding (hours) using a drag-based CME transit-time estimate.
- **DONKI CME influence windows + phase correlations in Space Analytics** (`app/app.py`, `app/space_weather_influence.py`, `tests/test_space_weather_influence.py`): Space Analytics event-aligned analysis can now build CME arrival/influence windows from DONKI CMEAnalysis speeds and compute baseline/event/recovery correlations vs Kp/Dst within those windows.
- **CME/shock arrival forecasts in Impact Predictions** (`app/space_weather_impact.py`, `app/app.py`): Added NASA DONKI **WSA+ENLIL** `estimatedShockArrivalTime` forecasts (with Kp scenario range + DBM cross-check using the correct **21.5 R☉ → 1 AU** propagation distance when `time21_5` is provided) and surfaced **confidence** in the summary table and event cards; added an in-app “Method & Accuracy” explainer.
- **Custom UI palette applied to Flight Surgeon + Overview boxes** (`app/welcome_header.py`, `app/app.py`): Applied the neutral palette (`#F2F1EF/#D8CFD0/#B1A6A4/#697184/#413F3D`) to custom HTML banners/cards on the Flight Surgeon header and the Overview page (without changing Streamlit’s default theme).
- **Entrypoint compatibility wrapper** (`app/app-Starflight.py`): Running older/alternate filenames now delegates to the canonical Research UI (`app/app.py` via `app/research_app.py`) so behavior stays consistent across machines.

## [1.8.64] - 2025-12-26

### Fixed
- **Space Analytics no longer “fades” or feels like it restarts when you change configuration** (`app/app.py`): Wrapped Space Analytics window/correlation/ML controls in `st.form()` to prevent reruns while editing, removed extra `st.rerun()` refreshes after actions, and disabled Streamlit stale-element dimming so long computations keep the page visually stable.

## [1.8.61] - 2025-12-26

### Fixed
- **Space Analytics no longer feels “dead” when prerequisites are missing** (`app/app.py`, `docs/Manual.md`): Added explicit prerequisite diagnostics (recording duration vs window size, NOAA errors), fixed misleading success messages on NOAA cache/fetch buttons, added a button-driven **Compute windows** tool (with overrides) to generate windowed HRV/HRF metrics, and improved ML preflight messaging (requires ≥30 usable windows).

## [1.8.62] - 2025-12-26

### Fixed
- **Space Weather / NOAA dashboards can be RR-synced and stay responsive** (`app/app.py`, `app/noaa_space.py`): Added optional **RR timeline syncing** for SWPC plots (Kp/F10.7), NOAA feed history windows, and DONKI date queries (with bounded padding + hard max window) to prevent accidental “download/plot everything” behavior that can make the Space Weather tab feel like it’s hanging.

## [1.8.63] - 2025-12-26

### Changed
- **Space Analytics runs without page fading** (`app/app.py`): Replaced long-running `st.spinner(...)` blocks in Space Analytics actions (NOAA fetch/refresh, window build, correlation scan, ML feature-matrix + training) with an always-visible **🧾 Computation Console** that streams detailed step-by-step logs inside a framed code box while the page remains fully visible.

## [1.8.59] - 2025-12-25

### Added
- **Space Analytics recovery + onset sequencing (prototype)** (`app/app.py`, `app/space_analytics_events.py`, `docs/Manual.md`): Extended event-aligned analysis to optionally compute **recovery-phase** deltas and added **button-driven onset detection** (first sustained deviation vs baseline) to explore whether HRV or HRF metrics tend to change first during an event.

## [1.8.58] - 2025-12-25

### Added
- **Space Analytics event-aligned analysis (prototype)** (`app/app.py`, `app/space_analytics_events.py`, `docs/Manual.md`): Added threshold-based event detection (Kp/Dst) with explicit start/end and an on-demand **baseline vs event delta table** for HRV/HRF targets to identify which physiology metrics shift during a space-weather event.

## [1.8.57] - 2025-12-25

### Changed
- **Heart Rate Fragmentation (HRF) documentation** (`app/app.py`, `docs/Manual.md`): Expanded the in-app HRF explanations with clear **medical/physiology meaning**, **operational interpretation**, and practical factors that can increase/decrease HRF. Added peer-reviewed citations (Costa 2017; Hayano 2020; Guichard 2025 PROOF‑AF) to the UI and manual.

## [1.8.56] - 2025-12-25

### Fixed
- **Export tab responsiveness** (`app/app.py`): Prevented heavy, unrequested work on reruns by making **markdown report generation** explicitly button-driven (session-cached) and by requiring an explicit **Prepare HRV export files** click before serializing large windowed data to CSV/JSON.
- **Science tab responsiveness** (`app/app.py`): Replaced the always-rendered full “Scientific Reference Guide” expanders with a **fast section picker** so the Research app stays responsive while switching tabs (Streamlit tabs are not lazy).

## [1.8.55] - 2025-12-25

### Fixed
- **Space Data tab “fade” rerun loops** (`.streamlit/config.toml`, `app/app.py`): Disabled Streamlit’s file watcher (`server.fileWatcherType = "none"`) to prevent unrequested reruns triggered by runtime cache/log writes (common on Windows/OneDrive). Also removed an unnecessary `st.rerun()` from the Space Data “Clear fetched feed” action to avoid extra flicker.
- **References tab loads reliably** (`app/app.py`): Removed legacy DONKI/correlation/feature-matrix logic that was incorrectly embedded in the **📚 References** tab and could trigger slow/failed renders. References now remain lightweight and point users to **🌐 Space Data** and **🔬 Space Analytics** for data and analysis.
- **About tab full renderer no longer mis-detects docs as errors** (`app/about_tab.py`): Replaced the fragile “contains the word ‘error’” heuristic with structured file-load status so `docs/Manual.md` and `CHANGELOG.md` previews render reliably.

### Changed
- **Streamlit config cleanup** (`.streamlit/config.toml`): Removed deprecated/invalid options (Streamlit 1.36.0) to eliminate startup warnings.

## [1.8.54] - 2025-12-25

### Added
- **Space Analytics tab (Correlations + ML)** (`app/app.py`): Added **🔬 Space Analytics** — an on-demand workspace to correlate NOAA predictors against **HRV + HRF** windowed metrics and train ML models from lagged space-data features. All analyses are **button-driven** and results persist in session state.
- **HRF↔HRV pairwise stats table** (`app/app.py`): The **🧩 HRF ↔ HRV** tab now includes a per-pair statistical summary table (test, result, p-value, meaning) with p-values formatted to **4 decimals**.

### Changed
- **GPU-aware boosting** (`app/app.py`): When GPU processing is enabled, XGBoost and LightGBM models now attempt GPU acceleration (safe CPU fallback on unsupported builds).
- **Unified Space Data tab (data-only)** (`app/app.py`): Space Data remains a stable, data-only dashboard for SWPC + NOAA + DONKI fetch/visualization. Correlation/ML workflows live in **🔬 Space Analytics**.
- **GPT-5.2 report interpretation includes Space Analytics results** (`app/app.py`, `app/gpt_interpretation.py`, `app/export_utils.py`): Export report generation now passes Space Analytics correlation/ML outputs into the **GPT‑5.2 high reasoning** payload and renders a bounded Space Analytics section in the markdown report when available.
- **Documented app-mode separation** (`docs/Manual.md`, `WARP.md`): Operational app is the crew-facing intake/mission workflow; Research app is the core statistics/analytics workspace.

### Fixed
- **Research app entrypoint loads the full UI reliably** (`app/research_app.py`): Hardened import path setup so `streamlit run app/research_app.py` always launches `app/app.py` (and therefore exposes Space Data/Space Analytics tabs) regardless of Streamlit/sys.path ordering.

## [1.8.52] - 2025-12-25

### Added
- **Dedicated HRF ↔ HRV tab** (`app/app.py`): Added **🧩 HRF ↔ HRV** — an offline workspace for heart-rate fragmentation (HRF) gauges and per-recording HRF↔HRV correlation matrices/scatter plots, intentionally decoupled from NOAA/SWPC/DONKI fetch pipelines.

### Fixed
- **Space Weather correlations persist across tab switches** (`app/app.py`): HRV↔Kp correlation outputs are now cached in session state and re-displayed when returning to the Space Weather tab, preventing “compute → switch tab → reset” behavior. Added a **Run HRV window analysis** CTA when windowed metrics are missing and stabilized Space Weather correlation widgets with explicit keys.
- **Heart-rate fragmentation metrics available in fast workflows** (`app/hrv_core.py`): HRF metrics (PIP/IALS/PSS and PROOF‑AF-derived PIP_H/PIP_S/PAS/W0–W3) are now computed regardless of the `include_advanced` flag, so fragmentation metrics are available for windowed and per-recording analyses without requiring “high compute” mode.

## [1.8.51] - 2025-12-24

### Added
- **NOAA correlation CTAs** (`app/app.py`): Added inline buttons beside the NOAA correlation callouts to trigger HRV window analysis when windowed metrics are missing, so users can start correlations and batch scans directly from the NOAA tab.
- **On-demand metric correlations** (`app/app.py`): The physiology correlation matrix now runs only when you click **Run correlations**, preventing any automatic correlation/analysis on render.
- **User-facing on-demand notices** (`app/app.py`): Added explicit “click to run” info and spinners for NOAA correlations, batch NOAA scans, and the physiology correlation matrix so users see a clear warning that computations may take time.
- **Instant Space Weather/NOAA tabs** (`app/app.py`): Removed automatic cache loads; both tabs now render immediately and only load cached or fresh data when you click **Load cached copy/NOAA** or **Fetch**, with spinners and success messaging. This keeps the UI responsive even with no HRV data.
- **About tab performance fix** (`app/app.py`, `app/about_tab.py`): About now defaults to a lightweight preview (instant), with optional buttons to load the full page/manual/changelog on demand to avoid long UI hangs.

### Changed
- **Moved inline HRV “Key References” list** (`app/app.py`): Removed non-APA inline reference links from the Circadian tab area; references are consolidated in the **📚 References** tab (APA 7 format).
- **NOAA Space tab reliability** (`app/app.py`, `app/noaa_space.py`, `app/user_profile_tab.py`): Fixed cache-load handling for “Full” scope, prevented Clinical Assessments from triggering NOAA network fetches, and added a hard overall fetch timeout so NOAA downloads can’t hang indefinitely.
- **Space Weather tab reliability** (`app/app.py`): Prevented “Fetch space weather” from hanging due to executor shutdown waiting on stuck network threads; added cache-only auto-bootstrap so the tab renders immediately without any network calls.
- **Logout reliability** (`app/user_profile_tab.py`, `app/app.py`): Logout is now executed via `on_click` callback (runs before rerender), preventing long “logout hangs”; and the `user_logged_out` flag is no longer accidentally cleared by unrelated flows.
- **Logout hardening across modules** (`app/app.py`, `app/user_management_ui.py`, `app/sleep_tab.py`): All logout buttons now use unique keys; `user_management_ui` logout sets the global `user_logged_out` flag; and `app.py` enforces a hard logout guard that clears any restored profile when logged out.
- **Disabled default auto-profile selection** (`app/app.py`): The app no longer silently auto-selects the author/single profile when none is set (this made logout appear broken). You can re-enable for demos via `HRV_AUTO_SELECT_DEFAULT_PROFILE=1`.

### Fixed
- **Wrist Monitoring refresh + Garmin Connect integrity** (`app/user_profile_tab.py`, `app/garmin_connect_service.py`): Wrist Monitoring history now refreshes immediately after Garmin sync/import (token-based cache bust + Refresh button, no forced rerun). Garmin Connect fetch no longer reports success while returning all-null placeholder rows, and daily field extraction is more robust for Vivosmart 5 exports.
- **Research app login reliability** (`app/user_profile_tab.py`): User selection login now uses stable widget keys + a pre-rerun `on_click` handler, and surfaces a clear error when the selected profile cannot be loaded. This fixes “login user does not work” in `app/research_app.py` (research mode).

## [1.8.50] - 2025-12-23

### Fixed
- **HRV data survives WebSocket reconnects** (`app/app.py`): Added unconditional cache restoration at the start of `main()` so that `windowed_df`, `multi_results_df`, `meta_rows`, `ml_summary_df`, and `episodes_df` are always restored from session state on every script rerun. This ensures NOAA Space correlations, ML, and plots work correctly even after browser disconnects/reconnects.
- **NOAA Space correlations and ML now display properly** (`app/app.py`): The correlation and batch ML sections no longer show "Run the HRV window analysis to enable…" after HRV analysis is completed; the cached results are now reliably available across tab switches and page scrolls.
- **Red warning box placed directly below Mode badge** (`app/app.py`): Moved the "Heavy Computations" warning to render immediately after the Mode: Research badge at the top of the page, with matching purple/red styling.

### Changed
- **Removed redundant cache rehydration code** (`app/app.py`): The late-stage rehydration block (added in 1.8.49) was replaced by the more robust unconditional restoration at variable initialization, simplifying the code flow.
- **Removed misplaced tab disclaimers** (`app/app.py`): Removed the inline red disclaimer messages from inside Space Weather and NOAA Space tabs since the warning is now prominently placed at the top.

## [1.8.49] - 2025-12-23

### Fixed
- **Space Weather loads fast (no hidden network fetches)** (`app/app.py`): Removed the automatic SWPC Kp download that was triggered during correlation UI rendering; Kp now loads from cache-only and requires an explicit user fetch to refresh.

### Changed
- **NOAA Space “Today (fast)” mode** (`app/app.py`): Added a fast default scope that loads only Kp + F10.7 for instant context; Core/Full remain available on demand.
- **Cache-only bootstrap for Space Weather + NOAA Space** (`app/app.py`, `app/noaa_space.py`): Tabs now show the last cached copy immediately without hitting the network.
- **Background prefetch now optional (default OFF)** (`app/app.py`): Background 12h refresh is no longer automatic; it’s a user toggle to avoid slow startup/CPU contention on Windows/OneDrive setups.

## [1.8.48] - 2025-12-23

### Fixed
- **Space Weather tab reliably renders** (`app/app.py`): Removed accidental gating of the SWPC dashboard on `SPACE_WEATHER_IMPACT_AVAILABLE` and fixed the Impact Predictions section so its controls render consistently.
- **User Profile errors no longer block NOAA/Export** (`app/app.py`): Added a safety net around `render_user_profile_tab()` so a profile-side exception can’t stop the rest of the app from rendering.
- **Streamlit rerun loops caused by repo file writes** (`app/app.py`, `.streamlit/config.toml`): Disabled file-based `_agent_debug_log` by default (logs to the main logger only when debug is enabled) and blacklisted `.cursor/` to prevent IDE background writes from triggering reloads.

## [1.8.47] - 2025-12-23

### Fixed
- **Population Norms now works immediately after RR upload** (`app/app.py`): The norms comparison no longer depends on windowed metrics being present; it now falls back to full-recording or quick RR-derived summaries and lets you choose the recording to compare.

### Changed
- **OpenAI/Agents analysis is now Export-tab only and strictly on-demand** (`app/app.py`): AI analysis no longer runs from analysis tabs and will never auto-trigger; it runs only when you click the Export-tab buttons.
- **Metric Explainer is now Export-tab only and on-demand** (`app/app.py`): Explanations are generated only when requested from Export; auto-refresh is off by default.
- **GPT-5.2 interpretation now exposes code interpreter** (`app/gpt_interpretation.py`): The export interpretation request now includes the `code_interpreter` tool for numeric/derived-stat computations from the payload.

### Added
- **Friendly “How to read this plot” guidance** (`app/app.py`): Added concise axis/interpretation help expanders for Time Series, Frequency (PSD), Nonlinear (Poincaré), and Spectrogram tabs.

## [1.8.46] - 2025-12-23

### Fixed
- **Streamlit “fade/restart” loops during HRV + space-weather work** (`.streamlit/config.toml`): Blacklisted `crew/`, `app/data_cache/`, and `logs/` from Streamlit’s watcher so writing HRV outputs / NOAA caches no longer triggers unintended reloads.
- **Space Weather / NOAA button flicker** (`app/app.py`): Removed redundant `st.rerun()` calls after fetch actions so results render immediately without extra UI restart.

### Changed
- **12h background refresh scope tuned for responsiveness** (`app/app.py`): Background auto-refresh now preloads the **Core NOAA feeds** (fast) and keeps DONKI background queries conservative, preventing UI stalls while still supporting research correlations.

### Added
- **Extended HRF (Heart Rate Fragmentation) metrics in HRV computation** (`app/hrv_core.py`): Added PIP_H/PIP_S, PAS, W0–W3, and a quality flag to the computed metric set for performance-oriented analysis.
- **HRF panel in Readiness tab** (`app/app.py`): New HRF expander summarizes fragmentation markers per dataset with literature-based interpretation.
- **Cache reset controls** (`app/app.py`): Added explicit (opt-in) buttons to clear NOAA/SWPC/DONKI cache folders for troubleshooting, without automatic deletion.

## [1.8.45] - 2025-12-23

### Added
- **Operational vs Research enforcement** (`app/app_mode.py`, `app/app.py`, `app/operational_app.py`, `app/research_app.py`): Added an app-mode badge and hard policy gates so Operational mode stays fast and Research mode owns correlations/ML dashboards.

### Changed
- **Operational-mode hard blocks** (`app/performance_utils.py`): Heavy downloads and heavy computations are forced OFF in Operational mode (even if toggled elsewhere), preventing accidental long-running correlation/ML workflows in the clinical UI.

## [1.8.44] - 2025-12-23

### Fixed
- **Startup stability (no crashes on page config)** (`app/app.py`, `app/operational_app.py`): Page config is now applied best-effort and will never crash the app if Streamlit disallows `set_page_config()` in a given run.

## [1.8.43] - 2025-12-23

### Fixed
- **Research app startup** (`app/app.py`, `app/research_app.py`): Resolved Streamlit `set_page_config()` ordering errors by ensuring page config is applied before importing Streamlit-cached modules.

### Added
- **Streamlit stability config** (`.streamlit/config.toml`): Enabled polling file watcher for OneDrive reliability and disabled fast reruns to reduce session race conditions.

## [1.8.42] - 2025-12-23

### Added
- **Operational vs Research apps** (`app/operational_app.py`, `app/research_app.py`): New split entrypoints in the same repo. Operational mode focuses on User Profile + lightweight space-weather context; Research mode keeps the full HRV/HRF computation + NOAA/Space Weather correlation dashboards.

## [1.8.41] - 2025-12-23

### Changed
- **Faster NOAA Space loads (Core vs Full)** (`app/app.py`): NOAA Space now defaults to a **Core** scope (key geomagnetic + solar-wind feeds) for fast loading, with an optional **Full** scope for the entire feed library.
- **HTTP connection pooling** (`app/app.py`, `app/noaa_space.py`, `app/space_weather_impact.py`): Reuse pooled `requests.Session` connections to reduce repeated TLS handshakes when pulling many SWPC feeds.
- **Background auto-fetch tuned for responsiveness** (`app/app.py`): Background fetch now preloads only the NOAA Core scope and uses a shorter DONKI default window to keep background refresh lightweight.

### Fixed
- **Space Weather fetch latency** (`app/app.py`): Kp and F10.7 fetches now run in parallel when using **📥 Fetch space weather**.

## [1.8.40] - 2025-12-23

### Fixed
- **Clinical Assessment wake time** (`app/user_profile_tab.py`): Garmin sleep end timestamps are now converted to the local timezone with timezone-aware defaults, and Garmin daily metric rows are normalized safely (dataclass/`asdict`). Wake time and hours-since-waking now reflect today's Vivosmart data instead of showing UTC-shifted times.
- **Bogotá timezone alignment** (`app/user_profile_tab.py`): All user-facing wake times and “hours since waking” now use Bogotá time (UTC-5) across clinical assessment and Garmin autofill flows, avoiding Pacific/UTC drift.
- **Visible timezone indicator** (`app/user_profile_tab.py`): Clinical Assessment and Profile Tools now display the detected Bogotá timezone (UTC-5) so users can confirm clock alignment.
- **Auto-only hours awake** (`app/user_profile_tab.py`): Hours since waking is now strictly auto-computed from the selected wake time and local clock to prevent drift or manual inconsistencies.
- **Space Weather/NOAA tab load guard** (`app/app.py`): Fixed an uninitialized loading placeholder that could raise an error before the NOAA Space tab rendered when the Space Weather dashboard wasn’t loaded, restoring the “Load Space Weather dashboard” and NOAA Space tabs.

## [1.8.39] - 2025-12-23

### Added
- **Low-End Computer Performance Mode** (`app/performance_utils.py`): New performance optimization features for users with limited CPU/memory resources:
  - **Heavy Computation Toggles**: Checkboxes to enable/disable CPU-intensive operations:
    - Spectrogram Analysis (FFT over sliding windows)
    - Nonlinear Metrics (DFA, entropy, Poincaré)
    - ML Pattern Detection (K-means clustering)
    - Windowed HRV Analysis (time-varying metrics)
    - Frequency Domain Analysis (PSD, band powers)
  - **Heavy Download Toggles**: Checkboxes to enable/disable network-intensive operations:
    - NOAA Space Weather Data (multiple feeds)
    - SpaceWeatherLive Data (web scraping)
    - NASA DONKI Events (CME, SEP, flares)
    - Space Weather Impact Predictions
    - GPT AI Interpretation (API calls)
  - **Auto-Detection**: Performance settings automatically adjust based on detected CPU tier (high/medium/low)
  - **Preset Integration**: Fast (Low CPU) preset now disables heavy computations and downloads automatically

### Changed
- **Performance Settings UI** (`app/performance_utils.py`): Reorganized sidebar expander with clear sections for computations and downloads
- **ML Clustering** (`app/app.py`): ML checkbox now respects performance settings and shows help text when disabled
- **Visualization Checkboxes** (`app/app.py`): Skip checkboxes for frequency/Poincaré/spectrogram now default to skip when respective computation is disabled in performance settings
- **Space Weather Auto-Fetch** (`app/app.py`): Background fetching now respects download toggle settings

### Documentation
- **updates2026.md**: Created research document with Heart Rate Fragmentation literature review, biomathematical models for human performance, and UAV combat simulation research

## [1.8.38] - 2025-12-22

### Fixed
- **Clinical assessment Garmin autofill** (`app/user_profile_tab.py`): Handle GarminDailyMetrics dataclass objects when populating sleep context to prevent `'GarminDailyMetrics' object has no attribute 'get'` errors in the clinical assessment panel.
- **Hours since waking calculation** (`app/user_profile_tab.py`): Hours awake now derives directly from wake time (manual or Garmin) and current clock time on every rerun, ensuring today's value stays accurate without extra Garmin fetches.

## [1.8.37] - 2025-12-21

### Added
- **Dual Garmin sleep autofill buttons** (`app/user_profile_tab.py`): One-click Vivosmart pull now exists both in the Profile Tools Engine and in the Sleep & Chronotype section under Energy & Nutrition. It fills sleep hours, sleep quality, hours awake, RMSSD, and resting HR for SAFTE and Operational Performance tools.

### Changed
- **Sleep input emphasis** (`app/user_profile_tab.py`): Sleep/chronotype inputs are highlighted alongside nutrition basics, with shared session keys feeding SAFTE fatigue and Operational Performance (HRV+SAFTE) tools.

### Notes
- All tests pass (`pytest`).

## [1.8.36] - 2025-12-21

### Added
- **Background Space Weather Fetch with 12-hour Auto-Refresh** (`app/app.py`): Space weather data (NOAA, SWPC, NASA DONKI) now fetches in a background daemon thread on app startup. Data automatically refreshes every 12 hours without user intervention. The UI remains fully responsive during fetches. Each tab shows data age and refresh status (e.g., "✅ Data: 2h ago | Auto-refresh: 12h").
- **Garmin sleep autofill in Profile Tools Engine** (`app/user_profile_tab.py`): One-click Vivosmart/Garmin pull populates sleep hours, sleep quality, hours awake, RMSSD, and resting HR for SAFTE/operational tools.
- **Sleep & chronotype inputs under Energy & Nutrition** (`app/user_profile_tab.py`): Added synced sliders/inputs (sleep hours, hours awake, sleep quality, chronotype offset, RMSSD, resting HR, VO₂) that push values into the Profile Tools Engine for SAFTE fatigue and Operational Performance.

### Changed
- **EVA Clearance Semaphore** (`app/user_profile_tab.py`): Replaced the bar chart for EVA Clearance States with a traffic-light semaphore visualization. Three circular indicators (GO/MONITOR/NO-GO) glow when active, with a summary panel showing the dominant status and total assessments.
- **Space Weather Tab UI** (`app/app.py`): Updated fetch buttons with icons and clearer help text. Status indicators now show data age and auto-refresh schedule. Stale data (>12h) triggers automatic background refresh on next page load.

### Fixed
- **node_modules restoration** (`node_modules/`): Restored ECharts npm package files that were inadvertently marked as deleted in git.

## [1.8.35] - 2025-12-20

### Added
- **XGBoost and LightGBM ML models** (`app/app.py`): Added optional XGBoost and LightGBM gradient boosting models to space-weather ML analysis. These models often outperform RandomForest by 5-15% on tabular data. Models are automatically included if packages are installed (`pip install xgboost lightgbm`).
- **SHAP model interpretability** (`app/app.py`): Added SHapley Additive exPlanations (SHAP) for model interpretability. SHAP provides individual prediction explanations, feature interaction effects, and global vs local importance rankings. Available if `shap` package is installed (`pip install shap`).
- **Enhanced ML UI** (`app/app.py`): Updated Space Weather tab to display XGBoost and LightGBM metrics alongside existing models. Added tabs for Permutation Importance and SHAP Values with separate dataframes. Button text dynamically updates to show available models.
- **SHAP export support** (`app/export_utils.py`): Added SHAP importances to PDF/Markdown export reports alongside permutation importances.

### Changed
- **ML model function signature** (`app/app.py`): Updated `_run_ml_models_space_weather()` to include XGBoost, LightGBM, and SHAP computation. Function gracefully handles missing optional dependencies.
- **Requirements documentation** (`requirements.txt`): Added optional ML dependencies section with installation instructions for XGBoost, LightGBM, and SHAP.

### Documentation
- **ML enhancements guide** (`docs/ML_Enhancements_2025.md`): Created comprehensive guide documenting current ML implementations, recommended enhancements, priority matrix, and implementation roadmap.
- **Manual updates** (`docs/Manual.md`): Updated Space Weather ML section to document new models (XGBoost, LightGBM) and SHAP interpretability features.

## [1.8.34] - 2025-12-19

### Documentation
- **Canonical run command uses `hrv-py312`** (`README.md`, `docs/Manual.md`): Documented `conda run -n hrv-py312 streamlit run app/app.py` (and matching `conda run` for `pip`) so the app is always run under the pinned Streamlit 1.36.0 environment.

## [1.8.33] - 2025-12-19

### Changed
- **Plot titles moved outside chart area** (`app/echarts_component.py`, `app/circadian_tab.py`, `app/gauge_builder.py`): ECharts plot titles are now rendered as Streamlit text above each plot (and removed from the ECharts option) so the plot canvas stays clean. Gauges also hide their in-gauge title label and rely on the external title.

## [1.8.32] - 2025-12-19

### Performance
- **Default plot cap set to 500** (`app/app.py`, `app/performance_utils.py`): Default rendering now uses 500 points for rapid identification and smoother UI; you can still increase caps via the RR plot dropdown and Performance Settings presets.
- **Time Series + HR plot rendering speedup** (`app/app.py`): Downsample *before* converting full columns to Python lists, preventing large list allocations on reruns and reducing the “faded / always running” UI when plotting long recordings.
- **Spectrogram rendering speedup** (`app/app.py`): Use cached spectrogram computation, downsample the heatmap resolution, and build ECharts heatmap triplets via NumPy (vectorized) to keep browser rendering responsive on long recordings.
- **RR upload caching speedup** (`app/app.py`): Cache `UploadedRR` objects directly in session state to avoid reconstructing large DataFrames on every rerun; also avoids re-reading file bytes twice during cache cleanup.
- **Library loader speedup** (`app/app.py`): Cache the RR library listing (`@st.cache_data`) and clear it after saving so the sidebar stays responsive even with many stored files.

### Changed
- **Save-to-library interaction** (`app/app.py`): Changed from a stateful checkbox to a one-shot button to reduce rerun churn and avoid UI race issues.

## [1.8.31] - 2025-12-19

### Added
- **RR Library Loader in sidebar** (`app/app.py`): New "📚 Load from Library" expander in the sidebar allows users to browse and load previously saved RR interval files from any user profile without re-uploading. Files are sorted by modification time (most recent first) and can be loaded directly into the analysis workspace with one click or loaded and analyzed immediately with "🚀 Load + Analyze".
- **Save uploaded files to library** (`app/app.py`): When files are uploaded via the sidebar and a user profile is active, a new "💾 Save X file(s) to library" button appears. Clicking it saves the uploaded RR files to the active user's profile for future analysis without needing to re-upload. Files are saved with timestamp prefixes if the original filename lacks a date.

### Fixed
- **Critical: HRV tab infinite loading fix** (`app/app.py`): Fixed bug where Time Series, Frequency, Nonlinear, and Spectrogram tabs would get stuck in infinite loading state (faded results) after uploading RR data. Root cause: `datasets` was not being cached after HRV analysis completed, so on each rerun the tabs received empty datasets. Added session_state caching (`_hrv_cached_datasets`, `_hrv_cached_windowed_df`) to persist processed data between reruns.
- **Library loader persistence fix** (`app/app.py`): Fixed bug where files loaded from the library would cause faded/stuck pages. Root cause: `st.session_state.pop("queued_rr_filepaths")` removed the queue after first processing, leaving `uploads` empty on subsequent reruns. Added `_persisted_uploads` session state to keep uploads alive across reruns.
- **datetime.time TypeError fix** (`app/app.py`): Fixed `TypeError: descriptor 'time' for 'datetime.datetime' objects doesn't apply to a 'int' object` by importing `time as dt_time` from datetime module and using `dt_time(20, 0)` instead of `datetime.time(20, 0)`.

## [1.8.30] - 2025-12-19

### Fixed
- **User Profile performance fix** (`app/user_profile_tab.py`): **Critical fix** - Replaced nested `st.tabs()` with selectbox-based navigation for profile sub-sections (Assessments, Clinical Profile, History, HRV, Readiness, Data, Sessions). Nested tabs in Streamlit render ALL content on every rerun, causing severe slowdowns and browser freezes in Edge/Chromium browsers. The new pattern only renders the selected section (lazy loading), dramatically improving performance.
- **SAFTE/USAF Crew Rest time input fix** (`app/app.py`): Fixed `TypeError: 'module' object is not callable` caused by `import time` shadowing `from datetime import time`. Changed `time(20, 0)` and `time(8, 0)` to `datetime.time(20, 0)` and `datetime.time(8, 0)` respectively.
- **SAFTE Auto-run stability improvements** (`app/app.py`): Reduced unnecessary operations by only saving tab settings when user explicitly clicks a button (not on every rerun). Added guard to prevent double-runs when auto-run button is clicked. Shows data source info after auto-run completes.

## [1.8.29] - 2025-12-19

### Fixed
- **Streamlit version stabilization** (`requirements.txt`): Pinned to **Streamlit 1.36.0**, the most stable version for this app. Testing showed:
  - 1.35.0: Tabs don't load properly - broken
  - **1.36.0: Most stable version - RECOMMENDED** (no SessionInfo/setIn errors)
  - 1.37.0+: Fragment changes cause SessionInfo/setIn errors
  - 1.40.2: Has cosmetic error popups but functionally works
  
  **Reinstall dependencies with `pip install --upgrade -r requirements.txt` to apply.**
  
- **Simplified error suppressor** (`app/app.py`): Removed aggressive client-side suppression that could interfere with legitimate UI elements. With Streamlit 1.36.0, the aggressive suppressor is no longer needed as the root cause errors are avoided.

### Documentation
- **Added Streamlit version requirements** (`docs/Manual.md`): Documented Streamlit 1.36.0 as the required stable version in the Troubleshooting section.

## [1.8.28] - 2025-12-18

### Added
- **Operational Performance predictor (HRV + SAFTE fusion)** (`app/profile_tools_engine.py`, `app/user_profile_tab.py`): Added a transparent, bounded **operational readiness score (0–100)** that fuses SAFTE effectiveness with HRV-derived recovery/autonomic markers, including **GO/CAUTION/NO‑GO** categories plus **best/worst 2‑hour task windows** and next‑12h alert windows.
- **Crew mission workspaces** (`app/app.py`, `app/user_database.py`, `app/user_data_manager.py`): Added a `crew/` folder with **Mission 1** and **Mission 2** workspaces and a sidebar mission selector. The app now stores the active mission’s **SQLite DB + backups** under `crew/<Mission>/db/` and per-subject files under `crew/<Mission>/subjects/` (legacy root DB/data are copied into Mission 1 on first use for safety).

### Fixed
- **Profile Tools RMSSD input default** (`app/user_profile_tab.py`): Corrected the RMSSD parameter widget default (previously incorrectly seeded from resting HR), improving out-of-the-box Profile Tools behavior.
- **ECharts HTML export template** (`app/echarts_component.py`): Escaped CSS/JS braces inside the Streamlit HTML f-string to prevent a runtime `NameError: name 'height' is not defined` when rendering charts.
- **ECharts charts not appearing** (`app/echarts_component.py`): Load the ECharts runtime from a Streamlit-served local static bundle (`.streamlit/static/echarts.min.js`) with CDN fallback and an in-iframe status/error message, preventing blank plots when CDN access is blocked.
- **USAF Crew Rest checker date/time defaults** (`app/app.py`): Fixed incorrect `datetime.date.today()` / `datetime.time(...)` usage caused by `from datetime import datetime` shadowing, which could crash the app before any plots rendered.

### Tests
- Added a regression test to ensure `render_echarts()` does not raise on CSS brace literals (`tests/test_echarts_component.py`).

### Documentation
- Updated `README.md` and `docs/Manual.md` to document the new Operational Performance tool and add neurovisceral integration references.

## [1.8.27] - 2025-12-18

### Added
- **Per-user SAFTE/FRMS default inputs** (`app/user_database.py`, `app/app.py`, `app/fatigue_integration.py`): Added persisted **fatigue profile defaults** (typical sleep window + duty window + weekend policy) so SAFTE and FRMS can auto-run using user-collected variables without manual re-entry.
- **SAFTE duty-weekend toggle** (`app/app.py`): FRMS “in-scope” duty mask can now optionally include weekends, improving schedule realism for shift/mission operations.

### Changed
- **Fatigue tab exports (ECharts-first)** (`app/app.py`): Removed the Plotly/Kaleido publication-export fallback and standardized on the built-in ECharts client-side export toolbar (PNG/SVG/HTML/spec JSON + Print/Save PDF).

### Tests
- Added regression coverage for fatigue profile defaults and assessment automation (`tests/test_fatigue_profile_defaults.py`).

### Documentation
- Synced `README.md`, `docs/Manual.md`, `WARP.md`, and `requirements.txt` version headers to **v1.8.27** and replaced placeholder clone URLs with the canonical repository (`strikerdlm/HRV`).

## [1.8.26] - 2025-12-18

### Added
- **Mission FRMS v2 prototype: Crew Risk Board** (`app/frms_v2.py`, `app/app.py`): Export tab now includes a **multi-profile** FRMS “crew risk board” that runs bounded SAFTE forecasts per selected active user and aggregates FRMS metrics/classifications into a roster view.
- **FRMS v2 exports + decision log** (`app/frms_v2.py`, `app/app.py`): Added **crew risk board CSV/JSON exports** and an exportable **decision log JSON** (decision owner + mitigations + embedded evidence payload) for audit trail workflows.

## [1.8.25] - 2025-12-18

### Added
- **Persisted study groups & assignments** (`app/user_database.py`, `app/app.py`): Export → Longitudinal cohort comparisons now supports **persisted** `study_groups` / `study_assignments` (Study ID + roster editor) instead of ad‑hoc control/intervention selectors.
- **Mixed-effects longitudinal inference** (`app/export_utils.py`, `app/app.py`): Optional **random-intercept mixed model** for Group × Time on Δ vs baseline (exports CSV + included in longitudinal Markdown report when enabled).
- **FRMS rule-based alerts** (`app/frms.py`, `app/app.py`): FRMS dashboard now emits a deterministic “why it triggered” alert list and includes alerts in the exported FRMS JSON payload.

### Dependencies
- Added `statsmodels` to `requirements.txt` for mixed-effects modeling.

## [1.8.24] - 2025-12-18

### Added
- **Longitudinal cohort comparisons (T0–T21)** (`app/app.py`, `app/export_utils.py`): Export tab now supports **control vs intervention** comparisons using **within-subject Δ vs baseline** per timepoint, with CSV + Markdown exports (includes effect sizes and FDR-adjusted p-values).

### Fixed
- **ECharts export controls** (`app/echarts_component.py`): All ECharts visuals now include built-in, client-side exports for **PNG (high-DPI)**, **SVG (vector)**, **HTML**, and **spec JSON**, plus a **Print/Save PDF** workflow (browser print).
- **Sleep tab compatibility import** (`app/echarts_component.py`): Restored the `st_echarts(...)` API used by `app/sleep_tab.py` so the sleep UI no longer degrades due to a missing import.

### Documentation
- Updated `README.md` and `docs/Manual.md` to reflect the new longitudinal cohort export workflow.

## [1.8.23] - 2025-12-17

### Added
- **Profile Tools Engine** (`app/profile_tools_engine.py`): New comprehensive calculation engine accessible per user profile:
  - **Recovery Score Calculator**: lnRMSSD-based recovery assessment with HRV, sleep, and resting HR components
  - **Training Readiness Assessment**: Multi-component readiness score with workout recommendations
  - **SAFTE Fatigue Prediction**: 24-hour cognitive effectiveness forecast using sleep homeostasis and circadian models
  - **Personalized HRV Analysis**: Age/sex-adjusted HRV interpretation with parasympathetic and stress indices
  - **Performance Forecast**: Hour-by-hour performance prediction with peak/low time identification
- **Profile Tools Engine UI** (`app/user_profile_tab.py`): New "🛠️ Profile Tools Engine" expander in Clinical Profile tab:
  - Tool selector for individual or combined analysis
  - Configurable input parameters (sleep, chronotype, HRV values)
  - Interactive results display with component breakdowns
  - 24-hour performance curve visualization
  - Markdown export functionality
  - Workout suggestions and clinical recommendations
- **Run All Tools Summary**: One-click execution of all profile tools with aggregated results display

### Fixed
- **Clinical Profile tab** (`app/user_profile_tab.py`): Removed nested Streamlit expanders that could crash the app with `StreamlitAPIException: Expanders may not be nested...` by converting inner panels (parameters/history/recommendations/subjective logs) to checkbox-controlled sections.
- **Wrist Monitoring history** (`app/user_profile_tab.py`): Fixed “latest available metric” selection so per-metric values truly come from the most recent non-null row in the latest-first table order (avoids index-label pitfalls when the DataFrame index is not reset or not unique).

### Scientific References (Profile Tools Engine)
- Plews DJ et al. (2013). J Appl Physiol - lnRMSSD for training monitoring
- Kiviniemi AM et al. (2007). Med Sci Sports Exerc - HRV-guided training
- Hursh SR et al. (2004). Aviat Space Environ Med - SAFTE fatigue model
- Borbély AA (1982). Hum Neurobiol - Two-process model of sleep regulation

## [1.8.22] - 2025-12-17

### Added
- **Personalized Health Metrics** (`app/personalized_computations.py`): New module providing user-specific physiological calculations tailored to individual profile data:
  - **Body fat estimation** using US Navy method (Hodgdon & Beckett 1984) with neck/waist/hip circumferences
  - **Sleep apnea risk** assessment using STOP-BANG score components (Chung et al. 2008)
  - **Age/sex-adjusted HRV reference ranges** from Nunan et al. (2010) and Shaffer & Ginsberg (2017)
  - **VO2max fitness classification** using ACSM Guidelines percentile tables
  - **Cardiovascular risk profile** assessment with multiple risk/protective factors
  - **Personalized hydration requirements** based on NASA-STD-3001 (32 mL/kg body weight)
- **Personalized Health Metrics UI** (`app/user_profile_tab.py`): New expander panel in Clinical Profile tab displaying:
  - BMI with WHO classification
  - Body fat percentage with ACSM category (Athletes/Fitness/Average/Obese)
  - STOP-BANG sleep apnea risk score with recommendations
  - Personalized HRV reference ranges table by age group
  - Fitness classification with percentile estimate
  - Cardiovascular risk factors and protective factors
  - Hydration requirements with glasses/liters display
  - One-click markdown summary export
- **Personalized HRV Interpretation** (`app/hrv_core.py`): New `interpret_hrv_personalized()` function that:
  - Interprets HRV metrics against age/sex-adjusted norms
  - Returns status (very_low/low/normal/high/very_high) per metric
  - Provides percentile estimate and z-score for each metric
  - Generates overall autonomic assessment with recommendations
- **Enhanced User Context** (`app/user_profile_tab.py`): `get_active_user_context()` now includes:
  - Body composition data (neck_cm, waist_cm, hip_cm, body_fat_pct, lean_mass_kg)
  - Personalized HRV norms for the user's age group
  - All personalized metrics calculations
- **Diego Malpica Profile Setup** (`app/setup_diego_profile.py`): Utility script to initialize complete user profile with:
  - Biometrics (weight 91 kg, height 173 cm)
  - Body composition (neck 41 cm, waist 94 cm, hip 102 cm)
  - Clinical assessment scales (ESS, PSQI, KSS, Samn-Perelli)
  - VO2max and fitness data

### Changed
- **User Profile Tab** imports and integrates the personalized_computations module with graceful fallback
- **Clinical Profile** section now includes "Personalized Health Metrics" expander after Exploration Medical Analytics
- **Active User Context** propagates body composition and personalized metrics to all tabs

### Documentation
- Updated `WARP.md` roadmap with Phase 5: Personalized User Profile Features (marked complete)
- Updated `README.md` features table with personalized health metrics and HRV interpretation
- Updated `docs/Manual.md` with comprehensive Personalized Health Metrics guide including:
  - US Navy body fat formula and classification tables
  - STOP-BANG score interpretation
  - Age-adjusted HRV reference ranges
  - VO2max fitness classification by age/sex
  - Cardiovascular risk factors
  - Hydration calculation methodology

### Scientific References
- Hodgdon JA, Beckett MB (1984). Naval Health Research Center - Body Fat Prediction
- Chung F et al. (2008). Anesthesiology - STOP-BANG Questionnaire
- Nunan D et al. (2010). PACE - Short-term HRV Normal Values
- Shaffer F, Ginsberg JP (2017). Front Public Health - HRV Metrics and Norms
- ACSM Guidelines for Exercise Testing and Prescription (11th Ed)
- NASA-STD-3001 Water Requirements

## [1.8.21] - 2025-12-14

### Added
- **Cohort / Group Summaries export** (`app/app.py`, `app/export_utils.py`): the Export tab now supports cohort-level exports for multi-user sessions, including a per-subject “latest snapshot” roster (HRV + clinical scales + exploration medical record fields when present) plus cohort descriptive statistics. CSV and Markdown downloads are provided.

### Tests
- Added regression coverage for cohort export utilities (`tests/test_cohort_export_utils.py`).

### Documentation
- Updated `WARP.md`, `README.md`, and `docs/Manual.md` to mark Group Summaries complete and describe the new cohort export workflow.

## [Unreleased]

### Added
- **FRMS + USAF crew rest dashboard (SAFTE tab)** (`app/app.py`, `app/frms.py`): The SAFTE/Fatigue tab now includes an ICAO-aligned FRMS summary (WOCL exposure + threshold-based risk matrix) and a USAF crew rest compliance checker (AFMAN 11-202V3 baseline), plus publication-grade plot exports (Plotly fallback: HTML/PNG/SVG/PDF).
- **Doctoral thesis proposal** (`docs/PhD.md`): Literature-backed dissertation concept for pilot/commander readiness classification, including multimodal predictors (sleep/fatigue/circadian/HRV/objective vigilance), countermeasure governance, and a 5×5 operational risk matrix for mission go/no-go decision support.
- **Per-user HRV analysis artifact cache in SQLite** (`app/user_database.py`, `app/app.py`): reusable HRV analysis payloads are now persisted per user and keyed by **file hash + analysis settings hash**, enabling cross-session reuse without recomputation when inputs and settings match.
- **Per-user GPT-5.2 export persistence** (`app/user_database.py`, `app/app.py`): GPT-5.2 high-reasoning interpretation markdown (and citation metadata) is now stored per user + payload hash so exports can include prior interpretations even when GPT is disabled/offline. A **combined HRV + GPT** markdown download is provided in the Export tab.
- **Longitudinal timepoints (T0–T21)** (`app/user_database.py`, `app/user_profile_tab.py`, `app/app.py`): Added a `measurement_timepoints` table and UI controls to tag new HRV measurements and clinical assessments to a study timepoint so baseline/Δ workflows can be built deterministically.
- **Baseline/Δ analytics (T0–T21)** (`app/user_database.py`, `app/user_profile_tab.py`): The **User Profile → HRV → HRV Measurement History** panel now includes a baseline/Δ table grouped by timepoint label (T0…T21), computing per-timepoint aggregates and deltas vs T0.
- **Profile HRV performance/recovery plots** (`app/user_profile_tab.py`): The **User Profile → HRV → HRV Measurement History** panel now includes additional trend visualizations (lnRMSSD, heart-rate, autonomic indices, and quality) plus optional HRV↔Garmin daily metric relationship plots when wearable history is present.
- **Profile RR Library → Analysis Workspace** (`app/user_profile_tab.py`, `app/app.py`): Added a **Stored RR Library** loader inside **User Profile → HRV** so you can load already-saved RR recordings into the main analysis workspace (with an optional “Load + run analysis” shortcut) without re-uploading files.
- **Profile Readiness & Recovery** (`app/user_profile_tab.py`): Added a **Readiness** sub-tab inside User Profile that computes readiness from stored parasympathetic-index history and renders HRV metric gauges in the same ECharts style as the main gauges tab.
- **Profile body composition persistence** (`app/user_profile_tab.py`, `app/user_database.py`): The **Body Composition** panel now saves measurements (body fat, lean/muscle mass, circumferences) to the database and renders trends/history per profile.
- **Profile exploration medicine auto-enrichment** (`app/user_profile_tab.py`): The **Exploration Medical Record** can now align records to a log date and auto-compute (a) **space-weather alert level** from NOAA Kp + >10 MeV proton flux (G/S scales) and (b) a **baseline cumulative radiation dose estimate** from mission profile/habitat + EVA hours (with NASA limit guidance). Stress and sleep fields can seed from objective HRV and Garmin daily metrics when available.
- **Garmin export JSON ingest (Vivosmart 5)** (`app/garmin_import.py`, `app/user_profile_tab.py`): The **User Profile → Data → Wrist Monitoring (Vivosmart 5)** uploader now accepts unzipped Garmin export `.json` files, including:
  - `UDSFile_*.json` daily summaries (steps, distance, active calories, stress, SpO₂, respiration, body battery)
  - `*_sleepData.json` (sleep stages + scores; supports the newer nested `sleepScores` schema)

### Changed
- **Fatigue zone thresholds** (`app/fatigue_integration.py`, `app/app.py`): Updated operational effectiveness zones to SAFTE/FAST-style thresholds and clarified boundary labels (≥90, >77–<90, >70–≤77, ≤70) for safer interpretation.
- **Covariate adjustment defaults** (`app/app.py`): age/sex/BMI/activity inputs now default to the active user profile context when available (with a “Use active profile defaults” toggle), ensuring profile-aware HRV interpretation is user-scoped.
- **Performance** (`app/app.py`, `app/user_profile_tab.py`, `app/user_database.py`, `app/i18n.py`): Bounded Streamlit caches (heavy HRV compute, space-weather fetches, profile/history loaders, i18n lookups) with explicit TTL + `max_entries` to keep memory usage stable during long sessions.
- **Readiness tab** (`app/app.py`): Readiness scoring now prefers the user’s **stored HRV history** in the database (parasympathetic index) so it can include more sessions than the currently loaded uploads.
- **SAFTE/Fatigue inputs** (`app/app.py`): Sleep duration and sleep quality can now auto-seed from the latest stored Garmin daily metrics (one-shot per new Garmin day), improving per-user workflow when wearable sleep data is available.

### Fixed
- **Garmin gauge thresholds** (`app/gauge_builder.py`): Fixed accidental constant shadowing and corrected `distance_km`/Garmin wellness thresholds so the intended km/kcal/stress/SpO₂ ranges are consistently applied.
- **User Profile** (`app/user_profile_tab.py`): Fixed Streamlit duplicate form-key crash by rendering the longitudinal timepoint selector once above the profile sub-tabs (instead of inside multiple tab panels).
- **User Profile HRV history refresh** (`app/user_profile_tab.py`): Added a **Regenerate plots** control in **HRV Measurement History** to force-refresh charts after new uploads/analysis runs (clears Streamlit data caches and reruns the HRV history renderer).
- **Navigation after HRV analysis** (`app/app.py`): Removed an early return that could trap the UI on an “already completed” message after analysis; the full tab navigation now renders and the action button switches to **Recompute HRV Analysis** when appropriate.
- **Logging** (`app/logging_config.py`): Suppressed benign Streamlit/Tornado `WebSocketClosedError` “Task exception was never retrieved” noise so `logs/errors.log` stays actionable.
- **Device imports** (`app/app.py`): ActiGraph and Somfit sidebar imports now run only when clicking an explicit **Import** button (prevents expensive re-processing on every rerun) and always clean up temporary files, improving UI smoothness and reliability.
- **Garmin daily metrics upsert** (`app/user_database.py`): Partial imports no longer wipe previously stored non-null fields (upsert now preserves existing values when the new value is NULL).
- **Wrist Monitoring stats/trends** (`app/user_profile_tab.py`): The History tab now loads a configurable number of stored Garmin days and renders trends + summary statistics across all saved daily metrics (not just a subset), and the “View all daily metrics” panel now shows the full loaded table (not just 10 rows).

### Tests
- Added regression coverage for timepoint persistence and database backups (`tests/test_longitudinal_timepoints.py`).
- Added regression coverage for tz-aware datetime handling in SWPC solar flux retrieval (`tests/test_space_weather_alignment.py`).

### Documentation
- Updated `README.md`, `docs/Manual.md`, and `docs/index.md` to reflect the current roadmap status (plot governance next), corrected the docs landing page away from the legacy notebook instructions, and added the verifiable PROOF-AF DOI citation.
- Updated `WARP.md` to match the current conda environment name (`hrv-py312`) and roadmap status.

## [1.8.20] - 2025-12-12

### Changed
- **OpenAI models**: Updated all OpenAI *language-model* calls to use `gpt-5.2` with high reasoning effort (`reasoning.effort="high"`) for interpretation, Agents SDK personas, and the SpaceWeatherLive extraction fallback (`app/gpt_interpretation.py`, `app/agent_runtime.py`, `app/spaceweather_openai_fallback.py`, `app/app.py`).

### Fixed
- **Fatigue tab auto-run** (`app/app.py`, `app/fatigue_integration.py`): the 5-day “Auto-run” button now matches the actual data priority (wrist → clinical → Garmin Connect) and attempts Garmin Connect only when credentials are configured, avoiding spurious error logs when `GARMIN_EMAIL`/`GARMIN_PASSWORD` are unset.

## [1.8.19] - 2025-12-11

### Fixed
- **Space Weather correlations** (`app/app.py`): the “Include weather covariates (Bogotá)” toggle now performs partial Pearson correlations that regress out ERA5 temperature, humidity, pressure, wind, precipitation, and cloud cover before computing HRV↔space-weather statistics. Previously the checkbox fetched data but never influenced the coefficients, leaving meteorological confounds in place.

### Tests
- Added regression tests to ensure (a) the new partial-correlation path actually dampens shared-weather artefacts and (b) the assessment-driven SAFTE automation keeps prioritizing wrist monitoring data ahead of clinical fallbacks (`tests/test_space_weather_alignment.py`, `tests/test_new_modules.py`).

### Documentation
- `docs/Manual.md`: documented how enabling weather covariates swaps the correlation engine into partial-r mode so analysts know when geomagnetic findings already control for local meteorology.

## [1.8.18] - 2025-12-11

### Added
- **Assessment-aware SAFTE auto-forecast** (`app/fatigue_integration.py`, `app/app.py`): the 5-day automation now prioritizes wrist monitoring data from the Assessment tab, falls back to subjective clinical sleep quality if wrist data is absent, and only then attempts a Garmin Connect fetch (`GARMIN_EMAIL`/`GARMIN_PASSWORD`). The source used and summary are displayed for traceability.

### Documentation
- README.md and docs/Manual.md now describe the Garmin auto-run flow and the `.env` variables it depends on.

## [1.8.17] - 2025-12-11

### Added
- **Agent telemetry logging** (`app/agent_logging.py`, `app/agent_runtime.py`, `app/agent_insights.py`, `app/gpt_interpretation.py`, `app/spaceweather_openai_fallback.py`): every OpenAI persona now records request payloads, doctor-level answers, and citation metadata to the rotating log/audit trail so flight surgeons can reconstruct each recommendation.
- **Markdown + audio exports** (`app/agent_insights.py`, `app/app.py`, `app/agent_audio.py`): metric explanations and GPT-5 interpretations can be downloaded as publication-grade markdown and rendered to discrete tts-hd audio clips for hands-free playback on-console.
- **TTS helper** (`app/agent_audio.py`): hardened HTTPS client for OpenAI `tts-1-hd` endpoints with configurable voice/model plus audit logging of synthesized clips.

### Changed
- **Agents SDK enforcement** (`app/agent_runtime.py`, `app/gpt_interpretation.py`): Personas now require `web_search` citations, append `## Sources` to every report, and run with high-effort reasoning so exported markdown stays doctorate-level and evidence based.
- **Metrics tab UI** (`app/app.py`): Agent appendix preview plus download/audio controls live alongside the explainability table, ensuring the reporting pipeline stays within a single workflow.

### Fixed
- Metric explainability exports previously lacked a consolidated appendix, making downstream reporting manual; the new markdown assembler guarantees deterministic references even without API keys.

## [1.8.16] - 2025-12-11

### Added
- **Metric Explainability Specialist** (`app/agent_runtime.py`, `app/agent_insights.py`, `app/app.py`): GPT-5.2 high-reasoning persona paired with `code_interpreter` plus a deterministic fallback panel inside the Metrics tab so every SDNN, RMSSD, pNN50, LF/HF, HF power, and mean HR value now includes a citation-backed explanation.
- **Unit tests** (`tests/test_agent_insights.py`): Coverage for the new agent insight manager to ensure per-metric classifications stay synchronized with Task Force (1996) and Shaffer & Ginsberg (2017) ranges.

### Changed
- Metrics tab now hashes its dataset snapshot and auto-refreshes the explanation panel when values change, ensuring users always read up-to-date interpretations before invoking the agent.

### Fixed
- Addressed the missing per-metric guidance in the Metrics tab by adding a deterministic explainer so users can always read contextual analysis even when the Agents SDK is offline or API keys are absent.

### Documentation
- README.md / docs/Manual.md: Documented the Metric Explainability Specialist persona, the new Metrics-tab panel, and how it ties into the Agents SDK rollout.

## [1.8.15] - 2025-12-10

### Added
- Sleep Analysis sidebar login and device import controls now run inside debounced forms with explicit submit buttons, reducing unnecessary reruns and completing the roadmap's batch submission objective for this tab.
- `app/agent_runtime.py`: structured OpenAI Agents SDK scaffold (tool belt, MCP servers, and personas) plus an About-tab expander so flight surgeons can audit forthcoming autonomous copilots.

### Changed
- Welcome header, sidebar branding, and the About tab now surface release date + git branch/commit metadata derived from `CHANGELOG.md`, ensuring the UI always mirrors the current build without restarting Streamlit.
- README.md and docs/Manual.md highlight the new release-awareness chips and link directly to the Agents SDK blueprint that is now backed by code.

### Fixed
- Garmin/ActiGraph/Somfit uploads no longer reprocess the same file on every rerun; imports execute only when the user presses the corresponding button and the uploader state is cleared afterwards to prevent duplicate data entries.
- `version_info.py` reloads when `CHANGELOG.md` changes instead of relying on a one-time cache, so Streamlit reruns instantly pick up new versions/badges.

### Documentation
- README.md: Added v1.8.15 highlights plus a status note that the agent blueprint now lives in code.
- docs/Manual.md: Updated version banner, release-awareness note, and a new section describing the agent runtime roadmap.

## [1.8.14] - 2025-12-10

### Added
- **📂 Load RR files** controls inside the Time, Frequency, and Nonlinear tabs so analysts can explicitly load a subset of uploaded RR recordings per visualization without touching the sidebar cache.
- Apache ECharts timelines across the User Profile (assessment history, Garmin wellness, HRV history, Exploration Medical analytics) for consistent, publication-ready styling.
- Unit tests covering the new space-weather alignment helpers.

### Changed
- Space weather correlations now resample NOAA/DONKI predictors onto the exact HRV window timestamps (bounded interpolation, no nearest-neighbor drift), matching heliobiology best practices.
- Weather covariates and the feature-matrix builder reuse the same alignment helper, ensuring every predictor/HRV pair references the same instant before statistics are computed.

### Fixed
- Prevented mismatched timestamps from contaminating Kp/NOAA correlation coefficients; empty joins now warn users instead of quietly reusing stale data.

## [1.8.13] - 2025-12-10

### Added
- Dataset info headers in Time Series, Frequency, Nonlinear, Spectrogram, and Gauges tabs showing file names, recording dates, durations, and beat counts for clearer analysis context.

### Changed
- Default analysis settings now enable Frequency plots, Poincaré, Spectrogram, Gauges, and ML-assisted deviation clustering for a richer out-of-the-box experience.

### Fixed
- Fixed pandas `MergeError` when reusing cached results that already contain `sdann_5min`/`sdnnidx_5min` columns; duplicate columns are dropped before merge.

## [1.8.12] - 2025-12-10

### Added
- Data tab tools to convert Garmin FIT → CSV inside the User Profile and download the result.
- CSV ingestion in the Data tab: upload Garmin CSV files to store them under the active profile.
- FIT → CSV conversion uses bounded parsing (fitparse) with per-profile storage of both raw FIT and generated CSV.

### Changed
- Data tab now surfaces FIT/CSV utilities before Garmin ingest for a streamlined workflow.

## [1.8.11] - 2025-12-10

### Added
- Optional reuse of cached HRV results by file hash + analysis settings with a sidebar toggle; warns when settings differ so you can recompute.
- Raw RR uploads now persist immediately to `data/{user}/rr_intervals` for the active profile (sidebar and profile uploads) so tracings are never lost between runs.

### Changed
- Analysis settings persistence now records covariate inputs (age/sex/BMI/exercise) and validates them before reusing cached results.
- Profile-tab RR uploads now set the active profile automatically to prevent cross-user mixing during analysis.

## [1.8.10] - 2025-12-10

### Added
- Per-user RR upload persistence and duplicate detection: RR uploads now store raw files and computed HRV results keyed by file hash per active profile, with sidebar warnings when a file was already analyzed.
- Profile-tab RR uploads: users can upload RR files directly inside the User Profile tab; files are saved to their data folder and queued for analysis without using the sidebar.
- Active profile indicator: a prominent light-bulb banner shows which profile is currently driving HRV analyses to prevent cross-user mix-ups.

### Changed
- HRV measurements table now tracks `source_file`, `file_hash`, `recording_start_utc`, `analysis_settings_json`, and `created_at` to bind analyses to uploads and settings.

---

## [1.8.9] - 2025-12-10

### Documentation
- **README.md**: Added the OpenAI Agents SDK integration blueprint outlining MCP bridges, toolchain activation (code interpreter, file/web search, Wolfram Alpha, E2B), and aerospace medicine use cases for autonomous agents.

---

## [1.8.8] - 2025-12-09

### Fixed
- **Garmin FIT wellness monitoring data** (`app/garmin_import.py`): 
  - Now properly extracts heart rate, stress, SpO2, respiration, and body battery from `monitoring` message types in FIT files (24/7 wellness tracking)
  - Previously only captured activity metrics (steps/calories); now captures ALL physiological data from monitoring messages
  - Added sleep message parsing (`sleep` and `sleep_level` message types)
  - Fixed data validation: returns wellness data even when RR intervals are absent (Vivosmart 5 optical sensor limitation)
  - **Fixed daily aggregation**: Steps, distance, and calories now use `max()` instead of sum for cumulative counters (fixes inflated values)
  - Added comprehensive logging to track extraction success for each metric type and daily summaries
  - Fixed undefined variable error (`fit_count`) in ZIP parsing logging
- **Garmin ZIP parsing** (`app/garmin_import.py`): 
  - ZIPs containing only embedded FIT files (no wellness JSON) now parse those FIT files properly
  - Batch processing of multiple FIT files inside ZIP with merged dataframes
- **Batch upload support** (`app/device_imports.py`): Sidebar Garmin uploader now accepts multiple FIT/ZIP files and processes all wellness metrics
- **Gauge aesthetics** (`app/gauge_builder.py`): Reduced ring width from 20px to 8px for cleaner, narrower gauge appearance

### Changed
- **User guidance** (`app/user_profile_tab.py`, `app/device_imports.py`): Added help sections explaining how to request complete wellness export from Garmin Connect to get sleep, stress, body battery, SpO₂, and respiration JSON files (not available in individual activity FIT exports)
- **Gauge aesthetics** (`app/gauge_builder.py`, `app/user_profile_tab.py`):
  - Added proper thresholds for all Garmin wellness metrics (steps, distance, calories, SpO2, stress, body battery, respiration, sleep)
  - Organized gauges into logical sections: Activity & Movement, Heart Rate & Stress, Sleep & Recovery, Respiration & SpO₂, Body Battery
  - Added prominent display of latest day values with thousand separators for large numbers
  - Improved layout with consistent two-ring gauge design matching the rest of the app

---

## [1.8.7] - 2025-12-09

### Added
- **Batch Garmin wrist uploads** (`app/device_imports.py`): Sidebar Garmin import now accepts multiple FIT/ZIP files at once, captures wellness metrics (steps, distance, sleep score/efficiency/duration, SpO₂, respiration awake/sleep, stress, calories, body battery) and queues them for Wrist Monitoring history.
- **FIT parser dependency**: Added `fitparse` to `requirements.txt` for Vivosmart 5 FIT ingestion.

### Changed
- Wrist monitoring automatically ingests pending sidebar metrics into the user’s history tab after batch uploads.

---

## [1.8.6] - 2025-12-09

### Added
- **Garmin Vivosmart 5 clinical ingest** (`app/garmin_import.py`, `app/user_profile_tab.py`, `app/user_database.py`, `app/device_imports.py`):
  - FIT and wellness ZIP parsing now captures steps, distance, calories, sleep score/efficiency/duration, stress, SpO₂, respiration (awake/sleep), and body battery charge/drain.
  - New `garmin_daily_metrics` table with upsert support to store per-day wellness summaries tied to each user profile.
  - User Profile → Data tab adds a Garmin Vivosmart 5 uploader; History tab shows double-ring ECharts gauges and recent daily metrics.
  - Sidebar Garmin import now accepts `.fit` for RR extraction from Vivosmart 5 FIT files.

### Documentation
- **README.md / docs/Manual.md**: Added guidance for the Vivosmart 5 clinical ingest workflow, thresholds (respiration 10–17 rpm), and the new gauges available in the Clinical Profile history.

## [1.8.5] - 2025-12-06

### Added
- **Polar AccessLink Automation** (`app/polar_accesslink.py`): Complete OAuth token management and VO2max sync
  - `PolarAccessLinkClient` class for per-user credential management
  - Secure token storage with XOR encryption (obfuscation for local SQLite)
  - VO2max history tracking with source attribution (Polar, manual, etc.)
  - Automatic sync with duplicate detection (avoids redundant entries)
  - Fitness class determination based on VO2max values
- **Database schema updates** (`app/user_database.py`):
  - `polar_credentials` table for persisting OAuth tokens per user
  - `vo2max_history` table for longitudinal VO2max tracking
  - `PolarCredentials` and `VO2maxEntry` dataclasses
  - Database methods: `save_polar_credentials()`, `get_polar_credentials()`, `delete_polar_credentials()`
  - Database methods: `save_vo2max_entry()`, `get_vo2max_history()`, `get_latest_vo2max()`, `get_vo2max_dataframe()`
- **Unit tests** (`tests/test_polar_accesslink.py`): 24 comprehensive tests covering:
  - Token encryption/decryption round-trips
  - Database CRUD operations for credentials and VO2max history
  - PolarAccessLinkClient lifecycle and sync operations
  - Mocked API response handling
- **Exploration Medical Analytics Dashboard** (`app/user_profile_tab.py`):
  - Radiation gauge tracks cumulative mSv vs NASA 1000 mSv guideline with daily accumulation rate
  - EVA workload cards summarize 72 h EVA hours, peaks, and days since last EVA alongside clearance histograms
  - Stress panel surfaces rolling averages for confinement stress, workload rating, and sleep duration
  - Frequency tables tally the most common acute symptoms and behavioral flags straight from ExMC logs
- **Unit tests** (`tests/test_new_modules.py`): Added coverage for the radiation-rate computation and frequency aggregation helper powering the dashboard

### Changed
- **NASA Nutrition Calculator** (`app/user_profile_tab.py`):
  - VO2max section now uses `PolarAccessLinkClient` for persistent sync
  - Added "💾 Save Manual Entry" button to record manual VO2max values
  - VO2max history expander shows recent entries with source and fitness class
  - Improved source attribution ("Polar AccessLink sync", "History", "Manual entry")
- **Import structure** (`app/polar_accesslink.py`): Fallback imports for both `app.` prefix and direct module imports

### Fixed
- **Token encryption** (`app/polar_accesslink.py`): `os.getlogin()` now falls back to environment variables when running in non-TTY environments

### Documentation
- **README.md / docs/Manual.md / WARP.md**: Documented the Exploration Medical Analytics dashboard, updated the roadmap status, and highlighted the new radiation/EVA/stress cards.

---

## [1.8.4] - 2025-12-05

### Fixed
- **FutureWarning** (`app/app.py`): Fixed deprecated `.fillna()` downcasting on artifact_flag column using explicit `boolean` dtype conversion.
- **CPU name detection** (`app/cpu_optimization.py`): Fixed `[WinError 2]` on modern Windows by reading CPU name from registry instead of deprecated `wmic` command.

---

## [1.8.3] - 2025-12-05

### Added
- **PANAS Scale (Positive and Negative Affect Schedule)** (`app/user_profile_tab.py`, `app/i18n.py`):
  - Full 20-item PANAS assessment (Watson, Clark & Tellegen, 1988)
  - Validated English and Spanish (Sandín et al., 1999) translations
  - Interactive select sliders for all 10 PA and 10 NA items
  - Real-time ECharts gauge visualizations for PA and NA scores
  - Normative interpretation thresholds (Crawford & Henry, 2004)
  - Integration with clinical assessment history and trends

### Changed
- **User Profile performance** (`app/user_profile_tab.py`): Assessment history now uses `@st.cache_data` with TTL for faster repeated loads after login.
- **ESS slider optimization** (`app/user_profile_tab.py`): Epworth Sleepiness Scale uses `st.select_slider` with pre-initialized session state for smoother interaction.
- **Medical history summary** (`app/user_profile_tab.py`): Summary now pulls latest exploration medical record from database, showing mission/EVA/radiation at a glance.
- **Assessment history** (`app/user_profile_tab.py`): Now displays PANAS PA/NA averages and trends alongside fatigue scales.
- **Exploration Medical Record (ExMC/EIMO)** (`app/user_profile_tab.py`): Expanded form per NASA Exploration Medical Capability and Earth-Independent Medical Operations frameworks:
  - Mission profiles: LEO through Mars Surface with EIMO autonomy levels
  - Radiation & space weather: cumulative dose, GCR concern flag
  - Health status: HRP risk categories, expanded acute symptoms, workload rating
  - Countermeasures: sleep quality, exercise modality, caloric intake
  - Medical logistics: resupply days tracking

### Fixed
- **Schema migration resilience** (`app/user_profile_tab.py`): All selectbox and multiselect widgets now gracefully handle stale values from database records when option lists change. Prevents `StreamlitAPIException` when stored defaults no longer match current options; logs migration events for debugging.
- **Database schema** (`app/user_database.py`): Added `panas_positive_affect` and `panas_negative_affect` columns to clinical_scales table with automatic migration.

### Removed
- **Deprecated MIST reference** (`app/user_profile_tab.py`): Removed outdated NASA MIST URL; form now cites ExMC/EIMO peer-reviewed sources.

### Documentation
- **PANAS documentation** (`docs/Manual.md`): Complete guide including interpretation tables, clinical significance, and scientific references.
- **Roadmap** (`docs/Manual.md`): Added ExMC Clinical Assessment milestone (Q4 2025 in progress) with planned Q1 2026 enhancements (CDSS, probabilistic risk, XR telepresence).

---

## [1.8.2] - 2025-12-05

### Changed
- **Always-on space weather pipelines** (`app/app.py`, `app/noaa_space.py`): Space Weather, NOAA Space, and impact predictions now auto-load on tab entry even with no RR uploads, using cache-first fetches and stale-cache fallback for Kp/F10.7 and NOAA feeds when connectivity drops.
- **Resilience and logging** (`app/app.py`, `app/noaa_space.py`): SWPC/NOAA fetch failures now log centrally and surface warnings while keeping prior cached data available.

### Fixed
- **NOAA auto-load retry storm** (`app/app.py`): Added auto-loading/attempt guards so NOAA auto-fetch runs once per session and won't hammer the APIs when feeds fail (empty bundles no longer trigger repeated retries).

### Documentation
- Updated **README.md** and **docs/Manual.md** to explain automatic loading and offline-friendly cache behavior for space weather features.

---

## [1.8.1] - 2025-12-05

### Added
- **Cross-tab result broker** (`app/ui_state_manager.py`): New per-user, per-tab broker shares small summaries safely across Streamlit reruns.
- **Circadian → SAFTE sync** (`app/circadian_tab.py`, `app/app.py`): Circadian tab publishes DLMO/CBT/ESRI plus light windows; SAFTE tab can apply the latest circadian sleep window and chronotype with one click.
- **Unit tests** (`tests/test_ui_state_manager.py`): Coverage for the broker’s publish/get/eviction behavior.

### Changed
- **Documentation** (`README.md`, `docs/Manual.md`, `WARP.md`): Roadmap now marks cross-tab correlation complete and explains the new circadian-to-fatigue bridge.

---

## [1.8.0] - 2025-12-05

### Changed
- **Portable database location** (`app/user_database.py`): Database now lives alongside the app (`hrv_users.db` in the project folder) for easy copying between machines.
- **Explicit HRV run control** (`app/app.py`): HRV analysis only runs after clicking **Run HRV Analysis**; uploads alone no longer trigger automatic computation.
- **Docs and version** (`README.md`, `docs/Manual.md`, `WARP.md`, `app/version_info.py`): Version bumped to 1.8.0 and navigation notes updated for the new workflow.

---

## [1.7.8] - 2025-12-05

### Changed
- **Tab layout** (`app/app.py`): Science tab moved next to References; About, Space Weather, and NOAA tabs remain fully active/visible.
- **Documentation** (`README.md`, `docs/Manual.md`, `WARP.md`): Updated version badges and navigation notes to match the new layout and visibility rules.
- **Version sync** (`app/version_info.py`): Default version updated to 1.7.8 to keep About and headers consistent with the changelog.

---

## [1.7.9] - 2025-12-05

### Changed
- **Profile load performance** (`app/user_database.py`, `app/user_profile_tab.py`, `app/user_management_ui.py`): HRV history queries now fetch only recent records without RR JSON payloads by default, reducing profile load times for large datasets.
- **Version sync** (`app/version_info.py`): Updated default version to align UI badges and About with this release.

---

## [1.7.7] - 2025-12-05

### Added
- **Tab-specific settings persistence** (`app/ui_state_manager.py`, `app/app.py`, `app/circadian_tab.py`): Circadian and SAFTE tabs now remember per-user configurations for the current session, rehydrating sliders and selectors when switching users or rerunning the app.

### Changed
- **Welcome/About auto-versioning** (`app/version_info.py` consumers): UI badges now source version numbers directly from the latest changelog entry to keep the welcome header and About tab synchronized with releases.

---

## [1.7.6] - 2025-12-05

### Added
- **Active user context bridge** (`app/app.py`, `app/circadian_tab.py`): The app now fetches the active astronaut’s demographics, chronotype, and latest exploration medical record once per rerun and shares it across mission tabs.
- **Profile-aware scenario sync** (`app/circadian_tab.py`): New **Align with active profile** button maps user chronotype/mission profile to light schedules, shift cadence, and model presets.

### Changed
- **SAFTE/Fatigue tab** (`app/app.py`): Inputs auto-populate age, sex, chronotype offset, sleep debt, and work cadence from the active profile. A sync button lets operators refresh values after editing NASA logs.
- **Documentation** (`README.md`, `docs/Manual.md`): Added guidance for the new profile sync workflows and updated the roadmap to mark the feature complete.

### Fixed
- **Pytest warning cleanup** (`app/statistical_analysis.py`, `tests/test_comprehensive_modules.py`): Renamed `TestType` to `StatisticalTestType` so pytest no longer attempts to collect it as a test class.

---

## [1.7.5] - 2025-12-05

### Added
- **Circadian scenario builder** (`app/circadian_tab.py`): Moved every configuration control from the global sidebar into the Circadian tab, added a batched form with an explicit **Apply scenario** button, and introduced a preset vault (up to five saved schedules per session).

### Changed
- **Circadian documentation** (`README.md`, `docs/Manual.md`, `WARP.md`): Roadmap now marks the relocation task as complete, manuals describe the new workflow, and Phase 3 lists SAFTE settings as the next configuration refactor target.

---

## [1.7.4] - 2025-12-05

### Added
- **Clinical assessment preview panel** (`app/user_profile_tab.py`): New Preview button summarizes ESS, KSS, Samn-Perelli, and VAS scores plus context before saving so crews can validate entries without hitting the database.

### Changed
- **Clinical assessment forms batched**: Epworth, Samn-Perelli, Karolinska, and VAS controls now live inside Streamlit forms. Slider adjustments no longer trigger full reruns, which keeps the Clinical Profile tab responsive even on lower-tier CPUs.
- **Debounced submissions**: A shared 0.8 s debounce guard prevents duplicate clinical assessments and exploration medical record entries when users double-click or multiple tabs submit simultaneously.

---

## [1.7.3] - 2025-12-04

### Added
- **HRV Results Caching System** (`app/hrv_cache.py`): Multi-layer caching for major performance gains
  - Hash-based cache keys using data fingerprints (size, first/last values, statistics)
  - Session state caching survives Streamlit reruns without recomputation
  - Automatic cache invalidation when data or settings change
  - `ComputationState` tracking to skip redundant computations entirely
- **Parallel Windowed Analysis**: Automatic parallel processing for multiple datasets
  - Uses ThreadPoolExecutor when multiple datasets are uploaded
  - Automatically enabled for systems with 4+ CPU cores
  - 2-4x faster when processing multiple datasets simultaneously
  - Falls back to sequential processing for single datasets or low-core systems
- **Process Priority Optimization**: Sets high priority for Python process on startup
  - Uses psutil to boost process priority (if available)
  - Windows: HIGH_PRIORITY_CLASS
  - Linux/Mac: nice value -10 (requires appropriate permissions)
  - 5-15% overall performance improvement
- **Performance Optimization Guide**: Comprehensive documentation
  - `docs/PERFORMANCE_OPTIMIZATION.md`: Technical deep-dive
  - `PERFORMANCE_OPTIONS.md`: Quick reference for users
  - Installation instructions for Numba and psutil
  - System-level optimization recommendations

### Changed
- **Upload Section Performance**: Files now cached in session state with hash-based invalidation
  - Files only re-parsed when content actually changes (hash comparison)
  - Eliminates repeated file parsing on tab switches and UI interactions
  - Automatic cleanup of stale cache entries when files are removed
- **Cleaning Performance**: `clean_rr_intervals()` results now cached
  - Cache key combines data hash + settings hash
  - Cache hit skips entire cleaning computation loop
  - Progress indicators show "Loading cached results..." when using cache
- **Computation State Tracking**: Smart detection of when recomputation is needed
  - Tracks uploaded files hash + analysis settings hash
  - Skips cleaning/windowed/comprehensive computations when data unchanged
  - Reduces redundant work on every Streamlit rerun

### Fixed
- **FutureWarning**: Fixed deprecated pandas `fillna()` downcasting behavior
  - Updated `artifact_flag` column handling to use `.infer_objects(copy=False)`
  - Eliminates console warning spam during time series visualization
- **Repeated Cleaning Operations**: Addressed root cause of slow app responsiveness
  - Cleaning was running on every user interaction (tab switch, slider move, etc.)
  - Now only runs when data or settings actually change

### Performance Impact
- **Typical speedup**: 5-10x faster on subsequent interactions after initial load
- **Parallel processing**: 2-4x faster when processing multiple datasets
- **With Numba installed**: Additional 2-5x speedup for advanced metrics (entropy, DFA)
- **Total potential gain**: 10-20x faster with all optimizations enabled
- **Memory**: Cache uses ~2-5% additional session state memory
- **Cache stats**: Available via Performance Settings sidebar button

### Recommendations
- **Install Numba**: `pip install numba` for 2-5x additional speedup on advanced metrics
- **Install psutil**: `pip install psutil` for better CPU detection and process priority
- **See**: `PERFORMANCE_OPTIONS.md` for quick setup guide

---

## [1.7.2] - 2025-12-04

### Added
- **Multi-User Sessions Expanded**: Support increased from 7 to 13 concurrent user sessions
  - Optimized for longitudinal study groups and research cohorts
  - Per-user calculation caching with improved memory management
  - Module version updated to 1.1.0

- **CPU Optimization Module**: New `app/cpu_optimization.py` for non-GPU systems
  - Smart CPU detection (cores, frequency, memory, performance tier)
  - Cross-platform support (Linux, macOS, Windows)
  - Automatic performance tier classification (low/medium/high)
  - Adaptive algorithm selection based on hardware capabilities

- **Optimized HRV Algorithms**: CPU-only performance enhancements
  - `compute_time_domain_fast()`: Vectorized time-domain metrics with reduced allocations
  - `compute_entropy_fast()`: Chunked entropy calculation (O(n) vs O(n²) for large arrays)
  - `compute_poincare_fast()`: Minimal allocation Poincaré analysis
  - `compute_dfa_fast()`: Segment-batched DFA with vectorized fluctuation
  - `compute_psd_fast()`: Optimized FFT with linear interpolation
  - `compute_hrv_fast()`: Comprehensive HRV with adaptive algorithm selection
  - `compute_windowed_hrv_fast()`: Adaptive windowed analysis with limits

- **Auto-Tuning Performance Settings**: Settings automatically adjust to hardware
  - "Auto (Recommended)" preset detects CPU and applies optimal settings
  - Visual CPU tier indicator in sidebar (🟢 High / 🟡 Medium / 🔴 Low)
  - New settings: `max_windows`, `use_fast_entropy`
  - Optional Numba JIT compilation support when available
  - Optional psutil integration for detailed CPU information

### Changed
- **Performance Settings UI**: Now shows detected CPU tier and auto-tunes defaults
  - Fast entropy mode enabled by default for low/medium CPUs
  - Window limits adjusted based on CPU performance tier
  - Memory optimization enabled by default for non-high-tier CPUs
- `performance_utils.py` updated to v1.1.0 with CPU detection integration

### Technical
- Added optional dependencies: `psutil` (CPU detection), `numba` (JIT compilation)
- All optimized functions maintain API compatibility with original implementations
- Subsample-based entropy for arrays >2000 samples on low-end CPUs

---

## [1.7.1] - 2025-12-03

### Changed
- **Performance Optimizations**: Major improvements to app responsiveness
  - `get_database()` now uses `@st.cache_resource` for singleton caching
  - Added `get_cached_user_list()` with 30-second TTL to avoid DB queries on rerun
  - User login dropdown uses cached data; full profile fetched only on selection
  - Multi-user session manager now cached with `@st.cache_resource`
  - i18n translation functions optimized with fast-path dictionary lookups
  - Added `@st.fragment` decorator to clinical assessment forms (ESS, KSS, Samn-Perelli)
  - NASA Nutrition Calculator and Medical Record forms now use partial reruns
  - Loading spinners added for assessment history and HRV data queries
  - **Space Weather Tab**: HRV-Kp correlation now requires explicit button click instead of auto-compute
  - Weather covariates checkbox defaults to unchecked for faster tab loading
  - `fetch_open_meteo_hourly()` cache decorator now has `show_spinner=False`
- **Fast Mode Enabled by Default**: All performance settings now default to fastest options
  - Minimal mode ON by default (skip heavy plots, limit datasets)
  - Skip Gauges, Frequency overlay, Poincaré, Spectrogram all ON by default
  - Max windows reduced from 1500 to 500
  - Step size increased from 1min to 2min for fewer windows
  - Performance preset defaults to "Fast (Low CPU)" instead of "Balanced"
  - Max plot points reduced from 2000 to 1000
  - Max dataframe rows reduced from 500 to 200

### Fixed
- **FutureWarning**: Fixed deprecated `pd.to_numeric(errors='ignore')` in SWPC and DONKI data fetchers
- Reduced unnecessary full page reruns when interacting with form widgets
- Eliminated repeated database initialization on every Streamlit rerun
- User list queries no longer block UI during page refresh

### Requirements
- Streamlit minimum version updated to 1.37 (required for `@st.fragment` support)

---

## [1.7.0] - 2025-12-03

### Added
- **Rebrand**: Physiological Laboratory → Mission Control - Flight Surgeon across UI, docs, metadata, and automation.

- **Exploration Medical Record**: NASA-style mission log stored in `medical_history`
  - Mission profile/day, habitat, EVA clearance, radiation dose, and space-weather alerts
  - Behavioral health, confinement stress, hydration, and countermeasure adherence tracking
  - Tabular history for 22-day isolation campaigns with JSON export for statistics

- **Polar AccessLink VO₂max Sync**: Optional integration with Polar Flow
  - Environment variable configuration (`POLAR_ACCESSLINK_TOKEN`, `POLAR_ACCESSLINK_USER_ID`)
  - One-click VO₂max fetch inside NASA Nutrition calculator
  - Exercise energy expenditure now compensates MET values using VO₂max-derived factors

- **Clinical Profile UI Tab**: New "🏥 Clinical Profile" tab in User Profile
  - NASA Nutrition Calculator with real-time BMR/TDEE/hydration calculations
  - Body composition entry form (body fat%, lean mass, circumferences)
  - Medical history summary view
  - Profile completeness indicators with missing field alerts
  - Exercise type selection with configurable duration (default 2 hours)

- **Multi-User Session Management**: Support for up to 7 concurrent users
  - New module: `app/multi_user_session.py`
  - User session tracking with quick-switch capability
  - Per-user calculation caching
  - Sessions tab in User Profile for management
  - `get_active_user_context()` for tabs to access user settings
  - `get_all_active_users()` for group analysis preparation

- **Multi-User & Longitudinal Study Roadmap** (see WARP.md):
  - Baseline + 22 measurements longitudinal tracking (planned)
  - Intra-subject analysis: within-individual change detection (planned)
  - Inter-subject analysis: between-group comparisons (planned)
  - Group × Time interaction effects (planned)

- **Spanish Language Support (i18n)**: Full bilingual support for clinical assessments
  - Colombian-validated translations for clinical scales (ESE-VC, KSS)
  - Escala de Somnolencia de Epworth (Chica-Urzola et al., 2007)
  - Escala de Somnolencia de Karolinska (Velásquez-Paz et al., 2022)
  - Escala de Fatiga de Samn-Perelli (aviation standards)
  - Language selector in User Profile settings
  - Automatic language sync when user logs in
  - New module: `app/i18n.py`

- **Comprehensive Clinical Profile Module**: Astronaut-grade physiological assessment
  - **Extended Anthropometrics**: Body composition analysis
    - Body fat %, lean mass, muscle mass, bone mass, water %
    - Circumference measurements (waist, hip, neck, chest, arm, thigh, calf)
    - Skinfold measurements for caliper-based body fat
    - US Navy body fat estimation method
    - Waist-to-hip and waist-to-height ratios
    - Visceral fat level tracking
  
  - **Basal Metabolic Rate Calculations**:
    - Mifflin-St Jeor equation (gold standard, ADA recommended)
    - Harris-Benedict equation (for comparison)
    - Katch-McArdle equation (when lean mass known)
    - VO2max-adjusted calculations
  
  - **NASA-Based Nutrition Requirements** (JSC67378):
    - Daily water: 32 mL/kg body weight minimum (2500 mL/day floor)
    - Activity-adjusted hydration with exercise add-ons
    - Macronutrient ratios: 15% protein, 30% fat, 55% carbs
    - Protein: 1.2-1.8 g/kg body mass
    - Extra 500 kcal for EVA/intense activities
  
  - **Exercise Energy Expenditure**:
    - MET-based calorie calculations for 15+ exercise types
    - Astronaut-specific exercises (ARED, CEVIS, T2)
    - Configurable duration (default: 2 hours)
    - Activity factor multipliers (PAL 1.2-2.0)
  
  - **Complete Medical History Tracking**:
    - Cardiovascular, respiratory, metabolic conditions
    - Neurological, musculoskeletal, psychiatric history
    - Allergies (drug, environmental, food, latex)
    - Surgical history, family history
    - Current medications and supplements
    - Lifestyle factors (tobacco, alcohol)
    - Cardiovascular risk factor summary
  
  - **Laboratory Data Management**:
    - Complete Blood Count (CBC/Hemogram)
    - Comprehensive Metabolic Panel
    - Lipid Panel with calculated ratios
    - Thyroid function tests
    - Iron studies and vitamins
    - Inflammatory markers
    - Urinalysis with microscopy
    - eGFR calculation (CKD-EPI 2021 race-free equation)
  
  - New module: `app/clinical_profile.py`

- **Database Schema Expansion**: New tables for clinical data
  - `body_composition` - Extended anthropometric measurements
  - `medical_history` - Comprehensive medical antecedents (JSON storage)
  - `lab_cbc` - Complete blood count results
  - `lab_chemistry` - Blood chemistry/metabolic panel
  - `lab_urinalysis` - Urinalysis results
  - `physiological_calcs` - Cached calculation results
  - Language preference field in user profiles

### Changed
- User Profile tab now supports language preference (EN/ES)
- Clinical scales render with translated strings based on user language
- Database schema version updated with migration support
- GPT-5.2 high reasoning workflow now lives inside the Export tab and consumes the rendered statistical report payload.

### Technical
- Database connection pooling with persistent connections
- WAL mode for concurrent database access
- Optimized user registration (single-transaction username check + creation)
- Added indices for body composition and laboratory tables

### References
- Mifflin MD et al. Am J Clin Nutr. 1990;51(2):241-247
- NASA JSC67378 Exploration Nutrition Requirements
- NASA-STD-3001 Water Requirements
- Inker LA et al. N Engl J Med. 2021;385(19):1737-1749 (CKD-EPI 2021)

---

## [1.6.4] - 2025-12-02

### Added
- **NVIDIA GPU Processing Support**: Hardware acceleration for HRV computations
  - Auto-detection of NVIDIA GPUs (RTX 5070, RTX 4090, RTX 3080, etc.)
  - CUDA-accelerated RMSSD, SDNN, pNN50, FFT PSD, and Poincaré calculations
  - Built-in GPU benchmark with CPU comparison (2-10x speedup on large arrays)
  - GPU settings sidebar panel with enable/disable toggle
  - Automatic fallback to CPU when GPU unavailable
  - New module: `app/gpu_processing.py`

- **Centralized User Profile Tab**: Complete user data management
  - User registration with biometric data (age, height, weight, BMI)
  - Validated clinical scales: ESS (Johns 1991), Samn-Perelli (1982), KSS (Åkerstedt 1990)
  - VAS fatigue/pain assessments with timestamped history
  - Assessment trend charts and longitudinal tracking
  - HRV measurement history linked to user profile
  - Data export/import (JSON format for portability)
  - SQLite database storage with multi-user support
  - New module: `app/user_profile_tab.py`

- **Centralized Logging Infrastructure**: Persistent debug and error logs
  - Rotating file logs in `logs/` directory (auto-created)
  - `logs/app.log` — All application logs (DEBUG level, 10 MB rotating)
  - `logs/errors.log` — Error-only log for critical issues
  - User action audit trail via `log_user_action()`
  - Console + file dual output with consistent formatting
  - New module: `app/logging_config.py`

### Changed
- Sidebar now includes GPU Processing settings (⚡ Performance + 🖥️ GPU)
- User Profile tab added as second tab (after Overview)
- Models can now access centralized user profile data via `get_current_user_data()`
- Updated requirements.txt with GPU installation instructions
- `setup_console_logging()` now integrates with centralized file logging
- Updated `.gitignore` to exclude `logs/` directory

### Fixed
- VO2max input field now accepts 0 (for "unknown - will be estimated")

### Documentation
- Updated `WARP.md` with logging infrastructure, GPU support, and troubleshooting
- Updated `.cursor/rules/agent.mdc` with logging policy and common bug patterns
- Added maintenance checklist and module architecture quick reference

## [1.6.3] - 2025-12-02

### Added
- **No-Data Navigation**: All tabs now accessible without uploading HRV data
  - Space Weather, Circadian, SAFTE, and Biofeedback tabs fully functional without uploads
  - Data-dependent tabs show friendly explanations with example data
- **Enhanced Welcome Experience**: Interactive module cards with availability indicators
- **User-Friendly Examples**: Each data-dependent tab shows reference values and interpretation guides
- **Sidebar Exploration Mode**: Quick-access panel highlighting available features
- **CPU Performance Optimization**: New performance utilities module
  - Configurable performance presets (Fast/Balanced/Quality/Custom)
  - Smart downsampling for plots based on CPU capability
  - DataFrame row limits with feedback
  - Session-state caching with TTL for expensive operations
  - Performance metrics tracking (cache hits, slowest operations)
  - New module: `app/performance_utils.py`

### Changed
- App structure refactored to show tabs immediately on load
- Welcome header now emphasizes modules that work without data
- Getting Started guide expanded with immediate exploration options
- Plot functions now auto-downsample based on performance settings
- Windowed metrics display respects performance row limits

---

## [1.6.2] - 2025-12-01

### Added
- **Space Weather Impact Predictions**: Real-time arrival time calculations for all solar energy categories
  - Photon/X-ray impacts (instantaneous detection)
  - Solar Energetic Particles (SEPs) from GOES proton flux
  - Solar wind plasma with L1→Earth travel time calculation
  - Geomagnetic conditions (Kp/Dst indices)
- **Polar H10 Monitoring Recommendations**: Automatic EKG capture timing guidance based on space weather severity
- **Bogotá Local Time Display**: All arrival times shown in Colombia timezone (UTC-5)
- **Priority Alert System**: Color-coded severity banners with countdown to next impact
- New module: `app/space_weather_impact.py` with complete prediction engine

### Changed
- Space Weather tab now displays impact predictions prominently at the top
- Enhanced severity classification (Quiet → Minor → Moderate → Strong → Severe → Extreme)

---

## [1.6.1] - 2025-11-29

### Added
- **Complete Circadian Module Integration**: All circadian files now in `app/circadian/`
  - **phasetools.py**: Cosinor analysis for phase extraction from time series data
  - **prc.py**: Phase Response Curves (PRC), Intensity Response Curves (IRC), Dosage Response Curves (DRC)
  - **sleep.py**: Two-Process Model of sleep regulation with clustering algorithms
  - **synthetic_data.py**: Generate synthetic wearable data from light schedules
  - **readers.py**: Actiwatch and generic wearable data loading with timestamp alignment
  - **plots.py**: Actogram visualization and stroboscopic plots
- **Removed Future_integrations folder**: All models fully integrated into main app

### Changed
- Circadian module version updated to 1.0.3
- All circadian imports now use `app.circadian.*` namespace
- Cross-platform compatibility verified for Windows and Linux

---

## [1.6.0] - 2025-11-29

### Added
- **Population Norms Tab**: Compare HRV metrics against scientifically validated population norms
  - Age and sex-stratified reference values from Nunan et al. (2010), Ortega et al. (2024), MESA Study
  - Percentile rankings and deviation categories (Very Low → Very High)
  - Full scientific citations with PMID links
- **Blood Pressure Variability (BPV) Module**: Comprehensive BPV analysis
  - Systolic/diastolic SD, CV, ARV (Average Real Variability), SV (Successive Variation)
  - Pulse pressure and MAP calculations
  - Risk assessment based on Parati et al. (2018), Rothwell et al. (2010) thresholds
  - HRV-BPV correlation analysis for autonomic assessment
- **Enhanced Welcome Page**: Professional laboratory branding with quick access
  - Data status panel showing loaded datasets
  - Quick access grid to all analysis modules
  - Getting started guide for new users
  - Contributing modules display (Circadian, SAFTE, HRV Core, ECharts)
- **UI State Manager**: Centralized data availability tracking
  - Conditional compute button enabling/disabling
  - Session persistence for data status
  - Multi-data-type awareness (RR, sleep, ECG, BP)
- **Device Import Reorganization**: Streamlined sidebar interface
  - Polar H10 RR data with professional interface
  - Garmin Vivosmart 5 integration
  - Generic RR file support
  - Unified data normalization pipeline

### Changed
- All tabs now accessible without data upload (navigation-first design)
- Compute buttons disabled until required data is uploaded
- Welcome header uses Streamlit native components for reliable rendering
- Sidebar reorganized with device-specific import sections

---

## [1.5.0] - 2025-11-28

### Added
- **Circadian Physiology Module**: Integrated circadian rhythm simulation with multiple mathematical models (Forger99, Jewett99, Hannay19, Hannay19TP)
- **User Profiles System**: Comprehensive biometric profiles with validated clinical scales (ESS, KSS, PSQI, Samn-Perelli)
- **Docker Support**: Full containerization with PostgreSQL/TimescaleDB for production deployment
- **Professional About Tab**: Complete documentation viewer with version info, changelog, and author details
- **Space Weather Persistence**: NOAA/NASA data stored in database for longitudinal correlation studies

### Changed
- Fixed wake validation logic in circadian models (Bug: `and` → `or` for proper range checking)
- Fixed CLI function calls in circadian module (`read_standard_json` → `load_json`, etc.)
- Improved cross-platform compatibility (Windows/Linux temp paths using `tempfile`)

### Fixed
- Chronic load calculation now uses proper daily average normalization
- Sample entropy range corrected to include all complete templates
- Fusion confidence now uses variance-based coefficient of variation instead of arbitrary scaling

---

## [1.4.0] - 2025-11-15

### Added
- **ECG R-Peak Detection**: Pan-Tompkins algorithm with template matching for research-grade beat detection
- **Multi-Modal Sensor Fusion**: Integration with Oura, WHOOP, Apple Health, Fitbit, and Garmin
- **Long-Term HRV Trending**: Baseline establishment, trend detection, and anomaly alerts
- **Exercise HRV Analysis**: Heart rate recovery (HRR), parasympathetic reactivation, TRIMP calculation
- **ML Predictions**: Atrial fibrillation risk, sudden cardiac death stratification, sleep apnea screening
- **Real-Time BLE Integration**: Live streaming from Polar H10/H9, Garmin HRM-Pro, Wahoo TICKR

### Changed
- Enhanced ECharts visualizations with modern two-ring gauge style
- Improved responsive chart sizing with ResizeObserver

---

## [1.3.0] - 2025-10-20

### Added
- **NOAA Space Weather Dashboard**: Comprehensive solar and geomagnetic data feeds
- **Fatigue Prediction (SAFTE Model)**: Sleep-based cognitive effectiveness modeling
- **Scientific Charts Module**: Publication-ready visualizations with unified physiological timelines
- **Biofeedback Mode**: Real-time coherence training with breathing guides

### Changed
- Reorganized tab structure for better workflow navigation
- Updated gauge builder with ECharts-based modern gauges

---

## [1.2.0] - 2025-09-15

### Added
- **ActiGraph GT3X Integration**: Research-grade accelerometer data import
- **Somfit Pro Integration**: Home sleep testing device support with EDF parsing
- **Publication Export**: APA-formatted tables and LaTeX export for journals
- **AI-Powered Interpretation**: GPT-5 integration for clinical narrative generation

### Changed
- Improved artifact detection algorithms
- Enhanced windowed analysis with configurable parameters

---

## [1.1.0] - 2025-08-01

### Added
- **Garmin Connect Integration**: Bulk export and FIT file support
- **Autonomic Function Tests**: Valsalva ratio, deep breathing E:I, 30:15 standing test
- **Readiness Assessment**: Morning HRV-based training readiness scoring
- **Multi-file Analysis**: Comparative analysis across multiple recordings

### Changed
- Redesigned sidebar configuration
- Improved PSD computation methods (Welch, Periodogram, AR)

---

## [1.0.0] - 2025-07-01

### Added
- **Core HRV Analysis**: Time-domain, frequency-domain, and nonlinear metrics
- **Poincaré Plots**: SD1/SD2 analysis with ellipse visualization
- **Spectrogram View**: Time-frequency analysis of HRV patterns
- **Quality Control**: Artifact detection with threshold-based filtering
- **Space Weather Correlation**: Integration with NASA DONKI and NOAA data
- **Export Functionality**: Markdown, CSV, and JSON export options

### Technical Foundation
- Streamlit-based web interface
- ECharts integration for interactive visualizations
- Modular architecture with separation of concerns
- Comprehensive type hints and documentation

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| 1.6.4 | 2025-12-02 | GPU acceleration (NVIDIA CUDA), centralized user profile, clinical scales |
| 1.6.3 | 2025-12-02 | No-data navigation, enhanced welcome experience, user-friendly examples |
| 1.6.2 | 2025-12-01 | Space weather impact predictions, Polar H10 timing recommendations |
| 1.6.0 | 2025-11-29 | Population norms, BPV analysis, enhanced welcome |
| 1.5.0 | 2025-11-28 | Circadian module, user profiles, Docker |
| 1.4.0 | 2025-11-15 | ECG detection, sensor fusion, ML predictions |
| 1.3.0 | 2025-10-20 | NOAA space weather, SAFTE fatigue model |
| 1.2.0 | 2025-09-15 | ActiGraph, Somfit, publication export |
| 1.1.0 | 2025-08-01 | Garmin, ANS tests, readiness scoring |
| 1.0.0 | 2025-07-01 | Initial release with core HRV analysis |

---

## Roadmap

### Completed (Q4 2025)
- ✅ Population normative database with age/sex stratification
- ✅ Blood Pressure Variability (BPV) integration
- ✅ Circadian rhythm analysis module
- ✅ Docker containerization with TimescaleDB
- ✅ NVIDIA GPU acceleration (RTX 5070/4090/3080)
- ✅ Centralized user profile system with clinical scales (ESS, Samn-Perelli, KSS)
- ✅ CPU performance optimization with presets

### Research-Based Priorities (2025-2026)

*Based on latest peer-reviewed literature (2024-2025):*

#### High Priority (Q1 2026)

| Feature | Scientific Basis | Impact |
|---------|------------------|--------|
| **Multimodal Fatigue ML** | Kim et al. 2025 - HRV+cortisol TabNet (AUC 0.77) | High |
| **Gradient Boosting Fatigue** | Goutham 2025 - LightGBM/XGBoost on WESAD | High |
| **Sleep-Phasic HRV** | Fan et al. 2024 - CAP/NCAP/REM analysis (80% accuracy) | Medium |
| **Edge Computing Mode** | Lavanya et al. 2023 - DL+DWT (99.3% arrhythmia) | Medium |

#### Medium Priority (Q2-Q3 2026)

| Feature | Scientific Basis | Impact |
|---------|------------------|--------|
| **Drowsiness Detection** | AlArnaout et al. 2025 - RF HRV (86% accuracy) | High |
| **Sleep Quality CNN** | Kiliç et al. 2023 - Wearable+survey deep learning | Medium |
| **Syncope Prediction** | Lee et al. 2024 - XGB 3-min advance warning | Medium |
| **Wearable Validation** | Dial et al. 2025 - Oura/WHOOP/Garmin benchmarks | Low |

### Legacy Planned Features
- Advanced nonlinear dynamics (MSE, RQA, Lyapunov)
- Mobile companion app for data collection
- RESTful API for third-party integration

### Under Research (Aerospace Medicine)
- G-tolerance assessment for aerospace applications
- Altitude/hypoxia HRV analysis
- Spatial disorientation markers
- Baroreflex sensitivity from HRV-BPV coherence

---

## Contributors

**Lead Developer & Author:**  
Dr. Diego Leonel Malpica Hincapié, MD  
Aerospace Medicine Specialist  
National University of Colombia

**Circadian Module:**  
Original package by Arcascope (Franco Tavella, Kevin Hannay, Olivia Walch)  
UI updates and integration by Dr. Diego L. Malpica

---

*For detailed feature documentation, see `docs/Manual.md`*
