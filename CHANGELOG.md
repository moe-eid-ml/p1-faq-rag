# Changelog

## [Unreleased]
- (planned) Split modules fully (`ui.py`, `retrieval.py`, etc.)
- (planned) CI badge + README polish (complete)
- (planned) Add "Hybrid" tweaks & better eval set (20 DE queries)

## [v0.1.3] — 2026-01-22
### Added
- MC-KOS-40: Scan limits (MAX_PDF_BYTES=50MB, MAX_SCAN_PAGES=500) with fail-closed Yellow
- MC-KOS-40: Regex-safe span finding with MAX_SPAN_SEARCH_CHARS=100K truncation guard
- MC-KOS-40: SCAN_LIMIT_EXCEEDED reason code for limit-hit evidence
- MC-KOS-41: Release checklist and v1 criteria in docs/RELEASE.md
- MC-KOS-42: Golden e2e tests locking v1 invariants (worst-check-wins, document_map, never-false-green, offset_basis)
- MC-KOS-43: Export report pack (`--out-dir`) with report.md, evidence_pack.json, document_map.json

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
