"""South African legal reference pack.

A curated, hand-checked set of statutes and common-law doctrines, plus the
machinery to select the relevant ones for a document and to police the
citations that come back out of the model.

Why curated rather than retrieved: South African statutes and judgments carry
no copyright (Copyright Act 98 of 1978 s 12(8)(a)), but every convenient
source of them is closed by contract. SAFLII blocks automated AI access across
its whole collection; LawLibrary and AfricanLII are CC BY-NC, which excludes
commercial use. The only clean commercial feed is the paid Laws.Africa API.
Until that is worth buying, a fixed pack of the provisions that actually decide
contract disputes covers most of the ground with no licensing exposure.

Why the citation whitelist matters more than the pack: South African courts have
imposed costs de bonis propriis and made Legal Practice Council referrals over
AI-fabricated authorities — Mavundla v MEC: COGTA KZN [2025] ZAKZPHC 2 and
Northbound Processing v SADPMR [2025] ZAGPJHC 661. A tool that invents a section
number exposes its user to exactly that. So the model may cite only from this
file, and anything else it produces is flagged before the reader sees it.

Every entry carries the date it was verified and a confidence level. Where the
research could not confirm a commencement date or a threshold, the entry says
so rather than stating it as settled.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

VERIFIED_ON = "2026-08-14"


def _trigger_pattern(triggers: tuple[str, ...]) -> re.Pattern[str]:
    """Whole-word matcher for a statute's trigger list."""
    alternatives = "|".join(re.escape(t) for t in sorted(triggers, key=len, reverse=True))
    # The alternation MUST be grouped: without (?:...) the lookbehind binds only
    # to the first alternative and the lookahead only to the last, so "land"
    # happily matches inside "landlord".
    return re.compile(rf"(?<![a-z])(?:{alternatives})(?![a-z])", re.IGNORECASE)


@dataclass(frozen=True)
class Statute:
    key: str
    title: str
    triggers: tuple[str, ...]
    applies_when: str
    checks: tuple[str, ...]
    confidence: str = "high"
    caveat: str = ""

    def matches(self, haystack: str) -> bool:
        return _trigger_pattern(self.triggers).search(haystack) is not None


@dataclass(frozen=True)
class Authority:
    """A leading case, cited only in the form recorded here."""

    name: str
    citation: str
    proposition: str


# ---------------------------------------------------------------------------
# Statutes
# ---------------------------------------------------------------------------

