import re
from functools import lru_cache

from pypdf import PdfReader

from .chapters import BY_ID
from .config import EXCERPT_CHARS, PDF_PAGE_OFFSET, TEXTBOOK_PDF


@lru_cache(maxsize=1)
def _reader() -> PdfReader:
    if not TEXTBOOK_PDF.exists():
        raise FileNotFoundError(
            f"Textbook PDF not found at {TEXTBOOK_PDF}. Put it in data/textbook.pdf "
            "or set TEXTBOOK_PDF in .env."
        )
    return PdfReader(str(TEXTBOOK_PDF))


@lru_cache(maxsize=None)
def chapter_text(chapter_id: int) -> str:
    ch = BY_ID[chapter_id]
    reader = _reader()
    first = ch.start_page - 1 + PDF_PAGE_OFFSET
    last = min(ch.end_page - 1 + PDF_PAGE_OFFSET, len(reader.pages) - 1)

    parts = []
    for i in range(first, last + 1):
        text = reader.pages[i].extract_text() or ""
        text = text.replace("Reprint 2026-27", "")
        text = re.sub(r"\n{3,}", "\n\n", text)
        parts.append(text.strip())

    return "\n\n".join(parts)


def sample_text(text: str, limit: int = EXCERPT_CHARS, phase: float = 0.0, windows: int = 6) -> str:
    if len(text) <= limit:
        return text

    size = limit // windows
    span = len(text) - size
    slices = []
    for j in range(windows):
        start = int((j + phase) * span / windows)
        newline = text.find("\n", start, start + 300)
        if newline != -1:
            start = newline + 1
        slices.append(text[start : start + size].strip())
    return "\n...\n".join(slices)


def chapter_excerpt(chapter_id: int, phase: float = 0.0) -> str:
    return sample_text(chapter_text(chapter_id), phase=phase)
