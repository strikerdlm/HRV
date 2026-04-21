# Novelty Verification and Q1 Venue Recommendation — HF/Medical/Psychology Repositioning

Author: Dr Diego Malpica MD
Date: 2026-04-21
Branch: `q1-hf-opi-reframe`
Scope: Literature-verified novelty positioning and Q1 venue recommendation for repositioning the manuscript toward medical / psychology / human factors, abandoning the prior biomedical-computing (CMPB/JBI) target.

---

## Executive summary

The existing `analysis/operational_performance_indicators_research.md` (760 lines) already contains the real novel contribution buried inside the repository: a **task-specific Operational Performance Indicator (OPI) framework** that fuses SAFTE fatigue effectiveness, HRV-derived autonomic markers, task-specific cognitive-load modifiers (grounded in Wickens' Multiple Resource Theory, Warm's vigilance decrement, Chen et al. teleoperator latency penalty), and environmental modifiers into a per-task composite readiness index. The framework covers 10 manned-aviation task categories (IMC, NVD, HMD, high-density ATC, emergency critical/non-critical, test pilot, carrier landing, weapons delivery, new-platform testing) and 7 UAS/teleoperation categories (ISR, strike, SAR/CSAR, autonomous swarm, contested environment, ground robot teleoperation, subsea).

Literature verification (four parallel queries across Europe PMC, OpenAlex, PubMed, Scite, + DOI cross-check via Crossref) confirms: **no published paper proposes a task-calibrated HRV + SAFTE + MRT composite readiness index with per-task weight profiles, open-source reference implementation, and coverage of both manned-aviation and UAS operators.** The closest adjacent work either:
- applies ML classifiers to physiological signals (no explicit biomathematical layer)
- integrates multiple physiological modalities at a single flight phase (no fatigue model and no full-taxonomy calibration)
- reviews the space without proposing a unified framework
- addresses manned aviation or UAS in isolation, not both

This is a defensible Q1 methodology contribution in human factors / aerospace psychology / applied physiology, provided the paper is explicitly framed as **methodology + open-source reference implementation + illustrative single-subject worked example** — not as a validated clinical or operational tool.

---

## Novelty claim (proposed, 130 words)

> We introduce the **Operational Performance Indicator (OPI) framework**, a task-calibrated composite readiness index that integrates SAFTE-style reservoir fatigue effectiveness, HRV-derived autonomic markers (RMSSD, LF/HF, stress index, complexity), and task-specific cognitive-load modifiers grounded in Multiple Resource Theory, Yerkes-Dodson arousal-performance mapping, allostatic load, and cognitive-readiness constructs. Per-task weight profiles and thresholds are specified for ten manned-aviation task categories and seven unmanned aircraft system operator categories, including an explicit vigilance-decrement model and control-latency penalty for teleoperation. The framework is distributed as an open-source reference implementation delivered through a Node-first (Next.js + FastAPI) architecture over a shared Python biomathematical backend. Evidence is bounded to conceptual framework definition, implementation, and engineering verification; external validation in field populations is positioned as the next study.

---

## Adjacent prior work — verified DOIs and differentiation

