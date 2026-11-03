#!/usr/bin/env bash
# Finish a Claude Code worktree: stop its stack, delete its data, remove it and its merged branch.
# Run from the primary checkout: ./scripts/worktree/worktree-done.sh <slug>
# Refuses a worktree with uncommitted work. An unmerged branch is kept.
set -euo pipefail

if [[ $# -ne 1 || "$1" == "-h" || "$1" == "--help" ]]; then
  echo "Usage: ./scripts/worktree/worktree-done.sh <slug>" >&2
  exit 1
fi

SLUG="$1"
if [[ ! "$SLUG" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "error: slug must match [A-Za-z0-9._-]+ (got: $SLUG)" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../compose-lib.sh
source "$SCRIPT_DIR/../compose-lib.sh"

PRIMARY="$(cd "$SCRIPT_DIR/../.." && pwd)"
WORKTREE="$PRIMARY/.claude/worktrees/$SLUG"
if [[ ! -d "$WORKTREE" ]]; then
  echo "error: no worktree at $WORKTREE" >&2
  exit 1
fi

if [[ -n "$(git -C "$WORKTREE" status --porcelain)" ]]; then
  echo "error: $WORKTREE has uncommitted work. Commit it or discard it first." >&2
  exit 1
fi

# Every refusal comes before anything is stopped or deleted.
if git -C "$PRIMARY" worktree list --porcelain |
  awk -v path="worktree $WORKTREE" 'BEGIN { RS = "" } index($0, path "\n") == 1 && /\nlocked/ { found = 1 } END { exit !found }'; then
  echo "error: $WORKTREE is locked by a running Claude session. Exit it first." >&2
  exit 1
fi

BRANCH="$(git -C "$WORKTREE" rev-parse --abbrev-ref HEAD)"

if [[ -f "$WORKTREE/.env" ]]; then
  compose_require_docker
  compose_require_env "$WORKTREE"
  DATA="$(compose_data_root "$WORKTREE")"
  echo "==> Stopping the stack"
  COMPOSE_ROOT="$WORKTREE" bash "$SCRIPT_DIR/../compose-down.sh" --wipe
  if [[ "$DATA" == "$HOME/melos-wt/"* && -d "$DATA" ]]; then
    echo "==> Deleting $DATA"
    # Postgres owns pgdata, so the delete runs as root in a container.
    docker run --rm -v "$DATA:/data" pgvector/pgvector:pg16 sh -c 'rm -rf /data/* /data/.[!.]*'
    rmdir "$DATA"
  else
    echo "!!  Keeping $DATA: it is not under ~/melos-wt/"
  fi
fi

echo "==> Removing $WORKTREE"
git -C "$PRIMARY" worktree remove "$WORKTREE"

if ! git -C "$PRIMARY" branch -d "$BRANCH"; then
  echo "!!  Kept branch $BRANCH: it is not merged."
fi
