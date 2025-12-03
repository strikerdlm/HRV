"""
Internationalization (i18n) module for HRV Analysis Suite.

Provides multilingual support starting with English and Spanish (Colombian).
Clinical scales use validated translations where available:
- Epworth Sleepiness Scale: ESE-VC (Chica-Urzola et al., 2007)
- Karolinska Sleepiness Scale: Colombian validation (Sleep Science, 2022)
- Samn-Perelli Fatigue Scale: Professional translation following aviation standards

Author: Dr. Diego Leonel Malpica Hincapié, MD
Version: 1.0.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Final, Optional

import streamlit as st

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# Session state key for language
_SESSION_LANGUAGE_KEY: Final[str] = "app_language"
_DEFAULT_LANGUAGE: Final[str] = "en"


class Language(str, Enum):
    """Supported languages."""
    
    ENGLISH = "en"
    SPANISH = "es"
    
    @property
    def display_name(self) -> str:
        """Get display name for the language."""
        names = {
            "en": "English",
            "es": "Español",
        }
        return names.get(self.value, self.value)
    
    @property
    def flag_emoji(self) -> str:
        """Get flag emoji for the language."""
        flags = {
            "en": "🇺🇸",
            "es": "🇨🇴",  # Colombian flag for Spanish
        }
        return flags.get(self.value, "🌐")


# ---------------------------------------------------------------------------
# Translation Dictionaries
# ---------------------------------------------------------------------------

# Epworth Sleepiness Scale - English original and Colombian validation (ESE-VC)
EPWORTH_TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    "en": {
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
        "response_options": {
            0: "Would never doze",
            1: "Slight chance of dozing",
            2: "Moderate chance of dozing", 
            3: "High chance of dozing",
        },
        "total_score": "Total Score",
        "interpretation": {
            "normal": "Normal daytime sleepiness",
            "mild": "Mild excessive daytime sleepiness",
            "moderate": "Moderate excessive daytime sleepiness",
            "severe": "Severe excessive daytime sleepiness",
        },
        "warning": "Score >10 suggests excessive daytime sleepiness. Consider sleep evaluation.",
    },
    "es": {
        # ESE-VC - Validated Colombian Version (Chica-Urzola et al., Rev Salud Publica 2007)
        "title": "Escala de Somnolencia de Epworth (ESE-VC)",
        "subtitle": "¿Qué tan probable es que usted se quede dormido en las siguientes situaciones? (0-3)",
        "help": "0 = Nunca, 3 = Alta probabilidad",
        "situations": [
            ("sitting_reading", "Sentado leyendo"),
            ("watching_tv", "Viendo televisión"),
            ("sitting_inactive_public", "Sentado, inactivo en un lugar público (ej: cine, reunión)"),
            ("passenger_car_hour", "Como pasajero en un carro durante una hora sin parar"),
            ("lying_down_afternoon", "Acostado descansando en la tarde"),
            ("sitting_talking", "Sentado conversando con alguien"),
            ("sitting_quietly_after_lunch", "Sentado tranquilo después de almorzar sin haber bebido alcohol"),
            ("car_stopped_traffic", "En un carro, mientras está parado por unos minutos en el tráfico"),
        ],
        "response_options": {
            0: "Nunca se quedaría dormido",
            1: "Escasa probabilidad de quedarse dormido",
            2: "Moderada probabilidad de quedarse dormido",
            3: "Alta probabilidad de quedarse dormido",
        },
        "total_score": "Puntaje Total",
        "interpretation": {
            "normal": "Somnolencia diurna normal",
            "mild": "Somnolencia diurna excesiva leve",
            "moderate": "Somnolencia diurna excesiva moderada",
            "severe": "Somnolencia diurna excesiva severa",
        },
        "warning": "Puntaje >10 sugiere somnolencia diurna excesiva. Considere evaluación de sueño.",
    },
}

# Karolinska Sleepiness Scale - Colombian validation (Sleep Science, 2022)
KAROLINSKA_TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    "en": {
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
    },
    "es": {
        # Colombian validation (Velásquez-Paz et al., Sleep Science 2022)
        "title": "Escala de Somnolencia de Karolinska (KSS)",
        "subtitle": "Califique su nivel actual de somnolencia",
        "current_sleepiness": "Somnolencia actual:",
        "options": {
            1: "1 - Extremadamente alerta",
            2: "2 - Muy alerta",
            3: "3 - Alerta",
            4: "4 - Bastante alerta",
            5: "5 - Ni alerta ni somnoliento",
            6: "6 - Algunas señales de somnolencia",
            7: "7 - Somnoliento, pero sin esfuerzo para permanecer despierto",
            8: "8 - Somnoliento, con algún esfuerzo para permanecer despierto",
            9: "9 - Extremadamente somnoliento, luchando contra el sueño",
        },
        "warning": "KSS ≥7 indica somnolencia significativa que puede afectar el desempeño.",
    },
}

# Samn-Perelli Fatigue Scale (aviation standard translation)
SAMN_PERELLI_TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    "en": {
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
        "risk_levels": {
            "LOW": "LOW",
            "MODERATE": "MODERATE",
            "HIGH": "HIGH",
            "CRITICAL": "CRITICAL",
        },
        "warning": "Fatigue level may impair performance. Consider rest before safety-critical tasks.",
    },
    "es": {
        # Professional translation following FAA/ICAO standards for aviation fatigue
        "title": "Escala de Fatiga de Samn-Perelli",
        "subtitle": "Seleccione la afirmación que mejor describe su estado actual",
        "current_state": "Estado actual de fatiga:",
        "options": {
            1: "1 - Completamente alerta, totalmente despierto",
            2: "2 - Muy animado, receptivo, pero no en mi mejor momento",
            3: "3 - Bien, algo fresco",
            4: "4 - Un poco cansado, menos fresco",
            5: "5 - Moderadamente cansado, decaído",
            6: "6 - Extremadamente cansado, muy difícil concentrarme",
            7: "7 - Completamente exhausto, incapaz de funcionar efectivamente",
        },
        "risk_level": "Nivel de Riesgo Operacional",
        "risk_levels": {
            "LOW": "BAJO",
            "MODERATE": "MODERADO",
            "HIGH": "ALTO",
            "CRITICAL": "CRÍTICO",
        },
        "warning": "El nivel de fatiga puede afectar el desempeño. Considere descansar antes de tareas críticas de seguridad.",
    },
}

# Visual Analog Scales
VAS_TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    "en": {
        "title": "Visual Analog Scales (VAS)",
        "subtitle": "Rate your current state on a 0-10 scale",
        "fatigue": "Fatigue (0 = None, 10 = Extreme)",
        "pain": "Pain (0 = None, 10 = Worst imaginable)",
    },
    "es": {
        "title": "Escalas Análogas Visuales (EAV)",
        "subtitle": "Califique su estado actual en una escala de 0-10",
        "fatigue": "Fatiga (0 = Ninguna, 10 = Extrema)",
        "pain": "Dolor (0 = Ninguno, 10 = El peor imaginable)",
    },
}

# User Interface Strings
UI_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # User Profile Tab
        "user_profile_clinical_assessments": "👤 User Profile & Clinical Assessments",
        "new_user_registration": "📝 New User Registration",
        "create_profile": "✅ Create Profile",
        "select_user": "🔑 Select or Login",
        "select_user_button": "✅ Select User",
        "edit_profile": "✏️ Edit Profile",
        "save_changes": "💾 Save Changes",
        "cancel": "❌ Cancel",
        
        # Form Labels
        "username": "Username",
        "username_required": "Username *",
        "full_name": "Full Name",
        "full_name_required": "Full Name *",
        "email": "Email",
        "password": "Password",
        "date_of_birth": "Date of Birth",
        "biological_sex": "Biological Sex",
        "occupation_type": "Occupation Type",
        "height_cm": "Height (cm)",
        "weight_kg": "Weight (kg)",
        "resting_hr": "Resting HR (bpm)",
        "vo2max": "VO2max (mL/kg/min)",
        "activity_level": "Activity Level",
        
        # Sex options
        "male": "Male",
        "female": "Female",
        "other": "Other",
        
        # Activity levels
        "sedentary": "Sedentary",
        "light": "Light",
        "moderate": "Moderate",
        "active": "Active",
        "very_active": "Very Active",
        
        # Occupation types
        "pilot": "Pilot",
        "atc": "Air Traffic Control",
        "flight_crew": "Flight Crew",
        "medical": "Medical",
        "shift_worker": "Shift Worker",
        "military": "Military",
        "driver": "Driver",
        "researcher": "Researcher",
        "office": "Office",
        "other_occupation": "Other",
        
        # Clinical Assessment
        "clinical_assessment": "📊 Clinical Assessment",
        "clinical_assessment_subtitle": "Complete standardized scales for fatigue and sleep evaluation",
        "assessment_context": "⏰ Assessment Context",
        "hours_since_waking": "Hours since waking",
        "hours_slept": "Hours slept last night",
        "caffeine_today": "Caffeine today (cups)",
        "select_scales": "Select scales to complete:",
        "assessment_notes": "Assessment Notes",
        "assessment_notes_placeholder": "Optional notes about current conditions, activities, etc.",
        "save_assessment": "💾 Save Assessment",
        "assessment_saved": "✅ Assessment saved successfully!",
        "assessment_history": "📈 Assessment History",
        
        # Scale descriptions
        "ess_description": "Epworth Sleepiness Scale (trait measure)",
        "sp_description": "Samn-Perelli Fatigue Scale (state measure)",
        "kss_description": "Karolinska Sleepiness Scale (state measure)",
        "vas_description": "Visual Analog Scales (fatigue, pain)",
        
        # Anthropometrics
        "anthropometrics": "📏 Anthropometrics",
        "bmi": "BMI",
        "estimated_vo2max": "Estimated if not known",
        
        # Messages
        "username_full_name_required": "Username and Full Name are required.",
        "username_exists": "Username '{username}' already exists.",
        "profile_created": "✅ Profile created for {name}!",
        "failed_create_profile": "Failed to create profile: {error}",
        "no_users_registered": "No users registered. Create a new profile below.",
        "password_help": "Optional - for multi-user setups",
        "username_help": "Unique identifier for login",
        
        # Settings
        "settings": "⚙️ Settings",
        "language": "Language",
        "language_help": "Select your preferred language / Seleccione su idioma preferido",
    },
    "es": {
        # User Profile Tab
        "user_profile_clinical_assessments": "👤 Perfil de Usuario y Evaluaciones Clínicas",
        "new_user_registration": "📝 Registro de Nuevo Usuario",
        "create_profile": "✅ Crear Perfil",
        "select_user": "🔑 Seleccionar o Iniciar Sesión",
        "select_user_button": "✅ Seleccionar Usuario",
        "edit_profile": "✏️ Editar Perfil",
        "save_changes": "💾 Guardar Cambios",
        "cancel": "❌ Cancelar",
        
        # Form Labels
        "username": "Nombre de usuario",
        "username_required": "Nombre de usuario *",
        "full_name": "Nombre completo",
        "full_name_required": "Nombre completo *",
        "email": "Correo electrónico",
        "password": "Contraseña",
        "date_of_birth": "Fecha de nacimiento",
        "biological_sex": "Sexo biológico",
        "occupation_type": "Tipo de ocupación",
        "height_cm": "Altura (cm)",
        "weight_kg": "Peso (kg)",
        "resting_hr": "FC en reposo (lpm)",
        "vo2max": "VO2max (mL/kg/min)",
        "activity_level": "Nivel de actividad",
        
        # Sex options
        "male": "Masculino",
        "female": "Femenino",
        "other": "Otro",
        
        # Activity levels
        "sedentary": "Sedentario",
        "light": "Ligero",
        "moderate": "Moderado",
        "active": "Activo",
        "very_active": "Muy Activo",
        
        # Occupation types
        "pilot": "Piloto",
        "atc": "Control de Tráfico Aéreo",
        "flight_crew": "Tripulación de Vuelo",
        "medical": "Médico",
        "shift_worker": "Trabajador por Turnos",
        "military": "Militar",
        "driver": "Conductor",
        "researcher": "Investigador",
        "office": "Oficina",
        "other_occupation": "Otro",
        
        # Clinical Assessment
        "clinical_assessment": "📊 Evaluación Clínica",
        "clinical_assessment_subtitle": "Complete escalas estandarizadas para evaluación de fatiga y sueño",
        "assessment_context": "⏰ Contexto de la Evaluación",
        "hours_since_waking": "Horas desde despertar",
        "hours_slept": "Horas dormidas anoche",
        "caffeine_today": "Cafeína hoy (tazas)",
        "select_scales": "Seleccione las escalas a completar:",
        "assessment_notes": "Notas de la Evaluación",
        "assessment_notes_placeholder": "Notas opcionales sobre condiciones actuales, actividades, etc.",
        "save_assessment": "💾 Guardar Evaluación",
        "assessment_saved": "✅ ¡Evaluación guardada exitosamente!",
        "assessment_history": "📈 Historial de Evaluaciones",
        
        # Scale descriptions
        "ess_description": "Escala de Somnolencia de Epworth (medida de rasgo)",
        "sp_description": "Escala de Fatiga Samn-Perelli (medida de estado)",
        "kss_description": "Escala de Somnolencia de Karolinska (medida de estado)",
        "vas_description": "Escalas Análogas Visuales (fatiga, dolor)",
        
        # Anthropometrics
        "anthropometrics": "📏 Antropometría",
        "bmi": "IMC",
        "estimated_vo2max": "Estimado si no se conoce",
        
        # Messages
        "username_full_name_required": "El nombre de usuario y nombre completo son requeridos.",
        "username_exists": "El nombre de usuario '{username}' ya existe.",
        "profile_created": "✅ ¡Perfil creado para {name}!",
        "failed_create_profile": "Error al crear el perfil: {error}",
        "no_users_registered": "No hay usuarios registrados. Cree un nuevo perfil abajo.",
        "password_help": "Opcional - para configuraciones multiusuario",
        "username_help": "Identificador único para inicio de sesión",
        
        # Settings
        "settings": "⚙️ Configuración",
        "language": "Idioma",
        "language_help": "Select your preferred language / Seleccione su idioma preferido",
    },
}


# ---------------------------------------------------------------------------
# Translation Functions
# ---------------------------------------------------------------------------

def get_current_language() -> Language:
    """Get the current language from session state.
    
    Returns:
        Current Language enum value.
    """
    lang_code = st.session_state.get(_SESSION_LANGUAGE_KEY, _DEFAULT_LANGUAGE)
    try:
        return Language(lang_code)
    except ValueError:
        return Language.ENGLISH


def set_language(language: Language) -> None:
    """Set the current language in session state.
    
    Args:
        language: Language to set.
    """
    st.session_state[_SESSION_LANGUAGE_KEY] = language.value
    _LOGGER.info("Language set to: %s", language.value)


def t(key: str, **kwargs: Any) -> str:
    """Get translated string for a UI key.
    
    Args:
        key: Translation key.
        **kwargs: Format arguments for the string.
        
    Returns:
        Translated string, or key if not found.
    """
    lang = get_current_language()
    translations = UI_TRANSLATIONS.get(lang.value, UI_TRANSLATIONS["en"])
    
    text = translations.get(key, UI_TRANSLATIONS["en"].get(key, key))
    
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    
    return text


def get_epworth_translations() -> Dict[str, Any]:
    """Get Epworth Sleepiness Scale translations for current language."""
    lang = get_current_language()
    return EPWORTH_TRANSLATIONS.get(lang.value, EPWORTH_TRANSLATIONS["en"])


def get_karolinska_translations() -> Dict[str, Any]:
    """Get Karolinska Sleepiness Scale translations for current language."""
    lang = get_current_language()
    return KAROLINSKA_TRANSLATIONS.get(lang.value, KAROLINSKA_TRANSLATIONS["en"])


def get_samn_perelli_translations() -> Dict[str, Any]:
    """Get Samn-Perelli Fatigue Scale translations for current language."""
    lang = get_current_language()
    return SAMN_PERELLI_TRANSLATIONS.get(lang.value, SAMN_PERELLI_TRANSLATIONS["en"])


def get_vas_translations() -> Dict[str, Any]:
    """Get VAS translations for current language."""
    lang = get_current_language()
    return VAS_TRANSLATIONS.get(lang.value, VAS_TRANSLATIONS["en"])


# ---------------------------------------------------------------------------
# Language Selector Widget
# ---------------------------------------------------------------------------

def render_language_selector(
    location: str = "main",
    key_suffix: str = "",
) -> Language:
    """Render a language selector widget.
    
    Args:
        location: "main" for main area, "sidebar" for sidebar.
        key_suffix: Optional suffix for widget key uniqueness.
        
    Returns:
        Selected Language.
    """
    current = get_current_language()
    
    languages = list(Language)
    current_index = languages.index(current)
    
    # Format function for display
    def format_lang(lang: Language) -> str:
        return f"{lang.flag_emoji} {lang.display_name}"
    
    widget_key = f"lang_selector_{location}_{key_suffix}"
    
    if location == "sidebar":
        selected = st.sidebar.selectbox(
            t("language"),
            options=languages,
            index=current_index,
            format_func=format_lang,
            key=widget_key,
            help=t("language_help"),
        )
    else:
        selected = st.selectbox(
            t("language"),
            options=languages,
            index=current_index,
            format_func=format_lang,
            key=widget_key,
            help=t("language_help"),
        )
    
    # Update session state if changed
    if selected != current:
        set_language(selected)
        st.rerun()
    
    return selected


def render_language_toggle() -> Language:
    """Render a compact language toggle (for headers/footers).
    
    Returns:
        Selected Language.
    """
    current = get_current_language()
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Simple toggle between EN and ES
        languages = list(Language)
        current_index = languages.index(current)
        
        new_lang = st.radio(
            "🌐",
            options=languages,
            index=current_index,
            format_func=lambda x: x.flag_emoji,
            horizontal=True,
            label_visibility="collapsed",
            key="lang_toggle_compact",
        )
        
        if new_lang != current:
            set_language(new_lang)
            st.rerun()
    
    return current


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    "Language",
    "get_current_language",
    "set_language",
    "t",
    "get_epworth_translations",
    "get_karolinska_translations",
    "get_samn_perelli_translations",
    "get_vas_translations",
    "render_language_selector",
    "render_language_toggle",
    "EPWORTH_TRANSLATIONS",
    "KAROLINSKA_TRANSLATIONS",
    "SAMN_PERELLI_TRANSLATIONS",
    "VAS_TRANSLATIONS",
    "UI_TRANSLATIONS",
]

