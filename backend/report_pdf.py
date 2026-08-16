"""Rendering a finished review as a branded PDF.

Why ReportLab and not an HTML-to-PDF converter: WeasyPrint and wkhtmltopdf both
need system libraries installed through packages.txt, and a deploy that dies on
a missing shared object is a worse outcome than writing the layout by hand.
ReportLab is a pure wheel, so the Streamlit Community Cloud build cannot break
on it.

The input is the Markdown the analysis produces. This module understands the
subset that actually appears in it — headings, bullets, numbered lists, tables,
bold, italic, links and the red <span> the skill uses for critical items — and
renders anything it does not recognise as plain text rather than dropping it.
Silently losing a line of a legal review would be the worst possible failure
mode here, so every branch ends with the text still on the page.
"""

from __future__ import annotations

import html as _html
import io
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, KeepTogether, ListFlowable, ListItem,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

from backend import languages
from backend.branding import (
    BRASS, BRASS_INK, DANGER, INK, LINE, MUTED, PAPER, SLATE, TAGLINE,
    WORDMARK, band_colours, SEVERITY_COLOURS, scales_drawing,
)

# A4, because this is a South African product and the reader will print it on
# A4. Letter-sized output looks subtly wrong in every office in the country.
PAGE_SIZE = A4
MARGIN_X = 18 * mm
MARGIN_TOP = 22 * mm
MARGIN_BOTTOM = 20 * mm
CONTENT_WIDTH = PAGE_SIZE[0] - 2 * MARGIN_X

def _register_fonts() -> tuple[str, str, str]:
    """Use DejaVu when it is installed, and fall back to the built-ins.

    ReportLab's standard fourteen fonts are WinAnsi encoded. That happens to
    cover Afrikaans, but it covers it by luck rather than design, and any
    character outside Latin-1 renders as a solid black box: a silent corruption
    of a legal document, which is the worst way for this to fail. DejaVu is
    Unicode and ships with fonts-dejavu-core, which packages.txt installs.

    Falling back rather than raising keeps a developer without the package
    working, at the cost of the coverage.
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = (
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/dejavu",
        "/Library/Fonts",
        "C:/Windows/Fonts",
    )
    faces = (("LE-Sans", "DejaVuSans.ttf"),
             ("LE-Sans-Bold", "DejaVuSans-Bold.ttf"),
             ("LE-Serif-Bold", "DejaVuSerif-Bold.ttf"))
    for directory in candidates:
        base = Path(directory)
        if not all((base / filename).exists() for _, filename in faces):
            continue
        try:
            for name, filename in faces:
                pdfmetrics.registerFont(TTFont(name, str(base / filename)))
        except Exception:  # noqa: BLE001 - any font error means fall back
            break
        return "LE-Sans", "LE-Sans-Bold", "LE-Serif-Bold"
    return "Helvetica", "Helvetica-Bold", "Times-Bold"


BODY_FONT, BODY_BOLD, DISPLAY_FONT = _register_fonts()

DISCLAIMER = (
    "This review was produced with AI assistance for informational purposes "
    "only and does not constitute legal advice. It may contain errors or "
    "omissions. Consult a qualified attorney before making legal or financial "
    "decisions, and always review the original document."
)


# --------------------------------------------------------------------------
# Inline Markdown. Order is load-bearing, so it is spelled out rather than
# chained: the red spans have to be lifted out before the XML escape, or the
# escape turns them into visible tags; and they have to go back in after it, or
# the escape eats the font tag we just added.
# --------------------------------------------------------------------------
_RED_OPEN = "\x01"
_RED_CLOSE = "\x02"

_SPAN_OPEN = re.compile(r"<span[^>]*color\s*:\s*#c00000[^>]*>", re.IGNORECASE)
_SPAN_ANY = re.compile(r"</?span[^>]*>", re.IGNORECASE)
_BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_ITALIC = re.compile(r"(?<![*\w])[*_](?!\s)([^*_]+?)(?<!\s)[*_](?![*\w])")
_CODE = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def _inline(text: str) -> str:
    """Markdown fragment to the mini-HTML ReportLab's Paragraph understands."""
    text = _SPAN_OPEN.sub(_RED_OPEN, text)
    text = _SPAN_ANY.sub(_RED_CLOSE, text)
    text = _html.escape(text, quote=False)
    text = _CODE.sub(r'<font face="Courier">\1</font>', text)
    text = _BOLD.sub(r"<b>\1</b>", text)
    text = _ITALIC.sub(r"<i>\1</i>", text)
    text = _LINK.sub(rf'<link href="\2" color="{BRASS_INK}">\1</link>', text)
    text = text.replace(_RED_OPEN, f'<font color="{DANGER}">')
    text = text.replace(_RED_CLOSE, "</font>")
    return text


