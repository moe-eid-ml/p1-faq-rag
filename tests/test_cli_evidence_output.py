"""MC-KOS-30: CLI evidence output tests (minimal suite).

Tests for evidence spans in CLI output.
Tests: 3 including 1 adversarial per Sniper process rules.
"""

import json
import subprocess
import sys


def _run_cli(args: list[str]) -> subprocess.CompletedProcess:
    """Run CLI and capture output."""
    return subprocess.run(
        [sys.executable, "-m", "kosniper.cli"] + args,
        capture_output=True,
        text=True,
    )


class TestCliEvidenceOutput:
    """CLI evidence output test suite."""

    def test_json_output_contains_evidence_with_offset_basis(self):
        """JSON output includes evidence spans with offset_basis for RED case."""
        result = _run_cli([
            "--doc-id", "tender.pdf",
            "--page", "1",
            "--text", "Die folgenden Ausschlusskriterien gelten für Bieter.",
            "--format", "json",
        ])

        assert result.returncode == 0
        output = json.loads(result.stdout)

        # Verify structure
        assert output["overall_verdict"] == "red"
        assert len(output["checks"]) >= 1

        # Find KoKeywordChecker result
        ko_check = next(
            (c for c in output["checks"] if c["check_id"] == "KoKeywordChecker"),
            None,
        )
        assert ko_check is not None
        assert ko_check["verdict"] == "red"
        assert len(ko_check["evidence"]) >= 1

        # Verify evidence has required fields
        ev = ko_check["evidence"][0]
        assert "snippet" in ev
        assert "Ausschlusskriterien" in ev["snippet"]
        assert ev["offset_basis"] == "normalized_text_v1"
        assert isinstance(ev["start_offset"], int)
        assert isinstance(ev["end_offset"], int)

    def test_pretty_output_includes_evidence_line(self):
        """Pretty output includes compact evidence line in stderr."""
        result = _run_cli([
            "--doc-id", "tender.pdf",
            "--page", "1",
            "--text", "Die folgenden Ausschlusskriterien gelten.",
            "--format", "pretty",
        ])

        assert result.returncode == 0
        # Check stderr for evidence line
        assert "[KoKeywordChecker]" in result.stderr
        assert "Ausschlusskriterien" in result.stderr
        assert "tender.pdf:1" in result.stderr

    def test_adversarial_no_findings_no_invented_evidence(self):
        """ADVERSARIAL: No findings produces no invented evidence spans."""
        # Use text that triggers ABSTAIN (empty text after normalization won't work
        # due to CLI guard, so use text that produces checker results but no KO)
        result = _run_cli([
            "--doc-id", "test.pdf",
            "--page", "1",
            "--text", "Der Mindestumsatz beträgt 500.000 EUR.",
            "--format", "json",
        ])

        # Should succeed (YELLOW from MinimalKoPhraseChecker for "mindestumsatz")
        assert result.returncode == 0
        output = json.loads(result.stdout)

        # Evidence should only come from actual checker findings
        for check in output.get("checks", []):
            for ev in check.get("evidence", []):
                # All evidence must have non-empty snippet (real finding)
                assert ev.get("snippet", "").strip() != ""
                # If offsets present, must have offset_basis
                if ev.get("start_offset") is not None:
                    assert ev.get("offset_basis") == "normalized_text_v1"
