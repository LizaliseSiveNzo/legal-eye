"""Tests for the common-law doctrine pack and the expanded citation guard."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.sa_doctrines import (  # noqa: E402
    CORE_AUTHORITY_KEYS,
    DOCTRINES,
    applicable_doctrines,
    doctrine_block,
    select_authorities,
)
from backend.za_law import (  # noqa: E402
    AUTHORITIES,
    STATUTES,
    authority_by_citation,
    reference_block,
    unknown_citations,
)


# --- doctrine pack integrity -----------------------------------------------


def test_every_doctrine_authority_resolves() -> None:
    by_citation = authority_by_citation()
    for doctrine in DOCTRINES:
        for key in doctrine.authority_keys:
            assert key in by_citation, f"{doctrine.key} cites unknown {key}"


def test_every_core_authority_resolves() -> None:
    by_citation = authority_by_citation()
    for key in CORE_AUTHORITY_KEYS:
        assert key in by_citation, key


def test_every_authority_is_self_consistent() -> None:
    for authority in AUTHORITIES:
        assert unknown_citations(authority.citation) == [], authority.name


def test_every_statute_title_cites_a_known_act() -> None:
    for statute in STATUTES:
        assert unknown_citations(statute.title) == [], statute.title


# --- doctrine selection -----------------------------------------------------


def test_restraint_clause_selects_restraint_doctrine() -> None:
    text = ("14. Restraint of trade. For 24 months after termination the employee "
            "shall not canvass clients of the company within Gauteng.")
    keys = [d.key for d in applicable_doctrines(text)]
    assert "RESTRAINT" in keys


def test_payment_clause_selects_mora() -> None:
    text = "The tenant shall pay R15,000 per month within 7 days of invoice."
    keys = [d.key for d in applicable_doctrines(text)]
    assert "MORA" in keys


def test_voetstoots_clause_selects_positive_malperformance() -> None:
    text = "The property is sold voetstoots. The purchaser shall have no claim."
    keys = [d.key for d in applicable_doctrines(text)]
    assert "POSITIVE_MALPERFORMANCE" in keys


def test_no_trigger_gets_the_fallback_doctrines() -> None:
    keys = [d.key for d in applicable_doctrines("qqq zzz")]
    assert keys == ["FORMATION", "INTERPRETATION", "MORA"]


def test_doctrines_dont_false_trigger_on_ordinary_words() -> None:
    # "interest" alone should not pull in every interest-adjacent doctrine;
    # the triggers are whole-word and specific.
    text = "The parties have a mutual interest in the success of the project."
    keys = [d.key for d in applicable_doctrines(text)]
    assert "MISREPRESENTATION" not in keys


# --- authority selection ----------------------------------------------------


def test_selected_authorities_include_core_plus_linked() -> None:
    doctrines = [d for d in DOCTRINES if d.key in {"RESTRAINT", "MISTAKE"}]
    selected = select_authorities(doctrines)
    citations = {a.citation.split(";")[0].strip() for a in selected}
    assert "1984 (4) SA 874 (A)" in citations          # Magna Alloys, doctrine-linked
    assert "1993 (3) SA 742 (A)" in citations          # Basson v Chilwan
    assert "1992 (3) SA 234 (A)" in citations          # Sonap Petroleum
    for core in CORE_AUTHORITY_KEYS:
        assert core in citations                        # core always present
    assert len(citations) == len(selected)              # no duplicates


def test_selection_without_doctrines_is_just_the_core() -> None:
    selected = select_authorities([])
    citations = {a.citation.split(";")[0].strip() for a in selected}
    assert citations == set(CORE_AUTHORITY_KEYS)


# --- citation guard: SA-style citations -------------------------------------


def test_real_sa_style_citations_pass_the_guard() -> None:
    text = ("See BK Tooling (Edms) Bpk v Scope Precision Engineering (Edms) Bpk "
            "1979 (1) SA 391 (A); also Union Government v Vianini 1941 AD 43 and "
            "Cape Explosive Works 1921 CPD 244.")
    assert unknown_citations(text) == []


def test_fabricated_sa_style_citations_are_flagged() -> None:
    text = ("The court held in Fabricated Holdings v Nobody 2001 (7) SA 999 (A); "
            "see also Ghost v Machine 1955 AD 999 and Fake v Case 1930 CPD 111.")
    flagged = unknown_citations(text)
    assert "2001 (7) SA 999 (A)" in flagged
    assert "1955 AD 999" in flagged
    assert "1930 CPD 111" in flagged


def test_dual_citations_pass_both_forms() -> None:
    text = ("Capitec Bank Holdings Ltd v Coral Lagoon Investments 194 (Pty) Ltd "
            "[2021] ZASCA 99; 2022 (1) SA 100 (SCA).")
    assert unknown_citations(text) == []


def test_bclr_citation_is_flagged_when_not_in_pack() -> None:
    assert "1999 (2) BCLR 145 (SCA)" in unknown_citations("1999 (2) BCLR 145 (SCA)")


# --- reference block composition -------------------------------------------


def test_reference_block_accepts_selected_authorities() -> None:
    by_citation = authority_by_citation()
    chosen = [by_citation[k] for k in list(CORE_AUTHORITY_KEYS)[:3]]
    block = reference_block(list(STATUTES)[:1], authorities=chosen)
    assert len(chosen) == 3
    assert "Leading authorities" in block
    assert "Mavundla" not in block  # not among the three chosen


def test_doctrine_block_renders_statements() -> None:
    doctrines = [d for d in DOCTRINES if d.key == "MORA"]
    block = doctrine_block(doctrines)
    assert "COMMON LAW DOCTRINES" in block
    assert "Mora" in block


def test_worst_case_pack_stays_under_budget() -> None:
    """The full pack (everything triggered at once) must stay far under the
    50,000-character input cap even though the document shares that budget."""
    block = reference_block(list(STATUTES))  # all statutes + all authorities
    block += "\n" + doctrine_block(list(DOCTRINES))
    assert len(block) < 45_000, len(block)


def test_realistic_selection_stays_lean() -> None:
    """A typical residential lease must inject a fraction of the full pack."""
    from backend.za_law import applicable_statutes

    text = ("RESIDENTIAL LEASE AGREEMENT between Alpha (Pty) Ltd (the Landlord) "
            "and Ms B Botha (the Tenant) for Unit 12, 1 Main Road, Sandton. "
            "The tenant shall pay R12,000 per month by debit order within 7 "
            "days of invoice. The deposit is R24,000. The tenant may not cede "
            "or sublet. Voetstoots. Interest on late payment at 2% per month.")
    statutes = applicable_statutes(text)
    doctrines = applicable_doctrines(text)
    authorities = select_authorities(doctrines)
    block = reference_block(statutes, authorities=authorities)
    block += "\n" + doctrine_block(doctrines)
    assert len(block) < 15_000, len(block)
    assert "Rental Housing Act" in block
