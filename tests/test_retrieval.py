import app

def test_wohngeld_question_returns_text():
    ans, src = app.answer("What do I need for Wohngeld?", k=2)
    assert isinstance(ans, str) and len(ans) > 0
    assert "Wohngeld" in src or "wohngeld" in src.lower()

    # Regression: sources should include a clickable "view" link to the GitHub file.
    assert "[view](" in src
    assert "https://github.com/moe-eid-ml/p1-faq-rag/blob/main/" in src


def test_abstain_on_nonsense_query():
    # Why: regression-proof the new abstain gate on junk queries.
    ans, src = app.answer("asdf qwerty", k=3, mode="TF-IDF", include="wohngeld")
    assert "Insufficient evidence" in ans
    assert isinstance(src, str) and len(src) > 0
    assert "Abstain" in src


def test_source_pointer_present_on_normal_answer():
    # Why: ensure answers include a lightweight source pointer when not abstaining.
    ans, _src = app.answer("Welche Unterlagen brauche ich für den Wohngeldantrag?", k=3, mode="TF-IDF", include="wohngeld")
    assert "Insufficient evidence" not in ans
    assert "\n\nSource: [" in ans
