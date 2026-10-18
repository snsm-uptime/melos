# Implementation Plan: Melos Recipe & Kitchen System

**Branch**: `001-recipe-kitchen-system` | **Date**: 2026-10-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-recipe-kitchen-system/spec.md`

**Note**: This plan is filled in by the `/speckit-plan` command and describes the execution workflow for implementation.

## Summary

Implement the complete Melos platform: a meal planning and shopping list system that captures recipes from multiple sources, structures them in a shared kitchen, answers questions about ingredients and meals, and generates consolidated shopping lists scaled to household size. The system reuses authentication, UI patterns, and deployment infrastructure from the finance-dashboard project while adding recipe extraction (via Gemini), ingredient catalog management, and shopping list consolidation.

**Core MVP**: Users can add recipes (text/URL/photo), view their kitchen, ask questions about it, and generate shopping lists. Role-based access (Visitor/Member/Owner) enables multi-user households.

## Technical Context

**Language/Version**: Python 3.12 (backend), JavaScript/TypeScript (frontend)

**Primary Dependencies**: 
- Backend: FastAPI, SQLAlchemy, Alembic, Google Gemini API
- Frontend: Next.js 16 (App Router), React 19, Tailwind 4
- Infrastructure: pgvector (PostgreSQL extension), WeasyPrint (PDF), aiosmtplib (email)

**Storage**: PostgreSQL 16 + pgvector (for embedding similarity search on recipes)

**Testing**: pytest (backend), vitest (frontend), contract tests

**Target Platform**: Web (desktop-first, responsive for mobile in v2)

**Project Type**: Web application (frontend + backend)

**Performance Goals**: 
- Recipe capture (text/URL/photo) completes in <2 minutes for typical recipes
- Shopping list generation from 5+ recipes in <10 seconds
- Question answering (similarity search + LLM) in <5 seconds
- Support 10+ concurrent users per kitchen without slowdown

**Constraints**: 
- No workers/queues; all operations are synchronous with UI feedback via progress states
- Ingredient scaling is linear (user reviews non-linear items manually)
- Session-based authentication only (no OAuth for v1)
- PDF generation uses server-side rendering (no client-side libraries)

**Scale/Scope**: 
- v1 targets small households (2–6 people)
- ~50–100 recipes per kitchen expected
- All recipes, ingredients, and shopping lists are kitchen-specific (full multi-tenancy)
- Reuses auth, session, and membership infrastructure from finance-dashboard

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Core Principles Verification**:

✅ **I. User-Centric Non-Technical Design**
- Spec explicitly targets non-technical home cooks; UI/UX is straightforward (no command-line, no configuration)
- Recipe capture accepts multiple source formats (text, URL, photo) to match how users naturally collect recipes
- No technical jargon in acceptance scenarios

✅ **II. Kitchen as Source of Truth**
- Kitchen entity is the authoritative hub for recipes, ingredients, and member roles
- All queries and decisions (shopping lists, question answering) are grounded in kitchen state
- Shared catalog prevents duplicate ingredient names; members operate on shared data

✅ **III. AI Structures, Code Scales**
- Gemini RecipeExtractor is bounded: structures free-form recipes into schema
- Kitchen Assistant answers questions grounded in kitchen data
- Domain layer (`domain/cart.py`) handles scaling, merging, and consolidation via pure code
- No AI substitution logic or meal recommendations in v1

✅ **IV. Contracts Before Implementation**
- Data contracts (Recipe, Ingredient, Kitchen, ShoppingList, Member) are defined in spec and will be formalized in `data-model.md`
- TOON encoding scheme (Appendix B) is documented in PRD
- API contracts will be defined in `contracts/` directory before implementation

✅ **V. Role-Based Access with Clear Boundaries**
- Visitor, Member, Owner roles are documented in spec and tested in acceptance scenarios
- Permission checks happen in application layer (following finance-dashboard pattern)
- No ambiguous cases remain in scope (admin/moderator roles out of scope)

**No Constitution violations detected. Ready to proceed.**

## Project Structure

### Documentation (this feature)

```text
specs/001-recipe-kitchen-system/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (NEXT: identify unknowns)
├── data-model.md        # Phase 1 output (entities, relationships, validation)
├── quickstart.md        # Phase 1 output (end-to-end validation workflow)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── api.md           # REST API endpoints and request/response shapes
│   ├── domain.md        # Domain model shapes (Recipe, Ingredient, etc.)
│   └── ui.md            # UI contract (page layouts, component responsibilities)
├── checklists/
│   └── requirements.md  # Specification quality checklist (passed ✅)
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

**Selected Structure**: Web application with reused finance-dashboard layout.

