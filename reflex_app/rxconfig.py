"""
Author: Dr Diego Malpica MD

Reflex configuration for Mission Control - Flight Surgeon (Reflex v2).

Notes
-----
- This Reflex app lives in `reflex_app/` to keep the legacy Streamlit app in `app/`
  untouched and runnable.
- `api_url` must be externally reachable in production. Use `API_URL` env var
  to override without code changes.
"""

from __future__ import annotations

import os

import reflex as rx


def _resolve_api_url() -> str | None:
    """Resolve API URL for production deployments.

    Reflex requires the browser to connect to the backend websocket; in production
    the `api_url` must be publicly reachable.
    """

    raw = os.environ.get("API_URL", "").strip()
    if raw:
        return raw
    # Default for local Docker runs; override via API_URL in prod.
    return "http://localhost:8000"


def _resolve_cors_allowed_origins() -> list[str]:
    """Resolve CORS origins for local + containerized access.

    Uses CORS_ALLOWED_ORIGINS env var (comma-separated) when provided.
    """

    raw = os.environ.get("CORS_ALLOWED_ORIGINS")
    if isinstance(raw, str) and raw.strip():
        parts = [item.strip() for item in raw.split(",")]
        return [item for item in parts if item]

    return ["*"]


config = rx.Config(
    app_name="hrv_reflex",
    api_url=_resolve_api_url(),
    cors_allowed_origins=_resolve_cors_allowed_origins(),
)

