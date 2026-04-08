# Author: Dr Diego Malpica MD

## Supplementary Appendix

This appendix consolidates supplementary material that strengthens the manuscript as a systems-and-modeling submission without expanding unsupported scientific claims. It focuses on engineering verification, model-layer notes, standards crosswalks, reporting positioning, and deployment prerequisites.

## S1. Extended engineering verification inventory

The main manuscript reports engineering verification at a summary level. The table below provides a more explicit inventory of representative software pathways, test anchors, and the corresponding claim boundary.

| Workflow area | Representative files | What is supported | Safe manuscript interpretation | What remains out of scope |
| --- | --- | --- | --- | --- |
| Scheduling, readiness, and IHPI-style logic | `app/scheduling_core.py`, `app/scheduling_engine.py`, `tests/test_scheduling_core.py` | Deterministic scoring rules, threshold behavior, and regression-tested decision pathways. | The platform includes implemented and tested operational decision-support logic. | Real-world mission benefit, decision accuracy, or deployment outcome improvement. |
| FRMS and fatigue pathways | `app/frms.py`, `app/frms_v2.py`, `app/fatigue_integration.py`, `tests/test_frms.py`, `tests/test_frms_v2.py`, `tests/test_fatigue_integration.py` | Rule-based fatigue integration and FRMS-related software behavior. | The fatigue layer is implemented as inspectable software rather than as opaque heuristics. | Prospective validation of fatigue predictions in operational cohorts. |
| Space-weather ingestion and caching | `app/noaa_space.py`, `tests/test_noaa_cache.py`, `tests/test_space_weather_impact.py` | NOAA ingest, cache behavior, and impact-model plumbing. | Environmental context is implemented as a tested software layer. | Proof that the environmental layer yields clinically validated interpretations. |
| Space-weather alignment workflows | `app/space_weather_alignment.py`, `tests/test_space_weather_alignment.py` | Alignment of environmental and physiological timelines. | The repository supports cross-domain temporal alignment and exploratory coupling. | Publication-grade claims from exploratory outputs without cohort provenance. |
| API and web-delivery pathways | `api/main.py`, `tests/test_api_user_profile_normalization.py`, `tests/test_research_windowed_endpoint.py` | Endpoint behavior, normalization, and shared-core delivery. | The Node-first delivery architecture is backed by testable service behavior. | End-user usability claims or deployment adoption claims without dedicated study data. |
| Reporting and export utilities | `app/publication_export.py`, `app/export_utils.py`, `tests/test_comprehensive_modules.py` | Structured statistical outputs, supporting exports, and some reporting helpers. | Reporting support is a first-class implementation concern in the repository. | Full manuscript reproducibility guarantees without a tagged release or archived DOI. |

## S2. Canonical model-layer notes

The main manuscript centers the following modeling layers. The notes below clarify what should be treated as canonical, mirrored, or contextual.

### HRV analytic core

- Canonical implementation: `app/hrv_core.py`
- Main manuscript framing: deterministic preprocessing plus standards-informed time-domain, frequency-domain, nonlinear, and windowed HRV metrics
- Reviewer caveat: explicit code-level implementation is strong, but external benchmark parity is still incomplete

### SAFTE/circadian layer

- Canonical implementation: `app/fatigue_calculator/safte_model.py`
- Mirrored implementation for web delivery: `frontend/src/lib/safte-model.ts`
- Main manuscript framing: homeostatic reservoir + circadian harmonics + sleep inertia + optional re-entrainment
- Reviewer caveat: mirrored TypeScript logic supports frontend/backend consistency, not independent physiological validation

### Readiness fusion layer

- Canonical implementation: `app/scheduling_core.py`
- Main manuscript framing: deterministic fusion of HRV-derived features, SAFTE state, KSS/PVT pathways, mission modifiers, and bounded GO/NO-GO logic
- Reviewer caveat: strong operational logic evidence does not equal mission-outcome validation

### Environmental timing and alignment layer

