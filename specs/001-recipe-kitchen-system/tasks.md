# Tasks: Melos Recipe & Kitchen System

**Input**: Design documents from `/specs/001-recipe-kitchen-system/`

**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/ ✅, research.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

---

## Phase 1: Setup (Shared Infrastructure & Project Initialization)

**Purpose**: Project initialization and basic structure

**Status**: ✅ Complete

- [x] T001 Create repository structure (api/, ui/, scripts/) with .gitignore
- [x] T002 Initialize Python backend: create pyproject.toml (FastAPI, SQLAlchemy, Alembic, google-genai, weasyprint, pytest)
- [x] T003 Initialize Next.js frontend: npm create next-app with TypeScript, Tailwind 4
- [x] T004 [P] Create Docker Compose file (PostgreSQL 16, pgvector extension, API container, UI container)
- [x] T005 [P] Setup environment configuration (api/settings.py, MELOS_* env vars, ui/.env.local)
- [x] T006 Setup linting & formatting tools (ruff for Python, prettier for JS/TS)
- [x] T007 Create base FastAPI application skeleton (api/src/main.py with health check)
- [x] T008 Create base Next.js pages (layout, home page redirect to /kitchen)

---

## Phase 2: Foundational (Blocking Prerequisites for All User Stories)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can begin

⚠️ **CRITICAL**: No user story work can proceed until this phase is complete

**Status**: ✅ Complete (42 / 42 tasks complete)

### Database Setup

- [x] T009 Create Alembic migration structure (api/src/adapters/persistence/migrations/)
- [x] T010 Create SQLAlchemy base models (api/src/adapters/persistence/models.py) with Kitchen, Recipe, Ingredient, RecipeIngredient, Category, Source, Member, Invite, Conversation, Message tables
- [x] T011 [P] Create database indexes per data-model.md (kitchens, recipes, ingredients, members, invites, conversations, messages)
- [x] T012 Generate initial Alembic migration: create all tables with constraints
- [x] T013 Create database seeding script for testing (api/scripts/seed-db.py)

### Authentication & Session (Reused from Finance-Dashboard)

- [x] T014 Integrate existing auth routes (api/src/api/routes/auth.py) - sign-up, sign-in, sign-out, session verification
- [x] T015 Create user model import from shared auth schema (email/password only; OAuth out of scope for v1)
- [x] T016 [P] Configure session middleware (api/src/api/dependencies.py) with melos_session cookie (httpOnly, Secure, SameSite=Lax)
- [x] T017 [P] Create auth verification utilities (api/src/api/security.py) with password validation (8-256 characters from finance-dashboard)

### Domain Layer Foundation

- [x] T018 Create domain layer structure (api/src/domain/) with validation rules from spec
- [x] T019 Implement Recipe domain model (api/src/domain/recipe.py): Recipe, RecipeIngredient, Unit enum, Difficulty enum, ParseResult
- [x] T020 Implement Ingredient domain model (api/src/domain/ingredient_catalog.py): Ingredient, Category, canonical name normalization
- [x] T021 [P] Implement Kitchen domain model (api/src/domain/kitchen.py): Kitchen, Member roles (Visitor, Member, Owner)
- [x] T022 [P] Implement ShoppingList domain model (api/src/domain/cart.py): shopping list consolidation, scaling logic, item merging
- [x] T023 Implement TOON encoder/decoder (api/src/domain/toon.py) for safe LLM prompting. Reference: /dev/docs/appendix_b_prompts.md (Appendix B: TOON encoding format and examples)
- [x] T024 [P] Implement validation rules (api/src/domain/validation.py): field lengths, constraints from data-model.md

### Adapters & Ports (External Services)

- [x] T025 Create ports/interfaces (api/src/application/ports.py): RecipeExtractor, Embedder, ChatModel, PageFetcher, PdfRenderer, Repositories
- [x] T026 [P] Implement Gemini adapter (api/src/adapters/llm/gemini.py): RecipeExtractor, ChatModel, Embedder using google-genai SDK
- [x] T027 [P] Create LLM prompts module (api/src/adapters/llm/prompts.py): Recipe extraction and chat system prompts. Reference: /dev/docs/appendix_b_prompts.md for system prompt specifications and TOON encoding format.
- [x] T028 Implement page fetcher (api/src/adapters/web/page_fetcher.py): fetch URLs with SSRF validation (blocklist private IPs), timeout 10s
- [x] T029 [P] Implement JSON-LD extractor (api/src/adapters/web/jsonld.py): parse schema.org/Recipe from HTML
- [x] T030 [P] Implement PDF renderer (api/src/adapters/pdf/weasyprint.py): render shopping list template to PDF bytes
- [x] T031 Create shopping list template (api/src/adapters/pdf/templates/shopping_list.html) with Jinja2, CSS styling

### Repositories & Persistence

