# PhD Thesis Proposal (Literature-Backed Draft)

**Working title**: *Mission‑Ready Physiology: Multimodal Readiness Classification and Risk‑Based Go/No‑Go Decision Support for Military Aviation and Aerospace Command Operations*

**Scope**: This is a dissertation-level research concept aligned with the “Mission Control – Flight Surgeon” platform in this repository (HRV + fatigue/circadian + wearable ingestion + operational context). It is **not** an aeromedical policy document and **not** personal medical advice.

---

## 1) Executive summary

High‑consequence aviation and aerospace operations routinely expose pilots/commanders to **sleep restriction, circadian misalignment, prolonged wakefulness, high workload, and stress**. These exposures reliably degrade vigilant attention and decision quality—often with imperfect subjective awareness—creating avoidable operational risk.

This thesis proposes a **readiness qualification system** that fuses:

- **Fatigue physiology and prediction** (sleep history, time awake, biomathematical models such as SAFTE-family),
- **Circadian state** (timing, phase-shift risk, circadian low),
- **Objective neurobehavioral performance** (vigilance/psychomotor testing),
- **Autonomic regulation markers** (short‑term HRV features anchored to within‑person baselines),
- **Operational context** (mission severity, workload, environmental stressors),

into a **calibrated probability of near‑term impairment** that is mapped to a **5×5 Likelihood × Severity risk matrix** with explicit mitigations (sleep, naps, light, caffeine; and—where permitted—pharmacologic countermeasures under aeromedical governance).

---

## 2) Core scientific basis (what predicts operational performance reliably)

### 2.1 Strongest, most consistent predictor class: sleep loss and time awake
Across laboratory and operationally relevant studies, both **total sleep deprivation** and **chronic partial sleep restriction** produce dose‑response degradation in neurobehavioral performance (especially vigilant attention) and can accumulate over days (Van Dongen et al., 2003; Belenky et al., 2003). Prolonged wakefulness can impair performance comparably to alcohol intoxication in controlled demonstrations (Dawson & Reid, 1997).

### 2.2 Objective vigilance testing: direct measurement of the failure mode
For aviation safety, the critical “failure mode” is often **lapses of attention**, slowed response speed, and degraded sustained attention under monotony and time‑on‑task. The psychomotor vigilance family of measures is widely used to quantify these changes; modern work emphasizes measurement precision and repeatability in PVT metrics (Basner et al., 2021).

### 2.3 Biomathematical models: useful forecasting, not self-sufficient
Biomathematical fatigue models are intended for applied settings (including warfighting) and provide a structured forecast from sleep/wake history and circadian timing (Hursh et al., 2004). Their operational value depends on calibration, appropriate inputs, and validation against objective performance—not on face validity.

### 2.4 Circadian misalignment: performance risk is time-locked
Circadian misalignment contributes to fatigue risk and performance decrements and can be mitigated by strategically timed light and melatonin cues (Smith & Eastman, 2012; Burke et al., 2013). Broad reviews emphasize that shift work/jet lag countermeasures must address both **sleep opportunity** and **circadian phase**.

### 2.5 HRV: plausible readiness adjunct if baseline‑anchored and protocol‑controlled
Short‑term HRV is a window into autonomic regulation; it is sensitive to training load, illness, stress, sleep, and breathing protocol. It is most defensible in readiness when treated as a **within‑person signal** (rolling baselines, deltas, and trends) rather than a population-only classification. Standards and reporting requirements are well established (Task Force, 1996; Shaffer & Ginsberg, 2017; Laborde et al., 2017), and sports/operational monitoring literature supports baseline‑anchored HRV as a practical marker of adaptation and strain (Plews et al., 2013).

### 2.6 Stimulants and “enhancers”: evidence exists, governance is decisive
Operational fatigue countermeasures include non‑pharmacologic strategies (naps, scheduling, light) and, in some military contexts, tightly governed pharmacologic options. Reviews and trials in aviators/operational environments evaluate **dextroamphetamine** and **modafinil** (Caldwell & Caldwell, 2005; Caldwell & Caldwell, 1997; Caldwell et al., 2003; Caldwell et al., 2004; Estrada et al., 2012). Caffeine remains a widely used countermeasure; multiple-dose strategies can sustain vigilance during extended wakefulness (Killgore & Kamimori, 2020), and combined “caffeine‑nap” strategies are under active study (Centofanti et al., 2020).

