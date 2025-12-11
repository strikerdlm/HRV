"""
Agent-aware metric explanation helpers for Mission Control - Flight Surgeon.

This module bridges the OpenAI Agents SDK scaffold with deterministic,
reference-backed explanations so clinicians always receive clear guidance,
even when API credentials are unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import math
import pandas as pd

try:  # pragma: no cover - dual import path support
    from app.logging_config import get_logger, log_exception
except ImportError:  # pragma: no cover - Streamlit execution fallback
    from logging_config import get_logger, log_exception  # type: ignore

from agent_runtime import AgentRuntime

_LOGGER = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class MetricReference:
    """Reference ranges and descriptions for a single HRV metric."""

    metric_key: str
    display_name: str
    unit: str
    lower_bound: float
    upper_bound: float
    citation: str
    rationale: str


@dataclass(frozen=True, slots=True)
class MetricExplanation:
    """Plain-language explanation for a metric value."""

    dataset: str
    metric_key: str
    display_name: str
    value: float
    unit: str
    status: str
    explanation: str
    citation: str


@dataclass(frozen=True, slots=True)
class MetricInsightResult:
    """Aggregate output for metric insight generation."""

    explanations: Tuple[MetricExplanation, ...]
    agent_markdown: Optional[str]
    agent_payload: Optional[Dict[str, Any]]
    agent_error: Optional[str]
    used_agent: bool


_DEFAULT_REFERENCES: Mapping[str, MetricReference] = {
    "sdnn": MetricReference(
        metric_key="sdnn",
        display_name="SDNN",
        unit="ms",
        lower_bound=34.0,
        upper_bound=66.0,
        citation="Task Force, 1996",
        rationale="SDNN captures total variability across sympathetic and parasympathetic inputs.",
    ),
    "rmssd": MetricReference(
        metric_key="rmssd",
        display_name="RMSSD",
        unit="ms",
        lower_bound=27.0,
        upper_bound=57.0,
        citation="Shaffer & Ginsberg, 2017",
        rationale="RMSSD reflects short-term, vagally mediated variability.",
    ),
    "pnn50": MetricReference(
        metric_key="pnn50",
        display_name="pNN50",
        unit="%",
        lower_bound=10.0,
        upper_bound=25.0,
        citation="Task Force, 1996",
        rationale="Percentage of successive NN differences >50 ms; marker of parasympathetic tone.",
    ),
    "lf_power": MetricReference(
        metric_key="lf_power",
        display_name="LF Power",
        unit="ms²",
        lower_bound=400.0,
        upper_bound=1500.0,
        citation="Task Force, 1996",
        rationale="Reflects baroreflex and mixed autonomic modulation in the 0.04-0.15 Hz band.",
    ),
    "hf_power": MetricReference(
        metric_key="hf_power",
        display_name="HF Power",
        unit="ms²",
        lower_bound=300.0,
        upper_bound=1200.0,
        citation="Shaffer & Ginsberg, 2017",
        rationale="Indexes respiratory sinus arrhythmia and parasympathetic activity (0.15-0.40 Hz).",
    ),
    "lf_hf_ratio": MetricReference(
        metric_key="lf_hf_ratio",
        display_name="LF/HF Ratio",
        unit="ratio",
        lower_bound=0.5,
        upper_bound=3.0,
        citation="Task Force, 1996",
        rationale="Contextual indicator of sympathovagal balance; interpretation requires breathing context.",
    ),
    "mean_hr_bpm": MetricReference(
        metric_key="mean_hr_bpm",
        display_name="Mean HR",
        unit="bpm",
        lower_bound=50.0,
        upper_bound=80.0,
        citation="Task Force, 1996",
        rationale="Resting heart rate anchor to interpret variability in operational terms.",
    ),
}


class LocalMetricExplainer:
    """Deterministic, reference-backed metric explanations."""

    def __init__(
        self,
        references: Mapping[str, MetricReference] | None = None,
    ) -> None:
        self._references = references or _DEFAULT_REFERENCES

    @property
    def reference_catalogue(self) -> Dict[str, Dict[str, Any]]:
        """Return the reference table in JSON-serializable form."""
        catalogue: Dict[str, Dict[str, Any]] = {}
        for metric, ref in self._references.items():
            catalogue[metric] = {
                "display_name": ref.display_name,
                "unit": ref.unit,
                "lower_bound": ref.lower_bound,
                "upper_bound": ref.upper_bound,
                "citation": ref.citation,
                "rationale": ref.rationale,
            }
        return catalogue

    def explain(
        self,
        metrics_df: pd.DataFrame,
        *,
        max_datasets: int = 3,
    ) -> Tuple[MetricExplanation, ...]:
        """
        Generate explanations for up to `max_datasets` rows in the metrics table.
        """
        if metrics_df.empty:
            return tuple()
        explanations: List[MetricExplanation] = []
        for row_index, (_, row) in enumerate(
            metrics_df.head(max_datasets).iterrows()
        ):
            dataset = str(row.get("source", f"dataset_{row_index+1}"))
            for ref in self._references.values():
                value = self._to_float(row.get(ref.metric_key))
                if value is None or not math.isfinite(value):
                    continue
                status, narrative = self._status_and_message(value, ref)
                explanations.append(
                    MetricExplanation(
                        dataset=dataset,
                        metric_key=ref.metric_key,
                        display_name=ref.display_name,
                        value=float(round(value, 2)),
                        unit=ref.unit,
                        status=status,
                        explanation=narrative,
                        citation=ref.citation,
                    )
                )
        return tuple(explanations)

    def build_metric_samples(
        self,
        metrics_df: pd.DataFrame,
        *,
        max_datasets: int = 3,
    ) -> List[Dict[str, Any]]:
        """Build JSON-friendly samples for mission context."""
        samples: List[Dict[str, Any]] = []
        if metrics_df.empty:
            return samples
        for row_index, (_, row) in enumerate(
            metrics_df.head(max_datasets).iterrows()
        ):
            dataset = str(row.get("source", f"dataset_{row_index+1}"))
            metric_entries: List[Dict[str, Any]] = []
            for ref in self._references.values():
                value = self._to_float(row.get(ref.metric_key))
                if value is None or not math.isfinite(value):
                    continue
                metric_entries.append(
                    {
                        "metric": ref.metric_key,
                        "display_name": ref.display_name,
                        "value": float(round(value, 3)),
                        "unit": ref.unit,
                        "reference_range": {
                            "lower": ref.lower_bound,
                            "upper": ref.upper_bound,
                        },
                    }
                )
            if metric_entries:
                samples.append(
                    {
                        "dataset": dataset,
                        "metrics": metric_entries,
                    }
                )
        return samples

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _status_and_message(
        value: float,
        reference: MetricReference,
    ) -> Tuple[str, str]:
        lo = reference.lower_bound
        hi = reference.upper_bound
        unit = reference.unit
        value_str = f"{value:.2f}"

        if value < lo:
            status = "below_reference"
            qualifier = "below"
        elif value > hi:
            status = "above_reference"
            qualifier = "above"
        else:
            status = "within_reference"
            qualifier = "within"

        explanation = (
            f"{reference.display_name} is {value_str} {unit} "
            f"({qualifier} {lo:.1f}-{hi:.1f} {unit}). "
            f"{reference.rationale}"
        ).strip()

        return status, explanation


class AgentInsightManager:
    """Coordinate deterministic explanations and the Agents SDK persona."""

    def __init__(
        self,
        *,
        runtime: Optional[AgentRuntime] = None,
        explainer: Optional[LocalMetricExplainer] = None,
    ) -> None:
        self._runtime = runtime or AgentRuntime()
        self._explainer = explainer or LocalMetricExplainer()

    def generate_metric_insights(
        self,
        metrics_df: pd.DataFrame,
        *,
        user_context: Mapping[str, Any] | None = None,
        run_agent: bool = False,
        max_datasets: int = 3,
    ) -> MetricInsightResult:
        """
        Produce deterministic explanations and (optionally) invoke the agent persona.
        """
        explanations = self._explainer.explain(
            metrics_df, max_datasets=max_datasets
        )
        metric_samples = self._explainer.build_metric_samples(
            metrics_df, max_datasets=max_datasets
        )
        if not metric_samples:
            return MetricInsightResult(
                explanations=tuple(),
                agent_markdown=None,
                agent_payload=None,
                agent_error=None,
                used_agent=False,
            )

        mission_context = {
            "user_profile": dict(user_context or {}),
            "metric_samples": metric_samples,
            "reference_catalogue": self._explainer.reference_catalogue,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        }

        user_prompt = (
            "Review the provided HRV metric samples. "
            "For each metric, compute how far the value is from the reference "
            "range, classify it as below/within/above reference, and explain "
            "the physiological meaning plus operational implication in 2-3 sentences. "
            "Cite the provided reference_catalogue entries (Task Force 1996 or "
            "Shaffer & Ginsberg 2017)."
        )

        agent_payload: Optional[Dict[str, Any]] = None
        agent_markdown: Optional[str] = None
        agent_error: Optional[str] = None
        used_agent = False

        try:
            agent_payload = self._runtime.build_request_payload(
                "metric_explainer",
                mission_context,
                user_prompt,
            )
        except ValueError as exc:
            agent_error = str(exc)

        if run_agent and agent_payload and self._runtime.is_available():
            try:
                response = self._runtime.run_agent(
                    "metric_explainer",
                    mission_context,
                    user_prompt,
                )
                agent_markdown = _coerce_response_text(response)
                used_agent = True
            except RuntimeError as exc:
                agent_error = str(exc)
            except Exception as exc:  # pragma: no cover - defensive
                log_exception(
                    _LOGGER,
                    "Metric explanation agent execution failed",
                    exc,
                )
                agent_error = str(exc)

        return MetricInsightResult(
            explanations=explanations,
            agent_markdown=agent_markdown,
            agent_payload=agent_payload,
            agent_error=agent_error,
            used_agent=used_agent,
        )


def _coerce_response_text(response: Any) -> str:
    """
    Extract human-readable text from an Agents SDK response object.
    """
    if response is None:
        return ""
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    if isinstance(output_text, Sequence):
        joined = " ".join(str(chunk) for chunk in output_text if chunk)
        if joined.strip():
            return joined.strip()
    content = getattr(response, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()
    return str(response)


__all__ = [
    "AgentInsightManager",
    "MetricInsightResult",
    "MetricExplanation",
]
