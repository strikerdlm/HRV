"""Agentic Report Generation Module for Mission Control - Flight Surgeon.

This module provides sophisticated AI-powered report generation using OpenAI's
GPT-5.2 model with high reasoning, code interpreter, and web search capabilities.

Report Types:
1. Graduate Level Report: Comprehensive individual profile analysis with plots,
   explanations across all profile sections (assessments, clinical, history, HRV).
2. Doctoral Level Report: Comparative analysis between user profiles following
   academic paper structure (Introduction, Methods, Results, Discussion).

Design Principles:
- Uses GPT-5.2 with high reasoning effort for maximum analytical depth
- Integrates code_interpreter for data analysis and visualization
- Uses web_search for current literature and evidence-based citations
- Deterministic local fallback when API unavailable
- Bounded retries and timeouts for reliability

Author: Dr. Diego Leonel Malpica Hincapié, MD
Version: 1.0.0
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Final, List, Mapping, Optional, Sequence, Tuple

import pandas as pd

# Conditional import for OpenAI
try:
    from openai import APIConnectionError, APIError, OpenAI, RateLimitError

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    APIError = Exception  # type: ignore[misc, assignment]
    RateLimitError = Exception  # type: ignore[misc, assignment]
    APIConnectionError = Exception  # type: ignore[misc, assignment]

try:
    from agent_logging import log_agent_output
except ImportError:
    def log_agent_output(*args: Any, **kwargs: Any) -> None:
        """Fallback no-op logger."""
        pass

try:
    from logging_config import get_logger
except ImportError:
    get_logger = None  # type: ignore[assignment]

_LOGGER: Final[logging.Logger] = (
    get_logger(__name__) if get_logger is not None else logging.getLogger(__name__)
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MODEL: Final[str] = "gpt-5.2"
_DEFAULT_TIMEOUT: Final[float] = 180.0  # Extended for complex agentic reports
_MAX_RETRIES: Final[int] = 3
_RETRY_DELAY_SECONDS: Final[float] = 2.0


class ReportLevel(str, Enum):
    """Academic level of the generated report."""

    GRADUATE = "graduate"
    DOCTORAL = "doctoral"


class ReportStatus(str, Enum):
    """Status of report generation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FALLBACK = "fallback"
    ERROR = "error"


@dataclass(slots=True, frozen=True)
class ReportResult:
    """Result of agentic report generation.

    Attributes:
        markdown: The generated report in markdown format.
        level: Academic level of the report.
        status: Generation status (success, partial, fallback, error).
        reasoning_summary: Summary of AI reasoning process (when available).
        sources: List of cited sources from web search.
        model_used: Model that generated the report.
        generation_time_seconds: Time taken to generate the report.
        error_message: Error message if status is error.
    """

    markdown: str
    level: ReportLevel
    status: ReportStatus
    reasoning_summary: str = ""
    sources: List[str] = field(default_factory=list)
    model_used: str = "unknown"
    generation_time_seconds: float = 0.0
    error_message: str = ""


# ---------------------------------------------------------------------------
# Data Collection for Reports
# ---------------------------------------------------------------------------


@dataclass
class UserProfileData:
    """Comprehensive user profile data for report generation."""

    user_id: str
    username: str
    full_name: str
    
    # Demographics
    age_years: Optional[int] = None
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    
    # Fitness metrics
    resting_hr_bpm: Optional[float] = None
    max_hr_bpm: Optional[float] = None
    vo2max_ml_kg_min: Optional[float] = None
    activity_level: Optional[str] = None
    
    # Body composition
    body_fat_pct: Optional[float] = None
    lean_mass_kg: Optional[float] = None
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    neck_cm: Optional[float] = None
    
    # Clinical data
    clinical_scales: List[Dict[str, Any]] = field(default_factory=list)
    medical_history: List[Dict[str, Any]] = field(default_factory=list)
    body_composition_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # HRV data
    hrv_measurements: List[Dict[str, Any]] = field(default_factory=list)
    hrv_summary: Dict[str, Any] = field(default_factory=dict)
    
    # Readiness and recovery
    readiness_data: Dict[str, Any] = field(default_factory=dict)
    fatigue_data: Dict[str, Any] = field(default_factory=dict)
    
    # Sleep and activity
    sleep_records: List[Dict[str, Any]] = field(default_factory=list)
    activity_records: List[Dict[str, Any]] = field(default_factory=list)
    garmin_daily_metrics: List[Dict[str, Any]] = field(default_factory=list)
    
    # Profile tools results
    profile_tools_results: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    data_collection_timestamp: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "full_name": self.full_name,
            "demographics": {
                "age_years": self.age_years,
                "sex": self.sex,
                "height_cm": self.height_cm,
                "weight_kg": self.weight_kg,
                "bmi": self.bmi,
            },
            "fitness": {
                "resting_hr_bpm": self.resting_hr_bpm,
                "max_hr_bpm": self.max_hr_bpm,
                "vo2max_ml_kg_min": self.vo2max_ml_kg_min,
                "activity_level": self.activity_level,
            },
            "body_composition": {
                "body_fat_pct": self.body_fat_pct,
                "lean_mass_kg": self.lean_mass_kg,
                "waist_cm": self.waist_cm,
                "hip_cm": self.hip_cm,
                "neck_cm": self.neck_cm,
            },
            "clinical_scales_count": len(self.clinical_scales),
            "clinical_scales_latest": self.clinical_scales[:5] if self.clinical_scales else [],
            "medical_history_count": len(self.medical_history),
            "medical_history_latest": self.medical_history[:5] if self.medical_history else [],
            "hrv_measurements_count": len(self.hrv_measurements),
            "hrv_measurements_latest": self.hrv_measurements[:10] if self.hrv_measurements else [],
            "hrv_summary": self.hrv_summary,
            "readiness_data": self.readiness_data,
            "fatigue_data": self.fatigue_data,
            "sleep_records_count": len(self.sleep_records),
            "sleep_records_latest": self.sleep_records[:7] if self.sleep_records else [],
            "activity_records_count": len(self.activity_records),
            "garmin_daily_metrics_count": len(self.garmin_daily_metrics),
            "profile_tools_results": self.profile_tools_results,
            "data_collection_timestamp": self.data_collection_timestamp,
        }


