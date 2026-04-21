# Sleep module backlog & implementation guide

This file merges the **pending feature list**, **literature grounding** (PubMed via paper-search MCP), and a **concrete rollout plan** for Mission Control / Garmin-backed research views.

---

## 1. Original backlog (unchanged intent)

### Pending to develop

- Sleep architecture, scoring, staging, hypnogram, latency  
- Sleep durations, consistency, efficiency, disturbance, arousal, fragmentation  
- Sleep apnea-related views (screening-style, not diagnostic)

### Desired correlations & metrics

See §4 for what is **implementable now** vs **needs non-Garmin / PSG data**.

---

## 2. What PubMed supports (compact evidence map)

Legend: **Human clinical / PSG or controlled studies** describing autonomic sleep physiology and correlations relevant to sleep × HRV × respiration × oxygenation.

| Theme | Finding (direction / context) | Example references |
|--------|-------------------------------|---------------------|
| **Sleep stages × HRV** | RMSSD/HF rise from wake → NREM (incl. SWS), partial reversal toward REM (parasympathetic modulation stage-dependent). Moderate sleep-disordered breathing **amplifies drops** HF/RMSSD **SWS → REM**. | PMID [20337904](https://pubmed.ncbi.nlm.nih.gov/20337904/), [19453563](https://pubmed.ncbi.nlm.nih.gov/19453563/) |
| **OSA severity × autonomic proxies** | Higher apnea burden ↔ altered LF/HF, RMSSD patterns across sleep (population/clinical cohorts); modern work links **wake RMSSD** ↔ **AHI**, **mean nocturnal SpO₂** (reported correlations; context-specific). | PMID [19453563](https://pubmed.ncbi.nlm.nih.gov/19453563/), [41953462](https://pubmed.ncbi.nlm.nih.gov/41953462/) |
| **Sleep deprivation / fragmentation × ANS** | Fragmentation / deprivation associated with **autonomic imbalance** (HF suppressed, sympathovagal shifts); systematic reviews emphasize **heterogeneity** of protocols. | PMID [40895095](https://pubmed.ncbi.nlm.nih.gov/40895095/), [40768960](https://pubmed.ncbi.nlm.nih.gov/40768960/) (circadian fragmentation ↔ suppressed HF / raised LF∶HF patterns) |

**Wearable caveat:** Garmin provides **daily summaries** (scores, epoch-style seconds for stages when the API exposes them), not clinical hypnograms. Plots must be labelled **exploratory / wellness device**, not PSG-equivalent ([Task Force / consensus on HRV standards](https://pubmed.ncbi.nlm.nih.gov/8598068/) applies to interpretation, not vendor validation).

---

## 3. Garmin daily data vs Pending.md ambitions

**Already in SQLite / API when sync succeeds:**  
`sleep_duration_hours`, `sleep_efficiency`, `sleep_score`, stage minutes (deep/REM/light/awake seconds→minutes where returned), overnight **HRV RMSSD**, **resting HR**, stress, **avg SpO₂**, respiration (wake/sleep averages), body battery summaries.

**Not available from Garmin daily summaries alone:**

| Pending.md concept | Garmin daily? | Practical note |
|--------------------|---------------|----------------|
| Hypnogram, arousal index, fragmentation index | No | Need raw epoch / event stream or research export |
| Formal sleep latency / WASO | Rarely complete | Garmin may expose partial summaries; validate per export |
| Sleep apnea diagnosis | No | Screening-style only (SpO₂ pattern proxies + symptoms off-device) |

Use this table to **trim scope for v1** and avoid over-claiming “apnea” from consumer aggregates.

---

## 4. Tiered implementation (simple & concrete)

### Tier A — Ship first (only existing columns; aligns with literature directions)

Implement as **paired time-series + scatter** on `/research/garmin` (and shared chart helpers), following `.cursor/rules/plots.mdc` (ECharts, `SCIENTIFIC_COLORS`, anti-clutter, dynamic axes).

| Plot / analysis | Variables (from DB/API) | Expected direction (literature) | Significance at α=0.05 |
|-------------------|-------------------------|----------------------------------|-------------------------|
| Sleep duration × overnight HRV | `sleep_duration_hours` vs `hrv_rmssd_ms` | Better sleep duration often tracks recovery / parasympathetic tone (population-dependent) | **Must be computed per user × window** (see §5) |
| Sleep score × RMSSD | `sleep_score` vs `hrv_rmssd_ms` | Higher subjective/derived score ↔ better recovery in many cohorts | Same |
| Stage balance × RMSSD | deep+REM minutes vs `hrv_rmssd_ms` | Stage physiology linked to autonomic state ([20337904](https://pubmed.ncbi.nlm.nih.gov/20337904/)) | Same |
| Resting HR × RMSSD | `resting_hr_bpm` vs `hrv_rmssd_ms` | Inverse association common (fitness / stress) | Same |
| SpO₂ × RMSSD | `avg_spo2` vs `hrv_rmssd_ms` | Lower nocturnal SpO₂ ↔ stress on autonomic system in OSA contexts ([41953462](https://pubmed.ncbi.nlm.nih.gov/41953462/) abstract reports RMSSD–SpO₂ patterns in one cohort) | Same |
| Respiration (sleep) × RMSSD | `avg_respiration_sleep` vs `hrv_rmssd_ms` | Physiological coupling; strength varies | Same |

**Backend:** extend `GET /api/research/garmin/history/{user_id}` payloads only if new aggregates are derived server-side (keep one source of truth).  
**Frontend:** reuse patterns from existing Garmin correlation scatter + trend builders; add **chart subtitle**: “Exploratory; wellness device; not diagnostic.”

### Tier B — Needs extra ingestion

- **Hypnogram / fragmentation / arousals:** ingest Garmin FIT/sleep JSON exports or research APIs into new tables; then staging pipelines from `app/garmin_import.py` patterns.  
- **Fatigue / performance / sleepiness scales:** join Garmin dates with **user-entered** KSS / PVT / workload endpoints already elsewhere in the app (`/research/fatigue`, `/research/pvt`) by `user_id` + date.

### Tier C — Screening-only language

- **Sleep apnea:** restrict UI to **“risk proxy”** composites (e.g., rolling low SpO₂ nights + high resting HR), never **AHI** unless PSG imported.

---

## 5. Statistical note on “significant at 0.05”

You asked to flag correlations significant at **α = 0.05**.

- Literature **p-values apply to those studies’ samples**, not your SQLite export.  
- **Implementation:** for each scatter pair and rolling window (e.g. ≥14 or ≥30 nights with non-null pairs), compute **Pearson or Spearman** + **two-sided p-value**, **FDR correction** if testing many pairs on the same window. Display: *r*, *p*, *n nights*, and a footnote when **n < 14** (“underpowered”).  
- Do **not** hard-code which pairs are “always significant”; surface **empirical** results.

Suggested minimal stack: **SciPy** (`scipy.stats.pearsonr` / `spearmanr`) in a small FastAPI helper under `/api/research/garmin/correlations/{user_id}` returning `{metric_x, metric_y, r, p, n, method}`.

---

## 6. File-level checklist (where to touch code)

| Step | Location |
|------|-----------|
| Paired nightly metrics already exposed | `api/research_endpoints.py` Garmin history/latest |
| Persist any new Garmin fields | `app/user_database.py` `GarminDailyMetrics`, migrations |
| Correlation endpoint (optional) | New route in `api/research_endpoints.py` or tiny module imported by router |
| Charts | `frontend/src/app/research/garmin/page.tsx`; palette `SCIENTIFIC_COLORS` / `plots.mdc` |
| Normative wording | Card disclaimers beside charts |

---

## 7. Duplicate lines in original notes

The earlier list repeated “Sleep architecture vs sleep disturbance/arousal/apnea” several times — treat as **one correlation family** per outcome (disturbance, arousal, apnea proxy) once Tier B/C data exist.

---

## References (from MCP PubMed search)

1. Liao D, et al. Sleep-disordered breathing in children — sleep stage-specific autonomic modulation. *J Sleep Res.* PMID [20337904](https://pubmed.ncbi.nlm.nih.gov/20337904/).  
2. Kesek M, et al. HRV during sleep and sleep apnoea — population women. PMID [19453563](https://pubmed.ncbi.nlm.nih.gov/19453563/).  
3. Zhang S, et al. Sleep deprivation and HRV — systematic review & meta-analysis. PMID [40895095](https://pubmed.ncbi.nlm.nih.gov/40895095/).  
4. Zhu L, et al. Circadian types and 24-hour HRV — fragmented sleep patterns. PMID [40768960](https://pubmed.ncbi.nlm.nih.gov/40768960/).  
5. Balali P, et al. Wake HRV vs sleep apnea indicators / SpO₂ (clinical + altitude cohort). PMID [41953462](https://pubmed.ncbi.nlm.nih.gov/41953462/).  

(Task Force HRV standards: Circulation 1996 — PMID [8598068](https://pubmed.ncbi.nlm.nih.gov/8598068/) — use for methodology text in exports.)


---

## 8. Cognition: literature (English synthesis) & Spanish / Latin America validation sources

### 8.1 Goal (Mission Control)

Use **short, repeatable cognitive probes** alongside **Garmin/PVT** to contextualize sleep–performance claims: join outcomes by **`user_id` + date**, same pattern as Tier B in §4 (fatigue/PVT). Tests do **not** validate Garmin sleep **accuracy** against PSG; they validate **whether worse sleep nights co-vary with next-day cognition** within your cohort.

### 8.2 SART (Sustained Attention to Response Task)

**English-language construct:** Go/no-go sustained attention / inhibition (withhold on rare “No-Go”). Widely used in fatigue, ADHD, and sleep-loss research.

- **Psychometric note:** Alternate stimulus sets exist (digits vs. gratings); validation of a non-numerical parallel form — PMID [37210673](https://pubmed.ncbi.nlm.nih.gov/37210673/) · DOI [10.1080/23279095.2023.2213792](https://doi.org/10.1080/23279095.2023.2213792) (Lanssens et al., *Applied Neuropsychology: Adult*). Clinical utility after TBI remains debated — PMID [16682059](https://pubmed.ncbi.nlm.nih.gov/16682059/) · DOI [10.1016/j.neuropsychologia.2006.02.012](https://doi.org/10.1016/j.neuropsychologia.2006.02.012) (Whyte et al., *Neuropsychologia*).
- **Operational note (same codebase as your PVT):** Passi et al. compared **PVT** vs **SART** under fatigue: performance patterns and HR/HRV coupling differ by task—“arousing” task characteristics can mask vigilance decrement — PMID [35959037](https://pubmed.ncbi.nlm.nih.gov/35959037/) · DOI [10.3389/fpsyg.2022.925157](https://doi.org/10.3389/fpsyg.2022.925157) (*Frontiers in Psychology*). Interpret **Garmin × cognition** correlations as **task-specific**, not interchangeable with PVT lapses.

**Spanish-speaking Latin America — direct SART norms:** Few peer-reviewed **pure SART** standardizations were located for Colombia specifically. Practical approach for Colombia:

1. Use **literature-backed** scoring (commission errors, omission errors, RT variability) with **within-person z-scores** until local norms exist.
2. Pair with instruments that **do** have Ibero-American normative projects (Rivera et al., *NeuroRehabilitation* special issue — see §8.5).
3. **Commercial Spanish CPT-family tools** used in Spain/LATAM schools (different paradigm than Robertson SART but addresses “atención sostenida”) — **CSAT-R** (*Tarea de Atención Sostenida en la Infancia – Revisada*): Spanish manual Hogrefe TEA; empirical study with ADHD/high-ability comparison using CSAT-R — Servera et al., *Anales de Psicología* / SciELO [DOI 10.6018/analesps.477731](https://doi.org/10.6018/analesps.477731) (includes collaborator affiliation Colombia). **Limits:** CSAT-R targets **children (~6–11)**; adults need PVT-like or adult CPT norms.

### 8.3 CPT (Continuous Performance Test)

**English-language construct:** Vigilance + inhibitory control over long stimulus streams (commission/omission, RT, variability). **Conners CPT-II** is the common commercial implementation.

**Latin America — empirical studies (Spanish venues / regional samples):**

Use **DOI-first** links where possible; some regional hosts (SciELO HTML) sit behind bot protection — the DOI remains the stable identifier.

| Focus | Region / language | Takeaway |
|--------|-------------------|----------|
| Conners CPT-II **Brazil vs US** children | Brazil | Brazilian children often outperform US published norms — argues for **local norms**, not imported US cutoffs — ERIC [EJ793561](https://eric.ed.gov/?id=EJ793561) (Miranda et al., *Journal of Attention Disorders*, 2008); journal DOI [10.1177/1087054707299412](https://doi.org/10.1177/1087054707299412). |
| Conners CPT **adolescents** age/gender | Brazil | Local reference data for **12–17 y** — Miranda et al., *Psychology & Neuroscience*, 2013 — DOI [10.3922/j.psns.2013.1.11](https://doi.org/10.3922/j.psns.2013.1.11) · optional mirror [SciELO HTML](https://www.scielo.br/j/pn/a/FFGyJgy7Y3DnbH7g3vpY3Px/?format=html&lang=en) (may challenge automated fetchers). |
| Conners CPT **TDAH vs controls** | Chile (Spanish article) | Discriminative utility — DOI [10.4067/S0718-48082017000300283](https://doi.org/10.4067/S0718-48082017000300283) (*Terapia Psicológica*, 2017). |
| **PennCNB-cv** (includes **Penn CPT**-class tasks) — Spanish validation | Spain | Community adolescent validation — PMID [39432534](https://pubmed.ncbi.nlm.nih.gov/39432534/) · DOI [10.1002/mpr.2035](https://doi.org/10.1002/mpr.2035) · PMC [PMC11493150](https://pmc.ncbi.nlm.nih.gov/articles/PMC11493150/). |

**Colombia-specific:** **BIS-15S** impulsivity scale validated in **Colombian** clinical + community Spanish speakers — PMID [21152412](https://pubmed.ncbi.nlm.nih.gov/21152412/) · DOI [10.1016/s0034-7450(14)60239-0](https://doi.org/10.1016/s0034-7450(14)60239-0) (*Revista Colombiana de Psiquiatría*; full text also [PMC2996610](https://pmc.ncbi.nlm.nih.gov/articles/PMC2996610/)). Self-report complement to CPT, not a substitute.

### 8.4 “Test de Atención Sostenida de Respuesta” (terminology)

In Spanish clinical catalogs this usually refers to **sustained-attention response tasks** generally (sometimes **CSAT-R** or other CPT-style tools). **Do not assume** one Spanish label maps 1∶1 to **Robertson SART** unless the stimulus rules (go/no-go mapping) match your implementation.

### 8.5 Ibero-American normative stack (attention-adjacent, Spanish)

The **NeuroRehabilitation** multi-paper project (*Commonly used Neuropsychological Tests for Spanish Speakers: Normative Data from Latin America*, ~2015) provides **Latin American Spanish-speaking** norms for tools such as **Trail Making Test**, **Brief Test of Attention (BTA)**, **Stroop**, etc. Anchor example (verified via PubMed MCP): Rivera et al., **Brief Test of Attention** norms — PMID [26639928](https://pubmed.ncbi.nlm.nih.gov/26639928/) · DOI [10.3233/NRE-151283](https://doi.org/10.3233/NRE-151283). Additional instruments in the same programme use sibling DOIs under `10.3233/NRE-15128*`. These are **not** SART/CPT but strengthen a **battery** interpretation.

**Colombian university sample (attention battery):** Standardization of **TMT-A/B + PASAT** in Manizales — CES Psicología ([DOI 10.21615/cesp.12.1.2](https://doi.org/10.21615/cesp.12.1.2)); discusses scarcity of Colombian norms and cites Ardila–Rosselli historic Colombian work.

### 8.6 Concrete implementation checklist (this repo)

| Step | Action |
|------|--------|
| 1 | Keep **PVT** as primary **adult** vigilance anchor (`/research/pvt`, `app/pvt_core.py`). |
| 2 | If adding **SART-like** web task, implement **fixed timing + withholding rule** identical to published SART; store **commission/omission/mean RT/SD RT** per session. |
| 3 | For **CPT-class** screening, prefer **documented** stimulus parameters or licensed software if clinical claims matter; otherwise label **“research CPT analogue.”** |
| 4 | Join tables: **`session_date` ↔ `garmin_daily_metrics.metric_date`** (+ optional lag +1 day for “night before → next day test”). |
| 5 | Statistics: same as §5 (correlation + FDR + report **n**); no claim of “validation of Garmin sleep” — only **concordance** with cognition. |
| 6 | Colombia deployment: plan a **local norm pilot** (n≥100 per age band) if clinical cutoffs are needed; until then use **within-person baselines** and literature ranges. |

### 8.7 References cited in §8 (quick list, with DOIs)

- SART parallel form — PMID [37210673](https://pubmed.ncbi.nlm.nih.gov/37210673/) · DOI [10.1080/23279095.2023.2213792](https://doi.org/10.1080/23279095.2023.2213792); SART TBI critique — PMID [16682059](https://pubmed.ncbi.nlm.nih.gov/16682059/) · DOI [10.1016/j.neuropsychologia.2006.02.012](https://doi.org/10.1016/j.neuropsychologia.2006.02.012).  
- PVT vs SART fatigue — PMID [35959037](https://pubmed.ncbi.nlm.nih.gov/35959037/) · DOI [10.3389/fpsyg.2022.925157](https://doi.org/10.3389/fpsyg.2022.925157).  
- CSAT-R empirical (Spanish context, incl. Colombia collaborator) — DOI [10.6018/analesps.477731](https://doi.org/10.6018/analesps.477731).  
- Conners CPT Brazil vs US — ERIC [EJ793561](https://eric.ed.gov/?id=EJ793561); journal DOI [10.1177/1087054707299412](https://doi.org/10.1177/1087054707299412).  
- Conners CPT Brazilian adolescents (12–17) — DOI [10.3922/j.psns.2013.1.11](https://doi.org/10.3922/j.psns.2013.1.11).  
- Conners CPT Chile (Spanish) — DOI [10.4067/S0718-48082017000300283](https://doi.org/10.4067/S0718-48082017000300283).  
- PennCNB-cv Spanish adolescents — PMID [39432534](https://pubmed.ncbi.nlm.nih.gov/39432534/) · DOI [10.1002/mpr.2035](https://doi.org/10.1002/mpr.2035) · PMC [PMC11493150](https://pmc.ncbi.nlm.nih.gov/articles/PMC11493150/).  
- BIS-15S Colombia — PMID [21152412](https://pubmed.ncbi.nlm.nih.gov/21152412/) · DOI [10.1016/s0034-7450(14)60239-0](https://doi.org/10.1016/s0034-7450(14)60239-0).  
- BTA Latin American norms (example paper from NeuroRehabilitation programme) — PMID [26639928](https://pubmed.ncbi.nlm.nih.gov/26639928/) · DOI [10.3233/NRE-151283](https://doi.org/10.3233/NRE-151283).  
- TMT/PASAT Manizales — DOI [10.21615/cesp.12.1.2](https://doi.org/10.21615/cesp.12.1.2).  

### 8.8 Open-source implementation stack (aligned with this repo)

**Goal:** Ship **research-grade** SART-like and CPT-*analogue* tasks without claiming equivalence to proprietary **Conners CPT-II** norms or commercial **CSAT-R** scoring. Useful outcomes for Mission Control mirror **PVT**: trial-level JSON → canonical Python scoring → SQLite via FastAPI → join with **`user_id` + session date** and Garmin rows.

| Layer | Recommendation | Notes |
|--------|------------------|--------|
| **Browser UI** | Extend the existing **React** pattern (`frontend/src/components/pvt/pvt-test.tsx`): `performance.now()`, `requestAnimationFrame` for stimulus onset, same timing caveats as `docs/PVT.md` (Anwyl-Irvine et al.). | Keeps one UX stack; reuse Card/Button patterns and session POST shape. |
| **Experiment framework (optional)** | **[jsPsych](https://www.jspsych.org/)** (MIT) for rapid iteration on go/no-go or CPT-like timelines; export trials JSON and feed the same scorer. | Good when you want plugins (keyboard, fullscreen, timeline) without hand-rolling state machines. |
| **Desktop / lab timing** | **PsychoPy** — already wired for PVT (`app/pvt_desktop.py` posts to `/api/pvt/sessions`). | Same pattern for SART: deterministic ISI/stim logs, POST to a new `/api/cognition/sessions` if added. |
| **Server truth** | New module e.g. `app/sart_core.py` / `app/cpt_analogue_core.py` parallel to **`app/pvt_core.py`**; FastAPI router parallel to **`api/pvt_endpoints.py`**. | Single source of truth for commission/omission/mean RT/SD RT; TS mirror only for live feedback if needed. |
| **What not to expect** | No OSS library reproduces **Conners** stimulus logic + proprietary norms; label UI **“CPT analogue (research)”** unless you license MHS tools. | **CSAT-R** is commercial (Hogrefe/TEA); cite Servera et al. for validity context only. |

### 8.9 Citation verification log

Identifiers below were cross-checked **April 2026** using the workspace **PubMed MCP** (`user-paper-search`: `search_pubmed`) and publisher/ERIC landing pages. Titles matched the abstracts returned by PubMed for PMIDs; DOIs matched those returned for PubMed records or resolved on publisher sites.

| Identifier | Resolves to |
|------------|-------------|
| PMID 37210673 | Lanssens et al., SART gratings parallel form (DOI 10.1080/23279095.2023.2213792). |
| PMID 16682059 | Whyte et al., SART after TBI (*Neuropsychologia*; DOI 10.1016/j.neuropsychologia.2006.02.012). |
| PMID 35959037 | Passi et al., PVT vs SART military fatigue (*Front. Psychol.*; DOI 10.3389/fpsyg.2022.925157). |
| PMID 21152412 | Orozco-Cabal et al., BIS-15S Colombia. |
| PMID 26639928 | Rivera et al., BTA Latin American norms (*NeuroRehabilitation*; DOI 10.3233/NRE-151283). |
| PMID 39432534 | Fernández-García et al., PennCNB-cv Spanish validation (DOI 10.1002/mpr.2035; full text PMC11493150). |
| ERIC EJ793561 | Miranda et al., Brazil vs US CPT-II (*J. Atten. Disord.* 2008). |
| DOI 10.3922/j.psns.2013.1.11 | Miranda et al., Brazilian adolescents CCPT II (*Psychol. Neurosci.* 2013). |
| DOI 10.4067/S0718-48082017000300283 | Chile Conners CPT ADHD vs controls (*Terapia Psicol.* 2017). |
| DOI 10.6018/analesps.477731 | Servera et al., CSAT-R (*Anales de Psicología* — journal ISSN resolver). |

**Note:** Regional portals (SciELO HTML, Redalyc) may throttle non-browser clients; prefer **DOI** or **PubMed/PMC** URLs for durable citations.

