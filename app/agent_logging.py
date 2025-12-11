"""Centralized logging helpers for OpenAI agent activity."""

from __future__ import annotations

import json
from typing import Any, Mapping, MutableMapping, Sequence

try:  # pragma: no cover - dual import paths when running as a package
	from app.logging_config import get_logger, log_user_action
except ImportError:  # pragma: no cover - Streamlit execution fallback
	from logging_config import get_logger, log_user_action  # type: ignore

_LOGGER = get_logger("agent_responses")


def _serialize_payload(payload: Mapping[str, Any] | Sequence[Any] | None) -> str:
	"""Serialize payload content defensively for log emission."""
	if payload is None:
		return "{}"
	try:
		return json.dumps(payload, default=str, ensure_ascii=False)
	except (TypeError, ValueError):
		return str(payload)


def log_agent_payload(agent_name: str, payload: Mapping[str, Any]) -> None:
	"""Persist a structured trace of the outbound agent request."""
	normalized: MutableMapping[str, Any] = {
		"agent": agent_name,
		"payload": payload,
	}
	_LOGGER.info("AGENT_PAYLOAD | %s", _serialize_payload(normalized))
	log_user_action(
		"agent_payload",
		{"agent": agent_name, "keys": sorted(payload.keys())},
	)


def log_agent_output(
	agent_name: str,
	content: str,
	*,
	citations: Sequence[str] | None = None,
	metadata: Mapping[str, Any] | None = None,
) -> None:
	"""Persist the textual answer produced by an agent persona."""
	entry: MutableMapping[str, Any] = {
		"agent": agent_name,
		"content": content,
		"length": len(content),
	}
	if citations:
		entry["citations"] = list(citations)
	if metadata:
		entry["metadata"] = dict(metadata)
	_LOGGER.info("AGENT_OUTPUT | %s", _serialize_payload(entry))
	log_user_action(
		"agent_output",
		{
			"agent": agent_name,
			"length": len(content),
			"citations": len(citations or []),
		},
	)


__all__ = ["log_agent_payload", "log_agent_output"]
