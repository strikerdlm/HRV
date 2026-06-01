"""
Garmin Connect import helpers (Vivosmart 5 and similar) using python-garminconnect.

This module:
- Authenticates with Garmin Connect using GARMIN_EMAIL / GARMIN_PASSWORD.
- Fetches daily wellness metrics (sleep, HRV, resting HR, stress, activity, SpO2, respiration, body battery).
- Normalizes into GarminDailyMetrics records for persistence.
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Final, Iterable, List, Optional, Tuple

import pandas as pd

try:
    from logging_config import get_logger, log_exception
except ImportError:  # pragma: no cover - fallback for non-app contexts
    get_logger = None  # type: ignore[assignment]
    log_exception = None  # type: ignore[assignment]

_LOGGER: Final[logging.Logger] = (
    get_logger(__name__) if get_logger is not None else logging.getLogger(__name__)
)

try:
    from garminconnect import (  # type: ignore
        Garmin,
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
        GarminConnectTooManyRequestsError,
    )
    from garth.exc import GarthException, GarthHTTPError  # type: ignore

    GARMIN_LIB_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    Garmin = None  # type: ignore
    GarminConnectAuthenticationError = Exception  # type: ignore
    GarminConnectConnectionError = Exception  # type: ignore
    GarminConnectTooManyRequestsError = Exception  # type: ignore
    GarthException = Exception  # type: ignore
    GarthHTTPError = Exception  # type: ignore
    GARMIN_LIB_AVAILABLE = False

try:
    # Package import
    from app.user_database import GarminDailyMetrics
except ImportError:  # pragma: no cover - fallback for direct/script imports
    from user_database import GarminDailyMetrics


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


class GarminAuthError(RuntimeError):
    """Raised when Garmin authentication is unavailable or fails."""


def _env_credentials(*, tokenstore_path: str | None = None) -> Tuple[str, str]:
    """Return Garmin credentials from environment (optionally after loading .env).

    Args:
        tokenstore_path: Optional path to the token directory, used only for error
            messaging when creds are missing.

    Raises:
        GarminAuthError: If credentials are not present in the environment.
    """

    # Best-effort load of .env in case this module is used standalone.
    try:
        try:
            # Package import (tests, package mode)
            from app.env_loader import load_env_file  # type: ignore
        except ImportError:
            # Script import (Streamlit adds app/ to sys.path)
            from env_loader import load_env_file  # type: ignore

        load_env_file()
    except ImportError:
        pass

    email = os.getenv("GARMIN_EMAIL", "").strip()
    password = os.getenv("GARMIN_PASSWORD", "").strip()
    if not email or not password:
        token_hint = f" Saved tokens directory: {tokenstore_path}" if tokenstore_path else ""
        raise GarminAuthError(
            "GARMIN_EMAIL/GARMIN_PASSWORD not configured (set in .env or environment)."
            f"{token_hint}"
        )
    return email, password


def _resolve_credentials(
    email: str | None = None,
    password: str | None = None,
    *,
    tokenstore_path: str | None = None,
) -> Tuple[str, str]:
    """Resolve Garmin credentials, preferring explicit (UI-entered) values.

    Resolution order:
        1) Explicit ``email`` and ``password`` arguments (both required).
        2) Environment / ``.env`` via :func:`_env_credentials`.

    This is the single credential chokepoint shared by the live-sync button,
    the autofill path, and any other caller, so UI-entered credentials and the
    ``.env`` workflow stay in sync.

    Raises:
        GarminAuthError: If no complete credential pair can be resolved.
    """
    email_clean = (email or "").strip()
    password_clean = (password or "").strip()
    if email_clean and password_clean:
        return email_clean, password_clean
    return _env_credentials(tokenstore_path=tokenstore_path)


def _safe_float(val: Any) -> Optional[float]:
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    return f if pd.notna(f) else None


def _safe_int(val: Any) -> Optional[int]:
    try:
        i = int(val)
    except (TypeError, ValueError):
        return None
    return i


def _dict_get_case_insensitive(dct: Dict[str, Any], key: str) -> Any:
    """Best-effort case-insensitive dictionary lookup (bounded)."""
    if key in dct:
        return dct.get(key)
    key_lower = key.lower()
    for k, v in dct.items():
        if isinstance(k, str) and k.lower() == key_lower:
            return v
    return None


def _get_first_case_insensitive(dct: Dict[str, Any], keys: Iterable[str]) -> Any:
    """Return the first non-None value for any candidate key (bounded)."""
    for key in keys:
        val = _dict_get_case_insensitive(dct, key)
        if val is not None:
            return val
    return None


def _record_has_any_metric(record: GarminDailyMetrics) -> bool:
    """Return True if at least one metric field is populated."""
    metric_fields = (
        "steps",
        "distance_km",
        "calories_kcal",
        "avg_hr_bpm",
        "resting_hr_bpm",
        "stress_score",
        "sleep_score",
        "sleep_efficiency",
        "sleep_duration_hours",
        "sleep_start_utc",
        "sleep_end_utc",
        "avg_spo2",
        "avg_respiration_awake",
        "avg_respiration_sleep",
        "hrv_rmssd_ms",
        "hrv_sdnn_ms",
        "body_battery_avg",
        "body_battery_charge",
        "body_battery_drain",
        "sleep_deep_minutes",
        "sleep_rem_minutes",
        "sleep_light_minutes",
        "sleep_awake_minutes",
    )
    for field_name in metric_fields:
        if getattr(record, field_name, None) is not None:
            return True
    return False


class GarminConnectClient:
    """Context-managed Garmin client with defensive login and session persistence."""

    def __init__(self, email: str | None = None, password: str | None = None) -> None:
        self.client: Optional[Garmin] = None
        # Optional explicit (UI-entered) credentials; fall back to env/.env when None.
        self._email = email
        self._password = password
        # Token storage directory (matches garminconnect default: ~/.garminconnect)
        self._tokenstore_dir = Path.home() / ".garminconnect"
        self._tokenstore_dir.mkdir(exist_ok=True)

    def __enter__(self) -> Garmin:
        if not GARMIN_LIB_AVAILABLE:
            raise GarminAuthError("python-garminconnect is not installed (see requirements.txt).")

        # Token storage path (matches garminconnect default: ~/.garminconnect)
        tokenstore_path = str(self._tokenstore_dir)

        # First try to login with stored tokens (avoids MFA prompts on subsequent logins).
        # IMPORTANT: Do this BEFORE requiring GARMIN_EMAIL/GARMIN_PASSWORD.
        token_login_succeeded = False
        try:
            _LOGGER.info("Attempting to use saved authentication tokens...")
            self.client = Garmin()  # type: ignore[arg-type]
            # login() can take a tokenstore path - it will try to load from there first
            self.client.login(tokenstore_path)  # type: ignore[arg-type]
            _LOGGER.info("Successfully logged in using saved tokens")
            
            # IMPORTANT: After token-based login, the display_name might not be set.
            # We need to trigger a call that populates it, otherwise API calls fail with
            # "None" in the URL path (e.g., /usersummary/daily/None).
            # The get_full_name() method populates display_name as a side effect.
            try:
                # Always fetch user info to ensure display_name is populated
                full_name = self.client.get_full_name()  # type: ignore[attr-defined]
                display_name = getattr(self.client, 'display_name', None)
                
                if display_name:
                    _LOGGER.info(f"User display_name loaded: {display_name} (full name: {full_name})")
                    token_login_succeeded = True
                else:
                    _LOGGER.warning("get_full_name() succeeded but display_name is still None")
                    raise GarminConnectAuthenticationError(
                        "Token login succeeded but display_name not available - tokens may be stale"
                    )
            except GarminConnectAuthenticationError:
                raise
            except Exception as name_exc:
                _LOGGER.warning(f"Could not fetch user info after token login: {name_exc}")
                raise GarminConnectAuthenticationError(
                    "Token login succeeded but could not fetch user info - tokens may be invalid"
                ) from name_exc
            
            if token_login_succeeded:
                return self.client
        except (
            FileNotFoundError,
            GarthHTTPError,
            GarminConnectAuthenticationError,
            GarminConnectConnectionError,
        ) as exc:
            # No valid tokens found or tokens expired - need fresh login
            _LOGGER.info(f"Token-based login failed ({type(exc).__name__}). Requesting fresh login credentials.")
            # Continue to fresh login below
        except Exception as exc:
            # Other errors during token restore - log and continue to fresh login
            _LOGGER.info(f"Token restore failed: {exc}. Attempting fresh login.")
        
        # Token restore failed or no tokens; fall back to password login,
        # preferring explicit (UI-entered) credentials over env/.env.
        email, password = _resolve_credentials(
            self._email, self._password, tokenstore_path=tokenstore_path
        )

        # Fresh login flow (with MFA support if needed)
        # Following official repository pattern from example.py
        # Note: In non-interactive environments (like Streamlit), MFA cannot be handled automatically
        # Users must either disable MFA or pre-generate tokens using example.py
        try:
            # Use return_on_mfa=True to detect MFA requirement (following repository pattern)
            self.client = Garmin(
                email=email, password=password, is_cn=False, return_on_mfa=True  # type: ignore[arg-type]
            )
            result1, result2 = self.client.login()  # type: ignore[assignment]
            
            # Check if MFA is required (following repository pattern)
            if result1 == "needs_mfa":
                raise GarminAuthError(
                    "Garmin account requires Multi-Factor Authentication (MFA/2FA). "
                    "MFA cannot be handled automatically in this non-interactive environment. "
                    "\n\nTo resolve this issue, you have two options: "
                    "\n\nOption 1 (Recommended): Pre-generate authentication tokens "
                    "\n  1. Run the official example.py script from python-garminconnect: "
                    "\n     python -c \"from garminconnect import Garmin; import os; "
                    "g = Garmin(os.getenv('GARMIN_EMAIL'), os.getenv('GARMIN_PASSWORD'), return_on_mfa=True); "
                    "r1, r2 = g.login(); "
                    "g.resume_login(r2, input('MFA code: ')) if r1 == 'needs_mfa' else None; "
                    "g.garth.dump('~/.garminconnect')\" "
                    "\n  2. This will prompt for MFA once and save tokens for future use "
                    "\n  3. The saved tokens will be used automatically on subsequent runs "
                    "\n\nOption 2: Temporarily disable MFA/2FA in your Garmin account settings "
                    "\n  (Not recommended for security reasons) "
                    f"\n\nToken storage location: {tokenstore_path}"
                )
            
            # Ensure display_name is set after fresh login
            try:
                # Always fetch user info to ensure display_name is populated
                full_name = self.client.get_full_name()  # type: ignore[attr-defined]
                display_name = getattr(self.client, 'display_name', None)
                
                if not display_name:
                    _LOGGER.error("Fresh login succeeded but display_name is None")
                    raise GarminAuthError(
                        "Authentication succeeded but could not retrieve user display name. "
                        "This may indicate an issue with the Garmin Connect API or your account. "
                        "Please verify your credentials and try again."
                    )
                
                _LOGGER.info(f"User display_name loaded: {display_name} (full name: {full_name})")
            except GarminAuthError:
                raise
            except Exception as name_exc:
                _LOGGER.error(f"Could not fetch user info after fresh login: {name_exc}")
                raise GarminAuthError(
                    "Authentication succeeded but could not retrieve user information. "
                    f"Error: {name_exc}"
                ) from name_exc
            
            # Save tokens for future use (reduces MFA prompts)
            # Following official repository pattern: garmin.garth.dump(tokenstore_path)
            try:
                if hasattr(self.client, 'garth'):
                    self.client.garth.dump(tokenstore_path)  # type: ignore[attr-defined]
                    _LOGGER.info(f"Authentication tokens saved to: {tokenstore_path}")
            except Exception:
                # Token save failed, but login succeeded so continue
                # Note: garminconnect may have already saved tokens automatically
                _LOGGER.debug("Could not explicitly save Garmin tokens (may be auto-saved)")
        except GarminConnectAuthenticationError as exc:
            error_msg = str(exc)
            if "GARMIN Authentication Application" in error_msg or "Unexpected title" in error_msg:
                raise GarminAuthError(
                    "Garmin authentication requires additional verification (MFA/2FA). "
                    "The 'GARMIN Authentication Application' error indicates your account requires "
                    "multi-factor authentication that cannot be automated. "
                    "\n\nPossible solutions: "
                    "1) Temporarily disable MFA/2FA in your Garmin account settings, "
                    "2) Use an app-specific password if available, "
                    "3) Verify your GARMIN_EMAIL and GARMIN_PASSWORD in .env are correct. "
                    f"\n\nOriginal error: {exc}"
                ) from exc
            raise GarminAuthError(f"Garmin authentication failed: {exc}") from exc
        except GarminConnectConnectionError as exc:
            error_msg = str(exc)
            if "GARMIN Authentication Application" in error_msg or "Unexpected title" in error_msg:
                raise GarminAuthError(
                    "Garmin SSO authentication error: 'GARMIN Authentication Application'. "
                    "This typically means: "
                    "1) Your account requires MFA/2FA that cannot be automated, "
                    "2) Garmin has changed their authentication flow (library may need update), or "
                    "3) Your credentials are incorrect. "
                    "\n\nPlease verify your GARMIN_EMAIL and GARMIN_PASSWORD in .env. "
                    "If MFA is enabled, you may need to disable it temporarily or use a different authentication method. "
                    f"\n\nOriginal error: {exc}"
                ) from exc
            raise GarminAuthError(f"Garmin connection error: {exc}") from exc
        except GarminConnectTooManyRequestsError as exc:
            raise GarminAuthError(f"Garmin rate limit reached: {exc}") from exc
        except Exception as exc:  # pragma: no cover - defensive
            error_msg = str(exc)
            if "GARMIN Authentication Application" in error_msg or "Unexpected title" in error_msg:
                raise GarminAuthError(
                    "Garmin authentication error: 'GARMIN Authentication Application'. "
                    "Your account likely requires MFA/2FA that cannot be automated. "
                    "Please check your .env credentials and consider temporarily disabling MFA. "
                    f"\n\nOriginal error: {exc}"
                ) from exc
            raise GarminAuthError(f"Garmin login failed: {exc}") from exc
        return self.client

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        try:
            if self.client:
                self.client.logout()
        except Exception:
            # Ignore logout failures
            pass


# -----------------------------------------------------------------------------
# Normalization helpers
# -----------------------------------------------------------------------------


def _extract_sleep(sleep_payload: Any) -> Dict[str, Any]:
    """Parse sleep payload to duration (h), efficiency (0..1), score (0..100), start/end UTC ISO.
    
    Garmin API structure (as of 2025):
    - dailySleepDTO.sleepTimeSeconds (duration in seconds)
    - dailySleepDTO.sleepScores.overall.value (sleep score 0-100)
    - sleepEfficiency may be missing; computed from awake/total if needed
    """
    if not sleep_payload:
        return {}
    if isinstance(sleep_payload, dict) and "dailySleepDTO" in sleep_payload:
        main = sleep_payload.get("dailySleepDTO") or {}
    else:
        main = sleep_payload if isinstance(sleep_payload, dict) else {}

    duration_s = (
        main.get("sleepTimeSeconds")
        or main.get("sleepDurationInSeconds")
        or main.get("durationInSeconds")
        or main.get("duration")
    )
    efficiency = main.get("sleepEfficiency")
    
    # Extract sleep score from nested sleepScores.overall.value structure
    score = main.get("sleepScore") or main.get("overallScore")
    if score is None:
        sleep_scores = main.get("sleepScores")
        if isinstance(sleep_scores, dict):
            overall = sleep_scores.get("overall")
            if isinstance(overall, dict):
                score = overall.get("value")
    
    start_ts = main.get("sleepStartTimestampGMT") or main.get("sleepStartTimestamp")
    end_ts = main.get("sleepEndTimestampGMT") or main.get("sleepEndTimestamp")

    def _to_iso(ts_val: Any) -> Optional[str]:
        if ts_val is None:
            return None
        try:
            # Garmin often returns milliseconds
            ts_int = int(ts_val)
            if ts_int > 1e12:
                ts_dt = datetime.fromtimestamp(ts_int / 1000.0, tz=timezone.utc)
            else:
                ts_dt = datetime.fromtimestamp(ts_int, tz=timezone.utc)
            return ts_dt.isoformat()
        except Exception:
            return None

    sleep_start_utc = _to_iso(start_ts)
    sleep_end_utc = _to_iso(end_ts)
    duration_hours = None
    if duration_s:
        duration_hours = float(max(0.0, _safe_float(duration_s) or 0.0) / 3600.0)

    eff = _safe_float(efficiency)
    if eff is not None and eff > 1.2:
        eff = eff / 100.0

    def _seconds_to_minutes(sec_val: Any) -> Optional[int]:
        sec = _safe_float(sec_val)
        if sec is None:
            return None
        return int(max(0.0, round(sec / 60.0)))

    return {
        "sleep_duration_hours": duration_hours,
        "sleep_efficiency": eff,
        "sleep_score": _safe_float(score),
        "sleep_start_utc": sleep_start_utc,
        "sleep_end_utc": sleep_end_utc,
        "sleep_deep_minutes": _seconds_to_minutes(main.get("deepSleepSeconds")),
        "sleep_rem_minutes": _seconds_to_minutes(main.get("remSleepSeconds")),
        "sleep_light_minutes": _seconds_to_minutes(main.get("lightSleepSeconds")),
        "sleep_awake_minutes": _seconds_to_minutes(main.get("awakeSleepSeconds")),
    }


def _extract_stress(stress_payload: Any) -> Optional[float]:
    if not stress_payload:
        return None
    if isinstance(stress_payload, dict):
        for key in ("overallStressLevel", "averageStressLevel", "avgStressLevel"):
            val = stress_payload.get(key)
            if val is not None:
                return _safe_float(val)
    if isinstance(stress_payload, list) and stress_payload:
        try:
            first = stress_payload[0]
            if isinstance(first, dict):
                return _safe_float(first.get("overallStressLevel") or first.get("stressLevel"))
        except Exception:
            return None
    return None


def _extract_body_battery(body_payload: Any) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Return (avg, charge, drain).
    
    Garmin API structure (as of 2025):
    - List of daily entries, each with:
      - charged: total charge gained
      - drained: total drain
      - bodyBatteryValuesArray: [[timestamp_ms, level], ...] pairs
    """
    if not body_payload:
        return None, None, None
    levels: List[float] = []
    charge: Optional[float] = None
    drain: Optional[float] = None
    try:
        if isinstance(body_payload, list):
            for row in body_payload:
                # Extract charge/drain from daily summary
                if charge is None:
                    charge = _safe_float(row.get("charged"))
                if drain is None:
                    drain = _safe_float(row.get("drained"))
                
                # Extract levels from bodyBatteryValuesArray: [[ts, level], ...]
                values_array = row.get("bodyBatteryValuesArray")
                if isinstance(values_array, list):
                    for entry in values_array:
                        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                            lvl = _safe_float(entry[1])  # [timestamp, level]
                            if lvl is not None:
                                levels.append(lvl)
                
                # Fallback to single-value keys
                if not levels:
                    lvl = _safe_float(
                        row.get("bodyBatteryValue")
                        or row.get("batteryLevel")
                        or row.get("bodyBatteryLevel")
                    )
                    if lvl is not None:
                        levels.append(lvl)
                        
        elif isinstance(body_payload, dict):
            # Single-day dict format
            values_array = body_payload.get("bodyBatteryValuesArray")
            if isinstance(values_array, list):
                for entry in values_array:
                    if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                        lvl = _safe_float(entry[1])
                        if lvl is not None:
                            levels.append(lvl)
            if not levels:
                lvl = _safe_float(
                    body_payload.get("bodyBatteryValue")
                    or body_payload.get("batteryLevel")
                )
                if lvl is not None:
                    levels.append(lvl)
            charge = _safe_float(body_payload.get("charged"))
            drain = _safe_float(body_payload.get("drained"))
    except Exception:
        return None, None, None
    avg_level = float(pd.Series(levels).mean()) if levels else None
    return avg_level, charge, drain


