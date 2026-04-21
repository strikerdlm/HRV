"""Build Figure 4 — Reference-implementation architecture.

Layered architecture diagram (bottom to top): data/sensor inputs, Python
analytic core, FastAPI orchestration, delivery surfaces. OPI pathway
highlighted. TypeScript SAFTE mirror shown on the right with an explicit
'architectural consistency, not independent model' annotation.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patches as mpatches


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
COL_SENSOR   = "#deebf7"
COL_CORE     = "#bdd7e7"
COL_CORE_HI  = "#fed98e"     # highlight colour for OPI-pathway modules
COL_API      = "#9ecae1"
COL_DELIVERY = "#6baed6"
COL_MIRROR   = "#bae4bc"
EDGE         = "#08519c"
EDGE_HI      = "#cc4c02"
TEXT         = "#1a1a1a"


def box(ax, x, y, w, h, label, face=COL_SENSOR,
        fontsize=8.0, weight="normal", ec=EDGE, lw=0.9, pad=0.012):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad={pad},rounding_size=0.03",
        linewidth=lw, edgecolor=ec, facecolor=face,
    ))
    ax.text(x + w / 2, y + h / 2, label,
            ha="center", va="center", fontsize=fontsize, color=TEXT,
            weight=weight)


def arrow_up(ax, x, y0, y1, colour=EDGE, lw=0.8, mutation=12):
    ax.add_patch(FancyArrowPatch(
        (x, y0), (x, y1),
        arrowstyle="-|>", mutation_scale=mutation,
        linewidth=lw, color=colour,
    ))


def build(out_base: Path) -> None:
    fig, ax = plt.subplots(figsize=(13.2, 7.6), dpi=300)
    ax.set_xlim(-0.5, 13.0)
    ax.set_ylim(0, 7.6)
    ax.axis("off")

    # Layer labels placed to the LEFT of each band (outside box extents).
    for y, label in [
        (6.42, "L4 — Delivery"),
        (4.95, "L3 — FastAPI"),
        (3.05, "L2 — Python core"),
        (0.70, "L1 — Sensors"),
    ]:
        ax.text(-0.30, y, label,
                ha="left", va="center",
                fontsize=8.5, color="#4a4a4a", style="italic", weight="bold")

    # -----------------------------------------------------------------------
    # L1 — Data and sensor inputs
    # -----------------------------------------------------------------------
    sensor_items = [
        ("RR-interval\nstream",             0.40),
        ("Sleep + activity\nhistory",       2.30),
        ("NOAA space\nweather feed",        4.20),
        ("Mission schedule\n& task context", 6.10),
        ("Control latency\n& vehicle count", 8.00),
        ("User-profile\n(persistent)",       9.90),
    ]
    for label, x in sensor_items:
        box(ax, x, 0.25, 1.80, 0.90, label, face=COL_SENSOR, fontsize=7.8)

    # -----------------------------------------------------------------------
    # L2 — Python analytic core
    # -----------------------------------------------------------------------
    core_items = [
        ("app/hrv_core.py\nHRV engine",                 0.40, True),
        ("app/fatigue_calculator/\nsafte_model.py",     2.30, True),
        ("app/scheduling_core.py\napp/frms*.py\nreadiness fusion", 4.20, True),
        ("app/noaa_space.py\napp/space_weather_*",      6.10, False),
        ("app/user_profile_tab.py\napp/user_database.py", 8.00, False),
        ("app/publication_export.py\napp/export_utils.py", 9.90, False),
    ]
    for label, x, highlighted in core_items:
        face = COL_CORE_HI if highlighted else COL_CORE
        ec = EDGE_HI if highlighted else EDGE
        lw = 1.3 if highlighted else 0.9
        box(ax, x, 2.25, 1.80, 1.60, label,
            face=face, ec=ec, lw=lw, fontsize=7.5)

    # -----------------------------------------------------------------------
    # L3 — FastAPI orchestration
    # -----------------------------------------------------------------------
    box(ax, 1.00, 4.40, 4.10, 1.10,
        "api/main.py\n" + r"$\cdot$ OPI + HRV + scheduling + user-profile endpoints",
        face=COL_API, fontsize=8.5, weight="bold")
    box(ax, 6.00, 4.40, 4.10, 1.10,
        "api/research_endpoints.py\n" + r"$\cdot$ research-route windowed analytics",
        face=COL_API, fontsize=8.5, weight="bold")

    # -----------------------------------------------------------------------
    # L4 — Delivery surfaces
    # -----------------------------------------------------------------------
    box(ax, 0.80, 5.85, 3.00, 1.15,
        "Next.js operational client\nscheduling · readiness · profile",
        face=COL_DELIVERY, fontsize=8.5, weight="bold")
    box(ax, 4.30, 5.85, 3.00, 1.15,
        "Next.js research client\nHRV · fatigue · correlations",
        face=COL_DELIVERY, fontsize=8.5, weight="bold")
    box(ax, 7.80, 5.85, 2.80, 1.15,
        "Streamlit entrypoints\n(secondary interfaces)",
        face="#c6dbef", fontsize=8.5)

    # -----------------------------------------------------------------------
    # TypeScript SAFTE mirror (right-side annotation)
    # -----------------------------------------------------------------------
    box(ax, 11.55, 2.70, 1.35, 1.10,
        "frontend/src/\nlib/safte-model.ts",
        face=COL_MIRROR, fontsize=7.2, weight="bold")
    ax.text(12.22, 4.00,
            "TypeScript SAFTE mirror",
            ha="center", va="bottom", fontsize=7.5, color=TEXT, weight="bold")
    ax.text(12.22, 2.60,
            "architectural consistency,\nnot independent model",
            ha="center", va="top", fontsize=6.8, color="#4a4a4a", style="italic")

    # Dashed sync arrow from canonical Python SAFTE (L2) to TS mirror, routed
    # above the L2 boxes to avoid crossing other modules.
    ax.add_patch(FancyArrowPatch(
        (4.10, 3.95), (11.55, 3.80),
        arrowstyle="<->", mutation_scale=12,
        linewidth=0.9, color="#4a4a4a",
        linestyle=(0, (5, 3)),
        connectionstyle="arc3,rad=-0.12",
    ))

    # -----------------------------------------------------------------------
    # Vertical flow arrows between layers
    # -----------------------------------------------------------------------
    # L1 -> L2
    for x_centre in (1.30, 3.20, 5.10, 7.00, 8.90, 10.80):
        if x_centre > 10.5:
            continue
        arrow_up(ax, x_centre, 1.18, 2.23)

    # L2 -> L3  (fan-in to API)
    for x_centre in (1.30, 3.20, 5.10):
        arrow_up(ax, x_centre, 3.88, 4.38, lw=0.8)
    for x_centre in (7.00, 8.90):
        arrow_up(ax, x_centre, 3.88, 4.38, lw=0.8)

    # L3 -> L4
    for x_src, x_dst in [(2.30, 2.30), (7.00, 5.80), (8.80, 9.10)]:
        arrow_up(ax, x_src, 5.52, 5.83, lw=0.9)

    # -----------------------------------------------------------------------
    # Title + legend
    # -----------------------------------------------------------------------
    ax.text(6.10, 7.45,
            "Figure 4 — Reference-implementation architecture; OPI pathway highlighted",
            ha="center", fontsize=11.5, weight="bold", color=TEXT)

    legend = [
        mpatches.Patch(facecolor=COL_CORE_HI, edgecolor=EDGE_HI, label="OPI pathway modules"),
        mpatches.Patch(facecolor=COL_CORE,    edgecolor=EDGE,    label="Supporting analytic modules"),
        mpatches.Patch(facecolor=COL_API,     edgecolor=EDGE,    label="FastAPI orchestration"),
        mpatches.Patch(facecolor=COL_DELIVERY, edgecolor=EDGE,   label="Primary delivery (Next.js)"),
        mpatches.Patch(facecolor="#c6dbef",   edgecolor=EDGE,    label="Secondary delivery (Streamlit)"),
        mpatches.Patch(facecolor=COL_MIRROR,  edgecolor=EDGE,    label="Client-side mirror"),
    ]
    ax.legend(handles=legend, loc="lower center", ncol=3,
              frameon=False, fontsize=7.8, bbox_to_anchor=(0.5, -0.02))

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
    import os
    for ext in ("pdf", "svg", "png"):
        p = out_base.with_suffix(f".{ext}")
        print(f"Written: {p.relative_to(repo_root)}  ({os.path.getsize(p):,} bytes)")
