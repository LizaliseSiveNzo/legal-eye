# Legal-Eye ⚖️

An AI legal document summarizer: drop in a contract, lease, or NDA and get back a structured, readable summary of the parties, obligations, critical clauses, and risks.

## Features

- **Three formats** — PDF, DOCX, and TXT (including text inside DOCX tables)
- **Scanned PDFs** — automatically detected and read with OCR, pages processed in parallel
- **Forensic analysis** — verifies the arithmetic, tests attachments against the covering document, and reports red flags with severity up to Critical
- **Structured output** — always the same headings, in the same order, as Markdown
- **Two interfaces** — a command-line tool and a drag-and-drop web app, sharing one core
- **Cost-controlled** — input truncated at 50,000 characters, output capped at 2,000 tokens, and a cache-friendly fixed system prompt
- **Honest errors** — scanned PDFs, password-protected files, bad API keys, and rate limits all produce a plain-English message instead of a traceback

## How the analysis works

The analysis runs in two passes, because the hardest findings should not depend
on whether a language model felt like doing the sum.

1. **Extract** — the model reads the document and its attachments and records
   what they say as structured JSON. No judgement at this stage.
2. **Verify** — `backend/forensics.py` checks those facts against each other in
   plain Python: does the payment schedule reconcile to the stated total, what
   is the derived unit price, how much of a graded parcel sits in its
   lowest-value categories, do quantities agree across the bundle, is an
   official act dated to a weekend, does one trading name appear under two legal
   forms, is a wire demanded with no account details in the document.
   It also computes the document's **risk score out of 10** — the worst finding
   sets a floor, the rest add on top — so the rating is reproducible rather
   than a matter of opinion.
3. **Analyse** — the model writes the review with those verified findings in
   hand, and is instructed not to contradict them.

Everything in step 2 is arithmetic, calendar maths or string comparison, so it
is reproducible and auditable. `tests/test_forensics.py` runs it against a real
document with no API calls and no network.

### Reading the output

The report leads with the material a reader triaging a stack of documents needs
first: a **risk rating out of 10**, a **Read This First** list of the four to
eight things that actually matter, and — where the document raises statutory,
licensing, sanctions, AML or export-control issues — a **Legal & Regulatory
Exposure** section directly beneath, so a lawyer sees their part without
hunting for it.

The few things that must not be missed are rendered in red: the rating when it
is 8 or above, each Critical finding, and each instruction not to do something.
Red is capped at eight passages per document, because colour stops working as
emphasis the moment it is everywhere. It is emitted as an inline HTML span, so
it shows in the web app and in any HTML-capable Markdown viewer; a downloaded
`.md` opened in a plain text editor will show the tag instead of the colour.

The analysis is deliberately not soft. Where a document puts the reader's money
beyond recovery, the output is allowed to say so directly, and severity runs to
**Critical**. It assesses documents, never people: it will not assert that any
named person or company has done anything wrong.

Two passes means roughly twice the API cost per document. `estimate_cost()`
accounts for both.

## Quickstart

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your API key
copy .env.example .env          # Windows  (macOS/Linux: cp .env.example .env)
# then open .env and paste your real DeepSeek key
```

**Command line:**

```bash
python -m backend.app "path\to\contract.pdf"
python -m backend.app "path\to\contract.pdf" -o summary.md
```

**Web app:**

```bash
streamlit run frontend/streamlit_app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501).

## Scanned documents

Signed contracts are usually scans — a photograph of each page, with no text inside the file. Legal-Eye detects these and reads them with OCR automatically. Nothing is uploaded anywhere: the text recognition runs on your own machine.

This needs the Tesseract program installed once, in addition to `pip install -r requirements.txt`:

- **Windows:** download the installer from https://github.com/UB-Mannheim/tesseract/wiki, run it, and tick **"Add Tesseract to PATH"** during setup. Restart your terminal afterwards.
- **macOS:** `brew install tesseract`
- **Linux:** `sudo apt install tesseract-ocr`

Without Tesseract, scanned PDFs produce a message explaining how to install it; everything else keeps working.

Expect roughly 5–10 seconds per scanned page. Text-based PDFs are unaffected and stay instant. A banner appears above any summary that came from OCR, because character recognition can misread names, figures, and dates.

To OCR a language other than English, install that language pack and set `OCR_LANGUAGE` in `.env` (for example `OCR_LANGUAGE=afr` for Afrikaans).

## Output structure

Every summary contains these sections, in this order:

| Section | What it covers |
|---|---|
| Executive Summary | Document type, purpose, key commercial terms |
| Parties | Every party and its role; flags undefined parties |
| Obligations | Who must do what, by when, for how much |
| Critical Clauses | Termination, liability, indemnity, IP, renewal, governing law… |
| Risk Assessment | A table of Risk / Severity / Reason |
| Recommendations | 3–6 concrete actions to take before signing |
| Legal Disclaimer | Fixed, verbatim disclaimer |

## Project structure

```
legal-eye/
├── backend/
│   ├── __init__.py
│   ├── config.py           Settings and API key, loaded from .env
│   ├── parser.py           Text extraction from PDF / DOCX / TXT
│   ├── summarizer.py       Legal system prompt + DeepSeek API call
│   └── app.py              Command-line entry point
├── frontend/
│   └── streamlit_app.py    Drag-and-drop web interface
├── tests/
│   └── test_smoke.py       Offline tests (mocked API — spends no credit)
├── requirements.txt
├── .env.example
└── README.md
```

## Cost

A typical document runs 5,000–50,000 characters, which costs roughly **$0.01–$0.03** per summary on `deepseek-chat`. A $10 credit covers several hundred documents. The web app shows a live estimate under each result.

The estimate is deliberately conservative: it assumes a full cache miss on input and a maxed-out response, so real costs come in at or below the number shown.

## Testing

The test suite runs entirely offline with a mocked API client, so it never spends credit:

```bash
pip install pytest
python -m pytest tests/ -v
```

## Disclaimer

Legal-Eye produces AI-generated summaries for informational purposes only. They are **not legal advice**, may contain errors or omissions, and must not be relied on for legal decisions. Always read the original document and consult a qualified attorney about your specific situation.

If you plan to charge clients for summaries produced by this tool, check the rules on unauthorized practice of law and professional liability in your jurisdiction first — a disclaimer in the output is not by itself a defence.
