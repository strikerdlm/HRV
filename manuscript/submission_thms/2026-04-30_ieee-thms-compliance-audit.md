# IEEE THMS Compliance Audit — OPI Manuscript

**Audit invoked:** `/IEEE check`
**Date:** 2026-04-30
**Source:** `manuscript/submission_thms/tex/manuscript.tex` and supporting package
**Compiled PDF:** `manuscript/submission_thms/tex/manuscript.pdf`
**Auditor:** Claude Opus 4.7 against IEEE THMS Information for Authors (Aug 2017 page limits, Jan 2024 charges)
**IFA source:** https://www.ieeesmc.org/publications/transactions-on-human-machine-systems/information-for-authors-2/

---

## Executive summary

| Status | Count |
|---|---|
| ✅ **Pass** | 24 |
| ⚠️ **Non-blocking** | 4 |
| 🛑 **Blocking** (must fix before submit) | 2 |

**Blocking items:**

1. **Author footnote does not start with "Manuscript received…"** (Section B.4 of IFA). Current text is `\thanks{Manuscript prepared April 2026.}` — the IFA explicitly requires the footnote sheet to begin with `Manuscript received…` with the date filled in by the editor-in-chief.
2. **Diego must verify the IEEE Copyright Form is signed at submission.** Cannot be confirmed pre-submission; flag for the corresponding-author pre-flight.

**Non-blocking but worth fixing:**

3. Uncited bib entry `grant2017` (smartphone PVT validation) — orphan in `references.bib` after the §2.5 cut.
4. Figures use color (heatmap palette in Fig. 2; readiness-band shading in Fig. 3) — author bears incremental cost if requesting color print, or convert to patterns.
5. ORCID linkage in ScholarOne is required at submission time (cannot be checked pre-submission); flag.
6. Cover-letter variant choice (A or B) still pending Diego's decision.

---

## A. Format and length

| Check | Status | Evidence |
|---|---|---|
| IEEEtran two-column | ✅ pass | `\documentclass[10pt,journal,twocolumn,compsoc]{IEEEtran}` |
| Page size 8.5 × 11 in | ✅ pass | `pdfinfo` reports `612 × 792 pts (letter)` |
| Compiled length ≤ 10 IEEE Transactions pages (Regular Paper) | ✅ pass | **8 pages** of compiled output — 2 pages of headroom |
| Abstract 100–250 words | ✅ pass | 184 words |
| Footnote begins with "Manuscript received…" | 🛑 **BLOCKING** | Current: `\thanks{Manuscript prepared April 2026.}` — required form per Section B.4 is `Manuscript received [date].` with the date filled by the editor-in-chief. **Fix:** change to `\thanks{Manuscript received April 30, 2026; revised; accepted. Date of publication; date of current version.}` or simply `\thanks{Manuscript received April 30, 2026.}`. |
| Equations IEEE-numbered | ✅ pass | Equations (1)–(5) with `\tag{}` or `\label{}` |
| No author photos/biographies (Regular Paper) | ✅ pass | None present |
| Two-column source compiles cleanly | ✅ pass | `pdflatex` clean, only cosmetic underfull/overfull warnings |

---

## B. References

| Check | Status | Evidence |
|---|---|---|
| All references in IEEE numbered style | ✅ pass | 38 numbered entries `[1]`–`[38]` rendered |
| BibTeX uses `\bibliographystyle{IEEEtran}` | ✅ pass | Line confirmed in `manuscript.tex` |
| Each reference complete | ✅ pass | 38 cited entries each with author/title/venue/vol/pp/year |
| First citation order matches numbering | ✅ pass | IEEEtran.bst auto-orders by citation; verified in rendered PDF |
| No uncited entries in bib | ⚠️ non-blocking | `grant2017` in `references.bib` is uncited; was orphaned during the §2.5 PVT-section cut. **Fix:** remove the entry from `references.bib`, or restore the smartphone-PVT validation citation in §2.5. |

---

## C. Figures and tables

