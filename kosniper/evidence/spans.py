"""MC-KOS-28: Evidence span finder.

Provides deterministic utilities for locating substrings in normalized text
and returning proof-first evidence spans with offsets.
"""

from __future__ import annotations

import re
from typing import Optional


def make_snippet(text: str, start: int, end: int, window: int = 80) -> str:
    """Extract a snippet with context window around a match.

    Args:
        text: Source text.
        start: Start offset of match.
        end: End offset of match.
        window: Context characters to include before/after match.

    Returns:
        Snippet string with context.
    """
    snippet_start = max(0, start - window)
    snippet_end = min(len(text), end + window)
    return text[snippet_start:snippet_end]


def find_span(
    text: str,
    needle: str,
    *,
    casefold: bool = True,
) -> Optional[dict]:
    """Find a substring in text and return span info.

    Args:
        text: Text to search (should be normalized_text_v1).
        needle: Substring to find.
        casefold: If True, perform case-insensitive search.

    Returns:
        Dict with start, end, offset_basis, snippet if found; None otherwise.
    """
    if not text or not needle:
        return None

    search_text = text.lower() if casefold else text
    search_needle = needle.lower() if casefold else needle

    idx = search_text.find(search_needle)
    if idx == -1:
        return None

    start = idx
    end = idx + len(needle)

    return {
        "start": start,
        "end": end,
        "offset_basis": "normalized_text_v1",
        "snippet": make_snippet(text, start, end),
    }


def find_span_regex(
    text: str,
    pattern: str,
    *,
    flags: int = re.IGNORECASE,
) -> Optional[dict]:
    """Find a regex match in text and return span info.

    Args:
        text: Text to search (should be normalized_text_v1).
        pattern: Regex pattern to match.
        flags: Regex flags (default: re.IGNORECASE).

    Returns:
        Dict with start, end, offset_basis, snippet if found; None otherwise.
    """
    if not text or not pattern:
        return None

    try:
        match = re.search(pattern, text, flags=flags)
    except re.error:
        return None

    if match is None:
        return None

    start, end = match.span()

    return {
        "start": start,
        "end": end,
        "offset_basis": "normalized_text_v1",
        "snippet": make_snippet(text, start, end),
    }


def find_all_spans(
    text: str,
    needle: str,
    *,
    casefold: bool = True,
) -> list[dict]:
    """Find all occurrences of a substring in text.

    Args:
        text: Text to search.
        needle: Substring to find.
        casefold: If True, perform case-insensitive search.

    Returns:
        List of span dicts (may be empty).
    """
    if not text or not needle:
        return []

    search_text = text.lower() if casefold else text
    search_needle = needle.lower() if casefold else needle

    results = []
    start_pos = 0

    while True:
        idx = search_text.find(search_needle, start_pos)
        if idx == -1:
            break

        start = idx
        end = idx + len(needle)
        results.append({
            "start": start,
            "end": end,
            "offset_basis": "normalized_text_v1",
            "snippet": make_snippet(text, start, end),
        })
        start_pos = end

    return results
