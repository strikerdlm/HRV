# Authors: Diego L. Malpica (PI); Ingrid Xiomara Bejarano Cifuentes

> **Note (2026-04-30):** This markdown was the working draft for the prose body. The canonical submission source is now `submission_thms/tex/manuscript.tex` (IEEEtran two-column LaTeX), which has been substantively revised since this markdown was last edited (title shortened, RQ-contribution alignment in §1.4, real uniform-weights numbers in §3.1, added §3.3 HRV-engine numerical benchmark on MIT-BIH NSR with NeuroKit2 [Table V], added Xu et al. 2026 and Donmez et al. 2010 citations, multi-vehicle and stress-penalty rationale restored, §4.4 Strengths folded into §4.1, hedge cleanup). When a discrepancy exists between this file and the .tex, the .tex wins.

## Title page

**Title:** Task-calibrated Operational Performance Indicators: a fusion framework for aviation and unmanned aircraft system operator state

**Running title:** Task-calibrated OPI for aerospace HMS operators

**Authors**

1. **Diego L. Malpica MD**^a,\* (Principal Investigator)
2. **Ingrid Xiomara Bejarano Cifuentes**^b

**Affiliations**

^a Aerospace Medicine — Subdirectorate of Aerospace Sciences, Direction of Aerospace Medicine (DIMAE), Colombian Aerospace Force (Fuerza Aeroespacial Colombiana), Bogotá D.C., Colombia
^b Centro de Investigación y Desarrollo de Tecnologías Aeroespaciales (CITAE), Colombian Aerospace Force (Fuerza Aeroespacial Colombiana), Bogotá D.C., Colombia

**Corresponding author**

**Diego L. Malpica MD** — affiliation ^a

| | |
| --- | --- |
| **E-mail** | diego.malpica@fac.mil.co |
| **ORCID** | https://orcid.org/0000-0002-2257-4940 |
| **Postal address** | Direction of Aerospace Medicine (DIMAE), Colombian Aerospace Force, Bogotá D.C., Colombia |

**Second author ORCID:** https://orcid.org/0000-0002-7981-2356

---

## Abstract

Operator-state monitoring in aviation and unmanned aircraft system (UAS) operations combines physiological signals, biomathematical fatigue models, and workload theory, yet no published human-machine systems (HMS) framework integrates these streams into an interpretable, task-calibrated readiness index spanning manned and unmanned operators with explicit weight profiles and an open reference implementation. This article defines the Operational Performance Indicator (OPI): a weighted composite of SAFTE effectiveness, heart-rate-variability (HRV) markers, Multiple Resource Theory task modifiers, and bounded task-operational penalties, including UAS-specific vigilance-decrement and teleoperation-latency terms. Seventeen operator categories — ten manned-aviation and seven UAS — receive explicit weight profiles. We summarize the MIT-licensed reference implementation, report engineering verification of the fusion pathway, and apply one 128-minute HRV recording under three task hypotheses to show that summary-consistent physiology yields different readiness scores when task context changes. Three research questions structure the contribution: whether task-calibrated weighting changes classification under summary-consistent input; whether theory-derived weights are identifiable on operationally-realistic samples; and whether a linear composite supports traceable safety-case logic for HMS gate decisions. Claims are limited to framework definition, software, and illustrative demonstration; prospective field validation is the next research step.

### Index Terms

Cognitive ergonomics; human-machine systems; operator state; vigilance decrement; teleoperation latency.

---

## 1. Introduction

### 1.1 Operator state and the limits of current monitoring approaches

Aviation and unmanned aircraft system (UAS) operations increasingly rely on physiological, behavioral, and schedule information to infer operator state and inform mission-level decisions. Heart-rate variability (HRV) is now a routine analytic layer in studies of workload, fatigue, and vigilance in safety-critical domains [1], [2]. Biomathematical fatigue modeling has matured from early pacemaker formulations to operational scheduling tools such as the Fatigue Avoidance Scheduling Tool built on the SAFTE model [3], [4], [5]. Subjective workload ratings and task batteries such as the Multi-Attribute Task Battery remain widely used to elicit and benchmark physiological responses [6]. Recent reviews document an active literature on wearable psychophysiological sensing in safety-critical environments [7] and on machine-learning classifiers for cognitive-state recognition across high-stakes domains [8].

Despite this activity, three structural limitations affect how operator-state information is used in practice. First, most published frameworks rely on a single information channel: HRV-only analyses, SAFTE-only fatigue forecasts, or electroencephalography-only workload classifiers [9]. Second, task-specific calibration is rare; the few composite studies that exist tend to be constrained to a narrow task slice such as cruise–approach–landing phases of a single aircraft type [10]. Third, the recent wave of machine-learning classifiers for operator state [11], [12], [13] demonstrates high classification accuracy on the tasks they evaluate, but black-box classifiers are difficult to audit, transfer across platforms, and modify when new task categories appear.

### 1.2 Theoretical grounding for a task-calibrated composite

Multiple Resource Theory (MRT) provides a principled framework for combining task demands with operator capacity [14], [15]. Rather than treating attention as a single undifferentiated pool, MRT decomposes operator capacity along modalities, processing stages, codes, and resources, and predicts that dual-task interference depends on the extent to which two tasks recruit the same dimensions. Operationally, this implies that the same HRV or fatigue state can have very different implications for performance depending on the task an operator is actually performing.

Two further constructs expand this principle. The Warm vigilance-resource framework [16] established that sustained-monitoring tasks deplete attentional resources predictably over time-on-task, with task-specific decay constants and asymptotic minima. The Chen teleoperation framework [17] formalized the impact of control latency on teleoperator performance, showing that latencies above ~100 ms force operators to adopt anticipatory or move-and-wait strategies with attendant cognitive cost. Together with situation-awareness theory [18] and the allostatic-load model of cumulative physiological strain [19], these constructs motivate a task-calibrated composite readiness index rather than a universal operator-state score.

### 1.3 Gap statement

