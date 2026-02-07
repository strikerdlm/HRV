# Author: Dr Diego Malpica MD
"""
FastAPI Backend for Mission Control - Flight Surgeon.

This API exposes the Python HRV analysis modules to the TypeScript frontend.
Run with: uvicorn api.main:app --reload --port 8080

Endpoints:
- /api/health - Health check
- /api/missions - List/set active mission
- /api/users - User profile CRUD
- /api/experiments - Experiment management
- /api/scheduling - Crew scheduling
- /api/hrv - HRV analysis endpoints
- /api/space-weather - Space weather data
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add app directory to path for imports
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_APP_DIR = _PROJECT_ROOT / "app"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Load environment variables from .env file
try:
    from env_loader import load_env_file
    _env_loaded = load_env_file(verbose=True)
except ImportError:
    # Fallback: try loading .env from project root directly
    try:
        from dotenv import load_dotenv
        _env_path = _PROJECT_ROOT / ".env"
        if _env_path.exists():
            load_dotenv(dotenv_path=_env_path)
            _env_loaded = True
        else:
            _env_loaded = False
    except ImportError:
        _env_loaded = False

# Configure logging
logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

if _env_loaded:
    _LOGGER.info("Environment variables loaded from .env")
else:
    _LOGGER.warning("No .env file loaded - some features may not work")


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    timestamp: str
    version: str = "1.0.0"


class MissionResponse(BaseModel):
    """Mission workspace response."""

    active_mission: str
    available_missions: list[str]


class SetMissionRequest(BaseModel):
    """Set active mission request."""

    mission: str = Field(..., description="Mission name (Mission 1 or Mission 2)")


class UserProfile(BaseModel):
    """User profile model."""

    user_id: str = ""
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    date_of_birth: Optional[str] = None
    sex: str = "other"
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    resting_hr_bpm: Optional[int] = None
    max_hr_bpm: Optional[int] = None
    vo2max_ml_kg_min: Optional[float] = None
    occupation: Optional[str] = None
    activity_level: Optional[str] = None
    smoking_status: Optional[str] = None
    alcohol_use: Optional[str] = None
    caffeine_intake_mg: Optional[int] = None
    medical_conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    language: str = "en"
    crew_role: Optional[str] = None
    crew_status: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CreateUserRequest(BaseModel):
    """Create user request."""

    username: str = Field(..., min_length=1, max_length=64)
    full_name: Optional[str] = None
    sex: str = "other"
    language: str = "en"


class UsersListResponse(BaseModel):
    """Users list response."""

    users: list[UserProfile]
    total: int


class ExperimentBase(BaseModel):
    """Experiment base model."""

    experiment_id: str = ""
    title: str
    description: Optional[str] = None
    status: str = "draft"
    priority: str = "medium"
    duration_minutes: int = 60
    required_crew: int = 1
    equipment: list[str] = Field(default_factory=list)
    assigned_crew: list[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CreateExperimentRequest(BaseModel):
    """Create experiment request."""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    priority: str = "medium"
    duration_minutes: int = Field(default=60, ge=15, le=480)
    required_crew: int = Field(default=1, ge=1, le=6)
    equipment: list[str] = Field(default_factory=list)


class ExperimentsListResponse(BaseModel):
    """Experiments list response."""

    experiments: list[ExperimentBase]
    total: int


class ScheduleEntry(BaseModel):
    """Schedule entry model."""

    entry_id: str
    crew_member: str
    activity: str
    start_time: str
    end_time: str
    category: str
    risk_level: str


class ScheduleResponse(BaseModel):
    """Schedule response."""

    schedule: list[ScheduleEntry]
    mission: str
    generated_at: str


class SpaceWeatherSnapshot(BaseModel):
    """Space weather snapshot model."""

    kp_index: Optional[float] = None
    dst_index: Optional[float] = None
    f10_7_flux: Optional[float] = None
    solar_wind_speed: Optional[float] = None
    solar_wind_density: Optional[float] = None
    xray_flux: Optional[str] = None
    proton_flux_10mev: Optional[float] = None
    fetched_at: Optional[str] = None


class HRVSummary(BaseModel):
    """HRV analysis summary model."""

    mean_hr: Optional[float] = None
    sdnn: Optional[float] = None
    rmssd: Optional[float] = None
    pnn50: Optional[float] = None
    lf_power: Optional[float] = None
    hf_power: Optional[float] = None
    lf_hf_ratio: Optional[float] = None
    total_beats: Optional[int] = None
    duration_minutes: Optional[float] = None
    artifact_percentage: Optional[float] = None


# ---------------------------------------------------------------------------
# App Lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    _LOGGER.info("Starting Mission Control API...")
    
    # Initialize logging from app module if available
    try:
        from logging_config import setup_logging
        await asyncio.to_thread(setup_logging)
        _LOGGER.info("Logging initialized from app module")
    except ImportError:
        _LOGGER.warning("Could not import app logging_config")
    
    yield
    
    _LOGGER.info("Shutting down Mission Control API...")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mission Control - Flight Surgeon API",
    description="REST API for the TypeScript frontend of the HRV Analysis Suite",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3100",
        "http://127.0.0.1:3100",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health Endpoint
# ---------------------------------------------------------------------------


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
    )


# ---------------------------------------------------------------------------
# Mission Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/missions", response_model=MissionResponse, tags=["Missions"])
async def get_missions() -> MissionResponse:
    """Get active mission and available missions."""
    active = os.environ.get("HRV_ACTIVE_MISSION", "Mission 1")
    return MissionResponse(
        active_mission=active,
        available_missions=["Mission 1", "Mission 2"],
    )


@app.post("/api/missions", response_model=MissionResponse, tags=["Missions"])
async def set_active_mission(request: SetMissionRequest) -> MissionResponse:
    """Set the active mission workspace."""
    mission = request.mission.strip()
    if mission not in {"Mission 1", "Mission 2"}:
        raise HTTPException(status_code=400, detail="Invalid mission name")
    
    os.environ["HRV_ACTIVE_MISSION"] = mission
    _LOGGER.info(f"Active mission set to: {mission}")
    
    return MissionResponse(
        active_mission=mission,
        available_missions=["Mission 1", "Mission 2"],
    )


# ---------------------------------------------------------------------------
# User Endpoints
# ---------------------------------------------------------------------------


def _get_user_database():
    """Get UserDatabase instance."""
    try:
        from user_database import UserDatabase
        return UserDatabase()
    except ImportError as exc:
        _LOGGER.error(f"Could not import UserDatabase: {exc}")
        raise HTTPException(
            status_code=500,
            detail="User database module not available"
        ) from exc


def _profile_to_dict(profile: Any) -> dict[str, Any]:
    """Convert a UserProfile dataclass to dict safely."""
    if hasattr(profile, "__dataclass_fields__"):
        return asdict(profile)
    return {
        "user_id": getattr(profile, "user_id", ""),
        "username": getattr(profile, "username", ""),
        "full_name": getattr(profile, "full_name", None),
        "email": getattr(profile, "email", None),
        "date_of_birth": str(getattr(profile, "date_of_birth", "")) if getattr(profile, "date_of_birth", None) else None,
        "sex": getattr(profile, "sex", "other"),
        "height_cm": getattr(profile, "height_cm", None),
        "weight_kg": getattr(profile, "weight_kg", None),
        "resting_hr_bpm": getattr(profile, "resting_hr_bpm", None),
        "max_hr_bpm": getattr(profile, "max_hr_bpm", None),
        "vo2max_ml_kg_min": getattr(profile, "vo2max_ml_kg_min", None),
        "occupation": getattr(profile, "occupation", None),
        "activity_level": getattr(profile, "activity_level", None),
        "smoking_status": getattr(profile, "smoking_status", None),
        "alcohol_use": getattr(profile, "alcohol_use", None),
        "caffeine_intake_mg": getattr(profile, "caffeine_intake_mg", None),
        "medical_conditions": getattr(profile, "medical_conditions", []) or [],
        "medications": getattr(profile, "medications", []) or [],
        "language": getattr(profile, "language", "en"),
        "crew_role": getattr(profile, "crew_role", None),
        "crew_status": getattr(profile, "crew_status", None),
        "created_at": str(getattr(profile, "created_at", "")) if getattr(profile, "created_at", None) else None,
        "updated_at": str(getattr(profile, "updated_at", "")) if getattr(profile, "updated_at", None) else None,
    }


@app.get("/api/users", response_model=UsersListResponse, tags=["Users"])
async def list_users(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> UsersListResponse:
    """List all users."""
    db = _get_user_database()
    
    try:
        users_raw = await asyncio.to_thread(db.list_users)
        users = [UserProfile(**_profile_to_dict(u)) for u in users_raw[offset:offset + limit]]
        return UsersListResponse(users=users, total=len(users_raw))
    except Exception as exc:
        _LOGGER.error(f"Error listing users: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/users/{user_id}", response_model=UserProfile, tags=["Users"])
async def get_user(user_id: str) -> UserProfile:
    """Get a specific user by ID."""
    db = _get_user_database()
    
    try:
        profile = await asyncio.to_thread(db.get_user, user_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="User not found")
        return UserProfile(**_profile_to_dict(profile))
    except HTTPException:
        raise
    except Exception as exc:
        _LOGGER.error(f"Error getting user {user_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/users", response_model=UserProfile, tags=["Users"])
async def create_user(request: CreateUserRequest) -> UserProfile:
    """Create a new user."""
    db = _get_user_database()
    
    try:
        from user_database import UserProfile as DBUserProfile
        
        profile = DBUserProfile(
            user_id="",
            username=request.username.strip(),
            full_name=request.full_name.strip() if request.full_name else request.username.strip(),
            email=None,
            date_of_birth=None,
            sex=request.sex.strip() or "other",
            height_cm=None,
            weight_kg=None,
            resting_hr_bpm=None,
            max_hr_bpm=None,
            vo2max_ml_kg_min=None,
            occupation=None,
            activity_level=None,
            smoking_status=None,
            alcohol_use=None,
            caffeine_intake_mg=None,
            medical_conditions=[],
            medications=[],
            language=request.language or "en",
            created_at=None,
            updated_at=None,
        )
        
        user_id = await asyncio.to_thread(db.create_user, profile, None)
        created = await asyncio.to_thread(db.get_user, user_id)
        
        if created is None:
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        return UserProfile(**_profile_to_dict(created))
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _LOGGER.error(f"Error creating user: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.put("/api/users/{user_id}", response_model=UserProfile, tags=["Users"])
async def update_user(user_id: str, request: UserProfile) -> UserProfile:
    """Update a user profile."""
    db = _get_user_database()
    
    try:
        existing = await asyncio.to_thread(db.get_user, user_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        from user_database import UserProfile as DBUserProfile
        
        # Update the existing profile with new values
        updated_profile = DBUserProfile(
            user_id=user_id,
            username=existing.username,  # Username cannot be changed
            full_name=request.full_name or existing.full_name,
            email=request.email or existing.email,
            date_of_birth=request.date_of_birth or existing.date_of_birth,
            sex=request.sex or existing.sex,
            height_cm=request.height_cm if request.height_cm is not None else existing.height_cm,
            weight_kg=request.weight_kg if request.weight_kg is not None else existing.weight_kg,
            resting_hr_bpm=request.resting_hr_bpm if request.resting_hr_bpm is not None else existing.resting_hr_bpm,
            max_hr_bpm=request.max_hr_bpm if request.max_hr_bpm is not None else existing.max_hr_bpm,
            vo2max_ml_kg_min=request.vo2max_ml_kg_min if request.vo2max_ml_kg_min is not None else existing.vo2max_ml_kg_min,
            occupation=request.occupation or existing.occupation,
            activity_level=request.activity_level or existing.activity_level,
            smoking_status=request.smoking_status if request.smoking_status is not None else getattr(existing, "smoking_status", None),
            alcohol_use=request.alcohol_use if request.alcohol_use is not None else getattr(existing, "alcohol_use", None),
            caffeine_intake_mg=request.caffeine_intake_mg if request.caffeine_intake_mg is not None else getattr(existing, "caffeine_intake_mg", None),
            medical_conditions=request.medical_conditions if request.medical_conditions else getattr(existing, "medical_conditions", []) or [],
            medications=request.medications if request.medications else getattr(existing, "medications", []) or [],
            language=request.language or existing.language,
            crew_role=request.crew_role if request.crew_role is not None else getattr(existing, "crew_role", None),
            crew_status=request.crew_status if request.crew_status is not None else getattr(existing, "crew_status", None),
            created_at=existing.created_at,
            updated_at=None,  # Will be set by update_user
        )
        
        await asyncio.to_thread(db.update_user, updated_profile)
        updated = await asyncio.to_thread(db.get_user, user_id)
        
        if updated is None:
            raise HTTPException(status_code=500, detail="Failed to update user")
        
        return UserProfile(**_profile_to_dict(updated))
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _LOGGER.error(f"Error updating user {user_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/api/users/{user_id}", tags=["Users"])
async def delete_user(user_id: str) -> dict[str, str]:
    """Delete a user."""
    db = _get_user_database()
    
    try:
        existing = await asyncio.to_thread(db.get_user, user_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        await asyncio.to_thread(db.delete_user, user_id)
        return {"message": f"User {user_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as exc:
        _LOGGER.error(f"Error deleting user {user_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Experiments Endpoints (Stub - expandable)
# ---------------------------------------------------------------------------

# In-memory storage for demo (replace with database in production)
_experiments_store: dict[str, dict[str, Any]] = {}


@app.get("/api/experiments", response_model=ExperimentsListResponse, tags=["Experiments"])
async def list_experiments() -> ExperimentsListResponse:
    """List all experiments."""
    experiments = [ExperimentBase(**exp) for exp in _experiments_store.values()]
    return ExperimentsListResponse(experiments=experiments, total=len(experiments))


@app.post("/api/experiments", response_model=ExperimentBase, tags=["Experiments"])
async def create_experiment(request: CreateExperimentRequest) -> ExperimentBase:
    """Create a new experiment."""
    import uuid
    
    experiment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    experiment = ExperimentBase(
        experiment_id=experiment_id,
        title=request.title,
        description=request.description,
        status="draft",
        priority=request.priority,
        duration_minutes=request.duration_minutes,
        required_crew=request.required_crew,
        equipment=request.equipment,
        assigned_crew=[],
        created_at=now,
        updated_at=now,
    )
    
    _experiments_store[experiment_id] = experiment.model_dump()
    return experiment


@app.delete("/api/experiments/{experiment_id}", tags=["Experiments"])
async def delete_experiment(experiment_id: str) -> dict[str, str]:
    """Delete an experiment."""
    if experiment_id not in _experiments_store:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    del _experiments_store[experiment_id]
    return {"message": f"Experiment {experiment_id} deleted successfully"}


# ---------------------------------------------------------------------------
# Space Weather Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/space-weather", response_model=SpaceWeatherSnapshot, tags=["Space Weather"])
async def get_space_weather() -> SpaceWeatherSnapshot:
    """Get current space weather snapshot."""
    import re
    
    try:
        from space_weather_impact import fetch_space_weather_snapshot
        
        snapshot = await asyncio.to_thread(fetch_space_weather_snapshot)
        
        # Extract values from the ImpactEvent objects in the snapshot
        # The snapshot is a dataclass with event objects, not a dict
        kp_index: Optional[float] = None
        dst_index: Optional[float] = None
        f10_7_flux: Optional[float] = None
        solar_wind_speed: Optional[float] = None
        solar_wind_density: Optional[float] = None
        xray_flux: Optional[str] = None
        proton_flux_10mev: Optional[float] = None
        
        # Helper to check for valid float (not NaN)
        def _valid_float(val: Any) -> bool:
            return val is not None and not (val != val)  # NaN check
        
        # Extract from geomagnetic event (Kp, Dst)
        # source_description format: "G2 (Kp=5.0, Dst=-30 nT)"
        if snapshot.geomagnetic_event:
            evt = snapshot.geomagnetic_event
            if _valid_float(evt.raw_value):
                kp_index = evt.raw_value
            # Parse Dst from source_description
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
        
        # Extract from photon event (X-ray class)
        if snapshot.photon_event:
            evt = snapshot.photon_event
            # Try to get X-ray class from source_description or unit
            if evt.source_description:
                # Format: "X1.5 Flare" or "C3.2"
                xray_match = re.search(r"([ABCMX]\d+\.?\d*)", evt.source_description)
                if xray_match:
                    xray_flux = xray_match.group(1)
            if not xray_flux and evt.unit:
                xray_flux = evt.unit
        
        # Extract from SEP event (proton flux)
        if snapshot.sep_event:
            evt = snapshot.sep_event
            if _valid_float(evt.raw_value):
                proton_flux_10mev = evt.raw_value
        
        return SpaceWeatherSnapshot(
            kp_index=kp_index,
            dst_index=dst_index,
            f10_7_flux=f10_7_flux,
            solar_wind_speed=solar_wind_speed,
            solar_wind_density=solar_wind_density,
            xray_flux=xray_flux,
            proton_flux_10mev=proton_flux_10mev,
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
    except ImportError:
        _LOGGER.warning("Space weather module not available")
        return SpaceWeatherSnapshot(
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as exc:
        _LOGGER.error(f"Error fetching space weather: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# HRV Endpoints (Stub - expandable)
# ---------------------------------------------------------------------------


@app.get("/api/hrv/summary/{user_id}", response_model=HRVSummary, tags=["HRV"])
async def get_hrv_summary(user_id: str) -> HRVSummary:
    """Get latest HRV summary for a user."""
    # This is a stub - in production, fetch from database
    return HRVSummary(
        mean_hr=None,
        sdnn=None,
        rmssd=None,
        pnn50=None,
        lf_power=None,
        hf_power=None,
        lf_hf_ratio=None,
        total_beats=None,
        duration_minutes=None,
        artifact_percentage=None,
    )


# ---------------------------------------------------------------------------
# Research Endpoints
# ---------------------------------------------------------------------------

try:
    from api.research_endpoints import router as research_router
    app.include_router(research_router)
    _LOGGER.info("Research endpoints registered")
except ImportError as exc:
    _LOGGER.warning(f"Could not load research endpoints: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8180,
        reload=True,
    )
