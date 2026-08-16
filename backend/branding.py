"""The Legal-Eye look, in one place.

The palette lives here rather than in the PDF module, the email module and the
Streamlit stylesheet separately, because three copies of a hex value drift. The
app page, the emailed PDF and the covering email should be recognisably the same
product, and that only holds if they read their colours from the same table.

Nothing here imports ReportLab at module level: the constants are useful to the
email builder too, which has no business pulling in a PDF engine.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Palette. Matches site/_brand.css and the Streamlit theme.
# --------------------------------------------------------------------------
INK = "#14283c"          # headings, and the header bar
INK_SOFT = "#23394f"
SLATE = "#44536a"        # body copy
MUTED = "#67748a"        # captions, footers
PAPER = "#f5f7fa"
CARD = "#ffffff"
LINE = "#dfe5ec"
LINE_STRONG = "#b9c4d1"
BRASS = "#a6782f"        # the accent: rules, the mark, small caps labels
BRASS_INK = "#8a6427"    # brass dark enough to read as text on white
BRASS_TINT = "#f4ead9"
DANGER = "#c00000"

WORDMARK = "LEGAL-EYE"
TAGLINE = "South African contract and document review"

# --------------------------------------------------------------------------
# Risk bands: strong / tint / ink / line / note.
#
# Every ink-on-tint pair here clears 4.5:1 contrast, which is what lets the band
# name stay legible at the small sizes it gets used at. Same five bands as the
# app, deliberately: a reader who saw 9/10 in red on screen should meet the same
# red in the PDF and in the email, or the colour stops meaning anything.
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

# Severity pills in the risk table. Same family as the bands, one step calmer,
# because a table of eight rows in full-strength band colour is unreadable.
SEVERITY_COLOURS: dict[str, tuple[str, str, str]] = {
    "Critical": ("#8f0000", "#fdecec", "#e8b4b4"),
    "High": ("#9c410a", "#fdf0e6", "#eec9a8"),
    "Medium": ("#7d6f00", "#fbf8e0", "#ddd18f"),
    "Low": ("#17603c", "#e9f5ee", "#a8d4bd"),
}

DEFAULT_BAND = ("#67748a", "#f5f7fa", "#44536a", "#dfe5ec",
                "No risk rating was produced for this review.")


def band_colours(band: str | None) -> tuple[str, str, str, str, str]:
    """Look up a band, tolerating whatever casing or stray words come back.

    The band is produced upstream and stored on the order, so by the time it
    reaches a renderer it has been through a database round trip. Falling back
    to neutral grey is better than raising: a review that renders without its
    colour is still a review, and one that fails to render is not.
    """
    if not band:
        return DEFAULT_BAND
    key = band.strip().title()
    if key in BANDS:
        return BANDS[key]
    for name in BANDS:
        if name.lower() in band.strip().lower():
            return BANDS[name]
    return DEFAULT_BAND


# --------------------------------------------------------------------------
# The mark: scales of justice, as line geometry rather than an image file.
#
# Vector keeps it sharp at any size and keeps a binary out of the repo, and it
# is the same four strokes the app draws as inline SVG, so the two cannot drift.
# Coordinates are the original 24x24 SVG viewBox, y increasing downward.
# --------------------------------------------------------------------------
_VIEWBOX = 24.0
_STROKE = 1.8

# (x1, y1, x2, y2) in viewBox units.
_SCALES_LINES = (
    (12.0, 4.0, 12.0, 19.0),    # the upright
    (7.0, 21.0, 17.0, 21.0),    # the foot
    (5.0, 17.0, 19.0, 17.0),    # the base rule
)
# The pan, as a closed triangle.
_SCALES_TRIANGLE = ((12.0, 6.0), (6.0, 13.0), (18.0, 13.0))


def scales_drawing(size: float = 22.0, colour: str = BRASS):
    """The scales mark as a ReportLab Drawing, ready to place in a story.

    Imported lazily so that importing this module for its colours alone does not
    drag in the graphics stack.
    """
    from reportlab.graphics.shapes import Drawing, Line, Polygon
    from reportlab.lib.colors import HexColor

    k = size / _VIEWBOX
    stroke = HexColor(colour)
    width = _STROKE * k

    def x(v: float) -> float:
        return v * k

    def y(v: float) -> float:
        # SVG measures down from the top; PDF measures up from the bottom.
        return (_VIEWBOX - v) * k

    drawing = Drawing(size, size)
    for x1, y1, x2, y2 in _SCALES_LINES:
        line = Line(x(x1), y(y1), x(x2), y(y2))
        line.strokeColor = stroke
        line.strokeWidth = width
        line.strokeLineCap = 1  # round, matching the SVG
        drawing.add(line)

    points: list[float] = []
    for px, py in _SCALES_TRIANGLE:
        points.extend([x(px), y(py)])
    pan = Polygon(points)
    pan.strokeColor = stroke
    pan.strokeWidth = width
    pan.strokeLineJoin = 1  # round
    pan.fillColor = None
    drawing.add(pan)
    return drawing
