# Adversarial Test Suite

Purpose: catch edge cases and boundary conditions that could cause false-green, fabricated evidence, or silent contract violations.

## Rules

1. Every PR with behavior changes must include 1+ adversarial test.
2. Adversarial tests verify **safe-fail** (Yellow/Abstain), not just "doesn't crash".
3. Name pattern: `test_adversarial_<scenario>.py` or embed as `def test_adversarial_*` in module tests.
4. Adversarial tests live under `tests/adversarial/` and run via `DISABLE_SEMANTIC=1 pytest -q` (CI).

## Example Scenarios

| Scenario | Expected Behavior |
|----------|-------------------|
| Empty/None input | Abstain, never Green |
| Missing evidence for non-neutral verdict | ValueError at construction |
| Offsets without offset_basis | ValueError (fail-closed) |
| overall_verdict != worst(check verdicts) | ValueError (contradiction) |
| Pathological regex input | No hang; timeout or safe return |

## Key Invariants

- **No false-green:** Empty results → Abstain
- **Proof-first:** Non-neutral verdict requires evidence with non-empty snippet
- **Worst-check-wins:** overall_verdict = worst verdict across checks
- **Offset integrity:** Offsets require offset_basis (current standard: `normalized_text_v1`)
