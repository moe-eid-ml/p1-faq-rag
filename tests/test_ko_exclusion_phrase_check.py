"""MC-KOS-32: Exclusion phrase checker tests (minimal suite).

Tests for regex-based exclusion phrase detection.
Tests: 2 including 1 adversarial per Sniper process rules.
"""

from kosniper.checkers.ko_exclusion_phrase_check import KoExclusionPhraseChecker
from kosniper.contracts import TrafficLight


class TestKoExclusionPhraseChecker:
    """Minimal exclusion phrase checker test suite."""

    def test_found_returns_red_with_evidence(self):
        """Exclusion phrase found returns RED with valid evidence."""
        checker = KoExclusionPhraseChecker()
        text = "Bei Nichtbeachtung erfolgt Ausschluss vom Verfahren."

        result = checker.run(text=text, doc_id="tender.pdf", page_number=1)

        assert result is not None
        assert result.status == TrafficLight.RED
        assert len(result.evidence) > 0
        assert "Ausschluss" in result.evidence[0].snippet
        assert result.evidence[0].offset_basis == "normalized_text_v1"
        assert result.evidence[0].start_offset is not None
        assert result.evidence[0].end_offset is not None

    def test_adversarial_not_found_returns_none(self):
        """ADVERSARIAL: No exclusion phrase returns None; no crash."""
        checker = KoExclusionPhraseChecker()
        # Text without exclusion patterns (just neutral mention)
        text = "Der Bieter muss die Anforderungen erfuellen."

        result = checker.run(text=text, doc_id="tender.pdf", page_number=1)

        assert result is None
