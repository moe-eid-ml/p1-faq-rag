import pytest
from kosniper.checkers.turnover_threshold import TurnoverThresholdChecker
from kosniper.contracts import TrafficLight


@pytest.fixture
def checker():
    return TurnoverThresholdChecker()


@pytest.fixture
def company_400k():
    return {"annual_turnover_eur": 400_000}


@pytest.fixture
def company_600k():
    return {"annual_turnover_eur": 600_000}


@pytest.fixture
def company_2m():
    return {"annual_turnover_eur": 2_000_000}


class TestRedFindings:
    """AC1: Clear requirement + company below -> RED."""

    def test_clear_threshold_company_below(self, checker, company_400k):
        """Basic case: 500k threshold, company has 400k -> RED."""
        text = "Der Mindestumsatz muss mindestens 500.000 EUR betragen."
        result = checker.run(text, "doc.pdf", 1, company_400k)
        assert result is not None
        assert result.status == TrafficLight.RED
        assert result.reason == "below_threshold"
        assert len(result.evidence) == 1
        assert result.evidence[0].doc_id == "doc.pdf"
        assert result.evidence[0].page_number == 1

    def test_mio_threshold_company_below(self, checker):
        """1,5 Mio. EUR = 1,500,000; company at 1M -> RED."""
        text = "Jahresumsatz: mindestens 1,5 Mio. EUR"
        result = checker.run(text, "doc.pdf", 1, {"annual_turnover_eur": 1_000_000})
        assert result is not None
        assert result.status == TrafficLight.RED
        assert result.reason == "below_threshold"

    def test_euro_symbol_threshold(self, checker, company_400k):
        """€ symbol instead of EUR."""
        text = "Mindestumsatz: 500.000 €"
        result = checker.run(text, "doc.pdf", 1, company_400k)
        assert result is not None
        assert result.status == TrafficLight.RED

    def test_german_thousands_separator(self, checker, company_400k):
        """1.000.000 € = 1,000,000 EUR."""
        text = "Der Mindestumsatz beträgt 1.000.000 €."
        result = checker.run(text, "doc.pdf", 1, company_400k)
        assert result is not None
        assert result.status == TrafficLight.RED


class TestZeroFindings:
    """AC2: Clear requirement + company meets -> zero findings (None)."""

    def test_threshold_met_returns_none(self, checker, company_600k):
        """Company at 600k meets 500k threshold -> None (neutral)."""
        text = "Der Mindestumsatz muss mindestens 500.000 EUR betragen."
        result = checker.run(text, "doc.pdf", 1, company_600k)
        assert result is None

    def test_threshold_exceeded_returns_none(self, checker, company_2m):
        """Company at 2M exceeds 500k threshold -> None."""
        text = "Mindestumsatz: 500.000 EUR"
        result = checker.run(text, "doc.pdf", 1, company_2m)
        assert result is None

    def test_no_turnover_keyword_returns_none(self, checker, company_400k):
        """No turnover requirement in text -> None."""
        text = "Bitte reichen Sie Ihre Unterlagen ein."
        result = checker.run(text, "doc.pdf", 1, company_400k)
        assert result is None


