---
layout: default
title: HRV Analysis
---

# Comprehensive Heart Rate Variability (HRV) Analysis

## About

This project provides a comprehensive Jupyter notebook for analyzing Heart Rate Variability (HRV) using the best methods available in Python. Developed by Diego Malpica, MD for aerospace medicine research, this tool helps researchers and clinicians work with physiological data collected during space analog simulations and other research scenarios.

## Key Features

- **Time Domain Metrics**: SDNN, RMSSD, pNN50, and other statistical measures
- **Frequency Domain Metrics**: VLF, LF, HF powers, LF/HF ratio using power spectral density
- **Nonlinear Metrics**: Poincaré plot, DFA (Detrended Fluctuation Analysis), entropy measures
- **Autonomic Nervous System Analysis**: Parasympathetic and sympathetic indices
- **Comprehensive Visualization**: RR interval time series, power spectral density, Poincaré plots
- **Statistical Analysis**: Summary statistics, correlations, and group comparisons
- **Export Capabilities**: Save results to CSV for further analysis

## Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/strikerdlm/hrv-analysis.git

# Navigate to the project directory
cd hrv-analysis

# Install dependencies
pip install numpy pandas scipy matplotlib seaborn
pip install hrvanalysis  # Optional but recommended
```

### Usage

Open the Jupyter notebook:

```bash
jupyter notebook scripts/HRV_Comprehensive_Analysis.ipynb
```

The notebook includes:
1. Data loading functions for CSV files
2. Comprehensive HRV analysis functions
3. Visualization tools
4. Statistical summaries
5. Export capabilities

## Documentation

- [Installation Guide](Installation_Guide.md)
- [User Manual](User_Manual.md)
- [Scientific Discussion](Scientific_Discussion_Parasympathetic_Analysis.md)

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## Acknowledgments

- Centro de Telemedicina de Colombia
- Women AeroSTEAM
- Valquiria Space Analog Simulation team 