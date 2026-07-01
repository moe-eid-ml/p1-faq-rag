# MC-KOS-51: LLM Evidence Checker

**Status: Phase 1 (mocked skeleton) — GO given 2026-07-01, implemented. Phase 2 (live SDK
+ first real eval) — UNDECIDED, requires explicit dependency approval before any work.**

Phase split (agreed with reviewer):
- **Phase 1 (done)**: no new dependencies. `LLMClient` Protocol + `get_llm_client()` factory
  (`kosniper/llm_client.py`), `LLMEvidenceChecker` (`kosniper/checkers/llm_evidence.py`)
  registered but inert in the default pipeline (factory returns None → checker returns None,
  so default output is byte-identical). Mocked-client tests cover malformed JSON, fabricated
  quote (poisons the batch), verified quote, empty findings, and disabled-by-default.
- **Phase 2 (undecided)**: add a real SDK behind the same Protocol, run the first live eval
  against fixtures/goldset. Separate go/no-go; `DISABLE_LLM=1` stays the hard off-switch.

## Why this mission exists

KOSniper's deterministic core is done (v0.1: demo loop + fail-closed verify on fixtures).
Its contract — no evidence no claim, never false-green, abstain on uncertainty — is exactly
the discipline LLM applications need. This mission reuses that trusted infrastructure to
learn real LLM engineering, instead of starting from a blank repo.

## Goal

Add ONE LLM-backed checker alongside the deterministic ones:

1. The LLM reads normalized tender text and proposes KO findings as structured JSON.
2. Every finding must include a **verbatim quote** from the document.
3. A deterministic verifier accepts a finding only if the quote is actually found in the
   normalized text (reusing the span finder from MC-KOS-40). Quote not found → the finding
   is discarded and the checker returns ABSTAIN with a reason code.
4. Never-false-green is preserved by construction: the LLM can only *add* caution, never
   remove it.

## What it teaches (the actual point)

- Structured output from an LLM: JSON contract, schema validation, malformed-output handling
- Grounding / citation verification: catching hallucinated evidence by exact matching
- Fail-closed integration of a non-deterministic component into a deterministic pipeline
- Eval discipline: measure the LLM checker's precision against existing fixtures/goldset

## Design sketch

- New checker conforming to the existing Checker interface, returning `CheckerResult`
- LLM call isolated behind a small client wrapper
- `DISABLE_LLM=1` (mirrors `DISABLE_SEMANTIC`) → checker abstains; CI stays deterministic
  and needs no API key
- Verified quote → evidence with snippet + offsets + `offset_basis: normalized_text_v1`
- Conservative verdict mapping for v1: a verified LLM finding raises at most YELLOW;
  RED stays reserved for deterministic checkers
- New reason codes (additive): e.g. `LLM_QUOTE_NOT_FOUND`, `LLM_OUTPUT_MALFORMED`

## Non-goals

- LLM never sets RED or GREEN directly in v1
- No batch processing or real-tender ingestion (still parked)
- No prompt-tuning rabbit holes: one prompt, iterate only via eval results
- No changes to the existing deterministic checkers or their test expectations

## Blockers requiring explicit approval (per CLAUDE.md)

- **New dependency**: an LLM SDK (e.g. `anthropic`) — needs explicit approval before adding
- API key via `.env` only (never committed); CI and the full test suite must pass with
  `DISABLE_LLM=1` and no key present

## Acceptance criteria (draft — refine at go time)

1. With `DISABLE_LLM=1`, the full existing suite passes unchanged.
2. Adversarial test: mocked LLM returns a fabricated quote → finding rejected, ABSTAIN + reason.
3. Adversarial test: mocked LLM returns malformed JSON → ABSTAIN + reason (no crash).
4. Happy path (mocked): verified quote → evidence with non-empty snippet, offsets, offset_basis.
5. Gates green: `ruff check . && python -m compileall -q . && DISABLE_SEMANTIC=1 pytest -q`

## Decision criteria

**Go** if: you want hands-on practice with structured outputs, grounding verification, and
LLM evals, on infrastructure you already built and trust. Estimated ~2–4 focused sessions
for the mocked skeleton + first real LLM run.

**No-go (archive)** if: you'd rather learn LLMs on a fresh codebase without this repo's
process overhead. Then: push main + tags, add an "archived" line to the README status
block, and close the repo. It stands as a complete portfolio piece either way.