def _extract_respiration(resp_payload: Any) -> Tuple[Optional[float], Optional[float]]:
    """Extract awake and sleep respiration averages from Garmin API response.
    
    Garmin API field names (as of 2025):
    - avgWakingRespirationValue (waking/awake average)
    - avgSleepRespirationValue (sleep average)
    - Older/alternate: awakeRespirationAvg, sleepRespirationAvg
    """
    awake = None
    sleep = None
    if isinstance(resp_payload, dict):
        # Try current API field names first, then fallback to legacy
        awake = _safe_float(
            resp_payload.get("avgWakingRespirationValue")
            or resp_payload.get("awakeRespirationAvg")
        )
        sleep = _safe_float(
            resp_payload.get("avgSleepRespirationValue")
            or resp_payload.get("sleepRespirationAvg")
        )
    elif isinstance(resp_payload, list) and resp_payload:
        try:
            first = resp_payload[0]
            if isinstance(first, dict):
                awake = _safe_float(
                    first.get("avgWakingRespirationValue")
                    or first.get("awakeRespirationAvg")
                )
                sleep = _safe_float(
                    first.get("avgSleepRespirationValue")
                    or first.get("sleepRespirationAvg")
                )
        except Exception:
            return None, None
    return awake, sleep


def _extract_spo2(spo_payload: Any) -> Optional[float]:
    """Extract average SpO2 from Garmin API response.
    
    Garmin API field names (as of 2025):
    - averageSpO2 (primary daily average)
    - avgSleepSpO2 (sleep-specific average)
    - avgSpO2Value, avgSpO2 (legacy/alternate)
    """
    if isinstance(spo_payload, dict):
        return _safe_float(
            spo_payload.get("averageSpO2")
            or spo_payload.get("avgSleepSpO2")
            or spo_payload.get("avgSpO2Value")
            or spo_payload.get("avgSpO2")
            or spo_payload.get("spo2Value")
        )
    if isinstance(spo_payload, list) and spo_payload:
        try:
            first = spo_payload[0]
            if isinstance(first, dict):
                return _safe_float(
                    first.get("averageSpO2")
                    or first.get("avgSpO2Value")
                    or first.get("avgSpO2")
                )
        except Exception:
            return None
    return None


