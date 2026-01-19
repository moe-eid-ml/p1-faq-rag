"""MC-KOS-29: KO keyword checker tests (minimal suite).

Tests for deterministic KO keyword detection with evidence spans.
Tests: 2 including 1 adversarial per Sniper process rules.
"""

from kosniper.checkers.ko_keyword_check import KoKeywordChecker
from kosniper.contracts import TrafficLight


class TestKoKeywordChecker:
    """Minimal KO keyword checker test suite."""

    def test_found_returns_red_with_evidence(self):
        """Happy path: KO keyword found returns RED with valid evidence."""
        checker = KoKeywordChecker()
        # Use "Ausschlusskriterien" (plural) which is in KO_KEYWORDS
        text = "Die folgenden Ausschlusskriterien gelten für alle Bieter."

        result = checker.run(text=text, doc_id="tender.pdf", page_number=1)

        assert result is not None
        assert result.status == TrafficLight.RED
        assert len(result.evidence) > 0
        assert "Ausschlusskriterien" in result.evidence[0].snippet
        assert result.evidence[0].offset_basis == "normalized_text_v1"
        assert result.evidence[0].start_offset is not None
        assert result.evidence[0].end_offset is not None

    def test_adversarial_not_found_returns_none(self):
        """ADVERSARIAL: No KO keyword returns None (no finding); no crash."""
        checker = KoKeywordChecker()
        text = "Der Bieter muss die Anforderungen erfüllen."

        result = checker.run(text=text, doc_id="tender.pdf", page_number=1)

        # Returns None when not found (no finding to report)
        assert result is None
