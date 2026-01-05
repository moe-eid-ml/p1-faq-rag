"""
RAG1 adapter for Sniper adversarial runner (Phase C).

- Calls existing app.answer(..., trace=True)
- Uses Sniper checkers (Phase C) to verify invariants when available
- Falls back to Phase B / legacy logic if checkers unavailable
- Hard invariant: no false GREEN (GREEN only via Phase C checkers)
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import app

# Phase C checker import (safe fallback if unavailable)
try:
    from sniper.checkers import determine_verdict
except ImportError:
    determine_verdict = None  # type: ignore[misc,assignment]


# Helper to normalize checker outputs for checks_summary
def _summarize_checks(checks: Any) -> List[Dict[str, Any]]:
    """Normalize checker outputs into a stable [{name, passed, reason}] shape.

    Supports:
      - [(name, check_obj)]
      - [(name, passed, reason, ...)]
      - [{"name"|"check"|"id": ..., "passed"|"ok": ..., "reason": ...}]
      - [check_obj] where attrs exist

    We default to passed=False when unknown (conservative).
    """
    out: List[Dict[str, Any]] = []
    if not checks:
        return out

    for item in checks:
        name: str = "checker"
        passed: Any = None
        reason: Any = None

        if isinstance(item, (tuple, list)):
            if len(item) >= 1:
                name = str(item[0])
            if len(item) == 2:
                chk = item[1]
                if isinstance(chk, dict):
                    passed = chk.get("passed", chk.get("ok"))
                    reason = chk.get("reason")
                else:
                    passed = getattr(chk, "passed", getattr(chk, "ok", None))
                    reason = getattr(chk, "reason", None)
            else:
                # Assume (name, passed, reason, ...) and ignore extras
                if len(item) >= 2:
                    passed = item[1]
                if len(item) >= 3:
                    reason = item[2]

        elif isinstance(item, dict):
            name = str(item.get("name") or item.get("check") or item.get("id") or "checker")
            passed = item.get("passed", item.get("ok"))
            reason = item.get("reason")

        else:
            name = str(getattr(item, "name", getattr(item, "check", getattr(item, "id", "checker"))))
            passed = getattr(item, "passed", getattr(item, "ok", None))
            reason = getattr(item, "reason", None)

        if passed is None:
            passed = False
        out.append({"name": name, "passed": bool(passed), "reason": str(reason) if reason is not None else ""})

    return out


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
    if not isinstance(trace, dict):
        trace = {}

    # Phase C: attempt Sniper checkers if available
    verdict_result = None
    checks_summary: Optional[List[Dict[str, Any]]] = None
    if determine_verdict is not None:
        try:
            verdict_result = determine_verdict(trace)
        except Exception:
            verdict_result = None

    if verdict_result is not None:
        # Phase C succeeded: use checker verdict
        verdict = verdict_result.verdict
        reason = verdict_result.reason
        checks_summary = _summarize_checks(verdict_result.checks)

        # Hard invariant: GREEN only if Phase C exists AND all checks passed.
        v_up = str(verdict).upper()
        if v_up not in {"GREEN", "YELLOW", "RED"}:
            v_up = "YELLOW"

        all_passed = bool(checks_summary) and all(bool(c.get("passed")) for c in checks_summary)
        if v_up == "GREEN" and not all_passed:
            # Conservative downgrade to avoid false-green.
            failing = next((c.get("name") for c in (checks_summary or []) if not c.get("passed")), "unknown")
            v_up = "YELLOW"
            reason = f"phase_c_incomplete_or_failed:{failing}:{reason}"

        verdict = v_up

        # Extra conservative guard: if the query names a specific year, we only allow GREEN
        # when that year appears somewhere in retrieved evidence/trace.
        if verdict == "GREEN":
            years = re.findall(r"\b(?:19|20)\d{2}\b", query)
            if years:
                evidence_blob = (srcs or "") + "\n" + json.dumps(trace, ensure_ascii=False)
                missing = [y for y in years if y not in evidence_blob]
                if missing:
                    verdict = "YELLOW"
                    reason = f"year_not_in_evidence:{','.join(missing)}:{reason}"

        # Extra conservative guard: if Phase B (sniper_trace_v1) disagrees or is missing,
        # we do NOT allow Phase C to output GREEN. This avoids false-greens while Phase C
        # checkers are still being hardened.
        if verdict == "GREEN":
            sniper_b = trace.get("sniper_trace_v1") if isinstance(trace, dict) else None
            b_verdict = None
            if isinstance(sniper_b, dict) and sniper_b:
                b_verdict = str(sniper_b.get("verdict", "")).upper()
            if b_verdict != "GREEN":
                verdict = "YELLOW"
                reason = f"phase_b_not_green:{b_verdict or 'missing'}:{reason}"
    else:
        # Fallback: Phase B policy (sniper_trace_v1) or legacy logic
        # Hard invariant: never GREEN without Phase C checkers
        sniper = trace.get("sniper_trace_v1") if isinstance(trace, dict) else None

        if isinstance(sniper, dict) and sniper:
            # Phase B fallback: use sniper_trace_v1 but cap at YELLOW
            raw_verdict = str(sniper.get("verdict", "YELLOW") or "YELLOW").upper()
            # Never GREEN without Phase C verification
            verdict = "YELLOW" if raw_verdict == "GREEN" else raw_verdict
            if verdict not in {"YELLOW", "RED"}:
                verdict = "YELLOW"

            reason = (
                sniper.get("verdict_reason")
                or sniper.get("reason")
                or "missing_verdict_reason"
            )
            if raw_verdict == "GREEN":
                reason = f"phase_c_unavailable:{reason}"
        else:
            # Legacy fallback (older traces without sniper_trace_v1)
            clarify = bool(trace.get("clarify"))
            abstained = bool(trace.get("abstained"))
            abstain_reason = trace.get("abstain_reason", "") or ""

            verdict = "YELLOW"
            if clarify:
                reason = "clarify"
            elif abstained:
                reason = f"abstain:{abstain_reason}" if abstain_reason else "abstain"
            else:
                reason = "fallback_no_phase_c"

    result: Dict[str, Any] = {
        "query": query,
        "verdict": verdict,
        "reason": reason,
        "answer": ans,
        "sources_md": srcs,
        "trace": trace,
    }
    if checks_summary is not None:
        result["checks"] = checks_summary
    return result
