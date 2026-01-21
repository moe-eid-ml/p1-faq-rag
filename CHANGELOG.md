# Changelog

## [Unreleased]
- (planned) Split modules fully (`ui.py`, `retrieval.py`, etc.)
- (planned) CI badge + README polish (complete)
- (planned) Add "Hybrid" tweaks & better eval set (20 DE queries)

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
