"""FastAPI endpoints for Psychomotor Vigilance Task (PVT) sessions.

Exposes:
    POST   /api/pvt/score                 — stateless scoring
    POST   /api/pvt/sessions              — save a completed session
    GET    /api/pvt/sessions/{user_id}    — list user's session history
    GET    /api/pvt/sessions/{user_id}/latest — most recent session

Backed by a lightweight SQLite table under `pvt_users.db`. Scoring logic
is fully delegated to `app.pvt_core` — this module does not re-implement
any metric calculations.

Author: Dr Diego Malpica MD
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_APP_DIR = _PROJECT_ROOT / "app"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.pvt_core import (  # noqa: E402
    PVTVariant,
    build_session_from_raw,
    operational_gate,
    score_session,
    variant_defaults,
)

_LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pvt", tags=["PVT"])


# ---------------------------------------------------------------------------
# SQLite persistence
# ---------------------------------------------------------------------------

_DB_PATH = _PROJECT_ROOT / "pvt_sessions.db"


def _init_db() -> None:
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pvt_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                variant TEXT NOT NULL,
                duration_min REAL NOT NULL,
                started_at TEXT,
                ended_at TEXT,
                device_label TEXT,
                software_version TEXT,
                notes TEXT,
                metrics_json TEXT NOT NULL,
                trials_json TEXT NOT NULL,
                gate_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pvt_user_created "
            "ON pvt_sessions (user_id, created_at DESC)"
        )
        conn.commit()


try:
    _init_db()
except Exception as exc:  # pragma: no cover - defensive
    _LOGGER.warning(f"PVT session DB init failed: {exc}")


# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------

class PVTTrialIn(BaseModel):
    index: int = Field(..., description="0-based trial index")
    isi_ms: float = Field(..., ge=0.0, description="Inter-stimulus interval in ms")
    stimulus_onset_ms: float = Field(..., ge=0.0, description="Time from session start to stimulus in ms")
    rt_ms: Optional[float] = Field(None, description="Reaction time in ms; null if no response")
    anticipatory: bool = Field(False, description="True if response fired before stimulus")


class PVTScoreRequest(BaseModel):
    variant: str = Field(..., description='One of "PVT-B", "PVT-5", "PVT-10"')
    duration_min: Optional[float] = Field(None, description="Override variant default duration (minutes)")
    lapse_threshold_ms: Optional[float] = Field(None, description="Override variant default lapse threshold")
    user_id: Optional[str] = Field(None)
    device_label: Optional[str] = Field(None, description="e.g. 'web', 'psychopy', 'tablet'")
    software_version: Optional[str] = Field(None)
    trials: list[PVTTrialIn]


class PVTScoreResponse(BaseModel):
    metrics: dict[str, Any]
    gate: dict[str, Any]
    lapse_threshold_ms: float
    variant: str
    duration_min: float


class PVTSessionSaveRequest(PVTScoreRequest):
    """Same as score request, plus optional audit fields persisted with the session."""
    started_at: Optional[str] = Field(None, description="ISO-8601")
    ended_at: Optional[str] = Field(None, description="ISO-8601")
    notes: Optional[str] = Field(None)


class PVTSessionSummary(BaseModel):
    id: int
    user_id: Optional[str]
    variant: str
    duration_min: float
    started_at: Optional[str]
    ended_at: Optional[str]
    device_label: Optional[str]
    created_at: str
    n_trials: int
    n_valid_trials: int
    n_lapses: int
    n_false_starts: int
    mean_rt_ms: Optional[float]
    mean_response_speed_per_s: Optional[float]
    pvt_lapses_3min: int
    decision: Optional[str]


class PVTSessionDetail(PVTSessionSummary):
    metrics: dict[str, Any]
    gate: dict[str, Any]
    trials: list[PVTTrialIn]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_variant(value: str) -> PVTVariant:
    try:
        return PVTVariant(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(f"Unknown PVT variant '{value}'. "
                    f"Expected one of: {[v.value for v in PVTVariant]}"),
        )


def _score(req: PVTScoreRequest) -> tuple[dict, dict, float, PVTVariant, float]:
    variant = _parse_variant(req.variant)
    defaults = variant_defaults(variant)
    duration = req.duration_min if req.duration_min is not None else defaults["duration_min"]
    lapse_ms = req.lapse_threshold_ms if req.lapse_threshold_ms is not None else defaults["lapse_threshold_ms"]

    started_at = None
    ended_at = None
    if isinstance(req, PVTSessionSaveRequest):
        if req.started_at:
            started_at = datetime.fromisoformat(req.started_at.replace("Z", "+00:00"))
        if req.ended_at:
            ended_at = datetime.fromisoformat(req.ended_at.replace("Z", "+00:00"))

    sess = build_session_from_raw(
        [t.model_dump() for t in req.trials],
        variant=variant,
        duration_min=duration,
        user_id=req.user_id,
        started_at=started_at,
        ended_at=ended_at,
        device_label=req.device_label,
        software_version=req.software_version,
    )
    metrics = score_session(sess, lapse_threshold_ms=lapse_ms)
    gate = operational_gate(metrics)
    return metrics, gate, lapse_ms, variant, duration


def _row_to_summary(row: sqlite3.Row) -> PVTSessionSummary:
    metrics = json.loads(row["metrics_json"])
    gate = json.loads(row["gate_json"] or "{}")
    return PVTSessionSummary(
        id=row["id"],
        user_id=row["user_id"],
        variant=row["variant"],
        duration_min=row["duration_min"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        device_label=row["device_label"],
        created_at=row["created_at"],
        n_trials=metrics.get("n_trials", 0),
        n_valid_trials=metrics.get("n_valid_trials", 0),
        n_lapses=metrics.get("n_lapses", 0),
        n_false_starts=metrics.get("n_false_starts", 0),
        mean_rt_ms=metrics.get("mean_rt_ms"),
        mean_response_speed_per_s=metrics.get("mean_response_speed_per_s"),
        pvt_lapses_3min=metrics.get("pvt_lapses_3min", 0),
        decision=gate.get("decision"),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/score", response_model=PVTScoreResponse, summary="Stateless PVT scoring")
def pvt_score(req: PVTScoreRequest) -> PVTScoreResponse:
    """Compute PVT metrics and the operational gate for a set of trials
    without persisting the session. Useful for live in-browser preview."""
    metrics, gate, lapse_ms, variant, duration = _score(req)
    return PVTScoreResponse(
        metrics=metrics, gate=gate, lapse_threshold_ms=lapse_ms,
        variant=variant.value, duration_min=duration,
    )


@router.post("/sessions", response_model=PVTSessionSummary, summary="Save a completed PVT session")
def save_pvt_session(req: PVTSessionSaveRequest) -> PVTSessionSummary:
    """Persist a completed session; returns the saved summary with decision."""
    metrics, gate, lapse_ms, variant, duration = _score(req)
    created_at = datetime.now(timezone.utc).isoformat()

    trials_payload = json.dumps([t.model_dump() for t in req.trials])
    with sqlite3.connect(_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            INSERT INTO pvt_sessions
                (user_id, variant, duration_min, started_at, ended_at,
                 device_label, software_version, notes,
                 metrics_json, trials_json, gate_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                req.user_id, variant.value, duration,
                req.started_at, req.ended_at,
                req.device_label, req.software_version, req.notes,
                json.dumps(metrics), trials_payload, json.dumps(gate),
                created_at,
            ),
        )
        new_id = cursor.lastrowid
        conn.commit()
        row = conn.execute(
            "SELECT * FROM pvt_sessions WHERE id = ?", (new_id,)
        ).fetchone()
    return _row_to_summary(row)


@router.get(
    "/sessions/{user_id}",
    response_model=list[PVTSessionSummary],
    summary="List a user's PVT session history",
)
def list_user_sessions(
    user_id: str,
    limit: int = Query(50, ge=1, le=500),
    variant: Optional[str] = Query(None),
) -> list[PVTSessionSummary]:
    with sqlite3.connect(_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if variant:
            rows = conn.execute(
                "SELECT * FROM pvt_sessions "
                "WHERE user_id = ? AND variant = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (user_id, variant, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM pvt_sessions "
                "WHERE user_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
    return [_row_to_summary(r) for r in rows]


@router.get(
    "/sessions/{user_id}/latest",
    response_model=PVTSessionDetail,
    summary="Most recent PVT session for a user (full detail)",
)
def latest_user_session(user_id: str) -> PVTSessionDetail:
    with sqlite3.connect(_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM pvt_sessions WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No PVT sessions found for user")
    summary = _row_to_summary(row)
    metrics = json.loads(row["metrics_json"])
    gate = json.loads(row["gate_json"] or "{}")
    trials = [PVTTrialIn(**t) for t in json.loads(row["trials_json"])]
    return PVTSessionDetail(
        **summary.model_dump(),
        metrics=metrics,
        gate=gate,
        trials=trials,
    )


@router.get(
    "/variants",
    summary="Return canonical PVT variant defaults",
)
def list_variants() -> dict[str, Any]:
    return {v.value: variant_defaults(v) for v in PVTVariant}
