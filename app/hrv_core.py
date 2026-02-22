from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy import signal, linalg
from scipy.interpolate import interp1d


def _moving_median(values: np.ndarray, window: int) -> np.ndarray:
	"""Return centered moving median using pandas rolling (fast)."""
	if values.size == 0:
		return values
	w = int(max(3, window + (window % 2 == 0)))
	ser = pd.Series(values, dtype=float)
	out = ser.rolling(window=w, center=True, min_periods=1).median()
	return out.to_numpy(dtype=float)


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
	"""Compute comprehensive time-domain HRV metrics.

	Metrics computed (Task Force 1996, Shaffer & Ginsberg 2017):
	- Statistical: mean_nni, sdnn, median_nni, mad_nni, cvnn
	- Heart rate: mean_hr, std_hr, min_hr, max_hr, hr_range
	- Successive differences: rmssd, sdsd, cvsd
	- Threshold crossings: nn50, pnn50, nn20, pnn20, nn10, pnn10
	- Derived: ln_rmssd (natural log), rmssd_cv

	References:
	- Task Force ESC/NASPE (1996). Eur Heart J 17:354-381.
	- Shaffer F, Ginsberg JP (2017). Front Public Health 5:258.
	"""
	if rr_intervals.size == 0:
		return {}
	metrics: Dict[str, float] = {}
	
	# Basic statistical measures
	metrics["mean_nni"] = float(np.mean(rr_intervals))
	metrics["sdnn"] = float(np.std(rr_intervals, ddof=1))
	metrics["median_nni"] = float(np.median(rr_intervals))
	metrics["mad_nni"] = float(np.median(np.abs(rr_intervals - metrics["median_nni"])))
	metrics["cvnn"] = float((metrics["sdnn"] / metrics["mean_nni"]) * 100) if metrics["mean_nni"] > 0 else 0.0
	metrics["range_nni"] = float(np.max(rr_intervals) - np.min(rr_intervals))
	
	# Heart rate derived measures
	hr_values = 60000.0 / rr_intervals
	metrics["mean_hr"] = float(np.mean(hr_values))
	metrics["std_hr"] = float(np.std(hr_values, ddof=1))
	metrics["min_hr"] = float(np.min(hr_values))
	metrics["max_hr"] = float(np.max(hr_values))
	metrics["hr_range"] = float(np.max(hr_values) - np.min(hr_values))
	
	if rr_intervals.size > 1:
		rr_diff = np.diff(rr_intervals)
		rmssd_val = float(np.sqrt(np.mean(rr_diff ** 2)))
		metrics["rmssd"] = rmssd_val
		metrics["sdsd"] = float(np.std(rr_diff, ddof=1))
		mean_abs = float(np.mean(np.abs(rr_diff)))
		metrics["cvsd"] = float((metrics["sdsd"] / mean_abs) * 100) if mean_abs > 0 else 0.0
		
		# Natural log of RMSSD - commonly used in research for normalization
		# Reference: Plews DJ et al. (2013). Int J Sports Physiol Perform.
		metrics["ln_rmssd"] = float(np.log(rmssd_val)) if rmssd_val > 0 else 0.0
		
		# RMSSD coefficient of variation (normalized RMSSD)
		metrics["rmssd_cv"] = float((rmssd_val / metrics["mean_nni"]) * 100) if metrics["mean_nni"] > 0 else 0.0
		
		# Standard threshold crossings
		nn50 = int(np.sum(np.abs(rr_diff) > 50.0))
		metrics["nn50"] = float(nn50)
		metrics["pnn50"] = float((nn50 / rr_diff.size) * 100.0)
		
		nn20 = int(np.sum(np.abs(rr_diff) > 20.0))
		metrics["nn20"] = float(nn20)
		metrics["pnn20"] = float((nn20 / rr_diff.size) * 100.0)
		
		# Additional thresholds (pNN10, pNN30) for finer granularity
		# Reference: Mietus JE et al. (2002). Heart rhythm.
		nn10 = int(np.sum(np.abs(rr_diff) > 10.0))
		metrics["nn10"] = float(nn10)
		metrics["pnn10"] = float((nn10 / rr_diff.size) * 100.0)
		
		nn30 = int(np.sum(np.abs(rr_diff) > 30.0))
		metrics["nn30"] = float(nn30)
		metrics["pnn30"] = float((nn30 / rr_diff.size) * 100.0)
	else:
		metrics.update(dict(
			rmssd=0.0, sdsd=0.0, cvsd=0.0, ln_rmssd=0.0, rmssd_cv=0.0,
			nn50=0.0, pnn50=0.0, nn20=0.0, pnn20=0.0, nn10=0.0, pnn10=0.0,
			nn30=0.0, pnn30=0.0
		))
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
	"""Compute Poincaré plot-derived HRV metrics.

	The Poincaré plot (return map) plots RR(n+1) vs RR(n), providing
	a geometric visualization of heart rate dynamics.

	Metrics computed:
	- SD1: Standard deviation perpendicular to identity line (short-term variability)
		   Mathematically equivalent to RMSSD/√2
	- SD2: Standard deviation along identity line (long-term variability)
		   Related to SDNN and reflects both short and long-term changes
	- SD1/SD2 ratio: Short-to-long-term variability ratio
	- SD2/SD1 ratio: Cardiac Sympathetic Index (CSI) - reflects sympathovagal balance
	- Ellipse area: S = π × SD1 × SD2 (dispersion measure)
	- CVI (Cardiac Vagal Index): log10(SD1 × SD2) - vagal modulation
	- CSI (Cardiac Sympathetic Index): SD2/SD1 - sympathetic modulation

	References:
	- Tulppo MP et al. (1996). Am J Physiol. 271:H244-H252.
	- Toichi M et al. (1997). J Auton Nerv Syst. 62:79-84.
	- Brennan M et al. (2001). IEEE Trans Biomed Eng. 48:1342-1347.
	"""
	if rr_intervals.size < 2:
		return {}
	rr1 = rr_intervals[:-1]
	rr2 = rr_intervals[1:]
	diff = rr2 - rr1
	sum_rr = rr2 + rr1
	
	# Standard Poincaré metrics
	sd1 = float(np.std(diff, ddof=1) / np.sqrt(2.0))
	sd2 = float(np.std(sum_rr, ddof=1) / np.sqrt(2.0))
	
	# Ratios
	sd1_sd2_ratio = float(sd1 / sd2) if sd2 > 0 else 0.0
	sd2_sd1_ratio = float(sd2 / sd1) if sd1 > 0 else 0.0
	
	# Ellipse area
	ellipse_area = float(np.pi * sd1 * sd2) if sd1 > 0 and sd2 > 0 else 0.0
	
	# Cardiac Vagal Index (CVI) - Toichi et al. (1997)
	# CVI = log10(SD1 × SD2) - reflects overall vagal modulation
	cvi = float(np.log10(sd1 * sd2)) if sd1 > 0 and sd2 > 0 else 0.0
	
	# Cardiac Sympathetic Index (CSI) - Toichi et al. (1997)
	# CSI = SD2/SD1 - higher values indicate sympathetic dominance
	csi = sd2_sd1_ratio
	
	# Modified CSI (normalized, bounded 0-10 for practical use)
	csi_modified = float(min(10.0, csi))
	
	# Sample statistics for the plot
	mean_rr1 = float(np.mean(rr1))
	mean_rr2 = float(np.mean(rr2))
	correlation = float(np.corrcoef(rr1, rr2)[0, 1]) if rr1.size > 2 else 0.0
	
	return {
		"sd1": sd1,
		"sd2": sd2,
		"sd1_sd2_ratio": sd1_sd2_ratio,
		"sd2_sd1_ratio": sd2_sd1_ratio,
		"ellipse_area": ellipse_area,
		"cvi": cvi,  # Cardiac Vagal Index
		"csi": csi,  # Cardiac Sympathetic Index
		"csi_modified": csi_modified,
		"poincare_correlation": correlation,
	}


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


