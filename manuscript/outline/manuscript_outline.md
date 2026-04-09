# Author: Dr Diego Malpica MD

## Manuscript Outline

## Working title candidates

1. **Mission Control - Flight Surgeon: a Next.js and Python biomathematical platform for HRV, fatigue-circadian modeling, and aerospace readiness support**
2. **A Node-first translational aerospace medicine system for HRV analytics, fatigue biomathematics, and mission-aware decision support**
3. **An API-backed biomathematical platform for autonomic monitoring, circadian-fatigue dynamics, and operational readiness**

## Candidate running titles

- **Aerospace Biomath Platform**
- **Mission Control Flight Surgeon**
- **Integrated Aerospace Readiness Platform**

## Central thesis

This manuscript should present **Mission Control - Flight Surgeon** as a Node-first translational biomathematical system that connects standards-informed HRV analytics with longitudinal user context, SAFTE/circadian dynamics, space-weather timing and alignment, and operational scheduling logic through a Next.js frontend, FastAPI orchestration, and a shared Python model stack.

The paper should argue that the key contribution is **layered biomathematical integration plus auditability**, not the invention of a single isolated algorithm.

## Section plan

| Section | Target content | Main evidence sources | Target length |
| --- | --- | --- | --- |
| Title and structured abstract | Problem, system, validation posture, bounded conclusions | `manuscript/evidence/evidence_matrix.md`, `manuscript/evidence/validation_story.md` | 250-350 words |
| Introduction | Fragmented tool landscape, translational gap, contribution statement | `manuscript/tables/literature_gap_comparison.md`, `README.md`, `docs/Manual.md` | 900-1,200 words |
| Methods | Requirements, architecture, computational modules, workflows, validation methodology | `manuscript/evidence/core_modules_scope.md`, `app/`, `api/main.py`, `README.md`, `WARP.md` | 1,500-2,000 words |
| Results | Implementation summary, engineering verification, reproducibility assets, optional curated analysis vignette | `manuscript/evidence/validation_story.md`, `tests/`, `analysis/` | 900-1,300 words |
| Discussion | Translational interpretation, limitations, maintainability, deployment pathway | `manuscript/evidence/evidence_matrix.md`, `manuscript/evidence/compliance_and_transparency_map.md` | 900-1,200 words |
| Compliance and transparency | Data/code availability, ethics, standards alignment, CRediT, funding, COI | `manuscript/evidence/compliance_and_transparency_map.md` | 400-700 words |

## Planned tables

1. **Table 1. Platform architecture and module families** — `manuscript/tables/platform_architecture_and_module_families.md`
2. **Table 2. Narrative comparison with external systems** — `manuscript/tables/literature_gap_comparison.md`
3. **Table 3. Engineering verification coverage by module family** — `manuscript/tables/engineering_verification_coverage.md`
4. **Table 4. Reproducibility and deployment metadata** — `manuscript/tables/reproducibility_and_deployment_metadata.md`
5. **Table 5. Compliance and transparency declarations** — `manuscript/tables/compliance_and_transparency_declarations.md`
6. **Table 6. Model layers, inputs, outputs, and evidence tiers** — `manuscript/tables/model_layers_and_evidence_tiers.md`

## Planned figures

1. **Figure 1. System architecture across inputs, analytic core, decision layers, and delivery surfaces** — rendered as `manuscript/figures/figure1_platform_architecture.svg`
2. **Figure 2. End-to-end operational workflow from RR ingestion to readiness and scheduling outputs** — rendered as `manuscript/figures/figure2_end_to_end_workflow.svg`
3. **Figure 3. Example research-to-operations data flow linking HRV, fatigue, and space-weather context** — rendered as `manuscript/figures/figure3_research_to_operations_coupling.svg`
4. **Figure 4. Verification map or result summary for tested module families** — rendered as `manuscript/figures/figure4_verification_coverage_map.svg`

See `manuscript/figures/figure_plan.md` for details.

## Writing order

1. Write Methods first from the code and architecture files.
2. Draft Results only from supported evidence classes.
3. Build the Introduction around the literature comparison table after Methods is stable.
4. Write the Discussion last so it reflects the final bounded evidence posture.
5. Finish the compliance sections only after the exact code version, data statement, and authorship list are confirmed.

