"""Deterministic forensic checks over facts extracted from a document.

Nothing in this module calls an API. Every finding is arithmetic, calendar
maths, or string comparison, so it is reproducible and auditable, and a
language model cannot hallucinate it away. The division of labour is
deliberate: the model reads the document and reports what it says; this module
checks whether what it says holds together.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

# Free consumer mailboxes. Legitimate for individuals; a signal when a
# counterparty uses one to transact six or seven figures.
FREE_EMAIL_DOMAINS = frozenset({
    "gmail.com", "yahoo.com", "yahoo.co.uk", "hotmail.com", "hotmail.co.uk",
    "outlook.com", "live.com", "msn.com", "aol.com", "gmx.com", "gmx.net",
    "mail.com", "yandex.com", "yandex.ru", "icloud.com", "me.com",
    "protonmail.com", "proton.me", "inbox.com", "rediffmail.com", "web.de",
})

# High-volume registered-agent and virtual-office addresses. Using one is not
# improper — thousands of real companies do — but it means the address is not
# an operating office, which matters when it is offered as evidence of substance.
MASS_AGENT_ADDRESS_FRAGMENTS = (
    "centerville road", "centreville road", "little falls drive",
    "orange street", "corporation trust center", "registered agents inc",
    "kemp house", "124 city road", "71-75 shelton street", "shelton street",
    "harley street", "regus", "wework", "mail boxes etc", "virtual office",
)

# Category words that mark industrial, damaged or waste material in a graded
# schedule. Matched case-insensitively against each line's label.
LOW_GRADE_KEYWORDS = (
    "boart", "bort", "industrial", "reject", "cube", "round", "damage",
    "cleavage", "clivage", "coated", "chip", "crushing", "grit", "mixed",
    "scrap", "waste", "off-grade", "offgrade", "broken", "no form",
)

_ENTITY_SUFFIXES = frozenset({
    "limited", "ltd", "inc", "incorporated", "llc", "llp", "lp", "plc",
    "corp", "corporation", "company", "co", "gmbh", "ag", "sa", "sarl",
    "bv", "nv", "pty", "pte", "spa", "srl", "oy", "ab", "as",
})

# Spellings of the same legal form, so "Acme Ltd" and "Acme Limited" are read
# as one entity rather than two.
_SUFFIX_ALIASES = {
    "ltd": "limited", "inc": "incorporated", "corp": "corporation",
    "co": "company", "plc": "public limited company",
}

_MONEY_CLEAN = re.compile(r"[^0-9.\-]")


@dataclass(frozen=True)
class Finding:
    """One deterministic observation about the document's internal consistency."""

    code: str
    severity: str
    headline: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.headline} — {self.detail}"


# --------------------------------------------------------------------------
# Coercion helpers. Extraction returns model-authored JSON, so assume nothing.
# --------------------------------------------------------------------------

