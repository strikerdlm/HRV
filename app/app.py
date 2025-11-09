from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import os
import sys
import logging

# Windows console safety to mitigate Colorama/Click re-entrancy during shutdown
if os.name == "nt":
	try:
		# Disable colored console to avoid nested writes on shutdown
		os.environ.setdefault("CLICOLOR", "0")
		os.environ.setdefault("NO_COLOR", "1")
		import colorama  # type: ignore
		colorama.just_fix_windows_console()
	except Exception:
		pass

from echarts_component import EChartsConfig, render_echarts
from export_utils import ExportConfiguration, ExportScope, build_markdown_report
from ml_enhancements import run_windowed_kmeans
from hrv_core import (
	build_readiness_baseline,
	clean_rr_intervals,
	compute_30_15_ratio,
	compute_comprehensive_hrv,
	compute_deep_breathing_response,
	compute_valsalva_ratio,
	compute_windowed_hrv,
	load_rr_intervals_from_text,
	psd_curve,
	readiness_from_pns,
	spectrogram_rr,
)


def setup_console_logging(level: int = logging.INFO) -> logging.Logger:
	"""
	Configure an application logger that writes to stderr with a stable format.
	This function is idempotent across Streamlit reruns: it clears
	existing handlers on the application logger to avoid duplicate
	messages.

	Parameters
	----------
	level : int
		Logging level to apply (e.g., logging.INFO, logging.DEBUG).

	Returns
	-------
	logging.Logger
		Configured logger instance for the application.

	Raises
	------
	TypeError
		If 'level' is not an int logging level.
	"""
	if not isinstance(level, int):
		raise TypeError("level must be an int logging level")
	app_logger = logging.getLogger("hrv_app")
	app_logger.propagate = False
	# Clear existing handlers to prevent duplicates after Streamlit reruns
	for handler in list(app_logger.handlers):
		app_logger.removeHandler(handler)

	stream_handler = logging.StreamHandler(stream=sys.stderr)
	stream_handler.setLevel(level)
	formatter = logging.Formatter(
		fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
		datefmt="%H:%M:%S",
	)
	stream_handler.setFormatter(formatter)

	app_logger.addHandler(stream_handler)
	app_logger.setLevel(level)

	# Route Python warnings to logging so they appear in the console too
	logging.captureWarnings(True)

	return app_logger


@st.cache_data(show_spinner=False)
def _cached_comprehensive(rr: np.ndarray, include_advanced: bool) -> Dict[str, Any]:
	return compute_comprehensive_hrv(rr, include_advanced=include_advanced)


@st.cache_data(show_spinner=False)
def _cached_psd(rr: np.ndarray, method: str) -> Tuple[np.ndarray, np.ndarray]:
	return psd_curve(rr, sampling_rate=4.0, method=method)


@st.cache_data(show_spinner=False)
def _cached_windowed(
	df: pd.DataFrame,
	rr_col: str,
	window: str,
	step: str,
	min_rr_count: int,
	max_windows: int,
	include_advanced: bool,
) -> pd.DataFrame:
	try:
		return compute_windowed_hrv(
			df,
			rr_col=rr_col,
			window=window,
			step=step,
			min_rr_count=min_rr_count,
			max_windows=max_windows,
			include_advanced=include_advanced,
		)
	except TypeError:
		# Backward-compat fallback if the imported function does not accept include_advanced
		return compute_windowed_hrv(
			df,
			rr_col=rr_col,
			window=window,
			step=step,
			min_rr_count=min_rr_count,
			max_windows=max_windows,
		)


