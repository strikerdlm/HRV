"""
Comprehensive Clinical Profile Module for Mission Control - Flight Surgeon.

Provides astronaut-grade physiological assessment including:
- Extended anthropometrics (body composition)
- Basal Metabolic Rate (Mifflin-St Jeor equation - gold standard)
- NASA-based hydration and nutrition requirements
- Exercise energy expenditure calculations
- Medical history and laboratory data tracking

Scientific References:
- Mifflin-St Jeor BMR: Mifflin et al., Am J Clin Nutr 1990;51:241-7
- NASA Nutrition: JSC67378 Exploration Nutrition Requirements
- Hydration: NASA-STD-3001 Water Requirements (32 mL/kg/day minimum)
- Activity Factors: Westerterp, 2018 (PAL 1.3-2.5 range)

Author: Dr. Diego Leonel Malpica Hincapié, MD
Version: 1.0.0
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timezone
from enum import Enum
from typing import Any, Dict, Final, List, Optional, Tuple

import requests

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums and Constants
# ---------------------------------------------------------------------------

class BiologicalSex(str, Enum):
    """Biological sex for physiological calculations."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class ActivityLevel(str, Enum):
    """Physical Activity Level (PAL) classifications."""
    SEDENTARY = "sedentary"  # Little/no exercise (PAL 1.2)
    LIGHTLY_ACTIVE = "lightly_active"  # Light exercise 1-3 days/week (PAL 1.375)
    MODERATELY_ACTIVE = "moderately_active"  # Moderate exercise 3-5 days/week (PAL 1.55)
    VERY_ACTIVE = "very_active"  # Hard exercise 6-7 days/week (PAL 1.725)
    EXTRA_ACTIVE = "extra_active"  # Very hard exercise, physical job (PAL 1.9)
    ASTRONAUT_TRAINING = "astronaut_training"  # ISS-like CM exercise (PAL 2.0)


# Physical Activity Level multipliers
PAL_MULTIPLIERS: Dict[ActivityLevel, float] = {
    ActivityLevel.SEDENTARY: 1.2,
    ActivityLevel.LIGHTLY_ACTIVE: 1.375,
    ActivityLevel.MODERATELY_ACTIVE: 1.55,
    ActivityLevel.VERY_ACTIVE: 1.725,
    ActivityLevel.EXTRA_ACTIVE: 1.9,
    ActivityLevel.ASTRONAUT_TRAINING: 2.0,
}

# NASA Nutritional Constants (JSC67378)
NASA_PROTEIN_MIN_G_KG: Final[float] = 1.2  # g/kg body mass
NASA_PROTEIN_MAX_G_KG: Final[float] = 1.8  # g/kg body mass
NASA_WATER_ML_KG: Final[float] = 32.0  # mL/kg body weight
NASA_WATER_MIN_ML: Final[float] = 2500.0  # Minimum mL/day
NASA_EVA_EXTRA_KCAL: Final[float] = 500.0  # Extra kcal for EVA/intense exercise
NASA_MACRO_PROTEIN_PCT: Final[float] = 0.15  # 15% protein
NASA_MACRO_FAT_PCT: Final[float] = 0.30  # 30% fat
NASA_MACRO_CARB_PCT: Final[float] = 0.55  # 55% carbohydrates

# MET values for common exercises (Metabolic Equivalent of Task)
EXERCISE_METS: Dict[str, float] = {
    "walking_moderate": 3.5,
    "walking_brisk": 4.3,
    "cycling_light": 5.5,
    "cycling_moderate": 7.0,
    "cycling_vigorous": 10.0,
    "running_jogging": 7.0,
    "running_moderate": 9.8,
    "running_vigorous": 11.5,
    "swimming_moderate": 6.0,
    "swimming_vigorous": 9.8,
    "resistance_training": 6.0,
    "rowing_moderate": 7.0,
    "elliptical": 5.0,
    "aerobics_general": 6.5,
    "hiit": 8.0,
    "astronaut_ared": 6.0,  # Advanced Resistive Exercise Device
    "astronaut_cevis": 7.0,  # Cycle Ergometer with Vibration Isolation
    "astronaut_t2": 8.0,  # Treadmill (T2)
}

POLAR_ACCESSLINK_BASE_URL: Final[str] = "https://www.polaraccesslink.com/v3"
VO2_REFERENCE_ML_KG_MIN: Final[float] = 45.0  # Average trained adult
VO2_ADJUSTMENT_MIN: Final[float] = 0.65  # Floor multiplier for low fitness
VO2_ADJUSTMENT_MAX: Final[float] = 1.35  # Ceiling multiplier for elite fitness


def polar_accesslink_available() -> bool:
    """Return True if environment variables for Polar AccessLink are configured."""
    return bool(
        os.getenv("POLAR_ACCESSLINK_TOKEN")
        and os.getenv("POLAR_ACCESSLINK_USER_ID")
    )


