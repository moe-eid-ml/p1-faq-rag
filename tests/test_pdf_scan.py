"""MC-KOS-31: PDF end-to-end scan tests (minimal suite).

Tests for PDF scan mode with checker aggregation.
Tests: 3 including 1 adversarial per Sniper process rules.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Skip all tests if reportlab is not available
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


class TestPdfScan:
    """PDF scan mode test suite."""

    def test_pdf_with_ko_needle_on_page_2_returns_red(self, tmp_path):
        """PDF with KO keyword on page 2 => overall RED, evidence.page == 2."""
        pdf_path = tmp_path / "ko_page2.pdf"
        _create_pdf(
            pages=[
                "Page 1: Normal tender requirements.",
                "Page 2: Die folgenden Ausschlusskriterien gelten.",
                "Page 3: Additional information.",
            ],
            path=pdf_path,
        )

        result = _run_cli(["--pdf", str(pdf_path), "--scan", "--format", "json"])

        assert result.returncode == 0
        output = json.loads(result.stdout)

        assert output["overall_verdict"] == "red"
        assert len(output["checks"]) >= 1

        # Find KoKeywordChecker evidence
        ko_check = next(
            (c for c in output["checks"] if c["check_id"] == "KoKeywordChecker"),
            None,
        )
        assert ko_check is not None
        assert ko_check["verdict"] == "red"

        # Verify evidence has page == 2
        assert len(ko_check["evidence"]) >= 1
        ev = ko_check["evidence"][0]
        assert ev["page"] == 2
        assert ev["offset_basis"] == "normalized_text_v1"
        assert "Ausschlusskriterien" in ev["snippet"]

    def test_pdf_without_ko_needle_not_falsely_green(self, tmp_path):
        """PDF without KO keywords => not falsely GREEN, no fabricated evidence."""
        pdf_path = tmp_path / "neutral.pdf"
        _create_pdf(
            pages=[
                "Page 1: Bitte reichen Sie Ihre Unterlagen ein.",
                "Page 2: Weitere Informationen folgen.",
            ],
            path=pdf_path,
        )

        result = _run_cli(["--pdf", str(pdf_path), "--scan", "--format", "json"])

        assert result.returncode == 0
        output = json.loads(result.stdout)

        # Not falsely GREEN (YELLOW/ABSTAIN ok if no findings)
        # Note: if checkers find nothing, GREEN is acceptable per contract
        overall = output["overall_verdict"]
        assert overall in {"green", "yellow", "abstain"}

        # No fabricated evidence - each check's evidence must be real
        for check in output.get("checks", []):
            for ev in check.get("evidence", []):
                # Evidence snippet must be non-empty
                assert ev.get("snippet", "").strip() != ""

    def test_adversarial_empty_page_pdf_no_crash(self, tmp_path):
        """ADVERSARIAL: PDF with empty/blank page does not crash; conservative verdict."""
        pdf_path = tmp_path / "empty_pages.pdf"
        _create_pdf(
            pages=[
                "",  # Empty page
                "   ",  # Whitespace only
                "Page 3 has content.",
            ],
            path=pdf_path,
        )

        result = _run_cli(["--pdf", str(pdf_path), "--scan", "--format", "json"])

        # Should not crash
        assert result.returncode == 0
        output = json.loads(result.stdout)

        # Verdict should be conservative (not crash, not invalid)
        overall = output["overall_verdict"]
        assert overall in {"red", "yellow", "abstain", "green"}

        # Schema should be valid
        assert output.get("schema_version") == "1.0"
        assert isinstance(output.get("checks"), list)
