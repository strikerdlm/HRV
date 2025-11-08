from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import signal
from scipy.interpolate import interp1d


def load_rr_intervals_from_text(name: str, content: str) -> np.ndarray:
	"""Parse a Polar-like RR text file content into an array of RR intervals (ms).

	Each non-empty line is parsed as a float and filtered to [300, 2000] ms.

	Args:
		name: Logical file name for error messages.
		content: File content as text.

	Returns:
		Vector of RR intervals in milliseconds.
	"""
	lines = content.splitlines()
	rr_values: List[float] = []
	for line in lines:
		line = line.strip()
		if not line:
			continue
		try:
			v = float(line)
		except ValueError:
			continue
		if 300.0 <= v <= 2000.0:
			rr_values.append(v)
	return np.asarray(rr_values, dtype=float)


def rr_from_hr(hr_series: pd.Series, min_rr: float = 300, max_rr: float = 2000) -> np.ndarray:
	"""Convert heart rate (bpm) to RR intervals (ms) with bounds."""
	hr_clean = pd.to_numeric(hr_series, errors="coerce").dropna()
	if hr_clean.empty:
		return np.array([], dtype=float)
	rr_ms = 60000.0 / hr_clean
	rr_ms = rr_ms.replace([np.inf, -np.inf], np.nan).dropna()
	rr_ms = rr_ms[(rr_ms >= min_rr) & (rr_ms <= max_rr)]
	return rr_ms.values.astype(float)


def compute_time_domain_metrics(rr_intervals: np.ndarray) -> Dict[str, float]:
	if rr_intervals.size == 0:
		return {}
	metrics: Dict[str, float] = {}
	metrics["mean_nni"] = float(np.mean(rr_intervals))
	metrics["sdnn"] = float(np.std(rr_intervals, ddof=1))
	metrics["median_nni"] = float(np.median(rr_intervals))
	metrics["mad_nni"] = float(np.median(np.abs(rr_intervals - metrics["median_nni"])))
	metrics["cvnn"] = float((metrics["sdnn"] / metrics["mean_nni"]) * 100) if metrics["mean_nni"] > 0 else 0.0
	hr_values = 60000.0 / rr_intervals
	metrics["mean_hr"] = float(np.mean(hr_values))
	metrics["std_hr"] = float(np.std(hr_values, ddof=1))
	metrics["min_hr"] = float(np.min(hr_values))
	metrics["max_hr"] = float(np.max(hr_values))
	if rr_intervals.size > 1:
		rr_diff = np.diff(rr_intervals)
		metrics["rmssd"] = float(np.sqrt(np.mean(rr_diff ** 2)))
		metrics["sdsd"] = float(np.std(rr_diff, ddof=1))
		mean_abs = float(np.mean(np.abs(rr_diff)))
		metrics["cvsd"] = float((metrics["sdsd"] / mean_abs) * 100) if mean_abs > 0 else 0.0
		nn50 = int(np.sum(np.abs(rr_diff) > 50.0))
		metrics["nn50"] = float(nn50)
		metrics["pnn50"] = float((nn50 / rr_diff.size) * 100.0)
		nn20 = int(np.sum(np.abs(rr_diff) > 20.0))
		metrics["nn20"] = float(nn20)
		metrics["pnn20"] = float((nn20 / rr_diff.size) * 100.0)
	else:
		metrics.update(dict(rmssd=0.0, sdsd=0.0, cvsd=0.0, nn50=0.0, pnn50=0.0, nn20=0.0, pnn20=0.0))
	return metrics


