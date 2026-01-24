#!/usr/bin/env bash
# MC-KOS-49: Demo script for KOSniper scan + verify workflow.
#
# Usage: demo_pack.sh <PDF_PATH> [--out-dir DIR] [--dry-run]
#
# Runs:
#   1) kosniper --pdf <PDF> --scan --out-dir <DIR>
#   2) kosniper --verify-pack --in-dir <DIR> --receipt
#
# Fail-closed: any step failure exits non-zero.

set -euo pipefail

# Defaults
OUT_DIR=""
DRY_RUN=false
PDF_PATH=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --out-dir)
            if [[ -z "${2:-}" || "$2" == -* ]]; then
                echo "Error: --out-dir requires a value" >&2
                exit 2
            fi
            OUT_DIR="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -* )
            echo "Error: Unknown option: $1" >&2
            exit 2
            ;;
        *)
            if [[ -z "$PDF_PATH" ]]; then
                PDF_PATH="$1"
                shift
            else
                echo "Error: Multiple PDF paths provided" >&2
                exit 2
            fi
            ;;
    esac
done

# Validate PDF path provided
if [[ -z "$PDF_PATH" ]]; then
    echo "Usage: demo_pack.sh <PDF_PATH> [--out-dir DIR] [--dry-run]" >&2
    exit 2
fi

# Validate PDF exists (unless dry-run)
if [[ "$DRY_RUN" == false ]] && [[ ! -f "$PDF_PATH" ]]; then
    echo "Error: PDF not found: $PDF_PATH" >&2
    exit 2
fi

# Set default out dir with timestamp to avoid collisions
if [[ -z "$OUT_DIR" ]]; then
    OUT_DIR="/tmp/kos_out_$(date +%Y%m%d_%H%M%S)"
fi

# Determine command: prefer `kosniper` if available, else fallback
if command -v kosniper >/dev/null 2>&1; then
    CMD=(kosniper)
else
    CMD=(python -m kosniper.cli)
fi

# Dry-run mode: print commands and exit
if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] Would run:"
    echo "  ${CMD[*]} --pdf \"$PDF_PATH\" --scan --out-dir \"$OUT_DIR\""
    echo "  ${CMD[*]} --verify-pack --in-dir \"$OUT_DIR\" --receipt"
    echo "[dry-run] Output dir: $OUT_DIR"
    exit 0
fi

# Execute scan
"${CMD[@]}" --pdf "$PDF_PATH" --scan --out-dir "$OUT_DIR"

# Execute verify with receipt
"${CMD[@]}" --verify-pack --in-dir "$OUT_DIR" --receipt

# Success
echo "Done. Output dir: $OUT_DIR"
