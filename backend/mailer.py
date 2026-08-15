"""Delivering a finished report by email.

Like payments, the provider sits behind a protocol so the delivery flow does not
change when the sending service does. The console sender keeps local development
working with no account and no risk of mailing a real person by accident.
"""

from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol


class EmailError(RuntimeError):
    """Raised when a report could not be sent."""


@dataclass(frozen=True)
class Message:
    to: str
    subject: str
    body_text: str
    attachment_name: str
    attachment_text: str


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
              f"({len(message.attachment_text):,} chars)")
        return f"console-{len(self.sent)}"


class ResendSender:
    """Transactional email through Resend.

    Deliverability is mostly a DNS problem, not a code problem. SPF, DKIM and
    DMARC records have to exist on the sending domain or reports will land in
    spam, which for a paid product reads as a failed purchase.
    """

    name = "resend"
    endpoint = "https://api.resend.com/emails"

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
            "text": message.body_text,
            "attachments": [{
                "filename": message.attachment_name,
                "content": base64.b64encode(
                    message.attachment_text.encode("utf-8")).decode("ascii"),
            }],
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8")).get("id", "")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            raise EmailError(f"Resend rejected the message ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise EmailError(f"Could not reach Resend: {exc.reason}") from exc


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
        email.add_attachment(message.attachment_text.encode("utf-8"),
                             maintype="text", subtype="markdown",
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


def build_message(to: str, report: str, document_names: list[str],
                  risk_score: int | None, risk_band: str | None,
                  order_reference: str) -> Message:
    """Compose the delivery email. Plain and factual, no marketing."""
    documents = ", ".join(document_names) if document_names else "your document"
    rating = (f"Risk rating: {risk_score} out of 10 ({risk_band}).\n"
              if risk_score is not None else "")
    subject = f"Your Legal-Eye review of {documents}"
    if risk_band:
        subject = f"Your Legal-Eye review ({risk_band} risk): {documents}"

    body = (
        f"Your review of {documents} is attached.\n\n"
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
    filename = "legal-eye-review.md"
    if document_names:
        stem = document_names[0].rsplit(".", 1)[0][:60].replace(" ", "_")
        filename = f"{stem}_review.md"
    return Message(to=to, subject=subject, body_text=body,
                   attachment_name=filename, attachment_text=report)