| # | Reference (verified) | Venue (JIF/Q) | What they did | Key limitation vs. OPI |
|---|---|---|---|---|
| 1 | Stevens CA, Morris MB, Fisher CR, Myers CW (2022). Profiling cognitive workload in an unmanned vehicle control task with cognitive models and physiological metrics. *Military Psychology* 35(6), 507-520. doi:10.1080/08995605.2022.2130673 | Military Psychology (Q3) | Cognitive Metrics Profiling (CMP) linked to physiological workload in one UAV control task | Single task; cognitive model not integrated with fatigue dynamics or HRV-based autonomic reserve; no per-task taxonomy |
| 2 | Vogl J, O'Brien K, St. Onge P (2025). One size does not fit all: a support vector machine exploration of multiclass cognitive state classifications using physiological measures. *Frontiers in Neuroergonomics* 6, 1566431. doi:10.3389/fnrgo.2025.1566431 | Frontiers in Neuroergonomics (Q2) | Individualised SVM classifiers of cognitive workload from ECG + pupillometry in a low-fidelity aviation simulator (n=3) | ML classifier on signals; no biomathematical layer; no per-task calibration; no fatigue modelling |
| 3 | Hamann A, van Klaren C, Zon R, Dehais F, Carstengerdes N, van Miltenburg M, Cabrera Castillos K (2025/2026). The state of the art in assessing mental fatigue in the cockpit using head-worn sensing technology. *Frontiers in Neuroergonomics* 6, 1673268. doi:10.3389/fnrgo.2025.1673268 | Frontiers in Neuroergonomics (Q2) | Narrative review of EEG/fNIRS/eye-tracking for cockpit mental fatigue | Review only; head-worn focus excludes HRV; no composite framework proposed |
| 4 | Li Q, Molloy O, El-Fiqi H, Eves G (2025). Applications of Machine Learning in Assessing Cognitive Load of Uncrewed Aerial System Operators and in Enhancing Training: A Systematic Review. *Drones* 9(11), 760. doi:10.3390/drones9110760 | Drones (MDPI) | Systematic review of ML approaches to UAS operator cognitive load | Systematic review of ML methods; explicitly identifies gaps in integrated frameworks; does not propose OPI-style composite |
| 5 | Feng C, Wanyan X, Yang K, Zhuang D, Wu X (2018). A comprehensive prediction and evaluation method of pilot workload. *Technology and Health Care* 26(S1), 65-78. doi:10.3233/thc-174201 | Tech & Health Care | MRT-grounded multinomial logistic regression on fixation + ECG + EDA features for 3 flight phases (cruise, approach, landing) | Only 3 flight phases; no fatigue model; no open implementation; no UAS coverage |
| 6 | Berthon L, Bernard F, Fleury S, Paquin R, Richir S (2025). Multi-dimensional measurement of mental workload in industrial context: an experiment in the field of helicopter maintenance. *Applied Ergonomics* 129, 104599. doi:10.1016/j.apergo.2025.104599 | **Applied Ergonomics (Q1 HF)** | NASA-TLX + HR + HRV + performance across helicopter maintenance tasks (n=10) | Maintenance only; no fatigue model; no readiness composite; demonstrates Applied Ergonomics venue fit for HRV+workload papers |
| 7 | Rabat A, Van Cutsem J, Marcora SM, Lambert A, Markwald R, Kubala AG, Friedl KE (2025). Fatigue and management of warfighter mental endurance. *BMJ Military Health* 171(5), 447-451. doi:10.1136/military-2025-002963 | BMJ Military Health | Review of military mental fatigue management; emphasises need for infrastructure for integrated physiological monitoring | Review positioning; no concrete framework or implementation — a landing page for our contribution to cite |
| 8 | Houghton R, Martinetti A, Majumdar A (2024). A Framework for Selecting and Assessing Wearable Sensors Deployed in Safety Critical Scenarios. *Sensors* 24(14), 4589. doi:10.3390/s24144589 | Sensors (Q1 I&I) | Framework for sensor selection in safety-critical HF contexts | Sensor-selection framework, not a readiness composite; complementary citation |
| 9 | Jin K, Rubio-Solis A, Naik R, Leff D, Kinross J, Mylonas G (2025). Human-Centric Cognitive State Recognition Using Physiological Signals: A Systematic Review of Machine Learning Strategies Across Application Domains. *Sensors* 25(13), 4207. doi:10.3390/s25134207 | Sensors (Q1 I&I) | 405-article systematic review of ML cognitive-state recognition incl. aviation | Shows field's dominant trend is ML classification, not biomathematical layering — positions our methodology as differentiated |
| 10 | Stevens, Vogl, Feng (as above) and Alsanousi MM, Prabhu VV (2025). Multimodal Hidden Markov Models for Real-Time Human Proficiency Assessment in Industry 5.0. *Applied Sciences* 15(14), 7739. doi:10.3390/app15147739 | Applied Sciences (Q2) | MHMM for proficiency assessment using HRV + TCT + NASA-TLX (Industry 5.0) | Industry 5.0 proficiency, not aviation readiness; simulation-based; no fatigue model; no per-task calibration |

