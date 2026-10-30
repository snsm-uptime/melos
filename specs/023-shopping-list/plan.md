# Implementation Plan: Consolidated Shopping List from the Kitchen Cart

**Branch**: `023-shopping-list` (story S-023) | **Date**: 2026-10-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/023-shopping-list/spec.md`

## Summary

The Cart page gets a shopping list below the cart's recipes. It is built fresh on every read from the cart and the recipes' ingredient lines, and is never stored. Each line is scaled by its recipe's factor, grouped by ingredient name and kind of measure (mass, volume, count), summed per unit without conversion, and shown with chips for the recipes it comes from. Vague lines go to a separate "Your call" section. The member who is editing the cart sees the list built from their own draft; everyone else sees the saved cart's list.

Technical approach: no schema change and no migration. The consolidation is a pure function in the existing `domain/cart.py` (exact `Fraction` arithmetic, sum first, `ceil` for counts, `format_factor` for amounts). One new use case, `GetShoppingListService` in `application/shopping_list.py`, checks kitchen access, picks the caller's draft or the saved cart, and loads ingredient lines through one new read-only port. One new route, `GET /kitchens/{id}/shopping-list`, returns structured data (names, amounts per unit, chips); the ui does the wording and the "Your call" heading in Spanish and English. The ui adds a `ShoppingListSection` to `CartScreen` that fetches the list again whenever the cart state changes (load, focus, draft PUT, save, discard).

## Technical Context

**Language/Version**: Python 3.12 (`api/`, uv). TypeScript, Next.js 16 App Router, React 19, Tailwind 4 (`ui/`).

**Primary Dependencies**: Existing only. api: SQLAlchemy, FastAPI, `domain/cart.py` (`scale_factor`, `format_factor`, `effective_people`), `application/ports.py` (`CartRepository`, `EditLockRepository`, `SessionRef`), `require_session_ref`. ui: `CartScreen`, `cartClient`, `forwardRecipeRequest`, `ui/lib/i18n`. **No new library.**

**Storage**: PostgreSQL 16, read only. Reads `cart`, `cart_item`, `cart_edit_lock` (the caller's draft), `recipe`, `recipe_ingredient`. **No migration**; nothing is written (FR-002, FR-014).

**Testing**: pytest + ruff (api): pure domain tests for the consolidation (AC5.1–AC5.4, rounding after sum, ordering, vague section, 20 hand-calculated carts for SC-004); application tests with fake ports (draft vs saved, dropped recipes, non-member 404, archived read); integration tests in the Compose test overlay (HTTP, non-member, other member sees saved cart while the editor sees the draft, read changes nothing, 100×20 read in few statements). vitest + eslint + typecheck (ui). Browser walk with two accounts (constitution §6).

**Target Platform**: Linux containers under Docker Compose; mobile-first browser ui.

**Project Type**: Web application (hexagonal FastAPI api + Next.js BFF ui).

**Performance Goals**: A cart of 100 recipes with 20 lines each (2000 lines) opens in under 1 s (SC-003): one query for all ingredient lines, a fixed number of other statements, and in-memory consolidation.

**Constraints**:
- `domain/` stays free of I/O (constitution §3). The consolidation takes plain values and returns plain values.
- No unit conversion or carry-over (constitution §5, PRD §4).
- Non-members and unknown kitchens get 404 (FR-012); an archived kitchen can still be read.
- The auth layer is not modified (§1). The route uses the existing `require_session_ref`.
- The route is read only: no lock is taken, no `last_active_at` is touched, no add count changes (FR-014).
- Logs carry outcomes and counts only (§4).

**Scale/Scope**: One kitchen per request. 1 new api route, 1 new use case, 1 new port, 1 extended domain module; 1 BFF route, 1 client module, 1 new ui section, 1 message set (es + en).

## Constitution Check

*GATE: passed before Phase 0 and re-checked after Phase 1 design.*

| Principle | Result |
|---|---|
| 1. Simplicity and reuse | Pass. No new service, table or library. Reuses the cart read, the lock/draft read and `require_session_ref` from spec 022. Auth layer untouched. |
| 2. Tech stack | Pass. No new dependency. |
| 3. Hexagonal | Pass. Consolidation, kinds, ordering and rounding are pure code in `domain/cart.py`; access checks and the draft-or-saved choice are in `application/shopping_list.py` (404 for non-members); the SQL read is in `adapters/persistence/`. |
| 4. Security and privacy | Pass. The draft is read only for the caller's own session; other members get the saved cart. Ingredient names, notes and titles are returned as data and rendered as text by React (no HTML injection). No personal data in tests. |
| 5. No AI shortcuts | Pass. No model involved. No conversion between units: `1 cup + 20 tbsp` stays as is. |
| 6. Testing | Pass. Domain → application (fakes) → integration (Compose) → ui → two-account browser walk. |
| 7. Deployment | Pass. Nothing added to Compose or server config. |
| 8. Git discipline | Pass. No schema change, so no Alembic migration. |
| 9. Scope | Pass. S-023 is Must (Appendix C: shopping list). Export (S-024), finalize (S-025), editing items (S-046) and MCP (S-032) stay out. |

Post-design re-check: unchanged. The design adds no table, service, library or auth change; all new ui text is in one new message set with both languages (spec 063 parity test).

## Project Structure

### Documentation (this feature)

```text
specs/023-shopping-list/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── shopping-list-api.md
│   └── shopping-list-ui.md
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks, not created here
```

### Source Code (repository root)

```text
api/
├── domain/
│   └── cart.py                       # + kinds and unit order, ScaledRecipe, ShoppingList types,
│                                     #   build_shopping_list, sort key (no I/O)
├── application/
│   ├── ports.py                      # + IngredientLineReader port, CartIngredientLine value type
│   └── shopping_list.py              # NEW: GetShoppingListService (access, draft-or-saved, facts, lines)
├── adapters/persistence/
│   └── carts.py                      # + SqlAlchemyIngredientLineReader (one query for all recipes)
├── api/
│   ├── deps.py                       # + get_get_shopping_list provider
│   ├── routes/shopping_list.py       # NEW: GET /kitchens/{id}/shopping-list
│   ├── schemas/shopping_list.py      # NEW: response models
│   └── main wiring                   # include the new router where the cart router is included
└── tests/                            # test_shopping_list_domain.py, test_shopping_list_application.py,
                                      # test_shopping_list_integration.py