def _money(value: object) -> float | None:
    """Coerce an extracted amount to a float, tolerating '$1,391,189.00' and 1391189."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if not isinstance(value, str):
        return None
    cleaned = _MONEY_CLEAN.sub("", value)
    if cleaned in ("", "-", ".", "-."):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _date(value: object) -> dt.date | None:
    """Parse an ISO date (YYYY-MM-DD). Anything else is treated as unknown."""
    if not isinstance(value, str):
        return None
    try:
        return dt.date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def _flag(facts: dict, key: str) -> bool | None:
    """Read a tri-state boolean: True, False, or None for 'not determined'."""
    value = facts.get(key)
    return value if isinstance(value, bool) else None


def _rows(facts: dict, key: str) -> list[dict]:
    """Return a list-of-dicts field, discarding malformed entries."""
    value = facts.get(key)
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _fmt(amount: float) -> str:
    return f"{amount:,.2f}"


def _entity_parts(name: str) -> tuple[str, str, str]:
    """Split a name into (head word, distinctive stem, canonical legal form)."""
    words = [w for w in re.sub(r"[^a-z0-9 ]", " ", name.lower()).split() if w]
    form: list[str] = []
    while words and words[-1] in _ENTITY_SUFFIXES:
        form.insert(0, words.pop())
    canonical = " ".join(_SUFFIX_ALIASES.get(w, w) for w in form)
    return (words[0] if words else ""), " ".join(words), canonical


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def check_payment_arithmetic(facts: dict) -> list[Finding]:
    """Reconcile the payment schedule against the stated total."""
    total = _money((facts.get("total_consideration") or {}).get("amount"))
    schedule = _rows(facts, "payment_schedule")
    amounts = [a for a in (_money(p.get("amount")) for p in schedule) if a is not None]
    if total is None or len(amounts) < 2:
        return []

    difference = total - sum(amounts)
    if abs(difference) < 0.005:
        return []

    parts = " + ".join(_fmt(a) for a in amounts)
    return [Finding(
        "MATH_TOTAL_MISMATCH",
        "medium",
        "Payment schedule does not reconcile to the stated total",
        f"The instalments sum to {_fmt(sum(amounts))} ({parts}), but the document "
        f"states a total of {_fmt(total)} — a difference of {_fmt(abs(difference))}. "
        "A document that specifies figures to the cent should reconcile exactly.",
    )]


def check_advance_exposure(facts: dict) -> list[Finding]:
    """Quantify money that leaves the buyer before they can verify what they bought."""
    total = _money((facts.get("total_consideration") or {}).get("amount"))
    advance = 0.0
    labels: list[str] = []
    for payment in _rows(facts, "payment_schedule"):
        amount = _money(payment.get("amount"))
        if amount is None:
            continue
        if payment.get("payable_before_delivery") is True:
            advance += amount
            labels.append(str(payment.get("label") or "instalment"))

    if advance <= 0:
        return []

    escrow = _flag(facts, "escrow_present")
    inspection = _flag(facts, "inspection_rights_present")
    refund = _flag(facts, "refund_mechanism_present")
    unprotected = escrow is False and (inspection is False or refund is False)

    share = f" ({advance / total * 100:.1f}% of the total)" if total else ""
    gaps = [name for name, present in
            (("escrow", escrow), ("inspection rights", inspection),
             ("refund mechanism", refund)) if present is False]
    gap_text = "no " + ", no ".join(gaps) if gaps else "no stated protection"

    return [Finding(
        "ADVANCE_UNPROTECTED" if unprotected else "ADVANCE_EXPOSURE",
        "critical" if unprotected else "high",
        "Funds leave the buyer before the goods or services can be verified",
        f"{_fmt(advance)}{share} is payable before delivery ({', '.join(labels)}), "
        f"and the document provides {gap_text}. Money paid on this basis is "
        "recoverable only by litigation against the counterparty, wherever it "
        "is found.",
    )]


def check_unit_price(facts: dict) -> list[Finding]:
    """Derive the unit price and flag a single flat rate applied to graded goods."""
    total = _money((facts.get("total_consideration") or {}).get("amount"))
    quantity_row = facts.get("quantity") or {}
    quantity = _money(quantity_row.get("value"))
    if total is None or not quantity:
        return []

    unit = total / quantity
    unit_name = str(quantity_row.get("unit") or "unit")
    graded = _flag(facts, "goods_are_graded_or_heterogeneous")
    is_round = abs(unit - round(unit)) < 0.0001 and round(unit) % 10 == 0

    if is_round and graded is True:
        return [Finding(
            "PRICE_FLAT_ON_GRADED_GOODS",
            "high",
            "One flat unit price applied across goods of widely different value",
            f"The price works out to exactly {_fmt(unit)} per {unit_name} "
            f"({_fmt(total)} / {quantity:,.2f}). The document itself describes the "
            "goods as falling into different grades or categories. Graded goods are "
            "priced lot by lot; a single round rate across all of them means the "
            "price is not derived from what is actually being sold.",
        )]
    if is_round:
        return [Finding(
            "PRICE_SUSPICIOUSLY_ROUND",
            "low",
            "Unit price is an exactly round figure",
            f"{_fmt(unit)} per {unit_name}. Worth confirming the price was derived "
            "from a valuation rather than chosen for convenience.",
        )]
    return [Finding(
        "PRICE_DERIVED",
        "info",
        "Derived unit price",
        f"{_fmt(unit)} per {unit_name} ({_fmt(total)} / {quantity:,.2f}).",
    )]


def check_entity_identity(facts: dict) -> list[Finding]:
    """Detect the same trading name appearing under different legal forms."""
    names: list[str] = []
    for party in _rows(facts, "parties"):
        name = party.get("name")
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    signatory_entity = (facts.get("signatory") or {}).get("entity")
    if isinstance(signatory_entity, str) and signatory_entity.strip():
        names.append(signatory_entity.strip())

    # Group by head word; within a group, a differing stem or a differing legal
    # form means a separate legal person wearing a familiar name.
    groups: dict[str, dict[tuple[str, str], set[str]]] = {}
    for name in names:
        head, stem, form = _entity_parts(name)
        if len(head) < 4:
            continue
        groups.setdefault(head, {}).setdefault((stem, form), set()).add(name)

    findings = []
    for head, variants in groups.items():
        if len(variants) < 2:
            continue
        listed = "; ".join(sorted({n for group in variants.values() for n in group}))
        findings.append(Finding(
            "ENTITY_MISMATCH",
            "high",
            "Related trading names used across two or more distinct legal entities",
            f"The name '{head}' appears as: {listed}. These are different legal "
            "persons. Confirm which entity holds the rights being disposed of, "
            "which is party to the contract, and which receives payment — and "
            "whether any document actually transfers anything between them.",
        ))
    return findings


def check_dates(facts: dict) -> list[Finding]:
    """Flag official acts dated to a weekend and deadlines that compress diligence."""
    findings: list[Finding] = []
    document_date = _date(facts.get("document_date"))

    for row in _rows(facts, "key_dates"):
        when = _date(row.get("date"))
        if when is None:
            continue
        label = str(row.get("label") or "date")

        if row.get("is_official_act") is True and when.weekday() >= 5:
            findings.append(Finding(
                "DATE_WEEKEND_OFFICIAL_ACT",
                "medium",
                "Official act dated to a weekend",
                f"{label} is dated {when.isoformat()}, a {when.strftime('%A')}. "
                "Government bodies and registries rarely transact at weekends. "
                "Confirm this directly with the issuing office.",
            ))

        if row.get("is_deadline") is True and document_date is not None:
            days = (when - document_date).days
            if 0 <= days <= 10:
                findings.append(Finding(
                    "DATE_COMPRESSED_DEADLINE",
                    "high",
                    "Deadline leaves too little time for verification",
                    f"{label} falls {days} day(s) after the document date "
                    f"({document_date.isoformat()} to {when.isoformat()}). Diligence, "
                    "bank verification and legal review do not fit in that window. "
                    "Urgency that prevents checking is itself a risk factor, "
                    "independent of whether the deadline is genuine.",
                ))
    return findings


def check_quantity_consistency(facts: dict) -> list[Finding]:
    """Flag figures stated in the same unit that do not agree across the bundle."""
    by_unit: dict[str, list[tuple[str, float]]] = {}
    for row in _rows(facts, "quantities_mentioned"):
        value = _money(row.get("value"))
        unit = str(row.get("unit") or "").strip().lower()
        if value is None or not unit:
            continue
        label = str(row.get("label") or row.get("source") or "unlabelled")
        by_unit.setdefault(unit, []).append((label, value))

    findings = []
    for unit, entries in by_unit.items():
        distinct = {value for _, value in entries}
        if len(distinct) < 2:
            continue
        listed = "; ".join(f"{label}: {value:,.2f}" for label, value in entries)
        findings.append(Finding(
            "QUANTITY_MISMATCH",
            "medium",
            f"Figures in {unit} do not agree across the document bundle",
            f"{listed}. Reconcile these before relying on any of them — an "
            "unexplained gap between a source figure and a transaction figure "
            "means part of the chain is undocumented.",
        ))
    return findings


def check_counterparty_signals(facts: dict) -> list[Finding]:
    """Check contact details offered as evidence of the counterparty's substance."""
    findings: list[Finding] = []
    total = _money((facts.get("total_consideration") or {}).get("amount")) or 0.0

    for email in facts.get("contact_emails") or []:
        if not isinstance(email, str) or "@" not in email:
            continue
        domain = email.rsplit("@", 1)[1].strip().lower()
        if domain in FREE_EMAIL_DOMAINS:
            findings.append(Finding(
                "CONTACT_FREE_WEBMAIL",
                "high" if total >= 100_000 else "medium",
                "Counterparty transacts from a free consumer mailbox",
                f"'{email}' is a free webmail address"
                + (f", used here for a transaction of {_fmt(total)}. " if total else ". ")
                + "It carries no domain ownership, no organisational control, and "
                "can be created and abandoned in minutes.",
            ))

    for address in facts.get("addresses") or []:
        if not isinstance(address, str):
            continue
        lowered = address.lower()
        for fragment in MASS_AGENT_ADDRESS_FRAGMENTS:
            if fragment in lowered:
                findings.append(Finding(
                    "ADDRESS_MASS_AGENT",
                    "medium",
                    "Address is a registered-agent or serviced-office location",
                    f"'{address}' matches a high-volume company-formation or "
                    "virtual-office address. Legitimate businesses use these, but "
                    "it is not an operating office and is not evidence of substance.",
                ))
                break
    return findings


