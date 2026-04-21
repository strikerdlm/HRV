# Author: Dr Diego Malpica MD

## Title

**Task-calibrated Operational Performance Indicators for aviation and unmanned aircraft system operators: a biomathematical framework integrating SAFTE fatigue, heart-rate variability, and cognitive-load theory, with open-source reference implementation**

**Running title:** Task-calibrated OPI for aerospace operators

**Target venue:** Applied Ergonomics (Elsevier)

---

## Structured Abstract

### Background and objective

Operator-state monitoring in aviation and unmanned aircraft system (UAS) operations increasingly combines physiological signals, biomathematical fatigue models, and subjective workload ratings, but no published framework integrates these components into a task-calibrated composite readiness index with per-task weight profiles, an explicit taxonomy covering both manned aviation and UAS operators, and an open-source reference implementation. This manuscript introduces the **Operational Performance Indicator (OPI)** framework and its reference implementation and reports engineering verification and a single illustrative worked example.

### Methods

The OPI combines four biomathematical components: SAFTE-style reservoir fatigue effectiveness, heart-rate-variability (HRV) derived autonomic markers, task-specific cognitive-load modifiers derived from Multiple Resource Theory, and environmental/operational modifiers. Per-task weight profiles and thresholds are specified for ten manned-aviation task categories (including instrument flight, night-vision operations, helmet-mounted-display flying, high-density air-traffic control, emergencies, test-pilot operations, carrier landing, weapons delivery, and new-platform testing) and seven UAS/teleoperator categories (including intelligence-surveillance-reconnaissance, strike, search-and-rescue, supervisory swarm control, contested-environment operations, and ground and subsea teleoperation). A Warm-type vigilance-decrement function and a Chen-type logarithmic control-latency penalty are included for the UAS subset. The reference implementation is open-source (MIT license) and delivered through a Next.js client over a FastAPI orchestration layer and a shared Python biomathematical backend. A single 128-minute HRV recording is used as an illustrative framework-instantiation example across three task hypotheses.

### Results

The reference implementation instantiates the framework end-to-end. Engineering verification covers readiness fusion, fatigue-risk-management behaviour, and API orchestration across the OPI pathway. The worked example demonstrates that an identical physiological input yields substantively different composite readiness outputs when the active task category changes, consistent with the MRT-derived weight profile design intent. Reproducibility is supported by open-source code, a structured export layer, and a documented execution environment.

### Conclusions

The OPI framework offers a theoretically grounded, task-calibrated alternative to machine-learning-only operator-state classifiers and to fatigue-only or HRV-only composites. The present contribution is bounded to framework definition, reference implementation, and illustrative demonstration; external calibration of per-task weights against field operator-performance data and multi-subject validation are stated as the next research steps.

### Keywords

heart rate variability; SAFTE; fatigue risk management; Multiple Resource Theory; operator readiness; aviation human factors; unmanned aircraft systems; teleoperation; biomathematical modelling; open-source software

---

## 1. Introduction

### 1.1 Operator state and the limits of current monitoring approaches

Aviation and unmanned aircraft system (UAS) operations increasingly rely on physiological, behavioural, and schedule information to infer operator state and inform mission-level decisions. Heart-rate variability (HRV) is now a routine analytic layer in studies of workload, fatigue, and vigilance in safety-critical domains (Shaffer & Ginsberg, 2017; Quigley et al., 2024). Biomathematical fatigue modelling has matured from early pacemaker formulations to operational scheduling tools such as the Fatigue Avoidance Scheduling Tool built on the SAFTE model (Forger, Jewett, & Kronauer, 1999; Hursh, Balkin, Miller, & Eddy, 2004; Devine et al., 2022). Subjective workload ratings and task-batteries such as MATB remain widely used to elicit and benchmark physiological responses (Pontiggia et al., 2024). Recent reviews document an active literature on wearable psychophysiological sensing in safety-critical environments (Houghton, Martinetti, & Majumdar, 2024) and on machine-learning classifiers for cognitive-state recognition across aviation and other high-stakes domains (Jin et al., 2025).

