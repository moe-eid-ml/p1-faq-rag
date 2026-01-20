"""MC-KOS-32: Exclusion phrase checker using regex spans.

Detects explicit exclusionary wording (Ausschluss) in tender text.
"""

import re
from typing import Any, Optional

from kosniper.checkers.base import Checker
from kosniper.contracts import CheckerResult, EvidenceSpan, ReasonCode, TrafficLight
from kosniper.evidence.spans import find_span_regex


class KoExclusionPhraseChecker(Checker):
    """Regex-based checker for explicit exclusion phrases.

    Behavior:
    - RED with evidence if exclusion phrase found
    - None if not found (no finding to report)
    - ABSTAIN for empty/whitespace-only text
    """

    name = "KoExclusionPhraseChecker"

    # Regex patterns for explicit exclusion phrases (case-insensitive)
    # Note: ausschluss(kriterium|grund) omitted to avoid overlap with MinimalKoPhraseChecker
    EXCLUSION_PATTERNS = [
        r"(bei\s+nichtbeachtung[^.]{0,120}(ausschluss|ausgeschlossen))",
        r"(wird\s+(vom\s+verfahren\s+)?ausgeschlossen)",
    ]

    def run(
        self, text: Optional[str], doc_id: str, page_number: int, **kwargs: Any
    ) -> Optional[CheckerResult]:
        """Run the exclusion phrase check.

        Args:
            text: Normalized text (normalized_text_v1).
            doc_id: Document identifier.
            page_number: Page number (1-indexed).

        Returns:
            CheckerResult with RED verdict if exclusion phrase found,
            None if not found (no finding to report).
        """
        if not text or not text.strip():
            return None

        # Search patterns in order (deterministic)
        for pattern in self.EXCLUSION_PATTERNS:
            span = find_span_regex(text, pattern, flags=re.IGNORECASE)
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
