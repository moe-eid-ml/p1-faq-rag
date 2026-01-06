from enum import Enum
from typing import List
from pydantic import BaseModel

class Confidence(str, Enum):
    HIGH = "green"      # 100% sure based on explicit text
    MEDIUM = "yellow"   # Likely, but requires human eyes
    LOW = "red"         # Explicit violation found
    ABSTAIN = "gray"    # Cannot find data / Not applicable

class EvidenceSpan(BaseModel):
    doc_id: str
    page_number: int
    text_snippet: str   # The exact text extracted
    start_offset: int   # Character index start
    end_offset: int     # Character index end

class CheckResult(BaseModel):
    checker_name: str
    status: Confidence
    reasoning: str            # Explanation of the logic
    evidence: List[EvidenceSpan] = [] 

    # THE SAFETY GATE:
    # Logic to enforce "No False Greens"
    # If a checker claims GREEN but provides NO EVIDENCE, this returns False.
    def is_safe_green(self) -> bool:
        if self.status == Confidence.HIGH and not self.evidence:
            return False 
        return True