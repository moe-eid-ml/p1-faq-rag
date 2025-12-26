# Roadmap

This document defines the finish line for `p1-faq-rag` and the prioritized work plan.

## Metrics & evaluation

We track two retrieval metrics:

- **Chunk-level** (`p_at_k`, `r_at_k`): strict, paragraph/chunk precision/recall (diagnostic).
- **File-level** (`file_p_at_k`, `file_r_at_k`): did we retrieve the correct document/file (product-facing KPI).

We also track metrics **by language** (DE/EN/AR) to avoid a single language dominating the KPI (Arabic can behave differently for lexical matching).

> Target improvements should be validated via `python cli.py eval --both -k {3,5} --include wohngeld`.

## Definition of Done (Core v1)

Core is considered **done** when all items below are true on `main`:

1) **Stability**
   - HF Space loads and answers queries (no crashes).
   - `CI` + `FAQ Pipeline CI` are green.

2) **Reproducibility**
   - On a clean clone: `make run`, `make prepush`, `make smoke`, `make eval` work.

3) **Reliability behavior**
   - Nonsense input → **Abstain** (no guessing).
   - Topic-only input (e.g., `Wohngeld`) → **Clarify** (1–4).
   - Normal query → answer + `Source: [n]`.

4) **Privacy**
   - Query logging is **opt-in** locally (default off) and **always off** on HF Space.

5) **Minimum retrieval KPI (Wohngeld)**
   - **file_p@3 ≥ 0.60** and **file_p@5 ≥ 0.55** on `data/wohngeld_eval.jsonl`.
   - Chunk metrics are tracked but not used as the release gate (they are intentionally strict).

## Work plan (priority order)

### P0 — Hit the Core v1 KPI (high ROI)

- Expand and tighten eval labels:
  - Add more queries (goal: 40–60 total; balanced DE/EN/AR).
  - Prefer **specific keywords** per query (avoid `["wohngeld"]`-only ground truth).
  - Optional upgrade: add `relevant_files` field for explicit file-level ground truth on key queries.

- Improve lexical retrieval:
  - Confirm the fused TF-IDF is actually used in the app path.
  - Tune weights (`w_char`, `w_word`) using eval results.
  - Keep **character n-grams** as the baseline (robust for German compounds and Arabic morphology); tune `w_char/w_word` with eval.

- Improve Hybrid ranking:
  - Keep RRF fusion.
  - Tune RRF constant (`k0`) and candidate pool size.

### P1 — “Proof + demo polish” (after KPI is hit)

- Add a short “Demo script” (3–4 prompts) for the Space.
- Keep README aligned with behavior (no internal TODO lists).
- Add one or two smoke regressions for the top failure modes.

### P2 — Optional “nice extras” (only after Core v1 is done)

- Lightweight reranker (cross-encoder or small rerank step) and measure impact.
- Confidence/calibration score to tune and explain abstain thresholds (abstain/clarify behavior exists in Core v1; calibration is a refinement).
- Simple API (FastAPI) and/or Docker packaging.

## Working style (to avoid churn)

- Batch changes locally; push only at checkpoints.
- One checkpoint = `make prepush` passes + a coherent commit message.
- If metrics don’t improve after 2–3 iterations, stop and re-scope the eval definition before continuing.