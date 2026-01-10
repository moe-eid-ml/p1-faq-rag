# MC-KOS-05: Checker Interface Alignment

## Goal
Align the `Checker` base class interface to match reality: checkers may return `None` for neutral/no-finding results. Update the abstract method signature to `-> Optional[CheckerResult]` and ensure all implementations match.

## Non-goals
- No behavior changes.
- No new features.
- No refactors beyond interface alignment.
- No UI changes.
- No new dependencies.

## Files to touch
- `kosniper/checkers/base.py` (update abstract method signature)
- `kosniper/checkers/minimal_ko_phrase.py` (ensure signature matches, use `Optional`)
- `kosniper/checkers/minimal_demo.py` (ensure signature matches if needed)
- `kosniper/checkers/turnover_threshold.py` (already returns `Optional`, verify)
- `tests/test_kosniper_checker_interface.py` (NEW)

## Behavioral contract
- No runtime behavior change.
- All checkers must use `typing.Optional[CheckerResult]` return type (Python<3.10 compatible).
- No `X | None` PEP604 syntax.

## Acceptance criteria
1. `Checker.run()` in base.py has return type `Optional[CheckerResult]`.
2. All checker implementations match this signature.
3. No PEP604 union syntax (`X | None`) in kosniper/ files.
4. Interface test passes: each checker returns `None` or `CheckerResult` instance.
5. `DISABLE_SEMANTIC=1 pytest -q` passes.
6. `ruff check .` passes.
7. `python -m compileall -q .` passes.

## Commands
```bash
DISABLE_SEMANTIC=1 pytest -q
ruff check .
python -m compileall -q .
```

## PR hygiene
- One intent: interface alignment.
- Keep changes minimal.

## Walkthrough (fill in PR)
- pipeline/data flow change: (none)
- new invariant/test: interface test verifying return types
- new failure mode covered: (none)
