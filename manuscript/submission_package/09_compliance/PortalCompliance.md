# Applied Ergonomics — Final Submission Compliance

**Manuscript:** *Task-calibrated Operational Performance Indicators for aviation and unmanned aircraft system operators…*
**Compiled:** 2026-04-29
**Verdict:** **READY for portal upload** — all journal hard-fail rules satisfied (see § 1).

---

## 1. Pass / fail at submission gate

| # | Requirement | Limit | Measured | Status |
|---|---|---:|---:|:---:|
| 1 | Body word count (Introduction → Conclusions) | 3,000 – 5,000 | **4,919** | PASS |
| 2 | Abstract length | 100 – 150 | **142** | PASS |
| 3 | Keywords — number | ≤ 3 | 3 | PASS |
| 4 | Keywords — no title-word overlap | strict | none | PASS |
| 5 | Keywords — American spelling | strict | OK | PASS |
| 6 | Highlights — bullet count | 3 – 5 | 5 | PASS |
| 7 | Highlights — chars/bullet (incl. spaces) | ≤ 85 | max 85 | PASS |
| 8 | Highlights — separate file ("Highlights.docx") | strict | present | PASS |
| 9 | Section numbering depth | ≤ 3 levels | max 2 | PASS |
| 10 | Reference style — author-date alphabetical | strict | confirmed | PASS |
| 11 | Figure citations in body | every fig cited | Figs 1, 2, 3, 4 all cited | PASS |
| 12 | Figure resolution (raster halftone) | ≥ 300 dpi | 300 dpi | PASS |
| 13 | Figure formats | EPS / PDF / TIFF / JPG | PDF + PNG + SVG | PASS |
| 14 | American spelling in body | strict | clean | PASS |
| 15 | CRediT author contributions | required | §6.4 present | PASS |
| 16 | Declaration of competing interests — text | required | §6.5 present | PASS |
| 17 | Declaration of competing interests — `.docx` | required, do not convert | `04_declarations/DeclarationOfCompetingInterests.docx` | PASS |
| 18 | AI-use declaration | required if AI used | present + separate `.docx` | PASS |
| 19 | Funding statement | required | §6.5 boilerplate | PASS |
| 20 | Ethics statement (incl. SAGER positioning) | required | §6.3 | PASS |
| 21 | Title page (authors, ORCIDs, corresponding) | required | complete | PASS |
| 22 | Cover letter | required | `03_cover_letter/CoverLetter.docx` + `.pdf` | PASS |
| 23 | Suggested reviewers (3–5, names + emails + ORCIDs + diverse geography) | required | 5 verified candidates | PASS |
| 24 | Manuscript Word/PDF for portal | required | `Manuscript.docx` (1.27 MB) + `Manuscript.pdf` (1.40 MB) | PASS |
| 25 | Figures — separate files (revised submission) | required only at revision | PDF/PNG/SVG retained | OK for initial |

## 2. Outstanding (non-blocking) — to settle before clicking Submit

| # | Item | Why it's not a blocker |
|---|---|---|
| O-1 | **Postal-address street + postal code** on the title page | EM portal usually accepts city + country; add the full mailing line if the form rejects. |
| O-2 | **Tagged release / Zenodo DOI** for the reported version | §6.2 currently says "will be cited"; recommended to cut `v0.6.0-opi`, deposit to Zenodo, paste the Concept DOI before clicking Submit. Procedure: `manuscript/submission/publication_workflow.md` § 1. |
| O-3 | **Graphical abstract** (optional) | Not produced. Encouraged but not required. |

## 3. How the package was prepared

```
manuscript/submission_package/
├── 01_manuscript/
│   ├── manuscript.md      (working markdown source — edited from draft)
│   ├── Manuscript.docx    (1.27 MB; figures embedded)
│   └── Manuscript.pdf     (1.40 MB; xelatex render with embedded figures)
├── 02_highlights/
│   ├── Highlights.md
│   └── Highlights.docx    ← upload to "Highlights" slot
├── 03_cover_letter/
│   ├── CoverLetter.md
│   ├── CoverLetter.docx   ← upload to "Cover Letter" slot
│   └── CoverLetter.pdf
├── 04_declarations/
│   ├── DeclarationOfCompetingInterests.{md,docx}  ← upload .docx unchanged
│   └── AI_Use_Declaration.{md,docx}               ← also embedded in manuscript before References
├── 05_figures/
│   ├── figure1_opi_conceptual_schematic.{pdf,png,svg}
│   ├── figure2_task_taxonomy_hrv_signatures.{pdf,png,svg}
│   ├── figure3_opi_worked_example.{pdf,png,svg}
│   ├── figure4_reference_implementation_architecture.{pdf,png,svg}
│   └── AllFigures.pdf (combined — for supplement upload if separate figs preferred)
├── 06_tables/
│   ├── Table1_task_taxonomy.md
│   ├── Table2_weight_profiles.md
│   ├── Table3_vigilance_latency.md
│   ├── Table4_reproducibility.md
│   ├── Table5_verification_coverage.md
│   └── Tables_1-5.docx    ← already included in main manuscript; available as separate upload
├── 07_supplement/
│   ├── SupplementaryAppendix.md
│   └── SupplementaryAppendix.docx
├── 08_suggested_reviewers/
│   ├── SuggestedReviewers.md   ← reference for the portal fields (5 verified candidates)
│   └── SuggestedReviewers.docx
└── 09_compliance/
    └── PortalCompliance.md     (this file)
```

## 4. Editorial changes applied to the working manuscript

1. **Abstract trimmed** 156 → 142 words (within 150-word cap).
2. **Keywords replaced** to remove all title-word overlap and British spelling: was *Heart rate variability; Fatigue modelling; Aviation ergonomics* → now **Crew readiness; Vigilance decrement; Teleoperation**.
3. **Figure 1, 2, 4 inline citations and embedded captions added** — §1.4, §2.2, §2.5 respectively. Figure 3 already cited in §3.1.
4. **Body trimmed** 6,392 → 4,919 words. §4.3 (principled simplicity) compressed from 5 paragraphs to 3; §4.5 (limitations) compressed from 9 paragraphs to 2; §2.5 module descriptions consolidated from 3 paragraphs to 1.
5. **British → American spelling sweep:** 35+ replacements across body (modelling → modeling, behaviour → behavior, colour → color, normalisation → normalization, characterised → characterized, summarised → summarized, analysed → analyzed, emphasised → emphasized, optimised → optimized, calibrable → calibratable, formalised → formalized, specialised → specialized, operationalises → operationalizes, generalise → generalize). Reference list left untouched (cited paper titles must keep original spelling).
6. **Scaffolding line removed** ("*Tables 1–5.* Editable sources for compilation…").
