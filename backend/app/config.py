import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT = BACKEND_DIR.parent
load_dotenv(ROOT / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Model names change over time; override in .env if this one is retired.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

TEXTBOOK_PDF = BACKEND_DIR / os.getenv("TEXTBOOK_PDF", "data/textbook.pdf")

# Number of PDF pages that come BEFORE printed page 1 (cover, foreword, contents...).
# Run `python backend/scripts/find_offset.py` to detect it.
PDF_PAGE_OFFSET = int(os.getenv("PDF_PAGE_OFFSET", "0"))

# Cap on how much chapter text is sent to Gemini per chapter.
MAX_CHARS_PER_CHAPTER = int(os.getenv("MAX_CHARS_PER_CHAPTER", "60000"))
