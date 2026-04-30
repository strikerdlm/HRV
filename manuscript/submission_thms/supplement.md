# Supplementary Material

**Manuscript:** Task-calibrated Operational Performance Indicators for aviation and unmanned aircraft system operators: a biomathematical human-machine systems framework.
**Target venue:** IEEE Transactions on Human-Machine Systems.
**Authors:** Diego L. Malpica MD; Ingrid Xiomara Bejarano Cifuentes.

This supplement collects reference-implementation detail, the full engineering-verification matrix, and ancillary materials referenced from the main text. The supplement is not required to follow the manuscript narrative; it is provided as inspectable backing for reviewers and adopters.

---

## S1. Reference-implementation architecture and module manifests

### S1.1 Architecture

The reference implementation separates client delivery from model execution while keeping the computational core as a single Python stack. Three logical layers are addressed:

1. **Client layer.** A Next.js / TypeScript web client under `frontend/` exposes operational and research routes. Charts and visualizations use Apache ECharts. The client communicates with the orchestration layer via REST endpoints.
2. **Orchestration layer.** A FastAPI service under `api/` exposes structured endpoints for HRV analysis (`api/main.py`), Psychomotor Vigilance Task scoring (`api/pvt_endpoints.py`), and research utilities (`api/research_endpoints.py`).
3. **Analytic core.** A shared Python module suite under `app/` hosts the HRV engine, SAFTE reservoir model, readiness-fusion logic, PVT, sleep, and trajectory-risk modules.

A client-side TypeScript SAFTE mirror (`frontend/src/lib/safte-model.ts`) reproduces the Python reservoir equations for responsive operational displays. This is treated as architectural consistency rather than an independent validation layer; formal parity testing is identified as future work.

### S1.2 Module manifest

| Module | File | Role |
|---|---|---|
| HRV engine | `app/hrv_core.py` | Time-, frequency-, and nonlinear-domain HRV metrics with bounded artefact heuristics |
| SAFTE reservoir | `app/fatigue_calculator/safte_model.py` | Two-process biomathematical fatigue effectiveness |
| Circadian models | `app/circadian/` | Forger99, Jewett99, Hannay19 phase models |
| Readiness fusion | `app/scheduling_core.py`, `app/scheduling_engine.py`, `app/frms.py`, `app/frms_v2.py` | Per-task OPI composition, gate logic, scheduling integration |
| PVT module | `app/pvt_core.py`, `api/pvt_endpoints.py`, `frontend/src/lib/pvt-scoring.ts` | PVT-B, PVT-5, PVT-10 administration and scoring; ≥20-lapse hard gate |
| Sleep module | `app/sleep_core.py`, `api/research_endpoints.py` | Sleep debt, Sleep Regularity Index, stage-balance proportions, four-band low-SpO₂ screening proxy |
| Trajectory-risk module | `app/trajectory_risk.py` | EWMA-based cumulative-strain modifier aligned with allostatic-load construct |
| Logging | `app/logging_config.py` | Centralized `get_logger(__name__)` infrastructure |
| Persistence | `app/user_database.py` | SQLite user and session persistence |
| Space-weather ingestion | `app/noaa_space.py` | NOAA space-weather data ingest (optional environmental modifier) |

### S1.3 Execution environment

The documented primary execution environment is Python 3.12 with dependencies declared in `requirements.txt`. The primary client is a Next.js application with dependencies under `frontend/package.json`. The repository ships with the test suite described in S2 and the worked-example artefacts referenced in the main text.

### S1.4 Reference-implementation availability

- **Source:** `https://github.com/strikerdlm/HRV` under the MIT license.
- **Frozen release:** A tagged release with archived Zenodo DOI corresponding to the reported manuscript version will be created and cited in the camera-ready.
- **Worked example:** `analysis/opi_worked_example.py` (script) and `analysis/opi_worked_example.json` (derived artefact).

---

## S2. Engineering-verification coverage (full)

