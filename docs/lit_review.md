# Physiological, Chronobiological, and Operational Foundations of a Multimodal Human-Performance Console
## A literature review aligned to the “Mission Control – Flight Surgeon” platform

**Document type:** Scoping review (PRISMA-ScR–reported) with module-aligned synthesis (IMRaD-structured)

**Scope note:** This paper synthesizes peer-reviewed scientific literature and US/EU governmental technical documents that underpin the analytic modules implemented in the *Mission Control – Flight Surgeon* application: HRV signal processing and interpretation; circadian modelling and light scheduling; fatigue forecasting and FRMS-style governance; blood-pressure variability; wearable acquisition; and integration of space-weather context (NOAA/NASA) with time-aligned physiological analytics.

---

## Abstract
**Background:** High-consequence aviation and space operations require continuous monitoring of physiological readiness under fluctuating sleep opportunity, circadian misalignment, workload, and environmental exposures. Modern field systems increasingly combine short-term heart rate variability (HRV) features, wearable-derived sleep metrics, circadian modelling, and biomathematical fatigue forecasts to support decision-making. Yet each component has non-trivial methodological dependencies (signal quality, protocol control, confounding, multiple testing) that determine whether outputs are interpretable and operationally safe.

**Objective:** To review the scientific and technical foundations relevant to a multimodal “flight surgeon console” approach, focusing on: (i) HRV standards, preprocessing, and interpretation across time/frequency/nonlinear domains; (ii) validated autonomic function testing paradigms; (iii) circadian pacemaker models and experimentally derived light phase-response curves; (iv) fatigue science, performance measurement, and biomathematical fatigue modelling; (v) blood pressure variability (BPV) as an autonomic/vascular risk construct; (vi) evidence on wearable acquisition validity; and (vii) the state of evidence linking space-weather indices to autonomic/cardiovascular outcomes.

**Methods:** A scoping review was conducted using established methodological frameworks and reported according to PRISMA-ScR (Arksey & O’Malley, 2005; Levac et al., 2010; Tricco et al., 2018; Peters et al., 2020). For the HRV–cognition component, we searched Europe PMC (REST API; English-language records with abstracts; publication dates 2000–2025) on 22 December 2025 using pre-specified title/abstract query families covering HRV and RR-interval terminology (e.g., heart rate variability, RMSSD, SDNN, HF-HRV, RR/NN interval) and cognitive domains (executive function, working memory, attention/vigilance, mental workload/cognitive load, cognitive impairment). Records were deduplicated by DOI (or PMID when DOI was absent) and mapped by year and domain. In parallel, official US/EU governmental and agency documents and high-impact consensus statements were included to support module-aligned operational context (circadian modelling, fatigue/FRMS, BPV, wearables, space weather).

**Results:** HRV is a robust noninvasive marker of autonomic regulation when measurement protocols are standardized and analyses respect known physiological constraints (record length requirements, respiration effects, ectopy/artifact handling). Contemporary guidance emphasizes transparent preprocessing and cautious interpretation of frequency-domain ratios, including the well-documented limitations of LF/HF as a sympathovagal “balance” surrogate. Systematic syntheses also support modest associations between resting vagally mediated HRV and executive function (consistent with neurovisceral integration frameworks), but effect sizes are small and highly context dependent. Circadian models (limit-cycle oscillators with light preprocessing) can predict phase and entrainment under controlled assumptions and are supported by rigorous human light phase-response curve experiments. Fatigue risk is dominated by sleep loss, time awake, and circadian phase, with objective vigilance testing (PVT-family) offering sensitive, repeatable measurement of the operational failure mode. Biomathematical models such as SAFTE/FAST provide useful forecasts when calibrated and embedded within FRMS governance rather than treated as standalone truth. Evidence associating geomagnetic activity with HRV and cardiovascular endpoints exists but is heterogeneous; effect sizes are generally small and vulnerable to confounding and time-series artefacts.

**Conclusions:** A multimodal console can be scientifically defensible if it prioritizes (i) signal validity and protocol metadata; (ii) within-person baselines; (iii) transparent modelling assumptions; (iv) conservative uncertainty communication; and (v) governance frameworks (FRMS-style) that separate “decision support” from clinical diagnosis.

**Keywords:** heart rate variability; heart rate fragmentation; circadian rhythms; fatigue risk management; SAFTE; psychomotor vigilance test; executive function; neurovisceral integration; blood pressure variability; wearable sensors; space weather; aerospace medicine.

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
### 2.1. Review design and reporting framework
This manuscript is structured using a module-aligned approach corresponding to the *Mission Control – Flight Surgeon* platform. The HRV–cognition component was conducted as a scoping review and reported according to PRISMA-ScR (Tricco et al., 2018), guided by established scoping-review methodology (Arksey & O’Malley, 2005; Levac et al., 2010; Peters et al., 2020). Adjacent domains required for operational deployment (HRV measurement standards and preprocessing, circadian models, fatigue/FRMS science, BPV, wearable validity, space-weather context, and governance) were synthesized narratively using consensus standards, systematic reviews, and key validation studies.

### 2.2. Review questions (HRV–cognition scoping component)
The scoping component addressed four questions:

1. What study designs and populations have been used to examine associations between vagally mediated HRV and cognitive outcomes?
2. Which cognitive domains (executive function, working memory, attention/vigilance, mental workload/cognitive load, cognitive impairment) are most commonly linked to HRV metrics?
3. How are HRV features operationalized (time-domain vs frequency-domain vs vagal proxies) and what measurement conditions (posture, respiration control, time-of-day) are reported?
4. What recurring confounders and methodological limitations affect interpretation, and what evidence gaps remain for operational decision support?

### 2.3. Eligibility criteria
We included English-language records with abstracts published between 1 January 2000 and 31 December 2025. For the HRV–cognition scoping component, records were eligible if they addressed HRV (including commonly used vagally mediated indices such as RMSSD and HF-HRV, and related HRV/RR terminology such as SDNN and RR/NN interval) in relation to at least one cognitive domain: executive function, working memory, attention/vigilance, mental workload/cognitive load, or cognitive impairment/dementia. We included primary studies (observational and interventional) and reviews.

Exclusion criteria were: missing abstract; non-English language metadata; and acronym ambiguity where “HRV” did not refer to heart rate variability (minimized by requiring explicit HRV terminology in the query families; residual ambiguity would require manual exclusion). Because indexing metadata do not reliably encode participant species across all sources, the search was designed to be human-focused but was not restricted using “Humans” MeSH filters; instead, we applied deterministic title/abstract screening rules (Section 2.5), including a conservative “non-human-only” exclusion filter and disambiguation of CPT (continuous performance test vs cold pressor test) within the attention/vigilance query family. Any remaining non-human-only records or false positives would require manual exclusion during downstream screening.

### 2.4. Information sources
#### 2.4.1. HRV–cognition scoping search
The primary source was Europe PMC (accessed via its REST API). Searches were executed on **22 December 2025**. Five query families were run (Appendix B): executive function, working memory, attention/vigilance, mental workload, and cognitive impairment. A pilot (broader, higher-sensitivity) strategy is documented in Appendix A for transparency.

#### 2.4.2. Module-aligned operational context sources (standards, models, and agency documents)
Government/agency technical documents were collected from official portals:

- NOAA Space Weather Prediction Center (SWPC) product documentation (Kp index; NOAA space weather scales).
- NASA/CCMC DONKI documentation for event catalogs and API access.
- FAA advisory circulars for FRMS.
- EASA documents (fatigue management materials; air-operations/FTL rules).
- ESA Space Weather service documentation.

In addition, high-impact consensus statements and widely used methodological references underpinning non-cognition modules (e.g., HRV standards and reporting recommendations; circadian models and PRCs; fatigue-model evaluations; wearable validation) were included to support operational interpretation.

#### 2.4.3. Heart rate fragmentation (HRF) targeted literature and technical-document search
Heart rate fragmentation is an emerging set of indices that is not explicitly defined in classic HRV standards, yet it directly affects how short-term HRV metrics (especially HF power and beat-to-beat indices) can be interpreted in aging and disease contexts. Therefore, we conducted a targeted narrative search on **23 December 2025** to identify: (i) foundational method papers defining HRF indices and related symbolic-dynamics formulations; (ii) large-cohort studies evaluating associations with cardiovascular outcomes, atrial fibrillation, and cognitive endpoints; (iii) papers focused on the methodological interaction between HRF and traditional HRV interpretation; and (iv) any governmental/agency documents that mention HRF in an operational monitoring context.

Searches were conducted in PubMed and Crossref, with supplementary full-text retrieval from the U.S. National Library of Medicine’s PubMed Central when available. Search terms included “heart rate fragmentation”, “fragmented sinoatrial dynamics”, “percentage of inflection points”, “sinus alternans”, and “erratic sinus rhythm,” combined with operationally relevant constructs (sleep, recovery, cognitive decline, fatigue, workload, allostatic load, and atrial fibrillation screening).

Because we did not identify major governmental/agency standards that directly operationalize HRF as of the search date, the translation in this review is framed primarily from peer-reviewed evidence, and explicitly bounded by the absence of consensus norms and the dependence of HRF estimates on beat classification and artefact control.

### 2.5. Search strategy and record management
Search strings were pre-specified to emphasize HRV/RR-interval terminology (e.g., heart rate variability, RMSSD, SDNN, HF-HRV, RR/NN interval) and key cognitive constructs. Full query strings are provided verbatim in Appendix B to enable replication; the pilot strategy and counts are preserved in Appendix A.

Records were retrieved in JSON format (pageSize=1000; bounded pagination) and deduplicated using a deterministic rule: DOI (case-insensitive) when available; otherwise PMID; otherwise the source-specific record identifier.

After deduplication, title/abstract screening was performed using deterministic, rule-based filters applied to Europe PMC core records (`abstractText`).

A record was excluded as “non-human-only” if its title/abstract contained animal-species keywords (rat/rats; mouse/mice/murine; dog/dogs/canine; pig/pigs/porcine; sheep/ovine; rabbit/rabbits; monkey/monkeys/macaque/primate; zebrafish; drosophila; C. elegans) and did not contain human-study indicators (human(s); participant(s); patient(s); volunteer(s); clinical; trial; adult(s); child(ren); adolescent(s); student(s)). This conservative filter was designed to remove clear non-human-only records while minimizing false exclusions; ambiguous cases were retained for downstream screening.

Because “CPT” is ambiguous (continuous performance test vs cold pressor test), records retrieved by the attention/vigilance query family that contained “cold pressor” in title/abstract were excluded as false positives for cognition.

Records that matched only RR/NN interval terminology without explicit HRV descriptors (heart rate variability/HRV; RMSSD; SDNN; HF-HRV) were flagged for manual verification but retained.

### 2.6. Data charting
For each unique record remaining after deduplication and title/abstract screening (non-human-only exclusion and CPT disambiguation), we charted: title, year, journal, DOI/PMID, publication type, open-access status (when available), and which query family/families retrieved the record. This charting enabled an evidence map across cognitive domains and years.

### 2.7. Synthesis approach
Scoping results are summarized as (i) a PRISMA-style accounting of records and (ii) an evidence map by cognitive domain and publication year (Section 3.0). These findings are then integrated with the broader module-aligned synthesis, emphasizing measurement validity, protocol constraints, and operational governance.

### 2.8. Critical appraisal
Consistent with PRISMA-ScR guidance, we did not perform formal risk-of-bias appraisal for every included study. Where mechanistic claims are made, we preferentially cite consensus standards, controlled studies, and systematic reviews, and treat observational associations as hypothesis-generating unless replicated.

### 2.9. Reference verification and traceability
To minimize citation error, all peer-reviewed sources were required to have a resolvable DOI or a stable URL. DOI-based references were verified using DOI resolution to ensure that the cited metadata corresponded to the intended publication. Older articles without DOI metadata were cited using stable bibliographic portals (e.g., PubMed). US/EU governmental and agency documents were cited from official publisher portals (e.g., FAA advisory circular PDFs; NOAA/ESA documentation portals; NASA NTRS), emphasizing stable URLs over transient mirrors.

### 2.10. Limitations of this review
This manuscript includes a PRISMA-ScR scoping component focused on HRV–cognition evidence indexed in Europe PMC and retrievable using the query families in Appendix B (Appendix A documents the pilot strategy). Europe PMC indexing and metadata evolve over time; therefore, rerunning the same searches on a different date may yield different record counts. In addition, because “Humans” tagging is incomplete across sources and because acronym ambiguity can occur (e.g., CPT), the scoping search was not restricted using MeSH filters; instead, we applied deterministic title/abstract screening rules (non-human-only exclusion and CPT disambiguation). Downstream screening remains required to confirm species and remove residual non-human records and other false positives.

Finally, the manuscript is multi-domain: while HRV–cognition evidence is mapped using scoping methods, non-cognition modules (circadian modelling, fatigue/FRMS, BPV, wearables, space weather) are synthesized using module-aligned consensus standards and key validation studies rather than exhaustive scoping searches for every subtopic.

---

## 3. Results
### 3.0. Evidence identification and evidence map (HRV–cognition scoping component)
Across five pre-specified query families (executive function, working memory, attention/vigilance, mental workload, cognitive impairment), Europe PMC returned **2,736** records (22 December 2025; Appendix B). After DOI/PMID-based deduplication, **2,090** unique records remained (58 without a DOI), with 646 duplicates removed. Deterministic title/abstract screening excluded 12 non-human-only records and an additional 61 records due to CPT ambiguity (“cold pressor” false positives within the attention/vigilance query family), leaving 2,017 records for evidence mapping. The query-family yields were: executive function (946), working memory (331), attention/vigilance (496), mental workload (504), and cognitive impairment (459). Because records can match multiple query families, these counts are not mutually exclusive.

A PRISMA-ScR-style flow narrative for this scoping component is as follows: (i) **Identification:** 2,736 records were identified on 22 December 2025 across five query families (Appendix B). (ii) **Deduplication:** 646 duplicates were removed using DOI/PMID-based deduplication, leaving 2,090 unique records (58 without DOI metadata). (iii) **Title/abstract screening (rule-based):** 2,090 records were screened; 12 non-human-only records were excluded. Because CPT is ambiguous (continuous performance test vs cold pressor test), 61 additional records were excluded as “cold pressor” false positives within the attention/vigilance query family. This left 2,017 records for record-level charting and evidence mapping. Additionally, 14 records that matched RR/NN interval terms without explicit HRV descriptors were flagged for manual verification but retained. (iv) **Full-text eligibility:** full-text eligibility assessment was not performed in this step; therefore, counts for “full texts assessed” and “studies included” are not reported and would require downstream screening.

Year distribution of records (Europe PMC `pubYear` metadata; after screening) was concentrated in recent years: 2020 (138), 2021 (196), 2022 (204), 2023 (205), 2024 (221), and 2025 (326) (Appendix B; retrieved 22 December 2025).

Europe PMC open-access metadata flagged 1,239/2,017 records (61.4%) as open access. The most frequent journal titles were Sci Rep (87), PLoS One (85), Front Psychol (78), Sensors (Basel) (75), Psychophysiology (44), and Int J Psychophysiol (43). Publication-type tags were dominated by “journal article” (1,986); review-tagged records included “review” (168) and “systematic review” (43) (metadata tags are not mutually exclusive).

