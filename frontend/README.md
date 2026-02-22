# Author: Dr Diego Malpica MD

# Mission Control - Flight Surgeon (TypeScript Frontend)

Modern TypeScript/React frontend for the HRV Analysis Suite, providing a beautiful, smooth interface while keeping the Streamlit backend intact.

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Framework** | Next.js 14 | React framework with App Router |
| **Language** | TypeScript | Type safety |
| **UI** | shadcn/ui + Radix | Accessible components |
| **Styling** | Tailwind CSS | Utility-first styling |
| **Charts** | Apache ECharts | Publication-quality visualizations |
| **Animations** | Framer Motion | Smooth transitions |
| **State** | Zustand | Lightweight state management |
| **Backend** | FastAPI | REST API bridge to Python modules |

## Quick Start

### Prerequisites

- Node.js 18+ (LTS recommended)
- Python 3.12 with hrv-py312 conda environment
- The main HRV project requirements installed

### 1. Install Frontend Dependencies

```powershell
cd frontend
npm install
```

### 2. Start the FastAPI Backend

Open a new terminal:

```powershell
# From project root
conda activate hrv-py312
pip install fastapi uvicorn
uvicorn api.main:app --reload --port 8180
```

The API will be available at `http://localhost:8180`

### 3. Start the Frontend

```powershell
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:3100`

### Quick Start (Both at Once)

Use the included PowerShell script to start both services:

```powershell
.\start-frontend.ps1
```

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── page.tsx            # Dashboard
│   │   ├── scheduling/         # Crew Scheduling
│   │   ├── experiments/        # Experiments Management
│   │   ├── profile/            # User Profiles
│   │   ├── about/              # About page
│   │   └── research/           # Research Features (NEW)
│   │       ├── page.tsx        # Research Hub
│   │       ├── space-weather/  # Space Weather Dashboard
│   │       ├── hrv-analysis/   # HRV Analysis (all domains)
│   │       ├── workload/       # Cognitive workload (segment annotation)
│   │       ├── vigilance/      # Windowed vigilance tracker
│   │       ├── flight-fatigue/ # Flight fatigue classifier
│   │       ├── correlations/   # Solar-HRV Correlations
│   │       └── garmin/         # Garmin Wearable Data
│   ├── components/
│   │   ├── ui/                 # shadcn/ui components
│   │   ├── layout/             # Layout components (Sidebar, Header)
│   │   ├── charts/             # ECharts wrappers
│   │   ├── flight-surgeon-console.tsx  # NASA Flight Surgeon Console
│   │   ├── hydration-thermoregulation.tsx  # Hydration & Thermoregulation
│   │   ├── extreme-weather-calc.tsx  # Extreme Weather Assessment
│   │   ├── ice-station-monitor.tsx  # ICE Station Monitor
│   │   └── metar-dashboard.tsx  # METAR Weather Dashboard
│   ├── lib/
│   │   ├── api.ts              # Operational API client
│   │   ├── research-api.ts     # Research API client
│   │   ├── store.ts            # Zustand state store
│   │   └── utils.ts            # Utility functions
│   └── types/
│       ├── index.ts            # Operational TypeScript interfaces
│       └── research.ts         # Research TypeScript interfaces
├── package.json
├── tailwind.config.ts
└── tsconfig.json
```

## API Endpoints

### Operational Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/missions` | GET/POST | Mission workspace management |
| `/api/users` | GET/POST/DELETE | User profile CRUD |
| `/api/experiments` | GET/POST/DELETE | Experiment management |
| `/api/space-weather` | GET | Space weather snapshot |

