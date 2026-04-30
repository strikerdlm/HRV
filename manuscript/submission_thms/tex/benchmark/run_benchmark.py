"""
HRV-engine numerical benchmark against NeuroKit2 on MIT-BIH NSR (PhysioNet).

Output:
- benchmark_results.csv : per-window metrics from each engine
- benchmark_summary.json : ICC + Bland-Altman LoA per metric

Run from repo root:
    /root/.venvs/hrv-bench/bin/python3 manuscript/submission_thms/tex/benchmark/run_benchmark.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import wfdb

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from app.hrv_core import compute_comprehensive_hrv  # noqa: E402

import neurokit2 as nk  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
WINDOW_SEC = 300  # 5-minute non-overlapping windows


def fetch_rr_intervals(record_id: str) -> np.ndarray:
    """Download one MIT-BIH NSR record and return RR intervals in milliseconds."""
    record = wfdb.rdrecord(record_id, pn_dir="nsrdb")
    annotation = wfdb.rdann(record_id, "atr", pn_dir="nsrdb")
    fs = record.fs
    rr_ms = np.diff(annotation.sample) / fs * 1000.0
    rr_ms = rr_ms[(rr_ms > 300) & (rr_ms < 2000)]
    return rr_ms


def windowed(rr_ms: np.ndarray, window_sec: int = WINDOW_SEC):
    cum = np.cumsum(rr_ms) / 1000.0
    end = cum[-1]
    starts = np.arange(0.0, end - window_sec, window_sec)
    for t0 in starts:
        mask = (cum >= t0) & (cum < t0 + window_sec)
        if mask.sum() >= 50:
            yield rr_ms[mask]


def metrics_app(rr_ms: np.ndarray) -> dict:
    out = compute_comprehensive_hrv(rr_ms.astype(float), include_advanced=True)
    flat = {
        "RMSSD": out.get("rmssd"),
        "SDNN": out.get("sdnn"),
        "pNN50": out.get("pnn50"),
        "LF": out.get("lf_power"),
        "HF": out.get("hf_power"),
        "LF_HF": out.get("lf_hf_ratio"),
        "SD1": out.get("sd1"),
        "SD2": out.get("sd2"),
        "SampEn": out.get("sample_entropy"),
    }
    return flat


def metrics_nk(rr_ms: np.ndarray) -> dict:
    rri_s = rr_ms / 1000.0
    pseudo_fs = 1000.0
    pseudo_peaks = (np.cumsum(rri_s) * pseudo_fs).astype(int)
    try:
        td = nk.hrv_time(pseudo_peaks, sampling_rate=pseudo_fs, show=False)
    except Exception:
        td = pd.DataFrame()
    try:
        fd = nk.hrv_frequency(pseudo_peaks, sampling_rate=pseudo_fs, show=False, normalize=False)
    except Exception:
        fd = pd.DataFrame()
    try:
        nl = nk.hrv_nonlinear(pseudo_peaks, sampling_rate=pseudo_fs, show=False)
    except Exception:
        nl = pd.DataFrame()

    def g(df, col):
        if col in df.columns:
            try:
                return float(df[col].iloc[0])
            except Exception:
                return None
        return None

    return {
        "RMSSD": g(td, "HRV_RMSSD"),
        "SDNN": g(td, "HRV_SDNN"),
        "pNN50": g(td, "HRV_pNN50"),
        "LF": g(fd, "HRV_LF"),
        "HF": g(fd, "HRV_HF"),
        "LF_HF": g(fd, "HRV_LFHF"),
        "SD1": g(nl, "HRV_SD1"),
        "SD2": g(nl, "HRV_SD2"),
        "SampEn": g(nl, "HRV_SampEn"),
    }


def icc_2_1(measurements: np.ndarray) -> float:
    """ICC(2,1) two-way random-effects, single-rater absolute agreement."""
    n, k = measurements.shape
    if n < 3 or k != 2:
        return float("nan")
    grand = measurements.mean()
    bms = k * np.var(measurements.mean(axis=1), ddof=1)
    rater_means = measurements.mean(axis=0)
    jms = n * np.sum((rater_means - grand) ** 2) / (k - 1)
    total_ss = np.sum((measurements - grand) ** 2)
    rms_num = total_ss - bms * (n - 1) - jms * (k - 1)
    ems = rms_num / ((n - 1) * (k - 1))
    denom = bms + (k - 1) * ems + (k / n) * (jms - ems)
    if denom <= 0:
        return float("nan")
    return float((bms - ems) / denom)


def bland_altman(a: np.ndarray, b: np.ndarray) -> dict:
    diff = a - b
    mean = (a + b) / 2.0
    bias = float(np.mean(diff))
    sd = float(np.std(diff, ddof=1))
    return {
        "bias": bias,
        "sd_diff": sd,
        "loa_lower": bias - 1.96 * sd,
        "loa_upper": bias + 1.96 * sd,
        "n": int(len(diff)),
        "mean_avg": float(np.mean(mean)),
    }


def main(records=("16265", "16272", "16273", "16420", "16483", "16539", "16773", "16786", "17052", "17453")):
    rows = []
    for rid in records:
        try:
            print(f"Fetching {rid}...", flush=True)
            rr = fetch_rr_intervals(rid)
        except Exception as e:
            print(f"  skip {rid}: {e}")
            continue
        for i, win in enumerate(windowed(rr)):
            try:
                a = metrics_app(win)
                b = metrics_nk(win)
                row = {"record": rid, "window_idx": i, "n_beats": len(win)}
                for k, va in a.items():
                    row[f"app_{k}"] = va
                    row[f"nk_{k}"] = b.get(k)
                rows.append(row)
            except Exception as e:
                print(f"  window {i} failed: {e}")
        print(f"  {rid}: {len(rows)} windows accumulated")
        if len(rows) >= 200:
            break

    df = pd.DataFrame(rows)
    csv_path = OUT_DIR / "benchmark_results.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nWrote {csv_path} with {len(df)} windows.")

    metrics = ["RMSSD", "SDNN", "pNN50", "LF", "HF", "LF_HF", "SD1", "SD2", "SampEn"]
    summary = {}
    for m in metrics:
        a_col = df[f"app_{m}"].astype(float)
        b_col = df[f"nk_{m}"].astype(float)
        valid = a_col.notna() & b_col.notna() & np.isfinite(a_col) & np.isfinite(b_col)
        a = a_col[valid].to_numpy()
        b = b_col[valid].to_numpy()
        if len(a) < 5:
            summary[m] = {"n": int(len(a)), "icc": None, "bland_altman": None}
            continue
        meas = np.stack([a, b], axis=1)
        icc = icc_2_1(meas)
        ba = bland_altman(a, b)
        summary[m] = {"n": int(len(a)), "icc_2_1": icc, "bland_altman": ba}

    with open(OUT_DIR / "benchmark_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote {OUT_DIR / 'benchmark_summary.json'}")
    for m, s in summary.items():
        if s.get("bland_altman"):
            ba = s["bland_altman"]
            print(f"  {m:6s}  n={s['n']:4d}  ICC(2,1)={s.get('icc_2_1', float('nan')):.3f}  bias={ba['bias']:.3f}  LoA=[{ba['loa_lower']:.3f}, {ba['loa_upper']:.3f}]")


if __name__ == "__main__":
    main()
