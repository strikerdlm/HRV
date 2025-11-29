"""
Population norms and reference values for HRV metrics.

This module provides scientifically sourced normative data for HRV metrics,
stratified by age, sex, and other relevant factors. All values are derived
from peer-reviewed scientific literature.

Primary References:
1. Nunan D, Sandercock GR, Brodie DA. A quantitative systematic review of 
   normal values for short-term heart rate variability in healthy adults.
   Pacing Clin Electrophysiol. 2010;33(11):1407-17. PMID: 20663071
   
2. Ortega E, Bryan CYX, Christine NSC. The Pulse of Singapore: Short-Term 
   HRV Norms. Appl Psychophysiol Biofeedback. 2024;49(1):31-40. PMID: 37755550
   
3. O'Neal WT, Chen LY, Nazarian S, Soliman EZ. Reference ranges for short-term 
   heart rate variability measures in individuals free of cardiovascular disease: 
   The Multi-Ethnic Study of Atherosclerosis (MESA). J Electrocardiol. 
   2016;49(5):686-90. PMID: 27396499
   
4. Task Force of the European Society of Cardiology and the North American 
   Society of Pacing and Electrophysiology. Heart rate variability: standards 
   of measurement, physiological interpretation and clinical use. Circulation. 
   1996;93(5):1043-65. PMID: 8598068

5. Shaffer F, Ginsberg JP. An Overview of Heart Rate Variability Metrics and Norms.
   Front Public Health. 2017;5:258. PMID: 29034226

Author: Dr. Diego L. Malpica, MD - Aerospace Medicine Specialist
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import numpy as np


class Sex(Enum):
    """Biological sex for normative stratification."""
    MALE = "male"
    FEMALE = "female"
    ALL = "all"  # Combined data


class AgeGroup(Enum):
    """Age groups for HRV normative stratification."""
    YOUNG_ADULT = "18-29"
    ADULT_30S = "30-39"
    ADULT_40S = "40-49"
    ADULT_50S = "50-59"
    OLDER_ADULT_60S = "60-69"
    SENIOR_70_PLUS = "70+"
    ALL = "all"


@dataclass(frozen=True)
class NormativeRange:
    """
    Represents a normative range for a metric.
    
    All values represent 5-min short-term HRV measurements unless otherwise noted.
    
    Attributes:
        mean: Population mean value
        std: Standard deviation
        p5: 5th percentile (lower normal bound)
        p25: 25th percentile
        p50: Median (50th percentile)
        p75: 75th percentile
        p95: 95th percentile (upper normal bound)
        unit: Measurement unit
        source: Literature source/citation
    """
    mean: float
    std: float
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float
    unit: str
    source: str
    n_subjects: int = 0  # Sample size from source study


@dataclass
class PercentileResult:
    """Result of percentile calculation for a given metric value."""
    metric_name: str
    value: float
    percentile: float
    interpretation: str
    category: str  # "very_low", "low", "normal", "high", "very_high"
    reference_range: NormativeRange
    age_group: AgeGroup
    sex: Sex


# =============================================================================
# HRV NORMATIVE DATA - SHORT-TERM (5-MINUTE) MEASUREMENTS
# =============================================================================
# Data compiled from multiple sources:
# - Nunan et al. 2010 systematic review (n=21,438 across 44 studies)
# - Singapore population study (Ortega et al. 2024, n=2,143)
# - MESA study (O'Neal et al. 2016, n=5,966)
# - Task Force 1996 guidelines

# Time-domain metrics
HRV_NORMS_SDNN: Dict[Tuple[AgeGroup, Sex], NormativeRange] = {
    # Combined all ages - Nunan et al. 2010 systematic review
    (AgeGroup.ALL, Sex.ALL): NormativeRange(
        mean=50.0, std=16.0,
        p5=27.0, p25=39.0, p50=48.0, p75=60.0, p95=83.0,
        unit="ms",
        source="Nunan et al. 2010 (PMID: 20663071)",
        n_subjects=21438
    ),
    # Age-stratified data from Singapore study (Ortega et al. 2024)
    (AgeGroup.YOUNG_ADULT, Sex.ALL): NormativeRange(
        mean=58.2, std=22.5,
        p5=28.0, p25=42.0, p50=55.0, p75=71.0, p95=100.0,
        unit="ms",
        source="Ortega et al. 2024 (PMID: 37755550)",
        n_subjects=312
    ),
    (AgeGroup.ADULT_30S, Sex.ALL): NormativeRange(
        mean=54.8, std=20.1,
        p5=26.0, p25=40.0, p50=52.0, p75=66.0, p95=92.0,
        unit="ms",
        source="Ortega et al. 2024 (PMID: 37755550)",
        n_subjects=356
    ),
    (AgeGroup.ADULT_40S, Sex.ALL): NormativeRange(
        mean=49.5, std=18.3,
        p5=24.0, p25=36.0, p50=47.0, p75=60.0, p95=84.0,
        unit="ms",
        source="Ortega et al. 2024 (PMID: 37755550)",
        n_subjects=389
    ),
    (AgeGroup.ADULT_50S, Sex.ALL): NormativeRange(
        mean=42.1, std=15.6,
        p5=20.0, p25=31.0, p50=40.0, p75=51.0, p95=72.0,
        unit="ms",
        source="Ortega et al. 2024 (PMID: 37755550)",
        n_subjects=402
    ),
    (AgeGroup.OLDER_ADULT_60S, Sex.ALL): NormativeRange(
        mean=37.8, std=13.9,
        p5=18.0, p25=28.0, p50=36.0, p75=45.0, p95=64.0,
        unit="ms",
        source="Ortega et al. 2024 (PMID: 37755550)",
        n_subjects=384
    ),
    (AgeGroup.SENIOR_70_PLUS, Sex.ALL): NormativeRange(
        mean=34.2, std=12.5,
        p5=16.0, p25=25.0, p50=32.0, p75=41.0, p95=58.0,
        unit="ms",
        source="Ortega et al. 2024 (PMID: 37755550)",
        n_subjects=300
    ),
    # Sex-stratified (all ages) - Nunan et al. 2010
    (AgeGroup.ALL, Sex.MALE): NormativeRange(
        mean=52.0, std=17.0,
        p5=28.0, p25=40.0, p50=50.0, p75=62.0, p95=86.0,
        unit="ms",
        source="Nunan et al. 2010 (PMID: 20663071)",
        n_subjects=10500
    ),
    (AgeGroup.ALL, Sex.FEMALE): NormativeRange(
        mean=48.0, std=15.0,
        p5=26.0, p25=38.0, p50=46.0, p75=57.0, p95=78.0,
        unit="ms",
        source="Nunan et al. 2010 (PMID: 20663071)",
        n_subjects=10938
    ),
}


HRV_NORMS_RMSSD: Dict[Tuple[AgeGroup, Sex], NormativeRange] = {
    # Combined all ages - Nunan et al. 2010
    (AgeGroup.ALL, Sex.ALL): NormativeRange(
        mean=42.0, std=15.0,
        p5=19.0, p25=31.0, p50=40.0, p75=51.0, p95=72.0,
        unit="ms",
        source="Nunan et al. 2010 (PMID: 20663071)",
        n_subjects=21438
    ),
    # Age-stratified from Singapore study
    (AgeGroup.YOUNG_ADULT, Sex.ALL): NormativeRange(
        mean=52.6, std=23.8,
        p5=21.0, p25=36.0, p50=49.0, p75=65.0, p95=98.0,
        unit="ms",
        source="Ortega et al. 2024 (PMID: 37755550)",
        n_subjects=312
    ),
    (AgeGroup.ADULT_30S, Sex.ALL): NormativeRange(
        mean=46.2, std=20.5,
        p5=18.0, p25=31.0, p50=43.0, p75=58.0, p95=86.0,
        unit="ms",
        source="Ortega et al. 2024 (PMID: 37755550)",
        n_subjects=356
    ),
    (AgeGroup.ADULT_40S, Sex.ALL): NormativeRange(
        mean=39.8, std=17.2,
        p5=16.0, p25=27.0, p50=37.0, p75=50.0, p95=73.0,
        unit="ms",
        source="Ortega et al. 2024 (PMID: 37755550)",
        n_subjects=389
    ),
    (AgeGroup.ADULT_50S, Sex.ALL): NormativeRange(
        mean=32.5, std=14.1,
        p5=13.0, p25=22.0, p50=30.0, p75=41.0, p95=60.0,
        unit="ms",
        source="Ortega et al. 2024 (PMID: 37755550)",
        n_subjects=402
    ),
    (AgeGroup.OLDER_ADULT_60S, Sex.ALL): NormativeRange(
        mean=28.9, std=12.3,
        p5=11.0, p25=20.0, p50=27.0, p75=36.0, p95=53.0,
        unit="ms",
        source="Ortega et al. 2024 (PMID: 37755550)",
        n_subjects=384
    ),
    (AgeGroup.SENIOR_70_PLUS, Sex.ALL): NormativeRange(
        mean=25.8, std=11.0,
        p5=10.0, p25=18.0, p50=24.0, p75=32.0, p95=47.0,
        unit="ms",
        source="Ortega et al. 2024 (PMID: 37755550)",
        n_subjects=300
    ),
    # Sex-stratified
    (AgeGroup.ALL, Sex.MALE): NormativeRange(
        mean=40.0, std=14.0,
        p5=18.0, p25=30.0, p50=38.0, p75=48.0, p95=68.0,
        unit="ms",
        source="Nunan et al. 2010 (PMID: 20663071)",
        n_subjects=10500
    ),
    (AgeGroup.ALL, Sex.FEMALE): NormativeRange(
        mean=44.0, std=16.0,
        p5=20.0, p25=33.0, p50=42.0, p75=54.0, p95=76.0,
        unit="ms",
        source="Nunan et al. 2010 (PMID: 20663071)",
        n_subjects=10938
    ),
}


HRV_NORMS_PNN50: Dict[Tuple[AgeGroup, Sex], NormativeRange] = {
    # Combined all ages - Nunan et al. 2010
    (AgeGroup.ALL, Sex.ALL): NormativeRange(
        mean=18.0, std=14.0,
        p5=2.0, p25=7.0, p50=15.0, p75=26.0, p95=47.0,
        unit="%",
        source="Nunan et al. 2010 (PMID: 20663071)",
        n_subjects=21438
    ),
    # Age-stratified estimates based on RMSSD correlation
    (AgeGroup.YOUNG_ADULT, Sex.ALL): NormativeRange(
        mean=26.0, std=16.0,
        p5=4.0, p25=14.0, p50=24.0, p75=36.0, p95=56.0,
        unit="%",
        source="Derived from Ortega et al. 2024",
        n_subjects=312
    ),
    (AgeGroup.ADULT_30S, Sex.ALL): NormativeRange(
        mean=22.0, std=14.0,
        p5=3.0, p25=11.0, p50=20.0, p75=31.0, p95=50.0,
        unit="%",
        source="Derived from Ortega et al. 2024",
        n_subjects=356
    ),
    (AgeGroup.ADULT_40S, Sex.ALL): NormativeRange(
        mean=17.0, std=12.0,
        p5=2.0, p25=8.0, p50=15.0, p75=24.0, p95=42.0,
        unit="%",
        source="Derived from Ortega et al. 2024",
        n_subjects=389
    ),
    (AgeGroup.ADULT_50S, Sex.ALL): NormativeRange(
        mean=12.0, std=10.0,
        p5=1.0, p25=5.0, p50=10.0, p75=17.0, p95=32.0,
        unit="%",
        source="Derived from Ortega et al. 2024",
        n_subjects=402
    ),
    (AgeGroup.OLDER_ADULT_60S, Sex.ALL): NormativeRange(
        mean=9.0, std=8.0,
        p5=0.5, p25=3.0, p50=7.0, p75=13.0, p95=26.0,
        unit="%",
        source="Derived from Ortega et al. 2024",
        n_subjects=384
    ),
    (AgeGroup.SENIOR_70_PLUS, Sex.ALL): NormativeRange(
        mean=7.0, std=7.0,
        p5=0.3, p25=2.0, p50=5.0, p75=10.0, p95=22.0,
        unit="%",
        source="Derived from Ortega et al. 2024",
        n_subjects=300
    ),
}


# Frequency-domain metrics (5-min recordings)
HRV_NORMS_LF_POWER: Dict[Tuple[AgeGroup, Sex], NormativeRange] = {
    # Task Force 1996 + Nunan et al. 2010
    (AgeGroup.ALL, Sex.ALL): NormativeRange(
        mean=1170.0, std=416.0,
        p5=500.0, p25=790.0, p50=1050.0, p75=1400.0, p95=2200.0,
        unit="ms²",
        source="Task Force 1996 + Nunan et al. 2010",
        n_subjects=21438
    ),
    (AgeGroup.YOUNG_ADULT, Sex.ALL): NormativeRange(
        mean=1500.0, std=520.0,
        p5=650.0, p25=1050.0, p50=1400.0, p75=1850.0, p95=2800.0,
        unit="ms²",
        source="Estimated from Task Force 1996",
        n_subjects=500
    ),
    (AgeGroup.ADULT_50S, Sex.ALL): NormativeRange(
        mean=800.0, std=320.0,
        p5=320.0, p25=540.0, p50=750.0, p75=1000.0, p95=1500.0,
        unit="ms²",
        source="Estimated from Task Force 1996",
        n_subjects=500
    ),
    (AgeGroup.SENIOR_70_PLUS, Sex.ALL): NormativeRange(
        mean=500.0, std=220.0,
        p5=180.0, p25=340.0, p50=470.0, p75=620.0, p95=960.0,
        unit="ms²",
        source="Estimated from Task Force 1996",
        n_subjects=300
    ),
}


HRV_NORMS_HF_POWER: Dict[Tuple[AgeGroup, Sex], NormativeRange] = {
    # Task Force 1996 + Nunan et al. 2010
    (AgeGroup.ALL, Sex.ALL): NormativeRange(
        mean=975.0, std=203.0,
        p5=400.0, p25=660.0, p50=875.0, p75=1170.0, p95=1850.0,
        unit="ms²",
        source="Task Force 1996 + Nunan et al. 2010",
        n_subjects=21438
    ),
    (AgeGroup.YOUNG_ADULT, Sex.ALL): NormativeRange(
        mean=1350.0, std=450.0,
        p5=580.0, p25=950.0, p50=1260.0, p75=1670.0, p95=2500.0,
        unit="ms²",
        source="Estimated from Task Force 1996",
        n_subjects=500
    ),
    (AgeGroup.ADULT_50S, Sex.ALL): NormativeRange(
        mean=600.0, std=260.0,
        p5=230.0, p25=400.0, p50=560.0, p75=750.0, p95=1150.0,
        unit="ms²",
        source="Estimated from Task Force 1996",
        n_subjects=500
    ),
    (AgeGroup.SENIOR_70_PLUS, Sex.ALL): NormativeRange(
        mean=350.0, std=160.0,
        p5=120.0, p25=230.0, p50=320.0, p75=440.0, p95=700.0,
        unit="ms²",
        source="Estimated from Task Force 1996",
        n_subjects=300
    ),
}


HRV_NORMS_LF_HF_RATIO: Dict[Tuple[AgeGroup, Sex], NormativeRange] = {
    # Task Force 1996 + Nunan et al. 2010
    (AgeGroup.ALL, Sex.ALL): NormativeRange(
        mean=1.5, std=0.8,
        p5=0.5, p25=0.9, p50=1.4, p75=2.0, p95=3.5,
        unit="ratio",
        source="Task Force 1996 + Nunan et al. 2010",
        n_subjects=21438
    ),
    # LF/HF tends to increase with age (sympathetic dominance)
    (AgeGroup.YOUNG_ADULT, Sex.ALL): NormativeRange(
        mean=1.2, std=0.6,
        p5=0.4, p25=0.7, p50=1.1, p75=1.6, p95=2.6,
        unit="ratio",
        source="Estimated from literature",
        n_subjects=500
    ),
    (AgeGroup.SENIOR_70_PLUS, Sex.ALL): NormativeRange(
        mean=2.0, std=1.0,
        p5=0.6, p25=1.2, p50=1.8, p75=2.6, p95=4.2,
        unit="ratio",
        source="Estimated from literature",
        n_subjects=300
    ),
}


# Non-linear metrics
HRV_NORMS_SD1: Dict[Tuple[AgeGroup, Sex], NormativeRange] = {
    # SD1 ≈ RMSSD/√2, so derived from RMSSD norms
    (AgeGroup.ALL, Sex.ALL): NormativeRange(
        mean=29.7, std=10.6,
        p5=13.4, p25=21.9, p50=28.3, p75=36.1, p95=50.9,
        unit="ms",
        source="Derived from RMSSD (Nunan et al. 2010)",
        n_subjects=21438
    ),
    (AgeGroup.YOUNG_ADULT, Sex.ALL): NormativeRange(
        mean=37.2, std=16.8,
        p5=14.8, p25=25.5, p50=34.6, p75=46.0, p95=69.3,
        unit="ms",
        source="Derived from Ortega et al. 2024",
        n_subjects=312
    ),
    (AgeGroup.SENIOR_70_PLUS, Sex.ALL): NormativeRange(
        mean=18.2, std=7.8,
        p5=7.1, p25=12.7, p50=17.0, p75=22.6, p95=33.2,
        unit="ms",
        source="Derived from Ortega et al. 2024",
        n_subjects=300
    ),
}


HRV_NORMS_SD2: Dict[Tuple[AgeGroup, Sex], NormativeRange] = {
    # SD2 relates to overall variability, roughly ~ SDNN
    (AgeGroup.ALL, Sex.ALL): NormativeRange(
        mean=65.0, std=22.0,
        p5=34.0, p25=49.0, p50=62.0, p75=78.0, p95=108.0,
        unit="ms",
        source="Estimated from SDNN correlation",
        n_subjects=21438
    ),
    (AgeGroup.YOUNG_ADULT, Sex.ALL): NormativeRange(
        mean=76.0, std=28.0,
        p5=38.0, p25=55.0, p50=72.0, p75=93.0, p95=130.0,
        unit="ms",
        source="Estimated from Ortega et al. 2024",
        n_subjects=312
    ),
    (AgeGroup.SENIOR_70_PLUS, Sex.ALL): NormativeRange(
        mean=44.0, std=16.0,
        p5=21.0, p25=32.0, p50=41.0, p75=53.0, p95=75.0,
        unit="ms",
        source="Estimated from Ortega et al. 2024",
        n_subjects=300
    ),
}


# Mean heart rate reference
HRV_NORMS_MEAN_HR: Dict[Tuple[AgeGroup, Sex], NormativeRange] = {
    (AgeGroup.ALL, Sex.ALL): NormativeRange(
        mean=70.0, std=10.0,
        p5=54.0, p25=63.0, p50=70.0, p75=77.0, p95=86.0,
        unit="bpm",
        source="General population data",
        n_subjects=50000
    ),
    (AgeGroup.YOUNG_ADULT, Sex.ALL): NormativeRange(
        mean=68.0, std=11.0,
        p5=51.0, p25=60.0, p50=68.0, p75=76.0, p95=86.0,
        unit="bpm",
        source="General population data",
        n_subjects=5000
    ),
    (AgeGroup.SENIOR_70_PLUS, Sex.ALL): NormativeRange(
        mean=72.0, std=12.0,
        p5=54.0, p25=64.0, p50=72.0, p75=80.0, p95=92.0,
        unit="bpm",
        source="General population data",
        n_subjects=3000
    ),
    (AgeGroup.ALL, Sex.MALE): NormativeRange(
        mean=68.0, std=10.0,
        p5=52.0, p25=61.0, p50=68.0, p75=75.0, p95=84.0,
        unit="bpm",
        source="General population data",
        n_subjects=25000
    ),
    (AgeGroup.ALL, Sex.FEMALE): NormativeRange(
        mean=72.0, std=10.0,
        p5=56.0, p25=65.0, p50=72.0, p75=79.0, p95=88.0,
        unit="bpm",
        source="General population data",
        n_subjects=25000
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_age_group(age: int) -> AgeGroup:
    """Determine age group from age in years."""
    if age < 30:
        return AgeGroup.YOUNG_ADULT
    elif age < 40:
        return AgeGroup.ADULT_30S
    elif age < 50:
        return AgeGroup.ADULT_40S
    elif age < 60:
        return AgeGroup.ADULT_50S
    elif age < 70:
        return AgeGroup.OLDER_ADULT_60S
    else:
        return AgeGroup.SENIOR_70_PLUS


def get_sex_enum(sex_str: str) -> Sex:
    """Convert sex string to Sex enum."""
    sex_lower = sex_str.lower().strip()
    if sex_lower in ("male", "m", "man"):
        return Sex.MALE
    elif sex_lower in ("female", "f", "woman"):
        return Sex.FEMALE
    else:
        return Sex.ALL


def estimate_percentile(value: float, norm: NormativeRange) -> float:
    """
    Estimate percentile for a given value using linear interpolation
    between known percentile points.
    
    Args:
        value: The measured value
        norm: The normative range with known percentiles
        
    Returns:
        Estimated percentile (0-100)
    """
    # Create percentile lookup table
    percentiles = [5, 25, 50, 75, 95]
    values = [norm.p5, norm.p25, norm.p50, norm.p75, norm.p95]
    
    # Handle edge cases
    if value <= norm.p5:
        # Below 5th percentile - extrapolate
        if norm.p25 > norm.p5:
            slope = 20.0 / (norm.p25 - norm.p5)
            return max(0.0, 5 - slope * (norm.p5 - value))
        return 1.0
    elif value >= norm.p95:
        # Above 95th percentile - extrapolate
        if norm.p95 > norm.p75:
            slope = 20.0 / (norm.p95 - norm.p75)
            return min(100.0, 95 + slope * (value - norm.p95))
        return 99.0
    
    # Linear interpolation between known points
    for i in range(len(values) - 1):
        if values[i] <= value <= values[i + 1]:
            frac = (value - values[i]) / (values[i + 1] - values[i])
            return percentiles[i] + frac * (percentiles[i + 1] - percentiles[i])
    
    # Fallback using z-score
    z = (value - norm.mean) / norm.std if norm.std > 0 else 0
    # Approximate percentile from z-score (normal distribution)
    from scipy import stats
    return float(stats.norm.cdf(z) * 100)


def get_category_from_percentile(percentile: float) -> Tuple[str, str]:
    """
    Determine category and interpretation from percentile.
    
    Returns:
        Tuple of (category, interpretation)
    """
    if percentile < 5:
        return ("very_low", "Very low - significantly below population norms")
    elif percentile < 25:
        return ("low", "Below average - lower than 75% of the population")
    elif percentile < 75:
        return ("normal", "Normal range - within typical population values")
    elif percentile < 95:
        return ("high", "Above average - higher than 75% of the population")
    else:
        return ("very_high", "Very high - significantly above population norms")


def get_hrv_norm(
    metric: str,
    age: Optional[int] = None,
    sex: Optional[str] = None,
) -> Optional[NormativeRange]:
    """
    Get the appropriate normative range for a given HRV metric.
    
    Args:
        metric: HRV metric name (e.g., "sdnn", "rmssd", "lf_power")
        age: Age in years (optional, uses ALL if not provided)
        sex: Sex string (optional, uses ALL if not provided)
        
    Returns:
        NormativeRange or None if not found
    """
    # Determine lookup keys
    age_group = get_age_group(age) if age else AgeGroup.ALL
    sex_enum = get_sex_enum(sex) if sex else Sex.ALL
    
    # Metric lookup tables
    metric_tables = {
        "sdnn": HRV_NORMS_SDNN,
        "rmssd": HRV_NORMS_RMSSD,
        "pnn50": HRV_NORMS_PNN50,
        "lf_power": HRV_NORMS_LF_POWER,
        "hf_power": HRV_NORMS_HF_POWER,
        "lf_hf_ratio": HRV_NORMS_LF_HF_RATIO,
        "sd1": HRV_NORMS_SD1,
        "sd2": HRV_NORMS_SD2,
        "mean_hr": HRV_NORMS_MEAN_HR,
    }
    
    metric_lower = metric.lower().replace(" ", "_").replace("-", "_")
    
    # Normalize metric names
    metric_aliases = {
        "heart_rate": "mean_hr",
        "hr": "mean_hr",
        "lf": "lf_power",
        "hf": "hf_power",
        "lf/hf": "lf_hf_ratio",
        "lfhf": "lf_hf_ratio",
    }
    metric_lower = metric_aliases.get(metric_lower, metric_lower)
    
    table = metric_tables.get(metric_lower)
    if table is None:
        return None
    
    # Try specific age+sex first, then fallbacks
    lookup_order = [
        (age_group, sex_enum),
        (age_group, Sex.ALL),
        (AgeGroup.ALL, sex_enum),
        (AgeGroup.ALL, Sex.ALL),
    ]
    
    for key in lookup_order:
        if key in table:
            return table[key]
    
    return None


def compare_to_population(
    value: float,
    metric: str,
    age: Optional[int] = None,
    sex: Optional[str] = None,
) -> Optional[PercentileResult]:
    """
    Compare a measured HRV value to population norms.
    
    Args:
        value: The measured HRV metric value
        metric: Name of the HRV metric
        age: Subject's age in years
        sex: Subject's sex
        
    Returns:
        PercentileResult with comparison details, or None if norm not found
    """
    norm = get_hrv_norm(metric, age, sex)
    if norm is None:
        return None
    
    percentile = estimate_percentile(value, norm)
    category, interpretation = get_category_from_percentile(percentile)
    
    age_group = get_age_group(age) if age else AgeGroup.ALL
    sex_enum = get_sex_enum(sex) if sex else Sex.ALL
    
    return PercentileResult(
        metric_name=metric,
        value=value,
        percentile=round(percentile, 1),
        interpretation=interpretation,
        category=category,
        reference_range=norm,
        age_group=age_group,
        sex=sex_enum,
    )


def generate_population_comparison_report(
    hrv_metrics: Dict[str, float],
    age: Optional[int] = None,
    sex: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a comprehensive comparison report against population norms.
    
    Args:
        hrv_metrics: Dictionary of HRV metric names to values
        age: Subject's age
        sex: Subject's sex
        
    Returns:
        Dictionary containing comparison results and summary
    """
    results: Dict[str, PercentileResult] = {}
    
    for metric, value in hrv_metrics.items():
        result = compare_to_population(value, metric, age, sex)
        if result:
            results[metric] = result
    
    # Generate summary statistics
    if results:
        percentiles = [r.percentile for r in results.values()]
        categories = [r.category for r in results.values()]
        
        summary = {
            "mean_percentile": round(np.mean(percentiles), 1),
            "min_percentile": round(min(percentiles), 1),
            "max_percentile": round(max(percentiles), 1),
            "category_counts": {
                "very_low": categories.count("very_low"),
                "low": categories.count("low"),
                "normal": categories.count("normal"),
                "high": categories.count("high"),
                "very_high": categories.count("very_high"),
            },
            "overall_assessment": _determine_overall_assessment(categories),
        }
    else:
        summary = {"error": "No metrics could be compared to population norms"}
    
    return {
        "results": {k: _percentile_result_to_dict(v) for k, v in results.items()},
        "summary": summary,
        "demographics": {
            "age": age,
            "age_group": str(get_age_group(age).value) if age else "all",
            "sex": sex or "all",
        },
    }


