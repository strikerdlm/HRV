# OPI Manuscript — Revision Plan for IEEE THMS

**Source manuscript:** `manuscript/submission_package/01_manuscript/manuscript.md` (~7,800 words, last built for Applied Ergonomics)
**Target:** IEEE THMS regular paper, 10 IEEE Transactions pages
**Working budget:** 5,500–6,000 words main text + ≤6 figures + ≤4 tables + ≤60 references
**Cut required:** ~1,800 words (≈25%) plus relocation of all code blocks and verification detail to a supplement

---

## Why this revision exists

Patrick G. Dempsey (Applied Ergonomics, JERG-D-26-00619) rejected the manuscript on pre-screen with five substantive complaints:

1. *"The manuscript is quite long"* — length pressure
2. *"Clearer research questions framed in the context of ergonomics theory and principles"* — RQs implicit, not framed
3. *"Technical editing would help, as the manuscript is quite difficult to follow"* — readability
4. *"Less emphasis on analytical methods as many readers and reviewers will not be able to follow the extensive computer code"* — code-heavy main text
5. *"Clearer implications for the application of ergonomics"* — application story not foregrounded

Three of these (1, 3, 4) are **independent of venue** and must be fixed. Two (2, 5) are venue-specific and the THMS reframe replaces ergonomics theory with **human-machine systems engineering** theory and replaces application-of-ergonomics with **inspectable-substrate-for-HMS-engineering** implications.

---

## Section-by-section cut targets

| Section | Current words | THMS target | Δ | Cuts / moves |
|---|---:|---:|---:|---|
| Title | — | — | — | Tighten: drop "with open-source reference implementation" — supplement covers it |
| Abstract | ~245 | **200** | −45 | Cut "Seventeen operator categories receive explicit profiles" (move to body); replace "API-linked modules" with "supporting modules" |
| 1. Introduction | ~1,250 | **900** | −350 | §1.1 keep; §1.2 trim (cut redundant Wickens/Endsley/McEwen citations to one each); §1.3 keep; §1.4 cut Antarctic campaign detail — move to §4.6 |
| 2. Methods | ~2,400 | **1,800** | −600 | §2.1 keep equations only, remove walk-through prose; §2.2 keep table reference, drop in-line list; §2.3 keep table reference; §2.4 condense vigilance and latency models to equations + brief justification; **§2.5 Reference implementation: cut to 100 words pointing to supplement and DOI**; §2.6 keep |
| 3. Results | ~1,000 | **900** | −100 | §3.1 keep; §3.2 cut verification table walkthrough to one paragraph + reference to supplement; §3.3 keep |
| 4. Discussion | ~1,400 | **1,250** | −150 | §4.1–4.4 keep; §4.2 trim comparison subsections; §4.5 limitations keep; **§4.6 reframe as "Validation roadmap and HMS-engineering integration" — replaces ergonomics-specific language** |
| 5. Conclusion | ~150 | **150** | 0 | Keep |
| 6. Compliance and Transparency | ~700 | **350** | −350 | Keep §6.1 data, §6.2 code, §6.3 ethics, §6.4 CRediT, §6.5 funding/COI; **drop §6.6 reporting-guideline positioning** (move to supplement); collapse remaining subsections to a single paragraph each |
| Acknowledgements + AI declaration | ~150 | **150** | 0 | Keep AI declaration verbatim — IEEE expects this |
| References | ~50 refs | **≤55 refs** | — | Audit; remove redundant supporting citations |
| **Total prose** | **~7,300** | **~5,700** | **−1,600** | Plus references and figures |

---

## Code block relocation map

The AE editor's strongest objection. Every code block in the main text moves to supplement; main text retains pseudocode and one-line equations.

| Current location | Disposition |
|---|---|
| Any inline Python/TypeScript snippet | **Cut from main text.** Pseudocode if essential. |
| `app/hrv_core.py` walkthroughs | Supplement S1: "Reference implementation reference card" |
| `app/pvt_core.py` derivation walkthrough | Supplement S2 |
| Engineering verification tables (Tables 5/6 in current package) | Keep ONE summary row in main text Table; full matrix in Supplement S3 |
| `app/safte_model.py` mathematical formulation | Keep equations in main text §2.1; cut narrative |

**Rule of thumb:** main text contains *what the framework computes* and *what the worked example shows*; supplement contains *how the implementation does it* and *how it was verified*.

---

