from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from echarts_component import EChartsConfig, render_echarts
from hrv_core import (
	compute_comprehensive_hrv,
	compute_windowed_hrv,
	load_rr_intervals_from_text,
	psd_curve,
	spectrogram_rr,
)


@dataclass(slots=True)
class UploadedRR:
	name: str
	rr_ms: np.ndarray
	df: pd.DataFrame


def _to_dataframe(name: str, rr_ms: np.ndarray) -> pd.DataFrame:
	if rr_ms.size == 0:
		return pd.DataFrame()
	hr = 60000.0 / rr_ms
	rr_cum_s = np.cumsum(rr_ms) / 1000.0
	start_ts = pd.Timestamp.now().normalize()
	timestamps = start_ts + pd.to_timedelta(rr_cum_s, unit="s")
	df = pd.DataFrame(
		{
			"timestamp": timestamps,
			"rr_intervals_ms": rr_ms,
			"heart_rate [bpm]": hr,
			"beat_index": np.arange(rr_ms.size, dtype=int),
			"source": name,
		}
	)
	return df


def _upload_section() -> Dict[str, UploadedRR]:
	st.sidebar.header("Upload RR (.txt)")
	files = st.sidebar.file_uploader(
		"Select one or more Polar-like RR .txt files (one ms value per line)",
		type=["txt"],
		accept_multiple_files=True,
	)
	out: Dict[str, UploadedRR] = {}
	if not files:
		return out
	for f in files:
		content = f.getvalue().decode("utf-8", errors="ignore")
		rr = load_rr_intervals_from_text(f.name, content)
		df = _to_dataframe(f.name, rr)
		out[f.name] = UploadedRR(name=f.name, rr_ms=rr, df=df)
	return out


def _echarts_line_series(name: str, x_vals: List, y_vals: List, smooth: bool = True) -> Dict:
	return {
		"name": name,
		"type": "line",
		"showSymbol": False,
		"smooth": smooth,
		"data": [[x, y] for x, y in zip(x_vals, y_vals)],
	}


def _echarts_scatter_series(name: str, x_vals: np.ndarray, y_vals: np.ndarray) -> Dict:
	return {
		"name": name,
		"type": "scatter",
		"symbolSize": 4,
		"data": [[float(x), float(y)] for x, y in zip(x_vals, y_vals)],
	}


def _plot_rr_timeseries(datasets: Dict[str, UploadedRR]) -> None:
	series = []
	for name, up in datasets.items():
		if up.df.empty:
			continue
		x = up.df["timestamp"].astype(str).tolist()
		y = up.df["rr_intervals_ms"].astype(float).tolist()
		series.append(_echarts_line_series(name, x, y))
	opt = {
		"title": {"text": "RR Intervals over Time", "left": "center"},
		"tooltip": {"trigger": "axis"},
		"legend": {"top": 24},
		"xAxis": {"type": "time"},
		"yAxis": {"type": "value", "name": "RR (ms)"},
		"dataZoom": [{"type": "inside"}, {"type": "slider"}],
		"series": series,
	}
	render_echarts(opt, height_px=420, config=EChartsConfig())


def _plot_hr_timeseries(datasets: Dict[str, UploadedRR]) -> None:
	series = []
	for name, up in datasets.items():
		if up.df.empty:
			continue
		x = up.df["timestamp"].astype(str).tolist()
		y = up.df["heart_rate [bpm]"].astype(float).tolist()
		series.append(_echarts_line_series(name, x, y))
	opt = {
		"title": {"text": "Heart Rate over Time", "left": "center"},
		"tooltip": {"trigger": "axis"},
		"legend": {"top": 24},
		"xAxis": {"type": "time"},
		"yAxis": {"type": "value", "name": "HR (bpm)"},
		"dataZoom": [{"type": "inside"}, {"type": "slider"}],
		"series": series,
	}
	render_echarts(opt, height_px=420, config=EChartsConfig())


