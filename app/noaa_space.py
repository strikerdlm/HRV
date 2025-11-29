from __future__ import annotations

import io
import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple, List

import numpy as np
import pandas as pd
import requests
import re
from pandas.api.types import is_datetime64_any_dtype

SWPC_BASE_URL = "https://services.swpc.noaa.gov/json/"
REQUEST_TIMEOUT = 10.0
CACHE_TTL = pd.Timedelta(hours=6)
NOAA_SPACE_CACHE_DIR = Path(__file__).resolve().parent / "data_cache" / "noaa_space"


@dataclass(frozen=True, slots=True)
class NOAASourceSpec:
    """
    Metadata describing a NOAA JSON feed used on the NOAA Space tab.

    Attributes
    ----------
    key :
        Unique identifier for the source (used for caching and lookups).
    path :
        Relative path under the SWPC base URL or an absolute URL for the feed.
    title :
        Human-readable title for display in the dashboard.
    description :
        Short explanation of the physical quantity represented by this feed.
    value_columns :
        Columns containing the primary numeric values to visualise.
    preferred_time_columns :
        Ordered list of candidate columns containing timestamp data.
    metadata_columns :
        Ancillary columns (categorical or numeric) to retain in the cleaned frame.
    explode_column :
        Optional column containing nested records to be flattened row-wise.
    flatten_rename :
        Optional column rename mapping applied after flattening nested data.
    units :
        Mapping from column name to unit string (e.g., {"flux": "sfu"}).
    cadence_minutes :
        Sampling cadence in minutes, if known. Used for labelling only.
    split_by_column :
        Optional categorical column used to pivot a single value column into
        multiple metric columns (e.g., proton flux per energy threshold).
    """

    key: str
    path: str
    title: str
    description: str
    value_columns: Sequence[str]
    preferred_time_columns: Sequence[str] = ("time_tag", "time_tag_full", "time", "timestamp")
    metadata_columns: Sequence[str] = ()
    explode_column: Optional[str] = None
    flatten_rename: Optional[Mapping[str, str]] = None
    units: Optional[Mapping[str, str]] = None
    cadence_minutes: Optional[int] = None
    split_by_column: Optional[str] = None


@dataclass(frozen=True, slots=True)
class NOAADataBundle:
    """
    Harmonised NOAA dataset ready for visualisation and correlation.

    Attributes
    ----------
    spec :
        The source specification used to fetch and process the dataset.
    frame :
        Cleaned pandas DataFrame sorted by ascending timestamp.
    time_column :
        Name of the column that contains timezone-aware UTC timestamps.
    value_columns :
        Tuple of numeric columns available for plotting and correlation.
    units :
        Mapping from each value column to its unit label (empty if unknown).
    split_labels :
        Optional mapping from pivoted column name to a human-readable label.
    """

    spec: NOAASourceSpec
    frame: pd.DataFrame
    time_column: str
    value_columns: Tuple[str, ...]
    units: Mapping[str, str]
    split_labels: Mapping[str, str] = field(default_factory=dict)