Existing tools do not adequately combine four features in a single open framework: (i) theoretically grounded biomathematical fatigue estimation, (ii) HRV-derived autonomic markers, (iii) task-specific cognitive-load modifiers, and (iv) explicit coverage of both manned aviation and UAS operator categories. Recent systematic reviews flag this gap for UAS operators [13] and for warfighter mental-fatigue management more broadly [20]. Cockpit-fatigue reviews focused on head-worn sensing omit HRV [9], while machine-learning classifier studies of UAV and aviation workload rarely publish an inspectable biomathematical layer or a task-taxonomy extension path [11], [12].

### 1.4 Research questions and contribution

This manuscript investigates three research questions:

> **RQ1.** Does task-calibrated weighting of fatigue, autonomic, and cognitive-load components change readiness classification when summary HRV indices are held constant?
>
> **RQ2.** Are theory-derived per-task weight profiles identifiable on operationally-realistic operator samples, given known constraints on aerospace data availability?
>
> **RQ3.** Does a linear weighted-composite substrate support traceable, audit-friendly safety-case logic for human-machine system gate decisions without sacrificing classification fidelity relative to opaque end-to-end classifiers?

The present manuscript addresses RQ1 through an illustrative worked example and frames RQ2 and RQ3 as the validation roadmap; field instrumentation for the 2026–2027 austral-summer Antarctic operational campaign is the subject of a separate protocol publication.

The objective of this work is to define the Operational Performance Indicator (OPI) framework (Fig. 1), provide its open-source reference implementation, and demonstrate the framework end-to-end with one illustrative worked example. The manuscript makes four contributions: (i) an explicit four-component weighted-composite readiness index with per-task weight profiles; (ii) a task taxonomy covering ten manned-aviation and seven UAS operator categories with expected HRV signatures and dominant failure modes; (iii) a Warm-type vigilance-decrement model and a Chen-type control-latency penalty for the UAS subset, components without direct analogue in prior composite readiness frameworks; and (iv) an MIT-licensed reference implementation with documented engineering verification across the fusion pathway. The framework does not claim validated diagnostic accuracy against operator outcomes, regulatory clearance, or numerical parity with external HRV or fatigue packages.

![Fig. 1. Conceptual schematic of the Operational Performance Indicator framework.](../05_figures/figure1_opi_conceptual_schematic.png)

**Fig. 1.** Conceptual schematic of the OPI framework. SAFTE-style fatigue effectiveness, HRV-derived autonomic markers, attention capacity, and task-operational modifiers feed a per-task weighted composite that maps to GO / GO-Monitor / CAUTION / NO-GO bands.

---

## 2. Methods

### 2.1 Framework formulation

The OPI is a weighted linear composite of four components, with explicit penalty terms for stress, task complexity, control latency, and multi-vehicle supervisory load. Two formulations are used.

For manned-aviation task categories the composite is

$$\textstyle \mathrm{OPI}_{\mathrm{task}} = w_1\,\mathrm{SAFTE_{eff}}\,T_{\mathrm{mod}} + w_2\,\mathrm{HRV_{rec}} + w_3\,\mathrm{Auto_{res}} - P_{\mathrm{stress}} - P_{\mathrm{cplx}}, \quad w_1{+}w_2{+}w_3 = 1. \tag{1}$$

For UAS and teleoperator task categories the composite is extended to

$$\textstyle \mathrm{OPI}_{\mathrm{UAS}} = w_1\,\mathrm{SAFTE_{eff}} + w_2\,V_{\mathrm{adj}} + w_3\,\mathrm{HRV_{rec}} + w_4\,\mathrm{Att_{cap}} - P_{\mathrm{lat}} - P_{\mathrm{mv}}, \quad w_1{+}w_2{+}w_3{+}w_4 = 1. \tag{2}$$

Component definitions, normalization rules, and penalty functional forms are given in Table II. Per-task weights and complexity modifiers are theory-derived from the cited HMS and human-factors literature; field calibration against operator-performance outcomes is future work (Section 4.6).

The framework is intentionally linear and interpretable. Each component maps to a named construct in the literature, each weight is traceable to a theoretical rationale, and each penalty has a bounded functional form. This design contrasts with the machine-learning classifiers that dominate recent operator-state work [11], [12], [8]: those classifiers achieve high in-distribution accuracy but are less extensible to new task categories, less auditable for safety review, and more sensitive to sensor drift and population differences. A transparent composite with theory-derived weights is not expected to outperform a well-trained classifier on its training distribution; it is expected to provide a reproducible, extensible, and inspectable substrate on which task-specific calibration and downstream classifier hybridization can be layered.

### 2.2 Task taxonomy

Seventeen operator task categories are specified across two blocks: ten manned-aviation categories and seven UAS / teleoperator categories. Each category is defined by its primary performance demands, dominant failure modes, and expected HRV signatures under high workload, drawn from the HMS literature (Fig. 2). Table I presents the taxonomy in full.

![Fig. 2. Task taxonomy and expected HRV signatures across the seventeen OPI operator categories.](../05_figures/figure2_task_taxonomy_hrv_signatures.png)

**Fig. 2.** OPI task taxonomy. The seventeen task categories are grouped into manned-aviation (10) and UAS / teleoperator (7) blocks; each row indicates dominant performance demands and expected HRV-recovery and autonomic-reserve signatures under high workload. Manned-aviation categories include instrument flight under reduced visibility (IMC), night-vision operations, helmet-mounted-display flying, high-density air-traffic control, critical and non-critical emergencies, test-pilot operations, carrier landing, weapons delivery, and new-platform flight testing. UAS categories include intelligence-surveillance-reconnaissance, strike, search-and-rescue, autonomous-swarm supervisory control, contested-environment operations, ground-robot teleoperation, and subsea or long-latency teleoperation.

The taxonomy is not exhaustive and not mutually exclusive. Mission-level activity often transitions across categories within a single sortie, and the OPI pipeline is designed to be re-evaluated per-window as the active task category changes. Additional categories can be added by specifying their primary demands, failure modes, and weight profile following the template used throughout the taxonomy.

**TABLE I.** OPI task taxonomy and dominant failure modes (n = 17). Readiness bands apply uniformly: GO ≥ 85, GO-Monitor 70–84, CAUTION 55–69, NO-GO < 55.