def fetch_polar_vo2max(
    *,
    access_token: Optional[str] = None,
    user_id: Optional[str] = None,
    timeout: float = 10.0,
) -> Optional[float]:
    """Fetch VO2max (cardiorespiratory fitness) from Polar AccessLink API.

    Polar's AccessLink API exposes exercise intensity, body metrics, and
    cardiorespiratory fitness data collected in Polar Flow.
    See: https://www.polar.com/accesslink-api/
    The API requires OAuth credentials provisioned in the developer portal.

    Args:
        access_token: OAuth access token (defaults to POLAR_ACCESSLINK_TOKEN env).
        user_id: Polar Flow user ID (defaults to POLAR_ACCESSLINK_USER_ID env).
        timeout: HTTP timeout in seconds.

    Returns:
        VO2max in mL·kg⁻¹·min⁻¹ if available, otherwise None.
    """
    token = (access_token or os.getenv("POLAR_ACCESSLINK_TOKEN", "")).strip()
    polar_user_id = (user_id or os.getenv("POLAR_ACCESSLINK_USER_ID", "")).strip()
    if not token or not polar_user_id:
        return None
    url = f"{POLAR_ACCESSLINK_BASE_URL}/users/{polar_user_id}/cardiorespiratory-fitness"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        _LOGGER.warning("Polar AccessLink VO2max fetch failed: %s", exc)
        return None
    # API payloads vary; search for the first numeric VO2 field.
    candidate_keys = ("vo2max", "vo2_max", "cardiorespiratory_fitness")
    for key in candidate_keys:
        value = payload.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    # Some responses embed data in lists/dicts
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, dict):
                for key in candidate_keys:
                    nested = value.get(key)
                    if isinstance(nested, (int, float)):
                        return float(nested)
    return None


def adjust_met_for_vo2(
    met_value: float,
    vo2max_ml_kg_min: Optional[float],
) -> Tuple[float, float]:
    """Adjust MET value by VO2max-derived fitness factor."""
    if vo2max_ml_kg_min is None or vo2max_ml_kg_min <= 0:
        return met_value, 1.0
    factor = vo2max_ml_kg_min / VO2_REFERENCE_ML_KG_MIN
    factor = max(VO2_ADJUSTMENT_MIN, min(VO2_ADJUSTMENT_MAX, factor))
    adjusted_met = max(1.0, met_value * factor)
    return adjusted_met, factor


# ---------------------------------------------------------------------------
# Body Composition Data Class
# ---------------------------------------------------------------------------

@dataclass
class BodyComposition:
    """Extended anthropometric measurements for body composition analysis."""
    
    # Basic measurements (required)
    height_cm: float
    weight_kg: float
    
    # Body composition (optional - from bioimpedance or DEXA)
    body_fat_pct: Optional[float] = None  # Body fat percentage
    lean_mass_kg: Optional[float] = None  # Lean body mass
    muscle_mass_kg: Optional[float] = None  # Skeletal muscle mass
    bone_mass_kg: Optional[float] = None  # Bone mineral content
    water_pct: Optional[float] = None  # Total body water percentage
    visceral_fat_level: Optional[int] = None  # Visceral fat rating (1-59)
    
    # Circumferences (cm) - useful for body composition estimation
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    neck_cm: Optional[float] = None
    chest_cm: Optional[float] = None
    arm_cm: Optional[float] = None  # Relaxed bicep
    thigh_cm: Optional[float] = None
    calf_cm: Optional[float] = None
    
    # Skinfold measurements (mm) - for caliper-based body fat
    skinfold_tricep: Optional[float] = None
    skinfold_subscapular: Optional[float] = None
    skinfold_suprailiac: Optional[float] = None
    skinfold_abdominal: Optional[float] = None
    skinfold_thigh: Optional[float] = None
    
    # Measurement metadata
    measurement_date: Optional[str] = None
    measurement_method: Optional[str] = None  # bioimpedance, dexa, calipers, etc.
    
    @property
    def bmi(self) -> float:
        """Calculate Body Mass Index (kg/m²)."""
        height_m = self.height_cm / 100.0
        return self.weight_kg / (height_m ** 2)
    
    @property
    def bmi_category(self) -> str:
        """WHO BMI classification."""
        bmi = self.bmi
        if bmi < 18.5:
            return "Underweight"
        elif bmi < 25.0:
            return "Normal weight"
        elif bmi < 30.0:
            return "Overweight"
        elif bmi < 35.0:
            return "Obese Class I"
        elif bmi < 40.0:
            return "Obese Class II"
        else:
            return "Obese Class III"
    
    @property
    def waist_to_hip_ratio(self) -> Optional[float]:
        """Calculate waist-to-hip ratio if measurements available."""
        if self.waist_cm and self.hip_cm:
            return self.waist_cm / self.hip_cm
        return None
    
    @property
    def waist_to_height_ratio(self) -> Optional[float]:
        """Calculate waist-to-height ratio (should be <0.5)."""
        if self.waist_cm:
            return self.waist_cm / self.height_cm
        return None
    
    @property
    def fat_free_mass_kg(self) -> Optional[float]:
        """Calculate fat-free mass if body fat % available."""
        if self.body_fat_pct is not None:
            return self.weight_kg * (1 - self.body_fat_pct / 100)
        return self.lean_mass_kg
    
    @property
    def fat_mass_kg(self) -> Optional[float]:
        """Calculate fat mass if body fat % available."""
        if self.body_fat_pct is not None:
            return self.weight_kg * (self.body_fat_pct / 100)
        return None
    
    def estimate_body_fat_navy(self, sex: BiologicalSex, age: int) -> Optional[float]:
        """
        Estimate body fat % using US Navy method.
        
        Requires: waist, neck, (hip for females), height
        Reference: Hodgdon & Beckett, 1984
        """
        if not self.waist_cm or not self.neck_cm:
            return None
        
        if sex == BiologicalSex.FEMALE and not self.hip_cm:
            return None
        
        if sex == BiologicalSex.MALE:
            # Male formula
            bf = 495 / (1.0324 - 0.19077 * math.log10(self.waist_cm - self.neck_cm) 
                       + 0.15456 * math.log10(self.height_cm)) - 450
        else:
            # Female formula
            bf = 495 / (1.29579 - 0.35004 * math.log10(self.waist_cm + self.hip_cm - self.neck_cm)
                       + 0.22100 * math.log10(self.height_cm)) - 450
        
        return max(0, min(100, bf))  # Clamp to valid range
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['bmi'] = self.bmi
        d['bmi_category'] = self.bmi_category
        d['waist_to_hip_ratio'] = self.waist_to_hip_ratio
        d['waist_to_height_ratio'] = self.waist_to_height_ratio
        d['fat_free_mass_kg'] = self.fat_free_mass_kg
        d['fat_mass_kg'] = self.fat_mass_kg
        return d