def _interpolate_rr(rr_intervals: np.ndarray, sampling_rate: float) -> Tuple[np.ndarray, np.ndarray]:
	rr_seconds = rr_intervals / 1000.0
	r_peak_times = np.concatenate([[0.0], np.cumsum(rr_seconds)])
	rr_timestamps = (r_peak_times[:-1] + r_peak_times[1:]) / 2.0
	total_duration = float(r_peak_times[-1])
	if total_duration <= 0:
		return np.array([]), np.array([])
	time_regular = np.arange(0.0, total_duration, 1.0 / sampling_rate)
	if time_regular.size < 10:
		return np.array([]), np.array([])
	kind = "cubic" if rr_intervals.size >= 4 else "linear"
	f = interp1d(rr_timestamps, rr_intervals, kind=kind, bounds_error=False, fill_value="extrapolate")
	rr_interpolated = f(time_regular)
	return time_regular, rr_interpolated


def compute_frequency_domain_metrics(
	rr_intervals: np.ndarray,
	method: str = "welch",
	sampling_rate: float = 4.0,
) -> Dict[str, float]:
	if rr_intervals.size < 50:
		return {}
	try:
		t_reg, rr_interp = _interpolate_rr(rr_intervals, sampling_rate)
		if t_reg.size == 0:
			return {}
		rr_det = signal.detrend(rr_interp)
		if method == "welch":
			freqs, psd = signal.welch(rr_det, fs=sampling_rate, nperseg=min(len(rr_det) // 4, 256), window="hann")
		else:
			freqs, psd = signal.periodogram(rr_det, fs=sampling_rate, window="hann")
		vlf_band = (0.0033, 0.04)
		lf_band = (0.04, 0.15)
		hf_band = (0.15, 0.4)
		vlf_mask = (freqs >= vlf_band[0]) & (freqs < vlf_band[1])
		lf_mask = (freqs >= lf_band[0]) & (freqs < lf_band[1])
		hf_mask = (freqs >= hf_band[0]) & (freqs < hf_band[1])
		vlf_power = float(np.trapz(psd[vlf_mask], freqs[vlf_mask])) if np.any(vlf_mask) else 0.0
		lf_power = float(np.trapz(psd[lf_mask], freqs[lf_mask])) if np.any(lf_mask) else 0.0
		hf_power = float(np.trapz(psd[hf_mask], freqs[hf_mask])) if np.any(hf_mask) else 0.0
		total_power = float(vlf_power + lf_power + hf_power)
		lf_nu = float((lf_power / (lf_power + hf_power)) * 100.0) if (lf_power + hf_power) > 0 else 0.0
		hf_nu = float((hf_power / (lf_power + hf_power)) * 100.0) if (lf_power + hf_power) > 0 else 0.0
		lf_hf_ratio = float(lf_power / hf_power) if hf_power > 0 else 0.0
		vlf_percent = float((vlf_power / total_power) * 100.0) if total_power > 0 else 0.0
		lf_percent = float((lf_power / total_power) * 100.0) if total_power > 0 else 0.0
		hf_percent = float((hf_power / total_power) * 100.0) if total_power > 0 else 0.0
		vlf_peak = float(freqs[vlf_mask][np.argmax(psd[vlf_mask])]) if np.any(vlf_mask) and vlf_power > 0 else 0.0
		lf_peak = float(freqs[lf_mask][np.argmax(psd[lf_mask])]) if np.any(lf_mask) and lf_power > 0 else 0.0
		hf_peak = float(freqs[hf_mask][np.argmax(psd[hf_mask])]) if np.any(hf_mask) and hf_power > 0 else 0.0
		return {
			"vlf_power": vlf_power,
			"lf_power": lf_power,
			"hf_power": hf_power,
			"total_power": total_power,
			"lf_nu": lf_nu,
			"hf_nu": hf_nu,
			"lf_hf_ratio": lf_hf_ratio,
			"vlf_percent": vlf_percent,
			"lf_percent": lf_percent,
			"hf_percent": hf_percent,
			"vlf_peak": vlf_peak,
			"lf_peak": lf_peak,
			"hf_peak": hf_peak,
			"method": method,
			"sampling_rate": sampling_rate,
		}
	except Exception:
		return {}


def compute_poincare_metrics(rr_intervals: np.ndarray) -> Dict[str, float]:
	if rr_intervals.size < 2:
		return {}
	rr1 = rr_intervals[:-1]
	rr2 = rr_intervals[1:]
	diff = rr2 - rr1
	sum_rr = rr2 + rr1
	sd1 = float(np.std(diff) / np.sqrt(2.0))
	sd2 = float(np.std(sum_rr) / np.sqrt(2.0))
	sd1_sd2_ratio = float(sd2 / sd1) if sd1 > 0 else 0.0
	ellipse_area = float(np.pi * sd1 * sd2) if sd1 > 0 and sd2 > 0 else 0.0
	return {"sd1": sd1, "sd2": sd2, "sd1_sd2_ratio": sd1_sd2_ratio, "ellipse_area": ellipse_area}


def compute_dfa_metrics(rr_intervals: np.ndarray) -> Dict[str, float]:
	if rr_intervals.size < 100:
		return {"dfa_alpha1": 0.0, "dfa_alpha2": 0.0}
	y = np.cumsum(rr_intervals - np.mean(rr_intervals))
	scales_short = np.arange(4, min(17, rr_intervals.size // 4))
	scales_long = np.arange(16, min(65, rr_intervals.size // 4))

	def _fluct(scales: np.ndarray) -> List[float]:
		res: List[float] = []
		for scale in scales:
			segments = int(len(y) // int(scale))
			if segments < 4:
				continue
			local: List[float] = []
			for i in range(segments):
				start = int(i * scale)
				end = int(start + scale)
				segment = y[start:end]
				x = np.arange(segment.size)
				coeffs = np.polyfit(x, segment, 1)
				trend = np.polyval(coeffs, x)
				detr = segment - trend
				local.append(float(np.sqrt(np.mean(detr**2))))
			if local:
				res.append(float(np.mean(local)))
		return res

	fluc_short = _fluct(scales_short)
	fluc_long = _fluct(scales_long)
	alpha1 = 0.0
	alpha2 = 0.0
	if len(fluc_short) > 2 and np.all(np.array(fluc_short) > 0):
		log_scales = np.log10(scales_short[: len(fluc_short)])
		log_fluc = np.log10(fluc_short)
		alpha1 = float(np.polyfit(log_scales, log_fluc, 1)[0])
	if len(fluc_long) > 2 and np.all(np.array(fluc_long) > 0):
		log_scales = np.log10(scales_long[: len(fluc_long)])
		log_fluc = np.log10(fluc_long)
		alpha2 = float(np.polyfit(log_scales, log_fluc, 1)[0])
	return {"dfa_alpha1": alpha1, "dfa_alpha2": alpha2}


def compute_comprehensive_hrv(rr_intervals: np.ndarray) -> Dict[str, Any]:
	"""Compute time, frequency, Poincaré, and DFA metrics plus indices."""
	results: Dict[str, Any] = {
		"n_intervals": int(rr_intervals.size),
		"recording_duration_minutes": float(np.sum(rr_intervals) / (1000.0 * 60.0)),
	}
	if rr_intervals.size < 10:
		return results
	results.update(compute_time_domain_metrics(rr_intervals))
	results.update(compute_frequency_domain_metrics(rr_intervals))
	results.update(compute_poincare_metrics(rr_intervals))
	results.update(compute_dfa_metrics(rr_intervals))
	if "hf_power" in results and "rmssd" in results:
		parasym_components = [
			float(results.get("hf_nu", 0.0)) / 100.0,
			min(1.0, float(results.get("rmssd", 0.0)) / 100.0),
			min(1.0, float(results.get("pnn50", 0.0)) / 50.0),
			min(1.0, float(results.get("sd1", 0.0)) / 50.0),
		]
		results["parasympathetic_index"] = float(np.mean([c for c in parasym_components if c > 0]))
		lf_hf_ratio = float(results.get("lf_hf_ratio", 0.0))
		results["sympathetic_index"] = float(min(1.0, lf_hf_ratio / 5.0))
		results["ans_balance"] = float(results["parasympathetic_index"] - results["sympathetic_index"])
	return results


def compute_windowed_hrv(
	df_in: pd.DataFrame,
	*,
	rr_col: str = "rr_intervals_ms",
	timestamp_col: str = "timestamp",
	window: str = "5min",
	step: str = "1min",
	min_rr_count: int = 60,
	max_windows: int = 500,
) -> pd.DataFrame:
	"""Sliding-window HRV metrics with explicit bounds."""
	if df_in.empty:
		return pd.DataFrame()
	df = df_in[[c for c in [timestamp_col, rr_col, "source"] if c in df_in.columns]].dropna(subset=[timestamp_col])
	if rr_col not in df.columns:
		return pd.DataFrame()
	df = df.sort_values(timestamp_col).copy()
	rr_vals = pd.to_numeric(df[rr_col], errors="coerce")
	mask = (rr_vals >= 300.0) & (rr_vals <= 2000.0)
	df = df.loc[mask].copy()
	if df.empty:
		return pd.DataFrame()
	t0 = pd.to_datetime(df[timestamp_col].iloc[0])
	tN = pd.to_datetime(df[timestamp_col].iloc[-1])
	win_delta = pd.to_timedelta(window)
	step_delta = pd.to_timedelta(step)
	if not (pd.notna(win_delta) and pd.notna(step_delta)):
		raise ValueError("Invalid window/step specification")
	starts: List[pd.Timestamp] = []
	s = t0
	count = 0
	while s + win_delta <= tN and count < max_windows:
		starts.append(s)
		s = s + step_delta
		count += 1
	results: List[Dict[str, float]] = []
	if not starts:
		return pd.DataFrame()
	for s in starts:
		e = s + win_delta
		w = df[(df[timestamp_col] >= s) & (df[timestamp_col] < e)]
		if len(w) < min_rr_count:
			continue
		rr = w[rr_col].to_numpy()
		metrics = compute_comprehensive_hrv(rr)
		metrics["start"] = s
		metrics["end"] = e
		if "source" in df.columns:
			metrics["source"] = w["source"].iloc[0]
		results.append(metrics)
	if not results:
		return pd.DataFrame()
	return pd.DataFrame(results)


def psd_curve(rr: np.ndarray, sampling_rate: float = 4.0) -> Tuple[np.ndarray, np.ndarray]:
	"""Return (freqs, psd) arrays suitable for plotting."""
	if rr.size < 50:
		return np.array([]), np.array([])
	t_reg, rr_interp = _interpolate_rr(rr, sampling_rate)
	if t_reg.size == 0:
		return np.array([]), np.array([])
	rr_det = signal.detrend(rr_interp)
	freqs, psd = signal.welch(rr_det, fs=sampling_rate, nperseg=min(len(rr_det) // 4, 256), window="hann")
	return freqs.astype(float), psd.astype(float)


def spectrogram_rr(
	rr: np.ndarray,
	*, sampling_rate: float = 4.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
	"""Compute RR interpolated spectrogram for time-frequency visualization."""
	if rr.size < 200:
		return np.array([]), np.array([]), np.array([[]])
	t_reg, rr_interp = _interpolate_rr(rr, sampling_rate)
	if t_reg.size == 0:
		return np.array([]), np.array([]), np.array([[]])
	rr_det = signal.detrend(rr_interp)
	fxx, txx, Sxx = signal.spectrogram(
		rr_det,
		fs=sampling_rate,
		window="hann",
		nperseg=min(256, len(rr_det) // 4),
		noverlap=None,
		detrend=False,
		scaling="density",
		mode="psd",
	)
	return fxx.astype(float), txx.astype(float), Sxx.astype(float)


