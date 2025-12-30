from __future__ import annotations

import os
import sys
from pathlib import Path

# This is a manual setup script (interactive login). It is not meant to run as part
# of an automated pytest suite.
if __name__ != "__main__":
    try:
        import pytest

        pytest.skip(
            "Manual Garmin Connect login script; not part of automated tests.",
            allow_module_level=True,
        )
    except ImportError:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"

# Ensure app modules are importable (consistent with other tests)
for path_str in (str(APP_ROOT), str(PROJECT_ROOT)):
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

# Load .env from project root in a portable way (works across computers)
try:
    from env_loader import load_env_file

    load_env_file()
except ImportError:
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)
    except ImportError:
        pass

from garminconnect import Garmin

# Get credentials from environment
email = os.getenv("GARMIN_EMAIL", "").strip()
password = os.getenv("GARMIN_PASSWORD", "").strip()
tokenstore_path = str(Path.home() / ".garminconnect")

if not email or not password:
    print("Error: GARMIN_EMAIL and GARMIN_PASSWORD must be set (in .env or environment).")
    raise SystemExit(1)

print("Logging in to Garmin Connect...")
print(f"Tokens will be saved to: {tokenstore_path}")

# Create client with MFA support
garmin = Garmin(email=email, password=password, is_cn=False, return_on_mfa=True)
result1, result2 = garmin.login()

# Handle MFA if required
if result1 == "needs_mfa":
    print("Multi-factor authentication required")
    mfa_code = input("Please enter your MFA code: ")
    print("Submitting MFA code...")
    garmin.resume_login(result2, mfa_code)
    print("MFA authentication successful")
else:
    print("Login successful")

# Save tokens for future use
garmin.garth.dump(tokenstore_path)
print(f"Authentication tokens saved to: {tokenstore_path}")
print("Setup complete - tokens are now available for the app")
