"""Offline tests for Legal-Eye. Uses a mocked DeepSeek client — spends no API credit."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import summarizer  # noqa: E402
from backend.ocr import ocr_available  # noqa: E402
from backend.parser import extract_document, extract_text  # noqa: E402
from backend.summarizer import (  # noqa: E402
    LEGAL_SYSTEM_PROMPT,
    _truncate_text,
    estimate_cost,
    summarize_legal_document,
)

SAMPLE = (
    "SERVICES AGREEMENT\n\nThis Agreement is made between Acme Corp (the "
    "Supplier) and Beta Ltd (the Client). The Supplier shall deliver monthly "
    "reports. The Client shall pay R15,000 per month within 30 days of invoice."
)


@pytest.fixture
def sample_dir(tmp_path: Path) -> Path:
    """Create one TXT, one DOCX, and one PDF containing the sample agreement."""
    (tmp_path / "agreement.txt").write_text(SAMPLE, encoding="utf-8")

    from docx import Document

    document = Document()
    for block in SAMPLE.split("\n\n"):
        document.add_paragraph(block)
    document.save(str(tmp_path / "agreement.docx"))

    from reportlab.lib.pagesizes import LETTER
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(str(tmp_path / "agreement.pdf"), pagesize=LETTER)
    y = 720
    for line in SAMPLE.replace("\n\n", "\n").split("\n"):
        pdf.drawString(72, y, line[:95])
        y -= 18
    pdf.save()

    return tmp_path


@pytest.mark.parametrize("name", ["agreement.txt", "agreement.docx", "agreement.pdf"])
def test_extracts_text_from_every_supported_format(sample_dir: Path, name: str) -> None:
    text = extract_text(str(sample_dir / name))
    assert "SERVICES AGREEMENT" in text
    assert "Acme Corp" in text
    assert "Beta Ltd" in text


def test_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract_text(str(tmp_path / "nope.pdf"))


def test_unsupported_extension_is_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "notes.rtf"
    bad.write_text("hello world, this is long enough", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text(str(bad))


def test_legacy_doc_gets_a_helpful_message(tmp_path: Path) -> None:
    bad = tmp_path / "old.doc"
    bad.write_text("legacy word document content here", encoding="utf-8")
    with pytest.raises(ValueError, match="save"):
        extract_text(str(bad))


def test_empty_file_reports_no_readable_text(tmp_path: Path) -> None:
    empty = tmp_path / "blank.txt"
    empty.write_text("   \n\n  ", encoding="utf-8")
    with pytest.raises(ValueError, match="No readable text"):
        extract_text(str(empty))


def test_latin1_fallback(tmp_path: Path) -> None:
    path = tmp_path / "latin.txt"
    path.write_bytes("Contrat de société: clause pénale résiliée".encode("latin-1"))
    assert "Contrat" in extract_text(str(path))


def test_truncation_adds_notice_and_respects_limit() -> None:
    long_text = "word " * 30_000
    result = _truncate_text(long_text, max_chars=1_000)
    assert "[Document truncated to 1,000 characters" in result
    assert len(result) < 1_200


def test_short_text_is_not_truncated() -> None:
    assert _truncate_text(SAMPLE) == SAMPLE


def test_cost_estimate_is_small_and_positive() -> None:
    assert 0 < estimate_cost(len(SAMPLE)) < 0.01
    assert estimate_cost(50_000) < 0.05
    assert estimate_cost(500_000) == estimate_cost(50_000)  # capped by truncation


def test_system_prompt_contains_required_sections() -> None:
    for heading in [
        "# Executive Summary",
        "## At a Glance",
        "## Parties",
        "## Obligations",
        "## Critical Clauses",
        "## Missing or Unaddressed",
        "## Risk Assessment",
        "## Recommendations",
        "## Legal Disclaimer",
    ]:
        assert heading in LEGAL_SYSTEM_PROMPT
    assert "does not constitute legal advice" in LEGAL_SYSTEM_PROMPT


def test_severity_definitions_are_explicit() -> None:
    """Severity must be defined, or the model rates everything Medium."""
    assert "Up to 12 rows" in LEGAL_SYSTEM_PROMPT
    assert "Do not cluster everything at Medium" in LEGAL_SYSTEM_PROMPT
    for level in ("Critical =", "High     =", "Medium   =", "Low      ="):
        assert level in LEGAL_SYSTEM_PROMPT


def test_priority_sections_lead_the_output() -> None:
    """A lawyer must see the rating, the summary bullets and any legal exposure first."""
    for heading in [
        "# Document Risk Rating: N/10",
        "## Read This First",
        "## Legal & Regulatory Exposure",
    ]:
        assert heading in LEGAL_SYSTEM_PROMPT
    # Order matters: these must precede the body of the analysis.
    assert LEGAL_SYSTEM_PROMPT.index("## Read This First") < LEGAL_SYSTEM_PROMPT.index(
        "# Executive Summary"
    )
    assert "never as an allegation" in LEGAL_SYSTEM_PROMPT


def test_red_text_is_bounded() -> None:
    """Colour only works as emphasis while it stays rare."""
    assert 'color:#c00000' in LEGAL_SYSTEM_PROMPT
    assert "Maximum 8 red passages" in LEGAL_SYSTEM_PROMPT
    assert "Nothing below High severity is ever red" in LEGAL_SYSTEM_PROMPT


def test_findings_cannot_be_silently_dropped() -> None:
    assert "MUST appear in your output" in LEGAL_SYSTEM_PROMPT
    assert "Rows MUST run Critical, then High, then Medium, then Low" in LEGAL_SYSTEM_PROMPT


def test_non_contract_documents_are_handled() -> None:
    assert "not a contract or agreement" in LEGAL_SYSTEM_PROMPT
    assert "Not applicable to this document type" in LEGAL_SYSTEM_PROMPT


def _mock_client(content: str) -> MagicMock:
    client = MagicMock()
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    client.chat.completions.create.return_value = response
    return client


def test_full_pipeline_with_mocked_api(sample_dir: Path) -> None:
    fake = _mock_client("# Executive Summary\nA services agreement.")
    with patch.object(summarizer, "_get_client", return_value=fake):
        text = extract_text(str(sample_dir / "agreement.docx"))
        summary = summarize_legal_document(text)

    assert summary.startswith("# Executive Summary")
    sent = fake.chat.completions.create.call_args.kwargs
    assert sent["messages"][0]["content"] == LEGAL_SYSTEM_PROMPT  # byte-identical
    assert sent["temperature"] == 0.2
    assert sent["max_tokens"] == 3_000


def test_empty_api_response_raises_runtime_error() -> None:
    fake = _mock_client("   ")
    with patch.object(summarizer, "_get_client", return_value=fake):
        with pytest.raises(RuntimeError, match="empty response"):
            summarize_legal_document(SAMPLE)


def test_blank_input_is_rejected_before_any_api_call() -> None:
    with pytest.raises(ValueError, match="empty"):
        summarize_legal_document("   ")


def test_auth_error_becomes_friendly_message() -> None:
    from openai import AuthenticationError

    fake = MagicMock()
    fake.chat.completions.create.side_effect = AuthenticationError(
        "bad key", response=MagicMock(status_code=401, headers={}), body=None
    )
    with patch.object(summarizer, "_get_client", return_value=fake):
        with pytest.raises(RuntimeError, match="Invalid API key"):
            summarize_legal_document(SAMPLE)


def test_rate_limit_retries_then_fails_clearly() -> None:
    from openai import RateLimitError

    fake = MagicMock()
    fake.chat.completions.create.side_effect = RateLimitError(
        "slow down", response=MagicMock(status_code=429, headers={}), body=None
    )
    with patch.object(summarizer, "_get_client", return_value=fake):
        with patch.object(summarizer.time, "sleep"):  # don't actually wait
            with pytest.raises(RuntimeError, match="AI service rate limit exceeded"):
                summarize_legal_document(SAMPLE)

    assert fake.chat.completions.create.call_count == 4  # 1 try + 3 retries


def test_rate_limit_recovers_on_retry() -> None:
    from openai import RateLimitError

    fake = _mock_client("# Executive Summary\nRecovered.")
    good = fake.chat.completions.create.return_value
    # The pipeline makes two API calls (extraction, then analysis); the first
    # is the one that gets rate-limited, so the side effect needs three entries:
    # raised error, retried success, then the second pass.
    fake.chat.completions.create.side_effect = [
        RateLimitError(
            "slow down", response=MagicMock(status_code=429, headers={}), body=None
        ),
        good,
        good,
    ]
    with patch.object(summarizer, "_get_client", return_value=fake):
        with patch.object(summarizer.time, "sleep"):
            assert summarize_legal_document(SAMPLE).startswith("# Executive Summary")


def test_connection_error_becomes_friendly_message() -> None:
    from openai import APIConnectionError

    fake = MagicMock()
    fake.chat.completions.create.side_effect = APIConnectionError(request=MagicMock())
    with patch.object(summarizer, "_get_client", return_value=fake):
        with pytest.raises(RuntimeError, match="Cannot reach the AI service"):
            summarize_legal_document(SAMPLE)


# --- Scanned PDF / OCR --------------------------------------------------------


@pytest.fixture
def scanned_pdf(tmp_path: Path) -> Path:
    """Build an image-only PDF: text rendered to a bitmap, no text layer at all."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (1700, 800), "white")
    draw = ImageDraw.Draw(image)
    lines = [
        "SERVICES AGREEMENT",
        "This Agreement is between Acme Corp and Beta Ltd.",
        "The Client shall pay 15000 per month within 30 days.",
    ]
    for i, line in enumerate(lines):
        draw.text((60, 80 + i * 90), line, fill="black")
    path = tmp_path / "scanned.pdf"
    image.save(str(path), "PDF", resolution=150.0)
    return path


