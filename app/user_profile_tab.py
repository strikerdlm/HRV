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
import time
import uuid
from collections import Counter
from datetime import datetime, date, timezone, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Final, List, Optional, Sequence

import numpy as np
import pandas as pd
import streamlit as st

try:
    from logging_config import get_logger, log_exception
except ImportError:  # pragma: no cover - fallback if logging_config missing
    get_logger = None  # type: ignore[assignment]
    log_exception = None  # type: ignore[assignment]

# Import database module
try:
    from user_database import (
        UserProfile,
        ClinicalScales,
        HRVMeasurement,
        GarminDailyMetrics,
        UserDatabase,
        get_database,
        get_cached_user_list,
        clear_user_cache,
    )
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    # Fallbacks for missing functions
    def get_cached_user_list() -> list:  # type: ignore[misc]
        return []
    def clear_user_cache() -> None:  # type: ignore[misc]
        pass

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
        get_panas_translations,
        render_language_selector,
    )
    I18N_AVAILABLE = True
except ImportError:
    I18N_AVAILABLE = False
    # Fallback function if i18n not available
    def t(key: str, **kwargs: Any) -> str:  # type: ignore[misc]
        return key
    def get_panas_translations() -> dict:  # type: ignore[misc]
        return {}

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

# Garmin wellness import (FIT/ZIP)
try:
    from garmin_import import (
        get_daily_physiology_summary,
        import_garmin_data,
    )
    GARMIN_IMPORT_AVAILABLE = True
except ImportError:
    GARMIN_IMPORT_AVAILABLE = False

# Visualization helpers
from echarts_component import render_echarts
from gauge_builder import GaugeThresholds, build_two_ring_gauge, get_gauge_thresholds

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

_LOGGER: Final[logging.Logger] = (
    get_logger(__name__) if get_logger is not None else logging.getLogger(__name__)
)

# Check for @st.fragment support (Streamlit 1.37+)
try:
    _HAS_FRAGMENT = hasattr(st, "fragment")
except AttributeError:
    _HAS_FRAGMENT = False


def _fragment_if_available(func: Any) -> Any:
    """Decorator that applies @st.fragment if available, otherwise no-op.
    
    Fragments allow partial reruns of just the decorated function,
    avoiding full page reruns when interacting with widgets inside.
    """
    if _HAS_FRAGMENT:
        return st.fragment(func)
    return func


# ---------------------------------------------------------------------------
# Session State Keys
# ---------------------------------------------------------------------------

_SESSION_CURRENT_USER = "current_user_profile"
_SESSION_USER_ID = "current_user_id"
_SESSION_SHOW_REGISTRATION = "show_registration_form"
_FORM_DEBOUNCE_PREFIX: Final[str] = "form_debounce_key_"
_FORM_DEBOUNCE_SECONDS: Final[float] = 0.8


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


def _should_process_form_submission(form_key: str, debounce_seconds: float = _FORM_DEBOUNCE_SECONDS) -> bool:
    """Prevent duplicate form submissions within a short interval."""
    state_key = f"{_FORM_DEBOUNCE_PREFIX}{form_key}"
    now = time.monotonic()
    last_submission = st.session_state.get(state_key, 0.0)
    if now - last_submission < debounce_seconds:
        return False
    st.session_state[state_key] = now
    return True


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


