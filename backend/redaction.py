"""Pseudonymise personal identifiers before text leaves South Africa.

POPIA s 72 restricts transferring personal information to a third party in a
foreign country. Legal-Eye sends document text to an AI provider outside the
Republic, and the data subjects in a contract are usually NOT the person
uploading it — they are the counterparty's directors, sureties and employees,
who cannot consent through your user. The cleanest answer is not to transfer
their information at all: replace it with tokens before the call and restore
the real values in the rendered report, which never leaves the machine.

SCOPE — read this before relying on it. This module removes high-confidence
IDENTIFIERS: ID numbers, tax and VAT numbers, email addresses, telephone
numbers and labelled account numbers. It does NOT remove personal NAMES, which
cannot be found reliably by pattern alone. Names in a document are still
personal information. This materially reduces the s 72 exposure; it does not
eliminate it. Treat it as one control among several, and have the position
confirmed by a South African legal practitioner.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.za_validators import luhn_ok, validate_sa_id

# Ordered: longer, more specific identifiers first, so a 13-digit ID is never
# consumed by a 10-digit pattern.
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_ID13 = re.compile(r"(?<!\d)\d{13}(?!\d)")
_TEN = re.compile(r"(?<!\d)\d{10}(?!\d)")
_PHONE = re.compile(r"(?:\+27|\b0)(?:\s?\d){9}\b")
_ACCOUNT = re.compile(
    r"((?:account|acc|a/c|rekening)\s*(?:number|no\.?|nr\.?|#)?\s*[:\-]?\s*)(\d{6,13})",
    re.IGNORECASE,
)


@dataclass
class Redaction:
    """Redacted text plus the mapping needed to put the real values back."""

    text: str
    mapping: dict[str, str] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.mapping)

    def summary(self) -> str:
        if not self.mapping:
            return "No personal identifiers were detected to redact."
        parts = ", ".join(f"{n} x {k.lower()}" for k, n in sorted(self.counts.items()))
        return (f"{self.total} personal identifier(s) replaced before transmission "
                f"({parts}). Names are not redacted — see backend/redaction.py.")


def redact(text: str) -> Redaction:
    """Replace personal identifiers with stable tokens.

    Each distinct value gets one token, so the model still sees that the same
    person appears in two places — which matters, because cross-referencing a
    signatory against a director is exactly the kind of finding we want kept.
    """
    result = Redaction(text=text or "")
    counters: dict[str, int] = {}
    seen: dict[str, str] = {}

    def token_for(kind: str, value: str) -> str:
        if value in seen:
            return seen[value]
        counters[kind] = counters.get(kind, 0) + 1
        token = f"[{kind}_{counters[kind]}]"
        seen[value] = token
        result.mapping[token] = value
        result.counts[kind] = counters[kind]
        return token

    def swap(pattern: re.Pattern[str], kind: str, guard=None) -> None:
        def replace(match: re.Match[str]) -> str:
            value = match.group(0)
            if guard is not None and not guard(value):
                return value
            return token_for(kind, value)

        result.text = pattern.sub(replace, result.text)

    # Account numbers first: the label anchors them, and the digits would
    # otherwise be swallowed by the generic numeric patterns below.
    def account(match: re.Match[str]) -> str:
        return match.group(1) + token_for("ACCOUNT", match.group(2))

    result.text = _ACCOUNT.sub(account, result.text)

    swap(_EMAIL, "EMAIL")
    # Only redact a 13-digit run that actually validates as an ID, so invoice
    # and reference numbers of the same length survive for the analysis.
    swap(_ID13, "SA_ID", lambda v: validate_sa_id(v).valid)
    swap(_TEN, "TAX_NUMBER", lambda v: v[0] in "012349" and luhn_ok(v))
    swap(_PHONE, "PHONE")

    return result


def restore(markdown: str, mapping: dict[str, str]) -> str:
    """Put the real values back into the finished report."""
    if not mapping:
        return markdown
    restored = markdown or ""
    # Longest tokens first so [SA_ID_11] is not clobbered by [SA_ID_1].
    for token in sorted(mapping, key=len, reverse=True):
        restored = restored.replace(token, mapping[token])
    return restored
