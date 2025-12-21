# Physiological, Chronobiological, and Operational Foundations of a Multimodal Human-Performance Console
## A literature review aligned to the “Mission Control – Flight Surgeon” platform

**Document type:** Narrative literature review (IMRaD-structured)

**Scope note:** This paper synthesizes peer-reviewed scientific literature and US/EU governmental technical documents that underpin the analytic modules implemented in the *Mission Control – Flight Surgeon* application: HRV signal processing and interpretation; circadian modelling and light scheduling; fatigue forecasting and FRMS-style governance; blood-pressure variability; wearable acquisition; and integration of space-weather context (NOAA/NASA) with time-aligned physiological analytics.

---

## Abstract
**Background:** High-consequence aviation and space operations require continuous monitoring of physiological readiness under fluctuating sleep opportunity, circadian misalignment, workload, and environmental exposures. Modern field systems increasingly combine short-term heart rate variability (HRV) features, wearable-derived sleep metrics, circadian modelling, and biomathematical fatigue forecasts to support decision-making. Yet each component has non-trivial methodological dependencies (signal quality, protocol control, confounding, multiple testing) that determine whether outputs are interpretable and operationally safe.

**Objective:** To review the scientific and technical foundations relevant to a multimodal “flight surgeon console” approach, focusing on: (i) HRV standards, preprocessing, and interpretation across time/frequency/nonlinear domains; (ii) validated autonomic function testing paradigms; (iii) circadian pacemaker models and experimentally derived light phase-response curves; (iv) fatigue science, performance measurement, and biomathematical fatigue modelling; (v) blood pressure variability (BPV) as an autonomic/vascular risk construct; (vi) evidence on wearable acquisition validity; and (vii) the state of evidence linking space-weather indices to autonomic/cardiovascular outcomes.

**Methods:** A targeted narrative review was performed using CrossRef and Semantic Scholar via MCP `paper-search` to identify peer-reviewed articles and high-impact consensus statements. US and European governmental/agency technical documents were collected from NOAA SWPC, NASA/CCMC, FAA, Department of the Air Force, EASA, and ESA repositories. Literature was synthesized thematically along the major modules implemented in the app and app-adjacent operational requirements (auditability, reproducibility, conservative risk communication).

**Results:** HRV is a robust noninvasive marker of autonomic regulation when measurement protocols are standardized and analyses respect known physiological constraints (record length requirements, respiration effects, ectopy/artifact handling). Contemporary guidance emphasizes transparent preprocessing and cautious interpretation of frequency-domain ratios, including the well-documented limitations of LF/HF as a sympathovagal “balance” surrogate. Circadian models (limit-cycle oscillators with light preprocessing) can predict phase and entrainment under controlled assumptions and are supported by rigorous human light phase-response curve experiments. Fatigue risk is dominated by sleep loss, time awake, and circadian phase, with objective vigilance testing (PVT-family) offering sensitive, repeatable measurement of the operational failure mode. Biomathematical models such as SAFTE/FAST provide useful forecasts when calibrated and embedded within FRMS governance rather than treated as standalone truth. Evidence associating geomagnetic activity with HRV and cardiovascular endpoints exists but is heterogeneous; effect sizes are generally small and vulnerable to confounding and time-series artefacts.

**Conclusions:** A multimodal console can be scientifically defensible if it prioritizes (i) signal validity and protocol metadata; (ii) within-person baselines; (iii) transparent modelling assumptions; (iv) conservative uncertainty communication; and (v) governance frameworks (FRMS-style) that separate “decision support” from clinical diagnosis.

**Keywords:** heart rate variability; circadian rhythms; fatigue risk management; SAFTE; psychomotor vigilance test; blood pressure variability; wearable sensors; space weather; aerospace medicine.

---

## 1. Introduction
### 1.1. Why a multimodal “flight surgeon console” exists
Human performance failures in aviation and spaceflight rarely arise from a single physiological pathway. Operational impairment is typically multi-determined by sleep restriction, circadian misalignment, prolonged wakefulness, high workload, stress, and—especially in exploration analogs—environmental perturbations that modulate autonomic regulation and recovery. Because subjective insight into impairment can be unreliable under fatigue, safety-critical contexts increasingly seek objective or quasi-objective proxies: vigilance tests, sleep opportunity tracking, and physiological signals that reflect autonomic state.

Heart rate variability (HRV) has emerged as an attractive candidate because it is noninvasive, comparatively easy to acquire in the field, and interpretable (within constraints) as a measure of autonomic modulation of the sinoatrial node (Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology, 1996; Shaffer & Ginsberg, 2017). However, HRV is not a monolithic biomarker. It is a family of features computed from interbeat interval (IBI/RR) series, and it is sensitive to measurement context (posture, respiration, time of day), signal quality (ectopy, motion artefact), and modelling/processing choices (filtering, detrending, spectral estimation). Consequently, building an operational tool around HRV requires careful alignment with standards and a principled treatment of uncertainty.

Parallel developments in chronobiology and fatigue science provide complementary structure. The circadian pacemaker can be modelled using biologically motivated oscillators with light preprocessing, allowing prediction of phase shifts and entrainment under known light schedules (Forger et al., 1999; Hannay et al., 2019). Human phase-response curves (PRCs) derived from carefully controlled melatonin-based protocols quantify when light exposure delays or advances circadian phase (Khalsa et al., 2003; St Hilaire et al., 2012). Fatigue science shows dose-response impairment from sleep loss and extended wakefulness, especially for vigilant attention, which is directly measured by psychomotor vigilance testing (PVT) and related tasks (Van Dongen et al., 2003; Belenky et al., 2003; Basner et al., 2021). Biomathematical fatigue models operationalize these principles into forecasts, but they require governance frameworks (fatigue risk management systems, FRMS) that treat model outputs as risk indicators rather than deterministic truth (Dawson et al., 2011; Federal Aviation Administration [FAA], 2013).

The *Mission Control – Flight Surgeon* platform integrates these scientific domains into a single app: HRV analysis across time/frequency/nonlinear domains; circadian simulation and light scheduling; fatigue forecasting (SAFTE-family) and FRMS-like dashboards; population norms and personalized baselines; blood pressure variability analytics; wearable ingestion; and integration of space-weather data from NOAA SWPC and NASA DONKI for time-aligned exploratory correlations. This review therefore takes a “module-aligned” approach: it synthesizes the literature base for each module and emphasizes methodological dependencies that determine whether outputs are meaningful.

### 1.2. A note on interpretation vs. diagnosis
HRV and related autonomic measures are probabilistic indicators. Low HRV is associated with elevated risk in multiple contexts, but it is not a diagnosis. Conversely, higher HRV is often interpreted as “better,” yet pathologically irregular rhythms (e.g., atrial fibrillation) can produce high variability that is not salutary. A system intended for operational decision support must therefore distinguish: (i) signal validity (is the RR series physiologically plausible and free of ectopy/artefact?); (ii) within-person change (is today different from this individual’s baseline under similar conditions?); and (iii) clinical interpretation (what does a deviation plausibly mean given confounders?). Contemporary reporting recommendations explicitly advocate documenting measurement conditions and preprocessing steps to prevent overinterpretation (Laborde et al., 2017).

### 1.3. Controversies that matter operationally
Three controversies are especially operationally relevant.

First, frequency-domain interpretation—particularly the LF/HF ratio—has a long history of being used as a proxy for “sympathovagal balance.” This interpretation is widely contested because LF power reflects baroreflex-related modulation with mixed sympathetic and parasympathetic contributions, and because the autonomic nervous system is nonlinear and context dependent. Direct critiques show that LF/HF is not a reliable measure of sympathovagal balance (Billman, 2013). Operational software that reports LF/HF should therefore treat it as a descriptive spectral feature, not a mechanistic readout.

Second, short-term measurements are often repurposed for readiness scoring. While short-term RMSSD-based features can be reproducible and useful as within-person markers, they are sensitive to protocol variability (posture, paced breathing) and require stable acquisition and preprocessing. Large systematic reviews show substantial inter-individual variability even among “healthy” adults, which limits purely population-based classification (Nunan et al., 2010).

Third, evidence linking space weather to human physiology is heterogeneous. Some epidemiological studies report associations between geomagnetic indices and HRV or cardiovascular outcomes (Alabdulgader et al., 2018; Vieira et al., 2022), while methodological critiques emphasize time-series pitfalls (autocorrelation, multiple comparisons) and confounding by seasonality, behavior, and air pollution. Any operational use should treat such correlations as exploratory and hypothesis-generating rather than decision-deterministic.

---

## 2. Methods
### 2.1. Review design
This is a targeted narrative literature review structured using IMRaD headings to match the app’s module architecture. The intent is not to produce a PRISMA-grade systematic review for each subtopic, but to synthesize high-value evidence and technical standards that support (or constrain) operational deployment.

### 2.2. Information sources
Peer-reviewed literature was identified using CrossRef and Semantic Scholar via MCP `paper-search`. Targeted searches were run for combinations of terms including:

- “heart rate variability standards,” “HRV reporting recommendations,” “RMSSD norms,” “artifact correction HRV,” “Kubios HRV software.”
- “Poincaré plot HRV,” “detrended fluctuation analysis heartbeat,” “sample entropy HRV,” “heart rate fragmentation.”
- “circadian pacemaker model,” “Forger Jewett Kronauer,” “human phase response curve bright light,” “circadian entrainment model Hannay.”
- “sleep restriction dose response performance,” “psychomotor vigilance test standardization,” “fatigue risk management systems,” “SAFTE FAST model.”
- “blood pressure variability clinical relevance,” “visit-to-visit blood pressure variability stroke risk.”
- “geomagnetic disturbances heart rate variability,” “solar wind heart rate variability.”
- “Polar H10 validity HRV,” “actigraphy sleep circadian,” “wearable sleep technology validation.”

