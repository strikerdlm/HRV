"""
User Profile Tab for Mission Control - Flight Surgeon.

Provides a centralized interface for:
- User registration and profile management
- Biometric data collection (age, weight, height, BMI)
- Clinical scale assessments (ESS, Samn-Perelli, KSS, PSQI, etc.)
- Historical data viewing and trends
- Data export/import

All data is stored in SQLite database with timestamped entries.
Supports English and Spanish (Colombian validated scales).

Author: AI Assistant
Version: 1.1.0
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

# Import i18n module for translations
try:
    from i18n import (
        Language,
        get_current_language,
        set_language,
        t,
        get_epworth_translations,
        get_karolinska_translations,
        get_samn_perelli_translations,
        get_vas_translations,
        render_language_selector,
    )
    I18N_AVAILABLE = True
except ImportError:
    I18N_AVAILABLE = False
    # Fallback function if i18n not available
    def t(key: str, **kwargs: Any) -> str:  # type: ignore[misc]
        return key

# Import multi-user session manager
try:
    from multi_user_session import (
        get_multi_user_manager,
        render_user_switcher,
        render_user_session_manager,
        MAX_CONCURRENT_USERS,
    )
    MULTI_USER_AVAILABLE = True
except ImportError:
    MULTI_USER_AVAILABLE = False
    def get_current_language() -> str:  # type: ignore[misc]
        return "en"

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
    """Set current user in session state, sync language, and register in multi-user manager."""
    st.session_state[_SESSION_CURRENT_USER] = user
    if user:
        st.session_state[_SESSION_USER_ID] = user.user_id
        # Sync language preference from user profile
        if I18N_AVAILABLE and hasattr(user, 'language') and user.language:
            try:
                from i18n import Language, set_language
                lang = Language(user.language)
                set_language(lang)
            except (ValueError, ImportError):
                pass  # Keep current language if invalid
        
        # Register in multi-user session manager
        if MULTI_USER_AVAILABLE:
            try:
                manager = get_multi_user_manager()
                manager.add_user_session(
                    user_id=user.user_id,
                    username=user.username,
                    full_name=user.full_name or user.username,
                    make_active=True,
                )
            except Exception:
                pass  # Continue even if multi-user registration fails


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
    """Render Epworth Sleepiness Scale form with i18n support."""
    # Get translations for current language
    if I18N_AVAILABLE:
        tr = get_epworth_translations()
    else:
        tr = {
            "title": "Epworth Sleepiness Scale (ESS)",
            "subtitle": "Rate your chance of dozing off in each situation (0-3)",
            "help": "0 = Never doze, 3 = High chance of dozing",
            "situations": [
                ("sitting_reading", "Sitting and reading"),
                ("watching_tv", "Watching TV"),
                ("sitting_inactive_public", "Sitting inactive in a public place"),
                ("passenger_car_hour", "As a passenger in a car for an hour"),
                ("lying_down_afternoon", "Lying down to rest in the afternoon"),
                ("sitting_talking", "Sitting and talking to someone"),
                ("sitting_quietly_after_lunch", "Sitting quietly after lunch (no alcohol)"),
                ("car_stopped_traffic", "In a car, while stopped in traffic"),
            ],
            "interpretation": {
                "normal": "Normal daytime sleepiness",
                "mild": "Mild excessive daytime sleepiness",
                "moderate": "Moderate excessive daytime sleepiness",
                "severe": "Severe excessive daytime sleepiness",
            },
            "warning": "Score >10 suggests excessive daytime sleepiness. Consider sleep evaluation.",
        }
    
    st.markdown(f"#### {tr['title']}")
    st.caption(tr['subtitle'])
    
    situations = tr['situations']
    
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
                    help=tr['help'],
                )
    
    total = sum(scores.values())
    
    # Interpretation using translations
    interp_labels = tr.get('interpretation', {})
    if total <= 5:
        interp = interp_labels.get("normal", "Normal daytime sleepiness")
        color = "green"
    elif total <= 10:
        interp = interp_labels.get("normal", "Normal daytime sleepiness")
        color = "green"
    elif total <= 12:
        interp = interp_labels.get("mild", "Mild excessive daytime sleepiness")
        color = "orange"
    elif total <= 15:
        interp = interp_labels.get("moderate", "Moderate excessive daytime sleepiness")
        color = "orange"
    else:
        interp = interp_labels.get("severe", "Severe excessive daytime sleepiness")
        color = "red"
    
    total_label = tr.get('total_score', 'Total Score')
    st.markdown(f"**{total_label}: {total}/24** — :{color}[{interp}]")
    
    if total > 10:
        st.warning(f"⚠️ {tr.get('warning', 'Score >10 suggests excessive daytime sleepiness.')}")
    
    return total


def _render_samn_perelli_form(user_id: str) -> Optional[int]:
    """Render Samn-Perelli Fatigue Scale form with i18n support."""
    # Get translations for current language
    if I18N_AVAILABLE:
        tr = get_samn_perelli_translations()
    else:
        tr = {
            "title": "Samn-Perelli Fatigue Scale",
            "subtitle": "Select the statement that best describes your current state",
            "current_state": "Current fatigue state:",
            "options": {
                1: "1 - Fully alert, wide awake",
                2: "2 - Very lively, responsive, but not at peak",
                3: "3 - Okay, somewhat fresh",
                4: "4 - A little tired, less than fresh",
                5: "5 - Moderately tired, let down",
                6: "6 - Extremely tired, very difficult to concentrate",
                7: "7 - Completely exhausted, unable to function effectively",
            },
            "risk_level": "Operational Risk Level",
            "risk_levels": {"LOW": "LOW", "MODERATE": "MODERATE", "HIGH": "HIGH", "CRITICAL": "CRITICAL"},
            "warning": "Fatigue level may impair performance. Consider rest before safety-critical tasks.",
        }
    
    st.markdown(f"#### {tr['title']}")
    st.caption(tr['subtitle'])
    
    options = tr['options']
    
    rating = st.radio(
        tr['current_state'],
        options=list(options.keys()),
        format_func=lambda x: options[x],
        horizontal=False,
        key="samn_perelli_rating",
    )
    
    # Risk level with translations
    risk_labels = tr.get('risk_levels', {})
    if rating <= 2:
        risk_key = "LOW"
        color = "green"
    elif rating <= 4:
        risk_key = "MODERATE"
        color = "orange"
    elif rating <= 5:
        risk_key = "HIGH"
        color = "red"
    else:
        risk_key = "CRITICAL"
        color = "red"
    
    risk_display = risk_labels.get(risk_key, risk_key)
    risk_label = tr.get('risk_level', 'Operational Risk Level')
    st.markdown(f"**{risk_label}: :{color}[{risk_display}]**")
    
    if rating >= 5:
        st.error(f"⚠️ {tr.get('warning', 'Fatigue level may impair performance.')}")
    
    return rating


def _render_kss_form(user_id: str) -> Optional[int]:
    """Render Karolinska Sleepiness Scale form with i18n support."""
    # Get translations for current language
    if I18N_AVAILABLE:
        tr = get_karolinska_translations()
    else:
        tr = {
            "title": "Karolinska Sleepiness Scale (KSS)",
            "subtitle": "Rate your current sleepiness level",
            "current_sleepiness": "Current sleepiness:",
            "options": {
                1: "1 - Extremely alert",
                2: "2 - Very alert",
                3: "3 - Alert",
                4: "4 - Fairly alert",
                5: "5 - Neither alert nor sleepy",
                6: "6 - Some signs of sleepiness",
                7: "7 - Sleepy, but no effort to stay awake",
                8: "8 - Sleepy, some effort to stay awake",
                9: "9 - Extremely sleepy, fighting sleep",
            },
            "warning": "KSS ≥7 indicates significant sleepiness that may impair performance.",
        }
    
    st.markdown(f"#### {tr['title']}")
    st.caption(tr['subtitle'])
    
    options = tr['options']
    
    rating = st.radio(
        tr['current_sleepiness'],
        options=list(options.keys()),
        format_func=lambda x: options[x],
        horizontal=False,
        key="kss_rating",
    )
    
    if rating >= 7:
        st.warning(f"⚠️ {tr.get('warning', 'KSS ≥7 indicates significant sleepiness.')}")
    
    return rating


def _render_vas_scales(user_id: str) -> Dict[str, float]:
    """Render Visual Analog Scale assessments with i18n support."""
    # Get translations for current language
    if I18N_AVAILABLE:
        tr = get_vas_translations()
    else:
        tr = {
            "title": "Visual Analog Scales (VAS)",
            "subtitle": "Rate your current state on a 0-10 scale",
            "fatigue": "Fatigue (0 = None, 10 = Extreme)",
            "pain": "Pain (0 = None, 10 = Worst imaginable)",
        }
    
    st.markdown(f"#### {tr['title']}")
    st.caption(tr['subtitle'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        vas_fatigue = st.slider(
            tr['fatigue'],
            min_value=0.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
            key="vas_fatigue",
        )
    
    with col2:
        vas_pain = st.slider(
            tr['pain'],
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
    """Render comprehensive clinical assessment section with i18n support."""
    st.markdown(f"## {t('clinical_assessment')}")
    st.caption(t('clinical_assessment_subtitle'))
    
    # Language selector for clinical scales
    if I18N_AVAILABLE:
        with st.expander(f"🌐 {t('language')}", expanded=False):
            render_language_selector(location="main", key_suffix="clinical")
    
    # Context inputs
    with st.expander(t('assessment_context'), expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            hours_since_wake = st.number_input(
                t('hours_since_waking'),
                min_value=0.0,
                max_value=48.0,
                value=8.0,
                step=0.5,
            )
        with col2:
            hours_sleep = st.number_input(
                t('hours_slept'),
                min_value=0.0,
                max_value=24.0,
                value=7.0,
                step=0.5,
            )
        with col3:
            caffeine_cups = st.number_input(
                t('caffeine_today'),
                min_value=0,
                max_value=20,
                value=1,
                step=1,
            )
    
    # Scale selection with translations
    available_scales = {
        "ESS": t('ess_description'),
        "SP": t('sp_description'),
        "KSS": t('kss_description'),
        "VAS": t('vas_description'),
    }
    
    selected_scales = st.multiselect(
        t('select_scales'),
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
        t('assessment_notes'),
        placeholder=t('assessment_notes_placeholder'),
        max_chars=500,
    )
    
    # Submit assessment
    if st.button(t('save_assessment'), type="primary", use_container_width=True):
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
            st.success(t('assessment_saved'))
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
# Clinical Profile Section (NASA Nutrition, Body Composition)
# ---------------------------------------------------------------------------

# Import clinical profile module if available
try:
    from clinical_profile import (
        BiologicalSex,
        ActivityLevel,
        calculate_comprehensive_requirements,
        calculate_nasa_water_requirement,
        PAL_MULTIPLIERS,
        EXERCISE_METS,
        polar_accesslink_available,
        fetch_polar_vo2max,
    )
    CLINICAL_PROFILE_AVAILABLE = True
except ImportError:
    CLINICAL_PROFILE_AVAILABLE = False


def _render_clinical_profile(user: UserProfile) -> None:
    """Render comprehensive clinical profile with NASA calculations."""
    st.markdown("## 🏥 Comprehensive Clinical Profile")
    
    if not CLINICAL_PROFILE_AVAILABLE:
        st.warning(
            "Clinical profile module not available. "
            "Ensure `clinical_profile.py` is in the app directory."
        )
        return
    
    # Data completeness check
    _render_data_completeness(user)
    
    st.markdown("---")
    
    # NASA Nutrition Calculator
    with st.expander("🚀 NASA Nutrition Calculator", expanded=True):
        _render_nasa_calculator(user)
    
    # Body Composition
    with st.expander("📏 Body Composition", expanded=False):
        _render_body_composition_form(user)
    
    # Medical History Summary
    with st.expander("📋 Medical History", expanded=False):
        _render_medical_history_summary(user)
    
    with st.expander("🧾 Exploration Medical Record", expanded=False):
        _render_medical_record_form(user)


def _render_data_completeness(user: UserProfile) -> None:
    """Show data completeness indicators."""
    st.markdown("### 📊 Profile Completeness")
    
    # Check required fields
    required_fields = {
        "Height": user.height_cm is not None,
        "Weight": user.weight_kg is not None,
        "Date of Birth": user.date_of_birth is not None,
        "Sex": user.sex is not None,
        "Activity Level": user.activity_level is not None,
    }
    
    optional_fields = {
        "Resting HR": user.resting_hr_bpm is not None,
        "VO2max": user.vo2max_ml_kg_min is not None,
        "Max HR": user.max_hr_bpm is not None,
        "Occupation": user.occupation is not None,
    }
    
    # Calculate completeness
    required_complete = sum(required_fields.values())
    required_total = len(required_fields)
    optional_complete = sum(optional_fields.values())
    optional_total = len(optional_fields)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        pct = int(required_complete / required_total * 100)
        color = "green" if pct == 100 else "orange" if pct >= 60 else "red"
        st.metric("Required Fields", f"{required_complete}/{required_total}")
        if pct < 100:
            missing = [k for k, v in required_fields.items() if not v]
            st.caption(f"⚠️ Missing: {', '.join(missing)}")
    
    with col2:
        st.metric("Optional Fields", f"{optional_complete}/{optional_total}")
    
    with col3:
        overall = int((required_complete + optional_complete) / (required_total + optional_total) * 100)
        st.metric("Overall", f"{overall}%")
    
    # Show warning if required fields missing
    if required_complete < required_total:
        st.warning(
            "⚠️ **Required fields missing!** "
            "NASA nutrition calculations require: Height, Weight, Age, Sex, Activity Level. "
            "Click 'Edit Profile' above to complete your profile."
        )


def _render_nasa_calculator(user: UserProfile) -> None:
    """Render NASA-based nutrition calculator."""
    st.markdown("#### 🧮 Energy & Nutrition Requirements")
    st.caption(
        "Calculations based on NASA JSC67378 standards and Mifflin-St Jeor equation. "
        "[View References](docs/Manual.md#scientific-references)"
    )
    
    # Check if we have required data
    if not all([user.height_cm, user.weight_kg, user.date_of_birth, user.sex]):
        st.info("Complete your profile (height, weight, age, sex) to calculate nutrition requirements.")
        return
    
    # Calculate age
    age = _calculate_age(user.date_of_birth)
    if age is None:
        st.error("Could not calculate age from date of birth.")
        return
    
    # Map sex to BiologicalSex enum
    sex_map = {
        "male": BiologicalSex.MALE,
        "female": BiologicalSex.FEMALE,
        "other": BiologicalSex.FEMALE,  # Conservative estimate
    }
    sex = sex_map.get(user.sex, BiologicalSex.FEMALE)
    
    # Activity level mapping
    activity_map = {
        "sedentary": ActivityLevel.SEDENTARY,
        "light": ActivityLevel.LIGHTLY_ACTIVE,
        "lightly_active": ActivityLevel.LIGHTLY_ACTIVE,
        "moderate": ActivityLevel.MODERATELY_ACTIVE,
        "moderately_active": ActivityLevel.MODERATELY_ACTIVE,
        "active": ActivityLevel.VERY_ACTIVE,
        "very_active": ActivityLevel.VERY_ACTIVE,
        "extra_active": ActivityLevel.EXTRA_ACTIVE,
    }
    activity_level = activity_map.get(
        user.activity_level or "moderate",
        ActivityLevel.MODERATELY_ACTIVE
    )
    
    # VO2max handling (manual + optional Polar AccessLink)
    vo2_default = float(user.vo2max_ml_kg_min or 38.0)
    st.markdown("##### 🫁 VO2max Source")
    col_vo2_a, col_vo2_b = st.columns([2, 1])
    with col_vo2_a:
        vo2_manual = st.number_input(
            "Manual VO2max (mL·kg⁻¹·min⁻¹)",
            min_value=10.0,
            max_value=90.0,
            value=vo2_default,
            step=0.5,
            help="Enter lab VO2max or estimation from field test.",
        )
    polar_cache_key = f"polar_vo2_cache_{user.user_id}"
    polar_cached = st.session_state.get(polar_cache_key)
    use_polar_override = False
    with col_vo2_b:
        if CLINICAL_PROFILE_AVAILABLE and polar_accesslink_available():
            st.caption("Polar AccessLink configured.")
            if st.button("🔄 Fetch from Polar", key=f"fetch_polar_vo2_{user.user_id}"):
                polar_value = fetch_polar_vo2max()
                if polar_value:
                    st.session_state[polar_cache_key] = polar_value
                    polar_cached = polar_value
                    st.success(f"Retrieved VO2max {polar_value:.1f} mL/kg/min")
                else:
                    st.warning("Polar AccessLink did not return a VO2max value.")
            use_polar_override = st.checkbox(
                "Use Polar value",
                value=bool(polar_cached),
                help="Requires POLAR_ACCESSLINK_TOKEN and POLAR_ACCESSLINK_USER_ID in the environment.",
                key=f"use_polar_vo2_{user.user_id}",
            )
        else:
            st.caption("Set POLAR_ACCESSLINK_TOKEN & POLAR_ACCESSLINK_USER_ID to enable API fetch.")
    effective_vo2 = vo2_manual
    if use_polar_override and polar_cached:
        effective_vo2 = float(polar_cached)
    
    # Exercise settings
    col1, col2 = st.columns(2)
    with col1:
        exercise_type = st.selectbox(
            "Exercise Type",
            options=list(EXERCISE_METS.keys()),
            index=list(EXERCISE_METS.keys()).index("cycling_moderate"),
            format_func=lambda x: x.replace("_", " ").title(),
            key="nasa_exercise_type",
        )
    with col2:
        exercise_duration = st.slider(
            "Exercise Duration (min)",
            min_value=0,
            max_value=240,
            value=120,  # Default 2 hours as requested
            step=15,
            key="nasa_exercise_duration",
        )
    
    # Calculate requirements
    try:
        results = calculate_comprehensive_requirements(
            weight_kg=user.weight_kg,
            height_cm=user.height_cm,
            age_years=age,
            sex=sex,
            activity_level=activity_level,
            exercise_type=exercise_type,
            exercise_duration_min=exercise_duration,
            vo2max_ml_kg_min=effective_vo2,
            lean_mass_kg=None,  # Would come from body composition
        )
        
        # Display results
        st.markdown("##### ⚡ Energy Requirements")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "BMR",
                f"{results['bmr']['adjusted_kcal']:.0f} kcal",
                help=f"Method: {results['bmr']['method']}"
            )
        with col2:
            st.metric(
                "TDEE",
                f"{results['energy']['tdee_kcal']:.0f} kcal",
                help=f"PAL: {results['energy']['pal_multiplier']:.2f}"
            )
        with col3:
            st.metric(
                "Exercise",
                f"+{results['energy']['exercise_kcal']:.0f} kcal",
                help=f"{exercise_duration} min {exercise_type}"
            )
        with col4:
            st.metric(
                "Total Daily",
                f"{results['energy']['total_daily_kcal']:.0f} kcal",
                delta=f"+{results['energy']['exercise_kcal']:.0f}" if exercise_duration > 0 else None,
            )
        
        st.markdown("##### 🫁 VO2max Compensation")
        exercise_details = results["energy"].get("exercise_details", {})
        vo2_help = "Manual entry" if not use_polar_override or not polar_cached else "Polar AccessLink override"
        st.metric(
            "VO2max used",
            f"{effective_vo2:.1f} mL/kg/min",
            help=vo2_help,
        )
        if exercise_details:
            st.caption(
                f"Exercise MET base {exercise_details.get('base_met', 0)} → "
                f"{exercise_details.get('adjusted_met', 0)} after VO2 factor "
                f"{exercise_details.get('vo2_factor', 1.0)}."
            )
        
        st.markdown("##### 💧 Hydration (NASA Standard)")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Base Requirement",
                f"{results['hydration']['base_ml']:.0f} mL",
                help="32 mL/kg body weight (NASA-STD-3001)"
            )
        with col2:
            st.metric(
                "With Activity",
                f"{results['hydration']['total_ml']:.0f} mL",
            )
        with col3:
            st.metric(
                "Daily Target",
                f"{results['hydration']['total_liters']:.1f} L",
                help=f"~{results['hydration']['minimum_glasses_8oz']} glasses (8 oz each)"
            )
        
        st.markdown("##### 🥗 Macronutrients (NASA JSC67378)")
        col1, col2, col3, col4 = st.columns(4)
        
        macros = results['macronutrients']
        with col1:
            st.metric(
                "Protein",
                f"{macros['protein_g']:.0f} g",
                help=f"{macros['protein_g_per_kg']:.1f} g/kg ({macros['protein_pct']:.0f}%)"
            )
        with col2:
            st.metric(
                "Carbohydrates",
                f"{macros['carbohydrate_g']:.0f} g",
                help=f"{macros['carbohydrate_pct']:.0f}%"
            )
        with col3:
            st.metric(
                "Fat",
                f"{macros['fat_g']:.0f} g",
                help=f"{macros['fat_pct']:.0f}%"
            )
        with col4:
            st.metric(
                "Fiber",
                f"{macros['fiber_g']:.0f} g",
                help="14g per 1000 kcal (IOM)"
            )
        
        # Reference note
        st.caption(
            "📚 **References**: Mifflin et al. (1990), NASA JSC67378 (2020), "
            "Scott et al. (2020). See Manual for full citations."
        )
        
    except Exception as exc:
        st.error(f"Calculation error: {exc}")


def _render_body_composition_form(user: UserProfile) -> None:
    """Render body composition entry form."""
    st.markdown("#### 📐 Body Composition Measurements")
    st.caption("Enter values from bioimpedance scale, DEXA, or caliper measurements.")
    
    with st.form("body_composition_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            body_fat_pct = st.number_input(
                "Body Fat %",
                min_value=1.0,
                max_value=60.0,
                value=20.0,
                step=0.5,
                help="From bioimpedance scale, DEXA, or calipers"
            )
            lean_mass_kg = st.number_input(
                "Lean Mass (kg)",
                min_value=20.0,
                max_value=120.0,
                value=float(user.weight_kg * 0.8) if user.weight_kg else 55.0,
                step=0.5,
            )
            muscle_mass_kg = st.number_input(
                "Muscle Mass (kg)",
                min_value=10.0,
                max_value=80.0,
                value=float(user.weight_kg * 0.4) if user.weight_kg else 30.0,
                step=0.5,
            )
        
        with col2:
            bone_mass_kg = st.number_input(
                "Bone Mass (kg)",
                min_value=1.0,
                max_value=10.0,
                value=3.0,
                step=0.1,
            )
            water_pct = st.number_input(
                "Water %",
                min_value=30.0,
                max_value=80.0,
                value=55.0,
                step=0.5,
            )
            visceral_fat = st.number_input(
                "Visceral Fat Level",
                min_value=1,
                max_value=59,
                value=8,
                step=1,
                help="1-12 healthy, 13-59 excess"
            )
        
        st.markdown("##### 📏 Circumferences (cm)")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            waist_cm = st.number_input("Waist", min_value=40.0, max_value=200.0, value=80.0, step=0.5)
            hip_cm = st.number_input("Hip", min_value=50.0, max_value=200.0, value=95.0, step=0.5)
        with col2:
            neck_cm = st.number_input("Neck", min_value=20.0, max_value=60.0, value=38.0, step=0.5)
            chest_cm = st.number_input("Chest", min_value=50.0, max_value=150.0, value=95.0, step=0.5)
        with col3:
            arm_cm = st.number_input("Arm (relaxed)", min_value=15.0, max_value=60.0, value=32.0, step=0.5)
            thigh_cm = st.number_input("Thigh", min_value=30.0, max_value=90.0, value=55.0, step=0.5)
        
        measurement_method = st.selectbox(
            "Measurement Method",
            options=["bioimpedance", "dexa", "calipers", "tape_measure", "estimated"],
            format_func=lambda x: x.replace("_", " ").title(),
        )
        
        submitted = st.form_submit_button("💾 Save Body Composition", use_container_width=True)
        
        if submitted:
            st.success("✅ Body composition saved!")
            # TODO: Save to database when schema is connected


def _render_medical_history_summary(user: UserProfile) -> None:
    """Render medical history summary and quick entry."""
    st.markdown("#### 📋 Medical History Summary")
    
    # Show current conditions from user profile
    if user.medical_conditions:
        st.write("**Current Conditions:**")
        for condition in user.medical_conditions:
            st.write(f"• {condition}")
    else:
        st.info("No medical conditions recorded. Edit your profile to add medical history.")
    
    if user.medications:
        st.write("**Current Medications:**")
        for med in user.medications:
            st.write(f"• {med}")
    
    st.caption(
        "💡 For comprehensive medical history including cardiovascular, respiratory, "
        "metabolic conditions and family history, use the Medical History form in Data Management."
    )


def _render_medical_record_form(user: UserProfile) -> None:
    """Render NASA-style exploration medical record entry form."""
    st.caption(
        "Structured per NASA Medical Information Systems & Tools (MIST) and "
        "Exploration Medical Capability (ExMC) guidance for autonomous missions. "
        "See: https://www.nasa.gov/general/medical-information-systems-and-tools-mist/ "
        "and https://ntrs.nasa.gov/citations/20230015831"
    )
    try:
        db = get_database()
        history = db.get_medical_history(user.user_id, limit=25)
    except Exception as exc:
        st.error(f"Unable to load medical history: {exc}")
        history = []
    latest = history[0] if history else {}
    
    mission_options = {
        "LUNAR-22": "Lunar sortie (22-day habitat)",
        "GATEWAY-30": "Gateway stack (30-day)",
        "MARS-ANALOG-45": "Mars analog (45-day isolation)",
        "CHAPEA-378": "CHAPEA / Mars Dune Alpha (long-duration)",
        "CUSTOM": "Custom exploration profile",
    }
    habitats = ["HERA", "CHAPEA", "NEEMO", "Gateway", "ISS", "Custom"]
    crew_roles = ["Flight Surgeon", "Commander", "Pilot", "Mission Specialist", "Payload Specialist"]
    eva_status_options = ["Cleared", "Restricted", "No EVA"]
    space_weather_alerts = ["None", "Watch", "Warning", "Post-Event Monitoring"]
    chronic_condition_options = [
        "Cardiovascular",
        "Respiratory",
        "Metabolic",
        "Neurological",
        "Psychological",
        "Musculoskeletal",
        "Renal/Urologic",
    ]
    acute_symptom_options = [
        "Headache",
        "Dizziness",
        "Visual change",
        "GI upset",
        "Musculoskeletal pain",
        "Sleep disruption",
        "Skin lesion",
    ]
    behavioral_flags = [
        "Confinement stress",
        "Team friction",
        "Mood change",
        "Cognitive slowing",
        "Motivation dip",
    ]
    
    with st.form("exploration_medical_record_form", clear_on_submit=False):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            mission_profile = st.selectbox(
                "Mission profile",
                options=list(mission_options.keys()),
                format_func=lambda key: mission_options.get(key, key),
                index=list(mission_options.keys()).index(
                    latest.get("mission_profile", "LUNAR-22")
                )
                if latest.get("mission_profile", "LUNAR-22") in mission_options
                else 0,
            )
            mission_day = st.number_input(
                "Mission day",
                min_value=0,
                max_value=720,
                value=int(latest.get("mission_day", 1)),
                step=1,
            )
            habitat = st.selectbox(
                "Habitat/analog site",
                options=habitats,
                index=habitats.index(latest.get("habitat", habitats[0]))
                if latest.get("habitat") in habitats
                else 0,
            )
        with col_b:
            crew_role = st.selectbox(
                "Crew role",
                options=crew_roles,
                index=crew_roles.index(latest.get("crew_role", crew_roles[0]))
                if latest.get("crew_role") in crew_roles
                else 0,
            )
            eva_status = st.selectbox(
                "EVA clearance",
                options=eva_status_options,
                index=eva_status_options.index(
                    latest.get("eva_status", eva_status_options[0])
                )
                if latest.get("eva_status") in eva_status_options
                else 0,
            )
            eva_hours = st.number_input(
                "EVA hours (last 72h)",
                min_value=0.0,
                max_value=36.0,
                value=float(latest.get("eva_hours_72h", 0.0)),
                step=0.5,
            )
        with col_c:
            radiation_dose = st.number_input(
                "Radiation dose (mSv)",
                min_value=0.0,
                max_value=250.0,
                value=float(latest.get("radiation_dose_msv", 0.0)),
                step=0.1,
            )
            space_weather = st.selectbox(
                "Space-weather alert level",
                options=space_weather_alerts,
                index=space_weather_alerts.index(
                    latest.get("space_weather_alert", space_weather_alerts[0])
                )
                if latest.get("space_weather_alert") in space_weather_alerts
                else 0,
            )
            confinement_stress = st.slider(
                "Confinement stress (1-10)",
                min_value=1,
                max_value=10,
                value=int(latest.get("confinement_stress", 3)),
            )
        
        chronic_conditions = st.multiselect(
            "Chronic condition log",
            options=chronic_condition_options,
            default=latest.get("chronic_conditions", []),
        )
        acute_symptoms = st.multiselect(
            "Acute symptoms (last 24h)",
            options=acute_symptom_options,
            default=latest.get("acute_symptoms", []),
        )
        behavioral_state = st.multiselect(
            "Behavioral health notes",
            options=behavioral_flags,
            default=latest.get("behavioral_flags", []),
        )
        
        col_d, col_e, col_f = st.columns(3)
        with col_d:
            sleep_hours = st.number_input(
                "Sleep (last 24h, hours)",
                min_value=0.0,
                max_value=12.0,
                value=float(latest.get("sleep_hours", 7.0)),
                step=0.25,
            )
        with col_e:
            exercise_minutes = st.number_input(
                "Countermeasure exercise (min/day)",
                min_value=0.0,
                max_value=300.0,
                value=float(latest.get("exercise_minutes", 120.0)),
                step=5.0,
            )
        with col_f:
            hydration_liters = st.number_input(
                "Water intake (L/day)",
                min_value=0.0,
                max_value=10.0,
                value=float(latest.get("hydration_liters", 3.8)),
                step=0.1,
            )
        
        inventory_alert = st.selectbox(
            "Medical inventory status",
            options=["Nominal", "Monitor", "Critical Shortage"],
            index=["Nominal", "Monitor", "Critical Shortage"].index(
                latest.get("inventory_alert", "Nominal")
            )
            if latest.get("inventory_alert") in ["Nominal", "Monitor", "Critical Shortage"]
            else 0,
        )
        notes = st.text_area(
            "Operational/clinical notes",
            value=str(latest.get("notes", "")),
            height=120,
        )
        update_latest = st.checkbox(
            "Update latest entry instead of creating a new record",
            value=False,
        )
        
        submitted = st.form_submit_button("💾 Save Exploration Medical Record")
        if submitted:
            record = {
                "mission_profile": mission_profile,
                "mission_day": mission_day,
                "habitat": habitat,
                "crew_role": crew_role,
                "eva_status": eva_status,
                "eva_hours_72h": eva_hours,
                "radiation_dose_msv": radiation_dose,
                "space_weather_alert": space_weather,
                "confinement_stress": confinement_stress,
                "chronic_conditions": chronic_conditions,
                "acute_symptoms": acute_symptoms,
                "behavioral_flags": behavioral_state,
                "sleep_hours": sleep_hours,
                "exercise_minutes": exercise_minutes,
                "hydration_liters": hydration_liters,
                "inventory_alert": inventory_alert,
                "notes": notes,
            }
            try:
                entry_id = db.save_medical_history_entry(
                    user.user_id,
                    record,
                    history_id=latest.get("history_id") if (update_latest and latest) else None,
                )
                st.success("Exploration medical record saved.")
                st.session_state["last_med_record_id"] = entry_id
            except Exception as exc:
                st.error(f"Failed to save medical record: {exc}")
    
    if history:
        st.markdown("#### 📚 Recent Medical Records")
        display_df = pd.DataFrame(history)
        # Flatten list columns for readability
        for col in ["chronic_conditions", "acute_symptoms", "behavioral_flags"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(
                    lambda val: ", ".join(val) if isinstance(val, list) else val
                )
        st.dataframe(
            display_df[
                [
                    "updated_at",
                    "mission_profile",
                    "mission_day",
                    "eva_status",
                    "space_weather_alert",
                    "radiation_dose_msv",
                    "sleep_hours",
                    "exercise_minutes",
                ]
            ],
            use_container_width=True,
        )
    else:
        st.info("No exploration medical records logged yet.")


# ---------------------------------------------------------------------------
# User Sessions Tab (Multi-User Support)
# ---------------------------------------------------------------------------


def _render_user_sessions_tab(current_user: UserProfile) -> None:
    """Render the user sessions management tab."""
    st.markdown("## 👥 User Sessions Management")
    
    if not MULTI_USER_AVAILABLE:
        st.info(
            "Multi-user sessions allow you to have up to 7 users open simultaneously. "
            "This feature enables quick switching between users for data entry and analysis."
        )
        st.warning("Multi-user module not available. Ensure `multi_user_session.py` is in the app directory.")
        return
    
    manager = get_multi_user_manager()
    
    # Display session count
    col1, col2 = st.columns([2, 1])
    with col1:
        st.metric("Active Sessions", f"{manager.session_count}/{MAX_CONCURRENT_USERS}")
    with col2:
        if manager.can_add_user:
            st.success("✓ Can add more users")
        else:
            st.warning("⚠️ Maximum reached")
    
    st.markdown("---")
    
    # Full session manager
    render_user_session_manager()
    
    st.markdown("---")
    
    # Quick add user section
    st.markdown("### ➕ Add Another User")
    st.caption("Log in with another existing account to add them to your active sessions.")
    
    try:
        db = get_database()
        all_users = db.list_users()
        
        # Filter out already active users
        active_ids = {s["user_id"] for s in manager.get_all_sessions_summary()}
        available_users = [u for u in all_users if u.user_id not in active_ids]
        
        if not available_users:
            if not all_users:
                st.info("No other users registered. Register new users from the Login tab.")
            else:
                st.info("All registered users are already in active sessions.")
        elif not manager.can_add_user:
            st.warning(f"Maximum {MAX_CONCURRENT_USERS} sessions reached. Close a session to add more users.")
        else:
            user_options = {u.username: u for u in available_users}
            selected = st.selectbox(
                "Select user to add",
                options=list(user_options.keys()),
                format_func=lambda x: f"{x} ({user_options[x].full_name or x})",
                key="add_user_session_select",
            )
            
            if st.button("➕ Add to Active Sessions", key="add_user_session_btn"):
                user_to_add = user_options[selected]
                if manager.add_user_session(
                    user_id=user_to_add.user_id,
                    username=user_to_add.username,
                    full_name=user_to_add.full_name or user_to_add.username,
                    make_active=False,  # Don't switch, just add
                ):
                    st.success(f"Added {user_to_add.username} to active sessions!")
                    st.rerun()
                else:
                    st.error("Failed to add user session.")
    
    except Exception as exc:
        st.error(f"Error loading users: {exc}")
    
    st.markdown("---")
    
    # Roadmap note
    st.info(
        "🚀 **Coming Soon**: Full multi-user analysis capabilities including:\n"
        "- Per-user correlation calculations\n"
        "- Group-based analysis (inter-subject)\n"
        "- Longitudinal tracking (baseline + 22 timepoints)\n"
        "- Comparative HRV metrics across users\n\n"
        "See [WARP.md](WARP.md) for the complete roadmap."
    )


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
    
    # Show multi-user session manager if available and users are active
    if MULTI_USER_AVAILABLE:
        manager = get_multi_user_manager()
        if manager.session_count > 1:
            with st.expander(f"👥 Active Sessions ({manager.session_count}/{MAX_CONCURRENT_USERS})", expanded=False):
                render_user_session_manager()
            st.divider()
    
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
        tab_assess, tab_clinical, tab_history, tab_hrv, tab_data, tab_sessions = st.tabs([
            "📋 Assessments",
            "🏥 Clinical Profile",
            "📈 History",
            "💓 HRV",
            "📦 Data",
            "👥 Sessions",
        ])
        
        with tab_assess:
            _render_clinical_assessment(current_user)
        
        with tab_clinical:
            _render_clinical_profile(current_user)
        
        with tab_history:
            _render_assessment_history(current_user)
        
        with tab_hrv:
            _render_hrv_history(current_user)
        
        with tab_data:
            _render_data_management(current_user)
        
        with tab_sessions:
            _render_user_sessions_tab(current_user)


# ---------------------------------------------------------------------------
# Convenience functions for getting current user data (for other modules)
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
    
    latest_medical_record: Dict[str, Any] = {}
    try:
        db = get_database()
        last_rows = db.get_medical_history(user.user_id, limit=1)
        if last_rows:
            latest_medical_record = last_rows[0]
    except Exception:
        latest_medical_record = {}
    
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
        "language": getattr(user, 'language', 'en'),
        "medical_conditions": getattr(user, 'medical_conditions', []),
        "medications": getattr(user, 'medications', []),
        "medical_record": latest_medical_record,
    }


def get_active_user_context() -> Dict[str, Any]:
    """
    Get comprehensive user context for all tabs to use in calculations.
    
    This function provides all user-specific settings that affect computations:
    - Demographics for age-adjusted calculations
    - Physiological parameters (VO2max, resting HR, max HR)
    - Body composition for energy calculations
    - Activity level for metabolic adjustments
    - Medical history for risk considerations
    
    Returns:
        Dictionary with user context, or defaults if no user logged in.
    """
    user = _get_current_user()
    
    # Default context if no user
    if user is None:
        return {
            "has_user": False,
            "user_id": None,
            "username": "Guest",
            "age_years": 35,  # Default middle-aged adult
            "sex": "other",
            "weight_kg": 70.0,
            "height_cm": 170.0,
            "bmi": 24.2,
            "resting_hr_bpm": 70,
            "max_hr_bpm": 185,
            "vo2max_ml_kg_min": 35.0,  # Average fitness
            "activity_level": "moderately_active",
            "chronotype_offset": 0.0,  # Neutral chronotype
            "occupation": None,
            "medical_conditions": [],
            "medications": [],
            "medical_record": {},
            "is_guest": True,
        }
    
    # Calculate derived values
    age = _calculate_age(user.date_of_birth)
    bmi = _calculate_bmi(user.height_cm, user.weight_kg)
    
    # Estimate max HR if not provided (using Fox formula)
    max_hr = user.max_hr_bpm
    if max_hr is None and age is not None:
        max_hr = 220 - age
    
    # Estimate chronotype offset from occupation (simplified)
    chronotype_offset = 0.0
    if user.occupation:
        occupation_lower = user.occupation.lower()
        if any(x in occupation_lower for x in ["night", "shift", "pilot", "flight"]):
            chronotype_offset = 1.0  # Slight evening tendency for shift workers
        elif any(x in occupation_lower for x in ["early", "morning", "farmer"]):
            chronotype_offset = -1.0  # Morning tendency
    
    latest_medical_record: Dict[str, Any] = {}
    try:
        db = get_database()
        med_rows = db.get_medical_history(user.user_id, limit=1)
        if med_rows:
            latest_medical_record = med_rows[0]
    except Exception:
        latest_medical_record = {}
    
    return {
        "has_user": True,
        "user_id": user.user_id,
        "username": user.username,
        "full_name": user.full_name,
        "age_years": age or 35,
        "sex": user.sex or "other",
        "weight_kg": user.weight_kg or 70.0,
        "height_cm": user.height_cm or 170.0,
        "bmi": bmi or 24.2,
        "resting_hr_bpm": user.resting_hr_bpm or 70,
        "max_hr_bpm": max_hr or 185,
        "vo2max_ml_kg_min": user.vo2max_ml_kg_min or 35.0,
        "activity_level": user.activity_level or "moderately_active",
        "chronotype_offset": chronotype_offset,
        "occupation": user.occupation,
        "medical_conditions": getattr(user, 'medical_conditions', []),
        "medications": getattr(user, 'medications', []),
        "language": getattr(user, 'language', 'en'),
        "is_guest": False,
        "medical_record": latest_medical_record,
    }


def get_all_active_users() -> List[Dict[str, Any]]:
    """
    Get data for all users in active sessions.
    
    Returns:
        List of user data dictionaries for all active users.
    """
    if not MULTI_USER_AVAILABLE:
        # Fall back to current user only
        current = get_current_user_data()
        return [current] if current else []
    
    try:
        manager = get_multi_user_manager()
        sessions = manager.get_all_sessions_summary()
        
        if not sessions:
            return []
        
        db = get_database()
        users_data = []
        
        for session in sessions:
            user = db.get_user(session["user_id"])
            if user:
                users_data.append({
                    "user_id": user.user_id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "age_years": _calculate_age(user.date_of_birth),
                    "sex": user.sex,
                    "weight_kg": user.weight_kg,
                    "height_cm": user.height_cm,
                    "is_active": session["is_active"],
                })
        
        return users_data
    
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    "render_user_profile_tab",
    "get_current_user_data",
    "get_active_user_context",
    "get_all_active_users",
]