This table extends the summary in main-text Table IV. Each row is a layer of the OPI fusion pathway with the representative tests or artefacts that exercise it, what is verified, the manuscript-safe interpretation, and explicit boundaries.

| Layer | Representative tests / artefacts | What is verified | Manuscript-safe interpretation | Boundary or caveat |
|---|---|---|---|---|
| HRV analytic core | `app/hrv_core.py`; `tests/test_research_windowed_endpoint.py` | The HRV computation layer is wired into endpoint workflows and executes through repository pathways | Implementation evidence and endpoint connectivity | Stronger as implementation evidence than as external numerical benchmark; Kubios / pyHRV / NeuroKit2 parity is future work |
| SAFTE / circadian model | `tests/test_frms.py`; `tests/test_frms_v2.py`; `tests/test_fatigue_integration.py`; `frontend/src/lib/safte-model.ts` | Fatigue-model behaviour, FRMS scoring, mirrored client/backend fatigue logic | Explicit fatigue-governance and circadian-modeling layer present | Not a substitute for prospective fatigue-outcome validation or full client/backend parity testing |
| Readiness fusion and scheduling | `tests/test_scheduling_core.py` | Deterministic threshold logic, score composition, rule behaviour for operational pathways | Readiness fusion is implemented and regression-tested | Does not establish real-world mission effectiveness |
| PVT vigilance module | `tests/test_pvt_core.py`; `api/pvt_endpoints.py`; `frontend/src/lib/pvt-scoring.ts` | Canonical PVT scoring, variant scaling, operational-gate integration; 28 tests | PVT module is implemented and regression-tested as a vigilance-related input | Browser-PVT timing inherits published web-PVT precision bounds (≈5–10 ms) rather than independent hardware validation in this manuscript |
| Sleep analytics module | `tests/test_sleep_core.py`; `app/sleep_core.py`; `api/research_endpoints.py` | Sleep debt, SRI, screening bands, gate behaviour, correlation engine with Benjamini-Hochberg FDR; 27 tests | Sleep module is implemented and regression-tested | Not a substitute for polysomnography validation or clinical sleep diagnosis |
| Longitudinal trajectory-risk module | `app/trajectory_risk.py` | EWMA-based longitudinal modifier and risk classification implemented | Implemented longitudinal adjustment layer | Dedicated regression tests not yet present; do not frame as regression-tested |
| API-backed web delivery | `tests/test_api_user_profile_normalization.py`; `tests/test_research_windowed_endpoint.py` | Profile normalization, request/response behaviour, endpoint-level analytical pathways | Web-delivery and reproducibility for tested pathways | Endpoint verification is stronger than underlying numerical-benchmark evidence |
| Reporting and export | `tests/test_comprehensive_modules.py` | Statistical helper behaviour and parts of the reporting surface | Reporting utilities are software-backed rather than ad hoc | Should not be framed as validation of every downstream analytic interpretation |

### S2.1 Test inventory summary

- Total test count: 421 tests across `tests/`
- PVT: 28 tests (`tests/test_pvt_core.py`)
- Sleep: 27 tests (`tests/test_sleep_core.py`)
- Scheduling-core readiness fusion: covered by `tests/test_scheduling_core.py`
- Fatigue-risk-management and SAFTE-adjacent: `tests/test_frms.py`, `tests/test_frms_v2.py`, `tests/test_fatigue_integration.py`
- API endpoint normalization and behaviour: `tests/test_api_user_profile_normalization.py`, `tests/test_research_windowed_endpoint.py`
- Statistical and charting modules: `tests/test_comprehensive_modules.py`

### S2.2 What this table does *not* cover

- External numerical benchmarking of the HRV engine against Kubios, pyHRV, or NeuroKit2 — future work.
- Operator-outcome validation of OPI gate decisions — future work; planned with the prospective field campaign described in §4.6.
- Formal parity testing of the client-side TypeScript SAFTE mirror against the canonical Python implementation — future work.
- Dedicated regression tests for the longitudinal trajectory-risk module — future work.

---

## S3. Worked-example reproducibility

