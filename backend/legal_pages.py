"""The About, Terms and Privacy page bodies, as Markdown.

Kept out of the Streamlit pages themselves for three reasons. The wording is a
legal disclosure and belongs under test. The same text will eventually have to
render into the static site as well, and two hand-maintained copies of a terms
page diverge within a month. And building the text from `Business` and `config`
means the pages cannot claim the software does something it does not.

That last point is doing real work here. The terms below describe a **free**
service whenever `PAYMENTS_ENABLED` is false, because in that state no payment
is taken, no price is shown and the ECTA cooling-off machinery has nothing to
attach to. This is the same `charging` distinction that `delivery.fulfil_order`
already enforces in code, expressed in prose.
"""

from __future__ import annotations

from backend import za_law
from backend.business import BUSINESS, NOT_SET, Business

# Counted from the pack rather than typed in, because the static marketing site
# still claims 17 statutes and the pack passed 30 some time ago. A number in a
# sales claim that nobody recomputes is a number that goes stale silently.
STATUTE_COUNT = len(za_law.STATUTES)
AUTHORITY_COUNT = len(za_law.AUTHORITIES)
IDENTIFIER_COUNT = 6  # SA ID, VAT, tax reference, CIPC, trust, bank branch code


def _warning(business: Business) -> str:
    """A banner naming the disclosures that are still outstanding, if any."""
    missing = business.missing_disclosures()
    if not missing:
        return ""
    # Each line needs its own "> " or the list escapes the blockquote and the
    # banner renders as a heading followed by loose bullets.
    items = "\n".join(f"> - {item}" for item in missing)
    return (
        "> **This page is not ready to publish.** The following details are "
        "required by law and have not been supplied, so they appear below as "
        f"placeholders:\n>\n{items}\n>\n"
        "> Set them in `.env` (see `.env.example`) before the site goes live.\n\n"
    )


# ---------------------------------------------------------------------------
# About
# ---------------------------------------------------------------------------
def about_markdown(business: Business = BUSINESS) -> str:
    """What the tool is, what it checks, and what it explicitly is not."""
    return f"""
# About Legal-Eye

Legal-Eye reads a contract and tells you what is in it and what looks risky,
under **South African law specifically** rather than law in general. Upload a
lease, an offer to purchase, a suretyship or an employment contract, and about a
minute later you get the parties, the obligations, the clauses worth arguing
about, the protections that are missing, and a risk rating out of 10.

## What it checks against

- **{STATUTE_COUNT} South African statutes**, from the Consumer Protection Act
  and the National Credit Act through to the Companies Act, the Alienation of
  Land Act and the Rental Housing Act. Only the statutes your document actually
  engages are applied.
- **{AUTHORITY_COUNT} leading judgments** on South African contract law,
  including *Beadica 231 CC v Trustees Oregon Trust* and *Barkhuizen v Napier*.
- **{IDENTIFIER_COUNT} kinds of South African identifier** are verified rather
  than taken at face value: ID numbers, VAT numbers, tax reference numbers, CIPC
  registration numbers, trust numbers and bank branch codes.

## How a review is produced

**One — extract.** The document is read and its facts are written down as
structured data: amounts, dates, parties, quantities. Nothing is judged yet.

**Two — verify.** The numbers are recomputed in ordinary code, not by the AI.
Does the payment schedule reconcile to the total? Does an ID number pass its
checksum? Was the company registered before the date it supposedly signed?

**Three — apply the law.** The relevant statutes are applied, and then every
citation in the output is checked against a curated list before you see it.
Anything outside that list is flagged as unverified rather than presented as
fact.

## Why the citation check exists

South African courts have ordered costs against practitioners personally, and
referred them to the Legal Practice Council, for filing authorities that an AI
invented. *Mavundla v MEC: COGTA KZN* and *Northbound Processing v SADPMR* are
the cautionary cases. Legal-Eye may cite only from a human-checked list, and
every citation is measured against it in code. This is the single most important
thing the tool does.

## What Legal-Eye is not

It is **not legal advice** and it is not a law firm. Using it creates no
attorney and client relationship. Under section 33 of the Legal Practice Act 28
of 2014, only an admitted legal practitioner may appear in court or draw
documents for use in legal proceedings — Legal-Eye does neither, and its output
must not be used for court papers.

Use it to work out which documents need an attorney's attention, and then take
them to one.

It can also be wrong. Any AI tool can misread a document, and OCR can misread
names, figures and dates on a scan. Check anything important against the
original.

## Your documents

Files are read in memory and deleted the moment analysis ends. Before any text
is sent for analysis, personal identifiers are replaced with placeholders. The
full position is in the [privacy notice](/Privacy).

---

*Legal-Eye is operated by {business.legal_name}, a {business.legal_form} in the
Republic of South Africa.*
"""


