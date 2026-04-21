# Author: Dr Diego Malpica MD

## Validation Story (OPI methodology paper)

This document defines the evidence posture for the manuscript so that Methods, Results, and Discussion sections remain defensible under Q1 HF review. Supersedes the prior systems-and-software validation story.

## Recommended manuscript stance

Treat the paper as a **methodology + reference implementation** contribution with:

- a theoretically grounded framework definition (OPI components + per-task weight profiles + vigilance/latency penalties),
- inspectable reference code with engineering verification across the fusion pathway,
- a single illustrative worked example demonstrating the pipeline end-to-end,
- explicit acknowledgement that field validation in operator populations is the next study.

The paper should not claim diagnostic accuracy, outcome benefit, clinical deployment readiness, or validated numerical parity with any external HRV or fatigue package.

## Evidence tiers

| Evidence tier | Current repository status | Can it appear in Results? | How to frame it |
| --- | --- | --- | --- |
| Framework definition (OPI equations, taxonomy, weights) | Strong (HF literature-grounded) | Yes | Describe as theory-derived framework; reference source literature for each component and weight. |
| Reference implementation | Strong | Yes | Describe as implemented software with code anchors; include repo URL and frozen release identifier. |
| Engineering verification of fusion logic | Strong for several modules | Yes | Report as software verification, not as operational validation. |
| Illustrative worked example (single 128-min recording) | Present | Yes, with explicit illustration framing | Treat as framework-instantiation demonstration, not as inferential data. |
| External numerical agreement with reference HRV package | Not assembled | No, explicitly out of scope | Move to limitations and future validation. |
| External benchmarking vs. alternative operator-readiness frameworks | Not assembled | No | Position as future work; cite Stevens 2022, Feng 2018, Vogl 2025 as candidate comparators. |
| Prospective or retrospective human-subject validation | Not assembled | No | Requires protocol, endpoints, and ethics documentation. |
| Regulatory certification or compliance evidence | None | No | Discuss intended alignment with NASA-STD-3001 and ICAO Doc 9966 only; never as certification. |

## What is already strong enough to report

### 1. OPI framework formulation

The repository's `analysis/operational_performance_indicators_research.md` contains the full framework derivation:

- Four-component weighted fusion for manned aviation (`OPI_task = w1·SAFTE_eff·Task_mod + w2·HRV_recovery + w3·Autonomic_reserve - Stress_penalty - Task_complexity_penalty`)
- Extended formulation for UAS (`OPI_UAS = w1·SAFTE_eff + w2·Vigilance_adj + w3·HRV_recovery + w4·Attention_capacity - Latency_penalty - Multi_vehicle_penalty`)
- Per-task weight profiles for 10 manned and 7 UAS task categories
- Task-complexity modifiers (0.70-1.0 depending on conditions)
- Readiness categories (GO / GO-Monitor / CAUTION / NO-GO) with score bands
- Theoretical grounding in MRT (Wickens 2002, 2008), SAFTE (Hursh 2004), vigilance decrement (Warm 2008), latency (Chen 2007), allostatic load (McEwen 1998), cognitive readiness (Fletcher 2019), Yerkes-Dodson (Teigen 1994)

These are all directly supported by the framework document and prior HF literature. They can be reported in Methods as theory-derived framework specifications.

### 2. Reference implementation

The Python backend (`app/fatigue_calculator/safte_model.py`, `app/hrv_core.py`, `app/scheduling_core.py`, `app/frms.py`, `app/frms_v2.py`) implements the OPI components. The TypeScript client mirror (`frontend/src/lib/safte-model.ts`) reproduces the SAFTE equations for responsive operational displays. The FastAPI orchestration layer (`api/main.py`, `api/research_endpoints.py`) exposes the pathway for web-delivered consumption. The repository is open-source under the MIT license at https://github.com/strikerdlm/HRV.

### 3. Engineering verification

The repository's test surface verifies representative behaviours across the OPI pathway:

- `tests/test_scheduling_core.py` — readiness fusion and task-complexity behaviour
- `tests/test_frms.py`, `tests/test_frms_v2.py` — FRMS and SAFTE-adjacent logic
- `tests/test_fatigue_integration.py` — fatigue component integration
- `tests/test_comprehensive_modules.py` — broader statistical and charting modules
- `tests/test_api_user_profile_normalization.py` — API input normalisation
- `tests/test_research_windowed_endpoint.py` — endpoint behaviour (with monkeypatched HRV inner calls)
- `tests/test_pvt_core.py` — PVT trial classification, session metrics, variant scaling, operational gate
- `tests/test_sleep_core.py` — stage balance, sleep debt, Sleep Regularity Index, SpO₂ screening bands, FDR-adjusted correlation engine

