# Author: Dr Diego Malpica MD

"""Mission Control - Flight Surgeon (Reflex v2) application entrypoint."""

from __future__ import annotations

import asyncio
from typing import Any

import reflex as rx

from .pages.echarts_demo import echarts_demo_page
from .pages.home import home_page
from .pages.operational import operational_page
from .pages.research import research_page
from .pages.space_weather_ds import space_weather_ds_page
from .theme import app_theme


async def _startup_logging_task(*, app: Any | None = None) -> None:  # noqa: ARG001
    """Initialize the shared logging stack without blocking the event loop."""

    # Keep imports inside the lifespan task to avoid import-time side effects.
    try:
        from app.logging_config import setup_logging  # type: ignore
    except Exception:
        # If the legacy package isn't on PYTHONPATH, don't crash the server.
        return

    await asyncio.to_thread(setup_logging)


# App setup.
app = rx.App(theme=app_theme())
app.register_lifespan_task(_startup_logging_task)

# Pages / routes.
app.add_page(home_page, route="/", title="Mission Control — Reflex v2")
app.add_page(space_weather_ds_page, route="/space-weather-ds", title="Space Weather DS")
app.add_page(operational_page, route="/operational", title="Operational")
app.add_page(research_page, route="/research", title="Research")
app.add_page(echarts_demo_page, route="/echarts-demo", title="ECharts Demo")

