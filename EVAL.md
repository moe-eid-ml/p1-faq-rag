# Evaluation — Wohngeld FAQ RAG

**Dataset:** 20 DE queries (keyword-labeled), Include=wohngeld, k=3  
**Date:** 2025-11-17

> Baseline results on a growing eval set. Metrics will improve as we refine corpus + labels.

- TF-IDF — P@3: **0.43**, R@3: **0.13**
- Semantic — P@3: **0.40**, R@3: **0.13**
- Hybrid — (pending re-run on 20-question set)

**Notes**
- Ground truth built from keywords → conservative recall.
- Corpus scoped to Wohngeld; chunking ~200 chars avg (median 177; p90 355; max 531).
- Language preference = DE; Include filter = “wohngeld”.

**Command**
```bash
make eval K=3 INCLUDE=wohngeld
