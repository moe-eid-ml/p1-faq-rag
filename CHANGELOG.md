# Changelog

## [Unreleased]
### Added
- MC-KOS-51 Phase 1: LLM evidence checker skeleton (mocked, no new dependencies)
  - `LLMClient` Protocol + `get_llm_client()` factory; `DISABLE_LLM=1` off-switch
  - `LLMEvidenceChecker`: quote verification via span finder; malformed output → ABSTAIN;
    any fabricated quote → ABSTAIN (poisons batch); all-verified → YELLOW max; inert in
    default pipeline (no live client in Phase 1)
  - Additive reason codes: `llm_output_malformed`, `llm_quote_not_found`, `llm_ko_signal_verified`
  - Review fix (Codex): verify ALL returned quotes, cap only emitted evidence — a fabricated
    quote beyond `MAX_FINDINGS` can no longer escape the poison-the-batch ABSTAIN
- Open decision: MC-KOS-51 Phase 2 (live SDK + first eval) — go, or archive the repo.

## [v0.1.4] — 2026-07-01 — Wrap-up
### Changed
- Repo wrapped as a complete learning project (FAQ RAG + KOSniper v0.1); gates green at wrap
- README: project-status banner + two-project framing (FAQ RAG and KOSniper)
- CLAUDE.md / HANDOFF.md: state tables updated to wrapped status
- Untracked `build/index.json` (build artifact; reproducible via `codex embed`)
- Pruned local branches already merged into main
- Fixed `codex-validate` pre-commit hook (module invocation replaces lost `codex` entrypoint)
- Marked FAQ-RAG roadmap/TODO docs as historical (README sections, docs/ROADMAP.md)
### Added
- `missions/MC-KOS-51-llm-evidence-checker.md` — PROPOSED LLM checker, go/no-go pending

> Note on tags: `v0.1`, `v0.1.1`, `v1.0.0` are legacy FAQ-RAG-era tags. The `v0.1.x`
> series in this changelog tracks the combined repo (KOSniper from v0.1.2 on).

## [v0.1.3] — 2026-01-22
### Added
- MC-KOS-40: Scan limits (MAX_PDF_BYTES=50MB, MAX_SCAN_PAGES=500) with fail-closed Yellow
- MC-KOS-40: Regex-safe span finding with MAX_SPAN_SEARCH_CHARS=100K truncation guard
- MC-KOS-40: SCAN_LIMIT_EXCEEDED reason code for limit-hit evidence
- MC-KOS-41: Release checklist and v1 criteria in docs/RELEASE.md
- MC-KOS-42: Golden e2e tests locking v1 invariants (worst-check-wins, document_map, never-false-green, offset_basis)
- MC-KOS-43: Export report pack (`--out-dir`) with report.md, evidence_pack.json, document_map.json
- MC-KOS-44: Severity-aware ordering (RED checks first, then YELLOW, ABSTAIN, GREEN)
- MC-KOS-45: Configurable scan limits (`--max-pdf-mb`, `--max-scan-pages`, env vars)

## [v0.1.2] — 2026-01-21
### Added
- PDF ingestion with `normalized_text_v1` and per-page SHA256 hashes
- `--scan` mode: run all checkers on PDF, output JSON evidence pack
- Checkers: MinimalKoPhraseChecker, KoKeywordChecker, KoExclusionPhraseChecker, TurnoverThresholdChecker
- Evidence spans with `start_offset`, `end_offset`, `offset_basis="normalized_text_v1"`
- Evidence selection policy: sort, dedupe, limit (max_k=3, max_total=10)
- Document map provenance with `overall_sha256`
- CLI guards: fail-closed on invalid verdict, offset_basis, contradictions
- Static fixture PDFs for deterministic end-to-end tests

## [v0.1.1] — 2025-11-16
### Fixed/Refactor
- Moved `detect_lang` to `app_pkg.lang`; removed duplicates
- Timezone-safe timestamps (`_dt.datetime.now(_dt.timezone.utc)`)
- CSV logging scoped + disabled on HF via `LOG_QUERIES`
- Makefile normalized; add `run`, `test`, `eval`, `ask`, `space-push`

## [v0.1.0] — 2025-11-14
### Added
- Multilingual FAQ RAG (DE/EN/AR) with TF-IDF, Semantic, Hybrid (RRF)
- Gradio UI + in-app eval (P@K/R@K)
- CLI eval + `ask.py` headless queries
- HF Space deploy + Python pin + on-disk embedding cache
