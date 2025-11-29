"""Comprehensive user profile module with validated clinical scales.

This module provides:
- Extended user biometric profiles (height, weight, BMI, VO2max)
- Validated clinical assessment scales for fatigue and sleep
- Integration with HRV/fatigue calculations
- Database-ready data models for Docker/PostgreSQL deployment

Validated Scales Included:
- Epworth Sleepiness Scale (ESS) - Johns MW, Sleep 1991
- Samn-Perelli Fatigue Scale - Samn & Perelli, 1982
- Karolinska Sleepiness Scale (KSS) - Åkerstedt & Gillberg, 1990
- Pittsburgh Sleep Quality Index (PSQI) - Buysse et al., Sleep 1989
- Stanford Sleepiness Scale (SSS) - Hoddes et al., 1973
- Fatigue Severity Scale (FSS) - Krupp et al., 1989
- Profile of Mood States - Fatigue subscale (POMS-F)

Author: Dr. Diego Malpica, MD - Aerospace Medicine Specialist
National University of Colombia | Colombian Aerospace Force

References:
- Johns MW. A new method for measuring daytime sleepiness: the Epworth
  sleepiness scale. Sleep. 1991;14(6):540-545.
- Samn SW, Perelli LP. Estimating aircrew fatigue: a technique with application
  to airlift operations. Brooks AFB, TX: USAF School of Aerospace Medicine; 1982.
- Åkerstedt T, Gillberg M. Subjective and objective sleepiness in the active
  individual. Int J Neurosci. 1990;52(1-2):29-37.
- Buysse DJ, et al. The Pittsburgh Sleep Quality Index: a new instrument for
  psychiatric practice and research. Psychiatry Res. 1989;28(2):193-213.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timezone
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Final, TypedDict

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Reference values for HRV normalization by age/sex
# Based on Nunan et al. 2010, Shaffer & Ginsberg 2017
_RMSSD_NORMS: Final[dict[str, dict[str, float]]] = {
    # Format: age_group: {male_mean, male_sd, female_mean, female_sd}
    "18-25": {"male_mean": 42.0, "male_sd": 15.0, "female_mean": 45.0, "female_sd": 18.0},
    "26-35": {"male_mean": 38.0, "male_sd": 14.0, "female_mean": 42.0, "female_sd": 16.0},
    "36-45": {"male_mean": 32.0, "male_sd": 12.0, "female_mean": 36.0, "female_sd": 14.0},
    "46-55": {"male_mean": 26.0, "male_sd": 10.0, "female_mean": 30.0, "female_sd": 12.0},
    "56-65": {"male_mean": 22.0, "male_sd": 9.0, "female_mean": 25.0, "female_sd": 10.0},
    "65+": {"male_mean": 18.0, "male_sd": 8.0, "female_mean": 21.0, "female_sd": 9.0},
}


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Sex(str, Enum):
    """Biological sex for physiological calculations."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class ActivityLevel(IntEnum):
    """Physical activity level classification.

    Based on WHO physical activity guidelines and PAL (Physical Activity Level).
    """

    SEDENTARY = 1  # PAL < 1.4: Desk job, no exercise
    LIGHTLY_ACTIVE = 2  # PAL 1.4-1.6: Light exercise 1-3 days/week
    MODERATELY_ACTIVE = 3  # PAL 1.6-1.9: Moderate exercise 3-5 days/week
    VERY_ACTIVE = 4  # PAL 1.9-2.2: Hard exercise 6-7 days/week
    EXTREMELY_ACTIVE = 5  # PAL > 2.2: Very hard exercise, physical job


class ChronotypeCategory(str, Enum):
    """Chronotype classification based on morningness-eveningness.

    Based on Horne & Östberg Morningness-Eveningness Questionnaire (MEQ).
    """

    DEFINITE_MORNING = "definite_morning"  # MEQ 70-86
    MODERATE_MORNING = "moderate_morning"  # MEQ 59-69
    NEITHER = "neither"  # MEQ 42-58
    MODERATE_EVENING = "moderate_evening"  # MEQ 31-41
    DEFINITE_EVENING = "definite_evening"  # MEQ 16-30


