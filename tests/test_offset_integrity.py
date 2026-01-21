"""MC-KOS-37: Offset integrity suite (repo-wide guardrail).

Tests: 3 including 1 adversarial per Sniper process rules.
"""

import pytest
from typing import cast

from kosniper.contracts import EvidenceSpan, CheckerResult


def assert_offset_integrity(result: CheckerResult, normalized_text: str) -> None:
    """Assert offset integrity for all evidence in a CheckerResult.

    Validates:
    - If offsets present: offset_basis == "normalized_text_v1"
    - If offsets present: 0 <= start < end <= len(normalized_text)
    - If offsets present: normalized_text[start:end] is non-empty
    - If offsets present: snippet contains the matched substring
    """
    for ev in result.evidence:
        if ev.start_offset is not None or ev.end_offset is not None:
            # Both must be present (EvidenceSpan invariant)
            assert ev.start_offset is not None, "start_offset missing but end_offset present"
            assert ev.end_offset is not None, "end_offset missing but start_offset present"

            # offset_basis must be normalized_text_v1
            assert ev.offset_basis == "normalized_text_v1", (
                f"offset_basis must be 'normalized_text_v1', got {ev.offset_basis!r}"
            )

            # Valid range
            assert 0 <= ev.start_offset < ev.end_offset <= len(normalized_text), (
                f"Invalid offset range: [{ev.start_offset}:{ev.end_offset}] "
                f"for text of length {len(normalized_text)}"
            )

            # Matched substring is non-empty and in snippet
            matched = normalized_text[ev.start_offset:ev.end_offset]
            assert matched, "Matched substring is empty"
            assert matched.lower() in ev.snippet.lower(), (
                f"Matched substring {matched!r} not found in snippet {ev.snippet!r}"
            )


class TestOffsetIntegrity:
    """Offset integrity guardrail tests."""

    def test_ko_keyword_checker_offset_integrity(self):
        """KoKeywordChecker RED result evidence passes offset integrity."""
        from kosniper.checkers.ko_keyword_check import KoKeywordChecker

        checker = KoKeywordChecker()
        text = "Dies sind Ausschlusskriterien für die Vergabe."

        result = checker.run(text=text, doc_id="test.pdf", page_number=1)

        assert result is not None
        assert result.status.value == "red"
        normalize = getattr(checker, "_normalize_text", None)
        normalized = normalize(text) if callable(normalize) else text
        if not isinstance(normalized, str):
            normalized = text
        assert_offset_integrity(result, cast(str, normalized))

    def test_turnover_checker_offset_integrity(self):
        """TurnoverThresholdChecker result evidence passes offset integrity."""
        from kosniper.checkers.turnover_threshold import TurnoverThresholdChecker

        checker = TurnoverThresholdChecker()
        text = "Der Mindestumsatz beträgt 500.000 EUR."
        company_profile = {"annual_turnover_eur": 400_000}

        result = checker.run(
            text=text,
            doc_id="test.pdf",
            page_number=1,
            company_profile=company_profile,
        )

        assert result is not None
        assert result.status.value == "red"
        # Use normalized text for validation
        normalized = checker._normalize_text(text)
        assert_offset_integrity(result, normalized)

    def test_adversarial_offsets_without_basis_fails(self):
        """ADVERSARIAL: EvidenceSpan with offsets but no offset_basis raises."""
        with pytest.raises(ValueError, match="offset_basis"):
            EvidenceSpan(
                doc_id="test.pdf",
                page_number=1,
                snippet="test snippet",
                start_offset=0,
                end_offset=10,
                # offset_basis intentionally omitted
            )