Government/agency technical documents were collected from official portals:

- NOAA Space Weather Prediction Center (SWPC) product documentation (Kp index; NOAA space weather scales).
- NASA/CCMC DONKI documentation for event catalogs and API access.
- FAA advisory circulars for FRMS.
- Department of the Air Force publications for crew-rest rules.
- EASA documents (fatigue management materials; air-operations/FTL rules).
- ESA Space Weather service documentation.

### 2.3. Inclusion and prioritization criteria
Included sources were prioritized when they met one or more of the following:

1. Consensus statements or widely cited standards relevant to HRV measurement and reporting.
2. Systematic reviews or large cohort studies that provide normative ranges or quantify variability.
3. Method papers that define core analytic constructs used in the app (e.g., entropy, DFA, fragmentation) or validated processing (e.g., artefact correction).
4. Controlled circadian PRC experiments and mechanistic circadian models used in sleep/circadian scheduling.
5. High-quality fatigue/performance studies (dose-response sleep restriction; PVT standardization) and operational fatigue frameworks.
6. Governmental technical documents that define operational standards (FRMS guidance; space-weather indices and scales).

### 2.4. Synthesis approach
Evidence was synthesized thematically according to the app’s modules. Within each module, findings are presented along three axes: (i) what the metric/model is intended to represent physiologically; (ii) conditions under which it is valid or interpretable; and (iii) known limitations and operational risks.

---

## 3. Results
### 3.1. HRV as a measurement construct: physiology and standards
HRV refers to variability in the timing of successive normal-to-normal (NN) intervals and reflects the combined action of intrinsic pacemaker dynamics and autonomic modulation. The landmark Task Force statement defines time-domain, frequency-domain, and geometric measures, and emphasizes that interpretation must consider recording duration and stationarity (Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology, 1996). Subsequent syntheses highlight that HRV is shaped by multiple physiological loops operating on distinct time scales: respiratory sinus arrhythmia (RSA) at high frequency, baroreflex-mediated oscillations in the low-frequency range, and slower influences such as thermoregulation and circadian rhythms (Shaffer & Ginsberg, 2017).

A central implication for operational tools is that “HRV” is not a single value but a vector of features whose meaning depends on context. For example, RMSSD is primarily sensitive to short-term beat-to-beat variability and is often interpreted as vagally mediated under resting conditions. SDNN reflects overall variability over the measurement period and aggregates multiple mechanisms. Frequency-domain measures decompose variance into bands (HF, LF, VLF), but these bands require sufficient recording length and are sensitive to respiration.

The app’s design choice to separate analysis into time-domain, frequency-domain, nonlinear, and windowed modules aligns with the Task Force architecture, but modern reporting recommendations further stress the need to document protocol variables and preprocessing decisions (Laborde et al., 2017). For an operational console, this translates into metadata capture (posture, time-of-day, breathing protocol, recent exercise/caffeine) and explicit quality gates (artifact percentage, ectopy handling) before deriving interpretive claims.

### 3.2. Acquisition and preprocessing: why RR quality dominates downstream validity
#### 3.2.1. R-peak detection and RR interval derivation
Any HRV pipeline begins with detection of cardiac cycles. Classical ECG-based QRS detectors—such as the Pan–Tompkins algorithm—remain influential because they provide a transparent and computationally efficient method for real-time detection (Pan & Tompkins, 1985). Although modern detectors may use wavelets or machine learning, the operational requirement remains the same: missed or spurious detections produce artificial variability that contaminates HRV features.

In RR-file workflows (as used by many chest-strap systems), the user receives a sequence of interbeat intervals rather than raw ECG. This shifts responsibility to the device firmware and vendor algorithms, which may be proprietary. Therefore, operational tools should incorporate plausibility filtering (e.g., rejecting physiologically implausible RR values) and artefact correction, while clearly marking when results depend on corrected data.

#### 3.2.2. Artefact and ectopy correction
Artefacts and ectopic beats are not minor nuisances; they can dominate spectral estimates and nonlinear features. In practice, artefact correction becomes a key determinant of reproducibility. Lipponen and Tarvainen proposed a robust correction algorithm using beat classification, demonstrating a method-oriented path to reduce artefact-induced bias while preserving physiological dynamics (Lipponen & Tarvainen, 2019). Such work underpins modern HRV software packages and provides a defensible rationale for correction routines.

The Kubios HRV platform is widely used in research and provides a reference point for feature definitions and preprocessing options; its software description paper helps anchor methodological comparability across studies (Tarvainen et al., 2014). For an operational console, “Kubios-like” should not mean copying thresholds blindly, but rather adopting the same philosophy: transparent preprocessing settings, explicit reporting of correction intensity, and sensitivity analysis when results materially change after correction.

#### 3.2.3. Reliability of short-term recordings
Short-term HRV measures are appealing because they are feasible in daily operations, but reliability is not automatic. Short-term measures can be repeatable under controlled conditions, yet between-day variability and protocol sensitivity remain substantial—reinforcing the use of standardized acquisition and rolling within-person baselines rather than reliance on population thresholds (Nunan et al., 2010).

#### 3.2.4. Wearable validity for RR acquisition (brief overview)
Because the app supports chest-strap and wearable ingestion, it is important to distinguish sensor modalities.

- **ECG chest straps** (e.g., Polar systems) measure cardiac electrical activity and can provide RR intervals with high fidelity under many conditions.
- **Wrist photoplethysmography (PPG)** infers pulse-to-pulse intervals from peripheral blood-volume changes and is more susceptible to motion artefact, vasoconstriction, and algorithmic smoothing.

Validation studies indicate that the Polar H10 can provide RR intervals suitable for many HRV analyses, with caveats during higher-intensity exercise and for certain nonlinear metrics (Schaffarczyk et al., 2022). Earlier work validating Polar devices for short-term HRV similarly supports feasibility under resting conditions (Nunan et al., 2009).

For sleep and circadian estimation, actigraphy remains foundational, but consumer multi-sensor wearables introduce both promise and risk: multi-sensor systems can capture autonomic parameters at scale, yet proprietary algorithms and firmware changes complicate reproducibility. Reviews in sleep medicine emphasize careful validation and standardized performance assessment before using consumer sleep tracking in research or clinical workflows (de Zambotti et al., 2019).

### 3.3. HRV feature families and interpretive constraints
The app reports metrics across time-, frequency-, and nonlinear domains. This is not merely a software convenience; it mirrors the reality that different HRV features emphasize different physiological time scales and respond differently to confounds.

#### 3.3.1. Time-domain features: RMSSD, SDNN, and the logic of within-person baselines
Time-domain features are computed directly from NN intervals. Two measures dominate operational monitoring: SDNN and RMSSD.

- **SDNN** summarizes overall dispersion of NN intervals over the recording window. In short-term recordings, SDNN reflects a mixture of mechanisms; in 24-hour recordings, it integrates circadian and activity-driven variability and has strong prognostic associations in clinical cardiology. However, SDNN is not interchangeable across recording durations (Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology, 1996).

- **RMSSD** captures beat-to-beat variability and is mathematically linked to vagally mediated changes under resting conditions. For operational readiness, RMSSD is attractive because it is comparatively robust to slow nonstationarity and can be derived from short recordings. Nonetheless, RMSSD is still sensitive to posture, breathing pattern, and ectopy artefacts.

A recurring theme in the monitoring literature is that the most defensible use of short-term HRV in readiness is *within-person*, not cross-sectional. In large systematic reviews, even healthy adults show wide dispersion of “normal” values (Nunan et al., 2010). This implies that population norms are better treated as contextual priors than as deterministic thresholds.

Sports and occupational monitoring literature operationalizes this point via **log-transformed RMSSD (lnRMSSD)** and rolling baselines. Plews and colleagues argued that HRV is useful when interpreted as an adaptation signal within a periodized training context, and that averaging across multiple measurements improves stability and interpretability (Plews et al., 2014). The direct translation to aerospace contexts is conceptual rather than literal: the “training load” analogue may be cumulative operational stressors, sleep debt, circadian disruption, or illness. The key methodological move is the same—use repeated measurements, stabilize estimates via aggregation, and interpret deviations relative to a personalized baseline.

Operationally, this implies that readiness scoring should:

1. Prefer **deltas vs. baseline** and trend features over single absolute values.
2. Require explicit protocol metadata (time-of-day, posture, breathing instructions).
3. Preserve and surface **quality indicators** (artifact rate, amount of correction applied).

#### 3.3.2. Frequency-domain features: band power, record-length constraints, and the LF/HF problem
Spectral HRV features—HF, LF, VLF, total power—are often attractive to users because they appear mechanistically meaningful. However, their interpretability is bounded by basic signal-analysis constraints and physiological confounding.

**Record length requirements.** The Task Force statement emphasized that a frequency component can only be meaningfully estimated when the recording contains multiple cycles of that oscillation (Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology, 1996). In practice, HF power (0.15–0.40 Hz) can be estimated from shorter segments than LF power (0.04–0.15 Hz), while VLF estimation is particularly fragile in short-term recordings.

