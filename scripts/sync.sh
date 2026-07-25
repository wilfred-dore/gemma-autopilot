#!/usr/bin/env bash
# Two-way sync with the Brev H100 box.
# Source of truth for CODE = this local repo. Source of truth for RUN DATA = the box.
#   ./scripts/sync.sh push   -> code to the box (excludes .git, .venv, runs)
#   ./scripts/sync.sh pull   -> run data (journal, state, logs) back to the Mac
set -euo pipefail
HOST="${AUTOPILOT_HOST:-domestic-crimson-felidae}"
REMOTE_DIR="/ephemeral/gemma-autopilot"

case "${1:-}" in
  push)
    rsync -az --delete \
      --exclude '.git' --exclude '.venv' --exclude '__pycache__' \
      --exclude 'runs/*.json' --exclude 'runs/*.jsonl' \
      ./ "$HOST:$REMOTE_DIR/"
    echo "pushed -> $HOST:$REMOTE_DIR"
    ;;
  pull)
    mkdir -p runs/backup
    rsync -az "$HOST:$REMOTE_DIR/runs/" runs/backup/ || true
    rsync -az "$HOST:/ephemeral/download.log" runs/backup/ 2>/dev/null || true
    echo "pulled run data -> runs/backup/"
    ;;
  *)
    echo "usage: $0 push|pull" >&2
    exit 1
    ;;
esac