## Research questions — explicit rewrite

Insert at the end of §1.3 (Gap statement) or as a new §1.4 before "Objective and contribution":

> This manuscript investigates three research questions:
>
> **RQ1.** Does task-calibrated weighting of fatigue, autonomic, and cognitive-load components change readiness classification when summary HRV indices are held constant?
>
> **RQ2.** Are theory-derived per-task weight profiles identifiable on operationally-realistic operator samples, given known constraints on aerospace data availability?
>
> **RQ3.** Does a linear weighted-composite substrate support traceable, audit-friendly safety-case logic for human-machine system gate decisions without sacrificing classification fidelity relative to opaque end-to-end classifiers?
>
> RQ1 is addressed in the present manuscript via the illustrative worked example. RQ2 and RQ3 are framed as the validation roadmap; field instrumentation is planned for the 2026–2027 austral summer Antarctic campaign and is the subject of a separate protocol publication.

Set this up so RQ1 is the contribution claimed, RQ2/RQ3 are honest as future work — keeping the evidence-discipline guardrail from `manuscript/CLAUDE.md`.

---

## Implication reframing — THMS-specific

Replace ergonomics-application language with HMS-engineering-substrate language. Concrete edits:

| Current phrasing | THMS reframe |
|---|---|
| "implications for ergonomics practice" | "implications for human-machine system design" |
| "operator readiness composite" | "human-state input layer for human-machine teaming" (use sparingly) |
| "aerospace ergonomics" | "aerospace human-machine systems" |
| "human factors literature" | "human-machine systems literature" (where context fits) |
| "audit-friendly" | keep — IEEE THMS reviewers value this term |
| "safety review" | keep, expand to "system test and evaluation" (mirrors THMS scope verbatim) |

Add to §4.1 Principal contribution a sentence like:

> The OPI framework is positioned as an inspectable input substrate for downstream human-machine teaming workflows, supporting the system test and evaluation activities that are central to aerospace operator-loop integration.

This single sentence maps your manuscript onto THMS scope language verbatim. Reviewers spot this.

---

## Title — proposed shortening

**Current (24 words):**
> Task-calibrated Operational Performance Indicators for aviation and unmanned aircraft system operators: a biomathematical framework integrating SAFTE fatigue, heart-rate variability, and cognitive-load theory, with open-source reference implementation

**Proposed (16 words):**
> Task-calibrated Operational Performance Indicators for aviation and unmanned aircraft system operators: a biomathematical human-machine systems framework

Drops "SAFTE/HRV/cognitive-load theory" (covered in abstract) and "open-source reference implementation" (covered in body and supplement). Adds "human-machine systems" — pulls the title onto THMS scope.

**Running title (max ~50 chars):** *Task-calibrated OPI for aerospace HMS operators* — 45 chars including spaces. Keep.

---

## Tables — keep / cut / move

| Current table | Action | Rationale |
|---|---|---|
| Table 1. Task taxonomy (17 categories) | **Keep** in main text | Spine of the contribution |
| Table 2. Component formulation and weight profiles | **Keep** in main text | Spine |
| Table 3. Vigilance/latency models | **Keep** | Compact; spine |
| Table 4. Related-work comparison | **Keep** but trim to 4 rows | Reviewer crutch |
| Table 5. Engineering verification coverage | **Move to supplement**; one summary row in main text | Code/test focus is what AE editor objected to |
| Table 6. Reproducibility/deployment metadata | **Move to supplement**; one paragraph in §6.2 main text | Same reason |
| Table 7. Compliance and transparency declarations | **Move to supplement**; collapse to a paragraph | AE-specific; not a THMS norm |

**Result: 4 tables in main text** (down from 7). Frees ~1.5 IEEE pages.

---

## Figures — keep / replace / move

| Current figure | Action | Rationale |
|---|---|---|
| Figure 1. Conceptual schematic | **Keep** | Anchor figure |
| Figure 2. Task taxonomy + HRV signatures | **Keep** | Spine |
| Figure 3. Worked example output | **Keep** | Spine — only empirical figure |
| Figure 4. Reference-implementation architecture | **Cut from main text**; move to supplement | Architectural detail not load-bearing for the framework claim |

**Result: 3 figures in main text** (down from 4). Frees ~0.75 IEEE pages.

Re-export all kept figures in IEEE-compliant format: vector SVG/EPS for line art, ≥600 dpi for raster, monochrome-readable when printed in B&W.