@st.cache_data(show_spinner=False)
def _cached_spectrogram(rr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
	return spectrogram_rr(rr, sampling_rate=4.0)


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
	points: List[List[Any]] = []
	for x, y in zip(x_vals, y_vals):
		if isinstance(x, (int, float, np.number)):
			x_value: Any = float(x)
		else:
			x_value = str(x)
		points.append([x_value, float(y)])
	return {
		"name": name,
		"type": "scatter",
		"symbolSize": 4,
		"data": points,
	}


def _prepare_rr_series(upload: UploadedRR, use_clean: bool) -> Tuple[pd.Series, pd.Series]:
	"""Return aligned timestamp and RR interval series for a dataset."""
	if upload.df.empty:
		raise ValueError(f"Dataset '{upload.name}' contains no RR samples.")
	column = "rr_intervals_ms_clean" if (use_clean and "rr_intervals_ms_clean" in upload.df.columns) else "rr_intervals_ms"
	if column not in upload.df.columns:
		raise ValueError(f"Column '{column}' not available for dataset '{upload.name}'.")
	timestamps = pd.to_datetime(upload.df["timestamp"], errors="coerce")
	rr_ms = pd.to_numeric(upload.df[column], errors="coerce")
	mask = timestamps.notna() & rr_ms.notna()
	if not mask.any():
		raise ValueError(f"No valid RR samples found for dataset '{upload.name}'.")
	return timestamps.loc[mask], rr_ms.loc[mask]


def _parse_window_seconds(raw_value: str, label: str) -> Tuple[float, float]:
	"""Parse a window definition string into a (start, end) tuple of seconds."""
	if not raw_value.strip():
		raise ValueError(f"{label} cannot be empty.")
	clean = raw_value.strip()
	for sep in (",", ";"):
		clean = clean.replace(sep, " ")
	parts: List[str] = []
	for token in clean.split():
		if "-" in token:
			subparts = [segment for segment in token.split("-") if segment]
			parts.extend(subparts)
		else:
			parts.append(token)
	if len(parts) != 2:
		raise ValueError(f"{label} must specify exactly two numbers (start and end seconds).")
	try:
		start = float(parts[0])
		end = float(parts[1])
	except ValueError as exc:  # pragma: no cover - defensive
		raise ValueError(f"{label} must contain numeric values.") from exc
	if not np.isfinite(start) or not np.isfinite(end):
		raise ValueError(f"{label} must contain finite values.")
	if end <= start:
		raise ValueError(f"{label} end must be greater than start.")
	return start, end


def _parse_float(raw_value: float | int | str, label: str) -> float:
	"""Parse a float input ensuring finiteness."""
	try:
		value = float(raw_value)
	except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
		raise ValueError(f"{label} must be a number.") from exc
	if not np.isfinite(value):
		raise ValueError(f"{label} must be finite.")
	return value


def _plot_rr_timeseries(datasets: Dict[str, UploadedRR], dev_windows: Optional[pd.DataFrame] = None, *, max_points: Optional[int] = None) -> None:
	series = []
	x_min: Optional[pd.Timestamp] = None
	x_max: Optional[pd.Timestamp] = None
	for name, up in datasets.items():
		if up.df.empty:
			continue
		ts_ser = pd.to_datetime(up.df["timestamp"], errors="coerce").dropna()
		if not ts_ser.empty:
			cur_min = ts_ser.iloc[0]
			cur_max = ts_ser.iloc[-1]
			x_min = cur_min if (x_min is None or cur_min < x_min) else x_min
			x_max = cur_max if (x_max is None or cur_max > x_max) else x_max
		x_vals = up.df["timestamp"].astype(str).tolist()
		y_vals = up.df["rr_intervals_ms"].astype(float).tolist()
		if max_points is not None and len(y_vals) > max_points:
			idx = np.linspace(0, len(y_vals) - 1, max_points).astype(int)
			x = [x_vals[i] for i in idx]
			y = [y_vals[i] for i in idx]
		else:
			x = x_vals
			y = y_vals
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
			y_cl_vals = up.df["rr_intervals_ms_clean"].astype(float).tolist()
			if max_points is not None and len(y_cl_vals) > max_points:
				y_cl = [y_cl_vals[i] for i in idx]
			else:
				y_cl = y_cl_vals
			series.append(
				{
					**_echarts_line_series(f"{name} (cleaned)", x, y_cl),
					"lineStyle": {"width": 2, "color": "#43a047"},
				}
			)
		if "artifact_flag" in up.df.columns:
			mask_series = up.df["artifact_flag"].fillna(False)
			mask = mask_series.astype(bool).to_numpy()
			if mask.any():
				timestamps_masked = up.df.loc[mask, "timestamp"]
				rr_masked = pd.to_numeric(up.df.loc[mask, "rr_intervals_ms"], errors="coerce")
				valid_mask = rr_masked.notna()
				if valid_mask.any():
					xf = timestamps_masked.loc[valid_mask].astype(str).to_numpy()
					yf = rr_masked.loc[valid_mask].to_numpy(dtype=float)
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
		"grid": {"left": 32, "right": 16, "containLabel": True},
		"xAxis": {
			"type": "time",
			"boundaryGap": False,
			**({"min": str(x_min)} if x_min is not None else {}),
			**({"max": str(x_max)} if x_max is not None else {}),
		},
		"yAxis": {"type": "value", "name": "RR (ms)"},
		"dataZoom": [{"type": "inside"}, {"type": "slider", "left": 32, "right": 16}],
		"series": series,
	}
	render_echarts(opt, height_px=420, width="100%", config=EChartsConfig())


def _plot_hr_timeseries(datasets: Dict[str, UploadedRR]) -> None:
	series = []
	x_min: Optional[pd.Timestamp] = None
	x_max: Optional[pd.Timestamp] = None
	for name, up in datasets.items():
		if up.df.empty:
			continue
		ts_ser = pd.to_datetime(up.df["timestamp"], errors="coerce").dropna()
		if not ts_ser.empty:
			cur_min = ts_ser.iloc[0]
			cur_max = ts_ser.iloc[-1]
			x_min = cur_min if (x_min is None or cur_min < x_min) else x_min
			x_max = cur_max if (x_max is None or cur_max > x_max) else x_max
		x = up.df["timestamp"].astype(str).tolist()
		y = up.df["heart_rate [bpm]"].astype(float).tolist()
		series.append(_echarts_line_series(name, x, y))
	opt = {
		"title": {"text": "Heart Rate over Time", "left": "center"},
		"tooltip": {"trigger": "axis"},
		"legend": {"top": 24},
		"grid": {"left": 32, "right": 16, "containLabel": True},
		"xAxis": {
			"type": "time",
			"boundaryGap": False,
			**({"min": str(x_min)} if x_min is not None else {}),
			**({"max": str(x_max)} if x_max is not None else {}),
		},
		"yAxis": {"type": "value", "name": "HR (bpm)"},
		"dataZoom": [{"type": "inside"}, {"type": "slider", "left": 32, "right": 16}],
		"series": series,
	}
	render_echarts(opt, height_px=420, width="100%", config=EChartsConfig())