class OccupationType(str, Enum):
    """Occupation type for fatigue risk context."""

    PILOT = "pilot"
    AIR_TRAFFIC_CONTROLLER = "atc"
    FLIGHT_CREW = "flight_crew"
    MEDICAL_PROFESSIONAL = "medical"
    SHIFT_WORKER = "shift_worker"
    MILITARY = "military"
    DRIVER = "driver"
    RESEARCHER = "researcher"
    OFFICE_WORKER = "office"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Clinical Scale Data Classes
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class EpworthSleepinessScale:
    """Epworth Sleepiness Scale (ESS) assessment.

    8 situations rated 0-3 for chance of dozing.
    Total score 0-24; >10 indicates excessive daytime sleepiness.

    Reference: Johns MW. Sleep 1991;14(6):540-545.
    """

    sitting_reading: int  # 0-3
    watching_tv: int  # 0-3
    sitting_inactive_public: int  # 0-3
    passenger_car_hour: int  # 0-3
    lying_down_afternoon: int  # 0-3
    sitting_talking: int  # 0-3
    sitting_quietly_after_lunch: int  # 0-3
    car_stopped_traffic: int  # 0-3
    assessment_date: date = field(default_factory=date.today)

    @property
    def total_score(self) -> int:
        """Calculate total ESS score (0-24)."""
        return (
            self.sitting_reading
            + self.watching_tv
            + self.sitting_inactive_public
            + self.passenger_car_hour
            + self.lying_down_afternoon
            + self.sitting_talking
            + self.sitting_quietly_after_lunch
            + self.car_stopped_traffic
        )

    @property
    def interpretation(self) -> str:
        """Interpret ESS score."""
        score = self.total_score
        if score <= 5:
            return "Lower normal daytime sleepiness"
        if score <= 10:
            return "Higher normal daytime sleepiness"
        if score <= 12:
            return "Mild excessive daytime sleepiness"
        if score <= 15:
            return "Moderate excessive daytime sleepiness"
        return "Severe excessive daytime sleepiness"

    @property
    def is_excessive_sleepiness(self) -> bool:
        """Check if score indicates excessive daytime sleepiness."""
        return self.total_score > 10


@dataclass(slots=True, frozen=True)
class SamnPerelliFatigueScale:
    """Samn-Perelli Fatigue Scale (7-point).

    Single-item self-report measure of current fatigue state.
    Widely used in aviation fatigue risk management.

    Reference: Samn SW, Perelli LP. USAF School of Aerospace Medicine, 1982.
    """

    rating: int  # 1-7
    assessment_datetime: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def __post_init__(self) -> None:
        """Validate rating is 1-7."""
        if not 1 <= self.rating <= 7:
            msg = f"Samn-Perelli rating must be 1-7, got {self.rating}"
            raise ValueError(msg)

    @property
    def interpretation(self) -> str:
        """Interpret Samn-Perelli rating."""
        interpretations = {
            1: "Fully alert, wide awake",
            2: "Very lively, responsive, but not at peak",
            3: "Okay, somewhat fresh",
            4: "A little tired, less than fresh",
            5: "Moderately tired, let down",
            6: "Extremely tired, very difficult to concentrate",
            7: "Completely exhausted, unable to function effectively",
        }
        return interpretations.get(self.rating, "Unknown")

    @property
    def risk_level(self) -> str:
        """Categorize fatigue risk level for operational decisions."""
        if self.rating <= 2:
            return "LOW"
        if self.rating <= 4:
            return "MODERATE"
        if self.rating <= 5:
            return "HIGH"
        return "CRITICAL"


@dataclass(slots=True, frozen=True)
class KarolinskaSleeipinessScale:
    """Karolinska Sleepiness Scale (KSS) assessment.

    9-point scale for momentary sleepiness state.
    Validated against EEG and behavioral measures.

    Reference: Åkerstedt T, Gillberg M. Int J Neurosci. 1990;52(1-2):29-37.
    """

    rating: int  # 1-9
    assessment_datetime: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def __post_init__(self) -> None:
        """Validate rating is 1-9."""
        if not 1 <= self.rating <= 9:
            msg = f"KSS rating must be 1-9, got {self.rating}"
            raise ValueError(msg)

    @property
    def interpretation(self) -> str:
        """Interpret KSS rating."""
        interpretations = {
            1: "Extremely alert",
            2: "Very alert",
            3: "Alert",
            4: "Fairly alert",
            5: "Neither alert nor sleepy",
            6: "Some signs of sleepiness",
            7: "Sleepy, but no effort to stay awake",
            8: "Sleepy, some effort to stay awake",
            9: "Extremely sleepy, fighting sleep",
        }
        return interpretations.get(self.rating, "Unknown")

    @property
    def is_impaired(self) -> bool:
        """Check if sleepiness level indicates impairment (KSS >= 7)."""
        return self.rating >= 7


