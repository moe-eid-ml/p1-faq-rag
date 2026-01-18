"""MC-KOS-27: PDF ingestion module.

Provides deterministic PDF text extraction and normalization.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from pypdf import PdfReader


def extract_pdf_pages(path: str) -> List[str]:
    """Extract text from each page of a PDF.

    Args:
        path: Path to PDF file.

    Returns:
        List of strings, one per page (0-indexed internally, but page numbers are 1-indexed).

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file is not a valid PDF.
    """
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    if not pdf_path.suffix.lower() == ".pdf":
        raise ValueError(f"File is not a PDF: {path}")

    try:
        reader = PdfReader(str(pdf_path))
    except Exception as e:
        raise ValueError(f"Cannot read PDF: {path} ({e})") from e

    pages: List[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)

    return pages


def normalize_text_v1(text: str) -> str:
    """Normalize text deterministically for offset computation.

    Normalization rules (v1):
    - Handle hyphenation at line breaks: "Mindest-\\numsatz" -> "Mindestumsatz"
    - Collapse multiple whitespace to single space
    - Strip leading/trailing whitespace

    Args:
        text: Raw text to normalize.

    Returns:
        Normalized text string.
    """
    if not text:
        return ""
    # Handle hyphenation at line breaks: "Mindest-\numsatz" -> "Mindestumsatz"
    normalized = re.sub(r"-\s*\n\s*", "", text)
    # Collapse whitespace
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def ingest_pdf(path: str, doc_id: str | None = None) -> dict:
    """Ingest a PDF and produce an intermediate artifact.

    Args:
        path: Path to PDF file.
        doc_id: Document identifier (defaults to filename).

    Returns:
        Dict with:
        - doc_id: str
        - pages: list of {page: int, raw_text: str, normalized_text_v1: str}
        - offset_basis: "normalized_text_v1"
    """
    pdf_path = Path(path)
    if doc_id is None:
        doc_id = pdf_path.name

    raw_pages = extract_pdf_pages(path)

    pages = []
    for i, raw_text in enumerate(raw_pages):
        pages.append({
            "page": i + 1,  # 1-indexed
            "raw_text": raw_text,
            "normalized_text_v1": normalize_text_v1(raw_text),
        })

    return {
        "doc_id": doc_id,
        "pages": pages,
        "offset_basis": "normalized_text_v1",
    }