- Canonical implementations: `app/space_weather_impact.py`, `app/space_weather_alignment.py`, `app/space_weather_influence.py`
- Main manuscript framing: NOAA ingestion, propagation timing, severity logic, and alignment to physiology windows
- Reviewer caveat: these are contextual timing models, not validated causal autonomic models

### Compact equation-style summary for reviewers

The biomathematical center of the manuscript can be summarized as:

- `HRV layer`: RR preprocessing -> mult-domain HRV features
- `Fatigue layer`: `E(t)` derived from homeostatic reservoir, circadian drive, and inertia
- `Readiness layer`: deterministic fusion of physiological and operational state variables
- `Environment layer`: timing, propagation, and alignment of space-weather context to physiology windows

## S3. Standards and operational-reference crosswalk

The platform draws on multiple operational and safety reference frameworks. The table below provides a conservative crosswalk for manuscript use.

| Framework or standard | Verified source | Where it informs the repository | Safe wording for manuscript use | Avoid saying |
| --- | --- | --- | --- | --- |
| NASA-STD-3001 Volume 1, Crew Health | NASA standards page, Rev. C, dated 2023-09-15 | Mission-health framing, crew health and human-systems reference context in operational modules and documentation | `designed with reference to NASA human-systems standards` | `NASA certified`, `NASA approved`, `compliant with NASA requirements` |
| ICAO Doc 9966 | ICAO publications page, 2nd ed., Version 2 (Revised), 2020 | FRMS-related operational framing, fatigue-management concepts, oversight logic | `informed by ICAO fatigue-management guidance` | `ICAO certified`, `ICAO compliant` |
| MIL-STD-882E-aligned risk framing | Repository code and docs language | Risk-matrix vocabulary and safety framing in operational logic | `aligned with established system-safety vocabulary` | `MIL-STD certified` |
| Crew-rest guidance / AFMAN-related operational constraints | FRMS-related code and changelog history | Crew-rest checks and operational scheduling logic | `implemented using rule-informed crew-rest constraints` | `validated military readiness standard` |

## S4. Reporting-guideline positioning

This manuscript should remain anchored to a software/systems/methods reporting posture unless stronger empirical evidence is added.

| Manuscript content area | Primary reporting backbone | Why it applies | Current status |
| --- | --- | --- | --- |
| Architecture, implementation, verification, and deployment surfaces | Journal-specific software/system or methods paper guidance | The main contribution is an integrated translational biomathematical software system. | Primary backbone for submission. |
| Any repository-backed observational analysis that might later be added | STROBE elements | Observational reporting becomes relevant only if empirical data are analyzed as study findings. | Secondary and conditional. |
| Predictive modeling or AI claims | TRIPOD+AI / CLAIM only where relevant | These frameworks apply only if the manuscript makes explicit predictive-model claims. | Currently not primary because the draft does not center validated predictive AI claims. |
| Reproducibility and transparency narrative | Versioned software reporting plus explicit availability statements | The paper reports code, artifacts, environment notes, and audit infrastructure. | Already reflected in the current draft. |

## S5. Non-claims and deployment prerequisites

### Non-claims

The current submission candidate does **not** establish:

- diagnostic accuracy,
- clinical effectiveness,
- mission outcome improvement,
- validated numerical equivalence of the integrated platform to all external reference software,
- fairness or subgroup robustness,
- regulatory clearance or certification.

### Deployment prerequisites before consequential use

Any real-world operational or clinical deployment would still require:

1. Local validation of workflow outputs against the intended use case.
2. Configuration control for thresholds, assumptions, and model settings.
3. Operator training and governance documentation.
4. Defined escalation pathways and human oversight for readiness or GO/NO-GO interpretations.
5. Release-specific archiving of the software version used operationally.

## S6. Reproducibility notes for reviewers

The documented primary execution path for the manuscript remains the conda `hrv-py312` environment with Python 3.12. The repository also contains container-related infrastructure, but the manuscript should not describe the execution environment as fully harmonized until any Python-version discrepancies between the conda path and container path are resolved. Reviewers should interpret the current paper as reporting a versioned open-source repository with engineering verification and reproducibility-oriented infrastructure, rather than as a frozen archival release unless a tagged release or DOI archive is added before submission.
