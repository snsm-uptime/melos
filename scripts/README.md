# Scripts — Docker Compose Utilities

This directory contains shell scripts that manage the Docker Compose stack for the melos project. They provide a consistent, safe interface for starting, stopping, and restarting services.

## Quick Start

**Start the stack:**
```bash
./scripts/compose-up.sh
```

**Stop the stack:**
```bash
./scripts/compose-down.sh
```

**Restart the stack:**
```bash
./scripts/compose-restart.sh
```

---

## Commands

### `compose-up.sh` — Start the Stack

Starts the hot-reload Compose stack with automatic rebuilds.

**Usage:**
```bash
./scripts/compose-up.sh [-d|--detach] [-- docker-compose-up-args...]
```

**Flags:**
- `-d`, `--detach` — Run in background. Prints service URLs and returns immediately.
- `--help` — Show help text.
- `--` — Pass remaining arguments to `docker compose up`. Everything after `--` is forwarded as-is.

**Examples:**

Start in foreground (tails logs):
```bash
./scripts/compose-up.sh
# Output:
# UI  http://localhost:3000
# API http://localhost:8000
# Health: curl -sf http://localhost:8000/health && curl -sf http://localhost:3000/health
```

Start in background:
```bash
./scripts/compose-up.sh -d
# Services run in background, prints URLs
```

### `compose-down.sh` — Stop the Stack

Stops the Compose stack and removes containers.

**Usage:**
```bash
./scripts/compose-down.sh [--wipe] [-- docker-compose-down-args...]
```

**Flags:**
- `--wipe` — Remove named volumes (e.g., `ui_node_modules`). Note: Postgres data is stored in a bind mount, not a named volume — use `compose-wipe-db.sh` to reset the database.
- `--help` — Show help text.
- `--` — Pass remaining arguments to `docker compose down`.

**Examples:**

Stop and keep all data:
```bash
./scripts/compose-down.sh
```

Stop and remove named volumes (full clean):
```bash
./scripts/compose-down.sh --wipe
```

### `compose-wipe-db.sh` — Wipe the Database Clean

Deletes the Postgres data directory on the host so the next stack start reinitializes an empty database. Postgres data is stored in a bind mount at `${MELOS_DATA:-$HOME/melos}/pgdata` instead of named volumes. Use `compose-down.sh --wipe` to remove named volumes like `ui_node_modules`.

**Usage:**
```bash
./scripts/compose-wipe-db.sh [-y|--yes] [--no-up] [-d|--detach]
```

**Flags:**
- `-y`, `--yes` — Skip the confirmation prompt.
- `--no-up` — Leave the stack down after wiping (skip `compose-up.sh`).
- `-d`, `--detach` — Start the stack back up in the background.
- `--help` — Show help text.

**What it does:**
1. Stops the Compose stack (`docker compose down`).
2. Deletes the host Postgres data directory (`${MELOS_DATA:-$HOME/melos}/pgdata`).
3. Starts the stack back up (unless `--no-up`).

**Examples:**

Wipe and restart (foreground), with confirmation prompt:
```bash
./scripts/compose-wipe-db.sh
```

Wipe without prompting, restart in background:
```bash
./scripts/compose-wipe-db.sh -y -d
```

Wipe only, leave the stack down:
```bash
./scripts/compose-wipe-db.sh -y --no-up
```

### `compose-restart.sh` — Restart the Stack

Stops and starts the stack in one command, with consistent file selection.

**Usage:**
```bash
./scripts/compose-restart.sh [-d|--detach] [--wipe] [-- docker-compose-up-args...]
```

**Flags:**
- `-d`, `--detach` — Start in background.
- `--wipe` — Remove named volumes on the way down.
- `--help` — Show help text.

**Examples:**

Quick restart (foreground):
```bash
./scripts/compose-restart.sh
```

Restart with fresh volumes and run detached:
```bash
./scripts/compose-restart.sh --wipe -d
```

---

## How They Work

### File Selection

Each script automatically selects the right docker-compose files:

