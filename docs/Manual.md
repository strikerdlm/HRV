## HRV Streamlit App Manual

This manual explains all features in the app, what the metrics mean physiologically, how to interpret them in medical terms, and key caveats grounded in contemporary scientific guidance.

### Who this is for
- Clinicians and researchers using short-term HRV (∼5 minutes) to characterize autonomic function at rest or across protocols.
- Users needing transparent, reproducible methods with clear assumptions and limitations.

### What this app does
- Loads Polar-like RR-interval text files (one RR in ms per line).
- Performs quality control (QC) with configurable artifact detection/correction.
- Computes time-, frequency-, geometric-, nonlinear-, and entropy-based metrics.
- Supports sliding-window analysis, spectrograms, and ECharts visualizations.
- Compares metrics to common short-term anchors with gauge displays.

References are included where relevant; see the References section at the end for sources and further reading.


## Data and Workflow

### Input format
- RR intervals in milliseconds; values outside 300–2000 ms are discarded.
- Multiple files allowed; each file is treated as a dataset.

### Data quality and preprocessing (QC)
- Sidebar toggles for artifact detection/correction:
  - Method: threshold vs moving median or previous-beat reference.
  - Deviation threshold: proportion difference beyond which a beat is flagged (default 0.2).
  - Median window (odd): smoothing window for median reference (default 11).
- Cleaned RR is used for frequency, nonlinear, spectrogram, and windowed metrics when QC is enabled.
- Time Series tab overlays:
  - Raw series (baseline).
  - Cleaned series (green).
  - Flagged artifacts (red points).

Scientific notes:
- Artifacts (missed/extra/misaligned beats; ectopy) degrade HRV validity. Conservative correction by interpolation is widely used in scientific software; avoid mass deletion that biases results.
- HR and breathing rate influence HRV (especially HF, LF/HF). Report protocols and consider HR correction judiciously.

Key sources: Psychophysiology Publication Guidelines (Part 1, 2024), Task Force 1996 consensus, Shaffer & Ginsberg 2017, Sacha/Frontiers 2016 on HR correction considerations.


## Tabs and Visualizations

### Overview
- Shows per-dataset metadata: beats, recording duration (minutes), mean HR (bpm), and percentage of flagged artifacts (if QC enabled).

### Time Series
- RR intervals vs time; heart rate vs time.
- QC overlays show cleaned RR (green) and flagged points (red), useful to verify data integrity before interpretation.

### Frequency
- PSD overlay (choose method in sidebar): Welch (default), Periodogram, AR (Yule–Walker approximation).
- VLF/LF/HF bands highlighted: VLF 0.0033–0.04 Hz; LF 0.04–0.15 Hz; HF 0.15–0.40 Hz.

### Nonlinear
- Poincaré plot (RRₙ vs RRₙ₊₁): visualizes short- and long-term variability patterns.

### Spectrogram
- Time–frequency heatmap of interpolated RR series; helps visualize spectral dynamics over time (e.g., HF breathing-related power).

### Windowed
- Sliding-window metrics (e.g., 5-min window, 1-min step) with minimum RR count threshold.
- Useful for long recordings and time-varying conditions (stationarity improves per-window validity).

### Metrics
- Full table of computed metrics (time, frequency, geometric, nonlinear, entropy), including QC summary if enabled.

### Gauges
- Normogram-style gauges for SDNN, RMSSD, LF/HF, and HF power versus commonly cited short-term anchors.
- Caveats: population, age, posture, and breathing change distributions; prioritize within-subject trends.

### ANS Function Tests
- The **ANS Function Tests** tab computes classic autonomic function ratios when you supply time windows (seconds from recording start):
  - **Valsalva ratio**: requires phase II (strain) and phase IV (recovery) windows; reports the minimum RR (phase II), maximum RR (phase IV), and their ratio.
  - **Deep breathing**: specify the start time, cycle length, and number of paced breathing cycles. The app returns expiratory/inspiratory (E:I) differences, ratios, and per-cycle details.
  - **30:15 ratio**: specify the moment of standing plus windows around the 15th and 30th beats post-stand; the ratio is longest RR around beat 30 divided by shortest RR around beat 15.
- For best results, enable artifact correction and align windows with the actual protocol cues (e.g., microphone cues, on-screen timers). If a window contains insufficient beats, the app warns and skips that metric.

### Science and References
- Concise scientific notes and citations.


## Metric Reference and Interpretation

Below are concise definitions, physiology, and medical interpretation guidance for common short-term HRV metrics. Norms are context-dependent; values vary by age, posture, breathing, health status, and recording conditions.