Despite this activity, three recurring structural limitations affect how operator-state information is used in practice. First, most published frameworks rely on a single information channel: HRV-only analyses, SAFTE-only fatigue forecasts, or electroencephalography-only workload classifiers (Hamann et al., 2026). Second, task-specific calibration is rare; the few composite studies that exist tend to be constrained to a narrow task slice such as cruise-approach-landing phases of a single aircraft type (Feng, Wanyan, Yang, Zhuang, & Wu, 2018). Third, the recent wave of machine-learning classifiers for operator state (Stevens, Morris, Fisher, & Myers, 2022; Vogl, O'Brien, & St. Onge, 2025; Li, Molloy, El-Fiqi, & Eves, 2025) demonstrates high classification accuracy on the tasks they evaluate, but black-box classifiers are difficult to audit, transfer across platforms, and modify when new task categories appear.

### 1.2 Multiple Resource Theory and biomathematical readiness components

Multiple Resource Theory (MRT) provides a principled framework for combining task demands with operator capacity (Wickens, 2002, 2008). Rather than treating attention as a single undifferentiated pool, MRT decomposes operator capacity along modalities (visual-auditory), processing stages (perceptual-central-responding), codes (verbal-spatial), and resources, and predicts that dual-task interference depends on the extent to which two tasks recruit the same dimensions. Operationally, this suggests that the same HRV or fatigue state can have very different implications for performance depending on the task an operator is actually performing. A high sympathetic load that is tolerable during a vigilance-dominated intelligence-surveillance-reconnaissance mission may be unacceptable during a precision carrier landing.

Two further HF constructs expand this principle. The Warm vigilance-resource framework (Warm, Parasuraman, & Matthews, 2008) established that sustained-monitoring tasks deplete attentional resources predictably over time-on-task, with task-specific decay constants and asymptotic minima. The Chen teleoperation framework (Chen, Haas, & Barnes, 2007) formalised the impact of control latency on teleoperator performance, showing that latencies above ~100 ms force operators to adopt anticipatory or move-and-wait strategies with attendant cognitive cost. Together with situation-awareness theory (Endsley, 1995) and the allostatic-load model of cumulative physiological strain (McEwen, 1998), these constructs motivate a task-calibrated composite readiness index rather than a universal operator-state score.

### 1.3 Gap statement

Existing tools do not adequately combine four features in a single open framework: (i) theoretically grounded biomathematical fatigue estimation, (ii) HRV-derived autonomic markers, (iii) task-specific cognitive-load modifiers derived from HF literature, and (iv) explicit coverage of both manned aviation and UAS operator categories. Recent systematic reviews explicitly flag this gap for UAS operators (Li et al., 2025) and for warfighter mental-fatigue management more broadly (Rabat et al., 2025). Published cockpit-fatigue reviews focus on head-worn sensing (electroencephalography, functional near-infrared spectroscopy, eye-tracking) and omit HRV (Hamann et al., 2026), while machine-learning classifier studies of UAV and aviation workload rarely publish an inspectable biomathematical layer or task-taxonomy extension path (Stevens et al., 2022; Vogl et al., 2025). Recent multi-dimensional workload studies in adjacent aviation contexts such as helicopter maintenance demonstrate the value of combining NASA-TLX, heart-rate, and HRV features but stop short of a formal composite-readiness framework (Berthon et al., 2025).

### 1.4 Objective and contribution

The objective of this work is to define the **Operational Performance Indicator (OPI) framework**, provide its open-source reference implementation, and demonstrate the framework end-to-end with a single illustrative worked example. The manuscript makes four specific contributions. First, it formulates an explicit four-component weighted composite readiness index with per-task weight profiles. Second, it specifies a task taxonomy covering ten manned-aviation and seven UAS operator categories, each with expected HRV signatures and dominant failure modes. Third, it integrates a Warm-type vigilance-decrement model and a Chen-type control-latency penalty for the UAS subset, components that have no direct analogue in manned aviation and are not present in prior composite readiness frameworks. Fourth, it distributes an open-source reference implementation under the MIT license with documented execution environment and engineering verification across the fusion pathway.

The manuscript does not claim validated numerical parity with any external HRV or fatigue package, diagnostic accuracy against operator outcomes, or regulatory clearance. Field calibration of the per-task weights against operator performance is stated as the next research step.

---

## 2. Methods

### 2.1 Framework formulation

The OPI is a weighted linear composite of four components, with explicit penalty terms for stress, task complexity, control latency, and multi-vehicle supervisory load. Two formulations are used, one for manned aviation and one for UAS / teleoperator tasks.

For manned-aviation task categories the composite is

```
OPI_task = w1 · SAFTE_eff · Task_mod
         + w2 · HRV_recovery
         + w3 · Autonomic_reserve
         − Stress_penalty
         − Task_complexity_penalty
```

with `w1 + w2 + w3 = 1.00`. For UAS and teleoperator task categories the composite is extended to

```
OPI_UAS = w1 · SAFTE_eff
        + w2 · Vigilance_adj
        + w3 · HRV_recovery
        + w4 · Attention_capacity
        − Latency_penalty
        − Multi_vehicle_penalty
```

with `w1 + w2 + w3 + w4 = 1.00`. Component definitions, normalisation rules, and penalty functional forms are given in full in the framework document accompanying this manuscript and summarised in Table 2. Per-task weights and complexity modifiers are theory-derived from the HF sources cited throughout this section; field calibration against operator-performance outcomes is future work (Section 4.6).

The framework is intentionally linear and interpretable. Each component maps to a named construct in the HF literature, each weight is traceable to a theoretical rationale, and each penalty has a bounded functional form. This design is a deliberate contrast with the machine-learning classifiers that dominate recent operator-state literature (Stevens et al., 2022; Vogl et al., 2025; Jin et al., 2025): those classifiers achieve high accuracy within their training distribution, but they are less extensible to new task categories, less auditable for safety review, and more sensitive to sensor drift and population differences. A transparent composite with theory-derived weights is not expected to outperform a well-trained classifier on an in-distribution test set; it is expected to provide a reproducible, extensible, and inspectable substrate on which task-specific calibration and future classifier hybridisation can be layered.

### 2.2 Task taxonomy

Seventeen operator task categories are specified across two blocks: ten manned-aviation categories and seven UAS / teleoperator categories. Each category is defined by its primary performance demands, its dominant failure modes, and the expected HRV signatures under high workload, drawn from the HF literature. Table 1 presents the taxonomy in full. Manned-aviation categories include instrument flight under reduced visibility (IMC), night-vision operations, helmet-mounted-display flying, high-density air-traffic control, critical and non-critical emergencies, test-pilot operations, carrier landing, weapons delivery, and new-platform flight testing. UAS categories include intelligence-surveillance-reconnaissance, strike operations, search-and-rescue, autonomous-swarm supervisory control, contested-environment operations, ground-robot teleoperation, and subsea or long-latency teleoperation.

The taxonomy is not exhaustive and is not mutually exclusive. Mission-level activity often transitions across categories within a single sortie, and the OPI pipeline is designed to be re-evaluated per-window as the active task category changes. Additional categories can be added by specifying their primary demands, failure modes, and weight profile following the template used throughout the taxonomy.

### 2.3 Per-task weight profiles

Per-task weight profiles for the seventeen categories are given in Table 2. Weights reflect the theoretical dominance of particular OPI components in particular task contexts. Examples: in precision-motor-control tasks such as carrier landing, the HRV-recovery component is weighted more heavily (`w2 = 0.30`) because short-term vagal recovery has been linked to fine-motor precision; in critical-emergency tasks, the autonomic-reserve component gains weight (`w3 = 0.25`) because recovery capacity from acute stress drives sustained performance; in UAS supervisory control of multiple vehicles, the attention-capacity component dominates (`w4 = 0.30`) because sustained exception-handling across vehicles depletes attentional resources (Warm et al., 2008). The rationale column in Table 2 cites the HF source supporting each profile.

The task-complexity modifier `Task_mod ∈ [0.70, 1.00]` applies multiplicatively to SAFTE_eff in the manned-aviation formulation and captures operational compounding: a CAT III instrument approach under low platform familiarity combines to a lower modifier than either condition alone. Compound modifiers multiply with a floor at 0.50 to prevent degenerate near-zero products.

A stress penalty proportional to the excess of the Baevsky stress index over 150 applies across all categories (Shaffer & Ginsberg, 2017), and a learning-curve modifier applies to new-platform testing only (Table 2).

### 2.4 Vigilance-decrement and control-latency models (UAS)

Two UAS-specific components have no analogue in manned aviation: the vigilance-decrement model for sustained monitoring and the control-latency penalty for teleoperation. Both are formalised in Table 3.

The vigilance-decrement model follows Warm et al. (2008):

```
Vigilance_capacity(t) = (V0 − Vmin) · e^(−λ · t) + Vmin
```

with task-specific decay constants `λ ∈ [0.08, 0.15]` per hour for high-event ISR, low-event ISR, multi-vehicle supervisory control, and ground teleoperation. Parameter values reflect the combined effects of sustained monitoring load and event rate and are theory-derived; operational field calibration is future work. Recommended maximum sortie durations are offered as planning heuristics rather than validated thresholds.

The control-latency penalty follows Chen et al. (2007):

```
Latency_penalty = 0.5 · ln(1 + latency_ms / 100)
```

The logarithmic form captures the diminishing-returns relationship between latency and performance loss: small latencies have minimal impact, intermediate latencies force move-and-wait control strategies, and large latencies recommend supervisory-control transitions or autonomous handoff. Numerical latency tiers with suggested strategy selection are given in Table 3.

A linear multi-vehicle penalty `Multi_vehicle_penalty = 3 · (n_vehicles − 1)` captures attentional sharing across supervised vehicles in swarm-control tasks.

### 2.5 Reference implementation

The reference implementation is distributed under the MIT license at `https://github.com/strikerdlm/HRV`. The architecture separates client delivery from model execution while keeping the computational core as a single Python stack.

The frontend is a Next.js 14 application under `frontend/` that exposes operational and research routes. The orchestration layer is a FastAPI service under `api/main.py` and `api/research_endpoints.py` that exposes structured endpoints for HRV analysis, scheduling and readiness, user-profile management, and environmental context retrieval. The shared analytic core lives under `app/` and contains the HRV engine (`app/hrv_core.py`), the SAFTE reservoir model (`app/fatigue_calculator/safte_model.py`), the readiness-fusion logic (`app/scheduling_core.py`, `app/scheduling_engine.py`, `app/frms.py`, `app/frms_v2.py`), environmental ingestion (`app/noaa_space.py` and related modules), user-profile persistence (`app/user_profile_tab.py`, `app/user_database.py`), and publication-oriented export utilities (`app/publication_export.py`, `app/export_utils.py`). A client-side TypeScript SAFTE mirror (`frontend/src/lib/safte-model.ts`) reproduces the Python reservoir equations for responsive operational displays and is treated as architectural consistency rather than an independent validation layer.

The HRV engine computes time-domain metrics (RMSSD, SDNN, pNN50, median-NN, CVNN), frequency-domain metrics (VLF, LF, HF power; LF/HF ratio), and nonlinear metrics (SD1, SD2, SampEn, DFA-α1, Poincaré ellipse area, Baevsky stress index) from RR-interval series, with bounded artefact heuristics and linear interpolation for invalid samples. Outputs feed the HRV_recovery, Autonomic_reserve, and Attention_capacity components of the OPI through documented normalisation functions. External numerical benchmarking of the HRV engine against reference packages (e.g., Kubios, pyHRV, NeuroKit2) is explicitly out of scope for this manuscript and is stated as future work.

Two additional reference-implementation modules were added to strengthen the operational path from physiological input to composite readiness. The first is an in-platform **Psychomotor Vigilance Task (PVT)** module (`app/pvt_core.py`) that administers and scores three validated variants: PVT-B (3 min, 355 ms lapse threshold; Basner & Dinges, 2011), PVT-5 (5 min), and PVT-10 (standard; Dinges et al., 1997). The browser administration surface runs in the Next.js client with `performance.now()` timing bounded to ≈5–10 ms per Anwyl-Irvine et al. (2020), complemented by a PsychoPy desktop driver for sub-millisecond research sessions where required (Garaizar & Vadillo, 2014). The module was also validated on smartphone and tablet hardware by Grant et al. (2017) against a gold-standard 10-minute laptop PVT across 38 hours of total sleep deprivation. Its `pvt_lapses_3min` output feeds the existing `score_pvt_lapses_3min` subscore in the readiness-fusion layer with a ≥20-lapse hard gate; this operationalises the PVT component referenced in §2.3.3 as an inspectable feed rather than an external input. The second is a **Garmin-backed sleep module** (`app/sleep_core.py`) that derives sleep debt (cumulative deficit over a 7-night rolling window), the **Sleep Regularity Index** (Lunsford-Avery et al., 2018) via 5-minute epoch matching between consecutive 24-hour cycles, stage-balance proportions, and a low-SpO₂ screening proxy (four-band; explicitly not a clinical apnea classification). These outputs feed the SAFTE effectiveness estimate and the environmental-modifier component of the OPI and drive a four-band operational sleep readiness gate. Consumer wearable data do not replace polysomnography: the accuracy bounds reported by Lee et al. (2025) and Schyvens et al. (2024) are surfaced alongside every visualisation, and clinical sleep-disorder claims are prohibited in the UI.

### 2.6 Worked-example methodology

A single 128-minute HRV recording collected in November 2025 (8,553 RR intervals, 0.047 % quality-flagged windows) was used as an illustrative worked example to demonstrate framework instantiation end-to-end. The recording was processed through the HRV engine to produce five-minute windowed metrics, fed into the SAFTE reservoir with sleep-history inputs reflecting a rested baseline, and combined through the OPI fusion logic under three task hypotheses: a CAT II instrument landing system approach (category 1), a two-hour UAS intelligence-surveillance-reconnaissance sortie (category 11), and a daytime carrier recovery (category 8). For each task hypothesis the full OPI time series was computed per window and mapped to the readiness categories defined in Table 1. This worked example is a **framework-instantiation demonstration**: it shows how the same physiological input yields different composite outputs when the active task category changes. It does not test whether the OPI predicts operator outcomes, and it does not generalise beyond this single recording.

---

## 3. Results

### 3.1 Illustrative worked example: framework instantiation across three task hypotheses

Figure 3 presents the per-window OPI time series for the three task hypotheses computed across eighty five-minute windows spanning the 128-minute recording. Across all windows, the three task hypotheses produced substantively different composite distributions from identical physiological input.

Under the **CAT II ILS approach** hypothesis (`w1 = 0.55`, `w2 = 0.25`, `w3 = 0.20`, `Task_mod = 0.90`), the composite score varied between **48.9 and 63.7** (mean 55.9, SD 3.7) and was classified in the **CAUTION** band (55-69) for 58.8 % of windows and in the **NO-GO** band (< 55) for 41.2 % of windows. No window reached the **GO** or **GO (Monitor)** bands, reflecting the combined effect of the Category II complexity modifier, the dominance of the SAFTE component under moderate baseline effectiveness, and the stress-index penalty in higher-arousal windows.

Under the **UAS ISR 2-hour sortie** hypothesis (`w1 = 0.35`, `w2 = 0.30`, `w3 = 0.15`, `w4 = 0.20`, Vigilance_adj evaluated through the Warm decay with `λ = 0.12 h⁻¹`, `V0 = 100`, `Vmin = 65`; latency penalty at 120 ms datalink; single vehicle), the composite was higher overall, varying between **64.1 and 81.8** (mean 72.4, SD 4.4), with **66.2 %** of windows classified as **GO (Monitor)** and the remaining **33.8 %** as **CAUTION**. The composite showed a visible downward drift as simulated time-on-task approached 2 hours, consistent with the Warm vigilance decrement. No window reached **GO** (≥ 85) and none reached **NO-GO**.

Under the **carrier-landing** hypothesis (`w1 = 0.50`, `w2 = 0.30`, `w3 = 0.20`, `Task_mod = 0.85` to reflect CVN deck motion and short-final demands), the composite was systematically lower, varying between **42.6 and 58.3** (mean 50.3, SD 4.1), with **86.2 %** of windows classified as **NO-GO** and the remaining **13.8 %** as **CAUTION**. The complexity modifier combined with the relatively moderate RMSSD-derived HRV_recovery in the recording produced the most stringent task-specific assessment of the three hypotheses.

The central observation is that identical physiological input yielded composite distributions that differed both in central tendency (mean OPI 55.9 vs. 72.4 vs. 50.3) and in category allocation (0 % / 33.8 % / 86.2 % NO-GO across the three tasks, respectively). This is consistent with the MRT-derived weight-profile design intent and demonstrates that a task-calibrated composite exposes task-specific readiness information that a task-agnostic composite would collapse. The illustrative numerical outputs are framework-instantiation values only; they do not reflect the readiness state of any operator performing any of the three tasks, because the recording was collected from a single individual in a non-operational context. The worked-example parameters and outputs are supplied in full at `analysis/opi_worked_example.json` and are reproducible from `analysis/opi_worked_example.py`.

### 3.2 Engineering verification of the OPI fusion pathway

Engineering verification of the reference implementation covers the major paths through the OPI pipeline at the software level. Automated tests exercise scheduling-core readiness fusion (`tests/test_scheduling_core.py`), fatigue-risk-management behaviour and SAFTE-adjacent logic (`tests/test_frms.py`, `tests/test_frms_v2.py`, `tests/test_fatigue_integration.py`), API endpoint normalisation and behaviour (`tests/test_api_user_profile_normalization.py`, `tests/test_research_windowed_endpoint.py`), environmental-modifier ingestion, caching, and alignment (`tests/test_noaa_cache.py`, `tests/test_space_weather_impact.py`, `tests/test_space_weather_alignment.py`), and broader statistical and charting modules (`tests/test_comprehensive_modules.py`). The PVT and sleep reference-implementation modules described in §2.5 are covered by dedicated test suites: `tests/test_pvt_core.py` (28 tests across trial classification, alert- and fatigued-session metrics, variant scaling, edge cases, and the operational gate) and `tests/test_sleep_core.py` (27 tests across stage balance, sleep debt scaling, Sleep Regularity Index behaviour on identical and alternating schedules, SpO₂ screening bands, operational gate escalation, and the Pearson / Spearman correlation engine with Benjamini-Hochberg FDR adjustment). A coverage map at the OPI-component level is supplied in Table 5.

These tests justify reporting that the readiness fusion, orchestration, environmental-modifier, vigilance, and sleep layers are implemented and regression-tested at the software level. They do not establish operational validation, clinical deployment readiness, or numerical equivalence of the HRV engine to external reference packages. In particular, the windowed-endpoint test monkeypatches the inner HRV computation to isolate endpoint behaviour, so that pathway is verified more directly than the underlying numerical implementation. The browser PVT and sleep analytics inherit the timing precision and wearable-device validity bounds of the underlying measurement surfaces rather than being independently benchmarked against reference hardware in this manuscript.

### 3.3 Reproducibility and reporting assets

The reference implementation is distributed at `https://github.com/strikerdlm/HRV` under the MIT license. The documented primary execution environment is `conda hrv-py312` with Python 3.12 and dependencies declared in `requirements.txt`, and the primary web client is a Next.js/TypeScript application with dependencies under `frontend/package.json`. The repository supports structured logging, cached environmental-data management, and export utilities designed to emit manuscript-oriented statistics and supporting artefacts. Before formal submission, a tagged release or archived DOI (e.g., Zenodo) will be cited as the frozen identifier for the reported version. These reproducibility characteristics are consistent with published guidance for reproducible computational research (Sandve, Nekrutenko, Taylor, & Hovig, 2013).

Table 4 summarises the reproducibility and deployment metadata.

---

## 4. Discussion

### 4.1 Principal contribution

The principal contribution of this manuscript is the specification of a task-calibrated composite operator-readiness index — the Operational Performance Indicator — together with its per-task weight profiles, vigilance-decrement and latency models, and an open-source reference implementation. The framework is intentionally linear, inspectable, and extensible. It is not a machine-learning classifier and it is not intended to outperform well-trained classifiers on in-distribution tasks. It is intended to provide a theoretically grounded substrate on which task-specific calibration, new task categories, and future classifier hybridisation can be layered with auditability preserved.

### 4.2 Comparison with adjacent frameworks

Several recent frameworks are adjacent to the OPI but differ in important ways. Feng et al. (2018) proposed an MRT-grounded multinomial logistic regression combining fixation-frequency, ECG, and electrodermal features for pilot workload across three flight phases (cruise, approach, landing), with reported discrimination accuracy of 84.85 %. The Feng framework validates the principle of MRT + physiological fusion but covers only three phases of one aircraft type, includes no fatigue model, and is distributed as a study result rather than as reusable software. The OPI extends this line of work to seventeen operator task categories, incorporates SAFTE fatigue dynamics, and ships as open-source reference code.

Stevens et al. (2022) used Cognitive Metrics Profiling to link a cognitive model to physiological workload in a single unmanned-vehicle control task. That work demonstrates the predictive value of cognitive-architecture modelling for workload but addresses a single task and does not provide per-task weight profiles across a taxonomy. Vogl et al. (2025) developed individualised support-vector machine classifiers of cognitive workload from ECG and pupillometry in a low-fidelity aviation simulator with three participants, reporting 70-80 % binary classification accuracy. Their work is complementary: the OPI can serve as a calibration layer under which classifiers like the Vogl model are trained on particular operator populations. Li et al. (2025) systematically reviewed machine-learning approaches for UAS operator cognitive load and explicitly identified the absence of unified frameworks integrating physiological signals, biomathematical fatigue, and task-specific weighting as a research gap. The OPI as proposed addresses that gap directly.

Berthon et al. (2025) recently published a multi-dimensional workload study in helicopter maintenance that combined NASA-TLX, heart rate, and HRV across tasks of varying complexity. The work confirms that combining subjective, physiological, and performance measures is tractable in an applied aviation context and validates the venue-level fit between this kind of contribution and Applied Ergonomics, while demonstrating the absence of a formal task-calibrated composite-readiness framework that OPI fills.

Hamann et al. (2026) reviewed the state of the art in cockpit mental-fatigue assessment using head-worn sensing (EEG, fNIRS, eye-tracking). Their conclusion — that mature methods exist but are not yet operationally deployable — highlights the broader need for inspectable, deployment-ready frameworks. The OPI is consistent with that need and accommodates head-worn signals as additional inputs to the Attention_capacity component where available.

Rabat et al. (2025) reviewed fatigue and management of warfighter mental endurance and called specifically for "an infrastructure for physiological monitoring and integrated analyses" combined with explainable and interpretable modelling. The OPI is a concrete instance of this infrastructure.

### 4.3 Theoretical grounding and choice of composite structure

The OPI's linear structure and per-task weighting reflect three theoretical commitments. First, Multiple Resource Theory predicts that task interference and performance ceiling depend on the specific demand profile of the task (Wickens, 2002, 2008); a composite that weights components differently by task category operationalises this prediction directly. Second, the allostatic-load framework (McEwen, 1998) distinguishes between acute stress responses (captured by the stress-index penalty) and cumulative regulatory strain (captured by the HRV_recovery and Autonomic_reserve components), consistent with a composite that separates short-term and longer-term autonomic signals. Third, situation-awareness theory (Endsley, 1995) motivates the attention-capacity component for UAS supervisory-control tasks where operator cognition is dominated by multi-target tracking and exception handling rather than fine-motor control.

The choice of a linear composite over a classifier was deliberate. Linear composites with theory-derived weights can be externally calibrated, sensitivity-analysed, audited by regulators, and extended to new task categories by domain experts. Classifiers require labelled training data that is rarely available for aerospace operators at scale, are less portable across populations, and are more vulnerable to sensor drift. Hybrid approaches that use classifiers to refine the per-task weights of a linear composite under particular operational conditions are a natural extension path.

### 4.4 Strengths

The OPI has several strengths as a methodology paper. The framework is theoretically grounded in multiple HF constructs with clearly cited source literature. It spans both manned aviation and UAS, two populations usually treated in separate research communities. It ships with an open-source reference implementation under the MIT license, enabling independent verification and extension. The reference implementation includes an in-platform PVT module (three validated variants plus browser and PsychoPy desktop administration surfaces) and a Garmin-backed sleep module (debt, Sleep Regularity Index, SpO₂ screening proxy) that concretise the vigilance and fatigue inputs to the composite as inspectable, regression-tested code rather than external dependencies. The evidence posture is explicitly tiered, distinguishing what is demonstrated (framework, implementation, engineering verification, illustrative example) from what remains to be validated (per-task weight calibration, operator outcome prediction, numerical parity with external HRV packages).

### 4.5 Limitations

The most important limitation is that **per-task OPI weights are theory-derived, not empirically calibrated against field operator performance**. The weights reflect the HF literature for each task category but have not been optimised against real operator outcomes. A reviewer could reasonably argue that the specific numerical values proposed for `w1`, `w2`, `w3`, and `w4` are a subset of a larger family of plausible profiles and that empirical selection among them is pending. This limitation is intrinsic to a methodology-introduction paper and is addressed in Section 4.6.

A second limitation is that the illustrative worked example uses a single HRV recording collected in a non-operational context. It demonstrates framework instantiation and does not demonstrate operational validity. All prose in Section 3 has been written to be consistent with this framing.

A third limitation is that the HRV engine has not been externally benchmarked against reference HRV packages for the purposes of this manuscript. The engine produces standards-aligned metrics and has internal verification for the fusion pathway, but numerical equivalence to Kubios or comparable tools is not established and is not claimed.

A fourth limitation is that the client-side TypeScript SAFTE mirror reproduces the canonical Python implementation for responsive display but has not been subjected to formal parity testing against the canonical version. This mirror is treated as architectural consistency rather than as an independent model.

A fifth limitation applies specifically to the vigilance-decrement and control-latency components: the decay constants and penalty coefficients are derived from seminal HF literature (Warm et al., 2008; Chen et al., 2007) and may require re-calibration for modern UAS platforms with advanced autonomy and degraded links, neither of which are typical of the original studies.

A sixth limitation is that the platform is not presented as a certified medical device or as a regulatory-cleared decision-support system. Operational modules draw on published aerospace, fatigue-management, and safety frameworks (ICAO, 2020; National Aeronautics and Space Administration, 2023), but these are alignment references, not certifications.

A seventh limitation applies to the Garmin-backed sleep module. Consumer wrist-worn sleep-tracking devices have been systematically compared against polysomnography with clinically meaningful disagreement on total sleep time, sleep efficiency, sleep latency, and wake-after-sleep-onset (Lee et al., 2025; Schyvens et al., 2024). The manuscript therefore bounds sleep-derived composites to pattern-level tracking and an explicit screening posture: Sleep Regularity Index and sleep debt are used as operational modifiers within a documented disclosure, and low-nocturnal-SpO₂ night counts are surfaced only as a screening proxy without any apnea or sleep-disordered-breathing diagnosis. Stronger claims would require polysomnographic ground truth and a dedicated validation protocol, which are out of scope for the present methodology paper.

An eighth limitation applies to the browser administration surface for the PVT. Robot-actuator benchmarking places typical web-browser reaction-time precision at the order of 5–10 ms across modern browsers and devices (Anwyl-Irvine et al., 2020). This is adequate for operational GO/NO-GO gating (which is driven by lapse counts) and for longitudinal within-operator tracking, but is not equivalent to laboratory-grade timing. Research sessions that require sub-millisecond precision should use the PsychoPy desktop driver, whose validity has been independently evaluated for brief-stimulus timing (Garaizar & Vadillo, 2014).

### 4.6 Validation roadmap

The most immediate next step is empirical calibration of the per-task OPI weights against field operator-performance data. A straightforward calibration study would enrol operators from at least two task categories (e.g., one manned-aviation and one UAS), collect per-sortie physiological and schedule data alongside task-specific performance outcomes, and use penalised regression or Bayesian hierarchical modelling to select weight profiles that maximise predictive concordance. Sensitivity analysis across weight families would then quantify how much the specific theory-derived values matter relative to the structure of the composite. The in-platform PVT and sleep modules now expose concrete, daily-collectable feeds for this calibration: `pvt_lapses_3min` as a vigilance anchor, `sleep_regularity_index` and `cumulative_debt_hours_7d` as chronobiological modifiers, and the FDR-adjusted correlation engine as a ready substrate for per-operator multi-session analysis.

A second priority is external numerical benchmarking of the HRV engine against reference implementations, producing intraclass correlation coefficients and Bland-Altman limits of agreement for time-domain, frequency-domain, and nonlinear metrics on standard test datasets (e.g., MIT-BIH Normal Sinus Rhythm, Fantasia). This is a bounded piece of work amenable to publication as a companion validation paper.

A third priority is comparative benchmarking against adjacent frameworks on matched datasets. Feng et al. (2018), Stevens et al. (2022), and Vogl et al. (2025) provide comparator systems whose outputs could be replicated and scored against the same ground-truth performance data used to calibrate the OPI.

A fourth priority is a minimal prospective pilot study in a well-characterised operator population, most naturally Colombian Air Force pilots in simulator-based training or UAS operators in training sorties, with ethics approval and a pre-specified analysis plan.

Beyond validation, future work includes a tagged release or archived DOI for the reported version, a formal artefact manifest for figures and tables, usability studies and role-specific deployment playbooks for flight surgeons and operational teams, and a separation of the vigilance and latency models into dedicated methodological studies if the UAS branch of the framework develops beyond its current scope.

---

## 5. Conclusions

The Operational Performance Indicator framework offers a theoretically grounded, task-calibrated alternative to fatigue-only composites, HRV-only analyses, and machine-learning operator-state classifiers. The framework covers both manned-aviation and UAS operator categories, ships as open-source reference code under the MIT license, and is supported by engineering verification across its fusion pathway. The present manuscript is bounded to framework definition, reference implementation, and illustrative demonstration; empirical calibration of per-task weights, external numerical benchmarking of the HRV engine, and prospective field validation in operator populations are the next research steps. The framework is designed to be extensible by domain experts without requiring re-training, which positions it as a substrate for iterative operational deployment and subsequent classifier hybridisation rather than as a closed analytic end-product.

---

## 6. Compliance and Transparency

### 6.1 Data availability

No new human-subject dataset was generated for the framework-definition and engineering-verification components reported in this manuscript. The single 128-minute HRV recording used for the illustrative worked example in Section 3.1 is available from the corresponding author on reasonable request and is not linked to any identified individual. Code, manuscript support files, and derived repository artefacts are available at the public source repository.

### 6.2 Code and artefact availability

The reference implementation is available as open-source software at `https://github.com/strikerdlm/HRV` under the MIT license. The primary execution environment is `conda hrv-py312` with Python 3.12 and dependencies declared in `requirements.txt`; the primary web client is a Next.js/TypeScript application with dependencies under `frontend/package.json`. A tagged release or archived DOI corresponding to the exact reported version will be cited before submission.

### 6.3 Ethics and regulatory alignment

Ethics approval and informed consent were not required for the framework-definition and engineering-verification components because no new human-subject dataset was generated or analysed for those components. The single illustrative HRV recording was contributed by the author for framework-demonstration purposes and is not linked to any operational scenario. If future versions of the manuscript incorporate prospective or retrospective operator data, study-specific ethics approval, consent documentation, and reporting-guideline alignment (STROBE for observational, TRIPOD+AI for predictive models) will be added.

The platform is not presented as a certified medical device or as a regulated decision-support system. Operational modules were designed with reference to published aerospace, fatigue-management, and safety frameworks, including NASA-STD-3001 human-systems standards and ICAO Doc 9966 fatigue-management guidance (International Civil Aviation Organization, 2020; National Aeronautics and Space Administration, 2023). These references inform design and threshold logic but do not constitute certification, legal compliance, or regulatory clearance.

### 6.4 Author contributions (CRediT)

Dr Diego Malpica MD contributed conceptualisation, methodology, software, formal analysis, investigation, writing — original draft, writing — review and editing, visualisation, supervision, and project administration. The CRediT statement will be updated if additional authors are added before submission.

### 6.5 Funding and conflicts of interest

No project-level external funding statement was identified in the repository materials at the time of drafting. This statement will be updated before submission if grant support, institutional sponsorship, or other funding applies. Conflict-of-interest declarations will be confirmed for all authors before submission.

### 6.6 Acknowledgments

The author acknowledges the open-source scientific Python ecosystem, the public technical and data resources that inform the environmental-modifier modules (NOAA Space Weather Prediction Center), and the HF research community whose foundational work on Multiple Resource Theory, vigilance, teleoperation, fatigue modelling, and situation awareness provides the theoretical basis for this framework.

### 6.7 Reporting-guideline positioning

This manuscript is a methodology and reference-implementation paper. The central claims are framework definition, implementation, and illustrative demonstration; the evidence base does not include prospective human-subject outcomes or predictive-accuracy evaluation. Reporting therefore emphasises transparent description of framework components, per-task parameterisation, reference-implementation architecture, and engineering verification. If future versions add empirical validation, adapted STROBE elements will be incorporated, and TRIPOD+AI or CLAIM extensions will apply only to sections making predictive-model claims.

---

## References

Anwyl-Irvine, A., Dalmaijer, E. S., Hodges, N., & Evershed, J. K. (2020). Realistic precision and accuracy of online experiment platforms, web browsers, and devices. *Behavior Research Methods, 53*(4), 1407-1425. https://doi.org/10.3758/s13428-020-01501-5

Basner, M., & Dinges, D. F. (2011). Maximizing sensitivity of the Psychomotor Vigilance Test (PVT) to sleep loss. *Sleep, 34*(5), 581-591. https://doi.org/10.1093/sleep/34.5.581

Berthon, L., Bernard, F., Fleury, S., Paquin, R., & Richir, S. (2025). Multi-dimensional measurement of mental workload in industrial context: an experiment in the field of helicopter maintenance. *Applied Ergonomics, 129*, 104599. https://doi.org/10.1016/j.apergo.2025.104599

Chen, J. Y. C., Haas, E. C., & Barnes, M. J. (2007). Human performance issues and user interface design for teleoperated robots. *IEEE Transactions on Systems, Man, and Cybernetics, Part C (Applications and Reviews), 37*(6), 1231-1245. https://doi.org/10.1109/TSMCC.2007.905819

Dinges, D. F., Pack, F., Williams, K., Gillen, K. A., Powell, J. W., Ott, G. E., Aptowicz, C., & Pack, A. I. (1997). Cumulative sleepiness, mood disturbance, and psychomotor vigilance performance decrements during a week of sleep restricted to 4-5 hours per night. *Sleep, 20*(4), 267-277. https://doi.org/10.1093/sleep/20.4.267

Devine, J. K., Garcia, C. R., Simoes, A. S., Guelere, M. R., de Godoy, B., Silva, D. S., Pacheco, P. C., Choynowski, J., & Hursh, S. R. (2022). Predictive biomathematical modeling compared to objective sleep during COVID-19 humanitarian flights. *Aerospace Medicine and Human Performance, 93*(1), 4-12. https://doi.org/10.3357/AMHP.5909.2022

Endsley, M. R. (1995). Toward a theory of situation awareness in dynamic systems. *Human Factors, 37*(1), 32-64. https://doi.org/10.1518/001872095779049543

Feng, C., Wanyan, X., Yang, K., Zhuang, D., & Wu, X. (2018). A comprehensive prediction and evaluation method of pilot workload. *Technology and Health Care, 26*(S1), 65-78. https://doi.org/10.3233/thc-174201

Forger, D. B., Jewett, M. E., & Kronauer, R. E. (1999). A simpler model of the human circadian pacemaker. *Journal of Biological Rhythms, 14*(6), 533-538. https://doi.org/10.1177/074873099129000867

Garaizar, P., & Vadillo, M. A. (2014). Accuracy and precision of visual stimulus timing in PsychoPy: No timing errors in standard usage. *PLoS ONE, 9*(11), e112033. https://doi.org/10.1371/journal.pone.0112033

Grant, D. A., Honn, K. A., Layton, M. E., Riedy, S. M., & Van Dongen, H. P. A. (2017). 3-minute smartphone-based and tablet-based psychomotor vigilance tests for the assessment of reduced alertness due to sleep deprivation. *Behavior Research Methods, 49*(3), 1020-1029. https://doi.org/10.3758/s13428-016-0763-8

Hamann, A., van Klaren, C., Zon, R., Dehais, F., Carstengerdes, N., van Miltenburg, M., & Cabrera Castillos, K. (2026). The state of the art in assessing mental fatigue in the cockpit using head-worn sensing technology. *Frontiers in Neuroergonomics, 6*, 1673268. https://doi.org/10.3389/fnrgo.2025.1673268

Houghton, R., Martinetti, A., & Majumdar, A. (2024). A framework for selecting and assessing wearable sensors deployed in safety critical scenarios. *Sensors, 24*(14), 4589. https://doi.org/10.3390/s24144589

Hursh, S. R., Balkin, T. J., Miller, J. C., & Eddy, D. R. (2004). The Fatigue Avoidance Scheduling Tool: Modeling to minimize the effects of fatigue on cognitive performance. *SAE Technical Paper Series*, 2004-01-2151. https://doi.org/10.4271/2004-01-2151

International Civil Aviation Organization. (2020). *Manual for the oversight of fatigue management approaches (Doc 9966, 2nd ed., Version 2, revised).* ICAO.

Jin, K., Rubio-Solis, A., Naik, R., Leff, D., Kinross, J., & Mylonas, G. (2025). Human-centric cognitive state recognition using physiological signals: A systematic review of machine learning strategies across application domains. *Sensors, 25*(13), 4207. https://doi.org/10.3390/s25134207

Lee, Y. J., Lee, J. Y., Cho, J. H., Kang, Y. J., & Choi, J. H. (2025). Performance of consumer wrist-worn sleep tracking devices compared to polysomnography: A meta-analysis. *Journal of Clinical Sleep Medicine, 21*(3), 573-582. https://doi.org/10.5664/jcsm.11460

Li, Q., Molloy, O., El-Fiqi, H., & Eves, G. (2025). Applications of machine learning in assessing cognitive load of uncrewed aerial system operators and in enhancing training: A systematic review. *Drones, 9*(11), 760. https://doi.org/10.3390/drones9110760

Lunsford-Avery, J. R., Engelhard, M. M., Navar, A. M., & Kollins, S. H. (2018). Validation of the Sleep Regularity Index in Older Adults and Associations with Cardiometabolic Risk. *Scientific Reports, 8*, 14158. https://doi.org/10.1038/s41598-018-32402-5

McEwen, B. S. (1998). Protective and damaging effects of stress mediators. *New England Journal of Medicine, 338*(3), 171-179. https://doi.org/10.1056/NEJM199801153380307

National Aeronautics and Space Administration. (2023). *NASA Spaceflight Human-System Standard Volume 1, Crew Health (NASA-STD-3001, Vol. 1, Rev. C).* NASA.

Pontiggia, A., Gomez-Merino, D., Quiquempoix, M., Beauchamps, V., Boffet, A., Fabries, P., Chennaoui, M., & Sauvet, F. (2024). MATB for assessing different mental workload levels. *Frontiers in Physiology, 15*, 1408242. https://doi.org/10.3389/fphys.2024.1408242

Quigley, K. S., Gianaros, P. J., Norman, G. J., Jennings, J. R., Berntson, G. G., & de Geus, E. J. C. (2024). Publication guidelines for human heart rate and heart rate variability studies in psychophysiology — Part 1: Physiological underpinnings and foundations of measurement. *Psychophysiology, 61*(9), e14604. https://doi.org/10.1111/psyp.14604

Rabat, A., Van Cutsem, J., Marcora, S. M., Lambert, A., Markwald, R., Kubala, A. G., & Friedl, K. E. (2025). Fatigue and management of warfighter mental endurance. *BMJ Military Health, 171*(5), 447-451. https://doi.org/10.1136/military-2025-002963

Sandve, G. K., Nekrutenko, A., Taylor, J., & Hovig, E. (2013). Ten simple rules for reproducible computational research. *PLoS Computational Biology, 9*(10), e1003285. https://doi.org/10.1371/journal.pcbi.1003285

Schyvens, A.-M., Van Oost, N. C., Aerts, J.-M., Masci, F., Peters, B., Neven, A., Dirix, H., Wets, G., Ross, V., & Verbraecken, J. (2024). Accuracy of Fitbit Charge 4, Garmin Vivosmart 4, and WHOOP versus polysomnography: Systematic review. *JMIR mHealth and uHealth, 12*, e52192. https://doi.org/10.2196/52192

Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability metrics and norms. *Frontiers in Public Health, 5*, 258. https://doi.org/10.3389/fpubh.2017.00258

Stevens, C. A., Morris, M. B., Fisher, C. R., & Myers, C. W. (2022). Profiling cognitive workload in an unmanned vehicle control task with cognitive models and physiological metrics. *Military Psychology, 35*(6), 507-520. https://doi.org/10.1080/08995605.2022.2130673

Vogl, J., O'Brien, K., & St. Onge, P. (2025). One size does not fit all: A support vector machine exploration of multiclass cognitive state classifications using physiological measures. *Frontiers in Neuroergonomics, 6*, 1566431. https://doi.org/10.3389/fnrgo.2025.1566431

Warm, J. S., Parasuraman, R., & Matthews, G. (2008). Vigilance requires hard mental work and is stressful. *Human Factors, 50*(3), 433-441. https://doi.org/10.1518/001872008X312152

Wickens, C. D. (2002). Multiple resources and performance prediction. *Theoretical Issues in Ergonomics Science, 3*(2), 159-177. https://doi.org/10.1080/14639220210123806

Wickens, C. D. (2008). Multiple resources and mental workload. *Human Factors, 50*(3), 449-455. https://doi.org/10.1518/001872008X288394

---

*End of manuscript draft v0.1 (branch: `q1-hf-opi-reframe`). Supplementary materials (engineering-verification inventory, standards crosswalk, deployment prerequisites, non-claims list) are consolidated in `manuscript/supplement/submission_support_appendix.md` and may require a light refresh to align terminology with the OPI framing.*