# ---------------------------------------------------------------------------
# Medical History Data Class
# ---------------------------------------------------------------------------

@dataclass
class MedicalHistory:
    """Comprehensive medical history and antecedents."""
    
    # Cardiovascular
    hypertension: bool = False
    hypertension_controlled: Optional[bool] = None
    coronary_artery_disease: bool = False
    arrhythmia: bool = False
    arrhythmia_type: Optional[str] = None  # AFib, SVT, PVCs, etc.
    heart_failure: bool = False
    valvular_disease: bool = False
    peripheral_vascular_disease: bool = False
    dvt_pe_history: bool = False  # Deep vein thrombosis / pulmonary embolism
    
    # Respiratory
    asthma: bool = False
    copd: bool = False
    sleep_apnea: bool = False
    sleep_apnea_treated: Optional[bool] = None
    
    # STOP-BANG Sleep Apnea Screening Components
    snoring: Optional[bool] = None  # S: Loud snoring (heard through closed doors)
    tiredness: Optional[bool] = None  # T: Daytime tiredness/fatigue
    observed_apnea: Optional[bool] = None  # O: Witnessed apnea (breathing stops during sleep)
    
    # Metabolic/Endocrine
    diabetes_type: Optional[str] = None  # None, Type1, Type2, Gestational
    diabetes_controlled: Optional[bool] = None
    thyroid_disorder: Optional[str] = None  # Hypo, Hyper, None
    dyslipidemia: bool = False
    
    # Neurological
    migraine: bool = False
    seizure_disorder: bool = False
    stroke_tia_history: bool = False
    neuropathy: bool = False
    
    # Musculoskeletal
    osteoarthritis: bool = False
    rheumatoid_arthritis: bool = False
    osteoporosis: bool = False
    back_problems: bool = False
    
    # Psychiatric
    depression: bool = False
    anxiety_disorder: bool = False
    ptsd: bool = False
    other_psychiatric: Optional[str] = None
    
    # Gastrointestinal
    gerd: bool = False
    ibs: bool = False
    liver_disease: bool = False
    
    # Renal
    chronic_kidney_disease: bool = False
    ckd_stage: Optional[int] = None  # 1-5
    kidney_stones: bool = False
    
    # Hematological
    anemia: bool = False
    bleeding_disorder: bool = False
    
    # Allergies
    drug_allergies: List[str] = field(default_factory=list)
    environmental_allergies: List[str] = field(default_factory=list)
    food_allergies: List[str] = field(default_factory=list)
    latex_allergy: bool = False
    
    # Surgical history
    surgical_history: List[str] = field(default_factory=list)
    
    # Family history
    family_heart_disease: bool = False
    family_diabetes: bool = False
    family_cancer: Optional[str] = None
    family_stroke: bool = False
    
    # Current medications
    current_medications: List[str] = field(default_factory=list)
    
    # Supplements
    supplements: List[str] = field(default_factory=list)
    
    # Lifestyle
    tobacco_use: Optional[str] = None  # never, former, current
    tobacco_pack_years: Optional[float] = None
    alcohol_drinks_per_week: Optional[int] = None
    recreational_drugs: bool = False
    
    # Reproductive (if applicable)
    pregnant: Optional[bool] = None
    weeks_pregnant: Optional[int] = None
    breastfeeding: Optional[bool] = None
    
    # Vaccination status
    vaccinations_up_to_date: bool = True
    
    # Additional notes
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def get_cardiovascular_risk_factors(self) -> List[str]:
        """Get list of cardiovascular risk factors."""
        factors = []
        if self.hypertension:
            factors.append("Hypertension")
        if self.diabetes_type:
            factors.append(f"Diabetes ({self.diabetes_type})")
        if self.dyslipidemia:
            factors.append("Dyslipidemia")
        if self.tobacco_use == "current":
            factors.append("Current tobacco use")
        if self.family_heart_disease:
            factors.append("Family history of heart disease")
        if self.coronary_artery_disease:
            factors.append("Coronary artery disease")
        if self.stroke_tia_history:
            factors.append("History of stroke/TIA")
        return factors