NOAA_SOURCES: Dict[str, NOAASourceSpec] = {
    "f107_flux": NOAASourceSpec(
        key="f107_flux",
        path="f107_cm_flux.json",
        title="F10.7 cm flux",
        description="NOAA SWPC 2.8 GHz solar radio flux (three daily slots).",
        value_columns=("flux", "ninety_day_mean"),
        metadata_columns=("frequency", "reporting_schedule"),
        units={"flux": "sfu", "ninety_day_mean": "sfu"},
        cadence_minutes=180,
    ),
    "solar_radio_multifrequency": NOAASourceSpec(
        key="solar_radio_multifrequency",
        path="solar-radio-flux.json",
        title="RSTE solar radio flux",
        description="Solar Radio Telescope Network flux across discrete frequencies.",
        value_columns=("frequency_mhz", "flux_sfu"),
        metadata_columns=("common_name",),
        explode_column="details",
        flatten_rename={
            "frequency": "frequency_mhz",
            "flux": "flux_sfu",
            "observed_quality": "quality_flag",
        },
        units={"flux_sfu": "sfu", "frequency_mhz": "MHz"},
        cadence_minutes=60,
    ),
    "planetary_k_index_1m": NOAASourceSpec(
        key="planetary_k_index_1m",
        path="planetary_k_index_1m.json",
        title="Planetary K index (1m)",
        description="Planetary K planetary geomagnetic index at one-minute cadence.",
        value_columns=("kp_index", "estimated_kp"),
        metadata_columns=("kp",),
        units={"kp_index": "Kp", "estimated_kp": "Kp"},
        cadence_minutes=1,
    ),
    "solar_wind_wind": NOAASourceSpec(
        key="solar_wind_wind",
        path="rtsw/rtsw_wind_1m.json",
        title="Solar wind (ACE/DSCOVR)",
        description="Real-time solar wind proton speed, density, and temperature.",
        value_columns=("proton_speed", "proton_density", "proton_temperature"),
        metadata_columns=("source", "overall_quality"),
        units={
            "proton_speed": "km/s",
            "proton_density": "1/cm³",
            "proton_temperature": "K",
        },
        cadence_minutes=1,
    ),
    "solar_wind_mag": NOAASourceSpec(
        key="solar_wind_mag",
        path="rtsw/rtsw_mag_1m.json",
        title="Interplanetary magnetic field",
        description="Magnetic field magnitude and vector components from ACE/DSCOVR.",
        value_columns=("bt", "bz_gse", "bz_gsm"),
        metadata_columns=("source", "overall_quality"),
        units={"bt": "nT", "bz_gse": "nT", "bz_gsm": "nT"},
        cadence_minutes=1,
    ),
    "goes_xray_flux": NOAASourceSpec(
        key="goes_xray_flux",
        path="goes/primary/xrays-1-day.json",
        title="GOES x-ray flux",
        description="GOES primary x-ray flux (0.05–0.4 nm band).",
        value_columns=("observed_flux", "flux"),
        metadata_columns=("satellite", "energy"),
        units={"observed_flux": "W/m²", "flux": "W/m²"},
        cadence_minutes=1,
    ),
    "goes_integral_protons": NOAASourceSpec(
        key="goes_integral_protons",
        path="goes/primary/integral-protons-1-day.json",
        title="GOES integral proton flux",
        description="GOES primary integral proton flux (≥1–≥500 MeV thresholds, 5-minute averages).",
        value_columns=("flux",),
        metadata_columns=("satellite", "energy"),
        units={"flux": "pfu"},
        cadence_minutes=5,
        split_by_column="energy",
    ),
    "geospace_pred_kp": NOAASourceSpec(
        key="geospace_pred_kp",
        path="geospace/geospace_pred_est_kp_1_hour.json",
        title="Predicted Kp (1 h model)",
        description="Short-term model forecast of planetary K index (1-hour cadence).",
        value_columns=("k",),
        preferred_time_columns=("model_prediction_time", "time_tag", "time"),
        units={"k": "Kp"},
        cadence_minutes=60,
    ),
    "geospace_dst": NOAASourceSpec(
        key="geospace_dst",
        path="geospace/geospace_dst_1_hour.json",
        title="Geomagnetic Dst (1 h)",
        description="Geomagnetic disturbance storm-time (Dst) index derived from low-latitude magnetometers.",
        value_columns=("dst",),
        units={"dst": "nT"},
        cadence_minutes=60,
    ),
    "geospace_dst_7d": NOAASourceSpec(
        key="geospace_dst_7d",
        path="geospace/geospace_dst_7_day.json",
        title="Geomagnetic Dst (7 d)",
        description="Seven-day history/forecast of the Dst index.",
        value_columns=("dst",),
        units={"dst": "nT"},
        cadence_minutes=60,
    ),
    "boulder_k_1m": NOAASourceSpec(
        key="boulder_k_1m",
        path="boulder_k_index_1m.json",
        title="Boulder K index (1 min)",
        description="Local geomagnetic K index recorded at Boulder, Colorado (1-minute cadence).",
        value_columns=("k_index",),
        units={"k_index": "K"},
        cadence_minutes=1,
    ),
    "sunspots_monthly": NOAASourceSpec(
        key="sunspots_monthly",
        path="solar-cycle/sunspots.json",
        title="Sunspot number (monthly)",
        description="Observed monthly sunspot numbers across the historical record.",
        value_columns=("ssn",),
        preferred_time_columns=("time-tag", "time_tag"),
        units={"ssn": "sunspot number"},
        cadence_minutes=43200,
    ),
    "f107_smoothed": NOAASourceSpec(
        key="f107_smoothed",
        path="solar-cycle/f10-7cm-flux-smoothed.json",
        title="F10.7 cm flux (monthly)",
        description="Monthly 10.7 cm solar radio flux with smoothed series.",
        value_columns=("f10.7", "smoothed_f10.7"),
        preferred_time_columns=("time-tag", "time_tag"),
        units={"f10.7": "sfu", "smoothed_f10.7": "sfu"},
        cadence_minutes=43200,
    ),
    "predicted_f107": NOAASourceSpec(
        key="predicted_f107",
        path="predicted_f107cm_flux.json",
        title="Predicted F10.7 flux",
        description="Three-day NOAA forecast of the 10.7 cm solar radio flux.",
        value_columns=("tencmfcst_1_day", "tencmfcst_2_day", "tencmfcst_3_day"),
        preferred_time_columns=("date", "time-tag", "time_tag"),
        units={
            "tencmfcst_1_day": "sfu",
            "tencmfcst_2_day": "sfu",
            "tencmfcst_3_day": "sfu",
        },
        cadence_minutes=1440,
    ),
    "predicted_fredericksburg": NOAASourceSpec(
        key="predicted_fredericksburg",
        path="predicted_fredericksburg_a_index.json",
        title="Predicted Fredericksburg a-index",
        description="Three-day NOAA forecast of the Fredericksburg a-index (geomagnetic activity).",
        value_columns=("afred_1_day", "afred_2_day", "afred_3_day"),
        preferred_time_columns=("date", "time-tag", "time_tag"),
        units={
            "afred_1_day": "a-index",
            "afred_2_day": "a-index",
            "afred_3_day": "a-index",
        },
        cadence_minutes=1440,
    ),
    "predicted_monthly_ssn": NOAASourceSpec(
        key="predicted_monthly_ssn",
        path="predicted_monthly_sunspot_number.json",
        title="Predicted monthly sunspot & flux",
        description="Monthly prediction of sunspot number and 10.7 cm flux (central/high/low).",
        value_columns=(
            "ssn_predicted",
            "ssn_high",
            "ssn_low",
            "flux_predicted",
            "flux_high",
            "flux_low",
        ),
        preferred_time_columns=("date", "time-tag", "time_tag"),
        units={
            "ssn_predicted": "sunspot number",
            "ssn_high": "sunspot number",
            "ssn_low": "sunspot number",
            "flux_predicted": "sfu",
            "flux_high": "sfu",
            "flux_low": "sfu",
        },
        cadence_minutes=43200,
    ),
    "solar_probabilities": NOAASourceSpec(
        key="solar_probabilities",
        path="solar_probabilities.json",
        title="Solar flare & proton probabilities",
        description="Probabilistic NOAA forecast of flare classes and proton events (1–3 day outlook).",
        value_columns=(
            "c_class_1_day",
            "c_class_2_day",
            "c_class_3_day",
            "m_class_1_day",
            "m_class_2_day",
            "m_class_3_day",
            "x_class_1_day",
            "x_class_2_day",
            "x_class_3_day",
            "10mev_protons_1_day",
            "10mev_protons_2_day",
            "10mev_protons_3_day",
        ),
        metadata_columns=("polar_cap_absorption",),
        units={col: "%" for col in (
            "c_class_1_day",
            "c_class_2_day",
            "c_class_3_day",
            "m_class_1_day",
            "m_class_2_day",
            "m_class_3_day",
            "x_class_1_day",
            "x_class_2_day",
            "x_class_3_day",
            "10mev_protons_1_day",
            "10mev_protons_2_day",
            "10mev_protons_3_day",
        )},
        cadence_minutes=1440,
    ),
}

