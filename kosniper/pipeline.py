from kosniper.contracts import RunResult, TrafficLight
from kosniper.checkers.minimal_ko_phrase import MinimalKoPhraseChecker

def run_single_page(text: str, doc_id: str = "demo.pdf", page_number: int = 1) -> RunResult:
    checker = MinimalKoPhraseChecker()
    r = checker.run(text=text, doc_id=doc_id, page_number=page_number)

    # MVP aggregation: RED not possible yet (no hard KO checker). YELLOW if anything flags.
    if r.status == TrafficLight.YELLOW:
        overall = TrafficLight.YELLOW
        summary = "Possible KO signal detected; review evidence."
    else:
        overall = TrafficLight.GREEN
        summary = "No KO signal detected by scanned demo checker."

    return RunResult(overall=overall, summary=summary, results=[r])