def _plot_psd_overlay(datasets: Dict[str, UploadedRR]) -> None:
	series = []
	for name, up in datasets.items():
		rr = up.rr_ms
		f, p = psd_curve(rr, sampling_rate=4.0)
		if f.size == 0:
			continue
		series.append(
			{
				"name": name,
				"type": "line",
				"showSymbol": False,
				"data": [[float(fi), float(pi)] for fi, pi in zip(f, p)],
			}
		)
	opt = {
		"title": {"text": "PSD Overlay (Welch)", "left": "center"},
		"tooltip": {"trigger": "axis"},
		"legend": {"top": 24},
		"xAxis": {"type": "value", "name": "Frequency (Hz)"},
		"yAxis": {"type": "log", "name": "PSD (ms²/Hz)"},
		"dataZoom": [{"type": "inside"}, {"type": "slider"}],
		"series": series,
		"visualMap": [
			{
				"show": False,
				"type": "continuous",
				"seriesIndex": 0,
				"min": 0.0,
				"max": 0.4,
			}
		],
		"graphic": [
			{"type": "group", "children": []}
		],
	}
	# Band overlays using dataZoom or markArea
	bands = {"VLF": (0.0033, 0.04), "LF": (0.04, 0.15), "HF": (0.15, 0.4)}
	mark_areas = []
	for label, (x0, x1) in bands.items():
		mark_areas.append(
			{
				"name": label,
				"itemStyle": {"color": "rgba(180,180,180,0.15)" if label == "VLF" else ("rgba(255,99,132,0.12)" if label == "LF" else "rgba(99,201,255,0.12)")},
				"label": {"show": True, "position": "insideTopLeft"},
				"data": [[{"xAxis": x0}, {"xAxis": x1}]],
			}
		)
	for s in series:
		s["markArea"] = {"silent": True, "data": [], "itemStyle": {"opacity": 1.0}}
	opt["series"] = series
	opt["markArea"] = mark_areas
	render_echarts(opt, height_px=420, config=EChartsConfig())


def _plot_poincare(datasets: Dict[str, UploadedRR], max_points: int = 5000) -> None:
	series = []
	for name, up in datasets.items():
		rr = up.rr_ms
		if rr.size < 2:
			continue
		rr = rr[(rr >= 300.0) & (rr <= 2000.0)]
		if rr.size < 2:
			continue
		x = rr[:-1]
		y = rr[1:]
		if x.size > max_points:
			idx = np.linspace(0, x.size - 1, max_points).astype(int)
			x = x[idx]
			y = y[idx]
		series.append(_echarts_scatter_series(name, x, y))
	opt = {
		"title": {"text": "Poincaré Plot (RRₙ vs RRₙ₊₁)", "left": "center"},
		"tooltip": {"trigger": "item"},
		"legend": {"top": 24},
		"xAxis": {"type": "value", "name": "RRₙ (ms)"},
		"yAxis": {"type": "value", "name": "RRₙ₊₁ (ms)"},
		"series": series,
	}
	render_echarts(opt, height_px=520, config=EChartsConfig())


def _plot_spectrogram(datasets: Dict[str, UploadedRR]) -> None:
	# Show one spectrogram at a time (select box)
	names = list(datasets.keys())
	if not names:
		return
	sel = st.selectbox("Spectrogram dataset", names, index=0)
	rr = datasets[sel].rr_ms
	fxx, txx, Sxx = spectrogram_rr(rr, sampling_rate=4.0)
	if fxx.size == 0:
		st.info("Insufficient RR for spectrogram.")
		return
	# Convert to [x,y,value] triplets for ECharts heatmap
	points = []
	for j, fy in enumerate(fxx):
		# Restrict to 0–0.5 Hz for readability
		if fy > 0.5:
			continue
		for i, tx in enumerate(txx):
			points.append([float(tx), float(fy), float(Sxx[j, i])])
	opt = {
		"title": {"text": f"RR Spectrogram — {sel}", "left": "center"},
		"tooltip": {"position": "top"},
		"grid": {"height": "70%", "top": "10%"},
		"xAxis": {"type": "value", "name": "Time (s)"},
		"yAxis": {"type": "value", "name": "Frequency (Hz)"},
		"visualMap": {
			"min": float(np.percentile(Sxx, 5)),
			"max": float(np.percentile(Sxx, 95)),
			"calculable": True,
			"orient": "horizontal",
			"left": "center",
			"bottom": 0,
		},
		"series": [
			{"name": "PSD", "type": "heatmap", "data": points, "emphasis": {"itemStyle": {"shadowBlur": 10}}}
		],
	}
	render_echarts(opt, height_px=520, config=EChartsConfig())


