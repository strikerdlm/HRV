"""OPI framework worked example — 128-min HRV recording, three task hypotheses.

Framework-instantiation demonstration for the OPI methodology manuscript
(manuscript/draft/opi_main_manuscript.md §3.1 and Figure 3). The script
generates representative windowed HRV metrics consistent with the
recording-level summary of the 2025-11-23 128-minute HRV recording
(8,553 RR intervals; mean HR 67.6 bpm; SDNN 107.7 ms; RMSSD 19.4 ms;
DFA-alpha1 1.36) and instantiates the OPI pipeline across three task
hypotheses:

    (A) CAT II ILS approach           — manned aviation, category 1
    (B) UAS ISR 2-hour sortie         — UAS / teleoperator, category 11
    (C) Carrier landing / recovery    — manned aviation, category 8

Outputs:

    analysis/opi_worked_example.json             — full JSON artefact
    manuscript/figures/figure3_opi_worked_example.pdf / .svg / .png

Scope and caveat: this is a framework-instantiation worked example, not
inferential data. Windowed HRV values are generated from the recording
summary with realistic variability rather than parsed from the raw
RR-interval file. The demonstration shows that the same physiological
input yields different composite readiness outputs when the active task
category changes; it does not generalise beyond the demonstration.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator


# ---------------------------------------------------------------------------
# 1. Windowed HRV metrics (80 five-minute overlapping windows)
# ---------------------------------------------------------------------------

def windowed_hrv(n_windows: int = 80, duration_min: float = 128.0, seed: int = 42):
    rng = np.random.default_rng(seed)
    t = np.linspace(0.0, duration_min, n_windows)

    rmssd = np.clip(19.4 + 3.5 * np.sin(t / 15.0) + rng.normal(0, 2.0, n_windows), 14.0, 27.0)
    sdnn = np.clip(107.7 - 30.0 * np.exp(-(t - 50.0) / 80.0) + rng.normal(0, 8.0, n_windows), 28.0, 120.0)
    sampen = np.clip(1.20 + 0.15 * np.cos(t / 25.0) + rng.normal(0, 0.05, n_windows), 0.85, 1.45)
    dfa_a1 = np.clip(1.36 + 0.10 * np.sin(t / 12.0) + rng.normal(0, 0.04, n_windows), 1.15, 1.58)
    stress_index = np.clip(140.0 + 40.0 * np.sin(t / 20.0) + rng.normal(0, 15.0, n_windows), 80.0, 230.0)

    return t, rmssd, sdnn, sampen, dfa_a1, stress_index


# ---------------------------------------------------------------------------
# 2. Normalised OPI input components (Tables 1–2 of the manuscript)
# ---------------------------------------------------------------------------

def _linear_clip(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return np.clip((x - lo) / (hi - lo) * 100.0, 0.0, 100.0)


def hrv_components(rmssd, sampen, dfa_a1):
    hrv_recovery = _linear_clip(rmssd, 15.0, 45.0)
    autonomic_reserve = _linear_clip(sampen, 0.8, 1.6)
    attention_capacity = _linear_clip(sampen * dfa_a1, 1.0, 2.2)
    return hrv_recovery, autonomic_reserve, attention_capacity


def safte_trajectory(t_minutes: np.ndarray) -> np.ndarray:
    """Baseline well-rested operator; ~88–91 % effectiveness with slow drift."""
    eff = 88.0 + 3.0 * np.sin(t_minutes / 60.0 * np.pi / 2.0) - 0.01 * t_minutes
    return np.clip(eff, 60.0, 100.0)


# ---------------------------------------------------------------------------
# 3. Penalty terms (Table 2–3)
# ---------------------------------------------------------------------------

def stress_penalty(si: np.ndarray, threshold: float = 150.0, k: float = 0.15) -> np.ndarray:
    return np.maximum(0.0, si - threshold) * k


def task_complexity_penalty(task_mod: float) -> float:
    return 5.0 * (1.0 - task_mod)


def latency_penalty(latency_ms: float) -> float:
    return 0.5 * np.log(1.0 + latency_ms / 100.0)


def multi_vehicle_penalty(n_vehicles: int) -> float:
    return 3.0 * max(0, n_vehicles - 1)


def vigilance_capacity(t_hours: np.ndarray, v0: float = 100.0, vmin: float = 65.0, lam: float = 0.12) -> np.ndarray:
    """Warm 2008 decay: (V0 - Vmin)·exp(-λ·t) + Vmin."""
    return (v0 - vmin) * np.exp(-lam * t_hours) + vmin


# ---------------------------------------------------------------------------
# 4. OPI computations for the three task hypotheses
# ---------------------------------------------------------------------------

def compute_opi(t_minutes, rmssd, sampen, dfa_a1, stress_si):
    hrv_rec, auto_res, att_cap = hrv_components(rmssd, sampen, dfa_a1)
    safte = safte_trajectory(t_minutes)

    # (A) CAT II ILS approach
    w1, w2, w3 = 0.55, 0.25, 0.20
    task_mod_ils = 0.90
    opi_ils = (
        w1 * safte * task_mod_ils
        + w2 * hrv_rec
        + w3 * auto_res
        - stress_penalty(stress_si)
        - task_complexity_penalty(task_mod_ils)
    )

    # (B) UAS ISR 2-hour sortie
    w1u, w2u, w3u, w4u = 0.35, 0.30, 0.15, 0.20
    vig_adj = vigilance_capacity(t_minutes / 60.0)
    opi_isr = (
        w1u * safte
        + w2u * vig_adj
        + w3u * hrv_rec
        + w4u * att_cap
        - latency_penalty(120.0)
        - multi_vehicle_penalty(1)
    )

    # (C) Carrier landing
    w1c, w2c, w3c = 0.50, 0.30, 0.20
    task_mod_c = 0.85
    opi_car = (
        w1c * safte * task_mod_c
        + w2c * hrv_rec
        + w3c * auto_res
        - stress_penalty(stress_si)
        - task_complexity_penalty(task_mod_c)
    )

    parameters = {
        "ils_cat_ii": {"w1": w1, "w2": w2, "w3": w3, "task_mod": task_mod_ils},
        "uas_isr": {
            "w1": w1u, "w2": w2u, "w3": w3u, "w4": w4u,
            "lambda_per_hour": 0.12, "V0": 100.0, "Vmin": 65.0,
            "latency_ms": 120.0, "n_vehicles": 1,
        },
        "carrier": {"w1": w1c, "w2": w2c, "w3": w3c, "task_mod": task_mod_c},
    }
    components = {
        "hrv_recovery": hrv_rec,
        "autonomic_reserve": auto_res,
        "attention_capacity": att_cap,
        "safte_eff": safte,
        "vigilance_adj_isr": vig_adj,
    }
    return opi_ils, opi_isr, opi_car, parameters, components


def categorise(opi_series: np.ndarray) -> np.ndarray:
    cats = np.empty(len(opi_series), dtype=object)
    for i, v in enumerate(opi_series):
        if v >= 85:
            cats[i] = "GO"
        elif v >= 70:
            cats[i] = "GO_Monitor"
        elif v >= 55:
            cats[i] = "CAUTION"
        else:
            cats[i] = "NO_GO"
    return cats


def task_summary(name: str, opi: np.ndarray, cats: np.ndarray) -> dict:
    return {
        "task": name,
        "opi_min": float(opi.min()),
        "opi_max": float(opi.max()),
        "opi_mean": float(opi.mean()),
        "opi_std": float(opi.std()),
        "pct_GO": float(np.mean(cats == "GO") * 100.0),
        "pct_GO_Monitor": float(np.mean(cats == "GO_Monitor") * 100.0),
        "pct_CAUTION": float(np.mean(cats == "CAUTION") * 100.0),
        "pct_NO_GO": float(np.mean(cats == "NO_GO") * 100.0),
    }


# ---------------------------------------------------------------------------
# 5. Figure 3
# ---------------------------------------------------------------------------

def build_figure(t_minutes, opi_series_list, titles, fig_path_base: Path):
    # Grayscale + hatching readiness bands (B&W print compliant).
    # Lighter = better readiness; CAUTION and NO-GO are hatched.
    bands = [
        (85, 100, "#f0f0f0", "",   "GO"),
        (70, 85,  "#d8d8d8", "",   "GO(Monitor)"),
        (55, 70,  "#b8b8b8", "..", "CAUTION"),
        (0,  55,  "#8c8c8c", "//", "NO-GO"),
    ]
    line_colour = "#000000"

    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.2), sharey=True, dpi=300)
    for ax, y, title in zip(axes, opi_series_list, titles):
        for lo, hi, col, hatch, _ in bands:
            ax.axhspan(lo, hi, facecolor=col, alpha=0.65,
                       edgecolor="#666666", linewidth=0.3, hatch=hatch)
        for th in (55, 70, 85):
            ax.axhline(th, color="#4a4a4a", linewidth=0.7, linestyle="--", alpha=0.8)
        ax.plot(
            t_minutes, y, color=line_colour, linewidth=1.6,
            marker="o", markersize=2.5,
            markerfacecolor=line_colour, markeredgecolor="none",
        )
        ax.set_xlim(0, 128)
        ax.set_ylim(30, 100)
        ax.set_xlabel("Time into recording (min)")
        ax.set_title(title, fontsize=10)
        ax.xaxis.set_major_locator(MultipleLocator(32))
        ax.yaxis.set_major_locator(MultipleLocator(10))
        ax.tick_params(axis="both", labelsize=8)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)

    axes[0].set_ylabel("OPI composite score")

    legend_handles = [
        mpatches.Patch(facecolor=col, alpha=0.7, edgecolor="#666666",
                       hatch=hatch, label=label)
        for _, _, col, hatch, label in bands
    ]
    fig.legend(
        handles=legend_handles, loc="lower center", ncol=4, frameon=False,
        bbox_to_anchor=(0.5, -0.02), fontsize=9,
    )
    fig.suptitle(
        "Figure 3 — Illustrative OPI worked example: same HRV input, three task hypotheses",
        fontsize=11, y=1.02,
    )
    plt.tight_layout(rect=(0, 0.04, 1, 0.98))

    for ext in ("pdf", "svg", "png"):
        out = fig_path_base.with_suffix(f".{ext}")
        fig.savefig(str(out), format=ext, bbox_inches="tight",
                    dpi=300 if ext == "png" else None)
    plt.close(fig)


# ---------------------------------------------------------------------------
# 6. Driver
# ---------------------------------------------------------------------------

def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    json_out = repo_root / "analysis" / "opi_worked_example.json"
    figure_out = repo_root / "manuscript" / "figures" / "figure3_opi_worked_example"

    t, rmssd, sdnn, sampen, dfa_a1, stress_si = windowed_hrv()
    opi_ils, opi_isr, opi_car, params, comps = compute_opi(t, rmssd, sampen, dfa_a1, stress_si)

    cats = {
        "ils": categorise(opi_ils),
        "isr": categorise(opi_isr),
        "car": categorise(opi_car),
    }
    summaries = [
        task_summary("CAT_II_ILS_approach", opi_ils, cats["ils"]),
        task_summary("UAS_ISR_2h_sortie", opi_isr, cats["isr"]),
        task_summary("Carrier_landing", opi_car, cats["car"]),
    ]

    print("OPI worked example — 128-min recording, three task hypotheses\n" + "=" * 64)
    for s in summaries:
        print(
            f"\n  {s['task']}:\n"
            f"    OPI  min-max   : {s['opi_min']:6.2f} – {s['opi_max']:6.2f}\n"
            f"    OPI  mean ± sd : {s['opi_mean']:6.2f} ± {s['opi_std']:5.2f}\n"
            f"    GO             : {s['pct_GO']:5.1f}%\n"
            f"    GO (Monitor)   : {s['pct_GO_Monitor']:5.1f}%\n"
            f"    CAUTION        : {s['pct_CAUTION']:5.1f}%\n"
            f"    NO-GO          : {s['pct_NO_GO']:5.1f}%"
        )

    artefact = {
        "source_recording": {
            "file": "2025-11-23 13-34-49.txt",
            "duration_min": 128.70,
            "beats": 8553,
            "mean_hr_bpm": 67.61,
            "sdnn_ms": 107.72,
            "rmssd_ms": 19.41,
            "dfa_alpha1": 1.36,
        },
        "framework_parameters": params,
        "summaries": summaries,
        "time_series": {
            "t_minutes": t.tolist(),
            "opi_ils": opi_ils.tolist(),
            "opi_isr": opi_isr.tolist(),
            "opi_carrier": opi_car.tolist(),
            "category_ils": cats["ils"].tolist(),
            "category_isr": cats["isr"].tolist(),
            "category_carrier": cats["car"].tolist(),
            "hrv_recovery": comps["hrv_recovery"].tolist(),
            "autonomic_reserve": comps["autonomic_reserve"].tolist(),
            "attention_capacity": comps["attention_capacity"].tolist(),
            "safte_eff": comps["safte_eff"].tolist(),
            "stress_index": stress_si.tolist(),
            "vigilance_adj_isr": comps["vigilance_adj_isr"].tolist(),
        },
        "scope_note": (
            "Framework-instantiation worked example. Windowed HRV values are "
            "representative of the recording-level summary statistics with "
            "realistic variability; they are not the raw windowed outputs of "
            "the actual recording. The example demonstrates that the same "
            "physiological input yields different composite readiness outputs "
            "when the active task category changes. It is not an empirical "
            "test and does not generalise beyond this demonstration."
        ),
    }

    json_out.parent.mkdir(parents=True, exist_ok=True)
    with json_out.open("w") as f:
        json.dump(artefact, f, indent=2)

    figure_out.parent.mkdir(parents=True, exist_ok=True)
    build_figure(
        t,
        (opi_ils, opi_isr, opi_car),
        (
            "(A) CAT II ILS approach\n$w_1=0.55, w_2=0.25, w_3=0.20$",
            "(B) UAS ISR 2-h sortie\n$w_1=0.35, w_2=0.30, w_3=0.15, w_4=0.20$",
            "(C) Carrier landing\n$w_1=0.50, w_2=0.30, w_3=0.20$",
        ),
        figure_out,
    )

    print(f"\nWritten: {json_out.relative_to(repo_root)}")
    for ext in ("pdf", "svg", "png"):
        p = figure_out.with_suffix(f".{ext}")
        print(f"Written: {p.relative_to(repo_root)}  ({os.path.getsize(p):,} bytes)")


if __name__ == "__main__":
    main()
