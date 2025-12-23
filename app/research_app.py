from __future__ import annotations

"""
Research Streamlit entrypoint (full dashboards).

This wrapper exists so the repo exposes two explicit entrypoints:
- Operational: `streamlit run app/operational_app.py`
- Research:    `streamlit run app/research_app.py`

The underlying implementation remains in `app/app.py` (historic entrypoint).
"""

import os


_ENV_SKIP_PAGE_CONFIG = "HRV_SKIP_STREAMLIT_PAGE_CONFIG"


def main() -> None:
    # This entrypoint delegates all UI and Streamlit configuration to `app/app.py`.
    # We keep this wrapper minimal to avoid Streamlit's `set_page_config` ordering
    # constraints being violated by import-time Streamlit usage in submodules.
    os.environ[_ENV_SKIP_PAGE_CONFIG] = "0"

    # When running Streamlit from inside `app/`, `import app` resolves to `app/app.py`
    # (not the package). That module defines `main()`.
    import app as research_app  # noqa: PLC0415

    research_app.main()


if __name__ == "__main__":
    main()


