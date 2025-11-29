"""
Space Weather Data Persistence Module.

Stores and retrieves NOAA/NASA space weather data with timestamps
for correlation analysis with physiological data.

Supports:
- NOAA SWPC: Kp index, F10.7 solar flux, solar wind, X-ray flux
- NASA DONKI: CME, solar flares, geomagnetic storms

Author: Dr. Diego L. Malpica, MD - Aerospace Medicine Specialist
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Try to import database libraries
try:
    import sqlalchemy
    from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, JSON, Text
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class SpaceWeatherRecord:
    """Single space weather measurement record."""
    
    timestamp: datetime
    source: str  # "NOAA_KP", "NOAA_F107", "NOAA_SOLARWIND", "NASA_DONKI"
    metric_name: str
    value: float
    unit: str = ""
    quality_flag: str = "normal"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "quality_flag": self.quality_flag,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpaceWeatherRecord":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data["source"],
            metric_name=data["metric_name"],
            value=data["value"],
            unit=data.get("unit", ""),
            quality_flag=data.get("quality_flag", "normal"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SpaceWeatherBatch:
    """Batch of space weather records for a time range."""
    
    source: str
    start_time: datetime
    end_time: datetime
    records: List[SpaceWeatherRecord] = field(default_factory=list)
    fetch_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame for analysis."""
        if not self.records:
            return pd.DataFrame()
        
        data = [
            {
                "timestamp": r.timestamp,
                "source": r.source,
                "metric_name": r.metric_name,
                "value": r.value,
                "unit": r.unit,
            }
            for r in self.records
        ]
        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df.sort_values("timestamp")


# ============================================================================
# File-Based Storage (Default)
# ============================================================================

