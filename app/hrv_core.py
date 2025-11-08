from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy import signal, linalg
from scipy.interpolate import interp1d


def _moving_median(values: np.ndarray, window: int) -> np.ndarray:
	"""Return centered moving median with edge reflection.

	Args:
		values: 1D array of RR intervals (ms).
		window: Odd window size >= 3.

	Returns:
		Array of same length with moving median estimates.
	"""
	if values.size == 0:
		return values
	w = int(max(3, window))
	if w % 2 == 0:
		w += 1
	pad = w // 2
	x = np.pad(values, (pad, pad), mode="reflect")
	out = np.empty_like(values, dtype=float)
	for i in range(values.size):
		seg = x[i : i + w]
		out[i] = float(np.median(seg))
	return out


def detect_artifacts(
	rr_ms: np.ndarray,
	*,
	method: str = "threshold_median",
	max_deviation: float = 0.2,
	median_window: int = 11,
) -> np.ndarray:
	"""Detect artifacts/ectopic beats using simple bounded heuristics.

	Methods:
	- threshold_median: flag if |rr - moving_median| / moving_median > max_deviation
	- threshold_prev: flag if |rr[i] - rr[i-1]| / rr[i-1] > max_deviation (i>0); rr[0] uses median

	Returns:
		Boolean mask of valid samples (True = keep).
	"""
	if rr_ms.size == 0:
		return np.array([], dtype=bool)
	rr = rr_ms.astype(float)
	if method == "threshold_prev":
		ref = np.roll(rr, 1)
		ref[0] = float(np.median(rr))
	else:
		ref = _moving_median(rr, window=median_window)
	with np.errstate(divide="ignore", invalid="ignore"):
		dev = np.abs(rr - ref) / np.maximum(ref, 1e-9)
	valid = dev <= float(max_deviation)
	# Always keep within physiological bounds even if heuristic says invalid
	in_bounds = (rr >= 300.0) & (rr <= 2000.0)
	return valid & in_bounds


