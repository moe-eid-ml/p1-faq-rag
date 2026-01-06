from kosniper.pipeline import run_single_page
from kosniper.contracts import TrafficLight

def test_demo_checker_yields_evidence_when_phrase_found():
    out = run_single_page("Dies ist ein Ausschlusskriterium laut Unterlage.", doc_id="x.pdf", page_number=3)
    assert out.overall == TrafficLight.YELLOW
    ev = out.results[0].evidence[0]
    assert ev.doc_id == "x.pdf"
    assert ev.page_number == 3
    assert ev.snippet
    assert ev.start_offset is not None
    assert ev.end_offset is not None