def check_payment_instructions(facts: dict) -> list[Finding]:
    """A document demanding a wire should say where the money goes."""
    if not _rows(facts, "payment_schedule"):
        return []
    if _flag(facts, "bank_details_present") is not False:
        return []
    return [Finding(
        "WIRE_NO_ACCOUNT_DETAILS",
        "high",
        "Payment demanded, but no account details appear in the document",
        "Settlement instructions would therefore arrive by separate message. That "
        "is the standard route for payment-diversion fraud, and it means the "
        "destination account is never fixed by anything the parties both signed. "
        "Require account details within the executed document, and confirm them "
        "by voice on a number obtained independently.",
    )]


def check_execution_status(facts: dict) -> list[Finding]:
    """Guard against describing an unexecuted document as binding."""
    if _flag(facts, "signed_by_all_parties") is not False:
        return []
    return [Finding(
        "NOT_COUNTERSIGNED",
        "medium",
        "Document is not executed by all parties",
        "It records one side's position. Describing it as a binding agreement "
        "overstates its status, and either party's obligations may be arguable.",
    )]


def check_missing_protections(facts: dict) -> list[Finding]:
    """Report standard protections the document does not contain."""
    has_advance = any(
        p.get("payable_before_delivery") is True for p in _rows(facts, "payment_schedule")
    )
    checks = (
        ("governing_law_stated", "medium", "No governing law",
         "No system of law is chosen, so which law applies would itself be the "
         "first thing litigated."),
        ("dispute_resolution_stated", "medium", "No dispute resolution mechanism",
         "No forum, arbitration seat or process is agreed, leaving enforcement to "
         "whichever court will take jurisdiction."),
        ("inspection_rights_present", "high" if has_advance else "medium",
         "No right to inspect before paying",
         "The buyer cannot verify quality, quantity or authenticity before the "
         "money is irrecoverable."),
        ("refund_mechanism_present", "high" if has_advance else "medium",
         "No refund or unwind mechanism",
         "Nothing states what happens to funds already transferred if the "
         "transaction does not complete."),
        ("escrow_present", "high" if has_advance else "low", "No escrow",
         "Nothing holds the money independently until each side has performed."),
    )
    findings = []
    for key, severity, headline, detail in checks:
        if _flag(facts, key) is False:
            findings.append(Finding(f"MISSING_{key.upper()}", severity, headline, detail))
    return findings