Operationally, the map underscores two practical points: (i) HRV–cognition evidence spans heterogeneous populations (healthy, clinical, aging) and heterogeneous cognitive endpoints (task performance, neuropsychological batteries, workload paradigms), and therefore requires careful protocol metadata and confounder control; and (ii) the strongest mechanistic interpretations remain anchored to vagally mediated HRV proxies and to controlled measurement conditions, consistent with neurovisceral integration frameworks.

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

Validation studies indicate that the Polar H10 can provide RR intervals suitable for many HRV analyses, with caveats during higher-intensity exercise and for certain nonlinear metrics (Schaffarczyk et al., 2022).

For sleep and circadian estimation, actigraphy remains foundational, but consumer multi-sensor wearables introduce both promise and risk: multi-sensor systems can capture autonomic parameters at scale, yet proprietary algorithms and firmware changes complicate reproducibility. Reviews in sleep medicine emphasize careful validation and standardized performance assessment before using consumer sleep tracking in research or clinical workflows (de Zambotti et al., 2019).

#### 3.2.5. Protocol standardization, stationarity, and respiration metadata
Short-term HRV features are often treated as “simple” because they can be computed quickly, but the inferential assumptions are not simple. Most HRV measures computed from short segments implicitly assume that the signal is *approximately stationary* over the analysis window, meaning that the statistical properties are not dominated by trends, step changes, or abrupt behavioral shifts. In field monitoring, this assumption is violated frequently: posture changes, speaking, anticipatory stress, and even minor movement can alter RR patterns within seconds.

Two consequences follow. First, the console must treat protocol metadata as part of the measurement, not as optional annotation. A 5-minute supine recording immediately after waking is physiologically and statistically different from a 5-minute seated recording after commuting or exercise. Second, many “physiological interpretations” of HRV metrics rely on structured respiration-driven variability. Respiratory sinus arrhythmia (RSA) is a real physiological phenomenon, but respiration also acts as a controllable confound: changing breathing rate or depth changes the spectral placement and magnitude of RR oscillations (Grossman et al., 1991). Therefore, when a console presents frequency-domain features, the defensible practice is to either (i) standardize breathing instructions (and record the cadence) or (ii) measure respiration and interpret spectral power conditionally.

Reporting recommendations emphasize documenting these factors precisely because they can create spurious longitudinal change: an apparent shift in HF power may reflect altered breathing, not altered autonomic regulation (Laborde et al., 2017; Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology, 1996). Operationally, this is a design constraint. If the app cannot verify stable measurement conditions, it should present results with reduced confidence and discourage fine-grained interpretation.

#### 3.2.6. Quality gates: plausibility screening, ectopy, and correction thresholds
Operational HRV systems should be designed to “fail closed” at the preprocessing layer. This is because many downstream metrics—especially nonlinear features—can change dramatically in the presence of missed beats, spurious detections, or excessive interpolation. A defensible preprocessing stack therefore includes at least three layers of QC.

1. **Physiological plausibility checks.** RR values outside plausible human ranges (given context and heart rate) should be flagged. Sudden isolated RR spikes often indicate detection errors rather than physiology.
2. **Beat classification and ectopy handling.** Ectopic beats are not just noise; they represent different electrophysiology. If an RR series contains ectopy, the console must decide whether it is in scope to correct, to segment, or to exclude. Robust artefact-correction methods provide a defensible rationale for correction when the fraction of affected beats is low (Lipponen & Tarvainen, 2019).
3. **Correction transparency and thresholds.** Correction is not free: interpolation can artificially reduce or increase variability depending on method. Therefore, correction fraction should be reported alongside HRV outputs, and thresholds should be conservative. When a segment requires heavy correction, the appropriate response is typically to suppress interpretive claims and request re-measurement rather than to propagate low-quality data into a “readiness score.”

These principles align with the broader philosophy of HRV standards and reporting guidance: preprocessing decisions materially shape interpretation and must be made explicit (Laborde et al., 2017; Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology, 1996).

#### 3.2.7. Ultra-short-term HRV: what 30–60 seconds can (and cannot) support
Ultra-short-term HRV (e.g., 30–60 seconds) is attractive in operations because it reduces friction: it can be performed during check-ins, pre-task briefings, or in constrained environments. However, the inferential problem is sharper than in 5-minute recordings. When record length is very short, preprocessing choices and transient nonstationarity can dominate the computed feature, and “accuracy” can refer either to agreement with a 5-minute reference or to decision validity for a downstream endpoint.

Evidence suggests that some time-domain indices can be usable in ultra-short-term windows under *strictly controlled* resting conditions. For example, smartphone/app workflows have shown high agreement with ECG for ultra-short-term RMSSD in laboratory-rest settings (Flatt & Esco, 2013). Similarly, validation work comparing ECG to a smartphone app that computes HRV from short segments found that time-domain indices (including RMSSD) can exhibit acceptable agreement in 1-minute windows, while frequency-domain indices generally require longer segments for defensible estimation (Chen et al., 2020).

Two operational caveats follow.

1. **Ultra-short-term HRV is primarily a *screening* layer.** It can support rapid “quality checks” (e.g., unusually high artefact rates; unstable breathing; abrupt nonstationarity) and can provide coarse within-person tracking, but it should not be treated as a high-specificity diagnostic indicator.
2. **Frequency-domain interpretation is disproportionately fragile in very short segments.** Even if an app outputs LF/HF from 60–120 seconds, the estimate may be dominated by resampling choices, windowing, and ectopy handling rather than by physiology. This places a premium on transparent preprocessing and conservative suppression rules.

Methodologically, this is consistent with the broader signal-processing literature showing that RR preprocessing can materially affect downstream variability estimates, especially when data are noisy or edited aggressively (Thuraisingham, 2006). In the console’s governance terms, ultra-short-term HRV is best framed as a low-latency, low-confidence feature that should trigger either (i) standardized re-measurement (e.g., 5-minute post-waking session) or (ii) corroboration using higher-validity indicators.

### 3.3. HRV feature families and interpretive constraints
The app reports metrics across time-, frequency-, and nonlinear domains. This is not merely a software convenience; it mirrors the reality that different HRV features emphasize different physiological time scales and respond differently to confounds.

#### 3.3.1. Time-domain features: RMSSD, SDNN, and the logic of within-person baselines
Time-domain features are computed directly from NN intervals. Two measures dominate operational monitoring: SDNN and RMSSD.

- **SDNN** summarizes overall dispersion of NN intervals over the recording window. In short-term recordings, SDNN reflects a mixture of mechanisms; in 24-hour recordings, it integrates circadian and activity-driven variability and has strong prognostic associations in clinical cardiology. However, SDNN is not interchangeable across recording durations (Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology, 1996).

- **RMSSD** captures beat-to-beat variability and is mathematically linked to vagally mediated changes under resting conditions. For operational readiness, RMSSD is attractive because it is comparatively robust to slow nonstationarity and can be derived from short recordings. Nonetheless, RMSSD is still sensitive to posture, breathing pattern, and ectopy artefacts.

A recurring theme in the monitoring literature is that the most defensible use of short-term HRV in readiness is *within-person*, not cross-sectional. In large systematic reviews, even healthy adults show wide dispersion of “normal” values (Nunan et al., 2010). This implies that population norms are better treated as contextual priors than as deterministic thresholds.

Operational monitoring frameworks often operationalize this point via **log-transformed RMSSD (lnRMSSD)** and rolling baselines to stabilize variance and emphasize within-person deviation rather than cross-sectional ranking. In practice, averaging across repeated short measurements can improve stability and reduce sensitivity to transient noise sources (e.g., small protocol deviations or occasional artefacts), which is especially important when the decision horizon is short. The direct translation to aerospace contexts is conceptual rather than literal: the “training load” analogue may be cumulative operational stressors, sleep debt, circadian disruption, or illness. The key methodological move is the same—use repeated measurements, stabilize estimates via aggregation, and interpret deviations relative to a personalized baseline.

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

Beyond interpretive controversies, frequency-domain HRV has methodological fragility that is operationally relevant.

**Spectral estimation is not neutral.** Practical pipelines usually convert unevenly sampled RR intervals into an evenly sampled time series via interpolation and then apply spectral estimation (e.g., FFT-based modified periodograms such as Welch’s method) or use methods designed for unevenly sampled series (e.g., Lomb–Scargle periodograms) (Welch, 1967; Lomb, 1976; Scargle, 1982). Choices about resampling rate, detrending, windowing, and segment rejection can shift LF/HF materially in short recordings. This matters in dashboards because users often interpret small changes as “physiological change,” when the dominant driver can be a different preprocessing path.

**Normalization can conceal absolute changes.** Many implementations report “normalized units” (LFnu, HFnu) by dividing LF and HF by total power minus VLF. This can be useful for presentation but can also obscure whether both LF and HF fell (global suppression) or whether only one component shifted. In readiness contexts, absolute power and time-domain vagal proxies may be more interpretable than normalized ratios, particularly when record length and respiration are not controlled.

**VLF in short-term segments is frequently misused.** The Task Force guidance emphasized that VLF estimation is unreliable in short-term recordings. Operationally, this is a reason to either omit VLF-derived conclusions from short segments or to label them explicitly as low-confidence descriptive features (Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology, 1996).

Taken together, these considerations argue for a conservative UI design: show frequency features with preprocessing provenance (window length, resampling method, respiration metadata) and avoid framing them as single-cause mechanistic readouts.

#### 3.3.3. Nonlinear and complexity metrics: what they add (and what they require)
Nonlinear features are often marketed as “advanced,” but their real value is that they capture properties not reducible to linear variance summaries. The app includes several prominent families.

**Entropy (ApEn, SampEn).** Approximate entropy (ApEn) was introduced as a statistic to quantify regularity/complexity in finite-length series (Pincus, 1991). Sample entropy (SampEn) was later proposed to reduce bias and improve consistency (Richman & Moorman, 2000). In HRV contexts, lower entropy is often interpreted as reduced adaptability or complexity-loss with aging and disease, but entropy estimates are sensitive to parameter choices (embedding dimension, tolerance) and to artefacts.

**Detrended fluctuation analysis (DFA).** DFA quantifies scaling properties and long-range correlations in nonstationary signals; Peng and colleagues demonstrated that healthy heartbeat dynamics exhibit fractal-like correlation structure and that pathological states may alter scaling exponents (Peng et al., 1995). In operational contexts, DFA-derived features can be informative but also fragile: they require sufficient data length and careful preprocessing, and their interpretation depends on whether the signal segment is stationary.

**Poincaré geometry (SD1, SD2) and their limitations.** Poincaré plots visualize NN(i) vs NN(i+1) structure. SD1 and SD2 quantify dispersion perpendicular and parallel to the identity line. However, the question “do these capture nonlinear features?” is not trivial. Brennan and colleagues examined whether existing Poincaré measures reflect nonlinear structure and highlighted limitations when such measures are treated as inherently nonlinear markers rather than geometric summaries (Brennan et al., 2001). Operationally, SD1 is often treated as a proxy for short-term variability (closely related to RMSSD), while SD2 relates to longer-term variability; but interpretive claims beyond this require caution.

**Heart rate fragmentation (HRF).** Fragmentation metrics aim to capture erratic switching in acceleration sign that is not well described by traditional HRV features. Costa and colleagues proposed HRF as a new approach to interbeat interval dynamics, suggesting it may represent altered pacemaker–autonomic interactions, particularly in aging and disease contexts (Costa et al., 2017a). For an operational console, fragmentation indices are best treated as *adjuncts* for pattern recognition and risk stratification rather than as direct “stress scores,” because their clinical meaning depends on rhythm classification and the exclusion of arrhythmias.

A key operational motivation for HRF is interpretive: traditional short-term HRV indices (including RMSSD and HF power) are often treated as proxies of cardiovagal modulation under resting conditions, but in some populations an apparent increase in beat-to-beat variability can reflect *instability* rather than adaptive vagal control. In other words, “high variability” is not always synonymous with “high vagal tone.” HRF was explicitly introduced to formalize this failure mode by quantifying *patterned volatility*—frequent reversals in acceleration sign—that can be difficult to recognize from ECG inspection and can inflate conventional short-term HRV metrics (Costa et al., 2017a; Hayano et al., 2020).

**Definition and computation (PIP, IALS, PSS, PAS).** In its most widely used formulation, HRF is quantified from NN intervals via four closely related indices (Costa et al., 2017a):

- **Percentage of inflection points (PIP):** the percentage of NN time points at which the sign of acceleration in NN intervals reverses (or transitions to/from a near-zero increment), operationalized via zero-crossings in the NN-increment series.
- **Inverse of the average length of acceleration/deceleration segments (IALS):** segments are runs between inflection points in which NN intervals decrease monotonically (acceleration) or increase monotonically (deceleration). Shorter average segments imply more rapid switching and thus higher fragmentation.
- **Percentage of short segments (PSS):** quantifies how much of the series is composed of very short acceleration/deceleration runs (a high density of brief segments).
- **Percentage of alternation segments (PAS):** captures a specific subtype of fragmentation—alternation—where acceleration sign flips on every beat (an “ABAB” alternation pattern over a minimum run length).

By construction, these indices are not redundant labels for “variability magnitude.” They are primarily probes of *local sign structure* and the persistence of monotonic runs. PAS is explicitly a subtype measure: a time series may be highly fragmented without exhibiting strict alternans, whereas a high PAS necessarily implies marked fragmentation (Costa et al., 2017a). This hierarchy is operationally useful because it supports interpretable rule-based gating (e.g., “fragmented but not alternans-dominant”).

**Symbolic-dynamics formulations and sampling-resolution dependence.** A complementary HRF formulation maps NN increments to a ternary symbolic sequence (deceleration / no-change / acceleration) and evaluates the frequency of short “word” patterns with different numbers of inflection points, with thresholds chosen to respect timing resolution (Costa et al., 2017b; Costa et al., 2018). In operational systems that ingest RR series from wearables, the analogous constraint is *vendor and firmware behavior*: any proprietary smoothing or beat correction upstream can damp (or artifactually create) rapid sign changes, directly shifting HRF indices.

**Beat classification, artefacts, and why HRF is also a quality-control primitive.** HRF is highly sensitive to beat-label integrity because missed beats, false detections, and ectopy create abrupt increments that appear as sign changes. Accordingly, foundational HRF work explicitly excludes segments around non-sinus beats when computing fragmentation indices, and also examines RR-series robustness as a secondary analysis (Costa et al., 2017a). Independent methodological work on HRV denoising confirms that fragmentation measures (e.g., PAS, PIP, PSS) are among the most artifact-sensitive HRV-derived features, meaning that signal quality issues can manifest as apparent “fragmentation” (Saleem et al., 2022). This has a practical implication for a flight-surgeon console: HRF should be treated not only as a physiological index but also as an **instrument-health flag**. When PIP/IALS/PSS rise concurrently with high artefact-correction fractions or implausible RR patterns, the first hypothesis should be measurement contamination rather than an acute physiological state change.

