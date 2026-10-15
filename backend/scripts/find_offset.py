"""Find how many PDF pages come before printed page 1 of the textbook.

Usage (from the repo root):
    python backend/scripts/find_offset.py [path/to/textbook.pdf]

The default PDF path is backend/data/textbook.pdf.

Put the printed number in PDF_PAGE_OFFSET in .env.
"""
import sys
from pathlib import Path

from pypdf import PdfReader

path = Path(sys.argv[1] if len(sys.argv) > 1 else "backend/data/textbook.pdf")
reader = PdfReader(str(path))

for idx in range(8, min(40, len(reader.pages))):
    text = (reader.pages[idx].extract_text() or "").lower()
    if "real numbers" in text and "1.1" in text and "introduction" in text:
        print(f"Chapter 1 starts at PDF page index {idx} (page {idx + 1} in a PDF viewer).")
        print(f"Set PDF_PAGE_OFFSET={idx}")
        break
else:
    print("Could not detect it automatically. Open the PDF, find the page where")
    print("Chapter 1 'Real Numbers' starts, and set PDF_PAGE_OFFSET to (its page number - 1).")
