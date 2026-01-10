from typing import List

from kosniper.contracts import CheckerResult, RunResult, TrafficLight
from kosniper.checkers.minimal_ko_phrase import MinimalKoPhraseChecker


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


def run_single_page(text: str, doc_id: str = "demo.pdf", page_number: int = 1) -> RunResult:
    # Guard: empty/None text -> ABSTAIN, never Green
    if text is None or text.strip() == "":
        return RunResult(
            overall=TrafficLight.ABSTAIN,
            summary="Insufficient data to assess; manual review required.",
            results=[],
        )

    checker = MinimalKoPhraseChecker()
    r = checker.run(text=text, doc_id=doc_id, page_number=page_number)
    results = [r]

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
