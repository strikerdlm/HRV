# Toward an Integrated, Scientifically Defensible Model of Human Performance for Safety‑Critical Operations

## Purpose and scope

This document proposes a theory and practical blueprint for integrating established biomathematical fatigue/performance models with real‑time autonomic physiology (HRV and heart rate fragmentation, HRF), workload context, circadian timing, and stimulant (caffeine) effects into a single governed model suitable for safety‑critical roles (pilot, astronaut). It synthesizes findings from `docs/lit_review.md` and `docs/updates2026.md`, and augments them with peer‑reviewed sources to ensure scientific traceability.

## Evidence base and design constraints (brief synthesis)

- Circadian and sleep homeostasis jointly determine large fractions of alertness and performance variance. The two‑process framework formalizes sleep pressure (Process S) and circadian drive (Process C) (Borbély, 1982). Limit‑cycle pacemaker models and human light phase‑response curves (PRCs) quantify light‑timing effects and enable phase estimation and what‑if schedule analysis (Jewett & Kronauer, 1998; Forger et al., 1999; Khalsa et al., 2003; St Hilaire et al., 2012).
- Biomathematical performance models operationalize these principles. The SAFTE family models effectiveness as a function of a sleep reservoir, circadian modulation, and sleep inertia (Hursh et al., 2004; Hursh et al., 2011). The Unified Model of Performance (UMP) extends prediction across total sleep deprivation and chronic restriction and has been coupled with caffeine dosing strategies (McCauley et al., 2009; Reifman group/2B‑Alert line of work). The HSE Fatigue/Risk Index (FRI) provides a schedule risk metric that accounts for duty timing/length and shift patterns (Folkard, Robertson, & Spencer, 2007). Vendor tools such as the Boeing Alertness Model (BAM) are widely used but are proprietary; they conceptually align with SAFTE‑like dynamics.
- Autonomic physiology captures acute state and potential degradation not fully explained by schedules. HRV features (e.g., RMSSD, HF power) and nonlinear metrics (SD1/SD2, entropy) provide vagal and complexity proxies but are sensitive to protocol, respiration, and artefacts; LF/HF is not a reliable sympathovagal balance surrogate (Task Force, 1996; Shaffer & Ginsberg, 2017; Billman, 2013). HRF (e.g., PIP, IALS, PAS) adds complementary information about beat‑to‑beat irregularity largely orthogonal to traditional HRV (Costa et al., 2017).
- Operational governance requires: quality‑gated measurement; individualized baselines; explicit uncertainty; and “fail‑closed” behavior (see `docs/lit_review.md` Section 4 and 5).

## Integration goals

- Preserve validated schedule‑based structure (sleep/circadian/inertia) for out‑of‑sample stability.
- Add physiology‑based acute‑state sensitivity without overfitting.
- Embed personalization and rigorous error control (mixed‑effects, blocked CV, FDR).
- Provide transparent reason codes for decisions and enable FRMS‑style auditability.

---

## Integrated architecture

The model is organized in modular layers. Each layer exposes inputs, internal state, and outputs with provenance and confidence scores.

### 1. Circadian/homeostatic core (S, C, I)

- Process S (homeostatic sleep pressure) and Process C (circadian drive) provide the macrostructure for alertness dynamics (Borbély, 1982). A limit‑cycle pacemaker (e.g., Forger/Jewett‑Kronauer class) converts light history into phase and amplitude, supporting PRC‑consistent phase shifts and entrainment (Jewett & Kronauer, 1998; Forger et al., 1999; Khalsa et al., 2003; St Hilaire et al., 2012).
- Sleep inertia I(t) is modeled as a short‑lived multiplicative penalty that dissipates after waking (SAFTE).

### 2. Biomathematical performance mapping

- SAFTE‑style effectiveness \(E_{\text{SAFTE}}(t)\) combines the sleep reservoir \(S(t)\), circadian modulation \(C(t)\), and inertia \(I(t)\) (Hursh et al., 2004; 2011).
- UMP‑style mapping \(P_{\text{UMP}}(t)\) allows calibration to PVT outcomes under both acute total sleep deprivation and chronic restriction, and can incorporate caffeine effects (McCauley et al., 2009; UMP/2B‑Alert translational work).
- HSE FRI provides a schedule‑risk prior \(R_{\text{FRI}}(t)\) sensitive to shift timing/length that may not be fully captured by sleep history alone (Folkard et al., 2007).

### 3. Acute autonomic state module (HRV/HRF), with quality gating

