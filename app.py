import os, glob, re, json
from datetime import datetime
import csv
import gradio as gr
import numpy as np
from sentence_transformers import SentenceTransformer
from tfidf import TfidfRetriever
import json
from eval import evaluate_run

# ----------------- Lang detect -----------------
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
AR_RE = re.compile(r'[\u0600-\u06FF]')

def detect_lang(s: str) -> str:
    try:
        from langdetect import detect
        code = detect(s)
        if code.startswith('de'):
            return "de"
        if code.startswith('ar'):
            return "ar"
        if code.startswith('en'):
            return "en"
    except Exception:
        pass
    if AR_RE.search(s):
        return "ar"
    s_low = s.lower()
    if any(ch in s for ch in "äöüßÄÖÜ") or re.search(r"\b(welche|unterlagen|brauche|für|zahlung|meldungen|infos|zu)\b", s_low):
        return "de"
    return "en"

# ----------------- Data loading -----------------
def load_docs():
    docs = []
    for p in sorted(glob.glob("docs/**/*.txt", recursive=True)):
        # skip archived files
        if "/_archive/" in p.replace("\\", "/"):
            continue
        with open(p, "r", encoding="utf-8") as f:
            content = f.read().strip()
        fname = os.path.basename(p)
        if "_ar" in fname or AR_RE.search(content):
            lang = "ar"
        elif "_de" in fname:
            lang = "de"
        elif "_en" in fname:
            lang = "en"
        else:
            lang = "en"
        for para in [x.strip() for x in content.split("\n\n") if x.strip()]:
            docs.append({"path": p, "text": para, "lang": lang})
    return docs

def file_ok(path, includes=None, excludes=None):
    b = os.path.basename(path).lower()
    if includes and not any(s in b for s in includes):
        return False
    if excludes and any(s in b for s in excludes):
        return False
    return True

docs = load_docs()
for i, d in enumerate(docs): d["id"] = i
DOC_INDEX = {(d["path"], d["text"]): i for i, d in enumerate(docs)}

# ----------------- Retrievers -----------------
embedder = SentenceTransformer(MODEL_NAME)
doc_embeddings = embedder.encode([d["text"] for d in docs], convert_to_numpy=True)
doc_embeddings = doc_embeddings / (np.linalg.norm(doc_embeddings, axis=-1, keepdims=True) + 1e-12)

def cos_scores_np(q_vec: np.ndarray, D: np.ndarray) -> np.ndarray:
    q = q_vec / (np.linalg.norm(q_vec) + 1e-12)
    return D @ q

tfidf = TfidfRetriever(docs)

def _prefer_lang(order_idxs, q_lang, k):
    primary = [i for i in order_idxs if docs[i]["lang"] == q_lang]
    secondary = [i for i in order_idxs if docs[i]["lang"] != q_lang]
    chosen = []
    for i in primary + secondary:
        if i not in chosen:
            chosen.append(i)
        if len(chosen) == k:
            break
    return chosen

# ----------------- Answer -----------------
def log_query(row: dict):
    os.makedirs("logs", exist_ok=True)
    path = os.path.join("logs", "queries.csv")
    header = ["ts","query","mode","k","include","exclude","lang_forced","lang_detected","top_files","top_langs","answer_len","corpus_size"]
    write_header = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if write_header:
            w.writeheader()
        w.writerow(row)