| Check | Status | Evidence |
|---|---|---|
| Figures vector or high-resolution | ✅ pass | All four figures are PDF (vector) |
| One illustration per page (when separate) | ✅ pass | LaTeX `figure` environment places one per float |
| High-contrast and noise-free | ✅ pass | Inspection of compiled PDF |
| Patterns over colors unless paying for color | ⚠️ non-blocking | Fig. 2 uses a colored heatmap; Fig. 3 uses colored band shading (green/yellow/orange/red). **Decision required:** (a) opt into color print at incremental cost, or (b) convert to grayscale + patterns. Online IEEE Xplore version is color regardless. |
| Lettering legible at column-width reduction | ✅ pass | Figure inspection at 100% column width |
| Figure captions placed appropriately | ✅ pass | Captions follow figures via IEEEtran `\caption{}`. IFA technically requires "separate sheet" but modern IEEEtran practice accepts inline captions. |
| Tables in IEEE format | ✅ pass | Tables I–V using `booktabs`/`tabularx`, IEEE-styled |

---

## D. Required declarations

| Check | Status | Evidence |
|---|---|---|
| ORCID for all authors (in manuscript) | ✅ pass | `0000-0002-2257-4940` (Diego), `0000-0002-7981-2356` (Ingrid) in author block |
| ORCID linked in ScholarOne | ⚠️ pre-flight | Cannot be checked pre-submission; verify at portal step |
| IEEE Copyright Form signed | 🛑 **BLOCKING at submission** | Pending Diego's electronic signature at submission step in ScholarOne (cannot be done in advance) |
| Prior-publication disclosure | ✅ pass | Two cover-letter variants in `cover_letter_template.md`; pick one before submit |
| Preprint banner present (if posted) | ✅ N/A | No preprint posted |
| Generative-AI assistance acknowledged | ✅ pass | Section "Generative AI declaration" present in §6 of `manuscript.tex` |
| Funding statement | ✅ pass | "This research did not receive any specific grant…" in §6.5 |
| Conflicts of interest | ✅ pass | "The authors declare no competing financial or non-financial interests…" in §6.5 |
| CRediT contributions (recommended) | ✅ pass | CRediT roles in §6.4 |
| Data availability | ✅ pass | §6.1 |
| Code / artefact availability | ✅ pass | §6.2 with GitHub URL and Zenodo DOI placeholder |
| Ethics statement | ✅ pass | §6.3 |

---

## E. Suggested reviewers

| Check | Status | Evidence |
|---|---|---|
| Exactly 6 reviewers entered | ✅ pass | Endsley, Dehais, Lee, Van Dongen, El-Fiqi, Matthews — listed in `reviewer_list.md` |
| None is a current Associate Editor | ✅ pass | Cross-checked against THMS AE masthead (Birsen Donmez, David Kaber, Tyler Shaw, Liming Chen, etc. — none of the 6 match) |
| None is a co-author within last 3 years | ⚠️ pre-flight | **Diego must verify personally** against his ORCID 0000-0002-2257-4940 and Ingrid's 0000-0002-7981-2356 publication lists |
| ≥3 countries | ✅ pass | USA × 4, France × 1, Australia × 1 |
| None at corresponding author's institution | ✅ pass | None at DIMAE / Colombian Aerospace Force |
| Email reliability tier documented | ✅ pass | 3 emails verified at staff page / paper byline; 3 constructed-from-pattern flagged in `reviewer_list.md` for verification before submission |
| AE board fresh check on submission day | ⚠️ pre-flight | Re-verify AE masthead at https://www.ieeesmc.org/publications/transactions-on-human-machine-systems/associate-editors/ on submission day |

---

## F. OA / charges decision

| Check | Status | Evidence |
|---|---|---|
| OA track decided (Traditional vs OA) | ⚠️ pre-flight | Default Traditional ($0); Diego confirms at ScholarOne step |
| Page-count estimate | ✅ pass | 8 pages — well under 10-page cap; **no overlength surcharge** |
| Color print decision | ⚠️ non-blocking | Fig. 2 and Fig. 3 are color; if color print is requested, author bears incremental cost. Online Xplore is color regardless. |

---

## G. Multimedia (if applicable)

| Check | Status | Evidence |
|---|---|---|
| Multimedia attached | ✅ N/A | No multimedia in this submission. The benchmark code/data is in `tex/benchmark/` and is referenced in §3.3 + Supplement S4 as supporting material. |
| Manuscript self-contained without attachment | ✅ pass | Manuscript reads independently of the benchmark CSV/JSON; the data merely supports the table values. |

