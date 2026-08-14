"""Legal-Eye web interface: drag-and-drop a legal document, get a structured summary."""

import sys
import tempfile
from pathlib import Path

import streamlit as st

# Make the project root importable so `backend.*` resolves when Streamlit runs
# this file directly (Streamlit puts the script's own folder on sys.path, not the root).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.parser import extract_document  # noqa: E402
from backend.summarizer import estimate_cost, summarize_legal_document  # noqa: E402

st.set_page_config(
    page_title="Legal-Eye — AI Legal Document Summarizer",
    page_icon="⚖️",
    layout="wide",
)

st.title("Legal-Eye ⚖️")
st.write("Upload a legal document and get an instant AI summary.")
st.caption(
    "⚠️ AI-generated summaries are for informational purposes only and do not "
    "constitute legal advice."
)

st.divider()

uploaded_file = st.file_uploader("Upload a document", type=["pdf", "docx", "txt"])
run = st.button("Summarize Document", type="primary", disabled=uploaded_file is None)

if uploaded_file is None:
    st.subheader("How it works")
    st.markdown(
        "1. **Upload** a contract, lease, NDA, or any legal document (PDF, DOCX, or TXT).\n"
        "2. **Click Summarize** — the text is extracted and analyzed by AI.\n"
        "3. **Read or download** a structured summary: parties, obligations, "
        "critical clauses, risks, and recommendations."
    )

if run and uploaded_file is not None:
    suffix = Path(uploaded_file.name).suffix or ".txt"
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(uploaded_file.getbuffer())
            temp_path = handle.name

        # The analysis runs in two passes, so report each stage rather than
        # leaving the reader watching one spinner for the whole wait.
        with st.status("Analyzing document…", expanded=False) as status:
            extraction = extract_document(temp_path)
            text = extraction.text
            summary = summarize_legal_document(
                text, on_progress=lambda stage: status.update(label=stage)
            )
            status.update(label="Analysis complete", state="complete")

        st.success(f"Summary ready for **{uploaded_file.name}**")
        if extraction.used_ocr:
            st.warning(
                "This document is a scan, so the text was read using OCR. "
                "Character recognition can misread names, figures, and dates — "
                "check anything important against the original."
            )
        # The analysis marks its most serious findings with inline colour,
        # so HTML has to render rather than appear as literal tags.
        st.markdown(summary, unsafe_allow_html=True)

        st.divider()
        left, right = st.columns([1, 2])
        with left:
            st.download_button(
                "⬇️ Download Summary (.md)",
                data=summary,
                file_name=f"{Path(uploaded_file.name).stem}_summary.md",
                mime="text/markdown",
            )
        with right:
            st.caption(
                f"📊 Input: ~{len(text):,} characters "
                f"(≈ ${estimate_cost(len(text)):.3f} estimated API cost)."
            )

    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        st.error(str(exc))
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)
