# Table 2 — OPI Component Weight Profiles and Formulation

Author: Dr Diego Malpica MD

This table formalises the Operational Performance Indicator (OPI) composite and enumerates the per-task weight profiles for the seventeen task categories defined in Table 1. Weights are theory-derived from the HF literature cited in the column "Rationale" and in the derivation document `analysis/operational_performance_indicators_research.md`. Empirical calibration of the weights against field performance outcomes is future work.

## OPI formulation

### Manned-aviation tasks (categories 1-10)

```
OPI_task = w1 · SAFTE_eff · Task_mod
         + w2 · HRV_recovery
         + w3 · Autonomic_reserve
         − Stress_penalty
         − Task_complexity_penalty
```

where
- `SAFTE_eff ∈ [0, 100]` — SAFTE/FAST-style reservoir cognitive-effectiveness estimate (Hursh 2004)
- `Task_mod ∈ [0.70, 1.00]` — task-complexity modifier (Table: task-complexity modifiers below)
- `HRV_recovery ∈ [0, 100]` — normalised index of short-term vagal recovery (derived from RMSSD, SDNN, and baseline deviation)
- `Autonomic_reserve ∈ [0, 100]` — normalised index of autonomic regulatory capacity (derived from HRV complexity and entropy metrics)
- `Stress_penalty = max(0, stress_index − 150) · 0.15` — penalty beyond Baevsky stress-index threshold
- `Task_complexity_penalty = 5 · (1 − Task_mod)` — explicit penalty for compound high-complexity conditions
- `w1 + w2 + w3 = 1.00` (normalisation constraint)

### UAS / teleoperator tasks (categories 11-17)

```
OPI_UAS = w1 · SAFTE_eff
        + w2 · Vigilance_adj
        + w3 · HRV_recovery
        + w4 · Attention_capacity
        − Latency_penalty
        − Multi_vehicle_penalty
```

where
- `Vigilance_adj = Vigilance_capacity(t)` per Warm 2008 decrement model (Table 3)
- `Attention_capacity ∈ [0, 100]` — normalised index combining SampEn and DFA-α1 as proxies for cognitive reserve
- `Latency_penalty = 0.5 · ln(1 + latency_ms / 100)` per Chen 2007 teleoperator model
- `Multi_vehicle_penalty = 3 · (n_vehicles − 1)` for supervisory-control tasks
- `w1 + w2 + w3 + w4 = 1.00` (normalisation constraint)

## Per-task component weight profiles

### Manned aviation (w1 SAFTE / w2 HRV-recovery / w3 autonomic-reserve)

| # | Task category | w1 (SAFTE) | w2 (HRV-recov) | w3 (Auto-res) | Rationale |
| --- | --- | --- | --- | --- | --- |
| 1 | IMC flying | 0.55 | 0.25 | 0.20 | Sustained cognitive load; fatigue-sensitive per Morris 2020 and Roscoe 1992 |
| 2 | NVD operations | 0.50 | 0.25 | 0.25 | Visual + cognitive fatigue; circadian-trough dominant; Crowley 1991; Rash 2009 |
| 3 | HMD flying | 0.50 | 0.30 | 0.20 | High information-processing rate; dual-task interference per Wickens 2008 |
| 4 | High-density ATC | 0.45 | 0.30 | 0.25 | Communication-stress load; Brookings 1996; Vogt 2006 |
| 5 | Emergency (critical) | 0.40 | 0.35 | 0.25 | Acute stress tolerance dominates; recovery post-eustress important; Driskell 1996 |
| 6 | Emergency (non-critical) | 0.50 | 0.25 | 0.25 | Moderate stress; procedure execution; mixed SAFTE + HRV |
| 7 | Test pilot | 0.45 | 0.30 | 0.25 | Uncertainty tolerance; self-selected baseline; Carretta 2011 |
| 8 | Carrier landing | 0.50 | 0.30 | 0.20 | Precision motor control; fine-motor markers drive component weighting; Bolia 2007 |
| 9 | Weapons delivery | 0.50 | 0.25 | 0.25 | Sustained attention + transient execution stress; Endsley 1995; Schreiber 2004 |
| 10 | New platform testing | 0.55 | 0.25 | 0.20 | Learning load; mode-confusion risk; Casner 2014 |

Normalisation check: each row sums to 1.00.

### UAS / teleoperator (w1 SAFTE / w2 vigilance / w3 HRV-recov / w4 attention-capacity)

