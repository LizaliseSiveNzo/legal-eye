"""Privacy notice, given under section 18 of POPIA."""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent.parent))  # project root, for backend.*
sys.path.insert(0, str(_HERE.parent.parent))         # frontend/, for page_chrome

from backend.legal_pages import privacy_markdown  # noqa: E402
from page_chrome import render_page  # noqa: E402

render_page("Privacy", privacy_markdown(), nav_note="Privacy notice (POPIA)")