STATUTES: tuple[Statute, ...] = (
    Statute(
        "CPA", "Consumer Protection Act 68 of 2008",
        ("consumer", "supplier", "goods", "services", "warranty", "voetstoots",
         "defect", "defects", "purchase", "sale", "returns", "guarantee",
         "lease", "rent", "tenant", "supply"),
        "Every transaction in the Republic, unless excluded by s 5(2). Juristic "
        "persons with asset value or annual turnover of R2 million or more are "
        "excluded; natural persons are always covered whatever the value. Credit "
        "agreements under the NCA are excluded, but the goods or services "
        "supplied under them remain covered.",
        (
            "s 48 — no term that is unfair, unreasonable or unjust, or that creates "
            "a significant imbalance. Covers express, implied and incorporated terms.",
            "s 49 — exemption, indemnity and assumption-of-risk terms must be drawn "
            "to the consumer's attention conspicuously and BEFORE the transaction. "
            "Where there is a risk of serious injury or death the consumer must "
            "additionally sign or initial. A buried indemnity does not survive s 49.",
            "s 51 — absolutely prohibited terms, void not voidable: waiver of CPA "
            "rights, waiver of liability for gross negligence, false acknowledgements "
            "of fact or receipt, and forfeiture of money to the supplier on cancellation.",
            "s 16 — 5 business day cooling-off applies to DIRECT MARKETING ONLY. "
            "There is no general CPA cooling-off right; do not over-read this.",
            "ss 55-56 — implied warranty that goods are safe, of good quality, free "
            "of defects and durable, with a 6-month return right at the CONSUMER's "
            "election. A voetstoots clause cannot exclude this where the CPA applies.",
        ),
        "medium",
        "The R2 million threshold was set by GN 294 in GG 34181 of 1 April 2011. "
        "Section 6 requires review at intervals of no more than five years and no "
        "later determination was found — confirm against a current gazette.",
    ),
    Statute(
        "NCA", "National Credit Act 34 of 2005",
        ("credit", "loan", "interest", "instalment", "repayment", "borrower",
         "lender", "facility", "advance", "arrears", "default"),
        "Every credit agreement at arm's length in the Republic. Juristic persons "
        "at or above R1 million asset value or turnover are excluded entirely; "
        "below that they are covered except for large agreements (principal debt "
        "over R250,000).",
        (
            "ss 78-88 — reckless credit. Check the s 81(2) affordability assessment. "
            "Note s 78(1): the reckless credit provisions do not apply to juristic "
            "persons at all.",
            "ss 92-93 — pre-agreement statement and quotation in the prescribed form.",
            "ss 100-101 — only the charges listed in s 101 are recoverable. Anything "
            "else in the fee schedule is not.",
            "ss 129-130 — pre-litigation notice. A defective s 129 notice is a "
            "standard defence to enforcement.",
            "Regulation 42 rate caps are repo PLUS a margin: mortgages +12%, credit "
            "facilities +14%, unsecured +21%, other +17%, short-term 5% per month on "
            "a first loan. At the current 7.00% repo that is 28% for unsecured credit. "
            "Many published tables reproduce the 2015 DRAFT formula (repo x 1.7 + x), "
            "which was never enacted and materially overstates the cap.",
            "s 103(5) statutory in duplum — while the consumer is in default, the "
            "aggregate of interest, initiation fee, service fee, credit insurance, "
            "default administration and collection costs may not exceed the unpaid "
            "principal as at the date of default. Run this alongside the common-law "
            "rule; they can give different answers.",
        ),
        "medium",
        "Repo rate 7.00% as at the MPC meeting of 23 July 2026 — recalculate the "
        "caps after each MPC announcement. The National Credit Amendment Act 7 of "
        "2019 (debt intervention) has no verified commencement; treat as not in force.",
    ),
    Statute(
        "ECTA", "Electronic Communications and Transactions Act 25 of 2002",
        ("electronic", "email", "e-mail", "digital signature", "electronic signature",
         "data message", "docusign", "scanned", "signed electronically"),
        "Any document executed or varied electronically.",
        (
            "s 13(1) — where a LAW requires a signature and does not specify the type, "
            "only an ADVANCED electronic signature will do. This is the commonest trap.",
            "s 13(3) — where the PARTIES require a signature, an ordinary electronic "
            "signature suffices if the method identified the person and indicated "
            "approval, and was reliable in the circumstances.",
            "Schedule 1 excludes the Wills Act, the Alienation of Land Act and the "
            "Bills of Exchange Act from ss 11-20.",
            "Schedule 2 — the Act gives NO validity to: alienation of immovable "
            "property; a lease of immovable property exceeding 20 years; a will or "
            "codicil; a bill of exchange.",
            "Suretyships are in neither Schedule, so a suretyship CAN be concluded "
            "electronically, subject to s 13 and the s 6 signature requirement.",
        ),
    ),
    Statute(
        "ALIENATION_LAND", "Alienation of Land Act 68 of 1981",
        ("land", "erf", "immovable", "immovable property", "deed of sale",
         "offer to purchase", "township", "sectional title", "alienation",
         "conveyancer", "conveyancing", "title deed"),
        "Any sale or other alienation of land.",
        (
            "s 2(1) — must be in writing and signed by the parties or by agents "
            "acting on WRITTEN authority. Non-compliance makes the deed VOID, not "
            "voidable. Check the agent's written mandate specifically.",
            "s 29A — 5-day right to revoke, but ONLY where the purchase price is "
            "R250,000 or less. Excluded: juristic persons and trusts, public "
            "auctions, and options valid for 5 days or more.",
            "Cannot be concluded electronically (ECTA Schedule 2).",
        ),
    ),
    Statute(
        "SURETYSHIP", "General Law Amendment Act 50 of 1956",
        ("surety", "suretyship", "guarantee", "guarantor", "co-principal debtor",
         "donation"),
        "Suretyships and executory donations.",
        (
            "s 6 — a suretyship is invalid unless its terms are in a written "
            "document signed by or on behalf of the SURETY. The creditor need not "
            "sign. The identity of creditor, principal debtor and the nature and "
            "amount of the debt must be ascertainable FROM THE DOCUMENT ITSELF.",
            "s 5 — an executory contract of donation is invalid unless in writing "
            "and signed by the donor, or by someone acting on the donor's written "
            "authority granted before two witnesses. Executed donations need no formality.",
        ),
    ),
    Statute(
        "COMPANIES", "Companies Act 71 of 2008",
        ("company", "(pty)", "director", "board", "resolution", "shareholder",
         "memorandum of incorporation", "business rescue", "liquidation"),
        "Any transaction with a company as party.",
        (
            "s 19(4) — constructive notice of the MOI is ABOLISHED, except for RF "
            "(ring-fenced) companies and personal liability companies (s 19(5)).",
            "s 20(7) — the Turquand rule, codified. A person dealing in good faith "
            "may presume compliance with internal formalities. It cures PROCEDURAL "
            "irregularity only; it never cures a total absence of authority.",
            "ss 44-45 — financial assistance for share acquisition, and to directors "
            "or related parties. Non-compliance makes the resolution VOID. Note that "
            "intra-group assistance is now exempt from s 45.",
            "ss 112/115 — disposal of the greater part of the assets or undertaking "
            "requires a special resolution.",
            "s 133 — the business rescue moratorium. No legal proceeding or "
            "enforcement may be commenced or continued without the practitioner's "
            "written consent or leave of the court. Check the CIPC status before "
            "advising on enforcement.",
            "s 136(2) — a business rescue practitioner may SUSPEND any obligation "
            "under a pre-commencement contract, and apply to cancel it. The "
            "counterparty is left with a concurrent damages claim only.",
        ),
        "medium",
        "The Companies Amendment Act 16 of 2024 was partially commenced on "
        "27 December 2024. Provisions on remuneration disclosure and takeover "
        "thresholds may still be pending — confirm before relying on them.",
    ),
    Statute(
        "TRUST_PROPERTY", "Trust Property Control Act 57 of 1988",
        ("trust", "trustee", "beneficiary", "founder", "letters of authority"),
        "Any transaction with a trust as party.",
        (
            "s 6(1) — a trustee may act only after the Master has authorised them. "
            "An act by a purported trustee before letters of authority are issued "
            "is a NULLITY, not a defect capable of ratification. Always call for "
            "the letters of authority.",
            "Check that ALL trustees required by the trust deed have signed — a "
            "trust generally acts jointly unless the deed says otherwise.",
        ),
    ),
    Statute(
        "POPIA", "Protection of Personal Information Act 4 of 2013",
        ("personal information", "data", "privacy", "popia", "processing",
         "data subject", "confidential information"),
        "Any contract under which one party processes personal information.",
        (
            "ss 20-21 — where an operator processes on a responsible party's behalf "
            "there MUST be a written contract requiring s 19 security measures and "
            "immediate notification of unauthorised access. Its absence is itself a "
            "contravention.",
            "s 72 — personal information may not be transferred to a third party in "
            "a foreign country unless one of five grounds applies. For offshore "
            "processing the workhorse is s 72(1)(a): a binding agreement giving "
            "adequate protection AND restricting onward transfer. South Africa has "
            "no adequacy list — do not accept an assertion that a country is adequate.",
            "s 69 — direct marketing by electronic communication requires opt-in "
            "consent, subject to a narrow existing-customer exception.",
        ),
    ),
    Statute(
        "FICA", "Financial Intelligence Centre Act 38 of 2001",
        ("kyc", "know your customer", "due diligence", "beneficial owner",
         "anti-money laundering", "aml", "source of funds", "proof of funds"),
        "Accountable institutions under Schedule 1 — since the 2022 amendments "
        "this includes credit providers, trust administrators, high-value goods "
        "dealers (single transactions of R100,000 or more) and crypto asset "
        "service providers.",
        (
            "ss 21-21H — identify and verify the client and anyone acting for them, "
            "establish and verify BENEFICIAL OWNERSHIP, screen against the Targeted "
            "Financial Sanctions list, and apply enhanced due diligence to prominent "
            "influential persons.",
            "s 42 — customer due diligence must follow the institution's documented "
            "Risk Management and Compliance Programme, not a generic standard.",
            "s 29 — suspicious and unusual transaction reports bind ANY business, "
            "not only accountable institutions, and must be filed without delay. "
            "ss 29(3)-(4) prohibit tipping off.",
        ),
        "high",
        "South Africa exited the FATF grey list on 24 October 2025. That reduces "
        "cross-border friction but relaxes no FICA obligation.",
    ),
    Statute(
        "PRESCRIPTION", "Prescription Act 68 of 1969",
        ("prescription", "prescribed", "time bar", "limitation", "stale", "arrear"),
        "Any claim where time may have run.",
        (
            "s 11(d) — ordinary contractual debts prescribe in THREE years. "
            "s 11(c) — six years for a bill of exchange or a NOTARIAL contract. "
            "s 11(a) — thirty years for a mortgage-secured or judgment debt.",
            "s 12(3) — the debt is not due until the creditor knows the debtor's "
            "identity and the facts, with deemed knowledge on reasonable care.",
            "s 14 — an express or tacit acknowledgement of liability interrupts "
            "prescription and it starts afresh.",
            "A clause purporting to EXTEND prescription is generally unenforceable; "
            "one SHORTENING time to sue is tested for reasonableness under Barkhuizen.",
        ),
    ),
    Statute(
        "PENALTIES", "Conventional Penalties Act 15 of 1962",
        ("penalty", "liquidated damages", "forfeit", "rouwkoop", "non-refundable",
         "acceleration"),
        "Any clause imposing a sum or forfeiture on breach, whatever it is called.",
        (
            "s 1 — penalty stipulations ARE enforceable, reversing the old common law.",
            "s 2 — a creditor may not recover both the penalty and damages for the "
            "same act unless the contract expressly provides for an election.",
            "s 3 — the court MAY REDUCE a penalty that is out of proportion to the "
            "prejudice suffered. This power CANNOT be excluded by agreement.",
            "s 4 — applies equally to forfeiture of instalments already paid.",
            "For consumer transactions CPA s 51(1)(g) may render forfeiture void "
            "outright, which is stricter than s 3 reduction.",
        ),
    ),
    Statute(
        "JURISDICTION", "Magistrates' Courts Act 32 of 1944 and the Arbitration Acts",
        ("jurisdiction", "forum", "arbitration", "dispute resolution", "court",
         "mediation", "governing law"),
        "Any dispute resolution or jurisdiction clause.",
        (
            "District magistrates' court R200,000; regional court R400,000. Parties "
            "may consent to jurisdiction above the limit under s 45.",
            "Small Claims Court R30,000 with effect from 1 August 2026.",
            "Arbitration Act 42 of 1965 s 33 — an award may be set aside only for "
            "misconduct, gross irregularity or improper procurement. Advise on how "
            "narrow that is before agreeing to arbitrate.",
            "International Arbitration Act 15 of 2017 applies the UNCITRAL Model Law "
            "where the arbitration is 'international' as defined — which determines "
            "the set-aside grounds.",
        ),
        "medium",
        "The R200,000 / R400,000 limits date from a 2014 determination and no later "
        "increase was found. Given their age, re-check the current gazette.",
    ),
    Statute(
        "PROPERTY_PRACTITIONERS", "Property Practitioners Act 22 of 2019",
        ("estate agent", "agent", "commission", "mandate", "property practitioner",
         "listing", "lease of property"),
        "Any transaction involving a property practitioner. In force 1 February 2022, "
        "replacing the Estate Agency Affairs Act 112 of 1976.",
        (
            "s 56 — a property practitioner without a valid Fidelity Fund Certificate "
            "is NOT ENTITLED to any commission or remuneration, and no one may pay it. "
            "Check the certificate before the commission clause.",
            "s 67 — the prescribed mandatory disclosure form must be completed and "
            "attached. If it is missing, the agreement is interpreted AS IF NO DEFECTS "
            "WERE DISCLOSED.",
        ),
    ),
    Statute(
        "LRA_BCEA", "Labour Relations Act 66 of 1995 and Basic Conditions of "
                    "Employment Act 75 of 1997",
        ("employee", "employment", "employer", "salary", "wage", "dismissal",
         "restraint of trade", "contractor", "going concern"),
        "Employment contracts and any sale of a business as a going concern.",
        (
            "LRA s 197 — on a transfer of a business as a going concern employees "
            "transfer AUTOMATICALLY and the new employer is substituted by operation "
            "of law. This overrides whatever the asset purchase agreement says.",
            "BCEA ss 4-5 — minimum terms cannot be contracted below.",
            "BCEA earnings threshold R269,600.90 per year from 1 May 2026 — above it, "
            "the working-time provisions do not apply.",
            "National Minimum Wage R30.23 per hour from 1 March 2026. Applies to "
            "'independent contractor' arrangements that are employment in substance.",
        ),
    ),
    Statute(
        "RENTAL", "Rental Housing Act 50 of 1999",
        ("lease", "tenant", "landlord", "rent", "deposit", "premises", "letting"),
        "Residential leases.",
        (
            "s 5(2) — a lease need not be in writing, but MUST be reduced to writing "
            "at the tenant's request.",
            "Check deposit handling, the interest payable on it, and the joint "
            "incoming and outgoing inspection requirements.",
            "Provincial Rental Housing Tribunal rulings have the effect of a "
            "magistrates' court order.",
        ),
        "medium",
        "The Rental Housing Amendment Act 35 of 2014 would make written leases "
        "compulsory, but no commencement was verified. Do not advise that written "
        "leases are mandatory.",
    ),
    Statute(
        "EXCHANGE_CONTROL", "Currency and Exchanges Act 9 of 1933 and the Exchange "
                            "Control Regulations, 1961",
        ("foreign", "offshore", "cross-border", "usd", "dollar", "euro", "pound",
         "non-resident", "export", "import", "remittance", "wire transfer"),
        "Cross-border payments, non-resident loans, offshore assignments and "
        "foreign-currency obligations.",
        (
            "Cross-border flows run through an Authorised Dealer and may need SARB "
            "Financial Surveillance Department approval. A contract that assumes "
            "funds can simply be remitted may be unperformable.",
            "Regulation 10(1)(c) restricts borrowing by non-residents.",
            "Check the Currency and Exchanges Manual for Authorised Dealers — it is "
            "updated frequently.",
        ),
    ),
    Statute(
        "MINERALS", "Diamonds Act 56 of 1986 and Precious Metals Act 37 of 2005",
        ("diamond", "diamonds", "carat", "gold", "platinum", "precious metal",
         "kimberley", "rough", "bullion", "unwrought"),
        "Any dealing in unpolished diamonds or unwrought precious metals.",
        (
            "Dealing in, possessing, importing or exporting unpolished diamonds "
            "requires a licence or permit from the South African Diamond and Precious "
            "Metals Regulator, plus Kimberley Process certification.",
            "Precious Metals Act — a licence is required to acquire, possess, smelt, "
            "refine or dispose of unwrought precious metal. A supply contract "
            "concluded without the requisite licence is unlawful.",
            "The buyer's own licensing position matters as much as the seller's. "
            "Check for a licence warranty and the licence number.",
        ),
    ),
)

