import argparse
import app  # uses your existing answer() + filters

def main():
    p = argparse.ArgumentParser(description="Ask a question against the Wohngeld RAG.")
    p.add_argument("question", help="Your question text")
    p.add_argument("-m", "--mode", choices=["TF-IDF", "Semantic", "Hybrid"], default="TF-IDF")
    p.add_argument("-k", "--k", type=int, default=3)
    p.add_argument("-i", "--include", default="wohngeld", help="Comma-separated filename keywords to include")
    p.add_argument("-x", "--exclude", default="", help="Comma-separated filename keywords to exclude")
    p.add_argument("-l", "--lang", default="", help="Force language (de/en/ar). Empty = auto-detect.")
    args = p.parse_args()

    ans, src = app.answer(
        args.question,
        k=args.k,
        mode=args.mode,
        include=args.include,
        exclude=args.exclude,
        lang=args.lang or None,
    )
    print("\n=== ANSWER ===\n" + ans.strip())
    print("\n=== SOURCES ===\n" + src.strip())

if __name__ == "__main__":
    main()
