"""MC-KOS-04: Tests for pipeline wiring with both checkers."""

from kosniper.pipeline import run_single_page
from kosniper.contracts import TrafficLight


class TestTurnoverCheckerWiring:
    """Test TurnoverThresholdChecker integration into pipeline."""

    def test_turnover_below_threshold_yields_red(self):
        """AC1: Turnover below threshold => overall RED."""
        text = "Der Mindestumsatz beträgt 500.000 EUR."
        company_profile = {"annual_turnover_eur": 400_000}
        result = run_single_page(text, "doc.pdf", 1, company_profile)
        assert result.overall == TrafficLight.RED
        # Should have turnover checker result with below_threshold
        turnover_results = [r for r in result.results if r.checker_name == "TurnoverThresholdChecker"]
        assert len(turnover_results) == 1
        assert turnover_results[0].reason == "below_threshold"

    def test_turnover_missing_company_profile_yields_yellow(self):
        """AC2: Turnover requirement exists but company profile missing => YELLOW."""
        text = "Der Mindestumsatz beträgt 500.000 EUR."
        result = run_single_page(text, "doc.pdf", 1, company_profile=None)
        assert result.overall == TrafficLight.YELLOW
        # Should have turnover checker result with missing_company_turnover
        turnover_results = [r for r in result.results if r.checker_name == "TurnoverThresholdChecker"]
        assert len(turnover_results) == 1
        assert turnover_results[0].reason == "missing_company_turnover"

    def test_no_ko_signals_yields_green(self):
        """AC3: No turnover phrase and no KO phrase => overall GREEN."""
        text = "Bitte reichen Sie Ihre Unterlagen vollständig ein."
        company_profile = {"annual_turnover_eur": 1_000_000}
        result = run_single_page(text, "doc.pdf", 1, company_profile)
        assert result.overall == TrafficLight.GREEN
        # No findings from either checker
        assert len(result.results) == 0

    def test_empty_text_yields_abstain(self):
        """AC4: Empty/None text => overall ABSTAIN."""
        result = run_single_page("", "doc.pdf", 1, {"annual_turnover_eur": 1_000_000})
        assert result.overall == TrafficLight.ABSTAIN

    def test_none_text_yields_abstain(self):
        """AC4: None text => overall ABSTAIN."""
        result = run_single_page(None, "doc.pdf", 1, {"annual_turnover_eur": 1_000_000})
        assert result.overall == TrafficLight.ABSTAIN


class TestBothCheckersRun:
    """Test that both checkers run and results are aggregated."""

    def test_phrase_and_turnover_both_detected(self):
        """Both phrase checker and turnover checker detect something."""
        # Text with both KO phrase and turnover requirement
        text = "Ausschlusskriterium: Der Mindestumsatz beträgt 500.000 EUR."
        company_profile = {"annual_turnover_eur": 400_000}
        result = run_single_page(text, "doc.pdf", 1, company_profile)
        # RED from turnover (below threshold) takes precedence
        assert result.overall == TrafficLight.RED
        # Both checkers should have results
        checker_names = {r.checker_name for r in result.results}
        assert "MinimalKoPhraseChecker" in checker_names
        assert "TurnoverThresholdChecker" in checker_names

    def test_phrase_yellow_turnover_met_yields_yellow(self):
        """Phrase checker YELLOW + turnover met => overall YELLOW."""
        text = "Ausschlusskriterium: Der Mindestumsatz beträgt 500.000 EUR."
        company_profile = {"annual_turnover_eur": 600_000}
        result = run_single_page(text, "doc.pdf", 1, company_profile)
        # Phrase checker yields YELLOW, turnover checker yields None (met)
        assert result.overall == TrafficLight.YELLOW
        # Only phrase checker result (turnover returns None when met)
        assert len(result.results) >= 1
        phrase_results = [r for r in result.results if r.checker_name == "MinimalKoPhraseChecker"]
        assert len(phrase_results) == 1

    def test_turnover_red_overrides_phrase_yellow(self):
        """RED from turnover overrides YELLOW from phrase checker."""
        text = "Zwingend erforderlich: Mindestumsatz 1.000.000 EUR."
        company_profile = {"annual_turnover_eur": 500_000}
        result = run_single_page(text, "doc.pdf", 1, company_profile)
        # RED takes precedence
        assert result.overall == TrafficLight.RED


class TestCompanyProfilePassthrough:
    """Test that company_profile is correctly passed to turnover checker."""

    def test_company_profile_used_for_comparison(self):
        """Company profile is used for threshold comparison."""
        # Use text with turnover keyword but no KO phrase trigger
        text = "Der Umsatz beträgt mindestens 500.000 EUR."

        # Below threshold -> RED
        result_below = run_single_page(text, "doc.pdf", 1, {"annual_turnover_eur": 400_000})
        assert result_below.overall == TrafficLight.RED

        # Meets threshold -> GREEN (no KO phrase, turnover met)
        result_meets = run_single_page(text, "doc.pdf", 1, {"annual_turnover_eur": 600_000})
        assert result_meets.overall == TrafficLight.GREEN
