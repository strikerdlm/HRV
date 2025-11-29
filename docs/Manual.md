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

### Covariate adjustment (patient profile)
- Optional sidebar controls let you enter age, sex, BMI, and exercise level.
- When enabled, RMSSD and SDNN are paired with covariate-adjusted expectations and z-scores (`rmssd_expected`, `rmssd_z_cov`, `sdnn_expected`, `sdnn_z_cov`) derived from conservative literature anchors.
- Use these adjustments to contextualize individual readings; document the covariates used and interpret alongside the unadjusted metrics.


## Tabs and Visualizations

### Overview
- Shows per-dataset metadata: beats, recording duration (minutes), mean HR (bpm), and percentage of flagged artifacts (if QC enabled).
- When deviation detection is enabled, the summary table counts green/yellow/red windows per dataset and reports the peak deviation index.
- Respiratory rate estimates (breaths/min) derived from the HF spectral peak appear when the PSD provides a reliable value.

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
- Optional deviation detection computes robust z-scores across selected metrics (RMSSD, SDNN, LF/HF, HF power by default) using median/MAD per dataset; warn and alert thresholds colour-code windows (green/yellow/red).
- The deviation timeline visualises when monitored metrics diverge; contiguous yellow/red runs meeting the “Min windows to define an episode” value are summarised as anomaly episodes.
- Deviant windows are also shaded on the tachogram so you can correlate numerical flags with signal segments.

### Metrics
- Full table of computed metrics (time, frequency, geometric, nonlinear, entropy), including QC summary if enabled.
- Advanced analytics columns include heart-rate fragmentation (PIP, IALS, PSS), phase-rectified capacities (deceleration/acceleration and anchor counts), symbolic dynamics percentages, permutation entropy (absolute/normalized), multifractal DFA descriptors, recurrence quantification measures, and heart-rate-normalized RMSSD outputs.
- When patient-profile adjustment is active, expected values and z-scores for RMSSD/SDNN appear so you can judge deviations against covariate-aware baselines.

### Gauges
- Normogram-style gauges for SDNN, RMSSD, LF/HF, and HF power versus commonly cited short-term anchors.
- Caveats: population, age, posture, and breathing change distributions; prioritize within-subject trends.
- A respiratory-rate gauge (breaths/min) appears when the HF peak is well defined; treat it as a qualitative respiration cue rather than a primary ventilatory measure.

### ANS Function Tests
- The **ANS Function Tests** tab computes classic autonomic function ratios when you supply time windows (seconds from recording start):
  - **Valsalva ratio**: requires phase II (strain) and phase IV (recovery) windows; reports the minimum RR (phase II), maximum RR (phase IV), and their ratio.
  - **Deep breathing**: specify the start time, cycle length, and number of paced breathing cycles. The app returns expiratory/inspiratory (E:I) differences, ratios, and per-cycle details.
  - **30:15 ratio**: specify the moment of standing plus windows around the 15th and 30th beats post-stand; the ratio is longest RR around beat 30 divided by shortest RR around beat 15.
- For best results, enable artifact correction and align windows with the actual protocol cues (e.g., microphone cues, on-screen timers). If a window contains insufficient beats, the app warns and skips that metric.

### Readiness
- Builds a readiness baseline from historical parasympathetic index values (derived from HF power, RMSSD, pNN50, and SD1).
- Select a current dataset, choose baseline sessions (last-in-first-out, capped by the “Historical window” slider), and decide whether to include the current measurement.
- Outputs readiness percentile, Kubios-style category (VERY LOW/LOW/NORMAL/HIGH), parasympathetic index, and baseline summary statistics. A line chart plots the baseline history with category thresholds.
- Require at least seven historical sessions recorded under comparable conditions (posture, time-of-day, breathing) for reliable categorisation. Rebuild the baseline whenever measurement conditions change.

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

### Advanced analytics (fragmentation, PRSA, symbolic, multifractal, recurrence, HR-normalised RMSSD)
- Heart-rate fragmentation metrics (`hrf_pip_pct`, `hrf_ials`, `hrf_pss_pct`, `hrf_segment_count`) capture rapid alternating accelerations/decelerations; sustained high fragmentation can flag arrhythmic risk or autonomic disorganization.
- Phase-rectified signal averaging outputs (`deceleration_capacity`, `acceleration_capacity`, anchor counts) quantify asymmetry in vagal versus sympathetic modulation; low deceleration capacity often accompanies reduced vagal drive.
- Symbolic dynamics percentages (`symbolic_0v_pct`, `symbolic_1v_pct`, `symbolic_2lv_pct`, `symbolic_2uv_pct`) summarise short symbolic patterns; richer variability yields lower 0V and higher 2UV proportions.
- Permutation entropy (absolute and normalised) reflects the diversity of ordinal patterns; lower values indicate more regular series but depend on window length and order settings.
- Multifractal DFA descriptors (`mfdfa_width`, `mfdfa_alpha_min`, `mfdfa_alpha_max`, `mfdfa_hurst_mean`) track scale-dependent variability; narrow widths imply monofractal behaviour.
- Recurrence quantification metrics (`rqa_rr`, `rqa_det`, `rqa_lam`, `rqa_lmax`) describe recurrence density, determinism, laminarity, and maximum diagonal length. Interpret deviations with protocol context, as radius/embedding defaults influence outcomes.
- Heart-rate-normalised RMSSD metrics (`rmssd_master_expected`, `rmssd_master_ratio`, `rmssd_master_residual`) compare observed RMSSD with a master curve anchored to mean HR, reducing heart-rate dependence when monitoring recovery.

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
- Readiness scoring depends on a stable baseline. Rebuild or reinterpret baselines if posture, time-of-day, breathing protocol, or sensor type changes materially.


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

## NOAA space‑weather metrics and physiology

The Space tab integrates NOAA SWPC feeds commonly used in space‑weather operations. Below are plain‑language definitions, typical scientific uses, and what current evidence suggests about potential links to human physiology (especially HRV). Evidence is correlational unless experimental designs are specified; individual sensitivity varies and confounding (seasonality, behavior, environment) must be considered.

