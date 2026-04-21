"""Build Figure 1 — OPI conceptual schematic.

Simplified, publication-grade four-column flow diagram: Inputs →
Components → Per-task modulation & penalties → Readiness output.
Follows .cursor/rules/plots.mdc: flat typography, muted palette,
minimal ornament, greyscale-readable.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


# ---------------------------------------------------------------------------
# Muted palette — coordinated with Figures 2 and 4
# ---------------------------------------------------------------------------
COL_INPUT = "#eaf2fb"     # pale blue — inputs
COL_COMP = "#c6dbef"      # soft blue — components (all tasks)
COL_COMP_UAS = "#9ecae1"  # medium blue — UAS-only components
COL_WEIGHT = "#f8d36b"    # warm gold — per-task weights
COL_PENALTY = "#e79f7b"   # muted umber — penalties
COL_OUTPUT = "#b9dfa7"    # calm green — readiness band
EDGE = "#2c3e50"
MUTED = "#5a6570"
TEXT = "#1a1a1a"


def box(ax, x, y, w, h, label, face, fontsize=8.0, weight="normal", lw=0.7):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.012,rounding_size=0.05",
        linewidth=lw, edgecolor=EDGE, facecolor=face,
    ))
    ax.text(x + w / 2, y + h / 2, label,
            ha="center", va="center", fontsize=fontsize, color=TEXT,
            weight=weight)


def arrow(ax, x0, y0, x1, y1, lw=0.6, colour=EDGE, mutation=8):
    ax.add_patch(FancyArrowPatch(
        (x0, y0), (x1, y1),
        arrowstyle="-|>", mutation_scale=mutation,
        linewidth=lw, color=colour,
    ))


def build(out_base: Path) -> None:
    fig, ax = plt.subplots(figsize=(13.0, 5.4), dpi=300)
    ax.set_xlim(0, 13.2)
    ax.set_ylim(0, 5.6)
    ax.axis("off")

    # Column headers
    headers = [(1.05, "Inputs"),
               (3.75, "OPI components"),
               (6.80, "Per-task weights · penalties"),
               (12.00, "Readiness")]
    for x, label in headers:
        ax.text(x, 5.20, label,
                ha="center", fontsize=10, weight="bold", color=TEXT)

    # =========================================================================
    # Column 1 — Inputs (four, evenly spaced)
    # =========================================================================
    input_rows = [
        ("RR-interval stream",                   4.00),
        ("Sleep + activity history",             2.95),
        ("Task context\n(category · complexity)", 1.90),
        ("Operational context\n(latency · n-vehicles)", 0.85),
    ]
    for label, y in input_rows:
        box(ax, 0.25, y, 1.60, 0.85, label, COL_INPUT, fontsize=7.8)

    # =========================================================================
    # Column 2 — OPI components
    # =========================================================================
    comp_rows = [
        (r"$\mathrm{SAFTE}_{\mathrm{eff}}$",    4.00, COL_COMP),
        ("HRV recovery\n(RMSSD · SDNN)",         2.95, COL_COMP),
        ("Autonomic reserve\n(SampEn · DFA-α1)", 1.90, COL_COMP),
        ("Vigilance · attention\n(UAS only)",    0.85, COL_COMP_UAS),
    ]
    for label, y, face in comp_rows:
        box(ax, 2.95, y, 1.60, 0.85, label, face, fontsize=7.8)

    # =========================================================================
    # Column 3 — Weights & penalties
    # =========================================================================
    weight_rows = [
        (r"$w_1, w_2, w_3\,(, w_4)$" + "\nper-task profile", 4.00, COL_WEIGHT),
        (r"$\mathrm{Task}_{\mathrm{mod}}$" + "\ncomplexity modifier", 2.95, COL_WEIGHT),
        ("Stress · task-complexity\npenalties", 1.90, COL_PENALTY),
        ("Latency · multi-vehicle\npenalties (UAS)", 0.85, COL_PENALTY),
    ]
    for label, y, face in weight_rows:
        box(ax, 5.75, y, 2.05, 0.85, label, face, fontsize=7.8)

    # Composition equation — placed between the penalties column and the readiness bands
    eq_text = r"$\mathrm{OPI} \;=\; \sum_i w_i\, C_i \;-\; \mathrm{pen.}$"
    ax.text(9.30, 2.80, eq_text,
            ha="center", va="center", fontsize=11.5, color=TEXT,
            bbox=dict(boxstyle="round,pad=0.22",
                      facecolor="#fbfcfe", edgecolor=EDGE, linewidth=0.7))

    # =========================================================================
    # Column 4 — Readiness bands
    # =========================================================================
    bands = [
        ("GO  (≥ 85)",       4.30, "#c7e0c2"),
        ("GO-Monitor 70-84", 3.40, "#e6eec1"),
        ("CAUTION 55-69",    2.50, "#f8d36b"),
        ("NO-GO (< 55)",     1.60, "#e79f7b"),
    ]
    for label, y, face in bands:
        box(ax, 11.10, y, 1.80, 0.65, label,
            face=face, fontsize=8.5, weight="bold", lw=0.9)

    # =========================================================================
    # Flow arrows — column-to-column at four horizontal levels
    # =========================================================================
    # Inputs → Components (y-aligned pairs)
    for y in (4.425, 3.375, 2.325, 1.275):
        arrow(ax, 1.87, y, 2.93, y)

    # Components → weights
    for y in (4.425, 3.375, 2.325, 1.275):
        arrow(ax, 4.57, y, 5.73, y)

    # Weights → equation (converging fan-in)
    for y in (4.425, 3.375, 2.325, 1.275):
        arrow(ax, 7.82, y, 8.75, 2.80, lw=0.5, colour=MUTED, mutation=7)

    # Equation → readiness
    arrow(ax, 9.90, 2.80, 11.08, 2.80, lw=1.2, mutation=14)

    # =========================================================================
    # Title + thin legend
    # =========================================================================
    ax.text(6.50, 5.52,
            "Figure 1 — Operational Performance Indicator (OPI) conceptual schematic",
            ha="center", fontsize=12, weight="bold", color=TEXT)

    legend_patches = [
        mpatches.Patch(facecolor=COL_COMP, edgecolor=EDGE, label="Components (all tasks)"),
        mpatches.Patch(facecolor=COL_COMP_UAS, edgecolor=EDGE, label="UAS-only component"),
        mpatches.Patch(facecolor=COL_WEIGHT, edgecolor=EDGE, label="Task weight · modifier"),
        mpatches.Patch(facecolor=COL_PENALTY, edgecolor=EDGE, label="Penalty (subtracted)"),
    ]
    ax.legend(handles=legend_patches, loc="lower center", ncol=4,
              frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.03))

    plt.tight_layout(rect=(0, 0.02, 1, 0.97))
    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(str(out_base.with_suffix(f".{ext}")),
                    format=ext, bbox_inches="tight",
                    dpi=300 if ext == "png" else None)
    plt.close(fig)


if __name__ == "__main__":
    import os
    repo_root = Path(__file__).resolve().parent.parent
    out_base = repo_root / "manuscript" / "figures" / "figure1_opi_conceptual_schematic"
    build(out_base)
    for ext in ("pdf", "svg", "png"):
        p = out_base.with_suffix(f".{ext}")
        print(f"Written: {p.relative_to(repo_root)}  ({os.path.getsize(p):,} bytes)")
