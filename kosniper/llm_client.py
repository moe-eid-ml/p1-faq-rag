"""MC-KOS-51 (Phase 1): LLM client boundary.

The checker never talks to an SDK directly; it only sees this Protocol.
Phase 1 ships no live client: get_llm_client() always returns None, so the
registered LLMEvidenceChecker is inert in the default pipeline (returns None,
contributing nothing). A live client (Phase 2) is a separate decision that
requires explicit dependency approval per CLAUDE.md.
"""

from __future__ import annotations

import os
from typing import Optional, Protocol


class LLMClient(Protocol):
    """Minimal completion interface the checker depends on."""

    def complete(self, prompt: str) -> str:
        """Return the raw model output for a prompt."""
        ...


def llm_disabled() -> bool:
    """True when the LLM checker is explicitly disabled (mirrors DISABLE_SEMANTIC)."""
    return os.environ.get("DISABLE_LLM") == "1"


def get_llm_client() -> Optional[LLMClient]:
    """Return a live LLM client, or None if disabled or unavailable.

    Phase 1: there is no live client, so this always returns None.
    Phase 2 would construct one here (behind the same Protocol), keeping
    DISABLE_LLM=1 as the hard off-switch so CI stays deterministic.
    """
    if llm_disabled():
        return None
    # Phase 1: no live client implemented yet.
    return None
