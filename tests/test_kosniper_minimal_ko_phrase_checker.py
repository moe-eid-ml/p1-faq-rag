import pytest
from kosniper.checkers.minimal_ko_phrase import MinimalKoPhraseChecker
from kosniper.contracts import TrafficLight


@pytest.fixture
def checker():
    return MinimalKoPhraseChecker()


class TestPhrasePresent:
    """AC1: phrase present -> exactly one finding, overall==yellow, evidence has doc_id, page_number, snippet."""

    def test_ausschlusskriterium_triggers_yellow(self, checker):
        result = checker.run(
            text="Dies ist ein Ausschlusskriterium für Bieter.",
            doc_id="tender.pdf",
            page_number=5,
        )
        assert result.status == TrafficLight.YELLOW
        assert len(result.evidence) == 1
        ev = result.evidence[0]
        assert ev.doc_id == "tender.pdf"
        assert ev.page_number == 5
        assert ev.snippet

    def test_mindestumsatz_triggers_yellow(self, checker):
        result = checker.run(
            text="Der Mindestumsatz beträgt 1 Million Euro.",
            doc_id="doc.pdf",
            page_number=2,
        )
        assert result.status == TrafficLight.YELLOW
        assert len(result.evidence) == 1

    def test_jahresumsatz_triggers_yellow(self, checker):
        result = checker.run(
            text="Jahresumsatz der letzten drei Jahre.",
            doc_id="doc.pdf",
            page_number=1,
        )
        assert result.status == TrafficLight.YELLOW
        assert len(result.evidence) == 1

    def test_zwingend_triggers_yellow(self, checker):
        result = checker.run(
            text="Diese Anforderung ist zwingend erforderlich.",
            doc_id="doc.pdf",
            page_number=1,
        )
        assert result.status == TrafficLight.YELLOW
        assert len(result.evidence) == 1

    def test_muss_triggers_yellow(self, checker):
        result = checker.run(
            text="Der Bieter muss nachweisen.",
            doc_id="doc.pdf",
            page_number=1,
        )
        assert result.status == TrafficLight.YELLOW
        assert len(result.evidence) == 1

    def test_case_insensitive_match(self, checker):
        result = checker.run(
            text="AUSSCHLUSSKRITERIUM in uppercase.",
            doc_id="doc.pdf",
            page_number=1,
        )
        assert result.status == TrafficLight.YELLOW
        assert len(result.evidence) == 1


class TestNoPhrase:
    """AC2: no phrase -> zero findings."""

    def test_no_ko_phrase_returns_zero_findings(self, checker):
        result = checker.run(
            text="Normale Ausschreibung ohne besondere Kriterien.",
            doc_id="doc.pdf",
            page_number=1,
        )
        # No phrase match -> None (zero findings)
        assert result is None

    def test_unrelated_text_returns_zero_findings(self, checker):
        result = checker.run(
            text="Lorem ipsum dolor sit amet.",
            doc_id="doc.pdf",
            page_number=1,
        )
        # No phrase match -> None (zero findings)
        assert result is None


class TestHyphenation:
    """AC3: Adversarial test for hyphenation/newline splits."""

    def test_hyphenated_mindestumsatz_triggers(self, checker):
        result = checker.run(
            text="Der Mindest-\numsatz beträgt 500.000 Euro.",
            doc_id="doc.pdf",
            page_number=3,
        )
        assert result.status == TrafficLight.YELLOW
        assert len(result.evidence) == 1
        assert "mindestumsatz" in result.reason.lower()

    def test_hyphenated_jahresumsatz_triggers(self, checker):
        result = checker.run(
            text="Der Jahres-\n  umsatz muss angegeben werden.",
            doc_id="doc.pdf",
            page_number=1,
        )
        assert result.status == TrafficLight.YELLOW
        assert len(result.evidence) == 1


class TestEmptyText:
    """Stop condition: empty/None text after normalization -> abstain."""

    def test_empty_string_returns_abstain(self, checker):
        result = checker.run(text="", doc_id="doc.pdf", page_number=1)
        assert result.status == TrafficLight.ABSTAIN
        assert result.reason == "no_text"
        assert len(result.evidence) == 0

    def test_whitespace_only_returns_abstain(self, checker):
        result = checker.run(text="   \n\t  ", doc_id="doc.pdf", page_number=1)
        assert result.status == TrafficLight.ABSTAIN
        assert result.reason == "no_text"
        assert len(result.evidence) == 0

    def test_none_text_returns_abstain(self, checker):
        result = checker.run(text=None, doc_id="doc.pdf", page_number=1)
        assert result.status == TrafficLight.ABSTAIN
        assert result.reason == "no_text"
        assert len(result.evidence) == 0
