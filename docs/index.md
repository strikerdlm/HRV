---
layout: default
title: Mission Control - Flight Surgeon
---

# Mission Control - Flight Surgeon

## About

Mission Control - Flight Surgeon is a research-grade platform for Heart Rate Variability (HRV) analysis with integrated **circadian simulation**, **fatigue/FRMS tooling (SAFTE)**, **operator readiness fusion (OPI, PVT, IHPI)**, and **space weather intelligence** (NOAA SWPC + NASA DONKI). It is designed for clinicians, researchers, and aerospace medicine use cases where outputs must be transparent, reproducible, and exportable.

The platform is delivered through **two interfaces over one shared Python analysis core**:

1. **Primary (2026 →):** a Next.js 14 / TypeScript frontend over a FastAPI Python backend — the canonical application for all new features (OPI framework, in-platform PVT, research analytics, operational scheduling).
2. **Legacy:** the original Streamlit interface — retained for single-user / local research workflows; maintenance fixes only.

## Key Features

- **Core HRV**: time / frequency / nonlinear metrics with QC and windowed analysis
- **Operator readiness**: Operational Performance Indicator (OPI) framework, Psychomotor Vigilance Task (PVT-B / PVT-5 / PVT-10), Integrated Human Performance Index (IHPI)
- **Clinical + aerospace modules**: circadian physiology, fatigue/FRMS (SAFTE), exploration medical record tooling
- **Space weather**: NOAA SWPC feeds + NASA DONKI events with offline-friendly caching
- **Publication exports**: Markdown / CSV / JSON / LaTeX plus publication-quality plot exports (ECharts-first)

## Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/strikerdlm/HRV.git
cd HRV

# Python environment (shared by both stacks)
python3 -m pip install -r requirements.txt

# Frontend dependencies (primary stack)
cd frontend && npm install && cd ..
```

### Usage — primary stack (Next.js + FastAPI)

```bash
# Terminal 1: FastAPI backend
uvicorn api.main:app --reload --port 8180

# Terminal 2: Next.js frontend
cd frontend && npm run dev   # → http://localhost:3100
```

### Usage — legacy Streamlit (optional)

```bash
streamlit run app/research_app.py       # legacy local research workbench
streamlit run app/operational_app.py    # legacy local crew-facing workflows
```

If you use conda, activate the project environment first (see the root README for the current environment name and setup steps).

## Documentation

- **Quick start + highlights**: see the root [`README.md`](../README.md)
- **Full manual**: [`Manual.md`](Manual.md)
- **Future performance (2026)**: [`future_2026.md`](future_2026.md)
- [Scientific Discussion](Scientific_Discussion_Parasympathetic_Analysis.md)

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## Acknowledgments

- Centro de Telemedicina de Colombia
- Women AeroSTEAM
- Valquiria Space Analog Simulation team 