"""
Unit tests for Polar AccessLink integration.

Tests:
- Token encryption/decryption
- PolarCredentials database operations
- VO2maxEntry database operations
- PolarAccessLinkClient functionality

Author: Dr. Diego Leonel Malpica Hincapié, MD
"""

from __future__ import annotations

import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

# Add app directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import directly from modules (not via app package to avoid import chains)
from user_database import (
    UserDatabase,
    UserProfile,
    PolarCredentials,
    VO2maxEntry,
)
from polar_accesslink import (
    PolarAccessLinkClient,
    PolarVO2maxResponse,
    PolarSyncResult,
    encrypt_token,
    decrypt_token,
    polar_accesslink_available,
    fetch_polar_vo2max,
    save_manual_vo2max,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_db() -> Generator[UserDatabase, None, None]:
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_polar.db"
        db = UserDatabase(db_path)
        yield db


@pytest.fixture
def test_user(temp_db: UserDatabase) -> UserProfile:
    """Create a test user in the database."""
    profile = UserProfile(
        user_id=str(uuid.uuid4()),
        username=f"testuser_{uuid.uuid4().hex[:8]}",
        full_name="Test User",
        email="test@example.com",
        date_of_birth="1985-06-15",
        sex="male",
        height_cm=175.0,
        weight_kg=70.0,
        vo2max_ml_kg_min=45.0,
    )
    temp_db.create_user(profile)
    return profile


# ---------------------------------------------------------------------------
# Token Encryption Tests
# ---------------------------------------------------------------------------

class TestTokenEncryption:
    """Tests for token encryption and decryption."""
    
    def test_encrypt_decrypt_roundtrip(self) -> None:
        """Test that encryption and decryption are inverses."""
        original = "test_access_token_xyz123"
        encrypted = encrypt_token(original)
        decrypted = decrypt_token(encrypted)
        assert decrypted == original
    
    def test_encrypt_empty_string(self) -> None:
        """Test encryption of empty string."""
        assert encrypt_token("") == ""
        assert decrypt_token("") == ""
    
    def test_encrypt_unicode(self) -> None:
        """Test encryption of unicode strings."""
        original = "token_with_émoji_🔑"
        encrypted = encrypt_token(original)
        decrypted = decrypt_token(encrypted)
        assert decrypted == original
    
    def test_encrypted_is_different(self) -> None:
        """Test that encrypted value differs from original."""
        original = "secret_token"
        encrypted = encrypt_token(original)
        # Encrypted should be base64, not contain original
        assert original not in encrypted
        assert encrypted != original
    
    def test_decrypt_invalid_base64(self) -> None:
        """Test decryption of invalid base64."""
        result = decrypt_token("not_valid_base64!!!")
        assert result == ""
    
    def test_different_tokens_different_encrypted(self) -> None:
        """Test that different tokens produce different encrypted values."""
        token1 = "token_one"
        token2 = "token_two"
        enc1 = encrypt_token(token1)
        enc2 = encrypt_token(token2)
        assert enc1 != enc2


# ---------------------------------------------------------------------------
# Database Operations Tests
# ---------------------------------------------------------------------------

class TestPolarCredentialsDatabase:
    """Tests for PolarCredentials database operations."""
    
    def test_save_and_get_credentials(
        self,
        temp_db: UserDatabase,
        test_user: UserProfile,
    ) -> None:
        """Test saving and retrieving Polar credentials."""
        creds = PolarCredentials(
            credential_id="",
            user_id=test_user.user_id,
            polar_user_id="polar_123456",
            access_token_encrypted=encrypt_token("access_token_xyz"),
            refresh_token_encrypted=encrypt_token("refresh_token_abc"),
            sync_enabled=True,
        )
        
        cred_id = temp_db.save_polar_credentials(creds)
        assert cred_id is not None
        
        # Retrieve and verify
        retrieved = temp_db.get_polar_credentials(test_user.user_id)
        assert retrieved is not None
        assert retrieved.user_id == test_user.user_id
        assert retrieved.polar_user_id == "polar_123456"
        assert retrieved.sync_enabled is True
        
        # Decrypt and verify tokens
        assert decrypt_token(retrieved.access_token_encrypted) == "access_token_xyz"
        assert decrypt_token(retrieved.refresh_token_encrypted) == "refresh_token_abc"
    
    def test_update_credentials(
        self,
        temp_db: UserDatabase,
        test_user: UserProfile,
    ) -> None:
        """Test updating existing credentials."""
        # Save initial
        creds = PolarCredentials(
            credential_id="",
            user_id=test_user.user_id,
            polar_user_id="polar_old",
            access_token_encrypted=encrypt_token("old_token"),
        )
        temp_db.save_polar_credentials(creds)
        
        # Update with new values
        creds.polar_user_id = "polar_new"
        creds.access_token_encrypted = encrypt_token("new_token")
        temp_db.save_polar_credentials(creds)
        
        # Verify update
        retrieved = temp_db.get_polar_credentials(test_user.user_id)
        assert retrieved.polar_user_id == "polar_new"
        assert decrypt_token(retrieved.access_token_encrypted) == "new_token"
    
    def test_delete_credentials(
        self,
        temp_db: UserDatabase,
        test_user: UserProfile,
    ) -> None:
        """Test deleting credentials."""
        creds = PolarCredentials(
            credential_id="",
            user_id=test_user.user_id,
            polar_user_id="polar_123",
            access_token_encrypted=encrypt_token("token"),
        )
        temp_db.save_polar_credentials(creds)
        
        # Verify exists
        assert temp_db.get_polar_credentials(test_user.user_id) is not None
        
        # Delete
        result = temp_db.delete_polar_credentials(test_user.user_id)
        assert result is True
        
        # Verify deleted
        assert temp_db.get_polar_credentials(test_user.user_id) is None
    
    def test_get_nonexistent_credentials(
        self,
        temp_db: UserDatabase,
    ) -> None:
        """Test getting credentials for non-existent user."""
        result = temp_db.get_polar_credentials("nonexistent_user_id")
        assert result is None


class TestVO2maxHistoryDatabase:
    """Tests for VO2max history database operations."""
    
    def test_save_and_get_vo2max_entry(
        self,
        temp_db: UserDatabase,
        test_user: UserProfile,
    ) -> None:
        """Test saving and retrieving VO2max entry."""
        entry = VO2maxEntry(
            entry_id="",
            user_id=test_user.user_id,
            measurement_date=datetime.now(timezone.utc).isoformat(),
            vo2max_ml_kg_min=48.5,
            source="polar",
            polar_fitness_class="Good",
            notes="Test entry",
        )
        
        entry_id = temp_db.save_vo2max_entry(entry)
        assert entry_id is not None
        
        # Retrieve and verify
        history = temp_db.get_vo2max_history(test_user.user_id)
        assert len(history) == 1
        assert history[0].vo2max_ml_kg_min == 48.5
        assert history[0].source == "polar"
        assert history[0].polar_fitness_class == "Good"
    
    def test_get_latest_vo2max(
        self,
        temp_db: UserDatabase,
        test_user: UserProfile,
    ) -> None:
        """Test getting most recent VO2max entry."""
        # Save multiple entries
        for i, vo2 in enumerate([45.0, 47.0, 50.0]):
            entry = VO2maxEntry(
                entry_id="",
                user_id=test_user.user_id,
                measurement_date=f"2025-01-0{i+1}T12:00:00Z",
                vo2max_ml_kg_min=vo2,
                source="manual",
            )
            temp_db.save_vo2max_entry(entry)
        
        latest = temp_db.get_latest_vo2max(test_user.user_id)
        assert latest is not None
        # Should be most recent (highest date, which has VO2 = 50.0)
        assert latest.vo2max_ml_kg_min == 50.0
    
    def test_vo2max_history_order(
        self,
        temp_db: UserDatabase,
        test_user: UserProfile,
    ) -> None:
        """Test that history is ordered by date descending."""
        dates = ["2025-01-01", "2025-01-15", "2025-01-10"]
        for date_str in dates:
            entry = VO2maxEntry(
                entry_id="",
                user_id=test_user.user_id,
                measurement_date=f"{date_str}T12:00:00Z",
                vo2max_ml_kg_min=45.0,
                source="manual",
            )
            temp_db.save_vo2max_entry(entry)
        
        history = temp_db.get_vo2max_history(test_user.user_id)
        assert len(history) == 3
        # Should be: 15th, 10th, 1st (descending)
        assert "01-15" in history[0].measurement_date
        assert "01-10" in history[1].measurement_date
        assert "01-01" in history[2].measurement_date
    
    def test_vo2max_dataframe(
        self,
        temp_db: UserDatabase,
        test_user: UserProfile,
    ) -> None:
        """Test getting VO2max history as DataFrame."""
        for vo2 in [45.0, 47.0, 50.0]:
            entry = VO2maxEntry(
                entry_id="",
                user_id=test_user.user_id,
                measurement_date=datetime.now(timezone.utc).isoformat(),
                vo2max_ml_kg_min=vo2,
                source="polar",
            )
            temp_db.save_vo2max_entry(entry)
        
        df = temp_db.get_vo2max_dataframe(test_user.user_id)
        assert len(df) == 3
        assert "vo2max_ml_kg_min" in df.columns
        assert "source" in df.columns
        assert "measurement_date" in df.columns


# ---------------------------------------------------------------------------
# PolarAccessLinkClient Tests
# ---------------------------------------------------------------------------

class TestPolarAccessLinkClient:
    """Tests for PolarAccessLinkClient."""
    
    def test_client_initialization(
        self,
        temp_db: UserDatabase,
        test_user: UserProfile,
    ) -> None:
        """Test client initialization."""
        client = PolarAccessLinkClient(test_user.user_id, db=temp_db)
        assert client.user_id == test_user.user_id
        assert client.db is temp_db
    
    def test_has_credentials_false(
        self,
        temp_db: UserDatabase,
        test_user: UserProfile,
    ) -> None:
        """Test has_credentials returns False when none stored."""
        client = PolarAccessLinkClient(test_user.user_id, db=temp_db)
        assert client.has_credentials() is False
    
    def test_save_and_check_credentials(
        self,
        temp_db: UserDatabase,
        test_user: UserProfile,
    ) -> None:
        """Test saving credentials via client."""
        client = PolarAccessLinkClient(test_user.user_id, db=temp_db)
        
        client.save_credentials(
            access_token="test_token",
            polar_user_id="polar_12345",
            refresh_token="refresh_xyz",
        )
        
        assert client.has_credentials() is True
        assert client.get_access_token() == "test_token"
        assert client.get_polar_user_id() == "polar_12345"
    
    def test_clear_credentials(
        self,
        temp_db: UserDatabase,
        test_user: UserProfile,
    ) -> None:
        """Test clearing credentials."""
        client = PolarAccessLinkClient(test_user.user_id, db=temp_db)
        
        client.save_credentials(
            access_token="test_token",
            polar_user_id="polar_12345",
        )
        
        assert client.has_credentials() is True
        client.clear_credentials()
        assert client.has_credentials() is False
    
    def test_fetch_vo2max_not_configured(
        self,
        temp_db: UserDatabase,
        test_user: UserProfile,
    ) -> None:
        """Test fetch_vo2max when not configured."""
        client = PolarAccessLinkClient(test_user.user_id, db=temp_db)
        response = client.fetch_vo2max()
        assert response.is_valid is False
    
    @patch("polar_accesslink.requests.get")
    def test_fetch_vo2max_success(
        self,
        mock_get: MagicMock,
        temp_db: UserDatabase,
        test_user: UserProfile,
    ) -> None:
        """Test successful VO2max fetch with mocked API."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"vo2max": 52.5}
        mock_get.return_value = mock_response
        
        # Save credentials
        client = PolarAccessLinkClient(test_user.user_id, db=temp_db)
        client.save_credentials(
            access_token="valid_token",
            polar_user_id="polar_user",
        )
        
        # Fetch
        response = client.fetch_vo2max()
        assert response.is_valid is True
        assert response.vo2max == 52.5
    
    @patch("polar_accesslink.requests.get")
    def test_sync_vo2max_saves_entry(
        self,
        mock_get: MagicMock,
        temp_db: UserDatabase,
        test_user: UserProfile,
    ) -> None:
        """Test that sync_vo2max saves entry to history."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"vo2max": 55.0}
        mock_get.return_value = mock_response
        
        client = PolarAccessLinkClient(test_user.user_id, db=temp_db)
        client.save_credentials(
            access_token="valid_token",
            polar_user_id="polar_user",
        )
        
        result = client.sync_vo2max()
        assert result.success is True
        assert result.vo2max == 55.0
        assert result.entries_saved == 1
        
        # Verify saved to history
        history = client.get_vo2max_history()
        assert len(history) == 1
        assert history[0].vo2max_ml_kg_min == 55.0
        assert history[0].source == "polar"


# ---------------------------------------------------------------------------
# Convenience Function Tests
# ---------------------------------------------------------------------------

class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    def test_polar_accesslink_available_false(self) -> None:
        """Test availability check when not configured."""
        # Clear env vars
        with patch.dict(os.environ, {}, clear=True):
            assert polar_accesslink_available() is False
    
    def test_polar_accesslink_available_true(self) -> None:
        """Test availability check when configured."""
        with patch.dict(os.environ, {
            "POLAR_ACCESSLINK_TOKEN": "token",
            "POLAR_ACCESSLINK_USER_ID": "user",
        }):
            assert polar_accesslink_available() is True
    
    def test_save_manual_vo2max(
        self,
        temp_db: UserDatabase,
        test_user: UserProfile,
    ) -> None:
        """Test saving manual VO2max entry."""
        entry_id = save_manual_vo2max(
            user_id=test_user.user_id,
            vo2max=42.5,
            notes="Manual fitness test",
            db=temp_db,
        )
        
        assert entry_id is not None
        
        # Verify saved
        history = temp_db.get_vo2max_history(test_user.user_id)
        assert len(history) == 1
        assert history[0].vo2max_ml_kg_min == 42.5
        assert history[0].source == "manual"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
