"""Mission-level FRMS v2 helpers (crew risk board + decision log).

This module extends the existing single-profile FRMS dashboard (see `app/frms.py`)
into a *mission-level* aggregation layer suitable for "crew risk board" workflows:

- Aggregate per-subject FRMS metrics/classifications into a single roster view.
- Provide deterministic roll-ups (counts, worst-case risk, ordered alerts).
- Build an exportable, auditable decision-log entry (inputs → classification → mitigations → outcome).

Design goals
- Pure functions and immutable dataclasses (no Streamlit, no DB I/O).
- Bounded execution: finite iterables only; deterministic ordering.
- JSON-serializable payloads for audit and downstream systems.

Primary references (see `docs/Manual.md` and in-app References tab):
- International Civil Aviation Organization. (2016). *Doc 9966* (FRMS oversight manual).
- International Civil Aviation Organization. (2011). *FRMS Implementation Guide for Operators*.
- Gander, P. H., et al. (2014). Crew fatigue SPIs for FRMS. *Aviation, Space, and Environmental Medicine*.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

try:
    # When running via `streamlit run app/app.py`, modules are often imported from `app/` directly.
    from frms import FRMSAlert, FRMSExposureMetrics, FRMSRiskClassification  # type: ignore
except ImportError:  # pragma: no cover - package import path
    from .frms import FRMSAlert, FRMSExposureMetrics, FRMSRiskClassification


@dataclass(frozen=True, slots=True)
class CrewMemberFRMS:
    """FRMS outcome bundle for a single crew member."""

    user_id: str
    display_name: str
    data_source: str  # e.g., "wrist_monitoring" | "clinical_assessment" | "garmin_connect" | "default"
    exposure: FRMSExposureMetrics
    classification: FRMSRiskClassification
    alerts: tuple[FRMSAlert, ...]


@dataclass(frozen=True, slots=True)
class CrewRiskBoard:
    """Mission-level FRMS v2 roster summary."""

    generated_utc: str
    config: Mapping[str, Any]
    members: tuple[CrewMemberFRMS, ...]
    worst_risk_level: str
    risk_level_counts: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class FRMSDecisionLogEntry:
    """Auditable decision log entry for operational FRMS governance."""

    created_utc: str
    decision: str  # e.g., "GO", "GO_WITH_MITIGATIONS", "NO_GO"
    decision_owner: str
    mitigations: tuple[str, ...]
    notes: str
    crew_risk_board: Mapping[str, Any]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload."""
        return {
            "created_utc": self.created_utc,
            "decision": self.decision,
            "decision_owner": self.decision_owner,
            "mitigations": list(self.mitigations),
            "notes": self.notes,
            "crew_risk_board": dict(self.crew_risk_board),
        }


def risk_level_rank(risk_level: str) -> int:
    """Map FRMS risk level labels to an ordinal for worst-case aggregation."""
    order = {"Low": 1, "Medium": 2, "High": 3, "Extreme": 4, "Unknown": 0}
    return int(order.get(str(risk_level), 0))


def summarize_risk_levels(members: Sequence[CrewMemberFRMS]) -> dict[str, int]:
    """Count members by FRMS risk level."""
    counts: dict[str, int] = {"Low": 0, "Medium": 0, "High": 0, "Extreme": 0, "Unknown": 0}
    for m in members:
        lab = str(m.classification.risk_level or "Unknown")
        if lab not in counts:
            counts["Unknown"] = int(counts.get("Unknown", 0)) + 1
        else:
            counts[lab] = int(counts.get(lab, 0)) + 1
    return counts


def compute_worst_risk_level(members: Sequence[CrewMemberFRMS]) -> str:
    """Return the worst (highest) risk level across members."""
    worst = "Unknown"
    worst_rank = -1
    for m in members:
        r = str(m.classification.risk_level or "Unknown")
        rk = risk_level_rank(r)
        if rk > worst_rank:
            worst_rank = rk
            worst = r
    return worst


def build_crew_risk_board(
    *,
    members: Sequence[CrewMemberFRMS],
    config: Mapping[str, Any],
    generated_utc: str | None = None,
) -> CrewRiskBoard:
    """Build a mission-level crew risk board with deterministic ordering."""
    if generated_utc is None:
        generated_utc = _dt.datetime.now(tz=_dt.timezone.utc).isoformat()

    # Deterministic ordering: worst risk first, then name, then user_id.
    ordered = sorted(
        list(members),
        key=lambda m: (-risk_level_rank(m.classification.risk_level), m.display_name.lower(), m.user_id),
    )
    counts = summarize_risk_levels(ordered)
    worst = compute_worst_risk_level(ordered)
    return CrewRiskBoard(
        generated_utc=str(generated_utc),
        config=dict(config),
        members=tuple(ordered),
        worst_risk_level=str(worst),
        risk_level_counts=counts,
    )


def crew_risk_board_to_payload(board: CrewRiskBoard) -> dict[str, Any]:
    """Convert a CrewRiskBoard to a JSON-serializable dict."""
    return {
        "generated_utc": board.generated_utc,
        "config": dict(board.config),
        "summary": {
            "worst_risk_level": board.worst_risk_level,
            "risk_level_counts": dict(board.risk_level_counts),
            "crew_size": int(len(board.members)),
        },
        "members": [
            {
                "user_id": m.user_id,
                "display_name": m.display_name,
                "data_source": m.data_source,
                "exposure": {
                    "samples_total": m.exposure.samples_total,
                    "samples_in_scope": m.exposure.samples_in_scope,
                    "hours_in_scope": m.exposure.hours_in_scope,
                    "hours_in_wocl": m.exposure.hours_in_wocl,
                    "min_effectiveness": m.exposure.min_effectiveness,
                    "mean_effectiveness": m.exposure.mean_effectiveness,
                    "hours_below_90": m.exposure.hours_below_90,
                    "hours_at_or_below_77": m.exposure.hours_at_or_below_77,
                    "hours_at_or_below_70": m.exposure.hours_at_or_below_70,
                    "pct_hours_in_wocl": m.exposure.pct_hours_in_wocl,
                    "pct_hours_at_or_below_77": m.exposure.pct_hours_at_or_below_77,
                },
                "classification": {
                    "severity": m.classification.severity,
                    "likelihood": m.classification.likelihood,
                    "risk_level": m.classification.risk_level,
                    "rationale": m.classification.rationale,
                },
                "alerts": [
                    {"level": a.level, "code": a.code, "message": a.message, "rationale": a.rationale}
                    for a in m.alerts
                ],
            }
            for m in board.members
        ],
    }


def build_decision_log_entry(
    *,
    board: CrewRiskBoard,
    decision: str,
    decision_owner: str,
    mitigations: Sequence[str] | None = None,
    notes: str = "",
    created_utc: str | None = None,
) -> FRMSDecisionLogEntry:
    """Build a decision log entry embedding a crew risk board payload."""
    if created_utc is None:
        created_utc = _dt.datetime.now(tz=_dt.timezone.utc).isoformat()
    mitigations_t = tuple([str(m).strip() for m in (mitigations or []) if str(m).strip()])
    return FRMSDecisionLogEntry(
        created_utc=str(created_utc),
        decision=str(decision).strip(),
        decision_owner=str(decision_owner).strip(),
        mitigations=mitigations_t,
        notes=str(notes or "").strip(),
        crew_risk_board=crew_risk_board_to_payload(board),
    )

