from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class TrafficLight(str, Enum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    ABSTAIN = "abstain"


# Verdict severity ordering: lower index = worse (red is worst, green is best)
_VERDICT_SEVERITY = [TrafficLight.RED, TrafficLight.YELLOW, TrafficLight.ABSTAIN, TrafficLight.GREEN]


def worst_verdict(verdicts: List["TrafficLight"]) -> "TrafficLight":
    """Return the worst verdict from a list (red > yellow > abstain > green).

    If empty list, returns GREEN (no signals = green).
    """
    if not verdicts:
        return TrafficLight.GREEN
    worst_idx = min(_VERDICT_SEVERITY.index(v) for v in verdicts)
    return _VERDICT_SEVERITY[worst_idx]


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
    offset_basis: Optional[str] = None  # e.g. "normalized_text_v1" - declares what offsets are relative to
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
        if has_start and (self.offset_basis is None or not self.offset_basis.strip()):
            raise ValueError("EvidenceSpan requires offset_basis when offsets are present")

    def to_dict(self) -> Dict[str, object]:
        """Convert to JSON-serializable dict. Only includes non-None optional fields."""
        d: Dict[str, object] = {
            "doc_id": self.doc_id,
            "page": self.page_number,
            "snippet": self.snippet,
        }
        if self.start_offset is not None:
            d["start_offset"] = self.start_offset
            d["end_offset"] = self.end_offset
        if self.offset_basis is not None:
            d["offset_basis"] = self.offset_basis
        if self.paragraph_index is not None:
            d["paragraph_index"] = self.paragraph_index
        if self.bbox is not None:
            d["bbox"] = self.bbox
        return d




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

    def to_dict(self) -> Dict[str, object]:
        """Convert to JSON-serializable dict for evidence pack."""
        return {
            "check_id": self.checker_name,
            "verdict": self.status.value,
            "reason": self.reason.value,
            "evidence": [ev.to_dict() for ev in self.evidence],
        }


@dataclass(frozen=True)
class RunResult:
    """Output of a single-page run.

    Public contract: this schema is intended to remain stable as checkers grow.
    Future-proofing note: provenance/trace packaging (BlackBox-style) should be added as
    optional, additive fields rather than changing existing meanings.

    Invariant: overall must equal worst verdict among results (if results non-empty).
    """

    overall: TrafficLight
    summary: str
    results: List[CheckerResult]

    def __post_init__(self) -> None:
        """Validate overall verdict matches worst of check verdicts."""
        if self.results:
            expected = worst_verdict([r.status for r in self.results])
            if self.overall != expected:
                raise ValueError(
                    f"RunResult.overall ({self.overall.value}) must equal worst verdict "
                    f"({expected.value}) from checks"
                )

    def to_dict(self) -> Dict[str, object]:
        """Convert to JSON-serializable dict for evidence pack."""
        return {
            "verdict": self.overall.value,
            "overall_verdict": self.overall.value,
            "summary": self.summary,
            "checks": [r.to_dict() for r in self.results],
        }


# Allowed schema versions for forward compatibility checks
ALLOWED_SCHEMA_VERSIONS = frozenset({"1.0"})


@dataclass(frozen=True)
class EvidencePack:
    """Machine-readable evidence pack artifact for KO-scanner output.

    Provides JSON-serializable format containing:
    1) overall traffic light verdict
    2) per-check entries with: check_id/name, verdict, and evidence items
    3) each evidence item includes: doc_id, page, snippet, optional offsets/bbox

    Strict rule enforced by CheckerResult: if evidence is missing for a check,
    that check cannot be GREEN (must be YELLOW/ABSTAIN/RED).

    Contract invariants (enforced at construction):
    - schema_version must be in ALLOWED_SCHEMA_VERSIONS
    - run_result.overall must equal worst verdict of checks (via RunResult)
    - All evidence with offsets must have offset_basis (via EvidenceSpan)
    """

    run_result: RunResult
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        """Validate schema version."""
        if self.schema_version not in ALLOWED_SCHEMA_VERSIONS:
            raise ValueError(
                f"EvidencePack schema_version ({self.schema_version}) not in "
                f"allowed versions: {sorted(ALLOWED_SCHEMA_VERSIONS)}"
            )

    def to_dict(self) -> Dict[str, object]:
        """Convert to JSON-serializable dict.

        Structure:
        {
            "schema_version": "1.0",
            "verdict": "red"|"yellow"|"green"|"abstain",
            "summary": "...",
            "checks": [
                {
                    "check_id": "CheckerName",
                    "verdict": "red"|"yellow"|"green"|"abstain",
                    "reason": "reason_code",
                    "evidence": [
                        {"doc_id": "...", "page": 1, "snippet": "...", ...}
                    ]
                }
            ]
        }
        """
        base = self.run_result.to_dict()
        return {
            "schema_version": self.schema_version,
            **base,
        }