### Research Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/research/space-weather/current` | GET | Full space weather with impact predictions |
| `/api/research/space-weather/noaa` | GET | NOAA data by source |
| `/api/research/hrv/latest/{user_id}` | GET | Latest HRV analysis for user |
| `/api/research/hrv/analyze` | POST | Analyze RR intervals |
| `/api/research/hrv/upload` | POST | Upload RR tracing with dedupe-aware persistence |
| `/api/research/hrv/tracings/{user_id}` | GET | List stored RR tracings for picker/load workflows |
| `/api/research/hrv/tracings/{user_id}/{measurement_id}` | GET | Load one stored RR tracing (RR values + cached analysis) |
| `/api/research/hrv/frequency/{user_id}` | GET | Frequency-domain analysis (Welch/Periodogram/AR/Lomb) |
| `/api/research/hrv/nonlinear/{user_id}` | GET | Nonlinear metrics with advanced RCMSE/MM-DFA gates |
| `/api/research/hrv/windowed/{user_id}` | GET | Sliding-window HRV trends and anomaly flags |
| `/api/research/workload/compute` | POST | Baseline/task/recovery workload reactivity metrics |
| `/api/research/vigilance/{user_id}` | GET | Windowed vigilance states with SAFTE overlay |
| `/api/research/flight-fatigue/{user_id}` | GET | Three-level flight fatigue classification |
| `/api/research/fusion/{user_id}` | GET | Integrated physiological fusion with uncertainty |
| `/api/research/models/calibration-report` | GET | Deployed model artifact metadata and calibration report |
| `/api/research/correlations/hrv-space-weather` | GET | HRV-Space Weather correlations |
| `/api/research/garmin/latest/{user_id}` | GET | Latest Garmin metrics |
| `/api/research/garmin/history/{user_id}` | GET | Garmin history (30 days) |
| `/api/research/garmin/sync/{user_id}` | POST | Sync data from Garmin Connect |

## Garmin Connect Integration