_NEGATIVE_TO_NAN: Dict[Tuple[str, str], float] = {
    ("f107_smoothed", "smoothed_f10.7"): 0.0,
}


def _ensure_cache_dir() -> None:
    NOAA_SPACE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(spec: NOAASourceSpec) -> Path:
    return NOAA_SPACE_CACHE_DIR / f"{spec.key}.json"


def _read_cache(spec: NOAASourceSpec) -> Optional[pd.DataFrame]:
    cache_file = _cache_path(spec)
    if not cache_file.exists():
        return None
    try:
        with cache_file.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("stored_kind") != "raw":
        return None
    stored_at_raw = payload.get("stored_at")
    stored_at = pd.to_datetime(stored_at_raw, utc=True, errors="coerce")
    if pd.isna(stored_at) or stored_at + CACHE_TTL < pd.Timestamp.now(tz="UTC"):
        return None
    data_json = payload.get("data")
    if not isinstance(data_json, str):
        return None
    try:
        df = pd.read_json(io.StringIO(data_json), orient="table", convert_dates=True)
    except ValueError:
        return None
    return df


def _write_cache(spec: NOAASourceSpec, df: pd.DataFrame) -> None:
    payload = {
        "stored_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "stored_kind": "raw",
        "data": df.to_json(orient="table", date_format="iso"),
    }
    try:
        _ensure_cache_dir()
        with _cache_path(spec).open("w", encoding="utf-8") as handle:
            json.dump(payload, handle)
    except OSError as exc:  # pragma: no cover - defensive
        logging.getLogger("hrv_app").warning(
            "Failed to write NOAA cache %s: %s", spec.key, exc, exc_info=True
        )


