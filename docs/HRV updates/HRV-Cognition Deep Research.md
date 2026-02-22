# HRV–Cognition Integrated Model: Deep Research Evidence for Next Development Phases

## 1. Theoretical Foundation: Neurovisceral Integration and the Central Autonomic Network

### 1.1 Thayer-Lane Neurovisceral Integration Model

The foundational model linking HRV to cognition is the **neurovisceral integration model** (Thayer & Lane, 2000), which proposes that heart rate variability — particularly vagally mediated HRV (vmHRV) — indexes prefrontal cortical function and the integrity of the Central Autonomic Network (CAN). The CAN comprises interconnected cortical and subcortical structures (prefrontal cortex, amygdala, insula, cingulate, hypothalamus, brainstem nuclei) that regulate both cardiac autonomic control and cognitive-emotional processing.[^1][^2]

Neuroimaging evidence from Wei et al. (2018) demonstrated that **structural covariance of prefrontal-amygdala pathways** is directly associated with individual differences in HRV. Gray matter volume covariance patterns of the amygdala encompassed large portions of cortical regions (prefrontal, cingulate, insula) and subcortical regions (striatum, hippocampus, midbrain), providing anatomical evidence that the amygdala is a pivotal node in neural pathways for HRV modulation.[^1]

**Implementation relevance**: The model predicts that higher resting vmHRV reflects more flexible, top-down prefrontal regulation → better executive function, attention, and cognitive flexibility. This is the theoretical justification for treating vmHRV as a *risk factor/resilience marker* in Mission Control.

### 1.2 Polyvagal Theory (Porges)

Porges' Polyvagal Theory (PVT, 2006; revisited 2025) provides a complementary evolutionary framework. Porges demonstrated that **higher baseline HRV was associated with more stable reaction time performance**, particularly during tasks involving unpredictable timing demands. Critically, Porges established HRV as an "intervening variable" — a physiological mediator linking psychological challenge to behavioral output. HRV suppression during cognitive tasks indexes mental effort, with low variability reflecting heightened neural engagement.[^3][^4]

**Key computational insight**: Within-task HRV suppression (reactivity) is more informative than resting HRV alone for predicting cognitive performance. Implement as `delta_lnRMSSD = task_lnRMSSD - baseline_lnRMSSD`.

***

## 2. Longitudinal Evidence: HRV Predicts Cognitive Decline

### 2.1 UK Biobank Longitudinal Study (Jandackova et al., 2024)

The most robust longitudinal evidence comes from a large UK study using **linear mixed-effects models** (N > 5,000, aged 44–69, 10-year follow-up):[^5]

- **Low RMSSD** (lowest quintile) was associated with **0.07 SD faster 10-year cognitive decline** (β = −0.07, 95% CI: −0.13 to −0.01; p = 0.018)
- **Low HF-HRV** associated with **0.06 SD faster decline** (β = −0.06, 95% CI: −0.12 to −0.004; p = 0.037)
- This translates to cognitive aging equivalent: low RMSSD → **3.5 years faster cognitive aging per decade**; low HF-HRV → **3 years faster**[^5]
- Sensitivity analysis: RMSSD β = −0.08 (95% CI: −0.14 to −0.01; p = 0.036)
- **RMSSD was more robust than HF-HRV** across sensitivity analyses
- Vocabulary decline was most strongly linked; reasoning capacity marginally linked to low RMSSD[^5]

**LME Model Structure** (for Cursor implementation):
```
Cognition_score ~ HRV_quintile * Time + Age + Sex + Education + Ethnicity + (1 | Subject)
```

### 2.2 MESA Study (Schaich et al., 2020)

The **Multi-Ethnic Study of Atherosclerosis** (N = 3,018; mean age 59.3 ± 9.2 years) found:[^6]

| HRV Metric | Cognitive Test | β per 2-fold HRV increase | 95% CI | Timepoint |
|---|---|---|---|---|
| SDNN | CASI (global cognition) | 0.37 | 0.06, 0.67 | Exam 1 |
| SDNN | Digit Symbol Coding (processing speed) | 0.80 | 0.17, 1.43 | Exam 1 |
| SDNN | Digit Span (working memory) | 0.17 | 0.01, 0.33 | Exam 5 |
| RMSSD | Digit Symbol Coding | 0.54 | 0.01, 1.08 | Exam 5 |

Adjustments included: age, race/ethnicity, sex, education, APOE genotype, and cardiovascular risk factors. Associations were attenuated after adjustment for resting heart rate, suggesting HR partially mediates the HRV-cognition link.[^6]

### 2.3 Meta-Analytic Evidence (Magnon et al., 2022)

A 2022 systematic review/meta-analysis of correlational studies found:[^7]

- **Pooled effect r = 0.19** (95% CI: 0.15–0.23) between vmHRV and executive functioning
- vmHRV predicted **inhibition and cognitive flexibility** more than working memory
- Moderated by HRV measure type and age
- **Small but robust effect** — vmHRV is a risk factor/resilience marker, not a deterministic cognition meter

***

## 3. Nonlinear HRV Complexity for Cognitive State Discrimination

### 3.1 RCMSE and MM-DFA (Bouny et al., 2021)

This study is the most directly implementable evidence for your nonlinear module. Bouny et al. (2021) demonstrated that **entropy and multifractal markers outperformed classical HRV** (RMSSD, LF, HF, LF/HF) for discriminating cognitive tasks:[^8]

**Experimental Design**: N = 37 students; Stroop (cognitive interference), Stop-Signal (action cancellation), Go/No-Go (action restraint) vs. baseline (neutral documentary); Polar H10; ~8 min per task; 400–600 RR samples.