---

## Order of operations

1. **Branch.** Create `thms-revision` branch from `main`. Tag the AE-rejected snapshot first: `git tag rejected-AE-2026-04-30`.
2. **Title + abstract rewrite.** Lock these first — they fix the framing the rest of the paper has to align with.
3. **Insert RQs** at the end of §1.3 (or new §1.4).
4. **Cut Methods §2.5 and §6.6**, move content to a new `submission_thms/supplement.md`. These are the largest single cuts.
5. **Pseudocode pass.** Replace every code block with prose + pseudocode. Then re-count words.
6. **Section-by-section cut to budget.** Use the table above as gating targets.
7. **Implication reframe pass.** Sweep the diff for AE-language → THMS-language replacements.
8. **Reference audit.** Cut to ≤55 refs; convert to IEEE numbered style.
9. **Figure/table re-export** to IEEE format.
10. **LaTeX two-column compile** with IEEEtran.cls; iterate to fit 10 pages exactly.
11. **Reviewer list rebuild** (6 names; THMS-active labs).
12. **Cover letter** from `cover_letter_template.md` with prior-submission disclosure phrasing.
13. **Final checklist** (`checklist.md`) before portal upload.

Estimated effort: **5–6 focused sessions** (each ~3 hours). Sessions:

1. Title / abstract / RQ rewrite + section cuts in markdown to hit ~5,700 prose words
2. Pseudocode pass (replace code blocks) + reference audit and IEEE-numbering conversion
3. **Markdown → IEEEtran two-column LaTeX conversion.** Compile under `IEEEtran.cls`, iterate prose until the manuscript fits 10 IEEE pages exactly. Word count alone does not predict page count — figures, tables, equations, and reference layout dominate. Plan for at least one full session here. This step is non-negotiable: ScholarOne accepts PDFs but the page-cap is enforced against the IEEE two-column rendering, not against the markdown source.
4. Figure/table re-export to IEEE format (vector EPS/SVG; ≥600 dpi raster; B&W-readable)
5. **Reviewer list construction.** Convert the seed traditions (Wickens, Parasuraman heirs, Endsley collaborators, Chen, Warm-tradition, Salas, Hancock, Lee, active THMS-publishing labs) into 6 *concrete people* with current affiliation, institutional email, URL. Each must be checked against the current THMS Associate Editor masthead and against your co-authorship history (last 3 years). Span ≥3 countries. Realistic effort 2–3 hours and must be done before portal upload.
6. Cover letter finalisation (pick variant A or B), checklist run, portal upload

Sessions 1, 2, and 6 are prose work. Sessions 3, 4, 5 are the *hidden cost* — they are the work that turns a clean markdown revision into an actual IEEE submission. Do not collapse them into the prose sessions.

---

## Decision points to resolve before starting

1. **Antarctic campaign protocol mention.** Stays in §1.4 (one sentence) and §4.6? Or cut entirely from this manuscript and reserve for the protocol publication? Recommendation: keep one sentence to motivate the framework's deployment intent; do not detail.
2. **Compliance and Transparency depth.** §6 is currently AE-shaped (Compliance + reporting-guideline positioning). For THMS, reduce to 1 paragraph each on data, code, ethics, CRediT, funding/COI, AI use. Confirm.
3. **PVT and sleep modules.** Currently introduced in §1.4 as part of the contribution. Recommendation: keep both — they concretise the vigilance and fatigue inputs and reinforce the HMS substrate framing — but cut their per-module verification narrative.
4. **Authorship metadata.** Confirmed: Diego (corresponding) + Ingrid. CRediT statement already in `submission_package/04_declarations/`. Reuse.
5. **Co-author review and approval** of the THMS pivot before submission. This is a real change of venue framing and should not be a unilateral PI decision.

---

## What does *not* need to change

- The 17-category task taxonomy — direct match to THMS scope
- The four-component fusion equations — equation form is fine, prose around them needs trimming
- The Warm-type vigilance and Chen-type latency models — these are HMS literature, on-target
- The illustrative worked example with three task hypotheses — exactly the right level of evidence for a framework paper
- The hedged claim envelope ("framework definition + software + illustrative demonstration; field validation is future work") — preserves evidence discipline; reviewers respect it
- The MIT-licensed reference implementation — repositioned as supplementary artefact, not main-text content
- Author identities, ORCIDs, affiliations
- Funding/COI declarations
