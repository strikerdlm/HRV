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
    async def handle_rr_upload(self, files: list[Any]):
        """Save uploaded RR text files to the server upload dir.

        Note: do not store RR arrays in state (keeps UI fast on slow machines).
        """
        self.job_error = ""
        self.job_message = ""

        if not isinstance(files, list) or not files:
            self.job_error = "No files received. Select RR files, then click Upload."
            yield rx.toast.error("No files selected. Please select files first.")
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
        yield rx.toast.success(f"Successfully uploaded {len(saved)} file(s)!")

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

        # Count successful vs error rows
        success_count = sum(1 for r in rows if "error" not in r)
        error_count = len(rows) - success_count

        async with self:
            self.session_metrics = rows
            # Build default trend chart (rmssd) for quick feedback.
            try:
                self.hrv_trend_option = self._build_hrv_daily_chart_option(self.hrv_trend_metric)
            except Exception:
                self.hrv_trend_option = {}
            self.job_running = False
            self.job_message = f"Completed! {success_count} sessions processed successfully."

        # Yield toast notification
        if error_count > 0:
            yield rx.toast.warning(
                f"Analysis complete: {success_count} successful, {error_count} errors",
                duration=5000,
            )
        else:
            yield rx.toast.success(
                f"Analysis complete! {success_count} sessions processed successfully.",
                duration=5000,
            )

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

        # Toast notification
        if error_rows:
            yield rx.toast.warning(
                f"NOAA fetch complete with {len(error_rows)} warning(s)",
                duration=4000,
            )
        else:
            yield rx.toast.success("NOAA data fetched successfully!", duration=3000)

    @rx.event
    async def export_session_metrics(self):
        """Write CSV/JSON exports to the Reflex upload dir and expose links."""

        if not self.session_metrics:
            self.export_files = []
            yield rx.toast.warning("No data to export. Run analysis first.")
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
        yield rx.toast.success("Export complete! Click the file badges to download.")


def _metric_badge(label: str, value: Any, unit: str, color_scheme: str = "blue") -> rx.Component:
    """Create a visually appealing metric badge."""
    if isinstance(value, (int, float)):
        display_val = f"{value:.1f}" if isinstance(value, float) else str(value)
    else:
        display_val = "—"

    return rx.box(
        rx.vstack(
            rx.text(label, size="1", weight="medium", color=colors()["text_secondary"]),
            rx.hstack(
                rx.text(display_val, size="4", weight="bold", color=colors()["text_primary"]),
                rx.text(unit, size="2", color=colors()["text_secondary"]),
                spacing="1",
                align="baseline",
            ),
            spacing="1",
            align="center",
        ),
        background=f"var(--{color_scheme}-2)",
        padding="12px 16px",
        border_radius="8px",
        min_width="90px",
    )


def _reactive_metric_badge(label: str, value: Any, unit: str, color_scheme: str = "blue") -> rx.Component:
    """Create a visually appealing metric badge for reactive Var values."""
    c = colors()
    return rx.box(
        rx.vstack(
            rx.text(label, size="1", weight="medium", color=c["text_secondary"]),
            rx.hstack(
                rx.cond(
                    value.is_not_none(),
                    rx.text(value, size="4", weight="bold", color=c["text_primary"]),
                    rx.text("—", size="4", weight="bold", color=c["text_secondary"]),
                ),
                rx.text(unit, size="2", color=c["text_secondary"]),
                spacing="1",
                align="baseline",
            ),
            spacing="1",
            align="center",
        ),
        background=f"var(--{color_scheme}-2)",
        padding="12px 16px",
        border_radius="8px",
        min_width="90px",
    )