# ---------------------------------------------------------------------------
# Terms
# ---------------------------------------------------------------------------
def _ecta_table(business: Business) -> str:
    """The ECTA s 43(1) supplier disclosure table, for a sole proprietorship.

    Rows (a), (f) and (g) differ from the company case and are the reason this
    is generated rather than written once: a sole proprietorship has no separate
    legal personality, so there is no registration number and there are no
    directors. Saying that plainly is a complete answer to (f); leaving it blank
    is not.
    """
    if business.charging:
        price_row = (
            f"{business.price_display} per bundle. No VAT is charged. There are "
            "no delivery charges, transaction fees or other costs, and the price "
            "shown before you pay is the total."
        )
        payment_row = (
            "Card payment, processed by our payment provider. We never see or "
            "store your card details."
        )
        delivery_row = (
            "Immediately on successful payment, and in any event within one "
            "hour. If it has not arrived, check your spam folder, then contact us."
        )
    else:
        price_row = (
            "**Nothing. The service is currently provided free of charge.** No "
            "payment is taken and no price is charged for a review or for having "
            "it emailed to you."
        )
        payment_row = "Not applicable. No payment is taken."
        delivery_row = (
            "Immediately on request, and in any event within one hour. If it has "
            "not arrived, check your spam folder, then contact us."
        )

    rows = [
        ("(a) Name and legal status",
         f"{business.proprietor_name}, trading as {business.trading_name}. "
         f"A {business.legal_form} conducted in the Republic of South Africa. "
         "This is not a company: the proprietor is personally the supplier."),
        ("(b) Physical address and telephone",
         f"{business.physical_address}  \n{business.phone}"),
        ("(c) Website and email",
         f"This application  \n{business.support_email}"),
        ("(d) Self-regulatory or accreditation bodies",
         "None. Legal-Eye is not a law firm and is not a member of any legal "
         "professional body. It is not regulated by the Legal Practice Council, "
         "because it does not provide legal services."),
        ("(e) Code of conduct", "None."),
        ("(f) Registration number, office bearers, place of registration",
         "Not applicable. A sole proprietorship is not a registered legal "
         "entity, has no registration number and has no directors or other "
         "office bearers. The business is conducted in the Republic of South "
         "Africa."),
        ("(g) Address for legal service", business.physical_address),
        ("(h) What you are buying",
         "An automated review of one bundle of up to five documents, delivered "
         "to your email address as a file. It covers the parties, obligations, "
         "critical clauses, missing protections, red flags, a risk rating out of "
         "10 and recommended actions, applying South African law. It is produced "
         "by software, not by a person, and it is not legal advice."),
        ("(i) Full price", price_row),
        ("(j) Manner of payment", payment_row),
        ("(k) Terms, and how to keep them",
         "These terms. You can save or print this page at any time, and a copy "
         "of the terms in force when you used the service is available on request."),
        ("(l) Time for delivery", delivery_row),
        ("(m) Record of the transaction",
         "Your emailed review is your record. We keep the order record, and you "
         "may request a copy at any time."),
        ("(n) Return, exchange and refund policy",
         "Set out in section 4 below."),
        ("(o) Dispute resolution",
         "We have not adopted an alternative dispute resolution code. You may "
         "complain to the National Consumer Commission, or approach a court of "
         "competent jurisdiction."),
        ("(p) Security and privacy",
         "Our handling of personal information is set out in the "
         "[privacy notice](/Privacy)."),
        ("(q) Minimum duration",
         "None. Each review is a single, once-off transaction. There is no "
         "subscription and nothing recurring."),
        ("(r) Your section 44 rights", "Set out in section 3 below."),
    ]
    header = "| ECTA s 43(1) | Detail |\n|---|---|\n"
    body = "\n".join(
        f"| {label} | {value} |" for label, value in rows
    )
    return header + body