### Time-domain metrics
- Mean NN (ms): average RR interval (parasympathetic and sympathetic influences). Lower values often reflect higher heart rate (e.g., stress, exertion), but interpret with protocol context.
- SDNN (ms): standard deviation of NN intervals. In short-term (∼5 min), reflects total variability but is not directly equivalent to 24-h SDNN. Lower SDNN at rest is generally associated with reduced overall variability; increases can reflect greater overall variability or measurement noise/artifacts if QC is poor.
- RMSSD (ms): root mean square of successive RR differences. A robust index of short-term vagal (parasympathetic) modulation at rest; higher RMSSD generally indicates stronger vagal tone. Sensitive to breathing rate and depth.
- NN20/NN50 (count) and pNN20/pNN50 (%): counts/proportions of successive differences >20 or >50 ms. Related to short-term vagal activity; pNN50 is traditional but less stable in very short recordings.
- HR statistics (mean, min, max, SD): contextualize autonomic balance; higher mean HR often associates with reduced vagal indices and increased sympathetic drive.
- CVNN (%): coefficient of variation of NN intervals; unitless normalization of SDNN by mean NN; interpret similarly to SDNN.

Clinical emphasis:
- RMSSD at rest is commonly used as a proxy of vagal modulation; reductions can reflect decreased parasympathetic activity due to stress, illness, sleep deprivation, or exertional load. Use within-subject trends and protocol notes.

### Frequency-domain metrics (VLF, LF, HF; normalized and ratios)
- Method: PSD from interpolated RR (default Welch); options for Periodogram and AR (Yule–Walker) are available.
- Bands: VLF 0.0033–0.04 Hz, LF 0.04–0.15 Hz, HF 0.15–0.40 Hz (short-term).
- VLF, LF, HF power (ms²/Hz): band-limited spectral energy. HF closely tracks respiratory sinus arrhythmia; LF reflects baroreflex-mediated rhythms with mixed sympathetic/parasympathetic contributions.
- LF/HF ratio: historically used as balance index; interpretation is limited and sensitive to breathing rate and protocol. Use with caution and context (e.g., spontaneous vs paced breathing).
- Normalized units (LFnu, HFnu) and percentages: relative within LF+HF or total power; useful for within-subject changes but sensitive to total power fluctuations and respiration.

Clinical emphasis:
- HF increases with slower, deeper breathing and higher vagal activity; LF/HF often decreases under strong vagal influence but is not a universal sympathovagal balance marker. Do not over-interpret LF/HF without breathing context.

### Geometric metrics
- HRV Triangular Index (unitless): total number of NN intervals divided by the height of the NN histogram; reflects overall variability; higher values indicate more variability.
- TINN (ms): baseline width of the NN histogram; another overall variability descriptor (depends on distribution shape and binning).
- Baevsky Stress Index (SI): SI = AMo / (2·Mo·MxDMn), where AMo is the relative mode height, Mo is modal NN (ms), and MxDMn is the range. Higher SI is interpreted as higher sympathetic predominance/“tension.” SI is sensitive to binning and distribution skew; interpret within-subject and with protocol context.

### Nonlinear metrics
- Poincaré SD1 (ms): short-axis dispersion; mathematically ~ RMSSD/√2. Reflects short-term vagal modulation.
- Poincaré SD2 (ms): long-axis dispersion; reflects longer-term variability components.
- SD1/SD2 ratio and ellipse area: composite descriptors; larger area indicates greater combined variability; ratio changes can indicate shifts in short vs long-term dynamics.
- DFA α1 and α2 (unitless): detrended fluctuation analysis scaling exponents; α1 (short-term, ~4–16 beats) often ~0.75–1.25 at healthy rest. Values below this can appear with exercise intensity near the aerobic threshold; values substantially above may suggest altered control/fractal properties. Requires adequate series length and stationarity.

### Entropy metrics (complexity/regularity)
- Approximate Entropy (ApEn) and Sample Entropy (SampEn) (unitless): quantify regularity/complexity in RR dynamics. Parameters commonly use m=2 and r=0.15–0.20·SD for short-term HRV. Lower entropy suggests more regular (less complex) dynamics—seen in rigid autonomic regulation states; higher entropy indicates greater complexity. Entropy estimates are sensitive to window length and parameters.

### Autonomic function ratios
- **Valsalva ratio**: longest RR during phase IV divided by the shortest RR during phase II of the Valsalva manoeuvre. Values ≥1.2 are often cited as normal in middle-aged adults; lower ratios may indicate impaired parasympathetic function. Ensure the windows capture the correct phases (approximately 5–15 s for strain, 15–25 s for release).
- **Deep breathing (E:I) response**: difference and ratio between expiratory and inspiratory RR intervals during paced breathing (commonly 6 breaths/min). Larger E:I differences/ratios reflect greater vagal modulation.
- **30:15 ratio**: ratio of the longest RR near the 30th beat after standing to the shortest RR near the 15th beat. Ratios ≥1.04 are typical in healthy adults; lower values suggest impaired reflex tachycardia response.
- Interpret ratios alongside age-specific norms, medications, and posture instructions. Document exact timing cues to improve reproducibility.


