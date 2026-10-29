# Implementation Plan: Shared Kitchen Cart with People, Meals, Scale Factor and Single-Editor Locks

**Branch**: `022-shared-cart` (spec folder `022-shared-cart`, story S-022; branch not created by this command) | **Date**: 2026-10-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/022-shared-cart/spec.md`

## Summary

Every kitchen gets one cart shared by its members: a people number (by default the kitchen's member count) and a set of kitchen-notebook recipes, each with a meals number. The Cart page shows each recipe's scale factor, people × meals / base servings. One member at a time edits the cart, through a draft held on the server; the same single-editor lock is added to recipe Edit (amends spec 027). A lock belongs to the editor's session and ends on save, discard, sign-out, session end, **5 minutes without activity**, or loss of access, which deletes it for good. While editing, the member sees an editing bar on the Cart page, fixed above the tab bar. Cards and the recipe page add and remove with a cart-icon button (a "+" that turns into an "×" when the recipe is in the cart); a refused add, the idle warning and "changes discarded" appear as toasts above the tab bar (UI clarification 2026-10-29, research R13, R14).

Technical approach: one Alembic migration adds `cart`, `cart_item`, `cart_edit_lock`, `recipe_edit_lock` and `recipe.cart_add_count`. Both lock tables reference `sessions.id` with `ON DELETE CASCADE`, so sign-out (which deletes the session row) frees locks with no change to the auth layer; an expired session or a `last_active_at` older than 5 minutes is treated as no lock on every read (research R10). Lock rows also reference the membership that allowed them (`ON DELETE CASCADE`), and archiving a kitchen deletes its locks, so lost access ends a lock for good (research R11). Concurrent lock attempts are serialized by `SELECT … FOR UPDATE` on the cart or recipe row. Scaling and the default people rule are pure functions in a new `domain/cart.py`. Cart entries and locks cascade from `recipe`, `notebook` and `kitchens` deletes.

## Technical Context

**Language/Version**: Python 3.12 (`api/`, uv). TypeScript, Next.js 16 App Router, React 19, Tailwind 4 (`ui/`).

**Primary Dependencies**: Existing only. api: SQLAlchemy, FastAPI, Alembic, `NotebookRepository.facts_for`, `domain/notebook.can_write_recipes`, spec 027 `recipe_manage.py`. ui: `ActionDialog`, `IconButton`, `AppShell`/`TabBar`, `RecipeCard`, `RecipeDetail`, `RecipeEdit`, `ui/lib/i18n`. **No new library** (the toast is a small in-house component, R13).

**Storage**: PostgreSQL 16. New tables `cart`, `cart_item`, `cart_edit_lock`, `recipe_edit_lock`; new column `recipe.cart_add_count`. Migration `0007_cart_and_edit_locks` (research R1–R4).

**Testing**: pytest + ruff (api): pure domain tests (`scale_factor`, `effective_people`, bounds), application tests with fake repositories (lock rules, draft save, add count), integration tests in the Compose test overlay (cascades, sign-out frees lock, concurrent acquire, 404 for non-members, archived read-only). The schema guard test in `tests/test_recipe_manage_integration.py` gets `cart_item` and `recipe_edit_lock` added. vitest + eslint + typecheck (ui). Browser walk with two accounts (constitution §6).

**Target Platform**: Linux containers under Docker Compose; mobile-first browser ui.

**Project Type**: Web application (hexagonal FastAPI api + Next.js BFF ui).

**Performance Goals**: Cart of 100 recipes read with all factors in under 1 s end to end (SC-008): one query for the cart and its recipes' base servings, one for the member count.

**Constraints**:
- `domain/` stays free of I/O (constitution §3).
- Non-members get 404 for every cart route; archived kitchens are read-only (spec FR-010, FR-011).
- The auth layer is not modified (constitution §1): locks read `sessions` rows through a new adapter query, they do not change `sessions.py`, the session store port or the auth routes.
- People and meals: whole numbers 1–99.
- Logs carry outcomes and counts only.

**Scale/Scope**: One kitchen per request. 7 cart routes, 2 recipe lock routes, 2 changed recipe routes; one new domain module, two new application modules; one Cart page and lock notices on recipe pages.

## Constitution Check

*GATE: passed before Phase 0 and re-checked after Phase 1 design.*

| Principle | Result |
|---|---|
| 1. Simplicity and reuse | Pass. No new service or library. Locks reuse the existing session rows. **Auth layer untouched** (R3): the lock tables only hold a foreign key to `sessions`; the new `require_session_ref` dependency was approved by the owner on 2026-10-29. |
| 2. Tech stack | Pass. No new dependency. |
| 3. Hexagonal | Pass. Scale and people rules in `domain/cart.py`; lock and draft rules in `application/`; SQL and row locks in `adapters/persistence/`; kitchen access in `application/` with 404 for non-members. |
| 4. Security and privacy | Pass. A draft is visible only to its session; the editor's alias is shown only to people who can already see the item. |
| 5. No AI shortcuts | Pass. No model involved; no unit conversion. |
| 6. Testing | Pass. Domain → application (fakes) → integration (Compose) → ui → two-account browser walk. |
| 7. Deployment | Pass. Nothing added to Compose or server config. |
| 8. Git discipline | Pass. Schema change through one Alembic migration with downgrade. |
| 9. Scope | Pass. S-022 is Must (Appendix C: cart). The recipe lock was asked for by the owner in spec clarification 2026-10-29. Shopping list, export, MCP are out. |

Post-design re-check: unchanged. Re-checked after the UI clarification (2026-10-29): still passes. The toast is an in-house ui component (no library, §2); `AppShell` gains only the toast viewport, no service, layer or api change (§1, §3); all new text is in `ui/lib/i18n/cart.ts`, es and en (§9). Complexity Tracking lists one deliberate trade-off.

## Project Structure

### Documentation (this feature)

```text
specs/022-shared-cart/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cart-api.md
│   ├── recipe-lock-api.md
│   └── cart-ui.md
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks, not created here
```

### Source Code (repository root)

```text
api/
├── domain/
│   ├── cart.py                     # NEW: effective_people, scale_factor, format_factor, bounds, LOCK_IDLE
│   └── errors.py                   # + CartLockedError, RecipeLockedError, NotLockHolderError, CartValueError
├── application/
│   ├── ports.py                    # + CartRepository, EditLockRepository, value types
│   ├── carts.py                    # NEW: GetCart, StartCartEdit, ReplaceCartDraft, AddToCartDraft,
│   │                               #      SaveCartDraft, DiscardCartDraft
│   ├── recipe_locks.py             # NEW: AcquireRecipeLock, ReleaseRecipeLock, lock_view helper
│   ├── kitchens.py                 # ArchiveKitchenService also deletes the kitchen's locks (R11)
│   └── recipe_manage.py            # GetRecipe returns editor; UpdateRecipe needs and releases lock;
│                                   # DeleteRecipe refused while another holds the lock
├── adapters/persistence/
│   ├── models.py                   # + CartModel, CartItemModel, CartEditLockModel, RecipeEditLockModel,
│   │                               #   RecipeModel.cart_add_count
│   ├── carts.py                    # NEW: cart read/create, FOR UPDATE, save draft, bump counts
│   ├── edit_locks.py               # NEW: session id from token, live lock reads, acquire/release
│   └── migrations/versions/0007_cart_and_edit_locks.py
├── api/
│   ├── deps.py                     # + require_session_ref (user id + session id), service providers
│   ├── routes/carts.py             # NEW: /kitchens/{id}/cart…
│   ├── routes/recipes.py           # + /recipes/{id}/edit-lock; PUT/DELETE map lock errors (409)
│   └── schemas/carts.py            # NEW
└── tests/                          # test_cart_domain.py, test_carts_application.py,
                                    # test_recipe_locks_application.py, test_carts_integration.py,
                                    # test_recipe_manage_integration.py (guard list)