def _metrics_preview(rows: Any) -> rx.Component:
    c = colors()
    empty_view = rx.callout(
        "No results yet. Upload RR files and click 'Run HRV Analysis' to compute metrics.",
        icon="info",
        color_scheme="blue",
        size="2",
    )

    def _row_view(row: Any) -> rx.Component:
        name = row.get("session_name", "session")
        err = row.get("error", "")

        error_view = rx.callout(
            rx.text(name, ": ", err),
            icon="triangle_alert",
            color_scheme="red",
            size="2",
        )

        metrics_view = rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("activity", size=18, color=c["accent"]),
                    rx.heading(name, size="3", weight="bold", color=c["text_primary"]),
                    spacing="2",
                    align="center",
                ),
                rx.separator(size="4"),
                rx.hstack(
                    _reactive_metric_badge("RMSSD", row.get("rmssd"), "ms", "sky"),
                    _reactive_metric_badge("SDNN", row.get("sdnn"), "ms", "blue"),
                    _reactive_metric_badge("Mean HR", row.get("mean_hr"), "bpm", "green"),
                    _reactive_metric_badge("Artifacts", row.get("artifact_pct"), "%", "amber"),
                    wrap="wrap",
                    spacing="3",
                    justify="start",
                ),
                spacing="3",
                align="start",
                width="100%",
            ),
            size="2",
            variant="surface",
        )
        return rx.cond(err, error_view, metrics_view)

    rows_view = rx.vstack(rx.foreach(rows, _row_view), spacing="3", width="100%")
    if isinstance(rows, list):
        return rows_view if rows else empty_view
    return rx.cond(rows.length() > 0, rows_view, empty_view)


def _section_header(icon_name: str, title: str, subtitle: str = "") -> rx.Component:
    """Create a consistent section header with icon."""
    c = colors()
    return rx.vstack(
        rx.hstack(
            rx.icon(icon_name, size=24, color=c["accent"]),
            rx.heading(title, size="5", weight="bold", color=c["text_primary"]),
            spacing="2",
            align="center",
        ),
        rx.cond(
            subtitle != "",
            rx.text(subtitle, size="2", color=c["text_secondary"]),
            rx.fragment(),
        ),
        spacing="1",
        align="start",
        width="100%",
    )


