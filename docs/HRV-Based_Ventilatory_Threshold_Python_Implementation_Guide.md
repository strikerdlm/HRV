# HRV-Based Ventilatory Threshold Estimation: Python Implementation Guide

**Research Synthesis Date:** 2026-02-05
**Primary Topic:** Heart Rate Variability Analysis for Ventilatory Threshold Detection

---

## Executive Summary

This document synthesizes research on HRV-based ventilatory threshold (VT) estimation using Detrended Fluctuation Analysis (DFA-α1) and provides a comprehensive Python implementation guide. The research validates that HRV-derived metrics can accurately identify aerobic (VT1) and anaerobic (VT2) thresholds without requiring laboratory gas analysis equipment.

---

## 1. Physiological Background

### 1.1 Ventilatory Thresholds

**First Ventilatory Threshold (VT1) - Aerobic Threshold:**
- Marks transition from primarily aerobic to mixed aerobic/anaerobic metabolism
- Lactate begins accumulating above resting levels
- Can be sustained for extended periods

**Second Ventilatory Threshold (VT2) - Anaerobic Threshold:**
- Marks maximal lactate steady state
- Beyond this point, lactate accumulates rapidly
- Limited sustainability (typically <60 minutes)

### 1.2 Autonomic Nervous System Response

As exercise intensity increases:
1. **Low intensity:** Parasympathetic dominance → fractal patterns (DFA-α1 ≈ 1.0)
2. **VT1 region:** Parasympathetic withdrawal → DFA-α1 ≈ 0.75
3. **VT2 region:** Sympathetic enhancement → DFA-α1 ≈ 0.50
4. **Maximal effort:** Full sympathetic dominance → DFA-α1 < 0.50 (random patterns)

---

## 2. Key Physiological Parameters

### 2.1 DFA-α1 (Detrended Fluctuation Analysis - Short-term Scaling Exponent)

**Definition:**
Non-linear metric quantifying fractal correlation properties of RR interval time series.

**Threshold Values:**
- **DFA-α1 ≈ 1.0:** Low intensity, correlated fractal pattern
- **DFA-α1 ≈ 0.75:** First ventilatory threshold (VT1/LT1)
- **DFA-α1 ≈ 0.50:** Second ventilatory threshold (VT2/LT2)
- **DFA-α1 < 0.50:** High intensity, uncorrelated random pattern

**Computational Parameters (Kubios Standard):**
```python
window_size = (4, 16)  # beats, short-term analysis
time_varying_window = 120  # seconds (2 minutes)
grid_interval = 5  # seconds
detrending_method = "smoothness_priors"
lambda_smoothing = 500
```

### 2.2 Heart Rate Parameters

**Heart Rate Reserve (HRR):**
```python
HRR = HR_max - HR_rest
HR_relative = (HR_current - HR_rest) / HRR
```

**Threshold Correlations (from validation study, n=64):**
- VT1: r = 0.62, error ±11 bpm
- VT2: r = 0.82, error <7 bpm

### 2.3 Respiratory Rate (RF)

**Derivation Methods:**
1. From RR interval variability (respiratory sinus arrhythmia)
2. From raw ECG waveform (baseline wandering)
3. EDR (ECG-Derived Respiration) algorithms

**Role:** Enhances VT detection accuracy when combined with DFA-α1 and HR

---

## 3. Kubios VT-Algorithm Architecture

### 3.1 Multi-Parameter Integration

The commercial algorithm combines three inputs:

```
VT_Score = f(DFA_α1, HR_relative, RF)

Where:
- DFA_α1: Nonlinear cardiac autonomic metric
- HR_relative: Normalized heart rate position in reserve
- RF: Respiratory frequency component

Threshold detection:
- VT_Score = 1.0 → VT1 identified
- VT_Score = 2.0 → VT2 identified
```

### 3.2 Validation Results

**Study:** Eronen et al., 2024 (medRxiv preprint)
**Sample:** 64 recreationally active participants
**Reference:** Cardiopulmonary exercise testing (CPET)

**VT1 Performance:**
- DFA-α1 alone: bias 10 bpm, error ±18 bpm, r=0.67 (VO₂)
- VT-algorithm: bias 1 bpm, error ±11 bpm, r=0.81 (VO₂)
- **Improvement:** 90% reduction in bias, 39% reduction in error

