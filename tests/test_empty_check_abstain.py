"""MC-KOS-33: Forbid empty-check GREEN tests (minimal suite).

Tests for never-false-green when no checker produces findings.
Tests: 2 including 1 adversarial per Sniper process rules.
"""

from kosniper.contracts import TrafficLight
from kosniper.pipeline import run_single_page


class TestEmptyCheckAbstain:
    """Empty check results must yield ABSTAIN, not GREEN."""

    def test_no_findings_yields_abstain_not_green(self):
        """No findings from any checker => ABSTAIN (never false-green)."""
        # Text that triggers no checker
        result = run_single_page(
            text="Bitte reichen Sie Ihre Unterlagen ein.",
            doc_id="doc.pdf",
            page_number=1,
        )

        assert result.overall == TrafficLight.ABSTAIN
        assert result.overall != TrafficLight.GREEN
        assert result.results == []

    def test_adversarial_explicit_verdicts_unchanged(self):
        """ADVERSARIAL: Explicit checker verdicts remain unchanged."""
        # Text that triggers MinimalKoPhraseChecker (YELLOW)
        result_yellow = run_single_page(
            text="Dies ist ein Ausschlusskriterium.",
            doc_id="doc.pdf",
            page_number=1,
        )
        assert result_yellow.overall == TrafficLight.YELLOW

        # Text that triggers ABSTAIN from checkers (empty text)
        result_abstain = run_single_page(
            text="",
            doc_id="doc.pdf",
            page_number=1,
        )
        assert result_abstain.overall == TrafficLight.ABSTAIN
