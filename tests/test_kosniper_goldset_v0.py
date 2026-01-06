import json
from pathlib import Path

LABELS = Path("data/kosniper/goldset_v0/labels/v0.jsonl")

ALLOWED_OVERALL = {"red", "yellow", "green", "abstain"}

def test_goldset_v0_jsonl_exists():
    assert LABELS.exists(), f"missing: {LABELS}"

def test_goldset_v0_labels_are_valid_records():
    seen = set()
    lines = LABELS.read_text(encoding="utf-8").splitlines()
    assert lines, "v0.jsonl is empty"

    for i, line in enumerate(lines, start=1):
        obj = json.loads(line)

        # required top-level fields
        assert isinstance(obj.get("case_id"), str) and obj["case_id"].strip()
        assert obj["case_id"] not in seen, f"duplicate case_id at line {i}: {obj['case_id']}"
        seen.add(obj["case_id"])

        assert isinstance(obj.get("doc_id"), str) and obj["doc_id"].strip()
        assert "/" not in obj["doc_id"], "doc_id must be a filename only (no paths)"

        assert isinstance(obj.get("page_number"), int) and obj["page_number"] >= 1
        assert isinstance(obj.get("text_hint"), str) and obj["text_hint"].strip()

        expected = obj.get("expected")
        assert isinstance(expected, dict), "expected must be an object"
        assert expected.get("overall") in ALLOWED_OVERALL
        hits = expected.get("checker_hits")
        assert isinstance(hits, list) and all(isinstance(x, str) and x.strip() for x in hits)
