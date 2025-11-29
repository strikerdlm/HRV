## HRV Analysis Suite — Complete User Manual

### Author

**Dr. Diego Malpica, MD**  
*Aerospace Medicine Specialist*  
National University of Colombia  
Physiology Instructor, Colombian Aerospace Force  
Researcher

---

This manual provides step-by-step instructions for all features of the HRV Analysis Suite with practical examples, interpretation guidance, and clinical/research best practices.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Data Preparation](#data-preparation)
3. [Uploading and Loading Data](#uploading-and-loading-data)
4. [Sidebar Configuration](#sidebar-configuration)
5. [Tab-by-Tab Guide](#tab-by-tab-guide)
6. [Autonomic Function Tests](#autonomic-function-tests)
7. [Space Weather Correlation](#space-weather-correlation)
8. [Fatigue Prediction (SAFTE Model)](#fatigue-prediction-safte-model)
9. [Biofeedback and Real-Time HRV](#biofeedback-and-real-time-hrv)
10. [Garmin Integration](#garmin-integration)
11. [ActiGraph GT3X Integration](#actigraph-gt3x-integration)
12. [Somfit Pro Integration](#somfit-pro-integration)
13. [AI-Powered Interpretation](#ai-powered-interpretation)
14. [Export and Publication](#export-and-publication)
15. [Metric Reference Tables](#metric-reference-tables)
16. [Troubleshooting](#troubleshooting)
17. [Scientific References](#scientific-references)
18. [Advanced ECG R-Peak Detection](#advanced-ecg-r-peak-detection)
19. [Multi-Modal Sensor Fusion](#multi-modal-sensor-fusion)
20. [Long-Term HRV Trending Analysis](#long-term-hrv-trending-analysis)
21. [Exercise HRV Analysis](#exercise-hrv-analysis)
22. [Machine Learning Predictions](#machine-learning-predictions)
23. [Real-Time BLE Integration](#real-time-ble-integration)
24. [Pending Developments and Roadmap](#pending-developments-and-roadmap)

---

## Getting Started

### System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.10 | 3.11+ |
| RAM | 4 GB | 8 GB |
| Storage | 500 MB | 1 GB |
| Browser | Chrome 90+ | Chrome/Edge latest |

### Installation Steps

**Step 1: Clone or download the repository**

```bash
git clone https://github.com/yourusername/hrv-space-weather.git
cd hrv-space-weather
```

**Step 2: Create a virtual environment (recommended)**

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

## Space Weather Correlation

### Setting Up Space Weather Analysis

**Step 1: Configure HRV data**

1. Upload RR files with timestamp-named filenames
2. Ensure files span at least several days for meaningful correlation
3. Process through windowed analysis

**Step 2: Open Space Weather tab**

1. Navigate to **Space Weather** tab
2. Click "Load SWPC Data" to fetch current solar/geomagnetic indices
3. Wait for data to load (cached for 6 hours)

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
   - Sleep quality (0-100%)
   - Prior sleep debt (hours)

**Step 2: Configure work schedule**

1. Check "Has work today"
2. Enter work start hour
3. Enter work duration
4. Select task type (low/medium/high cognitive demand)

**Step 3: Run prediction**

1. Click "Predict Fatigue"
2. View hourly effectiveness chart
3. Review risk assessment
4. Read recommendations

**Example scenario:**
```
Sleep: 11 PM - 6 AM (7 hours)
Quality: 80%
Prior debt: 2 hours
Work: 8 AM - 5 PM (9 hours)
Task: High cognitive demand

Results:
- Morning effectiveness: 85%
- Afternoon slump (2-4 PM): 65%
- End of day: 55%

Risk level: MODERATE
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

**For ZIP export:**

1. Go to sidebar → Garmin Import section
2. Click "Upload Garmin ZIP"
3. Select downloaded ZIP file
4. Wait for parsing (may take 30-60 seconds)
5. Review imported data summary

**For FIT files:**

1. Go to sidebar → Garmin Import section
2. Click "Upload FIT File"
3. Select `.fit` file
4. Review extracted RR intervals (if available)

### Available Garmin Data

| Data Type | What it contains | HRV use |
|-----------|-----------------|---------|
| Sleep | Stages, duration, scores | Overnight HRV context |
| HRV | Overnight RMSSD (5-min epochs) | Baseline trends |
| Heart Rate | Minute-level HR | RR interval derivation |
| Stress | Garmin stress score | Correlation with HRV |
| SpO2 | Pulse oximetry | Sleep apnea screening |
| Respiration | Breaths per minute | Breathing rate context |
| Body Battery | Energy level | Recovery tracking |

### Limitations

⚠️ **Optical sensor limitations:**
- Garmin Vivosmart 5 uses PPG (optical HR)
- Less accurate than chest strap for beat-level HRV
- Overnight HRV summaries are reasonable
- Beat-to-beat RR intervals may be limited

---

## ActiGraph GT3X Integration

### Overview

ActiGraph accelerometers (GT3X, GT3X+, GT9X Link) are research-grade wearable devices used for objective measurement of physical activity and sleep. The HRV Analysis Suite supports importing data from these devices to:

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

The HRV Analysis Suite imports Somfit data to analyze sleep-stage-specific HRV patterns and overnight autonomic function.

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

### Fallback Mode

If API is unavailable, the app provides:
- Rule-based interpretation
- Pre-defined thresholds
- Lower confidence score
- Core findings without nuance

---

## Export and Publication

### Generating Reports

**Step 1: Complete analysis**

1. Upload all relevant data files
2. Configure sidebar settings
3. Review all tabs for completeness

**Step 2: Go to Export tab**

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

11. PROOF-AF Study. (2025). Heart rate fragmentation and DFA α1 predict atrial fibrillation. *European Heart Journal Open, 5*(1), oeaf030.

### Fatigue Modeling

12. Hursh, S. R., Redmond, D. P., Johnson, M. L., et al. (2004). Fatigue models for applied research in warfighting. *Aviation, Space, and Environmental Medicine, 75*(3 Suppl), A44-A53.

13. Van Dongen, H. P., Maislin, G., Mullington, J. M., & Dinges, D. F. (2003). The cumulative cost of additional wakefulness: Dose-response effects on neurobehavioral functions and sleep physiology. *Sleep, 26*(2), 117-126.

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

## Pending Developments and Roadmap

This section outlines remaining planned enhancements and features under development for the HRV Analysis Suite.

### Completed Features (Q4 2025)

✅ **ECG R-Peak Detection** - Pan-Tompkins algorithm with template matching  
✅ **Multi-Modal Sensor Fusion** - Oura, WHOOP, Apple Health, Fitbit integration  
✅ **Long-Term Trending** - Baseline establishment, trend detection, alerts  
✅ **Exercise HRV Analysis** - HRR, parasympathetic reactivation, TRIMP  
✅ **ML Predictions** - AF risk, SCD stratification, sleep apnea screening  
✅ **Real-Time BLE Integration** - Polar H10/H9, Garmin, Wahoo support  

### Medium Priority Enhancements

#### Blood Pressure Variability (BPV) Integration
**Status:** Planned  
**Description:** Add support for continuous blood pressure monitoring data to analyze baroreflex sensitivity and BPV metrics.

- Import BP waveform data (Finapres, Portapres)
- Compute systolic/diastolic BPV
- Baroreflex sensitivity (sequence method, spectral)
- Cross-spectral HRV-BPV coherence

**Clinical relevance:** BPV complements HRV for comprehensive autonomic assessment.

#### Population Normative Database
**Status:** Planned  
**Description:** Expand reference ranges with age/sex/fitness-stratified normative data.

- Integrate published normative datasets
- Age-decade specific reference ranges
- Fitness-level adjustments (VO2max correlation)
- Disease-specific reference ranges
- Percentile rankings

#### Circadian Rhythm Analysis
**Status:** Planned  
**Description:** Tools for analyzing circadian patterns in HRV and physiology.

- Cosinor analysis for circadian rhythms
- Mesor, amplitude, acrophase extraction
- Circadian disruption indices
- Shift work impact assessment
- Jet lag recovery tracking

#### Advanced Nonlinear Dynamics
**Status:** Partially implemented  
**Description:** Additional nonlinear analysis methods for research applications.

- Multiscale entropy (MSE)
- Recurrence quantification analysis (RQA)
- Symbolic dynamics (word entropy)
- Correlation dimension
- Lyapunov exponents

**Current state:** DFA, SampEn, ApEn implemented; advanced methods pending.

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
| BPV integration | Q1 2026 | Planned |
| Circadian analysis | Q1 2026 | Planned |
| Population norms | Q2 2026 | Planned |
| Mobile app | Q4 2026 | Conceptual |

---

*Last updated: November 2025*
