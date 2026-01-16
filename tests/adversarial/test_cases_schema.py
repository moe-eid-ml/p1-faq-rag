import json
from pathlib import Path

from kosniper.contracts import TrafficLight

ALLOWED_VERDICTS = {t.name for t in TrafficLight}

def test_cases_v1_json_is_valid_and_well_formed():
    p = Path("tests/adversarial/cases_v1.json")
    assert p.exists(), "Missing tests/adversarial/cases_v1.json"

    cases = json.loads(p.read_text(encoding="utf-8"))
    assert isinstance(cases, list) and cases, "cases_v1.json must be a non-empty list"

    ids = set()
    for c in cases:
        assert isinstance(c, dict), "each case must be an object"
        for key in ["id", "title", "query", "expected_verdict", "expected_reason_contains", "requires_harness"]:
            assert key in c, f"case missing key: {key}"

        assert c["id"].startswith("ADV-"), "id must start with ADV-"
        assert c["id"] not in ids, f"duplicate id: {c['id']}"
        ids.add(c["id"])

        assert c["expected_verdict"] in ALLOWED_VERDICTS
        assert isinstance(c["expected_reason_contains"], list) and c["expected_reason_contains"], \
            "expected_reason_contains must be a non-empty list"
        assert isinstance(c["requires_harness"], bool)
