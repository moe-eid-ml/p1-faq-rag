from typing import Any, Dict, List, Optional

from kosniper.contracts import CheckerResult, EvidencePack, RunResult, TrafficLight
from kosniper.checkers.registry import get_checker_classes


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
    doc_id: str,
    page_number: int,
    company_profile: Optional[Dict[str, Any]] = None,
) -> RunResult:
    if not doc_id or page_number <= 0:
        raise ValueError("doc_id and page_number are required for provenance")

    results: List[CheckerResult] = []

    # Run all registered checkers in deterministic order
    for checker_cls in get_checker_classes():
        checker = checker_cls()
        result = checker.run(
            text=text,
            doc_id=doc_id,
            page_number=page_number,
            company_profile=company_profile,
        )
        if result is not None:
            results.append(result)

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


def make_evidence_pack(
    text: Optional[str],
    doc_id: str,
    page_number: int,
    company_profile: Optional[Dict[str, Any]] = None,
) -> EvidencePack:
    """Run KO-scanner and return machine-readable evidence pack.

    Convenience wrapper that runs the scanner and wraps result in EvidencePack.
    """
    if not doc_id or page_number <= 0:
        raise ValueError("doc_id and page_number are required for provenance")
    result = run_single_page(text, doc_id, page_number, company_profile)
    return EvidencePack(run_result=result)
