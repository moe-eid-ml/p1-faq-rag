"""
Adversarial runner (skeleton).

Goal:
- Load versioned adversarial cases (tests/adversarial/cases_v1.json)
- Provide a stable interface for CI to "run cases" and produce per-case results
- Implementation of real verdicting comes later (after we add Sniper wrapper / checkers)

For now this runner is intentionally conservative: returns YELLOW with a clear reason.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class AdversarialCase:
    id: str
    title: str
    query: str
    expected_verdict: str
    expected_reason_contains: List[str]
    requires_harness: bool


def load_cases(path: str | Path = "tests/adversarial/cases_v1.json") -> List[AdversarialCase]:
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    cases: List[AdversarialCase] = []
    for c in raw:
        cases.append(
            AdversarialCase(
                id=c["id"],
                title=c["title"],
                query=c["query"],
                expected_verdict=c["expected_verdict"],
                expected_reason_contains=list(c["expected_reason_contains"]),
                requires_harness=bool(c["requires_harness"]),
            )
        )
    return cases


# answer_fn signature: (query: str) -> dict-like output, later.
AnswerFn = Callable[[str], Dict]


def run_case(case: AdversarialCase, answer_fn: Optional[AnswerFn] = None) -> Dict:
    """
    Returns a stable result record.
    If answer_fn is provided, we call it and map to {id, verdict, reason, details}.
    """
    if answer_fn is None:
        return {
            "id": case.id,
            "verdict": "YELLOW",
            "reason": "runner_not_implemented",
            "details": {
                "title": case.title,
                "requires_harness": case.requires_harness,
            },
        }

    out = answer_fn(case.query) or {}
    verdict = out.get("verdict", "YELLOW")
    reason = out.get("reason", "missing_reason")
    return {
        "id": case.id,
        "verdict": verdict,
        "reason": reason,
        "details": {
            "title": case.title,
            "requires_harness": case.requires_harness,
        },
    }


def run_all(
    answer_fn: Optional[AnswerFn] = None,
    include_harness: bool = False,
    cases_path: str | Path = "tests/adversarial/cases_v1.json",
) -> List[Dict]:
    cases = load_cases(cases_path)
    results: List[Dict] = []
    for c in cases:
        if c.requires_harness and not include_harness:
            # Skip harness-required cases unless explicitly enabled.
            continue
        results.append(run_case(c, answer_fn=answer_fn))
    return results
