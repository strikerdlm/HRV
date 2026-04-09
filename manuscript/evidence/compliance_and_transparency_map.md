# Author: Dr Diego Malpica MD

## Compliance and Transparency Map

This document converts repository evidence into manuscript-ready transparency inputs and identifies what is still missing.

## Repository metadata for manuscript reporting

| Item | Value | Source |
| --- | --- | --- |
| Repository name | `HRV` / Mission Control - Flight Surgeon | `README.md` |
| Public repository URL | `https://github.com/strikerdlm/HRV.git` | git remote + `README.md` |
| License | MIT | `LICENSE` |
| Draft repository state | Active public git repository under version control | git metadata |
| Frozen submission identifier | Not yet assigned | git metadata |
| Primary documented Python environment | conda `hrv-py312`, Python 3.12 | `WARP.md`, `README.md`, `AGENTS.md` |
| Primary dependency file | `requirements.txt` | repository root |
| Main operational surfaces | Next.js frontend, FastAPI backend, secondary Streamlit research and operational interfaces | `README.md`, `api/main.py`, `frontend/` |

## Section-by-section map

| Manuscript subsection | Current repository evidence | Manuscript-safe wording today | Missing inputs or cautions |
| --- | --- | --- | --- |
| Data availability statement | `analysis/` exports exist; `docs/lit_review.md` includes review-style availability wording | State availability only for code and repository artifacts unless a curated dataset package is assembled. | Need dataset manifest, sharing conditions, and study linkage for any empirical tables or figures. |
| Code and artifact availability | Public GitHub URL, MIT license, Python and Next.js dependency docs, plus a future release identifier | Safe to report the repository URL, license, environment notes, and the presence of a Node.js/Next.js frontend over a Python backend. | Prefer a tagged release or archived DOI before final submission. |
| Ethics and consent | `docs/lit_review.md` contains a review-only `Not applicable` declaration | Use a software-only statement only if the manuscript reports no new or previously collected human-subject data. | If any human data are reported, insert protocol number, institution, and consent language. |
| Standards and regulatory alignment | NASA, ICAO, MIL-STD, and related standards are cited in code and docs | Safe to say the platform is informed by or aligned with these reference frameworks. | Do not claim certification, legal compliance, or clearance without formal documentation. |
| Reporting guideline alignment | Verified references available for STROBE, TRIPOD+AI, and CLAIM | Safe to describe a hybrid reporting strategy driven by manuscript content. | Only invoke TRIPOD+AI or CLAIM if predictive AI claims are actually reported. |
| Author contributions | Primary authorship consistently attributed to Dr Diego Malpica MD in repo files | Safe to prefill a provisional CRediT entry for Dr Diego. | Final author list and role distribution still require confirmation. |
| Funding | No project-level funding statement identified in the repository | Use `No external funding was reported` only if true. | Grant numbers or institutional support must be added if applicable. |
| Conflict of interest | No project-level COI statement identified in the repository | Use a neutral placeholder until confirmed. | Need explicit author declarations before submission. |
| Acknowledgments | Institutional and initiative context appears in `README.md` | Safe to acknowledge infrastructure or non-author contributors once confirmed. | Final names and affiliations still needed. |

## Standards and regulatory references present in the repository

| Reference framework | Where it appears | Safe manuscript interpretation |
| --- | --- | --- |
| NASA-STD-3001 | `app/scheduling_core.py`, `README.md`, `CHANGELOG.md`, other mission-health modules | The platform uses NASA-referenced thresholds and mission-health framing in several modules. |
| ICAO fatigue and safety references | `app/physiological_sms.py`, `README.md`, FRMS-related modules | The operational risk framing is informed by aviation fatigue-management concepts. |
| MIL-STD-882E | `app/physiological_sms.py`, `README.md`, frontend risk labels | Safety-matrix logic is aligned with an established system-safety vocabulary. |
| AFMAN and crew-rest references | FRMS-related code and changelog notes | Crew-rest checks can be described as rule-informed operational constraints. |

## Conservative language rules

Use these phrases:

- `informed by`
- `aligned with`
- `implemented using thresholds drawn from`
- `designed with reference to`
- `supports a deployment pathway toward`

Avoid these phrases unless new documentation is provided:

- `certified`
- `regulatory compliant`
- `HIPAA compliant`
- `GDPR compliant`
- `FDA cleared`
- `validated for clinical deployment`

## Draft statement templates

### Code and artifact availability

> Mission Control - Flight Surgeon is available as open-source software at `https://github.com/strikerdlm/HRV.git` under the MIT license. The repository includes a Next.js/TypeScript frontend over a Python backend and shared modeling core. Before submission, the manuscript should cite a tagged release or archived DOI corresponding to the frozen software version.

### Data availability

**If the paper remains software-only:**

> No new human-subject dataset was generated for the software-verification components reported here. Repository artifacts, code, and manuscript support files are available through the public source repository. Additional derived analysis artifacts are available from the authors on reasonable request.

**If retrospective or prospective data are added:**

> De-identified data supporting the findings of this study are available [insert repository or access procedure here], subject to institutional and ethical restrictions.

### Ethics approval

**If the paper remains software-only:**

> Ethics approval and informed consent were not required for the software-development and repository-verification components reported in this manuscript.

**If human data are added:**

> This study was approved by [institution and ethics board], protocol [number]. Participants provided [written informed consent / waiver rationale].

### Regulatory and standards alignment

> The platform is not presented as a certified medical device. Several operational modules were designed with reference to published aerospace, fatigue-management, and safety frameworks, including NASA-STD-3001, ICAO fatigue-management guidance, and MIL-STD-882E-aligned risk framing.

## Reproducibility caution

The repository documents a Python 3.12 conda environment as the primary development path, but the current `Dockerfile` uses Python 3.11. The manuscript should either:

1. report the conda environment as the authoritative execution path, or
2. reconcile the container environment before submission.

Do not describe the execution environment as fully harmonized until that inconsistency is resolved.

## Provisional CRediT template

- **Dr Diego Malpica MD:** Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Writing - original draft, Writing - review and editing, Visualization, Supervision, Project administration.

## Final inputs still required from the authors

1. Final author list and affiliations.
2. Funding statement and grant numbers, if any.
3. Conflict-of-interest declarations for all authors.
4. Study-specific ethics approval details, if any human data will be reported.
5. Preferred data-sharing pathway for any empirical results included in the final paper.