@dataclass(slots=True, frozen=True)
class StanfordSleepinessScale:
    """Stanford Sleepiness Scale (SSS) assessment.

    7-point scale for momentary sleepiness.

    Reference: Hoddes E, et al. Psychophysiology. 1973;10(4):431-436.
    """

    rating: int  # 1-7
    assessment_datetime: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def __post_init__(self) -> None:
        """Validate rating is 1-7."""
        if not 1 <= self.rating <= 7:
            msg = f"SSS rating must be 1-7, got {self.rating}"
            raise ValueError(msg)

    @property
    def interpretation(self) -> str:
        """Interpret SSS rating."""
        interpretations = {
            1: "Feeling active and vital; alert; wide awake",
            2: "Functioning at high level but not at peak; able to concentrate",
            3: "Relaxed; awake; not at full alertness; responsive",
            4: "A little foggy; not at peak; let down",
            5: "Fogginess; beginning to lose interest; slowed down",
            6: "Sleepiness; prefer to be lying down; woozy",
            7: "Almost in reverie; sleep onset soon; lost struggle to remain awake",
        }
        return interpretations.get(self.rating, "Unknown")


@dataclass(slots=True, frozen=True)
class FatigueSeverityScale:
    """Fatigue Severity Scale (FSS) assessment.

    9-item scale measuring impact of fatigue on daily functioning.
    Each item rated 1-7. Mean score ≥4 indicates significant fatigue.

    Reference: Krupp LB, et al. Arch Neurol. 1989;46(10):1121-1123.
    """

    item1_motivation: int  # 1-7
    item2_exercise: int  # 1-7
    item3_easily_fatigued: int  # 1-7
    item4_physical_functioning: int  # 1-7
    item5_frequent_problems: int  # 1-7
    item6_physical_activities: int  # 1-7
    item7_work_duties: int  # 1-7
    item8_most_disabling: int  # 1-7
    item9_interferes_life: int  # 1-7
    assessment_date: date = field(default_factory=date.today)

    @property
    def total_score(self) -> int:
        """Calculate total FSS score (9-63)."""
        return (
            self.item1_motivation
            + self.item2_exercise
            + self.item3_easily_fatigued
            + self.item4_physical_functioning
            + self.item5_frequent_problems
            + self.item6_physical_activities
            + self.item7_work_duties
            + self.item8_most_disabling
            + self.item9_interferes_life
        )

    @property
    def mean_score(self) -> float:
        """Calculate mean FSS score (1-7)."""
        return self.total_score / 9.0

    @property
    def interpretation(self) -> str:
        """Interpret FSS mean score."""
        mean = self.mean_score
        if mean < 3:
            return "No significant fatigue"
        if mean < 4:
            return "Mild fatigue impact"
        if mean < 5:
            return "Moderate fatigue impact"
        return "Severe fatigue impact"

    @property
    def has_significant_fatigue(self) -> bool:
        """Check if FSS indicates significant fatigue (mean ≥ 4)."""
        return self.mean_score >= 4.0


