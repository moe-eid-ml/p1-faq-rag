# MC-KOS-06: Reason/Evidence Schema Hardening

## Goal
Harden the CheckerResult schema:
1. Replace free-form string reasons with a typed `ReasonCode` enum
2. Enforce evidence requirement for non-neutral results (RED/YELLOW/ABSTAIN)

## Non-goals
- No UI changes.
- No new dependencies.
- No refactors beyond contracts/checkers/tests needed for this change.
- No behavior changes beyond validation.

## Files to touch
- `kosniper/contracts.py` (add ReasonCode enum, update CheckerResult)
- `kosniper/checkers/minimal_ko_phrase.py` (use ReasonCode)
- `kosniper/checkers/minimal_demo.py` (use ReasonCode, fix evidence)
- `kosniper/checkers/turnover_threshold.py` (use ReasonCode)
- `tests/test_kosniper_minimal_ko_phrase_checker.py` (assert ReasonCode)
- `tests/test_kosniper_invariants.py` (assert ReasonCode, evidence validation)
- `tests/test_kosniper_turnover_threshold_checker.py` (assert ReasonCode)

## ReasonCode values
- `NO_TEXT` - empty/whitespace text
- `KO_PHRASE_FOUND` - KO phrase detected
- `MISSING_CURRENCY` - turnover keyword without currency marker
- `AMBIGUOUS_REQUIREMENT` - ambiguity pattern detected
- `AMBIGUOUS_THRESHOLD_COUNT` - multiple thresholds found
- `MISSING_COMPANY_TURNOVER` - no company profile turnover
- `BELOW_THRESHOLD` - company turnover below requirement

## Evidence validation
- Non-neutral results (RED/YELLOW/ABSTAIN) MUST have:
  - Non-empty evidence list
  - Each evidence span must have non-empty snippet
- Validation enforced in CheckerResult.__post_init__

## Acceptance criteria
1. ReasonCode enum in contracts.py with all values above.
2. CheckerResult.reason is ReasonCode (not str).
3. CheckerResult validates evidence on non-neutral status.
4. All checkers use ReasonCode values.
5. Tests assert reason is ReasonCode, not string comparison.
6. At least one test verifies evidence validation rejects empty evidence.
7. `DISABLE_SEMANTIC=1 pytest -q` passes.
8. `ruff check .` passes.
9. `python -m compileall -q .` passes.

## Commands
```bash
DISABLE_SEMANTIC=1 pytest -q
ruff check .
python -m compileall -q .
```

## Walkthrough (fill in PR)
- pipeline/data flow change: (none)
- new invariant/test: evidence validation in CheckerResult, ReasonCode type checks
- new failure mode covered: empty evidence on non-neutral results
