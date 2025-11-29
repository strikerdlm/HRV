"""
Wearable data readers for circadian rhythm analysis.

Provides utilities for loading and processing wearable device data:
- WearableData: Pandas DataFrame accessor for wearable-specific methods
- load_json: Load JSON wearable data files
- load_csv: Load CSV wearable data files
- load_actiwatch: Load ActiWatch CSV exports
- Resampling and combining utilities

Original implementation: Arcascope (https://github.com/Arcascope/circadian)
"""

from __future__ import annotations

import json
from typing import Dict, Optional

import numpy as np
import pandas as pd


__all__ = [
    "VALID_WEARABLE_STREAMS",
    "ACTIWATCH_COLUMN_RENAMING",
    "WEARABLE_RESAMPLE_METHOD",
    "WearableData",
    "load_json",
    "load_csv",
    "load_actiwatch",
    "interval_fraction",
    "resample_df",
    "combine_wearable_dataframes",
]

VALID_WEARABLE_STREAMS = ["steps", "heartrate", "wake", "light_estimate", "activity"]


class WearableData:
    """Pandas DataFrame accessor implementing wearable-specific methods.
    
    This accessor is registered automatically when the module is imported,
    allowing you to use df.wearable.method() syntax on DataFrames.
    
    Example:
        >>> df = pd.DataFrame({'datetime': [...], 'steps': [...]})
        >>> df.wearable.add_metadata({'subject_id': '001'}, inplace=True)
    """

    def __init__(self, pandas_obj: pd.DataFrame) -> None:
        self._validate_columns(pandas_obj)
        self._obj = pandas_obj

    @staticmethod
    def _validate_columns(obj: pd.DataFrame) -> None:
        """Validate that DataFrame has required columns."""
        if "datetime" not in obj.columns:
            if "start" not in obj.columns or "end" not in obj.columns:
                raise AttributeError(
                    "DataFrame must have 'datetime' column or 'start' and 'end' columns"
                )

        if not any(col in obj.columns for col in VALID_WEARABLE_STREAMS):
            raise AttributeError(
                f"DataFrame must have at least one wearable data column from: {VALID_WEARABLE_STREAMS}."
            )

    @staticmethod
    def _validate_metadata(metadata: Optional[Dict[str, str]]) -> None:
        """Validate metadata dictionary format."""
        if metadata:
            if not isinstance(metadata, dict):
                raise AttributeError("Metadata must be a dictionary.")
            if not any(key in metadata.keys() for key in ["data_id", "subject_id"]):
                raise AttributeError(
                    "Metadata must have at least one of the following keys: data_id, subject_id."
                )
            if not all(isinstance(value, str) for value in metadata.values()):
                raise AttributeError("Metadata values must be strings.")

    @staticmethod
    def rename_columns(df: pd.DataFrame, inplace: bool = False) -> Optional[pd.DataFrame]:
        """Standardize column names by making them lowercase and replacing spaces with underscores."""
        columns = [col.lower().replace(" ", "_") for col in df.columns]
        if inplace:
            df.columns = columns
            return None
        else:
            new_df = df.copy()
            new_df.columns = columns
            return new_df

    def is_valid(self) -> bool:
        """Check if the DataFrame is valid wearable data."""
        self._validate_columns(self._obj)
        self._validate_metadata(self._obj.attrs)
        return True

    def add_metadata(
        self,
        metadata: Dict[str, str],
        inplace: bool = False,
    ) -> Optional[pd.DataFrame]:
        """Add metadata to the DataFrame.
        
        Args:
            metadata: Dictionary containing data_id, subject_id, or other info.
            inplace: Whether to modify the current DataFrame or return a new one.
            
        Returns:
            New DataFrame with metadata if inplace=False, otherwise None.
        """
        self._validate_metadata(metadata)
        if inplace:
            for key, value in metadata.items():
                self._obj.attrs[key] = value
            return None
        else:
            obj = self._obj.copy()
            for key, value in metadata.items():
                obj.attrs[key] = value
            return obj


