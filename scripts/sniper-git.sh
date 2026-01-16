#!/usr/bin/env bash
set -euo pipefail
die(){ echo "ERROR: $*" >&2; exit 1; }

need_clean(){
  if ! git diff --quiet || ! git diff --cached --quiet; then
    die "Working tree not clean. Commit/stash first."
  fi
}

sync_main(){
  git fetch origin
  git checkout main >/dev/null 2>&1 || die "No main branch"
  git pull --ff-only origin main
}

new_branch(){
  local mc="${1:?mc required (e.g. mc-kos-12)}"
  local slug="${2:?slug required (e.g. evidence-pack-v1)}"
  need_clean
  sync_main
  git checkout -b "feature/${mc}-${slug}"
  git status -sb
}

pr_link(){
  local b
  b="$(git branch --show-current)"
  git push -u origin HEAD >/dev/null
  echo "https://github.com/moe-eid-ml/p1-faq-rag/pull/new/${b}"
}

case "${1:-}" in
  sync) sync_main ;;
  new)  new_branch "${2:-}" "${3:-}" ;;
  pr)   pr_link ;;
  *) echo "Usage: scripts/sniper-git.sh {sync|new <mc> <slug>|pr}" ;;
esac
