"""Invariant guardrails to prevent hallucination-style regressions."""

from kosniper.checkers.minimal_ko_phrase import MinimalKoPhraseChecker
from kosniper.checkers.turnover_threshold import TurnoverThresholdChecker
from kosniper.pipeline import run_single_page
from kosniper.contracts import TrafficLight


def _assert_has_evidence(result):
    assert result is not None
    assert result.evidence, "Expected evidence for non-neutral result"
    for ev in result.evidence:
        assert ev.doc_id
        assert ev.page_number is not None
        assert ev.snippet.strip() != ""


def test_non_neutral_results_include_evidence():
    checker = MinimalKoPhraseChecker()
    result = checker.run("Dies ist ein Ausschlusskriterium.", "doc.pdf", 1)
    _assert_has_evidence(result)
    assert result.status == TrafficLight.YELLOW

    abstain_result = checker.run("", "doc.pdf", 2)
    _assert_has_evidence(abstain_result)
    assert abstain_result.status == TrafficLight.ABSTAIN


def test_non_empty_text_without_requirements_is_green():
    result = run_single_page("Bitte reichen Sie Ihr Angebot ein.", "doc.pdf", 1)
    assert result.overall == TrafficLight.GREEN
    assert result.results == []


def test_red_requires_threshold_and_company_profile():
    text = "Der Mindestumsatz beträgt 500.000 EUR."
    checker = TurnoverThresholdChecker()

    missing_profile = checker.run(text, "doc.pdf", 1, company_profile=None)
    assert missing_profile is not None
    assert missing_profile.status == TrafficLight.YELLOW
    assert missing_profile.reason == "missing_company_turnover"

    below_threshold = checker.run(
        text,
        "doc.pdf",
        1,
        company_profile={"annual_turnover_eur": 400_000},
    )
    assert below_threshold is not None
    assert below_threshold.status == TrafficLight.RED


def test_ambiguity_forces_yellow_when_multiple_thresholds():
    text = "Mindestumsatz 500.000 EUR und Mindestumsatz 600.000 EUR."
    result = TurnoverThresholdChecker().run(
        text,
        "doc.pdf",
        1,
        company_profile={"annual_turnover_eur": 1_000_000},
    )
    assert result is not None
    assert result.status == TrafficLight.YELLOW
    assert result.reason in {"ambiguous_requirement", "ambiguous_threshold_count"}


def test_outputs_are_deterministic():
    args = (
        "Ausschlusskriterium: Mindestumsatz 500.000 EUR.",
        "doc.pdf",
        1,
        {"annual_turnover_eur": 400_000},
    )
    first = run_single_page(*args)
    second = run_single_page(*args)
    assert first == second
