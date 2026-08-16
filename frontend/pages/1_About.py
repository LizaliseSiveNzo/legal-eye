"""About Legal-Eye.

Each page repeats the sys.path fix from `streamlit_app.py` rather than relying
on it. In a Streamlit multipage app the main script does not run when a visitor
lands directly on a subpage, so a page opened from a bookmark or a link in a
delivered email would otherwise fail to import `backend.*`.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent.parent))  # project root, for backend.*
sys.path.insert(0, str(_HERE.parent.parent))         # frontend/, for page_chrome

from backend.legal_pages import about_markdown  # noqa: E402
from page_chrome import render_page  # noqa: E402

render_page("About", about_markdown(), nav_note="About Legal-Eye")
