"""MC-KOS-13: CLI for KO scanner evidence pack generation.

Usage:
    python -m kosniper.cli --doc-id tender.pdf --page 3 --text "Mindestumsatz 500.000 EUR"
    python -m kosniper.cli --doc-id tender.pdf --page 3 --text-file input.txt --out result.json
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from kosniper.pipeline import make_evidence_pack


def main(argv: Optional[list[str]] = None) -> int:
    """Run KO scanner CLI and output EvidencePack JSON."""
    parser = argparse.ArgumentParser(
        description="Run KO scanner on text and output EvidencePack JSON.",
        prog="python -m kosniper.cli",
    )
    parser.add_argument(
        "--doc-id",
        required=True,
        help="Document identifier for provenance (required)",
    )
    parser.add_argument(
        "--page",
        type=int,
        required=True,
        help="Page number in document (required, must be >= 1)",
    )
    parser.add_argument(
        "--text",
        help="Text to scan (mutually exclusive with --text-file)",
    )
    parser.add_argument(
        "--text-file",
        help="Path to file containing text to scan (mutually exclusive with --text)",
    )
    parser.add_argument(
        "--out",
        help="Output file path (optional, defaults to stdout)",
    )
    parser.add_argument(
        "--format",
        choices=["pretty", "json"],
        default="pretty",
        help="Output format: pretty (indented) or json (compact)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress human summary output to stderr",
    )

    args = parser.parse_args(argv)

    # Validate mutually exclusive text input
    if args.text is not None and args.text_file is not None:
        print("Error: --text and --text-file are mutually exclusive", file=sys.stderr)
        return 2
    if args.text is None and args.text_file is None:
        print("Error: one of --text or --text-file is required", file=sys.stderr)
        return 2

    # Validate page number
    if args.page < 1:
        print("Error: --page must be >= 1", file=sys.stderr)
        return 2

    # Get text content
    if args.text is not None:
        text = args.text
    else:
        try:
            with open(args.text_file, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            print(f"Error reading text file: {e}", file=sys.stderr)
            return 2

    # Run scanner
    pack = make_evidence_pack(text=text, doc_id=args.doc_id, page_number=args.page)
    result = pack.to_dict()
    checks = result.get("checks")
    if not isinstance(checks, list):
        checks = []

    # Allowed verdict values (fail-closed: reject unknown)
    allowed_verdicts = {"red", "yellow", "abstain", "green"}

    # Guard 0: Validate overall_verdict exists and is allowed (fail-closed)
    overall = result.get("overall_verdict")
    if not isinstance(overall, str) or overall not in allowed_verdicts:
        print(
            f"Error: Invalid or missing overall_verdict ({overall!r}). "
            f"Must be one of: {sorted(allowed_verdicts)}",
            file=sys.stderr,
        )
        return 2

    # Guard 0b: Validate each check verdict (fail-closed)
    for i, check in enumerate(checks):
        check_verdict = check.get("verdict")
        if not isinstance(check_verdict, str) or check_verdict not in allowed_verdicts:
            print(
                f"Error: Invalid or missing verdict in check {i} ({check_verdict!r}). "
                f"Must be one of: {sorted(allowed_verdicts)}",
                file=sys.stderr,
            )
            return 2

    # Guard 1: GREEN without evidence is not allowed
    if overall == "green" and not checks:
        print("Error: GREEN without evidence is not allowed", file=sys.stderr)
        return 2

    # Guard 2: Contradiction check - no check verdict should be worse than overall
    # Severity ordering: red > yellow > abstain > green (lower index = worse)
    severity = {"red": 0, "yellow": 1, "abstain": 2, "green": 3}
    overall_sev = severity[overall]  # Safe: validated above
    for check in checks:
        check_verdict = check["verdict"]  # Safe: validated above
        check_sev = severity[check_verdict]
        if check_sev < overall_sev:
            print(
                f"Error: Contradictory output - check verdict ({check_verdict}) "
                f"is worse than overall verdict ({overall})",
                file=sys.stderr,
            )
            return 2

    # Output JSON
    if args.format == "json":
        json_output = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    else:
        json_output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(json_output)
            f.write("\n")
    else:
        print(json_output)

    # Print human summary to stderr
    if not args.quiet:
        summary = result.get("summary", "")
        check_count = len(checks)
        print(f"[{overall.upper()}] {summary} ({check_count} check(s))", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
