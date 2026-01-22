# Sniper North Star (Ultra-Spine)

This is the only always-true project spine. Keep it short. Everything else belongs in versioned docs.

## Product
- KOSniper first: Germany public tenders, bidder-side.
- Decision support only (not legal advice).
- Proof-first: no evidence, no output.
- Safe-fail bias: uncertain → Yellow/Abstain. Never false-green.

## Output contract
- Traffic light overall + per-check breakdown.
- Verdict enum: green | yellow | red | abstain (never green without evidence).
- Evidence per check: doc_id + page + snippet.
- Offsets/bbox are optional and additive (never required, never fabricated).
- **Worst-check-wins:** overall_verdict = worst verdict across all checks.
- **Offset basis:** when offsets exist, offset_basis must be set (current standard: `normalized_text_v1`).

## Workflow (safe but fast)
- One intent per PR.
- 2–5 tests per PR, always include 1 adversarial/edge.
- Run once near the end: DISABLE_SEMANTIC=1 pytest -q
- CI must be green before merge.
- Extras go to docs/parking-lot.md, not the diff.
- No refactor without its own Mission Card; no new deps without approval (see CLAUDE.md).

## Roles
- ChatGPT: mission cards, scope police, final review, learning prompts.
- OpenCode + Codex: implement + minimum tests + run locally.
- Opus 4.5: only for contracts/interfaces, knife-edge parsing/crypto, or wide fragile refactors.
- AG: optional planning/mission cards.

## End-of-PR ritual (non-negotiable)
Backwards Walkthrough:
1) What changed (1–3 files/sections)
2) Why it works (name the invariant/test)
3) Where it can break (failure mode + test)
4) One unsafe failure prevented (now impossible or forced Yellow/Abstain)
Optional: add one takeaway bullet to docs/learnlog.md.

## Preferences
- Never use 🙂.
