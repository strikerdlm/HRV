# Figure Plan — OPI Methodology Paper

Author: Dr Diego Malpica MD

This file specifies the four figures that support the OPI methodology manuscript (`manuscript/draft/opi_main_manuscript.md`). Figures 1 and 4 can be adapted from existing SVG assets under `manuscript/figures/`; Figures 2 and 3 are new and require generation from the taxonomy and the worked-example outputs respectively.

Target venue: **Applied Ergonomics** (Elsevier). Figure file formats to prepare for submission: PDF + EPS (vector) and TIFF 300 dpi (raster). Colour figures accepted at no extra charge online; greyscale-friendly palettes preferred.

---

## Figure 1 — OPI conceptual schematic

**Purpose:** Orient the reader to the four-component weighted fusion at the heart of the OPI framework, with visible inputs, per-task weights, penalty terms, and the output readiness-category band.

**Panels:** single panel.

**Content blocks (left → right, top → bottom):**

1. **Inputs** (left): RR-interval stream → HRV engine (RMSSD, LF/HF, SampEn, DFA-α1, stress index); sleep/activity history → SAFTE reservoir; environmental context (optional).
2. **Components** (centre-left):
   - HRV_recovery (from RMSSD + SDNN + baseline deviation)
   - Autonomic_reserve (from SampEn + DFA-α1)
   - Attention_capacity (UAS only; from entropy + DFA-α1)
   - SAFTE_eff (from reservoir + circadian term)
   - Vigilance_adj (UAS only; from Warm decay model)
3. **Weights and penalties** (centre-right): per-task weight profile selector `{w1, w2, w3, w4}`; Task_mod multiplier on SAFTE_eff; Stress_penalty; Task_complexity_penalty; Latency_penalty; Multi_vehicle_penalty.
4. **Output** (right): OPI composite score → readiness-category mapping (GO / GO-Monitor / CAUTION / NO-GO).

**Caption (draft, ~70 words):** Operational Performance Indicator (OPI) conceptual schematic. The framework combines four biomathematical components — SAFTE-style fatigue effectiveness, HRV-derived autonomic markers, Multiple Resource Theory-derived cognitive-load modifiers, and operational modifiers — into a per-task weighted composite readiness score. UAS and teleoperator task categories add a Warm-type vigilance-decrement term and a Chen-type control-latency penalty. Task-specific weight profiles and thresholds are given in Tables 1-3.

**Source material:** Adapt `manuscript/figures/figure1_platform_architecture.svg` — replace current "platform architecture" layer labels with OPI-component labels and add the output readiness-category block.

---

## Figure 2 — Task taxonomy and dominant autonomic signatures

**Purpose:** Show the full seventeen-category task taxonomy in a single glance, with associated dominant HRV signatures under high workload, enabling rapid task-to-signature look-up during reading.

**Panels:** two-panel vertical stack (manned aviation top, UAS bottom).

**Content blocks:**

1. **Top panel — manned aviation (10 categories):**
   - IMC · NVD · HMD · ATC · Emergency (critical) · Emergency (non-critical) · Test pilot · Carrier landing · Weapons delivery · New-platform
   - For each category: iconic marker plus dominant HRV signature text (e.g., "IMC — LF/HF↑, RMSSD↓"; "Carrier — RMSSD>35 ms target, SD1/SD2 ~0.4-0.6").
2. **Bottom panel — UAS / teleoperator (7 categories):**
   - ISR · Strike · SAR/CSAR · Swarm supervisory · Contested · Ground teleop · Subsea
   - For each category: dominant signature plus vigilance-decay annotation (e.g., "Low-event ISR — λ = 0.12 h⁻¹, Vmin = 65").

**Style:** small-multiples layout, each cell the same size, colour-coded by dominant signature family (LF/HF-dominant vs. RMSSD-dominant vs. complexity-dominant).

**Caption (draft, ~90 words):** Task taxonomy covered by the OPI framework with the dominant heart-rate-variability signature expected under high workload in each category. Manned-aviation categories (top) are organised left-to-right from cockpit-procedural tasks to precision-motor-control tasks to novel-platform tasks. UAS categories (bottom) are organised by dominant demand: vigilance-limited, decision-accuracy-limited, multi-task-limited, and latency-limited. Full HRV signatures, failure modes, and per-task OPI weights are given in Tables 1-2.

**Source material:** New figure. Generate from `manuscript/tables/opi_task_taxonomy.md`. SVG or matplotlib small-multiples layout.

---

## Figure 3 — Illustrative worked example

**Purpose:** Show that the same physiological input (one 128-min HRV recording) yields substantively different OPI composite outputs when the active task category changes, demonstrating the task-calibration design intent.

**Panels:** three-panel horizontal row (one per task hypothesis).

**Content:**

