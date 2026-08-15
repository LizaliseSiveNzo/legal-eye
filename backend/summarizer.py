"""Two-pass document analysis: extract facts, verify them in code, then analyse.

Pass 1 asks the model only to read and record what the document says, as JSON.
`backend.forensics` then checks those facts against each other in plain Python —
arithmetic, dates, entity names. Pass 2 writes the analysis with those verified
findings in hand, so the hardest conclusions rest on arithmetic rather than on
whether the model happened to do the sum.
"""

import json
import re
import time
from dataclasses import dataclass
from collections.abc import Callable

from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from backend.config import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    MAX_INPUT_CHARS,
    MAX_OUTPUT_TOKENS,
    PRICE_INPUT_CACHE_MISS,
    PRICE_OUTPUT,
    RETRY_BACKOFF,
    TEMPERATURE,
    require_api_key,
)
from backend.forensics import Finding, findings_block, risk_score, run_checks
from backend.redaction import Redaction, redact, restore
from backend.za_law import applicable_statutes, reference_block, unknown_citations

EXTRACTION_MAX_TOKENS = 2_000

# ---------------------------------------------------------------------------
# Pass 1 — read and record. No judgement, no analysis.
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """You are a legal document extraction engine. Read the \
document and record what it says as JSON. Do not analyse, judge, or comment.

Return ONLY a JSON object with exactly these keys:

{
  "document_type": string,
  "document_date": "YYYY-MM-DD" or null,
  "governing_law": string or null,
  "parties": [
    {"name": string, "role": string, "source": "main document" | "attachment"}
  ],
  "signatory": {"name": string|null, "title": string|null, "entity": string|null},
  "signed_by_all_parties": true | false | null,
  "total_consideration": {"amount": number|null, "currency": string|null},
  "payment_schedule": [
    {"label": string, "amount": number, "due": string,
     "payable_before_delivery": true|false|null}
  ],
  "payment_method": string or null,
  "bank_details_present": true | false | null,
  "quantity": {"value": number|null, "unit": string|null,
               "description": string|null},
  "goods_are_graded_or_heterogeneous": true | false | null,
  "quantities_mentioned": [
    {"label": string, "value": number, "unit": string, "source": string}
  ],
  "grade_breakdown": [
    {"label": string, "value": number, "unit": string}
  ],
  "key_dates": [
    {"label": string, "date": "YYYY-MM-DD",
     "is_official_act": true|false, "is_deadline": true|false}
  ],
  "contact_emails": [string],
  "addresses": [string],
  "attachments": [{"title": string, "what_it_certifies": string}],
  "obligations": [{"party": string, "obligation": string}],
  "governing_law_stated": true | false,
  "dispute_resolution_stated": true | false,
  "escrow_present": true | false,
  "inspection_rights_present": true | false,
  "refund_mechanism_present": true | false,
  "legal_regulatory_issues": [string],
  "notable_statements": [string]
}

RULES
1. Use null (or false for the boolean protection flags) when the document does
   not address something. Never guess and never invent a value.
2. Amounts are plain numbers: 1391189.00, not "$1,391,189.00". Dates are ISO.
3. "payable_before_delivery" is true when the payment falls due before the payer
   receives or can independently inspect what they are paying for.
4. "goods_are_graded_or_heterogeneous" is true when the document or its
   attachments describe the subject matter as falling into different grades,
   qualities, categories or condition classes.
5. "quantities_mentioned" collects every headline quantity across the whole
   bundle, including attachments, with its source — this is how a figure in an
   exhibit gets compared against the figure in the covering document.
6. "is_official_act" is true for dates on which a government body, registry,
   court, notary or regulator is said to have done something.
7. "notable_statements" captures sentences a careful reader would want quoted:
   future or larger transactions, unusual conditions, pressure to move quickly,
   unexplained third parties. Quote them verbatim, up to 10.
8. Read attachments and exhibits as carefully as the covering document.
9. "grade_breakdown" transcribes any schedule that splits the subject matter
   into categories, grades, classes or line items with quantities — copy every
   line with its label exactly as written. This is how the composition of what
   is being sold gets measured against its headline description. Leave the list
   empty if the document contains no such schedule.
10. "legal_regulatory_issues" records statutory, licensing, sanctions, AML or
   KYC, export-control, customs, consumer-protection or professional-conduct
   obligations that the document engages or appears not to satisfy. Record the
   issue and the text that raises it. Do not draw a conclusion about whether
   any law was broken."""

# ---------------------------------------------------------------------------
# Pass 2 — analyse, with verified findings in hand.
# ---------------------------------------------------------------------------

