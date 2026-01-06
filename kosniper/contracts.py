from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

class TrafficLight(str, Enum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    ABSTAIN = "abstain"

class EvidenceSpan(BaseModel):
    doc_id: str
    page_number: int
    snippet: str
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    paragraph_index: Optional[int] = None
    # bbox-ready (optional, do not require for MVP)
    bbox: Optional[dict] = None  # {"x0":..., "y0":..., "x1":..., "y1":...}

class CheckerResult(BaseModel):
    checker_name: str
    status: TrafficLight
    reason: str
    evidence: List[EvidenceSpan] = []

class RunResult(BaseModel):
    overall: TrafficLight
    summary: str
    results: List[CheckerResult]