# Register the accessor only once to avoid duplicate warnings in interactive apps
if not hasattr(pd.DataFrame, "wearable"):
    pd.api.extensions.register_dataframe_accessor("wearable")(WearableData)


def load_json(
    filepath: str,
    metadata: Optional[Dict[str, str]] = None,
) -> Dict[str, pd.DataFrame]:
    """Create a dataframe from a JSON containing wearable data.
    
    Args:
        filepath: Path to the JSON file.
        metadata: Optional metadata dictionary with data_id or subject_id.
        
    Returns:
        Dictionary of wearable DataFrames, one per data stream.
        
    Raises:
        AttributeError: If filepath is invalid or JSON has no valid keys.
    """
    if not isinstance(filepath, str):
        raise AttributeError("Filepath must be a string.")
    if metadata is not None:
        WearableData._validate_metadata(metadata)
    
    # Load JSON
    with open(filepath, "r", encoding="utf-8") as f:
        jdict = json.load(f)
    
    # Check valid keys - require at least one valid key, warn about invalid ones
    if not any(key in VALID_WEARABLE_STREAMS for key in jdict.keys()):
        raise AttributeError(
            "Invalid keys in JSON file. At least one key must be steps, heartrate, wake, light_estimate, or activity."
        )
    
    # Create DataFrame for each wearable stream
    df_dict: Dict[str, pd.DataFrame] = {}
    for key in jdict.keys():
        if key in VALID_WEARABLE_STREAMS:
            df_dict[key] = pd.DataFrame.from_dict(jdict[key])
        else:
            print(f"Excluded key: {key} because it's not a valid wearable stream column name.")
    
    # Process each DataFrame
    for key in df_dict.keys():
        df = df_dict[key]
        if "timestamp" in df.columns:
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
        elif "start" in df.columns and "end" in df.columns:
            df["start"] = pd.to_datetime(df["start"], unit="s")
            df["end"] = pd.to_datetime(df["end"], unit="s")
        
        if metadata is not None:
            df.wearable.add_metadata(metadata, inplace=True)
        else:
            df.wearable.add_metadata({"data_id": "unknown", "subject_id": "unknown"}, inplace=True)
        df_dict[key] = df
    
    return df_dict


def load_csv(
    filepath: str,
    metadata: Optional[Dict[str, str]] = None,
    timestamp_col: Optional[str] = None,
    *args,
    **kwargs,
) -> pd.DataFrame:
    """Create a DataFrame from a CSV containing wearable data.
    
    Args:
        filepath: Full path to CSV file.
        metadata: Optional metadata dictionary with data_id or subject_id.
        timestamp_col: Column name to use as timestamp (in seconds since epoch).
            If None, assumes a 'datetime' column exists.
        *args: Additional arguments passed to pd.read_csv.
        **kwargs: Additional keyword arguments passed to pd.read_csv.
        
    Returns:
        DataFrame with wearable data.
        
    Raises:
        AttributeError: If filepath or timestamp_col is invalid.
    """
    if not isinstance(filepath, str):
        raise AttributeError("Filepath must be a string.")
    if timestamp_col is not None and not isinstance(timestamp_col, str):
        raise AttributeError("Timestamp column must be a string.")
    if metadata is not None:
        WearableData._validate_metadata(metadata)
    
    # Load CSV
    df = pd.read_csv(filepath, *args, **kwargs)
    
    # Create datetime column
    if timestamp_col is not None:
        df["datetime"] = pd.to_datetime(df[timestamp_col], unit="s")
    else:
        if "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"])
        elif "start" in df.columns and "end" in df.columns:
            df["start"] = pd.to_datetime(df["start"])
            df["end"] = pd.to_datetime(df["end"])
        if "datetime" not in df.columns and "start" not in df.columns and "end" not in df.columns:
            raise AttributeError(
                "CSV file must have a column named 'datetime' or 'start' and 'end'"
            )
    
    # Add metadata
    if metadata is not None:
        df.wearable.add_metadata(metadata, inplace=True)
    else:
        df.wearable.add_metadata({"data_id": "unknown", "subject_id": "unknown"}, inplace=True)
    
    return df


