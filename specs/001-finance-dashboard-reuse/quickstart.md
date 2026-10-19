# Finance-Dashboard Reuse Integration — Quickstart & Validation

**Status:** Implementation guide for bootstrap phase  
**Audience:** Developers setting up Melos for the first time; code reviewers validating reuse  
**Time to complete:** ~15 minutes (setup + health checks)

---

## Prerequisites

- macOS, Linux, or WSL2 (Windows)
- Docker and Docker Compose (v2+)
- Git
- Bash shell
- Text editor
- No existing Melos or finance-dashboard repos locally (or use separate directories)

---

## Phase 1: Initial Setup

### 1.1 Clone and Navigate

```bash
git clone https://github.com/snsm-uptime/melos.git
cd melos
```

### 1.2 Copy Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in required values:

```bash
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<generate_secure_password>  # e.g., $(openssl rand -base64 32)
POSTGRES_DB=melos

# Session
SESSION_SECRET=<generate_random_string_64>  # e.g., $(openssl rand -base64 64)
SESSION_COOKIE_SECURE=false  # false in dev, true in prod
SESSION_COOKIE_SAMESITE=Lax

# Gemini (AI/LLM)
GEMINI_API_KEY=<obtain_from_google_ai_studio>
GEMINI_CHAT_MODEL=gemini-2.0-flash-exp
GEMINI_EMBED_MODEL=text-embedding-004
GEMINI_EMBED_DIM=768

# Email (optional for dev, but required if testing password reset)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<your_email>
SMTP_PASSWORD=<app_password>
SMTP_FROM=noreply@melos.local
SMTP_USE_TLS=false
SMTP_STARTTLS=true
SMTP_TIMEOUT_SECONDS=10

# App URL
PUBLIC_APP_URL=http://localhost:3000

# Dev Seeding (pre-populate test data)
SEED_DEV_USER=1
SEED_DEV_USER_EMAIL=dev@example.com
SEED_DEV_USER_PASSWORD=Password123!
SEED_DEV_USER_ALIAS=Developer
```

**Security note:** `.env` is in `.gitignore` and never committed. Keep secrets safe.

### 1.3 Create Data Directory

PostgreSQL data persists in a host volume outside the repo:

```bash
mkdir -p "${MELOS_DATA:-$HOME/melos}/pgdata"
chmod 700 "${MELOS_DATA:-$HOME/melos}"
```

### 1.4 Install Python Dependencies

```bash
cd api
uv sync --group dev
cd ..
```

**Note:** Never use `pip` or `python -m venv`. Use `uv` only.

### 1.5 Install Node.js Dependencies

```bash
cd ui
npm install
cd ..
```

---

## Phase 2: Start Services

### 2.1 Bring Up All Containers

```bash
./scripts/compose-up.sh -d
```

This starts:
- **db** (PostgreSQL 16 + pgvector on port 5432)
- **api** (FastAPI on port 8000)
- **ui** (Next.js on port 3000)
- **mcp** (MCP service on port 9000)

**Watch logs:**
```bash
docker compose logs -f
```

**Wait for startup:** ~30 seconds for all services to be healthy.

### 2.2 Verify Database Migrations

The API container runs `alembic upgrade head` automatically on startup. Verify:

```bash
docker compose exec api alembic current
```

Should output something like:
```
2026_10_19_001_initial_schema (head)
```

---

## Phase 3: Health Checks

### 3.1 API Health

```bash
curl -s http://localhost:8000/health | jq .
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-10-19T12:00:00Z",
  "version": "1.0.0"
}
```

### 3.2 UI Health (Browser)

Open: **http://localhost:3000**

**Expected:** Sign-in page with email and password fields

### 3.3 MCP Health

```bash
curl -s http://localhost:9000/health | jq .
```

**Expected response:**
```json
{
  "status": "healthy"
}
```

---

## Phase 4: Authentication Flow (Manual Validation)

### 4.1 Sign Up

1. Visit http://localhost:3000
2. Click "Sign Up" or navigate to http://localhost:3000/sign-up
3. Enter:
   - Email: `test@example.com`
   - Password: `TestPassword123!`
   - Alias: `Test User`
4. Click "Create Account"

**Expected:**
- Page redirects to http://localhost:3000/[kitchen] (kitchen selector or first kitchen)
- Browser cookies include `session_id` (HTTP-only)
- Database `user` table has one row

