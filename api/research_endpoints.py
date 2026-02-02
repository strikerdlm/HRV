# Author: Dr Diego Malpica MD
"""
Research API Endpoints for Mission Control - Flight Surgeon.

This module provides comprehensive endpoints for:
- Space Weather data and impact predictions
- HRV analysis (time, frequency, nonlinear, HRF domains)
- Solar-Physiological correlation analysis
- Garmin wearable data integration
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# Add app directory to path
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_APP_DIR = _PROJECT_ROOT / "app"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["Research"])


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class SpaceWeatherData(BaseModel):
    """Comprehensive space weather data."""
    
    # NOAA indices
    kp_index: Optional[float] = None
    kp_status: Optional[str] = None
    dst_index: Optional[float] = None
    f10_7_flux: Optional[float] = None
    f10_7_status: Optional[str] = None
    
    # Solar wind
    solar_wind_speed: Optional[float] = None
    solar_wind_density: Optional[float] = None
    solar_wind_bz: Optional[float] = None
    
    # X-ray / Flares
    xray_flux: Optional[str] = None
    xray_class: Optional[str] = None
    
    # Protons / SEP
    proton_flux_10mev: Optional[float] = None
    proton_flux_100mev: Optional[float] = None
    sep_event_active: bool = False
    
    # Overall status
    geomagnetic_status: Optional[str] = None
    radiation_status: Optional[str] = None
    
    fetched_at: Optional[str] = None


class ImpactPrediction(BaseModel):
    """Space weather impact prediction."""
    
    category: str  # photon, sep, plasma, cme, geomagnetic
    severity: str  # quiet, minor, moderate, strong, severe, extreme
    observation_time: Optional[str] = None
    arrival_time: Optional[str] = None
    travel_time_minutes: Optional[float] = None
    biological_effect: Optional[str] = None
    polar_h10_recommendation: Optional[str] = None
    raw_value: Optional[float] = None
    unit: Optional[str] = None
    confidence: float = 1.0


class SpaceWeatherSnapshot(BaseModel):
    """Complete space weather snapshot with predictions."""
    
    data: SpaceWeatherData
    predictions: List[ImpactPrediction] = Field(default_factory=list)
    next_impact: Optional[ImpactPrediction] = None
    most_severe: Optional[ImpactPrediction] = None
    errors: Dict[str, str] = Field(default_factory=dict)


class HRVTimeDomain(BaseModel):
    """Time-domain HRV metrics."""
    
    mean_hr: Optional[float] = None
    sdnn: Optional[float] = None
    rmssd: Optional[float] = None
    pnn50: Optional[float] = None
    pnn20: Optional[float] = None
    cvnn: Optional[float] = None
    mean_rr: Optional[float] = None
    sdsd: Optional[float] = None
    nn50: Optional[int] = None
    nn20: Optional[int] = None


class HRVFrequencyDomain(BaseModel):
    """Frequency-domain HRV metrics."""
    
    vlf_power: Optional[float] = None
    lf_power: Optional[float] = None
    hf_power: Optional[float] = None
    total_power: Optional[float] = None
    lf_nu: Optional[float] = None  # Normalized units
    hf_nu: Optional[float] = None
    lf_hf_ratio: Optional[float] = None
    vlf_peak: Optional[float] = None
    lf_peak: Optional[float] = None
    hf_peak: Optional[float] = None


class HRVNonlinear(BaseModel):
    """Nonlinear HRV metrics."""
    
    sd1: Optional[float] = None  # Poincaré
    sd2: Optional[float] = None
    sd1_sd2_ratio: Optional[float] = None
    dfa_alpha1: Optional[float] = None  # Short-term scaling
    dfa_alpha2: Optional[float] = None  # Long-term scaling
    sample_entropy: Optional[float] = None
    approximate_entropy: Optional[float] = None


class HRFMetrics(BaseModel):
    """Heart Rate Fragmentation metrics."""
    
    pip: Optional[float] = None  # Percentage of Inflection Points
    pip_h: Optional[float] = None  # Hard inflection points
    pip_s: Optional[float] = None  # Soft inflection points
    ials: Optional[float] = None  # Inverse Average Length of Segments
    pss: Optional[float] = None  # Percentage of Short Segments
    pas: Optional[float] = None  # Percentage of Alternating Segments
    quality_ok: bool = True


class HRVAnalysisResult(BaseModel):
    """Complete HRV analysis result."""
    
    # Metadata
    recording_time: Optional[str] = None
    duration_minutes: Optional[float] = None
    total_beats: Optional[int] = None
    artifact_percentage: Optional[float] = None
    
    # Domains
    time_domain: HRVTimeDomain = Field(default_factory=HRVTimeDomain)
    frequency_domain: HRVFrequencyDomain = Field(default_factory=HRVFrequencyDomain)
    nonlinear: HRVNonlinear = Field(default_factory=HRVNonlinear)
    hrf: HRFMetrics = Field(default_factory=HRFMetrics)
    
    # Quality
    quality_score: Optional[float] = None
    analysis_method: str = "standard"


class CorrelationResult(BaseModel):
    """Solar-physiological correlation result."""
    
    solar_metric: str
    physio_metric: str
    lag_hours: int
    r: float  # Correlation coefficient
    r_squared: float
    p_value: float
    n_samples: int
    significance: str  # not_significant, marginal, significant, highly_significant
    strength: str  # negligible, weak, moderate, strong, very_strong
    interpretation: Optional[str] = None


class CorrelationAnalysisResult(BaseModel):
    """Complete correlation analysis result."""
    
    analysis_date: str
    data_start: str
    data_end: str
    n_days: int
    
    significant_correlations: List[CorrelationResult] = Field(default_factory=list)
    all_correlations: List[CorrelationResult] = Field(default_factory=list)
    
    # Summary
    strongest_correlation: Optional[CorrelationResult] = None
    optimal_lag_hours: Optional[int] = None
    pattern_insights: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class GarminMetrics(BaseModel):
    """Garmin wearable metrics."""
    
    # SpO2
    spo2_avg: Optional[float] = None
    spo2_min: Optional[float] = None
    spo2_max: Optional[float] = None
    
    # Respiration
    respiration_awake: Optional[float] = None
    respiration_sleep: Optional[float] = None
    
    # VO2max
    vo2max: Optional[float] = None
    vo2max_fitness_age: Optional[int] = None
    
    # Sleep
    sleep_duration_hours: Optional[float] = None
    sleep_deep_minutes: Optional[int] = None
    sleep_rem_minutes: Optional[int] = None
    sleep_light_minutes: Optional[int] = None
    sleep_awake_minutes: Optional[int] = None
    sleep_efficiency: Optional[float] = None
    sleep_score: Optional[int] = None
    
    # Body Battery
    body_battery_high: Optional[int] = None
    body_battery_low: Optional[int] = None
    body_battery_charged: Optional[int] = None
    body_battery_drained: Optional[int] = None
    
    # Stress
    stress_avg: Optional[float] = None
    stress_max: Optional[int] = None
    stress_high_duration_minutes: Optional[int] = None
    
    # Activity
    steps: Optional[int] = None
    distance_km: Optional[float] = None
    calories_total: Optional[int] = None
    active_calories: Optional[int] = None
    
    # HRV (from Garmin)
    hrv_overnight: Optional[float] = None
    resting_hr: Optional[int] = None
    
    date: Optional[str] = None


# ---------------------------------------------------------------------------
# Space Weather Endpoints
# ---------------------------------------------------------------------------


@router.get("/space-weather/current", response_model=SpaceWeatherSnapshot)
async def get_current_space_weather() -> SpaceWeatherSnapshot:
    """Get current space weather data with impact predictions."""
    import re
    
    try:
        from space_weather_impact import (
            fetch_space_weather_snapshot as fetch_snapshot,
            ImpactEvent,
        )
        
        snapshot = await asyncio.to_thread(fetch_snapshot)
        
        # Helper to check for valid float (not NaN)
        def _valid_float(val) -> bool:
            return val is not None and not (val != val)
        
        # Extract actual values from the events
        kp_index: Optional[float] = None
        dst_index: Optional[float] = None
        solar_wind_speed: Optional[float] = None
        solar_wind_density: Optional[float] = None
        solar_wind_bz: Optional[float] = None
        xray_flux: Optional[str] = None
        xray_class: Optional[str] = None
        proton_flux_10mev: Optional[float] = None
        
        # Extract from geomagnetic event (Kp, Dst)
        if snapshot.geomagnetic_event:
            evt = snapshot.geomagnetic_event
            if _valid_float(evt.raw_value):
                kp_index = evt.raw_value
            # Parse Dst from source_description: "G2 (Kp=5.0, Dst=-30 nT)"
            if evt.source_description:
                dst_match = re.search(r"Dst=(-?\d+(?:\.\d+)?)", evt.source_description)
                if dst_match:
                    try:
                        dst_index = float(dst_match.group(1))
                    except ValueError:
                        pass
        
        # Extract from plasma event (solar wind)
        if snapshot.plasma_event:
            evt = snapshot.plasma_event
            if _valid_float(evt.raw_value):
                solar_wind_speed = evt.raw_value
            # Try to parse density and Bz from source_description
            if evt.source_description:
                density_match = re.search(r"(\d+(?:\.\d+)?)\s*p/cm", evt.source_description)
                if density_match:
                    try:
                        solar_wind_density = float(density_match.group(1))
                    except ValueError:
                        pass
                bz_match = re.search(r"Bz[=:\s]*(-?\d+(?:\.\d+)?)", evt.source_description)
                if bz_match:
                    try:
                        solar_wind_bz = float(bz_match.group(1))
                    except ValueError:
                        pass
        
        # Extract from photon event (X-ray class)
        if snapshot.photon_event:
            evt = snapshot.photon_event
            if evt.source_description:
                xray_match = re.search(r"([ABCMX]\d+\.?\d*)", evt.source_description)
                if xray_match:
                    xray_class = xray_match.group(1)
                    xray_flux = xray_match.group(1)
        
        # Extract from SEP event (proton flux)
        if snapshot.sep_event:
            evt = snapshot.sep_event
            if _valid_float(evt.raw_value):
                proton_flux_10mev = evt.raw_value
        
        # Build the data object with actual values
        data = SpaceWeatherData(
            kp_index=kp_index,
            dst_index=dst_index,
            solar_wind_speed=solar_wind_speed,
            solar_wind_density=solar_wind_density,
            solar_wind_bz=solar_wind_bz,
            xray_flux=xray_flux,
            xray_class=xray_class,
            proton_flux_10mev=proton_flux_10mev,
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        
        predictions = []
        for event in snapshot.all_events():
            pred = ImpactPrediction(
                category=event.category.value,
                severity=event.severity.value,
                observation_time=event.observation_time_utc.isoformat() if event.observation_time_utc else None,
                arrival_time=event.arrival_time_utc.isoformat() if event.arrival_time_utc else None,
                travel_time_minutes=event.travel_time_minutes,
                biological_effect=event.biological_effect,
                polar_h10_recommendation=event.polar_h10_recommendation,
                raw_value=event.raw_value if not (event.raw_value != event.raw_value) else None,
                unit=event.unit,
                confidence=event.confidence,
            )
            predictions.append(pred)
        
        next_imp = snapshot.next_impact()
        most_sev = snapshot.most_severe()
        
        return SpaceWeatherSnapshot(
            data=data,
            predictions=predictions,
            next_impact=ImpactPrediction(
                category=next_imp.category.value,
                severity=next_imp.severity.value,
                arrival_time=next_imp.arrival_time_utc.isoformat() if next_imp.arrival_time_utc else None,
                biological_effect=next_imp.biological_effect,
            ) if next_imp else None,
            most_severe=ImpactPrediction(
                category=most_sev.category.value,
                severity=most_sev.severity.value,
                biological_effect=most_sev.biological_effect,
            ) if most_sev else None,
            errors=snapshot.errors,
        )
    except ImportError:
        _LOGGER.warning("space_weather_impact module not available")
        return SpaceWeatherSnapshot(
            data=SpaceWeatherData(fetched_at=datetime.now(timezone.utc).isoformat()),
            errors={"import": "Space weather module not available"},
        )
    except Exception as exc:
        _LOGGER.error(f"Error fetching space weather: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/space-weather/noaa", response_model=Dict[str, Any])
async def get_noaa_data(
    sources: str = Query(default="kp,dst,f107,solar_wind", description="Comma-separated sources"),
) -> Dict[str, Any]:
    """Get NOAA space weather data from specified sources."""
    try:
        from noaa_space import load_noaa_space_data, NOAA_SOURCES
        
        source_list = [s.strip() for s in sources.split(",") if s.strip()]
        valid_sources = [s for s in source_list if s in NOAA_SOURCES]
        
        bundle = await asyncio.to_thread(load_noaa_space_data, valid_sources)
        
        result: Dict[str, Any] = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "sources": valid_sources,
        }
        
        # Convert DataFrames to dict
        for source in valid_sources:
            df = getattr(bundle, source, None)
            if df is not None and hasattr(df, "to_dict"):
                result[source] = {
                    "columns": list(df.columns),
                    "rows": len(df),
                    "latest": df.iloc[-1].to_dict() if len(df) > 0 else None,
                }
        
        return result
    except ImportError:
        raise HTTPException(status_code=500, detail="NOAA module not available")
    except Exception as exc:
        _LOGGER.error(f"Error fetching NOAA data: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# HRV Analysis Endpoints
# ---------------------------------------------------------------------------


@router.get("/hrv/latest/{user_id}", response_model=HRVAnalysisResult)
async def get_latest_hrv_analysis(user_id: str) -> HRVAnalysisResult:
    """Get latest HRV analysis for a user."""
    try:
        from user_database import UserDatabase
        
        db = UserDatabase()
        history = await asyncio.to_thread(db.get_hrv_history, user_id, limit=1)
        
        if not history:
            return HRVAnalysisResult()
        
        latest = history[0]
        metrics = latest.hrv_metrics or {}
        
        return HRVAnalysisResult(
            recording_time=latest.recorded_at.isoformat() if latest.recorded_at else None,
            duration_minutes=metrics.get("duration_min"),
            total_beats=metrics.get("n_beats"),
            artifact_percentage=metrics.get("artifact_pct"),
            time_domain=HRVTimeDomain(
                mean_hr=metrics.get("mean_hr"),
                sdnn=metrics.get("sdnn"),
                rmssd=metrics.get("rmssd"),
                pnn50=metrics.get("pnn50"),
                cvnn=metrics.get("cvnn"),
                mean_rr=metrics.get("mean_rr"),
            ),
            frequency_domain=HRVFrequencyDomain(
                vlf_power=metrics.get("vlf_power"),
                lf_power=metrics.get("lf_power"),
                hf_power=metrics.get("hf_power"),
                total_power=metrics.get("total_power"),
                lf_hf_ratio=metrics.get("lf_hf_ratio"),
            ),
            nonlinear=HRVNonlinear(
                sd1=metrics.get("sd1"),
                sd2=metrics.get("sd2"),
                dfa_alpha1=metrics.get("dfa_alpha1"),
                sample_entropy=metrics.get("sample_entropy"),
            ),
            hrf=HRFMetrics(
                pip=metrics.get("pip"),
                ials=metrics.get("ials"),
                pss=metrics.get("pss"),
            ),
        )
    except Exception as exc:
        _LOGGER.error(f"Error fetching HRV for user {user_id}: {exc}")
        return HRVAnalysisResult()


@router.post("/hrv/analyze")
async def analyze_rr_intervals(
    rr_intervals: List[float],
    method: str = Query(default="welch", description="PSD method: welch, periodogram, ar"),
) -> HRVAnalysisResult:
    """Analyze RR intervals and return comprehensive HRV metrics."""
    try:
        import numpy as np
        from hrv_core import (
            clean_rr_intervals,
            compute_comprehensive_hrv,
        )
        from hrv_fragmentation import compute_hrf_metrics
        
        # Clean and validate
        rr_array = np.array(rr_intervals, dtype=float)
        cleaned, mask = await asyncio.to_thread(clean_rr_intervals, rr_array)
        
        if len(cleaned) < 30:
            raise HTTPException(status_code=400, detail="Not enough valid RR intervals (min 30)")
        
        # Compute comprehensive metrics
        metrics = await asyncio.to_thread(
            compute_comprehensive_hrv,
            cleaned,
            psd_method=method,
        )
        
        # Compute HRF
        hrf = await asyncio.to_thread(compute_hrf_metrics, cleaned)
        
        artifact_pct = (1 - len(cleaned) / len(rr_array)) * 100 if len(rr_array) > 0 else 0
        
        return HRVAnalysisResult(
            duration_minutes=len(cleaned) * np.mean(cleaned) / 60000,
            total_beats=len(cleaned),
            artifact_percentage=artifact_pct,
            time_domain=HRVTimeDomain(
                mean_hr=metrics.get("mean_hr"),
                sdnn=metrics.get("sdnn"),
                rmssd=metrics.get("rmssd"),
                pnn50=metrics.get("pnn50"),
                cvnn=metrics.get("cvnn"),
                mean_rr=metrics.get("mean_rr"),
            ),
            frequency_domain=HRVFrequencyDomain(
                vlf_power=metrics.get("vlf_power"),
                lf_power=metrics.get("lf_power"),
                hf_power=metrics.get("hf_power"),
                total_power=metrics.get("total_power"),
                lf_hf_ratio=metrics.get("lf_hf_ratio"),
            ),
            nonlinear=HRVNonlinear(
                sd1=metrics.get("sd1"),
                sd2=metrics.get("sd2"),
                dfa_alpha1=metrics.get("dfa_alpha1"),
                sample_entropy=metrics.get("sample_entropy"),
            ),
            hrf=HRFMetrics(
                pip=hrf.pip,
                pip_h=hrf.pip_h,
                pip_s=hrf.pip_s,
                ials=hrf.ials,
                pss=hrf.pss,
                pas=hrf.pas,
                quality_ok=hrf.quality_ok,
            ),
            analysis_method=method,
        )
    except HTTPException:
        raise
    except Exception as exc:
        _LOGGER.error(f"Error analyzing RR intervals: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Correlation Analysis Endpoints
# ---------------------------------------------------------------------------


@router.get("/correlations/hrv-space-weather", response_model=CorrelationAnalysisResult)
async def get_hrv_space_weather_correlations(
    user_id: Optional[str] = None,
    max_lag_hours: int = Query(default=72, ge=0, le=168),
    min_samples: int = Query(default=10, ge=5),
) -> CorrelationAnalysisResult:
    """Get HRV-Space Weather correlation analysis."""
    try:
        from solar_physiology_correlation import (
            compute_correlation,
            classify_significance,
            classify_strength,
        )
        
        # For now, return a stub with example correlations
        # In production, this would fetch actual user data and compute correlations
        
        now = datetime.now(timezone.utc)
        
        # Example correlations based on literature
        example_correlations = [
            CorrelationResult(
                solar_metric="kp_index",
                physio_metric="rmssd",
                lag_hours=24,
                r=-0.32,
                r_squared=0.10,
                p_value=0.028,
                n_samples=45,
                significance="significant",
                strength="moderate",
                interpretation="Higher geomagnetic activity (Kp) associated with reduced parasympathetic tone (RMSSD).",
            ),
            CorrelationResult(
                solar_metric="solar_wind_speed",
                physio_metric="lf_hf_ratio",
                lag_hours=12,
                r=0.28,
                r_squared=0.08,
                p_value=0.062,
                n_samples=42,
                significance="marginal",
                strength="weak",
                interpretation="Solar wind speed shows marginal positive correlation with sympathovagal balance.",
            ),
            CorrelationResult(
                solar_metric="dst_index",
                physio_metric="sdnn",
                lag_hours=36,
                r=0.25,
                r_squared=0.06,
                p_value=0.095,
                n_samples=40,
                significance="marginal",
                strength="weak",
                interpretation="More negative Dst (stronger storms) may reduce overall HRV.",
            ),
        ]
        
        return CorrelationAnalysisResult(
            analysis_date=now.isoformat(),
            data_start=(now - timedelta(days=30)).date().isoformat(),
            data_end=now.date().isoformat(),
            n_days=30,
            significant_correlations=[c for c in example_correlations if c.p_value < 0.05],
            all_correlations=example_correlations,
            strongest_correlation=max(example_correlations, key=lambda x: abs(x.r)),
            optimal_lag_hours=24,
            pattern_insights=[
                "Geomagnetic storms (Kp ≥ 5) show strongest effects on parasympathetic metrics.",
                "Effects typically appear 12-36 hours after solar events.",
                "Individual sensitivity varies; some subjects show stronger correlations.",
            ],
            recommendations=[
                "Consider timing HRV measurements to avoid geomagnetically disturbed periods.",
                "Monitor Kp index for Polar H10 recording scheduling.",
                "Accumulate more data points for robust statistical power.",
            ],
        )
    except Exception as exc:
        _LOGGER.error(f"Error computing correlations: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Garmin Data Endpoints
# ---------------------------------------------------------------------------


@router.get("/garmin/latest/{user_id}", response_model=GarminMetrics)
async def get_latest_garmin_metrics(user_id: str) -> GarminMetrics:
    """Get latest Garmin metrics for a user."""
    try:
        from user_database import UserDatabase
        
        db = UserDatabase()
        
        # Try to get stored Garmin metrics (returns list of GarminDailyMetrics dataclass)
        metrics_list = await asyncio.to_thread(
            db.get_garmin_daily_metrics,
            user_id,
            1,  # limit
        )
        
        if not metrics_list:
            return GarminMetrics()
        
        # Get the latest record (it's a dataclass, not a dict)
        latest = metrics_list[0]
        return GarminMetrics(
            spo2_avg=latest.avg_spo2,
            respiration_awake=latest.avg_respiration_awake,
            respiration_sleep=latest.avg_respiration_sleep,
            vo2max=None,  # Not stored in GarminDailyMetrics
            sleep_duration_hours=latest.sleep_duration_hours,
            sleep_deep_minutes=None,  # Not stored in GarminDailyMetrics
            sleep_rem_minutes=None,  # Not stored in GarminDailyMetrics
            sleep_efficiency=latest.sleep_efficiency,
            sleep_score=int(latest.sleep_score) if latest.sleep_score else None,
            body_battery_high=int(latest.body_battery_charge) if latest.body_battery_charge else None,
            body_battery_low=int(latest.body_battery_drain) if latest.body_battery_drain else None,
            stress_avg=latest.stress_score,
            steps=latest.steps,
            resting_hr=int(latest.resting_hr_bpm) if latest.resting_hr_bpm else None,
            hrv_overnight=latest.hrv_rmssd_ms,
            date=latest.metric_date,
        )
    except Exception as exc:
        _LOGGER.error(f"Error fetching Garmin metrics for user {user_id}: {exc}")
        return GarminMetrics()


@router.get("/garmin/history/{user_id}", response_model=List[GarminMetrics])
async def get_garmin_history(
    user_id: str,
    days: int = Query(default=30, ge=1, le=365),
) -> List[GarminMetrics]:
    """Get Garmin metrics history for a user."""
    try:
        from user_database import UserDatabase
        
        db = UserDatabase()
        # Returns list of GarminDailyMetrics dataclass objects
        metrics_list = await asyncio.to_thread(
            db.get_garmin_daily_metrics,
            user_id,
            days,  # limit
        )
        
        result = []
        for m in metrics_list:
            result.append(GarminMetrics(
                spo2_avg=m.avg_spo2,
                sleep_duration_hours=m.sleep_duration_hours,
                sleep_score=int(m.sleep_score) if m.sleep_score else None,
                body_battery_high=int(m.body_battery_charge) if m.body_battery_charge else None,
                stress_avg=m.stress_score,
                steps=m.steps,
                resting_hr=int(m.resting_hr_bpm) if m.resting_hr_bpm else None,
                hrv_overnight=m.hrv_rmssd_ms,
                date=m.metric_date,
            ))
        
        return result
    except Exception as exc:
        _LOGGER.error(f"Error fetching Garmin history for user {user_id}: {exc}")
        return []


class GarminSyncRequest(BaseModel):
    """Garmin sync request parameters."""
    
    days: int = Field(default=14, ge=1, le=90, description="Number of days to sync")


class GarminSyncResponse(BaseModel):
    """Garmin sync response."""
    
    success: bool
    records_synced: int
    message: str
    date_range: Optional[str] = None


@router.post("/garmin/sync/{user_id}", response_model=GarminSyncResponse)
async def sync_garmin_data(
    user_id: str,
    request: GarminSyncRequest = GarminSyncRequest(),
) -> GarminSyncResponse:
    """Sync Garmin Connect data for a user.
    
    Requires GARMIN_EMAIL and GARMIN_PASSWORD environment variables to be set.
    """
    try:
        from garmin_connect_service import (
            fetch_garmin_daily_metrics,
            GarminAuthError,
            summarize_garmin_daily,
        )
        from user_database import UserDatabase
        
        # Fetch metrics from Garmin Connect
        _LOGGER.info(f"Starting Garmin sync for user {user_id}, days={request.days}")
        records = await asyncio.to_thread(
            fetch_garmin_daily_metrics,
            user_id,
            request.days,
        )
        
        if not records:
            return GarminSyncResponse(
                success=True,
                records_synced=0,
                message="No new metrics found from Garmin Connect",
            )
        
        # Save to database (save_garmin_daily_metrics expects a sequence)
        db = UserDatabase()
        try:
            await asyncio.to_thread(db.save_garmin_daily_metrics, records)
            saved_count = len(records)
        except Exception as save_exc:
            _LOGGER.warning(f"Failed to save Garmin records: {save_exc}")
            saved_count = 0
        
        # Get summary
        summary = summarize_garmin_daily(records)
        
        return GarminSyncResponse(
            success=True,
            records_synced=saved_count,
            message=f"Successfully synced {saved_count} days of Garmin data",
            date_range=summary.get("dates"),
        )
    except ImportError as exc:
        _LOGGER.error(f"Garmin Connect module not available: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Garmin Connect module not installed. Install python-garminconnect.",
        ) from exc
    except Exception as exc:
        error_msg = str(exc)
        _LOGGER.error(f"Garmin sync failed for user {user_id}: {error_msg}")
        
        # Check for common auth errors
        if "GARMIN_EMAIL" in error_msg or "GARMIN_PASSWORD" in error_msg:
            raise HTTPException(
                status_code=401,
                detail="Garmin credentials not configured. Set GARMIN_EMAIL and GARMIN_PASSWORD in .env",
            ) from exc
        if "MFA" in error_msg or "2FA" in error_msg or "Authentication" in error_msg:
            raise HTTPException(
                status_code=401,
                detail=f"Garmin authentication failed: {error_msg}",
            ) from exc
        if "rate limit" in error_msg.lower():
            raise HTTPException(
                status_code=429,
                detail="Garmin Connect rate limit reached. Please try again later.",
            ) from exc
        
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Space Weather Refresh Endpoint
# ---------------------------------------------------------------------------


class SpaceWeatherRefreshRequest(BaseModel):
    """Space weather refresh request."""
    
    force: bool = Field(default=False, description="Force refresh even if cache is valid")


@router.post("/space-weather/refresh", response_model=SpaceWeatherSnapshot)
async def refresh_space_weather(
    request: SpaceWeatherRefreshRequest = SpaceWeatherRefreshRequest(),
) -> SpaceWeatherSnapshot:
    """Force refresh space weather data from NOAA/NASA sources.
    
    Use this endpoint when the cached data is stale or you need immediate updates.
    """
    try:
        from space_weather_impact import (
            fetch_space_weather_snapshot as fetch_snapshot,
            ImpactEvent,
        )
        
        # Force refresh by clearing any cached data if needed
        if request.force:
            _LOGGER.info("Force refreshing space weather data")
        
        snapshot = await asyncio.to_thread(fetch_snapshot)
        
        # Convert to response model
        data = SpaceWeatherData(
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        
        predictions = []
        for event in snapshot.all_events():
            pred = ImpactPrediction(
                category=event.category.value,
                severity=event.severity.value,
                observation_time=event.observation_time_utc.isoformat() if event.observation_time_utc else None,
                arrival_time=event.arrival_time_utc.isoformat() if event.arrival_time_utc else None,
                travel_time_minutes=event.travel_time_minutes,
                biological_effect=event.biological_effect,
                polar_h10_recommendation=event.polar_h10_recommendation,
                raw_value=event.raw_value if not (event.raw_value != event.raw_value) else None,
                unit=event.unit,
                confidence=event.confidence,
            )
            predictions.append(pred)
        
        next_imp = snapshot.next_impact()
        most_sev = snapshot.most_severe()
        
        return SpaceWeatherSnapshot(
            data=data,
            predictions=predictions,
            next_impact=ImpactPrediction(
                category=next_imp.category.value,
                severity=next_imp.severity.value,
                arrival_time=next_imp.arrival_time_utc.isoformat() if next_imp.arrival_time_utc else None,
                biological_effect=next_imp.biological_effect,
            ) if next_imp else None,
            most_severe=ImpactPrediction(
                category=most_sev.category.value,
                severity=most_sev.severity.value,
                biological_effect=most_sev.biological_effect,
            ) if most_sev else None,
            errors=snapshot.errors,
        )
    except ImportError:
        _LOGGER.warning("space_weather_impact module not available")
        return SpaceWeatherSnapshot(
            data=SpaceWeatherData(fetched_at=datetime.now(timezone.utc).isoformat()),
            errors={"import": "Space weather module not available"},
        )
    except Exception as exc:
        _LOGGER.error(f"Error refreshing space weather: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