def _plain(text: str) -> str:
    """Strip markup down to bare words, for matching severity cells."""
    text = _SPAN_ANY.sub("", text)
    return text.replace("*", "").replace("`", "").strip()


# --------------------------------------------------------------------------
# Styles
# --------------------------------------------------------------------------
def _styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle(
        "body", fontName=BODY_FONT, fontSize=9.5, leading=14.5,
        textColor=colors.HexColor(SLATE), alignment=TA_LEFT, spaceAfter=7,
    )
    return {
        "body": base,
        "h1": ParagraphStyle(
            "h1", parent=base, fontName=DISPLAY_FONT, fontSize=16, leading=20,
            textColor=colors.HexColor(INK), spaceBefore=16, spaceAfter=8,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base, fontName=DISPLAY_FONT, fontSize=12.5, leading=16,
            textColor=colors.HexColor(INK), spaceBefore=14, spaceAfter=6,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "h3", parent=base, fontName=BODY_BOLD, fontSize=10, leading=14,
            textColor=colors.HexColor(BRASS_INK), spaceBefore=11, spaceAfter=4,
            keepWithNext=True,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=base, spaceAfter=3, leading=14,
        ),
        # Not Helvetica-Oblique: that is a built-in, so it would drop back to
        # Latin-1 coverage for one paragraph style and lose characters the rest
        # of the document renders correctly.
        "quote": ParagraphStyle(
            "quote", parent=base, leftIndent=10, borderPadding=0,
            textColor=colors.HexColor(MUTED),
        ),
        "cell": ParagraphStyle(
            "cell", parent=base, fontSize=8.8, leading=12.5, spaceAfter=0,
        ),
        "cellhead": ParagraphStyle(
            "cellhead", parent=base, fontSize=7.6, leading=10, spaceAfter=0,
            fontName=BODY_BOLD, textColor=colors.HexColor(MUTED),
        ),
        "meta": ParagraphStyle(
            "meta", parent=base, fontSize=8.5, leading=12,
            textColor=colors.HexColor(MUTED),
        ),
        "disclaimer": ParagraphStyle(
            "disclaimer", parent=base, fontSize=8, leading=11.5,
            textColor=colors.HexColor(MUTED),
        ),
    }


# --------------------------------------------------------------------------
# The cover header and the risk banner, drawn rather than laid out, because
# both are single blocks of colour that platypus has no natural way to express.
# --------------------------------------------------------------------------
class _CoverHeader(Flowable):
    """Navy band with the scales mark, the wordmark and the tagline."""

    HEIGHT = 30 * mm

    def __init__(self, width: float) -> None:
        super().__init__()
        self.width = width
        self.height = self.HEIGHT

    def draw(self) -> None:
        c = self.canv
        c.setFillColor(colors.HexColor(INK))
        c.rect(0, 0, self.width, self.height, stroke=0, fill=1)
        # A brass hairline under the band. It is the one detail that stops the
        # block reading as a generic dark rectangle.
        c.setFillColor(colors.HexColor(BRASS))
        c.rect(0, 0, self.width, 1.6, stroke=0, fill=1)

        mark = scales_drawing(size=15 * mm, colour=BRASS)
        mark.drawOn(c, 12 * mm, (self.height - 15 * mm) / 2 + 0.8)

        left = 12 * mm + 15 * mm + 6 * mm
        c.setFont(DISPLAY_FONT, 19)
        c.setFillColor(colors.white)
        c.drawString(left, self.height / 2 + 1.5 * mm, WORDMARK, charSpace=1.6)
        c.setFont(BODY_FONT, 8.4)
        c.setFillColor(colors.HexColor("#c7d2dd"))
        c.drawString(left, self.height / 2 - 4.2 * mm, TAGLINE)


