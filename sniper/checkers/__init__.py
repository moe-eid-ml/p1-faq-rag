from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class VerdictResult:
    verdict: str  # "GREEN" | "YELLOW" | "RED"
    reason: str
    checks: List[Dict[str, Any]]


_INJECTION_TOKENS = (
    "ignore previous instructions",
    "system prompt",
    "developer message",
    "reveal your prompt",
    "jailbreak",
    "do anything now",
    "dan",
)

def _as_str(x: Any) -> str:
    try:
        return "" if x is None else str(x)
    except Exception:
        return ""

def _find_sniper_trace_v1(trace: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(trace, dict):
        return None
    v = trace.get("sniper_trace_v1")
    if isinstance(v, dict):
        return v
    s = trace.get("sniper")
    if isinstance(s, dict) and isinstance(s.get("sniper_trace_v1"), dict):
        return s["sniper_trace_v1"]
    t = trace.get("trace")
    if isinstance(t, dict) and isinstance(t.get("sniper_trace_v1"), dict):
        return t["sniper_trace_v1"]
    return None

def _add_check(
    checks: List[Dict[str, Any]],
    check: str,
    ok: bool,
    severity: str,
    reason: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    item: Dict[str, Any] = {
        "check": check,
        "ok": bool(ok),
        "severity": severity,
        "reason": reason,
    }
    if details is not None:
        item["details"] = details
    checks.append(item)

def determine_verdict(trace: Dict[str, Any]) -> VerdictResult:
    checks: List[Dict[str, Any]] = []

    if not isinstance(trace, dict):
        _add_check(checks, "input", False, "YELLOW", "malformed_trace")
        return VerdictResult("YELLOW", "malformed_trace", checks)

    sniper_v1 = _find_sniper_trace_v1(trace)

    # 1) Provenance gate
    if sniper_v1 is None:
        _add_check(checks, "provenance", False, "YELLOW", "missing_sniper_trace_v1")
        return VerdictResult("YELLOW", "provenance:missing_sniper_trace_v1", checks)
    _add_check(checks, "provenance", True, "GREEN", "ok")

    # 2) Injection scan (very cheap heuristic, upgrade later)
    sources = sniper_v1.get("sources", [])
    hay = []
    if isinstance(sources, list):
        for s in sources:
            if isinstance(s, dict):
                hay.append(_as_str(s.get("chunk_text")))
                hay.append(_as_str(s.get("source_id")))
                hay.append(_as_str(s.get("page_ref")))
    hay.append(_as_str(sniper_v1.get("answer")))
    combined = "\n".join(hay).lower()

    hits = [t for t in _INJECTION_TOKENS if t in combined]
    if hits:
        _add_check(
            checks,
            "injection",
            False,
            "RED",
            "prompt_injection_detected",
            details={"hits": hits},
        )
        return VerdictResult("RED", "injection:prompt_injection_detected", checks)
    _add_check(checks, "injection", True, "GREEN", "ok")

    # 3) Contradiction stub (treat explicit flags as YELLOW)
    flags = [
        sniper_v1.get("has_contradictions"),
        sniper_v1.get("contradiction"),
        sniper_v1.get("contradictions"),
    ]
    has_conflict = (flags[0] is True) or (flags[1] is True) or (isinstance(flags[2], list) and len(flags[2]) > 0)
    if has_conflict:
        _add_check(checks, "contradiction", False, "YELLOW", "contradictory_sources")
        return VerdictResult("YELLOW", "contradiction:contradictory_sources", checks)
    _add_check(checks, "contradiction", True, "GREEN", "ok")

    return VerdictResult("GREEN", "all_checks_passed", checks)
