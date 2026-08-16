"""The covering email, built as HTML that survives real mail clients.

Three constraints shape everything here, and they are worth stating because the
result looks dated if you do not know why:

1. **Tables, not divs.** Outlook on Windows renders through Word, which ignores
   flexbox, grid and most positioning. Nested tables are the only layout that
   holds everywhere.
2. **Inline styles only.** Gmail strips <style> blocks in several contexts, so
   any rule that matters is written on the element itself.
3. **No images.** Gmail refuses data: URIs on <img>, and a remote logo would be
   blocked until the reader clicks "display images" — which means the brand mark
   would be invisible exactly when first impressions are formed. The wordmark is
   therefore typographic, and it renders identically everywhere. Once
   legal-eye.co.za serves assets, a hosted PNG can replace it.

The plain-text alternative is not a courtesy. Some clients refuse HTML outright,
and a message with no text/plain part scores worse with spam filters.
"""

from __future__ import annotations

import html

from backend.branding import (
    BRASS, INK, LINE, MUTED, PAPER, SLATE, TAGLINE, WORDMARK, band_colours,
)


def _row(label: str, value: str) -> str:
    return (
        f'<tr>'
        f'<td style="padding:6px 14px 6px 0;font:400 12px/18px Arial,Helvetica,'
        f'sans-serif;color:{MUTED};white-space:nowrap;vertical-align:top;">'
        f'{html.escape(label)}</td>'
        f'<td style="padding:6px 0;font:400 13px/19px Arial,Helvetica,sans-serif;'
        f'color:{INK};">{value}</td>'
        f'</tr>'
    )


def build_html(document_names: list[str], risk_score: int | None,
               risk_band: str | None, order_reference: str,
               attachment_name: str) -> str:
    """The branded covering email."""
    strong, tint, band_ink, band_line, note = band_colours(risk_band)
    documents = ", ".join(document_names) if document_names else "your document"
    documents_safe = html.escape(documents)
    band_name = (risk_band or "Unrated").title()

    # Single quotes around the font name: this sits inside a double-quoted HTML
    # attribute, and a nested double quote silently truncates the whole style.
    score_block = (
        f'<td style="padding:0 18px 0 0;font:700 34px/34px Georgia,'
        f"'Times New Roman',serif;"
        f'color:{band_ink};white-space:nowrap;vertical-align:middle;">'
        f'{risk_score}'
        f'<span style="font:400 15px/15px Arial,Helvetica,sans-serif;">/10</span></td>'
    ) if risk_score is not None else ""

    preheader = (
        f"Your Legal-Eye review of {documents} is attached. "
        f"Risk rating {risk_score} out of 10, {band_name}."
        if risk_score is not None
        else f"Your Legal-Eye review of {documents} is attached."
    )

    return f"""<!DOCTYPE html>
<html lang="en-ZA"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Your Legal-Eye review</title></head>
<body style="margin:0;padding:0;background:{PAPER};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">
{html.escape(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
 border="0" style="background:{PAPER};padding:26px 12px;">
<tr><td align="center">

<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
 style="width:600px;max-width:100%;background:#ffffff;border:1px solid {LINE};">

  <!-- Header -->
  <tr><td style="background:{INK};padding:22px 30px 20px 30px;">
    <div style="font:700 21px/24px Georgia,'Times New Roman',serif;color:#ffffff;
      letter-spacing:2.5px;">{WORDMARK}</div>
    <div style="font:400 12px/18px Arial,Helvetica,sans-serif;color:#c7d2dd;
      padding-top:4px;">{TAGLINE}</div>
  </td></tr>
  <tr><td style="background:{BRASS};font-size:0;line-height:0;height:3px;">&nbsp;</td></tr>

  <!-- Body -->
  <tr><td style="padding:30px 30px 8px 30px;">
    <p style="margin:0 0 16px 0;font:400 15px/23px Arial,Helvetica,sans-serif;
      color:{SLATE};">Your review of <strong style="color:{INK};">{documents_safe}</strong>
      is attached to this email as a PDF.</p>

    <!-- Risk band -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
      style="background:{tint};border:1px solid {band_line};border-left:5px solid {strong};">
      <tr><td style="padding:16px 20px;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
          <tr>
            {score_block}
            <td style="vertical-align:middle;">
              <div style="font:700 11px/15px Arial,Helvetica,sans-serif;
                color:{band_ink};letter-spacing:1.6px;text-transform:uppercase;">
                {html.escape(band_name)} risk</div>
              <div style="font:400 13px/19px Arial,Helvetica,sans-serif;
                color:{INK};padding-top:3px;">{html.escape(note)}</div>
            </td>
          </tr>
        </table>
      </td></tr>
    </table>

    <!-- Details -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
      style="padding:22px 0 4px 0;">
      {_row("Attachment", html.escape(attachment_name))}
      {_row("Reference", html.escape(order_reference))}
      {_row("Contains", "Priority findings, red flags, obligations, a risk table "
            "with severities, and recommended actions.")}
    </table>
  </td></tr>

  <!-- Disclaimer -->
  <tr><td style="padding:8px 30px 26px 30px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
      style="background:{PAPER};border-left:3px solid {BRASS};">
      <tr><td style="padding:14px 16px;font:400 12px/18px Arial,Helvetica,sans-serif;
        color:{MUTED};">
        <strong style="color:{INK};">Not legal advice.</strong> This review was
        produced by an automated tool for information only. It creates no attorney
        and client relationship, and it must not be used to prepare documents for
        court proceedings. AI systems can misstate or invent legal authorities, so
        verify every statutory reference and case citation against a primary South
        African source before relying on it. Consult an admitted South African
        legal practitioner before acting.
      </td></tr>
    </table>
  </td></tr>

  <!-- Footer -->
  <tr><td style="background:{INK};padding:20px 30px;">
    <div style="font:700 12px/16px Georgia,'Times New Roman',serif;color:{BRASS};
      letter-spacing:1.8px;">{WORDMARK}</div>
    <div style="font:400 11px/17px Arial,Helvetica,sans-serif;color:#9fb0c0;
      padding-top:7px;">
      You are receiving this because you asked for this review to be emailed to
      you. It is a once-off delivery, not a subscription. Your address is used to
      deliver this review and to keep the order record, and reports are removed
      from our records after the retention period.
    </div>
  </td></tr>

</table>
</td></tr></table>
</body></html>"""


def build_text(document_names: list[str], risk_score: int | None,
               risk_band: str | None, order_reference: str,
               attachment_name: str) -> str:
    """The text/plain alternative. Same facts, no markup."""
    documents = ", ".join(document_names) if document_names else "your document"
    rating = (f"Risk rating: {risk_score} out of 10 ({risk_band}).\n"
              if risk_score is not None else "")
    return (
        f"{WORDMARK}\n{TAGLINE}\n\n"
        f"Your review of {documents} is attached to this email as a PDF "
        f"({attachment_name}).\n\n"
        f"{rating}"
        "\nThis review was produced by an automated tool for information only. "
        "It is not legal advice, it creates no attorney and client relationship, "
        "and it must not be used to prepare documents for court proceedings. AI "
        "systems can misstate or invent legal authorities, so verify every "
        "statutory reference and case citation against a primary South African "
        "source before relying on it. Consult an admitted South African legal "
        "practitioner before acting.\n\n"
        f"Order reference: {order_reference}\n"
        "\nYou are receiving this because you asked for this report to be "
        "emailed to you. It is a once-off delivery and not a subscription.\n"
    )