## Interpretation Principles

- Prioritize within-subject comparisons over time; inter-individual “norms” vary widely by age, sex, posture, fitness, and breathing.
- Short-term anchors (e.g., RMSSD ~42±15 ms; SDNN ~50±16 ms) are population summaries and do not imply individual health status.
- Respiration strongly affects HF power and related indices; document or control breathing where possible.
- LF/HF is not a universal sympathovagal balance index; use with protocol detail and complementary measures.
- Data quality matters: artifacts inflate power and distort nonlinear metrics; use QC overlays to check flagged beats and re-run if needed.
- Use multi-domain corroboration (time, frequency, nonlinear) rather than relying on any single metric.


## Best Practices and Protocol

- Recording length: ≥5 minutes for short-term HRV at rest; include a stabilization period (e.g., ≥5 minutes) before recording.
- Posture and context: report posture (supine/sitting/standing), time-of-day, recent exertion/caffeine, and breathing instructions (spontaneous vs paced).
- Device and signal: ECG is preferred; PPG-derived RR is viable but can have non-uniform error and motion sensitivity—document device and conditions.
- QC: visualize RR time series with flags; if many artifacts (>5–10%), retest or interpret cautiously.
- Reporting: document sampling/processing, metrics, window sizes, PSD method, QC approach, breathing conditions, and any HR correction choices.


## Limitations and Cautions

- Arrhythmias and ectopy: HRV metrics assume sinus rhythm. Extensive ectopy invalidates standard HRV interpretations.
- Short-term vs 24-hour: SDNN and spectral indices differ across durations; avoid extrapolating short-term results to 24-hour risk markers.
- Respiration: HF power and LF/HF are sensitive to breathing; misinterpretation is common when breathing is uncontrolled or unknown.
- Entropy metrics: parameter- and length-sensitive; compare like-with-like and avoid over-interpretation in very short windows.


## Quick Guide (Clinical)

- RMSSD (ms): vagal modulation; lower at rest suggests reduced vagal activity (stress, illness, load). Track within-subject changes.
- SDNN (ms): overall variability (short-term proxy); interpret with QC and context; not a 24-h surrogate.
- HF power: parasympathetic/breathing-related; increases with slow/deep breathing.
- LF power: baroreflex and mixed influences; not purely sympathetic.
- LF/HF: limited for “balance.” Use caution and consider breathing rate.
- SD1/SD2 (Poincaré): SD1 ≈ vagal; SD2 longer-term components; ellipse area reflects combined variability.
- DFA α1: fractal-like correlation; ~0.75–1.25 at healthy rest; lower values can reflect exercise intensity near aerobic threshold.
- Entropy (ApEn/SampEn): lower entropy → more regular (rigid) dynamics; higher → greater complexity. Use consistent parameters.


## References (selected)

- Task Force of the ESC/NASPE (1996). Heart rate variability: standards of measurement, physiological interpretation and clinical use. [ESC PDF](https://www.escardio.org/static-file/Escardio/Guidelines/Scientific-Statements/guidelines-Heart-Rate-Variability-FT-1996.pdf)
- Shaffer, F., & Ginsberg, J. (2017). An overview of HRV metrics and norms. [Frontiers in Public Health](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full)
- Quigley, K. S., et al. (2024). Publication guidelines for HR and HRV studies in Psychophysiology—Part 1. [Wiley link](https://onlinelibrary.wiley.com/doi/10.1111/psyp.14604)
- Nunan, D., et al. (2010). Normal values for short-term HRV in healthy adults. [PubMed](https://pubmed.ncbi.nlm.nih.gov/20663071/)
- HR correction and respiration influences in HRV (methodological considerations). [Frontiers in Physiology, 2016](https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2016.00356/full)
- Laborde, S., Mosley, E., & Thayer, J. F. (2017). HRV in psychophysiology—planning, analysis, reporting. [Frontiers in Psychology](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2017.00213/full)


## Notes on App Implementation

- QC heuristics are transparent and bounded; they are not a substitute for full ECG beat annotation or clinical-grade editing. For high-stakes analyses, consider manual review.
- Frequency methods include Welch (default), Periodogram, and an AR (Yule–Walker) approximation for educational comparison; results differ across methods and settings.
- Entropy defaults (m=2, r=0.2·SD) follow common practice for short-term HRV but should be adjusted for specific study aims and lengths when needed.


