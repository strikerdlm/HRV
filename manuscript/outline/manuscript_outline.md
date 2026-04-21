# Author: Dr Diego Malpica MD

## Manuscript Outline (Q1 HF reframe — OPI methodology paper)

Supersedes the prior biomedical-computing framing. This outline is the authoritative plan for the `q1-hf-opi-reframe` branch. Historical rationale and literature verification: `manuscript/outline/novelty_and_venue_2026-04-21.md`.

## Working title

**Task-calibrated Operational Performance Indicators (OPI) for aviation and unmanned aircraft system operators: a biomathematical framework integrating SAFTE fatigue, heart-rate variability, and cognitive-load theory, with open-source reference implementation**

### Alternative titles

1. Task-calibrated operator readiness fusion: an open biomathematical framework integrating fatigue, autonomic, and cognitive-load components for aviation and UAS
2. An open Operational Performance Indicator framework for aerospace operators: task-specific fusion of SAFTE, HRV, and Multiple Resource Theory with reference implementation

### Running title

Task-calibrated OPI for aerospace operators

## Central thesis

Existing operator-state research ships either (a) one-off machine-learning classifiers on raw physiological signals or (b) isolated fatigue or workload models that cover only a narrow task slice. None ship a **task-calibrated, per-operator composite readiness index** grounded in Multiple Resource Theory (MRT), Yerkes-Dodson arousal-performance mapping, allostatic load, and cognitive-readiness constructs, with open-source reference implementation spanning both manned-aviation and UAS operator categories.

This manuscript contributes the **Operational Performance Indicator (OPI) framework**: a weighted fusion of SAFTE reservoir fatigue effectiveness, HRV-derived autonomic markers, MRT-derived cognitive-load modifiers, and environmental/operational modifiers, with per-task weight profiles and thresholds specified for ten manned-aviation task categories and seven UAS operator categories. The framework is distributed as open-source reference code delivered through a Next.js client over a FastAPI orchestration layer and a shared Python biomathematical backend. Evidence is bounded to framework definition, engineering verification, and a single illustrative worked example; field validation in operator populations is stated as the next research step.

## Target venue

**Primary:** Applied Ergonomics (Elsevier). Q1 in Human Factors and Ergonomics. JIF 3.4 (2024). Explicit scope for methodology papers in aerospace/military HF. Recent precedent: Berthon L, Bernard F, Fleury S, Paquin R, Richir S. (2025). *Applied Ergonomics* 129, 104599. doi:10.1016/j.apergo.2025.104599.

**Secondary:** Human Factors (HFES/SAGE). JIF 5.72. Higher bar; reframe for situation-awareness/readiness tradition if needed.

**Tertiary:** Sensors (MDPI). Q1 in Instruments & Instrumentation. JIF 3.5. Many HRV + operator monitoring precedents.

## Section plan (Applied Ergonomics target)

| Section | Target content | Main evidence sources | Target length |
| --- | --- | --- | --- |
| Title and structured abstract | Gap, framework, illustrative example, bounded conclusions | `manuscript/evidence/validation_story.md` | 250-350 words |
| 1. Introduction | HF gap: no open task-calibrated operator-readiness composite for aviation + UAS; cite recent reviews (Li 2025, Hamann 2025, Rabat 2025) as gap anchors; contribution statement | `manuscript/tables/opi_task_taxonomy.md`, `analysis/operational_performance_indicators_research.md` | 900-1,200 words |
| 2. Methods | 2.1 Framework formulation (OPI equations, MRT grounding, component choice); 2.2 Task taxonomy; 2.3 Per-task weight profiles; 2.4 Vigilance-decrement and latency-penalty models; 2.5 Reference implementation; 2.6 Worked-example methodology | `analysis/operational_performance_indicators_research.md`, `manuscript/tables/*` | 1,800-2,400 words |
| 3. Results | 3.1 Framework-instantiation worked example (128-min recording → OPI outputs for three task hypotheses); 3.2 Engineering verification of fusion logic; 3.3 Reference-implementation reproducibility | `manuscript/evidence/evidence_matrix.md`, `analysis/hrv_report_complete_*.md`, `tests/` | 900-1,300 words |
| 4. Discussion | Methodology contribution vs. Feng 2018, Stevens 2022, Vogl 2025; mechanistic interpretation of composite index; limitations; validation roadmap | `manuscript/evidence/evidence_matrix.md`, `manuscript/evidence/compliance_and_transparency_map.md` | 1,100-1,500 words |
| 5. Conclusion | Bounded methodology claim; next-steps statement | — | 120-180 words |
| Compliance and transparency | Data/code availability, ethics, standards framing, CRediT, funding, COI | `manuscript/evidence/compliance_and_transparency_map.md` | 300-500 words |

**Total word budget:** 5,200-6,900 words. Applied Ergonomics has a soft 8,000-word limit for research articles including references.

## Planned tables

