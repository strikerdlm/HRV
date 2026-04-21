"""Build Figure 1 — OPI conceptual schematic.

Four-column layout: Inputs → Components → Weights/Penalties → Output.
Targets publication-quality export in PDF, SVG, and 300 dpi PNG for
Applied Ergonomics submission. See manuscript/figures/figure_plan_opi.md.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patches as mpatches


# ---------------------------------------------------------------------------
# Colour palette (colourblind-safe; greyscale-readable)
# ---------------------------------------------------------------------------
COL_INPUT   = "#deebf7"     # light blue
COL_COMP    = "#bdd7e7"     # medium blue
COL_WEIGHT  = "#fed98e"     # light amber (MRT / task-specific)
COL_PENALTY = "#fdae61"     # amber (subtractive)
COL_OUTPUT  = "#bae4bc"     # green (readiness)
EDGE        = "#08519c"
TEXT        = "#1a1a1a"


def box(ax, x, y, w, h, label, face=COL_INPUT, fontsize=7.5, lw=0.8, weight="normal"):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.005,rounding_size=0.02",
        linewidth=lw, edgecolor=EDGE, facecolor=face,
    )
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, label,
            ha="center", va="center", fontsize=fontsize, color=TEXT,
            weight=weight, wrap=True)


def arrow(ax, x0, y0, x1, y1, colour=EDGE, lw=0.9, style="-|>", mutation=14):
    a = FancyArrowPatch(
        (x0, y0), (x1, y1),
        arrowstyle=style, mutation_scale=mutation,
        linewidth=lw, color=colour, zorder=1,
    )
    ax.add_patch(a)


def build(out_base: Path) -> None:
    fig, ax = plt.subplots(figsize=(11.5, 5.8), dpi=300)
    ax.set_xlim(0, 11.5)
    ax.set_ylim(0, 5.8)
    ax.axis("off")

    # -----------------------------------------------------------------------
    # Column 1 — Inputs
    # -----------------------------------------------------------------------
    ax.text(0.9, 5.5, "Inputs", ha="center", fontsize=10, weight="bold", color=TEXT)
    inputs = [
        ("RR-interval stream",      4.30),
        ("Sleep + activity history", 3.20),
        ("Task context\n(category + complexity)", 2.05),
        ("Operational context\n(latency, n-vehicles)", 0.80),
    ]
    for label, y in inputs:
        box(ax, 0.15, y, 1.5, 0.85, label, face=COL_INPUT)

    # -----------------------------------------------------------------------
    # Column 2 — Components
    # -----------------------------------------------------------------------
    ax.text(3.50, 5.5, "OPI components", ha="center", fontsize=10, weight="bold", color=TEXT)
    components_manned = [
        (r"SAFTE$_{\mathrm{eff}}$",       4.30, 0.90),
        ("HRV recovery\n(RMSSD, SDNN)",   3.20, 0.90),
        ("Autonomic reserve\n(SampEn, DFA-α1)", 2.05, 0.90),
    ]
    for label, y, h in components_manned:
        box(ax, 2.75, y, 1.5, h, label, face=COL_COMP)

    # UAS-specific components (coloured slightly different to flag UAS-only)
    box(ax, 2.75, 0.80, 1.5, 0.85,
        "Attention capacity\nVigilance (UAS)",
        face="#9ecae1")

    # -----------------------------------------------------------------------
    # Column 3 — Weights and penalties
    # -----------------------------------------------------------------------
    ax.text(6.40, 5.5, "Per-task weights & penalties",
            ha="center", fontsize=10, weight="bold", color=TEXT)

    box(ax, 5.5, 4.30, 1.8, 0.85,
        r"$w_1, w_2, w_3 (, w_4)$" + "\nper-task profile",
        face=COL_WEIGHT)
    box(ax, 5.5, 3.20, 1.8, 0.85,
        r"Task$_{\mathrm{mod}}$" + "\ncomplexity modifier",
        face=COL_WEIGHT)
    box(ax, 5.5, 2.05, 1.8, 0.85,
        "Stress penalty\nTask-complexity penalty",
        face=COL_PENALTY)
    box(ax, 5.5, 0.80, 1.8, 0.85,
        "Latency penalty (UAS)\nMulti-vehicle penalty",
        face=COL_PENALTY)

    # Composition equation (central)
    eq_text = (
        r"$\mathrm{OPI} = \sum_i w_i C_i \;-\; \mathrm{penalties}$"
    )
    ax.text(8.85, 3.00, eq_text,
            ha="center", va="center", fontsize=12, color=TEXT,
            bbox=dict(boxstyle="round,pad=0.30",
                      facecolor="#f7fbff", edgecolor=EDGE, linewidth=0.8))

    # -----------------------------------------------------------------------
    # Column 4 — Readiness bands (output)
    # -----------------------------------------------------------------------
    ax.text(10.65, 5.5, "Readiness categories", ha="center", fontsize=10, weight="bold", color=TEXT)
    bands = [
        ("GO  (≥85)",         4.55, "#bdd7e7"),
        ("GO-Monitor (70-84)", 3.60, "#bae4bc"),
        ("CAUTION (55-69)",    2.65, "#fed98e"),
        ("NO-GO (<55)",        1.70, "#fdae61"),
    ]
    for label, y, face in bands:
        box(ax, 9.80, y, 1.70, 0.70, label, face=face, fontsize=8.5, weight="bold", lw=0.9)

    # -----------------------------------------------------------------------
    # Arrows between columns
    # -----------------------------------------------------------------------
    # Inputs -> Components
    for y_src, y_dst in [(4.72, 4.72), (3.62, 3.62), (2.47, 2.47), (1.22, 1.22)]:
        arrow(ax, 1.68, y_src, 2.72, y_dst)

    # Components -> equation/weights
    for y in (4.72, 3.62, 2.47, 1.22):
        arrow(ax, 4.28, y, 5.46, y)

    # Weights/penalties -> equation
    for y in (4.72, 3.62, 2.47, 1.22):
        arrow(ax, 7.32, y, 8.20, 3.10 + 0.02, colour="#4a4a4a", lw=0.7, mutation=10)

    # Equation -> readiness
    arrow(ax, 9.50, 3.00, 9.78, 3.00, lw=1.3, mutation=18)

    # -----------------------------------------------------------------------
    # Title + legend
    # -----------------------------------------------------------------------
    ax.text(5.75, 5.65,
            "Figure 1 — Operational Performance Indicator (OPI) conceptual schematic",
            ha="center", fontsize=11, weight="bold", color=TEXT)

    # Tiny legend for manned/UAS distinction
    legend_patches = [
        mpatches.Patch(color=COL_COMP,     label="Components (all tasks)"),
        mpatches.Patch(color="#9ecae1",    label="Components (UAS only)"),
        mpatches.Patch(color=COL_WEIGHT,   label="Task-specific weight/modifier"),
        mpatches.Patch(color=COL_PENALTY,  label="Penalty term (subtractive)"),
    ]
    ax.legend(handles=legend_patches, loc="lower center", ncol=4,
              frameon=False, fontsize=7.5, bbox_to_anchor=(0.5, -0.02))

    plt.tight_layout(rect=(0, 0.02, 1, 0.98))

    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(str(out_base.with_suffix(f".{ext}")),
                    format=ext, bbox_inches="tight",
                    dpi=300 if ext == "png" else None)
    plt.close(fig)


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    out_base = repo_root / "manuscript" / "figures" / "figure1_opi_conceptual_schematic"
    build(out_base)
    import os
    for ext in ("pdf", "svg", "png"):
        p = out_base.with_suffix(f".{ext}")
        print(f"Written: {p.relative_to(repo_root)}  ({os.path.getsize(p):,} bytes)")