def _status_panel() -> rx.Component:
    """Create a prominent status panel showing current job state."""
    c = colors()

    # Running state - show spinner and progress
    running_view = rx.card(
        rx.vstack(
            rx.hstack(
                rx.spinner(size="3"),
                rx.vstack(
                    rx.text("Processing...", size="3", weight="bold", color=c["text_primary"]),
                    rx.text(SpaceWeatherDSState.job_message, size="2", color=c["text_secondary"]),
                    spacing="1",
                    align="start",
                ),
                spacing="3",
                align="center",
            ),
            rx.progress(
                value=SpaceWeatherDSState.job_progress_pct,
                size="3",
                color_scheme="sky",
            ),
            rx.text(
                SpaceWeatherDSState.job_progress_pct.to_string() + "% complete",
                size="1",
                color=c["text_secondary"],
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
        size="2",
        variant="surface",
        style={"background": "var(--sky-2)", "border": "2px solid var(--sky-6)"},
    )

    # Error state - show error callout
    error_view = rx.callout(
        SpaceWeatherDSState.job_error,
        icon="triangle_alert",
        color_scheme="red",
        size="2",
        high_contrast=True,
    )

    # Idle state with message
    idle_with_message = rx.callout(
        SpaceWeatherDSState.job_message,
        icon="check",
        color_scheme="green",
        size="2",
    )

    # Default idle state
    idle_default = rx.callout(
        "Ready to process. Upload files and click 'Run HRV Analysis' to begin.",
        icon="info",
        color_scheme="blue",
        size="2",
    )

    return rx.cond(
        SpaceWeatherDSState.job_running,
        running_view,
        rx.cond(
            SpaceWeatherDSState.job_error != "",
            error_view,
            rx.cond(
                SpaceWeatherDSState.job_message != "",
                idle_with_message,
                idle_default,
            ),
        ),
    )


def space_weather_ds_page() -> rx.Component:
    c = colors()

    upload_id = "rr_upload"
    try:
        noaa_keys = get_noaa_source_keys()
    except Exception:
        noaa_keys = ["planetary_k_index_3h", "geospace_dst", "f107_flux"]

    # File count badge
    file_count_badge = rx.cond(
        SpaceWeatherDSState.rr_files.length() > 0,
        rx.badge(
            SpaceWeatherDSState.rr_files.length().to_string() + " files loaded",
            color_scheme="green",
            size="2",
            variant="soft",
        ),
        rx.badge("No files loaded", color_scheme="gray", size="2", variant="soft"),
    )

    # Upload Card
    upload_card = rx.card(
        rx.vstack(
            _section_header("upload", "Upload RR Files", "Upload your RR interval text files (.txt or .csv)"),
            rx.separator(size="4"),
            rx.upload(
                rx.vstack(
                    rx.icon("file_plus", size=48, color=c["accent"]),
                    rx.text(
                        "Click to upload or drag and drop",
                        size="3",
                        weight="medium",
                        color=c["text_primary"],
                    ),
                    rx.text(
                        "Supports TXT/CSV files (max 60 files)",
                        size="2",
                        color=c["text_secondary"],
                    ),
                    spacing="2",
                    align="center",
                    padding="24px",
                ),
                id=upload_id,
                accept={"text/plain": [".txt", ".csv"]},
                multiple=True,
                max_files=60,
                border=f"2px dashed {c['border']}",
                border_radius="12px",
                padding="0",
                _hover={"border_color": c["accent"], "background": "var(--sky-1)"},
            ),
            rx.hstack(
                rx.button(
                    rx.icon("upload", size=16),
                    "Upload Files",
                    size="3",
                    color_scheme="sky",
                    on_click=SpaceWeatherDSState.handle_rr_upload(
                        rx.upload_files(upload_id=upload_id),
                    ),
                ),
                rx.button(
                    rx.icon("trash_2", size=16),
                    "Clear All",
                    size="3",
                    variant="outline",
                    color_scheme="red",
                    on_click=SpaceWeatherDSState.clear_rr_files,
                ),
                file_count_badge,
                spacing="3",
                align="center",
                wrap="wrap",
            ),
            rx.text(rx.selected_files(upload_id), size="2", color=c["text_secondary"]),
            spacing="4",
            align="start",
            width="100%",
        ),
        size="3",
        variant="surface",
    )

    # Configuration Card
    config_card = rx.card(
        rx.vstack(
            _section_header("settings", "Configuration", "Adjust analysis parameters"),
            rx.separator(size="4"),
            rx.grid(
                rx.vstack(
                    rx.text("Performance Profile", size="2", weight="medium", color=c["text_primary"]),
                    rx.select(
                        ["Lightweight", "Balanced", "RTX 5070 GPU"],
                        value=SpaceWeatherDSState.performance_profile,
                        on_change=SpaceWeatherDSState.set_performance_profile,
                        size="3",
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("QC Method", size="2", weight="medium", color=c["text_primary"]),
                    rx.select(
                        ["threshold_median", "threshold_prev"],
                        value=SpaceWeatherDSState.qc_method,
                        on_change=SpaceWeatherDSState.set_qc_method,
                        size="3",
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text("Max Deviation", size="2", weight="medium", color=c["text_primary"]),
                        rx.badge(
                            SpaceWeatherDSState.qc_max_deviation.to_string(),
                            color_scheme="sky",
                            size="1",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    rx.slider(
                        min=0.05,
                        max=0.5,
                        step=0.05,
                        value=[SpaceWeatherDSState.qc_max_deviation],
                        on_change=SpaceWeatherDSState.set_qc_max_deviation,
                        size="2",
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Median Window", size="2", weight="medium", color=c["text_primary"]),
                    rx.input(
                        type_="number",
                        value=SpaceWeatherDSState.qc_median_window,
                        min=5,
                        max=31,
                        step=2,
                        on_change=SpaceWeatherDSState.set_qc_median_window,
                        size="3",
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
                columns="2",
                spacing="4",
                width="100%",
            ),
            rx.separator(size="4"),
            rx.button(
                rx.cond(
                    SpaceWeatherDSState.job_running,
                    rx.hstack(
                        rx.spinner(size="2"),
                        rx.text("Processing..."),
                        spacing="2",
                        align="center",
                    ),
                    rx.hstack(
                        rx.icon("play", size=18),
                        rx.text("Run HRV Analysis"),
                        spacing="2",
                        align="center",
                    ),
                ),
                size="4",
                color_scheme="green",
                variant="solid",
                on_click=SpaceWeatherDSState.run_hrv_analysis,
                disabled=SpaceWeatherDSState.job_running,
                style={"width": "100%", "font_weight": "600"},
            ),
            spacing="4",
            align="start",
            width="100%",
        ),
        size="3",
        variant="surface",
    )

    # Status Card
    status_card = rx.card(
        rx.vstack(
            _section_header("activity", "Status"),
            rx.separator(size="4"),
            _status_panel(),
            spacing="4",
            align="start",
            width="100%",
        ),
        size="3",
        variant="surface",
    )

    # Results Card
    results_card = rx.card(
        rx.vstack(
            _section_header("bar_chart_3", "Analysis Results", "HRV metrics computed from your RR data"),
            rx.separator(size="4"),
            _metrics_preview(SpaceWeatherDSState.session_metrics),
            spacing="4",
            align="start",
            width="100%",
        ),
        size="3",
        variant="surface",
    )

    # HRV Trend Chart Card
    trend_card = rx.card(
        rx.vstack(
            _section_header("trending_up", "Daily Trend Chart", "Visualize HRV metrics over time"),
            rx.separator(size="4"),
            rx.hstack(
                rx.vstack(
                    rx.text("Metric", size="2", weight="medium", color=c["text_primary"]),
                    rx.select(
                        ["rmssd", "sdnn", "mean_hr", "pnn50"],
                        value=SpaceWeatherDSState.hrv_trend_metric,
                        on_change=SpaceWeatherDSState.set_hrv_trend_metric,
                        size="3",
                    ),
                    spacing="2",
                    align="start",
                ),
                rx.button(
                    rx.icon("refresh_cw", size=16),
                    "Build Chart",
                    size="3",
                    variant="outline",
                    color_scheme="sky",
                    on_click=SpaceWeatherDSState.rebuild_hrv_trend_chart,
                ),
                spacing="4",
                align="end",
            ),
            rx.cond(
                SpaceWeatherDSState.hrv_trend_option != {},
                rx.box(
                    echarts(option=SpaceWeatherDSState.hrv_trend_option),
                    width="100%",
                    height="400px",
                    border_radius="8px",
                    overflow="hidden",
                ),
                rx.callout(
                    "Need ≥3 days of data to render a daily trend chart. Run analysis first.",
                    icon="info",
                    color_scheme="blue",
                    size="2",
                ),
            ),
            spacing="4",
            align="start",
            width="100%",
        ),
        size="3",
        variant="surface",
    )

    # NOAA Space Weather Card
    noaa_card = rx.card(
        rx.vstack(
            _section_header("sun", "NOAA Space Weather", "Fetch and visualize space weather data"),
            rx.separator(size="4"),
            rx.grid(
                rx.vstack(
                    rx.text("Dataset", size="2", weight="medium", color=c["text_primary"]),
                    rx.select(
                        noaa_keys,
                        value=SpaceWeatherDSState.noaa_plot_key,
                        on_change=SpaceWeatherDSState.set_noaa_plot_key,
                        size="3",
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("Value Column", size="2", weight="medium", color=c["text_primary"]),
                    rx.select(
                        SpaceWeatherDSState.noaa_plot_columns,
                        value=SpaceWeatherDSState.noaa_plot_column,
                        on_change=SpaceWeatherDSState.set_noaa_plot_column,
                        size="3",
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
                columns="2",
                spacing="4",
                width="100%",
            ),
            rx.button(
                rx.cond(
                    SpaceWeatherDSState.noaa_running,
                    rx.hstack(
                        rx.spinner(size="2"),
                        rx.text("Fetching..."),
                        spacing="2",
                        align="center",
                    ),
                    rx.hstack(
                        rx.icon("download", size=16),
                        rx.text("Fetch NOAA Data"),
                        spacing="2",
                        align="center",
                    ),
                ),
                size="3",
                color_scheme="amber",
                on_click=SpaceWeatherDSState.fetch_noaa,
                loading=SpaceWeatherDSState.noaa_running,
                disabled=SpaceWeatherDSState.noaa_running,
            ),
            rx.cond(
                SpaceWeatherDSState.noaa_errors.length() > 0,
                rx.vstack(
                    rx.foreach(
                        SpaceWeatherDSState.noaa_errors,
                        lambda e: rx.callout(
                            rx.text(e.get("key"), ": ", e.get("error")),
                            icon="triangle_alert",
                            color_scheme="amber",
                            size="2",
                        ),
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.fragment(),
            ),
            rx.cond(
                SpaceWeatherDSState.noaa_option != {},
                rx.box(
                    echarts(option=SpaceWeatherDSState.noaa_option),
                    width="100%",
                    height="400px",
                    border_radius="8px",
                    overflow="hidden",
                ),
                rx.callout(
                    "Click 'Fetch NOAA Data' to load space weather data.",
                    icon="info",
                    color_scheme="blue",
                    size="2",
                ),
            ),
            spacing="4",
            align="start",
            width="100%",
        ),
        size="3",
        variant="surface",
    )

    # Export Card
    export_card = rx.card(
        rx.vstack(
            _section_header("download", "Export Data", "Download your analysis results"),
            rx.separator(size="4"),
            rx.hstack(
                rx.button(
                    rx.icon("file_spreadsheet", size=16),
                    "Export CSV & JSON",
                    size="3",
                    color_scheme="violet",
                    on_click=SpaceWeatherDSState.export_session_metrics,
                ),
                rx.cond(
                    SpaceWeatherDSState.export_files.length() > 0,
                    rx.hstack(
                        rx.foreach(
                            SpaceWeatherDSState.export_files,
                            lambda f: rx.link(
                                rx.badge(
                                    rx.icon("file_down", size=12),
                                    f.get("name", "export"),
                                    color_scheme="green",
                                    size="2",
                                    variant="soft",
                                ),
                                href=f.get("url", "#"),
                            ),
                        ),
                        spacing="2",
                    ),
                    rx.text("Export will appear here", size="2", color=c["text_secondary"]),
                ),
                spacing="4",
                align="center",
                wrap="wrap",
            ),
            spacing="4",
            align="start",
            width="100%",
        ),
        size="3",
        variant="surface",
    )

    body = rx.vstack(
        # Page header
        rx.hstack(
            rx.vstack(
                rx.heading(
                    "Space Weather Data Science",
                    size="7",
                    weight="bold",
                    color=c["text_primary"],
                ),
                rx.text(
                    "Analyze HRV data and correlate with space weather conditions",
                    size="3",
                    color=c["text_secondary"],
                ),
                spacing="1",
                align="start",
            ),
            rx.badge(
                "Phase 1 MVP",
                color_scheme="sky",
                size="2",
                variant="surface",
            ),
            justify="between",
            align="start",
            width="100%",
            wrap="wrap",
        ),
        rx.separator(size="4"),
        # Main content grid
        rx.grid(
            upload_card,
            config_card,
            columns="2",
            spacing="4",
            width="100%",
        ),
        status_card,
        results_card,
        trend_card,
        noaa_card,
        export_card,
        spacing="4",
        align="start",
        width="100%",
        max_width="1200px",
        padding="4",
    )
    return app_shell(title="Space Weather DS", body=body)

