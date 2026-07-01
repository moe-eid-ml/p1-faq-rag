# Parking Lot

Anything that is not required to satisfy the current PR acceptance criteria goes here.

## Parked at wrap-up (v0.1.4, 2026-07-01)

- **LLM evidence checker** — promoted to a proposed mission card:
  `missions/MC-KOS-51-llm-evidence-checker.md` (go/no-go decision pending).
- **Real tender ingestion + batch processing** — never started; only relevant if MC-KOS-51 is a go.
- **New deterministic checker families** — parked indefinitely.
- **Stale-hash validation** — parked indefinitely.
- **Remote branch cleanup** — stale branches still exist on `origin`; local merged branches
  were pruned at wrap-up. Delete remote ones whenever convenient.
- ~~**Broken pre-commit hook**~~ — `codex-validate` expected `.venv/bin/codex`, lost in a venv
  rebuild. **Fixed at wrap-up**: the hook now calls `.venv/bin/python -m tools.codex_cli.cli validate`
  (no separate install needed).

