import re

# Arabic Unicode block
AR_RE = re.compile(r"[\u0600-\u06FF]")

def detect_lang(s: str) -> str:
    """Lightweight detector: langdetect → Arabic regex → German heuristics → default EN."""
    try:
        from langdetect import detect
    except Exception:
        detect = None

    if not s or not s.strip():
        return "en"
    s = s.strip()

    # Primary: langdetect (best-effort)
    if detect:
        try:
            code = detect(s)
            if code.startswith("de"): return "de"
            if code.startswith("ar"): return "ar"
            if code.startswith("en"): return "en"
        except Exception:
            pass

    # Fallback 1: Arabic block present
    if AR_RE.search(s):
        return "ar"

    # Fallback 2: quick German heuristics (umlauts / common tokens)
    s_low = s.lower()
    if any(ch in s for ch in "äöüßÄÖÜ") or re.search(
        r"\b(welche|unterlagen|brauche|für|zahlung|meldungen|infos|zu)\b",
        s_low,
    ):
        return "de"

    return "en"
