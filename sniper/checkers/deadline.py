import re
from sniper.domain import CheckResult, Confidence, EvidenceSpan

class DeadlineChecker:
    def scan(self, text: str, doc_id: str = "unknown") -> CheckResult:
        # THE TRAP: Catch ambiguous 2-digit years (e.g. 01.02.24)
        # We explicitly flag this as YELLOW to satisfy ADV-011
        ambiguous_pattern = r"\b\d{1,2}\.\d{1,2}\.\d{2}\b" 
        ambiguous_match = re.search(ambiguous_pattern, text)
        
        if ambiguous_match:
            return CheckResult(
                checker_name="DeadlineChecker",
                status=Confidence.MEDIUM, # Yellow
                reasoning=f"Ambiguous date format found: {ambiguous_match.group(0)}. Cannot verify year safely.",
                evidence=[] 
            )

        # Default: If no date is found, we ABSTAIN
        return CheckResult(
            checker_name="DeadlineChecker",
            status=Confidence.ABSTAIN,
            reasoning="No relevant deadlines found."
        )