class FileBasedSpaceWeatherStore:
    """Simple file-based storage for space weather data."""
    
    def __init__(self, data_dir: str = "data/space_weather") -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self.data_dir / "index.json"
        self._index: Dict[str, Any] = self._load_index()
    
    def _load_index(self) -> Dict[str, Any]:
        """Load or create index file."""
        if self._index_file.exists():
            try:
                with open(self._index_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {"batches": [], "last_updated": {}}
        return {"batches": [], "last_updated": {}}
    
    def _save_index(self) -> None:
        """Save index file."""
        with open(self._index_file, "w") as f:
            json.dump(self._index, f, indent=2, default=str)
    
    def _get_batch_filename(self, source: str, date: datetime) -> str:
        """Generate filename for a batch."""
        date_str = date.strftime("%Y-%m-%d")
        return f"{source}_{date_str}.json"
    
    def store_batch(self, batch: SpaceWeatherBatch) -> bool:
        """Store a batch of space weather records."""
        try:
            # Group records by date
            records_by_date: Dict[str, List[Dict[str, Any]]] = {}
            for record in batch.records:
                date_key = record.timestamp.strftime("%Y-%m-%d")
                if date_key not in records_by_date:
                    records_by_date[date_key] = []
                records_by_date[date_key].append(record.to_dict())
            
            # Store each date's records
            for date_key, records in records_by_date.items():
                filename = f"{batch.source}_{date_key}.json"
                filepath = self.data_dir / filename
                
                # Load existing records if any
                existing_records = []
                if filepath.exists():
                    with open(filepath, "r") as f:
                        existing_records = json.load(f)
                
                # Merge (avoid duplicates by timestamp+metric)
                existing_keys = {
                    (r["timestamp"], r["metric_name"])
                    for r in existing_records
                }
                for record in records:
                    key = (record["timestamp"], record["metric_name"])
                    if key not in existing_keys:
                        existing_records.append(record)
                
                # Save
                with open(filepath, "w") as f:
                    json.dump(existing_records, f, indent=2)
            
            # Update index
            self._index["last_updated"][batch.source] = batch.fetch_time.isoformat()
            self._save_index()
            
            return True
            
        except Exception as e:
            print(f"Error storing space weather batch: {e}")
            return False
    
    def get_records(
        self,
        source: str,
        start_time: datetime,
        end_time: datetime,
        metric_name: Optional[str] = None,
    ) -> List[SpaceWeatherRecord]:
        """Retrieve records for a time range."""
        records = []
        
        # Iterate through date range
        current_date = start_time.date()
        end_date = end_time.date()
        
        while current_date <= end_date:
            filename = f"{source}_{current_date.strftime('%Y-%m-%d')}.json"
            filepath = self.data_dir / filename
            
            if filepath.exists():
                try:
                    with open(filepath, "r") as f:
                        day_records = json.load(f)
                    
                    for r_dict in day_records:
                        record = SpaceWeatherRecord.from_dict(r_dict)
                        if start_time <= record.timestamp <= end_time:
                            if metric_name is None or record.metric_name == metric_name:
                                records.append(record)
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
            
            current_date += timedelta(days=1)
        
        return sorted(records, key=lambda r: r.timestamp)
    
    def get_dataframe(
        self,
        source: str,
        start_time: datetime,
        end_time: datetime,
        metric_name: Optional[str] = None,
    ) -> pd.DataFrame:
        """Get records as DataFrame for analysis."""
        records = self.get_records(source, start_time, end_time, metric_name)
        batch = SpaceWeatherBatch(
            source=source,
            start_time=start_time,
            end_time=end_time,
            records=records,
        )
        return batch.to_dataframe()
    
    def get_last_update(self, source: str) -> Optional[datetime]:
        """Get last update time for a source."""
        ts_str = self._index.get("last_updated", {}).get(source)
        if ts_str:
            return datetime.fromisoformat(ts_str)
        return None
    
    def needs_update(self, source: str, max_age_hours: float = 1.0) -> bool:
        """Check if source data needs refresh."""
        last_update = self.get_last_update(source)
        if last_update is None:
            return True
        
        age = datetime.now(timezone.utc) - last_update
        return age.total_seconds() > max_age_hours * 3600


# ============================================================================
# Database Storage (PostgreSQL)
# ============================================================================

class DatabaseSpaceWeatherStore:
    """PostgreSQL-based storage for space weather data."""
    
    def __init__(self, database_url: Optional[str] = None) -> None:
        if not SQLALCHEMY_AVAILABLE:
            raise ImportError("SQLAlchemy required for database storage")
        
        self.database_url = database_url or os.environ.get(
            "DATABASE_URL",
            "postgresql://hrv_admin:changeme@localhost:5432/hrv_platform"
        )
        self.engine = create_engine(self.database_url)
        self._create_tables()
    
    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        create_sql = """
        CREATE TABLE IF NOT EXISTS space_weather_records (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL,
            source VARCHAR(50) NOT NULL,
            metric_name VARCHAR(100) NOT NULL,
            value DOUBLE PRECISION NOT NULL,
            unit VARCHAR(20),
            quality_flag VARCHAR(20) DEFAULT 'normal',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(timestamp, source, metric_name)
        );
        
        CREATE INDEX IF NOT EXISTS idx_sw_timestamp ON space_weather_records(timestamp);
        CREATE INDEX IF NOT EXISTS idx_sw_source ON space_weather_records(source);
        CREATE INDEX IF NOT EXISTS idx_sw_metric ON space_weather_records(metric_name);
        CREATE INDEX IF NOT EXISTS idx_sw_source_time ON space_weather_records(source, timestamp);
        
        CREATE TABLE IF NOT EXISTS space_weather_fetch_log (
            id SERIAL PRIMARY KEY,
            source VARCHAR(50) NOT NULL,
            fetch_time TIMESTAMPTZ NOT NULL,
            records_count INTEGER,
            status VARCHAR(20),
            error_message TEXT
        );
        """
        
        try:
            with self.engine.connect() as conn:
                conn.execute(sqlalchemy.text(create_sql))
                conn.commit()
        except Exception as e:
            print(f"Warning: Could not create space weather tables: {e}")
    
    def store_batch(self, batch: SpaceWeatherBatch) -> bool:
        """Store a batch of space weather records."""
        try:
            insert_sql = """
            INSERT INTO space_weather_records 
            (timestamp, source, metric_name, value, unit, quality_flag, metadata)
            VALUES (:timestamp, :source, :metric_name, :value, :unit, :quality_flag, :metadata)
            ON CONFLICT (timestamp, source, metric_name) 
            DO UPDATE SET value = EXCLUDED.value, quality_flag = EXCLUDED.quality_flag
            """
            
            with self.engine.connect() as conn:
                for record in batch.records:
                    conn.execute(
                        sqlalchemy.text(insert_sql),
                        {
                            "timestamp": record.timestamp,
                            "source": record.source,
                            "metric_name": record.metric_name,
                            "value": record.value,
                            "unit": record.unit,
                            "quality_flag": record.quality_flag,
                            "metadata": json.dumps(record.metadata),
                        }
                    )
                
                # Log the fetch
                log_sql = """
                INSERT INTO space_weather_fetch_log 
                (source, fetch_time, records_count, status)
                VALUES (:source, :fetch_time, :count, 'success')
                """
                conn.execute(
                    sqlalchemy.text(log_sql),
                    {
                        "source": batch.source,
                        "fetch_time": batch.fetch_time,
                        "count": len(batch.records),
                    }
                )
                conn.commit()
            
            return True
            
        except Exception as e:
            print(f"Error storing space weather batch: {e}")
            return False
    
    def get_records(
        self,
        source: str,
        start_time: datetime,
        end_time: datetime,
        metric_name: Optional[str] = None,
    ) -> List[SpaceWeatherRecord]:
        """Retrieve records for a time range."""
        query = """
        SELECT timestamp, source, metric_name, value, unit, quality_flag, metadata
        FROM space_weather_records
        WHERE source = :source 
          AND timestamp >= :start_time 
          AND timestamp <= :end_time
        """
        
        params = {
            "source": source,
            "start_time": start_time,
            "end_time": end_time,
        }
        
        if metric_name:
            query += " AND metric_name = :metric_name"
            params["metric_name"] = metric_name
        
        query += " ORDER BY timestamp"
        
        records = []
        try:
            with self.engine.connect() as conn:
                result = conn.execute(sqlalchemy.text(query), params)
                for row in result:
                    records.append(SpaceWeatherRecord(
                        timestamp=row.timestamp,
                        source=row.source,
                        metric_name=row.metric_name,
                        value=row.value,
                        unit=row.unit or "",
                        quality_flag=row.quality_flag or "normal",
                        metadata=json.loads(row.metadata) if row.metadata else {},
                    ))
        except Exception as e:
            print(f"Error fetching space weather records: {e}")
        
        return records
    
    def get_dataframe(
        self,
        source: str,
        start_time: datetime,
        end_time: datetime,
        metric_name: Optional[str] = None,
    ) -> pd.DataFrame:
        """Get records as DataFrame."""
        query = """
        SELECT timestamp, source, metric_name, value, unit
        FROM space_weather_records
        WHERE source = :source 
          AND timestamp >= :start_time 
          AND timestamp <= :end_time
        """
        
        params = {
            "source": source,
            "start_time": start_time,
            "end_time": end_time,
        }
        
        if metric_name:
            query += " AND metric_name = :metric_name"
            params["metric_name"] = metric_name
        
        query += " ORDER BY timestamp"
        
        try:
            return pd.read_sql(query, self.engine, params=params)
        except Exception:
            return pd.DataFrame()
    
    def get_last_update(self, source: str) -> Optional[datetime]:
        """Get last update time for a source."""
        query = """
        SELECT MAX(fetch_time) as last_update
        FROM space_weather_fetch_log
        WHERE source = :source AND status = 'success'
        """
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(sqlalchemy.text(query), {"source": source})
                row = result.fetchone()
                return row.last_update if row and row.last_update else None
        except Exception:
            return None
    
    def needs_update(self, source: str, max_age_hours: float = 1.0) -> bool:
        """Check if source data needs refresh."""
        last_update = self.get_last_update(source)
        if last_update is None:
            return True
        
        # Ensure timezone-aware comparison
        if last_update.tzinfo is None:
            last_update = last_update.replace(tzinfo=timezone.utc)
        
        age = datetime.now(timezone.utc) - last_update
        return age.total_seconds() > max_age_hours * 3600


# ============================================================================
# Unified Interface
# ============================================================================

def get_space_weather_store() -> FileBasedSpaceWeatherStore | DatabaseSpaceWeatherStore:
    """Get the appropriate space weather store based on environment."""
    database_url = os.environ.get("DATABASE_URL")
    
    if database_url and SQLALCHEMY_AVAILABLE:
        try:
            return DatabaseSpaceWeatherStore(database_url)
        except Exception as e:
            print(f"Warning: Could not connect to database, using file storage: {e}")
    
    return FileBasedSpaceWeatherStore()


# ============================================================================
# NOAA Data Fetchers with Persistence
# ============================================================================

def fetch_and_store_kp_index(
    store: FileBasedSpaceWeatherStore | DatabaseSpaceWeatherStore,
    days_back: int = 30,
) -> pd.DataFrame:
    """Fetch Kp index from NOAA and store persistently."""
    import urllib.request
    
    source = "NOAA_KP"
    
    # Check if we need to update
    if not store.needs_update(source, max_age_hours=1.0):
        # Return cached data
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days_back)
        return store.get_dataframe(source, start_time, end_time)
    
    # Fetch from NOAA
    url = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
    
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
        
        records = []
        for item in data:
            try:
                # Parse timestamp (format: 2025-11-29 12:00:00.000)
                ts_str = item.get("time_tag", "")
                if not ts_str:
                    continue
                
                timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                
                kp_value = float(item.get("kp_index", 0))
                
                records.append(SpaceWeatherRecord(
                    timestamp=timestamp,
                    source=source,
                    metric_name="Kp",
                    value=kp_value,
                    unit="",
                    quality_flag="measured",
                ))
                
            except (KeyError, ValueError, TypeError):
                continue
        
        if records:
            batch = SpaceWeatherBatch(
                source=source,
                start_time=records[0].timestamp,
                end_time=records[-1].timestamp,
                records=records,
            )
            store.store_batch(batch)
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days_back)
        return store.get_dataframe(source, start_time, end_time)
        
    except Exception as e:
        print(f"Error fetching Kp index: {e}")
        # Return cached data if available
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days_back)
        return store.get_dataframe(source, start_time, end_time)


