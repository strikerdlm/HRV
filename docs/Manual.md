# Author: Dr Diego Malpica MD

## Mission Control - Flight Surgeon — Complete User Manual

### Author

**Dr Diego Malpica MD**  
*Aerospace Medicine Specialist*  
National University of Colombia  
Physiology Instructor, Colombian Aerospace Force  
Contributing to **AsterPhysiology** Research Initiative

**GitHub Repository:** [https://github.com/strikerdlm/HRV](https://github.com/strikerdlm/HRV)  
**Version:** 1.17.0  
**Last Updated:** 2026-02-22

---

This manual provides step-by-step instructions for all features of Mission Control - Flight Surgeon with practical examples, interpretation guidance, and clinical/research best practices.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Data Preparation](#data-preparation)
3. [Uploading and Loading Data](#uploading-and-loading-data)
4. [Sidebar Configuration](#sidebar-configuration)
5. [Tab-by-Tab Guide](#tab-by-tab-guide)
6. [User Profiles and Clinical Scales](#user-profiles-and-clinical-scales)
7. [Population Norms Comparison](#population-norms-comparison)
8. [Blood Pressure Variability Analysis](#blood-pressure-variability-analysis)
9. [Circadian Physiology Module](#circadian-physiology-module)
10. [Autonomic Function Tests](#autonomic-function-tests)
11. [Space Data: Impact Predictions](#space-data-impact-predictions)
12. [Space Analytics (Correlations + ML)](#space-analytics-correlations--ml)
13. [Fatigue Prediction (SAFTE Model)](#fatigue-prediction-safte-model)
14. [Biofeedback and Real-Time HRV](#biofeedback-and-real-time-hrv)
15. [Garmin Integration](#garmin-integration)
16. [ActiGraph GT3X Integration](#actigraph-gt3x-integration)
17. [Somfit Pro Integration](#somfit-pro-integration)
18. [AI-Powered Interpretation](#ai-powered-interpretation)
19. [Export and Publication](#export-and-publication)
20. [Metric Reference Tables](#metric-reference-tables)
21. [Troubleshooting](#troubleshooting)
22. [Scientific References](#scientific-references)
23. [Advanced ECG R-Peak Detection](#advanced-ecg-r-peak-detection)
24. [Space Weather Data Science (Single User)](#space-weather-data-science-single-user)
24. [Multi-Modal Sensor Fusion](#multi-modal-sensor-fusion)
25. [Long-Term HRV Trending Analysis](#long-term-hrv-trending-analysis)
26. [Exercise HRV Analysis](#exercise-hrv-analysis)
27. [Machine Learning Predictions](#machine-learning-predictions)
28. [Real-Time BLE Integration](#real-time-ble-integration)
29. [Docker Deployment](#docker-deployment)
30. [Radiation Exposure Module](#radiation-exposure-module)
31. [Advanced Wearable Analytics](#advanced-wearable-analytics)
32. [Advanced HRV Analytics Platform](#advanced-hrv-analytics-platform)
33. [Crew Scheduling & Human Performance](#crew-scheduling--human-performance) ✨NEW
34. [Pending Developments and Roadmap](#pending-developments-and-roadmap)

---

## Getting Started

### Explore Without Data

The app is fully navigable **without uploading HRV data**. These features work immediately:

| Module | What You Can Do |
|--------|-----------------|
| 👤 **User Profile** | Register profile, complete clinical scales (ESS, Samn-Perelli, KSS), track history |
| 🌐 **Space Data** | Fetch live NOAA SWPC + NOAA feeds (+ NASA DONKI if configured), view Kp/F10.7/events (data-only; no correlations) |
| ☀️ **Circadian** | Simulate circadian rhythms with different light schedules |
| 😴 **SAFTE/Fatigue** | Model how sleep debt affects cognitive performance |
| 🫀 **Biofeedback** | Try the paced breathing demo |

All other tabs show **example data** and **reference values** to help you understand what's available before uploading your own recordings.

**Session persistence:** Circadian and SAFTE tabs now remember per-user configurations during the current session—when you switch users or rerun the app, your last light schedule and fatigue inputs are restored automatically.

**Cross-tab correlation:** The Circadian tab now publishes DLMO/CBT markers, ESRI, and light window details to the SAFTE/Fatigue tab. A single click in SAFTE applies the latest circadian sleep window and chronotype offset to fatigue simulations for tighter mission planning.

**Navigation note:** The Science tab now sits next to References for quick access. About and **Space Data** stay fully visible regardless of data state. Space Data loads instantly and uses explicit **Load cached / Fetch / Force refresh** controls (no auto-fetch on open) to stay stable on Windows/OneDrive. HRV history in the profile loads only the latest records for quicker switching. HRV analysis runs only after clicking **Run HRV Analysis**; the active mission database is stored under `crew/<Mission>/db/hrv_users.db` (selected in the sidebar Crew workspace selector) for mission-scoped portability.

**External space-data fetch (manual by design):** The unified Space Data dashboard is intentionally **manual/on-demand** to keep runs deterministic and avoid slow reloads. Use **Load cached** to view the last snapshot without network calls, then **Fetch**/**Force refresh** to pull fresh data from NOAA/NASA.

**Cache storage:** Space-data caches are persisted under `app/data_cache/` and mission HRV outputs under `crew/`. The Streamlit watcher is configured to ignore these folders to avoid unintended reload loops on Windows/OneDrive. If you suspect a corrupted cache, use the **Cache maintenance** controls in the **Space Data** tab to clear caches and refetch.

Manual fetch buttons remain available for on-demand refresh. Force refresh bypasses the cache to fetch fresh data directly from NOAA/NASA servers.

**Release awareness:** The welcome header and About tab now read version, release date, and git commit metadata directly from `CHANGELOG.md`, so flight surgeons can confirm they are on v1.8.15 (or later) without leaving the UI. The indicator flips to “dirty” whenever the working tree has uncommitted changes.

### System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.10 | 3.12+ |
| RAM | 4 GB | 8 GB |
| Storage | 500 MB | 1 GB |
| Browser | Chrome 90+ | Chrome/Edge latest |
| GPU (optional) | — | NVIDIA RTX 3080/4090/5070 |

### TypeScript Frontend (Modern UI)

A modern TypeScript/Next.js frontend is available under `frontend/` with a FastAPI backend under `api/`. This provides a responsive, app-like experience while leveraging the Python HRV analysis modules.

**Key points**
- **Streamlit preserved**: The main Streamlit app stays in `app/` unchanged.
- **TypeScript frontend**: Modern React/Next.js UI in `frontend/`.
- **FastAPI backend**: REST API in `api/` exposing Python HRV modules.
- **ECharts-first visuals**: Publication-quality charts using Apache ECharts.

**Features**
- Dashboard with crew profiles and space weather widget
- Research hub with expanded HRV-cognition modules:
  - Space Weather Dashboard (Kp, F10.7, solar wind gauges)
  - HRV Analysis (backend-driven time/frequency/nonlinear domains, Poincaré, HRF)
  - Frequency comparison (Welch vs Lomb-Scargle) with method-validity metadata
  - Cognitive Workload (baseline/task/recovery annotations; `ΔlnRMSSD`, `ΔHF`, `ΔLF/HF`)
  - Vigilance Tracker (30s/10s calibrated sliding windows + SAFTE overlay)
  - Flight Fatigue Classifier (calibrated low/moderate/high probabilities with missing-feature transparency)
  - Advanced nonlinear outputs (RCMSE and MM-DFA with strict minimum-sample gating)
  - Integrated Physiological Model fusion (probability + uncertainty interval)
  - Solar-HRV Correlations (heatmap, lag analysis)
  - Garmin Integration (sleep, SpO2, body battery)
  - Quality/Protocol panel across pages (stationarity, confidence, and interpretation caveats)
  - In-app reference/interpretation cards for workload, vigilance, and flight-fatigue metrics
  - Offline train / online infer split for vigilance and flight-fatigue models (`api/model_artifacts/`)
  - Calibration report endpoint for model traceability (`/api/research/models/calibration-report`)
  - Persistent RR tracing catalog/detail endpoints with dedupe-aware storage and reusable cached analyses (`/api/research/hrv/tracings/*`)
  - Global RR tracing loader in the research header so all HRV pages can target the same recording

**Run TypeScript Frontend (PowerShell)**
```powershell
# Option 1: Use the start script
.\start-frontend.ps1

# Option 2: Manual start
# Terminal 1 - Start API (port 8180)
conda activate hrv-py312
uvicorn api.main:app --reload --port 8180

# Terminal 2 - Start Frontend (port 3100)
cd frontend
npm install   # first time only
npm run dev
```

**Access Points**
- Frontend: http://localhost:3100
- API Docs: http://localhost:8180/docs

**Environment Configuration**
To use custom ports, set environment variables:
```powershell
$env:NEXT_PUBLIC_API_URL = "http://localhost:8180"
```

### GPU Acceleration (Optional)

For heavy HRV computations, GPU acceleration is supported via NVIDIA CUDA:

1. **Supported GPUs**: RTX 5070, RTX 4090, RTX 3080, and other CUDA-capable cards
2. **Installation by GPU family**:
   - **RTX 50xx (Blackwell)**: `pip install cupy-cuda12x` + CUDA Toolkit 12.8+
   - **RTX 40xx/30xx (Ada/Ampere)**: `pip install cupy-cuda12x`
   - **RTX 20xx (Turing)**: `pip install cupy-cuda11x`
3. **Usage**: Enable in sidebar under "🖥️ GPU Processing"
4. **Benefits**: 2-10x speedup for FFT, PSD, and large array operations

**RTX 50 Series (Blackwell) Note**: The RTX 5070/5080/5090 use Compute Capability 12.0 (sm_120), which requires CUDA Toolkit 12.8 or later for JIT kernel compilation. If you see `nvrtc64_120_0.dll` missing errors, see the [RTX 5070 CUDA Fix Guide](RTX_5070_CUDA_Fix.md) for step-by-step installation instructions. The app automatically detects your toolkit version and provides guidance if an upgrade is needed.

The app automatically detects GPU availability and falls back to CPU when CUDA is not present.

### Low-End Computer Performance Mode (v1.8.39)

For users with limited CPU, memory, or bandwidth, the app provides granular control over resource-intensive operations:

**Performance Settings** (Sidebar → ⚡ Performance Settings):

1. **Performance Presets**:
   - **Auto (Recommended)**: Automatically adjusts based on detected CPU tier
   - **Fast (Low CPU)**: Disables all heavy computations and downloads
   - **Balanced**: Enables most computations, disables ML clustering and NASA DONKI
   - **Quality (High CPU)**: Enables all features for full analysis
   - **Custom**: Manual control over all toggles

2. **Heavy Computation Toggles** (Custom preset):
   | Feature | CPU Impact | Description |
   |---------|------------|-------------|
   | Spectrogram Analysis | High | FFT over sliding windows |
   | Nonlinear Metrics | High | DFA, entropy, Poincaré |
   | ML Pattern Detection | High | K-means clustering |
   | Windowed HRV | Medium | Time-varying metrics |
   | Frequency Domain | Medium | PSD, band powers |

3. **Heavy Download Toggles** (Custom preset):
   | Feature | Bandwidth | Description |
   |---------|-----------|-------------|
   | NOAA Space Weather | High | Multiple feeds |
   | SpaceWeatherLive | Medium | Web scraping |
   | NASA DONKI Events | Medium | CME, SEP, flares |
   | Space Weather Impact | Medium | Predictions |
   | GPT AI Interpretation | Low | API calls |

**Performance Tier Auto-Detection**:
The app detects your CPU capabilities at startup:
- 🟢 **High**: ≥8 cores, ≥16GB RAM → All features enabled
- 🟡 **Medium**: 4-7 cores, ≥8GB RAM → Some heavy features disabled
- 🔴 **Low**: <4 cores or <8GB RAM → Most heavy features disabled

**Offline Mode**: Disable all download toggles for completely offline HRV analysis. Cached data remains available.

**Research stability controls (v1.9.9)**:
- **Sidebar-only navigation**: The sidebar **Navigation** selector drives the active view; tabs are hidden to prevent accidental multi-tab rendering.
- **Stable navigation (single section rendering)**: The selector gates heavy HRV renderers to the active view for smoother interaction.
- **Selection-change activation**: The active view is applied only when the sidebar selection changes to avoid redundant reruns.
- **Guest results visibility**: Manual tab gating is bypassed for the active section so guest HRV and Space Analytics outputs render immediately.
- **Rerun storm guard**: If rapid reruns are detected, the app automatically switches to manual-only processing, disables heavy plots, and surfaces a **Recover** button in Developer Tools.
- **Tab persistence removed**: The experimental tab persistence toggle was removed to prevent session_state mutation errors and rerun loops.
- **Guest analysis supported**: HRV processing and Space Weather correlations run without selecting a user profile (guest mode).

### Installation Steps

**Step 1: Clone or download the repository**

```bash
git clone https://github.com/strikerdlm/HRV.git
cd HRV
```

**Step 2: Set up Python environment**

**Option A: Using Conda (Recommended)**

```bash
# Recommended: run commands explicitly in the correct env (avoids wrong-env issues)
conda run -n hrv-py312 python --version

# (Optional interactive shell)
# conda activate hrv-py312
# python --version
```

**Option B: Using Virtual Environment**

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

**Step 3: Install dependencies**

```bash
# Conda (recommended)
conda run -n hrv-py312 pip install -r requirements.txt

# Virtualenv
# pip install -r requirements.txt
```

**Step 4: Set up environment variables (optional but recommended)**

Create a `.env` file in the project root:

```env
# Required for AI interpretation
OPENAI_API_KEY=sk-your-key-here

# Optional for NASA DONKI data
NASA_API_KEY=DEMO_KEY

# Optional for Garmin API access
GARMIN_EMAIL=your.email@example.com
GARMIN_PASSWORD=your_password
```

**Step 5: Launch the application**

```bash
# Conda (recommended)
conda run -n hrv-py312 streamlit run app/operational_app.py
# or (research app: core statistics/analytics dashboards)
# conda run -n hrv-py312 streamlit run app/research_app.py
# conda run -n hrv-py312 streamlit run app/app.py
# or (single-user data science app, latest Streamlit)
# conda run -n hrv-py312 pip install -r requirements_streamlit_latest.txt
# conda run -n hrv-py312 streamlit run app/space_weather_ds_app.py

# Virtualenv (after activating .venv)
# streamlit run app/operational_app.py
# or (full dashboards)
# streamlit run app/research_app.py
# streamlit run app/app.py
# or (single-user data science app, latest Streamlit)
# pip install -r requirements_streamlit_latest.txt
# streamlit run app/space_weather_ds_app.py
```

The app opens at `http://localhost:8501` in your default browser.

**Operational vs Research (rules of thumb)**:
- **Operational app**: **Crew-facing intake + mission operations** — collect and review crucial crew information (profiles/clinical logs) with lightweight context. Keep it **stable, fast, and non-analytic**.
- **Research app**: **Core statistics/analytics** — HRV/HRF computation, Space Data/Space Analytics (correlations + ML), exports, and GPT‑5.2 interpretation.
- **Space Weather Data Science (Single User)**: streamlined workflow focused on single-subject HRV/HRF, NOAA/Space Weather analytics, and ML patterns. Uses the latest Streamlit with a separate requirements file and no user profiles.

---

## Space Weather Data Science (Single User)

This standalone app (`app/space_weather_ds_app.py`) is a performance-focused, single-user workflow that preserves the space-weather and data-science capabilities of the research app without user profiles.

**Install (latest Streamlit)**:

```bash
# Conda
conda run -n hrv-py312 pip install -r requirements_streamlit_latest.txt
conda run -n hrv-py312 streamlit run app/space_weather_ds_app.py

# Virtualenv
pip install -r requirements_streamlit_latest.txt
streamlit run app/space_weather_ds_app.py
```

**Performance profiles**:
- **Lightweight (default)**: minimal compute, fast UI, reduced analytics scope.
- **Balanced**: full HRV/HRF metrics and correlations.
- **RTX 5070 GPU**: enables GPU acceleration where available (requires CUDA 13.x and `cupy-cuda13x`).

**Secrets**: Use a `.env` file for `GARMIN_EMAIL`, `GARMIN_PASSWORD`, and `NASA_API_KEY`. Never commit secrets.

---

## Data Preparation

### Creating RR Interval Files

RR intervals (time between heartbeats) can be exported from various devices:

#### From Polar H10 (via Polar Beat App)

1. Open Polar Beat app on your phone
2. Connect to Polar H10 chest strap
3. Start recording (orthostatic test or free recording)
4. After recording, go to History → Select session
5. Export RR data as `.txt` file
6. Transfer to computer

#### From Elite HRV

1. Open Elite HRV app
2. After recording, tap session
3. Export → RR Intervals
4. Save as `.txt` or `.csv`

#### From HRV4Training

1. Complete measurement in app
2. Go to History → Select reading
3. Export RR data
4. Email or save to cloud

### File Format Requirements

**Correct format** (one value per line, milliseconds):

```
1027
1007
991
1010
1020
1010
979
945
```

**Incorrect formats** (will not parse correctly):

```
# Wrong: comma-separated
1027, 1007, 991, 1010

# Wrong: with headers
RR Interval
1027
1007

# Wrong: seconds instead of milliseconds
1.027
1.007
```

### Naming Convention

For automatic timestamp detection, name files as:

```
YYYY-MM-DD HH-MM-SS.txt
```

**Examples:**
- `2025-11-06 00-43-42.txt` → November 6, 2025 at 00:43:42
- `2025-11-06_18-30-00.txt` → November 6, 2025 at 18:30:00

The app parses this timestamp to align your HRV data with space weather data for correlation analysis.

---

## Uploading and Loading Data

### Step-by-Step Upload Process

1. **Open the sidebar** (click `>` at top-left if collapsed)

2. **Locate the file uploader** under "📂 Upload RR Interval Files"

3. **Select files**: 
   - Click "Browse files"
   - Select one or multiple `.txt` files
   - Maximum 200 MB per file

4. **Wait for processing**:
   - Progress bar shows upload status
   - Files are validated automatically
   - Invalid values (outside 300-2000 ms) are filtered

5. **Verify upload**:
   - Check "Overview" tab for dataset summary
   - Each file appears as a separate dataset
   - Beat count, duration, and artifact % are displayed

### Multi-File Analysis

You can upload multiple files for comparative analysis:

```
Morning_Day1.txt
Evening_Day1.txt
Morning_Day2.txt
Evening_Day2.txt
```

The app will:
- Process each file independently
- Display metrics side-by-side in tables
- Overlay PSD curves in Frequency tab
- Compare across datasets in gauges

### Per-User Storage & Duplicate Protection

- RR uploads are saved to the active user profile (light-bulb indicator) and immediately written to `crew/<Mission>/subjects/{user}/rr_intervals`; computed HRV results persist with their analysis settings.
- Re-uploads with the same file hash trigger a sidebar warning; you can reuse stored results when the settings match (toggle in the sidebar) or force recomputation if settings changed.
- Sidebar uploads target the active profile (Diego by default). Uploading from **User Profile → HRV** scopes files to that user and sets that profile active before queuing them for analysis.
- In **User Profile → HRV → HRV Measurement History**, use **Regenerate plots** to force-refresh the HRV history charts after new uploads/analysis runs.
- In **User Profile → HRV → Stored RR Library**, you can load RR recordings already stored under that profile back into the main analysis workspace (optionally auto-running HRV analysis) without re-uploading.
- In **User Profile → Readiness**, readiness scoring uses stored parasympathetic-index history and shows HRV metric gauges with the same ECharts styling as the main gauges.

### FIT ↔ CSV Tools (User Profile → Data tab)

- Convert Garmin FIT files to CSV in-app, download the CSV, and automatically store both FIT and CSV under the active profile.
- Garmin CSV uploads are also stored under the active profile for later use.
- Conversion uses bounded parsing (fitparse) and surfaces a 10-row preview for quick verification.

### Sleep Tab Login & Device Imports

- The **Sleep Analysis** sidebar now batches inputs inside forms. Typing your ID/name no longer triggers a rerun; press **`🔑 Login / Create Account`** once to authenticate or register.
- Garmin, ActiGraph, and Somfit uploaders each include a dedicated **Import** button. Files are only processed when you click the button, preventing duplicate ingests on rerun.
- After a successful import, the uploader clears automatically so you can stage the next file without reprocessing the previous one.

**Workflow tip:**
1. Open **Sleep Analysis → Sidebar**.
2. Expand **🔐 Login / Register**, complete the form, and click **Login / Create Account**.
3. Expand a device section (Garmin / ActiGraph / Somfit), choose a file, and click the matching **📥 Import** button.
4. Use **📥 Load All Stored Data** to refresh the main Sleep Analysis tabs with the newly stored records.

### Example: Sample Data

If you don't have real data, create a test file:

```bash
# Generate 5 minutes of simulated RR intervals (Python)
import random
rr_intervals = [random.gauss(850, 50) for _ in range(300)]
with open('test_data.txt', 'w') as f:
    f.write('\n'.join(str(int(rr)) for rr in rr_intervals))
```

---

## Sidebar Configuration

### Quality Control Settings

| Setting | What it does | Recommended value |
|---------|--------------|-------------------|
| **Enable QC** | Toggles artifact detection | ✅ Always enable |
| **Method** | Detection algorithm | `threshold_median` |
| **Max deviation** | Threshold for flagging | 0.20 (20%) |
| **Median window** | Smoothing window | 11 beats |

**Step-by-step QC setup:**

1. Expand "🔧 Quality Control" in sidebar
2. Check "Enable artifact detection"
3. Select method: `threshold_median` (most robust)
4. Set max deviation: 0.20 for typical data, 0.15 for clean data
5. Leave median window at 11 unless you have very short recordings

### Windowed Analysis Settings

| Setting | What it does | Recommended value |
|---------|--------------|-------------------|
| **Window size** | Analysis window duration | 5 min |
| **Step size** | Window overlap | 1 min |
| **Min RR count** | Minimum beats per window | 60 |
| **Max windows** | Limit for long recordings | 500 |

**Step-by-step windowed setup:**

1. Expand "📊 Windowed Analysis" in sidebar
2. Set window: `5min` (standard short-term)
3. Set step: `1min` for high resolution, `5min` for non-overlapping
4. Set min RR: 60 (allows windows with artifacts)

### PSD Method Selection

| Method | Best for | Trade-offs |
|--------|----------|------------|
| **Welch** | General use | Good noise rejection, moderate resolution |
| **Periodogram** | Clean data | High resolution, sensitive to noise |
| **AR (Yule-Walker)** | Educational | Parametric, smooth spectrum |

**Step-by-step PSD setup:**

1. Expand "📈 Frequency Analysis" in sidebar
2. Select method: `Welch` for most cases
3. Note: AR method is approximate and for comparison only

### Patient Profile (Optional)

For covariate-adjusted metrics:

1. Expand "👤 Patient Profile" in sidebar
2. Enter age (years)
3. Select sex (Male/Female/Other)
4. Enter BMI
5. Select exercise level (Sedentary/Moderate/Athlete)

This enables:
- Age/sex/BMI-adjusted RMSSD and SDNN expectations
- Z-scores relative to adjusted baselines
- More accurate interpretation for your demographic

---

## Tab-by-Tab Guide

### Overview Tab

**Purpose:** Quick summary of uploaded data and key metrics

**What you see:**
- Table with dataset metadata (file name, beat count, duration, mean HR, artifact %)
- Summary of respiratory rate estimates
- Deviation flag counts (if windowed analysis enabled)

**How to use:**

1. After upload, check this tab first
2. Verify beat counts match expected recording duration
3. Check artifact % (target: <5%)
4. If artifact % is high, return to Time Series tab to investigate

**Example interpretation:**
```
Dataset: 2025-11-06_00-43-42.txt
Beats: 350
Duration: 5.2 min
Mean HR: 68 bpm
Artifacts: 2.3%

→ Good quality recording, proceed with analysis
```

### Time Series Tab

**Purpose:** Visualize raw and cleaned RR intervals

**Loader tip:** Open the **📂 Load RR files** expander at the top of the tab to pick which uploaded recordings feed this view. The selection only affects this tab, so you can isolate a single recording when multiple RR files are staged.

**What you see:**
- Top chart: RR intervals over time
- Bottom chart: Heart rate over time
- If QC enabled: Green line (cleaned), red dots (artifacts)

**How to use:**

1. Look for sudden spikes or drops (potential artifacts)
2. Verify red dots align with obvious outliers
3. Check if green line smoothly interpolates through artifacts
4. If too many artifacts, consider re-recording

**Scientific note:** Artifacts (ectopic beats, missed beats, motion) inflate variability metrics. Correction by interpolation is standard practice but should be documented.

### Frequency Tab

**Purpose:** Analyze frequency components of HRV

**Loader tip:** Use **📂 Load RR files** to explicitly choose which recordings are included in the PSD overlay. Narrowing the selection keeps Welch/AR plots readable when dozens of files are uploaded.

**What you see:**
- Power Spectral Density (PSD) curve
- Shaded bands: VLF (gray), LF (blue), HF (pink)
- Legend with absolute power values

**Band definitions:**
| Band | Frequency | Physiological interpretation |
|------|-----------|------------------------------|
| VLF | 0.0033–0.04 Hz | Thermoregulation, hormonal (not reliable <5 min) |
| LF | 0.04–0.15 Hz | Baroreflex, mixed sympathetic/parasympathetic |
| HF | 0.15–0.40 Hz | Respiratory sinus arrhythmia (vagal) |

**How to use:**

1. Check HF peak: Should show clear peak if RSA present
2. Note LF/HF ratio in metrics table
3. Compare across datasets using overlay

**Interpretation example:**
```
HF power: 1200 ms²/Hz → Strong vagal activity
LF power: 800 ms²/Hz → Moderate baroreflex
LF/HF: 0.67 → Vagal predominance (typical at rest)
```

### Nonlinear Tab

**Purpose:** Visualize beat-to-beat dynamics

**Loader tip:** Select the recording for Poincaré and entropy plots via **📂 Load RR files**. This avoids mixing unrelated datasets when batch uploads are queued.

**What you see:**
- Poincaré plot: Each point is (RRₙ, RRₙ₊₁)
- SD1/SD2 ellipse overlay
- Color coding by dataset

**Poincaré interpretation:**
| Metric | Meaning | Normal range |
|--------|---------|--------------|
| SD1 | Short-term variability (~RMSSD/√2) | 30-60 ms |
| SD2 | Long-term variability | 60-120 ms |
| SD1/SD2 | Balance of short vs long-term | 0.3-0.5 |

**How to use:**

1. Cloud shape indicates variability pattern
2. Elongated along identity line → high long-term variability
3. Wide perpendicular to identity → high short-term variability
4. Tight cluster → reduced overall variability

### Spectrogram Tab

**Purpose:** Time-frequency analysis

**What you see:**
- Heatmap: x-axis (time), y-axis (frequency), color (power)
- HF band (0.15-0.4 Hz) shows breathing rhythm
- LF band (0.04-0.15 Hz) shows slower autonomic rhythms

**How to use:**

1. Look for consistent HF power (breathing regularity)
2. Note any sudden changes in spectral patterns
3. Identify non-stationary segments
4. Useful for finding when autonomic state changed

### Windowed Tab

**Purpose:** Track HRV changes over time

**What you see:**
- Line plots of metrics across windows
- Deviation timeline with colored flags
- Anomaly episode summary

**Deviation detection:**
| Color | Meaning | Z-score |
|-------|---------|---------|
| 🟢 Green | Normal | |z| < 2 |
| 🟡 Yellow | Warn | 2 ≤ |z| < 3 |
| 🔴 Red | Alert | |z| ≥ 3 |

**How to use:**

1. Enable deviation detection in sidebar
2. Set threshold (default: 2.0 SD)
3. Select metrics to monitor (RMSSD, SDNN, LF/HF, HF power)
4. Review flag timeline for anomaly episodes
5. Investigate red/yellow windows in Time Series tab

**Production longitudinal mode (Next.js frontend):**
- Windowed endpoint supports **`scope=all|selected`**:
  - `all`: merges windows from all ingested RR tracings to build a longitudinal timeline.
  - `selected`: analyzes only the RR tracing chosen in the global header loader.
- Trend review includes:
  - OLS slope + **Theil-Sen robust slope** with 95% CI
  - Kendall tau with p-value
  - FDR-adjusted q-values for trend/correlation screening
- Correlation heatmaps and association cards prioritize **q-value significance** (Benjamini-Hochberg), while showing raw p-values for transparency.

### Metrics Tab

**Purpose:** Complete numerical results

**What you see:**
- Comprehensive table with all computed metrics
- Organized by domain (time, frequency, nonlinear, entropy, fragmentation)
- Export button for CSV download

**Key metrics to review:**
| Metric | Clinical significance |
|--------|----------------------|
| RMSSD | Vagal activity (higher = more parasympathetic) |
| SDNN | Total variability (lower = poorer prognosis) |
| LF/HF | Autonomic balance (interpret with caution) |
| DFA α1 | Fractal dynamics (0.75-1.25 normal at rest) |
| SampEn | Complexity (lower = more rigid/predictable) |

### Gauges Tab

**Purpose:** Visual comparison to reference ranges

**What you see:**
- 30+ gauges organized by domain
- Color zones: Green (optimal), Yellow (caution), Red (concern)
- Needle shows current value

**How to read gauges:**

1. **Green zone**: Value within typical healthy range
2. **Yellow zone**: Value warrants attention
3. **Red zone**: Value significantly abnormal (investigate further)

**Important caveats:**
- Reference ranges are population-based
- Age, fitness, medications affect individual ranges
- Use for within-subject trending primarily

---

## User Profiles and Clinical Scales

This feature enables personalized HRV analysis and fatigue assessment by incorporating user-specific biometric data and validated clinical questionnaires.

All longitudinal plots inside the profile (assessment history, Garmin wellness trends, HRV history, and Exploration Medical Analytics) now render with Apache ECharts for consistent styling and publication-ready exports.

### EVA Clearance Semaphore (v1.8.36)

The **Exploration Medical Analytics** section now displays EVA clearance states as a traffic-light semaphore instead of a bar chart:

- **GO** (green) — Crew member is cleared for EVA
- **MONITOR** (amber) — Requires mitigation or flight surgeon review before EVA
- **NO-GO** (red) — Not cleared for EVA

Each indicator glows when active (count > 0) and dims when inactive. A summary panel shows the dominant status and total assessments. This visualization provides an at-a-glance operational readiness indicator for mission planners.

### Sleep & Chronotype Inputs + Garmin Autofill (v1.8.37)

- **Energy & Nutrition → Sleep & Chronotype**: Sliders/inputs for sleep hours, sleep quality, hours awake, chronotype offset, RMSSD, resting HR, and VO₂. A **Sync to Profile Tools Engine** button pushes these values into SAFTE fatigue and Operational Performance tools. A **📡 Autofill from Garmin** button prefers stored Garmin daily metrics (when present) and falls back to live Garmin Connect to fill these fields automatically.
- **Profile Tools Engine → Garmin Autofill**: One-click Vivosmart/Garmin pull fills sleep hours, sleep quality, hours awake, RMSSD, and resting HR for SAFTE/Operational calculations. Users without a device can still enter values manually.

### Longitudinal timepoints (T0–T21)

Mission Control now supports **study timepoints** so you can run baseline + follow-up workflows (e.g., **T0_baseline**, **T1** … **T21**) without losing determinism.

- **Where**: User Profile → **Assessments** and **HRV** tabs
- **How**: Select a timepoint label, set the measurement date, then click **Save / Apply timepoint**. New assessments and HRV measurements saved after that will carry the linked `timepoint_id`.
- **Unassigned**: You can leave the timepoint as **Unassigned** if the entry is not part of a longitudinal protocol.

### Batched Clinical Assessments (December 2025 Sprint)

- **Clinical form batching:** Epworth, Samn-Perelli, Karolinska, and VAS controls now live inside Streamlit forms so you can adjust multiple sliders without forcing a full-page rerun. Press **Preview** to refresh summaries or **Save** to persist the assessment.
- **Debounced commits:** Each submit action passes through a 0.8 s debounce guard to prevent duplicate entries when users double-click or when the page reruns due to other activity.
- **Exploration medical record protection:** NASA-style mission logs share the same debounce to keep longitudinal data clean even when uploading from multiple tabs.

**Next focus:** Ensure every analysis tab consumes the active user context so NASA nutrition, fatigue, and circadian modules stay synchronized without re-entering profile data.

### Circadian Scenario Builder (December 2025 Sprint)

- **In-tab controls:** The Circadian Physiology tab now hosts its own configuration drawer, freeing the global sidebar for mission controls.
- **Batched apply button:** All sliders and selectors live inside a single form—adjust everything first, then click **Apply scenario** to trigger a single simulation rerun.
- **Preset vault:** Save up to five named scenarios (e.g., *Night Ops*, *Mars Analog*) directly in the tab. Presets persist across reruns and are shared with multi-user sessions.
- **Mission defaults:** A single “Reset defaults” button restores NASA baseline parameters (30-day run, Hannay19 model, regular 08:00–22:00 light) in one click.

### User Biometric Profile

The platform collects essential biometric data to tailor physiological calculations:

#### Required Measurements (Metric System)

| Parameter | Unit | Range | Purpose |
|-----------|------|-------|---------|
| Height | cm | 100-250 | BMI calculation, VO₂max estimation |
| Weight | kg | 30-300 | BMI calculation, metabolic estimates |
| Date of Birth | date | - | Age-based normative comparisons |
| Sex | M/F/Other | - | Sex-specific HRV norms |

#### Calculated Metrics

**Body Mass Index (BMI)**
$$BMI = \frac{weight_{kg}}{(height_m)^2}$$

Classification (WHO):
- <18.5: Underweight
- 18.5-24.9: Normal weight
- 25.0-29.9: Overweight
- ≥30.0: Obese

**VO₂max Estimation** (when not directly measured)

Uses the Jackson et al. (1990) non-exercise prediction equation:
$$VO_2max = 56.363 + (1.921 \times PA) - (0.381 \times age) - (0.754 \times BMI) + (10.987 \times sex)$$

Where PA = Physical Activity rating (1-7), sex = 1 (male) or 0 (female).

**Maximum Heart Rate** (Tanaka formula):
$$HR_{max} = 208 - (0.7 \times age)$$

Reference: Tanaka H, et al. *J Am Coll Cardiol.* 2001;37(1):153-156.

### Personalized Health Metrics (NEW in v1.8.22)

The **Personalized Health Metrics** panel in the Clinical Profile tab provides comprehensive health assessments tailored to your individual profile data. All calculations use your specific measurements (weight, height, age, sex, body circumferences) rather than generic population averages.

#### Body Fat Estimation (US Navy Method)

Uses the Hodgdon & Beckett (1984) circumference-based method from the Naval Health Research Center:

**Male formula:**
$$BF\% = \frac{495}{1.0324 - 0.19077 \times \log_{10}(waist - neck) + 0.15456 \times \log_{10}(height)} - 450$$

**Female formula:**
$$BF\% = \frac{495}{1.29579 - 0.35004 \times \log_{10}(waist + hip - neck) + 0.22100 \times \log_{10}(height)} - 450$$

**Required measurements:**
- Neck circumference (cm) — measured below the larynx
- Waist circumference (cm) — at navel for males, narrowest point for females
- Hip circumference (cm) — required for females only

**Body Fat Classification (ACSM):**

| Category | Male | Female |
|----------|------|--------|
| Essential Fat | 2-5% | 10-13% |
| Athletes | 6-13% | 14-20% |
| Fitness | 14-17% | 21-24% |
| Average | 18-24% | 25-31% |
| Obese | >25% | >32% |

#### Sleep Apnea Risk (STOP-BANG Score)

Calculates obstructive sleep apnea risk using STOP-BANG questionnaire components (Chung F et al., Anesthesiology 2008):

| Component | Criteria |
|-----------|----------|
| **S** - Snoring | Loud snoring |
| **T** - Tiredness | Daytime fatigue/sleepiness |
| **O** - Observed | Witnessed breathing stops |
| **P** - Pressure | High blood pressure |
| **B** - BMI | BMI > 35 kg/m² |
| **A** - Age | Age > 50 years |
| **N** - Neck | Neck > 40 cm (male) or > 38 cm (female) |
| **G** - Gender | Male sex |

**Risk Interpretation:**
- **0-2**: Low risk of OSA
- **3-4**: Intermediate risk — consider clinical evaluation
- **5-8**: High risk — recommend sleep study (polysomnography)

#### Personalized HRV Reference Ranges

All HRV metrics are interpreted against age/sex-adjusted reference ranges from:
- Nunan D et al. *PACE* 2010;33:1407-17
- Shaffer F, Ginsberg JP. *Front Public Health* 2017;5:258

| Age Group | RMSSD (ms) | SDNN (ms) | pNN50 (%) | HF Power (ms²) |
|-----------|------------|-----------|-----------|----------------|
| 20-29 | 19-75 | 25-85 | 2-45 | 300-2000 |
| 30-39 | 15-65 | 22-75 | 1.5-38 | 200-1600 |
| 40-49 | 12-55 | 20-65 | 1-30 | 150-1200 |
| 50-59 | 10-45 | 18-58 | 0.5-22 | 100-900 |
| 60-69 | 8-40 | 16-52 | 0.3-18 | 60-700 |
| 70+ | 7-35 | 14-46 | 0.2-14 | 40-550 |

Each metric displays:
- **Status**: very_low, low, normal, high, very_high
- **Percentile estimate**: Where you fall in your age group
- **Z-score**: Standard deviations from age-group mean
- **Interpretation**: Human-readable guidance

#### Fitness Classification (VO₂max)

Uses ACSM Guidelines for Exercise Testing (11th Ed) percentile tables:

| Category | Male 30-39 | Female 30-39 |
|----------|------------|--------------|
| Very Poor | <23 | <22 |
| Poor | 23-31 | 22-27.5 |
| Fair | 31-35.5 | 27.5-31.5 |
| Good | 35.5-40 | 31.5-35.5 |
| Excellent | 40-44 | 35.5-39 |
| Superior | >44 | >39 |

#### Cardiovascular Risk Profile

Assesses multiple risk factors following simplified Framingham-like criteria:

**Risk Factors Assessed:**
- Age (≥45 male, ≥55 female)
- Elevated BMI (≥25 overweight, ≥30 obese)
- Hypertension (SBP ≥130 mmHg)
- Dyslipidemia (TC/HDL ratio, low HDL)
- Current smoking
- Diabetes
- Family history of premature CVD
- Low cardiorespiratory fitness

**Protective Factors:**
- Healthy BMI (18.5-24.9)
- Normal blood pressure
- High HDL (≥60 mg/dL)
- Non-smoker
- Excellent fitness (high VO₂max)
- Low resting heart rate

#### Personalized Hydration Requirements

Based on NASA-STD-3001 Water Requirements:

$$Base_{mL} = weight_{kg} \times 32$$

Adjustments:
- **Activity level**: Sedentary (×1.0) to Very Active (×1.4)
- **Exercise**: +750 mL per hour of activity
- **Hot environment**: +25%
- **Altitude >2500m**: +12%

#### Using Personalized Metrics

1. **Complete Your Profile**: Navigate to **User Profile → Edit Profile** and enter height, weight, date of birth, and sex.

2. **Add Body Composition**: Go to **Clinical Profile → Body Composition** and enter circumference measurements (especially neck, waist, and hip).

3. **View Personalized Metrics**: Open **Clinical Profile → Personalized Health Metrics** to see all calculated assessments.

4. **Export Summary**: Click **Copy Summary to Clipboard** to generate a markdown report of your personalized metrics.

5. **Cross-Tab Integration**: Your profile data automatically flows to:
   - HRV interpretation (age-adjusted norms)
   - NASA Nutrition Calculator (VO₂max compensation)
   - NASA Nutrition sleep inputs share values with the Profile Tools Engine; Garmin autofill updates both
   - Fatigue Prediction (sleep requirements)
   - Circadian Physiology (chronotype adjustments)

### Profile Tools Engine (NEW in v1.8.23)

The **Profile Tools Engine** provides comprehensive calculation engines accessible per user profile. Each tool uses your individual profile data (age, sex, weight, chronotype, HRV values) to deliver personalized physiological assessments.

#### Available Tools

| Tool | Description | Key Outputs |
|------|-------------|-------------|
| **Recovery Score** | lnRMSSD-based recovery assessment | Score (0-100), status, component breakdown |
| **Training Readiness** | Multi-component readiness assessment | Readiness score, workout suggestions |
| **Fatigue Prediction (SAFTE)** | 24-hour cognitive effectiveness forecast | Current/predicted effectiveness, risk level |
| **Operational Performance (HRV + SAFTE)** | Fused readiness for safety-critical tasks | Readiness score, GO/CAUTION/NO-GO, best/worst 2h windows |
| **Personalized HRV Analysis** | Age/sex-adjusted HRV interpretation | Parasympathetic index, stress index, autonomic balance |
| **Performance Forecast** | Hour-by-hour performance prediction | Peak/low times, 24-hour curve |

#### Recovery Score Calculation

Based on Plews et al. (2013) and the lnRMSSD methodology:

**Components:**
- **HRV Component (0-50 points)**: Compares lnRMSSD to personal baseline or age-adjusted norms
- **Sleep Component (0-30 points)**: Evaluates sleep duration and quality
- **Resting HR Component (0-20 points)**: Compares to baseline heart rate

**Status Classifications:**
| Score | Status | Training Recommendation |
|-------|--------|------------------------|
| 80-100 | Excellent | High-intensity training OK |
| 65-79 | Good | Normal training day |
| 50-64 | Moderate | Reduce intensity 10-20% |
| 35-49 | Low | Active recovery only |
| 0-34 | Poor | Rest day recommended |

Reference: Plews DJ, et al. *J Appl Physiol.* 2013;115(4):531-538.

#### Training Readiness Assessment

Multi-component score for workout planning:

**Components:**
- **HRV (0-35 points)**: Current HRV status vs age norms
- **Sleep (0-25 points)**: Duration × quality factor
- **Fatigue (0-20 points)**: Time since last training, intensity
- **Strain (0-20 points)**: Accumulated training load

**Readiness Levels:**
| Level | Score | Action |
|-------|-------|--------|
| Optimal | 85+ | Competition-ready, HIIT OK |
| High | 70-84 | Proceed as planned |
| Moderate | 50-69 | Focus on technique |
| Low | 30-49 | Active recovery |
| Very Low | <30 | Full rest day |

Reference: Kiviniemi AM, et al. *Med Sci Sports Exerc.* 2007;39(4):625-631.

#### SAFTE Fatigue Prediction

Based on the Sleep, Activity, Fatigue, and Task Effectiveness model.

**Model components (implementation):**
- **Circadian process**: cosine-shaped 24h alertness curve with chronotype offset.
- **Homeostatic process**: sleep pressure accumulation (~2.4% effectiveness loss per hour awake), floored near 65% after 24h awake.
- **Sleep debt**: deficit from insufficient sleep (baseline need 8h). Debt is bounded (≤24h equivalent) to avoid runaway penalties.
- **Sleep quality**: scales effective sleep (sleep_quality × 0.95).
- **Debt penalty**: up to 20 points (2.5 points per hour debt) applied after circadian × homeostatic.
- **Workload penalty**: up to 5 points at workload_intensity = 1.0.
- **Clamps**: outputs constrained to 45–100% for UI stability.

**Outputs:**
- Current effectiveness (%)
- 4h, 8h, 24h forecasts
- Risk level (Minimal to Critical)
- Optimal sleep time
- 24-hour performance curve

**Space-data correlations (status):**
- The **🌐 Space Data** tab is intentionally **data-only** (fetch + visualize).
- Correlation + ML workflows now live in the **🔬 Space Analytics** tab (button-driven; no auto-runs).
- Scientific context (useful for study design):
  - Ramishvili et al. 2023, Atmosphere 14(12):1707 — adaptation to geomagnetic storms (https://doi.org/10.3390/atmos14121707)
  - Mattoni et al. 2019, bioRxiv — highlights autocorrelation and small effect sizes (https://doi.org/10.1101/684035)
  - Papailiou & Mavromichalaki 2025, Atmosphere 16(6):711 — HR changes around major storms (https://doi.org/10.3390/atmos16060711)

**Assumptions & limitations:**
- Deterministic, bounded approximation (not full SAFTE-R parameterization).
- No pharmacology/caffeine, no individualized reservoir size, no explicit shift-work light model.
- For calibration with observed alertness/PVT labels, use FRMS v2 hooks to tune parameters.

Reference: Hursh SR, et al. *Aviat Space Environ Med.* 2004;75(3):A44-A53.

#### Operational Performance (HRV + SAFTE)

This tool provides a **transparent fusion** of:

- **SAFTE effectiveness (%)** (sleep + circadian drivers of alertness), and
- **HRV-derived recovery/autonomic state** (lnRMSSD-based recovery score, parasympathetic index, stress index)

into a single **Operational Readiness Score (0–100)** that supports **task scheduling** and **risk awareness**.

**Key outputs:**
- **Operational readiness score (0–100)**: higher = better expected operational readiness.
- **Category**:
  - **GO** (≥85): peak readiness window
  - **GO (monitor)** (70–84): adequate readiness; continue monitoring
  - **CAUTION** (55–69): elevated risk; reduce complexity, add verification steps
  - **NO‑GO** (<55): avoid safety‑critical tasks when possible
- **Best / worst 2-hour windows**: derived from the next‑24h SAFTE curve, applying the current HRV state as a modifier.
- **Next‑12h alert windows**: projected hours where readiness is low enough to warrant avoiding critical tasks.

**Operational interpretation notes:**
- The score is a **planning index**, not a medical diagnosis or a validated probability of error.
- Use it to **sequence** demanding tasks into the best readiness window and to **trigger mitigations** (nap, workload reduction, second-person verification).

#### Personalized HRV Analysis

Age/sex-adjusted interpretation using Nunan et al. (2010) and Shaffer & Ginsberg (2017) norms:

**Calculated Indices:**
- **Parasympathetic Index (0-10)**: Overall vagal tone assessment
- **Stress Index**: Baevsky-style sympathetic activity indicator
- **Autonomic Balance**: LF/HF ratio interpretation

**Metric Interpretation:**
| Status | Meaning |
|--------|---------|
| Very Low | >2 SD below mean for age group |
| Low | 1-2 SD below mean |
| Normal | Within ±1 SD of mean |
| High | 1-2 SD above mean |
| Very High | >2 SD above mean |

#### Advanced HRV Analytics Platform (v1.8.82+)

The **🧬 Advanced HRV Analytics** expander in HRV History provides state-of-the-art statistical analysis, ML pattern recognition, and clinical decision support. Access it via **User Profile → HRV → Advanced HRV Analytics**.

**5-Tab Interface:**

| Tab | Content |
|-----|---------|
| 🎯 Clinical Decision | Overall status (Green/Yellow/Orange/Red), autonomic balance gauge, metric assessments, alerts, recommendations |
| 📊 Statistical Tests | Descriptive stats, Shapiro-Wilk normality tests, t-tests vs reference, effect sizes (Cohen's d) |
| 📈 Trends & Forecast | Trend direction, slope significance, R², % change, 7-day forecasts with 95% CI |
| 🔍 Anomalies & Patterns | Z-score/IQR anomaly detection, pattern recognition (autonomic balance, chronic stress) |
| 🔗 HRV + Garmin | Cross-correlation matrix, concordance score, integrated stress/recovery scores |

**Statistical Tests (p-values in 4 decimals):**

| Test | Purpose | Output |
|------|---------|--------|
| Shapiro-Wilk | Normality assessment | W-statistic, p-value, interpretation |
| One-sample t-test | Comparison vs age-reference | t, p, Cohen's d, effect label |
| Paired t-test | Pre-post change detection | t, p, effect size, direction |
| Mann-Whitney U | Non-parametric comparison | U, p, rank-biserial r |
| Spearman correlation | Cross-metric associations | ρ, p, strength label |

**Age-Stratified Reference Values (RMSSD, ms):**

| Age Range | Mean | SD | 15th %ile | 85th %ile |
|-----------|------|-----|-----------|-----------|
| 18-25 | 42.0 | 19.0 | 26.0 | 62.0 |
| 26-35 | 39.0 | 18.0 | 24.0 | 58.0 |
| 36-45 | 35.0 | 17.0 | 21.0 | 52.0 |
| 46-55 | 30.0 | 15.0 | 17.0 | 46.0 |
| 56-65 | 25.0 | 13.0 | 14.0 | 40.0 |
| 66+ | 21.0 | 11.0 | 12.0 | 34.0 |

*Source: Nunan et al. (2010). Scand J Med Sci Sports 20(1):e30-44*

**Clinical Decision Support Semaphore:**

| Risk Level | Color | Meaning | Action |
|------------|-------|---------|--------|
| GREEN | 🟢 | Normal/Favorable | Maintain current practices |
| YELLOW | 🟡 | Monitor/Borderline | Track trends, minor adjustments |
| ORANGE | 🟠 | Caution/Elevated | Active intervention recommended |
| RED | 🔴 | Alert/High Risk | Consult healthcare provider |

**Autonomic State Classification:**

| State | LF/HF Range | Clinical Meaning |
|-------|-------------|------------------|
| Parasympathetic Dominant | < 0.8 | Rest & digest, good recovery |
| Balanced | 0.8 - 2.0 | Healthy autonomic regulation |
| Sympathetic Dominant | > 3.0 | Stress response, reduced recovery |
| Dysregulated | Variable + low RMSSD | Impaired autonomic function |

**Scientific References:**
- Task Force (1996). Circulation 93(5):1043-65
- Shaffer & Ginsberg (2017). Front Public Health 5:258
- Nunan et al. (2010). Scand J Med Sci Sports 20(1):e30-44
- Thayer et al. (2012). Neurosci Biobehav Rev 36(2):747-56
- Cohen (1988). Statistical Power Analysis for the Behavioral Sciences

#### Performance Forecast

24-hour cognitive performance prediction:

**Features:**
- Peak performance time identification
- Circadian low point warning
- Post-lunch dip detection
- Critical window alerts
- Work schedule integration

#### Using the Profile Tools Engine

1. Navigate to **User Profile → Clinical Profile → Profile Tools Engine**
2. Select a tool from the dropdown (or choose "All Tools Summary")
3. Configure input parameters:
   - Sleep hours and quality
   - Hours awake
   - Chronotype selection
   - RMSSD value (from HRV analysis)
   - Resting heart rate
4. Click **🚀 Run Calculations**
5. Review results with component breakdowns
6. Export summary to Markdown if needed

#### Scientific References (Profile Tools Engine)

- Plews DJ, Laursen PB, Stanley J, Kilding AE, Buchheit M. Training adaptation and heart rate variability in elite endurance athletes: opening the door to effective monitoring. *Sports Med.* 2013;43(9):773-781.
- Kiviniemi AM, Hautala AJ, Kinnunen H, Tulppo MP. Endurance training guided individually by daily heart rate variability measurements. *Eur J Appl Physiol.* 2007;101(6):743-751.
- Hursh SR, Redmond DP, Johnson ML, et al. Fatigue models for applied research in warfighting. *Aviat Space Environ Med.* 2004;75(3 Suppl):A44-A53.
- Borbély AA. A two process model of sleep regulation. *Hum Neurobiol.* 1982;1(3):195-204.
- Thayer, J. F., & Lane, R. D. (2000). A model of neurovisceral integration in emotion regulation and dysregulation. *Journal of Affective Disorders, 61*(3), 201–216. https://doi.org/10.1016/S0165-0327(00)00338-4
- Laborde, S., Mosley, E., & Thayer, J. F. (2017). Heart rate variability and cardiac vagal tone in psychophysiological research: Recommendations for experiment planning, data analysis, and data reporting. *Frontiers in Psychology, 8*, 213. https://doi.org/10.3389/fpsyg.2017.00213

### Exploration Medical Record (NASA isolation missions)

Mission Control - Flight Surgeon now includes an exploration medical record aligned with NASA's Medical Information Systems & Tools (MIST) architecture and the Exploration Medical Capability (ExMC) guidance for Earth-independent care. Every entry is stored in the `medical_history` table (JSON payload) so longitudinal and group-level statistics can be performed later. Key fields:

| Field | Description | Units |
|-------|-------------|-------|
| `mission_profile` | Scenario (e.g., LUNAR-22, Gateway-30, Mars analog) | categorical |
| `record_date` | Log date used to align HRV/Garmin/space-weather context | YYYY-MM-DD |
| `mission_day` | Mission elapsed day (supports ≥22 days) | integer |
| `habitat` | Analog site (HERA, CHAPEA, NEEMO, etc.) | categorical |
| `eva_status` | EVA clearance (Cleared, Restricted, No EVA) | categorical |
| `eva_hours_72h` | EVA hours accumulated during the last 72 h | hours |
| `radiation_dose_msv` | Cumulative effective dose (auto-estimated from mission environment + EVA by default) | mSv |
| `space_weather_alert` | Space-weather alert (computed from NOAA Kp + >10 MeV proton flux by default) | categorical |
| `confinement_stress` | Stress indicator (can seed from objective HRV indices) | ordinal |
| `sleep_hours` | Sleep obtained in the last 24 h (seeds from Garmin daily sleep when available) | hours |
| `exercise_minutes` | Countermeasure exercise duration | minutes |
| `hydration_liters` | Water intake per day | liters |
| `behavioral_flags` | Team cohesion / cognitive notes | categorical |

The UI form includes chronic condition selectors, acute symptom checklists, and free-text notes for operational anomalies. Each submission either creates a new mission-day entry or updates the latest record, enabling high-resolution studies for 22-day isolation missions up to Mars analog campaigns.

#### Exploration Medical Analytics Dashboard

The Clinical Profile tab now exposes an **Exploration Medical Analytics** dashboard that aggregates every ExMC/EIMO entry into actionable indicators:

- **Radiation Gauge**: Displays the highest cumulative dose logged/estimated to date, percentage of the NASA **600 mSv career effective dose design limit** (STD-3001), and daily accumulation rate to highlight accelerating exposure trends.
- **EVA Workload Cards**: Summaries for average/peak EVA hours (rolling 72 h), days since the last EVA, and a clearance histogram so teams can identify when restrictions cluster around specific mission profiles.
- **Stress & Behavioral Trends**: Objective HRV stress/PNS time series and Garmin sleep duration trends are shown when available; subjective logs remain available for comparison (workload/stress notes).
- **Symptom & Behavioral Frequency Tables**: Top acute symptoms and behavioral health flags are tallied automatically, giving medical officers a quick triage list without exporting raw JSON.

All indicators update in real time once a record is saved, giving crews immediate feedback without leaving the Clinical Profile context.

#### Radiation Exposure Module (v1.8.80+)

The `radiation_exposure` module provides evidence-based dose rate estimates for space mission planning:

| Environment | Nominal Rate (mSv/day) | Reference |
|-------------|------------------------|-----------|
| Earth Surface | 0.0066 | UNSCEAR 2000 (~2.4 mSv/year) |
| Antarctica (high altitude) | 0.003–0.008 | Mishev et al. (2023) |
| Flight Altitude (35,000 ft) | 0.144 | FAA AC 120-52; O'Brien 1978 |
| Low Earth Orbit (ISS) | 0.20–0.73 | Berger et al. (2020); NASA LSAH 2023 |
| Lunar Gateway | 0.80–1.80 | Simonsen et al. (2025); ICRP 123 |
| Lunar Surface | 1.00–1.80 | Zhang et al. (2020), Science Advances |
| Mars Transit | 1.30–2.50 | Zeitlin et al. (2013), MSL RAD |
| Mars Surface | 0.45–0.80 | Hassler et al. (2014), MSL RAD |

**Key Features:**
- **Career Limit Tracking**: NASA STD-3001 Vol 1 Rev B sets career effective dose design limit at **600 mSv**
- **Alert Zones**: GO (<30%), MONITOR (30–60%), CAUTION (60–80%), NO-GO (>80%)
- **Solar Cycle Adjustment**: Dose rates modulated by solar cycle phase (minimum = higher GCR, maximum = lower GCR but more SPE risk)
- **EVA Multipliers**: Environment-specific shielding reduction factors for EVA operations
- **SPE Alerts**: Solar Particle Event risk flagged when NOAA S-scale ≥2

**EVA Risk Matrix:**
The Go/No-Go assessment follows ICAO/USAF FRMS-style risk matrix methodology:
- **Severity axis**: Based on cumulative career dose (Negligible/Minor/Major/Severe)
- **Likelihood axis**: Based on space weather conditions (S/G storm scales)
- **Recommendations**: Active dosimetry, task reassignment, shelter protocols

### Polar AccessLink VO₂max (optional)

If a crew member uses Polar Flow, the NASA Nutrition calculator can import and track VO₂max via Polar AccessLink. The system now provides **automated sync** with persistent token storage and historical tracking.

#### Quick Setup (Environment Variables)

1. Register an application in the [Polar AccessLink program](https://www.polar.com/accesslink-api/).
2. Set environment variables (never committed to source control):
   - `POLAR_ACCESSLINK_TOKEN` — OAuth bearer token
   - `POLAR_ACCESSLINK_USER_ID` — Polar Flow user ID
3. Restart the app. The NASA Nutrition calculator will show a **🔄 Sync from Polar** button.

#### Automated Sync Features (v1.8.5+)

The new Polar AccessLink automation module provides:

- **Persistent Token Storage**: OAuth tokens are encrypted and stored in the local database per user. No need to reconfigure on each app restart.
- **VO₂max History Tracking**: Every sync saves to a history table with timestamp, source attribution (Polar vs manual), and Polar fitness class.
- **Duplicate Detection**: The system avoids saving redundant entries if the value hasn't changed within 24 hours.
- **Manual Entry Fallback**: Click **💾 Save Manual Entry** to record lab-tested VO₂max values with proper attribution.
- **History Expander**: View recent VO₂max entries with dates, values, sources, and fitness classifications.

#### VO₂max Source Attribution

The calculator shows the source of the effective VO₂max value:
- **"Polar AccessLink sync"**: Latest value fetched from Polar API
- **"History (Polar)"** / **"History (Manual)"**: Value from stored history
- **"Manual entry"**: Directly entered in the form

#### Fitness Classifications

Based on Polar's methodology, VO₂max values are classified as:
- Very Poor: <25 mL/kg/min
- Poor: 25–39 mL/kg/min
- Fair: 40–44 mL/kg/min
- Moderate: 45–50 mL/kg/min
- Good: 51–56 mL/kg/min
- Very Good: 57–62 mL/kg/min
- Excellent: ≥63 mL/kg/min

Polar AccessLink provides access to body metrics, exercise intensity, and cardiorespiratory fitness data that have already been uploaded to Polar Flow's cloud infrastructure.

### Validated Clinical Scales

The platform includes scientifically validated instruments for fatigue and sleep assessment:

#### Samn-Perelli Fatigue Scale (Aviation Standard)

7-point scale for operational fatigue assessment, widely used in aviation fatigue risk management.

| Rating | Description | Risk Level |
|--------|-------------|------------|
| 1 | Fully alert, wide awake | LOW |
| 2 | Very lively, responsive | LOW |
| 3 | Okay, somewhat fresh | MODERATE |
| 4 | A little tired | MODERATE |
| 5 | Moderately tired, let down | HIGH |
| 6 | Extremely tired | CRITICAL |
| 7 | Completely exhausted | CRITICAL |

**Reference:** Samn SW, Perelli LP. *Estimating aircrew fatigue: a technique with application to airlift operations.* Brooks AFB, TX: USAF School of Aerospace Medicine; 1982.

#### Karolinska Sleepiness Scale (KSS)

9-point scale for momentary sleepiness, validated against EEG and behavioral measures.

| Rating | Description |
|--------|-------------|
| 1 | Extremely alert |
| 2 | Very alert |
| 3 | Alert |
| 4 | Fairly alert |
| 5 | Neither alert nor sleepy |
| 6 | Some signs of sleepiness |
| 7 | Sleepy, but no effort to stay awake |
| 8 | Sleepy, some effort to stay awake |
| 9 | Extremely sleepy, fighting sleep |

**Impairment Threshold:** KSS ≥ 7 indicates potential performance impairment.

**Reference:** Åkerstedt T, Gillberg M. *Int J Neurosci.* 1990;52(1-2):29-37.

#### Epworth Sleepiness Scale (ESS)

8-item questionnaire measuring general level of daytime sleepiness.

**Situations assessed:**
1. Sitting and reading
2. Watching TV
3. Sitting inactive in public
4. Passenger in car for 1 hour
5. Lying down in afternoon
6. Sitting and talking to someone
7. Sitting quietly after lunch (no alcohol)
8. In car, stopped in traffic

**Scoring:** Each item 0-3 (chance of dozing). Total score 0-24.

| Score | Interpretation |
|-------|----------------|
| 0-5 | Lower normal daytime sleepiness |
| 6-10 | Higher normal daytime sleepiness |
| 11-12 | Mild excessive daytime sleepiness |
| 13-15 | Moderate excessive daytime sleepiness |
| 16-24 | Severe excessive daytime sleepiness |

**Clinical Threshold:** ESS > 10 indicates excessive daytime sleepiness requiring clinical evaluation.

**Reference:** Johns MW. *A new method for measuring daytime sleepiness: the Epworth sleepiness scale.* Sleep. 1991;14(6):540-545.

#### Pittsburgh Sleep Quality Index (PSQI)

19-item questionnaire assessing sleep quality over the past month.

**7 Component Scores:**
1. Subjective sleep quality
2. Sleep latency
3. Sleep duration
4. Habitual sleep efficiency
5. Sleep disturbances
6. Use of sleeping medication
7. Daytime dysfunction

**Global Score:** Sum of components (0-21)
- 0-5: Good sleep quality
- 6-10: Poor sleep quality
- 11-15: Moderate sleep disturbance
- >15: Severe sleep disturbance

**Clinical Threshold:** PSQI > 5 indicates poor sleep quality.

**Reference:** Buysse DJ, et al. *The Pittsburgh Sleep Quality Index: a new instrument for psychiatric practice and research.* Psychiatry Res. 1989;28(2):193-213.

#### Fatigue Severity Scale (FSS)

9-item scale measuring the impact of fatigue on daily functioning.

**Items assess agreement (1-7) with statements about:**
- Motivation problems
- Exercise impacts
- Physical functioning
- Work/duty performance

**Scoring:** Mean score across 9 items.
- <3: No significant fatigue
- 3-4: Mild fatigue impact
- 4-5: Moderate fatigue impact
- ≥5: Severe fatigue impact

**Reference:** Krupp LB, et al. *Arch Neurol.* 1989;46(10):1121-1123.

#### Positive and Negative Affect Schedule (PANAS)

The PANAS is a 20-item self-report measure of affect developed by Watson, Clark, and Tellegen (1988). It is one of the most widely used measures of mood in psychological research.

**Structure:**
- **Positive Affect (PA):** 10 items measuring extent of enthusiastic, active, alert states
- **Negative Affect (NA):** 10 items measuring extent of distress, unpleasurable engagement

**Positive Affect Items:** Interested, Excited, Strong, Enthusiastic, Proud, Alert, Inspired, Determined, Attentive, Active

**Negative Affect Items:** Distressed, Upset, Guilty, Scared, Hostile, Irritable, Ashamed, Nervous, Jittery, Afraid

**Response Scale:** 5-point Likert scale
1. Very slightly or not at all
2. A little
3. Moderately
4. Quite a bit
5. Extremely

**Scoring:** Sum items for each subscale. Score range: 10-50 for each.

| PA Score | Interpretation |
|----------|----------------|
| 10-22 | Low positive affect (sadness, lethargy) |
| 23-39 | Moderate positive affect |
| 40-50 | High positive affect (energetic, engaged) |

| NA Score | Interpretation |
|----------|----------------|
| 10-14 | Low negative affect (calm, serene) |
| 15-22 | Moderate negative affect |
| 23-50 | High negative affect (distress, anxiety) |

**Clinical Significance:**
- PA and NA are largely independent dimensions
- High NA is associated with anxiety and depression
- Low PA is specifically linked to depression (distinct from high NA)
- Together they provide a comprehensive picture of affective state

**Available Languages:**
- **English:** Original validation (Watson, Clark, & Tellegen, 1988)
- **Spanish:** Validated translation (Sandín et al., 1999, Psicothema; α=0.92 PA, α=0.88 NA)

**References:**
- Watson D, Clark LA, Tellegen A. *Development and validation of brief measures of positive and negative affect: The PANAS scales.* J Pers Soc Psychol. 1988;54(6):1063-1070. DOI: 10.1037/0022-3514.54.6.1063
- Sandín B, et al. *Escalas PANAS de afecto positivo y negativo: Validación factorial y convergencia transcultural.* Psicothema. 1999;11(1):37-51.
- Crawford JR, Henry JD. *The Positive and Negative Affect Schedule (PANAS): Construct validity, measurement properties and normative data in a large non-clinical sample.* Br J Clin Psychol. 2004;43(3):245-265.

### Profile-Adjusted HRV Interpretation

HRV metrics are interpreted relative to age and sex-specific normative values:

**RMSSD Normative Values** (based on Nunan et al. 2010):

| Age Group | Male Mean±SD | Female Mean±SD |
|-----------|--------------|----------------|
| 18-25 | 42.0±15.0 ms | 45.0±18.0 ms |
| 26-35 | 38.0±14.0 ms | 42.0±16.0 ms |
| 36-45 | 32.0±12.0 ms | 36.0±14.0 ms |
| 46-55 | 26.0±10.0 ms | 30.0±12.0 ms |
| 56-65 | 22.0±9.0 ms | 25.0±10.0 ms |
| 65+ | 18.0±8.0 ms | 21.0±9.0 ms |

**Reference:** Nunan D, et al. *A quantitative systematic review of normal values for short‐term heart rate variability in healthy adults.* Pacing Clin Electrophysiol. 2010;33(11):1407-1417.

### Health Condition Adjustments

The system accounts for conditions that affect HRV baseline:

| Condition | HRV Effect | Adjustment |
|-----------|------------|------------|
| Beta-blockers | ↑ HRV | ×1.3 factor |
| Cardiac condition | ↓ HRV | ×0.85 factor |
| Diabetes | ↓ HRV | ×0.9 factor |
| Smoking | ↓ HRV | Noted in interpretation |

### Data Storage

User profiles and assessments are stored in:
- **Local mode:** JSON files in `data/profiles/` and `data/assessments/`
- **Docker mode:** PostgreSQL database with TimescaleDB for time-series optimization

All data remains under user control. No data is transmitted externally unless explicitly exported.

---

## Population Norms Comparison

The Population Norms tab enables comparison of your HRV metrics against scientifically validated reference values from large-scale studies.

### Scientific Sources

The platform integrates normative data from multiple peer-reviewed sources:

| Source | Sample Size | Population | Metrics |
|--------|-------------|------------|---------|
| Nunan et al. (2010) | n=21,438 | Meta-analysis of 44 studies | SDNN, RMSSD, pNN50, LF, HF, LF/HF |
| Ortega et al. (2024) | n=2,143 | Singapore multiethnic adults | RMSSD, SDNN stratified by age/sex |
| MESA Study (2016) | n=5,966 | Multi-ethnic US adults | Time and frequency domain |
| Task Force (1996) | - | ESC/NASPE guidelines | All standard metrics |

**References:**
- Nunan D, et al. *Pacing Clin Electrophysiol.* 2010;33(11):1407-1417. [PMID: 20663071](https://pubmed.ncbi.nlm.nih.gov/20663071/)
- Ortega E, et al. *J Gen Intern Med.* 2024;39(1):101-108. [PMID: 37755550](https://pubmed.ncbi.nlm.nih.gov/37755550/)
- O'Neal WT, et al. *Am J Cardiol.* 2016. [PMID: 27396499](https://pubmed.ncbi.nlm.nih.gov/27396499/)

### Age and Sex Stratification

HRV values are stratified by demographic factors:

**RMSSD Reference Values (ms) by Age and Sex:**

| Age Group | Male Mean±SD | Female Mean±SD |
|-----------|--------------|----------------|
| 18-25 | 42.0±15.0 | 45.0±18.0 |
| 26-35 | 38.0±14.0 | 42.0±16.0 |
| 36-45 | 32.0±12.0 | 36.0±14.0 |
| 46-55 | 26.0±10.0 | 30.0±12.0 |
| 56-65 | 22.0±9.0 | 25.0±10.0 |
| 65+ | 18.0±8.0 | 21.0±9.0 |

### Deviation Categories

Your values are classified relative to population norms:

| Category | Definition | Interpretation |
|----------|------------|----------------|
| Very Low | <5th percentile | Significantly below normal |
| Low | 5th-25th percentile | Below average |
| Normal | 25th-75th percentile | Within normal range |
| High | 75th-95th percentile | Above average |
| Very High | >95th percentile | Significantly elevated |

### Using the Population Norms Tab

1. **Upload and process HRV data** in any analysis tab
2. **Navigate to Population Norms tab**
3. **Enter demographics** (age, sex)
4. **Review comparison table** showing:
   - Your value for each metric
   - Population mean and standard deviation
   - Deviation in standard deviations
   - Percentile ranking
   - Category classification

### Clinical Interpretation Guidelines

- **Normal range:** Values within one standard deviation of the mean
- **Above/Below Average:** Values 1-2 SD from the mean may warrant monitoring
- **Very High/Low:** Values beyond 2 SD should be interpreted in clinical context

⚠️ **Important:** HRV varies significantly with posture, time of day, hydration, and measurement protocol. Compare within-subject trends for training decisions; use population norms for general health context.

---

## Blood Pressure Variability Analysis

Blood Pressure Variability (BPV) is an emerging biomarker for cardiovascular risk independent of mean blood pressure values. The BPV module complements HRV analysis for comprehensive autonomic assessment.

### Scientific Background

BPV reflects the beat-to-beat and visit-to-visit fluctuations in blood pressure mediated by:
- Baroreflex sensitivity
- Arterial stiffness
- Autonomic nervous system function
- End-organ damage

**Key References:**
- Parati G, et al. *J Clin Hypertens.* 2018;20(7):1133-1137. [PMID: 29927042](https://pubmed.ncbi.nlm.nih.gov/29927042/)
- Rothwell PM, et al. *Lancet.* 2010;375(9718):895-905. [PMID: 20226988](https://pubmed.ncbi.nlm.nih.gov/20226988/)
- Saren J, et al. *Age and Ageing.* 2024. [DOI: 10.1093/ageing/afae262](https://doi.org/10.1093/ageing/afae262)

### BPV Metrics

| Metric | Definition | Clinical Significance |
|--------|------------|----------------------|
| **SD** | Standard deviation of BP readings | Overall variability magnitude |
| **CV** | Coefficient of variation (SD/mean × 100) | Normalized variability |
| **ARV** | Average Real Variability (mean of absolute successive differences) | Short-term fluctuations |
| **SV** | Successive Variation (RMS of successive differences) | Beat-to-beat variability |
| **Pulse Pressure** | Systolic - Diastolic | Arterial stiffness indicator |
| **MAP** | Mean Arterial Pressure | Organ perfusion pressure |

### Risk Stratification

Based on clinical literature, elevated BPV is associated with:

| BPV Level | Systolic CV | Risk Implication |
|-----------|-------------|------------------|
| Low | <5% | Normal variability |
| Moderate | 5-10% | Monitoring recommended |
| High | 10-15% | Increased CV risk |
| Very High | >15% | Significant risk factor |

### HRV-BPV Correlation

The module calculates correlation between HRV and BPV metrics to assess autonomic coherence:

- **High correlation:** Synchronized autonomic regulation
- **Low correlation:** Autonomic dysregulation or baroreflex impairment
- **Inverse correlation:** May indicate specific pathophysiology

### Using the BPV Tab

1. **Import BP data** with systolic, diastolic, and timestamp columns
2. **Select analysis type:**
   - Short-term (beat-to-beat, 24-hour ambulatory)
   - Long-term (visit-to-visit, week-to-week)
3. **Click "Compute BPV Metrics"**
4. **Review results** including:
   - All BPV metrics with interpretations
   - Risk category assessment
   - HRV-BPV correlation analysis
   - Time series visualization

### Data Requirements

BPV analysis requires blood pressure data in one of these formats:
- CSV with columns: `timestamp`, `systolic`, `diastolic`
- Continuous BP monitor export (Finapres, Portapres)
- Home BP log with timestamps

### Limitations

⚠️ **Important Considerations:**
- BPV from office measurements less reliable than ambulatory monitoring
- White-coat effect can artificially increase BPV
- Irregular measurement intervals affect time-domain metrics
- Standard cuff measurements lack beat-to-beat resolution

---

## Circadian Physiology Module

The Circadian Physiology tab provides mathematical modeling of human circadian rhythms, enabling simulation of light exposure effects on the biological clock and prediction of circadian disruption.

### Scientific Foundation

The module implements validated mathematical models of the human circadian pacemaker:

| Model | Description | Best For |
|-------|-------------|----------|
| **Forger99** | Two-process model with direct light input | General circadian simulation |
| **Jewett99** | Modified Kronauer model with melatonin suppression | Light sensitivity studies |
| **Hannay19** | Amplitude-phase model with limit cycle | Phase shift prediction |
| **Hannay19TP** | Two-population extension | Split-sleep schedules |

**Citation:**
```
@software{franco_tavella_2023_8206871,
  author = {Franco Tavella and Kevin Hannay and Olivia Walch},
  title = {Arcascope/circadian},
  year = 2023,
  publisher = {Zenodo},
  doi = {10.5281/zenodo.8206871}
}
```

### Light Schedule Types

The module generates various light exposure patterns:

| Schedule | Description | Use Case |
|----------|-------------|----------|
| **Regular** | Fixed wake/sleep with ambient light | Baseline simulation |
| **Shift Work** | Rotating or fixed shift patterns | Occupational health |
| **Slam Shift** | Abrupt schedule change | Jet lag simulation |
| **Social Jetlag** | Weekend delay pattern | Lifestyle assessment |
| **Custom Pulse** | User-defined light pulses | Light therapy planning |

### Key Metrics

**Entrainment Signal Regularity Index (ESRI):**
- Quantifies how well a light schedule promotes stable circadian entrainment
- Range: 0 (irregular) to 1 (perfectly regular)
- Higher ESRI indicates more circadian-friendly schedules

**Phase Coherence:**
- Measures stability of circadian timing across days
- Based on circular statistics of phase markers (e.g., DLMO times)

**Social Jetlag Index:**
- Difference between weekend and weekday sleep midpoints
- >1 hour associated with adverse health outcomes

### Using the Circadian Tab

**Step 1: Configure Scenario (In-Tab Builder)**
1. Open the scenario builder panel at the top of the Circadian tab.
2. Pick one or more models (Hannay19 is the mission default).
3. Select a light schedule template and adjust its parameters (wake window, shift hours, custom pulse, etc.).
4. Define the simulation window (days, integration step, equilibration passes).
5. Toggle visualization flags (DLMO/CBT markers, light overlay) as needed.
6. Optionally **Save preset** (up to five) or load an existing scenario. Presets persist across reruns and multi-user sessions.
> **Profile sync:** Use **Align with active profile** to pull chronotype, mission profile, and latest NASA medical log data into the scenario builder. The stored configuration updates automatically whenever you switch astronauts.

**Step 2: Apply and Simulate**
1. Click **Apply scenario** once. All widgets are batched through the form, so heavy simulations only run after this action.
2. The light schedule plot updates immediately, followed by amplitude/phase trajectories for every selected model.

**Step 3: Analyze Outputs**
- Use the double-plotted actogram to inspect entrainment stability and rapid phase shifts.
- Review ESRI to quantify how entrainment-friendly the schedule is (0–1 scale).
- Compare DLMO/CBT markers between models to plan light therapy or shift rotations.
- Export the scenario (JSON) along with preset notes for mission planning logs.

### Clinical Applications

1. **Jet Lag Prediction:** Simulate travel across time zones
2. **Shift Work Assessment:** Evaluate rotation schedules
3. **Light Therapy Planning:** Optimize timing and duration
4. **Sleep Disorder Analysis:** Identify circadian misalignment
5. **Performance Forecasting:** Predict alertness windows

### Integration with HRV

Circadian phase affects HRV metrics:
- HRV typically peaks during sleep (parasympathetic dominance)
- Circadian disruption correlates with reduced HRV
- Use circadian simulation to contextualize HRV measurements

### Advanced Circadian Analysis Tools

#### Cosinor Analysis (phasetools.py)

Cosinor analysis fits a cosine function to time-series data to extract circadian parameters:

```
y(t) = M + A × cos(2πt/τ + φ)
```

Where:
- **M (MESOR)**: Midline Estimating Statistic of Rhythm - baseline level
- **A (Amplitude)**: Peak-to-trough difference / 2
- **φ (Acrophase)**: Time of peak value
- **τ (Period)**: Fixed at 24h for circadian analysis

**Available Functions:**
| Function | Description |
|----------|-------------|
| `cosinor()` | Fit cosinor model to data, return MESOR, amplitude, acrophase |
| `cosinor_phase()` | Extract phase only from time series |
| `cosinor_goals()` | Compare actual vs target phase for intervention planning |

**Clinical Applications:**
- Quantify circadian amplitude (reduced in aging, depression, dementia)
- Track phase shifts in jet lag recovery
- Monitor phase stability in shift workers

#### Phase Response Curves (prc.py)

Phase Response Curves (PRCs) describe how light pulses at different circadian phases shift the biological clock:

| Component | Description |
|-----------|-------------|
| **PhaseResponseCurveLight** | Full PRC computation for light stimuli |
| **IntensityResponseCurveLight** | How pulse intensity affects phase shift magnitude |
| **DosageResponseCurve** | Relationship between light duration and effect |
| **PRCFinder** | Automated optimal light timing recommendations |

**Light Pulse Parameters:**
- `RimmerLightPulseLight`: Standard Rimmer protocol light pulses
- `make_pulse()`: Generate custom light pulses
- `get_pulse()`: Retrieve preset pulse configurations

**Use Cases:**
1. **Jet Lag Optimization**: Find optimal light exposure windows post-travel
2. **Shift Work Adaptation**: Plan light exposure for night shift workers
3. **Delayed Sleep Phase**: Determine morning light therapy timing
4. **Advanced Sleep Phase**: Plan evening light exposure

#### Two-Process Model of Sleep (sleep.py)

The Two-Process Model (Borbély, 1982) describes sleep-wake regulation:

**Process S (Homeostatic):**
- Sleep pressure accumulates during wakefulness
- Dissipates exponentially during sleep
- $$S(t) = S_0 \times e^{-t/\tau_d}$$ (sleep decay)
- $$S(t) = S_{max} - (S_{max} - S_0) \times e^{-t/\tau_r}$$ (wake rise)

**Process C (Circadian):**
- 24-hour oscillation in sleep propensity
- Interacts with Process S to determine alertness

**Available Functions:**
| Function | Description |
|----------|-------------|
| `TwoProcessModel` | Complete model with customizable parameters |
| `sleep_midpoint()` | Calculate sleep midpoint from wake/sleep times |
| `cluster_sleep_periods_scipy()` | Detect sleep bouts from actigraphy data |

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `tau_d` | 18.18 h | Process S decay time constant |
| `tau_r` | 4.2 h | Process S rise time constant |
| `S_0` | 0.35 | Initial sleep pressure |
| `S_max` | 0.75 | Maximum sleep pressure |
| `circadian_amplitude` | 0.12 | Process C amplitude |

#### Synthetic Data Generation (synthetic_data.py)

Generate realistic wearable data for testing and validation:

| Function | Description |
|----------|-------------|
| `generate_activity_from_light()` | Create activity patterns from light schedules |

**Use Cases:**
- Algorithm validation without real patient data
- Training machine learning models
- Protocol development and testing
- Educational demonstrations

#### Wearable Data Readers (readers.py)

Load data from various wearable devices:

| Function | Input Format | Output |
|----------|--------------|--------|
| `load_json()` | Standard JSON with timestamps | WearableData object |
| `load_csv()` | CSV with time/activity columns | WearableData object |
| `load_actiwatch()` | Actiwatch CSV export | WearableData object |
| `resample_df()` | Any DataFrame | Resampled to target frequency |
| `combine_wearable_dataframes()` | Multiple DataFrames | Merged time series |

**WearableData Class:**
```python
@dataclass
class WearableData:
    time_total: NDArray[np.float64]  # Hours since start
    steps: NDArray[np.float64]       # Step counts
    light_estimate: NDArray[np.float64]  # Estimated light exposure
```

### Circadian-HRV Integration Research

Recent research highlights important connections:

1. **DLMO-HRV Correlation**: Dim Light Melatonin Onset (DLMO) timing correlates with nocturnal HRV patterns (Scheer et al., 2009)

2. **Social Jetlag and HRV**: >2h social jetlag associated with 15-20% reduction in RMSSD (Rutters et al., 2014)

3. **Shift Work and Autonomic Dysfunction**: Night shift workers show reduced HRV compared to day workers, partially mediated by circadian misalignment (Boudreau et al., 2013)

4. **Light Therapy for HRV**: Morning bright light therapy (10,000 lux) improves both circadian alignment and vagal tone (Gronfier et al., 2004)

**Recommended Protocols:**
| Assessment | Protocol |
|------------|----------|
| Circadian HRV Profile | 24-48h Holter + DLMO measurement |
| Shift Work Assessment | Pre/post shift HRV + light exposure logging |
| Jet Lag Recovery | Daily morning HRV + circadian simulation |
| Light Therapy Monitoring | Weekly HRV + subjective sleepiness |

---

## Autonomic Function Tests

*Clinical-grade autonomic reflex assessments with comprehensive step-by-step protocols*

### Introduction: The Ewing Battery and Beyond

The cardiovascular autonomic reflex tests described in this section derive from the seminal work of **Ewing and colleagues** at the University of Edinburgh, who in 1976 demonstrated that a battery of simple bedside tests could detect diabetic autonomic neuropathy and predict survival disadvantage (Lefrandt et al., 2010). These tests remain the **gold standard** for non-invasive assessment of cardiovascular autonomic function (Task Force, 1996; Baker et al., 2024).

#### Physiological Basis

The autonomic nervous system (ANS) maintains cardiovascular homeostasis through two complementary divisions:

| Division | Primary Neurotransmitter | Cardiac Effects | Primary Receptors |
|----------|-------------------------|-----------------|-------------------|
| **Parasympathetic** | Acetylcholine | ↓ Heart rate, ↓ AV conduction | Muscarinic (M₂) |
| **Sympathetic** | Norepinephrine | ↑ Heart rate, ↑ Contractility, ↑ Conduction | β₁-adrenergic |

Cardiovascular autonomic testing exploits specific physiological reflexes to selectively assess:
- **Cardiovagal function** (parasympathetic → heart)
- **Adrenergic function** (sympathetic → heart and vasculature)
- **Baroreflex sensitivity** (integrated feedback control)

#### Pre-Test Requirements

Before performing any autonomic function test, ensure standardized conditions:

| Requirement | Rationale |
|-------------|-----------|
| **Fasting ≥2 hours** | Postprandial blood flow redistribution affects responses |
| **No caffeine ≥12 hours** | Adenosine receptor blockade alters vagal tone |
| **No alcohol ≥24 hours** | Acute alcohol suppresses HRV |
| **No tobacco ≥2 hours** | Nicotine stimulates sympathetic activity |
| **Quiet, temperature-controlled room (22-24°C)** | Environmental stress confounds results |
| **Supine rest ≥10 minutes** | Achieve stable baseline autonomic state |
| **Empty bladder** | Bladder distension triggers sympathetic activation |

---

### Test 1: Deep Breathing Test (E:I Ratio)

**Primary Assessment:** Cardiovagal (parasympathetic) function

#### Physiological Mechanism

The deep breathing test exploits **respiratory sinus arrhythmia (RSA)**, the physiological variation in heart rate linked to the respiratory cycle. During inspiration, vagal efferent activity to the heart is inhibited ("vagal gating"), producing relative tachycardia. During expiration, vagal tone is restored, producing relative bradycardia (Quispe & Novak, 2021).

This reflex is mediated by:
1. **Pulmonary stretch receptors** → nucleus tractus solitarius (NTS)
2. **Central respiratory oscillator** (pre-Bötzinger complex) → nucleus ambiguus
3. **Cardiac vagal preganglionic neurons** → sinoatrial node

The magnitude of RSA is directly proportional to **cardiovagal tone** and declines with age (~2-3 bpm per decade after age 30) (Kowalewski & Urban, 2004).

#### Step-by-Step Protocol

**Equipment Required:**
- Continuous ECG or heart rate monitor (≥250 Hz sampling recommended)
- Metronome or visual pacer (for 6 breaths/minute = 5s in, 5s out)
- Stopwatch

**Procedure:**

1. **Preparation (5 minutes)**
   - Subject supine in quiet room
   - Attach ECG leads or HR monitor
   - Explain procedure: "Breathe deeply and slowly following the pacer"
   - Practice 2-3 breaths to ensure understanding

2. **Baseline Recording (1 minute)**
   - Record spontaneous breathing as baseline
   - Note resting heart rate

3. **Deep Breathing Protocol (1 minute)**
   - Start metronome/pacer at **6 breaths per minute** (10-second cycles)
   - Instruct: "Breathe IN for 5 seconds... breathe OUT for 5 seconds"
   - Record exactly **6 complete respiratory cycles**
   - Ensure maximal but comfortable tidal volume

4. **Post-Test Recovery (1 minute)**
   - Return to spontaneous breathing
   - Continue recording for normalization

**In-App Implementation:**

1. Navigate to **ANS Function Tests** tab
2. Expand **"Deep Breathing"** section
3. Enter parameters:
   - **Start time:** Second when paced breathing began (e.g., 60s)
   - **Cycle length:** 10 seconds (for 6 breaths/min)
   - **Number of cycles:** 6
4. Click **"Compute Deep Breathing"**

#### Calculated Metrics

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **E:I Ratio** | Mean(max RR during expiration) / Mean(min RR during inspiration) | Primary outcome |
| **E-I Difference** | Mean(max RR) - Mean(min RR) in ms | Absolute magnitude |
| **HR Difference** | Mean HR change (bpm) across cycles | Clinical convention |

#### Interpretation & Normal Values

| Age Group | E:I Ratio (Normal) | HR Difference (Normal) |
|-----------|--------------------|------------------------|
| 20-29 years | ≥1.22 | ≥15 bpm |
| 30-39 years | ≥1.18 | ≥13 bpm |
| 40-49 years | ≥1.14 | ≥11 bpm |
| 50-59 years | ≥1.10 | ≥9 bpm |
| 60-69 years | ≥1.07 | ≥7 bpm |
| ≥70 years | ≥1.04 | ≥5 bpm |

*Source: Adapted from Ziegler et al., 2001; Alauddin et al., 2024*

**Abnormal Result Interpretation:**
- **E:I ratio <1.10** (age-adjusted): Suggests **cardiovagal dysfunction**
- **Absent respiratory variation**: Severe vagal impairment or complete autonomic failure

**Clinical Conditions with Reduced E:I Ratio:**
- Diabetic autonomic neuropathy
- Parkinson's disease / MSA
- Heart failure
- Post-cardiac transplant
- Aging (physiological decline)

---

### Test 2: Valsalva Maneuver

**Primary Assessment:** Integrated cardiovagal and adrenergic function

#### Physiological Mechanism

The Valsalva maneuver produces a characteristic **four-phase cardiovascular response** that tests both parasympathetic and sympathetic pathways (Randall et al., 2019; Baker et al., 2024):

| Phase | Hemodynamic Event | ANS Response |
|-------|-------------------|--------------|
| **I** (Onset) | ↑ Intrathoracic pressure → transient ↑ BP | None (mechanical) |
| **II Early** | ↓ Venous return → ↓ Cardiac output → ↓ BP | Baroreceptor-mediated ↑ HR |
| **II Late** | Sympathetic vasoconstriction → partial BP recovery | Adrenergic compensation |
| **III** (Release) | Sudden ↓ Intrathoracic pressure → brief ↓ BP | None (mechanical) |
| **IV** (Overshoot) | ↑ Venous return + persistent vasoconstriction → ↑ BP | Vagal bradycardia reflex |

The **Valsalva ratio** (VR) reflects the magnitude of vagal recovery in Phase IV relative to the sympathetic tachycardia in Phase II.

#### Step-by-Step Protocol

**Equipment Required:**
- Continuous ECG monitor
- Manometer or pressure gauge (target: 40 mmHg)
- Stopwatch
- Optional: continuous beat-to-beat blood pressure (Finapres/CNAP)

**Procedure:**

1. **Setup (2 minutes)**
   - Subject seated or semi-recumbent (45°)
   - Attach ECG and (if available) beat-to-beat BP monitor
   - Connect mouthpiece to manometer
   - Explain: "Blow into the tube and maintain the pressure at 40 for 15 seconds"

2. **Practice Trial**
   - Have subject practice maintaining 40 mmHg expiratory pressure
   - Verify no air leak (nose clip may be needed)

3. **Baseline (30 seconds)**
   - Record resting ECG for stable baseline

4. **Valsalva Strain (15 seconds)**
   - Mark exact START time
   - Subject exhales against closed glottis maintaining **40 mmHg** for **15 seconds**
   - Monitor pressure gauge for compliance
   - Mark exact END time

5. **Recovery (45 seconds)**
   - Release strain; resume normal breathing
   - Continue recording for **≥45 seconds** post-strain
   - Phase IV overshoot typically occurs at 20-30 seconds post-release

**In-App Implementation:**

1. Navigate to **ANS Function Tests** tab
2. Expand **"Valsalva Ratio"** section
3. Enter parameters:
   - **Phase II Start:** Second when strain began (e.g., 30s)
   - **Phase II End:** Second when strain ended (e.g., 45s = 30+15)
   - **Phase IV Start:** Second when strain released (= Phase II End)
   - **Phase IV End:** 20-30 seconds after release (e.g., 75s)
4. Click **"Compute Valsalva Ratio"**

#### Calculated Metrics

| Metric | Formula | What It Assesses |
|--------|---------|------------------|
| **Valsalva Ratio** | RR_max(Phase IV) / RR_min(Phase II) | Cardiovagal function |
| **Phase II BP late** | Slope of BP recovery during late Phase II | Adrenergic function |
| **Phase IV Overshoot** | Peak BP above baseline | Sympathetic vasoconstriction |
| **Pressure Recovery Time (PRT)** | Time from Phase III nadir to baseline BP | Adrenergic function |

#### Interpretation & Normal Values

| Age Group | Valsalva Ratio (Normal) | Borderline | Abnormal |
|-----------|-------------------------|------------|----------|
| 10-29 years | ≥1.50 | 1.20-1.49 | <1.20 |
| 30-39 years | ≥1.45 | 1.15-1.44 | <1.15 |
| 40-49 years | ≥1.35 | 1.10-1.34 | <1.10 |
| 50-59 years | ≥1.25 | 1.05-1.24 | <1.05 |
| ≥60 years | ≥1.15 | 1.00-1.14 | <1.00 |

*Source: Ewing criteria; Phurpa & Ferdousi, 2021*

**Abnormal Response Patterns:**

| Pattern | Phase II | Phase IV | Indicates |
|---------|----------|----------|-----------|
| **Square-wave** | Flat (no HR increase) | Absent overshoot | Severe autonomic failure |
| **Absent Phase IV overshoot** | Present | Absent | Adrenergic dysfunction |
| **Prolonged Phase II recovery** | Slow | Delayed | Early sympathetic impairment |

---

### Test 3: Lying-to-Standing Test (30:15 Ratio)

**Primary Assessment:** Cardiovagal and early adrenergic response to orthostatic challenge

#### Physiological Mechanism

Upon standing, approximately **500-700 mL of blood** pools in the lower extremities due to gravity. This triggers a coordinated autonomic response (Baker et al., 2024):

1. **Immediate Phase (0-15 seconds):**
   - ↓ Venous return → ↓ Stroke volume → ↓ BP
   - Baroreceptor unloading → **vagal withdrawal** → Tachycardia
   - **Beat 15** captures maximum HR (shortest RR interval)

2. **Secondary Phase (15-30 seconds):**
   - Sympathetic vasoconstriction restores BP
   - **Vagal rebound** (baroreflex-mediated) → Relative bradycardia
   - **Beat 30** captures recovery HR (longest RR interval)

The **30:15 ratio** quantifies the integrity of this biphasic vagal response.

#### Step-by-Step Protocol

**Equipment Required:**
- Continuous ECG monitor
- Sphygmomanometer (for orthostatic BP measurement)
- Stopwatch

**Procedure:**

1. **Supine Baseline (5 minutes)**
   - Subject supine, completely relaxed
   - Record stable baseline HR and BP
   - Note baseline RR interval

2. **Standing Command**
   - Instruct: "When I say 'stand,' rise as quickly as you can and remain still"
   - Mark exact STAND time on recording

3. **Standing Phase (3 minutes)**
   - Subject stands motionless
   - **Do not allow leg crossing, fidgeting, or leaning**
   - Measure BP at 1 minute and 3 minutes standing

4. **Data Analysis**
   - Identify **RR interval at beat 15** after standing (typically shortest)
   - Identify **RR interval at beat 30** after standing (typically longest)
   - Calculate ratio

**In-App Implementation:**

1. Navigate to **ANS Function Tests** tab
2. Expand **"30:15 Ratio"** section
3. Enter parameters:
   - **Stand time:** Exact second when subject stood (e.g., 300s)
   - **Window 15:** Time range containing beat 15 (e.g., 308-312s ≈ 10s after standing)
   - **Window 30:** Time range containing beat 30 (e.g., 318-325s ≈ 20s after standing)
4. Click **"Compute 30:15 Ratio"**

#### Interpretation & Normal Values

| Age Group | 30:15 Ratio (Normal) | Borderline | Abnormal |
|-----------|----------------------|------------|----------|
| 20-39 years | ≥1.15 | 1.04-1.14 | <1.04 |
| 40-59 years | ≥1.10 | 1.01-1.09 | <1.01 |
| ≥60 years | ≥1.04 | 0.98-1.03 | <0.98 |

*Source: Kowalewski & Urban, 2004; Sharma et al., 2023*

**Orthostatic Blood Pressure Criteria:**

| Condition | Systolic BP Change | Diastolic BP Change |
|-----------|-------------------|---------------------|
| **Normal** | ↓ <20 mmHg | ↓ <10 mmHg |
| **Orthostatic Hypotension** | ↓ ≥20 mmHg | ↓ ≥10 mmHg |
| **Severe OH** | ↓ ≥30 mmHg | ↓ ≥15 mmHg |
| **Delayed OH** | ↓ ≥20/10 mmHg after 3 minutes | (Calió et al., 2025) |

---

### Test 4: Isometric Handgrip Test

**Primary Assessment:** Sympathetic adrenergic function (blood pressure response)

#### Physiological Mechanism

Sustained isometric muscle contraction activates the **exercise pressor reflex** through:

1. **Mechanoreceptor activation** (Group III afferents) → Immediate response
2. **Metaboreceptor activation** (Group IV afferents) → Sustained response from metabolite accumulation

These afferents synapse in the **rostral ventrolateral medulla (RVLM)**, the primary sympathetic premotor nucleus, producing:
- ↑ Sympathetic outflow to resistance vessels
- ↑ Cardiac sympathetic drive (↑ HR, ↑ contractility)
- ↓ Vagal tone

The net effect is a **sustained increase in blood pressure** proportional to sympathetic efferent integrity (Quispe & Novak, 2021).

#### Step-by-Step Protocol

**Equipment Required:**
- Handgrip dynamometer with maximal voluntary contraction (MVC) measurement
- Sphygmomanometer
- Stopwatch

**Procedure:**

1. **Determine Maximum Voluntary Contraction (MVC)**
   - Subject squeezes dynamometer with maximum effort × 3 attempts
   - Record highest value as MVC (e.g., 40 kg)

2. **Calculate Target Force**
   - Target = **30% of MVC** (e.g., 12 kg for 40 kg MVC)
   - This intensity produces metabolite accumulation without fatigue

3. **Baseline Measurement**
   - Record resting BP (both arms)
   - Record resting HR

4. **Sustained Handgrip (3-5 minutes)**
   - Subject maintains **30% MVC** grip with dominant hand
   - Monitor force output for compliance
   - Measure BP at **1, 2, and 3 minutes** of sustained grip
   - Continue to 5 minutes if tolerated

5. **Recovery (2 minutes)**
   - Release grip; measure BP at 1 and 2 minutes post-grip

**In-App Implementation:**

The handgrip test requires manual BP measurements; the app assists with:
1. **MVC Calculator:** Enter 3 attempts → calculates 30% target
2. **Timer:** Guides measurement intervals
3. **Data Entry:** Record BP values for automatic calculation

#### Interpretation & Normal Values

| Outcome | Normal Response | Abnormal Response |
|---------|-----------------|-------------------|
| **Diastolic BP Rise** | ↑ ≥16 mmHg by minute 3 | ↑ <10 mmHg |
| **Systolic BP Rise** | ↑ ≥20 mmHg | Variable (less specific) |
| **Heart Rate Rise** | ↑ 10-20 bpm | Blunted (<10 bpm) |

*Source: Quispe & Novak, 2021; Alauddin et al., 2024*

**Abnormal Response Interpretation:**
- **Blunted BP response (<10 mmHg DBP rise):** Suggests sympathetic efferent dysfunction
- **Exaggerated BP response (>40 mmHg):** May indicate hyper-adrenergic state

---

### Test 5: Orthostatic Blood Pressure Response

**Primary Assessment:** Integrated sympathetic vasoconstrictor function

#### Physiological Mechanism

The sustained orthostatic challenge (3+ minutes) tests the ability of sympathetic vasoconstriction to maintain blood pressure against gravitational pooling. Unlike the 30:15 ratio (which assesses early vagal responses), sustained standing reveals **adrenergic insufficiency** (Baker et al., 2024).

Orthostatic hypotension (OH) results from failure of:
1. **Baroreflex-mediated sympathetic activation**
2. **Peripheral vasoconstriction** (α₁-adrenergic)
3. **Renin-angiotensin-aldosterone system** (delayed)
4. **Venous compliance** (postural reflexes)

#### Step-by-Step Protocol

**Equipment Required:**
- Sphygmomanometer (preferably automated)
- Optional: Beat-to-beat BP monitor, tilt table

**Procedure:**

1. **Supine Baseline (5-10 minutes)**
   - Subject supine for full equilibration
   - Measure BP × 2 (1 minute apart); average for baseline

2. **Active Standing Test**
   - Subject stands unassisted
   - Measure BP immediately (within 30 seconds)
   - Measure BP at **1, 2, and 3 minutes** standing
   - For delayed OH: continue to 5-10 minutes

3. **Tilt Table Alternative (70° head-up)**
   - Passive tilting eliminates muscle pump contribution
   - More sensitive for detecting autonomic failure
   - Standard duration: 10 minutes minimum, 45 minutes for vasovagal syncope provocation

#### Interpretation & Normal Values

| Classification | Criteria | Clinical Significance |
|----------------|----------|----------------------|
| **Normal** | ↓SBP <20, ↓DBP <10 mmHg | Intact autonomic function |
| **Classical OH** | ↓SBP ≥20 or ↓DBP ≥10 mmHg within 3 min | Autonomic failure |
| **Initial OH** | ↓SBP >40 or ↓DBP >20 mmHg within 15 sec | Transient mismatch |
| **Delayed OH** | ↓SBP ≥20/↓DBP ≥10 mmHg after 3 min | Progressive failure |
| **POTS** | HR ↑≥30 bpm (or ≥120 bpm) without OH | Hyperadrenergic/neuropathic |

*Source: Freeman et al., 2011; Calió et al., 2025; Durstenfeld et al., 2025*

---

### Composite Scoring: The Ewing Score

The original **Ewing battery** combines multiple tests into a composite autonomic dysfunction score:

| Score | Criteria |
|-------|----------|
| **0** | All tests normal |
| **1** | 1 abnormal cardiovagal test |
| **2** | 2 abnormal cardiovagal tests |
| **3** | 2 abnormal cardiovagal + 1 abnormal adrenergic test |
| **4** | 2 abnormal cardiovagal + 2 abnormal adrenergic tests |
| **5** | All tests abnormal |

**Interpretation:**
- **Score 0-1:** Normal or early involvement
- **Score 2-3:** Definite autonomic neuropathy
- **Score 4-5:** Severe/advanced autonomic failure

*Source: Lefrandt et al., 2010; Shobhawat et al., 2025*

---

### Clinical Applications

| Condition | Key Findings |
|-----------|--------------|
| **Diabetic Autonomic Neuropathy** | ↓E:I ratio, ↓Valsalva ratio, OH |
| **Parkinson's Disease** | OH, ↓Phase IV overshoot, ↓30:15 ratio |
| **Multiple System Atrophy** | Severe OH, absent Phase IV, pan-autonomic failure |
| **POTS** | ↑HR ≥30 bpm standing, normal BP, ↑Valsalva HR response |
| **Pure Autonomic Failure** | Severe OH, absent all responses |
| **Long COVID** | Variable dysautonomia, often ↓30:15 ratio, POTS features |

---

### References for Autonomic Function Tests

1. **Task Force of ESC and NASPE** (1996). Heart rate variability: Standards of measurement, physiological interpretation and clinical use. *Circulation*, 93(5), 1043-1065. [DOI: 10.1161/01.CIR.93.5.1043](https://doi.org/10.1161/01.CIR.93.5.1043)

2. **Baker, J.R., Hira, R., Uppal, J., & Raj, S.R.** (2024). Clinical assessment of the autonomic nervous system. *Cardiac Electrophysiology Clinics*. [DOI: 10.1016/j.ccep.2024.02.001](https://doi.org/10.1016/j.ccep.2024.02.001) | [PMID: 39084717](https://pubmed.ncbi.nlm.nih.gov/39084717/)

3. **Quispe, R.C., & Novak, P.** (2021). Auxiliary tests of autonomic functions. *Journal of Clinical Neurophysiology*, 38(5). [DOI: 10.1097/WNP.0000000000000626](https://doi.org/10.1097/WNP.0000000000000626) | [PMID: 34009848](https://pubmed.ncbi.nlm.nih.gov/34009848/)

4. **Żyliński, M., Niewiadomski, W., Cybulski, G., & Gąsiorowska, A.** (2021). Device for controlling stimulus self-application during autonomic nervous system tests. *Medical Devices: Evidence and Research*, 14, 177-187. [DOI: 10.2147/MDER.S300384](https://doi.org/10.2147/MDER.S300384) | [PMID: 34104008](https://pubmed.ncbi.nlm.nih.gov/34104008/)

5. **Randall, E.B., Billeschou, A., Brinth, L.S., Mehlsen, J., & Olufsen, M.S.** (2019). A model-based analysis of autonomic nervous function in response to the Valsalva maneuver. *Journal of Applied Physiology*, 127(5), 1382-1402. [DOI: 10.1152/japplphysiol.00015.2019](https://doi.org/10.1152/japplphysiol.00015.2019) | [PMID: 31369335](https://pubmed.ncbi.nlm.nih.gov/31369335/)

6. **Kowalewski, M.A., & Urban, M.** (2004). Short- and long-term reproducibility of autonomic measures in supine and standing positions. *Clinical Autonomic Research*, 14(4), 249-257. [PMID: 12889989](https://pubmed.ncbi.nlm.nih.gov/12889989/)

7. **Lefrandt, J.D., Smit, A.J., Zeebregts, C.J., Gans, R.O., & Hoogenberg, K.H.** (2010). Autonomic dysfunction in diabetes: A consequence of cardiovascular damage. *Hormone and Metabolic Research*, 42 Suppl 1, S50-S55. [PMID: 20879972](https://pubmed.ncbi.nlm.nih.gov/20879972/)

8. **Ziegler, D., Laude, D., Akila, F., & Elghozi, J.L.** (2001). Time- and frequency-domain estimation of early diabetic cardiovascular autonomic neuropathy. *Diabetes Care*, 24(10), 1793-1798. [PMID: 11794718](https://pubmed.ncbi.nlm.nih.gov/11794718/)

9. **Phurpa, M., & Ferdousi, S.** (2021). Short-term heart rate variability: A technique to detect subclinical cardiac autonomic neuropathy in type 2 diabetes mellitus. *Journal of Bangladesh Society of Physiologists*, 16(1). [PMID: 33830127](https://pubmed.ncbi.nlm.nih.gov/33830127/)

10. **Sharma, V., Pattnaik, S., Ahluwalia, H., & Kaur, M.** (2023). Pre-pandemic autonomic function as a predictor of the COVID clinical course in young adults. *Clinical and Experimental Pharmacology and Physiology*, 50(8). [DOI: 10.1111/1440-1681.13776](https://doi.org/10.1111/1440-1681.13776) | [PMID: 37122115](https://pubmed.ncbi.nlm.nih.gov/37122115/)

11. **Alauddin, W., Chaswal, M., Bashir, M., & Isser, H.S.** (2024). Cardiovascular autonomic modulation in chronic coronary syndrome following percutaneous coronary intervention. *Cureus*, 16(7), e65092. [DOI: 10.7759/cureus.65092](https://doi.org/10.7759/cureus.65092) | [PMID: 39171068](https://pubmed.ncbi.nlm.nih.gov/39171068/)

12. **Durstenfeld, M.S., et al.** (2025). Case-control study of autonomic symptoms in the setting of Long COVID with tilt table testing. *PLoS ONE*. [DOI: 10.1371/journal.pone.0335218](https://doi.org/10.1371/journal.pone.0335218) | [PMID: 41134786](https://pubmed.ncbi.nlm.nih.gov/41134786/)

13. **Calió, B., et al.** (2025). Delayed orthostatic hypotension in Parkinson's disease and in the general ageing population. *Age and Ageing*. [DOI: 10.1093/ageing/afaf187](https://doi.org/10.1093/ageing/afaf187) | [PMID: 40622385](https://pubmed.ncbi.nlm.nih.gov/40622385/)

14. **Shobhawat, M., et al.** (2025). Assessing the impact of BMI and glycaemic control on cardiac autonomic neuropathy in patients with early and long-standing diabetes mellitus. *Annals of Indian Academy of Neurology*. [DOI: 10.1177/09727531251384548](https://doi.org/10.1177/09727531251384548) | [PMID: 41280749](https://pubmed.ncbi.nlm.nih.gov/41280749/)

---

## Space Data: Impact Predictions

The Space Weather Impact Predictions feature calculates exact arrival times for different categories of solar energy hitting Earth, providing Polar H10 EKG monitoring recommendations optimized for your research on biological effects.

Impact predictions live in the **🌐 Space Data** tab. The dashboard is **manual/on-demand**: click **🔄 Fetch Impact Predictions** to compute updated arrival times. If the network is unavailable, the app will keep showing the last available cached context and surface any fetch errors.

**Debugging note (hangs/freezes):** The Space Data tab now includes a **📋 Space Data step log (debug)** panel that records each fetch step with **duration + error**. If a “run all” action is slow, use the **🧪 Step-by-step (debug hangs)** expander to run each sub-step independently and pinpoint the culprit source.
If a specific sub-step stalls on your network, lower/raise **Step timeout (seconds)** in the step-by-step panel (the UI will fail fast instead of freezing).

### Energy Categories Tracked

| Category | Symbol | Source | Travel Time | Detection Method |
|----------|--------|--------|-------------|------------------|
| **Photon/X-ray** | ☀️ | Solar flares | ~8.3 min (instantaneous at detector) | GOES X-ray flux |
| **SEP (Protons)** | ⚡ | Solar flares/CMEs | Minutes to hours | GOES integral proton flux |
| **Solar Wind Plasma** | 🌊 | L1 (DSCOVR/ACE) | 30-60 min from L1 | SWPC plasma-1-day.json |
| **Geomagnetic** | 🧲 | Magnetosphere | Immediate (ongoing) | Kp and Dst indices |

### Understanding Arrival Times

All times are displayed in **Bogotá, Colombia timezone (UTC-5)** for your research location.

#### Photon/X-ray Events
- **What**: Solar flare electromagnetic radiation
- **Travel time**: ~8.3 minutes from Sun to Earth
- **Display**: Observation time equals impact time (already at Earth when detected)
- **Biological relevance**: Ionospheric disturbance onset, potential acute autonomic response

#### Solar Energetic Particles (SEPs)
- **What**: High-energy protons (>10 MeV) accelerated by flares/CME shocks
- **Travel time**: Near-instantaneous at geostationary orbit
- **NOAA S-Scale**: S1 (Minor) → S5 (Extreme) based on flux thresholds
- **Biological relevance**: Radiation exposure, documented HRV perturbations during major events

#### Solar Wind Plasma
- **What**: Solar wind measured at L1 Lagrange point (~1.5 million km from Earth)
- **Travel time**: Calculated as `L1_distance / solar_wind_speed`
  - Typical: 30-60 minutes depending on speed (300-800 km/s)
- **Formula**: `ETA = observation_time + (1,500,000 km / speed_km_s)`
- **Biological relevance**: Geomagnetic coupling, storm onset timing

#### Geomagnetic Conditions
- **What**: Current state of Earth's magnetic field
- **Indices**: Kp (0-9 scale), Dst (nT, negative = storm)
- **G-Scale**: G1 (Minor) → G5 (Extreme) based on Kp thresholds
- **Biological relevance**: Published associations with HRV depression, cardiovascular events

### Severity Classification

| Severity | Color | Kp Equivalent | Biological Implication |
|----------|-------|---------------|------------------------|
| **QUIET** | ⚪ Gray | <4 | Ideal baseline recording |
| **MINOR** | 🟢 Green | 4 | Subtle effects possible |
| **MODERATE** | 🟡 Yellow | 5 | Small HRV changes in some |
| **STRONG** | 🟠 Orange | 6 | Consistent HRV effects |
| **SEVERE** | 🟠 Orange-Red | 7 | Significant autonomic stress |
| **EXTREME** | 🔴 Red | 8-9 | Major physiological impact |

### Polar H10 Monitoring Recommendations

The system generates automatic recommendations for EKG capture timing:

#### Extreme/Severe Events
```
🔴 IMMEDIATE: Begin continuous Polar H10 monitoring NOW.
X-class flare detected—high probability of SEP/CME follow-up.
Record for next 6-12 hours for acute autonomic response capture.
```

#### Strong Events
```
🟠 ALERT: Prepare Polar H10. Strong activity detected.
Monitor for particle arrival in next 1-6 hours.
Start recording 30 min before expected arrival.
```

#### Moderate Events
```
🟡 STANDBY: Have Polar H10 ready.
Begin 5-min baseline recording now, then monitor for escalation.
```

#### Quiet Conditions
```
⚪ QUIET: Background conditions.
Ideal time for baseline Polar H10 recording (control data).
```

### Using the Impact Predictions

**Step 1: Fetch Predictions**

1. Navigate to **🌐 Space Data** tab
2. Click **"🔄 Fetch Impact Predictions"** to compute/update arrivals
3. Wait for data retrieval (~5-10 seconds)

If the fetch is slow or returns partial data, open **🧪 Step-by-step (debug hangs)** and run the specific sub-step (X-rays / protons / solar wind / CME-ENLIL / Kp-Dst). Check **📋 Space Data step log (debug)** for timings and error strings.

**Step 2: Review Arrival Times Table**

The table displays:
- **Category**: Type of energy (PHOTON, SEP, PLASMA_L1, GEOMAGNETIC)
- **Severity**: Current classification
- **Arrival (Bogotá)**: Exact local time of expected impact
- **Countdown**: Time remaining until arrival
- **Description**: Source details and measurements
- **Biological Effect**: Expected physiological implications
- **Polar H10 Action**: Recommended monitoring protocol

**Step 3: Follow Priority Recommendation**

The colored banner at the top shows the highest-priority action based on the most severe event detected.

**Step 4: Plan Recording Sessions**

Use the arrival times to schedule Polar H10 sessions:
- Start recording 30-60 minutes before predicted arrival
- Continue for 2-6 hours after arrival depending on severity
- Capture both acute impact and recovery phases

### Example Scenario

```
Current Conditions (2025-12-01 14:00 COT):

☀️ PHOTON - STRONG (M2.3 flare)
   Arrival: 2025-12-01 13:55:22 COT (already arrived)
   
⚡ SEP - MODERATE (S2, 150 pfu)
   Arrival: 2025-12-01 14:02:00 COT (ongoing)
   
🌊 PLASMA_L1 - STRONG (High-speed stream, 620 km/s)
   Arrival: 2025-12-01 14:42:33 COT (in 42 minutes)
   
🧲 GEOMAGNETIC - MODERATE (Kp=5.3, Dst=-45 nT)
   Arrival: 2025-12-01 14:00:00 COT (current)

PRIORITY RECOMMENDATION:
🟠 Solar wind disturbance arriving in 42 minutes.
Begin Polar H10 recording within next 15 minutes.
Continue for 3 hours post-arrival for storm response capture.
```

### Data Sources

| Data Type | NOAA Endpoint | Update Cadence |
|-----------|---------------|----------------|
| X-ray flux | `xrays-1-day.json` | 1 minute |
| Proton flux | `integral-protons-1-day.json` | 5 minutes |
| Solar wind plasma | `plasma-1-day.json` | 1 minute |
| Kp index | `planetary_k_index_1m.json` | 1 minute |
| Dst index | `geospace_dst_1_hour.json` | 1 hour |

**CME/Shock forecasts (model-based):**
- NASA DONKI **WSA+ENLIL** simulations (shock arrival): `WSAEnlilSimulations` (event-driven; updated when new simulations run)

### Scientific References

- NOAA Space Weather Prediction Center. (n.d.). *Space Weather Scales* (R, S, G). Retrieved 2025-12-26, from [https://www.swpc.noaa.gov/noaa-scales-explanation](https://www.swpc.noaa.gov/noaa-scales-explanation)
- Odstrčil, D. (2003). Modeling 3-D solar wind structure. *Advances in Space Research, 32*(4), 497–506. [https://doi.org/10.1016/S0273-1177(03)00332-6](https://doi.org/10.1016/S0273-1177(03)00332-6)
- Vieira CLZ, et al. (2022). Geomagnetic disturbances are associated with reduced heart rate variability. *Sci Total Environ, 839*, 156312.
- Alabdulgader A, et al. (2018). Long-term study of HRV responses to changes in the solar and geomagnetic environment. *Sci Rep, 8*(1), 2663.
- McCraty R, et al. (2017). Synchronization of human autonomic nervous system rhythms with geomagnetic activity. *Int J Environ Res Public Health, 14*(7), 770.
- Ramishvili A, Janashia K, Tvildiani L. (2023). High Heart Rate Variability Causes Better Adaptation to the Impact of Geomagnetic Storms. *Atmosphere, 14*(12), 1707. https://doi.org/10.3390/atmos14121707
- Mattoni M, Ahn S, Fröhlich C, Fröhlich F. (2019). Exploring the Relationship between Geomagnetic Activity and Human Heart Rate Variability. *bioRxiv*. https://doi.org/10.1101/684035
- Papailiou MC, Mavromichalaki H. (2025). Heart Rate Variations During Two Historic Geomagnetic Storms: October and November 2003. *Atmosphere, 16*(6), 711. https://doi.org/10.3390/atmos16060711

---

## Space Analytics (Correlations + ML)

The **🔬 Space Analytics** tab is the on-demand workspace for **correlations + machine learning** between **space-data predictors** and **HRV/HRF metrics**.

- **Space Data remains data-only**: use **🌐 Space Data** to fetch and inspect SWPC/NOAA/DONKI datasets.
- **Analytics is button-driven**: nothing auto-runs; you must click the relevant **Run** buttons for correlation scans and ML training.
- **Manual-only processing (default)**: auto-run requests are blocked; disable **Manual-only processing** in **Processing Mode** to allow load-and-run shortcuts.
- **Targets supported**: standard HRV metrics (e.g., RMSSD/SDNN/HF) and heart-rate fragmentation (HRF) metrics (e.g., PIP/W3) when present in windowed outputs.
- **GPT export integration**: when you generate the Export report + **GPT‑5.2 high‑reasoning interpretation**, any Space Analytics results from the current session are included automatically.

### Event-aligned analysis (prototype)

Space Analytics now includes a **🧭 Event-aligned analysis (prototype)** section designed for the research question:

> **During a space-weather event (start → end), do HRV, HRF, or both change? Which specific metrics are affected, and what do those changes mean?**

**What it does (current prototype):**
- Defines events deterministically using **threshold crossings** on a selected predictor time series (e.g., **Kp** or **Dst**).
- Optionally defines events using **NASA DONKI CMEAnalysis** by estimating **Sun→Earth arrival** from CME speed (drag-based transit model) and building an **Earth influence window** (arrival uncertainty + post-arrival duration).
- Extracts explicit **event start/end** windows (with user-configurable max-gap and minimum duration).
- Computes a **baseline vs event delta table** (and optional **recovery** deltas) for selected HRV/HRF metrics using windowed HRV timelines:
  - Baseline: \([event_start − baseline_hours, event_start)\)
  - Event: \([event_start, event_end]\)
  - Recovery (optional): \((event_end, event_end + recovery_hours]\)
- Ranks metrics by effect size and annotates results with short **physiology/operational meanings** for common HRV/HRF metrics.
- Computes **phase correlations** (baseline/event/recovery) between a selected **Earth-side space-weather index** (e.g., **Kp**, **Dst**) and your chosen HRV/HRF metrics.

**How to use it:**
1. Ensure you have **windowed HRV/HRF metrics** (run HRV window analysis).
   - If **HRV windows = 0**, your recording is often **shorter than the selected window** (e.g., 3 minutes of data with a 5‑minute window). Reduce **Window/Step** or upload a longer recording.
   - In **📦 Data status** (Space Analytics), you can now click **🪟 Compute windows** (button-driven) to generate windowed HRV/HRF metrics needed for correlations/ML.
2. In Space Analytics, load/fetch **NOAA Core** feeds (needs Kp and/or Dst available).
3. Open **Run event-aligned delta analysis**:
   - Choose **Kp**, **Dst**, or **DONKI CME (DBM arrival window)** as the event definition source
   - Choose the value column, threshold, and condition (≥/≤)
   - Click **Detect events**
4. Select the event you care about and set baseline duration (hours).
5. (Optional) Enable **Include recovery phase** and set recovery duration (hours).
6. Select HRV/HRF targets and click **Run baseline vs event delta table**.
7. (Optional) Use **Correlations within timeframes** to compute per-phase associations against **Kp/Dst**.

**Reference for CME transit modeling:**
- Dumbović, M., Čalogović, J., Martinić, K., et al. (2021). Drag-Based Model (DBM) Tools for Forecast of Coronal Mass Ejection Arrival Time and Speed. *Frontiers in Astronomy and Space Sciences, 8*, 58. https://doi.org/10.3389/fspas.2021.639986

**Sequencing (prototype): which changes first?**
- The tab also supports an **onset detection** heuristic: it finds the first time a metric shows a **sustained deviation** from baseline using a simple **z-score threshold** for N consecutive windows.
- Use this to explore whether HRV metrics tend to shift before HRF metrics (or vice versa) during an event window.

**Interpretation guardrails:**
- This is an **association discovery tool**, not causation.
- Always validate **data quality** (motion/artifacts/ectopy) and interpret with **sleep, activity, posture, and circadian timing** context.

### ML Suite note (minimum data)

- The Space Analytics **ML Suite** requires **≥30 usable windowed rows** after merging lagged predictors. If you have fewer windows, the app will show the usable sample count and skip training.

### NOAA dashboard (within Space Data)

**Available data feeds:**
| Feed | Description | Cadence |
|------|-------------|---------|
| Planetary Kp | Geomagnetic storm index | 3-hour |
| Dst | Ring current strength | Hourly |
| F10.7 | Solar radio flux | Daily |
| Solar wind | Speed, density, temp | Real-time |
| X-ray flux | Solar flare activity | 1-min |
| Proton flux | Radiation storm levels | 5-min |

Use **⚡ Load cached NOAA** to view the last snapshot without network calls, then **📥 Fetch NOAA feeds** / **🔄 Force refresh** to update. If NOAA is unreachable, the dashboard shows the last cached snapshot and posts a warning.
Background auto-fetch is off by default; enable **Allow background space-data auto-fetch** in **Processing Mode** if you want automatic fetches on tab open.

**HRV-timeline alignment (recommended):**
- If you have uploaded RR/HRV data, enable the **RR timeline sync** toggles for SWPC/NOAA/DONKI.
- The app will auto-seed a conservative default **DONKI padding (days)** (to capture Sun→Earth travel time) and a larger default **RR padding (hours)** (to capture impact + recovery around your recording). You can override these if you want narrower windows.

---

## Fatigue Prediction (SAFTE Model)

### Understanding SAFTE

The Sleep, Activity, Fatigue, and Task Effectiveness (SAFTE) model predicts cognitive performance based on:

1. **Homeostatic process**: Sleep pressure accumulates during wakefulness
2. **Circadian process**: 24-hour biological rhythm affects alertness
3. **Sleep inertia**: Grogginess immediately after waking

### Using the Fatigue Tab

**Step 1: Configure sleep schedule**

1. Go to **Fatigue** tab
2. Enter last night's sleep:
   - Bedtime hour (0-23)
   - Wake time hour (0-23)
   - Sleep quality (0–1, where 1.0 is best)
   - Sleep duration (hours)
   - Prior sleep debt (hours, optional)

> **Profile sync:** Click **Sync with active profile** to auto-fill age, sex, chronotype offset, sleep debt, and work cadence from the currently selected astronaut's exploration medical record. The values refresh automatically after you switch users, so you only need to tweak edge cases.
>
> **Garmin auto-fill (stored):** If Garmin daily sleep metrics have been ingested into the profile database (sleep duration and sleep efficiency/score), the Fatigue tab can auto-seed sleep duration and sleep quality **once per new Garmin day**. You can disable this behavior via the on-tab checkbox.
>
> **Profile defaults (persisted):** Use **“Save as profile defaults (SAFTE/FRMS)”** to store a typical sleep window + duty window (and weekend policy) in SQLite. Future SAFTE/FRMS runs will auto-load these values so operators don’t need to re-enter schedules.

**Step 2: Configure work schedule**

1. Enable **Include work schedule**
2. Enter work start hour and work end hour
3. (Optional) Enable **Include weekends (Sat/Sun) as duty** for shift/mission operations
4. Set cognitive load (0–3)

**Step 3: Run prediction**

1. Click **🚀 Run Fatigue Prediction**
2. View hourly effectiveness chart
3. Review risk assessment
4. Read recommendations

### FRMS & USAF Upgrades (Safety Management Dashboard)

The SAFTE tab includes an aviation-grade **FRMS-style dashboard** aligned with ICAO and USAF/DoD guidance:

- **Predictive (model-based) fatigue risk** using SAFTE effectiveness.
- **WOCL exposure** (Window of Circadian Low, typically ~02:00–06:00 local).
- **Operational effectiveness thresholds** commonly used with SAFTE/FAST:
  - **≥90%**: low risk ("well-rested" baseline)
  - **>77–<90%**: caution / transitional range
  - **>70–≤77%**: high risk (often compared to ~0.05% BAC impairment)
  - **≤70%**: severe impairment (often compared to ~0.08% BAC impairment)
- **Critical Job Window** input to evaluate risk specifically for scheduled safety-critical tasks.
- **Dual risk matrix** classification using both ICAO and USAF/DoD standards for structured decision support.

#### ICAO Risk Matrix (Doc 9859)

The ICAO risk matrix follows the Safety Management Manual (Doc 9859) definitions:

**Probability Levels (Table 2-12):**
| Level | Name | Description | Mapping (% time ≤77%) |
|-------|------|-------------|----------------------|
| 5 | Frequent | Likely to occur many times; has occurred frequently | ≥50% |
| 4 | Occasional | Likely to occur sometimes; has occurred infrequently | 30–50% |
| 3 | Remote | Unlikely but possible; has occurred rarely | 15–30% |
| 2 | Improbable | Very unlikely to occur; not known to have occurred | 5–15% |
| 1 | Extremely Improbable | Almost inconceivable the event will occur | <5% |

**Severity Levels (Table 2-11):**
| Level | Name | Description | Mapping (Min Effectiveness) |
|-------|------|-------------|----------------------------|
| E | Negligible | Few consequences | ≥85% |
| D | Minor | Operating limitations, minor incident | 77–85% |
| C | Major | Significant reduction in safety margins | 70–77% |
| B | Hazardous | Large reduction in safety margins | 60–70% |
| A | Catastrophic | Equipment destroyed, multiple deaths | <60% |

**Risk Tolerability:**
- **Acceptable** (green): Risk is acceptable; no action required
- **Tolerable** (yellow): Risk is tolerable with review; monitoring required
- **Undesirable** (orange): Risk is undesirable; mitigation required
- **Intolerable** (red): Risk is intolerable; operations must cease

#### USAF/DoD Risk Matrix (MIL-STD-882E)

The USAF risk matrix follows the DoD Standard Practice for System Safety (MIL-STD-882E):

**Probability Levels (Table II):**
| Level | Name | Description | Mapping (Risk Score) |
|-------|------|-------------|---------------------|
| A | Frequent | Likely to occur often in the life of an item | ≥5 |
| B | Probable | Will occur several times in the life of an item | 4 |
| C | Occasional | Likely to occur sometime in the life of an item | 2–3 |
| D | Remote | Unlikely, but possible to occur in the life of an item | 1 |
| E | Improbable | So unlikely, can be assumed occurrence may not be experienced | 0 |

*Risk score combines: sleep debt (0–3 pts), WOCL exposure (0–2 pts), and time ≤77% (0–2 pts).*

**Severity Categories (Table I):**
| Level | Name | Description | Mapping (Min Effectiveness) |
|-------|------|-------------|----------------------------|
| IV | Negligible | Less than minor injury, less than minor damage | ≥90% |
| III | Marginal | Minor injury, minor system damage | 77–90% |
| II | Critical | Severe injury, major system damage | 70–77% |
| I | Catastrophic | Death, system loss | <70% |

**Risk Assessment (Table III):**
- **Low** (green): Acceptable with review
- **Medium** (yellow): Acceptable with controls
- **Serious** (orange): Undesirable; senior leadership review required
- **High** (red): Unacceptable; corrective action required

It also includes a **USAF crew rest check** (AFMAN 11-202V3 baseline):

- Crew rest typically requires **≥12 hours non-duty** before FDP with **≥8 hours uninterrupted sleep opportunity**.
- If crew rest is interrupted by official business, it must restart (update the "crew rest start" time accordingly).

### Exports (Publication-Grade)

The SAFTE tab provides exports for downstream reporting and publication workflows:

- **Predictions (CSV)**: full time series of DateTime, performance, and circadian drive.
- **FRMS dashboard payload (JSON)** and **FRMS summary (CSV)** for audit trails.
- **Plot exports (PNG, SVG, HTML, spec JSON + Print/Save PDF)** via the built-in **ECharts export toolbar** shown above each plot (exports are generated locally in your browser).

### Mission FRMS v2 — Crew Risk Board (Multi-Profile)

In addition to the single-user FRMS dashboard inside the SAFTE tab, the app includes a **mission-level FRMS v2 prototype**:

- **Where to find it**: **Export → Group summaries (cohort export) → “🛡️ Mission FRMS v2 — Crew Risk Board (multi-profile)”**.
- **What it does**: Runs a bounded SAFTE forecast **per selected active user** (data priority: wrist monitoring → clinical scales → Garmin Connect (if configured) → defaults) and then computes:
  - FRMS exposure metrics (WOCL exposure, time ≤77%/≤70%, min effectiveness) for a **shared scope** (all hours or a duty-window).
  - FRMS risk matrix classification per crew member.
  - Rule-based FRMS alerts per crew member (“why it triggered”).
- **What you can export**:
  - **Crew risk board (CSV)**: roster-style table for briefings.
  - **Crew risk board payload (JSON)**: structured evidence packet for audit and integration.
  - **Decision log entry (JSON)**: an auditable record capturing **decision owner + decision + mitigations + notes** with the embedded board payload.

> **Current limitation (prototype)**: The mission board does **not** yet include per-crew individualized crew-rest times or a persistent decision-log database table; it focuses on **multi-profile aggregation + exports** first (FRMS v2 scaffolding).

> **One-click Garmin automation:** Press **Auto-run Garmin (5-day forecast)** to fetch the latest Garmin sleep/stress data (requires `GARMIN_EMAIL` and `GARMIN_PASSWORD` in your `.env`) and run a 5-day SAFTE forecast with the active user profile. The tab also shows the Garmin summary used for traceability.
>
> **Data priority:** The 5-day automation first uses wrist monitoring data saved in the Assessment tab. If none exists, it uses the subjective clinical sleep quality from the same tab. Only if both are missing will it attempt a live Garmin Connect fetch (requires `.env` credentials). The source used is shown after the run.

**Example scenario:**
```
Sleep: 11 PM - 6 AM (7 hours)
Quality: 80%
Prior debt: 2 hours
Work: 8 AM - 5 PM (9 hours)
Task: High cognitive demand

Results:
- Morning effectiveness: 92% (low risk)
- Mid-afternoon dip (2-4 PM): 84% (caution)
- End of day: 79% (caution)

High-risk exposure (≤77%): 0 hours
Recommendations:
- Take 20-min nap between 1-3 PM
- Avoid critical decisions after 4 PM
- Increase sleep tonight by 1 hour
```

### Fatigue Risk Factors

| Factor | Description | Mitigation |
|--------|-------------|------------|
| **Sleep debt** | Cumulative shortage | Extra sleep on subsequent nights |
| **Circadian nadir** | 3-5 AM, 2-4 PM dips | Strategic napping, task scheduling |
| **Sleep inertia** | Post-wake grogginess | Allow 30-60 min before demanding tasks |
| **Extended wakefulness** | >16 hours awake | Enforce rest periods |

### Key References (Fatigue / FRMS)

#### ICAO Safety Management Standards
- International Civil Aviation Organization. (2018). *Safety Management Manual* (Doc 9859, 4th ed.). ICAO Store. https://store.icao.int/en/safety-management-manual-doc-9859
- International Civil Aviation Organization. (2016). *Manual for the Oversight of Fatigue Management Approaches* (Doc 9966, 2nd ed.). https://www.icao.int/safety/fatiguemanagement/FRMS%20Tools/Doc%209966.FRMS.2016%20Edition.en.pdf
- SKYbrary. (n.d.). *ICAO Safety Management Manual Doc 9859*. https://skybrary.aero/articles/icao-safety-management-manual-doc-9859

#### USAF/DoD System Safety Standards
- Department of Defense. (2023). *MIL-STD-882E w/Change 1: Standard Practice for System Safety* (27 September 2023). U.S. Army Combat Capabilities Development Command. https://safety.army.mil/Portals/0/Documents/ON-DUTY/SYSTEMSAFETY/Standard/MIL-STD-882E-change-1.pdf
- Department of the Air Force. (n.d.). *AFMAN 11-202V3: General Flight Rules.* https://static.e-publishing.af.mil/production/1/af_a3/publication/afman11-202v3/afman11-202v3.pdf
- United States Air Forces in Europe. (2016). *Fatigue Risk Management System: What it's all about*. USAFE Public Affairs. https://www.usafe.af.mil/News/Article-Display/Article/809251/fatigue-risk-management-system-what-its-all-about
- Tvaryanas, A. P., & MacPherson, G. D. (2017). *Fatiguing the force: Using operational data to improve the United States Air Force fatigue risk management system*. International Symposium on Aviation Psychology. https://corescholar.libraries.wright.edu/cgi/viewcontent.cgi?article=1000&context=isap_2017

#### FAA and Other Aviation Standards
- Federal Aviation Administration. (2010). *Flightcrew Member Duty and Rest Requirements* (Docket No. FAA-2009-1093; Attachment 1). https://downloads.regulations.gov/FAA-2009-1093-2518/attachment_1.pdf
- Federal Aviation Administration. (2013). *Advisory Circular 120-103A: Fatigue Risk Management Systems for Aviation Safety*. https://www.faa.gov/regulations_policies/advisory_circulars/index.cfm/go/document.information/documentid/1021088

#### Fatigue Science Research
- Gander, P. H., Mangie, J., Van Den Berg, M. J., Smith, A. A., Mulrine, H. M., & Signal, T. L. (2014). Crew fatigue safety performance indicators for fatigue risk management systems. *Aviation, Space, and Environmental Medicine, 85*(2), 139–147. https://doi.org/10.3357/asem.3748.2014
- National Aeronautics and Space Administration. (2012). *NASA–easyJet Collaboration on the Human Factors Monitoring Program (HFMP) Study* (NASA NTRS No. 20120013448). https://ntrs.nasa.gov/api/citations/20120013448/downloads/20120013448.pdf
- Federal Railroad Administration. (2006). *Validation and calibration of a fatigue assessment tool for railroad work schedules* (Final report; DOT/FRA/ORD-06/21). https://rosap.ntl.bts.gov/view/dot/62575
- Hursh, S. R., Redmond, D. P., Johnson, M. L., et al. (2004). Fatigue models for applied research in warfighting. *Aviation, Space, and Environmental Medicine, 75*(3 Suppl), A44–A53.

---

## Biofeedback and Real-Time HRV

### Starting a Biofeedback Session

**Step 1: Configure session**

1. Go to **Biofeedback** tab
2. Select breathing rate (typically 6 breaths/min)
3. Choose session duration (5-20 min)
4. Enable/disable audio cues

**Step 2: Connect heart rate source**

For simulation (testing):
1. Select "Simulated" as data source
2. Adjust baseline HR and variability

For live data:
1. Connect Polar H10 or compatible BLE device
2. Select device from dropdown
3. Verify connection status

**Step 3: Begin session**

1. Click "Start Session"
2. Follow breathing guide (inhale/exhale visual)
3. Watch coherence score
4. Complete full session for best results

### Understanding Coherence

**Coherence levels:**
| Level | Score | Interpretation |
|-------|-------|----------------|
| 🔴 Low | 0-33 | Scattered HRV pattern |
| 🟡 Medium | 34-66 | Developing coherence |
| 🟢 High | 67-100 | Optimal coherent state |

**Benefits of high coherence:**
- Reduced stress response
- Improved emotional regulation
- Enhanced cognitive performance
- Better recovery from stress

### Best Practices

1. **Consistency**: Practice at same time daily
2. **Environment**: Quiet, comfortable setting
3. **Duration**: Start with 5 min, build to 20 min
4. **Frequency**: Daily practice for 4-6 weeks
5. **Progress tracking**: Save sessions for trend analysis

---

## Garmin Integration

### Exporting Garmin Wellness Data

**Method 1: Bulk Export (Recommended)**

1. Log into Garmin Connect web
2. Go to Account Settings (gear icon)
3. Click "Account Information"
4. Click "Export Your Data"
5. Request wellness data
6. Wait for email with download link
7. Download ZIP file

**Method 2: Individual FIT Files**

1. Log into Garmin Connect web
2. Go to Activities
3. Select an activity
4. Click gear icon → "Export Original"
5. Save `.fit` file

### Importing into HRV App

**For Vivosmart 5 FIT, wellness ZIP, or Garmin export JSON (fills Clinical Profile gauges):**

1. Open **User Profile → 📦 Data → Garmin Vivosmart 5 Import**.
2. Upload a `.fit` file (Export Original), the wellness `.zip` export, or an unzipped Garmin export `.json` file (e.g., `UDSFile_*.json`, `*_sleepData.json`).
3. The app parses steps, distance, calories, sleep score/efficiency, SpO₂, respiration (awake + sleep), stress, and body battery (charge/drain) when those fields are present in the export.
4. You can import multiple files sequentially; partial imports **preserve** any previously stored non-null daily values.
5. Results are saved to the user's profile and shown as double-ring ECharts gauges in the **📈 History** tab.
6. If Wrist Monitoring looks stale after a sync/import, click **🔄 Refresh wrist metrics** inside the Wrist Monitoring panel to reload from the mission database.

**Legacy ZIP import in sidebar (RR only):**

1. Go to sidebar → Garmin Import section
2. Upload `.fit`, `.csv`, or `.zip` if you only need RR intervals for HRV analysis.

### Available Garmin Data

| Data Type | What it contains | HRV use |
|-----------|-----------------|---------|
| Steps & Distance | Daily steps (monotonic or summed) and distance | Activity load context |
| Calories | Total/active calories | Energy balance context |
| Sleep | Stages, duration, sleep score, efficiency | Overnight HRV context |
| HRV | Overnight RMSSD (5-min epochs) | Baseline trends |
| Heart Rate | Avg/Resting HR | Readiness / training load |
| Stress | Garmin stress score | Correlation with HRV |
| SpO₂ | Pulse oximetry | Sleep apnea screening |
| Respiration | Awake & sleep averages (sleep flag from Garmin; guardrails: 10–17 rpm for sleep) | Breathing rate context |
| Body Battery | Daily average plus charge (+) and drain (–) estimates | Recovery tracking |

### Limitations

⚠️ **Optical sensor limitations:**
- Garmin Vivosmart 5 uses PPG (optical HR)
- Less accurate than chest strap for beat-level HRV
- Overnight HRV summaries are reasonable
- Beat-to-beat RR intervals may be limited

---

## ActiGraph GT3X Integration

### Overview

ActiGraph accelerometers (GT3X, GT3X+, GT9X Link) are research-grade wearable devices used for objective measurement of physical activity and sleep. The Mission Control - Flight Surgeon supports importing data from these devices to:

- Correlate activity patterns with HRV metrics
- Classify sleep/wake periods for overnight HRV analysis
- Assess activity intensity and sedentary behavior
- Validate self-reported activity data

### Supported File Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| GT3X Binary | `.gt3x` | Native ActiGraph format (ZIP archive with binary data) |
| ActiLife Database | `.agd` | Processed epoch data (SQLite database) |
| CSV Export | `.csv` | ActiLife exported counts or raw acceleration |

### Importing ActiGraph Data

**Step 1: Export from ActiLife**

1. Connect ActiGraph device to computer
2. Open ActiLife software
3. Download data from device
4. Export as desired format:
   - Raw: `.gt3x` file (recommended for research)
   - Processed: `.agd` file (includes epoch summaries)
   - CSV: Activity counts or raw acceleration

**Step 2: Upload to HRV App**

1. Expand "📊 ActiGraph GT3X Import" in sidebar
2. Click file uploader
3. Select your ActiGraph file
4. Wait for processing

**Step 3: Review imported data**

The app displays:
- Number of acceleration samples
- Device type and sampling rate
- Activity intensity classifications
- Sleep/wake periods (if detected)
- Quality warnings (data gaps, extreme values)

### Available Metrics

| Metric | Description | Use in HRV Analysis |
|--------|-------------|---------------------|
| Activity Counts | Epoch-based movement summary | Activity context for HRV |
| Vector Magnitude | Combined XYZ acceleration | Physical activity level |
| Sleep/Wake | Actigraphy-based classification | Overnight HRV windows |
| Intensity | Sedentary/Light/Moderate/Vigorous | Activity correlation |
| Wear Time | Valid data periods | Quality assessment |

### Activity Intensity Cut-Points

The app uses Freedson adult cut-points (counts per minute):

| Intensity | CPM Range | Description |
|-----------|-----------|-------------|
| Sedentary | 0-99 | Sitting, lying |
| Light | 100-1951 | Standing, slow walking |
| Moderate | 1952-5724 | Brisk walking |
| Vigorous | 5725+ | Running, exercise |

### Sleep/Wake Classification

Sleep periods are detected using a simplified Cole-Kripke algorithm:
- Activity threshold: 40 counts/epoch
- Minimum sleep duration: 3 consecutive epochs
- Results align with PSG in ~85% of epochs

### Limitations

⚠️ **Accelerometer limitations:**
- No direct heart rate measurement (unless HR monitor paired)
- RR intervals estimated from HR data (if available)
- Sleep staging less accurate than PSG
- Wear compliance affects data quality

---

## Somfit Pro Integration

### Overview

The Compumedics Somfit/Somfit Pro is a miniaturized home sleep testing device that attaches to the forehead and captures:

- Single-channel EEG (for sleep staging)
- EOG (eye movements)
- Heart rate (PPG-based)
- SpO2 (pulse oximetry)
- Body position

The Mission Control - Flight Surgeon imports Somfit data to analyze sleep-stage-specific HRV patterns and overnight autonomic function.

### Supported File Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| European Data Format | `.edf`, `.edf+` | Standard PSG export format |
| Profusion XML | `.xml` | Sleep scoring annotations |
| CSV Export | `.csv` | Summary data from Nexus360 |

### Importing Somfit Data

**Step 1: Export from Profusion Nexus360**

1. Complete sleep study with Somfit device
2. Upload data via Somfit app
3. Access Profusion Nexus360 cloud platform
4. Export study as EDF file
5. Optionally export scoring annotations as XML

**Step 2: Upload to HRV App**

1. Expand "😴 Somfit Pro Import" in sidebar
2. Select main data file (.edf or .csv)
3. Optionally add scoring annotations (.xml)
4. Wait for processing

**Step 3: Review imported data**

The app displays:
- Recording duration
- Number of signals
- Sleep architecture metrics (if staging available)
- Heart rate and SpO2 data quality
- Extracted RR intervals

### Sleep Architecture Metrics

When sleep staging is available, the app computes:

| Metric | Description | Normal Range |
|--------|-------------|--------------|
| TST | Total Sleep Time | 7-9 hours |
| SE | Sleep Efficiency | >85% |
| SOL | Sleep Onset Latency | <30 min |
| WASO | Wake After Sleep Onset | <30 min |
| REM Latency | Time to first REM | 70-120 min |
| N1% | Stage N1 percentage | 2-5% |
| N2% | Stage N2 percentage | 45-55% |
| N3% | Stage N3 percentage | 15-25% |
| REM% | REM percentage | 20-25% |

### Stage-Specific HRV Analysis

The app can compute HRV metrics for each sleep stage:

```
Stage   Mean RR   SDNN    RMSSD   Mean HR
Wake    850 ms    45 ms   35 ms   71 bpm
N1      920 ms    50 ms   42 ms   65 bpm
N2      950 ms    55 ms   48 ms   63 bpm
N3      980 ms    40 ms   52 ms   61 bpm
REM     900 ms    60 ms   45 ms   67 bpm
```

This reveals autonomic patterns:
- **N3 (deep sleep)**: Highest parasympathetic activity (RMSSD)
- **REM**: Variable HR with sympathetic bursts
- **Wake**: Lower HRV than sleep stages

### RR Interval Extraction

**From Heart Rate Signal:**
- RR intervals estimated as: RR = 60000 / HR (ms)
- Suitable for general HRV trends
- Not beat-to-beat accurate

**From ECG (if available):**
- R-peak detection using band-pass filtering
- True beat-to-beat intervals
- Recommended for research

### Respiratory Event Analysis

If respiratory events are scored, the app reports:

| Metric | Description | Severity |
|--------|-------------|----------|
| AHI | Apnea-Hypopnea Index | <5: Normal, 5-15: Mild, 15-30: Moderate, >30: Severe |
| ODI | Oxygen Desaturation Index | Events per hour with ≥3% desat |
| Min SpO2 | Lowest SpO2 during sleep | <90%: Significant |

### Limitations

⚠️ **Somfit limitations:**
- Single EEG channel may miss some sleep transitions
- PPG-based HR less accurate than ECG for HRV
- RR intervals are derived, not measured
- Home environment may affect signal quality

### Clinical Applications

1. **Sleep apnea screening**: AHI, ODI, SpO2 nadir
2. **Insomnia assessment**: SOL, WASO, SE
3. **Circadian analysis**: Sleep timing, architecture
4. **Autonomic function**: Stage-specific HRV patterns
5. **Treatment monitoring**: Pre/post intervention comparisons

---

## AI-Powered Interpretation

### Setting Up GPT Interpretation

**Step 1: Get OpenAI API key**

1. Go to https://platform.openai.com
2. Sign up or log in
3. Go to API Keys section
4. Create new secret key
5. Copy key (starts with `sk-`)

**Step 2: Configure environment**

Add to `.env` file:
```env
OPENAI_API_KEY=sk-your-key-here
```

**Step 3: Request interpretation**

1. Upload and process HRV data
2. Go to **Export** tab
3. Click "Request GPT-5 Interpretation"
4. Wait 30-60 seconds for response
5. Review formatted interpretation

### What GPT Analyzes

The AI reviews:
- All computed HRV metrics
- Deviation episodes
- Autonomic function test results
- Windowed metric patterns
- ML cluster assignments

### Interpretation Structure

```markdown
## Clinical Summary
Brief overview of findings...

## Time-Domain Analysis
RMSSD interpretation...
SDNN interpretation...

## Frequency-Domain Analysis
LF/HF ratio meaning...
HF power significance...

## Nonlinear Dynamics
DFA α1 interpretation...
Entropy findings...

## Recommendations
Evidence-based suggestions...

## Limitations
Important caveats...

## References
Cited literature...
```

### Logging & Audit Trail

- Every OpenAI persona (Metric Explainability Specialist, GPT-5 interpretation, SpaceWeatherLive fallback) now records both the request payload and the full markdown answer to `logs/app.log` via `app/agent_logging.py`. Audit metadata (persona, mission context hash, citation count) is also routed through `log_user_action(...)` so crews can correlate recommendations with uploaded RR files and NOAA bundles.
- Responses must call the `web_search` tool before finalizing conclusions. The developer instructions enforce APA citations plus a trailing `## Sources` section that lists DOI/PMID or official NASA/NOAA links.

### Markdown & Audio Export

- The Metrics tab exposes a **Metric Explainability Appendix** download that merges deterministic Task Force (1996) ranges with the GPT narrative. Use the "Download metric explanations (Markdown)" button for publication-ready inserts.
- Both the metrics appendix and GPT-5 interpretation panels include **Generate tts-hd audio** controls (OpenAI `tts-1-hd` via `app/agent_audio.py`). This produces a discreet MP3 clip for headset playback during mission briefs, with every synthesis event logged for compliance.

### Fallback Mode

If API is unavailable, the app provides:
- Rule-based interpretation
- Pre-defined thresholds
- Lower confidence score
- Core findings without nuance

### OpenAI Agents SDK Roadmap

- `app/agent_runtime.py` now codifies the blueprint from README.md with immutable dataclasses for:
  - **Personas** — Solar-Physiology Correlator, Wearable Recovery Concierge, Environmental Threat Watcher (each with tool lists, mission summaries, and deterministic instructions).
  - **Tool Belt** — Built-in `code_interpreter`, `file_search`, `web_search`, plus custom Wolfram Alpha, NOAA gateway, and E2B sandbox functions with explicit JSON schemas.
  - **MCP Servers** — `mcp://hrv-db`, `mcp://docs`, and `mcp://space-weather-cache`, each scoped read-only for agents.
- The About tab includes an expander that mirrors this configuration so mission directors can audit which files/APIs every persona can touch before the SDK goes live.
- Agent payloads now include mission context snapshots, ensuring every autonomous analysis cites the exact RR uploads, NOAA bundle timestamps, and profile metadata it used.
- **NEW:** The **Metric Explainability Specialist** persona feeds the Metrics tab's "Metric Explanations (Agent SDK)" panel via `app/agent_insights.py`, delivering Task Force (1996) / Shaffer & Ginsberg (2017) comparisons locally and invoking GPT-5.2 + `code_interpreter` when `OPENAI_API_KEY` is set.

---

## Export and Publication

### Generating Reports

**Step 1: Complete analysis**

1. Upload all relevant data files
2. Configure sidebar settings
3. Review all tabs for completeness

**Step 2: Go to Export tab**

**Group summaries (cohort export)**  
If you have multiple active users open (study group workflow), the Export tab now includes a **Group summaries (cohort export)** panel that generates:
- A **per-subject “latest snapshot” roster** (latest HRV measurement + latest clinical scales + latest Exploration Medical record when available)
- **Cohort-level descriptive statistics** (n, mean, SD, median, min, max) for common HRV, scale, and mission variables
- Download options for **CSV** (roster + stats) and a **Markdown cohort report**

**Longitudinal cohort comparisons (T0–T21)**  
If your HRV measurements are tagged with longitudinal timepoints (T0…T21), the Export tab also includes a **Longitudinal cohort comparisons (T0–T21)** expander that:
- Computes **within-subject Δ vs baseline** (timepoint value − subject baseline value) per metric
- Aggregates Δ by **group × timepoint** (using **persisted** study groups/assignments stored in SQLite under a **Study ID**)
- Runs **between-group comparisons** on Δ distributions per timepoint and metric (effect sizes + FDR-adjusted p-values)
- Optionally fits a **mixed-effects model** (random intercept per subject) for **Group × Time** inference on Δ vs baseline
- Provides download options for **CSV** (summary + comparisons) and a **Markdown longitudinal cohort report**

**How to use (recommended workflow):**
1. In **User Profile**, tag each saved HRV measurement to a timepoint label (T0…T21).
2. Keep **2+ users active** (User Profile tab) so they appear in the Export cohort selector.
3. In **Export → Group summaries (cohort export)**, expand **Longitudinal cohort comparisons (T0–T21)**.
4. Enter a **Study ID**, then use the **persisted roster editor** to assign each active user to a group (e.g., Control/Intervention).
5. Select the two groups to compare, choose metrics, optionally enable the **mixed-effects model**, then click **Compute longitudinal group comparisons**.

**Interpretation note:** Baseline deltas at **T0** are excluded from between-group testing (Δ = 0 by definition). The comparison focuses on how **change from baseline** differs between groups over time.

1. Select export format:
   - Markdown (for Word/docs)
   - LaTeX (for academic papers)
   - CSV (for statistical software)
   - JSON (for programmatic use)

**Step 3: Configure export scope**

Select components to include:
- [ ] Dataset overview
- [ ] Time-domain metrics
- [ ] Frequency-domain metrics
- [ ] Nonlinear metrics
- [ ] Windowed analysis
- [ ] Deviation episodes
- [ ] Autonomic tests
- [ ] Space weather correlations
- [ ] AI interpretation

**Step 4: Download**

Click "Generate Report" and save file.

### APA Format Tables

For publications, metrics are formatted per APA 7th edition:

```
Table 1
Heart Rate Variability Metrics (N = 350 beats)

Metric          M        SD       95% CI
─────────────────────────────────────────
SDNN (ms)      52.3     8.4     [48.7, 55.9]
RMSSD (ms)     41.2    12.1     [36.3, 46.1]
pNN50 (%)      18.4     6.2     [15.2, 21.6]
LF/HF ratio     1.23    0.45    [1.05, 1.41]

Note. CI = confidence interval; SDNN = standard 
deviation of NN intervals; RMSSD = root mean 
square of successive differences.
```

### LaTeX Export

For journal submissions:

```latex
\begin{table}[h]
\caption{Heart Rate Variability Metrics}
\begin{tabular}{lccc}
\toprule
Metric & M & SD & 95\% CI \\
\midrule
SDNN (ms) & 52.3 & 8.4 & [48.7, 55.9] \\
RMSSD (ms) & 41.2 & 12.1 & [36.3, 46.1] \\
\bottomrule
\end{tabular}
\end{table}
```

---

## Metric Reference Tables

### Time-Domain Metrics

| Metric | Unit | Definition | Typical range | Clinical significance |
|--------|------|------------|---------------|----------------------|
| Mean NN | ms | Average RR interval | 750-1000 | Inverse of mean HR |
| SDNN | ms | SD of all NN intervals | 40-80 | Total variability |
| RMSSD | ms | Root mean square of successive differences | 25-60 | Vagal activity |
| pNN50 | % | % successive differences >50 ms | 5-25 | Vagal activity |
| Mean HR | bpm | Average heart rate | 50-80 | Autonomic state |
| CVNN | % | Coefficient of variation | 4-8 | Normalized variability |

### Frequency-Domain Metrics

| Metric | Unit | Definition | Typical range | Clinical significance |
|--------|------|------------|---------------|----------------------|
| VLF power | ms² | Very low frequency power | 300-800 | Thermoregulation (unreliable <5min) |
| LF power | ms² | Low frequency power | 400-1500 | Baroreflex, mixed ANS |
| HF power | ms² | High frequency power | 300-1200 | Vagal, respiratory |
| LF/HF ratio | - | LF to HF ratio | 0.5-3.0 | Balance (use cautiously) |
| LF nu | % | LF in normalized units | 40-70 | Relative LF contribution |
| HF nu | % | HF in normalized units | 30-60 | Relative HF contribution |

### Nonlinear Metrics

| Metric | Unit | Definition | Typical range | Clinical significance |
|--------|------|------------|---------------|----------------------|
| SD1 | ms | Poincaré short-axis | 20-50 | ≈ RMSSD/√2, vagal |
| SD2 | ms | Poincaré long-axis | 50-120 | Longer-term variability |
| DFA α1 | - | Short-term scaling exponent | 0.75-1.25 | Fractal dynamics |
| DFA α2 | - | Long-term scaling exponent | 0.85-1.10 | Long-range correlations |
| SampEn | - | Sample entropy | 1.0-2.0 | Complexity/regularity |
| ApEn | - | Approximate entropy | 0.8-1.5 | Complexity/regularity |

### Fragmentation Metrics

| Metric | Unit | Definition | Typical range | Clinical significance |
|--------|------|------------|---------------|----------------------|
| PIP | % | Percentage of inflection points | 40-60 | Fragmentation level |
| IALS | - | Inverse average segment length | 0.3-0.5 | How often direction changes |
| PSS | % | Percentage of short segments | 30-50 | Short run frequency |
| W3 | % | 3-variation word frequency | 10-25 | Maximum fragmentation pattern |

**What is Heart Rate Fragmentation (HRF)?**  
Heart Rate Fragmentation (HRF) describes frequent beat-to-beat **direction changes** in RR interval dynamics (acceleration ↔ deceleration). It can appear even when the ECG looks like sinus rhythm and is often framed as **sinoatrial instability** or a breakdown of smooth beat-to-beat regulation (Costa et al., 2017; Hayano et al., 2020).

**Why it matters (medical / physiology framing)**  
- HRF can contribute “erratic” short-term variability that is **not purely vagal modulation**, so elevated fragmentation can **confound** interpretation of HF power / RMSSD as “more parasympathetic tone” in some cases (Costa et al., 2017; Hayano et al., 2020).  
- In older cohorts, HRF markers (e.g., PIP) have been studied for **long-term incident atrial fibrillation** prediction (Guichard et al., 2025; PROOF-AF).

**Operational interpretation (how to use it)**  
- Treat HRF as a **rhythm stability flag**, not a diagnosis: first verify data quality (motion, sensor contact, ectopy/artifacts).  
- If quality is good and HRF is persistently elevated versus baseline, interpret alongside mean HR, RMSSD/HF, sleep, symptoms, and workload context.

**How to decrease / increase HRF (practical levers)**  
- To decrease *measured* HRF: record at true rest (quiet breathing, no talking/movement), ensure good sensor contact, and prefer cleaned RR series when available.  
- Factors that can increase HRF (or the appearance of HRF) include irregular breathing, acute stress, sleep loss, alcohol, illness/inflammation, stimulants, and ectopic beats/arrhythmia. Focus on trends and context rather than single-session spikes.

**HRF ↔ HRV workspace:** Use the **🧩 HRF ↔ HRV** tab (Research app) to view HRF gauges (PIP/IALS/W3) and compute **HRF↔HRV correlation matrices and scatter plots**. This tab is offline and does not depend on Space Weather / NOAA / DONKI fetches.

---

## Troubleshooting

### Streamlit Version Requirement

> ⚠️ **CRITICAL: This app requires Streamlit 1.36.0**
>
> This is the most stable Streamlit version for Mission Control - Flight Surgeon.
> 
> | Version | Status |
> |---------|--------|
> | **1.35.0** | ❌ Tabs don't load properly |
> | **1.36.0** | ✅ **RECOMMENDED** - Most stable version |
> | **1.37.0+** | ❌ SessionInfo/setIn race condition errors |
> | **1.40.2+** | ⚠️ Works but has cosmetic error popups |
>
> **To install the correct version:**
> ```bash
> # Conda (recommended)
> conda run -n hrv-py312 pip install streamlit==1.36.0
> # or
> conda run -n hrv-py312 pip install --upgrade -r requirements.txt
>
> # Virtualenv
> # pip install streamlit==1.36.0
> # or
> # pip install --upgrade -r requirements.txt
> ```
>
> **Do not upgrade Streamlit** unless you have tested the new version thoroughly.

---

### Common Issues

**Problem: No data appears after upload**

Solutions:
1. Check file format (one value per line)
2. Verify values are in milliseconds (300-2000 range)
3. Ensure file has `.txt` extension
4. Try smaller file first

**Problem: High artifact percentage (>10%)**

Solutions:
1. Check electrode/sensor contact during recording
2. Reduce movement during recording
3. Adjust QC threshold (try 0.25 instead of 0.20)
4. Review Time Series tab for systematic issues

**Problem: Frequency analysis shows no clear peaks**

Solutions:
1. Ensure recording is ≥5 minutes
2. Check for stationarity (no major HR changes)
3. Try different PSD method
4. Verify data quality

**Problem: Space weather tab shows no data**

Solutions:
1. Check internet connection
2. Wait for cache to expire (6 hours)
3. Try manual refresh button
4. Check NOAA service status

**Problem: GPT interpretation fails**

Solutions:
1. Verify OPENAI_API_KEY in `.env`
2. Check API key validity
3. Ensure sufficient OpenAI credits
4. Try again after a few minutes

### Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| "No valid RR intervals" | All values outside 300-2000 ms | Check data format |
| "Insufficient beats for frequency analysis" | <50 beats | Use longer recording |
| "API rate limit exceeded" | Too many requests | Wait 60 seconds |
| "Connection timeout" | Network issue | Check internet |

---

## Scientific References

### Core HRV Standards

1. Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology. (1996). Heart rate variability: Standards of measurement, physiological interpretation and clinical use. *Circulation, 93*(5), 1043-1065.

2. Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability metrics and norms. *Frontiers in Public Health, 5*, 258. https://doi.org/10.3389/fpubh.2017.00258

3. Nunan, D., Sandercock, G. R., & Brodie, D. A. (2010). A quantitative systematic review of normal values for short-term heart rate variability in healthy adults. *Pacing and Clinical Electrophysiology, 33*(11), 1407-1417.

4. Quigley, K. S., Saporta, A., & Engel, M. (2024). Publication guidelines for heart rate and heart rate variability studies in Psychophysiology. *Psychophysiology, 61*(4), e14604.

### Space Weather & Health

5. Vieira, C. L. Z., Alvares, D., Blomberg, A., et al. (2022). Geomagnetic disturbances are associated with reduced heart rate variability. *Science of The Total Environment, 839*, 156312.

6. Alabdulgader, A., McCraty, R., Atkinson, M., et al. (2018). Long-term study of heart rate variability responses to changes in the solar and geomagnetic environment. *Scientific Reports, 8*(1), 2663.

7. Vencloviene, J., Radisauskas, R., Tamosiunas, A., et al. (2020). Associations between solar and geomagnetic activity and hospital admissions for myocardial infarction. *International Journal of Environmental Research and Public Health, 17*(9), 3153.

### Entropy and Nonlinear Analysis

8. Richman, J. S., & Moorman, J. R. (2000). Physiological time-series analysis using approximate entropy and sample entropy. *American Journal of Physiology-Heart and Circulatory Physiology, 278*(6), H2039-H2049.

9. Peng, C. K., Havlin, S., Stanley, H. E., & Goldberger, A. L. (1995). Quantification of scaling exponents and crossover phenomena in nonstationary heartbeat time series. *Chaos, 5*(1), 82-87.

### Fragmentation and Arrhythmia

10. Costa, M. D., Davis, R. B., & Goldberger, A. L. (2017). Heart rate fragmentation: A new approach to the analysis of cardiac interbeat interval dynamics. *Frontiers in Physiology, 8*, 255. https://doi.org/10.3389/fphys.2017.00255

11. Costa, M. D., Davis, R. B., & Goldberger, A. L. (2017). Heart rate fragmentation: A symbolic dynamical approach. *Frontiers in Physiology, 8*, 827. https://doi.org/10.3389/fphys.2017.00827

12. Hayano, J., Kisohara, M., Ueda, N., & Yuda, E. (2020). Impact of heart rate fragmentation on the assessment of heart rate variability. *Applied Sciences, 10*(9), 3314. https://doi.org/10.3390/app10093314

13. Guichard, J.-B., et al. (2025). Assessing heart rate fragmentation to predict atrial fibrillation in the general population aged 65: the PROOF-AF study. *European Heart Journal Open, 5*(3), oeaf030. https://doi.org/10.1093/ehjopen/oeaf030

### Fatigue Modeling

14. Hursh, S. R., Redmond, D. P., Johnson, M. L., et al. (2004). Fatigue models for applied research in warfighting. *Aviation, Space, and Environmental Medicine, 75*(3 Suppl), A44-A53.

15. Van Dongen, H. P., Maislin, G., Mullington, J. M., & Dinges, D. F. (2003). The cumulative cost of additional wakefulness: Dose-response effects on neurobehavioral functions and sleep physiology. *Sleep, 26*(2), 117-126.

### Basal Metabolic Rate & Nutrition

16. Mifflin, M. D., St Jeor, S. T., Hill, L. A., Scott, B. J., Daugherty, S. A., & Koh, Y. O. (1990). A new predictive equation for resting energy expenditure in healthy individuals. *American Journal of Clinical Nutrition, 51*(2), 241-247. https://doi.org/10.1093/ajcn/51.2.241

17. Harris, J. A., & Benedict, F. G. (1918). A biometric study of human basal metabolism. *Proceedings of the National Academy of Sciences, 4*(12), 370-373.

18. NASA Johnson Space Center. (2020). *Nutritional Requirements for Exploration Missions up to 365 days* (JSC67378). Houston, TX: NASA.

19. Scott, J. P. R., Green, D. A., Weerts, G., & Cheuvront, S. N. (2020). Body size and its implications upon resource utilization during human space exploration missions. *Scientific Reports, 10*, 13836. https://doi.org/10.1038/s41598-020-70054-6

### Clinical Scales (Validated Translations)

20. Chica-Urzola, H. L., Escobar-Córdoba, F., & Eslava-Schmalbach, J. (2007). Validación de la Escala de Somnolencia de Epworth. *Revista de Salud Pública, 9*(4), 558-567. https://doi.org/10.1590/S0124-00642007000400008

21. Velásquez-Paz, J. A., Torres, J. C., Valencia-Flores, M., et al. (2022). Validation of the Colombian version of the Karolinska sleepiness scale. *Sleep Science, 15*(Spec 1), 190-196. https://doi.org/10.5935/1984-0063.20220006

22. Samn, S. W., & Perelli, L. P. (1982). *Estimating aircrew fatigue: A technique with implications to airlift operations* (USAF-SAM-TR-82-21). Brooks Air Force Base, TX: USAF School of Aerospace Medicine.

### Kidney Function (eGFR)

23. Inker, L. A., Eneanya, N. D., Coresh, J., et al. (2021). New creatinine- and cystatin C-based equations to estimate GFR without race. *New England Journal of Medicine, 385*(19), 1737-1749. https://doi.org/10.1056/NEJMoa2102953

### Body Composition

24. Hodgdon, J. A., & Beckett, M. B. (1984). *Prediction of percent body fat for U.S. Navy men from body circumferences and height* (NHRC-84-11). San Diego, CA: Naval Health Research Center.

### Exploration Medical Records

25. NASA. (2023). *Medical Information Systems and Tools (MIST).* https://www.nasa.gov/general/medical-information-systems-and-tools-mist/

26. NASA Ames Research Center. (2024). *A Clinical Decision Support System for Earth-independent Medical Operations.* https://www.nasa.gov/centers-and-facilities/ames/ames-science/ames-space-biosciences/a-clinical-decision-support-system-for-earth-independent-medical-operations/

27. NASA Human Research Program. (2023). *Exploration Medical Capability - Advancing Medical System Design and Risk-Informed Decision Making for Deep Space Exploration.* NASA Technical Reports Server. https://ntrs.nasa.gov/citations/20230015831

28. NASA Glenn Research Center. (2024). *Exploration Medical Technologies.* https://www.nasa.gov/glenn/glenn-expertise-space-exploration/human-health-performance/exploration-medical-technologies/

### Space Radiation & Space-Weather Scales

29. National Aeronautics and Space Administration. (2022). *NASA Space Flight Human-System Standard, Volume 1: Crew Health* (NASA-STD-3001, Rev. B). NASA. https://www.nasa.gov/wp-content/uploads/2020/10/2022-01-05_nasa-std-3001_vol.1_rev._b_final_draft_with_signature_010522.pdf

30. Zhang, S., Berger, T., Matthiä, D., Hellweg, C. E., et al. (2020). First measurements of the radiation dose on the lunar surface. *Science Advances, 6*(39), eaaz1334. https://doi.org/10.1126/sciadv.aaz1334

31. Hassler, D. M., Zeitlin, C., Wimmer-Schweingruber, R. F., Ehresmann, B., et al. (2014). Mars' surface radiation environment measured with the Mars Science Laboratory's Curiosity rover. *Science, 343*(6169), 1244797. https://doi.org/10.1126/science.1244797

32. NOAA Space Weather Prediction Center. (n.d.). *Solar radiation storms (S-scale).* https://www.swpc.noaa.gov/phenomena/solar-radiation-storm

33. National Academies of Sciences, Engineering, and Medicine. (2021). *Space Radiation and Astronaut Health: Managing and Communicating Cancer Risks*. The National Academies Press. https://nap.nationalacademies.org/read/26155/chapter/5

34. Cucinotta, F. A. (2014). *Radiation risk acceptability and limitations*. NASA Johnson Space Center. https://three.jsc.nasa.gov/articles/astronautradlimitsfc.pdf

35. Cucinotta, F. A., Kim, M.-H. Y., & Chappell, L. J. (2013). Space radiation cancer risk projections and uncertainties – 2012. *Reports on Progress in Physics, 76*(5), 056701. https://doi.org/10.1088/0034-4885/76/5/056701

### Crew Scheduling & Workload Management

36. National Aeronautics and Space Administration. (2022). *NASA Space Flight Human-System Standard, Volume 2: Human Factors, Habitability, and Environmental Health* (NASA-STD-3001, Rev. D). NASA. https://standards.nasa.gov/standard/NASA/NASA-STD-3001_VOL_2

37. NASA Office of the Chief Health and Medical Officer. (2023). *Cognitive Workload Technical Brief* (NASA-STD-3001 Technical Brief TB-032). NASA. https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-032-cognitive-workload.pdf

38. NASA Ames Research Center. (2024). *Playbook: Next-generation planning, scheduling, and execution tools*. Human-Computer Interaction Group. https://hci.arc.nasa.gov/work/playbook.html

39. NASA. (2024). *OpenSPIFe: Open Scheduling and Planning Interface for Exploration*. GitHub Repository. https://github.com/nasa/OpenSPIFe

40. Silva-Martinez, J., Marquez, J. J., Hillenius, S., & Kanefsky, B. (2019). Lessons learned from International Space Station Crew Autonomous Scheduling Test. *NASA Technical Reports Server* (NTRS 20190027148). https://ntrs.nasa.gov/citations/20190027148

41. NASA Human Research Program. (2024). *Crew Scheduling Tools Research Task* (Task 820). Human Research Roadmap. https://humanresearchroadmap.nasa.gov/tasks/?i=820

### API Integrations

33. Polar Electro. (2024). *Polar AccessLink API Documentation.* https://www.polar.com/accesslink-api/

34. Developer Tech News. (2014). *Polar opens its API for developers to access health data.* https://www.developer-tech.com/news/polar-opens-its-api-developers-access-user-health-data/

### Time-Frequency Analysis & Spectrograms

35. de Boer, R. W., & Karemaker, J. M. (2019). Cross-wavelet time-frequency analysis reveals sympathetic contribution to baroreflex sensitivity as cause of variable phase delay between blood pressure and heart rate. *Frontiers in Neuroscience, 13*, 694. https://doi.org/10.3389/fnins.2019.00694 [PMID: 31338017]

36. Oliver, T. E., Sánchez-Hechavarría, M. E., Carrazana-Escalona, R., et al. (2023). Rapid adjustments to autonomic control of cardiac rhythm at the onset of isometric exercise in healthy young adults. *Physiological Reports, 11*(5), e15616. https://doi.org/10.14814/phy2.15616 [PMID: 36823959]

37. Pichot, V., Roche, F., Celle, S., Barthélémy, J. C., & Chouchou, F. (2016). HRVanalysis: A free software for analyzing cardiac autonomic activity. *Frontiers in Physiology, 7*, 557. [PMID: 27920726]

### Windowed & Ultra-Short-Term HRV

38. Schroeder, E. B., Whitsel, E. A., Evans, G. W., Prineas, R. J., Chambless, L. E., & Heiss, G. (2004). Repeatability of heart rate variability measures. *Annals of Noninvasive Electrocardiology, 9*(3), 257-268. [PMID: 15286929]

39. Chen, Y. S., Lu, W. A., Pagaduan, J. C., & Kuo, C. D. (2020). A novel smartphone app for the measurement of ultra-short-term and short-term heart rate variability: Validity and reliability study. *JMIR mHealth and uHealth, 8*(7), e18761. https://doi.org/10.2196/18761 [PMID: 32735219]

40. Chapman, C. L., Schafer, E. A., Potter, A. W., et al. (2025). Day-to-day reliability of basal heart rate and short-term and ultra short-term heart rate variability assessment by the Equivital eq02+ LifeMonitor in US Army soldiers. *BMJ Military Health*. https://doi.org/10.1136/military-2024-002687 [PMID: 39004444]

### HRV-Guided Training & Readiness

41. Plews, D. J., Laursen, P. B., Stanley, J., Kilding, A. E., & Buchheit, M. (2013). Training adaptation and heart rate variability in elite endurance athletes: Opening the door to effective monitoring. *Sports Medicine, 43*, 773-781. https://doi.org/10.1007/s40279-013-0071-8

42. Botek, M., McKune, A. J., Krejci, J., Stejskal, P., & Gaba, A. (2014). Change in performance in response to training load adjustment based on autonomic activity. *International Journal of Sports Medicine, 35*(6), 482-488. https://doi.org/10.1055/s-0033-1354385 [PMID: 24129989]

43. Alfonso, C., Clarke, D. C., & Capdevila, L. (2025). Individual training prescribed by heart rate variability, heart rate and well-being scores in experienced cyclists. *Scientific Reports, 15*, 13540. https://doi.org/10.1038/s41598-025-13540-z [PMID: 41028151]

44. Kiviniemi, A. M., Hautala, A. J., Kinnunen, H., & Tulppo, M. P. (2007). Endurance training guided individually by daily heart rate variability measurements. *European Journal of Applied Physiology, 101*(6), 743-751. https://doi.org/10.1007/s00421-007-0552-2

45. Thayer, J. F., Åhs, F., Fredrikson, M., Sollers, J. J., & Wager, T. D. (2012). A meta-analysis of heart rate variability and neuroimaging studies: Implications for heart rate variability as a marker of stress and health. *Neuroscience & Biobehavioral Reviews, 36*(2), 747-756. https://doi.org/10.1016/j.neubiorev.2011.11.009

### Normative Values & Reference Ranges

46. Sammito, S., & Böckelmann, I. (2016). Reference values for time- and frequency-domain heart rate variability measures. *Heart Rhythm, 13*(6), 1309-1316. [PMID: 26883166]

47. Ziegler, D., et al. (1999). Normal ranges and reproducibility of statistical, geometric, frequency domain, and non-linear measures of 24-hour heart rate variability. *Annals of Noninvasive Electrocardiology, 4*(4), 415-424. [PMID: 10668921]

48. Ortega, E., Bryan, C. Y. X., & Christine, N. S. C. (2024). The pulse of Singapore: Short-term HRV norms. *Applied Psychophysiology and Biofeedback, 49*, 95-102. [PMID: 37755550]

49. Billman, G. E. (2013). The LF/HF ratio does not accurately measure cardiac sympatho-vagal balance. *Frontiers in Physiology, 4*, 26. https://doi.org/10.3389/fphys.2013.00026

50. Koenig, J., & Thayer, J. F. (2016). Sex differences in healthy human heart rate variability: A meta-analysis. *Neuroscience & Biobehavioral Reviews, 64*, 288-310. https://doi.org/10.1016/j.neubiorev.2016.03.007

### Circadian HRV Patterns

51. Buitrago-Ricaurte, N., Riveros-Rivera, A., & Riveros, A. J. (2025). Age and sex affect circadian patterns of cardiac autonomic function. *Scientific Reports, 15*, 18525. https://doi.org/10.1038/s41598-025-18525-6 [PMID: 41022949]

52. Rasouli, M., Feli, M., Azimi, I., et al. (2025). Circadian rhythm of heart rate and heart rate variability in pregnancy. *NPJ Women's Health, 3*, 107. https://doi.org/10.1038/s44294-025-00107-6 [PMID: 41070097]

53. Weinschenk, S., Topbas-Selcuki, N. F., Benrath, J., et al. (2025). Effects of therapy with local anesthetics on heart rate variability over 24 hours. *Chronobiology International, 42*(1). https://doi.org/10.1080/07420528.2025.2560963 [PMID: 41020483]

54. Lee, J. D., Huang, Y. C., Lee, M., et al. (2025). Circadian patterns of heart rate and heart rate variability in wake-up stroke: Evidence of parasympathetic dysregulation. *Current Neurovascular Research, 22*(1). https://doi.org/10.2174/0115672026418606251007070743 [PMID: 41126417]

55. To, N. M., Vo, V. Q., Ngo, Q. C., et al. (2025). Day and night patterns of heart rate variability in type 2 diabetes: Gender and microvascular complications considerations in normal and micro-albuminuria. *IEEE EMBC, 2025*, 11253277. https://doi.org/10.1109/EMBC58623.2025.11253277 [PMID: 41335990]

---

## Appendix: Sample Workflows

### Morning Readiness Check (5 minutes)

```
1. Wake up, stay supine
2. Start HRV recording (1-5 min)
3. Upload to app
4. Check Readiness tab
   - Compare to baseline
   - Note category (NORMAL/LOW/HIGH)
5. Adjust training intensity accordingly
```

### Pre-Competition Assessment (15 minutes)

```
1. Record 5-min supine HRV
2. Upload and review:
   - RMSSD trend vs baseline
   - LF/HF ratio
   - Readiness score
3. Check space weather:
   - Note Kp index
   - Consider if sensitive to geomagnetic activity
4. Make tactical adjustments if needed
```

### Clinical Autonomic Battery (30 minutes)

```
1. 5-min supine baseline recording
2. Valsalva maneuver (15s strain)
3. Deep breathing test (6 cycles)
4. 30:15 standing test
5. Upload recording with timestamps
6. Process all tests in ANS tab
7. Export clinical report
8. Document in patient record
```

### Research Data Collection (variable)

```
1. Standardize protocol:
   - Same time of day
   - Same posture
   - Controlled breathing (spontaneous or paced)
2. Record ≥5 min per session
3. Name files: SubjectID_Date_Condition.txt
4. Batch upload all files
5. Use windowed analysis for long recordings
6. Enable space weather correlation if relevant
7. Export CSV for external statistical analysis
8. Generate LaTeX tables for publication
```

---

## Advanced ECG R-Peak Detection

### Overview

The ECG R-Peak Detection module provides robust algorithms for identifying R-peaks (the highest amplitude deflection in the QRS complex) from raw electrocardiogram signals. Accurate R-peak detection is the foundation of true beat-to-beat HRV analysis, as RR intervals derived from heart rate approximations lack the precision needed for detailed autonomic assessment.

### Scientific Background

The QRS complex represents ventricular depolarization and is the most prominent feature of the ECG waveform. The R-peak, typically the largest deflection, serves as the fiducial point for measuring RR intervals. The precision of R-peak localization directly impacts the accuracy of all subsequent HRV metrics, particularly high-frequency components and nonlinear measures (Zhai et al., 2023).

**Why R-Peak Detection Matters:**

- **True beat-to-beat timing**: Heart rate monitors report averaged HR, losing beat-to-beat variability information
- **Artifact identification**: Raw ECG allows detection of ectopic beats, noise, and motion artifacts
- **High-frequency HRV**: Accurate timing is critical for respiratory sinus arrhythmia quantification
- **Research applications**: Publications require beat-to-beat RR intervals from validated detection algorithms

### Pan-Tompkins Algorithm

The Pan-Tompkins algorithm (Pan & Tompkins, 1985) is the gold-standard method for QRS detection, implemented in our module with enhancements for improved accuracy.

**Algorithm Pipeline:**

1. **Bandpass filtering (5-15 Hz)**: Removes baseline wander and high-frequency noise while preserving QRS energy
2. **Derivative filter**: Emphasizes the steep slopes of the QRS complex
3. **Squaring**: Amplifies differences and makes all values positive
4. **Moving window integration**: Smooths the signal to create QRS envelope
5. **Adaptive thresholding**: Dynamically adjusts detection threshold based on signal and noise levels
6. **Search-back**: Recovers missed beats during low-amplitude periods

**Performance Characteristics:**

| Metric | Value | Database |
|--------|-------|----------|
| Sensitivity | 99.78% | MIT-BIH Arrhythmia |
| Positive Predictive Value | 99.78% | MIT-BIH Arrhythmia |
| Detection Error Rate | 0.44% | MIT-BIH Arrhythmia |
| Localization Error | 8.35 ms | MIT-BIH Arrhythmia |

*Based on Zhai et al. (2023) validation study*

### Template Matching

Template matching provides an additional layer of accuracy by comparing detected beats against a learned QRS template, enabling:

- **Ectopic beat identification**: Premature ventricular contractions (PVCs) and premature atrial contractions (PACs) have different morphologies
- **Noise rejection**: Non-cardiac artifacts that pass initial detection are filtered
- **Beat classification**: Normal sinus beats vs. aberrant conduction

**How Template Matching Works:**

1. **Template generation**: Average of initial 10-20 high-quality beats
2. **Cross-correlation**: Each candidate beat is correlated with the template
3. **Similarity threshold**: Beats with correlation < 0.8 are flagged for review
4. **Adaptive updating**: Template evolves with signal changes

### Using ECG R-Peak Detection

**Step 1: Prepare ECG Data**

Supported formats:
- EDF/EDF+ (European Data Format)
- CSV with time and voltage columns
- Raw binary with header specification

**Step 2: Configure Detection Parameters**

| Parameter | Default | Description |
|-----------|---------|-------------|
| Sampling rate | Auto-detect | ECG sampling frequency (Hz) |
| Filter order | 2 | Butterworth filter order |
| Integration window | 150 ms | Moving average window |
| Refractory period | 200 ms | Minimum RR interval |
| Template correlation | 0.8 | Minimum similarity threshold |

**Step 3: Run Detection**

1. Upload ECG file in sidebar
2. Select "ECG R-Peak Detection" analysis mode
3. Review detected peaks overlaid on ECG trace
4. Manually correct any missed or false detections
5. Export RR intervals for HRV analysis

### Quality Assessment

The module provides automatic quality metrics:

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| Signal-to-Noise Ratio | >20 dB | 10-20 dB | <10 dB |
| Baseline Wander | <0.5 mV | 0.5-1.0 mV | >1.0 mV |
| Detection Confidence | >95% | 85-95% | <85% |
| Ectopic Beat Rate | <5% | 5-10% | >10% |

### Clinical Applications

1. **Research HRV studies**: Publications require validated R-peak detection
2. **Holter analysis**: Process 24-hour ECG recordings
3. **Wearable ECG**: Analyze data from Polar H10, Apple Watch ECG, KardiaMobile
4. **Sleep studies**: Extract RR intervals from overnight PSG recordings
5. **Exercise testing**: High-precision timing during stress tests

### References

- Pan, J., & Tompkins, W. J. (1985). A real-time QRS detection algorithm. *IEEE Transactions on Biomedical Engineering, 32*(3), 230-236.
- Zhai, D., Bao, X., Long, X., et al. (2023). Precise detection and localization of R-peaks from ECG signals. *Mathematical Biosciences and Engineering, 20*(10), 19191-19210.
- Farzaneh, N., Ghanbari, H., Liu, M., et al. (2023). A comprehensive comparison of six publicly available algorithms for localization of QRS complex. *IEEE EMBC*, 1-4.

---

## Multi-Modal Sensor Fusion

### Overview

The Multi-Modal Sensor Fusion module integrates physiological data from multiple wearable devices and platforms, enabling comprehensive health assessment that leverages the strengths of different sensors while compensating for individual device limitations.

### Scientific Background

Modern wearable devices use different sensing technologies with varying accuracy profiles. Photoplethysmography (PPG)-based wrist devices excel at continuous monitoring but may struggle during movement, while chest straps provide excellent beat-to-beat accuracy but are less convenient for 24/7 wear. Sensor fusion combines these complementary data sources to provide more robust and complete physiological insights (Dial et al., 2025; Schaffarczyk et al., 2022).

**Validation Studies Summary:**

| Device | RHR Accuracy (CCC) | HRV Accuracy (MAPE) | Best Use Case |
|--------|-------------------|---------------------|---------------|
| Oura Gen 4 | 0.98 | 5.96% | Nocturnal HRV |
| Oura Gen 3 | 0.97 | 7.15% | Sleep tracking |
| WHOOP 4.0 | 0.91 | 8.17% | Recovery monitoring |
| Polar H10 | >0.99 | <5% | Research/clinical |
| Garmin Fenix | 0.87* | 10.52% | Activity tracking |

*Dial et al., 2025; Schaffarczyk et al., 2022*

### Supported Platforms

#### Oura Ring Integration

**Data Available:**
- Nocturnal HRV (RMSSD, 5-minute epochs)
- Resting heart rate
- Sleep stages and duration
- Body temperature deviation
- Respiratory rate
- Activity and step counts
- Readiness score

**Import Method:**
1. Export data from Oura web dashboard (JSON format)
2. Upload to HRV Suite via sidebar
3. Automatic parsing and alignment with other data sources

#### WHOOP Integration

**Data Available:**
- HRV (RMSSD during slow-wave sleep)
- Resting heart rate
- Respiratory rate
- Sleep performance metrics
- Strain score (daily load)
- Recovery percentage

**Import Method:**
1. Request data export from WHOOP app
2. Upload CSV files to HRV Suite
3. Strain and recovery metrics correlated with HRV trends

#### Apple Health Integration

**Data Available:**
- Heart rate samples (continuous)
- HRV measurements (SDNN)
- Resting heart rate
- Walking heart rate
- Heart rate recovery
- Sleep analysis
- Activity and workouts

**Import Method:**
1. Export Health data from iPhone (Settings → Health → Export)
2. Upload the export.zip file
3. Automatic extraction of relevant health records

#### Fitbit Integration

**Data Available:**
- Heart rate (continuous PPG)
- HRV (SpO2 app, limited)
- Sleep stages
- Active zone minutes
- Resting heart rate trends

**Import Method:**
1. Request data download from Fitbit account
2. Upload JSON export files
3. Parse and integrate with existing datasets

### Fusion Algorithms

**Weighted Averaging:**

When multiple devices provide overlapping measurements, the fusion algorithm applies quality-weighted averaging:

```
HRV_fused = Σ(w_i × HRV_i) / Σ(w_i)

where w_i = quality_score × device_accuracy × temporal_proximity
```

**Conflict Resolution:**

When devices disagree significantly:
1. Flag the discrepancy for user review
2. Apply device-specific accuracy priors
3. Consider context (activity level, time of day)
4. Default to highest-accuracy device for that metric

**Gap Filling:**

Missing data from one device can be estimated using:
- Correlated data from other devices
- Historical patterns for that individual
- Circadian rhythm models

### Cross-Device Validation

The module automatically validates data quality by:

1. **Temporal alignment**: Synchronizing timestamps across devices
2. **Correlation analysis**: Checking agreement between overlapping measurements
3. **Outlier detection**: Flagging values inconsistent across devices
4. **Quality scoring**: Assigning confidence levels to fused metrics

### Practical Workflow

**Step 1: Configure Data Sources**

1. Expand "Multi-Modal Fusion" in sidebar
2. Select active data sources
3. Set primary device for each metric type
4. Configure fusion preferences

**Step 2: Upload Data**

1. Upload exports from each platform
2. Review automatic timestamp alignment
3. Resolve any detected conflicts
4. Verify data coverage timeline

**Step 3: Review Fused Results**

1. View unified dashboard with all metrics
2. Compare device-specific vs. fused values
3. Identify periods of poor agreement
4. Export comprehensive dataset

### Limitations and Considerations

⚠️ **Important Caveats:**

- **PPG limitations**: Wrist-based devices less accurate during movement
- **Algorithm differences**: Each device uses proprietary HRV calculations
- **Sampling differences**: Continuous vs. spot-check measurements
- **Timestamp accuracy**: Device clock synchronization may vary

### References

- Dial, M. B., Hollander, M. E., Vatne, E., et al. (2025). Validation of nocturnal resting heart rate and heart rate variability in consumer wearables. *Physiological Reports, 13*(8), e70527.
- Schaffarczyk, M., Rogers, B., Reer, R., & Gronwald, T. (2022). Validity of the Polar H10 sensor for heart rate variability analysis. *Sensors, 22*(17), 6536.
- Sinichi, M., Gevonden, M. J., & Krabbendam, L. (2025). Quality in question: Assessing the accuracy of four heart rate wearables. *Psychophysiology, 62*(1), e70004.

---

## Long-Term HRV Trending Analysis

### Overview

The Long-Term Trending module provides tools for tracking HRV changes over extended periods (weeks to months), enabling detection of gradual physiological changes, training adaptations, and early warning signs of health issues that may not be apparent in single-session analyses.

### Scientific Background

Single HRV measurements provide a snapshot of autonomic function at one moment, but significant biological information is contained in how HRV changes over time. Day-to-day variability in HRV is normal and can be substantial (CV of 10-30% for RMSSD), making trend detection challenging without appropriate statistical methods.

**Key Concepts:**

- **Baseline establishment**: Individual reference values account for personal variation
- **Meaningful change detection**: Distinguishing true physiological changes from normal fluctuation
- **Circadian and ultradian rhythms**: HRV varies predictably throughout the day
- **Seasonal patterns**: Some individuals show seasonal HRV variation

### Baseline Calculation Methods

#### Rolling Average Baseline

The default method uses a rolling window (typically 7-14 days) to establish current baseline:

```
Baseline_t = mean(HRV_{t-n} ... HRV_{t-1})

where n = window size (days)
```

**Advantages:**
- Adapts to gradual changes
- Robust to single outliers
- Intuitive interpretation

**Limitations:**
- Slow to detect rapid changes
- May miss acute deviations

#### Exponentially Weighted Moving Average (EWMA)

EWMA provides faster response to recent changes:

```
Baseline_t = α × HRV_t + (1-α) × Baseline_{t-1}

where α = smoothing factor (0.1-0.3 typical)
```

#### Coefficient of Variation (CV) Baseline

For individuals with high day-to-day variability, CV-based methods normalize for individual variation:

```
Z_score = (HRV_t - Baseline_t) / SD_baseline
```

### Trend Detection Algorithms

#### Linear Regression Trend

Fits a linear model to detect gradual changes:

```
HRV = β₀ + β₁ × time + ε
```

- **Positive β₁**: Improving trend (increasing HRV)
- **Negative β₁**: Declining trend (decreasing HRV)
- **p-value**: Statistical significance of trend

#### Change Point Detection

Identifies sudden shifts in HRV baseline using:

- **CUSUM (Cumulative Sum)**: Detects sustained shifts from baseline
- **Bayesian Change Point**: Probabilistic detection of regime changes
- **PELT Algorithm**: Optimal partitioning for multiple change points

#### Seasonal Decomposition

Separates HRV time series into components:

```
HRV_t = Trend_t + Seasonal_t + Residual_t
```

Useful for identifying:
- Long-term trends independent of seasonal effects
- Weekly patterns (e.g., weekend recovery)
- Annual cycles

### Clinical Applications

#### Training Load Monitoring

For athletes and fitness enthusiasts:

| Trend Pattern | Interpretation | Recommendation |
|--------------|----------------|----------------|
| Stable baseline, normal variability | Appropriate training load | Continue current program |
| Declining trend (>2 weeks) | Accumulated fatigue | Increase recovery, reduce volume |
| Increasing trend | Positive adaptation | May increase training stimulus |
| Increased variability | Inconsistent recovery | Improve sleep/nutrition consistency |
| Sudden drop (>2 SD) | Acute stressor | Investigate cause, rest if needed |

#### Health Monitoring

| Pattern | Possible Causes | Action |
|---------|-----------------|--------|
| Gradual decline over months | Deconditioning, aging, chronic stress | Medical evaluation, lifestyle assessment |
| Sudden sustained drop | Illness onset, medication change | Medical consultation |
| Increased morning HRV | Improved fitness, reduced stress | Positive indicator |
| Loss of circadian pattern | Sleep disorder, shift work | Sleep assessment |

### Using the Trending Module

**Step 1: Accumulate Data**

- Minimum 14 days recommended for baseline
- 30+ days ideal for trend detection
- Consistent measurement timing improves accuracy

**Step 2: Configure Analysis**

| Setting | Options | Recommendation |
|---------|---------|----------------|
| Baseline window | 7, 14, 30 days | 14 days for most users |
| Trend window | 7, 14, 30 days | Match to monitoring goals |
| Alert threshold | 1.5, 2.0, 2.5 SD | 2.0 SD for general use |
| Metrics tracked | RMSSD, SDNN, HF, LF/HF | RMSSD primary, others secondary |

**Step 3: Interpret Results**

The dashboard displays:
- Current value vs. baseline
- Z-score (standard deviations from baseline)
- Trend direction and significance
- Alert status (normal/caution/alert)

### Visualization Options

1. **Time series plot**: Daily values with baseline and confidence bands
2. **Z-score chart**: Standardized deviations over time
3. **Trend decomposition**: Separated trend, seasonal, residual components
4. **Calendar heatmap**: Color-coded daily values for pattern recognition
5. **Correlation matrix**: Relationships between HRV and lifestyle factors

### Correlation with External Factors

The module can correlate HRV trends with:

- **Sleep metrics**: Duration, quality, timing
- **Activity data**: Steps, exercise sessions, strain
- **Subjective ratings**: Stress, mood, energy
- **Environmental factors**: Temperature, altitude
- **Menstrual cycle**: For female users (optional tracking)

### Limitations

⚠️ **Important Considerations:**

- **Measurement consistency**: Time of day, posture, and conditions affect HRV
- **Individual variation**: "Normal" ranges vary widely between individuals
- **Confounding factors**: Many variables influence HRV simultaneously
- **Statistical power**: Short time series limit trend detection sensitivity

### References

- Liu, J., & Zhang, F. (2024). Autonomic nervous system and sarcopenia in elderly patients: Insights from long-term heart rate variability monitoring. *International Journal of General Medicine, 17*, 3823-3833.
- Mooren, F., et al. (2023). Autonomic dysregulation in long-term patients suffering from Post-COVID-19 Syndrome. *Scientific Reports, 13*, 15814.
- Mehrabanian, M., et al. (2024). The predictive value of heart rate variability for long-term outcomes in patients undergoing CABG. *Journal of Tehran Heart Center, 19*(4), 255-263.

---

## Exercise HRV Analysis

### Overview

The Exercise HRV Analysis module provides specialized tools for analyzing heart rate variability patterns during and after physical exercise, including heart rate recovery (HRR), parasympathetic reactivation, and training load quantification. These metrics are essential for athletes, coaches, and exercise physiologists optimizing performance and preventing overtraining.

### Scientific Background

Exercise induces a characteristic autonomic response: sympathetic activation during exertion followed by parasympathetic reactivation during recovery. The speed and magnitude of this recovery provides valuable information about fitness, fatigue, and cardiovascular health.

**Key Physiological Concepts:**

- **Vagal withdrawal**: During exercise, parasympathetic activity decreases, allowing HR to rise
- **Sympathetic activation**: Catecholamine release increases HR and contractility
- **Parasympathetic reactivation**: Post-exercise vagal activity returns, slowing HR
- **Heart rate recovery (HRR)**: Rate of HR decline after exercise cessation

### Heart Rate Recovery (HRR) Analysis

HRR is the decrease in heart rate from peak exercise to a specified time point post-exercise.

**Standard HRR Metrics:**

| Metric | Definition | Normal Values | Clinical Significance |
|--------|------------|---------------|----------------------|
| HRR1 | HR_peak - HR_1min | >12 bpm | Abnormal if <12 bpm |
| HRR2 | HR_peak - HR_2min | >22 bpm | Mortality predictor |
| HRR3 | HR_peak - HR_3min | >32 bpm | Recovery capacity |
| T30 | Time to 30 bpm drop | <60 sec | Fitness indicator |

**Prognostic Value:**

Abnormal HRR (HRR1 <12 bpm) is associated with:
- 2-4× increased mortality risk
- Increased cardiovascular event risk
- Autonomic dysfunction
- Reduced fitness level

### Parasympathetic Reactivation

Post-exercise parasympathetic reactivation can be quantified using time-varying HRV analysis:

**Short-term HRV Recovery:**

| Time Window | Primary Metric | Interpretation |
|-------------|----------------|----------------|
| 0-30 sec | HR decay rate | Immediate vagal reactivation |
| 30-60 sec | RMSSD30s | Early parasympathetic return |
| 1-5 min | RMSSD, HF power | Sustained recovery |
| 5-30 min | Return to baseline | Complete recovery |

**Parasympathetic Reactivation Index (PRI):**

```
PRI = (RMSSD_recovery - RMSSD_exercise) / RMSSD_baseline × 100
```

Higher PRI indicates faster autonomic recovery.

### Training Load Quantification

#### TRIMP (Training Impulse)

Banister's TRIMP quantifies training load using HR and duration:

```
TRIMP = Duration × ΔHR_ratio × e^(b × ΔHR_ratio)

where:
ΔHR_ratio = (HR_exercise - HR_rest) / (HR_max - HR_rest)
b = 1.92 (males) or 1.67 (females)
```

#### Session RPE

Combines duration with perceived exertion:

```
sRPE = Duration (min) × RPE (0-10 scale)
```

#### HRV-Guided Training

Using morning HRV to guide training decisions:

| HRV Status | Recommendation |
|------------|----------------|
| Above baseline (+1 SD) | Green light for high intensity |
| Within baseline (±1 SD) | Normal training |
| Below baseline (-1 SD) | Consider reduced intensity |
| Significantly below (-2 SD) | Recovery day recommended |

### Exercise Protocol Analysis

**Pre-Exercise Assessment:**
- 5-minute resting HRV measurement
- Baseline establishment
- Readiness score calculation

**During Exercise:**
- Real-time HR monitoring
- DFA α1 for intensity threshold detection
- Accumulated load calculation

**Post-Exercise Recovery:**
- Immediate HRR (0-3 min)
- Short-term recovery (3-30 min)
- Next-day HRV comparison

### DFA α1 for Exercise Intensity

Detrended Fluctuation Analysis alpha 1 (DFA α1) provides objective intensity zone boundaries:

| DFA α1 Value | Intensity Zone | Physiological State |
|--------------|----------------|---------------------|
| >1.0 | Zone 1 (Recovery) | Aerobic, low intensity |
| 0.75-1.0 | Zone 2 (Aerobic) | Moderate, sustainable |
| 0.5-0.75 | Zone 3 (Threshold) | Ventilatory threshold |
| <0.5 | Zone 4-5 (Anaerobic) | High intensity, unsustainable |

### Practical Workflow

**Step 1: Record Exercise Session**

1. Start HRV recording before exercise (5-min baseline)
2. Continue recording throughout exercise
3. Record recovery for at least 5 minutes post-exercise
4. Note exercise type, intensity, and duration

**Step 2: Upload and Analyze**

1. Upload RR interval file
2. Mark exercise start and end times
3. Select analysis type (HRR, recovery HRV, TRIMP)
4. Review automated metrics

**Step 3: Interpret Results**

1. Compare HRR to personal baseline and norms
2. Assess parasympathetic reactivation rate
3. Review training load vs. recovery capacity
4. Make training decisions based on trends

### Overtraining Detection

Chronic overtraining (overreaching) manifests in HRV patterns:

| Indicator | Pattern | Action |
|-----------|---------|--------|
| Declining resting HRV | 7+ day trend | Reduce training volume |
| Elevated resting HR | >5 bpm above baseline | Increase recovery |
| Reduced HRR | <baseline HRR | Deload week |
| Increased HRV variability | Erratic day-to-day | Improve sleep/nutrition |
| Parasympathetic saturation | Very high resting HRV | May indicate deep fatigue |

### References

- Gronwald, T., et al. (2025). Recovery of linear and nonlinear heart rate variability metrics after exercise. *European Journal of Sport Science, 25*(3), e70077.
- Sabino-Carvalho, J. L., et al. (2025). Aerobic cycling exercise training and vagal reactivation in CKD patients. *Medicine & Science in Sports & Exercise*.
- Porzio, E., et al. (2025). Heart rate variability and parasympathetic reactivation in endurance horses. *Veterinary Sciences, 12*(11), 1028.

---

## Machine Learning Predictions

### Overview

The Machine Learning Predictions module leverages advanced algorithms to predict clinical outcomes and detect patterns from HRV data. These models provide risk stratification for conditions including atrial fibrillation (AF), sudden cardiac death (SCD), and sleep apnea, offering clinicians and researchers powerful tools for early detection and prevention.

### Scientific Background

HRV contains rich information about autonomic function and cardiovascular health that can be extracted using machine learning techniques. Recent advances have demonstrated that ML models can identify subtle patterns in HRV data that predict clinical events with accuracy comparable to or exceeding traditional risk scores.

**Evidence Base:**

| Application | Accuracy | Key Features | Reference |
|-------------|----------|--------------|-----------|
| AF prediction | AUC 0.85-0.92 | RMSSD, entropy, fragmentation | Grégoire et al., 2025 |
| SCD risk | AUC 0.75-0.85 | SDNN, DFA α1, VLF | Sessa et al., 2018 |
| Sleep apnea | AUC 0.80-0.90 | Time/frequency domain | Hao et al., 2025 |

### Atrial Fibrillation Risk Prediction

#### Overview

Atrial fibrillation is the most common sustained cardiac arrhythmia, affecting 2-3% of adults. Early detection enables stroke prevention through anticoagulation. HRV-based ML models can identify individuals at elevated AF risk before clinical presentation.

#### Model Features

The AF prediction model uses:

**Time-Domain Features:**
- RMSSD (reduced in AF-prone individuals)
- pNN50 (parasympathetic marker)
- SDNN (total variability)
- Heart rate fragmentation indices

**Frequency-Domain Features:**
- LF/HF ratio (autonomic balance)
- HF power (vagal activity)
- Spectral entropy

**Nonlinear Features:**
- DFA α1 (fractal dynamics)
- Sample entropy (complexity)
- Poincaré SD1/SD2 ratio

#### Risk Stratification

| Risk Level | Probability | Recommendation |
|------------|-------------|----------------|
| Low | <10% | Routine monitoring |
| Moderate | 10-30% | Enhanced surveillance, lifestyle modification |
| High | >30% | Cardiology referral, consider extended monitoring |

#### Interpretation

The model outputs:
- **Risk probability**: 0-100% likelihood of AF development
- **Contributing factors**: Which HRV features drove the prediction
- **Confidence interval**: Uncertainty in the estimate
- **Comparison to population**: Percentile ranking

### Sudden Cardiac Death Risk Stratification

#### Overview

Sudden cardiac death (SCD) accounts for 15-20% of all deaths. Identifying high-risk individuals enables preventive interventions including implantable defibrillators. HRV provides prognostic information about SCD risk, particularly in post-myocardial infarction patients.

#### Risk Factors from HRV

| HRV Metric | High Risk Threshold | Relative Risk |
|------------|---------------------|---------------|
| SDNN <70 ms | 24-hour recording | 2-4× |
| SDNN <50 ms | 24-hour recording | 5-10× |
| DFA α1 <0.65 | Short-term | 2-3× |
| VLF power reduced | 24-hour | 2-3× |
| Low HRV + Low LVEF | Combined | 10×+ |

#### Model Architecture

The SCD risk model combines:
1. **HRV features**: Time, frequency, nonlinear domains
2. **Clinical variables**: Age, LVEF, prior MI, medications
3. **ECG features**: QT interval, T-wave alternans (if available)

#### Output Interpretation

- **Risk score**: 0-100 scale
- **Risk category**: Low/Moderate/High/Very High
- **Key contributors**: Which factors elevate risk
- **Actionable recommendations**: Based on modifiable factors

### Sleep Apnea Screening

#### Overview

Obstructive sleep apnea (OSA) affects 10-30% of adults and is associated with cardiovascular disease, hypertension, and cognitive impairment. HRV-based screening can identify individuals who should undergo formal polysomnography.

#### Physiological Basis

OSA causes characteristic HRV patterns:
- **Cyclic variation**: Alternating sympathetic/parasympathetic activity
- **Reduced HRV**: Overall autonomic dysfunction
- **Increased LF/HF**: Sympathetic predominance
- **Desaturation-related changes**: Hypoxia affects autonomic tone

#### Screening Model

**Input Features:**
- Nocturnal HRV metrics (SDNN, RMSSD, LF, HF)
- Heart rate patterns during sleep
- Respiratory-related HRV changes
- Demographic factors (age, BMI, sex)

**Output:**
- **OSA probability**: Likelihood of AHI ≥5
- **Severity estimate**: Mild/Moderate/Severe
- **Recommendation**: PSG referral if indicated

#### Validation

Recent meta-analysis (Hao et al., 2025) of ML-based OSA detection:
- Pooled sensitivity: 85%
- Pooled specificity: 82%
- Suitable for screening, not diagnosis

### Model Transparency and Limitations

#### Explainable AI

All predictions include:
- **Feature importance**: Which HRV metrics contributed most
- **SHAP values**: Direction and magnitude of each feature's effect
- **Uncertainty quantification**: Confidence in predictions
- **Comparison cases**: Similar profiles from training data

#### Limitations

⚠️ **Important Caveats:**

1. **Screening, not diagnosis**: ML predictions support clinical decision-making but don't replace diagnostic testing
2. **Population-specific**: Models trained on specific populations may not generalize
3. **Data quality dependent**: Predictions only as good as input data
4. **Temporal validity**: Models may need retraining as populations change
5. **Regulatory status**: Research tools, not FDA-cleared diagnostics

### Using ML Predictions

**Step 1: Ensure Data Quality**

- Minimum 5-minute recording (24-hour preferred for SCD)
- <5% artifact rate
- Appropriate measurement conditions

**Step 2: Select Prediction Model**

1. Go to "ML Predictions" tab
2. Select target condition (AF, SCD, Sleep Apnea)
3. Review required data and input clinical variables
4. Run prediction

**Step 3: Interpret Results**

1. Review risk probability and category
2. Examine contributing factors
3. Consider clinical context
4. Discuss with healthcare provider if elevated risk

### References

- Grégoire, J. M., et al. (2025). Short-term atrial fibrillation onset prediction using machine learning. *European Heart Journal - Digital Health*.
- Hao, Y., et al. (2025). ECG heart rate variability for machine learning diagnosis of obstructive sleep apnoea: A Bayesian meta-analysis. *Sleep and Breathing*.
- Sessa, F., et al. (2018). Heart rate variability as predictive factor for sudden cardiac death. *Aging, 10*(2), 166-177.
- Attar, E. T. (2025). Detailed evaluation of sleep apnea using heart rate variability. *Frontiers in Neurology, 16*, 1636983.

---

## Real-Time BLE Integration

### Overview

The Real-Time BLE (Bluetooth Low Energy) Integration module enables direct connection to compatible heart rate monitors for live HRV streaming, biofeedback sessions, and continuous monitoring. This provides immediate feedback during training, meditation, or clinical assessments without the delay of post-hoc analysis.

### Scientific Background

BLE heart rate monitors transmit RR intervals in real-time, enabling immediate computation of HRV metrics. The Bluetooth SIG Heart Rate Service specification defines a standardized protocol for HR and RR interval transmission, ensuring interoperability across devices.

**Device Accuracy:**

| Device | RR Accuracy | HRV Agreement | Best For |
|--------|-------------|---------------|----------|
| Polar H10 | <1 ms error | Excellent | Research, clinical |
| Polar H9 | <2 ms error | Very good | Training, biofeedback |
| Garmin HRM-Pro | <3 ms error | Good | Sports training |
| Wahoo TICKR | <3 ms error | Good | Fitness applications |

*Based on Schaffarczyk et al., 2022; Schweizer & Gilgen-Ammann, 2024*

### Supported Devices

#### Polar H10/H9

**Features:**
- True ECG-quality RR intervals
- 1ms timing resolution
- Memory for offline recording
- Dual connectivity (BLE + ANT+)
- Firmware-based artifact detection

**Special Capabilities:**
- Polar Measurement Data (PMD) service for raw ECG
- Accelerometer data for motion detection
- Extended memory (up to 65 hours)

#### Garmin HRM-Pro/HRM-Dual

**Features:**
- Running dynamics (HRM-Pro)
- Dual transmission (ANT+ and BLE)
- Pool swimming compatible
- Long battery life

#### Wahoo TICKR/TICKR X

**Features:**
- Dual-band transmission
- Workout memory (TICKR X)
- Calorie tracking
- Comfortable fit

#### Generic BLE HR Devices

Any device implementing the standard Bluetooth Heart Rate Service (UUID: 0x180D) can connect, though RR interval availability varies.

### Connection Process

**Step 1: Enable Bluetooth**

Ensure system Bluetooth is enabled and the HRV Suite has permission to access Bluetooth devices.

**Step 2: Scan for Devices**

1. Go to "Real-Time BLE" tab
2. Click "Scan for Devices"
3. Wait for device discovery (10-30 seconds)
4. Devices appear in list with signal strength

**Step 3: Connect**

1. Select your device from the list
2. Click "Connect"
3. Wait for connection confirmation
4. Verify RR interval streaming begins

**Step 4: Start Session**

1. Configure session parameters (duration, metrics)
2. Click "Start Recording"
3. Monitor real-time HRV display
4. End session and save data

### Real-Time HRV Computation

The module computes HRV metrics in real-time using sliding windows:

| Metric | Window Size | Update Rate | Latency |
|--------|-------------|-------------|---------|
| Heart Rate | 5 beats | Per beat | <1 sec |
| RMSSD | 30-60 beats | Every 5 beats | ~30 sec |
| SDNN | 60-120 beats | Every 10 beats | ~60 sec |
| Coherence | 60 beats | Every 5 beats | ~30 sec |
| Respiratory Rate | 60 beats | Every 10 beats | ~60 sec |

### Coherence Biofeedback

The coherence score provides real-time feedback on HRV patterns optimal for stress reduction and emotional regulation.

**Coherence Calculation:**

Coherence reflects the presence of a dominant frequency in the 0.04-0.26 Hz range (resonance frequency), indicating synchronized heart-brain activity.

```
Coherence = (Power in coherence band) / (Total power) × Peak sharpness factor
```

**Coherence Levels:**

| Level | Score | Visual Feedback | Interpretation |
|-------|-------|-----------------|----------------|
| Low | 0-33 | Red | Scattered, irregular pattern |
| Medium | 34-66 | Yellow | Developing coherence |
| High | 67-100 | Green | Optimal coherent state |

### Biofeedback Session Protocol

**Preparation:**
1. Quiet environment, comfortable position
2. Wet electrodes for good contact
3. Allow 2-3 minutes for signal stabilization

**Session Structure:**
1. **Baseline** (2 min): Relaxed breathing, establish baseline
2. **Paced breathing** (5-15 min): Follow breathing guide (typically 6 breaths/min)
3. **Free practice** (optional): Maintain coherence without guide
4. **Recovery** (2 min): Return to normal breathing

**Breathing Guide:**

The visual breathing guide displays:
- Inhale/exhale timing (adjustable ratio)
- Target breathing rate (4-7 breaths/min)
- Real-time coherence feedback
- Session progress

### Session Recording and Export

**Recorded Data:**
- All RR intervals with timestamps
- Computed HRV metrics (per-window)
- Coherence scores
- Session markers and notes
- Device information

**Export Formats:**
- CSV (RR intervals + metrics)
- JSON (complete session data)
- HRV Suite format (for re-analysis)

### Technical Considerations

#### Signal Quality

**Electrode Contact:**
- Wet chest strap electrodes before use
- Ensure snug but comfortable fit
- Position below pectoral muscles

**Motion Artifacts:**
- Minimize movement during sessions
- Some devices have motion compensation
- Review data for artifact periods

#### Connectivity Issues

| Issue | Possible Cause | Solution |
|-------|----------------|----------|
| Device not found | Bluetooth off, device not advertising | Enable Bluetooth, wake device |
| Connection drops | Distance, interference | Move closer, reduce interference |
| No RR intervals | Device limitation, firmware | Check device specs, update firmware |
| Erratic data | Poor electrode contact | Rewet electrodes, adjust fit |

### Platform Limitations

⚠️ **Web Browser Limitations:**

The Web Bluetooth API has restrictions:
- Requires HTTPS or localhost
- User gesture required to initiate scan
- Limited to specific browsers (Chrome, Edge)
- Some features require desktop app

**Desktop Application:**

For full BLE functionality, consider the desktop version which provides:
- Background connections
- Multiple device support
- Extended recording sessions
- System-level Bluetooth access

### References

- Schaffarczyk, M., Rogers, B., Reer, R., & Gronwald, T. (2022). Validity of the Polar H10 sensor for heart rate variability analysis. *Sensors, 22*(17), 6536.
- Schweizer, T., & Gilgen-Ammann, R. (2024). Wrist-worn and arm-worn wearables for monitoring heart rate. *JMIR mHealth and uHealth*.
- Martini, C., et al. (2022). Commercially available heart rate monitor repurposed for automatic arrhythmia detection. *Diagnostics, 12*(3), 712.
- Gilgen-Ammann, R., et al. (2019). RR interval signal quality of a heart rate monitor and an ECG Holter. *Sensors, 19*(21), 4717.

---

## Docker Deployment

The Mission Control - Flight Surgeon supports containerized deployment for production environments with persistent data storage.

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 10GB disk space

### Quick Start

```bash
# Clone repository
git clone https://github.com/strikerdlm/HRV.git
cd HRV

# Create environment file
cp .env.example .env
# Edit .env with your settings

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Run TypeScript Frontend with FastAPI (optional)
docker-compose --profile typescript up -d api
```

The Streamlit application will be available at `http://localhost:8501`.

### Services

| Service | Port | Description |
|---------|------|-------------|
| **app** | 8501 | Streamlit application |
| **api** | 8180 | FastAPI backend (for TypeScript frontend) |
| **db** | 5432 | PostgreSQL with TimescaleDB |
| **redis** | 6379 | Session caching |
| **pgadmin** | 5050 | Database administration (optional) |

### Environment Variables

Create a `.env` file with:

```env
# Database credentials
POSTGRES_DB=hrv_platform
POSTGRES_USER=hrv_admin
POSTGRES_PASSWORD=your_secure_password

# Application settings
APP_PORT=8501
LOG_LEVEL=INFO

# API keys (optional)
OPENAI_API_KEY=sk-your-key
NASA_API_KEY=DEMO_KEY
```

⚠️ **Security:** Never commit `.env` files to version control.

### Data Persistence

Docker volumes ensure data persistence:

| Volume | Purpose |
|--------|---------|
| `hrv_postgres_data` | User profiles, HRV data, correlations |
| `hrv_redis_data` | Session cache |
| `hrv_app_data` | Uploaded files, exports |

### Database Schema

The PostgreSQL database includes:

- **user_profiles:** Biometric data and clinical scales
- **noaa_kp_index:** Geomagnetic storm indices
- **noaa_f107_index:** Solar radio flux
- **noaa_solar_wind:** Real-time solar wind parameters
- **hrv_sw_correlations:** HRV-space weather correlation results
- **ml_predictions:** Machine learning prediction history

### Production Considerations

1. **SSL/TLS:** Configure reverse proxy (nginx, Traefik) for HTTPS
2. **Backups:** Schedule regular PostgreSQL backups
3. **Monitoring:** Add health check endpoints to monitoring system
4. **Scaling:** Use Docker Swarm or Kubernetes for high availability

### Useful Commands

```bash
# Stop services
docker-compose down

# Stop and remove volumes (CAUTION: deletes data)
docker-compose down -v

# Rebuild after code changes
docker-compose build --no-cache app
docker-compose up -d

# Database backup
docker exec hrv_database pg_dump -U hrv_admin hrv_platform > backup.sql

# Access database shell
docker exec -it hrv_database psql -U hrv_admin -d hrv_platform

# Include pgAdmin for database management
docker-compose --profile admin up -d
```

---

## Radiation Exposure Module

*Added in v1.8.80*

The Radiation Exposure Module provides evidence-based space radiation dose estimation, day-by-day cumulative tracking, and EVA Go/No-Go assessment for exploration medicine operations.

### Overview

Location: **User Profile → Clinical Profile → Exploration Medical Analytics → ☢️ Radiation Exposure**

The module supports 10 radiation environments with literature-derived dose rates:

| Environment | Dose Rate (mSv/day) | Source |
|-------------|---------------------|--------|
| Earth Surface | 0.007 | Background radiation |
| Antarctica | 0.009 | Elevated cosmic rays |
| Flight Altitude (12 km) | 0.015 | Aviation exposure |
| LEO/ISS | 0.50 | MATROSHKA-R (Berger 2020) |
| Lunar Gateway | 1.05 | NASA estimates |
| Lunar Transit | 1.30 | Deep space GCR |
| Lunar Surface (nominal) | 0.55 | Chang'E-4 LND (Zhang 2020) |
| Lunar Surface (SPE) | 5.50 | Solar particle events |
| Mars Transit | 1.84 | MSL RAD (Zeitlin 2013) |
| Mars Surface | 0.67 | MSL RAD (Hassler 2014) |

### Features

**4-Tab Interface:**

1. **Current Status**: Cumulative dose gauge showing career percentage against NASA STD-3001 limits (600 mSv career)
2. **Day-by-Day Timeline**: ECharts line chart with dose accumulation over time and limit threshold lines (30%, 60%, 80%, 100%)
3. **Environment Comparison**: Bar chart comparing projected doses across all environments
4. **EVA Go/No-Go Matrix**: SAFTE-style heatmap showing risk levels based on cumulative dose and space weather conditions

**EVA Risk Assessment:**

| Status | Career % | Criteria |
|--------|----------|----------|
| 🟢 GO | <30% | Normal operations |
| 🟡 CAUTION | 30-60% | Enhanced monitoring |
| 🟠 MARGINAL | 60-80% | Mission review required |
| 🔴 NO-GO | >80% | EVA prohibited |

### Scientific References

- NASA. (2015). *NASA Space Flight Human-System Standard Volume 1, Revision A: Crew Health* (NASA-STD-3001). https://www.nasa.gov/sites/default/files/atoms/files/nasa-std-3001_vol_1_rev_a.pdf
- Zhang, S., et al. (2020). First measurements of the radiation dose on the lunar surface. *Science Advances, 6*(39), eaaz1334. https://doi.org/10.1126/sciadv.aaz1334
- Zeitlin, C., et al. (2013). Measurements of energetic particle radiation in transit to Mars on the Mars Science Laboratory. *Science, 340*(6136), 1080-1084. https://doi.org/10.1126/science.1235989
- Hassler, D. M., et al. (2014). Mars' surface radiation environment measured with the Mars Science Laboratory's Curiosity rover. *Science, 343*(6169), 1244797. https://doi.org/10.1126/science.1244797
- Berger, T., et al. (2020). MATROSHKA-R results on the ISS. *Life Sciences in Space Research, 27*, 58-69.
- ICRP. (2013). *Assessment of Radiation Exposure of Astronauts in Space* (Publication 123). Annals of the ICRP, 42(4).

---

## Advanced Wearable Analytics

*Added in v1.8.81*

The Advanced Wearable Analytics module provides sophisticated predictive modeling for Garmin wearable metrics, enabling proactive health monitoring and performance optimization.

### Overview

Location: **User Profile → Clinical Profile → Wrist Monitoring Data → 🧠 Advanced Predictive Analytics**

### Features

**5-Tab Interface:**

1. **Body Battery Forecast**
   - Holt-Winters double exponential smoothing
   - 3-day prediction with 95% confidence intervals
   - Recovery time estimation
   - ECharts visualization with historical + forecast

2. **Allostatic Load Index**
   - Chronic stress assessment (0-10 scale)
   - Based on McEwen (1998) allostatic load model
   - Component breakdown:
     - Cardiovascular (resting HR deviation)
     - Autonomic (HRV depression)
     - Sleep (quality deficit)
     - Energy (Body Battery depletion)
   - Risk levels: Low (0-3), Moderate (3-5), High (5-7), Very High (>7)

3. **Circadian Rhythm Analysis**
   - Chronotype detection (Early Bird / Intermediate / Night Owl)
   - Peak performance hour identification
   - Optimal sleep window recommendations
   - Activity pattern visualization

4. **Stress Prediction**
   - Next-day stress level forecasting
   - Contributing factor identification
   - Personalized recommendations
   - Risk level semaphore (Low/Moderate/High/Very High)

5. **Recovery Status**
   - Recovery state classification (Recovered / Partial / Fatigued / Depleted)
   - Sleep debt calculation (hours)
   - Days to full recovery estimation
   - Optimal rest protocol recommendations

### Scientific References

- McEwen, B. S. (1998). Stress, adaptation, and disease: Allostasis and allostatic load. *Annals of the New York Academy of Sciences, 840*(1), 33-44. https://doi.org/10.1111/j.1749-6632.1998.tb09546.x
- Seeman, T. E., et al. (2001). Allostatic load as a marker of cumulative biological risk. *PNAS, 98*(8), 4770-4775. https://doi.org/10.1073/pnas.081072698
- Hyndman, R. J., & Athanasopoulos, G. (2021). *Forecasting: Principles and Practice* (3rd ed.). OTexts. https://otexts.com/fpp3/

---

## Advanced HRV Analytics Platform

*Added in v1.8.82*

The Advanced HRV Analytics Platform provides state-of-the-art statistical analysis, machine learning pattern recognition, and clinical decision support for comprehensive HRV assessment. This section provides graduate-level physiological explanations for each visualization and metric.

### Overview

Location: **User Profile → History → HRV Measurement History → 🧬 Advanced HRV Analytics**

### Physiological Foundation: The Neurovisceral Integration Model

Heart rate variability reflects the dynamic interplay between the sympathetic and parasympathetic branches of the autonomic nervous system (ANS). The **neurovisceral integration model** (Thayer & Lane, 2000, 2009; Thayer et al., 2012) proposes that HRV serves as an index of the functional integrity of a central autonomic network (CAN) that links prefrontal cortical regions with brainstem nuclei controlling cardiac chronotropy.

The CAN comprises inhibitory GABAergic pathways from the medial prefrontal cortex (mPFC) to the amygdala, which in turn modulates vagal efferent output via the nucleus ambiguus. Under conditions of safety, prefrontal inhibition of the amygdala permits high vagal tone and correspondingly high HRV. Conversely, threat perception or chronic stress disinhibits the amygdala, reducing vagal output and lowering HRV (Thayer & Lane, 2009).

This model explains why reduced HRV is associated with:
- **Impaired executive function** (prefrontal hypofunction)
- **Emotional dysregulation** (amygdala hyperactivity)
- **Chronic disease states** (sustained sympathetic dominance)
- **All-cause mortality** (reduced physiological flexibility)

### Tab 1: Clinical Decision Support — Physiological Interpretation

#### Autonomic Balance Gauge (0-100 Scale)

The autonomic balance score synthesizes multiple HRV indices into a single metric reflecting the sympathovagal equilibrium. Higher scores indicate greater parasympathetic (vagal) predominance, associated with rest-and-digest physiology and adaptive stress responses.

**Physiological Basis:**

The score integrates:
- **RMSSD deviation from age norms**: RMSSD (root mean square of successive differences) reflects beat-to-beat variability primarily mediated by the vagus nerve. Mathematically, RMSSD = √[Σ(RRᵢ₊₁ - RRᵢ)² / (N-1)]. Because successive beat differences are filtered at ~0.15 Hz, RMSSD captures high-frequency vagal modulation with minimal sympathetic contamination (Task Force, 1996).

- **Stress Index (Baevsky)**: SI = AMo / (2 × Mo × MxDMn), where AMo is the amplitude of the modal RR interval, Mo is the mode, and MxDMn is the variation range. Elevated SI (>150) indicates sympathetic dominance and reduced cardiac autonomic flexibility (Baevsky et al., 1984).

- **LF/HF ratio considerations**: While historically interpreted as sympathovagal balance, the LF/HF ratio is now understood to reflect complex, non-linear ANS interactions rather than simple sympathetic-to-parasympathetic ratios. Low-frequency power (0.04-0.15 Hz) contains both sympathetic and parasympathetic contributions, including baroreflex activity (Reyes del Paso et al., 2013).

#### Autonomic State Classification

| State | LF/HF Range | Physiological Interpretation |
|-------|-------------|------------------------------|
| **Parasympathetic Dominant** | <0.8 | High vagal tone; rest-and-digest predominance; typically seen during deep relaxation, post-prandial periods, or trained athletes at rest |
| **Balanced** | 0.8-2.0 | Homeostatic equilibrium; flexible autonomic responsivity; associated with adaptive stress coping |
| **Sympathetic Dominant** | >3.0 | Fight-or-flight activation; elevated catecholamine release; may indicate acute stress, physical exertion, or chronic dysregulation |
| **Dysregulated** | Variable | Inconsistent patterns; may indicate autonomic neuropathy, severe deconditioning, or measurement artifact |

#### Metric Assessments and Z-Scores

Each HRV metric is compared against age- and sex-stratified reference distributions. The Z-score transformation standardizes values: Z = (X - μ) / σ, where X is the observed value, μ is the population mean, and σ is the population standard deviation.

**Clinical Significance Thresholds:**
- |Z| < 1.0: Within normal range (68% of healthy population)
- 1.0 ≤ |Z| < 2.0: Borderline (warning zone)
- |Z| ≥ 2.0: Clinically significant deviation (<5% of healthy population)

### Tab 2: Statistical Tests — Methodological Rationale

#### Descriptive Statistics

| Statistic | Formula | Physiological Relevance |
|-----------|---------|------------------------|
| **Mean** | Σxᵢ/n | Central tendency of HRV distribution |
| **SD** | √[Σ(xᵢ-x̄)²/(n-1)] | Total variability; reflects overall ANS flexibility |
| **Median** | Middle value | Robust central tendency; resistant to outliers |
| **CV%** | (SD/Mean)×100 | Normalized variability; allows cross-metric comparison |
| **Skewness** | Σ[(xᵢ-x̄)/σ]³/n | Distribution asymmetry; positive skew common in HRV |
| **Kurtosis** | Σ[(xᵢ-x̄)/σ]⁴/n - 3 | Tail heaviness; excess kurtosis indicates outlier-prone data |
| **SEM** | SD/√n | Precision of mean estimate; critical for power analysis |

#### Shapiro-Wilk Normality Test

The Shapiro-Wilk test (1965) evaluates the null hypothesis that data are drawn from a normal (Gaussian) distribution. HRV metrics often exhibit positive skewness due to physiological floor effects (RR intervals cannot be negative) and the multiplicative nature of autonomic modulation.

**Test Statistic:** W = (Σaᵢx₍ᵢ₎)² / Σ(xᵢ-x̄)²

**Interpretation:**
- W → 1: Data approximate normality
- p > 0.05: Fail to reject normality (parametric tests appropriate)
- p ≤ 0.05: Significant deviation from normality (consider non-parametric alternatives or log-transformation)

**Clinical Note:** RMSSD and HF power typically require natural log transformation (lnRMSSD, lnHF) for parametric analysis due to inherent positive skewness (Plews et al., 2013).

#### One-Sample t-Test Against Age-Stratified References

The one-sample t-test compares the individual's mean HRV against population reference values:

t = (x̄ - μ₀) / (s/√n)

where μ₀ is the age-stratified reference mean. This test addresses the question: "Is this individual's HRV significantly different from what we expect for their age group?"

**Age-Stratified Reference Values (5-minute recordings):**

| Age Group | RMSSD (ms) | SDNN (ms) | Source |
|-----------|------------|-----------|--------|
| 20-29 | 42.6 ± 18.5 | 50.0 ± 16.0 | Nunan et al. (2010) |
| 30-39 | 34.0 ± 14.5 | 45.0 ± 14.0 | Nunan et al. (2010) |
| 40-49 | 28.5 ± 12.0 | 40.0 ± 12.0 | Shaffer & Ginsberg (2017) |
| 50-59 | 24.0 ± 10.0 | 35.0 ± 11.0 | Shaffer & Ginsberg (2017) |
| 60+ | 20.0 ± 8.5 | 30.0 ± 10.0 | O'Neal et al. (2016) |

**Physiological Rationale:** HRV declines approximately 3-4% per decade due to progressive vagal withdrawal, reduced sinoatrial node responsivity, and arterial stiffening (Geovanini et al., 2020).

#### Cohen's d Effect Size

Cohen's d quantifies the standardized magnitude of difference:

d = (x̄₁ - x̄₂) / s_pooled

**Interpretation (Cohen, 1988):**
- |d| < 0.2: Negligible effect (clinically meaningless)
- 0.2 ≤ |d| < 0.5: Small effect (detectable but modest)
- 0.5 ≤ |d| < 0.8: Medium effect (clinically relevant)
- |d| ≥ 0.8: Large effect (substantial clinical significance)

**Clinical Application:** Effect sizes complement p-values by quantifying practical significance. A statistically significant (p < 0.05) but small (d = 0.2) effect may not warrant clinical intervention.

### Tab 3: Trends & Forecast — Longitudinal Analysis

#### Physiological Rationale for Trend Monitoring

Day-to-day HRV fluctuations reflect the integration of multiple physiological and behavioral inputs:
- **Sleep quality and duration**: Sleep deprivation reduces vagal tone (Tobaldini et al., 2013)
- **Physical training load**: Overtraining suppresses HRV; adequate recovery restores it (Plews et al., 2013)
- **Psychological stress**: Acute stress elevates sympathetic activity; chronic stress produces sustained HRV depression (Lennartsson et al., 2016)
- **Illness and inflammation**: Systemic inflammation reduces vagal tone via the inflammatory reflex (Thayer & Sternberg, 2006)

#### Linear Regression Trend Analysis

The 7-day trend uses ordinary least squares (OLS) regression:

ŷ = β₀ + β₁t

where t is time (days) and ŷ is predicted HRV. The slope (β₁) indicates trend direction:
- β₁ > 0: Improving (increasing vagal tone)
- β₁ ≈ 0: Stable (homeostatic maintenance)
- β₁ < 0: Declining (progressive sympathetic shift or accumulated stress)

**Slope Significance Testing:**

t = β₁ / SE(β₁)

A significant positive slope (p < 0.05) suggests genuine physiological improvement rather than random fluctuation.

#### 7-Day Forecast with Confidence Intervals

The forecast extrapolates the linear trend with 95% confidence bounds:

CI = ŷ ± t₀.₀₂₅ × SE(ŷ)

**Clinical Interpretation:**
- **Narrow CI**: Consistent HRV pattern; high forecast confidence
- **Wide CI**: Variable HRV; forecast uncertainty reflects physiological instability

**Caution:** Linear extrapolation assumes trend continuation. Sudden stressors (illness, travel, acute psychological stress) can invalidate forecasts.

### Tab 4: Anomalies & Patterns — Machine Learning Approaches

#### Anomaly Detection: Z-Score Method

The Z-score method flags observations exceeding ±2.5 standard deviations:

Anomaly if: |Z| = |(xᵢ - x̄) / s| > 2.5

**Physiological Causes of HRV Anomalies:**
- **Unusually low RMSSD**: Acute illness, severe stress, cardiac arrhythmia, measurement artifact
- **Unusually high RMSSD**: Post-exercise parasympathetic rebound, vagal maneuvers, measurement error

#### Anomaly Detection: IQR Method

The interquartile range (IQR) method is robust to non-normal distributions:

Anomaly if: xᵢ < Q₁ - 1.5×IQR or xᵢ > Q₃ + 1.5×IQR

This method identifies outliers in the tails of the distribution without assuming normality.

#### Pattern Recognition: RMSSD Variability (CV%)

Day-to-day RMSSD variability, quantified as coefficient of variation (CV%), indicates measurement consistency and autonomic stability:

| CV% Category | Interpretation | Clinical Implication |
|--------------|----------------|---------------------|
| <15% | Very stable | Consistent physiology; reliable trend detection |
| 15-40% | Normal variability | Expected day-to-day fluctuation |
| >40% | High variability | Inconsistent conditions; consider standardizing measurement protocol |

**Sources of Elevated CV%:**
- Inconsistent measurement timing (circadian effects)
- Variable pre-recording conditions (caffeine, exercise, posture)
- Genuine physiological instability (autonomic dysfunction)

#### Chronic Stress Pattern Detection

The platform identifies chronic stress when >50% of recordings show Stress Index (SI) > 150. Sustained sympathetic dominance is associated with:
- Increased cardiovascular morbidity (Thayer et al., 2010)
- Impaired cognitive performance (Thayer et al., 2009)
- Reduced emotional regulation capacity (Thayer & Lane, 2000)

### Tab 5: HRV + Garmin Integration — Multi-Modal Validation

#### Cross-Validation Rationale

Consumer wearables (Garmin, Oura, Whoop) provide continuous physiological monitoring but with varying accuracy compared to research-grade ECG. Cross-validation identifies:
- **Concordance**: Agreement between sources strengthens confidence
- **Discordance**: Disagreement warrants investigation (device error, timing mismatch, or genuine physiological difference)

#### Validation Evidence for Consumer Wearables

| Device | RMSSD Accuracy | Source |
|--------|----------------|--------|
| Polar H10 (chest strap) | CCC = 0.97-0.99 | Miller et al. (2022); Gold standard for research |
| Oura Ring Gen 3/4 | CCC = 0.97-0.99 | Dial et al. (2025) |
| Garmin (wrist-based) | CCC = 0.87 | Dial et al. (2025); Lower accuracy due to PPG limitations |
| Whoop 4.0 | CCC = 0.94 | Dial et al. (2025) |

#### Cross-Correlation Matrix (Spearman ρ)

Spearman's rank correlation is used because:
1. It does not assume linear relationships
2. It is robust to outliers
3. HRV metrics often have non-normal distributions

**Expected Correlations:**
- **RMSSD ↔ Body Battery**: Moderate positive (r ≈ 0.3-0.5); higher vagal tone supports recovery
- **Stress Index ↔ Garmin Stress Score**: Moderate positive (r ≈ 0.4-0.6); both reflect sympathetic activation
- **SDNN ↔ Sleep Score**: Moderate positive (r ≈ 0.3-0.5); overall HRV reflects sleep quality

#### Discordance Flags

The platform flags discordance when Polar H10 HRV and Garmin metrics disagree significantly (e.g., high RMSSD but low Body Battery). Possible explanations:
- **Timing mismatch**: Garmin averages overnight; Polar captures morning snapshot
- **Algorithm differences**: Proprietary Garmin algorithms may weight factors differently
- **Measurement artifact**: Wrist-based PPG susceptible to motion artifact

### Methodological Considerations for Valid HRV Assessment

Following Task Force (1996) and Quigley et al. (2024) guidelines:

1. **Recording duration**: Minimum 5 minutes for short-term analysis; 24 hours for circadian patterns
2. **Posture standardization**: Supine or seated; consistent across sessions
3. **Time of day**: Circadian variation peaks vagal tone at night; standardize timing
4. **Pre-recording conditions**: Avoid caffeine, alcohol, and vigorous exercise 2+ hours prior
5. **Breathing**: Spontaneous breathing preferred; controlled breathing affects HF power
6. **Artifact handling**: <5% ectopic beats; use validated artifact correction

### Comprehensive Scientific References

**Core HRV Standards:**
- Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology. (1996). Heart rate variability: Standards of measurement, physiological interpretation, and clinical use. *Circulation, 93*(5), 1043-1065. https://doi.org/10.1161/01.CIR.93.5.1043
- Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability metrics and norms. *Frontiers in Public Health, 5*, 258. https://doi.org/10.3389/fpubh.2017.00258
- Quigley, K. S., Kanoski, S., Grill, W. M., Barrett, L. F., & Tsakiris, M. (2024). Publication guidelines for heart rate and heart rate variability. *Psychophysiology, 61*(4), e14604. https://doi.org/10.1111/psyp.14604

**Normative Values:**
- Nunan, D., Sandercock, G. R., & Brodie, D. A. (2010). A quantitative systematic review of normal values for short-term heart rate variability in healthy adults. *Pacing and Clinical Electrophysiology, 33*(11), 1407-1417. https://doi.org/10.1111/j.1540-8159.2010.02841.x
- O'Neal, W. T., Chen, L. Y., Nazarian, S., & Soliman, E. Z. (2016). Reference ranges for short-term heart rate variability measures in individuals free of cardiovascular disease: The Multi-Ethnic Study of Atherosclerosis (MESA). *Journal of Electrocardiology, 49*(5), 686-690. https://doi.org/10.1016/j.jelectrocard.2016.06.008
- Ortega, E., Bryan, C. Y. X., & Christine, N. S. C. (2024). The pulse of Singapore: Short-term HRV norms. *Journal of General Internal Medicine, 39*(1), 101-108. https://doi.org/10.1007/s10484-023-09603-4
- Geovanini, G. R., Vasques, E. R., de Oliveira Alvim, R., et al. (2020). Age and sex differences in heart rate variability and vagal specific patterns—Baependi Heart Study. *Global Heart, 15*(1), 71. https://doi.org/10.5334/gh.873

**Neurovisceral Integration Model:**
- Thayer, J. F., & Lane, R. D. (2000). A model of neurovisceral integration in emotion regulation and dysregulation. *Journal of Affective Disorders, 61*(3), 201-216. https://doi.org/10.1016/S0165-0327(00)00338-4
- Thayer, J. F., & Lane, R. D. (2009). Claude Bernard and the heart-brain connection: Further elaboration of a model of neurovisceral integration. *Neuroscience & Biobehavioral Reviews, 33*(2), 81-88. https://doi.org/10.1016/j.neubiorev.2008.08.004
- Thayer, J. F., Åhs, F., Fredrikson, M., Sollers, J. J., & Wager, T. D. (2012). A meta-analysis of heart rate variability and neuroimaging studies: Implications for heart rate variability as a marker of stress and health. *Neuroscience & Biobehavioral Reviews, 36*(2), 747-756. https://doi.org/10.1016/j.neubiorev.2011.11.009
- Thayer, J. F., Hansen, A. L., Saus-Rose, E., & Johnsen, B. H. (2009). Heart rate variability, prefrontal neural function, and cognitive performance: The neurovisceral integration perspective on self-regulation, adaptation, and health. *Annals of Behavioral Medicine, 37*(2), 141-153. https://doi.org/10.1007/s12160-009-9101-z
- Thayer, J. F., & Sternberg, E. (2006). Beyond heart rate variability: Vagal regulation of allostatic systems. *Annals of the New York Academy of Sciences, 1088*(1), 361-372. https://doi.org/10.1196/annals.1366.014

**Stress and Clinical Applications:**
- Lennartsson, A. K., Jonsdottir, I., & Sjörs, A. (2016). Low heart rate variability in patients with clinical burnout. *International Journal of Psychophysiology, 110*, 171-178. https://doi.org/10.1016/j.ijpsycho.2016.08.005
- Gruionu, G., Aktaruzzaman, M., Gupta, A., et al. (2024). Heart rate variability parameters indicate altered autonomic tone in subjects with COVID-19. *Scientific Reports, 14*, 31082. https://doi.org/10.1038/s41598-024-80918-w
- Roddick, C. M., Seo, Y. S., Barkovich, S. L., et al. (2025). Cardiac vagal recovery following acute psychological stress in human adults: A scoping review. *Neuroscience & Biobehavioral Reviews, 169*, 106268. https://doi.org/10.1016/j.neubiorev.2025.106268

**Wearable Validation:**
- Miller, D. J., Sargent, C., & Roach, G. D. (2022). A validation of six wearable devices for estimating sleep, heart rate and heart rate variability in healthy adults. *Sensors, 22*(16), 6317. https://doi.org/10.3390/s22166317
- Dial, M. B., Hollander, M. E., Vatne, E. A., et al. (2025). Validation of nocturnal resting heart rate and heart rate variability in consumer wearables. *Physiological Reports, 13*(2), e70527. https://doi.org/10.14814/phy2.70527
- Hannon, J., O'Hagan, A., Lambe, R., et al. (2025). Associations between daily heart rate variability and self-reported wellness: A 14-day observational study in healthy adults. *Sensors, 25*(14), 4415. https://doi.org/10.3390/s25144415
- Fuller, D., Colwell, E., Low, J., et al. (2020). Reliability and validity of commercially available wearable devices for measuring steps, energy expenditure, and heart rate: Systematic review. *JMIR mHealth and uHealth, 8*(9), e18694. https://doi.org/10.2196/18694

**Statistical Methods:**
- Cohen, J. (1988). *Statistical power analysis for the behavioral sciences* (2nd ed.). Lawrence Erlbaum Associates.
- Shapiro, S. S., & Wilk, M. B. (1965). An analysis of variance test for normality (complete samples). *Biometrika, 52*(3-4), 591-611. https://doi.org/10.1093/biomet/52.3-4.591
- Plews, D. J., Laursen, P. B., Stanley, J., Kilding, A. E., & Buchheit, M. (2013). Training adaptation and heart rate variability in elite endurance athletes: Opening the door to effective monitoring. *Sports Medicine, 43*(9), 773-781. https://doi.org/10.1007/s40279-013-0071-8

---

## Crew Scheduling & Human Performance

### Overview

The **Crew Scheduling and Human Performance Management** module is a comprehensive tool for mission planning, risk assessment, and GO/NO-GO decisions. It implements evidence-based scoring functions following SAFTE-FAST validation, NASA Human Performance standards, and IOC Energy Availability thresholds.

**Access:**
- **TypeScript Frontend (Modern UI):** http://localhost:3100/scheduling
- **Streamlit (Legacy):** Operational App → 🗓️ Crew Scheduling tab

### TypeScript/Next.js Frontend Implementation (v1.9.16)

The modern frontend provides a complete crew management and scheduling interface with four main tabs:

#### Status Dashboard Tab
- **Crew Status Overview**: Grid of IHPI circular gauge widgets showing real-time performance scores for each crew member
- **IHPI Gauges**: Visual circular progress indicators (0-100) with color-coded zones:
  - Green (≥80%): GO status
  - Yellow (60-79%): MARGINAL status
  - Red (<60%): NO-GO status
- **Sub-metrics Display**: Fatigue level, sleep debt (hours), and readiness score per crew member
- **Active Alerts Panel**: Real-time warnings and recommendations (elevated fatigue, EVA preparation, etc.)
- **Day Summary Card**: Task completion progress, work hours, exercise hours, sleep scheduled, compliance percentage

#### Schedule Tab
- **Date Navigation**: Previous/next day controls with "Today" quick button
- **Category Filters**: Filter activities by type (medical, exercise, experiment, work, meal, sleep, maintenance, communication, personal, emergency)
- **Activity Cards**: Timeline view with:
  - Time column (start/end in 12-hour format)
  - Activity title and description
  - Priority badge (critical/high/medium/low with color coding)
  - Category badge with location
  - Assigned crew members
  - Status controls (Start, Complete, Done indicators)
- **Day Summary**: Real-time tracking of completed tasks and compliance

#### Crew Management Tab
- **Crew Member Cards**: Card-based UI showing:
  - Role designation (CDR, PLT, MS1-MS4)
  - Status indicator (on duty, off duty, rest, EVA, medical)
  - IHPI score with progress bar
  - Quick stats grid (sleep debt, fatigue, readiness)
  - Edit and Delete buttons
- **Add Crew Member Dialog**: Create new profiles with username, full name, sex, and role
- **Comprehensive Admin Profile Editor**: 5-section tabbed dialog for full profile editing:

  **1. Identity Section**
  - Full name, email, sex (male/female/other)
  - Date of birth (date picker)
  - Language preference (EN, ES, FR, DE, RU, ZH, JA)
  - Read-only metadata: User ID, username, creation date

  **2. Operational Section**
  - Crew role: CDR (Commander), PLT (Pilot), MS1-MS4 (Mission Specialists)
  - Current status: On Duty, Off Duty, Rest Period, EVA Operations, Medical Hold
  - Occupation/specialty field

  **3. Biometrics Section**
  - Height (cm) with range validation (100-250)
  - Weight (kg) with 0.1 precision
  - Resting heart rate (bpm) range 30-120
  - Maximum heart rate (bpm) range 120-220
  - VO2max (ml/kg/min) with 0.1 precision
  - Activity level selector (sedentary to very active)
  - Auto-calculated BMI display

  **4. Lifestyle Section**
  - Smoking status: Never, Former, Current (light/moderate/heavy)
  - Alcohol use: None, Occasional, Light, Moderate, Heavy
  - Daily caffeine intake (mg) with reference values (1 cup coffee ≈ 95mg)

  **5. Medical Section**
  - Medical conditions (comma-separated list)
  - Current medications with dosage (comma-separated list)
  - Confidentiality notice for sensitive data

#### Performance Tab
- **IHPI Gauge Grid**: Circular gauges for all crew members with sub-metrics
- **Detailed Metrics Table**: Tabular view with columns:
  - Crew member (role + name)
  - Status badge
  - IHPI percentage (color-coded)
  - Fatigue level
  - Sleep debt
  - Readiness score
  - Go/No-Go determination (GO, MARGINAL, NO-GO badges)
- **Scientific Foundation**: Evidence citations (Hursh et al. 2004, Samel et al. 1997, Van Dongen et al. 2003)

### Mission Workspace Selector

The frontend includes a mission workspace selector at the top of the scheduling page:
- Switch between Mission 1 and Mission 2
- Mission-scoped database and configurations
- Visual indicator showing active mission

### Key Components

#### 1. Integrated Human Performance Indicator (IHPI)

The IHPI is a composite score (0-100) that integrates eight performance domains with hard-cap gating logic:

| Component | Weight | Source/Standard |
|-----------|--------|-----------------|
| SAFTE Effectiveness | 30% | SAFTE-FAST validation |
| PVT Performance | 20% | 3-min protocol, 355ms lapse |
| Circadian Alignment | 10% | Phase offset vs chronotype |
| HRV (lnRMSSD z-score) | 10% | Plews et al. (2013) |
| Hydration Status | 10% | ACSM + USG thresholds |
| Energy Availability | 10% | IOC Consensus (2018) |
| Subjective Sleepiness | 5% | KSS + Samn-Perelli |
| Task-Specific Readiness | 5% | VO2max + recovery time |

**Hard-Cap Gating:** If any critical domain (SAFTE, Hydration, PVT, Subjective) scores 0, the entire IHPI is capped at 0 regardless of other component scores.

#### 2. Subscore Mappers (0-1 Scale)

Each component uses scientifically validated scoring functions:

| Metric | Score = 1.0 | Score = 0.0 | Mapping |
|--------|-------------|-------------|---------|
| SAFTE Effectiveness | ≥90% | ≤70% | Linear 70→90 |
| KSS (Sleepiness) | ≤5 | ≥8 | Linear 5→8 |
| PVT Lapses (3-min) | ≤10 | ≥20 | Linear 10→20 |
| HRV z-score | ≥-0.5 | ≤-2.0 | Linear |
| Body Mass Loss | ≤0.5% | ≥2.0% | Linear |
| USG | <1.020 | ≥1.030 | Linear |
| Energy Availability | ≥45 kcal/kg FFM | ≤30 kcal/kg FFM | Linear |
| Circadian Offset | ≤1 hour | ≥6 hours | Linear |

#### 3. EVA GO/NO-GO Decision Matrix

The decision algorithm follows a hierarchical gate structure:

**Hard NO-GO Gates (any triggers NO-GO):**
- SAFTE Effectiveness < 70% (critical risk zone)
- KSS Score ≥ 8 (severe sleepiness)
- Sleep < 6h in last 24h
- Time Awake ≥ 21h
- Body Mass Loss > 2%
- USG ≥ 1.030
- PVT Lapses ≥ 20 (3-min protocol)
- VO2max < 32.9 ml/kg/min (NASA requirement)
- Time Since Last EVA < 24h

**HOLD Zone:**
- SAFTE 70-79% (high-risk zone, requires mitigation)

**GO Thresholds:**
- **GO**: IHPI ≥ 85, all gates passed
- **GO-with-mitigation**: IHPI 75-84, add naps/breaks/task simplification
- **HOLD**: IHPI < 75, optimize sleep / delay EVA / reduce workload

### Activity Management

#### Fixed Activities (Daily Requirements)

| Activity | Duration | Timing | MET Value |
|----------|----------|--------|-----------|
| Briefing | 60 min | 07:00 (sync) | 1.3-1.8 |
| Breakfast | 45 min | Flexible | 1.5 |
| Lunch | 45 min | Flexible | 1.5 |
| Dinner | 45 min | Flexible | 1.5 |
| Exercise | 60 min | Resource limited | 6-8 |
| Recreation | 60 min | Individual | 1-6 |
| Hygiene | 30 min | Pre-duty | 2.0-2.8 |
| Sleep | 8 hours | Optimized | 1.0 |

#### Variable Activities

| Activity | MET Value | Recovery | Special Requirements |
|----------|-----------|----------|---------------------|
| Lab Work | 1.5-2.5 | 15 min/hr | Cognitive load |
| EVA | 2-7 | 48h min | VO2max ≥32.9, medical clearance |

**Energy Computation:** All metabolic costs stored in kcal (nutrition) and Watts (thermal/ECLSS).
- Formula: `kcal/hr = MET × body_mass_kg`
- EVA planning: +200 kcal per EVA-hour above nominal intake

### UI Tabs (Streamlit Legacy)

#### Status Dashboard
- **Live Crew Cards**: 6 crew status cards with color-coded IHPI gauges
- **Alert Panel**: Active warnings and recommendations
- **Quick Actions**: One-click access to individual crew details

#### Timeline & Scheduling
- **24-Hour Gantt Chart**: Activity timeline with crew assignments
- **Activity Legend**: Color-coded by activity type
- **Scheduling Controls**: Add, modify, or remove activities
- **Optimization**: "Optimize Schedule" button for constraint-based optimization

#### Risk Analysis
- **Risk Matrix Heatmap**: Likelihood × Severity grid per domain
- **Individual Performance Gauges**: IHPI radar charts per crew member
- **Trend Analysis**: Historical risk patterns

#### Summary & Export
- **Readiness Metrics**: Aggregate crew readiness statistics
- **Alerts Summary**: Consolidated warning list
- **Export Options**: JSON, CSV data export

### API Endpoints

The FastAPI backend exposes the following endpoints for crew management:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/users` | GET | List all user profiles |
| `/api/users` | POST | Create new user profile |
| `/api/users/{user_id}` | GET | Get specific user profile |
| `/api/users/{user_id}` | PUT | Update user profile (all fields) |
| `/api/users/{user_id}` | DELETE | Delete user profile |

The PUT endpoint accepts all `UserProfile` fields including:
- Identity: `full_name`, `email`, `sex`, `date_of_birth`, `language`
- Biometrics: `height_cm`, `weight_kg`, `resting_hr_bpm`, `max_hr_bpm`, `vo2max_ml_kg_min`, `activity_level`
- Lifestyle: `smoking_status`, `alcohol_use`, `caffeine_intake_mg`
- Medical: `medical_conditions` (array), `medications` (array), `occupation`

### Scientific References

All scoring functions, thresholds, and decision logic are derived from peer-reviewed literature and validated standards. References include DOIs/PMIDs for verification.

#### Fatigue Models & Performance Prediction

1. **Hursh SR**, Redmond DP, Johnson ML, et al. (2004). Fatigue models for applied research in warfighting. *Aviation, Space, and Environmental Medicine, 75*(3 Suppl), A44-A53. **PMID: 15018265**
   - *Key finding:* SAFTE effectiveness thresholds validated: ≥90% low-risk, ≤70% approximates 0.08 BAC cognitive impairment
   - *Used for:* SAFTE scoring function (70→90 maps to 0→1), fatigue risk zones

2. **Paul MA**, Hursh SR, Love R. (2020). The Importance of Validating Sleep Behavior Models for Fatigue Management Software in Military Aviation. *Military Medicine, 185*(11-12), e1986-e1992. https://doi.org/10.1093/milmed/usaa210
   - *Key finding:* SAFTE-FAST harmonized in Canadian Air Force; achieved near-perfect fatigue risk estimates after population-specific calibration
   - *Used for:* Military aviation fatigue management validation

3. **Veksler BZ**, Morris MB, Krusmark M, Gunzelmann G. (2022). Integrated Modeling of Fatigue Impacts on C-17 Approach and Landing Performance. *Journal of Cognitive Engineering and Decision Making, 17*(2), 123-145. https://doi.org/10.1080/24721840.2022.2149526
   - *Key finding:* Biomathematical fatigue models successfully predict performance degradations on specific aircraft operations
   - *Used for:* SAFTE integration with task-specific performance models

#### Heart Rate Variability & Recovery

4. **Task Force of the European Society of Cardiology and NASPE**. (1996). Heart rate variability: standards of measurement, physiological interpretation and clinical use. *European Heart Journal, 17*, 354-381. https://doi.org/10.1093/oxfordjournals.eurheartj.a014868
   - *Key finding:* Gold-standard HRV protocols: 5-min short-term recordings, RMSSD as primary vagal marker
   - *Used for:* HRV measurement standards, RMSSD interpretation thresholds

5. **Plews DJ**, Laursen PB, Stanley J, Kilding AE, Buchheit M. (2013). Training adaptation and heart rate variability in elite endurance athletes: Opening the door to effective monitoring. *Sports Medicine, 43*(9), 773-781. https://doi.org/10.1007/s40279-013-0071-8
   - *Key finding:* lnRMSSD z-score approach with 14-28 day rolling baseline; z < -1 indicates overreaching/inadequate recovery
   - *Used for:* HRV z-score calculation (-0.5→-2.0 maps to 1→0), individualized monitoring

6. **Esco MA**, Fields AD, Mohammadnabi MA, Kliszczewicz BM. (2025). Monitoring Training Adaptation and Recovery Status in Athletes Using Heart Rate Variability via Mobile Devices. *Sensors, 26*(1), 3. https://doi.org/10.3390/s26010003
   - *Key finding:* Weekly RMSSD averages and coefficient of variation capture chronic adaptations and acute perturbations
   - *Used for:* Mobile HRV monitoring protocols, recovery assessment patterns

#### Energy Availability & RED-S

7. **Mountjoy M**, Sundgot-Borgen JK, Burke LM, et al. (2018). IOC Consensus Statement on Relative Energy Deficiency in Sport (RED-S): 2018 Update. *British Journal of Sports Medicine, 52*(11), 687-697. https://doi.org/10.1136/bjsports-2018-099193
   - *Key finding:* EA thresholds established: ≥45 kcal/kg FFM/day optimal; <30 kcal/kg FFM/day triggers physiological impairments
   - *Used for:* Energy Availability scoring (30→45 maps to 0→1), RED-S risk assessment

8. **Mountjoy M**, Ackerman KE, Bailey DM, et al. (2023). 2023 International Olympic Committee's (IOC) Consensus Statement on Relative Energy Deficiency in Sport (REDs). *British Journal of Sports Medicine, 57*(17), 1073-1097. https://doi.org/10.1136/bjsports-2023-106994
   - *Key finding:* Updated REDs Clinical Assessment Tool Version 2 with severity classification and return-to-sport guidelines
   - *Used for:* Updated EA assessment methodology, clinical decision support

#### Vigilance & Psychomotor Performance

9. **Basner M**, Dinges DF. (2011). Maximizing sensitivity of the psychomotor vigilance test (PVT) to sleep loss. *Sleep, 34*(5), 581-591. https://doi.org/10.1093/sleep/34.5.581
   - *Key finding:* 3-minute PVT with 355ms lapse threshold highly sensitive to sleep loss; comparable to 10-minute gold standard
   - *Used for:* PVT scoring function (10-20 lapses maps to 1→0), vigilance assessment

10. **Åkerstedt T**, Gillberg M. (1990). Subjective and objective sleepiness in the active individual. *International Journal of Neuroscience, 52*(1-2), 29-37. https://doi.org/10.3109/00207459008994241
    - *Key finding:* KSS validated against EEG: 1-5 alert states, 6-7 caution, 8-9 severe sleepiness requiring intervention
    - *Used for:* KSS scoring (5→8 maps to 1→0), subjective sleepiness assessment

#### EVA Physiology & NASA Standards

11. **NASA-STD-3001 Volume 1 Revision B**. (2022). Human Performance Capabilities. NASA Johnson Space Center. Document JSC-65044.
    - *Key finding:* EVA VO₂max requirement: ≥32.9 ml/kg/min for microgravity extravehicular operations
    - *Used for:* EVA GO/NO-GO VO₂max gate, task-specific readiness scoring

12. **Waligora JM**, Kumar KV. (1995). Energy utilization rates during shuttle extravehicular activities. NASA Technical Report, NTRS. **PMID: 11540993**
    - *Key finding:* Shuttle EVA average metabolic rate: 194 kcal/hr (significantly lower than Skylab 238 kcal/hr due to improved training)
    - *Used for:* EVA MET value assignment (~4.5 METs for 70kg), energy expenditure planning

13. **Greenleaf JE**. (1989). Energy and thermal regulation during bed rest and spaceflight. *Journal of Applied Physiology, 67*(2), 507-516. **PMID: 2676944**
    - *Key finding:* Long-duration spaceflight energy requirements ~3,100 kcal/day; 5-hr EVA sortie adds +529,250 kcal/year
    - *Used for:* Mission energy planning, EVA nutritional requirements (+200 kcal/EVA-hour)

#### Metabolic Equivalents

14. **Ainsworth BE**, Haskell WL, Herrmann SD, et al. (2024). 2024 Compendium of Physical Activities: A Third Update of Activity Codes and MET Intensities. *Medicine & Science in Sports & Exercise, 56*(Suppl), S1-S152. https://doi.org/10.1249/MSS.0000000000003356
    - *Key finding:* Standardized MET values for 800+ activities: sleeping 1.0, sitting meetings 1.5, cycling moderate 7.0 METs
    - *Used for:* Activity MET assignments, daily energy expenditure calculations

#### Hydration & Cognitive Performance

15. **Armstrong LE**, Casa DJ, Millard-Stafford M, et al. (2007). ACSM position stand: Exertional heat illness during training and competition. *Medicine & Science in Sports & Exercise, 39*(3), 556-572. https://doi.org/10.1249/mss.0b013e31802fa199
    - *Key finding:* Body mass loss >2% impairs cognitive and physical performance; USG ≥1.030 indicates significant hypohydration
    - *Used for:* Hydration scoring thresholds (0.5%→2% maps to 1→0), dehydration NO-GO gates

#### Circadian & Fatigue Management Standards

16. **ICAO Doc 9966**. (2016). Manual for the Oversight of Fatigue Management Approaches. International Civil Aviation Organization, 2nd Edition.
    - *Key finding:* Circadian phase misalignment >6 hours severely degrades performance; FRMS requires evidence-based prescriptive limits
    - *Used for:* Circadian scoring (1h→6h offset maps to 1→0), FRMS framework

17. **AFMAN 11-202V3**. (2022). General Flight Rules. U.S. Air Force Manual.
    - *Key finding:* Military crew rest requirements: minimum 8 hours rest opportunity, maximum 16 hours duty day
    - *Used for:* Crew rest planning, duty time limits, sleep gate thresholds

### Interpreting Results

#### IHPI Score Interpretation

| Score Range | Status | Action |
|-------------|--------|--------|
| 85-100 | GO | All systems nominal |
| 75-84 | GO-with-mitigation | Add countermeasures |
| 60-74 | HOLD | Delay activity, optimize rest |
| <60 | NO-GO | Medical/rest intervention required |

#### Risk Level Colors

| Color | Risk Level | Meaning |
|-------|------------|---------|
| 🟢 Green | Low | Optimal performance expected |
| 🔵 Blue | Normal | Acceptable with monitoring |
| 🟡 Yellow | Moderate | Caution, mitigation recommended |
| 🔴 Red | High/Critical | Activity restriction required |

### Best Practices

1. **Baseline Establishment**: Allow 2 weeks minimum for HRV baseline (rolling 14-28 day window)
2. **Standardized Measurements**: HRV measured morning, seated, 5-min duration
3. **Recovery Planning**: Minimum 48h between EVAs (24h absolute minimum with FS approval)
4. **Energy Balance**: Monitor Energy Availability to prevent RED-S
5. **Hydration Tracking**: Daily body mass measurements + USG when available
6. **Circadian Alignment**: Optimize sleep timing to individual chronotype

### Space Weather & EVA Radiation Dashboards

*Added in v1.9.1*

The Crew Scheduling module includes comprehensive real-time space weather monitoring and EVA radiation assessment dashboards designed for mission control operations.

#### EVA Radiation Metrics Dashboard

**Location:** Crew Scheduling → EVA Procedures & Checklists → ☢️ Radiation → Space Radiation Assessment for EVA

**Purpose:** Provides real-time visualization of the three most critical radiation parameters used by Mission Control for EVA decision-making.

**Visualization Features:**

- **Multi-Metric Horizontal Bar Chart**: Displays Proton Flux (>10 MeV), Kp Index, and EVA Dose Rate
- **Normalized Display**: All metrics shown as percentage of critical threshold (0-200%) for visual comparison
- **Color-Coded Risk Zones**: 
  - Green: Low risk (<50% of threshold)
  - Yellow/Orange: Moderate risk (50-100% of threshold)
  - Red: High risk (>100% of threshold)
- **Critical Threshold Reference**: Red dashed line at 100% indicating operational critical threshold
- **Dynamic Axis Scaling**: Uses `_auto_axis_bounds()` to ensure all data points are visible
- **Real-Time Data Integration**: Fetches live space weather data from NOAA SWPC and SpaceWeatherLive APIs

**Metrics Displayed:**

1. **Proton Flux (>10 MeV, pfu)**
   - Indicates solar particle event (SPE) activity
   - S-Scale classification (S0-S5)
   - Color coding based on current S-scale level

2. **Kp Index**
   - Geomagnetic activity indicator
   - G-Scale classification (G0-G5)
   - Color coding based on current G-scale level

3. **EVA Dose Rate (mSv/hr)**
   - Estimated radiation exposure during planned EVA
   - Based on selected mission environment and space weather conditions
   - Thresholds: Normal (<0.8 mSv/hr), Caution (2.0 mSv/hr), Warning (5.0 mSv/hr), NO-GO (10.0 mSv/hr)

**Interpretation:**

- Values <100%: Below critical threshold, operations may proceed with standard protocols
- Values ≥100%: At or above critical threshold, enhanced monitoring or mission modification required
- Color coding provides immediate visual risk assessment

#### Space Weather Real-Time Dashboard

**Location:** Crew Scheduling → EVA Procedures & Checklists → ☢️ Radiation → Additional Real-Time Data

**Purpose:** Beautiful gauge-based visualization of real-time space weather parameters for operational monitoring.

**Layout:**

- **Top Row (3 gauges)**: Flare probability gauges
  - C-Class Flare Probability (0-100%)
  - M-Class Flare Probability (0-100%)
  - X-Class Flare Probability (0-100%)

- **Bottom Row (2 gauges)**: Space environment metrics
  - F10.7 Flux (50-300 sfu) with historic average and projected trend
  - Active CMEs (0-10 count)

**Gauge Features:**

- **Modern Two-Ring Style**: Animated progress indicators with color-coded zones
- **Color Semantics**:
  - Green: Low risk/normal conditions
  - Yellow/Orange: Moderate risk/caution
  - Red: High risk/warning
- **Real-Time Updates**: Data source and timestamp displayed in subtitle
- **Large Display**: 380px height for improved visibility in mission control environments

**F10.7 Flux Gauge:**

- **Range**: 50-300 sfu (typical solar cycle range)
- **Historic Average**: Displays typical solar cycle average (150 sfu)
- **Projected Trend**: Shows estimated future value based on current trend
- **Color Zones**: 
  - Green (50-100 sfu): Low solar activity
  - Yellow (100-200 sfu): Moderate solar activity
  - Red (200-300 sfu): High solar activity

**Active CMEs Gauge:**

- **Range**: 0-10 CMEs
- **Color Zones**:
  - Green (0-2 CMEs): Low activity
  - Yellow (2-5 CMEs): Moderate activity
  - Red (5+ CMEs): High activity

**Flare Probability Gauges:**

- **C-Class**: Minor flares, typically low impact
  - Color zones: Green (<30%), Yellow (30-60%), Red (>60%)
- **M-Class**: Moderate flares, can affect communications
  - Color zones: Blue (<20%), Yellow (20-40%), Red (>40%)
- **X-Class**: Extreme flares, significant operational impact
  - Color zones: Yellow (<5%), Orange (5-15%), Red (>15%)

**Data Sources:**

- NOAA Space Weather Prediction Center (SWPC)
- SpaceWeatherLive API
- NASA Space Radiation Analysis Group (SRAG)

**Operational Use:**

1. **Pre-EVA Assessment**: Review all gauges before EVA planning
2. **Real-Time Monitoring**: Monitor space weather conditions during mission operations
3. **Risk Communication**: Use color-coded zones for quick risk assessment in mission briefings
4. **Trend Analysis**: F10.7 Flux projection helps anticipate future space weather conditions

#### Scientific References

- NOAA Space Weather Prediction Center. (n.d.). *Space Weather Scales* (R, S, G). Retrieved from https://www.swpc.noaa.gov/noaa-scales-explanation
- NASA-STD-3001 Vol 1 Rev B. (2022). *Crew Health Standard*. NASA Johnson Space Center.
- Space Weather Prediction Center. (n.d.). *Operational Thresholds*. Retrieved from https://www.swpc.noaa.gov/
- SpaceWeatherLive. (n.d.). *API Documentation*. Retrieved from https://www.spaceweatherlive.com/

---

## Pending Developments and Roadmap

This section outlines completed features and remaining planned enhancements for the Mission Control - Flight Surgeon.

### Completed Features (Q1 2026)

✅ **Comprehensive Crew Scheduling Frontend (v1.9.16)** - Full TypeScript/Next.js operational app with Status Dashboard, Schedule management, Crew Management (CRUD), Performance metrics, comprehensive 5-section admin profile editor, mission workspace selector

### Completed Features (Q4 2025)

✅ **Enhanced Space Weather & EVA Radiation Dashboards (v1.9.1)** - Real-time gauge-based space weather visualization, EVA radiation metrics dashboard with normalized threshold display, verified technical resource links  
✅ **Crew Scheduling & Human Performance (v1.9.0)** - IHPI composite scoring, EVA GO/NO-GO matrix, constraint-based optimization, real-time risk assessment  
✅ **Radiation Exposure Module (v1.8.80)** - Evidence-based dose models for 10 environments, day-by-day tracking, EVA Go/No-Go matrix  
✅ **Advanced Wearable Analytics (v1.8.81)** - Body Battery forecasting, Allostatic Load Index, Circadian Rhythm Analysis, Stress Prediction  
✅ **Advanced HRV Analytics Platform (v1.8.82)** - ML pattern recognition, statistical tests, trend forecasting, clinical decision support  
✅ **ECG R-Peak Detection** - Pan-Tompkins algorithm with template matching  
✅ **Multi-Modal Sensor Fusion** - Oura, WHOOP, Apple Health, Fitbit integration  
✅ **Long-Term Trending** - Baseline establishment, trend detection, alerts  
✅ **Exercise HRV Analysis** - HRR, parasympathetic reactivation, TRIMP  
✅ **ML Predictions** - AF risk, SCD stratification, sleep apnea screening  
✅ **Real-Time BLE Integration** - Polar H10/H9, Garmin, Wahoo support  
✅ **Population Norms Comparison** - Age/sex-stratified reference values from Nunan, Ortega, MESA  
✅ **Blood Pressure Variability** - BPV metrics with HRV-BPV correlation analysis  
✅ **Circadian Physiology Module** - Complete integration with all advanced tools
  - Forger99, Jewett99, Hannay19, Hannay19TP models
  - ESRI (Entrainment Signal Regularity Index)
  - Cosinor analysis for phase extraction
  - Phase Response Curves (PRC), Intensity Response Curves (IRC)
  - Two-Process Model of sleep regulation
  - Synthetic data generation
  - Actiwatch and wearable data readers
✅ **User Profiles System** - Biometrics and validated clinical scales (ESS, KSS, PSQI)  
✅ **Docker Deployment** - Full containerization with PostgreSQL/TimescaleDB  
✅ **Professional Welcome Page** - Laboratory branding with quick access grid  
✅ **Per-user reuse & exports** - HRV analysis artifacts and GPT-5.2 interpretation markdown persist per user in SQLite for cross-session reuse and user-scoped exports  
✅ **Baseline/Δ analytics (T0–T21)** - User Profile → HRV Measurement History includes a baseline/Δ table grouped by longitudinal timepoint labels (T0…T21)  
✅ **Cohort longitudinal comparisons (T0–T21)** - Export tab supports control vs intervention comparisons using within-subject Δ vs baseline per timepoint, with CSV + Markdown exports  
✅ **Persisted study groups + mixed-effects inference** - Export tab supports persisted Study IDs/groups (SQLite) and optional random-intercept mixed-effects modeling for Group × Time on Δ vs baseline  
✅ **Space-weather inference & ML (HRV ↔ Kp)** - Spearman + Pearson with CI95, BH-FDR, partials with weather covariates; optional ElasticNet + RandomForest + XGBoost + LightGBM on lagged Kp with permutation importances and SHAP interpretability; citation-backed context in UI/docs.

### Remaining Enhancements

#### Plot Governance (ECharts-first, publication-grade everywhere)
**Status:** In progress (Priority: CRITICAL)  
**Description:** Enforce the project plotting policy across *all* tabs and modules.

- Standardize chart styling (titles, axis labels with units, legends, tooltips, colorblind-safe palette).
- Require a short explanatory paragraph beneath every plot (what the user sees, axis/units, preprocessing).
- Add publication-grade plot exports across the app (SVG/PNG high-DPI/HTML + data/spec export, plus PDF via browser print workflow).
- Keep `requirements.txt`, `README.md`, `docs/Manual.md`, and `CHANGELOG.md` updated whenever plots/features change.

**Current implementation note:** Every Apache ECharts chart now includes an inline export toolbar for **PNG (high-DPI)**, **SVG (vector)**, **HTML**, and **spec JSON** exports, plus **Print/Save PDF** using your browser’s print dialog.

#### Technology watchlist (Human Performance Newsletter — 2025-12-18)
**Status:** Planned (Priority: High; research-first)  
**Description:** Candidate features inspired by `docs/HumanPerformance-Newsletter.md` that align with mission human-performance monitoring. These items are **not yet implemented** and will require peer-reviewed validation, dataset availability, and clear clinical/operational boundaries before activation.

- **Wearable biomarker ingestion (sweat / cortisol / lactate / electrolytes)**:
  - Add a generic **biomarkers** storage model (timestamped values + units + sensor/source + quality flags).
  - Add ECharts plots for biomarker trends and stress/strain overlays with HRV + sleep + workload (where available).
- **Muscle oxygen saturation (SmO₂) support (NIRS wearables)**:
  - Import + persist SmO₂ time series and session summaries.
  - Add threshold/zone helpers (e.g., plateau detection during incremental exercise) and rehab tracking comparisons (e.g., bilateral symmetry over time).
- **Respiratory rate estimation from PPG/HRV**:
  - Add a deterministic RR-estimation pipeline (bounded windowing, validation/quality checks) to support sleep and biofeedback workflows when direct respiration is unavailable.
- **Signal quality scoring (PPG/ECG readiness checks)**:
  - Add a standardized **signal quality index** for device imports (motion artifacts, clipping, dropout) so downstream metrics can warn or down-weight low-quality segments.
- **Early illness / anomaly detection from longitudinal HRV trends**:
  - Add optional per-user “baseline deviation alerts” for sustained RMSSD/SDNN changes (with transparent rules and conservative defaults).
- **Edge/offline-first processing & privacy**:
  - Strengthen local-only workflows (no cloud dependency) and make “on-device / on-prem” processing the default for sensitive deployments.

#### Fatigue Safety Management (ICAO FRMS + USAF doctrine) inside SAFTE tab
**Status:** Implemented baseline + planned FRMS v2 (Priority: CRITICAL; research-first)  
**Description:** The SAFTE/Fatigue module now includes a baseline FRMS-style dashboard (with rule-based “why it triggered” alerts) plus USAF crew-rest compliance checks. The next milestone is **FRMS v2**: mission-level aggregation across *all profiles* with escalation + audit trail.

- ✅ ICAO-aligned FRMS summary + risk matrix, designed for deterministic “why it triggered” traceability.
- ✅ USAF crew rest compliance checks (AFMAN 11-202V3) with clear “compliant / waiver required / not compliant” outputs.
- ✅ Exportable evidence: FRMS JSON export and plot export workflows.
- ✅ **FRMS v2 prototype (Crew Risk Board)**: Export tab aggregates FRMS metrics/classifications across selected active profiles and exports **crew board CSV/JSON** plus a **decision log JSON** (audit trail).
- 🔜 **FRMS v2 requisites to complete (end-to-end)**:
  - **Roster & mission window model**: explicit shift/EVA/task windows per crew member (start/end, timezone, role) with versioned assumptions.
  - **Crew-rest at scale**: per-crew crew-rest start, FDP start, planned sleep opportunity, and waiver rules (not a single global setting).
  - **Escalation rules**: configurable trigger thresholds (time ≤77%, WOCL overlap, noncompliant crew rest) with severity tiers and required mitigations/approvals.
  - **SPIs / trending**: track fatigue safety performance indicators over time (e.g., exposure hours ≤77%, WOCL duty overlap rate, alert rates, waiver rates), aligned with FRMS safety assurance practices.
  - **Hazard / occurrence reporting**: structured near-miss / incident logging linked to the predicted-risk context and crew state.
  - **Audit log persistence**: persist decision logs (inputs → classification → mitigations → outcome) in SQLite/Postgres with immutable records and export.
  - **Validation hooks**: optional PVT/vigilance testing, outcome labeling, and calibration hooks (e.g., SAFTE-R parameterization) to quantify predictive skill on the mission roster.
  - **Governance artifacts**: model card, data dictionary, and misuse constraints (what the tool can/can’t decide).

#### Per-user persistence across all mission modules
**Status:** Planned  
**Description:** Persist *computed outputs* (not only inputs/settings) for each user so results are instantly available across reruns and sessions.

- Circadian scenario run history (inputs + outputs + key markers like DLMO/CBT/ESRI)
- SAFTE run history (inputs + outputs + data-source provenance: wrist → clinical → Garmin Connect)
- Mission package export per subject (HRV + circadian + SAFTE + radiation + space-weather context + stored GPT report)

#### SAFTE-R performance prediction (per subject)
**Status:** Planned  
**Description:** Add an explicit SAFTE-R option (parameterization and UI) under each subject profile to predict performance with an audit trail of assumptions and inputs.

#### Mission-specific radiation dose modelling
**Status:** Planned  
**Description:** Tie dose computation to the mission being simulated (environment/shielding/EVA timeline) and persist dose model inputs/outputs per user and per mission scenario.

#### HRV protocol covariates (measurement accuracy)
**Status:** Planned  
**Description:** Capture and persist key acquisition covariates so comparisons and interpretation remain valid across users and sessions.

- Evidence base: Task Force (1996); Laborde, Mosley, & Thayer (2017); Quigley et al. (2024) — see References section for links.
- Posture/body position, time-of-day, breathing protocol / estimated respiratory rate
- Recent exercise, caffeine/nicotine/alcohol, acute illness/fever, medication changes
- Context tags (rest/sleep/exercise/recovery) to prevent mixing protocols in baselines

#### Advanced Nonlinear Dynamics
**Status:** Partially implemented  
**Description:** Additional nonlinear analysis methods for research applications.

- Multiscale entropy (MSE)
- Recurrence quantification analysis (RQA)
- Symbolic dynamics (word entropy)
- Correlation dimension
- Lyapunov exponents

**Current state:** DFA, SampEn, ApEn implemented; advanced methods pending.

#### Baroreflex Sensitivity from HRV-BPV
**Status:** Planned  
**Description:** Cross-spectral analysis of HRV and BPV for baroreflex assessment.

- Sequence method (spontaneous baroreflex)
- Spectral (α coefficient in LF band)
- Transfer function analysis
- Coherence thresholding

### Infrastructure Improvements

#### Database Backend
**Status:** Planned  
**Description:** Persistent storage for longitudinal data and multi-user support.

- PostgreSQL/SQLite backend
- User authentication
- Data encryption at rest
- Cloud sync options
- GDPR compliance tools

#### 14. API Development
**Status:** Planned  
**Description:** RESTful API for programmatic access and third-party integration.

- HRV computation endpoints
- Batch processing API
- Webhook notifications
- OAuth2 authentication
- Rate limiting and quotas

#### 15. Mobile Companion App
**Status:** Conceptual  
**Description:** Mobile app for data collection and quick HRV checks.

- Morning readiness protocol
- Quick 1-minute HRV measurement
- Push notifications for trends
- Sync with main platform
- Offline data collection

### Aerospace Medicine Specific

#### 16. G-Tolerance Assessment
**Status:** Planned  
**Description:** HRV-based tools for assessing G-tolerance and pilot fitness.

- Pre-flight autonomic screening
- G-LOC risk indicators
- Fatigue-HRV correlation for flight duty
- Anti-G straining maneuver analysis
- Hypoxia response patterns

**Relevance:** Dr. Malpica's aerospace medicine expertise.

#### 17. Altitude/Hypoxia Analysis
**Status:** Planned  
**Description:** HRV changes during altitude exposure and hypoxia.

- Acute mountain sickness prediction
- Acclimatization monitoring
- Hypoxic ventilatory response correlation
- SpO2-HRV relationship analysis
- High-altitude training optimization

#### 18. Spatial Disorientation Markers
**Status:** Research phase  
**Description:** Investigate HRV patterns associated with vestibular stress.

- Coriolis stimulation response
- Motion sickness susceptibility
- Vestibular-autonomic coupling
- Simulator sickness prediction

#### 19. Exploration Medical Capability (ExMC) Clinical Assessment  
**Status:** In Progress (Q4 2025)  
**Description:** Comprehensive clinical profile system aligned with NASA ExMC and EIMO frameworks for deep-space mission autonomy.

**Implemented:**
- Mission profile taxonomy (LEO through Mars Surface)
- EIMO autonomy level tracking (ground-supported → full autonomy)
- Radiation dose and space weather monitoring
- HRP risk category alignment (chronic/acute symptom catalogs)
- Countermeasure tracking (exercise, sleep, hydration, nutrition)
- Behavioral health flags (confinement stress, workload, team dynamics)
- Medical inventory and resupply logistics

**Planned Enhancements (Q1 2026):**
- AI-assisted clinical decision support (CDSS) per MEDEA concept (García-Gómez, 2020)
- Probabilistic risk assessment for medical events
- Integration with HRV longitudinal trends for fitness-for-duty checks
- Extended reality (XR) telepresence support annotations
- Pharmaceutical stability tracking and pharmacokinetics modeling
- Just-in-time training module cross-links

**Scientific References:**
- Levin DR, et al. (2023). Enabling Human Space Exploration Missions Through Progressively Earth Independent Medical Operations (EIMO). *IEEE Open J Eng Med Biol.* DOI: 10.1109/OJEMB.2023.3255513
- Anderson A, et al. (2025). Development of Progressively Earth-Independent Medical Operations to Enable NASA Exploration Missions. *Wilderness Environ Med.* DOI: 10.1177/10806032241310386
- García-Gómez JM. (2020). Basic principles and concept design of a real-time clinical decision support system for autonomous medical care on missions to Mars based on adaptive deep learning. arXiv:2010.07029
- Tran KA, et al. (2025). Managing Select Medical Emergencies During Long-Duration Space Missions. *Aerosp Med Hum Perform.* DOI: 10.3357/AMHP.6510.2025

### Research-Based Feature Ideas (2025-2026)

Based on recent scientific literature, the following features are under consideration:

#### 1. HRV-Based Mental Health Monitoring

**Scientific Basis:** Gu & Hu (2025) demonstrated 97% accuracy in predicting emotional states from HRV using Bi-LSTM networks.

**Planned Features:**
- Real-time emotional state classification (neutral, anxious, depressed)
- Long-term mood trajectory tracking
- Integration with digital phenotyping data
- Intervention effectiveness monitoring

**Reference:** Gu X, Hu X. (2025). Research on mood monitoring and intervention for anxiety disorder patients based on deep learning wearable devices. *Technol Health Care*. [PMID: 40105160]

#### 2. Transcutaneous Vagus Nerve Stimulation (taVNS) Response Prediction

**Scientific Basis:** Li et al. (2025) showed that autonomic response to taVNS predicts changes in consciousness, with 86% classification accuracy using SVM on HRV features.

**Planned Features:**
- Pre-taVNS HRV baseline assessment
- Response prediction scoring
- Optimal stimulation parameter recommendations
- Treatment outcome tracking

**Reference:** Li Y, et al. (2025). The autonomic response following taVNS predicts changes in level of consciousness in DoC patients. *Sci Rep, 15*(1). [PMID: 40025051]

#### 3. Circadian-HRV Coupled Analysis

**Scientific Basis:** Emerging research shows bidirectional coupling between circadian rhythms and autonomic function.

**Planned Features:**
- Joint circadian-HRV state estimation
- Chrono-autonomic profile generation
- Light exposure optimization based on HRV response
- Personalized circadian intervention timing

#### 4. Deep Learning for Continuous HRV Prediction

**Scientific Basis:** Recent advances in transformer architectures for physiological time series.

**Planned Features:**
- Predictive HRV modeling (1-24h horizon)
- Anomaly detection with uncertainty quantification
- Transfer learning from large HRV databases
- Federated learning for privacy-preserving model updates

#### 5. Aerospace-Specific Fatigue Biomarkers

**Scientific Basis:** Integration of HRV, circadian models, and cognitive performance testing for aviation applications.

**Planned Features:**
- G-LOC risk prediction from pre-flight HRV
- Hypoxia susceptibility assessment
- Fatigue-related accident risk scoring
- Crew scheduling optimization

#### 6. Baroreflex-Circadian Interaction Analysis

**Scientific Basis:** Baroreflex sensitivity shows circadian variation that may be disrupted in cardiovascular disease.

**Planned Features:**
- Time-of-day baroreflex assessment
- HRV-BPV coherence analysis by circadian phase
- Nocturnal blood pressure dipping prediction
- Cardiovascular risk stratification

### How to Contribute

If you're interested in contributing to any of these developments:

1. **Code contributions**: Fork the repository and submit pull requests
2. **Testing**: Help validate new features with your data
3. **Documentation**: Improve user guides and scientific references
4. **Feature requests**: Open GitHub issues with detailed use cases
5. **Research collaboration**: Contact Dr. Malpica for academic partnerships

### Development Timeline

| Feature | Target Quarter | Status |
|---------|----------------|--------|
| ECG R-peak detection | Q4 2025 | ✅ Completed |
| Multi-modal fusion | Q4 2025 | ✅ Completed |
| Long-term trending | Q4 2025 | ✅ Completed |
| Exercise HRV | Q4 2025 | ✅ Completed |
| ML predictions | Q4 2025 | ✅ Completed |
| Real-time BLE | Q4 2025 | ✅ Completed |
| Population norms | Q4 2025 | ✅ Completed |
| BPV integration | Q4 2025 | ✅ Completed |
| Circadian analysis | Q4 2025 | ✅ Completed |
| User profiles | Q4 2025 | ✅ Completed |
| Docker deployment | Q4 2025 | ✅ Completed |
| ExMC Clinical Assessment | Q4 2025 | 🔄 In Progress |
| Ventilatory Threshold (DFA-α1) | Q1 2026 | ✅ Completed |
| Trajectory Risk / Allostatic Load | Q1 2026 | ✅ Completed |
| Baroreflex sensitivity | Q1 2026 | Planned |
| Advanced nonlinear | Q1 2026 | Planned |
| ExMC CDSS / AI support | Q1 2026 | Planned |
| Mobile app | Q4 2026 | Conceptual |

---

## Physiological Trajectory Risk Module (Allostatic Load Alarm)

### Overview

The Trajectory Risk Module adds a **longitudinal layer** to the readiness model that the single-day snapshot misses. An operator can look "fine" today — adequate sleep, normal resting HRV — but be on a multi-day downward trajectory: lnRMSSD declining 5% per day, resting HR creeping upward, sleep quality eroding. The daily readiness score might still say "GO" because each individual day is within population norms. The trajectory module catches this by computing EWMA-smoothed trends and Smallest Worthwhile Change (SWC) exceedance across multiple metrics simultaneously.

### Scientific Basis

This module implements the **allostatic load** concept (McEwen, 1998): cumulative physiological "wear and tear" predicts functional decline independently of any single acute measurement. Key evidence:

- **EWMA-based HRV monitoring** detects overreaching before performance decline (Plews et al., 2013; Bellenger et al., 2016)
- **SWC = 0.5 × CV** of lnRMSSD identifies meaningful vs. noise changes (Buchheit, 2014)
- **Multi-metric trajectory analysis** outperforms single-metric snapshot for readiness (Moreno-Gutiérrez et al., 2021: 73% accuracy combining HRV + wellness in soccer)
- **Sleep-debt potentiation**: declining sleep quality amplifies HRV decline non-linearly (Tobaldini et al., 2017)

### How It Works

**Metrics tracked (4 parallel streams):**

| Metric | Source | Higher = Better | Purpose |
|---|---|---|---|
| lnRMSSD | Morning HRV | Yes | Vagal autonomic reserve |
| Resting HR | Wearable | No | Sympathetic activation |
| Sleep Quality | Wearable/self-report | Yes | Recovery adequacy |
| DFA-α1 (rest) | HRV nonlinear | Yes | Cardiac complexity |

**Algorithm:**
1. **EWMA smoothing** (span=7, α≈0.25) applied to each daily metric series
2. **Baseline computation** from first 7 days of data (mean, SD, CV)
3. **SWC exceedance test**: |EWMA_current - EWMA_baseline| > 0.5 × baseline_SD
4. **Z-score computation**: deviation from baseline in standard deviation units
5. **PSI (Physiological Strain Index)**: composite 0-100 using sigmoid-mapped z-scores with SWC amplification
6. **Risk classification**: 5-tier system based on PSI + count of declining metrics + SWC exceedances
7. **Compound risk detection**: simultaneous sleep + HRV decline triggers 1.3× penalty amplifier

### Risk Classification

| Risk Level | PSI Range | Description | Action |
|---|---|---|---|
| **IMPROVING** | <25, no decline | Positive adaptation trajectory | Continue current program |
| **STABLE** | <50, minor fluctuation | Normal day-to-day variation | Monitor normally |
| **WATCH** | ≥50 or 1 SWC exceeded | One metric deviating meaningfully | Ensure adequate recovery |
| **ELEVATED** | ≥70 or 2+ SWC exceeded | Multi-metric degradation | Reduce load 24-48h |
| **CRITICAL** | ≥85 or 3+ SWC exceeded | Severe sustained decline | Immediate workload reduction; PVT validation |

### Integration with Readiness Model

The trajectory module outputs a **bounded modifier (±8 points)** that fuses into the operational readiness score:

- **IMPROVING**: +2 to +5 bonus (positive adaptation)
- **STABLE**: 0 (neutral)
- **WATCH**: -2 to -4 penalty
- **ELEVATED**: -4 to -6 penalty
- **CRITICAL**: -6 to -8 penalty

When sleep + HRV decline simultaneously (compound risk), the penalty is amplified by 1.3×, capped at -8 points. This models the non-linear Fatigue-Hypoxia feedback loop identified in the IRM literature review.

### Minimum Data Requirements

- **5 days** minimum for any trajectory assessment
- **7 days** for full baseline establishment
- **14+ days** for highest confidence assessments
- Data confidence degrades proportionally below 14 days

### References

- Bellenger, C.R., et al. (2016). Monitoring athletic training status through autonomic HRV measures. *Sports Med*, 46, 1461-1486. doi: 10.1007/s40279-016-0487-7
- Buchheit, M. (2014). Monitoring training status with HR measures. *Front Physiol*, 5, 73. doi: 10.3389/fphys.2014.00073
- McEwen, B.S. (1998). Protective and damaging effects of stress mediators. *NEJM*, 338, 171-179. doi: 10.1056/NEJM199801153380307
- Plews, D.J., et al. (2013). Training adaptation and HRV in elite athletes. *J Strength Cond Res*, 27(12), 3159-3165.
- Tobaldini, E., et al. (2017). Sleep deprivation and autonomic nervous system. *Sleep Med Rev*, 35, 62-73. doi: 10.1016/j.smrv.2016.08.003
- Juster, R.P., et al. (2010). Allostatic load biomarkers. *Neurosci Biobehav Rev*, 35, 2-16. doi: 10.1016/j.neubiorev.2009.10.002

---

## Environmental Monitoring, METAR Weather, and Extreme Environment Calculators

### ICE Station Environmental Monitor

The dashboard includes a simulated Isolated Confined Environment (ICE) research station monitoring panel with 8 environmental sensors critical for habitability assessment in Antarctic and space analog missions.

**Key Sensors and Thresholds:**

| Sensor | Normal Range | Danger Threshold | Health Impact |
|---|---|---|---|
| Temperature | 18-24 C | <16 or >28 C | Cognitive performance, thermal comfort |
| Relative Humidity | 30-60% | <20 or >70% | Respiratory health, condensation |
| CO2 | 400-1000 ppm | >1500 ppm | Cognitive impairment at >1000 ppm (Satish et al., 2012) |
| Barometric Pressure | 980-1030 hPa | <950 hPa | Altitude-equivalent headache |
| PM2.5 | 0-25 ug/m3 | >50 ug/m3 | Respiratory irritation |
| Noise | 30-50 dB | >70 dB | Sleep disruption, stress response |
| Light Level | 300-500 lux | <100 lux | Circadian disruption in polar winter |
| O2 Level | 20.5-21.0% | <19.5% | Hypoxia risk in sealed habitats |

### METAR Aviation Weather Dashboard

Real-time decoded METAR data from any ICAO station worldwide using the FAA AviationWeather.gov API (free, no API key required). Includes wind compass gauge, decoded fields, flight category (VFR/MVFR/IFR/LIFR), and raw METAR text.

Default stations: SKBO (Bogota), SAWE (Marambio, Antarctica), SCRM (King George Island).

### Wind Chill and Frostbite Calculator

Implements the NWS 2001 formula (Osczevski & Bluestein, 2005):

`WC = 13.12 + 0.6215*Ta - 11.37*V^0.16 + 0.3965*Ta*V^0.16`

Where Ta = air temperature (C), V = wind speed at 10m (km/h). Frostbite time estimated from NWS lookup tables.

### WBGT Heat Stress Calculator

Implements the ISO 7243:2017 simplified estimation (Steadman, 1979):

`WBGT = 0.567*Ta + 0.393*e + 3.94`

Where e = water vapor pressure (hPa) from temperature and humidity. Includes NIOSH-aligned work/rest guidance.

### Jet Lag Circadian Performance Model

Based on Waterhouse et al. (2007) and Arendt (2009):

- Eastward resynchronization rate: ~0.67 h/day (phase advance, harder)
- Westward resynchronization rate: ~1.0 h/day (phase delay, easier)
- Performance follows exponential recovery: `factor = 1.0 - penalty * exp(-day / tau)`
- Readiness modifier bounded to +/-6 points
- Interactive recovery curve chart in the crew performance modal

**References:**
- Osczevski, R., & Bluestein, M. (2005). BAMS, 86(10), 1453-1458.
- ISO 7243:2017. WBGT heat stress assessment.
- Steadman, R.G. (1979). J Appl Meteor, 18, 861-873.
- Satish, U., et al. (2012). Environ Health Perspect, 120(12), 1671-1677. DOI: 10.1289/ehp.1104789
- Waterhouse, J., et al. (2007). Lancet, 369, 1117-1129. PMID: 17398311
- Arendt, J. (2009). Sleep Med Rev, 13(4), 249-256. PMID: 19153053
- Burgess, H.J., et al. (2003). J Biol Rhythms, 18(4), 318-328. PMID: 12932084

---

## Physiological SMS Risk Assessment

### Overview

The Physiological SMS Risk Assessment module integrates baseline blood pressure and basal body temperature into the operational readiness model as bounded modifiers, and provides Safety Management System (SMS)-style risk matrices for two critical activity types: Extravehicular Activity (EVA) and high-performance military flight.

This module addresses the need for a comprehensive, multi-vital readiness assessment that goes beyond HRV alone. Resting blood pressure provides complementary autonomic information under sympathetic control (Porta et al., 2012), while basal body temperature reflects circadian phase, infection status, and thermoregulatory health (Kim & Lee, 2017; Zhang et al., 2025).

### Blood Pressure Readiness Modifier

Resting blood pressure is classified per ACC/AHA 2017 Hypertension Clinical Practice Guidelines. The modifier is bounded to +/-4 points to prevent overpowering the base SAFTE + HRV readiness model.

| SBP / DBP Range | Classification | Modifier | Rationale |
|---|---|---|---|
| SBP 90-120, DBP 60-80 | Optimal | +2 | ACC/AHA optimal range; positive cardiovascular indicator |
| SBP 120-129, DBP < 80 | Elevated | 0 | Neutral; within tolerable range |
| SBP 130-139 or DBP 80-89 | Stage 1 HTN | -2 | Increased cardiovascular load |
| SBP >= 140 or DBP >= 90 | Stage 2 HTN | -4 | EVA/flight disqualifying risk factor |
| SBP < 90 or DBP < 60 | Hypotension | -3 | Orthostatic/syncope and G-LOC risk |

### Temperature Readiness Modifier

Basal oral body temperature is classified against standard clinical ranges. The modifier is bounded to +/-3 points.

| Oral Temperature | Classification | Modifier | Rationale |
|---|---|---|---|
| 36.1 - 37.2 C | Normal | 0 | Euthermia, within circadian variation |
| 37.3 - 37.7 C | Low-grade elevation | -1 | Possible early illness or post-exercise |
| 37.8 - 38.2 C | Mild fever | -2 | Active inflammation; reduced tolerance |
| > 38.3 C | Fever | -3 | Disqualifying for EVA/flight |
| 35.0 - 36.0 C | Mild hypothermia | -1 | Cold exposure or hypothyroidism concern |
| < 35.0 C | Hypothermia | -3 | Medical emergency |

### EVA Readiness SMS Matrix (ICAO Doc 9859)

A 5x5 risk matrix adapted from the ICAO Safety Management Manual for spacewalk operations:

- **Severity** (5 levels): Maps from the fused readiness score (0-100)
- **Likelihood** (5 levels): Maps from physiological flags (BP disqualifiers, temperature disqualifiers, PSI score, trajectory risk)
- **Risk levels**: Acceptable, Tolerable, Undesirable, Intolerable
- **Hard disqualifiers**: Fever > 37.8 C, SBP > 160, PSI > 85 — any one forces Intolerable

### Military Flight SMS Matrix (MIL-STD-882E)

A 4x5 risk matrix per DoD Standard Practice for System Safety:

- **Severity** (4 levels): Negligible, Marginal, Critical, Catastrophic (per MIL-STD-882E Table I)
- **Likelihood** (5 levels): Improbable, Remote, Occasional, Probable, Frequent (per Table II)
- **Risk levels**: Low, Medium, Serious, High (per Table III)
- **G-LOC risk flag**: Triggered by hypotension + low RMSSD or resting tachycardia
- **Crew rest integration**: USAF AFMAN 11-202V3 compliance status

### API Endpoints

- `POST /api/research/readiness/{user_id}/vitals` — Submit BP + temperature, get enhanced readiness with dual SMS
- `GET /api/research/sms/eva` — EVA SMS risk classification with heatmap matrix data
- `GET /api/research/sms/flight` — Military Flight SMS classification with heatmap matrix data

### Frontend Pages

- **Research**: `/research/physiological-readiness` — Vitals form, modifier waterfall chart, dual SMS heatmaps, scientific citations
- **Operational**: `/scheduling/readiness` — Go/No-Go decision panels, large readiness banner, compact SMS matrices

### References

- Porta, A., et al. (2012). Short-term complexity indexes of HP and SAP variabilities provide complementary information. *J Appl Physiol, 113*(12), 1810-1820. PMID: 23104699
- Lucini, D., Solaro, N., & Pagani, M. (2014). Autonomic indices from cardiovascular variability help identify hypertension. *J Hypertens, 32*(2), 363-373. PMID: 24232167
- Zhang, R., et al. (2020). Analysis of autonomic nervous pattern in hypertension based on short-term HRV. *Biomed Tech, 65*(4), 437-447. PMID: 32769220
- Crowe, M., et al. (2025). Comparison of rectal and gastrointestinal core temperatures during heat tolerance testing. *Medicina, 61*(6), 1111. DOI: 10.3390/medicina61061111
- Kim, S., & Lee, J.-Y. (2017). Prediction of body core temperature with HRV. Semantic Scholar: 6f60ddec.
- Zhang, Z., et al. (2025). Research of physiological monitoring models in the military domain. DOI: 10.1109/ICCNEA66167.2025.11211893
- Goutham, D., & Saravanasankar, S. (2025). AI-driven fatigue prediction using wearable sensor data and gradient-boosted ML models. DOI: 10.1109/ICRISET64803.2025.11254790
- ICAO. (2018). *Safety Management Manual* (Doc 9859, 4th ed.).
- US DoD. (2012). *MIL-STD-882E: Standard Practice for System Safety*.

---

## Ventilatory Threshold Estimation (Experimental)

### Overview

The Ventilatory Threshold (VT) Estimation module provides non-invasive detection of aerobic (VT1) and anaerobic (VT2) thresholds using heart rate variability analysis. This eliminates the need for laboratory-based cardiopulmonary exercise testing (CPET) with gas exchange analysis — a significant advancement for field testing, remote environments, and aerospace operations where laboratory equipment is unavailable.

> **Full scientific report:** For the complete literature review, Python implementation framework, and validation evidence, see [HRV_Ventilatory_Threshold_Comprehensive_Scientific_Report.md](HRV_Ventilatory_Threshold_Comprehensive_Scientific_Report.md).

### Scientific Background

Accurate determination of exercise intensity thresholds is fundamental to exercise prescription, performance optimization, and physiological monitoring in aerospace medicine (Rogers et al., 2021). Traditional CPET requires specialized laboratory equipment, trained personnel, controlled environments, and significant resources — constraints that preclude widespread application in field settings, analog missions, military operations, and continuous monitoring scenarios.

**Autonomic Regulation During Exercise**

Exercise intensity modulates autonomic nervous system (ANS) balance with measurable effects on heart rate variability patterns (Aubert et al., 2003; Shaffer & Ginsberg, 2017):

1. **Below VT1**: Vagal dominance with preserved fractal correlation
2. **VT1 region**: Progressive vagal withdrawal
3. **VT1-VT2**: Mixed autonomic regulation with sympathetic enhancement
4. **Above VT2**: Sympathetic dominance with loss of fractal organization
5. **Maximal intensity**: Near-complete vagal withdrawal, random HR patterns

**Detrended Fluctuation Analysis (DFA-α1)** quantifies fractal correlation properties of RR interval time series (Peng et al., 1995). The short-term scaling exponent (α1, computed over 4-16 beats) reflects short-range correlations in RR intervals and transitions predictably during exercise:

| DFA-α1 Value | Signal Character | Interpretation | Autonomic State |
|---|---|---|---|
| ~1.5 | Brownian motion | Extremely organized | — |
| ~1.0 | 1/f noise | Correlated fractal pattern | Parasympathetic dominance (rest/low intensity) |
| ~0.75 | Transitional | **VT1 (Aerobic Threshold)** | Progressive vagal withdrawal |
| ~0.50 | Random walk | **VT2 (Anaerobic Threshold)** | Sympathetic dominance |
| <0.50 | Anti-correlated | Near-maximal/maximal intensity | Near-complete vagal withdrawal |

### Multi-Parameter Algorithm

The implementation uses a multi-parameter approach inspired by the Kubios VT-algorithm architecture (Eronen et al., 2024). Rather than relying on DFA-α1 alone, it integrates three complementary physiological signals:

- **DFA-α1 (60% weight)**: Primary fractal correlation metric computed in 120-second sliding windows with 5-second steps, following Kubios standard methodology
- **Heart Rate Reserve (30% weight)**: Normalized HR position between resting and age-predicted maximum, tracking the intensity continuum
- **Respiratory Frequency (10% weight)**: Ventilatory modulation extracted from the HF spectral band (0.15-0.40 Hz) via respiratory sinus arrhythmia analysis

**Algorithm Steps:**
1. RR interval extraction and artifact correction (±20% median threshold)
2. Time-varying DFA-α1 computation (120s window, 5s step)
3. Heart rate reserve normalization
4. Respiratory frequency extraction from HRV spectral analysis
5. Multi-parameter integration with weighted combination
6. Threshold identification and confidence scoring

### Validation Evidence

**Primary Validation Study — Eronen et al. (2024, n=64):**

Recreationally active participants (18-65 years) underwent incremental CPET on a cycle ergometer with simultaneous ECG recording and gas exchange analysis.

| Metric | DFA-α1 Alone | Multi-Parameter (VT-Algorithm) | Improvement |
|---|---|---|---|
| VT1 VO₂ correlation | r = 0.67 | r = 0.81 | +20.9% |
| VT1 HR bias | 10 ± 18 bpm | 1 ± 11 bpm | 90% bias reduction |
| VT1 HR standard error | ±18 bpm | ±11 bpm | 39% SE reduction |
| VT2 HR correlation | r = 0.82 | r = 0.82 | Equal |
| VT2 VO₂ correlation | — | r = 0.93 | — |
| VT2 HR standard error | <7 bpm | <7 bpm | Clinically acceptable |

**Supporting Evidence — Gronwald et al. (2020, Systematic Review):**

- 16 studies analyzed (n=327 total participants)
- DFA-α1 threshold of 0.75 consistently identified VT1/LT1
- Correlation with lactate threshold: r = 0.61-0.81
- Test-retest reliability: CV <6%

**Supporting Evidence — Rogers et al. (2021, Elite Cyclists):**

- n=20 elite cyclists
- DFA-α1 at 0.75 correlated with LT1: r = 0.89, p<0.001
- Heart rate at DFA-α1=0.75 within ±5 bpm of lactate-based LT1 in 85% of cases

**Sex-Specific Analysis:**

- Women showed DFA-α1 thresholds at 0.75 (VT1) and 0.50 (VT2) with r=0.81 and r=0.86 respectively
- No significant sex differences in DFA-α1 threshold values
- Similar reliability across sexes (CV <6%)

### Methodological Factors Affecting Accuracy

| Factor | Effect on Accuracy | Recommendation |
|---|---|---|
| Artifact rate <5% | Excellent agreement | Use automated artifact correction |
| Artifact rate 5-10% | Good agreement | Manual inspection recommended |
| Artifact rate >10% | Poor agreement | Consider test invalid |
| Stage duration ≥2 min | Optimal | Allows autonomic stabilization |
| Stage duration <2 min | Reduced accuracy | May miss threshold transition |
| Increment size 10-25W | Optimal | Appropriate resolution |
| Trained athletes | Higher correlation | More stable autonomic patterns |
| Sedentary individuals | Variable results | Individual calibration beneficial |
| Laboratory (controlled) | Best accuracy | Reference standard |
| Field (variable) | Reduced accuracy | Increased artifact rate |

### Comparison with Alternative Threshold Detection Methods

| Method | Accuracy | Cost | Portability | Real-time | Invasiveness |
|---|---|---|---|---|---|
| **CPET (Gas Exchange)** | Gold standard | Very High | No | Yes | Moderate (mouthpiece) |
| **Blood Lactate** | Excellent | Moderate | Limited | No | High (blood samples) |
| **HRV (DFA-α1 only)** | Good | Low | Yes | Yes | None |
| **HRV (Multi-parameter)** | Excellent | Low | Yes | Yes | None |
| **Talk Test** | Fair | None | Yes | Yes | None |
| **RPE-based** | Fair-Good | None | Yes | Yes | None |

### Features in the Application

1. **DFA-α1 Time Series Visualization**: Publication-quality chart showing DFA-α1 evolution during exercise with intensity zone shading (green=Zone 1/aerobic, orange=Zone 2/threshold, red=Zone 3/high intensity)
2. **Heart Rate Progression**: Instantaneous and windowed-mean HR with VT1/VT2 markers
3. **DFA-α1 vs HR Scatter**: Demonstrates the inverse relationship between cardiac complexity and exercise intensity
4. **Multi-Parameter Integrated Score**: Shows the weighted combination used for threshold detection
5. **Exercise Intensity Zones**: Personalized Zone 1, Zone 2, Zone 3 with HR targets derived from detected thresholds
6. **Signal Quality Assessment**: Artifact rate, DFA range verification, monotonic decrease check
7. **Confidence Scoring**: Each detected threshold includes a confidence metric based on transition smoothness and monotonicity
8. **Demo Mode**: Synthetic 20-minute graded exercise test data for exploring the module without real recordings

### Integration with Readiness Model

The VT-derived fitness score is integrated into the operational readiness model as a bounded modifier (±5 points maximum):

- **Resting DFA-α1 ~1.0**: Healthy fractal dynamics — positive readiness modifier
- **VT1 at high %HR reserve**: Excellent aerobic base — positive modifier
- **Low resting DFA-α1 (<0.65)**: Possible overtraining or autonomic dysfunction — negative modifier
- **VT2 correlation with operational capacity**: Higher anaerobic threshold indicates greater reserve for high-stress operations

### Aerospace-Specific Applications

This module has particular relevance to aerospace medicine and operational environments:

- **Microgravity countermeasure exercise**: Optimize exercise prescriptions aboard ISS without metabolic carts
- **Analog mission monitoring**: Field-deployable threshold detection for Mars analog and Antarctic expeditions
- **Military operations**: Fitness assessment without laboratory infrastructure
- **Special operations selection**: Continuous autonomic monitoring during graded physical tests
- **Spaceflight deconditioning tracking**: Monitor VT changes during long-duration missions to detect cardiovascular deconditioning
- **Spacesuit exercise testing**: Adaptations for constrained exercise protocols

### Future Directions

**Research Priorities:**

1. **Larger validation studies** across diverse populations (age ranges, fitness levels, clinical populations, exercise modalities)
2. **Machine learning integration**: Deep learning for pattern recognition in HRV signatures, individual calibration algorithms, and automated artifact detection
3. **Real-time wearable implementation**: Embedded algorithms for live threshold estimation during exercise with adaptive training prescription
4. **Longitudinal studies**: Training-induced VT changes, seasonal variation, aging effects, and disease progression monitoring
5. **Multi-modal sensor fusion**: Integration with accelerometry, skin temperature, and electrodermal activity for enhanced accuracy

### Quality Control Checklist

**Pre-Test:**
- [ ] Participant instructions provided (no caffeine 4h prior, adequate rest)
- [ ] Equipment calibrated (ergometer, HR monitor electrode contact)
- [ ] Baseline measurements recorded (resting HR, blood pressure)

**During Test:**
- [ ] ECG quality monitored in real-time
- [ ] Work rate progression adheres to protocol (2-3 min stages, 10-25W increments)
- [ ] Total test duration sufficient (>8-12 minutes)

**Post-Test:**
- [ ] Artifact rate <5%
- [ ] Signal quality score >85%
- [ ] Clear DFA-α1 decrease observed
- [ ] Thresholds physiologically plausible (VT1 < VT2)
- [ ] Confidence scores >60%

### Limitations

- **Experimental**: Clinical decisions should always be validated against gold-standard CPET when available
- **Signal quality**: Requires >85% quality, <5% artifact rate for reliable results
- **Protocol**: Best results with incremental exercise tests (2-3 min stages, 10-25W increments on ergometer)
- **Individual variation**: ~10-20% of individuals show atypical DFA-α1 patterns (high baseline sympathetic tone, medications, caffeine)
- **Exercise modality**: Validation primarily in cycling; running shows higher variability due to motion artifacts
- **Proprietary algorithms**: The exact Kubios VT-algorithm weights are not publicly available; our implementation follows the published architecture

### API Endpoints

- `GET /api/research/vt/demo` — Demo analysis with synthetic 20-min graded exercise data
- `POST /api/research/vt/analyze` — Upload RR intervals for VT detection

### References

- Eronen, T., Tikkanen, J., Junttila, J., Kaikkonen, K., Kentta, T. V., Huikuri, H. V., et al. (2024). Heart rate variability based ventilatory threshold estimation — Validation of a commercially available algorithm. *medRxiv*. [DOI: 10.1101/2024.08.14.24311967](https://doi.org/10.1101/2024.08.14.24311967)
- Gronwald, T., Rogers, B., & Hoos, O. (2020). Correlation properties of heart rate variability during endurance exercise: A systematic review. *Annals of Noninvasive Electrocardiology, 25*(1), e12697. [DOI: 10.1111/anec.12697](https://doi.org/10.1111/anec.12697)
- Rogers, B., Giles, D., Draper, N., Hoos, O., & Gronwald, T. (2021). A new detection method defining the aerobic threshold for endurance exercise and training prescription based on fractal correlation properties of heart rate variability. *Frontiers in Physiology, 11*, 596567. [DOI: 10.3389/fphys.2020.596567](https://doi.org/10.3389/fphys.2020.596567)
- Rogers, B., Giles, D., Draper, N., Mourot, L., & Gronwald, T. (2021). Influence of artefact correction and recording device type on the practical application of a non-linear heart rate variability biomarker for aerobic threshold determination. *Sensors, 21*(3), 821. [DOI: 10.3390/s21030821](https://doi.org/10.3390/s21030821)
- Gronwald, T., Hoos, O., & Hottenrott, K. (2019). Effects of a short-term cycling interval session and active recovery on non-linear dynamics of cardiac autonomic activity in endurance trained cyclists. *Journal of Clinical Medicine, 8*(2), 194. [DOI: 10.3390/jcm8020194](https://doi.org/10.3390/jcm8020194)
- Peng, C. K., Havlin, S., Stanley, H. E., & Goldberger, A. L. (1995). Quantification of scaling exponents and crossover phenomena in nonstationary heartbeat time series. *Chaos, 5*(1), 82-87. [DOI: 10.1063/1.166141](https://doi.org/10.1063/1.166141)
- Poole, D. C., Rossiter, H. B., Brooks, G. A., & Gladden, L. B. (2021). The anaerobic threshold: 50+ years of controversy. *Journal of Physiology, 599*(3), 737-767. [DOI: 10.1113/JP279963](https://doi.org/10.1113/JP279963)
- Aubert, A. E., Seps, B., & Beckers, F. (2003). Heart rate variability in athletes. *Sports Medicine, 33*(12), 889-919. [DOI: 10.2165/00007256-200333120-00003](https://doi.org/10.2165/00007256-200333120-00003)
- Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability metrics and norms. *Frontiers in Public Health, 5*, 258. [DOI: 10.3389/fpubh.2017.00258](https://doi.org/10.3389/fpubh.2017.00258)
- Seiler, S., Haugen, O., & Kuffel, E. (2007). Autonomic recovery after exercise in trained athletes: Intensity and duration effects. *Medicine & Science in Sports & Exercise, 39*(8), 1366-1373. [DOI: 10.1249/mss.0b013e318060f17d](https://doi.org/10.1249/mss.0b013e318060f17d)
- Buchheit, M., & Laursen, P. B. (2013). High-intensity interval training, solutions to the programming puzzle: Part I: Cardiopulmonary emphasis. *Sports Medicine, 43*(5), 313-338. [DOI: 10.1007/s40279-013-0029-x](https://doi.org/10.1007/s40279-013-0029-x)
- Charles, J. B., & Lathers, C. M. (1994). Cardiovascular adaptation to spaceflight. *Journal of Clinical Pharmacology, 34*(5), 394-405. [DOI: 10.1002/j.1552-4604.1994.tb04977.x](https://doi.org/10.1002/j.1552-4604.1994.tb04977.x)
- Baevsky, R. M., Funtova, I. I., Diedrich, A., Pashchenko, A. V., Tank, J., & Jordan, J. (2007). Autonomic function testing aboard the International Space Station. *Clinical Autonomic Research, 17*(3), 131-136. [DOI: 10.1007/s10286-007-0418-y](https://doi.org/10.1007/s10286-007-0418-y)
- Convertino, V. A. (2002). Planning strategies for development of effective exercise and nutrition countermeasures for long-duration space flight. *Nutrition, 18*(10), 880-888. [DOI: 10.1016/s0899-9007(02)00910-5](https://doi.org/10.1016/s0899-9007(02)00910-5)
- Makowski, D., Pham, T., Lau, Z. J., Brammer, J. C., Lespinasse, F., Pham, H., et al. (2021). NeuroKit2: A Python toolbox for neurophysiological signal processing. *Behavior Research Methods, 53*(4), 1689-1696. [DOI: 10.3758/s13428-020-01516-y](https://doi.org/10.3758/s13428-020-01516-y)
- Shaffer F, Ginsberg JP. (2017). An Overview of HRV Metrics and Norms. *Front Public Health*, 5:258.

---

*Last updated: February 5, 2026*