# ---------------------------------------------------------------------------
# Laboratory Data Classes
# ---------------------------------------------------------------------------

@dataclass
class CompleteBloodCount:
    """Complete Blood Count (CBC) / Hemogram."""
    
    # Test metadata
    test_date: str
    laboratory: Optional[str] = None
    
    # Red blood cells
    rbc_million_ul: Optional[float] = None  # Red blood cell count (M/µL)
    hemoglobin_g_dl: Optional[float] = None  # Hemoglobin (g/dL)
    hematocrit_pct: Optional[float] = None  # Hematocrit (%)
    mcv_fl: Optional[float] = None  # Mean corpuscular volume (fL)
    mch_pg: Optional[float] = None  # Mean corpuscular hemoglobin (pg)
    mchc_g_dl: Optional[float] = None  # Mean corpuscular hemoglobin concentration (g/dL)
    rdw_pct: Optional[float] = None  # Red cell distribution width (%)
    
    # White blood cells
    wbc_thousand_ul: Optional[float] = None  # White blood cell count (K/µL)
    neutrophils_pct: Optional[float] = None
    lymphocytes_pct: Optional[float] = None
    monocytes_pct: Optional[float] = None
    eosinophils_pct: Optional[float] = None
    basophils_pct: Optional[float] = None
    
    # Absolute counts
    neutrophils_abs: Optional[float] = None  # K/µL
    lymphocytes_abs: Optional[float] = None
    monocytes_abs: Optional[float] = None
    eosinophils_abs: Optional[float] = None
    basophils_abs: Optional[float] = None
    
    # Platelets
    platelets_thousand_ul: Optional[float] = None  # Platelet count (K/µL)
    mpv_fl: Optional[float] = None  # Mean platelet volume (fL)
    
    # Reticulocytes (if ordered)
    reticulocyte_pct: Optional[float] = None
    reticulocyte_abs: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def check_anemia(self, sex: BiologicalSex) -> Tuple[bool, str]:
        """Check for anemia based on WHO criteria."""
        if self.hemoglobin_g_dl is None:
            return False, "Hemoglobin not available"
        
        # WHO anemia thresholds
        if sex == BiologicalSex.MALE:
            threshold = 13.0
        else:
            threshold = 12.0
        
        if self.hemoglobin_g_dl < threshold:
            severity = "mild" if self.hemoglobin_g_dl >= threshold - 2 else "moderate" if self.hemoglobin_g_dl >= threshold - 4 else "severe"
            return True, f"Anemia detected ({severity})"
        return False, "No anemia"


