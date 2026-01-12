from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class TrafficLight(str, Enum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    ABSTAIN = "abstain"


class ReasonCode(str, Enum):
    """Typed reason codes for CheckerResult."""

    NO_TEXT = "no_text"
    KO_PHRASE_FOUND = "ko_phrase_found"
    MISSING_CURRENCY = "missing_currency"
    AMBIGUOUS_REQUIREMENT = "ambiguous_requirement"
    AMBIGUOUS_THRESHOLD_COUNT = "ambiguous_threshold_count"
    MISSING_COMPANY_TURNOVER = "missing_company_turnover"
    BELOW_THRESHOLD = "below_threshold"


@dataclass(frozen=True)
class EvidenceSpan:
    """Evidence snippet anchored to a document location.

    Notes (public contract):
    - `start_offset` / `end_offset` are optional character offsets into the *text that was evaluated*.
      In the MVP, many checkers will not provide offsets (both are `None`).
    - If one offset is present, both must be present (pair invariant).
    - Offsets may refer to normalized/processed text; consumers must not assume they align
      perfectly with raw PDF bytes.
    - `bbox` is optional (MVP may omit it). Consumers must not require `bbox`.
    """

    doc_id: str
    page_number: int
    snippet: str
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    paragraph_index: Optional[int] = None
    # bbox-ready (optional, do not require for MVP)
    bbox: Optional[Dict[str, float]] = None  # {"x0":..., "y0":..., "x1":..., "y1":...}

    def __post_init__(self) -> None:
        """Validate offset pair invariants."""
        has_start = self.start_offset is not None
        has_end = self.end_offset is not None
        if has_start != has_end:
            raise ValueError(
                "EvidenceSpan requires start_offset and end_offset to be both None or both int"
            )


@dataclass(frozen=True)
class CheckerResult:
    checker_name: str
    status: TrafficLight
    reason: ReasonCode
    evidence: List[EvidenceSpan] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate evidence for non-neutral results.

        Public contract:
        - Non-neutral results (RED/YELLOW/ABSTAIN) must include at least one EvidenceSpan.
        - Each EvidenceSpan.snippet must be non-empty (human-auditable proof).
        """
        # Non-neutral results (RED/YELLOW/ABSTAIN) require evidence
        if self.status in (TrafficLight.RED, TrafficLight.YELLOW, TrafficLight.ABSTAIN):
            if not self.evidence:
                raise ValueError(
                    f"Non-neutral result ({self.status.value}) requires non-empty evidence"
                )
            for ev in self.evidence:
                if not ev.snippet or not ev.snippet.strip():
                    raise ValueError(
                        f"Non-neutral result ({self.status.value}) requires non-empty snippet"
                    )


@dataclass(frozen=True)
class RunResult:
    """Output of a single-page run.

    Public contract: this schema is intended to remain stable as checkers grow.
    Future-proofing note: provenance/trace packaging (BlackBox-style) should be added as
    optional, additive fields rather than changing existing meanings.
    """

    overall: TrafficLight
    summary: str
    results: List[CheckerResult]
