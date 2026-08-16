# Legal-Eye: knowledge base gap analysis

Reviewed against `backend/za_law.py` pack 2.0, verified 2026-08-16.
Written 16 August 2026.

---

## First, what is actually there

Worth stating plainly, because the pack is in better shape than a quick look
suggests:

- **34 statutes**, each with trigger words, an `applies_when` scope note and a
  list of concrete checks.
- **40 leading authorities**, injected selectively rather than all at once.
- **Confidence is genuinely used**, not decorative: 18 entries marked high, 15
  medium, 1 low, and **17 carry an explicit caveat**. That is unusual discipline
  and it is the reason I trust the rest of the file.
- A **citation guard** (`unknown_citations`) that flags anything the model cites
  which is not in the pack, recognising SA-style, AD and provincial-division
  citation formats.

The coverage already spans consumer, credit, electronic transactions, land,
suretyship, companies, trusts, privacy, AML, prescription, penalties,
jurisdiction, property practitioners, employment, rental, exchange control,
minerals, interest, insolvency, matrimonial property, competition, corruption,
statutory interpretation, negotiable instruments, payments, VAT, sectional
titles, eviction, workplace injury, insurance, public procurement, wills and
estates, customary marriage, and debt collection.

So this is not a thin knowledge base. The gaps below are real, but they are the
gaps of a serious pack, not a starter one.

---

## The uncomfortable part: your stated goal is two products

> "know everything about the south African justice system so that it would be
> able to answer all questions that were brought to it"

That describes a **legal research and advice product**. What you have built is a
**document review product**. They look similar and they are not, and the
difference is where the risk sits.

**Document review is bounded.** The document supplies the facts. Your pack
supplies the law. The output is issue-spotting against a fixed frame, and every
claim can be traced to either the document or a whitelisted provision. When the
tool does not know something, the document is still there for the reader to
check. That is defensible, and the citation whitelist is what makes it
defensible.

**Open question answering is unbounded.** There is no document to anchor to, no
natural limit on what gets asked, and no way for the reader to check the answer
against anything. Every wrong answer is entirely yours. And the failure mode is
not "I don't know" but a fluent, confident, wrong section number, which is
exactly what earned costs orders *de bonis propriis* in *Mavundla* and
*Northbound*, both of which you already cite in your own file header.

There is a second problem specific to you. You are not an admitted attorney.
Legal Practice Act s 33 reserves court appearance and preparing documents for
proceedings, so a review tool is lawful. But a product that answers "can I evict
my tenant" is doing something a reasonable person will experience as legal
advice, whatever the disclaimer says, and no disclaimer has ever prevented a
complaint from someone who relied on a wrong answer and lost money.

**My recommendation:** pursue "knows more" hard and "answers anything" not at
all. Depth of coverage inside document review is where the commercial value is
anyway, because that is what a professional will pay for.

---

## Structural gaps, which matter more than the missing statutes

A longer list of Acts will not fix any of these, and each one silently degrades
accuracy across every document.

### 1. The whitelist is a single point of trust

This is the most important item on the page. `unknown_citations` flags anything
outside the pack, which means anything **inside** the pack is presented to the
reader as verified. If a single citation in `za_law.py` carries a typo or a
wrong year, your guard does not catch it. It certifies it.

One transposed digit turns your strongest feature into a liability, and it will
be invisible because everything downstream trusts the file.

**Fix:** a scheduled human verification pass, entry by entry, against a primary
source, recorded per entry rather than per file. Add `verified_on` and
`verified_by` to `Statute` and `Authority`, and a test that fails the build when
any entry is older than, say, twelve months. Today `VERIFIED_ON` is a single
module-level date covering all 74 entries, which cannot stay true as the pack
grows.

### 2. Trigger words are lexical, so coverage is accidental

`applicable_statutes` lowercases the text and looks for whole words. That means:

- An IP licence agreement containing none of your trigger words falls through to
  the fallback and gets **only** Prescription and Jurisdiction.
- "goods" pulls in the entire CPA whether or not the document is a consumer
  transaction.
- There are no negative triggers, so nothing can rule a statute out.

You already extract `document_type` in the first pass. Routing on document type,
in addition to keywords, would fix most of this cheaply. Semantic matching over
short statute descriptions would fix the rest.

### 3. Numbers that move are frozen in prose

Several thresholds in the pack change on their own schedule:

| Value | Moves |
|---|---|
| Prescribed rate of interest | Repo-linked, resets twice a year |
| CPA juristic person threshold (R2m) | By ministerial determination |
| NCA thresholds | By determination |
| BCEA earnings threshold | Annually |
| National minimum wage | Annually |

Frozen in an `applies_when` string, these rot silently and the tool keeps
asserting them with confidence. They belong in a small rates module with
effective-date ranges, so the pack can say "as at" and warn when the figure is
stale.

### 4. The model reasons over your paraphrase, not the statute