```text
api/                                 # Python backend (FastAPI)
├── src/
│   ├── domain/                       # Pure logic layer (no I/O)
│   │   ├── recipe.py                 # Recipe, Unit, Size, Dimension
│   │   ├── ingredient_catalog.py     # Ingredient name normalization
│   │   ├── cart.py                   # Shopping list scaling & merging
│   │   ├── kitchen.py                # Kitchen, membership (from finance)
│   │   ├── toon.py                   # TOON encoder for recipes/ingredients
│   │   └── validation.py             # Shared rules (from Spec)
│   ├── application/                  # Use cases + ports (interfaces)
│   │   ├── ports.py                  # RecipeExtractor, Embedder, ChatModel, PageFetcher, PdfRenderer
│   │   ├── use_cases/
│   │   │   ├── capture_recipe.py     # Text/URL/photo → RecipeDraft
│   │   │   ├── recipes.py            # List, retrieve, edit recipes
│   │   │   ├── ingredients.py        # Ingredients, categories, normalize names
│   │   │   ├── shopping_list.py      # Cart → consolidated list
│   │   │   ├── conversations.py      # Ask questions, search recipes
│   │   │   ├── kitchens.py           # Create, view kitchen (from finance)
│   │   │   ├── invites.py            # Send, accept invites (from finance)
│   │   │   └── exports.py            # PDF, markdown exports
│   │   └── repositories/             # Interfaces for data access
│   ├── adapters/                     # Implementations of ports
│   │   ├── llm/
│   │   │   ├── gemini.py             # RecipeExtractor, ChatModel, Embedder (google-genai SDK)
│   │   │   └── prompts.py            # System prompts for extraction and chat
│   │   ├── web/
│   │   │   ├── page_fetcher.py       # Fetch & parse HTML (SSRF-safe)
│   │   │   └── jsonld.py             # Extract schema.org/Recipe JSON-LD
│   │   ├── pdf/
│   │   │   ├── weasyprint.py         # PDF rendering
│   │   │   └── templates/
│   │   │       └── shopping_list.html # Shopping list template
│   │   ├── persistence/
│   │   │   ├── models.py             # SQLAlchemy models
│   │   │   ├── repositories.py       # Concrete repository implementations
│   │   │   └── migrations/           # Alembic migrations
│   │   └── email/                    # SMTP (reused from finance)
│   ├── api/
│   │   ├── routes/
│   │   │   ├── auth.py               # Sign up, sign in, password reset (reused)
│   │   │   ├── kitchens.py           # Create, view, list kitchens
│   │   │   ├── members.py            # Add, list, remove members
│   │   │   ├── invites.py            # Send, list invites
│   │   │   ├── recipes.py            # Create, list, edit, delete recipes
│   │   │   ├── drafts.py             # Capture recipe (text/URL/photo) → draft
│   │   │   ├── ingredients.py        # List, normalize, match ingredients
│   │   │   ├── categories.py         # List ingredient categories
│   │   │   ├── shopping_list.py      # Cart, consolidation, export
│   │   │   ├── conversations.py      # Ask questions, list messages
│   │   │   ├── sources.py            # Recipe sources (URL, photo metadata)
│   │   │   ├── exports.py            # PDF, markdown exports
│   │   │   └── health.py             # Health check
│   │   ├── dependencies.py           # Request/response middleware
│   │   ├── security.py               # Auth verification
│   │   └── main.py                   # FastAPI app
│   └── settings.py                   # Configuration, env vars
├── tests/
│   ├── unit/                         # Pure logic tests (domain/)
│   │   ├── test_recipe.py
│   │   ├── test_cart.py
│   │   ├── test_ingredient_catalog.py
│   │   └── test_toon.py
│   ├── integration/                  # Use case tests with DB
│   │   ├── test_capture_recipe.py
│   │   ├── test_shopping_list.py
│   │   └── test_conversations.py
│   └── contract/                     # API contract tests
│       ├── test_recipe_endpoints.py
│       ├── test_kitchen_endpoints.py
│       └── test_shopping_list_endpoints.py
└── pyproject.toml                    # Python dependencies (uv)

ui/                                  # Next.js frontend (React 19)
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── layout.tsx
│   │   ├── page.tsx                  # Home
│   │   ├── (auth)/                   # Authentication pages (reused)
│   │   │   ├── sign-up/page.tsx
│   │   │   ├── sign-in/page.tsx
│   │   │   └── forgot-password/page.tsx
│   │   ├── kitchen/                  # Kitchen-scoped pages
│   │   │   ├── layout.tsx            # Kitchen shell (AppShell)
│   │   │   ├── page.tsx              # Kitchen overview
│   │   │   ├── recipes/
│   │   │   │   ├── page.tsx          # List recipes
│   │   │   │   ├── [id]/page.tsx     # View recipe
│   │   │   │   └── add/page.tsx      # Add recipe (text/URL/photo)
│   │   │   ├── ingredients/
│   │   │   │   ├── page.tsx          # Ingredient catalog
│   │   │   │   └── [id]/page.tsx     # View ingredient
│   │   │   ├── members/
│   │   │   │   ├── page.tsx          # Manage members
│   │   │   │   └── invite/page.tsx   # Send invite
│   │   │   ├── shopping-list/
│   │   │   │   ├── page.tsx          # View and generate list
│   │   │   │   └── [id]/page.tsx     # View saved list
│   │   │   ├── ask/
│   │   │   │   └── page.tsx          # Ask questions, chat
│   │   │   └── settings/
│   │   │       └── page.tsx          # Kitchen settings
│   │   └── account/page.tsx          # User account (reused)
│   ├── components/
│   │   ├── layout/                   # AppShell, AccountMenu (reused)
│   │   ├── recipe/                   # Recipe-specific components
│   │   │   ├── RecipeCard.tsx
│   │   │   ├── RecipeForm.tsx
│   │   │   ├── RecipeViewer.tsx
│   │   │   └── RecipeDraftViewer.tsx
│   │   ├── ingredient/               # Ingredient components
│   │   │   ├── IngredientList.tsx
│   │   │   ├── IngredientCard.tsx
│   │   │   └── IngredientMatcher.tsx
│   │   ├── shopping/                 # Shopping list components
│   │   │   ├── ShoppingListViewer.tsx
│   │   │   ├── ShoppingListGenerator.tsx
│   │   │   └── ExportButton.tsx
│   │   ├── kitchen/
│   │   │   ├── KitchenOverview.tsx
│   │   │   ├── MemberList.tsx
│   │   │   └── InviteForm.tsx
│   │   ├── common/                   # Reused (Chip, IconButton, etc.)
│   │   │   ├── ActionDialog.tsx
│   │   │   ├── CopyButton.tsx
│   │   │   └── Disclosure.tsx
│   │   └── ask/
│   │       ├── ConversationView.tsx
│   │       └── AskForm.tsx
│   ├── lib/
│   │   ├── api.ts                    # API client
│   │   ├── auth.ts                   # Session, login (reused)
│   │   └── hooks.ts                  # Custom hooks (useKitchen, useRecipes, etc.)
│   └── styles/
│       └── globals.css               # Tailwind 4
├── tests/
│   ├── unit/
│   │   └── hooks/                    # Hook tests
│   └── e2e/
│       └── kitchen.spec.ts           # E2E: add recipe, view, generate list
└── package.json

scripts/                              # Shared scripts
├── compose-up.sh
├── compose-down.sh
├── compose-restart.sh
├── wipe-db.sh
└── worktree/                         # Git worktree automation

docker-compose.yml                    # Services: db, api, ui
.github/workflows/                    # CI/CD (reused from finance)
```

