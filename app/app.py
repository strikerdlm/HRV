from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import streamlit as st

from echarts_component import EChartsConfig, render_echarts
from hrv_core import (
	compute_comprehensive_hrv,
	compute_windowed_hrv,
	load_rr_intervals_from_text,
	clean_rr_intervals,
	psd_curve,
	spectrogram_rr,
)


@dataclass(slots=True)
class UploadedRR:
	name: str
	rr_ms: np.ndarray
	df: pd.DataFrame
	rr_ms_clean: Optional[np.ndarray] = None
	artifact_valid_mask: Optional[np.ndarray] = None
	qc_summary: Optional[Dict] = None


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


def _plot_rr_timeseries(datasets: Dict[str, UploadedRR], dev_windows: Optional[pd.DataFrame] = None) -> None:
	series = []
	for name, up in datasets.items():
		if up.df.empty:
			continue
		x = up.df["timestamp"].astype(str).tolist()
		y = up.df["rr_intervals_ms"].astype(float).tolist()
		ser = _echarts_line_series(f"{name} (raw)", x, y)
		# Add deviation markAreas per dataset if available
		if dev_windows is not None and not dev_windows.empty and "dev_level" in dev_windows.columns:
			sub = dev_windows[dev_windows["source"] == name]
			if not sub.empty:
				items = []
				for _, row in sub.iterrows():
					start = row.get("start", None)
					end = row.get("end", None)
					level = str(row.get("dev_level", ""))
					if pd.isna(start) or pd.isna(end) or level not in ("yellow", "red"):
						continue
					color = "rgba(251,140,0,0.12)" if level == "yellow" else "rgba(229,57,53,0.12)"
					items.append([
						{"xAxis": str(pd.to_datetime(start)) , "itemStyle": {"color": color}},
						{"xAxis": str(pd.to_datetime(end)) , "itemStyle": {"color": color}},
					])
				if items:
					ser["markArea"] = {"silent": True, "data": items}
		series.append(ser)
		if "rr_intervals_ms_clean" in up.df.columns:
			y_cl = up.df["rr_intervals_ms_clean"].astype(float).tolist()
			series.append(
				{
					**_echarts_line_series(f"{name} (cleaned)", x, y_cl),
					"lineStyle": {"width": 2, "color": "#43a047"},
				}
			)
		if "artifact_flag" in up.df.columns:
			mask = up.df["artifact_flag"].astype(bool).to_numpy()
			if mask.any():
				xf = up.df.loc[mask, "timestamp"].astype(float).to_numpy()
				yf = up.df.loc[mask, "rr_intervals_ms"].astype(float).to_numpy()
				series.append(
					{
						**_echarts_scatter_series(f"{name} artifacts", xf, yf),
						"itemStyle": {"color": "#e53935"},
						"symbolSize": 5,
					}
				)
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