def check_grade_composition(facts: dict) -> list[Finding]:
    """Measure how much of a graded parcel sits in its lowest-value categories.

    Keyword matching is a heuristic and deliberately conservative: it only
    reports when the low-grade share is large enough that no reasonable reading
    of the schedule makes the headline description accurate.
    """
    rows = _rows(facts, "grade_breakdown")
    if not rows:
        return []

    total_quantity = 0.0
    low_quantity = 0.0
    low_labels: list[str] = []
    for row in rows:
        value = _money(row.get("value"))
        if value is None or value <= 0:
            continue
        total_quantity += value
        label = str(row.get("label") or "")
        if any(word in label.lower() for word in LOW_GRADE_KEYWORDS):
            low_quantity += value
            low_labels.append(label)

    if total_quantity <= 0 or low_quantity <= 0:
        return []

    share = low_quantity / total_quantity
    if share < 0.40:
        return []

    unit_name = str((facts.get("quantity") or {}).get("unit") or "unit")
    detail = (
        f"{low_quantity:,.2f} of {total_quantity:,.2f} {unit_name}s "
        f"({share * 100:.1f}%) fall into the schedule's lowest-value categories "
        f"({', '.join(low_labels[:6])}"
        + (", and others" if len(low_labels) > 6 else "")
        + ")."
    )

    total = _money((facts.get("total_consideration") or {}).get("amount"))
    quantity = _money((facts.get("quantity") or {}).get("value"))
    if total and quantity:
        unit_price = total / quantity
        detail += (
            f" At the derived price of {_fmt(unit_price)} per {unit_name}, that "
            f"portion alone accounts for {_fmt(low_quantity * unit_price)} of the "
            f"{_fmt(total)} total."
        )
    detail += (
        " A headline description covering the whole quantity therefore does not "
        "describe most of what is being sold."
    )

    return [Finding(
        "COMPOSITION_LOW_GRADE_MAJORITY",
        "critical" if share >= 0.75 else "high",
        "Most of the quantity sits in the lowest-value categories",
        detail,
    )]