def _interpretation(multi_results: pd.DataFrame, windowed: Optional[pd.DataFrame]) -> None:
	if multi_results.empty:
		return
	st.subheader("Interpretation")
	# Short-term, commonly cited anchors
	rmssd_mu, rmssd_sigma = 42.0, 15.0
	sdnn_mu, sdnn_sigma = 50.0, 16.0
	lfhf_mu, lfhf_sigma = 2.8, 2.6

	def pos(value: float, mu: float, sigma: float) -> str:
		if not np.isfinite(value):
			return "n/a"
		lo, hi = mu - sigma, mu + sigma
		return "below" if value < lo else ("above" if value > hi else "within")

	lines: List[str] = []
	for _, row in multi_results.iterrows():
		src = str(row.get("source", "N/A"))
		sdnn = float(row.get("sdnn", np.nan))
		rmssd = float(row.get("rmssd", np.nan))
		lfhf = float(row.get("lf_hf_ratio", np.nan))
		lines.append(
			f"- {src}: SDNN {sdnn:.1f} ms ({pos(sdnn, sdnn_mu, sdnn_sigma)}), "
			f"RMSSD {rmssd:.1f} ms ({pos(rmssd, rmssd_mu, rmssd_sigma)}), "
			f"LF/HF {lfhf:.2f} ({pos(lfhf, lfhf_mu, lfhf_sigma)})"
		)
	st.markdown("\n".join(lines))
	st.caption(
		"References: Task Force 1996; short-term time-domain and spectral anchors are cohort-dependent. "
		"See project Normative.md for more detail."
	)


def main() -> None:
	st.set_page_config(page_title="HRV Analysis — Streamlit + ECharts", layout="wide")
	st.title("HRV Analysis")
	st.caption("Modern, scientific, interactive analysis with Apache ECharts.")
	st.markdown(
		"Using Apache ECharts for high-quality, interactive plots "
		"(see the official handbook: [ECharts Handbook](https://echarts.apache.org/handbook/en/get-started/))."
	)

	uploads = _upload_section()
	if not uploads:
		st.info("Upload one or more RR .txt files to begin.")
		return

	# Controls
	col_a, col_b, col_c = st.sidebar.columns(3)
	with col_a:
		win = st.text_input("Window", "5min")
	with col_b:
		step = st.text_input("Step", "1min")
	with col_c:
		min_rr = st.number_input("Min RR per window", min_value=30, max_value=1000, value=60, step=10)

	# Prepare dataset dict
	datasets = uploads
	st.subheader("Overview")
	meta_rows = []
	for name, up in datasets.items():
		if up.rr_ms.size == 0:
			continue
		meta_rows.append(
			{
				"source": name,
				"beats": int(up.rr_ms.size),
				"duration_min": float(up.rr_ms.sum() / (1000.0 * 60.0)),
				"mean_hr": float(np.mean(60000.0 / up.rr_ms)),
			}
		)
	if meta_rows:
		st.dataframe(pd.DataFrame(meta_rows))

	# Plots
	st.subheader("Time Series")
	_plot_rr_timeseries(datasets)
	_plot_hr_timeseries(datasets)

	st.subheader("Frequency Domain")
	_plot_psd_overlay(datasets)

	st.subheader("Nonlinear")
	_plot_poincare(datasets)

	st.subheader("Time-Frequency (Spectrogram)")
	_plot_spectrogram(datasets)

	# Windowed metrics
	st.subheader("Windowed Metrics (per dataset)")
	windowed_all: List[pd.DataFrame] = []
	for name, up in datasets.items():
		wdf = compute_windowed_hrv(
			up.df,
			window=win,
			step=step,
			min_rr_count=int(min_rr),
		)
		if not wdf.empty:
			windowed_all.append(wdf.assign(source=name))
	if windowed_all:
		windowed_df = pd.concat(windowed_all, ignore_index=True)
		st.dataframe(windowed_df[["start", "source"] + [c for c in windowed_df.columns if c not in ("start", "source")]].head(50))
	else:
		windowed_df = pd.DataFrame()

	# Full-recording metrics
	st.subheader("Full-Recording HRV Metrics")
	multi_results: List[Dict] = []
	for name, up in datasets.items():
		if up.rr_ms.size >= 10:
			m = compute_comprehensive_hrv(up.rr_ms)
			m["source"] = name
			multi_results.append(m)
	multi_results_df = pd.DataFrame(multi_results) if multi_results else pd.DataFrame()
	if not multi_results_df.empty:
		st.dataframe(multi_results_df)

	_interpretation(multi_results_df, windowed_df if not windowed_df.empty else None)


if __name__ == "__main__":
	main()