ACTIWATCH_COLUMN_RENAMING = {
    "White Light": "light_estimate",
    "Sleep/Wake": "wake",
    "Activity": "activity",
}


def load_actiwatch(
    filepath: str,
    metadata: Optional[Dict[str, str]] = None,
    *args,
    **kwargs,
) -> pd.DataFrame:
    """Create a DataFrame from an ActiWatch CSV file.
    
    Args:
        filepath: Full path to ActiWatch CSV file.
        metadata: Optional metadata dictionary with data_id or subject_id.
        *args: Additional arguments passed to pd.read_csv.
        **kwargs: Additional keyword arguments passed to pd.read_csv.
        
    Returns:
        DataFrame with standardized column names.
    """
    if not isinstance(filepath, str):
        raise AttributeError("Filepath must be a string.")
    if metadata is not None:
        WearableData._validate_metadata(metadata)
    
    # Load CSV
    df = pd.read_csv(filepath, *args, **kwargs)
    df["datetime"] = pd.to_datetime(df["Date"] + " " + df["Time"])
    
    # Drop unnecessary columns
    df.drop(columns=["Date", "Time"], inplace=True)
    
    # Rename columns to standard names
    df.rename(columns=ACTIWATCH_COLUMN_RENAMING, inplace=True)
    
    # Add metadata
    if metadata is not None:
        df.wearable.add_metadata(metadata, inplace=True)
    else:
        df.wearable.add_metadata({"data_id": "unknown", "subject_id": "unknown"}, inplace=True)
    
    return df


def interval_fraction(
    starts: pd.Series,
    stops: pd.Series,
    ref_start: pd.Timestamp,
    ref_stop: pd.Timestamp,
) -> pd.Series:
    """Calculate the fraction of each interval contained in a reference interval.
    
    Args:
        starts: Start datetimes of intervals.
        stops: Stop datetimes of intervals.
        ref_start: Start datetime of reference interval.
        ref_stop: Stop datetime of reference interval.
        
    Returns:
        Series with fraction of each interval within the reference.
    """
    max_starts = starts.apply(lambda x: max(x, ref_start))
    min_ends = stops.apply(lambda x: min(x, ref_stop))
    contained_intervals = (min_ends - max_starts).apply(lambda x: x.total_seconds())
    full_intervals = (stops - starts).apply(lambda x: x.total_seconds())
    return contained_intervals / full_intervals


WEARABLE_RESAMPLE_METHOD = {
    "steps": "sum",
    "wake": "max",
    "heartrate": "mean",
    "light_estimate": "mean",
    "activity": "mean",
}