**Default (compose-up, compose-down, compose-restart):**
- `docker-compose.yml` — base production config
- `docker-compose.dev.yml` — development overrides (hot reload, debug env vars)

**Other overlays available (not used by default):**
- `docker-compose.prod.yml` — production hardening (restart policies, no host DB port, SESSION_COOKIE_SECURE)
- `docker-compose.test.yml` — pytest runner with ephemeral DB (used as: `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api`)
- `docker-compose.worktree.yml` — isolated project name and ports for parallel checkouts (requires `MELOS_DATA`, `COMPOSE_PROJECT_NAME`, `API_HOST_PORT`, `UI_HOST_PORT`, `DB_HOST_PORT`)
- `docker-compose.worktree-lite.yml` — lightweight variant (API + DB only, skip UI rebuild)

### Validation

Before running any command, the scripts verify:

1. **Docker is available:** `docker` command on PATH and daemon is reachable.
2. **Docker Compose v2 is available:** Uses the `docker compose` plugin (not standalone `docker-compose`).
3. **`.env` file exists:** Prevents accidental use of the default project name, which could hit the wrong stack.
4. **Required compose files exist:** Ensures `docker-compose.yml` and `docker-compose.dev.yml` are present.

If any check fails, the script exits with a clear error message.

### Configuration

The scripts read your `.env` file to determine service ports:

- `API_HOST_PORT` — API server port (default: 8000)
- `UI_HOST_PORT` — UI server port (default: 3000)

After starting the stack, it prints the URLs you can visit:
```
UI  http://localhost:3000
API http://localhost:8000
Health: curl -sf http://localhost:8000/health && curl -sf http://localhost:3000/health
```

---

## The Helper Library: `compose-lib.sh`

This file is sourced by all scripts and provides shared utility functions.

### Key Functions

**`compose_repo_root`** — Find the project root directory.

**`compose_env_get KEY .env`** — Safely extract a value from `.env` without eval-ing the entire file.

**`compose_files REPO_ROOT`** — Get the list of docker-compose files to use (with `-f` prefixes).

**`compose_run REPO_ROOT [args]`** — Execute `docker compose` with the correct file set.

**`compose_require_docker`** — Verify Docker and Docker Compose v2 are available.

**`compose_require_env REPO_ROOT`** — Verify `.env` file exists.

**`compose_require_files REPO_ROOT`** — Verify required compose files exist.

**`compose_print_urls REPO_ROOT`** — Print the UI and API service URLs.

---

## Common Workflows

### Fresh Start (Clean Slate)

```bash
./scripts/compose-down.sh --wipe
./scripts/compose-up.sh
```

### Quick Restart (Keep Data)

```bash
./scripts/compose-restart.sh
```

### Restart in Background

```bash
./scripts/compose-restart.sh -d
# Services rebuild and run in background
```

### Debug a Specific Service

```bash
./scripts/compose-up.sh
# Let it run, then in another terminal:
docker compose logs -f api
docker compose exec api bash
```

---

## Troubleshooting

**Error: `missing .env — copy .env.example first`**
```bash
cp .env.example .env
```

**Error: `docker daemon not reachable`**
```bash
# Start Docker Desktop:
open /Applications/Docker.app
# or on Linux: sudo systemctl start docker
```

**Error: `Docker Compose v2 plugin not available`**
Update Docker Desktop or install the compose plugin.

**Containers keep restarting**
```bash
# Check logs:
docker compose logs -f

# Restart with fresh volumes:
./scripts/compose-restart.sh --wipe -d
```

**Port already in use (e.g., 8000 or 3000)**
```bash
# Override in .env:
echo "API_HOST_PORT=9000" >> .env
./scripts/compose-up.sh -d
```

---

## Script Maintenance

All entry-point scripts source `compose-lib.sh`. When adding logic:

- **Shared behavior** (repo root detection, env parsing, validation) → add to `compose-lib.sh`
- **Command-specific behavior** (up flags, down flags) → modify the individual script
- **New commands** → create a new script and source `compose-lib.sh` at the top
