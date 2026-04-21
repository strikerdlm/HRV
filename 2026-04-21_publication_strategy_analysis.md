# Publication Strategy Analysis

**Date:** 2026-04-21
**Manuscript:** Mission Control - Flight Surgeon
**Type:** Systems / software / methods paper (open-source biomathematical platform)
**Evidence posture:** Engineering verification strong; clinical validation explicitly bounded / future work

---

## 1. Core Publishing Problem

This manuscript is a **software-and-systems paper**, not a clinical trial. Its strongest evidence is architecture, implementation, and engineering verification (366 tests). Its weakest evidence is external numerical benchmarking, human-subject validation, and regulatory certification. The publication strategy must match journals whose scope explicitly accepts systems/methods submissions without demanding clinical cohort data.

---

## 2. Journal Shortlist: Detailed Comparison

| Journal | Quartile / IF (2024) | APC (USD) | Colombia / LMIC Waiver | Preprint Policy | Software/Methods Fit | Time to First Decision | Clinical Validation Required? |
|---|---|---|---|---|---|---|---|
| **CMPB** | Q1 (Med. Informatics 86.4%); IF **4.8** | $3,180 hybrid; subscription $0 | No automatic waiver for hybrid; case-by-case hardship | Very friendly (SSRN integration; preprints do NOT count as prior publication) | **Excellent — explicit scope for computing methodology and software systems** | ~40 days median | **No** |
| **JBI** | Q1 (Med. Informatics 70.8%); IF **4.5** | ~$3,000+ hybrid; subscription $0 | Same as CMPB | Very friendly (SSRN; explicit policy) | **Excellent — premier methods journal; AMIA-endorsed** | ~40-60 days | **No** |
| **npj Digital Medicine** | Q1 (Med. Informatics **99.5%**); IF **15.1** | ~$3,090-$3,590 fully OA | No automatic waiver; discretionary only | Explicitly allows; update preprint with published DOI | Strong; requires utility + validation + availability | **Median 10 days** | No for systems, but bar is higher |
| **Military Medical Research** | Q1 (Medicine, Gen. 97.6%); IF **22.9** | **$0 (fully waived)** | **APC fully waived for all authors** | Conservative but not restrictive | Good; domain-forward for operational medicine | ~8 weeks | No for systems |
| **PLOS Digital Health** | Q1 (Hlth Care Sci. 96.2%); IF **7.7** | $3,043 | Need-based waiver available; Global Equity programs | Extremely friendly | **Explicitly welcomes software** with dedicated guidelines | ~16 weeks | No |
| **BMC Med. Inform. Decis. Mak.** | Q1/Q2; IF **3.3** | $3,090 | Discretionary only | Springer Nature standard | Excellent; direct scope match | ~23 weeks | No |
| **JMIR** | Q1; IF **6.0** | $3,350 | APF waiver/support available on justification | Very friendly | Strong; largest digital health journal by citations | Efficient | No |

### Key Finding: APC Reality for Colombia

- Colombia is classified as **upper-middle income** by the World Bank.
- **Elsevier GPOA pilot** (50% discount) applies only to fully Gold OA journals; CMPB and JBI are **hybrid**, so no automatic discount.
- **Nature / Springer** automatic waivers apply only to lowest-income countries; Colombia is not eligible.
- **PLOS** has the most flexible need-based waiver program among the commercial publishers.
- **Military Medical Research** is the only Q1 journal in the list with a **guaranteed zero APC**.

---

## 3. Tiered Recommendation

### Tier 1 — Submit Here First

1. **CMPB (primary target)**
   - Only journal whose founding mission is literally computing methodology and software for biomedicine.
   - No clinical validation required.
   - Can publish subscription-route for free if APC is unavailable.
   - Preprint policy is seamless.
   - Risk: low. Rejection would likely be due to perceived lack of methodological novelty rather than scope mismatch.

2. **JBI (strong alternative)**
   - Higher methodological prestige (AMIA endorsement).
   - Same Elsevier hybrid structure = same APC constraints.
   - Adds friction: mandatory graphical abstract, Statement of Significance, 6,000-word limit, max 8 figures/tables.
   - Use if the paper reads more as methodological innovation than systems description.

### Tier 2 — Strategic Options (High Impact, Low or Manageable Cost)

