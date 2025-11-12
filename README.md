# P1 — Multilingual FAQ RAG (EN/DE/AR)

Dual-mode retrieval (Semantic vs TF-IDF) with language gating, filename filters, and a metrics CLI.

## Features
- TF-IDF ↔ Semantic switch (MiniLM)
- Language auto-detect + override (de/en/ar)
- Filename **Include** filter (e.g., `faq`)
- Eval CLI: Precision@K / Recall@K
- Gradio UI

## Run
```bash
source .venv/bin/activate
python app.py
## Results (FAQ subset)

- k=3, Include=faq  
  - TF-IDF: **P@3 = 0.57**, **R@3 = 0.80**  
  - Semantic: **P@3 = 0.33**, **R@3 = 1.00**

- k=1, Include=faq  
  - TF-IDF: **P@1 = 0.80**, **R@1 = 0.80**  
  - Semantic: **P@1 = 1.00**, **R@1 = 1.00**
python cli.py eval --both -k 3 --include faq
## Wohngeld MVP (Multilingual)

**Corpus:** `docs/wohngeld` (DE/EN/AR). Other texts archived and excluded from index.  
**Default mode:** Hybrid (RRF).  
**UI tip:** set **Include** → `wohngeld`; use **Language (override)** for strict DE/EN/AR.

### Eval — `data/wohngeld_eval.jsonl`
**k=3 (Include=wohngeld)**  
- TF-IDF: **P@3 = 0.40**, **R@3 = 1.00**  
- Semantic: **P@3 = 0.40**, **R@3 = 1.00**  
- Hybrid: **P@3 = 0.40**, **R@3 = 1.00**

**k=1 (Include=wohngeld)**  
- Hybrid: **P@1 = 0.80**, **R@1 = 0.70**

### Run
```bash
source .venv/bin/activate
python app.py

## Tooling

We use a small Typer CLI to keep the FAQ corpus clean and builds reproducible.

**Commands**
- `codex validate` — ensures Q/A are Arabic-only and blocks banned terms.
- `codex slugs` — enforces `slug__YYYY-MM-DD.txt` filenames.
- `codex embed` — builds `build/index.json` from `docs/faq/ar`.
- `codex sync` — validate → slugs → embed (one command).

**Dev/CI**
- Local guard: pre-commit runs `codex validate` on each commit.
- CI: `.github/workflows/faq-ci.yml` validates and builds on push/PR.

**Security hygiene**
- No secrets committed. Use `.env.example` (not `.env`).
- `.gitignore` excludes `.venv/`, `build/`, `__pycache__/`, `.pytest_cache/`.