@dataclass
class BloodChemistry:
    """Comprehensive Metabolic Panel and additional chemistry."""
    
    # Test metadata
    test_date: str
    fasting: bool = True
    laboratory: Optional[str] = None
    
    # Basic Metabolic Panel
    glucose_mg_dl: Optional[float] = None
    bun_mg_dl: Optional[float] = None  # Blood Urea Nitrogen
    creatinine_mg_dl: Optional[float] = None
    sodium_meq_l: Optional[float] = None
    potassium_meq_l: Optional[float] = None
    chloride_meq_l: Optional[float] = None
    co2_meq_l: Optional[float] = None  # Bicarbonate
    calcium_mg_dl: Optional[float] = None
    
    # Comprehensive additions
    total_protein_g_dl: Optional[float] = None
    albumin_g_dl: Optional[float] = None
    globulin_g_dl: Optional[float] = None
    bilirubin_total_mg_dl: Optional[float] = None
    bilirubin_direct_mg_dl: Optional[float] = None
    
    # Liver enzymes
    ast_u_l: Optional[float] = None  # Aspartate aminotransferase
    alt_u_l: Optional[float] = None  # Alanine aminotransferase
    alp_u_l: Optional[float] = None  # Alkaline phosphatase
    ggt_u_l: Optional[float] = None  # Gamma-glutamyl transferase
    
    # Lipid Panel
    total_cholesterol_mg_dl: Optional[float] = None
    ldl_cholesterol_mg_dl: Optional[float] = None
    hdl_cholesterol_mg_dl: Optional[float] = None
    triglycerides_mg_dl: Optional[float] = None
    vldl_mg_dl: Optional[float] = None
    
    # Diabetes markers
    hba1c_pct: Optional[float] = None  # Glycated hemoglobin
    fasting_insulin_uiu_ml: Optional[float] = None
    
    # Thyroid
    tsh_miu_l: Optional[float] = None
    free_t4_ng_dl: Optional[float] = None
    free_t3_pg_ml: Optional[float] = None
    
    # Iron studies
    iron_ug_dl: Optional[float] = None
    tibc_ug_dl: Optional[float] = None  # Total iron-binding capacity
    ferritin_ng_ml: Optional[float] = None
    transferrin_saturation_pct: Optional[float] = None
    
    # Vitamins
    vitamin_d_25oh_ng_ml: Optional[float] = None
    vitamin_b12_pg_ml: Optional[float] = None
    folate_ng_ml: Optional[float] = None
    
    # Inflammatory markers
    crp_mg_l: Optional[float] = None  # C-reactive protein
    esr_mm_hr: Optional[float] = None  # Erythrocyte sedimentation rate
    
    # Cardiac markers (if applicable)
    troponin_ng_ml: Optional[float] = None
    bnp_pg_ml: Optional[float] = None  # B-type natriuretic peptide
    
    # Electrolytes (additional)
    magnesium_mg_dl: Optional[float] = None
    phosphorus_mg_dl: Optional[float] = None
    
    # Uric acid
    uric_acid_mg_dl: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @property
    def egfr_ml_min(self) -> Optional[float]:
        """
        Estimate GFR using CKD-EPI 2021 equation (race-free).
        
        Requires creatinine, age, and sex.
        """
        if self.creatinine_mg_dl is None:
            return None
        # This is a simplified version - full implementation would need age and sex
        # CKD-EPI 2021: 142 × min(Cr/κ, 1)^α × max(Cr/κ, 1)^-1.200 × 0.9938^age × (1.012 if female)
        return None  # Placeholder - needs to be called with demographics
    
    @property
    def anion_gap(self) -> Optional[float]:
        """Calculate anion gap if electrolytes available."""
        if all([self.sodium_meq_l, self.chloride_meq_l, self.co2_meq_l]):
            return self.sodium_meq_l - (self.chloride_meq_l + self.co2_meq_l)
        return None
    
    @property
    def ldl_hdl_ratio(self) -> Optional[float]:
        """Calculate LDL/HDL ratio."""
        if self.ldl_cholesterol_mg_dl and self.hdl_cholesterol_mg_dl:
            return self.ldl_cholesterol_mg_dl / self.hdl_cholesterol_mg_dl
        return None
    
    @property
    def non_hdl_cholesterol(self) -> Optional[float]:
        """Calculate non-HDL cholesterol."""
        if self.total_cholesterol_mg_dl and self.hdl_cholesterol_mg_dl:
            return self.total_cholesterol_mg_dl - self.hdl_cholesterol_mg_dl
        return None


@dataclass
class Urinalysis:
    """Complete urinalysis results."""
    
    # Test metadata
    test_date: str
    collection_method: str = "clean_catch"  # clean_catch, catheter, 24hr
    
    # Physical examination
    color: Optional[str] = None  # yellow, amber, red, etc.
    appearance: Optional[str] = None  # clear, cloudy, turbid
    specific_gravity: Optional[float] = None  # 1.001-1.035
    
    # Chemical analysis (dipstick)
    ph: Optional[float] = None  # 4.5-8.0
    protein_mg_dl: Optional[float] = None  # or qualitative: negative, trace, +, ++, +++
    protein_qualitative: Optional[str] = None
    glucose_mg_dl: Optional[float] = None
    glucose_qualitative: Optional[str] = None
    ketones: Optional[str] = None  # negative, trace, small, moderate, large
    blood: Optional[str] = None  # negative, trace, +, ++, +++
    bilirubin: Optional[str] = None
    urobilinogen_eu_dl: Optional[float] = None
    nitrite: Optional[str] = None  # negative, positive
    leukocyte_esterase: Optional[str] = None  # negative, trace, +, ++, +++
    
    # Microscopic examination
    rbc_per_hpf: Optional[float] = None  # Red blood cells per high power field
    wbc_per_hpf: Optional[float] = None  # White blood cells per high power field
    epithelial_cells_per_hpf: Optional[float] = None
    bacteria: Optional[str] = None  # none, few, moderate, many
    casts: Optional[str] = None  # hyaline, granular, cellular, etc.
    crystals: Optional[str] = None  # type if present
    yeast: Optional[str] = None
    
    # 24-hour collection (if applicable)
    volume_ml_24hr: Optional[float] = None
    creatinine_clearance_ml_min: Optional[float] = None
    protein_g_24hr: Optional[float] = None
    albumin_mg_24hr: Optional[float] = None
    sodium_meq_24hr: Optional[float] = None
    potassium_meq_24hr: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Metabolic Calculations
# ---------------------------------------------------------------------------

def calculate_bmr_mifflin_st_jeor(
    weight_kg: float,
    height_cm: float,
    age_years: int,
    sex: BiologicalSex,
) -> float:
    """
    Calculate Basal Metabolic Rate using Mifflin-St Jeor equation.
    
    This is the most accurate equation for estimating BMR, recommended by
    the American Dietetic Association (now Academy of Nutrition and Dietetics).
    
    Reference: Mifflin MD et al. Am J Clin Nutr. 1990;51(2):241-247.
    
    Args:
        weight_kg: Body weight in kilograms
        height_cm: Height in centimeters
        age_years: Age in years
        sex: Biological sex for calculation
        
    Returns:
        BMR in kcal/day
    """
    # Base calculation
    bmr = (10.0 * weight_kg) + (6.25 * height_cm) - (5.0 * age_years)
    
    # Sex-specific adjustment
    if sex == BiologicalSex.MALE:
        bmr += 5
    else:  # Female or Other (use female as conservative estimate)
        bmr -= 161
    
    return bmr