---

## 3) Central thesis statement

A **multimodal, baseline‑anchored, risk‑calibrated** readiness model combining (i) sleep/fatigue forecasting, (ii) circadian state, (iii) objective vigilance testing, and (iv) HRV/autonomic markers can provide **more accurate and operationally actionable** go/no‑go decision support for pilots/commanders than single‑modality gates (self‑report alone, sleep duration alone, or HRV alone), while preserving interpretability necessary for aerospace medicine oversight.

---

## 4) Research questions, hypotheses, and objectives

### 4.1 Research questions
1. **Prediction**: Which combination of physiological (HRV), sleep/fatigue, circadian, and objective cognitive predictors best estimates **near‑term operational impairment** (0–24 h) in pilots/commanders?
2. **Calibration and utility**: Can predicted impairment probabilities be **calibrated** and mapped to a 5×5 risk matrix that improves decision utility (e.g., reduces high‑risk exposures) compared to current practice?
3. **Generalization**: How well do models trained on controlled/simulator contexts generalize to field duty cycles?
4. **Countermeasure effects**: Which mitigations reduce modeled risk category while maintaining safety (side effects, sleep inertia, rebound fatigue)?

### 4.2 Hypotheses (testable)
- **H1**: Sleep history + time awake + circadian phase predictors will account for the largest share of variance in objective impairment.
- **H2**: Adding a brief objective vigilance measure will significantly improve prediction and calibration beyond sleep-only models.
- **H3**: HRV baseline deviations (e.g., lnRMSSD delta from rolling baseline) will improve classification in subgroups/contexts (e.g., stress/illness, high workload), but will be insufficient as a standalone gate.
- **H4**: Countermeasure-aware decision logic will yield better utility (decision‑curve analysis) than raw risk predictions.

### 4.3 Objectives (deliverables)
- **O1**: A longitudinal multimodal dataset of pilots/commanders with standardized HRV recordings, sleep metrics, circadian descriptors, and repeated objective performance testing.
- **O2**: A validated readiness classifier producing a calibrated probability of impairment and uncertainty estimates.
- **O3**: A 5×5 operational risk matrix implementation with explicit mitigations and escalation rules.
- **O4**: Prospective validation in simulator and field duty cycles.
- **O5**: Governance artifacts: model card, data dictionary, decision audit trail design, fairness and misuse assessments.

---

## 5) Operational definition of “readiness” (outcomes)

### 5.1 Primary outcome
**Near‑term performance impairment (0–24 h)** defined via objective endpoints:
- Degradation in vigilant attention (reaction time distribution, lapses).
- Simulator performance decrement (procedural errors, tracking, comms accuracy) where available.

### 5.2 Secondary outcomes
- Safety-critical error proxies and near‑miss events where recordable.
- Subjective fatigue/sleepiness (supportive, not decisive).

---

## 6) Predictors (candidate variable set) and measurement principles

### 6.1 Measurement principles
- **Within‑person baselines first**: readiness is primarily a deviation-from-normal problem.
- **Protocol control**: posture, time-of-day, breathing protocol, recent exertion, stimulants.
- **Quality gates**: artifact %, ectopy flags, missingness modeling.

### 6.2 HRV/autonomic predictors (short-term)
- Time domain: lnRMSSD/RMSSD; short‑term SDNN; pNN50 (with caution).
- Nonlinear: SD1; DFA α1 (if measurement length supports it).
- QC: artifact rate and stability indicators.

Key rationale: HRV standards and reporting are foundational (Task Force, 1996; Shaffer & Ginsberg, 2017; Laborde et al., 2017), and baseline‑anchored monitoring literature supports lnRMSSD/RMSSD in daily readiness contexts (Plews et al., 2013; Plews et al., 2014).

### 6.3 Sleep/fatigue predictors
- Sleep duration/efficiency; multi-night sleep debt.
- Time awake; prior-day schedule.
- SAFTE-family effectiveness forecast (Hursh et al., 2004).

### 6.4 Circadian predictors
- Circadian phase proxies (chronotype + schedule; optionally light exposure proxies).
- Night operations indicator; circadian low proximity.
- Phase shift interventions where used (Smith & Eastman, 2012; Burke et al., 2013).

