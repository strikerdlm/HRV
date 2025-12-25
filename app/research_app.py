from __future__ import annotations

# Research Streamlit entrypoint (full dashboards).
#
# Run:
#   streamlit run app/research_app.py

import os
import sys
from pathlib import Path


_ENV_SKIP_PAGE_CONFIG = "HRV_SKIP_STREAMLIT_PAGE_CONFIG"
_ENV_APP_MODE = "HRV_APP_MODE"


def _ensure_import_paths() -> None:
    """Ensure repo-root + app/ are on sys.path in a deterministic order.

    Streamlit's sys.path can vary depending on how the app is launched.
    We want `from app import app as research_app` to always resolve to the
    `app/app.py` module (not the `app/` package itself or an ambiguous import).
    """

    app_dir = Path(__file__).resolve().parent
    repo_root = app_dir.parent

    app_str = str(app_dir)
    root_str = str(repo_root)

    # Remove existing occurrences so we can reinsert in a stable order.
    sys.path[:] = [p for p in sys.path if p not in (root_str, app_str)]
    # Prefer repo root so `app` resolves as a package, then keep app/ so
    # intra-app absolute imports (e.g., `import hrv_core`) continue to work.
    sys.path.insert(0, root_str)
    sys.path.insert(1, app_str)


def main() -> None:
    # This entrypoint delegates all UI and Streamlit configuration to `app/app.py`.
    # We keep this wrapper minimal to avoid Streamlit's `set_page_config` ordering
    # constraints being violated by import-time Streamlit usage in submodules.
    _ensure_import_paths()
    os.environ[_ENV_SKIP_PAGE_CONFIG] = "0"
    os.environ[_ENV_APP_MODE] = "research"

    # Import the research UI entrypoint explicitly.
    # - `app` is the package (`app/__init__.py`)
    # - `app.app` is the Streamlit UI module (`app/app.py`)
    from app import app as research_app  # noqa: PLC0415

    research_app.main()


if __name__ == "__main__":
    main()