def calculate_bmr_harris_benedict(
    weight_kg: float,
    height_cm: float,
    age_years: int,
    sex: BiologicalSex,
) -> float:
    """
    Calculate BMR using revised Harris-Benedict equation (1984).
    
    Less accurate than Mifflin-St Jeor but included for comparison.
    
    Args:
        weight_kg: Body weight in kilograms
        height_cm: Height in centimeters
        age_years: Age in years
        sex: Biological sex
        
    Returns:
        BMR in kcal/day
    """
    if sex == BiologicalSex.MALE:
        bmr = 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * age_years)
    else:
        bmr = 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * age_years)
    
    return bmr


def calculate_bmr_katch_mcardle(
    lean_mass_kg: float,
) -> float:
    """
    Calculate BMR using Katch-McArdle equation.
    
    More accurate when lean body mass is known (from body composition).
    
    Args:
        lean_mass_kg: Lean body mass in kilograms
        
    Returns:
        BMR in kcal/day
    """
    return 370 + (21.6 * lean_mass_kg)


def calculate_tdee(
    bmr: float,
    activity_level: ActivityLevel,
) -> float:
    """
    Calculate Total Daily Energy Expenditure (TDEE).
    
    Args:
        bmr: Basal Metabolic Rate in kcal/day
        activity_level: Physical activity level
        
    Returns:
        TDEE in kcal/day
    """
    pal = PAL_MULTIPLIERS.get(activity_level, 1.55)
    return bmr * pal


def calculate_exercise_energy_expenditure(
    weight_kg: float,
    exercise_type: str,
    duration_minutes: float,
    vo2max_ml_kg_min: Optional[float] = None,
) -> Dict[str, float]:
    """
    Calculate exercise energy expenditure with VO2max compensation.
    
    This function returns both the baseline MET-derived calories and an
    adjusted estimate that scales effort according to the participant's
    VO2max. Astronauts with higher aerobic capacity expend noticeably more
    energy for the same scheduled countermeasure block, so planning must
    compensate accordingly (NASA Glenn Exploration Medical Technologies).
    See: https://www.nasa.gov/glenn/glenn-expertise-space-exploration/human-health-performance/exploration-medical-technologies/
    
    Args:
        weight_kg: Body weight in kilograms
        exercise_type: Type of exercise (key from EXERCISE_METS)
        duration_minutes: Exercise duration in minutes
        vo2max_ml_kg_min: Optional VO2max for scaling effort
        
    Returns:
        Dictionary with baseline/adjusted METs and kcal estimates
    """
    base_met = EXERCISE_METS.get(exercise_type, 5.0)
    adjusted_met, vo2_factor = adjust_met_for_vo2(base_met, vo2max_ml_kg_min)
    duration_hours = max(0.0, duration_minutes) / 60.0
    base_kcal = base_met * weight_kg * duration_hours
    adjusted_kcal = adjusted_met * weight_kg * duration_hours
    return {
        "base_met": round(base_met, 3),
        "adjusted_met": round(adjusted_met, 3),
        "vo2_factor": round(vo2_factor, 3),
        "base_kcal": round(base_kcal, 2),
        "adjusted_kcal": round(adjusted_kcal, 2),
    }


def calculate_exercise_calories(
    weight_kg: float,
    exercise_type: str,
    duration_minutes: float,
    vo2max_ml_kg_min: Optional[float] = None,
) -> float:
    """Backward-compatible helper returning only the adjusted calories."""
    summary = calculate_exercise_energy_expenditure(
        weight_kg=weight_kg,
        exercise_type=exercise_type,
        duration_minutes=duration_minutes,
        vo2max_ml_kg_min=vo2max_ml_kg_min,
    )
    return summary["adjusted_kcal"]