| # | Task category | Block | Dominant failure mode |
|---|---|---|---|
| 1 | IMC instrument flying | Manned | Spatial disorientation; task saturation |
| 2 | Night-vision-device operations | Manned | Obstacle collision; misjudged clearance |
| 3 | Helmet-mounted-display flying | Manned | Target fixation; vestibular-visual conflict |
| 4 | High-density air-traffic control | Manned | Sequencing errors; missed communications |
| 5 | Critical emergency (immediate-action) | Manned | Decision paralysis; fixation errors |
| 6 | Non-critical emergency (abnormal/cautionary) | Manned | Checklist errors; sequence mistakes |
| 7 | Test-pilot operations | Manned | Unexpected dynamics; recovery failure |
| 8 | Carrier landing (CV/CVN) | Manned | Bolter; ramp strike |
| 9 | Weapons delivery | Manned | Fratricide; collateral damage |
| 10 | New-platform / new-weapons-platform testing | Manned | Mode confusion; incorrect inputs |
| 11 | UAS ISR (intelligence-surveillance-reconnaissance) | UAS | Vigilance decrement; missed events |
| 12 | UAS strike | UAS | Target misclassification; collateral damage |
| 13 | UAS SAR / CSAR | UAS | Situational-awareness breakdown |
| 14 | Autonomous-swarm supervisory control | UAS | Automation bias; exception-queue overflow |
| 15 | Contested-environment UAS operations | UAS | Dual-task interference |
| 16 | Ground-robot teleoperation | Teleop | Orientation errors; control reversals |
| 17 | Subsea / long-latency teleoperation | Teleop | Control-loop instability; autonomous handoff |

### 2.3 Per-task weight profiles

Per-task weight profiles for the seventeen categories are given in Table II. Weights reflect the theoretical dominance of particular OPI components in particular task contexts. Examples: in precision-motor-control tasks such as carrier landing the HRV-recovery component is weighted more heavily ($w_2 = 0.30$) because short-term vagal recovery has been linked to fine-motor precision; in critical-emergency tasks the autonomic-reserve component gains weight ($w_3 = 0.25$) because recovery capacity from acute stress drives sustained performance; in UAS supervisory control of multiple vehicles the attention-capacity component dominates ($w_4 = 0.30$) because sustained exception-handling depletes attentional resources [16]. The rationale column in Table II cites the source supporting each profile.

A task-complexity modifier $T_{\mathrm{mod}} \in [0.70, 1.00]$ applies multiplicatively to $\mathrm{SAFTE_{eff}}$ in the manned-aviation formulation and captures operational compounding. Compound modifiers multiply with a floor at 0.50 to prevent degenerate near-zero products. A stress penalty $P_{\mathrm{stress}} = 0.15 \max(0, S_{\mathrm{idx}} - 150)$, where $S_{\mathrm{idx}}$ is the Baevsky stress index, applies across all categories [1], and a learning-curve modifier applies to new-platform testing only (Table II).

**TABLE II.** OPI per-task component weights. Each manned row sums to $w_1{+}w_2{+}w_3 = 1$; each UAS/teleop row sums to $w_1{+}w_2{+}w_3{+}w_4 = 1$. Latency and multi-vehicle penalties apply additively after the weighted sum for UAS rows.

| # | Task | $w_1$ SAFTE | $w_2$ HRV-rec | $w_3$ Auto-res | $w_4$ Att-cap | Rationale (key reference) |
|---|---|:---:|:---:|:---:|:---:|---|
| 1 | IMC | 0.55 | 0.25 | 0.20 | — | Sustained cognitive load [10] |
| 2 | NVD | 0.50 | 0.25 | 0.25 | — | Visual + cognitive fatigue |
| 3 | HMD | 0.50 | 0.30 | 0.20 | — | Dual-task interference [15] |
| 4 | High-density ATC | 0.45 | 0.30 | 0.25 | — | Communication-stress load |
| 5 | Emergency (critical) | 0.40 | 0.35 | 0.25 | — | Acute stress + recovery |
| 6 | Emergency (non-critical) | 0.50 | 0.25 | 0.25 | — | Procedure execution |
| 7 | Test pilot | 0.45 | 0.30 | 0.25 | — | Uncertainty tolerance |
| 8 | Carrier landing | 0.50 | 0.30 | 0.20 | — | Precision motor control |
| 9 | Weapons delivery | 0.50 | 0.25 | 0.25 | — | Sustained attention + transient stress [18] |
| 10 | New-platform testing | 0.55 | 0.25 | 0.20 | — | Learning load |
| 11 | UAS ISR | 0.35 | 0.30 | 0.15 | 0.20 | Vigilance + discrete events [16] |
| 12 | UAS strike | 0.30 | 0.15 | 0.25 | 0.30 | Decision under threat |
| 13 | UAS SAR / CSAR | 0.30 | 0.20 | 0.25 | 0.25 | Multi-task SA |
| 14 | Swarm supervisory | 0.30 | 0.25 | 0.15 | 0.30 | Exception handling |
| 15 | Contested UAS | 0.30 | 0.20 | 0.25 | 0.25 | Dual-task threat monitoring |
| 16 | Ground teleop | 0.35 | 0.15 | 0.20 | 0.30 | Spatial transformation |
| 17 | Subsea / long-latency | 0.30 | 0.20 | 0.25 | 0.25 | Latency-dominated load |

Note: for UAS rows column $w_2$ is the vigilance-adjustment weight rather than HRV-recovery; HRV-recovery is in $w_3$ and attention-capacity in $w_4$. Task-complexity modifiers $T_{\mathrm{mod}}$ are applied separately (e.g., 0.95 / 0.90 / 0.85 for CAT I / II / III approaches; 0.85–1.00 for traffic-density tiers; 0.70 for critical multi-system emergencies).

### 2.4 Vigilance-decrement and control-latency models (UAS)

Two UAS-specific components have no analogue in manned aviation: the vigilance-decrement model for sustained monitoring and the control-latency penalty for teleoperation. Both are formalized in Table III.

The vigilance-decrement model follows Warm *et al.* [16]:

