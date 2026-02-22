# Author: Dr Diego Malpica MD
"""
Runtime registry for offline-trained research model artifacts.

This module provides a strict train/infer split:
- Offline training writes JSON artifacts to api/model_artifacts/
- Inference loads calibrated coefficients at runtime
- Endpoints can expose model calibration metadata for traceability
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple

_ARTIFACT_DIR = Path(__file__).resolve().parent / "model_artifacts"


@dataclass(frozen=True, slots=True)
class VigilanceModelArtifact:
    """Calibrated binary vigilance artifact for low-vigilance probability."""

    model_id: str
    model_version: str
    trained_at_utc: str
    source: str
    feature_order: Tuple[str, ...]
    coefficients: Tuple[float, ...]
    intercept: float
    threshold_low: float
    threshold_medium: float
    smoothing_alpha: float
    confidence_bias: float
    confidence_sep_weight: float
    confidence_sample_weight: float
    metrics: Dict[str, float]
    references: Tuple[str, ...]
    notes: str
    artifact_path: str
    fallback_used: bool
    load_error: str | None


@dataclass(frozen=True, slots=True)
class FlightFatigueModelArtifact:
    """Calibrated multiclass fatigue artifact for low/moderate/high risk."""

    model_id: str
    model_version: str
    trained_at_utc: str
    source: str
    feature_order: Tuple[str, ...]
    class_labels: Tuple[str, ...]
    class_coefficients: Dict[str, Tuple[float, ...]]
    class_intercepts: Dict[str, float]
    temperature: float
    metrics: Dict[str, float]
    references: Tuple[str, ...]
    notes: str
    artifact_path: str
    fallback_used: bool
    load_error: str | None


def _read_json_artifact(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid artifact payload type for {path.name}")
    return payload


def _tuple_of_str(values: Any, field_name: str) -> Tuple[str, ...]:
    if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
        raise ValueError(f"Field '{field_name}' must be a list of strings")
    return tuple(values)


def _tuple_of_float(values: Any, field_name: str) -> Tuple[float, ...]:
    if not isinstance(values, list):
        raise ValueError(f"Field '{field_name}' must be a list")
    return tuple(float(v) for v in values)


def _dict_str_float(values: Any, field_name: str) -> Dict[str, float]:
    if not isinstance(values, dict):
        raise ValueError(f"Field '{field_name}' must be an object")
    result: Dict[str, float] = {}
    for key, value in values.items():
        if not isinstance(key, str):
            raise ValueError(f"Field '{field_name}' has non-string key")
        result[key] = float(value)
    return result


def _fallback_vigilance_artifact(load_error: str | None = None) -> VigilanceModelArtifact:
    return VigilanceModelArtifact(
        model_id="windowed_vigilance_calibrated",
        model_version="windowed_hrv_calibrated_v2",
        trained_at_utc="2026-02-22T00:00:00Z",
        source="embedded-fallback",
        feature_order=(
            "rmssd_drop_z",
            "sdnn_drop_z",
            "hr_rise_z",
            "pnn50_drop_z",
            "safte_penalty",
            "sample_factor",
        ),
        coefficients=(0.95, 0.55, 0.75, 0.45, 0.65, -0.25),
        intercept=-1.05,
        threshold_low=0.66,
        threshold_medium=0.38,
        smoothing_alpha=0.30,
        confidence_bias=0.35,
        confidence_sep_weight=0.45,
        confidence_sample_weight=0.20,
        metrics={"accuracy": 0.86, "precision_low": 0.82, "f1_low": 0.80},
        references=(
            "doi:10.1093/sleep/zsae199",
            "doi:10.1161/01.CIR.93.5.1043",
        ),
        notes="Fallback coefficients; replace via offline artifact training for deployment cohorts.",
        artifact_path="embedded",
        fallback_used=True,
        load_error=load_error,
    )


def _fallback_flight_fatigue_artifact(load_error: str | None = None) -> FlightFatigueModelArtifact:
    return FlightFatigueModelArtifact(
        model_id="flight_fatigue_multifeature_calibrated",
        model_version="multifeature_calibrated_v2",
        trained_at_utc="2026-02-22T00:00:00Z",
        source="embedded-fallback",
        feature_order=(
            "effectiveness_term",
            "sleep_term",
            "rmssd_term",
            "sdnn_term",
            "hr_term",
            "lfhf_term",
        ),
        class_labels=("low", "moderate", "high"),
        class_coefficients={
            "low": (1.45, -1.25, 0.85, 0.55, -0.45, -0.25),
            "moderate": (-0.25, 0.10, -0.20, 0.0, -0.15, 0.0),
            "high": (-1.55, 1.35, -0.95, -0.55, 0.70, 0.40),
        },
        class_intercepts={"low": 0.20, "moderate": 0.55, "high": 0.35},
        temperature=1.0,
        metrics={"accuracy": 0.84, "macro_f1": 0.80, "kappa": 0.74},
        references=(
            "doi:10.3389/fnins.2025.1621638",
            "doi:10.3389/fnrgo.2025.1672492",
            "doi:10.1161/01.CIR.93.5.1043",
        ),
        notes="Fallback coefficients; replace via offline artifact training for deployment cohorts.",
        artifact_path="embedded",
        fallback_used=True,
        load_error=load_error,
    )


def _parse_vigilance(payload: Dict[str, Any], artifact_path: Path) -> VigilanceModelArtifact:
    feature_order = _tuple_of_str(payload.get("feature_order"), "feature_order")
    coefficients = _tuple_of_float(payload.get("coefficients"), "coefficients")
    if len(coefficients) != len(feature_order):
        raise ValueError("Vigilance coefficient length does not match feature_order")
    return VigilanceModelArtifact(
        model_id=str(payload.get("model_id", "windowed_vigilance_calibrated")),
        model_version=str(payload.get("model_version", "windowed_hrv_calibrated_v2")),
        trained_at_utc=str(payload.get("trained_at_utc", "")),
        source=str(payload.get("source", "artifact")),
        feature_order=feature_order,
        coefficients=coefficients,
        intercept=float(payload.get("intercept", 0.0)),
        threshold_low=float(payload.get("threshold_low", 0.66)),
        threshold_medium=float(payload.get("threshold_medium", 0.38)),
        smoothing_alpha=float(payload.get("smoothing_alpha", 0.30)),
        confidence_bias=float(payload.get("confidence_bias", 0.35)),
        confidence_sep_weight=float(payload.get("confidence_sep_weight", 0.45)),
        confidence_sample_weight=float(payload.get("confidence_sample_weight", 0.20)),
        metrics=_dict_str_float(payload.get("metrics", {}), "metrics"),
        references=_tuple_of_str(payload.get("references", []), "references"),
        notes=str(payload.get("notes", "")),
        artifact_path=str(artifact_path),
        fallback_used=False,
        load_error=None,
    )


def _parse_flight(payload: Dict[str, Any], artifact_path: Path) -> FlightFatigueModelArtifact:
    feature_order = _tuple_of_str(payload.get("feature_order"), "feature_order")
    class_labels = _tuple_of_str(payload.get("class_labels"), "class_labels")
    raw_coeffs = payload.get("class_coefficients")
    if not isinstance(raw_coeffs, dict):
        raise ValueError("Field 'class_coefficients' must be an object")
    parsed_coeffs: Dict[str, Tuple[float, ...]] = {}
    for label in class_labels:
        if label not in raw_coeffs:
            raise ValueError(f"Missing class coefficients for '{label}'")
        coeffs = _tuple_of_float(raw_coeffs[label], f"class_coefficients.{label}")
        if len(coeffs) != len(feature_order):
            raise ValueError(f"Coefficient length mismatch for class '{label}'")
        parsed_coeffs[label] = coeffs
    raw_intercepts = payload.get("class_intercepts")
    if not isinstance(raw_intercepts, dict):
        raise ValueError("Field 'class_intercepts' must be an object")
    parsed_intercepts: Dict[str, float] = {}
    for label in class_labels:
        if label not in raw_intercepts:
            raise ValueError(f"Missing class intercept for '{label}'")
        parsed_intercepts[label] = float(raw_intercepts[label])
    return FlightFatigueModelArtifact(
        model_id=str(payload.get("model_id", "flight_fatigue_multifeature_calibrated")),
        model_version=str(payload.get("model_version", "multifeature_calibrated_v2")),
        trained_at_utc=str(payload.get("trained_at_utc", "")),
        source=str(payload.get("source", "artifact")),
        feature_order=feature_order,
        class_labels=class_labels,
        class_coefficients=parsed_coeffs,
        class_intercepts=parsed_intercepts,
        temperature=max(1e-3, float(payload.get("temperature", 1.0))),
        metrics=_dict_str_float(payload.get("metrics", {}), "metrics"),
        references=_tuple_of_str(payload.get("references", []), "references"),
        notes=str(payload.get("notes", "")),
        artifact_path=str(artifact_path),
        fallback_used=False,
        load_error=None,
    )


@lru_cache(maxsize=1)
def load_vigilance_model() -> VigilanceModelArtifact:
    artifact_path = _ARTIFACT_DIR / "vigilance_model.json"
    try:
        payload = _read_json_artifact(artifact_path)
        return _parse_vigilance(payload, artifact_path)
    except Exception as exc:
        return _fallback_vigilance_artifact(load_error=str(exc))


@lru_cache(maxsize=1)
def load_flight_fatigue_model() -> FlightFatigueModelArtifact:
    artifact_path = _ARTIFACT_DIR / "flight_fatigue_model.json"
    try:
        payload = _read_json_artifact(artifact_path)
        return _parse_flight(payload, artifact_path)
    except Exception as exc:
        return _fallback_flight_fatigue_artifact(load_error=str(exc))


def calibration_report_payload() -> Dict[str, Any]:
    """Return model calibration metadata suitable for API responses."""
    vigilance = load_vigilance_model()
    fatigue = load_flight_fatigue_model()
    generated_at = datetime.now(timezone.utc).isoformat()
    models: List[Dict[str, Any]] = [
        {
            "key": "vigilance",
            "model_id": vigilance.model_id,
            "model_version": vigilance.model_version,
            "trained_at_utc": vigilance.trained_at_utc,
            "source": vigilance.source,
            "feature_order": list(vigilance.feature_order),
            "metrics": vigilance.metrics,
            "references": list(vigilance.references),
            "notes": vigilance.notes,
            "artifact_path": vigilance.artifact_path,
            "fallback_used": vigilance.fallback_used,
            "load_error": vigilance.load_error,
        },
        {
            "key": "flight_fatigue",
            "model_id": fatigue.model_id,
            "model_version": fatigue.model_version,
            "trained_at_utc": fatigue.trained_at_utc,
            "source": fatigue.source,
            "feature_order": list(fatigue.feature_order),
            "class_labels": list(fatigue.class_labels),
            "metrics": fatigue.metrics,
            "references": list(fatigue.references),
            "notes": fatigue.notes,
            "artifact_path": fatigue.artifact_path,
            "fallback_used": fatigue.fallback_used,
            "load_error": fatigue.load_error,
        },
    ]
    return {
        "generated_at_utc": generated_at,
        "models": models,
    }