def _plot_psd_overlay(datasets: Dict[str, UploadedRR], *, method: str) -> None:
	series = []
	for name, up in datasets.items():
		rr = up.rr_ms_clean if (up.rr_ms_clean is not None) else up.rr_ms
		f, p = psd_curve(rr, sampling_rate=4.0, method=str(method))
		if f.size == 0:
			continue
		series.append(
			{
				"name": f"{name}{' (cleaned)' if (up.rr_ms_clean is not None) else ''}",
				"type": "line",
				"showSymbol": False,
				"data": [[float(fi), float(pi)] for fi, pi in zip(f, p)],
			}
		)
	opt = {
		"title": {"text": f"PSD Overlay ({method.title()})", "left": "center"},
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
		rr = up.rr_ms_clean if (up.rr_ms_clean is not None) else up.rr_ms
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
	up = datasets[sel]
	rr = up.rr_ms_clean if (up.rr_ms_clean is not None) else up.rr_ms
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


def _compute_deviation_scores(
	windowed_df: pd.DataFrame,
	*,
	metrics: List[str],
	z_warn: float = 1.0,
	z_alert: float = 2.0,
) -> pd.DataFrame:
	"""Compute robust deviation per window by source using median/MAD.

	Returns input DataFrame with added columns:
	- dev_index: max |robust z| across selected metrics
	- dev_level: 'green' | 'yellow' | 'red'
	"""
	if windowed_df.empty or not metrics:
		return windowed_df
	df = windowed_df.copy()
	if "source" not in df.columns or "start" not in df.columns:
		return df
	def _robust_stats(x: pd.Series) -> Tuple[float, float]:
		med = float(np.median(x.values))
		mad = float(np.median(np.abs(x.values - med)))
		return med, mad
	dev_indices: List[float] = []
	for idx, row in df.iterrows():
		src = row.get("source", None)
		if src is None:
			dev_indices.append(0.0)
			continue
		sub = df[df["source"] == src]
		z_vals: List[float] = []
		for mname in metrics:
			if mname not in df.columns or not np.isfinite(row.get(mname, np.nan)):
				continue
			med, mad = _robust_stats(sub[mname].dropna())
			if mad <= 1e-12:
				z = 0.0
			else:
				z = 0.6745 * (float(row[mname]) - med) / mad
			z_vals.append(abs(float(z)))
		dev_indices.append(float(max(z_vals) if z_vals else 0.0))
	df["dev_index"] = dev_indices
	def _level(v: float) -> str:
		return "green" if v < z_warn else ("yellow" if v < z_alert else "red")
	df["dev_level"] = [ _level(v) for v in df["dev_index"].astype(float).tolist() ]
	return df


def _plot_deviation_timeline(windowed_df: pd.DataFrame) -> None:
	if windowed_df.empty or "start" not in windowed_df.columns or "dev_level" not in windowed_df.columns:
		st.info("No deviation data to display.")
		return
	series = []
	colors = {"green": "#43a047", "yellow": "#fb8c00", "red": "#e53935"}
	for src, sub in windowed_df.groupby("source"):
		for level in ["green", "yellow", "red"]:
			ss = sub[sub["dev_level"] == level]
			if ss.empty:
				continue
			data = [[str(x), float(y)] for x, y in zip(ss["start"].astype(str), ss["dev_index"].astype(float))]
			series.append(
				{
					"name": f"{src} — {level}",
					"type": "scatter",
					"symbolSize": 8,
					"itemStyle": {"color": colors[level]},
					"data": data,
				}
			)
	opt = {
		"title": {"text": "Deviation Timeline (max |robust z| across metrics)", "left": "center"},
		"tooltip": {"trigger": "item"},
		"legend": {"top": 24},
		"xAxis": {"type": "time", "name": "Window start"},
		"yAxis": {"type": "value", "name": "Deviation index"},
		"dataZoom": [{"type": "inside"}, {"type": "slider"}],
		"series": series,
		"markLine": {
			"silent": True,
			"data": [
				{"yAxis": 1.0, "lineStyle": {"type": "dashed", "color": "#fb8c00"}},
				{"yAxis": 2.0, "lineStyle": {"type": "dashed", "color": "#e53935"}},
			],
		},
	}
	render_echarts(opt, height_px=360, config=EChartsConfig())


def _gauge_option(title: str, value: float, mu: float, sigma: float, vmin: float, vmax: float, unit: str) -> Dict:
	# Compute band thresholds
	lo = max(vmin, mu - sigma)
	hi = min(vmax, mu + sigma)
	span = max(1e-9, vmax - vmin)
	lo_r = max(0.0, min(1.0, (lo - vmin) / span))
	hi_r = max(0.0, min(1.0, (hi - vmin) / span))
	# Axis line colors: [0..lo]=red, (lo..hi]=green, (hi..1]=orange
	axis_colors = [[lo_r, "#e53935"], [hi_r, "#43a047"], [1.0, "#fb8c00"]]
	return {
		"title": {"text": title, "left": "center"},
		"series": [
			{
				"type": "gauge",
				"min": float(vmin),
				"max": float(vmax),
				"axisLine": {"lineStyle": {"width": 14, "color": axis_colors}},
				"pointer": {"width": 4},
				"splitNumber": 8,
				"progress": {"show": False},
				"detail": {"formatter": f"{value:.1f} {unit}", "fontSize": 14},
				"data": [{"value": float(value)}],
			}
		],
	}


def _render_normogram_gauges(multi_results_df: pd.DataFrame) -> None:
	if multi_results_df.empty:
		st.info("No metrics available for gauges.")
		return
	names = multi_results_df["source"].astype(str).tolist() if "source" in multi_results_df.columns else ["Current"]
	sel = st.selectbox("Select dataset for gauges", names, index=0)
	row = multi_results_df[multi_results_df["source"] == sel].iloc[0] if "source" in multi_results_df.columns else multi_results_df.iloc[0]
	# Anchors from Normative.md (short-term ~5 min)
	sdnn_mu, sdnn_sigma = 50.0, 16.0
	rmssd_mu, rmssd_sigma = 42.0, 15.0
	lfhf_mu, lfhf_sigma = 2.8, 2.6
	hf_mu, hf_sigma = 657.0, 777.0
	# Values
	sdnn = float(row.get("sdnn", np.nan))
	rmssd = float(row.get("rmssd", np.nan))
	lfhf = float(row.get("lf_hf_ratio", np.nan))
	hf_power = float(row.get("hf_power", np.nan))
	# Gauge ranges
	sdnn_vmin, sdnn_vmax = 0.0, 120.0
	rmssd_vmin, rmssd_vmax = 0.0, 100.0
	lfhf_vmin, lfhf_vmax = 0.0, 12.0
	# For HF power, choose a dynamic max to keep needle in range
	hf_vmin, hf_vmax = 0.0, float(max(hf_mu + 3 * hf_sigma, (hf_power if np.isfinite(hf_power) else 0.0) * 1.5, 3000.0))
	cols = st.columns(2)
	with cols[0]:
		render_echarts(_gauge_option("SDNN (ms)", sdnn, sdnn_mu, sdnn_sigma, sdnn_vmin, sdnn_vmax, "ms"), height_px=300, config=EChartsConfig())
	with cols[1]:
		render_echarts(_gauge_option("RMSSD (ms)", rmssd, rmssd_mu, rmssd_sigma, rmssd_vmin, rmssd_vmax, "ms"), height_px=300, config=EChartsConfig())
	cols2 = st.columns(2)
	with cols2[0]:
		render_echarts(_gauge_option("LF/HF (ratio)", lfhf, lfhf_mu, lfhf_sigma, lfhf_vmin, lfhf_vmax, ""), height_px=300, config=EChartsConfig())
	with cols2[1]:
		render_echarts(_gauge_option("HF Power (ms²)", hf_power, hf_mu, hf_sigma, hf_vmin, hf_vmax, "ms²"), height_px=300, config=EChartsConfig())
	# Respiratory rate gauge (derived from HF peak when RSA present)
	resp_bpm = float(row.get("respiratory_rate_bpm", np.nan))
	cols3 = st.columns(1)
	with cols3[0]:
		render_echarts(
			_gauge_option("Respiratory rate (breaths/min)", resp_bpm, 16.0, 4.0, 6.0, 30.0, "breaths/min"),
			height_px=300,
			config=EChartsConfig(),
		)
	st.caption("Bands reflect mean ± SD from short-term (∼5 min) references; see Normative.md for details and caveats.")


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
	# Make the central container and iframes use the full page width
	st.markdown(
		"""
		<style>
		.block-container { max-width: 100% !important; padding-left: 1rem; padding-right: 1rem; }
		iframe { width: 100% !important; }
		</style>
		""",
		unsafe_allow_html=True,
	)
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

	# QC controls
	st.sidebar.markdown("---")
	st.sidebar.subheader("Data Quality")
	apply_clean = st.sidebar.checkbox("Apply artifact correction", value=True)
	method = st.sidebar.selectbox("QC method", ["threshold_median", "threshold_prev"], index=0)
	max_dev = st.sidebar.slider("Deviation threshold", min_value=0.05, max_value=0.5, value=0.2, step=0.05)
	median_win = st.sidebar.number_input("Median window (odd)", min_value=3, max_value=99, value=11, step=2)
	psd_method = st.sidebar.selectbox("PSD method", ["welch", "periodogram", "ar"], index=0)
	st.sidebar.markdown("---")
	st.sidebar.subheader("Deviation detection")
	apply_dev = st.sidebar.checkbox("Detect deviations in windowed metrics", value=True)
	dev_metrics = st.sidebar.multiselect(
		"Metrics to monitor",
		options=["rmssd", "sdnn", "lf_hf_ratio", "hf_power"],
		default=["rmssd", "sdnn", "lf_hf_ratio", "hf_power"],
	)
	z_warn = st.sidebar.slider("Warn threshold (|z|)", min_value=0.5, max_value=3.0, value=1.0, step=0.1)
	z_alert = st.sidebar.slider("Alert threshold (|z|)", min_value=1.0, max_value=5.0, value=2.0, step=0.1)

	# Prepare dataset dict
	datasets = uploads

	# Apply cleaning
	if apply_clean:
		for name, up in datasets.items():
			if up.rr_ms.size == 0:
				continue
			cleaned, valid_mask, summary = clean_rr_intervals(
				up.rr_ms,
				method=str(method),
				max_deviation=float(max_dev),
				median_window=int(median_win),
			)
			up.rr_ms_clean = cleaned
			up.artifact_valid_mask = valid_mask
			up.qc_summary = summary
			if not up.df.empty:
				n = min(len(up.df), cleaned.size)
				up.df.loc[: n - 1, "rr_intervals_ms_clean"] = cleaned[:n]
				if valid_mask.size >= n:
					up.df.loc[: n - 1, "artifact_flag"] = ~valid_mask[:n]
				else:
					up.df["artifact_flag"] = False
	# Compute reusable results
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
				"flagged_pct": float(up.qc_summary.get("flagged_pct", 0.0)) if (apply_clean and up.qc_summary) else 0.0,
			}
		)
	windowed_all: List[pd.DataFrame] = []
	for name, up in datasets.items():
		wdf = compute_windowed_hrv(
			up.df,
			rr_col="rr_intervals_ms_clean" if (apply_clean and "rr_intervals_ms_clean" in up.df.columns) else "rr_intervals_ms",
			window=win,
			step=step,
			min_rr_count=int(min_rr),
		)
		if not wdf.empty:
			windowed_all.append(wdf.assign(source=name))
	if windowed_all:
		windowed_df = pd.concat(windowed_all, ignore_index=True)
		if apply_dev:
			windowed_df = _compute_deviation_scores(windowed_df, metrics=dev_metrics, z_warn=float(z_warn), z_alert=float(z_alert))
	else:
		windowed_df = pd.DataFrame()

	# Full-recording metrics
	multi_results: List[Dict] = []
	for name, up in datasets.items():
		if up.rr_ms.size >= 10:
			use_rr = up.rr_ms_clean if (apply_clean and up.rr_ms_clean is not None) else up.rr_ms
			m = compute_comprehensive_hrv(use_rr)
			m["source"] = name
			if apply_clean and up.qc_summary:
				m["qc_flagged_pct"] = float(up.qc_summary.get("flagged_pct", 0.0))
				m["qc_method"] = str(up.qc_summary.get("qc_method", {}))
			multi_results.append(m)
	multi_results_df = pd.DataFrame(multi_results) if multi_results else pd.DataFrame()

	# Tabs
	tab_overview, tab_ts, tab_freq, tab_nl, tab_tfr, tab_window, tab_metrics, tab_gauges, tab_science, tab_refs, tab_about = st.tabs(
		["Overview", "Time Series", "Frequency", "Nonlinear", "Spectrogram", "Windowed", "Metrics", "Gauges", "Science", "References", "About"]
	)
	with tab_overview:
		if meta_rows:
			st.dataframe(pd.DataFrame(meta_rows))
		# Deviation summary per dataset
		if apply_dev and not windowed_df.empty and "dev_level" in windowed_df.columns:
			summary = (
				windowed_df.groupby("source")["dev_level"]
				.value_counts()
				.unstack(fill_value=0)
				.reindex(columns=["green", "yellow", "red"], fill_value=0)
				.reset_index()
			)
			# Add max deviation index per source for quick scan
			max_dev = windowed_df.groupby("source")["dev_index"].max().rename("max_dev_index")
			summary = summary.merge(max_dev, on="source", how="left")
			st.dataframe(summary.rename(columns={"green":"windows_green","yellow":"windows_yellow","red":"windows_red"}))
		# Show derived respiratory rate when available
		if not multi_results_df.empty and "respiratory_rate_bpm" in multi_results_df.columns:
			st.dataframe(
				multi_results_df[["source", "respiratory_rate_bpm"]].rename(
					columns={"respiratory_rate_bpm": "respiratory_rate [breaths/min]"}
				)
			)
	with tab_ts:
		_plot_rr_timeseries(datasets, dev_windows=windowed_df if (apply_dev and "dev_level" in windowed_df.columns) else None)
		_plot_hr_timeseries(datasets)
		st.markdown(
			"**Scientific notes (time series)**  \n"
			"- RR intervals (ms) are beat-to-beat times; healthy resting dynamics are irregular and complex.  \n"
			"- Heart rate (bpm) is the inverse of RR; variability in RR reflects autonomic modulation.  \n"
			"Short-term norms and physiological context summarized by "
			"[Task Force 1996](https://www.escardio.org/static-file/Escardio/Guidelines/Scientific-Statements/guidelines-Heart-Rate-Variability-FT-1996.pdf) "
			"and updated in [Shaffer & Ginsberg, 2017](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full)."
		)
	with tab_freq:
		_plot_psd_overlay(datasets, method=psd_method)
		st.markdown(
			"**Scientific notes (frequency domain)**  \n"
			"- Bands: VLF 0.0033–0.04 Hz, LF 0.04–0.15 Hz, HF 0.15–0.40 Hz.  \n"
			"- HF indexes respiratory sinus arrhythmia (parasympathetic activity); LF reflects baroreflex and mixed influences; LF/HF has limited validity as a ‘balance’ index and should be interpreted with breathing context.  \n"
			"References: [Task Force 1996](https://www.escardio.org/static-file/Escardio/Guidelines/Scientific-Statements/guidelines-Heart-Rate-Variability-FT-1996.pdf); "
			"[Nunan et al., 2010](https://pubmed.ncbi.nlm.nih.gov/20663071/); "
			"[Shaffer & Ginsberg, 2017](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full)."
		)
	with tab_nl:
		_plot_poincare(datasets)
		st.markdown(
			"**Scientific notes (nonlinear)**  \n"
			"- Poincaré SD1 ≈ RMSSD (short-term vagal modulation); SD2 relates to longer-term variability.  \n"
			"- DFA α1 ≈ 0.75–1.25 at rest reflects healthy fractal-like regulation; lower values can indicate exercise intensity near the aerobic threshold in exertional contexts.  \n"
			"References: [Shaffer & Ginsberg, 2017](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full)."
		)
	with tab_tfr:
		_plot_spectrogram(datasets)
		st.markdown(
			"**Scientific notes (time–frequency)**  \n"
			"- Spectrogram visualizes how spectral power evolves; HF tracks respiration; LF reflects slower autonomic rhythms.  \n"
			"- Stationarity assumptions matter; windowed PSD improves interpretability for long, varying recordings."
		)
	with tab_window:
		st.markdown(
			"**Scientific notes (windowed metrics)**  \n"
			"- Sliding windows (e.g., 5 min, step 1 min) estimate locally stationary segments to track trends over time.  \n"
			"- Minimum RR count safeguards metric stability; interpretation should consider protocol and respiration."
		)
		if not windowed_df.empty:
			st.dataframe(windowed_df[["start", "source"] + [c for c in windowed_df.columns if c not in ("start", "source")]].head(50))
			if apply_dev and "dev_level" in windowed_df.columns:
				st.markdown("Deviation timeline across selected metrics (green < warn, yellow ≥ warn, red ≥ alert):")
				_plot_deviation_timeline(windowed_df)
		else:
			st.info("No windowed metrics to display.")
	with tab_metrics:
		if not multi_results_df.empty:
			st.dataframe(multi_results_df)
		else:
			st.info("No metrics to display.")
	with tab_gauges:
		_render_normogram_gauges(multi_results_df)
		st.markdown(
			"**Scientific notes (normogram gauges)**  \n"
			"- Gauges compare observed values to short-term (∼5 min) population references (mean ± SD).  \n"
			"- Cohort, age, posture, and breathing materially shift distributions; use within-subject trends for decisions.  \n"
			"References: [Nunan et al., 2010](https://pubmed.ncbi.nlm.nih.gov/20663071/); "
			"[Sammito & Böckelmann, 2016](https://pubmed.ncbi.nlm.nih.gov/27986557/)."
		)
	with tab_science:
		st.markdown(
			"- **Time-domain (SDNN, RMSSD)**: Short-term SDNN (~5 min) ≈ 50±16 ms; RMSSD ≈ 42±15 ms in healthy adults; both decrease with age. RMSSD reflects vagal (parasympathetic) activity.\n"
			"- **Frequency-domain (LF/HF)**: LF (0.04–0.15 Hz), HF (0.15–0.40 Hz). LF/HF (~2.8±2.6) has limitations as a sympathovagal balance index; interpret with breathing context.\n"
			"- **Nonlinear (Poincaré, DFA)**: SD1≈RMSSD; SD2 relates to longer-term variability. DFA α1 in 0.75–1.25 is typical at rest.\n\n"
			"Key references: "
			"[Task Force 1996](https://www.escardio.org/static-file/Escardio/Guidelines/Scientific-Statements/guidelines-Heart-Rate-Variability-FT-1996.pdf), "
			"[Shaffer & Ginsberg 2017](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full), "
			"[Nunan et al. 2010](https://pubmed.ncbi.nlm.nih.gov/20663071/)."
		)
	with tab_about:
		st.markdown(
			"### About the Author\n"
			"**Dr. Diego Leonel Malpica Hincapié** — Aerospace Medicine (Colombia)\n\n"
			"- Professional service within Colombian Military Health / Fuerza Aérea Colombiana (public record).\n"
			"- Focus areas: aerospace medicine, operational performance, fatigue, psychophysiology, and HRV.\n"
			"- This app and analysis workflow were authored and curated by Dr. Malpica.\n\n"
			"Sources:\n"
			"- SIGEP II — Función Pública (public record): "
			"[profile link](https://www.funcionpublica.gov.co/web/sigep/hdv/-/directorio/S767357-8012-4/view)\n"
			"- Related academic listing with name occurrence: "
			"[Redalyc article page](https://www.redalyc.org/journal/6735/673573283005/movil/)\n\n"
			"Project links:\n"
			"- GitHub repository: https://github.com/strikerdlm/HRV\n"
			"- HRV Normative review in this project: `docs/Normative.md`\n"
			"- Charting: [Apache ECharts](https://echarts.apache.org/handbook/en/get-started/)\n\n"
			"Notes:\n"
			"- HRV interpretation is protocol- and cohort-dependent. Use within-subject trends and documented context "
			"(posture, time-of-day, respiration) for decisions.\n"
		)
	with tab_refs:
		st.markdown(
			"**Selected references (APA format)**  \n"
			"- Malik, M., Bigger, J. T., Camm, A. J., Kleiger, R. E., Malliani, A., Moss, A. J., & Schwartz, P. J. (1996). Heart rate variability: Standards of measurement, physiological interpretation, and clinical use. European Heart Journal, 17(3), 354–381. "
			"https://www.escardio.org/static-file/Escardio/Guidelines/Scientific-Statements/guidelines-Heart-Rate-Variability-FT-1996.pdf  \n"
			"- Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability metrics and norms. Frontiers in Public Health, 5, 258. "
			"https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full  \n"
			"- Nunan, D., Sandercock, G. R. H., & Brodie, D. A. (2010). A quantitative systematic review of normal values for short-term heart rate variability in healthy adults. Pacing and Clinical Electrophysiology, 33(11), 1407–1417. https://pubmed.ncbi.nlm.nih.gov/20663071/  \n"
			"- Quigley, K. S., Berntson, G. G., Gianaros, P. J., Jennings, J. R., Norman, G. J., Thayer, J. F., & de Geus, E. (2024). Publication guidelines for human heart rate and heart rate variability studies in psychophysiology—Part 1: Physiological underpinnings and foundations of measurement. Psychophysiology. https://onlinelibrary.wiley.com/doi/10.1111/psyp.14604  \n"
			"- Laborde, S., Mosley, E., & Thayer, J. F. (2017). Heart rate variability and cardiac vagal tone in psychophysiological research—Recommendations for experiment planning, data analysis, and data reporting. Frontiers in Psychology, 8, 213. "
			"https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2017.00213/full  \n"
			"- Sammito, S., & Böckelmann, I. (2016). Reference values for time- and frequency-domain heart rate variability measures. Heart Rhythm, 13(6), 1309–1316. https://pubmed.ncbi.nlm.nih.gov/27986557/  \n"
			"- Berkoff, D. J., Cairns, C. B., Sanchez, L. D., & Moorman, C. T. (2007). Heart rate variability in elite American track-and-field athletes. Journal of Strength and Conditioning Research, 21(1), 227–231. https://pubmed.ncbi.nlm.nih.gov/17313294/"
		)


if __name__ == "__main__":
	main()


