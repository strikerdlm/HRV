"""Build Figure 2 — OPI task taxonomy and dominant autonomic signatures.

Simplified small-multiples layout. Two panels: ten manned-aviation
task categories at top, seven UAS / teleoperator categories at bottom.
Every cell names the task, its category index, and a short dominant-
signature tag. Palette coordinated with Figures 1 and 4.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


# ---------------------------------------------------------------------------
# Grayscale signature-family palette — seven evenly-spaced smooth shades.
# No hatching: distinct shades alone ensure legibility and keep black
# text readable at all font sizes.
# ---------------------------------------------------------------------------
SIG_COLOURS = {
    "LF_HF_dominant":   "#f4f4f4",  # near-white
    "Vagal_withdrawal": "#e2e2e2",  # very light grey
    "Complexity_drop":  "#d0d0d0",  # light grey
    "Precision_markers":"#bebebe",  # soft grey
    "Acute_suppression":"#acacac",  # medium-light grey
    "Vigilance_decay":  "#9a9a9a",  # medium grey
    "Latency_dominant": "#888888",  # medium-dark grey
}
EDGE = "#2c3e50"
MUTED = "#5a6570"
TEXT = "#1a1a1a"


# ---------------------------------------------------------------------------
# Manned-aviation taxonomy (ten categories)
# ---------------------------------------------------------------------------
MANNED = [
    dict(n=1,  name="IMC flying",
         sig="LF/HF ↑  ·  RMSSD ↓",
         family="LF_HF_dominant"),
    dict(n=2,  name="NVD operations",
         sig="Stress ↑  ·  RMSSD ↓",
         family="LF_HF_dominant"),
    dict(n=3,  name="HMD flying",
         sig="Complexity ↓",
         family="Complexity_drop"),
    dict(n=4,  name="High-density ATC",
         sig="HF ↓↓  ·  entropy ↓",
         family="Vagal_withdrawal"),
    dict(n=5,  name="Critical emergency",
         sig="Acute RMSSD ↓↓",
         family="Acute_suppression"),
    dict(n=6,  name="Non-critical\nemergency",
         sig="Moderate LF/HF ↑",
         family="LF_HF_dominant"),
    dict(n=7,  name="Test pilot",
         sig="Wide arousal band",
         family="Complexity_drop"),
    dict(n=8,  name="Carrier landing",
         sig="RMSSD > 35 ms target",
         family="Precision_markers"),
    dict(n=9,  name="Weapons delivery",
         sig="HF ↓  ·  entropy ↓",
         family="Vagal_withdrawal"),
    dict(n=10, name="New-platform\ntesting",
         sig="Learning-load\ncomplexity ↓",
         family="Complexity_drop"),
]

# ---------------------------------------------------------------------------
# UAS / teleoperator taxonomy (seven categories)
# ---------------------------------------------------------------------------
UAS = [
    dict(n=11, name="ISR",
         sig="λ = 0.08 h⁻¹\nVmin = 70",
         family="Vigilance_decay"),
    dict(n=12, name="Strike",
         sig="Acute spike  ·  entropy ↓",
         family="Acute_suppression"),
    dict(n=13, name="SAR / CSAR",
         sig="Sustained LF ↑",
         family="LF_HF_dominant"),
    dict(n=14, name="Swarm\nsupervisory",
         sig="Multi-vehicle penalty\ncomplexity ↓",
         family="Complexity_drop"),
    dict(n=15, name="Contested\nenvironment",
         sig="Persistent LF ↑",
         family="Vagal_withdrawal"),
    dict(n=16, name="Ground-robot\nteleoperation",
         sig="Spatial-transformation\nload",
         family="Latency_dominant"),
    dict(n=17, name="Subsea / long-\nlatency teleop",
         sig="Latency dominates",
         family="Latency_dominant"),
]


def draw_cell(ax, x, y, w, h, entry):
    face = SIG_COLOURS[entry["family"]]
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.010,rounding_size=0.04",
        linewidth=0.6, edgecolor=EDGE, facecolor=face,
    ))
    # Index + task name (top)
    ax.text(x + w / 2, y + h - 0.15,
            f"#{entry['n']}  {entry['name']}",
            ha="center", va="top",
            fontsize=8.5, weight="bold", color=TEXT)
    # Dominant-signature tag (bottom)
    ax.text(x + w / 2, y + 0.14,
            entry["sig"],
            ha="center", va="bottom",
            fontsize=7.6, color=TEXT)


def build(out_base: Path) -> None:
    fig = plt.figure(figsize=(13.0, 7.0), dpi=300)

    # =========================================================================
    # Top panel — manned aviation (2 rows × 5 cols)
    # =========================================================================
    ax_top = fig.add_axes((0.04, 0.56, 0.92, 0.36))
    ax_top.set_xlim(0, 10.0)
    ax_top.set_ylim(0, 2.6)
    ax_top.axis("off")
    ax_top.text(5.0, 2.46,
                "A.  Manned aviation task categories  (n = 10)",
                ha="center", fontsize=11, weight="bold", color=TEXT)

    cell_w, cell_h = 1.85, 0.92
    x_gap, y_gap = 0.13, 0.16
    for idx, entry in enumerate(MANNED):
        row = idx // 5
        col = idx % 5
        x = 0.15 + col * (cell_w + x_gap)
        y = 1.10 - row * (cell_h + y_gap)
        draw_cell(ax_top, x, y, cell_w, cell_h, entry)

    # =========================================================================
    # Bottom panel — UAS / teleoperator (2 rows × 4 cols, last cell empty)
    # =========================================================================
    ax_bot = fig.add_axes((0.04, 0.08, 0.92, 0.42))
    ax_bot.set_xlim(0, 10.0)
    ax_bot.set_ylim(0, 2.6)
    ax_bot.axis("off")
    ax_bot.text(5.0, 2.46,
                "B.  UAS / teleoperator task categories  (n = 7)",
                ha="center", fontsize=11, weight="bold", color=TEXT)

    uas_cell_w = 2.30
    for idx, entry in enumerate(UAS):
        row = idx // 4
        col = idx % 4
        x = 0.30 + col * (uas_cell_w + x_gap)
        y = 1.10 - row * (cell_h + y_gap)
        draw_cell(ax_bot, x, y, uas_cell_w, cell_h, entry)

    # =========================================================================
    # Legend (signature families) along the bottom margin
    # =========================================================================
    legend_entries = [
        ("LF_HF_dominant",    "LF/HF ↑ dominant"),
        ("Vagal_withdrawal",  "Vagal withdrawal"),
        ("Complexity_drop",   "Complexity / entropy ↓"),
        ("Precision_markers", "Precision-motor markers"),
        ("Acute_suppression", "Acute stress suppression"),
        ("Vigilance_decay",   "Vigilance decay (UAS)"),
        ("Latency_dominant",  "Latency-dominant (UAS)"),
    ]
    patches = [mpatches.Patch(facecolor=SIG_COLOURS[k], edgecolor=EDGE, label=v)
               for k, v in legend_entries]
    fig.legend(handles=patches, loc="lower center", ncol=7,
               frameon=False, fontsize=8, bbox_to_anchor=(0.5, 0.005))

    fig.suptitle(
        "Figure 2 — Task taxonomy and dominant autonomic signatures",
        fontsize=12, weight="bold", y=0.985,
    )

    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(str(out_base.with_suffix(f".{ext}")),
                    format=ext, bbox_inches="tight",
                    dpi=300 if ext == "png" else None)
    plt.close(fig)


if __name__ == "__main__":
    import os
    repo_root = Path(__file__).resolve().parent.parent
    out_base = repo_root / "manuscript" / "figures" / "figure2_task_taxonomy_hrv_signatures"
    build(out_base)
    for ext in ("pdf", "svg", "png"):
        p = out_base.with_suffix(f".{ext}")
        print(f"Written: {p.relative_to(repo_root)}  ({os.path.getsize(p):,} bytes)")
