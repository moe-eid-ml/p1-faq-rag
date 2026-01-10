"""MC-KOS-05: Tests for checker interface alignment."""

from kosniper.checkers import MinimalKoPhraseChecker, TurnoverThresholdChecker, DemoKoPhraseChecker
from kosniper.contracts import CheckerResult


class TestCheckerInterface:
    """Verify all checkers return Optional[CheckerResult] (None or CheckerResult instance)."""

    def test_minimal_ko_phrase_checker_returns_valid_type(self):
        """MinimalKoPhraseChecker.run() returns None or CheckerResult."""
        checker = MinimalKoPhraseChecker()

        # With trigger phrase -> should return CheckerResult
        result_with_phrase = checker.run(
            text="Dies ist ein Ausschlusskriterium.",
            doc_id="test.pdf",
            page_number=1,
        )
        assert result_with_phrase is None or isinstance(result_with_phrase, CheckerResult)

        # Without trigger phrase -> should return None
        result_no_phrase = checker.run(
            text="Normale Ausschreibung ohne besondere Kriterien.",
            doc_id="test.pdf",
            page_number=1,
        )
        assert result_no_phrase is None or isinstance(result_no_phrase, CheckerResult)

    def test_demo_ko_phrase_checker_returns_valid_type(self):
        """DemoKoPhraseChecker.run() returns None or CheckerResult."""
        checker = DemoKoPhraseChecker()

        # With trigger phrase
        result_with_phrase = checker.run(
            text="Dies ist ein Ausschlusskriterium.",
            doc_id="test.pdf",
            page_number=1,
        )
        assert result_with_phrase is None or isinstance(result_with_phrase, CheckerResult)

        # Without trigger phrase
        result_no_phrase = checker.run(
            text="Normale Ausschreibung.",
            doc_id="test.pdf",
            page_number=1,
        )
        assert result_no_phrase is None or isinstance(result_no_phrase, CheckerResult)

    def test_turnover_threshold_checker_returns_valid_type(self):
        """TurnoverThresholdChecker.run() returns None or CheckerResult."""
        checker = TurnoverThresholdChecker()

        # With turnover requirement, company below
        result_below = checker.run(
            text="Mindestumsatz: 500.000 EUR",
            doc_id="test.pdf",
            page_number=1,
            company_profile={"annual_turnover_eur": 400_000},
        )
        assert result_below is None or isinstance(result_below, CheckerResult)

        # With turnover requirement, company meets
        result_meets = checker.run(
            text="Mindestumsatz: 500.000 EUR",
            doc_id="test.pdf",
            page_number=1,
            company_profile={"annual_turnover_eur": 600_000},
        )
        assert result_meets is None or isinstance(result_meets, CheckerResult)

        # No turnover requirement
        result_none = checker.run(
            text="Bitte reichen Sie Ihre Unterlagen ein.",
            doc_id="test.pdf",
            page_number=1,
            company_profile={"annual_turnover_eur": 1_000_000},
        )
        assert result_none is None or isinstance(result_none, CheckerResult)

    def test_minimal_ko_phrase_checker_empty_text_returns_valid_type(self):
        """MinimalKoPhraseChecker with empty text returns None or CheckerResult."""
        checker = MinimalKoPhraseChecker()
        result = checker.run(text="", doc_id="test.pdf", page_number=1)
        assert result is None or isinstance(result, CheckerResult)

    def test_turnover_checker_empty_text_returns_valid_type(self):
        """TurnoverThresholdChecker with empty text returns None or CheckerResult."""
        checker = TurnoverThresholdChecker()
        result = checker.run(
            text="",
            doc_id="test.pdf",
            page_number=1,
            company_profile={"annual_turnover_eur": 1_000_000},
        )
        assert result is None or isinstance(result, CheckerResult)
