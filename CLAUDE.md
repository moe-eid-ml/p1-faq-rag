# Sniper / KOSniper: Operating Rules (autoloaded by Claude Code)

Read first:
- docs/north_star.md
- docs/prompt_guardrails.md
- .github/pull_request_template.md

Non-negotiables:
- No evidence, no claim. If you can't cite file+symbol+short quote: NEED FILE: <path>.
- One intent per PR. 2–5 tests incl 1 adversarial. Run DISABLE_SEMANTIC=1 pytest -q once near end. CI green before merge.
- Safe-fail: uncertain -> Yellow/Abstain. Never false-green. Never fabricate evidence.
- Schema changes additive only: new fields optional + defaulted.
- New checkers must not overlap existing trigger keywords/patterns (avoid changing existing test expectations).
- No refactor without its own Mission Card.
- No new dependencies without explicit user approval.

Stop rules (fail-closed):
- Cannot cite file+symbol+quote → say `NEED FILE: <path>` and stop.
- Change touches unlisted files → refuse, request updated Mission Card.
- Adding dependency → stop, request approval.

Working style:
- Start with a short plan + file list.
- Implement minimal diff + tests.
- End with Backwards Walkthrough + 1 unsafe failure prevented.

---

## Current Verified State

| Item | Value |
|------|-------|
| **Main HEAD** | `ed87b74` (MC-KOS-50) |
| **Demo loop** | ✅ Works on fixture |
| **Ingestion** | ⬜ Not started |

## Gates (copy-paste)

```bash
ruff check . && python -m compileall -q . && DISABLE_SEMANTIC=1 pytest -q
```

## Demo Loop (the money path)

```bash
bash scripts/demo_pack.sh tests/fixtures/fixture_ko_page2.pdf --out-dir ~/kos_demo_out
cat ~/kos_demo_out/verify_receipt.json
```

Expected: `"status": "ok"` + 4 artifacts.

## Scope Boundaries

- **In scope**: Demo loop with fixtures, fail-closed verification.
- **Not started**: Real tender ingestion, batch processing.
- **Parking lot**: New checker families, stale-hash validation.
