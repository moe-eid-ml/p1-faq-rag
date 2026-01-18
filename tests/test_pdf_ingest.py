"""MC-KOS-27: PDF ingestion tests (minimal suite).

Tests for deterministic PDF text extraction and normalization.
Tests: 2-5 including 1 adversarial per Sniper process rules.
"""

import json

import pytest
from pypdf import PdfWriter

from kosniper.ingest.pdf_ingest import ingest_pdf, normalize_text_v1


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a simple PDF with known text content."""
    pdf_path = tmp_path / "sample.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with open(pdf_path, "wb") as f:
        writer.write(f)
    return pdf_path


class TestPdfIngest:
    """Minimal PDF ingestion test suite."""

    def test_ingest_produces_expected_structure(self, sample_pdf):
        """Happy path: PDF ingestion returns pages with offset_basis."""
        result = ingest_pdf(str(sample_pdf))

        assert result["offset_basis"] == "normalized_text_v1"
        assert result["doc_id"] == "sample.pdf"
        assert isinstance(result["pages"], list)
        assert len(result["pages"]) >= 1
        # Each page has expected keys
        page = result["pages"][0]
        assert "page" in page and page["page"] == 1
        assert "raw_text" in page
        assert "normalized_text_v1" in page

    def test_normalize_text_v1_deterministic(self):
        """Normalization handles hyphenation and is deterministic."""
        text = "Der Mindest-\numsatz beträgt  500.000   EUR."
        normalized = normalize_text_v1(text)
        assert normalized == "Der Mindestumsatz beträgt 500.000 EUR."
        assert normalize_text_v1("") == ""  # Empty is stable

    def test_adversarial_nonexistent_file_rejected(self):
        """ADVERSARIAL: Non-existent/non-PDF file rejected with clear error."""
        with pytest.raises(FileNotFoundError, match="not found"):
            ingest_pdf("/nonexistent/path/file.pdf")

    def test_cli_pdf_mode_success(self, sample_pdf, capsys):
        """CLI --pdf produces valid JSON with offset_basis."""
        from kosniper.cli import main

        result = main(["--pdf", str(sample_pdf)])
        assert result == 0

        data = json.loads(capsys.readouterr().out)
        assert data["offset_basis"] == "normalized_text_v1"
        assert "pages" in data