1. **Table 1. OPI task taxonomy** — 17 task categories × primary demands × HRV signatures × failure modes — `manuscript/tables/opi_task_taxonomy.md`
2. **Table 2. OPI component formulation and weight profiles** — per-task w1/w2/w3/w4 weights + modifiers — `manuscript/tables/opi_weight_profiles.md`
3. **Table 3. Vigilance-decrement and control-latency models** — λ per task, latency penalty coefficients — `manuscript/tables/opi_vigilance_latency_models.md`
4. **Table 4. Related-work comparison** — OPI vs. adjacent published frameworks (Feng 2018, Stevens 2022, Vogl 2025, Li 2025, Berthon 2025) — `manuscript/tables/literature_gap_comparison.md` (to be refreshed)
5. **Table 5. Engineering verification coverage by OPI component** — tests that exercise each layer — `manuscript/tables/engineering_verification_coverage.md` (to be refreshed)
6. **Table 6. Reproducibility and deployment metadata** — repo URL, license, environment, frozen release — `manuscript/tables/reproducibility_and_deployment_metadata.md` (minor refresh)
7. **Table 7. Compliance and transparency declarations** — `manuscript/tables/compliance_and_transparency_declarations.md` (minor refresh)

## Planned figures

1. **Figure 1. OPI conceptual schematic** — four-component fusion diagram with inputs, weights, modifiers, output categories
2. **Figure 2. Task taxonomy and HRV signatures** — 17 task categories × dominant autonomic patterns, organised for quick-read clinical/operational interpretation
3. **Figure 3. Illustrative worked example** — 128-min recording fed through OPI for three task hypotheses (IMC approach, UAS ISR, carrier landing) with composite outputs and category assignment over time
4. **Figure 4. Reference-implementation architecture** — Node-first Next.js client + FastAPI orchestration + shared Python model stack, simplified to show OPI pathway

Details in `manuscript/figures/figure_plan_opi.md` (to be created). Existing SVG assets from the prior framing can be reused or updated rather than redrawn from scratch where the content still holds.

## Writing order

1. Commit this outline (done in the same branch sequence).
2. Refresh `evidence/evidence_matrix.md` and `evidence/validation_story.md` to match the OPI framing.
3. Draft the three OPI tables first (taxonomy → weights → vigilance/latency). These are the spine; Methods writes from them.
4. Draft Methods section from the tables.
5. Draft Results from the worked example + test coverage.
6. Draft Introduction last (after Methods is stable so the gap statement aligns).
7. Draft Discussion last (after all empirical and methodological content is fixed).
8. Draft Compliance section after authorship/funding are confirmed.
9. Cover letter and highlights after the draft is assembled.

## Q1 journal targeting — final

Checked April 2026 via Clarivate/SCImago/Resurchify + journal websites. Full verification notes in `manuscript/outline/novelty_and_venue_2026-04-21.md`.

| Journal | JIF 2024 | Q-category | Current fit | Packaging implication |
| --- | --- | --- | --- | --- |
| **Applied Ergonomics** (Elsevier) | **3.4** | **Q1 Human Factors & Ergonomics** | **Primary target** | Methodology paper + reference implementation + illustrative example; hedged evidence tiering; 79-day first-decision |
| Human Factors (HFES/SAGE) | 5.72 | Q1 flagship HF | Secondary | Higher bar; reframe for SA/readiness theoretical contribution if needed |
| Sensors (MDPI) | 3.5 | Q1 Instruments & Instrumentation | Tertiary | Faster turnaround; OA APC required; many HRV+wearable precedents |
| Frontiers in Neuroergonomics | 1.9 | Q2 HF&E | Specialty fallback | Specialty fit; below Q1 threshold |

### Recommended submission order

1. **Primary:** Applied Ergonomics
2. **Secondary (if AE rejects):** Human Factors
3. **Tertiary (faster turnaround):** Sensors
4. **If Q1 target relaxed:** Frontiers in Neuroergonomics

### Explicit exclusions

- **CMPB, JBI, npj Digital Medicine** — excluded by author instruction; require numerical validation the repository does not yet support.
- **Aerospace Medicine and Human Performance** — not Q1.
- **Military Psychology** — not Q1.

## Scope guardrails

1. The paper is a **methodology + reference implementation** paper. It does not claim validated operational outcomes, diagnostic accuracy, or regulatory clearance.
2. The single 128-min HRV recording is treated as an **illustrative framework-instantiation worked example**. It is not inferential data. All language in Results must be consistent with this framing.
3. Space-weather modules are kept as an optional environmental modifier only. The single-subject HRV↔space-weather correlation CSVs move to supplementary demonstrations. No autonomic↔solar causal claim is made.
4. Regulatory standards (NASA-STD-3001, ICAO Doc 9966) are **alignment**, not certification. Continue to use "informed by", "aligned with", or "designed with reference to".
5. Per-task OPI weights are **theory-derived from HF literature**. External empirical calibration against field performance data is stated as future work.
6. TypeScript client-side SAFTE mirror is **architectural consistency**, not an independent validation layer.
