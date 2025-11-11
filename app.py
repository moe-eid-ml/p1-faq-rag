import os, glob, re
import gradio as gr
import numpy as np
from sentence_transformers import SentenceTransformer
from tfidf import TfidfRetriever

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
AR_RE = re.compile(r'[\u0600-\u06FF]')  # Arabic block

def detect_lang(s: str) -> str:
    try:
        from langdetect import detect
        code = detect(s)
        if code.startswith('de'): return "de"
        if code.startswith('ar'): return "ar"
        if code.startswith('en'): return "en"
    except Exception:
        pass
    if AR_RE.search(s): return "ar"
    s_low = s.lower()
    if any(ch in s for ch in "äöüßÄÖÜ") or re.search(r"\b(welche|unterlagen|brauche|für|zahlung|meldungen|infos|zu)\b", s_low):
        return "de"
    return "en"

def load_docs():
    docs = []
    for p in sorted(glob.glob("docs/**/*.txt", recursive=True)):
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
    if includes and not any(s.lower() in b for s in includes):
        return False
    if excludes and any(s.lower() in b for s in excludes):
        return False
    return True

docs = load_docs()
for i, d in enumerate(docs):
    d["id"] = i
DOC_INDEX = {(d["path"], d["text"]): i for i, d in enumerate(docs)}

# ---- Semantic embedder ----
embedder = SentenceTransformer(MODEL_NAME)
doc_embeddings = embedder.encode([d["text"] for d in docs], convert_to_numpy=True)
doc_embeddings = doc_embeddings / (np.linalg.norm(doc_embeddings, axis=-1, keepdims=True) + 1e-12)

def cos_scores_np(q_vec: np.ndarray, D: np.ndarray) -> np.ndarray:
    q = q_vec / (np.linalg.norm(q_vec) + 1e-12)
    return D @ q

# ---- TF-IDF retriever ----
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

def answer(query, k=3, mode="Semantic", include="", lang="auto", exclude=""):
    if not query.strip():
        return "Ask a question.", ""

    q_lang = lang if lang in ("de", "en", "ar") else detect_lang(query)
    includes = [s.strip().lower() for s in include.split(",") if s.strip()] or None
    excludes = [s.strip().lower() for s in exclude.split(",") if s.strip()] or None
    if mode == "TF-IDF":
        passages, scores = tfidf.search(query, k=max(k * 3, 12))
        order = np.argsort(scores)[::-1]
        idx_map = [DOC_INDEX.get((p["path"], p["text"])) for p in passages]
        order_idxs = [idx for j in order for idx in [idx_map[j]] if idx is not None]

    elif mode == "Hybrid":
        # Semantic ranking
        q_emb = embedder.encode(query, convert_to_numpy=True)
        sem_scores = cos_scores_np(q_emb, doc_embeddings)
        sem_order = sem_scores.argsort()[::-1].tolist()

        # TF-IDF ranking (wider pool)
        passages, scores = tfidf.search(query, k=max(k * 10, 200))
        order = np.argsort(scores)[::-1]
        idx_map = [DOC_INDEX.get((p["path"], p["text"])) for p in passages]
        tf_order = [idx for j in order for idx in [idx_map[j]] if idx is not None]

        # Reciprocal Rank Fusion (RRF)
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

    # optional filename filter
    if includes or excludes:
        order_idxs = [i for i in order_idxs if file_ok(docs[i]["path"], includes, excludes)]
    # hard language filter if user selected (keep only that lang if we have hits)
    if lang in ("de", "en", "ar"):
        filtered = [i for i in order_idxs if docs[i]["lang"] == lang]
        if filtered:
            order_idxs = filtered

    chosen = _prefer_lang(order_idxs, q_lang, k)
    top = [docs[i] for i in chosen]
    if not top:
        return "No results.", ""
    answer_text = top[0]["text"]
    sources = "\n\n".join(
        f"[{j+1}] {d['text']} (from {os.path.basename(d['path'])}, lang={d['lang']})"
        for j, d in enumerate(top)
    )
    return answer_text, sources

# ---- UI ----
CSS = """
#answer_box textarea {min-height: 300px !important; height: 300px !important;}
#source_box textarea {min-height: 180px !important; height: 180px !important;}
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
    src = gr.Textbox(label="Top sources", lines=12, interactive=True, show_copy_button=True, elem_id="source_box")
    go = gr.Button("Search")
    go.click(answer, [q, k, mode, include, lang], [ans, src])

if __name__ == "__main__":
    demo.launch()
