# Mission Control - Flight Surgeon

## Author

**Dr. Diego Leonel Malpica Hincapié, MD**  
*Aerospace Medicine Specialist*  
National University of Colombia  
Physiology Instructor, Colombian Aerospace Force  
Contributing to **AsterPhysiology** Research Initiative

[![GitHub](https://img.shields.io/badge/GitHub-strikerdlm%2FHRV-blue?logo=github)](https://github.com/strikerdlm/HRV)
[![Version](https://img.shields.io/badge/Version-1.8.0-green)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![CUDA](https://img.shields.io/badge/CUDA-Optional-76B900?logo=nvidia)](https://developer.nvidia.com/cuda-toolkit)
[![i18n](https://img.shields.io/badge/i18n-EN%20%7C%20ES-blue)](app/i18n.py)
[![Last Updated](https://img.shields.io/badge/Updated-2025--12--05-blue)](CHANGELOG.md)

---

Mission Control - Flight Surgeon is a comprehensive, research-grade Heart Rate Variability (HRV) operations console that blends circadian simulation, blood-pressure variability, population norms, and real-time space weather intelligence from NOAA SWPC and NASA DONKI. It is built for clinicians, researchers, and aerospace medicine specialists who need transparent, reproducible physiological metrics with publication-ready exports.

**NEW in v1.8.0**: HRV analysis runs only when you click **Run HRV Analysis**, and the database now sits alongside the app (`hrv_users.db`) for easy copy/portability.

**NEW in v1.7.9**: Profile HRV history now loads only the latest records (without RR payloads) for much faster profile switching.

**NEW in v1.7.8**: Science tab now lives next to References; About, Space Weather, and NOAA tabs stay fully visible, and version badges remain synced with the changelog.

**NEW in v1.7.7**: Per-user tab settings persistence for Circadian and SAFTE tabs—your scenarios and fatigue inputs reload automatically when switching users or rerunning the app.

**NEW in v1.7.0**: Astronaut-grade clinical profiles with NASA nutrition calculations, Spanish language support (Colombian-validated scales), extended anthropometrics, and laboratory data tracking.

## 🚀 Quick Start

### Prerequisites

- Python 3.12 (recommended) or 3.10+
- Conda (for environment management) or pip
- pip package manager

### Installation

#### Option 1: Using Conda (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/hrv-space-weather.git
cd hrv-space-weather

# Activate the conda environment
conda activate hrv-py312

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app/app.py
```

#### Option 2: Using Virtual Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/hrv-space-weather.git
cd hrv-space-weather

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app/app.py
```

The app will open in your default browser at `http://localhost:8501`.

### Your First Analysis (5 Minutes)

1. **Prepare your data**: Create a text file with one RR interval (in milliseconds) per line:
   ```
   1027
   1007
   991
   1010
   1020
   ...
   ```
   Name it with a timestamp for automatic time alignment: `2025-11-06 00-43-42.txt`

2. **Upload**: Click "Browse files" in the sidebar and select your RR file(s)

3. **Explore tabs**: Start with **Overview** for summary statistics, then explore **Gauges** for visual benchmarks

4. **Export**: Go to **Export** tab to download a comprehensive Markdown report

### Polar AccessLink (optional VO2max sync)

Mission Control - Flight Surgeon can pull VO2max estimates from Polar Flow via the AccessLink API for higher-fidelity exercise compensation:

1. Register an application in the [Polar AccessLink program](https://www.polar.com/accesslink-api/) and complete the OAuth handshake to obtain a bearer token.
2. Set environment variables (never commit secrets):
   - `POLAR_ACCESSLINK_TOKEN` — bearer token returned by AccessLink.
   - `POLAR_ACCESSLINK_USER_ID` — numeric user identifier reported by Polar Flow.
3. Restart the app and open **User Profile → NASA Nutrition**. A **Use Polar value** toggle will appear when credentials are available.

If the env vars are omitted the calculator falls back to the VO2max stored in the user profile.

---

## 🚀 Explore Without Data

The app is fully navigable **without uploading HRV data**. These features work immediately:

| Module | What You Can Do |
|--------|-----------------|
| 🌍 **Space Weather** | Fetch live NASA/NOAA data, see CME arrival predictions, get Polar H10 timing |
| ☀️ **Circadian** | Simulate circadian rhythms with different light schedules |
| 😴 **SAFTE/Fatigue** | Model how sleep debt affects cognitive performance |
| 🫀 **Biofeedback** | Try the paced breathing demo |

All other tabs show **example data** and **reference values** to help you understand what's available before uploading your own recordings.

---

## 📋 Features Overview

| Feature | Description |
|---------|-------------|
| **Time-Domain Metrics** | SDNN, RMSSD, pNN50, Mean HR, CVNN, and more |
| **Frequency-Domain Analysis** | VLF/LF/HF power, normalized units, LF/HF ratio via Welch, Periodogram, or AR methods |
| **Nonlinear Metrics** | Poincaré SD1/SD2, DFA α1/α2, Sample/Approximate Entropy |
| **Heart Rate Fragmentation** | PIP, IALS, PSS per PROOF-AF methodology |
| **Geometric Metrics** | HRV Triangular Index, TINN, Baevsky Stress Index |
| **Population Norms** | Age/sex-stratified comparison against Nunan et al., Ortega et al., MESA Study data |
| **Blood Pressure Variability** | BPV metrics (SD, CV, ARV, SV) with HRV-BPV correlation analysis |
| **Circadian Physiology** | Forger99, Jewett99, Hannay19 models with ESRI and light schedule simulation |
| **Sliding Window Analysis** | Configurable windows with deviation detection and anomaly episodes |
| **Autonomic Function Tests** | Valsalva ratio, Deep breathing E:I response, 30:15 standing ratio |
| **Readiness Scoring** | Kubios-style parasympathetic index with historical baseline comparison |
| **Space Weather Correlation** | NOAA Kp, Dst, F10.7, solar wind, X-ray flux with lag-aware correlations |
| **Space Weather Impact Predictions** | Exact arrival times for photons, SEPs, solar wind plasma, with Polar H10 timing recommendations |
| **NASA DONKI Integration** | Flares, CMEs, geomagnetic storms, radiation belt enhancements |
| **Fatigue Prediction** | SAFTE biomathematical model for cognitive performance |
| **HRV Biofeedback** | Real-time coherence training with paced breathing |
| **CPU Performance Mode** | Adjustable presets (Fast/Balanced/Quality) with smart downsampling |
| **GPU Acceleration** | NVIDIA CUDA support (RTX 5070/4090/3080) for heavy computations |
| **User Profile System** | Centralized biometrics, clinical scales (ESS, Samn-Perelli, KSS), history tracking |
| **Active User Context Sync** | Circadian and SAFTE tabs auto-fill age, chronotype, sleep debt, and mission schedules from the selected profile with a single sync button |
| **Clinical Profiles** | Astronaut-grade assessment: BMR, TDEE, NASA nutrition, body composition |
| **Exploration Medical Record** | NASA isolation/mission log with EVA, radiation, stress, and behavioral metrics |
| **Polar AccessLink VO2 Integration** | Optional VO2max sync for exercise compensation via AccessLink API |
| **Multi-Language** | English + Spanish (Colombian-validated scales: ESE-VC, KSS-CO) |
| **Laboratory Tracking** | CBC/Hemogram, Blood Chemistry, Urinalysis with normal ranges |
| **Multi-Device Import** | Polar H10, Garmin Vivosmart 5, ActiGraph GT3X, Somfit Pro |
| **Docker Deployment** | Containerized with PostgreSQL/TimescaleDB for production environments |
| **AI Interpretation** | GPT-5.1 high-reasoning analysis with scientific citations |
| **Publication Export** | APA 7th edition formatted reports, LaTeX tables, CSV/JSON data |

---

## 🗺️ Development Roadmap (v2.0)

### Current Sprint (December 2025)

| Priority | Feature | Status |
|----------|---------|--------|
| ✅ DONE | Multi-user sessions (1-13 concurrent) | Complete |
| ✅ DONE | CPU optimization for non-GPU systems | Complete |
| ✅ DONE | Smart CPU auto-detection & tuning | Complete |
| ✅ DONE | Clinical Profile UI visualization | Complete (batched forms + debounced saves) |
| ✅ DONE | Move Circadian settings to tab | Complete |
| ✅ DONE | Active user context sync across mission tabs | Complete (Circadian + SAFTE auto-populate) |
| 🟢 LOW | Per-tab settings persistence | Planned |

**Best next task:** Implement tab-specific settings persistence so mission planners can capture separate Circadian, SAFTE, and NOAA configurations per astronaut.

### Planned Features (Q1 2026)

#### Longitudinal Study Support
- **Baseline + 22 Measurements**: Track subjects over time (T0 → T21)
- **Intra-Subject Analysis**: Within-individual change detection, trend analysis
- **Inter-Subject Analysis**: Between-group comparisons, effect sizes
- **Mixed-Effects Models**: Random subject intercepts, repeated measures

#### Group Analysis Framework
```
Study Design:
├── Control Group (n subjects)
│   └── Each subject: T0, T1, T2, ... T21
└── Intervention Group (n subjects)
    └── Each subject: T0, T1, T2, ... T21
```

**Analysis Types**:
- Per-subject time series with individual baselines
- Per-group aggregated statistics at each timepoint  
- Group × Time interaction effects
- Responder vs non-responder classification
- Effect size calculations (Cohen's d, η²)

> **For detailed roadmap**: See [WARP.md](WARP.md) section "🚀 DEVELOPMENT ROADMAP"

---

## 📁 Input Data Format

### Polar-Style RR Text Files

The app accepts text files with one RR interval per line in **milliseconds**:

```
1027
1007
991
1010
```

**Filename convention**: `YYYY-MM-DD HH-MM-SS.txt` (e.g., `2025-11-06 00-43-42.txt`)
- The timestamp is parsed to align HRV windows with space weather data
- Timezone is assumed GMT-5 (adjustable)
- Values outside 300–2000 ms are automatically filtered

### Garmin Data Sources

1. **Wellness Export ZIP**: Download from Garmin Connect → Account Settings → Export Wellness Data
2. **FIT Files**: Export individual activities from Garmin Connect web
3. **API Access**: Configure `GARMIN_EMAIL` and `GARMIN_PASSWORD` in `.env`

### ActiGraph GT3X Files

1. **GT3X Binary**: Native format from ActiGraph devices (GT3X, GT3X+, GT9X Link)
2. **AGD Database**: ActiLife processed epoch data
3. **CSV Export**: Activity counts or raw acceleration from ActiLife

### Somfit Pro Files

1. **EDF/EDF+**: European Data Format from Compumedics Profusion Nexus360
2. **XML Annotations**: Sleep staging scores from Profusion
3. **CSV Export**: Summary data exports

### Sample Data Structure

```
project/
├── 2025-11-06 00-43-42.txt    # Morning recording
├── 2025-11-06 18-30-00.txt    # Evening recording
├── garmin_export.zip          # Optional Garmin data
└── .env                       # API keys (not committed)
```

---

## 🖥️ Application Tabs

### Overview Tab
- Dataset metadata: beat count, duration, mean HR, artifact percentage
- Respiratory rate estimate from HF spectral peak
- Summary table with green/yellow/red deviation flags

### Time Series Tab
- RR intervals and heart rate over time
- QC overlays: cleaned series (green), flagged artifacts (red)
- Interactive zoom and pan

### Frequency Tab
- Power Spectral Density (PSD) with VLF/LF/HF band highlighting
- Methods: Welch (default), Periodogram, AR (Yule-Walker)
- Band power comparison across datasets

### Nonlinear Tab
- Poincaré plot with SD1/SD2 ellipse
- DFA scaling exponents (α1: short-term, α2: long-term)
- Entropy metrics visualization

### Spectrogram Tab
- Time-frequency heatmap showing spectral dynamics
- Track HF (breathing) and LF (baroreflex) power evolution
- Useful for identifying non-stationary segments

### Windowed Tab
- Sliding-window metrics (default: 5-min window, 1-min step)
- Deviation detection with configurable z-score thresholds
- Anomaly episode timeline with contiguous run detection

### Metrics Tab
- Complete table of all computed metrics across domains
- Advanced analytics: fragmentation, PRSA, symbolic dynamics, multifractal DFA
- Covariate-adjusted values when patient profile is configured

### ANS Function Tests Tab
- **Valsalva Ratio**: Phase II (strain) vs Phase IV (recovery)
- **Deep Breathing**: E:I difference and ratio across paced breathing cycles
- **30:15 Ratio**: Orthostatic response after standing

### Readiness Tab
- Parasympathetic index from HF, RMSSD, pNN50, SD1
- Historical baseline comparison (requires ≥7 sessions)
- Kubios-style categories: VERY LOW / LOW / NORMAL / HIGH

### Gauges Tab
- 30+ metric gauges with clinical reference ranges
- Two-ring design with color-coded zones (green/yellow/red)
- Based on published normative data (Nunan 2010, Shaffer 2017, PROOF-AF 2025)

### Unified Timeline Tab
- Time-synchronized view of all physiological metrics
- ML pattern detection: anomalies, trends, change points
- Correlation matrix heatmap

### Biofeedback Tab
- Real-time HRV streaming (simulated or from device)
- Paced breathing guide with configurable breath rate
- Coherence score tracking

### Fatigue Tab
- SAFTE model for cognitive performance prediction
- Sleep schedule and work schedule inputs
- Risk assessment with factor breakdown
- Recommendations based on fatigue level
- One-click **Sync with active profile** button pulls age, chronotype, sleep debt, and mission schedule directly from the selected astronaut's medical log

### Space Weather Tab
- **Impact Predictions**: Exact arrival times for all energy categories in Bogotá (UTC-5)
  - Photon/X-ray events (instantaneous)
  - Solar Energetic Particles (SEPs)
  - Solar wind plasma (L1→Earth travel time calculated)
  - Geomagnetic conditions (Kp/Dst)
- **Polar H10 Recommendations**: Automatic EKG timing guidance based on event severity
- Live Kp index, solar flux, solar wind parameters
- SpaceWeatherLive snapshot with CME/flare data
- Lag-aware correlations (0–72h) with HRV metrics
- Partial correlations controlling for weather covariates

### NOAA Space Tab
- Comprehensive NOAA SWPC data feeds
- Interactive gauges for all space weather metrics
- Batch correlation analysis across multiple parameters
- Feature matrix builder for predictive modeling

### Export Tab
- Markdown report with all metrics and interpretations
- CSV/JSON data export
- LaTeX tables for publications
- GPT-5.1 AI interpretation (requires API key)

### Circadian Physiology Tab
- Multiple mathematical models: Forger99, Jewett99, Hannay19, Hannay19TP
- Light schedule generation (Regular, Shift Work, Slam Shift, Social Jetlag)
- Entrainment Signal Regularity Index (ESRI) calculation
- Phase and amplitude trajectory visualization
- Integrated scenario builder with in-tab presets and batched submissions (no sidebar required)
- **Align with active profile** auto-populates light schedules and model selections based on the active user's chronotype, mission profile, and NASA medical history
- Based on Arcascope circadian package (Tavella, Hannay, Walch)

### Population Norms Tab
- Compare HRV metrics against published population norms
- Age and sex-stratified reference values
- Sources: Nunan et al. (2010), Ortega et al. (2024), MESA Study, Task Force 1996
- Percentile rankings and deviation categories
- Full scientific citations with PMID links

### BPV Analysis Tab
- Blood Pressure Variability metrics: SD, CV, ARV, SV
- Pulse pressure and MAP calculations
- Risk assessment based on clinical literature
- HRV-BPV correlation for autonomic assessment
- References: Parati et al. (2018), Rothwell et al. (2010), Saren et al. (2024)

### About Tab
- Author information and professional profiles
- Contributing authors (Circadian: Arcascope; SAFTE: IBR/USAF)
- Version history and changelog
- Complete user manual (docs/Manual.md)
- Scientific references and citations

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# OpenAI API (for GPT interpretation)
OPENAI_API_KEY=sk-...

# NASA DONKI (optional, has generous free tier)
NASA_API_KEY=DEMO_KEY

# Garmin Connect (for API access)
GARMIN_EMAIL=your.email@example.com
GARMIN_PASSWORD=your_password

# AccuWeather (for weather covariates)
ACCUWEATHER_API_KEY=your_key
```

⚠️ **Security**: Never commit `.env` to version control. Ensure `.gitignore` includes `.env`.

### Sidebar Settings

| Setting | Default | Description |
|---------|---------|-------------|
| **Window size** | 5 min | Sliding window duration for windowed analysis |
| **Step size** | 1 min | Window overlap/step |
| **Min RR count** | 60 | Minimum beats per window |
| **QC method** | threshold_median | Artifact detection algorithm |
| **Max deviation** | 0.2 | Artifact threshold (20% deviation) |
| **Median window** | 11 | Rolling median window for QC |
| **PSD method** | Welch | Spectral estimation method |

---

## 📊 Example Workflow

### Clinical Autonomic Assessment

```
1. Patient preparation: 5-min rest, supine position, quiet room
2. Record: Start Polar H10 recording, save RR intervals
3. Upload: Load file into app
4. QC Review: Check Time Series tab for artifacts (<5% acceptable)
5. Metrics: Review Metrics tab for comprehensive values
6. Autonomic Tests: Perform Valsalva, deep breathing protocols
7. Export: Generate report for clinical documentation
```

### Research Protocol

```
1. Define cohort: Age, sex, health status
2. Standardize: Same time-of-day, posture, breathing instructions
3. Record: ≥5 min per session, label files with subject ID
4. Process: Upload batch of files
5. Analyze: Use windowed metrics for time-varying analysis
6. Correlate: Enable space weather correlation if studying solar effects
7. Statistics: Export CSV for external statistical packages
8. Publish: Use LaTeX export for manuscript tables
```

### Personal Tracking

```
1. Morning routine: 1-5 min HRV recording immediately upon waking
2. Consistent setup: Same position, before coffee/exercise
3. Upload daily: Build 7+ day baseline
4. Check Readiness: Monitor parasympathetic index trend
5. Adjust training: Reduce intensity when readiness is LOW
```

---

## 🔬 Space Weather Correlation Analysis

### Scientific Background

Geomagnetic storms and solar activity have been associated with cardiovascular effects in epidemiological studies:

- **Kp Index**: Higher geomagnetic activity correlates with reduced HRV in some cohorts
- **Solar Wind**: Speed/pressure variations may precede autonomic changes
- **F10.7 Flux**: Proxy for overall solar activity with long-term health correlations

### Using the Correlation Tools

1. **Configure lag range**: Start with 0–72h, step 6h
2. **Enable weather covariates**: Control for temperature, humidity, pressure
3. **Review FDR-adjusted q-values**: Multiple comparison correction
4. **Interpret cautiously**: Effect sizes are typically small (r = 0.1–0.3)

### Feature Matrix Builder

The NOAA Space tab includes an advanced feature matrix builder:

1. Generate a lagged feature matrix combining HRV metrics with solar predictors
2. Rank predictors by correlation strength with minimum sample guardrails
3. Train quick linear models to explore relationships
4. Download correlations, rankings, and coefficients for further analysis

---

## 📚 References

### Core HRV Standards

- Task Force of ESC/NASPE (1996). Heart rate variability standards. *Circulation, 93*(5), 1043-1065. [PMID: 8598068](https://pubmed.ncbi.nlm.nih.gov/8598068/)
- Shaffer, F., & Ginsberg, J. P. (2017). An overview of HRV metrics and norms. *Front Public Health, 5*, 258. [PMID: 29034226](https://pubmed.ncbi.nlm.nih.gov/29034226/)
- Nunan, D., et al. (2010). Normal values for short-term HRV in healthy adults. *Pacing Clin Electrophysiol, 33*(11), 1407-1417. [PMID: 20663071](https://pubmed.ncbi.nlm.nih.gov/20663071/)
- Quigley, K. S., et al. (2024). Publication guidelines for HR and HRV. *Psychophysiology, 61*(4), e14604.

### Population Norms

- Ortega, E., et al. (2024). The Pulse of Singapore: Short-Term HRV Norms. *J Gen Intern Med, 39*(1), 101-108. [PMID: 37755550](https://pubmed.ncbi.nlm.nih.gov/37755550/)
- O'Neal, W. T., et al. (2016). MESA Study HRV normative values. *Am J Cardiol*. [PMID: 27396499](https://pubmed.ncbi.nlm.nih.gov/27396499/)

### Blood Pressure Variability

- Parati, G., et al. (2018). BPV: clinical relevance and application. *J Clin Hypertens, 20*(7), 1133-1137. [PMID: 29927042](https://pubmed.ncbi.nlm.nih.gov/29927042/)
- Rothwell, P. M., et al. (2010). Visit-to-visit variability of blood pressure and stroke risk. *Lancet, 375*(9718), 895-905. [PMID: 20226988](https://pubmed.ncbi.nlm.nih.gov/20226988/)
- Saren, J., et al. (2024). Blood pressure variability and health outcomes in adults 65+. *Age and Ageing*. [DOI: 10.1093/ageing/afae262](https://doi.org/10.1093/ageing/afae262)

### Circadian Physiology

- Tavella, F., Hannay, K., & Walch, O. (2023). Arcascope/circadian. Zenodo. [DOI: 10.5281/zenodo.8206871](https://doi.org/10.5281/zenodo.8206871)
- Forger, D. B., et al. (1999). A simpler model of the human circadian pacemaker. *J Biol Rhythms, 14*(6), 532-537.

### Space Weather & Physiology

- Vieira, C. L. Z., et al. (2022). Geomagnetic disturbances reduce HRV. *Sci Total Environ, 839*, 156312.
- Alabdulgader, A., et al. (2018). Long-term HRV responses to solar activity. *Sci Rep, 8*(1), 2663.
- Vencloviene, J., et al. (2020). Solar wind and AMI risk. *Int J Environ Res Public Health, 17*(9), 3153.

### Fragmentation & Arrhythmia Risk

- PROOF-AF Study (2025). HRF and DFA α1 predict atrial fibrillation. *EHJ Open, 5*(1), oeaf030.

---

## 🛠️ Development

### Project Structure

```
HRV/
├── app/
│   ├── app.py                      # Main Streamlit application
│   ├── hrv_core.py                 # Core HRV computation functions
│   ├── circadian/                  # Circadian rhythm simulation module
│   │   ├── __init__.py             # Module exports
│   │   ├── models.py               # Forger99, Jewett99, Hannay19 models
│   │   ├── lights.py               # Light schedule generation
│   │   ├── metrics.py              # ESRI and phase coherence
│   │   └── plots.py                # Actogram and visualization
│   ├── about_tab.py                # About tab with author info
│   ├── bpv_analysis.py             # Blood Pressure Variability analysis
│   ├── circadian_tab.py            # Circadian physiology UI
│   ├── device_imports.py           # Multi-device data import
│   ├── population_norms.py         # Population norms comparison
│   ├── user_profile.py             # User biometric profiles
│   ├── profile_ui.py               # Profile management UI
│   ├── ui_state_manager.py         # Centralized UI state
│   ├── welcome_header.py           # Professional welcome page
│   ├── gauge_builder.py            # Gauge visualization builder
│   ├── gpt_interpretation.py       # GPT-5.1 AI interpretation
│   ├── gpu_processing.py           # NVIDIA CUDA GPU acceleration
│   ├── noaa_space.py               # NOAA space weather data
│   ├── performance_utils.py        # CPU performance optimization utilities
│   ├── space_weather_impact.py     # Impact predictions & Polar H10 timing
│   ├── space_weather_persistence.py # NOAA/NASA data persistence
│   ├── user_profile_tab.py         # Centralized user profile & clinical scales
│   ├── garmin_import.py            # Garmin data import
│   ├── actigraph_import.py         # ActiGraph GT3X/GT3X+ import
│   ├── somfit_import.py            # Compumedics Somfit/Somfit Pro import
│   ├── fatigue_integration.py      # SAFTE fatigue model
│   ├── realtime_hrv.py             # Real-time HRV streaming
│   ├── ml_analytics.py             # ML anomaly/trend detection
│   ├── ml_predictions.py           # AF/SCD/Apnea risk models
│   └── publication_export.py       # Export utilities
├── db/
│   └── init/                       # Database initialization scripts
│       ├── 01_schema.sql           # User profiles schema
│       └── 02_space_weather_schema.sql  # Space weather tables
├── docs/
│   └── Manual.md                   # Comprehensive user manual
├── Dockerfile                      # Container image definition
├── docker-compose.yml              # Multi-service orchestration
├── requirements.txt
├── README.md
└── CHANGELOG.md
```

### Docker Deployment

For production deployment with persistent data storage:

```bash
# Start all services (PostgreSQL, Redis, App)
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down

# Include pgAdmin for database management
docker-compose --profile admin up -d
```

**Environment Variables** (create `.env` file):
```env
POSTGRES_PASSWORD=your_secure_password
OPENAI_API_KEY=sk-your-key
APP_PORT=8501
```

### Running Tests

```bash
pytest tests/ -v --cov=app
```

### Code Quality

```bash
# Format
black app/ tests/
isort app/ tests/

# Lint
ruff check app/ tests/

# Type check
mypy app/ --strict

# Security
bandit -r app/
pip-audit
```

---

## 📄 License

MIT License — See [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📞 Support

- **Documentation**: See `docs/Manual.md` for comprehensive usage guide
- **Issues**: Open a GitHub issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
