#!/usr/bin/env bash
# MC-KOS-19: One-command demo runner for KOSniper
# Runs CLI on sample, writes evidence_pack.json, prints summary.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

python -m kosniper.cli \
    --doc-id sample.pdf \
    --page 1 \
    --text-file samples/tender_ko_phrase.txt \
    --out evidence_pack.json

echo "Written: evidence_pack.json"
