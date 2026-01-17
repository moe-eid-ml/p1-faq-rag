import re
from typing import Any, Optional

from kosniper.contracts import CheckerResult, EvidenceSpan, ReasonCode, TrafficLight
from kosniper.checkers.base import Checker


class MinimalKoPhraseChecker(Checker):
    name = "MinimalKoPhraseChecker"

    def run(
        self, text: Optional[str], doc_id: str, page_number: int, **kwargs: Any
    ) -> Optional[CheckerResult]:
        if not text:
            return None
        m = re.search(r"Ausschlusskriterium", text, flags=re.IGNORECASE)
        if not m:
            # No phrase match -> zero findings (None)
            return None

        start, end = m.span()
        snippet = text[max(0, start - 60) : min(len(text), end + 60)]

        return CheckerResult(
            checker_name=self.name,
            status=TrafficLight.YELLOW,  # matcher-only signal, not a verdict
            reason=ReasonCode.KO_PHRASE_FOUND,
            evidence=[
                EvidenceSpan(
                    doc_id=doc_id,
                    page_number=page_number,
                    snippet=snippet,
                    start_offset=start,
                    end_offset=end,
                    offset_basis="raw_text_v1",
                )
            ],
        )
