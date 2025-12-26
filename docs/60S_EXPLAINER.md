# 60s Explainer (p1-faq-rag)

## What this is
A multilingual (DE/EN/AR) Wohngeld FAQ assistant that answers questions **with sources** using Retrieval-Augmented Generation (RAG).

## Pipeline in ~60 seconds

1) **Input**
   - User asks a question (optionally chooses mode: TF‑IDF / Semantic / Hybrid) and can filter by topic (`include`) and language (`lang`).

2) **Pre-checks (reliability)**
   - If the input is nonsense → the app **abstains** (doesn’t guess).
   - If it’s too broad (e.g., just “Wohngeld”) → the app asks **1–4 clarifying questions**.

3) **Retrieval**
   - We retrieve relevant chunks from a small curated corpus (`docs/wohngeld/*`).
   - **TF‑IDF** uses character n‑grams (robust for German compounds + Arabic morphology).
   - **Semantic** uses embeddings (when available).
   - **Hybrid** combines lexical + semantic using RRF-style fusion with guardrails.

4) **Language preference**
   - The ranker prefers sources in the user’s language (DE/EN/AR), while still allowing cross‑language matches if needed.

5) **Answer generation**
   - The model is prompted to answer using the retrieved chunks.
   - The response always includes a **Sources** section with links to the underlying documents.

6) **Evaluation**
   - `python cli.py eval --both -k {3,5} --include wohngeld`
   - We report chunk metrics (diagnostic) and **file-level metrics** (product KPI) + `by_lang` breakdown.

## “Wow” feature: Trace view
In the UI you can enable **Show trace** to see a compact debug view:
- selected mode + language preference
- candidate pool sizes
- top retrieved sources + scores/ids

It makes behavior inspectable and helps explain “why did it answer that?” in a demo.

**Note on source links:** In **local** mode, sources are served via Gradio’s `/file=` route (so they open in the browser). If you prefer permanent shareable links, use **github** mode.
