# Author: Dr Diego Malpica MD
"""Physiological SMS Risk Assessment Module.

Provides Safety Management System (SMS)-style risk matrices for EVA and
military flight operations, integrating baseline blood pressure and basal
body temperature as bounded readiness modifiers.

Design goals (per project rules):
- Pure functions, no Streamlit dependencies.
- Bounded execution, no recursion.
- Fully typed, explicit validation.
- All thresholds grounded in peer-reviewed literature.

SMS Matrix Standards:
- EVA Readiness: ICAO Doc 9859 (2018) adapted for spacewalk physiology.
- Military Flight: MIL-STD-882E (DoD Standard Practice for System Safety).

Scientific References:
- Porta et al. (2012). HP and SAP variability complexity provide complementary
  information. J Appl Physiol, 113(12), 1810-1820. PMID: 23104699
- Lucini et al. (2014). Autonomic indices from cardiovascular variability help
  identify hypertension. J Hypertens, 32(2), 363-373. PMID: 24232167
- Zhang et al. (2020). Autonomic pattern analysis in hypertension based on
  short-term HRV. Biomed Tech, 65(4), 437-447. PMID: 32769220
- Crowe et al. (2025). Resting HR and SBP predict heat tolerance in military
  personnel. Medicina, 61(6), 1111. DOI: 10.3390/medicina61061111
- Kim & Lee (2017). Prediction of body core temperature with HRV.
  Semantic Scholar: 6f60ddec.
- Zhang et al. (2025). Physiological monitoring models in military domain.
  DOI: 10.1109/ICCNEA66167.2025.11211893
- Goutham & Saravanasankar (2025). AI-driven fatigue prediction using wearable
  sensor data. DOI: 10.1109/ICRISET64803.2025.11254790
- ICAO. (2018). Safety Management Manual (Doc 9859, 4th ed.).
- US DoD. (2012). MIL-STD-882E: Standard Practice for System Safety.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BPClassification:
    """Blood pressure classification per ACC/AHA 2017 guidelines."""

    category: str  # "Optimal", "Elevated", "Stage1_HTN", "Stage2_HTN", "Hypotension"
    modifier: float  # bounded readiness modifier
    rationale: str
    disqualifying: bool  # hard stop for EVA/flight


@dataclass(frozen=True, slots=True)
class TemperatureClassification:
    """Basal body temperature classification."""

    category: str  # "Normal", "LowGrade", "MildFever", "Fever", "MildHypothermia", "Hypothermia"
    modifier: float  # bounded readiness modifier
    rationale: str
    disqualifying: bool  # hard stop for EVA/flight


@dataclass(frozen=True, slots=True)
class SMSClassification:
    """SMS-style risk classification for operational activities."""

    severity: str
    likelihood: str
    risk_level: str
    rationale: str
    disqualifiers: Tuple[str, ...]  # immutable list of hard-stop reasons
    activity_type: str  # "EVA" or "FLIGHT"


# ---------------------------------------------------------------------------
# Blood Pressure Modifier (bounded ±4 points)
# ---------------------------------------------------------------------------

def compute_bp_readiness_modifier(
    sbp_mmhg: Optional[float],
    dbp_mmhg: Optional[float],
) -> BPClassification:
    """Compute readiness modifier from resting blood pressure.

    Based on ACC/AHA 2017 Hypertension Clinical Practice Guidelines and
    Crowe et al. (2025) military heat tolerance findings.

    Args:
        sbp_mmhg: Resting systolic blood pressure in mmHg, or None.
        dbp_mmhg: Resting diastolic blood pressure in mmHg, or None.

    Returns:
        BPClassification with category, modifier, rationale, and flag.

    Raises:
        ValueError: If values are non-finite or physiologically implausible.
    """
    if sbp_mmhg is None or dbp_mmhg is None:
        return BPClassification(
            category="Unknown",
            modifier=0.0,
            rationale="Blood pressure not provided; no modifier applied.",
            disqualifying=False,
        )

    sbp = float(sbp_mmhg)
    dbp = float(dbp_mmhg)

    if not math.isfinite(sbp) or not math.isfinite(dbp):
        raise ValueError("BP values must be finite numbers.")
    if sbp < 40 or sbp > 300 or dbp < 20 or dbp > 200:
        raise ValueError(
            f"BP values out of physiological range: SBP={sbp}, DBP={dbp}. "
            "Expected SBP 40-300, DBP 20-200 mmHg."
        )

    # Hypotension check (orthostatic/syncope risk, G-LOC concern)
    if sbp < 90 or dbp < 60:
        return BPClassification(
            category="Hypotension",
            modifier=-3.0,
            rationale=(
                f"SBP={sbp:.0f}, DBP={dbp:.0f} mmHg. Hypotension detected. "
                "Orthostatic syncope and G-LOC risk elevated "
                "(Crowe et al., 2025; Convertino, 2002)."
            ),
            disqualifying=True,
        )

    # Stage 2 Hypertension (EVA/flight disqualifying)
    if sbp >= 140 or dbp >= 90:
        return BPClassification(
            category="Stage2_HTN",
            modifier=-4.0,
            rationale=(
                f"SBP={sbp:.0f}, DBP={dbp:.0f} mmHg. Stage 2 hypertension "
                "(ACC/AHA 2017). Cardiovascular event risk elevated during "
                "high-G or EVA exertion (Lucini et al., 2014)."
            ),
            disqualifying=True,
        )

    # Stage 1 Hypertension
    if sbp >= 130 or dbp >= 80:
        return BPClassification(
            category="Stage1_HTN",
            modifier=-2.0,
            rationale=(
                f"SBP={sbp:.0f}, DBP={dbp:.0f} mmHg. Stage 1 hypertension "
                "(ACC/AHA 2017). Moderate cardiovascular load increase."
            ),
            disqualifying=False,
        )

    # Elevated
    if sbp >= 120:
        return BPClassification(
            category="Elevated",
            modifier=0.0,
            rationale=(
                f"SBP={sbp:.0f}, DBP={dbp:.0f} mmHg. Elevated blood pressure "
                "(ACC/AHA 2017). Within tolerable range."
            ),
            disqualifying=False,
        )

    # Optimal
    return BPClassification(
        category="Optimal",
        modifier=2.0,
        rationale=(
            f"SBP={sbp:.0f}, DBP={dbp:.0f} mmHg. Optimal blood pressure "
            "(ACC/AHA 2017). Positive readiness indicator "
            "(Crowe et al., 2025)."
        ),
        disqualifying=False,
    )


# ---------------------------------------------------------------------------
# Temperature Modifier (bounded ±3 points)
# ---------------------------------------------------------------------------

def compute_temperature_readiness_modifier(
    temp_c: Optional[float],
) -> TemperatureClassification:
    """Compute readiness modifier from basal (oral) body temperature.

    Based on thermoregulatory physiology and fatigue prediction models
    (Kim & Lee, 2017; Zhang et al., 2025; Goutham & Saravanasankar, 2025).

    Args:
        temp_c: Oral/surface body temperature in degrees Celsius, or None.

    Returns:
        TemperatureClassification with category, modifier, rationale, flag.

    Raises:
        ValueError: If value is non-finite or physiologically implausible.
    """
    if temp_c is None:
        return TemperatureClassification(
            category="Unknown",
            modifier=0.0,
            rationale="Body temperature not provided; no modifier applied.",
            disqualifying=False,
        )

    temp = float(temp_c)

    if not math.isfinite(temp):
        raise ValueError("Temperature must be a finite number.")
    if temp < 25.0 or temp > 45.0:
        raise ValueError(
            f"Temperature out of physiological range: {temp:.1f} C. "
            "Expected 25.0-45.0 C."
        )

    # Hypothermia
    if temp < 35.0:
        return TemperatureClassification(
            category="Hypothermia",
            modifier=-3.0,
            rationale=(
                f"Oral temp={temp:.1f} C. Hypothermia detected (<35.0 C). "
                "Medical emergency — cognitive and motor impairment expected."
            ),
            disqualifying=True,
        )

    # Mild hypothermia / subnormal
    if temp < 36.1:
        return TemperatureClassification(
            category="MildHypothermia",
            modifier=-1.0,
            rationale=(
                f"Oral temp={temp:.1f} C. Subnormal temperature (35.0-36.0 C). "
                "Possible cold exposure, fatigue, or hypothyroidism concern "
                "(Kim & Lee, 2017)."
            ),
            disqualifying=False,
        )

    # Normal
    if temp <= 37.2:
        return TemperatureClassification(
            category="Normal",
            modifier=0.0,
            rationale=(
                f"Oral temp={temp:.1f} C. Normal euthermia (36.1-37.2 C). "
                "Within expected circadian variation."
            ),
            disqualifying=False,
        )

    # Low-grade elevation
    if temp <= 37.7:
        return TemperatureClassification(
            category="LowGrade",
            modifier=-1.0,
            rationale=(
                f"Oral temp={temp:.1f} C. Low-grade elevation (37.3-37.7 C). "
                "Possible early illness, post-exercise, or circadian peak."
            ),
            disqualifying=False,
        )

    # Mild fever
    if temp <= 38.2:
        return TemperatureClassification(
            category="MildFever",
            modifier=-2.0,
            rationale=(
                f"Oral temp={temp:.1f} C. Mild fever (37.8-38.2 C). "
                "Active inflammation or infection likely. Reduced heat tolerance "
                "and performance capacity (Zhang et al., 2025)."
            ),
            disqualifying=True,
        )

    # Fever
    return TemperatureClassification(
        category="Fever",
        modifier=-3.0,
        rationale=(
            f"Oral temp={temp:.1f} C. Fever (>38.3 C). "
            "Disqualifying for EVA/flight. Active infection or heat illness "
            "(Goutham & Saravanasankar, 2025)."
        ),
        disqualifying=True,
    )


# ---------------------------------------------------------------------------
# EVA Readiness SMS Matrix (ICAO Doc 9859 adapted)
# ---------------------------------------------------------------------------

# Severity categories (5 levels) — maps from readiness score
_EVA_SEVERITY_ORDER: Tuple[str, ...] = (
    "Negligible", "Minor", "Major", "Hazardous", "Catastrophic",
)

# Likelihood categories (5 levels) — maps from physiological risk flags
_EVA_LIKELIHOOD_ORDER: Tuple[str, ...] = (
    "Extremely Improbable", "Improbable", "Remote", "Occasional", "Frequent",
)

# 5x5 EVA risk matrix (ICAO Doc 9859, Table 2-13 adapted for EVA ops)
# Rows: severity (Negligible → Catastrophic)
# Columns: likelihood (Extremely Improbable → Frequent)
_EVA_RISK_MATRIX: dict[str, Tuple[str, ...]] = {
    "Negligible":   ("Acceptable", "Acceptable", "Acceptable", "Tolerable", "Tolerable"),
    "Minor":        ("Acceptable", "Acceptable", "Tolerable", "Undesirable", "Undesirable"),
    "Major":        ("Acceptable", "Tolerable", "Undesirable", "Undesirable", "Intolerable"),
    "Hazardous":    ("Tolerable", "Undesirable", "Undesirable", "Intolerable", "Intolerable"),
    "Catastrophic": ("Undesirable", "Undesirable", "Intolerable", "Intolerable", "Intolerable"),
}


def _eva_severity_from_readiness(readiness_score: float) -> str:
    """Map readiness score (0-100) to EVA severity category."""
    score = max(0.0, min(100.0, float(readiness_score)))
    if score >= 85:
        return "Negligible"
    if score >= 75:
        return "Minor"
    if score >= 60:
        return "Major"
    if score >= 45:
        return "Hazardous"
    return "Catastrophic"


def _eva_likelihood_from_flags(
    *,
    bp_disqualifying: bool,
    temp_disqualifying: bool,
    psi_score: Optional[float],
    trajectory_risk_level: Optional[str],
    n_disqualifiers: int,
) -> str:
    """Map physiological flags to EVA likelihood category."""
    risk_count = 0
    if bp_disqualifying:
        risk_count += 2
    if temp_disqualifying:
        risk_count += 2
    if psi_score is not None and float(psi_score) >= 70.0:
        risk_count += 2
    elif psi_score is not None and float(psi_score) >= 50.0:
        risk_count += 1
    if trajectory_risk_level in ("ELEVATED", "CRITICAL"):
        risk_count += 1
    risk_count += min(n_disqualifiers, 3)  # cap extra disqualifiers

    if risk_count >= 6:
        return "Frequent"
    if risk_count >= 4:
        return "Occasional"
    if risk_count >= 2:
        return "Remote"
    if risk_count >= 1:
        return "Improbable"
    return "Extremely Improbable"


def classify_eva_risk(
    *,
    readiness_score: float,
    bp_class: BPClassification,
    temp_class: TemperatureClassification,
    psi_score: Optional[float] = None,
    trajectory_risk_level: Optional[str] = None,
) -> SMSClassification:
    """Classify EVA readiness using ICAO Doc 9859 SMS matrix.

    Args:
        readiness_score: Fused operational readiness (0-100).
        bp_class: Blood pressure classification.
        temp_class: Temperature classification.
        psi_score: Physiological Strain Index (0-100), optional.
        trajectory_risk_level: Trajectory risk level string, optional.

    Returns:
        SMSClassification for EVA operations.
    """
    disqualifiers: List[str] = []
    if bp_class.disqualifying:
        disqualifiers.append(f"BP: {bp_class.category} — {bp_class.rationale}")
    if temp_class.disqualifying:
        disqualifiers.append(f"Temp: {temp_class.category} — {temp_class.rationale}")
    if psi_score is not None and float(psi_score) >= 85.0:
        disqualifiers.append(f"PSI={psi_score:.0f} — Critical physiological strain")

    severity = _eva_severity_from_readiness(readiness_score)
    likelihood = _eva_likelihood_from_flags(
        bp_disqualifying=bp_class.disqualifying,
        temp_disqualifying=temp_class.disqualifying,
        psi_score=psi_score,
        trajectory_risk_level=trajectory_risk_level,
        n_disqualifiers=len(disqualifiers),
    )

    lik_idx = _EVA_LIKELIHOOD_ORDER.index(likelihood)
    risk_level = _EVA_RISK_MATRIX[severity][lik_idx]

    # Force Intolerable if any hard disqualifier present
    if disqualifiers:
        risk_level = "Intolerable"

    rationale = (
        f"Readiness={readiness_score:.0f}/100 → Severity={severity}; "
        f"Likelihood={likelihood} (flags: BP={bp_class.category}, "
        f"Temp={temp_class.category}"
    )
    if psi_score is not None:
        rationale += f", PSI={psi_score:.0f}"
    rationale += f"); Risk={risk_level}."
    if disqualifiers:
        rationale += f" Hard disqualifiers present ({len(disqualifiers)})."

    return SMSClassification(
        severity=severity,
        likelihood=likelihood,
        risk_level=risk_level,
        rationale=rationale,
        disqualifiers=tuple(disqualifiers),
        activity_type="EVA",
    )


# ---------------------------------------------------------------------------
# Military Flight Readiness SMS Matrix (MIL-STD-882E)
# ---------------------------------------------------------------------------

# Severity categories (4 levels, per MIL-STD-882E Table I)
_FLIGHT_SEVERITY_ORDER: Tuple[str, ...] = (
    "Negligible", "Marginal", "Critical", "Catastrophic",
)

# Likelihood categories (5 levels, per MIL-STD-882E Table II)
_FLIGHT_LIKELIHOOD_ORDER: Tuple[str, ...] = (
    "Improbable", "Remote", "Occasional", "Probable", "Frequent",
)

# 4x5 flight risk matrix (MIL-STD-882E Table III)
_FLIGHT_RISK_MATRIX: dict[str, Tuple[str, ...]] = {
    "Negligible":   ("Low", "Low", "Medium", "Medium", "Medium"),
    "Marginal":     ("Low", "Medium", "Medium", "Serious", "Serious"),
    "Critical":     ("Medium", "Medium", "Serious", "High", "High"),
    "Catastrophic": ("Medium", "Serious", "High", "High", "High"),
}


def _flight_severity_from_readiness(readiness_score: float) -> str:
    """Map readiness score to MIL-STD-882E severity (Table I)."""
    score = max(0.0, min(100.0, float(readiness_score)))
    if score >= 85:
        return "Negligible"
    if score >= 70:
        return "Marginal"
    if score >= 50:
        return "Critical"
    return "Catastrophic"


def _flight_likelihood_from_flags(
    *,
    bp_disqualifying: bool,
    temp_disqualifying: bool,
    psi_score: Optional[float],
    crew_rest_compliant: Optional[bool],
    g_loc_risk: bool,
    n_disqualifiers: int,
) -> str:
    """Map physiological and operational flags to MIL-STD-882E likelihood."""
    risk_count = 0
    if bp_disqualifying:
        risk_count += 2
    if temp_disqualifying:
        risk_count += 2
    if g_loc_risk:
        risk_count += 2
    if psi_score is not None and float(psi_score) >= 70.0:
        risk_count += 2
    elif psi_score is not None and float(psi_score) >= 50.0:
        risk_count += 1
    if crew_rest_compliant is not None and not crew_rest_compliant:
        risk_count += 2
    risk_count += min(n_disqualifiers, 2)

    if risk_count >= 7:
        return "Frequent"
    if risk_count >= 5:
        return "Probable"
    if risk_count >= 3:
        return "Occasional"
    if risk_count >= 1:
        return "Remote"
    return "Improbable"


def classify_flight_risk(
    *,
    readiness_score: float,
    bp_class: BPClassification,
    temp_class: TemperatureClassification,
    psi_score: Optional[float] = None,
    crew_rest_compliant: Optional[bool] = None,
    resting_hr_bpm: Optional[float] = None,
    rmssd_ms: Optional[float] = None,
) -> SMSClassification:
    """Classify military flight readiness using MIL-STD-882E SMS matrix.

    Includes G-LOC risk assessment: hypotension + low HRV indicates
    reduced G-tolerance (Convertino, 2002; Crowe et al., 2025).

    Args:
        readiness_score: Fused operational readiness (0-100).
        bp_class: Blood pressure classification.
        temp_class: Temperature classification.
        psi_score: Physiological Strain Index (0-100), optional.
        crew_rest_compliant: USAF crew rest compliance, optional.
        resting_hr_bpm: Resting heart rate for G-LOC assessment, optional.
        rmssd_ms: RMSSD for G-LOC assessment, optional.

    Returns:
        SMSClassification for military flight operations.
    """
    disqualifiers: List[str] = []
    if bp_class.disqualifying:
        disqualifiers.append(f"BP: {bp_class.category} — {bp_class.rationale}")
    if temp_class.disqualifying:
        disqualifiers.append(f"Temp: {temp_class.category} — {temp_class.rationale}")
    if crew_rest_compliant is not None and not crew_rest_compliant:
        disqualifiers.append("Crew rest non-compliant (AFMAN 11-202V3)")

    # G-LOC risk: hypotension + low parasympathetic tone
    g_loc_risk = False
    if bp_class.category == "Hypotension":
        g_loc_risk = True
        if rmssd_ms is not None and float(rmssd_ms) < 20.0:
            disqualifiers.append(
                f"G-LOC risk: hypotension + low RMSSD ({rmssd_ms:.0f} ms). "
                "Reduced G-tolerance expected (Convertino, 2002)."
            )
    elif resting_hr_bpm is not None and float(resting_hr_bpm) > 100:
        g_loc_risk = True
        disqualifiers.append(
            f"Resting tachycardia (HR={resting_hr_bpm:.0f} bpm). "
            "Reduced G-tolerance margin."
        )

    severity = _flight_severity_from_readiness(readiness_score)
    likelihood = _flight_likelihood_from_flags(
        bp_disqualifying=bp_class.disqualifying,
        temp_disqualifying=temp_class.disqualifying,
        psi_score=psi_score,
        crew_rest_compliant=crew_rest_compliant,
        g_loc_risk=g_loc_risk,
        n_disqualifiers=len(disqualifiers),
    )

    lik_idx = _FLIGHT_LIKELIHOOD_ORDER.index(likelihood)
    risk_level = _FLIGHT_RISK_MATRIX[severity][lik_idx]

    # Force High if any hard disqualifier present
    if disqualifiers:
        risk_level = "High"

    rationale = (
        f"Readiness={readiness_score:.0f}/100 → Severity={severity} "
        f"(MIL-STD-882E Table I); Likelihood={likelihood} (Table II); "
        f"Risk={risk_level} (Table III). "
        f"BP={bp_class.category}, Temp={temp_class.category}"
    )
    if g_loc_risk:
        rationale += ", G-LOC risk flagged"
    if crew_rest_compliant is not None:
        rationale += f", CrewRest={'compliant' if crew_rest_compliant else 'NON-COMPLIANT'}"
    rationale += "."
    if disqualifiers:
        rationale += f" Hard disqualifiers: {len(disqualifiers)}."

    return SMSClassification(
        severity=severity,
        likelihood=likelihood,
        risk_level=risk_level,
        rationale=rationale,
        disqualifiers=tuple(disqualifiers),
        activity_type="FLIGHT",
    )


# ---------------------------------------------------------------------------
# Matrix data builders (for ECharts heatmap visualization)
# ---------------------------------------------------------------------------

def build_eva_sms_heatmap_data() -> dict:
    """Build EVA SMS matrix data suitable for ECharts heatmap.

    Returns:
        Dict with keys: severity_labels, likelihood_labels, data, risk_levels.
        data is a list of [col_idx, row_idx, value] tuples.
    """
    risk_value_map = {
        "Acceptable": 0, "Tolerable": 1, "Undesirable": 2, "Intolerable": 3,
    }
    data: List[List[int]] = []
    for row_idx, severity in enumerate(_EVA_SEVERITY_ORDER):
        for col_idx, _lik in enumerate(_EVA_LIKELIHOOD_ORDER):
            risk = _EVA_RISK_MATRIX[severity][col_idx]
            data.append([col_idx, row_idx, risk_value_map[risk]])

    return {
        "severity_labels": list(_EVA_SEVERITY_ORDER),
        "likelihood_labels": list(_EVA_LIKELIHOOD_ORDER),
        "data": data,
        "risk_levels": ["Acceptable", "Tolerable", "Undesirable", "Intolerable"],
        "risk_colors": ["#27ae60", "#f39c12", "#e67e22", "#e74c3c"],
    }


def build_flight_sms_heatmap_data() -> dict:
    """Build military flight SMS matrix data suitable for ECharts heatmap.

    Returns:
        Dict with keys: severity_labels, likelihood_labels, data, risk_levels.
        data is a list of [col_idx, row_idx, value] tuples.
    """
    risk_value_map = {"Low": 0, "Medium": 1, "Serious": 2, "High": 3}
    data: List[List[int]] = []
    for row_idx, severity in enumerate(_FLIGHT_SEVERITY_ORDER):
        for col_idx, _lik in enumerate(_FLIGHT_LIKELIHOOD_ORDER):
            risk = _FLIGHT_RISK_MATRIX[severity][col_idx]
            data.append([col_idx, row_idx, risk_value_map[risk]])

    return {
        "severity_labels": list(_FLIGHT_SEVERITY_ORDER),
        "likelihood_labels": list(_FLIGHT_LIKELIHOOD_ORDER),
        "data": data,
        "risk_levels": ["Low", "Medium", "Serious", "High"],
        "risk_colors": ["#27ae60", "#f39c12", "#e67e22", "#e74c3c"],
    }
