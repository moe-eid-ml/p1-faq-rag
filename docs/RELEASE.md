# KOSniper Release Guide

## v1 Criteria

KOSniper v1 is "live" when all of the following are true:

| Criterion | Requirement |
|-----------|-------------|
| **False-green rate** | 0% on adversarial test set |
| **Proof-first** | Every non-neutral verdict has evidence with non-empty snippet |
| **Offset integrity** | All offsets have `offset_basis` set (standard: `normalized_text_v1`) |
| **Worst-check-wins** | `overall_verdict` = worst verdict across all checks |
| **Deterministic** | Same input always produces same output; no network/time/randomness |
| **Fail-closed** | Limits exceeded → Yellow/Abstain (never Green) |
| **CI green** | All commands in release checklist pass |

## Release Checklist

Run these commands before any release:

```bash
# 1. Lint
ruff check .

# 2. Byte-compile (syntax check)
python -m compileall -q .

# 3. Tests (deterministic, no network)
DISABLE_SEMANTIC=1 pytest -q

# 4. Demo scan (verify end-to-end)
python -m kosniper.cli --pdf tests/fixtures/fixture_ko_page2.pdf --scan
python -m kosniper.cli --pdf tests/fixtures/fixture_neutral.pdf --scan
```

All must pass. If any fail, do not release.

## Versioning

- **MAJOR:** Breaking contract changes (verdict enum, evidence schema)
- **MINOR:** New checkers, new optional fields, new CLI flags
- **PATCH:** Bug fixes, doc updates, performance improvements

Current: See `CHANGELOG.md` for version history.