def fetch_and_store_solar_wind(
    store: FileBasedSpaceWeatherStore | DatabaseSpaceWeatherStore,
    days_back: int = 7,
) -> pd.DataFrame:
    """Fetch solar wind data from NOAA and store persistently."""
    import urllib.request
    
    source = "NOAA_SOLARWIND"
    
    if not store.needs_update(source, max_age_hours=0.5):
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days_back)
        return store.get_dataframe(source, start_time, end_time)
    
    url = "https://services.swpc.noaa.gov/products/solar-wind/plasma-7-day.json"
    
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
        
        records = []
        # Skip header row
        for row in data[1:]:
            try:
                ts_str = row[0]
                timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                
                # Density
                if row[1] is not None:
                    records.append(SpaceWeatherRecord(
                        timestamp=timestamp,
                        source=source,
                        metric_name="density",
                        value=float(row[1]),
                        unit="p/cc",
                    ))
                
                # Speed
                if row[2] is not None:
                    records.append(SpaceWeatherRecord(
                        timestamp=timestamp,
                        source=source,
                        metric_name="speed",
                        value=float(row[2]),
                        unit="km/s",
                    ))
                
                # Temperature
                if row[3] is not None:
                    records.append(SpaceWeatherRecord(
                        timestamp=timestamp,
                        source=source,
                        metric_name="temperature",
                        value=float(row[3]),
                        unit="K",
                    ))
                    
            except (IndexError, ValueError, TypeError):
                continue
        
        if records:
            batch = SpaceWeatherBatch(
                source=source,
                start_time=records[0].timestamp,
                end_time=records[-1].timestamp,
                records=records,
            )
            store.store_batch(batch)
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days_back)
        return store.get_dataframe(source, start_time, end_time)
        
    except Exception as e:
        print(f"Error fetching solar wind: {e}")
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days_back)
        return store.get_dataframe(source, start_time, end_time)


