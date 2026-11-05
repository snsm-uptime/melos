# Implementation Plan: Shopping by Store

**Branch**: `070-shopping-by-store` (story S-070) | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/070-shopping-by-store/spec.md`

## Summary

Three parts on top of the saved shopping list (S-025), the ingredient catalog (S-018) and the side panel (S-064):

1. **Bought**: a `bought` flag on `shopping_list_item`, toggled by any kitchen member on the active list, carried across cart refreshes by a pure domain rule, frozen by Done.
2. **Places per person**: seven default places as fixed keys in code (names translated in the UI), custom places in a new `place` table, and one person's choice per normalized ingredient name in `ingredient_place`. No row means Supermarket. A one-shot copy replaces a person's places with another member's.
3. **UI**: an "Ingredients" side-panel entry opening `/ingredients` (catalog with place pickers and place management), store tabs with "not bought" counts on the active and closed lists, a bought toggle per line, and an optional place picker when adding an item by hand.

The list read resolves each item's place **for the viewer**, so the same list shows different tabs to different members (FR-010). Details in [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.12 (api), TypeScript with Next.js 16 and React 19 (ui)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, Pydantic (api); Tailwind 4 (ui). No new dependency.

**Storage**: PostgreSQL. Migration `0018_shopping_places`: `shopping_list_item.bought`, tables `place` and `ingredient_place`.

**Testing**: pytest (domain pure, application with fake ports, HTTP against Postgres in the Compose test overlay); vitest for components; browser walk per quickstart.

**Target Platform**: the existing Compose stack (db, api, ui, mcp).

**Project Type**: web application (api + ui, BFF routes under `ui/app/api`).

**Performance Goals**: SC-001 toggle shown in under 0.5 s (optimistic UI); SC-005 a 100-item list with tabs in under 1 s; place resolution for a list is one extra query.

**Constraints**: hexagonal layers (constitution 3); membership checks in `application/` with 404 for non-members; the auth layer is not touched (places hang off `users.id` by FK only).

**Scale/Scope**: at most 30 custom places per person; a few hundred ingredient names per person; lists up to about 100 items.

## Constitution Check

*GATE: checked before Phase 0 and again after Phase 1.*

| Principle | Check | Result |
|---|---|---|
| 1 Simplicity and reuse | Default places are code constants, not rows; no new service, queue or worker; reuses `normalize_name`, the side-panel entry and the S-025 routes | Pass |
| 2 Tech stack | No new library | Pass |
| 3 Hexagonal | Bought carry-over and place resolution are pure functions in `domain/`; use cases and ports in `application/`; SQL in `adapters/persistence/` | Pass |
| 4 Security and privacy | Places are private to a person; another person's places are readable only through the copy action, and only for someone who shares a kitchen or notebook with them (404 otherwise). No personal data in tests | Pass |
| 5 No AI shortcuts | No AI used | Pass |
| 6 Testing | Domain, application and HTTP tests listed in quickstart; schema guard test updated for the new tables | Pass |
| 7 Deployment | One Alembic migration with downgrade | Pass |
| 8 Git | Built on its own branch, small commits | Pass |
| 9 Product scope | S-070 is in the backlog with a spec; no MVP-era rule is lifted | Pass |

Auth layer: untouched. `users` gains no column.

**Post-design re-check**: Pass. Nothing in data-model.md or contracts/ changes the table above.

## Project Structure

### Documentation (this feature)

```text
specs/070-shopping-by-store/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── shopping-list.md
│   └── places.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
api/
├── domain/
│   ├── places.py                 # new: default keys, name rules, resolve_place(), Supermarket fallback
│   └── shopping_list.py          # SavedLine.bought; carry_bought(old, new)
├── application/
│   ├── places.py                 # new: list/add/rename/delete places, set ingredient place, catalog page, copy from member
│   ├── ports.py                  # PlaceRepository port
│   └── shopping_list.py          # SetItemBoughtService; views carry place per item for the viewer; hand add with place
├── adapters/persistence/
│   ├── models.py                 # PlaceModel, IngredientPlaceModel, ShoppingListItemModel.bought
│   ├── places.py                 # new: SqlAlchemyPlaceRepository
│   ├── shopping_lists.py         # bought column; replace_cart_lines carries bought
│   └── migrations/versions/0018_shopping_places.py
└── api/
    ├── routes/places.py          # new: /me/places, /me/ingredient-places, /me/place-sources, /me/places/copy
    ├── routes/shopping_list.py   # PATCH item bought; place on add
    └── schemas/{places,shopping_list}.py

ui/
├── app/ingredients/page.tsx      # new catalog page
├── app/api/me/places/...         # new BFF routes
├── app/api/kitchens/[kitchenId]/shopping-list/items/[itemId]/route.ts   # add PATCH
├── app/kitchens/[kitchenId]/shopping-lists/...   # tabs + bought toggle (active and closed)
├── components/SidePanel/SidePanel.tsx            # "Ingredients" entry
├── components/StoreTabs/                         # new tab strip
└── lib/i18n/places.ts                            # default place names, en and es
```

**Structure Decision**: the existing api + ui layout; one new domain module, one new use-case module, one new repository, one new route module, one new page.

## Complexity Tracking

No constitution violations.