def _cooling_off(business: Business) -> str:
    """Section 3. The cooling-off analysis only bites where there is a sale."""
    if not business.charging:
        return """## 3. Cooling-off rights

Section 44 of ECTA gives a consumer seven days to cancel an **electronic
transaction** without reason and without penalty.

Because the service is currently free, there is no sale, nothing is paid and
there is nothing to cancel or refund. Section 44 has nothing to attach to. If
you would rather we did not email you a review, simply do not ask for one.

If charging is introduced later, this section will be replaced with the full
section 44 and section 42(2)(d) position, and you will see the consent step at
checkout before any payment is taken."""

    return """## 3. Your cooling-off right, and when it falls away

Section 44 of ECTA gives a consumer seven days to cancel an electronic
transaction without reason and without penalty. For services, that period runs
from the date the agreement is concluded.

> **Read this before you tick the delivery box.** Section 42(2)(d) of ECTA
> provides that the seven-day cooling-off right does not apply to a service that
> began, with your consent, before the seven days had passed. Because your
> review is sent immediately on payment, we ask you to confirm separately, at
> checkout, that you want delivery to start straight away. If you give that
> confirmation, delivery begins at once and the seven-day right in section 44
> falls away by operation of section 42(2)(d).

You do not have to give that confirmation. If you would rather keep the seven-day
right, do not tick the box and contact us instead. We will hold your order and
deliver after the seven days have passed.

We record the date and time of that confirmation with your order. We do not
purport to exclude any right under Chapter VII of ECTA, and any term that tried
to would be void under section 48 in any event. Nothing in these terms limits
any right you have under the Consumer Protection Act."""


def _refunds(business: Business) -> str:
    """Section 4."""
    if not business.charging:
        return f"""## 4. Refunds

Nothing is charged, so there is nothing to refund.

If a review never arrived, or is materially wrong about what your document says,
or your document could not be read properly and we did not warn you, we still
want to know. Email {business.support_email} and we will re-run it."""

    return f"""## 4. Refunds

If you cancel under section 3 above, or under section 43(3), you get a **full
refund**. We deduct nothing. Section 44(2) of ECTA allows a supplier to charge
only the direct cost of returning goods, and since a review is a file there is
nothing to return and nothing to deduct. Refunds are made within 30 days of
cancellation, as section 44(3) requires, and usually far sooner.

Separately from any legal right, we will refund you if:

- the review never arrived and we cannot deliver it;
- the review is materially wrong about what your document says; or
- the document could not be read properly and we did not warn you.

Email {business.support_email} with your order reference. We would rather refund
you than argue."""