### 6.5 Objective performance predictors
- Brief vigilance/psychomotor testing.
- Repeated measures to quantify vulnerability and learning effects.

### 6.6 Operational context predictors
- Mission demand category, expected duration, time‑on‑task.
- Environmental stressors (heat, hypoxia training days, high‑G days).

---

## 7) Study design (recommended doctoral program)

### 7.1 Phase A — Baseline, reliability, and protocol validation (4–8 weeks)
- Daily morning HRV (standardized).
- Nightly sleep capture.
- Brief objective performance test 3–5×/week.

Outputs: reliability estimates, minimal detectable change, baseline establishment rules.

### 7.2 Phase B — Controlled operational stressors (simulator + duty-cycle analogs)
Within-subject, counterbalanced blocks:
- Partial sleep restriction and/or extended wakefulness under supervision.
- Night‑shift/circadian misalignment conditions.
- Standardized simulator sortie profiles.

Outputs: effect sizes, feature sensitivity, countermeasure response characterization.

### 7.3 Phase C — Prospective field validation
Observational cohort across real duty cycles:
- Predict next‑day impairment probability.
- Compare to objective and operational proxy outcomes.

Outputs: calibration, generalization, safety utility, and governance evidence.

---

## 8) Modeling and statistical plan

### 8.1 Modeling targets
- **Probability** of impairment (for Likelihood axis).
- **Ordinal readiness tier** (for simpler operational communication).

### 8.2 Model families (interpretability-first)
- Regularized logistic regression / generalized additive models.
- Tree ensembles with monotonic constraints (where justified) and explainability.
- Mixed-effects baselines for repeated-measures benchmarking.

### 8.3 Validation (avoid leakage)
- Subject‑wise train/test splits.
- Nested cross-validation.
- Calibration curves and Brier score.
- Decision-curve analysis.
- Sensitivity analyses: protocol deviations, caffeine, illness.

### 8.4 Uncertainty and fail-safe design
- Conformal prediction / abstention: if uncertainty high → “Needs review.”
- Conservative defaults: never “upgrade” readiness purely due to model confidence; only recommend mitigations/monitoring.

---

## 9) Synthetic/artificial data strategy (AI development support)

Synthetic data is for pipeline testing and robustness—not for final scientific claims.

- **Physiologic RR simulation** with tunable HRV parameters and realistic artifact injection.
- **Scenario‑based fatigue labels** generated from sleep schedules using biomathematical models.
- **Domain randomization** for missingness/compliance/sensor noise.

---

## 10) 5×5 risk matrix for mission readiness

### 10.1 Likelihood axis (rows): probability of impairment in next 0–24 h
Map calibrated predicted probability \(p\) to likelihood category:

- **L1 Rare**: \(p < 0.05\)
- **L2 Unlikely**: \(0.05 \le p < 0.15\)
- **L3 Possible**: \(0.15 \le p < 0.30\)
- **L4 Likely**: \(0.30 \le p < 0.50\)
- **L5 Almost certain**: \(p \ge 0.50\)

Thresholds are **tunable** and must be empirically validated.

### 10.2 Severity axis (columns): consequence if impairment occurs
Mission-defined consequence categories:

- **S1 Negligible**
- **S2 Minor**
- **S3 Moderate**
- **S4 Major**
- **S5 Catastrophic**

### 10.3 Risk scoring table (example)

| Likelihood \ Severity | S1 | S2 | S3 | S4 | S5 |
|---|---:|---:|---:|---:|---:|
| **L1** | 1 | 2 | 3 | 4 | 5 |
| **L2** | 2 | 4 | 6 | 8 | 10 |
| **L3** | 3 | 6 | 9 | 12 | 15 |
| **L4** | 4 | 8 | 12 | 16 | 20 |
| **L5** | 5 | 10 | 15 | 20 | 25 |

### 10.4 Recommended decision bands (to validate with stakeholders)
- **1–4 (Green)**: GO.
- **5–9 (Yellow)**: GO with mitigations and monitoring.
- **10–14 (Orange)**: Delay/mitigate or restrict duty; supervisory review.
- **15–19 (Red)**: NO‑GO unless mission‑critical waiver with enhanced mitigations + aeromedical oversight.
- **20–25 (Critical)**: NO‑GO.