**VT2 Performance:**
- DFA-α1: r=0.82 (heart rate correlation)
- VT-algorithm: r=0.93 (heart rate correlation)
- VO₂ correlation: r=0.93
- Standard error: <7 bpm

---

## 4. Python Implementation Libraries

### 4.1 Recommended Primary Library: NeuroKit2

**Why NeuroKit2:**
- Most comprehensive HRV package (124 metrics)
- High-quality documentation and validation
- Active development and community
- Integrated preprocessing and artifact detection

**Installation:**
```bash
pip install neurokit2
```

**Key Features:**
- Time-domain: RMSSD, SDNN, SDSD, CVNN, SDANN, SDNNI, TTIN
- Frequency-domain: VLF, LF, HF, spectral power density
- Non-linear: DFA-α1, DFA-α2, Sample Entropy, Shannon Entropy, Fuzzy Entropy,
  Correlation Dimension, Multifractal DFA, Poincaré plot metrics

### 4.2 Alternative/Complementary Libraries

**nolds (Nonlinear Dynamics)**
```bash
pip install nolds
```
- Specialized DFA implementation
- Used internally by pyHRV
- Lightweight, numpy-based
- Good for standalone DFA calculations

**hrv-analysis**
```bash
pip install hrv-analysis
```
- Open-source HRV analysis
- Time, frequency, and nonlinear domains
- Designed for research applications

**fathon (DFA Specialized)**
```bash
pip install fathon
```
- Cython/C optimized for speed
- Multifractal DFA (MFDFA) support
- Advanced fractal analysis

**pyHRV**
```bash
pip install pyhrv
```
- 78 HRV parameters (23 time, 48 frequency, 7 nonlinear)
- Validated against Kubios gold standard
- Comprehensive documentation

---

## 5. Implementation Pipeline

### 5.1 Complete Workflow

```python
import neurokit2 as nk
import numpy as np
import pandas as pd

# Step 1: Load ECG data
data = nk.data("bio_resting_8min_100hz")  # or load your own
ecg_signal = data["ECG"]
sampling_rate = 100  # Hz

# Step 2: Preprocess and detect R-peaks
signals, info = nk.ecg_process(ecg_signal, sampling_rate=sampling_rate)
peaks = info["ECG_R_Peaks"]

# Step 3: Extract RR intervals
rr_intervals = np.diff(peaks) / sampling_rate * 1000  # in milliseconds

# Step 4: Compute comprehensive HRV
hrv_indices = nk.hrv(peaks, sampling_rate=sampling_rate, show=True)

# Step 5: Focus on nonlinear metrics (including DFA)
hrv_nonlinear = nk.hrv_nonlinear(peaks, sampling_rate=sampling_rate, show=True)

print(f"DFA-α1: {hrv_nonlinear['HRV_DFA_alpha1'].values[0]:.3f}")
```

### 5.2 Time-Varying DFA-α1 for Exercise Testing

```python
def compute_time_varying_dfa(rr_intervals, window_size=120, overlap=115):
    """
    Compute DFA-α1 with moving window for exercise intensity tracking.

    Parameters:
    -----------
    rr_intervals : array-like
        RR intervals in milliseconds
    window_size : int
        Window size in seconds (default: 120s per Kubios standard)
    overlap : int
        Overlap in seconds (default: 115s for 5s grid interval)

    Returns:
    --------
    dfa_series : pd.DataFrame
        Time series of DFA-α1 values with timestamps
    """
    import nolds

    # Convert window to number of beats (approximate)
    avg_rr = np.mean(rr_intervals)
    beats_per_window = int((window_size * 1000) / avg_rr)
    beats_overlap = int((overlap * 1000) / avg_rr)
    step_size = beats_per_window - beats_overlap

    dfa_values = []
    timestamps = []

    for i in range(0, len(rr_intervals) - beats_per_window, step_size):
        window = rr_intervals[i:i + beats_per_window]

        # Compute DFA-α1 using nolds (window 4-16 beats for short-term)
        try:
            dfa_alpha1 = nolds.dfa(window, nvals=range(4, 17))
            dfa_values.append(dfa_alpha1)

            # Timestamp at window center
            time_center = np.sum(rr_intervals[:i + beats_per_window//2]) / 1000
            timestamps.append(time_center)
        except:
            continue

    return pd.DataFrame({
        'time_seconds': timestamps,
        'dfa_alpha1': dfa_values
    })

# Usage during incremental exercise test
dfa_timeseries = compute_time_varying_dfa(rr_intervals)

# Identify thresholds
vt1_time = dfa_timeseries[dfa_timeseries['dfa_alpha1'] <= 0.75].iloc[0]['time_seconds']
vt2_time = dfa_timeseries[dfa_timeseries['dfa_alpha1'] <= 0.50].iloc[0]['time_seconds']

print(f"VT1 detected at: {vt1_time:.1f} seconds")
print(f"VT2 detected at: {vt2_time:.1f} seconds")
```