**Evidence base and clinical signal: HRF as sinoatrial instability and risk marker.** Empirically, HRF indices increase with age and are elevated in coronary artery disease cohorts compared with ostensibly healthy subjects, while outperforming several traditional and nonlinear HRV measures in discrimination under free-running conditions (Costa et al., 2017a). In a large community cohort (MESA), higher fragmentation was associated with incident cardiovascular events and cardiovascular mortality in adjusted models, and added incremental value to established risk indices (Costa et al., 2018). Fragmentation indices—especially PIP—have also been evaluated for long-horizon atrial fibrillation prediction in community cohorts, supporting a role for HRF as a screening covariate when interpreting HRV in older adults (Costa et al., 2021a; Guichard et al., 2025). Beyond cohort associations, analyses in cardiology-clinic populations suggest that HRF captures information about beat-to-beat rhythm control mechanisms that is not reducible to canonical HRV measures, and that greater fragmentation predicts poorer survival independently of multiple clinical risk factors (Lensen et al., 2020). A complementary perspective paper frames HRF as a dynamical marker of altered pacemaker–neuroautonomic function that may track the “pace” of biological aging, with the hypothesis that truly system-level interventions would reduce fragmentation toward more fluent patterns (Costa & Goldberger, 2019).

**From cardiovascular risk to human performance: what is defensible today.** Direct evidence linking HRF to acute operational performance endpoints (e.g., vigilance lapses, decision errors) remains limited. Nonetheless, HRF has several scientifically defensible relevance pathways to “human performance” monitoring:

1. **Guardrail against false reassurance from high short-term HRV.** In readiness contexts, an increase in HF power or RMSSD is often interpreted as “better recovery.” HRF provides a mechanism-aware caution: high-frequency variability can include fragmented, non-vagal dynamics and can confound parasympathetic functional assessment (Hayano et al., 2020). Thus, incorporating HRF can prevent “green” interpretations based solely on variability amplitude.
2. **Longitudinal risk context for cognition and brain health.** Within MESA, HRF has been used to predict cognitive decline, supporting the view that fragmented sinoatrial dynamics may relate to broader brain–heart health trajectories (Costa et al., 2021b). Complementary evidence links HRF indices to brain MRI markers of small vessel disease, providing a plausible vascular pathway through which fragmented cardiac control could covary with cognitive aging risk (Heckbert et al., 2024). These are not acute performance tests, but they are directly relevant to long-horizon mission readiness, selection, and health surveillance.
3. **Recovery modelling: sleep as a restorative perturbation.** HRF has been operationalized as a dynamic “before vs after sleep” change (ΔHRF) to quantify sleep-related improvement in cardiac neuroautonomic functionality, with the hypothesis that diminished renewability tracks aging and future event risk (Costa et al., 2022). For human performance programs, this suggests a promising construct: not only *resting baseline* but also *restoration capacity*.
4. **Stress and cumulative load constructs in ostensibly healthy samples.** HRF has been proposed as a biomarker of early allostatic load and stress reactivity in healthy adults, with evidence that HRF differentiates baseline, stressor, and recovery conditions and may show blunted reactivity patterns in individuals with elevated symptom burdens (Chan & Andersen, 2025). In parallel, HRV-based monitoring of stress and allostatic load has been studied in first responder and tactical operator populations, with systematic reviews underscoring both promise and methodological heterogeneity (Corrigan et al., 2021).

**Operational synthesis and critique.** The most defensible use of HRF in a flight-surgeon console is therefore conservative and layered:

- Use HRF as a **measurement and interpretation gate** for vagal-proxy HRV metrics (especially HF power and RMSSD), not as a standalone “stress score.”
- Compute HRF only when rhythm classification is credible (sufficient normal sinus beats; ectopy and artefact rates below thresholds), and display HRF alongside quality indicators.
- Treat persistently elevated fragmentation as a **risk-context marker** (possible sinoatrial instability, aging-related degradation, or disease risk) and as a trigger for corroboration (repeat high-fidelity ECG, clinical review), rather than as an acute workload readout.
- Explicitly communicate that HRF is not codified in classic HRV standards and lacks widely accepted normative cut points for operational decision-making; its decision utility is highest in within-person, longitudinal contexts.

In short, heart rate fragmentation provides a needed corrective to the “more HRV is always better” narrative. Its scientific value lies in separating smooth, vagally mediated variability from erratic beat-to-beat switching that can arise from degraded control, thereby reducing one important class of false inference in multimodal readiness monitoring.

A practical synthesis is that nonlinear metrics add value primarily when:

1. Signal quality is high (artefact-corrected without excessive interpolation).
2. Record lengths match the requirements of the metric (especially for scaling properties).
3. Outputs are triangulated with time/frequency features and with contextual covariates.

#### 3.3.4. HRV, self-regulation, and the neurovisceral integration framework
Many users implicitly interpret “low HRV” as “high stress.” That mapping is directionally plausible in some contexts but is not a physiological law. A more defensible framing is provided by the neurovisceral integration perspective: vagally mediated HRV (often indexed by HF-HRV/RMSSD under resting conditions) is treated as an observable marker of functional coupling between central executive networks and peripheral autonomic regulation (Thayer & Lane, 2000; Thayer et al., 2009).

The model’s operational value is that it provides a coherent hypothesis for why HRV correlates with executive function, affect regulation, and health outcomes: the same inhibitory control systems that support flexible behavior also modulate autonomic output through the central autonomic network. Later elaborations emphasize hierarchical organization and context dependence—i.e., “integration” is not uniform across tasks and may vary with threat, arousal, and individual differences (Smith et al., 2017; Thayer & Lane, 2009).

At the same time, empirical evidence also supports caution. In large-sample work linking resting HF-HRV with executive function and regional cerebral blood flow, the expected “global” integration signal is not always observed; some analyses suggest that relationships are more circumscribed than the strongest forms of the hypothesis imply (Jennings et al., 2014). For a flight-surgeon console, this pushes toward conservative design: the HRV-stress link should be presented as a *non-specific* indicator whose interpretive weight depends on context (sleep loss, workload, illness, medication, paced breathing), and whose decision utility increases when triangulated with performance tasks, symptom reports, and schedule context.

Systematic syntheses provide a useful “reality check” on effect size and heterogeneity. A systematic review and meta-analysis focused specifically on executive functions reported a small positive association between resting vagally mediated HRV and executive-function performance (overall r≈0.19), with stronger evidence for inhibition and shifting than for updating/working-memory outcomes (Magnon et al., 2022). This magnitude is operationally meaningful only when interpreted as a *probabilistic* contributor: even if the association is real, it will not support high-specificity individual classification.

Broader reviews converge on a similar direction while underscoring confounding and design limitations. A systematic review of HRV and cognition found that reduced parasympathetic activity (and in some studies increased sympathetic activity) was associated with worse cognitive performance across multiple domains, with aging and cardiovascular status emerging as major moderators (Forte et al., 2019). Importantly, a narrative systematic review of longitudinal studies suggests that higher parasympathetic HRV may predict better future cognitive performance, but also emphasizes that the longitudinal evidence base remains comparatively small and methodologically heterogeneous (Nicolini et al., 2024). For an operational platform, the implication is that HRV can be a *risk and resilience marker* relevant to cognition, but not a stand-alone cognitive assay.

Evidence in neurodegenerative disease and dementia contexts provides both supportive signals and heterogeneity. A systematic review and meta-analysis reported a moderate association between higher HRV and better cognition/behavior across neurodegenerative conditions (r≈0.25) (Liu et al., 2022). In contrast, meta-analytic comparisons of dementia/neurocognitive-disorder groups to controls show that resting HRV is lower on average, with variability by subtype and measurement (Cheng et al., 2022). At the individual-study level, null differences have also been reported under standardized short-term resting protocols in Alzheimer’s disease and vascular dementia (Allan et al., 2005), underscoring sensitivity to protocol, phenotype, comorbidity, and medication.

Finally, cognition is not only an endpoint; it is also a state-dependent *perturbation* of autonomic dynamics. Experimental work shows that mental workload can acutely alter HRV and reduce nonlinear dynamics, meaning that “HRV suppression” may reflect momentary cognitive demand rather than degraded readiness per se (Delliaux et al., 2019). This creates a practical interpretive constraint: the console should explicitly separate **resting, protocol-controlled HRV** (trait-like baseline and recovery tracking) from **task-evoked HRV** (state reactivity during cognitive load), and should avoid interpreting task-related vagal withdrawal as a pathological signal without corroboration.

Taken together, the most defensible translation is to treat HRV–cognition links as *contextual modifiers* that increase decision utility when combined with direct performance measures (e.g., PVT-family tasks) and schedule/sleep context, rather than as a replacement for cognitive testing.

### 3.4. Autonomic function tests: controlled provocations vs passive monitoring
The app includes autonomic function tests (deep breathing, Valsalva, orthostatic responses). These tests differ from passive HRV monitoring because they intentionally provoke autonomic reflexes to probe specific pathways.

#### 3.4.1. Deep breathing tests (E:I responses)
Deep breathing protocols aim to amplify RSA and quantify cardiovagal responsiveness. Classic clinical approaches compute the expiration–inspiration (E:I) ratio or related heart rate response metrics. Studies in diabetics with and without symptoms of autonomic neuropathy show that deep breathing responses can be sensitive to autonomic dysfunction, though specificity varies with protocol and patient group (Sundkvist et al., 1982). Reviews of clinical autonomic testing emphasize that HRV with deep breathing is a sensitive cardiovagal measure and that standardized coaching (especially breathing rate, depth, and posture) is essential for interpretability (Shields, 2009).

Operationally, deep breathing tests offer two advantages:

- They provide a standardized *challenge* condition that can be more comparable across days than free-breathing rest.
- They can separate “low resting HRV due to transient factors” from “blunted vagal reactivity,” although this is not perfect.

However, deep breathing tests also introduce their own confounds: learning effects, poor compliance with breathing cadence, and anxiety-induced sympathetic activation.

#### 3.4.2. Valsalva manoeuvre and orthostatic ratios
The Valsalva manoeuvre probes baroreflex function across phases of pressure change, and the Valsalva ratio is a commonly reported summary. Orthostatic ratios (e.g., 30:15) reflect the immediate heart rate response to standing. In practice, these tests are used as part of batteries rather than interpreted in isolation. Selecting an appropriate test battery (or subset) is itself a methodological decision with trade-offs between sensitivity, specificity, user compliance, and operational feasibility.

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
2. **Predictions must remain conservative.** Even in controlled studies, individuals vary in light sensitivity and in the magnitude of circadian responses, implying that model-based prescriptions should be presented as *risk-reducing guidance* rather than deterministic instructions (Chellappa, 2020).

#### 3.7.3. Oscillator-based circadian pacemaker models: mechanistic structure with operational utility
The app’s circadian module draws on a family of models that treat the circadian pacemaker as a limit-cycle oscillator coupled to light via photic preprocessing. Forger and colleagues presented a biologically grounded model capable of reproducing key human phase-resetting phenomena (Forger et al., 1999). Complementary work refined photic drive and oscillator structure to better match empirical PRCs and entrainment behavior (Jewett et al., 1998). More recent modelling work emphasizes “macroscopic” approaches and parameter identifiability—critical issues when applying models to individuals with limited calibration data (Hannay et al., 2019).

From an aerospace-human-factors perspective, the value of these models is not that they “prove” circadian mechanisms, but that they provide a **computable mapping** from schedules to predicted phase, enabling what-if analyses (e.g., projected phase at launch time given a light plan). The scientific defensibility of this mapping depends on transparent assumptions: light measurement, adherence to the schedule, baseline entrainment state, and whether the model is individualized.

#### 3.7.4. Circadian modulation of HRV and cardiovascular physiology: time-of-day as a confound
Even when a user’s behavior is stable, autonomic physiology exhibits circadian modulation. Early ambulatory work demonstrated a circadian pattern in HRV, with systematic variation across the 24-hour day (Mølgaard et al., 1991). This matters operationally because many HRV dashboards implicitly compare “today vs. yesterday” or “today vs. baseline,” yet a measurement taken at 0600 and one taken at 2200 are not comparable without time-of-day normalization and behavioral metadata.

Therefore, a conservative multimodal console should incorporate at least one of:

- **Protocol standardization:** measure at consistent times and conditions (e.g., post-waking, supine, fixed breathing instructions).
- **Circadian-aware baselines:** maintain baselines stratified by clock time or model phase.
- **Covariate adjustment:** include time-of-day (and ideally model phase) in statistical models to prevent spurious “fatigue” interpretations.

#### 3.7.5. Sleep-stage structure: why “nightly HRV” is not a single physiological state
Even if a wearable provides a single nocturnal RMSSD value, the underlying physiology is not constant over the night. Autonomic regulation shifts across sleep stages (NREM vs REM) and interacts with circadian phase. This matters because sleep-stage composition changes with sleep debt, alcohol, stress, and circadian misalignment—exactly the conditions that operational monitoring seeks to track.

In controlled laboratory work, HRV exhibits systematic circadian variation across sleep stages, implying that both *when* in the circadian cycle a sleep episode occurs and *which stages dominate* can shift the distribution of HRV values (Boudreau et al., 2013). Operationally, this means that two “similar” nights can yield different nocturnal HRV summaries simply because of differences in stage structure or timing.

For the console’s architecture, the implication is to treat nocturnal HRV as a structured time series rather than as a scalar. When possible, compute HRV on comparable within-night windows (e.g., stable 5-minute segments) and interpret changes alongside sleep staging or at least alongside sleep timing metadata.

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
Biomathematical fatigue models represent an attempt to formalize well-established drivers of performance impairment—sleep history (homeostatic sleep pressure), circadian phase, and sleep inertia—into a forecast of expected alertness or task effectiveness. Reviews of fatigue modelling in work settings describe how such models are used to compare schedules, identify periods of elevated risk, and support FRMS decision-making, while also documenting limitations and common misuses (Dawson et al., 2011).

A key operational distinction is that fatigue models are **schedule-to-risk mappings**, not direct measurements of performance. Their utility therefore depends on how accurately schedules and sleep opportunities are represented and how closely the model’s assumptions match the population and context. Many operational tools also include a layer that *predicts sleep obtained* during planned rest opportunities (e.g., inflight bunk rest). This can be highly valuable when objective sleep measurement is unavailable, but it also introduces additional uncertainty: errors in predicted sleep propagate directly into the predicted risk state.

Applied aviation evidence illustrates both promise and constraint. Devine and colleagues compared biomathematical model predictions to sleep diary and actigraphy from ultra-long-range humanitarian flights and reported strong agreement between predicted and observed sleep estimates during these atypical operations (Devine et al., 2022). Such results support the use of modelling as a practical forecasting layer when direct measurement is sparse. However, they should not be overgeneralized into universal “validation.” Agreement in sleep prediction does not guarantee accurate prediction of all cognitive outcomes, and model performance can vary with rest quality, operational countermeasures, and circadian disruption patterns.

Consequently, a conservative console should treat fatigue-model outputs as *risk indicators* whose confidence depends on explicit conditions:

- **Input validity.** Predictions are only as reliable as the underlying schedule and sleep inputs (including time-zone handling and duty/rest definitions).
- **Population calibration.** Most models are calibrated at the population level; without individual calibration, uncertainty is larger for outliers and vulnerable subgroups.
- **Unmodelled determinants.** Illness, acute stress, workload, medications, and stimulant use can materially shift risk but may not be captured.
- **Operational extremes.** Very long duty periods, unusual rest environments, and rapidly shifting schedules can push models outside their intended calibration range.

