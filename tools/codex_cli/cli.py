import glob, pathlib, re, time, json
import regex as re2
import typer

app = typer.Typer(help="FAQ pipeline CLI")
AR_PATH = "docs/faq/ar"
META_KEYS = ("ID:", "CAT:", "TAGS:", "Q:", "A:")
LATIN = re.compile(r"[A-Za-z]")
ARABIC_BLOCK = re2.compile(r"\p{Arabic}", re2.UNICODE)

def iter_txt(path=AR_PATH):
    for p in sorted(glob.glob(f"{path}/**/*.txt", recursive=True)):
        yield pathlib.Path(p)

def parse_qa(text:str):
    lines = [l.rstrip() for l in text.splitlines()]
    meta, body = {}, []
    for l in lines:
        if any(l.startswith(k) for k in META_KEYS[:-2]):  # ID/CAT/TAGS
            k, v = l.split(":", 1); meta[k]=v.strip(); continue
        body.append(l)
    q = next((l[2:].strip() for l in body if l.startswith("Q:")), "")
    a_lines = []
    seen_a = False
    for l in body:
        if l.startswith("A:"):
            seen_a = True
            a_lines.append(l[2:].strip()); continue
        if seen_a: a_lines.append(l)
    a = "\n".join(a_lines).strip()
    return meta, q, a

@app.command()
def validate(path: str = AR_PATH, banned: str = "banned_terms.txt"):
    """Ensure Q/A content is Arabic-only; block banned terms."""
    problems = []
    banned_terms = []
    try:
        with open(banned, "r", encoding="utf-8") as f:
            banned_terms = [t.strip() for t in f if t.strip()]
    except FileNotFoundError:
        pass
    for p in iter_txt(path):
        t = p.read_text(encoding="utf-8")
        meta,q,a = parse_qa(t)
        content = f"{q}\n{a}"
        if LATIN.search(content):
            problems.append((p, "Contains Latin letters in Q/A"))
        if not ARABIC_BLOCK.search(content):
            problems.append((p, "No Arabic characters detected in Q/A"))
        for term in banned_terms:
            if term and term in content:
                problems.append((p, f"Banned term: {term}"))
    if problems:
        for p, why in problems: print(f"FAIL {p}: {why}")
        raise typer.Exit(code=1)
    print("OK All files valid.")

@app.command()
def slugs(path: str = AR_PATH, fix: bool = False):
    """Enforce slug__YYYY-MM-DD.txt file names."""
    pat = re.compile(r"^[a-z0-9\-]+__\d{4}-\d{2}-\d{2}\.txt$")
    for p in iter_txt(path):
        if not pat.match(p.name):
            print(f"WARN bad slug: {p.name}")
            if fix:
                slug = re.sub(r"[^a-z0-9\-]", "-", p.stem.lower())
                new = p.with_name(f"{slug}__{time.strftime('%Y-%m-%d')}.txt")
                p.rename(new); print(f"FIX → {new.name}")

@app.command()
def embed(path: str = AR_PATH, out: str = "build/index.json"):
    """Build a simple JSON index (stub for embeddings)."""
    pathlib.Path("build").mkdir(exist_ok=True)
    items = []
    for p in iter_txt(path):
        meta,q,a = parse_qa(p.read_text(encoding="utf-8"))
        items.append({"id": meta.get("ID") or p.stem, "q": q, "a": a, "path": str(p)})
    with open(out, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"Built {out} ({len(items)} docs)")

@app.command()
def sync():
    """Validate → Slugs → Embed."""
    validate()
    slugs()
    embed()
    print("Sync complete.")

if __name__ == "__main__":
    app()