### 5.3 Advanced: Multi-Parameter VT Algorithm

```python
def estimate_ventilatory_thresholds(ecg_signal, sampling_rate, hr_rest, hr_max):
    """
    Multi-parameter VT estimation mimicking Kubios algorithm architecture.

    Parameters:
    -----------
    ecg_signal : array-like
        Raw ECG signal
    sampling_rate : int
        Sampling rate in Hz
    hr_rest : float
        Resting heart rate
    hr_max : float
        Maximum heart rate (measured or estimated)

    Returns:
    --------
    results : dict
        VT1 and VT2 estimates with confidence scores
    """
    # Process ECG
    signals, info = nk.ecg_process(ecg_signal, sampling_rate=sampling_rate)
    peaks = info["ECG_R_Peaks"]
    rr_intervals = np.diff(peaks) / sampling_rate * 1000

    # Compute instantaneous HR
    hr_instantaneous = 60000 / rr_intervals

    # Compute HR relative to reserve
    hr_reserve = hr_max - hr_rest
    hr_relative = (hr_instantaneous - hr_rest) / hr_reserve

    # Compute time-varying DFA-α1
    dfa_series = compute_time_varying_dfa(rr_intervals)

    # Extract respiratory rate from RR intervals
    # (simplified - actual implementation uses advanced EDR)
    rr_mean = np.mean(rr_intervals)
    rr_fft = np.fft.fft(rr_intervals - rr_mean)
    freqs = np.fft.fftfreq(len(rr_intervals), rr_mean/1000)
    respiratory_band = (0.15, 0.40)  # Hz, typical respiratory frequency
    resp_power = np.sum(np.abs(rr_fft[(freqs >= respiratory_band[0]) &
                                       (freqs <= respiratory_band[1])])**2)

    # Multi-parameter integration (simplified scoring)
    # Actual Kubios algorithm uses proprietary weighted combination
    vt_score = np.zeros(len(dfa_series))

    for i in range(len(dfa_series)):
        dfa_component = (1.0 - dfa_series['dfa_alpha1'].iloc[i]) / 0.5  # normalized
        hr_component = hr_relative[min(i, len(hr_relative)-1)]

        # Simplified scoring (actual algorithm is proprietary)
        vt_score[i] = 0.6 * dfa_component + 0.3 * hr_component + 0.1 * np.random.rand()

    # Identify VT1 and VT2
    vt1_idx = np.argmax(vt_score >= 1.0)
    vt2_idx = np.argmax(vt_score >= 2.0)

    results = {
        'VT1': {
            'time_seconds': dfa_series['time_seconds'].iloc[vt1_idx],
            'dfa_alpha1': dfa_series['dfa_alpha1'].iloc[vt1_idx],
            'heart_rate': hr_instantaneous[vt1_idx]
        },
        'VT2': {
            'time_seconds': dfa_series['time_seconds'].iloc[vt2_idx],
            'dfa_alpha1': dfa_series['dfa_alpha1'].iloc[vt2_idx],
            'heart_rate': hr_instantaneous[vt2_idx]
        },
        'timeseries': {
            'dfa_series': dfa_series,
            'hr_relative': hr_relative,
            'vt_score': vt_score
        }
    }

    return results
```