def terms_markdown(business: Business = BUSINESS) -> str:
    """The full terms and conditions."""
    if business.charging:
        short = (
            "Legal-Eye reads a contract and tells you what is in it and what "
            "looks risky. It is not a lawyer and it is not legal advice. You see "
            "the review on screen for free. You pay only if you want a copy "
            "emailed to you. If we get something wrong, tell us and we will "
            "refund you."
        )
        liability_cap = (
            "our total liability arising out of any review is limited to the "
            "amount you paid for that review"
        )
    else:
        short = (
            "Legal-Eye reads a contract and tells you what is in it and what "
            "looks risky. It is not a lawyer and it is not legal advice. The "
            "service is currently free: nothing is charged, for the review or "
            "for having it emailed to you."
        )
        liability_cap = (
            "our total liability arising out of any review is limited to the "
            "amount you paid for it, which is currently nothing, and in any "
            "event to R1,000"
        )

    return f"""{_warning(business)}# Terms and conditions

*Last updated {business.effective_date}.*

These terms are written in plain language, as section 22 of the Consumer
Protection Act 68 of 2008 requires. If anything here is unclear, email us before
you use the service and we will explain it.

> **The short version.** {short}

## 1. Who you are contracting with

The information below is provided as section 43(1) of the Electronic
Communications and Transactions Act 25 of 2002 requires. Each row corresponds to
a paragraph of that section.

{_ecta_table(business)}

### A note on VAT

{business.trading_name} is **not a registered VAT vendor**. No VAT is charged on
any amount, no VAT is included in any price shown, and no VAT invoice can be
issued. If that changes we will register, display the number here, and say so.

## 2. Checking your order before you commit

Section 43(2) of ECTA entitles you to review the whole transaction, correct any
mistakes, and withdraw from it, before you finally place your order. Before
anything is sent you will see a summary showing the documents, the email address
the review will go to, and any amount payable, with the ability to change any of
them or to abandon the process entirely.

If we fail to give you any of the information in section 1 above, or fail to give
you that review step, section 43(3) of ECTA entitles you to cancel within 14 days
of receiving the review.

{_cooling_off(business)}

{_refunds(business)}

## 5. What Legal-Eye is not

This section matters more than any other, so it is set out plainly.

1. **It is not legal advice.** Legal-Eye is an automated tool that reads
   documents and reports what it finds. It does not know your circumstances,
   your commercial position or what you have been told verbally.
2. **No attorney and client relationship is created** by using the service, and
   nothing you upload is protected by legal professional privilege as against us.
3. **It must not be used for court documents.** Under section 33 of the Legal
   Practice Act 28 of 2014, only an admitted legal practitioner may appear in
   court or draw documents intended for use in legal proceedings. Legal-Eye does
   neither and you must not use its output for that purpose.
4. **The proprietor is not an admitted legal practitioner.** Legal-Eye is
   software, sold as software. Nothing it produces is the work of an attorney.
5. **AI can be wrong, including about the law.** Automated systems can misread a
   document, and can misstate or invent statutory references and case citations.
   Legal-Eye restricts citations to a curated list and flags anything outside it,
   but you must verify every statutory reference and citation against a primary
   South African source before relying on it.
6. **Scanned documents are read by OCR**, which can misread names, figures and
   dates. Always check important details against the original.

## 6. Limitation of liability

> **Please read this clause carefully. It limits our liability to you, and
> section 49 of the Consumer Protection Act requires us to draw it to your
> attention specifically.** By using a review you acknowledge that you have read
> and understood it.

Legal-Eye is supplied as a triage tool. To the extent the law allows,
{liability_cap}. We are not liable for a decision you took, or did not take, on
the strength of a review, and you should obtain advice from an admitted legal
practitioner before acting.

Nothing in this clause limits our liability for death or personal injury, for
fraud, for gross negligence, or for anything else that cannot lawfully be
limited. In particular, section 51 of the Consumer Protection Act makes any
attempt to waive liability for gross negligence void, and we do not attempt it.
Section 43(6) of ECTA makes us liable for damage caused by a failure to use a
sufficiently secure payment system, and that liability is not limited here.

## 7. Delivery failures

If we cannot deliver your review, section 46 of ECTA requires us to tell you and,
where anything was paid, refund you within 30 days. We will do both, and in
practice within a working day.

## 8. Your documents and your personal information

Your documents are read in memory and deleted immediately after analysis.
Personal identifiers are replaced with placeholders before any text is sent for
analysis. Delivered reviews are removed from our records after
{business.retention_days} days. The full position is in the
[privacy notice](/Privacy), which forms part of these terms.

## 9. Law and disputes

These terms are governed by the law of the Republic of South Africa. Section 47
of ECTA applies the protections in Chapter VII regardless of any choice of law,
and we do not attempt to displace them. Complaints go to
{business.support_email} first. If we cannot resolve it, you may approach the
National Consumer Commission, or a court of competent jurisdiction.
"""


