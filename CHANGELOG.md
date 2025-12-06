# Changelog

All notable changes to the Mission Control - Flight Surgeon are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- GPT-5.1 high reasoning workflow now lives inside the Export tab and consumes the rendered statistical report payload.

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