$$V_{\mathrm{cap}}(t) = (V_0 - V_{\min}) e^{-\lambda t} + V_{\min}, \tag{3}$$

with task-specific decay constants $\lambda \in [0.08, 0.15]\,\mathrm{h^{-1}}$ for high-event ISR, low-event ISR, multi-vehicle supervisory control, and ground teleoperation. Parameter values reflect the combined effects of sustained monitoring load and event rate and are theory-derived; operational field calibration is future work. Recommended maximum sortie durations are offered as planning heuristics rather than validated thresholds.

The control-latency penalty follows Chen *et al.* [17]:

$$P_{\mathrm{lat}} = \frac{1}{2}\ln\!\left(1 + \frac{\ell}{100\,\mathrm{ms}}\right), \tag{4}$$

where $\ell$ is round-trip control latency in milliseconds. The logarithmic form captures diminishing returns. A linear multi-vehicle penalty $P_{\mathrm{mv}} = 3(n_v - 1)$, where $n_v$ is the number of supervised vehicles, captures attentional sharing across swarm-control tasks.

**TABLE III.** UAS vigilance-decrement parameters and control-latency tiers.

| (a) Vigilance decay | $\lambda$ (h⁻¹) | $V_0$ | $V_{\min}$ | Planning sortie cap |
|---|:---:|:---:|:---:|:---:|
| High-event ISR | 0.08 | 100 | 70 | 2.0 h |
| Low-event ISR | 0.12 | 100 | 65 | 1.5 h |
| Multi-vehicle supervisory | 0.15 | 100 | 60 | 1.0 h |
| Ground teleoperation | 0.10 | 100 | 70 | 1.5 h |

| (b) Latency tier $\ell$ (ms) | $P_{\mathrm{lat}}$ | Recommended control strategy |
|---|:---:|---|
| < 100 | ≈ 0 | Direct teleoperation |
| 100 – 300 | 0.35 – 0.69 | Anticipatory control |
| 300 – 700 | 0.69 – 1.05 | Move-and-wait control |
| 700 – 1500 | 1.05 – 1.39 | Supervisory-control shift |
| > 1500 | > 1.39 | Autonomous handoff recommended |

### 2.5 Reference implementation

The reference implementation is distributed under the MIT license at `https://github.com/strikerdlm/HRV` (frozen Zenodo DOI to be cited in the camera-ready). The architecture separates client delivery from model execution while keeping the computational core as a single Python stack. A web client communicates with a FastAPI orchestration layer that exposes structured endpoints for HRV analysis, scheduling and readiness, user-profile management, and research utilities. The shared analytic core hosts the HRV engine, SAFTE reservoir model, readiness-fusion logic, Psychomotor Vigilance Task (PVT) module, sleep-analytics module, and longitudinal trajectory-risk module. Architecture and module manifests are provided in Supplement S1.

The HRV engine computes time-domain metrics (RMSSD, SDNN, pNN50), frequency-domain metrics (VLF, LF, HF power; LF/HF ratio), and nonlinear metrics (SD1, SD2, sample entropy, DFA-α1, Poincaré ellipse area, Baevsky stress index) from RR-interval series, with bounded artefact heuristics and linear interpolation for invalid samples. Outputs feed the $\mathrm{HRV_{rec}}$, $\mathrm{Auto_{res}}$, and $\mathrm{Att_{cap}}$ components through documented normalization functions. External numerical benchmarking against reference packages such as Kubios, pyHRV, and NeuroKit2 is out of scope for this manuscript and is stated as future work.

Three modules concretize the operational path from physiological input to composite readiness. The **PVT module** administers and scores three validated variants — PVT-B (3 min, 355 ms lapse threshold) [21], PVT-5, and PVT-10 [22] — through a browser surface (≈5–10 ms timing precision) [23] and a PsychoPy desktop driver for sub-millisecond research sessions [24]. PVT lapses feed the readiness-fusion layer with a ≥20-lapse hard gate. The **sleep module** derives sleep debt (rolling 7-night cumulative deficit), the Sleep Regularity Index [26], stage-balance proportions, and a four-band low-SpO₂ screening proxy (not a clinical apnea classification); the module surfaces consumer-wearable bounds against polysomnography [27], [28] at every visualization, with research-grade ground truth supplied by ActiGraph wGT3X-BT recordings [29]. The **trajectory-risk module** maintains exponentially weighted moving averages of OPI, $\mathrm{SAFTE_{eff}}$, and $\mathrm{HRV_{rec}}$ and exposes a bounded cumulative-strain modifier aligned with the allostatic-load construct [19].

### 2.6 Worked-example methodology

A single 128-minute HRV recording (8553 RR intervals, 0.047 % quality-flagged windows) collected in November 2025 was used to anchor an illustrative worked example. For the public worked-example artefact, recording-level summary statistics were used to generate representative five-minute windowed HRV metrics with realistic variability rather than re-parsing a raw RR-interval file; representative windows were combined with a rested-baseline SAFTE trajectory and the OPI fusion logic under three task hypotheses: a CAT II instrument landing system (ILS) approach (manned-aviation category 1), a two-hour UAS intelligence-surveillance-reconnaissance (ISR) sortie (UAS category 11), and a daytime carrier recovery (manned-aviation category 8). For each hypothesis the full OPI time series was computed per window and mapped to the readiness categories defined in Table I. This worked example is a framework-instantiation demonstration: it shows how the same summary-consistent physiological input yields different composite outputs when the active task category changes. It does not test whether the OPI predicts operator outcomes and does not generalize beyond a single-recording illustration.

---

## 3. Results

### 3.1 Illustrative worked example: framework instantiation across three task hypotheses

Fig. 3 presents per-window OPI time series for the three task hypotheses computed across eighty representative five-minute windows spanning the 128-minute recording duration. The three hypotheses produced substantively different composite distributions from identical summary-consistent physiological input.