def _extract_hrv(hrv_payload: Any) -> Tuple[Optional[float], Optional[float]]:
    rmssd = None
    sdnn = None
    if isinstance(hrv_payload, dict):
        rmssd = _safe_float(
            hrv_payload.get("rmssd") or hrv_payload.get("hrvRmssd") or hrv_payload.get("lastNightAvgRmssd")
        )
        sdnn = _safe_float(hrv_payload.get("sdnn") or hrv_payload.get("hrvSdnn"))
    elif isinstance(hrv_payload, list) and hrv_payload:
        try:
            first = hrv_payload[0] if isinstance(hrv_payload[0], dict) else None
            if first:
                rmssd = _safe_float(first.get("rmssd") or first.get("hrvRmssd"))
                sdnn = _safe_float(first.get("sdnn") or first.get("hrvSdnn"))
        except Exception:
            return None, None
    return rmssd, sdnn


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def login_and_get_display_name(email: str, password: str) -> str:
    """Validate Garmin credentials and return the account's full name.

    Used by the UI "Connect" step to confirm credentials before fetching and to
    seed the ``~/.garminconnect`` token cache. Raises :class:`GarminAuthError`
    (or a Garmin library error) if authentication fails.
    """
    with GarminConnectClient(email=email, password=password) as client:
        full_name = client.get_full_name()
        return str(full_name) if full_name is not None else ""


