# Author: Dr Diego Malpica MD

"""ECharts integration validation page (Reflex v2).

Uses `reflex-echarts` (echarts-for-react) to ensure the ECharts stack works
before migrating full dashboards.
"""

from __future__ import annotations

import random
from typing import Any

import reflex as rx
from reflex_echarts import echarts

from ..layout import app_shell
from ..theme import colors


class EChartsDemoState(rx.State):
    """State for the ECharts demo page."""

    option: dict[str, Any] = {
        "title": {
            "text": "ECharts Demo — HRV-style Trend (Example)",
            "subtext": "Demo only. Validates JSON-only option rendering in Reflex.",
            "left": "center",
            "textStyle": {"color": "#1a1a1a", "fontWeight": "bold", "fontSize": 16},
            "subtextStyle": {"color": "#2c3e50"},
        },
        "tooltip": {"trigger": "axis", "textStyle": {"color": "#1a1a1a"}},
        "legend": {"data": ["Series"], "textStyle": {"color": "#1a1a1a"}},
        "grid": {"left": "10%", "right": "6%", "top": "22%", "bottom": "16%"},
        "xAxis": {
            "type": "category",
            "data": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "name": "Day",
            "nameLocation": "middle",
            "nameGap": 30,
            "axisLabel": {"color": "#1a1a1a"},
            "axisLine": {"lineStyle": {"color": "#2c3e50"}},
        },
        "yAxis": {
            "type": "value",
            "name": "RMSSD (ms)",
            "nameLocation": "middle",
            "nameGap": 45,
            "axisLabel": {"color": "#1a1a1a"},
            "axisLine": {"lineStyle": {"color": "#2c3e50"}},
            "splitLine": {"lineStyle": {"color": "rgba(44, 62, 80, 0.1)"}},
        },
        "series": [{"name": "Series", "type": "line", "data": [42, 38, 45, 41, 55, 49, 52]}],
    }

    @rx.event
    def randomize(self) -> None:
        values = [random.randint(25, 75) for _ in range(7)]
        # Update in-place is fine; Reflex tracks state mutations on event handlers.
        self.option["series"][0]["data"] = values


def echarts_demo_page() -> rx.Component:
    c = colors()
    body = rx.vstack(
        rx.text(
            "If this chart renders, `reflex-echarts` is working and we can keep ECharts-first visuals.",
            color=c["text_secondary"],
        ),
        rx.box(
            echarts(option=EChartsDemoState.option),
            width="100%",
            max_width="1100px",
            border=f"1px solid {c['border']}",
            border_radius="10px",
            padding="8px",
        ),
        rx.button("Randomize demo data", on_click=EChartsDemoState.randomize),
        spacing="3",
        align="start",
        width="100%",
    )
    return app_shell(title="ECharts Demo", body=body)