### Planetary K index (Kp)
- What it is: A quasi‑logarithmic global index (0–9) of geomagnetic storm intensity from magnetometer stations (3‑hour cadence operationally; we also use 1‑min products and model forecasts). Higher Kp reflects stronger geomagnetic disturbances.
- Why it matters physically: Southward interplanetary magnetic field (IMF Bz < 0) and elevated solar wind speed/pressure couple into Earth’s magnetosphere, increasing auroral electrojets and variability detected by magnetometers—captured by Kp.
- Physiology: Multiple human studies associate higher geomagnetic activity with HRV changes (often reduced vagal indices/total power) and increased cardiovascular event risk.
  - Geomagnetic disturbances reduced HRV in the Normative Aging Study (panel of older men), consistent with a stressor effect [Vieira 2022, Sci Total Environ, PubMed 35644403].
  - A long‑term study found HR increases with solar wind intensity (stress response) and HRV changes with solar/geomagnetic activity [Alabdulgader 2018, Sci Rep, PubMed 29422633].
  - Population studies reported increased acute coronary events around storms and with higher solar‑wind variables [Vencloviene 2020, PubMed 32291532]. A recent systematic review suggests elevated risks of MI/ACS and stroke during storms (RR ≈1.3–1.6) [Gaisenok 2025, PubMed 40256184].
- Interpretation for HRV: Expect small effect sizes; reductions in SDNN/RMSSD or HF can appear around higher Kp. Test lags from 0–72 h; both anticipatory and delayed effects are reported.

### Dst index (storm‑time disturbance)
- What it is: Hourly index (nT) of the symmetric ring current strength; more negative Dst indicates stronger global storms (e.g., −50 to −100 nT moderate; < −200 nT severe).
- Physiology: Not all HRV studies use Dst directly, but Dst codifies storm intensity. Findings linking storms to HRV decreases and higher CVD risks likely extend to periods of strongly negative Dst, in line with Kp‑based results [Vieira 2022; Gaisenok 2025].
- Interpretation for HRV: Consider Dst as a complementary metric to Kp; scan similar lags and inspect directionality per metric.

### Solar wind speed/density/temperature (ACE/DSCOVR) and IMF Bt/Bz
- What these are: In‑situ solar‑wind plasma parameters (km/s, cm⁻³, K) and interplanetary magnetic field magnitude/orientation (nT). Bz < 0 (southward) enhances magnetospheric coupling; higher speed/dynamic pressure often precede or co‑occur with geomagnetic activity.
- Physiology: Increases in solar‑wind intensity have been associated with higher heart rate and HRV changes consistent with stress responses [Alabdulgader 2018, Sci Rep]. Links to AMI risk have been reported for higher solar‑wind speed/pressure at short lags in population data [Vencloviene 2020].
- Interpretation for HRV: Examine lags (0–72 h). IMF Bz southward intervals may precede Kp/Dst rises; alignment with HRV changes can clarify causal ordering.

### F10.7 cm solar radio flux (2.8 GHz)
- What it is: Daily 10.7‑cm solar flux (sfu) proxy for solar EUV output and overall solar activity.
- Physiology: Long‑term data showed associations between F10.7, cosmic rays, and HRV measures (e.g., higher HRV/parasympathetic activity with higher F10.7 and Schumann resonance power) [Alabdulgader 2018]. Other cohorts report mixed findings depending on covariates and timing.
- Interpretation for HRV: Consider F10.7 as a background driver of ionospheric state and solar cycle; effects are typically smaller and slower than storm indices but may be detectable in well‑controlled longitudinal data.

### GOES integral proton flux (≥1–≥500 MeV)
- What it is: Particle flux thresholds used to classify solar radiation storms (S‑scale). Large events often accompany CME‑driven storms.
- Physiology: Direct HRV evidence is limited; however, radiation storms frequently co‑occur with geomagnetic disturbances linked to HRV and CVD risk (see Kp/Dst). Aviation/spaceflight literature discusses radiation exposure risks; clinical correlations at ground level remain uncertain for HRV.
- Interpretation for HRV: Treat increases as context for concurrent geomagnetic activity; look for coincident Kp/Dst/solar‑wind changes when evaluating HRV.

### GOES x‑ray flux (flares, 0.05–0.4 nm and 0.1–0.8 nm)
- What it is: Soft x‑ray irradiance measured by GOES; used for flare class (A/B/C/M/X). Flares may not by themselves drive geomagnetic storms (CME/IMF coupling is key).
- Physiology: Direct HRV links are sparse. Use primarily as context; any HRV response is more likely mediated by subsequent solar‑wind/IMF changes and resulting geomagnetic activity.

### Predicted Kp (model products)
- What it is: Short‑horizon model estimates of Kp (e.g., 1‑h cadence). Useful for anticipation and planning.
- Physiology: As with observed Kp; use forecasts to pre‑specify HRV analysis windows and test anticipatory/lagged responses.

### Solar radio flux (multifrequency network)
- What it is: Discrete‑frequency flux from NOAA’s solar radio telescope network; tracks broad‑band emission and bursts.
- Physiology: Not a direct driver; best treated as solar context and cross‑check with F10.7 and flare activity.

### Practical guidance for analysis
- Use multiple metrics jointly: Kp/Dst (disturbances), solar‑wind speed/pressure/IMF (drivers), and F10.7 (background activity). Proton/x‑ray flux provide event context.
- Always scan lags (e.g., −24 to +72 h) and check both signs of correlation; report sample sizes and CIs.
- Adjust for time‑of‑day, weekday/season, temperature, and behavior (sleep/exercise). Treat findings as exploratory unless replicated prospectively.