- Compute a physiology factor \(A_{\text{AN}}(t)\) from HRV and HRF, bounded to [0, 1.2] to prevent over‑dominance. Suggested construction under resting, protocol‑controlled conditions:
  - HRV vagal proxy: lnRMSSD (time‑domain) and SD1, with respiration metadata when available.
  - HRF fragmentation proxy: normalized PIP (and optionally IALS, PAS, W3).
  - Within‑person standardization: z‑scores relative to phase‑matched baselines.
  - Saturating transforms to avoid linear overinterpretation (e.g., logistic on z‑scores).
- Apply strict quality gates:
  - Reject or down‑weight if artefact‑correction fraction is high (Lipponen & Tarvainen, 2019).
  - Enforce physiological plausibility and stationarity checks (Task Force, 1996; Laborde et al., 2017).
  - If respiration is uncontrolled, reduce confidence for frequency features.

### 4. Workload and operational context

- Include workload/task demand \(W(t)\) using operational metadata (phase of mission, task intensity) and schedule‑informed priors (HSE FRI). When available, add objective markers (e.g., dual‑task demand, comm metrics) with bounded effects.

### 5. Caffeine/pharmacology

- Incorporate a simple pharmacokinetic/pharmacodynamic sub‑model \(U_{\text{caf}}(t)\) (UMP/2B‑Alert lineage) to capture timing/dose of caffeine and expected modulation of alertness, with subject‑level sensitivity calibrated from historical PVT and sleep data.

### 6. Environment and hazard modifiers

- Optional bounded factors \(X(t)\) (hypoxia, thermal load, microgravity phase, space‑weather alerts) that can nudge risk up/down with conservative weights unless validated for the specific cohort and condition (see `docs/lit_review.md` Sections 3.10 and 3.13).

### Fusion and personalization

We recommend multiplicative fusion with log‑linear personalization to maintain interpretability, followed by a sigmoid to keep predictions in [0,1]:
\[
P(t) \;=\; \sigma\!\left(
\alpha_0 \;+\; \alpha_1 \log E_{\text{SAFTE}}(t) \;+\; \alpha_2 \log P_{\text{UMP}}(t) \;+\; \alpha_3 \log A_{\text{AN}}(t) \;+\; \alpha_4 \log W(t) \;+\; \alpha_5 \log U_{\text{caf}}(t) \;+\; \alpha_6 \log X(t)
\right),
\]
with safeguards when any term is missing/low‑confidence (see fail‑closed behavior below). In practice:

- Choose one primary schedule model (SAFTE or UMP) for parsimony and treat the other as a prior/regularizer; or use model stacking with non‑negative weights constrained to sum ≤ 1.
- Personalize via hierarchical/mixed‑effects: subject‑level random intercepts/slopes on the schedule and caffeine terms, and subject‑level sensitivities for HRV/HRF. Calibrate against objective endpoints (PVT lapses/RTs) with blocked or forward‑chaining time‑series cross‑validation (Bergmeir et al., 2018).

### Fail‑closed behavior and reason codes

- If HRV/HRF quality gates fail or protocol is uncontrolled (posture/time‑of‑day/respiration unknown), set \(A_{\text{AN}}\) to neutral (1.0) and emit a “reduced confidence: physiology” reason code.
- If schedule inputs are incomplete (sleep history gaps; uncertain timezone), inflate uncertainty on \(E_{\text{SAFTE}}\)/\(P_{\text{UMP}}\) and require corroboration by PVT before elevating risk.
- When sub‑modules disagree (e.g., favorable schedule but suppressed HRV/HRF), surface disagreement explicitly and prompt objective verification rather than forcibly fusing to a single confident state.

---

## Measurement and modeling governance

### 1. Acquisition standards and QC

- HRV/HRF: enforce standardized resting recordings (e.g., morning supine, breath instructions), respiration metadata, plausibility checks, and conservative artefact thresholds (Task Force, 1996; Laborde et al., 2017; Lipponen & Tarvainen, 2019). Report correction fraction and protocol variables with each output. Favor ECG‑derived RR for decision support; treat PPG PRV cautiously (`docs/lit_review.md` 3.2.4, 3.9.1).
- Windowing and baselines: maintain phase‑matched baselines (clock‑time or model phase), and compute robust summaries (e.g., rolling medians; lnRMSSD) alongside raw values (`docs/lit_review.md` 3.14).

### 2. Statistical controls

