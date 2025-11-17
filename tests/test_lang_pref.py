import re
import app

SRC_LINE = re.compile(r"^\[\d+\].+— `(?P<fname>[^`]+)` • (?P<lang>..)\b", re.M)

def _lang_and_files(src: str):
    langs, files = [], []
    for m in SRC_LINE.finditer(src):
        langs.append(m.group("lang"))
        files.append(m.group("fname"))
    return langs, files

def test_de_lang_override_and_include():
    q = "Welche Unterlagen brauche ich für den Wohngeldantrag?"
    ans, src = app.answer(q, k=3, mode="TF-IDF", include="wohngeld", exclude="", lang="de")
    assert isinstance(ans, str) and ans.strip()
    langs, files = _lang_and_files(src)
    assert len(langs) >= 3
    # language should be DE for all sources
    assert all(l == "de" for l in langs)
    # at least 2 of the top files should contain 'wohngeld' in name
    assert sum("wohngeld" in f.lower() for f in files) >= 2

def test_force_de_even_with_en_query():
    q = "What documents are needed for Wohngeld?"
    ans, src = app.answer(q, k=3, mode="Semantic", include="wohngeld", exclude="", lang="de")
    langs, files = _lang_and_files(src)
    assert len(langs) >= 3
    assert all(l == "de" for l in langs)
