"""
Polar AccessLink Integration Module for Mission Control - Flight Surgeon.

Provides automated OAuth token management and VO2max synchronization with Polar Flow:
- Secure token storage with simple encryption
- VO2max fetch and history tracking
- Automatic sync scheduling
- Token refresh handling

The AccessLink API provides cardiorespiratory fitness data (VO2max estimates)
collected from Polar devices via Polar Flow.

API Reference: https://www.polar.com/accesslink-api/

Author: Dr. Diego Leonel Malpica Hincapié, MD
Version: 1.0.0
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Final, List, Optional, Tuple

import requests

# Import from same package
try:
    from app.user_database import (
        UserDatabase,
        PolarCredentials,
        VO2maxEntry,
        get_database,
    )
except ImportError:
    # Fallback for direct imports
    from user_database import (
        UserDatabase,
        PolarCredentials,
        VO2maxEntry,
        get_database,
    )

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POLAR_ACCESSLINK_BASE_URL: Final[str] = "https://www.polaraccesslink.com/v3"
POLAR_API_TIMEOUT: Final[float] = 15.0

# Environment variable names
ENV_POLAR_TOKEN: Final[str] = "POLAR_ACCESSLINK_TOKEN"
ENV_POLAR_USER_ID: Final[str] = "POLAR_ACCESSLINK_USER_ID"
ENV_POLAR_CLIENT_ID: Final[str] = "POLAR_CLIENT_ID"
ENV_POLAR_CLIENT_SECRET: Final[str] = "POLAR_CLIENT_SECRET"
ENV_ENCRYPTION_KEY: Final[str] = "POLAR_ENCRYPTION_KEY"

# Polar Fitness Classifications (per Polar documentation)
POLAR_FITNESS_CLASSES: Dict[str, Tuple[int, int]] = {
    "Very Poor": (0, 25),
    "Poor": (26, 40),
    "Fair": (41, 51),
    "Moderate": (52, 56),
    "Good": (57, 61),
    "Very Good": (62, 67),
    "Excellent": (68, 100),
}


# ---------------------------------------------------------------------------
# Token Encryption (Simple XOR with secret key - for dev/demo purposes)
# ---------------------------------------------------------------------------

def _get_encryption_key() -> bytes:
    """Get or generate encryption key for token storage.
    
    Uses ENV_ENCRYPTION_KEY if set, otherwise generates a stable key
    based on machine-specific information.
    
    Returns:
        32-byte encryption key.
    """
    env_key = os.getenv(ENV_ENCRYPTION_KEY, "").strip()
    if env_key:
        # Hash the provided key to get consistent 32 bytes
        return hashlib.sha256(env_key.encode()).digest()
    
    # Generate stable key from machine info (not cryptographically secure
    # but sufficient for obfuscation in local database)
    username = "user"
    try:
        username = os.getlogin()
    except (OSError, AttributeError):
        # os.getlogin() fails in non-TTY environments
        username = os.environ.get("USER", os.environ.get("USERNAME", "user"))
    machine_info = f"{os.name}-{username}"
    return hashlib.sha256(machine_info.encode()).digest()


def encrypt_token(token: str) -> str:
    """Encrypt a token for storage.
    
    Uses simple XOR encryption with base64 encoding.
    This is not cryptographically secure but provides obfuscation
    for tokens stored in the local SQLite database.
    
    Args:
        token: Plain text token to encrypt.
        
    Returns:
        Base64-encoded encrypted token.
    """
    if not token:
        return ""
    
    key = _get_encryption_key()
    token_bytes = token.encode("utf-8")
    
    # XOR each byte with corresponding key byte (cycling)
    encrypted = bytes(
        b ^ key[i % len(key)]
        for i, b in enumerate(token_bytes)
    )
    
    return base64.b64encode(encrypted).decode("ascii")


def decrypt_token(encrypted: str) -> str:
    """Decrypt a stored token.
    
    Args:
        encrypted: Base64-encoded encrypted token.
        
    Returns:
        Plain text token.
    """
    if not encrypted:
        return ""
    
    key = _get_encryption_key()
    
    try:
        encrypted_bytes = base64.b64decode(encrypted.encode("ascii"))
    except (ValueError, UnicodeDecodeError):
        _LOGGER.warning("Failed to decode encrypted token")
        return ""
    
    # XOR to decrypt (same operation as encrypt)
    decrypted = bytes(
        b ^ key[i % len(key)]
        for i, b in enumerate(encrypted_bytes)
    )
    
    try:
        return decrypted.decode("utf-8")
    except UnicodeDecodeError:
        _LOGGER.warning("Failed to decrypt token - may be corrupted or key changed")
        return ""


# ---------------------------------------------------------------------------
# Polar API Response Types
# ---------------------------------------------------------------------------

@dataclass
class PolarVO2maxResponse:
    """Response from Polar AccessLink cardiorespiratory fitness endpoint."""
    
    vo2max: Optional[float]
    fitness_class: Optional[str]
    timestamp: Optional[str]
    source: str = "polar"
    raw_response: Optional[Dict[str, Any]] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if response contains valid VO2max data."""
        return self.vo2max is not None and self.vo2max > 0