`checks` are summaries. For most provisions that is fine. For **formalities** it
is not, because formalities turn on exact words and the consequence of getting
one wrong is that the whole agreement is void:

- General Law Amendment Act s 6 (suretyship in writing, signed by the surety)
- Alienation of Land Act s 2(1) (sale of land in writing, signed by both)
- Wills Act s 2(1) (execution formalities)
- Copyright Act s 22(3) (assignment in writing, signed by the assignor)

Store those verbatim. Perhaps thirty provisions in total. It is the highest
accuracy return per line of work in this whole document.

### 5. Cases have no subsequent history

An `Authority` records a name, a citation and a proposition. It does not record
whether the case is still good law. *Beadica* materially recalibrated how
*Barkhuizen* is applied, and both sit in your pack side by side with equal
weight. Add a `status` field and a `superseded_by`, and the pack starts encoding
how the law moved rather than a flat list of names.

### 6. The reader is never told what the tool did not know

Right now a review looks equally confident whether the document sat squarely
inside your 34 statutes or fell mostly outside them. This is the honesty feature
your competitors will not build, and it costs almost nothing: when the analysis
raises an issue that maps to no statute in the pack, say so.

> "This document raises questions under intellectual property law, which is
> outside this tool's verified reference pack. Those points are flagged but not
> analysed against a statute."

A professional will trust the tool **more** for saying that, not less. It is
also the cheapest possible protection against the exact complaint that would hurt
you most.

### 7. OCR is English only

`packages.txt` installs `tesseract-ocr-eng` and `OCR_LANGUAGE` defaults to
`eng`. Afrikaans contracts are ordinary in South African property, agricultural
and estate work, and an Afrikaans scan currently OCRs into noise that the model
then confidently analyses.

Adding `tesseract-ocr-afr` to `packages.txt` is a one-line change. It is
probably the single cheapest accuracy improvement available to you.

---

## Domain gaps, ranked

**Every citation below is a candidate that must be verified against a primary
source before it enters the whitelist.** I am working from knowledge, not from a
licensed database, and per point 1 above an unverified entry in the pack is worse
than an absent one. Treat this as a research list.

### Tier 1: missing, and they change outcomes in common documents

| Area | Why it belongs | Rough effort |
|---|---|---|
| **Constitution of the Republic, 1996** | ss 39(2), 34, 25, 9, 14. Your pack cites *Barkhuizen* and *Beadica* but not the constitutional hook they turn on. Public policy control of contract terms runs through here. | Small |
| **CPA Regulations, GNR 293 of 2011** | Regulation 44 is a list of terms **presumed unfair**. For a contract review tool this is close to a ready-made checklist, and you already carry the parent Act. Regulation 2 covers franchise agreements. | Small, very high value |
| **Intellectual property: Copyright Act 98 of 1978, Trade Marks Act 194 of 1993, Patents Act 57 of 1978, Designs Act 195 of 1993** | IP assignment and licence clauses appear in most commercial agreements. Copyright s 22(3) is a formality trap of the same family as suretyship, and you catch none of it today. | Medium |
| **Companies Act, the parts you do not cover** | Business rescue (Ch 6), s 45 financial assistance, s 75 personal financial interest, s 20(7) and the Turquand rule. Business rescue in particular changes what a counterparty can lawfully sign. | Medium |
| **B-BBEE Act 53 of 2003 and the Codes** | Nearly every South African supply, services and procurement contract carries a B-BBEE clause. You have PPPFA and PFMA but not the substantive regime. | Medium |
| **Deeds Registries Act 47 of 1937 and Transfer Duty Act 40 of 1949** | Property is one of your best consumer segments and you have Alienation of Land without the registration and duty layer. | Medium |
| **Income Tax Act 58 of 1962 and Tax Administration Act 28 of 2011** | s 35A withholding on non-resident sellers catches people constantly; s 7C on loans to trusts pairs with the Trust Property Control Act you already have. | Medium |
| **Close Corporations Act 69 of 1984** | Still a large installed base, and members' interests transfer differently from shares. | Small |
| **PAIA 2 of 2000** | The natural twin of POPIA, which you cover well. | Small |
| **Cybercrimes Act 19 of 2020** | Data, security and breach-notification clauses. | Small |

### Tier 2: real gaps, narrower documents

| Area | Note |
|---|---|
| PAJA 3 of 2000, and the Institution of Legal Proceedings against Certain Organs of State Act 40 of 2002 | The s 3 notice requirement and short time bar is a brutal trap in anything involving an organ of state |
| MPRDA 28 of 2002 | You have Diamonds and Precious Metals but not the rights regime underneath them |
| Housing Consumer Protection Measures Act 95 of 1998 | NHBRC enrolment on new builds |
| FAIS 37 of 2002, Financial Sector Regulation Act 9 of 2017 | Anything touching financial advice or intermediation |
| Employment beyond LRA and BCEA | Employment Equity Act 55 of 1998, OHSA 85 of 1993, National Minimum Wage Act 9 of 2018 |
| Family: Divorce Act 70 of 1979, Children's Act 38 of 2005, Maintenance Act 99 of 1998 | Pairs with the Matrimonial Property and Customary Marriages entries you already have |
| Superior Courts Act 10 of 2013 | Jurisdiction above the magistrates' courts |
| Apportionment of Damages Act 34 of 1956 | Liability and indemnity clauses |
| NEMA 107 of 1998 | Property and industrial transactions |
| Legal Practice Act 28 of 2014 | You rely on it in your own disclaimer; it should be in the pack |

