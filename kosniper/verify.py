"""MC-KOS-46: Verify export pack integrity.

Validates an out-dir produced by `kosniper --scan --out-dir`:
- Required files exist: evidence_pack.json, document_map.json
- JSON parses correctly
- Proof-first invariants hold (offset_basis, no false-green, worst-check-wins)

Fail-closed: any validation failure returns error tuple (False, reason).
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Valid verdicts in severity order
VALID_VERDICTS = {"red", "yellow", "abstain", "green"}
SEVERITY_RANK = {"red": 0, "yellow": 1, "abstain": 2, "green": 3}


def verify_pack(in_dir: str) -> Tuple[bool, str]:
    """Verify an export pack directory.

    Args:
        in_dir: Path to directory containing evidence_pack.json and document_map.json.

    Returns:
        (True, "OK") if valid, (False, "error reason") if invalid.

    Fail-closed: any missing file, parse error, or invariant violation fails.
    """
    dir_path = Path(in_dir)

    # 1. Check directory exists
    if not dir_path.is_dir():
        return False, f"Directory not found: {in_dir}"

    # 2. Check required files exist
    evidence_pack_path = dir_path / "evidence_pack.json"
    document_map_path = dir_path / "document_map.json"

    if not evidence_pack_path.exists():
        return False, "Missing required file: evidence_pack.json"
    if not document_map_path.exists():
        return False, "Missing required file: document_map.json"

    # 3. Load and parse JSON
    try:
        with open(evidence_pack_path, encoding="utf-8") as f:
            evidence_pack = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in evidence_pack.json: {e}"
    except OSError as e:
        return False, f"Error reading evidence_pack.json: {e}"

    try:
        with open(document_map_path, encoding="utf-8") as f:
            document_map = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in document_map.json: {e}"
    except OSError as e:
        return False, f"Error reading document_map.json: {e}"

    # 4. Validate document_map structure
    doc_map_result = _validate_document_map(document_map)
    if not doc_map_result[0]:
        return doc_map_result

    # 5. Validate evidence_pack invariants
    pack_result = _validate_evidence_pack(evidence_pack)
    if not pack_result[0]:
        return pack_result

    return True, "OK"


def _validate_document_map(doc_map: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate document_map.json structure."""
    # Must have doc_id
    if not doc_map.get("doc_id"):
        return False, "document_map.json: missing or empty doc_id"

    # Must have offset_basis
    if not doc_map.get("offset_basis"):
        return False, "document_map.json: missing offset_basis"

    # Must have overall_sha256 (can be null for aborted scans, but key must exist)
    if "overall_sha256" not in doc_map:
        return False, "document_map.json: missing overall_sha256 field"

    return True, "OK"


