"""Tests for the deterministic checks. No API, no network, no model involved.

The fixture is a real document that a soft summary got wrong: a 2024 offer
letter for a parcel of rough diamonds. Every check below fires on facts the
first-generation single-pass summary missed entirely.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.forensics import (  # noqa: E402
    Finding,
    check_grade_composition,
    check_advance_exposure,
    check_counterparty_signals,
    check_dates,
    check_entity_identity,
    check_execution_status,
    check_payment_arithmetic,
    check_payment_instructions,
    check_quantity_consistency,
    check_unit_price,
    findings_block,
    risk_score,
    run_checks,
)


@pytest.fixture
def diamond_offer() -> dict:
    """Facts as pass 1 would extract them from the offer letter and its exhibits."""
    return {
        "document_type": "Commercial offer letter",
        "document_date": "2024-03-24",
        "parties": [
            {"name": "Centreville Trading Limited", "role": "Seller",
             "source": "main document"},
            {"name": "Centreville Group, Inc", "role": "Contracting party",
             "source": "attachment"},
            {"name": "Africapacity Brawn Investment Group", "role": "Buyer",
             "source": "main document"},
        ],
        "signatory": {"name": "P. Sagaspe", "title": "CEO",
                      "entity": "Centreville Group, Inc"},
        "signed_by_all_parties": False,
        "total_consideration": {"amount": 3974827.00, "currency": "USD"},
        "payment_schedule": [
            {"label": "Deposit on verification", "amount": 1391189.00,
             "due": "immediately", "payable_before_delivery": True},
            {"label": "Balance at release", "amount": 2583637.55,
             "due": "at release", "payable_before_delivery": True},
        ],
        "payment_method": "international wire transfer",
        "bank_details_present": False,
        "quantity": {"value": 39748.27, "unit": "carat",
                     "description": "rough diamonds"},
        "goods_are_graded_or_heterogeneous": True,
        "quantities_mentioned": [
            {"label": "Parcel awarded", "value": 39748.27, "unit": "carat",
             "source": "award schedule"},
            {"label": "Offered at tender", "value": 53824.21, "unit": "carat",
             "source": "tender invitation"},
        ],
        "key_dates": [
            {"label": "Award by state body", "date": "2024-03-23",
             "is_official_act": True, "is_deadline": False},
            {"label": "Completion before Easter weekend", "date": "2024-03-29",
             "is_official_act": False, "is_deadline": True},
        ],
        "contact_emails": ["centrevillegroup@yahoo.com"],
        "addresses": ["Centreville Road, Suite 400, Wilmington, Delaware 19808"],
        "governing_law_stated": False,
        "dispute_resolution_stated": False,
        "escrow_present": False,
        "inspection_rights_present": False,
        "refund_mechanism_present": False,
    }


def codes(findings: list[Finding]) -> set[str]:
    return {finding.code for finding in findings}


def test_detects_the_forty_five_cent_discrepancy(diamond_offer: dict) -> None:
    """1,391,189.00 + 2,583,637.55 is 0.45 short of the stated 3,974,827.00."""
    findings = check_payment_arithmetic(diamond_offer)
    assert codes(findings) == {"MATH_TOTAL_MISMATCH"}
    assert "0.45" in findings[0].detail


def test_reconciled_schedule_produces_no_finding(diamond_offer: dict) -> None:
    diamond_offer["payment_schedule"][1]["amount"] = 2583638.00
    assert check_payment_arithmetic(diamond_offer) == []


def test_flat_round_price_on_graded_goods_is_high(diamond_offer: dict) -> None:
    """3,974,827.00 / 39,748.27 ct is exactly $100.00 across every grade."""
    findings = check_unit_price(diamond_offer)
    assert codes(findings) == {"PRICE_FLAT_ON_GRADED_GOODS"}
    assert findings[0].severity == "high"
    assert "100.00" in findings[0].detail


def test_uniform_goods_only_get_a_low_note(diamond_offer: dict) -> None:
    diamond_offer["goods_are_graded_or_heterogeneous"] = False
    assert codes(check_unit_price(diamond_offer)) == {"PRICE_SUSPICIOUSLY_ROUND"}


def test_unprotected_advance_is_critical(diamond_offer: dict) -> None:
    findings = check_advance_exposure(diamond_offer)
    assert findings[0].code == "ADVANCE_UNPROTECTED"
    assert findings[0].severity == "critical"


def test_escrow_downgrades_the_advance_finding(diamond_offer: dict) -> None:
    diamond_offer["escrow_present"] = True
    assert check_advance_exposure(diamond_offer)[0].severity == "high"


def test_limited_and_inc_are_caught_as_different_entities(diamond_offer: dict) -> None:
    findings = check_entity_identity(diamond_offer)
    assert codes(findings) == {"ENTITY_MISMATCH"}
    assert "Centreville Trading Limited" in findings[0].detail
    assert "Centreville Group, Inc" in findings[0].detail


def test_single_legal_form_is_not_flagged(diamond_offer: dict) -> None:
    diamond_offer["parties"] = [
        {"name": "Acme Trading Ltd", "role": "Seller", "source": "main document"}
    ]
    diamond_offer["signatory"]["entity"] = "Acme Trading Ltd"
    assert check_entity_identity(diamond_offer) == []


def test_weekend_official_act_and_five_day_deadline(diamond_offer: dict) -> None:
    findings = check_dates(diamond_offer)
    assert codes(findings) == {"DATE_WEEKEND_OFFICIAL_ACT", "DATE_COMPRESSED_DEADLINE"}
    weekend = next(f for f in findings if f.code == "DATE_WEEKEND_OFFICIAL_ACT")
    assert "Saturday" in weekend.detail


def test_tender_and_award_quantities_disagree(diamond_offer: dict) -> None:
    findings = check_quantity_consistency(diamond_offer)
    assert codes(findings) == {"QUANTITY_MISMATCH"}
    assert "53,824.21" in findings[0].detail


def test_free_webmail_and_agent_address(diamond_offer: dict) -> None:
    findings = check_counterparty_signals(diamond_offer)
    assert codes(findings) == {"CONTACT_FREE_WEBMAIL", "ADDRESS_MASS_AGENT"}
    webmail = next(f for f in findings if f.code == "CONTACT_FREE_WEBMAIL")
    assert webmail.severity == "high"  # because the transaction is over $100k


def test_corporate_domain_is_not_flagged(diamond_offer: dict) -> None:
    diamond_offer["contact_emails"] = ["deals@centrevilletrading.co.uk"]
    diamond_offer["addresses"] = ["12 Mining House, Johannesburg"]
    assert check_counterparty_signals(diamond_offer) == []


def test_wire_demanded_without_account_details(diamond_offer: dict) -> None:
    assert codes(check_payment_instructions(diamond_offer)) == {"WIRE_NO_ACCOUNT_DETAILS"}


def test_unexecuted_document_is_flagged(diamond_offer: dict) -> None:
    assert codes(check_execution_status(diamond_offer)) == {"NOT_COUNTERSIGNED"}


def test_full_run_is_ordered_by_severity(diamond_offer: dict) -> None:
    findings = run_checks(diamond_offer)
    severities = [f.severity for f in findings]
    assert severities[0] == "critical"
    assert severities == sorted(
        severities, key=lambda s: ["critical", "high", "medium", "low", "info"].index(s)
    )
    assert len(findings) >= 10


def test_empty_facts_produce_no_findings_and_no_crash() -> None:
    assert run_checks({}) == []
    assert "No deterministic inconsistencies" in findings_block([])


def test_malformed_facts_do_not_raise() -> None:
    """Pass 1 is model output, so every field must survive being the wrong type."""
    garbage = {
        "total_consideration": "not a dict",
        "payment_schedule": ["not a dict", {"amount": "??"}],
        "parties": None,
        "key_dates": [{"date": "not-a-date", "is_deadline": True}],
        "quantity": {"value": "abc", "unit": None},
        "contact_emails": [None, 42, "no-at-sign"],
        "addresses": [None],
    }
    assert isinstance(run_checks(garbage), list)


def test_amounts_written_as_strings_are_still_reconciled(diamond_offer: dict) -> None:
    """Models return '$1,391,189.00' as often as 1391189.0."""
    diamond_offer["total_consideration"]["amount"] = "$3,974,827.00"
    diamond_offer["payment_schedule"][0]["amount"] = "$1,391,189.00"
    diamond_offer["payment_schedule"][1]["amount"] = "$2,583,637.55"
    assert codes(check_payment_arithmetic(diamond_offer)) == {"MATH_TOTAL_MISMATCH"}


# ---------------------------------------------------------------------------
# Grade composition — the finding a soft summary describes only qualitatively
# ---------------------------------------------------------------------------

@pytest.fixture
def graded_parcel(diamond_offer: dict) -> dict:
    """The MIBA schedule: gem material at the top, waste categories underneath."""
    diamond_offer["grade_breakdown"] = [
        {"label": "Special / gem stones", "value": 1500.00},
        {"label": "Sawable D colour", "value": 2000.00},
        {"label": "Makeable H4 colour", "value": 3176.75},
        {"label": "Mixed boart", "value": 8353.19},
        {"label": "Coated rejections (+5 cts)", "value": 4670.96},
        {"label": "Coated rejections (-21+15)", "value": 4229.20},
        {"label": "Industrials -21+1", "value": 4603.45},
        {"label": "Cubes & rounds -21+1", "value": 2642.75},
        {"label": "Cubes & rounds +21", "value": 3296.65},
        {"label": "Coated cleavages", "value": 3377.64},
    ]
    return diamond_offer


def test_low_grade_majority_is_measured_not_described(graded_parcel: dict) -> None:
    findings = check_grade_composition(graded_parcel)
    assert codes(findings) == {"COMPOSITION_LOW_GRADE_MAJORITY"}
    assert findings[0].severity == "critical"  # over 75% of the quantity
    assert "82.4%" in findings[0].detail  # the share, computed not guessed
    assert "100.00" in findings[0].detail  # priced at the derived unit rate


def test_gem_parcel_does_not_trip_the_composition_check(graded_parcel: dict) -> None:
    graded_parcel["grade_breakdown"] = [
        {"label": "Gem sawable D-F", "value": 30000.00},
        {"label": "Mixed boart", "value": 2000.00},
    ]
    assert check_grade_composition(graded_parcel) == []


def test_no_schedule_means_no_composition_finding(diamond_offer: dict) -> None:
    assert check_grade_composition(diamond_offer) == []


# ---------------------------------------------------------------------------
# Risk score — deterministic, so it can be defended rather than argued about
# ---------------------------------------------------------------------------

def make(severity: str, count: int = 1) -> list[Finding]:
    return [Finding(f"C{i}", severity, "headline", "detail") for i in range(count)]


@pytest.mark.parametrize(
    "findings, expected",
    [
        ([], (1, "Low")),
        (make("medium"), (2, "Low")),
        (make("medium", 3), (3, "Moderate")),
        (make("high"), (4, "Moderate")),
        (make("high", 3), (5, "Elevated")),
        (make("high", 7), (7, "High")),
        (make("critical"), (8, "High")),
        (make("critical", 2), (9, "Critical")),
    ],
)
def test_risk_score_curve(findings: list[Finding], expected: tuple[int, str]) -> None:
    assert risk_score(findings) == expected


def test_worst_finding_sets_the_floor(diamond_offer: dict) -> None:
    """One Critical finding must outrank a pile of Mediums, not be averaged into them."""
    assert risk_score(make("critical"))[0] > risk_score(make("medium", 8))[0]


def test_score_is_capped_and_never_below_one() -> None:
    assert risk_score(make("critical", 20)) == (10, "Critical")
    assert risk_score(make("info", 5))[0] == 1


def test_real_document_scores_at_the_top(graded_parcel: dict) -> None:
    score, band = risk_score(run_checks(graded_parcel))
    assert (score, band) == (10, "Critical")