- [x] T032 Create repository interfaces (api/src/application/repositories/) with base repository class
- [x] T033 Implement KitchenRepository (api/src/adapters/persistence/repositories.py): create, read, list kitchens (kitchen_id scoped)
- [x] T034 [P] Implement RecipeRepository: create, read, update, delete, list recipes per kitchen
- [x] T035 [P] Implement IngredientRepository: create, read, update, list ingredients; support canonical name matching (Levenshtein distance, ≥80% threshold). Reference: domain/ingredient_catalog.py
- [x] T036 [P] Implement MemberRepository: read members, check roles, verify kitchen access
- [x] T037 [P] Implement ShoppingListRepository: create, read shopping lists (computed, not persisted)
- [x] T038 [P] Implement InviteRepository: create, read, accept invites; enforce token uniqueness and expiry

### API Foundation

- [x] T039 Setup FastAPI app initialization (api/src/api/main.py): middleware, error handlers, CORS
- [x] T040 [P] Create health check endpoint (api/src/api/routes/health.py): GET /health
- [x] T041 [P] Create kitchen endpoints skeleton (api/src/api/routes/kitchens.py) with role-based access control
- [x] T042 [P] Setup request validation and error response standardization (api/src/api/dependencies.py)

### Frontend Foundation

- [x] T043 Create app shell layout (ui/src/components/layout/AppShell.tsx) with navigation, user menu
- [x] T044 [P] Create reusable components (ui/src/components/common/): ActionDialog, CopyButton, Disclosure, ErrorBoundary
- [x] T045 [P] Setup API client (ui/src/lib/api.ts): fetch wrapper with auth headers, error handling
- [x] T046 [P] Setup authentication utilities (ui/src/lib/auth.ts): session check, login/logout, protected routes
- [x] T047 [P] Create custom hooks (ui/src/lib/hooks.ts): useKitchen, useAuth, useAsync
- [x] T048 Create home page redirect (ui/src/app/page.tsx) → /kitchen if authenticated, /auth/sign-in otherwise
- [x] T049 [P] Create auth pages skeleton (ui/src/app/(auth)/): sign-up, sign-in, forgot-password (reused from finance-dashboard)

### Create First Kitchen on Sign-Up

- [x] T050 Create sign-up flow (api/src/application/use_cases/kitchens.py): on user registration, auto-create "My Kitchen" with user as owner

**Checkpoint**: Foundation ready—authentication, database, domain models, adapters, and basic API are in place. User story implementation can now begin.

---

## Phase 3: User Story 1 - Add Recipe to Kitchen (Priority: P1) 🎯 MVP

**Goal**: Enable users to capture recipes from text, URLs, or photos and store them in their shared kitchen with automatically extracted ingredients and instructions.

**Independent Test**: User can paste recipe text, provide URL, or upload photo; system extracts and displays structured recipe with ingredients; recipe persists in kitchen and appears in recipe list.

### Tests for User Story 1 (OPTIONAL - provided as reference)

- [ ] T051 [P] [US1] Contract test: POST /kitchens/{id}/recipes/draft with text input (tests/contract/test_recipe_endpoints.py)
- [ ] T052 [P] [US1] Contract test: POST /kitchens/{id}/recipes/draft with URL input
- [ ] T053 [P] [US1] Contract test: POST /kitchens/{id}/recipes/draft with photo upload
- [ ] T054 [P] [US1] Integration test: capture recipe, verify ingredients stored (tests/integration/test_capture_recipe.py)
- [ ] T055 [US1] Unit test: TOON parser handles invalid input gracefully (tests/unit/test_toon.py)
- [ ] T055b [US1] Contract test: DELETE /recipes/{id} permissions — verify Member can delete own, Owner can delete any, Visitor cannot delete (tests/contract/test_recipe_delete_permissions.py)

### Implementation for User Story 1

#### API Endpoints

- [ ] T056 [US1] Implement POST /kitchens/{kitchen_id}/recipes/draft endpoint (api/src/api/routes/drafts.py): accept text/URL/photo, return RecipeDraft with extracted content
- [ ] T057 [US1] Implement POST /kitchens/{kitchen_id}/recipes endpoint: save draft → Recipe, create RecipeIngredients, link to ingredient catalog
- [ ] T058 [US1] Implement GET /kitchens/{kitchen_id}/recipes endpoint: list all recipes per kitchen
- [ ] T059 [US1] Implement GET /kitchens/{kitchen_id}/recipes/{recipe_id} endpoint: view recipe with ingredients
- [ ] T060 [US1] Implement DELETE /kitchens/{kitchen_id}/recipes/{recipe_id} endpoint: soft-delete recipe
- [ ] T061 [US1] Implement GET /kitchens/{kitchen_id}/recipes/{recipe_id}/sources endpoint: fetch original source metadata

#### Domain & Use Cases

- [ ] T062 [P] [US1] Implement CaptureRecipeUseCase (api/src/application/use_cases/capture_recipe.py): coordinate text/URL/photo extraction → RecipeDraft
- [ ] T063 [P] [US1] Implement RecipesUseCase (api/src/application/use_cases/recipes.py): create, list, retrieve, delete recipes
- [ ] T064 [US1] Implement recipe embedding on save (api/src/adapters/llm/gemini.py): embed recipe ingredients + instructions via Gemini Embeddings API, store in pgvector
- [ ] T065 [P] [US1] Implement source tracking (api/src/adapters/persistence/models.py): Source entity for text/URL/photo metadata

