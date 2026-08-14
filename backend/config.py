"""Central configuration for Legal-Eye. Loads settings from .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (one level above backend/), regardless of cwd.
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").strip()
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()

MAX_INPUT_CHARS: int = 50_000
MAX_OUTPUT_TOKENS: int = 3_000
TEMPERATURE: float = 0.2

# OCR settings for scanned PDFs. 300 DPI is the accuracy/speed sweet spot for
# Tesseract; below 200 accuracy drops sharply, above 400 gains little.
OCR_DPI: int = 300
OCR_LANGUAGE: str = os.getenv("OCR_LANGUAGE", "eng").strip()
OCR_MAX_PAGES: int = 60
# A PDF yielding fewer than this many characters is treated as a scan.
SCANNED_PDF_THRESHOLD: int = 100

# Retry schedule (seconds) used when DeepSeek returns a rate-limit error.
RETRY_BACKOFF: tuple[int, ...] = (2, 5, 10)

# deepseek-chat pricing, USD per 1M tokens. Update if DeepSeek changes rates.
PRICE_INPUT_CACHE_MISS: float = 0.27
PRICE_INPUT_CACHE_HIT: float = 0.07
PRICE_OUTPUT: float = 1.10

MISSING_KEY_MESSAGE: str = (
    "API key is not set. Copy .env.example to .env and add your API key "
    "(the .env.example file says where to get one)."
)


def require_api_key() -> str:
    """Return the API key, or raise RuntimeError with setup instructions if unset."""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError(MISSING_KEY_MESSAGE)
    return DEEPSEEK_API_KEY
