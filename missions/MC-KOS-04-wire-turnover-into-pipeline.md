# MC-KOS-04: Wire TurnoverThresholdChecker into Pipeline

## Goal
Wire the `TurnoverThresholdChecker` into `run_single_page` so that both checkers run in sequence and their results are aggregated with the existing precedence logic.

## Non-goals
- No UI changes.
- No new dependencies.
- No changes to checker logic (already implemented in MC-KOS-02/03).
- No offset handling.

## Files to touch
- `kosniper/pipeline.py` (add TurnoverThresholdChecker, add company_profile param)
- `tests/test_kosniper_pipeline_wiring.py` (NEW)

## Behavioral contract

### Input changes
Add optional argument to `run_single_page`:
```python
def run_single_page(
    text: str,
    doc_id: str = "demo.pdf",
    page_number: int = 1,
    company_profile: dict | None = None,
) -> RunResult:
```

### Checker execution
1. If text is None or empty/whitespace: return ABSTAIN immediately (existing guard).
2. Run `MinimalKoPhraseChecker` (does not need company_profile).
3. Run `TurnoverThresholdChecker` with company_profile.
4. Collect results: if a checker returns None, ignore it (neutral).

### Aggregation
Keep existing precedence: RED > YELLOW > ABSTAIN > GREEN.

## Acceptance criteria
1. Turnover below threshold (e.g., "Mindestumsatz 500.000 EUR", company 400k) => overall RED.
2. Turnover requirement exists but company profile missing => overall YELLOW (not GREEN).
3. No turnover phrase and no KO phrase => overall GREEN.
4. Empty/None text => overall ABSTAIN.
5. `DISABLE_SEMANTIC=1 pytest -q` passes.

## Commands
```bash
DISABLE_SEMANTIC=1 pytest -q
```

## PR hygiene
- One intent: wire turnover checker into pipeline.
- Keep changes minimal.

## Walkthrough (fill in PR)
- pipeline/data flow change:
- new invariant/test:
- new failure mode covered:
