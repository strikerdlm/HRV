# Sleep module — platform guide

**Author:** Dr Diego Malpica MD
**Status:** active (added 2026-04-21)

## What it is

The Sleep module analyses Garmin-backed nightly sleep metrics for aerospace operators and surfaces them through three new FastAPI endpoints, a research dashboard at `/research/sleep`, and an operational pre-flight gate at `/scheduling/sleep`. The scope is intentionally bounded to **Pending.md §4 Tier A** (metrics available in Garmin daily summaries) with explicit exclusion of Tier B (hypnograms / arousals / fragmentation) and Tier C (apnea diagnosis).

The central integration point is the shared `garmin_daily_metrics` table (`app/user_database.py`); the canonical scoring module is `app/sleep_core.py`; and every visualisation carries the **"Exploratory — Garmin wellness device; not PSG-diagnostic"** disclosure per the Lee 2025 and Schyvens 2024 consumer-wearable validation meta-analyses.

## Scope

**In scope (Tier A):**

- Sleep duration, efficiency, and score aggregates over configurable windows
- Stage-balance derivations: deep/REM/light/awake percentages, deep+REM fraction, deep:REM ratio
- Cumulative sleep debt (7-night rolling; deficit vs typical target)
- Sleep Regularity Index (Lunsford-Avery 2018): epoch-match probability between consecutive 24-hour cycles
- Bedtime / waketime / midpoint standard deviations
- Low-SpO₂ night flagging as a **screening** proxy (never AHI / apnea)
- Pairwise Pearson or Spearman correlations with Benjamini-Hochberg FDR adjustment across the eight Tier A pairs
- Operational readiness gate (GO / GO_MONITOR / CAUTION / NO_GO)

**Out of scope for this module:**

- Hypnograms, arousal indices, fragmentation metrics, WASO, sleep latency — require Tier B per-epoch ingestion
- Apnea / SDB diagnosis, AHI or RDI calculation — not available from consumer summaries
- Any claim of PSG equivalence — bounded by Lee 2025 / Schyvens 2024

## Validated metrics (every reference DOI-verified)

| Metric family | Formula / definition | Primary source |
|---|---|---|
| Sleep debt (7d) | Σᵢ max(0, target − observedᵢ) over last 7 nights; deficit vs 7.5 h default | Operational convention; Dinges 1997 dose-response evidence |
| Sleep Regularity Index (SRI) | 2·(Pₘₐₜcₕ − 0.5)·100, where Pₘₐₜcₕ = probability of same state (asleep / awake) at a given minute on two consecutive days; 5-min epochs | Lunsford-Avery et al. 2018 — DOI 10.1038/s41598-018-32402-5 |
| Bedtime / waketime SD | Population std-dev of bedtime (resp. waketime) across nights, in minutes | Pending.md §4 — regularity proxies |
| Stage balance | Per-stage minutes ÷ total sleep time; deep+REM proportion is the salient operational composite | Garmin sleep summary |
| Low-SpO₂ screening | Flag nights where average SpO₂ < 92 %; gate bands NORMAL / MILD / ELEVATED / HIGH_FLAG by count over 7 nights | Balali 2025 (PMID 41953462) context; strictly screening |
| Correlation engine | Pearson r (SciPy when available, pure-Python fallback) with two-sided p and Benjamini-Hochberg FDR-q across the Tier A pair set; underpowered flag when n_nights < 14 | Pending.md §5 |

## Administration surfaces

### FastAPI sleep endpoints (primary — consumed by both dashboards)