---

## 11) Countermeasure framework (including pharmaceuticals)

### 11.1 Naps and controlled rest
Napping can improve alertness and performance, but operational implementation must manage sleep inertia and cockpit safety constraints (Hartzler, 2014; Hilditch et al., 2016; Hilditch et al., 2020).

### 11.2 Caffeine strategies
Evidence supports caffeine’s ability to sustain vigilance during extended wakefulness, including multiple-dose approaches (Killgore & Kamimori, 2020). Caffeine‑nap strategies may provide additive benefit in night shift analogs (Centofanti et al., 2020).

### 11.3 Light and circadian phase shifting
Shift work and night ops countermeasures include strategically timed light exposure; evidence and management strategies are reviewed in depth (Smith & Eastman, 2012). Time-cue combinations (light + melatonin) can phase advance circadian timing (Burke et al., 2013).

### 11.4 Pharmacologic alertness aids (military governance required)
Military aviation literature includes trials and reviews on stimulant countermeasures:
- Dextroamphetamine efficacy in flight contexts (Caldwell & Caldwell, 1997) and in pilots under sleep deprivation (Caldwell et al., 2003).
- Modafinil effects in pilots under prolonged wakefulness (Caldwell et al., 2004) and as a replacement for dextroamphetamine in helicopter pilots (Estrada et al., 2012).
- Policy-oriented reviews on pharmacologic countermeasures and fitness-for-duty considerations (Caldwell & Caldwell, 2005; Kautz et al., 2007).

**Doctoral governance requirement**: the dissertation must explicitly address contraindications, side-effect monitoring, duty-time restrictions, dependency risk, interaction with sleep debt, and chain-of-command authorization.

---

## 12) People, roles, and infrastructure needed

### 12.1 Core team
- Aerospace medicine PI + flight surgeon oversight.
- Human factors psychologist.
- Biostatistician.
- ML engineer (deployment + monitoring + explainability).
- Operations SME (mission severity, workload realism).
- Ethics/data protection lead.

### 12.2 Infrastructure
- High-quality RR capture (ECG chest strap preferred for RR precision).
- Actigraphy/wearables for sleep.
- Simulator with standardized performance scoring.
- Secure data governance and audit trails.

---

## 13) Ethics, governance, and misuse prevention

- Protect against punitive misuse; define non-punitive readiness intent.
- Ensure informed consent and voluntariness.
- Bias/fairness testing across sex, age, chronotype.
- Clear boundary: decision support only; command and aeromedical policy retain authority.

---

## 14) How this maps to the existing app

The platform already provides:
- HRV QC and comprehensive metrics.
- Circadian and fatigue forecasting tools.
- Longitudinal user profiles and exports.

Dissertation additions would be:
- Standardized objective performance testing integration.
- Model training/validation pipelines and governance artifacts.
- Risk-matrix decision layer and countermeasure playbooks.

---

## 15) References (curated starting bibliography; DOI/PMID where available)

### HRV standards and autonomic framework
- Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology. (1996). Heart rate variability: Standards of measurement, physiological interpretation and clinical use. *Circulation, 93*(5), 1043–1065. (PMID: 8598068)
- Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability metrics and norms. *Frontiers in Public Health, 5*, 258. https://doi.org/10.3389/fpubh.2017.00258 (PMID: 29034226)
- Laborde, S., Mosley, E., & Thayer, J. F. (2017). Heart rate variability and cardiac vagal tone in psychophysiological research—Recommendations for experiment planning, data analysis, and data reporting. *Frontiers in Psychology, 8*, 213. https://doi.org/10.3389/fpsyg.2017.00213 (PMID: 28265249)
- Thayer, J. F., & Lane, R. D. (2000). A model of neurovisceral integration in emotion regulation and dysregulation. *Journal of Affective Disorders, 61*(3), 201–216. https://doi.org/10.1016/S0165-0327(00)00338-4 (PMID: 11163422)