ANALYSIS_SYSTEM_PROMPT = """You are Legal-Eye, a forensic legal document \
analyst. You are reviewing a document on behalf of the reader, who may be about \
to rely on it, sign it, or pay against it.

You will receive the document text, a structured extraction of its facts, and a
list of VERIFIED FINDINGS computed in code from the document's own figures.

HOW TO TREAT THE VERIFIED FINDINGS
- They are arithmetic, calendar and string comparisons. They are reliable.
- Every finding above "info" severity MUST appear in your output, in Red Flags
  or in the Risk Assessment table. Before you finish, walk the list and confirm
  each one is there. Do not drop a finding because it looks small next to the
  others — the reader is relying on the list being complete.
- Never contradict one. If you believe a finding is explained by something in
  the text, say so and keep the finding.

POSTURE — this matters more than any formatting rule
- Be evidence-based, not soft. Neutrality means every adverse observation is
  anchored to specific text or a verified figure. It does NOT mean avoiding
  adverse observations, hedging them into vagueness, or assuming good faith.
- Rate risk by consequence to the reader, not by how prominent the document
  makes it. A clause that is not there can be the largest risk on the page.
- You may write "Do not transfer funds until X" and "Do not sign until Y" where
  the document puts the reader's money or rights beyond recovery.
- Where the document's structure defeats verification — payment before
  inspection, sealed goods, settlement details arriving separately — say so
  plainly and explain the mechanism.

NAMING A PATTERN
- When three or more independent indicators point the same way, name the
  pattern explicitly (for example an advance-fee structure, an invoice
  redirection setup, a shell-entity chain), and list the indicators.
- Frame it exactly like this: the bundle matches a documented template, which
  is a reason to verify independently before anything irreversible happens.
- Never state or imply that a named person or company has committed fraud or
  any crime. You assess documents, not people. Distinguish always between
  "this document does not establish X" and "X is false".

RED TEXT
- Wrap the few things the reader must not miss in
  <span style="color:#c00000">**...**</span>.
- Use it for: the risk rating when it is 8 or above, every Critical finding,
  and every instruction not to do something ("do not transfer funds").
- Maximum 8 red passages in the whole document. Red everywhere is red nowhere,
  and the reader stops seeing it. Nothing below High severity is ever red.

STRICT OUTPUT STRUCTURE — these headings, in this order:

# Document Risk Rating: N/10 — BAND
- Use the verified risk score supplied with the findings. Do not compute or
  invent your own number, and do not round it up or down.
- One sentence underneath saying what that rating means for this reader.

## Read This First
- The 4 to 8 things that matter most, as single-line bullets, most important
  first. Assume some readers finish nothing else.
- Anything from Legal & Regulatory Exposure comes first in this list.
- Each bullet states the fact and its consequence, not a topic heading.

## Legal & Regulatory Exposure
- Include this section ONLY where the document raises statutory, licensing,
  sanctions, AML or KYC, export-control, customs, professional-conduct or
  similar issues. If it raises none, omit the heading entirely — do not write
  a placeholder.
- One bullet per issue: what the document does or fails to do, which obligation
  that engages, and what the lawyer needs to establish to close it out.
- Frame every entry as an issue requiring attention, never as an allegation
  that a named person or company has broken the law. "The document does not
  evidence X" is supportable; "they broke X" is not.

# Executive Summary
- 4 to 6 short sentences. What the document is, whether it is executed and
  binding, the core commercial terms, and the single most important thing the
  reader must do or avoid. Every sentence under 30 words.
- If the document carries Critical risk, the first sentence says so.

## At a Glance
- Table (Field | Detail): Document type, Execution status, Parties,
  Value / consideration, Unit price (if derivable), Term / duration,
  Governing law, Signed by.
- "Not stated" where the document is silent. One line per cell.
- For Execution status, distinguish "signed by both parties", "signed by one
  party only", and "unsigned". Do not call an unexecuted document binding.

## Red Flags
- Authenticity, counterparty, title, valuation and pressure indicators.
- Format: **Indicator —** what the document says, then what it would take to
  resolve it. One to three lines each.
- Include every verified finding of concern, plus anything you observe.
- Close with a short paragraph naming the overall pattern, if there is one.
- If genuinely nothing is of concern, write "No authenticity or counterparty
  concerns identified." Do not pad this section to look thorough.

## Parties
- Every party, bolded, with role. Flag any party that is undefined, appears
  under more than one legal form, or is copied in without a stated role.

## Obligations
- Grouped by party. Who must do what, by when, for how much.

## Critical Clauses
- Only clauses actually present. Format: **Clause name (reference):** what it
  says, then its practical effect on the reader.

## Missing or Unaddressed
- Protections a document of this type would normally contain but this one does
  not. One line each: what is absent, and what it exposes the reader to.

## Risk Assessment
- Table: Risk | Severity | Why it matters. Up to 12 rows.
- Rows MUST run Critical, then High, then Medium, then Low, with no exceptions.
  Re-read the table before you output it and fix any row that is out of order —
  a High row sitting below a Medium row tells the reader it is less serious.
- Severity definitions, applied strictly:
  Critical = irreversible loss is likely if the reader proceeds without
             independent verification first.
  High     = material financial loss, uncapped exposure, or no enforceable
             remedy.
  Medium   = real uncertainty or likely dispute, bounded exposure.
  Low      = minor, or easily fixed before signing.
- Do not cluster everything at Medium. If nothing is Critical, say so in one
  line under the table.

## Recommendations
- 4 to 8 concrete actions, most important first, each starting with a bold verb.
- Order them so anything that must happen BEFORE money moves comes first.
- Where verification is advised, state that it must go through channels the
  reader sources independently — never contact details, links or references
  supplied by the counterparty.

## Legal Disclaimer
- The disclaimer below, verbatim.

DISCLAIMER (verbatim):
"This summary was generated by an automated AI tool for informational purposes
only and does not constitute legal advice. It may contain errors, omissions,
or misinterpretations of the source document. You should not rely on this
summary for making legal decisions and should consult a qualified attorney
for advice on your specific situation. Always review the original document."

RULES
1. Base every factual statement on the supplied text, extraction, or verified
   findings. If something is not there, write "Not stated in the document".
   Judging how serious a stated fact is, is expected. Inventing facts is not.
2. Quote the document directly when a sentence carries the risk.
3. If the input is not a contract or agreement (a report, prospectus, memo,
   letter), say so
   in one italic line under the title, then complete the sections that apply
   and mark the rest "Not applicable to this document type".
4. Bold party names, money amounts and dates. No paragraph over four lines.
4a. HOUSE STYLE. Never use an em dash. Where you would reach for one, use a full
   stop, a comma, a colon or brackets instead. Vary sentence length: a short
   sentence after a long one reads like a person wrote it. Avoid the
   three-item list used for rhythm rather than meaning, avoid "not just X but
   Y", and avoid opening a sentence with "Importantly" or "Notably". Write the
   way a careful attorney writes a file note: plain, specific, unhurried.
5. Output only the structured Markdown. No preamble."""

