"""MC-KOS-51 (Phase 1): LLM evidence checker with deterministic quote verification.

The LLM may only *propose* findings; every proposed quote must be located verbatim
in the normalized text by the deterministic span finder before it becomes evidence.
Fail-closed rules:
- Empty/whitespace text -> ABSTAIN (no_text), like other registered checkers
- No client (disabled/unavailable) -> None (no claim; default pipeline unchanged)
- Malformed output -> ABSTAIN (llm_output_malformed)
- Any unverifiable quote poisons the batch -> ABSTAIN (llm_quote_not_found)
- All quotes verified -> at most YELLOW (RED stays reserved for deterministic checkers)
- Empty findings -> None (an LLM saying "nothing found" is never GREEN evidence)
"""

import json
from typing import Any, List, Optional

from kosniper.checkers.base import Checker
from kosniper.contracts import CheckerResult, EvidenceSpan, ReasonCode, TrafficLight
from kosniper.evidence.spans import MAX_SPAN_SEARCH_CHARS, find_span
from kosniper.llm_client import LLMClient, get_llm_client

# Cap accepted findings per page; the rest are ignored (deterministic truncation)
MAX_FINDINGS = 5
# Preview length for unverified-claim/malformed-output audit snippets
CLAIM_PREVIEW_CHARS = 160


def build_prompt(text: str) -> str:
    """Build the extraction prompt over verifiable text only.

    Truncates to MAX_SPAN_SEARCH_CHARS so the model never sees text the
    span finder cannot verify against.
    """
    excerpt = text[:MAX_SPAN_SEARCH_CHARS]
    return (
        "You are scanning a German public-tender page for knockout (KO) criteria "
        "that could disqualify a bidder.\n"
        "Respond with JSON only, no prose, in exactly this shape:\n"
        '{"findings": [{"quote": "<verbatim quote from the text>"}]}\n'
        "Rules: each quote must be copied verbatim from the text below; "
        'if there is no KO signal, respond {"findings": []}.\n'
        "--- TEXT ---\n"
        f"{excerpt}"
    )


def _parse_quotes(raw: str) -> Optional[List[str]]:
    """Parse model output into a list of quote strings.

    Returns None on any malformed output (invalid JSON or wrong shape).
    An empty findings list parses to [] (valid, distinct from malformed).
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    findings = data.get("findings")
    if not isinstance(findings, list):
        return None
    quotes: List[str] = []
    for item in findings:
        if not isinstance(item, dict):
            return None
        quote = item.get("quote")
        if not isinstance(quote, str) or not quote.strip():
            return None
        quotes.append(quote)
    return quotes


def _claim_preview(label: str, content: str) -> str:
    """Audit snippet for a claim that is NOT document text (label makes it non-empty)."""
    return f"[{label}] {content[:CLAIM_PREVIEW_CHARS]}".strip()


class LLMEvidenceChecker(Checker):
    """Proposes KO findings via an LLM; accepts them only after quote verification.

    Behavior:
    - ABSTAIN (no_text) for empty/whitespace text (deterministic, no LLM needed)
    - None if no client is available (disabled)
    - ABSTAIN (llm_output_malformed) if the model output cannot be parsed
    - ABSTAIN (llm_quote_not_found) if any proposed quote is not in the text
    - YELLOW (llm_ko_signal_verified) with offset evidence if all quotes verify
    - None if the model reports no findings (never GREEN on LLM say-so)
    """

    name = "LLMEvidenceChecker"

    def __init__(self, client: Optional[LLMClient] = None) -> None:
        self._client = client if client is not None else get_llm_client()

    def run(
        self, text: Optional[str], doc_id: str, page_number: int, **kwargs: Any
    ) -> Optional[CheckerResult]:
        # Empty text is a deterministic fact; abstain regardless of client presence
        # (registered-checker invariant: empty text must ABSTAIN, never go silent).
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

        if self._client is None:
            return None

        raw = self._client.complete(build_prompt(text))
        quotes = _parse_quotes(raw)

        if quotes is None:
            return CheckerResult(
                checker_name=self.name,
                status=TrafficLight.ABSTAIN,
                reason=ReasonCode.LLM_OUTPUT_MALFORMED,
                evidence=[
                    EvidenceSpan(
                        doc_id=doc_id,
                        page_number=page_number,
                        snippet=_claim_preview("llm output malformed", raw),
                    )
                ],
            )

        if not quotes:
            return None

        verified: List[EvidenceSpan] = []
        unverified: List[str] = []
        for quote in quotes[:MAX_FINDINGS]:
            span = find_span(text, quote)
            if span is None:
                unverified.append(quote)
            else:
                verified.append(
                    EvidenceSpan(
                        doc_id=doc_id,
                        page_number=page_number,
                        snippet=span["snippet"],
                        start_offset=span["start"],
                        end_offset=span["end"],
                        offset_basis=span["offset_basis"],
                    )
                )

        if unverified:
            # One fabricated quote poisons the batch: the model is not
            # trustworthy on this page, so no verified subset survives.
            return CheckerResult(
                checker_name=self.name,
                status=TrafficLight.ABSTAIN,
                reason=ReasonCode.LLM_QUOTE_NOT_FOUND,
                evidence=[
                    EvidenceSpan(
                        doc_id=doc_id,
                        page_number=page_number,
                        snippet=_claim_preview("unverified llm claim", quote),
                    )
                    for quote in unverified
                ],
            )

        return CheckerResult(
            checker_name=self.name,
            status=TrafficLight.YELLOW,
            reason=ReasonCode.LLM_KO_SIGNAL_VERIFIED,
            evidence=verified,
        )
