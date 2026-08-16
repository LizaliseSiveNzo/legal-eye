"""Shared chrome for the About, Terms and Privacy pages.

The three pages are all the same shape — a header bar, a column of prose, a
footer — so the styling lives here rather than being pasted into each one. The
tokens match `streamlit_app.py`: ink #14283c, slate #44536a, muted #67748a on
paper #f5f7fa, brass #a6782f decorative and #8a6427 for text, Georgia for
display type.

The CSS deliberately targets plain elements inside `.block-container` rather
than a wrapper `<div>`. Streamlit renders every `st.markdown` call into its own
DOM container, so an opening tag emitted in one call and a closing tag in
another do not wrap what sits between them, and a wrapper class never matches.
These pages contain nothing but our own prose, so styling the elements directly
is both simpler and more reliable.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

SCALES = (
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
    'stroke-linejoin="round"><path d="M12 4v15"/><path d="M7 21h10"/>'
    '<path d="M12 6l-6 7h12l-6-7z"/><path d="M5 17h14"/></svg>'
)

_CSS = """
<style>
  .block-container { max-width: 880px; padding-top: 1.5rem; }

  .le-bar {
    display:flex; align-items:center; gap:12px; flex-wrap:wrap;
    border-bottom:1px solid #dfe5ee; padding-bottom:14px; margin-bottom:8px;
  }
  .le-brand {
    display:inline-flex; align-items:center; gap:8px;
    font-family:Georgia,'Times New Roman',serif; letter-spacing:.14em;
    font-size:.95rem; color:#14283c; font-weight:700;
  }
  .le-note { color:#67748a; font-size:.82rem; margin-left:auto; }

  .block-container h1 {
    font-family:Georgia,'Times New Roman',serif; color:#14283c;
    font-size:2rem; margin:.4rem 0 1rem; font-weight:700;
  }
  .block-container h2 {
    font-family:Georgia,'Times New Roman',serif; color:#14283c;
    font-size:1.25rem; margin:2rem 0 .6rem;
    border-top:1px solid #e6ebf2; padding-top:1.2rem; font-weight:700;
  }
  .block-container h3 { color:#44536a; font-size:1rem; margin:1.4rem 0 .4rem; }
  .block-container p, .block-container li { color:#44536a; line-height:1.65; }

  .block-container table { width:100%; border-collapse:collapse; margin:1rem 0; font-size:.86rem; }
  .block-container thead th {
    text-align:left; background:#eef2f7; color:#14283c;
    padding:8px 10px; border:1px solid #dfe5ee; font-weight:600;
  }
  .block-container tbody td {
    padding:8px 10px; border:1px solid #dfe5ee; color:#44536a; vertical-align:top;
  }

  .block-container blockquote {
    background:#fbf7ef; border-left:3px solid #a6782f; margin:1.1rem 0;
    padding:.85rem 1rem; border-radius:0 6px 6px 0;
  }
  .block-container blockquote p { color:#5a4a2c; margin:.3rem 0; }
  .block-container a { color:#8a6427; }

  .le-footer {
    margin-top:40px; border-top:1px solid #dfe5ee; padding-top:18px;
    color:#67748a; font-size:.82rem;
  }
  .le-footer a { color:#8a6427; margin-right:16px; }
</style>
"""


def render_page(title: str, body_markdown: str, nav_note: str = "") -> None:
    """Draw one legal page: header bar, prose, footer with cross-links."""
    st.set_page_config(
        page_title=f"{title} | Legal-Eye",
        page_icon="⚖️",
        layout="centered",
    )
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(
        f'<div class="le-bar"><span class="le-brand">{SCALES}'
        f"<span>LEGAL-EYE</span></span>"
        f'<span class="le-note">{nav_note or title}</span></div>',
        unsafe_allow_html=True,
    )

    st.markdown(body_markdown)

    st.markdown(
        f"""
<div class="le-footer">
  <p><a href="/" target="_self">Review a contract</a>
     <a href="/About" target="_self">About</a>
     <a href="/Terms" target="_self">Terms</a>
     <a href="/Privacy" target="_self">Privacy notice</a></p>
  <p>&copy; {date.today().year} Legal-Eye. Not legal advice. Documents are
  deleted the moment analysis ends.</p>
</div>
""",
        unsafe_allow_html=True,
    )