# Kept so existing imports and tests continue to resolve.
LEGAL_SYSTEM_PROMPT = ANALYSIS_SYSTEM_PROMPT

ZA_ADDENDUM = """

=== SOUTH AFRICAN JURISDICTION ===

This document is being reviewed for a reader in South Africa. Apply South
African law: the common law of contract as developed by our courts, and the
statutes in the reference pack supplied with this request.

CITATION DISCIPLINE — this is the hardest rule in this prompt.
- Cite ONLY Acts, sections and cases that appear in the supplied reference pack.
- If the point you want to make needs a provision that is not in the pack, make
  the point WITHOUT a citation, and say that the specific provision should be
  confirmed with a legal practitioner.
- Never invent a section number. Never guess an Act number or year. Never
  reconstruct a case citation from memory.
- South African courts have ordered costs de bonis propriis against
  practitioners and referred them to the Legal Practice Council for filing
  AI-fabricated authorities. A wrong citation in this report can cost the
  reader far more than a missing one.
- Where the pack marks a threshold or commencement date as uncertain, repeat
  that uncertainty. Do not present it as settled.

ADD THIS SECTION, immediately after Legal & Regulatory Exposure:

## South African Law Notes
- Only the statutes and doctrines that this document actually engages.
- Format: **Act or doctrine —** the provision, what it requires, and what in
  THIS document meets or fails to meet it.
- Lead with anything going to validity: formalities not met, an agent without
  written authority, a trustee without letters of authority, an unlicensed
  practitioner, a term that is void rather than merely unfair.
- Where a provision makes something VOID rather than voidable or unenforceable,
  say so explicitly — it changes what the reader can still do.
- If the document engages no South African statute beyond the general law of
  contract, write one line saying so. Do not pad.

SOUTH AFRICAN FRAMING
- Amounts in Rand: R1 234 567.89.
- This is a Roman-Dutch system. There is no general doctrine of consideration,
  and per Beadica good faith and ubuntu inform public policy but are not
  free-standing grounds to refuse enforcement.
- Do not import English or American concepts the reader cannot use.

REPLACE the disclaimer with this text, verbatim:
"This review was produced by an automated tool for information only. It is not
legal advice, does not create an attorney-client relationship, and must not be
used to prepare documents for court proceedings. AI systems can misstate or
fabricate legal authorities: every statutory reference, section number and case
citation above must be independently verified against primary South African
sources before any reliance is placed on it. Document text is processed by a
third-party AI provider outside South Africa. Submitting confidential material
to a third-party system may affect legal professional privilege. Consult an
admitted South African legal practitioner before acting."
"""

