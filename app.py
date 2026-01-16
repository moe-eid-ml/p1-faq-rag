import os
import glob
import re
import json
import numpy as np
import csv
import hashlib
import uuid


# Gradio is optional: tests/CI import this module without needing the UI.
try:
    import gradio as gr
except Exception:
    gr = None

from tfidf import TfidfRetriever
import datetime as _dt

from app_pkg.lang import detect_lang, AR_RE
from app_pkg.retrieval import source_url
from kosniper.contracts import TrafficLight
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

GITHUB_BLOB_BASE = "https://github.com/moe-eid-ml/p1-faq-rag/blob/main/"
SEMANTIC_DISABLED = os.getenv("DISABLE_SEMANTIC", "0") == "1"


class SemanticUnavailableError(RuntimeError):
    """Raised when semantic retrieval is requested but unavailable in strict mode."""


# ----------------- Lang detect -----------------
# logging flags: opt-in locally, always disable on Hugging Face Spaces
IS_SPACE = bool(os.getenv("SPACE_ID") or os.getenv("HF_SPACE"))
LOG_QUERIES = (os.getenv("LOG_QUERIES", "0") == "1") and (not IS_SPACE)

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

#
# ----------------- Retrievers -----------------
# --- Semantic embedder (lazy + optional, with on-disk cache) ---
BUILD_DIR = "build"
EMB_NPY = os.path.join(BUILD_DIR, "doc_embeddings.npy")
EMB_META = os.path.join(BUILD_DIR, "doc_embeddings.meta")

embedder = None
doc_embeddings = None
_semantic_ready = False

def semantic_ready() -> bool:
    return bool(_semantic_ready)

def ensure_semantic_ready() -> bool:
    _init_embeddings()
    return bool(_semantic_ready)

def _emb_cache_key(model_name, _docs):
    mts = [os.path.getmtime(d["path"]) for d in _docs]
    return f"{model_name}|{len(_docs)}|{int(sum(mts))}"

def _init_embeddings():
    """Init embeddings lazily.

    If `sentence_transformers` isn't installed, keep semantic disabled and allow
    TF-IDF-only operation (tests + basic usage).
    """
    global embedder, doc_embeddings, _semantic_ready
    if _semantic_ready:
        return
    if SEMANTIC_DISABLED:
        _semantic_ready = False
        return

    try:
        from sentence_transformers import SentenceTransformer
    except ModuleNotFoundError:
        _semantic_ready = False
        return

    os.makedirs(BUILD_DIR, exist_ok=True)
    embedder = SentenceTransformer(MODEL_NAME)
    texts = [d["text"] for d in docs]
    _key = _emb_cache_key(MODEL_NAME, docs)

    try:
        if os.path.exists(EMB_NPY) and os.path.exists(EMB_META):
            with open(EMB_META, "r", encoding="utf-8") as f:
                if f.read().strip() == _key:
                    doc_embeddings = np.load(EMB_NPY)
                else:
                    raise FileNotFoundError
        else:
            raise FileNotFoundError
    except Exception:
        doc_embeddings = embedder.encode(texts, convert_to_numpy=True)
        np.save(EMB_NPY, doc_embeddings)
        with open(EMB_META, "w", encoding="utf-8") as f:
            f.write(_key)

    # L2-normalize once
    doc_embeddings = doc_embeddings / (np.linalg.norm(doc_embeddings, axis=-1, keepdims=True) + 1e-12)
    _semantic_ready = True

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
    if not LOG_QUERIES:
        return
    os.makedirs("logs", exist_ok=True)
    path = os.path.join("logs", "queries.csv")
    header = ["ts","query","mode","k","include","exclude","lang_forced","lang_detected","top_files","top_langs","answer_len","corpus_size"]
    write_header = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if write_header:
            w.writeheader()
        w.writerow(row)

