"""Delivering a finished report by email.

Like payments, the provider sits behind a protocol so the delivery flow does not
change when the sending service does. The console sender keeps local development
working with no account and no risk of mailing a real person by accident.
"""

from __future__ import annotations

import logging
import re
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol


class EmailError(RuntimeError):
    """Raised when a report could not be sent."""


@dataclass(frozen=True)
class Message:
    """One outbound email: an HTML body, a text fallback, and one attachment.

    The attachment is bytes rather than str because it is now a PDF. Keeping it
    binary means the same field can carry any future format without another
    round of changes through every sender.
    """

    to: str
    subject: str
    body_text: str
    body_html: str
    attachment_name: str
    attachment_bytes: bytes
    attachment_type: str = "application/pdf"


class EmailSender(Protocol):
    name: str

    def send(self, message: Message) -> str:
        """Send the message and return a provider message id, or raise."""


class ConsoleSender:
    """Prints instead of sending. Default in development."""

    name = "console"

    def __init__(self) -> None:
        self.sent: list[Message] = []

    def send(self, message: Message) -> str:
        self.sent.append(message)
        print(f"[email] to={message.to} subject={message.subject!r} "
              f"attachment={message.attachment_name} "
              f"({len(message.attachment_bytes):,} bytes)")
        return f"console-{len(self.sent)}"


def _describe(status: int, body: str) -> str:
    """Turn a rejected HTTP response into one readable sentence.

    Raw bodies were being pasted into the page untouched, so a Cloudflare block
    page arrived as "error code: 1010" run together with the sentence after it.
    Worth the few lines: this text is the only thing anyone sees when a delivery
    fails, and the whole cost of a vague error is an evening spent guessing.
    """
    import json as _json
    import re as _re

    text = _re.sub(r"<[^>]+>", " ", body)
    text = _re.sub(r"\s+", " ", text).strip()

    if "1010" in text and "error code" in text.lower():
        return ("The request was blocked by Resend's firewall before it reached "
                "their API, which usually means the sending code is missing a "
                "User-Agent header.")

    try:
        parsed = _json.loads(body)
    except ValueError:
        parsed = None
    if isinstance(parsed, dict):
        text = str(parsed.get("message") or parsed.get("error") or text).strip()

    text = text[:300].rstrip()
    if text and not text.endswith((".", "!", "?")):
        text += "."
    return f"Resend rejected the message ({status}): {text or 'no detail given.'}"


class ResendSender:
    """Transactional email through Resend.

    Deliverability is mostly a DNS problem, not a code problem. SPF, DKIM and
    DMARC records have to exist on the sending domain or reports will land in
    spam, which for a paid product reads as a failed purchase.
    """

    name = "resend"
    endpoint = "https://api.resend.com/emails"

    # Resend sits behind Cloudflare, which screens callers by client signature.
    # urllib's default "Python-urllib/3.x" is on the blocked list, so the send
    # never reached Resend at all: Cloudflare answered 403 with "error code:
    # 1010" and the account's own API log stayed empty, which read as though the
    # app had never called out. An honest, specific User-Agent clears it.
    user_agent = "legal-eye/1.0 (+https://legal-eye.co.za)"

    def __init__(self, api_key: str, sender: str) -> None:
        if not api_key:
            raise EmailError("RESEND_API_KEY is not set.")
        self.api_key = api_key
        self.sender = sender

    def send(self, message: Message) -> str:
        import base64
        import json
        import urllib.error
        import urllib.request

        payload = {
            "from": self.sender,
            "to": [message.to],
            "subject": message.subject,
            # Both parts, deliberately. A message with no text/plain alternative
            # scores worse with spam filters, and some clients refuse HTML.
            "text": message.body_text,
            "html": message.body_html,
            "attachments": [{
                "filename": message.attachment_name,
                "content": base64.b64encode(
                    message.attachment_bytes).decode("ascii"),
                "content_type": message.attachment_type,
            }],
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json",
                     "Accept": "application/json",
                     "User-Agent": self.user_agent},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8")).get("id", "")
        except urllib.error.HTTPError as exc:
            raise EmailError(_describe(exc.code,
                                       exc.read().decode("utf-8", "replace"))) from exc
        except urllib.error.URLError as exc:
            raise EmailError(f"Could not reach Resend: {exc.reason}.") from exc