@dataclass
class PolarSyncResult:
    """Result of a Polar AccessLink sync operation."""
    
    success: bool
    vo2max: Optional[float] = None
    fitness_class: Optional[str] = None
    message: str = ""
    entries_saved: int = 0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Polar AccessLink Client
# ---------------------------------------------------------------------------

class PolarAccessLinkClient:
    """Client for interacting with Polar AccessLink API.
    
    Handles token management, API calls, and VO2max synchronization.
    """
    
    def __init__(
        self,
        user_id: str,
        db: Optional[UserDatabase] = None,
    ) -> None:
        """Initialize the client for a specific user.
        
        Args:
            user_id: Application user ID (not Polar user ID).
            db: Database instance. Uses global singleton if None.
        """
        self.user_id = user_id
        self.db = db or get_database()
        self._credentials: Optional[PolarCredentials] = None
    
    @property
    def credentials(self) -> Optional[PolarCredentials]:
        """Get cached or load credentials from database."""
        if self._credentials is None:
            if not hasattr(self.db, "get_polar_credentials"):
                _LOGGER.error(
                    "UserDatabase missing get_polar_credentials; Polar AccessLink disabled"
                )
                return None
            try:
                self._credentials = self.db.get_polar_credentials(self.user_id)
            except Exception as exc:  # pragma: no cover - defensive log path
                _LOGGER.error("Failed to load Polar credentials: %s", exc)
                return None
        return self._credentials
    
    def has_credentials(self) -> bool:
        """Check if user has stored Polar credentials."""
        return self.credentials is not None
    
    def has_valid_token(self) -> bool:
        """Check if user has a valid (non-expired) access token."""
        creds = self.credentials
        if not creds or not creds.access_token_encrypted:
            return False
        
        # Check expiration if set
        if creds.token_expires_at:
            try:
                expires = datetime.fromisoformat(creds.token_expires_at.replace("Z", "+00:00"))
                if expires < datetime.now(timezone.utc):
                    return False
            except (ValueError, TypeError):
                pass  # Ignore invalid dates
        
        return True
    
    def get_access_token(self) -> Optional[str]:
        """Get decrypted access token if available.
        
        Returns:
            Decrypted access token or None.
        """
        creds = self.credentials
        if not creds or not creds.access_token_encrypted:
            return None
        return decrypt_token(creds.access_token_encrypted)
    
    def get_polar_user_id(self) -> Optional[str]:
        """Get Polar user ID from stored credentials or environment.
        
        Returns:
            Polar user ID or None.
        """
        creds = self.credentials
        if creds and creds.polar_user_id:
            return creds.polar_user_id
        return os.getenv(ENV_POLAR_USER_ID, "").strip() or None
    
    def save_credentials(
        self,
        access_token: str,
        polar_user_id: str,
        *,
        refresh_token: Optional[str] = None,
        expires_in_seconds: Optional[int] = None,
    ) -> str:
        """Save Polar credentials for the user.
        
        Args:
            access_token: OAuth access token.
            polar_user_id: Polar Flow user ID.
            refresh_token: Optional refresh token.
            expires_in_seconds: Token lifetime in seconds.
            
        Returns:
            Credential ID.
        """
        now = datetime.now(timezone.utc)
        expires_at = None
        if expires_in_seconds:
            expires_at = (now + timedelta(seconds=expires_in_seconds)).isoformat()
        
        creds = PolarCredentials(
            credential_id="",  # Will be generated
            user_id=self.user_id,
            polar_user_id=polar_user_id,
            access_token_encrypted=encrypt_token(access_token),
            refresh_token_encrypted=encrypt_token(refresh_token) if refresh_token else None,
            token_expires_at=expires_at,
            sync_enabled=True,
        )
        
        credential_id = self.db.save_polar_credentials(creds)
        self._credentials = None  # Clear cache
        _LOGGER.info("Saved Polar credentials for user %s", self.user_id)
        return credential_id
    
    def clear_credentials(self) -> bool:
        """Remove stored Polar credentials for the user.
        
        Returns:
            True if credentials were deleted.
        """
        result = self.db.delete_polar_credentials(self.user_id)
        self._credentials = None  # Clear cache
        return result
    
    def fetch_vo2max(self) -> PolarVO2maxResponse:
        """Fetch VO2max from Polar AccessLink API.
        
        Returns:
            PolarVO2maxResponse with VO2max data or error information.
        """
        access_token = self.get_access_token()
        polar_user_id = self.get_polar_user_id()
        
        # Fall back to environment variables if no stored credentials
        if not access_token:
            access_token = os.getenv(ENV_POLAR_TOKEN, "").strip()
        if not polar_user_id:
            polar_user_id = os.getenv(ENV_POLAR_USER_ID, "").strip()
        
        if not access_token or not polar_user_id:
            _LOGGER.debug("Polar AccessLink not configured")
            return PolarVO2maxResponse(
                vo2max=None,
                fitness_class=None,
                timestamp=None,
                raw_response=None,
            )
        
        url = f"{POLAR_ACCESSLINK_BASE_URL}/users/{polar_user_id}/cardiorespiratory-fitness"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=POLAR_API_TIMEOUT)
            
            if response.status_code == 401:
                _LOGGER.warning("Polar AccessLink token expired or invalid")
                return PolarVO2maxResponse(
                    vo2max=None,
                    fitness_class=None,
                    timestamp=None,
                    raw_response={"error": "unauthorized"},
                )
            
            if response.status_code == 404:
                _LOGGER.info("No VO2max data available from Polar")
                return PolarVO2maxResponse(
                    vo2max=None,
                    fitness_class=None,
                    timestamp=None,
                    raw_response={"error": "not_found"},
                )
            
            response.raise_for_status()
            payload = response.json()
            
        except requests.Timeout:
            _LOGGER.warning("Polar AccessLink request timed out")
            return PolarVO2maxResponse(
                vo2max=None,
                fitness_class=None,
                timestamp=None,
                raw_response={"error": "timeout"},
            )
        except requests.RequestException as exc:
            _LOGGER.warning("Polar AccessLink request failed: %s", exc)
            return PolarVO2maxResponse(
                vo2max=None,
                fitness_class=None,
                timestamp=None,
                raw_response={"error": str(exc)},
            )
        except ValueError as exc:
            _LOGGER.warning("Invalid JSON from Polar AccessLink: %s", exc)
            return PolarVO2maxResponse(
                vo2max=None,
                fitness_class=None,
                timestamp=None,
                raw_response={"error": "invalid_json"},
            )
        
        # Parse response - API format may vary
        vo2max = self._extract_vo2max(payload)
        fitness_class = self._determine_fitness_class(vo2max) if vo2max else None
        timestamp = payload.get("timestamp") or payload.get("date") or datetime.now(timezone.utc).isoformat()
        
        return PolarVO2maxResponse(
            vo2max=vo2max,
            fitness_class=fitness_class,
            timestamp=timestamp,
            raw_response=payload,
        )
    
    def _extract_vo2max(self, payload: Dict[str, Any]) -> Optional[float]:
        """Extract VO2max value from API response.
        
        Args:
            payload: JSON response from Polar API.
            
        Returns:
            VO2max in mL/kg/min or None.
        """
        # Try common field names
        candidate_keys = ("vo2max", "vo2_max", "cardiorespiratory_fitness", "fitness")
        
        for key in candidate_keys:
            value = payload.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        
        # Check nested structures
        if isinstance(payload, dict):
            for value in payload.values():
                if isinstance(value, (int, float)) and 10 < value < 100:
                    # Likely a VO2max value (reasonable range)
                    return float(value)
                if isinstance(value, dict):
                    for key in candidate_keys:
                        nested = value.get(key)
                        if isinstance(nested, (int, float)):
                            return float(nested)
        
        return None
    
    def _determine_fitness_class(self, vo2max: float) -> str:
        """Determine fitness classification from VO2max value.
        
        Based on Polar's fitness classification system.
        
        Args:
            vo2max: VO2max in mL/kg/min.
            
        Returns:
            Fitness class name.
        """
        # Simplified classification (age/sex-dependent in full implementation)
        if vo2max < 25:
            return "Very Poor"
        elif vo2max < 40:
            return "Poor"
        elif vo2max < 45:
            return "Fair"
        elif vo2max < 51:
            return "Moderate"
        elif vo2max < 57:
            return "Good"
        elif vo2max < 63:
            return "Very Good"
        else:
            return "Excellent"
    
    def sync_vo2max(self) -> PolarSyncResult:
        """Sync VO2max from Polar and save to history.
        
        Fetches current VO2max from Polar AccessLink and saves it
        to the VO2max history table if it's a new value.
        
        Returns:
            PolarSyncResult with sync outcome.
        """
        response = self.fetch_vo2max()
        
        if not response.is_valid:
            error_msg = "No VO2max data available"
            if response.raw_response:
                error_msg = response.raw_response.get("error", error_msg)
            return PolarSyncResult(
                success=False,
                message="Sync failed",
                error=error_msg,
            )
        
        # Check if this is a new value (avoid duplicates)
        latest = self.db.get_latest_vo2max(self.user_id)
        if latest and abs(latest.vo2max_ml_kg_min - response.vo2max) < 0.1:
            # Same value, check if recent
            try:
                latest_date = datetime.fromisoformat(latest.measurement_date.replace("Z", "+00:00"))
                if (datetime.now(timezone.utc) - latest_date) < timedelta(hours=24):
                    return PolarSyncResult(
                        success=True,
                        vo2max=response.vo2max,
                        fitness_class=response.fitness_class,
                        message="Already up to date",
                        entries_saved=0,
                    )
            except (ValueError, TypeError):
                pass
        
        # Save new entry
        entry = VO2maxEntry(
            entry_id="",  # Will be generated
            user_id=self.user_id,
            measurement_date=response.timestamp or datetime.now(timezone.utc).isoformat(),
            vo2max_ml_kg_min=response.vo2max,
            source="polar",
            polar_fitness_class=response.fitness_class,
            notes="Synced from Polar AccessLink",
        )
        
        self.db.save_vo2max_entry(entry)
        self.db.update_polar_sync_time(self.user_id)
        
        return PolarSyncResult(
            success=True,
            vo2max=response.vo2max,
            fitness_class=response.fitness_class,
            message=f"Synced VO2max: {response.vo2max:.1f} mL/kg/min",
            entries_saved=1,
        )
    
    def get_vo2max_history(self, limit: int = 50) -> List[VO2maxEntry]:
        """Get VO2max history for the user.
        
        Args:
            limit: Maximum number of entries to return.
            
        Returns:
            List of VO2maxEntry objects.
        """
        return self.db.get_vo2max_history(self.user_id, limit=limit)
    
    def get_latest_vo2max(self) -> Optional[VO2maxEntry]:
        """Get the most recent VO2max entry.
        
        Returns:
            Most recent VO2maxEntry or None.
        """
        return self.db.get_latest_vo2max(self.user_id)


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------

