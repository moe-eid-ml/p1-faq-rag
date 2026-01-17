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
  local origin_url
  local repo
  b="$(git branch --show-current)"
  origin_url="$(git remote get-url origin)"
  if [[ "${origin_url}" == git@*:* ]]; then
    repo="${origin_url#git@}"
    repo="${repo#*:}"
  else
    repo="${origin_url#https://github.com/}"
    repo="${repo#http://github.com/}"
  fi
  repo="${repo%.git}"
  git push -u origin HEAD >/dev/null
  echo "https://github.com/${repo}/pull/new/${b}"
}

case "${1:-}" in
  sync) sync_main ;;
  new)  new_branch "${2:-}" "${3:-}" ;;
  pr)   pr_link ;;
  *) echo "Usage: scripts/sniper-git.sh {sync|new <mc> <slug>|pr}" ;;
esac