class _RiskBanner(Flowable):
    """The score, the band name and what the band means, in the band colour."""

    HEIGHT = 26 * mm

    def __init__(self, width: float, score: int | None, band: str | None,
                 note: str, band_label: str | None = None,
                 risk_word: str = "risk") -> None:
        super().__init__()
        self.width = width
        self.height = self.HEIGHT
        self.score = score
        # `band` stays in English because it selects the colour; `band_label` is
        # what the reader sees.
        self.band = (band or "Unrated").title()
        self.band_label = band_label or self.band
        self.risk_word = risk_word
        self.note = note

    def draw(self) -> None:
        c = self.canv
        strong, tint, ink, line, _ = band_colours(self.band)

        c.setFillColor(colors.HexColor(tint))
        c.setStrokeColor(colors.HexColor(line))
        c.setLineWidth(0.7)
        c.rect(0, 0, self.width, self.height, stroke=1, fill=1)
        c.setFillColor(colors.HexColor(strong))
        c.rect(0, 0, 2.2 * mm, self.height, stroke=0, fill=1)

        pad = 8 * mm
        c.setFillColor(colors.HexColor(ink))
        c.setFont(DISPLAY_FONT, 27)
        score_text = f"{self.score}" if self.score is not None else "–"
        c.drawString(pad, self.height - 12.5 * mm, score_text)
        score_width = c.stringWidth(score_text, DISPLAY_FONT, 27)
        c.setFont(BODY_FONT, 11)
        c.drawString(pad + score_width + 1.5, self.height - 12.5 * mm, "/10")

        text_left = pad + 24 * mm
        c.setFont(BODY_BOLD, 8.6)
        c.drawString(text_left, self.height - 8.5 * mm,
                     f"{self.band_label} {self.risk_word}".upper(), charSpace=1.4)

        # Reserve the meter's column before wrapping, or the note runs under it.
        seg_w, gap = 3.4 * mm, 1.0 * mm
        meter_total = 10 * seg_w + 9 * gap
        reserved = (meter_total + 6 * mm) if self.score is not None else 0

        c.setFont(BODY_FONT, 8.8)
        c.setFillColor(colors.HexColor(INK))
        y = self.height - 13.5 * mm
        for line_text in _wrap(c, self.note, BODY_FONT, 8.8,
                               self.width - text_left - pad - reserved):
            c.drawString(text_left, y, line_text)
            y -= 4.4 * mm

        # Ten segments, filled to the score. A reader takes the meter in before
        # they read the number, which is the point of putting it there.
        if self.score is not None:
            x = self.width - pad - meter_total
            for i in range(10):
                filled = i < self.score
                c.setFillColor(colors.HexColor(strong) if filled else colors.white)
                c.setStrokeColor(colors.HexColor(strong if filled else line))
                c.setLineWidth(0.6)
                c.rect(x, 5.5 * mm, seg_w, 6.5 * mm, stroke=1, fill=1)
                x += seg_w + gap


def _wrap(canvas_obj, text: str, font: str, size: float, max_width: float,
          max_lines: int = 3) -> list[str]:
    """Greedy wrap against real glyph widths, capped at max_lines.

    Anything that does not fit ends in an ellipsis rather than being cut mid
    word, which otherwise reads as a rendering fault rather than a summary.
    """
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if canvas_obj.stringWidth(trial, font, size) <= max_width:
            current = trial
            continue
        lines.append(current or word)
        current = "" if not current else word
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    elif current:
        last = lines[-1]
        while last and canvas_obj.stringWidth(
                last + "...", font, size) > max_width:
            last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]
        lines[-1] = f"{last}..."
    return lines


# --------------------------------------------------------------------------
# Markdown to flowables
# --------------------------------------------------------------------------
# The report opens with its own "# Document Risk Rating: 9/10 — CRITICAL"
# heading. The banner above already states the score, the band and what the band
# means, so leaving both in prints the same verdict three times on one page.
_RATING_HEADING = re.compile(
    r"^\s*#{1,2}\s*(?:document\s+)?risk\s+rating\s*:.*$", re.IGNORECASE
)

_TABLE_DIVIDER = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$")
_BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
_NUMBERED = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_RULE = re.compile(r"^\s*(-{3,}|_{3,}|\*{3,})\s*$")


@dataclass
class _Row:
    cells: list[str]


