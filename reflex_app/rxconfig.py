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

    raw = os.environ.get("API_URL")
    if raw is None:
        return None
    value = raw.strip()
    return value or None


config = rx.Config(
    app_name="hrv_reflex",
    api_url=_resolve_api_url(),
)