def fetch_garmin_daily_metrics(
    user_id: str,
    days: int = 14,
    *,
    email: str | None = None,
    password: str | None = None,
) -> List[GarminDailyMetrics]:
    """
    Fetch daily Garmin metrics for the last N days (inclusive of today).

    Args:
        user_id: Profile identifier the metrics are stored against.
        days: Number of days to fetch (inclusive of today), capped at 90.
        email: Optional explicit Garmin email (UI-entered). Falls back to env/.env.
        password: Optional explicit Garmin password (UI-entered). Falls back to env/.env.

    Returns a list of GarminDailyMetrics ready for persistence.
    """
    if not user_id:
        raise ValueError("user_id is required to fetch Garmin metrics.")
    try:
        days = int(days)
    except (TypeError, ValueError):
        raise ValueError("days must be an integer.") from None
    if days <= 0:
        return []
    max_days = 90
    if days > max_days:
        # Defensive cap to reduce rate-limit risk.
        _LOGGER.info("Capping Garmin Connect fetch to %d days (requested %d).", max_days, days)
        days = max_days

    start_date = date.today() - timedelta(days=days - 1)
    records: List[GarminDailyMetrics] = []
    errors: list[str] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    with GarminConnectClient(email=email, password=password) as client:
        for idx in range(days):
            day = start_date + timedelta(days=idx)
            day_iso = day.isoformat()

            # Use get_stats() which returns comprehensive daily data including
            # activity, stress, body battery, SpO2, respiration, HR in one call
            day_errors: list[Exception] = []
            stats: Dict[str, Any] = {}
            try:
                stats = client.get_stats(day_iso) or {}
            except Exception as exc:
                day_errors.append(exc)
                # Fallback to user_summary if get_stats fails
                try:
                    stats = client.get_user_summary(day_iso) or {}
                except Exception as exc2:
                    day_errors.append(exc2)
                    stats = {}
            if not isinstance(stats, dict):
                stats = {}

            # Activity metrics from stats
            steps = _safe_int(
                _get_first_case_insensitive(stats, ("totalSteps", "steps", "total_steps"))
            )

            distance_km: Optional[float] = None
            dist_m = _safe_float(
                _get_first_case_insensitive(stats, ("totalDistanceMeters", "totalDistanceInMeters"))
            )
            dist_km = _safe_float(
                _get_first_case_insensitive(stats, ("distanceKm", "distance_km", "distanceKilometers"))
            )
            dist_any = _safe_float(
                _get_first_case_insensitive(stats, ("totalDistance", "distance", "total_distance"))
            )
            if dist_m is not None:
                distance_km = dist_m / 1000.0
            elif dist_km is not None:
                distance_km = dist_km
            elif dist_any is not None:
                # Heuristic: very large values are almost certainly meters.
                distance_km = (dist_any / 1000.0) if dist_any > 100.0 else dist_any

            calories = _safe_float(
                _get_first_case_insensitive(
                    stats,
                    (
                        "totalKilocalories",
                        "totalCalories",
                        "activeKilocalories",
                        "activeCalories",
                        "calories",
                        "caloriesKcal",
                    ),
                )
            )
            avg_hr = _safe_float(
                _get_first_case_insensitive(
                    stats,
                    (
                        "averageHR",
                        "averageHeartRate",
                        "avgHeartRate",
                        "avg_hr",
                        "maxAvgHeartRate",
                        "avg_heart_rate",
                    ),
                )
            )
            resting_hr = _safe_float(
                _get_first_case_insensitive(
                    stats,
                    (
                        "restingHeartRate",
                        "restingHR",
                        "currentDayRestingHeartRate",
                        "restingHeartRateBpm",
                    ),
                )
            )
            
            # Stress from stats (backup from dedicated endpoint)
            stress_score = _safe_float(
                _get_first_case_insensitive(
                    stats,
                    (
                        "averageStressLevel",
                        "avgStressLevel",
                        "overallStressLevel",
                    ),
                )
            )
            
            # SpO2 from stats
            spo2_avg = _safe_float(
                _get_first_case_insensitive(
                    stats,
                    (
                        "averageSpO2",
                        "averageSpo2",
                        "avgSpo2",
                        "averageSpO2Value",
                        "averageSpo2Value",
                    ),
                )
            )
            
            # Respiration from stats
            resp_awake = _safe_float(
                _get_first_case_insensitive(
                    stats,
                    (
                        "avgWakingRespirationValue",
                        "awakeRespirationAvg",
                        "avgRespirationValue",
                    ),
                )
            )
            resp_sleep = None  # Sleep respiration needs separate call
            
            # Body battery from stats
            body_charge = _safe_float(
                _get_first_case_insensitive(
                    stats,
                    (
                        "bodyBatteryChargedValue",
                        "bodyBatteryCharged",
                        "chargedValue",
                    ),
                )
            )
            body_drain = _safe_float(
                _get_first_case_insensitive(
                    stats,
                    (
                        "bodyBatteryDrainedValue",
                        "bodyBatteryDrained",
                        "drainedValue",
                    ),
                )
            )
            body_avg = _safe_float(
                _get_first_case_insensitive(
                    stats,
                    (
                        "bodyBatteryMostRecentValue",
                        "bodyBatteryValue",
                        "bodyBatteryLevel",
                        "bodyBatteryMostRecent",
                    ),
                )
            )

            # Sleep - need dedicated endpoint for score/duration/efficiency
            sleep_info: Dict[str, Any] = {}
            try:
                sleep_payload = client.get_sleep_data(day_iso)
                sleep_info = _extract_sleep(sleep_payload)
            except Exception as exc:
                day_errors.append(exc)
                sleep_info = {}

            # If stress not in stats, try dedicated endpoint
            if stress_score is None:
                try:
                    stress_payload = client.get_all_day_stress(day_iso)
                    stress_score = _extract_stress(stress_payload)
                except Exception as exc:
                    day_errors.append(exc)

            # Get sleep respiration from dedicated endpoint
            try:
                resp_payload = client.get_respiration_data(day_iso)
                _, resp_sleep_from_api = _extract_respiration(resp_payload)
                if resp_sleep_from_api is not None:
                    resp_sleep = resp_sleep_from_api
                # Also fill awake if stats didn't have it
                if resp_awake is None:
                    resp_awake_from_api, _ = _extract_respiration(resp_payload)
                    resp_awake = resp_awake_from_api
            except Exception as exc:
                day_errors.append(exc)

            # If SpO2 not in stats, try dedicated endpoint
            if spo2_avg is None:
                try:
                    spo2_payload = client.get_spo2_data(day_iso)
                    spo2_avg = _extract_spo2(spo2_payload)
                except Exception as exc:
                    day_errors.append(exc)

            # If body battery not complete from stats, try dedicated endpoint
            if body_avg is None or body_charge is None or body_drain is None:
                try:
                    body_payload = client.get_body_battery(day_iso)
                    bb_avg, bb_charge, bb_drain = _extract_body_battery(body_payload)
                    if body_avg is None:
                        body_avg = bb_avg
                    if body_charge is None:
                        body_charge = bb_charge
                    if body_drain is None:
                        body_drain = bb_drain
                except Exception as exc:
                    day_errors.append(exc)

            # HRV (nightly) - always from dedicated endpoint
            hrv_rmssd = None
            hrv_sdnn = None
            try:
                hrv_payload = client.get_hrv_data(day_iso)
                hrv_rmssd, hrv_sdnn = _extract_hrv(hrv_payload)
            except Exception as exc:
                day_errors.append(exc)
                hrv_rmssd, hrv_sdnn = None, None

            record = GarminDailyMetrics(
                entry_id="",
                user_id=user_id,
                metric_date=day_iso,
                steps=steps,
                distance_km=distance_km,
                calories_kcal=calories,
                avg_hr_bpm=avg_hr,
                resting_hr_bpm=resting_hr,
                stress_score=stress_score,
                sleep_score=sleep_info.get("sleep_score"),
                sleep_efficiency=sleep_info.get("sleep_efficiency"),
                sleep_duration_hours=sleep_info.get("sleep_duration_hours"),
                sleep_start_utc=sleep_info.get("sleep_start_utc"),
                sleep_end_utc=sleep_info.get("sleep_end_utc"),
                sleep_deep_minutes=sleep_info.get("sleep_deep_minutes"),
                sleep_rem_minutes=sleep_info.get("sleep_rem_minutes"),
                sleep_light_minutes=sleep_info.get("sleep_light_minutes"),
                sleep_awake_minutes=sleep_info.get("sleep_awake_minutes"),
                avg_spo2=spo2_avg,
                avg_respiration_awake=resp_awake,
                avg_respiration_sleep=resp_sleep,
                hrv_rmssd_ms=hrv_rmssd,
                hrv_sdnn_ms=hrv_sdnn,
                body_battery_avg=body_avg,
                body_battery_charge=body_charge,
                body_battery_drain=body_drain,
                source="garmin_connect_api",
                created_at=now_iso,
            )
            if _record_has_any_metric(record):
                records.append(record)
            else:
                # Avoid returning "all-null" placeholder rows that look like incorrect data.
                if day_errors:
                    errors.append(f"{day_iso}: {day_errors[-1]}")
                    if log_exception is not None:
                        log_exception(_LOGGER, f"Garmin Connect fetch produced no metrics for {day_iso}", day_errors[-1])

    if not records and errors:
        raise GarminAuthError(
            "Garmin Connect returned no usable daily metrics. "
            f"Most recent error: {errors[-1]}"
        )
    return records


def summarize_garmin_daily(records: Iterable[GarminDailyMetrics]) -> Dict[str, Any]:
    """Small helper to produce a user-facing summary."""
    recs = list(records)
    if not recs:
        return {"count": 0}
    df = pd.DataFrame([asdict(r) for r in recs])
    return {
        "count": len(recs),
        "dates": (
            f"{pd.to_datetime(df['metric_date']).min().date().isoformat()} → "
            f"{pd.to_datetime(df['metric_date']).max().date().isoformat()}"
        ),
        "steps_mean": _safe_float(pd.to_numeric(df.get("steps"), errors="coerce").mean()),
        "sleep_hours_mean": _safe_float(pd.to_numeric(df.get("sleep_duration_hours"), errors="coerce").mean()),
        "resting_hr_mean": _safe_float(pd.to_numeric(df.get("resting_hr_bpm"), errors="coerce").mean()),
    }
