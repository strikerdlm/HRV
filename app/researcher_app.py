from __future__ import annotations

"""
Compatibility Streamlit entrypoint.

Some environments/machines have used `app/researcher_app.py` as the Research UI
launch file. The canonical entrypoint is `app/research_app.py`.

This wrapper keeps behavior identical across machines without changing Streamlit
defaults or relying on external path conventions.
"""

import sys
from pathlib import Path


def _ensure_import_paths() -> None:
    """Ensure repo-root + app/ are on sys.path in a deterministic order.

    Streamlit's sys.path can vary depending on how the app is launched.
    We need this setup before importing research_app to avoid ModuleNotFoundError.
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


# Configure sys.path BEFORE importing research_app to avoid ModuleNotFoundError
_ensure_import_paths()

from research_app import main  # noqa: PLC0415


if __name__ == "__main__":
    main()


