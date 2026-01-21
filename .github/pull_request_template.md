Title: <feat|fix|chore>(<area>): <short>

What:
- <1 line>

Why:
- <1 line>

How tested:
- DISABLE_SEMANTIC=1 pytest -q

Walkthrough (pre-merge, while fresh):
- pipeline/data flow change: <1 bullet>
- new invariant/test: <1 bullet>
- new failure mode covered: <1 bullet>
- unsafe failure prevented: <1 bullet (now impossible or forced Yellow/Abstain)>

Tests added (2–5 incl 1 adversarial):
- <test + what it proves> (or "N/A (doc-only)")

Pre-merge checklist:
- [ ] Imports/symbols exist (`rg "<symbol>" -S .`)
- [ ] Test fails without this change
- [ ] No invariants weakened
- [ ] No new deps (or approved)
- [ ] `ruff check . && python -m compileall -q . && DISABLE_SEMANTIC=1 pytest -q`

Parking lot (not in this PR):
- <optional bullets>