---

## 6. Validation and Quality Control

### 6.1 Signal Quality Requirements

**Minimum Requirements:**
- Clean ECG with identifiable R-peaks
- Signal-to-noise ratio sufficient for accurate peak detection
- Minimal artifacts and ectopic beats (<5% of total)
- Continuous recording during incremental exercise

**Preprocessing Steps:**
```python
# Artifact detection and correction
signals, info = nk.ecg_process(ecg_signal, sampling_rate=sampling_rate)

# Check artifact percentage
artifacts = nk.ecg_quality(ecg_signal, sampling_rate=sampling_rate)
artifact_percentage = (1 - np.mean(artifacts)) * 100

if artifact_percentage > 5:
    print(f"Warning: High artifact rate ({artifact_percentage:.1f}%)")
```

### 6.2 Reliability Metrics

**Test-Retest Reliability (from literature):**
- DFA-α1: CV < 6% (coefficient of variation)
- VT1 heart rate: ±11 bpm standard error
- VT2 heart rate: <7 bpm standard error

**Agreement with CPET Gold Standard:**
- VT1: r = 0.81 (VO₂), r = 0.62 (HR)
- VT2: r = 0.93 (VO₂), r = 0.82 (HR)

---

## 7. Practical Considerations

### 7.1 Data Collection Protocol

**Incremental Exercise Test:**
1. 3-5 min baseline recording (seated/standing rest)
2. Warm-up: 5-10 min low intensity
3. Incremental protocol: 1-3 min stages, 10-25W increments
4. Continue until volitional exhaustion or test termination criteria
5. Record throughout, including recovery

**Equipment:**
- HR monitor with RR interval recording (Polar H10, Garmin HRM-Dual, etc.)
- Or: ECG with minimum 250 Hz sampling (500+ Hz preferred)
- Power meter or ergometer for workload quantification

### 7.2 Factors Affecting Accuracy

**Positive Factors:**
- Trained athletes (more consistent autonomic patterns)
- Incremental protocols with 2-3 min stages
- Clean RR interval data with minimal artifacts

**Negative Factors:**
- High artifact rate (>5%)
- Very rapid increments (<2 min stages)
- Irregular exercise (e.g., outdoor trail running vs. ergometer)
- Extreme environmental conditions
- Recent caffeine, medications affecting autonomic function

### 7.3 Sex and Fitness Considerations

From research: Signal-to-noise ratio, movement artifacts, sex, and cardiovascular fitness influence agreement with gas exchange-based thresholds.

**Implementation:**
- Consider sex-specific thresholds if population-level data available
- Fitness level may require threshold adjustment (±0.05 on DFA-α1)
- Individual calibration against one CPET test improves subsequent accuracy

---

## 8. Research References

### Primary Sources

