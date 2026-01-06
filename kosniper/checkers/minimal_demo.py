import re
from kosniper.contracts import CheckerResult, EvidenceSpan, TrafficLight
from kosniper.checkers.base import Checker

class MinimalKoPhraseChecker(Checker):
    name = "MinimalKoPhraseChecker"

    def run(self, text: str, doc_id: str, page_number: int) -> CheckerResult:
        m = re.search(r"Ausschlusskriterium", text, flags=re.IGNORECASE)
        if not m:
            return CheckerResult(
                checker_name=self.name,
                status=TrafficLight.ABSTAIN,
                reason="No explicit KO phrase found in this minimal demo checker.",
                evidence=[],
            )

        start, end = m.span()
        snippet = text[max(0, start - 60) : min(len(text), end + 60)]

        return CheckerResult(
            checker_name=self.name,
            status=TrafficLight.YELLOW,  # matcher-only signal, not a verdict
            reason="Found explicit KO-related phrase; manual verification required.",
            evidence=[
                EvidenceSpan(
                    doc_id=doc_id,
                    page_number=page_number,
                    snippet=snippet,
                    start_offset=start,
                    end_offset=end,
                )
            ],
        )