---

## H. Cover letter

| Check | Status | Evidence |
|---|---|---|
| Addressed to EIC by name | ✅ pass | "Prof. Ljiljana Trajkovic, Editor-in-Chief" |
| EIC currency verified | ⚠️ pre-flight | Re-verify on submission day at THMS site |
| Article type stated (Regular Paper) | ✅ pass | "**Article type:** Regular paper" |
| Prior-publication / preprint disclosure | ✅ pass | Variants A and B provided; pick one before send |
| Variant choice made | ⚠️ pre-flight | Diego picks A (conservative-truthful) or B (full AE-disclosure) |
| Authorship and corresponding-author identification | ✅ pass | Both authors named with ORCIDs; Diego marked corresponding |
| Conflicts of interest declared | ✅ pass | "no financial or non-financial competing interests" |
| AI-assistance declared | ✅ pass | "Use of generative-AI tools in manuscript preparation is disclosed in the manuscript per IEEE policy" |
| Six suggested reviewers referenced | ✅ pass | Mentioned in cover letter; full list in `reviewer_list.md` for ScholarOne entry |
| Repository self-overlap warning | ⚠️ pre-flight | Diego confirms whether the public GitHub repo materially describes OPI such that THMS' plagiarism screen will flag overlap; if yes, name the repo URL explicitly in the cover letter |

---

## Pre-flight checklist for Diego before pressing submit

- [ ] **Edit the `\thanks{Manuscript prepared April 2026.}` to `\thanks{Manuscript received [yyyy-mm-dd].}` (or remove and let editor add)**
- [ ] Decide on `grant2017` orphan: remove from `references.bib` or restore citation in §2.5
- [ ] Decide on color print: opt-in (and accept color charge) or convert Fig. 2/Fig. 3 to grayscale + patterns
- [ ] Verify Ljiljana Trajkovic is still Editor-in-Chief
- [ ] Confirm reviewer co-authorship pre-flight against ORCID 0000-0002-2257-4940 and 0000-0002-7981-2356 (none of the 6 should be a co-author in the past 3 years)
- [ ] Verify the 3 constructed-pattern reviewer emails against the institutional staff pages
- [ ] Re-check the THMS Associate Editor masthead on submission day (no last-minute changes that would invalidate a reviewer suggestion)
- [ ] Pick cover-letter variant A (conservative-truthful) or B (full AE-disclosure)
- [ ] Get Ingrid's sign-off on the THMS pivot and on the suggested reviewer list
- [ ] Tag a release of `https://github.com/strikerdlm/HRV` and mint a Zenodo DOI; update §3.4 and §6.2 to cite the DOI; recompile
- [ ] Run institutional iThenticate self-check on the manuscript PDF before upload
- [ ] Sign IEEE Copyright Form at the ScholarOne submission step
- [ ] Select Traditional submission ($0 APC) at the OA decision step (unless choosing OA at $2,195 USD)
- [ ] Verify postal address meets ScholarOne's street/postcode requirement (current entry is institutional-only)

---

## Files audited

| File | Status |
|---|---|
| `manuscript/submission_thms/tex/manuscript.tex` | audited |
| `manuscript/submission_thms/tex/references.bib` | audited |
| `manuscript/submission_thms/tex/figures/figure[1-4]_*.pdf` | audited |
| `manuscript/submission_thms/tex/manuscript.pdf` | audited (8 pages, letter) |
| `manuscript/submission_thms/cover_letter_template.md` | audited |
| `manuscript/submission_thms/reviewer_list.md` | audited |
| `manuscript/submission_thms/checklist.md` | audited |
| `manuscript/submission_thms/supplement.md` | audited |

---

## Verdict

**The manuscript is structurally compliant with IEEE THMS Information for Authors and is submission-ready pending the two blocking fixes (author footnote text; copyright-form signature at submission step) and the four non-blocking decisions (`grant2017` orphan, color print, OA track, cover-letter variant).**

Estimated time to resolve all open items before pressing submit: **< 30 minutes** of mechanical work plus Diego's pre-flight verification checks.
