# LEGAL-EYE — Master Plan & Architecture
### AI Legal Document Summarizer — Chief Architect Deliverable

> **How to use this document:** Read Sections A–E first to understand the system, then copy each prompt in **Section F** one at a time and paste it into Claude to generate the actual code files. Paste each prompt in a **new chat**, in the order given, and save each generated file to the path shown.

---

# SECTION A: Project Overview & High-Level Architecture

## A.1 What LEGAL-EYE Does
LEGAL-EYE takes a legal document (PDF, DOCX, or TXT), extracts its text, sends it to the **DeepSeek API** together with a specialized legal-analysis system prompt, and returns a **highly structured Markdown summary** covering:

- Executive Summary
- Parties
- Obligations
- Critical Clauses
- Risk Assessment
- Recommendations
- Legal Disclaimer

The business model is **API arbitrage**: DeepSeek is roughly 90% cheaper than Claude/GPT, so summarizing a document costs under $0.10 in API fees while clients can be charged $30–$100 per document.

## A.2 System Flow

```
┌─────────────┐   upload    ┌──────────────────┐   extract text   ┌──────────────────┐
│  User       │ ──────────► │  frontend/       │ ───────────────► │  backend/        │
│  (browser)  │             │  streamlit_app   │                  │  parser.py       │
└─────────────┘             └──────────────────┘                  └────────┬─────────┘
                                                                           │ raw text
                                                                           ▼
┌─────────────┐   Markdown  ┌──────────────────┐   truncated text   ┌──────────────────┐
│  User sees  │ ◄────────── │  backend/        │ ◄───────────────── │  backend/        │
│  formatted  │             │  summarizer.py   │                    │  summarizer.py   │
│  summary    │             │  (render result) │                    │  (build prompt)  │
└─────────────┘             └──────────────────┘                    └────────┬─────────┘
                                                                             │ API call
                                                                             ▼
                                                                   ┌──────────────────┐
                                                                   │  DeepSeek API    │
                                                                   │  (OpenAI SDK)    │
                                                                   │  base_url:       │
                                                                   │  api.deepseek.com│
                                                                   └──────────────────┘
```

**Simplified:** User uploads PDF → `parser.py` extracts text → `summarizer.py` truncates text, injects the legal system prompt, calls DeepSeek → structured Markdown returned → Streamlit renders it.

## A.3 Tech Stack

| Layer      | Technology                                    | Why |
|------------|-----------------------------------------------|-----|
| Language   | Python 3.10+                                  | Simple, ubiquitous, great SDK support |
| AI API     | DeepSeek (via `openai` Python SDK)            | OpenAI-compatible format, ~90% cheaper |
| PDF parsing| `pypdf`                                       | Lightweight, pure Python, reliable text extraction |
| DOCX parse | `python-docx`                                 | Standard library for Word documents |
| Web UI     | Streamlit                                     | Fastest path from script to web app; drag-and-drop upload built in |
| Config     | `python-dotenv` + `.env`                      | Keeps the API key out of source code |
| Payments (Phase 3) | Stripe                              | Standard for micro-SaaS billing |

## A.4 Key Architectural Decisions

1. **Single backend module for all logic.** The core flow (`parse → summarize`) lives in `backend/` with no framework dependency, so the same code powers both the Phase 1 CLI and the Phase 2 web UI.
2. **Markdown as the output format.** Markdown renders natively in Streamlit (`st.markdown`), in terminals (raw text), and later in any SaaS frontend.
3. **OpenAI SDK, not a custom HTTP client.** DeepSeek's API is OpenAI-compatible; using the official `openai` SDK gives us retries, typing, and a familiar `chat.completions.create()` interface.
4. **Cost-first engineering.** Truncate input to 50,000 characters, cap output tokens, and keep the system prompt byte-for-byte identical on every call so DeepSeek's automatic prompt caching maximizes cache hits (cache hits are billed at a fraction of the miss price).
5. **No code in this document.** This plan deliberately contains zero runnable code — Section F contains the prompts that will make Claude generate it.

---

# SECTION B: Folder & File Structure

