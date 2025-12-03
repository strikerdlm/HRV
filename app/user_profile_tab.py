"""
User Profile Tab for HRV Analysis Suite.

Provides a centralized interface for:
- User registration and profile management
- Biometric data collection (age, weight, height, BMI)
- Clinical scale assessments (ESS, Samn-Perelli, KSS, PSQI, etc.)
- Historical data viewing and trends
- Data export/import

All data is stored in SQLite database with timestamped entries.

Author: AI Assistant
Version: 1.0.0
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, date, timezone, timedelta
from typing import Any, Dict, Final, List, Optional

import numpy as np
import pandas as pd
import streamlit as st

# Import database module
try:
    from user_database import (
        UserProfile,
        ClinicalScales,
        HRVMeasurement,
        UserDatabase,
        get_database,
    )
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

# Import profile module
try:
    from user_profile import (
        EpworthSleepinessScale,
        SamnPerelliFatigueScale,
        KarolinskaSleeipinessScale,
        StanfordSleepinessScale,
        FatigueSeverityScale,
        PittsburghSleepQualityIndex,
        UserBiometricProfile,
        ClinicalAssessmentSession,
        Sex,
        ActivityLevel,
        ChronotypeCategory,
        OccupationType,
    )
    PROFILE_MODULE_AVAILABLE = True
except ImportError:
    PROFILE_MODULE_AVAILABLE = False

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Session State Keys
# ---------------------------------------------------------------------------

_SESSION_CURRENT_USER = "current_user_profile"
_SESSION_USER_ID = "current_user_id"
_SESSION_SHOW_REGISTRATION = "show_registration_form"


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _get_current_user() -> Optional[UserProfile]:
    """Get currently logged-in user from session state."""
    return st.session_state.get(_SESSION_CURRENT_USER)


def _set_current_user(user: Optional[UserProfile]) -> None:
    """Set current user in session state."""
    st.session_state[_SESSION_CURRENT_USER] = user
    if user:
        st.session_state[_SESSION_USER_ID] = user.user_id


def _calculate_age(dob_str: Optional[str]) -> Optional[int]:
    """Calculate age from date of birth string (YYYY-MM-DD)."""
    if not dob_str:
        return None
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        today = date.today()
        age = today.year - dob.year
        if (today.month, today.day) < (dob.month, dob.day):
            age -= 1
        return age
    except ValueError:
        return None


def _calculate_bmi(height_cm: Optional[float], weight_kg: Optional[float]) -> Optional[float]:
    """Calculate BMI from height and weight."""
    if not height_cm or not weight_kg or height_cm <= 0:
        return None
    height_m = height_cm / 100.0
    return weight_kg / (height_m ** 2)


def _bmi_category(bmi: Optional[float]) -> str:
    """Get BMI category according to WHO classification."""
    if bmi is None:
        return "Unknown"
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25.0:
        return "Normal"
    if bmi < 30.0:
        return "Overweight"
    if bmi < 35.0:
        return "Obese I"
    if bmi < 40.0:
        return "Obese II"
    return "Obese III"


# ---------------------------------------------------------------------------
# User Registration Form
# ---------------------------------------------------------------------------


def _render_registration_form() -> Optional[UserProfile]:
    """Render new user registration form."""
    st.markdown("### 📝 New User Registration")
    
    with st.form("registration_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input(
                "Username *",
                max_chars=50,
                help="Unique identifier for login",
            )
            full_name = st.text_input(
                "Full Name *",
                max_chars=100,
            )
            email = st.text_input(
                "Email",
                max_chars=100,
            )
            password = st.text_input(
                "Password",
                type="password",
                help="Optional - for multi-user setups",
            )
        
        with col2:
            date_of_birth = st.date_input(
                "Date of Birth",
                value=date(1990, 1, 1),
                min_value=date(1920, 1, 1),
                max_value=date.today(),
            )
            sex = st.selectbox(
                "Biological Sex",
                options=["male", "female", "other"],
                index=0,
            )
            occupation = st.selectbox(
                "Occupation Type",
                options=[
                    "pilot", "atc", "flight_crew", "medical",
                    "shift_worker", "military", "driver", "researcher",
                    "office", "other"
                ],
                index=9,
                format_func=lambda x: x.replace("_", " ").title(),
            )
        
        st.markdown("#### 📏 Anthropometrics")
        col_h, col_w = st.columns(2)
        with col_h:
            height_cm = st.number_input(
                "Height (cm)",
                min_value=100.0,
                max_value=250.0,
                value=170.0,
                step=0.5,
            )
        with col_w:
            weight_kg = st.number_input(
                "Weight (kg)",
                min_value=30.0,
                max_value=300.0,
                value=70.0,
                step=0.5,
            )
        
        # Show calculated BMI
        bmi = _calculate_bmi(height_cm, weight_kg)
        if bmi:
            st.caption(f"**BMI**: {bmi:.1f} kg/m² ({_bmi_category(bmi)})")
        
        st.markdown("#### 💪 Fitness & Lifestyle")
        col_hr, col_vo2 = st.columns(2)
        with col_hr:
            resting_hr = st.number_input(
                "Resting Heart Rate (bpm)",
                min_value=30,
                max_value=120,
                value=65,
                step=1,
            )
        with col_vo2:
            vo2max = st.number_input(
                "VO2max (ml/kg/min)",
                min_value=0.0,
                max_value=90.0,
                value=0.0,
                step=0.5,
                help="Leave 0 if unknown - will be estimated",
            )
        
        activity_level = st.select_slider(
            "Activity Level",
            options=["Sedentary", "Light", "Moderate", "Active", "Very Active"],
            value="Moderate",
        )
        
        submit = st.form_submit_button("✅ Create Profile", use_container_width=True)
        
        if submit:
            if not username or not full_name:
                st.error("Username and Full Name are required.")
                return None
            
            # Create profile
            profile = UserProfile(
                user_id=str(uuid.uuid4()),
                username=username.lower().strip(),
                full_name=full_name.strip(),
                email=email.strip() if email else None,
                date_of_birth=date_of_birth.isoformat() if date_of_birth else None,
                sex=sex,
                height_cm=float(height_cm),
                weight_kg=float(weight_kg),
                resting_hr_bpm=float(resting_hr),
                max_hr_bpm=None,
                vo2max_ml_kg_min=float(vo2max) if vo2max > 0 else None,
                occupation=occupation,
                activity_level=activity_level.lower().replace(" ", "_"),
            )
            
            try:
                db = get_database()
                # Optimized: check and create in single transaction
                user_id, created = db.create_user_if_not_exists(
                    profile,
                    password if password else None,
                )
                
                if not created:
                    st.error(f"Username '{profile.username}' already exists.")
                    return None
                
                st.success(f"✅ Profile created for {full_name}!")
                return profile
                
            except Exception as exc:
                st.error(f"Failed to create profile: {exc}")
                return None
    
    return None


# ---------------------------------------------------------------------------
# User Login
# ---------------------------------------------------------------------------


def _render_login_section() -> Optional[UserProfile]:
    """Render user login/selection section."""
    db = get_database()
    users = db.list_users()
    
    if not users:
        st.info("No users registered. Create a new profile below.")
        return None
    
    st.markdown("### 🔑 Select or Login")
    
    col_select, col_action = st.columns([3, 1])
    
    with col_select:
        user_options = {u.username: u for u in users}
        selected_username = st.selectbox(
            "Select User",
            options=list(user_options.keys()),
            format_func=lambda x: f"{user_options[x].full_name} (@{x})",
        )
    
    with col_action:
        st.write("")  # Spacing
        if st.button("✅ Select User", use_container_width=True):
            user = user_options.get(selected_username)
            if user:
                _set_current_user(user)
                st.success(f"Logged in as {user.full_name}")
                st.rerun()
    
    return None


# ---------------------------------------------------------------------------
# Profile Display & Edit
# ---------------------------------------------------------------------------


def _render_profile_view(user: UserProfile) -> None:
    """Render user profile view with edit option."""
    
    st.markdown(f"### 👤 {user.full_name}")
    st.caption(f"@{user.username} • User ID: {user.user_id[:8]}...")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    age = _calculate_age(user.date_of_birth)
    with col1:
        st.metric("Age", f"{age} years" if age else "—")
    
    bmi = _calculate_bmi(user.height_cm, user.weight_kg)
    with col2:
        st.metric("BMI", f"{bmi:.1f}" if bmi else "—", _bmi_category(bmi) if bmi else None)
    
    with col3:
        st.metric("Resting HR", f"{user.resting_hr_bpm:.0f} bpm" if user.resting_hr_bpm else "—")
    
    with col4:
        # Estimated max HR using Tanaka formula
        max_hr = 208 - (0.7 * age) if age else None
        st.metric("Est. Max HR", f"{max_hr:.0f} bpm" if max_hr else "—")
    
    # Details expander
    with st.expander("📋 Full Profile Details"):
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("**Personal Information**")
            st.write(f"- **Sex**: {user.sex or '—'}")
            st.write(f"- **Date of Birth**: {user.date_of_birth or '—'}")
            st.write(f"- **Email**: {user.email or '—'}")
            st.write(f"- **Occupation**: {user.occupation or '—'}")
            
        with col_b:
            st.markdown("**Anthropometrics**")
            st.write(f"- **Height**: {user.height_cm:.1f} cm" if user.height_cm else "- **Height**: —")
            st.write(f"- **Weight**: {user.weight_kg:.1f} kg" if user.weight_kg else "- **Weight**: —")
            st.write(f"- **Activity Level**: {user.activity_level or '—'}")
            st.write(f"- **VO2max**: {user.vo2max_ml_kg_min:.1f} ml/kg/min" if user.vo2max_ml_kg_min else "- **VO2max**: —")
        
        st.markdown("---")
        st.caption(f"Created: {user.created_at[:10] if user.created_at else '—'} | Updated: {user.updated_at[:10] if user.updated_at else '—'}")
    
    # Edit profile button
    if st.button("✏️ Edit Profile"):
        st.session_state["edit_profile_mode"] = True
        st.rerun()


def _render_profile_edit(user: UserProfile) -> None:
    """Render profile edit form."""
    st.markdown("### ✏️ Edit Profile")
    
    with st.form("edit_profile_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input("Full Name", value=user.full_name or "")
            email = st.text_input("Email", value=user.email or "")
            
            # Parse date
            dob_value = date(1990, 1, 1)
            if user.date_of_birth:
                try:
                    dob_value = datetime.strptime(user.date_of_birth, "%Y-%m-%d").date()
                except ValueError:
                    pass
            
            date_of_birth = st.date_input("Date of Birth", value=dob_value)
            sex = st.selectbox(
                "Sex",
                options=["male", "female", "other"],
                index=["male", "female", "other"].index(user.sex) if user.sex in ["male", "female", "other"] else 0,
            )
        
        with col2:
            height_cm = st.number_input("Height (cm)", value=user.height_cm or 170.0, min_value=100.0, max_value=250.0)
            weight_kg = st.number_input("Weight (kg)", value=user.weight_kg or 70.0, min_value=30.0, max_value=300.0)
            resting_hr = st.number_input("Resting HR (bpm)", value=int(user.resting_hr_bpm or 65), min_value=30, max_value=120)
            vo2max = st.number_input(
                "VO2max (ml/kg/min)",
                value=user.vo2max_ml_kg_min or 0.0,
                min_value=0.0,
                max_value=90.0,
            )
        
        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.form_submit_button("💾 Save Changes", use_container_width=True):
                user.full_name = full_name
                user.email = email
                user.date_of_birth = date_of_birth.isoformat()
                user.sex = sex
                user.height_cm = height_cm
                user.weight_kg = weight_kg
                user.resting_hr_bpm = resting_hr
                user.vo2max_ml_kg_min = vo2max if vo2max > 0 else None
                
                try:
                    db = get_database()
                    db.update_user(user)
                    st.session_state["edit_profile_mode"] = False
                    st.success("Profile updated!")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Failed to update: {exc}")
        
        with col_cancel:
            if st.form_submit_button("❌ Cancel", use_container_width=True):
                st.session_state["edit_profile_mode"] = False
                st.rerun()


# ---------------------------------------------------------------------------
# Clinical Scales Forms
# ---------------------------------------------------------------------------


def _render_epworth_form(user_id: str) -> Optional[int]:
    """Render Epworth Sleepiness Scale form."""
    st.markdown("#### Epworth Sleepiness Scale (ESS)")
    st.caption("Rate your chance of dozing off in each situation (0-3)")
    
    situations = [
        ("sitting_reading", "Sitting and reading"),
        ("watching_tv", "Watching TV"),
        ("sitting_inactive_public", "Sitting inactive in a public place"),
        ("passenger_car_hour", "As a passenger in a car for an hour"),
        ("lying_down_afternoon", "Lying down to rest in the afternoon"),
        ("sitting_talking", "Sitting and talking to someone"),
        ("sitting_quietly_after_lunch", "Sitting quietly after lunch (no alcohol)"),
        ("car_stopped_traffic", "In a car, while stopped in traffic"),
    ]
    
    scores: Dict[str, int] = {}
    
    cols_per_row = 2
    for i in range(0, len(situations), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, (key, label) in enumerate(situations[i:i + cols_per_row]):
            with cols[j]:
                scores[key] = st.slider(
                    label,
                    min_value=0,
                    max_value=3,
                    value=0,
                    key=f"ess_{key}",
                    help="0 = Never doze, 3 = High chance of dozing",
                )
    
    total = sum(scores.values())
    
    # Interpretation
    if total <= 5:
        interp = "Lower normal daytime sleepiness"
        color = "green"
    elif total <= 10:
        interp = "Higher normal daytime sleepiness"
        color = "green"
    elif total <= 12:
        interp = "Mild excessive daytime sleepiness"
        color = "orange"
    elif total <= 15:
        interp = "Moderate excessive daytime sleepiness"
        color = "orange"
    else:
        interp = "Severe excessive daytime sleepiness"
        color = "red"
    
    st.markdown(f"**Total Score: {total}/24** — :{color}[{interp}]")
    
    if total > 10:
        st.warning("⚠️ Score >10 suggests excessive daytime sleepiness. Consider sleep evaluation.")
    
    return total


def _render_samn_perelli_form(user_id: str) -> Optional[int]:
    """Render Samn-Perelli Fatigue Scale form."""
    st.markdown("#### Samn-Perelli Fatigue Scale")
    st.caption("Select the statement that best describes your current state")
    
    options = {
        1: "1 - Fully alert, wide awake",
        2: "2 - Very lively, responsive, but not at peak",
        3: "3 - Okay, somewhat fresh",
        4: "4 - A little tired, less than fresh",
        5: "5 - Moderately tired, let down",
        6: "6 - Extremely tired, very difficult to concentrate",
        7: "7 - Completely exhausted, unable to function effectively",
    }
    
    rating = st.radio(
        "Current fatigue state:",
        options=list(options.keys()),
        format_func=lambda x: options[x],
        horizontal=False,
        key="samn_perelli_rating",
    )
    
    # Risk level
    if rating <= 2:
        risk = "LOW"
        color = "green"
    elif rating <= 4:
        risk = "MODERATE"
        color = "orange"
    elif rating <= 5:
        risk = "HIGH"
        color = "red"
    else:
        risk = "CRITICAL"
        color = "red"
    
    st.markdown(f"**Operational Risk Level: :{color}[{risk}]**")
    
    if rating >= 5:
        st.error("⚠️ Fatigue level may impair performance. Consider rest before safety-critical tasks.")
    
    return rating


def _render_kss_form(user_id: str) -> Optional[int]:
    """Render Karolinska Sleepiness Scale form."""
    st.markdown("#### Karolinska Sleepiness Scale (KSS)")
    st.caption("Rate your current sleepiness level")
    
    options = {
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
        "Current sleepiness:",
        options=list(options.keys()),
        format_func=lambda x: options[x],
        horizontal=False,
        key="kss_rating",
    )
    
    if rating >= 7:
        st.warning("⚠️ KSS ≥7 indicates significant sleepiness that may impair performance.")
    
    return rating


def _render_vas_scales(user_id: str) -> Dict[str, float]:
    """Render Visual Analog Scale assessments."""
    st.markdown("#### Visual Analog Scales (VAS)")
    st.caption("Rate your current state on a 0-10 scale")
    
    col1, col2 = st.columns(2)
    
    with col1:
        vas_fatigue = st.slider(
            "Fatigue (0 = None, 10 = Extreme)",
            min_value=0.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
            key="vas_fatigue",
        )
    
    with col2:
        vas_pain = st.slider(
            "Pain (0 = None, 10 = Worst)",
            min_value=0.0,
            max_value=10.0,
            value=0.0,
            step=0.5,
            key="vas_pain",
        )
    
    return {"vas_fatigue": vas_fatigue, "vas_pain": vas_pain}


# ---------------------------------------------------------------------------
# Clinical Assessment Session
# ---------------------------------------------------------------------------


def _render_clinical_assessment(user: UserProfile) -> None:
    """Render comprehensive clinical assessment section."""
    st.markdown("## 📊 Clinical Assessment")
    st.caption("Complete standardized scales for fatigue and sleep evaluation")
    
    # Context inputs
    with st.expander("⏰ Assessment Context", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            hours_since_wake = st.number_input(
                "Hours since waking",
                min_value=0.0,
                max_value=48.0,
                value=8.0,
                step=0.5,
            )
        with col2:
            hours_sleep = st.number_input(
                "Hours slept last night",
                min_value=0.0,
                max_value=24.0,
                value=7.0,
                step=0.5,
            )
        with col3:
            caffeine_cups = st.number_input(
                "Caffeine today (cups)",
                min_value=0,
                max_value=20,
                value=1,
                step=1,
            )
    
    # Scale selection
    available_scales = {
        "ESS": "Epworth Sleepiness Scale (trait measure)",
        "SP": "Samn-Perelli Fatigue Scale (state measure)",
        "KSS": "Karolinska Sleepiness Scale (state measure)",
        "VAS": "Visual Analog Scales (fatigue, pain)",
    }
    
    selected_scales = st.multiselect(
        "Select scales to complete:",
        options=list(available_scales.keys()),
        default=["SP", "KSS"],
        format_func=lambda x: f"{x}: {available_scales[x]}",
    )
    
    # Render selected scales
    results: Dict[str, Any] = {}
    
    if "ESS" in selected_scales:
        with st.expander("📋 Epworth Sleepiness Scale", expanded=True):
            results["ess"] = _render_epworth_form(user.user_id)
    
    if "SP" in selected_scales:
        with st.expander("📋 Samn-Perelli Fatigue Scale", expanded=True):
            results["samn_perelli"] = _render_samn_perelli_form(user.user_id)
    
    if "KSS" in selected_scales:
        with st.expander("📋 Karolinska Sleepiness Scale", expanded=True):
            results["kss"] = _render_kss_form(user.user_id)
    
    if "VAS" in selected_scales:
        with st.expander("📋 Visual Analog Scales", expanded=True):
            vas_results = _render_vas_scales(user.user_id)
            results.update(vas_results)
    
    # Notes
    notes = st.text_area(
        "Assessment Notes",
        placeholder="Optional notes about current conditions, activities, etc.",
        max_chars=500,
    )
    
    # Submit assessment
    if st.button("💾 Save Assessment", type="primary", use_container_width=True):
        try:
            db = get_database()
            
            scales = ClinicalScales(
                assessment_id=str(uuid.uuid4()),
                user_id=user.user_id,
                assessment_date=datetime.now(timezone.utc).isoformat(),
                epworth_sleepiness_scale=results.get("ess"),
                karolinska_sleepiness_scale=results.get("kss"),
                samn_perelli_fatigue=results.get("samn_perelli"),
                vas_fatigue=results.get("vas_fatigue"),
                vas_pain=results.get("vas_pain"),
                notes=f"Wake: {hours_since_wake}h, Sleep: {hours_sleep}h, Caffeine: {caffeine_cups} cups. {notes}",
            )
            
            db.save_clinical_scales(scales)
            st.success("✅ Assessment saved successfully!")
            st.balloons()
            
        except Exception as exc:
            st.error(f"Failed to save assessment: {exc}")


# ---------------------------------------------------------------------------
# Assessment History
# ---------------------------------------------------------------------------


def _render_assessment_history(user: UserProfile) -> None:
    """Render clinical assessment history."""
    st.markdown("## 📈 Assessment History")
    
    try:
        db = get_database()
        history = db.get_clinical_scales_history(user.user_id, limit=50)
        
        if not history:
            st.info("No assessment history found. Complete a clinical assessment to start tracking.")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame([h.to_dict() for h in history])
        df["assessment_date"] = pd.to_datetime(df["assessment_date"])
        df = df.sort_values("assessment_date", ascending=False)
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Assessments", len(df))
        with col2:
            if "samn_perelli_fatigue" in df.columns:
                mean_sp = df["samn_perelli_fatigue"].mean()
                st.metric("Avg Samn-Perelli", f"{mean_sp:.1f}" if pd.notna(mean_sp) else "—")
        with col3:
            if "karolinska_sleepiness_scale" in df.columns:
                mean_kss = df["karolinska_sleepiness_scale"].mean()
                st.metric("Avg KSS", f"{mean_kss:.1f}" if pd.notna(mean_kss) else "—")
        
        # Trend chart
        if len(df) > 1:
            chart_data = df[["assessment_date", "samn_perelli_fatigue", "karolinska_sleepiness_scale"]].dropna(how="all", subset=["samn_perelli_fatigue", "karolinska_sleepiness_scale"])
            if not chart_data.empty:
                chart_data = chart_data.set_index("assessment_date")
                st.line_chart(chart_data)
        
        # Data table
        with st.expander("📊 All Assessment Data"):
            display_cols = [
                "assessment_date",
                "epworth_sleepiness_scale",
                "samn_perelli_fatigue",
                "karolinska_sleepiness_scale",
                "vas_fatigue",
                "vas_pain",
                "notes",
            ]
            display_df = df[[c for c in display_cols if c in df.columns]]
            st.dataframe(display_df, use_container_width=True)
        
    except Exception as exc:
        st.error(f"Failed to load history: {exc}")


# ---------------------------------------------------------------------------
# HRV History Section
# ---------------------------------------------------------------------------


def _render_hrv_history(user: UserProfile) -> None:
    """Render HRV measurement history."""
    st.markdown("## 💓 HRV Measurement History")
    
    try:
        db = get_database()
        df = db.get_hrv_dataframe(user.user_id)
        
        if df.empty:
            st.info("No HRV measurements recorded. Import HRV data from the main analysis to populate this section.")
            return
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Recordings", len(df))
        with col2:
            if "rmssd_ms" in df.columns:
                st.metric("Avg RMSSD", f"{df['rmssd_ms'].mean():.1f} ms")
        with col3:
            if "sdnn_ms" in df.columns:
                st.metric("Avg SDNN", f"{df['sdnn_ms'].mean():.1f} ms")
        with col4:
            if "mean_hr_bpm" in df.columns:
                st.metric("Avg HR", f"{df['mean_hr_bpm'].mean():.0f} bpm")
        
        # Trend chart
        if len(df) > 1 and "measurement_date" in df.columns:
            chart_cols = ["rmssd_ms", "sdnn_ms"]
            available_cols = [c for c in chart_cols if c in df.columns]
            if available_cols:
                chart_data = df.set_index("measurement_date")[available_cols]
                st.line_chart(chart_data)
        
        # Full data table
        with st.expander("📊 All HRV Measurements"):
            st.dataframe(df, use_container_width=True)
        
    except Exception as exc:
        st.error(f"Failed to load HRV history: {exc}")


# ---------------------------------------------------------------------------
# Data Export/Import
# ---------------------------------------------------------------------------


def _render_data_management(user: UserProfile) -> None:
    """Render data export/import section."""
    st.markdown("## 📦 Data Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Export Data")
        if st.button("📥 Export All User Data", use_container_width=True):
            try:
                import json
                db = get_database()
                
                export_data = {
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "user_profile": user.to_dict(),
                    "clinical_scales": [s.to_dict() for s in db.get_clinical_scales_history(user.user_id)],
                    "hrv_measurements": [m.to_dict() for m in db.get_hrv_history(user.user_id)],
                }
                
                json_str = json.dumps(export_data, indent=2, default=str)
                st.download_button(
                    "💾 Download JSON",
                    data=json_str,
                    file_name=f"{user.username}_data_export.json",
                    mime="application/json",
                )
                
            except Exception as exc:
                st.error(f"Export failed: {exc}")
    
    with col2:
        st.markdown("### Account Actions")
        
        if st.button("🚪 Logout", use_container_width=True):
            _set_current_user(None)
            st.session_state.pop("edit_profile_mode", None)
            st.rerun()
        
        st.markdown("---")
        
        with st.expander("⚠️ Danger Zone"):
            st.warning("Deleting your account will remove all data permanently.")
            if st.button("🗑️ Delete Account", type="secondary"):
                st.session_state["confirm_delete"] = True
            
            if st.session_state.get("confirm_delete"):
                st.error("Are you sure? This cannot be undone.")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("Yes, Delete", type="primary"):
                        try:
                            db = get_database()
                            db.delete_user(user.user_id)
                            _set_current_user(None)
                            st.session_state.pop("confirm_delete", None)
                            st.success("Account deleted.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Delete failed: {exc}")
                with col_no:
                    if st.button("Cancel"):
                        st.session_state.pop("confirm_delete", None)
                        st.rerun()


# ---------------------------------------------------------------------------
# Main Tab Renderer
# ---------------------------------------------------------------------------


def render_user_profile_tab() -> None:
    """
    Render the complete User Profile tab.
    
    This is the main entry point for the tab.
    """
    st.header("👤 User Profile & Clinical Assessments")
    
    if not DATABASE_AVAILABLE:
        st.error(
            "User database module not available. "
            "Please ensure `user_database.py` is in the app directory."
        )
        return
    
    # Check current user
    current_user = _get_current_user()
    
    if current_user is None:
        # Show login/registration
        tab_login, tab_register = st.tabs(["🔑 Login", "📝 Register"])
        
        with tab_login:
            _render_login_section()
        
        with tab_register:
            new_user = _render_registration_form()
            if new_user:
                _set_current_user(new_user)
                st.rerun()
    else:
        # Show profile and assessments
        if st.session_state.get("edit_profile_mode"):
            _render_profile_edit(current_user)
        else:
            _render_profile_view(current_user)
        
        st.markdown("---")
        
        # Sub-tabs for different sections
        tab_assess, tab_history, tab_hrv, tab_data = st.tabs([
            "📋 New Assessment",
            "📈 Assessment History",
            "💓 HRV History",
            "📦 Data Management",
        ])
        
        with tab_assess:
            _render_clinical_assessment(current_user)
        
        with tab_history:
            _render_assessment_history(current_user)
        
        with tab_hrv:
            _render_hrv_history(current_user)
        
        with tab_data:
            _render_data_management(current_user)


# ---------------------------------------------------------------------------
# Convenience function for getting current user data
# ---------------------------------------------------------------------------


def get_current_user_data() -> Optional[Dict[str, Any]]:
    """
    Get current user's data for use by other modules.
    
    Returns:
        Dictionary with user profile data or None if not logged in.
    """
    user = _get_current_user()
    if user is None:
        return None
    
    return {
        "user_id": user.user_id,
        "username": user.username,
        "full_name": user.full_name,
        "age_years": _calculate_age(user.date_of_birth),
        "sex": user.sex,
        "height_cm": user.height_cm,
        "weight_kg": user.weight_kg,
        "bmi": _calculate_bmi(user.height_cm, user.weight_kg),
        "resting_hr_bpm": user.resting_hr_bpm,
        "max_hr_bpm": user.max_hr_bpm,
        "vo2max_ml_kg_min": user.vo2max_ml_kg_min,
        "activity_level": user.activity_level,
        "occupation": user.occupation,
    }


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    "render_user_profile_tab",
    "get_current_user_data",
]