# ---------------------------------------------------------------------------
# Common law
# ---------------------------------------------------------------------------

AUTHORITIES: tuple[Authority, ...] = (
    Authority("SA Sentrale Ko-operatiewe Graanmaatskappy Bpk v Shifren en Andere",
              "1964 (4) SA 760 (A)",
              "A non-variation clause that entrenches BOTH itself and the other "
              "terms is valid, and oral variations are void. If it is not "
              "self-entrenching it can itself be varied orally and the shield fails."),
    Authority("Barkhuizen v Napier", "[2007] ZACC 5; 2007 (5) SA 323 (CC)",
              "Two-stage public policy test: is the clause objectively unreasonable "
              "on its face, and if not, should it still not be enforced given the "
              "circumstances that prevented compliance."),
    Authority("Beadica 231 CC v Trustees for the time being of the Oregon Trust",
              "[2020] ZACC 13; 2020 (5) SA 247 (CC)",
              "The current governing authority, and it narrowed things. Good faith, "
              "ubuntu and fairness are underlying values informing public policy, "
              "NOT free-standing grounds to refuse enforcement. A court may not "
              "decline to enforce a term merely because it thinks it unfair."),
    Authority("Standard Bank of South Africa Ltd v Oneanate Investments (Pty) Ltd",
              "1998 (1) SA 811 (SCA)",
              "Common-law in duplum: arrear interest stops running once it equals "
              "the outstanding capital."),
    Authority("Paulsen and Another v Slip Knot Investments 777 (Pty) Ltd",
              "[2015] ZACC 5; 2015 (3) SA 479 (CC)",
              "Overturned Oneanate's litigation exception — in duplum now continues "
              "to run during litigation. Any source saying otherwise is out of date."),
    Authority("Spring Forest Trading 599 CC v Wilberry (Pty) Ltd t/a Ecowash",
              "2015 (2) SA 118 (SCA)",
              "Typed names in emails satisfied 'signature' under ECTA s 13(3), so a "
              "contract requiring writing and signature was validly cancelled by email."),
    Authority("Natal Joint Municipal Pension Fund v Endumeni Municipality",
              "2012 (4) SA 593 (SCA)",
              "Context and purpose are admissible aids to interpretation from the "
              "outset; no ambiguity threshold is required. An entire-agreement "
              "clause bars additional TERMS, not contextual evidence of MEANING."),
    Authority("Union Government v Vianini Ferro-Concrete Pipes (Pty) Ltd",
              "1941 AD 43",
              "The parol evidence (integration) rule: where a contract is the "
              "exclusive memorial, extrinsic evidence cannot contradict, add to "
              "or vary its terms."),
    Authority("George v Fairmead (Pty) Ltd", "1958 (2) SA 465 (A)",
              "Caveat subscriptor — a signatory is bound by what they sign. The "
              "escapes are narrow: iustus error, or where the other party caused "
              "or knew of the mistake and failed to point out an unexpected term."),
    Authority("Damons N.O. and Another v Bezuidenhout", "[2025] ZAGPPHC 820",
              "Drawing up documents generally is NOT reserved to legal "
              "practitioners; documents are 'intended for use' in proceedings only "
              "once introduced into them. Leave to appeal refused."),
    Authority("Mavundla v MEC: Department of Co-Operative Government and "
              "Traditional Affairs KZN", "[2025] ZAKZPHC 2",
              "AI-fabricated citations: costs de bonis propriis and referral to the "
              "Legal Practice Council. Every authority must be verified."),
    Authority("Northbound Processing (Pty) Ltd v SA Diamond and Precious Metals "
              "Regulator", "[2025] ZAGPJHC 661",
              "Those using AI have a professional duty to check the accuracy of "
              "what it produces. Conduct referred to the LPC."),
)