3. **Military Medical Research (zero-cost wildcard)**
   - Highest IF (22.9), zero APC, fastest turnaround (~8 weeks).
   - Domain-aligned for aerospace readiness / operational medicine.
   - Caveat: Chinese military-affiliated editorial context (KeAi / Beijing). Consider whether geopolitical framing aligns with academic positioning.
   - If comfortable with that context, this is financially unbeatable.

4. **PLOS Digital Health (best accessible high-impact option)**
   - IF 7.7, explicitly pro-software editorial policy.
   - Need-based waivers are more flexible than Elsevier/Nature.
   - Requires full algorithm details, dependency lists, installation instructions, test data, and direct code links at submission.

### Tier 3 — Stretch or Backup

5. **npj Digital Medicine** — Most prestigious but most expensive with weakest waiver safety net. Only pursue with confirmed APC funding.
6. **BMC Medical Informatics and Decision Making** — Safe Q1/Q2 backup for rapid resubmission.
7. **JMIR** — High citation visibility; APF waivers negotiable but not guaranteed.

---

## 4. Preprint Strategy

### Recommended Server: medRxiv (Health Informatics)

- Active health informatics channel accepts software/methods papers without clinical trial data.
- Compatible with all target journals.
- If scope screening fails, fallback to **arXiv cs.HC**.
- Do not dual-post to both simultaneously.

### Timing

| Strategy | Verdict |
|---|---|
| Preprint before submission | **Recommended.** Low scooping risk for software; establishes priority; enables community feedback; all target journals allow it. |
| Preprint after acceptance | Loses early visibility and priority. |
| No preprint | Not recommended for software papers. |

---

## 5. Archiving and DOI Strategy

Do this **before** preprint submission:

1. Create GitHub release (e.g., `v1.0.0`).
2. Enable Zenodo-GitHub integration. Zenodo automatically mints a DOI.
3. Use the **Concept DOI** in the manuscript (resolves to latest version).
4. Add `CITATION.cff` and OSI-approved LICENSE (MIT or Apache-2.0) to repository root.
5. Optional: force Software Heritage archival via `save.softwareheritage.org` for SWHID.

This is mandatory for npj Digital Medicine and strongly preferred by all others.

---

## 6. Parallel JOSS Submission

Simultaneously prepare a **Journal of Open Source Software (JOSS)** submission:

- **Cost:** $0
- **Indexed:** DOAJ-listed
- **Scope:** Exactly matches this platform (Next.js/FastAPI/Python stack)
- **Requirements:** Open-source license, documentation, tests (366 tests already satisfy this), installation instructions, Statement of Need
- **Dual publication:** Ethically acceptable; JOSS and a traditional journal serve different scholarly functions. JOSS explicitly asks authors to disclose related publications.

---

## 7. Submission Tactics

### Cover Letter Framing (All Journals)

Use the cover letter to **preempt scope critiques**:

> This manuscript reports the architecture, implementation, and engineering verification of Mission Control - Flight Surgeon, an open-source biomathematical platform for HRV analytics, fatigue-circadian modeling, and aerospace readiness. Clinical validation in operational populations is planned as a separate prospective study.

### Handling "Where Is the Clinical Validation?"

1. Define contribution boundaries in the **abstract**: "This paper describes the design, implementation, and bounded verification of..."
2. Cite the journal's own scope language (CMPB: "application software design"; JBI: "novel biomedical informatics methods").
3. Emphasize generalizability (especially for JBI).
4. Provide a translational workflow schematic showing operational integration intent, even without validation data.

### Graphical Abstract Requirements

| Journal | Required? | Specs |
|---|---|---|
| CMPB | Optional but encouraged | Min 531x1328 px; TIFF/EPS/PDF |
| JBI | **Mandatory** | Same specs; must be provided at submission |
| npj Digital Medicine | Best practice | High-res vector or TIFF |
| Military Medical Research | Best practice | Springer Nature figure guidelines |

For a systems paper, show the four-layer pipeline (HRV → fatigue-circadian → readiness → environment) as a clean left-to-right flow. Minimal text.

### Data / Code Availability Templates

**For CMPB / JBI (Elsevier standard):**

```
Data Availability: The datasets generated during this study are included in this published article and its supplementary information files.
Code Availability: The underlying code is available at [GitHub URL] and archived in Zenodo at https://doi.org/xx.xxxx/zenodo.xxxxx under an MIT License.
```

