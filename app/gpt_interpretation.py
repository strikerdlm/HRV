from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

import pandas as pd
from openai import OpenAI
from openai import APIError


@dataclass(slots=True, frozen=True)
class InterpretationResult:
	markdown: str
	reasoning_encrypted: Optional[str]
	sources: List[str]


class GPT5InterpretationError(RuntimeError):
	pass


def _clean_scalar(value: Any) -> Any:
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
			raise GPT5InterpretationError("Failed to convert scalar for serialization.") from exc
	return str(value)


def _records_from_dataframe(
	df: pd.DataFrame,
	*,
	max_rows: int,
	max_columns: int,
	round_decimals: int = 3,
) -> List[Dict[str, Any]]:
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
	max_table_rows: int = 12,
	max_table_columns: int = 12,
) -> str:
	payload: Dict[str, Any] = {
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
			{"id": "time_series", "description": "RR and heart rate time series with artifact flags."},
			{"id": "frequency_overlay", "description": "Power spectral density overlay across datasets."},
			{"id": "nonlinear", "description": "Poincaré, DFA, entropy, and nonlinear scatter plots."},
			{"id": "spectrogram", "description": "Time–frequency spectrogram of RR intervals."},
			{"id": "windowed_metrics", "description": "Sliding-window metrics with deviation flag timeline."},
			{"id": "autonomic_tests", "description": "Valsalva, deep breathing, and 30:15 ratio metrics."},
			{"id": "readiness", "description": "Parasympathetic readiness indices versus baseline."},
			{"id": "gauges", "description": "Dashboard gauges summarizing HRV domains."},
		],
	}
	return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def _clean_scalar_dict(row: Mapping[str, Any]) -> Dict[str, Any]:
	return {str(key): _clean_scalar(value) for key, value in row.items()}


def build_messages(analysis_payload: str) -> List[Dict[str, Any]]:
	developer_prompt = (
		"You are a doctoral-level biomedical research assistant. "
		"Interpret the HRV analysis payload, synthesising insights across plots, tables, and computed metrics. "
		"Deliver a structured markdown briefing aimed at aerospace medicine and psychophysiology experts. "
		"Include multi-paragraph interpretation for each plot family, highlight statistically relevant findings, "
		"and connect results to clinical or operational readiness implications. "
		"Prioritise determinism, cite numeric values from the payload, and finish with concise recommendations."
	)
	user_prompt = (
		"Analyse the following HRV study output and produce a doctoral-level report:\n"
		f"{analysis_payload}"
	)
	return [
		{
			"role": "developer",
			"content": [
				{
					"type": "input_text",
					"text": developer_prompt,
				}
			],
		},
		{
			"role": "user",
			"content": [
				{
					"type": "input_text",
					"text": user_prompt,
				}
			],
		},
	]


def request_interpretation(
	analysis_payload: str,
	*,
	timeout: float = 60.0,
) -> InterpretationResult:
	if not analysis_payload:
		raise GPT5InterpretationError("Analysis payload is empty.")
	api_key = os.getenv("OPENAI_API_KEY") or ""
	if not api_key:
		raise GPT5InterpretationError("OPENAI_API_KEY is not set.")
	try:
		client = OpenAI(timeout=timeout)
		response = client.responses.create(
			model="gpt-5",
			input=build_messages(analysis_payload),
			text={"format": {"type": "text"}, "verbosity": "high"},
			reasoning={"effort": "high", "summary": "detailed"},
			tools=[],
			store=False,
			include=["reasoning.encrypted_content", "web_search_call.action.sources"],
		)
	except APIError as exc:
		raise GPT5InterpretationError(f"OpenAI API error: {exc.message}") from exc
	except Exception as exc:
		raise GPT5InterpretationError("OpenAI request failed.") from exc
	markdown = _extract_markdown(response)
	reasoning_encrypted = _extract_reasoning_encrypted(response)
	sources = _extract_sources(response)
	return InterpretationResult(markdown=markdown, reasoning_encrypted=reasoning_encrypted, sources=sources)


def _extract_markdown(response: Any) -> str:
	output_text = getattr(response, "output_text", None)
	if isinstance(output_text, str) and output_text.strip():
		return output_text.strip()
	output = getattr(response, "output", None)
	if not output:
		raise GPT5InterpretationError("Response did not contain output text.")
	chunks: List[str] = []
	for item in output:
		content = getattr(item, "content", []) or []
		for segment in content:
			text_value = getattr(segment, "text", None)
			if isinstance(text_value, str):
				chunks.append(text_value)
	if not chunks:
		raise GPT5InterpretationError("Response output was empty.")
	return "\n\n".join(chunks).strip()


def _extract_reasoning_encrypted(response: Any) -> Optional[str]:
	reasoning = getattr(response, "reasoning", None)
	if not reasoning:
		return None
	return getattr(reasoning, "encrypted_content", None)


def _extract_sources(response: Any) -> List[str]:
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

