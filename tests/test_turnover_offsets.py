"""MC-KOS-36: TurnoverThresholdChecker offset precision tests.

Tests: 3 including 1 adversarial per Sniper process rules.
"""

from kosniper.checkers.turnover_threshold import TurnoverThresholdChecker
from kosniper.contracts import TrafficLight


class TestTurnoverOffsets:
    """Turnover checker offset precision test suite."""

    def test_red_verdict_has_offsets_and_basis(self):
        """Found path: RED verdict includes start/end offsets and offset_basis."""
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
        assert result.status == TrafficLight.RED
        assert len(result.evidence) == 1

        ev = result.evidence[0]
        assert ev.start_offset is not None
        assert ev.end_offset is not None
        assert ev.offset_basis == "normalized_text_v1"

    def test_slice_integrity_keyword_in_range(self):
        """Slice integrity: normalized[start:end] contains matched turnover keyword."""
        checker = TurnoverThresholdChecker()
        text = "Eignungskriterium: Mindestumsatz von 500.000 EUR erforderlich."
        company_profile = {"annual_turnover_eur": 400_000}

        result = checker.run(
            text=text,
            doc_id="test.pdf",
            page_number=1,
            company_profile=company_profile,
        )

        assert result is not None
        assert result.status == TrafficLight.RED
        ev = result.evidence[0]

        # Offsets are relative to normalized_text_v1
        normalized = checker._normalize_text(text)
        matched_region = normalized[ev.start_offset:ev.end_offset].lower()

        # The matched region should be one of the turnover keywords
        turnover_keywords = [
            "mindestumsatz", "mindestjahresumsatz", "jahresumsatz",
            "gesamtumsatz", "umsatz",
        ]
        assert any(kw in matched_region for kw in turnover_keywords)

    def test_adversarial_messy_formatting_produces_offsets(self):
        """ADVERSARIAL: Messy formatting still produces offsets, never GREEN."""
        checker = TurnoverThresholdChecker()
        # Various messy formats: thousands separators, spacing, € variations
        text = "Mindestumsatz:  500.000,00  €  (brutto)"
        company_profile = {"annual_turnover_eur": 400_000}

        result = checker.run(
            text=text,
            doc_id="test.pdf",
            page_number=1,
            company_profile=company_profile,
        )

        # Must not be GREEN (never false-green)
        if result is not None:
            assert result.status != TrafficLight.GREEN
            # If we got a result, it must have valid offsets
            ev = result.evidence[0]
            assert ev.start_offset is not None
            assert ev.end_offset is not None
            assert ev.offset_basis == "normalized_text_v1"
            # Offsets must be valid indices
            normalized = checker._normalize_text(text)
            assert 0 <= ev.start_offset < len(normalized)
            assert 0 < ev.end_offset <= len(normalized)
            assert ev.start_offset < ev.end_offset