def _split_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _build_table(rows: list[_Row], styles: dict[str, ParagraphStyle]) -> Table:
    """A Markdown table as a styled Table, with severity cells tinted."""
    columns = max(len(row.cells) for row in rows)
    data: list[list] = []
    severity_cells: list[tuple[int, int, str]] = []

    for r, row in enumerate(rows):
        cells = row.cells + [""] * (columns - len(row.cells))
        style = styles["cellhead"] if r == 0 else styles["cell"]
        rendered = []
        for c, cell in enumerate(cells):
            label = _plain(cell)
            if r > 0 and label.title() in SEVERITY_COLOURS:
                severity_cells.append((c, r, label.title()))
                text_colour = SEVERITY_COLOURS[label.title()][0]
                rendered.append(Paragraph(
                    f'<b><font color="{text_colour}">{_html.escape(label.upper())}'
                    f"</font></b>", styles["cell"]))
            else:
                text = _inline(cell)
                if r == 0:
                    text = text.upper() if len(text) < 40 else text
                rendered.append(Paragraph(text, style))
        data.append(rendered)

    # Two columns reads as a label/value sheet; three or more as a real table.
    if columns == 2:
        widths = [CONTENT_WIDTH * 0.32, CONTENT_WIDTH * 0.68]
    elif columns == 3:
        widths = [CONTENT_WIDTH * 0.34, CONTENT_WIDTH * 0.15, CONTENT_WIDTH * 0.51]
    else:
        widths = [CONTENT_WIDTH / columns] * columns

    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor(BRASS)),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, colors.HexColor(LINE)),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(LINE)),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(PAPER)),
    ]
    for col, row, severity in severity_cells:
        _, tint, border = SEVERITY_COLOURS[severity]
        commands.append(("BACKGROUND", (col, row), (col, row), colors.HexColor(tint)))
        commands.append(("BOX", (col, row), (col, row), 0.5, colors.HexColor(border)))
    table.setStyle(TableStyle(commands))
    return table


def _markdown_flowables(markdown: str,
                        styles: dict[str, ParagraphStyle]) -> list:
    """Walk the report line by line, emitting flowables.

    A line-based walk rather than a real parser: the input comes from one known
    generator with a fixed template, and every unmatched line still reaches the
    page as a paragraph.
    """
    story: list = []
    lines = markdown.replace("\r\n", "\n").split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if _RULE.match(stripped):
            story.append(Spacer(1, 5))
            i += 1
            continue

        # Table: a pipe row followed by a divider row.
        if (stripped.startswith("|")
                and i + 1 < len(lines) and _TABLE_DIVIDER.match(lines[i + 1])):
            rows = [_Row(_split_row(stripped))]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_Row(_split_row(lines[i])))
                i += 1
            # No spacer before the table: a heading's keepWithNext binds to the
            # very next flowable, and a Spacer sitting between them is what
            # leaves a section title stranded alone at the foot of a page.
            story.append(_build_table(rows, styles))
            story.append(Spacer(1, 9))
            continue

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped[level:].strip()
            key = "h1" if level == 1 else "h2" if level == 2 else "h3"
            story.append(Paragraph(_inline(text), styles[key]))
            if level == 1:
                story.append(_Rule(CONTENT_WIDTH, BRASS, 1.0))
                story.append(Spacer(1, 6))
            i += 1
            continue

        if stripped.startswith(">"):
            story.append(Paragraph(_inline(stripped.lstrip("> ").strip()),
                                   styles["quote"]))
            i += 1
            continue

        bullet = _BULLET.match(line)
        numbered = _NUMBERED.match(line)
        if bullet or numbered:
            pattern = _BULLET if bullet else _NUMBERED
            items, kind = [], "bullet" if bullet else "1"
            while i < len(lines):
                match = pattern.match(lines[i])
                if not match:
                    break
                items.append(ListItem(
                    Paragraph(_inline(match.group(1)), styles["bullet"]),
                    leftIndent=13,
                ))
                i += 1
            story.append(ListFlowable(
                items, bulletType=kind, start="•" if bullet else 1,
                bulletColor=colors.HexColor(BRASS),
                bulletFontName=BODY_FONT if bullet else BODY_BOLD,
                bulletFontSize=9 if bullet else 8.5,
                leftIndent=14, bulletOffsetY=-0.5 if bullet else 0,
            ))
            story.append(Spacer(1, 6))
            continue

        story.append(Paragraph(_inline(stripped), styles["body"]))
        i += 1

    return story


class _Rule(Flowable):
    """A plain horizontal rule. Cheaper than a one-cell table."""

    def __init__(self, width: float, colour: str, thickness: float = 0.6) -> None:
        super().__init__()
        self.width, self.colour, self.thickness = width, colour, thickness
        self.height = thickness

    def draw(self) -> None:
        self.canv.setStrokeColor(colors.HexColor(self.colour))
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)