**Respiration as both signal and confound.** HF power is strongly linked to RSA and thus to respiratory rate and tidal volume. Changes in breathing pattern—spontaneous vs paced—can materially shift HF power and consequently any derived indices that normalize or ratio spectral components. Therefore, frequency-domain interpretation without respiration context risks attributing protocol variance to physiology.

**LF is not “sympathetic.”** The historical framing that LF reflects sympathetic tone and HF reflects parasympathetic tone was always oversimplified; LF includes significant parasympathetic contributions and is strongly shaped by baroreflex dynamics. Billman’s critique is operationally decisive: LF/HF does not accurately measure cardiac sympathovagal balance, especially when used as a standalone surrogate (Billman, 2013).

For an operational console, the design implication is not to remove LF/HF, but to reframe it:

- Treat LF, HF, and LF/HF primarily as *descriptive spectral features* whose meaning depends on context.
- Avoid presenting LF/HF as a direct measure of “sympathetic dominance.”
- When LF/HF is shown, pair it with explicit caveats and with additional markers (e.g., RMSSD/SD1) that are more interpretable as vagal proxies under resting conditions.

#### 3.3.3. Nonlinear and complexity metrics: what they add (and what they require)
Nonlinear features are often marketed as “advanced,” but their real value is that they capture properties not reducible to linear variance summaries. The app includes several prominent families.

**Entropy (ApEn, SampEn).** Approximate entropy (ApEn) was introduced as a statistic to quantify regularity/complexity in finite-length series (Pincus, 1991). Sample entropy (SampEn) was later proposed to reduce bias and improve consistency (Richman & Moorman, 2000). In HRV contexts, lower entropy is often interpreted as reduced adaptability or complexity-loss with aging and disease, but entropy estimates are sensitive to parameter choices (embedding dimension, tolerance) and to artefacts.

**Detrended fluctuation analysis (DFA).** DFA quantifies scaling properties and long-range correlations in nonstationary signals; Peng and colleagues demonstrated that healthy heartbeat dynamics exhibit fractal-like correlation structure and that pathological states may alter scaling exponents (Peng et al., 1995). In operational contexts, DFA-derived features can be informative but also fragile: they require sufficient data length and careful preprocessing, and their interpretation depends on whether the signal segment is stationary.

**Poincaré geometry (SD1, SD2) and their limitations.** Poincaré plots visualize NN(i) vs NN(i+1) structure. SD1 and SD2 quantify dispersion perpendicular and parallel to the identity line. However, the question “do these capture nonlinear features?” is not trivial. Brennan and colleagues examined whether existing Poincaré measures reflect nonlinear structure and highlighted limitations when such measures are treated as inherently nonlinear markers rather than geometric summaries (Brennan et al., 2001). Operationally, SD1 is often treated as a proxy for short-term variability (closely related to RMSSD), while SD2 relates to longer-term variability; but interpretive claims beyond this require caution.

**Heart rate fragmentation (HRF).** Fragmentation metrics aim to capture erratic switching in acceleration sign that is not well described by traditional HRV features. Costa and colleagues proposed HRF as a new approach to interbeat interval dynamics, suggesting it may represent altered pacemaker–autonomic interactions, particularly in aging and disease contexts (Costa et al., 2017). For an operational console, fragmentation indices are best treated as *adjuncts* for pattern recognition and risk stratification rather than as direct “stress scores,” because their clinical meaning depends on rhythm classification and the exclusion of arrhythmias.

A practical synthesis is that nonlinear metrics add value primarily when:

1. Signal quality is high (artefact-corrected without excessive interpolation).
2. Record lengths match the requirements of the metric (especially for scaling properties).
3. Outputs are triangulated with time/frequency features and with contextual covariates.

### 3.4. Autonomic function tests: controlled provocations vs passive monitoring
The app includes autonomic function tests (deep breathing, Valsalva, orthostatic responses). These tests differ from passive HRV monitoring because they intentionally provoke autonomic reflexes to probe specific pathways.

#### 3.4.1. Deep breathing tests (E:I responses)
Deep breathing protocols aim to amplify RSA and quantify cardiovagal responsiveness. Classic clinical approaches compute the expiration–inspiration (E:I) ratio or related heart rate response metrics. Studies in diabetics with and without symptoms of autonomic neuropathy show that deep breathing responses can be sensitive to autonomic dysfunction, though specificity varies with protocol and patient group (Sundkvist et al., 1982). Reviews of clinical autonomic testing emphasize that HRV with deep breathing is a sensitive cardiovagal measure and that standardized coaching (especially breathing rate, depth, and posture) is essential for interpretability (Shields, 2009).

Operationally, deep breathing tests offer two advantages:

- They provide a standardized *challenge* condition that can be more comparable across days than free-breathing rest.
- They can separate “low resting HRV due to transient factors” from “blunted vagal reactivity,” although this is not perfect.

However, deep breathing tests also introduce their own confounds: learning effects, poor compliance with breathing cadence, and anxiety-induced sympathetic activation.

#### 3.4.2. Valsalva manoeuvre and orthostatic ratios
The Valsalva manoeuvre probes baroreflex function across phases of pressure change, and the Valsalva ratio is a commonly reported summary. Orthostatic ratios (e.g., 30:15) reflect the immediate heart rate response to standing. In practice, these tests are used as part of batteries rather than interpreted in isolation. Selecting an appropriate test battery (or subset) is itself a methodological decision; data-driven work on test selection for cardiac autonomic neuropathy shows that not all components of the Ewing battery contribute equally to classification accuracy under practical constraints (Stranieri et al., 2013).

For a flight surgeon console, these tests can serve as periodic “calibration checks” of autonomic responsiveness, but they must be interpreted with operational constraints in mind (space suits, orthostatic intolerance risk, and mission safety constraints may limit provocative testing).

### 3.5. Population norms and personalized interpretation: what norms can and cannot do
Population norms are frequently requested by end-users because they enable immediate categorization (“low/normal/high”). Yet the HRV literature cautions that normative values are contingent on measurement protocol and sample characteristics.

Nunan and colleagues synthesized short-term HRV values across tens of thousands of healthy participants, finding substantial dispersion and systematic differences from earlier reference values, likely reflecting heterogeneity in measurement protocols and populations (Nunan et al., 2010). This has two operational implications:

1. **Norms are conditional.** A norm is valid only to the extent that the user’s measurement matches the protocol assumptions behind the norm.
2. **Decision utility favors baselines.** For readiness decisions, within-person deviations are often more informative than absolute comparisons, particularly when the decision horizon is short.

Shaffer and Ginsberg similarly emphasize that HRV interpretation requires attention to context and to the meaning of different metrics (Shaffer & Ginsberg, 2017). In practice, an operational tool should provide both: (i) normative context (as a prior), and (ii) individualized baselines (as the primary signal).

### 3.6. Blood pressure variability (BPV) and HRV–BPV coupling
BPV is conceptually adjacent to HRV because both reflect regulatory dynamics, but BPV includes additional vascular and measurement components. Parati and colleagues framed BPV as a phenomenon spanning seconds to years with complex physiological determinants, and argued that BPV has independent clinical relevance beyond mean blood pressure (Parati et al., 2018). Visit-to-visit BPV, in particular, has been associated with stroke and coronary outcomes, suggesting that variability metrics can carry prognostic information (Rothwell et al., 2010).

For an integrated console, BPV analytics are valuable for at least three reasons:

1. **Autonomic–vascular complementarity.** HRV reflects cardiac autonomic modulation; BPV reflects vascular tone regulation, baroreflex coupling, and arterial properties.
2. **Shared confounds but different sensitivity.** Stress, sleep loss, and circadian phase can influence both HRV and BPV, but through partly distinct pathways.
3. **Risk stratification.** In cardiovascular risk contexts, BPV may capture risk not fully represented by HRV.

Methodologically, BPV metrics are sensitive to sampling and measurement conditions (office vs ambulatory; device type; posture). Thus, as with HRV, BPV interpretation requires protocol metadata and conservative inference.

### 3.7. Circadian biology and modelling: phase, light response, and operational confounding
Circadian timing is not merely an explanatory backdrop; it is an active, measurable determinant of performance, sleep propensity, and many physiological endpoints that a flight-surgeon console monitors. When a system includes both HRV metrics and fatigue forecasts, circadian phase becomes a unifying latent variable: it modulates autonomic tone, alters sleep pressure dynamics, and changes the meaning of “normal” at a given clock time.

#### 3.7.1. What circadian models try to estimate: internal phase under imperfect observability
The operational quantity of interest is typically **internal circadian phase** (e.g., timing of melatonin onset, core body temperature minimum, or an equivalent model phase variable), not simply clock time. Yet in field settings, internal phase is rarely measured directly because gold-standard biomarkers require laboratory assays (e.g., dim light melatonin onset). Consequently, scheduling software often relies on *forward modelling* from observable inputs—light exposure, sleep timing, and sometimes activity—into predicted phase.

This introduces an inferential asymmetry: models are easy to run but hard to validate in situ. A defensible app therefore treats model phase as an *estimate with uncertainty* rather than a ground truth, and emphasizes that error grows when inputs are missing or unreliable (e.g., poor light measurement; inaccurate sleep timing).

