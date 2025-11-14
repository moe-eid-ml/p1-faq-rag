import sys, os, re
from pypdf import PdfReader

def to_paragraphs(text: str, min_len=60, max_len=400):
    # normalize whitespace
    text = re.sub(r'\r', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    blocks = re.split(r'\n\s*\n', text)  # blank-line blocks

    def split_block(b):
        # sentence-ish split (handles ?, !, . and Arabic ؟)
        sents = re.split(r'(?<=[\.\!\?؟])\s+', b.strip())
        out, cur = [], ""
        for s in sents:
            if not s:
                continue
            # keep bullets intact
            if re.match(r'^[\-\u2022•]', s):
                if cur:
                    out.append(cur.strip())
                    cur = ""
                out.append(s.strip())
                continue
            # grow chunk up to max_len
            if len(cur) + (1 if cur else 0) + len(s) <= max_len:
                cur = (cur + " " + s).strip() if cur else s.strip()
            else:
                if cur:
                    out.append(cur.strip())
                cur = s.strip()
        if cur:
            out.append(cur.strip())
        return out

    paras = []
    for b in blocks:
        for p in split_block(b):
            p = re.sub(r'\s+', ' ', p).strip()
            if len(p) >= min_len:
                paras.append(p)

    return '\n\n'.join(paras).strip()

def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/ingest_pdf.py <pdf_path> <out_txt_path> [de|en|ar]")
        sys.exit(1)
    pdf_path, out_txt = sys.argv[1], sys.argv[2]
    lang = (sys.argv[3] if len(sys.argv) > 3 else "de").lower()
    if lang not in {"de","en","ar"}:
        print("lang must be de|en|ar"); sys.exit(1)

    reader = PdfReader(pdf_path)
    raw = "\n\n".join((page.extract_text() or "") for page in reader.pages)
    text = to_paragraphs(raw)

    root, ext = os.path.splitext(out_txt)
    if not root.endswith(f"_{lang}"):
        out_txt = f"{root}_{lang}{ext}"

    os.makedirs(os.path.dirname(out_txt), exist_ok=True)
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(f"Wrote: {out_txt}")

if __name__ == "__main__":
    main()
