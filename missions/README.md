# Missions

This folder contains **Mission Cards**: small, testable “contracts” for one-intent PRs.

The rule is simple:
- **If it’s not in the Mission Card’s Acceptance Criteria, it does not go in the diff.**
- Anything useful but out-of-scope goes into `parking-lot.md` (root).

## Why this exists
Mission Cards prevent scope creep, keep PRs reviewable, and make it easy to use coding agents (Claude Code/Codex) without losing control.

## Workflow (PR factory)
1. **Write a Mission Card** (AG or you)
   - Goal, Non-goals, Files to touch, Behavioral contract, Stop conditions, Acceptance criteria, Commands.
2. **Implementation (Claude Code)**
   - Claude gets only: the Mission Card + repo tree + the test commands.
   - Loop: implement → run tests → fix until green.
3. **Review (GPT)**
   - Paste back: `git diff` + test output (and failure logs if needed).
   - Reviewer pass checks: spec vs AC, hidden coupling, failure modes (Yellow/Abstain), adversarial coverage.
4. **PR hygiene**
   - Feature-flag risky behavior.
   - Add tests + at least 1 adversarial case per checker.
   - End the PR description with a **Walkthrough** section (see below).

## Naming
- One mission per PR.
- Files are named: `MC-<AREA>-<NN>-<short-slug>.md`
  - Example: `MC-KOS-01-minimal-ko-phrase.md`

## Mission Card template
Every card should include:
- Goal
- Non-goals (explicit)
- Files to touch
- Behavioral contract
- Stop conditions (what becomes Yellow/Abstain)
- Acceptance criteria (must be testable)
- Commands (exact)
- PR hygiene notes
- Walkthrough placeholders

## Walkthrough (required in PR description)
Three bullets, filled while the change is fresh:
- pipeline/data flow change:
- new invariant/test:
- new failure mode covered:

## Tips
- Prefer conservative defaults: **Yellow/Abstain beats false Green**.
- Keep contracts stable: “no evidence, no output.”
- Avoid `#` inline comments in zsh commands (it can break pasted command blocks).
