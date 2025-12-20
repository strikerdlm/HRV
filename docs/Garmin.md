Plan for Garmin Connect to get the vivosmart 5 from Garmin

This repo = 

https://github.com/cyberjunky/python-garminconnect

Contains a python-garminconnect to get basic metrics about the day to get into the profile database:

## Quick setup (live import)

1) Set credentials in `.env` (or environment):
```
GARMIN_EMAIL=you@example.com
GARMIN_PASSWORD=your_password
```
2) Install dependency (already added to requirements):
```
pip install -r requirements.txt
```
3) In the app, go to **User Profile → Wrist Monitoring → Import from Garmin Connect**, pick a window (7/14/30 days), and click **Fetch from Garmin Connect**. Data stored per-user in `garmin_daily_metrics`:
- Steps, distance, calories, resting HR, stress
- Sleep: score/efficiency/duration + start/end timestamps
- HRV (rmssd/sdnn) when Garmin exposes it
- Respiration (awake/sleep), SpO₂
- Body Battery (avg/charge/drain)

4) SAFTE/Fatigue tab auto-fills sleep duration/quality and bedtime/waketime from the latest Garmin day (if enabled).



# Garth Migration

```
importgarminconnect
```

## Login

Request email and password. If MFA is enabled, Garth will request it.

```
fromgetpassimport getpass

email = input("Enter email address: ")
password = getpass("Enter password: ")

garmin = garminconnect.Garmin(email, password)
garmin.login()

garmin.display_name
```

Save session

```
importos

GARTH_HOME = os.getenv("GARTH_HOME", "~/.garth")
garmin.garth.dump(GARTH_HOME)
```

## Get Connect stats

```
fromdatetimeimport date, timedelta

yesterday = date.today() - timedelta(days=1)
yesterday = yesterday.isoformat()
yesterday
```

```
garmin.get_stats(yesterday).keys()
```

```
garmin.get_user_summary(yesterday).keys()
```

```
garmin.get_steps_data(yesterday)[:2]
```

```
garmin.get_floors(yesterday).keys()
```

```
garmin.get_daily_steps(yesterday, yesterday)
```

```
garmin.get_heart_rates(yesterday).keys()
```

```
garmin.get_stats_and_body(yesterday).keys()
```

```
garmin.get_body_composition(yesterday)
```

```
garmin.get_body_battery(yesterday)[0].keys()
```

```
garmin.get_blood_pressure(yesterday)
```

```
garmin.get_max_metrics(yesterday)
```

```
garmin.get_hydration_data(yesterday)
```

```
garmin.get_respiration_data(yesterday).keys()
```

```
garmin.get_spo2_data(yesterday).keys()
```

```
garmin.get_personal_record()[:2]
```

```
garmin.get_all_day_stress(yesterday)["bodyBatteryValuesArray"][:10]
```


And there are may other functions to get information:

Install

```
python3 -m pip install --upgrade pip
python3 -m pip install garminconnect
```


# 1. Create and activate a virtual environment

python3 -m venv .venv --copies
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install PDM (Python Dependency Manager)

pip install pdm

# 3. Install all development dependencies

pdm install --group :all

# 4. Install optional tools for enhanced development experience

pip install "black[jupyter]" codespell pre-commit

# 5. Setup pre-commit hooks (optional)

pre-commit install --install-hooks


# Install PDM via pipx (recommended for system-wide tools)

python3 -m pip install --user pipx
pipx install pdm

# Then proceed with project setup

pdm install --group :all

pdm run format      # Auto-format code (isort, black, ruff --fix)
pdm run lint        # Check code quality (isort, ruff, black, mypy)
pdm run codespell   # Check spelling errors (install codespell if needed)
pdm run test        # Run test suite
pdm run testcov     # Run tests with coverage report
pdm run all         # Run all checks
pdm run clean      # Clean build artifacts and cache files
pdm run build      # Build package for distribution
pdm run publish    # Build and publish to PyPI



**View all available commands:**

pdm run --list     # Display all available PDM scripts



## Authentication