def answer(query, k=3, mode="Semantic", include="", lang="auto", exclude=""):
    if not query.strip():
        return "Ask a question.", ""

    q_lang = lang if lang in ("de", "en", "ar") else detect_lang(query)
    includes = [s.strip().lower() for s in (include or "").split(",") if s.strip()] or None
    excludes = [s.strip().lower() for s in (exclude or "").split(",") if s.strip()] or None

    if mode == "TF-IDF":
        passages, scores = tfidf.search(query, k=max(k * 3, 12))
        order = np.argsort(scores)[::-1]
        idx_map = [DOC_INDEX.get((p["path"], p["text"])) for p in passages]
        order_idxs = [idx for j in order for idx in [idx_map[j]] if idx is not None]

    elif mode == "Hybrid":
        # semantic ranking
        q_emb = embedder.encode(query, convert_to_numpy=True)
        sem_scores = cos_scores_np(q_emb, doc_embeddings)
        sem_order = sem_scores.argsort()[::-1].tolist()
        # tf-idf ranking (wider pool)
        passages, scores = tfidf.search(query, k=max(k * 10, 200))
        order = np.argsort(scores)[::-1]
        idx_map = [DOC_INDEX.get((p["path"], p["text"])) for p in passages]
        tf_order = [idx for j in order for idx in [idx_map[j]] if idx is not None]
        # reciprocal rank fusion
        k0 = 60.0
        rrf = {}
        for r, i in enumerate(sem_order):
            rrf[i] = rrf.get(i, 0.0) + 1.0 / (k0 + r + 1)
        for r, i in enumerate(tf_order):
            rrf[i] = rrf.get(i, 0.0) + 1.0 / (k0 + r + 1)
        order_idxs = [i for i, _ in sorted(rrf.items(), key=lambda x: x[1], reverse=True)]

    else:  # Semantic
        q_emb = embedder.encode(query, convert_to_numpy=True)
        scores = cos_scores_np(q_emb, doc_embeddings)
        order_idxs = scores.argsort()[::-1].tolist()

    # filename filter
    if includes or excludes:
        order_idxs = [i for i in order_idxs if file_ok(docs[i]["path"], includes, excludes)]

    # forced-language with backfill up to K
    if lang in ("de", "en", "ar"):
        same = [i for i in order_idxs if docs[i]["lang"] == lang]
        if len(same) >= k:
            order_idxs = same
        else:
            backfill = [i for i in order_idxs if docs[i]["lang"] != lang]
            order_idxs = same + backfill

    # final selection with lang preference
    chosen = _prefer_lang(order_idxs, q_lang, k)
    top = [docs[i] for i in chosen]
    if not top:
        return "No results.", ""

    # -------- Sources (Markdown with highlights) --------
    def _short(s, n=240):
        s = " ".join(s.split())
        return s if len(s) <= n else s[:n-1] + "…"

    # header
    header = (
        f"**Mode:** {mode} • **Top-K:** {k} • **Include:** {include or '—'} "
        f"• **Exclude:** {exclude or '—'} • **Lang:** {q_lang}"
        f"{' (forced)' if lang in ('de','en','ar') else ''}"
    )

    # simple keyword highlights from the query
    q_tokens = re.findall(r"\w+", query.lower(), flags=re.UNICODE)
    kw = {t for t in q_tokens if len(t) >= 3}

    def highlight(text: str) -> str:
        out = text
        for kword in kw:
            out = re.sub(rf"(?iu){re.escape(kword)}", lambda m: f"**{m.group(0)}**", out)
        return out

    lines = []
    for j, d in enumerate(top):
        ts = datetime.fromtimestamp(os.path.getmtime(d['path'])).strftime('%Y-%m-%d')
        snippet = _short(highlight(d['text']))
        lines.append(f"[{j+1}] {snippet}  — `{os.path.basename(d['path'])}` • {d['lang']} • updated {ts}")

    answer_text = top[0]["text"]
    sources = "### Sources\n" + header + "\n\n" + "\n\n".join(lines)
    log_query({
        "ts": datetime.now().isoformat(timespec="seconds"),
        "query": query,
        "mode": mode,
        "k": k,
        "include": include or "",
        "exclude": exclude or "",
        "lang_forced": lang,
        "lang_detected": q_lang,
        "top_files": "|".join(os.path.basename(d["path"]) for d in top),
        "top_langs": "|".join(d["lang"] for d in top),
        "answer_len": len(answer_text),
        "corpus_size": len(docs),
    })
    return answer_text, sources

