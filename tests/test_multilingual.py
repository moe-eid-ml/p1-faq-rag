# -*- coding: utf-8 -*-
import app

def _ok(q):
    ans, src = app.answer(q, k=3)
    assert isinstance(ans, str) and len(ans) > 0
    return ans, src

def test_en():
    ans, src = _ok("What do I need for Wohngeld?")
    assert "lang=en" in src.lower() or "wohngeld" in (ans.lower() + src.lower())

def test_de():
    ans, src = _ok("Welche Unterlagen brauche ich für Wohngeld?")
    assert "lang=de" in src.lower() or "wohngeld" in (ans.lower() + src.lower())

def test_ar():
    ans, src = _ok("س: ما هي المستندات المطلوبة للحصول على بدل السكن؟")
    # Arabic phrasing no longer contains 'Wohngeld' → assert Arabic content/lang
    assert "lang=ar" in src.lower() or "بدل السكن" in ans