These constraints argue for “fail-closed” behaviour: when inputs are missing or conditions are outside calibration, the console should reduce confidence and prompt objective verification (e.g., PVT-family testing) rather than presenting a deceptively precise single-number forecast.

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
Chest-strap ECG sensors estimate RR intervals from electrical depolarization and can be highly accurate at rest. Validation studies show that Polar H10 RR intervals exhibit high agreement with ECG across common resting protocols, supporting many HRV analyses (Schaffarczyk et al., 2022).

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

#### 3.9.3. Wearables as clinical instruments: reliability, drift, and translation barriers
Wearables create a “measurement abundance” problem: the limiting factor is not feature computation, but trust in the signal chain and in the stability of algorithms over time. Reviews of wearable devices in precision medicine emphasize both the promise (continuous longitudinal monitoring; detection of arrhythmias and infection-related physiological changes) and the translational barriers, including data standardization, privacy/security, regulatory alignment, and clinical validity (Babu et al., 2024).

Similarly, focused reviews of wearable heart rate and HRV monitoring highlight that measurement validity depends on sensor modality, motion conditions, and the device’s processing pipeline, and that clinical value requires careful attention to accuracy and interpretability trade-offs (Alugubelli et al., 2022). For operational dashboards, these reviews support a conservative engineering stance: treat wearable-derived HRV as an *instrument output* that requires calibration, provenance tracking, and periodic revalidation.

#### 3.9.4. Pre-symptomatic illness detection: baseline deviation as a detection strategy
One reason HRV and related autonomic metrics are attractive in “mission control” concepts is that they may shift early in systemic illness, inflammation, or infection. A prominent example is the use of smartwatch-derived physiological data for pre-symptomatic detection of COVID-19, which demonstrated that individualized anomaly detection on wearable time series can flag a subset of cases before symptom onset (Mishra et al., 2020).

This evidence supports a key design principle already emphasized in this review: **within-person baselines dominate cross-sectional thresholds**. The Mishra approach is fundamentally deviation-based—detecting departures from an individual’s own expected trajectory—rather than comparing to population cutoffs. However, it also reinforces the need for governance: deviation-based detectors will generate false positives whenever non-infectious perturbations (sleep restriction, psychological stress, alcohol, travel) shift physiology. Therefore, illness-detection modules should be framed as screening/triage tools that prompt corroboration (symptom checks, confirmatory testing, clinical assessment) rather than as diagnostic statements.

#### 3.9.5. HRV for drowsiness and vigilance risk: promising signals, difficult ground truth
In transportation and safety research, HRV features have been used as inputs to machine-learning models for drowsiness detection, typically paired with behavioral labels or proxy measures. Recent work demonstrates the feasibility of wearable HRV–based drowsiness classification using modern ML pipelines (AlArnaout et al., 2025). For a flight-surgeon console, the relevance is conceptual: HRV may carry information about autonomic arousal and fatigue-related state changes.

However, this application also illustrates a recurrent limitation: “ground truth” for drowsiness is often noisy (self-report, lane-keeping proxies, or limited task batteries), and HRV can be confounded by workload, posture, and respiration. Therefore, HRV-based drowsiness indicators should be treated as adjunctive features and anchored—when feasible—to direct performance measures (e.g., PVT-family tasks).

### 3.10. Space-weather integration: indices, data products, and the evidentiary bar for physiology links
The app integrates NOAA/NASA space-weather context with time-aligned physiological analytics. From a scientific perspective, this is best framed as a hypothesis-generating module: it merges a well-characterized geophysical measurement domain with a physiologic domain where effect sizes are likely small and confounding is substantial.

#### 3.10.1. Data products: what Kp and event catalogs actually represent
NOAA’s Space Weather Prediction Center (SWPC) provides standard indices and explanatory documentation. The planetary K index (Kp) reflects global geomagnetic activity derived from multiple magnetometer stations and is commonly used to characterize geomagnetic disturbances (NOAA Space Weather Prediction Center [SWPC], n.d.-a). NOAA also publishes standardized space weather scales (G for geomagnetic storms, S for solar radiation storms, R for radio blackouts), which support categorical operational communication (NOAA Space Weather Prediction Center [SWPC], n.d.-b).

NASA’s Community Coordinated Modeling Center (CCMC) maintains the DONKI system to catalogue space-weather events (e.g., solar flares, CMEs, geomagnetic storms) and provides an API-oriented interface for retrieving event timing and metadata (NASA/CCMC, n.d.). These resources enable reproducible alignment between geophysical events and physiological time series if timestamps, time zones, and sampling windows are handled correctly.

European operational documentation is also available. The ESA Space Weather Service Network maintains program documents (requirements, system descriptions, and product catalogues) that support standardized interpretation and integration of European space-weather products (European Space Agency [ESA], n.d.).

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
Naïve validation approaches can dramatically overestimate performance when temporal dependence exists. Work on cross-validation for time series emphasizes that standard random-fold CV can be invalid under autocorrelation; blocked or forward-chaining CV approaches are needed to avoid leakage (Bergmeir et al., 2018). In addition, model selection, feature engineering, and threshold/hyperparameter tuning must be nested within the validation procedure to avoid optimistic bias. These issues generalize to multimodal physiology: if thresholds are tuned on past missions and then evaluated on the same data, the dashboard will appear more accurate than it is.

#### 3.11.5. Interpretability: useful explanations without reification
Operational adoption often requires explanations. Feature attribution methods such as SHAP (Shapley additive explanations) provide a mathematically grounded way to attribute model predictions to input features. Lundberg and colleagues introduced efficient algorithms for consistent feature attribution in tree ensembles and demonstrated how local explanations can aggregate to global understanding (Lundberg et al., 2020). In a flight-surgeon console, interpretability should be treated as a *communication layer* that aids oversight, not as a proof of causality.

#### 3.11.6. Reporting and appraisal frameworks for prediction models: TRIPOD, PROBAST, and extensions to AI/ML
Physiological consoles routinely embed prediction logic, yet the transparency and rigor of such models often lag behind the standards expected in clinical prediction research. Reporting guidelines and risk-of-bias assessment tools developed for prognostic and diagnostic prediction models provide a blueprint for disciplined model development, evaluation, and deployment.

**TRIPOD: Transparent reporting for prediction models.** The Transparent Reporting of a multivariable prediction model for Individual Prognosis Or Diagnosis (TRIPOD) statement was published to improve the quality and transparency of prediction model studies by specifying a 22-item checklist for reporting model development, validation, and updating studies (Collins et al., 2015). TRIPOD emphasizes that full and clear reporting of all aspects of a model—from participant selection and predictor definitions to model specification, performance metrics, and handling of missing data—is essential for readers to assess risk of bias and clinical usefulness. While TRIPOD was originally developed for regression-based models, its core principles (transparent study design, explicit handling of data, reproducible feature definitions, and honest reporting of limitations) apply equally to operational physiology dashboards.

Recognizing that machine learning and artificial intelligence methods have become widespread in prediction model development, an extension to TRIPOD was recently published. TRIPOD+AI updates the original 22-item checklist to 27 items, harmonizing guidance for studies that use either regression or machine learning methods (Collins et al., 2024). Key additions address algorithm selection and tuning, handling of model complexity and interpretability, data preprocessing pipelines, and documentation of software and code availability. For a mission-medicine console, TRIPOD+AI underscores that prediction components—whether a biomathematical fatigue forecast, an HRV-derived stress classifier, or an illness-detection anomaly model—should be documented with the same rigor expected of publishable clinical prediction models: clear definition of predictors, explicit preprocessing and feature engineering steps, transparent model-selection procedures, appropriate validation strategies, and honest reporting of performance across clinically relevant subgroups and conditions.

**PROBAST: Risk-of-bias assessment for prediction model studies.** Systematic reviews of prediction models require tools to evaluate study quality. The Prediction model Risk Of Bias ASsessment Tool (PROBAST) provides a structured framework to assess risk of bias and applicability in four domains: participants, predictors, outcome, and analysis (Wolff et al., 2019; Moons et al., 2019). PROBAST uses signaling questions to guide reviewers in identifying methodological weaknesses—such as inappropriate participant selection, poorly defined predictors, outcome measurement issues, or analytic flaws like overfitting, inadequate sample size, or failure to validate the model. In a console development context, PROBAST logic can inform internal quality assurance: Are the "participants" (missions, individuals, measurement sessions) representative of the intended use population? Are predictors (HRV features, sleep estimates) measured with acceptable validity and without incorporating future information? Is the outcome (performance failure, illness, fatigue) defined prospectively and measured without bias? Are analyses transparent, with appropriate handling of missing data, model complexity, and calibration assessment?

Recently, PROBAST was updated to better accommodate prediction models developed with artificial intelligence and machine learning methods. PROBAST+AI is structured to support assessment of both **model development** and **model evaluation**, using targeted signaling questions that cover domains including participants/data sources, predictors, outcome, and analysis (Moons et al., 2025). For operational dashboards, PROBAST+AI serves as a governance checklist: Does the development dataset reflect the operational environment? Are predictor definitions stable across device updates? Is model tuning separated from final evaluation? Are calibration and uncertainty reported in a way that supports safe thresholding and fail-closed behavior?

Together, TRIPOD+AI and PROBAST+AI establish a disciplined standard for any prediction component embedded in a physiological console. If a fatigue forecast or HRV classifier cannot meet these standards—or if meeting them reveals that performance is marginal, poorly calibrated, or non-generalizable—then the console design should either improve the model, restrict its use to narrow validated conditions, or remove it in favor of simpler indicators.

#### 3.11.7. Decision-analytic evaluation: moving beyond discrimination to clinical utility
Traditional prediction model evaluation emphasizes discrimination (e.g., area under the ROC curve, AUC) and calibration (agreement between predicted probabilities and observed event rates). While these metrics are necessary, they are not sufficient for operational decision support. A model with excellent AUC may still fail to improve decisions if its predictions do not align with the decision threshold that operators actually use, or if acting on the predictions does not change outcomes.

**Decision curve analysis (DCA)** formalizes the idea that model evaluation should account for decision consequences. DCA explicitly incorporates the trade-off between false positives and false negatives as a function of the decision threshold, and it quantifies the net benefit of using a model compared to alternative strategies (treating all, treating none, or using a simpler model) across a range of thresholds (Vickers & Elkin, 2006). The key conceptual advantage of DCA is that it does not assume a single fixed threshold; instead, it recognizes that the acceptable trade-off between sensitivity and specificity depends on the clinical or operational context and the relative costs of action versus inaction.

For a flight surgeon console, DCA logic is directly applicable. Consider a fatigue risk classifier that flags individuals at high risk of performance impairment. The decision threshold for flagging should reflect the operational context: In a high-consequence safety-critical role, the cost of missing an impaired operator (false negative) may be much higher than the cost of unnecessarily restricting a capable operator (false positive). Conversely, in a resource-constrained environment where pulling someone from duty creates operational strain, the threshold might shift. DCA makes these trade-offs explicit by plotting net benefit as a function of threshold probability, allowing decision-makers to see whether the model provides value at the thresholds they actually care about.

Crucially, DCA also exposes when a prediction model adds no value. If the decision curve for the model does not exceed the curves for "treat all" or "treat none" strategies—or if it does not exceed a simpler baseline model (e.g., using only sleep history without HRV)—then the added complexity is not justified. For operational consoles, this is a strong argument for incremental validation: each new module or feature should demonstrate decision-analytic value beyond what simpler inputs already provide, rather than being added because the feature is "available" or "interesting."

#### 3.11.8. Regulatory and institutional guidance for clinical decision support software
Physiological monitoring consoles occupy a gray zone in medical device regulation: they may support clinical or operational decisions without being explicitly labeled as diagnostic devices. However, the principles articulated in regulatory and institutional guidance for clinical decision support (CDS) software and software as a medical device (SaMD) are directly relevant to operational physiology platforms, particularly when those platforms influence safety-critical decisions.

**FDA Clinical Decision Support Software guidance.** In September 2022, the U.S. Food and Drug Administration published final guidance clarifying its regulatory oversight of clinical decision support software (U.S. Food and Drug Administration [FDA], 2022). The guidance interprets section 520(o)(1)(E) of the Federal Food, Drug, and Cosmetic Act, which excludes certain CDS software functions from the definition of a medical device if they meet four criteria. A summary interpretation of these four criteria is provided in the FDA’s CDS guidance materials and FAQs (FDA, 2022; FDA, n.d.).

While this guidance is specific to U.S. regulatory context, its logic is instructive for any decision-support console. The four criteria collectively emphasize transparency, clinician autonomy, and the distinction between tools that support reasoning versus tools that replace reasoning. For a mission-medicine platform, this framing suggests that the console is most defensible when it:

- Surfaces the basis for its outputs (e.g., "fatigue forecast elevated due to 4 hours sleep in past 24 hours and adverse circadian phase"),
- Provides recommendations or contextualized information rather than binary directives (e.g., "consider additional rest or objective performance testing" rather than "operator unfit for duty"),
- Avoids replacing clinical or operational judgment with algorithmic outputs presented as definitive.

Conversely, if the console processes continuous physiological signals (e.g., real-time ECG waveforms) or provides time-critical automated alerts that operators are expected to act on immediately without independent corroboration, it may cross into regulated device territory and require additional validation, quality system controls, and regulatory clearance or approval.

**IMDRF Software as a Medical Device: Clinical Evaluation.** The International Medical Device Regulators Forum (IMDRF) published guidance on clinical evaluation of Software as a Medical Device (SaMD), providing a framework for assessing the safety, effectiveness, and performance of software intended for medical purposes (International Medical Device Regulators Forum [IMDRF], 2017). The central operationally relevant principle is risk proportionality: the level of clinical evaluation and performance evidence should be commensurate with the intended purpose, context of use, and potential harms if the software output is wrong.

For SaMD, clinical evaluation includes establishing valid clinical associations (the relationship between software output and the clinical condition), demonstrating analytical and clinical performance (accuracy, reliability, and clinical validity in the intended use environment), and assessing whether the software achieves its intended benefits without introducing unacceptable risks. Even when a physiological console is not formally regulated as SaMD, adopting IMDRF evaluation logic supports disciplined development:

- **Valid clinical association:** If the console uses HRV to infer fatigue risk, is there a validated causal or predictive relationship between the specific HRV features used and the operationally relevant endpoint (e.g., vigilance task performance, error rate, near-miss incidence)?
- **Analytical performance:** Do the HRV/sleep/circadian algorithms perform accurately under the range of real-world conditions (motion, artefact, missing data, device variability) expected in operations?
- **Clinical (operational) performance:** Does using the console improve operational safety or performance outcomes compared to not using it, or compared to simpler alternatives?

IMDRF's risk-proportionate approach also clarifies that outputs influencing critical or time-sensitive decisions demand stronger evidence than outputs used for general wellness or informational purposes.

**Good Machine Learning Practice for medical devices.** Recognizing the unique challenges of AI/ML-enabled medical devices, regulatory agencies have articulated guiding principles for Good Machine Learning Practice (GMLP). In 2021, FDA, Health Canada, and the UK MHRA jointly released 10 guiding principles emphasizing multi-disciplinary expertise throughout the product lifecycle, good software engineering and cybersecurity practices, representative training and test datasets, independence of training and test sets, use of best-available reference standards, tailored model design, focus on human-AI team performance, clinically relevant testing, clear user information, and monitoring of deployed models for performance drift and retraining risks (FDA, Health Canada, & MHRA, 2021). In January 2025, IMDRF finalized an international consensus document building on these principles (IMDRF, 2025).

