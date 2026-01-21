"""MC-KOS-38: Fixture PDF scan tests (deterministic end-to-end).

Tests: 2 using static fixture PDFs under tests/fixtures/.
"""

import json
import subprocess
import sys
from pathlib import Path

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


class TestFixturePdfScan:
    """Deterministic end-to-end scan tests using fixture PDFs."""

    def test_ko_page2_returns_red_with_evidence(self):
        """fixture_ko_page2.pdf => RED + evidence on page 2 + offset_basis."""
        pdf_path = FIXTURES_DIR / "fixture_ko_page2.pdf"
        assert pdf_path.exists(), f"Fixture missing: {pdf_path}"

        output = _run_scan(pdf_path)

        assert output["overall_verdict"] == "red"
        assert len(output["checks"]) >= 1

        # Find the RED check with evidence
        red_checks = [c for c in output["checks"] if c["verdict"] == "red"]
        assert len(red_checks) >= 1

        ev = red_checks[0]["evidence"][0]
        assert ev["page"] == 2
        assert ev["offset_basis"] == "normalized_text_v1"
        assert ev["start_offset"] is not None
        assert ev["end_offset"] is not None

    def test_neutral_returns_abstain_no_evidence(self):
        """fixture_neutral.pdf => ABSTAIN + no fabricated evidence."""
        pdf_path = FIXTURES_DIR / "fixture_neutral.pdf"
        assert pdf_path.exists(), f"Fixture missing: {pdf_path}"

        output = _run_scan(pdf_path)

        assert output["overall_verdict"] == "abstain"
        # No checks means no fabricated evidence (never false-green)
        assert len(output["checks"]) == 0
