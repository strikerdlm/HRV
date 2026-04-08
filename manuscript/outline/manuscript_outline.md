# Author: Dr Diego Malpica MD

## Manuscript Outline

## Working title candidates

1. **Mission Control - Flight Surgeon: an open-source aerospace medicine platform for HRV analytics, fatigue modeling, space-weather context, and operational decision support**
2. **An integrated translational aerospace medicine software platform for autonomic monitoring, fatigue forecasting, and mission-aware decision support**
3. **A dual-interface physiological operations platform for aerospace medicine research and operational readiness**

## Candidate running titles

- **Aerospace Physiology Ops Platform**
- **Mission Control Flight Surgeon**
- **Integrated Aerospace HRV Platform**

## Central thesis

This manuscript should present **Mission Control - Flight Surgeon** as a translational software platform that connects standards-informed HRV analytics with longitudinal user context, circadian and fatigue modeling, space-weather context, and operational scheduling logic across research and operational interfaces.

The paper should argue that the key contribution is **integration plus auditability**, not the invention of a single isolated algorithm.

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

## Planned figures

1. **Figure 1. System architecture across inputs, analytic core, decision layers, and delivery surfaces** — spec and draft caption in `manuscript/figures/figure_plan.md`
2. **Figure 2. End-to-end operational workflow from RR ingestion to readiness and scheduling outputs** — spec and draft caption in `manuscript/figures/figure_plan.md`
3. **Figure 3. Example research-to-operations data flow linking HRV, fatigue, and space-weather context** — spec and draft caption in `manuscript/figures/figure_plan.md`
4. **Figure 4. Verification map or result summary for tested module families** — spec and draft caption in `manuscript/figures/figure_plan.md`

See `manuscript/figures/figure_plan.md` for details.

## Writing order

1. Write Methods first from the code and architecture files.
2. Draft Results only from supported evidence classes.
3. Build the Introduction around the literature comparison table after Methods is stable.
4. Write the Discussion last so it reflects the final bounded evidence posture.
5. Finish the compliance sections only after the exact code version, data statement, and authorship list are confirmed.

## Current submission-candidate status

1. The main manuscript draft now contains a structured abstract, Introduction, Methods, Results, Discussion, and Compliance/Transparency sections.
2. The planned five-table package now exists as manuscript markdown assets.
3. Figure specifications and draft captions exist, but rendered figure assets are still pending.
4. The remaining blockers to a cleaner submission candidate are final reference expansion, rendered figures, and author-level metadata confirmation.

## Scope guardrails

1. Keep the main paper centered on the seven core workflows defined in `manuscript/evidence/core_modules_scope.md`.
2. Move device-specific ingestion details, GPU optimizations, real-time pathways, and advanced AI modules to supplementary materials unless they become central claims.
3. Treat exploratory CSV artifacts as optional examples, not mandatory headline results.
4. Use regulatory language conservatively: the platform is informed by operational standards, not certified by them.