**Structure Decision**: Reuses finance-dashboard layout (hexagonal API + Next.js UI) with Melos-specific domains. All Melos data is kitchen-scoped; auth, session, and membership infrastructure are reused. No new services required (no workers, no queue).

---

## Phase 0: Research (COMPLETE)

✅ All unknowns resolved in `research.md`:

1. Recipe extraction & TOON encoding → TOON per PRD Appendix B
2. Page fetching & SSRF safety → URL validation + timeout
3. Ingredient scaling → US measurements only; non-linear user-reviewed
4. Shopping list consolidation → Canonical names + kitchen catalog
5. Question answering → Embeddings + pgvector + TOON context
6. PDF generation → WeasyPrint + Jinja2
7. Authentication reuse → Full reuse; no Melos-specific changes
8. Multi-tenancy isolation → Kitchen-scoped; 404 for non-members
9. Recipe extraction errors → RecipeDraft with error state
10. Role model & permissions → Visitor/Member/Owner; clear boundaries

**Status**: Ready for Phase 1 design ✅

---

## Phase 1: Design (COMPLETE)

✅ All design artifacts generated:

### 1. Data Model (`data-model.md`)
- 10 core entities: Kitchen, Recipe, Ingredient, RecipeIngredient, Category, ShoppingList, Source, Member, Invite, Conversation, Message
- Full field definitions, relationships, validation rules
- Indexes and migration strategy

### 2. API Contracts (`contracts/api.md`)
- REST endpoints for all features
- Request/response shapes (JSON)
- Error handling and status codes
- Reused auth endpoints from finance-dashboard

### 3. Domain Contracts (`contracts/domain.md`)
- Entity shapes (Python dataclasses)
- Domain logic (validation, scaling, merging, embedding)
- Computed fields and state machines
- Recipe extraction, shopping cart, ingredient normalization, question answering

### 4. UI Contracts (`contracts/ui.md`)
- Page hierarchy (App Router structure)
- Core pages and responsibilities
- Shared components (AppShell, RecipeCard, etc.)
- Responsive breakpoints and accessibility

### 5. Quickstart Guide (`quickstart.md`)
- 7 end-to-end validation scenarios
- API testing via curl
- UI testing instructions
- Success criteria coverage

**Status**: Ready for Phase 2 (task generation) ✅

---

## Next Phase: `/speckit-tasks`

The implementation phase will:
1. Read this plan and all Phase 1 artifacts
2. Break down work into granular, sequenced tasks
3. Assign effort estimates and dependencies
4. Generate `tasks.md` with task list for developers

Then, developers execute tasks in sequence, validating against:
- Spec requirements
- Data model contracts
- API contracts
- UI contracts
- Quickstart scenarios