class TestYellowAmbiguous:
    """AC3: Ambiguous requirements -> YELLOW."""

    def test_durchschnittlich_yellow(self, checker, company_600k):
        """Average requirement is ambiguous."""
        text = "Durchschnittlicher Jahresumsatz der letzten 3 Jahre: mind. 500.000 EUR"
        result = checker.run(text, "doc.pdf", 1, company_600k)
        assert result is not None
        assert result.status == TrafficLight.YELLOW
        assert result.reason == "ambiguous_requirement"

    def test_multi_year_yellow(self, checker, company_600k):
        """Multi-year reference is ambiguous."""
        text = "Umsatz in den letzten 3 Geschäftsjahren: mindestens 1.000.000 EUR"
        result = checker.run(text, "doc.pdf", 1, company_600k)
        assert result is not None
        assert result.status == TrafficLight.YELLOW
        assert result.reason == "ambiguous_requirement"

    def test_multiple_thresholds_yellow(self, checker, company_400k):
        """Multiple distinct thresholds -> YELLOW."""
        text = """
        Gesamtumsatz: mindestens 1.000.000 EUR.
        Umsatz im relevanten Geschäftsbereich: mindestens 500.000 EUR.
        """
        result = checker.run(text, "doc.pdf", 1, company_400k)
        assert result is not None
        assert result.status == TrafficLight.YELLOW
        # Could be ambiguous_requirement or ambiguous_threshold_count
        assert "ambiguous" in result.reason

    def test_range_yellow(self, checker, company_400k):
        """Range pattern is ambiguous."""
        text = "Jahresumsatz zwischen 500.000 und 1.000.000 EUR"
        result = checker.run(text, "doc.pdf", 1, company_400k)
        assert result is not None
        assert result.status == TrafficLight.YELLOW
        assert result.reason == "ambiguous_requirement"


class TestYellowMissingData:
    """AC4: Missing company profile -> YELLOW."""

    def test_no_company_profile(self, checker):
        """Threshold exists but no company profile -> YELLOW."""
        text = "Mindestumsatz: 500.000 EUR"
        result = checker.run(text, "doc.pdf", 1, None)
        assert result is not None
        assert result.status == TrafficLight.YELLOW
        assert result.reason == "missing_company_turnover"

    def test_empty_company_profile(self, checker):
        """Threshold exists but empty profile -> YELLOW."""
        text = "Mindestumsatz: 500.000 EUR"
        result = checker.run(text, "doc.pdf", 1, {})
        assert result is not None
        assert result.status == TrafficLight.YELLOW
        assert result.reason == "missing_company_turnover"

    def test_missing_turnover_field(self, checker):
        """Profile exists but missing turnover field -> YELLOW."""
        text = "Mindestumsatz: 500.000 EUR"
        result = checker.run(text, "doc.pdf", 1, {"company_name": "Acme"})
        assert result is not None
        assert result.status == TrafficLight.YELLOW
        assert result.reason == "missing_company_turnover"

    def test_missing_currency_yellow(self, checker, company_400k):
        """Turnover keyword but no currency marker -> YELLOW."""
        text = "Mindestumsatz: 500.000"
        result = checker.run(text, "doc.pdf", 1, company_400k)
        assert result is not None
        assert result.status == TrafficLight.YELLOW
        assert result.reason == "missing_currency"


class TestAbstain:
    """AC5: Empty/None text -> ABSTAIN."""

    def test_empty_string_abstain(self, checker, company_400k):
        result = checker.run("", "doc.pdf", 1, company_400k)
        assert result is not None
        assert result.status == TrafficLight.ABSTAIN
        assert result.reason == "no_text"

    def test_none_text_abstain(self, checker, company_400k):
        result = checker.run(None, "doc.pdf", 1, company_400k)
        assert result is not None
        assert result.status == TrafficLight.ABSTAIN
        assert result.reason == "no_text"

    def test_whitespace_only_abstain(self, checker, company_400k):
        result = checker.run("   \n\t  ", "doc.pdf", 1, company_400k)
        assert result is not None
        assert result.status == TrafficLight.ABSTAIN
        assert result.reason == "no_text"