def resample_df(
    df: pd.DataFrame,
    name: str,
    freq: str,
    agg_method: str,
    initial_datetime: Optional[pd.Timestamp] = None,
    final_datetime: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """Resample a wearable DataFrame to a new frequency.
    
    Args:
        df: DataFrame to resample.
        name: Name of the wearable data column (steps, heartrate, wake, light_estimate, activity).
        freq: Target frequency (e.g., '1min', '5min', '1H', '1D').
        agg_method: Aggregation method ('sum', 'mean', 'max', 'min').
        initial_datetime: Start datetime for resampling. Defaults to data minimum.
        final_datetime: End datetime for resampling. Defaults to data maximum.
        
    Returns:
        Resampled DataFrame with datetime and value columns.
    """
    # Validate inputs
    if not df.wearable.is_valid():
        raise AttributeError("DataFrame must be a valid wearable dataframe.")
    if not isinstance(df, pd.DataFrame):
        raise AttributeError("DataFrame must be a pandas dataframe.")
    if not isinstance(freq, str):
        raise AttributeError("Frequency must be a string.")
    if name is not None and name not in VALID_WEARABLE_STREAMS:
        raise AttributeError(f"Name must be one of: {VALID_WEARABLE_STREAMS}.")
    if name not in df.columns:
        raise AttributeError(f"Name must be one of: {df.columns}.")
    if agg_method not in ["sum", "mean", "max", "min"]:
        raise AttributeError("Aggregation method must be one of: sum, mean, max, min.")
    if initial_datetime is not None and not isinstance(initial_datetime, pd.Timestamp):
        raise AttributeError("Initial datetime must be a pandas timestamp.")
    if final_datetime is not None and not isinstance(final_datetime, pd.Timestamp):
        raise AttributeError("Final datetime must be a pandas timestamp.")
    
    values = df[name]
    
    if "start" in df.columns and "end" in df.columns:
        # Data specified in intervals
        starts = df.start
        stops = df.end
        if initial_datetime is None:
            initial_datetime = starts.min()
        if final_datetime is None:
            final_datetime = stops.max()
        new_datetime = pd.date_range(initial_datetime, final_datetime, freq=freq)
        new_values = np.zeros(len(new_datetime))
        
        for idx, dt in enumerate(new_datetime):
            next_dt = dt + pd.to_timedelta(freq)
            mask = (starts <= next_dt) & (stops > dt)
            if len(values[mask]) > 0:
                value_fraction = interval_fraction(starts[mask], stops[mask], dt, next_dt)
                new_values[idx] = (values[mask] * value_fraction).agg(agg_method)
    else:
        # Data specified per datetime
        data_datetimes = df.datetime
        if initial_datetime is None:
            initial_datetime = data_datetimes.min()
        if final_datetime is None:
            final_datetime = data_datetimes.max()
        new_datetime = pd.date_range(initial_datetime, final_datetime, freq=freq)
        new_values = np.zeros(len(new_datetime))
        
        for idx, dt in enumerate(new_datetime):
            next_dt = dt + pd.to_timedelta(freq)
            mask = (data_datetimes <= next_dt) & (data_datetimes >= dt)
            if len(values[mask]) > 0:
                new_values[idx] = values[mask].agg(agg_method)
    
    return pd.DataFrame({"datetime": new_datetime, name: new_values})


def combine_wearable_dataframes(
    df_dict: Dict[str, pd.DataFrame],
    resample_freq: str,
    metadata: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """Combine multiple wearable DataFrames into a single DataFrame with resampling.
    
    Args:
        df_dict: Dictionary of wearable DataFrames keyed by data type.
        resample_freq: Target frequency (e.g., '10min').
        metadata: Optional metadata for combined DataFrame.
        
    Returns:
        Combined and resampled DataFrame.
    """
    df_list = []
    
    # Find common initial and final datetimes
    initial_datetimes = []
    final_datetimes = []
    
    for name in df_dict.keys():
        df = df_dict[name]
        df.wearable.is_valid()
        if "start" in df.columns:
            initial_datetimes.append(df.start.min())
            final_datetimes.append(df.end.max())
        else:
            initial_datetimes.append(df.datetime.min())
            final_datetimes.append(df.datetime.max())
    
    initial_datetime = min(initial_datetimes)
    final_datetime = max(final_datetimes)
    
    # Resample each DataFrame
    for name in df_dict.keys():
        df = df_dict[name]
        new_df = resample_df(
            df,
            name,
            resample_freq,
            WEARABLE_RESAMPLE_METHOD[name],
            initial_datetime=initial_datetime,
            final_datetime=final_datetime,
        )
        df_list.append(new_df)
    
    # Merge all DataFrames by datetime
    df = df_list[0]
    for i in range(1, len(df_list)):
        df = df.merge(df_list[i], on="datetime", how="outer")
    
    # Sort by datetime
    df.sort_values(by="datetime", inplace=True)
    
    # Add metadata
    if metadata is not None:
        df.wearable.add_metadata(metadata, inplace=True)
    else:
        df.wearable.add_metadata({"data_id": "combined_dataframe"}, inplace=True)
    
    return df