For a physiological console, GMLP principles reinforce several operational design constraints:

- Training data should represent the diversity of the intended use population (e.g., age, sex, baseline fitness, occupational roles, measurement conditions).
- Test datasets must be truly independent—not just a random split of the same mission or cohort, which can introduce subtle dependencies.
- Model performance should be evaluated on the human-AI team, not the algorithm in isolation: Does the console+operator combination perform better than the operator alone?
- Deployed models should be monitored for drift: if HRV distributions, sleep patterns, or device characteristics change over time, model performance may degrade silently.

These principles apply even if the console is not formally submitted for regulatory review. They articulate best practice for any system where algorithmic outputs influence safety-critical decisions.

#### 3.11.9. Construct validity and the endpoint problem in operational physiology
A recurring challenge in operational physiology is the mismatch between what is measured and what is operationally meaningful. HRV is a measurable signal, but "stress," "fatigue," and "readiness" are latent constructs. Treating HRV as a direct proxy for these constructs—without validating that relationship in the operational context—risks reification: mistaking the measurement for the phenomenon.

**The construct validity requirement.** In psychometrics and measurement theory, construct validity refers to the degree to which a test or instrument actually measures the theoretical construct it claims to measure. For physiological monitoring, construct validity demands empirical evidence linking the measured signal (e.g., RMSSD, LF/HF, sleep duration) to the operationally relevant outcome (e.g., error rate, vigilance lapses, decision quality). This linkage is not assumed; it must be demonstrated in the population and context of use.

For a console that presents a "fatigue risk score" derived from sleep history, circadian phase, and HRV, construct validity requires showing that this score predicts objective performance decrements (e.g., PVT lapses, simulator errors, operational near-misses) in the target population, with known sensitivity, specificity, and calibration. If the score correlates with self-reported sleepiness but not with objective performance, then its operational utility is limited: self-report is cheaper and does not require the physiological instrumentation overhead.

Similarly, if an HRV-derived "stress index" does not predict performance outcomes beyond what is predicted by sleep history alone, then the added measurement burden and algorithmic complexity are not justified. The console's value proposition depends on incremental validity: each physiological feature or model should contribute unique, actionable information that improves decision-making beyond simpler inputs.

**The endpoint problem.** A related challenge is that the most operationally meaningful endpoints—mission success, error-free task completion, avoidance of serious incidents—are rare and difficult to measure prospectively in controlled studies. As a result, validation studies often substitute proxy endpoints: PVT reaction time, self-report scales, or subjective ratings of alertness. These proxies are useful for research but introduce epistemic uncertainty when translated to operational settings.

For example, a console may be validated against PVT lapses in a laboratory sleep-restriction study. PVT is a well-characterized measure of sustained attention and has known sensitivity to sleep loss. However, operational performance in high-workload, safety-critical roles involves not only sustained attention but also decision-making under uncertainty, coordination with team members, situation awareness, and adaptive problem-solving. A model that predicts PVT lapses may fail to predict operational errors if those errors are driven by factors that PVT does not capture.

This does not invalidate PVT or other proxy measures, but it does impose a responsibility on console developers and users: proxy-validated outputs should be framed as indicators of one facet of performance risk, not as comprehensive readiness assessments. The console should clearly communicate what has been validated ("this score predicts sustained attention performance in controlled settings") and what remains uncertain ("its relationship to operational error rates in the field is not yet established").

**Toward a layered validation framework.** A scientifically defensible console adopts a layered approach to validation:

1. **Measurement validity:** Do the sensors and algorithms accurately capture the intended physiological or behavioral signals (e.g., RR intervals, sleep/wake states, circadian phase)? This is assessed by comparison to gold standards (ECG, polysomnography, dim light melatonin onset).
2. **Predictive validity:** Do the features and models predict proxy outcomes (e.g., PVT performance, self-reported fatigue) in controlled studies? This establishes that the signals carry information relevant to the constructs of interest.
3. **Operational validity:** Do the console outputs improve real-world decision-making and outcomes when used in the operational environment? This is the most challenging validation tier and typically requires prospective field trials or operational pilot deployments with careful outcome tracking.

Most consoles operate somewhere between tiers 2 and 3: they have evidence of predictive validity from controlled studies but lack direct evidence of operational impact. Recognizing this, the console should be framed as a decision-support aid that provides additional context to inform operational judgment, not as a validated diagnostic or clearance system. Over time, as operational data accumulate and outcomes are tracked, the evidence base can strengthen. However, this requires a commitment to continuous evaluation, feedback loops, and honest reporting of both successes and failures—consistent with the FRMS learning-system philosophy.

### 3.12. HRV biofeedback and controlled breathing: intervention science vs measurement confounding
Because the app includes biofeedback capabilities, it is important to distinguish two roles for controlled breathing.

First, **paced breathing is a measurement confound** in HRV assessment. It can increase HF power when breathing is in the HF band, or shift respiratory-driven variability into the LF band when breathing is slowed toward ~0.1 Hz, materially altering LF, HF, and LF/HF without any necessary change in sympathetic tone. Thus, when paced breathing is used for standardization, the breathing rate must be documented and the interpretation of spectral features must be adjusted accordingly (Grossman et al., 1991).

Second, **paced breathing can be an intervention**. HRV biofeedback and resonance-frequency breathing aim to enhance baroreflex-mediated oscillations and autonomic regulation, and they have been studied across clinical and performance contexts. Reviews of HRV biofeedback describe plausible mechanistic pathways (baroreflex engagement, respiratory–cardiovascular coupling) and emphasize protocol specificity, particularly the need to individualize resonance frequency and to distinguish training effects from acute breathing-induced shifts (Lehrer & Gevirtz, 2014).

More recent quantitative syntheses strengthen the evidence base while also clarifying its limits. A systematic review and meta-analysis concluded that HRV biofeedback can improve emotional and physical health and performance outcomes across studied contexts, while highlighting heterogeneity in protocols and endpoints (Lehrer et al., 2020). Meta-analytic evidence also suggests that HRV biofeedback may reduce depressive symptoms in adult samples, again with meaningful between-study variability (Pizzoli et al., 2021). In cognition-specific outcomes, a systematic review focused on executive functions across the lifespan suggests potential benefits of HRV biofeedback, while emphasizing heterogeneity and limited study quality (Tinello et al., 2022). Importantly for operational medicine, there is now meta-analytic synthesis specifically in military PTSD populations suggesting HRV biofeedback may reduce symptomatology with low attrition, although available studies remain small and the evidence base is still developing (Kenemore et al., 2024).

For console design, these findings support a pragmatic role for biofeedback modules as structured training interventions. However, they also reinforce a separation-of-concerns requirement: the console should (i) log whether HRV was measured under paced breathing, (ii) avoid comparing paced-breathing sessions to free-breathing baselines without explicit adjustment, and (iii) avoid treating acute breathing-induced shifts as evidence of long-term autonomic change.

For an operational console, the safe synthesis is that biofeedback modules should be framed as training/skill-building tools, while analysis modules should clearly label when measurements were taken under paced-breathing conditions.

### 3.13. Brief environmental context (spaceflight): standards, human-system integration, and radiation as metadata
The app’s “mission control” framing is consistent with aerospace medicine contexts where environment and operational constraints shape physiological baselines. NASA human-system integration standards (NASA-STD-3001 Volume 2) provide a comprehensive framework for designing and evaluating human health and performance requirements across spaceflight conditions (National Aeronautics and Space Administration [NASA], 2022).

Within this review’s scope, radiation is treated only as contextual environmental metadata rather than as a radiobiological topic. The operationally relevant implication is that environmental factors (including radiation environment, cabin pressure/oxygenation, thermal load) can shift baselines and recovery trajectories; therefore, multimodal consoles should (i) capture environment metadata when available, and (ii) avoid attributing unexplained physiological deviations to a single environmental cause without stronger evidence (Yamazaki & Sone, 2001).

#### 3.13.1. Acute cardiovascular responses to microgravity: baseline shifts, not necessarily “stress”
Spaceflight introduces a set of physiological shifts (fluid redistribution, altered baroreflex loading, countermeasure exercise) that can change resting cardiovascular baselines. In-flight measurements from Shuttle astronauts show that heart rate and diastolic pressure can decrease in microgravity alongside reductions in heart rate variability and blood pressure variability, suggesting that the microgravity environment itself is not necessarily a chronic cardiovascular “stress” in the colloquial sense (Fritsch-Yelle et al., 1996). For an operational console, the key implication is that baseline shifts are expected: changes in HRV/BPV during flight should be interpreted relative to phase-of-mission baselines and countermeasure context, not compared directly to Earth baselines.

#### 3.13.2. Long-duration missions: altered HRV time structure and “intrinsic” regulation
Long-duration ISS missions enable analysis of HRV beyond short-term vagal proxies. Work examining the time structure and fractal properties of long-term HRV suggests that microgravity can alter aspects of the intrinsic cardiovascular autonomic regulatory system. For example, observational work using 24-hour ECG in astronauts reported changes in power-law scaling and related features during long-duration missions, with effects emerging early in flight and persisting (Otsuka et al., 2015). Complementary analyses report that long-term exposure to microgravity alters the time structure of HRV, implying that the distribution and temporal organization of interbeat dynamics differ in space versus on Earth (Otsuka et al., 2016).

From a mission-medicine perspective, these findings strengthen the case for longitudinal analytics: if the time structure of HRV changes with mission phase, then a “one-size-fits-all” threshold for HRV suppression is unlikely to generalize across environments.

#### 3.13.3. Circadian organization in space: synchronizers and the risk of misattribution
Spaceflight operations can perturb circadian organization through unusual light exposure, altered sleep timing, and mission demands. Evidence indicates that long-duration microgravity exposure can affect circadian rhythms of HRV, with inter-individual variability changing over flight stages and recovery occurring later in flight for some indices (Yamamoto et al., 2014). Related analyses interpret HRV spectral structure as reflecting adaptation processes across mission time, including differential patterns across the day and early sleep periods (Otsuka et al., 2018).

For a flight surgeon console, this reinforces a design constraint: circadian phase, sleep timing, and mission schedule should be treated as first-class covariates for interpreting autonomic metrics. In-flight deviations that look like “stress” on an Earth-calibrated dashboard may instead reflect altered circadian organization or environmental baseline shifts.

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

### 3.15. Hypoxia and low-oxygen environments: HRV signatures and operational interpretation
Aviation, altitude exposure, and some spaceflight-adjacent contexts can involve reduced inspired oxygen pressure (hypobaric or normobaric hypoxia), which engages chemoreflex pathways and shifts autonomic balance. From an HRV perspective, hypoxia can produce changes in both time-domain and frequency-domain measures, and it can also alter higher-order dynamics such as entropy and cardiorespiratory synchronization.

Controlled and quasi-controlled studies support that acute hypoxia perturbs multiple HRV features and coupling measures. For example, experimental work reported that acute hypoxia can alter HRV, sample entropy, and cardiorespiratory phase synchronization—highlighting that hypoxia is not merely a “heart rate increase,” but a broader dynamical perturbation (Zhang et al., 2014). In exercise-plus-hypoxia settings, studies have examined how HRV changes relate to acute mountain sickness and acclimatization processes, suggesting that autonomic markers may carry some predictive information but are not deterministic (Mairer et al., 2013). A recent meta-analysis synthesizing HRV findings in acute mountain sickness supports that some HRV parameters differ between AMS and non-AMS groups before and after ascent, but also underscores heterogeneity and the current lack of stable clinical thresholds (Tsai et al., 2025).

Field-oriented evidence underscores that operational feasibility often drives measurement design. Smartphone-enabled HRV acquisition has been studied in altitude contexts in relation to acute mountain sickness, demonstrating that short, portable HRV workflows can be collected during ascent and may relate to symptom risk (Mellor et al., 2018). Other work combining oximetry and HRV similarly suggests that multimodal approaches (SpO2 plus autonomic features) may outperform either signal alone for mild-to-moderate altitude illness classification (Koehle et al., 2010).

For a mission-medicine dashboard, the implication is not to use HRV as a standalone hypoxia detector, but to treat oxygenation state as a *confounder and covariate*. When low-oxygen exposure is plausible, the console should integrate SpO2 (or cabin/altitude metadata when available) and reduce confidence in autonomic interpretations that assume stable oxygenation.

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

**Separate calibration from evaluation.** Physiological monitoring systems routinely embed choices: which HRV metric to emphasize, which artefact threshold to use, how to define a baseline window, which covariates to adjust for, and which thresholds trigger alerts. If these choices are tuned on the same data that later evaluate “accuracy,” the system will appear better than it is. Time-series dependence exacerbates this risk because adjacent days are correlated. The solution is methodological discipline: use temporally appropriate validation (blocked or forward-chaining approaches) and separate the tuning window from the evaluation window (Bergmeir et al., 2018).

**Treat inference as conditional on protocol and metadata.** Many apparent failures of HRV monitoring are failures of protocol consistency (time-of-day, posture, breathing) rather than failures of physiology. A console that logs and enforces protocol metadata can prevent this category of error. In practice, validation should stratify by protocol adherence and quantify how much predictive value collapses when metadata is missing.

**Quantify uncertainty and error budgets.** Operational systems should not present point estimates without uncertainty qualifiers. In a console context, uncertainty is not only statistical; it is also *data-quality uncertainty* (artefact correction fraction, missingness) and *model-input uncertainty* (sleep/wake estimates from wearables). A defensible approach treats the dashboard as a system that reports (i) an estimate, (ii) a confidence score driven by data quality, and (iii) the reasons confidence is reduced.

#### 4.5.1. Validation is not one number: discrimination, calibration, subgroup performance, and drift
Prediction models are often summarized by a single performance statistic (AUC, accuracy, correlation). For a multimodal console, this practice is scientifically insufficient and operationally unsafe.

First, **discrimination is not calibration**. A classifier can rank individuals correctly (high AUC) while producing miscalibrated probability estimates that systematically overstate or understate risk. Miscalibration matters because operational decisions are threshold-based: whether to trigger additional monitoring, mandate rest, or reassign tasks depends not only on rank ordering but on the estimated magnitude of risk. In other words, if the console reports “high fatigue risk,” users will implicitly interpret that as a probability claim, even if the underlying model output is an uncalibrated score.

Second, **overall performance averages can hide dangerous subgroup failures**. Operational populations are heterogeneous: age, sex, baseline fitness, chronic conditions, and medication use can alter physiological baselines and feature distributions; measurement conditions vary with duty status and environment. A model that performs well overall may underperform in specific subgroups or contexts (e.g., older personnel, high-altitude operations, high-motion acquisition conditions). For a mission-medicine console, subgroup evaluation is not merely an equity concern; it is a safety concern because systematic underperformance in one subgroup can translate into systematic misclassification and misallocation of mitigation resources.

Third, **time is a confounder and a threat**. The validity of a model trained on last year's device firmware may decay when the vendor updates peak detection, changes sleep algorithms, or alters artifact correction defaults. Even if the physiology is stable, the measurement pipeline is not. Therefore, “validation” should not be treated as a one-time event; it should be a lifecycle commitment that includes periodic revalidation, drift monitoring, and clear versioning of both devices and analytics.

