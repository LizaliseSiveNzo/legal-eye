"""The legal pages are a disclosure, so they are tested like one.

Three things are worth failing a build over: a page that still contains an
unfilled placeholder, a page that claims VAT is included when the business is
not a registered vendor, and a page that describes a paid service when charging
is switched off. Each has a test below.
"""

from __future__ import annotations

import re

import pytest

from backend import config, legal_pages
from backend.business import NOT_SET, Business

PAGES = (legal_pages.about_markdown,
         legal_pages.terms_markdown,
         legal_pages.privacy_markdown)


def flat(text: str) -> str:
    """Collapse whitespace so assertions survive markdown line wrapping.

    Without this, a phrase like "**full refund**" that happens to wrap across
    two source lines reads as "full\\nrefund" and a substring check fails for a
    reason that has nothing to do with the page being wrong.
    """
    return re.sub(r"\s+", " ", text)


@pytest.fixture
def complete() -> Business:
    """A business with every mandatory disclosure supplied."""
    return Business(
        proprietor_name="A B Example",
        physical_address="1 Example Street, Cape Town, 8001",
        phone="+27 21 000 0000",
        support_email="help@example.co.za",
    )


@pytest.fixture
def incomplete() -> Business:
    """A business missing the details that cannot be guessed."""
    return Business(
        proprietor_name="A B Example",
        physical_address=NOT_SET,
        phone=NOT_SET,
        support_email="help@example.co.za",
    )


# --- The placeholders this work was meant to remove ------------------------

def test_no_double_bracket_placeholders_survive(complete):
    """The old static pages carried 38 of these. None may reach a reader."""
    for page in PAGES:
        assert not re.search(r"\[\[[A-Z_]+\]\]", page(complete))


def test_complete_business_renders_no_warning_banner(complete):
    for page in PAGES:
        assert "TO BE COMPLETED BEFORE LAUNCH" not in page(complete)


def test_incomplete_business_is_flagged_loudly(incomplete):
    """A missing address must be impossible to miss, on the page and in code."""
    assert not incomplete.is_publishable()
    assert "Physical address (ECTA s 43(1)(b))" in incomplete.missing_disclosures()

    terms = legal_pages.terms_markdown(incomplete)
    assert "This page is not ready to publish" in terms
    assert NOT_SET in terms


# --- VAT. A wrong claim here is an offence, not a typo ---------------------

def test_no_page_claims_vat_is_included(complete):
    assert complete.vat_registered is False
    for page in PAGES:
        assert "including VAT" not in page(complete)
        assert "incl VAT" not in page(complete)


def test_terms_state_the_business_is_not_a_vat_vendor(complete):
    assert "not a registered VAT vendor" in legal_pages.terms_markdown(complete)


# --- Sole proprietorship, not a company ------------------------------------

def test_terms_do_not_invent_a_registration_number_or_directors(complete):
    """Row (f) must answer the question, not supply a fabricated number.

    The row *label* legitimately contains the words "registration number", so
    the thing to assert is that the answer disclaims one rather than inventing
    a CIPC-shaped value.
    """
    terms = flat(legal_pages.terms_markdown(complete))

    assert "sole proprietorship is not a registered legal entity" in terms
    assert "has no registration number" in terms
    assert "no directors or other office bearers" in terms
    # Nothing anywhere on the page may look like a CIPC number (2019/123456/07)
    # or a SARS VAT number (10 digits starting with 4).
    assert not re.search(r"\b\d{4}/\d{6}/\d{2}\b", terms)
    assert not re.search(r"\b4\d{9}\b", terms)


def test_privacy_names_the_proprietor_as_information_officer(complete):
    assert complete.information_officer == "A B Example"
    assert "A B Example" in legal_pages.privacy_markdown(complete)


# --- The pages must describe the software that is actually running ---------

def test_free_mode_terms_do_not_describe_a_payment(complete, monkeypatch):
    """Charging off is the current default, so this is the shipped wording."""
    monkeypatch.setattr(config, "PAYMENTS_ENABLED", False)
    assert complete.charging is False

    terms = flat(legal_pages.terms_markdown(complete))
    assert "currently provided free of charge" in terms
    assert "nothing to refund" in terms
    # No sale means s 44 has nothing to attach to, so the consent box must not
    # be described as though the reader will see one.
    assert "tick the delivery box" not in terms


def test_charging_mode_terms_restore_the_cooling_off_machinery(
        complete, monkeypatch):
    monkeypatch.setattr(config, "PAYMENTS_ENABLED", True)
    assert complete.charging is True

    terms = flat(legal_pages.terms_markdown(complete))
    assert "42(2)(d)" in terms
    assert "full refund" in terms
    assert complete.price_display in terms


def test_cross_border_transfer_is_disclosed_with_a_country(complete):
    privacy = legal_pages.privacy_markdown(complete)
    assert "section 72" in privacy
    assert complete.ai_provider_country in privacy
    assert "do not upload it" in privacy


def test_about_counts_come_from_the_pack_not_from_prose(complete):
    """The static site still says 17 statutes. These numbers are computed."""
    from backend import za_law

    about = legal_pages.about_markdown(complete)
    assert f"{len(za_law.STATUTES)} South African statutes" in about
    assert f"{len(za_law.AUTHORITIES)} leading judgments" in about


def test_retention_period_matches_config(complete):
    from backend import config

    privacy = legal_pages.privacy_markdown(complete)
    assert f"{config.REPORT_RETENTION_DAYS} days" in privacy


# --- Cross-links between the pages resolve to real Streamlit routes --------

def test_internal_links_point_at_the_app_pages(complete):
    """/Privacy and /Terms are the routes Streamlit derives from pages/*.py."""
    assert "(/Privacy)" in legal_pages.terms_markdown(complete)
    assert "(/Privacy)" in legal_pages.about_markdown(complete)
    for page in PAGES:
        assert "legal-eye.co.za" not in page(complete)
