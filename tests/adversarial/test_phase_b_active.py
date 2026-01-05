"""
Phase B verification test (hard fail).

This test verifies that Phase B is active by asserting that `sniper_trace_v1`
exists in the trace returned by `app.answer(..., trace=True)`.

If this test fails, Phase B integration is broken and must be fixed before
proceeding with Phase C.
"""

import json

import app


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
    assert sniper["verdict"] in {"GREEN", "YELLOW", "RED"}, \
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
