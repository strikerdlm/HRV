# Comprehensive Heart Rate Variability (HRV) Analysis

A complete Jupyter notebook for comprehensive HRV analysis using the best methods available in Python.

## Overview

This project provides a comprehensive Jupyter notebook (`scripts/HRV_Comprehensive_Analysis.ipynb`) that implements state-of-the-art HRV analysis methods including:

- **Time Domain Metrics**: SDNN, RMSSD, pNN50, NN50, NN20, and other statistical measures
- **Frequency Domain Metrics**: VLF, LF, HF powers, LF/HF ratio using Welch's method and periodogram
- **Nonlinear Metrics**: Poincaré plot (SD1, SD2), DFA (Detrended Fluctuation Analysis)
- **Autonomic Nervous System Analysis**: Parasympathetic and sympathetic indices, ANS balance
- **Comprehensive Visualization**: RR interval time series, power spectral density, Poincaré plots
- **Statistical Analysis**: Summary statistics, correlations, group comparisons

## Quick Start

### Installation

```bash
# Install required packages
pip install numpy pandas scipy matplotlib seaborn

# Optional: Install hrvanalysis library for additional metrics
pip install hrvanalysis
```

### Usage

1. Open the Jupyter notebook:
```bash
jupyter notebook scripts/HRV_Comprehensive_Analysis.ipynb
```

2. Load your data:
   - Modify the data loading section to point to your CSV files
   - Ensure your data has a heart rate column (e.g., `heart_rate [bpm]`)
   - Optional: Include grouping columns like `subject`, `Sol`, `condition`, etc.

3. Run all cells to perform comprehensive HRV analysis

## Data Format

Your input data should be a pandas DataFrame with:
- **Heart rate column**: `heart_rate [bpm]` or similar
- **Optional grouping columns**: `subject`, `Sol`, `condition`, etc.
- **Optional time column**: `timestamp` or `time [s/1000]`

Example:
```python
import pandas as pd

df = pd.DataFrame({
    'heart_rate [bpm]': [70, 72, 68, 75, ...],
    'subject': ['Subject1', 'Subject1', ...],
    'Sol': [1, 1, 2, 2, ...],
    'timestamp': pd.date_range('2023-01-01', periods=1000, freq='1s')
})
```

## Features

### Time Domain Analysis
- Mean NN intervals, SDNN, RMSSD
- pNN50, pNN20 (percentage of successive intervals differing by >50ms or >20ms)
- Heart rate statistics (mean, std, min, max)
- Coefficient of variation measures

### Frequency Domain Analysis
- Power spectral density using Welch's method
- VLF (0.0033-0.04 Hz), LF (0.04-0.15 Hz), HF (0.15-0.4 Hz) bands
- Normalized units and percentages
- LF/HF ratio for sympathovagal balance

### Nonlinear Analysis
- Poincaré plot metrics (SD1, SD2, ellipse area)
- Detrended Fluctuation Analysis (DFA α1, α2)
- Fractal scaling properties

### Autonomic Nervous System Indices
- Parasympathetic index (based on HF power, RMSSD, pNN50, SD1)
- Sympathetic index (based on LF/HF ratio)
- ANS balance score

### Visualization
- RR interval time series plots
- Power spectral density plots with frequency band markers
- Poincaré plots with SD1/SD2 ellipses
- Correlation heatmaps of HRV metrics

## Output

The notebook generates:
1. **Comprehensive HRV metrics** as a pandas DataFrame
2. **Visualizations** for each analysis segment
3. **Summary statistics** and group comparisons
4. **CSV export** of all computed metrics

## Requirements

- Python 3.7+
- numpy
- pandas
- scipy
- matplotlib
- seaborn
- hrvanalysis (optional, for additional metrics)

## References

1. Task Force of the European Society of Cardiology. (1996). Heart rate variability: standards of measurement, physiological interpretation, and clinical use. *Circulation*, 93(5), 1043-1065.

2. Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability metrics and norms. *Frontiers in public health*, 5, 258.

3. Malik, M., et al. (1996). Heart rate variability: Standards of measurement, physiological interpretation, and clinical use. *European Heart Journal*, 17(3), 354-381.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Diego Malpica, MD  
Aerospace and Physiology Research

## Acknowledgments

- Centro de Telemedicina de Colombia
- Women AeroSTEAM
- Valquiria Space Analog Simulation team