#### Text Recipe Extraction

- [ ] T066 [US1] Implement text recipe extractor (api/src/adapters/llm/gemini.py): call Gemini RecipeExtractor on pasted text, return ParseResult{is_recipe, reason, draft}
- [ ] T067 [US1] Add error handling for malformed input: if extraction fails, return RecipeDraft with error state; user can edit or retry

#### URL Recipe Extraction

- [ ] T068 [US1] Implement URL recipe extractor (api/src/adapters/web/page_fetcher.py + jsonld.py): fetch page, try JSON-LD first, fall back to text extraction
- [ ] T069 [US1] Validate URL safety: reject private IPs (127.0.0.*, 10.0.0.*, 172.16.*.*, 192.168.*.*, 169.254.*), enforce 10s timeout
- [ ] T070 [US1] Add robots.txt + User-Agent header (User-Agent: Melos-Recipe-Fetcher/1.0)

#### Photo Recipe Extraction

- [ ] T071 [US1] Implement photo upload endpoint (api/src/api/routes/drafts.py): accept multipart form-data with image file, validate MIME type (JPEG, PNG)
- [ ] T072 [US1] Store photo temporarily (api/src/adapters/persistence/models.py): Source.photo_filename
- [ ] T073 [US1] Implement vision-based extraction (api/src/adapters/llm/gemini.py): send image to Gemini Vision, OCR → recipe text → parse
- [ ] T074 [US1] Handle OCR failures: if vision fails, return error state; user can provide text instead
- [ ] T074b [US1] Implement OCR error handling UI (ui/src/components/recipe/RecipeCapturePhoto.tsx): show error message, allow user to paste text as fallback

#### Ingredient Matching & Catalog

- [ ] T075 [US1] Implement ingredient matching (api/src/application/use_cases/ingredients.py): when recipe saved, match extracted ingredients to kitchen catalog
- [ ] T076 [US1] Create missing ingredients on-demand (api/src/application/use_cases/ingredients.py): if ingredient not in catalog, auto-create with user category hint
- [ ] T077 [P] [US1] Create RecipeIngredient links (api/src/adapters/persistence/models.py): quantity, unit, is_linear flag per ingredient

#### Frontend - Add Recipe Flow

- [ ] T078 [US1] Create recipe capture page (ui/src/app/kitchen/recipes/add/page.tsx): tabbed form (text/URL/photo input)
- [ ] T079 [P] [US1] Create text recipe form (ui/src/components/recipe/RecipeCaptureText.tsx): textarea for pasting recipe
- [ ] T080 [P] [US1] Create URL recipe form (ui/src/components/recipe/RecipeCaptureUrl.tsx): URL input with validation
- [ ] T081 [P] [US1] Create photo upload form (ui/src/components/recipe/RecipeCapturePhoto.tsx): file input, preview
- [ ] T082 [US1] Create recipe draft viewer (ui/src/components/recipe/RecipeDraftViewer.tsx): display extracted ingredients, instructions; allow user edits
- [ ] T083 [US1] Create recipe form (ui/src/components/recipe/RecipeForm.tsx): edit title, ingredients, instructions; save or discard
- [ ] T084 [US1] Create recipe list view (ui/src/app/kitchen/recipes/page.tsx): table of recipes per kitchen with title, yield, cook time, actions

#### Frontend - View Recipe

- [ ] T085 [US1] Create recipe detail page (ui/src/app/kitchen/recipes/[id]/page.tsx): show recipe, ingredients with quantities, instructions
- [ ] T086 [US1] Create recipe card component (ui/src/components/recipe/RecipeCard.tsx): preview card (title, image placeholder, yield, time)
- [ ] T087 [US1] Add delete recipe action (ui/src/components/recipe/): confirm dialog, call DELETE endpoint

**Checkpoint**: At this point, users can add recipes to their kitchen from any source (text/URL/photo), and the recipes are stored with structured ingredients. Recipe list is viewable. This is the core MVP feature.

---

## Phase 4: User Story 2 - View Kitchen Inventory & Recipes (Priority: P1)

**Goal**: Display all recipes and ingredients in the kitchen with visibility into what's available and what's needed.

**Independent Test**: Kitchen contains multiple recipes; user opens kitchen view and sees all recipes and ingredients; ingredient catalog aggregates duplicate names; shared membership shows all recipes regardless of who added them.

### Tests for User Story 2 (OPTIONAL)

- [ ] T088 [P] [US2] Contract test: GET /kitchens/{id} returns all recipes and ingredients (tests/contract/test_kitchen_endpoints.py)
- [ ] T089 [P] [US2] Contract test: GET /kitchens/{id}/ingredients lists deduplicated ingredients
- [ ] T090 [US2] Integration test: ingredient catalog merges overlapping names (tests/integration/test_ingredient_catalog.py)

