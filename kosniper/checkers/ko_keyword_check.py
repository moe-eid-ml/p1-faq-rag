"""MC-KOS-29: KO keyword checker using evidence spans.

Deterministic checker that scans normalized_text_v1 for KO keywords
and returns evidence spans with offsets.
"""

from typing import Any, Optional

from kosniper.checkers.base import Checker
from kosniper.contracts import CheckerResult, EvidenceSpan, ReasonCode, TrafficLight
from kosniper.evidence.spans import find_span


class KoKeywordChecker(Checker):
    """Deterministic KO keyword checker using evidence spans.

    Behavior:
    - RED with evidence if KO keyword found
    - None if not found (no finding to report)
    - ABSTAIN for empty/whitespace-only text

    Keywords are chosen to NOT overlap with MinimalKoPhraseChecker.
    """

    name = "KoKeywordChecker"

    # Hard KO keywords - if found, this is a RED signal
    # Chosen to NOT overlap with MinimalKoPhraseChecker keywords
    KO_KEYWORDS = [
        "ausschlusskriterien",      # plural form (not "ausschlusskriterium")
        "zwingend erforderlich",    # full phrase (not just "zwingend")
        "mangelnde eignung",        # lacking suitability
    ]

    def run(
        self, text: Optional[str], doc_id: str, page_number: int, **kwargs: Any
    ) -> Optional[CheckerResult]:
        """Run the KO keyword check.

        Args:
            text: Normalized text (normalized_text_v1).
            doc_id: Document identifier.
            page_number: Page number (1-indexed).

        Returns:
            CheckerResult with RED verdict if KO keyword found,
            None if not found (no finding to report).
        """
        # Handle empty/missing text
        if not text or not text.strip():
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

        # Search for KO keywords using evidence spans
        for keyword in self.KO_KEYWORDS:
            span = find_span(text, keyword)
            if span is not None:
                return CheckerResult(
                    checker_name=self.name,
                    status=TrafficLight.RED,
                    reason=ReasonCode.KO_PHRASE_FOUND,
                    evidence=[
                        EvidenceSpan(
                            doc_id=doc_id,
                            page_number=page_number,
                            snippet=span["snippet"],
                            start_offset=span["start"],
                            end_offset=span["end"],
                            offset_basis=span["offset_basis"],
                        )
                    ],
                )

        # Not found - return None (no finding to report)
        return None