**Red flags (must cite to pre-empt reviewer objection):**
- Feng et al. 2018 (same MRT + physiology + pilot workload spine, different scope)
- Stevens et al. 2022 (UAV control + cognitive model + physiology, same AFRL lineage)
- Li et al. 2025 (UAS systematic review — explicitly asks for integrated frameworks, creates a landing page for our paper)
- Rabat et al. 2025 (calls for infrastructure, citable as gap statement)

---

## Residual gap after verification

1. **No published task-calibrated HRV + SAFTE + MRT composite** for aviation/UAS operators with per-task weight profiles and thresholds derived from HF literature.
2. **No open-source reference implementation** distributed as software for operator readiness fusion; existing tools (FAST, Kubios) do one job each, and recent ML classifiers ship as research code or commercial black boxes.
3. **No unified taxonomy spanning manned aviation and UAS** in one framework; literature treats these as separate communities (Hamann 2025 is cockpit only; Li 2025 UAS only).
4. **No explicit vigilance-decrement and control-latency penalty** in existing composite readiness indices for UAS operators, despite decades of supporting research (Warm, Chen).

This is a genuine research gap. The framework as written in `analysis/operational_performance_indicators_research.md` closes it.

---

## Q1 venue ranking (medical/psychology/human factors)

Verified against journal websites and Clarivate/SCImago rankings (April 2026).

| Rank | Journal | JIF (2024) | Q / Category | Methods paper OK? | APC | Decision risk |
|---|---|---|---|---|---|---|
| **1 (primary)** | **Applied Ergonomics** (Elsevier) | **3.4** | **Q1 Human Factors** | Yes — explicitly welcomes methodology papers on HF in military/aerospace contexts | Hybrid; $0 standard / $3,600 OA | **Medium-low**: strong scope fit (Berthon 2025 precedent), aviation-friendly, 79-day first-decision |
| **2 (secondary)** | **Human Factors** (HFES/SAGE) | **5.72** | **Q1 flagship HF** | Yes, but bar is higher; methodology papers expected to advance HF theory | $1,500 OA optional | **Medium-high**: higher bar; 10-week review; but best JIF and exact domain |
| **3 (tertiary)** | **Sensors** (MDPI) | **3.5** | **Q1 Instruments & Instrumentation** | Yes — multiple HRV/wearable/methodology precedents | $2,600 OA (required) | **Low**: broad scope, fast turnaround, but "Q1" is category-dependent (I&I yes; Engineering Electrical = Q2) |
| 4 (specialty) | Frontiers in Neuroergonomics | 1.9 | Q2 HF&E | Yes — explicit specialty venue | $2,590 OA | Low but Q2, so does not meet Diego's Q1 requirement |
| 5 (fallback Q1) | Ergonomics (T&F) | ~3.5 | Q1 HF | Yes | Hybrid | Medium |
| 6 (fallback Q1) | Safety Science (Elsevier) | ~6.1 | Q1 Safety/OR | Maybe; needs safety-outcomes framing | Hybrid | High — less exact scope fit |

### Recommended submission order

