from typing import Any, Dict, List, Optional

from kosniper.contracts import CheckerResult, RunResult, TrafficLight
from kosniper.checkers.minimal_ko_phrase import MinimalKoPhraseChecker
from kosniper.checkers.turnover_threshold import TurnoverThresholdChecker


def _aggregate_status(results: List[CheckerResult]) -> TrafficLight:
    """Aggregate checker results with precedence: red > yellow > abstain > green."""
    statuses = {r.status for r in results}

    if TrafficLight.RED in statuses:
        return TrafficLight.RED
    if TrafficLight.YELLOW in statuses:
        return TrafficLight.YELLOW
    if TrafficLight.ABSTAIN in statuses:
        return TrafficLight.ABSTAIN
    return TrafficLight.GREEN


def run_single_page(
    text: Optional[str],
    doc_id: str = "demo.pdf",
    page_number: int = 1,
    company_profile: Optional[Dict[str, Any]] = None,
) -> RunResult:
    # Guard: empty/None text -> ABSTAIN, never Green
    if text is None or text.strip() == "":
        return RunResult(
            overall=TrafficLight.ABSTAIN,
            summary="Insufficient data to assess; manual review required.",
            results=[],
        )

    results: List[CheckerResult] = []

    # Run MinimalKoPhraseChecker
    phrase_checker = MinimalKoPhraseChecker()
    phrase_result = phrase_checker.run(text=text, doc_id=doc_id, page_number=page_number)
    if phrase_result is not None:
        results.append(phrase_result)

    # Run TurnoverThresholdChecker
    turnover_checker = TurnoverThresholdChecker()
    turnover_result = turnover_checker.run(
        text=text,
        doc_id=doc_id,
        page_number=page_number,
        company_profile=company_profile,
    )
    if turnover_result is not None:
        results.append(turnover_result)

    # Aggregate results
    if not results:
        # No findings from any checker -> GREEN
        return RunResult(
            overall=TrafficLight.GREEN,
            summary="No KO signal detected.",
            results=[],
        )

    overall = _aggregate_status(results)

    if overall == TrafficLight.RED:
        summary = "Hard KO detected; disqualification likely."
    elif overall == TrafficLight.YELLOW:
        summary = "Possible KO signal detected; review evidence."
    elif overall == TrafficLight.ABSTAIN:
        summary = "Insufficient data to assess; manual review required."
    else:
        summary = "No KO signal detected."

    return RunResult(overall=overall, summary=summary, results=results)
