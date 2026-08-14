"""Legal-Eye web interface: drag-and-drop a legal document, get a structured summary.

Visual system (tokens): ink #14283c / slate #44536a / muted #67748a on paper
#f5f7fa with white cards, brass accent #a6782f (decorative) and #8a6427 (text).
Display type: Georgia serif; body: system sans. Spacing scale 8/16/24/32/48.
"""

import html
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

# Make the project root importable so `backend.*` resolves when Streamlit runs
# this file directly (Streamlit puts the script's own folder on sys.path, not the root).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.parser import extract_document  # noqa: E402
from backend.summarizer import analyze_legal_document  # noqa: E402

MAX_FILES = 5  # hard cap: the bundle is reviewed as one combined document

st.set_page_config(
    page_title="Legal-Eye — AI Legal Document Review",
    page_icon="⚖️",
    layout="wide",
)

# --------------------------------------------------------------------------
# Style tokens — the single source of truth for every visual decision below.
# --------------------------------------------------------------------------
st.markdown(
    """
<style>
:root{
  --ink:#14283c; --ink-soft:#23394f; --slate:#44536a; --muted:#67748a;
  --paper:#f5f7fa; --card:#ffffff; --line:#dfe5ec; --line-strong:#b9c4d1;
  --brass:#a6782f; --brass-ink:#8a6427; --brass-tint:#f4ead9;
  --ok:#1f7a4d; --warn:#8a5a00; --danger:#c00000;
  --radius:10px;
}
.stApp{background:var(--paper); color:var(--slate);}
.stApp, .stApp button, .stApp input, .stApp textarea{
  font-family:"Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif;
}
.block-container{max-width:1080px; padding-top:2.4rem; padding-bottom:4rem;}

/* Chrome hygiene */
#MainMenu, footer, [data-testid="stToolbar"]{visibility:hidden;}
[data-testid="stDecoration"]{display:none;}

h1,h2,h3,h4{color:var(--ink);}

/* Top bar — white, with the logo centred. Streamlit's own header is fixed to
   the viewport and would float over the page on scroll, so it is removed
   outright rather than recoloured. */
header[data-testid="stHeader"]{display:none;}
.le-topbar{position:relative; display:flex; justify-content:center; align-items:center;
  padding:14px 20px; background:#ffffff; border:1px solid var(--line);
  border-radius:var(--radius); margin-bottom:36px;}
.le-brand{display:flex; align-items:center; gap:10px;}
.le-brand svg{color:var(--brass);}
.le-wordmark{font-size:18px; font-weight:700; letter-spacing:.06em; color:var(--ink);}
.le-topnote{position:absolute; right:20px; top:50%; transform:translateY(-50%);
  font-size:12.5px; color:var(--muted); border:1px solid var(--line);
  padding:6px 12px; border-radius:999px;}

/* Hero */
.le-hero{max-width:820px; margin:0 0 28px 0;}
.le-eyebrow{font-size:12px; font-weight:700; letter-spacing:.16em;
  text-transform:uppercase; color:var(--brass-ink); margin-bottom:14px;}
.le-hero h1{font-family:Georgia, "Iowan Old Style", "Times New Roman", serif;
  font-weight:700; font-size:clamp(34px,4.6vw,48px); line-height:1.12;
  letter-spacing:-.01em; color:var(--ink); margin:0 0 18px 0;}
.le-sub{font-size:16.5px; line-height:1.65; color:var(--slate); max-width:640px; margin:0 0 22px 0;}
.le-chips{display:flex; flex-wrap:wrap; gap:10px;}
.le-chip{font-size:13px; color:var(--slate); background:var(--card);
  border:1px solid var(--line); border-radius:999px; padding:7px 14px;}

/* Stats */
.le-stats{display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin:0 0 36px 0;}
.le-stat{background:var(--card); border:1px solid var(--line); border-top:3px solid var(--brass);
  border-radius:var(--radius); padding:18px 20px;}
.le-stat-value{font-size:26px; font-weight:700; color:var(--ink); line-height:1.1;}
.le-stat-label{font-size:12.5px; line-height:1.5; color:var(--muted); margin-top:6px;}

/* Section headings */
.le-section{margin:44px 0 18px 0;}
.le-section h2{font-family:Georgia, "Iowan Old Style", "Times New Roman", serif;
  font-size:25px; font-weight:700; margin:0 0 8px 0;}
.le-section p{margin:0; font-size:15px; color:var(--muted); max-width:660px;}

/* Upload panel */
.le-panelhead{display:flex; justify-content:space-between; align-items:flex-end;
  gap:16px; margin:0 0 10px 0;}
.le-panelhead h3{margin:0 0 4px 0; font-size:19px;}
.le-panelhead p{margin:0; font-size:14.5px; color:var(--muted);}
.le-panelhint{font-size:14.5px; font-style:italic; color:var(--brass-ink); white-space:nowrap;}
[data-testid="stFileUploaderDropzone"]{
  background:var(--card); border:2px dashed var(--line-strong);
  border-radius:var(--radius); padding:8px;}
[data-testid="stFileUploaderDropzone"]:hover{border-color:var(--brass);}
.le-privacy{display:flex; gap:10px; align-items:flex-start; font-size:13.5px;
  line-height:1.55; color:var(--muted); margin-top:14px;}
.le-privacy svg{flex:none; color:var(--ok); margin-top:1px;}

/* Primary button — white with brass text */
.stApp [data-testid="stBaseButton-primary"]{
  background:#ffffff; color:var(--brass-ink); border:1px solid var(--brass);
  border-radius:8px; font-weight:600; padding:0.55rem 1.6rem;}
.stApp [data-testid="stBaseButton-primary"]:hover{
  background:var(--brass-tint); border-color:var(--brass-ink);}
.stApp [data-testid="stBaseButton-primary"]:disabled{
  background:#ffffff; color:var(--muted); border-color:var(--line);}

/* Widget labels and radio options. Streamlit renders these through generated
   classes that inherit a default text colour, so they need to be set here or
   they sit almost invisible against the paper background. */
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label,
.stRadio label, [data-testid="stRadio"] label, [data-testid="stRadio"] p,
.stCheckbox label, .stCheckbox p, [data-testid="stFileUploader"] label{
  color:var(--ink) !important;}
[data-testid="stWidgetLabel"] p{
  font-size:12px !important; font-weight:700 !important; letter-spacing:.14em;
  text-transform:uppercase; color:var(--brass-ink) !important;}
[data-testid="stRadio"] label p{font-size:14.5px !important; font-weight:500 !important;}
[data-testid="stRadio"] [role="radiogroup"]{gap:18px;}
/* The dropzone's own instruction text washes out the same way. */
[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small{color:var(--slate) !important;}

/* Uploader and download buttons — same white/brass treatment as the primary.
   !important is needed: Streamlit's generated classes outrank plain selectors. */
[data-testid="stFileUploaderDropzone"] button,
.stApp [data-testid="stBaseButton-secondary"],
.stApp [data-testid="baseButton-secondary"],
.stApp [data-testid="stDownloadButton"] button{
  background:#ffffff !important; color:var(--brass-ink) !important;
  border:1px solid var(--brass) !important; border-radius:8px !important;
  font-weight:600 !important;}
[data-testid="stFileUploaderDropzone"] button:hover,
.stApp [data-testid="stBaseButton-secondary"]:hover,
.stApp [data-testid="baseButton-secondary"]:hover,
.stApp [data-testid="stDownloadButton"] button:hover{
  background:var(--brass-tint) !important; border-color:var(--brass-ink) !important;
  color:var(--brass-ink) !important;}
[data-testid="stFileUploaderDropzone"] button svg,
.stApp [data-testid="stDownloadButton"] button svg{
  color:var(--brass-ink) !important; fill:currentColor;}

/* Notices — white ground, brass rule, ink text. Streamlit's default success
   and warning colours are tinted panels whose text drops out against them. */
.le-note{display:flex; gap:11px; align-items:flex-start; background:var(--card);
  border:1px solid var(--line); border-left:4px solid var(--brass);
  border-radius:8px; padding:14px 16px; margin:0 0 12px 0;
  font-size:14.5px; line-height:1.6; color:var(--ink);}
.le-note svg{flex:none; margin-top:2px; color:var(--brass);}
.le-note strong{color:var(--ink);}
.le-note-error{border-left-color:var(--danger);}
.le-note-error svg{color:var(--danger);}

/* Risk band — the four colours are set per-run from the computed score. */
.le-band{display:flex; gap:18px; align-items:center; background:var(--band-tint,#fff);
  border:1px solid var(--band-line,var(--line)); border-left:6px solid var(--band,var(--brass));
  border-radius:var(--radius); padding:18px 22px; margin:0 0 14px 0;}
.le-band-score{font-family:Georgia,"Times New Roman",serif; font-size:36px; font-weight:700;
  color:var(--band-ink,var(--ink)); line-height:1; white-space:nowrap;}
.le-band-score small{font-size:16px; font-weight:400; opacity:.65;}
.le-band-body{display:flex; flex-direction:column; gap:4px; min-width:0;}
.le-band-name{font-size:12px; font-weight:700; letter-spacing:.16em; text-transform:uppercase;
  color:var(--band-ink,var(--ink));}
.le-band-note{font-size:14.5px; line-height:1.55; color:var(--ink);}
.le-meter{display:flex; gap:3px; margin-left:auto; flex:none;}
.le-meter span{width:14px; height:26px; border-radius:2px; background:#ffffff;
  border:1px solid var(--band-line,var(--line));}
.le-meter span.on{background:var(--band,var(--brass)); border-color:var(--band,var(--brass));}

/* Severity pills inside the risk table */
.le-sev{display:inline-block; font-size:11.5px; font-weight:700; letter-spacing:.05em;
  text-transform:uppercase; padding:3px 9px; border-radius:999px; border:1px solid;
  white-space:nowrap;}
.le-sev-critical{color:#8f0000; background:#fdecec; border-color:#e8b4b4;}
.le-sev-high{color:#9c410a; background:#fdf0e6; border-color:#eec9a8;}
.le-sev-medium{color:#7d6f00; background:#fbf8e0; border-color:#ddd18f;}
.le-sev-low{color:#17603c; background:#e9f5ee; border-color:#a8d4bd;}

/* Result card + alerts */
[data-testid="stVerticalBlockBorderWrapper"]{
  border:1px solid var(--band-line,var(--line))!important;
  border-top:5px solid var(--band,var(--brass))!important;
  border-radius:var(--radius); background:var(--card);}
/* Fallback for any Streamlit-generated alert not replaced above. */
[data-testid="stAlert"]{background:var(--card)!important; border:1px solid var(--line)!important;
  border-left:4px solid var(--brass)!important; border-radius:8px; box-shadow:none;}
[data-testid="stAlert"] p, [data-testid="stAlert"] div, [data-testid="stAlert"] li{
  color:var(--ink)!important;}
.le-meta{font-size:13px; color:var(--muted);}

/* Steps */
.le-steps{display:grid; grid-template-columns:repeat(3,1fr); gap:14px;}
.le-step{background:var(--card); border:1px solid var(--line); border-radius:var(--radius);
  padding:22px;}
.le-step-num{font-family:Georgia, serif; font-size:15px; font-weight:700; color:var(--brass-ink);
  letter-spacing:.08em; text-transform:uppercase; margin-bottom:10px;}
.le-step h4{margin:0 0 8px 0; font-size:16.5px;}
.le-step p{margin:0; font-size:13.5px; line-height:1.6; color:var(--muted);}

/* What you get */
.le-grid{display:grid; grid-template-columns:1fr 1fr; gap:12px;}
.le-item{background:var(--card); border:1px solid var(--line); border-radius:var(--radius);
  padding:16px 18px;}
.le-item h4{margin:0 0 4px 0; font-size:14.5px;}
.le-item p{margin:0; font-size:13px; line-height:1.55; color:var(--muted);}

/* Why trust */
.le-why{background:var(--ink); border-radius:var(--radius); padding:30px 32px; margin:0;}
.le-why h3{color:#ffffff; font-family:Georgia, serif; font-size:22px; margin:0 0 16px 0;}
.le-why ul{list-style:none; margin:0; padding:0; display:grid;
  grid-template-columns:1fr 1fr; gap:12px 28px;}
.le-why li{color:#c7d2dd; font-size:13.5px; line-height:1.6; padding-left:26px; position:relative;}
.le-why li::before{content:""; position:absolute; left:0; top:4px; width:14px; height:14px;
  border:2px solid var(--brass); border-radius:50%;}
.le-why li::after{content:""; position:absolute; left:4.5px; top:8px; width:6px; height:3.5px;
  border-left:2px solid var(--brass); border-bottom:2px solid var(--brass);
  transform:rotate(-45deg);}

/* FAQ */
[data-testid="stExpander"]{background:var(--card); border:1px solid var(--line)!important;
  border-radius:8px; margin-bottom:10px;}
[data-testid="stExpander"] summary{font-weight:600; color:var(--ink);}
[data-testid="stExpander"] p, [data-testid="stExpander"] li{font-size:14px; color:var(--slate);}

/* Footer */
.le-footer{background:var(--ink); border-radius:var(--radius); padding:30px 32px; margin-top:44px;}
.le-footer-brand{display:flex; align-items:center; gap:10px; margin-bottom:12px;}
.le-footer-brand svg{color:var(--brass);}
.le-footer-brand span{color:#ffffff; font-weight:700; letter-spacing:.06em; font-size:15px;}
.le-footer p{color:#c7d2dd; font-size:12.5px; line-height:1.7; margin:0 0 10px 0; max-width:880px;}
.le-footer .le-footline{color:#8fa2b4; font-size:12px; border-top:1px solid #2e465c;
  padding-top:14px; margin-top:6px;}

@media (max-width:900px){
  .le-stats{grid-template-columns:1fr 1fr;}
  .le-steps{grid-template-columns:1fr;}
  .le-grid{grid-template-columns:1fr;}
  .le-why ul{grid-template-columns:1fr;}
  .le-topnote{display:none;}
  .le-panelhead{flex-wrap:wrap;}
}
@media (prefers-reduced-motion:reduce){
  *, *::before, *::after{transition:none!important; animation:none!important;}
}
</style>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Icons — inline SVG only; no emoji used as product iconography.
# --------------------------------------------------------------------------
SCALES = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4v15"/><path d="M7 21h10"/><path d="M12 6l-6 7h12l-6-7z"/><path d="M5 17h14"/></svg>'
SHIELD = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l7 3v5c0 4.6-3 8.1-7 10-4-1.9-7-5.4-7-10V6l7-3z"/><path d="M9 12l2 2 4-4"/></svg>'

CHECK = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>'
ALERT = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg>'


def notice(body: str, icon: str = CHECK, kind: str = "") -> None:
    """Render a themed notice. Replaces st.success/st.warning/st.error, whose
    default tinted panels do not sit in this palette and whose text can drop
    out against them."""
    css_class = f"le-note {kind}".strip()
    st.markdown(
        f'<div class="{css_class}">{icon}<span>{body}</span></div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Risk bands — strong / tint / ink / line, per band. Every ink-on-tint pair
# clears 4.5:1 contrast, so the label stays readable at small sizes.
# --------------------------------------------------------------------------
BANDS: dict[str, tuple[str, str, str, str, str]] = {
    "Critical": ("#c00000", "#fdecec", "#8f0000", "#e8b4b4",
                 "Irreversible loss is likely if you proceed before verifying "
                 "independently. Treat every deadline in the document as noise."),
    "High": ("#cc5500", "#fdf0e6", "#9c410a", "#eec9a8",
             "Material loss or no enforceable remedy. Resolve the flagged items "
             "before signing or paying."),
    "Elevated": ("#c98a00", "#fdf6e3", "#8a6000", "#e7d29b",
                 "Real gaps that could become expensive. Worth a proper read "
                 "and some negotiation."),
    "Moderate": ("#b8a200", "#fbf8e0", "#7d6f00", "#ddd18f",
                 "Ordinary commercial risk with some loose ends. Tidy them up "
                 "before execution."),
    "Low": ("#1f7a4d", "#e9f5ee", "#17603c", "#a8d4bd",
            "Nothing serious surfaced. Skim the findings and proceed."),
}

_SEVERITY_CELL = re.compile(
    r"(?<=\|)(\s*)\*{0,2}(Critical|High|Medium|Low)\*{0,2}(\s*)(?=\|)"
)


def colour_severities(markdown: str) -> str:
    """Turn bare severity words in table cells into coloured pills."""

    def pill(match: re.Match[str]) -> str:
        word = match.group(2)
        return (f'{match.group(1)}<span class="le-sev le-sev-{word.lower()}">'
                f"{word}</span>{match.group(3)}")

    return _SEVERITY_CELL.sub(pill, markdown)


def render_risk_band(score: int, band: str) -> None:
    """Colour the page for this result and draw the rating banner.

    The band colour is published as CSS variables rather than written into each
    element, so the report card picks it up too and the whole review is framed
    in one colour.
    """
    strong, tint, ink, line, note = BANDS.get(band, BANDS["Moderate"])
    meter = "".join(
        f'<span class="{"on" if i < score else ""}"></span>' for i in range(10)
    )
    st.markdown(
        f"""<style>:root{{--band:{strong}; --band-tint:{tint};
        --band-ink:{ink}; --band-line:{line};}}</style>
<div class="le-band">
  <div class="le-band-score">{score}<small>/10</small></div>
  <div class="le-band-body">
    <div class="le-band-name">{html.escape(band)} risk</div>
    <div class="le-band-note">{note}</div>
  </div>
  <div class="le-meter">{meter}</div>
</div>""",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Top bar + hero
# --------------------------------------------------------------------------
st.markdown(
    f"""
<div class="le-topbar">
  <div class="le-brand">{SCALES}<span class="le-wordmark">LEGAL-EYE</span></div>
  <span class="le-topnote">AI document triage — not legal advice</span>
</div>

<div class="le-hero">
  <div class="le-eyebrow">AI Contract Review</div>
  <h1>Know what you're signing before you sign it.</h1>
  <p class="le-sub">Drop in a contract, lease, NDA or any legal document and get a
  structured, plain-English review in about a minute — parties, obligations,
  critical clauses and a reproducible risk score out of 10.</p>
  <div class="le-chips">
    <span class="le-chip">PDF · DOCX · TXT</span>
    <span class="le-chip">Reproducible risk score</span>
    <span class="le-chip">File deleted after analysis</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Trust stats — every number below is a real property of the software.
# --------------------------------------------------------------------------
st.markdown(
    """
<div class="le-stats">
  <div class="le-stat"><div class="le-stat-value">11</div>
    <div class="le-stat-label">deterministic checks re-do the arithmetic, dates and quantities</div></div>
  <div class="le-stat"><div class="le-stat-value">3</div>
    <div class="le-stat-label">file formats — PDF, DOCX and TXT, scanned pages included</div></div>
  <div class="le-stat"><div class="le-stat-value">2</div>
    <div class="le-stat-label">analysis passes — facts are verified in code before the report is written</div></div>
  <div class="le-stat"><div class="le-stat-value">0</div>
    <div class="le-stat-label">files stored — processed in memory, deleted the moment analysis ends</div></div>
</div>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Upload panel
# --------------------------------------------------------------------------
st.markdown(
    """
<div class="le-panelhead">
  <div>
    <h3>Start a review</h3>
    <p>Select up to 5 documents, then run the analysis. They are reviewed together as one bundle.</p>
  </div>
  <span class="le-panelhint">Import up to 5 documents for analysis →</span>
</div>
""",
    unsafe_allow_html=True,
)

uploaded_files = st.file_uploader(
    "Upload documents (up to 5)",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=True,
)

if uploaded_files and len(uploaded_files) > MAX_FILES:
    notice(
        f"You selected {len(uploaded_files)} documents. Only the first "
        f"{MAX_FILES} are analyzed — remove the extras or run them in a "
        "second batch afterwards.",
        icon=ALERT,
    )

settings_left, settings_right = st.columns(2)
with settings_left:
    jurisdiction_label = st.radio(
        "Jurisdiction",
        ["South Africa", "General / other"],
        horizontal=True,
        help="South Africa applies SA statutes and case law, and restricts "
             "citations to a curated list this tool can vouch for.",
    )
with settings_right:
    audience_label = st.radio(
        "Written for",
        ["Legal professional", "Plain language"],
        horizontal=True,
        help="Same analysis either way — only the wording changes.",
    )

JURISDICTION = "ZA" if jurisdiction_label == "South Africa" else "GENERAL"
AUDIENCE = "plain" if audience_label == "Plain language" else "professional"
run = st.button(
    "Summarize Documents",
    type="primary",
    disabled=not uploaded_files,
)

st.markdown(
    f"""
<div class="le-privacy">{SHIELD}
  <span>Your documents are read in memory and their temporary files are deleted
  the moment analysis finishes. Legal-Eye never stores, logs or shares your
  documents.</span>
</div>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Results — same pipeline as before, presented in a card.
# --------------------------------------------------------------------------
if run and uploaded_files:
    files = list(uploaded_files[:MAX_FILES])
    temp_paths: list[str] = []
    try:
        parts: list[str] = []
        ocr_names: list[str] = []
        with st.status("Analyzing documents…", expanded=False) as status:
            # Bundle the files into one labelled document so the analysis runs
            # once over everything — cross-document checks (quantities that
            # must agree across a bundle, attachments vs the covering
            # document) then see the whole picture.
            for i, upload in enumerate(files, start=1):
                status.update(label=f"Reading document {i} of {len(files)}…")
                suffix = Path(upload.name).suffix or ".txt"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                    handle.write(upload.getbuffer())
                    temp_paths.append(handle.name)
                extraction = extract_document(temp_paths[-1])
                if extraction.used_ocr:
                    ocr_names.append(upload.name)
                parts.append(
                    f"========== DOCUMENT {i} OF {len(files)}: {upload.name} "
                    f"==========\n\n{extraction.text}"
                )
            text = "\n\n".join(parts)
            analysis = analyze_legal_document(
                text,
                on_progress=lambda stage: status.update(label=stage),
                jurisdiction=JURISDICTION,
                audience=AUDIENCE,
            )
            summary = analysis.summary
            status.update(label="Analysis complete", state="complete")

        if len(files) == 1:
            notice(f"Summary ready for <strong>{html.escape(files[0].name)}</strong>")
        else:
            names = ", ".join(html.escape(f.name) for f in files)
            notice(
                f"Summary ready — <strong>{len(files)} documents analyzed "
                f"together</strong>: {names}"
            )
        if ocr_names:
            notice(
                "These documents are scans, so their text was read using OCR. "
                "Character recognition can misread names, figures, and dates — "
                f"check anything important against the original: "
                f"{', '.join(html.escape(n) for n in ocr_names)}.",
                icon=ALERT,
            )
        if analysis.redaction_summary and "No personal" not in analysis.redaction_summary:
            notice(
                f"{html.escape(analysis.redaction_summary)} They were restored "
                "in the report below, which never leaves this machine.",
                icon=SHIELD,
            )
        if analysis.unverified_citations:
            notice(
                f"{len(analysis.unverified_citations)} legal reference(s) in this "
                "report are <strong>not in the tool's verified list</strong> and may "
                "be inaccurate. They are listed at the end of the report — check "
                "each against a primary source before relying on it.",
                icon=ALERT,
                kind="le-note-error",
            )

        render_risk_band(analysis.score, analysis.band)

        # The analysis marks its most serious findings with inline colour, and
        # colour_severities adds the pills, so HTML has to render rather than
        # appear as literal tags.
        with st.container(border=True):
            st.markdown(colour_severities(summary), unsafe_allow_html=True)

        st.download_button(
            "Download summary (.md)",
            data=summary,
            file_name=f"{Path(files[0].name).stem if len(files) == 1 else 'bundle'}_summary.md",
            mime="text/markdown",
        )
        st.markdown(
            f'<div class="le-meta">Input: ~{len(text):,} characters analyzed '
            f"across {len(files)} document{'' if len(files) == 1 else 's'}</div>",
            unsafe_allow_html=True,
        )

    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        notice(html.escape(str(exc)), icon=ALERT, kind="le-note-error")
    finally:
        for path in temp_paths:
            Path(path).unlink(missing_ok=True)

# --------------------------------------------------------------------------
# How the review works
# --------------------------------------------------------------------------
st.markdown(
    """
<div class="le-section">
  <h2>How the review works</h2>
  <p>Two passes plus a deterministic verification layer — the hardest findings
  never depend on a model happening to do the sum.</p>
</div>
<div class="le-steps">
  <div class="le-step"><div class="le-step-num">Step 1 — Extract</div>
    <h4>The facts are recorded</h4>
    <p>The document and its attachments are read, and their facts — amounts,
    payment schedules, dates, parties, quantities — are recorded as structured
    data. No judgement at this stage.</p></div>
  <div class="le-step"><div class="le-step-num">Step 2 — Verify</div>
    <h4>The arithmetic is redone</h4>
    <p>Eleven checks re-derive the numbers in plain code: does the payment
    schedule reconcile to the stated total? Do quantities agree across the
    bundle? Is an official act dated to a weekend?</p></div>
  <div class="le-step"><div class="le-step-num">Step 3 — Analyse</div>
    <h4>The report is written</h4>
    <p>The review is written with those verified findings in hand — and is
    explicitly instructed never to contradict them.</p></div>
</div>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# What you get
# --------------------------------------------------------------------------
st.markdown(
    """
<div class="le-section">
  <h2>What every report contains</h2>
  <p>Always the same headings, in the same order, in clean Markdown.</p>
</div>
<div class="le-grid">
  <div class="le-item"><h4>Document Risk Rating</h4><p>A score out of 10, up front — the worst finding sets a floor, the rest add on top.</p></div>
  <div class="le-item"><h4>Read This First</h4><p>The four to eight things that actually matter, before anything else.</p></div>
  <div class="le-item"><h4>Legal &amp; Regulatory Exposure</h4><p>Statutory, licensing, sanctions, AML and export-control flags, when present.</p></div>
  <div class="le-item"><h4>Executive Summary</h4><p>Document type, purpose and the key commercial terms.</p></div>
  <div class="le-item"><h4>Parties</h4><p>Every party and its role — undefined or ambiguously named parties are flagged.</p></div>
  <div class="le-item"><h4>Obligations</h4><p>Who must do what, by when, and for how much.</p></div>
  <div class="le-item"><h4>Critical Clauses</h4><p>Termination, liability, indemnity, IP, renewal, governing law and more.</p></div>
  <div class="le-item"><h4>Risk Assessment</h4><p>A table of risk, severity and reason — severity runs to Critical.</p></div>
  <div class="le-item"><h4>Recommendations</h4><p>Three to six concrete actions to take before signing.</p></div>
  <div class="le-item"><h4>Legal Disclaimer</h4><p>A fixed disclaimer closes every report — no exceptions.</p></div>
</div>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Why trust it
# --------------------------------------------------------------------------
st.markdown(
    """
<div class="le-section">
  <h2>Built to be defensible</h2>
  <p>Nothing on this page relies on vibes — the serious work is reproducible.</p>
</div>
<div class="le-why">
  <h3>Why the numbers can be trusted</h3>
  <ul>
    <li>The risk score comes from arithmetic and calendar checks in plain code — the same document always gets the same score.</li>
    <li>The model is instructed to be objective and neutral, and to report only what the document says.</li>
    <li>Red-flag emphasis is capped per report, so nothing gets buried in alarm noise.</li>
    <li>Scans, password-protected files, bad keys and rate limits all produce a plain-English message — never a traceback.</li>
  </ul>
</div>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# FAQ
# --------------------------------------------------------------------------
st.markdown(
    """
<div class="le-section">
  <h2>Questions you'll probably ask</h2>
</div>
""",
    unsafe_allow_html=True,
)

with st.expander("Is this legal advice?"):
    st.markdown(
        "No. Legal-Eye is an automated triage tool for reviewing documents. "
        "Every report carries a fixed disclaimer, and it does not replace a "
        "qualified attorney. Use it to decide what needs a lawyer's attention."
    )

with st.expander("Is my document stored anywhere?"):
    st.markdown(
        "No. The file is read in memory, written to a temporary location only "
        "while being analyzed, and deleted immediately afterwards. Legal-Eye "
        "never stores, logs or shares your documents."
    )

with st.expander("Which formats are supported?"):
    st.markdown(
        "PDF, DOCX and TXT, including text inside DOCX tables. Scanned PDFs "
        "without a text layer are read with local OCR when Tesseract is "
        "installed on the machine."
    )

with st.expander("Can it get things wrong?"):
    st.markdown(
        "Yes — any AI tool can misread a document, and OCR can misread names, "
        "figures and dates. That is exactly why the verification pass redoes "
        "the arithmetic deterministically and why the report ends with a "
        "disclaimer. Check anything important against the original."
    )

# --------------------------------------------------------------------------
# Footer
# --------------------------------------------------------------------------
st.markdown(
    f"""
<div class="le-footer">
  <div class="le-footer-brand">{SCALES}<span>LEGAL-EYE</span></div>
  <p><strong style="color:#fff">Legal disclaimer.</strong> Legal-Eye is an AI tool for
  document triage and informational purposes only. It does not constitute legal
  advice, it may contain errors or omissions, and it is not a substitute for a
  qualified attorney. Always review the original document before making
  decisions.</p>
  <p class="le-footline">© {date.today().year} Legal-Eye. All documents are
  processed locally and deleted after analysis.</p>
</div>
""",
    unsafe_allow_html=True,
)