```
legal-eye/
├── backend/                          # All core logic (framework-agnostic)
│   ├── __init__.py                   # Marks backend as a Python package (empty file)
│   ├── parser.py                     # Extracts text from PDF, DOCX, TXT files
│   ├── summarizer.py                 # Core logic: legal system prompt + DeepSeek API call
│   ├── config.py                     # Loads API key and settings from .env; central constants
│   └── app.py                        # Entry point: ties parser + summarizer into one pipeline
│                                     # (Phase 1: CLI. Phase 2: importable by Streamlit)
├── frontend/
│   └── streamlit_app.py              # Drag-and-drop web interface (Phase 2)
├── requirements.txt                  # All Python dependencies with minimum versions
├── .env.example                      # Template for environment variables (copy to .env)
├── .env                              # Your real API key (NEVER commit this; gitignored)
├── .gitignore                        # Excludes .env, __pycache__, venv, etc.
├── README.md                         # Setup instructions, usage, architecture overview
└── LEGAL-EYE_Master_Plan.md          # This document
```

**Notes on the structure:**
- `app.py` doubles as the Phase 1 deliverable: run `python backend/app.py path/to/contract.pdf` and the summary prints to the terminal. Phase 2 only adds the Streamlit layer on top — nothing in the core changes.
- `summarizer.py` is the "money file": it contains the hardcoded legal system prompt (Section D) and the DeepSeek call.
- `config.py` is a single source of truth so the CLI and the web app never disagree on settings.

---

# SECTION C: Step-by-Step Development Roadmap

### Phase 1 (Day 1 — "Profit in < 1 day")
**CLI Script.** A command-line Python tool:
- User runs: `python backend/app.py "C:\path\to\contract.pdf"`
- `parser.py` extracts the text, `summarizer.py` calls DeepSeek, and the formatted Markdown summary **prints to the terminal**.
- Deliverables: `backend/` package, `requirements.txt`, `.env` setup.
- **Definition of done:** summarizing a real PDF from the terminal works end-to-end.

### Phase 2 (Day 2 — "Make it sellable")
**Web UI with Streamlit.**
- Non-technical clients visit a local web page, drag-and-drop a file, click **"Summarize Document"**, and see the formatted Markdown summary.
- Add a "Download Summary (.md)" button.
- Deliverable: `frontend/streamlit_app.py`.
- **Definition of done:** a non-technical person can summarize a document without touching a terminal.

### Phase 3 (Future — "Turn it into a Micro-SaaS")
**Stripe Payments + User Accounts.**
- Deploy the Streamlit app to Streamlit Community Cloud (free hosting to start).
- Add Stripe Checkout ($30–$100 per document, or monthly subscription).
- Add per-user API-key usage tracking and daily usage caps.
- **Definition of done:** a stranger pays money and receives a summary automatically.
- *(Out of scope for now — revisit only after Phase 2 makes money or validates demand.)*

---

# SECTION D: The "Secret Sauce" — Legal System Prompt

This is the **exact** system prompt to hardcode in `summarizer.py` as a module-level constant named `LEGAL_SYSTEM_PROMPT`. It must be pasted **verbatim** — every character identical on every API call — to maximize DeepSeek prompt-cache hits (cheaper tokens).

```
You are Legal-Eye, an AI legal document summarization assistant.

Your task: analyze the legal document provided by the user and produce a
highly structured, objective, and neutral summary in Markdown format.

STRICT OUTPUT STRUCTURE — use these headings in this exact order:

# Executive Summary
- 3 to 5 sentences stating: what kind of document this is, its core purpose,
  the key commercial terms, and the most important thing the reader must know.

## Parties
- List every party with its role (e.g., Licensor, Tenant, Employer).
- Note any party that is undefined, missing, or ambiguously named.

## Obligations
- Bullet list of each party's main obligations, duties, and payment terms.
- State who must do what, when, and for how much money.

## Critical Clauses
- Bullet list of the clauses that most affect the reader: term and termination,
  payment, liability caps, indemnities, confidentiality, IP ownership,
  non-compete, automatic renewal, assignment, governing law, dispute resolution.
- For each clause, cite the clause number/section if visible in the text.

## Risk Assessment
- A table with columns: Risk | Severity (High/Medium/Low) | Reason.
- Flag one-sided terms, missing definitions, unlimited liability, vague
  obligations, unfavorable jurisdictions, and hidden costs.

## Recommendations
- 3 to 6 concrete, practical suggestions for the reader (e.g., "negotiate the
  liability cap", "request a definition of Confidential Information").
- Phrase them as actions, not legal advice.

## Legal Disclaimer
- End with the disclaimer text below, verbatim.

LEGAL DISCLAIMER (must appear verbatim):
"This summary was generated by an automated AI tool for informational purposes
only and does not constitute legal advice. It may contain errors, omissions,
or misinterpretations of the source document. You should not rely on this
summary for making legal decisions and should consult a qualified attorney
for advice on your specific situation. Always review the original document."

RULES:
1. Be objective and neutral. Do not take sides, do not editorialize, and do
   not give legal advice. State only what the document says and what a
   reasonable reader should verify or negotiate.
2. Base every statement ONLY on the text provided. If information is missing,
   say "Not stated in the document" — never invent or assume.
3. If the input is not a legal document or is unreadable, say so plainly and
   summarize what you can.
4. Output ONLY the structured Markdown above. No preamble, no closing remarks
   beyond the disclaimer.
```

