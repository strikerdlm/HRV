from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import pandas as pd
import numpy as np


@dataclass(frozen=True)
class ColumnMap:
    id_col: str = "ID"
    event_col: str = "Event"
    start_col: str = "Start"
    end_col: str = "End"


def load_event_csv(file_like, columns: ColumnMap) -> pd.DataFrame:
    df = pd.read_csv(file_like)
    # Standardize column names
    required = {
        columns.id_col,
        columns.event_col,
        columns.start_col,
        columns.end_col,
    }
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in CSV: {missing}")
    df = df.rename(
        columns={
            columns.id_col: "ID",
            columns.event_col: "Event",
            columns.start_col: "Start",
            columns.end_col: "End",
        }
    )
    # Parse datetimes
    df["Start"] = pd.to_datetime(df["Start"], errors="coerce")
    df["End"] = pd.to_datetime(df["End"], errors="coerce")
    df = df.dropna(subset=["Start", "End"])  # keep valid rows only
    # Ensure ordering
    df = df.sort_values(["ID", "Start"]).reset_index(drop=True)
    return df


def _expand_events_to_minutes(events: pd.DataFrame) -> pd.DataFrame:
    # Build per-minute rows across observation range
    obs_start = events["Start"].min()
    obs_end = events["End"].max()
    minutes = pd.date_range(obs_start, obs_end, freq="1min")
    base = pd.DataFrame({"Obs_DateTime": minutes})
    return base


def build_epoch_tables(
    df: pd.DataFrame,
    subject_id: str,
    sleep_id: str = "Sleep",
    work_id: str = "Work",
    test_id: str = "Test",
    crewing_id: str = "Crewing",
    limit_days: int = 21,
) -> Dict[str, pd.DataFrame]:
    # Filter subject
    sub = df[df["ID"].astype(str) == str(subject_id)].copy()
    if sub.empty:
        raise ValueError("No rows for selected subject")

    obs_span_days = (sub["End"].max() - sub["Start"].min()).days + 1
    if obs_span_days > limit_days:
        raise ValueError(
            f"Observation period too long ({obs_span_days}d). "
            f"Must be <= {limit_days} days."
        )

    base = _expand_events_to_minutes(sub)
    base["ID"] = subject_id

    def vectorize_flag(event_label: str) -> pd.Series:
        rows = sub[sub["Event"] == event_label][["Start", "End"]]
        if rows.empty:
            return pd.Series(0, index=base.index)
        # Efficient interval marking
        ts = pd.Series(0, index=base.index)
        for _, r in rows.iterrows():
            start = max(r["Start"], base["Obs_DateTime"].iloc[0])
            end = min(r["End"], base["Obs_DateTime"].iloc[-1])
            if end <= start:
                continue
            mask = (
                (base["Obs_DateTime"] >= start)
                & (base["Obs_DateTime"] < end)
            )
            ts[mask] = 1
        return ts

    base["Sleep"] = vectorize_flag(sleep_id)
    base["Work"] = vectorize_flag(work_id)
    base["Test"] = vectorize_flag(test_id)
    base["Crewing"] = vectorize_flag(crewing_id)

    # Epoch and derived timing fields
    base["Epochs"] = np.arange(len(base))
    start0 = base["Obs_DateTime"].iloc[0]
    hour = (
        base["Obs_DateTime"].dt.hour
        + base["Obs_DateTime"].dt.minute / 60.0
    )
    days = (
        (base["Obs_DateTime"].dt.normalize() - start0.normalize()).dt.days
        + 1
    )
    base["Time"] = hour
    base["Days"] = days
    base["Fraction_Days"] = (days + hour / 24.0) - 1.0

    return {"Epoch_Table": base}


def derive_bedtime_hour(df: pd.DataFrame, sleep_id: str = "Sleep") -> float:
    # Use median hour of sleep Start times as bedtime
    starts = df.loc[df["Event"].astype(str) == str(sleep_id), "Start"].dt.hour
    if starts.empty:
        return 23.0
    return float(starts.median())


def schedule_from_epoch_table(
    epoch_table: pd.DataFrame,
) -> Tuple[Dict[int, bool], int]:
    # Convert per-minute Sleep to per-hour boolean map and total hours
    start = epoch_table["Obs_DateTime"].iloc[0]
    end = epoch_table["Obs_DateTime"].iloc[-1]
    total_hours = int(
        np.ceil((end - start).total_seconds() / 3600.0)
    )
    asleep_by_hour: Dict[int, bool] = {}

    # Aggregate by hour bins
    epoch_table = epoch_table.copy()
    epoch_table["HourIndex"] = (
        (epoch_table["Obs_DateTime"] - start).dt.total_seconds() // 3600
    ).astype(int)
    grouped = epoch_table.groupby("HourIndex")["Sleep"].mean()
    for h in range(total_hours):
        asleep_by_hour[h] = bool(grouped.get(h, 0.0) >= 0.5)
    return asleep_by_hour, total_hours