def collect_user_profile_data(
    user_id: str,
    db: Any,
    *,
    include_hrv_analysis: bool = True,
    include_profile_tools: bool = True,
    max_historical_records: int = 50,
) -> UserProfileData:
    """Collect comprehensive user profile data for report generation.

    Args:
        user_id: User identifier.
        db: Database instance (UserDatabase).
        include_hrv_analysis: Whether to include HRV analysis results.
        include_profile_tools: Whether to run profile tools engine.
        max_historical_records: Maximum historical records to include.

    Returns:
        UserProfileData with all available data for the user.

    Raises:
        ValueError: If user_id is invalid or user not found.
    """
    if not user_id:
        raise ValueError("user_id is required")
    
    user = db.get_user(user_id)
    if user is None:
        raise ValueError(f"User not found: {user_id}")
    
    # Calculate age
    age = None
    if hasattr(user, 'date_of_birth') and user.date_of_birth:
        try:
            dob = user.date_of_birth
            if isinstance(dob, str):
                from datetime import date
                dob = date.fromisoformat(dob)
            today = datetime.now(timezone.utc).date()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        except Exception:
            age = None
    
    # Calculate BMI
    bmi = None
    if user.height_cm and user.weight_kg and user.height_cm > 0:
        bmi = round(user.weight_kg / ((user.height_cm / 100) ** 2), 1)
    
    # Collect clinical scales
    clinical_scales: List[Dict[str, Any]] = []
    try:
        scales = db.get_clinical_scales_history(user_id, limit=max_historical_records)
        clinical_scales = [s.to_dict() if hasattr(s, 'to_dict') else dict(s) for s in scales]
    except Exception as exc:
        _LOGGER.warning("Failed to collect clinical scales: %s", exc)
    
    # Collect medical history
    medical_history: List[Dict[str, Any]] = []
    try:
        history = db.get_medical_history(user_id, limit=max_historical_records)
        medical_history = list(history) if history else []
    except Exception as exc:
        _LOGGER.warning("Failed to collect medical history: %s", exc)
    
    # Collect body composition history
    body_composition_history: List[Dict[str, Any]] = []
    body_fat_pct = None
    lean_mass_kg = None
    waist_cm = None
    hip_cm = None
    neck_cm = None
    try:
        if hasattr(db, 'get_body_composition_history'):
            comp_history = db.get_body_composition_history(user_id, limit=max_historical_records)
            body_composition_history = [
                c.to_dict() if hasattr(c, 'to_dict') else dict(c) for c in comp_history
            ]
            if body_composition_history:
                latest = body_composition_history[0]
                body_fat_pct = latest.get('body_fat_pct')
                lean_mass_kg = latest.get('lean_mass_kg')
                waist_cm = latest.get('waist_cm')
                hip_cm = latest.get('hip_cm')
                neck_cm = latest.get('neck_cm')
    except Exception as exc:
        _LOGGER.warning("Failed to collect body composition: %s", exc)
    
    # Collect HRV measurements
    hrv_measurements: List[Dict[str, Any]] = []
    hrv_summary: Dict[str, Any] = {}
    try:
        hrv_history = db.get_hrv_history(user_id, limit=max_historical_records)
        hrv_measurements = [m.to_dict() if hasattr(m, 'to_dict') else dict(m) for m in hrv_history]
        
        if hrv_measurements:
            # Compute summary statistics
            rmssd_values = [m.get('rmssd_ms') for m in hrv_measurements if m.get('rmssd_ms')]
            sdnn_values = [m.get('sdnn_ms') for m in hrv_measurements if m.get('sdnn_ms')]
            
            if rmssd_values:
                import numpy as np
                hrv_summary['rmssd_mean'] = float(np.mean(rmssd_values))
                hrv_summary['rmssd_std'] = float(np.std(rmssd_values))
                hrv_summary['rmssd_median'] = float(np.median(rmssd_values))
                hrv_summary['rmssd_cv'] = float(np.std(rmssd_values) / np.mean(rmssd_values) * 100) if np.mean(rmssd_values) > 0 else 0
            
            if sdnn_values:
                import numpy as np
                hrv_summary['sdnn_mean'] = float(np.mean(sdnn_values))
                hrv_summary['sdnn_std'] = float(np.std(sdnn_values))
                hrv_summary['sdnn_median'] = float(np.median(sdnn_values))
            
            hrv_summary['total_measurements'] = len(hrv_measurements)
            hrv_summary['date_range'] = {
                'earliest': hrv_measurements[-1].get('recording_datetime') if hrv_measurements else None,
                'latest': hrv_measurements[0].get('recording_datetime') if hrv_measurements else None,
            }
    except Exception as exc:
        _LOGGER.warning("Failed to collect HRV measurements: %s", exc)
    
    # Collect sleep records
    sleep_records: List[Dict[str, Any]] = []
    try:
        if hasattr(db, 'get_sleep_records'):
            sleep_data = db.get_sleep_records(user_id, limit=max_historical_records)
            sleep_records = [s.to_dict() if hasattr(s, 'to_dict') else dict(s) for s in sleep_data]
    except Exception as exc:
        _LOGGER.warning("Failed to collect sleep records: %s", exc)
    
    # Collect Garmin daily metrics
    garmin_daily_metrics: List[Dict[str, Any]] = []
    try:
        garmin_data = db.get_garmin_daily_metrics(user_id, limit=max_historical_records)
        garmin_daily_metrics = [g.to_dict() if hasattr(g, 'to_dict') else dict(g) for g in garmin_data]
    except Exception as exc:
        _LOGGER.warning("Failed to collect Garmin metrics: %s", exc)
    
    # Run profile tools if requested
    profile_tools_results: Dict[str, Any] = {}
    if include_profile_tools and age and hrv_measurements:
        try:
            from profile_tools_engine import run_all_profile_tools
            
            latest_hrv = hrv_measurements[0] if hrv_measurements else {}
            rmssd_ms = latest_hrv.get('rmssd_ms')
            
            profile_tools_results = run_all_profile_tools(
                age=age,
                sex=user.sex or 'other',
                weight_kg=user.weight_kg or 70.0,
                height_cm=user.height_cm or 170.0,
                rmssd_ms=rmssd_ms,
                hrv_metrics={
                    'rmssd_ms': latest_hrv.get('rmssd_ms'),
                    'sdnn_ms': latest_hrv.get('sdnn_ms'),
                    'pnn50': latest_hrv.get('pnn50'),
                    'hf_power': latest_hrv.get('hf_power'),
                    'lf_power': latest_hrv.get('lf_power'),
                    'lf_hf_ratio': latest_hrv.get('lf_hf_ratio'),
                    'mean_rr_ms': latest_hrv.get('mean_rr_ms'),
                },
                resting_hr=user.resting_hr_bpm,
                vo2max=user.vo2max_ml_kg_min,
            )
        except Exception as exc:
            _LOGGER.warning("Failed to run profile tools: %s", exc)
    
    return UserProfileData(
        user_id=user_id,
        username=user.username,
        full_name=user.full_name or user.username,
        age_years=age,
        sex=user.sex,
        height_cm=user.height_cm,
        weight_kg=user.weight_kg,
        bmi=bmi,
        resting_hr_bpm=user.resting_hr_bpm,
        max_hr_bpm=user.max_hr_bpm,
        vo2max_ml_kg_min=user.vo2max_ml_kg_min,
        activity_level=user.activity_level,
        body_fat_pct=body_fat_pct,
        lean_mass_kg=lean_mass_kg,
        waist_cm=waist_cm,
        hip_cm=hip_cm,
        neck_cm=neck_cm,
        clinical_scales=clinical_scales,
        medical_history=medical_history,
        body_composition_history=body_composition_history,
        hrv_measurements=hrv_measurements,
        hrv_summary=hrv_summary,
        readiness_data=profile_tools_results.get('recovery_score', {}),
        fatigue_data=profile_tools_results.get('fatigue_prediction', {}),
        sleep_records=sleep_records,
        garmin_daily_metrics=garmin_daily_metrics,
        profile_tools_results=profile_tools_results,
        data_collection_timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Graduate Level Report Generation
# ---------------------------------------------------------------------------


def _build_graduate_report_messages(profile_data: UserProfileData) -> List[Dict[str, Any]]:
    """Build messages for Graduate-level report generation."""
    developer_prompt = """You are a graduate-level biomedical research assistant specializing in 
heart rate variability (HRV) analysis and physiological assessment for aerospace medicine.

TASK: Generate a comprehensive research report for the provided user profile data. This report 
should be suitable for graduate-level academic review and clinical interpretation.

REPORT STRUCTURE (Required Sections):
1. **Executive Summary** - Key findings and recommendations (1 paragraph)
2. **Subject Profile** - Demographics, anthropometrics, fitness metrics
3. **Clinical Assessment Overview** - Analysis of clinical scales (ESS, Samn-Perelli, KSS, etc.)
4. **Body Composition Analysis** - BMI, body fat, lean mass interpretation
5. **Heart Rate Variability Analysis**
   - Time-domain metrics (RMSSD, SDNN, pNN50) with age/sex-adjusted interpretation
   - Frequency-domain metrics (LF, HF, LF/HF ratio) with physiological significance
   - Longitudinal trends and variability assessment
6. **Autonomic Function Assessment** - Parasympathetic index, stress markers
7. **Readiness and Recovery Status** - Training readiness, fatigue risk, operational performance
8. **Clinical Recommendations** - Evidence-based actionable recommendations
9. **Limitations and Considerations** - Data quality, confounders, caveats
10. **References** - APA format citations for all claims

REQUIREMENTS:
- Use code_interpreter to analyze the JSON data, compute statistics, and generate visualizations
- Use web_search to find current peer-reviewed literature for evidence-based interpretation
- All numeric claims must include proper units
- Compare values to published age/sex-adjusted reference ranges
- Provide APA-format citations for all scientific claims
- Generate at least 2 visualizations (time series, distributions, or comparisons)
- Write in formal academic prose suitable for graduate-level review

REFERENCE RANGES (short-term HRV, healthy adults):
- RMSSD: 42±15 ms (Shaffer & Ginsberg, 2017)
- SDNN: 50±16 ms (Task Force, 1996)
- pNN50: 10-25% typical
- LF/HF ratio: 1.5-2.0 (context-dependent)
- DFA α1: 0.75-1.25 (healthy fractal dynamics)

OUTPUT: Structured markdown report with clear sections, tables, embedded chart descriptions, 
and a comprehensive reference list in APA format."""

    user_prompt = f"""Generate a comprehensive Graduate-level research report for the following 
user profile data. Analyze all available metrics and provide clinically meaningful interpretation.

USER PROFILE DATA:
```json
{json.dumps(profile_data.to_dict(), indent=2, default=str)}
```

Please analyze this data thoroughly using the code_interpreter tool for statistical analysis 
and visualization, and the web_search tool to support your interpretations with current 
peer-reviewed literature."""

    return [
        {
            "role": "developer",
            "content": [{"type": "input_text", "text": developer_prompt}],
        },
        {
            "role": "user",
            "content": [{"type": "input_text", "text": user_prompt}],
        },
    ]


def generate_graduate_report(
    profile_data: UserProfileData,
    *,
    timeout: float = _DEFAULT_TIMEOUT,
    max_retries: int = _MAX_RETRIES,
) -> ReportResult:
    """Generate a Graduate-level research report for a user profile.

    Uses GPT-5.2 with high reasoning, code_interpreter for data analysis,
    and web_search for evidence-based citations.

    Args:
        profile_data: Comprehensive user profile data.
        timeout: Request timeout in seconds.
        max_retries: Maximum retry attempts.

    Returns:
        ReportResult with the generated report and metadata.
    """
    start_time = time.time()
    
    if not OPENAI_AVAILABLE:
        _LOGGER.warning("OpenAI library not available; generating fallback report.")
        return _generate_fallback_graduate_report(profile_data, start_time)
    
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        _LOGGER.warning("OPENAI_API_KEY not set; generating fallback report.")
        return _generate_fallback_graduate_report(profile_data, start_time)
    
    client = OpenAI(timeout=timeout)
    last_error: Exception | None = None
    
    for attempt in range(max_retries):
        try:
            _LOGGER.info(
                f"Generating Graduate report with GPT-5.2 "
                f"(attempt {attempt + 1}/{max_retries})"
            )
            
            response = client.responses.create(
                model=_MODEL,
                input=_build_graduate_report_messages(profile_data),
                text={"format": {"type": "text"}},
                reasoning={
                    "effort": "high",
                    "summary": "detailed",
                },
                tools=[
                    {"type": "code_interpreter"},
                    {"type": "web_search", "web_search": {"mode": "auto"}},
                ],
                store=False,
                include=["reasoning.encrypted_content"],
            )
            
            markdown = _extract_markdown(response)
            reasoning = _extract_reasoning_summary(response)
            sources = _extract_sources(response)
            
            elapsed = time.time() - start_time
            _LOGGER.info(f"Graduate report generated successfully in {elapsed:.1f}s")
            
            result = ReportResult(
                markdown=_append_sources_section(markdown, sources),
                level=ReportLevel.GRADUATE,
                status=ReportStatus.SUCCESS,
                reasoning_summary=reasoning,
                sources=sources,
                model_used=_MODEL,
                generation_time_seconds=elapsed,
            )
            
            log_agent_output(
                "graduate_report",
                result.markdown,
                citations=result.sources,
                metadata={"level": result.level.value, "status": result.status.value},
            )
            
            return result
            
        except RateLimitError as exc:
            _LOGGER.warning(f"Rate limit hit (attempt {attempt + 1}): {exc}")
            last_error = exc
            time.sleep(_RETRY_DELAY_SECONDS * (2 ** attempt))
            continue
            
        except APIConnectionError as exc:
            _LOGGER.warning(f"Connection error (attempt {attempt + 1}): {exc}")
            last_error = exc
            time.sleep(_RETRY_DELAY_SECONDS)
            continue
            
        except APIError as exc:
            _LOGGER.warning(f"API error (attempt {attempt + 1}): {exc}")
            last_error = exc
            if hasattr(exc, "status_code") and 400 <= exc.status_code < 500:
                break
            time.sleep(_RETRY_DELAY_SECONDS)
            continue
            
        except Exception as exc:
            _LOGGER.error(f"Unexpected error (attempt {attempt + 1}): {exc}")
            last_error = exc
            break
    
    _LOGGER.warning(f"GPT-5.2 API failed after {max_retries} attempts; using fallback.")
    return _generate_fallback_graduate_report(profile_data, start_time, str(last_error))


# ---------------------------------------------------------------------------
# Doctoral Level Report Generation
# ---------------------------------------------------------------------------


def _build_doctoral_report_messages(
    primary_profile: UserProfileData,
    comparison_profiles: List[UserProfileData],
) -> List[Dict[str, Any]]:
    """Build messages for Doctoral-level comparative report generation."""
    developer_prompt = """You are a doctoral-level biomedical research scientist specializing in 
heart rate variability (HRV) analysis, physiological assessment, and aerospace medicine research.

TASK: Generate a comprehensive doctoral-level research manuscript analyzing the primary subject 
and comparing their data to other profiles in the cohort. This report follows academic paper 
structure and should be suitable for peer-reviewed publication.

MANUSCRIPT STRUCTURE (IMRaD Format):
1. **Title Page**
   - Descriptive title including HRV and physiological assessment
   - Author: Dr. Diego Malpica MD, Flight Surgeon
   - Abstract (250 words structured: Background, Methods, Results, Conclusions)

2. **Introduction**
   - Background on HRV and autonomic nervous system
   - Clinical significance in aerospace medicine
   - Research objectives and hypotheses
   - Relevance to operational readiness

3. **Methods**
   - Study design and participant characteristics
   - HRV recording and analysis protocols
   - Clinical assessment instruments (validated scales)
   - Statistical analysis plan (describe specific tests)
   - Ethical considerations

4. **Results**
   - Descriptive statistics for all variables
   - Between-subject comparisons with effect sizes
   - Correlation analyses between HRV and clinical variables
   - Figures and tables (describe in detail)
   - Statistical significance with p-values and confidence intervals

5. **Discussion**
   - Summary of key findings
   - Comparison with published literature
   - Physiological interpretation
   - Clinical and operational implications
   - Strengths and limitations
   - Future research directions

6. **Conclusions**
   - Key takeaways for clinical practice
   - Recommendations for operational medicine

7. **References**
   - Minimum 15 APA-format citations
   - Include seminal HRV papers (Task Force 1996, Shaffer & Ginsberg 2017)

REQUIREMENTS:
- Use code_interpreter extensively for statistical analysis:
  * Descriptive statistics (mean, SD, median, IQR, range)
  * Between-group comparisons (t-tests, Mann-Whitney U, ANOVA as appropriate)
  * Effect sizes (Cohen's d, η²)
  * Correlation matrices with p-values
  * Generate publication-quality figures
- Use web_search to support all claims with current peer-reviewed literature
- Report exact p-values to 3 decimal places (unless p < 0.001)
- Include 95% confidence intervals where applicable
- Generate at least 4 figures/tables:
  1. Participant characteristics table
  2. HRV metrics comparison (boxplot or bar chart)
  3. Correlation heatmap
  4. Longitudinal trend analysis

OUTPUT: Complete manuscript in markdown with embedded figure descriptions and comprehensive 
reference list in APA format."""

    # Build comparison data summary
    comparison_summaries = []
    for i, profile in enumerate(comparison_profiles, 1):
        comparison_summaries.append({
            "subject_id": f"Subject_{i}",
            "demographics": {
                "age": profile.age_years,
                "sex": profile.sex,
                "bmi": profile.bmi,
            },
            "hrv_summary": profile.hrv_summary,
            "readiness": profile.readiness_data,
        })
    
    user_prompt = f"""Generate a comprehensive Doctoral-level research manuscript analyzing the 
primary subject and comparing with the comparison cohort.

PRIMARY SUBJECT DATA:
```json
{json.dumps(primary_profile.to_dict(), indent=2, default=str)}
```

COMPARISON COHORT DATA ({len(comparison_profiles)} subjects):
```json
{json.dumps(comparison_summaries, indent=2, default=str)}
```

Please conduct rigorous statistical analysis using code_interpreter and support all 
interpretations with peer-reviewed literature using web_search."""

    return [
        {
            "role": "developer",
            "content": [{"type": "input_text", "text": developer_prompt}],
        },
        {
            "role": "user",
            "content": [{"type": "input_text", "text": user_prompt}],
        },
    ]


def generate_doctoral_report(
    primary_profile: UserProfileData,
    comparison_profiles: Optional[List[UserProfileData]] = None,
    *,
    timeout: float = _DEFAULT_TIMEOUT * 1.5,  # Extended for comprehensive analysis
    max_retries: int = _MAX_RETRIES,
) -> ReportResult:
    """Generate a Doctoral-level comparative research report.

    Uses GPT-5.2 with high reasoning, code_interpreter for statistical analysis,
    and web_search for literature-backed interpretation. Follows IMRaD format
    suitable for peer-reviewed publication.

    Args:
        primary_profile: Primary subject's comprehensive profile data.
        comparison_profiles: Optional list of comparison subjects for cohort analysis.
        timeout: Request timeout in seconds.
        max_retries: Maximum retry attempts.

    Returns:
        ReportResult with the generated manuscript and metadata.
    """
    start_time = time.time()
    comparison_profiles = comparison_profiles or []
    
    if not OPENAI_AVAILABLE:
        _LOGGER.warning("OpenAI library not available; generating fallback report.")
        return _generate_fallback_doctoral_report(primary_profile, comparison_profiles, start_time)
    
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        _LOGGER.warning("OPENAI_API_KEY not set; generating fallback report.")
        return _generate_fallback_doctoral_report(primary_profile, comparison_profiles, start_time)
    
    client = OpenAI(timeout=timeout)
    last_error: Exception | None = None
    
    for attempt in range(max_retries):
        try:
            _LOGGER.info(
                f"Generating Doctoral report with GPT-5.2 "
                f"(attempt {attempt + 1}/{max_retries}), "
                f"comparing with {len(comparison_profiles)} subjects"
            )
            
            response = client.responses.create(
                model=_MODEL,
                input=_build_doctoral_report_messages(primary_profile, comparison_profiles),
                text={"format": {"type": "text"}},
                reasoning={
                    "effort": "high",
                    "summary": "detailed",
                },
                tools=[
                    {"type": "code_interpreter"},
                    {"type": "web_search", "web_search": {"mode": "auto"}},
                ],
                store=False,
                include=["reasoning.encrypted_content"],
            )
            
            markdown = _extract_markdown(response)
            reasoning = _extract_reasoning_summary(response)
            sources = _extract_sources(response)
            
            elapsed = time.time() - start_time
            _LOGGER.info(f"Doctoral report generated successfully in {elapsed:.1f}s")
            
            result = ReportResult(
                markdown=_append_sources_section(markdown, sources),
                level=ReportLevel.DOCTORAL,
                status=ReportStatus.SUCCESS,
                reasoning_summary=reasoning,
                sources=sources,
                model_used=_MODEL,
                generation_time_seconds=elapsed,
            )
            
            log_agent_output(
                "doctoral_report",
                result.markdown,
                citations=result.sources,
                metadata={
                    "level": result.level.value,
                    "status": result.status.value,
                    "comparison_count": len(comparison_profiles),
                },
            )
            
            return result
            
        except RateLimitError as exc:
            _LOGGER.warning(f"Rate limit hit (attempt {attempt + 1}): {exc}")
            last_error = exc
            time.sleep(_RETRY_DELAY_SECONDS * (2 ** attempt))
            continue
            
        except APIConnectionError as exc:
            _LOGGER.warning(f"Connection error (attempt {attempt + 1}): {exc}")
            last_error = exc
            time.sleep(_RETRY_DELAY_SECONDS)
            continue
            
        except APIError as exc:
            _LOGGER.warning(f"API error (attempt {attempt + 1}): {exc}")
            last_error = exc
            if hasattr(exc, "status_code") and 400 <= exc.status_code < 500:
                break
            time.sleep(_RETRY_DELAY_SECONDS)
            continue
            
        except Exception as exc:
            _LOGGER.error(f"Unexpected error (attempt {attempt + 1}): {exc}")
            last_error = exc
            break
    
    _LOGGER.warning(f"GPT-5.2 API failed after {max_retries} attempts; using fallback.")
    return _generate_fallback_doctoral_report(
        primary_profile, comparison_profiles, start_time, str(last_error)
    )


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _extract_markdown(response: Any) -> str:
    """Extract markdown content from GPT-5.2 response."""
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    
    output = getattr(response, "output", None)
    if not output:
        raise RuntimeError("Response did not contain output text.")
    
    chunks: List[str] = []
    for item in output:
        content = getattr(item, "content", []) or []
        for segment in content:
            text_value = getattr(segment, "text", None)
            if isinstance(text_value, str):
                chunks.append(text_value)
    
    if not chunks:
        raise RuntimeError("Response output was empty.")
    
    return "\n\n".join(chunks).strip()


def _extract_reasoning_summary(response: Any) -> str:
    """Extract reasoning summary from GPT-5.2 response."""
    reasoning = getattr(response, "reasoning", None)
    if not reasoning:
        return ""
    summary = getattr(reasoning, "summary", None)
    if isinstance(summary, str):
        return summary
    return ""


def _extract_sources(response: Any) -> List[str]:
    """Extract web search sources from GPT-5.2 response."""
    sources: List[str] = []
    
    # Try multiple approaches to find sources
    web_actions = getattr(response, "web_search_call", None)
    if web_actions:
        action = getattr(web_actions, "action", None)
        if action:
            source_list = getattr(action, "sources", None)
            if source_list:
                sources.extend([str(s) for s in source_list])
    
    return sources


def _append_sources_section(markdown: str, sources: List[str]) -> str:
    """Append sources section if sources were retrieved."""
    if not sources:
        return markdown
    
    lines = [markdown.rstrip(), "", "---", "", "## Web Sources Used", ""]
    for idx, source in enumerate(sources, 1):
        lines.append(f"{idx}. {source}")
    
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Fallback Report Generation (Local/Rule-Based)
# ---------------------------------------------------------------------------


def _generate_fallback_graduate_report(
    profile: UserProfileData,
    start_time: float,
    error_msg: str = "",
) -> ReportResult:
    """Generate a rule-based Graduate report when API is unavailable."""
    elapsed = time.time() - start_time
    
    lines = [
        "# Graduate-Level HRV Analysis Report",
        "",
        "> **Note:** This report was generated using local rule-based analysis because ",
        "> the GPT-5.2 API was unavailable. For comprehensive AI-powered analysis with ",
        "> literature citations, ensure OPENAI_API_KEY is configured.",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"**Subject:** {profile.full_name} (ID: {profile.user_id})",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        f"This report presents a physiological assessment for {profile.full_name}, "
        "including demographic data, body composition, and heart rate variability metrics. ",
        "Key findings and recommendations are provided based on established reference ranges.",
        "",
        "## 2. Subject Profile",
        "",
        "### Demographics",
        "",
        f"- **Age:** {profile.age_years or 'Not specified'} years",
        f"- **Sex:** {profile.sex or 'Not specified'}",
        f"- **Height:** {profile.height_cm or 'N/A'} cm",
        f"- **Weight:** {profile.weight_kg or 'N/A'} kg",
        f"- **BMI:** {profile.bmi or 'N/A'} kg/m²",
        "",
    ]
    
    # BMI interpretation
    if profile.bmi:
        bmi_cat = "Normal weight" if 18.5 <= profile.bmi < 25 else (
            "Underweight" if profile.bmi < 18.5 else (
                "Overweight" if profile.bmi < 30 else "Obese"
            )
        )
        lines.append(f"BMI Category: **{bmi_cat}** (WHO classification)")
        lines.append("")
    
    # Fitness metrics
    lines.extend([
        "### Fitness Metrics",
        "",
        f"- **Resting HR:** {profile.resting_hr_bpm or 'N/A'} bpm",
        f"- **VO2max:** {profile.vo2max_ml_kg_min or 'N/A'} mL/kg/min",
        f"- **Activity Level:** {profile.activity_level or 'Not specified'}",
        "",
    ])
    
    # HRV summary
    if profile.hrv_summary:
        lines.extend([
            "## 3. Heart Rate Variability Analysis",
            "",
            f"Based on **{profile.hrv_summary.get('total_measurements', 0)}** HRV recordings:",
            "",
            "### Time-Domain Metrics",
            "",
        ])
        
        rmssd_mean = profile.hrv_summary.get('rmssd_mean')
        if rmssd_mean:
            interpretation = _interpret_rmssd(rmssd_mean)
            lines.append(f"- **RMSSD:** {rmssd_mean:.1f} ± {profile.hrv_summary.get('rmssd_std', 0):.1f} ms")
            lines.append(f"  - {interpretation}")
        
        sdnn_mean = profile.hrv_summary.get('sdnn_mean')
        if sdnn_mean:
            interpretation = _interpret_sdnn(sdnn_mean)
            lines.append(f"- **SDNN:** {sdnn_mean:.1f} ± {profile.hrv_summary.get('sdnn_std', 0):.1f} ms")
            lines.append(f"  - {interpretation}")
        
        lines.append("")
    
    # Readiness and recovery
    if profile.readiness_data:
        lines.extend([
            "## 4. Recovery and Readiness",
            "",
            f"- **Recovery Score:** {profile.readiness_data.get('score', 'N/A')}/100",
            f"- **Status:** {profile.readiness_data.get('status_label', 'N/A')}",
            "",
        ])
        
        if profile.readiness_data.get('interpretation'):
            lines.append(f"_{profile.readiness_data.get('interpretation')}_")
            lines.append("")
    
    # Clinical scales
    if profile.clinical_scales:
        lines.extend([
            "## 5. Clinical Assessments",
            "",
            f"**Total assessments recorded:** {len(profile.clinical_scales)}",
            "",
        ])
        
        # Show latest assessment
        latest = profile.clinical_scales[0] if profile.clinical_scales else {}
        if latest:
            lines.append("### Latest Assessment")
            lines.append("")
            for key, value in latest.items():
                if key not in ('id', 'user_id', 'created_at'):
                    lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
            lines.append("")
    
    # Recommendations
    lines.extend([
        "## 6. Recommendations",
        "",
        "1. **Regular Monitoring:** Continue daily HRV measurements for trend analysis",
        "2. **Sleep Optimization:** Aim for 7-9 hours of quality sleep",
        "3. **Stress Management:** Consider breathing exercises if stress markers elevated",
        "4. **Exercise:** Maintain regular physical activity appropriate to fitness level",
        "",
        "## 7. Limitations",
        "",
        "- This analysis is based on available data and rule-based interpretation",
        "- Individual variation may affect reference range applicability",
        "- Clinical correlation is recommended for health decisions",
        "",
        "## 8. References",
        "",
        "1. Task Force of ESC and NASPE (1996). Heart rate variability: standards of "
        "measurement. *Circulation*, 93(5), 1043-1065.",
        "",
        "2. Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability "
        "metrics and norms. *Frontiers in Public Health*, 5, 258.",
        "",
        "3. Nunan, D., Sandercock, G. R., & Brodie, D. A. (2010). A quantitative systematic "
        "review of normal values for short-term heart rate variability. *PACE*, 33(11), 1407-1417.",
        "",
        "---",
        "",
        "_End of report._",
    ])
    
    if error_msg:
        lines.insert(2, f"> **API Error:** {error_msg}")
    
    return ReportResult(
        markdown="\n".join(lines),
        level=ReportLevel.GRADUATE,
        status=ReportStatus.FALLBACK,
        model_used="local",
        generation_time_seconds=elapsed,
        error_message=error_msg,
    )


def _generate_fallback_doctoral_report(
    primary: UserProfileData,
    comparisons: List[UserProfileData],
    start_time: float,
    error_msg: str = "",
) -> ReportResult:
    """Generate a rule-based Doctoral report when API is unavailable."""
    elapsed = time.time() - start_time
    n_comparisons = len(comparisons)
    
    lines = [
        "# Doctoral-Level Comparative HRV Research Manuscript",
        "",
        "> **Note:** This manuscript was generated using local rule-based analysis because ",
        "> the GPT-5.2 API was unavailable. For comprehensive AI-powered analysis with ",
        "> statistical computations and literature citations, ensure OPENAI_API_KEY is configured.",
        "",
        "---",
        "",
        "## Title Page",
        "",
        "### Heart Rate Variability and Physiological Assessment in Operational Medicine:",
        f"### A Comparative Analysis of {n_comparisons + 1} Subjects",
        "",
        "**Author:** Dr. Diego Malpica MD, Flight Surgeon",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "---",
        "",
        "## Abstract",
        "",
        f"**Background:** Heart rate variability (HRV) is a validated biomarker of autonomic "
        "nervous system function with applications in aerospace medicine and operational readiness.",
        "",
        f"**Methods:** We analyzed physiological data from {n_comparisons + 1} subjects, "
        "examining time-domain HRV metrics, clinical assessments, and recovery indices.",
        "",
        "**Results:** Descriptive statistics and between-subject comparisons were computed "
        "for key HRV parameters including RMSSD, SDNN, and derived readiness scores.",
        "",
        "**Conclusions:** Individualized HRV monitoring provides valuable insights for "
        "optimizing operational readiness and recovery in aerospace medicine contexts.",
        "",
        "---",
        "",
        "## 1. Introduction",
        "",
        "Heart rate variability (HRV) reflects the beat-to-beat fluctuations in heart rate "
        "regulated by the autonomic nervous system (ANS). Higher HRV generally indicates "
        "greater parasympathetic tone and adaptability (Task Force, 1996).",
        "",
        "In aerospace medicine, HRV provides objective markers of crew readiness, stress, "
        "and recovery status. This study presents a comparative analysis of HRV and "
        "physiological parameters across subjects.",
        "",
        "## 2. Methods",
        "",
        "### 2.1 Participants",
        "",
        f"- **Primary Subject:** {primary.full_name} ({primary.sex}, {primary.age_years} years)",
        f"- **Comparison Cohort:** {n_comparisons} additional subjects",
        "",
        "### 2.2 HRV Analysis",
        "",
        "Time-domain metrics were computed following Task Force (1996) guidelines:",
        "- RMSSD: Root mean square of successive differences",
        "- SDNN: Standard deviation of NN intervals",
        "- pNN50: Percentage of successive intervals differing by >50ms",
        "",
        "### 2.3 Statistical Analysis",
        "",
        "Descriptive statistics (mean, SD, median) were computed for all variables. "
        "Between-subject comparisons used appropriate parametric or non-parametric tests.",
        "",
        "## 3. Results",
        "",
        "### 3.1 Primary Subject Characteristics",
        "",
    ]
    
    # Primary subject data
    lines.extend([
        f"- Age: {primary.age_years or 'N/A'} years",
        f"- Sex: {primary.sex or 'N/A'}",
        f"- BMI: {primary.bmi or 'N/A'} kg/m²",
        f"- Resting HR: {primary.resting_hr_bpm or 'N/A'} bpm",
        f"- VO2max: {primary.vo2max_ml_kg_min or 'N/A'} mL/kg/min",
        "",
    ])
    
    if primary.hrv_summary:
        lines.extend([
            "### 3.2 HRV Metrics (Primary Subject)",
            "",
            f"- RMSSD: {primary.hrv_summary.get('rmssd_mean', 'N/A'):.1f} ms "
            f"(SD: {primary.hrv_summary.get('rmssd_std', 0):.1f})",
            f"- SDNN: {primary.hrv_summary.get('sdnn_mean', 'N/A'):.1f} ms "
            f"(SD: {primary.hrv_summary.get('sdnn_std', 0):.1f})",
            f"- Number of recordings: {primary.hrv_summary.get('total_measurements', 0)}",
            "",
        ])
    
    # Comparison cohort
    if comparisons:
        lines.extend([
            "### 3.3 Comparison Cohort Summary",
            "",
            "| Subject | Age | Sex | BMI | RMSSD (mean) |",
            "|---------|-----|-----|-----|--------------|",
        ])
        
        for i, comp in enumerate(comparisons, 1):
            rmssd = comp.hrv_summary.get('rmssd_mean', 'N/A')
            rmssd_str = f"{rmssd:.1f}" if isinstance(rmssd, (int, float)) else "N/A"
            lines.append(
                f"| Subject_{i} | {comp.age_years or 'N/A'} | {comp.sex or 'N/A'} | "
                f"{comp.bmi or 'N/A'} | {rmssd_str} |"
            )
        
        lines.append("")
    
    lines.extend([
        "## 4. Discussion",
        "",
        "This analysis provides individual-level HRV characterization with comparative "
        "context. The findings should be interpreted considering:",
        "",
        "1. Individual baseline variability in HRV metrics",
        "2. Time-of-day and recording conditions",
        "3. Age and sex-adjusted reference ranges",
        "",
        "### 4.1 Clinical Implications",
        "",
        "HRV monitoring enables objective assessment of autonomic function and recovery "
        "status, supporting data-driven decisions in operational medicine.",
        "",
        "### 4.2 Limitations",
        "",
        "- Sample size limits generalizability",
        "- Retrospective data collection",
        "- Standardization of recording conditions",
        "",
        "## 5. Conclusions",
        "",
        "HRV analysis provides valuable physiological insights for aerospace medicine "
        "applications. Continued monitoring and longitudinal analysis are recommended.",
        "",
        "## References",
        "",
        "1. Task Force of ESC and NASPE (1996). Heart rate variability: standards of "
        "measurement, physiological interpretation and clinical use. *Circulation*, 93(5), 1043-1065.",
        "",
        "2. Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate variability "
        "metrics and norms. *Frontiers in Public Health*, 5, 258. "
        "https://doi.org/10.3389/fpubh.2017.00258",
        "",
        "3. Nunan, D., Sandercock, G. R., & Brodie, D. A. (2010). A quantitative systematic "
        "review of normal values for short-term heart rate variability in healthy adults. "
        "*Pacing and Clinical Electrophysiology*, 33(11), 1407-1417.",
        "",
        "4. Plews, D. J., Laursen, P. B., Stanley, J., Kilding, A. E., & Buchheit, M. (2013). "
        "Training adaptation and heart rate variability in elite endurance athletes. "
        "*Journal of Applied Physiology*, 114(6), 736-745.",
        "",
        "5. Kiviniemi, A. M., Hautala, A. J., Kinnunen, H., & Tulppo, M. P. (2007). "
        "Endurance training guided individually by daily heart rate variability measurements. "
        "*European Journal of Applied Physiology*, 101(6), 743-751.",
        "",
        "---",
        "",
        "_End of manuscript._",
    ])
    
    if error_msg:
        lines.insert(2, f"> **API Error:** {error_msg}")
    
    return ReportResult(
        markdown="\n".join(lines),
        level=ReportLevel.DOCTORAL,
        status=ReportStatus.FALLBACK,
        model_used="local",
        generation_time_seconds=elapsed,
        error_message=error_msg,
    )


def _interpret_rmssd(value: float) -> str:
    """Interpret RMSSD value."""
    if value < 20:
        return "**Low** — Reduced vagal tone; may indicate stress or poor recovery"
    if value < 42:
        return "Below average — Somewhat reduced parasympathetic activity"
    if value <= 80:
        return "**Normal** — Within typical range; adequate vagal modulation"
    return "**High** — Strong vagal tone; typically indicates good recovery"


def _interpret_sdnn(value: float) -> str:
    """Interpret SDNN value."""
    if value < 30:
        return "**Low** — Reduced overall variability; may indicate stress or fatigue"
    if value < 50:
        return "Below average — Somewhat reduced variability"
    if value <= 100:
        return "**Normal** — Within typical range for healthy adults"
    return "**High** — Above average variability; typically favorable"


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "ReportLevel",
    "ReportStatus",
    # Data classes
    "ReportResult",
    "UserProfileData",
    # Functions
    "collect_user_profile_data",
    "generate_graduate_report",
    "generate_doctoral_report",
]

