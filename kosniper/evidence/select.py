"""MC-KOS-35: Evidence selection policy.

Applies deterministic filtering, sorting, deduplication, and truncation
to evidence lists before output. Never fabricates evidence.
"""

from typing import Any, Dict, List, Optional, Tuple


def _sort_key(ev: Dict[str, Any]) -> Tuple:
    """Generate stable sort key for evidence item.

    Ordering: (doc_id, page_number, start, end, snippet)
    Missing start/end sorts last (use large sentinel values).
    """
    doc_id = ev.get("doc_id", "")
    page = ev.get("page", 0)
    start = ev.get("start_offset")
    end = ev.get("end_offset")
    snippet = ev.get("snippet", "")

    # Missing offsets sort last
    start_key = start if start is not None else float("inf")
    end_key = end if end is not None else float("inf")

    return (doc_id, page, start_key, end_key, snippet)


def _dedup_key(ev: Dict[str, Any]) -> Tuple:
    """Generate deduplication key for evidence item."""
    return (
        ev.get("doc_id", ""),
        ev.get("page", 0),
        ev.get("start_offset"),
        ev.get("end_offset"),
        ev.get("snippet", ""),
        ev.get("offset_basis"),
    )


def _truncate_snippet(ev: Dict[str, Any], max_len: int) -> Dict[str, Any]:
    """Truncate snippet to max_len chars, adding ellipsis if truncated."""
    snippet = ev.get("snippet", "")
    if len(snippet) > max_len:
        ev = ev.copy()
        ev["snippet"] = snippet[: max_len - 3] + "..."
    return ev


def apply_evidence_policy(
    checks: List[Dict[str, Any]],
    *,
    max_k: int = 3,
    max_total: int = 10,
    max_snippet_len: int = 200,
) -> List[Dict[str, Any]]:
    """Apply evidence selection policy to check results.

    Args:
        checks: List of check dicts with "evidence" lists.
        max_k: Maximum evidence items per check.
        max_total: Maximum total evidence items across all checks.
        max_snippet_len: Maximum snippet length (truncated with "...").

    Returns:
        New list of check dicts with filtered/formatted evidence.
        Never fabricates evidence; only filters what checkers produce.
    """
    result = []
    total_evidence = 0

    for check in checks:
        check = check.copy()
        evidence = check.get("evidence", [])

        # Deduplicate
        seen = set()
        deduped = []
        for ev in evidence:
            key = _dedup_key(ev)
            if key not in seen:
                seen.add(key)
                deduped.append(ev)

        # Sort deterministically
        deduped.sort(key=_sort_key)

        # Limit per check
        deduped = deduped[:max_k]

        # Limit total
        remaining = max_total - total_evidence
        if remaining <= 0:
            deduped = []
        elif len(deduped) > remaining:
            deduped = deduped[:remaining]

        # Truncate snippets
        deduped = [_truncate_snippet(ev, max_snippet_len) for ev in deduped]

        total_evidence += len(deduped)
        check["evidence"] = deduped
        result.append(check)

    return result


def validate_evidence_offset_basis(checks: List[Dict[str, Any]]) -> Optional[str]:
    """Validate offset_basis for all evidence with offsets (fail-closed).

    Args:
        checks: List of check dicts with "evidence" lists.

    Returns:
        Error message if validation fails, None if valid.
    """
    for check in checks:
        for ev in check.get("evidence", []):
            has_offsets = ev.get("start_offset") is not None
            if has_offsets:
                basis = ev.get("offset_basis")
                if basis != "normalized_text_v1":
                    return (
                        f"Evidence has offsets but invalid offset_basis "
                        f"({basis!r}). Must be 'normalized_text_v1'."
                    )
    return None
