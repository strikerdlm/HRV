## Mission Control - Flight Surgeon — Complete User Manual

### Author

**Dr. Diego Leonel Malpica Hincapié, MD**  
*Aerospace Medicine Specialist*  
National University of Colombia  
Physiology Instructor, Colombian Aerospace Force  
Contributing to **AsterPhysiology** Research Initiative

**GitHub Repository:** [https://github.com/strikerdlm/HRV](https://github.com/strikerdlm/HRV)  
**Version:** 1.8.23  
**Last Updated:** 2025-12-18

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
11. [Space Weather Impact Predictions](#space-weather-impact-predictions)
12. [Space Weather Correlation](#space-weather-correlation)
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
24. [Multi-Modal Sensor Fusion](#multi-modal-sensor-fusion)
25. [Long-Term HRV Trending Analysis](#long-term-hrv-trending-analysis)
26. [Exercise HRV Analysis](#exercise-hrv-analysis)
27. [Machine Learning Predictions](#machine-learning-predictions)
28. [Real-Time BLE Integration](#real-time-ble-integration)
29. [Docker Deployment](#docker-deployment)
30. [Pending Developments and Roadmap](#pending-developments-and-roadmap)

---

## Getting Started

### Explore Without Data

The app is fully navigable **without uploading HRV data**. These features work immediately:

| Module | What You Can Do |
|--------|-----------------|
| 👤 **User Profile** | Register profile, complete clinical scales (ESS, Samn-Perelli, KSS), track history |
| 🌍 **Space Weather** | Fetch live NASA/NOAA data, see CME arrival predictions, get Polar H10 timing |
| ☀️ **Circadian** | Simulate circadian rhythms with different light schedules |
| 😴 **SAFTE/Fatigue** | Model how sleep debt affects cognitive performance |
| 🫀 **Biofeedback** | Try the paced breathing demo |

All other tabs show **example data** and **reference values** to help you understand what's available before uploading your own recordings.

**Session persistence:** Circadian and SAFTE tabs now remember per-user configurations during the current session—when you switch users or rerun the app, your last light schedule and fatigue inputs are restored automatically.

**Cross-tab correlation:** The Circadian tab now publishes DLMO/CBT markers, ESRI, and light window details to the SAFTE/Fatigue tab. A single click in SAFTE applies the latest circadian sleep window and chronotype offset to fatigue simulations for tighter mission planning.

**Navigation note:** The Science tab now sits next to References for quick access. About, Space Weather, and NOAA tabs stay fully visible regardless of data state. Space Weather and NOAA tabs auto-load cache-first data on open (reusing cached Kp/F10.7/NOAA feeds if offline) even without RR uploads. HRV history in the profile loads only the latest records for quicker switching. HRV analysis runs only after clicking **Run HRV Analysis**; the database lives alongside the app (`hrv_users.db`) for easy portability.

**Release awareness:** The welcome header and About tab now read version, release date, and git commit metadata directly from `CHANGELOG.md`, so flight surgeons can confirm they are on v1.8.15 (or later) without leaving the UI. The indicator flips to “dirty” whenever the working tree has uncommitted changes.

### System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.10 | 3.11+ |
| RAM | 4 GB | 8 GB |
| Storage | 500 MB | 1 GB |
| Browser | Chrome 90+ | Chrome/Edge latest |
| GPU (optional) | — | NVIDIA RTX 3080/4090/5070 |

### GPU Acceleration (Optional)

For heavy HRV computations, GPU acceleration is supported via NVIDIA CUDA:

1. **Supported GPUs**: RTX 5070, RTX 4090, RTX 3080, and other CUDA-capable cards
2. **Installation**: `pip install cupy-cuda12x` (for CUDA 12.x)
3. **Usage**: Enable in sidebar under "🖥️ GPU Processing"
4. **Benefits**: 2-10x speedup for FFT, PSD, and large array operations

The app automatically detects GPU availability and falls back to CPU when CUDA is not present.

### Installation Steps

**Step 1: Clone or download the repository**

```bash
git clone https://github.com/yourusername/hrv-space-weather.git
cd hrv-space-weather
```

**Step 2: Set up Python environment**

**Option A: Using Conda (Recommended)**

```bash
# Activate the conda environment
conda activate hrv-py312

# Verify Python version (should be 3.12)
python --version
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
pip install -r requirements.txt
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
streamlit run app/app.py
```

The app opens at `http://localhost:8501` in your default browser.

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

- RR uploads are saved to the active user profile (light-bulb indicator) and immediately written to `data/{user}/rr_intervals`; computed HRV results persist with their analysis settings.
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

Based on the Sleep, Activity, Fatigue, and Task Effectiveness model:

**Model Components:**
- **Circadian Process**: 24-hour alertness rhythm adjusted for chronotype
- **Homeostatic Process**: Sleep pressure accumulation (~2.4%/hour awake)
- **Sleep Debt**: Cumulative deficit from insufficient sleep

**Outputs:**
- Current effectiveness (%)
- 4h, 8h, 24h forecasts
- Risk level (Minimal to Critical)
- Optimal sleep time
- 24-hour performance curve

Reference: Hursh SR, et al. *Aviat Space Environ Med.* 2004;75(3):A44-A53.

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

### Valsalva Maneuver

**Protocol:**
1. Record continuous RR intervals (≥60 seconds)
2. Patient performs 15-second forced expiration against closed glottis
3. Note exact timing of strain start/end

**Step-by-step in app:**

1. Go to **ANS Function Tests** tab
2. Expand "Valsalva Ratio" section
3. Enter Phase II window (strain period):
   - Start: seconds from recording start when strain began
   - End: seconds when strain ended (typically +15s)
4. Enter Phase IV window (recovery period):
   - Start: seconds when strain was released
   - End: typically +15-20s after release
5. Click "Compute Valsalva Ratio"

**Example:**
```
Recording starts at 0s
Patient begins strain at 10s
Strain ends at 25s
Recovery monitored until 45s

Phase II window: 10-25s
Phase IV window: 25-45s

Result:
Phase II min RR: 650 ms
Phase IV max RR: 950 ms
Valsalva ratio: 1.46

Interpretation: Normal (>1.2 in middle-aged adults)
```

### Deep Breathing Test

**Protocol:**
1. Patient breathes at controlled rate (typically 6 breaths/min = 10s cycles)
2. Record 6 complete cycles
3. E:I ratio reflects vagal reactivity

**Step-by-step in app:**

1. Go to **ANS Function Tests** tab
2. Expand "Deep Breathing" section
3. Enter:
   - Start time: when paced breathing began
   - Cycle length: 10s for 6 breaths/min
   - Number of cycles: 6
4. Click "Compute Deep Breathing"

**Example:**
```
Paced breathing starts at 30s
6 breaths/min = 10s per cycle
6 cycles measured

Settings:
Start time: 30s
Cycle length: 10s
Cycles: 6

Result:
Mean E:I difference: 180 ms
Mean E:I ratio: 1.24
Mean HR difference: 12 bpm

Interpretation: Normal vagal reactivity
```

### 30:15 Standing Ratio

**Protocol:**
1. Patient supine for baseline
2. Patient stands at specified time
3. Record HR response: initial tachycardia (beat 15), relative bradycardia (beat 30)

**Step-by-step in app:**

1. Go to **ANS Function Tests** tab
2. Expand "30:15 Ratio" section
3. Enter:
   - Stand time: exact second when patient stood
   - Window 15: time range around 15th beat post-stand
   - Window 30: time range around 30th beat post-stand
4. Click "Compute 30:15 Ratio"

**Example:**
```
Patient stood at 60s
Estimate beat 15 at ~70s (±2s)
Estimate beat 30 at ~85s (±2s)

Settings:
Stand time: 60s
Window 15: 68-72s
Window 30: 83-87s

Result:
RR at beat 15 (min): 620 ms
RR at beat 30 (max): 780 ms
30:15 ratio: 1.26

Interpretation: Normal (>1.04 in healthy adults)
```

---

## Space Weather Impact Predictions

The Space Weather Impact Predictions feature calculates exact arrival times for different categories of solar energy hitting Earth, providing Polar H10 EKG monitoring recommendations optimized for your research on biological effects.

Data now preloads automatically when you open the Space Weather tab (cache-first). If the network is unavailable, the app serves the last cached Kp/F10.7 snapshot and surfaces a warning; you can still click **🔄 Fetch Impact Predictions** to force a refresh.

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

1. Navigate to **Space Weather** tab (impact predictions auto-load using cache-first data)
2. Click **"🔄 Fetch Impact Predictions"** if you want to force a refresh
3. Wait for data retrieval (~5-10 seconds)

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

### Scientific References

- Vieira CLZ, et al. (2022). Geomagnetic disturbances are associated with reduced heart rate variability. *Sci Total Environ, 839*, 156312.
- Alabdulgader A, et al. (2018). Long-term study of HRV responses to changes in the solar and geomagnetic environment. *Sci Rep, 8*(1), 2663.
- McCraty R, et al. (2017). Synchronization of human autonomic nervous system rhythms with geomagnetic activity. *Int J Environ Res Public Health, 14*(7), 770.

---

## Space Weather Correlation

### Setting Up Space Weather Analysis

**Step 1: Configure HRV data**

1. Upload RR files with timestamp-named filenames
2. Ensure files span at least several days for meaningful correlation
3. Process through windowed analysis

**Step 2: Open Space Weather tab**

1. Navigate to **Space Weather** tab
2. The app auto-loads SWPC Kp/F10.7 data cache-first; click **"Fetch space weather data"** if you want to force a refresh
3. Data is cached for 6 hours; if offline, the last cached copy is shown with a warning

**Step 3: Configure correlation parameters**

1. Set lag range: start=0h, end=72h, step=6h
2. Enable/disable weather covariates (Bogotá temperature, humidity, pressure)
3. Select HRV metrics to correlate

**Step 4: Run correlation analysis**

1. Click "Compute correlations"
2. Review results table with:
   - Pearson r coefficient
   - p-value (statistical significance)
   - q-value (FDR-adjusted for multiple comparisons)
   - Optimal lag (hours before/after HRV measurement)

> **Weather covariates & partial r:** When you enable **Include weather covariates (Bogotá)** the app fetches ERA5 temperature, humidity, pressure, wind, precipitation, and cloud-cover from Open-Meteo for the exact HRV timestamps. Each correlation is then recomputed as a **partial Pearson r**, removing the shared variance explained by those weather variables. This isolates geomagnetic/solar effects from local meteorology so you can distinguish heliobiology signals from hot/cold-day confounders.

**Time alignment:** HRV windows and NOAA predictors are synchronized to the exact same timestamp before computing correlations—no nearest-neighbor merges. The app resamples solar/geomagnetic data onto the HRV window start times with bounded interpolation (default tolerance 90 min) so that each sample pair represents the same instant, mirroring the methodology recommended by McCraty et al. (2017) for peer-reviewed heliobiology studies.

### Interpreting Space Weather Correlations

**Correlation strength:**
| |r| | Interpretation |
|-----|----------------|
| <0.1 | Negligible |
| 0.1-0.3 | Weak |
| 0.3-0.5 | Moderate |
| 0.5-0.7 | Strong |
| >0.7 | Very strong |

**Statistical significance:**
| p-value | Interpretation |
|---------|----------------|
| <0.001 | Highly significant |
| 0.001-0.01 | Very significant |
| 0.01-0.05 | Significant |
| 0.05-0.10 | Marginally significant |
| >0.10 | Not significant |

**Example interpretation:**
```
Metric: RMSSD
Kp correlation: r = -0.24, p = 0.032, lag = 24h

Interpretation: Weak negative correlation between geomagnetic 
activity and vagal HRV, with effects appearing 24 hours after 
storm onset. Effect size is modest; individual sensitivity varies.
```

### NOAA Space Dashboard

**Available data feeds:**
| Feed | Description | Cadence |
|------|-------------|---------|
| Planetary Kp | Geomagnetic storm index | 3-hour |
| Dst | Ring current strength | Hourly |
| F10.7 | Solar radio flux | Daily |
| Solar wind | Speed, density, temp | Real-time |
| X-ray flux | Solar flare activity | 1-min |
| Proton flux | Radiation storm levels | 5-min |

Data auto-loads when you open the **NOAA Space** tab (cache-first). Use **Fetch NOAA feeds** to refresh, or **Force refresh NOAA feeds** to bypass cache. If NOAA is unreachable, the dashboard shows the last cached snapshot and posts a warning.

**Feature Matrix Builder:**

1. Click "Generate Feature Matrix"
2. Select HRV metrics and space weather predictors
3. Set lag range for each predictor
4. Click "Build Matrix"
5. Download CSV for external analysis

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

**Step 2: Configure work schedule**

1. Enable **Include work schedule**
2. Enter work start hour and work end hour
3. Set cognitive load (0–3)

**Step 3: Run prediction**

1. Click **🚀 Run Fatigue Prediction**
2. View hourly effectiveness chart
3. Review risk assessment
4. Read recommendations

### FRMS & USAF Upgrades (Safety Management Dashboard)

The SAFTE tab includes an aviation-grade **FRMS-style dashboard** aligned with ICAO guidance:

- **Predictive (model-based) fatigue risk** using SAFTE effectiveness.
- **WOCL exposure** (Window of Circadian Low, typically ~02:00–06:00 local).
- **Operational effectiveness thresholds** commonly used with SAFTE/FAST:
  - **≥90%**: low risk (“well-rested” baseline)
  - **>77–<90%**: caution / transitional range
  - **>70–≤77%**: high risk (often compared to ~0.05% BAC impairment)
  - **≤70%**: severe impairment (often compared to ~0.08% BAC impairment)
- **SMS-style risk matrix** classification (severity × likelihood) for structured decision support.

It also includes a **USAF crew rest check** (AFMAN 11-202V3 baseline):

- Crew rest typically requires **≥12 hours non-duty** before FDP with **≥8 hours uninterrupted sleep opportunity**.
- If crew rest is interrupted by official business, it must restart (update the “crew rest start” time accordingly).

### Exports (Publication-Grade)

The SAFTE tab provides exports for downstream reporting and publication workflows:

- **Predictions (CSV)**: full time series of DateTime, performance, and circadian drive.
- **FRMS dashboard payload (JSON)** and **FRMS summary (CSV)** for audit trails.
- **Plot exports (HTML, PNG, SVG, PDF)** via Plotly export fallback (static image export requires `kaleido`).

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

- International Civil Aviation Organization. (2016). *Manual for the Oversight of Fatigue Management Approaches* (Doc 9966, 2nd ed.). https://www.icao.int/safety/fatiguemanagement/FRMS%20Tools/Doc%209966.FRMS.2016%20Edition.en.pdf
- Department of the Air Force. (n.d.). *AFMAN 11-202V3: General Flight Rules.* https://static.e-publishing.af.mil/production/1/af_a3/publication/afman11-202v3/afman11-202v3.pdf
- Federal Aviation Administration. (2010). *Flightcrew Member Duty and Rest Requirements* (Docket No. FAA-2009-1093; Attachment 1). https://downloads.regulations.gov/FAA-2009-1093-2518/attachment_1.pdf
- National Aeronautics and Space Administration. (2012). *NASA–easyJet Collaboration on the Human Factors Monitoring Program (HFMP) Study* (NASA NTRS No. 20120013448). https://ntrs.nasa.gov/api/citations/20120013448/downloads/20120013448.pdf
- Federal Railroad Administration. (2006). *Validation and calibration of a fatigue assessment tool for railroad work schedules* (Final report; DOT/FRA/ORD-06/21). https://rosap.ntl.bts.gov/view/dot/62575

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

---

## Troubleshooting

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

10. Costa, M. D., Davis, R. B., & Goldberger, A. L. (2017). Heart rate fragmentation: A new approach to the analysis of cardiac interbeat interval dynamics. *Frontiers in Physiology, 8*, 255.

11. Guichard, J. B., et al. (2025). Assessing heart rate fragmentation to predict atrial fibrillation in the general population aged 65: the PROOF-AF study. *European Heart Journal Open*. https://doi.org/10.1093/ehjopen/oeaf030

### Fatigue Modeling

12. Hursh, S. R., Redmond, D. P., Johnson, M. L., et al. (2004). Fatigue models for applied research in warfighting. *Aviation, Space, and Environmental Medicine, 75*(3 Suppl), A44-A53.

13. Van Dongen, H. P., Maislin, G., Mullington, J. M., & Dinges, D. F. (2003). The cumulative cost of additional wakefulness: Dose-response effects on neurobehavioral functions and sleep physiology. *Sleep, 26*(2), 117-126.

### Basal Metabolic Rate & Nutrition

14. Mifflin, M. D., St Jeor, S. T., Hill, L. A., Scott, B. J., Daugherty, S. A., & Koh, Y. O. (1990). A new predictive equation for resting energy expenditure in healthy individuals. *American Journal of Clinical Nutrition, 51*(2), 241-247. https://doi.org/10.1093/ajcn/51.2.241

15. Harris, J. A., & Benedict, F. G. (1918). A biometric study of human basal metabolism. *Proceedings of the National Academy of Sciences, 4*(12), 370-373.

16. NASA Johnson Space Center. (2020). *Nutritional Requirements for Exploration Missions up to 365 days* (JSC67378). Houston, TX: NASA.

17. Scott, J. P. R., Green, D. A., Weerts, G., & Cheuvront, S. N. (2020). Body size and its implications upon resource utilization during human space exploration missions. *Scientific Reports, 10*, 13836. https://doi.org/10.1038/s41598-020-70054-6

### Clinical Scales (Validated Translations)

18. Chica-Urzola, H. L., Escobar-Córdoba, F., & Eslava-Schmalbach, J. (2007). Validación de la Escala de Somnolencia de Epworth. *Revista de Salud Pública, 9*(4), 558-567. https://doi.org/10.1590/S0124-00642007000400008

19. Velásquez-Paz, J. A., Torres, J. C., Valencia-Flores, M., et al. (2022). Validation of the Colombian version of the Karolinska sleepiness scale. *Sleep Science, 15*(Spec 1), 190-196. https://doi.org/10.5935/1984-0063.20220006

20. Samn, S. W., & Perelli, L. P. (1982). *Estimating aircrew fatigue: A technique with implications to airlift operations* (USAF-SAM-TR-82-21). Brooks Air Force Base, TX: USAF School of Aerospace Medicine.

### Kidney Function (eGFR)

21. Inker, L. A., Eneanya, N. D., Coresh, J., et al. (2021). New creatinine- and cystatin C-based equations to estimate GFR without race. *New England Journal of Medicine, 385*(19), 1737-1749. https://doi.org/10.1056/NEJMoa2102953

### Body Composition

22. Hodgdon, J. A., & Beckett, M. B. (1984). *Prediction of percent body fat for U.S. Navy men from body circumferences and height* (NHRC-84-11). San Diego, CA: Naval Health Research Center.

### Exploration Medical Records

23. NASA. (2023). *Medical Information Systems and Tools (MIST).* https://www.nasa.gov/general/medical-information-systems-and-tools-mist/

24. NASA Ames Research Center. (2024). *A Clinical Decision Support System for Earth-independent Medical Operations.* https://www.nasa.gov/centers-and-facilities/ames/ames-science/ames-space-biosciences/a-clinical-decision-support-system-for-earth-independent-medical-operations/

25. NASA Human Research Program. (2023). *Exploration Medical Capability - Advancing Medical System Design and Risk-Informed Decision Making for Deep Space Exploration.* NASA Technical Reports Server. https://ntrs.nasa.gov/citations/20230015831

26. NASA Glenn Research Center. (2024). *Exploration Medical Technologies.* https://www.nasa.gov/glenn/glenn-expertise-space-exploration/human-health-performance/exploration-medical-technologies/

### Space Radiation & Space-Weather Scales

27. National Aeronautics and Space Administration. (2022). *NASA Space Flight Human-System Standard, Volume 1: Crew Health* (NASA-STD-3001, Rev. B). NASA. https://www.nasa.gov/wp-content/uploads/2020/10/2022-01-05_nasa-std-3001_vol.1_rev._b_final_draft_with_signature_010522.pdf

28. Zhang, S., Berger, T., Matthiä, D., Hellweg, C. E., et al. (2020). First measurements of the radiation dose on the lunar surface. *Science Advances, 6*(39), eaaz1334. https://doi.org/10.1126/sciadv.aaz1334

29. Hassler, D. M., Zeitlin, C., Wimmer-Schweingruber, R. F., Ehresmann, B., et al. (2014). Mars' surface radiation environment measured with the Mars Science Laboratory's Curiosity rover. *Science, 343*(6169), 1244797. https://doi.org/10.1126/science.1244797

30. NOAA Space Weather Prediction Center. (n.d.). *Solar radiation storms (S-scale).* https://www.swpc.noaa.gov/phenomena/solar-radiation-storm

### API Integrations

31. Polar Electro. (2024). *Polar AccessLink API Documentation.* https://www.polar.com/accesslink-api/

32. Developer Tech News. (2014). *Polar opens its API for developers to access health data.* https://www.developer-tech.com/news/polar-opens-its-api-developers-access-user-health-data/

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
```

The application will be available at `http://localhost:8501`.

### Services

| Service | Port | Description |
|---------|------|-------------|
| **app** | 8501 | Streamlit application |
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

## Pending Developments and Roadmap

This section outlines completed features and remaining planned enhancements for the Mission Control - Flight Surgeon.

### Completed Features (Q4 2025)

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

### Remaining Enhancements

#### Plot Governance (ECharts-first, publication-grade everywhere)
**Status:** In progress (Priority: CRITICAL)  
**Description:** Enforce the project plotting policy across *all* tabs and modules.

- Standardize chart styling (titles, axis labels with units, legends, tooltips, colorblind-safe palette).
- Require a short explanatory paragraph beneath every plot (what the user sees, axis/units, preprocessing).
- Add publication-grade plot exports across the app (SVG/PNG high-DPI/HTML + data/spec export, plus PDF via browser print workflow).
- Keep `requirements.txt`, `README.md`, `docs/Manual.md`, and `CHANGELOG.md` updated whenever plots/features change.

**Current implementation note:** Every Apache ECharts chart now includes an inline export toolbar for **PNG (high-DPI)**, **SVG (vector)**, **HTML**, and **spec JSON** exports, plus **Print/Save PDF** using your browser’s print dialog.

#### Fatigue Safety Management (ICAO FRMS + USAF doctrine) inside SAFTE tab
**Status:** Implemented baseline + planned FRMS v2 (Priority: CRITICAL; research-first)  
**Description:** The SAFTE/Fatigue module now includes a baseline FRMS-style dashboard (with rule-based “why it triggered” alerts) plus USAF crew-rest compliance checks. The next milestone is **FRMS v2**: mission-level aggregation across *all profiles* with escalation + audit trail.

- ✅ ICAO-aligned FRMS summary + risk matrix, designed for deterministic “why it triggered” traceability.
- ✅ USAF crew rest compliance checks (AFMAN 11-202V3) with clear “compliant / waiver required / not compliant” outputs.
- ✅ Exportable evidence: FRMS JSON export and plot export workflows.
- 🔜 FRMS v2: mission-level roster + “crew risk board”, escalation rules, SPIs/trending, and an auditable decision log (inputs → classification → mitigation → outcome).

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
| Baroreflex sensitivity | Q1 2026 | Planned |
| Advanced nonlinear | Q1 2026 | Planned |
| ExMC CDSS / AI support | Q1 2026 | Planned |
| Mobile app | Q4 2026 | Conceptual |

---

*Last updated: December 3, 2025*