# ---------------------------------------------------------------------------
# Selection and rendering
# ---------------------------------------------------------------------------

def applicable_statutes(text: str, facts: dict | None = None) -> list[Statute]:
    """Pick the statutes a document actually engages, by trigger word."""
    haystack = (text or "").lower()
    if facts:
        haystack += " " + " ".join(
            str(v) for v in (facts.get("document_type"), facts.get("payment_method"))
            if v
        ).lower()
    selected = [s for s in STATUTES if s.matches(haystack)]
    # A contract with no trigger at all still deserves the general framework.
    if not selected:
        selected = [s for s in STATUTES if s.key in {"PRESCRIPTION", "JURISDICTION"}]
    return selected


def reference_block(statutes: list[Statute], include_authorities: bool = True) -> str:
    """Render the selected law for injection into the analysis prompt."""
    parts = [
        "SOUTH AFRICAN LAW REFERENCE PACK",
        f"Curated and verified on {VERIFIED_ON}. You may cite ONLY what appears "
        "below. Do not cite any other Act, section or case, and do not paraphrase "
        "a provision into a section number that is not listed here.",
        "",
    ]
    for statute in statutes:
        parts.append(f"### {statute.title}")
        parts.append(f"Applies: {statute.applies_when}")
        for check in statute.checks:
            parts.append(f"  - {check}")
        if statute.caveat:
            parts.append(f"  ! CAVEAT ({statute.confidence} confidence): {statute.caveat}")
        parts.append("")

    if include_authorities:
        parts.append("### Leading authorities")
        for authority in AUTHORITIES:
            parts.append(f"  - {authority.name} {authority.citation} — "
                         f"{authority.proposition}")
        parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Citation policing
