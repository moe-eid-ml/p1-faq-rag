# Sniper / KOSniper: Operating Rules (autoloaded by Claude Code)

Read first:
- docs/north_star.md
- docs/prompt_guardrails.md
- .github/pull_request_template.md

Non-negotiables:
- No evidence, no claim. If you can’t cite file+symbol+short quote: NEED FILE: <path>.
- One intent per PR. 2–5 tests incl 1 adversarial. Run DISABLE_SEMANTIC=1 pytest -q once near end. CI green before merge.
- Safe-fail: uncertain -> Yellow/Abstain. Never false-green. Never fabricate evidence.
- Schema changes additive only: new fields optional + defaulted.

Working style:
- Start with a short plan + file list.
- Implement minimal diff + tests.
- End with Backwards Walkthrough + 1 unsafe failure prevented.