Under the **CAT II ILS approach** ($w_1{=}0.55$, $w_2{=}0.25$, $w_3{=}0.20$, $T_{\mathrm{mod}}{=}0.90$), the composite varied between **48.9 and 63.7** (mean 55.9, SD 3.7) and was classified in the **CAUTION** band (55–69) for 58.8 % of windows and in the **NO-GO** band ($<55$) for 41.2 % of windows. No window reached the **GO** or **GO (Monitor)** bands, reflecting the combined effect of the Category II complexity modifier, the dominance of the SAFTE component under moderate baseline effectiveness, and the stress-index penalty in higher-arousal windows.

Under the **UAS ISR 2-hour sortie** ($w_1{=}0.35$, $w_2{=}0.30$, $w_3{=}0.15$, $w_4{=}0.20$; Warm decay with $\lambda{=}0.12\,\mathrm{h^{-1}}$, $V_0{=}100$, $V_{\min}{=}65$; latency penalty at 120 ms datalink; single vehicle), the composite was higher overall, varying between **64.1 and 81.8** (mean 72.4, SD 4.4), with **66.2 %** of windows classified as **GO (Monitor)** and the remaining **33.8 %** as **CAUTION**. The composite showed a visible downward drift as simulated time-on-task approached two hours, consistent with the Warm vigilance decrement. No window reached **GO** ($\geq 85$) and none reached **NO-GO**.

Under the **carrier-landing** hypothesis ($w_1{=}0.50$, $w_2{=}0.30$, $w_3{=}0.20$, $T_{\mathrm{mod}}{=}0.85$ to reflect CVN deck motion and short-final demands), the composite was systematically lower, varying between **42.6 and 58.3** (mean 50.3, SD 4.1), with **86.2 %** of windows classified as **NO-GO** and the remaining **13.8 %** as **CAUTION**. The complexity modifier combined with the moderate RMSSD-derived $\mathrm{HRV_{rec}}$ in the recording produced the most stringent task-specific assessment of the three hypotheses.

The central observation, addressing **RQ1**, is that the same summary-consistent physiological input yielded composite distributions differing in central tendency (mean OPI 55.9 vs. 72.4 vs. 50.3) and in category allocation (0 % / 33.8 % / 86.2 % NO-GO). This is consistent with the MRT-derived weight-profile design intent and demonstrates that a task-calibrated composite exposes task-specific readiness information that a task-agnostic composite would collapse. The illustrative numerical outputs are framework-instantiation values only; they do not reflect the readiness state of any operator performing any of the three tasks, because the recording was collected from a single individual in a non-operational context.

![Fig. 3. Per-window OPI time series for three task hypotheses from one 128-minute recording.](tex/figures/figure3_opi_worked_example.pdf)

**Fig. 3.** Per-window Operational Performance Indicator (OPI) composite scores for three task hypotheses (CAT II ILS approach, UAS ISR 2-hour sortie, carrier landing) computed from identical physiological input across eighty 5-minute windows.

### 3.2 Engineering verification of the OPI fusion pathway

Engineering verification of the reference implementation covers the major tested paths through the OPI pipeline at the software level. Automated tests exercise scheduling-core readiness fusion, fatigue-risk-management behavior, SAFTE-adjacent logic, API endpoint normalization, and broader statistical and charting modules. The PVT and sleep reference modules are covered by dedicated test suites: 28 PVT tests across trial classification, alert- and fatigued-session metrics, variant scaling, edge cases, and the operational gate; and 27 sleep tests across stage balance, sleep-debt scaling, Sleep Regularity Index behavior, SpO₂ screening bands, operational-gate escalation, and the correlation engine with Benjamini-Hochberg FDR adjustment. The longitudinal trajectory-risk module is implemented and documented but is not yet covered by dedicated regression tests; the UAS Warm/Chen formulations are formalized in framework artefacts and instantiated in the worked-example script rather than exposed as a separately tested operational API pathway. A summary coverage row is given in Table IV; the full coverage matrix appears in Supplement S2.

These tests justify reporting that the readiness fusion, orchestration, PVT, and sleep layers are implemented and regression-tested at the software level. They do not establish operational validation, clinical deployment readiness, or numerical equivalence of the HRV engine to external reference packages.

**TABLE IV.** Engineering-verification coverage by OPI fusion-pathway layer (summary). Full per-test coverage matrix: Supplement S2.

| Layer | Status | Manuscript-safe interpretation |
|---|---|---|
| HRV analytic core | Implemented; endpoint-tested | Numerics implemented and integrated; not externally benchmarked |
| SAFTE / circadian | Implemented; integration-tested | Fatigue-governance layer present; not outcome-validated |
| Readiness fusion / scheduling | Implemented; regression-tested | Threshold logic and score composition behave deterministically |
| PVT module | Implemented; regression-tested | Three variants and operational gate verified |
| Sleep module | Implemented; regression-tested | Debt, SRI, screening bands, gate, correlation engine verified |
| Trajectory-risk module | Implemented; not yet covered | Do not frame as regression-tested |
| API delivery | Endpoint-tested | Profile and windowed pathways exercised |

### 3.3 Reproducibility

The reference implementation is distributed under the MIT license. The documented primary execution environment is Python 3.12 with dependencies declared in `requirements.txt`; the primary client is a Next.js / TypeScript application. The repository supports structured logging, cached environmental-data management, and export utilities designed to emit manuscript-oriented statistics and supporting artefacts. A tagged release with archived Zenodo DOI will be cited in the camera-ready as the frozen identifier for the reported version. These reproducibility characteristics are consistent with published guidance for reproducible computational research [33].

---

## 4. Discussion

### 4.1 Principal contribution

The principal contribution of this manuscript is neither a new physiological marker nor a new machine-learning classifier but a deliberately simple, theoretically grounded substrate for aerospace operator-readiness decisions: the OPI — a linear weighted composite whose per-task weight profiles, Warm-type vigilance-decrement model, Chen-type control-latency penalty, operational gate thresholds, and reference-implementation modules are specified in the open and distributed as inspectable code. The framework is positioned as an inspectable input substrate for downstream human-machine teaming workflows, supporting the system test and evaluation activities that are central to aerospace operator-loop integration. Its simplicity is a design choice, not a limitation of method: the composite is intended to be audited line by line by safety reviewers, extended by domain experts without re-training, and calibrated against operator outcomes using modest-sample-size Bayesian hierarchical or penalized-regression studies.