class SMTPSender:
    """Plain SMTP, for an existing mailbox. Watch the daily sending limits."""

    name = "smtp"

    def __init__(self, host: str, port: int, username: str, password: str,
                 sender: str) -> None:
        self.host, self.port = host, port
        self.username, self.password, self.sender = username, password, sender

    def send(self, message: Message) -> str:
        email = EmailMessage()
        email["From"] = self.sender
        email["To"] = message.to
        email["Subject"] = message.subject
        email.set_content(message.body_text)
        email.add_alternative(message.body_html, subtype="html")
        maintype, _, subtype = message.attachment_type.partition("/")
        email.add_attachment(message.attachment_bytes,
                             maintype=maintype or "application",
                             subtype=subtype or "octet-stream",
                             filename=message.attachment_name)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                server.starttls(context=ssl.create_default_context())
                if self.username:
                    server.login(self.username, self.password)
                server.send_message(email)
        except (smtplib.SMTPException, OSError) as exc:
            raise EmailError(f"Could not send the report: {exc}") from exc
        return email["Message-ID"] or "smtp"


_SAFE_STEM = re.compile(r"[^A-Za-z0-9._-]+")


def attachment_filename(document_names: list[str]) -> str:
    """A filename a mail client and a Windows desktop will both accept.

    Anything outside letters, digits, dot, dash and underscore is replaced:
    quotes and semicolons in a filename break the Content-Disposition header,
    and colons and slashes are illegal on Windows. The reader's own document
    name is worth keeping, so it is cleaned rather than discarded.
    """
    if not document_names:
        return "legal-eye-review.pdf"
    stem = document_names[0].rsplit(".", 1)[0][:60]
    stem = _SAFE_STEM.sub("_", stem).strip("_")
    return f"{stem}_review.pdf" if stem else "legal-eye-review.pdf"


def build_message(to: str, report: str, document_names: list[str],
                  risk_score: int | None, risk_band: str | None,
                  order_reference: str) -> Message:
    """Compose the delivery email: branded HTML, text fallback, PDF attached.

    The PDF is rendered here rather than upstream so that every path to a
    delivery produces the same document. A retry from the order store has no
    access to the Streamlit session, only to the stored Markdown, so the Markdown
    has to remain the single source the attachment is built from.
    """
    from backend.email_template import build_html, build_text
    from backend.report_pdf import render_report_pdf

    documents = ", ".join(document_names) if document_names else "your document"
    subject = f"Your Legal-Eye review of {documents}"
    if risk_band:
        subject = f"Your Legal-Eye review ({risk_band} risk): {documents}"

    filename = attachment_filename(document_names)
    content_type = "application/pdf"
    try:
        attachment = render_report_pdf(report, document_names, risk_score,
                                       risk_band, order_reference)
    except Exception as exc:  # noqa: BLE001 - deliberate catch-all, see below
        # Typesetting must never cost the reader their review. This path touches
        # fonts, table layout and whatever Markdown the model happened to
        # produce, so it has more ways to fail than the rest of delivery put
        # together. Falling back to the Markdown means the reader still gets a
        # readable review; raising here would mean they get nothing.
        logging.getLogger(__name__).warning(
            "PDF rendering failed for order %s, falling back to Markdown: %s",
            order_reference, exc,
        )
        filename = filename.removesuffix(".pdf") + ".md"
        attachment = report.encode("utf-8")
        content_type = "text/markdown"

    return Message(
        to=to,
        subject=subject,
        body_text=build_text(document_names, risk_score, risk_band,
                             order_reference, filename),
        body_html=build_html(document_names, risk_score, risk_band,
                             order_reference, filename),
        attachment_name=filename,
        attachment_bytes=attachment,
        attachment_type=content_type,
    )
