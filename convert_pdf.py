from pypdf import PdfReader
from pathlib import Path

def pdf_to_txt(pdf_path: Path) -> Path:
    text = []
    reader = PdfReader(str(pdf_path))
    for page in reader.pages:
        text.append(page.extract_text() or "")
    out = pdf_path.with_suffix(".txt")
    # normalize whitespace → blank lines become paragraph breaks
    joined = "\n".join(text)
    # collapse 3+ newlines to 2, trim trailing spaces
    import re
    joined = re.sub(r"\n{3,}", "\n\n", joined)
    joined = "\n".join(line.rstrip() for line in joined.splitlines())
    out.write_text(joined, encoding="utf-8")
    return out

if __name__ == "__main__":
    docs = Path("docs")
    docs.mkdir(exist_ok=True)
    pdfs = list(docs.glob("*.pdf"))
    if not pdfs:
        print("No PDFs found in docs/. Drop files like docs/faq_de.pdf or docs/guide_en.pdf")
    for p in pdfs:
        out = pdf_to_txt(p)
        print(f"Converted: {p.name} -> {out.name}")
