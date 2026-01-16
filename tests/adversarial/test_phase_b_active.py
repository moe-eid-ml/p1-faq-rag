"""
Phase B verification test (hard fail).

This test verifies that Phase B is active by asserting that `sniper_trace_v1`
exists in the trace returned by `app.answer(..., trace=True)`.

If this test fails, Phase B integration is broken and must be fixed before
proceeding with Phase C.
"""

import json

import app

from sniper.checkers import determine_verdict
from kosniper.contracts import TrafficLight


def test_sniper_trace_v1_exists_in_trace():
    """
    Hard-fail verification that Phase B is active.

    Calls app.answer with trace=True and asserts sniper_trace_v1 is present.
    """
    # Use a simple query that will return results
    query = "Wohngeld documents required"

    result = app.answer(
        query,
        k=3,
        mode="TF-IDF",
        include="wohngeld",
        lang="auto",
        exclude="",
        link_mode="github",
        trace=True,
    )

    # answer returns (answer_text, sources, trace_json) when trace=True
    assert len(result) == 3, "Expected 3-tuple return when trace=True"
    answer_text, sources, trace_json = result

    assert trace_json, "trace_json should not be empty"

    try:
        trace = json.loads(trace_json)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"CRITICAL: trace_json is not valid JSON: {e}")

    if "sniper_trace_v1" not in trace:
        raise RuntimeError(
            "CRITICAL: 'sniper_trace_v1' not found in trace. "
            "Phase B is not active! Fix Phase B integration before proceeding."
        )

    sniper = trace["sniper_trace_v1"]

    # Verify required fields in sniper_trace_v1
    required_fields = [
        "trace_id",
        "timestamp",
        "query",
        "verdict",
        "verdict_reason",
        "sources",
        "model_version",
        "pipeline_version",
    ]

    for field in required_fields:
        assert field in sniper, f"sniper_trace_v1 missing required field: {field}"

    # Verify verdict is valid
    assert sniper["verdict"] in {t.name for t in TrafficLight}, \
        f"Invalid verdict: {sniper['verdict']}"

    # Verify sources is a list
    assert isinstance(sniper["sources"], list), "sources must be a list"

    # For non-empty results, verify source structure
    if sniper["sources"]:
        for src in sniper["sources"]:
            assert "source_id" in src, "source missing source_id"
            assert "chunk_hash" in src, "source missing chunk_hash"
            assert "retrieval_score" in src, "source missing retrieval_score"


def test_sniper_trace_v1_on_empty_query():
    """
    Verify sniper_trace_v1 is emitted even for edge cases like empty query.
    """
    result = app.answer(
        "",  # empty query
        k=3,
        mode="TF-IDF",
        include="",
        lang="auto",
        exclude="",
        link_mode="github",
        trace=True,
    )

    assert len(result) == 3
    _, _, trace_json = result

    trace = json.loads(trace_json)

    if "sniper_trace_v1" not in trace:
        raise RuntimeError(
            "CRITICAL: 'sniper_trace_v1' not found in trace for empty query. "
            "Phase B must emit provenance for all code paths!"
        )

    sniper = trace["sniper_trace_v1"]
    assert sniper["verdict"] == "YELLOW", "Empty query should yield YELLOW verdict"
    assert sniper["verdict_reason"] == "empty_query"


def test_sniper_trace_v1_on_no_results():
    """
    Verify sniper_trace_v1 is emitted when no results are found.
    """
    # Use an absurd query that won't match anything
    result = app.answer(
        "xyzzy123nonexistent",
        k=3,
        mode="TF-IDF",
        include="nonexistent_file_filter",  # force no matches
        lang="auto",
        exclude="",
        link_mode="github",
        trace=True,
    )

    assert len(result) == 3
    _, _, trace_json = result

    trace = json.loads(trace_json)

    if "sniper_trace_v1" not in trace:
        raise RuntimeError(
            "CRITICAL: 'sniper_trace_v1' not found in trace for no-results case. "
            "Phase B must emit provenance for all code paths!"
        )

    sniper = trace["sniper_trace_v1"]
    assert sniper["verdict"] == "YELLOW", "No results should yield YELLOW verdict"


def test_phase_c_checks_schema_is_stable():
    """Lock Phase C check item schema to prevent drift.

    We intentionally test the *shape* only (not the verdict), so future checker
    additions don't break CI as long as they obey the schema.
    """
    # Get a real trace from the pipeline
    result = app.answer(
        "Wohngeld documents required",
        k=3,
        mode="TF-IDF",
        include="wohngeld",
        lang="auto",
        exclude="",
        link_mode="github",
        trace=True,
    )

    assert len(result) == 3
    _, _, trace_json = result
    trace = json.loads(trace_json)

    verdict_result = determine_verdict(trace)
    assert hasattr(verdict_result, "checks"), "Phase C verdict_result must expose .checks"

    checks = verdict_result.checks
    assert isinstance(checks, list), ".checks must be a list"
    assert checks, "Phase C should emit at least one check item"

    required = {"check", "ok", "severity", "reason"}
    allowed_sev = {"GREEN", "YELLOW", "RED"}

    for item in checks:
        assert isinstance(item, dict), "Each check item must be a dict"
        assert required.issubset(item.keys()), f"Check item missing keys: {required - set(item.keys())}"
        assert isinstance(item["check"], str) and item["check"], "check must be a non-empty string"
        assert isinstance(item["ok"], bool), "ok must be a bool"
        assert item["severity"] in allowed_sev, f"Invalid severity: {item['severity']}"
        assert isinstance(item["reason"], str), "reason must be a string"

        # details is optional, but if present it must be a dict
        if "details" in item:
            assert isinstance(item["details"], dict), "details must be a dict when present"

        # Guard against legacy/accidental schema keys
        assert "passed" not in item, "Legacy key 'passed' must not appear in check items"
        assert "name" not in item, "Legacy key 'name' must not appear in check items"
