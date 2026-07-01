# KOSniper Project Handoff

## What We're Building

**KOSniper** (formerly "Sniper") is a bidder-side KO scanner for German public tenders. It scans tender PDFs for knockout criteria that would disqualify a bid, producing machine-readable evidence packs with provenance.

## Core Principles

- **Proof-first**: Every non-neutral verdict must have evidence with a non-empty snippet
- **Never false-green**: Empty/no findings → ABSTAIN (not GREEN); 0% false-green rate
- **Traffic light verdicts**: RED > YELLOW > ABSTAIN > GREEN (severity ordering)
- **Per-check evidence**: Each checker produces its own evidence list
- **Offsets rule**: When offsets exist, `offset_basis` must be set to `"normalized_text_v1"`
- **Worst-check-wins**: `overall_verdict` = worst verdict across all checks
- **Uncertainty handling**: Unknown → YELLOW or ABSTAIN (fail-closed, never GREEN)
- **Additive schema only**: No breaking changes to output contract

## Deterministic Gates

All PRs must pass before merge:

```bash
ruff check .
python -m compileall -q .
DISABLE_SEMANTIC=1 pytest -q
```

## Workflow Non-Negotiables

- **One intent per PR**: Single focused change
- **2–5 tests per feature**: Including 1 adversarial test
- **CI green**: All gates must pass
- **Park extras**: Out-of-scope ideas go to backlog, not current PR
- **Roles**: User = PM/architect; Assistant = senior engineer (Opus)
- **Post-PR output**: Include Backwards Walkthrough + 1 unsafe failure prevented
- **Copy-paste templates**: Every assistant output includes squash title + PR description

## What's Merged and Green (MC-KOS-39..45)

| MC | Description |
|----|-------------|
| MC-KOS-39 | v0.1 release polish (README/CHANGELOG) |
| MC-KOS-40 | Scan limits (MAX_PDF_BYTES=50MB, MAX_SCAN_PAGES=500) + regex-safe spans |
| MC-KOS-41 | Release packaging + docs/RELEASE.md checklist |
| MC-KOS-42 | Golden e2e tests locking v1 invariants |
| MC-KOS-43 | Export report pack (`--out-dir`) with report.md, evidence_pack.json |
| MC-KOS-44 | Severity-aware ordering (RED checks first) |
| MC-KOS-45 | Configurable scan limits (`--max-pdf-mb`, `--max-scan-pages`, env vars) |

## Current Repo State

- WARNING: This file can be stale; see CLAUDE.md for current verified state.
- **Status**: Wrapped at v0.1.4 (2026-07-01) — complete as a learning project, no active work
- **Tests**: 274 passed, 8 skipped, 1 xfailed (green at wrap)
- **Working tree**: Clean

## Plan Forward

One open decision, then done:

1. **Decide MC-KOS-51** (LLM evidence checker) — see `missions/MC-KOS-51-llm-evidence-checker.md`
   - **Go** → implement per the mission card (requires explicit dependency approval first)
   - **No-go** → archive: push main + tags, add "archived" to the README status block, close the repo

## Output Format Reminder

Every assistant response should include:
- Max 3 steps per output
- Copy-paste squash title: `MC-KOS-XX: <description>`
- PR description template with Summary + Test plan
