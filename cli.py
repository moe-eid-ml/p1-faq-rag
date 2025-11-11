import argparse, json
from os.path import basename
import numpy as np

import app
from eval import evaluate_run

def load_eval(path="data/wohngeld_eval.jsonl"):
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items

def file_ok(path, includes=None, excludes=None):
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
        if d["lang"] != lang:
            continue
        if not file_ok(d["path"], includes, excludes):
            continue
        text = d["text"].lower()
        if any(k in text for k in kw) or not kw:
            ids.append(i)
    return ids

def predict_ids(query, mode, k, includes=None, excludes=None):
    m = mode.lower()
    if m == "tfidf":
        passages, scores = app.tfidf.search(query, k=max(k * 3, 12))
        order = np.argsort(scores)[::-1]
        idx_map = [app.DOC_INDEX.get((p["path"], p["text"])) for p in passages]
        ranked = [idx for j in order for idx in [idx_map[j]] if idx is not None]

    elif m == "hybrid":
        # semantic ranking
        q_emb = app.embedder.encode(query, convert_to_numpy=True)
        sem_scores = app.cos_scores_np(q_emb, app.doc_embeddings)
        sem_order = sem_scores.argsort()[::-1].tolist()
        # tf-idf (wider pool)
        passages, scores = app.tfidf.search(query, k=max(k * 10, 200))
        order = np.argsort(scores)[::-1]
        idx_map = [app.DOC_INDEX.get((p["path"], p["text"])) for p in passages]
        tf_order = [idx for j in order for idx in [idx_map[j]] if idx is not None]
        # reciprocal rank fusion
        k0 = 60.0
        rrf = {}
        for r, i in enumerate(sem_order):
            rrf[i] = rrf.get(i, 0.0) + 1.0 / (k0 + r + 1)
        for r, i in enumerate(tf_order):
            rrf[i] = rrf.get(i, 0.0) + 1.0 / (k0 + r + 1)
        ranked = [i for i, _ in sorted(rrf.items(), key=lambda x: x[1], reverse=True)]

    else:  # semantic
        q_emb = app.embedder.encode(query, convert_to_numpy=True)
        scores = app.cos_scores_np(q_emb, app.doc_embeddings)
        ranked = scores.argsort()[::-1].tolist()

    # filename filter
    ranked = [i for i in ranked if file_ok(app.docs[i]["path"], includes, excludes)]
    # language preference
    q_lang = app.detect_lang(query)
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
    ap.add_argument("cmd", choices=["eval"])
    ap.add_argument("--mode", choices=["tfidf","semantic","hybrid"], default="semantic")
    ap.add_argument("-k", type=int, default=3)
    ap.add_argument("--file", default="data/wohngeld_eval.jsonl")
    ap.add_argument("--both", action="store_true")
    ap.add_argument("--include", action="append")
    ap.add_argument("--exclude", action="append")
    args = ap.parse_args()

    items = load_eval(args.file)
    gt = [ground_truth_ids(it, args.include, args.exclude) for it in items]

    modes = ["tfidf","semantic"] if args.both else [args.mode]
    for m in modes:
        preds = [predict_ids(it["q"], m, args.k, args.include, args.exclude) for it in items]
        res = evaluate_run(gt, preds, k=args.k)
        print(json.dumps({"mode": m, **res}, ensure_ascii=False))

if __name__ == "__main__":
    main()