def calculate_nasa_water_requirement(
    weight_kg: float,
    activity_level: ActivityLevel = ActivityLevel.MODERATELY_ACTIVE,
    exercise_hours: float = 0.0,
    hot_environment: bool = False,
) -> Dict[str, float]:
    """
    Calculate daily water requirements based on NASA standards.
    
    Reference: NASA-STD-3001 Water Requirements
    
    Args:
        weight_kg: Body weight in kilograms
        activity_level: Physical activity level
        exercise_hours: Additional exercise hours beyond normal activity
        hot_environment: Whether in hot environment (increases requirements)
        
    Returns:
        Dictionary with water requirement details in mL
    """
    # Base requirement: 32 mL/kg body weight
    base_ml = max(weight_kg * NASA_WATER_ML_KG, NASA_WATER_MIN_ML)
    
    # Activity adjustment (NASA astronauts need more during exercise)
    activity_multipliers = {
        ActivityLevel.SEDENTARY: 1.0,
        ActivityLevel.LIGHTLY_ACTIVE: 1.1,
        ActivityLevel.MODERATELY_ACTIVE: 1.2,
        ActivityLevel.VERY_ACTIVE: 1.3,
        ActivityLevel.EXTRA_ACTIVE: 1.4,
        ActivityLevel.ASTRONAUT_TRAINING: 1.5,
    }
    activity_mult = activity_multipliers.get(activity_level, 1.2)
    
    # Exercise adds ~500-1000 mL per hour of vigorous activity
    exercise_ml = exercise_hours * 750  # Average
    
    # Hot environment adds 20%
    environment_mult = 1.2 if hot_environment else 1.0
    
    total_ml = (base_ml * activity_mult + exercise_ml) * environment_mult
    
    return {
        "base_ml": base_ml,
        "activity_adjusted_ml": base_ml * activity_mult,
        "exercise_additional_ml": exercise_ml,
        "environment_multiplier": environment_mult,
        "total_ml": total_ml,
        "total_liters": total_ml / 1000,
        "minimum_glasses_8oz": math.ceil(total_ml / 237),  # 8 oz = 237 mL
    }


def calculate_nasa_macronutrients(
    tdee_kcal: float,
    weight_kg: float,
    is_high_activity: bool = False,
) -> Dict[str, Any]:
    """
    Calculate macronutrient requirements based on NASA guidelines.
    
    Reference: JSC67378 Exploration Nutrition Requirements
    
    Args:
        tdee_kcal: Total daily energy expenditure in kcal
        weight_kg: Body weight in kilograms
        is_high_activity: Whether subject has high activity (uses higher protein)
        
    Returns:
        Dictionary with macronutrient requirements
    """
    # Protein: 1.2-1.8 g/kg, use middle-high for active individuals
    protein_g_kg = NASA_PROTEIN_MAX_G_KG if is_high_activity else (NASA_PROTEIN_MIN_G_KG + NASA_PROTEIN_MAX_G_KG) / 2
    protein_g = weight_kg * protein_g_kg
    protein_kcal = protein_g * 4  # 4 kcal per gram protein
    
    # Fat: 30% of calories
    fat_kcal = tdee_kcal * NASA_MACRO_FAT_PCT
    fat_g = fat_kcal / 9  # 9 kcal per gram fat
    
    # Carbohydrates: remainder (approximately 55%)
    carb_kcal = tdee_kcal - protein_kcal - fat_kcal
    carb_g = carb_kcal / 4  # 4 kcal per gram carb
    
    # Fiber: 14g per 1000 kcal (IOM recommendation)
    fiber_g = (tdee_kcal / 1000) * 14
    
    return {
        "total_kcal": tdee_kcal,
        "protein_g": round(protein_g, 1),
        "protein_kcal": round(protein_kcal, 0),
        "protein_pct": round(protein_kcal / tdee_kcal * 100, 1),
        "fat_g": round(fat_g, 1),
        "fat_kcal": round(fat_kcal, 0),
        "fat_pct": round(fat_kcal / tdee_kcal * 100, 1),
        "carbohydrate_g": round(carb_g, 1),
        "carbohydrate_kcal": round(carb_kcal, 0),
        "carbohydrate_pct": round(carb_kcal / tdee_kcal * 100, 1),
        "fiber_g": round(fiber_g, 1),
        "protein_g_per_kg": protein_g_kg,
    }


