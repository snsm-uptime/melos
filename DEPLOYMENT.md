# Production Deployment Guide

**Melos Bootstrap** — Docker Compose on a single server with reverse proxy (nginx, Caddy, or Apache) terminating TLS outside the repo.

## Deployment Model

Melos runs as a multi-service Docker Compose stack on the operator's server:

```
┌─────────────────────────────┐
│ Internet                    │
└──────────────┬──────────────┘
               │ HTTPS (TLS)
┌──────────────▼──────────────┐
│ Reverse Proxy (nginx/Caddy) │ ← outside repo
├─────────────────────────────┤
│ api:8000    ui:3000         │ ← HTTP (localhost only)
│ mcp:9000    db:5432         │
└─────────────────────────────┘
```

- **TLS termination** is managed **outside the repository** (by the reverse proxy)
- **API, UI, and MCP** listen on `localhost` (Docker bridge) only
- **PostgreSQL** uses a dedicated volume at `${MELOS_DATA}/pgdata` (outside the container)
- **No secrets** are stored in the repo; they live in `.env` on the operator's server only

## Prerequisites

1. **Docker & Docker Compose**
   - Docker Engine 20.10+ with Compose v2 support
   - Verify: `docker compose version`

2. **System Resources**
   - CPU: 2+ cores
   - RAM: 2GB+ (for PostgreSQL, API, UI, MCP)
   - Disk: 20GB+ for `${MELOS_DATA}`

