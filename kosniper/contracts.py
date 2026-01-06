from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class TrafficLight(str, Enum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    ABSTAIN = "abstain"


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
    reason: str
    evidence: List[EvidenceSpan] = field(default_factory=list)


@dataclass(frozen=True)
class RunResult:
    overall: TrafficLight
    summary: str
    results: List[CheckerResult]