def _plot_psd_overlay(datasets: Dict[str, UploadedRR], *, method: str) -> None:
	series = []
	for name, up in datasets.items():
		rr = up.rr_ms_clean if (up.rr_ms_clean is not None) else up.rr_ms
		f, p = _cached_psd(rr, method=str(method))
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
		"grid": {"left": 32, "right": 16, "containLabel": True},
		"xAxis": {"type": "value", "name": "Frequency (Hz)", "boundaryGap": False},
		"yAxis": {"type": "log", "name": "PSD (ms²/Hz)"},
		"dataZoom": [{"type": "inside"}, {"type": "slider", "left": 32, "right": 16}],
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
	render_echarts(opt, height_px=420, width="100%", config=EChartsConfig())


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
		"grid": {"left": 32, "right": 16, "containLabel": True},
		"xAxis": {"type": "value", "name": "RRₙ (ms)", "boundaryGap": False},
		"yAxis": {"type": "value", "name": "RRₙ₊₁ (ms)"},
		"series": series,
	}
	render_echarts(opt, height_px=520, width="100%", config=EChartsConfig())


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
		"grid": {"height": "70%", "top": "10%", "left": 32, "right": 16, "containLabel": True},
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
	render_echarts(opt, height_px=520, width="100%", config=EChartsConfig())


