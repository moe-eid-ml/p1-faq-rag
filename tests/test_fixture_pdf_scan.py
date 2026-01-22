"""MC-KOS-38/42: Fixture PDF scan tests (deterministic end-to-end).

Tests: 6 using static fixture PDFs under tests/fixtures/.
Includes golden tests that lock v1 invariants (MC-KOS-42).
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

        assert "evidence" in red_checks[0], "Red check missing 'evidence' key"
        assert len(red_checks[0]["evidence"]) >= 1, "Red check has no evidence items"
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


class TestV1GoldenInvariants:
    """MC-KOS-42: Golden tests that lock v1 invariants."""

    def test_document_map_present_with_sha256(self):
        """v1 invariant: document_map present with overall_sha256 for both KO and neutral."""
        for fixture_name in ["fixture_ko_page2.pdf", "fixture_neutral.pdf"]:
            pdf_path = FIXTURES_DIR / fixture_name
            assert pdf_path.exists(), f"Fixture missing: {pdf_path}"

            output = _run_scan(pdf_path)

            # document_map must be present
            assert "document_map" in output, f"{fixture_name}: missing document_map"
            doc_map = output["document_map"]

            # Required fields
            assert "doc_id" in doc_map, f"{fixture_name}: missing doc_id"
            assert "offset_basis" in doc_map, f"{fixture_name}: missing offset_basis"
            assert doc_map["offset_basis"] == "normalized_text_v1"
            assert "pages" in doc_map, f"{fixture_name}: missing pages"
            assert "overall_sha256" in doc_map, f"{fixture_name}: missing overall_sha256"
            assert doc_map["overall_sha256"] is not None, f"{fixture_name}: sha256 is None"
            assert len(doc_map["overall_sha256"]) == 64, f"{fixture_name}: sha256 wrong length"

    def test_worst_check_wins_overall_verdict(self):
        """v1 invariant: overall_verdict = worst verdict across all checks."""
        pdf_path = FIXTURES_DIR / "fixture_ko_page2.pdf"
        output = _run_scan(pdf_path)

        checks = output.get("checks", [])
        overall = output.get("overall_verdict")

        # Severity ordering: red > yellow > abstain > green (lower index = worse)
        severity = {"red": 0, "yellow": 1, "abstain": 2, "green": 3}

        if checks:
            worst_check_sev = min(severity.get(c["verdict"], 3) for c in checks)
            overall_sev = severity.get(overall, 3)
            # overall must be at least as severe as the worst check
            assert overall_sev <= worst_check_sev, (
                f"Worst-check-wins violated: overall={overall} but worst check is "
                f"{[c['verdict'] for c in checks if severity.get(c['verdict'], 3) == worst_check_sev][0]}"
            )

    def test_never_false_green_invariant(self):
        """v1 invariant: empty/no findings => ABSTAIN (not GREEN)."""
        pdf_path = FIXTURES_DIR / "fixture_neutral.pdf"
        output = _run_scan(pdf_path)

        checks = output.get("checks", [])
        overall = output.get("overall_verdict")

        # If no checks (no findings), must be ABSTAIN not GREEN
        if len(checks) == 0:
            assert overall != "green", "Never false-green: empty checks must be ABSTAIN not GREEN"
            assert overall == "abstain", f"Empty checks should be ABSTAIN, got {overall}"

    def test_adversarial_offset_basis_required_when_offsets_present(self):
        """ADVERSARIAL: Every evidence span with offsets must have offset_basis set."""
        pdf_path = FIXTURES_DIR / "fixture_ko_page2.pdf"
        output = _run_scan(pdf_path)

        for i, check in enumerate(output.get("checks", [])):
            for j, ev in enumerate(check.get("evidence", [])):
                has_offsets = ev.get("start_offset") is not None or ev.get("end_offset") is not None
                if has_offsets:
                    assert ev.get("offset_basis") == "normalized_text_v1", (
                        f"check[{i}].evidence[{j}]: offset_basis missing/wrong "
                        f"when offsets present (start={ev.get('start_offset')}, end={ev.get('end_offset')})"
                    )
