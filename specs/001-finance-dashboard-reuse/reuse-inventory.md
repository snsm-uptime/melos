# Melos Reuse Inventory — What Gets Copied, Adapted, and Built New

**Status:** Implementation Planning  
**Date:** 2026-10-19  
**Scope:** Bootstrap phase only; future features tracked in separate specs

---

## Repository Layout & Configuration

| Component | Source | Status | Adaptation | Files |
|-----------|--------|--------|----------|-------|
| **Python runtime** | finance-dashboard | ✓ Reused | Python 3.12, `uv` tooling | `.python-version`, `pyproject.toml`, `uv.lock` |
| **Node.js runtime** | finance-dashboard | ✓ Reused | Latest stable | `.node-version`, `package.json`, `package-lock.json` |
| **Docker Compose base** | finance-dashboard | ✓ Reused as-is | — | `docker-compose.yml` |
| **Compose dev overlay** | finance-dashboard | ⚙ Adapted | Add Gemini env vars, pgvector config, MELOS_* prefix | `docker-compose.dev.yml` |
| **Compose test overlay** | finance-dashboard | ✓ Reused as-is | — | `docker-compose.test.yml` |
| **Compose prod overlay** | finance-dashboard | ✓ Reused as-is | — | `docker-compose.prod.yml` |
| **Worktree Compose overlays** | finance-dashboard | ✓ Reused | Names adapted to Melos | `docker-compose.worktree.yml`, `.worktree-lite.yml` |
| **CI/CD workflow** | finance-dashboard | ✓ Reused as-is | Same lint, test, build steps | `.github/workflows/ci.yml` |
| **Cursor worktree config** | finance-dashboard | ✓ Reused as-is | — | `.cursor/worktrees.json` |
| **.env.example** | finance-dashboard | ⚙ Adapted | New vars: `MELOS_*`, `GEMINI_*`; no finance credentials | `.env.example` |
| **.gitignore** | finance-dashboard | ✓ Reused | Standard Python/Node ignores | `.gitignore` |

---

## API Layer (Backend)

### Pure Domain Layer (`api/domain/`)

| Module | Purpose | Reused? | Notes |
|--------|---------|---------|-------|
| `recipe.py` | Recipe units, dimensions, validation | ✗ NEW | Melos-specific recipe model |
| `cart.py` | Cart scaling, consolidation rules | ✗ NEW | Melos-specific cart logic |
| `ingredient_catalog.py` | Ingredient name normalization | ✗ NEW | Melos ingredient data |
| `toon.py` | TOON encoding for LLM prompts | ✗ NEW | Melos-specific prompt formatting |
| `render.py` | Markdown/embed text generation | ✗ NEW | Melos export/display logic |
| `kitchen.py` | Kitchen domain model | ✓ Reused (from finance "list") | Renamed, same structure |
| `membership.py` | Membership (owner/member) model | ✓ Reused | Same access control pattern |
| `invite.py` | Invite-by-email logic | ✓ Reused | Same flow structure |

### Application Layer (`api/application/`)

| Module | Purpose | Reused? | Notes |
|--------|---------|---------|-------|
| `ports.py` | Port definitions (RecipeExtractor, Embedder, ChatModel, etc.) | ✗ NEW | Melos-specific service abstractions |
| **Use Cases:** | | | |
| `auth/*` | Session, password reset, email verification | ✓ Reused | Reuse without modification (FR5) |
| `kitchens.py` | Kitchen CRUD, access control | ✓ Reused pattern | Kitchen replaces "list"; membership check pattern reused |
| `invites.py` | Invite management | ✓ Reused pattern | Same flow, kitchen scope |
| `recipes.py` | Recipe CRUD | ✗ NEW | Melos feature |
| `capture_recipe.py` | Recipe extraction from text/URL | ✗ NEW | Melos feature; uses RecipeExtractor port |
| `ingredients.py` | Ingredient catalog | ✗ NEW | Melos feature |
| `categories.py` | Category management | ✗ NEW | Melos feature |
| `carts.py` | Cart operations | ✗ NEW | Melos feature |
| `shopping_list.py` | Shopping list CRUD and history | ✗ NEW | Melos feature |
| `conversations.py` | Conversation management | ✗ NEW | Melos feature; uses ChatModel port |
| `exports.py` | PDF/Markdown generation | ✗ NEW | Melos feature; uses PdfRenderer port |

### Adapters (`api/adapters/`)

