import os, glob, re
import gradio as gr
import numpy as np
from sentence_transformers import SentenceTransformer
from tfidf import TfidfRetriever

# --- env config (.env + sane defaults) ---
import os
import json
from dotenv import load_dotenv
load_dotenv()

INDEX_PATH = os.getenv("INDEX_PATH", "build/index.json")
AR_PATH    = os.getenv("AR_PATH", "docs/faq/ar")

def load_corpus():
    """
    Prefer a prebuilt JSON index at INDEX_PATH.
    If missing, fall back to parsing Arabic FAQ files in AR_PATH.
    """
    import os, json, glob, pathlib

    # 1) Prebuilt index (fast path)
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    # 2) Fallback: parse raw files
    items = []
    for p in sorted(glob.glob(f"{AR_PATH}/**/*.txt", recursive=True)):
        text = open(p, encoding="utf-8").read()
        lines = [l.rstrip() for l in text.splitlines()]
        # Extract first Q: line
        q = next((l[2:].strip() for l in lines if l.startswith("Q:")), "")
        # Extract everything after first A:
        a = text.split("A:", 1)[1].strip() if "A:" in text else ""
        items.append({"id": pathlib.Path(p).stem, "q": q, "a": a, "path": str(p)})
    return items

def load_corpus_v2():
    """
    Prefer INDEX_PATH JSON; include docs/wohngeld/*.txt; else parse AR_PATH.
    Ensures every doc has 'text' and 'lang'.
    """
    import os, json, glob, pathlib, re
    ARABIC = re.compile(r'[\u0600-\u06FF]')
    items, seen = [], set()

    def _add(d):
        p = d.get("path","")
        if p in seen: return
        seen.add(p)
        txt = d.get("text") or ((d.get("q","") + "\n" + d.get("a","")).strip())
        d["text"] = txt
        d["lang"] = d.get("lang") or ("ar" if ARABIC.search(txt) else "en")
        d["id"] = d.get("id") or d.get("path") or str(len(items))
        items.append(d)

    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            for d in json.load(f):
                _add({"id": d.get("id"), "q": d.get("q",""), "a": d.get("a",""),
                      "text": d.get("text"), "path": d.get("path",""), "lang": d.get("lang")})

    for p in sorted(glob.glob("docs/wohngeld/*.txt")):
        name = pathlib.Path(p).name.lower()
        txt = open(p, encoding="utf-8").read()
        lang = "de" if "_de" in name else "en" if "_en" in name else ("ar" if ARABIC.search(txt) else "en")
        _add({"id": name, "q": "", "a": "", "text": txt, "path": p, "lang": lang})

    if not items:
        for p in sorted(glob.glob(f"{AR_PATH}/**/*.txt", recursive=True)):
            t = open(p, encoding="utf-8").read()
            lines = [l.rstrip() for l in t.splitlines()]
            q = next((l[2:].strip() for l in lines if l.startswith("Q:")), "")
            a = t.split("A:", 1)[1].strip() if "A:" in t else ""
            _add({"id": pathlib.Path(p).stem, "q": q, "a": a,
                  "text": (q + "\n" + a).strip(), "path": p, "lang": "ar"})
    return items

# --- initialize corpus (prefers build/index.json, falls back to docs/faq/ar) ---
CORPUS = load_corpus_v2()

# Back-compat aliases (in case the rest of the app expects these names)
DOCUMENTS = CORPUS
INDEX = CORPUS

# --- back-compat: ensure each doc has 'text' ---
for d in CORPUS:
    if "text" not in d:
        d["text"] = ((d.get("q","") + "\n" + d.get("a","")).strip())

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

docs = CORPUS
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
    primary = [i for i in order_idxs if docs[i].get("lang") == q_lang]
    fallback = [i for i in order_idxs if docs[i].get("lang") != q_lang]
    picked = (primary + fallback)[:k] if primary else fallback[:k]
    return picked

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
    # compact sources with header, dates, and keyword highlights
    from datetime import datetime
    def _short(s, n=240):
        s = " ".join(s.split())
        return s if len(s) <= n else s[:n-1] + "…"

    # simple keyword highlights from the query (len ≥ 3)
    q_tokens = re.findall(r"\w+", query.lower(), flags=re.UNICODE)
    kw = {t for t in q_tokens if len(t) >= 3}

    def highlight(text: str) -> str:
        out = text
        for k in kw:
            out = re.sub(rf"(?iu){re.escape(k)}", lambda m: f"**{m.group(0)}**", out)
        return out

    header = (
        f"**Mode:** {mode} • **Top-K:** {k} • **Include:** {include or '—'} "
        f"• **Exclude:** {locals().get('exclude','') or '—'} • **Lang:** {q_lang}"
        f"{' (forced)' if lang in ('de','en','ar') else ''}"
    )

    lines = []
    for j, d in enumerate(top):
        ts = datetime.fromtimestamp(os.path.getmtime(d['path'])).strftime('%Y-%m-%d')
        snippet = _short(highlight(d['text']))
        lines.append(f"[{j+1}] {snippet}  — `{os.path.basename(d['path'])}` • {d['lang']} • updated {ts}")

    sources = header + "\n\n" + "\n\n".join(lines)
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
    src = gr.Markdown(label="Top sources", elem_id="source_box")
    go = gr.Button("Search")
    go.click(answer, [q, k, mode, include, lang], [ans, src])

if __name__ == "__main__":
    demo.launch()