In practice, a defensible evaluation package for a console’s prediction components should include: (i) discrimination metrics; (ii) calibration assessment (calibration-in-the-large, calibration slope, and calibration plots where feasible); (iii) subgroup analyses tied to plausible physiological or operational modifiers; and (iv) temporal and site/mission-stratified performance reporting to quantify generalizability.

#### 4.5.2. Decision utility: do console outputs improve decisions, not just predictions?
Operational medicine is fundamentally decision-oriented. The relevant question is not simply “does the model predict fatigue?” but “does the model improve decisions compared with what operators already do?” This is where many physiological dashboards fail: they provide plausible-looking numbers without demonstrating that those numbers lead to better actions.

Decision curve analysis provides a formal method to evaluate whether a prediction model adds net benefit across a range of decision thresholds (Vickers & Elkin, 2006). For a flight surgeon console, the intervention triggered by an alert is often not treatment but *mitigation* (additional rest, task reallocation, increased supervision, strategic napping when feasible, or objective performance testing). The costs of mitigation are real: removing a crew member from duty may reduce mission capacity, and repeated false alarms can erode trust and induce alarm fatigue. Conversely, missing a truly impaired operator may carry a high safety cost.

DCA helps make these trade-offs explicit. It asks: given a threshold probability at which action would be taken (for example, “if estimated probability of performance impairment exceeds 20%, trigger a mitigation protocol”), does the model provide higher net benefit than simpler baselines? In physiology consoles, the simplest baselines may be schedule-only fatigue forecasts, sleep duration thresholds, or even policy-based duty limits. If adding HRV does not increase net benefit at relevant thresholds, then HRV should be treated as contextual information rather than a decision trigger.

Importantly, “utility” must be evaluated at the system level, not only at the model level. A high-performing algorithm can still reduce safety if it induces automation bias, if it is used outside validated conditions, or if it diverts attention from higher-value indicators (such as objective vigilance testing). Therefore, the strongest validation evidence for a console is not retrospective model performance but prospective evaluation of decision outcomes: whether integrating console outputs into operational workflows reduces errors, near-misses, or measurable performance decrements.

#### 4.5.3. Reporting and appraisal as governance: TRIPOD(+AI) and PROBAST(+AI) as templates for console validation
A doctoral-level critique must acknowledge that many deployed “readiness” dashboards are, in effect, unreported prediction models: they produce scores that imply a prediction about a latent state (fatigue, stress, readiness) but provide insufficient documentation to appraise validity.

TRIPOD was developed to improve transparent reporting of multivariable prediction models, specifying what should be reported so that readers can judge risk of bias and potential usefulness (Collins et al., 2015). TRIPOD+AI extends this to machine-learning-based prediction models and explicitly supersedes the original checklist for studies using AI/ML methods (Collins et al., 2024). In parallel, PROBAST provides a structured tool to assess risk of bias and applicability of prediction model studies (Wolff et al., 2019; Moons et al., 2019), and PROBAST+AI updates appraisal for modern AI/ML workflows (Moons et al., 2025).

For a mission-medicine console, these frameworks can be translated into concrete governance requirements:

- **Explicit intended use and endpoint definition.** What decision is the model intended to inform? What outcome is it supposed to predict, and on what time horizon?
- **Predictor definition stability.** Are predictors defined in a way that is stable across devices and firmware updates? Are preprocessing defaults documented and version-controlled?
- **Appropriate validation design.** Is there external validation across missions, sites, or time periods? Are validation splits truly independent, avoiding leakage via repeated measures from the same individuals?
- **Calibration and uncertainty reporting.** Are probability estimates calibrated? Are confidence intervals reported? Is uncertainty communicated in a way that supports “fail-closed” behavior when data quality is low?
- **Applicability and transportability.** Is the model appropriate for the target population and operational environment, or was it trained in a convenience sample with very different measurement conditions?

The practical implication is that console outputs should carry “model cards” in the broad sense: provenance, training context, evaluation context, known limitations, and conditions under which performance is expected to degrade. Without such documentation, the console becomes a high-dimensional generator of plausible noise rather than a defensible decision-support instrument.

#### 4.5.4. Regulatory logic as an epistemic boundary: the FDA non-device CDS criteria and interpretability requirements
Even when a platform is not marketed as a regulated medical device, regulatory guidance provides a useful epistemic boundary for safe design. The FDA’s Clinical Decision Support Software guidance clarifies the distinction between non-device CDS and device CDS functions, emphasizing clinician autonomy and the requirement that users can understand the basis for recommendations (FDA, 2022; FDA, n.d.). The FDA describes four criteria that must all be met for a CDS function to be considered non-device, including that the software does not analyze medical images/signals/patterns, is intended to support health care professionals with medical information, provides recommendations rather than directives, and provides the basis for recommendations so the professional does not primarily rely on them.

For a mission-medicine console, this logic translates into a clear design constraint: **do not present algorithmic outputs as authoritative directives unless the evidence base and oversight mechanisms match the risk.** Many dashboards inadvertently violate this principle by rendering outputs as binary “fit/unfit” labels without surfacing data quality, assumptions, or rationale. Such design encourages inappropriate reliance.

A more defensible strategy is to treat algorithmic outputs as *structured arguments* rather than verdicts. For example, rather than presenting “fatigue risk = high,” the console should present: (i) the relevant inputs (sleep opportunity, time awake, circadian phase estimate, HRV deviation); (ii) the inferential chain (which component contributes what); (iii) the uncertainty (missing data, low-quality signals); and (iv) the recommended action range (mitigation options) rather than a single mandated action.

This approach aligns with the broader theme of this review: measurement and modelling are conditional. A high-stakes console must embody that conditionality in its user interface and workflow design.

#### 4.5.5. Lifecycle monitoring and change management: from static validation to continuous safety assurance
A physiological console is not a static instrument. Its performance can change with shifts in operational tempo, changes in population characteristics, and changes in device vendors, firmware, or preprocessing pipelines. Therefore, a mature validation strategy must include continuous monitoring.

Good Machine Learning Practice guiding principles explicitly emphasize lifecycle monitoring, representative datasets, independence of training and test sets, and the importance of evaluating the performance of the human-AI team (FDA, Health Canada, & MHRA, 2021; IMDRF, 2025). For operational physiology, these principles can be operationalized as:

- **Model performance monitoring:** track calibration drift and alert-rate drift over time; investigate sudden shifts that may indicate device firmware changes or population shifts.
- **Change control:** treat model updates, preprocessing changes, and threshold changes as safety-relevant changes requiring documentation, review, and (when appropriate) revalidation.
- **Post-deployment auditing:** periodically review cases where console outputs disagreed with objective performance measures or clinical outcomes to identify systematic failure modes.
- **Human factors oversight:** evaluate how users interpret and act on console outputs, including whether the interface design induces automation bias or whether reason codes improve appropriate skepticism.

The underlying point is that “validation” is not a box to check at launch. For a flight surgeon console, validation is a living safety case: it evolves with the system, the population, and the measurement ecosystem.

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

#### 4.6.1. Reproducibility as a safety requirement: retain raw signals, enable reprocessing, and make assumptions inspectable
In high-consequence settings, reproducibility is not an academic virtue; it is a safety requirement. When a physiological console influences decisions about duty status, countermeasures, or medical evaluation, it must be possible to answer a simple after-action question: *why did the dashboard say what it said?* That question cannot be answered if only downstream summary scores are retained.

**Retain raw data at the appropriate layer.** A console should store, at minimum, the highest-fidelity representation of the measurement that is realistically available: RR intervals (with timestamps) for ECG-derived HRV, beat-quality flags or artifact classifications when available, and session metadata (posture, time-of-day, acquisition duration). When only vendor summaries are available, the console should label those as vendor-derived and treat them as less reproducible inputs. The distinction matters because many HRV metrics—especially nonlinear features—are sensitive to preprocessing and artifact correction; reprocessing from raw or near-raw data enables retrospective verification and method comparison (Tarvainen et al., 2014; Lipponen & Tarvainen, 2019).

**Treat preprocessing as part of the measurement.** In physiological analytics, preprocessing choices (artifact correction thresholds, ectopy handling, interpolation decisions, detrending) can change results materially. Therefore, preprocessing parameters should be logged and versioned alongside the outputs, not treated as hidden implementation defaults. In practice, each reported metric should be traceable to: (i) input data identifiers (device/session), (ii) preprocessing settings, and (iii) algorithm version. This is the minimum structure required to support internal reproducibility, cross-device comparability, and scientific auditability.

**Enable deterministic reanalysis and independent verification.** Operational software should strive for determinism: the same inputs and settings should produce the same outputs. Where stochastic algorithms are used (e.g., certain ML workflows), random seeds and software versions should be captured. Deterministic reanalysis matters for two reasons. First, it enables the platform to act as its own forensic instrument: investigators can re-run the pipeline to reproduce what the system displayed at the time of a decision. Second, it supports scientific improvement: when failures occur, developers can test alternative preprocessing or feature definitions on the same raw data to determine whether the error was driven by sensor artifacts, algorithm design, or an invalid inference step.

**Make assumptions visible and contestable.** A console can only be governed if its assumptions are visible. Assumption visibility includes more than algorithm transparency: it includes window definitions (“rolling 7-day baseline”), inclusion/exclusion criteria for sessions (“discard sessions with >5% corrected beats”), and how missing data are handled (“carry-forward last valid phase estimate for 24 h”). These assumptions should be user-visible at an appropriate level and also machine-loggable for later audit.

**Separate exploratory analytics from controlled inference in the data layer.** As argued earlier for space-weather overlays, dashboards tend to blur exploration and inference. A reproducible system can prevent this by encoding “analysis modes” that determine which outputs are displayed: exploratory overlays may use flexible windows and many features, whereas inference outputs must be tied to prespecified models, thresholds, and multiple-testing controls. Importantly, the audit trail should record which mode was used. This is how the console avoids retrospectively laundering exploratory findings into apparent confirmatory evidence.

**Design for longitudinal comparability across device ecosystems.** Longitudinal monitoring is central to the console concept, yet longitudinal comparability is fragile. If a vendor updates firmware and changes RR detection or sleep staging, apparent physiological trends may be instrument artifacts. Provenance logging and deterministic reprocessing mitigate this, but the deeper requirement is a stable “data contract”: a well-defined schema for what constitutes a session, a day, a sleep episode, and a valid baseline window. Without a stable data contract, the same individual can appear to drift simply because definitions drift.

In summary, reproducibility is a core part of “fail-closed” design. When the system cannot defend its outputs with traceable inputs and logged assumptions, it should reduce confidence, request remeasurement, or defer to simpler, objective checks (e.g., standardized performance tasks). This conservative stance is not anti-automation; it is how automation earns trust.

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

Chellappa, S. L. (2020). Individual differences in light sensitivity affect sleep and circadian rhythms. Sleep, 44(2). https://doi.org/10.1093/sleep/zsaa214

Costa, M. D., Davis, R. B., & Goldberger, A. L. (2017a). Heart rate fragmentation: A new approach to the analysis of cardiac interbeat interval dynamics. Frontiers in Physiology, 8. https://doi.org/10.3389/fphys.2017.00255

Dawson, D., Ian Noy, Y., Härmä, M., Åkerstedt, T., & Belenky, G. (2011). Modelling fatigue and the use of fatigue models in work settings. Accident Analysis & Prevention, 43(2), 549–564. https://doi.org/10.1016/j.aap.2009.12.030

de Zambotti, M., Cellini, N., Goldstone, A., Colrain, I. M., & Baker, F. C. (2019). Wearable sleep technology in clinical and research settings. Medicine & Science in Sports & Exercise, 51(7), 1538–1557. https://doi.org/10.1249/MSS.0000000000001947

Devine, J. K., Garcia, C. R., Simoes, A. S., Guelere, M. R., de Godoy, B., Silva, D. S., Pacheco, P. C., Choynowski, J., & Hursh, S. R. (2022). Predictive biomathematical modeling compared to objective sleep during COVID-19 humanitarian flights. Aerospace Medicine and Human Performance, 93(1), 4–12. https://doi.org/10.3357/amhp.5909.2022

European Space Agency. (n.d.). ESA Programme Documents - Space Weather. Retrieved December 21, 2025, from https://swe.ssa.esa.int/documents

European Union Aviation Safety Agency. (2023). Easy Access Rules for Air Operations (online publication). Retrieved December 21, 2025, from https://www.easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-air-operations

Federal Aviation Administration. (2013). Fatigue Risk Management Systems for Aviation Safety (Advisory Circular No. 120-103A). U.S. Department of Transportation. https://www.faa.gov/documentlibrary/media/advisory_circular/ac_120-103a.pdf

Forger, D. B., Jewett, M. E., & Kronauer, R. E. (1999). A simpler model of the human circadian pacemaker. Journal of Biological Rhythms, 14(6), 533–538. https://doi.org/10.1177/074873099129000867

Grossman, P., Karemaker, J., & Wieling, W. (1991). Prediction of tonic parasympathetic cardiac control using respiratory sinus arrhythmia: The need for respiratory control. Psychophysiology, 28(2), 201–216. https://doi.org/10.1111/j.1469-8986.1991.tb00412.x

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

Nunan, D., Sandercock, G. R. H., & Brodie, D. A. (2010). A quantitative systematic review of normal values for short-term heart rate variability in healthy adults. Pacing and Clinical Electrophysiology, 33(11), 1407–1417. https://doi.org/10.1111/j.1540-8159.2010.02841.x

Pan, J., & Tompkins, W. J. (1985). A real-time QRS detection algorithm. IEEE Transactions on Biomedical Engineering, BME-32(3), 230–236. https://doi.org/10.1109/TBME.1985.325532

Parati, G., Stergiou, G. S., Dolan, E., & Bilo, G. (2018). Blood pressure variability: Clinical relevance and application. The Journal of Clinical Hypertension, 20(7), 1133–1137. https://doi.org/10.1111/jch.13304

Peng, C.-K., Havlin, S., Stanley, H. E., & Goldberger, A. L. (1995). Quantification of scaling exponents and crossover phenomena in nonstationary heartbeat time series. Chaos: An Interdisciplinary Journal of Nonlinear Science, 5(1), 82–87. https://doi.org/10.1063/1.166141

Pincus, S. M. (1991). Approximate entropy as a measure of system complexity. Proceedings of the National Academy of Sciences, 88(6), 2297–2301. https://doi.org/10.1073/pnas.88.6.2297

Richman, J. S., & Moorman, J. R. (2000). Physiological time-series analysis using approximate entropy and sample entropy. American Journal of Physiology-Heart and Circulatory Physiology, 278(6), H2039–H2049. https://doi.org/10.1152/ajpheart.2000.278.6.h2039

Rothwell, P. M., Howard, S. C., Dolan, E., O’Brien, E., Dobson, J. E., Dahlöf, B., Sever, P. S., & Poulter, N. R. (2010). Prognostic significance of visit-to-visit variability, maximum systolic blood pressure, and episodic hypertension. The Lancet, 375(9718), 895–905. https://doi.org/10.1016/S0140-6736(10)60308-X