### Implementation for User Story 2

#### API Endpoints

- [ ] T091 [US2] Implement GET /kitchens/{kitchen_id} endpoint (api/src/api/routes/kitchens.py): return kitchen overview with recipe count, ingredient count, member list
- [ ] T092 [US2] Implement GET /kitchens/{kitchen_id}/ingredients endpoint: list all ingredients in kitchen catalog with categories
- [ ] T093 [US2] Implement GET /kitchens/{kitchen_id}/categories endpoint: list ingredient categories
- [ ] T094 [US2] Implement PUT /kitchens/{kitchen_id}/ingredients/{ingredient_id} endpoint: update ingredient canonical name or category

#### Ingredient Aggregation Logic

- [ ] T095 [US2] Implement ingredient aggregation (api/src/application/use_cases/ingredients.py): compute canonical names, merge aliases
- [ ] T096 [US2] Implement ingredient matching service (api/src/domain/ingredient_catalog.py): normalize names for aggregation (lowercase, strip whitespace, fuzzy match)

#### Frontend - Kitchen Overview

- [ ] T097 [US2] Create kitchen overview page (ui/src/app/kitchen/page.tsx): dashboard showing recipes, ingredients, member count
- [ ] T098 [P] [US2] Create kitchen stats section (ui/src/components/kitchen/KitchenOverview.tsx): recipe count, ingredient count, member list
- [ ] T099 [P] [US2] Create recipe list in overview (ui/src/components/recipe/RecipeGrid.tsx): grid/list of recipe cards

#### Frontend - Ingredient Catalog

- [ ] T100 [US2] Create ingredient catalog page (ui/src/app/kitchen/ingredients/page.tsx): list all ingredients with categories
- [ ] T101 [US2] Create ingredient card (ui/src/components/ingredient/IngredientCard.tsx): display name, category, unit, aliases
- [ ] T102 [US2] Create ingredient detail page (ui/src/app/kitchen/ingredients/[id]/page.tsx): show full ingredient info, recipes using it
- [ ] T103 [US2] Implement ingredient search/filter (ui/src/components/ingredient/IngredientList.tsx): search by name, filter by category

**Checkpoint**: Users can view their complete kitchen inventory—all recipes and ingredients are visible, aggregated, and categorized. Shared membership allows any member to see recipes added by others.

---

## Phase 5: User Story 3 - Generate Consolidated Shopping List (Priority: P1)

**Goal**: Generate a single merged and scaled shopping list from selected recipes for a given number of people.

**Independent Test**: Select 2+ recipes, specify headcount, generate list; verify quantities are merged (same ingredient summed), scaled (×headcount/yield), and grouped by category.

### Tests for User Story 3 (OPTIONAL)

- [ ] T104 [P] [US3] Contract test: POST /kitchens/{id}/shopping-list generates list (tests/contract/test_shopping_list_endpoints.py)
- [ ] T105 [P] [US3] Unit test: cart.py scaling logic (tests/unit/test_cart.py): verify quantity scaling for common units (cup, tbsp, tsp, oz, lb) with ±5% accuracy. Test merging, non-linear flag handling. Document conversion table.
- [ ] T106 [US3] Integration test: E2E shopping list generation (tests/integration/test_shopping_list.py)

### Implementation for User Story 3

#### Domain Logic

- [ ] T107 [P] [US3] Implement ShoppingCart (api/src/domain/cart.py): consolidate, scale, merge recipe ingredients
  - Input: recipes[], headcount, kitchen catalog
  - Output: aggregated items sorted by category
  - Logic: for each recipe, scale all items by (headcount / recipe.yield_servings), merge by ingredient_id, sum quantities
  - Non-linear items (is_linear=False) should be flagged for user review
- [ ] T108 [P] [US3] Implement shopping list rendering (api/src/domain/cart.py): group items by category, format for display/export

#### API Endpoints

- [ ] T109 [US3] Implement POST /kitchens/{kitchen_id}/shopping-list endpoint (api/src/api/routes/shopping_list.py): accept recipe_ids[], headcount, return ShoppingListResponse
- [ ] T110 [US3] Implement GET /kitchens/{kitchen_id}/shopping-lists endpoint: list saved shopping lists (for future reference)
- [ ] T111 [US3] Implement GET /kitchens/{kitchen_id}/shopping-lists/{list_id} endpoint: retrieve saved list
- [ ] T112 [US3] Implement POST /kitchens/{kitchen_id}/shopping-lists/{list_id}/export endpoint: export as PDF or markdown

#### PDF Export

- [ ] T113 [US3] Implement shopping list PDF renderer (api/src/adapters/pdf/weasyprint.py): render shopping_list.html template with consolidated items, grouped by category
- [ ] T114 [US3] Add kitchen name, generated date, headcount to PDF template
- [ ] T115 [US3] Test PDF output manually: verify layout, grouping, quantities

#### Frontend - Shopping List Generator