def test_scanned_pdf_has_no_text_layer(scanned_pdf: Path) -> None:
    """Guard the fixture itself: if this ever gains a text layer the OCR test is void."""
    from pypdf import PdfReader

    embedded = "".join((p.extract_text() or "") for p in PdfReader(str(scanned_pdf)).pages)
    assert embedded.strip() == ""


@pytest.mark.skipif(not ocr_available(), reason="Tesseract not installed")
def test_scanned_pdf_is_read_via_ocr(scanned_pdf: Path) -> None:
    result = extract_document(str(scanned_pdf))
    assert result.used_ocr is True
    assert result.pages == 1
    assert "AGREEMENT" in result.text.upper()


def test_text_layer_pdf_does_not_use_ocr(sample_dir: Path) -> None:
    result = extract_document(str(sample_dir / "agreement.pdf"))
    assert result.used_ocr is False
    assert "Acme Corp" in result.text


def test_scanned_pdf_without_tesseract_explains_how_to_install(
    scanned_pdf: Path,
) -> None:
    with patch("backend.parser.ocr_available", return_value=False):
        with pytest.raises(ValueError, match="Install Tesseract|OCR is not available"):
            extract_document(str(scanned_pdf))


def test_extract_text_still_returns_a_plain_string(sample_dir: Path) -> None:
    """The original API must keep working for any existing callers."""
    text = extract_text(str(sample_dir / "agreement.txt"))
    assert isinstance(text, str)
    assert "Acme Corp" in text
