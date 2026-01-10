# MC-KOS-01: Minimal KO Phrase Checker (text-only)

## Goal
Ship the smallest deterministic checker that detects “KO-ish” phrases in extracted page text and **forces a conservative result** (Yellow/Abstain) with **evidence**. This is the first building block for KOSniper’s rule: **no evidence, no output**.

## Non-goals (explicitly out of scope)
- No PDF parsing/OCR work in this PR (assume page text already exists as a string).
- No numeric threshold extraction (no Umsatz math).
- No UI / Gradio changes.
- No new dependencies.
- No refactors outside the touched files.

## Inputs
- Page text (string) plus minimal context:
  - `doc_id` (filename)
  - `page_number` (1-indexed)
- Goldset label schema already in repo (`data/kosniper/goldset_v0/labels/v0.jsonl`).

## Files to touch
- `kosniper/checkers/minimal_ko_phrase.py` (NEW)
- `kosniper/checkers/__init__.py` (wire export/registry)
- `kosniper/pipeline.py` (wire checker into the existing checker runner, only if needed)
- `tests/test_kosniper_minimal_ko_phrase_checker.py` (NEW)

## Behavioral contract
### Trigger phrases (v0 list)
Match **case-insensitive** against normalized text:
- `ausschlusskriterium`
- `mindestumsatz`
- `jahresumsatz`
- `zwingend`
- `muss`

Normalization requirement:
- Collapse whitespace.
- Handle simple hyphenation/newline splits (e.g. `Mindest-\numsatz` should match `mindestumsatz`).

### Output
- If any phrase matches: emit exactly **one** finding (keep it simple) with:
  - `overall = "yellow"` (never Red, never Green)
  - Evidence populated with at least: `doc_id`, `page_number`, `snippet` containing the matched phrase.
- If no phrase matches: emit **zero** findings.

### Stop conditions (safety)
- If `page_text` is empty/None after normalization: do **not** return Green.
  - Preferred: return one finding with `overall = "abstain"` and reason `no_text` (if the contracts support a reason field), otherwise return zero findings.
- Under uncertainty: default to **Yellow/Abstain**.

## Acceptance criteria
1. Unit test: phrase present → exactly one finding; `overall == "yellow"`; evidence contains `doc_id`, `page_number`, `snippet`.
2. Unit test: no phrase → zero findings.
3. Adversarial test: hyphenation/newline split (`Mindest-\numsatz`) still triggers.
4. `DISABLE_SEMANTIC=1 pytest -q` passes.

## Commands
- `DISABLE_SEMANTIC=1 pytest -q`

## PR hygiene
- Anything discovered that is useful but not required by the acceptance criteria goes to `parking-lot.md` (do not include it in the diff).
- Keep changes minimal and local to listed files.

## Walkthrough (fill in PR)
- pipeline/data flow change: 
- new invariant/test: 
- new failure mode covered: 
