"""MC-KOS-21: Tests for overall verdict worst-case invariant.

Verifies:
1) worst_verdict helper computes correct ordering
2) RunResult.overall must equal worst of check verdicts
3) Adversarial: mismatched overall raises ValueError
"""

import pytest

from kosniper.contracts import (
    CheckerResult,
    EvidenceSpan,
    ReasonCode,
    RunResult,
    TrafficLight,
    worst_verdict,
)


class TestWorstVerdictHelper:
    """Tests for worst_verdict() helper function."""

    def test_empty_list_returns_green(self):
        """Empty list returns GREEN (no signals = green)."""
        assert worst_verdict([]) == TrafficLight.GREEN

    def test_single_red_returns_red(self):
        """Single RED returns RED."""
        assert worst_verdict([TrafficLight.RED]) == TrafficLight.RED

    def test_single_green_returns_green(self):
        """Single GREEN returns GREEN."""
        assert worst_verdict([TrafficLight.GREEN]) == TrafficLight.GREEN

    def test_red_beats_yellow(self):
        """RED is worse than YELLOW."""
        assert worst_verdict([TrafficLight.YELLOW, TrafficLight.RED]) == TrafficLight.RED

    def test_yellow_beats_abstain(self):
        """YELLOW is worse than ABSTAIN."""
        assert worst_verdict([TrafficLight.ABSTAIN, TrafficLight.YELLOW]) == TrafficLight.YELLOW

    def test_abstain_beats_green(self):
        """ABSTAIN is worse than GREEN."""
        assert worst_verdict([TrafficLight.GREEN, TrafficLight.ABSTAIN]) == TrafficLight.ABSTAIN

    def test_full_ordering(self):
        """Full ordering: red > yellow > abstain > green."""
        all_verdicts = [
            TrafficLight.GREEN,
            TrafficLight.ABSTAIN,
            TrafficLight.YELLOW,
            TrafficLight.RED,
        ]
        assert worst_verdict(all_verdicts) == TrafficLight.RED

    def test_multiple_same_verdict(self):
        """Multiple same verdicts return that verdict."""
        assert worst_verdict([TrafficLight.YELLOW, TrafficLight.YELLOW]) == TrafficLight.YELLOW


class TestRunResultWorstVerdictInvariant:
    """Tests for RunResult overall verdict invariant."""

    def _make_evidence(self, doc_id: str = "doc.pdf") -> EvidenceSpan:
        """Helper to create valid evidence span."""
        return EvidenceSpan(doc_id=doc_id, page_number=1, snippet="test snippet")

    def test_single_red_check_requires_red_overall(self):
        """Single RED check requires RED overall."""
        check = CheckerResult(
            checker_name="Test",
            status=TrafficLight.RED,
            reason=ReasonCode.BELOW_THRESHOLD,
            evidence=[self._make_evidence()],
        )
        result = RunResult(
            overall=TrafficLight.RED,
            summary="Red detected",
            results=[check],
        )
        assert result.overall == TrafficLight.RED

    def test_mixed_yellow_abstain_requires_yellow_overall(self):
        """Mixed YELLOW + ABSTAIN requires YELLOW overall."""
        checks = [
            CheckerResult(
                checker_name="YellowChecker",
                status=TrafficLight.YELLOW,
                reason=ReasonCode.KO_PHRASE_FOUND,
                evidence=[self._make_evidence()],
            ),
            CheckerResult(
                checker_name="AbstainChecker",
                status=TrafficLight.ABSTAIN,
                reason=ReasonCode.NO_TEXT,
                evidence=[self._make_evidence()],
            ),
        ]
        result = RunResult(
            overall=TrafficLight.YELLOW,
            summary="Yellow worst",
            results=checks,
        )
        assert result.overall == TrafficLight.YELLOW

    def test_empty_checks_allows_green_overall(self):
        """Empty checks list allows GREEN overall (no signals)."""
        result = RunResult(
            overall=TrafficLight.GREEN,
            summary="No signals",
            results=[],
        )
        assert result.overall == TrafficLight.GREEN


class TestRunResultWorstVerdictAdversarial:
    """Adversarial tests for overall verdict invariant."""

    def _make_evidence(self) -> EvidenceSpan:
        return EvidenceSpan(doc_id="doc.pdf", page_number=1, snippet="test snippet")

    def test_adversarial_green_overall_with_red_check_rejected(self):
        """ADVERSARIAL: GREEN overall with RED check must raise ValueError."""
        red_check = CheckerResult(
            checker_name="RedChecker",
            status=TrafficLight.RED,
            reason=ReasonCode.BELOW_THRESHOLD,
            evidence=[self._make_evidence()],
        )
        with pytest.raises(ValueError, match="must equal worst verdict"):
            RunResult(
                overall=TrafficLight.GREEN,
                summary="Invalid",
                results=[red_check],
            )

    def test_adversarial_green_overall_with_yellow_check_rejected(self):
        """ADVERSARIAL: GREEN overall with YELLOW check must raise ValueError."""
        yellow_check = CheckerResult(
            checker_name="YellowChecker",
            status=TrafficLight.YELLOW,
            reason=ReasonCode.KO_PHRASE_FOUND,
            evidence=[self._make_evidence()],
        )
        with pytest.raises(ValueError, match="must equal worst verdict"):
            RunResult(
                overall=TrafficLight.GREEN,
                summary="Invalid",
                results=[yellow_check],
            )

    def test_adversarial_yellow_overall_with_red_check_rejected(self):
        """ADVERSARIAL: YELLOW overall with RED check must raise ValueError."""
        red_check = CheckerResult(
            checker_name="RedChecker",
            status=TrafficLight.RED,
            reason=ReasonCode.BELOW_THRESHOLD,
            evidence=[self._make_evidence()],
        )
        with pytest.raises(ValueError, match="must equal worst verdict"):
            RunResult(
                overall=TrafficLight.YELLOW,
                summary="Invalid",
                results=[red_check],
            )

    def test_adversarial_abstain_overall_with_yellow_check_rejected(self):
        """ADVERSARIAL: ABSTAIN overall with YELLOW check must raise ValueError."""
        yellow_check = CheckerResult(
            checker_name="YellowChecker",
            status=TrafficLight.YELLOW,
            reason=ReasonCode.KO_PHRASE_FOUND,
            evidence=[self._make_evidence()],
        )
        with pytest.raises(ValueError, match="must equal worst verdict"):
            RunResult(
                overall=TrafficLight.ABSTAIN,
                summary="Invalid",
                results=[yellow_check],
            )