1. **Primary: Applied Ergonomics** — Q1 in HF, JIF 3.4, explicitly scopes aerospace/military HF methodology, recent HRV+workload paper (Berthon 2025) confirms scope. Risk of desk-rejection is low given the methodology + reference software framing and explicit evidence tiering.
2. **Secondary (if Applied Ergonomics rejects):** Human Factors (HFES/SAGE) — highest JIF among HF journals; more rigorous review; re-package to emphasise SA/readiness theoretical contribution.
3. **Tertiary (if both reject or faster turnaround preferred):** Sensors — Q1 in I&I; multiple HRV + operator monitoring precedents; fast turnaround.
4. **If Q1 target relaxed:** Frontiers in Neuroergonomics — specialty venue with Dehais as Field Chief Editor; fast turnaround; but Q2.

### Why not previously considered venues

- **CMPB**, **JBI**, **npj Digital Medicine** — excluded (Diego's instruction); all require numerical validation that the repository doesn't yet support.
- **AMHP** — not Q1 in any category; already excluded in the outline.
- **Military Psychology** — Q3; not Q1.
- **IEEE THMS (Transactions on Human-Machine Systems)** — Q2 in many categories; possible fallback but the review cycle is slow.
- **Chronobiology International** — good fit for fatigue/circadian papers but the OPI is primarily a task-readiness framework with SAFTE being one of four components.

---

## Recommended paper reframing (manuscript-level changes required)

**New title (working):**
> Task-calibrated Operational Performance Indicators (OPI) for aviation and unmanned aircraft system operators: a biomathematical framework integrating SAFTE fatigue, heart-rate variability, and cognitive-load theory, with open-source reference implementation

**Running title:** Task-calibrated OPI for aerospace operators

**New central thesis:** The paper contributes a **task-calibrated composite readiness index** that fuses four biomathematical components — SAFTE effectiveness, HRV autonomic markers, MRT-derived cognitive-load modifiers, and environmental/operational modifiers — into a single per-task interpretable output, with weight profiles and thresholds specified for ten manned and seven UAS operator task categories and distributed as open-source software.

**Section-level changes vs. current draft:**

| Section | Current framing | New framing |
|---|---|---|
| Abstract | Node-first systems platform for HRV + fatigue + space-weather | Task-calibrated OPI methodology + reference implementation + illustrative worked example |
| Introduction | HRV interpretation depends on context; platform integrates context | HF gap: no open, task-calibrated composite readiness index for aviation/UAS; cite Hamann 2025, Li 2025, Rabat 2025 as gap anchors |
| Methods | Requirements → architecture → implementation → validation methodology | Framework definition (OPI equations, MRT grounding, task taxonomy) → per-task weight profiles → component specs (HRV / SAFTE / vigilance / latency) → reference implementation → worked-example methodology |
| Results | Implementation summary + engineering verification | Worked example output (128-min recording → OPI outputs across multiple task hypotheses) + engineering verification for fusion logic + reproducibility |
| Discussion | Systems contribution vs. HRV packages | Methodology contribution vs. Feng 2018, Stevens 2022, Vogl 2025, Li 2025; hedged claims; field-validation roadmap |
| Tables | 6 tables (arch/gap/verif/reprod/compliance/layers) | Retain 1,3,4,5; replace 2 and 6 with OPI-specific: task taxonomy table (17 categories × demands × HRV signatures), OPI weight profiles table, vigilance-decrement table, latency-penalty table |
| Figures | Platform arch, workflow, research-to-ops, verification map | OPI conceptual schematic, task taxonomy figure, worked-example output, reference-implementation architecture |
| Space-weather content | Equal partner in the narrative | Downgraded to optional "environmental modifier" component with clear caveat that causal inference is out of scope |
| Evidence matrix | Current claims | Update: framework as Supported, implementation as Supported, engineering verification as Supported, external validation remains Gap |

**Space-weather positioning change:** Given the HF reframing, space-weather becomes a single optional environmental modifier in the OPI, not a co-equal modelling layer. This de-risks the paper enormously — reviewers won't question autonomic-solar causal claims because the paper no longer makes them. The single-subject correlation artifact is moved to Supplementary Demonstrations.

**Worked-example strategy:** Use the existing 128-minute HRV recording (2025-11-23) as a **framework-instantiation demonstration** — show the full input → preprocessing → HRV metrics → SAFTE effectiveness → OPI composite for each of three hypothetical task scenarios (e.g., IMC approach, UAS ISR sortie, carrier landing). This turns an n=1 dataset from an inferential liability into a legitimate methodology illustration, which is standard practice for HF framework papers.

---

## Execution plan (this branch: `q1-hf-opi-reframe`)

Each step a separate commit. Order matters — later steps depend on earlier ones.

1. **(this file)** Commit novelty+venue recommendation as the new planning anchor.
2. Update `manuscript/outline/manuscript_outline.md` with new thesis, title, section plan, venue choice.
3. Update `manuscript/evidence/evidence_matrix.md` with OPI framework claims.
4. Update `manuscript/evidence/validation_story.md` with methodology-paper evidence posture.
5. Create `manuscript/tables/opi_task_taxonomy.md` (17 task categories × primary demands × HRV signatures × OPI weights).
6. Create `manuscript/tables/opi_weight_profiles.md` (per-task w1/w2/w3 weights + modifiers).
7. Create `manuscript/tables/opi_vigilance_latency_models.md` (vigilance decrement λ, latency penalty coefficients).
8. Rewrite `manuscript/draft/main_manuscript_scaffold.md` into `manuscript/draft/opi_main_manuscript.md` (Applied Ergonomics target; 5,000-6,500 words; structured abstract).
9. Update `manuscript/references/seed_references.md` with the 10 verified OPI references + retain relevant existing ones.
10. Create `manuscript/figures/figure_plan_opi.md` with four new figures (OPI schematic, taxonomy, worked example, implementation arch).
11. Create `manuscript/submission/cover_letter_applied_ergonomics.md`.
12. Create `manuscript/submission/highlights.md` (Elsevier-style 3-5 bullets).
13. Update `manuscript/README.md` to point to OPI reframe as the authoritative current plan.
14. Optional: run the existing 128-min recording through the OPI formula in `e2b` to produce the worked-example numbers for Results.

After Diego confirms this plan, execute commits 1-13 in order. Figures (SVG) can be drafted with existing Python/SVG generators in the repo.

---

## What this plan does NOT do

- Does not run external numerical HRV benchmarking (Path A of the prior advisor recommendation was rejected in favour of Path B; the new framing does not need it).
- Does not add new empirical data beyond the existing 128-min recording (treated as illustrative, not inferential).
- Does not claim diagnostic accuracy, outcome benefit, or operational validation.
- Does not delete the existing biomedical-computing (CMPB) framing files; they remain in git history on `main`. The reframe happens on this branch only until Diego merges.

---

## Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Reviewer asks "where is the empirical validation of the OPI weights?" | **High** | Hedge explicitly: weights are theory-derived from HF literature; external validation is stated as next study; cite analogous framework papers (e.g., SAFTE original 2004) that predated population validation |
| Reviewer asks "why should I believe the MRT-derived weights?" | Medium | Show derivation trace from each HF reference to each weight; include sensitivity-analysis demonstration using the worked example |
| Reviewer asks "how does this compare to Feng et al. 2018?" | **High** | Explicit comparison row in Related Work table; differentiate on (a) fatigue model inclusion, (b) task taxonomy breadth, (c) UAS coverage, (d) open implementation |
| Paper desk-rejected for scope | Low at Applied Ergonomics | Berthon 2025 precedent; aviation+HF is in scope |
| Reviewer challenges single-subject worked example | Medium | Frame explicitly as "framework instantiation illustration, not an empirical test"; move all inferential-sounding language to Limitations |
| Open-source component triggers reviewer concerns about reproducibility | Low-Medium | Cite tagged release DOI in cover letter (commit 11), document environment fully, include a minimal Docker path in Supplementary |

---

*End of novelty and venue recommendation.*