- [ ] T116 [US3] Create shopping list page (ui/src/app/kitchen/shopping-list/page.tsx): recipe selector (checkboxes), headcount input, generate button
- [ ] T117 [US3] Create recipe selector component (ui/src/components/shopping/RecipeSelector.tsx): checkboxes for recipes, search/filter
- [ ] T118 [US3] Create shopping list viewer (ui/src/components/shopping/ShoppingListViewer.tsx): display consolidated list, grouped by category
- [ ] T119 [US3] Implement quantity scaling UI (ui/src/components/shopping/): flag non-linear items with warning "Please review this item"
- [ ] T120 [US3] Implement export button (ui/src/components/shopping/ExportButton.tsx): download as PDF

**Checkpoint**: Users can generate complete, merged shopping lists scaled to their household size, export as PDF, and use for shopping.

---

## Phase 6: User Story 4 - Answer Questions About Kitchen (Priority: P2)

**Goal**: Enable users to ask natural-language questions about their kitchen and get answers grounded in kitchen data.

**Independent Test**: Kitchen has recipes and ingredients; user asks "what meals can we make?", "do we have eggs?"; system returns accurate answers based on kitchen state.

### Tests for User Story 4 (OPTIONAL)

- [ ] T121 [P] [US4] Contract test: POST /kitchens/{id}/conversations endpoint (tests/contract/test_conversation_endpoints.py)
- [ ] T122 [P] [US4] Integration test: Kitchen Assistant Q&A (tests/integration/test_conversations.py)
- [ ] T123 [US4] Unit test: TOON context serialization (tests/unit/test_toon.py)

### Implementation for User Story 4

#### Domain & Use Cases

- [ ] T124 [US4] Implement ConversationUseCase (api/src/application/use_cases/conversations.py): create conversation, add messages, get chat history. Support expected question types: fact lookup ("Do we have eggs?"), meal suggestions ("What meals can we make?"), ingredient computation ("How much flour do we need?").
- [ ] T125 [US4] Implement Kitchen Assistant logic (api/src/adapters/llm/gemini.py): embed query, search pgvector, build TOON context, call ChatModel
- [ ] T126 [US4] Implement context building (api/src/application/use_cases/conversations.py): serialize top-5 similar recipes as TOON, include kitchen catalog, last 6 messages

#### API Endpoints

- [ ] T127 [US4] Implement POST /kitchens/{kitchen_id}/conversations endpoint (api/src/api/routes/conversations.py): create conversation, return conversation_id
- [ ] T128 [US4] Implement POST /kitchens/{kitchen_id}/conversations/{conversation_id}/messages endpoint: send message (user), get response (assistant with cited_recipe_ids)
- [ ] T129 [US4] Implement GET /kitchens/{kitchen_id}/conversations endpoint: list conversations
- [ ] T130 [US4] Implement GET /kitchens/{kitchen_id}/conversations/{conversation_id}/messages endpoint: get conversation history

#### LLM Integration

- [ ] T131 [US4] Implement Kitchen Assistant system prompt (api/src/adapters/llm/prompts.py): grounded in TOON context, cite specific recipes, handle unknown cases
- [ ] T132 [US4] Implement embeddings search (api/src/adapters/llm/gemini.py): embed query using Gemini Embeddings API, query pgvector, return top-5 recipes
- [ ] T133 [US4] Implement response validation (api/src/application/use_cases/conversations.py): verify cited_recipe_ids exist in context, strip invalid citations
- [ ] T134 [US4] Add conversation history context (api/src/application/use_cases/conversations.py): include last 6 messages to prevent drift

#### Frontend - Conversation UI

- [ ] T135 [US4] Create ask page (ui/src/app/kitchen/ask/page.tsx): conversation list on left, chat on right
- [ ] T136 [US4] Create conversation view (ui/src/components/ask/ConversationView.tsx): message history, timestamp, author (user/assistant)
- [ ] T137 [US4] Create ask form (ui/src/components/ask/AskForm.tsx): text input, send button, loading state
- [ ] T138 [US4] Display cited recipes (ui/src/components/ask/): show recipe cards inline when assistant cites them
- [ ] T139 [US4] Implement conversation list (ui/src/components/ask/): list conversations, delete, create new

**Checkpoint**: Users can ask their kitchen questions and get grounded, accurate answers with recipe citations.

---

## Phase 7: User Story 5 - Manage Shared Kitchen & Members (Priority: P2)

**Goal**: Enable kitchen owners to invite household members and set role-based permissions.

**Independent Test**: Owner invites member by email, member receives invite, member accepts and joins kitchen with member-level permissions; visitor can view but not edit; owner can remove members.

### Tests for User Story 5 (OPTIONAL)

- [ ] T140 [P] [US5] Contract test: POST /kitchens/{id}/invites endpoint (tests/contract/test_member_endpoints.py)
- [ ] T141 [P] [US5] Contract test: GET /kitchens/{id}/members endpoint
- [ ] T142 [US5] Integration test: role-based access control (tests/integration/test_members.py)