def fetch_and_store_f107(
    store: FileBasedSpaceWeatherStore | DatabaseSpaceWeatherStore,
    days_back: int = 90,
) -> pd.DataFrame:
    """Fetch F10.7 solar flux from NOAA and store persistently."""
    import urllib.request
    
    source = "NOAA_F107"
    
    if not store.needs_update(source, max_age_hours=6.0):
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days_back)
        return store.get_dataframe(source, start_time, end_time)
    
    url = "https://services.swpc.noaa.gov/json/f107_cm_flux.json"
    
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
        
        records = []
        for item in data:
            try:
                ts_str = item.get("time_tag", "")
                if not ts_str:
                    continue
                
                timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                
                flux = float(item.get("flux", 0))
                
                records.append(SpaceWeatherRecord(
                    timestamp=timestamp,
                    source=source,
                    metric_name="F10.7",
                    value=flux,
                    unit="sfu",
                ))
                
            except (KeyError, ValueError, TypeError):
                continue
        
        if records:
            batch = SpaceWeatherBatch(
                source=source,
                start_time=records[0].timestamp,
                end_time=records[-1].timestamp,
                records=records,
            )
            store.store_batch(batch)
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days_back)
        return store.get_dataframe(source, start_time, end_time)
        
    except Exception as e:
        print(f"Error fetching F10.7: {e}")
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days_back)
        return store.get_dataframe(source, start_time, end_time)


