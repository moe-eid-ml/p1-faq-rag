from kosniper.pipeline import run_single_page
from kosniper.contracts import TrafficLight


def test_demo_checker_yields_evidence_when_phrase_found():
    out = run_single_page("Dies ist ein Ausschlusskriterium laut Unterlage.", doc_id="x.pdf", page_number=3)
    assert out.overall == TrafficLight.YELLOW
    ev = out.results[0].evidence[0]
    assert ev.doc_id == "x.pdf"
    assert ev.page_number == 3
    assert ev.snippet


def test_empty_page_text_returns_abstain_not_green():
    """Pipeline guard: empty text must return ABSTAIN, never GREEN."""
    out = run_single_page("", doc_id="empty.pdf", page_number=1)
    assert out.overall == TrafficLight.ABSTAIN
    assert out.overall != TrafficLight.GREEN


def test_none_page_text_returns_abstain_not_green():
    """Pipeline guard: None text must return ABSTAIN, never GREEN."""
    out = run_single_page(None, doc_id="none.pdf", page_number=1)
    assert out.overall == TrafficLight.ABSTAIN
    assert out.overall != TrafficLight.GREEN


def test_whitespace_only_page_text_returns_abstain():
    """Pipeline guard: whitespace-only text must return ABSTAIN."""
    out = run_single_page("   \n\t  ", doc_id="ws.pdf", page_number=1)
    assert out.overall == TrafficLight.ABSTAIN
    assert out.overall != TrafficLight.GREEN