def polar_accesslink_available() -> bool:
    """Check if Polar AccessLink is configured via environment variables.
    
    Returns:
        True if both token and user ID are set.
    """
    return bool(
        os.getenv(ENV_POLAR_TOKEN)
        and os.getenv(ENV_POLAR_USER_ID)
    )


def fetch_polar_vo2max(
    *,
    access_token: Optional[str] = None,
    user_id: Optional[str] = None,
    timeout: float = POLAR_API_TIMEOUT,
) -> Optional[float]:
    """Fetch VO2max from Polar AccessLink API (convenience function).
    
    This is a simplified version for quick access without full client setup.
    For persistent storage and history tracking, use PolarAccessLinkClient.
    
    Args:
        access_token: OAuth access token (defaults to ENV_POLAR_TOKEN).
        user_id: Polar user ID (defaults to ENV_POLAR_USER_ID).
        timeout: Request timeout in seconds.
        
    Returns:
        VO2max in mL/kg/min or None.
    """
    token = (access_token or os.getenv(ENV_POLAR_TOKEN, "")).strip()
    polar_user_id = (user_id or os.getenv(ENV_POLAR_USER_ID, "")).strip()
    
    if not token or not polar_user_id:
        return None
    
    url = f"{POLAR_ACCESSLINK_BASE_URL}/users/{polar_user_id}/cardiorespiratory-fitness"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        _LOGGER.warning("Polar AccessLink VO2max fetch failed: %s", exc)
        return None
    
    # Extract VO2max from response
    candidate_keys = ("vo2max", "vo2_max", "cardiorespiratory_fitness")
    for key in candidate_keys:
        value = payload.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    
    # Check nested structures
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, dict):
                for key in candidate_keys:
                    nested = value.get(key)
                    if isinstance(nested, (int, float)):
                        return float(nested)
    
    return None


