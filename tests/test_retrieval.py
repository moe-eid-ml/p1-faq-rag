import app

def test_wohngeld_question_returns_text():
    ans, src = app.answer("What do I need for Wohngeld?", k=2)
    assert isinstance(ans, str) and len(ans) > 0
    assert "Wohngeld" in src or "wohngeld" in src.lower()