[](https://github.com/cyberjunky/python-garminconnect/tree/master#-authentication)

The library uses the same OAuth authentication as the official Garmin Connect app via [Garth](https://github.com/matin/garth).

**Key Features:**

* Login credentials valid for one year (no repeated logins)
* Secure OAuth token storage
* Same authentication flow as official app

**Advanced Configuration:**

```python
# Optional: Custom OAuth consumer (before login)
import os
import garth
garth.sso.OAUTH_CONSUMER = {
    'key': os.getenv('GARTH_OAUTH_KEY', '<YOUR_KEY>'),
    'secret': os.getenv('GARTH_OAUTH_SECRET', '<YOUR_SECRET>'),
}
# Note: Set these env vars securely; placeholders are non-sensitive.
```

**Token Storage:** Tokens are automatically saved to `~/.garminconnect` directory for persistent authentication. For security, ensure restrictive permissions:

```shell
chmod 700 ~/.garminconnect
chmod 600 ~/.garminconnect/* 2>/dev/null || true
```

## 🧪 Testing

[](https://github.com/cyberjunky/python-garminconnect/tree/master#-testing)

Run the test suite to verify functionality:

**Prerequisites:**

Create tokens in ~/.garminconnect by running the example program.

```shell
# Install development dependencies
pdm install --group :all
```

**Run Tests:**

```shell
pdm run test        # Run all tests
pdm run testcov     # Run tests with coverage report
```

Optional: keep test tokens isolated

```shell
export GARMINTOKENS="$(mktemp -d)"
python3 ./example.py # create fresh tokens for tests
pdm run test
```

**Note:** Tests automatically use `~/.garminconnect` as the default token file location. You can override this by setting the `GARMINTOKENS` environment variable. Run `example.py` first to generate authentication tokens for testing.

**For Developers:** Tests use VCR cassettes to record/replay HTTP interactions. If tests fail with authentication errors, ensure valid tokens exist in `~/.garminconnect`

## 📦 Publishing

[](https://github.com/cyberjunky/python-garminconnect/tree/master#-publishing)

For package maintainers:

**Setup PyPI credentials:**

```shell
pip install twine
# Edit with your preferred editor, or create via here-doc:
# cat > ~/.pypirc <<'EOF'
# [pypi]
# username = __token__
# password = <PyPI_API_TOKEN>
# EOF
```

```ini
[pypi]
username = __token__
password = <PyPI_API_TOKEN>
```

Recommended: use environment variables and restrict file perms

```shell
chmod 600 ~/.pypirc
export TWINE_USERNAME="__token__"
export TWINE_PASSWORD="<PyPI_API_TOKEN>"
```

**Publish new version:**

```shell
pdm run publish    # Build and publish to PyPI
```

**Alternative publishing steps:**

```shell
pdm run build      # Build package only
pdm publish        # Publish pre-built package
```

Example Code


#!/usr/bin/env python3
"""
🏃‍♂️ Simple Garmin Connect API Example
==========================================

This example demonstrates the basic usage of python-garminconnect:

- Authentication with email/password
- Token storage and automatic reuse
- MFA (Multi-Factor Authentication) support
- Comprehensive error handling for all API calls
- Basic API calls for user stats

For a comprehensive demo of all available API calls, see demo.py

Dependencies:
pip3 install garth requests

Environment Variables (optional):
export EMAIL=`<your garmin email address>`
export PASSWORD=`<your garmin password>`
export GARMINTOKENS=`<path to token storage>`
"""

import logging
import os
import sys
from datetime import date
from getpass import getpass
from pathlib import Path

import requests
from garth.exc import GarthException, GarthHTTPError

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

# Suppress garminconnect library logging to avoid tracebacks in normal operation

logging.getLogger("garminconnect").setLevel(logging.CRITICAL)

def safe_api_call(api_method, *args, **kwargs):
    """
    Safe API call wrapper with comprehensive error handling.

    This demonstrates the error handling patterns used throughout the library.
    Returns (success: bool, result: Any, error_message: str)
    """
    try:
        result = api_method(*args, **kwargs)
        return True, result, None

    except GarthHTTPError as e:
        # Handle specific HTTP errors gracefully
        error_str = str(e)
        status_code = getattr(getattr(e, "response", None), "status_code", None)

    if status_code == 400 or "400" in error_str:
            return (
                False,
                None,
                "Endpoint not available (400 Bad Request) - Feature may not be enabled for your account",
            )
        elif status_code == 401 or "401" in error_str:
            return (
                False,
                None,
                "Authentication required (401 Unauthorized) - Please re-authenticate",
            )
        elif status_code == 403 or "403" in error_str:
            return (
                False,
                None,
                "Access denied (403 Forbidden) - Account may not have permission",
            )
        elif status_code == 404 or "404" in error_str:
            return (
                False,
                None,
                "Endpoint not found (404) - Feature may have been moved or removed",
            )
        elif status_code == 429 or "429" in error_str:
            return (
                False,
                None,
                "Rate limit exceeded (429) - Please wait before making more requests",
            )
        elif status_code == 500 or "500" in error_str:
            return (
                False,
                None,
                "Server error (500) - Garmin's servers are experiencing issues",
            )
        elif status_code == 503 or "503" in error_str:
            return (
                False,
                None,
                "Service unavailable (503) - Garmin's servers are temporarily unavailable",
            )
        else:
            return False, None, f"HTTP error: {e}"

    except FileNotFoundError:
        return (
            False,
            None,
            "No valid tokens found. Please login with your email/password to create new tokens.",
        )

    except GarminConnectAuthenticationError as e:
        return False, None, f"Authentication issue: {e}"

    except GarminConnectConnectionError as e:
        return False, None, f"Connection issue: {e}"

    except GarminConnectTooManyRequestsError as e:
        return False, None, f"Rate limit exceeded: {e}"

    except Exception as e:
        return False, None, f"Unexpected error: {e}"

def get_credentials():
    """Get email and password from environment or user input."""
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")

    if not email:
        email = input("Login email: ")
    if not password:
        password = getpass("Enter password: ")

    return email, password

def init_api() -> Garmin | None:
    """Initialize Garmin API with authentication and token management."""

    # Configure token storage
    tokenstore = os.getenv("GARMINTOKENS", "~/.garminconnect")
    tokenstore_path = Path(tokenstore).expanduser()

    print(f"🔐 Token storage: {tokenstore_path}")

    # Check if token files exist
    if tokenstore_path.exists():
        print("📄 Found existing token directory")
        token_files = list(tokenstore_path.glob("*.json"))
        if token_files:
            print(
                f"🔑 Found {len(token_files)} token file(s): {[f.name for f in token_files]}"
            )
        else:
            print("⚠️ Token directory exists but no token files found")
    else:
        print("📭 No existing token directory found")

    # First try to login with stored tokens
    try:
        print("🔄 Attempting to use saved authentication tokens...")
        garmin = Garmin()
        garmin.login(str(tokenstore_path))
        print("✅ Successfully logged in using saved tokens!")
        return garmin

    except (
        FileNotFoundError,
        GarthHTTPError,
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
    ):
        print("🔑 No valid tokens found. Requesting fresh login credentials.")

    # Loop for credential entry with retry on auth failure
    while True:
        try:
            # Get credentials
            email, password = get_credentials()

    print("� Logging in with credentials...")
            garmin = Garmin(
                email=email, password=password, is_cn=False, return_on_mfa=True
            )
            result1, result2 = garmin.login()

    if result1 == "needs_mfa":
                print("🔐 Multi-factor authentication required")

    mfa_code = input("Please enter your MFA code: ")
                print("🔄 Submitting MFA code...")

    try:
                    garmin.resume_login(result2, mfa_code)
                    print("✅ MFA authentication successful!")

    except GarthHTTPError as garth_error:
                    # Handle specific HTTP errors from MFA
                    error_str = str(garth_error)
                    if "429" in error_str and "Too Many Requests" in error_str:
                        print("❌ Too many MFA attempts")
                        print("💡 Please wait 30 minutes before trying again")
                        sys.exit(1)
                    elif "401" in error_str or "403" in error_str:
                        print("❌ Invalid MFA code")
                        print("💡 Please verify your MFA code and try again")
                        continue
                    else:
                        # Other HTTP errors - don't retry
                        print(f"❌ MFA authentication failed: {garth_error}")
                        sys.exit(1)

    except GarthException as garth_error:
                    print(f"❌ MFA authentication failed: {garth_error}")
                    print("💡 Please verify your MFA code and try again")
                    continue

    # Save tokens for future use
            garmin.garth.dump(str(tokenstore_path))
            print(f"💾 Authentication tokens saved to: {tokenstore_path}")
            print("✅ Login successful!")
            return garmin

    except GarminConnectAuthenticationError:
            print("❌ Authentication failed:")
            print("💡 Please check your username and password and try again")
            # Continue the loop to retry
            continue

    except (
            FileNotFoundError,
            GarthHTTPError,
            GarminConnectConnectionError,
            requests.exceptions.HTTPError,
        ) as err:
            print(f"❌ Connection error: {err}")
            print("💡 Please check your internet connection and try again")
            return None

    except KeyboardInterrupt:
            print("\n👋 Cancelled by user")
            return None

def display_user_info(api: Garmin):
    """Display basic user information with proper error handling."""
    print("\n" + "=" * 60)
    print("👤 User Information")
    print("=" * 60)

    # Get user's full name
    success, full_name, error_msg = safe_api_call(api.get_full_name)
    if success:
        print(f"📝 Name: {full_name}")
    else:
        print(f"📝 Name: ⚠️ {error_msg}")

    # Get user profile number from device info
    success, device_info, error_msg = safe_api_call(api.get_device_last_used)
    if success and device_info and device_info.get("userProfileNumber"):
        user_profile_number = device_info.get("userProfileNumber")
        print(f"🆔 Profile Number: {user_profile_number}")
    else:
        if not success:
            print(f"🆔 Profile Number: ⚠️ {error_msg}")
        else:
            print("🆔 Profile Number: Not available")

def display_daily_stats(api: Garmin):
    """Display today's activity statistics with proper error handling."""
    today = date.today().isoformat()

    print("\n" + "=" * 60)
    print(f"📊 Daily Stats for {today}")
    print("=" * 60)

    # Get user summary (steps, calories, etc.)
    success, summary, error_msg = safe_api_call(api.get_user_summary, today)
    if success and summary:
        steps = summary.get("totalSteps", 0)
        distance = summary.get("totalDistanceMeters", 0) / 1000  # Convert to km
        calories = summary.get("totalKilocalories", 0)
        floors = summary.get("floorsClimbed", 0)

    print(f"👣 Steps: {steps:,}")
        print(f"📏 Distance: {distance:.2f} km")
        print(f"🔥 Calories: {calories}")
        print(f"🏢 Floors: {floors}")

    # Fun motivation based on steps
        if steps < 5000:
            print("🐌 Time to get those legs moving!")
        elif steps > 15000:
            print("🏃‍♂️ You're crushing it today!")
        else:
            print("👍 Nice progress! Keep it up!")
    else:
        if not success:
            print(f"⚠️ Could not fetch daily stats: {error_msg}")
        else:
            print("⚠️ No activity summary available for today")

    # Get hydration data
    success, hydration, error_msg = safe_api_call(api.get_hydration_data, today)
    if success and hydration and hydration.get("valueInML"):
        hydration_ml = int(hydration.get("valueInML", 0))
        hydration_goal = hydration.get("goalInML", 0)
        hydration_cups = round(hydration_ml / 240, 1)  # 240ml = 1 cup

    print(f"💧 Hydration: {hydration_ml}ml ({hydration_cups} cups)")

    if hydration_goal > 0:
            hydration_percent = round((hydration_ml / hydration_goal) * 100)
            print(f"🎯 Goal Progress: {hydration_percent}% of {hydration_goal}ml")
    else:
        if not success:
            print(f"💧 Hydration: ⚠️ {error_msg}")
        else:
            print("💧 Hydration: No data available")

def main():
    """Main example demonstrating basic Garmin Connect API usage."""
    print("🏃‍♂️ Simple Garmin Connect API Example")
    print("=" * 60)

    # Initialize API with authentication (will only prompt for credentials if needed)
    api = init_api()

    if not api:
        print("❌ Failed to initialize API. Exiting.")
        return

    # Display user information
    display_user_info(api)

    # Display daily statistics
    display_daily_stats(api)

    print("\n" + "=" * 60)
    print("✅ Example completed successfully!")
    print("💡 For a comprehensive demo of all API features, run: python demo.py")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🚪 Exiting example. Goodbye! 👋")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
