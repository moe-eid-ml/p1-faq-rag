from __future__ import annotations

from dataclasses import dataclass
import datetime as _dt
import re
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


def _parse_iso_z(ts: str) -> Optional[_dt.datetime]:
    """Parse ISO timestamps that may end with 'Z' into aware UTC datetimes."""
    if not ts:
        return None
    s = ts.strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = _dt.datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc)
        return dt.astimezone(_dt.timezone.utc)
    except Exception:
        return None


def _parse_source_mtime(src: Dict[str, Any]) -> Optional[_dt.datetime]:
    """Best-effort parse of source modified timestamps.

    Supports epoch seconds and ISO strings under common keys.
    """
    for key in ("mtime", "modified_at", "updated_at", "file_mtime", "source_mtime", "timestamp"):
        v = src.get(key)
        if v is None:
            continue
        # epoch seconds
        if isinstance(v, (int, float)):
            try:
                return _dt.datetime.fromtimestamp(float(v), tz=_dt.timezone.utc)
            except Exception:
                continue
        # ISO string
        if isinstance(v, str):
            dt = _parse_iso_z(v)
            if dt is not None:
                return dt
    return None

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

    # Temporal guard: future-year queries are inherently unverifiable.
    q_text = _as_str(sniper_v1.get("query"))
    yrs = re.findall(r"\b(?:19|20)\d{2}\b", q_text)
    if yrs:
        now_year = _dt.datetime.now(_dt.timezone.utc).year
        future_years = sorted({int(y) for y in yrs if int(y) > now_year})
        if future_years:
            missing = [str(y) for y in future_years if str(y) not in combined]
            if missing:
                _add_check(
                    checks,
                    "temporal",
                    False,
                    "YELLOW",
                    "year_not_in_evidence",
                    details={"years": missing, "kind": "future"},
                )
                return VerdictResult(
                    "YELLOW",
                    f"future:cannot verify:year_not_in_evidence:{','.join(missing)}",
                    checks,
                )
            _add_check(
                checks,
                "temporal",
                False,
                "YELLOW",
                "future_year_in_query",
                details={"years": [str(y) for y in future_years], "kind": "future"},
            )
            return VerdictResult("YELLOW", "future:cannot verify", checks)

    # 1b) Respect Phase B verdict: if Phase B is not GREEN, Phase C must not return GREEN.
    b_verdict = _as_str(sniper_v1.get("verdict")).upper()
    b_reason_raw = _as_str(sniper_v1.get("verdict_reason") or sniper_v1.get("reason"))
    b_reason_pretty = b_reason_raw.replace("_", " ")

    # If Phase B doesn't provide a helpful reason, infer a stable hint for tests/UX.
    if (not b_reason_raw) or (b_reason_raw == "all_checks_passed"):
        b_reason_pretty = "no results" if not sources else "insufficient evidence"

    if b_verdict and b_verdict != "GREEN":
        _add_check(
            checks,
            "phase_b",
            False,
            "YELLOW",
            "phase_b_not_green",
            details={"verdict": b_verdict, "verdict_reason": b_reason_raw},
        )
        return VerdictResult(
            "YELLOW",
            f"phase_b_not_green:{b_verdict}:{b_reason_pretty}",
            checks,
        )

    _add_check(checks, "phase_b", True, "GREEN", "ok")

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

    # 4) Outdated sources (best-effort). Only downgrade when we can parse mtimes.
    now_dt = _parse_iso_z(_as_str(sniper_v1.get("timestamp")))
    if now_dt is None:
        now_dt = _dt.datetime.now(_dt.timezone.utc)

    parsed: List[Dict[str, Any]] = []
    if isinstance(sources, list):
        for src in sources:
            if not isinstance(src, dict):
                continue
            mdt = _parse_source_mtime(src)
            if mdt is None:
                continue
            age_days = int((now_dt - mdt).total_seconds() // 86400)
            parsed.append(
                {
                    "source_id": _as_str(src.get("source_id")),
                    "page_ref": _as_str(src.get("page_ref")),
                    "age_days": age_days,
                }
            )

    # Flag only very old sources to avoid spurious yellows on stable statutes.
    max_age = 730
    offenders = [p for p in parsed if p.get("age_days", 0) > max_age]
    if offenders:
        offenders_sorted = sorted(offenders, key=lambda x: int(x.get("age_days", 0)), reverse=True)
        _add_check(
            checks,
            "outdated_sources",
            False,
            "YELLOW",
            "source_mtime_too_old",
            details={"max_age_days": max_age, "offenders": offenders_sorted[:5]},
        )
        return VerdictResult("YELLOW", "outdated_sources:source_mtime_too_old", checks)

    _add_check(
        checks,
        "outdated_sources",
        True,
        "GREEN",
        "ok" if parsed else "no_parseable_mtime",
        details={"max_age_days": max_age, "checked": len(parsed)},
    )

    return VerdictResult("GREEN", "all_checks_passed", checks)
