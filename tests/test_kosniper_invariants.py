"""Invariant guardrails to prevent hallucination-style regressions."""

import pytest

from kosniper.checkers.minimal_ko_phrase import MinimalKoPhraseChecker
from kosniper.checkers.turnover_threshold import TurnoverThresholdChecker
from kosniper.pipeline import run_single_page
from kosniper.contracts import CheckerResult, EvidenceSpan, ReasonCode, TrafficLight
from kosniper.checkers.registry import get_checker_classes


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
    assert result is not None
    _assert_has_evidence(result)
    assert result.status == TrafficLight.YELLOW

    abstain_result = checker.run("", "doc.pdf", 2)
    assert abstain_result is not None
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
    assert missing_profile.reason == ReasonCode.MISSING_COMPANY_TURNOVER

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
    assert result.reason in {ReasonCode.AMBIGUOUS_REQUIREMENT, ReasonCode.AMBIGUOUS_THRESHOLD_COUNT}


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


def test_non_neutral_result_rejects_empty_evidence():
    """CheckerResult validation: non-neutral status requires non-empty evidence."""

    # RED with empty evidence should raise
    with pytest.raises(ValueError, match="requires non-empty evidence"):
        CheckerResult(
            checker_name="TestChecker",
            status=TrafficLight.RED,
            reason=ReasonCode.BELOW_THRESHOLD,
            evidence=[],
        )

    # YELLOW with empty evidence should raise
    with pytest.raises(ValueError, match="requires non-empty evidence"):
        CheckerResult(
            checker_name="TestChecker",
            status=TrafficLight.YELLOW,
            reason=ReasonCode.KO_PHRASE_FOUND,
            evidence=[],
        )

    # ABSTAIN with empty evidence should raise
    with pytest.raises(ValueError, match="requires non-empty evidence"):
        CheckerResult(
            checker_name="TestChecker",
            status=TrafficLight.ABSTAIN,
            reason=ReasonCode.NO_TEXT,
            evidence=[],
        )


def test_non_neutral_result_rejects_empty_snippet():
    """CheckerResult validation: non-neutral status requires non-empty snippet."""

    with pytest.raises(ValueError, match="requires non-empty snippet"):
        CheckerResult(
            checker_name="TestChecker",
            status=TrafficLight.YELLOW,
            reason=ReasonCode.KO_PHRASE_FOUND,
            evidence=[EvidenceSpan(doc_id="test.pdf", page_number=1, snippet="")],
        )

    with pytest.raises(ValueError, match="requires non-empty snippet"):
        CheckerResult(
            checker_name="TestChecker",
            status=TrafficLight.RED,
            reason=ReasonCode.BELOW_THRESHOLD,
            evidence=[EvidenceSpan(doc_id="test.pdf", page_number=1, snippet="   ")],
        )


def test_run_single_page_none_text_returns_abstain():
    """Invariant: run_single_page(None, ...) => ABSTAIN, not GREEN.

    MC-KOS-08: Ensures None text is safe and never becomes GREEN.
    """
    result = run_single_page(None, "doc.pdf", 1)
    assert result.overall == TrafficLight.ABSTAIN

    # Guardrail: ABSTAIN must be evidenced (no evidence, no output).
    assert result.results, "ABSTAIN should carry checker evidence when text is None"
    for r in result.results:
        _assert_has_evidence(r)
        assert r.status == TrafficLight.ABSTAIN

    # Explainability: pipeline should provide a human-readable reason.
    assert result.summary  # non-empty summary


# Trigger inputs that produce findings for each registered checker.
# Derived from existing tests and checker implementations.
_CHECKER_TRIGGER_INPUTS = {
    "MinimalKoPhraseChecker": {
        "text": "Dies ist ein Ausschlusskriterium.",
        "doc_id": "test.pdf",
        "page_number": 1,
    },
    "TurnoverThresholdChecker": {
        "text": "Der Mindestumsatz beträgt 500.000 EUR.",
        "doc_id": "test.pdf",
        "page_number": 1,
        "company_profile": {"annual_turnover_eur": 400_000},
    },
}


@pytest.mark.parametrize("checker_cls", get_checker_classes(), ids=lambda c: c.__name__)
def test_evidence_span_offsets_are_consistent(checker_cls):
    """Invariant: start_offset and end_offset must be both None or both int.

    Ensures checkers don't produce half-populated offset pairs, which would
    confuse consumers expecting either full offset info or none.
    """
    checker = checker_cls()
    trigger = _CHECKER_TRIGGER_INPUTS.get(checker_cls.__name__)

    if trigger is None:
        pytest.skip(f"No trigger input defined for {checker_cls.__name__}")

    result = checker.run(**trigger)

    # Allow None result (no finding) - nothing to check
    if result is None:
        return

    for i, ev in enumerate(result.evidence):
        has_start = ev.start_offset is not None
        has_end = ev.end_offset is not None
        assert has_start == has_end, (
            f"{checker_cls.__name__}: EvidenceSpan[{i}] has inconsistent offsets - "
            f"start_offset={ev.start_offset!r}, end_offset={ev.end_offset!r}; "
            f"expected both None or both int"
        )


@pytest.mark.parametrize("checker_cls", get_checker_classes(), ids=lambda c: c.__name__)
@pytest.mark.parametrize("empty_text", [None, "", "   "], ids=["None", "empty", "whitespace"])
def test_registered_checker_empty_text_yields_abstain(checker_cls, empty_text):
    """Invariant: all registered checkers must ABSTAIN (not None) on empty text."""
    checker = checker_cls()
    result = checker.run(text=empty_text, doc_id="test.pdf", page_number=1)

    assert result is not None, f"{checker_cls.__name__} returned None for empty_text={empty_text!r}"
    assert result.status == TrafficLight.ABSTAIN, (
        f"{checker_cls.__name__} returned {result.status} for empty_text={empty_text!r}; expected ABSTAIN"
    )


def test_no_duplicate_checker_names_in_registry():
    """Invariant: checker .name exists and is unique across the registry."""
    classes = get_checker_classes()

    missing_name = [cls.__name__ for cls in classes if not hasattr(cls, "name")]
    assert not missing_name, f"Registered checker(s) missing required .name attribute: {missing_name}"

    names = [cls.name for cls in classes]
    assert len(names) == len(set(names)), f"Duplicate checker name(s) in registry: {names}"


def test_all_registered_checkers_have_trigger_input():
    """Invariant: every registered checker must have a trigger input defined."""
    for checker_cls in get_checker_classes():
        assert checker_cls.__name__ in _CHECKER_TRIGGER_INPUTS, (
            f"{checker_cls.__name__} missing from _CHECKER_TRIGGER_INPUTS"
        )
