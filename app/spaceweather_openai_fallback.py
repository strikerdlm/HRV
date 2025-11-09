from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Mapping, Optional

import json
import os

from openai import OpenAI

try:
from spaceweatherlive_client import (
	CMERecord,
		FlareProbabilities,
		KpForecastEntry,
	SIDCUrsigramReport,
		SpaceWeatherSnapshot,
	)
except ImportError:
	from .spaceweatherlive_client import (  # type: ignore
	CMERecord,
		FlareProbabilities,
		KpForecastEntry,
	SIDCUrsigramReport,
		SpaceWeatherSnapshot,
	)
from datetime import datetime, timezone


def _build_instruction() -> str:
	return (
		"You are a research assistant. Extract key space weather metrics from the provided HTML snippets. "
		"Return a strict JSON object with this schema:\n"
		"{\n"
		'  "kp_forecast": [{"day": str, "min_kp": number|null, "max_kp": number|null}],\n'
		'  "solar_wind_speed_kms": number|null,\n'
		'  "solar_wind_density_pcc": number|null,\n'
		'  "imf_bt_nt": number|null,\n'
		'  "imf_bz_nt": number|null,\n'
		'  "sunspot_number": number|null,\n'
		'  "f107_flux": number|null,\n'
		'  "flare_probabilities": {"C": number|null, "M": number|null, "X": number|null},\n'
		'  "cmes": [\n'
		"    {\n"
		'      "cactus_id": string,\n'
		'      "onset_time_utc": string|null,\n'
		'      "duration_hours": number|null,\n'
		'      "position_angle_deg": number|null,\n'
		'      "angular_width_deg": number|null,\n'
		'      "velocity_kms": number|null,\n'
		'      "velocity_variation_kms": number|null,\n'
		'      "velocity_min_kms": number|null,\n'
		'      "velocity_max_kms": number|null,\n'
		'      "halo_class": string|null\n'
		"    }\n"
		"  ],\n"
		'  "sidc_ursigram": {\n'
		'    "issued_utc": string|null,\n'
		'    "bulletin_excerpt": string|null,\n'
		'    "cme_highlights": string|null\n'
		"  }\n"
		"}\n"
		"- Numbers must be numeric (not strings). If a field is missing, use null.\n"
		"- For Kp values like 'Kp5-' output 5.0.\n"
		"- Dates must be ISO-8601 strings (UTC preferred) when available.\n"
	)


def _parse_iso_datetime(value: object) -> Optional[datetime]:
	if not isinstance(value, str):
		return None
	text = value.strip()
	if not text:
		return None
	try:
		if text.endswith("Z"):
			text = text[:-1] + "+00:00"
		return datetime.fromisoformat(text)
	except ValueError:
		return None


