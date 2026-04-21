"""Build Figure 2 — Task taxonomy and dominant HRV signatures.

Small-multiples layout. Top panel shows 10 manned-aviation categories;
bottom panel shows 7 UAS/teleoperator categories. Each cell names the
task, summarises its dominant autonomic signature under high workload,
and is colour-coded by signature family.

Source taxonomy: manuscript/tables/opi_task_taxonomy.md.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.patches as mpatches


# ---------------------------------------------------------------------------
# Signature-family colour palette
# ---------------------------------------------------------------------------
SIG_COLOURS = {
    "LF_HF_dominant":     "#fed98e",   # sympathetic shift
    "Vagal_withdrawal":   "#fdae61",   # parasympathetic drop
    "Complexity_drop":    "#d9d9d9",   # entropy / complexity reduction
    "Precision_markers":  "#bae4bc",   # RMSSD + Poincaré targets
    "Acute_suppression":  "#fcae91",   # acute stress signature
    "Vigilance_decay":    "#fdd49e",   # UAS vigilance decrement
    "Latency_dominant":   "#c6dbef",   # UAS latency-sensitive
}
EDGE = "#08519c"
TEXT = "#1a1a1a"


# ---------------------------------------------------------------------------
# Manned aviation taxonomy (10 categories)
# ---------------------------------------------------------------------------
MANNED = [
    dict(n=1,  name="IMC flying",
         sig="LF/HF ↑ 40-80%\nRMSSD ↓",
         family="LF_HF_dominant"),
    dict(n=2,  name="NVD operations",
         sig="Stress index ↑\nRMSSD ↓ over time",
         family="LF_HF_dominant"),
    dict(n=3,  name="HMD flying",
         sig="Complexity ↓\n(SampEn)",
         family="Complexity_drop"),
    dict(n=4,  name="High-density ATC",
         sig="HF ↓↓\nEntropy ↓ at saturation",
         family="Vagal_withdrawal"),
    dict(n=5,  name="Critical emergency",
         sig="Acute suppression:\nRMSSD ↓↓, HF ↓↓",
         family="Acute_suppression"),
    dict(n=6,  name="Non-critical\nemergency",
         sig="Moderate LF/HF ↑\nStress index moderate",
         family="LF_HF_dominant"),
    dict(n=7,  name="Test pilot",
         sig="Wide arousal band\nRapid recovery",
         family="Complexity_drop"),
    dict(n=8,  name="Carrier landing",
         sig="RMSSD > 35 ms target\nSD1/SD2 ~ 0.4-0.6",
         family="Precision_markers"),
    dict(n=9,  name="Weapons delivery",
         sig="Ingress LF ↑\nTarget: HF ↓, entropy ↓",
         family="Vagal_withdrawal"),
    dict(n=10, name="New-platform\ntesting",
         sig="Learning load:\ncomplexity ↓",
         family="Complexity_drop"),
]


# ---------------------------------------------------------------------------
# UAS taxonomy (7 categories)
# ---------------------------------------------------------------------------
UAS = [
    dict(n=11, name="ISR\n(high-event)",
         sig="λ = 0.08 h⁻¹\nVmin = 70",
         family="Vigilance_decay"),
    dict(n=12, name="Strike",
         sig="Acute release spike\nEntropy ↓",
         family="Acute_suppression"),
    dict(n=13, name="SAR / CSAR",
         sig="Sustained LF ↑\nDynamic SA load",
         family="LF_HF_dominant"),
    dict(n=14, name="Swarm\nsupervisory",
         sig="Multi-vehicle penalty\nComplexity ↓",
         family="Complexity_drop"),
    dict(n=15, name="Contested\nenvironment",
         sig="Persistent LF ↑\nEntropy ↓",
         family="Vagal_withdrawal"),
    dict(n=16, name="Ground-robot\nteleoperation",
         sig="Spatial-transformation\nload; complexity ↓",
         family="Latency_dominant"),
    dict(n=17, name="Subsea / long-\nlatency teleop",
         sig="Latency dominates\nStress index ↑",
         family="Latency_dominant"),
]


def draw_cell(ax, x, y, w, h, entry):
    face = SIG_COLOURS[entry["family"]]
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.005,rounding_size=0.02",
        linewidth=0.8, edgecolor=EDGE, facecolor=face,
    ))
    # Task number + name
    ax.text(x + w / 2, y + h - 0.15,
            f"#{entry['n']}  {entry['name']}",
            ha="center", va="top",
            fontsize=8.5, weight="bold", color=TEXT)
    # HRV signature text
    ax.text(x + w / 2, y + 0.12,
            entry["sig"],
            ha="center", va="bottom",
            fontsize=7.8, color=TEXT)


def build(out_base: Path) -> None:
    fig = plt.figure(figsize=(13.2, 7.2), dpi=300)

    # -----------------------------------------------------------------------
    # Manned panel — 2 rows × 5 cols
    # -----------------------------------------------------------------------
    ax_top = fig.add_axes((0.04, 0.56, 0.92, 0.37))
    ax_top.set_xlim(0, 10.0)
    ax_top.set_ylim(0, 2.6)
    ax_top.axis("off")
    ax_top.text(5.0, 2.50,
                "A.  Manned aviation task categories (10)",
                ha="center", fontsize=11, weight="bold", color=TEXT)

    cell_w, cell_h = 1.85, 0.96
    x_gap, y_gap = 0.13, 0.14
    for idx, entry in enumerate(MANNED):
        row = idx // 5
        col = idx % 5
        x = 0.15 + col * (cell_w + x_gap)
        y = 1.20 - row * (cell_h + y_gap)
        draw_cell(ax_top, x, y, cell_w, cell_h, entry)

    # -----------------------------------------------------------------------
    # UAS panel — 2 rows × 4 cols (last cell empty)
    # -----------------------------------------------------------------------
    ax_bot = fig.add_axes((0.04, 0.08, 0.92, 0.42))
    ax_bot.set_xlim(0, 10.0)
    ax_bot.set_ylim(0, 2.6)
    ax_bot.axis("off")
    ax_bot.text(5.0, 2.50,
                "B.  UAS / teleoperator task categories (7)",
                ha="center", fontsize=11, weight="bold", color=TEXT)

    uas_cell_w = 2.30
    for idx, entry in enumerate(UAS):
        row = idx // 4
        col = idx % 4
        x = 0.30 + col * (uas_cell_w + x_gap)
        y = 1.20 - row * (cell_h + y_gap)
        draw_cell(ax_bot, x, y, uas_cell_w, cell_h, entry)

    # -----------------------------------------------------------------------
    # Legend (signature families)
    # -----------------------------------------------------------------------
    legend_entries = [
        ("LF_HF_dominant",    "LF/HF ↑ dominant"),
        ("Vagal_withdrawal",  "Vagal withdrawal"),
        ("Complexity_drop",   "Complexity / entropy ↓"),
        ("Precision_markers", "Precision-motor markers"),
        ("Acute_suppression", "Acute stress suppression"),
        ("Vigilance_decay",   "Vigilance decay (UAS)"),
        ("Latency_dominant",  "Latency-dominant (UAS)"),
    ]
    patches = [mpatches.Patch(color=SIG_COLOURS[k], label=v, edgecolor=EDGE)
               for k, v in legend_entries]
    fig.legend(handles=patches, loc="lower center", ncol=7,
               frameon=False, fontsize=8, bbox_to_anchor=(0.5, 0.01))

    fig.suptitle(
        "Figure 2 — OPI task taxonomy and dominant autonomic signatures",
        fontsize=12, weight="bold", y=0.985,
    )

    out_base.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(str(out_base.with_suffix(f".{ext}")),
                    format=ext, bbox_inches="tight",
                    dpi=300 if ext == "png" else None)
    plt.close(fig)


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    out_base = repo_root / "manuscript" / "figures" / "figure2_task_taxonomy_hrv_signatures"
    build(out_base)
    import os
    for ext in ("pdf", "svg", "png"):
        p = out_base.with_suffix(f".{ext}")
        print(f"Written: {p.relative_to(repo_root)}  ({os.path.getsize(p):,} bytes)")