**RCMSE (Refined Composite Multiscale Entropy)**:
```
RCMSE(x, τ, m, r) = -ln[∑_{k=1}^{τ} n_{k,τ}^{m+1} / ∑_{k=1}^{τ} n_{k,τ}^{m}]
```
Parameters: m = 2, r = 0.15 × SD, scales τ = 1–4 (preserves >120 samples/scale).
**Entropy index** Ei = area under RCMSE curve (trapezoidal rule).[^8]

**MM-DFA (Multifractal-Multiscale Detrended Fluctuation Analysis)**:
1. Integrate: y(k) = Σ(RR_i − mean(RR))
2. Split into n-sized overlapping blocks
3. Detrend (1st-order polynomial)
4. F_q(n) = [1/M Σ σ_{n,k}^{2q}]^{1/q}
5. α(q,n) = local slope of log F_q vs log n
6. MFi(n) = std[α(q,n)] across q values
7. **MFI** = area under MFi(n=10→17s) curve[^8]

**Results**:

| Metric | Baseline | Stroop (interference) | Stop-Signal (cancel) | Go/No-Go (restraint) |
|---|---|---|---|---|
| **Ei** (entropy index) | 5.96 ± 0.35 | **6.20 ± 0.22*** | 6.01 ± 0.34 | 6.03 ± 0.37 |
| **MFI** (multifractal index) | 0.46 ± 0.20 | 0.48 ± 0.24 | **0.64 ± 0.44*** | 0.39 ± 0.18 |
| RMSSD | 43.3 ± 18.9 | 42.0 ± 18.1 | 45.3 ± 21.1 | 44.7 ± 21.7 |
| LF/HF | 2.25 ± 1.69 | 2.62 ± 1.95 | 2.23 ± 1.19 | 2.23 ± 1.51 |

*p < 0.01 vs baseline

**ROC Analysis (discrimination vs baseline)**:

| Index | Stroop AUC | SST AUC | GNGT AUC |
|---|---|---|---|
| **Ei** | **0.69** | 0.53 | 0.56 |
| **MFI** | 0.52 | **0.58** | **0.61** |
| RMSSD | 0.53 | 0.51 | 0.50 |
| LF/HF | 0.56 | 0.45 | 0.49 |
| Mean RR | 0.55 | 0.51 | 0.52 |

**Key finding**: Entropy detects cognitive interference (Stroop-like attention tasks); multifractality detects action inhibition/cancellation. Classical HRV metrics fail to distinguish cognitive states.[^8]

**Preprocessing pipeline for implementation**:
```
RR → Artifact correction (<1% manual interpolation)
  ↓
Empirical Mode Decomposition → Remove trend
  ↓
RWS stationarity test (~40% stationary)
  ↓
RCMSE + MM-DFA computation
```

**Surrogate validation**: Shuffled surrogates distinguish complexity from white noise. IAAFT (phase-randomized) surrogates detect nonlinearities in 40–60% of participants for entropy and 20–35% for multifractality.[^8]

### 3.2 Entropy Under Mental Load (Linear + Nonlinear Analysis)

Research combining linear and nonlinear HRV analyses under mental load confirmed that **SampEn, Poincaré SD1/SD2, and B parameters are effective sensitivity indicators** for detecting mental load (p < 0.01 for subjective questionnaire scores, p < 0.05 for time perception error rates). Mental stress typically decreases HRV complexity (including entropy features), while relaxation increases it.[^9][^10]

***

## 4. Sliding-Window Real-Time HRV–Vigilance Tracking

### 4.1 Xie & Ma (2025) — 30-Second Sliding Window

The most directly implementable real-time approach comes from Xie & Ma (2025), published in *Sleep*:[^11]

**Design**: 44 healthy adults; Psychomotor Vigilance Tasks (PVT); well-rested and sleep-deprived conditions; simultaneous ECG.

**Sliding Window Parameters**:
- Window length: **30 seconds**
- Step size: **10 seconds**
- Feature extraction per window: time-domain HRV features

**Ground Truth**: Behavioral performance classified per window:
- High vigilance (fastest 40%)
- Intermediate (middle 20%)
- Low vigilance (slowest 40%)

**ML Classifiers**: k-NN, SVM, AdaBoost, Random Forest

**Results**:
- **SVM achieved 89% accuracy** for binary classification (high vs low vigilance)
- Three-class leave-one-participant-out CV: **72% overall accuracy**
- SVM maintained **84% precision for low-vigilance epochs**
- Temporary performance decrements associated with **decreased HR and increased time-domain HRV**[^11]

**Implementation specification for Mission Control**:
```python
def sliding_vigilance_hrv(rr_intervals, window_sec=30, step_sec=10):
    features_list = []
    timestamps = np.cumsum(rr_intervals)
    for start in np.arange(0, timestamps[-1] - window_sec, step_sec):
        end = start + window_sec
        mask = (timestamps >= start) & (timestamps < end)
        window_rr = rr_intervals[mask]
        if len(window_rr) < 10:
            continue
        features = extract_time_domain(window_rr)  # RMSSD, SDNN, pNN50, mean_HR
        features_list.append(features)
    return np.array(features_list)
```

### 4.2 ICU Mortality Prediction — Multi-Window Validation (David et al., 2025)

A 2025 study validated HRV indices extracted from **sliding windows of 2, 5, and 7 minutes** across observation periods, demonstrating that window length materially impacts HRV reliability and downstream predictions.[^12]

***

## 5. Bayesian State-Space Modeling for Autonomic Outflow

### 5.1 Rosas et al. (2023) — Bayesian at Heart

This framework represents a paradigm shift for HRV analysis and is directly relevant for Mission Control's advanced analytics module:[^13][^14]

