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

    clarify = bool(trace.get("clarify"))
    abstained = bool(trace.get("abstained"))
    abstain_reason = trace.get("abstain_reason", "") or ""

    # Minimal verdict mapping for v1:
    # - clarify or abstain => YELLOW
    # - otherwise GREEN
    verdict = "YELLOW" if (clarify or abstained) else "GREEN"

    return {
        "query": query,
        "verdict": verdict,
        "reason": "clarify" if clarify else ("abstain:" + abstain_reason if abstained else "sourced_answer"),
        "answer": ans,
        "sources_md": srcs,
        "trace": trace,
    }