**Why this prompt works:** fixed heading order = predictable output; the verbatim disclaimer is a liability shield; "objective and neutral" + "never invent" prevents hallucinated legal conclusions; and keeping it byte-identical on every call earns DeepSeek cache discounts.

---

# SECTION E: Technical Specifications for Each File

## E.1 `backend/parser.py`

**Imports required:**
```python
from pathlib import Path
from pypdf import PdfReader
from docx import Document
```

**Function signatures:**
```python
def extract_text(file_path: str) -> str:
    """Extract raw text from a .pdf, .docx, or .txt file. Returns the text as a single string."""
def _extract_pdf(path: Path) -> str:
    """Internal: extract text from all pages of a PDF."""
def _extract_docx(path: Path) -> str:
    """Internal: extract text from all paragraphs of a DOCX."""
def _extract_txt(path: Path) -> str:
    """Internal: read a plain-text file (utf-8 with fallback to latin-1)."""
```

**Logic flow (pseudocode):**
```
extract_text(file_path):
    1. Convert to Path; check the file exists → raise FileNotFoundError otherwise
    2. Switch on lowercase suffix:
       .pdf  → _extract_pdf
       .docx → _extract_docx
       .txt  → _extract_txt
       else  → raise ValueError("Unsupported file type: ...")
    3. Strip excessive whitespace; join pages/paragraphs with "\n\n"
    4. If result is empty or < 10 characters → raise ValueError("No readable text found")
    5. Return text
```

**Error handling:** encrypted/scanned PDFs and corrupt files must raise a clear `ValueError` (never crash silently); scanned (image-only) PDFs produce empty text and are reported with a friendly message like *"No extractable text — the PDF appears to be scanned/images."*

## E.2 `backend/summarizer.py`

**Imports required:**
```python
import os
from openai import OpenAI, AuthenticationError, RateLimitError, APIConnectionError
from backend.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, MAX_INPUT_CHARS, MAX_OUTPUT_TOKENS
```

**Function signatures:**
```python
def summarize_legal_document(text: str) -> str:
    """Send text to DeepSeek with the legal system prompt; return the Markdown summary."""
def _truncate_text(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    """Cut text to max_chars, keeping whole words, and append a truncation notice."""
```

**Logic flow (pseudocode):**
```
summarize_legal_document(text):
    1. text = _truncate_text(text)                # hard cap at 50,000 chars
    2. client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    3. response = client.chat.completions.create(
           model=DEEPSEEK_MODEL,                 # "deepseek-chat"
           messages=[
               {"role": "system", "content": LEGAL_SYSTEM_PROMPT},   # Section D, verbatim
               {"role": "user",   "content": text},
           ],
           temperature=0.2,                       # low = consistent, professional output
           max_tokens=MAX_OUTPUT_TOKENS,          # 2,000 (cap cost)
       )
    4. summary = response.choices[0].message.content.strip()
    5. If summary empty → raise RuntimeError("Empty response from API")
    6. Return summary

Error handling:
    AuthenticationError → "Invalid API key. Check your .env file." (re-raise with clear message)
    RateLimitError      → retry up to 3 times with 2/5/10s backoff, then fail clearly
    APIConnectionError  → "Cannot reach DeepSeek. Check your internet connection."
```

