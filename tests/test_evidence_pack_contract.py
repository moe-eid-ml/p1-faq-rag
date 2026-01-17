"""MC-KOS-23: Evidence Pack Contract Tests (minimal suite).

Documents and enforces the stable, deterministic evidence pack contract.
Tests: 2-5 including 1 adversarial per Sniper process rules.
"""

import json

import pytest

from kosniper.contracts import (
    CheckerResult,
    EvidencePack,
    EvidenceSpan,
    ReasonCode,
    RunResult,
    TrafficLight,
)


class TestEvidencePackContract:
    """Minimal contract test suite."""

    def test_valid_pack_serializes_with_expected_keys(self):
        """Happy path: valid EvidencePack constructs and serializes."""
        evidence = EvidenceSpan(
            doc_id="test.pdf",
            page_number=1,
            snippet="test snippet",
            start_offset=0,
            end_offset=12,
            offset_basis="normalized_text_v1",
        )
        check = CheckerResult(
            checker_name="TestChecker",
            status=TrafficLight.YELLOW,
            reason=ReasonCode.KO_PHRASE_FOUND,
            evidence=[evidence],
        )
        run_result = RunResult(
            overall=TrafficLight.YELLOW,
            summary="Test summary",
            results=[check],
        )
        pack = EvidencePack(run_result=run_result)

        d = pack.to_dict()
        assert d["schema_version"] == "1.0"
        assert d["overall_verdict"] == "yellow"
        assert d["verdict"] == "yellow"
        assert "checks" in d
        assert len(d["checks"]) == 1
        # Round-trip through JSON
        assert json.loads(json.dumps(d))["overall_verdict"] == "yellow"

    def test_overall_equals_worst_verdict_of_checks(self):
        """Invariant: overall must equal worst verdict (red > yellow > abstain > green)."""
        ev = EvidenceSpan(doc_id="test.pdf", page_number=1, snippet="test")
        checks = [
            CheckerResult(
                checker_name="Yellow",
                status=TrafficLight.YELLOW,
                reason=ReasonCode.KO_PHRASE_FOUND,
                evidence=[ev],
            ),
            CheckerResult(
                checker_name="Red",
                status=TrafficLight.RED,
                reason=ReasonCode.BELOW_THRESHOLD,
                evidence=[ev],
            ),
        ]
        # Must set overall=RED (the worst)
        run_result = RunResult(overall=TrafficLight.RED, summary="Mixed", results=checks)
        pack = EvidencePack(run_result=run_result)
        assert pack.to_dict()["overall_verdict"] == "red"

    def test_adversarial_mismatched_overall_rejected(self):
        """ADVERSARIAL: overall != worst verdict raises ValueError."""
        ev = EvidenceSpan(doc_id="test.pdf", page_number=1, snippet="test")
        red_check = CheckerResult(
            checker_name="Red",
            status=TrafficLight.RED,
            reason=ReasonCode.BELOW_THRESHOLD,
            evidence=[ev],
        )
        with pytest.raises(ValueError, match="must equal worst verdict"):
            RunResult(overall=TrafficLight.GREEN, summary="Invalid", results=[red_check])

    def test_adversarial_offsets_without_basis_rejected(self):
        """ADVERSARIAL: offsets without offset_basis raises ValueError."""
        with pytest.raises(ValueError, match="offset_basis"):
            EvidenceSpan(
                doc_id="test.pdf",
                page_number=1,
                snippet="test",
                start_offset=0,
                end_offset=4,
                # offset_basis intentionally missing
            )