#### 3.7.2. Light phase-response curves (PRCs): experimentally grounded but individual-specific
Human light PRCs quantify how timed light exposures advance or delay circadian phase. Controlled laboratory studies using melatonin-based phase markers show strong phase dependence: light presented in the biological evening tends to produce phase delays, whereas light in the late biological night/early morning produces phase advances (Khalsa et al., 2003). Subsequent work using shorter (1 h) light pulses similarly demonstrates structured PRCs and highlights that response magnitude depends on pulse timing and intensity (St Hilaire et al., 2012).

For operational tools, PRC evidence supports two pragmatic design choices:

1. **Schedule interventions should be phase-targeted.** The same light exposure can be beneficial or counterproductive depending on phase.
2. **Predictions must remain conservative.** Even in controlled studies, individuals vary in circadian period and response sensitivity, implying that model-based prescriptions should be presented as *risk-reducing guidance* rather than deterministic instructions.

#### 3.7.3. Oscillator-based circadian pacemaker models: mechanistic structure with operational utility
The app’s circadian module draws on a family of models that treat the circadian pacemaker as a limit-cycle oscillator coupled to light via photic preprocessing. Forger and colleagues presented a biologically grounded model capable of reproducing key human phase-resetting phenomena (Forger et al., 1999). Complementary work refined photic drive and oscillator structure to better match empirical PRCs and entrainment behavior (Jewett et al., 1998). More recent modelling work emphasizes “macroscopic” approaches and parameter identifiability—critical issues when applying models to individuals with limited calibration data (Hannay et al., 2019).

From an aerospace-human-factors perspective, the value of these models is not that they “prove” circadian mechanisms, but that they provide a **computable mapping** from schedules to predicted phase, enabling what-if analyses (e.g., projected phase at launch time given a light plan). The scientific defensibility of this mapping depends on transparent assumptions: light measurement, adherence to the schedule, baseline entrainment state, and whether the model is individualized.

#### 3.7.4. Circadian modulation of HRV and cardiovascular physiology: time-of-day as a confound
Even when a user’s behavior is stable, autonomic physiology exhibits circadian modulation. Early ambulatory work demonstrated a circadian pattern in HRV, with systematic variation across the 24-hour day (Mølgaard et al., 1991). This matters operationally because many HRV dashboards implicitly compare “today vs. yesterday” or “today vs. baseline,” yet a measurement taken at 0600 and one taken at 2200 are not comparable without time-of-day normalization and behavioral metadata.

Therefore, a conservative multimodal console should incorporate at least one of:

- **Protocol standardization:** measure at consistent times and conditions (e.g., post-waking, supine, fixed breathing instructions).
- **Circadian-aware baselines:** maintain baselines stratified by clock time or model phase.
- **Covariate adjustment:** include time-of-day (and ideally model phase) in statistical models to prevent spurious “fatigue” interpretations.

### 3.8. Fatigue science, vigilance measurement, and FRMS governance
Fatigue-related impairment is a central operational risk because it affects attention, reaction time, decision quality, and error monitoring. A flight surgeon console that includes fatigue forecasting must be grounded in three evidence layers: (i) dose-response relationships for sleep loss and time awake; (ii) objective measurement of the failure mode (vigilant attention lapses); and (iii) governance frameworks that prevent deterministic misuse.

#### 3.8.1. Dose-response impairment from sleep restriction and extended wakefulness
Controlled studies show that chronic partial sleep restriction produces cumulative neurobehavioral impairment that can be comparable to, or exceed, impairment from acute total sleep deprivation. Van Dongen and colleagues demonstrated dose-response impairment across multiple days of restricted sleep, with escalating performance lapses and subjective underestimation of impairment (Van Dongen et al., 2003). Belenky and colleagues similarly showed that reduced sleep opportunity (e.g., 3–7 h time in bed) yields systematic degradation in objective performance measures and that recovery requires more than a single night of unrestricted sleep (Belenky et al., 2003).

For operational translation, these findings imply that:

- Fatigue risk cannot be inferred solely from “last night’s sleep.” Multi-day sleep history matters.
- Users may not perceive the extent of impairment, motivating objective measures and conservative thresholds.

#### 3.8.2. Psychomotor vigilance testing (PVT): measuring the operational failure mode
The psychomotor vigilance test family is a cornerstone measure because it targets vigilant attention and provides a near-ceiling-free metric of lapses and reaction time slowing. Standardization work emphasizes that PVT variants differ in duration (e.g., 3-min vs 10-min), outcome definitions, and susceptibility to strategy, motivating careful protocol control and clear reporting of metrics (Basner et al., 2021).

A flight-surgeon console benefits from PVT-family integration for two reasons:

1. It anchors model outputs (fatigue forecasts) to an observable behavioral endpoint.
2. It provides a validity check when physiological proxies (HRV, sleep tracking) disagree.

#### 3.8.3. Biomathematical fatigue models (SAFTE/FAST): useful, but only under governance
Biomathematical models typically integrate at least three drivers: **homeostatic sleep pressure**, **circadian modulation**, and **sleep inertia**. Peer-reviewed syntheses describe fatigue models used in work settings, including their structure, assumptions, and operational application in safety contexts (Dawson et al., 2011).

In operational deployments, such models may be implemented within scheduling tools to forecast performance risk from sleep-wake schedules. However, model validity remains conditional: forecasts can be systematically wrong when inputs are inaccurate, when schedules are extreme, or when unmodelled stressors (illness, high workload) dominate.

However, model validity is conditional:

- Inputs (sleep timing/quality) must be reasonably accurate.
- Outputs are probabilistic and population-calibrated unless individualized.
- Model error can be operationally meaningful when schedules are extreme, when individuals differ strongly, or when additional stressors (illness, high workload) are present.

Thus, model outputs should be framed as *risk indicators* rather than “fitness certificates.”

#### 3.8.4. FRMS as a safety framework (US/EU governmental context)
Fatigue risk management systems (FRMS) treat fatigue as a hazard managed through layered controls: scheduling rules, education, monitoring, reporting, and continuous improvement. FAA guidance explicitly emphasizes FRMS as a structured approach to manage fatigue risk rather than a single numerical model output (Federal Aviation Administration [FAA], 2013). European regulation similarly embeds fatigue management into air-operations frameworks (European Union Aviation Safety Agency [EASA], 2023).

A console that integrates SAFTE-like forecasts should align with FRMS logic by:

- Capturing assumptions and uncertainty (e.g., missing sleep data; reliance on defaults).
- Supporting trend analysis and safety investigations rather than real-time punitive decisions.
- Enabling audit trails (who viewed what, what inputs were used) and encouraging reporting.

Critically, FRMS is not “a model in a dashboard.” It is a structured safety process that treats fatigue as a hazard managed through multiple barriers. In prescriptive regimes, duty limits and rest requirements serve as coarse risk controls. In performance-based regimes, FRMS supplements prescriptive rules with monitoring, reporting culture, and continuous improvement. A console can support this only if it is designed as part of that system: it should help document fatigue hazards (e.g., repeated schedule compression), track leading indicators (sleep opportunity, time awake, circadian phase estimates, vigilance performance), and support after-action review when outcomes are adverse.

This perspective also changes how a biomathematical fatigue forecast should be communicated. The forecast should be treated as one layer in a barrier model, not as the barrier itself. For example, when a forecast indicates elevated fatigue risk, FRMS-consistent actions include operational mitigations (schedule adjustment, strategic napping when feasible, task reallocation, increased supervision, or additional objective testing), as well as documentation for later safety assurance. Conversely, when a forecast indicates low risk, it should not be interpreted as a waiver of other concerns (illness, acute stress, degraded sleep quality). In other words, the console should be designed to prevent “single-number clearance,” aligning the user’s mental model with the FRMS principle that fatigue risk is managed, not eliminated.

### 3.9. Wearable and field acquisition: what can be trusted, when, and why
Because the platform ingests wearable data, the validity of the upstream measurement chain is a first-order determinant of downstream analytic quality.

#### 3.9.1. ECG-derived RR intervals vs PPG-derived pulse intervals
Chest-strap ECG sensors estimate RR intervals from electrical depolarization and can be highly accurate at rest. Validation studies show that Polar H10 RR intervals exhibit high agreement with ECG across common resting protocols, supporting many HRV analyses (Schaffarczyk et al., 2022). Polar S810-family validation work similarly supports feasibility for short-term HRV monitoring under controlled conditions (Nunan et al., 2009).

Wrist-worn PPG estimates inter-beat intervals indirectly via peripheral pulse arrival timing and waveform detection. A key conceptual distinction is that **pulse rate variability (PRV)** is not identical to HRV: PRV is influenced by vascular tone and pulse transit dynamics, and it is more susceptible to motion and vasoconstriction. A major review concluded that PRV can approximate HRV under resting, stable conditions, but agreement degrades with stressors, posture changes, and motion—conditions common in operations (Schäfer & Vagedes, 2013).

Operational implications include:

- Prefer chest-strap ECG for HRV metrics intended to support decisions.
- If PPG is used, restrict interpretation to conditions where PRV≈HRV is plausible (resting, minimal motion), and surface uncertainty flags.

#### 3.9.2. Actigraphy and consumer sleep technologies: validated constructs and known failure modes
Sleep timing and sleep opportunity are critical inputs for both circadian and fatigue modules. Actigraphy has long been used to estimate rest–activity cycles and sleep timing in field studies; guidance reviews emphasize that actigraphy is best for sleep–wake *timing* and less reliable for sleep staging without polysomnography (Ancoli-Israel et al., 2003).