**Configuration (via `config.py`):**
- `DEEPSEEK_API_KEY` — read from `.env` (never hardcode)
- `DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"` (OpenAI-SDK-compatible endpoint)
- `DEEPSEEK_MODEL = "deepseek-chat"` (the cheap V3 model; do **not** use `deepseek-reasoner` — it costs more and is unnecessary for summarization)
- `MAX_INPUT_CHARS = 50_000`, `MAX_OUTPUT_TOKENS = 2_000`, `TEMPERATURE = 0.2`

**Cost-efficiency notes to encode:** identical system prompt every call (cache hits), hard input truncation, capped output tokens, and the system prompt instructs *only* structured output (no wasted tokens).

## E.3 `backend/config.py`

**Imports:** `os`, `from dotenv import load_dotenv`

**Logic flow:**
```
1. load_dotenv()                        # loads .env from project root
2. DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
3. If key missing → raise RuntimeError("DEEPSEEK_API_KEY not set. Copy .env.example to .env")
4. Export all constants (base URL, model, truncation and token limits) as module-level UPPER_CASE names
```

## E.4 `backend/app.py` (Phase 1 CLI entry point)

**Imports:** `sys`, `argparse`, `backend.parser.extract_text`, `backend.summarizer.summarize_legal_document`

**Logic flow:**
```
1. argparse: positional arg "file_path", optional --no-truncate flag
2. text = extract_text(file_path)
3. print("Analyzing document...") to stderr
4. summary = summarize_legal_document(text)
5. print(summary) to stdout
6. Catch ValueError/FileNotFoundError → print friendly error, exit code 1
```

**Run with:** `python -m backend.app "C:\path\to\contract.pdf"` (or `python backend/app.py ...`).

## E.5 `frontend/streamlit_app.py` (Phase 2)

**Imports:** `streamlit as st`, `backend.parser.extract_text`, `backend.summarizer.summarize_legal_document`, `tempfile`

**Logic flow:**
```
1. st.set_page_config(page_title="Legal-Eye", layout="wide")
2. st.title + one-line tagline + warning note ("AI-generated, not legal advice")
3. uploaded_file = st.file_uploader(..., type=["pdf", "docx", "txt"])
4. On "Summarize Document" button:
     a. Save upload to a temp file (parser needs a path)
     b. st.spinner("Analyzing document…")
     c. text = extract_text(temp_path) ; summary = summarize_legal_document(text)
     d. st.markdown(summary)                     # renders the structured output nicely
     e. st.download_button("Download Summary (.md)", summary)
     f. Show token/cost estimate line (e.g., "≈ 6k input tokens, ~$0.01")
5. Catch errors → st.error(friendly message)
```

## E.6 `requirements.txt`

```
openai>=1.30.0
streamlit>=1.30.0
pypdf>=4.0.0
python-docx>=1.1.0
python-dotenv>=1.0.0
```

## E.7 `.env.example` / `.env`

```
# DeepSeek API key — get one at https://platform.deepseek.com
DEEPSEEK_API_KEY=sk-your-key-here

# DeepSeek OpenAI-compatible endpoint (do not change)
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# Model: deepseek-chat is the cost-efficient choice
DEEPSEEK_MODEL=deepseek-chat
```

---

# SECTION F: THE HAND-OFF — Prompts for Claude (CRITICAL)

> **Instructions:** Open a **new chat with Claude** for each prompt. Copy the entire fenced prompt (including the `=====` delimiters), paste it, and save the output to the file path stated. Do them in order: 1 → 2 → 3 → 4 → 5. After all files exist, run the Phase 1 smoke test at the end.

---

## Prompt for Claude #1: `backend/parser.py`