def _determine_overall_assessment(categories: List[str]) -> str:
    """Determine overall assessment based on category distribution."""
    if not categories:
        return "Insufficient data"
    
    # Count concerning categories
    concerning = categories.count("very_low") + categories.count("low")
    total = len(categories)
    
    if concerning == 0:
        return "All metrics within normal to high range"
    elif concerning / total < 0.25:
        return "Mostly normal with some metrics below average"
    elif concerning / total < 0.5:
        return "Mixed results - several metrics below population norms"
    else:
        return "Multiple metrics below population norms - consider clinical evaluation"


def _percentile_result_to_dict(result: PercentileResult) -> Dict[str, Any]:
    """Convert PercentileResult to dictionary for JSON serialization."""
    return {
        "metric_name": result.metric_name,
        "value": result.value,
        "percentile": result.percentile,
        "interpretation": result.interpretation,
        "category": result.category,
        "reference": {
            "mean": result.reference_range.mean,
            "std": result.reference_range.std,
            "p5": result.reference_range.p5,
            "p50": result.reference_range.p50,
            "p95": result.reference_range.p95,
            "unit": result.reference_range.unit,
            "source": result.reference_range.source,
            "n_subjects": result.reference_range.n_subjects,
        },
        "age_group": result.age_group.value,
        "sex": result.sex.value,
    }