Modern consumer wearables combine accelerometry with PPG and sometimes skin temperature. Reviews in sports medicine and sleep research emphasize that proprietary algorithms can change without notice and that validation should be device- and firmware-specific (de Zambotti et al., 2019). For an operational console, the appropriate posture is therefore to treat wearable sleep outputs as *estimates* that are most useful for:

- Sleep timing (bed/wake time, sleep opportunity),
- Night-to-night trends,
- Identifying gross disturbances,

rather than as definitive sleep stage or clinical diagnosis.

### 3.10. Space-weather integration: indices, data products, and the evidentiary bar for physiology links
The app integrates NOAA/NASA space-weather context with time-aligned physiological analytics. From a scientific perspective, this is best framed as a hypothesis-generating module: it merges a well-characterized geophysical measurement domain with a physiologic domain where effect sizes are likely small and confounding is substantial.

#### 3.10.1. Data products: what Kp and event catalogs actually represent
NOAA’s Space Weather Prediction Center (SWPC) provides standard indices and explanatory documentation. The planetary K index (Kp) reflects global geomagnetic activity derived from multiple magnetometer stations and is commonly used to characterize geomagnetic disturbances (NOAA Space Weather Prediction Center [SWPC], n.d.-a). NOAA also publishes standardized space weather scales (G for geomagnetic storms, S for solar radiation storms, R for radio blackouts), which support categorical operational communication (NOAA Space Weather Prediction Center [SWPC], n.d.-b).

NASA’s Community Coordinated Modeling Center (CCMC) maintains the DONKI system to catalogue space-weather events (e.g., solar flares, CMEs, geomagnetic storms) and provides an API-oriented interface for retrieving event timing and metadata (NASA/CCMC, n.d.). These resources enable reproducible alignment between geophysical events and physiological time series if timestamps, time zones, and sampling windows are handled correctly.

#### 3.10.2. Evidence on geomagnetic activity and autonomic/cardiovascular outcomes: plausible pathways, mixed findings
Mechanistic hypotheses linking geomagnetic activity to autonomic function include melatonin modulation, magnetoreception-related pathways, and indirect behavioral mediators. Empirically, studies report associations between geomagnetic indices and HRV in specific cohorts. For example, an experimental and observational analysis reported changes in HRV with geomagnetic activity in a cohort study context (Alabdulgader et al., 2018). Large longitudinal cohort work has also examined associations between solar and geomagnetic indices and HRV (Vieira et al., 2022).

However, multiple threats to validity are salient:

- **Autocorrelation and seasonality:** both geomagnetic indices and human physiology exhibit temporal structure.
- **Multiple comparisons and researcher degrees of freedom:** time-window selection, lag choice, and subgrouping can inflate false positives.
- **Confounding:** temperature, air pollution, behavior, and seasonal illness can covary with both outcomes and exposures.

In practice, these threats imply that any geophysical–physiological association workflow should incorporate safeguards that are rarely used in informal dashboard exploration. Examples include:

- **Pre-specifying windows and lags** before viewing outcomes (e.g., “0–24 h after Kp≥5”) rather than choosing windows that visually “look best.”
- **Negative controls** (e.g., shuffled exposure series; pseudo-events) to estimate the false positive rate of the analytic pipeline.
- **Adjustment for time structure** by explicitly modelling seasonality and autocorrelation or by using appropriately blocked comparisons.
- **Multiple-testing control** when scanning many HRV/BPV features and many candidate lags.
- **Replication across cohorts or time periods** to distinguish fragile correlations from robust signals.

A key design implication is that the console should separate *visual overlay* from *statistical inference*: overlays support hypothesis generation, whereas inference requires prespecified modelling choices and explicit error control.

Therefore, a defensible operational app should present space-weather–physiology overlays as exploratory visual analytics, paired with conservative statistical controls (e.g., multiple-testing correction) and explicit warnings against causal inference.

### 3.11. Statistics, machine learning, and governance for physiological decision support
A multimodal console combines multiple signals and can easily drift into “dashboard overconfidence.” The scientific literature on modelling and inference offers concrete governance tools to reduce error.

#### 3.11.1. Multiple testing control and exploratory analytics
When dozens of features are monitored (HRV time/frequency/nonlinear, BPV metrics, sleep metrics, fatigue model outputs), repeated hypothesis tests will generate false positives even if no true effect exists. The Benjamini–Hochberg procedure provides a practical false discovery rate (FDR) control method that is widely used in high-dimensional settings (Benjamini & Hochberg, 1995). For operational analytics, FDR control is particularly appropriate when the aim is *screening and prioritization* rather than confirmatory clinical diagnosis.

#### 3.11.2. Mixed-effects models: separating within-person change from between-person differences
Because physiological baselines vary widely, analyses that pool individuals without accounting for random effects risk misleading inference. Linear mixed-effects models provide a principled framework for longitudinal, repeated-measures data by separating within-subject and between-subject variance components (Laird & Ware, 1982). In a flight surgeon context, this supports: (i) estimating an individual’s deviation from baseline while borrowing strength across individuals; and (ii) adjusting for covariates such as time-of-day, posture, and recent sleep.

#### 3.11.3. Change-point detection as an operationally meaningful analytic primitive
Operationally, the question “did something change?” is often more actionable than “what is the absolute value?” Change-point detection methods formalize this. The PELT algorithm provides an efficient approach for detecting multiple change points in time series under penalized likelihood, enabling detection of regime shifts such as sudden HRV suppression or step changes in sleep timing (Killick et al., 2012).

#### 3.11.4. Validation, leakage, and time-series cross-validation
Naïve validation approaches can dramatically overestimate performance when temporal dependence exists. Work on cross-validation for time series emphasizes that standard random-fold CV can be invalid under autocorrelation; blocked or forward-chaining CV approaches are needed to avoid leakage (Bergmeir et al., 2018). In addition, model selection and hyperparameter tuning performed on the same data used for evaluation can yield optimistic bias; formal analyses in bioinformatics show substantial bias in gene selection pipelines when evaluation is not nested correctly (Varma & Simon, 2006). These issues generalize to multimodal physiology: if feature engineering and threshold selection are tuned on past missions and then evaluated on the same data, the dashboard will appear more accurate than it is.

#### 3.11.5. Interpretability: useful explanations without reification
Operational adoption often requires explanations. Feature attribution methods such as SHAP (Shapley additive explanations) provide a mathematically grounded way to attribute model predictions to input features. Lundberg and colleagues introduced efficient algorithms for consistent feature attribution in tree ensembles and demonstrated how local explanations can aggregate to global understanding (Lundberg et al., 2020). In a flight-surgeon console, interpretability should be treated as a *communication layer* that aids oversight, not as a proof of causality.

### 3.12. HRV biofeedback and controlled breathing: intervention science vs measurement confounding
Because the app includes biofeedback capabilities, it is important to distinguish two roles for controlled breathing.

First, **paced breathing is a measurement confound** in HRV assessment. It can increase HF power when breathing is in the HF band, or shift respiratory-driven variability into the LF band when breathing is slowed toward ~0.1 Hz, materially altering LF, HF, and LF/HF without any necessary change in sympathetic tone. Thus, when paced breathing is used for standardization, the breathing rate must be documented and the interpretation of spectral features must be adjusted accordingly.

Second, **paced breathing can be an intervention**. HRV biofeedback and resonance-frequency breathing aim to enhance baroreflex-mediated oscillations and autonomic regulation, and they have been studied across clinical and performance contexts. Reviews of HRV biofeedback describe plausible mechanistic pathways (baroreflex engagement, respiratory–cardiovascular coupling) and emphasize protocol specificity, particularly the need to individualize resonance frequency and to distinguish training effects from acute breathing-induced shifts (Lehrer & Gevirtz, 2014).

For an operational console, the safe synthesis is that biofeedback modules should be framed as training/skill-building tools, while analysis modules should clearly label when measurements were taken under paced-breathing conditions.

### 3.13. Brief environmental context (spaceflight): standards, human-system integration, and radiation as metadata
The app’s “mission control” framing is consistent with aerospace medicine contexts where environment and operational constraints shape physiological baselines. NASA human-system integration standards (NASA-STD-3001 Volume 2) provide a comprehensive framework for designing and evaluating human health and performance requirements across spaceflight conditions (National Aeronautics and Space Administration [NASA], 2022).

Within this review’s scope, radiation is treated only as contextual environmental metadata rather than as a radiobiological topic. The operationally relevant implication is that environmental factors (including radiation environment, cabin pressure/oxygenation, thermal load) can shift baselines and recovery trajectories; therefore, multimodal consoles should (i) capture environment metadata when available, and (ii) avoid attributing unexplained physiological deviations to a single environmental cause without stronger evidence.

### 3.14. Windowed and longitudinal analytics: why trend features are not optional
The app includes windowed HRV and time-series analyses because operational physiology is rarely stationary. Even under stable conditions, HRV varies across the day due to circadian timing and behavior. Across days, additional nonstationarities arise from sleep debt accumulation, illness, training/workload cycles, and changes in measurement protocol adherence. Consequently, “single-session” HRV snapshots are insufficient for high-stakes interpretation unless they are embedded in a longitudinal framework.

A windowed approach provides three forms of operational value.

First, it **stabilizes estimates** by aggregating repeated short measurements. Short-term HRV features can be noisy, especially when acquisition conditions drift. Aggregation (e.g., rolling medians) reduces the influence of outliers and supports the within-person baseline logic emphasized throughout this review.

