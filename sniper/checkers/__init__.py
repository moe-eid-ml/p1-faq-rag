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

def determine_verdict(trace: Dict[str, Any]) -> VerdictResult:
    checks: List[Dict[str, Any]] = []

    if not isinstance(trace, dict):
        return VerdictResult("YELLOW", "malformed_trace", [{"check": "input", "ok": False, "severity": "YELLOW"}])

    sniper_v1 = _find_sniper_trace_v1(trace)

    # 1) Provenance gate
    if sniper_v1 is None:
        checks.append({"check": "provenance", "ok": False, "severity": "YELLOW", "reason": "missing_sniper_trace_v1"})
        return VerdictResult("YELLOW", "provenance:missing_sniper_trace_v1", checks)
    checks.append({"check": "provenance", "ok": True, "severity": "GREEN", "reason": "ok"})

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
        checks.append(
            {
                "passed": False,
                "reason": "prompt_injection_detected",
                "details": {"hits": hits},
            }
        )
        return VerdictResult("RED", "injection:prompt_injection_detected", checks)
    checks.append({"check": "injection", "ok": True, "severity": "GREEN", "reason": "ok"})

    # 3) Contradiction stub (treat explicit flags as YELLOW)
    flags = [
        sniper_v1.get("has_contradictions"),
        sniper_v1.get("contradiction"),
        sniper_v1.get("contradictions"),
    ]
    has_conflict = (flags[0] is True) or (flags[1] is True) or (isinstance(flags[2], list) and len(flags[2]) > 0)
    if has_conflict:
        checks.append({"check": "contradiction", "ok": False, "severity": "YELLOW", "reason": "contradictory_sources"})
        return VerdictResult("YELLOW", "contradiction:contradictory_sources", checks)
    checks.append({"check": "contradiction", "ok": True, "severity": "GREEN", "reason": "ok"})

    return VerdictResult("GREEN", "all_checks_passed", checks)