### 4.2 Comparison with adjacent frameworks

Several recent frameworks are adjacent to the OPI but differ in important ways. Feng *et al.* [10] proposed an MRT-grounded multinomial logistic regression combining fixation-frequency, ECG, and electrodermal features for pilot workload across three flight phases (cruise, approach, landing), with reported discrimination accuracy of 84.85 %. The Feng framework validates the principle of MRT + physiological fusion but covers only three phases of one aircraft type, includes no fatigue model, and is distributed as a study result rather than as reusable software. The OPI extends this line of work to seventeen operator task categories, incorporates SAFTE fatigue dynamics, and ships as open-source reference code.

Stevens *et al.* [11] used Cognitive Metrics Profiling to link a cognitive model to physiological workload in a single unmanned-vehicle control task. Vogl *et al.* [12] developed individualized support-vector-machine classifiers of cognitive workload from ECG and pupillometry in a low-fidelity aviation simulator with three participants, reporting 70–80 % binary classification accuracy. Their work is complementary: the OPI can serve as a calibration layer under which classifiers like the Vogl model are trained on particular operator populations. Li *et al.* [13] systematically reviewed machine-learning approaches for UAS operator cognitive load and explicitly identified the absence of unified frameworks integrating physiological signals, biomathematical fatigue, and task-specific weighting as a research gap. The OPI as proposed addresses that gap directly. Hamann *et al.* [9] reviewed cockpit mental-fatigue assessment using head-worn sensing and concluded that mature methods exist but are not yet operationally deployable; the OPI is consistent with that conclusion and accommodates head-worn signals as additional inputs to the $\mathrm{Att_{cap}}$ component where available. Rabat *et al.* [20] called specifically for "an infrastructure for physiological monitoring and integrated analyses" combined with explainable and interpretable modeling — the OPI is a concrete instance of that infrastructure.

### 4.3 Theoretical grounding and the case for principled simplicity

The OPI's linear structure and per-task weighting reflect three theoretical commitments: MRT predicts task-specific demand profiles [14], [15]; the allostatic-load framework [19] distinguishes acute stress (captured by the stress penalty) from cumulative regulatory strain (captured by $\mathrm{HRV_{rec}}$ and $\mathrm{Auto_{res}}$); and situation-awareness theory [18] motivates the dedicated attention-capacity component for UAS supervisory-control tasks. The composite leverages this evidence directly rather than reconstructing it from data.

The deliberate use of a linear composite in an era of machine-learning ascendancy reflects four structural constraints of aerospace HMS engineering. Labeled outcome data are scarce; a single squadron rarely produces the tens of thousands of labeled sorties modern classifiers require. Populations are small and heterogeneous across platforms; classifiers trained on one transfer poorly to another [12]. Sensor generations change faster than training cycles. And the cost function is dominated by safety review: an unexplainable automated NO-GO cannot be approved by a safety board or defended after an incident.

Against these constraints, a linear composite with theory-derived weights is **inspectable** (every gate decision decomposes into named contributions), **extensible** (new task categories specified through demand analysis without training data), **calibratable** on modest samples via penalized regression or Bayesian hierarchical modeling, and **falsifiable** at the level of individual per-task weight profiles. The framework does not reject classifiers; it positions them as downstream refinements that locally tune the composite under specified conditions, while the overall HMS-substrate structure remains auditable. This addresses **RQ3** at the design-rationale level; an empirical comparison against opaque classifiers on matched datasets is identified as future work in Section 4.6.

### 4.4 Strengths

The OPI is theoretically grounded in multiple HMS and human-factors constructs with clearly cited source literature. It spans both manned aviation and UAS — two populations usually treated in separate research communities — and ships with an open-source reference implementation under the MIT license, enabling independent verification and extension. The reference implementation includes an in-platform PVT module, an actigraphy-backed sleep module, and a longitudinal trajectory-risk module, which together concretize the vigilance, fatigue, and cumulative-strain inputs to the composite as inspectable code rather than external dependencies. The evidence posture is explicitly tiered, distinguishing what is demonstrated (framework, implementation, engineering verification, illustrative example) from what remains to be validated (per-task weight calibration, operator-outcome prediction, numerical parity with external HRV packages).

### 4.5 Limitations

The most important limitation is that **per-task OPI weights are theory-derived, not empirically calibrated** against operator performance; specific values for $w_1$–$w_4$ represent one of a larger family of plausible profiles, with empirical selection pending (Section 4.6, **RQ2**). The illustrative worked example uses a single HRV recording in a non-operational context and demonstrates framework instantiation rather than operational validity; the public artefact relies on representative five-minute windows generated from recording-level summary statistics. The HRV engine produces standards-aligned metrics with internal verification but is not externally benchmarked against Kubios or comparable tools. The vigilance-decrement and control-latency parameters [16], [17] may require recalibration for modern UAS platforms with advanced autonomy or degraded links. The platform is not a certified medical device; references to ICAO Doc 9966 and NASA-STD-3001 are alignment, not certification [34], [35]. The sleep-analytics layer in consumer-wearable mode inherits the meaningful disagreement against polysomnography reported across consumer devices [27], [28]; operational-mode use is therefore bounded to pattern-level tracking, with low-nocturnal-SpO₂ night counts surfaced as a screening proxy rather than a clinical apnea diagnosis.

### 4.6 Validation roadmap

The most immediate next step, addressing **RQ2**, is a planned prospective field validation during the 2026–2027 Colombian Antarctic aerial campaign on a Colombian Air Force C-130 Hercules. Consenting crew will wear the ActiGraph wGT3X-BT for sleep and activity ground truth [29] and the Polar H10 chest-strap electrocardiogram during structured daily HRV windows and mission task blocks [30]–[32]. Longitudinal OPI trajectories, PVT lapses, Sleep Regularity Index, cumulative sleep debt, and trajectory-risk EWMA series will be analyzed with penalized regression or Bayesian hierarchical models to refine per-task weight profiles for extended-endurance, over-water, and instrument-flight categories against performance and self-reported workload benchmarks. Sensitivity analysis across weight families will quantify how much the specific theory-derived values matter relative to the structure of the composite. The campaign protocol is the subject of a separate publication.