def _download_dataset(spec: NOAASourceSpec) -> pd.DataFrame:
    path = spec.path
    url = path if path.startswith("http") else f"{SWPC_BASE_URL}{path}"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    records: Sequence[Any]
    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict):
            records = payload
        elif payload and isinstance(payload[0], list):
            header = payload[0]
            rows = payload[1:]
            df = pd.DataFrame(rows, columns=header)
            return df
        else:
            records = payload
    elif isinstance(payload, dict):
        data_block = payload.get("data") or payload.get("series") or payload.get("observations")
        if data_block is None:
            records = [payload]
        elif isinstance(data_block, Iterable):
            records = list(data_block)  # type: ignore[arg-type]
        else:
            records = [data_block]
    else:
        records = []
    return pd.json_normalize(records)


def _detect_time_column(df: pd.DataFrame, candidates: Sequence[str]) -> str:
    for column in candidates:
        if column in df.columns:
            return column
    for column in df.columns:
        if is_datetime64_any_dtype(df[column]):
            return column
    raise ValueError("No timestamp column detected in NOAA dataset.")


def _flatten_nested_column(df: pd.DataFrame, column: str, rename_map: Optional[Mapping[str, str]]) -> pd.DataFrame:
    working = df.copy()
    if column not in working.columns:
        return working.drop(columns=[column], errors="ignore")
    mask = working[column].apply(
        lambda value: isinstance(value, Iterable) and not isinstance(value, (str, bytes))
    )
    filtered = working.loc[mask].copy()
    if filtered.empty:
        return working.drop(columns=[column], errors="ignore")
    filtered = filtered.explode(column, ignore_index=True)
    nested = pd.json_normalize(filtered[column])
    nested = nested.rename(columns=rename_map or {})
    filtered = filtered.drop(columns=[column]).reset_index(drop=True)
    combined = pd.concat([filtered, nested], axis=1)
    return combined


def _prepare_frame(spec: NOAASourceSpec, raw_df: pd.DataFrame) -> NOAADataBundle:
    split_labels: Dict[str, str] = {}
    if raw_df.empty:
        empty_df = pd.DataFrame(columns=["time_tag"])
        return NOAADataBundle(
            spec=spec,
            frame=empty_df,
            time_column="time_tag",
            value_columns=tuple(spec.value_columns),
            units=spec.units or {},
            split_labels={},
        )
    df = raw_df.copy()
    if spec.explode_column:
        df = _flatten_nested_column(df, spec.explode_column, spec.flatten_rename)
    for column in df.columns:
        if df[column].dtype == object:
            lower = column.lower()
            if any(token in lower for token in ("time", "date", "tag")):
                df[column] = pd.to_datetime(df[column], errors="coerce", utc=True)
    time_column = _detect_time_column(df, spec.preferred_time_columns)
    df[time_column] = pd.to_datetime(df[time_column], errors="coerce", utc=True)
    df = df.dropna(subset=[time_column])
    df = df.sort_values(time_column)
    selected_columns = list(dict.fromkeys([time_column, *spec.metadata_columns, *spec.value_columns]))
    existing_columns = [col for col in selected_columns if col in df.columns]
    df = df[existing_columns].copy()
    numeric_columns = [col for col in spec.value_columns if col in df.columns]
    unit_mapping: Dict[str, str] = dict(spec.units or {})
    split_column = spec.split_by_column
    if split_column and numeric_columns:
        base_value = numeric_columns[0]
        if split_column in df.columns:
            subset = df[[time_column, split_column, base_value]].dropna(subset=[time_column, split_column])
            if not subset.empty:
                pivot = (
                    subset.pivot_table(
                        index=time_column,
                        columns=split_column,
                        values=base_value,
                        aggfunc="mean",
                    )
                    .sort_index()
                    .dropna(how="all", axis=1)
                )
                if not pivot.empty:
                    sanitized_columns: Dict[str, str] = {}
                    new_columns: list[str] = []
                    unit_value = spec.units.get(base_value) if spec.units else None
                    for cat in pivot.columns:
                        label = str(cat).strip()
                        sanitized = _sanitize_split_value(label)
                        col_name = f"{base_value}_{sanitized}" if sanitized else f"{base_value}_category"
                        if col_name in new_columns:
                            suffix = 1
                            candidate = f"{col_name}_{suffix}"
                            while candidate in new_columns:
                                suffix += 1
                                candidate = f"{col_name}_{suffix}"
                            col_name = candidate
                        new_columns.append(col_name)
                        split_labels[col_name] = label
                        if unit_value:
                            unit_mapping[col_name] = unit_value
                    pivot.columns = new_columns
                    df = pivot.reset_index().rename(columns={"index": time_column})
                    numeric_columns = new_columns
                    return NOAADataBundle(
                        spec=spec,
                        frame=df.reset_index(drop=True),
                        time_column=time_column,
                        value_columns=tuple(numeric_columns),
                        units=unit_mapping,
                        split_labels=split_labels,
                    )
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")
        sentinel_threshold = _NEGATIVE_TO_NAN.get((spec.key, column))
        if sentinel_threshold is not None:
            df[column] = df[column].mask(df[column] < sentinel_threshold)
    return NOAADataBundle(
        spec=spec,
        frame=df.reset_index(drop=True),
        time_column=time_column,
        value_columns=tuple(numeric_columns),
        units=unit_mapping,
        split_labels=split_labels,
    )