# ---------------------------------------------------------------------------

_ACT_RE = re.compile(r"\b([A-Z][A-Za-z'()\-]*(?:\s+(?:of|and|in|the|for|to|"
                     r"[A-Z][A-Za-z'()\-]*)){0,9}?\s+Act)\s+(\d+)\s+of\s+(\d{4})")
_CASE_RE = re.compile(r"\[(\d{4})\]\s+(ZACC|ZASCA|ZAGPJHC|ZAGPPHC|ZAKZPHC|ZAWCHC|"
                      r"ZALCJHB|ZAECGHC|ZAFSHC|ZANWHC|ZALMPPHC|ZAMPMHC|ZANCHC)\s+(\d+)")


def _known_acts() -> set[tuple[str, str]]:
    known = set()
    for statute in STATUTES:
        for number, year in re.findall(r"Act (\d+) of (\d{4})", statute.title):
            known.add((number, year))
    return known


def _known_cases() -> set[str]:
    return {a.citation.split(";")[0].strip() for a in AUTHORITIES}


def unknown_citations(markdown: str) -> list[str]:
    """Return citations in the output that are not in this reference pack.

    Courts have imposed costs and made LPC referrals over invented authorities.
    Anything this returns should be surfaced to the reader as unverified rather
    than quietly published.
    """
    known_acts = _known_acts()
    known_cases = _known_cases()
    unknown: list[str] = []

    for name, number, year in _ACT_RE.findall(markdown or ""):
        if (number, year) not in known_acts:
            candidate = f"{name.strip()} {number} of {year}"
            if candidate not in unknown:
                unknown.append(candidate)

    for year, court, number in _CASE_RE.findall(markdown or ""):
        citation = f"[{year}] {court} {number}"
        if not any(citation in known for known in known_cases) and citation not in unknown:
            unknown.append(citation)

    return unknown