def _compute_deviation_scores(
	windowed_df: pd.DataFrame,
	*,
	metrics: List[str],
	z_warn: float = 1.0,
	z_alert: float = 2.0,
) -> pd.DataFrame:
	"""Compute robust deviation per window by source using median/MAD (vectorized)."""
	if windowed_df.empty or not metrics:
		return windowed_df
	df = windowed_df.copy()
	if "source" not in df.columns or "start" not in df.columns:
		return df
	metrics_present = [m for m in metrics if m in df.columns]
	if not metrics_present:
		df["dev_index"] = 0.0
		df["dev_level"] = "green"
		return df

	# Vectorized robust z for each metric
	z_cols: List[str] = []
	for mname in metrics_present:
		val = pd.to_numeric(df[mname], errors="coerce")
		med = df.groupby("source")[mname].transform(lambda x: float(np.median(pd.to_numeric(x, errors="coerce").dropna())))
		mad = df.groupby("source")[mname].transform(lambda x: float(np.median(np.abs(pd.to_numeric(x, errors="coerce").dropna() - np.median(pd.to_numeric(x, errors="coerce").dropna())))))
		# Avoid division by zero; if MAD=0 treat as zero deviation around median
		mad_safe = mad.replace(0, np.nan)
		z = 0.6745 * (val - med) / mad_safe
		z_abs = z.abs().fillna(0.0)
		col = f"__z_{mname}"
		df[col] = z_abs
		z_cols.append(col)

	df["dev_index"] = df[z_cols].max(axis=1) if z_cols else 0.0
	df.drop(columns=z_cols, inplace=True, errors="ignore")
	df["dev_level"] = np.where(
		df["dev_index"] < float(z_warn),
		"green",
		np.where(df["dev_index"] < float(z_alert), "yellow", "red"),
	)
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
		"grid": {"left": 32, "right": 16, "containLabel": True},
		"xAxis": {"type": "time", "name": "Window start", "boundaryGap": False},
		"yAxis": {"type": "value", "name": "Deviation index"},
		"dataZoom": [{"type": "inside"}, {"type": "slider", "left": 32, "right": 16}],
		"series": series,
		"markLine": {
			"silent": True,
			"data": [
				{"yAxis": 1.0, "lineStyle": {"type": "dashed", "color": "#fb8c00"}},
				{"yAxis": 2.0, "lineStyle": {"type": "dashed", "color": "#e53935"}},
			],
		},
	}
	render_echarts(opt, height_px=360, width="100%", config=EChartsConfig())


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
	logger: logging.Logger = setup_console_logging(logging.INFO)
	# Streamlit detailed tracebacks in the UI and console
	st.set_option("client.showErrorDetails", True)
	st.set_page_config(page_title="HRV Analysis — Streamlit + ECharts", layout="wide")
	# Make the central container and iframes use the full page width
	st.markdown(
		"""
		<style>
		.block-container { max-width: 100% !important; padding-left: 0; padding-right: 0; }
		div[data-testid="stIFrame"] { width: 100% !important; }
		div[data-testid="stIFrame"] > iframe { width: 100% !important; }
		[title~="st.iframe"] { width: 100% !important; }
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
	max_windows = st.sidebar.number_input("Max windows (for long tracings)", min_value=200, max_value=20000, value=1500, step=100)

	# QC controls
	st.sidebar.markdown("---")
	st.sidebar.subheader("Data Quality")
	apply_clean = st.sidebar.checkbox("Apply artifact correction", value=True)
	method = st.sidebar.selectbox("QC method", ["threshold_median", "threshold_prev"], index=0)
	max_dev = st.sidebar.slider("Deviation threshold", min_value=0.05, max_value=0.5, value=0.2, step=0.05)
	median_win = st.sidebar.number_input("Median window (odd)", min_value=3, max_value=99, value=11, step=2)
	psd_method = st.sidebar.selectbox("PSD method", ["welch", "periodogram", "ar"], index=0)
	fast_windowing = st.sidebar.checkbox("Fast time-domain windowing (skip spectral/nonlinear in windows)", value=True)
	high_compute = st.sidebar.checkbox("Advanced analysis (high compute for full-recording metrics)", value=False)
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
	min_sustain = st.sidebar.number_input("Min windows to define an episode", min_value=1, max_value=60, value=3, step=1)
	st.sidebar.markdown("---")
	st.sidebar.subheader("Performance & display")
	minimal_mode = st.sidebar.checkbox("Minimal mode (fastest)", value=True)
	max_datasets = st.sidebar.number_input("Process first N datasets", min_value=1, value=3, step=1)
	rr_plot_cap = st.sidebar.selectbox("RR plot point cap per dataset", ["500","2000","10000","No limit"], index=1)
	skip_freq = st.sidebar.checkbox("Skip Frequency overlay plot", value=True)
	skip_poincare = st.sidebar.checkbox("Skip Poincaré plot", value=True)
	skip_spectrogram = st.sidebar.checkbox("Skip Spectrogram", value=True)
	skip_gauges = st.sidebar.checkbox("Skip Gauges", value=False)
	show_debug = st.sidebar.checkbox("Show detailed progress logs", value=False)
	# Adjust runtime log verbosity from sidebar preference
	logger.setLevel(logging.DEBUG if show_debug else logging.INFO)
	for _handler in logger.handlers:
		_handler.setLevel(logger.level)

	st.sidebar.subheader("ML enhancements")
	enable_ml = st.sidebar.checkbox("Enable ML-assisted deviation clustering", value=False)
	st.sidebar.markdown("---")
	st.sidebar.subheader("Patient profile (covariate adjustment)")
	enable_cov = st.sidebar.checkbox("Enable covariate adjustment (RMSSD/SDNN)", value=False)
	age_years = st.sidebar.number_input("Age (years)", min_value=10, max_value=100, value=45, step=1)
	sex = st.sidebar.selectbox("Sex", ["Female", "Male"], index=1)
	bmi = st.sidebar.number_input("BMI (kg/m²)", min_value=10.0, max_value=60.0, value=29.0, step=0.5)
	exercise = st.sidebar.selectbox("Exercise regularity", ["Sedentary", "Moderate", "Athlete"], index=0)

	# Apply minimal mode overrides to ensure fastest behavior by default
	if minimal_mode:
		max_datasets = 1
		rr_plot_cap = "500"
		skip_freq = True
		skip_poincare = True
		skip_spectrogram = True
		skip_gauges = True
		fast_windowing = True
		high_compute = False
		max_windows = min(int(max_windows), 800)
		enable_ml = False
		st.sidebar.caption("Minimal mode: processing 1 dataset, fast time-domain windowing, heavy plots/tabs skipped.")

	# Prepare dataset dict (limit number of datasets for performance)
	datasets_all = uploads
	dataset_items = list(datasets_all.items())
	datasets = dict(dataset_items[: int(max_datasets)])

	# Cleaning + metadata with immediate percentage updates (no progress bars)
	total = max(1, len(datasets))
	txt_clean = st.empty()
	txt_clean.text(("Cleaning datasets... " if apply_clean else "Preparing datasets... ") + "0%")
	logger.info("Starting %s of %d dataset(s)", "cleaning" if apply_clean else "preparation", total)
	meta_rows = []
	completed = 0
	for name, up in datasets.items():
		if up.rr_ms.size == 0:
			completed += 1
			txt_clean.text(
				("Cleaning datasets... " if apply_clean else "Preparing datasets... ")
				+ f"{min(100, int(completed * 100 / total))}%"
			)
			continue
		if apply_clean:
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
		meta_rows.append(
			{
				"source": name,
				"beats": int(up.rr_ms.size),
				"duration_min": float(up.rr_ms.sum() / (1000.0 * 60.0)),
				"mean_hr": float(np.mean(60000.0 / up.rr_ms)),
				"flagged_pct": float(up.qc_summary.get("flagged_pct", 0.0)) if (apply_clean and up.qc_summary) else 0.0,
			}
		)
		completed += 1
		txt_clean.text(
			("Cleaning datasets... " if apply_clean else "Preparing datasets... ")
			+ f"{min(100, int(completed * 100 / total))}%"
		)
	logger.info("Finished %s of %d dataset(s)", "cleaning" if apply_clean else "preparation", total)
	txt_clean.text(("Cleaning complete." if apply_clean else "Preparation complete.") + " 100%")

	windowed_all: List[pd.DataFrame] = []
	txt_win = st.empty()
	txt_win.text("Computing windowed metrics... 0%")
	total_win = max(1, len(datasets))
	done_win = 0
	for name, up in datasets.items():
		wdf = _cached_windowed(
			up.df,
			rr_col="rr_intervals_ms_clean" if (apply_clean and "rr_intervals_ms_clean" in up.df.columns) else "rr_intervals_ms",
			window=win,
			step=step,
			min_rr_count=int(min_rr),
			max_windows=int(max_windows),
			include_advanced=not bool(fast_windowing),
		)
		if not wdf.empty:
			windowed_all.append(wdf.assign(source=name))
		done_win += 1
		txt_win.text("Computing windowed metrics... " + f"{min(100, int(done_win * 100 / total_win))}%")
	if windowed_all:
		windowed_df = pd.concat(windowed_all, ignore_index=True)
		if apply_dev:
			windowed_df = _compute_deviation_scores(windowed_df, metrics=dev_metrics, z_warn=float(z_warn), z_alert=float(z_alert))
	else:
		windowed_df = pd.DataFrame()
	txt_win.text("Computing windowed metrics... 100%")

	ml_summary_df = pd.DataFrame()
	ml_error_message = ""
	if enable_ml and not windowed_df.empty:
		ml_metrics = list(dev_metrics) if dev_metrics else ["rmssd", "sdnn", "lf_hf_ratio", "hf_power"]
		try:
			ml_result = run_windowed_kmeans(
				windowed_df,
				ml_metrics,
				n_clusters=2,
				max_iterations=50,
			)
		except ValueError as exc:
			logger.warning("ML clustering failed: %s", exc, exc_info=True)
			ml_error_message = str(exc)
		else:
			windowed_df = ml_result.windowed_with_clusters
			ml_summary_df = ml_result.cluster_summary

	# Aggregate anomaly episodes (contiguous yellow/red windows)
	def _episodes(df: pd.DataFrame, min_len: int) -> pd.DataFrame:
		if df.empty or "dev_level" not in df.columns:
			return pd.DataFrame()
		out = []
		step_td = pd.to_timedelta(step)
		for src, sub in df.sort_values(["source","start"]).groupby("source"):
			cur_level = None
			cur_start = None
			cur_end = None
			cur_count = 0
			cur_max = 0.0
			prev_start = None
			for _, r in sub.iterrows():
				level = str(r.get("dev_level","green"))
				if level == "green":
					level = None
				start_ts = pd.to_datetime(r.get("start"))
				end_ts = pd.to_datetime(r.get("end"))
				if cur_level is None and level is not None:
					cur_level = level
					cur_start = start_ts
					cur_end = end_ts
					cur_count = 1
					cur_max = float(r.get("dev_index", 0.0))
				elif cur_level is not None:
					# continue if same level and contiguous
					if level == cur_level and prev_start is not None and (start_ts - prev_start) <= step_td * 1.5:
						cur_end = end_ts
						cur_count += 1
						cur_max = max(cur_max, float(r.get("dev_index", 0.0)))
					else:
						if cur_count >= int(min_len):
							out.append({"source": src, "level": cur_level, "start": cur_start, "end": cur_end, "n_windows": cur_count, "max_dev_index": cur_max})
						cur_level = level
						cur_start = start_ts if level is not None else None
						cur_end = end_ts if level is not None else None
						cur_count = 1 if level is not None else 0
						cur_max = float(r.get("dev_index", 0.0)) if level is not None else 0.0
				prev_start = start_ts
			if cur_level is not None and cur_count >= int(min_len):
				out.append({"source": src, "level": cur_level, "start": cur_start, "end": cur_end, "n_windows": cur_count, "max_dev_index": cur_max})
		return pd.DataFrame(out)

	episodes_df = _episodes(windowed_df, int(min_sustain)) if (apply_dev and not windowed_df.empty and "dev_level" in windowed_df.columns) else pd.DataFrame()

	# Full-recording metrics
	multi_results: List[Dict] = []
	ordered_sources: List[str] = []
	txt_full = st.empty()
	txt_full.text("Computing full-recording metrics... 0%")

	total_full = max(1, len(datasets))
	done_full = 0
	for name, up in datasets.items():
		if up.rr_ms.size >= 10:
			use_rr = up.rr_ms_clean if (apply_clean and up.rr_ms_clean is not None) else up.rr_ms
			m = _cached_comprehensive(use_rr, include_advanced=bool(high_compute))
			m["source"] = name
			if apply_clean and up.qc_summary:
				m["qc_flagged_pct"] = float(up.qc_summary.get("flagged_pct", 0.0))
				m["qc_method"] = str(up.qc_summary.get("qc_method", {}))
			if enable_cov:
				from hrv_core import covariate_adjust_short_term as _cov
				adj = _cov(
					age_years=int(age_years),
					sex=str(sex),
					bmi=float(bmi),
					exercise_level=str(exercise),
					rmssd=float(m.get("rmssd", np.nan)),
					sdnn=float(m.get("sdnn", np.nan)),
				)
				m.update(adj)
			multi_results.append(m)
			ordered_sources.append(name)
			done_full += 1
			txt_full.text("Computing full-recording metrics... " + f"{min(100, int(done_full * 100 / total_full))}%")
	txt_full.text("Computing full-recording metrics... 100%")
	multi_results_df = pd.DataFrame(multi_results) if multi_results else pd.DataFrame()

	# Long-term summaries (5-min windows): SDANN (std of mean_nni), SDNNIDX (mean of window SDNN)
	if not windowed_df.empty and "mean_nni" in windowed_df.columns and "sdnn" in windowed_df.columns:
		lts = (
			windowed_df.groupby("source")
			.agg(sdann_5min=("mean_nni", lambda x: float(np.std(pd.to_numeric(x, errors="coerce").dropna(), ddof=1))),
			     sdnnidx_5min=("sdnn", lambda x: float(np.mean(pd.to_numeric(x, errors="coerce").dropna()))))
			.reset_index()
		)
		if not multi_results_df.empty:
			multi_results_df = multi_results_df.merge(lts, on="source", how="left")

	pns_mapping: Dict[str, float] = {}
	if not multi_results_df.empty and "parasympathetic_index" in multi_results_df.columns:
		for src in ordered_sources:
			row = multi_results_df[multi_results_df["source"] == src]
			if row.empty:
				continue
			val = float(row["parasympathetic_index"].iloc[0])
			if np.isfinite(val):
				pns_mapping[src] = val

	# Tabs
	tab_overview, tab_ts, tab_freq, tab_nl, tab_tfr, tab_window, tab_metrics, tab_ans, tab_readiness, tab_gauges, tab_science, tab_export, tab_refs, tab_about = st.tabs(
		[
			"Overview",
			"Time Series",
			"Frequency",
			"Nonlinear",
			"Spectrogram",
			"Windowed",
			"Metrics",
			"ANS Function Tests",
			"Readiness",
			"Gauges",
			"Science",
			"Export",
			"References",
			"About",
		]
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
		max_pts = None if rr_plot_cap == "No limit" else int(rr_plot_cap)
		_plot_rr_timeseries(datasets, dev_windows=windowed_df if (apply_dev and "dev_level" in windowed_df.columns) else None, max_points=max_pts)
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
		if skip_freq:
			st.info("Frequency overlay disabled (Performance & display).")
		else:
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
		if skip_poincare:
			st.info("Poincaré plot disabled (Performance & display).")
		else:
			_plot_poincare(datasets)
		st.markdown(
			"**Scientific notes (nonlinear)**  \n"
			"- Poincaré SD1 ≈ RMSSD (short-term vagal modulation); SD2 relates to longer-term variability.  \n"
			"- DFA α1 ≈ 0.75–1.25 at rest reflects healthy fractal-like regulation; lower values can indicate exercise intensity near the aerobic threshold in exertional contexts.  \n"
			"References: [Shaffer & Ginsberg, 2017](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2017.00258/full)."
		)
	with tab_tfr:
		if skip_spectrogram:
			st.info("Spectrogram disabled (Performance & display).")
		else:
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
				if not episodes_df.empty:
					st.markdown("Anomaly episodes (contiguous yellow/red windows):")
					st.dataframe(episodes_df.sort_values(["source","start"]))
			if enable_ml:
				if ml_summary_df.empty:
					if ml_error_message:
						st.warning(f"ML clustering unavailable: {ml_error_message}")
				else:
					st.markdown("ML-assisted deviation clusters (unsupervised k-means):")
					st.dataframe(ml_summary_df)
		else:
			st.info("No windowed metrics to display.")
	with tab_metrics:
		if not multi_results_df.empty:
			st.dataframe(multi_results_df)
			novel_columns = [
				"hrf_pip_pct",
				"hrf_ials",
				"hrf_pss_pct",
				"deceleration_capacity",
				"acceleration_capacity",
				"permutation_entropy",
				"permutation_entropy_norm",
				"symbolic_0v_pct",
				"symbolic_2uv_pct",
				"mfdfa_width",
				"rqa_rr",
				"rqa_det",
				"entropy_lf",
				"entropy_hf",
				"entropy_lf_hf_ratio",
				"rmssd_master_ratio",
			]
			available_novel = [col for col in novel_columns if col in multi_results_df.columns]
			if available_novel:
				st.markdown("Novel metrics (advanced signal analytics):")
				st.dataframe(multi_results_df[["source"] + available_novel])
			if enable_cov and "rmssd_z_cov" in multi_results_df.columns:
				st.markdown("Covariate-adjusted (patient profile) expectations and z-scores:")
				cols_to_show = ["source"]
				for c in ["rmssd","rmssd_expected","rmssd_z_cov","sdnn","sdnn_expected","sdnn_z_cov"]:
					if c in multi_results_df.columns:
						cols_to_show.append(c)
				st.dataframe(multi_results_df[cols_to_show])
		else:
			st.info("No metrics to display.")
	with tab_ans:
		st.subheader("Autonomic Function Tests")
		st.markdown(
			"Configure time windows relative to the recording start to derive classical autonomic function ratios. "
			"Windows are specified in seconds as `start end` (e.g., `15 25`)."
		)
		if not datasets:
			st.info("Upload a dataset to compute autonomic function metrics.")
		else:
			names = list(datasets.keys())
			selected_dataset_name = st.selectbox("Dataset", names, index=0)
			selected_dataset = datasets[selected_dataset_name]
			use_clean_for_ans = st.checkbox(
				"Use cleaned RR series (if available)",
				value=bool(apply_clean),
				key="ans_use_clean_checkbox",
			)
			try:
				ts_series, rr_series = _prepare_rr_series(selected_dataset, use_clean_for_ans)
			except ValueError as exc:
				logger.warning("Preparing RR series failed: %s", exc, exc_info=True)
				st.warning(str(exc))
			else:
				with st.form(f"ans-form-{selected_dataset_name}"):
					col_a, col_b = st.columns(2)
					vals_phase_ii_input = col_a.text_input("Valsalva phase II window (s)", "15 25")
					vals_phase_iv_input = col_b.text_input("Valsalva phase IV window (s)", "25 35")
					deep_start_input = col_a.number_input("Deep breathing start (s)", min_value=0.0, value=0.0, step=1.0)
					deep_cycle_input = col_b.number_input("Deep breathing cycle length (s)", min_value=1.0, value=10.0, step=0.5)
					deep_cycles_input = col_a.number_input("Number of breathing cycles", min_value=1, max_value=12, value=6, step=1)
					stand_time_input = col_b.number_input("Stand event time (s)", min_value=0.0, value=60.0, step=1.0)
					ratio15_window_input = col_a.text_input("30:15 ratio – 15th-beat window (s)", "5 20")
					ratio30_window_input = col_b.text_input("30:15 ratio – 30th-beat window (s)", "20 40")
					submit_ans = st.form_submit_button("Compute ANS metrics")
				if submit_ans:
					errors: List[str] = []
					valsalva_result: Optional[Dict[str, float]] = None
					deep_breathing_result: Optional[Dict[str, Any]] = None
					ratio_30_15_result: Optional[Dict[str, float]] = None
					try:
						phase_ii_window = _parse_window_seconds(vals_phase_ii_input, "Valsalva phase II window")
						phase_iv_window = _parse_window_seconds(vals_phase_iv_input, "Valsalva phase IV window")
						valsalva_result = compute_valsalva_ratio(ts_series, rr_series, phase_ii_window, phase_iv_window)
					except ValueError as exc:
						logger.warning("Valsalva ratio computation inputs invalid: %s", exc, exc_info=True)
						errors.append(f"Valsalva ratio: {exc}")
					try:
						start_time_s = _parse_float(deep_start_input, "Deep breathing start (s)")
						cycle_length_s = _parse_float(deep_cycle_input, "Deep breathing cycle length (s)")
						deep_breathing_result = compute_deep_breathing_response(
							ts_series,
							rr_series,
							start_time_s=start_time_s,
							cycle_length_s=cycle_length_s,
							n_cycles=int(deep_cycles_input),
						)
					except ValueError as exc:
						logger.warning("Deep breathing response inputs invalid: %s", exc, exc_info=True)
						errors.append(f"Deep breathing response: {exc}")
					try:
						window_15_s = _parse_window_seconds(ratio15_window_input, "30:15 ratio (15th-beat window)")
						window_30_s = _parse_window_seconds(ratio30_window_input, "30:15 ratio (30th-beat window)")
						stand_time_s = _parse_float(stand_time_input, "Stand event time (s)")
						ratio_30_15_result = compute_30_15_ratio(
							ts_series,
							rr_series,
							stand_time_s=stand_time_s,
							window_15_s=window_15_s,
							window_30_s=window_30_s,
						)
					except ValueError as exc:
						logger.warning("30:15 ratio inputs invalid: %s", exc, exc_info=True)
						errors.append(f"30:15 ratio: {exc}")
					if errors:
						for err in errors:
							st.warning(err)
					if valsalva_result is not None:
						st.markdown("### Valsalva Ratio")
						cols = st.columns(3)
						cols[0].metric("Valsalva ratio", f"{valsalva_result['valsalva_ratio']:.2f}")
						cols[1].metric("Phase II min RR (ms)", f"{valsalva_result['phase_ii_min_rr_ms']:.1f}")
						cols[2].metric("Phase IV max RR (ms)", f"{valsalva_result['phase_iv_max_rr_ms']:.1f}")
					if deep_breathing_result is not None:
						st.markdown("### Deep Breathing (E:I Response)")
						col_db1, col_db2, col_db3 = st.columns(3)
						col_db1.metric("Mean E–I difference (ms)", f"{deep_breathing_result['ei_mean_difference_ms']:.1f}")
						col_db2.metric("Mean E–I ratio", f"{deep_breathing_result['ei_mean_ratio']:.3f}")
						col_db3.metric("Mean HR difference (bpm)", f"{deep_breathing_result['hr_mean_difference_bpm']:.1f}")
						details_df = pd.DataFrame(list(deep_breathing_result["cycle_details"]))
						st.dataframe(details_df.rename(columns={"cycle_index": "cycle"}))
					if ratio_30_15_result is not None:
						st.markdown("### 30:15 Ratio")
						col_30a, col_30b, col_30c = st.columns(3)
						col_30a.metric("30:15 ratio", f"{ratio_30_15_result['ratio_30_15']:.2f}")
						col_30b.metric("15th-beat min RR (ms)", f"{ratio_30_15_result['rr_15_min_ms']:.1f}")
						col_30c.metric("30th-beat max RR (ms)", f"{ratio_30_15_result['rr_30_max_ms']:.1f}")
	with tab_readiness:
		st.markdown(
			"**Readiness index (PNS percentile)**  \n"
			"Compares the current parasympathetic index with your historical baseline. "
			"Categories follow the Kubios readiness definitions (VERY LOW, LOW, NORMAL, HIGH)."
		)
		if not pns_mapping:
			st.info("Upload multiple sessions with successful metric computation to enable readiness analysis.")
		else:
			ordered_names = [name for name in ordered_sources if name in pns_mapping]
			if not ordered_names:
				st.info("Ready metrics unavailable; ensure parasympathetic index was computed.")
			else:
				default_idx = max(len(ordered_names) - 1, 0)
				current_sel = st.selectbox("Current measurement", ordered_names, index=default_idx)
				default_baseline = [name for name in ordered_names if name != current_sel]
				baseline_sel = st.multiselect(
					"Historical baseline datasets (oldest to newest)",
					options=ordered_names,
					default=default_baseline,
				)
				include_current = st.checkbox("Include current measurement in baseline", value=False)
				min_hist = int(
					st.number_input("Minimum historical samples", min_value=3, max_value=30, value=7, step=1)
				)
				max_default = int(max(min_hist, min(30, len(ordered_names))))
				max_hist = int(
					st.slider(
						"Historical window (max records retained)",
						min_value=min_hist,
						max_value=90,
						value=max_default,
						step=1,
					)
				)
				history_names: List[str] = []
				for name in ordered_names:
					if name in baseline_sel and (include_current or name != current_sel):
						history_names.append(name)
				if include_current and current_sel not in history_names:
					history_names.append(current_sel)
				if not history_names:
					st.warning("Select at least one baseline record to build readiness baseline.")
				else:
					history_values = [pns_mapping[name] for name in ordered_names if name in history_names]
					# Avoid raising errors when insufficient history is available
					if len(history_values) < int(min_hist):
						st.info(f"Readiness baseline needs at least {int(min_hist)} samples; currently {len(history_values)}.")
						baseline = None
					else:
						try:
							baseline = build_readiness_baseline(history_values, min_samples=min_hist, max_samples=max_hist)
						except ValueError as exc:
							logger.warning("Readiness baseline configuration issue: %s", exc, exc_info=True)
							st.warning(f"Baseline configuration issue: {exc}")
							baseline = None
					if baseline is not None:
						current_pns = float(pns_mapping.get(current_sel, np.nan))
						if not np.isfinite(current_pns):
							st.warning("Current measurement lacks a valid parasympathetic index.")
						else:
							readiness = readiness_from_pns(current_pns, baseline)
							col_a, col_b, col_c = st.columns(3)
							col_a.metric("Readiness score (percentile)", f"{readiness['readiness_score']:.1f}")
							col_b.metric("Category", readiness["readiness_category"])
							col_c.metric("PNS index", f"{readiness['pns_index']:.3f}")
							details_df = pd.DataFrame(
								{
									"baseline_mean": [readiness["baseline_mean"]],
									"baseline_std": [readiness["baseline_std"]],
									"very_low_cut": [readiness["very_low_cut"]],
									"low_cut": [readiness["low_cut"]],
									"high_cut": [readiness["high_cut"]],
									"baseline_samples": [readiness["baseline_count"]],
									"z_score": [readiness["z_score"]],
								}
							)
							st.dataframe(details_df)
							history_labels = history_names.copy()
							if current_sel not in history_labels:
								history_labels.append(current_sel)
							line_series = {
								"name": "Baseline PNS history",
								"type": "line",
								"showSymbol": True,
								"smooth": True,
								"data": [[label, float(pns_mapping[label])] for label in history_names],
							}
							current_series = {
								"name": f"{current_sel} (current)",
								"type": "scatter",
								"symbolSize": 12,
								"itemStyle": {"color": "#1e88e5"},
								"data": [[current_sel, readiness["pns_index"]]],
							}
							opt = {
								"title": {"text": "Parasympathetic index baseline", "left": "center"},
								"tooltip": {"trigger": "axis"},
								"grid": {"left": 32, "right": 16, "containLabel": True},
								"xAxis": {"type": "category", "name": "Session", "data": history_labels, "boundaryGap": False},
								"yAxis": {"type": "value", "name": "PNS index"},
								"legend": {"top": 24},
								"series": [line_series, current_series],
							}
							mark_lines = [
								{"yAxis": readiness["very_low_cut"], "name": "Very low cut"},
								{"yAxis": readiness["low_cut"], "name": "Low cut"},
								{"yAxis": readiness["high_cut"], "name": "High cut"},
							]
							line_series["markLine"] = {"symbol": "none", "data": mark_lines}
							render_echarts(opt, height_px=360, width="100%", config=EChartsConfig())
							st.markdown(
								"- **VERY LOW**: below ~3% of historical PNS values; indicative of high stress or limited recovery.  \n"
								"- **LOW**: between ~3% and 17%, often aligned with moderate stress or incomplete rest.  \n"
								"- **NORMAL**: within ~17–84% of history, reflecting typical readiness.  \n"
								"- **HIGH**: above ~84%, often seen with strong recovery and parasympathetic dominance."
							)
							st.caption(
								"Baseline uses the selected historical sessions (last-in-first-out capped at the chosen window). "
								"Consistent daily morning recordings (1–5 minutes, relaxed breathing) improve reliability."
							)
	with tab_gauges:
		if skip_gauges:
			st.info("Gauges disabled (Performance & display).")
		else:
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
	with tab_export:
		st.subheader("Export report")
		if not meta_rows and multi_results_df.empty:
			st.info("Run an analysis to enable export.")
		else:
			scope_choice = st.radio(
				"Report scope",
				options=[ExportScope.SUMMARY, ExportScope.COMPLETE],
				index=0,
				format_func=lambda scope: "Summary (partial)" if scope == ExportScope.SUMMARY else "Complete (full)",
			)
			include_windowed_opt = st.checkbox(
				"Include windowed metrics section",
				value=(scope_choice == ExportScope.COMPLETE),
				disabled=windowed_df.empty,
			)
			include_ml_opt = st.checkbox(
				"Include ML clustering summary",
				value=(enable_ml and not ml_summary_df.empty),
				disabled=ml_summary_df.empty,
			)
			available_sources: List[str] = []
			if ordered_sources:
				available_sources = ordered_sources
			elif meta_rows:
				meta_sources = {str(row.get("source", row.get("name", ""))) for row in meta_rows if row.get("source") or row.get("name")}
				available_sources = sorted([src for src in meta_sources if src])
			elif not multi_results_df.empty and "source" in multi_results_df.columns:
				available_sources = sorted(multi_results_df["source"].astype(str).unique().tolist())
			selected_sources = st.multiselect(
				"Datasets to include",
				options=available_sources,
				default=available_sources,
			)
			notes_input = st.text_area(
				"Additional notes (optional)",
				placeholder="Add protocol notes, observations, or follow-up actions.",
				height=120,
			)
			export_config = ExportConfiguration(
				scope=scope_choice,
				include_windowed=include_windowed_opt,
				include_ml=include_ml_opt,
			)
			try:
				report_markdown = build_markdown_report(
					meta_rows=meta_rows,
					multi_results_df=multi_results_df,
					windowed_df=windowed_df,
					episodes_df=episodes_df,
					ml_summary_df=ml_summary_df if include_ml_opt else None,
					config=export_config,
					selected_sources=selected_sources,
					additional_notes=notes_input,
				)
			except ValueError as exc:
				logger.warning("Report generation failed: %s", exc, exc_info=True)
				st.warning(str(exc))
			else:
				st.text_area("Report preview", report_markdown, height=360)
				file_suffix = scope_choice.value
				timestamp_str = pd.Timestamp.utcnow().strftime("%Y%m%dT%H%M%SZ")
				file_name = f"hrv_report_{file_suffix}_{timestamp_str}.md"
				st.download_button(
					label="Download markdown report",
					data=report_markdown.encode("utf-8"),
					file_name=file_name,
					mime="text/markdown",
				)
				if include_ml_opt and ml_summary_df.empty and enable_ml and ml_error_message:
					st.info(f"ML section included but no clusters were generated: {ml_error_message}")
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