| Directory | Purpose | Reused? | Implementation |
|-----------|---------|---------|-----------------|
| `llm/gemini.py` | Gemini API integration | ✗ NEW | Implements ChatModel and Embedder ports; google-genai SDK |
| `web/page_fetcher.py` | SSRF-safe URL fetching | ✗ NEW | Implements PageFetcher port; httpx with SSRF validation |
| `web/jsonld.py` | JSON-LD recipe parsing | ✗ NEW | Utility for recipe extraction from web pages |
| `pdf/weasyprint.py` | PDF rendering | ✗ NEW | Implements PdfRenderer port; WeasyPrint with Unicode fonts |
| `pdf/templates/` | PDF templates | ✗ NEW | HTML templates for recipe/list export |
| `pdf/fonts/` | Unicode font files | ✗ NEW | Fonts for PDF rendering (e.g., DejaVu for symbols) |
| **persistence/** | | | |
| `models.py` | SQLAlchemy ORM models | ✓ Reused + NEW | Reuse: User, Session, PasswordReset, EmailVerification, Preferences; New: Recipe, Ingredient, Cart, ShoppingList, Conversation, etc. |
| `sessions.py` | Session storage | ✓ Reused as-is | Session table, httpOnly cookie |
| `password_hasher.py` | Argon2 hashing | ✓ Reused as-is | Password hashing (FR5.1) |
| `password_reset.py` | Password reset tokens | ✓ Reused as-is | Token table and queries (FR5.1) |
| `email_verification.py` | Email verification tokens | ✓ Reused as-is | Token table and queries (FR5.1) |
| `repositories.py` | Data access objects | ✓ Reused + NEW | Reuse: SqlAlchemyAuthUserRepository; New: RecipeRepository, etc. |
| **email/** | | | |
| `smtp.py` | SMTP email adapter | ✓ Reused as-is | aiosmtplib wrapper for password reset/verification emails (FR5.1) |
| `settings.py` | Email configuration | ✓ Reused as-is | SMTP environment variables |
| **auth/** | All files listed in FR5.1 | ✓ Reused as-is | No modifications; see FR5.1 for complete inventory |

### API Routes (`api/api/routes/`)

| File | Endpoints | Reused? | Notes |
|------|-----------|---------|-------|
| `auth.py` | `/auth/*` | ✓ Reused as-is | Register, sign-in, sign-out, session, me, password reset, email verify (FR5.1) |
| `kitchens.py` | `/kitchens/*` | ✗ NEW | Kitchen CRUD with access control |
| `members.py` | `/kitchens/{id}/members/*` | ✗ NEW | Member management (add, remove, list) |
| `invites.py` | `/kitchens/{id}/invites/*` | ✗ NEW | Invite management (create, accept, resend) |
| `recipes.py` | `/kitchens/{id}/recipes/*` | ✗ NEW | Recipe CRUD |
| `drafts.py` | `/kitchens/{id}/drafts/*` | ✗ NEW | Draft recipe management (pre-review) |
| `ingredients.py` | `/kitchens/{id}/ingredients/*` | ✗ NEW | Ingredient catalog |
| `categories.py` | `/kitchens/{id}/categories/*` | ✗ NEW | Category management |
| `carts.py` | `/kitchens/{id}/carts/*` | ✗ NEW | Cart operations |
| `shopping_list.py` | `/kitchens/{id}/shopping-list/*` | ✗ NEW | Shopping list CRUD |
| `conversations.py` | `/kitchens/{id}/conversations/*` | ✗ NEW | Conversation management |
| `messages.py` | `/kitchens/{id}/conversations/{id}/messages/*` | ✗ NEW | Message CRUD |
| `exports.py` | `/kitchens/{id}/exports/*` | ✗ NEW | PDF/Markdown export |
| `health.py` | `/health` | ✗ NEW | Health check endpoint |

### Configuration & Setup

| File | Purpose | Reused? | Changes |
|------|---------|---------|---------|
| `api/settings.py` | Environment variable loading | ✓ Reused + Extended | Add Gemini, pgvector, seed config vars |
| `api/app.py` | FastAPI app initialization | ✓ Reused + Extended | Add Gemini/embedding initialization; rate limit, session middleware setup |
| `api/deps.py` | Dependency injection | ✓ Reused + Extended | Reuse: auth, session; New: kitchen access guard |
| `api/schemas/` | Pydantic models | ✓ Reused + NEW | Reuse: auth schemas; New: recipe, cart, etc. schemas |

---

## UI Layer (Frontend)

### Page Components

| Path | Purpose | Reused? | Adaptation |
|------|---------|---------|----------|
| **Auth Pages** (Reused with Minor Changes) | | | |
| `app/sign-in/` | Sign-in flow | ✓ Reused as-is | — |
| `app/sign-up/` | Sign-up flow | ✓ Reused as-is | — |
| `app/forgot-password/` | Forgot password flow | ✓ Reused as-is | — |
| `app/reset-password/` | Reset password (token validation) | ✓ Reused as-is | — |
| `app/verify/` | Email verification | ✓ Reused as-is | — |
| `app/account/` | User profile & preferences | ✓ Reused + Adapted | Remove language selection UI (FR5.2) |
| **Kitchen Pages** (New for Melos) | | | |
| `app/[kitchen]/recipes/` | Recipe list and browse | ✗ NEW | Kitchen-scoped recipe UI |
| `app/[kitchen]/recipes/[id]/` | Recipe detail | ✗ NEW | Recipe view, edit, delete |
| `app/[kitchen]/capture/` | Recipe capture (URL/text) | ✗ NEW | Form for recipe input |
| `app/[kitchen]/cart/` | Shopping cart | ✗ NEW | Cart view, add/remove items |
| `app/[kitchen]/shopping-list/` | Shopping list | ✗ NEW | List view, check off items |
| `app/[kitchen]/chat/` | Conversation interface | ✗ NEW | Chat UI with history |
| `app/[kitchen]/settings/` | Kitchen settings & members | ✗ NEW | Kitchen config, member list, invites |
| `app/kitchens/` | Kitchen selection/creation | ✗ NEW | List user's kitchens |

### Reusable Components

| Component | Purpose | Reused? | Notes |
|-----------|---------|---------|-------|
| `AppShell.tsx` | Main layout wrapper | ✓ Reused as-is | Session init, nav, theme provider |
| `AccountMenu.tsx` | User dropdown menu | ✓ Reused + Adapted | Remove language selector (FR5.2) |
| `PreferencesProvider.tsx` | Theme/preferences context | ✓ Reused + Adapted | Rename localStorage keys: `fh_*` → `melos_*`; remove language toggle (FR5.2) |
| `RedirectIfAuthenticated.tsx` | Route guard | ✓ Reused as-is | Redirect authed users from auth pages |
| `ActionDialog.tsx` | Confirmation modal | ✓ Reused as-is | Generic modal component |
| `Chip.tsx`, `ChipPicker.tsx` | Tag-like components | ✓ Reused as-is | Category/ingredient selection |
| `IconButton.tsx`, `Disclosure.tsx` | UI primitives | ✓ Reused as-is | Common button/expand patterns |
| `CopyButton.tsx` | Copy-to-clipboard | ✓ Reused as-is | Copy recipe links, ingredients |
| **Kitchen Components** (New) | | | |
| `KitchenSelector.tsx` | Kitchen switcher | ✗ NEW | Dropdown/menu for kitchen switching |
| `RecipeCard.tsx` | Recipe preview card | ✗ NEW | Summary, image, quick actions |
| `CartItem.tsx` | Cart item with scaling | ✗ NEW | Editable quantity, removal |
| `ConversationMessage.tsx` | Chat message bubble | ✗ NEW | Message display with citations |
| `InviteLink.tsx` | Invite sharing UI | ✗ NEW | Copy invite link, send email option |

### Backend-for-Frontend (BFF) Routes

| Path | Purpose | Reused? | Notes |
|------|---------|---------|-------|
| `app/api/auth/sign-in/` | Proxy → POST /auth/sign-in | ✓ Reused as-is | Cookie forwarding |
| `app/api/auth/register/` | Proxy → POST /auth/register | ✓ Reused as-is | — |
| `app/api/auth/sign-out/` | Proxy → POST /auth/sign-out | ✓ Reused as-is | — |
| `app/api/auth/session/` | Proxy → GET /auth/session | ✓ Reused as-is | — |
| `app/api/auth/me/` | Proxy → GET /auth/me | ✓ Reused as-is | — |
| `app/api/auth/verify/` | Proxy → email verification | ✓ Reused as-is | — |
| `app/api/auth/password-reset/` | Proxy → password reset | ✓ Reused as-is | — |

### Utilities & Libraries

| File | Purpose | Reused? | Notes |
|------|---------|---------|-------|
| `lib/session.ts` | Session types and helpers | ✓ Reused as-is | — |
| `lib/authBff.ts` | BFF auth proxy logic | ✓ Reused as-is | Cookie forwarding, IP header validation |
| `lib/authBff.test.ts` | BFF tests | ✓ Reused as-is | — |
| `lib/api.ts` | API client wrapper | ✗ NEW | Fetch wrapper, error handling, kitchen context |
| `lib/format.ts` | Text formatting utilities | ✗ NEW | Recipe display, quantity formatting |

### Styling & Theme

| File | Purpose | Reused? | Notes |
|------|---------|---------|-------|
| `styles/globals.css` | Global styles | ✓ Reused as-is | Tailwind directives, CSS variables |
| `tailwind.config.ts` | Tailwind configuration | ✓ Reused | Color palette, spacing, typography |
| `tailwind.config.ts` (color updates) | Dark mode support | ✓ Reused as-is | CSS variables for theme switching |

---

## Scripts & Tooling

| Script | Purpose | Reused? | Adaptation |
|--------|---------|---------|----------|
| `scripts/compose-up.sh` | Start all services | ✓ Reused as-is | — |
| `scripts/compose-down.sh` | Stop all services | ✓ Reused as-is | — |
| `scripts/compose-restart.sh` | Restart services | ✓ Reused as-is | — |
| `scripts/compose-wipe-db.sh` | Reset database | ✓ Reused as-is | — |
| `scripts/compose-lib.sh` | Helper functions | ✓ Reused as-is | — |
| `scripts/worktree/` | Worktree management | ✓ Reused | Names adapted to Melos |
| `api/scripts/seed_dev_user.py` | Development seeding | ✗ NEW | Pre-create test user, kitchen, recipes |
| `api/scripts/alembic/` | Database migrations | ✓ Reused pattern | New Alembic migrations for Melos schema |

---

## Database Schema

### Reused Tables (Auth Layer)
- `user` — User credentials, email, created_at
- `session` — Session storage, cookie tokens
- `password_reset_token` — Token for password reset
- `email_verification` — Token for email verification
- `preferences` — User preferences (theme, locale, photo)

### Reused Tables (Kitchen/Membership)
- `kitchen` — Kitchen metadata (renamed from "list")
- `membership` — Kitchen membership (owner/member roles)
- `invite` — Kitchen invites (email + token)

### New Tables (Melos)
- `recipe` — Recipe data (title, servings, source_url)
- `recipe_ingredient` — Recipe ingredient lines
- `ingredient` — Ingredient master catalog
- `category` — Category master catalog
- `recipe_category` — Recipe-to-category junction
- `cart` — Shopping cart (kitchen_id, user_id, created_at)
- `cart_item` — Cart items (recipe_id, meal_count)
- `shopping_list` — Shopping list (kitchen_id, created_at, closing_date)
- `shopping_list_item` — Items in list (ingredient, quantity, checked)
- `conversation` — Chat session (kitchen_id, created_at)
- `message` — Chat messages (conversation_id, role, content, citations)
- `recipe_embedding` — pgvector embeddings for semantic search
- `source` — Recipe source tracking (URL, import date)

---

## Dependencies & Versions

### Python (`api/pyproject.toml`)

**Reused:**
- FastAPI 0.141.1, Uvicorn 0.52.1 (web framework)
- SQLAlchemy 2.0.51, Alembic 1.18.5 (ORM, migrations)
- psycopg 3.3.4 (PostgreSQL driver, async)
- Pydantic 2.13.4 (validation)
- argon2-cffi 25.1.0 (password hashing)
- aiosmtplib 5.1.2 (email)
- pytest 9.1.1, httpx 0.28.1 (testing)
- ruff 0.14.7 (linting)

**New:**
- google-genai (Gemini API)
- httpx (web scraping, page fetching)
- beautifulsoup4 (HTML parsing for JSON-LD)
- weasyprint (PDF generation)
- psycopg[binary] for pgvector (pgvector NumPy integration)

### Node.js (`ui/package.json`)

**Reused:**
- Next.js 16.2.12, React 19.2.4, React DOM 19.2.4
- Tailwind CSS 4.3.3, PostCSS 8.5.26 (styling)
- TypeScript 5 (type safety)
- Vitest 4.1.10 (testing)
- ESLint 9 (linting)
- Turbopack (bundler, dev mode)

---

## Implementation Phases (Checklist Reference)

See **Appendix A: Reuse Checklist** in spec.md for validation.

**Phase 1: Bootstrap**
- [ ] Copy api/ structure with auth layer as-is
- [ ] Copy ui/ structure with auth components and minimal adaptations
- [ ] Copy Compose files and scripts
- [ ] Adapt .env.example with MELOS_* and GEMINI_* vars
- [ ] Verify all tests pass locally and in Compose

**Phase 2: Melos Features** (Separate feature specs)
- [ ] Implement recipe capture (RecipeExtractor port)
- [ ] Implement cart and shopping list (CRUD, consolidation)
- [ ] Implement conversations (ChatModel port, Embedder port)
- [ ] Implement exports (PDF rendering)

---

## Status Summary

| Category | % Complete | Notes |
|----------|----------|-------|
| Planning | 100% | Spec and research complete |
| Bootstrap Prep | 0% | Awaiting implementation start |
| Melos Features | 0% | Deferred to separate feature specs |

