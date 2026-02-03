# Mission Control - Flight Surgeon

## Author

**Dr Diego Malpica MD**
*Aerospace Medicine Specialist*
National University of Colombia
Physiology Instructor, Colombian Aerospace Force
Contributing to **AsterPhysiology** Research Initiative

[![GitHub](https://img.shields.io/badge/GitHub-strikerdlm%2FHRV-blue?logo=github)](https://github.com/strikerdlm/HRV)
[![Version](https://img.shields.io/badge/Version-1.9.16-green)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![CUDA](https://img.shields.io/badge/CUDA-Optional-76B900?logo=nvidia)](https://developer.nvidia.com/cuda-toolkit)
[![i18n](https://img.shields.io/badge/i18n-EN%20%7C%20ES-blue)](app/i18n.py)
[![Last Updated](https://img.shields.io/badge/Updated-2026--02--02-blue)](CHANGELOG.md)

---

Mission Control - Flight Surgeon is a comprehensive, research-grade Heart Rate Variability (HRV) operations console that blends circadian simulation, blood-pressure variability, population norms, and real-time space weather intelligence from NOAA SWPC and NASA DONKI. It is built for clinicians, researchers, and aerospace medicine specialists who need transparent, reproducible physiological metrics with publication-ready exports.

**NEW in v1.9.16**: **Comprehensive Crew Scheduling & Human Performance** — Full operational app implementation in TypeScript/Next.js frontend with Status Dashboard (IHPI gauges, alerts), Schedule management (activity cards, filters), Crew Management (full CRUD with comprehensive admin profile editor), and Performance metrics (Go/No-Go indicators). Includes 5-section tabbed profile editor covering identity, operational, biometrics, lifestyle, and medical fields.

**NEW in v1.9.15**: **Research Frontend Expansion** — Added 11 dedicated TypeScript/Next.js research pages (Time Series, Frequency, Nonlinear, HRF, Windowed, Readiness, ANS Tests, Fatigue, Circadian, Population Norms, Timeline, Export, Science) with publication-grade ECharts, mock-data fallbacks, and reorganized sidebar navigation.

**NEW in v1.9.14**: **TypeScript/Next.js Frontend** — Modern frontend under `frontend/` with FastAPI backend under `api/`. Features include crew dashboard, space weather gauges, HRV analysis with Poincaré plots, solar-HRV correlations, and Garmin integration. Run both with `.\start-frontend.ps1` (frontend port 3100, API port 8180).

**NEW in v1.9.10**: **Space Weather Data Science (Single User)** — New streamlined research app (`app/space_weather_ds_app.py`) using the latest Streamlit (1.53.1) with a separate requirements file (`requirements_streamlit_latest.txt`) and performance profiles (Lightweight default, RTX 5070 GPU mode).

**NEW in v1.9.9**: **Guest Results Visibility** — Sidebar-driven navigation now activates the selected view only when it changes and bypasses manual tab gating so guest HRV and Space Analytics outputs render immediately.

**NEW in v1.9.8**: **Sidebar-Only Navigation + Guest Analysis** — The sidebar selector now drives the active view (tabs hidden), stable navigation is always on in Research, and HRV + Space Weather analyses run in guest mode without selecting a profile.

**NEW in v1.9.7**: **Research Stability + NASA Autofill Sync** — Removed experimental tab persistence to prevent rerun loops, and NASA Nutrition sleep inputs now share the Profile Tools values so Garmin autofill updates the visible fields immediately.

**NEW in v1.9.6**: **Research Stability Controls** — Stable navigation mode renders one section at a time via a sidebar selector, a rerun storm guard auto-disables heavy plots during rapid reruns, and time-series artifacts/deviation timelines now downsample to performance caps for smooth interaction.

**NEW in v1.9.1**: **Enhanced Space Weather & EVA Radiation Dashboards** — Beautiful real-time space weather visualization with gauge-based dashboard showing flare probabilities (C/M/X-Class), F10.7 Flux with historic/projected trends, and Active CMEs. New EVA Radiation Metrics Dashboard provides comprehensive radiation monitoring with normalized threshold visualization. All gauges use modern two-ring style with color-coded risk zones. UI improvements include dark blue font colors for better readability and verified/validated technical resource links.

**NEW in v1.8.82**: **Advanced HRV Analytics Platform** — State-of-the-art statistical analysis, ML pattern recognition, and clinical decision support with 5-tab interface (Clinical Decision, Statistical Tests, Trends & Forecast, Anomalies & Patterns, HRV + Garmin Integration). Features Shapiro-Wilk normality tests, age-stratified t-tests with Cohen's d effect sizes, 7-day forecasting with 95% CI, anomaly detection (Z-score/IQR), autonomic balance assessment, and semaphored risk recommendations (Green/Yellow/Orange/Red). All p-values displayed to 4 decimal places with scientific citations (Task Force 1996, Nunan 2010, Shaffer 2017).

**NEW in v1.8.81**: **Advanced Wearable Analytics** — Sophisticated predictive modeling for Garmin metrics: Body Battery forecasting (Holt-Winters smoothing with 95% CI), Allostatic Load Index (McEwen 1998), Circadian Rhythm Analysis (chronotype detection, peak performance hours), Stress Prediction (next-day forecasting), and Recovery Analysis (sleep debt calculation, days to full recovery).

**NEW in v1.8.80**: **Radiation Exposure Module** — Evidence-based space radiation dose estimation with 10 environments (Earth, Antarctica, LEO/ISS, Lunar Gateway, Lunar Transit, Lunar Surface ± SPE, Mars Transit, Mars Surface). Day-by-day cumulative tracking, EVA Go/No-Go assessment matrix (SAFTE-style visualization), NASA STD-3001 career limits (600 mSv), and literature-derived dose rates (Zhang 2020, Zeitlin 2013, Hassler 2014, Berger 2020).

**NEW in v1.8.68**: **Modern HRV Progress Tracking** — Real-time, detailed progress indicators for all HRV computations with step-by-step status, elapsed time tracking, and animated visual feedback. **Tab Persistence** keeps you on the current tab during analysis. **Enhanced HRV Metrics** including LnRMSSD, CVI (Cardiac Vagal Index), CSI (Cardiac Sympathetic Index), SDANN, SDNNi, and generalized pNNx. **HRF ↔ HRV Correlation Visualization** with interactive ECharts heatmaps showing r-values, t-statistics, and p-values (4 decimals) with scientific context.

**NEW in v1.8.37**: **Dual Garmin sleep autofill buttons + synced sleep/chronotype inputs** — One-click Vivosmart/Garmin pull now exists in both the Profile Tools Engine and the Sleep & Chronotype section under Energy & Nutrition. It fills sleep hours, quality, hours awake, RMSSD, resting HR, and feeds SAFTE fatigue plus Operational Performance, preferring stored Garmin daily metrics when available.
**NEW in v1.8.28**: **Crew mission workspaces** — The app now organizes data under `crew/` with **Mission 1** and **Mission 2**. The active mission’s **SQLite DB + backups** live in `crew/<Mission>/db/`, and per-subject files live in `crew/<Mission>/subjects/`.

**NEW in v1.8.27**: **Per-user SAFTE/FRMS defaults** — Save a typical **sleep window**, **duty window**, and **weekend policy** per profile so SAFTE/FRMS workflows can auto-load reproducible schedules without re-entry.

**NEW in v1.8.26**: **Mission FRMS v2 “Crew Risk Board” prototype** — Export a multi-profile roster view with crew-level FRMS metrics/classification plus **CSV/JSON** outputs and an **audit decision log (JSON)**.

**NEW in v1.8.25**: **Persisted study groups + mixed-effects inference** — In the Export tab, define a **Study ID**, assign users to **persisted groups** (stored in SQLite), and optionally run a **random-intercept mixed-effects model** for Group × Time on Δ vs baseline. The SAFTE/FRMS dashboard also surfaces a rule-based “why it triggered” alert list and includes it in the FRMS JSON export.

**NEW in v1.8.24**: **Longitudinal cohort comparisons (T0–T21)** — In the Export tab, compare **control vs intervention** using **within-subject Δ vs baseline** per timepoint, with CSV + Markdown exports (effect sizes + FDR-adjusted p-values).

**NEW in v1.8.23**: **Profile Tools Engine** — Comprehensive calculation engines accessible per user profile: SAFTE fatigue prediction with 24-hour cognitive effectiveness forecast, lnRMSSD-based recovery scoring, training readiness assessment with workout recommendations, personalized HRV analysis with parasympathetic/stress indices, and hour-by-hour performance forecasting. Run all tools with one click and export results to Markdown.

**NEW in v1.8.22**: **Personalized User Profile Features** — All calculations are now tailored to the individual user profile. Body fat estimation via US Navy method (using neck/waist/hip circumferences), sleep apnea risk (STOP-BANG score), age/sex-adjusted HRV reference ranges, VO2max fitness classification, cardiovascular risk profile, and personalized hydration requirements. Profile data flows to all tabs for truly personalized physiological assessments.

**NEW in v1.8.17**: OpenAI personas now log every request/answer with enforced `web_search` citations, the Metrics tab ships a one-click markdown appendix + tts-hd audio playback, and GPT-5 interpretations gain the same doctorate-level export/audio tooling for flight surgeon handovers.

**NEW in v1.8.15**: Sleep Analysis login + device import controls now run inside debounced sidebar forms to stop redundant reruns, the welcome/header + About tab badge the live release date and git commit directly from `CHANGELOG.md`, and `app/agent_runtime.py` seeds the OpenAI Agents SDK plan (personas, MCP servers, tool belt) with a new About tab expander describing the rollout.

**NEW in v1.8.14**: Each Time, Frequency, and Nonlinear tab now includes a dedicated RR file loader plus production ECharts visualizations in the User Profile, and space-weather correlations enforce exact timestamp alignment for Q1 journal submissions.

**NEW in v1.8.5**: Polar AccessLink automation with persistent OAuth tokens and VO2max history tracking. Sync your cardiorespiratory fitness data with one click and track changes over time.

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
git clone https://github.com/strikerdlm/HRV.git
cd HRV

# Recommended: run commands explicitly in the correct env (avoids wrong-env issues)
conda run -n hrv-py312 pip install -r requirements.txt
conda run -n hrv-py312 streamlit run app/operational_app.py  # fast UI (profile + simple space-weather context)
# or (full dashboards: correlations/ML + NOAA/Space Weather analysis)
conda run -n hrv-py312 streamlit run app/research_app.py
# or (single-user data science app with latest Streamlit)
conda run -n hrv-py312 pip install -r requirements_streamlit_latest.txt
conda run -n hrv-py312 streamlit run app/space_weather_ds_app.py

# (Optional interactive shell)
# conda activate hrv-py312
# streamlit run app/operational_app.py
```

#### TypeScript/Next.js Frontend (Modern UI)

A modern TypeScript/React frontend is available under `frontend/` with a FastAPI backend under `api/`.

**Prerequisites**:
- Node.js 18+ (LTS recommended)
- Python 3.12 and the `hrv-py312` conda env

**Quick Start (PowerShell)**:

```powershell
# Option 1: Use the start script (starts both API and frontend)
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

**Access Points**:
- Frontend: http://localhost:3100
- API Docs: http://localhost:8180/docs
- Streamlit: http://localhost:8501 (unchanged)

#### Option 2: Using Virtual Environment

```bash
# Clone the repository
git clone https://github.com/strikerdlm/HRV.git
cd HRV

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app/operational_app.py
# or (full dashboards)
streamlit run app/research_app.py
# or (single-user data science app with latest Streamlit)
pip install -r requirements_streamlit_latest.txt
streamlit run app/space_weather_ds_app.py
```

The app will open in your default browser at `http://localhost:8501`.

### Operational vs Research — the “philosophy” (rules of thumb)

- **Operational app** (`app/operational_app.py`): use for **clinical workflows** (User Profile, mission logs) and **lightweight space-weather context** (cached NOAA Kp/proton alerting inside the profile). Keep this app **fast, stable, and low-latency**.
- **Research app** (`app/research_app.py`): use for **HRV/HRF computation**, **NOAA/Space Weather dashboards**, **correlations**, and **ML**. This app can be heavier and is where experimental/advanced analytics should live.
- **Space Weather Data Science (Single User)** (`app/space_weather_ds_app.py`): streamlined workflow focused on single-subject analytics, NOAA/Space Weather correlations, and ML patterns. Uses the latest Streamlit via `requirements_streamlit_latest.txt`.

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
3. **Run Analysis**: Click **Run HRV Analysis** at the top of the page. You'll see real-time progress indicators showing each computation step (validation, artifact detection, windowed metrics, full-recording metrics, ML clustering, etc.) with elapsed time and completion percentage.
4. **Explore tabs**: Start with **Overview** for summary statistics, then explore **Gauges** for visual benchmarks. The active tab persists during analysis, so you can continue working while computations run.
5. **Export**: Go to **Export** tab to download a comprehensive Markdown report or generate a GPT-5.2 high-reasoning analysis

**Per-user persistence:** RR uploads are saved with the active profile (see the light-bulb banner) and immediately written to `crew/<Mission>/subjects/{user}/rr_intervals`. The app warns when you re-upload a previously analyzed file and can reuse stored HRV results when the file hash and analysis settings match (toggle in the sidebar) or let you recompute. Sidebar uploads target the active profile (Diego by default); uploads from the User Profile tab are scoped to that user and set that profile active. In **User Profile → HRV → HRV Measurement History**, use **Regenerate plots** if charts look stale after a new analysis run. In **User Profile → HRV → Stored RR Library**, you can load previously saved RR recordings back into the analysis workspace (optionally auto-running analysis) without re-uploading.

**Real-time progress tracking:** When you click **Run HRV Analysis**, you'll see a detailed progress panel showing each computation step (validation, artifact detection, windowed metrics, full-recording metrics, ML clustering, etc.) with elapsed time and completion percentage. The active tab persists during analysis, so you can continue working while computations run in the background.

**Per-profile readiness:** **User Profile → Readiness** computes readiness from stored parasympathetic-index history and displays HRV metric gauges using the same ECharts styling as the main Gauges tab.

**Clinical profile persistence:** **User Profile → Clinical Profile → Body Composition** now saves anthropometrics (body fat, lean/muscle mass, circumferences) to the database and renders per-user trends/history.

**Exploration medicine auto-enrichment:** **User Profile → Clinical Profile → Exploration Medical Record** includes a log date selector and can auto-compute a space-weather alert (NOAA Kp + >10 MeV proton flux) plus a baseline cumulative radiation dose estimate from mission profile/habitat + EVA hours, displaying the dose alongside NASA limit guidance. Stress and sleep fields can seed from objective HRV and Garmin daily metrics when present.

**FIT ↔ CSV tools (Data tab):** Convert Garmin FIT files to CSV directly inside the User Profile → Data tab, download the CSV, and store both FIT and CSV under the active profile. You can also upload Garmin CSVs to keep them with your profile.

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

| Module                    | What You Can Do                                                              |
| ------------------------- | ---------------------------------------------------------------------------- |
| 🌍**Space Weather** | Fetch live NASA/NOAA data, see CME arrival predictions, get Polar H10 timing |
| ☀️**Circadian**   | Simulate circadian rhythms with different light schedules                    |
| 😴**SAFTE/Fatigue** | Guided SAFTE fatigue workflow with auto-fill (wrist → clinical → Garmin → defaults), FRMS-style dashboard + USAF crew rest checks, and per-user saved schedule defaults |
| 🫀**Biofeedback**   | Try the paced breathing demo                                                 |

All other tabs show **example data** and **reference values** to help you understand what's available before uploading your own recordings.

---

## 📋 Features Overview

| Feature                                      | Description                                                                                                                                                                                        |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Time-Domain Metrics**                | SDNN, RMSSD, pNN50, Mean HR, CVNN, plus per-tab RR file loaders so you can select the exact recordings rendered in each visualization                                                             |
| **Frequency-Domain Analysis**          | VLF/LF/HF power, normalized units, LF/HF ratio via Welch, Periodogram, or AR methods with on-tab RR file selection                                                                                |
| **Nonlinear Metrics**                  | Poincaré SD1/SD2, DFA α1/α2, Sample/Approximate Entropy with on-demand RR loaders for publication-grade plots                                                                                    |
| **Heart Rate Fragmentation**           | PIP, IALS, PSS per PROOF-AF methodology with **HRF ↔ HRV correlation analysis** (interactive ECharts heatmaps with r, t-statistic, p-value)                                                                                                                      |
| **Geometric Metrics**                  | HRV Triangular Index, TINN (enhanced), Baevsky Stress Index                                                                                                                                         |
| **Advanced HRV Metrics** ✨NEW         | LnRMSSD, CVI (Cardiac Vagal Index), CSI (Cardiac Sympathetic Index), Mean HRmax-HRmin, Generalized pNNx (10ms/30ms/50ms), SDANN, SDNNi (long-term variability)                                      |
| **Population Norms**                   | Age/sex-stratified comparison against Nunan et al., Ortega et al., MESA Study data                                                                                                                 |
| **Blood Pressure Variability**         | BPV metrics (SD, CV, ARV, SV) with HRV-BPV correlation analysis                                                                                                                                    |
| **Circadian Physiology**               | Forger99, Jewett99, Hannay19 models with ESRI and light schedule simulation                                                                                                                        |
| **Sliding Window Analysis**            | Configurable windows with deviation detection and anomaly episodes                                                                                                                                 |
| **Autonomic Function Tests**           | Valsalva ratio, Deep breathing E:I response, 30:15 standing ratio                                                                                                                                  |
| **Readiness Scoring**                  | Kubios-style parasympathetic index with historical baseline comparison                                                                                                                             |
| **Space Weather Correlation**          | NOAA Kp, Dst, F10.7, solar wind, and X-ray flux correlations using exact timestamp synchronization (no nearest-neighbor drift) with configurable lags                                            |
| **Space Weather Impact Predictions**   | Exact arrival times for photons, SEPs, solar wind plasma, with Polar H10 timing recommendations                                                                                                    |
| **NASA DONKI Integration**             | Flares, CMEs, geomagnetic storms, radiation belt enhancements                                                                                                                                      |
| **Fatigue Prediction**                 | SAFTE biomathematical model for cognitive effectiveness + FRMS-style (ICAO-aligned) dashboard + USAF crew rest checks + publication-grade plot exports (ECharts toolbar: PNG/SVG/HTML/spec JSON + Print/Save PDF)                                               |
| **HRV Biofeedback**                    | Real-time coherence training with paced breathing                                                                                                                                                  |
| **CPU Performance Mode**               | Adjustable presets (Fast/Balanced/Quality) with smart downsampling                                                                                                                                 |
| **GPU Acceleration**                   | NVIDIA CUDA support (RTX 5070/4090/3080) for heavy computations                                                                                                                                    |
| **User Profile System**                | Centralized biometrics, clinical scales (ESS, Samn-Perelli, KSS), history tracking with ECharts timelines for assessments, Garmin wellness, HRV history, and exploration medicine dashboards      |
| **Personalized Health Metrics**        | Body fat (US Navy method), sleep apnea risk (STOP-BANG), age-adjusted HRV norms, VO2max fitness classification, cardiovascular risk profile, personalized hydration requirements                 |
| **Profile Tools Engine** ✨NEW         | SAFTE fatigue prediction, recovery score (lnRMSSD-based), training readiness assessment, **operational performance (HRV+SAFTE fused readiness)**, personalized HRV analysis, 24-hour performance forecast — all using profile data                      |
| **Active User Context Sync**           | Circadian and SAFTE tabs auto-fill age, chronotype, sleep debt, and mission schedules from the selected profile with a single sync button; body composition data flows to all tabs              |
| **Clinical Profiles**                  | Astronaut-grade assessment: BMR, TDEE, NASA nutrition, body composition with circumference tracking (neck, waist, hip, chest, arm, thigh, calf)                                                   |
| **Personalized HRV Interpretation**    | Age/sex-adjusted reference ranges from Nunan et al. (2010) and Shaffer & Ginsberg (2017); status, percentile estimate, and recommendations per metric                                             |
| **Exploration Medical Record**         | NASA isolation/mission log with EVA, radiation, stress, and behavioral metrics                                                                                                                     |
| **Exploration Medical Analytics**      | Radiation/EVA/stress dashboards with trend cards sourced from ExMC logs                                                                                                                            |
| **Radiation Exposure Module** ✨NEW    | Evidence-based dose models for 10 environments (LEO, Lunar, Mars), day-by-day tracking, EVA Go/No-Go matrix, NASA STD-3001 limits, space weather integration                                      |
| **Advanced Wearable Analytics** ✨NEW  | Body Battery forecasting (Holt-Winters), Allostatic Load Index, Circadian Rhythm Analysis, Stress Prediction, Recovery Analysis with sleep debt calculation                                       |
| **Advanced HRV Analytics** ✨NEW       | ML pattern recognition, statistical tests (Shapiro-Wilk, t-tests, Mann-Whitney U), trend forecasting, anomaly detection, clinical decision support with semaphored recommendations                |
| **Polar AccessLink VO2 Integration**   | Optional VO2max sync for exercise compensation via AccessLink API                                                                                                                                  |
| **Multi-Language**                     | English + Spanish (Colombian-validated scales: ESE-VC, KSS-CO)                                                                                                                                     |
| **Laboratory Tracking**                | CBC/Hemogram, Blood Chemistry, Urinalysis with normal ranges                                                                                                                                       |
| **Multi-Device Import**                | Polar H10, Garmin Vivosmart 5, ActiGraph GT3X, Somfit Pro                                                                                                                                          |
| **FIT ↔ CSV Tools**                    | Convert Garmin FIT to CSV inside the Data tab, download, and store both FIT/CSV per profile; import Garmin CSVs into the active profile                                                          |
| **Garmin Vivosmart 5 Clinical Ingest** | Upload FIT/ZIP (batch supported) to auto-fill steps, distance, sleep score/quality/duration, SpO₂, respiration (awake/sleep), stress, calories, and body battery charge/drain with ECharts gauges |
| **Docker Deployment**                  | Containerized with PostgreSQL/TimescaleDB for production environments                                                                                                                              |
| **AI Interpretation**                  | GPT-5.2 high-reasoning analysis with enforced `web_search` citations, mission logging, markdown appendix, and optional tts-hd audio playback                                                      |
| **Modern Progress Tracking** ✨NEW      | Real-time step-by-step progress indicators for HRV computations and space weather fetches with elapsed time, completion percentage, and visual status indicators                                    |
| **Tab Persistence** ✨NEW              | Active tab persists across Streamlit reruns (compute/analyze buttons), maintaining workflow continuity                                                                                            |
| **HRF ↔ HRV Correlation Visualization** ✨NEW | Interactive ECharts heatmaps showing Pearson correlations between Heart Rate Fragmentation and HRV metrics with r-values, t-statistics, p-values (4 decimals), scatter plots, and scientific interpretation |
| **Publication Export**                 | APA 7th edition formatted reports, LaTeX tables, CSV/JSON data                                                                                                                                     |

---

## 🗺️ Development Roadmap (v2.0)

### Current Sprint (December 2025)

| Priority | Feature                                      | Status                                                |
| -------- | -------------------------------------------- | ----------------------------------------------------- |
| ✅ DONE  | Multi-user sessions (1-13 concurrent)        | Complete                                              |
| ✅ DONE  | CPU optimization for non-GPU systems         | Complete                                              |
| ✅ DONE  | Smart CPU auto-detection & tuning            | Complete                                              |
| ✅ DONE  | Clinical Profile UI visualization            | Complete (batched forms + debounced saves)            |
| ✅ DONE  | Move Circadian settings to tab               | Complete                                              |
| ✅ DONE  | Active user context sync across mission tabs | Complete (Circadian + SAFTE auto-populate)            |
| ✅ DONE  | Per-tab settings persistence                 | Complete (TabSettingsManager)                         |
| ✅ DONE  | Cross-tab correlation (Circadian → Fatigue) | Complete (shared broker + auto-applied sleep window)  |
| ✅ DONE  | Polar AccessLink automation                  | Complete (persistent OAuth tokens + VO2max history)   |
| ✅ DONE  | Exploration Medical Analytics dashboards     | Complete (radiation/EVA/stress cards in Clinical tab) |
| ✅ DONE  | Longitudinal timepoints (T0–T21)             | Complete (tag HRV + assessments to study timepoints)  |
| ✅ DONE  | Baseline/Δ analytics (T0–T21)                | Complete (User Profile → HRV Measurement History baseline/Δ table) |
| ✅ DONE  | Per-user HRV cache + GPT export persistence  | Complete (SQLite-backed reusable payloads + reports)  |
| ✅ DONE  | SAFTE tab FRMS dashboard + USAF crew rest    | Complete (ICAO-aligned FRMS dashboard + AFMAN 11-202V3 checks + plot exports) |
| ✅ DONE  | Cohort/group baseline/Δ comparisons (T0–T21) | Complete (Export → Longitudinal cohort comparisons: control vs intervention) |
| 🚧 IN PROGRESS | Plot governance enforcement across all tabs | Standardize captions/labels/exports for every plot (ECharts-first; Plotly fallback) |

**Best next task:** Finish **plot governance enforcement** across *all* tabs (captions + axis units + consistent tooltips/legends + export coverage), then extend FRMS into a **mission-level “crew risk board”** (multi-profile aggregation + escalation + audit trail).

### Planned Features (Q1 2026)

#### Mission FRMS v2.0 (comprehensive crew readiness + alerts)
The SAFTE tab already ships a baseline **predictive FRMS dashboard** (exposure metrics + SMS-style risk matrix + USAF crew rest check). The next milestone is a **mission-wide FRMS system** that runs across *all profiles* and produces actionable alerts + mitigations for safety-critical windows.

**Status update:** A **prototype “Crew Risk Board”** is now available in **Export → Group summaries → “Mission FRMS v2 — Crew Risk Board (multi-profile)”**, including **CSV/JSON exports** plus an exportable **decision log (JSON)** for audit trail workflows.

**What’s left to implement (end-to-end FRMS):**
- **Mission-level roster + “crew risk board”**: aggregate fatigue exposure and risk classification across all active profiles (per shift/EVA/task window), with a single view for flight surgeon / mission director decision-making.
- **FRMS processes (predictive + proactive + reactive)**: add structured hazard reporting, SPIs/trending, safety assurance checks, and a transparent audit trail for risk decisions (inputs → classification → mitigation → outcome).
- **Alerting + escalation**: rules-based alerts when thresholds are crossed (e.g., time ≤77% in-scope, WOCL overlap, crew-rest noncompliance), plus “why it triggered” explanations and exportable evidence packets.
- **Evidence-based countermeasure recommender**: standardized, mission-safe recommendations (sleep extension, controlled rest, caffeine timing, light scheduling, task re-allocation), with citations per recommendation and explicit constraints/limitations.
- **Model calibration + validation layer**: optional PVT/psychomotor vigilance testing, incident/near-miss logging, and calibration hooks (SAFTE-R + individualized parameters) to validate predictive skill for this mission.

**Core standards & research (verifiable sources, APA):**
- International Civil Aviation Organization. (2016). *Manual for the Oversight of Fatigue Management Approaches* (Doc 9966, 2nd ed.). https://www.icao.int/safety/fatiguemanagement/FRMS%20Tools/Doc%209966.FRMS.2016%20Edition.en.pdf
- International Civil Aviation Organization. (2011). *FRMS Implementation Guide for Operators* (July 2011). https://www.icao.int/safety/fatiguemanagement/FRMS%20Tools/FRMS%20Implementation%20Guide%20for%20Operators%20July%202011.pdf
- International Civil Aviation Organization. (2018). *Safety Management Manual* (Doc 9859, 4th ed.). https://store.icao.int/en/safety-management-manual-doc-9859
- Federal Aviation Administration. (2013). *Fatigue Risk Management Systems for Aviation Safety* (Advisory Circular AC 120-103A). https://www.faa.gov/documentlibrary/media/advisory_circular/ac_120-103a.pdf
- International Air Transport Association, International Civil Aviation Organization, & International Federation of Air Line Pilots’ Associations. (2015). *Fatigue Management Guide for Airline Operators* (2nd ed.). https://www.ifalpa.org/media/2279/fmg-for-airline-operators-2nd-ed.pdf
- Department of the Air Force. (n.d.). *AFMAN 11-202V3: General Flight Rules.* https://static.e-publishing.af.mil/production/1/af_a3/publication/afman11-202v3/afman11-202v3.pdf
- Hursh, S. R., Redmond, D. P., Johnson, M. L., Thorne, D. R., Belenky, G., Balkin, T. J., Storm, W. F., Miller, J. C., & Eddy, D. R. (2004). Fatigue models for applied research in warfighting. *Aviation, Space, and Environmental Medicine, 75*(3 Suppl), A44–A53. https://doi.org/10.1097/01.ASM.0000122824.30373.5E
- Van Dongen, H. P. A., Maislin, G., Mullington, J. M., & Dinges, D. F. (2003). The cumulative cost of additional wakefulness: Dose-response effects on neurobehavioral functions and sleep physiology from chronic sleep restriction and total sleep deprivation. *Sleep, 26*(2), 117–126. https://doi.org/10.1093/sleep/26.2.117
- Belenky, G., Wesensten, N. J., Thorne, D. R., Thomas, M. L., Sing, H. C., Redmond, D. P., Russo, M. B., & Balkin, T. J. (2003). Patterns of performance degradation and restoration during sleep restriction and subsequent recovery: A sleep dose-response study. *Journal of Sleep Research, 12*(1), 1–12. https://doi.org/10.1046/j.1365-2869.2003.00337.x
- Dawson, D., & Reid, K. (1997). Fatigue, alcohol and performance impairment. *Nature, 388*(6639), 235. https://doi.org/10.1038/40775
- Williamson, A. M., & Feyer, A.-M. (2000). Moderate sleep deprivation produces impairments in cognitive and motor performance equivalent to legally prescribed levels of alcohol intoxication. *Occupational and Environmental Medicine, 57*(10), 649–655. https://doi.org/10.1136/oem.57.10.649
- Folkard, S., & Tucker, P. (2003). Shift work, safety and productivity. *Occupational Medicine, 53*(2), 95–101. https://doi.org/10.1093/occmed/kqg047
- Hilditch, C. J., Arsintescu, L., Gregory, K. B., & Flynn-Evans, E. E. (2020). Mitigating fatigue on the flight deck: How is controlled rest used in practice? *Chronobiology International, 37*(11), 1563–1574. https://doi.org/10.1080/07420528.2020.1803898

#### Per-user computation persistence (beyond HRV)
- **Circadian run history per user**: persist circadian scenario inputs + outputs (DLMO/CBT/ESRI trajectories) so users can review and export prior simulations without rerunning.
- **SAFTE run history per user**: persist SAFTE inputs + forecasts (and the data source used: wrist → clinical → Garmin Connect) for auditability and fast reuse.
- **Cross-module “mission package export” per user**: one-click export bundling HRV + circadian + fatigue + space-weather context + stored GPT-5.2 report.

#### SAFTE-R performance prediction (per subject)
- **SAFTE-R model option**: add SAFTE-R parameterization and expose it under each subject in **User Profile → Fatigue**, including calibration hooks (sleep/wake history + chronotype + workload).

#### Mission-specific radiation dose modelling
- **Mission-linked dose model**: compute effective dose per user from the mission being simulated (environment/shielding/EVA timeline + storm-time hazard flags), and persist both model inputs and outputs per mission scenario.

#### HRV protocol covariates (measurement accuracy)
- **Protocol context capture**: store and apply key covariates (posture, time-of-day, breathing protocol/respiratory rate, recent exercise/caffeine/nicotine/alcohol, acute illness, medication changes) to improve per-user interpretation and comparability across sessions.

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

> **For detailed roadmap**: See [WARP.md](WARP.md) section "🚀 DEVELOPMENT ROADMAP" and `docs/Manual.md` → **Pending Developments and Roadmap**.

---

## 🤖 OpenAI Agents SDK Integration Blueprint

Mission Control - Flight Surgeon already uses GPT-5.2 high-reasoning summaries; the next leap is to embed OpenAI Agents SDK with code interpreter, Model Context Protocol (MCP), web/file search, Wolfram Alpha reasoning, and E2B secure sandboxes so every astronaut profile benefits from autonomous, tool-using copilots. This blueprint stays aligned with the v2.0 roadmap and keeps all healthcare data on-device while letting agents reason over HRV, space weather, and wearable signals in near real time.

> **Implementation status**: `app/agent_runtime.py` now defines the tool belt, MCP scopes, and all three personas; the About tab includes an expander that surfaces this configuration for mission leads.

> **v1.8.17 update**: Every persona now enforces `web_search`-backed citations, logs its request/response payloads to `logs/app.log`, and exposes Markdown + tts-hd exports (Metrics tab + Export tab) so doctor-level answers can be reviewed offline or played back discreetly during mission briefs.

### Strategic Outcomes
- Close the loop between RR uploads, NOAA/SWPC feeds, and mission decisions through MCP-enabled agents rather than ad-hoc scripts.
- Deliver reproducible science packages (not just prose) by combining `code_interpreter` outputs, Wolfram Alpha derivations, and sandboxed E2B notebooks per analysis.
- Expose mission-ready automations (fatigue clearance, EVA go/no-go, radiation countermeasure planning) that adapt to simple wearable inputs plus atmospheric/space-weather loads.
- Keep compliance: secrets in `.env`, deterministic Python hand-offs, logging via `logging_config.py`, and audit trails in `logs/`.

### Architecture Snapshot
- **Agent Runtime**: `openai.agents` service (GPT-5.2 High Reasoning) deployed as a sidecar service (`app/agent_router.py`, future) to keep Streamlit reruns clean.
- **Context Graph (MCP)**: Servers for `hrv_users.db`, `docs/Manual.md`, `logs/app.log`, NOAA cache folders, and structured exports. Each server enforces read-only scopes per agent.
- **Tool Belt**:
  - `code_interpreter` for bounded analytics on uploaded RR arrays (cap output to `/tmp/agents/<session>` and delete per request).
  - `file_search` indexing curated corpora (Manual, WARP, NASA/NOAA references, exploration medical SOPs).
  - `web_search` with mission-safe providers (NASA ADS, SWPC, PubMed) for fresh solar/anatomic insights.
  - **Wolfram Alpha API** via custom tool spec for symbolic math (ionospheric absorption, radiation transport) with AppID stored in `.env`.
  - **E2B workspace** for heavy simulations (multi-hour circadian entrainment, Monte Carlo radiation) while keeping deterministic seeds.
  - NOAA/DONKI/SpaceWeatherLive fetchers exposed as callable tools rather than Streamlit callbacks so agents can refresh data on demand.

### Step-by-Step Implementation Plan
1. **Stabilize Data & Logging (Week 0)**
   - Confirm `hrv_users.db` migrations are current; add read-only SQLite roles for agents (`sqlite3.connect(..., uri=True, mode=ro)` in planned `agent_data_bridge.py`).
   - Harden logging: ensure `logs/app.log` and `logs/errors.log` rotate at 10 MB, then register them with MCP so agents can cite trace IDs when recommending actions.
   - Capture wearables ingest health (Garmin, Polar) in a single `data_ingest_status.json` so agents know whether they can rely on the latest VO₂max/sleep metrics.
2. **Model Context Protocol Bridges (Week 1)**
   - Stand up MCP servers (e.g., `mcp://hrv-db`, `mcp://docs`, `mcp://space-weather-cache`) using the OpenAI MCP SDK; map each to deterministic selectors:
     1. `hrv-db`: parameterized SQL views (recent RR sessions, cohort aggregates, radiation dose log).
     2. `docs`: pinned commit of `docs/Manual.md`, `WARP.md`, scientific PDFs.
     3. `space-weather-cache`: JSON snapshots under `app/data_cache/noaa_space/` with TTL metadata.
   - Define per-agent policies (read vs. write) and include mission tags (`user_id`, `session_id`) so every tool call is auditable.
3. **Toolchain Enablement (Week 1–2)**
   - **code_interpreter**: configure 512 MB sandbox, mount-only `/tmp/mission_control/agents/<cedula>`; prevent network, allow `numpy`, `pandas`, `scipy`, `statsmodels`, `plotly`. Pipe outputs back as Markdown tables and PNGs for Streamlit tabs.
   - **file_search**: run nightly embeddings over `docs/`, `CHANGELOG.md`, and curated PDFs; store vector store in `app/data_cache/vector_db/` with mission-specific namespaces.
   - **web_search**: whitelist NASA ADS, SWPC, NOAA, ESA Space Weather, PubMed; default to 3 snippets with citation metadata so reports remain evidence-backed.
   - **Wolfram Alpha**: create `wolfram_alpha` tool definition referencing `.env` `WOLFRAM_APP_ID`; restrict queries to mission physics (solar wind propagation, Schumann resonances, barometric modeling).
   - **E2B**: template E2B sandboxes (Python 3.12) loaded with `requirements.txt`; expose `launch_e2b_simulation(params)` tool returning signed artifact URLs for downstream inclusion.
   - **Other APIs**: add NOAA/SpaceWeatherLive tool specs so the agents call the same deterministic fetch routines used in `app/noaa_space.py` rather than inventing new HTTP clients.
4. **Mission-Focused Agent Definitions (Week 2)**
   - **Solar-Physiology Correlator**: Automates RR↔space-weather lag scans via `code_interpreter`, writes results into MCP `correlation_reports` table, escalates anomalies when `|r|>0.6` and FDR q<0.05.
   - **Wearable Recovery Concierge**: Uses `file_search` (Manual norms) + `hrv-db` views + Wolfram Alpha to translate Garmin/Polar data into operational prescriptions (hydration, EVA scheduling).
   - **Environmental Threat Watcher**: Combines `web_search`, NOAA tools, and E2B radiation Monte Carlo runs to predict when atmospheric or geomagnetic disturbances degrade HRV readiness; posts alerts into Streamlit notification center.
  - Each agent uses GPT-5.2 High Reasoning for responses, with `instructions` embedding the deterministic rules (bounded loops, type-safe outputs, cite NOAA/peer-reviewed sources).
5. **Experience Integration (Week 3)**
   - Extend `app/gpt_interpretation.py` to call the Agent Router: user selects “Autonomous Analysis” → app posts mission context (user profile, selected sessions, NOAA bundle IDs) to the chosen agent.
   - Surface multi-modal outputs: Markdown summary, structured JSON (metrics, decision, confidence), and optional PNGs/CSVs from `code_interpreter` or E2B.
   - Log every agent call using `log_user_action("agent_run", {...})` with toolchain metadata for HIPAA-like traceability.
6. **Validation & Flight Readiness (Week 4)**
   - Run regression notebooks (pytest + hypothesis) to confirm agent-generated code never mutates data outside `/tmp`.
   - Simulate degraded comms: disable WAN and ensure MCP/file_search fallbacks still produce actionable guidance.
   - Conduct SME review sessions (flight surgeons, biomed engineers) to vet recommendations before enabling in production tabs.

### Metric Explainability Specialist (NEW)
- `app/agent_runtime.py` now includes a **Metric Explainability Specialist** persona that binds GPT-5.2 high reasoning + `code_interpreter` to per-metric narrative output.
- `app/agent_insights.py` packages mission context (`metric_samples`, reference catalogue, active user profile) and gracefully falls back to deterministic Task Force (1996) / Shaffer & Ginsberg (2017) comparisons when the API key is missing.
- The **Metrics** tab surfaces a new "Metric Explanations (Agent SDK)" panel so every SDNN, RMSSD, pNN50, LF/HF, HF power, and mean HR value includes a human-readable status + citation even before the agent executes.

### Disruptive Opportunities in Aerospace Medicine
- **Closed-loop EVA readiness**: Agents correlate HRV drops, atmospheric pressure swings, and predicted Kp surges to recommend countermeasures before EVA windows open.
- **Adaptive countermeasure playlists**: E2B sandboxes prototype breathing/light protocols, while code_interpreter validates HRV improvements on-the-fly.
- **Personalized atmospheric risk scoring**: Wolfram Alpha tool computes ionospheric absorption paths customized to mission latitude, feeding fatigue risk dashboards.
- **Rapid research translation**: web_search + file_search let agents cite fresh literature (Task Force updates, ExMC memos) while maintaining deterministic sourcing.

### Future Potential
- Multi-agent swarms (circadian planner + fatigue guardian) negotiating mission trade-offs via MCP shared memory.
- Automated publication drafts combining code_interpreter figures, Agents SDK narrative, and NASA-standard tables for journals.
- Voice-enabled mission control where wearables stream into agents that reason aloud about human performance vs. solar storms.

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

* **Wellness Export ZIP**: Download from Garmin Connect → Account Settings → Export Wellness Data
  ```
  https://connect.garmin.com/modern/settings/accountInformation
  ```
* **Export JSON (unzipped)**: You can also upload individual Garmin export `.json` files (e.g., `UDSFile_*.json`, `*_sleepData.json`) in **User Profile → Data → Wrist Monitoring (Vivosmart 5)**.
* **FIT Files**: Export individual activities from Garmin Connect web
* **API Access**: Configure `GARMIN_EMAIL` and `GARMIN_PASSWORD` in `.env` (see Configuration below).
  - **Recommended**: use token-based login via `~/.garminconnect` (see “Garmin Connect token authentication” below).

### Environment Configuration

The application uses a **portable environment loader** (`app/env_loader.py`) that automatically finds and loads your `.env` file from the project root, regardless of computer username or absolute path.

**Supported variables** (create `.env` in project root):
```env
GARMIN_EMAIL=your_email@example.com
GARMIN_PASSWORD=your_password
NASA_API_KEY=your_nasa_api_key
ACCUWEATHER_API_KEY=your_accuweather_key
OPENAI_API_KEY=sk-proj-...
```

**How it works:**
- Searches upward from `app/` for marker files (`.env`, `README.md`, `.git`, etc.)
- Loads environment variables without hardcoded paths
- Works across different computers and directory structures
- Falls back gracefully if `.env` is not found

**Manual usage** (optional):
```python
from env_loader import load_env_file, get_env_variable

# Method 1: Automatic loading
load_env_file(verbose=True)

# Method 2: Get specific variables with validation
api_key = get_env_variable("NASA_API_KEY", required=True)
```

See `app/env_loader_example.py` for complete examples.

#### Garmin Connect token authentication (recommended)
Garmin logins can require MFA/extra verification and may fail in non-interactive environments.
This project supports **token-based auth**:
- The app will **try saved tokens first**, before falling back to `GARMIN_EMAIL` / `GARMIN_PASSWORD`.
- Tokens are stored under your home directory at `~/.garminconnect/`.

**Generate tokens (one-time interactive step):**
1. Ensure `.env` contains `GARMIN_EMAIL` and `GARMIN_PASSWORD`.
   - If your password contains characters like `#` or spaces, wrap it in quotes.
2. Run:
   ```
   python tests/test_garmin_email.py
   ```
3. Follow prompts (including MFA if required). Tokens will be saved to `~/.garminconnect/`.

**Move to a new computer:**
- Copy the entire `~/.garminconnect/` directory to the new machine under the new user’s home directory.

**Security note:** Treat `~/.garminconnect/` like a password/API key (do not commit it to git).

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
- **NEW:** "Metric Explanations (Agent SDK)" panel that annotates each SDNN/RMSSD/pNN50/LF/HF/Mean HR value with Task Force/Shaffer ranges, plus optional GPT-5.2 agent narratives that leverage `code_interpreter`.

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

### HRF ↔ HRV Correlations Tab ✨NEW

- **Interactive ECharts Heatmap**: Color-coded correlation matrix between HRF metrics (PIP, IALS, PSS) and HRV metrics
- **Detailed Statistics Table**: Pearson r, t-statistic, p-value (4 decimals) with strength/direction interpretation
- **Top Correlation Scatter Plot**: Visualizes the strongest HRF↔HRV relationship with regression line
- **Scientific Context**: Explains HRF vs HRV differences, research findings (Costa 2017, Cathey 2024, Galdino 2023), and correlation interpretation
- **Per-Recording Analysis**: Computes correlations across multiple recordings for population-level insights
- **Button-Driven Computation**: Click "Compute HRF↔HRV correlations" to run analysis (results cached in session)

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
- **Auto-run assessment (5-day forecast)** uses wrist monitoring data from the Assessment tab when present, falls back to subjective clinical sleep quality if wrist data is absent, and only falls back to Garmin Connect API (requires `GARMIN_EMAIL`/`GARMIN_PASSWORD`) when neither is available; the summary used in the prediction is displayed for traceability.

### Space Weather Tab

- **Impact Predictions**: Exact arrival times for all energy categories in Bogotá (UTC-5)
  - Photon/X-ray events (instantaneous)
  - Solar Energetic Particles (SEPs)
  - Solar wind plasma (L1→Earth travel time calculated)
  - Geomagnetic conditions (Kp/Dst)
- **Polar H10 Recommendations**: Automatic EKG timing guidance based on event severity
- **Always-on data**: Auto-loads on tab open (cache-first) and falls back to the last cached Kp/F10.7 values if the network blips—no RR uploads required
- Live Kp index, solar flux, solar wind parameters
- SpaceWeatherLive snapshot with CME/flare data
- Lag-aware correlations (0–72h) with HRV metrics
- Partial correlations controlling for weather covariates

### NOAA Space Tab

- Comprehensive NOAA SWPC data feeds
- Manual fetch by default (cache-first); optional auto-fetch toggle in Processing Mode; manual refresh available
- Interactive gauges for all space weather metrics
- Batch correlation analysis across multiple parameters
- Feature matrix builder for predictive modeling

### Export Tab

- Markdown report with all metrics and interpretations
- CSV/JSON data export
- LaTeX tables for publications
- **🤖 GPT-5.2 High Reasoning Analysis**: Complete AI-powered report generation with code interpreter, web search citations, and comprehensive physiological interpretation (requires API key)
- **Plot exports (all ECharts charts)**: Use the inline export toolbar to download **PNG (high-DPI)**, **SVG (vector)**, **HTML**, and **spec JSON**, or **Print/Save PDF** from your browser.

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

| Setting                 | Default          | Description                                   |
| ----------------------- | ---------------- | --------------------------------------------- |
| **Window size**   | 5 min            | Sliding window duration for windowed analysis |
| **Step size**     | 1 min            | Window overlap/step                           |
| **Min RR count**  | 60               | Minimum beats per window                      |
| **QC method**     | threshold_median | Artifact detection algorithm                  |
| **Max deviation** | 0.2              | Artifact threshold (20% deviation)            |
| **Median window** | 11               | Rolling median window for QC                  |
| **PSD method**    | Welch            | Spectral estimation method                    |
| **Processing Mode** | Manual-only     | Disable auto-run requests; optional space-data auto-fetch when enabled |
| **Manual tab rendering** | On        | Require explicit **Load** per tab before running computations/plots (Processing Mode) |

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
│   ├── research_app.py             # Research UI entrypoint (full dashboards)
│   ├── operational_app.py          # Operational UI entrypoint (fast workflow)
│   ├── space_weather_ds_app.py     # Single-user space weather data science app
│   ├── hrv_core.py                 # Core HRV computation functions
│   ├── hrv_progress.py             # Modern HRV progress tracking (v1.8.68)
│   ├── hrv_interpretation.py       # Enhanced HRV interpretation module (v1.8.68)
│   ├── space_weather_progress.py   # Space weather progress tracking (v1.8.67)
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
│   ├── gpt_interpretation.py       # GPT-5.2 AI interpretation
│   ├── gpu_processing.py           # NVIDIA CUDA GPU acceleration
│   ├── noaa_space.py               # NOAA space weather data
│   ├── performance_utils.py        # CPU performance optimization utilities
│   ├── space_weather_impact.py     # Impact predictions & Polar H10 timing
│   ├── space_weather_persistence.py # NOAA/NASA data persistence
│   ├── radiation_exposure.py       # Evidence-based radiation dose models (v1.8.80)
│   ├── wearable_analytics.py       # Advanced Garmin predictive analytics (v1.8.81)
│   ├── advanced_hrv_analytics.py   # ML/statistics/clinical decision support (v1.8.82)
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

# Run TypeScript frontend with FastAPI backend (API :8180)
docker-compose --profile typescript up -d api
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
