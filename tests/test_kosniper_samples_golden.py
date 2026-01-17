"""MC-KOS-14: Golden deterministic tests against samples/ folder.

Tests verify CLI produces valid EvidencePack JSON with correct
provenance and safe-fail invariants.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SAMPLES_DIR = Path(__file__).parent.parent / "samples"
PROJECT_ROOT = Path(__file__).parent.parent


def _run_cli_with_sample(sample_filename: str, doc_id: str, page: int = 1) -> subprocess.CompletedProcess:
    """Run CLI against a sample file and return the result."""
    sample_path = SAMPLES_DIR / sample_filename
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "kosniper.cli",
            "--doc-id",
            doc_id,
            "--page",
            str(page),
            "--text-file",
            str(sample_path),
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


class TestGoldenSamplesStructure:
    """Tests that CLI output against samples is structurally valid."""

    def test_ko_phrase_sample_returns_valid_json(self):
        """Sample with KO phrase returns valid EvidencePack JSON."""
        result = _run_cli_with_sample("tender_ko_phrase.txt", "tender_ko_phrase.pdf", 1)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        data = json.loads(result.stdout)
        assert data.get("schema_version") == "1.0"
        assert "overall_verdict" in data
        assert "checks" in data
        assert isinstance(data["checks"], list)

    def test_turnover_sample_returns_valid_json(self):
        """Sample with turnover threshold returns valid EvidencePack JSON."""
        result = _run_cli_with_sample("tender_turnover.txt", "tender_turnover.pdf", 1)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        data = json.loads(result.stdout)
        assert data.get("schema_version") == "1.0"
        assert "overall_verdict" in data
        assert "checks" in data
        assert isinstance(data["checks"], list)


class TestGoldenVerdictConstraints:
    """Tests that verdicts follow safe-fail invariants."""

    def test_ko_phrase_sample_not_green_without_evidence(self):
        """KO phrase sample: if checks empty, verdict must not be green."""
        result = _run_cli_with_sample("tender_ko_phrase.txt", "tender_ko_phrase.pdf", 1)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        data = json.loads(result.stdout)
        verdict = data.get("overall_verdict", "")
        checks = data.get("checks", [])

        assert verdict != "green", "KO phrase sample must not yield GREEN"
        assert len(checks) > 0

    def test_turnover_sample_not_green_without_evidence(self):
        """Turnover sample: if checks empty, verdict must not be green."""
        result = _run_cli_with_sample("tender_turnover.txt", "tender_turnover.pdf", 1)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        data = json.loads(result.stdout)
        verdict = data.get("overall_verdict", "")
        checks = data.get("checks", [])

        assert verdict != "green", "Turnover sample must not yield GREEN"
        assert len(checks) > 0

    def test_non_green_verdict_requires_checks(self):
        """Non-green overall verdict must have at least one check."""
        result = _run_cli_with_sample("tender_ko_phrase.txt", "tender_ko_phrase.pdf", 1)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        data = json.loads(result.stdout)
        verdict = data.get("overall_verdict", "")
        checks = data.get("checks", [])

        if verdict in ("red", "yellow", "abstain"):
            assert len(checks) > 0, f"Verdict {verdict} requires at least one check"


class TestGoldenProvenanceFields:
    """Tests that evidence spans include provenance fields."""

    def test_ko_phrase_evidence_has_provenance(self):
        """Evidence spans from KO phrase sample include doc_id and page."""
        result = _run_cli_with_sample("tender_ko_phrase.txt", "tender_ko_phrase.pdf", 3)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        data = json.loads(result.stdout)
        checks = data.get("checks", [])

        for check in checks:
            if check.get("verdict") != "green":
                evidence_list = check.get("evidence", [])
                assert len(evidence_list) > 0, (
                    f"Non-green check {check.get('check_id')} must have evidence"
                )
                for ev in evidence_list:
                    assert "doc_id" in ev, f"Evidence missing doc_id: {ev}"
                    assert "page" in ev, f"Evidence missing page: {ev}"
                    assert ev["doc_id"] == "tender_ko_phrase.pdf", (
                        f"Expected doc_id tender_ko_phrase.pdf, got {ev['doc_id']}"
                    )
                    assert ev["page"] == 3, f"Expected page 3, got {ev['page']}"

    def test_turnover_evidence_has_provenance(self):
        """Evidence spans from turnover sample include doc_id and page."""
        result = _run_cli_with_sample("tender_turnover.txt", "tender_turnover.pdf", 7)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        data = json.loads(result.stdout)
        checks = data.get("checks", [])

        for check in checks:
            if check.get("verdict") != "green":
                evidence_list = check.get("evidence", [])
                assert len(evidence_list) > 0, (
                    f"Non-green check {check.get('check_id')} must have evidence"
                )
                for ev in evidence_list:
                    assert "doc_id" in ev, f"Evidence missing doc_id: {ev}"
                    assert "page" in ev, f"Evidence missing page: {ev}"
                    assert ev["doc_id"] == "tender_turnover.pdf", (
                        f"Expected doc_id tender_turnover.pdf, got {ev['doc_id']}"
                    )
                    assert ev["page"] == 7, f"Expected page 7, got {ev['page']}"

    def test_evidence_snippet_is_nonempty(self):
        """Evidence snippets must be non-empty strings."""
        result = _run_cli_with_sample("tender_ko_phrase.txt", "tender_ko_phrase.pdf", 1)

        assert result.returncode == 0, f"stderr: {result.stderr}"

        data = json.loads(result.stdout)
        checks = data.get("checks", [])

        for check in checks:
            if check.get("verdict") != "green":
                for ev in check.get("evidence", []):
                    snippet = ev.get("snippet", "")
                    assert isinstance(snippet, str), f"Snippet must be string: {ev}"
                    assert len(snippet.strip()) > 0, f"Snippet must be non-empty: {ev}"
                    # Offsets (when present) must be paired and monotonic
                    if "start_offset" in ev or "end_offset" in ev:
                        assert "start_offset" in ev and "end_offset" in ev, (
                            f"Offsets must be paired: {ev}"
                        )
                        assert isinstance(ev["start_offset"], int)
                        assert isinstance(ev["end_offset"], int)
                        assert 0 <= ev["start_offset"] <= ev["end_offset"], (
                            f"Offsets must be ordered and non-negative: {ev}"
                        )
                        # If a normalized_text field is present, offsets must slice a non-empty span.
                        normalized = data.get("normalized_text")
                        if isinstance(normalized, str):
                            sliced = normalized[ev["start_offset"]:ev["end_offset"]]
                            assert sliced.strip(), "Offset slice must be non-empty"


class TestGoldenSafetyInvariants:
    """Tests for CLI safety invariants."""

    def test_neutral_sample_rejects_green_without_evidence(self):
        """Neutral sample: CLI rejects GREEN without evidence (safe-fail)."""
        result = _run_cli_with_sample("tender_neutral.txt", "tender_neutral.pdf", 1)

        # CLI must reject GREEN without evidence
        assert result.returncode == 2, (
            f"Expected exit 2 for GREEN without evidence, got {result.returncode}"
        )
        assert "GREEN without evidence" in result.stderr