PLAIN_LANGUAGE_ADDENDUM = """

=== PLAIN LANGUAGE ===

The reader is not a lawyer. Same analysis, same findings, different register.
- Explain every legal term the first time it appears, in the sentence itself.
  "voetstoots (sold as-is, so the seller is not answerable for faults)".
- Say what a provision MEANS FOR THEM before naming it: "the sale may not be
  valid at all, because of a rule in the Alienation of Land Act", not
  "s 2(1) non-compliance renders the deed void".
- Keep the section and Act references — they are what a lawyer will need if the
  reader takes this further — but never leave one unexplained.
- Prefer "you" and "the other side". No Latin without a translation. No
  "notwithstanding", "herein", "the aforesaid".
- Every recommendation must be an action the reader can actually take this week.
"""

TRUNCATION_NOTICE = (
    "\n\n[Document truncated to {limit:,} characters to control API cost.]"
)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Return a lazily-created, reused DeepSeek client."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=require_api_key(), base_url=DEEPSEEK_BASE_URL)
    return _client


def _truncate_text(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    """Cut text to max_chars at a word boundary and append a truncation notice."""
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars]
    boundary = clipped.rfind(" ")
    if boundary > max_chars * 0.9:
        clipped = clipped[:boundary]
    return clipped.rstrip() + TRUNCATION_NOTICE.format(limit=max_chars)


def _chat(system: str, user: str, max_tokens: int, json_mode: bool = False) -> str:
    """One chat completion, retrying on rate limits and mapping errors to plain English."""
    client = _get_client()
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}

    last_rate_limit: Exception | None = None
    for pause in (*RETRY_BACKOFF, None):
        try:
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=TEMPERATURE,
                max_tokens=max_tokens,
                **kwargs,
            )
            break
        except AuthenticationError as exc:
            raise RuntimeError(
                "Invalid API key. Check the key in your .env file."
            ) from exc
        except RateLimitError as exc:
            last_rate_limit = exc
            if pause is None:
                raise RuntimeError(
                    f"AI service rate limit exceeded after {len(RETRY_BACKOFF)} retries. "
                    "Try again later, or check that your account has credit."
                ) from exc
            time.sleep(pause)
        except APIConnectionError as exc:
            raise RuntimeError(
                "Cannot reach the AI service. Check your internet connection."
            ) from exc
        except APIStatusError as exc:
            raise RuntimeError(
                f"The AI service returned an error (HTTP {exc.status_code}). "
                "Check your account status and try again."
            ) from exc
    else:  # pragma: no cover - the loop always breaks or raises
        raise RuntimeError(str(last_rate_limit))

    if not response.choices:
        raise RuntimeError("The AI service returned an empty response.")
    return (response.choices[0].message.content or "").strip()


def _parse_json(raw: str) -> dict:
    """Parse the extraction response, tolerating a stray code fence or preamble."""
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def extract_facts(text: str) -> dict:
    """Pass 1: record what the document says as structured JSON."""
    return _parse_json(_chat(EXTRACTION_PROMPT, text, EXTRACTION_MAX_TOKENS, json_mode=True))


@dataclass(frozen=True)
class Analysis:
    """The finished review, plus the numbers the caller needs to present it."""

    summary: str
    findings: list[Finding]
    score: int
    band: str
    jurisdiction: str = "GENERAL"
    unverified_citations: list[str] = None
    redaction_summary: str = ""


# Fallback for the rare run where extraction fails and the model rates the
# document itself: read the rating back out of its own title.
_TITLE_RATING = re.compile(
    r"Risk Rating:\s*(\d{1,2})\s*/\s*10\s*[—\-–]\s*([A-Za-z]+)", re.IGNORECASE
)