| # | Task category | w1 (SAFTE) | w2 (Vigilance) | w3 (HRV-recov) | w4 (Attention) | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| 11 | ISR (high-event) | 0.35 | 0.30 | 0.15 | 0.20 | Sustained vigilance + discrete-event workload; Warm 2008 |
| 12 | Strike | 0.30 | 0.15 | 0.25 | 0.30 | Decision accuracy under threat; entropy-based attention reserve critical |
| 13 | SAR / CSAR | 0.30 | 0.20 | 0.25 | 0.25 | Multi-task coordination; dynamic SA |
| 14 | Autonomous-swarm supervisory | 0.30 | 0.25 | 0.15 | 0.30 | Exception-handling over sustained supervisory baseline |
| 15 | Contested environment | 0.30 | 0.20 | 0.25 | 0.25 | Dual-task threat monitoring + mission execution |
| 16 | Ground-robot teleoperation | 0.35 | 0.15 | 0.20 | 0.30 | Spatial transformation + mental rotation |
| 17 | Subsea / long-latency | 0.30 | 0.20 | 0.25 | 0.25 | Latency penalty dominates; attention and HRV recovery both load |

Normalisation check: each row sums to 1.00. For UAS rows, the latency penalty and multi-vehicle penalty are applied additively after the weighted sum.

## Task-complexity modifiers (Task_mod)

Applied multiplicatively to SAFTE_eff in the manned-aviation formula. Ranges are operational defaults; local empirical calibration is recommended before field use.

| Factor | Range | Application |
| --- | --- | --- |
| IMC approach category | 0.95 (CAT I) / 0.90 (CAT II) / 0.85 (CAT III) | Lower minima imply higher instrument demand and smaller safety margins |
| NVD terrain type | 0.90 (complex mountainous) to 1.00 (flat) | Terrain interpretation load |
| ATC traffic density | 0.85 (peak) to 1.00 (low) | Communication tempo and aircraft-tracking count |
| Emergency severity | 0.70 (critical multi-system) to 0.95 (abnormal single-system) | Combined time pressure and consequence |
| Platform familiarity | 0.80 (novel) to 1.00 (experienced) | Learning-curve effect per Casner 2014 |
| Time pressure | 0.85 (compressed) to 1.00 (normal) | Decision-latency constraint |

Compound modifiers multiply: `Task_mod = ∏ factor_i` bounded to `[0.50, 1.00]`.

## Stress penalty

`Stress_penalty = max(0, stress_index − 150) · 0.15`

Applied across all seventeen task categories. The 150 threshold follows operational interpretations of the Baevsky stress index reported by Shaffer & Ginsberg 2017 and operational military reviews. Penalty coefficient `0.15` chosen so that a stress_index of 300 (high acute load) yields a 22.5-point deduction, consistent with the readiness-category band widths in Table 1.

## Learning-curve modifier (new-platform testing only)

Applied to `OPI_task` after the weighted-sum step for category 10 only:

| Experience level | OPI adjustment | Oversight level |
| --- | --- | --- |
| Initial training | − 20 | Increased supervision |
| Basic proficiency | − 10 | Standard oversight |
| Mission ready | 0 (baseline) | Normal operations |
| Instructor qualified | + 5 | Reduced supervision |

Bounded such that the post-adjustment OPI remains in `[0, 100]`.

## Illustrative calculation (IMC CAT II approach)

Inputs:

- SAFTE_eff = 82
- HRV_recovery = 65
- Autonomic_reserve = 52
- Stress index = 145 (below threshold)
- Task = CAT II ILS approach (Task_mod = 0.90)

Computation:

```
OPI_IMC = 0.55 · 82 · 0.90 + 0.25 · 65 + 0.20 · 52
        = 40.59 + 16.25 + 10.40
        = 67.24

Stress_penalty = max(0, 145 − 150) · 0.15 = 0
Task_complexity_penalty = 5 · (1 − 0.90) = 0.50

OPI_IMC_final = 67.24 − 0 − 0.50 = 66.74
```

Readiness category: **CAUTION** (55-69) — "proceed with mission modification or enhanced monitoring".

## Implementation anchors

- Canonical Python implementation: `app/scheduling_core.py`, `app/frms.py`, `app/frms_v2.py`
- SAFTE component: `app/fatigue_calculator/safte_model.py`
- HRV components feeding HRV_recovery, Autonomic_reserve, Attention_capacity: `app/hrv_core.py`
- TypeScript client mirror (SAFTE only): `frontend/src/lib/safte-model.ts`

## Cross-reference

- Task definitions and expected HRV signatures: `manuscript/tables/opi_task_taxonomy.md`
- Vigilance-decrement and latency-penalty model parameters: `manuscript/tables/opi_vigilance_latency_models.md`
- Full derivation and citations: `analysis/operational_performance_indicators_research.md`