# ---------------------------------------------------------------------------
# Privacy
# ---------------------------------------------------------------------------
def privacy_markdown(business: Business = BUSINESS) -> str:
    """The POPIA section 18 notice."""
    paid_rows = ""
    if business.charging:
        paid_rows = (
            "\n| Payment confirmation and reference | To reconcile payments and "
            "handle refunds. We never receive your card details. | At least five "
            "years, as tax law requires. |"
        )

    return f"""{_warning(business)}# Privacy notice

*Last updated {business.effective_date}.*

This notice is given under section 18 of the Protection of Personal Information
Act 4 of 2013 (POPIA).

> **The short version.** Your document is read and then deleted. Before any text
> leaves our server for analysis, ID numbers, email addresses, phone numbers and
> account numbers are swapped for placeholders. Analysis is done by an AI
> provider outside South Africa, which we explain below. If you ask for delivery
> we keep your email address and the order record, and we delete the review
> itself after {business.retention_days} days.

## Who is responsible

The responsible party is **{business.legal_name}**, a {business.legal_form}
conducted at {business.physical_address}.

Because this is a sole proprietorship and not a company, the proprietor is
personally the responsible party, and is also the Information Officer for the
purposes of POPIA: **{business.information_officer}**.

For anything in this notice, contact {business.support_email}.

## What we collect, and why

| Information | Why we have it | How long we keep it |
|---|---|---|
| The document you upload | To produce your review. It is the whole purpose of the service. | Read in memory and deleted immediately after analysis. Not stored. |
| Personal information inside that document, such as the names of parties, directors or sureties | It arrives as part of your document. We do not seek it out and we do not use it for anything other than producing your review. | Same as above. Deleted with the document. |
| Your email address | To deliver the review you asked for, and to keep the order record. | Order record retained at least five years for tax purposes. |
| The review itself, if you asked for delivery | So we can resend it if delivery fails. | Deleted {business.retention_days} days after delivery. The order record stays; the review text goes. |{paid_rows}
| Marketing consent, if you gave it | To send you occasional emails about Legal-Eye. Recorded separately from your order. | Until you withdraw it. |

## Identifiers are removed before analysis

Before your document text is sent for analysis, we replace personal identifiers
with placeholders: South African ID numbers, email addresses, telephone numbers
and account numbers. The real values are put back only in the review shown on
your screen and in the copy emailed to you.

We want to be straight with you about the limit of this. It removes
**identifiers**. It does not remove **names**, which cannot be detected reliably
by pattern alone, and a name in a contract is still personal information. So this
reduces what crosses the border. It does not reduce it to nothing.

## Processing outside South Africa

Analysis is performed by {business.ai_provider_description} located in
**{business.ai_provider_country}**. This is a transfer of personal information
outside the Republic, and it is governed by section 72 of POPIA.

We rely on {business.section_72_basis}.

South Africa has no list of countries deemed to give adequate protection, so we
do not claim that any country is adequate. We minimise what is transferred, as
described above. You should assume that the laws of the receiving country differ
from South African law and may permit access by authorities there.

**If you would prefer that your document is not processed outside South Africa,
do not upload it, and contact us instead.**

## Marketing

Giving us your address so we can deliver a review is **not** consent to market
to you. Section 69 of POPIA requires separate opt-in consent for electronic
direct marketing, and we ask for it separately, with the box unticked. If you do
opt in, every message carries an unsubscribe link and you can withdraw at any
time.

## Who else sees your information

- The AI provider described above, for analysis only.
- Our email delivery provider, which transmits your review.
{"- Our payment provider, which handles your payment and holds your card details rather than us." if business.charging else ""}

We do not sell your information, and we do not share it for advertising.

## Your rights

Under POPIA you may ask us what personal information we hold about you
(section 23), ask us to correct or delete information that is inaccurate,
irrelevant, excessive or out of date (section 24), and object to processing
(section 11(3)). Email {business.support_email} and we will respond within a
reasonable time and without charge for a straightforward request.

If you are not satisfied, you may complain to the Information Regulator (South
Africa), JD House, 27 Stiemens Street, Braamfontein, Johannesburg, or by email to
complaints.IR@justice.gov.za.

## Security

We take the steps section 19 of POPIA requires: encrypted connections, restricted
access to the order records, no storage of uploaded documents, and deletion of
review text after {business.retention_days} days. If personal information is ever
accessed by someone unauthorised, we will notify the Information Regulator and
you, as section 22 requires.
"""
