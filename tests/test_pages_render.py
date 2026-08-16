"""The pages behind the footer links actually render.

This is the test that would have caught the original bug. The footer pointed at
legal-eye.co.za, a domain with no DNS record, so all three links dead-ended —
and nothing in the suite noticed, because no test had ever loaded a page.

Streamlit is a single-page app: the server answers *every* path with the same
shell HTML, so an HTTP 200 proves nothing about whether a route exists. These
tests use Streamlit's own AppTest harness, which executes the page script and
exposes what it rendered.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit", reason="Streamlit is not installed")

from streamlit.testing.v1 import AppTest  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = PROJECT_ROOT / "frontend" / "pages"

# Filename -> the route Streamlit derives from it, and a phrase that must appear.
CASES = [
    ("1_About.py", "/About", "About Legal-Eye"),
    ("2_Terms.py", "/Terms", "Terms and conditions"),
    ("3_Privacy.py", "/Privacy", "Privacy notice"),
]


def render(filename: str) -> str:
    at = AppTest.from_file(str(PAGES_DIR / filename), default_timeout=60).run()
    assert not at.exception, f"{filename} raised: {[e.value for e in at.exception]}"
    return "\n".join(block.value for block in at.markdown)


@pytest.mark.parametrize("filename,route,phrase", CASES)
def test_page_renders_real_content(filename, route, phrase):
    body = render(filename)
    assert phrase in body
    assert len(body) > 2000, "page rendered but is suspiciously short"


@pytest.mark.parametrize("filename,route,phrase", CASES)
def test_page_carries_no_unfilled_placeholder(filename, route, phrase):
    assert "[[" not in render(filename)


def test_every_page_file_is_reachable_as_a_route():
    """Guard against a page being added to pages/ but never linked, or renamed."""
    on_disk = {p.name for p in PAGES_DIR.glob("*.py")}
    expected = {filename for filename, _, _ in CASES}
    assert on_disk == expected, (
        "pages/ and this test have drifted apart; update CASES so new pages "
        "are covered and linked from the footer"
    )


def test_footer_links_point_at_those_routes():
    """The bug was here: three anchors at a domain that does not resolve."""
    app = (PROJECT_ROOT / "frontend" / "streamlit_app.py").read_text(
        encoding="utf-8")

    for _, route, _ in CASES:
        assert f'href="{route}"' in app, f"footer no longer links to {route}"

    assert "legal-eye.co.za" not in app, (
        "the footer points at legal-eye.co.za again, which has no DNS record"
    )