The frontend integrates with Garmin Connect via the [python-garminconnect](https://github.com/cyberjunky/python-garminconnect) library for fetching wearable health data.

### Configuration

Add your Garmin Connect credentials to the project root `.env` file:

```env
GARMIN_EMAIL=your_garmin_email@example.com
GARMIN_PASSWORD=your_garmin_password
```

**Security Note**: Never commit `.env` to version control. The `.gitignore` already excludes it.

### Token-Based Authentication (Recommended)

For accounts with MFA/2FA enabled, pre-generate authentication tokens:

1. Run the token generator once (interactive, handles MFA prompts):

```bash
conda activate hrv-py312
python tests/test_garmin_email.py
```

2. Tokens are saved to `~/.garminconnect/` and will be used automatically on subsequent syncs.

### Features Available

When properly configured, the Garmin page (`/research/garmin`) provides:

- **Real-time Sync**: Click "Sync Data" to fetch up to 90 days of metrics from Garmin Connect
- **Metrics Displayed**: Steps, resting HR, overnight HRV (RMSSD), SpO2, stress, respiration, Body Battery, sleep (duration, score, efficiency, stages)
- **History**: View trends over the last 7-30 days

### Troubleshooting

| Error | Solution |
|-------|----------|
| "GARMIN_EMAIL/GARMIN_PASSWORD not configured" | Add credentials to `.env` file |
| "MFA/2FA required" | Run `test_garmin_email.py` to generate tokens |
| "Rate limit reached" | Wait a few minutes before retrying |
| "Authentication failed" | Verify credentials, check for typos |

## Development

### Type Checking

```bash
npm run typecheck
```

### Linting

```bash
npm run lint
```

### Build for Production

```bash
npm run build
npm run start
```

## Features

### Operational Features

- **Dashboard**: Overview with stats, space weather widget, quick actions
- **Crew Scheduling**: Daily schedule management with crew status
- **Experiments**: Create and manage science protocols (max 10)
- **User Profiles**: Create, view, and manage crew profiles
- **About**: Author info, version, technology stack, references
- **Flight Surgeon Console** (NEW):
  - Nutritional requirements calculator (BMR + TEE with cold/altitude/activity factors)
  - Water requirements calculator with environmental adjustments
  - Altitude physiology monitor (SpO2, HR, AMS checklist)
  - 5 expandable scientific plots (energy breakdown, macronutrient radar,
    water stacked bar, altitude physiology, environmental stress heatmap)
  - Based on NASA-STD-3001 Vol. 2, adapted for analog missions
    (Antarctica, high-altitude stations, extreme environments)

### Research Features (NEW)

- **Research Hub**: Central dashboard linking all research modules
- **Quality-first interpretation layer**:
  - Shared `AnalysisContext` contract across research endpoints
  - Reusable `QualityPanel` in key pages (confidence, stationarity, validity, caveats)
- **Space Weather Dashboard**: 
  - Real-time Kp, Dst, F10.7, solar wind gauges
  - Impact predictions by energy category (photon, SEP, plasma, CME)
  - Polar H10 recording recommendations
  - Scientific context from Alabdulgader et al., Stoupel et al.
- **HRV Analysis**:
  - Time-domain metrics (SDNN, RMSSD, pNN50, etc.) from backend analysis endpoint
  - Frequency-domain with PSD method switching and Welch/Lomb compare mode
  - Nonlinear analysis with Poincaré plot (SD1, SD2, DFA α1, entropy)
  - Advanced nonlinear outputs (RCMSE/MM-DFA) when data sufficiency gates pass
  - Heart Rate Fragmentation (HRF): PIP, IALS, PSS, PAS
  - Global RR tracing loader in the research header for cross-page analysis consistency
  - Database-backed RR tracing catalog/detail APIs with dedupe-aware storage and cached analysis reuse
- **Cognitive Workload**:
  - Segment annotation (baseline/task/recovery) on RR trace
  - Reactivity metrics: `ΔlnRMSSD`, `ΔHF`, `ΔLF/HF`, recovery slope
  - Threshold flags for critical-role screening + JSON export
- **Vigilance Tracker**:
  - Calibrated sliding window vigilance state classification (default 30s/10s)
  - SAFTE effectiveness overlay and low-vigilance highlighting
- **Flight Fatigue Classifier**:
  - Calibrated low/moderate/high risk probabilities with model rationale
  - Required vs missing features visibility for transparent fallback behavior
- **Train/Infer split for cognition/fatigue models**:
  - Runtime inference loads offline artifact JSON files from `api/model_artifacts/`
  - Offline retraining utility: `api/train_research_models.py`
  - Calibration metadata endpoint for traceability: `/api/research/models/calibration-report`
- **Integrated Physiological Fusion**:
  - Log-linear factor fusion (schedule/autonomic/workload/environment)
  - Probability output with uncertainty interval and confidence labeling
- **Solar-HRV Correlations**:
  - Correlation heatmap (solar metrics vs. HRV parameters)
  - Lag analysis charts (0-72 hours)
  - Significance testing with p-values
  - Pattern insights and recommendations
- **Garmin Integration**:
  - SpO2 monitoring with gauge
  - Sleep architecture charts (deep, REM, light, awake)
  - Body Battery visualization
  - Respiration rates (awake/sleep)
  - Stress metrics and activity tracking

## Charts

The frontend uses Apache ECharts following the project's publication-quality standards:

- **Dark font colors** (never gray/light per `plots.mdc` rules)
- **Scientific color palette** for consistent visualization
- **Dynamic axis bounds** to prevent data clipping
- **Export toolbox** for PNG, SVG, and data view

### Example Usage

```tsx
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";

<EChartsWrapper
  option={{
    title: { text: "HRV Metrics" },
    xAxis: { type: "category", data: ["Mon", "Tue", "Wed"] },
    yAxis: { type: "value" },
    series: [{ type: "line", data: [120, 200, 150] }],
  }}
  height={380}
/>
```

## Relationship to Streamlit App

This TypeScript frontend is an **alternative UI** that coexists with:

- `app/` - Streamlit app (unchanged)

Both UIs share the same backend data via `api/main.py`.

## License

MIT License - See LICENSE for details.
