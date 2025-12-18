from __future__ import annotations

import datetime as dt

from app.frms import FRMSAlert, FRMSExposureMetrics, FRMSRiskClassification
from app.frms_v2 import (
    CrewMemberFRMS,
    build_crew_risk_board,
    build_decision_log_entry,
    crew_risk_board_to_payload,
)


def _exposure(min_eff: float, *, pct_hi: float = 0.0) -> FRMSExposureMetrics:
    return FRMSExposureMetrics(
        samples_total=24,
        samples_in_scope=24,
        hours_in_scope=24.0,
        hours_in_wocl=4.0,
        min_effectiveness=min_eff,
        mean_effectiveness=90.0,
        hours_below_90=2.0,
        hours_at_or_below_77=1.0 if pct_hi > 0 else 0.0,
        hours_at_or_below_70=0.0,
        pct_hours_in_wocl=16.7,
        pct_hours_at_or_below_77=pct_hi,
    )


def _cls(risk: str) -> FRMSRiskClassification:
    # The aggregation layer should not depend on the classifier implementation details.
    return FRMSRiskClassification(
        severity="Major",
        likelihood="Possible",
        risk_level=risk,
        rationale="test rationale",
    )


def test_crew_risk_board_orders_by_worst_risk_then_name() -> None:
    a = CrewMemberFRMS(
        user_id="u2",
        display_name="Bravo",
        data_source="default",
        exposure=_exposure(72.0, pct_hi=25.0),
        classification=_cls("High"),
        alerts=tuple(),
    )
    b = CrewMemberFRMS(
        user_id="u1",
        display_name="Alpha",
        data_source="default",
        exposure=_exposure(95.0, pct_hi=0.0),
        classification=_cls("Low"),
        alerts=tuple(),
    )
    c = CrewMemberFRMS(
        user_id="u3",
        display_name="Charlie",
        data_source="default",
        exposure=_exposure(68.0, pct_hi=40.0),
        classification=_cls("Extreme"),
        alerts=tuple(),
    )
    board = build_crew_risk_board(members=[a, b, c], config={"x": 1}, generated_utc="2025-01-01T00:00:00+00:00")
    assert [m.user_id for m in board.members] == ["u3", "u2", "u1"]
    assert board.worst_risk_level == "Extreme"
    assert board.risk_level_counts["Low"] == 1
    assert board.risk_level_counts["High"] == 1
    assert board.risk_level_counts["Extreme"] == 1


def test_crew_risk_board_payload_is_json_serializable_shape() -> None:
    member = CrewMemberFRMS(
        user_id="u1",
        display_name="Alpha",
        data_source="wrist_monitoring",
        exposure=_exposure(88.0, pct_hi=10.0),
        classification=_cls("Medium"),
        alerts=(FRMSAlert(level="warning", code="w", message="m", rationale="r"),),
    )
    board = build_crew_risk_board(members=[member], config={"mode": "test"}, generated_utc="2025-01-01T00:00:00+00:00")
    payload = crew_risk_board_to_payload(board)
    assert payload["generated_utc"] == "2025-01-01T00:00:00+00:00"
    assert payload["summary"]["crew_size"] == 1
    assert payload["members"][0]["user_id"] == "u1"
    assert payload["members"][0]["alerts"][0]["code"] == "w"


def test_decision_log_entry_embeds_board_payload() -> None:
    member = CrewMemberFRMS(
        user_id="u1",
        display_name="Alpha",
        data_source="default",
        exposure=_exposure(92.0),
        classification=_cls("Low"),
        alerts=tuple(),
    )
    board = build_crew_risk_board(members=[member], config={"scope": "all"}, generated_utc="2025-01-01T00:00:00+00:00")
    entry = build_decision_log_entry(
        board=board,
        decision="GO_WITH_MITIGATIONS",
        decision_owner="Flight Surgeon",
        mitigations=["nap", "caffeine timing"],
        notes="test",
        created_utc=dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc).isoformat(),
    )
    payload = entry.to_payload()
    assert payload["decision"] == "GO_WITH_MITIGATIONS"
    assert payload["crew_risk_board"]["summary"]["crew_size"] == 1

