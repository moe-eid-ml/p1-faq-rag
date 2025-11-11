import app
from tfidf import TfidfRetriever

def test_tfidf_returns_results():
    r = TfidfRetriever(app.docs)
    top, scores = r.search("Wohngeld Unterlagen", k=2)
    assert len(top) == 2
    assert all("text" in t for t in top)
