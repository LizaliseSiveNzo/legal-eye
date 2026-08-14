"""Tests for the South African layer. No API, no network."""

import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.redaction import redact, restore  # noqa: E402
from backend.za_law import (  # noqa: E402
    AUTHORITIES,
    STATUTES,
    applicable_statutes,
    reference_block,
    unknown_citations,
)
from backend.za_validators import (  # noqa: E402
    luhn_ok,
    validate_branch_code,
    validate_cipc,
    validate_sa_id,
    validate_trust,
    validate_vat,
)

TODAY = dt.date(2026, 8, 14)


def with_check_digit(payload: str) -> str:
    return next(payload + d for d in "0123456789" if luhn_ok(payload + d))


# --- ID numbers -----------------------------------------------------------

@pytest.mark.parametrize("number", [
    "8001015009087", "7503305044089", "9001010001088",
    "0002295000083", "6012314999185",
])
def test_valid_ids(number: str) -> None:
    assert validate_sa_id(number, TODAY).valid


@pytest.mark.parametrize("number", [
    "8503305044089",      # bad checksum
    "800101500908",       # too short
    "8001015009087 ".replace("7", "8").strip(),
    "9913015009083",      # month 91
])
def test_invalid_ids(number: str) -> None:
    assert not validate_sa_id(number, TODAY).valid


def test_every_single_digit_mutation_is_caught() -> None:
    base = "8001015009087"
    for i in range(13):
        for digit in "0123456789":
            if digit != base[i]:
                assert not validate_sa_id(base[:i] + digit + base[i + 1:], TODAY).valid


def test_century_ambiguity_is_reported_not_guessed() -> None:
    number = with_check_digit("010101" + "5009" + "0" + "8")
    result = validate_sa_id(number, TODAY)
    assert len(result.data["birth_dates"]) == 2
    assert "century" in result.warnings[0].lower()


def test_future_century_is_excluded() -> None:
    result = validate_sa_id("6012314999185", TODAY)
    assert result.data["birth_dates"] == ["1960-12-31"]
    assert not result.warnings


def test_leap_day_resolves_to_the_only_possible_century() -> None:
    # 1900 was not a leap year, so 000229 can only be 2000.
    assert validate_sa_id("0002295000083", TODAY).data["birth_dates"] == ["2000-02-29"]


def test_unknown_citizenship_digit_warns_but_does_not_reject() -> None:
    result = validate_sa_id(with_check_digit("900101" + "5009" + "2" + "8"), TODAY)
    assert result.valid and "Digit 11" in result.warnings[0]


# --- other identifiers ----------------------------------------------------

def test_vat_format_rules() -> None:
    assert not validate_vat("5123456789").valid   # must start with 4
    assert not validate_vat("412345678").valid    # must be 10 digits


def test_cipc_name_and_suffix_must_agree() -> None:
    assert validate_cipc("2015/123456/07", "Acme Trading (Pty) Ltd").valid
    mismatch = validate_cipc("2015/123456/23", "Acme Trading (Pty) Ltd")
    assert mismatch.valid and mismatch.warnings


def test_company_cannot_predate_its_own_registration() -> None:
    result = validate_cipc("2026/000123/07", None, dt.date(2024, 3, 24))
    assert not result.valid and "cannot contract before it exists" in result.detail


def test_trust_number_without_an_office_letter_is_incomplete() -> None:
    assert validate_trust("IT1234/2014(G)").valid
    bare = validate_trust("IT1234/2014")
    assert not bare.valid and "not unique across the Masters" in bare.detail


def test_branch_codes() -> None:
    assert validate_branch_code("632005").valid      # Absa
    assert not validate_branch_code("999999").valid


# --- statute selection ----------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("Lease between landlord and tenant, monthly rent R12,000.", "RENTAL"),
    ("Deed of sale of Erf 123, the estate agent claims commission.", "ALIENATION_LAND"),
    ("Loan agreement, interest at prime plus 2%, instalments monthly.", "NCA"),
    ("Deed of suretyship; the surety binds himself.", "SURETYSHIP"),
    ("39,748.27 carats of rough diamonds, wire transfer in USD.", "MINERALS"),
    ("The Trust, represented by its trustees, purchases the plant.", "TRUST_PROPERTY"),
])
def test_triggers_select_the_right_statute(text: str, expected: str) -> None:
    assert expected in {s.key for s in applicable_statutes(text)}


def test_land_statute_is_not_triggered_by_the_word_landlord() -> None:
    """Substring matching once put the Alienation of Land Act on every lease."""
    keys = {s.key for s in applicable_statutes("The landlord and the tenant agree.")}
    assert "ALIENATION_LAND" not in keys


def test_wire_transfer_does_not_trigger_the_land_statute() -> None:
    keys = {s.key for s in applicable_statutes("Payment by international wire transfer.")}
    assert "ALIENATION_LAND" not in keys


def test_documents_with_no_trigger_still_get_the_general_framework() -> None:
    assert [s.key for s in applicable_statutes("qqq zzz")] == ["PRESCRIPTION", "JURISDICTION"]


def test_reference_block_states_the_citation_limit() -> None:
    block = reference_block(list(STATUTES)[:2])
    assert "You may cite ONLY what appears below" in block


# --- citation policing ----------------------------------------------------

def test_real_citations_pass_the_guard() -> None:
    text = ("Under the Consumer Protection Act 68 of 2008 s 51 and Beadica 231 CC "
            "[2020] ZACC 13, read with Barkhuizen v Napier [2007] ZACC 5.")
    assert unknown_citations(text) == []


def test_fabricated_citations_are_flagged() -> None:
    text = ("The Imaginary Widgets Act 12 of 2099 applies, per Nobody v Someone "
            "[2024] ZACC 99. The Companies Act 71 of 2008 also applies.")
    flagged = unknown_citations(text)
    assert "[2024] ZACC 99" in flagged
    assert any("Imaginary Widgets Act 12 of 2099" in c for c in flagged)
    assert not any("Companies Act 71" in c for c in flagged)


def test_every_authority_is_self_consistent() -> None:
    for authority in AUTHORITIES:
        assert unknown_citations(authority.citation) == [], authority.name


# --- redaction ------------------------------------------------------------

def test_identifiers_are_removed_before_transmission() -> None:
    doc = ("Surety J Dlamini, ID 8001015009087, account number 1234567890, "
           "j.dlamini@example.co.za, +27 82 555 1234. Invoice 9988776655443.")
    result = redact(doc)
    for value in ("8001015009087", "1234567890", "j.dlamini@example.co.za"):
        assert value not in result.text
    # A 13-digit run that is not a valid ID must survive for the analysis.
    assert "9988776655443" in result.text


def test_one_person_gets_one_token() -> None:
    """The model must still see that the same person appears twice."""
    result = redact("ID 8001015009087 and again 8001015009087.")
    assert result.text.count("[SA_ID_1]") == 2


def test_restore_is_exact() -> None:
    result = redact("ID 8001015009087, mail a@b.co.za")
    assert restore(result.text, result.mapping) == "ID 8001015009087, mail a@b.co.za"


def test_restore_handles_double_digit_token_numbers() -> None:
    """[SA_ID_1] must not clobber [SA_ID_11]."""
    mapping = {f"[SA_ID_{i}]": f"value{i}" for i in range(1, 13)}
    text = " ".join(mapping)
    restored = restore(text, mapping)
    assert "value11" in restored and "[SA_ID" not in restored


def test_redaction_summary_admits_what_it_does_not_cover() -> None:
    assert "Names are not redacted" in redact("ID 8001015009087").summary()