def fetch_noaa_source(spec: NOAASourceSpec, *, use_cache: bool = True) -> NOAADataBundle:
    """
    Fetch and cache a NOAA feed according to the provided specification.

    Parameters
    ----------
    spec :
        Data source specification.
    use_cache :
        When True, attempt to load from the local cache before performing a network request.

    Returns
    -------
    NOAADataBundle
        Harmonised dataset ready for visualisation.

    Raises
    ------
    requests.RequestException
        If the HTTP request fails.
    ValueError
        If the dataset lacks a detectable timestamp column.
    """

    if use_cache:
        cached = _read_cache(spec)
        if cached is not None:
            return _prepare_frame(spec, cached)
    raw_df = _download_dataset(spec)
    bundle = _prepare_frame(spec, raw_df)
    _write_cache(spec, raw_df)
    return bundle


def load_noaa_space_data(
    keys: Optional[Sequence[str]] = None,
    *,
    use_cache: bool = True,
) -> Tuple[Dict[str, NOAADataBundle], Dict[str, str]]:
    """
    Load one or more NOAA datasets defined in :data:`NOAA_SOURCES`.

    Parameters
    ----------
    keys :
        Optional iterable of source identifiers to load. When omitted, every configured source is fetched.
    use_cache :
        Toggle cache usage. Setting this to False forces a fresh download.

    Returns
    -------
    Tuple[Dict[str, NOAADataBundle], Dict[str, str]]
        Mapping of key → data bundle and a mapping of key → error message for failed downloads.
    """

    selected_keys = list(keys) if keys is not None else list(NOAA_SOURCES.keys())
    bundles: Dict[str, NOAADataBundle] = {}
    errors: Dict[str, str] = {}
    for key in selected_keys:
        spec = NOAA_SOURCES.get(key)
        if spec is None:
            errors[key] = "Unknown NOAA dataset key."
            continue
        try:
            bundles[key] = fetch_noaa_source(spec, use_cache=use_cache)
        except (requests.RequestException, ValueError) as exc:
            errors[key] = str(exc)
    return bundles, errors


def _sanitize_split_value(text: str) -> str:
    """
    Sanitize a categorical label for use as a DataFrame column suffix.
    """

    base = text.strip().lower()
    replacements = {
        ">=": "ge_",
        "<=": "le_",
        ">": "gt_",
        "<": "lt_",
        "±": "_pm_",
        "%": "_pct",
        "/": "_",
    }
    for key, value in replacements.items():
        base = base.replace(key, value)
    base = re.sub(r"[^0-9a-zA-Z_]+", "_", base)
    base = re.sub(r"_+", "_", base).strip("_")
    return base or "category"


# --- Human-readable explanations and likely HRV effects (concise) ---