@dataclass(slots=True)
class PittsburghSleepQualityIndex:
    """Pittsburgh Sleep Quality Index (PSQI) assessment.

    19 self-rated questions generating 7 component scores.
    Global score 0-21; >5 indicates poor sleep quality.

    Reference: Buysse DJ, et al. Psychiatry Res. 1989;28(2):193-213.
    """

    # Component 1: Subjective sleep quality (0-3)
    subjective_quality: int  # Question 9

    # Component 2: Sleep latency (0-3)
    sleep_latency_minutes: int  # Question 2
    cannot_sleep_30min_frequency: int  # Question 5a (0-3)

    # Component 3: Sleep duration (0-3)
    hours_of_sleep: float  # Question 4

    # Component 4: Habitual sleep efficiency (0-3)
    bedtime_hour: int  # Question 1
    wake_time_hour: int  # Question 3
    # Efficiency calculated from hours_of_sleep / time_in_bed

    # Component 5: Sleep disturbances (0-3)
    wake_middle_night: int  # 5b (0-3)
    bathroom_frequency: int  # 5c (0-3)
    breathing_difficulty: int  # 5d (0-3)
    cough_snore: int  # 5e (0-3)
    feel_cold: int  # 5f (0-3)
    feel_hot: int  # 5g (0-3)
    bad_dreams: int  # 5h (0-3)
    pain: int  # 5i (0-3)
    other_reasons: int  # 5j (0-3)

    # Component 6: Use of sleep medication (0-3)
    sleep_medication_frequency: int  # Question 6 (0-3)

    # Component 7: Daytime dysfunction (0-3)
    trouble_staying_awake: int  # Question 7 (0-3)
    enthusiasm_problem: int  # Question 8 (0-3)

    assessment_date: date = field(default_factory=date.today)

    @property
    def component1_quality(self) -> int:
        """Component 1: Subjective sleep quality."""
        return min(3, self.subjective_quality)

    @property
    def component2_latency(self) -> int:
        """Component 2: Sleep latency score."""
        q2_score = 0
        if self.sleep_latency_minutes <= 15:
            q2_score = 0
        elif self.sleep_latency_minutes <= 30:
            q2_score = 1
        elif self.sleep_latency_minutes <= 60:
            q2_score = 2
        else:
            q2_score = 3

        sum_score = q2_score + self.cannot_sleep_30min_frequency
        if sum_score == 0:
            return 0
        if sum_score <= 2:
            return 1
        if sum_score <= 4:
            return 2
        return 3

    @property
    def component3_duration(self) -> int:
        """Component 3: Sleep duration score."""
        if self.hours_of_sleep > 7:
            return 0
        if self.hours_of_sleep >= 6:
            return 1
        if self.hours_of_sleep >= 5:
            return 2
        return 3

    @property
    def component4_efficiency(self) -> int:
        """Component 4: Habitual sleep efficiency score."""
        time_in_bed = (self.wake_time_hour - self.bedtime_hour) % 24
        if time_in_bed <= 0:
            time_in_bed = 8  # Default assumption
        efficiency = (self.hours_of_sleep / time_in_bed) * 100
        if efficiency >= 85:
            return 0
        if efficiency >= 75:
            return 1
        if efficiency >= 65:
            return 2
        return 3

    @property
    def component5_disturbances(self) -> int:
        """Component 5: Sleep disturbances score."""
        total = (
            self.wake_middle_night
            + self.bathroom_frequency
            + self.breathing_difficulty
            + self.cough_snore
            + self.feel_cold
            + self.feel_hot
            + self.bad_dreams
            + self.pain
            + self.other_reasons
        )
        if total == 0:
            return 0
        if total <= 9:
            return 1
        if total <= 18:
            return 2
        return 3

    @property
    def component6_medication(self) -> int:
        """Component 6: Use of sleep medication score."""
        return min(3, self.sleep_medication_frequency)

    @property
    def component7_dysfunction(self) -> int:
        """Component 7: Daytime dysfunction score."""
        sum_score = self.trouble_staying_awake + self.enthusiasm_problem
        if sum_score == 0:
            return 0
        if sum_score <= 2:
            return 1
        if sum_score <= 4:
            return 2
        return 3

    @property
    def global_score(self) -> int:
        """Calculate global PSQI score (0-21)."""
        return (
            self.component1_quality
            + self.component2_latency
            + self.component3_duration
            + self.component4_efficiency
            + self.component5_disturbances
            + self.component6_medication
            + self.component7_dysfunction
        )

    @property
    def interpretation(self) -> str:
        """Interpret global PSQI score."""
        score = self.global_score
        if score <= 5:
            return "Good sleep quality"
        if score <= 10:
            return "Poor sleep quality"
        if score <= 15:
            return "Moderate sleep disturbance"
        return "Severe sleep disturbance"

    @property
    def has_poor_sleep(self) -> bool:
        """Check if PSQI indicates poor sleep quality (>5)."""
        return self.global_score > 5


