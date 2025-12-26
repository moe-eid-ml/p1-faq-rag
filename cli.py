import argparse
import json
from os.path import basename

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None

import app

try:
    # Most repos here have eval.py at repo root
    from eval import evaluate_run
except Exception:  # pragma: no cover
    # Fallback if eval lives under app_pkg/
    from app_pkg.eval import evaluate_run  # type: ignore


_SEM_MODEL = None
_SEM_X = None


def _ensure_semantic():
    global _SEM_MODEL, _SEM_X
    if _SEM_MODEL is not None and _SEM_X is not None:
        return
    if SentenceTransformer is None:
        return
    try:
        _SEM_MODEL = SentenceTransformer(getattr(app, "MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"))
        emb = _SEM_MODEL.encode(
            [d["text"] for d in app.docs],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        _SEM_X = np.asarray(emb, dtype=np.float32)
    except Exception:
        _SEM_MODEL = None
        _SEM_X = None


def semantic_available() -> bool:
    _ensure_semantic()
    return _SEM_MODEL is not None and _SEM_X is not None


def load_eval(path: str = "data/wohngeld_eval.jsonl"):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def file_ok(path: str, includes=None, excludes=None) -> bool:
    b = basename(path).lower()
    if includes and not any(s.lower() in b for s in includes):
        return False
    if excludes and any(s.lower() in b for s in excludes):
        return False
    return True


def ground_truth_ids(item, includes=None, excludes=None):
    kw = [k.lower() for k in item.get("keywords", [])]
    lang = item.get("lang", "en")
    ids = []
    for i, d in enumerate(app.docs):
        if d.get("lang") != lang:
            continue
        if not file_ok(d.get("path", ""), includes, excludes):
            continue
        text = d.get("text", "").lower()
        if any(k in text for k in kw) or not kw:
            ids.append(i)
    return ids


def _file_key(doc_id: int) -> str:
    return basename(app.docs[doc_id]["path"]).lower()


def _unique_preserve_order(items):
    out = []
    seen = set()
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def to_file_ids(doc_ids, file_id_map):
    keys = _unique_preserve_order(_file_key(i) for i in doc_ids)
    return [file_id_map[k] for k in keys if k in file_id_map]


def ground_truth_file_ids(item, file_id_map, includes=None, excludes=None):
    # If the eval item specifies relevant files explicitly, use that as file-level GT.
    rf = item.get("relevant_files")
    if rf:
        out = []
        for f in rf:
            key = basename(f).lower()
            if key in file_id_map:
                out.append(file_id_map[key])
        return _unique_preserve_order(out)

    # Fallback: derive file-level GT from chunk-level GT (keywords-based).
    ids = ground_truth_ids(item, includes, excludes)
    return to_file_ids(ids, file_id_map)


def predict_ids(query, mode, k, includes=None, excludes=None, q_lang_override=None):
    m = mode.lower()

    if m == "tfidf":
        passages, scores = app.tfidf.search(query, k=max(k * 10, 200))
        order = np.argsort(scores)[::-1]
        idx_map = [app.DOC_INDEX.get((p["path"], p["text"])) for p in passages]
        ranked = [idx for j in order for idx in [idx_map[j]] if idx is not None]

    elif m == "hybrid":
        if not semantic_available():
            passages, scores = app.tfidf.search(query, k=max(k * 10, 200))
            order = np.argsort(scores)[::-1]
            idx_map = [app.DOC_INDEX.get((p["path"], p["text"])) for p in passages]
            ranked = [idx for j in order for idx in [idx_map[j]] if idx is not None]
        else:
            # semantic ranking
            q_emb = _SEM_MODEL.encode([query], normalize_embeddings=True, show_progress_bar=False)
            q_emb = np.asarray(q_emb, dtype=np.float32).reshape(-1)
            sem_scores = _SEM_X @ q_emb
            sem_order = sem_scores.argsort()[::-1].tolist()

            # tf-idf (wider pool)
            passages, scores = app.tfidf.search(query, k=max(k * 10, 200))
            order = np.argsort(scores)[::-1]
            idx_map = [app.DOC_INDEX.get((p["path"], p["text"])) for p in passages]
            tf_order = [idx for j in order for idx in [idx_map[j]] if idx is not None]

            # RRF guardrails (match app.py)
            SEM_CAND = 300
            TF_CAND = min(len(tf_order), 1200)
            k0 = 90.0
            rrf = {}
            for r, i in enumerate(tf_order[:TF_CAND]):
                rrf[i] = rrf.get(i, 0.0) + 1.0 / (k0 + r + 1)
            for r, i in enumerate(sem_order[:SEM_CAND]):
                rrf[i] = rrf.get(i, 0.0) + 1.0 / (k0 + r + 1)
            ranked = [i for i, _ in sorted(rrf.items(), key=lambda x: x[1], reverse=True)]

    else:  # semantic
        if not semantic_available():
            passages, scores = app.tfidf.search(query, k=max(k * 10, 200))
            order = np.argsort(scores)[::-1]
            idx_map = [app.DOC_INDEX.get((p["path"], p["text"])) for p in passages]
            ranked = [idx for j in order for idx in [idx_map[j]] if idx is not None]
        else:
            q_emb = _SEM_MODEL.encode([query], normalize_embeddings=True, show_progress_bar=False)
            q_emb = np.asarray(q_emb, dtype=np.float32).reshape(-1)
            scores = _SEM_X @ q_emb
            ranked = scores.argsort()[::-1].tolist()

    # filename filter
    ranked = [i for i in ranked if file_ok(app.docs[i]["path"], includes, excludes)]

    # language preference (use eval item's declared lang when provided)
    q_lang = q_lang_override or app.detect_lang(query)
    primary = [i for i in ranked if app.docs[i]["lang"] == q_lang]
    secondary = [i for i in ranked if app.docs[i]["lang"] != q_lang]

    out = []
    for i in primary + secondary:
        if i not in out:
            out.append(i)
        if len(out) == k:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    # ---- eval ----
    p_eval = sub.add_parser("eval", help="Run retrieval eval on JSONL queries")
    p_eval.add_argument("--mode", choices=["tfidf", "semantic", "hybrid"], default="semantic")
    p_eval.add_argument("-k", type=int, default=3)
    p_eval.add_argument("--file", default="data/wohngeld_eval.jsonl")
    p_eval.add_argument("--both", action="store_true")
    p_eval.add_argument("--include", action="append")
    p_eval.add_argument("--exclude", action="append")

    # ---- ask ----
    p_ask = sub.add_parser("ask", help="Ask a question via the CLI")
    p_ask.add_argument("q", help="User question")
    p_ask.add_argument("--mode", choices=["TF-IDF", "Semantic", "Hybrid"], default="Semantic")
    p_ask.add_argument("-k", type=int, default=3)
    p_ask.add_argument("--include", default="", help="Substring filter for filenames (single string)")
    p_ask.add_argument("--exclude", default="", help="Substring exclude filter for filenames (single string)")
    p_ask.add_argument("--lang", choices=["auto", "de", "en", "ar"], default="auto")
    p_ask.add_argument("--link-mode", choices=["github", "plain"], default="github")
    p_ask.add_argument("--trace", action="store_true", help="Print retrieval trace JSON")

    args = ap.parse_args()

    if args.cmd == "ask":
        if args.trace:
            ans, src, tr = app.answer(
                args.q,
                k=args.k,
                mode=args.mode,
                include=args.include,
                lang=args.lang,
                exclude=args.exclude,
                link_mode=args.link_mode,
                trace=True,
            )
            print(ans)
            print()
            print(src)
            print()
            print("--- TRACE ---")
            print(tr)
        else:
            ans, src = app.answer(
                args.q,
                k=args.k,
                mode=args.mode,
                include=args.include,
                lang=args.lang,
                exclude=args.exclude,
                link_mode=args.link_mode,
            )
            print(ans)
            print()
            print(src)
        return

    # ---- eval ----
    items = load_eval(args.file)
    gt = [ground_truth_ids(it, args.include, args.exclude) for it in items]

    all_files = sorted({basename(d["path"]).lower() for d in app.docs})
    file_id_map = {f: i for i, f in enumerate(all_files)}
    gt_files = [ground_truth_file_ids(it, file_id_map, args.include, args.exclude) for it in items]

    modes = ["tfidf", "semantic", "hybrid"] if args.both else [args.mode]
    for m in modes:
        preds = [predict_ids(it["q"], m, args.k, args.include, args.exclude, q_lang_override=it.get("lang")) for it in items]
        res = evaluate_run(gt, preds, k=args.k)

        preds_files = [to_file_ids(p, file_id_map) for p in preds]
        res_files = evaluate_run(gt_files, preds_files, k=args.k)

        # Per-language breakdown
        by_lang = {}
        for L in sorted({it.get("lang", "en") for it in items}):
            idxs = [i for i, it in enumerate(items) if it.get("lang", "en") == L]
            if not idxs:
                continue
            gt_L = [gt[i] for i in idxs]
            pr_L = [preds[i] for i in idxs]
            gtF_L = [gt_files[i] for i in idxs]
            prF_L = [preds_files[i] for i in idxs]
            rL = evaluate_run(gt_L, pr_L, k=args.k)
            rFL = evaluate_run(gtF_L, prF_L, k=args.k)
            by_lang[L] = {
                "p_at_k": rL["p_at_k"],
                "r_at_k": rL["r_at_k"],
                "file_p_at_k": rFL["p_at_k"],
                "file_r_at_k": rFL["r_at_k"],
                "queries": len(idxs),
            }

        print(
            json.dumps(
                {
                    "mode": m,
                    **res,
                    "file_p_at_k": res_files["p_at_k"],
                    "file_r_at_k": res_files["r_at_k"],
                    "by_lang": by_lang,
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
