"""MC-KOS-34: Document map provenance tests (minimal suite).

Tests for document_map artifact in --scan output.
Tests: 3 including 1 adversarial per Sniper process rules.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("reportlab")

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


def _create_pdf(pages: list[str], path: Path) -> None:
    """Create a PDF with the given text on each page."""
    c = canvas.Canvas(str(path), pagesize=letter)
    for text in pages:
        c.drawString(72, 720, text)
        c.showPage()
    c.save()


def _run_cli(args: list[str]) -> subprocess.CompletedProcess:
    """Run CLI and capture output."""
    return subprocess.run(
        [sys.executable, "-m", "kosniper.cli"] + args,
        capture_output=True,
        text=True,
    )


class TestDocumentMap:
    """Document map provenance test suite."""

    def test_scan_output_contains_document_map(self, tmp_path):
        """--scan JSON output contains document_map with correct structure."""
        pdf_path = tmp_path / "test.pdf"
        _create_pdf(
            pages=["Page 1 content.", "Page 2 content.", "Page 3 content."],
            path=pdf_path,
        )

        result = _run_cli(["--pdf", str(pdf_path), "--scan", "--format", "json"])

        assert result.returncode == 0
        output = json.loads(result.stdout)

        # Verify document_map exists and has correct structure
        assert "document_map" in output
        doc_map = output["document_map"]

        assert doc_map["doc_id"] == pdf_path.name
        assert doc_map["offset_basis"] == "normalized_text_v1"
        assert len(doc_map["pages"]) == 3
        assert "overall_sha256" in doc_map

        # Verify page entries have required fields
        for page in doc_map["pages"]:
            assert "page_number" in page
            assert "raw_text_sha256" in page
            assert "normalized_text_sha256" in page
            assert "char_count_raw" in page
            assert "char_count_normalized" in page
            # SHA256 is 64 hex chars
            assert len(page["raw_text_sha256"]) == 64
            assert len(page["normalized_text_sha256"]) == 64

    def test_hashes_are_stable(self, tmp_path):
        """Same input produces identical hashes (determinism)."""
        pdf_path = tmp_path / "stable.pdf"
        _create_pdf(pages=["Deterministic content."], path=pdf_path)

        result1 = _run_cli(["--pdf", str(pdf_path), "--scan", "--format", "json"])
        result2 = _run_cli(["--pdf", str(pdf_path), "--scan", "--format", "json"])

        assert result1.returncode == 0
        assert result2.returncode == 0

        output1 = json.loads(result1.stdout)
        output2 = json.loads(result2.stdout)

        # Hashes must be identical across runs
        map1, map2 = output1["document_map"], output2["document_map"]
        assert map1["overall_sha256"] == map2["overall_sha256"]
        assert map1["pages"][0]["raw_text_sha256"] == map2["pages"][0]["raw_text_sha256"]
        assert map1["pages"][0]["normalized_text_sha256"] == map2["pages"][0]["normalized_text_sha256"]

    def test_adversarial_empty_page_produces_hashes(self, tmp_path):
        """ADVERSARIAL: Empty/blank page produces hashes (of empty string), no crash."""
        pdf_path = tmp_path / "empty.pdf"
        _create_pdf(pages=["", "   ", "Content."], path=pdf_path)

        result = _run_cli(["--pdf", str(pdf_path), "--scan", "--format", "json"])

        assert result.returncode == 0
        output = json.loads(result.stdout)

        doc_map = output["document_map"]
        assert len(doc_map["pages"]) == 3

        # Empty pages still have valid hashes
        for page in doc_map["pages"]:
            assert len(page["raw_text_sha256"]) == 64
            assert len(page["normalized_text_sha256"]) == 64
            assert isinstance(page["char_count_raw"], int)
            assert isinstance(page["char_count_normalized"], int)