ALL_CHECKS = (
    check_payment_arithmetic,
    check_advance_exposure,
    check_unit_price,
    check_grade_composition,
    check_entity_identity,
    check_dates,
    check_quantity_consistency,
    check_counterparty_signals,
    check_payment_instructions,
    check_execution_status,
    check_missing_protections,
)


def run_checks(facts: dict) -> list[Finding]:
    """Run every check, most severe first. A broken check never sinks the run."""
    findings: list[Finding] = []
    for check in ALL_CHECKS:
        try:
            findings.extend(check(facts))
        except Exception:  # A malformed extraction must not abort the analysis.
            continue
    findings.sort(key=lambda f: (SEVERITY_RANK.get(f.severity, 9), f.code))
    return findings


def findings_block(findings: list[Finding]) -> str:
    """Render findings for injection into the analysis prompt."""
    if not findings:
        return "No deterministic inconsistencies were detected in the extracted facts."
    return "\n".join(f"- {finding}" for finding in findings)


# --------------------------------------------------------------------------
# Overall rating
# --------------------------------------------------------------------------

# The worst finding sets a floor; everything else adds on top. Summing alone
# let a single Critical finding score mid-range, which understated it, and let
# a pile of trivia outrank one severe defect.
SEVERITY_FLOORS = {"critical": 7.0, "high": 4.0, "medium": 2.0, "low": 1.0}
SEVERITY_INCREMENTS = {
    "critical": 1.0, "high": 0.4, "medium": 0.3, "low": 0.05, "info": 0.0,
}

RISK_BANDS = ((9, "Critical"), (7, "High"), (5, "Elevated"), (3, "Moderate"), (1, "Low"))


def risk_score(findings: list[Finding]) -> tuple[int, str]:
    """Score the document 1-10 from its findings, with a band label.

    Deterministic on purpose: the same findings always produce the same number,
    so the rating can be defended rather than argued about.
    """
    floor = max(
        (SEVERITY_FLOORS.get(f.severity, 1.0) for f in findings if f.severity != "info"),
        default=1.0,
    )
    total = floor + sum(SEVERITY_INCREMENTS.get(f.severity, 0.0) for f in findings)
    score = max(1, min(10, round(total)))
    band = next(name for threshold, name in RISK_BANDS if score >= threshold)
    return score, band