### Tier 3: common-law doctrines with no entry

Your 40 authorities are strong on formation, interpretation, penalties and
public policy. These doctrines decide real disputes and appear to have no
coverage:

- **Simulated transactions and substance over form.** The single most useful
  doctrine for a fraud-adjacent review tool, and you have nothing on it.
- **Stipulatio alteri**, contracts for the benefit of a third party
- **Tacit terms**, and the officious bystander test
- **Estoppel**
- **Cession, delegation and assignment**
- **Set-off, novation and compromise**
- **Rectification**
- **Suspensive and resolutive conditions**
- **Latent defects and the common-law voetstoots position**, alongside the CPA
  treatment you already have
- **Caveat subscriptor** and the ticket cases
- **Unjustified enrichment**
- ***Pactum commissorium***, forfeiture in security agreements

I have deliberately not given case citations here. Given point 1, sending you a
list of remembered citations to paste into the trust anchor of your product
would be irresponsible. Identify the doctrine, then have the leading case
confirmed against a primary source before it goes in.

---

## The corpus question, and an honest ceiling

Your file header already reaches the right conclusion, and the research confirms
it. Restating it with the current position:

| Source | Content | Commercial use |
|---|---|---|
| **Laws.Africa Content API** | Consolidated legislation | CC-BY-NC-SA by default, **but they explicitly welcome commercial use under negotiated terms**. Legislation only, no case law. |
| **gov.za** | Acts as gazetted, bilingual PDFs | Free, but **as enacted, not consolidated**. Dangerous on its own: you would cite provisions that later amendments repealed. |
| **SAFLII** | Judgments | Blocks automated and AI access |
| **AfricanLII, LawLibrary** | Judgments | CC BY-NC, excludes commercial use |
| **LexisNexis SA, Juta** | Everything, curated | Closed, commercial, expensive |

The strategic conclusion is worth saying in one line:

> **Statutes scale. Case law does not.**

Consolidated legislation is licensable today, from one source, on terms you can
negotiate. Case law has no clean commercial feed short of a publisher deal. So
the sensible architecture is asymmetric: retrieve statutes from a licensed
corpus, and keep the case law hand-curated, small and verified. That also
matches where the value is, because a wrong section number is embarrassing and a
wrong case citation is what gets people referred to the Legal Practice Council.

That is also the honest ceiling on "knows everything". You can get to
near-complete statutory coverage. You cannot get to complete case law coverage
without a publisher licence, and no amount of engineering changes that.

---

## What I would do, in order

**This month, cheap and high return**

1. Add `tesseract-ocr-afr` to `packages.txt`. One line.
2. Add the known-unknowns line to the report. The tool says when a document
   raises issues outside the pack.
3. Add per-entry `verified_on`, and a test that fails when an entry goes stale.
4. Add CPA Regulations reg 44 and reg 2. Highest value per hour of work in this
   document.
5. Route statute selection on `document_type`, not only trigger words.

**Next quarter**

6. Verbatim text for the thirty formality provisions.
7. Tier 1 domains, in the table's order, verified as you go.
8. A rates module for the moving thresholds, with effective dates.
9. `status` and `superseded_by` on `Authority`.

**When revenue justifies it**

10. Contact Laws.Africa about commercial terms for consolidated legislation, and
    move statutory coverage to retrieval while keeping the whitelist as the
    citation guard. The two mechanisms are complementary: retrieval decides what
    the model *sees*, the whitelist decides what it may *cite*.
11. Have an admitted practitioner review the whole pack. This is the item that
    converts the knowledge base from a personal project into an asset a buyer
    would pay for, and it is also the one you cannot do yourself.

---

## What I would not do

- **Do not add statutes in bulk to raise the count.** An unverified entry is
  worse than a gap, because the guard certifies it.
- **Do not build open legal Q&A**, for the reasons in the second section.
- **Do not scrape SAFLII.** Their terms prohibit it, they are the goodwill of the
  South African legal community, and being the legal-tech company that scraped
  the free case law repository is not a reputation you recover from.
- **Do not let the pack's single `VERIFIED_ON` date grow stale.** It is currently
  honest. In six months, unchanged, it will be a false statement made to every
  reader of every report.

---

*This is an engineering and product analysis, not legal advice. The statutory
references are research leads for a qualified South African practitioner to
confirm, and none of them should enter the citation whitelist unverified.*