Mounted under `/api/research` via `api/research_endpoints.py`:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/research/garmin/sleep-summary/{user_id}` | Aggregate: debt, regularity, SpO₂ screening, readiness, latest-night stage balance |
| `GET` | `/api/research/garmin/sleep-correlations/{user_id}` | Tier A pairwise correlations with r, p, FDR-q, n_nights |
| `GET` | `/api/research/garmin/sleep-debt-trend/{user_id}` | Per-night duration, deficit, and 7-night rolling debt |

All three read from `garmin_daily_metrics` via `UserDatabase.get_garmin_daily_metrics(user_id, days)`.

### Research dashboard (Next.js — `/research/sleep`)

Comprehensive plot-first dashboard assembling the Tier A analysis:

- **Headline KPIs:** 30-day mean duration, 7-night debt, SRI, low-SpO₂ nights
- **Operational readiness banner** from the gate logic
- **Sleep duration trend:** nightly bars + 7-day rolling mean + 7-9 h target band + 5 h hard-floor line
- **Sleep-debt curve:** 7-night rolling debt area with 4 h CAUTION and 8 h NO-GO markLines
- **Stage balance:** stacked bar per night + latest-night pie
- **Regularity strip:** bedtime / waketime per night + SRI and time-SD breakdown
- **Correlation matrix heatmap:** Tier A × HRV RMSSD with FDR-q tooltips
- **Six per-pair scatter plots** with OLS fit and r/p/q captions
- **Evidence map card** with tooltipped PubMed / DOI chips for every theme

### Operational sleep gate (Next.js — `/scheduling/sleep`)

Pre-flight / shift-check view mirroring the operational PVT gate:

- Four-band decision banner (GO / GO_MONITOR / CAUTION / NO_GO) from `operational_sleep_gate`
- Four KPIs colour-coded to gate thresholds
- Debt gauge (segmented by CAUTION / NO_GO bands)
- Last-7-night duration bar with accept and floor markLines
- SpO₂ screening overview (screening language only, never clinical)
- 30-night sleep-debt curve
- Decision-detail table
- Explicit Garmin-vs-PSG disclosure card

## Backend module: `app/sleep_core.py`

Single source of truth for scoring and gate logic. Tests: `tests/test_sleep_core.py` — 27 tests covering stage balance, sleep debt scaling, SRI behaviour on identical / alternating schedules, SpO₂ band transitions, operational gate escalation, correlation + BH FDR monotonicity, and empty / partial-data edge cases. All tests pass.

Use this module from any new code path that needs sleep metrics. Do not re-implement scoring elsewhere.

## Operational gate logic

```
IF last_night < 5 h            → NO_GO
ELIF last_night < 6 h          → CAUTION
ELIF 7-night debt ≥ 8 h        → NO_GO
ELIF 7-night debt in [4, 8) h  → CAUTION
ELIF 7-night debt ≥ 2 h        → GO_MONITOR
IF SRI < 40 %                  → escalate to CAUTION
IF ≥4 low-SpO₂ nights in 7     → escalate to CAUTION (never NO_GO alone)
IF ≥2 low-SpO₂ nights in 7     → escalate to GO_MONITOR
ELSE                           → GO
```

All thresholds live in `app/sleep_core.py` module constants and mirror into `frontend/src/lib/sleep-metrics.ts` `SLEEP_THRESHOLDS`.

## Language rules (enforce in any UI extension)

1. **No clinical sleep-disorder classification.** Never use AHI, RDI, "sleep apnea", "obstructive sleep apnea", or "sleep-disordered breathing" as a diagnosis. SpO₂-based outputs are always prefixed with "screening proxy" or "screening only".
2. **Wearable caveat everywhere.** Every chart carries "Exploratory — Garmin wellness device; not PSG-diagnostic" or equivalent.
3. **Underpowered flag.** Any correlation computed on n_nights < 14 is flagged via the `note` field and surfaced in the UI.
4. **Garmin vs PSG disclosure.** The research page evidence card and the operational disclosure card cite Lee 2025 (DOI 10.5664/jcsm.11460) and Schyvens 2024 (DOI 10.2196/52192) explicitly.

## Integration with the readiness pipeline

The sleep-debt output feeds downstream readiness aggregators alongside the existing SAFTE effectiveness and `pvt_lapses_3min` inputs. A sleep NO-GO does not override existing gate layers; it adds a new independent layer to the fused readiness decision. See `app/scheduling_core.py` for the combined `IHPI` computation (to be extended in a follow-up when Diego decides how sleep debt integrates weight-wise).

## Validation references (all DOIs Crossref / PubMed verified)

- Lunsford-Avery JR, Engelhard MM, Navar AM, Kollins SH. (2018). Validation of the Sleep Regularity Index in Older Adults and Associations with Cardiometabolic Risk. *Scientific Reports* 8. [10.1038/s41598-018-32402-5](https://doi.org/10.1038/s41598-018-32402-5). PMID [30242174](https://pubmed.ncbi.nlm.nih.gov/30242174/).
- Lee YJ, Lee JY, Cho JH, Kang YJ, Choi JH. (2025). Performance of consumer wrist-worn sleep tracking devices compared to polysomnography: a meta-analysis. *J Clin Sleep Med* 21(3):573–582. [10.5664/jcsm.11460](https://doi.org/10.5664/jcsm.11460). PMID [39484805](https://pubmed.ncbi.nlm.nih.gov/39484805/).
- Schyvens AM, Van Oost NC, Aerts JM, Masci F, Peters B, Neven A, Dirix H, Wets G, Ross V, Verbraecken J. (2024). Accuracy of Fitbit Charge 4, Garmin Vivosmart 4, and WHOOP Versus Polysomnography: Systematic Review. [10.2196/52192](https://doi.org/10.2196/52192). PMID [38557808](https://pubmed.ncbi.nlm.nih.gov/38557808/).
- Liao D, et al. Sleep-disordered breathing in children — sleep stage-specific autonomic modulation. *J Sleep Res.* PMID [20337904](https://pubmed.ncbi.nlm.nih.gov/20337904/).
- Kesek M, et al. HRV during sleep and sleep apnoea — population women. PMID [19453563](https://pubmed.ncbi.nlm.nih.gov/19453563/).
- Zhang S, et al. Sleep deprivation and HRV — systematic review & meta-analysis. PMID [40895095](https://pubmed.ncbi.nlm.nih.gov/40895095/).
- Zhu L, et al. Circadian types and 24-hour HRV — fragmented sleep patterns. PMID [40768960](https://pubmed.ncbi.nlm.nih.gov/40768960/).
- Balali P, et al. Wake HRV vs sleep apnea indicators / SpO₂ (clinical + altitude cohort). PMID [41953462](https://pubmed.ncbi.nlm.nih.gov/41953462/).
- Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology. (1996). Heart rate variability: standards of measurement, physiological interpretation and clinical use. *Circulation* 93(5):1043–1065. [10.1161/01.cir.93.5.1043](https://doi.org/10.1161/01.cir.93.5.1043). PMID [8598068](https://pubmed.ncbi.nlm.nih.gov/8598068/).

## Future work (Tier B / Tier C)

- **Tier B — hypnogram ingestion.** Add a `garmin_sleep_epochs` table, ingest per-epoch stage data from Garmin FIT / research exports, and build arousal / fragmentation metrics.
- **Tier C — expanded screening proxy.** Compose SpO₂ patterns with nightly respiration-rate variability and resting HR patterns into a documented screening composite. Still no clinical claim.
- **Cognition join.** Use the existing `/research/pvt` session dates to join next-day attentional performance to each night's sleep metrics. See Pending.md §8 for the PVT and (potential) SART / CPT-analogue integration path.
- **IHPI weight integration.** Decide a weighting scheme for the sleep-debt subscore alongside SAFTE and PVT in `app/scheduling_core.py`.