- Separate exploration from inference. Use pre‑specified windows/lags for overlays (e.g., space‑weather context), negative controls/pseudo‑events, and FDR control (Benjamini & Hochberg, 1995). For drift detection, prefer penalized change‑point methods (e.g., PELT; Killick et al., 2012).

### 3. Personalization and calibration

- Calibrate subject‑level parameters using repeated PVT (3–10 min variants per Basner et al., 2021) and recent sleep/caffeine logs. Use blocked/forward‑chaining CV to avoid leakage. Where PVT is unavailable, restrict personalization to schedule terms and keep physiology effects conservative.

### 4. Provenance and auditability

- Log device type/firmware, preprocessing settings, schedule sources, caffeine inputs, and model versioning with each prediction to support FRMS and after‑action review (`docs/lit_review.md` 4.6, 4.7).

---

## Practical mapping to pilot/astronaut workflows

- Pre‑mission: schedule risk evaluation (FRI prior), SAFTE/UMP projection with planned duty/rest, and light‑schedule what‑ifs via the pacemaker model. Establish/refresh physiology baselines (HRV/HRF) under standardized conditions.
- Mission phase: real‑time updates of \(S,C,I\) from sleep logs/actigraphy; bounded physiology updates when QC passes; optional caffeine planner enforcing safe caps and optimal timing (UMP lineage). Emit reason codes (e.g., “elevated fatigue risk due to 3‑day sleep debt; physiology neutral”).
- Elevated risk or disagreement: trigger objective verification (brief PVT), review schedule mitigation (naps, shift adjustments), and document actions per FRMS guidance (`docs/lit_review.md` 3.8.4).
- Spaceflight specifics: treat microgravity stage and hypoxia/thermal load as metadata modifiers with conservative weights; interpret HRV/BPV relative to mission‑phase baselines rather than Earth norms (`docs/lit_review.md` 3.13).

---

## Minimal, evidence‑grounded equation set (suggested starting point)

### 1. Schedule effectiveness (pick one primary; expose both during R&D)

\[ E_{\text{sched}}(t) \in (0,1.3], \quad \text{from SAFTE or UMP (with caffeine)}. \]

### 2. Physiology factor (bounded, baseline‑relative, QC‑gated)

\[
A_{\text{AN}}(t) \;=\; \exp\!\left(\gamma_1 \,\tilde{z}_{\text{lnRMSSD}}(t) \;-\; \gamma_2 \,\tilde{z}_{\text{PIP}}(t)\right),
\quad A_{\text{AN}} \in [0.8,\,1.2],
\]
where tildes denote phase‑matched, winsorized z‑scores. Apply \(A_{\text{AN}}=1\) (neutral) if QC fails.

### 3. Workload/context factor (bounded)

\[ W(t) \in [0.9,\,1.1], \quad \text{from duty/task metadata and FRI prior.} \]

### 4. Environment modifier (optional, conservative)

\[ X(t) \in [0.95,\,1.05]. \]

### 5. Final fusion with personalization (random effects on \(\alpha\)s)

\[
P(t) \;=\; \sigma\!\left(
\alpha_0 + \alpha_1 \log E_{\text{sched}}(t) + \alpha_2 \log A_{\text{AN}}(t) + \alpha_3 \log W(t) + \alpha_4 \log X(t)
\right).
\]
Report \(P(t)\) with a confidence score derived from sub‑module QC and input completeness.

---

## Validation plan (what must hold before operational reliance)

- Endpoint‑first: evaluate against PVT lapses/RT as the primary operational failure mode (Basner et al., 2021; Van Dongen et al., 2003), not only subjective scales.
- Cohort‑appropriate calibration: pilots/astronaut analog populations with duty/rest patterns representative of intended use.
- Time‑series‑aware evaluation: blocked/forward‑chaining CV; pre‑registered windows/lags; nested hyperparameter tuning (Bergmeir et al., 2018).
- Error budget and uncertainty: quantify contributions from schedule uncertainty, physiology QC, caffeine adherence, and environment modifiers; require objective corroboration when uncertainty is high.

---

## References

- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate. Journal of the Royal Statistical Society Series B, 57(1), 289–300. <https://doi.org/10.1111/j.2517-6161.1995.tb02031.x>
- Billman, G. E. (2013). The LF/HF ratio does not accurately measure cardiac sympatho‑vagal balance. Frontiers in Physiology, 4, 26. <https://doi.org/10.3389/fphys.2013.00026>
- Borbély, A. A. (1982). A two‑process model of sleep regulation. Human Neurobiology, 1, 195–204.
- Costa, M. D., Davis, R. B., & Goldberger, A. L. (2017). Heart rate fragmentation. Frontiers in Physiology, 8, 255. <https://doi.org/10.3389/fphys.2017.00255>
- Forger, D. B., Jewett, M. E., & Kronauer, R. E. (1999). A simpler model of the human circadian pacemaker. Journal of Biological Rhythms, 14(6), 533–538. <https://doi.org/10.1177/074873099129000867>
- Folkard, S., Robertson, K. A., & Spencer, M. B. (2007). A fatigue/risk index to assess work schedules. Somnologie, 11, 177–185. <https://doi.org/10.1007/s11818-007-0308-6>
- Hursh, S. R., et al. (2004). Fatigue models for applied research in warfighting. Aviation, Space, and Environmental Medicine, 75(3 Suppl), A44–A53.
- Hursh, S. R., et al. (2011). The DoD Sleep, Activity, Fatigue, and Task Effectiveness Model (DOT/FAA/AM‑11/8). U.S. DOT/FAA.
- Jennings, J. R., et al. (2014). Focusing neurovisceral integration. Psychophysiology, 52(2), 214–224. <https://doi.org/10.1111/psyp.12319>
- Jewett, M. E., & Kronauer, R. E. (1998). Refinement of limit‑cycle oscillator model of light effects on the human pacemaker. Journal of Theoretical Biology, 192(4), 455–465. <https://doi.org/10.1006/jtbi.1998.0667>
- Khalsa, S. B. S., et al. (2003). A phase response curve to single bright light pulses in humans. The Journal of Physiology, 549(3), 945–952. <https://doi.org/10.1113/jphysiol.2003.040477>
- Killick, R., Fearnhead, P., & Eckley, I. A. (2012). Optimal detection of changepoints with linear cost (PELT). JASA, 107(500), 1590–1598. <https://doi.org/10.1080/01621459.2012.737745>
- Laborde, S., Mosley, E., & Thayer, J. F. (2017). HRV in psychophysiology: recommendations. Frontiers in Psychology, 8, 213. <https://doi.org/10.3389/fpsyg.2017.00213>
- Lipponen, J. A., & Tarvainen, M. P. (2019). Robust HRV artefact correction. Journal of Medical Engineering & Technology, 43(3), 173–181. <https://doi.org/10.1080/03091902.2019.1640306>
- McCauley, P., et al. (2009). A new mathematical model for the homeostatic effects of sleep loss on neurobehavioral performance. Journal of Theoretical Biology, 256, 227–239. <https://doi.org/10.1016/j.jtbi.2008.09.012>
- Nunan, D., Sandercock, G. R. H., & Brodie, D. A. (2010). Normal values for short‑term HRV. Pacing and Clinical Electrophysiology, 33(11), 1407–1417. <https://doi.org/10.1111/j.1540-8159.2010.02841.x>
- Shaffer, F., & Ginsberg, J. P. (2017). HRV metrics and norms. Frontiers in Public Health, 5, 258. <https://doi.org/10.3389/fpubh.2017.00258>
- St Hilaire, M. A., et al. (2012). Human PRC to a 1‑h pulse of bright light. The Journal of Physiology, 590(13), 3035–3045. <https://doi.org/10.1113/jphysiol.2012.227892>
- Task Force of the ESC and NASPE. (1996). HRV: Standards of measurement, physiological interpretation, and clinical use. Circulation, 93(5), 1043–1065. <https://doi.org/10.1161/01.CIR.93.5.1043>
- Van Dongen, H. P. A., et al. (2003). Dose‑response effects of sleep restriction. Sleep, 26(2), 117–126. <https://doi.org/10.1093/sleep/26.2.117>
- Basner, M., et al. (2021). Standardization of PVT methods and reporting. Sleep, 44(7). <https://doi.org/10.1093/sleep/zsab114>

Notes: UMP/2B‑Alert caffeine‑optimization work has multiple publications; see recent SLEEP reports summarizing unified modeling and personalized caffeine dosing algorithms. BAM is also documented in agency/vendor sources (and may not be fully citable due to proprietary constraints).

---

## Summary

This integrated model retains the external validity of schedule‑based biomathematics (SAFTE/UMP), augments it with a disciplined, quality‑gated physiology layer (HRV/HRF), and wraps both in circadian‑aware baselines, conservative fusion, and FRMS governance. It emphasizes within‑person calibration to objective endpoints (PVT), transparent provenance, and explicit uncertainty—properties required for credible application in aviation and spaceflight.
