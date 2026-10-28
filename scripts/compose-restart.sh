#!/usr/bin/env bash
# Restart the Compose stack (down then up) with a consistent -f set.
# Usage: ./scripts/compose-restart.sh [-d|--detach] [--wipe [-y|--yes]] [--] [extra up args...]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DETACH=0
WIPE=0
YES=0
EXTRA=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -d|--detach) DETACH=1; shift ;;
    --wipe) WIPE=1; shift ;;
    -y|--yes) YES=1; shift ;;
    --) shift; EXTRA+=("$@"); break ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/compose-restart.sh [-d|--detach] [--wipe [-y|--yes]] [-- docker-compose-up-args...]

Runs compose-down then compose-up with the same checkout Compose file set.

--wipe (destructive) starts from scratch: it deletes the Postgres data
directory (MELOS_DATA/pgdata, via compose-wipe-db.sh) and removes the named
Compose volumes (e.g. ui_node_modules). Postgres comes up empty, migrations
run and the dev seed (SEED_DEV_USER=1) recreates its users and kitchens.
It asks for confirmation first; -y/--yes skips the prompt. Only this
checkout's pgdata is touched. Prefer a plain restart otherwise.
EOF
      exit 0
      ;;
    *) EXTRA+=("$1"); shift ;;
  esac
done

UP_FLAGS=()
[[ "$DETACH" == "1" ]] && UP_FLAGS+=(-d)

if [[ "$WIPE" == "1" ]]; then
  # Database first: it confirms, stops the stack and deletes pgdata (and stays down), so a
  # "no" answer aborts before anything else is removed. Then the named volumes go.
  WIPE_DB_FLAGS=(--no-up)
  [[ "$YES" == "1" ]] && WIPE_DB_FLAGS+=(--yes)
  "$SCRIPT_DIR/compose-wipe-db.sh" "${WIPE_DB_FLAGS[@]}"
  PGDATA_WIPED=1 "$SCRIPT_DIR/compose-down.sh" --wipe
else
  "$SCRIPT_DIR/compose-down.sh"
fi
"$SCRIPT_DIR/compose-up.sh" "${UP_FLAGS[@]+"${UP_FLAGS[@]}"}" "${EXTRA[@]+"${EXTRA[@]}"}"