```
===== BEGIN PROMPT =====
You are a senior Python engineer. Create ONE file: backend/parser.py for a
project called "Legal-Eye" (an AI legal document summarizer).

CONTEXT: This module extracts raw text from legal documents so another module
can send the text to an AI API for summarization. It must be pure, framework-free
Python (no web framework, no network calls).

HARD REQUIREMENTS:
1. Support exactly three file types, chosen by extension: .pdf, .docx, .txt.
2. PDF: use pypdf (from pypdf import PdfReader). Iterate all pages; skip pages
   with no extractable text. Join pages with two newlines.
3. DOCX: use python-docx (from docx import Document). Join non-empty paragraphs
   with two newlines.
4. TXT: read with encoding="utf-8", fall back to encoding="latin-1" on
   UnicodeDecodeError.
5. Public API — exactly this function:
   def extract_text(file_path: str) -> str:
       """Extract raw text from a .pdf, .docx, or .txt file."""
   It must:
     - Convert file_path to pathlib.Path and raise FileNotFoundError with a clear
       message if the file does not exist.
     - Raise ValueError("Unsupported file type: .xyz. Supported: .pdf, .docx, .txt")
       for any other extension.
     - Collapse 3+ consecutive blank lines into one; strip leading/trailing
       whitespace.
     - Raise ValueError with the message "No readable text found — the document
       may be scanned (image-only) or empty." if the extracted text is empty or
       shorter than 10 characters.
6. Internal helpers: _extract_pdf(path), _extract_docx(path), _extract_txt(path),
   each returning str.
7. Wrap pypdf/python-docx exceptions (corrupt files, encrypted PDFs) into a
   ValueError with a friendly, specific message. Never let a raw traceback escape.
8. Style: type hints on all functions, one-line docstrings, no comments that
   narrate the obvious, no external dependencies beyond pypdf and python-docx.

OUTPUT: Only the complete, runnable contents of backend/parser.py in one code
block. Do not include explanations, installation instructions, or extra files.
===== END PROMPT =====
```

---

## Prompt for Claude #2: `backend/summarizer.py` (THE MONEY FILE)

```
===== BEGIN PROMPT =====
You are a senior Python engineer specializing in LLM API integrations. Create
ONE file: backend/summarizer.py for a project called "Legal-Eye".

CONTEXT: This module sends extracted legal-document text to the DeepSeek API
(via the OpenAI-compatible SDK) and returns a structured Markdown summary. It
contains a hardcoded legal system prompt and all API-call logic.

HARD REQUIREMENTS:
1. Imports:
   import os
   from openai import OpenAI, AuthenticationError, RateLimitError, APIConnectionError
   from backend.config import (DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
                               MAX_INPUT_CHARS, MAX_OUTPUT_TOKENS, TEMPERATURE)
2. Define a module-level constant LEGAL_SYSTEM_PROMPT containing EXACTLY the
   following text, character-for-character (preserve every line break), as a
   triple-quoted string:

   [PASTE THE ENTIRE SECTION D SYSTEM PROMPT HERE, INCLUDING THE DISCLAIMER]

3. Public API — exactly this function:
   def summarize_legal_document(text: str) -> str:
       """Send text to DeepSeek with the legal system prompt; return the Markdown summary."""
4. Logic inside summarize_legal_document:
   a. Truncate: if len(text) > MAX_INPUT_CHARS, cut to MAX_INPUT_CHARS at a word
      boundary and append "\n\n[Document truncated to 50,000 characters to control
      API cost.]"
   b. Instantiate the client ONCE at module level (lazy): client = OpenAI(
      api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL). Use a module-level
      _client = None + _get_client() helper if you prefer; either way, do not
      recreate the client on every call.
   c. Call:
      response = client.chat.completions.create(
          model=DEEPSEEK_MODEL,
          messages=[
              {"role": "system", "content": LEGAL_SYSTEM_PROMPT},
              {"role": "user", "content": text},
          ],
          temperature=TEMPERATURE,
          max_tokens=MAX_OUTPUT_TOKENS,
      )
   d. Extract response.choices[0].message.content, strip it, and if empty raise
      RuntimeError("DeepSeek returned an empty response.")
5. Error handling — catch and re-raise as RuntimeError with these EXACT friendly
   messages:
     AuthenticationError -> "Invalid DEEPSEEK_API_KEY. Check your .env file."
     RateLimitError      -> retry up to 3 times with sleep(2), sleep(5), sleep(10)
                            between attempts; if still failing, raise RuntimeError(
                            "DeepSeek rate limit exceeded after 3 retries. Try again later.")
     APIConnectionError  -> "Cannot reach DeepSeek API. Check your internet connection."
6. Add a helper:
   def estimate_cost(input_chars: int) -> float:
       """Rough cost estimate in USD (deepseek-chat: ~$0.27/M input cache-miss,
       ~$0.07/M cached, ~$1.10/M output). Return a conservative upper bound."""
   Keep the math conservative and clearly commented as an estimate.
7. Style: type hints everywhere, one-line docstrings, constants imported from
   backend.config only (no magic numbers), no comments narrating the obvious.

OUTPUT: Only the complete, runnable contents of backend/summarizer.py in one
code block. Do not include explanations or extra files.
===== END PROMPT =====
```