# ----------------- In-app Eval (lazy import to avoid circular) -----------------
from eval import evaluate_run
def eval_ui(k, include, lang):
    # self-contained eval (no cli import)
    k = int(k)
    includes = [s.strip().lower() for s in (include or "").split(",") if s.strip()] or None

    # load eval items
    items = []
    try:
        with open("data/wohngeld_eval.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    items.append(json.loads(line))
    except Exception as e:
        return f"**Eval error:** {e}"

    def _ground_truth_ids(item):
        kw = [x.lower() for x in item.get("keywords", [])]
        lang_item = item.get("lang", "en")
        ids = []
        for i, d in enumerate(docs):
            if d["lang"] != lang_item:
                continue
            if not file_ok(d["path"], includes, None):
                continue
            text = d["text"].lower()
            if not kw or any(kword in text for kword in kw):
                ids.append(i)
        return ids

    def _predict_ids(query, mode):
        m = mode.lower()
        if m == "tfidf":
            passages, scores = tfidf.search(query, k=max(k * 3, 12))
            order = np.argsort(scores)[::-1]
            idx_map = [DOC_INDEX.get((p["path"], p["text"])) for p in passages]
            ranked = [idx for j in order for idx in [idx_map[j]] if idx is not None]
        elif m == "hybrid":
            q_emb = embedder.encode(query, convert_to_numpy=True)
            sem_scores = cos_scores_np(q_emb, doc_embeddings)
            sem_order = sem_scores.argsort()[::-1].tolist()
            passages, scores = tfidf.search(query, k=max(k * 10, 200))
            order = np.argsort(scores)[::-1]
            idx_map = [DOC_INDEX.get((p["path"], p["text"])) for p in passages]
            tf_order = [idx for j in order for idx in [idx_map[j]] if idx is not None]
            k0 = 60.0
            rrf = {}
            for r, i in enumerate(sem_order):
                rrf[i] = rrf.get(i, 0.0) + 1.0 / (k0 + r + 1)
            for r, i in enumerate(tf_order):
                rrf[i] = rrf.get(i, 0.0) + 1.0 / (k0 + r + 1)
            ranked = [i for i, _ in sorted(rrf.items(), key=lambda x: x[1], reverse=True)]
        else:  # semantic
            q_emb = embedder.encode(query, convert_to_numpy=True)
            scores = cos_scores_np(q_emb, doc_embeddings)
            ranked = scores.argsort()[::-1].tolist()

        # filename filter + language preference to top-k
        ranked = [i for i in ranked if file_ok(docs[i]["path"], includes, None)]
        q_lang = detect_lang(query)
        ranked = _prefer_lang(ranked, q_lang, k)
        return ranked

    gt = [_ground_truth_ids(it) for it in items]
    lines = []
    for m in ["tfidf", "semantic", "hybrid"]:
        preds = [_predict_ids(it["q"], m) for it in items]
        res = evaluate_run(gt, preds, k=k)
        lines.append(f"- {m.title()}: **P@{k} = {res['p_at_k']:.2f}**, **R@{k} = {res['r_at_k']:.2f}**")
    return "### Eval (data/wohngeld_eval.jsonl)\n" + "\n".join(lines)
def _reset_defaults():
    # k, mode, include, exclude, lang
    return 3, "Hybrid", "wohngeld", "", "auto"
def _reset_defaults():
    # k, mode, include, exclude, lang
    return 3, "Hybrid", "wohngeld", "", "auto"

# ----------------- UI -----------------
CSS = """
#answer_box textarea {min-height: 300px !important; height: 300px !important;}
#source_box {min-height: 180px !important;}
"""

with gr.Blocks(css=CSS, title="P1 — Mini FAQ (EN/DE/AR)") as demo:
    gr.Markdown("### Multilingual FAQ (EN/DE/AR) — language-aware retrieval")
    with gr.Row():
        q = gr.Textbox(label="Your question", lines=4, scale=3, placeholder="Ask in English, Deutsch, or العربية")
        k = gr.Slider(1, 5, step=1, value=3, label="Top-K", scale=1)
        mode = gr.Radio(choices=["Semantic","TF-IDF","Hybrid"], value="Hybrid", label="Retrieval mode")
        include = gr.Textbox(
            label="Include filenames (comma-separated, optional)",
            placeholder="e.g. wohngeld, faq",
            value="wohngeld",
            scale=1
        )
        exclude = gr.Textbox(
            label="Exclude filenames (comma-separated, optional)",
            placeholder="e.g. pdf, bescheid, scan",
            value="",
            scale=1
        )
        lang = gr.Dropdown(
            label="Language (override)",
            choices=["auto", "de", "en", "ar"],
            value="auto",
            scale=1
        )
    ans = gr.Textbox(label="Answer", lines=16, interactive=True, show_copy_button=True, elem_id="answer_box")
    src = gr.Markdown(label="Top sources", elem_id="source_box")

    go = gr.Button("Search")
    go.click(answer, [q, k, mode, include, lang, exclude], [ans, src])
    reset = gr.Button("Reset filters")
    reset.click(_reset_defaults, [], [k, mode, include, exclude, lang])
    with gr.Row():
        ebtn = gr.Button("Evaluate (P@K / R@K)")
        emd = gr.Markdown()
    ebtn.click(eval_ui, [k, include, lang], [emd])

if __name__ == "__main__":
    demo.launch()