def compute_comprehensive_hrv(
	rr_intervals: np.ndarray,
	*,
	include_advanced: bool = True,
) -> Dict[str, Any]:
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
	# DFA is relatively expensive (loop-based); skip it in non-advanced mode for very long series.
	should_compute_dfa = include_advanced or rr_intervals.size <= 20000
	if should_compute_dfa:
		results.update(compute_dfa_metrics(rr_intervals))
	else:
		results["dfa_alpha1"] = np.nan
		results["dfa_alpha2"] = np.nan
	results.update(compute_geometric_metrics(rr_intervals))
	# Heart-rate fragmentation (HRF) metrics are inexpensive (O(n)) and useful across
	# both fast/operational and advanced/research views, so compute them regardless
	# of the include_advanced flag.
	results.update(compute_heart_rate_fragmentation(rr_intervals))
	# Add extended HRF (Heart Rate Fragmentation) metrics for research-grade analysis.
	# This complements the lightweight `compute_heart_rate_fragmentation` outputs and
	# enables richer performance/correlation analysis.
	try:
		from hrv_fragmentation import compute_hrf_metrics  # noqa: PLC0415
	except Exception:
		compute_hrf_metrics = None  # type: ignore[assignment]
	if compute_hrf_metrics is not None:
		hrf = compute_hrf_metrics(rr_intervals)
		# Percent-based HRF features (0..100).
		results["hrf_pip_h_pct"] = float(hrf.pip_h)
		results["hrf_pip_s_pct"] = float(hrf.pip_s)
		results["hrf_pas_pct"] = float(hrf.pas)
		results["hrf_w0_pct"] = float(hrf.w0)
		results["hrf_w1_pct"] = float(hrf.w1)
		results["hrf_w2_pct"] = float(hrf.w2)
		results["hrf_w3_pct"] = float(hrf.w3)
		results["hrf_w3"] = float(hrf.w3)
		results["hrf_quality_ok"] = bool(hrf.quality_ok)
	# Convenience alias used by some gauge configurations.
	if "hrf_pip_pct" in results:
		results["hrf_pip"] = float(results["hrf_pip_pct"])

	# Entropy metrics are computationally heavy (O(n^2)); treat as advanced.
	if include_advanced:
		results.update(compute_entropy_metrics(rr_intervals, m=2, r_ratio=0.2))
		results.update(compute_phase_rectified_capacity(rr_intervals, scale=2))
		results.update(compute_symbolic_dynamics_metrics(rr_intervals))
		results.update(compute_permutation_entropy(rr_intervals, order=3, delay=1))
		results.update(compute_mfdfa_metrics(rr_intervals))
		results.update(compute_rqa_metrics(rr_intervals))
		results.update(compute_frequency_domain_entropy(rr_intervals))
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
		if include_advanced:
			norm_metrics = compute_hr_normalized_metrics(
				mean_hr_bpm=float(results.get("mean_hr", 0.0)),
				rmssd_ms=float(results.get("rmssd", 0.0)),
			)
			results.update(norm_metrics)
	return results


def compute_long_term_metrics(
	rr_intervals: np.ndarray,
	*,
	segment_duration_ms: float = 300000.0,  # 5 minutes default
) -> Dict[str, float]:
	"""Compute long-term HRV metrics for extended recordings (≥1 hour).

	These metrics are designed for 24-hour Holter recordings but can be
	applied to any recording longer than ~1 hour that can be segmented
	into 5-minute epochs.

	Metrics computed:
	- SDANN: Standard deviation of average NN intervals in each 5-min segment
			 Reflects circadian/ultradian rhythms and long-term variability
	- SDNNi: Mean of the standard deviations of NN intervals in all segments
			 Reflects short-term variability averaged over long recording
	- SDANN/SDNNi ratio: Long-term vs short-term variability ratio

	Reference: Task Force ESC/NASPE (1996). Eur Heart J 17:354-381.

	Args:
		rr_intervals: RR intervals in milliseconds (continuous series).
		segment_duration_ms: Duration of each segment in ms (default 5 min).

	Returns:
		Dictionary with SDANN, SDNNi, and related metrics.
	"""
	total_duration_ms = float(np.sum(rr_intervals))
	
	# Need at least 2 segments to compute SDANN
	if total_duration_ms < 2 * segment_duration_ms:
		return {
			"sdann": 0.0,
			"sdnni": 0.0,
			"sdann_sdnni_ratio": 0.0,
			"n_segments": 0.0,
			"total_duration_hours": total_duration_ms / 3600000.0,
		}
	
	# Segment the recording into epochs
	segment_means: List[float] = []
	segment_stds: List[float] = []
	
	cumsum_ms = np.cumsum(rr_intervals)
	segment_start_idx = 0
	segment_start_ms = 0.0
	
	for idx in range(len(cumsum_ms)):
		segment_end_ms = cumsum_ms[idx]
		if segment_end_ms - segment_start_ms >= segment_duration_ms:
			# Complete segment found
			segment_rr = rr_intervals[segment_start_idx : idx + 1]
			if segment_rr.size >= 30:  # Minimum beats per segment
				segment_means.append(float(np.mean(segment_rr)))
				if segment_rr.size > 1:
					segment_stds.append(float(np.std(segment_rr, ddof=1)))
			# Start new segment
			segment_start_idx = idx + 1
			segment_start_ms = segment_end_ms
	
	n_segments = len(segment_means)
	if n_segments < 2:
		return {
			"sdann": 0.0,
			"sdnni": 0.0,
			"sdann_sdnni_ratio": 0.0,
			"n_segments": float(n_segments),
			"total_duration_hours": total_duration_ms / 3600000.0,
		}
	
	# SDANN: SD of segment means
	sdann = float(np.std(segment_means, ddof=1))
	
	# SDNNi: Mean of segment SDs
	sdnni = float(np.mean(segment_stds)) if segment_stds else 0.0
	
	# Ratio
	ratio = float(sdann / sdnni) if sdnni > 0 else 0.0
	
	return {
		"sdann": sdann,
		"sdnni": sdnni,
		"sdann_sdnni_ratio": ratio,
		"n_segments": float(n_segments),
		"total_duration_hours": total_duration_ms / 3600000.0,
	}


def compute_ultra_short_metrics(
	rr_intervals: np.ndarray,
	*,
	duration_seconds: int = 60,
) -> Dict[str, float]:
	"""Compute HRV metrics validated for ultra-short recordings (<5 min).

	Ultra-short HRV analysis (1-3 minutes) uses specific metrics that have
	been validated against standard 5-minute recordings.

	Validated ultra-short metrics (Shaffer & Ginsberg 2017; Munoz et al. 2015):
	- RMSSD: Remains valid down to 10-second windows
	- ln(RMSSD): Log-transformed RMSSD for normalization
	- pNN50: Valid for ≥1 minute recordings
	- SD1: Equivalent to RMSSD/√2, valid for ultra-short

	NOT recommended for ultra-short:
	- SDNN: Requires ≥5 minutes for stability
	- Frequency domain: Requires ≥2 minutes for LF, ≥1 min for HF

	Args:
		rr_intervals: RR intervals in milliseconds.
		duration_seconds: Actual recording duration in seconds.

	Returns:
		Dictionary with ultra-short-validated metrics and quality flags.
	"""
	if rr_intervals.size < 10:
		return {
			"uss_rmssd": 0.0,
			"uss_ln_rmssd": 0.0,
			"uss_pnn50": 0.0,
			"uss_sd1": 0.0,
			"uss_mean_hr": 0.0,
			"uss_quality": "insufficient_data",
		}
	
	# Compute validated ultra-short metrics
	rr_diff = np.diff(rr_intervals)
	rmssd = float(np.sqrt(np.mean(rr_diff ** 2))) if rr_diff.size > 0 else 0.0
	ln_rmssd = float(np.log(rmssd)) if rmssd > 0 else 0.0
	
	nn50 = int(np.sum(np.abs(rr_diff) > 50.0))
	pnn50 = float((nn50 / rr_diff.size) * 100.0) if rr_diff.size > 0 else 0.0
	
	# SD1 from Poincaré (equivalent to RMSSD/√2)
	sd1 = float(np.std(rr_diff, ddof=1) / np.sqrt(2.0)) if rr_diff.size > 1 else 0.0
	
	# Mean HR
	mean_hr = float(60000.0 / np.mean(rr_intervals)) if np.mean(rr_intervals) > 0 else 0.0
	
	# Quality assessment
	if duration_seconds < 30:
		quality = "very_short"
	elif duration_seconds < 60:
		quality = "short"
	elif duration_seconds < 180:
		quality = "moderate"
	else:
		quality = "good"
	
	return {
		"uss_rmssd": rmssd,
		"uss_ln_rmssd": ln_rmssd,
		"uss_pnn50": pnn50,
		"uss_sd1": sd1,
		"uss_mean_hr": mean_hr,
		"uss_quality": quality,
	}


