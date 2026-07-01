"""MC-KOS-51 (Phase 1): LLM evidence checker tests (mocked client only).

No live LLM, no SDK, no network: a FakeClient returns canned output so every
fail-closed path is exercised deterministically.
"""

import json

from kosniper.checkers.llm_evidence import MAX_FINDINGS, LLMEvidenceChecker
from kosniper.contracts import ReasonCode, TrafficLight
from kosniper.pipeline import run_single_page

PAGE_TEXT = (
    "Die Vergabestelle weist darauf hin: ein Mindestjahresumsatz von 2 Mio. EUR "
    "ist zwingend nachzuweisen. Weitere Unterlagen sind beizufuegen."
)
REAL_QUOTE = "ein Mindestjahresumsatz von 2 Mio. EUR ist zwingend nachzuweisen"


class FakeClient:
    def __init__(self, response: str) -> None:
        self._response = response

    def complete(self, prompt: str) -> str:
        return self._response


def test_disabled_by_default_is_inert(monkeypatch):
    """No live client in Phase 1: default checker returns None and the
    default pipeline output contains no LLM check (golden behavior preserved)."""
    monkeypatch.setenv("DISABLE_LLM", "1")
    assert LLMEvidenceChecker().run(PAGE_TEXT, "doc.pdf", 1) is None

    monkeypatch.delenv("DISABLE_LLM")
    assert LLMEvidenceChecker().run(PAGE_TEXT, "doc.pdf", 1) is None

    result = run_single_page("Bitte reichen Sie Ihre Unterlagen ein.", "doc.pdf", 1)
    assert "LLMEvidenceChecker" not in {r.checker_name for r in result.results}
    assert result.overall == TrafficLight.ABSTAIN  # never false-green, unchanged


def test_malformed_output_abstains():
    """Adversarial: garbage model output must ABSTAIN, never crash or go green."""
    checker = LLMEvidenceChecker(client=FakeClient('{"findings": [{"quo'))
    result = checker.run(PAGE_TEXT, "doc.pdf", 1)
    assert result.status == TrafficLight.ABSTAIN
    assert result.reason == ReasonCode.LLM_OUTPUT_MALFORMED
    assert result.evidence and result.evidence[0].snippet.strip()
    assert result.evidence[0].start_offset is None  # no fake anchoring


def test_fabricated_quote_poisons_batch():
    """Adversarial: one hallucinated quote rejects the whole batch, even when
    another quote is genuinely present in the text."""
    response = (
        '{"findings": [{"quote": "%s"}, '
        '{"quote": "Der Bieter wird ohne Ausnahme sofort ausgeschlossen."}]}' % REAL_QUOTE
    )
    checker = LLMEvidenceChecker(client=FakeClient(response))
    result = checker.run(PAGE_TEXT, "doc.pdf", 1)
    assert result.status == TrafficLight.ABSTAIN
    assert result.reason == ReasonCode.LLM_QUOTE_NOT_FOUND
    assert all(ev.start_offset is None for ev in result.evidence)
    assert any("unverified llm claim" in ev.snippet for ev in result.evidence)


def test_verified_quote_yields_yellow_with_offsets():
    """Happy path: verified quote becomes document-derived evidence with
    offsets on normalized_text_v1, capped at YELLOW."""
    checker = LLMEvidenceChecker(client=FakeClient('{"findings": [{"quote": "%s"}]}' % REAL_QUOTE))
    result = checker.run(PAGE_TEXT, "doc.pdf", 2)
    assert result.status == TrafficLight.YELLOW
    assert result.reason == ReasonCode.LLM_KO_SIGNAL_VERIFIED
    ev = result.evidence[0]
    assert ev.page_number == 2
    assert ev.offset_basis == "normalized_text_v1"
    assert PAGE_TEXT[ev.start_offset : ev.end_offset].lower() == REAL_QUOTE.lower()
    assert REAL_QUOTE.lower() in ev.snippet.lower()


def test_fabricated_quote_after_cap_still_poisons_batch():
    """Adversarial (review finding): a fabricated quote beyond MAX_FINDINGS must
    still poison the batch — verification covers ALL quotes, the cap applies
    only to emitted evidence."""
    real_quotes = ["Die Vergabestelle", "Mindestjahresumsatz", "zwingend", "Unterlagen", "beizufuegen"]
    assert len(real_quotes) == MAX_FINDINGS  # fabricated quote lands exactly after the cap
    findings = [{"quote": q} for q in real_quotes]
    findings.append({"quote": "Frei erfundenes Zitat ohne Beleg im Text."})
    checker = LLMEvidenceChecker(client=FakeClient(json.dumps({"findings": findings})))
    result = checker.run(PAGE_TEXT, "doc.pdf", 1)
    assert result.status == TrafficLight.ABSTAIN
    assert result.reason == ReasonCode.LLM_QUOTE_NOT_FOUND


def test_empty_findings_is_no_claim_not_green():
    """An LLM reporting 'nothing found' is not evidence: no result at all,
    so the pipeline's never-false-green aggregation stays in charge."""
    checker = LLMEvidenceChecker(client=FakeClient('{"findings": []}'))
    assert checker.run(PAGE_TEXT, "doc.pdf", 1) is None