Schaffarczyk, M., Rogers, B., Reer, R., & Gronwald, T. (2022). Validity of the Polar H10 sensor for heart rate variability analysis during resting state and incremental exercise in recreational men and women. Sensors, 22(17), 6536. https://doi.org/10.3390/s22176536

Schäfer, A., & Vagedes, J. (2013). How accurate is pulse rate variability as an estimate of heart rate variability? International Journal of Cardiology, 166(1), 15–29. https://doi.org/10.1016/j.ijcard.2012.03.119

Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability metrics and norms. Frontiers in Public Health, 5, 258. https://doi.org/10.3389/fpubh.2017.00258

Shields, R. W. (2009). Heart rate variability with deep breathing as a clinical test of cardiovagal function. Cleveland Clinic Journal of Medicine, 76(4 suppl 2), S37–S40. https://doi.org/10.3949/ccjm.76.s2.08

St Hilaire, M. A., Gooley, J. J., Khalsa, S. B. S., Kronauer, R. E., Czeisler, C. A., & Lockley, S. W. (2012). Human phase response curve to a 1 h pulse of bright white light. The Journal of Physiology, 590(13), 3035–3045. https://doi.org/10.1113/jphysiol.2012.227892

Sundkvist, G., Lilja, B., & Almér, L.-O. (1982). Deep breathing, Valsalva, and tilt table tests in diabetics with and without symptoms of autonomic neuropathy. Acta Medica Scandinavica, 211(5), 369–373. https://doi.org/10.1111/j.0954-6820.1982.tb01964.x

Tarvainen, M. P., Niskanen, J.-P., Lipponen, J. A., Ranta-aho, P. O., & Karjalainen, P. A. (2014). Kubios HRV – Heart rate variability analysis software. Computer Methods and Programs in Biomedicine, 113(1), 210–220. https://doi.org/10.1016/j.cmpb.2013.07.024

Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology. (1996). Heart rate variability: Standards of measurement, physiological interpretation, and clinical use. Circulation, 93(5), 1043–1065. https://doi.org/10.1161/01.CIR.93.5.1043

Van Dongen, H. P. A., Maislin, G., Mullington, J. M., & Dinges, D. F. (2003). The cumulative cost of additional wakefulness: Dose-response effects on neurobehavioral functions and sleep physiology from chronic sleep restriction and total sleep deprivation. Sleep, 26(2), 117–126. https://doi.org/10.1093/sleep/26.2.117

Vieira, C. L. Z., Chen, K., Garshick, E., Liu, M., Vokonas, P., Ljungman, P., Schwartz, J., & Koutrakis, P. (2022). Geomagnetic disturbances reduce heart rate variability in the Normative Aging Study. Science of The Total Environment, 839, 156235. https://doi.org/10.1016/j.scitotenv.2022.156235

Welch, P. (1967). The use of fast Fourier transform for the estimation of power spectra: A method based on time averaging over short, modified periodograms. IEEE Transactions on Audio and Electroacoustics, 15(2), 70–73. https://doi.org/10.1109/TAU.1967.1161901

Yamazaki, F., & Sone, R. (2001). Thermal stress modulates arterial pressure variability and arterial baroreflex response of heart rate during head-up tilt in humans. European Journal of Applied Physiology, 84(4), 350–357. https://doi.org/10.1007/s004210100387

Yamamoto, N., Otsuka, K., Kubo, Y., Hayashi, M., Mizuno, K., Ohshima, H., & Mukai, C. (2014). Effects of long-term microgravity exposure in space on circadian rhythms of heart rate variability. Chronobiology International, 32(3), 327–340. https://doi.org/10.3109/07420528.2014.979940

AlArnaout, Z., Zaki, C., Kotb, Y., AlAkkoumi, M., & Mostafa, N. (2025). Exploiting heart rate variability for driver drowsiness detection using wearable sensors and machine learning. Scientific Reports, 15(1). https://doi.org/10.1038/s41598-025-08582-2

Alugubelli, N., Abuissa, H., & Roka, A. (2022). Wearable devices for remote monitoring of heart rate and heart rate variability: What we know and what is coming. Sensors, 22(22), 8903. https://doi.org/10.3390/s22228903

Babu, S. G., Chandrashekar, P., Manjunath, N. K., Tran, P., & Shetty, D. K. (2024). Wearable devices in precision medicine: Translating innovations to clinic. Annual Review of Medicine, 75, 435–452. https://doi.org/10.1146/annurev-med-052422-020437

Boudreau, P., Yeh, W.-H., Dumont, G. A., & Boivin, D. B. (2013). Circadian variation of heart rate variability across sleep stages. Sleep, 36(12), 1919–1928. https://doi.org/10.5665/sleep.3230

Chen, Y.-S., Lu, W.-A., Pagaduan, J. C., & Kuo, C.-D. (2020). A novel smartphone app for the measurement of ultra–short-term and short-term heart rate variability: Validity and reliability study. JMIR mHealth and uHealth, 8(7), e18761. https://doi.org/10.2196/18761

Flatt, A. A., & Esco, M. R. (2013). Validity of the ithlete™ smart phone application for determining ultra-short-term heart rate variability. Journal of Human Kinetics, 39, 85–92. https://doi.org/10.2478/hukin-2013-0071

Fritsch-Yelle, J. M., Charles, J. B., Jones, M. M., Beightol, L. A., & Eckberg, D. L. (1996). Microgravity decreases heart rate and arterial pressure in humans. Journal of Applied Physiology, 80(3), 910–914. https://doi.org/10.1152/jappl.1996.80.3.910

Jennings, J. R., Allen, B., Gianaros, P. J., Thayer, J. F., & Manuck, S. B. (2014). Focusing neurovisceral integration: Cognition, heart rate variability, and cerebral blood flow. Psychophysiology, 52(2), 214–224. https://doi.org/10.1111/psyp.12319

Kenemore, J., Benham, G., Charak, R., & Hernandez Rodriguez, J. (2024). Heart rate variability biofeedback as a treatment for military PTSD: A meta-analysis. Military Medicine, 189(9–10), e1903–e1909. https://doi.org/10.1093/milmed/usae003

Koehle, M. S., Guenette, J. A., & Warburton, D. E. R. (2010). Oximetry, heart rate variability, and the diagnosis of mild-to-moderate acute mountain sickness. European Journal of Emergency Medicine, 17(2), 119–122. https://doi.org/10.1097/mej.0b013e32832fa099

Lehrer, P., Kaur, K., Sharma, A., Shah, K., Huseby, R., Bhavsar, J., Sgobba, P., & Zhang, Y. (2020). Heart rate variability biofeedback improves emotional and physical health and performance: A systematic review and meta analysis. Applied Psychophysiology and Biofeedback, 45(3), 109–129. https://doi.org/10.1007/s10484-020-09466-z

Mairer, K., Wille, M., Grander, W., & Burtscher, M. (2013). Effects of exercise and hypoxia on heart rate variability and acute mountain sickness. International Journal of Sports Medicine, 34(8), 700–706. https://doi.org/10.1055/s-0032-1327577

Mellor, A., Bakker-Dyos, J., O’Hara, J., Woods, D. R., Holdsworth, D. A., & Boos, C. J. (2018). Smartphone-enabled heart rate variability and acute mountain sickness. Clinical Journal of Sport Medicine, 28(1), 76–81. https://doi.org/10.1097/jsm.0000000000000427

Mishra, T., Wang, M., Metwally, A. A., Bogu, G. K., Brooks, A. W., Bahmani, A., Alavi, A., Celli, A., Higgs, E., Dagan-Rosenfeld, O., Fay, B., Kirkpatrick, S., Kellogg, R., Gibson, M., Wang, T., Hunting, E. M., Mamic, P., Ganz, A. B., Rolnik, B., Li, X., & Snyder, M. P. (2020). Pre-symptomatic detection of COVID-19 from smartwatch data. Nature Biomedical Engineering, 4(12), 1208–1220. https://doi.org/10.1038/s41551-020-00640-6

Otsuka, K., Cornelissen, G., Kubo, Y., Hayashi, M., Yamamoto, N., Shibata, K., Aiba, T., Furukawa, S., Ohshima, H., & Mukai, C. (2015). Intrinsic cardiovascular autonomic regulatory system of astronauts exposed long-term to microgravity in space: observational study. npj Microgravity, 1(1), 15018. https://doi.org/10.1038/npjmgrav.2015.18

Otsuka, K., Cornelissen, G., Furukawa, S., Kubo, Y., Hayashi, M., Shibata, K., Mizuno, K., Aiba, T., Ohshima, H., & Mukai, C. (2016). Long-term exposure to space’s microgravity alters the time structure of heart rate variability of astronauts. Heliyon, 2(12), e00211. https://doi.org/10.1016/j.heliyon.2016.e00211

Otsuka, K., Cornelissen, G., Kubo, Y., Shibata, K., Hayashi, M., Mizuno, K., Ohshima, H., Furukawa, S., & Mukai, C. (2018). Circadian challenge of astronauts’ unconscious mind adapting to microgravity in space, estimated by heart rate variability. Scientific Reports, 8(1). https://doi.org/10.1038/s41598-018-28740-z

Pizzoli, S. F. M., Marzorati, C., Gatti, D., Monzani, D., Mazzocco, K., & Pravettoni, G. (2021). A meta-analysis on heart rate variability biofeedback and depressive symptoms. Scientific Reports, 11(1). https://doi.org/10.1038/s41598-021-86149-7

Smith, R., Thayer, J. F., Khalsa, S. S., & Lane, R. D. (2017). The hierarchical basis of neurovisceral integration. Neuroscience & Biobehavioral Reviews, 75, 274–296. https://doi.org/10.1016/j.neubiorev.2017.02.003

Thayer, J. F., & Lane, R. D. (2000). A model of neurovisceral integration in emotion regulation and dysregulation. Journal of Affective Disorders, 61(3), 201–216. https://doi.org/10.1016/S0165-0327(00)00338-4

Thayer, J. F., & Lane, R. D. (2009). Claude Bernard and the heart–brain connection: Further elaboration of a model of neurovisceral integration. Neuroscience & Biobehavioral Reviews, 33(2), 81–88. https://doi.org/10.1016/j.neubiorev.2008.08.004

Thayer, J. F., Hansen, A. L., Saus-Rose, E., & Johnsen, B. H. (2009). Heart rate variability, prefrontal neural function, and cognitive performance: The neurovisceral integration perspective on self-regulation, adaptation, and health. Annals of Behavioral Medicine, 37(2), 141–153. https://doi.org/10.1007/s12160-009-9101-z

Tsai, T.-Y., Lin, J.-X., Ou, J.-C., & Huang, T.-Y. (2025). The role of heart rate variability in acute mountain sickness: A meta-analysis. Medicine, 104(24), e42692. https://doi.org/10.1097/md.0000000000042692

Thuraisingham, R. A. (2006). Preprocessing RR interval time series for heart rate variability analysis and estimates of standard deviation of RR intervals. Computer Methods and Programs in Biomedicine, 83(1), 78–82. https://doi.org/10.1016/j.cmpb.2006.05.002

Zhang, C., Lan, J., Shi, Y., Gao, R., Li, C., Lu, M., & Wang, L. (2014). Effect of acute hypoxia on heart rate variability, sample entropy and cardiorespiratory phase synchronization. BioMedical Engineering OnLine, 13(1), 73. https://doi.org/10.1186/1475-925x-13-73

Delliaux, S., Delaforge, A., Deharo, J.-C., & Chaumet, G. (2019). Mental workload alters heart rate variability, lowering non-linear dynamics. Frontiers in Physiology, 10, 565. https://doi.org/10.3389/fphys.2019.00565

Forte, G., Favieri, F., & Casagrande, M. (2019). Heart rate variability and cognitive function: A systematic review. Frontiers in Neuroscience, 13, 710. https://doi.org/10.3389/fnins.2019.00710

Lomb, N. R. (1976). Least-squares frequency analysis of unequally spaced data. Astrophysics and Space Science, 39, 447–462. https://doi.org/10.1007/BF00648343

Magnon, V., Vallet, G. T., Benson, A., Mermillod, M., Chausse, P., Lacroix, A., Bouillon-Minois, J.-B., & Dutheil, F. (2022). Does heart rate variability predict better executive functioning? A systematic review and meta-analysis. Cortex, 155, 218–236. https://doi.org/10.1016/j.cortex.2022.07.008

Nicolini, P., Malfatto, G., & Lucchi, T. (2024). Heart rate variability and cognition: A narrative systematic review of longitudinal studies. Journal of Clinical Medicine, 13(1), 280. https://doi.org/10.3390/jcm13010280

Cheng, Y.-C., Huang, Y.-C., & Huang, W.-L. (2022). Heart rate variability in patients with dementia or neurocognitive disorders: A systematic review and meta-analysis. The Australian and New Zealand Journal of Psychiatry, 56(1), 16–27. https://doi.org/10.1177/0004867420976853

Liu, K. Y., Elliott, T., Knowles, M., & Howard, R. (2022). Heart rate variability in relation to cognition and behavior in neurodegenerative diseases: A systematic review and meta-analysis. Ageing Research Reviews, 73, 101539. https://doi.org/10.1016/j.arr.2021.101539

Allan, L. M., Kerr, S. R. J., Ballard, C. G., Allen, J., Murray, A., McLaren, A. T., & Kenny, R. A. (2005). Autonomic function assessed by heart rate variability is normal in Alzheimer’s disease and vascular dementia. Dementia and Geriatric Cognitive Disorders, 19(2–3), 140–144. https://doi.org/10.1159/000082885

Scargle, J. D. (1982). Studies in astronomical time series analysis. II - Statistical aspects of spectral analysis of unevenly spaced data. The Astrophysical Journal, 263, 835–853. https://doi.org/10.1086/160554

Tinello, D., Kliegel, M., & Zuber, S. (2022). Does heart rate variability biofeedback enhance executive functions across the lifespan? A systematic review. Journal of Cognitive Enhancement, 6(1), 126–142. https://doi.org/10.1007/s41465-021-00218-3

Arksey, H., & O’Malley, L. (2005). Scoping studies: towards a methodological framework. International Journal of Social Research Methodology, 8(1), 19–32. https://doi.org/10.1080/1364557032000119616

Levac, D., Colquhoun, H., & O’Brien, K. K. (2010). Scoping studies: advancing the methodology. Implementation Science, 5, 69. https://doi.org/10.1186/1748-5908-5-69

Munn, Z., Peters, M. D. J., Stern, C., Tufanaru, C., McArthur, A., & Aromataris, E. (2018). Systematic review or scoping review? Guidance for authors when choosing between a systematic or scoping review approach. BMC Medical Research Methodology, 18(1), 143. https://doi.org/10.1186/s12874-018-0611-x

Peters, M. D. J., Marnie, C., Tricco, A. C., Pollock, D., Munn, Z., Alexander, L., McInerney, P., Godfrey, C. M., & Khalil, H. (2020). Updated methodological guidance for the conduct of scoping reviews. JBI Evidence Synthesis, 18(10), 2119–2126. https://doi.org/10.11124/JBIES-20-00167

