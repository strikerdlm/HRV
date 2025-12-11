"""Utilities for generating discreet TTS audio responses via OpenAI tts-hd."""

from __future__ import annotations

import os
from typing import Final

import requests

try:  # pragma: no cover - dual import paths
	from app.logging_config import get_logger, log_exception, log_user_action
except ImportError:  # pragma: no cover - Streamlit fallback
	from logging_config import (  # type: ignore
		get_logger,
		log_exception,
		log_user_action,
	)

_LOGGER = get_logger("agent_tts")
_TTS_ENDPOINT: Final[str] = os.getenv(
	"OPENAI_TTS_ENDPOINT",
	"https://api.openai.com/v1/audio/speech",
)
_DEFAULT_MODEL: Final[str] = os.getenv("OPENAI_TTS_MODEL", "tts-1-hd")
_DEFAULT_VOICE: Final[str] = os.getenv("OPENAI_TTS_VOICE", "alloy")
_DEFAULT_FORMAT: Final[str] = os.getenv("OPENAI_TTS_FORMAT", "mp3")
_MAX_CHARS: Final[int] = 6000


def synthesize_agent_speech(
	text: str,
	*,
	model: str | None = None,
	voice: str | None = None,
	audio_format: str | None = None,
	timeout: int = 60,
) -> bytes:
	"""Convert markdown/text into a high-fidelity audio clip."""
	sanitized = (text or "").strip()
	if not sanitized:
		raise ValueError("Cannot synthesize audio for empty content.")

	if len(sanitized) > _MAX_CHARS:
		sanitized = sanitized[:_MAX_CHARS]

	api_key = os.getenv("OPENAI_API_KEY")
	if not api_key:
		raise RuntimeError("OPENAI_API_KEY is required for TTS playback.")

	payload = {
		"model": model or _DEFAULT_MODEL,
		"voice": voice or _DEFAULT_VOICE,
		"input": sanitized,
		"format": audio_format or _DEFAULT_FORMAT,
	}

	headers = {
		"Authorization": f"Bearer {api_key}",
		"Content-Type": "application/json",
	}

	try:
		response = requests.post(
			_TTS_ENDPOINT,
			json=payload,
			headers=headers,
			timeout=timeout,
		)
		response.raise_for_status()
	except requests.RequestException as exc:  # pragma: no cover - network path
		log_exception(_LOGGER, "TTS synthesis request failed", exc)
		raise RuntimeError("Text-to-speech synthesis failed") from exc

	audio_bytes = response.content
	if not audio_bytes:
		raise RuntimeError("Text-to-speech response did not include audio data.")

	log_user_action(
		"agent_tts_generated",
		{
			"model": payload["model"],
			"voice": payload["voice"],
			"chars": len(sanitized),
			"bytes": len(audio_bytes),
		},
	)
	_LOGGER.info(
		"TTS audio generated | model=%s | voice=%s | bytes=%d",
		payload["model"],
		payload["voice"],
		len(audio_bytes),
	)
	return audio_bytes


__all__ = ["synthesize_agent_speech"]