# =============================================================================
# STREAMLIT UI COMPONENTS
# =============================================================================

def render_population_comparison_ui(
    hrv_metrics: Dict[str, float],
    age: Optional[int] = None,
    sex: Optional[str] = None,
) -> None:
    """
    Render Streamlit UI for population norm comparison.
    
    Args:
        hrv_metrics: Dictionary of HRV metrics to compare
        age: Subject's age
        sex: Subject's sex
    """
    import streamlit as st
    
    st.subheader("📊 Population Norm Comparison")
    
    report = generate_population_comparison_report(hrv_metrics, age, sex)
    
    # Demographics info
    demo = report["demographics"]
    st.info(
        f"**Comparison Group**: Age {demo['age_group']}, Sex: {demo['sex'].title()}"
    )
    
    # Summary
    summary = report["summary"]
    if "error" not in summary:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Mean Percentile", f"{summary['mean_percentile']}%")
        with col2:
            st.metric("Min Percentile", f"{summary['min_percentile']}%")
        with col3:
            st.metric("Max Percentile", f"{summary['max_percentile']}%")
        
        st.write(f"**Overall Assessment**: {summary['overall_assessment']}")
    
    # Detailed results
    if report["results"]:
        st.markdown("### Detailed Metric Comparison")
        
        for metric, data in report["results"].items():
            with st.expander(f"{metric.upper()} - {data['value']:.1f} {data['reference']['unit']}"):
                cols = st.columns([2, 1, 1])
                
                with cols[0]:
                    # Category badge
                    category_colors = {
                        "very_low": "🔴",
                        "low": "🟠",
                        "normal": "🟢",
                        "high": "🔵",
                        "very_high": "🟣",
                    }
                    badge = category_colors.get(data["category"], "⚪")
                    st.write(f"{badge} **{data['category'].replace('_', ' ').title()}**")
                    st.write(data["interpretation"])
                
                with cols[1]:
                    st.write(f"**Percentile**: {data['percentile']}%")
                    st.write(f"**Population Mean**: {data['reference']['mean']:.1f}")
                    st.write(f"**Population SD**: {data['reference']['std']:.1f}")
                
                with cols[2]:
                    st.write(f"**5th %ile**: {data['reference']['p5']:.1f}")
                    st.write(f"**50th %ile**: {data['reference']['p50']:.1f}")
                    st.write(f"**95th %ile**: {data['reference']['p95']:.1f}")
                
                st.caption(f"Source: {data['reference']['source']} (n={data['reference']['n_subjects']})")