def _safe_float(value: Any) -> Optional[float]:
    """Convert to float if valid, otherwise None."""
    if value is None:
        return None
    try:
        if isinstance(value, (float, int)) and (pd.isna(value)):
            return None
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> Optional[int]:
    """Convert to int if valid, otherwise None."""
    if value is None:
        return None
    try:
        if isinstance(value, (float, int)) and (pd.isna(value)):
            return None
        return int(value)
    except Exception:
        return None


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
                
                # Clear user cache after successful creation
                clear_user_cache()
                
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
    # Use cached user list for better performance
    cached_users = get_cached_user_list()
    
    if not cached_users:
        st.info("No users registered. Create a new profile below.")
        return None
    
    st.markdown("### 🔑 Select or Login")
    
    col_select, col_action = st.columns([3, 1])
    
    with col_select:
        # Build options from cached data (avoiding full DB query)
        user_options = {u["username"]: u for u in cached_users}
        selected_username = st.selectbox(
            "Select User",
            options=list(user_options.keys()),
            format_func=lambda x: f"{user_options[x]['full_name']} (@{x})",
        )
    
    with col_action:
        st.write("")  # Spacing
        if st.button("✅ Select User", use_container_width=True):
            selected_data = user_options.get(selected_username)
            if selected_data:
                # Fetch full user profile only when needed
                db = get_database()
                user = db.get_user(selected_data["user_id"])
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
    """Render Epworth Sleepiness Scale form with i18n support.
    
    Uses st.session_state to aggregate slider values without triggering full reruns.
    """
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
    
    # Use select_slider for smoother interaction (fewer DOM updates)
    scores: Dict[str, int] = {}
    
    cols_per_row = 2
    for i in range(0, len(situations), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, (key, label) in enumerate(situations[i:i + cols_per_row]):
            with cols[j]:
                slider_key = f"ess_{key}"
                # Pre-initialize session state for smoother behavior
                if slider_key not in st.session_state:
                    st.session_state[slider_key] = 0
                scores[key] = st.select_slider(
                    label,
                    options=[0, 1, 2, 3],
                    value=st.session_state.get(slider_key, 0),
                    key=slider_key,
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


def _render_panas_form(user_id: str) -> Dict[str, Optional[int]]:
    """Render PANAS (Positive and Negative Affect Schedule) form with i18n support.
    
    Returns PA and NA scores (10-50 each) based on Watson, Clark & Tellegen (1988).
    Spanish validation: Sandín et al. (1999), Psicothema.
    """
    # Get translations for current language
    if I18N_AVAILABLE:
        tr = get_panas_translations()
    else:
        tr = {
            "title": "Positive and Negative Affect Schedule (PANAS)",
            "subtitle": "Indicate to what extent you feel this way right now",
            "response_options": {1: "Very slightly", 2: "A little", 3: "Moderately", 4: "Quite a bit", 5: "Extremely"},
            "pa_items": [
                ("interested", "Interested"), ("excited", "Excited"), ("strong", "Strong"),
                ("enthusiastic", "Enthusiastic"), ("proud", "Proud"), ("alert", "Alert"),
                ("inspired", "Inspired"), ("determined", "Determined"), ("attentive", "Attentive"),
                ("active", "Active"),
            ],
            "na_items": [
                ("distressed", "Distressed"), ("upset", "Upset"), ("guilty", "Guilty"),
                ("scared", "Scared"), ("hostile", "Hostile"), ("irritable", "Irritable"),
                ("ashamed", "Ashamed"), ("nervous", "Nervous"), ("jittery", "Jittery"),
                ("afraid", "Afraid"),
            ],
            "pa_label": "Positive Affect (PA)",
            "na_label": "Negative Affect (NA)",
            "score_range": "Score range: 10–50",
            "interpretation": {
                "pa_high": "High positive affect",
                "pa_moderate": "Moderate positive affect",
                "pa_low": "Low positive affect",
                "na_high": "High negative affect",
                "na_moderate": "Moderate negative affect",
                "na_low": "Low negative affect",
            },
            "reference": "Watson, Clark, & Tellegen (1988)",
            "clinical_note": "PA and NA are independent dimensions.",
        }
    
    st.markdown(f"#### {tr['title']}")
    st.caption(tr['subtitle'])
    
    response_opts = tr['response_options']
    pa_items = tr['pa_items']
    na_items = tr['na_items']
    
    # Pre-initialize session state for smoother behavior
    for key, _ in pa_items + na_items:
        state_key = f"panas_{key}"
        if state_key not in st.session_state:
            st.session_state[state_key] = 3  # Default to "Moderately"
    
    # Create two columns for PA and NA
    col_pa, col_na = st.columns(2)
    
    pa_scores: Dict[str, int] = {}
    na_scores: Dict[str, int] = {}
    
    with col_pa:
        st.markdown(f"**{tr['pa_label']}** 🌟")
        for key, label in pa_items:
            state_key = f"panas_{key}"
            pa_scores[key] = st.select_slider(
                label,
                options=list(response_opts.keys()),
                value=st.session_state.get(state_key, 3),
                format_func=lambda x: f"{x}",
                key=state_key,
                help=response_opts.get(st.session_state.get(state_key, 3), ""),
            )
    
    with col_na:
        st.markdown(f"**{tr['na_label']}** ⚡")
        for key, label in na_items:
            state_key = f"panas_{key}"
            na_scores[key] = st.select_slider(
                label,
                options=list(response_opts.keys()),
                value=st.session_state.get(state_key, 3),
                format_func=lambda x: f"{x}",
                key=state_key,
                help=response_opts.get(st.session_state.get(state_key, 3), ""),
            )
    
    # Calculate totals
    pa_total = sum(pa_scores.values())
    na_total = sum(na_scores.values())
    
    # Interpretation thresholds (based on normative data from Crawford & Henry, 2004)
    # PA: Mean ~31, SD ~8 → Low <23, Moderate 23-39, High >39
    # NA: Mean ~16, SD ~6 → Low <10, Moderate 10-22, High >22
    interp = tr.get('interpretation', {})
    
    if pa_total >= 40:
        pa_interp = interp.get("pa_high", "High positive affect")
        pa_color = "green"
    elif pa_total >= 23:
        pa_interp = interp.get("pa_moderate", "Moderate positive affect")
        pa_color = "blue"
    else:
        pa_interp = interp.get("pa_low", "Low positive affect")
        pa_color = "orange"
    
    if na_total >= 23:
        na_interp = interp.get("na_high", "High negative affect")
        na_color = "red"
    elif na_total >= 10:
        na_interp = interp.get("na_moderate", "Moderate negative affect")
        na_color = "orange"
    else:
        na_interp = interp.get("na_low", "Low negative affect")
        na_color = "green"
    
    st.markdown("---")
    
    # Display results with gauges using ECharts
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        _render_panas_gauge(
            value=pa_total,
            title=tr['pa_label'],
            min_val=10,
            max_val=50,
            color_zones=[
                (23, "#ff9800"),  # Low (orange)
                (40, "#2196f3"),  # Moderate (blue)
                (50, "#4caf50"),  # High (green)
            ],
            key_suffix="pa",
        )
        st.markdown(f"**PA: {pa_total}/50** — :{pa_color}[{pa_interp}]")
    
    with col_g2:
        _render_panas_gauge(
            value=na_total,
            title=tr['na_label'],
            min_val=10,
            max_val=50,
            color_zones=[
                (10, "#4caf50"),  # Low (green)
                (23, "#ff9800"),  # Moderate (orange)
                (50, "#f44336"),  # High (red)
            ],
            key_suffix="na",
        )
        st.markdown(f"**NA: {na_total}/50** — :{na_color}[{na_interp}]")
    
    # Clinical note
    st.caption(f"💡 {tr.get('clinical_note', '')}")
    st.caption(f"📚 {tr.get('reference', '')}")
    
    return {"panas_pa": pa_total, "panas_na": na_total}


def _render_panas_gauge(
    value: int,
    title: str,
    min_val: int,
    max_val: int,
    color_zones: list,
    key_suffix: str,
) -> None:
    """Render a modern ECharts gauge for PANAS scores.
    
    Args:
        value: Current score value.
        title: Gauge title.
        min_val: Minimum scale value.
        max_val: Maximum scale value.
        color_zones: List of (threshold, color) tuples for gauge zones.
        key_suffix: Unique key suffix for the component.
    """
    import json
    
    # Build color zone config for ECharts
    zones = []
    prev_threshold = min_val
    for threshold, color in color_zones:
        zones.append([
            (threshold - min_val) / (max_val - min_val),
            color
        ])
        prev_threshold = threshold
    
    # ECharts gauge option - modern two-ring style
    option = {
        "series": [
            {
                "type": "gauge",
                "center": ["50%", "60%"],
                "startAngle": 200,
                "endAngle": -20,
                "min": min_val,
                "max": max_val,
                "splitNumber": 8,
                "itemStyle": {"color": "#2196f3"},
                "progress": {
                    "show": True,
                    "width": 20,
                    "itemStyle": {
                        "color": {
                            "type": "linear",
                            "x": 0, "y": 0, "x2": 1, "y2": 0,
                            "colorStops": [
                                {"offset": 0, "color": color_zones[0][1]},
                                {"offset": 0.5, "color": color_zones[1][1] if len(color_zones) > 1 else color_zones[0][1]},
                                {"offset": 1, "color": color_zones[-1][1]},
                            ],
                        }
                    }
                },
                "pointer": {
                    "icon": "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z",
                    "length": "12%",
                    "width": 20,
                    "offsetCenter": [0, "-60%"],
                    "itemStyle": {"color": "auto"},
                },
                "axisLine": {
                    "lineStyle": {
                        "width": 20,
                        "color": zones,
                    }
                },
                "axisTick": {
                    "distance": -30,
                    "splitNumber": 5,
                    "lineStyle": {"width": 2, "color": "#999"},
                },
                "splitLine": {
                    "distance": -35,
                    "length": 14,
                    "lineStyle": {"width": 3, "color": "#999"},
                },
                "axisLabel": {
                    "distance": -20,
                    "color": "#999",
                    "fontSize": 12,
                },
                "anchor": {
                    "show": False,
                },
                "title": {"show": False},
                "detail": {
                    "valueAnimation": True,
                    "width": "60%",
                    "lineHeight": 40,
                    "borderRadius": 8,
                    "offsetCenter": [0, "-15%"],
                    "fontSize": 28,
                    "fontWeight": "bold",
                    "formatter": "{value}",
                    "color": "inherit",
                },
                "data": [{"value": value}],
            }
        ],
    }
    
    # Render using streamlit-echarts if available, otherwise use HTML/JS
    try:
        from streamlit_echarts import st_echarts
        st_echarts(options=option, height="220px", key=f"panas_gauge_{key_suffix}")
    except ImportError:
        # Fallback: render as HTML with ECharts CDN
        option_json = json.dumps(option)
        html = f'''
        <div id="panas_gauge_{key_suffix}" style="width:100%;height:220px;"></div>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
        <script>
            var chart = echarts.init(document.getElementById('panas_gauge_{key_suffix}'));
            chart.setOption({option_json});
            window.addEventListener('resize', function() {{ chart.resize(); }});
        </script>
        '''
        st.components.v1.html(html, height=240)


# ---------------------------------------------------------------------------
# Clinical Assessment Session
# ---------------------------------------------------------------------------


def _render_clinical_assessment(user: UserProfile) -> None:
    """Render comprehensive clinical assessment section with batched submissions."""
    st.markdown(f"## {t('clinical_assessment')}")
    st.caption(t('clinical_assessment_subtitle'))
    
    if I18N_AVAILABLE:
        with st.expander(f"🌐 {t('language')}", expanded=False):
            render_language_selector(location="main", key_suffix="clinical")
    
    available_scales = {
        "ESS": t('ess_description'),
        "SP": t('sp_description'),
        "KSS": t('kss_description'),
        "VAS": t('vas_description'),
        "PANAS": "Positive and Negative Affect Schedule (mood/affect)",
    }
    
    st.caption("⚡ Inputs are batched — use Preview or Save to refresh scores without full reruns.")
    
    selected_scales = st.multiselect(
        t('select_scales'),
        options=list(available_scales.keys()),
        default=["SP", "KSS"],
        format_func=lambda x: f"{x}: {available_scales[x]}",
    )
    
    form_key = f"clinical_assessment_form_{user.user_id}"
    results: Dict[str, Any] = {}
    context_data: Dict[str, Any] = {}
    notes_text = ""
    
    with st.form(form_key, clear_on_submit=False):
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
        context_data = {
            "hours_since_wake": hours_since_wake,
            "hours_sleep": hours_sleep,
            "caffeine_cups": caffeine_cups,
        }
        
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
                results.update(_render_vas_scales(user.user_id))
        
        if "PANAS" in selected_scales:
            with st.expander("📋 PANAS - Positive & Negative Affect", expanded=True):
                panas_result = _render_panas_form(user.user_id)
                results["panas_pa"] = panas_result.get("panas_pa")
                results["panas_na"] = panas_result.get("panas_na")
        
        notes_text = st.text_area(
            t('assessment_notes'),
            placeholder=t('assessment_notes_placeholder'),
            max_chars=500,
        )
        
        col_save, col_preview = st.columns([3, 1])
        save_clicked = col_save.form_submit_button(
            t('save_assessment'),
            type="primary",
            use_container_width=True,
        )
        preview_clicked = col_preview.form_submit_button(
            "🔁 Preview Scores",
            use_container_width=True,
        )
    
    if preview_clicked or save_clicked:
        _render_assessment_preview(results, context_data, notes_text)
    
    if save_clicked:
        if not _should_process_form_submission(form_key):
            st.info("Processing previous submission... please wait.")
            return
        try:
            db = get_database()
            context_note = (
                f"Wake: {context_data.get('hours_since_wake', 0)}h, "
                f"Sleep: {context_data.get('hours_sleep', 0)}h, "
                f"Caffeine: {context_data.get('caffeine_cups', 0)} cups. "
                f"{notes_text}"
            )
            scales = ClinicalScales(
                assessment_id=str(uuid.uuid4()),
                user_id=user.user_id,
                assessment_date=datetime.now(timezone.utc).isoformat(),
                epworth_sleepiness_scale=results.get("ess"),
                karolinska_sleepiness_scale=results.get("kss"),
                samn_perelli_fatigue=results.get("samn_perelli"),
                panas_positive_affect=results.get("panas_pa"),
                panas_negative_affect=results.get("panas_na"),
                vas_fatigue=results.get("vas_fatigue"),
                vas_pain=results.get("vas_pain"),
                notes=context_note,
            )
            db.save_clinical_scales(scales)
            st.success(t('assessment_saved'))
            st.balloons()
        except Exception as exc:
            st.error(f"Failed to save assessment: {exc}")


def _render_assessment_preview(
    results: Dict[str, Any],
    context_data: Dict[str, Any],
    notes_text: str,
) -> None:
    """Display a summary panel for previewed assessments."""
    if not results:
        st.info("Select at least one scale to preview.")
        return
    
    st.markdown("### 📊 Assessment Preview")
    col1, col2, col3 = st.columns(3)
    with col1:
        value = results.get("samn_perelli")
        st.metric("Samn-Perelli", f"{value:.1f}" if value is not None else "—")
    with col2:
        value = results.get("kss")
        st.metric("KSS", f"{value:.1f}" if value is not None else "—")
    with col3:
        value = results.get("ess")
        st.metric("ESS", f"{value:.0f}" if value is not None else "—")
    
    # PANAS preview
    panas_pa = results.get("panas_pa")
    panas_na = results.get("panas_na")
    if panas_pa is not None or panas_na is not None:
        col_pa, col_na = st.columns(2)
        with col_pa:
            if panas_pa is not None:
                pa_color = "green" if panas_pa >= 40 else ("blue" if panas_pa >= 23 else "orange")
                st.metric("PANAS PA", f"{panas_pa}/50", help="Positive Affect")
        with col_na:
            if panas_na is not None:
                na_color = "red" if panas_na >= 23 else ("orange" if panas_na >= 10 else "green")
                st.metric("PANAS NA", f"{panas_na}/50", help="Negative Affect")
    
    vas_fatigue = results.get("vas_fatigue")
    vas_pain = results.get("vas_pain")
    if vas_fatigue is not None or vas_pain is not None:
        st.caption(
            f"VAS — Fatigue: {vas_fatigue if vas_fatigue is not None else '—'}/10 · "
            f"Pain: {vas_pain if vas_pain is not None else '—'}/10"
        )
    
    st.caption(
        "Context: Wake "
        f"{context_data.get('hours_since_wake', '—')}h | Sleep "
        f"{context_data.get('hours_sleep', '—')}h | Caffeine "
        f"{context_data.get('caffeine_cups', '—')} cups"
    )
    if notes_text.strip():
        st.caption(f"Notes: {notes_text.strip()}")


# ---------------------------------------------------------------------------
# Assessment History
# ---------------------------------------------------------------------------


@_fragment_if_available
def _render_assessment_history(user: UserProfile) -> None:
    """Render clinical assessment history."""
    st.markdown("## 📈 Assessment History")
    
    # Use cached loader for fast repeated views
    @st.cache_data(ttl=30, show_spinner=False)
    def _load_history(uid: str, limit: int) -> list:
        db = get_database()
        return [h.to_dict() for h in db.get_clinical_scales_history(uid, limit=limit)]
    
    try:
        history_dicts = _load_history(user.user_id, 50)
        
        if not history_dicts:
            st.info("No assessment history found. Complete a clinical assessment to start tracking.")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(history_dicts)
        df["assessment_date"] = pd.to_datetime(df["assessment_date"])
        df = df.sort_values("assessment_date", ascending=False)
        
        # Summary metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Assessments", len(df))
        with col2:
            if "samn_perelli_fatigue" in df.columns:
                mean_sp = df["samn_perelli_fatigue"].mean()
                st.metric("Avg SP", f"{mean_sp:.1f}" if pd.notna(mean_sp) else "—")
        with col3:
            if "karolinska_sleepiness_scale" in df.columns:
                mean_kss = df["karolinska_sleepiness_scale"].mean()
                st.metric("Avg KSS", f"{mean_kss:.1f}" if pd.notna(mean_kss) else "—")
        with col4:
            if "panas_positive_affect" in df.columns:
                mean_pa = df["panas_positive_affect"].mean()
                st.metric("Avg PA", f"{mean_pa:.0f}" if pd.notna(mean_pa) else "—", help="PANAS Positive Affect")
        with col5:
            if "panas_negative_affect" in df.columns:
                mean_na = df["panas_negative_affect"].mean()
                st.metric("Avg NA", f"{mean_na:.0f}" if pd.notna(mean_na) else "—", help="PANAS Negative Affect")
        
        # Trend charts - Fatigue scales
        if len(df) > 1:
            st.markdown("##### 📈 Fatigue & Sleepiness Trends")
            chart_cols = ["samn_perelli_fatigue", "karolinska_sleepiness_scale"]
            available_cols = [c for c in chart_cols if c in df.columns]
            if available_cols:
                chart_data = df[["assessment_date"] + available_cols].dropna(how="all", subset=available_cols)
                if not chart_data.empty:
                    chart_data = chart_data.set_index("assessment_date")
                    st.line_chart(chart_data)
            
            # PANAS Trend chart
            panas_cols = ["panas_positive_affect", "panas_negative_affect"]
            available_panas = [c for c in panas_cols if c in df.columns]
            if available_panas and df[available_panas].notna().any().any():
                st.markdown("##### 🎭 PANAS Affect Trends")
                panas_data = df[["assessment_date"] + available_panas].dropna(how="all", subset=available_panas)
                if not panas_data.empty:
                    panas_data = panas_data.set_index("assessment_date")
                    st.line_chart(panas_data)
        
        # Data table
        with st.expander("📊 All Assessment Data"):
            display_cols = [
                "assessment_date",
                "epworth_sleepiness_scale",
                "samn_perelli_fatigue",
                "karolinska_sleepiness_scale",
                "panas_positive_affect",
                "panas_negative_affect",
                "vas_fatigue",
                "vas_pain",
                "notes",
            ]
            display_df = df[[c for c in display_cols if c in df.columns]]
            st.dataframe(display_df, use_container_width=True)
        
    except Exception as exc:
        st.error(f"Failed to load history: {exc}")


@_fragment_if_available
def _render_garmin_metrics_history(user: UserProfile) -> None:
    """Render wrist-wearable wellness/activity history with gauges."""
    st.markdown("## ⌚ Wrist Monitoring")

    # If sidebar ingestion placed pending metrics, persist them now
    pending_sidebar = st.session_state.pop("garmin_daily_pending", None)
    if pending_sidebar:
        try:
            pending_df = pd.DataFrame(pending_sidebar)
            if not pending_df.empty:
                entries: List[GarminDailyMetrics] = []
                now_iso = datetime.now(timezone.utc).isoformat()
                for _, row in pending_df.iterrows():
                    day_val = row.get("date")
                    if pd.isna(day_val):
                        continue
                    metric_date = pd.to_datetime(day_val).date().isoformat()
                    avg_hr = _safe_float(row.get("avg_hr_session")) or _safe_float(row.get("avg_hr"))
                    resting_hr = _safe_float(row.get("resting_hr_bpm")) or _safe_float(row.get("min_hr"))
                    entries.append(
                        GarminDailyMetrics(
                            entry_id=str(uuid.uuid4()),
                            user_id=user.user_id,
                            metric_date=metric_date,
                            steps=_safe_int(row.get("steps")),
                            distance_km=_safe_float(row.get("distance_km")),
                            calories_kcal=_safe_float(row.get("calories_kcal")),
                            avg_hr_bpm=avg_hr,
                            resting_hr_bpm=resting_hr,
                            stress_score=_safe_float(row.get("avg_stress")),
                            sleep_score=_safe_float(row.get("sleep_score")),
                            sleep_efficiency=_safe_float(row.get("sleep_efficiency")),
                            sleep_duration_hours=_safe_float(row.get("sleep_duration_hours")),
                            avg_spo2=_safe_float(row.get("avg_sleep_spo2")) or _safe_float(row.get("avg_spo2")),
                            avg_respiration_awake=_safe_float(row.get("avg_respiration_awake")),
                            avg_respiration_sleep=_safe_float(row.get("avg_sleep_respiration")),
                            body_battery_avg=_safe_float(row.get("body_battery_avg")) or _safe_float(row.get("avg_body_battery")),
                            body_battery_charge=_safe_float(row.get("body_battery_charge")),
                            body_battery_drain=_safe_float(row.get("body_battery_drain")),
                            source="garmin_import_sidebar",
                            created_at=now_iso,
                        )
                    )
                if entries:
                    db = get_database()
                    db.save_garmin_daily_metrics(entries)
        except Exception as exc:  # noqa: BLE001
            if log_exception is not None:
                log_exception(_LOGGER, "Failed to persist sidebar Garmin metrics", exc)

    if not GARMIN_IMPORT_AVAILABLE:
        st.info("Garmin import module unavailable. Install fitparse and rerun.")
        return

    @st.cache_data(ttl=30, show_spinner=False)
    def _load_history(uid: str) -> pd.DataFrame:
        db = get_database()
        if hasattr(db, "get_garmin_daily_dataframe"):
            return db.get_garmin_daily_dataframe(uid, limit=180)  # type: ignore[attr-defined]
        if hasattr(db, "get_garmin_daily_metrics"):
            metrics = db.get_garmin_daily_metrics(uid, limit=180)  # type: ignore[attr-defined]
            if not metrics:
                return pd.DataFrame()
            return pd.DataFrame([m.to_dict() for m in metrics])
        return pd.DataFrame()

    try:
        df = _load_history(user.user_id)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Unable to load Garmin history: {exc}")
        return

    if df.empty and not hasattr(get_database(), "get_garmin_daily_metrics"):
        st.warning(
            "Wrist monitoring history requires the updated database methods. "
            "Please restart the app to reload the updated code, or run a fresh session."
        )
        return

    if df.empty:
        st.info("No Garmin wellness metrics stored yet. Upload a FIT/ZIP file in the Data tab.")
        return

    if "metric_date" in df.columns:
        df["metric_date"] = pd.to_datetime(df["metric_date"])
        df.sort_values("metric_date", ascending=False, inplace=True)

    latest = df.iloc[0]
    
    # Debug: show what values we have
    _LOGGER.info(
        "Wrist monitoring latest day: steps=%s, distance_km=%s, calories=%s, sleep_score=%s, stress=%s",
        latest.get("steps"), latest.get("distance_km"), latest.get("calories_kcal"),
        latest.get("sleep_score"), latest.get("stress_score"),
    )
    
    # Show latest day values prominently
    st.markdown(f"### 📅 Latest Day: {latest.get('metric_date', '—')}")
    col_a, col_b, col_c, col_d, col_e = st.columns(5)
    with col_a:
        steps_val = _safe_float(latest.get("steps"))
        st.metric("Steps", f"{steps_val:,.0f}" if steps_val else "—")
    with col_b:
        dist_val = _safe_float(latest.get("distance_km"))
        st.metric("Distance", f"{dist_val:.1f} km" if dist_val else "—")
    with col_c:
        cal_val = _safe_float(latest.get("calories_kcal"))
        st.metric("Calories", f"{cal_val:,.0f} kcal" if cal_val else "—")
    with col_d:
        sleep_val = _safe_float(latest.get("sleep_score"))
        st.metric("Sleep Score", f"{sleep_val:.0f}" if sleep_val else "—")
    with col_e:
        stress_val = _safe_float(latest.get("stress_score"))
        st.metric("Stress", f"{stress_val:.0f}" if stress_val else "—")
    
    st.markdown("---")

    # Summary indicators
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Days logged", f"{len(df)}")
    with col2:
        if "steps" in df.columns:
            steps_mean = df['steps'].mean()
            st.metric("Avg steps", f"{steps_mean:,.0f}" if pd.notna(steps_mean) else "—")
    with col3:
        if "sleep_score" in df.columns:
            sleep_mean = df['sleep_score'].mean()
            st.metric("Avg sleep score", f"{sleep_mean:.1f}" if pd.notna(sleep_mean) else "—")
    with col4:
        if "stress_score" in df.columns:
            stress_mean = df['stress_score'].mean()
            st.metric("Avg stress", f"{stress_mean:.1f}" if pd.notna(stress_mean) else "—")

    # Render gauges in organized sections
    st.markdown("### 🏃 Activity & Movement")
    cols = st.columns(3)
    activity_gauges = [
        ("steps", "Steps", latest.get("steps"), "steps"),
        ("distance_km", "Distance", latest.get("distance_km"), "distance_km"),
        ("calories_kcal", "Calories", latest.get("calories_kcal"), "calories_kcal"),
    ]
    for col, (_key, title, value, threshold_key) in zip(cols, activity_gauges):
        val = _safe_float(value)
        if val is None or pd.isna(val):
            with col:
                st.info(f"No {title} data")
            continue
        thresholds = get_gauge_thresholds(threshold_key)
        if not thresholds:
            continue
        option = build_two_ring_gauge(threshold_key, val, title=title, thresholds=thresholds)
        with col:
            render_echarts(option, height_px=280)
    
    st.markdown("### ❤️ Heart Rate & Stress")
    cols = st.columns(3)
    hr_gauges = [
        ("avg_hr_bpm", "Avg HR", latest.get("avg_hr_bpm"), "avg_hr_bpm"),
        ("resting_hr_bpm", "Resting HR", latest.get("resting_hr_bpm"), "resting_hr_bpm"),
        ("stress_score", "Stress", latest.get("stress_score"), "stress_score"),
    ]
    for col, (_key, title, value, threshold_key) in zip(cols, hr_gauges):
        val = _safe_float(value)
        if val is None or pd.isna(val):
            with col:
                st.info(f"No {title} data")
            continue
        thresholds = get_gauge_thresholds(threshold_key)
        if not thresholds:
            continue
        option = build_two_ring_gauge(threshold_key, val, title=title, thresholds=thresholds)
        with col:
            render_echarts(option, height_px=280)
    
    st.markdown("### 😴 Sleep & Recovery")
    cols = st.columns(3)
    sleep_gauges = [
        ("sleep_score", "Sleep Score", latest.get("sleep_score"), "sleep_score"),
        ("sleep_efficiency", "Sleep Efficiency", latest.get("sleep_efficiency"), "sleep_efficiency"),
        ("sleep_duration_hours", "Sleep Duration", latest.get("sleep_duration_hours"), "sleep_duration_hours"),
    ]
    for col, (_key, title, value, threshold_key) in zip(cols, sleep_gauges):
        val = _safe_float(value)
        if val is None or pd.isna(val):
            with col:
                st.info(f"No {title} data")
            continue
        thresholds = get_gauge_thresholds(threshold_key)
        if not thresholds:
            continue
        option = build_two_ring_gauge(threshold_key, val, title=title, thresholds=thresholds)
        with col:
            render_echarts(option, height_px=280)
    
    st.markdown("### 🫁 Respiration & SpO₂")
    cols = st.columns(3)
    resp_gauges = [
        ("avg_spo2", "SpO₂", latest.get("avg_spo2"), "spo2_pct"),
        ("avg_respiration_awake", "Resp Awake", latest.get("avg_respiration_awake"), "respiration_awake_bpm"),
        ("avg_respiration_sleep", "Resp Sleep", latest.get("avg_respiration_sleep"), "respiration_sleep_bpm"),
    ]
    for col, (_key, title, value, threshold_key) in zip(cols, resp_gauges):
        val = _safe_float(value)
        if val is None or pd.isna(val):
            with col:
                st.info(f"No {title} data")
            continue
        thresholds = get_gauge_thresholds(threshold_key)
        if not thresholds:
            continue
        option = build_two_ring_gauge(threshold_key, val, title=title, thresholds=thresholds)
        with col:
            render_echarts(option, height_px=280)
    
    st.markdown("### 🔋 Body Battery")
    cols = st.columns(3)
    bb_gauges = [
        ("body_battery_avg", "Avg Level", latest.get("body_battery_avg"), "body_battery_avg"),
        ("body_battery_charge", "Charged", latest.get("body_battery_charge"), "body_battery_charge"),
        ("body_battery_drain", "Drained", latest.get("body_battery_drain"), "body_battery_drain"),
    ]
    for col, (_key, title, value, threshold_key) in zip(cols, bb_gauges):
        val = _safe_float(value)
        if val is None or pd.isna(val):
            with col:
                st.info(f"No {title} data")
            continue
        thresholds = get_gauge_thresholds(threshold_key)
        if not thresholds:
            continue
        option = build_two_ring_gauge(threshold_key, val, title=title, thresholds=thresholds)
        with col:
            render_echarts(option, height_px=280)

    st.markdown("---")
    st.markdown("### 📊 Recent Daily Metrics")
    
    with st.expander("View all columns", expanded=False):
        preview_cols = [
            "metric_date",
            "steps",
            "distance_km",
            "calories_kcal",
            "avg_hr_bpm",
            "resting_hr_bpm",
            "stress_score",
            "sleep_score",
            "sleep_efficiency",
            "sleep_duration_hours",
            "avg_spo2",
            "avg_respiration_awake",
            "avg_respiration_sleep",
            "body_battery_avg",
            "body_battery_charge",
            "body_battery_drain",
        ]
        existing_cols = [c for c in preview_cols if c in df.columns]
        display_df = df[existing_cols].head(10).copy()
        
        # Format for better display
        if "metric_date" in display_df.columns:
            display_df["metric_date"] = display_df["metric_date"].dt.strftime("%Y-%m-%d")
        
        st.dataframe(
            display_df.reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )

# ---------------------------------------------------------------------------
# HRV History Section
# ---------------------------------------------------------------------------


def _render_hrv_history(user: UserProfile) -> None:
    """Render HRV measurement history."""
    st.markdown("## 💓 HRV Measurement History")
    
    try:
        with st.spinner("Loading HRV measurements..."):
            db = get_database()
            df = db.get_hrv_dataframe(user.user_id, limit=500, include_rr=False)
        
        if df.empty:
            st.info("No HRV measurements recorded. Import HRV data from the main analysis to populate this section.")
            return
        
        df = df.sort_values("measurement_date")
        if len(df) >= 500:
            st.caption("Showing the 500 most recent HRV measurements for faster loading.")
    
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
                    "garmin_daily_metrics": [g.to_dict() for g in db.get_garmin_daily_metrics(user.user_id)],
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


def _render_garmin_ingest(user: UserProfile) -> None:
    """Render Garmin Vivosmart 5 ingest to populate clinical gauges."""
    st.markdown("## ⌚ Wrist Monitoring (Vivosmart 5)")
    st.caption(
        "Upload a Garmin Vivosmart 5 FIT file or wellness ZIP export. "
        "Steps, distance, sleep score/efficiency, respiration (awake/sleep), "
        "SpO₂, stress, calories, and body battery will be stored in your profile history."
    )

    if not GARMIN_IMPORT_AVAILABLE:
        st.info("Garmin import module unavailable. Ensure fitparse is installed and garmin_import.py is present.")
        return

    uploaded = st.file_uploader(
        "Select FIT or Garmin wellness ZIP",
        type=["fit", "zip"],
        key=f"garmin_ingest_{user.user_id}",
        accept_multiple_files=False,
    )

    if uploaded is None:
        return

    suffix = Path(uploaded.name).suffix.lower()
    if suffix not in {".fit", ".zip"}:
        st.error("Unsupported file type. Please upload a .fit or Garmin wellness .zip export.")
        return

    with st.spinner("Parsing Garmin data..."):
        temp_path: Optional[Path] = None
        try:
            with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded.read())
                temp_path = Path(tmp.name)

            data = import_garmin_data(
                fit_path=temp_path if suffix == ".fit" else None,
                zip_path=temp_path if suffix == ".zip" else None,
            )
            daily_df = get_daily_physiology_summary(data)
        except Exception as exc:  # noqa: BLE001
            if log_exception is not None:
                log_exception(_LOGGER, "Garmin ingest failed", exc)
            st.error(f"Failed to parse Garmin file: {exc}")
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)
            return
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    if daily_df.empty:
        st.warning("No usable Garmin wellness metrics were found in the file.")
        return

    entries: List[GarminDailyMetrics] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # Also persist any pending sidebar ingestion if present
    pending_sidebar = st.session_state.pop("garmin_daily_pending", None)
    if pending_sidebar:
        pending_df = pd.DataFrame(pending_sidebar)
        if not pending_df.empty:
            daily_df = pd.concat([daily_df, pending_df], ignore_index=True)

    for _, row in daily_df.iterrows():
        day_val = row.get("date")
        if pd.isna(day_val):
            continue
        metric_date = pd.to_datetime(day_val).date().isoformat()
        avg_hr = _safe_float(row.get("avg_hr_session")) or _safe_float(row.get("avg_hr"))
        resting_hr = _safe_float(row.get("resting_hr_bpm")) or _safe_float(row.get("min_hr"))
        entries.append(
            GarminDailyMetrics(
                entry_id=str(uuid.uuid4()),
                user_id=user.user_id,
                metric_date=metric_date,
                steps=_safe_int(row.get("steps")),
                distance_km=_safe_float(row.get("distance_km")),
                calories_kcal=_safe_float(row.get("calories_kcal")),
                avg_hr_bpm=avg_hr,
                resting_hr_bpm=resting_hr,
                stress_score=_safe_float(row.get("avg_stress")),
                sleep_score=_safe_float(row.get("sleep_score")),
                sleep_efficiency=_safe_float(row.get("sleep_efficiency")),
                sleep_duration_hours=_safe_float(row.get("sleep_duration_hours")),
                avg_spo2=_safe_float(row.get("avg_sleep_spo2")) or _safe_float(row.get("avg_spo2")),
                avg_respiration_awake=_safe_float(row.get("avg_respiration_awake")),
                avg_respiration_sleep=_safe_float(row.get("avg_sleep_respiration")),
                body_battery_avg=_safe_float(row.get("body_battery_avg")) or _safe_float(row.get("avg_body_battery")),
                body_battery_charge=_safe_float(row.get("body_battery_charge")),
                body_battery_drain=_safe_float(row.get("body_battery_drain")),
                source=data.source,
                created_at=now_iso,
            )
        )

    try:
        db = get_database()
        db.save_garmin_daily_metrics(entries)
        st.cache_data.clear()
        st.success(f"Saved {len(entries)} day(s) of Garmin wellness metrics to the profile.")
        st.dataframe(
            daily_df.sort_values("date", ascending=False).head(5),
            use_container_width=True,
        )
    except Exception as exc:  # noqa: BLE001
        if log_exception is not None:
            log_exception(_LOGGER, "Failed to persist Garmin daily metrics", exc)
        st.error(f"Unable to save Garmin metrics: {exc}")


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
    )
    CLINICAL_PROFILE_AVAILABLE = True