**Verify in API logs:**
```bash
docker compose logs api | grep "register\|201"
```

### 4.2 Sign In (New Session)

1. Sign out (account menu → Sign Out)
2. Sign in with the same credentials

**Expected:**
- Redirects to kitchen selector/dashboard
- Session cookie is refreshed
- Same `user_id` in API response

### 4.3 Sign Out

1. Click account menu (top right)
2. Click "Sign Out"

**Expected:**
- Redirected to http://localhost:3000/sign-in
- Session cookie is cleared
- Subsequent API calls return 401

---

## Phase 5: Kitchen Setup (Manual Validation)

### 5.1 Create a Kitchen

1. Sign in if not already
2. Navigate to kitchen creation page
3. Enter kitchen name: `Test Kitchen`
4. Click "Create"

**Expected:**
- Redirects to http://localhost:3000/[kitchen_id]/recipes (kitchen dashboard)
- Kitchen appears in kitchen list

**Verify in API logs:**
```bash
docker compose logs api | grep "kitchen\|POST"
```

### 5.2 Verify Seeded Data (If SEED_DEV_USER=1)

If you enabled `SEED_DEV_USER`, the dev user is pre-created with sample recipes:

1. Sign in with `SEED_DEV_USER_EMAIL` (from .env)
2. You should see a kitchen with 3–5 recipes
3. Recipes have ingredients, categories, and steps

**Database check:**
```bash
docker compose exec db psql -U postgres -d melos -c "SELECT COUNT(*) FROM recipe;"
```

Should return: `3` or more recipes.

---

## Phase 6: Code Quality & Testing

### 6.1 Python Linting

```bash
cd api
uv run ruff check .
cd ..
```

**Expected:** No errors. If there are warnings, ensure they align with the project's ruff.toml config.

### 6.2 Python Tests

```bash
cd api
uv run pytest -q
cd ..
```

Or in Compose:
```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api
```

**Expected:** All tests pass.

### 6.3 JavaScript Linting

```bash
cd ui
npm run lint
cd ..
```

**Expected:** No errors.

### 6.4 UI Tests

```bash
cd ui
npm test
cd ..
```

**Expected:** All tests pass.

---

## Phase 7: File Inventory Validation

### 7.1 Auth Layer Verification

Check that all required auth files are present and not modified:

```bash
# Check file existence
for file in \
  api/routes/auth.py \
  api/schemas/auth.py \
  api/deps.py \
  api/settings.py \
  api/app.py \
  api/application/email_verification.py \
  api/application/password_reset.py \
  api/application/preferences.py \
  api/adapters/persistence/sessions.py \
  api/adapters/persistence/password_hasher.py \
  api/adapters/persistence/repositories.py \
  api/adapters/persistence/models.py \
  api/adapters/email/smtp.py; do
  [ -f "$file" ] && echo "✓ $file" || echo "✗ MISSING: $file"
done
```

**Expected:** All files present (✓ marks).

### 7.2 UI Auth Components Verification

```bash
for file in \
  ui/app/sign-in/page.tsx \
  ui/app/sign-up/page.tsx \
  ui/app/forgot-password/page.tsx \
  ui/app/reset-password/page.tsx \
  ui/app/verify/page.tsx \
  ui/app/account/page.tsx \
  ui/components/AppShell.tsx \
  ui/components/PreferencesProvider.tsx \
  ui/components/AccountMenu.tsx \
  ui/lib/session.ts \
  ui/lib/authBff.ts; do
  [ -f "$file" ] && echo "✓ $file" || echo "✗ MISSING: $file"
done
```

**Expected:** All files present.

### 7.3 Environment Prefix Check

Verify that `.env` uses `MELOS_*` prefix (not `FH_*`):

```bash
grep -E "^FH_" .env && echo "✗ Found FH_ prefix (should be MELOS_)" || echo "✓ No FH_ prefix found"
```

**Expected:** `✓ No FH_ prefix found`

### 7.4 Dockerfile & Compose Verification