**Core Concept**: Instead of treating heart rate as a point estimate from IBIs, model it as a **hidden stochastic process** that drives observed heartbeats, using Bayesian inference to obtain posterior distributions.

**Generative Model** (Markovian state-space):
\[
p(x_{1:T}, z_{1:T}) = p(z_1) \; p(x_1|z_1) \prod_{t=2}^{T} p(z_t|z_{t-1}) \; p(x_t|z_t)
\]

Where:
- \(z_t\) = hidden heart rate process (Gamma Markov Chain)
- \(x_t\) = observed heartbeat counts (Poisson distributed)
- Auxiliary variables \(y_t\) for tractable inference[^13]

**GMC Dynamics**:
\[
z_1 \sim \mathcal{G}(\alpha_1, \beta_1), \quad y_t|z_{t-1} \sim \text{IG}(\gamma, \gamma z_{t-1}), \quad z_t|y_t \sim \mathcal{G}(\gamma, \gamma/y_t)
\]

**Posterior Inference**: Gibbs sampler (MCMC); N_r = 20,000 iterations; discard first N_d = 5,000; N_s = 100 trajectories.

**Bayesian Estimator** for any property F:
\[
\hat{F} = \mathbb{E}_{p(z|x)}[F(z)] \approx \frac{1}{N_s} \sum_{i=1}^{N_s} F(z^{(i)})
\]

**Key Results** (tilt-table validation, 10 subjects):