except ImportError:
    CLINICAL_PROFILE_AVAILABLE = False

# Import Polar AccessLink module if available
try:
    from polar_accesslink import (
        PolarAccessLinkClient,
        polar_accesslink_available,
        fetch_polar_vo2max,
        save_manual_vo2max,
    )
    POLAR_MODULE_AVAILABLE = True
except ImportError:
    POLAR_MODULE_AVAILABLE = False
    def polar_accesslink_available() -> bool:  # type: ignore[misc]
        return False
    def fetch_polar_vo2max() -> None:  # type: ignore[misc]
        return None


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
    
    with st.expander("📊 Exploration Medical Analytics", expanded=False):
        _render_exploration_medical_analytics(user)


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


@_fragment_if_available
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
    
    # VO2max handling (manual + optional Polar AccessLink with history)
    vo2_default = float(user.vo2max_ml_kg_min or 38.0)
    st.markdown("##### 🫁 VO2max Source")
    
    # Check for latest VO2max from history
    latest_vo2_entry = None
    polar_client = None
    if POLAR_MODULE_AVAILABLE and DATABASE_AVAILABLE:
        try:
            polar_client = PolarAccessLinkClient(user.user_id)
            latest_vo2_entry = polar_client.get_latest_vo2max()
            if latest_vo2_entry:
                vo2_default = latest_vo2_entry.vo2max_ml_kg_min
        except Exception:
            pass  # Continue with default
    
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
        # Check if Polar is configured (env vars or stored credentials)
        has_polar = polar_accesslink_available()
        has_stored_creds = polar_client.has_credentials() if polar_client else False
        
        if has_polar or has_stored_creds:
            st.caption("✅ Polar AccessLink configured")
            if st.button("🔄 Sync from Polar", key=f"sync_polar_vo2_{user.user_id}"):
                if polar_client:
                    with st.spinner("Syncing from Polar Flow..."):
                        result = polar_client.sync_vo2max()
                    if result.success and result.vo2max:
                        st.session_state[polar_cache_key] = result.vo2max
                        polar_cached = result.vo2max
                        st.success(
                            f"VO2max: **{result.vo2max:.1f}** mL/kg/min "
                            f"({result.fitness_class or 'N/A'})"
                        )
                    elif result.success:
                        st.info(result.message)
                    else:
                        st.warning(f"Sync failed: {result.error or 'Unknown error'}")
                else:
                    # Fallback to simple fetch
                    polar_value = fetch_polar_vo2max()
                    if polar_value:
                        st.session_state[polar_cache_key] = polar_value
                        polar_cached = polar_value
                        st.success(f"Retrieved VO2max {polar_value:.1f} mL/kg/min")
                    else:
                        st.warning("Polar AccessLink did not return a VO2max value.")
            
            use_polar_override = st.checkbox(
                "Use synced value",
                value=bool(polar_cached or latest_vo2_entry),
                help="Use the most recent synced or stored VO2max value.",
                key=f"use_polar_vo2_{user.user_id}",
            )
        else:
            st.caption("ℹ️ Set POLAR_ACCESSLINK_TOKEN & POLAR_ACCESSLINK_USER_ID to enable.")
        
        # Save manual entry button
        if st.button("💾 Save Manual Entry", key=f"save_manual_vo2_{user.user_id}"):
            if POLAR_MODULE_AVAILABLE:
                try:
                    save_manual_vo2max(
                        user_id=user.user_id,
                        vo2max=vo2_manual,
                        notes="Manual entry from NASA Nutrition Calculator",
                    )
                    st.success(f"Saved VO2max {vo2_manual:.1f} mL/kg/min to history")
                except Exception as e:
                    st.error(f"Failed to save: {e}")
    
    # Determine effective VO2max
    effective_vo2 = vo2_manual
    if use_polar_override:
        if polar_cached:
            effective_vo2 = float(polar_cached)
        elif latest_vo2_entry:
            effective_vo2 = latest_vo2_entry.vo2max_ml_kg_min
    
    # Show VO2max history if available
    if polar_client and POLAR_MODULE_AVAILABLE:
        vo2_history = polar_client.get_vo2max_history(limit=10)
        if len(vo2_history) > 1:
            with st.expander("📈 VO2max History", expanded=False):
                history_data = [
                    {
                        "Date": entry.measurement_date[:10] if entry.measurement_date else "N/A",
                        "VO2max": f"{entry.vo2max_ml_kg_min:.1f}",
                        "Source": entry.source.title(),
                        "Class": entry.polar_fitness_class or "—",
                    }
                    for entry in vo2_history
                ]
                st.dataframe(history_data, use_container_width=True, hide_index=True)
    
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
        # Determine source description
        if use_polar_override and polar_cached:
            vo2_source = "Polar AccessLink sync"
        elif use_polar_override and latest_vo2_entry:
            vo2_source = f"History ({latest_vo2_entry.source.title()})"
        else:
            vo2_source = "Manual entry"
        st.metric(
            "VO2max used",
            f"{effective_vo2:.1f} mL/kg/min",
            help=vo2_source,
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
    
    form_key = f"body_composition_form_{user.user_id}"
    with st.form(form_key, clear_on_submit=False):
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
        
        submitted = st.form_submit_button(
            "💾 Save Body Composition",
            use_container_width=True,
        )
        
        if submitted:
            st.success("✅ Body composition saved!")
            # TODO: Save to database when schema is connected


def _render_medical_history_summary(user: UserProfile) -> None:
    """Render medical history summary pulling from both profile and medical_history table."""
    st.markdown("#### 📋 Medical History Summary")
    
    # Load latest medical record from database for richer context
    @st.cache_data(ttl=30, show_spinner=False)
    def _load_latest_record(uid: str) -> Dict[str, Any]:
        try:
            db = get_database()
            rows = db.get_medical_history(uid, limit=1)
            return rows[0] if rows else {}
        except Exception:
            return {}
    
    latest_record = _load_latest_record(user.user_id)
    
    # Show current conditions from user profile
    if user.medical_conditions:
        st.write("**Current Conditions:**")
        for condition in user.medical_conditions:
            st.write(f"• {condition}")
    
    if user.medications:
        st.write("**Current Medications:**")
        for med in user.medications:
            st.write(f"• {med}")
    
    # Show most recent exploration medical record summary
    if latest_record:
        st.markdown("---")
        st.markdown("**Latest Exploration Medical Record:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            mission = latest_record.get("mission_profile", "—")
            day = latest_record.get("mission_day", "—")
            st.metric("Mission", f"{mission} D{day}")
        with col2:
            eva_status = latest_record.get("eva_status", "—")
            st.metric("EVA Status", eva_status)
        with col3:
            rad = latest_record.get("radiation_dose_msv", 0.0)
            st.metric("Radiation (mSv)", f"{rad:.1f}")
        
        # Chronic/acute flags
        chronic_list = latest_record.get("chronic_conditions", [])
        acute_list = latest_record.get("acute_symptoms", [])
        if chronic_list:
            st.caption(f"🩺 Chronic: {', '.join(chronic_list)}")
        if acute_list:
            st.caption(f"⚠️ Acute (24h): {', '.join(acute_list)}")
        st.caption(f"_Updated: {latest_record.get('updated_at', '—')}_")
    else:
        if not user.medical_conditions and not user.medications:
            st.info("No medical history recorded. Edit your profile or use the Exploration Medical Record form.")


@st.cache_data(ttl=60, show_spinner=False)
def _load_medical_history_dataframe(user_id: str) -> pd.DataFrame:
    """Load exploration medical history entries as a typed DataFrame."""
    if not user_id:
        return pd.DataFrame()
    try:
        db = get_database()
        records = db.get_medical_history(user_id, limit=180)
    except Exception as exc:
        _LOGGER.warning("Unable to load exploration medical history for %s: %s", user_id, exc)
        return pd.DataFrame()
    if not records:
        return pd.DataFrame()
    history_df = pd.DataFrame(records)
    numeric_columns = [
        "mission_day",
        "radiation_dose_msv",
        "eva_hours_72h",
        "days_since_last_eva",
        "confinement_stress",
        "workload_rating",
        "sleep_hours",
        "sleep_quality",
        "exercise_minutes",
        "hydration_liters",
        "caloric_intake",
        "comm_delay_min",
    ]
    for column in numeric_columns:
        if column in history_df.columns:
            history_df[column] = pd.to_numeric(history_df[column], errors="coerce")
    if "updated_at" in history_df.columns:
        history_df["updated_at"] = pd.to_datetime(history_df["updated_at"], errors="coerce")
        history_df.sort_values("updated_at", inplace=True)
    elif "mission_day" in history_df.columns:
        history_df.sort_values("mission_day", inplace=True)
    history_df.reset_index(drop=True, inplace=True)
    return history_df


def _compute_radiation_rate(history_df: pd.DataFrame) -> Optional[float]:
    """Compute average cumulative radiation increase per mission day."""
    if history_df.empty or not {"mission_day", "radiation_dose_msv"}.issubset(history_df.columns):
        return None
    valid = history_df.dropna(subset=["mission_day", "radiation_dose_msv"]).sort_values("mission_day")
    if len(valid) < 2:
        return None
    start_day = float(valid["mission_day"].iloc[0])
    end_day = float(valid["mission_day"].iloc[-1])
    if start_day == end_day:
        return None
    start_dose = float(valid["radiation_dose_msv"].iloc[0])
    end_dose = float(valid["radiation_dose_msv"].iloc[-1])
    return (end_dose - start_dose) / (end_day - start_day)


def _build_frequency_df(values: Sequence[Any], top_n: int = 5) -> pd.DataFrame:
    """Aggregate frequency counts for list-like history fields."""
    counts: Counter[str] = Counter()
    for entry in values:
        if entry is None or (isinstance(entry, float) and np.isnan(entry)):
            continue
        if isinstance(entry, (list, tuple, set)):
            for item in entry:
                text = str(item).strip()
                if text:
                    counts[text] += 1
        elif isinstance(entry, str):
            text = entry.strip()
            if text:
                counts[text] += 1
        else:
            text = str(entry).strip()
            if text:
                counts[text] += 1
    if not counts:
        return pd.DataFrame(columns=["Label", "Count"])
    most_common = counts.most_common(max(1, top_n))
    return pd.DataFrame(most_common, columns=["Label", "Count"])


def _render_exploration_medical_analytics(user: UserProfile) -> None:
    """Render exploration medical analytics dashboard with aggregate indicators."""
    st.markdown("#### 📊 Exploration Medical Analytics Dashboard")
    history_df = _load_medical_history_dataframe(user.user_id)
    if history_df.empty:
        st.info("Log at least one exploration medical record to unlock analytics.")
        return
    latest_entry = history_df.iloc[-1]

    # Radiation exposure
    st.markdown("##### ☢️ Radiation Exposure")
    rad_series = history_df["radiation_dose_msv"].dropna() if "radiation_dose_msv" in history_df.columns else pd.Series(dtype=float)
    rad_limit = 1000.0  # NASA career limit guideline for deep-space crews
    if rad_series.empty:
        st.warning("No radiation dose entries recorded yet.")
    else:
        max_rad = float(rad_series.max())
        median_rad = float(rad_series.median())
        rad_rate = _compute_radiation_rate(history_df)
        remaining = max(rad_limit - max_rad, 0.0)
        col_r1, col_r2, col_r3 = st.columns(3)
        col_r1.metric(
            "Max cumulative dose",
            f"{max_rad:.1f} mSv",
            delta=f"{remaining:.1f} mSv below NASA limit",
        )
        col_r2.metric(
            "Median logged dose",
            f"{median_rad:.1f} mSv",
            delta=None,
        )
        col_r3.metric(
            "Daily accumulation",
            f"{rad_rate:.2f} mSv/day" if rad_rate is not None else "—",
            delta=None if rad_rate is None else "Avg change per mission day",
        )
        progress_value = min(max_rad / rad_limit, 1.0)
        st.progress(progress_value)
        st.caption(f"{progress_value * 100:.1f}% of NASA 1000 mSv career guideline")
        if {"mission_day"}.issubset(history_df.columns):
            chart_df = history_df.dropna(subset=["mission_day", "radiation_dose_msv"]).copy()
            if not chart_df.empty:
                chart_df = chart_df.sort_values("mission_day").set_index("mission_day")
                chart_df.rename(columns={"radiation_dose_msv": "Radiation (mSv)"}, inplace=True)
                st.line_chart(chart_df[["Radiation (mSv)"]])

    # EVA workload
    st.markdown("##### 🧑‍🚀 EVA Workload")
    eva_series = history_df["eva_hours_72h"].dropna() if "eva_hours_72h" in history_df.columns else pd.Series(dtype=float)
    avg_eva = float(eva_series.mean()) if not eva_series.empty else None
    peak_eva = float(eva_series.max()) if not eva_series.empty else None
    days_since_last = latest_entry.get("days_since_last_eva")
    days_since_last_display = (
        f"{int(days_since_last)} d" if days_since_last is not None and not np.isnan(days_since_last) else "—"
    )
    col_e1, col_e2, col_e3 = st.columns(3)
    col_e1.metric("Avg EVA hrs (72h)", f"{avg_eva:.1f} h" if avg_eva is not None else "—")
    col_e2.metric("Peak EVA load", f"{peak_eva:.1f} h" if peak_eva is not None else "—", delta="Rolling 72h window")
    col_e3.metric("Days since last EVA", days_since_last_display)
    if "eva_status" in history_df.columns:
        eva_status_counts = history_df["eva_status"].dropna().value_counts().head(4)
        if not eva_status_counts.empty:
            st.bar_chart(eva_status_counts.rename("EVA Clearance States"))

    # Stress and behavioral indicators
    st.markdown("##### 🧠 Stress & Behavioral Indicators")
    stress_series = history_df["confinement_stress"].dropna() if "confinement_stress" in history_df.columns else pd.Series(dtype=float)
    workload_series = history_df["workload_rating"].dropna() if "workload_rating" in history_df.columns else pd.Series(dtype=float)
    sleep_series = history_df["sleep_hours"].dropna() if "sleep_hours" in history_df.columns else pd.Series(dtype=float)
    recent_window = history_df.tail(min(len(history_df), 5))
    recent_stress = (
        float(recent_window["confinement_stress"].dropna().mean())
        if "confinement_stress" in recent_window.columns and not recent_window["confinement_stress"].dropna().empty
        else None
    )
    baseline_stress = float(stress_series.mean()) if not stress_series.empty else None
    stress_delta = (
        None if baseline_stress is None or recent_stress is None else recent_stress - baseline_stress
    )
    recent_workload = (
        float(recent_window["workload_rating"].dropna().mean())
        if "workload_rating" in recent_window.columns and not recent_window["workload_rating"].dropna().empty
        else None
    )
    workload_delta = (
        None
        if workload_series.empty or recent_workload is None
        else recent_workload - float(workload_series.mean())
    )
    recent_sleep = (
        float(recent_window["sleep_hours"].dropna().mean())
        if "sleep_hours" in recent_window.columns and not recent_window["sleep_hours"].dropna().empty
        else None
    )
    col_s1, col_s2, col_s3 = st.columns(3)
    col_s1.metric(
        "Confinement stress (last 5)",
        f"{recent_stress:.1f}/10" if recent_stress is not None else "—",
        delta=f"{stress_delta:+.1f} vs avg" if stress_delta is not None else None,
    )
    col_s2.metric(
        "Workload rating (last 5)",
        f"{recent_workload:.1f}/10" if recent_workload is not None else "—",
        delta=f"{workload_delta:+.1f} vs avg" if workload_delta is not None else None,
    )
    col_s3.metric(
        "Sleep hours (last 5)",
        f"{recent_sleep:.1f} h" if recent_sleep is not None else "—",
        delta=None,
    )
    symptom_df = _build_frequency_df(
        history_df["acute_symptoms"].tolist() if "acute_symptoms" in history_df.columns else [],
        top_n=5,
    )
    behavior_df = _build_frequency_df(
        history_df["behavioral_flags"].tolist() if "behavioral_flags" in history_df.columns else [],
        top_n=5,
    )
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if symptom_df.empty:
            st.caption("No acute symptom trends logged yet.")
        else:
            st.caption("Top acute symptoms (all-time)")
            st.dataframe(symptom_df, use_container_width=True, hide_index=True)
    with col_b2:
        if behavior_df.empty:
            st.caption("No behavioral flags logged yet.")
        else:
            st.caption("Behavioral health flags (frequency)")
            st.dataframe(behavior_df, use_container_width=True, hide_index=True)


@_fragment_if_available
def _render_medical_record_form(user: UserProfile) -> None:
    """Render NASA-style exploration medical record entry form.
    
    Structured per Exploration Medical Capability (ExMC) and Earth-Independent
    Medical Operations (EIMO) framework for autonomous deep-space missions.
    Reference: https://ntrs.nasa.gov/citations/20230015831 (ExMC AsMA 2024).
    """
    st.caption(
        "Structured per NASA Exploration Medical Capability (ExMC) and the "
        "Earth-Independent Medical Operations (EIMO) paradigm for deep-space "
        "autonomy. Reference: Lehnhardt et al., NASA Technical Reports Server, "
        "2023 (DOI: 10.1109/OJEMB.2023.3255513)."
    )
    
    # -------------------------------------------------------------------------
    # Helper: Safe index lookup for selectbox (resilient to schema changes)
    # -------------------------------------------------------------------------
    def _safe_selectbox_index(stored_value: Any, options: list, default_index: int = 0) -> int:
        """Return index of stored_value in options, or default_index if not found."""
        if stored_value in options:
            return options.index(stored_value)
        if stored_value is not None:
            _LOGGER.debug(
                "Selectbox schema migration: stored value %r not in options, using default index %d",
                stored_value,
                default_index,
            )
        return default_index
    
    try:
        db = get_database()
        history = db.get_medical_history(user.user_id, limit=25)
        _LOGGER.debug("Loaded %d medical history entries for user %s", len(history), user.user_id)
    except Exception as exc:
        _LOGGER.warning("Unable to load medical history for user %s: %s", user.user_id, exc)
        st.error(f"Unable to load medical history: {exc}")
        history = []
    latest = history[0] if history else {}
    
    # Mission profiles aligned with NASA EIMO planning horizons
    mission_options = {
        "LEO-ISS": "ISS / Low-Earth Orbit (continuous ground support)",
        "LUNAR-SLS": "Artemis lunar sortie (6–30 days, limited EIMO)",
        "GATEWAY-30": "Gateway cislunar (30-day increments)",
        "LUNAR-SURFACE-90": "Lunar surface sustained (up to 90 days)",
        "MARS-TRANSIT-180": "Mars transit (180+ days, high EIMO)",
        "MARS-SURFACE-500": "Mars surface (500+ days, full autonomy)",
        "ANALOG-CHAPEA": "CHAPEA / Mars Dune Alpha analog",
        "ANALOG-HERA": "HERA campaign (45-day isolation)",
        "CUSTOM": "Custom exploration profile",
    }
    habitats = ["ISS", "Gateway", "Starship HLS", "Mars Dune Alpha", "HERA", "NEEMO", "Lunar Hab", "Custom"]
    crew_roles = [
        "Flight Surgeon",
        "Crew Medical Officer (CMO)",
        "Commander",
        "Pilot",
        "Mission Specialist",
        "Payload Specialist",
        "Research Scientist",
    ]
    eva_status_options = ["Cleared", "Cleared with Restriction", "No EVA", "Post-EVA Recovery"]
    space_weather_alerts = ["None", "Watch", "Warning", "Storm In Progress", "Post-Event Monitoring"]
    # Chronic condition categories per HRP/ExMC risk taxonomy
    chronic_condition_options = [
        "Cardiovascular (SANS, arrhythmia)",
        "Respiratory (atelectasis, hypoxia history)",
        "Metabolic (glucose, bone loss)",
        "Neurological (vestibular, ICP)",
        "Psychological (anxiety, depression, adjustment)",
        "Musculoskeletal (muscle atrophy, back pain)",
        "Renal/Urologic (nephrolithiasis)",
        "Dermatologic (rash, infection)",
        "Ophthalmologic (SANS-related)",
        "Immunologic (allergy, infection susceptibility)",
    ]
    # Acute symptoms expanded per ExMC clinical decision support categories
    acute_symptom_options = [
        "Headache",
        "Dizziness / Vertigo",
        "Visual change (blur, scotoma)",
        "Nausea / Vomiting",
        "Abdominal pain",
        "Chest pain / Palpitations",
        "Dyspnea",
        "Musculoskeletal pain (specify)",
        "Skin lesion / Wound",
        "Sleep disruption (insomnia / hypersomnia)",
        "Cognitive change (attention, memory)",
        "Mood change (irritability, apathy)",
        "Fever / Chills",
        "Urinary symptoms",
    ]
    behavioral_flags = [
        "Confinement stress",
        "Team friction / Interpersonal conflict",
        "Mood dysregulation",
        "Cognitive slowing / Attention deficit",
        "Motivation dip / Amotivation",
        "Sleep-wake cycle disruption",
        "Isolation distress",
        "Homesickness / Nostalgia",
    ]
    # EIMO autonomy level (per Levin et al. 2023)
    autonomy_levels = [
        "Ground-Supported (real-time telemedicine)",
        "Delayed Support (2–20 min latency)",
        "Limited Autonomy (hours to days delay)",
        "Full EIMO (crew autonomous)",
    ]
    
    form_key = f"exploration_medical_record_form_{user.user_id}"
    with st.form(form_key, clear_on_submit=False):
        # ─────────────────────────────────────────────────────────────────────
        # Section 1: Mission Context (EIMO Phase & Habitat)
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("##### 🚀 Mission Context")
        col_a, col_b, col_c = st.columns(3)
        mission_keys = list(mission_options.keys())
        with col_a:
            mission_profile = st.selectbox(
                "Mission profile",
                options=mission_keys,
                format_func=lambda key: mission_options.get(key, key),
                index=_safe_selectbox_index(latest.get("mission_profile"), mission_keys, 0),
            )
            mission_day = st.number_input(
                "Mission day",
                min_value=0,
                max_value=999,
                value=int(latest.get("mission_day", 1)),
                step=1,
            )
            habitat = st.selectbox(
                "Habitat / Analog site",
                options=habitats,
                index=_safe_selectbox_index(latest.get("habitat"), habitats, 0),
            )
        with col_b:
            crew_role = st.selectbox(
                "Crew role",
                options=crew_roles,
                index=_safe_selectbox_index(latest.get("crew_role"), crew_roles, 0),
            )
            autonomy_level = st.selectbox(
                "EIMO autonomy level",
                options=autonomy_levels,
                index=_safe_selectbox_index(latest.get("autonomy_level"), autonomy_levels, 0),
                help="Earth-Independent Medical Operations autonomy classification",
            )
            comm_delay_min = st.number_input(
                "Comm delay (min, one-way)",
                min_value=0.0,
                max_value=25.0,
                value=float(latest.get("comm_delay_min", 0.0)),
                step=0.5,
                help="Mars averages 3–22 min one-way; Gateway ~1.3 s",
            )
        with col_c:
            eva_status = st.selectbox(
                "EVA clearance",
                options=eva_status_options,
                index=_safe_selectbox_index(latest.get("eva_status"), eva_status_options, 0),
            )
            eva_hours = st.number_input(
                "EVA hours (last 72h)",
                min_value=0.0,
                max_value=36.0,
                value=float(latest.get("eva_hours_72h", 0.0)),
                step=0.5,
            )
            days_since_last_eva = st.number_input(
                "Days since last EVA",
                min_value=0,
                max_value=365,
                value=int(latest.get("days_since_last_eva", 0)),
                step=1,
            )
        
        # ─────────────────────────────────────────────────────────────────────
        # Section 2: Radiation & Space Weather (ExMC risk domain)
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("##### ☢️ Radiation & Space Weather")
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            radiation_dose = st.number_input(
                "Cumulative dose (mSv)",
                min_value=0.0,
                max_value=1200.0,
                value=float(latest.get("radiation_dose_msv", 0.0)),
                step=0.5,
                help="Career limit ~1000 mSv (NASA); Mars transit ~300 mSv per transit",
            )
        with col_r2:
            space_weather = st.selectbox(
                "Space-weather alert level",
                options=space_weather_alerts,
                index=_safe_selectbox_index(latest.get("space_weather_alert"), space_weather_alerts, 0),
            )
        with col_r3:
            galactic_cosmic_ray = st.checkbox(
                "GCR exposure concern",
                value=latest.get("gcr_concern", False),
                help="Galactic Cosmic Ray monitoring for deep-space missions",
            )
        
        # ─────────────────────────────────────────────────────────────────────
        # Section 3: Health Status (Chronic / Acute / Behavioral)
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("##### 🩺 Health Status")
        
        # Helper to filter stored defaults against current options (resilient to schema changes)
        def _safe_multiselect_default(stored: list, options: list) -> list:
            """Return only stored values that exist in current options."""
            if not stored:
                return []
            valid = [v for v in stored if v in options]
            # Log migration warnings for stale values
            stale = set(stored) - set(valid)
            if stale:
                _LOGGER.debug(
                    "Multiselect schema migration: dropped stale defaults %s",
                    stale,
                )
            return valid
        
        chronic_conditions = st.multiselect(
            "Chronic condition log (HRP risk categories)",
            options=chronic_condition_options,
            default=_safe_multiselect_default(
                latest.get("chronic_conditions", []),
                chronic_condition_options,
            ),
        )
        acute_symptoms = st.multiselect(
            "Acute symptoms (last 24h)",
            options=acute_symptom_options,
            default=_safe_multiselect_default(
                latest.get("acute_symptoms", []),
                acute_symptom_options,
            ),
        )
        behavioral_state = st.multiselect(
            "Behavioral health notes",
            options=behavioral_flags,
            default=_safe_multiselect_default(
                latest.get("behavioral_flags", []),
                behavioral_flags,
            ),
        )
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            confinement_stress = st.slider(
                "Confinement stress (1–10)",
                min_value=1,
                max_value=10,
                value=int(latest.get("confinement_stress", 3)),
            )
        with col_h2:
            workload_rating = st.slider(
                "Workload rating (1–10)",
                min_value=1,
                max_value=10,
                value=int(latest.get("workload_rating", 5)),
                help="NASA TLX-style subjective workload",
            )
        
        # ─────────────────────────────────────────────────────────────────────
        # Section 4: Countermeasures & Life Support
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("##### 🏋️ Countermeasures & Life Support")
        col_d, col_e, col_f = st.columns(3)
        with col_d:
            sleep_hours = st.number_input(
                "Sleep (last 24h, hours)",
                min_value=0.0,
                max_value=14.0,
                value=float(latest.get("sleep_hours", 7.0)),
                step=0.25,
            )
            sleep_quality = st.slider(
                "Sleep quality (1–5)",
                min_value=1,
                max_value=5,
                value=int(latest.get("sleep_quality", 3)),
            )
        with col_e:
            exercise_minutes = st.number_input(
                "Countermeasure exercise (min/day)",
                min_value=0.0,
                max_value=300.0,
                value=float(latest.get("exercise_minutes", 120.0)),
                step=5.0,
                help="ISS target ~2 h/day resistive + aerobic",
            )
            _exercise_modalities = ["ARED", "T2 / COLBERT", "CEVIS", "Combined", "Limited", "None"]
            exercise_type = st.selectbox(
                "Primary exercise modality",
                options=_exercise_modalities,
                index=_safe_selectbox_index(latest.get("exercise_type"), _exercise_modalities, 3),
            )
        with col_f:
            hydration_liters = st.number_input(
                "Water intake (L/day)",
                min_value=0.0,
                max_value=10.0,
                value=float(latest.get("hydration_liters", 3.8)),
                step=0.1,
            )
            caloric_intake = st.number_input(
                "Caloric intake (kcal/day)",
                min_value=0,
                max_value=5000,
                value=int(latest.get("caloric_intake", 2500)),
                step=50,
            )
        
        # ─────────────────────────────────────────────────────────────────────
        # Section 5: Medical Inventory & Logistics
        # ─────────────────────────────────────────────────────────────────────
        st.markdown("##### 📦 Medical Inventory & Logistics")
        col_inv1, col_inv2 = st.columns(2)
        with col_inv1:
            _inventory_status_options = ["Nominal", "Monitor", "Low Stock", "Critical Shortage"]
            inventory_alert = st.selectbox(
                "Medical inventory status",
                options=_inventory_status_options,
                index=_safe_selectbox_index(latest.get("inventory_alert"), _inventory_status_options, 0),
            )
        with col_inv2:
            resupply_days = st.number_input(
                "Days until next resupply",
                min_value=0,
                max_value=999,
                value=int(latest.get("resupply_days", 0)),
                step=1,
                help="0 = N/A or continuous resupply (LEO)",
            )
        
        notes = st.text_area(
            "Operational / Clinical notes",
            value=str(latest.get("notes", "")),
            height=100,
        )
        update_latest = st.checkbox(
            "Update latest entry instead of creating a new record",
            value=False,
        )
        
        submitted = st.form_submit_button("💾 Save Exploration Medical Record")
        if submitted:
            if not _should_process_form_submission(form_key):
                st.info("Processing previous submission... please wait.")
                return
            record = {
                # Mission Context
                "mission_profile": mission_profile,
                "mission_day": mission_day,
                "habitat": habitat,
                "crew_role": crew_role,
                "autonomy_level": autonomy_level,
                "comm_delay_min": comm_delay_min,
                "eva_status": eva_status,
                "eva_hours_72h": eva_hours,
                "days_since_last_eva": days_since_last_eva,
                # Radiation & Space Weather
                "radiation_dose_msv": radiation_dose,
                "space_weather_alert": space_weather,
                "gcr_concern": galactic_cosmic_ray,
                # Health Status
                "chronic_conditions": chronic_conditions,
                "acute_symptoms": acute_symptoms,
                "behavioral_flags": behavioral_state,
                "confinement_stress": confinement_stress,
                "workload_rating": workload_rating,
                # Countermeasures
                "sleep_hours": sleep_hours,
                "sleep_quality": sleep_quality,
                "exercise_minutes": exercise_minutes,
                "exercise_type": exercise_type,
                "hydration_liters": hydration_liters,
                "caloric_intake": caloric_intake,
                # Inventory
                "inventory_alert": inventory_alert,
                "resupply_days": resupply_days,
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
            st.markdown("---")
            _render_garmin_metrics_history(current_user)
        
        with tab_hrv:
            _render_hrv_history(current_user)
        
        with tab_data:
            _render_garmin_ingest(current_user)
            st.markdown("---")
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