_NOAA_METRIC_EXPLANATIONS: Dict[Tuple[str, str], Dict[str, str]] = {
    # Geomagnetic activity
    ("planetary_k_index_1m", "kp_index"): {
        "title": "Planetary K index (Kp)",
        "what": "Global 0–9 index of geomagnetic disturbance strength from ground magnetometers.",
        "why": "Higher Kp indicates stronger storms driven by solar-wind coupling (often with southward IMF Bz).",
        "physiology": "Studies associate higher geomagnetic activity with small reductions in HRV (lower SDNN/RMSSD, HF) and higher cardiovascular risk in populations.",
        "likely_effect": "Most probable HRV correlation: negative (higher Kp → lower vagal/total HRV), with lags from 0 to ~72 h.",
        "refs": "Vieira 2022; Gaisenok 2025; McCraty 2017; Papailiou 2023.",
    },
    ("planetary_k_index_1m", "estimated_kp"): {
        "title": "Estimated Kp (nowcast)",
        "what": "Near-real-time estimate of Kp prior to final processing.",
        "why": "Operational nowcast of geomagnetic variability.",
        "physiology": "As for Kp.",
        "likely_effect": "Negative correlation with vagal/total HRV is most probable.",
        "refs": "As Kp.",
    },
    ("boulder_k_1m", "k_index"): {
        "title": "Boulder K index",
        "what": "Local geomagnetic K index recorded at Boulder, Colorado (0–9 scale).",
        "why": "Highlights local disturbances that may differ from global Kp.",
        "physiology": "Spatial variations of geomagnetic activity can modulate local HRV responses similarly to Kp.",
        "likely_effect": "Most probable HRV correlation: negative (higher local K → lower HRV).",
        "refs": "Vieira 2022; Papailiou 2023.",
    },
    ("geospace_dst", "dst"): {
        "title": "Dst (storm-time disturbance)",
        "what": "Hourly nT index of ring current; more negative values indicate stronger geomagnetic storms.",
        "why": "Captures global storm intensity driven by magnetospheric currents.",
        "physiology": "Storm periods linked to HRV decreases and cardiovascular events in population data.",
        "likely_effect": "Most probable HRV correlation: positive with |Dst| (more negative Dst → lower HRV).",
        "refs": "Vieira 2022; Gaisenok 2025.",
    },
    ("geospace_dst_7d", "dst"): {
        "title": "Dst (7-day)",
        "what": "Seven-day history/forecast of the Dst geomagnetic storm index.",
        "why": "Shows storm evolution and near-term expectations.",
        "physiology": "Same implications as hourly Dst; track multi-day storm phases versus HRV recovery.",
        "likely_effect": "More negative Dst intervals likely align with lower HRV.",
        "refs": "Vieira 2022; Gaisenok 2025.",
    },
    # Solar wind / IMF
    ("solar_wind_wind", "proton_speed"): {
        "title": "Solar-wind speed",
        "what": "Flow speed of the solar wind near Earth (km/s).",
        "why": "Higher speeds increase energy input to the magnetosphere and storm potential.",
        "physiology": "Higher speed associated with increased heart rate and HRV changes consistent with stress responses.",
        "likely_effect": "Most probable HRV correlation: negative (higher speed → lower HRV) with short lags (0–72 h).",
        "refs": "Alabdulgader 2018; Vencloviene 2020.",
    },
    ("solar_wind_wind", "proton_density"): {
        "title": "Solar-wind proton density",
        "what": "Particle number density (1/cm³).",
        "why": "Contributes to dynamic pressure; can precede sudden impulses and substorms.",
        "physiology": "Less consistent alone; consider with speed/IMF and Kp/Dst.",
        "likely_effect": "Possible negative HRV correlation when coincident with other drivers.",
        "refs": "Vencloviene 2020 (pressure).",
    },
    ("solar_wind_mag", "bt"): {
        "title": "IMF total field (Bt)",
        "what": "Magnitude (nT) of the interplanetary magnetic field.",
        "why": "Stronger Bt with southward Bz increases coupling and storm strength.",
        "physiology": "Context for Kp/Dst; not a direct HRV driver by itself.",
        "likely_effect": "Indirect; effects mediated via geomagnetic activity indices.",
        "refs": "Space weather coupling context.",
    },
    ("solar_wind_mag", "bz_gse"): {
        "title": "IMF Bz (GSE)",
        "what": "North–south IMF component; Bz < 0 (southward) favors strong coupling.",
        "why": "Southward Bz is a key trigger for storms.",
        "physiology": "Indirect driver; HRV effects via subsequent geomagnetic activity.",
        "likely_effect": "Negative HRV correlation when Bz is sustained southward and followed by elevated Kp/Dst.",
        "refs": "Space weather coupling context.",
    },
    # Solar radio / flares / protons
    ("f107_flux", "flux"): {
        "title": "F10.7 cm flux",
        "what": "Solar 2.8 GHz radio flux (sfu), a proxy for EUV output and solar activity.",
        "why": "Higher F10.7 indicates more active Sun / ionospheric changes.",
        "physiology": "Reports vary; some show small increases in HRV/parasympathetic indices with higher background activity.",
        "likely_effect": "Small positive HRV correlation is plausible (context‑dependent).",
        "refs": "Alabdulgader 2018.",
    },
    ("f107_smoothed", "f10.7"): {
        "title": "F10.7 flux (monthly)",
        "what": "Monthly mean 10.7 cm solar radio flux.",
        "why": "Background solar cycle driver for ionospheric conditions.",
        "physiology": "Slow changes may track shifts in HRV baseline via solar-cycle modulation.",
        "likely_effect": "Small positive HRV correlation plausible; interpret with long-term context.",
        "refs": "Alabdulgader 2018.",
    },
    ("f107_smoothed", "smoothed_f10.7"): {
        "title": "F10.7 smoothed flux",
        "what": "Smoothed monthly 10.7 cm solar flux highlighting solar-cycle trend.",
        "why": "Provides cleaner solar-cycle signal for long-term analysis.",
        "physiology": "As above; use for trend-level analyses alongside HRV baselines.",
        "likely_effect": "Small positive HRV correlation plausible.",
        "refs": "Alabdulgader 2018.",
    },
    ("goes_integral_protons", "flux"): {
        "title": "GOES integral proton flux",
        "what": "Particle flux above energy thresholds; used to define radiation storms (S‑scale).",
        "why": "Often accompanies CME‑driven storms impacting geomagnetic activity.",
        "physiology": "Ground‑level HRV links are uncertain; treat as context with Kp/Dst and solar‑wind changes.",
        "likely_effect": "Indirect; monitor alongside geomagnetic indices.",
        "refs": "Operational/aviation context.",
    },
    ("goes_xray_flux", "observed_flux"): {
        "title": "GOES x‑ray flux",
        "what": "Soft x‑ray irradiance (0.05–0.4/0.1–0.8 nm) used for flare classification.",
        "why": "Flares indicate active regions; not all cause storms without CME/IMF coupling.",
        "physiology": "Direct HRV effects not established; use as solar context.",
        "likely_effect": "Indirect via subsequent solar‑wind/geomagnetic changes.",
        "refs": "Operational flare context.",
    },
    ("geospace_pred_kp", "k"): {
        "title": "Predicted Kp (model)",
        "what": "Short‑term model forecast of Kp at 1‑hour cadence.",
        "why": "Provides anticipation for geomagnetic variability.",
        "physiology": "As for Kp; enables pre‑registration of analysis windows.",
        "likely_effect": "Expected negative HRV correlation if predictions verify.",
        "refs": "As Kp.",
    },
    ("predicted_f107", "tencmfcst_1_day"): {
        "title": "F10.7 forecast (1 day)",
        "what": "NOAA 1-day forecast of the 10.7 cm solar radio flux.",
        "why": "Anticipates short-term solar EUV output changes.",
        "physiology": "Use alongside Kp/Dst forecasts for expected HRV shifts.",
        "likely_effect": "Small positive HRV correlation expected if values rise (contextual).",
        "refs": "Operational forecast context.",
    },
    ("predicted_fredericksburg", "afred_1_day"): {
        "title": "Fredericksburg a-index forecast (1 day)",
        "what": "NOAA 1-day forecast of the Fredericksburg geomagnetic a-index.",
        "why": "Higher a-index reflects stronger geomagnetic agitation at mid-latitudes.",
        "physiology": "Similar to Kp/Dst, elevated forecasts may precede HRV reductions if storms occur.",
        "likely_effect": "Most probable HRV correlation: negative (higher forecasted a-index → lower HRV).",
        "refs": "Gaisenok 2025; Vencloviene 2020.",
    },
    ("predicted_monthly_ssn", "ssn_predicted"): {
        "title": "Predicted sunspot number (monthly)",
        "what": "NOAA prediction of monthly international sunspot number.",
        "why": "Tracks expected solar-cycle strength and background solar activity.",
        "physiology": "Long-term shifts in solar activity may modulate HRV baselines via geomagnetic coupling.",
        "likely_effect": "Slow positive HRV correlation plausible with higher sunspot forecasts.",
        "refs": "Alabdulgader 2018; McCraty 2017.",
    },
    ("predicted_monthly_ssn", "flux_predicted"): {
        "title": "Predicted 10.7 cm flux (monthly)",
        "what": "Forecast of monthly 10.7 cm solar radio flux.",
        "why": "Indicates expected EUV output for ionospheric state changes.",
        "physiology": "Use for trend context alongside observed F10.7 and HRV baselines.",
        "likely_effect": "Small positive HRV correlation plausible.",
        "refs": "Alabdulgader 2018.",
    },
    ("sunspots_monthly", "ssn"): {
        "title": "Sunspot number",
        "what": "Observed monthly international sunspot number (dimensionless).",
        "why": "Proxy for solar magnetic activity and solar-cycle phase.",
        "physiology": "Solar-cycle background may modulate baseline HRV over long periods (via F10.7, cosmic rays).",
        "likely_effect": "Slow positive HRV correlation plausible with higher sunspot activity (contextual).",
        "refs": "Alabdulgader 2018; McCraty 2017.",
    },
}

