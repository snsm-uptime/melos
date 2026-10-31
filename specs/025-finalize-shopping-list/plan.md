# Implementation Plan: Saved Shopping List, Closed with Done

**Branch**: `025-finalize-shopping-list` (story S-025) | **Date**: 2026-10-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/025-finalize-shopping-list/spec.md`

## Summary

A kitchen gets one stored active shopping list. Saving the cart creates or refreshes its cart lines with the existing S-023 consolidation, members add and remove items by hand, and Done sets the closing date and makes the list read only. Closed lists can be browsed. Two new tables, one migration, no new service or library.

## Technical Context

**Language/Version**: Python 3.12 (`api/`, uv). TypeScript, Next.js 16 App Router, React 19, Tailwind 4 (`ui/`).

**Primary Dependencies**: Existing only: FastAPI, SQLAlchemy, Alembic, `domain/cart.py` (`build_shopping_list`), `domain/ingredient_catalog.py` (`normalize_name`).

**Storage**: PostgreSQL 16. New tables `shopping_list` and `shopping_list_item`, migration `0009_shopping_lists` (down revision `0008_cart_servings`). See [data-model.md](./data-model.md).

**Testing**: pytest + ruff (domain, application with fake ports, Compose integration, migration up/down/up); vitest, eslint, typecheck (ui); two-account browser walk ([quickstart.md](./quickstart.md)).

**Target Platform**: Linux containers under Docker Compose; mobile-first browser ui.

**Project Type**: Web application (hexagonal FastAPI api + Next.js BFF ui).

**Performance Goals**: A list from a 100-recipe cart opens in under 1 s (SC-005): stored lines are read in one query with no consolidation.

**Constraints**: `domain/` free of I/O; 404 for non-members; archived kitchens read only; logs carry outcomes and counts only; auth untouched; all new text in es and en.

**Scale/Scope**: One kitchen per request. 2 tables, 5 new shopping list routes, 1 extended cart save, 1 BFF extension, 1 new page.

## Constitution Check

*GATE: passed before Phase 0 and re-checked after Phase 1 design.*

| Principle | Result |
|---|---|
| 1. Simplicity and reuse | Pass. Reuses `build_shopping_list`; no new service or library. |
| 2. Tech stack | Pass. No new dependency. |
| 3. Hexagonal | Pass. List rules in `domain/`, access and flow in `application/`, SQL in `adapters/persistence/`. |
| 4. Security and privacy | Pass. 404 for non-members, also for a list of another kitchen. Hand-typed text renders as text. |
| 5. No AI shortcuts | Pass. No model; no unit conversion. |
| 6. Testing | Pass. All four layers plus the browser walk. |
| 7. Deployment | Pass. Nothing added to Compose or server config. |
| 8. Git discipline | Pass. Schema change through Alembic. |
| 9. Scope | Pass. S-025 is Must; S-024, S-031, S-032 and the rest of S-046 stay out. |

Post-design re-check: unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/025-finalize-shopping-list/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/shopping-list-api.md
└── checklists/requirements.md
```

### Source Code

```text
api/
├── domain/shopping_list.py                         # new: saved list rules
├── application/shopping_list.py                    # shared builder; read, add, remove, Done, history
├── application/carts.py                            # SaveCartService refreshes the list
├── application/ports.py                            # ShoppingListRepository
├── adapters/persistence/shopping_lists.py          # new
├── adapters/persistence/migrations/versions/0009_shopping_lists.py  # new
├── api/routes/shopping_list.py, api/schemas/shopping_list.py, api/deps.py
└── tests/
ui/
├── app/api/kitchens/[kitchenId]/shopping-list/...  # BFF: items, done
├── app/api/kitchens/[kitchenId]/shopping-lists/... # BFF: closed lists
├── app/kitchens/[kitchenId]/shopping-lists/...     # past lists pages
├── components/ShoppingList/                        # hand item form, Done, status
└── lib/shoppingListClient.ts, lib/i18n/shoppingList.ts
```

**Structure Decision**: Extend the existing shopping list modules; no new top-level folder.

## Complexity Tracking

No constitution violations.