Second, windowed analysis makes **time alignment** explicit. When the console combines HRV, sleep, fatigue forecasts, and space-weather indices, each signal has its own sampling cadence and latency. A well-designed time-series layer forces consistent treatment of time zones, missingness, and the definitions of “day,” “mission day,” or “sleep episode.” In practice, the most common operational error mode is not statistical sophistication but misalignment: comparing metrics computed over different windows and then attributing differences to physiology.

Third, windowed analyses enable **change-focused questions**. Operators often need to know whether physiology is drifting, whether a perturbation occurred after a schedule change, or whether an intervention (sleep extension, workload reduction, biofeedback) is associated with recovery. Methods such as change-point detection (Killick et al., 2012) can formalize “something changed” as a testable statement rather than a subjective impression from a dashboard. Importantly, these methods should not be treated as automated diagnoses; they are flags that a regime shift may have occurred and therefore that context review is warranted.

An additional methodological consideration is that physiological feature distributions are often skewed and heteroskedastic. Even when daily measurements are protocol-controlled, variance can change with stress exposure, illness, or sleep loss. Windowed analytics should therefore emphasize robust summaries (median, trimmed means) and variance-aware representations (e.g., baseline mean with control limits) rather than relying solely on raw day-to-day fluctuations. Transformations can improve interpretability—for example, lnRMSSD is commonly used to stabilize variance in longitudinal monitoring—and standardized effect sizes (within-person z-scores relative to an appropriate baseline window) can support communication without implying that the underlying physiology is Gaussian.

Finally, the choice of window length is itself a modelling decision with trade-offs. Short windows react quickly but can be noisy and sensitive to missingness; long windows are stable but can dilute acute changes and conceal recovery trajectories. A defensible console makes these trade-offs explicit and avoids silently changing windows in ways that alter user interpretation.

Operationally, this argues for three implementation constraints:

- Keep window definitions explicit and user-visible (e.g., “rolling 7-day baseline from morning supine recordings”).
- Preserve raw-session values alongside smoothed values to avoid hiding acute events.
- Surface uncertainty driven by missing data, artefact correction, and protocol deviations.

---

## 4. Discussion
### 4.1. Why multimodal fusion is both necessary and dangerous
The scientific case for multimodal fusion is straightforward: no single signal captures readiness. HRV reflects autonomic modulation but is confounded by posture, respiration, circadian phase, and signal quality. Fatigue models capture known determinants of impairment (sleep history, time awake, circadian phase) but depend on the accuracy of sleep inputs and population-level parameterization. PVT-family measures directly assess vigilant attention but are sensitive to motivation and require user compliance. Space-weather indices are precise geophysical measurements, but any physiological impacts are small and context dependent.

The danger is equally straightforward: combining multiple imperfect signals can create an illusion of precision. A system that reports “readiness 73/100” without surfacing uncertainty and protocol dependencies invites misuse. Therefore, the defensible position is not to avoid fusion, but to design fusion under governance: conservative thresholds, audit trails, uncertainty visualization, and a clear separation between exploratory analytics and decision-critical indicators.

### 4.2. A defensible hierarchy of evidence for operational decision support
For high-consequence contexts, a conservative hierarchy is appropriate:

1. **Behavioral performance measures** (e.g., PVT) are closest to the operational failure mode.
2. **Schedule- and history-based fatigue forecasts** provide forward-looking risk indicators when inputs are reliable.
3. **Physiological markers** (HRV/BPV) provide additional context and may detect illness/stress, but require strict quality gating.
4. **Environmental overlays** (space weather) are best treated as exploratory context unless validated for the specific population and use case.

In this hierarchy, HRV is most defensible when it is:

- acquired with a high-fidelity modality (ECG chest strap),
- measured under standardized conditions,
- interpreted as within-person deviations,
- and triangulated with sleep and performance indicators.

### 4.3. Governance, auditability, and “fail-closed” design
A flight surgeon console is ultimately a decision-support instrument. It should be designed to fail closed: when inputs are missing, low quality, or inconsistent, the system should *reduce* confidence rather than extrapolate. Practical mechanisms include:

- Mandatory quality gates (artifact percentage, ectopy flags, missingness thresholds).
- Transparent provenance for each metric (device, firmware, preprocessing settings).
- Explicit uncertainty messaging (e.g., “phase estimate low confidence due to missing light data”).
- Multiple testing controls and pre-specified analytics for exploratory correlations.

### 4.4. Limitations and research directions
Several limitations constrain current best practice.

First, physiological features are high-dimensional and context sensitive; without careful protocol standardization, dashboards risk becoming collections of noisy indicators. Second, circadian phase prediction remains imperfect without biomarker calibration, particularly when light inputs are not measured. Third, fatigue models capture major determinants but cannot fully incorporate stress, illness, and workload without additional sensing and validated coupling.

A research-aligned roadmap for such platforms therefore includes: (i) calibration studies that directly compare wearable-derived inputs to gold standards (ECG, polysomnography, melatonin assays) in relevant operational populations; (ii) prospective evaluation of decision-support outputs against objective performance endpoints; and (iii) robust statistical governance that treats exploratory findings as hypotheses to be tested rather than as immediate operational rules.

### 4.5. Validation and calibration: linking dashboard outputs to operational outcomes
A multimodal console is only as defensible as its validation. “Looks plausible” is not a sufficient criterion when outputs may influence mission-critical decisions. Validation should therefore be framed as an **evidence chain** that connects upstream measurements to downstream decision utility.

**Define the endpoint first.** In high-consequence monitoring, the most meaningful endpoints are often operational: vigilance lapses, errors, near-misses, or task-performance degradation. Physiological proxies (HRV, BPV) are not direct measures of these endpoints. In contrast, PVT-family measures directly probe vigilant attention and have well-characterized dose-response sensitivity to sleep loss and circadian misalignment (Basner et al., 2021; Van Dongen et al., 2003). A practical validation strategy therefore uses PVT (or other performance tasks) as a reference outcome and evaluates whether the console improves the detection of performance-risk states beyond what could be achieved from sleep history alone.

**Separate calibration from evaluation.** Physiological monitoring systems routinely embed choices: which HRV metric to emphasize, which artefact threshold to use, how to define a baseline window, which covariates to adjust for, and which thresholds trigger alerts. If these choices are tuned on the same data that later evaluate “accuracy,” the system will appear better than it is. Time-series dependence exacerbates this risk because adjacent days are correlated. The solution is methodological discipline: use temporally appropriate validation (blocked or forward-chaining approaches) and separate the tuning window from the evaluation window (Bergmeir et al., 2018; Varma & Simon, 2006).

**Treat inference as conditional on protocol and metadata.** Many apparent failures of HRV monitoring are failures of protocol consistency (time-of-day, posture, breathing) rather than failures of physiology. A console that logs and enforces protocol metadata can prevent this category of error. In practice, validation should stratify by protocol adherence and quantify how much predictive value collapses when metadata is missing.

**Quantify uncertainty and error budgets.** Operational systems should not present point estimates without uncertainty qualifiers. In a console context, uncertainty is not only statistical; it is also *data-quality uncertainty* (artefact correction fraction, missingness) and *model-input uncertainty* (sleep/wake estimates from wearables). A defensible approach treats the dashboard as a system that reports (i) an estimate, (ii) a confidence score driven by data quality, and (iii) the reasons confidence is reduced.

### 4.6. Reproducibility in mixed-device ecosystems: provenance, versioning, and audit trails
A core barrier to reproducible physiological analytics is that much of the pipeline is embedded in devices and proprietary firmware. Even when downstream analytics are open and well-defined, upstream data generation can change.

**Provenance is part of the measurement.** For HRV, the effective “instrument” is not just the chest strap, but also the vendor’s peak-detection algorithm, filtering choices, and update cadence. For sleep estimation, the instrument is the wearable plus its classification model. Therefore, a console should log device type, sampling characteristics (when known), firmware/app versions, and acquisition conditions. Without this metadata, longitudinal comparisons can be contaminated by silent instrument drift.

**Anchor analytics to stable feature definitions.** HRV analysis packages such as Kubios are widely used in research partly because they provide transparent definitions and documented preprocessing choices (Tarvainen et al., 2014). While an operational console need not replicate Kubios, it should similarly:

- define each metric precisely,
- document preprocessing defaults,
- record any deviations from defaults at run time,
- and provide the ability to re-run analyses under different correction settings.

**Make correction visible.** Artefact correction is sometimes treated as an implementation detail, but it can drive results, particularly for nonlinear metrics. Algorithms for artefact correction provide a rationale for defensible correction, yet they also highlight that correction is not neutral (Lipponen & Tarvainen, 2019). Operationally, this implies that the console should surface the proportion of corrected beats and warn when correction intensity makes downstream interpretation fragile.

**Design for auditability.** FRMS logic emphasizes learning systems and continuous improvement rather than punitive “gotcha” decisions (Federal Aviation Administration, 2013). In software terms, this maps to audit trails: what data were ingested, what processing settings were used, what outputs were displayed, and when. This is critical not only for scientific defensibility but also for operational investigations when outcomes are adverse.

### 4.7. Communicating uncertainty and preventing automation bias
Human factors determine whether analytic quality translates into safety. When a dashboard is used under time pressure, users tend to overweight salient summary numbers. If the console presents a single readiness score without qualifiers, it risks inducing **automation bias**: unwarranted trust in the system’s output.

A conservative design approach therefore emphasizes:

- **Layered outputs:** show a top-level state (e.g., “green/yellow/red”) only when confidence is high, and provide drill-down to show why.
- **Reason codes:** accompany alerts with structured explanations (e.g., “low RMSSD with high artefact correction fraction,” “fatigue forecast elevated due to 3-day sleep debt,” “phase estimate low confidence due to missing light data”).
- **Consistency checks:** when signals disagree (e.g., HRV suggests stress but PVT is normal), present this explicitly rather than forcing a single fused number.
- **Fail-closed behavior:** when data quality is poor, suppress interpretive outputs and encourage re-measurement under standardized conditions.

### 4.8. Synthesis: operational principles for a scientifically defensible console
Across modules, several principles recur.

1. **Prefer within-person baselines over population thresholds** for short-term decision support.
2. **Treat models as conditional estimates**, not as truth: circadian phase and fatigue forecasts depend on inputs and assumptions.
3. **Prioritize measurement validity**, especially RR quality, protocol metadata, and device provenance.
4. **Control false positives** with explicit statistical governance in high-dimensional monitoring.
5. **Communicate uncertainty** as a first-class output to reduce automation bias.

These principles do not eliminate uncertainty, but they constrain how uncertainty can mislead, which is the core goal in operational medicine.

## 5. Conclusions
This review synthesized peer-reviewed evidence and US/EU governmental technical documents that underpin a multimodal “flight surgeon console” approach. The scientific foundation for such systems is strong *if* the console is treated as a governed decision-support stack rather than as an automated diagnostic engine.

At the measurement layer, HRV and BPV analytics are defensible only when the upstream signal chain is credible. HRV standards emphasize that recording duration, stationarity, and preprocessing choices constrain interpretation (Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology, 1996). In operational settings, this translates into a simple rule: a console should privilege high-quality RR series acquired under standardized conditions over “always-on” but low-fidelity signals. Artefact correction can improve utility, yet it also introduces sensitivity to method; therefore, correction intensity and quality flags should be surfaced as part of the output rather than treated as hidden implementation details (Lipponen & Tarvainen, 2019).

At the physiology and modelling layer, the key conclusion is that readiness is multi-determined. HRV features provide information about autonomic modulation, but they are strongly confounded by time-of-day, posture, and breathing. Circadian timing alters baselines and performance risk, and mechanistic oscillator models supported by human PRC experiments can provide schedule guidance when their assumptions are explicit (Forger et al., 1999; Khalsa et al., 2003; St Hilaire et al., 2012). Fatigue risk is dominated by sleep history, time awake, and circadian phase; objective vigilance tasks provide a direct measurement of the failure mode and can anchor interpretation when physiological proxies disagree (Basner et al., 2021; Van Dongen et al., 2003). Biomathematical fatigue models add operational value when embedded within FRMS governance—i.e., as risk indicators integrated with education, reporting, and continuous improvement rather than as deterministic truth (Federal Aviation Administration, 2013).

At the integration layer, a console’s value is determined by whether it reduces error. Wearables can provide high-resolution longitudinal data, but they also introduce reproducibility risks due to proprietary algorithms and silent firmware changes; this makes provenance logging and stable feature definitions a safety requirement, not a luxury (de Zambotti et al., 2019; Tarvainen et al., 2014). Space-weather indices are precise and well-defined geophysical products, but evidence of physiological impacts is heterogeneous and likely small; thus, space-weather overlays are most defensible as hypothesis-generating context paired with conservative time-series governance (Alabdulgader et al., 2018; Vieira et al., 2022).

### 5.1. Minimum defensible operating assumptions
To avoid “dashboard overconfidence,” a flight-surgeon console should adopt minimum assumptions that constrain misuse:

- **Decision support, not diagnosis.** The system reports risk indicators and confidence, not clinical determinations.
- **Protocol metadata is mandatory.** Time-of-day, posture, and breathing protocol are logged for HRV comparisons.
- **Quality gating is enforced.** If artefact correction or missingness exceeds a threshold, interpretive outputs are suppressed.
- **Baselines are individualized.** Population norms are optional context; within-person baselines are primary.
- **Uncertainty is explicit.** Every headline metric has a confidence indicator driven by data quality and model-input completeness.

### 5.2. Practical implications for the Mission Control – Flight Surgeon platform
Within the scope reviewed here, several practical implications follow for the app’s module architecture.

1. **HRV modules should remain modular and metadata-aware.** Time-, frequency-, and nonlinear features should be presented with protocol constraints and record-length requirements. Frequency-domain metrics should not be framed as direct sympathetic surrogates, and LF/HF should be treated as descriptive rather than mechanistic.
2. **Circadian and fatigue modules should be cross-linked.** Phase estimates and fatigue forecasts share causal drivers; integrating them reduces contradictory interpretations (e.g., low HRV at an adverse circadian phase should not be misread as illness without corroboration).
3. **Windowed analytics should be a first-class layer.** Trend features and change-focused questions are often more actionable than single-session values; however, the console should preserve raw values alongside smoothed summaries and keep window definitions explicit.
4. **Governance controls should be part of the product.** Multiple testing control, time-series-aware validation, and audit trails are not “research add-ons”; they are safety features when outputs may influence operational decisions.

### 5.3. Closing statement
A multimodal physiological console can be scientifically credible and operationally useful when it respects the conditional nature of its metrics and models. The core design goal is not to eliminate uncertainty, but to prevent uncertainty from masquerading as certainty. Achieving this requires disciplined measurement, transparent assumptions, conservative inference, and FRMS-style governance that keeps the system oriented toward safety and learning.

Finally, the most constructive way to deploy such a system is iteratively: start with a narrow set of high-confidence measurements (standardized morning HRV, sleep opportunity, vigilance testing), establish within-person baselines, and only then layer more complex models (circadian phase estimation, biomathematical fatigue forecasts, exploratory environmental overlays). Each added module should be justified by incremental decision value and paired with an explicit failure analysis: how could this output be wrong, and what would the consequence be if it were trusted? In that framing, the console becomes a platform for disciplined operational physiology rather than a collection of attractive plots.

---

## References
Alabdulgader, A., McCraty, R., Atkinson, M., Dobyns, Y., Vainoras, A., Ragulskis, M., & Stolc, V. (2018). Long-term study of heart rate variability responses to changes in the solar and geomagnetic environment. Scientific Reports, 8(1). https://doi.org/10.1038/s41598-018-20932-x

Ancoli-Israel, S., Cole, R., Alessi, C., Chambers, M., Moorcroft, W., & Pollak, C. P. (2003). The role of actigraphy in the study of sleep and circadian rhythms. Sleep, 26(3), 342–392. https://doi.org/10.1093/sleep/26.3.342

Basner, M., Moore, T. M., Nasrini, J., Gur, R. C., & Dinges, D. F. (2021). Standardization of psychomotor vigilance testing methods and reporting. Sleep, 44(7). https://doi.org/10.1093/sleep/zsab114

Belenky, G., Wesensten, N. J., Thorne, D. R., Thomas, M. L., Sing, H. C., Redmond, D. P., Russo, M. B., & Balkin, T. J. (2003). Patterns of performance degradation and restoration during sleep restriction and subsequent recovery: a sleep dose-response study. Journal of Sleep Research, 12(1), 1–12. https://doi.org/10.1046/j.1365-2869.2003.00337.x

Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate: A practical and powerful approach to multiple testing. Journal of the Royal Statistical Society Series B: Statistical Methodology, 57(1), 289–300. https://doi.org/10.1111/j.2517-6161.1995.tb02031.x

Bergmeir, C., Hyndman, R. J., & Koo, B. (2018). A note on the validity of cross-validation for evaluating autoregressive time series prediction. Computational Statistics & Data Analysis, 120, 70–83. https://doi.org/10.1016/j.csda.2017.11.003

Billman, G. E. (2013). The LF/HF ratio does not accurately measure cardiac sympatho-vagal balance. Frontiers in Physiology, 4. https://doi.org/10.3389/fphys.2013.00026

Brennan, M., Palaniswami, M., & Kamen, P. (2001). Do existing measures of Poincaré plot geometry reflect nonlinear features of heart rate variability? IEEE Transactions on Biomedical Engineering, 48(11), 1342–1347. https://doi.org/10.1109/10.959330

Costa, M. D., Davis, R. B., & Goldberger, A. L. (2017). Heart rate fragmentation: A new approach to the analysis of cardiac interbeat interval dynamics. Frontiers in Physiology, 8. https://doi.org/10.3389/fphys.2017.00255

Dawson, D., Ian Noy, Y., Härmä, M., Åkerstedt, T., & Belenky, G. (2011). Modelling fatigue and the use of fatigue models in work settings. Accident Analysis & Prevention, 43(2), 549–564. https://doi.org/10.1016/j.aap.2009.12.030

de Zambotti, M., Cellini, N., Goldstone, A., Colrain, I. M., & Baker, F. C. (2019). Wearable sleep technology in clinical and research settings. Medicine & Science in Sports & Exercise, 51(7), 1538–1557. https://doi.org/10.1249/MSS.0000000000001947

European Union Aviation Safety Agency. (2023). Easy Access Rules for Air Operations (online publication). Retrieved December 21, 2025, from https://www.easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-air-operations

Federal Aviation Administration. (2013). Fatigue Risk Management Systems for Aviation Safety (Advisory Circular No. 120-103A). U.S. Department of Transportation. https://www.faa.gov/documentlibrary/media/advisory_circular/ac_120-103a.pdf

