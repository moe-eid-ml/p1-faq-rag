import json
from pathlib import Path

from sniper.adversarial.runner import run_all


def test_no_false_green_on_non_green_cases():
    # Load expected verdicts from the versioned dataset
    cases = json.loads(Path("tests/adversarial/cases_v1.json").read_text(encoding="utf-8"))
    expected = {c["id"]: c["expected_verdict"] for c in cases}

    # For now we only run non-harness cases in CI (include_harness=False)
    results = run_all(include_harness=False)

    assert results, "runner returned no results"
    for r in results:
        cid = r["id"]
        exp = expected[cid]
        verdict = r["verdict"]

        # Hard gate: anything that isn't expected GREEN must never come out GREEN.
        if exp in {"YELLOW", "RED"}:
            assert verdict != "GREEN", f"FALSE GREEN on {cid}: expected {exp}, got {verdict}"