# ---------------------------------------------------------------------------
# User Profile Data Class
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class UserBiometricProfile:
    """Comprehensive user biometric profile for physiological calculations.

    All measurements in metric system per user requirements.
    """

    # Identity
    user_id: str
    name: str
    date_of_birth: date | None = None
    sex: Sex = Sex.OTHER
    occupation: OccupationType = OccupationType.OTHER

    # Anthropometrics
    height_cm: float | None = None  # Height in centimeters
    weight_kg: float | None = None  # Weight in kilograms

    # Fitness
    resting_heart_rate_bpm: float | None = None
    measured_vo2max_ml_kg_min: float | None = None  # If measured directly
    activity_level: ActivityLevel = ActivityLevel.MODERATELY_ACTIVE

    # Chronotype
    chronotype: ChronotypeCategory = ChronotypeCategory.NEITHER
    chronotype_offset_hours: float = 0.0  # Phase shift for circadian model

    # Health conditions affecting HRV
    has_hypertension: bool = False
    has_diabetes: bool = False
    has_cardiac_condition: bool = False
    takes_beta_blockers: bool = False
    is_smoker: bool = False
    caffeine_intake_cups_per_day: int = 0

    # Contact
    email: str = ""
    notes: str = ""

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    @property
    def age_years(self) -> int | None:
        """Calculate age in years from date of birth."""
        if self.date_of_birth is None:
            return None
        today = date.today()
        age = today.year - self.date_of_birth.year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            age -= 1
        return age

    @property
    def bmi(self) -> float | None:
        """Calculate Body Mass Index (kg/m²).

        Formula: BMI = weight_kg / (height_m)²
        Classification (WHO):
        - <18.5: Underweight
        - 18.5-24.9: Normal weight
        - 25.0-29.9: Overweight
        - ≥30.0: Obese
        """
        if self.height_cm is None or self.weight_kg is None:
            return None
        if self.height_cm <= 0 or self.weight_kg <= 0:
            return None
        height_m = self.height_cm / 100.0
        return self.weight_kg / (height_m * height_m)

    @property
    def bmi_category(self) -> str:
        """Categorize BMI according to WHO classification."""
        bmi_val = self.bmi
        if bmi_val is None:
            return "Unknown"
        if bmi_val < 18.5:
            return "Underweight"
        if bmi_val < 25.0:
            return "Normal weight"
        if bmi_val < 30.0:
            return "Overweight"
        if bmi_val < 35.0:
            return "Obese Class I"
        if bmi_val < 40.0:
            return "Obese Class II"
        return "Obese Class III"

    @property
    def estimated_vo2max(self) -> float | None:
        """Estimate VO2max if not directly measured.

        Uses age-predicted maximum heart rate and resting HR.
        Jackson et al. non-exercise VO2max prediction equation.

        Reference: Jackson AS, et al. Med Sci Sports Exerc. 1990;22(6):863-870.
        """
        if self.measured_vo2max_ml_kg_min is not None:
            return self.measured_vo2max_ml_kg_min

        age = self.age_years
        if age is None:
            return None

        # Non-exercise VO2max estimation (Jackson et al.)
        # VO2max = 56.363 + (1.921 * PA) - (0.381 * age) - (0.754 * BMI) + (10.987 * sex)
        # where sex = 1 for male, 0 for female, PA = 0-7 activity rating

        bmi_val = self.bmi
        if bmi_val is None:
            bmi_val = 25.0  # Assume average if unknown

        sex_factor = 1.0 if self.sex == Sex.MALE else 0.0 if self.sex == Sex.FEMALE else 0.5
        pa_rating = float(self.activity_level) * 1.4  # Map 1-5 to ~1.4-7

        vo2max = 56.363 + (1.921 * pa_rating) - (0.381 * age) - (0.754 * bmi_val) + (10.987 * sex_factor)
        return max(10.0, min(80.0, vo2max))

    @property
    def vo2max(self) -> float | None:
        """Get VO2max (measured or estimated)."""
        if self.measured_vo2max_ml_kg_min is not None:
            return self.measured_vo2max_ml_kg_min
        return self.estimated_vo2max

    @property
    def vo2max_percentile(self) -> int | None:
        """Calculate VO2max percentile for age and sex.

        Based on ACSM normative data.
        """
        vo2 = self.vo2max
        age = self.age_years
        if vo2 is None or age is None:
            return None

        # Simplified percentile ranges (ACSM Guidelines, 11th ed.)
        # These are approximate for illustrative purposes
        if self.sex == Sex.MALE:
            if age < 30:
                if vo2 >= 55:
                    return 95
                if vo2 >= 50:
                    return 80
                if vo2 >= 43:
                    return 50
                if vo2 >= 37:
                    return 20
                return 5
            if age < 40:
                if vo2 >= 52:
                    return 95
                if vo2 >= 47:
                    return 80
                if vo2 >= 40:
                    return 50
                if vo2 >= 34:
                    return 20
                return 5
            if age < 50:
                if vo2 >= 49:
                    return 95
                if vo2 >= 43:
                    return 80
                if vo2 >= 36:
                    return 50
                if vo2 >= 31:
                    return 20
                return 5
            # 50+
            if vo2 >= 43:
                return 95
            if vo2 >= 38:
                return 80
            if vo2 >= 32:
                return 50
            if vo2 >= 26:
                return 20
            return 5
        else:  # Female or Other
            if age < 30:
                if vo2 >= 49:
                    return 95
                if vo2 >= 43:
                    return 80
                if vo2 >= 36:
                    return 50
                if vo2 >= 30:
                    return 20
                return 5
            if age < 40:
                if vo2 >= 46:
                    return 95
                if vo2 >= 40:
                    return 80
                if vo2 >= 33:
                    return 50
                if vo2 >= 27:
                    return 20
                return 5
            if age < 50:
                if vo2 >= 42:
                    return 95
                if vo2 >= 36:
                    return 80
                if vo2 >= 29:
                    return 50
                if vo2 >= 24:
                    return 20
                return 5
            # 50+
            if vo2 >= 37:
                return 95
            if vo2 >= 32:
                return 80
            if vo2 >= 25:
                return 50
            if vo2 >= 20:
                return 20
            return 5

    @property
    def max_heart_rate_predicted(self) -> int | None:
        """Calculate age-predicted maximum heart rate.

        Uses Tanaka formula (more accurate than 220-age):
        HRmax = 208 - (0.7 × age)

        Reference: Tanaka H, et al. J Am Coll Cardiol. 2001;37(1):153-156.
        """
        age = self.age_years
        if age is None:
            return None
        return int(208 - (0.7 * age))

    @property
    def heart_rate_reserve(self) -> int | None:
        """Calculate heart rate reserve (HRmax - HRrest)."""
        hr_max = self.max_heart_rate_predicted
        if hr_max is None or self.resting_heart_rate_bpm is None:
            return None
        return int(hr_max - self.resting_heart_rate_bpm)

    def get_age_group(self) -> str:
        """Get age group for normative HRV comparisons."""
        age = self.age_years
        if age is None:
            return "unknown"
        if age < 26:
            return "18-25"
        if age < 36:
            return "26-35"
        if age < 46:
            return "36-45"
        if age < 56:
            return "46-55"
        if age < 66:
            return "56-65"
        return "65+"

    def get_rmssd_percentile(self, rmssd_ms: float) -> float | None:
        """Calculate RMSSD percentile relative to age/sex norms.

        Based on Nunan et al. 2010 normative data.
        """
        age_group = self.get_age_group()
        if age_group == "unknown" or age_group not in _RMSSD_NORMS:
            return None

        norms = _RMSSD_NORMS[age_group]
        sex_key = "male" if self.sex == Sex.MALE else "female"
        mean = norms[f"{sex_key}_mean"]
        sd = norms[f"{sex_key}_sd"]

        # Calculate z-score and convert to percentile
        z_score = (rmssd_ms - mean) / sd
        # Use standard normal CDF approximation
        percentile = 0.5 * (1 + math.erf(z_score / math.sqrt(2)))
        return percentile * 100

    def get_hrv_adjustment_factor(self) -> float:
        """Get adjustment factor for HRV interpretation based on profile.

        Accounts for factors that systematically affect HRV.
        """
        factor = 1.0

        # Age adjustment (HRV decreases ~3-4% per decade)
        age = self.age_years
        if age is not None:
            age_factor = 1.0 - ((age - 30) * 0.003) if age > 30 else 1.0
            factor *= max(0.7, min(1.0, age_factor))

        # Fitness adjustment (higher fitness = higher HRV baseline)
        vo2 = self.vo2max
        if vo2 is not None:
            if vo2 > 50:
                factor *= 1.15
            elif vo2 > 40:
                factor *= 1.05

        # Medical conditions
        if self.takes_beta_blockers:
            factor *= 1.3  # Beta blockers increase HRV
        if self.has_cardiac_condition:
            factor *= 0.85
        if self.has_diabetes:
            factor *= 0.9

        return factor

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "sex": self.sex.value,
            "occupation": self.occupation.value,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "resting_heart_rate_bpm": self.resting_heart_rate_bpm,
            "measured_vo2max_ml_kg_min": self.measured_vo2max_ml_kg_min,
            "activity_level": int(self.activity_level),
            "chronotype": self.chronotype.value,
            "chronotype_offset_hours": self.chronotype_offset_hours,
            "has_hypertension": self.has_hypertension,
            "has_diabetes": self.has_diabetes,
            "has_cardiac_condition": self.has_cardiac_condition,
            "takes_beta_blockers": self.takes_beta_blockers,
            "is_smoker": self.is_smoker,
            "caffeine_intake_cups_per_day": self.caffeine_intake_cups_per_day,
            "email": self.email,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            # Computed properties
            "age_years": self.age_years,
            "bmi": self.bmi,
            "bmi_category": self.bmi_category,
            "vo2max": self.vo2max,
            "vo2max_percentile": self.vo2max_percentile,
            "max_heart_rate_predicted": self.max_heart_rate_predicted,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserBiometricProfile":
        """Create from dictionary."""
        return cls(
            user_id=data["user_id"],
            name=data.get("name", ""),
            date_of_birth=date.fromisoformat(data["date_of_birth"]) if data.get("date_of_birth") else None,
            sex=Sex(data.get("sex", "other")),
            occupation=OccupationType(data.get("occupation", "other")),
            height_cm=data.get("height_cm"),
            weight_kg=data.get("weight_kg"),
            resting_heart_rate_bpm=data.get("resting_heart_rate_bpm"),
            measured_vo2max_ml_kg_min=data.get("measured_vo2max_ml_kg_min"),
            activity_level=ActivityLevel(data.get("activity_level", 3)),
            chronotype=ChronotypeCategory(data.get("chronotype", "neither")),
            chronotype_offset_hours=data.get("chronotype_offset_hours", 0.0),
            has_hypertension=data.get("has_hypertension", False),
            has_diabetes=data.get("has_diabetes", False),
            has_cardiac_condition=data.get("has_cardiac_condition", False),
            takes_beta_blockers=data.get("takes_beta_blockers", False),
            is_smoker=data.get("is_smoker", False),
            caffeine_intake_cups_per_day=data.get("caffeine_intake_cups_per_day", 0),
            email=data.get("email", ""),
            notes=data.get("notes", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(tz=timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(tz=timezone.utc),
        )


# ---------------------------------------------------------------------------
# Composite Assessment Session
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ClinicalAssessmentSession:
    """Container for a complete clinical assessment session.

    Groups multiple validated scales taken at the same time.
    """

    session_id: str
    user_id: str
    assessment_datetime: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    # Optional scale assessments
    epworth: EpworthSleepinessScale | None = None
    samn_perelli: SamnPerelliFatigueScale | None = None
    kss: KarolinskaSleeipinessScale | None = None
    sss: StanfordSleepinessScale | None = None
    fss: FatigueSeverityScale | None = None
    psqi: PittsburghSleepQualityIndex | None = None

    # Contextual data
    hours_since_wake: float | None = None
    hours_of_sleep_last_night: float | None = None
    caffeine_intake_today_cups: int = 0
    notes: str = ""

    @property
    def composite_fatigue_score(self) -> float | None:
        """Calculate composite fatigue score (0-100) from available scales.

        Normalizes and weights available scale scores.
        Higher score = more fatigue.
        """
        scores: list[float] = []
        weights: list[float] = []

        if self.samn_perelli is not None:
            # Normalize 1-7 to 0-100
            score = ((self.samn_perelli.rating - 1) / 6.0) * 100
            scores.append(score)
            weights.append(1.5)  # High weight for operational fatigue

        if self.kss is not None:
            # Normalize 1-9 to 0-100
            score = ((self.kss.rating - 1) / 8.0) * 100
            scores.append(score)
            weights.append(1.2)

        if self.sss is not None:
            # Normalize 1-7 to 0-100
            score = ((self.sss.rating - 1) / 6.0) * 100
            scores.append(score)
            weights.append(1.0)

        if self.fss is not None:
            # Normalize mean 1-7 to 0-100
            score = ((self.fss.mean_score - 1) / 6.0) * 100
            scores.append(score)
            weights.append(1.0)

        if self.epworth is not None:
            # Normalize 0-24 to 0-100
            score = (self.epworth.total_score / 24.0) * 100
            scores.append(score)
            weights.append(0.8)  # Lower weight - measures trait not state

        if not scores:
            return None

        # Weighted average
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        total_weight = sum(weights)
        return weighted_sum / total_weight

    @property
    def operational_risk_level(self) -> str:
        """Determine operational risk level based on assessments.

        Returns:
            Risk level: LOW, MODERATE, HIGH, or CRITICAL
        """
        # Check individual critical thresholds
        if self.samn_perelli is not None and self.samn_perelli.rating >= 6:
            return "CRITICAL"
        if self.kss is not None and self.kss.rating >= 8:
            return "CRITICAL"

        # Check composite score
        composite = self.composite_fatigue_score
        if composite is not None:
            if composite >= 75:
                return "CRITICAL"
            if composite >= 55:
                return "HIGH"
            if composite >= 35:
                return "MODERATE"
            return "LOW"

        # Default based on available data
        if self.samn_perelli is not None:
            return self.samn_perelli.risk_level
        if self.kss is not None and self.kss.is_impaired:
            return "HIGH"

        return "UNKNOWN"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "assessment_datetime": self.assessment_datetime.isoformat(),
            "epworth": asdict(self.epworth) if self.epworth else None,
            "samn_perelli": asdict(self.samn_perelli) if self.samn_perelli else None,
            "kss": asdict(self.kss) if self.kss else None,
            "sss": asdict(self.sss) if self.sss else None,
            "fss": asdict(self.fss) if self.fss else None,
            "psqi": asdict(self.psqi) if self.psqi else None,
            "hours_since_wake": self.hours_since_wake,
            "hours_of_sleep_last_night": self.hours_of_sleep_last_night,
            "caffeine_intake_today_cups": self.caffeine_intake_today_cups,
            "notes": self.notes,
            "composite_fatigue_score": self.composite_fatigue_score,
            "operational_risk_level": self.operational_risk_level,
        }


# ---------------------------------------------------------------------------
# Profile Manager
# ---------------------------------------------------------------------------


class UserProfileManager:
    """Manager for user profiles and clinical assessments."""

    def __init__(self, data_path: Path | None = None) -> None:
        """Initialize profile manager.

        Args:
            data_path: Base path for data storage (default: ./data).
        """
        self._data_path = data_path or Path("data")
        self._profiles_dir = self._data_path / "profiles"
        self._assessments_dir = self._data_path / "assessments"

        # Create directories
        self._profiles_dir.mkdir(parents=True, exist_ok=True)
        self._assessments_dir.mkdir(parents=True, exist_ok=True)

    def save_profile(self, profile: UserBiometricProfile) -> Path:
        """Save user profile to disk.

        Args:
            profile: User biometric profile.

        Returns:
            Path to saved profile file.
        """
        profile.updated_at = datetime.now(tz=timezone.utc)
        file_path = self._profiles_dir / f"{profile.user_id}_profile.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2, default=str)

        _LOGGER.info("Saved profile: %s", file_path)
        return file_path

    def load_profile(self, user_id: str) -> UserBiometricProfile | None:
        """Load user profile from disk.

        Args:
            user_id: User identifier.

        Returns:
            UserBiometricProfile or None if not found.
        """
        file_path = self._profiles_dir / f"{user_id}_profile.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            return UserBiometricProfile.from_dict(data)
        except Exception as exc:
            _LOGGER.warning("Failed to load profile %s: %s", user_id, exc)
            return None

    def save_assessment(self, assessment: ClinicalAssessmentSession) -> Path:
        """Save clinical assessment session.

        Args:
            assessment: Clinical assessment session.

        Returns:
            Path to saved assessment file.
        """
        user_dir = self._assessments_dir / assessment.user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        timestamp = assessment.assessment_datetime.strftime("%Y%m%d_%H%M%S")
        file_path = user_dir / f"{timestamp}_{assessment.session_id}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(assessment.to_dict(), f, indent=2, default=str)

        _LOGGER.info("Saved assessment: %s", file_path)
        return file_path

    def load_assessments(
        self,
        user_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Load assessment history for a user.

        Args:
            user_id: User identifier.
            limit: Maximum assessments to return.

        Returns:
            List of assessment dictionaries, most recent first.
        """
        user_dir = self._assessments_dir / user_id

        if not user_dir.exists():
            return []

        assessments: list[dict[str, Any]] = []

        for file_path in sorted(user_dir.glob("*.json"), reverse=True):
            if len(assessments) >= limit:
                break
            try:
                with open(file_path, encoding="utf-8") as f:
                    assessments.append(json.load(f))
            except Exception as exc:
                _LOGGER.warning("Failed to load assessment %s: %s", file_path, exc)

        return assessments

    def list_users(self) -> list[str]:
        """List all user IDs with profiles.

        Returns:
            List of user IDs.
        """
        users: list[str] = []
        for file_path in self._profiles_dir.glob("*_profile.json"):
            user_id = file_path.stem.replace("_profile", "")
            users.append(user_id)
        return sorted(users)


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------


def create_profile_manager(data_path: str | Path | None = None) -> UserProfileManager:
    """Create a UserProfileManager instance.

    Args:
        data_path: Optional base path for data storage.

    Returns:
        Configured UserProfileManager.
    """
    return UserProfileManager(
        data_path=Path(data_path) if data_path else None
    )


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """Calculate BMI from weight and height.

    Args:
        weight_kg: Weight in kilograms.
        height_cm: Height in centimeters.

    Returns:
        BMI in kg/m².
    """
    if height_cm <= 0 or weight_kg <= 0:
        msg = "Weight and height must be positive"
        raise ValueError(msg)
    height_m = height_cm / 100.0
    return weight_kg / (height_m * height_m)


def estimate_vo2max_non_exercise(
    age: int,
    sex: Sex,
    bmi: float,
    activity_level: ActivityLevel,
) -> float:
    """Estimate VO2max without exercise test.

    Uses Jackson et al. non-exercise prediction equation.

    Args:
        age: Age in years.
        sex: Biological sex.
        bmi: Body Mass Index.
        activity_level: Physical activity level.

    Returns:
        Estimated VO2max in mL/kg/min.
    """
    sex_factor = 1.0 if sex == Sex.MALE else 0.0 if sex == Sex.FEMALE else 0.5
    pa_rating = float(activity_level) * 1.4

    vo2max = 56.363 + (1.921 * pa_rating) - (0.381 * age) - (0.754 * bmi) + (10.987 * sex_factor)
    return max(10.0, min(80.0, vo2max))