def calculate_comprehensive_requirements(
    weight_kg: float,
    height_cm: float,
    age_years: int,
    sex: BiologicalSex,
    activity_level: ActivityLevel,
    exercise_type: str = "cycling_moderate",
    exercise_duration_min: float = 120,  # 2 hours as requested
    vo2max_ml_kg_min: Optional[float] = None,
    lean_mass_kg: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Calculate comprehensive physiological requirements for astronaut-grade assessment.
    
    Includes adjustments based on VO2max and body composition if available.
    
    Args:
        weight_kg: Body weight in kilograms
        height_cm: Height in centimeters
        age_years: Age in years
        sex: Biological sex
        activity_level: Physical activity level
        exercise_type: Type of planned exercise
        exercise_duration_min: Exercise duration in minutes
        vo2max_ml_kg_min: VO2max if known (adjusts calculations)
        lean_mass_kg: Lean body mass if known (more accurate BMR)
        
    Returns:
        Comprehensive dictionary with all calculated requirements
    """
    # Calculate BMR using best available method
    if lean_mass_kg:
        bmr = calculate_bmr_katch_mcardle(lean_mass_kg)
        bmr_method = "Katch-McArdle (lean mass)"
    else:
        bmr = calculate_bmr_mifflin_st_jeor(weight_kg, height_cm, age_years, sex)
        bmr_method = "Mifflin-St Jeor"
    
    # Harris-Benedict for comparison
    bmr_harris = calculate_bmr_harris_benedict(weight_kg, height_cm, age_years, sex)
    
    # Adjust BMR based on VO2max if available (higher VO2max = higher metabolism)
    bmr_adjusted = bmr
    vo2max_adjustment = 1.0
    if vo2max_ml_kg_min:
        # VO2max above average (45 mL/kg/min) increases BMR
        if vo2max_ml_kg_min > 45:
            vo2max_adjustment = 1 + (vo2max_ml_kg_min - 45) * 0.005  # 0.5% per unit above average
        elif vo2max_ml_kg_min < 35:
            vo2max_adjustment = 1 - (35 - vo2max_ml_kg_min) * 0.005  # 0.5% per unit below average
        bmr_adjusted = bmr * vo2max_adjustment
    
    # Calculate TDEE
    tdee = calculate_tdee(bmr_adjusted, activity_level)
    
    # Exercise calories for the specified duration
    exercise_summary = calculate_exercise_energy_expenditure(
        weight_kg=weight_kg,
        exercise_type=exercise_type,
        duration_minutes=exercise_duration_min,
        vo2max_ml_kg_min=vo2max_ml_kg_min,
    )
    exercise_kcal = exercise_summary["adjusted_kcal"]
    
    # Total daily needs with exercise
    total_kcal_with_exercise = tdee + exercise_kcal
    
    # NASA EVA-level adjustment (extra 500 kcal for intense activities)
    is_high_intensity = exercise_type in ["running_vigorous", "hiit", "astronaut_t2", "swimming_vigorous"]
    if is_high_intensity:
        total_kcal_with_exercise += NASA_EVA_EXTRA_KCAL
    
    # Water requirements
    exercise_hours = exercise_duration_min / 60
    water_reqs = calculate_nasa_water_requirement(
        weight_kg, activity_level, exercise_hours
    )
    
    # Macronutrient requirements
    macros = calculate_nasa_macronutrients(
        total_kcal_with_exercise, weight_kg, is_high_intensity
    )
    
    # Calculate recommended ranges
    return {
        "bmr": {
            "value_kcal": round(bmr, 0),
            "method": bmr_method,
            "harris_benedict_kcal": round(bmr_harris, 0),
            "vo2max_adjustment": round(vo2max_adjustment, 3),
            "adjusted_kcal": round(bmr_adjusted, 0),
        },
        "energy": {
            "bmr_kcal": round(bmr_adjusted, 0),
            "tdee_kcal": round(tdee, 0),
            "activity_level": activity_level.value,
            "pal_multiplier": PAL_MULTIPLIERS.get(activity_level, 1.55),
            "exercise_kcal": round(exercise_kcal, 0),
            "exercise_type": exercise_type,
            "exercise_duration_min": exercise_duration_min,
            "eva_adjustment_kcal": NASA_EVA_EXTRA_KCAL if is_high_intensity else 0,
            "total_daily_kcal": round(total_kcal_with_exercise, 0),
            "exercise_details": exercise_summary,
        },
        "hydration": water_reqs,
        "macronutrients": macros,
        "subject_data": {
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "age_years": age_years,
            "sex": sex.value,
            "vo2max_ml_kg_min": vo2max_ml_kg_min,
            "lean_mass_kg": lean_mass_kg,
        },
        "nasa_reference": "JSC67378 Exploration Nutrition Requirements",
        "bmr_reference": "Mifflin et al., Am J Clin Nutr 1990;51:241-7",
        "calculation_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def calculate_egfr_ckd_epi_2021(
    creatinine_mg_dl: float,
    age_years: int,
    sex: BiologicalSex,
) -> float:
    """
    Calculate estimated GFR using CKD-EPI 2021 equation (race-free).
    
    Reference: Inker LA, et al. N Engl J Med. 2021;385(19):1737-1749.
    
    Args:
        creatinine_mg_dl: Serum creatinine in mg/dL
        age_years: Age in years
        sex: Biological sex
        
    Returns:
        eGFR in mL/min/1.73m²
    """
    if sex == BiologicalSex.FEMALE:
        kappa = 0.7
        alpha = -0.241
        sex_mult = 1.012
    else:
        kappa = 0.9
        alpha = -0.302
        sex_mult = 1.0
    
    cr_kappa = creatinine_mg_dl / kappa
    
    if cr_kappa < 1:
        egfr = 142 * (cr_kappa ** alpha) * (0.9938 ** age_years) * sex_mult
    else:
        egfr = 142 * (cr_kappa ** -1.200) * (0.9938 ** age_years) * sex_mult
    
    return round(egfr, 1)


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "BiologicalSex",
    "ActivityLevel",
    # Data classes
    "BodyComposition",
    "MedicalHistory",
    "CompleteBloodCount",
    "BloodChemistry",
    "Urinalysis",
    # Constants
    "PAL_MULTIPLIERS",
    "EXERCISE_METS",
    "NASA_PROTEIN_MIN_G_KG",
    "NASA_PROTEIN_MAX_G_KG",
    "NASA_WATER_ML_KG",
    "NASA_WATER_MIN_ML",
    # Calculation functions
    "calculate_bmr_mifflin_st_jeor",
    "calculate_bmr_harris_benedict",
    "calculate_bmr_katch_mcardle",
    "calculate_tdee",
    "calculate_exercise_calories",
    "calculate_nasa_water_requirement",
    "calculate_nasa_macronutrients",
    "calculate_comprehensive_requirements",
    "calculate_egfr_ckd_epi_2021",
]

