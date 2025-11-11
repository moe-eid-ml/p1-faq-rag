import app

def _call(mode):
    ans, src = app.answer("Welche Unterlagen brauche ich für Wohngeld?", k=3, mode=mode)
    assert isinstance(ans, str) and len(ans) > 0
    assert isinstance(src, str) and "[1]" in src

def test_semantic():
    _call("Semantic")

def test_tfidf():
    _call("TF-IDF")