Tricco, A. C., Lillie, E., Zarin, W., O’Brien, K. K., Colquhoun, H., Levac, D., Moher, D., Peters, M. D. J., Horsley, T., Weeks, L., Hempel, S., Akl, E. A., Chang, C., McGowan, J., Stewart, L., et al. (2018). PRISMA Extension for Scoping Reviews (PRISMA-ScR): Checklist and Explanation. Annals of Internal Medicine, 169(7), 467–473. https://doi.org/10.7326/M18-0850

Chan, J. F., & Andersen, J. P. (2025). Heart Rate Fragmentation: A Novel Analytic Approach to Detect Allostatic Load Among Healthy Adults. Applied Psychophysiology and Biofeedback. https://doi.org/10.1007/s10484-025-09721-1

Corrigan, S. L., Roberts, S., Warmington, S., Drain, J., & Main, L. C. (2021). Monitoring stress and allostatic load in first responders and tactical operators using heart rate variability: a systematic review. BMC Public Health, 21(1). https://doi.org/10.1186/s12889-021-11595-x

Costa, M. D., Davis, R. B., & Goldberger, A. L. (2017b). Heart Rate Fragmentation: A Symbolic Dynamical Approach. Frontiers in Physiology, 8, 827. https://doi.org/10.3389/fphys.2017.00827

Costa, M. D., Redline, S., Davis, R. B., Heckbert, S. R., Soliman, E. Z., & Goldberger, A. L. (2018). Heart Rate Fragmentation as a Novel Biomarker of Adverse Cardiovascular Events: The Multi-Ethnic Study of Atherosclerosis. Frontiers in Physiology, 9, 1117. https://doi.org/10.3389/fphys.2018.01117

Costa, M. D., & Goldberger, A. L. (2019). Heart rate fragmentation: using cardiac pacemaker dynamics to probe the pace of biological aging. American Journal of Physiology-Heart and Circulatory Physiology. https://doi.org/10.1152/ajpheart.00110.2019

Costa, M. D., Redline, S., Soliman, E. Z., Goldberger, A. L., & Heckbert, S. R. (2021a). Fragmented sinoatrial dynamics in the prediction of atrial fibrillation: the Multi-Ethnic Study of Atherosclerosis. American Journal of Physiology-Heart and Circulatory Physiology. https://doi.org/10.1152/ajpheart.00421.2020

Costa, M. D., Redline, S., Hughes, T. M., Heckbert, S. R., & Goldberger, A. L. (2021b). Prediction of Cognitive Decline Using Heart Rate Fragmentation Analysis: The Multi-Ethnic Study of Atherosclerosis. Frontiers in Aging Neuroscience, 13, 708130. https://doi.org/10.3389/fnagi.2021.708130

Costa, M. D., Heckbert, S. R., Redline, S., & Goldberger, A. L. (2022). Method to quantify the impact of sleep on cardiac neuroautonomic functionality: application to the prediction of cardiovascular events in the Multi-Ethnic Study of Atherosclerosis. American Journal of Physiology-Regulatory, Integrative and Comparative Physiology. https://doi.org/10.1152/ajpregu.00184.2022

Guichard, J.-B., Hupin, D., Pichot, V., Berger, M., Celle, S., Borràs, R., Roca-Luque, I., Mont, L., Da Costa, A., Barthélémy, J.-C., & Roche, F. (2025). Assessing heart rate fragmentation to predict atrial fibrillation in the general population aged 65: the PROOF-AF study. European Heart Journal Open, 5(3). https://doi.org/10.1093/ehjopen/oeaf030

Hayano, J., Kisohara, M., Ueda, N., & Yuda, E. (2020). Impact of Heart Rate Fragmentation on the Assessment of Heart Rate Variability. Applied Sciences, 10(9), 3314. https://doi.org/10.3390/app10093314

Heckbert, S. R., Jensen, P. N., Erus, G., Nasrallah, I. M., Rashid, T., Habes, M., Austin, T. R., Floyd, J. S., Schaich, C. L., Redline, S., Bryan, R. N., & Costa, M. D. (2024). Heart rate fragmentation and brain MRI markers of small vessel disease in MESA. Alzheimer's & Dementia. https://doi.org/10.1002/alz.13554

Lensen, I. S., Monfredi, O. J., Andris, R. T., Lake, D. E., & Moorman, J. R. (2020). Heart rate fragmentation gives novel insights into non-autonomic mechanisms governing beat-to-beat control of the heart’s rhythm. JRSM Cardiovascular Disease, 9. https://doi.org/10.1177/2048004020948732

Saleem, S., Khandoker, A., Alkhodari, M., Hadjileontiadis, L., & Jelinek, H. F. (2022). A two-step pre-processing tool to remove Gaussian and ectopic noise for heart rate variability analysis. Scientific Reports, 12(1). https://doi.org/10.1038/s41598-022-21776-2

Collins, G. S., Reitsma, J. B., Altman, D. G., & Moons, K. G. M. (2015). Transparent Reporting of a multivariable prediction model for Individual Prognosis Or Diagnosis (TRIPOD): The TRIPOD Statement. Annals of Internal Medicine, 162(1), 55–63. https://doi.org/10.7326/M14-0697

Collins, G. S., Moons, K. G. M., Dhiman, P., Riley, R. D., Beam, A. L., Van Calster, B., Ghassemi, M., Liu, X., Reitsma, J. B., van Smeden, M., Boulesteix, A.-L., Camaradou, J.-C., Celi, L. A., Denaxas, S., Denniston, A. K., Glocker, B., Golub, R. M., Harvey, H., Heinze, G., Hoffman, M. M., Kengne, A.-P., Lam, E., Lee, N., Loder, E. W., Maier-Hein, L., Mateen, B. A., McCradden, M. D., Oakden-Rayner, L., Ordish, J., Parnell, R., Rose, S., Singh, K., Wynants, L., & Logullo, P. (2024). TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. BMJ. https://doi.org/10.1136/bmj-2023-078378

International Medical Device Regulators Forum. (2017). Software as a Medical Device (SaMD): Clinical Evaluation (IMDRF/SaMD WG/N41FINAL:2017). Retrieved December 23, 2025, from https://www.imdrf.org/sites/default/files/docs/imdrf/final/technical/imdrf-tech-170921-samd-n41-clinical-evaluation_1.pdf

International Medical Device Regulators Forum. (2025). Good machine learning practice for medical device development: Guiding principles (IMDRF/AIML WG/N88 FINAL:2025). Retrieved December 23, 2025, from https://www.imdrf.org/sites/default/files/2025-01/IMDRF_AIML%20WG_GMLP_N88%20Final_0.pdf

Moons, K. G. M., Wolff, R. F., Riley, R. D., Whiting, P. F., Westwood, M., Collins, G. S., Reitsma, J. B., Kleijnen, J., & Mallett, S. (2019). PROBAST: A Tool to Assess Risk of Bias and Applicability of Prediction Model Studies: Explanation and Elaboration. Annals of Internal Medicine, 170(1), W1–W33. https://doi.org/10.7326/M18-1377

Moons, K. G. M., Damen, J. A. A., Kaul, T., Hooft, L., Andaur Navarro, C., Dhiman, P., Beam, A. L., Van Calster, B., Celi, L. A., Denaxas, S., Denniston, A. K., Ghassemi, M., Heinze, G., Kengne, A.-P., Maier-Hein, L., Liu, X., Logullo, P., McCradden, M. D., Liu, N., Oakden-Rayner, L., Singh, K., Ting, D. S., Wynants, L., Yang, B., Reitsma, J. B., Riley, R. D., Collins, G. S., & van Smeden, M. (2025). PROBAST+AI: an updated quality, risk of bias, and applicability assessment tool for prediction models using regression or artificial intelligence methods. BMJ. https://doi.org/10.1136/bmj-2024-082505

U.S. Food and Drug Administration. (2022). Clinical Decision Support Software: Guidance for Industry and Food and Drug Administration Staff. Retrieved December 23, 2025, from https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software

U.S. Food and Drug Administration. (n.d.). Clinical Decision Support Software Frequently Asked Questions (FAQs). Retrieved December 23, 2025, from https://www.fda.gov/medical-devices/software-medical-device-samd/clinical-decision-support-software-frequently-asked-questions-faqs

U.S. Food and Drug Administration, Health Canada, & Medicines and Healthcare products Regulatory Agency. (2021). Good Machine Learning Practice for Medical Device Development: Guiding Principles. Retrieved December 23, 2025, from https://www.canada.ca/en/health-canada/services/drugs-health-products/medical-devices/good-machine-learning-practice-medical-device-development.html

Vickers, A. J., & Elkin, E. B. (2006). Decision curve analysis: a novel method for evaluating prediction models. Medical Decision Making, 26(6), 565–574. https://doi.org/10.1177/0272989X06295361

Wolff, R. F., Moons, K. G. M., Riley, R. D., Whiting, P. F., Westwood, M., Collins, G. S., Reitsma, J. B., Kleijnen, J., & Mallett, S. (2019). PROBAST: A Tool to Assess the Risk of Bias and Applicability of Prediction Model Studies. Annals of Internal Medicine, 170(1), 51–58. https://doi.org/10.7326/M18-1376

---

## Appendix A. Pilot Europe PMC search strategy for the HRV–cognition scoping component (higher sensitivity)
**Search date:** 22 December 2025

**Note:** This pilot strategy was used to assess sensitivity and inform refinement of the final query set reported in Appendix B.

**Data source:** Europe PMC REST API (`https://www.ebi.ac.uk/europepmc/webservices/rest/search`)

**Core settings:** `format=json`, `resultType=lite`, `pageSize=1000`, `cursorMark=*`

**Deduplication rule:** case-insensitive DOI when available; otherwise PMID; otherwise source-specific record identifier.

### A.1. Query families (verbatim)
**Executive function**
`TITLE_ABS:(rmssd OR "hf-hrv" OR "high frequency heart rate variability" OR "vagally mediated" OR "cardiac vagal" OR "cardiac vagal control") AND TITLE_ABS:("executive function" OR inhibition OR shifting OR updating OR stroop OR flanker OR "go/no-go" OR "cognitive control") AND HAS_ABSTRACT:Y AND LANG:eng AND (FIRST_PDATE:[2000-01-01 TO 2025-12-31])`

**Working memory**
`TITLE_ABS:(rmssd OR "hf-hrv" OR "high frequency heart rate variability" OR "vagally mediated" OR "cardiac vagal" OR "cardiac vagal control") AND TITLE_ABS:("working memory" OR "n-back" OR "digit span" OR "short-term memory") AND HAS_ABSTRACT:Y AND LANG:eng AND (FIRST_PDATE:[2000-01-01 TO 2025-12-31])`

**Attention / vigilance**
`TITLE_ABS:(rmssd OR "hf-hrv" OR "high frequency heart rate variability" OR "vagally mediated" OR "cardiac vagal" OR "cardiac vagal control") AND TITLE_ABS:(attention OR vigilance OR "psychomotor vigilance" OR PVT OR "sustained attention" OR "reaction time") AND HAS_ABSTRACT:Y AND LANG:eng AND (FIRST_PDATE:[2000-01-01 TO 2025-12-31])`

**Mental workload / cognitive load**
`TITLE_ABS:(rmssd OR "hf-hrv" OR "high frequency heart rate variability" OR "vagally mediated" OR "cardiac vagal" OR "cardiac vagal control") AND TITLE_ABS:("mental workload" OR workload OR "cognitive load" OR "NASA-TLX") AND HAS_ABSTRACT:Y AND LANG:eng AND (FIRST_PDATE:[2000-01-01 TO 2025-12-31])`

**Cognitive impairment / dementia**
`TITLE_ABS:("heart rate variability" OR rmssd OR "hf-hrv" OR "cardiac vagal") AND TITLE_ABS:(dementia OR alzheimer* OR "mild cognitive impairment" OR MCI) AND HAS_ABSTRACT:Y AND LANG:eng AND (FIRST_PDATE:[2000-01-01 TO 2025-12-31])`

### A.2. Reproducible record counts (as retrieved on 22 December 2025)
- Records identified (sum across query families): 2,571
- Duplicates removed (DOI/PMID rule): 577
- Unique records mapped: 1,994
- Unique records without a DOI: 49

**Query-family yields (not mutually exclusive due to overlap):** executive function (896), working memory (256), attention/vigilance (835), mental workload (265), cognitive impairment (319)

---

## Appendix B. Final Europe PMC search strategy for the HRV–cognition scoping component (higher precision)
**Search date:** 22 December 2025

**Data source:** Europe PMC REST API (`https://www.ebi.ac.uk/europepmc/webservices/rest/search`)

**Core settings:** `format=json`, `resultType=lite`, `pageSize=1000`, `cursorMark=*`

**Deduplication rule:** case-insensitive DOI when available; otherwise PMID; otherwise source-specific record identifier.

### B.1. Query families (verbatim)
**Executive function**
`TITLE_ABS:("heart rate variability" OR rmssd OR sdnn OR "hf-hrv" OR "rr interval" OR "nn interval") AND TITLE_ABS:("executive function" OR "cognitive control" OR "inhibitory control" OR "task switching" OR "set shifting" OR stroop OR flanker OR "go/no-go" OR "go no go") AND HAS_ABSTRACT:Y AND LANG:eng AND (FIRST_PDATE:[2000-01-01 TO 2025-12-31])`

**Working memory**
`TITLE_ABS:("heart rate variability" OR rmssd OR sdnn OR "hf-hrv" OR "rr interval" OR "nn interval") AND TITLE_ABS:("working memory" OR "n-back" OR "digit span") AND HAS_ABSTRACT:Y AND LANG:eng AND (FIRST_PDATE:[2000-01-01 TO 2025-12-31])`

**Attention / vigilance**
`TITLE_ABS:("heart rate variability" OR rmssd OR sdnn OR "hf-hrv" OR "rr interval" OR "nn interval") AND TITLE_ABS:("psychomotor vigilance" OR PVT OR vigilance OR "sustained attention" OR "continuous performance test" OR CPT) AND HAS_ABSTRACT:Y AND LANG:eng AND (FIRST_PDATE:[2000-01-01 TO 2025-12-31])`

**Note:** The token “CPT” is ambiguous (continuous performance test vs cold pressor test). Records with “cold pressor” in title/abstract were excluded during screening (Section 2.5).

**Mental workload / cognitive load**
`TITLE_ABS:("heart rate variability" OR rmssd OR sdnn OR "hf-hrv" OR "rr interval" OR "nn interval") AND TITLE_ABS:("mental workload" OR "cognitive load" OR "NASA-TLX") AND HAS_ABSTRACT:Y AND LANG:eng AND (FIRST_PDATE:[2000-01-01 TO 2025-12-31])`

**Cognitive impairment / dementia**
`TITLE_ABS:("heart rate variability" OR rmssd OR sdnn OR "hf-hrv") AND TITLE_ABS:("cognitive impairment" OR "mild cognitive impairment" OR dementia OR alzheimer* OR "cognitive decline") AND HAS_ABSTRACT:Y AND LANG:eng AND (FIRST_PDATE:[2000-01-01 TO 2025-12-31])`

### B.2. Reproducible record counts (as retrieved on 22 December 2025)
- Records identified (sum across query families): 2,736
- Duplicates removed (DOI/PMID rule): 646
- Unique records mapped: 2,090
- Unique records without a DOI: 58

**Query-family yields (not mutually exclusive due to overlap):** executive function (946), working memory (331), attention/vigilance (496), mental workload (504), cognitive impairment (459)