### Sleep loss, fatigue, and performance degradation
- Van Dongen, H. P. A., Maislin, G., Mullington, J. M., & Dinges, D. F. (2003). The cumulative cost of additional wakefulness: dose-response effects on neurobehavioral functions and sleep physiology from chronic sleep restriction and total sleep deprivation. *Sleep, 26*(2), 117–126. https://doi.org/10.1093/sleep/26.2.117 (PMID: 12683469)
- Belenky, G., Wesensten, N. J., Thorne, D. R., Thomas, M. L., Sing, H. C., Redmond, D. P., Russo, M. B., & Balkin, T. J. (2003). Patterns of performance degradation and restoration during sleep restriction and subsequent recovery: a sleep dose-response study. *Journal of Sleep Research, 12*(1), 1–12. https://doi.org/10.1046/j.1365-2869.2003.00337.x (PMID: 12603781)
- Dawson, D., & Reid, K. (1997). Fatigue, alcohol and performance impairment. *Nature, 388*(6639), 235. https://doi.org/10.1038/40775 (PMID: 9230429)
- Lim, J., & Dinges, D. F. (2010). A meta-analysis of the impact of short-term sleep deprivation on cognitive variables. *Psychological Bulletin, 136*(3), 375–389. https://doi.org/10.1037/a0018883 (PMID: 20438143)
- Basner, M., Moore, T. M., Nasrini, J., Gur, R. C., & Dinges, D. F. (2021). Response speed measurements on the psychomotor vigilance test: how precise is precise enough? *Sleep, 44*(1). https://doi.org/10.1093/sleep/zsaa121 (PMID: 32556295)

### Biomathematical fatigue modeling and operational application
- Hursh, S. R., Redmond, D. P., Johnson, M. L., Thorne, D. R., Belenky, G., Balkin, T. J., Storm, W. F., Miller, J. C., & Eddy, D. R. (2004). Fatigue models for applied research in warfighting. *Aviation, Space, and Environmental Medicine, 75*(3 Suppl), A44–A53; discussion A54–A60. (PMID: 15018265)

### Aviation fatigue management, FRMS, and napping
- Caldwell, J. A. (2001). The impact of fatigue in air medical and other types of operations: a review of fatigue facts and potential countermeasures. *Air Medical Journal, 20*(1), 25–32. (PMID: 11182702)
- Hartzler, B. M. (2014). Fatigue on the flight deck: the consequences of sleep loss and the benefits of napping. *Accident Analysis & Prevention, 62*, 309–318. https://doi.org/10.1016/j.aap.2013.10.010 (PMID: 24215936)
- Hilditch, C. J., Dorrian, J., & Banks, S. (2016). Time to wake up: reactive countermeasures to sleep inertia. *Industrial Health, 54*(6), 528–541. https://doi.org/10.2486/indhealth.2015-0236 (PMID: 27193071)
- Hilditch, C. J., Arsintescu, L., Gregory, K. B., & Flynn‑Evans, E. E. (2020). Mitigating fatigue on the flight deck: how is controlled rest used in practice? *Chronobiology International, 37*(9–10), 1483–1491. https://doi.org/10.1080/07420528.2020.1803898 (PMID: 32838563)
- Gander, P. H., Mangie, J., Van Den Berg, M. J., Smith, A. A., Mulrine, H. M., & Signal, T. L. (2014). Crew fatigue safety performance indicators for fatigue risk management systems. *Aviation, Space, and Environmental Medicine, 85*(2), 139–147. https://doi.org/10.3357/asem.3748.2014 (PMID: 24597158)

### Circadian misalignment and light/melatonin countermeasures
- Smith, M. R., & Eastman, C. I. (2012). Shift work: health, performance and safety problems, traditional countermeasures, and innovative management strategies to reduce circadian misalignment. *Nature and Science of Sleep, 4*, 111–132. https://doi.org/10.2147/NSS.S10372 (PMID: 23620685)
- Burke, T. M., Markwald, R. R., Chinoy, E. D., Snider, J. A., Bessman, S. C., Jung, C. M., & Wright, K. P. (2013). Combination of light and melatonin time cues for phase advancing the human circadian clock. *Sleep, 36*(11), 1617–1624. https://doi.org/10.5665/sleep.3110 (PMID: 24179293)
- Cyr, M., Artenie, D. Z., Al Bikaii, A., Lee, V., Raz, A., & Olson, J. A. (2023). An evening light intervention reduces fatigue and errors during night shifts: a randomized controlled trial. *Sleep Health, 9*(3), 373–380. https://doi.org/10.1016/j.sleh.2023.02.004 (PMID: 37080863)