## Current submission-candidate status

1. The main manuscript draft now contains a structured abstract, Introduction, Methods, Results, Discussion, Conclusion, and Compliance/Transparency sections.
2. The planned table package now includes six manuscript markdown assets, including a dedicated biomathematical layer summary.
3. Figure specifications and rendered SVG assets now exist for Figure 1 through Figure 4.
4. Reference expansion and bibliography verification passes have been completed; remaining blockers are author-level metadata confirmation, venue-specific templating, and release/archive packaging for the cited software version.
5. **Agent orientation:** pipeline position, Q1 publication checklist, and guardrails are maintained in `manuscript/README.md` (read this when onboarding to the paper effort).

## Q1 journal targeting shortlist

Checked against live journal pages and ranking sources on 2026-04-09. The shortlist below is meant to guide packaging, not to claim template compliance before export into the chosen journal format.

| Journal | Current fit | Main upside | Main risk for this manuscript | Immediate packaging implication |
| --- | --- | --- | --- | --- |
| **Computer Methods and Programs in Biomedicine (CMPB)** | **Best current fit** | Q1 venue with explicit scope for biomedical computing methods, software systems, and implementation papers. The current manuscript already reads like a systems-and-methods paper. | Reviewers will still expect a cleaner computational evaluation package than a software-verification-only story. | Keep the Node-first architecture and biomathematical layer narrative central; strengthen reproducibility packaging and keep claims tightly bounded to implementation plus engineering verification. |
| **Journal of Biomedical Informatics (JBI)** | **Strong alternative** | Q1 biomedical informatics journal with a clear methodological focus and good alignment for an API-backed translational decision-support platform. | JBI is more selective about conceptual informatics contribution than about feature breadth alone; the paper must read as a methodology contribution, not a product description. | Restructure the final export toward JBI's preferred shape: structured abstract, explicit Related Work framing, clear Conclusion, and a graphical abstract. |
| **npj Digital Medicine** | **Ambitious stretch target** | High-visibility Q1 journal with strong interest in digital medicine platforms and translational deployment. | The current repository-backed evidence base is probably too engineering-heavy unless paired with a stronger external validation, human-use study, or benchmark package. | If this venue is chosen, compress the title and abstract aggressively, add a statistics/reproducibility subsection, and plan for a more demanding validation story than the current draft supports. |
| **Military Medical Research** | **Domain-forward option** | Q1 operational-medicine venue with stronger mission-readiness and aerospace-adjacent framing than the informatics journals. | The manuscript would need to foreground operational relevance and deployment governance more than software architecture. | Keep the translational discussion, declarations, and operational-readiness framing prominent; expect stricter expectations around practical significance and military/mission context. |

### Recommended submission order

1. **Primary target:** `Computer Methods and Programs in Biomedicine`
2. **Secondary target:** `Journal of Biomedical Informatics`
3. **Stretch target if validation is upgraded:** `npj Digital Medicine`
4. **Domain-specific fallback while staying Q1:** `Military Medical Research`

### Explicit non-priority venue

- **Aerospace Medicine and Human Performance** remains topically relevant, but it is not a Q1 journal in the current ranking sources, so it should not be the lead target if the Q1 requirement is strict.

### Packaging decisions implied by the shortlist

1. Keep the paper framed as a **software / systems / methods manuscript** rather than as a clinical validation paper.
2. Preserve the **Node-first + shared Python biomathematical stack** as the organizing contribution, because that is the angle with the best cross-journal fit.
3. Add a **clear Conclusion section** in the main draft and keep the abstract within the usual 150-300 word range expected by the shortlisted journals.
4. Replace moving-branch metadata with a **tagged release or archived DOI** before submission.
5. Treat any future empirical vignette as optional unless its provenance is curated strongly enough to survive higher-tier review.

## Scope guardrails

1. Keep the main paper centered on the seven core workflows defined in `manuscript/evidence/core_modules_scope.md`.
2. Move device-specific ingestion details, GPU optimizations, real-time pathways, and advanced AI modules to supplementary materials unless they become central claims.
3. Treat exploratory CSV artifacts as optional examples, not mandatory headline results.
4. Use regulatory language conservatively: the platform is informed by operational standards, not certified by them.