A second priority is external numerical benchmarking of the HRV engine against reference implementations on standard test datasets (e.g., MIT-BIH Normal Sinus Rhythm), producing intraclass correlation coefficients and Bland-Altman limits of agreement for time-domain, frequency-domain, and nonlinear metrics. A third priority, addressing **RQ3**, is comparative benchmarking against opaque classifier baselines on matched datasets — Stevens *et al.* [11] and Vogl *et al.* [12] provide comparator systems whose outputs can be replicated and scored against the same ground truth used to calibrate the OPI. A fourth priority is a prospective pilot study in a well-characterized manned-aviation or UAS training population with ethics approval and a pre-specified analysis plan.

---

## 5. Conclusions

The Operational Performance Indicator framework offers a theoretically grounded, task-calibrated alternative to fatigue-only composites, HRV-only analyses, and machine-learning operator-state classifiers. The framework covers both manned-aviation and UAS operator categories, ships as open-source reference code under the MIT license, and is supported by engineering verification across its fusion pathway. The present manuscript is bounded to framework definition, reference implementation, and illustrative demonstration; empirical calibration of per-task weights, external numerical benchmarking of the HRV engine, and prospective field validation in operator populations are the next research steps. The framework is designed to be extensible by domain experts without retraining, positioning it as an inspectable HMS substrate for iterative operational deployment and downstream classifier hybridization rather than as a closed analytic end-product.

---

## 6. Compliance and Transparency

### 6.1 Data availability

No new human-subject dataset was generated for the framework-definition and engineering-verification components reported in this manuscript. The single 128-minute HRV recording used to anchor the illustrative worked example is available from the corresponding author on reasonable request as a de-identified illustrative dataset. The public repository contains the derived JSON artefact and reproduction script for the worked example.

### 6.2 Code and artefact availability

The reference implementation is available as open-source software at `https://github.com/strikerdlm/HRV` under the MIT license. The primary execution environment is Python 3.12 with dependencies declared in `requirements.txt`; the primary client is a Next.js / TypeScript application. A tagged release and archived Zenodo DOI corresponding to the reported version will be cited in the camera-ready.

### 6.3 Ethics

Ethics approval and informed consent were not required for the framework-definition and engineering-verification components because no new human-subject dataset was generated or analyzed. The single illustrative HRV recording was contributed by the corresponding author for framework-demonstration purposes and is presented only as de-identified illustrative material. The platform is not presented as a certified medical device or regulated decision-support system. Operational modules were designed with reference to NASA-STD-3001 human-systems standards [35] and ICAO Doc 9966 fatigue-management guidance [34]; these references inform design and threshold logic but do not constitute certification or regulatory clearance.

### 6.4 Author contributions (CRediT)

**Diego L. Malpica:** Conceptualization; Methodology; Software; Formal analysis; Investigation; Writing — original draft; Writing — review & editing; Visualization; Supervision; Project administration. **Ingrid Xiomara Bejarano Cifuentes:** Investigation; Writing — review & editing; Resources.

### 6.5 Funding and competing interests

This research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit sectors. The authors declare no competing financial or non-financial interests related to this manuscript.

---

## Acknowledgements

The authors acknowledge the open-source scientific Python ecosystem, DIMAE and CITAE within the Colombian Aerospace Force, and the human-factors and human-machine systems research communities whose foundational work on Multiple Resource Theory, vigilance, teleoperation, fatigue modeling, and situation awareness provides the theoretical basis for this framework.

---

## Declaration of generative AI and AI-assisted technologies in the manuscript preparation process

During the preparation of this work the authors used AI-assisted technologies (large language-model-based drafting, editing, literature cross-checking, and formatting workflows under human oversight). After using these tools, the authors reviewed and edited the content as needed and take full responsibility for the content of the manuscript.

---

## References

[1] F. Shaffer and J. P. Ginsberg, "An overview of heart rate variability metrics and norms," *Front. Public Health*, vol. 5, p. 258, 2017.

[2] K. S. Quigley, P. J. Gianaros, G. J. Norman, J. R. Jennings, G. G. Berntson, and E. J. C. de Geus, "Publication guidelines for human heart rate and heart rate variability studies in psychophysiology — Part 1: Physiological underpinnings and foundations of measurement," *Psychophysiology*, vol. 61, no. 9, p. e14604, 2024.

[3] D. B. Forger, M. E. Jewett, and R. E. Kronauer, "A simpler model of the human circadian pacemaker," *J. Biol. Rhythms*, vol. 14, no. 6, pp. 533–538, 1999.

[4] S. R. Hursh, T. J. Balkin, J. C. Miller, and D. R. Eddy, "The Fatigue Avoidance Scheduling Tool: Modeling to minimize the effects of fatigue on cognitive performance," SAE Tech. Paper Ser. 2004-01-2151, 2004.

[5] J. K. Devine *et al.*, "Predictive biomathematical modeling compared to objective sleep during COVID-19 humanitarian flights," *Aerosp. Med. Hum. Perform.*, vol. 93, no. 1, pp. 4–12, 2022.

[6] A. Pontiggia *et al.*, "MATB for assessing different mental workload levels," *Front. Physiol.*, vol. 15, p. 1408242, 2024.

[7] R. Houghton, A. Martinetti, and A. Majumdar, "A framework for selecting and assessing wearable sensors deployed in safety critical scenarios," *Sensors*, vol. 24, no. 14, p. 4589, 2024.

[8] K. Jin, A. Rubio-Solis, R. Naik, D. Leff, J. Kinross, and G. Mylonas, "Human-centric cognitive state recognition using physiological signals: A systematic review of machine learning strategies across application domains," *Sensors*, vol. 25, no. 13, p. 4207, 2025.

[9] A. Hamann *et al.*, "The state of the art in assessing mental fatigue in the cockpit using head-worn sensing technology," *Front. Neuroergon.*, vol. 6, p. 1673268, 2026.