### Implementation for User Story 5

#### Domain & Use Cases

- [ ] T143 [US5] Implement InvitesUseCase (api/src/application/use_cases/invites.py): create invite, accept invite, validate tokens, enforce expiry
- [ ] T144 [US5] Implement MembersUseCase (api/src/application/use_cases/kitchens.py): list members, change role, remove member
- [ ] T145 [US5] Implement permission checks: Visitor=view, Member=add/edit recipes, Owner=manage kitchen + members (api/src/api/security.py)

#### API Endpoints

- [ ] T146 [US5] Implement POST /kitchens/{kitchen_id}/invites endpoint (api/src/api/routes/invites.py): owner sends invite (email, role), return invite token
- [ ] T147 [US5] Implement GET /kitchens/{kitchen_id}/invites endpoint: list pending invites (owner only)
- [ ] T148 [US5] Implement POST /invites/{token}/accept endpoint: accept invite by token, create Member, set joined_at
- [ ] T149 [US5] Implement GET /kitchens/{kitchen_id}/members endpoint: list members with roles
- [ ] T150 [US5] Implement PUT /kitchens/{kitchen_id}/members/{user_id} endpoint: change member role (owner only)
- [ ] T151 [US5] Implement DELETE /kitchens/{kitchen_id}/members/{user_id} endpoint: remove member, soft-delete is_active (owner only)

#### Invite Workflow & Email

- [ ] T152 [US5] Implement invite token generation (api/src/adapters/persistence/repositories.py): UUID token, 7-day expiry. Follow finance-dashboard pattern.
- [ ] T153 [US5] Implement invite email (api/src/adapters/email/): send invite link to invitee (reuse finance-dashboard email service and SMTP settings)
- [ ] T154 [US5] Create accept invite page (ui/src/app/(auth)/accept-invite/[token]/page.tsx): display kitchen name, show join button; if not logged in, sign up first (uses invite_token parameter)
- [ ] T155b [US5] Implement kitchen deletion (owner only): DELETE /kitchens/{id} endpoint with owner-only permission check. Note: Members can only EXIT (leave) kitchen, not delete it (api/src/api/routes/kitchens.py)

#### Frontend - Member Management

- [ ] T155 [US5] Create members page (ui/src/app/kitchen/members/page.tsx): list members, owner actions (remove, change role)
- [ ] T156 [US5] Create member list (ui/src/components/kitchen/MemberList.tsx): table of members with roles, actions
- [ ] T157 [US5] Create invite form (ui/src/app/kitchen/members/invite/page.tsx): email input, role selector, send invite button
- [ ] T158 [US5] Implement role change UI (ui/src/components/kitchen/): dropdown to change role (owner only)

**Checkpoint**: Kitchen owners can invite members, manage roles, and control access. Multi-user households are now fully supported.

---

## Phase 8: User Story 6 - Standardize Ingredient Names Across Kitchen (Priority: P3)

**Goal**: Help users consolidate ingredient name variants into canonical names.

**Independent Test**: Multiple recipes use "flour", "all-purpose flour", "APF"; user reviews ingredient catalog and merges them under "Flour - All Purpose"; future recipes with similar names are matched to canonical.

### Tests for User Story 6 (OPTIONAL)

- [ ] T159 [P] [US6] Unit test: ingredient name matching algorithm (tests/unit/test_ingredient_catalog.py)
- [ ] T160 [P] [US6] Integration test: suggest merges, user confirms (tests/integration/test_ingredient_standardization.py)

### Implementation for User Story 6

#### Domain Logic

- [ ] T161 [US6] Implement ingredient fuzzy matching (api/src/domain/ingredient_catalog.py): suggest candidates for merging (cosine similarity on names)
- [ ] T162 [US6] Implement alias management (api/src/domain/ingredient_catalog.py): aliases array on Ingredient, match variants to canonical

#### API Endpoints

- [ ] T163 [US6] Implement GET /kitchens/{kitchen_id}/ingredients/suggestions endpoint: return merge suggestions (variant names, matched canonical)
- [ ] T164 [US6] Implement POST /kitchens/{kitchen_id}/ingredients/merge endpoint: merge two ingredients, redirect RecipeIngredients, update aliases
- [ ] T165 [US6] Implement PUT /kitchens/{kitchen_id}/ingredients/{ingredient_id}/aliases endpoint: add/remove aliases
- [ ] T166 [US6] Implement ingredient search/match (api/src/api/routes/ingredients.py): search for ingredient by name, return canonical matches

#### Frontend - Standardization UI

- [ ] T167 [US6] Create ingredient standardization page (ui/src/app/kitchen/ingredients/standardize/page.tsx): show suggestions, merge UI
- [ ] T168 [US6] Create merge dialog (ui/src/components/ingredient/MergeDialog.tsx): select canonical name, confirm merge, show affected recipes
- [ ] T169 [US6] Create alias editor (ui/src/components/ingredient/AliasEditor.tsx): add/remove aliases for ingredient

