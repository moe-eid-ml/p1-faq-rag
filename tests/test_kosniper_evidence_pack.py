"""MC-KOS-11: Tests for Evidence Pack v1.

Tests for machine-readable evidence pack artifact that contains:
1) overall traffic light verdict
2) per-check entries with: check_id/name, verdict, and evidence items
3) each evidence item includes: doc_id, page, snippet, optional offsets/bbox
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
from kosniper.pipeline import make_evidence_pack


class TestEvidencePackSerialization:
    """Tests for EvidencePack JSON serialization."""

    def test_basic_serialization_structure(self):
        """Evidence pack serializes to expected JSON structure."""
        evidence = EvidenceSpan(
            doc_id="tender.pdf",
            page_number=3,
            snippet="Mindestumsatz 500.000 EUR erforderlich",
        )
        check_result = CheckerResult(
            checker_name="TurnoverThresholdChecker",
            status=TrafficLight.RED,
            reason=ReasonCode.BELOW_THRESHOLD,
            evidence=[evidence],
        )
        run_result = RunResult(
            overall=TrafficLight.RED,
            summary="Hard KO detected; disqualification likely.",
            results=[check_result],
        )
        pack = EvidencePack(run_result=run_result)

        d = pack.to_dict()
        assert isinstance(d, dict)
        checks = d.get("checks")
        assert isinstance(checks, list)
        assert checks

        assert d["schema_version"] == "1.0"
        assert d["verdict"] == "red"
        assert d["overall_verdict"] == "red"
        assert d["summary"] == "Hard KO detected; disqualification likely."
        assert len(checks) == 1

        check = checks[0]
        assert check["check_id"] == "TurnoverThresholdChecker"
        assert check["verdict"] == "red"
        assert check["reason"] == "below_threshold"
        assert len(check["evidence"]) == 1

        ev = check["evidence"][0]
        assert ev["doc_id"] == "tender.pdf"
        assert ev["page"] == 3
        assert ev["snippet"] == "Mindestumsatz 500.000 EUR erforderlich"

    def test_json_serializable(self):
        """Evidence pack dict is JSON serializable (no dataclass/enum remnants)."""
        run_result = RunResult(
            overall=TrafficLight.GREEN,
            summary="No KO signal detected.",
            results=[],
        )
        pack = EvidencePack(run_result=run_result)

        json_str = json.dumps(pack.to_dict())
        assert '"schema_version": "1.0"' in json_str
        assert '"verdict": "green"' in json_str
        assert '"overall_verdict": "green"' in json_str

    def test_optional_fields_included_when_present(self):
        """Optional fields (offsets, bbox) appear when populated."""
        evidence = EvidenceSpan(
            doc_id="doc.pdf",
            page_number=1,
            snippet="Test snippet",
            start_offset=100,
            end_offset=115,
            paragraph_index=2,
            bbox={"x0": 0.1, "y0": 0.2, "x1": 0.9, "y1": 0.3},
        )
        check_result = CheckerResult(
            checker_name="TestChecker",
            status=TrafficLight.YELLOW,
            reason=ReasonCode.KO_PHRASE_FOUND,
            evidence=[evidence],
        )
        run_result = RunResult(
            overall=TrafficLight.YELLOW,
            summary="Possible KO signal detected.",
            results=[check_result],
        )
        pack = EvidencePack(run_result=run_result)
        d = pack.to_dict()
        checks = d.get("checks")
        assert isinstance(checks, list)

        ev = checks[0]["evidence"][0]
        assert ev["start_offset"] == 100
        assert ev["end_offset"] == 115
        assert ev["paragraph_index"] == 2
        assert ev["bbox"] == {"x0": 0.1, "y0": 0.2, "x1": 0.9, "y1": 0.3}

    def test_optional_fields_omitted_when_none(self):
        """Optional fields (offsets, bbox) are omitted when None (clean JSON)."""
        evidence = EvidenceSpan(
            doc_id="doc.pdf",
            page_number=1,
            snippet="Test snippet",
        )
        check_result = CheckerResult(
            checker_name="TestChecker",
            status=TrafficLight.YELLOW,
            reason=ReasonCode.KO_PHRASE_FOUND,
            evidence=[evidence],
        )
        run_result = RunResult(
            overall=TrafficLight.YELLOW,
            summary="Possible KO signal detected.",
            results=[check_result],
        )
        pack = EvidencePack(run_result=run_result)
        d = pack.to_dict()
        checks = d.get("checks")
        assert isinstance(checks, list)

        ev = checks[0]["evidence"][0]
        assert "start_offset" not in ev
        assert "end_offset" not in ev
        assert "paragraph_index" not in ev
        assert "bbox" not in ev


class TestEvidencePackInvariants:
    """Adversarial tests enforcing no-evidence-no-claim rule."""

    def test_adversarial_non_neutral_without_evidence_rejected(self):
        """ADVERSARIAL: Non-neutral verdict without evidence is impossible."""
        with pytest.raises(ValueError, match="requires non-empty evidence"):
            CheckerResult(
                checker_name="FakeChecker",
                status=TrafficLight.RED,
                reason=ReasonCode.BELOW_THRESHOLD,
                evidence=[],
            )

        with pytest.raises(ValueError, match="requires non-empty evidence"):
            CheckerResult(
                checker_name="FakeChecker",
                status=TrafficLight.YELLOW,
                reason=ReasonCode.KO_PHRASE_FOUND,
                evidence=[],
            )

        with pytest.raises(ValueError, match="requires non-empty evidence"):
            CheckerResult(
                checker_name="FakeChecker",
                status=TrafficLight.ABSTAIN,
                reason=ReasonCode.NO_TEXT,
                evidence=[],
            )

    def test_adversarial_empty_snippet_rejected(self):
        """ADVERSARIAL: Non-neutral verdict with empty snippet is rejected."""
        with pytest.raises(ValueError, match="requires non-empty snippet"):
            CheckerResult(
                checker_name="FakeChecker",
                status=TrafficLight.RED,
                reason=ReasonCode.BELOW_THRESHOLD,
                evidence=[EvidenceSpan(doc_id="doc.pdf", page_number=1, snippet="")],
            )

        with pytest.raises(ValueError, match="requires non-empty snippet"):
            CheckerResult(
                checker_name="FakeChecker",
                status=TrafficLight.YELLOW,
                reason=ReasonCode.KO_PHRASE_FOUND,
                evidence=[EvidenceSpan(doc_id="doc.pdf", page_number=1, snippet="   ")],
            )

    def test_abstain_has_meta_evidence(self):
        """ADVERSARIAL: ABSTAIN includes meta-evidence span."""
        pack = make_evidence_pack(
            text=None,
            doc_id="doc.pdf",
            page_number=1,
            company_profile={"annual_turnover_eur": 1_000_000},
        )
        d = pack.to_dict()
        checks = d.get("checks")
        assert isinstance(checks, list)
        assert d["overall_verdict"] == "abstain"
        assert checks
        for check in checks:
            assert check["evidence"]
            assert check["evidence"][0]["snippet"].startswith("(no text)")


class TestMakeEvidencePack:
    """Tests for make_evidence_pack() convenience function."""

    def test_make_evidence_pack_requires_doc_metadata(self):
        with pytest.raises(TypeError):
            make_evidence_pack("Der Mindestumsatz beträgt 500.000 EUR.")  # type: ignore[call-arg]

    def test_make_evidence_pack_returns_pack(self):
        """make_evidence_pack returns EvidencePack with correct structure."""
        pack = make_evidence_pack(
            text="Der Mindestumsatz beträgt 500.000 EUR.",
            doc_id="tender.pdf",
            page_number=5,
            company_profile={"annual_turnover_eur": 400_000},
        )

        assert isinstance(pack, EvidencePack)
        d = pack.to_dict()
        checks = d.get("checks")
        assert isinstance(checks, list)

        assert d["verdict"] == "red"  # Below threshold
        assert d["overall_verdict"] == "red"
        assert d["schema_version"] == "1.0"
        assert len(checks) >= 1

        turnover_checks = [c for c in checks if c["check_id"] == "TurnoverThresholdChecker"]
        assert len(turnover_checks) == 1
        assert turnover_checks[0]["verdict"] == "red"
        assert turnover_checks[0]["evidence"][0]["doc_id"] == "tender.pdf"
        assert turnover_checks[0]["evidence"][0]["page"] == 5

    def test_make_evidence_pack_green_has_empty_checks(self):
        """GREEN verdict has empty checks list (no signals detected)."""
        pack = make_evidence_pack(
            text="Bitte reichen Sie Ihre Unterlagen ein.",
            doc_id="doc.pdf",
            page_number=1,
            company_profile={"annual_turnover_eur": 1_000_000},
        )

        d = pack.to_dict()
        checks = d.get("checks")
        assert isinstance(checks, list)
        assert d["verdict"] == "green"
        assert d["overall_verdict"] == "green"
        assert checks == []

    def test_make_evidence_pack_multiple_checks(self):
        """Evidence pack contains results from multiple checkers."""
        pack = make_evidence_pack(
            text="Ausschlusskriterium: Der Mindestumsatz beträgt 500.000 EUR.",
            doc_id="multi.pdf",
            page_number=2,
            company_profile={"annual_turnover_eur": 400_000},
        )

        d = pack.to_dict()
        checks = d.get("checks")
        assert isinstance(checks, list)
        assert d["verdict"] == "red"  # RED takes precedence
        assert d["overall_verdict"] == "red"

        check_ids = {c["check_id"] for c in checks}
        assert "MinimalKoPhraseChecker" in check_ids
        assert "TurnoverThresholdChecker" in check_ids

        for check in checks:
            assert len(check["evidence"]) >= 1
            assert check["evidence"][0]["doc_id"] == "multi.pdf"
            assert check["evidence"][0]["page"] == 2
