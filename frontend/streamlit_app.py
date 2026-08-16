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
from backend.config import (  # noqa: E402
    DATABASE_URL,
    EMAIL_FROM,
    EMAIL_PROVIDER,
    ORDERS_DB_PATH,
    ORDERS_SCHEMA,
    PAYMENT_PROVIDER,
    PAYMENTS_ALLOW_DEV,
    PAYMENTS_ENABLED,
    REPORT_CURRENCY,
    REPORT_PRICE_CENTS,
    REPORT_RETENTION_DAYS,
    RESEND_API_KEY,
)
from backend.delivery import fulfil_order  # noqa: E402
from backend.mailer import ConsoleSender, EmailError, ResendSender  # noqa: E402
from backend.orders import create_order, get_order_store  # noqa: E402
from backend.orders import OrderError, OrderStore, valid_email  # noqa: E402
from backend.payments import PaymentError, get_provider  # noqa: E402

MAX_FILES = 5  # hard cap: the bundle is reviewed as one combined document

st.set_page_config(
    page_title="Legal-Eye | AI Contract Review for South Africa",
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
.block-container{max-width:1180px; padding-top:2.4rem; padding-bottom:4rem;}
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
.le-uploadhint{font-size:12.5px; color:var(--muted); margin:6px 0 0 0;}
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
/* The native button text differs between Streamlit versions ("Upload" vs
   "Browse files") — hide it and show our own label instead. Scope this to the
   DROPZONE button only: [data-testid="stFileUploader"] button matches every
   button in the widget, including each uploaded file's delete button, which
   then rendered "Import documents" next to every x. */
[data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"]{
  display:none;}
[data-testid="stFileUploaderDropzone"] button::after{content:"Import documents";}
/* Delete buttons stay a bare x — no label, no pseudo-element, brass icon. */
[data-testid="stFileUploaderDeleteBtn"]::after,
[data-testid="stFileUploaderDeleteBtn"] *::after{content:none !important;}
[data-testid="stFileUploaderDeleteBtn"] [data-testid="stMarkdownContainer"],
[data-testid="stFileUploaderDeleteBtn"] p,
[data-testid="stFileUploaderDeleteBtn"] span:not([class*="icon"]):not([class*="Icon"]){
  display:none !important;}
[data-testid="stFileUploaderDeleteBtn"]{
  background:transparent !important; border:none !important; padding:2px !important;}
[data-testid="stFileUploaderDeleteBtn"] svg{
  color:var(--brass-ink) !important; fill:currentColor;}
[data-testid="stFileUploaderDeleteBtn"]:hover svg{color:var(--danger) !important;}
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
/* Nothing may escape the report card. Long reference numbers, URLs and
   unbroken strings wrap instead of pushing the layout wider. */
[data-testid="stVerticalBlockBorderWrapper"] *{
  overflow-wrap:anywhere; word-break:break-word; min-width:0;}
[data-testid="stVerticalBlockBorderWrapper"]{padding:4px 6px;}
[data-testid="stVerticalBlockBorderWrapper"] table{
  display:block; width:100%; overflow-x:auto; border-collapse:collapse;}
[data-testid="stVerticalBlockBorderWrapper"] td,
[data-testid="stVerticalBlockBorderWrapper"] th{
  padding:8px 10px; vertical-align:top;}
[data-testid="stVerticalBlockBorderWrapper"] pre,
[data-testid="stVerticalBlockBorderWrapper"] code{
  white-space:pre-wrap; overflow-wrap:anywhere;}
/* If a stray equation survives, let it scroll rather than break the page. */
[data-testid="stVerticalBlockBorderWrapper"] .katex-display{
  overflow-x:auto; overflow-y:hidden;}
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


@st.cache_resource
@st.cache_resource(show_spinner=False)
def _order_store() -> OrderStore:
    """Postgres in deployment, SQLite locally.

    Cached because it is built on every rerun otherwise, and the SQLite branch
    runs its migration each time it is constructed. The store itself holds no
    open connection, so caching it across reruns is safe.
    """
    return get_order_store(DATABASE_URL, ORDERS_DB_PATH, ORDERS_SCHEMA)


def _email_sender():
    if EMAIL_PROVIDER == "resend":
        return ResendSender(RESEND_API_KEY, EMAIL_FROM)
    return ConsoleSender()


def _price() -> str:
    symbol = "R" if REPORT_CURRENCY == "ZAR" else f"{REPORT_CURRENCY} "
    return f"{symbol}{REPORT_PRICE_CENTS / 100:,.2f}"


def delivery_panel(analysis, document_names: list[str]) -> None:
    """Email the finished review.

    Two modes, driven by PAYMENTS_ENABLED. While charging is off the review is
    sent free: no price, no payment step, and no cooling-off consent, because
    none of that applies where there is no sale. The order is still recorded, so
    delivery, retries and the retention rules behave identically either way.
    """
    if PAYMENTS_ENABLED:
        blurb = (f"We will email you the full review as a PDF you can keep, "
                 f"print and forward, for {_price()}. The copy on this page "
                 f"stays where it is.")
        button = f"Pay {_price()} and email it to me"
    else:
        blurb = ("We will email you the full review as a PDF you can keep, "
                 "print and forward. It is free while Legal-Eye is in early "
                 "access.")
        button = "Email the review to me"

    st.markdown(
        f"""
<div class="le-section" style="margin:34px 0 14px 0;">
  <h2>Email me this review</h2>
  <p>{blurb}</p>
</div>
""",
        unsafe_allow_html=True,
    )

    # A console sender writes to the server log and delivers nothing. Say so
    # rather than reporting a success the reader will never receive.
    if EMAIL_PROVIDER == "console":
        notice(
            "<strong>Email is not configured.</strong> EMAIL_PROVIDER is set to "
            "'console', so the review is written to the server log instead of "
            "being sent. Set EMAIL_PROVIDER and RESEND_API_KEY to deliver for real.",
            icon=ALERT, kind="le-note-error",
        )

    with st.form("deliver_report"):
        email = st.text_input("Email address", placeholder="you@company.co.za")
        consent = True
        if PAYMENTS_ENABLED:
            consent = st.checkbox(
                "Send my review immediately. I understand that because delivery "
                "starts straight away, the seven-day cooling-off right in "
                "section 44 of the Electronic Communications and Transactions "
                "Act falls away under section 42(2)(d).",
                value=False,
            )
        marketing = st.checkbox(
            "Occasionally email me about Legal-Eye. Unticked means we only use "
            "your address to send this one review.",
            value=False,
        )
        submitted = st.form_submit_button(button, type="primary")

    st.markdown(
        '<div class="le-uploadhint">Your address is used to deliver this review '
        "and to keep the order record. It is not shared, and it is not added to "
        "any mailing list unless you tick the box above. Reports are removed "
        f"from our records after {REPORT_RETENTION_DAYS} days. See our "
        "<a href='/Terms' target='_self'>terms</a> and "
        "<a href='/Privacy' target='_self'>privacy notice</a>.</div>",
        unsafe_allow_html=True,
    )

    if not submitted:
        return

    if not valid_email(email):
        notice("That does not look like an email address. Please check it and "
               "try again.", icon=ALERT, kind="le-note-error")
        return

    if PAYMENTS_ENABLED and not consent:
        notice("Please tick the box confirming you want the review sent "
               "immediately. We need that confirmation on record before we can "
               "deliver, and you can read why in our "
               "<a href='/Terms' target='_self'>terms</a>.",
               icon=ALERT, kind="le-note-error")
        return

    try:
        order = create_order(
            _order_store(),
            email=email,
            report=analysis.summary,
            document_names=document_names,
            amount_cents=REPORT_PRICE_CENTS if PAYMENTS_ENABLED else 0,
            risk_score=analysis.score,
            risk_band=analysis.band,
            marketing_opt_in=marketing,
            currency=REPORT_CURRENCY,
            immediate_delivery_consent=consent,
        )
        spinner = ("Confirming payment and sending your review..."
                   if PAYMENTS_ENABLED else "Sending your review...")
        with st.spinner(spinner):
            delivered = fulfil_order(
                _order_store(),
                order,
                get_provider(PAYMENT_PROVIDER, allow_dev=PAYMENTS_ALLOW_DEV),
                _email_sender(),
                charging=PAYMENTS_ENABLED,
            )
    except PaymentError as exc:
        notice(f"Payment could not be completed. {html.escape(str(exc))}",
               icon=ALERT, kind="le-note-error")
        return
    except EmailError as exc:
        notice(f"The email did not send. {html.escape(str(exc))} Your review is "
               "still on this page, and you can try again.",
               icon=ALERT, kind="le-note-error")
        return
    except OrderError as exc:
        notice(html.escape(str(exc)), icon=ALERT, kind="le-note-error")
        return

    notice(f"Sent to <strong>{html.escape(delivered.email)}</strong>. Reference "
           f"<strong>{delivered.id[:12]}</strong>. If it has not arrived in a "
           "few minutes, check your spam folder.")


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


def escape_currency(markdown: str) -> str:
    """Stop Streamlit reading currency amounts as LaTeX math.

    Streamlit renders $...$ as inline maths. A paragraph containing two amounts,
    say $1,391,189.00 and $2,583,637.55, therefore has everything between them
    swallowed into an equation: serif italic, spaces stripped, and no wrapping,
    so it overflows the container. Escaping every dollar sign avoids it. Reports
    never contain intentional LaTeX, so nothing legitimate is lost.
    """
    return (markdown or "").replace("\\$", "$").replace("$", "\\$")


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
# Header. Kept to a single render call: the landing page does the explaining,
# so this page only has to say what it is and get out of the way.
# --------------------------------------------------------------------------
st.markdown(
    f"""
<div class="le-topbar">
  <div class="le-brand">{SCALES}<span class="le-wordmark">LEGAL-EYE</span></div>
  <span class="le-topnote">Built for South African law. Not legal advice.</span>
</div>

<div class="le-hero">
  <div class="le-eyebrow">AI Contract Review · South Africa</div>
  <h1>Review a contract.</h1>
  <p class="le-sub">Upload up to five documents. They are checked against the
  South African statutes that decide these disputes, and you get the parties,
  the obligations, the clauses worth arguing about and a risk score out of 10.
  <a href="/About" target="_self">How it works</a>.</p>
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
st.markdown(
    '<div class="le-uploadhint">Drag and drop several files at once, or hold '
    "Ctrl (⌘ on Mac) while selecting files in the dialog.</div>",
    unsafe_allow_html=True,
)

if uploaded_files and len(uploaded_files) > MAX_FILES:
    notice(
        f"You selected {len(uploaded_files)} documents. Only the first "
        f"{MAX_FILES} are analyzed. Remove the extras, or run them in a "
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
        help="Same analysis either way. Only the wording changes.",
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
    # Imported at the point of use, not at module level. It pulls in the OpenAI
    # client, which is dead weight on a page load where nobody runs an analysis.
    from backend.summarizer import analyze_legal_document

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
            status.update(label="Analysis complete", state="complete")

        # Park the finished review in session state instead of rendering it
        # straight from these local variables.
        #
        # Streamlit reruns this file from the top on every interaction, and a
        # button reports True only on the single rerun that follows its click.
        # So the moment the reader submitted the email form, the script reran
        # with run = False, this whole block was skipped, the review disappeared
        # off the page and the send was never reached. Nothing errored, nothing
        # was logged, and no request ever left the server. Session state
        # survives reruns, which is what makes the form usable at all.
        st.session_state["review"] = {
            "analysis": analysis,
            "document_names": [f.name for f in files],
            "ocr_names": ocr_names,
            "characters": len(text),
        }

    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        st.session_state.pop("review", None)
        notice(html.escape(str(exc)), icon=ALERT, kind="le-note-error")
    finally:
        for path in temp_paths:
            Path(path).unlink(missing_ok=True)


# --------------------------------------------------------------------------
# Rendered from session state, not from the run above, so the review stays on
# screen across the reruns that the email field, the checkboxes and the submit
# button all trigger.
# --------------------------------------------------------------------------
review = st.session_state.get("review")
if review:
    analysis = review["analysis"]
    document_names = review["document_names"]
    ocr_names = review["ocr_names"]

    if len(document_names) == 1:
        notice(f"Summary ready for <strong>{html.escape(document_names[0])}</strong>")
    else:
        names = ", ".join(html.escape(n) for n in document_names)
        notice(
            f"Summary ready for <strong>{len(document_names)} documents, analyzed "
            f"together</strong>: {names}"
        )
    if ocr_names:
        notice(
            "These documents are scans, so their text was read using OCR. "
            "Character recognition can misread names, figures and dates, so "
            f"check anything important against the original: "
            f"{', '.join(html.escape(n) for n in ocr_names)}.",
            icon=ALERT,
        )
    if analysis.redaction_summary and "No personal" not in analysis.redaction_summary:
        notice(
            f"{html.escape(analysis.redaction_summary)} They are restored in "
            "the report below, which never leaves this machine.",
            icon=SHIELD,
        )
    if analysis.unverified_citations:
        notice(
            f"{len(analysis.unverified_citations)} legal reference(s) in this "
            "report are <strong>not in the tool's verified list</strong> and may "
            "be inaccurate. They are listed at the end of the report. Check each "
            "one against a primary source before you rely on it.",
            icon=ALERT,
            kind="le-note-error",
        )

    render_risk_band(analysis.score, analysis.band)

    # The analysis marks its most serious findings with inline colour, and
    # colour_severities adds the pills, so HTML has to render rather than
    # appear as literal tags.
    with st.container(border=True):
        st.markdown(escape_currency(colour_severities(analysis.summary)),
                    unsafe_allow_html=True)

    # The review itself stays on screen. What delivery adds is a copy the
    # reader can keep and forward.
    delivery_panel(analysis, document_names)

    st.markdown(
        f'<div class="le-meta">Input: ~{review["characters"]:,} characters '
        f'analyzed across {len(document_names)} '
        f"document{'' if len(document_names) == 1 else 's'}</div>",
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------
# Footer. Deliberately short: the landing page carries the explanatory content,
# and duplicating it here cost about five seconds of render time per visit.
# What stays is what the tool page itself needs, which is the disclaimer.
# --------------------------------------------------------------------------
st.markdown(
    f"""
<div class="le-footer">
  <div class="le-footer-brand">{SCALES}<span>LEGAL-EYE</span></div>
  <p><strong style="color:#fff">Legal disclaimer.</strong> Legal-Eye is an
  automated document triage tool for informational purposes only. It is not
  legal advice, it creates no attorney and client relationship, and it must not
  be used to prepare documents for court proceedings. AI systems can misstate or
  invent legal authorities, so verify every statutory reference and case
  citation against a primary South African source before relying on it. Document
  text is processed by a third-party AI provider outside South Africa. Consult
  an admitted South African legal practitioner before acting.</p>
  <p><a href="/About" target="_self">About Legal-Eye</a> &middot;
     <a href="/Terms" target="_self">Terms</a> &middot;
     <a href="/Privacy" target="_self">Privacy notice</a></p>
  <p class="le-footline">&copy; {date.today().year} Legal-Eye. Contract review
  for South Africa. Documents are deleted the moment analysis ends.</p>
</div>
""",
    unsafe_allow_html=True,
)