**Checkpoint**: Ingredient catalog is standardized, reducing duplicates and improving shopping list accuracy. Multi-variant recipes are consolidated under canonical names.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and overall system quality

### Testing & Documentation

- [ ] T170 [P] Run all contract tests end-to-end (tests/contract/) and verify API behavior
- [ ] T171 [P] Run all integration tests (tests/integration/) and verify workflows
- [ ] T172 [P] Run unit tests (tests/unit/) for domain logic
- [ ] T173 Write API documentation (docs/api.md or Swagger OpenAPI spec)
- [ ] T174 Write developer setup guide (docs/SETUP.md): local dev, Docker, running tests
- [ ] T175 Run quickstart.md validation: verify all 7 scenarios work end-to-end

### Frontend Polish

- [ ] T176 [P] [P] Responsive design: test on mobile (375px), tablet (768px), desktop (1024px+)
- [ ] T177 [P] [P] Accessibility: check WCAG 2.1 AA compliance (keyboard nav, screen reader, contrast)
- [ ] T178 [P] Error message clarity: ensure all API errors are user-friendly
- [ ] T179 Loading states: add spinners/skeletons for all async operations
- [ ] T180 Implement kitchen switcher (ui/src/components/kitchen/): users with multiple kitchens can switch

### Backend Hardening

- [ ] T181 [P] Input validation: enforce all data-model.md constraints (length, type, required fields)
- [ ] T182 [P] Error handling: standardize error responses (error code, message, details)
- [ ] T183 Logging: add structured logging for recipe extraction, shopping list generation, QA
- [ ] T184 Rate limiting: add rate limits to public endpoints (recipe capture, chat)
- [ ] T185 CORS: verify CORS settings allow frontend domain only

### Database & Performance