def answer(query, k=3, mode="Semantic", include="", lang="auto", exclude="", link_mode="github", trace: bool = False, strict: bool = False):
    if not query.strip():
        if trace:
            trace_id = str(uuid.uuid4())
            ts = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            pipeline_version = os.getenv("GITHUB_SHA") or os.getenv("SNIPER_PIPELINE_VERSION") or "dev"

            sniper_trace_v1 = {
                "trace_id": trace_id,
                "timestamp": ts,
                "query": query,
                "verdict": TrafficLight.YELLOW.name,
                "verdict_reason": "empty_query",
                "answer": None,
                "sources": [],
                "model_version": os.getenv("MODEL_VERSION", "unknown"),
                "pipeline_version": pipeline_version,
            }

            trace_payload = {
                "mode": mode,
                "include": include,
                "exclude": exclude,
                "k": k,
                "link_mode": link_mode,
                "query": query,
                "sniper_trace_v1": sniper_trace_v1,
            }

            return "Ask a question.", "", json.dumps(trace_payload, ensure_ascii=False, indent=2)

        return "Ask a question.", ""

    # If the user replies with 1–4 from the clarify prompt, expand into a concrete query.
    _q0 = query.strip()
    if _q0 and _q0[0] in {"1", "2", "3", "4"}:
        _sel = _q0[0]
        rest = _q0[1:]

        ok = False
        extra = ""
        if rest == "":
            ok = True
        else:
            # Allow: "  ..." or ".)/:/- ..." (separator must be followed by whitespace).
            m = re.match(r"^(?:\s+|[\)\:\-]\s+|\.\s+)(.*)$", rest)
            if m:
                ok = True
                extra = (m.group(1) or "").strip()

        if ok:
            _expand = {
                "1": "Wohngeld eligibility requirements Voraussetzungen wer kann beantragen",
                "2": "Wohngeld required documents Unterlagen Nachweise beizufügen",
                "3": "Wohngeld income calculation Einkommen Freibeträge Vermögen berücksichtigt",
                "4": "Wohngeld where to apply Antrag stellen zuständig Bearbeitungszeit",
            }[_sel]
            query = f"{_expand} {extra}".strip()

    q_lang = lang if lang in ("de", "en", "ar") else detect_lang(query)

    trace_payload = None
    if trace:
        trace_payload = {
            "mode": mode,
            "lang_arg": lang,
            "q_lang": q_lang,
            "k": k,
            "include": include,
            "exclude": exclude,
            "link_mode": link_mode,
            "semantic_ready": _semantic_ready,
        }

    # Heuristic: English questions containing "Wohngeld" can be misdetected as German.
    # We only apply this in auto mode to avoid overriding an explicit user choice.
    if lang == "auto" and q_lang == "de":
        _toks = set(re.findall(r"[A-Za-z]+", query.lower()))
        _en_hint = {
            "what","which","where","when","why","how",
            "documents","required","need","apply","application","processing","time",
            "eligibility","income","rent","proof",
        }
        _de_hint = {
            "unterlagen","antrag","berechnung","einkommen","bearbeitung","mietstufe",
            "voraussetzungen","anspruch","wer","wie","wo","wann","dauer",
        }
        if (len(_toks & _en_hint) >= 2) and (len(_toks & _de_hint) == 0):
            q_lang = "en"
    includes = [s.strip().lower() for s in (include or "").split(",") if s.strip()] or None
    excludes = [s.strip().lower() for s in (exclude or "").split(",") if s.strip()] or None

    def _tfidf_pool() -> int:
        # Wider pool helps ensure language preference has candidates (especially EN/AR).
        pool = max(k * 10, 200)
        if q_lang in ("en", "ar"):
            pool = max(pool, 1200)
        return pool

    # retrieval confidence helpers
    tfidf_score_by_id = {}
    used_semantic_scores = False

    if mode == "TF-IDF":
        passages, scores = tfidf.search(query, k=_tfidf_pool())
        order = np.argsort(scores)[::-1]
        idx_map = [DOC_INDEX.get((p["path"], p["text"])) for p in passages]
        order_idxs = [idx for j in order for idx in [idx_map[j]] if idx is not None]
        for p, s in zip(passages, scores):
            idx = DOC_INDEX.get((p["path"], p["text"]))
            if idx is None:
                continue
            prev = tfidf_score_by_id.get(idx)
            s = float(s)
            if prev is None or s > prev:
                tfidf_score_by_id[idx] = s

    elif mode == "Hybrid":
        # 1) semantic query embedding (once)
        _init_embeddings()
        if not _semantic_ready:
            if strict:
                raise SemanticUnavailableError("Semantic embeddings unavailable (strict mode)")
            mode = "TF-IDF"
        if mode == "Hybrid":
            q_emb = embedder.encode(query, convert_to_numpy=True)
            sem_scores = cos_scores_np(q_emb, doc_embeddings)
            used_semantic_scores = True

            # 2) lexical candidate pool (broad)
            passages, scores = tfidf.search(query, k=_tfidf_pool())
            order = np.argsort(scores)[::-1]
            idx_map = [DOC_INDEX.get((p["path"], p["text"])) for p in passages]
            tf_order = [idx for j in order for idx in [idx_map[j]] if idx is not None]

            # 3) fuse semantic + lexical using Reciprocal Rank Fusion (RRF)
            # Guardrail: only let semantic vote with its top-N to avoid long-tail noise.
            sem_order = sem_scores.argsort()[::-1].tolist()
            SEM_CAND = 300
            TF_CAND = min(len(tf_order), 1200)
            k0 = 90.0

            rrf = {}
            # Lexical first: if TF-IDF already found the right file, don't let semantic tail drag it down.
            for r, i in enumerate(tf_order[:TF_CAND]):
                rrf[i] = rrf.get(i, 0.0) + 1.0 / (k0 + r + 1)
            for r, i in enumerate(sem_order[:SEM_CAND]):
                rrf[i] = rrf.get(i, 0.0) + 1.0 / (k0 + r + 1)

            order_idxs = [i for i, _ in sorted(rrf.items(), key=lambda x: x[1], reverse=True)]
        else:
            passages, scores = tfidf.search(query, k=_tfidf_pool())
            order = np.argsort(scores)[::-1]
            idx_map = [DOC_INDEX.get((p["path"], p["text"])) for p in passages]
            order_idxs = [idx for j in order for idx in [idx_map[j]] if idx is not None]
            for p, s in zip(passages, scores):
                idx = DOC_INDEX.get((p["path"], p["text"]))
                if idx is None:
                    continue
                prev = tfidf_score_by_id.get(idx)
                s = float(s)
                if prev is None or s > prev:
                    tfidf_score_by_id[idx] = s
    else:  # Semantic
        _init_embeddings()
        if not _semantic_ready:
            if strict:
                raise SemanticUnavailableError("Semantic embeddings unavailable (strict mode)")
            # fallback to TF-IDF if semantic deps are missing
            passages, scores = tfidf.search(query, k=_tfidf_pool())
            order = np.argsort(scores)[::-1]
            idx_map = [DOC_INDEX.get((p["path"], p["text"])) for p in passages]
            order_idxs = [idx for j in order for idx in [idx_map[j]] if idx is not None]
            for p, s in zip(passages, scores):
                idx = DOC_INDEX.get((p["path"], p["text"]))
                if idx is None:
                    continue
                prev = tfidf_score_by_id.get(idx)
                s = float(s)
                if prev is None or s > prev:
                    tfidf_score_by_id[idx] = s
        else:
            q_emb = embedder.encode(query, convert_to_numpy=True)
            scores = cos_scores_np(q_emb, doc_embeddings)
            used_semantic_scores = True
            order_idxs = scores.argsort()[::-1].tolist()
    # filename filter (run AFTER we have order_idxs)
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
        if trace:
            trace_id = str(uuid.uuid4())
            ts = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            pipeline_version = os.getenv("GITHUB_SHA") or os.getenv("SNIPER_PIPELINE_VERSION") or "dev"

            sniper_trace_v1 = {
                "trace_id": trace_id,
                "timestamp": ts,
                "query": query,
                "verdict": TrafficLight.YELLOW.name,
                "verdict_reason": "no_results",
                "answer": None,
                "sources": [],
                "model_version": os.getenv("MODEL_VERSION", "unknown"),
                "pipeline_version": pipeline_version,
            }

            trace_payload = {
                "mode": mode,
                "include": include,
                "exclude": exclude,
                "k": k,
                "link_mode": link_mode,
                "query": query,
                "sniper_trace_v1": sniper_trace_v1,
            }

            return "No results.", "", json.dumps(trace_payload, ensure_ascii=False, indent=2)

        return "No results.", ""

    # -------- Abstain gate (MVP) --------
    def _score_for(idx: int):
        if used_semantic_scores:
            try:
                if mode == "Hybrid":
                    return float(sem_scores[idx])
                return float(scores[idx])
            except Exception:
                return None
        return tfidf_score_by_id.get(idx)

    s1 = _score_for(chosen[0]) if chosen else None
    s2 = _score_for(chosen[1]) if len(chosen) > 1 else None

    # Thresholds are intentionally conservative; we’ll tune later with a few examples.
    if used_semantic_scores:
        MIN_TOP, MIN_GAP = 0.25, 0.03
    else:
        MIN_TOP, MIN_GAP = 0.05, 0.01

    abstained = False
    abstain_reason = ""
    if s1 is None:
        abstained = True
        abstain_reason = "no usable retrieval scores"
    elif s1 < MIN_TOP:
        abstained = True
        abstain_reason = "weak retrieval match"
    elif s2 is not None and (s1 - s2) < MIN_GAP:
        abstained = True
        abstain_reason = "ambiguous retrieval (top results too close)"

    # Extra safety: if none of the meaningful query tokens appear in the retrieved sources,
    # abstain (helps when TF-IDF returns a plausible-looking but unrelated snippet).
    _q_tokens = re.findall(r"\w+", query.lower(), flags=re.UNICODE)
    _stop = {
        # EN
        "the","and","or","to","of","in","on","for","with","a","an","is","are","was","were","be",
        "what","which","who","whom","where","when","why","how",
        # DE
        "der","die","das","und","oder","zu","von","im","in","am","an","auf","für","mit","ein","eine","einer","eines",
        "was","welche","welcher","welches","wer","wo","wann","warum","wie",
        # AR (very light)
        "ما","ماذا","من","أين","متى","لماذا","كيف","في","على","و","او","أو"
    }
    _kw2 = {t for t in _q_tokens if len(t) >= 3 and t not in _stop}

    # -------- Broad-query clarify gate (MVP) --------
    # Clarify only for truly topic-only queries, or for very short queries when
    # retrieval confidence is borderline / ambiguous.
    _q_norm = " ".join(_q_tokens)
    topic_only = _q_norm in {"wohngeld", "wohngeld antrag", "wohngeld unterlagen"}

    # Avoid clarifying on purely numeric/punctuation queries (e.g., "1.5").
    has_alpha = bool(re.search(r"[A-Za-zÄÖÜäöü\u0600-\u06FF]", query))

    broad_clarify = topic_only
    if has_alpha and (not broad_clarify) and len(query.strip()) <= 32 and len(_kw2) <= 2:
        borderline = (s1 is not None and s1 < (MIN_TOP * 1.5))
        ambiguous = (s2 is not None and (s1 - s2) < (MIN_GAP * 1.5))
        if borderline or ambiguous:
            broad_clarify = True
    # If this is a topic-only query, prefer clarifying over abstaining.
    if topic_only:
        abstained = False
        abstain_reason = ""

    _hay = (
        " ".join(d["text"] for d in top)
        + " "
        + " ".join(os.path.basename(d["path"]) for d in top)
    ).lower()
    if (not topic_only) and _kw2 and not any(t in _hay for t in _kw2):
        abstained = True
        abstain_reason = "no lexical overlap with retrieved sources"

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
    if abstained:
        header += f" • **Abstain:** yes ({abstain_reason})"
        header += (
            "\n\n💡 **Tip:** Try rephrasing with Wohngeld-specific keywords, set **Include** → `wohngeld`, "
            "and/or increase **Top-K** (e.g., 5–10)."
        )
    if broad_clarify:
        header += " • **Clarify:** yes (query too broad)"

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
        path = d["path"]
        ts = _dt.datetime.fromtimestamp(os.path.getmtime(path), tz=_dt.timezone.utc).strftime('%Y-%m-%d')
        snippet = _short(highlight(d["text"]))
        fname = os.path.basename(path)
        url = source_url(path, link_mode=link_mode, github_blob_base=GITHUB_BLOB_BASE)
        lines.append(f"[{j+1}] {snippet}  — `{fname}` • {d['lang']} • updated {ts} • [view]({url})")

    # pick a proper answer: skip alias blocks, meta headers, and keyword-only lists
    def _strip_meta(s: str) -> str:
        return re.sub(r'^\s*\[meta\][^\n]*\n?', '', s, flags=re.IGNORECASE).strip()

    def _is_keyword_block(s: str) -> bool:
        s2 = s.strip().lower()
        if s2.startswith("stichwörter"):
            return True
        # many commas but no sentence enders → likely just keywords
        if s.count(",") >= 4 and not re.search(r'[.!؟!?]', s):
            return True
        return False

    # candidates = non-alias texts from top-K (keep source index for lightweight citations)
    cand_pairs = [(d["text"], j) for j, d in enumerate(top) if "aliasfragen" not in d["text"].lower()]

    # prefer texts that don't start with [Meta]; then the rest (keep source index)
    primary = [(t, j) for (t, j) in cand_pairs if not t.lstrip().lower().startswith("[meta]")]
    ordered = primary + [(t, j) for (t, j) in cand_pairs if (t, j) not in primary]

    answer_text = ""
    answer_src = None  # 0-based index into `top`
    for t, j in ordered:
        stripped = _strip_meta(t)
        if _is_keyword_block(stripped):
            continue
        if len(stripped) >= 40:  # avoid too-short after stripping
            answer_text = stripped
            answer_src = j
            break
    if not answer_text:
        # ultimate fallback: first available text (strip meta anyway)
        if cand_pairs:
            fallback, j = cand_pairs[0]
            answer_src = j
        else:
            fallback, j = top[0]["text"], 0
            answer_src = j
        answer_text = _strip_meta(fallback)
    # If retrieval confidence is low, abstain instead of answering from snippets.
    if abstained:
        answer_text = (
            "Insufficient evidence in the retrieved documents to answer confidently.\n\n"
            "Try:\n"
            "- adding Wohngeld-specific keywords (e.g., Unterlagen, Einkommen, Bearbeitungszeit)\n"
            "- setting **Include** → `wohngeld`\n"
            "- increasing **Top-K** (e.g., 5–10)\n"
        )
    elif broad_clarify:
        answer_text = (
            "Your question is a bit broad — which part do you mean?\n\n"
            "1) Eligibility (who can apply)\n"
            "2) Documents (Unterlagen)\n"
            "3) Income rules (Einkommen)\n"
            "4) Where/when to apply + processing time\n\n"
            "Reply with 1–4 (and optionally: city + household size + rent), "
            "and I’ll narrow it down using the sources below."
        )
        answer_src = None
    else:
        # Lightweight citation coverage: point to the top source we used.
        if answer_src is not None:
            src_file = os.path.basename(top[answer_src]["path"]) if top and answer_src < len(top) else ""
            suffix = f" (`{src_file}`)" if src_file else ""
            answer_text = f"{answer_text}\n\nSource: [{answer_src + 1}]{suffix}"
    sources = "### Sources\n" + header + "\n\n" + "\n\n".join(lines)
    log_query({
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
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
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    sources = f"Time: {stamp} • Mode: {mode} • k={k} • lang={q_lang}\n\n" + sources

    if trace:
        # Minimal, stable trace for demos: what settings were used + what sources were chosen.
        trace_payload = trace_payload or {}
        trace_payload.update(
            {
                "final_mode": mode,
                "final_q_lang": q_lang,
                "clarify": bool(broad_clarify),
                "abstained": bool(abstained),
                "abstain_reason": abstain_reason,
                "tfidf_pool": _tfidf_pool(),
                "top_docs": [
                    {
                        "rank": j + 1,
                        "id": d.get("id"),
                        "lang": d.get("lang"),
                        "file": os.path.basename(d.get("path", "")),
                        "path": d.get("path"),
                    }
                    for j, d in enumerate(top)
                ],
            }
        )

        # ----------------- Sniper provenance emission (Phase B: emission only) -----------------
        # We emit a Sniper-compatible provenance trace block so downstream adapters/checkers
        # can start consuming stable structure. Verdict stays conservative (no GREEN yet).
        pipeline_version = os.getenv("GITHUB_SHA") or os.getenv("SNIPER_PIPELINE_VERSION") or "dev"
        def _to_01(x):
            if x is None:
                return 0.0
            try:
                x = float(x)
            except Exception:
                return 0.0
            # Cosine similarity can be [-1, 1]; map to [0, 1] when semantic was used.
            if used_semantic_scores:
                x = (x + 1.0) / 2.0
            return max(0.0, min(1.0, x))

        sources_v1 = []
        for rank, idx in enumerate(chosen, start=1):
            d = docs[idx]
            chunk_text = d.get("text", "") or ""
            chunk_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
            retrieval_score = _to_01(_score_for(idx))
            sources_v1.append(
                {
                    "source_id": f"{d.get('path', '')}#doc{d.get('id')}",
                    "chunk_hash": chunk_hash,
                    "chunk_text": chunk_text,
                    "retrieval_score": retrieval_score,
                    "page_ref": None,
                }
            )

        # Phase B policy: provenance is emitted, but we still do not certify GREEN.
        sniper_verdict = TrafficLight.YELLOW
        sniper_reason = (
            "clarify" if bool(broad_clarify)
            else f"abstain:{abstain_reason}" if bool(abstained)
            else "phase_b_provenance_emission_only"
        )

        trace_payload["sniper_trace_v1"] = {
            "trace_id": str(uuid.uuid4()),
            "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "query": query,
            "verdict": sniper_verdict.name,
            "verdict_reason": sniper_reason,
            "answer": None if sniper_verdict == TrafficLight.RED else answer_text,
            "sources": sources_v1,
            "model_version": MODEL_NAME,
            "pipeline_version": pipeline_version,
        }

        return answer_text, sources, json.dumps(trace_payload, ensure_ascii=False, indent=2)

    return answer_text, sources

# ----------------- In-app Eval (lazy import to avoid circular) -----------------
def eval_ui(k, include, lang):
    from eval import evaluate_run
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
            passages, scores = tfidf.search(query, k=max(k * 10, 200))
            order = np.argsort(scores)[::-1]
            idx_map = [DOC_INDEX.get((p["path"], p["text"])) for p in passages]
            ranked = [idx for j in order for idx in [idx_map[j]] if idx is not None]
        elif m == "hybrid":
            _init_embeddings()
            if not _semantic_ready:
                passages, scores = tfidf.search(query, k=max(k * 10, 200))
                order = np.argsort(scores)[::-1]
                idx_map = [DOC_INDEX.get((p["path"], p["text"])) for p in passages]
                ranked = [idx for j in order for idx in [idx_map[j]] if idx is not None]
                ranked = [i for i in ranked if file_ok(docs[i]["path"], includes, None)]
                q_lang = detect_lang(query)
                return _prefer_lang(ranked, q_lang, k)
            q_emb = embedder.encode(query, convert_to_numpy=True)
            sem_scores = cos_scores_np(q_emb, doc_embeddings)
            sem_order = sem_scores.argsort()[::-1].tolist()
            passages, scores = tfidf.search(query, k=max(k * 10, 200))
            order = np.argsort(scores)[::-1]
            idx_map = [DOC_INDEX.get((p["path"], p["text"])) for p in passages]
            tf_order = [idx for j in order for idx in [idx_map[j]] if idx is not None]
            # Guardrail: only let semantic vote with its top-N to avoid long-tail noise.
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
            _init_embeddings()
            if not _semantic_ready:
                passages, scores = tfidf.search(query, k=max(k * 10, 200))
                order = np.argsort(scores)[::-1]
                idx_map = [DOC_INDEX.get((p["path"], p["text"])) for p in passages]
                ranked = [idx for j in order for idx in [idx_map[j]] if idx is not None]
                ranked = [i for i in ranked if file_ok(docs[i]["path"], includes, None)]
                q_lang = detect_lang(query)
                return _prefer_lang(ranked, q_lang, k)
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
    # k, mode, include, exclude, lang, link_mode
    return 3, "TF-IDF", "wohngeld", "", "auto", "github"
def _fill_q(s: str) -> str:
    return s or ""

# ----------------- UI -----------------

# Gradio UI is constructed only on demand, not at import-time.
CSS = """
#answer_box textarea {min-height: 300px !important; height: 300px !important;}
#source_box {min-height: 180px !important;}
"""

def build_demo():
    """Build and return the Gradio UI.

    Kept out of module import-time so tests can import `app` even when Gradio
    isn't installed.
    """
    if gr is None:
        raise RuntimeError("Gradio is not installed. Install it to run the UI.")

    with gr.Blocks(css=CSS, title="P1 — Mini FAQ (EN/DE/AR)") as demo:
        gr.Markdown("### Multilingual FAQ (EN/DE/AR) — language-aware retrieval")
        gr.Markdown(
            "**Privacy:** This demo does not store your queries. · "
            "[GitHub](https://github.com/moe-eid-ml/p1-faq-rag) · "
            "[Hugging Face Space](https://huggingface.co/spaces/HFHQ92/wohngeld-faq-rag)"
        )
        with gr.Row():
            q = gr.Textbox(
                label="Your question",
                lines=4,
                scale=3,
                placeholder="Ask in English, Deutsch, or العربية (if asked to clarify, reply with 1-4 + optional context)",
            )
            k = gr.Slider(1, 5, step=1, value=3, label="Top-K", scale=1)
            mode = gr.Radio(choices=["Semantic","TF-IDF","Hybrid"], value="TF-IDF", label="Retrieval mode")
            include = gr.Textbox(
                label="Include filenames (comma-separated, optional)",
                placeholder="e.g. wohngeld, faq",
                value="wohngeld",
                scale=1,
            )
            exclude = gr.Textbox(
                label="Exclude filenames (comma-separated, optional)",
                placeholder="e.g. pdf, bescheid, scan",
                value="",
                scale=1,
            )
            lang = gr.Dropdown(
                label="Language (override)",
                choices=["auto", "de", "en", "ar"],
                value="auto",
                scale=1,
            )
            link_mode = gr.Radio(
                label="Source links",
                choices=["github", "local"],
                value="github",
                scale=1,
            )
            show_trace = gr.Checkbox(label="Show trace", value=False, scale=1)
        with gr.Row():
            sample = gr.Dropdown(
                label="Sample question",
                choices=[
                    "Welche Unterlagen brauche ich für den Wohngeldantrag?",
                    "Wo stelle ich den Wohngeldantrag in meiner Stadt?",
                    "Wie lange dauert die Bearbeitung vom Wohngeld?",
                    "Wie wird die Höhe des Wohngelds berechnet?",
                    "Wann sollte ich den Weiterleistungsantrag stellen?",
                ],
                value=None,
                scale=3,
            )
        ans = gr.Textbox(label="Answer", lines=16, interactive=True, show_copy_button=True, elem_id="answer_box")
        src = gr.Markdown(label="Top sources", elem_id="source_box")
        tr = gr.Textbox(label="Trace (JSON)", lines=10, interactive=True, show_copy_button=True)

        def answer_ui(query, k, mode, include, lang, exclude, link_mode, show_trace):
            if show_trace:
                a, s, t = answer(query, k, mode, include, lang, exclude, link_mode, trace=True)
                return a, s, t
            a, s = answer(query, k, mode, include, lang, exclude, link_mode, trace=False)
            return a, s, ""

        go = gr.Button("Search")
        go.click(answer_ui, [q, k, mode, include, lang, exclude, link_mode, show_trace], [ans, src, tr])
        sample.change(_fill_q, [sample], [q])
        reset = gr.Button("Reset filters")
        reset.click(_reset_defaults, [], [k, mode, include, exclude, lang, link_mode])
        with gr.Row():
            ebtn = gr.Button("Evaluate (P@K / R@K)")
            emd = gr.Markdown()
            ebtn.click(eval_ui, [k, include, lang], [emd])

    return demo


# Expose a module-level name for compatibility. It's only built on demand.
demo = None


if __name__ == "__main__":
    demo = build_demo()
    demo.launch()