def _validate_evidence_pack(pack: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate evidence_pack.json invariants."""
    # Must have overall_verdict
    overall_verdict = pack.get("overall_verdict") or pack.get("verdict")
    if not overall_verdict:
        return False, "evidence_pack.json: missing overall_verdict"

    if not isinstance(overall_verdict, str):
        return False, (
            "evidence_pack.json: overall_verdict must be a string, "
            f"got {type(overall_verdict).__name__}"
        )

    # Verdict must be valid
    if overall_verdict.lower() not in VALID_VERDICTS:
        return False, f"evidence_pack.json: invalid overall_verdict '{overall_verdict}'"

    checks = pack.get("checks", [])

    # Validate worst-check-wins
    if checks:
        worst_result = _validate_worst_check_wins(overall_verdict, checks)
        if not worst_result[0]:
            return worst_result

    # Validate offset_basis for all evidence with offsets
    offset_result = _validate_offset_basis(checks)
    if not offset_result[0]:
        return offset_result

    # Validate no false-green (GREEN requires evidence)
    green_result = _validate_no_false_green(overall_verdict, checks)
    if not green_result[0]:
        return green_result

    return True, "OK"


def _validate_worst_check_wins(overall_verdict: str, checks: List[Dict]) -> Tuple[bool, str]:
    """Validate overall_verdict is at least as severe as worst check."""
    if not checks:
        return True, "OK"

    if not isinstance(overall_verdict, str) or overall_verdict.lower() not in VALID_VERDICTS:
        return False, (
            f"evidence_pack.json: invalid overall_verdict '{overall_verdict}'"
        )

    verdicts: List[str] = []
    for i, check in enumerate(checks):
        if not isinstance(check, dict):
            return False, f"check[{i}] must be a dict, got {type(check).__name__}"
        verdict = check.get("verdict")
        if not isinstance(verdict, str) or verdict.lower() not in VALID_VERDICTS:
            return False, (
                f"check[{i}].verdict invalid: {verdict!r}"
            )
        verdicts.append(verdict.lower())

    overall_sev = SEVERITY_RANK[overall_verdict.lower()]
    worst_check_sev = min(
        SEVERITY_RANK[verdict]
        for verdict in verdicts
    )

    if overall_sev > worst_check_sev:
        worst_index = min(
            range(len(verdicts)),
            key=lambda i: SEVERITY_RANK[verdicts[i]],
        )
        worst_verdict = checks[worst_index]["verdict"]
        return False, (
            f"Worst-check-wins violated: overall_verdict={overall_verdict} "
            f"but worst check has verdict={worst_verdict}"
        )

    return True, "OK"


def _validate_offset_basis(checks: List[Dict]) -> Tuple[bool, str]:
    """Validate all evidence with offsets has offset_basis='normalized_text_v1'."""
    for i, check in enumerate(checks):
        if not isinstance(check, dict):
            return False, f"check[{i}] must be a dict, got {type(check).__name__}"
        for j, ev in enumerate(check.get("evidence", [])):
            has_offsets = ev.get("start_offset") is not None or ev.get("end_offset") is not None
            if has_offsets:
                offset_basis = ev.get("offset_basis")
                if offset_basis != "normalized_text_v1":
                    return False, (
                        f"check[{i}].evidence[{j}]: offset_basis={offset_basis!r} "
                        f"but offsets present (must be 'normalized_text_v1')"
                    )
    return True, "OK"


def _validate_no_false_green(overall_verdict: str, checks: List[Dict]) -> Tuple[bool, str]:
    """Validate GREEN verdict is not produced without evidence."""
    if overall_verdict.lower() != "green":
        return True, "OK"

    # GREEN requires at least one check with evidence
    has_evidence = any(
        isinstance(check, dict) and check.get("evidence") for check in checks
    )

    if not has_evidence:
        return False, "False-green: overall_verdict=green but no evidence present"

    return True, "OK"


def write_receipt(in_dir: str) -> Tuple[bool, str]:
    """Write verify_receipt.json to the input directory.

    Only call this after verify_pack() returns (True, "OK").
    Fail-closed: catches OSError and returns (False, error_msg).

    Args:
        in_dir: Path to directory containing the verified pack.

    Returns:
        (True, "OK") on success, (False, "error reason") on failure.
    """
    dir_path = Path(in_dir)
    receipt_path = dir_path / "verify_receipt.json"

    # Load document_map.json and evidence_pack.json to extract sha256 if present
    doc_map_sha256 = None
    evidence_pack_sha256 = None

    try:
        with open(dir_path / "document_map.json", encoding="utf-8") as f:
            doc_map = json.load(f)
            doc_map_sha256 = doc_map.get("overall_sha256")
    except (OSError, json.JSONDecodeError):
        pass  # Not critical for receipt

    try:
        with open(dir_path / "evidence_pack.json", encoding="utf-8") as f:
            evidence_pack = json.load(f)
            # evidence_pack doesn't have its own sha256 key by schema
            # but check anyway for forward compatibility
            evidence_pack_sha256 = evidence_pack.get("overall_sha256")
    except (OSError, json.JSONDecodeError):
        pass  # Not critical for receipt

    # Get version if available
    try:
        from importlib.metadata import version as get_version
        tool_version = get_version("p1-faq-rag")
    except Exception:
        tool_version = "unknown"

    receipt = {
        "status": "ok",
        "tool": "kosniper",
        "version": tool_version,
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "in_dir": in_dir,
    }

    if doc_map_sha256 is not None:
        receipt["document_map_sha256"] = doc_map_sha256
    if evidence_pack_sha256 is not None:
        receipt["evidence_pack_sha256"] = evidence_pack_sha256

    try:
        with open(receipt_path, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except OSError as e:
        return False, f"Failed to write verify_receipt.json: {e}"

    return True, "OK"