# ============================================================================
# Correlation Helper Functions
# ============================================================================

def align_space_weather_with_hrv(
    hrv_df: pd.DataFrame,
    space_weather_df: pd.DataFrame,
    metric_name: str,
    lag_hours: int = 0,
) -> pd.DataFrame:
    """Align space weather data with HRV measurements for correlation analysis.
    
    Args:
        hrv_df: DataFrame with HRV data (must have timestamp column)
        space_weather_df: DataFrame with space weather data
        metric_name: Name of the space weather metric to align
        lag_hours: Hours to shift space weather data (positive = SW before HRV)
    
    Returns:
        Merged DataFrame with aligned data
    """
    if hrv_df.empty or space_weather_df.empty:
        return pd.DataFrame()
    
    # Filter to requested metric
    sw_metric = space_weather_df[space_weather_df["metric_name"] == metric_name].copy()
    if sw_metric.empty:
        return pd.DataFrame()
    
    # Apply lag
    if lag_hours != 0:
        sw_metric["timestamp"] = sw_metric["timestamp"] + timedelta(hours=lag_hours)
    
    # Rename value column
    sw_metric = sw_metric.rename(columns={"value": f"sw_{metric_name}"})
    sw_metric = sw_metric[["timestamp", f"sw_{metric_name}"]]
    
    # Merge using nearest timestamp
    merged = pd.merge_asof(
        hrv_df.sort_values("timestamp"),
        sw_metric.sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta(hours=3),  # Max 3 hour gap
    )
    
    return merged


def compute_hrv_space_weather_correlation(
    hrv_df: pd.DataFrame,
    hrv_metric: str,
    space_weather_df: pd.DataFrame,
    sw_metric: str,
    lag_range: Tuple[int, int] = (-24, 72),
    lag_step: int = 6,
) -> pd.DataFrame:
    """Compute correlations between HRV and space weather at various lags.
    
    Args:
        hrv_df: DataFrame with HRV data
        hrv_metric: Name of HRV metric column
        space_weather_df: DataFrame with space weather data
        sw_metric: Name of space weather metric
        lag_range: (min_lag, max_lag) in hours
        lag_step: Step size for lag search in hours
    
    Returns:
        DataFrame with correlation results at each lag
    """
    from scipy import stats
    
    results = []
    
    for lag in range(lag_range[0], lag_range[1] + 1, lag_step):
        aligned = align_space_weather_with_hrv(
            hrv_df, space_weather_df, sw_metric, lag_hours=lag
        )
        
        if len(aligned) < 10:
            continue
        
        sw_col = f"sw_{sw_metric}"
        if sw_col not in aligned.columns or hrv_metric not in aligned.columns:
            continue
        
        # Drop NaN values
        valid = aligned[[hrv_metric, sw_col]].dropna()
        if len(valid) < 10:
            continue
        
        # Compute Pearson correlation
        r, p_value = stats.pearsonr(valid[hrv_metric], valid[sw_col])
        
        results.append({
            "hrv_metric": hrv_metric,
            "sw_metric": sw_metric,
            "lag_hours": lag,
            "correlation": r,
            "p_value": p_value,
            "n_samples": len(valid),
        })
    
    return pd.DataFrame(results)