```bash
# Check Compose files exist
for file in docker-compose.yml docker-compose.dev.yml docker-compose.test.yml docker-compose.prod.yml; do
  [ -f "$file" ] && echo "✓ $file" || echo "✗ MISSING: $file"
done

# Check pgvector image is used
grep -q "pgvector/pgvector:pg16" docker-compose.yml && echo "✓ pgvector image found" || echo "✗ pgvector image missing"
```

**Expected:** All files present, pgvector image confirmed.

---

## Phase 8: Cleanup & Teardown

### 8.1 Stop Services

```bash
./scripts/compose-down.sh
```

### 8.2 Wipe Database (Optional, Resets State)

```bash
./scripts/compose-wipe-db.sh
```

This deletes all data and starts fresh. Useful for testing seeding again.

### 8.3 Remove Containers

```bash
docker compose down -v
```

---

## Troubleshooting

### Issue: Port Already in Use

If port 3000, 8000, or 9000 is already in use:

```bash
# Find process using port 8000
lsof -i :8000

# Kill process (replace PID)
kill -9 <PID>

# Or use different ports
API_HOST_PORT=8001 UI_HOST_PORT=3001 ./scripts/compose-up.sh
```

### Issue: Database Won't Start

Check Postgres logs:
```bash
docker compose logs db
```

Common issues:
- Data directory permissions (`chmod 700 ~/melos`)
- POSTGRES_PASSWORD not set
- Existing pgdata conflicts

Solution:
```bash
rm -rf ~/melos/pgdata
mkdir -p ~/melos/pgdata
chmod 700 ~/melos
./scripts/compose-down.sh
./scripts/compose-up.sh
```

### Issue: Alembic Migration Failed

Check API logs:
```bash
docker compose logs api | grep -i "alembic\|migration"
```

If migration is stuck:
```bash
docker compose exec api alembic stamp head
docker compose restart api
```

### Issue: SMTP Connection Failed

If you see email errors and SMTP is misconfigured:
1. Verify `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` in `.env`
2. For Gmail: Use an [app password](https://support.google.com/accounts/answer/185833), not your account password
3. For local testing: Leave SMTP blank (no password reset emails sent, but auth still works)

---

## Next Steps

1. **Read AGENTS.md** — Understand the development workflow and architecture boundaries
2. **Read constitution.md** — Review project principles and compliance requirements
3. **Start feature work** — See `specs/` for feature specifications
4. **Join development** — Check out a worktree branch and begin feature implementation

---

## Success Criteria

All these should pass before claiming bootstrap is complete:

- [ ] All 4 services (db, api, ui, mcp) are healthy (GET /health returns 200)
- [ ] Sign up → sign in → sign out flow works end-to-end
- [ ] Kitchen creation and viewing works
- [ ] All Python tests pass (uv run pytest -q)
- [ ] All JavaScript tests pass (npm test)
- [ ] Linting passes (ruff check ., npm run lint)
- [ ] Auth layer files present (no modifications)
- [ ] UI auth components present (with expected adaptations)
- [ ] Database migrations run automatically on startup
- [ ] No credentials or secrets appear in `.env.example`, README, or codebase

---

## Validation Script (Optional)

Save this as `scripts/validate-bootstrap.sh` for automated checks:

```bash
#!/bin/bash

set -e

echo "=== Melos Bootstrap Validation ==="
echo

# Health checks
echo "1. Checking service health..."
curl -s http://localhost:8000/health > /dev/null && echo "✓ API healthy" || echo "✗ API unhealthy"
curl -s http://localhost:9000/health > /dev/null && echo "✓ MCP healthy" || echo "✗ MCP unhealthy"

# File inventory
echo
echo "2. Checking auth layer files..."
files=(
  "api/routes/auth.py"
  "api/schemas/auth.py"
  "ui/app/sign-in/page.tsx"
  "ui/components/PreferencesProvider.tsx"
)
for file in "${files[@]}"; do
  [ -f "$file" ] && echo "✓ $file" || echo "✗ $file missing"
done

# Tests
echo
echo "3. Running Python tests..."
cd api && uv run pytest -q && echo "✓ Python tests pass" || echo "✗ Python tests failed"
cd ../ui && npm test && echo "✓ JavaScript tests pass" || echo "✗ JavaScript tests failed"
cd ..

echo
echo "=== Bootstrap Validation Complete ==="
```

Run:
```bash
chmod +x scripts/validate-bootstrap.sh
./scripts/validate-bootstrap.sh
```

