"""Optical character recognition for scanned PDFs, using Tesseract locally."""

import io
import os
import shutil
from concurrent.futures import ThreadPoolExecutor

from backend.config import OCR_DPI, OCR_LANGUAGE, OCR_MAX_PAGES

TESSERACT_MISSING_MESSAGE = (
    "This PDF is a scan (images only) and OCR is not available. Install "
    "Tesseract to read scanned documents:\n"
    "  Windows: winget install UB-Mannheim.TesseractOCR\n"
    "           (or the installer at https://github.com/UB-Mannheim/tesseract/wiki)\n"
    "  macOS:   brew install tesseract\n"
    "  Linux:   sudo apt install tesseract-ocr"
)

# Default install locations, checked when Tesseract is installed but not on PATH.
_FALLBACK_PATHS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe",
    r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe",
    "/opt/homebrew/bin/tesseract",
    "/usr/local/bin/tesseract",
    "/usr/bin/tesseract",
)


def _tesseract_path() -> str | None:
    """Find the Tesseract binary: PATH first, then the usual install locations."""
    on_path = shutil.which("tesseract")
    if on_path:
        return on_path
    for candidate in _FALLBACK_PATHS:
        resolved = os.path.expandvars(candidate)
        if "%" not in resolved and os.path.isfile(resolved):
            return resolved
    return None


def ocr_available() -> bool:
    """Return True if both the Python bindings and the Tesseract binary are present."""
    try:
        import pymupdf  # noqa: F401
        import pytesseract
    except ImportError:
        return False

    binary = _tesseract_path()
    if binary is None:
        return False

    # Point the bindings at the binary we found, in case it is not on PATH.
    pytesseract.pytesseract.tesseract_cmd = binary
    return True


def _worker_count(page_count: int) -> int:
    """Pick a thread count: Tesseract runs as a subprocess, so threads scale well."""
    return max(1, min(page_count, (os.cpu_count() or 2), 8))


def _render_pages(path: str, max_pages: int) -> tuple[list[bytes], bool]:
    """Rasterize each PDF page to PNG bytes. PyMuPDF is used serially by design."""
    import pymupdf

    try:
        document = pymupdf.open(path)
    except Exception as exc:
        raise ValueError(f"Could not open the PDF for OCR. ({exc})") from exc

    images: list[bytes] = []
    truncated = False
    try:
        for index, page in enumerate(document):
            if index >= max_pages:
                truncated = True
                break
            try:
                images.append(page.get_pixmap(dpi=OCR_DPI).tobytes("png"))
            except Exception:
                images.append(b"")  # Keep page order; this page yields no text.
    finally:
        document.close()

    return images, truncated


def _read_image(png: bytes) -> str:
    """Run Tesseract over one rendered page, returning an empty string on failure."""
    if not png:
        return ""
    import pytesseract
    from PIL import Image

    try:
        with Image.open(io.BytesIO(png)) as image:
            return pytesseract.image_to_string(image, lang=OCR_LANGUAGE).strip()
    except Exception:
        return ""  # A single unreadable page should not sink the document.


def ocr_pdf(path: str, max_pages: int = OCR_MAX_PAGES) -> str:
    """Render a scanned PDF to images and read them with Tesseract, pages in parallel."""
    if not ocr_available():
        raise ValueError(TESSERACT_MISSING_MESSAGE)

    images, truncated = _render_pages(path, max_pages)
    if not images:
        raise ValueError("The PDF has no pages to read.")

    with ThreadPoolExecutor(max_workers=_worker_count(len(images))) as pool:
        pages = [text for text in pool.map(_read_image, images) if text]

    if not pages:
        raise ValueError(
            "OCR ran but found no readable text. The scan may be too faint, "
            "skewed, or handwritten."
        )

    result = "\n\n".join(pages)
    if truncated:
        result += f"\n\n[Only the first {max_pages} pages were read by OCR.]"
    return result