for column in ("tencmfcst_1_day", "tencmfcst_2_day", "tencmfcst_3_day"):
    if column != "tencmfcst_1_day":
        _NOAA_METRIC_EXPLANATIONS[("predicted_f107", column)] = _NOAA_METRIC_EXPLANATIONS[
            ("predicted_f107", "tencmfcst_1_day")
        ].copy()

for column in ("afred_2_day", "afred_3_day"):
    _NOAA_METRIC_EXPLANATIONS[("predicted_fredericksburg", column)] = _NOAA_METRIC_EXPLANATIONS[
        ("predicted_fredericksburg", "afred_1_day")
    ].copy()

for column in ("ssn_high", "ssn_low"):
    _NOAA_METRIC_EXPLANATIONS[("predicted_monthly_ssn", column)] = _NOAA_METRIC_EXPLANATIONS[
        ("predicted_monthly_ssn", "ssn_predicted")
    ].copy()

for column in ("flux_high", "flux_low"):
    _NOAA_METRIC_EXPLANATIONS[("predicted_monthly_ssn", column)] = _NOAA_METRIC_EXPLANATIONS[
        ("predicted_monthly_ssn", "flux_predicted")
    ].copy()

for column in (
    "c_class_1_day",
    "c_class_2_day",
    "c_class_3_day",
    "m_class_1_day",
    "m_class_2_day",
    "m_class_3_day",
    "x_class_1_day",
    "x_class_2_day",
    "x_class_3_day",
    "10mev_protons_1_day",
    "10mev_protons_2_day",
    "10mev_protons_3_day",
):
    _NOAA_METRIC_EXPLANATIONS.setdefault(
        ("solar_probabilities", column),
        {
            "title": f"Solar probabilities ({column.replace('_', ' ')})",
            "what": "NOAA probabilistic forecast (% chance) for flare classes or >10 MeV proton events over 1–3 days.",
            "why": "Higher probabilities indicate elevated risk of radiation storms and geomagnetic impacts.",
            "physiology": "Anticipate potential HRV reductions if elevated probabilities lead to storms (via increased geomagnetic activity).",
            "likely_effect": "Indirect: higher probabilities may precede periods of lower HRV should storms materialize.",
            "refs": "Gaisenok 2025; operational NOAA guidance.",
        },
    )


def get_noaa_metric_explanations() -> List[Dict[str, str]]:
    """
    Return a compact list of NOAA metric explanations for use in GPT/export.
    """
    rows: List[Dict[str, str]] = []
    for (dataset_key, value_col), info in _NOAA_METRIC_EXPLANATIONS.items():
        rows.append(
            {
                "metric_group": "NOAA",
                "dataset": dataset_key,
                "value_column": value_col,
                "title": info.get("title", f"{dataset_key}.{value_col}"),
                "what": info.get("what", ""),
                "why": info.get("why", ""),
                "physiology": info.get("physiology", ""),
                "likely_effect": info.get("likely_effect", ""),
                "references": info.get("refs", ""),
            }
        )
    return rows


def explain_noaa_metric(dataset_key: str, value_column: str) -> Optional[Dict[str, str]]:
    """
    Look up a concise explanation for a specific NOAA dataset/value column.
    """
    return _NOAA_METRIC_EXPLANATIONS.get((dataset_key, value_column))