ui/
├── app/
│   ├── kitchens/[kitchenId]/cart/page.tsx           # NEW Cart page
│   ├── api/kitchens/[kitchenId]/cart/…              # NEW BFF routes (contracts/cart-api.md)
│   ├── api/recipes/[recipeId]/edit-lock/route.ts    # NEW BFF
│   └── recipes/[recipeId]/edit/page.tsx             # acquires lock on open, releases on cancel/leave
├── components/
│   ├── Cart/                                        # NEW: CartView, CartEntryRow, CountField, EditorNotice,
│   │                                                #      CartEditingBar (Cart page only, above the tab bar, + idle warning)
│   ├── Toast/                                       # NEW: ToastProvider, useToast, viewport (R13)
│   ├── AppShell.tsx                                 # hosts the toast viewport above TabBar
│   ├── RecipeCard/RecipeCard.tsx                    # + cart-icon button on kitchen cards (R14)
│   └── RecipeDetail/                                # + Add/Remove cart action, lock notice, gated Edit/Delete
├── app/icons/CartPlusIcon.tsx                        # NEW: cart with "+", rotates to "×" when in cart (R14)
├── hooks/useLockKeepAlive.ts                         # NEW: activity-only keep-alive, idle warning (R10)
└── lib/cartClient.ts, lib/cartFactor.ts, lib/i18n/cart.ts (es + en)
```

**Structure Decision**: Extends the existing hexagonal api and BFF ui. The cart gets its own application module (`carts.py`) because its use cases are kitchen-scoped, unlike `recipe_manage.py`. Recipe locks get a small module (`recipe_locks.py`) that `recipe_manage.py` calls, so spec 027's services stay the single place a recipe is edited or deleted.

## Complexity Tracking

| Choice | Why needed | Simpler alternative rejected because |
|---|---|---|
| Server-held cart draft (`cart_edit_lock.draft`, JSON) | Spec US3: other members must keep seeing the saved cart while the editor changes it, and the draft must survive a closed tab within the session. | Client-only draft: lost on tab close and cannot be discarded by sign-out from another device. Writing each change straight to the cart: others would see unsaved changes. |
