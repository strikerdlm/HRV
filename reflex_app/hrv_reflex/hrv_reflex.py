# Author: Dr Diego Malpica MD

"""Reflex app module entrypoint.

Reflex expects a module matching `rxconfig.py` `app_name` containing the `app`
instance. We keep the real implementation in `app.py` and re-export it here.
"""

from __future__ import annotations

from .app import app  # noqa: F401