The 128-minute illustrative recording, representative five-minute window generation, and three task-hypothesis OPI computations are reproducible from `analysis/opi_worked_example.py`. The script consumes recording-level summary statistics and outputs `analysis/opi_worked_example.json` containing time-series for each task hypothesis (`opi_ils`, `opi_isr`, `opi_carrier`), category assignments, and the four component time-series (HRV recovery, autonomic reserve, attention capacity, SAFTE effectiveness, stress index, vigilance adjustment for the ISR hypothesis). The artefact contains 80 windows (`t_minutes` length 80), spanning the 128-minute recording duration at 1.6-minute spacing.

Re-running the worked example requires only a Python 3.12 environment with the dependencies declared in `requirements.txt`. The script is deterministic: representative-window generation uses a fixed pseudo-random seed.

---

## S4. HRV-engine benchmark extension protocol

Section~3.3 of the main manuscript reports a numerical benchmark of the OPI HRV engine against NeuroKit2 [Makowski 2021] on the MIT-BIH Normal Sinus Rhythm Database [Goldberger 2000], for time-domain and Poincaré metrics. Extension to frequency-domain and entropy metrics follows the same ICC(2,1) + Bland-Altman protocol on the same dataset, and is in progress at the time of this submission.

**Frequency-domain extension.** LF (0.04–0.15 Hz), HF (0.15–0.40 Hz), and LF/HF ratio computed via the same 5-minute non-overlapping windows. The benchmark requires a temporal sampling-rate parameter for NeuroKit2 of at least 1000 Hz to avoid resampling artefacts that suppressed agreement at the 250 Hz default attempted in the initial benchmarking run; we report this as a methodological note for downstream replication.

**Entropy extension.** Sample entropy (m=2, r=0.2 × SD) and DFA-α1 (window 4–16) computed on the same RR series for both engines. Differences in entropy implementations between engines (in particular, embedding-distance computation choice) are documented as part of the benchmark protocol.

**Reporting.** Final results will be appended to `benchmark_summary.json` and `benchmark_results.csv` in the public repository under `manuscript/submission_thms/tex/benchmark/`. The repository tag corresponding to the camera-ready manuscript will include the extended benchmark.

---

## S5. Reporting-guideline positioning

This manuscript is a methodology and reference-implementation paper. The central claims are framework definition, implementation, illustrative demonstration, and a deterministic numerical benchmark of the HRV engine. The evidence base does not include prospective human-subject outcomes or predictive-accuracy evaluation. Reporting therefore emphasizes transparent description of framework components, per-task parameterization, reference-implementation architecture, and engineering verification.

If future versions add empirical validation, adapted STROBE elements will be incorporated for observational designs, and TRIPOD+AI or CLAIM extensions will apply only to sections making predictive-model claims. SAGER-aligned analysis and reporting will be added if the empirical work permits sex- and gender-stratified analysis.

---

## S6. Architectural reference figure

The reference-implementation architecture figure (a Next.js client over a FastAPI orchestration layer and a shared Python analytic core) is provided in Fig. S1.

![Fig. S1. Reference-implementation architecture.](../05_figures/figure4_reference_implementation_architecture.png)

**Fig. S1.** Reference-implementation architecture. The Next.js client communicates with a FastAPI orchestration layer that exposes structured endpoints for HRV analysis, scheduling and readiness, user-profile management, and research utilities; the shared Python analytic core under `app/` hosts the HRV engine, SAFTE reservoir model, readiness-fusion logic, PVT, sleep, and trajectory-risk modules.

---

**Note on supplement section labelling.** In the main manuscript, forward references to Supplement S1 (architecture/module manifests) and Supplement S2 (full engineering-verification coverage matrix) point to the corresponding sections above. The S3 (worked-example reproducibility), S4 (benchmark extension protocol), S5 (reporting-guideline positioning), and S6 (architecture figure) sections provide additional reviewer-facing material referenced from Sections 2.5, 3.3, 4.5, and 6 of the main manuscript.