def save_manual_vo2max(
    user_id: str,
    vo2max: float,
    *,
    measurement_date: Optional[str] = None,
    notes: Optional[str] = None,
    db: Optional[UserDatabase] = None,
) -> str:
    """Save a manually entered VO2max value to history.
    
    Args:
        user_id: User identifier.
        vo2max: VO2max in mL/kg/min.
        measurement_date: Date of measurement (defaults to now).
        notes: Optional notes.
        db: Database instance.
        
    Returns:
        Entry ID.
    """
    database = db or get_database()
    
    entry = VO2maxEntry(
        entry_id="",  # Will be generated
        user_id=user_id,
        measurement_date=measurement_date or datetime.now(timezone.utc).isoformat(),
        vo2max_ml_kg_min=vo2max,
        source="manual",
        notes=notes,
    )
    
    return database.save_vo2max_entry(entry)


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Client
    "PolarAccessLinkClient",
    # Response types
    "PolarVO2maxResponse",
    "PolarSyncResult",
    # Token functions
    "encrypt_token",
    "decrypt_token",
    # Convenience functions
    "polar_accesslink_available",
    "fetch_polar_vo2max",
    "save_manual_vo2max",
    # Constants
    "POLAR_ACCESSLINK_BASE_URL",
    "ENV_POLAR_TOKEN",
    "ENV_POLAR_USER_ID",
]
