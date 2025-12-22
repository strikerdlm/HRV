---
layout: default
title: Mission Control - Flight Surgeon
---

# Mission Control - Flight Surgeon

## About

Mission Control - Flight Surgeon is a research-grade **Streamlit** application for Heart Rate Variability (HRV) analysis with integrated **circadian simulation**, **fatigue/FRMS tooling (SAFTE)**, and **space weather intelligence** (NOAA SWPC + NASA DONKI). It is designed for clinicians, researchers, and aerospace medicine use cases where outputs must be transparent, reproducible, and exportable.

## Key Features

- **Core HRV**: time/frequency/nonlinear metrics with QC and windowed analysis
- **Clinical + aerospace modules**: circadian physiology, fatigue/FRMS (SAFTE), exploration medical record tooling
- **Space weather**: NOAA SWPC feeds + NASA DONKI events with offline-friendly caching
- **Publication exports**: Markdown/CSV/JSON/LaTeX plus high-quality plot exports (ECharts-first)

## Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/strikerdlm/HRV.git

# Navigate to the project directory
cd HRV

# Install dependencies
python3 -m pip install -r requirements.txt
```

### Usage

Run the Streamlit application:

```bash
streamlit run app/app.py
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