"""Streamlit UI components for user profile and clinical assessments.

This module provides Streamlit widgets for:
- User profile creation and editing
- Biometric data input (height, weight, age, BMI calculation)
- Clinical scale questionnaires (ESS, Samn-Perelli, KSS, PSQI, FSS)
- Assessment history visualization
- Profile-adjusted HRV interpretation

Author: Dr. Diego Malpica, MD - Aerospace Medicine Specialist
National University of Colombia | Colombian Aerospace Force
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any, Final

import streamlit as st

from .user_profile import (
    UserBiometricProfile,
    UserProfileManager,
    ClinicalAssessmentSession,
    EpworthSleepinessScale,
    SamnPerelliFatigueScale,
    KarolinskaSleeipinessScale,
    StanfordSleepinessScale,
    FatigueSeverityScale,
    PittsburghSleepQualityIndex,
    Sex,
    ActivityLevel,
    ChronotypeCategory,
    OccupationType,
    calculate_bmi,
    create_profile_manager,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Session State Helpers
# ---------------------------------------------------------------------------


def _get_profile_manager() -> UserProfileManager:
    """Get or create profile manager from session state."""
    if "profile_manager" not in st.session_state:
        st.session_state.profile_manager = create_profile_manager()
    return st.session_state.profile_manager


def _get_current_profile() -> UserBiometricProfile | None:
    """Get current user profile from session state."""
    return st.session_state.get("current_profile")


def _set_current_profile(profile: UserBiometricProfile | None) -> None:
    """Set current user profile in session state."""
    st.session_state.current_profile = profile


# ---------------------------------------------------------------------------
# UI Components
# ---------------------------------------------------------------------------


def render_user_selector() -> str | None:
    """Render user selection dropdown.

    Returns:
        Selected user_id or None.
    """
    manager = _get_profile_manager()
    users = manager.list_users()

    if not users:
        st.info("No users found. Create a new profile below.")
        return None

    # Add option for new user
    options = ["➕ Create New User"] + users

    selected = st.selectbox(
        "Select User / Participant",
        options,
        key="user_selector",
        help="Select an existing user or create a new profile",
    )

    if selected == "➕ Create New User":
        return None

    return selected


def render_profile_form(existing_profile: UserBiometricProfile | None = None) -> UserBiometricProfile | None:
    """Render user profile form with biometric inputs.

    Args:
        existing_profile: Existing profile to edit, or None for new.

    Returns:
        Created/updated profile or None if cancelled.
    """
    st.subheader("👤 User Profile" if existing_profile is None else "✏️ Edit Profile")

    with st.form("profile_form", clear_on_submit=False):
        # Identity
        col1, col2 = st.columns(2)

        with col1:
            user_id = st.text_input(
                "User ID (Cedula/ID Number)",
                value=existing_profile.user_id if existing_profile else "",
                disabled=existing_profile is not None,
                help="Unique identifier - cannot be changed after creation",
            )

            name = st.text_input(
                "Full Name",
                value=existing_profile.name if existing_profile else "",
            )

            dob_value = existing_profile.date_of_birth if existing_profile else None
            date_of_birth = st.date_input(
                "Date of Birth",
                value=dob_value,
                min_value=date(1920, 1, 1),
                max_value=date.today(),
            )

        with col2:
            sex_options = [s.value for s in Sex]
            sex_index = sex_options.index(existing_profile.sex.value) if existing_profile else 2
            sex = st.selectbox(
                "Biological Sex",
                sex_options,
                index=sex_index,
                format_func=lambda x: x.capitalize(),
            )

            occupation_options = [o.value for o in OccupationType]
            occ_index = occupation_options.index(existing_profile.occupation.value) if existing_profile else 9
            occupation = st.selectbox(
                "Occupation Type",
                occupation_options,
                index=occ_index,
                format_func=lambda x: x.replace("_", " ").title(),
            )

            email = st.text_input(
                "Email (optional)",
                value=existing_profile.email if existing_profile else "",
            )

        st.markdown("---")
        st.markdown("### 📏 Anthropometrics")

        col1, col2, col3 = st.columns(3)

        with col1:
            height_cm = st.number_input(
                "Height (cm)",
                min_value=100.0,
                max_value=250.0,
                value=existing_profile.height_cm if existing_profile and existing_profile.height_cm else 170.0,
                step=0.5,
                help="Height in centimeters",
            )

        with col2:
            weight_kg = st.number_input(
                "Weight (kg)",
                min_value=30.0,
                max_value=300.0,
                value=existing_profile.weight_kg if existing_profile and existing_profile.weight_kg else 70.0,
                step=0.5,
                help="Weight in kilograms",
            )

        with col3:
            # Calculate and display BMI
            if height_cm > 0 and weight_kg > 0:
                bmi = calculate_bmi(weight_kg, height_cm)
                st.metric("BMI (calculated)", f"{bmi:.1f} kg/m²")

        st.markdown("---")
        st.markdown("### 💪 Fitness & Activity")

        col1, col2 = st.columns(2)

        with col1:
            rhr = st.number_input(
                "Resting Heart Rate (bpm)",
                min_value=30,
                max_value=120,
                value=int(existing_profile.resting_heart_rate_bpm) if existing_profile and existing_profile.resting_heart_rate_bpm else 65,
                help="Morning resting heart rate",
            )

            vo2max_measured = st.number_input(
                "Measured VO₂max (mL/kg/min, optional)",
                min_value=0.0,
                max_value=90.0,
                value=existing_profile.measured_vo2max_ml_kg_min if existing_profile and existing_profile.measured_vo2max_ml_kg_min else 0.0,
                step=0.5,
                help="Leave at 0 if not measured; will be estimated from other data",
            )

        with col2:
            activity_levels = [
                ("Sedentary (desk job, no exercise)", ActivityLevel.SEDENTARY),
                ("Lightly Active (1-3 days/week)", ActivityLevel.LIGHTLY_ACTIVE),
                ("Moderately Active (3-5 days/week)", ActivityLevel.MODERATELY_ACTIVE),
                ("Very Active (6-7 days/week)", ActivityLevel.VERY_ACTIVE),
                ("Extremely Active (athlete)", ActivityLevel.EXTREMELY_ACTIVE),
            ]
            activity_names = [a[0] for a in activity_levels]
            current_activity = existing_profile.activity_level if existing_profile else ActivityLevel.MODERATELY_ACTIVE
            activity_index = next(i for i, a in enumerate(activity_levels) if a[1] == current_activity)

            activity_selection = st.selectbox(
                "Physical Activity Level",
                activity_names,
                index=activity_index,
            )
            activity_level = activity_levels[activity_names.index(activity_selection)][1]

        st.markdown("---")
        st.markdown("### 🌙 Chronotype")

        chronotype_options = [
            ("Definite Morning Type (early bird)", ChronotypeCategory.DEFINITE_MORNING),
            ("Moderate Morning Type", ChronotypeCategory.MODERATE_MORNING),
            ("Neither Type (intermediate)", ChronotypeCategory.NEITHER),
            ("Moderate Evening Type", ChronotypeCategory.MODERATE_EVENING),
            ("Definite Evening Type (night owl)", ChronotypeCategory.DEFINITE_EVENING),
        ]
        chronotype_names = [c[0] for c in chronotype_options]
        current_chrono = existing_profile.chronotype if existing_profile else ChronotypeCategory.NEITHER
        chrono_index = next(i for i, c in enumerate(chronotype_options) if c[1] == current_chrono)

        chronotype_selection = st.selectbox(
            "Chronotype (Sleep Preference)",
            chronotype_names,
            index=chrono_index,
            help="Your natural sleep-wake preference",
        )
        chronotype = chronotype_options[chronotype_names.index(chronotype_selection)][1]

        st.markdown("---")
        st.markdown("### 🏥 Health Conditions")
        st.caption("These affect HRV interpretation and fatigue calculations")

        col1, col2 = st.columns(2)

        with col1:
            has_hypertension = st.checkbox(
                "Hypertension",
                value=existing_profile.has_hypertension if existing_profile else False,
            )
            has_diabetes = st.checkbox(
                "Diabetes",
                value=existing_profile.has_diabetes if existing_profile else False,
            )
            has_cardiac = st.checkbox(
                "Cardiac Condition",
                value=existing_profile.has_cardiac_condition if existing_profile else False,
            )

        with col2:
            takes_beta_blockers = st.checkbox(
                "Takes Beta Blockers",
                value=existing_profile.takes_beta_blockers if existing_profile else False,
            )
            is_smoker = st.checkbox(
                "Current Smoker",
                value=existing_profile.is_smoker if existing_profile else False,
            )
            caffeine = st.number_input(
                "Caffeine (cups/day)",
                min_value=0,
                max_value=20,
                value=existing_profile.caffeine_intake_cups_per_day if existing_profile else 2,
            )

        notes = st.text_area(
            "Notes",
            value=existing_profile.notes if existing_profile else "",
            help="Additional notes about the participant",
        )

        # Submit button
        submitted = st.form_submit_button(
            "💾 Save Profile",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            if not user_id:
                st.error("User ID is required")
                return None

            profile = UserBiometricProfile(
                user_id=user_id,
                name=name,
                date_of_birth=date_of_birth if date_of_birth else None,
                sex=Sex(sex),
                occupation=OccupationType(occupation),
                height_cm=height_cm,
                weight_kg=weight_kg,
                resting_heart_rate_bpm=float(rhr),
                measured_vo2max_ml_kg_min=vo2max_measured if vo2max_measured > 0 else None,
                activity_level=activity_level,
                chronotype=chronotype,
                has_hypertension=has_hypertension,
                has_diabetes=has_diabetes,
                has_cardiac_condition=has_cardiac,
                takes_beta_blockers=takes_beta_blockers,
                is_smoker=is_smoker,
                caffeine_intake_cups_per_day=caffeine,
                email=email,
                notes=notes,
            )

            # Save profile
            manager = _get_profile_manager()
            manager.save_profile(profile)
            _set_current_profile(profile)

            st.success(f"✅ Profile saved for {name}")
            return profile

    return existing_profile


def render_profile_summary(profile: UserBiometricProfile) -> None:
    """Render profile summary card."""
    st.markdown(f"### 👤 {profile.name}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        age = profile.age_years
        st.metric("Age", f"{age} years" if age else "N/A")

    with col2:
        bmi = profile.bmi
        st.metric("BMI", f"{bmi:.1f}" if bmi else "N/A", delta=profile.bmi_category if bmi else None)

    with col3:
        vo2 = profile.vo2max
        label = "VO₂max (measured)" if profile.measured_vo2max_ml_kg_min else "VO₂max (est.)"
        st.metric(label, f"{vo2:.1f}" if vo2 else "N/A")

    with col4:
        hrmax = profile.max_heart_rate_predicted
        st.metric("HR Max (pred.)", f"{hrmax} bpm" if hrmax else "N/A")


def render_samn_perelli_form() -> SamnPerelliFatigueScale | None:
    """Render Samn-Perelli Fatigue Scale quick assessment.

    Returns:
        Completed assessment or None.
    """
    st.markdown("### ⚡ Samn-Perelli Fatigue Scale")
    st.caption("Rate your current fatigue level (1 = Fully Alert, 7 = Exhausted)")

    descriptions = {
        1: "1 - Fully alert, wide awake",
        2: "2 - Very lively, responsive, but not at peak",
        3: "3 - Okay, somewhat fresh",
        4: "4 - A little tired, less than fresh",
        5: "5 - Moderately tired, let down",
        6: "6 - Extremely tired, very difficult to concentrate",
        7: "7 - Completely exhausted, unable to function effectively",
    }

    rating = st.radio(
        "Current fatigue level:",
        options=list(descriptions.keys()),
        format_func=lambda x: descriptions[x],
        horizontal=False,
        key="sp_rating",
    )

    if st.button("Submit Fatigue Rating", key="sp_submit"):
        assessment = SamnPerelliFatigueScale(rating=rating)
        st.success(f"✅ Recorded: {assessment.interpretation}")

        # Show risk level with color
        risk = assessment.risk_level
        colors = {"LOW": "green", "MODERATE": "orange", "HIGH": "red", "CRITICAL": "red"}
        st.markdown(f"**Operational Risk Level:** :{colors.get(risk, 'gray')}[{risk}]")

        return assessment

    return None


def render_kss_form() -> KarolinskaSleeipinessScale | None:
    """Render Karolinska Sleepiness Scale assessment.

    Returns:
        Completed assessment or None.
    """
    st.markdown("### 😴 Karolinska Sleepiness Scale")
    st.caption("Rate your current sleepiness level (1 = Extremely Alert, 9 = Extremely Sleepy)")

    descriptions = {
        1: "1 - Extremely alert",
        2: "2 - Very alert",
        3: "3 - Alert",
        4: "4 - Fairly alert",
        5: "5 - Neither alert nor sleepy",
        6: "6 - Some signs of sleepiness",
        7: "7 - Sleepy, but no effort to stay awake",
        8: "8 - Sleepy, some effort to stay awake",
        9: "9 - Extremely sleepy, fighting sleep",
    }

    rating = st.radio(
        "Current sleepiness level:",
        options=list(descriptions.keys()),
        format_func=lambda x: descriptions[x],
        horizontal=False,
        key="kss_rating",
    )

    if st.button("Submit Sleepiness Rating", key="kss_submit"):
        assessment = KarolinskaSleeipinessScale(rating=rating)
        st.success(f"✅ Recorded: {assessment.interpretation}")

        if assessment.is_impaired:
            st.warning("⚠️ Sleepiness level indicates potential impairment (KSS ≥ 7)")

        return assessment

    return None


def render_epworth_form() -> EpworthSleepinessScale | None:
    """Render Epworth Sleepiness Scale questionnaire.

    Returns:
        Completed assessment or None.
    """
    st.markdown("### 📋 Epworth Sleepiness Scale")
    st.caption("How likely are you to doze off in each situation? (0 = Never, 3 = High chance)")

    situations = [
        ("Sitting and reading", "sitting_reading"),
        ("Watching TV", "watching_tv"),
        ("Sitting inactive in a public place", "sitting_inactive_public"),
        ("As a passenger in a car for an hour", "passenger_car_hour"),
        ("Lying down to rest in the afternoon", "lying_down_afternoon"),
        ("Sitting and talking to someone", "sitting_talking"),
        ("Sitting quietly after lunch (no alcohol)", "sitting_quietly_after_lunch"),
        ("In a car, while stopped in traffic", "car_stopped_traffic"),
    ]

    options = ["0 - Never", "1 - Slight", "2 - Moderate", "3 - High"]

    with st.form("epworth_form"):
        responses: dict[str, int] = {}

        for desc, key in situations:
            val = st.selectbox(
                desc,
                options,
                key=f"ess_{key}",
            )
            responses[key] = int(val[0])

        submitted = st.form_submit_button("Submit ESS")

        if submitted:
            assessment = EpworthSleepinessScale(**responses)  # type: ignore[arg-type]
            st.success(f"✅ ESS Total Score: {assessment.total_score}/24")
            st.info(f"📊 {assessment.interpretation}")

            if assessment.is_excessive_sleepiness:
                st.warning("⚠️ Score > 10 indicates excessive daytime sleepiness. Consider clinical evaluation.")

            return assessment

    return None


def render_psqi_form() -> PittsburghSleepQualityIndex | None:
    """Render Pittsburgh Sleep Quality Index questionnaire.

    Returns:
        Completed assessment or None.
    """
    st.markdown("### 🛏️ Pittsburgh Sleep Quality Index")
    st.caption("Answer based on your sleep during the PAST MONTH")

    with st.form("psqi_form"):
        st.markdown("#### Sleep Timing")
        col1, col2 = st.columns(2)

        with col1:
            bedtime = st.number_input(
                "Usual bedtime (hour, 24h format)",
                min_value=0,
                max_value=23,
                value=23,
            )

        with col2:
            waketime = st.number_input(
                "Usual wake time (hour, 24h format)",
                min_value=0,
                max_value=23,
                value=7,
            )

        col1, col2 = st.columns(2)

        with col1:
            latency = st.number_input(
                "Minutes to fall asleep",
                min_value=0,
                max_value=240,
                value=15,
            )

        with col2:
            hours_sleep = st.number_input(
                "Hours of actual sleep",
                min_value=0.0,
                max_value=16.0,
                value=7.0,
                step=0.5,
            )

        st.markdown("#### Sleep Quality")
        quality = st.selectbox(
            "Overall sleep quality",
            ["Very good", "Fairly good", "Fairly bad", "Very bad"],
        )
        quality_score = ["Very good", "Fairly good", "Fairly bad", "Very bad"].index(quality)

        st.markdown("#### Sleep Disturbances")
        st.caption("How often during the past month...")

        freq_options = ["Not during past month", "Less than once/week", "1-2 times/week", "3+ times/week"]

        cannot_sleep = st.selectbox("Cannot get to sleep within 30 minutes", freq_options)
        wake_middle = st.selectbox("Wake up in the middle of the night or early morning", freq_options)
        bathroom = st.selectbox("Have to get up to use the bathroom", freq_options)
        breathing = st.selectbox("Cannot breathe comfortably", freq_options)
        cough = st.selectbox("Cough or snore loudly", freq_options)
        cold = st.selectbox("Feel too cold", freq_options)
        hot = st.selectbox("Feel too hot", freq_options)
        dreams = st.selectbox("Have bad dreams", freq_options)
        pain = st.selectbox("Have pain", freq_options)
        other = st.selectbox("Other reason(s)", freq_options)

        st.markdown("#### Medication & Daytime Function")
        medication = st.selectbox("Take sleep medication", freq_options)
        staying_awake = st.selectbox("Trouble staying awake during activities", freq_options)
        enthusiasm = st.selectbox("Problem keeping up enthusiasm for things", freq_options)

        submitted = st.form_submit_button("Calculate PSQI Score")

        if submitted:
            assessment = PittsburghSleepQualityIndex(
                subjective_quality=quality_score,
                sleep_latency_minutes=latency,
                cannot_sleep_30min_frequency=freq_options.index(cannot_sleep),
                hours_of_sleep=hours_sleep,
                bedtime_hour=bedtime,
                wake_time_hour=waketime,
                wake_middle_night=freq_options.index(wake_middle),
                bathroom_frequency=freq_options.index(bathroom),
                breathing_difficulty=freq_options.index(breathing),
                cough_snore=freq_options.index(cough),
                feel_cold=freq_options.index(cold),
                feel_hot=freq_options.index(hot),
                bad_dreams=freq_options.index(dreams),
                pain=freq_options.index(pain),
                other_reasons=freq_options.index(other),
                sleep_medication_frequency=freq_options.index(medication),
                trouble_staying_awake=freq_options.index(staying_awake),
                enthusiasm_problem=freq_options.index(enthusiasm),
            )

            st.success(f"✅ PSQI Global Score: {assessment.global_score}/21")
            st.info(f"📊 {assessment.interpretation}")

            if assessment.has_poor_sleep:
                st.warning("⚠️ Score > 5 indicates poor sleep quality. Consider sleep hygiene improvements or clinical evaluation.")

            # Show component scores
            with st.expander("Component Scores"):
                st.write(f"1. Subjective Quality: {assessment.component1_quality}")
                st.write(f"2. Sleep Latency: {assessment.component2_latency}")
                st.write(f"3. Sleep Duration: {assessment.component3_duration}")
                st.write(f"4. Sleep Efficiency: {assessment.component4_efficiency}")
                st.write(f"5. Sleep Disturbances: {assessment.component5_disturbances}")
                st.write(f"6. Sleep Medication: {assessment.component6_medication}")
                st.write(f"7. Daytime Dysfunction: {assessment.component7_dysfunction}")

            return assessment

    return None


def render_profile_tab() -> None:
    """Render the complete profile management tab."""
    st.header("👤 User Profile & Assessments")

    # User selection
    selected_user = render_user_selector()

    if selected_user:
        # Load existing profile
        manager = _get_profile_manager()
        profile = manager.load_profile(selected_user)
        _set_current_profile(profile)

        if profile:
            render_profile_summary(profile)

            tab1, tab2, tab3 = st.tabs(["Edit Profile", "Quick Assessments", "Full Questionnaires"])

            with tab1:
                render_profile_form(profile)

            with tab2:
                col1, col2 = st.columns(2)
                with col1:
                    render_samn_perelli_form()
                with col2:
                    render_kss_form()

            with tab3:
                st.markdown("---")
                render_epworth_form()
                st.markdown("---")
                render_psqi_form()
    else:
        # New user creation
        render_profile_form()


# ---------------------------------------------------------------------------
# Integration with HRV Analysis
# ---------------------------------------------------------------------------


def get_profile_adjusted_hrv_interpretation(
    rmssd_ms: float,
    profile: UserBiometricProfile | None,
) -> dict[str, Any]:
    """Get HRV interpretation adjusted for user profile.

    Args:
        rmssd_ms: Measured RMSSD in milliseconds.
        profile: User profile for context.

    Returns:
        Dictionary with interpretation details.
    """
    result: dict[str, Any] = {
        "rmssd_ms": rmssd_ms,
        "has_profile_context": profile is not None,
    }

    if profile is None:
        # Generic interpretation without profile
        if rmssd_ms < 20:
            result["status"] = "Low"
            result["description"] = "Below typical range; may indicate stress or reduced parasympathetic activity"
        elif rmssd_ms < 40:
            result["status"] = "Normal"
            result["description"] = "Within typical range for adults"
        else:
            result["status"] = "High"
            result["description"] = "Above typical range; suggests good parasympathetic tone"
        return result

    # Profile-adjusted interpretation
    percentile = profile.get_rmssd_percentile(rmssd_ms)
    adjustment = profile.get_hrv_adjustment_factor()
    adjusted_rmssd = rmssd_ms / adjustment

    result["age_years"] = profile.age_years
    result["sex"] = profile.sex.value
    result["adjustment_factor"] = adjustment
    result["adjusted_rmssd"] = adjusted_rmssd

    if percentile is not None:
        result["percentile"] = percentile

        if percentile < 20:
            result["status"] = "Below Expected"
            result["description"] = f"RMSSD is at the {percentile:.0f}th percentile for your age/sex group"
        elif percentile < 80:
            result["status"] = "Within Expected"
            result["description"] = f"RMSSD is at the {percentile:.0f}th percentile - normal for your demographic"
        else:
            result["status"] = "Above Expected"
            result["description"] = f"RMSSD at the {percentile:.0f}th percentile - excellent parasympathetic tone"
    else:
        # Fallback without percentile
        if adjusted_rmssd < 20:
            result["status"] = "Low"
            result["description"] = "Below typical range (adjusted for your profile)"
        elif adjusted_rmssd < 40:
            result["status"] = "Normal"
            result["description"] = "Within typical range (adjusted for your profile)"
        else:
            result["status"] = "High"
            result["description"] = "Above typical range (adjusted for your profile)"

    # Add health condition notes
    notes: list[str] = []
    if profile.takes_beta_blockers:
        notes.append("Beta-blocker use typically increases HRV")
    if profile.has_cardiac_condition:
        notes.append("Cardiac conditions may affect HRV baseline")
    if profile.is_smoker:
        notes.append("Smoking typically reduces HRV")

    if notes:
        result["profile_notes"] = notes

    return result

