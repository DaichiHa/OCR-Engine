"""PDF text-layer extraction helpers."""

from __future__ import annotations

from pathlib import Path
from typing import List

from PyPDF2 import PdfReader


def extract_text_layers(pdf_path: str | Path) -> List[str]:
    """Extract text content from each page of a PDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        A list of per-page text strings (empty string when no text layer exists).
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    reader = PdfReader(str(path))
    pages_text: List[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)
    return pages_text
