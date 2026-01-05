import json
from pathlib import Path

from sniper.adversarial.runner import run_all
from sniper.integrations.rag1_adapter import answer_fn


def _load_cases() -> list[dict]:
    path = Path(__file__).parent / "cases_v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _result_id(r: dict) -> str | None:
    # Be tolerant to runner result shapes.
    for k in ("id", "case_id", "caseId"):
        v = r.get(k)
        if isinstance(v, str) and v:
            return v
    case = r.get("case")
    if isinstance(case, dict):
        v = case.get("id")
        if isinstance(v, str) and v:
            return v
    return None


def test_runner_enforces_expected_verdicts_and_reasons_for_non_harness_cases():
    cases = _load_cases()
    non_harness = [c for c in cases if not c.get("requires_harness", False)]

    # Run the non-harness cases through the real adapter without crashing.
    results = run_all(answer_fn=answer_fn, include_harness=False)
    assert results, "runner returned no results"

    # Build a lookup by case id.
    by_id: dict[str, dict] = {}
    for r in results:
        cid = _result_id(r)
        if cid:
            by_id[cid] = r

    # Ensure we executed all non-harness cases.
    missing = [c.get("id") for c in non_harness if c.get("id") not in by_id]
    assert not missing, f"missing results for case ids: {missing}"

    for c in non_harness:
        cid = c["id"]
        r = by_id[cid]

        verdict = str(r.get("verdict", "")).upper()
        assert verdict in {"GREEN", "YELLOW", "RED"}
        assert verdict == c["expected_verdict"], f"{cid}: expected {c['expected_verdict']} got {verdict}"

        reason = str(r.get("reason", ""))
        expected_bits = c.get("expected_reason_contains", [])
        if expected_bits:
            reason_l = reason.lower()
            hits = [b for b in expected_bits if str(b).lower() in reason_l]
            assert hits, f"{cid}: reason '{reason}' missing any of {expected_bits}"

        # Global invariant: never silently pass unexpected verdicts.
        assert "error" not in reason.lower(), f"{cid}: runner/adaptor error leaked into reason: {reason}"
