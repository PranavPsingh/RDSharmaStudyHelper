import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT = BACKEND_DIR.parent
load_dotenv(ROOT / ".env")  # local development only; on Vercel the values come from project environment variables

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Model names change over time; override in .env if this one is retired.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

TEXTBOOK_PDF = BACKEND_DIR / os.getenv("TEXTBOOK_PDF", "data/textbook.pdf")

# Number of PDF pages that come BEFORE printed page 1 (cover, foreword, contents...).
# Run `python backend/scripts/find_offset.py` to detect it.
PDF_PAGE_OFFSET = int(os.getenv("PDF_PAGE_OFFSET", "0"))

EXCERPT_CHARS = int(os.getenv("EXCERPT_CHARS", "15000"))
MAX_PARALLEL_CALLS = int(os.getenv("MAX_PARALLEL_CALLS", "3"))
_thinking_budget = os.getenv("GEMINI_THINKING_BUDGET", "1024")
GEMINI_THINKING_BUDGET = int(_thinking_budget) if _thinking_budget.strip() else None
