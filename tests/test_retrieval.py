import app


def test_wohngeld_question_returns_text():
    # Deterministic in CI: scope to wohngeld + TF-IDF, and use a specific query.
    ans, src = app.answer(
        "What documents do I need for a Wohngeld application in Germany?",
        k=3,
        mode="TF-IDF",
        include="wohngeld",
    )
    assert isinstance(ans, str) and len(ans) > 0
    assert "wohngeld" in src.lower()

    # Regression: sources should include a clickable "view" link to the GitHub file.
    assert "[view](" in src
    assert "https://github.com/moe-eid-ml/p1-faq-rag/blob/main/" in src


def test_abstain_on_nonsense_query():
    # Regression: junk queries should abstain instead of guessing.
    ans, src = app.answer("asdf qwerty", k=3, mode="TF-IDF", include="wohngeld")
    assert "Insufficient evidence" in ans
    assert "### Sources" in src
    assert "Abstain" in src


def test_source_pointer_present_on_normal_answer():
    # Regression: normal answers should include a lightweight source pointer.
    ans, _src = app.answer(
        "Welche Unterlagen brauche ich für den Wohngeldantrag?",
        k=3,
        mode="TF-IDF",
        include="wohngeld",
    )
    assert "Insufficient evidence" not in ans
    assert "\n\nSource: [" in ans


def test_link_mode_local_uses_file_urls():
    # Regression: local link mode should produce file:// URLs.
    _ans, src = app.answer(
        "What documents do I need for a Wohngeld application in Germany?",
        k=2,
        mode="TF-IDF",
        include="wohngeld",
        link_mode="local",
    )
    assert "file://" in src


def test_reset_defaults_sets_github_links():
    # Regression: reset defaults should set link mode back to github.
    defaults = app._reset_defaults()
    assert defaults[-1] == "github"


def test_broad_query_triggers_clarify_prompt():
    # Regression: truly topic-only queries should ask for clarification (not abstain, not a snippet answer).
    ans, src = app.answer("Wohngeld", k=3, mode="TF-IDF", include="wohngeld")
    assert "Your question is a bit broad" in ans
    assert "Clarify" in src
    assert "**Abstain:** yes" not in src
    assert "\n\nSource: [" not in ans


def test_query_logging_disabled_by_default():
    # Privacy regression: logging should be opt-in (off by default).
    assert app.LOG_QUERIES is False