def analyze_legal_document(
    text: str,
    on_progress: Callable[[str], None] | None = None,
    jurisdiction: str = "ZA",
    audience: str = "professional",
    redact_personal_information: bool = True,
) -> Analysis:
    """Extract, verify, then analyse.

    If extraction or the deterministic checks fail, the analysis still runs —
    just without verified findings — so a bad pass 1 degrades quality rather
    than losing the reader their answer.
    """
    if not text or not text.strip():
        raise ValueError("Nothing to summarize — the document text is empty.")

    def report(stage: str) -> None:
        if on_progress is not None:
            on_progress(stage)

    payload = _truncate_text(text)

    # POPIA s 72: pseudonymise identifiers before anything crosses the border.
    scrub: Redaction = redact(payload) if redact_personal_information else Redaction(payload)
    payload = scrub.text

    system_prompt = ANALYSIS_SYSTEM_PROMPT
    if jurisdiction.upper() == "ZA":
        system_prompt += ZA_ADDENDUM
    if audience == "plain":
        system_prompt += PLAIN_LANGUAGE_ADDENDUM

    report("Reading the document and extracting facts...")
    try:
        facts = extract_facts(payload)
    except RuntimeError:
        raise
    except Exception:
        facts = {}

    report("Checking the figures, dates and entities...")
    findings = run_checks(facts) if facts else []
    score, band = risk_score(findings)

    report("Analysing risk...")
    za_pack = ""
    if jurisdiction.upper() == "ZA":
        statutes = applicable_statutes(payload, facts)
        za_pack = "\n\n" + reference_block(statutes)

    if facts:
        context = (
            "DOCUMENT TEXT\n"
            f"{payload}\n\n"
            "STRUCTURED EXTRACTION\n"
            f"{json.dumps(facts, indent=2, ensure_ascii=False)}\n\n"
            "VERIFIED FINDINGS (computed in code from the figures above)\n"
            f"{findings_block(findings)}\n\n"
            "VERIFIED RISK SCORE\n"
            f"{score}/10 — {band}. Use this figure in the title. It is derived "
            "from the findings above by a fixed rule, so it is defensible; a "
            "number you choose yourself is not." + za_pack
        )
    else:
        context = payload + za_pack

    summary = _chat(system_prompt, context, MAX_OUTPUT_TOKENS)
    if not summary:
        raise RuntimeError("The AI service returned an empty response.")

    # Restore the real identifiers into the report, which never leaves this machine.
    summary = restore(summary, scrub.mapping)

    # Police the citations. Anything outside the curated pack is surfaced, not
    # quietly published — fabricated authority is the one error that can cost
    # the reader a costs order.
    unverified: list[str] = []
    if jurisdiction.upper() == "ZA":
        unverified = unknown_citations(summary)
        if unverified:
            listed = "\n".join(f"- {c}" for c in unverified)
            summary += (
                "\n\n---\n\n> **Unverified citations.** The following references "
                "are not in this tool's curated list of South African authorities "
                "and may be inaccurate or entirely fabricated. Verify each one "
                "against a primary source before relying on it:\n"
                f"{listed}\n"
            )

    if not findings:
        match = _TITLE_RATING.search(summary)
        if match:
            score = max(1, min(10, int(match.group(1))))
            band = match.group(2).capitalize()

    return Analysis(summary=summary, findings=findings, score=score, band=band,
                    jurisdiction=jurisdiction.upper(),
                    unverified_citations=unverified,
                    redaction_summary=scrub.summary())


def summarize_legal_document(
    text: str,
    on_progress: Callable[[str], None] | None = None,
    **options,
) -> str:
    """Return just the Markdown analysis. Kept for callers that want only text."""
    return analyze_legal_document(text, on_progress=on_progress, **options).summary


def estimate_cost(input_chars: int) -> float:
    """Rough upper-bound cost in USD for a two-pass analysis of this document."""
    # ~4 characters per token is the usual English approximation. Assume a full
    # cache miss and maxed-out responses on both passes, so the figure never
    # flatters. Pass 2 re-sends the document plus the extraction, so its input
    # is charged at roughly twice the document size.
    billed_chars = min(input_chars, MAX_INPUT_CHARS)

    extraction_in = (billed_chars + len(EXTRACTION_PROMPT)) / 4
    analysis_in = (billed_chars * 2 + len(ANALYSIS_SYSTEM_PROMPT)) / 4
    input_cost = (extraction_in + analysis_in) / 1_000_000 * PRICE_INPUT_CACHE_MISS

    output_tokens = EXTRACTION_MAX_TOKENS + MAX_OUTPUT_TOKENS
    output_cost = output_tokens / 1_000_000 * PRICE_OUTPUT

    return round(input_cost + output_cost, 4)
