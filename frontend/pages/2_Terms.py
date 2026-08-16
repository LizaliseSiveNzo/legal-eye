"""Terms and conditions, including the ECTA s 43(1) supplier disclosures."""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent.parent))  # project root, for backend.*
sys.path.insert(0, str(_HERE.parent.parent))         # frontend/, for page_chrome

from backend.legal_pages import terms_markdown  # noqa: E402
from page_chrome import render_page  # noqa: E402

render_page("Terms", terms_markdown(), nav_note="Terms and conditions")