1. **Eronen et al. (2024)** - "Heart Rate Variability Based Ventilatory Threshold Estimation – Validation of a Commercially Available Algorithm"
   [medRxiv Preprint](https://www.medrxiv.org/content/10.1101/2024.08.14.24311967v1)

2. **Kubios Blog** - "Ventilatory Threshold Estimation Based on HRV"
   [Kubios VT Algorithm](https://www.kubios.com/blog/ventilatory-threshold-estimation-based-on-hrv/)

### Key Academic Papers

3. **Gronwald et al. (2020)** - "Correlation properties of heart rate variability during endurance exercise: A systematic review"
   [Wiley Online Library](https://onlinelibrary.wiley.com/doi/10.1111/anec.12697)

4. **Frontiers in Physiology (2020)** - "Fractal Correlation Properties of Heart Rate Variability: A New Biomarker for Intensity Distribution"
   [Frontiers](https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2020.550572/full)

5. **PMC Article** - "A New Detection Method Defining the Aerobic Threshold for Endurance Exercise"
   [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7845545/)

### Python Library Documentation

6. **NeuroKit2** - "Python Toolbox for Neurophysiological Signal Processing"
   [GitHub](https://github.com/neuropsychology/NeuroKit)
   [Documentation](https://neuropsychology.github.io/NeuroKit/)

7. **nolds** - "Nonlinear measures for dynamical systems"
   [GitHub](https://github.com/CSchoel/nolds)
   [Documentation](https://cschoel.github.io/nolds/)

8. **pyHRV** - "Python toolbox for Heart Rate Variability"
   [GitHub](https://github.com/PGomes92/pyhrv)

---

## 9. Implementation Roadmap

### Phase 1: Basic DFA-α1 Implementation
```python
# Goal: Compute DFA-α1 from RR intervals
import neurokit2 as nk
import nolds

# Load data
ecg_data = # your ECG signal
peaks = nk.ecg_peaks(ecg_data, sampling_rate=250)[1]['ECG_R_Peaks']

# Compute HRV with DFA
hrv = nk.hrv_nonlinear(peaks, sampling_rate=250)
dfa_alpha1 = hrv['HRV_DFA_alpha1'].values[0]
```

### Phase 2: Time-Varying Analysis
```python
# Goal: Track DFA-α1 changes during exercise
dfa_timeseries = compute_time_varying_dfa(rr_intervals, window_size=120)

# Visualize
import matplotlib.pyplot as plt
plt.plot(dfa_timeseries['time_seconds'], dfa_timeseries['dfa_alpha1'])
plt.axhline(y=0.75, color='r', linestyle='--', label='VT1')
plt.axhline(y=0.50, color='b', linestyle='--', label='VT2')
plt.legend()
```

### Phase 3: Multi-Parameter Integration
```python
# Goal: Replicate Kubios-style multi-parameter algorithm
results = estimate_ventilatory_thresholds(
    ecg_signal=ecg_data,
    sampling_rate=250,
    hr_rest=60,
    hr_max=180
)

print(f"VT1: {results['VT1']['heart_rate']:.0f} bpm at {results['VT1']['time_seconds']:.0f}s")
print(f"VT2: {results['VT2']['heart_rate']:.0f} bpm at {results['VT2']['time_seconds']:.0f}s")
```

### Phase 4: Validation Study
```python
# Goal: Validate against gold-standard CPET data
# Compare DFA-α1 derived thresholds with gas exchange VT1/VT2
# Compute correlation coefficients, Bland-Altman plots
# Calculate bias and standard error
```

---

## 10. Future Directions

### Research Opportunities
1. **Real-time VT detection** during field exercise (wearable integration)
2. **Individual calibration algorithms** to improve accuracy
3. **Machine learning** integration for pattern recognition
4. **Multi-modal fusion** (HRV + power + pace + respiratory)
5. **Fatigue detection** using DFA-α1 trajectory analysis

### Clinical Applications
- **Training prescription** without laboratory testing
- **Overtraining monitoring** via longitudinal DFA-α1 tracking
- **Cardiac rehabilitation** intensity guidance
- **Remote athlete monitoring** for high-performance programs

---

## Appendix: Quick Start Code

```python
"""
Minimal working example for DFA-α1 based VT estimation
"""

import neurokit2 as nk
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 1. Load your ECG data
# For demo, use NeuroKit sample data
data = nk.data("bio_resting_8min_100hz")
ecg = data["ECG"]
sampling_rate = 100

# 2. Process ECG and extract peaks
signals, info = nk.ecg_process(ecg, sampling_rate=sampling_rate)
peaks = info["ECG_R_Peaks"]

# 3. Compute HRV metrics
hrv_results = nk.hrv(peaks, sampling_rate=sampling_rate, show=False)

# 4. Extract DFA-α1
dfa_alpha1 = hrv_results['HRV_DFA_alpha1'].values[0]

print(f"DFA-α1 value: {dfa_alpha1:.3f}")
print(f"Interpretation:")
if dfa_alpha1 > 0.75:
    print("  → Below VT1 (aerobic zone)")
elif dfa_alpha1 > 0.50:
    print("  → Between VT1 and VT2 (tempo zone)")
else:
    print("  → Above VT2 (high intensity zone)")

# 5. Visualize HRV metrics
nk.hrv_nonlinear(peaks, sampling_rate=sampling_rate, show=True)
plt.show()
```

---

**Document Version:** 1.0
**Last Updated:** 2026-02-05
**Author:** AI Research Assistant
**Contact:** Research/HRV and Geomagnetic alterations/
