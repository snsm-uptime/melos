# How to Develop (Local)

## Prerequisites

- Docker with Compose v2
- Node 18+ and `npm`
- Python 3.10+ (for API development)

## First-Time Setup

```bash
git clone <repo-url> melos
cd melos

# Copy the environment file and fill in secrets
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD, GEMINI_API_KEY, SESSION_SECRET, etc.

# Create the data directory for Postgres
mkdir -p "${MELOS_DATA:-$HOME/melos}/pgdata"

# Install dependencies (optional if using Docker for everything)
cd api && uv sync --group dev && cd ..
cd ui && npm install && cd ..
```

## Starting the Development Stack

The melos project uses Docker Compose with a development overlay for hot-reload code changes.

### Quick Start

```bash
# Start all services (database, API, UI) in foreground with logs
./scripts/compose-up.sh

# Or start in background
./scripts/compose-up.sh -d
```

### Service URLs

After the stack starts, you'll see:

```
UI  http://localhost:3000
API http://localhost:8000
```

**Health checks:**
```bash
curl -sf http://localhost:8000/health  # API
curl -sf http://localhost:3000/health  # UI
```

## Development Workflows

### Stop the Stack

```bash
./scripts/compose-down.sh
```

### Restart the Stack (Keep Data)

```bash
./scripts/compose-restart.sh
```

### Restart with Fresh Database

```bash
./scripts/compose-restart.sh --wipe -d
```

### Clean Database Only

If you want to keep containers running but reset the database:

```bash
./scripts/compose-wipe-db.sh -y -d
```

### Logs

While the stack is running:

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f ui
docker compose logs -f db

# Follow API logs with timestamps
docker compose logs -f --timestamps api
```

### Interactive Shell in a Container

```bash
# API Python shell
docker compose exec api bash

# UI Node shell
docker compose exec ui bash

# Database
docker compose exec db psql -U melos -d melos
```

## How the Docker Compose Setup Works

### Files

- **`docker-compose.yml`** — Base configuration (dev + prod)
  - Services: `db` (PostgreSQL 16 with pgvector), `api`, `ui`
  - Default ports: 5432 (db), 8000 (api), 3000 (ui)
  - Data bound to host at `${MELOS_DATA:-$HOME/melos}/pgdata`
  - Credentials from `.env` variables

- **`docker-compose.dev.yml`** — Development overlay
  - Adds hot-reload for code changes
  - Bind-mounts source code for live editing
  - Sets dev-mode environment variables (DEV_RELOAD, LOG_LEVEL=DEBUG)
  - Volume: `ui_node_modules` (prevents conflicts between host and container npm)

- **`docker-compose.{prod,test,worktree,worktree-lite}.yml`** — Optional overlays
  - `prod`: Production hardening (restart policies, no host DB port)
  - `test`: Ephemeral database for pytest
  - `worktree`: Isolated ports and project name for parallel checkouts
  - `worktree-lite`: API + DB only (skip UI rebuild)

### Helper Scripts

All scripts are in `scripts/`:

- **`compose-up.sh [-d]`** — Start the stack
- **`compose-down.sh [--wipe]`** — Stop the stack
- **`compose-restart.sh [-d] [--wipe]`** — Stop and restart
- **`compose-wipe-db.sh [-y] [-d]`** — Reset database volumes

See `scripts/README.md` for detailed documentation.

### Configuration

The `.env` file controls key settings:

```bash
API_HOST_PORT=8000          # API port on your machine
UI_HOST_PORT=3000           # UI port on your machine
SEED_DEV_DATA=1             # Seed dev data on API start (0 to disable)
```

## Code Changes and Hot Reload

### API (Python/FastAPI)

The API runs with `--reload` in dev mode. When you save a `.py` file:

1. The file is bind-mounted into the container
2. Uvicorn detects the change and restarts the process
3. Refresh your browser to see the change

**Note:** Some changes (like model definitions or imports) may require a manual restart:

```bash
./scripts/compose-restart.sh -d
```

### UI (Next.js)

The UI runs Next.js dev server with hot module reload. When you save:

1. The file is bind-mounted into the container
2. Next.js rebuilds that route/component
3. Your browser hot-reloads (usually automatically)

**Polling mode:** Both API and UI use polling for file watching (works better with Docker mount caching).

## Database

### PostgreSQL with pgvector

A single PostgreSQL 16 instance with the `pgvector` extension for vector embeddings. Recipes and embeddings both live in the same database.

- **Service:** `db` (in compose)
- **Host:** `db` (from inside containers) or `localhost` (from your machine)
- **Port:** 5432
- **Username:** `POSTGRES_USER` from `.env` (default: `melos`)
- **Password:** `POSTGRES_PASSWORD` from `.env`
- **Database:** `POSTGRES_DB` from `.env` (default: `melos`)
- **Data location:** `${MELOS_DATA:-$HOME/melos}/pgdata` (host bind mount)

Connect from your machine:
```bash
psql -U melos -h localhost -d melos -c "SELECT * FROM recipes LIMIT 1;"
```

From inside a container:
```bash
docker compose exec db psql -U melos -d melos -c "SELECT * FROM recipes LIMIT 1;"
```

### Migrations

When you change the schema, use Alembic:

```bash
# Generate a migration based on model changes
docker compose exec api alembic revision --autogenerate -m "Description"