| Metric | Frequentist | Bayes θ=0.01 | Bayes θ=1 |
|---|---|---|---|
| Mean HR discrimination | Strong (z > 9) | Comparable | Comparable |
| HF-HRV discrimination | Moderate (all **) | **Stronger** (all **/***)  | Weak |
| Permutation Entropy | Not significant | Not significant | **Strong** (***) |
| Hurst Exponent (DFA) | Marginal | Weak | **Strongest** (***) |

The Bayesian model with θ = 1 **reveals complexity effects that frequentist methods miss entirely**.[^13]

**GitHub Implementation**: [github.com/ferosas/BayesianAtHeart](https://github.com/ferosas/BayesianAtHeart) — Python, uses Fathon (DFA/Hurst), Ordpy (permutation entropy).[^14]

### 5.2 Bayesian HRV + Cognitive Performance (Sepúlveda-Figueroa et al., 2026)

A January 2026 study used **Bayesian hierarchical modeling** with high-resolution HRV data to demonstrate that cognitive status (evaluated via Addenbrooke's Cognitive Examination) exerts selective influence on autonomic dynamics. The effect was most pronounced in **LF, VLF, and composite PNS index**, both at baseline and during physiological stress.[^15]

***

## 6. Flight Fatigue and Pilot Mental Workload Classification

### 6.1 Guo et al. (2025) — Flight Fatigue Three-Level Classification (N = 90 Pilots)

The most clinically relevant pilot study for Mission Control:[^16][^17]

**Population**: 90 male Chinese military pilots; mean age 31.6 ± 6.8; 896 ± 131 flight hours.

**Protocol**: Chest strap ECG (SensEcho, 200 Hz) + respiratory signals during **actual flight operations** (not simulator). Baseline seated ECG; post-flight 5-min ECG. 392 sessions total. Flight durations up to 120 min. Jet fighter operations.

**Fatigue Classification** (RPE-based):
- Non-fatigue: RPE 6–10
- Mild fatigue: RPE 11–16
- Severe fatigue: RPE 17–20

**Selected Features** (12 HRV + 1 respiratory, statistically significant p < 0.05):
Mean HR, Mean RR, SDNN, RMSSD, pNN50, pNN20, LF, HF, LF/HF, LFn, HFn, SD1/SD2, Mean Rsp

**ML Results** (10-fold subject-level CV):

| Model | Accuracy | Precision | Recall | F1 Score |
|---|---|---|---|---|
| LightGBM | **0.886 ± 0.057** | **0.837 ± 0.064** | **0.861 ± 0.086** | **0.849 ± 0.067** |
| SVM | Lower | Lower | Lower | Lower |
| KNN | Lower | Lower | Lower | Lower |
| DT | Lower | Lower | Lower | Lower |

**Confusion Matrix (LightGBM)**: Non-fatigue prediction 92.82% accuracy; severe fatigue 81.60% accuracy. Main confusion: mild ↔ severe fatigue (15.34% misclassification).[^17]

**Critical advantages**: Single-lead ECG chest strap; validated during actual flight (not simulator); comparable to EEG-based methods (0.8–0.9 accuracy) with far superior operational feasibility.[^17]

### 6.2 Yuan et al. (2025) — A320 Traffic Pattern Mental Workload

A separate study on A320 traffic pattern workload (N = 20 pilot cadets) identified **4 key HRV features** via Kruskal-Wallis + RF importance:[^18]

| Feature | Significance (p) | RF Importance |
|---|---|---|
| Min_HR | 0.017 | 0.04573 |
| SD2 | 0.046 | 0.03467 |
| SDNN | 0.044 | 0.03369 |
| Modified_csi | 0.026 | 0.03250 |

XGBoost achieved **66.67% accuracy** (5-class) with these 4 features — a 16.58% improvement over using all 30 features. Flight performance scores correlated with workload (r = −0.73, p < 0.01).[^18]

**Phase-specific HRV dynamics**:

| Feature | Takeoff | Climb | Cruise | Descent | Landing |
|---|---|---|---|---|---|
| Min_HR (bpm) | 76.85 | 59.98 | 41.86 | 71.88 | **78.75** |
| SDNN (ms) | 29.54 | 89.09 | **263.42** | 43.12 | **21.49** |
| SD2 (ms) | 37.57 | 117.01 | **357.82** | 54.52 | **26.51** |
| Performance Score | 85.4 | 90.5 | **92.9** | 87.9 | **82.9** |

Landing = highest workload (lowest SDNN, SD2, performance); Cruise = recovery (highest SDNN, SD2, performance).[^18]

***

## 7. Cognitive Load Prediction with Multimodal Features

### 7.1 MIT Lincoln Laboratory (Rao et al., 2020)

VR marksmanship with embedded working memory task (N = 8):[^19]

- **Random Forest, AUC = 0.94** for cognitive load classification (3 vs 6 digits)
- **Individual modality AUCs**: Gait = 0.947; Speech = 0.775; Heart/Breathing = 0.564; Body/Rifle = 0.507
- Heart rate alone was insufficient; **multimodal fusion is essential**
- Key cardiac features: HR, HRV, RMSSD, pNN50, breathing rate (computed per trial phase)
- Leave-one-subject-out cross-validation
- Digit recall prediction: AUC = 0.711; Marksmanship performance: AUC = 0.576[^19]

**Implication for Mission Control**: HRV should be combined with behavioral proxies (flight performance metrics, eye-tracking, or speech features) for robust workload inference.

***

## 8. Heart Rate Fragmentation (HRF) — Cognitive Decline Biomarker

### 8.1 Costa & Goldberger (2019, 2021)

Heart Rate Fragmentation (HRF) resolves the "HRV paradox" by revealing two mechanisms of short-term HR fluctuations:[^20][^21]

1. **Physiologic vagal tone modulation** → marker of intact heart rate control
2. **Sinus rhythm fragmentation** → marker of breakdown

Key metrics:
- **PIP** (Percentage of Inflection Points): density of sign changes in ΔRR
- **IALS** (Inverse of Average Length of Acceleration/Deceleration Segments)
- **PSS** (Percentage of Short Segments)

**Evidence for cognition**:
- HRF is **independently associated with cognitive performance and future cognitive decline** in MESA[^20]
- Increased HRF during sleep was associated with **diminished concurrent and future cognitive performance** and greater cognitive decline[^22]
- HRF was associated with **brain small vessel disease** (greater white matter hyperintensity volume, lower white matter fractional anisotropy on MRI)[^20]
- **ΔHRF** (before-after sleep) decreased with age and predicted incident major adverse cardiovascular events[^20]

**PhysioNet implementation**: Software for computing HRF available at physionet.org/content/heart-rate-fragmentation-code/ v1.0.0.[^20]

**Implementation in Mission Control**: Add HRF metrics alongside existing PIP/IALS/PSS (already in v1.16.0 per your file). Use sleep-derived ΔHRF as a longitudinal cognitive resilience marker.

***

## 9. Respiration Correction and Cardiorespiratory Coupling

### 9.1 ECG-Derived Respiration (EDR)

NeuroKit2 provides a complete EDR pipeline:[^23][^24]

```python
import neurokit2 as nk
# Extract peaks
rpeaks, info = nk.ecg_peaks(ecg, sampling_rate=1000)
ecg_rate = nk.ecg_rate(rpeaks, sampling_rate=1000, desired_length=len(ecg))
# ECG-derived respiration
edr = nk.ecg_rsp(ecg_rate, sampling_rate=1000)
```

Methods available: Van Gent et al. (2019) (default), Charlton et al., and others.[^24]

PhysioNet also provides a C program for EDR based on measuring mean cardiac electrical axis variations correlated with respiration.[^25]

### 9.2 Adaptive Noise Cancellation (ANC) for Respiration Removal

Cassani et al. (2013) demonstrated an ANC structure that cancels respiration influence from HRV signals, achieving **improved PSD estimation** of ANS control without affecting other frequency components. Effective for both spontaneous and controlled respiration.[^26]

### 9.3 Cardiopulmonary Resonance Function (CRF/CRI)

Cui et al. (2020) proposed modeling RSA as modulation of HR by respiration using **spectral Granger causality** to disentangle RR-intervals into:[^27]
- **R-HRV**: Respiratory-modulation component
- **NR-HRV**: Non-respiratory component

CRI showed superior representation ability compared to standard HRV and Cardiopulmonary Coupling index in paced breathing and sleep stages.[^27]

### 9.4 RSA Computation in NeuroKit2

NeuroKit2 provides RSA calculation with configurable windows:[^28]

```python
ecg_signals, info = nk.ecg_process(data["ECG"], sampling_rate=100)
rsp_signals, _ = nk.rsp_process(data["RSP"], sampling_rate=100)
rsa = nk.hrv_rsa(ecg_signals, rsp_signals, info, 
                  sampling_rate=100, continuous=False)
# Returns: RSA_P2T_Mean, RSA_P2T_SD, RSA_Gates_Mean_log, etc.
```

For continuous RSA estimation: `continuous=True`, window = 32s default, window_number = 8.[^28]

***

## 10. Information-Theoretic Approaches: Transfer Entropy

### 10.1 HR–RR Transfer Entropy as Biomarker (Keshmiri et al., 2024)

Transfer entropy (TE) between heart rate and respiratory rate provides a **two-dimensional biomarker** of cardiorespiratory physiology:[^29]

- **RR → HR** transfer entropy correlated with alcohol consumption and exercise habits
- Active Information Storage (AIS) of HR captured age correlations more clearly than linear AR models
- Implemented in Python using **JIDT library v1.5** (KSG-based algorithms)[^29]

```python
# Using JIDT for transfer entropy
from jpype import *
startJVM(getDefaultJVMPath(), "-ea", 
         f"-Djava.class.path=infodynamics.jar")
teCalc = JClass("infodynamics.measures.continuous.kraskov.TransferEntropyCalculatorKraskov")()
teCalc.initialise(1, 1, 1, 1, 1)
teCalc.setObservations(hr_array, rr_array)
te_result = teCalc.computeAverageLocalOfObservations()
```

### 10.2 Decreased Cardiorespiratory Information Transfer in Pathology (Morandotti et al., 2025)

Morandotti et al. (2025) demonstrated that **decreased cardio-respiratory information transfer** (measured by TE) is associated with pathological conditions, validating TE as a clinically relevant biomarker.[^30]

***

## 11. Comprehensive HRV Pipeline (NeuroKit2)

### 11.1 Frasch (2022) — 124-Feature Pipeline

A comprehensive HRV estimation pipeline using NeuroKit2 was published for sleep physiology applications:[^31]

- **124 HRV measures** including time-domain, frequency-domain, and nonlinear with **dynamic time-delay-based complexity estimation**
- **Temporal fluctuations of HRV estimates themselves** (meta-HRV): analyzing how HRV metrics change over sliding windows
- User-definable time window length
- Supports univariate (single heart rate) and intermittently coupled (fetal-maternal) data
- Accepts RR intervals or peak timestamps from ECG or PPG[^31]

### 11.2 NeuroKit2 Standard Pipeline

```python
import neurokit2 as nk
data = nk.data("bio_resting_5min_100hz")
peaks, info = nk.ecg_peaks(data["ECG"], sampling_rate=100)
# 99 columns including RSA
hrv_all = nk.hrv(peaks, sampling_rate=100)
# Or individual domains:
hrv_time = nk.hrv_time(peaks, sampling_rate=100)
hrv_freq = nk.hrv_frequency(peaks, sampling_rate=100)
hrv_nonlinear = nk.hrv_nonlinear(peaks, sampling_rate=100)
```

Minimum recommended durations: 1 min for HF, 2 min for LF, 5 min for LF/HF.[^32]

***

## 12. DFA-alpha1: Exercise and Cognitive State Thresholds

### 12.1 Methodological Considerations (Hoos & Gronwald, 2025)

A 2025 commentary clarified critical issues with DFA-alpha1 for threshold determination:[^33]

- **Signal-to-noise ratio, movement artifacts, sex, and cardiovascular fitness** are highly influential on DFA-alpha1
- Short-term scaling exponent requires careful methodological consideration
- For operational use: validate DFA-alpha1 against concurrent task difficulty measures before using as a standalone cognitive load indicator

***

## 13. Allostatic Load and HRV-Cognitive Resilience

### 13.1 HRV as Allostatic Resilience Marker

Higher HRV is associated with **psychological flexibility and allostatic resilience**. Longitudinal studies show that reduced HRV predicts psychological and physiological morbidity years later. Reduced vagal tone may directly contribute to increased allostatic load, though bidirectional effects exist (chronic diseases → autonomic neuropathy → reduced HRV).[^34]

The allostatic load construct involves seven physiological systems: SNS, PNS, HPA axis, inflammation, cardiovascular, glucose, and lipids — each contributing to the final AL score. A systematic review found that **high allostatic load is associated with poor cognitive functioning**.[^35][^36]

**Implementation**: Your existing Allostatic Load Index should incorporate HRV (specifically RMSSD, HF power) as the PNS subsystem marker, alongside cortisol/sleep/inflammatory markers when available.

***

## 14. Development Roadmap: Implementation-Ready Evidence Matrix

### Phase 3: Cognition/Workload Modeling (per your HRV.md roadmap)

| Module | Evidence Source | Key Metric | Implementation |
|---|---|---|---|
| **Nonlinear Cognitive Discriminator** | Bouny 2021[^8] | Ei (RCMSE), MFI (MM-DFA) | Add to `hrv_nonlinear` pipeline; 3-min sliding windows; AUC = 0.69 for interference detection |
| **Real-Time Vigilance Tracker** | Xie & Ma 2025[^11] | SVM on 30s HRV windows | 89% binary accuracy; 84% precision for low-vigilance detection |
| **Flight Fatigue Classifier** | Guo 2025[^17] | LightGBM on 12 HRV + Rsp | 88.6% accuracy, 3-level classification; validated on 90 real-flight pilots |
| **Longitudinal Cognitive Risk** | Jandackova 2024[^5] | RMSSD quintile × Time LME | β = -0.07 SD per decade; 3.5-year cognitive aging acceleration |
| **HRF Cognitive Biomarker** | Costa 2021[^22] | PIP, IALS, PSS during sleep | Independent predictor of concurrent + future cognitive decline |
| **Bayesian HR Estimation** | Rosas 2023[^14] | Posterior HR trajectories | Better complexity discrimination; GitHub implementation available |
| **Respiration Correction** | NeuroKit2[^24]; Cui 2020[^27] | EDR + spectral G-causality | CRF/CRI for disentangling respiratory from non-respiratory HRV |
| **Transfer Entropy Coupling** | Keshmiri 2024[^29] | TE(RR→HR) | JIDT Python library; two-dimensional cardiorespiratory biomarker |
| **Workload Multimodal Fusion** | Rao 2020[^19]; Wang 2024[^37] | RF/SVM multimodal | HRV alone AUC = 0.56; combined = 0.94; add behavioral features |

### Phase 3 Implementation Priority Order

1. **Add RCMSE + MM-DFA** to nonlinear module (Bouny algorithms, validated for short series)
2. **Implement 30s sliding window** vigilance tracker with SVM (Xie & Ma parameters)
3. **Add LightGBM fatigue classifier** with the 13-feature set from Guo 2025
4. **Integrate Bayesian HR estimation** (BayesianAtHeart GitHub) as optional advanced mode
5. **Implement respiration-corrected HRV** via NeuroKit2 EDR + CRF/CRI
6. **Add transfer entropy** cardiorespiratory coupling (JIDT library)
7. **Build LME longitudinal risk model** with RMSSD quintiles per Jandackova specifications

***

## 15. Key Mathematical Specifications for Cursor Implementation

### 15.1 RCMSE Algorithm

```python
def compute_rcmse(rr_detrended, m=2, r_ratio=0.15, max_scale=4):
    """Refined Composite Multiscale Entropy (Bouny 2021 implementation)"""
    sd = np.std(rr_detrended)
    r = r_ratio * sd
    rcmse_values = []
    for tau in range(1, max_scale + 1):
        # Generate tau coarse-grained series (overlapping)
        n_total_m, n_total_m1 = 0, 0
        for k in range(1, tau + 1):
            coarse = coarse_grain(rr_detrended, tau, k)
            nm = count_matches(coarse, m, r)
            nm1 = count_matches(coarse, m + 1, r)
            n_total_m += nm
            n_total_m1 += nm1
        if n_total_m > 0 and n_total_m1 > 0:
            rcmse_values.append(-np.log(n_total_m1 / n_total_m))
        else:
            rcmse_values.append(np.nan)
    # Entropy index = area under curve (trapezoidal)
    ei = np.trapz(rcmse_values, dx=1)
    return rcmse_values, ei
```

### 15.2 Within-Person Cognitive Reactivity Z-Score

```python
def cognitive_reactivity_zscore(baseline_rr, task_rr):
    """Compute within-person z-score for HRV reactivity"""
    base_lnrmssd = np.log(compute_rmssd(baseline_rr))
    task_lnrmssd = np.log(compute_rmssd(task_rr))
    base_sd = estimate_baseline_sd(baseline_rr)  # from multiple baselines
    z = (task_lnrmssd - base_lnrmssd) / base_sd
    return z  # negative = sympathetic activation; positive = vagal recovery
```

### 15.3 LME Model Template (statsmodels)

```python
import statsmodels.formula.api as smf

# Longitudinal cognitive risk model (per Jandackova 2024)
model = smf.mixedlm(
    "cognition_score ~ hrv_quintile * time_years + age + sex + education",
    data=longitudinal_df,
    groups=longitudinal_df["subject_id"],
    re_formula="~1"  # random intercept per subject
)
result = model.fit()
# Expected: hrv_quintile:time_years β ≈ -0.07 SD/decade for lowest quintile
```

***

## 16. Signal Quality and Reliability Considerations

### Short-Term HRV Clinical Reliability (Besson et al., 2025)

A 2025 study investigating HRV measurement reliability established that **consistent protocols** for short-term HRV measurements are essential for clinical reliability across settings and positions. This reinforces the need for your Phase 0 reproducibility requirements: log correction regime, stationarity gate, signal quality index per window.[^38]

### Minimum Duration Rules (from your HRV.md + literature)

| Metric | Minimum Window | Confidence Level |
|---|---|---|
| lnRMSSD | 60 seconds | Acceptable |
| RMSSD | 60 seconds | Acceptable |
| pNN50 | 60 seconds | Context-dependent |
| SDNN | 120+ seconds | Stability concerns < 2 min |
| HF power | 120+ seconds | Needs respiration control |
| LF power | 300+ seconds | Standard recommendation |
| LF/HF | 300+ seconds | Standard recommendation |
| SampEn | 300+ RR intervals | m=2, r=0.2×SD |
| DFA-alpha1 | 200+ RR intervals | Sensitive to artifacts |
| RCMSE (τ=1–4) | 400–600 RR | Preserves >120 samples/scale |

***

## References Cited (Key DOIs for Traceability)

1. Thayer & Lane (2000) — Neurovisceral integration model. DOI: 10.1016/S0165-0327(00)00338-4
2. Bouny et al. (2021) — RCMSE + MM-DFA cognitive-autonomic. DOI: 10.3390/e23060663
3. Xie & Ma (2025) — Sliding-window HRV vigilance. DOI: 10.1093/sleep/zsae199
4. Jandackova et al. (2024) — Midlife HRV cognitive decline. DOI (PMC11617396)
5. Schaich et al. (2020) — MESA HRV-cognition. DOI: 10.1161/JAHA.119.013827
6. Guo et al. (2025) — Flight fatigue 3-level classification. DOI: 10.3389/fnins.2025.1621638
7. Rosas et al. (2023) — Bayesian state-space HR. arXiv:2303.04863
8. Costa & Goldberger (2019, 2021) — Heart rate fragmentation. DOI: 10.1152/ajpheart.00110.2019
9. Rao et al. (2020) — MIT cognitive load prediction. DOI: 10.3389/fnhum.2020.00222
10. Yuan et al. (2025) — A320 pilot MWL. DOI: 10.3389/fnrgo.2025.1672492
11. Cui et al. (2020) — CRF/CRI. DOI: 10.3389/fphys.2020.00867
12. Keshmiri et al. (2024) — HR-RR transfer entropy. bioRxiv: 2024.01.21.576502
13. Frasch (2022) — NeuroKit2 124-feature pipeline. DOI: 10.1016/j.mex.2022.101782
14. Forte et al. (2019) — HRV cognitive function systematic review. DOI: 10.3389/fnins.2019.00710
15. Wei et al. (2018) — Prefrontal-amygdala HRV. DOI: 10.3389/fnhum.2018.00002
16. Porges (2025) — Polyvagal theory revisited. PMC12479538
17. Sepúlveda-Figueroa et al. (2026) — Bayesian HRV-cognition. PMC12891186
18. Hoos & Gronwald (2025) — DFA-alpha1 methodology. DOI: 10.1007/s00421-025-05859-2

---

## References

1. [Structural Covariance of the Prefrontal-Amygdala ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC5838315/) - The neurovisceral integration model has shown a key role of the amygdala in neural circuits underlyi...

2. [A model of neurovisceral integration in emotion regulation ...](https://www.sciencedirect.com/science/article/abs/pii/S0165032700003384) - by JF Thayer · 2000 · Cited by 4232 — We have presented evidence that autonomic control of the heart...

3. [Polyvagal theory: a journey from physiological observation to ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC12479538/) - Polyvagal theory (PVT) offers an integrative model of autonomic regulation that accounts for the evo...

4. [The Polyvagal Perspective](https://pmc.ncbi.nlm.nih.gov/articles/PMC1868418/) - by SW Porges · 2006 · Cited by 5191 — The literature consistently supports the model relating autono...

5. [Midlife heart rate variability and cognitive decline - PMC - NIH](https://pmc.ncbi.nlm.nih.gov/articles/PMC11617396/) - by VK Jandackova · 2024 · Cited by 4 — Cognitive decline in individuals with low RMSSD and HF-HRV wa...

6. [Association of Heart Rate Variability With Cognitive Performance: The Multi‐Ethnic Study of Atherosclerosis](https://pmc.ncbi.nlm.nih.gov/articles/PMC7428623/) - Heart rate variability (HRV) is associated with vascular risk factors for dementia, but whether HRV ...

7. [Heart Rate Variability and Cognitive Function: A Systematic Review](https://pmc.ncbi.nlm.nih.gov/articles/PMC6637318/) - Background: Autonomic dysfunctions may precede the development of cognitive impairment, but the conn...

8. [Entropy and Multifractal-Multiscale Indices of Heart Rate Time Series to Evaluate Intricate Cognitive-Autonomic Interactions](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8230296/) - Recent research has clarified the existence of a networked system involving a cortical and subcortic...

9. [Linear and nonlinear analyses of heart rate variability signals under mental load](https://www.sciencedirect.com/science/article/abs/pii/S1746809422002804) - Mental load has an important effect on the efficiency and reliability of human–machine systems. This...

10. [Entropy analysis of heart rate variability and its application ... - NIHpmc.ncbi.nlm.nih.gov › articles › PMC6597986](https://pmc.ncbi.nlm.nih.gov/articles/PMC6597986/) - The current method to evaluate major depressive disorder (MDD) relies on subjective clinical intervi...

11. [Tracking vigilance fluctuations in real-time: a sliding- ...](https://pubmed.ncbi.nlm.nih.gov/39185558/) - by T Xie · 2025 · Cited by 10 — This study aimed to improve the objectivity and efficiency of HRV-ba...

12. [Analyzing Heart Rate Variability for COVID-19 ICU Mortality ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC12347825/) - by G David · 2025 · Cited by 1 — Methods: HRV indices were extracted from four ECG leads (I, II, III...

13. [Bayesian at heart: Towards autonomic outflow estimation  via generative state-space modelling of heart rate dynamics](https://arxiv.org/pdf/2303.04863.pdf)

14. [Bayesian at heart: Towards autonomic outflow estimation ...](https://arxiv.org/abs/2303.04863) - by FE Rosas · 2023 · Cited by 10 — Bayesian at heart: Towards autonomic outflow estimation via gener...

15. [From brain to heart: cognitive performance shapes exercise](https://pmc.ncbi.nlm.nih.gov/articles/PMC12891186/) - by P Sepúlveda-Figueroa · 2026 — This study employs a Bayesian modeling approach to extend beyond st...

16. [Assessment of flight fatigue using heart rate variability and ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC12263958/) - by D Guo · 2025 · Cited by 8 — This study proposes a novel HRV-based method for the automatic and ob...

17. [Assessment of flight fatigue using heart rate variability and ...](https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2025.1621638/full) - by D Guo · 2025 · Cited by 8 — The accurate identification of flight fatigue is crucial for managing...

18. [Pilot mental workload analysis in the A320 traffic pattern ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC12647116/) - Pilot mental workload is a critical factor influencing flight safety, particularly during dynamic fl...

19. [Predicting Cognitive Load and Operational Performance in a ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC7350508/) - Modern operational environments can place significant demands on a service member's cognitive resour...

20. [Software for computing Heart Rate Fragmentation v1.0.0](https://physionet.org/content/heart-rate-fragmentation-code/) - by M Costa · Cited by 1 — Heart rate fragmentation (HRF) is a new method for assessing neuroautonomi...

21. [Heart rate fragmentation: using cardiac pacemaker ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC6620676/) - This perspectives article discusses the use of a novel set of dynamical biomarkers in the assessment...

22. [Prediction of Cognitive Decline Using Heart Rate ... - PubMed](https://pubmed.ncbi.nlm.nih.gov/34512310/) - by MD Costa · 2021 · Cited by 27 — Increased HRF assessed during sleep was independently associated ...

23. [ECG-Derived Respiration (EDR) Analysis¶](https://rpanderson-neurokit2.readthedocs.io/en/latest/examples/edr.html)

24. [ECG-Derived Respiration (EDR) — NeuroKit2 0.2.13 ...](https://neuropsychology.github.io/NeuroKit/examples/ecg_edr/ecg_edr.html)

25. [ECG-Derived Respiration](https://archive.physionet.org/physiotools/edr/)

26. [Microsoft Word - lascas_1.3.docx](https://www.castoriscausa.com/files/cassani_2013_anc.pdf)

27. [Frontiers | Cardiopulmonary Resonance Function and Indices—A Quantitative Measurement for Respiratory Sinus Arrhythmia](https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2020.00867/full) - Respiratory sinus arrhythmia (RSA) represents a physiological phenomenon of cardiopulmonary interact...

28. [HRV — NeuroKit2 0.2.13 documentation - GitHub Pages](https://neuropsychology.github.io/NeuroKit/functions/hrv.html)

29. [Information Dynamics of the Heart and Respiration Rates](https://www.biorxiv.org/content/10.1101/2024.01.21.576502v1.full-text) - We propose the AIS of HR and the transfer entropy RR → HR as two-dimensional biomarkers of cardiores...

30. [Decreased cardio-respiratory information transfer is ...](https://pubmed.ncbi.nlm.nih.gov/39679499/) - by C Morandotti · 2025 · Cited by 8 — This study used the concept of transfer entropy (TE) to measur...

31. [Comprehensive HRV estimation pipeline in Python using ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC9307944/) - NeuroKit2 is a Python Toolbox for Neurophysiological Signal Processing. The presented method is an a...

32. [Heart Rate Variability (HRV) — NeuroKit2 0.2.13 ...](https://neuropsychology.github.io/NeuroKit/examples/ecg_hrv/ecg_hrv.html)

33. [Cassirame et al.`s (2025) Detrended fluctuation analysis to ...](https://pmc.ncbi.nlm.nih.gov/articles/PMC12423231/) - by O Hoos · 2025 · Cited by 5 — The study sheds light on relevant methodological problems and influe...

34. [Heart-rate variability: a biomarker to study the influence ... - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5882295/) - by HA Young · 2018 · Cited by 340 — Heart-rate variability (HRV) (the time differences between one b...

35. [Mitochondrial Nexus To Allostatic Load Biomarkers - PMC - NIH](https://pmc.ncbi.nlm.nih.gov/articles/PMC5901647/)

36. [The association between allostatic load and cognitive ...](https://pubmed.ncbi.nlm.nih.gov/32892066/) - Previous research suggests that high allostatic load (AL), a biological indicator of physiological d...

37. [HRV.md](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/387607/8287ec3a-fd8f-4a62-83f4-75049140fb48/HRV.md?AWSAccessKeyId=ASIA2F3EMEYE3OZ4A4GJ&Signature=lBdTpXaI2tYE4sul5uCHp46seYg%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJGMEQCIBvlnL8FkwO4UeQCM03Ib7x95aFpLe7voPXbn%2BDu8jCVAiA2ZiGpDawlMwlQ39liSRhVGGRyBMoQC3bx7YX9EbnC%2FCr8BAjI%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAEaDDY5OTc1MzMwOTcwNSIMkchOV8IAUnJWlDJKKtAEdPvLcBy6FK%2Bl9OX0Z7BHWafZqtxYa5DBQEToKD%2BsBWKC%2FfdQlmr4xK5fGLj231ggkmc%2BdnltiXva0lJ91ochmahrx467j1pXUV%2BXEz3LvWan73xywxsiIA7qCXXc3TY1%2FinHtDPLKMQLgucI4jry7RlWQEBjOQf4%2Bhr9h%2B8a0jKlIdQnJzbc4eFjtHdwQUewBPmaU%2BjEodCagcCFqdzytkSI%2B9cvYiA9E7xBR0RYdywAQHwGiJElYF8ljj3vnW9I%2Fzp%2FFRvUqwsL5jUIaF0wzbdA4mkbNgcHdVLsyBGEQssv4SQ1nvnhGGPzM%2BRHebkwVOmrerKQaSgLA%2F6z1A46Qp7SRVSD4kjMw%2F5zzJyx75Z41purJNdnIcHi7wLm%2FAiO8LYo2N2xuqGi5SpdP9IZ%2BjJhq3gk1xD111TI4rAwABEwWN%2FWCTX5SENZFohZGubXhrXX7FRHVXnuuhTGWQfu59%2BnNOpnlhNOhaB%2FssPc%2FsmIKgxkiwf1bigaq3Nl%2FGMbcEMZJwsZIUbdPyDhNFE%2B6jrM0GmLXToLMQIiDTwp1SeLNnrJEPIYArcng4y12gbttzh%2BUgXwwsi4Hl6nEGdvWu6osRP9QgHi6JZSJSXSfMIjgeRVk5UO3%2BRi%2FSDRgOYQs0GGQeG%2Fx59CdOhFXsbUqaQC6Fg7QJ58uE3ha8nn7mpc5KgbIROqBjt1lICXzoxErCATv6FjMUQnvqK1tFS4bG7AL4p0Y0Ub7c2%2BsjPLHWvCcnAPCnIsfZZSpqQVsuOqOweV8RYmSZt9obtO22R%2BHTClo%2BzMBjqZAYB7W386n3NFAr7Pkv5kDbH3ffBvVVCLadx4Xq5AYcomCugaLnog4b9mfXVI4IqicQl3RiQMiCBVw9IVyXFrEWqeutuGYYzvTuchU2EA7jihqkZ5eQ11fm64kICdGFLz7D73b6D1QPL03MIz%2BgNBy8ViVYO2%2BcSQKoCjql2X7Mox2GUqt5c8jse3ZL0OX3nxsDwdf1cELwyRtA%3D%3D&Expires=1771775940) - Mission Control - Flight Surgeon is a comprehensive, research-grade Heart Rate Variability HRV opera...

38. [Assessing the clinical reliability of short-term heart rate ...](https://www.nature.com/articles/s41598-025-89892-3) - by C Besson · 2025 · Cited by 50 — This study investigates the reliability of short-term HRV measure...

