# How to Develop (Local)

## Prerequisites

- Docker with Compose v2
- Node 18+ and `npm`
- Python 3.10+ (for API development)

## First-Time Setup

```bash
git clone <repo-url> melos
cd melos

# Copy the environment file
cp .env.example .env

# Install dependencies (optional if using Docker for everything)
cd api && pip install -r requirements.txt && cd ..
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
docker compose logs -f postgres

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
docker compose exec postgres psql -U melos -d melos_db
```

## How the Docker Compose Setup Works

### Files

- **`docker-compose.yml`** — Production configuration (base)
  - Services: postgres, pgvector, api, ui
  - Default ports: 5432 (db), 8000 (api), 3000 (ui)
  - Uses production builds and read-only volumes

- **`docker-compose.dev.yml`** — Development overlay
  - Adds hot-reload for code changes
  - Bind-mounts source code for live editing
  - Sets dev-mode environment variables (DEV_RELOAD, LOG_LEVEL=DEBUG)
  - Volume: `ui_node_modules` (prevents conflicts between host and container npm)

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

### PostgreSQL

- **Host:** localhost (from your machine) or `postgres` (from inside containers)
- **Port:** 5432
- **Username:** `melos`
- **Password:** `melos_dev_password` (from `.env`)
- **Database:** `melos_db`

### pgvector (Optional)

A second Postgres instance with the `pgvector` extension for vector embeddings.

- **Port:** 5433
- **Same credentials as main postgres**

Connect to it: `psql -U melos -h localhost -p 5433 -d melos_db`

### Migrations

When you change the schema:

1. **If using Alembic (Flask-style):**
   ```bash
   docker compose exec api alembic revision --autogenerate -m "Description"
   docker compose exec api alembic upgrade head
   ```

2. **Restart the stack** to ensure the database schema is up to date:
   ```bash
   ./scripts/compose-restart.sh -d
   ```

## Environment Variables

### `.env` File

Copy `.env.example` to `.env` and customize:

```bash
# Ports
API_HOST_PORT=8000
UI_HOST_PORT=3000

# Development
SEED_DEV_DATA=1            # Auto-seed test data when API starts (set to 0 to disable)

# Database (set in docker-compose.yml)
POSTGRES_USER=melos
POSTGRES_PASSWORD=melos_dev_password
POSTGRES_DB=melos_db
```

### API Environment (Development)

Inside the container, the API has:

```
DEV_RELOAD=true            # Enable auto-reload on file changes
LOG_LEVEL=DEBUG            # Verbose logging
SEED_DEV_DATA=1            # Seed test data (from .env)
DATABASE_URL=postgresql://melos:melos_dev_password@postgres:5432/melos_db
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
# Ensure postgres is healthy
docker compose exec postgres pg_isready -U melos

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