Forger, D. B., Jewett, M. E., & Kronauer, R. E. (1999). A simpler model of the human circadian pacemaker. Journal of Biological Rhythms, 14(6), 533–538. https://doi.org/10.1177/074873099129000867

Hannay, K. M., Booth, V., & Forger, D. B. (2019). Macroscopic models for human circadian rhythms. Journal of Biological Rhythms, 34(6), 658–671. https://doi.org/10.1177/0748730419878298

Jewett, M. E., & Kronauer, R. E. (1998). Refinement of limit cycle oscillator model of the effects of light on the human circadian pacemaker. Journal of Theoretical Biology, 192(4), 455–465. https://doi.org/10.1006/jtbi.1998.0667

Khalsa, S. B. S., Jewett, M. E., Cajochen, C., & Czeisler, C. A. (2003). A phase response curve to single bright light pulses in human subjects. The Journal of Physiology, 549(3), 945–952. https://doi.org/10.1113/jphysiol.2003.040477

Killick, R., Fearnhead, P., & Eckley, I. A. (2012). Optimal detection of changepoints with a linear computational cost. Journal of the American Statistical Association, 107(500), 1590–1598. https://doi.org/10.1080/01621459.2012.737745

Laborde, S., Mosley, E., & Thayer, J. F. (2017). Heart rate variability and cardiac vagal tone in psychophysiological research: Recommendations for experiment planning, data analysis, and data reporting. Frontiers in Psychology, 8, 213. https://doi.org/10.3389/fpsyg.2017.00213

Laird, N. M., & Ware, J. H. (1982). Random-effects models for longitudinal data. Biometrics, 38(4), 963–974. https://doi.org/10.2307/2529876

Lehrer, P. M., & Gevirtz, R. (2014). Heart rate variability biofeedback: How and why does it work? Frontiers in Psychology, 5, 756. https://doi.org/10.3389/fpsyg.2014.00756

Lipponen, J. A., & Tarvainen, M. P. (2019). A robust algorithm for heart rate variability time series artefact correction using novel beat classification. Journal of Medical Engineering & Technology, 43(3), 173–181. https://doi.org/10.1080/03091902.2019.1640306

Lundberg, S. M., Erion, G., Chen, H., DeGrave, A., Prutkin, J. M., Nair, B., Katz, R., Himmelfarb, J., Bansal, N., & Lee, S.-I. (2020). From local explanations to global understanding with explainable AI for trees. Nature Machine Intelligence, 2(1), 56–67. https://doi.org/10.1038/s42256-019-0138-9

Mølgaard, H., Sørensen, K. E., & Bjerregaard, P. (1991). Circadian variation and influence of risk factors on heart rate variability in healthy subjects. The American Journal of Cardiology, 68(8), 777–784. https://doi.org/10.1016/0002-9149(91)90653-3

NASA/CCMC. (n.d.). DONKI: Space Weather Database of Notifications, Knowledge, Information. Retrieved December 21, 2025, from https://ccmc.gsfc.nasa.gov/tools/DONKI/

National Aeronautics and Space Administration. (2022). NASA-STD-3001, Volume 2, Revision B: Human factors, habitability, and environmental health. NASA Technical Reports Server. https://ntrs.nasa.gov/citations/20220001995

NOAA Space Weather Prediction Center. (n.d.-a). The K-index (PDF). Retrieved December 21, 2025, from https://www.swpc.noaa.gov/sites/default/files/images/u2/TheK-index.pdf

NOAA Space Weather Prediction Center. (n.d.-b). NOAA scales explanation. Retrieved December 21, 2025, from https://www.swpc.noaa.gov/noaa-scales-explanation

Nunan, D., Donovan, G., Jakovljevic, D. G., Hodges, L. D., Sandercock, G. R. H., & Brodie, D. A. (2009). Validity and reliability of short-term heart-rate variability from the Polar S810. Medicine & Science in Sports & Exercise, 41(1), 243–250. https://doi.org/10.1249/MSS.0b013e318184a4b1

Nunan, D., Sandercock, G. R. H., & Brodie, D. A. (2010). A quantitative systematic review of normal values for short-term heart rate variability in healthy adults. Pacing and Clinical Electrophysiology, 33(11), 1407–1417. https://doi.org/10.1111/j.1540-8159.2010.02841.x

Pan, J., & Tompkins, W. J. (1985). A real-time QRS detection algorithm. IEEE Transactions on Biomedical Engineering, BME-32(3), 230–236. https://doi.org/10.1109/TBME.1985.325532

Parati, G., Stergiou, G. S., Dolan, E., & Bilo, G. (2018). Blood pressure variability: Clinical relevance and application. The Journal of Clinical Hypertension, 20(7), 1133–1137. https://doi.org/10.1111/jch.13304

Peng, C.-K., Havlin, S., Stanley, H. E., & Goldberger, A. L. (1995). Quantification of scaling exponents and crossover phenomena in nonstationary heartbeat time series. Chaos: An Interdisciplinary Journal of Nonlinear Science, 5(1), 82–87. https://doi.org/10.1063/1.166141

Pincus, S. M. (1991). Approximate entropy as a measure of system complexity. Proceedings of the National Academy of Sciences, 88(6), 2297–2301. https://doi.org/10.1073/pnas.88.6.2297

Plews, D. J., Laursen, P. B., Meur, Y. L., Hausswirth, C., Kilding, A. E., & Buchheit, M. (2014). Monitoring training with heart-rate variability: How much compliance is needed for valid assessment? International Journal of Sports Physiology and Performance, 9(5), 783–790. https://doi.org/10.1123/ijspp.2013-0455

Richman, J. S., & Moorman, J. R. (2000). Physiological time-series analysis using approximate entropy and sample entropy. American Journal of Physiology-Heart and Circulatory Physiology, 278(6), H2039–H2049. https://doi.org/10.1152/ajpheart.2000.278.6.h2039

Rothwell, P. M., Howard, S. C., Dolan, E., O’Brien, E., Dobson, J. E., Dahlöf, B., Sever, P. S., & Poulter, N. R. (2010). Prognostic significance of visit-to-visit variability, maximum systolic blood pressure, and episodic hypertension. The Lancet, 375(9718), 895–905. https://doi.org/10.1016/S0140-6736(10)60308-X

Schaffarczyk, M., Rogers, B., Reer, R., & Gronwald, T. (2022). Validity of the Polar H10 sensor for heart rate variability analysis during resting state and incremental exercise in recreational men and women. Sensors, 22(17), 6536. https://doi.org/10.3390/s22176536

Schäfer, A., & Vagedes, J. (2013). How accurate is pulse rate variability as an estimate of heart rate variability? International Journal of Cardiology, 166(1), 15–29. https://doi.org/10.1016/j.ijcard.2012.03.119

Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability metrics and norms. Frontiers in Public Health, 5, 258. https://doi.org/10.3389/fpubh.2017.00258

Shields, R. W. (2009). Heart rate variability with deep breathing as a clinical test of cardiovagal function. Cleveland Clinic Journal of Medicine, 76(4 suppl 2), S37–S40. https://doi.org/10.3949/ccjm.76.s2.08

St Hilaire, M. A., Gooley, J. J., Khalsa, S. B. S., Kronauer, R. E., Czeisler, C. A., & Lockley, S. W. (2012). Human phase response curve to a 1 h pulse of bright white light. The Journal of Physiology, 590(13), 3035–3045. https://doi.org/10.1113/jphysiol.2012.227892

Stranieri, A., Abawajy, J., Kelarev, A., Huda, S., Chowdhury, M., & Jelinek, H. F. (2013). An approach for Ewing test selection to support the clinical assessment of cardiac autonomic neuropathy. Artificial Intelligence in Medicine, 58(3), 185–193. https://doi.org/10.1016/j.artmed.2013.04.007

Sundkvist, G., Lilja, B., & Almér, L.-O. (1982). Deep breathing, Valsalva, and tilt table tests in diabetics with and without symptoms of autonomic neuropathy. Acta Medica Scandinavica, 211(5), 369–373. https://pubmed.ncbi.nlm.nih.gov/7113752/

Tarvainen, M. P., Niskanen, J.-P., Lipponen, J. A., Ranta-aho, P. O., & Karjalainen, P. A. (2014). Kubios HRV – Heart rate variability analysis software. Computer Methods and Programs in Biomedicine, 113(1), 210–220. https://doi.org/10.1016/j.cmpb.2013.07.024

Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology. (1996). Heart rate variability: Standards of measurement, physiological interpretation, and clinical use. Circulation, 93(5), 1043–1065. https://doi.org/10.1161/01.CIR.93.5.1043

Van Dongen, H. P. A., Maislin, G., Mullington, J. M., & Dinges, D. F. (2003). The cumulative cost of additional wakefulness: Dose-response effects on neurobehavioral functions and sleep physiology from chronic sleep restriction and total sleep deprivation. Sleep, 26(2), 117–126. https://doi.org/10.1093/sleep/26.2.117

Varma, S., & Simon, R. (2006). Bias in error estimation when using cross-validation for model selection. BMC Bioinformatics, 7(1), 91. https://doi.org/10.1186/1471-2105-7-91

Vieira, C. L. Z., Chen, K., Garshick, E., Liu, M., Vokonas, P., Ljungman, P., Schwartz, J., & Koutrakis, P. (2022). Geomagnetic disturbances reduce heart rate variability in the Normative Aging Study. Science of The Total Environment, 839, 156235. https://doi.org/10.1016/j.scitotenv.2022.156235
