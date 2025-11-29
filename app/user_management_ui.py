"""
Multi-User Management UI for HRV Analysis Platform.

Provides Streamlit interface for:
- User selection and authentication
- Profile creation and editing
- Clinical scale assessments
- Data export/import
- Longitudinal statistics visualization

Author: Dr. Diego Leonel Malpica Hincapié, MD
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from .user_database import (
    UserProfile,
    ClinicalScales,
    HRVMeasurement,
    UserDatabase,
    get_database,
    get_database_path,
)

# Session state keys
SESSION_USER_ID = "current_user_id"
SESSION_USER_PROFILE = "current_user_profile"


# ---------------------------------------------------------------------------
# Session Management
# ---------------------------------------------------------------------------

def get_current_user() -> Optional[UserProfile]:
    """Get the currently logged-in user from session state."""
    return st.session_state.get(SESSION_USER_PROFILE)


def set_current_user(profile: Optional[UserProfile]) -> None:
    """Set the current user in session state."""
    if profile:
        st.session_state[SESSION_USER_ID] = profile.user_id
        st.session_state[SESSION_USER_PROFILE] = profile
    else:
        st.session_state.pop(SESSION_USER_ID, None)
        st.session_state.pop(SESSION_USER_PROFILE, None)


def is_user_logged_in() -> bool:
    """Check if a user is logged in."""
    return SESSION_USER_ID in st.session_state


# ---------------------------------------------------------------------------
# User Selection Widget
# ---------------------------------------------------------------------------

def render_user_selector() -> Optional[UserProfile]:
    """Render user selection/login widget in sidebar.
    
    Returns:
        Selected UserProfile or None.
    """
    db = get_database()
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("👤 User Profile")
    
    # Check if user is logged in
    current_user = get_current_user()
    
    if current_user:
        # Show current user info
        st.sidebar.success(f"**{current_user.full_name}**")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("📝 Edit", key="edit_profile_btn", use_container_width=True):
                st.session_state["show_profile_editor"] = True
        with col2:
            if st.button("🚪 Logout", key="logout_btn", use_container_width=True):
                set_current_user(None)
                st.rerun()
        
        # Quick stats
        hrv_count = len(db.get_hrv_history(current_user.user_id, limit=10000))
        scale_count = len(db.get_clinical_scales_history(current_user.user_id, limit=10000))
        
        st.sidebar.caption(f"📊 {hrv_count} HRV measurements | 📋 {scale_count} assessments")
        
        return current_user
    
    # User selection/creation
    users = db.list_users()
    
    if users:
        # Select existing user
        user_options = {u.full_name: u for u in users}
        user_options["➕ Create New User"] = None
        
        selected = st.sidebar.selectbox(
            "Select User",
            options=list(user_options.keys()),
            key="user_selector"
        )
        
        if selected == "➕ Create New User":
            if st.sidebar.button("Create Profile", key="create_profile_btn", use_container_width=True):
                st.session_state["show_profile_creator"] = True
        else:
            profile = user_options[selected]
            if profile and st.sidebar.button("Login", key="login_btn", use_container_width=True):
                set_current_user(profile)
                st.rerun()
    else:
        st.sidebar.info("No users found. Create your first profile!")
        if st.sidebar.button("➕ Create Profile", key="create_first_profile", use_container_width=True):
            st.session_state["show_profile_creator"] = True
    
    return None


# ---------------------------------------------------------------------------
# Profile Creator/Editor Forms
# ---------------------------------------------------------------------------

def render_profile_creator() -> None:
    """Render new user profile creation form."""
    if not st.session_state.get("show_profile_creator", False):
        return
    
    st.markdown("## 👤 Create New User Profile")
    st.markdown("Fill out your information to enable personalized calculations and tracking.")
    
    with st.form("new_profile_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Basic Information")
            username = st.text_input("Username*", help="Unique identifier for login")
            full_name = st.text_input("Full Name*")
            email = st.text_input("Email")
            
            dob = st.date_input(
                "Date of Birth",
                value=None,
                min_value=date(1920, 1, 1),
                max_value=date.today(),
            )
            
            sex = st.selectbox("Sex", ["", "male", "female", "other"])
        
        with col2:
            st.markdown("### Biometrics")
            height_cm = st.number_input("Height (cm)", min_value=100.0, max_value=250.0, value=170.0, step=0.5)
            weight_kg = st.number_input("Weight (kg)", min_value=30.0, max_value=300.0, value=70.0, step=0.5)
            resting_hr = st.number_input("Resting Heart Rate (bpm)", min_value=30, max_value=120, value=60)
            max_hr = st.number_input("Max Heart Rate (bpm, 0=estimate)", min_value=0, max_value=250, value=0)
            vo2max = st.number_input("VO2max (ml/kg/min, 0=unknown)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
        
        st.markdown("### Lifestyle Factors")
        col3, col4 = st.columns(2)
        
        with col3:
            occupation = st.text_input("Occupation")
            activity_level = st.selectbox(
                "Activity Level",
                ["", "sedentary", "light", "moderate", "active", "very_active"],
                format_func=lambda x: {
                    "": "Select...",
                    "sedentary": "Sedentary (desk job, little exercise)",
                    "light": "Light (light exercise 1-3 days/week)",
                    "moderate": "Moderate (moderate exercise 3-5 days/week)",
                    "active": "Active (hard exercise 6-7 days/week)",
                    "very_active": "Very Active (athlete/physical job)"
                }.get(x, x)
            )
        
        with col4:
            smoking = st.selectbox("Smoking Status", ["", "never", "former", "current"])
            alcohol = st.selectbox("Alcohol Use", ["", "none", "occasional", "moderate", "heavy"])
            caffeine = st.number_input("Daily Caffeine (mg)", min_value=0, max_value=1000, value=0,
                                       help="Average daily caffeine intake (1 coffee ≈ 95mg)")
        
        st.markdown("### Medical Information")
        conditions = st.text_area(
            "Medical Conditions",
            help="Enter conditions separated by commas (e.g., hypertension, diabetes)"
        )
        medications = st.text_area(
            "Current Medications",
            help="Enter medications separated by commas"
        )
        
        col_submit, col_cancel = st.columns(2)
        with col_submit:
            submitted = st.form_submit_button("✅ Create Profile", use_container_width=True, type="primary")
        with col_cancel:
            cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)
        
        if cancelled:
            st.session_state["show_profile_creator"] = False
            st.rerun()
        
        if submitted:
            if not username or not full_name:
                st.error("Username and Full Name are required!")
                return
            
            db = get_database()
            
            # Check if username exists
            if db.get_user_by_username(username):
                st.error(f"Username '{username}' already exists!")
                return
            
            # Create profile
            profile = UserProfile(
                user_id=str(uuid.uuid4()),
                username=username,
                full_name=full_name,
                email=email if email else None,
                date_of_birth=dob.isoformat() if dob else None,
                sex=sex if sex else None,
                height_cm=height_cm,
                weight_kg=weight_kg,
                resting_hr_bpm=float(resting_hr) if resting_hr else None,
                max_hr_bpm=float(max_hr) if max_hr > 0 else None,
                vo2max_ml_kg_min=vo2max if vo2max > 0 else None,
                occupation=occupation if occupation else None,
                activity_level=activity_level if activity_level else None,
                smoking_status=smoking if smoking else None,
                alcohol_use=alcohol if alcohol else None,
                caffeine_intake_mg=float(caffeine) if caffeine else None,
                medical_conditions=[c.strip() for c in conditions.split(",") if c.strip()],
                medications=[m.strip() for m in medications.split(",") if m.strip()],
            )
            
            try:
                db.create_user(profile)
                set_current_user(profile)
                st.session_state["show_profile_creator"] = False
                st.success(f"Profile created for {full_name}!")
                st.rerun()
            except Exception as e:
                st.error(f"Error creating profile: {e}")


def render_profile_editor() -> None:
    """Render profile editing form for current user."""
    if not st.session_state.get("show_profile_editor", False):
        return
    
    current_user = get_current_user()
    if not current_user:
        st.session_state["show_profile_editor"] = False
        return
    
    st.markdown(f"## 📝 Edit Profile: {current_user.full_name}")
    
    with st.form("edit_profile_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Basic Information")
            full_name = st.text_input("Full Name*", value=current_user.full_name)
            email = st.text_input("Email", value=current_user.email or "")
            
            dob_value = None
            if current_user.date_of_birth:
                try:
                    dob_value = date.fromisoformat(current_user.date_of_birth)
                except ValueError:
                    pass
            
            dob = st.date_input(
                "Date of Birth",
                value=dob_value,
                min_value=date(1920, 1, 1),
                max_value=date.today(),
            )
            
            sex = st.selectbox(
                "Sex",
                ["", "male", "female", "other"],
                index=["", "male", "female", "other"].index(current_user.sex or "")
            )
        
        with col2:
            st.markdown("### Biometrics")
            height_cm = st.number_input(
                "Height (cm)",
                min_value=100.0, max_value=250.0,
                value=current_user.height_cm or 170.0, step=0.5
            )
            weight_kg = st.number_input(
                "Weight (kg)",
                min_value=30.0, max_value=300.0,
                value=current_user.weight_kg or 70.0, step=0.5
            )
            resting_hr = st.number_input(
                "Resting Heart Rate (bpm)",
                min_value=30, max_value=120,
                value=int(current_user.resting_hr_bpm or 60)
            )
            max_hr = st.number_input(
                "Max Heart Rate (bpm, 0=estimate)",
                min_value=0, max_value=250,
                value=int(current_user.max_hr_bpm or 0)
            )
            vo2max = st.number_input(
                "VO2max (ml/kg/min, 0=unknown)",
                min_value=0.0, max_value=100.0,
                value=current_user.vo2max_ml_kg_min or 0.0, step=0.5
            )
        
        st.markdown("### Lifestyle Factors")
        col3, col4 = st.columns(2)
        
        activity_options = ["", "sedentary", "light", "moderate", "active", "very_active"]
        
        with col3:
            occupation = st.text_input("Occupation", value=current_user.occupation or "")
            activity_level = st.selectbox(
                "Activity Level",
                activity_options,
                index=activity_options.index(current_user.activity_level or ""),
                format_func=lambda x: {
                    "": "Select...",
                    "sedentary": "Sedentary",
                    "light": "Light",
                    "moderate": "Moderate",
                    "active": "Active",
                    "very_active": "Very Active"
                }.get(x, x)
            )
        
        smoking_options = ["", "never", "former", "current"]
        alcohol_options = ["", "none", "occasional", "moderate", "heavy"]
        
        with col4:
            smoking = st.selectbox(
                "Smoking Status",
                smoking_options,
                index=smoking_options.index(current_user.smoking_status or "")
            )
            alcohol = st.selectbox(
                "Alcohol Use",
                alcohol_options,
                index=alcohol_options.index(current_user.alcohol_use or "")
            )
            caffeine = st.number_input(
                "Daily Caffeine (mg)",
                min_value=0, max_value=1000,
                value=int(current_user.caffeine_intake_mg or 0)
            )
        
        st.markdown("### Medical Information")
        conditions = st.text_area(
            "Medical Conditions",
            value=", ".join(current_user.medical_conditions) if current_user.medical_conditions else ""
        )
        medications = st.text_area(
            "Current Medications",
            value=", ".join(current_user.medications) if current_user.medications else ""
        )
        
        col_submit, col_cancel = st.columns(2)
        with col_submit:
            submitted = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")
        with col_cancel:
            cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)
        
        if cancelled:
            st.session_state["show_profile_editor"] = False
            st.rerun()
        
        if submitted:
            if not full_name:
                st.error("Full Name is required!")
                return
            
            # Update profile
            current_user.full_name = full_name
            current_user.email = email if email else None
            current_user.date_of_birth = dob.isoformat() if dob else None
            current_user.sex = sex if sex else None
            current_user.height_cm = height_cm
            current_user.weight_kg = weight_kg
            current_user.resting_hr_bpm = float(resting_hr) if resting_hr else None
            current_user.max_hr_bpm = float(max_hr) if max_hr > 0 else None
            current_user.vo2max_ml_kg_min = vo2max if vo2max > 0 else None
            current_user.occupation = occupation if occupation else None
            current_user.activity_level = activity_level if activity_level else None
            current_user.smoking_status = smoking if smoking else None
            current_user.alcohol_use = alcohol if alcohol else None
            current_user.caffeine_intake_mg = float(caffeine) if caffeine else None
            current_user.medical_conditions = [c.strip() for c in conditions.split(",") if c.strip()]
            current_user.medications = [m.strip() for m in medications.split(",") if m.strip()]
            
            db = get_database()
            try:
                db.update_user(current_user)
                set_current_user(current_user)
                st.session_state["show_profile_editor"] = False
                st.success("Profile updated!")
                st.rerun()
            except Exception as e:
                st.error(f"Error updating profile: {e}")


# ---------------------------------------------------------------------------
# Clinical Scales Form
# ---------------------------------------------------------------------------

def render_clinical_scales_form() -> Optional[ClinicalScales]:
    """Render clinical scales assessment form.
    
    Returns:
        ClinicalScales if saved, None otherwise.
    """
    current_user = get_current_user()
    if not current_user:
        st.warning("Please log in to record clinical assessments.")
        return None
    
    st.markdown("## 📋 Clinical Scales Assessment")
    st.markdown("Complete standardized questionnaires for fatigue, sleepiness, and mood monitoring.")
    
    with st.form("clinical_scales_form"):
        assessment_date = st.date_input("Assessment Date", value=date.today())
        
        st.markdown("### Sleep & Fatigue Scales")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Karolinska Sleepiness Scale (KSS)**")
            st.caption("Current sleepiness level")
            kss = st.slider(
                "KSS Score",
                min_value=1, max_value=9, value=5,
                help="1=Very alert, 5=Neither alert nor sleepy, 9=Very sleepy"
            )
            
            st.markdown("**Samn-Perelli Fatigue Scale**")
            st.caption("Current fatigue level")
            samn_perelli = st.slider(
                "SP Score",
                min_value=1, max_value=7, value=3,
                help="1=Fully alert, 4=Somewhat foggy, 7=Completely exhausted"
            )
        
        with col2:
            st.markdown("**Epworth Sleepiness Scale (ESS)**")
            st.caption("Daytime sleepiness tendency")
            ess = st.number_input("ESS Total (0-24)", min_value=0, max_value=24, value=0,
                                  help="Sum of 8 questions about sleepiness in daily situations")
            
            st.markdown("**Pittsburgh Sleep Quality (PSQI)**")
            st.caption("Past month sleep quality")
            psqi = st.number_input("PSQI Score (0-21)", min_value=0, max_value=21, value=0,
                                   help=">5 indicates poor sleep quality")
        
        with col3:
            st.markdown("**Insomnia Severity Index (ISI)**")
            st.caption("Insomnia symptoms")
            isi = st.number_input("ISI Score (0-28)", min_value=0, max_value=28, value=0,
                                  help="0-7 none, 8-14 mild, 15-21 moderate, 22-28 severe")
            
            st.markdown("**Fatigue Severity Scale (FSS)**")
            st.caption("Impact of fatigue")
            fss = st.number_input("FSS Mean (1.0-7.0)", min_value=1.0, max_value=7.0, value=1.0, step=0.1,
                                  help="Mean of 9 items; >4 indicates significant fatigue")
        
        st.markdown("### Mood & Stress Scales")
        col4, col5 = st.columns(2)
        
        with col4:
            st.markdown("**Perceived Stress Scale (PSS)**")
            pss = st.number_input("PSS Score (0-40)", min_value=0, max_value=40, value=0,
                                  help="0-13 low, 14-26 moderate, 27-40 high stress")
            
            st.markdown("**Beck Depression Inventory (BDI)**")
            bdi = st.number_input("BDI Score (0-63)", min_value=0, max_value=63, value=0,
                                  help="0-9 minimal, 10-18 mild, 19-29 moderate, 30+ severe")
        
        with col5:
            st.markdown("**Visual Analog Scales (0-10)**")
            vas_fatigue = st.slider("VAS Fatigue", min_value=0.0, max_value=10.0, value=0.0, step=0.5,
                                    help="0=No fatigue, 10=Worst possible fatigue")
            vas_pain = st.slider("VAS Pain", min_value=0.0, max_value=10.0, value=0.0, step=0.5,
                                help="0=No pain, 10=Worst possible pain")
        
        st.markdown("### Physical Exertion")
        borg_rpe = st.slider(
            "Borg RPE (6-20)",
            min_value=6, max_value=20, value=6,
            help="Rate of Perceived Exertion: 6=No exertion, 13=Somewhat hard, 20=Max exertion"
        )
        
        notes = st.text_area("Notes", help="Any additional observations or context")
        
        submitted = st.form_submit_button("💾 Save Assessment", use_container_width=True, type="primary")
        
        if submitted:
            scales = ClinicalScales(
                assessment_id=str(uuid.uuid4()),
                user_id=current_user.user_id,
                assessment_date=assessment_date.isoformat(),
                karolinska_sleepiness_scale=kss,
                samn_perelli_fatigue=samn_perelli,
                epworth_sleepiness_scale=ess if ess > 0 else None,
                pittsburgh_sleep_quality_index=psqi if psqi > 0 else None,
                insomnia_severity_index=isi if isi > 0 else None,
                fatigue_severity_scale=fss if fss > 1.0 else None,
                perceived_stress_scale=pss if pss > 0 else None,
                beck_depression_inventory=bdi if bdi > 0 else None,
                vas_fatigue=vas_fatigue if vas_fatigue > 0 else None,
                vas_pain=vas_pain if vas_pain > 0 else None,
                borg_rpe=borg_rpe if borg_rpe > 6 else None,
                notes=notes if notes else None,
            )
            
            db = get_database()
            db.save_clinical_scales(scales)
            st.success("Assessment saved!")
            return scales
    
    return None


# ---------------------------------------------------------------------------
# User Profile Summary Card
# ---------------------------------------------------------------------------

def render_profile_summary_card() -> None:
    """Render a summary card for the current user's profile."""
    current_user = get_current_user()
    if not current_user:
        return
    
    st.markdown("### 👤 Profile Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Age", f"{current_user.age_years or '—'} years")
        st.metric("Height", f"{current_user.height_cm or '—'} cm")
        st.metric("Weight", f"{current_user.weight_kg or '—'} kg")
    
    with col2:
        bmi = current_user.bmi
        bmi_str = f"{bmi:.1f}" if bmi else "—"
        bmi_status = ""
        if bmi:
            if bmi < 18.5:
                bmi_status = " (Underweight)"
            elif bmi < 25:
                bmi_status = " (Normal)"
            elif bmi < 30:
                bmi_status = " (Overweight)"
            else:
                bmi_status = " (Obese)"
        st.metric("BMI", f"{bmi_str}{bmi_status}")
        st.metric("Resting HR", f"{current_user.resting_hr_bpm or '—'} bpm")
        st.metric("Est. Max HR", f"{current_user.estimated_max_hr:.0f} bpm" if current_user.estimated_max_hr else "—")
    
    with col3:
        st.metric("VO2max", f"{current_user.vo2max_ml_kg_min or '—'} ml/kg/min")
        st.metric("Activity", current_user.activity_level or "—")
        st.metric("Sex", current_user.sex.capitalize() if current_user.sex else "—")


