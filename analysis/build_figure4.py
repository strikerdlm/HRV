"""Build Figure 4 — Reference-implementation architecture.

Clean four-layer stack for the OPI manuscript. Follows `.cursor/rules/plots.mdc`:
single-line title, SCIENTIFIC_COLORS palette, minimal ornament, flat typography.

Layers (bottom → top):
    L1 — Input instrumentation (research-grade wearables for validation)
    L2 — Python analytic core (single-source-of-truth scoring modules)
    L3 — FastAPI orchestration (REST endpoints for clients and studies)
    L4 — Next.js delivery surfaces (research + operational)

No consumer-wearable, space-weather, or legacy-UI components are depicted.
The instrumentation layer foregrounds the two research-grade sensors used
in the upcoming Antarctic validation:
    * ActiGraph wGT3X-BT wrist accelerometer (sleep / activity ground truth)
    * Polar H10 chest-strap ECG (RR-interval gold standard among wearables)
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


# ---------------------------------------------------------------------------
# Palette — muted, publication-neutral, greyscale-readable
# ---------------------------------------------------------------------------
COL_SENSOR = "#eaf2fb"   # very pale blue — inputs
COL_CORE = "#c6dbef"     # soft blue — analytic core
COL_CORE_HI = "#f8d36b"  # warm gold — OPI-pathway highlight
COL_API = "#9ecae1"      # medium blue — API
COL_DELIVERY = "#6baed6" # saturated blue — delivery surfaces
EDGE = "#2c3e50"         # deep slate for borders
EDGE_HI = "#b8732f"      # warm umber for highlighted border
TEXT = "#1a1a1a"
MUTED = "#5a6570"


def box(ax, x, y, w, h, label, face=COL_SENSOR,
        fontsize=8.5, weight="normal", ec=EDGE, lw=0.6, ls="-"):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.012,rounding_size=0.05",
        linewidth=lw, edgecolor=ec, facecolor=face,
        linestyle=ls,
    ))
    ax.text(x + w / 2, y + h / 2, label,
            ha="center", va="center", fontsize=fontsize, color=TEXT,
            weight=weight)


def arrow_up(ax, x, y0, y1, colour=EDGE, lw=0.6, mutation=8):
    ax.add_patch(FancyArrowPatch(
        (x, y0), (x, y1),
        arrowstyle="-|>", mutation_scale=mutation,
        linewidth=lw, color=colour,
    ))


def layer_band(ax, y_bottom, y_top, label, side_x=-0.25):
    """Left-side layer label, no background band to keep the figure clean."""
    ax.text(side_x, (y_bottom + y_top) / 2, label,
            ha="right", va="center",
            fontsize=9, color=MUTED, style="italic")


def build(out_base: Path) -> None:
    fig, ax = plt.subplots(figsize=(12.6, 7.0), dpi=300)
    ax.set_xlim(-1.2, 13.0)
    ax.set_ylim(0, 7.4)
    ax.axis("off")

    # =========================================================================
    # L1 — Input instrumentation
    # =========================================================================
    # Research-grade instrumentation for the forthcoming Antarctic validation
    # is called out explicitly. Two sensors + operator-level context.
    layer_band(ax, 0.25, 1.35, "L1 — Inputs")

    box(ax, 0.40, 0.25, 2.40, 1.10,
        "ActiGraph wGT3X-BT\n(wrist accelerometer)\nsleep · activity",
        face=COL_SENSOR, fontsize=8.2, weight="bold", lw=0.9)
    box(ax, 3.20, 0.25, 2.40, 1.10,
        "Polar H10\n(chest-strap ECG)\nRR intervals · HRV",
        face=COL_SENSOR, fontsize=8.2, weight="bold", lw=0.9)
    box(ax, 6.00, 0.25, 2.40, 1.10,
        "Sleep & schedule\ncontext\n(chronotype · duty)",
        face=COL_SENSOR, fontsize=8.2)
    box(ax, 8.80, 0.25, 2.40, 1.10,
        "Task context\n(category ·\ncomplexity · n_vehicles)",
        face=COL_SENSOR, fontsize=8.2)
    # Small non-critical optional input (kept intentionally thin)
    box(ax, 11.60, 0.25, 1.20, 1.10,
        "Operator\nprofile",
        face=COL_SENSOR, fontsize=8.2)

    # =========================================================================
    # L2 — Python analytic core (single-source-of-truth scoring)
    # =========================================================================
    layer_band(ax, 2.15, 3.60, "L2 — Python core")

    core_rows = [
        # y row 1: OPI-pathway modules (gold highlight)
        ("app/hrv_core.py\nHRV engine", 0.40, 2.15, True),
        ("app/fatigue_calculator/\nsafte_model.py", 3.00, 2.15, True),
        ("app/pvt_core.py\nPVT-B / 5 / 10", 5.60, 2.15, True),
        ("app/sleep_core.py\nSRI · debt · stage", 8.20, 2.15, True),
        # y row 2: fusion + longitudinal + integration (gold highlight)
        ("app/scheduling_core.py\napp/frms*.py\nreadiness fusion", 0.40, 3.60, True),
        ("app/trajectory_risk.py\nallostatic-load PSI", 3.00, 3.60, True),
        ("app/hydration_\nthermoregulation.py\nPhSI cold/heat", 5.60, 3.60, True),
        ("app/physiological_sms.py\nSMS risk matrix", 8.20, 3.60, True),
    ]
    for label, x, y, highlighted in core_rows:
        face = COL_CORE_HI if highlighted else COL_CORE
        ec = EDGE_HI if highlighted else EDGE
        lw = 1.0 if highlighted else 0.7
        box(ax, x, y, 2.40, 1.25, label,
            face=face, ec=ec, lw=lw, fontsize=7.8)

    # Persistence side-box (right column)
    box(ax, 10.80, 2.15, 2.00, 2.70,
        "app/user_database.py\napp/publication_\nexport.py\n\nSQLite persistence\n+ structured export",
        face=COL_CORE, fontsize=8.0, lw=0.7)

    # =========================================================================
    # L3 — FastAPI orchestration
    # =========================================================================
    layer_band(ax, 5.10, 5.95, "L3 — FastAPI")

    box(ax, 0.40, 5.15, 6.30, 0.80,
        "api/main.py  ·  /api/pvt/*  ·  /api/research/*  ·  /api/scheduling/*",
        face=COL_API, fontsize=9, weight="bold", lw=0.9)
    box(ax, 6.90, 5.15, 5.90, 0.80,
        "HRV · fatigue · PVT · sleep · readiness · OPI endpoints",
        face=COL_API, fontsize=9, weight="bold", lw=0.9)

    # =========================================================================
    # L4 — Next.js delivery surfaces
    # =========================================================================
    layer_band(ax, 6.25, 7.15, "L4 — Next.js")

    box(ax, 0.40, 6.30, 5.00, 0.90,
        "Research dashboard\nOPI decomposition · Tier-A correlations · trajectories",
        face=COL_DELIVERY, fontsize=9, weight="bold", lw=0.9)
    box(ax, 5.60, 6.30, 3.60, 0.90,
        "Operational gate\nPVT-B · sleep · fused IHPI",
        face=COL_DELIVERY, fontsize=9, weight="bold", lw=0.9)
    box(ax, 9.40, 6.30, 3.40, 0.90,
        "Worked-example &\nreproducibility console",
        face=COL_DELIVERY, fontsize=9, weight="bold", lw=0.9)

    # =========================================================================
    # Flow arrows — layer-to-layer, sparse and readable
    # =========================================================================
    for x_centre in (1.60, 4.40, 7.20, 10.00, 12.20):
        arrow_up(ax, x_centre, 1.38, 2.13, lw=0.55)

    # L2 (row 1) → L2 (row 2) — readiness fusion draws from the scoring row.
    # Represented as a single consolidated arrow up the middle.
    arrow_up(ax, 3.00, 3.43, 3.58, lw=0.55)
    arrow_up(ax, 5.60, 3.43, 3.58, lw=0.55)
    arrow_up(ax, 8.20, 3.43, 3.58, lw=0.55)
    # from row-1 HRV → row-2 fusion
    ax.add_patch(FancyArrowPatch(
        (1.60, 3.43), (1.60, 3.58),
        arrowstyle="-|>", mutation_scale=8,
        linewidth=0.55, color=EDGE,
    ))

    # L2 → L3
    for x_centre in (2.40, 4.80, 7.20, 9.60):
        arrow_up(ax, x_centre, 4.88, 5.13, lw=0.55)
    arrow_up(ax, 11.80, 4.88, 5.13, lw=0.55)

    # L3 → L4
    for x_src in (2.90, 7.40, 11.10):
        arrow_up(ax, x_src, 5.98, 6.28, lw=0.55)

    # =========================================================================
    # Title + minimal legend
    # =========================================================================
    ax.text(5.90, 7.28,
            "Figure 4 — Reference-implementation architecture",
            ha="center", fontsize=12, weight="bold", color=TEXT)

    # Legend: one short line below the figure
    ax.text(5.90, -0.05,
            "Gold-bordered modules compose the OPI fusion pathway. "
            "Antarctic validation instruments boxed in bold at L1.",
            ha="center", fontsize=8, color=MUTED, style="italic")

    plt.tight_layout(rect=(0, 0.02, 1, 0.98))
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(str(out_base.with_suffix(f".{ext}")),
                    format=ext, bbox_inches="tight",
                    dpi=300 if ext == "png" else None)
    plt.close(fig)


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    out_base = repo_root / "manuscript" / "figures" / "figure4_reference_implementation_architecture"
    build(out_base)
    for ext in ("pdf", "svg", "png"):
        p = out_base.with_suffix(f".{ext}")
        print(f"Written: {p.relative_to(repo_root)}  ({os.path.getsize(p):,} bytes)")
