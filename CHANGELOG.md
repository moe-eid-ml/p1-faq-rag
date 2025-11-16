# Changelog

## [Unreleased]
- (planned) Split modules fully (`ui.py`, `retrieval.py`, etc.)
- (planned) CI badge + README polish (complete)
- (planned) Add “Hybrid” tweaks & better eval set (20 DE queries)

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