This supports a Results subsection on engineering verification of the fusion pathway, bounded to software behaviour.

### 4. Illustrative worked example (once executed)

The single 128-minute HRV recording in `analysis/hrv_report_complete_20251124T020445Z.md` (8,553 RR intervals, 2025-11-23) supports an illustrative worked example: the pipeline can be run end-to-end (RR → HRV metrics → SAFTE effectiveness estimate → OPI composite) under three hypothetical task scenarios (e.g., IMC approach, UAS ISR sortie, carrier landing) to demonstrate how the same physiological input yields task-specific readiness outputs.

This is standard HF methodology-paper practice: frame the example as a framework instantiation, not as inferential data. Explicitly state in Methods and Results that the worked example does not generalise beyond the single recording.

## Important caveats for the Results section

### 1. The worked example is not an empirical test

The single-subject 128-minute recording demonstrates the pipeline and produces illustrative numbers. It does not test whether the OPI predicts operator outcomes. All Results prose must make this explicit.

### 2. OPI weights are theory-derived, not empirically calibrated

Per-task weights (`w1`, `w2`, `w3`, `w4`) are derived from HF literature on task demands and Multiple Resource Theory. They have not been optimised against field performance data. The Methods section must trace each weight to its source references.

### 3. HRV numerics are implemented but not externally benchmarked

`app/hrv_core.py` is part of the reference implementation. External numerical agreement with Kubios, pyHRV, or NeuroKit2 is explicitly out of scope for this paper. This is stated as a limitation, not hidden.

### 4. Endpoint tests are stronger than some underlying analytic benchmarks

`tests/test_research_windowed_endpoint.py` verifies endpoint plumbing while monkeypatching `hrv_core.compute_windowed_hrv`. This is valuable engineering evidence for the orchestration layer but not evidence about HRV numerical correctness. Describe accurately.

### 5. Client-side SAFTE mirror is architectural consistency

`frontend/src/lib/safte-model.ts` is a TypeScript re-implementation of the Python canonical SAFTE model. It serves responsive operational displays. It is not an independent validation layer.

### 6. The experimental space-weather modifier is out of scope for this manuscript

The experimental NOAA space-weather modifier layer has been retired from the manuscript narrative. Any remaining single-subject HRV↔space-weather correlation CSVs are not part of this submission and would require their own dedicated, pre-registered protocol with appropriate handling of within-subject autocorrelation before any environmental-modifier claim could be advanced.

## Recommended Results structure

### 3.1 Illustrative worked example

Run the 128-min recording through the OPI pipeline under three hypothetical task scenarios. Present the per-window OPI time-series for each scenario, the resulting readiness-category assignments, and how the task-specific weight profile changes the composite output for identical physiological input. Figure 3 shows this visually. Table 2 provides numerical summary.

### 3.2 Engineering verification of the OPI fusion pathway

Summarise test-backed behaviour by OPI component: readiness fusion orchestration, SAFTE/FRMS logic, API normalisation and endpoint behaviour. Table 5 provides the coverage map. Explicitly delimit this as software verification, not operational validation.

### 3.3 Reproducibility and availability

Report repository URL, license, environment specifications, frozen release identifier (once issued), and export utilities. Cite the reproducibility literature (Sandve 2013) for reporting-guideline alignment.

## Claims that should remain out of scope

Do not claim any of the following without new evidence:

- diagnostic or predictive accuracy of the OPI against operator outcomes,
- performance or safety benefits of OPI-informed decisions,
- validated numerical parity of the HRV engine with reference packages,
- validated parity between Python canonical SAFTE and TypeScript client mirror,
- generalisability of the worked example beyond the single recording,
- causal inference about environmental modifiers on autonomic state,
- regulatory clearance, fitness-for-duty determination, or certification.

## Minimal evidence package needed for a follow-up validation paper

1. A multi-subject field dataset with operator performance outcomes (simulator or operational) for the target task categories. The first such dataset is planned from the 2026–2027 Colombian Antarctic aerial campaign: a Colombian Air Force C-130 Hercules conducting multi-leg Drake Passage sorties during the austral summer, instrumented with the ActiGraph wGT3X-BT wrist accelerometer (Buchan, 2024) and the Polar H10 chest-strap electrocardiogram (Pereira et al., 2020; Hinde et al., 2021; Yang & Ben-Menachem, 2024).
2. Ethics approval and consent documentation.
3. External numerical benchmarking of `app/hrv_core.py` against reference HRV software (Kubios, pyHRV, NeuroKit2).
4. External benchmarking of the OPI composite against alternative frameworks (Stevens 2022 CMP, Feng 2018 logistic, Vogl 2025 SVM).
5. Sensitivity analysis of the per-task weights against field performance variance.
6. A tagged release or Zenodo DOI matched to the reported validation version.
