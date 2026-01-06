from enum import Enum
from typing import List
from pydantic import BaseModel

class Confidence(str, Enum):
    HIGH = "green"
    MEDIUM = "yellow"
    LOW = "red"
    ABSTAIN = "gray"

class EvidenceSpan(BaseModel):
    doc_id: str
    page_number: int
    text_snippet: str
    start_offset: int
    end_offset: int

class CheckResult(BaseModel):
    checker_name: str
    status: Confidence
    reasoning: str
    evidence: List[EvidenceSpan] = [] 

    def is_safe_green(self) -> bool:
        if self.status == Confidence.HIGH and not self.evidence:
            return False 
        return True
