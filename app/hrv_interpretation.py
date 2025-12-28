"""
HRV Metric Interpretation Module

Provides scientifically-grounded interpretations for HRV metrics with clinical
context, physiological explanations, and actionable recommendations.

This module bridges the gap between raw HRV numbers and meaningful insights
for researchers and clinicians.

References:
- Task Force ESC/NASPE (1996). Eur Heart J 17:354-381.
- Shaffer F, Ginsberg JP (2017). Front Public Health 5:258.
- Nunan D et al. (2010). PACE 33:1407-1417.
- Bigger JT et al. (1992). Circulation 85:164-171.

Author: Dr Diego Malpica MD
Version: 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class InterpretationLevel(Enum):
    """Severity/status level for metric interpretation."""
    
    VERY_LOW = "very_low"
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    VERY_HIGH = "very_high"
    OPTIMAL = "optimal"


@dataclass(frozen=True, slots=True)
class MetricInterpretation:
    """Comprehensive interpretation for an HRV metric."""
    
    metric_name: str
    display_name: str
    value: float
    unit: str
    level: InterpretationLevel
    short_description: str
    physiological_meaning: str
    clinical_significance: str
    recommendations: List[str]
    reference_range: str
    reference_source: str
    
    @property
    def level_color(self) -> str:
        """Return color code for the interpretation level."""
        colors = {
            InterpretationLevel.VERY_LOW: "#ff4d4f",
            InterpretationLevel.LOW: "#faad14", 
            InterpretationLevel.NORMAL: "#52c41a",
            InterpretationLevel.HIGH: "#1890ff",
            InterpretationLevel.VERY_HIGH: "#722ed1",
            InterpretationLevel.OPTIMAL: "#13c2c2",
        }
        return colors.get(self.level, "#666666")
    
    @property
    def level_emoji(self) -> str:
        """Return emoji for the interpretation level."""
        emojis = {
            InterpretationLevel.VERY_LOW: "🔴",
            InterpretationLevel.LOW: "🟡",
            InterpretationLevel.NORMAL: "🟢",
            InterpretationLevel.HIGH: "🔵",
            InterpretationLevel.VERY_HIGH: "🟣",
            InterpretationLevel.OPTIMAL: "✨",
        }
        return emojis.get(self.level, "⚪")


# =============================================================================
# Metric Reference Data with Clinical Context
# =============================================================================

METRIC_REFERENCES: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # Time-Domain Metrics
    # -------------------------------------------------------------------------
    "sdnn": {
        "display_name": "SDNN",
        "unit": "ms",
        "full_name": "Standard Deviation of NN Intervals",
        "physiological_meaning": (
            "SDNN reflects the total variability of heart rate over the recording period. "
            "It captures both sympathetic and parasympathetic contributions to HRV and "
            "is strongly influenced by circadian rhythms in 24-hour recordings."
        ),
        "clinical_significance": (
            "Low SDNN (<50 ms in 24h) is associated with increased cardiovascular mortality "
            "and adverse outcomes post-MI. SDNN <100 ms in 24h recordings indicates reduced "
            "ANS function. For 5-min recordings, values below 30 ms suggest compromised "
            "autonomic regulation."
        ),
        "thresholds": {
            "5min": {"very_low": 30, "low": 50, "normal": 100, "high": 150},
            "24h": {"very_low": 50, "low": 100, "normal": 141, "high": 200},
        },
        "reference_source": "Task Force 1996; Nunan et al. 2010",
        "higher_is_better": True,
    },
    "rmssd": {
        "display_name": "RMSSD",
        "unit": "ms",
        "full_name": "Root Mean Square of Successive Differences",
        "physiological_meaning": (
            "RMSSD reflects beat-to-beat (short-term) variability and is the primary "
            "marker of vagal (parasympathetic) modulation of heart rate. It is relatively "
            "free of respiratory influences and remains valid even in ultra-short recordings."
        ),
        "clinical_significance": (
            "Low RMSSD indicates reduced vagal tone, associated with stress, fatigue, "
            "inflammation, and increased cardiovascular risk. Athletes typically show "
            "elevated RMSSD (>50 ms). Values below 20 ms suggest significant vagal "
            "withdrawal and warrant clinical attention."
        ),
        "thresholds": {
            "5min": {"very_low": 20, "low": 42, "normal": 80, "high": 120},
        },
        "reference_source": "Shaffer & Ginsberg 2017; Task Force 1996",
        "higher_is_better": True,
    },
    "ln_rmssd": {
        "display_name": "lnRMSSD",
        "unit": "",
        "full_name": "Natural Log of RMSSD",
        "physiological_meaning": (
            "Natural log transformation of RMSSD normalizes its distribution for statistical "
            "analysis and trend tracking. Commonly used in training load monitoring and "
            "recovery assessment in sports science."
        ),
        "clinical_significance": (
            "lnRMSSD is the preferred metric for daily HRV tracking due to its stability. "
            "A meaningful change is typically ≥0.5 units from baseline. Day-to-day coefficient "
            "of variation (CV) >10% may indicate maladaptation to training."
        ),
        "thresholds": {
            "5min": {"very_low": 2.5, "low": 3.5, "normal": 4.2, "high": 5.0},
        },
        "reference_source": "Plews et al. 2013",
        "higher_is_better": True,
    },
    "pnn50": {
        "display_name": "pNN50",
        "unit": "%",
        "full_name": "Percentage of NN50 Intervals",
        "physiological_meaning": (
            "pNN50 quantifies the percentage of successive NN intervals differing by >50 ms. "
            "Like RMSSD, it reflects vagal modulation but with a threshold-based approach "
            "that may be more intuitive for some applications."
        ),
        "clinical_significance": (
            "Values below 3% indicate significantly reduced parasympathetic activity. "
            "Healthy young adults typically show 10-25%. pNN50 correlates strongly with "
            "HF power and RMSSD (r≈0.9) but may be less sensitive at low HRV levels."
        ),
        "thresholds": {
            "5min": {"very_low": 3, "low": 10, "normal": 30, "high": 50},
        },
        "reference_source": "Task Force 1996; Nunan et al. 2010",
        "higher_is_better": True,
    },
    "mean_hr": {
        "display_name": "Mean HR",
        "unit": "bpm",
        "full_name": "Mean Heart Rate",
        "physiological_meaning": (
            "Mean heart rate during the recording period. Resting HR is primarily "
            "determined by intrinsic sinoatrial node rate minus vagal inhibition, "
            "with sympathetic influence at higher rates."
        ),
        "clinical_significance": (
            "Elevated resting HR (>80 bpm) is associated with increased cardiovascular "
            "mortality. HR recovery after exercise is a strong prognostic marker. "
            "Athletes may have resting HR in the 40-60 bpm range."
        ),
        "thresholds": {
            "rest": {"very_low": 40, "low": 50, "normal": 70, "high": 90, "very_high": 100},
        },
        "reference_source": "Fox et al. 2007",
        "higher_is_better": False,  # Lower resting HR is generally better
    },
    
    # -------------------------------------------------------------------------
    # Frequency-Domain Metrics
    # -------------------------------------------------------------------------
    "hf_power": {
        "display_name": "HF Power",
        "unit": "ms²",
        "full_name": "High-Frequency Power (0.15-0.4 Hz)",
        "physiological_meaning": (
            "HF power reflects respiratory sinus arrhythmia (RSA) and is mediated almost "
            "exclusively by the vagus nerve. The HF band corresponds to typical respiratory "
            "frequencies (9-24 breaths/min)."
        ),
        "clinical_significance": (
            "Reduced HF power indicates vagal withdrawal, seen in stress, disease, and aging. "
            "HF power <150 ms² in 5-min recordings suggests compromised parasympathetic "
            "function. Note: controlled breathing affects HF substantially."
        ),
        "thresholds": {
            "5min": {"very_low": 100, "low": 500, "normal": 1500, "high": 3000},
        },
        "reference_source": "Task Force 1996; Shaffer & Ginsberg 2017",
        "higher_is_better": True,
    },
    "lf_power": {
        "display_name": "LF Power",
        "unit": "ms²",
        "full_name": "Low-Frequency Power (0.04-0.15 Hz)",
        "physiological_meaning": (
            "LF power reflects both sympathetic and parasympathetic influences, with "
            "substantial contribution from the baroreflex. The ~0.1 Hz (10-second) "
            "Mayer wave is a key component. LF is NOT a pure sympathetic marker."
        ),
        "clinical_significance": (
            "The traditional interpretation of LF as 'sympathetic' is contested. LF power "
            "is reduced in conditions with baroreflex impairment. In supine position at rest, "
            "LF has significant vagal contribution."
        ),
        "thresholds": {
            "5min": {"very_low": 200, "low": 800, "normal": 2000, "high": 4000},
        },
        "reference_source": "Task Force 1996; Goldstein et al. 2011",
        "higher_is_better": None,  # Context-dependent
    },
    "lf_hf_ratio": {
        "display_name": "LF/HF Ratio",
        "unit": "",
        "full_name": "Low-Frequency to High-Frequency Ratio",
        "physiological_meaning": (
            "LF/HF ratio was historically interpreted as 'sympathovagal balance'. "
            "However, this interpretation is now considered oversimplified. The ratio "
            "is influenced by many factors including posture, breathing, and age."
        ),
        "clinical_significance": (
            "Use LF/HF ratio cautiously. High values (>4) during rest may indicate "
            "sympathetic predominance or vagal withdrawal. Very low values (<0.5) may "
            "indicate parasympathetic dominance or slow breathing. Interpret in context."
        ),
        "thresholds": {
            "5min": {"very_low": 0.5, "low": 1.0, "normal": 2.0, "high": 4.0},
        },
        "reference_source": "Task Force 1996 (with caveats)",
        "higher_is_better": None,  # Balance is ideal
    },
    "total_power": {
        "display_name": "Total Power",
        "unit": "ms²",
        "full_name": "Total Spectral Power",
        "physiological_meaning": (
            "Total power represents the overall magnitude of HRV across all frequency bands. "
            "It correlates strongly with SDNN and reflects the total variance in the "
            "RR interval time series."
        ),
        "clinical_significance": (
            "Low total power indicates globally reduced HRV, associated with stress, "
            "disease, and mortality risk. For 5-min recordings, values <500 ms² suggest "
            "significantly compromised autonomic function."
        ),
        "thresholds": {
            "5min": {"very_low": 500, "low": 2000, "normal": 5000, "high": 10000},
        },
        "reference_source": "Task Force 1996",
        "higher_is_better": True,
    },
    
    # -------------------------------------------------------------------------
    # Poincaré / Nonlinear Metrics
    # -------------------------------------------------------------------------
    "sd1": {
        "display_name": "SD1",
        "unit": "ms",
        "full_name": "Poincaré SD1 (Short-term Variability)",
        "physiological_meaning": (
            "SD1 is the standard deviation of the Poincaré plot perpendicular to the "
            "line of identity. It equals RMSSD/√2 and reflects beat-to-beat (instantaneous) "
            "variability, primarily vagal in origin."
        ),
        "clinical_significance": (
            "SD1 provides a geometric visualization of RMSSD. Low SD1 indicates reduced "
            "vagal modulation. Useful for identifying arrhythmias and ectopic beats "
            "through visual inspection of the Poincaré plot."
        ),
        "thresholds": {
            "5min": {"very_low": 15, "low": 30, "normal": 60, "high": 100},
        },
        "reference_source": "Brennan et al. 2001",
        "higher_is_better": True,
    },
    "sd2": {
        "display_name": "SD2",
        "unit": "ms",
        "full_name": "Poincaré SD2 (Long-term Variability)",
        "physiological_meaning": (
            "SD2 is the standard deviation along the line of identity. It reflects "
            "both short-term and long-term HRV, combining information about SDNN and RMSSD. "
            "SD2 correlates with baroreflex sensitivity and LF power."
        ),
        "clinical_significance": (
            "SD2 captures global variability including slow oscillations. A high SD2/SD1 "
            "ratio (CSI >3) may indicate sympathetic dominance. SD2 is reduced in "
            "conditions with impaired autonomic regulation."
        ),
        "thresholds": {
            "5min": {"very_low": 30, "low": 70, "normal": 120, "high": 180},
        },
        "reference_source": "Brennan et al. 2001",
        "higher_is_better": True,
    },
    "cvi": {
        "display_name": "CVI",
        "unit": "",
        "full_name": "Cardiac Vagal Index",
        "physiological_meaning": (
            "CVI = log₁₀(SD1 × SD2) provides an integrated measure of vagal modulation. "
            "It combines short-term and long-term variability into a single logarithmic index."
        ),
        "clinical_significance": (
            "CVI decreases with reduced vagal function. Values below 3.0 indicate "
            "significantly impaired parasympathetic modulation. Useful for assessing "
            "overall autonomic health."
        ),
        "thresholds": {
            "5min": {"very_low": 2.5, "low": 3.5, "normal": 4.5, "high": 6.0},
        },
        "reference_source": "Toichi et al. 1997",
        "higher_is_better": True,
    },
    "csi": {
        "display_name": "CSI",
        "unit": "",
        "full_name": "Cardiac Sympathetic Index",
        "physiological_meaning": (
            "CSI = SD2/SD1 reflects the ratio of long-term to short-term variability. "
            "Higher values indicate relatively greater sympathetic influence compared "
            "to vagal modulation."
        ),
        "clinical_significance": (
            "CSI >3 suggests sympathetic predominance; values <1.5 indicate vagal "
            "dominance. During stress or exercise, CSI increases. Elevated resting "
            "CSI may indicate chronic sympathetic activation."
        ),
        "thresholds": {
            "5min": {"very_low": 1.0, "low": 1.5, "normal": 2.5, "high": 4.0, "very_high": 6.0},
        },
        "reference_source": "Toichi et al. 1997",
        "higher_is_better": False,  # Lower CSI at rest is generally better
    },
    "dfa_alpha1": {
        "display_name": "DFA α1",
        "unit": "",
        "full_name": "Detrended Fluctuation Analysis (Short-term)",
        "physiological_meaning": (
            "DFA α1 (4-16 beats) quantifies the fractal scaling behavior of short-term "
            "heart rate fluctuations. Healthy hearts show α1 ≈ 1.0 (1/f noise), reflecting "
            "complex, adaptive dynamics."
        ),
        "clinical_significance": (
            "α1 < 0.75 indicates loss of fractal correlation (more random, 'white noise'), "
            "seen in congestive heart failure. α1 > 1.5 indicates over-correlated dynamics "
            "(too regular), seen in some arrhythmias. α1 ≈ 1.0 indicates healthy complexity."
        ),
        "thresholds": {
            "5min": {"very_low": 0.5, "low": 0.75, "normal": 1.0, "high": 1.3, "very_high": 1.5},
        },
        "reference_source": "Peng et al. 1995; Goldberger et al. 2002",
        "higher_is_better": None,  # Optimal around 1.0
    },
    
    # -------------------------------------------------------------------------
    # Entropy Metrics
    # -------------------------------------------------------------------------
    "sampen": {
        "display_name": "SampEn",
        "unit": "",
        "full_name": "Sample Entropy",
        "physiological_meaning": (
            "Sample entropy quantifies the complexity/unpredictability of the RR time series. "
            "Higher SampEn indicates greater irregularity. Healthy hearts show moderate "
            "complexity; very high or very low values suggest pathology."
        ),
        "clinical_significance": (
            "SampEn is reduced in heart failure and increases with healthy aging. "
            "Very low SampEn (<0.5) may indicate pathological regularity. "
            "Useful for detecting subtle changes in autonomic regulation."
        ),
        "thresholds": {
            "5min": {"very_low": 0.5, "low": 1.0, "normal": 1.5, "high": 2.0, "very_high": 2.5},
        },
        "reference_source": "Richman & Moorman 2000",
        "higher_is_better": None,  # Moderate values optimal
    },
    
    # -------------------------------------------------------------------------
    # Heart Rate Fragmentation Metrics
    # -------------------------------------------------------------------------
    "hrf_pip_pct": {
        "display_name": "PIP",
        "unit": "%",
        "full_name": "Percentage of Inflection Points",
        "physiological_meaning": (
            "PIP measures how often the heart rate changes direction (accelerates vs decelerates). "
            "High fragmentation indicates frequent, small changes rather than smooth trends. "
            "Reflects impaired autonomic control."
        ),
        "clinical_significance": (
            "PIP >65% is associated with increased atrial fibrillation risk. "
            "Heart rate fragmentation increases with age and cardiovascular disease. "
            "Lower values indicate smoother, more coherent autonomic regulation."
        ),
        "thresholds": {
            "5min": {"low": 30, "normal": 50, "high": 65, "very_high": 80},
        },
        "reference_source": "Costa et al. 2017",
        "higher_is_better": False,  # Lower fragmentation is better
    },
    
    # -------------------------------------------------------------------------
    # Geometric Metrics
    # -------------------------------------------------------------------------
    "baevsky_stress_index": {
        "display_name": "Stress Index",
        "unit": "",
        "full_name": "Baevsky Stress Index (SI)",
        "physiological_meaning": (
            "SI = AMo / (2 × Mo × MxDMn) quantifies cardiovascular stress through the "
            "histogram of RR intervals. Higher values indicate reduced variability "
            "and increased sympathetic activation."
        ),
        "clinical_significance": (
            "SI >150 suggests elevated stress; values >300 indicate significant "
            "sympathetic activation. Used extensively in Russian space medicine "
            "for cosmonaut monitoring. Lower values indicate relaxation."
        ),
        "thresholds": {
            "5min": {"low": 50, "normal": 150, "high": 300, "very_high": 500},
        },
        "reference_source": "Baevsky & Berseneva 2008",
        "higher_is_better": False,
    },
    "hrv_triangular_index": {
        "display_name": "HRVI",
        "unit": "",
        "full_name": "HRV Triangular Index",
        "physiological_meaning": (
            "HRVI = N / max(histogram) represents the integral of the NN histogram "
            "divided by its height. It provides a geometric measure of total HRV "
            "that is relatively insensitive to artifacts."
        ),
        "clinical_significance": (
            "HRVI <15 in 24h recordings indicates significantly reduced variability. "
            "This metric is robust to ectopic beats and is recommended for Holter "
            "analysis where artifact rejection may be imperfect."
        ),
        "thresholds": {
            "5min": {"very_low": 5, "low": 10, "normal": 20, "high": 35},
            "24h": {"very_low": 15, "low": 20, "normal": 37, "high": 50},
        },
        "reference_source": "Task Force 1996",
        "higher_is_better": True,
    },
}


# =============================================================================
# Interpretation Functions
# =============================================================================

def get_interpretation_level(
    metric_name: str,
    value: float,
    recording_type: str = "5min",
) -> InterpretationLevel:
    """Determine the interpretation level for a metric value.
    
    Args:
        metric_name: Name of the metric (e.g., 'rmssd', 'sdnn').
        value: The metric value.
        recording_type: '5min' or '24h' for appropriate thresholds.
    
    Returns:
        InterpretationLevel enum value.
    """
    ref = METRIC_REFERENCES.get(metric_name.lower())
    if not ref:
        return InterpretationLevel.NORMAL
    
    thresholds = ref.get("thresholds", {}).get(recording_type, {})
    if not thresholds:
        return InterpretationLevel.NORMAL
    
    higher_is_better = ref.get("higher_is_better", True)
    
    very_low = thresholds.get("very_low", float("-inf"))
    low = thresholds.get("low", float("-inf"))
    normal = thresholds.get("normal", float("inf"))
    high = thresholds.get("high", float("inf"))
    very_high = thresholds.get("very_high", float("inf"))
    
    if higher_is_better:
        if value < very_low:
            return InterpretationLevel.VERY_LOW
        elif value < low:
            return InterpretationLevel.LOW
        elif value <= high:
            return InterpretationLevel.NORMAL
        elif value <= very_high:
            return InterpretationLevel.HIGH
        else:
            return InterpretationLevel.VERY_HIGH
    elif higher_is_better is False:
        # Lower is better (e.g., stress index, HR)
        if value > very_high:
            return InterpretationLevel.VERY_LOW  # Bad
        elif value > high:
            return InterpretationLevel.LOW  # Concerning
        elif value >= low:
            return InterpretationLevel.NORMAL
        elif value >= very_low:
            return InterpretationLevel.HIGH  # Good
        else:
            return InterpretationLevel.OPTIMAL
    else:
        # Neither higher nor lower is better (optimal in middle)
        # e.g., DFA α1 optimal around 1.0
        if value < very_low or value > very_high:
            return InterpretationLevel.VERY_LOW  # Abnormal
        elif value < low or value > high:
            return InterpretationLevel.LOW  # Borderline
        else:
            return InterpretationLevel.NORMAL


def interpret_metric(
    metric_name: str,
    value: float,
    recording_type: str = "5min",
) -> Optional[MetricInterpretation]:
    """Generate a comprehensive interpretation for an HRV metric.
    
    Args:
        metric_name: Name of the metric.
        value: The metric value.
        recording_type: '5min' or '24h'.
    
    Returns:
        MetricInterpretation dataclass or None if metric not found.
    """
    ref = METRIC_REFERENCES.get(metric_name.lower())
    if not ref:
        return None
    
    level = get_interpretation_level(metric_name, value, recording_type)
    thresholds = ref.get("thresholds", {}).get(recording_type, {})
    
    # Build reference range string
    low_t = thresholds.get("low", "?")
    high_t = thresholds.get("high", "?")
    ref_range = f"{low_t} – {high_t} {ref['unit']}"
    
    # Generate recommendations based on level
    recommendations = _generate_recommendations(metric_name, level)
    
    # Generate short description based on level
    short_desc = _generate_short_description(metric_name, level, value, ref)
    
    return MetricInterpretation(
        metric_name=metric_name,
        display_name=ref["display_name"],
        value=value,
        unit=ref["unit"],
        level=level,
        short_description=short_desc,
        physiological_meaning=ref["physiological_meaning"],
        clinical_significance=ref["clinical_significance"],
        recommendations=recommendations,
        reference_range=ref_range,
        reference_source=ref["reference_source"],
    )


def _generate_short_description(
    metric_name: str,
    level: InterpretationLevel,
    value: float,
    ref: Dict[str, Any],
) -> str:
    """Generate a concise description based on the metric level."""
    display_name = ref["display_name"]
    higher_is_better = ref.get("higher_is_better", True)
    
    if level == InterpretationLevel.VERY_LOW:
        if higher_is_better:
            return f"{display_name} significantly below normal range, indicating reduced autonomic function"
        elif higher_is_better is False:
            return f"{display_name} significantly elevated, indicating increased physiological stress"
        else:
            return f"{display_name} outside optimal range, indicating altered cardiac dynamics"
    
    elif level == InterpretationLevel.LOW:
        if higher_is_better:
            return f"{display_name} below normal, suggesting reduced parasympathetic activity"
        elif higher_is_better is False:
            return f"{display_name} elevated, suggesting increased sympathetic activation"
        else:
            return f"{display_name} borderline, monitor for changes"
    
    elif level == InterpretationLevel.NORMAL:
        return f"{display_name} within normal range, indicating healthy autonomic regulation"
    
    elif level == InterpretationLevel.HIGH:
        if higher_is_better:
            return f"{display_name} above average, indicating good vagal tone"
        elif higher_is_better is False:
            return f"{display_name} below average, indicating good regulation"
        else:
            return f"{display_name} in upper range, consider context"
    
    elif level == InterpretationLevel.VERY_HIGH:
        if higher_is_better:
            return f"{display_name} well above average, indicating excellent parasympathetic function"
        elif higher_is_better is False:
            return f"{display_name} unusually low, verify measurement accuracy"
        else:
            return f"{display_name} significantly elevated, investigate underlying cause"
    
    elif level == InterpretationLevel.OPTIMAL:
        return f"{display_name} at optimal level"
    
    return f"{display_name}: {value:.1f} {ref['unit']}"


def _generate_recommendations(
    metric_name: str,
    level: InterpretationLevel,
) -> List[str]:
    """Generate actionable recommendations based on metric and level."""
    recommendations = []
    
    metric_key = metric_name.lower()
    
    if level in (InterpretationLevel.VERY_LOW, InterpretationLevel.LOW):
        # General low HRV recommendations
        if metric_key in ("rmssd", "hf_power", "pnn50", "sd1", "cvi"):
            recommendations.extend([
                "Consider stress management techniques (meditation, deep breathing)",
                "Evaluate sleep quality and duration (aim for 7-9 hours)",
                "Review exercise intensity - may indicate overtraining",
                "Assess hydration and nutrition status",
            ])
        elif metric_key in ("sdnn", "total_power", "hrv_triangular_index"):
            recommendations.extend([
                "Comprehensive autonomic assessment recommended",
                "Review cardiovascular risk factors",
                "Consider lifestyle modifications for overall health",
            ])
        elif metric_key in ("baevsky_stress_index", "mean_hr"):
            recommendations.extend([
                "Implement active recovery protocols",
                "Practice relaxation techniques",
                "Consider reducing caffeine and stimulant intake",
            ])
    
    elif level == InterpretationLevel.NORMAL:
        recommendations.extend([
            "Maintain current lifestyle habits",
            "Continue regular monitoring for trend analysis",
        ])
    
    elif level in (InterpretationLevel.HIGH, InterpretationLevel.VERY_HIGH):
        if metric_key in ("rmssd", "hf_power", "sd1"):
            recommendations.extend([
                "Excellent vagal tone - maintain current practices",
                "Consider progressive training load if athletic goals exist",
            ])
        elif metric_key in ("baevsky_stress_index", "csi", "lf_hf_ratio"):
            recommendations.extend([
                "Unusually low stress markers - verify measurement conditions",
                "Ensure recording was taken at rest in supine position",
            ])
    
    return recommendations


def generate_summary_interpretation(
    metrics: Dict[str, float],
    recording_type: str = "5min",
) -> Dict[str, Any]:
    """Generate an overall summary interpretation from multiple metrics.
    
    Args:
        metrics: Dictionary of metric name -> value.
        recording_type: '5min' or '24h'.
    
    Returns:
        Dictionary with overall assessment, key findings, and recommendations.
    """
    interpretations = []
    
    for name, value in metrics.items():
        interp = interpret_metric(name, value, recording_type)
        if interp:
            interpretations.append(interp)
    
    # Count levels
    level_counts = {}
    for interp in interpretations:
        level_counts[interp.level] = level_counts.get(interp.level, 0) + 1
    
    # Determine overall assessment
    if level_counts.get(InterpretationLevel.VERY_LOW, 0) >= 2:
        overall = "SIGNIFICANTLY REDUCED autonomic function"
        severity = "high"
    elif level_counts.get(InterpretationLevel.VERY_LOW, 0) + level_counts.get(InterpretationLevel.LOW, 0) >= 3:
        overall = "REDUCED autonomic regulation"
        severity = "moderate"
    elif level_counts.get(InterpretationLevel.NORMAL, 0) >= len(interpretations) * 0.5:
        overall = "NORMAL autonomic function"
        severity = "normal"
    elif level_counts.get(InterpretationLevel.HIGH, 0) + level_counts.get(InterpretationLevel.VERY_HIGH, 0) >= 3:
        overall = "ELEVATED HRV - excellent autonomic health"
        severity = "good"
    else:
        overall = "MIXED findings - context-dependent assessment"
        severity = "moderate"
    
    # Extract key findings
    key_findings = []
    for interp in interpretations:
        if interp.level in (InterpretationLevel.VERY_LOW, InterpretationLevel.LOW):
            key_findings.append(f"⚠️ {interp.display_name}: {interp.short_description}")
        elif interp.level in (InterpretationLevel.HIGH, InterpretationLevel.VERY_HIGH):
            key_findings.append(f"✅ {interp.display_name}: {interp.short_description}")
    
    # Aggregate recommendations
    all_recommendations = set()
    for interp in interpretations:
        all_recommendations.update(interp.recommendations)
    
    return {
        "overall_assessment": overall,
        "severity": severity,
        "key_findings": key_findings[:5],  # Top 5
        "recommendations": list(all_recommendations)[:6],  # Top 6
        "interpretations": interpretations,
        "level_counts": level_counts,
    }

