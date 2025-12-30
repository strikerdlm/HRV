"""Portable environment variable loader that works across different computers.

This module provides a deterministic way to locate and load the .env file from
the project root, regardless of the machine's username or absolute path structure.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

_ENV_LOADED = False

# Optional override for locating the .env file (absolute or relative path)
_ENV_PATH_OVERRIDE_VAR = "HRV_DOTENV_PATH"


def find_project_root(*, start_path: Optional[Path] = None) -> Optional[Path]:
    """Find the project root directory by searching for marker files.

    Searches upward from the start path until it finds a directory containing
    one or more project marker files (e.g., .env, README.md, requirements.txt).

    Args:
        start_path: Path to start searching from. Defaults to this file's directory.

    Returns:
        Path to project root, or None if not found within 10 parent levels.
    """
    if start_path is None:
        start_path = Path(__file__).resolve().parent

    # Project marker files that indicate the root directory
    markers = {".env", "README.md", "requirements.txt", "pyproject.toml", ".git"}

    current = start_path
    max_depth = 10  # Safety bound to prevent infinite loops

    for _ in range(max_depth):
        # Check if any marker file exists in the current directory
        if any((current / marker).exists() for marker in markers):
            return current

        # Move up one directory
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    return None


def load_env_file(*, env_path: Optional[Path] = None, verbose: bool = False) -> bool:
    """Load environment variables from a .env file.

    This function is portable across computers because it does not hardcode
    machine-specific absolute paths.

    Resolution order:
    1) Explicit `env_path` argument (if provided)
    2) Environment variable override `HRV_DOTENV_PATH`
    3) Auto-detect project root and use `<root>/.env`

    The function is idempotent: calling multiple times will not reload the file.

    Args:
        env_path: Optional explicit path to .env file.
        verbose: If True, prints diagnostic messages.

    Returns:
        True if a .env file was found and loaded, False otherwise.

    Raises:
        ImportError: If python-dotenv is not installed.
    """
    global _ENV_LOADED

    if _ENV_LOADED:
        if verbose:
            print("Environment already loaded, skipping reload")
        return True

    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        msg = "python-dotenv is required. Install via: pip install python-dotenv"
        raise ImportError(msg) from exc

    if env_path is None:
        override_raw = os.environ.get(_ENV_PATH_OVERRIDE_VAR, "").strip()
        if override_raw:
            candidate = Path(override_raw).expanduser()
            # If a relative override is provided, resolve it against CWD.
            if not candidate.is_absolute():
                candidate = (Path.cwd() / candidate).resolve()
            env_path = candidate

    if env_path is None:
        project_root = find_project_root()
        if project_root is None:
            if verbose:
                print("Could not locate project root; .env file not loaded")
            return False
        env_path = project_root / ".env"

    if not env_path.exists():
        if verbose:
            print(f".env file not found at: {env_path}")
        return False

    # Load the .env file
    load_dotenv(dotenv_path=env_path, override=False)
    _ENV_LOADED = True

    if verbose:
        print(f"Loaded .env from: {env_path}")

    return True


def get_env_variable(
    name: str,
    *,
    default: Optional[str] = None,
    required: bool = False,
) -> Optional[str]:
    """Get an environment variable with optional validation.

    Args:
        name: Environment variable name.
        default: Default value if variable is not set.
        required: If True, raises ValueError when variable is not set.

    Returns:
        Variable value, default value, or None.

    Raises:
        ValueError: If required=True and variable is not set.
    """
    # Ensure .env is loaded
    load_env_file()

    value = os.environ.get(name)
    if value is not None:
        return value.strip()

    if required:
        msg = f"Required environment variable '{name}' is not set"
        raise ValueError(msg)

    return default