1. **Left panel — CAT II ILS approach (category 1):** OPI composite time series (blue line) over the 128-min recording duration, with horizontal dashed lines at the four readiness-category thresholds (85, 70, 55). Shaded bands behind the line to indicate the readiness category in each window.
2. **Centre panel — UAS ISR sortie (category 11):** Same format; the second x-axis shows simulated time-on-task starting at 0 h and reaching ≈2 h by the end of the recording, capturing the vigilance-decay contribution.
3. **Right panel — Carrier recovery (category 8):** Same format; higher w2 on HRV_recovery produces visibly more short-term variability in the composite line.

**Annotations:** text box in each panel listing the weight profile used `{w1, w2, w3, (w4)}`; small inset subplot (optional) showing the per-component contribution stack for one representative window.

**Caption (draft, ~110 words):** Illustrative worked example of OPI framework instantiation across three task hypotheses computed from the same 128-minute HRV recording. Per-window OPI time series (blue) is shown against readiness-category thresholds (dashed horizontal lines) with shaded bands indicating the assigned category. The same physiological input produces systematically different composite outputs across the three task hypotheses, consistent with the Multiple Resource Theory-derived weight profiles (Table 2). This demonstration shows how a task-agnostic composite would collapse information that the OPI preserves. The worked example is a framework-instantiation illustration; it is not an empirical test and does not generalise beyond this single recording.

**Source material:** New figure. Generate via the script at `analysis/` (see Task #10 execution plan) — the script produces a JSON artifact and the figure PDF/SVG/PNG.

---

## Figure 4 — Reference-implementation architecture

**Purpose:** Show the reference implementation's delivery path from physiological inputs through the API orchestration to operational and research interfaces, making the OPI pathway explicit within the broader software stack.

**Panels:** single panel.

**Content blocks (bottom → top):**

1. **Data and sensor layer (bottom):** RR-interval stream, sleep/activity history, environmental feeds.
2. **Python analytic core:** `app/hrv_core.py`, `app/fatigue_calculator/safte_model.py`, `app/scheduling_core.py`, `app/frms.py`, `app/user_profile_tab.py`, `app/noaa_space.py`. Highlight the OPI pathway in colour.
3. **FastAPI orchestration:** `api/main.py`, `api/research_endpoints.py`.
4. **Delivery surfaces (top):** Next.js operational client, Next.js research client, (secondary) Streamlit entrypoints.
5. **Mirror arrow (right):** TypeScript SAFTE mirror `frontend/src/lib/safte-model.ts` for responsive client-side displays, explicitly labelled "architectural consistency, not independent model".

**Caption (draft, ~85 words):** Reference-implementation architecture. The OPI pathway is highlighted in colour across the four layers of the stack: sensor and input layer, Python analytic core, FastAPI orchestration, and delivery surfaces. The TypeScript client-side SAFTE mirror (right) reproduces the canonical Python implementation for responsive operational displays and is treated as architectural consistency rather than as an independent validation layer. Engineering verification tests covering the pathway are listed in Table 5.

**Source material:** Adapt `manuscript/figures/figure1_platform_architecture.svg` or `figure3_research_to_operations_coupling.svg`. Relabel layers, highlight OPI pathway, add the mirror-arrow annotation.

---

## Retired figures (from prior framing)

The prior systems-and-software framing planned four figures (platform architecture, end-to-end workflow, research-to-operations coupling, verification coverage map). Of these:

- Figure 1 (`figure1_platform_architecture.svg`) → adapted as the new Figure 4
- Figure 2 (`figure2_end_to_end_workflow.svg`) → retired; workflow information now distributed across the new Figure 1 (conceptual) and Figure 4 (architecture)
- Figure 3 (`figure3_research_to_operations_coupling.svg`) → retired; the research-to-operations narrative is now backgrounded given the methodology-paper framing
- Figure 4 (`figure4_verification_coverage_map.svg`) → retained in repository as Supplementary Figure S1, supporting Table 5

The four retained SVG files remain in `manuscript/figures/` and do not need to be deleted — they serve as source material for adaptation and as supplementary material.

---

## Export and submission preparation

Before Applied Ergonomics submission:

1. Regenerate Figures 1-4 at publication quality: PDF (vector) + EPS (vector) + TIFF 300 dpi (raster).
2. Verify figures render legibly at single-column (≈8.4 cm) and double-column (≈17.6 cm) widths.
3. Verify colourblind-safe palette; greyscale conversion should remain readable.
4. Confirm font sizes ≥ 8 pt at final print size.
5. Update captions per Applied Ergonomics house style once the journal template is imported.

## Cross-reference

- Draft manuscript referring to these figures: `manuscript/draft/opi_main_manuscript.md`
- Tables that supply the numerical content for Figures 2 and 3: `manuscript/tables/opi_task_taxonomy.md`, `manuscript/tables/opi_weight_profiles.md`, `manuscript/tables/opi_vigilance_latency_models.md`
- Worked-example script to produce Figure 3 data: to be added under `analysis/` during Task #10 execution.