# Review and edit the migration file in api/src/adapters/persistence/migrations/versions/

# Apply the migration
docker compose exec api alembic upgrade head
```

Or restart the stack to auto-apply pending migrations:
```bash
./scripts/compose-restart.sh -d
```

## Environment Variables

### `.env` File

Copy `.env.example` to `.env` and customize:

```bash
# Data directory (outside the repo)
MELOS_DATA=${HOME}/melos

# Database
POSTGRES_USER=melos
POSTGRES_PASSWORD=<secure-password>  # Set to a secure value, never commit to git
POSTGRES_DB=melos

# Other services (Gemini, SMTP, etc.)
# See .env.example for the full list
```

### API Environment (Development)

Inside the container, the API has:

```
DEV_RELOAD=true            # Enable auto-reload on file changes
LOG_LEVEL=DEBUG            # Verbose logging
SEED_DEV_DATA=1            # Seed test data (from .env)
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
```

## Testing

### API Tests

```bash
docker compose exec api pytest
docker compose exec api pytest tests/test_api.py -v
```

### UI Tests

```bash
docker compose exec ui npm test
docker compose exec ui npm run test:e2e
```

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8000 or 3000
lsof -i :8000
lsof -i :3000

# Override in .env
echo "API_HOST_PORT=9000" >> .env
./scripts/compose-restart.sh -d
```

### Docker Daemon Not Reachable

```bash
# macOS
open /Applications/Docker.app

# Linux
sudo systemctl start docker
```

### Container Won't Start

```bash
# Check logs
docker compose logs api
docker compose logs ui
docker compose logs postgres

# Rebuild without cache
./scripts/compose-restart.sh --wipe -d
```

### Database Connection Refused

```bash
# Ensure db is healthy
docker compose exec db pg_isready -U melos

# Reset database
./scripts/compose-wipe-db.sh -y -d
```

### Code Changes Not Reflecting

1. **API:** Check that Uvicorn reloaded:
   ```bash
   docker compose logs api | grep -i reload
   ```

2. **UI:** Hard refresh your browser (Cmd+Shift+R on macOS)

3. **Still stuck:** Restart the services:
   ```bash
   ./scripts/compose-restart.sh -d
   ```

## Performance Tips

1. **Use `--detach` for background runs:**
   ```bash
   ./scripts/compose-up.sh -d
   ```

2. **Build images once, then reuse:**
   ```bash
   docker compose build    # One-time build
   docker compose up -d    # Quick start afterward
   ```

3. **Limit logs output:**
   ```bash
   docker compose logs --tail=100 -f api
   ```

4. **Check resource usage:**
   ```bash
   docker stats
   ```

## Next Steps

- See `scripts/README.md` for advanced script usage
- Check `dev/docs/prd.md` for product requirements
- Review API structure in `api/` and UI structure in `ui/`
