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

    # Phase B policy: consume Sniper-compatible trace if present.
    # Rationale: `app.answer(..., trace=True)` now emits `sniper_trace_v1`.
    # The adapter should treat that as the source of truth for verdicting and reasons.
    sniper = trace.get("sniper_trace_v1") if isinstance(trace, dict) else None

    if isinstance(sniper, dict) and sniper:
        verdict = str(sniper.get("verdict", "YELLOW") or "YELLOW").upper()
        if verdict not in {"GREEN", "YELLOW", "RED"}:
            verdict = "YELLOW"

        reason = (
            sniper.get("verdict_reason")
            or sniper.get("reason")
            or "missing_verdict_reason"
        )
    else:
        # Backwards-compatible fallback (older traces).
        clarify = bool(trace.get("clarify"))
        abstained = bool(trace.get("abstained"))
        abstain_reason = trace.get("abstain_reason", "") or ""

        verdict = "YELLOW"
        if clarify:
            reason = "clarify"
        elif abstained:
            reason = f"abstain:{abstain_reason}" if abstain_reason else "abstain"
        else:
            reason = "stubbed_adapter_no_sniper_trace"

    return {
        "query": query,
        "verdict": verdict,
        "reason": reason,
        "answer": ans,
        "sources_md": srcs,
        "trace": trace,
    }
