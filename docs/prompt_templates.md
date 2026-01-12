# Prompt templates (paste-ready)

Always paste this first line in any tool prompt:
"Read and obey: docs/north_star.md and docs/prompt_guardrails.md. No evidence, no claim."

---

## 1) Codex / OpenCode implementation prompt (surgical build)

Read and obey:
- docs/north_star.md
- docs/prompt_guardrails.md

Task:
- Implement the Mission Card below with minimal code changes.
- Add 2–5 tests (include 1 adversarial/edge).
- Run once near the end: DISABLE_SEMANTIC=1 pytest -q
- Fix until green.
- Output: (1) files changed list, (2) brief diff summary, (3) tests added and what they prove, (4) exact commands run + results.

Hard rules:
- If you reference any symbol or file, it must exist in repo (or say NEED FILE).
- Safe-fail: if uncertain, force Yellow/Abstain (never false-green without evidence).
- Do not weaken invariants to “make tests pass”.

Mission Card:
[PASTE MISSION CARD HERE]

---

## 2) Opus 4.5 architecture / knife-edge prompt (rare use)

Read and obey:
- docs/north_star.md
- docs/prompt_guardrails.md

Mission:
- Deep review of the specific area below (contracts/interfaces/parsing/crypto/refactor).
- Max 3 recommendations. Each must be one PR with acceptance criteria + tests.
- Every factual claim needs evidence (file path + symbol + short quote). If not available, say NEED FILE and stop.

Area / Question:
[PASTE AREA + QUESTION HERE]

Output format:
A) Verified findings (with evidence)
B) Suspected risks (label speculative; say what evidence needed)
C) Recommendations (max 3): PR title + acceptance criteria + tests + unsafe failure prevented

---

## 3) ChatGPT Mission Card template (fast)

Goal (1–2 lines):
Non-goals:
Acceptance criteria (3–6 bullets, testable):
Tests to add (2–5 bullets, include 1 adversarial/edge):
Command: DISABLE_SEMANTIC=1 pytest -q
Parking lot: (link docs/parking-lot.md)

---

## 4) “Claude always knows the plan” header (paste at top of Claude sessions)

Read and obey:
- docs/north_star.md
- docs/prompt_guardrails.md
- .github/pull_request_template.md

If you cannot access repo files in your environment, respond with:
NEED FILE: <path>
and ask me to paste the file contents.
