# MC-KOS-08: Align checker text nullability (Optional[str]) end-to-end

## Goal
Make the checker interface and pipeline consistently accept `text: Optional[str]` without changing runtime semantics.
This removes LSP/type drift and prevents future regressions where `None` accidentally yields GREEN or crashes.

## Non-goals
- No new checkers.
- No changes to precedence rules.
- No parsing/logic changes (only interface + safe normalization/forwarding).
- No UI changes.

## Files to touch
- `kosniper/checkers/base.py`
- `kosniper/checkers/minimal_ko_phrase.py`
- `kosniper/checkers/minimal_demo.py`
- `kosniper/checkers/turnover_threshold.py`
- `kosniper/pipeline.py`
- `tests/test_kosniper_invariants.py` (or a new minimal test file if cleaner)

## Contract
- `Checker.run(text: Optional[str], doc_id: str, page_number: int, **kwargs) -> Optional[CheckerResult]`
- `pipeline.run_single_page(text: Optional[str], ...)` must not crash on `None`.
- Behavior must remain:
  - `None/empty/whitespace text` ⇒ pipeline overall **ABSTAIN** (not GREEN), with evidence present on ABSTAIN findings.
  - Non-empty text and no matches ⇒ **GREEN** (no findings), as before.

## Acceptance criteria
1) All checker `run()` signatures match base interface (including `Optional[str]` + `**kwargs`).
2) Pipeline accepts `text=None` and returns overall **ABSTAIN**.
3) No existing tests change meaning; only adjust tests if they depended on old typing.
4) `DISABLE_SEMANTIC=1 pytest -q`, `ruff check .`, `python -m compileall -q .` all pass.

## Suggested tests
- Add/extend an invariant test:
  - `run_single_page(None, "doc.pdf", 1)` ⇒ `overall == ABSTAIN` and at least one result has evidence.
- Keep it minimal: one new test is enough if it would have caught the old mismatch.

## Commands
- `DISABLE_SEMANTIC=1 pytest -q`
- `ruff check .`
- `python -m compileall -q .`

## Walkthrough (fill in PR)
- pipeline/data flow change:
- new invariant/test:
- new failure mode covered: