# Applied Ergonomics — Submission Compliance Report

**Date generated:** 2026-04-29
**Manuscript:** *Task-calibrated Operational Performance Indicators for aviation and unmanned aircraft system operators…*
**Source draft:** `manuscript/draft/opi_main_manuscript.md`
**Target journal:** *Applied Ergonomics* (Elsevier) — Editorial Manager portal `https://www.editorialmanager.com/JERG`
**Verdict:** **NOT READY TO SUBMIT.** Several hard-fail items must be resolved first — see § Action plan.

---

## 1. Pass / Fail summary

| # | Requirement | Limit | Measured | Status |
|---|---|---|---|---|
| 1 | Body word count (Introduction → Conclusions) | 3,000 – 5,000 | **6,392** | **FAIL** (~28 % over) |
| 2 | Abstract length | 100 – 150 words | **156** | **FAIL** (6 over) |
| 3 | Keywords — number | ≤ 3 | 3 | PASS |
| 4 | Keywords — none appearing in title | strict | All 3 contain title words | **FAIL** |
| 5 | Keywords — American spelling | strict | "Fatigue modelling" (British) | **FAIL** |
| 6 | Highlights — bullet count | 3 – 5 | 5 | PASS |
| 7 | Highlights — characters per bullet (incl. spaces) | ≤ 85 | max 85 (#1) | PASS |
| 8 | Highlights — separate file named "Highlights" | strict | `highlights.md` (not the required filename, only Markdown) | **FAIL — artefact gap** |
| 9 | Section numbering depth | ≤ 3 levels (1, 1.1, 1.1.1) | max 2 levels | PASS |
| 10 | Reference style — author-date alphabetical | strict | confirmed; no numeric `[1]` style anywhere | PASS |
| 11 | References list — author count | n/a | 34 entries | PASS |
| 12 | Figure citations in body | every figure cited | only Figure 3 cited; **Figures 1, 2, 4 NOT cited** | **FAIL** |
| 13 | Table citations in body | every table cited | Tables 1–5 cited; folder also contains 4 unreferenced supplementary tables (compliance, gap, model layers, platform architecture) — these can stay as supplement | PASS for body |
| 14 | Figure resolution (raster halftone) | ≥ 300 dpi | all four PNGs at 300 dpi | PASS |
| 15 | Figure formats | EPS / PDF / TIFF / JPG | PDF + SVG + PNG provided | PASS (PDF preferred for vector; SVG is acceptable but EPS/PDF is the journal preference) |
| 16 | American spelling in body | strict | 25+ British spellings flagged (see § 4) | **FAIL** |
| 17 | CRediT author contributions | required | §6.4 present | PASS |
| 18 | Declaration of competing interests — text | required | §6.5 present | PASS |
| 19 | Declaration of competing interests — Elsevier .docx template | strict, do not convert | **No .docx file in `submission/`** | **FAIL — artefact gap** |
| 20 | AI use declaration | required if AI used in preparation | full statement before References ✓ | PASS |
| 21 | Funding statement | required | §6.5 includes Elsevier boilerplate | PASS |
| 22 | Ethics statement | required (incl. SAGER positioning) | §6.3 covers methodology paper posture | PASS |
| 23 | Title page — author block, ORCID, corresponding author | required | complete except postal street/code placeholder | PASS (placeholder OK pre-portal) |
| 24 | Cover letter | required | `cover_letter_applied_ergonomics.md` drafted | PASS (Markdown — needs Word/PDF export) |
| 25 | Suggested reviewers (3–5, names + institutional emails + ORCIDs + diverse geography) | required at submission | cover letter punts to portal; **no list assembled** | **FAIL — artefact gap** |
| 26 | Tagged release / archived DOI for reported version | required for reproducibility statement | repository has not been tagged; §6.2 promises "will be cited" | **FAIL — blocker self-flagged** |
| 27 | Single Word/PDF manuscript for Editorial Manager | required (initial submission "Your Paper Your Way") | only Markdown available | **FAIL — artefact gap** |
| 28 | Graphical abstract (optional but encouraged) | ≥ 531 × 1328 px | not produced | optional (no fail) |

---

## 2. Hard-fail items grouped by what they block

### A. Items that block **portal acceptance** (Editorial Manager will not accept the package as-is)

1. **No Word/PDF of the manuscript.** Only Markdown exists. Editorial Manager requires `.docx` or `.pdf` for the Manuscript slot.
2. **No file named "Highlights".** Journal requires a separate uploadable file (Highlights.docx or .txt) — `highlights.md` does not satisfy this.
3. **No Elsevier Declaration of Competing Interests `.docx`.** Journal requires the **official Elsevier template**; the rule explicitly says **do not convert** to other formats. Source the template from the *Guide for Authors* page.
4. **No Suggested Reviewers list at submission.** Cover letter § "Suggested reviewers" defers to the portal but Applied Ergonomics expects 3–5 candidates with full names, institutional emails, ORCIDs, and geographic diversity at submission.
5. **Figures 1, 2, and 4 not cited in body text.** Only Figure 3 is referenced. Editorial Manager / peer review will reject orphan figures.
6. **No tagged release / Zenodo DOI.** §6.2 says one "will be cited"; status is "Not started" per `README.md`. Cut a release before submission.

### B. Items that block **editor acceptance** (editor will return for revision before peer review)

1. **Body word count 6,392 vs. cap 5,000** — ~28 % over. README and `highlights.md` already note this and suggest "contact the Editor" — that is a flag the team has been waving past. The overage is large enough that the editor is more likely to desk-return than to grant a waiver. **Recommend: trim to ≤ 5,000 words rather than negotiate the exception.**
2. **Abstract 156 vs. cap 150 words** — must be trimmed by 6+ words.
3. **All three keywords contain title words** ("heart rate variability", "fatigue", "aviation"). Replace with non-overlapping terms.
4. **"Fatigue modelling" uses British spelling** in the keywords field. Use "fatigue modeling" (American).
5. **British spellings in body** — 25+ instances spread across `modelling` (×6), `behaviour/behavioural` (×6), `colour` (×3), `normalisation` (×3), `characterised` (×4), `summarised` (×1), `analysed` (×2), `emphasised` (×1). Convert to American spelling globally.

---

## 3. Detailed findings

### 3.1 Word count

```
Body (Introduction §1 → Conclusions §5, code fences stripped): 6,392 words
Journal cap: 5,000
Overage: +1,392 words (~28 %)
```

Method: `re.findall(r"[A-Za-z][A-Za-z'\-]*", body)` after stripping fenced code blocks. Title page, abstract, keywords, acknowledgements, AI declaration, references, and §6 *Compliance and Transparency* are excluded from the count per Elsevier's "Introduction through Conclusions" rule.

### 3.2 Abstract

```
Word count: 156
Journal limit: 100 – 150
```

Abstract is otherwise compliant: standalone, no abbreviations introduced without expansion, not numbered as a section. Trim 6+ words.

### 3.3 Keywords

```
Current: "Heart rate variability"; "Fatigue modelling"; "Aviation ergonomics"
```

Title overlap audit (American case-insensitive token match against title words):
- `Heart rate variability` → contains *heart, rate, variability* — all in title.
- `Fatigue modelling` → contains *fatigue* — in title; also "modelling" is British.
- `Aviation ergonomics` → contains *aviation* — in title.

**All three keywords fail the "no title word" rule.** Suggested alternatives (non-title, indexed terms, American spelling):
- *Operator readiness*
- *Cognitive load*
- *Teleoperation*
- *Vigilance decrement*
- *Multiple resource theory*
- *Composite index*
- *Biomathematical model*

Choose 3 that are not already in the title and do not overlap with each other.

### 3.4 Highlights — character counts (re-verified)

| # | Length | Bullet |
|---|---:|---|
| 1 | 85 | We introduce Operational Performance Indicators (OPI) for aviation and UAS operators. |
| 2 | 83 | OPI fuses SAFTE, HRV, and Multiple Resource Theory-derived task-calibrated weights. |
| 3 | 80 | Per-task weights are specified for 10 manned-aviation and 7 UAS task categories. |
| 4 | 82 | A Warm-type vigilance model and Chen-type latency penalty cover UAS teleoperation. |
| 5 | 74 | Open-source reference implementation is distributed under the MIT license. |

Bullet 1 is at the limit; consider trimming to leave a safety margin (e.g., drop "Operational" or replace with the abbreviation).

The content passes; the **filename does not** — Elsevier requires a separately uploaded "Highlights" file (Word `.docx` strongly preferred, `.txt` acceptable). See § 5.

### 3.5 Reference style

- Author-date alphabetical (Harvard / APA hybrid). Confirmed by spot-check of inline citations: `(Shaffer & Ginsberg, 2017)`, `(Forger, Jewett, & Kronauer, 1999; Hursh, Balkin, Miller, & Eddy, 2004)`, `(Hamann et al., 2026)`, etc.
- No `[1]` / `[2]` numeric callouts found in the manuscript body.
- Reference list contains 34 entries, alphabetical by first-author surname.

### 3.6 Figures

- Files in `figures/` (publication-quality):
  - `figure1_opi_conceptual_schematic.{pdf,png,svg}` — 3870 × 1511 @ 300 dpi
  - `figure2_task_taxonomy_hrv_signatures.{pdf,png,svg}` — 3713 × 2101 @ 300 dpi
  - `figure3_opi_worked_example.{pdf,png,svg}` — 3930 × 1351 @ 300 dpi
  - `figure4_reference_implementation_architecture.{pdf,png,svg}` — 3708 × 1983 @ 300 dpi
- Body cites only **Figure 3** (line 166 and figure caption at line 178). Figures 1, 2, and 4 are not introduced anywhere in the prose. **Add introductory citations** in §§ 1.4 (Figure 1 — conceptual schematic), 2.2 (Figure 2 — task taxonomy / HRV signatures), and 2.5 or 3.2 (Figure 4 — reference implementation architecture).

### 3.7 Tables

- Body cites Tables 1–5. The `tables/` folder contains 9 markdown sources; the four extras (`compliance_and_transparency_declarations.md`, `literature_gap_comparison.md`, `model_layers_and_evidence_tiers.md`, `platform_architecture_and_module_families.md`) are appropriate for the **supplement**. Confirm or move them out of the main-submission table block.
- Body sentence at line 180 — `*Tables 1–5.* Editable sources for compilation into the submission file are in 'manuscript/tables/'…` — is **scaffolding text** that should not appear in the final submission file. Remove before exporting.

### 3.8 British spelling sweep (American required)

```
modelling          ×6
behaviour          ×5
behavioural        ×1
colour             ×3
normalisation      ×3
characterised      ×4
summarised         ×1
analysed           ×2
emphasised         ×1
calibrable         ×2   (rare-but-valid; not a UK/US issue — consider 'calibratable')
```

Do a global, careful pass. Be cautious about cited paper titles (do **not** alter quoted titles in the reference list — only body prose).

### 3.9 Declarations / metadata

- §6.4 CRediT — present, two-author distribution.
- §6.5 Funding — Elsevier boilerplate present.
- §6.5 Competing interests — wording present; **upload the Elsevier `.docx` template separately** (do not convert). Source: *Applied Ergonomics* Guide for Authors → Declaration of competing interests.
- AI declaration — present immediately before References. Wording is conservative and aligned with Elsevier policy; verify the section heading exactly matches Elsevier's required title `Declaration of generative AI and AI-assisted technologies in the manuscript preparation process` (it does).
- Ethics §6.3 — methodology-paper posture, with SAGER mention conditional on future empirical extension. PASS.

### 3.10 Reproducibility / DOI

- §6.2 still says "A tagged release or archived DOI corresponding to the exact reported version will be issued and cited in the final manuscript."
- Cover letter § "Data and code availability" makes the same promise.
- Per `README.md` pipeline table: tagged release / archive DOI = "Not started".
- **Action:** cut `v0.6.0-opi` (or equivalent) on `strikerdlm/HRV`, deposit to Zenodo, paste the Concept DOI into §6.2 and the cover letter before submission. Procedure already documented in `submission/publication_workflow.md` § 1.

---

## 4. Action plan — what to do, in priority order

### Phase 1 — Editorial pass on the manuscript (1–3 days)
1. **Cut body to ≤ 5,000 words.** Highest-yield candidates: §4.3 (currently 5 paragraphs on principled simplicity — collapse to 3); §2.5 reference-implementation paragraph blocks (move detailed module descriptions to Supplement); §4.5 limitations (some can be folded into §4.6 validation roadmap).
2. **Trim abstract to ≤ 150 words.**
3. **Replace keywords** with three terms that do not appear in the title and use American spelling (suggested above).
4. **Add inline citations for Figures 1, 2, and 4.**
5. **Global British → American spelling pass** (terms in § 3.8). Skip cited paper titles in the reference list.
6. **Remove the "Tables 1–5" scaffolding sentence** at line 180.

### Phase 2 — Build the artefact bundle (½ day)
7. **Cut a tagged release** of `strikerdlm/HRV`, deposit to Zenodo, paste the Concept DOI into §6.2 and the cover letter.
8. **Render the manuscript to `.docx` (or `.pdf`).** Pandoc + reference template, or paste into a Word file.
9. **Create `Highlights.docx`** (not `highlights.md`) — exactly the 5 bullets, no commentary, file named "Highlights".
10. **Download the Elsevier Declaration of Competing Interests `.docx` template**, fill it, upload as-is — **do not convert**.
11. **Assemble the Suggested Reviewers list** — 3–5 entries with name + institution + country + institutional email + ORCID + 1-line rationale. See `SuggestedReviewers.md` (template stub created alongside this report).

### Phase 3 — Portal submission (1 hour, after Phases 1–2 are clean)
12. Editorial Manager → "Submit New Manuscript" → Article type **Research Article**.
13. Paste Title, Abstract (≤150 words), and the 3 fixed Keywords.
14. Add both authors with ORCIDs; mark Diego L. Malpica as corresponding.
15. Upload: Manuscript (.docx/.pdf), Highlights, Cover Letter, COI .docx, Suggested Reviewers (entered in portal fields), optional supplement.
16. Confirm AI-use declaration in the portal field (matches the manuscript section).
17. Approve the system-generated PDF proof — verify all figures cited and present, references in author-date format, abstract within limit.

---

## 5. What is already good

- Theoretical positioning, contribution claims, and limitations are well-articulated and traceable to cited literature.
- Figure assets are publication-grade (300 dpi, vector + raster + SVG sources).
- DOI-verified seed bibliography (34 entries, all with DOIs).
- Author block, CRediT, AI declaration, ethics, funding all present and conformant in content.
- Cover letter is venue-fit, contribution-clear, and honest about scope.
- Highlights content is within character limits.
- Reference style is correct.
- Repository has a documented reproducibility posture in §6.2 and `submission/publication_workflow.md`.

---

## 6. Re-run this check

```bash
cd /root/.openclaw/workspace/hrv/HRV/manuscript
python3 - <<'PY'
import re
text = open('draft/opi_main_manuscript.md').read()
body = text.split('## 1. Introduction',1)[1].split('## 6. Compliance and Transparency',1)[0]
body = re.sub(r'```.*?```','',body,flags=re.S)
print('body words:', len(re.findall(r"[A-Za-z][A-Za-z'\-]*", body)))
abs_block = text.split('## Abstract',1)[1].split('### Keywords',1)[0]
print('abstract words:', len(re.findall(r"[A-Za-z][A-Za-z'\-]*", abs_block)))
PY
```

---

*Report produced by `/applied-ergonomics-submit` on 2026-04-29.*