3. **Reverse Proxy** (outside repo)
   - nginx, Caddy, or Apache configured for HTTPS/TLS
   - Routes traffic to `http://localhost:3000` (UI) and `http://localhost:8000` (API)
   - Manages SSL certificates (Let's Encrypt recommended)

4. **Environment**
   - PostgreSQL 16+ (provided by Docker image `pgvector/pgvector:pg16`)
   - SMTP relay for transactional email (Gmail, AWS SES, SendGrid, etc.)

## Server Setup

### 1. Clone or Deploy the Repository

```bash
# Clone the repository on the production server
git clone https://github.com/your-org/melos.git /opt/melos
cd /opt/melos

# Check out the release branch/tag
git checkout main  # or a tagged release
```

### 2. Create Data and Config Directories

```bash
# Create data directory outside the repo
mkdir -p /var/melos/pgdata /var/melos/pdfs
chown 999:999 /var/melos/pgdata  # postgres user in the container
chmod 700 /var/melos/pgdata
```

### 3. Populate `.env` File

**DO NOT copy `.env.example` directly.** Instead, create `.env` with your production values:

```bash
cp .env.example .env
# Edit .env with a secure editor (never commit it)
nano .env
```

**Critical Production Settings:**

```env
# Data directory (outside repo)
MELOS_DATA=/var/melos

# PostgreSQL
POSTGRES_USER=melos
POSTGRES_PASSWORD=$(openssl rand -base64 32)  # Generate a secure password
POSTGRES_DB=melos

# Session & Security
SESSION_SECRET=$(openssl rand -base64 32)     # Generate a secure secret
SESSION_COOKIE_SECURE=true                    # HTTPS only in prod
SESSION_COOKIE_SAMESITE=strict               # Strict in prod

# Public URL (for email links, password reset, invites)
PUBLIC_APP_URL=https://melos.example.com

# Gemini API (if using AI features)
GEMINI_API_KEY=<your-actual-api-key>
GEMINI_CHAT_MODEL=gemini-2.0-flash
GEMINI_EMBED_MODEL=text-embedding-004
GEMINI_EMBED_DIM=768

# SMTP (required for password reset, email verification, invites)
SMTP_HOST=<your-smtp-provider>
SMTP_PORT=587
SMTP_USER=<your-smtp-username>
SMTP_PASSWORD=<your-smtp-password>
SMTP_FROM=Melos <noreply@melos.example.com>
SMTP_STARTTLS=true

# Auth Rate Limits
AUTH_RATE_LIMIT_REGISTER_MAX=5
AUTH_RATE_LIMIT_REGISTER_WINDOW_SECONDS=3600
AUTH_RATE_LIMIT_SIGN_IN_MAX=20
AUTH_RATE_LIMIT_SIGN_IN_WINDOW_SECONDS=900

# Trusted Proxies (reverse proxy CIDR)
TRUSTED_PROXY_IPS=<reverse-proxy-ip>,127.0.0.1,::1

# Disable dev seed in production
SEED_DEV_USER=0
```

**Secure Password Generation:**
```bash
# Use one of these to generate strong secrets:
openssl rand -base64 32
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Configure Reverse Proxy

Set up your reverse proxy (nginx, Caddy, or Apache) to:

1. **Listen on port 443 (HTTPS)** with your TLS certificate
2. **Route `/` to `http://localhost:3000`** (Next.js UI)
3. **Route `/api/` to `http://localhost:8000`** (FastAPI backend)
4. **Set `X-Melos-Client-IP` header** from the client's real IP

**Example nginx Configuration:**

```nginx
upstream melos_ui {
    server localhost:3000;
}

upstream melos_api {
    server localhost:8000;
}

server {
    listen 443 ssl http2;
    server_name melos.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Redirect HTTP to HTTPS
    error_page 497 =301 https://$host$request_uri;

    # Logging
    access_log /var/log/nginx/melos_access.log;
    error_log /var/log/nginx/melos_error.log;

    # UI (default)
    location / {
        proxy_pass http://melos_ui;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # For rate limiting on auth endpoints
        proxy_set_header X-Melos-Client-IP $remote_addr;
    }

    # API proxy
    location /api/ {
        proxy_pass http://melos_api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Melos-Client-IP $remote_addr;
        
        # For file uploads
        client_max_body_size 50M;
    }
}
```

### 5. Start the Docker Compose Stack

```bash
cd /opt/melos

# Pull the latest images
docker compose pull

# Start services in the background
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose up -d

# Verify all services are healthy
docker compose ps
```

**Expected Output:**
```
NAME       IMAGE              STATUS
melos-db   pgvector:pg16      Up (healthy)
melos-api  melos-api:latest   Up (healthy)
melos-ui   melos-ui:latest    Up (healthy)
melos-mcp  melos-mcp:latest   Up (healthy)
```

### 6. Verify Health Endpoints

```bash
# Check API health
curl -I http://localhost:8000/health
# Expected: 200 OK with JSON {"status":"healthy","service":"api","timestamp":"..."}

# Check UI health
curl -I http://localhost:3000/health
# Expected: 200 OK with JSON {"status":"healthy","service":"ui","timestamp":"..."}

# Check MCP health
curl -I http://localhost:9000/health
# Expected: 200 OK with JSON {"status":"healthy","service":"mcp","timestamp":"..."}

# Check from the reverse proxy
curl -I https://melos.example.com/health
# Expected: 200 OK from the UI
```

### 7. Verify Database Migrations

```bash
# Check current migration
docker compose exec api uv run alembic current
# Expected: 0002_pgvector_kitchen_lang (head)

# Verify pgvector extension is installed
docker compose exec db psql -U melos -d melos -c "\\dx vector"
# Expected: vector extension listed
```

### 8. Test Core Flows

1. **Sign Up**: Navigate to https://melos.example.com and create an account
2. **Verify Email**: Check your inbox for the verification email
3. **Sign In**: Use the credentials to sign in
4. **Kitchen Operations**: Create a kitchen, invite a member, test permissions

## Monitoring & Operations

### Health Checks

The Docker Compose stack includes health checks for all services. Monitor the status:

```bash
# View logs for all services
docker compose logs -f

# View logs for a specific service
docker compose logs -f api
docker compose logs -f ui

# Check service status
docker compose ps
```

### Backup and Recovery

#### Backup PostgreSQL Data

```bash
# Stop all services
docker compose down

# Backup the database volume
tar -czf /backups/melos-pgdata-$(date +%Y-%m-%d).tar.gz /var/melos/pgdata

# Restart services
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose up -d
```

#### Restore from Backup

```bash
# Stop services
docker compose down

# Remove corrupted data
rm -rf /var/melos/pgdata/*

# Extract backup
tar -xzf /backups/melos-pgdata-YYYY-MM-DD.tar.gz -C /

# Restart
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose up -d
```

### Common Operations

**Restart services:**
```bash
docker compose restart
```

**Update to latest version:**
```bash
git pull
docker compose pull
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose up -d
```

**View recent logs:**
```bash
docker compose logs --tail=50 -f
```

**Scale a service (if needed):**
```bash
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml docker compose up -d --scale api=2
```

## Troubleshooting

### Services won't start

```bash
# Check logs
docker compose logs api
docker compose logs ui
docker compose logs db

# Verify .env file has all required values
env | grep -E "POSTGRES|SESSION|SMTP" | head -10

# Verify data directory exists
ls -la /var/melos/pgdata
```

### Database migration fails

```bash
# Check Alembic history
docker compose exec api uv run alembic history

# If stuck, reset to a known state
docker compose exec api uv run alembic downgrade -1
docker compose exec api uv run alembic upgrade head
```

### Email not being sent

```bash
# Check SMTP configuration in logs
docker compose logs api | grep -i smtp

# Test SMTP manually
docker compose exec api python3 << 'EOF'
import os
from adapters.email import load_smtp_settings, SmtpEmailSender
settings = load_smtp_settings()
print(f"Host: {settings.host}, Port: {settings.port}, User: {settings.user}")
EOF
```

### High memory usage

```bash
# Check Docker stats
docker stats

# Restart the problematic service
docker compose restart api  # or ui, db, mcp
```

## Security Checklist

- [ ] `.env` file is **not committed** to version control (verify `.gitignore`)
- [ ] PostgreSQL password is **strong and random** (32+ characters)
- [ ] SESSION_SECRET is **strong and random** (32+ characters)
- [ ] TLS certificate is valid and not expired
- [ ] SMTP password is stored **only in `.env`**, never in code or logs
- [ ] GEMINI_API_KEY is stored **only in `.env`** if used
- [ ] `TRUSTED_PROXY_IPS` is set to **only the reverse proxy IP**
- [ ] Health endpoints are accessible (no authentication required per design)
- [ ] Rate limits are configured appropriately for your user base
- [ ] Backup of PostgreSQL data is on a separate, secure storage

## Getting Help

- **Issues**: Check [GitHub Issues](https://github.com/your-org/melos/issues)
- **Documentation**: See [README.md](README.md) and [CONTRIBUTING.md](CONTRIBUTING.md)
- **Spec**: Full specification in [specs/001-finance-dashboard-reuse/](specs/001-finance-dashboard-reuse/)
- **Constitution**: Project governance in [.specify/memory/constitution.md](.specify/memory/constitution.md)

