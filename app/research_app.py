from __future__ import annotations

# Research Streamlit entrypoint (full dashboards).
#
# Run:
#   streamlit run app/research_app.py

import os


_ENV_SKIP_PAGE_CONFIG = "HRV_SKIP_STREAMLIT_PAGE_CONFIG"
_ENV_APP_MODE = "HRV_APP_MODE"


def main() -> None:
    # This entrypoint delegates all UI and Streamlit configuration to `app/app.py`.
    # We keep this wrapper minimal to avoid Streamlit's `set_page_config` ordering
    # constraints being violated by import-time Streamlit usage in submodules.
    os.environ[_ENV_SKIP_PAGE_CONFIG] = "0"
    os.environ[_ENV_APP_MODE] = "research"

    # When running Streamlit from inside `app/`, `import app` resolves to `app/app.py`
    # (not the package). That module defines `main()`.
    import app as research_app  # noqa: PLC0415

    research_app.main()


if __name__ == "__main__":
    main()