def compute_windowed_hrv(
	df_in: pd.DataFrame,
	*,
	rr_col: str = "rr_intervals_ms",
	timestamp_col: str = "timestamp",
	window: str = "5min",
	step: str = "1min",
	min_rr_count: int = 60,
	max_windows: int = 500,
	include_advanced: bool = True,
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
		# Fast path: time-domain only when include_advanced is False
		if include_advanced:
			metrics = compute_comprehensive_hrv(rr, include_advanced=True)
		else:
			metrics = compute_time_domain_metrics(rr)
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
	elif method == "ar":
		# Match AR PSD approach used by compute_frequency_domain_metrics.
		order = int(min(16, max(4, len(rr_det) // 20)))
		x = rr_det - np.mean(rr_det)
		r = np.correlate(x, x, mode="full")[len(x) - 1 : len(x) - 1 + order + 1] / len(x)
		R = linalg.toeplitz(r[:-1])
		try:
			a = np.linalg.solve(R, -r[1:])
			sigma2 = float(r[0] + np.dot(a, r[1:]))
		except Exception:
			a = np.zeros(order, dtype=float)
			sigma2 = float(np.var(x))
		freqs = np.linspace(0.0, sampling_rate / 2.0, num=512, endpoint=True)
		w = 2.0 * np.pi * freqs / sampling_rate
		den = np.ones_like(freqs, dtype=complex)
		for k in range(1, order + 1):
			den += a[k - 1] * np.exp(-1j * w * k)
		psd = (sigma2 / (np.abs(den) ** 2)).real
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
	
	References:
	- Baevsky RM, Chernikova AG (2017). Heart rate variability analysis: physiological foundations and main methods.
	  Cardiometry 10:66-76.
	- Baevsky RM, Baranov VM, Funtova II, et al. (2007). Autonomic cardiovascular and respiratory control during
	  105-day head-down bed rest. Aviat Space Environ Med 78(5):463-470.
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


def compute_baevsky_stress_index(rr_intervals: np.ndarray, *, bin_width_ms: float = 50.0) -> float:
	"""Calculate Baevsky Stress Index using proper 50ms bin width as per scientific literature.
	
	Formula: SI = AMo / (2 × Mo × MxDMn)
	Where:
	- AMo = amplitude of mode (fraction 0-1 of RR intervals in the mode bin)
	- Mo = mode (most frequent RR interval) in milliseconds
	- MxDMn = variation scope (difference between shortest and longest RR interval) in milliseconds
	
	This implementation uses 50ms bin width (per literature) but maintains the same units
	as compute_geometric_metrics to ensure consistency with existing stored values.
	
	References:
	- Baevsky RM, Chernikova AG (2017). Heart rate variability analysis: physiological foundations and main methods.
	  Cardiometry 10:66-76. DOI: 10.12710/cardiometry.2017.10.6676
	- Baevsky RM, Baranov VM, Funtova II, et al. (2007). Autonomic cardiovascular and respiratory control during
	  105-day head-down bed rest. Aviat Space Environ Med 78(5):463-470.
	- Frontiers in Physiology (2021). Optimizing Autonomic Function Analysis via Heart Rate Variability.
	  DOI: 10.3389/fphys.2021.619722
	
	Args:
		rr_intervals: RR intervals in milliseconds
		bin_width_ms: Histogram bin width in milliseconds (default 50ms per literature)
		
	Returns:
		Baevsky Stress Index (typically 0-500, higher = more stress)
		Note: Values match compute_geometric_metrics implementation for consistency
	"""
	if rr_intervals.size < 10:
		return 0.0
	
	rr = rr_intervals.astype(float)
	# Remove outliers (RR intervals outside physiological range: 300-2000 ms)
	rr = rr[(rr >= 300) & (rr <= 2000)]
	if rr.size < 10:
		return 0.0
	
	min_v = float(np.min(rr))
	max_v = float(np.max(rr))
	if not np.isfinite(min_v) or not np.isfinite(max_v) or max_v <= min_v:
		return 0.0
	
	# Create histogram with 50ms bin width (per scientific literature)
	bins = int(max(10, np.ceil((max_v - min_v) / bin_width_ms)))
	hist, edges = np.histogram(rr, bins=bins, range=(min_v, max_v))
	
	if hist.size == 0 or np.max(hist) == 0:
		return 0.0
	
	# Find mode (most frequent RR interval)
	mode_idx = int(np.argmax(hist))
	mode_center_ms = float((edges[mode_idx] + edges[mode_idx + 1]) / 2.0)
	
	# AMo = amplitude of mode (fraction 0-1, NOT percentage)
	# Per literature: AMo is the fraction of intervals in the mode bin
	# This matches the original compute_geometric_metrics implementation
	N = int(rr.size)
	AMo = float(hist[mode_idx] / N) if N > 0 else 0.0  # Fraction (0-1), not percentage
	
	# MxDMn = variation scope (range) in milliseconds
	# Keep in milliseconds to match original implementation and existing stored values
	MxDMn_ms = float(max_v - min_v)
	
	# Calculate Baevsky Stress Index
	# Formula: SI = AMo / (2 * Mo * MxDMn)
	# Where AMo is fraction (0-1), Mo is in ms, MxDMn is in ms
	# This matches the original compute_geometric_metrics implementation for consistency
	if mode_center_ms > 0 and MxDMn_ms > 0:
		si = AMo / (2.0 * mode_center_ms * MxDMn_ms)
		return float(si)
	
	return 0.0


def compute_parasympathetic_index(
	rr_intervals: np.ndarray,
	age: int,
	*,
	rmssd_ms: Optional[float] = None,
	pnn50_pct: Optional[float] = None,
) -> float:
	"""Calculate Parasympathetic Index (0-10 scale) from RR intervals using age-adjusted norms.
	
	The Parasympathetic Index reflects vagal tone and recovery capacity. Higher values (7-10) indicate
	strong parasympathetic activity, while lower values (1-4) suggest reduced vagal tone.
	
	Calculation based on:
	1. RMSSD (primary parasympathetic indicator)
	2. pNN50 (percentage of successive intervals differing by >50ms)
	3. Age-adjusted reference ranges (Nunan et al. 2010, Shaffer & Ginsberg 2017)
	
	References:
	- Nunan D, Sandercock GR, Brodie DA (2010). A quantitative systematic review of normal values for
	  short-term heart rate variability in healthy adults. Pacing Clin Electrophysiol 33(11):1407-1417.
	  DOI: 10.1111/j.1540-8159.2010.02841.x
	- Shaffer F, Ginsberg JP (2017). An overview of heart rate variability metrics and norms.
	  Front Public Health 5:258. DOI: 10.3389/fpubh.2017.00258
	- Task Force of the European Society of Cardiology and the North American Society of Pacing and
	  Electrophysiology (1996). Heart rate variability: standards of measurement, physiological
	  interpretation and clinical use. Eur Heart J 17(3):354-381.
	
	Args:
		rr_intervals: RR intervals in milliseconds
		age: Age in years (for age-adjusted norms)
		rmssd_ms: Pre-calculated RMSSD in ms (optional, will compute if not provided)
		pnn50_pct: Pre-calculated pNN50 percentage (optional, will compute if not provided)
		
	Returns:
		Parasympathetic Index (0-10 scale, higher = better parasympathetic activity)
	"""
	if rr_intervals.size < 10:
		return 0.0
	
	# Calculate RMSSD if not provided
	if rmssd_ms is None:
		rr = rr_intervals.astype(float)
		rr = rr[(rr >= 300) & (rr <= 2000)]  # Remove outliers
		if rr.size < 2:
			return 0.0
		diff_rr = np.diff(rr)
		rmssd_ms = float(np.sqrt(np.mean(diff_rr ** 2)))
	
	# Calculate pNN50 if not provided
	if pnn50_pct is None:
		rr = rr_intervals.astype(float)
		rr = rr[(rr >= 300) & (rr <= 2000)]  # Remove outliers
		if rr.size < 2:
			return 0.0
		diff_rr = np.diff(rr)
		nn50 = np.sum(np.abs(diff_rr) > 50)
		pnn50_pct = float((nn50 / len(diff_rr)) * 100.0) if len(diff_rr) > 0 else 0.0
	
	# Age-adjusted RMSSD reference values (Nunan et al. 2010)
	age_groups = [
		((18, 25), (42.0, 19.0, 19.0, 75.0)),  # (mean, sd, p5, p95)
		((26, 35), (39.0, 18.0, 17.0, 70.0)),
		((36, 45), (35.0, 17.0, 15.0, 63.0)),
		((46, 55), (30.0, 15.0, 12.0, 55.0)),
		((56, 65), (25.0, 13.0, 10.0, 48.0)),
		((66, 100), (21.0, 11.0, 8.0, 40.0)),
	]
	
	# Find age group
	age_mean, age_sd, age_p5, age_p95 = 30.0, 15.0, 12.0, 55.0  # Default: 46-55
	for (age_min, age_max), (mean, sd, p5, p95) in age_groups:
		if age_min <= age <= age_max:
			age_mean, age_sd, age_p5, age_p95 = mean, sd, p5, p95
			break
	
	# Calculate ln(RMSSD) for normalization (more normally distributed)
	ln_rmssd = np.log(rmssd_ms) if rmssd_ms > 0 else 0.0
	ln_mean = np.log(age_mean) if age_mean > 0 else 0.0
	ln_p5 = np.log(age_p5) if age_p5 > 0 else 0.0
	ln_p95 = np.log(age_p95) if age_p95 > 0 else 0.0
	
	# Normalize to 0-10 scale
	# High parasympathetic (p95+): 8-10
	# Good parasympathetic (p50-p95): 6-8
	# Normal (p5-p50): 4-6
	# Low (below p5): 1-4
	
	if ln_rmssd >= ln_p95:
		# Excellent parasympathetic activity (top 5%)
		pns_index = 8.0 + min(2.0, ((ln_rmssd - ln_p95) / (ln_p95 - ln_mean)) * 2.0)
	elif ln_rmssd >= ln_mean:
		# Good parasympathetic activity (above mean)
		pns_index = 6.0 + ((ln_rmssd - ln_mean) / (ln_p95 - ln_mean)) * 2.0
	elif ln_rmssd >= ln_p5:
		# Normal parasympathetic activity
		pns_index = 4.0 + ((ln_rmssd - ln_p5) / (ln_mean - ln_p5)) * 2.0
	else:
		# Low parasympathetic activity (below 5th percentile)
		pns_index = max(1.0, 1.0 + ((ln_rmssd / ln_p5) * 3.0)) if ln_p5 > 0 else 1.0
	
	# Adjust based on pNN50 (secondary parasympathetic indicator)
	# pNN50 reference: typically 5-20% in healthy adults, decreases with age
	pnn50_factor = 1.0
	if pnn50_pct > 15:
		pnn50_factor = 1.1  # Boost if pNN50 is high
	elif pnn50_pct < 2:
		pnn50_factor = 0.9  # Reduce if pNN50 is very low
	
	pns_index = float(np.clip(pns_index * pnn50_factor, 0.0, 10.0))
	
	return pns_index


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


def compute_heart_rate_fragmentation(rr_intervals: np.ndarray) -> Dict[str, float]:
	"""Compute heart rate fragmentation metrics (PIP, IALS, PSS).

	Args:
		rr_intervals: RR interval series in milliseconds.

	Returns:
		Dictionary with HRF metrics expressed in percentage/beat units.
	"""
	if rr_intervals.size < 5:
		return {
			"hrf_pip_pct": 0.0,
			"hrf_ials": 0.0,
			"hrf_pss_pct": 0.0,
			"hrf_segment_count": 0.0,
		}
	diff = np.diff(rr_intervals.astype(float))
	signs = np.sign(diff)
	prev_sign = 0.0
	inflections = 0
	valid_transitions = 0
	for sign in signs:
		if sign == 0.0:
			continue
		if prev_sign != 0.0:
			valid_transitions += 1
			if sign != prev_sign:
				inflections += 1
		prev_sign = sign
	pip = float(100.0 * inflections / valid_transitions) if valid_transitions > 0 else 0.0
	segment_lengths: List[int] = []
	current_sign = 0.0
	current_run = 0
	for sign in signs:
		if sign == 0.0:
			if current_run > 0:
				segment_lengths.append(current_run + 1)
				current_run = 0
				current_sign = 0.0
			continue
		if sign == current_sign:
			current_run += 1
		else:
			if current_run > 0:
				segment_lengths.append(current_run + 1)
			current_sign = sign
			current_run = 1
	if current_run > 0:
		segment_lengths.append(current_run + 1)
	if not segment_lengths:
		return {
			"hrf_pip_pct": pip,
			"hrf_ials": 0.0,
			"hrf_pss_pct": 0.0,
			"hrf_segment_count": 0.0,
		}
	segments = np.asarray(segment_lengths, dtype=float)
	mean_length = float(np.mean(segments))
	ials = float(1.0 / mean_length) if mean_length > 0.0 else 0.0
	pss = float(100.0 * np.sum(segments < 3.0) / segments.size)
	return {
		"hrf_pip_pct": pip,
		"hrf_ials": ials,
		"hrf_pss_pct": pss,
		"hrf_segment_count": float(segments.size),
	}


def compute_phase_rectified_capacity(
	rr_intervals: np.ndarray,
	*,
	scale: int = 2,
) -> Dict[str, float]:
	"""Compute deceleration and acceleration capacities using PRSA."""
	if rr_intervals.size < (2 * scale + 1) or scale < 1:
		return {
			"deceleration_capacity": 0.0,
			"acceleration_capacity": 0.0,
			"dc_anchor_count": 0.0,
			"ac_anchor_count": 0.0,
		}
	rr = rr_intervals.astype(float)
	window = 2 * scale + 1
	dc_segments: List[np.ndarray] = []
	ac_segments: List[np.ndarray] = []
	for idx in range(scale, rr.size - scale):
		delta = rr[idx] - rr[idx - 1]
		segment = rr[idx - scale : idx + scale + 1]
		if segment.size != window:
			continue
		if delta > 0:
			dc_segments.append(segment)
		elif delta < 0:
			ac_segments.append(segment)
	if dc_segments:
		dc_stack = np.vstack(dc_segments)
		pre = dc_stack[:, :scale]
		post = dc_stack[:, scale + 1 :]
		dc = float(np.mean(post) - np.mean(pre))
	else:
		dc = 0.0
	if ac_segments:
		ac_stack = np.vstack(ac_segments)
		pre = ac_stack[:, :scale]
		post = ac_stack[:, scale + 1 :]
		ac = float(np.mean(post) - np.mean(pre))
	else:
		ac = 0.0
	return {
		"deceleration_capacity": dc,
		"acceleration_capacity": ac,
		"dc_anchor_count": float(len(dc_segments)),
		"ac_anchor_count": float(len(ac_segments)),
	}


def compute_symbolic_dynamics_metrics(
	rr_intervals: np.ndarray,
	*,
	levels: int = 6,
	pattern_length: int = 3,
) -> Dict[str, float]:
	"""Compute symbolic dynamics pattern percentages (0V, 1V, 2LV, 2UV)."""
	if rr_intervals.size < pattern_length or levels < 2:
		return {
			"symbolic_0v_pct": 0.0,
			"symbolic_1v_pct": 0.0,
			"symbolic_2lv_pct": 0.0,
			"symbolic_2uv_pct": 0.0,
		}
	rr = rr_intervals.astype(float)
	min_rr = float(np.min(rr))
	max_rr = float(np.max(rr))
	if not np.isfinite(min_rr) or not np.isfinite(max_rr) or max_rr <= min_rr:
		return {
			"symbolic_0v_pct": 0.0,
			"symbolic_1v_pct": 0.0,
			"symbolic_2lv_pct": 0.0,
			"symbolic_2uv_pct": 0.0,
		}
	bins = np.linspace(min_rr, max_rr, num=levels + 1)
	symbols = np.digitize(rr, bins[1:-1], right=False)
	total_patterns = rr.size - pattern_length + 1
	if total_patterns <= 0:
		return {
			"symbolic_0v_pct": 0.0,
			"symbolic_1v_pct": 0.0,
			"symbolic_2lv_pct": 0.0,
			"symbolic_2uv_pct": 0.0,
		}
	counts = {"0V": 0, "1V": 0, "2LV": 0, "2UV": 0}
	for start in range(total_patterns):
		pattern = symbols[start : start + pattern_length]
		if np.all(pattern == pattern[0]):
			counts["0V"] += 1
			continue
		if np.all(np.diff(pattern) > 0) or np.all(np.diff(pattern) < 0):
			counts["2LV"] += 1
			continue
		if pattern[0] != pattern[1] and pattern[1] != pattern[2] and (
			(pattern[0] < pattern[1] > pattern[2]) or (pattern[0] > pattern[1] < pattern[2])
		):
			counts["2UV"] += 1
		else:
			counts["1V"] += 1
	return {
		"symbolic_0v_pct": float(100.0 * counts["0V"] / total_patterns),
		"symbolic_1v_pct": float(100.0 * counts["1V"] / total_patterns),
		"symbolic_2lv_pct": float(100.0 * counts["2LV"] / total_patterns),
		"symbolic_2uv_pct": float(100.0 * counts["2UV"] / total_patterns),
	}


def compute_permutation_entropy(
	rr_intervals: np.ndarray,
	*,
	order: int = 3,
	delay: int = 1,
) -> Dict[str, float]:
	"""Compute permutation entropy (absolute and normalized)."""
	if order < 2 or delay < 1:
		raise ValueError("order must be >=2 and delay must be >=1")
	n = int(rr_intervals.size)
	window = (order - 1) * delay
	if n <= window:
		return {"permutation_entropy": 0.0, "permutation_entropy_norm": 0.0}
	data = rr_intervals.astype(float)
	pattern_counts: Dict[Tuple[int, ...], int] = {}
	for start in range(n - window):
		indices = range(start, start + order * delay, delay)
		window_values = data[list(indices)]
		ranks = tuple(np.argsort(window_values, kind="mergesort"))
		pattern_counts[ranks] = pattern_counts.get(ranks, 0) + 1
	counts = np.array(list(pattern_counts.values()), dtype=float)
	probabilities = counts / np.sum(counts)
	entropy = float(-np.sum(probabilities * np.log(probabilities + 1e-12)))
	max_entropy = math.log(math.factorial(order))
	normalized = float(entropy / max_entropy) if max_entropy > 0 else 0.0
	return {"permutation_entropy": entropy, "permutation_entropy_norm": normalized}


def _mfdfa_segment_rms(profile: np.ndarray, scale: int, order: int) -> np.ndarray:
	segments = profile.size // scale
	if segments < 2:
		return np.array([], dtype=float)
	rms_values: List[float] = []
	for start in range(0, segments * scale, scale):
		segment = profile[start : start + scale]
		x = np.arange(segment.size)
		coeffs = np.polyfit(x, segment, order)
		trend = np.polyval(coeffs, x)
		detrended = segment - trend
		rms_values.append(float(np.sqrt(np.mean(detrended**2))))
	return np.asarray(rms_values, dtype=float)


def _mfdfa_prepare_maps(
	profile: np.ndarray,
	scales: Sequence[int],
	q_values: Sequence[float],
	order: int,
) -> Tuple[np.ndarray, Dict[float, np.ndarray]]:
	log_scales: List[float] = []
	fq_maps: Dict[float, List[float]] = {q: [] for q in q_values}
	for scale in scales:
		rms_values = _mfdfa_segment_rms(profile, scale, order)
		if rms_values.size == 0:
			continue
		log_scales.append(math.log(scale))
		for q in q_values:
			if abs(q) < 1e-8:
				value = float(math.exp(np.mean(np.log(rms_values + 1e-12))))
			else:
				rms_q = np.mean(rms_values**q)
				value = float(rms_q ** (1.0 / q)) if rms_q > 0 else 0.0
			fq_maps[q].append(math.log(value + 1e-12))
	log_scales_arr = np.asarray(log_scales, dtype=float)
	return log_scales_arr, {q: np.asarray(vals, dtype=float) for q, vals in fq_maps.items()}


def _mfdfa_estimate_hurst(
	log_scales: np.ndarray,
	fq_maps: Dict[float, np.ndarray],
) -> Tuple[np.ndarray, np.ndarray]:
	if log_scales.size == 0:
		return np.array([], dtype=float), np.array([], dtype=float)
	q_list: List[float] = []
	h_values: List[float] = []
	for q, values in fq_maps.items():
		if values.size != log_scales.size:
			continue
		slope, _ = np.polyfit(log_scales, values, 1)
		q_list.append(float(q))
		h_values.append(float(slope))
	q_arr = np.asarray(q_list, dtype=float)
	h_arr = np.asarray(h_values, dtype=float)
	if q_arr.size <= 1:
		return q_arr, h_arr
	order = np.argsort(q_arr)
	return q_arr[order], h_arr[order]


def compute_mfdfa_metrics(
	rr_intervals: np.ndarray,
	*,
	order: int = 1,
	scales: Optional[Sequence[int]] = None,
	q_values: Optional[Sequence[float]] = None,
) -> Dict[str, float]:
	"""Compute multifractal DFA spectrum width and related statistics."""
	if rr_intervals.size < 128:
		return {
			"mfdfa_width": 0.0,
			"mfdfa_alpha_min": 0.0,
			"mfdfa_alpha_max": 0.0,
			"mfdfa_hurst_mean": 0.0,
		}
	rr = rr_intervals.astype(float)
	profile = np.cumsum(rr - np.mean(rr))
	if scales is None:
		max_scale = max(16, int(rr.size // 10))
		scales = [s for s in range(16, max_scale, 8) if s > order + 1]
	if not scales:
		return {
			"mfdfa_width": 0.0,
			"mfdfa_alpha_min": 0.0,
			"mfdfa_alpha_max": 0.0,
			"mfdfa_hurst_mean": 0.0,
		}
	if q_values is None:
		q_values = (-5.0, -3.0, -1.0, 0.0, 1.0, 3.0, 5.0)
	log_scales, fq_maps = _mfdfa_prepare_maps(profile, scales, q_values, order)
	if log_scales.size == 0:
		return {
			"mfdfa_width": 0.0,
			"mfdfa_alpha_min": 0.0,
			"mfdfa_alpha_max": 0.0,
			"mfdfa_hurst_mean": 0.0,
		}
	q_arr, h_arr = _mfdfa_estimate_hurst(log_scales, fq_maps)
	if h_arr.size == 0:
		return {
			"mfdfa_width": 0.0,
			"mfdfa_alpha_min": 0.0,
			"mfdfa_alpha_max": 0.0,
			"mfdfa_hurst_mean": 0.0,
		}
	tau = q_arr * h_arr - 1.0
	alpha = np.gradient(tau, q_arr, edge_order=1) + h_arr
	f_alpha = q_arr * alpha - tau
	alpha_min = float(np.min(alpha))
	alpha_max = float(np.max(alpha))
	width = float(alpha_max - alpha_min)
	return {
		"mfdfa_width": width,
		"mfdfa_alpha_min": alpha_min,
		"mfdfa_alpha_max": alpha_max,
		"mfdfa_hurst_mean": float(np.mean(h_arr)),
	}


def _run_lengths(sequence: Iterable[int]) -> List[int]:
	lengths: List[int] = []
	current = 0
	for item in sequence:
		if item:
			current += 1
		elif current > 0:
			lengths.append(current)
			current = 0
	if current > 0:
		lengths.append(current)
	return lengths


def compute_rqa_metrics(
	rr_intervals: np.ndarray,
	*,
	embedding_dim: int = 2,
	delay: int = 1,
	radius: Optional[float] = None,
	min_diag: int = 2,
	min_vert: int = 2,
) -> Dict[str, float]:
	"""Compute recurrence quantification analysis metrics."""
	if embedding_dim < 1 or delay < 1:
		raise ValueError("embedding_dim must be >=1 and delay must be >=1")
	n = int(rr_intervals.size)
	required = (embedding_dim - 1) * delay + 1
	if n < required or n < 32:
		return {
			"rqa_rr": 0.0,
			"rqa_det": 0.0,
			"rqa_lam": 0.0,
			"rqa_lmax": 0.0,
		}
	rr = rr_intervals.astype(float)
	embedded = []
	for start in range(0, n - required + 1):
		indices = [start + i * delay for i in range(embedding_dim)]
		embedded.append(rr[indices])
	matrix = np.asarray(embedded, dtype=float)
	if matrix.shape[0] < 2:
		return {
			"rqa_rr": 0.0,
			"rqa_det": 0.0,
			"rqa_lam": 0.0,
			"rqa_lmax": 0.0,
		}
	diff = matrix[:, None, :] - matrix[None, :, :]
	distances = np.sqrt(np.sum(diff**2, axis=2))
	if radius is None:
		std = float(np.std(distances))
		radius = 0.1 * std if std > 0 else 1e-6
	recur = (distances <= radius).astype(int)
	np.fill_diagonal(recur, 0)
	total_points = float(np.sum(recur))
	if total_points <= 0:
		return {
			"rqa_rr": 0.0,
			"rqa_det": 0.0,
			"rqa_lam": 0.0,
			"rqa_lmax": 0.0,
		}
	N = recur.shape[0]
	rqa_rr = float(total_points / (N * N))
	diag_lengths: List[int] = []
	for offset in range(-(N - 1), N):
		diag = np.diag(recur, k=offset)
		diag_lengths.extend(_run_lengths(diag))
	det_lengths = [length for length in diag_lengths if length >= min_diag]
	det_points = float(sum(det_lengths))
	rqa_det = float(det_points / total_points) if total_points > 0 else 0.0
	lmax = float(max(det_lengths)) if det_lengths else 0.0
	lam_lengths: List[int] = []
	for col in recur.T:
		lam_lengths.extend(_run_lengths(col))
	lam_selected = [length for length in lam_lengths if length >= min_vert]
	lam_points = float(sum(lam_selected))
	rqa_lam = float(lam_points / total_points) if total_points > 0 else 0.0
	return {
		"rqa_rr": rqa_rr,
		"rqa_det": rqa_det,
		"rqa_lam": rqa_lam,
		"rqa_lmax": lmax,
	}


def compute_frequency_domain_entropy(
	rr_intervals: np.ndarray,
	*,
	sampling_rate: float = 4.0,
	method: str = "welch",
) -> Dict[str, float]:
	"""Compute entropy-based frequency-domain HRV metrics."""
	freqs, psd = psd_curve(rr_intervals, sampling_rate=sampling_rate, method=method)
	if freqs.size == 0:
		return {
			"entropy_lf": 0.0,
			"entropy_hf": 0.0,
			"entropy_total": 0.0,
			"entropy_lf_hf_ratio": 0.0,
		}

	def _band_entropy(mask: np.ndarray) -> float:
		selected = psd[mask]
		if selected.size <= 1:
			return 0.0
		prob = selected / np.sum(selected)
		entropy = -np.sum(prob * np.log(prob + 1e-12))
		return float(entropy / math.log(selected.size))

	lf_mask = (freqs >= 0.04) & (freqs < 0.15)
	hf_mask = (freqs >= 0.15) & (freqs <= 0.4)
	valid_mask = freqs > 0.0
	total_entropy = _band_entropy(valid_mask)
	lf_entropy = _band_entropy(lf_mask)
	hf_entropy = _band_entropy(hf_mask)
	ratio = float(lf_entropy / hf_entropy) if hf_entropy > 0 else 0.0
	return {
		"entropy_lf": lf_entropy,
		"entropy_hf": hf_entropy,
		"entropy_total": total_entropy,
		"entropy_lf_hf_ratio": ratio,
	}


@dataclass(frozen=True, slots=True)
class MasterCurveParams:
	"""Parameters for heart-rate normalization of RMSSD."""

	amplitude: float = 44.0
	decay: float = 0.033
	offset: float = 5.0
	hr_reference: float = 50.0


def compute_hr_normalized_metrics(
	mean_hr_bpm: float,
	rmssd_ms: float,
	*,
	params: MasterCurveParams = MasterCurveParams(),
) -> Dict[str, float]:
	"""Normalize RMSSD against a master curve to reduce heart-rate dependence."""
	if not np.isfinite(mean_hr_bpm) or mean_hr_bpm <= 0.0 or not np.isfinite(rmssd_ms) or rmssd_ms < 0.0:
		return {
			"rmssd_master_expected": 0.0,
			"rmssd_master_ratio": 0.0,
			"rmssd_master_residual": 0.0,
		}
	adjusted_hr = float(mean_hr_bpm - params.hr_reference)
	expected = params.amplitude * math.exp(-params.decay * adjusted_hr) + params.offset
	if expected <= 0.0:
		return {
			"rmssd_master_expected": expected,
			"rmssd_master_ratio": 0.0,
			"rmssd_master_residual": rmssd_ms,
		}
	ratio = float(rmssd_ms / expected)
	residual = float(rmssd_ms - expected)
	return {
		"rmssd_master_expected": float(expected),
		"rmssd_master_ratio": ratio,
		"rmssd_master_residual": residual,
	}


def _relative_seconds_from_timestamps(timestamps: pd.Series) -> np.ndarray:
	"""Convert a datetime-like pandas Series to seconds relative to the first timestamp."""
	if timestamps.empty:
		raise ValueError("timestamps series must contain at least one value")
	if not pd.api.types.is_datetime64_any_dtype(timestamps):
		raise TypeError("timestamps series must be datetime64 dtype")
	start = timestamps.iloc[0]
	relative = (timestamps - start).dt.total_seconds()
	return relative.to_numpy(dtype=float)


def _validate_window(window: Tuple[float, float], label: str) -> Tuple[float, float]:
	"""Validate and return a (start, end) window in seconds."""
	if len(window) != 2:
		raise ValueError(f"{label} must contain exactly two values (start, end)")
	start, end = float(window[0]), float(window[1])
	if not np.isfinite(start) or not np.isfinite(end):
		raise ValueError(f"{label} must contain finite numeric values")
	if end <= start:
		raise ValueError(f"{label} end must be greater than start")
	return start, end


def _extract_window_values(
	relative_seconds: np.ndarray,
	values: np.ndarray,
	window: Tuple[float, float],
	label: str,
) -> np.ndarray:
	"""Return values whose corresponding times fall within the given window."""
	start, end = _validate_window(window, label)
	if relative_seconds.size != values.size:
		raise ValueError("relative_seconds and values must share the same length")
	mask = (relative_seconds >= start) & (relative_seconds <= end)
	window_values = values[mask]
	if window_values.size == 0:
		raise ValueError(f"No samples found inside {label} window ({start}–{end} s)")
	return window_values.astype(float)


def compute_valsalva_ratio(
	timestamps: pd.Series,
	rr_intervals_ms: pd.Series,
	phase_ii_window: Tuple[float, float],
	phase_iv_window: Tuple[float, float],
) -> Dict[str, float]:
	"""Compute the Valsalva ratio using windows for phase II (strain) and phase IV (release).

	Args:
		timestamps: Datetime index aligned with RR samples.
		rr_intervals_ms: RR interval series (ms) aligned with timestamps.
		phase_ii_window: Tuple defining the phase II window in seconds from recording start.
		phase_iv_window: Tuple defining the phase IV window in seconds from recording start.

	Returns:
		Dictionary containing phase minima/maxima and the Valsalva ratio.

	Raises:
		ValueError: If inputs are incompatible or windows contain insufficient samples.
	"""
	if rr_intervals_ms.size == 0:
		raise ValueError("RR interval series is empty; cannot compute Valsalva ratio")
	rr_numeric = pd.to_numeric(rr_intervals_ms, errors="coerce")
	valid = rr_numeric.notna()
	if not valid.any():
		raise ValueError("RR interval series contains no valid numeric samples")
	rr_values = rr_numeric.loc[valid].to_numpy(dtype=float)
	time_values = timestamps.loc[valid]
	relative_seconds = _relative_seconds_from_timestamps(time_values)
	phase_ii_values = _extract_window_values(relative_seconds, rr_values, phase_ii_window, "phase II")
	phase_iv_values = _extract_window_values(relative_seconds, rr_values, phase_iv_window, "phase IV")
	phase_ii_min = float(np.min(phase_ii_values))
	phase_iv_max = float(np.max(phase_iv_values))
	if phase_ii_min <= 0.0:
		raise ValueError("Phase II minimum RR must be positive to compute the ratio")
	valsalva_ratio = float(phase_iv_max / phase_ii_min)
	return {
		"valsalva_ratio": valsalva_ratio,
		"phase_ii_min_rr_ms": phase_ii_min,
		"phase_iv_max_rr_ms": phase_iv_max,
		"phase_ii_window": tuple(float(v) for v in phase_ii_window),
		"phase_iv_window": tuple(float(v) for v in phase_iv_window),
	}


def compute_deep_breathing_response(
	timestamps: pd.Series,
	rr_intervals_ms: pd.Series,
	start_time_s: float,
	cycle_length_s: float,
	n_cycles: int,
) -> Dict[str, Any]:
	"""Compute E:I response metrics for a paced deep-breathing protocol.

	Args:
		timestamps: Datetime index aligned with RR samples.
		rr_intervals_ms: RR interval series (ms) aligned with timestamps.
		start_time_s: Time (seconds from recording start) where the breathing protocol begins.
		cycle_length_s: Duration of a single breathing cycle in seconds.
		n_cycles: Number of consecutive cycles to analyse.

	Returns:
		Dictionary with mean E–I difference, ratio, HR difference, and per-cycle details.

	Raises:
		ValueError: If parameters are invalid or cycles lack sufficient samples.
	"""
	if n_cycles <= 0 or n_cycles > 20:
		raise ValueError("n_cycles must be between 1 and 20")
	if cycle_length_s <= 0.0 or not np.isfinite(cycle_length_s):
		raise ValueError("cycle_length_s must be a positive finite number")
	rr_numeric = pd.to_numeric(rr_intervals_ms, errors="coerce")
	valid = rr_numeric.notna()
	if not valid.any():
		raise ValueError("RR interval series contains no valid numeric samples")
	rr_values = rr_numeric.loc[valid].to_numpy(dtype=float)
	time_values = timestamps.loc[valid]
	relative_seconds = _relative_seconds_from_timestamps(time_values)
	if start_time_s < 0.0:
		raise ValueError("start_time_s cannot be negative")
	cycle_stats: List[Dict[str, float]] = []
	for idx in range(n_cycles):
		window_start = start_time_s + (idx * cycle_length_s)
		window_end = window_start + cycle_length_s
		window_values = _extract_window_values(
			relative_seconds,
			rr_values,
			(window_start, window_end),
			f"cycle {idx + 1}",
		)
		exp_rr = float(np.max(window_values))
		insp_rr = float(np.min(window_values))
		if insp_rr <= 0.0:
			raise ValueError("Inspiratory RR must be positive to compute ratios")
		diff = exp_rr - insp_rr
		ratio = float(exp_rr / insp_rr)
		exp_hr = float(60000.0 / insp_rr)  # HR highest during inspiration (shorter RR)
		insp_hr = float(60000.0 / exp_rr)  # HR lowest during expiration (longer RR)
		hr_diff = exp_hr - insp_hr
		cycle_stats.append(
			{
				"cycle_index": float(idx + 1),
				"expiration_rr_ms": exp_rr,
				"inspiration_rr_ms": insp_rr,
				"ei_difference_ms": diff,
				"ei_ratio": ratio,
				"hr_difference_bpm": hr_diff,
			}
		)
	diff_values = np.array([item["ei_difference_ms"] for item in cycle_stats], dtype=float)
	ratio_values = np.array([item["ei_ratio"] for item in cycle_stats], dtype=float)
	hr_differences = np.array([item["hr_difference_bpm"] for item in cycle_stats], dtype=float)
	return {
		"ei_mean_difference_ms": float(np.mean(diff_values)),
		"ei_max_difference_ms": float(np.max(diff_values)),
		"ei_mean_ratio": float(np.mean(ratio_values)),
		"hr_mean_difference_bpm": float(np.mean(hr_differences)),
		"cycles_analyzed": int(n_cycles),
		"cycle_details": tuple(cycle_stats),
	}


def compute_30_15_ratio(
	timestamps: pd.Series,
	rr_intervals_ms: pd.Series,
	stand_time_s: float,
	window_15_s: Tuple[float, float],
	window_30_s: Tuple[float, float],
) -> Dict[str, float]:
	"""Compute the 30:15 ratio for orthostatic testing.

	Args:
		timestamps: Datetime index aligned with RR samples.
		rr_intervals_ms: RR interval series (ms) aligned with timestamps.
		stand_time_s: Time (seconds from recording start) when standing occurs.
		window_15_s: Window (seconds after stand) to search for the shortest RR around beat 15.
		window_30_s: Window (seconds after stand) to search for the longest RR around beat 30.

	Returns:
		Dictionary with component RR values and the 30:15 ratio.

	Raises:
		ValueError: If windows are invalid or lack data.
	"""
	if stand_time_s < 0.0 or not np.isfinite(stand_time_s):
		raise ValueError("stand_time_s must be a finite, non-negative value")
	rr_numeric = pd.to_numeric(rr_intervals_ms, errors="coerce")
	valid = rr_numeric.notna()
	if not valid.any():
		raise ValueError("RR interval series contains no valid numeric samples")
	rr_values = rr_numeric.loc[valid].to_numpy(dtype=float)
	time_values = timestamps.loc[valid]
	relative_seconds = _relative_seconds_from_timestamps(time_values) - float(stand_time_s)
	window_15 = _validate_window(window_15_s, "30:15 (15th-beat) window")
	window_30 = _validate_window(window_30_s, "30:15 (30th-beat) window")
	rr_15_values = _extract_window_values(relative_seconds, rr_values, window_15, "30:15 (15th-beat) window")
	rr_30_values = _extract_window_values(relative_seconds, rr_values, window_30, "30:15 (30th-beat) window")
	shortest_15 = float(np.min(rr_15_values))
	longest_30 = float(np.max(rr_30_values))
	if shortest_15 <= 0.0:
		raise ValueError("Shortest RR in 15th-beat window must be positive to compute ratio")
	ratio = float(longest_30 / shortest_15)
	return {
		"ratio_30_15": ratio,
		"rr_15_min_ms": shortest_15,
		"rr_30_max_ms": longest_30,
		"window_15_s": tuple(float(v) for v in window_15),
		"window_30_s": tuple(float(v) for v in window_30),
	}


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


# ---------------------------------------------------------------------------
# Personalized HRV Interpretation
# ---------------------------------------------------------------------------

def interpret_hrv_personalized(
	hrv_results: Dict[str, Any],
	user_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
	"""
	Interpret HRV results using personalized norms based on user profile.
	
	This function takes the computed HRV metrics and provides personalized
	interpretations based on the user's age, sex, and other profile data.
	
	Args:
		hrv_results: Dictionary of computed HRV metrics from compute_comprehensive_hrv()
		user_context: Optional user profile data from get_active_user_context()
			Expected keys: age_years, sex, hrv_norms, personalized_metrics
	
	Returns:
		Dictionary with interpreted metrics including:
		- status: "normal", "low", "high", "very_low", "very_high"
		- interpretation: Human-readable interpretation
		- percentile_estimate: Estimated percentile for age group
		- reference_range: Normal range for the user's age group
	"""
	interpretations: Dict[str, Any] = {
		"has_personalization": user_context is not None,
		"metrics": {},
	}
	
	# Default age group norms (30-39 years as fallback)
	default_norms = {
		"rmssd_ms": {"mean": 35.0, "sd": 13.0, "p5": 15.0, "p95": 65.0},
		"sdnn_ms": {"mean": 45.0, "sd": 14.0, "p5": 22.0, "p95": 75.0},
		"pnn50_pct": {"mean": 14.0, "sd": 10.0, "p5": 1.5, "p95": 38.0},
		"hf_power_ms2": {"mean": 755.0, "sd": 350.0, "p5": 200.0, "p95": 1600.0},
		"lf_power_ms2": {"mean": 1050.0, "sd": 420.0, "p5": 380.0, "p95": 2000.0},
		"lf_hf_ratio": {"mean": 1.8, "sd": 0.8, "p5": 0.6, "p95": 3.5},
	}
	
	# Get personalized norms if available
	personalized_norms = default_norms.copy()
	age_group = "30-39"
	sex = "other"
	
	if user_context:
		age_group = user_context.get("hrv_norms", {}).get("age_group", age_group)
		sex = user_context.get("sex", sex)
		
		# Override with personalized norms if available
		hrv_norms_data = user_context.get("hrv_norms", {}).get("metrics", {})
		for metric_name, values in hrv_norms_data.items():
			if metric_name in personalized_norms and isinstance(values, dict):
				personalized_norms[metric_name] = {
					"mean": values.get("mean", personalized_norms[metric_name]["mean"]),
					"sd": values.get("sd", personalized_norms[metric_name]["sd"]),
					"p5": values.get("percentile_5", personalized_norms[metric_name]["p5"]),
					"p95": values.get("percentile_95", personalized_norms[metric_name]["p95"]),
				}
		
		interpretations["age_group"] = age_group
		interpretations["sex"] = sex
	
	# Interpret each key metric
	key_metrics = [
		("rmssd_ms", "RMSSD", "ms", "Parasympathetic modulation marker"),
		("sdnn_ms", "SDNN", "ms", "Overall HRV reflecting autonomic regulation"),
		("pnn50_pct", "pNN50", "%", "High frequency vagal activity indicator"),
		("hf_power_ms2", "HF Power", "ms²", "Respiratory sinus arrhythmia"),
		("lf_power_ms2", "LF Power", "ms²", "Baroreflex and mixed autonomic activity"),
		("lf_hf_ratio", "LF/HF Ratio", "", "Sympathovagal balance (interpret with caution)"),
	]
	
	for metric_key, display_name, unit, description in key_metrics:
		value = hrv_results.get(metric_key)
		if value is None or not np.isfinite(value):
			continue
		
		norms = personalized_norms.get(metric_key, default_norms.get(metric_key, {}))
		mean = norms.get("mean", 35.0)
		sd = norms.get("sd", 13.0)
		p5 = norms.get("p5", 15.0)
		p95 = norms.get("p95", 65.0)
		
		# Calculate z-score
		z_score = (value - mean) / sd if sd > 0 else 0
		
		# Estimate percentile (using normal distribution approximation)
		from math import erf, sqrt
		percentile = int(50 * (1 + erf(z_score / sqrt(2))))
		percentile = max(1, min(99, percentile))
		
		# Determine status
		if value < mean - 2 * sd:
			status = "very_low"
			interpretation = f"Significantly below normal for age {age_group}"
		elif value < mean - sd:
			status = "low"
			interpretation = f"Below normal for age {age_group}"
		elif value > mean + 2 * sd:
			status = "very_high"
			interpretation = f"Significantly above normal for age {age_group}"
		elif value > mean + sd:
			status = "high"
			interpretation = f"Above normal for age {age_group}"
		else:
			status = "normal"
			interpretation = f"Within normal range for age {age_group}"
		
		interpretations["metrics"][metric_key] = {
			"display_name": display_name,
			"value": float(value),
			"unit": unit,
			"status": status,
			"interpretation": interpretation,
			"description": description,
			"percentile_estimate": percentile,
			"z_score": round(z_score, 2),
			"reference_mean": mean,
			"reference_sd": sd,
			"reference_range": f"{p5:.1f} - {p95:.1f}",
		}
	
	# Overall autonomic interpretation
	rmssd_status = interpretations["metrics"].get("rmssd_ms", {}).get("status", "normal")
	lf_hf_status = interpretations["metrics"].get("lf_hf_ratio", {}).get("status", "normal")
	
	if rmssd_status in ["very_low", "low"]:
		overall = "Reduced parasympathetic activity"
		recommendation = "Consider recovery strategies, stress management, and sleep optimization"
	elif rmssd_status in ["very_high", "high"]:
		overall = "Elevated parasympathetic activity"
		recommendation = "Good vagal tone, indicative of recovery state or high fitness"
	else:
		overall = "Balanced autonomic function"
		recommendation = "Continue current lifestyle habits"
	
	interpretations["overall_status"] = overall
	interpretations["recommendation"] = recommendation
	interpretations["reference"] = "Nunan et al. PACE 2010; Shaffer & Ginsberg 2017"
	
	return interpretations