> **⚠️ Before pasting:** the prompt contains the marker `[PASTE THE ENTIRE SECTION D SYSTEM PROMPT HERE...]`. Replace that marker with the full system prompt from **Section D** of this document (including the verbatim disclaimer), keeping it inside the triple quotes.

---

## Prompt for Claude #3: `backend/config.py`

```
===== BEGIN PROMPT =====
You are a senior Python engineer. Create ONE file: backend/config.py for the
"Legal-Eye" project (an AI legal document summarizer using the DeepSeek API).

HARD REQUIREMENTS:
1. Imports: import os; from dotenv import load_dotenv
2. Call load_dotenv() at module level so a .env file in the project root is loaded.
3. Define these module-level constants:
   DEEPSEEK_API_KEY  = os.getenv("DEEPSEEK_API_KEY")
   DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
   DEEPSEEK_MODEL    = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
   MAX_INPUT_CHARS   = 50_000
   MAX_OUTPUT_TOKENS = 2_000
   TEMPERATURE       = 0.2
4. Immediately after loading, validate: if DEEPSEEK_API_KEY is None or empty, raise
   RuntimeError("DEEPSEEK_API_KEY is not set. Copy .env.example to .env and add
   your DeepSeek API key.")
5. Style: type hints where meaningful, one-line docstrings, no extra logic.

OUTPUT: Only the complete, runnable contents of backend/config.py in one code
block. Do not include explanations or extra files.
===== END PROMPT =====
```

---

## Prompt for Claude #4: `backend/app.py` (Phase 1 CLI)

```
===== BEGIN PROMPT =====
You are a senior Python engineer. Create ONE file: backend/app.py for the
"Legal-Eye" project. This is the Phase 1 command-line entry point.

CONTEXT: Legal-Eye summarizes legal documents. Two sibling modules already exist:
  - backend/parser.py      with:  def extract_text(file_path: str) -> str
  - backend/summarizer.py  with:  def summarize_legal_document(text: str) -> str
Both raise ValueError with friendly messages on bad input.

HARD REQUIREMENTS:
1. Use argparse. Positional argument: file_path (the document to summarize).
   Optional flag: --max-chars N (default 50000) is NOT needed — skip it.
   Keep the interface minimal: exactly one positional argument.
2. Flow:
   a. text = extract_text(args.file_path)
   b. print("Analyzing document with DeepSeek...", file=sys.stderr)  (progress on
      stderr so stdout stays clean for piping)
   c. summary = summarize_legal_document(text)
   d. print(summary)
3. Error handling: catch FileNotFoundError, ValueError, and RuntimeError; print the
   message to stderr as "Error: <message>" and exit with code 1.
4. Include an `if __name__ == "__main__":` guard. Also make the script runnable as
   `python -m backend.app` by putting the argparse logic in a main() function called
   from both the `__main__` guard.
5. Style: type hints, one-line docstrings, no extra features, no colors, no logging
   framework.

OUTPUT: Only the complete, runnable contents of backend/app.py in one code block.
Do not include explanations or extra files.
===== END PROMPT =====
```

---

## Prompt for Claude #5: `frontend/streamlit_app.py` (Phase 2 Web UI)