# ---------------------------------------------------------------------------
# Data Export/Import
# ---------------------------------------------------------------------------

def render_data_export_import() -> None:
    """Render data export/import section."""
    current_user = get_current_user()
    if not current_user:
        st.warning("Please log in to export/import data.")
        return
    
    st.markdown("### 📤 Export / 📥 Import Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Export Your Data**")
        st.caption("Download all your profile, measurements, and assessments as JSON.")
        
        if st.button("📤 Export to JSON", key="export_data_btn"):
            db = get_database()
            
            # Create export data
            export_path = Path(f"{current_user.username}_hrv_data.json")
            try:
                db.export_user_data(current_user.user_id, export_path)
                
                with open(export_path, "r") as f:
                    json_data = f.read()
                
                st.download_button(
                    label="⬇️ Download JSON",
                    data=json_data,
                    file_name=f"{current_user.username}_hrv_export.json",
                    mime="application/json"
                )
                
                # Clean up temp file
                export_path.unlink(missing_ok=True)
                
            except Exception as e:
                st.error(f"Export failed: {e}")
    
    with col2:
        st.markdown("**Import Data**")
        st.caption("Upload previously exported JSON data.")
        
        uploaded_file = st.file_uploader(
            "Choose JSON file",
            type=["json"],
            key="import_data_file"
        )
        
        if uploaded_file and st.button("📥 Import Data", key="import_data_btn"):
            db = get_database()
            
            # Save uploaded file temporarily
            import_path = Path(f"temp_import_{uuid.uuid4()}.json")
            try:
                with open(import_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                
                new_user_id = db.import_user_data(import_path)
                st.success(f"Data imported successfully! New user ID: {new_user_id}")
                
            except Exception as e:
                st.error(f"Import failed: {e}")
            finally:
                import_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Longitudinal Statistics Display
# ---------------------------------------------------------------------------

def render_longitudinal_stats(metric: str = "rmssd_ms") -> None:
    """Render longitudinal statistics for a metric."""
    current_user = get_current_user()
    if not current_user:
        return
    
    db = get_database()
    stats = db.compute_longitudinal_stats(current_user.user_id, metric)
    
    if not stats or stats.get("n", 0) < 2:
        st.info("Need at least 2 measurements for longitudinal statistics.")
        return
    
    st.markdown(f"### 📈 Longitudinal Statistics: {metric.upper()}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("N", stats.get("n", "—"))
        st.metric("Mean", f"{stats.get('mean', 0):.2f}")
    
    with col2:
        st.metric("Std Dev", f"{stats.get('std', 0):.2f}")
        st.metric("CV%", f"{stats.get('cv_pct', 0):.1f}%")
    
    with col3:
        st.metric("Median", f"{stats.get('median', 0):.2f}")
        st.metric("IQR", f"{stats.get('iqr', 0):.2f}")
    
    with col4:
        if "trend_direction" in stats:
            trend_icon = "📈" if stats["trend_direction"] == "increasing" else "📉"
            st.metric("Trend", f"{trend_icon} {stats['trend_direction'].capitalize()}")
        if "pct_change_total" in stats:
            st.metric("Total Change", f"{stats['pct_change_total']:.1f}%")
    
    # 95% CI
    if "ci_95_lower" in stats and "ci_95_upper" in stats:
        st.caption(f"95% CI: [{stats['ci_95_lower']:.2f}, {stats['ci_95_upper']:.2f}]")


# ---------------------------------------------------------------------------
# Main Render Function
# ---------------------------------------------------------------------------

def render_user_management_tab() -> None:
    """Render the complete user management tab."""
    st.markdown("# 👥 User Management")
    st.markdown("Manage profiles, track assessments, and analyze longitudinal data.")
    
    # Show profile creator/editor if needed
    render_profile_creator()
    render_profile_editor()
    
    current_user = get_current_user()
    
    if not current_user:
        st.info("👈 Select or create a user profile from the sidebar to get started.")
        
        # Quick create button
        if st.button("➕ Create New Profile", key="quick_create_profile"):
            st.session_state["show_profile_creator"] = True
            st.rerun()
        return
    
    # Tab navigation for user management sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Profile Summary",
        "📋 Clinical Scales",
        "📈 Statistics",
        "💾 Export/Import"
    ])
    
    with tab1:
        render_profile_summary_card()
        
        st.markdown("---")
        
        # Show recent measurements
        db = get_database()
        hrv_history = db.get_hrv_history(current_user.user_id, limit=5)
        
        if hrv_history:
            st.markdown("### Recent HRV Measurements")
            for meas in hrv_history:
                with st.expander(f"📊 {meas.measurement_date[:10]} - {meas.device_name or 'Unknown'}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("RMSSD", f"{meas.rmssd_ms:.1f} ms" if meas.rmssd_ms else "—")
                    col2.metric("SDNN", f"{meas.sdnn_ms:.1f} ms" if meas.sdnn_ms else "—")
                    col3.metric("Mean HR", f"{meas.mean_hr_bpm:.0f} bpm" if meas.mean_hr_bpm else "—")
        else:
            st.info("No HRV measurements recorded yet. Import data to get started!")
    
    with tab2:
        render_clinical_scales_form()
        
        st.markdown("---")
        
        # Show recent assessments
        scales_history = db.get_clinical_scales_history(current_user.user_id, limit=5)
        
        if scales_history:
            st.markdown("### Recent Assessments")
            for scale in scales_history:
                with st.expander(f"📋 {scale.assessment_date}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("KSS", scale.karolinska_sleepiness_scale or "—")
                    col2.metric("Samn-Perelli", scale.samn_perelli_fatigue or "—")
                    col3.metric("VAS Fatigue", f"{scale.vas_fatigue:.1f}" if scale.vas_fatigue else "—")
    
    with tab3:
        metric_options = [
            "rmssd_ms", "sdnn_ms", "mean_hr_bpm", "pnn50_pct",
            "lf_power_ms2", "hf_power_ms2", "lf_hf_ratio",
            "dfa_alpha1", "sd1_ms", "sd2_ms"
        ]
        
        selected_metric = st.selectbox("Select Metric", metric_options)
        render_longitudinal_stats(selected_metric)
        
        # Show HRV trend chart
        df = db.get_hrv_dataframe(current_user.user_id)
        if not df.empty and selected_metric in df.columns:
            st.markdown("### Trend Over Time")
            chart_data = df[["measurement_date", selected_metric]].dropna()
            if not chart_data.empty:
                st.line_chart(chart_data.set_index("measurement_date")[selected_metric])
    
    with tab4:
        render_data_export_import()
        
        st.markdown("---")
        st.markdown("### ⚙️ Database Info")
        st.caption(f"Database location: `{get_database_path()}`")


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    "render_user_selector",
    "render_profile_creator",
    "render_profile_editor",
    "render_clinical_scales_form",
    "render_profile_summary_card",
    "render_data_export_import",
    "render_longitudinal_stats",
    "render_user_management_tab",
    "get_current_user",
    "set_current_user",
    "is_user_logged_in",
]

