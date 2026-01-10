# MC-KOS-03: Avoid False RED on Repeated Turnover Criteria

## Goal
Fix false RED when multiple turnover criteria on the same page share the same numeric threshold. The de-duplication logic must not collapse distinct matches solely by numeric value—multiple distinct occurrences should be treated as ambiguous.

## Non-goals
- No new features.
- No PDF parsing changes.
- No pipeline wiring changes.
- No new dependencies.

## Files to touch
- `kosniper/checkers/turnover_threshold.py` (modify de-dup logic)
- `tests/test_kosniper_turnover_threshold_checker.py` (add regression tests)

## Behavioral contract
### Current (broken) behavior
The checker de-duplicates extracted thresholds by numeric value. If "Mindestumsatz 500.000 EUR" and "Umsatz im relevanten Geschäftsbereich 500.000 EUR" appear on the same page, they collapse to one threshold (500,000) and may produce RED if the company is below.

### Fixed behavior
Multiple distinct matches on a page (different keyword positions/snippets) with the same or different values must be treated as **ambiguous** and return **YELLOW** with reason `ambiguous_threshold_count` or `ambiguous_requirement`. Conservative is correct.

## Acceptance criteria
1. Two separate turnover criteria with the same value (e.g., "Mindestumsatz 500.000 EUR" + "Umsatz im relevanten Geschäftsbereich 500.000 EUR") yields **one YELLOW finding**, not RED.
2. A page with the same sentence repeated should be conservative (YELLOW is acceptable).
3. Single unambiguous threshold still works as before (RED if below, None if met).
4. `DISABLE_SEMANTIC=1 pytest -q` passes.

## Commands
```bash
DISABLE_SEMANTIC=1 pytest -q
```

## PR hygiene
- One intent: fix the false RED on multi-criteria pages.
- Keep changes minimal.

## Walkthrough (fill in PR)
- pipeline/data flow change:
- new invariant/test:
- new failure mode covered:
