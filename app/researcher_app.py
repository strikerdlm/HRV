from __future__ import annotations

"""
Compatibility Streamlit entrypoint.

Some environments/machines have used `app/researcher_app.py` as the Research UI
launch file. The canonical entrypoint is `app/research_app.py`.

This wrapper keeps behavior identical across machines without changing Streamlit
defaults or relying on external path conventions.
"""

from research_app import main


if __name__ == "__main__":
    main()


