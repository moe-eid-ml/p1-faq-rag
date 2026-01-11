import re
from typing import Any, Optional

from kosniper.contracts import CheckerResult, EvidenceSpan, ReasonCode, TrafficLight
from kosniper.checkers.base import Checker


class MinimalKoPhraseChecker(Checker):
    """Minimal deterministic checker for KO phrases in German tender text.

    Detects "KO-ish" phrases and forces a conservative result (Yellow/Abstain)
    with evidence. Rule: no evidence, no output.
    """

    name = "MinimalKoPhraseChecker"

    # v0 trigger phrases (matched case-insensitive)
    TRIGGER_PHRASES = [
        "ausschlusskriterium",
        "mindestumsatz",
        "jahresumsatz",
        "zwingend",
        "muss",
    ]

    def _normalize(self, text: str) -> str:
        """Normalize text: handle hyphenation at line breaks, collapse whitespace."""
        if not text:
            return ""
        # Handle hyphenation at line breaks: "Mindest-\numsatz" -> "Mindestumsatz"
        normalized = re.sub(r"-\s*\n\s*", "", text)
        # Collapse whitespace
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def run(
        self, text: str, doc_id: str, page_number: int, **kwargs: Any
    ) -> Optional[CheckerResult]:
        normalized = self._normalize(text)

        # Stop condition: empty text after normalization -> abstain
        if not normalized:
            return CheckerResult(
                checker_name=self.name,
                status=TrafficLight.ABSTAIN,
                reason=ReasonCode.NO_TEXT,
                evidence=[
                    EvidenceSpan(
                        doc_id=doc_id,
                        page_number=page_number,
                        snippet="(no text)",
                    )
                ],
            )

        # Search for trigger phrases (case-insensitive)
        normalized_lower = normalized.lower()
        for phrase in self.TRIGGER_PHRASES:
            idx = normalized_lower.find(phrase)
            if idx != -1:
                # Found a match - extract snippet with context
                snippet_start = max(0, idx - 60)
                snippet_end = min(len(normalized), idx + len(phrase) + 60)
                snippet = normalized[snippet_start:snippet_end]

                return CheckerResult(
                    checker_name=self.name,
                    status=TrafficLight.YELLOW,
                    reason=ReasonCode.KO_PHRASE_FOUND,
                    evidence=[
                        EvidenceSpan(
                            doc_id=doc_id,
                            page_number=page_number,
                            snippet=snippet,
                            # Offsets omitted: computed on normalized text, not original
                        )
                    ],
                )

        # No phrase matches -> zero findings (None)
        return None
