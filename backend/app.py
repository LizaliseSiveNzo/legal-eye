"""Legal-Eye command-line entry point: summarize a legal document to stdout."""

import argparse
import sys
from pathlib import Path

# Allow `python backend/app.py ...` as well as `python -m backend.app ...`.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.parser import extract_document  # noqa: E402
from backend.summarizer import estimate_cost, summarize_legal_document  # noqa: E402


def main() -> int:
    """Parse arguments, summarize the document, and print the Markdown result."""
    parser = argparse.ArgumentParser(
        prog="legal-eye",
        description="Summarize a legal document (.pdf, .docx, .txt) using AI.",
    )
    parser.add_argument("file_path", help="Path to the document to summarize")
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Also write the summary to this file (e.g. summary.md)",
    )
    args = parser.parse_args()

    try:
        extraction = extract_document(args.file_path)
        text = extraction.text
        if extraction.used_ocr:
            print(
                "Scanned document detected — text read via OCR. Verify names, "
                "figures, and dates against the original.",
                file=sys.stderr,
            )
        print(
            f"Analyzing document with AI... "
            f"({len(text):,} characters, ~${estimate_cost(len(text)):.3f})",
            file=sys.stderr,
        )
        summary = summarize_legal_document(
            text, on_progress=lambda stage: print(f"  {stage}", file=sys.stderr)
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130

    print(summary)

    if args.output:
        try:
            Path(args.output).write_text(summary, encoding="utf-8")
            print(f"Saved summary to {args.output}", file=sys.stderr)
        except OSError as exc:
            print(f"Error: could not write {args.output}: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