### Key scientific sources
- Vieira CLZ et al. Geomagnetic disturbances reduce HRV (Normative Aging Study). Sci Total Environ 2022. [PubMed 35644403](https://pubmed.ncbi.nlm.nih.gov/35644403/).
- Alabdulgader A et al. Long‑term HRV responses to solar/geomagnetic activity. Sci Rep 2018. [PubMed 29422633](https://pubmed.ncbi.nlm.nih.gov/29422633/).
- Vencloviene J et al. Solar‑wind and geomagnetic activity associated with AMI risk. 2020. [PubMed 32291532](https://pubmed.ncbi.nlm.nih.gov/32291532/).
- Poskotinova L et al. Baroreflex/HRV sensitivity to local geomagnetic variations. Life 2022. [PubMed 35888190](https://pubmed.ncbi.nlm.nih.gov/35888190/).
- Papailiou M et al. Space‑weather phenomena and heart rate changes in Greece. 2023. [PubMed 36227358](https://pubmed.ncbi.nlm.nih.gov/36227358/).
- McCraty R et al. Synchronization of autonomic rhythms with geomagnetic activity. IJERPH 2017. [PubMed 28703754](https://pubmed.ncbi.nlm.nih.gov/28703754/).
- Gaisenok O et al. Systematic review: geomagnetic storms and MI/ACS/stroke risks. 2025. [PubMed 40256184](https://pubmed.ncbi.nlm.nih.gov/40256184/).
- Shaffer, F., & Ginsberg, J. (2017). An overview of HRV metrics and norms. [Frontiers in Public Health](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full)
- Quigley, K. S., et al. (2024). Publication guidelines for HR and HRV studies in Psychophysiology—Part 1. [Wiley link](https://onlinelibrary.wiley.com/doi/10.1111/psyp.14604)
- Nunan, D., et al. (2010). Normal values for short-term HRV in healthy adults. [PubMed](https://pubmed.ncbi.nlm.nih.gov/20663071/)
- HR correction and respiration influences in HRV (methodological considerations). [Frontiers in Physiology, 2016](https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2016.00356/full)
- Laborde, S., Mosley, E., & Thayer, J. F. (2017). HRV in psychophysiology—planning, analysis, reporting. [Frontiers in Psychology](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2017.00213/full)


## Research-backed improvement roadmap (Nov 2025)

### Diurnal wearable HRV baselines for CKD and metabolic phenotypes
- The Chronic Renal Insufficiency Cohort (CRIC) analysed approximately 50 ± 9 hours of wearable ECG per participant (n = 458) and showed that diabetes reduced SDNN by 7.4 ms while higher proteinuria (uPCR ≥ 0.2) lowered SDNN by 5.7 ms, underscoring time-of-day and comorbidity effects on HRV [npj Digital Medicine 2025](https://www.nature.com/articles/s41746-025-02010-5).
- **Proposed feature:** add a diurnal baseline engine that tags each segment by local clock time, sleep/wake status, and renal/metabolic phenotype so readiness scores compare like-for-like contexts.
- **Quality gains:** encourage uploads of ≥48 h wearable exports, surface recording coverage/motion artefact ratios, and allow phenotype filters (CKD stage, diabetes, proteinuria) when computing baselines or trend alerts.

### Anticipatory stress & workload reactivity testing
- A Unity-based mental arithmetic paradigm showed graded task difficulty produced significant anticipatory SDNN suppressions that paralleled NASA‑TLX workload scores in healthy adults [Journal of Physiological Anthropology 2025](https://jphysiolanthropol.biomedcentral.com/articles/10.1186/s40101-025-00413-7).
- **Proposed feature:** integrate a “Cognitive Challenge” tab with standardised low/medium/high arithmetic blocks, automated PRE/ANTICIPATION/TASK/RECOVERY segmentation, SDNN/RMSSD deltas, and embedded NASA‑TLX style questionnaires.
- **Quality gains:** extend the deviation detector to flag sensitisation (progressive vagal withdrawal across repeated anticipatory blocks) so occupational or aerospace users can quantify resilience training effects.

### Neuromodulation & rehabilitation session monitoring
- High-intensity paired associative stimulation (TMS + peripheral nerve stimulation) in cervical SCI patients used continuous HRV to verify the protocol did not provoke unsafe autonomic swings despite occasional discomfort reports [Scientific Reports 2025](https://www.nature.com/articles/s41598-025-25802-x).
- **Proposed feature:** allow clinicians to bookmark PRE/STIM/POST windows for neuromodulation, log stimulation parameters, and compare SDNN/RMSSD/HF trajectories across visits to document autonomic safety.
- **Quality gains:** define personalised confidence intervals for session phases and emit warnings/exports when parasympathetic suppression exceeds expected ranges, supporting IRB and rehabilitation documentation.

### Cycle-aware readiness for healthy menstruating individuals
- In a sample of 116 healthy participants wearing Oura rings, heart rate was lowest during menses, and RMSSD dipped in the late-luteal phase for younger adults while midlife adults showed lower overall RMSSD and higher activity [Chronobiol Int 2024; PubMed 39108015](https://pubmed.ncbi.nlm.nih.gov/39108015/).
- **Proposed feature:** add an optional menstrual phase tracker that ingests LH-kit or diary markers, annotates HRV windows by phase, and compares current SDNN/RMSSD against phase-matched baselines to avoid false “low readiness” alerts in healthy users.
- **Quality gains:** report phase-stratified trends, surface expected amplitude/mesor differences by age band, and document when HRV deviations exceed the individual’s historical menstrual oscillation.

### HRV biofeedback for healthy stress management
- A randomized active-controlled trial in healthy university students (10×20 min sessions) showed HRV biofeedback increased resting vagally mediated HRV compared with control, especially in participants with higher pre-training RMSSD [Applied Psychophysiology & Biofeedback 2024; PubMed 38888656](https://pubmed.ncbi.nlm.nih.gov/38888656/). Ongoing HeartBEAM work is extending daily slow-paced breathing protocols to healthy older adults to test cognitive and biomarker benefits [Trials 2024; PubMed 38491546](https://pubmed.ncbi.nlm.nih.gov/38491546/).
- **Proposed feature:** bundle a guided HRV-biofeedback mode (paced breathing + live coherence gauge) with automatic tracking of adherence, resting vmHRV gains, and participant stratification by baseline RMSSD to identify likely responders.
- **Quality gains:** support configurable training blocks (e.g., 10 sessions/3 weeks), aggregate vmHRV deltas into longitudinal dashboards, and expose exportable adherence + outcome summaries for wellness coaches or research protocols.

### Everyday wearable fusion for lifestyle monitoring
- A 2024 engineering study demonstrated a ring-shaped device that simultaneously captures ECG, PPG, galvanic skin response, and motion to derive HRV and other physiological indices comfortably in daily life [Biosensors 2024; PubMed 38667198](https://pubmed.ncbi.nlm.nih.gov/38667198/).
- **Proposed feature:** generalise the import pipeline to accept multi-sensor wearable exports (RR + PPG + skin conductance), automatically align modalities, and enrich the dashboard with composite stress/sympathetic proxies to serve healthy users tracking training load, sleep, and mood.
- **Quality gains:** add signal-quality diagnostics per modality, allow cross-checking RR intervals derived from ECG vs PPG, and provide plug-ins for ring/watch ecosystems so everyday users can run the HRV analyses without lab-grade hardware.

---

## Advanced HRV Metrics Roadmap (Nov 2025)

### Heart Rate Fragmentation (HRF) metrics
Heart rate fragmentation captures non-autonomic components of short-term variability that traditional HRV measures miss. The PROOF-AF study (18-year follow-up, n=1011 aged 65) found that increased **Percentage of Inflection Points (PIP)** and reduced **α1 fractal index** independently predicted atrial fibrillation occurrence, outperforming classical HRV markers alone [EHJ Open 2025; DOI 10.1093/ehjopen/oeaf030](https://doi.org/10.1093/ehjopen/oeaf030). Additional HRF metrics include:
- **PIP_H / PIP_S** (hard and soft inflection points) — quantify abrupt vs gradual beat-to-beat direction changes.
- **Word distributions (W₀–W₃)** — count 4-beat sequences by number of inflection points; elevated W₃ correlates with ANS breakdown.
- **IALS (Inverse Average Length of Segments)** — captures how frequently acceleration/deceleration runs are interrupted.
- **Proposed feature:** add HRF panel (PIP, PIP_H, PIP_S, W₀–W₃, IALS) alongside existing Poincaré and entropy tabs; flag elevated fragmentation as a potential arrhythmia-risk marker for users aged 60+.
- **Quality gains:** improve ectopic-beat filtering before HRF computation; provide reference bands from PROOF cohort.

### Nonlinear and entropy metrics expansion
Recent systematic reviews confirm entropy measures capture complexity lost in linear HRV:
- **Sample Entropy (SampEn)** and **Approximate Entropy (ApEn)** — quantify irregularity; reduced in cardiovascular disease and aging [Frontiers Neurology 2025; DOI 10.3389/fneur.2025.1636983](https://doi.org/10.3389/fneur.2025.1636983).
- **Permutation Entropy (PermEn)** — robust to noise; useful for real-world wearable data [medRxiv 2025.01.07.25320157](https://www.medrxiv.org/content/10.1101/2025.01.07.25320157).
- **Multiscale Entropy (MSE)** — assesses complexity across time scales; sex differences observed at coarse scales [IEEE ESGCO 2024; DOI 10.1109/ESGCO63003.2024.10767001](https://doi.org/10.1109/ESGCO63003.2024.10767001).
- **Multiscale-Multifractal DFA (MMF-DFA)** — identifies shift-worker cardiovascular stress via altered fractal scaling at short scales [Front. Neuroergonomics 2024; DOI 10.3389/fnrgo.2024.1382919](https://doi.org/10.3389/fnrgo.2024.1382919).
- **Proposed feature:** add selectable entropy panel (SampEn, ApEn, PermEn) with configurable embedding dimension (m) and tolerance (r); expose MMF-DFA for advanced users.
- **Quality gains:** provide age- and sex-stratified entropy norms from published datasets.

### Poincaré plot enhancements
Poincaré plots (SD1, SD2, SD1/SD2) are widely used but mathematically equivalent to RMSSD/SDNN [Entropy 2025; DOI 10.3390/e27080861](https://doi.org/10.3390/e27080861). Novel extensions add value:
- **Motion path analysis** — tracks dynamic progression of successive points rather than static ellipse descriptors [medRxiv 2025.03.21.25324311](https://www.medrxiv.org/content/10.1101/2025.03.21.25324311).
- **CSI (Cardiac Sympathetic Index)** and **CVI (Cardiac Vagal Index)** — derived from SD1/SD2 ratio; useful for autonomic balance tracking.
- **Proposed feature:** overlay motion-path trajectories on Poincaré scatter; compute CSI/CVI and display alongside SD1/SD2.

### Wearable-derived HRV for mental health monitoring
A 4-week longitudinal study (n=47) using smartwatch PPG found RMSSD, SDNN, SDSD, LF, and LF/HF negatively correlated with PHQ-9 depression and GAD-7 anxiety scores, though parasympathetically biased metrics showed weaker correlations [Frontiers Psychiatry 2024; DOI 10.3389/fpsyt.2024.1371946](https://doi.org/10.3389/fpsyt.2024.1371946). Wearable HRV across menstrual cycles showed inverse associations with premenstrual disorder symptoms, stronger for affective than physiological symptoms [medRxiv 2024.10.27.24316196](https://doi.org/10.1101/2024.10.27.24316196).
- **Proposed feature:** integrate optional mood/symptom diary with HRV trends; compute rolling correlations between vmHRV and self-reported scores.

### Exercise modality effects on HRV
A 2024 network meta-analysis of 16 RCTs (n=623) found HIIT most effective for improving SDNN, RMSSD, and LF/HF; resistance training best for HF power; combined training best for LF power [Reviews Cardiovasc Med 2024; DOI 10.31083/j.rcm2501009](https://doi.org/10.31083/j.rcm2501009). A separate meta-analysis (16 RCTs) confirmed exercise training enhances SDNN, RMSSD, and HF, with effects moderated by sex, age, and exercise type [Cureus 2024; DOI 10.7759/cureus.62465](https://doi.org/10.7759/cureus.62465).
- **Proposed feature:** add training-type tags to sessions; generate modality-specific HRV response summaries.

### Reference values for older adults
A 2024 systematic review found wide variability in HRV reference values for older adults (n=21–6250 across 11 studies) due to non-standardised methods [Psychophysiology 2024; DOI 10.1111/psyp.14661](https://doi.org/10.1111/psyp.14661). Normative data for children (linear and nonlinear indices) were published in 2024 [Clin Auton Res 2024; DOI 10.1007/s10286-024-01056-x](https://doi.org/10.1007/s10286-024-01056-x).
- **Proposed feature:** allow user to select age bracket and display corresponding percentile bands from published norms.

---

## Sleep Metrics Development Roadmap (Nov 2025)

### Rationale
Sleep quality, quantity, and staging are tightly coupled with HRV and autonomic health. Integrating actigraphy-based sleep analysis enables users to correlate nocturnal HRV with sleep architecture, supporting holistic readiness and recovery dashboards.

### Key sleep metrics to implement
| Metric | Definition | Clinical relevance |
|--------|------------|--------------------|
| **Total Sleep Time (TST)** | Minutes scored as sleep within the sleep period | Primary measure of sleep quantity |
| **Time in Bed (TIB)** | Minutes from lights-off to final awakening | Denominator for efficiency |
| **Sleep Efficiency (SE)** | TST / TIB × 100% | <85% suggests insomnia; target ≥90% |
| **Sleep Onset Latency (SOL)** | Minutes from lights-off to first sleep epoch | >30 min indicates difficulty initiating sleep |
| **Wake After Sleep Onset (WASO)** | Minutes awake after initial sleep onset | Elevated WASO indicates sleep fragmentation |
| **Number of Awakenings** | Count of wake bouts during sleep period | Correlates with subjective sleep quality |
| **Sleep Stages (N1, N2, N3/SWS, REM)** | Percentage or minutes per stage | Deep sleep (N3) and REM are restorative; imbalance may signal disorders |

### Open-source libraries for sleep analysis
1. **GGIR** (R package) — the research community standard for raw accelerometer processing; validated against PSG for sleep/wake classification in adults and children [J Meas Phys Behav 2019; DOI 10.1123/jmpb.2018-0063](https://cran.r-project.org/package=GGIR). Recent 2024 validation in paediatric populations confirms reasonable agreement with PSG [Sleep 2025; DOI 10.1093/sleep/zsaf282](https://doi.org/10.1093/sleep/zsaf282).
2. **ActiSleep Tracker** (Python) — a 2025 JOSS-published dashboard for refining GGIR sleep predictions with manual adjustment [JOSS 2025; DOI 10.21105/joss.08181](https://doi.org/10.21105/joss.08181).
3. **YASA (Yet Another Spindle Algorithm)** (Python) — open-source automatic sleep staging from EEG (C4-A1, EOG, EMG); 82–83% agreement with human scorers [Sleep 2024 abstract; raphaelvallat/yasa](https://github.com/raphaelvallat/yasa). Zenodo sample data available for testing [Zenodo 2024; DOI 10.5281/zenodo.14564285](https://zenodo.org/records/14564285).
4. **PhysioEx** (Python) — a 2025 library for explainable deep-learning sleep staging with XAI support [Physiol Meas 2025; PubMed 39874654](https://pubmed.ncbi.nlm.nih.gov/39874654/).
5. **NeuroKit2** (Python) — comprehensive physiological signal processing including HRV, ECG, EDA; can derive sleep-relevant HRV features from overnight recordings [Zenodo 2024; DOI 10.5281/zenodo.15395460](https://zenodo.org/records/15395460).
6. **SleepEEGpy** (Python) — simplifies sleep EEG preprocessing and integrates with MNE-Python [ScienceDirect 2025; DOI 10.1016/j.compbiomed.2025.109839](https://doi.org/10.1016/j.compbiomed.2025.109839).

### Validation evidence
- A 2024 systematic review of actigraphy sleep staging found limited but promising ability to classify sleep stages vs PSG; heterogeneity in stage groupings limits direct comparison [J Sleep Res 2024; DOI 10.1111/jsr.14143](https://doi.org/10.1111/jsr.14143).
- Deep-learning models combining actigraphy + coarse HR achieve 78.7% accuracy for 3-stage (Wake/NREM/REM) and 72.5% for 4-stage classification [SLEEP 2021; DOI 10.1093/sleep/zsab072.249](https://doi.org/10.1093/sleep/zsab072.249). A 2025 LSTM approach in children showed similar performance [J Sleep Res 2025; DOI 10.1111/jsr.70149](https://doi.org/10.1111/jsr.70149).
- Instantaneous HR from single-lead ECG achieves 72.8% accuracy on 4-class staging and 87.7% on sleep/wake, outperforming pure actigraphy [ERJ Open Res 2021; DOI 10.1183/23120541.SLEEPANDBREATHING-2021.63](https://doi.org/10.1183/23120541.SLEEPANDBREATHING-2021.63).

### Proposed implementation plan
1. **Phase 1 — Actigraphy import:** accept raw accelerometer files (ActiGraph .gt3x, GENEActiv .bin, Axivity .cwa); wrap GGIR via `rpy2` or call R subprocess; compute TST, TIB, SE, SOL, WASO, awakenings.
2. **Phase 2 — Sleep diary integration:** allow user to input lights-off/on times and subjective quality ratings; compare objective vs subjective metrics.
3. **Phase 3 — HRV-sleep fusion:** align overnight RR intervals with sleep epochs; compute per-stage HRV (e.g., RMSSD during N3 vs REM); surface in dashboard.
4. **Phase 4 — Optional EEG staging:** if user provides EEG/EOG/EMG, invoke YASA or PhysioEx for automatic staging; display hypnogram alongside HRV time series.
5. **Quality gains:** provide signal-quality checks for accelerometer data; flag nights with <4 h TST or SE <70% for review; export sleep summaries in CSV/JSON.

---

## Consumer Smartwatch & Wearable Integration (Nov 2025)

### Garmin Vivosmart 5 — Device Profile

| Attribute | Value |
|-----------|-------|
| **Sensors** | Garmin Elevate optical HR (PPG), 3-axis accelerometer, ambient light, pulse oximeter (SpO₂) |
| **HRV capability** | 24/7 HR tracking; overnight HRV RMSSD (5-min intervals) during configured sleep window; no beat-to-beat RR export via Connect app |
| **Sleep tracking** | Automatic sleep detection via actigraphy + PPG; stages (light, deep, REM) shown in Garmin Connect; ~70% accuracy vs PSG per Garmin validation study |
| **Body Battery / Stress** | Proprietary composite score derived from HRV, stress, activity, and sleep |
| **Data export options** | (1) Per-activity .FIT file via Garmin Connect web ("Export Original"); (2) Bulk wellness export (JSON) via Account Settings → Export Wellness Data; (3) Unofficial API via `garminconnect` Python library |
| **Limitations** | Optical HR sensor less accurate than chest strap for beat-level HRV; no raw RR intervals in standard export; requires workaround for continuous HRV data |

### Data access pathways

#### 1. Garmin Connect Wellness Export (official)
- Navigate to **Account Settings → Account Information → Export Wellness Data**.
- Garmin emails a ZIP containing JSON files under `DI_CONNECT/DI-Connect-Wellness/`:
  - `*_sleepData.json` — nightly sleep stages, duration, scores.
  - `*_hrvData.json` — overnight HRV RMSSD summaries (5-min epochs).
  - `*_stressData.json` — stress level time series.
  - `*_heartRateData.json` — minute-level HR.
- **Pros:** official, no API keys; **Cons:** manual, no real-time, limited granularity.

#### 2. FIT file export (per activity)
- In Garmin Connect web, open an activity → gear icon → **Export Original** → `.FIT` file.
- Parse with **fitparse** or **fitdecode** Python libraries.
- FIT files from some devices include `hrv` records with beat-to-beat RR intervals during activities.
- **Vivosmart 5 limitation:** wellness/sleep FIT files typically lack raw RR; activity FIT files may include HR but not beat-level HRV.

#### 3. Unofficial `garminconnect` Python library
- GitHub: [cyberjunky/python-garminconnect](https://github.com/cyberjunky/python-garminconnect)
- Provides programmatic access to Garmin Connect data (sleep, HR, HRV, stress, activities).
- Requires Garmin Connect credentials (stored securely via `.env` or keyring).
- Example endpoints:
  - `get_sleep_data(date)` — sleep stages, scores.
  - `get_hrv_data(date)` — overnight HRV RMSSD.
  - `get_heart_rates(date)` — minute-level HR.
  - `download_activity(activity_id)` — raw FIT bytes.
- **Caution:** unofficial API; may break with Garmin updates; use rate limiting.

### Recommended Python libraries

| Library | Purpose | Install |
|---------|---------|---------|
| **garminconnect** | Unofficial Garmin Connect API wrapper | `pip install garminconnect` |
| **fitparse** | Parse ANT/Garmin .FIT files | `pip install fitparse` |
| **fitdecode** | Alternative FIT parser (handles edge cases) | `pip install fitdecode` |
| **gpxpy** | Parse GPX exports (activity routes) | `pip install gpxpy` |
| **tcxreader** | Parse TCX exports | `pip install tcxreader` |

### Proposed Garmin import module (`app/garmin_import.py`)

**Scope:**
1. Authenticate to Garmin Connect via `garminconnect` (credentials from `.env`).
2. Fetch sleep, HRV, HR, and stress data for a date range.
3. Parse bulk wellness JSON export if user provides ZIP.
4. Parse individual FIT files for activity-level HRV (if available).
5. Return standardised DataFrames: `sleep_df`, `hrv_df`, `hr_df`, `stress_df`.
6. Integrate with existing HRV analysis pipeline (feed overnight RR/RMSSD into `hrv_core.py`).

**Quality controls:**
- Validate timestamps and handle timezone conversions.
- Flag nights with missing or sparse HRV data.
- Cross-check HR vs HRV consistency.
- Warn user about optical-sensor limitations for beat-level analysis.

---

## Implemented Features (Nov 2025)

### Module Integration Status

| Module | Status | Description |
|--------|--------|-------------|
| `hrv_core.py` | ✅ Complete | Core HRV computation (time, frequency, nonlinear, entropy) |
| `gauge_builder.py` | ✅ Complete | 30+ metric gauges with clinical thresholds |
| `gpt_interpretation.py` | ✅ Complete | GPT-5.1 high-reasoning interpretation |
| `publication_export.py` | ✅ Complete | APA-formatted statistical exports |
| `ml_analytics.py` | ✅ Complete | Anomaly detection, trend analysis, ML classification |
| `statistical_analysis.py` | ✅ Complete | Comprehensive inferential statistics |
| `multiday_tracker.py` | ✅ Complete | Longitudinal tracking with rolling statistics |
| `solar_physiology_correlation.py` | ✅ Complete | Solar-HRV correlation with lag analysis |
| `scientific_charts.py` | ✅ Complete | Publication-ready ECharts visualizations |
| `hrv_fragmentation.py` | ✅ Complete | HRF metrics (PIP, IALS, W0-W3) |
| `sleep_metrics.py` | ✅ Complete | Sleep staging and quality metrics |
| `garmin_import.py` | ✅ Complete | Garmin wellness data import (HR, HRV, SpO2, stress) |
| `fatigue_integration.py` | ✅ Complete | SAFTE model for fatigue prediction |
| `noaa_space.py` | ✅ Complete | NOAA space weather data integration |

### Comprehensive Gauge System (`app/gauge_builder.py`)
The app now includes a unified gauge visualization system with 30+ metrics across all HRV domains:

| Domain | Metrics |
|--------|---------|
| **Time-domain** | SDNN, RMSSD, pNN50, Mean HR, Mean NN |
| **Frequency-domain** | LF/HF ratio, HF power, LF power, Total power, HF nu, LF nu |
| **Nonlinear** | SD1, SD2, DFA α1, DFA α2 |
| **Entropy** | Sample Entropy, Approximate Entropy |
| **Fragmentation** | PIP, IALS, W3 |
| **Autonomic indices** | Parasympathetic index, Sympathetic index, ANS balance, Stress index |
| **Sleep** | Sleep efficiency, TST, WASO, SOL |

Each gauge uses:
- Modern two-ring design with lowered center detail
- Color-coded zones (green/yellow/red) based on published clinical thresholds
- Reference bands from peer-reviewed normative data (Nunan 2010, Shaffer 2017, PROOF-AF 2025)

### AI-Powered Interpretation (`app/gpt_interpretation.py`)
The GPT interpretation module now features:
- **GPT-5.1 High Reasoning**: Single model with maximum reasoning effort
- **Robust error handling**: Automatic retries with exponential backoff
- **Rate limiting**: Respects API limits with graceful degradation
- **Local fallback**: Rule-based interpretation when API unavailable
- **Confidence scoring**: Reports model used and confidence level

### Publication-Ready Exports (`app/publication_export.py`)
Export utilities for Q1 journal submissions:
- **Statistical summaries**: Mean ± SD, Median [IQR], 95% CI (APA 7th edition format)
- **Effect size calculations**: Cohen's d, Hedges' g with interpretation
- **Correlation matrices**: Pearson r with p-values and significance markers
- **Normality testing**: Shapiro-Wilk with skewness/kurtosis
- **LaTeX table generation**: Publication-ready table code
- **Reproducibility metadata**: Software versions, parameters, data hashes

### Statistical Analysis (`app/statistical_analysis.py`)
Comprehensive inferential statistics for publication:
- **Descriptive statistics**: Mean, SD, SEM, median, IQR, percentiles, skewness, kurtosis
- **Normality testing**: Shapiro-Wilk with automatic test selection
- **Group comparisons**: Independent/paired t-tests, Mann-Whitney U, Wilcoxon, ANOVA, Kruskal-Wallis
- **Effect sizes**: Cohen's d, Hedges' g, η², ω² with verbal interpretation
- **Multiple comparison corrections**: Bonferroni, FDR (Benjamini-Hochberg)
- **Correlation analysis**: Pearson, Spearman with 95% CI
- **Regression**: Linear regression with AIC/BIC model selection

### ML Analytics (`app/ml_analytics.py`)
Machine learning features for advanced analysis:

**Anomaly Detection**:
- Z-score method (parametric)
- IQR method (non-parametric)
- MAD method (robust to outliers)
- Isolation Forest (multivariate)
- Local Outlier Factor (density-based)

**Trend Analysis**:
- Linear trend detection with significance testing
- Change point detection using PELT-like algorithm
- Segment classification with per-segment statistics
- Rolling statistics (mean, std, min, max)

**Predictive Modeling**:
- Feature importance ranking (correlation-based)
- Readiness prediction from historical data
- HRV state classification (optimal/normal/suboptimal/concerning)

### Multi-day Longitudinal Tracking (`app/multiday_tracker.py`)
Track HRV, sleep, and activity across multiple days:
- **Daily records**: HRV, sleep, and activity metrics per day
- **Rolling statistics**: 7-day rolling mean, SD, min, max
- **Trend analysis**: Linear trend with significance testing
- **Intervention analysis**: Pre/post comparison with effect sizes
- **Alert system**: Configurable thresholds for attention/warning/critical
- **Recommendations**: Automated suggestions based on trends

### Solar-Physiology Correlation (`app/solar_physiology_correlation.py`)
Analyze relationships between space weather and physiology:
- **Solar metrics**: Kp index, Dst, F10.7 flux, solar wind, X-ray flux
- **Physiological metrics**: HRV, sleep, activity, ANS balance
- **Lag analysis**: Test correlations at 0-7 day lags
- **Significance classification**: Marginal, significant, highly significant
- **Correlation strength**: Negligible, weak, moderate, strong, very strong
- **Comprehensive reports**: Publication-ready correlation summaries

### Scientific Charts (`app/scientific_charts.py`)
Publication-ready visualizations using ECharts:
- **HRV time series**: Multi-metric synchronized timeline
- **Frequency domain**: PSD with band highlighting
- **Poincaré plot**: SD1/SD2 ellipse with scatter
- **Hypnogram**: Sleep stage visualization
- **Sleep architecture**: Stage distribution pie/bar charts
- **ANS balance gauge**: Sympathovagal balance indicator
- **Multi-day trends**: Rolling statistics with confidence bands
- **Correlation heatmap**: Inter-metric correlation matrix
- **ML pattern chart**: Anomalies, trends, change points

### Unified Physiological Timeline (`app/app.py`)
New tab for synchronized multi-metric visualization:
- **Cross-domain analysis**: HRV, cardiac, respiratory, stress metrics
- **ML pattern detection**: Real-time anomaly and trend detection
- **Correlation matrix**: Interactive heatmap of metric relationships
- **Automated interpretation**: Significant findings highlighted

### Heart Rate Fragmentation (`app/hrv_fragmentation.py`)
Complete HRF metrics per PROOF-AF study methodology:
- PIP, PIP_H, PIP_S (inflection point percentages)
- W0–W3 (word distributions)
- IALS (Inverse Average Length of Segments)
- PSS, PAS (Short/Alternating Segment percentages)

### Sleep Metrics (`app/sleep_metrics.py`)
Sleep analysis from actigraphy/wearable data:
- TST, TIB, Sleep Efficiency
- SOL, WASO, Number of Awakenings
- Sleep stage percentages (N1, N2, N3, REM)
- Quality interpretation based on clinical thresholds

### Garmin Integration (`app/garmin_import.py`)
Support for Garmin Vivosmart 5 and compatible devices:
- Authentication via `garminconnect` library
- Fetch sleep, HRV, HR, stress, SpO2, respiration, body battery data
- Parse wellness export ZIP files
- Parse individual FIT files
- Time-synchronized physiological data structure
- Quality checks and timestamp validation

### SAFTE Fatigue Prediction (`app/fatigue_integration.py`)
Biomathematical model for cognitive performance prediction:
- **Homeostatic process**: Sleep pressure accumulation during wakefulness
- **Circadian process**: 24h + 12h biological rhythms
- **Sleep inertia**: Post-sleep grogginess modeling
- **Performance prediction**: Hourly effectiveness estimates
- **Risk assessment**: Fatigue risk scoring with factor breakdown
- **Recommendations**: Automated sleep/work schedule suggestions

---

## Suggested Future Implementations (Science-Based Roadmap)

### 1. Real-Time HRV Streaming & Biofeedback
**Scientific basis:** A 2024 systematic review showed HRV biofeedback (10×20 min sessions) significantly increased resting vagally-mediated HRV in healthy adults, with stronger effects in those with higher baseline RMSSD [Appl Psychophysiol Biofeedback 2024; PubMed 38888656].

**Proposed features:**
- Live RR interval streaming via Polar H10 SDK or BLE heart rate monitors
- Real-time coherence gauge with paced breathing guide
- Session tracking with adherence metrics
- Pre/post vmHRV comparison dashboard

**Implementation priority:** High — enables active intervention rather than passive monitoring

### 2. Wearable Data Fusion (Multi-Sensor)
**Scientific basis:** Ring-shaped devices combining ECG, PPG, galvanic skin response, and accelerometry achieve robust HRV estimation in daily life [Biosensors 2024; PubMed 38667198]. Multi-modal fusion improves signal quality and enables comprehensive stress assessment.

**Proposed features:**
- Import from Oura Ring, Whoop, Apple Watch, Fitbit
- Cross-validate RR intervals from ECG vs PPG sources
- Skin conductance integration for sympathetic arousal proxy
- Signal quality scoring per modality

**Implementation priority:** High — expands user base and data richness

### 3. Circadian & Chronotype-Aware Analysis
**Scientific basis:** The CRIC study (n=458) demonstrated significant time-of-day effects on HRV, with diabetes and proteinuria modulating diurnal patterns [npj Digital Medicine 2025]. Menstrual phase tracking in Oura Ring users showed RMSSD dips in late-luteal phase [Chronobiol Int 2024; PubMed 39108015].

**Proposed features:**
- Diurnal baseline engine with hourly HRV norms
- Chronotype questionnaire (MEQ) integration
- Menstrual phase tracking with phase-matched baselines
- Shift-work pattern detection and alerting

**Implementation priority:** Medium — improves baseline accuracy

### 4. Cognitive Load & Mental Health Monitoring
**Scientific basis:** A Unity-based mental arithmetic paradigm showed graded anticipatory SDNN suppression paralleling NASA-TLX workload scores [J Physiol Anthropol 2025]. Wearable HRV correlated negatively with PHQ-9 depression and GAD-7 anxiety scores over 4 weeks [Front Psychiatry 2024; DOI 10.3389/fpsyt.2024.1371946].

**Proposed features:**
- Cognitive challenge tab with standardized tasks (N-back, arithmetic)
- PRE/ANTICIPATION/TASK/RECOVERY automatic segmentation
- Optional mood/symptom diary with rolling HRV correlations
- Workload estimation from HRV patterns

**Implementation priority:** Medium — valuable for occupational health

### 5. Advanced Entropy & Complexity Metrics
**Scientific basis:** Recent systematic reviews confirm entropy measures capture complexity lost in linear HRV analysis [Front Neurol 2025; DOI 10.3389/fneur.2025.1636983]. Multiscale entropy shows sex differences at coarse scales [IEEE ESGCO 2024].

**Proposed features:**
- Multiscale Entropy (MSE) with configurable scale range
- Fuzzy Entropy for improved noise robustness
- Recurrence Quantification Analysis (RQA) expansion
- Symbolic dynamics with customizable word length

**Implementation priority:** Medium — enhances nonlinear analysis depth

### 6. Exercise Training Response Tracking
**Scientific basis:** A 2024 network meta-analysis (16 RCTs, n=623) found HIIT most effective for SDNN/RMSSD improvement, resistance training best for HF power, combined training best for LF power [Rev Cardiovasc Med 2024; DOI 10.31083/j.rcm2501009].

**Proposed features:**
- Training type tagging (HIIT, resistance, endurance, combined)
- Modality-specific HRV response curves
- Training load estimation from HRV suppression/recovery
- Overtraining risk alerts based on chronic HRV trends

**Implementation priority:** Medium — valuable for athletes and coaches

### 7. Age-Stratified Reference Values
**Scientific basis:** A 2024 systematic review found wide variability in HRV reference values for older adults due to non-standardized methods [Psychophysiology 2024; DOI 10.1111/psyp.14661]. Pediatric normative data were published in 2024 [Clin Auton Res 2024; DOI 10.1007/s10286-024-01056-x].

**Proposed features:**
- Age bracket selection (pediatric, young adult, middle-aged, older adult)
- Sex-stratified percentile bands from published norms
- Automatic flagging when values deviate from age-matched norms
- Longitudinal aging trajectory visualization

**Implementation priority:** Medium — improves clinical interpretation

### 8. Neuromodulation Session Monitoring
**Scientific basis:** TMS + peripheral nerve stimulation protocols in SCI patients used continuous HRV to verify autonomic safety [Sci Rep 2025; DOI 10.1038/s41598-025-25802-x].

**Proposed features:**
- PRE/STIM/POST window bookmarking
- Stimulation parameter logging
- Autonomic safety threshold monitoring
- Cross-session trajectory comparison

**Implementation priority:** Low — specialized clinical use

### 9. Arrhythmia Risk Stratification
**Scientific basis:** The PROOF-AF study (18-year follow-up, n=1011) found elevated PIP and reduced DFA α1 independently predicted atrial fibrillation [EHJ Open 2025; DOI 10.1093/ehjopen/oeaf030].

**Proposed features:**
- AF risk score combining PIP, α1, and traditional HRV
- Ectopic beat burden estimation
- Long-term rhythm stability tracking
- Clinical alert thresholds with sensitivity/specificity trade-offs

**Implementation priority:** Low — requires clinical validation

### 10. Cloud-Based Multi-User Research Platform
**Scientific basis:** Large-scale HRV studies require standardized data collection, quality control, and analysis pipelines across multiple sites.

**Proposed features:**
- Secure cloud storage with HIPAA/GDPR compliance
- Multi-site study management dashboard
- Automated data quality scoring
- Batch analysis with reproducibility metadata
- Export to BIDS format for neuroimaging integration

**Implementation priority:** Low — infrastructure-heavy

---

## Notes on App Implementation

- QC heuristics are transparent and bounded; they are not a substitute for full ECG beat annotation or clinical-grade editing. For high-stakes analyses, consider manual review.
- Frequency methods include Welch (default), Periodogram, and an AR (Yule–Walker) approximation for educational comparison; results differ across methods and settings.
- Entropy defaults (m=2, r=0.2·SD) follow common practice for short-term HRV but should be adjusted for specific study aims and lengths when needed.
- Deviation detection relies on robust statistics within the current session. Review flagged windows alongside qualitative notes rather than treating them as automated diagnoses.
- Readiness scoring mirrors Kubios percentile categories for familiarity but should complement—never replace—clinical evaluation or longitudinal decision-making.
- AI interpretation uses GPT models when available; local rule-based fallback ensures functionality without API access.
- Publication exports follow APA 7th edition guidelines and include all statistical details required for peer review.


