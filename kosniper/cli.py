"""MC-KOS-13: CLI for KO scanner evidence pack generation.

Usage:
    python -m kosniper.cli --doc-id tender.pdf --page 3 --text "Mindestumsatz 500.000 EUR"
    python -m kosniper.cli --doc-id tender.pdf --page 3 --text-file input.txt --out result.json
    python -m kosniper.cli --pdf tender.pdf --out ingest.json  (PDF ingest mode)
    python -m kosniper.cli --pdf tender.pdf --find "Ausschlusskriterium"  (find span in PDF)
    python -m kosniper.cli --pdf tender.pdf --scan --out result.json  (PDF scan mode)
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from kosniper.pipeline import make_evidence_pack

# MC-KOS-40/45: Scan limits to prevent DoS / OOM (configurable via CLI/env)
DEFAULT_MAX_PDF_BYTES = 50_000_000  # 50 MB
DEFAULT_MAX_SCAN_PAGES = 500


def _resolve_limit(cli_value, env_var: str, default: int) -> int:
    """Resolve limit from CLI arg > env var > default. Returns int."""
    import os
    if cli_value is not None:
        return int(cli_value)
    env_val = os.environ.get(env_var)
    if env_val is not None:
        try:
            return int(env_val)
        except ValueError:
            print(
                f"Warning: Invalid {env_var}={env_val!r}, using default {default}",
                file=sys.stderr,
            )
            return default
    return default


def main(argv: Optional[list[str]] = None) -> int:
    """Run KO scanner CLI and output EvidencePack JSON."""
    parser = argparse.ArgumentParser(
        description="Run KO scanner on text and output EvidencePack JSON.",
        prog="python -m kosniper.cli",
    )
    parser.add_argument(
        "--doc-id",
        help="Document identifier for provenance (required for scanner mode, optional for --pdf)",
    )
    parser.add_argument(
        "--page",
        type=int,
        help="Page number in document (required for scanner mode, must be >= 1)",
    )
    parser.add_argument(
        "--text",
        help="Text to scan (mutually exclusive with --text-file)",
    )
    parser.add_argument(
        "--text-file",
        help="Path to file containing text to scan (mutually exclusive with --text, --pdf)",
    )
    parser.add_argument(
        "--pdf",
        help="Path to PDF file for ingestion mode (mutually exclusive with --text, --text-file)",
    )
    parser.add_argument(
        "--find",
        help="Find substring in PDF pages and return span info (requires --pdf)",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Run KO scanner on all PDF pages (requires --pdf, mutually exclusive with --find)",
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
    parser.add_argument(
        "--out-dir",
        help="Output directory for report pack (report.md + evidence_pack.json; requires --scan)",
    )
    parser.add_argument(
        "--verify-pack",
        action="store_true",
        help="Verify an evidence pack directory",
    )
    parser.add_argument(
        "--in-dir",
        help="Input directory for --verify-pack",
    )
    parser.add_argument(
        "--receipt",
        action="store_true",
        help="Write verify_receipt.json on successful verification (requires --verify-pack)",
    )
    # MC-KOS-45: Configurable scan limits
    parser.add_argument(
        "--max-pdf-mb",
        type=int,
        help=f"Max PDF size in MB (default {DEFAULT_MAX_PDF_BYTES // 1_000_000}; env: KOSNIPER_MAX_PDF_BYTES)",
    )
    parser.add_argument(
        "--max-scan-pages",
        type=int,
        help=f"Max pages to scan (default {DEFAULT_MAX_SCAN_PAGES}; env: KOSNIPER_MAX_SCAN_PAGES)",
    )

    args = parser.parse_args(argv)

    if args.verify_pack:
        if args.in_dir is None:
            print("Error: --verify-pack requires --in-dir", file=sys.stderr)
            return 2
        from kosniper.verify import verify_pack, write_receipt

        ok, msg = verify_pack(args.in_dir)
        if ok:
            if args.receipt:
                receipt_ok, receipt_msg = write_receipt(args.in_dir)
                if not receipt_ok:
                    print(f"Error: {receipt_msg}", file=sys.stderr)
                    return 2
            print("OK")
            return 0
        # Fail-closed: do not write receipt on verification failure
        print(f"Error: {msg}", file=sys.stderr)
        return 2

    # Count input modes
    input_modes = sum([
        args.text is not None,
        args.text_file is not None,
        args.pdf is not None,
    ])

    if input_modes > 1:
        print("Error: --text, --text-file, and --pdf are mutually exclusive", file=sys.stderr)
        return 2
    if input_modes == 0:
        print("Error: one of --text, --text-file, or --pdf is required", file=sys.stderr)
        return 2

    # Validate --find requires --pdf
    if args.find is not None and args.pdf is None:
        print("Error: --find requires --pdf", file=sys.stderr)
        return 2

    # Validate --scan requires --pdf and is mutually exclusive with --find
    if args.scan and args.pdf is None:
        print("Error: --scan requires --pdf", file=sys.stderr)
        return 2
    if args.scan and args.find is not None:
        print("Error: --scan and --find are mutually exclusive", file=sys.stderr)
        return 2

    # MC-KOS-43: Validate --out-dir requires --scan
    if args.out_dir is not None and not args.scan:
        print("Error: --out-dir requires --scan", file=sys.stderr)
        return 2

    # MC-KOS-45: Resolve scan limits (CLI > env > default)
    max_pdf_bytes = _resolve_limit(
        args.max_pdf_mb * 1_000_000 if args.max_pdf_mb is not None else None,
        "KOSNIPER_MAX_PDF_BYTES",
        DEFAULT_MAX_PDF_BYTES,
    )
    max_scan_pages = _resolve_limit(
        args.max_scan_pages,
        "KOSNIPER_MAX_SCAN_PAGES",
        DEFAULT_MAX_SCAN_PAGES,
    )

    # PDF ingestion mode
    if args.pdf is not None:
        import os
        from kosniper.ingest.pdf_ingest import ingest_pdf

        # MC-KOS-40: Check file size limit
        try:
            file_size = os.path.getsize(args.pdf)
        except OSError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2

        if file_size > max_pdf_bytes:
            # Fail-closed with Yellow verdict (never Green without evidence)
            from kosniper.contracts import CheckerResult, EvidenceSpan, ReasonCode, TrafficLight
            limit_check = CheckerResult(
                checker_name="ScanLimitGuard",
                status=TrafficLight.YELLOW,
                reason=ReasonCode.SCAN_LIMIT_EXCEEDED,
                evidence=[EvidenceSpan(
                    doc_id=args.pdf,
                    page_number=0,
                    snippet=f"SCAN_ABORTED: file_size={file_size} exceeds max_bytes={max_pdf_bytes}",
                )],
            )
            doc_id = args.doc_id if args.doc_id else os.path.basename(args.pdf)
            result = {
                "schema_version": "1.0",
                "verdict": "yellow",
                "overall_verdict": "yellow",
                "summary": "Scan aborted: file size limit exceeded.",
                "checks": [limit_check.to_dict()],
                "document_map": {
                    "doc_id": doc_id,
                    "offset_basis": "normalized_text_v1",
                    "pages": [],
                    "overall_sha256": None,
                },
            }
            if args.format == "json":
                json_output = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
            else:
                json_output = json.dumps(result, indent=2, ensure_ascii=False)
            if args.out:
                with open(args.out, "w", encoding="utf-8") as f:
                    f.write(json_output + "\n")
            else:
                print(json_output)
            if not args.quiet:
                print("Overall: yellow (file size limit exceeded)", file=sys.stderr)
            return 0

        try:
            ingest_result = ingest_pdf(args.pdf, doc_id=args.doc_id if args.doc_id else None)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2

        # If --find is specified, search for the needle in pages
        if args.find is not None:
            from kosniper.evidence.spans import find_span

            spans = []
            for page_info in ingest_result.get("pages", []):
                normalized = page_info.get("normalized_text_v1", "")
                span = find_span(normalized, args.find)
                if span is not None:
                    span["page"] = page_info["page"]
                    span["doc_id"] = ingest_result["doc_id"]
                    spans.append(span)

            result = {
                "doc_id": ingest_result["doc_id"],
                "needle": args.find,
                "matches": spans,
            }
        elif args.scan:
            # MC-KOS-31: PDF scan mode - run checkers on all pages
            # Ordering: page order (1, 2, ...) × registry order (deterministic)
            import hashlib

            from kosniper.pipeline import run_single_page
            from kosniper.contracts import worst_verdict, TrafficLight, CheckerResult, EvidenceSpan, ReasonCode

            doc_id = ingest_result["doc_id"]
            all_checks = []
            all_verdicts = []
            page_map_entries = []

            # MC-KOS-40/45: Check page count limit (configurable)
            pages = ingest_result.get("pages", [])
            if len(pages) > max_scan_pages:
                limit_check = CheckerResult(
                    checker_name="ScanLimitGuard",
                    status=TrafficLight.YELLOW,
                    reason=ReasonCode.SCAN_LIMIT_EXCEEDED,
                    evidence=[EvidenceSpan(
                        doc_id=doc_id,
                        page_number=0,
                        snippet=f"SCAN_ABORTED: page_count={len(pages)} exceeds max_pages={max_scan_pages}",
                    )],
                )
                all_checks.append(limit_check.to_dict())
                all_verdicts.append(TrafficLight.YELLOW)
                pages = []  # Skip page processing

            for page_info in pages:
                page_num = page_info["page"]
                raw_text = page_info.get("raw_text", "")
                normalized = page_info.get("normalized_text_v1", "")

                # Build page map entry for provenance
                page_map_entries.append({
                    "page_number": page_num,
                    "raw_text_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
                    "normalized_text_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
                    "char_count_raw": len(raw_text),
                    "char_count_normalized": len(normalized),
                })

                page_result = run_single_page(
                    text=normalized,
                    doc_id=doc_id,
                    page_number=page_num,
                )

                all_verdicts.append(page_result.overall)
                for check_result in page_result.results:
                    all_checks.append(check_result.to_dict())

            # MC-KOS-35: Apply evidence selection policy and validate
            from kosniper.evidence.select import apply_evidence_policy, validate_evidence_offset_basis

            # Validate offset_basis for all evidence with offsets (fail-closed)
            error = validate_evidence_offset_basis(all_checks)
            if error:
                print(f"Error: {error}", file=sys.stderr)
                return 2

            # Apply evidence policy (sort, dedupe, limit, truncate)
            all_checks = apply_evidence_policy(all_checks)

            # Aggregate overall verdict (worst across all pages)
            overall = worst_verdict(all_verdicts) if all_verdicts else TrafficLight.ABSTAIN

            # Generate summary
            if overall == TrafficLight.RED:
                summary = "Hard KO detected; disqualification likely."
            elif overall == TrafficLight.YELLOW:
                summary = "Possible KO signal detected; review evidence."
            elif overall == TrafficLight.ABSTAIN:
                summary = "Insufficient data to assess; manual review required."
            else:
                summary = "No KO signal detected."

            # MC-KOS-34: Build document_map for provenance
            document_map = {
                "doc_id": doc_id,
                "offset_basis": "normalized_text_v1",
                "pages": page_map_entries,
            }
            # Compute overall_sha256 from canonical JSON (sorted keys, no whitespace)
            map_json = json.dumps(document_map, sort_keys=True, separators=(",", ":"))
            document_map["overall_sha256"] = hashlib.sha256(map_json.encode("utf-8")).hexdigest()

            result = {
                "schema_version": "1.0",
                "verdict": overall.value,
                "overall_verdict": overall.value,
                "summary": summary,
                "checks": all_checks,
                "document_map": document_map,
            }
        else:
            result = ingest_result

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

        # MC-KOS-43: Write report pack to --out-dir (scan mode only)
        if args.out_dir is not None and args.scan:
            from kosniper.export.report_md import render_report

            try:
                os.makedirs(args.out_dir, exist_ok=True)

                # Write evidence_pack.json
                pack_path = os.path.join(args.out_dir, "evidence_pack.json")
                with open(pack_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                    f.write("\n")

                # Write report.md
                report_path = os.path.join(args.out_dir, "report.md")
                report_md = render_report(result)
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(report_md)

                # Write document_map.json if present
                doc_map = result.get("document_map")
                if doc_map:
                    map_path = os.path.join(args.out_dir, "document_map.json")
                    with open(map_path, "w", encoding="utf-8") as f:
                        json.dump(doc_map, f, indent=2, ensure_ascii=False)
                        f.write("\n")
            except OSError as e:
                print(f"Error writing report pack: {e}", file=sys.stderr)
                return 2

            if not args.quiet:
                print(f"[REPORT] Written to {args.out_dir}/", file=sys.stderr)

        if not args.quiet:
            if args.find is not None:
                match_count = len(result.get("matches", []))
                print(f"[FIND] '{args.find}' ({match_count} match(es))", file=sys.stderr)
            elif args.scan:
                overall = result.get("overall_verdict", "unknown")
                summary = result.get("summary", "")
                check_count = len(result.get("checks", []))
                print(f"[{overall.upper()}] {summary} ({check_count} check(s))", file=sys.stderr)
            else:
                page_count = len(result.get("pages", []))
                doc_id = result.get("doc_id", args.pdf)
                print(f"[INGEST] {doc_id} ({page_count} page(s))", file=sys.stderr)

        return 0

    # Validate required args for scanner mode
    if args.doc_id is None:
        print("Error: --doc-id is required for scanner mode", file=sys.stderr)
        return 2
    if args.page is None:
        print("Error: --page is required for scanner mode", file=sys.stderr)
        return 2
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

    # MC-KOS-35: Apply evidence selection policy and validate
    from kosniper.evidence.select import apply_evidence_policy, validate_evidence_offset_basis

    error = validate_evidence_offset_basis(checks)
    if error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    checks = apply_evidence_policy(checks)
    result["checks"] = checks

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

        # Print compact evidence lines for pretty mode
        if args.format == "pretty":
            for check in checks:
                check_id = check.get("check_id", "unknown")
                for ev in check.get("evidence", []):
                    snippet = ev.get("snippet", "")
                    # Truncate snippet for display
                    if len(snippet) > 60:
                        snippet = snippet[:57] + "..."
                    doc_id = ev.get("doc_id", "")
                    page = ev.get("page", "")
                    loc = f"{doc_id}:{page}" if doc_id and page else ""
                    print(f"  [{check_id}] \"{snippet}\" ({loc})", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