# --------------------------------------------------------------------------
# Running header and footer
# --------------------------------------------------------------------------
def _decorator(footer: str, page_word: str):
    """Build the per-page callback.

    A closure rather than a module-level function because ReportLab hands the
    callback only (canvas, doc), and the running footer now has to be in the
    reader's language.
    """

    def decorate(canvas_obj, doc) -> None:
        canvas_obj.saveState()
        width, height = PAGE_SIZE

        if doc.page > 1:
            canvas_obj.setFont(BODY_BOLD, 7.2)
            canvas_obj.setFillColor(colors.HexColor(BRASS_INK))
            canvas_obj.drawString(MARGIN_X, height - 13 * mm, WORDMARK,
                                  charSpace=1.2)
            canvas_obj.setStrokeColor(colors.HexColor(LINE))
            canvas_obj.setLineWidth(0.5)
            canvas_obj.line(MARGIN_X, height - 15.5 * mm,
                            width - MARGIN_X, height - 15.5 * mm)

        canvas_obj.setStrokeColor(colors.HexColor(LINE))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(MARGIN_X, 14 * mm, width - MARGIN_X, 14 * mm)
        canvas_obj.setFont(BODY_FONT, 7.2)
        canvas_obj.setFillColor(colors.HexColor(MUTED))
        canvas_obj.drawString(MARGIN_X, 10 * mm, footer)
        canvas_obj.drawRightString(width - MARGIN_X, 10 * mm,
                                   f"{page_word} {doc.page}")
        canvas_obj.restoreState()

    return decorate


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def render_report_pdf(report_markdown: str, document_names: list[str],
                      risk_score: int | None, risk_band: str | None,
                      order_reference: str,
                      generated_on: date | None = None,
                      language: str = "en") -> bytes:
    """The finished review as PDF bytes, ready to attach."""
    lang = languages.get(language)
    text = lang.strings
    styles = _styles()
    buffer = io.BytesIO()

    doc = BaseDocTemplate(
        buffer, pagesize=PAGE_SIZE,
        leftMargin=MARGIN_X, rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM,
        title=f"Legal-Eye review {order_reference}",
        author="Legal-Eye", subject="Automated legal document review",
        creator="Legal-Eye",
    )
    frame = Frame(MARGIN_X, MARGIN_BOTTOM, CONTENT_WIDTH,
                  PAGE_SIZE[1] - MARGIN_TOP - MARGIN_BOTTOM, id="body")
    doc.addPageTemplates([
        PageTemplate(id="all", frames=[frame],
                     onPage=_decorator(text["footer"], text["page"])),
    ])

    # The band note comes from the language pack when there is one, so the
    # banner does not sit in English above a translated report.
    _, _, _, _, note = band_colours(risk_band)
    band_key = (risk_band or "").strip().title()
    if band_key in lang.bands:
        _, note = lang.bands[band_key]
    documents = ", ".join(document_names) if document_names else "your document"
    when = (generated_on or date.today()).strftime("%d %B %Y")

    body = "\n".join(
        line for line in report_markdown.replace("\r\n", "\n").split("\n")
        if not _RATING_HEADING.match(line)
    )

    story: list = [
        _CoverHeader(CONTENT_WIDTH),
        Spacer(1, 12),
        Paragraph(_html.escape(documents), styles["h1"]),
        _Rule(CONTENT_WIDTH, BRASS, 1.0),
        Spacer(1, 7),
        Paragraph(
            f"{_html.escape(text['document_review'])} &nbsp;·&nbsp; "
            f"{_html.escape(text['prepared'])} {_html.escape(when)} "
            f"&nbsp;·&nbsp; {_html.escape(text['reference'])} "
            f"{_html.escape(order_reference)}",
            styles["meta"],
        ),
        Spacer(1, 11),
        _RiskBanner(CONTENT_WIDTH, risk_score, risk_band, note,
                    lang.bands.get(band_key, (None,))[0],
                    text["risk_suffix"]),
        Spacer(1, 14),
    ]

    # A translated review says so before the reader relies on it, not in the
    # small print at the end.
    for line in languages.notices(lang):
        story.append(Paragraph(_html.escape(line), styles["meta"]))
    if languages.notices(lang):
        story.append(Spacer(1, 10))

    story.extend(_markdown_flowables(body, styles))

    # Only add the standing disclaimer if the review did not already close with
    # one. Printing it twice reads as boilerplate and gets skipped, which
    # defeats the point of having it.
    if "does not constitute legal advice" not in report_markdown:
        story.append(Spacer(1, 14))
        story.append(KeepTogether([
            _Rule(CONTENT_WIDTH, LINE),
            Spacer(1, 6),
            Paragraph(DISCLAIMER, styles["disclaimer"]),
        ]))

    doc.build(story)
    return buffer.getvalue()
