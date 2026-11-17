#!/usr/bin/env bash
# Create the GitHub repo for SidAgent and push. Run AFTER: gh auth login
# Usage: ./scripts/push_to_github.sh [--public]   (default: --private)
set -euo pipefail
cd "$(dirname "$0")/.."

VISIBILITY="--private"
if [[ "${1:-}" == "--public" ]]; then VISIBILITY="--public"; fi

if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI is not logged in. Run: gh auth login   (see docs/GOING_LIVE.md)"
  exit 1
fi

if git remote get-url origin >/dev/null 2>&1; then
  echo "Remote 'origin' already exists - pushing."
  git push -u origin main
else
  gh repo create sid-agent --source=. --remote=origin "$VISIBILITY" --push \
    --description "SidAgent - a personal AI agent that does things: tasks, internship applications, live course lookups. Provider-flexible LLM, eval-tested."
fi
echo "Done."
