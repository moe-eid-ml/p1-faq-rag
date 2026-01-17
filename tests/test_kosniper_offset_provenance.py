"""MC-KOS-15: Tests for offset provenance in evidence spans.

Tests verify:
1) Checker populates start_offset/end_offset for matches
2) Offsets are within bounds and slice contains matched phrase
3) Adversarial: proof-first invariants still hold
"""

import pytest

from kosniper.checkers.minimal_ko_phrase import MinimalKoPhraseChecker
from kosniper.contracts import CheckerResult, EvidenceSpan, ReasonCode, TrafficLight


@pytest.fixture
def checker():
    return MinimalKoPhraseChecker()


class TestOffsetProvenance:
    """Tests that checker populates offset fields correctly."""

    def test_ko_phrase_has_offsets(self, checker):
        """Matched phrase includes start_offset and end_offset in evidence."""
        text = "Dies ist ein Ausschlusskriterium für Bieter."
        result = checker.run(text=text, doc_id="doc.pdf", page_number=1)

        assert result is not None
        assert result.status == TrafficLight.YELLOW
        assert len(result.evidence) == 1

        ev = result.evidence[0]
        assert ev.start_offset is not None
        assert ev.end_offset is not None
        assert ev.start_offset < ev.end_offset

    def test_offsets_within_bounds(self, checker):
        """Offsets are within text bounds (0 <= start < end <= len)."""
        text = "Der Mindestumsatz beträgt 500.000 EUR."
        result = checker.run(text=text, doc_id="doc.pdf", page_number=1)

        assert result is not None
        ev = result.evidence[0]

        # Offsets are on normalized text, get normalized length
        normalized = checker._normalize(text)
        assert ev.start_offset >= 0
        assert ev.end_offset <= len(normalized)
        assert ev.start_offset < ev.end_offset

    def test_offset_slice_contains_phrase(self, checker):
        """text[start:end] contains the matched trigger phrase."""
        text = "Der Jahresumsatz der letzten drei Jahre ist relevant."
        result = checker.run(text=text, doc_id="doc.pdf", page_number=1)

        assert result is not None
        ev = result.evidence[0]

        normalized = checker._normalize(text)
        sliced = normalized[ev.start_offset:ev.end_offset].lower()
        assert sliced in [p.lower() for p in checker.TRIGGER_PHRASES]

    def test_multiple_phrases_offset_accurate(self, checker):
        """First matched phrase offset is accurate."""
        text = "Ausschlusskriterium: Der Mindestumsatz beträgt 500.000 EUR."
        result = checker.run(text=text, doc_id="doc.pdf", page_number=1)

        assert result is not None
        ev = result.evidence[0]

        normalized = checker._normalize(text)
        sliced = normalized[ev.start_offset:ev.end_offset].lower()
        # First trigger phrase matched should be "ausschlusskriterium"
        assert sliced == "ausschlusskriterium"


class TestOffsetEdgeCases:
    """Edge cases for offset computation."""

    def test_phrase_at_start(self, checker):
        """Phrase at text start has offset 0."""
        text = "Ausschlusskriterium am Anfang."
        result = checker.run(text=text, doc_id="doc.pdf", page_number=1)

        assert result is not None
        ev = result.evidence[0]
        assert ev.start_offset == 0

    def test_phrase_at_end(self, checker):
        """Phrase at text end has correct end_offset."""
        text = "Dies ist ein Ausschlusskriterium"
        result = checker.run(text=text, doc_id="doc.pdf", page_number=1)

        assert result is not None
        ev = result.evidence[0]

        normalized = checker._normalize(text)
        assert ev.end_offset == len(normalized)

    def test_hyphenated_phrase_offset(self, checker):
        """Hyphenated phrase (normalized) has correct offsets."""
        text = "Der Mindest-\numsatz beträgt 500.000 EUR."
        result = checker.run(text=text, doc_id="doc.pdf", page_number=1)

        assert result is not None
        ev = result.evidence[0]

        # After normalization, hyphenation is removed
        normalized = checker._normalize(text)
        sliced = normalized[ev.start_offset:ev.end_offset].lower()
        assert sliced == "mindestumsatz"


class TestOffsetAdversarial:
    """Adversarial tests: proof-first invariants with offsets."""

    def test_adversarial_empty_evidence_not_green(self):
        """ADVERSARIAL: Non-green verdict still requires evidence (no regression)."""
        with pytest.raises(ValueError, match="requires non-empty evidence"):
            CheckerResult(
                checker_name="FakeChecker",
                status=TrafficLight.YELLOW,
                reason=ReasonCode.KO_PHRASE_FOUND,
                evidence=[],
            )

    def test_adversarial_offset_pair_invariant(self):
        """ADVERSARIAL: start_offset without end_offset is rejected."""
        with pytest.raises(ValueError, match="start_offset and end_offset"):
            EvidenceSpan(
                doc_id="doc.pdf",
                page_number=1,
                snippet="test",
                start_offset=10,
                end_offset=None,
            )

        with pytest.raises(ValueError, match="start_offset and end_offset"):
            EvidenceSpan(
                doc_id="doc.pdf",
                page_number=1,
                snippet="test",
                start_offset=None,
                end_offset=20,
            )

    def test_adversarial_no_text_still_abstains(self, checker):
        """ADVERSARIAL: Empty text still produces ABSTAIN (no false-green)."""
        result = checker.run(text="", doc_id="doc.pdf", page_number=1)

        assert result is not None
        assert result.status == TrafficLight.ABSTAIN
        assert result.reason == ReasonCode.NO_TEXT
        # No offsets for abstain case (no match)
        ev = result.evidence[0]
        assert ev.start_offset is None
        assert ev.end_offset is None
