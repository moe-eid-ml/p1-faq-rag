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
    doc_id: str
    page_number: int
    snippet: str
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    paragraph_index: Optional[int] = None
    # bbox-ready (optional, do not require for MVP)
    bbox: Optional[Dict[str, float]] = None  # {"x0":..., "y0":..., "x1":..., "y1":...}


@dataclass(frozen=True)
class CheckerResult:
    checker_name: str
    status: TrafficLight
    reason: ReasonCode
    evidence: List[EvidenceSpan] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate evidence for non-neutral results."""
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
    overall: TrafficLight
    summary: str
    results: List[CheckerResult]
