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
