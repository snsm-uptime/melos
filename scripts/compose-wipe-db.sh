#!/usr/bin/env bash
# Wipe the Postgres data for this checkout's Compose stack (destructive).
# Postgres data is stored in a bind mount at MELOS_DATA/pgdata on the host.
# This script stops the stack and deletes that directory, so Postgres reinitializes from scratch.
# Usage: ./scripts/compose-wipe-db.sh [-y|--yes] [--no-up] [-d|--detach]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=compose-lib.sh
source "$SCRIPT_DIR/compose-lib.sh"

ROOT="$(compose_repo_root)"
YES=0
NO_UP=0
DETACH=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes) YES=1; shift ;;
    --no-up) NO_UP=1; shift ;;
    -d|--detach) DETACH=1; shift ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/compose-wipe-db.sh [-y|--yes] [--no-up] [-d|--detach]

Stops this checkout's Compose stack and deletes the Postgres data directory
(${MELOS_DATA:-$HOME/melos}/pgdata) on the host so Postgres reinitializes empty.

Note: --wipe on compose-down.sh removes named volumes (ui_node_modules).
Use this script to reset just the database.

-y, --yes    Skip the confirmation prompt.
--no-up      Leave the stack down after wiping (skip compose-up.sh).
-d, --detach Start the stack back up in the background.
--help       Show this help text.
EOF
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

compose_require_docker
compose_require_env "$ROOT"

MELOS_DATA="$(compose_env_get MELOS_DATA "$ROOT/.env")"
MELOS_DATA="${MELOS_DATA:-${HOME}/melos}"
PGDATA_PATH="${MELOS_DATA}/pgdata"

echo "==> This will DELETE all Postgres data at: $PGDATA_PATH"
if [[ "$YES" != "1" ]]; then
  read -r -p "Type 'yes' to continue: " CONFIRM
  if [[ "$CONFIRM" != "yes" ]]; then
    echo "Aborted."
    exit 1
  fi
fi

echo "==> Stopping stack in $ROOT"
compose_run "$ROOT" down

if [[ -d "$PGDATA_PATH" ]]; then
  echo "==> Removing Postgres data at $PGDATA_PATH"
  rm -rf "$PGDATA_PATH"
else
  echo "==> Postgres data directory not found at $PGDATA_PATH (already clean)"
fi

if [[ "$NO_UP" == "1" ]]; then
  echo "Done. Stack left down (--no-up). Run ./scripts/compose-up.sh when ready."
  exit 0
fi

UP_ARGS=()
[[ "$DETACH" == "1" ]] && UP_ARGS+=(-d)
"$SCRIPT_DIR/compose-up.sh" "${UP_ARGS[@]+"${UP_ARGS[@]}"}"