def interpolate_outliers(rr_ms: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
	"""Linearly interpolate over invalid samples; endpoints are forward/backward filled.

	Args:
		rr_ms: RR series (ms).
		valid_mask: Boolean mask of valid samples (True means keep original).

	Returns:
		Cleaned RR series with invalid points replaced by interpolation.
	"""
	if rr_ms.size == 0:
		return rr_ms
	rr = rr_ms.astype(float).copy()
	valid_idx = np.where(valid_mask)[0]
	if valid_idx.size == 0:
		# Nothing to anchor; return original
		return rr
	if valid_idx.size == rr.size:
		return rr
	invalid_idx = np.where(~valid_mask)[0]
	# Build interpolation over indices
	x = valid_idx.astype(float)
	y = rr[valid_idx]
	f = interp1d(x, y, kind="linear", bounds_error=False, fill_value=(y[0], y[-1]))
	rr[invalid_idx] = f(invalid_idx.astype(float))
	return rr


def clean_rr_intervals(
	rr_ms: np.ndarray,
	*,
	method: str = "threshold_median",
	max_deviation: float = 0.2,
	median_window: int = 11,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, float]]:
	"""Detect and correct artifacts by interpolation.

	Returns:
		(cleaned_rr_ms, valid_mask, summary_dict)
	"""
	if rr_ms.size == 0:
		return rr_ms, np.array([], dtype=bool), {"n": 0.0, "n_flagged": 0.0, "flagged_pct": 0.0}
	valid = detect_artifacts(rr_ms, method=method, max_deviation=max_deviation, median_window=median_window)
	cleaned = interpolate_outliers(rr_ms, valid_mask=valid)
	n = float(rr_ms.size)
	n_flagged = float(np.sum(~valid))
	summary = {
		"n": n,
		"n_flagged": n_flagged,
		"flagged_pct": float((n_flagged / n) * 100.0) if n > 0 else 0.0,
		"qc_method": {"method": method, "max_deviation": float(max_deviation), "median_window": int(median_window)},
	}
	return cleaned, valid, summary


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
		elif method == "periodogram":
			freqs, psd = signal.periodogram(rr_det, fs=sampling_rate, window="hann")
		elif method == "ar":
			# Simple AR(Yule-Walker) PSD with fixed order
			order = int(min(16, max(4, len(rr_det) // 20)))
			# Autocorrelation
			x = rr_det - np.mean(rr_det)
			r = np.correlate(x, x, mode="full")[len(x) - 1 : len(x) - 1 + order + 1] / len(x)
			R = linalg.toeplitz(r[:-1])
			try:
				a = np.linalg.solve(R, -r[1:])
				sigma2 = float(r[0] + np.dot(a, r[1:]))
			except Exception:
				a = np.zeros(order, dtype=float)
				sigma2 = float(np.var(x))
			# Frequency response
			freqs = np.linspace(0.0, sampling_rate / 2.0, num=512, endpoint=True)
			w = 2.0 * np.pi * freqs / sampling_rate
			den = np.ones_like(freqs, dtype=complex)
			for k in range(1, order + 1):
				den += a[k - 1] * np.exp(-1j * w * k)
			psd = (sigma2 / (np.abs(den) ** 2)).real
		else:
			freqs, psd = signal.welch(rr_det, fs=sampling_rate, nperseg=min(len(rr_det) // 4, 256), window="hann")
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
		# Derived respiratory rate (breaths/min) from HF peak (Hz) when RSA is present
		respiratory_rate_bpm = float(hf_peak * 60.0) if hf_peak > 0 else 0.0
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
			"respiratory_rate_bpm": respiratory_rate_bpm,
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
	results.update(compute_geometric_metrics(rr_intervals))
	# Entropy metrics with default parameters (m=2, r=0.2*SD)
	results.update(compute_entropy_metrics(rr_intervals, m=2, r_ratio=0.2))
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


def psd_curve(rr: np.ndarray, sampling_rate: float = 4.0, *, method: str = "welch") -> Tuple[np.ndarray, np.ndarray]:
	"""Return (freqs, psd) arrays suitable for plotting."""
	if rr.size < 50:
		return np.array([]), np.array([])
	t_reg, rr_interp = _interpolate_rr(rr, sampling_rate)
	if t_reg.size == 0:
		return np.array([]), np.array([])
	rr_det = signal.detrend(rr_interp)
	if method == "welch":
		freqs, psd = signal.welch(rr_det, fs=sampling_rate, nperseg=min(len(rr_det) // 4, 256), window="hann")
	elif method == "periodogram":
		freqs, psd = signal.periodogram(rr_det, fs=sampling_rate, window="hann")
	else:
		# fall back to metrics routine for AR or unknown
		out = compute_frequency_domain_metrics(rr, method=method, sampling_rate=sampling_rate)
		if not out:
			return np.array([]), np.array([])
		# Recompute for plotting grid based on returned band metrics isn't practical; use Welch fallback
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


def compute_geometric_metrics(rr_intervals: np.ndarray) -> Dict[str, float]:
	"""Compute geometric HRV metrics: HRV triangular index, TINN (approx), Baevsky Stress Index.

	Notes:
	- HRV triangular index (HRVI) = N / max(bin count) with bin width ~7.8125 ms.
	- TINN approximated as baseline width between first/last nonzero histogram bins around the mode.
	- Baevsky Stress Index SI = AMo / (2 * Mo * MxDMn), with AMo fraction (0..1), Mo in ms, MxDMn range in ms.
	"""
	if rr_intervals.size < 3:
		return {}
	rr = rr_intervals.astype(float)
	bin_width = 7.8125  # ms
	min_v = float(np.min(rr))
	max_v = float(np.max(rr))
	if not np.isfinite(min_v) or not np.isfinite(max_v) or max_v <= min_v:
		return {}
	bins = int(max(10, np.ceil((max_v - min_v) / bin_width)))
	hist, edges = np.histogram(rr, bins=bins, range=(min_v, max_v))
	N = int(rr.size)
	max_count = int(np.max(hist)) if hist.size > 0 else 0
	hrvi = float(N / max_count) if max_count > 0 else 0.0
	# Mode and amplitude
	mode_idx = int(np.argmax(hist)) if hist.size > 0 else 0
	mode_center = float((edges[mode_idx] + edges[mode_idx + 1]) / 2.0) if hist.size > 0 else float(np.median(rr))
	AMo = float(hist[mode_idx] / N) if N > 0 and hist.size > 0 else 0.0
	MxDMn = float(max_v - min_v)
	si = float(AMo / (2.0 * mode_center * MxDMn)) if (mode_center > 0 and MxDMn > 0) else 0.0
	# Approximate TINN as baseline width between first and last nonzero bins
	nonzero_bins = np.where(hist > 0)[0]
	if nonzero_bins.size >= 2:
		left_edge = float(edges[nonzero_bins[0]])
		right_edge = float(edges[nonzero_bins[-1] + 1])
		tinn = float(right_edge - left_edge)
	else:
		tinn = 0.0
	return {"hrv_triangular_index": hrvi, "tinn": tinn, "baevsky_stress_index": si}


def compute_entropy_metrics(
	rr_intervals: np.ndarray,
	*,
	m: int = 2,
	r_ratio: float = 0.2,
) -> Dict[str, float]:
	"""Compute Approximate Entropy (ApEn) and Sample Entropy (SampEn) for RR series.

	Args:
		rr_intervals: RR intervals in milliseconds.
		m: Embedding dimension (commonly 2).
		r_ratio: Tolerance as fraction of the series standard deviation (commonly 0.15–0.20).

	Returns:
		Dictionary with 'apen' and 'sampen'. Returns 0.0 when undefined.
	"""
	n = int(rr_intervals.size)
	if n < (m + 2):
		return {"apen": 0.0, "sampen": 0.0}
	x = rr_intervals.astype(float)
	sd = float(np.std(x, ddof=0))
	r = float(max(1e-9, r_ratio * sd))

	def _phi(dim: int) -> float:
		counts: List[int] = []
		for i in range(0, n - dim + 1):
			ref = x[i : i + dim]
			c = 0
			for j in range(0, n - dim + 1):
				if i == j:
					continue
				win = x[j : j + dim]
				if np.max(np.abs(ref - win)) <= r:
					c += 1
			counts.append(c)
		if not counts:
			return 0.0
		return float(np.mean(np.array(counts, dtype=float) / max(1, (n - dim))))

	phi_m = _phi(m)
	phi_m1 = _phi(m + 1)
	apen = float(-np.log(phi_m1 / max(1e-12, phi_m))) if (phi_m > 0 and phi_m1 > 0) else 0.0

	# SampEn: negative log of conditional probability without self-matches
	def _match_count(dim: int) -> Tuple[int, int]:
		Cm = 0
		for i in range(0, n - dim):
			ref = x[i : i + dim]
			for j in range(i + 1, n - dim + 1):
				win = x[j : j + dim]
				if np.max(np.abs(ref - win)) <= r:
					Cm += 1
		return Cm, (n - dim) * (n - dim + 1) // 2

	Cm, total_m = _match_count(m)
	Cm1, total_m1 = _match_count(m + 1)
	p_m = float(Cm / max(1, total_m))
	p_m1 = float(Cm1 / max(1, total_m1))
	sampen = float(-np.log(p_m1 / max(1e-12, p_m))) if (p_m > 0 and p_m1 > 0) else 0.0
	return {"apen": apen, "sampen": sampen}


def covariate_adjust_short_term(
	*,
	age_years: float,
	sex: str,
	bmi: float,
	exercise_level: str,
	rmssd: Optional[float],
	sdnn: Optional[float],
) -> Dict[str, float]:
	"""Compute covariate-adjusted expectations and z-scores for short-term RMSSD and SDNN.

	The adjustment uses transparent, conservative coefficients grounded in common anchors:
	- Baselines (female, 40y, BMI 25, sedentary): RMSSD_mu=42 ms (sigma≈15), SDNN_mu=50 ms (sigma≈16)
	- Age effect (per year): RMSSD −0.3 ms, SDNN −0.35 ms
	- BMI effect (per unit): RMSSD −0.4 ms, SDNN −0.3 ms
	- Male offsets: RMSSD −2.0 ms, SDNN −1.0 ms
	- Exercise offsets: sedentary 0; moderate +5 ms; athlete +12 ms (RMSSD); SDNN +5/+10 ms

	These defaults are intended as starting points and should be interpreted with protocol context.
	"""
	# Baselines and sigmas
	rmssd_mu0 = 42.0
	rmssd_sigma = 15.0
	sdnn_mu0 = 50.0
	sdnn_sigma = 16.0
	# Coefficients
	b_age_rmssd = -0.3
	b_bmi_rmssd = -0.4
	b_male_rmssd = -2.0
	b_age_sdnn = -0.35
	b_bmi_sdnn = -0.3
	b_male_sdnn = -1.0
	# Exercise offsets
	ex_levels = {"sedentary": (0.0, 0.0), "moderate": (5.0, 5.0), "athlete": (12.0, 10.0)}
	ex_rmssd_off, ex_sdnn_off = ex_levels.get(str(exercise_level).lower(), (0.0, 0.0))
	male = 1.0 if str(sex).lower().startswith("m") else 0.0
	age_years = float(age_years)
	bmi = float(bmi)
	# Expected means
	rmssd_expected = rmssd_mu0 + b_age_rmssd * (age_years - 40.0) + b_bmi_rmssd * (bmi - 25.0) + b_male_rmssd * male + ex_rmssd_off
	sdnn_expected = sdnn_mu0 + b_age_sdnn * (age_years - 40.0) + b_bmi_sdnn * (bmi - 25.0) + b_male_sdnn * male + ex_sdnn_off
	out: Dict[str, float] = {
		"rmssd_expected": float(rmssd_expected),
		"sdnn_expected": float(sdnn_expected),
		"rmssd_z_cov": 0.0,
		"sdnn_z_cov": 0.0,
	}
	if rmssd is not None and np.isfinite(rmssd) and rmssd_sigma > 0:
		out["rmssd_z_cov"] = float((float(rmssd) - rmssd_expected) / rmssd_sigma)
	if sdnn is not None and np.isfinite(sdnn) and sdnn_sigma > 0:
		out["sdnn_z_cov"] = float((float(sdnn) - sdnn_expected) / sdnn_sigma)
	return out


@dataclass(frozen=True, slots=True)
class ReadinessBaseline:
	"""Statistical summary of historical parasympathetic index values."""

	count: int
	mean: float
	std: float
	very_low_cut: float
	low_cut: float
	high_cut: float
	history: Tuple[float, ...]


def build_readiness_baseline(
	values: Sequence[float],
	*,
	min_samples: int = 7,
	max_samples: int = 90,
) -> ReadinessBaseline:
	"""Construct readiness baseline from historical parasympathetic index values.

	Args:
		values: Historical PNS index values ordered from oldest to newest.
		min_samples: Minimum number of historical samples required (default 7).
		max_samples: Maximum samples to retain (default 90, reflecting ~90 days).

	Returns:
		ReadinessBaseline dataclass with summary statistics and percentile cuts.

	Raises:
		ValueError: If there are fewer than `min_samples` valid values or if
			max_samples < min_samples.
	"""
	if max_samples < min_samples:
		raise ValueError("max_samples must be greater than or equal to min_samples")
	arr = np.asarray(values, dtype=float)
	arr = arr[np.isfinite(arr)]
	if arr.size == 0:
		raise ValueError("No finite values supplied for baseline construction")
	if arr.size > max_samples:
		arr = arr[-int(max_samples) :]
	if arr.size < int(min_samples):
		raise ValueError(
			f"At least {min_samples} historical samples are required; received {arr.size}"
		)
	arr_sorted = np.sort(arr)
	mean = float(np.mean(arr_sorted))
	std = float(np.std(arr_sorted, ddof=1)) if arr_sorted.size > 1 else 0.0
	very_low_cut = float(np.percentile(arr_sorted, 3.0, method="linear"))
	low_cut = float(np.percentile(arr_sorted, 17.0, method="linear"))
	high_cut = float(np.percentile(arr_sorted, 84.0, method="linear"))
	return ReadinessBaseline(
		count=int(arr_sorted.size),
		mean=mean,
		std=std,
		very_low_cut=very_low_cut,
		low_cut=low_cut,
		high_cut=high_cut,
		history=tuple(float(v) for v in arr_sorted.tolist()),
	)


def readiness_from_pns(
	current_value: float,
	baseline: ReadinessBaseline,
) -> Dict[str, float | str | int]:
	"""Calculate readiness index metrics from the current PNS value and baseline.

	Args:
		current_value: Current parasympathetic index (0–1 scale recommended).
		baseline: Baseline statistics returned by `build_readiness_baseline`.

	Returns:
		Dictionary containing readiness score (percentile rank), z-score,
		category label, and baseline-derived thresholds.
	"""
	if not np.isfinite(current_value):
		raise ValueError("current_value must be finite")
	if baseline.count <= 0:
		raise ValueError("baseline must contain at least one value")
	arr = np.asarray(baseline.history, dtype=float)
	arr_sorted = np.sort(arr)
	count = arr_sorted.size
	# Percentile rank using right-inclusive count
	position = int(np.searchsorted(arr_sorted, current_value, side="right"))
	percentile_rank = float((position / count) * 100.0)
	std = float(baseline.std)
	if std < 1e-9:
		z_score = 0.0
	else:
		z_score = float((current_value - baseline.mean) / std)
	if current_value <= baseline.very_low_cut:
		category = "VERY LOW"
	elif current_value <= baseline.low_cut:
		category = "LOW"
	elif current_value <= baseline.high_cut:
		category = "NORMAL"
	else:
		category = "HIGH"
	score = float(np.clip(percentile_rank, 0.0, 100.0))
	return {
		"readiness_score": score,
		"readiness_category": category,
		"percentile_rank": percentile_rank,
		"z_score": z_score,
		"pns_index": float(current_value),
		"baseline_mean": float(baseline.mean),
		"baseline_std": std,
		"very_low_cut": float(baseline.very_low_cut),
		"low_cut": float(baseline.low_cut),
		"high_cut": float(baseline.high_cut),
		"baseline_count": int(baseline.count),
	}


