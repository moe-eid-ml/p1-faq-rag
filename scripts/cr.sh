#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-origin/main}"
coderabbit review --plain --type all --base "$BASE" -c coderabbit.md
