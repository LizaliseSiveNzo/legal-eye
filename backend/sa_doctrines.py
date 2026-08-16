"""South African common-law doctrine pack.

The counterpart of za_law.STATUTES: a curated set of contract-law doctrines,
each with the triggers that select it for a document, an accurate statement of
the current law, and the leading authorities that anchor it (the Authority
objects themselves live in za_law.AUTHORITIES — this file references them by
primary citation, so the propositions stay in one place).

The same rules apply as to the statute pack: the model may rely on these
statements, and may cite only the authorities in the Leading authorities
section. Where a proposition could not be verified to the date in
za_law.VERIFIED_ON, the entry says so instead of guessing.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.za_law import (
    AUTHORITIES,
    Authority,
    authority_by_citation,
    trigger_pattern,
)


@dataclass(frozen=True)
class Doctrine:
    key: str
    name: str
    triggers: tuple[str, ...]
    statement: str
    authority_keys: tuple[str, ...] = ()
    caveat: str = ""

    def matches(self, haystack: str) -> bool:
        return trigger_pattern(self.triggers).search(haystack) is not None


# The cases every South African report gets, whatever the document — the
# constitutional framework of modern SA contract law and the two cautionary
# tales about fabricated authority.
CORE_AUTHORITY_KEYS: tuple[str, ...] = (
    "1964 (4) SA 760 (A)",   # Shifren — non-variation clauses
    "[2007] ZACC 5",         # Barkhuizen — public policy test
    "[2020] ZACC 13",        # Beadica — good faith's true reach
    "2012 (4) SA 593 (SCA)", # Endumeni — interpretation
    "1958 (2) SA 465 (A)",   # George v Fairmead — caveat subscriptor
    "[2025] ZAKZPHC 2",      # Mavundla — fabricated citations
    "[2025] ZAGPJHC 661",    # Northbound — AI accuracy duty
)

DOCTRINES: tuple[Doctrine, ...] = (
    Doctrine(
        "FORMATION",
        "Formation and consensus",
        ("offer", "acceptance", "accepts", "accepted", "signature", "signed",
         "conclude", "concluded", "agreement", "appendix", "addendum"),
        "A contract requires real agreement on its essential terms. An offer "
        "must be definite enough that acceptance turns it into a contract; a "
        "purported acceptance that changes the terms is a counter-offer, which "
        "kills the original offer. In postal contracts acceptance is complete "
        "on posting (expedition theory). An offer may be revoked any time before "
        "acceptance, and revocation by publication is effective against people "
        "who had not yet accepted. Where one party's conduct reasonably creates "
        "the appearance of agreement, that party can be held to the appearance "
        "under quasi-mutual assent. Check in the document whether the 'acceptance' "
        "actually accepted, or quietly varied, the offer.",
        ("1921 CPD 244", "1915 AD 100", "1911 AD 121"),
    ),
    Doctrine(
        "MISTAKE",
        "Mistake and iustus error",
        ("mistake", "error", "misunderstanding", "iustus", "misunderstood",
         "clerical error", "erroneous"),
        "Only a mistake that is both material (as to identity, terms or subject "
        "matter) and reasonable (iustus) avoids a contract. A signatory is bound "
        "by what they sign — caveat subscriptor — unless the error is excusable. "
        "The classic excusable cases: the other party knew or caused the mistake, "
        "or induced it by misrepresentation. Error about the very subject matter "
        "(error in corpore) means no agreement ever came into being. A party who "
        "could have read the document and did not rarely succeeds in avoiding it.",
        ("1992 (3) SA 234 (A)", "1958 (2) SA 473 (A)"),
    ),
    Doctrine(
        "MISREPRESENTATION",
        "Misrepresentation",
        ("misrepresentation", "misrepresented", "representation", "warrants",
         "warranty", "disclosure", "nondisclosure", "non-disclosure"),
        "A pre-contract misrepresentation grounds rescission where it induced "
        "the contract. If fraudulent, rescission carries delictual damages too; "
        "a negligent misstatement may sound in delict for pure economic loss. "
        "An innocent misrepresentation supports rescission in principle but not "
        "damages. A clause saying the buyer 'acknowledges no representations "
        "were made' does not by itself defeat a proved misrepresentation, and "
        "in consumer transactions the CPA limits the effect of such clauses.",
        ("1991 (4) SA 559 (A)",),
    ),
    Doctrine(
        "DURESS",
        "Duress and intimidation",
        ("duress", "coercion", "intimidation", "threat", "threatened", "force",
         "undue pressure", "compelled"),
        "Consent procured by duress makes the contract voidable and entitles the "
        "victim to restitution. The requirements are a threat of considerable "
        "evil that is unlawful, imminent and actually operative on the mind of "
        "the threatened party. Economic pressure can amount to duress only in "
        "clear cases; a threat to exercise a lawful right (such as to cancel or "
        "to sue) is not duress.",
        ("1974 (1) SA 298 (C)",),
    ),
    Doctrine(
        "UNDUE_INFLUENCE",
        "Undue influence",
        ("undue influence", "influence", "fiduciary", "confidence", "adviser",
         "dependent", "vulnerable party"),
        "Where one party held influence over the other and used it to procure an "
        "unconscionable bargain, the transaction is voidable. Once the influenced "
        "party shows the relationship of influence and a bargain that calls for "
        "an explanation, the burden shifts to the other party to prove the "
        "transaction was freely and fairly concluded. Relationships of confidence "
        "— adviser and client, trustee and beneficiary, caregiver and dependent "
        "— are the natural triggers.",
        ("1956 (1) SA 483 (A)",),
    ),
    Doctrine(
        "CERTAINTY",
        "Certainty of terms",
        ("agreement to agree", "vague", "uncertain", "to be agreed", "to be "
         "negotiated", "deadlock", "price to be determined"),
        "Terms must be definite or objectively determinable, or the contract is "
        "void for vagueness. An 'agreement to agree' — a promise to negotiate the "
        "price or the terms later — is generally void unless it supplies a "
        "workable deadlock-breaking mechanism, such as valuation by a named third "
        "party. A formula (CPI-linked, bank prime-linked, published list price) "
        "saves a clause; a bare promise to agree later does not.",
        ("1999 (4) SA 928 (SCA)",),
    ),
    Doctrine(
        "FORMALITIES",
        "Formalities",
        ("in writing", "written", "signature required", "formality",
         "formalities", "signed by both parties", "witnesses"),
        "South African contract law requires no writing, except where statute "
        "imposes one — the Alienation of Land Act for land, the General Law "
        "Amendment Act s 6 for suretyships, the Wills Act for wills. Where the "
        "statute requires writing and signature, non-compliance makes the "
        "transaction void, and estoppel cannot supply the missing formality. "
        "Where only the parties' own agreement requires writing (a non-variation "
        "clause), the question is governed by Shifren: oral variations are void "
        "only if the clause entrenches itself. Check the statute, not habit, "
        "before calling a formality mandatory.",
        ("1964 (4) SA 760 (A)",),
    ),
    Doctrine(
        "ILLEGALITY",
        "Illegality and public policy",
        ("illegal", "unlawful", "public policy", "contrary to law", "prohibited",
         "unenforceable", "contra bonos mores"),
        "A contract contrary to statute or public policy is unenforceable, and "
        "what was performed under it is generally not recoverable (the par delictum "
        "rule, with narrow exceptions). Security or credit terms that deprive a "
        "debtor of the means to earn can be struck down as contrary to public "
        "policy. Since Beadica, good faith and ubuntu inform public policy but are "
        "not free-standing grounds to refuse enforcement. Distinguish clauses that "
        "are void outright from those a court might sever.",
        ("1989 (1) SA 1 (A)",),
    ),
    Doctrine(
        "IMPOSSIBILITY",
        "Impossibility and force majeure",
        ("impossibility", "impossible", "force majeure", "act of god", "vis "
         "major", "casus fortuitus", "circumstances beyond", "loadshedding",
         "load shedding"),
        "Supervening impossibility of performance, without the debtor's fault, "
        "extinguishes the obligation. The impossibility must be objective — "
        "performance must have become impossible, not merely more difficult, "
        "expensive or commercially unattractive. A force majeure clause is "
        "interpreted like any other term: what it lists counts, and general "
        "words are read against the specific events listed. Without a clause, "
        "the common law applies. A party who caused the impossibility through "
        "its own fault remains liable.",
        ("1919 AD 427",),
    ),
    Doctrine(
        "VARIATION",
        "Variation and non-variation clauses",
        ("variation", "vary", "amendment", "amend", "no variation", "entire "
         "agreement", "non-variation", "changes to this agreement"),
        "A contract may be varied by agreement, express or tacit. A non-variation "
        "clause entrenches the requirement of written, signed variation — but only "
        "if the clause also entrenches itself; otherwise it can itself be varied "
        "orally and the shield fails. An entire-agreement clause bars additional "
        "TERMS, not contextual evidence of meaning. Electronic variation is "
        "possible where the parties' own formalities are met (Spring Forest). "
        "Read both clauses together before advising that a variation is void.",
        ("1964 (4) SA 760 (A)", "2015 (2) SA 118 (SCA)"),
    ),
    Doctrine(
        "INTERPRETATION",
        "Interpretation",
        ("interpretation", "interpreted", "construction", "meaning of",
         "ambiguous", "ambiguity", "defined terms", "clause means"),
        "The governing rule is objective: the meaning a reasonable reader, aware "
        "of the context and purpose, would give the words. Language, context and "
        "purpose are considered together from the outset — there is no threshold "
        "of ambiguity first. The words used remain the anchor; a court will not "
        "strain them to reach a kinder commercial outcome. Contra proferentem is "
        "a last resort, not a starting point. Where the model proposes a meaning "
        "of a clause, it must first quote the actual words.",
        ("2012 (4) SA 593 (SCA)", "2009 (4) SA 399 (SCA)",
         "2014 (2) SA 494 (SCA)", "[2021] ZASCA 99"),
    ),
    Doctrine(
        "PAROL",
        "Parol evidence and integration",
        ("parol", "integration", "entire agreement", "exclusive memorial",
         "extrinsic evidence", "surrounding circumstances"),
        "Where a written contract is the exclusive memorial of the agreement, "
        "extrinsic evidence may not contradict, add to or vary its terms. But "
        "evidence of context and purpose is always admissible to interpret it, "
        "and evidence may be led to show the contract is void, voidable or "
        "subject to a condition precedent. An entire-agreement clause bars "
        "additional terms, not interpretation aids. Flag where the document "
        "purports to be the whole agreement while an annexure or email is "
        "excluded without saying so.",
        ("1941 AD 43", "2012 (4) SA 593 (SCA)"),
    ),
    Doctrine(
        "MORA",
        "Mora (default)",
        ("mora", "default", "late payment", "late performance", "delay",
         "overdue", "within 30 days", "due date", "interest on"),
        "Where no time for performance is fixed, the debtor must be placed in "
        "mora by demand before breach arises (mora ex persona). Where a time is "
        "fixed, the debtor is in mora automatically (mora ex re). A date is "
        "'essential' — allowing cancellation for lateness alone — only where the "
        "contract says so clearly. Mora interest runs from the date of default "
        "at the agreed rate, or the prescribed rate where none is agreed. Check "
        "the document: 'time is of the essence' changes the default position "
        "materially.",
        ("1979 (1) SA 391 (A)", "2011 (2) SA 118 (SCA)"),
    ),
    Doctrine(
        "POSITIVE_MALPERFORMANCE",
        "Defective performance",
        ("defective", "defects", "quality", "specification", "specifications",
         "not fit for purpose", "poor workmanship", "remedy the defect",
         "latent defect", "voetstoots", "sold as is"),
        "Defective performance is breach. The aggrieved party's remedies: "
        "damages measured by the reasonable cost of remedying the defect or the "
        "difference between value as performed and as warranted; a reduction of "
        "the price; or, for material defects, cancellation. For latent defects "
        "in a sale the aedilitian remedies (actio redhibitoria, actio quanti "
        "minoris) apply unless excluded — and where the CPA applies, the "
        "implied quality warranty limits how far they can be excluded.",
        ("1977 (3) SA 670 (A)",),
    ),
    Doctrine(
        "REPUDIATION",
        "Repudiation and anticipatory breach",
        ("repudiation", "repudiate", "anticipatory", "refuse to perform",
         "walk away", "abandon", "cancel the agreement", "terminate the "
         "agreement"),
        "Repudiation is conduct that unequivocally shows an intention not to be "
        "bound. The innocent party then has an election: cancel and claim "
        "damages, or hold the contract open and tender performance. The election "
        "must be plain — silence is not cancellation. A wrongful 'cancellation' "
        "by one party is itself a repudiation the other may accept. Check the "
        "document's cancellation clauses: a unilateral right to terminate is "
        "construed strictly and exercised precisely.",
        ("2001 (1) SA 581 (SCA)",),
    ),
    Doctrine(
        "EXCEPTIO",
        "Exceptio non adimpleti contractus",
        ("reciprocal", "simultaneous performance", "co-dependent", "subject to "
         "delivery", "payment upon delivery", "against delivery"),
        "In reciprocal contracts a party claiming performance must itself be "
        "ready and willing to perform (exceptio non adimpleti contractus). The "
        "defence suspends, rather than cancels, the obligation. A clause making "
        "one party's obligation conditional on the other's performance is the "
        "contractual form of the same idea. Where the document demands payment "
        "before delivery but the counterparty's obligation is described as "
        "'against delivery', the tension should be flagged.",
        ("1979 (1) SA 391 (A)",),
    ),
    Doctrine(
        "CANCELLATION",
        "Cancellation and restitution",
        ("cancellation", "cancel", "rescission", "rescind", "restitution",
         "restore", "refund", "return of goods", "termination"),
        "Cancellation for breach requires a material breach or an express "
        "cancellation right (lex commissoria), followed by a clear election. "
        "Cancellation obliges both parties to restore what they received — a "
        "party cannot keep the benefit while undoing the burden. Clauses that "
        "say the seller keeps all payments on cancellation are penalty clauses: "
        "enforceable in principle but reducible, and in consumer transactions "
        "potentially void under the CPA. Map what the document says happens to "
        "money already paid on termination.",
        ("1985 (3) SA 429 (A)",),
    ),
    Doctrine(
        "DAMAGES",
        "Damages for breach",
        ("damages", "loss", "losses", "claim for", "compensation", "liable "
         "for", "indemnify", "indemnity", "recover"),
        "Contractual damages aim at positive interesse: putting the innocent "
        "party where it would have been had the contract been performed. Loss "
        "must be caused by the breach and not too remote. After cancellation, "
        "damages are measured by the difference between contract price and the "
        "value of performance actually rendered. Interest on unpaid money is "
        "recoverable as damages. Indemnity clauses (first-party losses, "
        "including third-party claims and costs) go further than liability "
        "caps and should be assessed separately from them.",
        ("2001 (4) SA 551 (SCA)", "[2015] ZASCA 111", "1976 (2) SA 545 (A)"),
    ),
    Doctrine(
        "SPECIFIC_PERFORMANCE",
        "Specific performance",
        ("specific performance", "compel performance", "enforce performance",
         "must perform", "obligation to deliver"),
        "Specific performance is a substantive right: the aggrieved party is "
        "entitled to an order compelling performance unless the defendant shows "
        "grounds for refusal, such as undue hardship. That damages would be "
        "adequate is not in itself a ground. In practice the questions for a "
        "document are whether performance remains possible, and whether the "
        "contract describes the obligation precisely enough to be compelled.",
        ("1986 (1) SA 776 (A)", "1981 (4) SA 1 (A)"),
    ),
    Doctrine(
        "CESSION",
        "Cession and delegation",
        ("cession", "cede", "assign", "assignment", "delegation", "novation",
         "third party rights", "transfers its rights"),
        "Rights are transferred by cession, which needs no writing (unless the "
        "underlying right requires it) and no debtor's consent — the debtor "
        "performs to the cessionary once notified. A pactum de non cedendo binds "
        "the parties but a cession in breach of it still transfers the right; "
        "the cedent answers in damages. Obligations, by contrast, are delegated "
        "only with the creditor's consent — a clause letting one party 'transfer "
        "this agreement' without consent is a warning sign for the counterparty.",
        ("1920 AD 600",),
    ),
    Doctrine(
        "ESTOPPEL",
        "Estoppel",
        ("estoppel", "estopped", "represented", "relied on", "held out",
         "apparent authority", "ostensible"),
        "Estoppel prevents a party from denying a state of affairs its "
        "representation caused another to rely on, to that other's prejudice. "
        "It is a shield, not a sword: it cannot found a cause of action, and it "
        "cannot circumvent a statutory formality (a sale of land without the "
        "Alienation of Land Act writing cannot be rescued by estoppel). In "
        "company contracts, apparent authority of directors is now largely "
        "governed by the Companies Act s 20(7), which codified the Turquand "
        "rule.",
        (),
        "No single authority is cited: estoppel propositions vary by context. "
        "Apply the general requirements — representation, fault, prejudice — "
        "and rely on the statutory authority for company dealings.",
    ),
    Doctrine(
        "RESTRAINT",
        "Restraint of trade",
        ("restraint of trade", "non-compete", "non-solicitation", "restraint",
         "non compete", "compete", "solicit", "goodwill"),
        "Restraints of trade are prima facie valid: the onus is on the party "
        "alleging unreasonableness. The reasonableness inquiry asks whether the "
        "restrainer has a protectable interest (customer connections, "
        "confidential information, goodwill), whether the restraint's area and "
        "duration are reasonable, and whether it offends public policy or goes "
        "further than needed. In employment, a restraint cannot protect against "
        "mere competition by an employee using general skill and knowledge. "
        "Reasonableness is judged at the time of enforcement.",
        ("1984 (4) SA 874 (A)", "1993 (3) SA 742 (A)"),
    ),
    Doctrine(
        "INSURANCE_PRINCIPLES",
        "Insurance principles",
        ("insurance", "insurer", "insured", "policy", "premium", "underwriter",
         "cover", "excess"),
        "Insurance contracts are uberrimae fidei: the proposer must disclose "
        "every material fact, and material non-disclosure or misrepresentation "
        "entitles the insurer to avoid the policy. What is 'material' is judged "
        "by the reasonable insurer's standard. Indemnity clauses in commercial "
        "contracts are not insurance and none of this applies to them — do not "
        "conflate the two. For consumer insurance the Policyholder Protection "
        "Rules add disclosure, waiting-period and cancellation protections.",
        ("1985 (1) SA 419 (A)",),
    ),
    Doctrine(
        "AGENCY",
        "Agency and authority",
        ("agent", "agency", "authority", "authorised", "mandate", "power of "
         "attorney", "on behalf of", "duly authorised"),
        "An agent binds the principal only within actual or ostensible "
        "authority. Actual authority may be express or implied; ostensible "
        "authority arises where the principal's representation causes the third "
        "party reasonably to believe in it. For companies, s 20(7) of the "
        "Companies Act protects good-faith outsiders against internal-formality "
        "defects, but never against a total absence of authority. An agent "
        "contracting without authority warrants authority and is personally "
        "liable. Check the document: who signs, for whom, under what authority.",
        (),
        "Statutory anchor only — Companies Act s 20(7) in the statute pack. "
        "The common-law propositions are settled and cited without a case.",
    ),
    Doctrine(
        "ENRICHMENT",
        "Enrichment",
        ("enrichment", "unjustified enrichment", "unjust enrichment",
         "restitution", "money had and received", "condictio"),
        "Where money or value moved under an invalid or failed contract, the "
        "transferor may recover it through the enrichment remedies (condictio "
        "indebiti and its relatives) — the general action requires enrichment "
        "without cause, impoverishment, and absence of a defence. This is the "
        "safety net behind cancellation and voidness: when the document's "
        "termination clause is silent on restitution of payments already made, "
        "the common law may still require them to be returned.",
        (),
        "Stated as doctrine without a case anchor; the propositions are "
        "settled but the leading authorities are not in this pack.",
    ),
)

# ---------------------------------------------------------------------------
# Selection and rendering
# ---------------------------------------------------------------------------


def applicable_doctrines(text: str, facts: dict | None = None) -> list[Doctrine]:
    """Pick the doctrines a document actually engages, by trigger word."""
    haystack = (text or "").lower()
    if facts:
        haystack += " " + " ".join(
            str(v) for v in (facts.get("document_type"), facts.get("payment_method"))
            if v
        ).lower()
    selected = [d for d in DOCTRINES if d.matches(haystack)]
    # A document with no doctrinal trigger still gets the general frame.
    if not selected:
        selected = [d for d in DOCTRINES if d.key in {"FORMATION", "INTERPRETATION", "MORA"}]
    return selected


def select_authorities(doctrines: list[Doctrine]) -> list[Authority]:
    """The leading cases for this run: the fixed core plus the selected doctrines'."""
    by_citation = authority_by_citation()
    keys: list[str] = list(CORE_AUTHORITY_KEYS)
    for doctrine in doctrines:
        for key in doctrine.authority_keys:
            if key not in keys:
                keys.append(key)
    return [by_citation[key] for key in keys if key in by_citation]


def doctrine_block(doctrines: list[Doctrine]) -> str:
    """Render the selected doctrines for injection into the analysis prompt."""
    if not doctrines:
        return ""
    parts = [
        "COMMON LAW DOCTRINES",
        "Selected for this document. Apply these as the current South African "
        "common law. Cite only the cases in the Leading authorities section "
        "above.",
        "",
    ]
    for doctrine in doctrines:
        parts.append(f"### {doctrine.name}")
        parts.append(doctrine.statement)
        if doctrine.caveat:
            parts.append(f"  ! CAVEAT: {doctrine.caveat}")
        parts.append("")
    return "\n".join(parts)


def doctrine_keys_resolve() -> list[str]:
    """Return any doctrine authority key that does not exist in the pack."""
    by_citation = authority_by_citation()
    missing: list[str] = []
    for doctrine in DOCTRINES:
        for key in doctrine.authority_keys:
            if key not in by_citation:
                missing.append(f"{doctrine.key}: {key}")
    for key in CORE_AUTHORITY_KEYS:
        if key not in by_citation:
            missing.append(f"CORE: {key}")
    return missing