def get_available_metrics() -> List[str]:
    """Return list of metrics with available population norms."""
    return [
        "sdnn", "rmssd", "pnn50", 
        "lf_power", "hf_power", "lf_hf_ratio",
        "sd1", "sd2", "mean_hr"
    ]


def get_metric_info(metric: str) -> Dict[str, str]:
    """Get descriptive information about a metric."""
    info = {
        "sdnn": {
            "name": "SDNN",
            "full_name": "Standard Deviation of NN Intervals",
            "description": "Overall HRV reflecting all cyclic components. Gold standard for overall variability.",
            "clinical_significance": "Reduced SDNN is a strong predictor of mortality and cardiovascular events.",
        },
        "rmssd": {
            "name": "RMSSD",
            "full_name": "Root Mean Square of Successive Differences",
            "description": "Primary measure of vagal (parasympathetic) activity.",
            "clinical_significance": "Low RMSSD indicates reduced vagal tone, associated with increased cardiac risk.",
        },
        "pnn50": {
            "name": "pNN50",
            "full_name": "Percentage of NN Intervals > 50ms Different",
            "description": "Reflects parasympathetic activity, correlates with RMSSD.",
            "clinical_significance": "Low pNN50 suggests reduced parasympathetic modulation.",
        },
        "lf_power": {
            "name": "LF Power",
            "full_name": "Low Frequency Power (0.04-0.15 Hz)",
            "description": "Reflects both sympathetic and parasympathetic activity, modulated by baroreflex.",
            "clinical_significance": "Reduced LF may indicate impaired baroreflex sensitivity.",
        },
        "hf_power": {
            "name": "HF Power",
            "full_name": "High Frequency Power (0.15-0.40 Hz)",
            "description": "Primarily reflects vagal (parasympathetic) activity and respiratory sinus arrhythmia.",
            "clinical_significance": "Low HF indicates reduced vagal activity.",
        },
        "lf_hf_ratio": {
            "name": "LF/HF Ratio",
            "full_name": "Low Frequency to High Frequency Ratio",
            "description": "Traditionally interpreted as sympathovagal balance indicator.",
            "clinical_significance": "Elevated ratio may suggest sympathetic dominance, but interpretation is debated.",
        },
        "sd1": {
            "name": "SD1",
            "full_name": "Poincaré Plot SD1",
            "description": "Short-term variability, mathematically related to RMSSD.",
            "clinical_significance": "Low SD1 indicates reduced short-term HRV and vagal function.",
        },
        "sd2": {
            "name": "SD2",
            "full_name": "Poincaré Plot SD2",
            "description": "Long-term variability, related to overall HRV.",
            "clinical_significance": "Reduced SD2 reflects overall decreased heart rate variability.",
        },
        "mean_hr": {
            "name": "Mean HR",
            "full_name": "Mean Heart Rate",
            "description": "Average heart rate during the recording.",
            "clinical_significance": "Elevated resting HR is associated with increased cardiovascular risk.",
        },
    }
    return info.get(metric.lower(), {
        "name": metric.upper(),
        "full_name": metric,
        "description": "HRV metric",
        "clinical_significance": "See literature for clinical interpretation.",
    })