**For npj Digital Medicine (Nature Portfolio — mandatory separate sections):**

```
Data Availability
The datasets generated and/or analysed during the current study are available in the [repository name] repository, [persistent URL].

Code Availability
The underlying code for this study is available at [GitHub URL] and can be accessed via this link [persistent URL].
```

Nature Portfolio explicitly states: GitHub alone is insufficient; code should be deposited in a DOI-minting repository (Zenodo or Code Ocean).

### Supplementary Materials

- CMPB / JBI: Peer-reviewed, published online as received (not typeset). Combine text and figures in one PDF; tables as individual files. Excel/PowerPoint appear as-is.
- npj Digital Medicine: Submit as a single merged PDF if possible. Sent to referees. Not edited by production.
- Best practice: Include detailed verification tables, architecture diagrams, and API documentation.

### Authorship and CRediT

- **CRediT:** Supported by all journals; increasingly mandatory for Elsevier and Nature Portfolio.
- **ORCID:** Required for corresponding authors at Nature; encouraged everywhere.
- **Author Contributions (npj Digital Medicine):** Mandatory; use initials to specify individual contributions.

---

## 8. Actionable Next Steps

### Immediate (This Week)

- [ ] Confirm APC funding status (institutional / grant / personal budget)
- [ ] Check Colombian institutional transformative agreements with Elsevier, Springer Nature, or JMIR
- [ ] Finalize repository hygiene: add `CITATION.cff`, LICENSE, installation instructions, minimal reproducible example
- [ ] Create GitHub release `v1.0.0` and enable Zenodo integration
- [ ] Add Software Heritage archival (optional but strengthens reproducibility)

### Week 1-2

- [ ] Post preprint to **medRxiv Health Informatics** (or arXiv cs.HC fallback), citing Zenodo DOI
- [ ] Prepare cover letter for chosen Tier 1 journal
- [ ] Prepare graphical abstract if targeting JBI or npj Digital Medicine
- [ ] Draft Data Availability and Code Availability statements

### Parallel Track

- [ ] Prepare JOSS submission (zero APC; short paper; strengthens software credit)

### Weeks 2-4

- [ ] Submit to primary target journal, disclosing preprint DOI and any related submissions in cover letter
- [ ] If CMPB rejects, assess reviewer feedback and pivot to JBI or BMC Medical Informatics
- [ ] If APC is a hard constraint, submit to **Military Medical Research** instead

### Post-Acceptance

- [ ] Update preprint metadata with published DOI (required by Nature; good practice for all)
- [ ] Update Zenodo record with journal citation

---

## 9. Decision Matrix

| If this is true... | Then do this... |
|---|---|
| You have APC funding confirmed | Submit to **CMPB** (primary) or **JBI** (prestige). Consider **npj Digital Medicine** as stretch. |
| You have no APC funding | Submit to **Military Medical Research** (zero cost, Q1, IF 22.9) or **JOSS** (zero cost, software credit). |
| You want maximum methodological prestige | **JBI** (AMIA-endorsed, strict but respected). |
| You want fastest publication | **Military Medical Research** (~8 weeks) or **npj Digital Medicine** (median 10 days to first decision). |
| You want strongest software-specific credit | **JOSS** (free, indexed, peer-reviewed software paper). |
| You want lowest risk of scope rejection | **CMPB** (explicitly founded for computing methodology and software). |
| You want explicit pro-software editorial policy | **PLOS Digital Health** (dedicated software guidelines, need-based waivers). |

---

## 10. Open Questions for Diego

1. **APC budget:** Is there institutional or grant funding for publication fees? This determines whether CMPB/JBI/npj are viable.
2. **Institutional agreements:** Does Universidad Nacional de Colombia (or affiliated institution) have a read-and-publish deal with Elsevier, Springer Nature, or JMIR?
3. **Geopolitical comfort:** Are you comfortable submitting to Military Medical Research given its Chinese military-affiliated editorial context?
4. **JOSS interest:** Do you want to pursue the parallel JOSS submission for independent software credit?
5. **Preprint preference:** Any reason to avoid preprinting before journal submission?

---

*Document generated from subagent research on journal policies, APC structures, preprint compatibility, and submission tactics. All quartile/IF data retrieved from live sources on 2026-04-21. APC figures are current as of that date but should be verified at the journal's official author guidelines page before submission.*
