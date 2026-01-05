"""
RAG1 adapter for Sniper adversarial runner.

- Calls existing app.answer(..., trace=True)
- Interprets trace JSON into a Sniper-style verdict (GREEN/YELLOW/RED)
- This is intentionally minimal and conservative.
"""

from __future__ import annotations

import json
from typing import Dict

import app


def answer_fn(query: str) -> Dict:
    # Use conservative defaults; we're testing gating behavior, not retrieval tuning.
    ans, srcs, trace_json = app.answer(
        query,
        k=3,
        mode="TF-IDF",
        include="wohngeld",
        lang="auto",
        exclude="",
        link_mode="github",
        trace=True,
    )

    try:
        trace = json.loads(trace_json) if trace_json else {}
    except Exception:
        trace = {}

    # Phase A policy: STUBBED adapter.
    # Rationale: RAG1 can return an answer string and a trace, but it does not yet
    # guarantee per-claim evidence binding in the Sniper provenance format.
    # To prevent accidental FALSE GREENs, we default to YELLOW until Sniper checkers
    # + provenance emission are implemented.

    clarify = bool(trace.get("clarify"))
    abstained = bool(trace.get("abstained"))
    abstain_reason = trace.get("abstain_reason", "") or ""

    verdict = "YELLOW"

    # Prefer the most specific reason we have.
    if clarify:
        reason = "clarify"
    elif abstained:
        reason = f"abstain:{abstain_reason}" if abstain_reason else "abstain"
    else:
        reason = "stubbed_adapter_no_provenance_yet"

    return {
        "query": query,
        "verdict": verdict,
        "reason": reason,
        "answer": ans,
        "sources_md": srcs,
        "trace": trace,
    }
