"""GPT-5.1 interpretation module for HRV analysis.

This module provides AI-powered interpretation of HRV analysis results using
OpenAI's GPT-5.1 model with high reasoning capabilities. It includes:
- GPT-5.1 with high reasoning effort for doctoral-level analysis
- Robust error handling with retry logic
- Rate limiting and timeout management
- Local rule-based fallback when API unavailable

Design principles:
- Uses only GPT-5.1 for maximum interpretation quality
- High reasoning effort for complex HRV analysis
- Graceful degradation when API is unavailable
- Deterministic fallback interpretations
- Bounded retries and timeouts
- Comprehensive error reporting
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Final, Iterable, Mapping, Optional

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

from agent_logging import log_agent_output

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# GPT-5.1 is the only model used for interpretation
_MODEL: Final[str] = "gpt-5.1"

_DEFAULT_TIMEOUT: Final[float] = 120.0  # Increased for high reasoning
_MAX_RETRIES: Final[int] = 3
_RETRY_DELAY_SECONDS: Final[float] = 2.0


class InterpretationMode(str, Enum):
    """Mode for interpretation generation."""

    API = "api"
    LOCAL = "local"


@dataclass(slots=True, frozen=True)
class InterpretationResult:
    """Result of HRV interpretation.

    Attributes:
        markdown: Formatted interpretation text.
        reasoning_encrypted: Encrypted reasoning from GPT-5.1.
        sources: List of cited sources.
        model_used: Model that generated the interpretation (always gpt-5.1 for API).
        mode: Whether API or local fallback was used.
        confidence: Confidence level (1.0 for API, lower for local).
    """

    markdown: str
    reasoning_encrypted: str | None = None
    sources: list[str] = field(default_factory=list)
    model_used: str = "unknown"
    mode: InterpretationMode = InterpretationMode.API
    confidence: float = 1.0


class GPT5InterpretationError(RuntimeError):
    """Exception raised when interpretation fails."""

    pass


def _clean_scalar(value: Any) -> Any:
    """Clean a scalar value for JSON serialization."""
    if value is None:
        return None
    if isinstance(value, (int, float, bool, str)):
        return value
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception as exc:
            raise GPT5InterpretationError(
                "Failed to convert scalar for serialization."
            ) from exc
    return str(value)


def _records_from_dataframe(
    df: pd.DataFrame,
    *,
    max_rows: int,
    max_columns: int,
    round_decimals: int = 3,
) -> list[dict[str, Any]]:
    """Convert DataFrame to list of records for JSON serialization."""
    if df.empty:
        return []
    selected_columns = list(df.columns[:max_columns])
    trimmed = df.loc[:, selected_columns].head(max_rows).copy()
    for column in trimmed.columns:
        if pd.api.types.is_numeric_dtype(trimmed[column]):
            trimmed[column] = trimmed[column].round(round_decimals)
        trimmed[column] = trimmed[column].map(_clean_scalar)
    return trimmed.to_dict(orient="records")


def build_analysis_payload(
    meta_rows: Iterable[Mapping[str, Any]],
    multi_results_df: pd.DataFrame,
    windowed_df: pd.DataFrame,
    episodes_df: pd.DataFrame,
    ml_summary_df: pd.DataFrame,
    *,
    report_markdown: Optional[str] = None,
    max_table_rows: int = 12,
    max_table_columns: int = 20,
) -> str:
    """Build JSON payload for AI interpretation.

    Args:
        meta_rows: Dataset metadata rows.
        multi_results_df: Comprehensive metrics DataFrame.
        windowed_df: Windowed metrics DataFrame.
        episodes_df: Deviation episodes DataFrame.
        ml_summary_df: ML clustering summary DataFrame.
        max_table_rows: Maximum rows per table.
        max_table_columns: Maximum columns per table.
        report_markdown: Optional markdown export preview to include.

    Returns:
        JSON string payload for interpretation.
    """
    payload: dict[str, Any] = {
        "datasets_overview": [_clean_scalar_dict(row) for row in meta_rows],
        "summary_metrics": _records_from_dataframe(
            multi_results_df,
            max_rows=max_table_rows,
            max_columns=max_table_columns,
        ),
        "windowed_metrics_sample": _records_from_dataframe(
            windowed_df,
            max_rows=max_table_rows,
            max_columns=max_table_columns,
        ),
        "episodes_summary": _records_from_dataframe(
            episodes_df,
            max_rows=max_table_rows,
            max_columns=max_table_columns,
        ),
        "ml_clusters": _records_from_dataframe(
            ml_summary_df,
            max_rows=max_table_rows,
            max_columns=max_table_columns,
        ),
        "plot_catalogue": [
            {
                "id": "time_series",
                "description": "RR and heart rate time series with artifact flags.",
            },
            {
                "id": "frequency_overlay",
                "description": "Power spectral density overlay across datasets.",
            },
            {
                "id": "nonlinear",
                "description": "Poincaré, DFA, entropy, and nonlinear scatter plots.",
            },
            {
                "id": "spectrogram",
                "description": "Time–frequency spectrogram of RR intervals.",
            },
            {
                "id": "windowed_metrics",
                "description": "Sliding-window metrics with deviation flag timeline.",
            },
            {
                "id": "autonomic_tests",
                "description": "Valsalva, deep breathing, and 30:15 ratio metrics.",
            },
            {
                "id": "readiness",
                "description": "Parasympathetic readiness indices versus baseline.",
            },
            {
                "id": "gauges",
                "description": "Dashboard gauges summarizing HRV domains.",
            },
        ],
    }
    if report_markdown:
        payload["export_markdown_excerpt"] = report_markdown[:12000]
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def _clean_scalar_dict(row: Mapping[str, Any]) -> dict[str, Any]:
    """Clean a dictionary for JSON serialization."""
    return {str(key): _clean_scalar(value) for key, value in row.items()}


def _build_gpt5_messages(analysis_payload: str) -> list[dict[str, Any]]:
    """Build messages for GPT-5.1 Responses API format with high reasoning."""
    developer_prompt = (
        "You are a doctoral-level biomedical research assistant specializing in "
        "heart rate variability (HRV) analysis for publication in Q1 scientific journals. "
        "Your expertise spans autonomic nervous system physiology, cardiovascular "
        "psychophysiology, and aerospace medicine.\n\n"
        "TASK: Interpret the HRV analysis payload with maximum analytical depth, "
        "synthesizing insights across all computed metrics, time-domain, frequency-domain, "
        "and nonlinear analyses.\n\n"
        "REQUIREMENTS:\n"
        "1. Provide multi-paragraph interpretation for each metric domain\n"
        "2. Cite specific numeric values from the payload with proper units\n"
        "3. Compare values against published reference ranges (cite sources)\n"
        "4. Identify statistically significant findings and clinical implications\n"
        "5. Discuss autonomic balance and its physiological significance\n"
        "6. Address methodological considerations and data quality\n"
        "7. Connect findings to operational readiness (aerospace/occupational context)\n"
        "8. Provide evidence-based recommendations\n\n"
        "REFERENCE RANGES (short-term, healthy adults at rest):\n"
        "- SDNN: 50±16 ms (Task Force, 1996)\n"
        "- RMSSD: 42±15 ms (Shaffer & Ginsberg, 2017)\n"
        "- pNN50: 10-25% typical range\n"
        "- LF power: 1000-1500 ms² (absolute)\n"
        "- HF power: 500-1000 ms² (absolute)\n"
        "- LF/HF ratio: 1.5-2.0 (context-dependent)\n"
        "- DFA α1: 0.75-1.25 (healthy fractal dynamics)\n"
        "- Sample Entropy: 1.0-2.0 (healthy complexity)\n\n"
        "OUTPUT FORMAT: Structured markdown with clear sections, tables where appropriate, "
        "and a final summary with actionable recommendations.\n\n"
        "CITATIONS: Use the `web_search` tool to retrieve peer-reviewed or NASA/NOAA sources "
        "for every novel claim. Present citations in APA format with DOI/URL under a `## Sources` "
        "section."
    )
    user_prompt = (
        "Analyze the following comprehensive HRV study output and produce a "
        "doctoral-level research report suitable for peer-reviewed publication:\n\n"
        f"{analysis_payload}"
    )
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


def _request_gpt5_high_reasoning(
    client: Any,
    analysis_payload: str,
) -> tuple[str, str | None, list[str]]:
    """Request interpretation using GPT-5.1 with high reasoning effort.

    Args:
        client: OpenAI client instance.
        analysis_payload: JSON payload for interpretation.

    Returns:
        Tuple of (markdown, reasoning_encrypted, sources).
    """
    response = client.responses.create(
        model=_MODEL,
        input=_build_gpt5_messages(analysis_payload),
        text={"format": {"type": "text"}},
        reasoning={
            "effort": "high",
            "summary": "detailed",
        },
        tools=[{"type": "web_search", "web_search": {"mode": "auto"}}],
        store=False,
        include=["reasoning.encrypted_content"],
    )

    markdown = _extract_markdown_gpt5(response)
    reasoning = _extract_reasoning_encrypted(response)
    sources = _extract_sources(response)

    return markdown, reasoning, sources


def request_interpretation(
    analysis_payload: str,
    *,
    timeout: float = _DEFAULT_TIMEOUT,
    max_retries: int = _MAX_RETRIES,
) -> InterpretationResult:
    """Request AI interpretation using GPT-5.1 with high reasoning.

    This function uses only GPT-5.1 with high reasoning effort for maximum
    interpretation quality. If the API is unavailable, it falls back to
    local rule-based interpretation.

    Args:
        analysis_payload: JSON payload from build_analysis_payload.
        timeout: Request timeout in seconds (default 120s for high reasoning).
        max_retries: Maximum retry attempts.

    Returns:
        InterpretationResult with interpretation and metadata.
    """
    if not analysis_payload:
        raise GPT5InterpretationError("Analysis payload is empty.")

    if not OPENAI_AVAILABLE:
        _LOGGER.warning("OpenAI library not available; using local fallback.")
        fallback_result = _generate_local_interpretation(analysis_payload)
        log_agent_output(
            "gpt5_interpretation",
            fallback_result.markdown,
            citations=fallback_result.sources,
            metadata={"mode": fallback_result.mode.value},
        )
        return fallback_result

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        _LOGGER.warning("OPENAI_API_KEY not set; using local fallback.")
        fallback_result = _generate_local_interpretation(analysis_payload)
        log_agent_output(
            "gpt5_interpretation",
            fallback_result.markdown,
            citations=fallback_result.sources,
            metadata={"mode": fallback_result.mode.value},
        )
        return fallback_result

    client = OpenAI(timeout=timeout)
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            _LOGGER.info(
                f"Requesting GPT-5.1 interpretation with high reasoning "
                f"(attempt {attempt + 1}/{max_retries})"
            )

            markdown, reasoning, sources = _request_gpt5_high_reasoning(
                client, analysis_payload
            )

            _LOGGER.info("GPT-5.1 interpretation completed successfully.")

            result = InterpretationResult(
                markdown=_append_sources_section(markdown, sources),
                reasoning_encrypted=reasoning,
                sources=sources,
                model_used=_MODEL,
                mode=InterpretationMode.API,
                confidence=1.0,
            )
            log_agent_output(
                "gpt5_interpretation",
                result.markdown,
                citations=result.sources,
                metadata={"mode": result.mode.value},
            )
            return result

        except RateLimitError as exc:
            _LOGGER.warning(f"Rate limit hit (attempt {attempt + 1}): {exc}")
            last_error = exc
            # Exponential backoff for rate limits
            delay = _RETRY_DELAY_SECONDS * (2**attempt)
            time.sleep(delay)
            continue

        except APIConnectionError as exc:
            _LOGGER.warning(f"Connection error (attempt {attempt + 1}): {exc}")
            last_error = exc
            time.sleep(_RETRY_DELAY_SECONDS)
            continue

        except APIError as exc:
            _LOGGER.warning(f"API error (attempt {attempt + 1}): {exc}")
            last_error = exc
            # Don't retry on 4xx client errors (except rate limit)
            if hasattr(exc, "status_code") and 400 <= exc.status_code < 500:
                break
            time.sleep(_RETRY_DELAY_SECONDS)
            continue

        except Exception as exc:
            _LOGGER.error(f"Unexpected error (attempt {attempt + 1}): {exc}")
            last_error = exc
            break

    # API failed; use local fallback
    _LOGGER.warning(
        f"GPT-5.1 API failed after {max_retries} attempts; using local fallback. "
        f"Last error: {last_error}"
    )
    fallback_result = _generate_local_interpretation(analysis_payload)
    log_agent_output(
        "gpt5_interpretation",
        fallback_result.markdown,
        citations=fallback_result.sources,
        metadata={"mode": fallback_result.mode.value},
    )
    return fallback_result


def _extract_markdown_gpt5(response: Any) -> str:
    """Extract markdown from GPT-5.1 Responses API response."""
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = getattr(response, "output", None)
    if not output:
        raise GPT5InterpretationError("Response did not contain output text.")

    chunks: list[str] = []
    for item in output:
        content = getattr(item, "content", []) or []
        for segment in content:
            text_value = getattr(segment, "text", None)
            if isinstance(text_value, str):
                chunks.append(text_value)

    if not chunks:
        raise GPT5InterpretationError("Response output was empty.")

    return "\n\n".join(chunks).strip()


def _extract_reasoning_encrypted(response: Any) -> str | None:
    """Extract encrypted reasoning from GPT-5.1 response."""
    reasoning = getattr(response, "reasoning", None)
    if not reasoning:
        return None
    return getattr(reasoning, "encrypted_content", None)


def _extract_sources(response: Any) -> list[str]:
    """Extract web search sources from GPT-5.1 response."""
    web_actions = getattr(response, "web_search_call", None)
    if not web_actions:
        return []
    action = getattr(web_actions, "action", None)
    if not action:
        return []
    sources = getattr(action, "sources", None)
    if not sources:
        return []
    return [str(source) for source in sources]


def _append_sources_section(markdown: str, sources: list[str]) -> str:
    """Append a Sources section when the API returns citation metadata."""
    if not sources:
        return markdown
    lines = [markdown.rstrip(), "", "## Sources", ""]
    for idx, source in enumerate(sources, 1):
        lines.append(f"{idx}. {source}")
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Local rule-based interpretation fallback
# ---------------------------------------------------------------------------


def _generate_local_interpretation(payload_json: str) -> InterpretationResult:
    """Generate rule-based interpretation when API unavailable.

    This provides a deterministic fallback interpretation based on
    established HRV reference ranges and clinical guidelines.

    Args:
        payload_json: JSON payload string.

    Returns:
        InterpretationResult with local interpretation.
    """
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return InterpretationResult(
            markdown="**Error:** Could not parse analysis payload.",
            model_used="local",
            mode=InterpretationMode.LOCAL,
            confidence=0.0,
        )

    lines: list[str] = [
        "# HRV Analysis Interpretation",
        "",
        "> **Note:** This interpretation was generated using local rule-based analysis "
        "because the GPT-5.1 API was unavailable. For comprehensive AI-powered analysis, "
        "ensure OPENAI_API_KEY is configured.",
        "",
    ]

    # Dataset overview
    datasets = payload.get("datasets_overview", [])
    if datasets:
        lines.extend(
            [
                "## Dataset Summary",
                "",
                f"Analyzed **{len(datasets)}** dataset(s):",
                "",
            ]
        )
        for ds in datasets:
            name = ds.get("source", ds.get("name", "Unknown"))
            n_beats = ds.get("n_intervals", ds.get("beats", "N/A"))
            duration = ds.get("recording_duration_minutes", "N/A")
            if isinstance(duration, (int, float)):
                lines.append(f"- **{name}**: {n_beats} beats, {duration:.1f} min")
            else:
                lines.append(f"- **{name}**: {n_beats} beats")
        lines.append("")

    # Metrics interpretation
    metrics = payload.get("summary_metrics", [])
    if metrics:
        lines.extend(
            [
                "## Metrics Interpretation",
                "",
            ]
        )

        for m in metrics:
            source = m.get("source", "Dataset")
            lines.append(f"### {source}")
            lines.append("")

            # Time-domain
            sdnn = m.get("sdnn")
            rmssd = m.get("rmssd")
            pnn50 = m.get("pnn50")
            mean_hr = m.get("mean_hr")

            lines.append("#### Time-Domain Metrics")
            lines.append("")

            if sdnn is not None:
                interpretation = _interpret_sdnn(sdnn)
                lines.append(f"- **SDNN:** {sdnn:.1f} ms — {interpretation}")

            if rmssd is not None:
                interpretation = _interpret_rmssd(rmssd)
                lines.append(f"- **RMSSD:** {rmssd:.1f} ms — {interpretation}")

            if pnn50 is not None:
                interpretation = _interpret_pnn50(pnn50)
                lines.append(f"- **pNN50:** {pnn50:.1f}% — {interpretation}")

            if mean_hr is not None:
                interpretation = _interpret_hr(mean_hr)
                lines.append(f"- **Mean HR:** {mean_hr:.1f} bpm — {interpretation}")

            lines.append("")

            # Frequency-domain
            lf_hf = m.get("lf_hf_ratio")
            hf_power = m.get("hf_power")
            lf_power = m.get("lf_power")

            lines.append("#### Frequency-Domain Metrics")
            lines.append("")

            if lf_power is not None:
                lines.append(f"- **LF Power:** {lf_power:.1f} ms²")

            if hf_power is not None:
                interpretation = _interpret_hf_power(hf_power)
                lines.append(f"- **HF Power:** {hf_power:.1f} ms² — {interpretation}")

            if lf_hf is not None:
                interpretation = _interpret_lf_hf(lf_hf)
                lines.append(f"- **LF/HF Ratio:** {lf_hf:.2f} — {interpretation}")

            lines.append("")

            # Nonlinear
            dfa_alpha1 = m.get("dfa_alpha1")
            sd1 = m.get("sd1")
            sd2 = m.get("sd2")
            sample_entropy = m.get("sample_entropy")

            lines.append("#### Nonlinear Metrics")
            lines.append("")

            if dfa_alpha1 is not None:
                interpretation = _interpret_dfa_alpha1(dfa_alpha1)
                lines.append(f"- **DFA α1:** {dfa_alpha1:.2f} — {interpretation}")

            if sd1 is not None:
                lines.append(
                    f"- **Poincaré SD1:** {sd1:.1f} ms (short-term vagal modulation)"
                )

            if sd2 is not None:
                lines.append(
                    f"- **Poincaré SD2:** {sd2:.1f} ms (long-term variability)"
                )

            if sample_entropy is not None:
                interpretation = _interpret_sample_entropy(sample_entropy)
                lines.append(
                    f"- **Sample Entropy:** {sample_entropy:.2f} — {interpretation}"
                )

            lines.append("")

    # Recommendations
    lines.extend(
        [
            "## Clinical Recommendations",
            "",
            "1. **Baseline Comparison:** Compare these results with your personal "
            "baseline for meaningful interpretation.",
            "2. **Recording Conditions:** Consider posture, time of day, and breathing "
            "pattern when interpreting values.",
            "3. **Clinical Consultation:** For clinical decisions, consult with a "
            "qualified healthcare provider.",
            "4. **Repeat Measurement:** If values deviate significantly from your norm, "
            "consider repeat measurement under controlled conditions.",
            "",
            "## References",
            "",
            "- Task Force of ESC and NASPE (1996). Heart rate variability: standards "
            "of measurement. *Circulation*, 93(5), 1043-1065.",
            "- Shaffer, F., & Ginsberg, J. P. (2017). An overview of heart rate "
            "variability metrics and norms. *Frontiers in Public Health*, 5, 258.",
            "",
        ]
    )

    return InterpretationResult(
        markdown="\n".join(lines),
        model_used="local",
        mode=InterpretationMode.LOCAL,
        confidence=0.7,
    )


def _interpret_sdnn(value: float) -> str:
    """Interpret SDNN value."""
    if value < 30:
        return (
            "**Low** — Reduced overall variability; may indicate stress, fatigue, "
            "or autonomic dysfunction."
        )
    if value < 50:
        return "Below average — Somewhat reduced variability; monitor trends."
    if value <= 100:
        return "**Normal** — Within typical range for healthy adults at rest."
    return "**High** — Above average variability; typically favorable."


def _interpret_rmssd(value: float) -> str:
    """Interpret RMSSD value."""
    if value < 20:
        return (
            "**Low** — Reduced vagal tone; may indicate stress, poor recovery, "
            "or parasympathetic withdrawal."
        )
    if value < 42:
        return "Below average — Somewhat reduced parasympathetic activity."
    if value <= 80:
        return "**Normal** — Within typical range; adequate vagal modulation."
    return (
        "**High** — Strong vagal tone; typically indicates good recovery and "
        "parasympathetic dominance."
    )


def _interpret_pnn50(value: float) -> str:
    """Interpret pNN50 value."""
    if value < 3:
        return "**Low** — Reduced beat-to-beat variability."
    if value < 10:
        return "Below average."
    if value <= 30:
        return "**Normal** — Typical range."
    return "**High** — Strong short-term variability."


def _interpret_hr(value: float) -> str:
    """Interpret mean heart rate."""
    if value < 50:
        return "Bradycardic — Consider athletic conditioning or medication effects."
    if value < 60:
        return "Low-normal — Typical for well-conditioned individuals."
    if value <= 80:
        return "**Normal** — Within typical resting range."
    if value <= 100:
        return "Elevated — May indicate stress, dehydration, or recent activity."
    return "**Tachycardic** — Consider underlying causes."


def _interpret_lf_hf(value: float) -> str:
    """Interpret LF/HF ratio."""
    if value < 0.5:
        return "Strong parasympathetic dominance."
    if value < 1.5:
        return "Parasympathetic-leaning balance."
    if value <= 3.0:
        return (
            "**Balanced** — Within typical range (interpret with breathing context)."
        )
    if value <= 5.0:
        return "Sympathetic-leaning — May indicate stress or arousal."
    return "**High** — Strong sympathetic predominance; consider stress factors."


def _interpret_hf_power(value: float) -> str:
    """Interpret HF power."""
    if value < 100:
        return "**Low** — Reduced parasympathetic/respiratory activity."
    if value < 500:
        return "Below average."
    if value <= 1500:
        return "**Normal** — Adequate parasympathetic activity."
    return "**High** — Strong parasympathetic/respiratory influence."


def _interpret_dfa_alpha1(value: float) -> str:
    """Interpret DFA α1."""
    if value < 0.5:
        return "**Low** — Anti-correlated dynamics; may indicate high exercise intensity."
    if value < 0.75:
        return "Below typical resting range."
    if value <= 1.25:
        return "**Normal** — Healthy fractal-like correlation at rest."
    if value <= 1.5:
        return "Above typical range."
    return "**High** — Strong correlation; may indicate reduced complexity."


def _interpret_sample_entropy(value: float) -> str:
    """Interpret Sample Entropy."""
    if value < 0.5:
        return "**Low** — Reduced complexity; highly predictable signal."
    if value < 1.0:
        return "Below average complexity."
    if value <= 2.0:
        return "**Normal** — Healthy complexity and unpredictability."
    return "**High** — High complexity; may indicate noise or arrhythmia."
