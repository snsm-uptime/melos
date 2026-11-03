#!/usr/bin/env bash
# Make this Claude Code worktree ready to work in: dependencies, its own .env, ports and data dir.
# Runs from the SessionStart hook in .claude/settings.json. Does nothing in the primary checkout
# or in a worktree that is already set up. It does not start Docker.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
GIT_DIR="$(git rev-parse --path-format=absolute --git-dir)"
COMMON_DIR="$(git rev-parse --path-format=absolute --git-common-dir)"
[[ "$GIT_DIR" != "$COMMON_DIR" ]] || exit 0

MARKER_BEGIN="# --- worktree overrides (generated) ---"
MARKER_END="# --- end worktree overrides ---"
grep -qsF "worktree overrides (generated)" "$ROOT/.env" && exit 0

PRIMARY="$(dirname "$COMMON_DIR")"
if [[ ! -f "$PRIMARY/.env" ]]; then
  echo "worktree: no .env in $PRIMARY, so this worktree was not set up" >&2
  exit 0
fi

# Dependencies first: .env is what marks the worktree as done, so a failure here runs again.
(cd "$ROOT/api" && uv sync --group dev --quiet)
(cd "$ROOT/ui" && npm ci --silent >/dev/null)

SLUG="$(basename "$ROOT" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')"
NAME="$(printf 'melos-%s' "$SLUG" | cut -c1-50)"
DATA="$HOME/melos-wt/$NAME"

# One offset per worktree path, 1..40. The ranges below do not overlap.
OFFSET=$(( $(printf '%s' "$ROOT" | cksum | awk '{print $1}') % 40 + 1 ))

mkdir -p "$DATA/pgdata" "$DATA/pdfs"
# The api runs as a non-root user with no chown on start.
chmod 777 "$DATA/pdfs"

KEYS='MELOS_COMPOSE_NAME|API_HOST_PORT|UI_HOST_PORT|MCP_HOST_PORT|DEBUG_PORT|UI_DEBUG_PORT|UI_DEBUG_WORKER_PORT|MELOS_DATA|PUBLIC_APP_URL'
TMP="$(mktemp "$ROOT/.env.XXXXXX")"
{
  grep -vE "^($KEYS)=" "$PRIMARY/.env" || true
  echo
  echo "$MARKER_BEGIN"
  echo "MELOS_COMPOSE_NAME=$NAME"
  echo "API_HOST_PORT=$((8000 + OFFSET * 10))"
  echo "UI_HOST_PORT=$((3000 + OFFSET * 10))"
  echo "MCP_HOST_PORT=$((9400 + OFFSET * 10))"
  echo "DEBUG_PORT=$((5700 + OFFSET))"
  echo "UI_DEBUG_PORT=$((9200 + OFFSET * 2))"
  # Next.js needs this to be UI_DEBUG_PORT + 1.
  echo "UI_DEBUG_WORKER_PORT=$((9201 + OFFSET * 2))"
  echo "MELOS_DATA=$DATA"
  echo "PUBLIC_APP_URL=http://localhost:$((3000 + OFFSET * 10))"
  echo "$MARKER_END"
} >"$TMP"
chmod 600 "$TMP"
mv "$TMP" "$ROOT/.env"

echo "Worktree ready: project $NAME, UI on port $((3000 + OFFSET * 10)). Start it with ./scripts/compose-up.sh -d"
