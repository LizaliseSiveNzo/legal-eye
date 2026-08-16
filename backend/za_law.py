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

Pack history:
- 2.0 (2026-08-16): 17 statutes added (prescribed interest, insolvency,
  matrimonial property, competition, PRECCA, interpretation of time, bills of
  exchange, payment systems, VAT, sectional titles/CSOS, PIE/ESTA, COIDA/UIF,
  insurance, public procurement, wills/estates, customary marriages, debt
  collection); NCA ss 89-90 added; 28 leading authorities added; the citation
  guard now recognises SA-style, AD and provincial-division citations;
  authorities are injected selectively rather than all at once.
- 1.0 (2026-08-14): initial 17 statutes and 12 authorities.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

VERIFIED_ON = "2026-08-16"
PACK_VERSION = "2.0"


def trigger_pattern(triggers: tuple[str, ...]) -> re.Pattern[str]:
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
        return trigger_pattern(self.triggers).search(haystack) is not None


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
            "s 90(2) — unlawful provisions are VOID. The list is long but closed: "
            "terms that defeat the Act's purposes, misrepresent the price or the "
            "parties' rights, waive common-law protections, or authorise entry onto "
            "premises or unlawful collection practices. Test every suspicious term "
            "against the list.",
            "s 89 — unlawful credit agreements: among others, agreements by "
            "unregistered providers, negative-option marketing agreements, and "
            "ancillary arrangements that defeat the Act. Void from inception.",
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
    Statute(
        "PRESCRIBED_INTEREST", "Prescribed Rate of Interest Act 55 of 1975",
        ("interest rate", "prime rate", "mora interest", "prescribed rate",
         "late payment", "per annum", "accrue"),
        "Any debt where interest runs and no rate is agreed, or where the parties "
        "adopt the prescribed rate.",
        (
            "s 1(1) — a debt bears interest at the prescribed rate from when it is "
            "due, where no other rate is agreed or set by law.",
            "The prescribed rate is the repo rate plus 3.5 percentage points "
            "(GN R1077 in GG 37970 of 8 September 2014). At the 7.00% repo rate of "
            "July 2026 that is 10.5% per annum.",
            "Parties may agree a different rate, but it is tested for reasonableness "
            "under the common law and Barkhuizen, and for credit agreements the "
            "NCA rate caps apply instead.",
        ),
        "medium",
        "The prescribed rate is amended by gazette; confirm the current repo-linked "
        "rate before quoting it.",
    ),
    Statute(
        "INSOLVENCY", "Insolvency Act 24 of 1936",
        ("insolvent", "insolvency", "sequestration", "sequestrated",
         "winding up", "wound up", "liquidate", "liquidation",
         "unable to pay its debts"),
        "Any transaction with a party that is, or may become, insolvent. Companies "
        "follow the Companies Act liquidation and business rescue regime, but these "
        "provisions are the model for voidable dispositions and still bind natural "
        "persons and trusts.",
        (
            "s 26(1) — a disposition not made for value: made within two years of "
            "sequestration it is set aside without proving insolvency; older than "
            "two years it is set aside only if the debtor was insolvent at the time.",
            "s 29(1) — a disposition within six months of sequestration that "
            "preferred one creditor above others is voidable if the debtor's "
            "liabilities exceeded assets immediately afterwards, without proving "
            "any intent to prefer.",
            "s 30 — a disposition made with the intent to prefer one creditor while "
            "insolvent is voidable, whatever its date.",
            "s 31 — collusive dealings to prejudice other creditors are void, and "
            "the court may set them aside.",
            "s 34 — a trader alienating their business or its goodwill must publish "
            "a notice and give creditors 30 days to object; without compliance the "
            "alienation is void as against creditors.",
        ),
        "medium",
        "The look-back windows and what counts as 'value' are litigated ground. "
        "Treat these as red flags to verify with an insolvency practitioner, not "
        "final rulings.",
    ),
    Statute(
        "MATRIMONIAL", "Matrimonial Property Act 88 of 1984",
        ("married", "marriage", "spouse", "in community of property",
         "antenuptial", "accrual", "married in community"),
        "Any party contracting while married in community of property.",
        (
            "s 15(2) — listed transactions require the other spouse's written consent "
            "attested by two witnesses: among them, alienating or burdening immovable "
            "property, entering a suretyship, and credit agreements regulated by the NCA.",
            "s 15(3) — other listed transactions need the spouse's consent; the form "
            "is looser than under s 15(2).",
            "A transaction concluded without the required consent is invalid as "
            "against the innocent spouse, and the requirement is enforced strictly. "
            "Call for the marriage certificate and the consent itself.",
        ),
        "low",
        "The exact effect of non-compliance (void ab initio versus voidable) has "
        "divided the courts; flag the issue and confirm against current authority.",
    ),
    Statute(
        "COMPETITION", "Competition Act 89 of 1998",
        ("competition", "compete", "non-compete", "restraint of trade",
         "price fixing", "collusion", "cartel", "market share", "merger",
         "exclusive dealing", "resale price", "dominance", "dominant",
         "exclusivity"),
        "Agreements that restrain, restrict or distort competition: sale-of-business "
        "or employment non-competes, exclusivity, resale price clauses, and mergers.",
        (
            "s 4(1)(b) — horizontal agreements between competitors are per se "
            "prohibited: price fixing, market division, and collusive tendering.",
            "s 5(1) — vertical agreements are prohibited if they substantially "
            "prevent or lessen competition; minimum resale price maintenance is the "
            "commonest trap.",
            "s 8 — abuse of dominance: excessive pricing, exclusionary acts, "
            "refusing access to an essential facility. Relevant where one party is "
            "a dominant firm.",
            "Intermediate and large mergers require Competition Commission approval "
            "before implementation. The financial thresholds are set by the Minister "
            "and have been amended repeatedly — do not rely on published tables.",
        ),
        "medium",
        "Merger thresholds and the buyer-power provisions have changed since "
        "commencement; confirm the current determinations before relying on them.",
    ),
    Statute(
        "PRECCA", "Prevention and Combating of Corrupt Activities Act 12 of 2004",
        ("bribe", "bribery", "corrupt", "corruption", "kickback", "gratification",
         "facilitation payment", "conflict of interest"),
        "Clauses touching gifts, hospitality, commissions to officials, "
        "facilitation payments, or consultancy fees to politically connected persons.",
        (
            "s 3 — the general offence of corruption: giving or accepting any "
            "gratification in exchange for acting dishonestly or influencing "
            "another's conduct. It binds private parties as well as officials.",
            "s 34 — a person in a position of authority who knows or ought to know "
            "of corruption must report it to the police. No contract term can "
            "override that duty.",
            "A contract procured by bribery is tainted and may be unenforceable on "
            "public-policy grounds, quite apart from criminal exposure.",
        ),
        "high",
    ),
    Statute(
        "INTERPRETATION_ACT", "Interpretation Act 33 of 1957",
        ("business day", "business days", "calendar days", "calendar day",
         "notice period", "reckoned", "computed from", "within 30 days"),
        "Any clause computing time: notice periods, cooling-off days, 'business "
        "days', deadlines measured in days or months.",
        (
            "s 4 — when a period is reckoned in days, the first day is excluded and "
            "the last day included. If the last day falls on a Sunday or public "
            "holiday, the period ends on the next day that is not one.",
            "s 2 — 'month' means a calendar month, not thirty days.",
            "Public Holidays Act 36 of 1994 — 'public holiday' includes days declared "
            "by proclamation; check the current list before computing a deadline.",
        ),
        "high",
    ),
    Statute(
        "BILLS_EXCHANGE", "Bills of Exchange Act 34 of 1964",
        ("cheque", "bill of exchange", "promissory note", "bank draft",
         "crossed cheque"),
        "Payment by cheque, bill of exchange or promissory note.",
        (
            "A promissory note is an unconditional written promise, signed by the "
            "maker, to pay a sum certain. A cheque is a bill drawn on a banker and "
            "payable on demand.",
            "The instrument must be in writing and signed; the sum must be certain.",
            "Prescription on a bill or note is six years (Prescription Act s 11(c)).",
        ),
        "high",
    ),
    Statute(
        "NPS", "National Payment System Act 78 of 1998",
        ("debit order", "debit orders", "eft", "electronic funds transfer",
         "payment system", "naedo", "debicheck", "authenticated mandate",
         "early debit order"),
        "Debit orders, EFT mandates and other payment instructions through the "
        "South African clearing system.",
        (
            "Debit orders run through a bank participating in the payment system "
            "recognised by the SARB. The mandate must be authorised by the payer.",
            "Unauthorised debit orders can be disputed through the payer's bank and "
            "reversed within defined windows. A clause waiving the right to dispute "
            "an unauthorised debit is unlikely to stand.",
            "DebiCheck authenticated mandates are the standard for new debit orders; "
            "the agreement should say whether the mandate is authenticated.",
        ),
        "medium",
        "Payment-system rules change through PASA and SARB directives; treat the "
        "mechanics as current practice to confirm, not fixed law.",
    ),
    Statute(
        "VAT", "Value-Added Tax Act 89 of 1991",
        ("vat", "value added tax", "tax invoice", "zero-rated", "zero rating",
         "standard rated", "output tax", "input tax"),
        "Any supply of goods or services, or a price clause expressed as inclusive "
        "or exclusive of VAT.",
        (
            "s 7(1) — VAT is levied on the supply of goods or services by a vendor "
            "in the course of an enterprise. The price clause must say whether the "
            "price is inclusive or exclusive of VAT.",
            "s 20 — a vendor must issue a tax invoice within 21 days of the supply: "
            "a full tax invoice for R5,000 or more, an abridged one between R50 and "
            "R5,000. A purchaser cannot claim an input credit without one.",
            "s 11 — zero-rated supplies (for example exported goods) attract VAT at "
            "0%; the contract should state the basis relied on.",
        ),
        "high",
    ),
    Statute(
        "SECTIONAL_TITLES",
        "Sectional Titles Schemes Management Act 8 of 2011 and the Community "
        "Schemes Ombud Service Act 9 of 2011",
        ("sectional title", "body corporate", "levy", "levies",
         "exclusive use area", "scheme rules", "conduct rules", "unit owner",
         "sectional plan"),
        "Sectional title schemes: levies, body corporate duties, exclusive use "
        "areas, conduct rules.",
        (
            "The body corporate owes statutory duties to maintain common property "
            "and insure the buildings; a contract cannot contract out of them.",
            "Members are liable for levies. Special levies require proper "
            "decision-making; a scheme rule that conflicts with the Act or the "
            "management rules is invalid.",
            "Scheme disputes, including levy disputes, are routed through the "
            "Community Schemes Ombud Service; its adjudication orders are enforceable.",
        ),
        "medium",
        "Section numbers in this Act are high-traffic and frequently amended; "
        "verify the specific provision against the current text before quoting it.",
    ),
    Statute(
        "PIE_ESTA",
        "Prevention of Illegal Eviction from and Unlawful Occupation of Land Act "
        "19 of 1998 and the Extension of Security of Tenure Act 62 of 1997",
        ("eviction", "evict", "unlawful occupation", "unlawful occupier",
         "occupier", "farm dweller", "labour tenant", "esta"),
        "Leases, sale-of-land and security arrangements that contemplate removing "
        "an occupier.",
        (
            "PIE s 4 — an eviction requires a court order, obtained only after the "
            "occupier has been given notice and the court has weighed all the "
            "circumstances ('just and equitable'). A self-help or lockout clause is "
            "unlawful, and unlawful eviction is an offence.",
            "ESTA s 6 — occupiers who have lived on land with the owner's consent "
            "have occupation rights; termination must be lawful and just and equitable.",
            "Any clause permitting the owner to evict without a court order is "
            "unenforceable and signals deeper trouble.",
        ),
        "high",
    ),
    Statute(
        "COIDA_UIF",
        "Compensation for Occupational Injuries and Diseases Act 130 of 1993 and "
        "the Unemployment Insurance Act 63 of 2001",
        ("coida", "occupational injury", "workplace injury", "workmen's "
         "compensation", "uif", "unemployment insurance", "compensation for "
         "occupational injuries"),
        "Employment and contractor agreements, especially indemnities for "
        "workplace injury.",
        (
            "COIDA s 35(1) — an employee may not claim damages from the employer "
            "for an occupational injury; compensation is claimed under COIDA. An "
            "employee's indemnity to the employer for such injury is ineffective.",
            "COIDA does not protect third parties: a subcontractor injured on site "
            "may claim from the principal contractor. Mutual indemnities between "
            "contractors and principals carry the real risk here.",
            "UIF — employers must register and contribute; a worker styled an "
            "'independent contractor' who is an employee in substance attracts "
            "UIF and COIDA obligations.",
        ),
        "medium",
        "The employee-versus-independent-contractor boundary is fact-heavy and "
        "frequently tested; flag it rather than decide it.",
    ),
    Statute(
        "INSURANCE", "Insurance Act 18 of 2017",
        ("insurer", "insured", "insurance policy", "policyholder", "premium",
         "underwriter", "reinsurance", "claims made", "indemnity insurance"),
        "Insurance policies, indemnity arrangements resembling insurance, premium "
        "finance and warranty arrangements.",
        (
            "The Act consolidates insurance regulation; the Policyholder Protection "
            "Rules issued under it (replacing the Long-term and Short-term "
            "Insurance Acts' rules) govern how insurers treat policyholders.",
            "PPR duties are strict: material terms must be disclosed in plain "
            "language, customers treated fairly, and claims handled without "
            "reliance on undisclosed technicalities. A policy term contradicting "
            "the PPRs is vulnerable.",
            "A contract under which one party assumes another's risk may be "
            "'insurance business' requiring licensing; 'guarantee' schemes that are "
            "insurance in substance are risky.",
        ),
        "medium",
        "PPR rule numbers change; cite the duty, not the rule number, unless "
        "verified.",
    ),
    Statute(
        "PUBLIC_PROCUREMENT",
        "Public Finance Management Act 1 of 1999 and the Preferential "
        "Procurement Policy Framework Act 5 of 2000",
        ("procurement", "organ of state", "public entity", "municipality",
         "municipal", "invitation to tender", "tender award", "bidder",
         "tender"),
        "Contracts with organs of state: national or provincial departments, "
        "municipalities, public entities and state-owned companies.",
        (
            "Constitution s 217 — procurement must be fair, equitable, transparent, "
            "competitive and cost-effective.",
            "PFMA — an accounting officer who commits expenditure without authority "
            "acts irregularly; a supplier's contract with an organ of state must fit "
            "an approved procurement process.",
            "PPPFA — preference points must follow the prescribed framework; an "
            "award outside it is open to review and set-aside.",
            "A private supplier dealing with the state should confirm the "
            "procurement authority and process in writing before performance starts.",
        ),
        "medium",
        "The procurement regime has been in flux (PPPR 2022 litigation and "
        "replacement legislation); treat the framework as a flag to verify, not "
        "settled text.",
    ),
    Statute(
        "WILLS_ESTATES", "Wills Act 7 of 1953 and the Administration of Estates "
                         "Act 66 of 1965",
        ("last will", "will and testament", "testator", "testatrix", "executor",
         "executrix", "bequest", "legatee", "heir", "inheritance",
         "deceased estate"),
        "Documents dealing with inheritance, executors, or the estate of a "
        "deceased person.",
        (
            "Wills Act s 2(1)(a) — a will must be signed at its end by the testator "
            "(or by someone in their presence and at their direction) in the "
            "presence of two or more competent witnesses who sign in the presence "
            "of the testator and of each other.",
            "A will cannot be made or varied electronically (ECTA Schedule 1); an "
            "e-signed 'will' is invalid.",
            "Administration of Estates Act — the estate is administered under the "
            "Master's supervision; only the appointed executor may deal with estate "
            "assets. Letters of executorship are the equivalent of letters of "
            "authority for trusts.",
        ),
        "high",
    ),
    Statute(
        "CUSTOMARY", "Recognition of Customary Marriages Act 120 of 1998",
        ("customary marriage", "customary law", "lobola", "lobolo",
         "customary union", "polygamous marriage"),
        "Any party to a customary marriage, or documents referring to lobola or a "
        "customary union.",
        (
            "s 3(1) — a customary marriage requires: both spouses over 18, consent "
            "of both, and the marriage negotiated and entered into or celebrated "
            "in accordance with customary law.",
            "s 4(1) — the marriage must be registered within three months.",
            "s 7(2) — a customary marriage entered into after commencement is in "
            "community of property unless an antenuptial contract excludes it. "
            "Subsequent (polygamous) marriages require a court-approved contract "
            "regulating the matrimonial property system.",
        ),
        "medium",
        "Property consequences of polygamous marriages follow court practice that "
        "has shifted (Ramuhovhi v President of the RSA [2017] ZACC 41); flag and "
        "verify.",
    ),
    Statute(
        "DEBT_COLLECTORS", "Debt Collectors Act 114 of 1998",
        ("debt collector", "collection costs", "collection commission",
         "handed over for collection", "collections agency"),
        "Clauses about collection costs, debt collectors, or attorneys' collection "
        "commission.",
        (
            "A person who collects debts for reward must be registered as a debt "
            "collector; an unregistered collector may not recover fees.",
            "Collection costs must be lawful and reasonable; the tariff under the "
            "Magistrates' Courts Rules governs attorney collection charges. A "
            "clause imposing arbitrary collection costs is vulnerable.",
        ),
        "medium",
        "Tariffs change; check the current scale before quoting it.",
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
    Authority("Cape Explosive Works Ltd v South African Oil and Fat Industries Ltd",
              "1921 CPD 244",
              "The expedition (posting) theory for postal contracts: acceptance is "
              "complete when posted, so the contract arises then, not on receipt."),
    Authority("Bloom v American Swiss Watch Co", "1915 AD 100",
              "An offer of reward may be revoked by a notice published as widely as "
              "the offer itself, effective against persons who have not yet accepted."),
    Authority("Pieters & Co v Salomon", "1911 AD 121",
              "Quasi-mutual assent: where one party's conduct reasonably induces the "
              "other to believe in consent, the first is held to that appearance."),
    Authority("Sonap Petroleum (SA) (Pty) Ltd v Pappadogianis", "1992 (3) SA 234 (A)",
              "For mistake to avoid a contract it must be both material and reasonable "
              "(iustus error). A signatory who could have read the terms and did not "
              "rarely succeeds."),
    Authority("National and Overseas Distributors Corporation (Pty) Ltd v Potato Board",
              "1958 (2) SA 473 (A)",
              "Error in corpore — a mistake about the very subject matter of the "
              "contract — precludes true agreement and no contract arises."),
    Authority("Bayer South Africa (Pty) Ltd v Frost", "1991 (4) SA 559 (A)",
              "Fraudulent pre-contract misrepresentation grounds rescission and "
              "delictual damages; negligent misstatement may also sound in delict "
              "for pure economic loss."),
    Authority("Arend and Another v Astra Furnishers (Pty) Ltd", "1974 (1) SA 298 (C)",
              "Duress vitiates consent: a threat that is unlawful, imminent and "
              "operative on the mind of the contracting party makes the contract "
              "voidable, with restitution available."),
    Authority("Preller and Others v Jordaan", "1956 (1) SA 483 (A)",
              "Undue influence: where one party held influence over the other and "
              "used it to procure an unconscionable bargain, the transaction is "
              "voidable; the onus shifts once influence and the outcome are shown."),
    Authority("NBS Boland Bank Ltd v One Berg River Drive CC", "1999 (4) SA 928 (SCA)",
              "An 'agreement to agree' is void for vagueness unless it contains a "
              "workable deadlock-breaking mechanism. Terms must be definite or "
              "objectively determinable."),
    Authority("Sasfin (Pty) Ltd v Beukes", "1989 (1) SA 1 (A)",
              "An agreement contrary to public policy is unenforceable. Security terms "
              "that deprive a debtor of the means to earn are not saved by severance "
              "when they undermine the agreement's substance."),
    Authority("Peters, Flamman and Co v Kokstad Municipality", "1919 AD 427",
              "Supervening impossibility of performance without the debtor's fault "
              "extinguishes the obligation. Performance must be objectively impossible, "
              "not merely more difficult or more expensive."),
    Authority("KPMG Chartered Accountants (SA) v Securefin Ltd", "2009 (4) SA 399 (SCA)",
              "Interpretation admits the context known to the parties, including the "
              "nature and purpose of the contract — but evidence cannot contradict "
              "clear terms."),
    Authority("Bothma-Batho Transport (Edms) Bpk v S Bothma & Seun Transport "
              "(Edms) Bpk", "2014 (2) SA 494 (SCA)",
              "The words the parties used are the starting point: interpretation "
              "stays anchored in the language read in context, not in what a party "
              "wishes it had said."),
    Authority("Capitec Bank Holdings Ltd v Coral Lagoon Investments 194 (Pty) Ltd",
              "[2021] ZASCA 99; 2022 (1) SA 100 (SCA)",
              "Interpretation is not mechanical; the aim is the contract's objective "
              "meaning, but a court may not strain the words to avoid commercial "
              "consequences the parties themselves chose."),
    Authority("BK Tooling (Edms) Bpk v Scope Precision Engineering (Edms) Bpk",
              "1979 (1) SA 391 (A)",
              "Mora: where no time is fixed the debtor must be placed in mora by "
              "demand (mora ex persona); where a time is fixed the debtor is "
              "automatically in mora (mora ex re). Time is of the essence only "
              "where the contract says so clearly."),
    Authority("Scoin Trading (Pty) Ltd v Bernstein NO", "2011 (2) SA 118 (SCA)",
              "A date for performance is essential only where the contract makes it "
              "so, expressly or by necessary implication; the general position "
              "favours interpretation that keeps the contract alive."),
    Authority("Holmdene Brickworks (Pty) Ltd v Roberts Construction Co Ltd",
              "1977 (3) SA 670 (A)",
              "Measure of damages for defective performance: the reasonable cost of "
              "remedying the defect, or the difference between the value as performed "
              "and as warranted, whichever the circumstances indicate."),
    Authority("Datacolor International (Pty) Ltd v Intamarket (Pty) Ltd",
              "2001 (1) SA 581 (SCA)",
              "Repudiation requires conduct that unequivocally shows an intention not "
              "to be bound. The innocent party must elect — cancel, or hold the "
              "contract open — and the election must be plain."),
    Authority("Baker v Probert", "1985 (3) SA 429 (A)",
              "Cancellation of a contract obliges both parties to restore what they "
              "received; a party who rescinds cannot retain the benefits of the "
              "bargain while undoing its burdens."),
    Authority("Shatz Investments (Pty) Ltd v Kalovyrnas", "1976 (2) SA 545 (A)",
              "Interest as damages: interest on an unpaid sum is recoverable as "
              "damages where the debtor's breach caused the loss of use of the money."),
    Authority("Novartis SA (Pty) Ltd v Maphil Trading (Pty) Ltd",
              "[2015] ZASCA 111; 2016 (1) SA 518 (SCA)",
              "Damages after cancellation are measured by the difference between the "
              "contract price and the value of the performance actually rendered — "
              "the injured party is placed in the position it would have occupied "
              "had the contract been performed."),
    Authority("Thoroughbred Breeders' Association v Price Waterhouse",
              "2001 (4) SA 551 (SCA)",
              "Contractual damages aim at positive interesse: putting the innocent "
              "party in the position it would have been in had the contract been "
              "performed, not merely reversing its expenses."),
    Authority("Benson v SA Mutual Life Assurance Society", "1986 (1) SA 776 (A)",
              "Specific performance is a substantive right, but the court has a "
              "discretion to refuse it where the order would operate unduly harshly "
              "on the defendant."),
    Authority("ISEP Structural Engineering and Plating (Pty) Ltd v Inland "
              "Exploration Co (Pty) Ltd", "1981 (4) SA 1 (A)",
              "Specific performance is not a discretionary remedy in the narrow sense: "
              "a plaintiff is entitled to it as of right unless the defendant shows "
              "grounds for refusal. Adequacy of damages is not in itself such a ground."),
    Authority("Paiges v Van Ryn Gold Mines Estates Ltd", "1920 AD 600",
              "A pactum de non cedendo binds the parties but does not prevent the "
              "right from passing: a cession in breach of it is still effective, and "
              "the cedent answers in damages."),
    Authority("Magna Alloys and Research (SA) (Pty) Ltd v Ellis",
              "1984 (4) SA 874 (A)",
              "Restraints of trade are prima facie valid and enforceable. The onus is "
              "on the party alleging unreasonableness — not on the party enforcing."),
    Authority("Basson v Chilwan and Others", "1993 (3) SA 742 (A)",
              "Reasonableness of a restraint asks: is there a protectable interest, is "
              "the restraint's area and period reasonable, does it offend public "
              "policy, and does it go further than needed."),
    Authority("Mutual and Federal Insurance Co Ltd v Oudtshoorn Municipality",
              "1985 (1) SA 419 (A)",
              "Insurance contracts are uberrimae fidei: utmost good faith. Material "
              "non-disclosure or misrepresentation entitles the insurer to avoid the "
              "policy, regardless of the proposer's innocence."),
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


def reference_block(
    statutes: list[Statute],
    authorities: list[Authority] | None = None,
    include_authorities: bool = True,
) -> str:
    """Render the selected law for injection into the analysis prompt.

    `authorities` selects the leading cases to include; when omitted, the full
    pack is rendered (the historical behaviour).
    """
    parts = [
        "SOUTH AFRICAN LAW REFERENCE PACK",
        f"Curated and verified on {VERIFIED_ON} (pack {PACK_VERSION}). You may "
        "cite ONLY what appears below. Do not cite any other Act, section or "
        "case, and do not paraphrase a provision into a section number that is "
        "not listed here.",
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
        chosen = AUTHORITIES if authorities is None else authorities
        parts.append("### Leading authorities")
        for authority in chosen:
            parts.append(f"  - {authority.name} {authority.citation} — "
                         f"{authority.proposition}")
        parts.append("")
    return "\n".join(parts)


def authority_by_citation() -> dict[str, Authority]:
    """Map each authority's primary citation to the Authority object."""
    return {a.citation.split(";")[0].strip(): a for a in AUTHORITIES}


# ---------------------------------------------------------------------------
# Citation policing
# ---------------------------------------------------------------------------

_ACT_RE = re.compile(r"\b([A-Z][A-Za-z'()\-]*(?:\s+(?:of|and|in|the|for|to|"
                     r"[A-Z][A-Za-z'()\-]*)){0,9}?\s+Act)\s+(\d+)\s+of\s+(\d{4})")
_CASE_RE = re.compile(r"\[(\d{4})\]\s+(ZACC|ZASCA|ZAGPJHC|ZAGPPHC|ZAKZPHC|ZAWCHC|"
                      r"ZALCJHB|ZAECGHC|ZAFSHC|ZANWHC|ZALMPPHC|ZAMPMHC|ZANCHC)\s+(\d+)")
# Pre-2003 SA reports style: 1979 (1) SA 391 (A), 1999 (4) SA 928 (SCA), plus the
# BCLR/SACR reporters, the old Appellate Division and provincial divisions.
# Without these the whitelist simply cannot see the citation format most SA
# judgments use, and fabricated ones slip through unverified.
_SA_CASE_RE = re.compile(
    r"\b(\d{4})\s*\(\s*(\d{1,2})\s*\)\s*(SA|BCLR|SACR|ALL\s+SA)\s+(\d+)"
    r"\s*\(\s*([A-Z]{1,4})\s*\)"
)
_AD_CASE_RE = re.compile(r"\b(\d{4})\s+AD\s+(\d+)")
_PROV_CASE_RE = re.compile(
    r"\b(\d{4})\s+(CPD|EDL|GWL|NPD|OPD|EPD|TPD|WLD|SWA|NC)\s+(\d+)"
)


def _norm(citation: str) -> str:
    """A citation's identity, ignoring brackets, case and spacing."""
    return re.sub(r"\s+", "", citation.lower()).replace("[", "").replace("]", "")


def _known_acts() -> set[tuple[str, str]]:
    known = set()
    for statute in STATUTES:
        for number, year in re.findall(r"Act (\d+) of (\d{4})", statute.title):
            known.add((number, year))
    return known


def _known_cases() -> set[str]:
    """Every citable form of every authority, normalised."""
    known = set()
    for authority in AUTHORITIES:
        for part in authority.citation.split(";"):
            known.add(_norm(part.strip()))
    return known


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
        if _norm(citation) not in known_cases and citation not in unknown:
            unknown.append(citation)

    for year, volume, reporter, page, court in _SA_CASE_RE.findall(markdown or ""):
        citation = f"{year} ({volume}) {reporter} {page} ({court})"
        if _norm(citation) not in known_cases and citation not in unknown:
            unknown.append(citation)

    for year, page in _AD_CASE_RE.findall(markdown or ""):
        citation = f"{year} AD {page}"
        if _norm(citation) not in known_cases and citation not in unknown:
            unknown.append(citation)

    for year, division, page in _PROV_CASE_RE.findall(markdown or ""):
        citation = f"{year} {division} {page}"
        if _norm(citation) not in known_cases and citation not in unknown:
            unknown.append(citation)

    return unknown