class TestAdversarial:
    """AC6: Adversarial cases including hyphenation."""

    def test_hyphenated_mindestumsatz(self, checker, company_400k):
        """Hyphenation at line break: Mindest-\\numsatz -> mindestumsatz."""
        text = "Der Mindest-\numsatz beträgt 500.000 EUR."
        result = checker.run(text, "doc.pdf", 1, company_400k)
        assert result is not None
        assert result.status == TrafficLight.RED

    def test_hyphenated_jahresumsatz(self, checker, company_400k):
        """Hyphenation: Jahres-\\numsatz."""
        text = "Der Jahres-\numsatz muss mindestens 500.000 EUR betragen."
        result = checker.run(text, "doc.pdf", 1, company_400k)
        assert result is not None
        assert result.status == TrafficLight.RED

    def test_mio_with_decimal(self, checker):
        """1,5 Mio. EUR = 1,500,000."""
        text = "Mindestjahresumsatz von 1,5 Mio. EUR erforderlich."
        result = checker.run(text, "doc.pdf", 1, {"annual_turnover_eur": 1_200_000})
        assert result is not None
        assert result.status == TrafficLight.RED

    def test_tsd_multiplier(self, checker, company_400k):
        """500 Tsd. EUR = 500,000."""
        text = "Mindestumsatz: 500 Tsd. EUR"
        result = checker.run(text, "doc.pdf", 1, company_400k)
        assert result is not None
        assert result.status == TrafficLight.RED

    def test_nicht_unterschreiten_phrasing(self, checker, company_400k):
        """'darf nicht unterschreiten' phrasing."""
        text = "Der Jahresumsatz darf 500.000 EUR nicht unterschreiten."
        result = checker.run(text, "doc.pdf", 1, company_400k)
        # Should detect turnover requirement
        assert result is not None
        # Either RED (if parsed) or at least not None
        assert result.status in (TrafficLight.RED, TrafficLight.YELLOW)


class TestEvidenceFormat:
    """Verify evidence contains required fields."""

    def test_evidence_has_required_fields(self, checker, company_400k):
        text = "Der Mindestumsatz muss mindestens 500.000 EUR betragen."
        result = checker.run(text, "doc.pdf", 3, company_400k)
        assert result is not None
        assert len(result.evidence) == 1
        ev = result.evidence[0]
        assert ev.doc_id == "doc.pdf"
        assert ev.page_number == 3
        assert ev.snippet
        assert "500" in ev.snippet or "mindestumsatz" in ev.snippet.lower()
        # Offsets should be None (v0)
        assert ev.start_offset is None
        assert ev.end_offset is None


class TestMultiCriteriaRegression:
    """MC-KOS-03: Avoid false RED on repeated turnover criteria with same value."""

    def test_two_criteria_same_value_yields_yellow(self, checker, company_400k):
        """Two separate criteria with same value must yield YELLOW, not RED."""
        text = """
        Mindestumsatz: 500.000 EUR.
        Umsatz im relevanten Geschäftsbereich: 500.000 EUR.
        """
        result = checker.run(text, "doc.pdf", 1, company_400k)
        assert result is not None
        # Must be YELLOW (ambiguous), NOT RED
        assert result.status == TrafficLight.YELLOW
        assert result.status != TrafficLight.RED
        assert "ambiguous" in result.reason

    def test_same_sentence_repeated_yields_yellow(self, checker, company_400k):
        """Same sentence repeated should be conservative (YELLOW)."""
        text = """
        Der Mindestumsatz beträgt 500.000 EUR.
        Der Mindestumsatz beträgt 500.000 EUR.
        """
        result = checker.run(text, "doc.pdf", 1, company_400k)
        assert result is not None
        # Conservative: YELLOW for repeated criteria
        assert result.status == TrafficLight.YELLOW
        assert result.status != TrafficLight.RED

    def test_single_criterion_still_works(self, checker, company_400k):
        """Single unambiguous threshold still produces RED if below."""
        text = "Der Mindestumsatz beträgt 500.000 EUR."
        result = checker.run(text, "doc.pdf", 1, company_400k)
        assert result is not None
        assert result.status == TrafficLight.RED
        assert result.reason == "below_threshold"

    def test_single_criterion_met_returns_none(self, checker, company_600k):
        """Single unambiguous threshold still returns None if met."""
        text = "Der Mindestumsatz beträgt 500.000 EUR."
        result = checker.run(text, "doc.pdf", 1, company_600k)
        assert result is None