### HRV in readiness/monitoring contexts
- Plews, D. J., Laursen, P. B., Stanley, J., Kilding, A. E., & Buchheit, M. (2013). Training adaptation and heart rate variability in elite endurance athletes: opening the door to effective monitoring. *Sports Medicine, 43*(9), 773–781. https://doi.org/10.1007/s40279-013-0071-8 (PMID: 23852425)
- Plews, D. J., Laursen, P. B., Le Meur, Y., Hausswirth, C., Kilding, A. E., & Buchheit, M. (2014). Monitoring training with heart rate-variability: how much compliance is needed for valid assessment? *International Journal of Sports Physiology and Performance, 9*(5), 783–790. https://doi.org/10.1123/ijspp.2013-0455 (PMID: 24334285)

### Pharmacologic and stimulant countermeasures (aviation / operational)
- Caldwell, J. A., & Caldwell, J. L. (1997). An in-flight investigation of the efficacy of dextroamphetamine for sustaining helicopter pilot performance. *Aviation, Space, and Environmental Medicine, 68*(12), 1073–1080. (PMID: 9408555)
- Caldwell, J. A., Caldwell, J. L., Smythe, N. K., & Hall, K. K. (2000). A double-blind, placebo-controlled investigation of the efficacy of modafinil for sustaining the alertness and performance of aviators: a helicopter simulator study. *Psychopharmacology, 150*(3), 272–282. https://doi.org/10.1007/s002130000450 (PMID: 10923755)
- Caldwell, J. A., Caldwell, J. L., & Darlington, K. K. (2003). Utility of dextroamphetamine for attenuating the impact of sleep deprivation in pilots. *Aviation, Space, and Environmental Medicine, 74*(11), 1125–1134. (PMID: 14620468)
- Caldwell, J. A., Caldwell, J. L., Smith, J. K., & Brown, D. L. (2004). Modafinil's effects on simulator performance and mood in pilots during 37 h without sleep. *Aviation, Space, and Environmental Medicine, 75*(9), 777–784. (PMID: 15460629)
- Caldwell, J. A., & Caldwell, J. L. (2005). Fatigue in military aviation: an overview of US military-approved pharmacological countermeasures. *Aviation, Space, and Environmental Medicine, 76*(7 Suppl), C39–C51. (PMID: 16018329)
- Kautz, M. A., Thomas, M. L., & Caldwell, J. L. (2007). Considerations of pharmacology on fitness for duty in the operational environment. *Aviation, Space, and Environmental Medicine, 78*(5 Suppl), B107–B112. (PMID: 17547311)
- Estrada, A., Kelley, A. M., Webb, C. M., Athy, J. R., & Crowley, J. S. (2012). Modafinil as a replacement for dextroamphetamine for sustaining alertness in military helicopter pilots. *Aviation, Space, and Environmental Medicine, 83*(6), 556–564. https://doi.org/10.3357/asem.3129.2012 (PMID: 22764609)
- Killgore, W. D. S., & Kamimori, G. H. (2020). Multiple caffeine doses maintain vigilance, attention, complex motor sequence expression, and manual dexterity during 77 hours of total sleep deprivation. *Neurobiology of Sleep and Circadian Rhythms, 9*, 100051. https://doi.org/10.1016/j.nbscr.2020.100051 (PMID: 33364521)
- Centofanti, S., Banks, S., Coussens, S., Gray, D., Munro, E., Nielsen, J., & Dorrian, J. (2020). A pilot study investigating the impact of a caffeine-nap on alertness during a simulated night shift. *Chronobiology International, 37*(9–10), 1469–1473. https://doi.org/10.1080/07420528.2020.1804922 (PMID: 32819191)

---

## Appendix A — Suggested next literature expansions

To complete a full dissertation proposal and final manuscript, add focused reviews and primary studies on:
- Inter-individual vulnerability to sleep loss and operational fatigue.
- Ocular metrics/EEG as objective fatigue markers for aviation.
- Fitness, aerobic capacity, and stress resilience links to performance in pilots/commanders.
- Formal decision science for risk matrices in Safety Management Systems.
