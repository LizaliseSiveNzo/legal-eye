"""Arithmetic validation of South African identifiers.

Every check here is a checksum, a date, or a format comparison — no API calls
and no model involvement, so results are reproducible and auditable.

A caveat that belongs in the output as much as in this docstring: a valid
checksum proves a number is *well formed*, never that it *exists*. Confirming
existence needs a real lookup — CIPC via BizPortal, a VAT number via the SARS
Vendor Search, an ID via a Home Affairs bureau. The findings say which is which.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

# CIPC entity-type suffixes. CIPC publishes no authoritative list — the
# convention is administrative, inherited from CIPRO, not statutory. The first
# five are well corroborated across sources; the rest are single-source, so an
# unrecognised suffix is reported, never rejected.
CIPC_SUFFIXES = {
    "06": "public company (Ltd)",
    "07": "private company ((Pty) Ltd)",
    "08": "non-profit company (NPC)",
    "21": "personal liability company (Inc)",
    "23": "close corporation (CC)",
    "09": "company limited by guarantee",
    "10": "external company",
    "22": "unlimited company",
    "24": "primary co-operative",
    "25": "secondary co-operative",
    "26": "tertiary co-operative",
    "30": "state-owned company (SOC Ltd)",
    "31": "statutory body",
}
CIPC_SUFFIXES_CORROBORATED = frozenset({"06", "07", "08", "21", "23"})

# Name endings that should agree with the registration suffix.
NAME_SUFFIX_TO_CODE = (
    ("(pty) ltd", "07"), ("pty ltd", "07"), ("proprietary limited", "07"),
    ("npc", "08"), ("soc ltd", "30"),
    ("close corporation", "23"), (" cc", "23"),
    (" inc", "21"), ("incorporated", "21"),
)

# Universal branch codes for the major South African banks.
UNIVERSAL_BRANCH_CODES = {
    "632005": "Absa", "250655": "FNB / FirstRand", "051001": "Standard Bank",
    "198765": "Nedbank", "470010": "Capitec", "450105": "Capitec Business",
    "580105": "Investec", "430000": "African Bank", "679000": "Discovery Bank",
    "462005": "Bidvest Bank", "678910": "TymeBank / GoTyme", "888000": "Bank Zero",
    "683000": "Sasfin", "584000": "Grindrod", "410105": "Access Bank SA",
    "460005": "SA Postbank", "587000": "HSBC", "589000": "Finbond Mutual",
    "490991": "Standard Bank (MTN)", "801000": "State Bank of India",
}

_CIPC_RE = re.compile(r"^((?:19|20)\d{2}|\d{2})\s*/\s*(\d{1,6})\s*/\s*(\d{2})$")
_TRUST_RE = re.compile(r"^(IT|MT)\s*(\d+)\s*/\s*(\d{4})\s*(?:\(\s*([A-Z]{1,2})\s*\))?$", re.I)


@dataclass
class IdentifierResult:
    """Outcome of validating one identifier."""

    kind: str
    value: str
    valid: bool
    detail: str
    warnings: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def luhn_ok(number: str) -> bool:
    """Standard Luhn (mod 10) over the whole string, check digit included."""
    if not number.isdigit():
        return False
    total = 0
    for index, char in enumerate(reversed(number)):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _birth_dates(yy: int, mm: int, dd: int, today: dt.date) -> list[dt.date]:
    """Return every century-plausible reading of a YYMMDD prefix.

    The century is not encoded in an SA ID number, so it cannot be recovered
    from the number alone. Returning both candidates and reconciling against
    the document beats silently picking one and misdating anyone born before
    the current century's cutoff.
    """
    candidates = []
    for century in (1900, 2000):
        try:
            candidate = dt.date(century + yy, mm, dd)
        except ValueError:
            continue  # e.g. 29 February in a non-leap century
        if candidate <= today:
            candidates.append(candidate)
    return candidates


def validate_sa_id(value: str, today: dt.date | None = None) -> IdentifierResult:
    """Validate a 13-digit South African ID number.

    Layout YYMMDD SSSS C A Z: date of birth, gender sequence (0000-4999 female,
    5000-9999 male), citizenship, a discontinued apartheid-era classifier that
    is deliberately not decoded here, and a Luhn check digit.
    """
    today = today or dt.date.today()
    number = _digits(value)
    warnings: list[str] = []

    if len(number) != 13:
        return IdentifierResult("sa_id", value, False,
                                f"Expected 13 digits, found {len(number)}.")

    if not luhn_ok(number):
        return IdentifierResult("sa_id", value, False,
                                "Fails the Luhn check digit — the number is not "
                                "internally consistent.")

    dates = _birth_dates(int(number[0:2]), int(number[2:4]), int(number[4:6]), today)
    if not dates:
        return IdentifierResult("sa_id", value, False,
                                f"Digits 1-6 ({number[0:6]}) are not a valid date "
                                "of birth in any century.")

    gender = "male" if int(number[6:10]) >= 5000 else "female"

    citizenship_digit = number[10]
    citizenship = {"0": "SA citizen", "1": "permanent resident"}.get(citizenship_digit)
    if citizenship is None:
        citizenship = f"unrecognised citizenship digit ({citizenship_digit})"
        warnings.append(
            f"Digit 11 is '{citizenship_digit}'. Only 0 (citizen) and 1 (permanent "
            "resident) are standard; some sources report 2 for refugees. Confirm "
            "with the Department of Home Affairs."
        )

    if len(dates) > 1:
        warnings.append(
            "The century is not encoded in an SA ID number, so the date of birth "
            f"is either {dates[0].isoformat()} or {dates[1].isoformat()}. "
            "Reconcile against the document."
        )

    shown = " or ".join(d.isoformat() for d in dates)
    return IdentifierResult(
        "sa_id", value, True,
        f"Checksum valid. Date of birth {shown}, {gender}, {citizenship}.",
        warnings,
        {"birth_dates": [d.isoformat() for d in dates], "gender": gender,
         "citizenship": citizenship},
    )


def validate_vat(value: str) -> IdentifierResult:
    """Validate a SARS VAT number: 10 digits, first digit 4, Luhn."""
    number = _digits(value)
    if len(number) != 10:
        return IdentifierResult("vat", value, False,
                                f"A VAT number is 10 digits; found {len(number)}.")
    if not number.startswith("4"):
        return IdentifierResult("vat", value, False,
                                f"A VAT number starts with 4; this starts with "
                                f"{number[0]}.")
    if not luhn_ok(number):
        # Deliberately a warning rather than a rejection: the Luhn basis is
        # strongly indicated by independent implementations but was not
        # confirmed against a published known-valid number.
        return IdentifierResult(
            "vat", value, False,
            "Format is right but the checksum fails. Verify against the SARS VAT "
            "Vendor Search before treating this as invalid.",
            ["The SARS VAT checksum basis is inferred, not published. Treat a "
             "failure as a prompt to verify, not as proof of forgery."],
        )
    return IdentifierResult("vat", value, True,
                            "Format and checksum valid. Confirm the registered "
                            "name via the SARS VAT Vendor Search.")


def validate_tax_reference(value: str) -> IdentifierResult:
    """Validate a SARS income tax reference: 10 digits, leading 0/1/2/3/9, Luhn."""
    number = _digits(value)
    if len(number) != 10:
        return IdentifierResult("tax_ref", value, False,
                                f"Expected 10 digits, found {len(number)}.")
    if number[0] not in "01239":
        return IdentifierResult("tax_ref", value, False,
                                f"An income tax reference starts with 0, 1, 2, 3 "
                                f"or 9; this starts with {number[0]}.")
    if not luhn_ok(number):
        return IdentifierResult("tax_ref", value, False, "Fails the checksum.")
    return IdentifierResult("tax_ref", value, True, "Format and checksum valid.")


def validate_cipc(value: str, entity_name: str | None = None,
                  document_date: dt.date | None = None) -> IdentifierResult:
    """Validate a CIPC registration number: YYYY/NNNNNN/NN.

    There is no checksum, so this is format, year plausibility and suffix
    agreement only — which is still enough to catch the common errors.
    """
    match = _CIPC_RE.match((value or "").strip())
    if not match:
        return IdentifierResult("company_registration", value, False,
                                "Does not match the CIPC format YYYY/NNNNNN/NN.")

    year_text, sequence, suffix = match.groups()
    year = int(year_text) if len(year_text) == 4 else (
        1900 + int(year_text) if int(year_text) > 30 else 2000 + int(year_text)
    )
    warnings: list[str] = []

    entity_type = CIPC_SUFFIXES.get(suffix)
    if entity_type is None:
        warnings.append(f"Suffix /{suffix} is not a recognised entity-type code. "
                        "CIPC publishes no authoritative list, so confirm against "
                        "a CIPC disclosure certificate rather than assuming.")
    elif suffix not in CIPC_SUFFIXES_CORROBORATED:
        warnings.append(f"Suffix /{suffix} is reported as {entity_type}, but that "
                        "code is weakly corroborated. Confirm with CIPC.")

    if year < 1900 or year > dt.date.today().year:
        return IdentifierResult("company_registration", value, False,
                                f"Registration year {year} is not plausible.")

    if document_date is not None and year > document_date.year:
        return IdentifierResult(
            "company_registration", value, False,
            f"The company was registered in {year}, but the document is dated "
            f"{document_date.isoformat()}. An entity cannot contract before it "
            "exists — check whether the number, the date, or the party is wrong.",
        )

    if entity_name:
        lowered = " " + entity_name.lower().strip()
        for ending, expected in NAME_SUFFIX_TO_CODE:
            if lowered.endswith(ending):
                if expected != suffix:
                    warnings.append(
                        f"The name ends '{ending.strip()}', which implies "
                        f"/{expected} ({CIPC_SUFFIXES.get(expected)}), but the "
                        f"number ends /{suffix} "
                        f"({entity_type or 'unrecognised'}). One of them is wrong."
                    )
                break

    described = entity_type or f"unrecognised type /{suffix}"
    return IdentifierResult(
        "company_registration", value, True,
        f"Format valid. Registered {year}, {described}. There is no checksum in a "
        "CIPC number — confirm existence and status via BizPortal.",
        warnings, {"year": year, "suffix": suffix, "entity_type": entity_type},
    )


def validate_trust(value: str) -> IdentifierResult:
    """Validate a Master's Office trust number, e.g. IT1234/2014(G).

    The office letter is not decoration. The 15 Masters' offices allocated
    sequences independently, so an IT number without its office suffix is not
    nationally unique and cannot identify a trust.
    """
    match = _TRUST_RE.match((value or "").strip())
    if not match:
        return IdentifierResult("trust", value, False,
                                "Does not match the Master's Office format, "
                                "e.g. IT1234/2014(G).")
    prefix, sequence, year, office = match.groups()
    if not office:
        return IdentifierResult(
            "trust", value, False,
            f"{prefix.upper()}{sequence}/{year} has no Master's Office letter. "
            "Trust numbers are not unique across the Masters' offices, so this "
            "does not identify a trust on its own — the same number exists in "
            "other offices. Ask for the full reference.",
        )
    return IdentifierResult("trust", value, True,
                            f"Format valid: {prefix.upper()}{sequence}/{year}, "
                            f"Master's Office {office.upper()}. Confirm the "
                            "trustees' letters of authority separately.",
                            [], {"office": office.upper(), "year": int(year)})


def validate_branch_code(value: str) -> IdentifierResult:
    """Check a 6-digit universal branch code against the known banks."""
    code = _digits(value)
    if len(code) != 6:
        return IdentifierResult("branch_code", value, False,
                                f"A branch code is 6 digits; found {len(code)}.")
    bank = UNIVERSAL_BRANCH_CODES.get(code)
    if bank is None:
        return IdentifierResult("branch_code", value, False,
                                "Not a universal branch code for any major South "
                                "African bank. It may be a legacy branch-specific "
                                "code — confirm with the bank.")
    return IdentifierResult("branch_code", value, True, f"Universal branch code for {bank}.")


VALIDATORS = {
    "sa_id": lambda v, **kw: validate_sa_id(v),
    "vat": lambda v, **kw: validate_vat(v),
    "tax_ref": lambda v, **kw: validate_tax_reference(v),
    "company_registration": lambda v, **kw: validate_cipc(
        v, kw.get("entity_name"), kw.get("document_date")),
    "trust": lambda v, **kw: validate_trust(v),
    "branch_code": lambda v, **kw: validate_branch_code(v),
}


def validate(kind: str, value: str, **context) -> IdentifierResult | None:
    """Dispatch to the validator for `kind`, or None if the kind is unknown."""
    validator = VALIDATORS.get((kind or "").strip().lower())
    return validator(value, **context) if validator else None
