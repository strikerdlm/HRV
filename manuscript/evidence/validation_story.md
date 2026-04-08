# Author: Dr Diego Malpica MD

## Validation Story

This document defines the evidence posture for the manuscript so that the Methods and Results sections remain defensible.

## Recommended manuscript stance

Treat the paper as a **translational systems and software manuscript** with:

- strong implementation evidence,
- meaningful engineering verification across several operational paths,
- selective use of exploratory quantitative artifacts,
- explicit acknowledgment that integrated human-subject validation is still incomplete.

The paper should therefore distinguish between **software verification**, **exploratory empirical outputs**, and **future formal validation**.

## Evidence tiers

| Evidence tier | Current repository status | Can it appear in Results? | How to frame it |
| --- | --- | --- | --- |
| Architecture and implementation | Strong | Yes | Describe as implemented system capabilities with code anchors. |
| Unit and integration tests | Strong for several operational modules | Yes | Report as engineering verification, not as clinical validation. |
| Exported exploratory analyses | Present but not yet fully curated | Cautiously | Use only if provenance, cohort description, and analysis protocol can be documented. |
| External numerical agreement against a reference HRV package | Not yet assembled for the integrated platform | No, unless added | Move to limitations or future validation. |
| Prospective or retrospective human-subject validation of the full platform | Not identified as manuscript-ready in the repo | No | Requires protocol, endpoints, and ethics details. |
| Regulatory certification or compliance evidence | Not present | No | Discuss intended alignment and deployment pathway only. |

## What is already strong enough to report

### 1. Platform implementation

The repository clearly supports a system-level Methods and Results section around:

- the shared Python analysis core,
- the Next.js frontend and FastAPI orchestration layer,
- the secondary Streamlit interfaces retained in the repository,
- the user-profile persistence layer,
- the SAFTE/circadian model layer,
- the scheduling and readiness fusion logic,
- the space-weather ingest, propagation, and alignment modules,
- the export and reproducibility utilities.

These claims are architecture claims and are directly supported by repository files.

### 2. Engineering verification

The test surface is strongest for the modules that matter most to an operational paper:

- `tests/test_scheduling_core.py`
- `tests/test_frms.py`
- `tests/test_frms_v2.py`
- `tests/test_fatigue_integration.py`
- `tests/test_space_weather_impact.py`
- `tests/test_noaa_cache.py`
- `tests/test_space_weather_alignment.py`
- `tests/test_comprehensive_modules.py`
- `tests/test_api_user_profile_normalization.py`

This supports a Results subsection centered on software verification, deterministic rule behavior, and model-layer implementation.

### 3. Quantitative artifacts that may be usable

The repository contains exported correlation outputs such as:

- `analysis/noaa_batch_correlations_20251124T020423Z.csv`
- `analysis/noaa_batch_correlations_20251123T224453Z.csv`

These show that the code can generate lagged correlation outputs with confidence intervals and sample sizes. However, they should enter the manuscript only if the underlying study context is made explicit:

- who or what generated the observations,
- how recordings were selected,
- what preprocessing rules were used,
- whether multiple files or participants were pooled,
- what the intended inferential scope is.

Without that provenance, these artifacts are best treated as **demonstrations of implemented analysis capability** rather than definitive scientific findings.

## Important caveats for the Results section

### 1. Core HRV numerics are implemented but not yet externally benchmarked

`app/hrv_core.py` is central to the paper, but the repository does not yet expose a manuscript-ready benchmark against a trusted reference package or public test vectors. The manuscript can therefore describe:

- what the engine computes,
- how it is integrated,
- how it is parameterized,

but should not claim proven numerical equivalence to an external gold standard unless that benchmark is added.

### 2. Endpoint tests are stronger than some underlying analytic benchmarks

`tests/test_research_windowed_endpoint.py` verifies endpoint behavior and data plumbing, but it explicitly monkeypatches `hrv_core.compute_windowed_hrv` during the test setup. This means the endpoint pathway is verified more directly than the underlying numerical implementation.

That is still valuable engineering evidence, but the manuscript should phrase it accurately.

### 3. Client-side model mirroring is not independent validation

The repository includes a TypeScript SAFTE implementation under `frontend/src/lib/safte-model.ts` that mirrors the canonical Python implementation in `app/fatigue_calculator/safte_model.py`. This is valuable evidence for architectural consistency between the Node-first client and backend model stack. However, it should not be treated as a second validation source. The manuscript should describe the mirrored implementation as consistency-oriented delivery logic unless explicit parity testing is added.

### 4. Exploratory correlation outputs are not the same as validated scientific findings

The presence of effect sizes, confidence intervals, and p-values in exported CSV files does not by itself establish a publishable validation study. The manuscript must first document:

- the analytical population,
- the unit of analysis,
- time-alignment rules,
- missing-data handling,
- multiplicity control,
- and the intended causal or associative interpretation.

## Recommended Results structure

### 3.1 System implementation summary

Report Node-first delivery, FastAPI orchestration, model layering, and module coupling. This is the strongest Results subsection available today.

### 3.2 Engineering verification

Summarize test-backed evidence by domain:

- readiness fusion and IHPI scoring,
- SAFTE/fatigue and FRMS logic,
- space-weather ingest, propagation, and alignment,
- API normalization and Node-client-facing endpoint behavior,
- export and reporting helpers.

### 3.3 Reproducibility and operational artifacts

Report:

- repository URL,
- branch and commit hash,
- environment expectations,
- export utilities,
- logging and audit infrastructure.

### 3.4 Optional exploratory analysis vignette

Include only if provenance can be documented clearly. If not, move these materials to Supplementary Demonstrations or omit from the main Results section.

## Claims that should remain out of scope

Do not claim any of the following without new evidence:

- diagnostic accuracy,
- patient or crew outcome improvement,
- real-world deployment effectiveness,
- fairness or subgroup robustness,
- regulatory clearance,
- generalizable clinical benefit across populations,
- validated numerical parity with external reference software.

## Minimal evidence package needed for a stronger future paper

1. Reference benchmarking for `app/hrv_core.py` against known HRV outputs.
2. A curated retrospective or prospective dataset with explicit cohort and protocol details.
3. Study-specific ethics approval and consent materials if human data are reported.
4. A tagged software release or archived DOI corresponding to the reported version.
5. A small set of benchmark tasks linking operational use cases to measurable outcomes.
