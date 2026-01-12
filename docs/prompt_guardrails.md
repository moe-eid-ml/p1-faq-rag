# Prompt Guardrails (paste-first header)

Use this header at the top of any Codex / OpenCode / Opus / Claude prompt.

## Non-negotiable guardrails
1) No evidence, no claim: if you can’t cite a file path + symbol + short quote, say NEED FILE: <path>.
2) Separate Verified vs Suspected vs Recommendations.
3) One intent per PR. Keep scope tight.
4) Determinism only: no network/time/randomness.
5) Safe-fail: if uncertain, force Yellow/Abstain (never confident green without evidence).
6) Schema/contract changes must be additive: new fields optional + defaulted.
7) Don’t “fix” failures by weakening invariants.

## Required output format
A) Verified findings (with evidence)
B) Suspected risks (explicitly speculative; say what evidence you need)
C) Recommendation (max 3) with:
   - PR title
   - acceptance criteria
   - tests to add
   - unsafe failure prevented

## Code patch rules
- Every import/symbol must exist in-repo (or request the file).
- Prefer tests-first. If you change behavior, add the test that would fail without it.