- [ ] T186 Verify database indexes exist per Phase 2 (T011)
- [ ] T187 [P] Profile query performance: shopping list generation (target: <10s for 5 recipes), embeddings search (target: <5s for 100 recipes). Use Python profiler; identify slow queries and optimize indexes.
- [ ] T188 [P] Load test: verify system handles 10+ concurrent users in single kitchen. Test on staging with production-like DB (100 recipes, 50 ingredients). Target endpoints: POST /recipes/draft, GET /shopping-list, POST /conversations/*/messages. Report p50/p95/p99 latencies for each endpoint.
- [ ] T189 Backup strategy: document database backup and recovery process

### Deployment

- [ ] T190 Docker images: api Dockerfile, ui Dockerfile, ensure services start
- [ ] T191 Environment variables: document all MELOS_* and NEXT_* vars
- [ ] T192 Database migrations: run Alembic on startup, verify schema is current
- [ ] T193 Health checks: verify /health endpoint and liveness probes
- [ ] T194 CI/CD: setup GitHub Actions workflow (lint, test, build, push)

### Final Validation

- [ ] T195 Run quickstart.md 7 scenarios with fresh database
- [ ] T196 Test all user stories independently: US1 → US3 (MVP), then US4 → US6
- [ ] T197 Performance validation: recipe capture <2min, shopping list <10s, QA <5s
- [ ] T198 Accessibility check: keyboard nav, screen reader, color contrast
- [ ] T199 Security review: SSRF safety, SQL injection, XSS, CSRF (if forms present)
- [ ] T200 Documentation complete: API docs, setup guide, architecture diagram

---

## Dependencies & Execution Order

### Phase Dependencies

```
Setup (Phase 1)
    ↓
Foundational (Phase 2) — BLOCKS all user stories
    ↓
├── US1: Add Recipe (Phase 3)
├── US2: View Kitchen (Phase 4)
├── US3: Shopping List (Phase 5) — depends on US1 + US3
├── US4: Ask Questions (Phase 6) — depends on US1
├── US5: Manage Members (Phase 7)
└── US6: Standardize Ingredients (Phase 8) — depends on US1
    ↓
Polish & Polish (Phase 9)
```

### Within-Phase Execution

**Phase 2 Parallelization** (Foundational):
- T009–T013: Database (sequential: setup → models → indexes → migration → seed)
- T014–T017: Auth (parallel: integrate → model → middleware → security)
- T018–T024: Domain models (parallel: all domains can be built in parallel)
- T025–T031: Adapters (parallel: Gemini, page fetcher, PDF renderer, template)
- T032–T038: Repositories (parallel: all repositories can be built in parallel)
- T039–T042: API foundation (parallel: app init, health, kitchens skeleton, validation)
- T043–T050: Frontend foundation (parallel: components, hooks, auth, home)

**Phase 3+ User Stories** (US1–US6):
- All user stories can run in **parallel** once Phase 2 is complete
- Within each story, tests → models → services → endpoints → UI (sequential dependencies)
- Frontend pages are independent per story

### Parallel Example: Phase 3 (US1)

```bash
Team can work on these in parallel:
T056–T061 (API endpoints) — different routes, no conflicts
T062–T065 (Domain/use cases) — different modules
T066–T074 (Extractors) — different adapters
T078–T087 (Frontend) — different pages/components
```

---

## Implementation Strategy

### MVP First (US1–US3 Only)

This is the minimum viable product that solves the core user problem:

1. ✅ Complete Phase 1: Setup
2. ✅ Complete Phase 2: Foundational
3. ✅ Complete Phase 3: US1 (Add Recipe)
4. ✅ Complete Phase 4: US2 (View Kitchen)
5. ✅ Complete Phase 5: US3 (Shopping List)
6. 🛑 **STOP and VALIDATE**: Test all 3 user stories end-to-end
7. Deploy/demo MVP (users can capture recipes, view kitchen, generate shopping lists)

### Post-MVP (US4–US6)

Add these features after MVP validation:

1. ✅ US4 (Ask Questions) — adds intelligence
2. ✅ US5 (Manage Members) — adds multi-user support
3. ✅ US6 (Standardize Ingredients) — improves data quality

### Incremental Delivery

Each user story is independently testable and deployable:

- **Sprint 1**: Setup + Foundational → infrastructure ready
- **Sprint 2**: US1 → users can add recipes
- **Sprint 3**: US2 + US3 → users can plan meals
- **Sprint 4**: US4 → intelligent meal planning assistant
- **Sprint 5**: US5 → multi-user households
- **Sprint 6**: US6 → ingredient standardization

### Parallel Team Strategy

With 3 developers on this feature:

1. **Developer A** (Backend core): Phase 2 foundational + domain models
2. **Developer B** (API): Phase 3 + Phase 4 endpoints (US1, US2)
3. **Developer C** (Frontend): Phase 3 + Phase 4 UI (US1, US2)

Once Foundational is complete:

- **A** → US4 (Chat/embeddings, complex domain)
- **B** → US5 (Members/invites API)
- **C** → US6 (Ingredient standardization UI)

---

## Success Criteria per Story

### US1 - Add Recipe
- [ ] ✅ Can add recipe from text, URL, photo
- [ ] ✅ Ingredients are extracted and stored
- [ ] ✅ RecipeIngredients link to kitchen ingredient catalog
- [ ] ✅ Recipe appears in kitchen recipe list

### US2 - View Kitchen
- [ ] ✅ Kitchen overview shows recipe count, ingredient count, members
- [ ] ✅ Recipe list is complete and searchable
- [ ] ✅ Ingredient catalog aggregates duplicates
- [ ] ✅ All members see the same data

### US3 - Shopping List
- [ ] ✅ Select recipes and headcount → consolidated list generated
- [ ] ✅ Quantities are merged (sum by ingredient)
- [ ] ✅ Quantities are scaled (×headcount/yield)
- [ ] ✅ Items grouped by category
- [ ] ✅ PDF export works

### US4 - Ask Questions
- [ ] ✅ Ask natural-language question
- [ ] ✅ Answer is grounded in kitchen recipes/ingredients
- [ ] ✅ Citations show relevant recipes
- [ ] ✅ Conversation history persists

### US5 - Manage Members
- [ ] ✅ Owner can send invite (email)
- [ ] ✅ Member receives email with link
- [ ] ✅ Member accepts → joins with member role
- [ ] ✅ Owner can change roles, remove members
- [ ] ✅ Visitor/Member/Owner permissions enforced

### US6 - Standardize Ingredients
- [ ] ✅ Ingredient merge suggestions shown
- [ ] ✅ User can merge duplicate ingredients
- [ ] ✅ Aliases are stored and searched
- [ ] ✅ Shopping lists use canonical names

---

## Notes & Constraints

- **No workers/queues**: All operations are synchronous (recipe extraction, embeddings, PDF generation)
- **No OAuth**: Session-based auth only
- **No metric conversion**: US measurements only; future consideration
- **No dietary filtering**: Ingredient substitution out of scope for v1
- **Ingredient scaling**: Linear only; non-linear items flagged for user review
- **Kitchen ownership**: 1 owner per kitchen; no complex org structures
- **Performance targets**: Recipe capture <2min, shopping list <10s, QA <5s, 10+ concurrent users
- **Data isolation**: kitchen_id on all tables; non-members get 404
- **Audit trail**: Basic (created_at, updated_at); detailed audit out of scope for v1

---

## Task Checklist Status

**Total Tasks**: 200

**Phase Breakdown**:
- Phase 1 Setup: 8 tasks
- Phase 2 Foundational: 42 tasks
- Phase 3 US1: 30 tasks
- Phase 4 US2: 13 tasks
- Phase 5 US3: 20 tasks
- Phase 6 US4: 19 tasks
- Phase 7 US5: 15 tasks
- Phase 8 US6: 9 tasks
- Phase 9 Polish: 31 tasks

**Parallelizable Tasks** [P]: ~45 tasks can run in parallel

**MVP Scope** (US1–US3): 103 tasks
**Extended Scope** (US4–US6): 43 tasks
**Polish**: 31 tasks (optional for v1)

---

**Ready to start Phase 1: Setup.** Each task is specific, includes file paths, and can be independently validated.
