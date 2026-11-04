#!/bin/sh
# Named volume ui_node_modules survives image rebuilds. Re-run npm ci when the
# bind-mounted lockfile no longer matches what is installed in that volume.
#
# Starts as root, then runs the app as the host user who owns the bind-mounted
# source (read from package.json). Otherwise `next dev` writes ./ui/.next on the
# host as root, and removing the worktree later fails.
set -e
cd /app
if [ -f package-lock.json ]; then
  lock_hash="$(sha256sum package-lock.json | awk '{print $1}')"
  stamp="node_modules/.package-lock-hash"
  if [ ! -f "$stamp" ] || [ "$(cat "$stamp")" != "$lock_hash" ]; then
    echo "ui: installing dependencies from package-lock.json"
    npm ci
    mkdir -p node_modules
    printf '%s\n' "$lock_hash" > "$stamp"
  fi
fi

if [ "$(id -u)" = "0" ]; then
  host_uid="$(stat -c %u package.json)"
  host_gid="$(stat -c %g package.json)"
  if [ "$host_uid" != "0" ]; then
    mkdir -p .next
    # Chown only paths still owned by someone else: a full recursive chown of
    # node_modules on every start would be slow.
    for p in node_modules .next next-env.d.ts; do
      [ -e "$p" ] || continue
      find "$p" \( ! -user "$host_uid" -o ! -group "$host_gid" \) \
        -exec chown -h "$host_uid:$host_gid" {} +
    done
    export HOME=/tmp  # npm/next caches; the host uid may have no home here
    exec setpriv --reuid="$host_uid" --regid="$host_gid" --clear-groups "$@"
  fi
fi
exec "$@"