ui/
├── app/api/kitchens/[kitchenId]/shopping-list/route.ts   # NEW BFF (GET)
├── components/ShoppingList/                              # NEW: ShoppingListSection, ShoppingLine,
│                                                         #      RecipeChips, index.ts (+ tests)
├── components/Cart/CartScreen.tsx                        # renders the section below CartView
├── lib/shoppingListClient.ts                             # NEW: fetch + types (+ test)
├── lib/shoppingListText.ts                               # NEW: line wording `{name}, {size} — {amounts}`
└── lib/i18n/shoppingList.ts                              # NEW: es + en; registered in parity.test.ts
```

**Structure Decision**: Extends the existing hexagonal api and BFF ui. The consolidation lives in `domain/cart.py` as the PRD and backlog require (§1.5 C, S-023). The use case gets its own module (`shopping_list.py`, named in PRD §1.3) because it is a read of a derived view, not a cart write; it reuses the cart ports instead of calling the cart services. The ingredient lines come through a separate small port so the existing `CartRepository` fakes in spec 022 tests do not change.

## Complexity Tracking

No constitution violations. One deliberate trade-off:

| Choice | Why needed | Simpler alternative rejected because |
|---|---|---|
| The ui fetches the list again after each saved draft change, instead of computing it in the browser | FR-001 says the editor's list follows the draft, and the rules (exact fractions, ceil after sum, ordering) must exist once, in `domain/cart.py`. | Computing in the ui would duplicate every rule in TypeScript and risk two answers for one cart. The cost is a short delay (the existing 300 ms draft debounce plus one request). |