def extract_spaceweather_with_openai(
	html_sections: Mapping[str, str],
	model: str = "gpt-5",
) -> Optional[SpaceWeatherSnapshot]:
	"""
	Fallback extraction: ask OpenAI Responses API to parse SpaceWeatherLive HTML into a JSON payload,
	then map that to SpaceWeatherSnapshot.

	Parameters
	----------
	html_sections : Mapping[str, str]
		Dictionary with HTML snippets keyed by page name (e.g. {"home": "<html...>", "solar_activity": "<html...>"}).
	model : str
		OpenAI model name (default: "gpt-5").

	Returns
	-------
	Optional[SpaceWeatherSnapshot]
		Parsed snapshot if the model returns valid JSON; None on failure.
	"""
	# Ensure API key is configured via environment (never commit secrets)
	if not os.getenv("OPENAI_API_KEY"):
		return None

	client = OpenAI()

	# Combine all HTML segments into one user content block
	joined_html = "\n\n".join([f"[{k}]\n{v}" for k, v in html_sections.items()])

	try:
		resp = client.responses.create(
			model=model,
			input=[
				{
					"role": "developer",
					"content": [{"type": "input_text", "text": _build_instruction()}],
				},
				{
					"role": "user",
					"content": [{"type": "input_text", "text": joined_html}],
				},
			],
			text={"format": {"type": "json_object"}, "verbosity": "medium"},
			reasoning={"effort": "high", "summary": "auto"},
			store=False,
			include=[],
		)
	except Exception:
		return None

	# Extract text content (robust to minor client variations)
	json_text: Optional[str] = None
	try:
		if hasattr(resp, "output_text"):
			json_text = resp.output_text  # type: ignore[attr-defined]
		elif hasattr(resp, "output") and resp.output:
			# responses SDK often returns structured chunks; fall back to first text chunk
			chunks = getattr(resp, "output")
			for ch in chunks:  # type: ignore[assignment]
				content = getattr(ch, "content", None)
				if isinstance(content, list):
					for c in content:
						if isinstance(c, dict) and c.get("type") == "output_text":
							json_text = c.get("text")
							break
				if json_text:
					break
	except Exception:
		json_text = None

	if not json_text:
		return None

	try:
		payload: Dict[str, object] = json.loads(json_text)
	except json.JSONDecodeError:
		return None

	# Map JSON payload into our dataclasses with defensive checks
	kp_raw = payload.get("kp_forecast") if isinstance(payload, dict) else None
	kp: list[KpForecastEntry] = []
	if isinstance(kp_raw, list):
		for item in kp_raw:
			if not isinstance(item, dict):
				continue
			day = str(item.get("day")) if item.get("day") is not None else ""
			min_kp = item.get("min_kp")
			max_kp = item.get("max_kp")
			kp.append(
				KpForecastEntry(
					day_label=day,
					min_kp=float(min_kp) if isinstance(min_kp, (int, float)) else None,
					max_kp=float(max_kp) if isinstance(max_kp, (int, float)) else None,
				)
			)

	def _num_or_none(x: object) -> Optional[float]:
		return float(x) if isinstance(x, (int, float)) else None

	flare = payload.get("flare_probabilities") if isinstance(payload, dict) else None
	fp = FlareProbabilities(
		c_class_pct=_num_or_none(flare.get("C")) if isinstance(flare, dict) else None,
		m_class_pct=_num_or_none(flare.get("M")) if isinstance(flare, dict) else None,
		x_class_pct=_num_or_none(flare.get("X")) if isinstance(flare, dict) else None,
	)

	cme_entries: List[CMERecord] = []
	if isinstance(payload, dict):
		cme_raw = payload.get("cmes")
		if isinstance(cme_raw, list):
			for item in cme_raw:
				if not isinstance(item, dict):
					continue
				cme_id = str(item.get("cactus_id") or "").strip()
				if not cme_id:
					continue
				cme_entries.append(
					CMERecord(
						cactus_id=cme_id,
						onset_time_utc=_parse_iso_datetime(item.get("onset_time_utc")),
						duration_hours=_num_or_none(item.get("duration_hours")),
						position_angle_deg=_num_or_none(item.get("position_angle_deg")),
						angular_width_deg=_num_or_none(item.get("angular_width_deg")),
						velocity_kms=_num_or_none(item.get("velocity_kms")),
						velocity_variation_kms=_num_or_none(item.get("velocity_variation_kms")),
						velocity_min_kms=_num_or_none(item.get("velocity_min_kms")),
						velocity_max_kms=_num_or_none(item.get("velocity_max_kms")),
						halo_class=str(item.get("halo_class")).strip() if item.get("halo_class") else None,
					)
				)

	sidc_payload = payload.get("sidc_ursigram") if isinstance(payload, dict) else None
	sidc_report = None
	if isinstance(sidc_payload, dict):
		sidc_report = SIDCUrsigramReport(
			issued_utc=_parse_iso_datetime(sidc_payload.get("issued_utc")),
			bulletin_excerpt=str(sidc_payload.get("bulletin_excerpt")).strip()
			if sidc_payload.get("bulletin_excerpt")
			else None,
			cme_highlights=str(sidc_payload.get("cme_highlights")).strip()
			if sidc_payload.get("cme_highlights")
			else None,
		)

	return SpaceWeatherSnapshot(
		timestamp_utc=datetime.now(timezone.utc),
		kp_forecast=kp,
		solar_wind_speed_kms=_num_or_none(payload.get("solar_wind_speed_kms")) if isinstance(payload, dict) else None,
		solar_wind_density_pcc=_num_or_none(payload.get("solar_wind_density_pcc")) if isinstance(payload, dict) else None,
		imf_bt_nt=_num_or_none(payload.get("imf_bt_nt")) if isinstance(payload, dict) else None,
		imf_bz_nt=_num_or_none(payload.get("imf_bz_nt")) if isinstance(payload, dict) else None,
		sunspot_number=int(payload.get("sunspot_number")) if isinstance(payload, dict) and isinstance(payload.get("sunspot_number"), (int, float)) else None,
		f107_flux=_num_or_none(payload.get("f107_flux")) if isinstance(payload, dict) else None,
		flare_probabilities=fp,
		cme_records=cme_entries,
		sidc_report=sidc_report,
	)


