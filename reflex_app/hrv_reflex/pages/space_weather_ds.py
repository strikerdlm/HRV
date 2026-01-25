# Author: Dr Diego Malpica MD

"""Space Weather Data Science route (Phase 1 MVP)."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import reflex as rx
from reflex_echarts import echarts

from ..layout import app_shell
from ..services.echarts_builders import build_time_series_chart
from ..services.noaa_reflex import (
    build_noaa_chart_option,
    build_noaa_daily_series,
    fetch_noaa_bundles,
    get_noaa_source_keys,
    summarize_noaa_bundle,
)
from ..services.space_weather_ds_core import QCSettings, compute_session_metrics_from_text
from ..theme import colors


def _sanitize_filename(name: str) -> str:
    if not isinstance(name, str):
        return "uploaded_rr.txt"
    base = name.replace("\\", "/").split("/")[-1].strip()
    if not base:
        return "uploaded_rr.txt"
    # Keep it simple: allow alnum, space, dash, underscore, dot.
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_. ()")
    safe = "".join(ch if ch in allowed else "_" for ch in base)
    return safe[:120] or "uploaded_rr.txt"


class SpaceWeatherDSState(rx.State):
    """State for the Space Weather DS workflow (single user)."""

    # Performance profile (mirrors Streamlit DS philosophy)
    performance_profile: str = "Lightweight"

    # Stored uploaded RR file names (saved under Reflex upload dir)
    rr_files: list[str] = []

    # QC settings
    qc_method: str = "threshold_median"
    qc_max_deviation: float = 0.2
    qc_median_window: int = 11

    # Job status
    job_running: bool = False
    job_progress_pct: int = 0
    job_message: str = ""
    job_error: str = ""

    # Results (compact, JSON-friendly)
    session_metrics: list[dict[str, Any]] = []

    # HRV daily trend chart (ECharts option dict)
    hrv_trend_metric: str = "rmssd"
    hrv_trend_option: dict[str, Any] = {}

    # NOAA state
    noaa_selected_keys: list[str] = ["planetary_k_index_3h", "geospace_dst", "f107_flux"]
    noaa_summary: list[dict[str, Any]] = []
    noaa_errors: list[dict[str, str]] = []
    noaa_plot_key: str = "planetary_k_index_3h"
    noaa_plot_column: str = "Kp"
    noaa_plot_columns: list[str] = []
    noaa_option: dict[str, Any] = {}
    noaa_running: bool = False

    # Export links
    export_files: list[dict[str, str]] = []

    def _profile_settings(self) -> tuple[bool, int]:
        """Return (include_advanced, max_sessions) for the active profile."""
        name = str(self.performance_profile)
        if name == "Balanced":
            return True, 60
        if name == "RTX 5070 GPU":
            # GPU integration will be enabled in Phase 1.5+ (safe CPU fallback for MVP).
            return True, 120
        return False, 20

    def _rr_storage_dir(self) -> Path:
        base = rx.get_upload_dir() / "hrv_reflex" / "rr"
        base.mkdir(parents=True, exist_ok=True)
        return base

    def _export_dir(self) -> Path:
        base = rx.get_upload_dir() / "hrv_reflex" / "exports"
        base.mkdir(parents=True, exist_ok=True)
        return base

    @rx.event
    def set_performance_profile(self, value: str) -> None:
        """Set the performance profile selection."""
        allowed = ("Lightweight", "Balanced", "RTX 5070 GPU")
        if not isinstance(value, str) or value not in allowed:
            self.job_error = "Invalid performance profile selection."
            return
        self.performance_profile = value
        self.job_error = ""

    @rx.event
    def set_qc_method(self, value: str) -> None:
        """Set the QC method selection."""
        allowed = ("threshold_median", "threshold_prev")
        if not isinstance(value, str) or value not in allowed:
            self.job_error = "Invalid QC method selection."
            return
        self.qc_method = value
        self.job_error = ""

    @rx.event
    def set_qc_max_deviation(self, value: Sequence[float | int] | float | int) -> None:
        """Set the maximum RR deviation fraction for QC."""
        resolved: float | None = None
        if isinstance(value, (int, float)):
            resolved = float(value)
        elif isinstance(value, str):
            self.job_error = "Invalid max deviation selection."
            return
        elif isinstance(value, Sequence):
            if not value:
                self.job_error = "Invalid max deviation selection."
                return
            first = value[0]
            if not isinstance(first, (int, float)):
                self.job_error = "Invalid max deviation selection."
                return
            resolved = float(first)
        else:
            self.job_error = "Invalid max deviation selection."
            return

        if resolved < 0.05 or resolved > 0.5:
            self.job_error = "Max deviation must be between 0.05 and 0.5."
            return

        self.qc_max_deviation = resolved
        self.job_error = ""

    @rx.event
    def set_qc_median_window(self, value: int | float | str) -> None:
        """Set the QC median window length (odd integer)."""
        resolved: int | None = None
        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed.isdigit():
                resolved = int(trimmed)
            else:
                self.job_error = "Invalid median window selection."
                return
        elif isinstance(value, (int, float)):
            resolved = int(value)
        else:
            self.job_error = "Invalid median window selection."
            return

        if resolved < 5 or resolved > 31 or resolved % 2 == 0:
            self.job_error = "Median window must be an odd number between 5 and 31."
            return
        self.qc_median_window = resolved
        self.job_error = ""

    @rx.event
    def clear_rr_files(self) -> None:
        self.rr_files = []
        self.session_metrics = []
        self.hrv_trend_option = {}
        self.export_files = []
        self.job_error = ""
        self.job_message = ""
        self.job_progress_pct = 0

    @rx.event
    async def handle_rr_upload(self, files: list[Any]) -> None:
        """Save uploaded RR text files to the server upload dir.

        Note: do not store RR arrays in state (keeps UI fast on slow machines).
        """
        self.job_error = ""
        self.job_message = ""

        if not isinstance(files, list) or not files:
            self.job_error = "No files received. Select RR files, then click Upload."
            return

        storage = self._rr_storage_dir()
        saved: list[str] = []
        max_files = 60  # hard bound
        for item in files[:max_files]:
            name = _sanitize_filename(getattr(item, "filename", "uploaded_rr.txt"))
            target = storage / name
            try:
                data = await item.read()
            except Exception as exc:
                self.job_error = f"Failed to read upload: {exc}"
                continue
            # Bound disk usage (10 MB per file cap)
            if not isinstance(data, (bytes, bytearray)) or len(data) > 10_000_000:
                self.job_error = f"{name}: file too large or invalid."
                continue
            try:
                with target.open("wb") as handle:
                    handle.write(data)
            except OSError as exc:
                self.job_error = f"{name}: failed to save file: {exc}"
                continue
            saved.append(name)

        # Deduplicate while preserving order
        existing = set(self.rr_files)
        merged: list[str] = list(self.rr_files)
        for name in saved:
            if name not in existing:
                merged.append(name)
                existing.add(name)
        self.rr_files = merged
        self.job_message = f"Uploaded {len(saved)} file(s)."

    @rx.event
    def set_hrv_trend_metric(self, value: str) -> None:
        self.hrv_trend_metric = str(value)

    def _build_hrv_daily_chart_option(self, metric: str) -> dict[str, Any]:
        import pandas as pd
        import numpy as np
        from datetime import datetime

        rows = list(self.session_metrics)
        if not rows:
            return {}
        # Build a small dataframe from session metrics.
        records: list[dict[str, Any]] = []
        for r in rows:
            if "error" in r:
                continue
            ts_raw = r.get("session_start_utc")
            try:
                ts = pd.to_datetime(ts_raw, utc=True, errors="coerce")
            except Exception:
                ts = pd.NaT
            val = r.get(metric)
            try:
                fv = float(val) if val is not None else np.nan
            except (TypeError, ValueError):
                fv = np.nan
            records.append({"ts": ts, "value": fv})
        df = pd.DataFrame(records).dropna(subset=["ts"])
        if df.empty:
            return {}
        df["date"] = df["ts"].dt.date
        daily = df.groupby("date")["value"].mean()
        if daily.size < 3:
            return {}
        daily.index = pd.to_datetime(daily.index)
        dates = [d.to_pydatetime() for d in daily.index.to_pydatetime()]
        values = [None if not np.isfinite(v) else float(v) for v in daily.to_numpy(dtype=float)]
        unit_map = {"rmssd": "ms", "sdnn": "ms", "mean_hr": "bpm", "pnn50": "%"}
        unit = unit_map.get(metric, "")
        return build_time_series_chart(
            dates,
            values,
            metric_label=metric,
            unit=unit,
            subtitle="Daily mean with 7-day EWMA and 10–90 percentile reference band.",
        )

    @rx.event
    def rebuild_hrv_trend_chart(self) -> None:
        self.hrv_trend_option = self._build_hrv_daily_chart_option(self.hrv_trend_metric)

    @rx.event(background=True)
    async def run_hrv_analysis(self) -> None:
        """Compute HRV/HRF metrics in a background task."""

        include_advanced, max_sessions = self._profile_settings()
        rr_files = list(self.rr_files)[:max_sessions]
        if not rr_files:
            async with self:
                self.job_error = "Upload RR files first."
            return

        qc = QCSettings(
            method=str(self.qc_method),
            max_deviation=float(self.qc_max_deviation),
            median_window=int(self.qc_median_window),
        )
        storage = self._rr_storage_dir()

        async with self:
            self.job_running = True
            self.job_error = ""
            self.job_message = "Starting analysis..."
            self.job_progress_pct = 0
            self.session_metrics = []
            self.hrv_trend_option = {}
            self.export_files = []

        rows: list[dict[str, Any]] = []
        total = len(rr_files)
        for idx, name in enumerate(rr_files):
            # Do IO + compute outside lock.
            path = storage / name
            try:
                with path.open("rb") as handle:
                    raw = handle.read(10_000_000)
                content = raw.decode("utf-8", errors="ignore")
                metrics = await asyncio.to_thread(
                    compute_session_metrics_from_text,
                    filename=name,
                    content=content,
                    qc=qc,
                    include_advanced=include_advanced,
                )
            except Exception as exc:
                metrics = {"session_name": name, "error": str(exc)}
            rows.append(metrics)
            pct = int(((idx + 1) / max(1, total)) * 100)
            async with self:
                self.job_message = f"Processed {idx + 1}/{total}"
                self.job_progress_pct = pct

        async with self:
            self.session_metrics = rows
            # Build default trend chart (rmssd) for quick feedback.
            try:
                self.hrv_trend_option = self._build_hrv_daily_chart_option(self.hrv_trend_metric)
            except Exception:
                self.hrv_trend_option = {}
            self.job_running = False
            self.job_message = "Done."

    @rx.event
    def set_noaa_plot_key(self, value: str) -> None:
        self.noaa_plot_key = str(value)

    @rx.event
    def set_noaa_plot_column(self, value: str) -> None:
        self.noaa_plot_column = str(value)

    @rx.event(background=True)
    async def fetch_noaa(self) -> None:
        """Fetch NOAA feeds and build a chart option (background)."""

        # Always include the currently selected plot key.
        keys = list(dict.fromkeys([str(self.noaa_plot_key), *list(self.noaa_selected_keys)]))[:12]
        if not keys:
            async with self:
                self.noaa_errors = [{"key": "__all__", "error": "Select at least one NOAA dataset."}]
            return

        async with self:
            self.noaa_errors = []
            self.noaa_summary = []
            self.noaa_option = {}
            self.noaa_plot_columns = []
            self.noaa_running = True

        try:
            bundles, errors = await asyncio.to_thread(fetch_noaa_bundles, keys, use_cache=True, overall_timeout_s=45.0)
        except Exception as exc:
            async with self:
                self.noaa_errors = [{"key": "__all__", "error": str(exc)}]
                self.noaa_running = False
            return

        summaries: list[dict[str, Any]] = []
        for key, bundle in bundles.items():
            try:
                summaries.append(summarize_noaa_bundle(key, bundle))
            except Exception:
                continue

        error_rows = [{"key": k, "error": v} for k, v in (errors or {}).items()]

        # Build plot option for the current selection (if available).
        option: dict[str, Any] = {}
        plot_cols: list[str] = []
        bundle = bundles.get(self.noaa_plot_key)
        if bundle is not None:
            plot_cols = list(getattr(bundle, "value_columns", ()) or ())
            chosen_col = self.noaa_plot_column
            if chosen_col not in plot_cols and plot_cols:
                chosen_col = plot_cols[0]
            if chosen_col:
                try:
                    series = build_noaa_daily_series(bundle=bundle, value_column=chosen_col)
                    option = build_noaa_chart_option(series=series, value_column=chosen_col)
                except Exception:
                    option = {}

        async with self:
            self.noaa_summary = summaries
            self.noaa_errors = error_rows
            self.noaa_plot_columns = plot_cols
            self.noaa_option = option
            self.noaa_running = False

    @rx.event
    async def export_session_metrics(self) -> None:
        """Write CSV/JSON exports to the Reflex upload dir and expose links."""

        if not self.session_metrics:
            self.export_files = []
            return

        export_dir = self._export_dir()
        csv_name = "session_metrics_reflex.csv"
        json_name = "session_metrics_reflex.json"
        try:
            import pandas as pd

            df = pd.DataFrame(self.session_metrics)
            await asyncio.to_thread(df.to_csv, export_dir / csv_name, index=False)
        except Exception:
            # Fallback: write minimal CSV manually.
            header = sorted({k for row in self.session_metrics for k in row.keys()})
            lines = [",".join(header)]
            for row in self.session_metrics:
                lines.append(",".join(str(row.get(k, "")) for k in header))
            await asyncio.to_thread((export_dir / csv_name).write_text, "\n".join(lines), encoding="utf-8")

        import json

        await asyncio.to_thread(
            (export_dir / json_name).write_text,
            json.dumps(self.session_metrics, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        self.export_files = [
            {"name": csv_name, "url": rx.get_upload_url(f"hrv_reflex/exports/{csv_name}")},
            {"name": json_name, "url": rx.get_upload_url(f"hrv_reflex/exports/{json_name}")},
        ]


def _metrics_preview(rows: Any) -> rx.Component:
    c = colors()
    empty_view = rx.text("No results yet. Upload files and click Run analysis.", color=c["text_secondary"])

    def _metric_text(label: str, value: Any, unit: str) -> rx.Component:
        if isinstance(value, (int, float)):
            return rx.text(f"{label}: {value} {unit}".strip())
        if value is None:
            return rx.text(f"{label}: —")
        return rx.cond(
            value.is_not_none(),
            rx.text(f"{label}: ", value, f" {unit}".strip()),
            rx.text(f"{label}: —"),
        )

    def _row_view(row: Any) -> rx.Component:
        if isinstance(row, dict):
            name = str(row.get("session_name", "session"))
            err = row.get("error")
            if err:
                return rx.callout(f"{name}: {err}", icon="triangle_alert", color_scheme="red")
            rmssd = row.get("rmssd")
            sdnn = row.get("sdnn")
            mean_hr = row.get("mean_hr")
            artifact = row.get("artifact_pct")
            return rx.box(
                rx.vstack(
                    rx.heading(name, size="3", color=c["text_primary"]),
                    rx.hstack(
                        _metric_text("RMSSD", rmssd, "ms"),
                        _metric_text("SDNN", sdnn, "ms"),
                        _metric_text("Mean HR", mean_hr, "bpm"),
                        _metric_text("Artifacts", artifact, "%"),
                        wrap="wrap",
                        spacing="4",
                        color=c["text_secondary"],
                    ),
                    spacing="2",
                    align="start",
                ),
                border=f"1px solid {c['border']}",
                border_radius="10px",
                padding="12px",
                width="100%",
            )

        name = row.get("session_name", "session")
        err = row.get("error", "")
        error_view = rx.callout(rx.text(name, ": ", err), icon="triangle_alert", color_scheme="red")
        metrics_view = rx.box(
            rx.vstack(
                rx.heading(name, size="3", color=c["text_primary"]),
                rx.hstack(
                    _metric_text("RMSSD", row.get("rmssd"), "ms"),
                    _metric_text("SDNN", row.get("sdnn"), "ms"),
                    _metric_text("Mean HR", row.get("mean_hr"), "bpm"),
                    _metric_text("Artifacts", row.get("artifact_pct"), "%"),
                    wrap="wrap",
                    spacing="4",
                    color=c["text_secondary"],
                ),
                spacing="2",
                align="start",
            ),
            border=f"1px solid {c['border']}",
            border_radius="10px",
            padding="12px",
            width="100%",
        )
        return rx.cond(err, error_view, metrics_view)

    rows_view = rx.vstack(rx.foreach(rows, _row_view), spacing="3", width="100%")
    if isinstance(rows, list):
        return rows_view if rows else empty_view
    return rx.cond(rows.length() > 0, rows_view, empty_view)


def space_weather_ds_page() -> rx.Component:
    c = colors()

    upload_id = "rr_upload"
    try:
        noaa_keys = get_noaa_source_keys()
    except Exception:
        noaa_keys = ["planetary_k_index_3h", "geospace_dst", "f107_flux"]

    body = rx.vstack(
        rx.callout(
            "Phase 1 MVP: RR ingest + QC + HRV/HRF compute (background task) with minimal, fast UI.",
            icon="info",
            color_scheme="blue",
        ),
        rx.hstack(
            rx.vstack(
                rx.heading("1) Upload RR files", size="4", color=c["text_primary"]),
                rx.upload(
                    rx.text("Click to upload or drag and drop RR text files (TXT/CSV)."),
                    id=upload_id,
                    accept={"text/plain": [".txt", ".csv"]},
                    multiple=True,
                    max_files=60,
                ),
                rx.hstack(
                    rx.button(
                        "Upload",
                        on_click=SpaceWeatherDSState.handle_rr_upload(
                            rx.upload_files(upload_id=upload_id),
                        ),
                    ),
                    rx.button(
                        "Clear",
                        variant="outline",
                        on_click=SpaceWeatherDSState.clear_rr_files,
                    ),
                    spacing="2",
                ),
                rx.text(rx.selected_files(upload_id), color=c["text_secondary"]),
                spacing="2",
                align="start",
                width="100%",
            ),
            rx.vstack(
                rx.heading("2) Configure & run", size="4", color=c["text_primary"]),
                rx.hstack(
                    rx.text("Profile:", color=c["text_secondary"]),
                    rx.select(
                        ["Lightweight", "Balanced", "RTX 5070 GPU"],
                        value=SpaceWeatherDSState.performance_profile,
                        on_change=SpaceWeatherDSState.set_performance_profile,
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.hstack(
                    rx.text("QC method:", color=c["text_secondary"]),
                    rx.select(
                        ["threshold_median", "threshold_prev"],
                        value=SpaceWeatherDSState.qc_method,
                        on_change=SpaceWeatherDSState.set_qc_method,
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.hstack(
                    rx.text("Max deviation:", color=c["text_secondary"]),
                    rx.slider(
                        min=0.05,
                        max=0.5,
                        step=0.05,
                        value=[SpaceWeatherDSState.qc_max_deviation],
                        on_change=SpaceWeatherDSState.set_qc_max_deviation,
                    ),
                    spacing="2",
                    align="center",
                    width="100%",
                ),
                rx.hstack(
                    rx.text("Median window:", color=c["text_secondary"]),
                    rx.input(
                        type_="number",
                        value=SpaceWeatherDSState.qc_median_window,
                        min=5,
                        max=31,
                        step=2,
                        on_change=SpaceWeatherDSState.set_qc_median_window,
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.button(
                    "Run HRV analysis",
                    on_click=SpaceWeatherDSState.run_hrv_analysis,
                    disabled=SpaceWeatherDSState.job_running,
                    loading=SpaceWeatherDSState.job_running,
                ),
                rx.cond(
                    SpaceWeatherDSState.job_running,
                    rx.progress(value=SpaceWeatherDSState.job_progress_pct),
                    rx.text("", color=c["text_secondary"]),
                ),
                rx.cond(
                    SpaceWeatherDSState.job_error != "",
                    rx.callout(SpaceWeatherDSState.job_error, icon="triangle_alert", color_scheme="red"),
                    rx.text(SpaceWeatherDSState.job_message, color=c["text_secondary"]),
                ),
                spacing="2",
                align="start",
                width="100%",
            ),
            spacing="6",
            align="start",
            width="100%",
            wrap="wrap",
        ),
        rx.divider(),
        rx.heading("3) Results (preview)", size="4", color=c["text_primary"]),
        _metrics_preview(SpaceWeatherDSState.session_metrics),
        rx.divider(),
        rx.heading("4) Daily trend chart (ECharts)", size="4", color=c["text_primary"]),
        rx.hstack(
            rx.text("Metric:", color=c["text_secondary"]),
            rx.select(
                ["rmssd", "sdnn", "mean_hr", "pnn50"],
                value=SpaceWeatherDSState.hrv_trend_metric,
                on_change=SpaceWeatherDSState.set_hrv_trend_metric,
            ),
            rx.button("Build chart", variant="outline", on_click=SpaceWeatherDSState.rebuild_hrv_trend_chart),
            spacing="2",
            align="center",
        ),
        rx.cond(
            SpaceWeatherDSState.hrv_trend_option != {},
            rx.box(
                echarts(option=SpaceWeatherDSState.hrv_trend_option),
                width="100%",
                max_width="1100px",
                border=f"1px solid {c['border']}",
                border_radius="10px",
                padding="8px",
            ),
            rx.text("Need ≥3 days of data to render a daily trend chart.", color=c["text_secondary"]),
        ),
        rx.divider(),
        rx.heading("5) NOAA Space Weather (fetch + plot)", size="4", color=c["text_primary"]),
        rx.text("Fetch is cache-first and runs in a background task.", color=c["text_secondary"]),
        rx.hstack(
            rx.vstack(
                rx.text("Dataset:", color=c["text_secondary"]),
                rx.select(
                    noaa_keys,
                    value=SpaceWeatherDSState.noaa_plot_key,
                    on_change=SpaceWeatherDSState.set_noaa_plot_key,
                ),
                rx.button(
                    "Fetch NOAA feed (cache-first)",
                    on_click=SpaceWeatherDSState.fetch_noaa,
                    loading=SpaceWeatherDSState.noaa_running,
                    disabled=SpaceWeatherDSState.noaa_running,
                ),
                spacing="2",
                align="start",
                width="100%",
            ),
            rx.vstack(
                rx.text("Value column:", color=c["text_secondary"]),
                rx.select(
                    SpaceWeatherDSState.noaa_plot_columns,
                    value=SpaceWeatherDSState.noaa_plot_column,
                    on_change=SpaceWeatherDSState.set_noaa_plot_column,
                ),
                spacing="2",
                align="start",
                width="100%",
            ),
            spacing="6",
            align="start",
            width="100%",
            wrap="wrap",
        ),
        rx.cond(
            SpaceWeatherDSState.noaa_errors != [],
            rx.vstack(
                rx.foreach(
                    SpaceWeatherDSState.noaa_errors,
                    lambda e: rx.callout(
                        f"{e.get('key')}: {e.get('error')}",
                        icon="triangle_alert",
                        color_scheme="yellow",
                    ),
                ),
                spacing="2",
                width="100%",
            ),
            rx.text("", color=c["text_secondary"]),
        ),
        rx.cond(
            SpaceWeatherDSState.noaa_option != {},
            rx.box(
                echarts(option=SpaceWeatherDSState.noaa_option),
                width="100%",
                max_width="1100px",
                border=f"1px solid {c['border']}",
                border_radius="10px",
                padding="8px",
            ),
            rx.text("Fetch NOAA feeds to render a chart.", color=c["text_secondary"]),
        ),
        rx.divider(),
        rx.heading("6) Export", size="4", color=c["text_primary"]),
        rx.button("Export session metrics (CSV + JSON)", on_click=SpaceWeatherDSState.export_session_metrics),
        rx.cond(
            SpaceWeatherDSState.export_files != [],
            rx.vstack(
                rx.foreach(
                    SpaceWeatherDSState.export_files,
                    lambda f: rx.link(f.get("name", "export"), href=f.get("url", "#")),
                ),
                spacing="2",
                align="start",
            ),
            rx.text("No exports yet.", color=c["text_secondary"]),
        ),
        spacing="4",
        align="start",
        width="100%",
        max_width="1100px",
    )
    return app_shell(title="Space Weather Data Science (Single User)", body=body)

