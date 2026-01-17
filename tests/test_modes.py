import os

import pytest

import app


def _call(mode):
    ans, src = app.answer("Welche Unterlagen brauche ich für Wohngeld?", k=3, mode=mode)
    assert isinstance(ans, str) and len(ans) > 0
    assert isinstance(src, str) and "[1]" in src

def test_semantic():
    _call("Semantic")

def test_tfidf():
    _call("TF-IDF")

def test_semantic_strict_requires_semantic():
    if os.getenv("DISABLE_SEMANTIC") == "1":
        pytest.skip("Semantic disabled via DISABLE_SEMANTIC")
    if not app.ensure_semantic_ready():
        pytest.fail("Semantic strict mode unavailable; install sentence-transformers/torch or set DISABLE_SEMANTIC=1 to skip")
    ans, src = app.answer("Welche Unterlagen brauche ich für Wohngeld?", k=3, mode="Semantic", strict=True)
    assert isinstance(ans, str) and len(ans) > 0
    assert isinstance(src, str) and "[1]" in src