```
===== BEGIN PROMPT =====
You are a senior Python engineer who specializes in Streamlit. Create ONE file:
frontend/streamlit_app.py for the "Legal-Eye" project (an AI legal document
summarizer).

CONTEXT: Two sibling modules already exist and are importable as:
  from backend.parser import extract_text            # (file_path: str) -> str
  from backend.summarizer import summarize_legal_document, estimate_cost
  # summarize_legal_document(text: str) -> str        # returns Markdown summary
  # estimate_cost(input_chars: int) -> float          # USD estimate
Both raise ValueError / RuntimeError with friendly messages on failure.

HARD REQUIREMENTS — build a clean, minimal, professional UI:
1. st.set_page_config(page_title="Legal-Eye — AI Legal Document Summarizer",
   page_icon="⚖️", layout="wide")
2. Header: title "Legal-Eye ⚖️", subtitle "Upload a legal document and get an
   instant AI summary. Powered by DeepSeek."
3. A small caption/warning: "⚠️ AI-generated summaries are for informational
   purposes only and do not constitute legal advice."
4. File uploader: st.file_uploader("Upload a document", type=["pdf", "docx", "txt"])
5. A primary button "Summarize Document" (disabled when no file is uploaded).
6. When clicked:
   a. Write the uploaded file to a NamedTemporaryFile (suffix matching the original
      filename) using tempfile; the parser needs a real path.
   b. Show st.spinner("Analyzing document with DeepSeek…") around the work.
   c. text = extract_text(temp_path); summary = summarize_legal_document(text)
   d. st.markdown(summary)  — render the structured result beautifully
   e. st.download_button("⬇️ Download Summary (.md)", data=summary,
      file_name="summary.md", mime="text/markdown")
   f. Show a subtle info line: f"📊 Input: ~{len(text):,} characters
      (≈ ${estimate_cost(len(text)):.3f} estimated API cost)."
7. Error handling: catch ValueError and RuntimeError and show st.error(message).
   Never show a raw traceback.
8. Empty state: when no file is uploaded, show a short 3-bullet "How it works" section.
9. Style: clean spacing, use st.columns only if it genuinely helps, no emojis
   beyond the ones specified, no custom CSS, no session state beyond what's needed
   to avoid re-running on every widget interaction.

OUTPUT: Only the complete, runnable contents of frontend/streamlit_app.py in one
code block. Do not include explanations or extra files.
===== END PROMPT =====
```

---

## Prompt for Claude #6: `requirements.txt`, `.env.example`, `.gitignore`, `README.md`

```
===== BEGIN PROMPT =====
You are a senior DevOps-minded Python engineer. Create FOUR small files for the
"Legal-Eye" project (an AI legal document summarizer using DeepSeek, Streamlit,
pypdf, python-docx, and python-dotenv).

FILE 1 — requirements.txt (exactly these lines, nothing else):
openai>=1.30.0
streamlit>=1.30.0
pypdf>=4.0.0
python-docx>=1.1.0
python-dotenv>=1.0.0

FILE 2 — .env.example (exactly this content):
# DeepSeek API key — get one at https://platform.deepseek.com
DEEPSEEK_API_KEY=sk-your-key-here

# DeepSeek OpenAI-compatible endpoint (do not change)
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# Model: deepseek-chat is the cost-efficient choice
DEEPSEEK_MODEL=deepseek-chat

FILE 3 — .gitignore (cover Python + this project):
__pycache__/
*.pyc
.env
.venv/
venv/
.streamlit/secrets.toml
.DS_Store

FILE 4 — README.md (concise but complete, in Markdown) containing:
  - Project title "Legal-Eye ⚖️" and one-sentence description
  - Features list (PDF/DOCX/TXT support, structured Markdown summary, CLI + Web UI)
  - Quickstart: python -m venv .venv → activate → pip install -r requirements.txt →
    copy .env.example to .env and paste a DeepSeek API key →
    CLI: python -m backend.app path/to/contract.pdf →
    Web: streamlit run frontend/streamlit_app.py
  - Output structure (the headings the summary contains)
  - Cost note: typical document ≈ 5,000–50,000 chars → roughly $0.01–$0.10 per
    document on deepseek-chat
  - Disclaimer paragraph: AI-generated, not legal advice, consult an attorney

OUTPUT: All four files, each in its own code block, labeled with the exact filename.
Do not include explanations beyond the files.
===== END PROMPT =====
```

---

## Phase 1 Smoke Test (after all files are generated)

Run these commands in the `legal-eye` folder:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # then paste your real DeepSeek API key into .env
python -m backend.app "path\to\a\test\contract.pdf"
```

**Expected result:** the structured Markdown summary prints in the terminal, ending with the legal disclaimer. If it works, Phase 1 is done — proceed to Phase 2 by generating `frontend/streamlit_app.py` (Prompt #5) and running `streamlit run frontend/streamlit_app.py`.

---

# APPENDIX: Cost & Safety Budget

- **Input budget:** max 50,000 chars ≈ 12,500–16,000 tokens ≈ $0.004–$0.02 per document on `deepseek-chat`.
- **Output budget:** capped at 2,000 tokens ≈ $0.002.
- **Worst case per document: ≈ $0.03.** The $10 credit funds **300+ documents** at full length — hundreds more for typical contracts.
- **Safety rails already designed in:** truncation, token caps, retry/backoff, cache-friendly identical system prompt, and the verbatim legal disclaimer in every output.
