"""MC-KOS-43: Export report pack tests.

Tests: 3 including 1 adversarial per Sniper process rules.
"""

import json
import subprocess
import sys
from pathlib import Path

from kosniper.export.report_md import render_report

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _run_scan(pdf_path: Path) -> dict:
    """Run CLI --scan on PDF and return parsed JSON output."""
    result = subprocess.run(
        [sys.executable, "-m", "kosniper.cli", "--pdf", str(pdf_path), "--scan", "--format", "json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    return json.loads(result.stdout)


class TestReportMd:
    """Tests for render_report function."""

    def test_golden_report_contains_expected_sections_ko(self):
        """Golden: KO fixture report contains verdict, checks, evidence, provenance."""
        pdf_path = FIXTURES_DIR / "fixture_ko_page2.pdf"
        pack = _run_scan(pdf_path)

        report = render_report(pack)

        # Header and verdict
        assert "# KOSniper Report" in report
        assert "**Overall Verdict:** RED" in report

        # Summary
        assert "**Summary:**" in report

        # Checks section with evidence
        assert "## Checks" in report
        assert "### " in report  # At least one checker heading
        assert "**Verdict:** red" in report
        assert "**Evidence:**" in report

        # Document provenance
        assert "## Document Provenance" in report
        assert "**Document:**" in report
        assert "**SHA256:**" in report

        # Footer
        assert "schema 1.0" in report

    def test_golden_report_contains_expected_sections_neutral(self):
        """Golden: Neutral fixture report contains verdict but no fabricated evidence."""
        pdf_path = FIXTURES_DIR / "fixture_neutral.pdf"
        pack = _run_scan(pdf_path)

        report = render_report(pack)

        # Header and verdict
        assert "# KOSniper Report" in report
        assert "**Overall Verdict:** ABSTAIN" in report

        # No fabricated checks - should show "no findings" message
        assert "No checks produced findings" in report
        assert "Manual review required" in report

        # Document provenance still present
        assert "## Document Provenance" in report

    def test_adversarial_abstain_never_implies_green(self):
        """ADVERSARIAL: Empty checks (ABSTAIN) renders without crashing, never implies GREEN."""
        # Construct minimal ABSTAIN pack directly (no checks)
        pack = {
            "schema_version": "1.0",
            "overall_verdict": "abstain",
            "verdict": "abstain",
            "summary": "Insufficient data to assess; manual review required.",
            "checks": [],
            "document_map": {
                "doc_id": "test.pdf",
                "offset_basis": "normalized_text_v1",
                "pages": [],
                "overall_sha256": "abc123",
            },
        }

        # Must not crash
        report = render_report(pack)

        # Must show ABSTAIN verdict
        assert "**Overall Verdict:** ABSTAIN" in report

        # Must NOT imply GREEN
        assert "GREEN" not in report
        assert "green" not in report.lower().replace("abstain", "").replace("no checks", "")

        # Must indicate no findings / manual review
        assert "No checks produced findings" in report or "manual review" in report.lower()


class TestCliOutDir:
    """Tests for --out-dir CLI flag."""

    def test_out_dir_writes_report_pack(self, tmp_path):
        """--out-dir writes evidence_pack.json, report.md, document_map.json."""
        pdf_path = FIXTURES_DIR / "fixture_ko_page2.pdf"
        out_dir = tmp_path / "report_pack"

        result = subprocess.run(
            [
                sys.executable, "-m", "kosniper.cli",
                "--pdf", str(pdf_path),
                "--scan",
                "--out-dir", str(out_dir),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Check files exist
        assert (out_dir / "evidence_pack.json").exists()
        assert (out_dir / "report.md").exists()
        assert (out_dir / "document_map.json").exists()

        # Verify evidence_pack.json is valid JSON with expected fields
        with open(out_dir / "evidence_pack.json") as f:
            pack = json.load(f)
        assert pack["overall_verdict"] == "red"
        assert "checks" in pack
        assert "document_map" in pack

        # Verify report.md contains expected content
        report = (out_dir / "report.md").read_text()
        assert "# KOSniper Report" in report
        assert "**Overall Verdict:** RED" in report

        # Verify document_map.json matches pack's document_map
        with open(out_dir / "document_map.json") as f:
            doc_map = json.load(f)
        assert doc_map["doc_id"] == pack["document_map"]["doc_id"]
        assert doc_map["overall_sha256"] == pack["document_map"]["overall_sha256"]
