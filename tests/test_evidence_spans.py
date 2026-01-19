"""MC-KOS-28: Evidence span finder tests (minimal suite).

Tests for deterministic substring/regex finding with offset tracking.
Tests: 2-5 including 1 adversarial per Sniper process rules.
"""

from kosniper.evidence.spans import find_span, find_span_regex, make_snippet


class TestEvidenceSpans:
    """Minimal evidence span finder test suite."""

    def test_find_span_returns_correct_offsets_and_snippet(self):
        """Happy path: find_span returns correct offsets and snippet contains needle."""
        text = "Der Mindestumsatz beträgt 500.000 EUR."
        result = find_span(text, "mindestumsatz")

        assert result is not None
        assert result["start"] == 4
        assert result["end"] == 17
        assert result["offset_basis"] == "normalized_text_v1"
        assert "Mindestumsatz" in result["snippet"]
        # Verify slice matches (case-insensitive search, original case in text)
        assert text[result["start"]:result["end"]] == "Mindestumsatz"

    def test_find_span_regex_returns_correct_offsets(self):
        """Regex path: find_span_regex finds pattern and returns offsets."""
        text = "Jahresumsatz: 500.000 EUR erforderlich"
        result = find_span_regex(text, r"\d+\.\d+\s+EUR")

        assert result is not None
        assert result["offset_basis"] == "normalized_text_v1"
        assert "500.000 EUR" in result["snippet"]
        # Verify slice matches
        matched = text[result["start"]:result["end"]]
        assert matched == "500.000 EUR"

    def test_adversarial_needle_not_found_returns_none(self):
        """ADVERSARIAL: needle not found returns None, no exception."""
        text = "Der Bieter muss die Anforderungen erfüllen."

        assert find_span(text, "Ausschlusskriterium") is None
        assert find_span_regex(text, r"XYZ\d+") is None
        assert find_span("", "test") is None
        assert find_span(text, "") is None

    def test_make_snippet_respects_window(self):
        """Snippet extraction respects window size."""
        text = "A" * 100 + "NEEDLE" + "B" * 100
        snippet = make_snippet(text, 100, 106, window=10)

        assert len(snippet) == 26  # 10 + 6 + 10
        assert "NEEDLE" in snippet
        assert snippet.startswith("A" * 10)
        assert snippet.endswith("B" * 10)