[10] C. Feng, X. Wanyan, K. Yang, D. Zhuang, and X. Wu, "A comprehensive prediction and evaluation method of pilot workload," *Technol. Health Care*, vol. 26, no. S1, pp. 65–78, 2018.

[11] C. A. Stevens, M. B. Morris, C. R. Fisher, and C. W. Myers, "Profiling cognitive workload in an unmanned vehicle control task with cognitive models and physiological metrics," *Mil. Psychol.*, vol. 35, no. 6, pp. 507–520, 2022.

[12] J. Vogl, K. O'Brien, and P. St. Onge, "One size does not fit all: A support vector machine exploration of multiclass cognitive state classifications using physiological measures," *Front. Neuroergon.*, vol. 6, p. 1566431, 2025.

[13] Q. Li, O. Molloy, H. El-Fiqi, and G. Eves, "Applications of machine learning in assessing cognitive load of uncrewed aerial system operators and in enhancing training: A systematic review," *Drones*, vol. 9, no. 11, p. 760, 2025.

[14] C. D. Wickens, "Multiple resources and performance prediction," *Theor. Issues Ergon. Sci.*, vol. 3, no. 2, pp. 159–177, 2002.

[15] C. D. Wickens, "Multiple resources and mental workload," *Hum. Factors*, vol. 50, no. 3, pp. 449–455, 2008.

[16] J. S. Warm, R. Parasuraman, and G. Matthews, "Vigilance requires hard mental work and is stressful," *Hum. Factors*, vol. 50, no. 3, pp. 433–441, 2008.

[17] J. Y. C. Chen, E. C. Haas, and M. J. Barnes, "Human performance issues and user interface design for teleoperated robots," *IEEE Trans. Syst., Man, Cybern. C, Appl. Rev.*, vol. 37, no. 6, pp. 1231–1245, Nov. 2007.

[18] M. R. Endsley, "Toward a theory of situation awareness in dynamic systems," *Hum. Factors*, vol. 37, no. 1, pp. 32–64, 1995.

[19] B. S. McEwen, "Protective and damaging effects of stress mediators," *N. Engl. J. Med.*, vol. 338, no. 3, pp. 171–179, 1998.

[20] A. Rabat *et al.*, "Fatigue and management of warfighter mental endurance," *BMJ Mil. Health*, vol. 171, no. 5, pp. 447–451, 2025.

[21] M. Basner and D. F. Dinges, "Maximizing sensitivity of the Psychomotor Vigilance Test (PVT) to sleep loss," *Sleep*, vol. 34, no. 5, pp. 581–591, 2011.

[22] D. F. Dinges *et al.*, "Cumulative sleepiness, mood disturbance, and psychomotor vigilance performance decrements during a week of sleep restricted to 4–5 hours per night," *Sleep*, vol. 20, no. 4, pp. 267–277, 1997.

[23] A. Anwyl-Irvine, E. S. Dalmaijer, N. Hodges, and J. K. Evershed, "Realistic precision and accuracy of online experiment platforms, web browsers, and devices," *Behav. Res. Methods*, vol. 53, no. 4, pp. 1407–1425, 2020.

[24] P. Garaizar and M. A. Vadillo, "Accuracy and precision of visual stimulus timing in PsychoPy: No timing errors in standard usage," *PLoS ONE*, vol. 9, no. 11, p. e112033, 2014.

[25] D. A. Grant, K. A. Honn, M. E. Layton, S. M. Riedy, and H. P. A. Van Dongen, "3-minute smartphone-based and tablet-based psychomotor vigilance tests for the assessment of reduced alertness due to sleep deprivation," *Behav. Res. Methods*, vol. 49, no. 3, pp. 1020–1029, 2017.

[26] J. R. Lunsford-Avery, M. M. Engelhard, A. M. Navar, and S. H. Kollins, "Validation of the Sleep Regularity Index in older adults and associations with cardiometabolic risk," *Sci. Rep.*, vol. 8, p. 14158, 2018.

[27] Y. J. Lee, J. Y. Lee, J. H. Cho, Y. J. Kang, and J. H. Choi, "Performance of consumer wrist-worn sleep tracking devices compared to polysomnography: A meta-analysis," *J. Clin. Sleep Med.*, vol. 21, no. 3, pp. 573–582, 2025.

[28] A.-M. Schyvens *et al.*, "Accuracy of Fitbit Charge 4, Garmin Vivosmart 4, and WHOOP versus polysomnography: Systematic review," *JMIR mHealth uHealth*, vol. 12, p. e52192, 2024.

[29] D. S. Buchan, "Comparison of sleep and physical activity metrics from wrist-worn ActiGraph wGT3X-BT and GT9X accelerometers during free-living in adults," *J. Meas. Phys. Behav.*, vol. 7, no. 1, 2024.

[30] R. A. Pereira, J. L. B. Alves, J. H. C. Silva, M. S. Costa, and A. S. Silva, "Validity of a smartphone application and chest strap for recording RR intervals at rest in athletes," *Int. J. Sports Physiol. Perform.*, vol. 15, no. 6, pp. 896–899, 2020.

[31] K. Hinde, G. White, and N. Armstrong, "Wearable devices suitable for monitoring twenty-four-hour heart rate variability in military populations," *Sensors*, vol. 21, no. 4, p. 1061, 2021.

[32] J. Yang and E. Ben-Menachem, "Accuracy and clinical utility of heart rate variability derived from a wearable heart rate monitor in patients undergoing major abdominal surgery," *J. Clin. Monit. Comput.*, vol. 38, no. 2, pp. 433–443, 2024.

[33] G. K. Sandve, A. Nekrutenko, J. Taylor, and E. Hovig, "Ten simple rules for reproducible computational research," *PLoS Comput. Biol.*, vol. 9, no. 10, p. e1003285, 2013.

[34] International Civil Aviation Organization, *Manual for the Oversight of Fatigue Management Approaches (Doc 9966)*, 2nd ed., Version 2 (revised). Montréal, Canada: ICAO, 2020.

[35] National Aeronautics and Space Administration, *NASA Spaceflight Human-System Standard, Volume 1: Crew Health (NASA-STD-3001, Vol. 1, Rev. C)*. Washington, DC, USA: NASA, 2023.
