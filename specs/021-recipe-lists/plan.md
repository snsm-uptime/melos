# Implementation Plan: Recipe Lists for a Personal Notebook and a Kitchen

**Branch**: `021-recipe-lists` (spec folder `021-recipe-lists`, story S-021) | **Date**: 2026-10-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/021-recipe-lists/spec.md`

## Summary

Members can finally see the recipes spec 020 stores. Two read routes return a page of recipe
cards: one for a single notebook the caller can read, one for all notebooks of a kitchen. Both
take a page number and a text filter (title or ingredient name, ignoring case and accents), return
12 cards newest first, and write nothing. The ui adds a notebook page (`/notebooks/[notebookId]`)
with the card grid, the filter and numbered pages; the kitchen page gains the same list for the
combined recipes; the notebook cards of spec 060 become links; and a personal Save now returns to
the notebook page.

Technical approach: no new table. One migration enables the `unaccent` extension so the filter
can ignore accents in SQL. A pure domain module normalizes the filter text and clamps the page. Two
use cases in `application/` check access (reusing spec 056) and call one new port,
`RecipeListRepository`, implemented in `adapters/persistence/`. The ui adds a client, two BFF
routes, a `RecipeCard`, a `RecipeList` and the page.

## Technical Context

**Language/Version**: Python 3.12 (`api/`, uv). TypeScript, Next.js 16 App Router, React 19, Tailwind 4 (`ui/`).

**Primary Dependencies**: Existing only. api: SQLAlchemy, FastAPI, `NotebookRepository.facts_for`, `AuthorizeKitchenAccessService`, `domain/ingredient_catalog.normalize_name`. ui: `NotebookCard`, `SavedNotice`, `notebooksClient` patterns. **No new library.**

**Storage**: PostgreSQL 16. No new table or column. Migration `0006_unaccent` runs `CREATE EXTENSION IF NOT EXISTS unaccent` (same pattern as the `vector` extension in `0002`). Existing `recipe`, `recipe_ingredient` and `users` tables are only read.

**Testing**: pytest + ruff (api): pure domain tests, application tests against a fake list repository, integration tests in the Compose test overlay against Postgres (filter, accents, paging, access, no writes), migration upgrade/downgrade check. vitest + eslint + typecheck (ui). Browser check of both lists (constitution §6).

**Target Platform**: Linux containers under Docker Compose; mobile-first browser ui.

**Project Type**: Web application (hexagonal FastAPI api + Next.js BFF ui).

**Performance Goals**: First page of a notebook or kitchen with up to 200 recipes in under 2 seconds end to end (SC-002); server side well under 300 ms with a filter.

**Constraints**:
- `domain/` stays free of I/O and SDK imports (constitution §3).
- Access is checked in `application/`; no access gives the same 404 as a missing notebook or kitchen (FR-010).
- Reads only: a list never creates a notebook, recipe or catalog entry (FR-012). The kitchen list does not call the first-open notebook creation of spec 056 FR-008a.
- The filter text is bound as a query parameter, with `%`, `_` and `\` escaped so it matches literally (constitution §4).
- Cards carry no detail link, cart checkbox or category data (FR-014).

**Scale/Scope**: One household, up to a few hundred recipes per list. 1 migration, 1 domain module, 2 use cases, 1 port and adapter, 2 routes; ui: client, 2 BFF routes, 2 components, 1 page, edits to 3 existing files. Test files for each.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| 1. Simplicity and reuse | No new service or library. Reuses notebook access, kitchen authorization and the name normalizer. | Pass |
| 2. Tech stack stability | SQLAlchemy, FastAPI, Alembic, Next.js as before. `unaccent` is a Postgres contrib extension, not a dependency. | Pass |
| 3. Hexagonal architecture | Normalizing and paging rules in `domain/`; access and use cases in `application/`; SQL in `adapters/persistence/`; routes only map errors. | Pass |
| 4. Security and privacy | Same 404 for missing and forbidden; filter bound as a parameter and wildcard-escaped; no real data in fixtures. | Pass |
| 5. No AI shortcuts | No AI call; read only. | Pass (n/a) |
| 6. Testing and quality | Domain tests first, application tests with a fake repository, integration on Postgres, vitest, browser check. | Pass |
| 7. Deployment | No deploy change; the extension ships in the migration. | Pass |
| 8. Git discipline | Schema change through Alembic `0006_unaccent` with a tested downgrade. | Pass |
| 9. Product scope | Recipe lists are a Must (PRD J3). Ingredient/author filters and frequency sort stay with S-047 (Should). | Pass |

**Re-check after design (Phase 1)**: unchanged, all Pass. The new surface is two `GET` routes that follow the auth, access and error pattern of the notebook read routes.

## Project Structure

### Documentation (this feature)

```text
specs/021-recipe-lists/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── list-api.md
│   └── list-ui.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks, not created here
```

### Source Code (repository root)

```text
api/
├── domain/recipe_search.py                         # new: search key, page clamp
├── application/recipe_lists.py                     # new: two use cases
├── application/ports.py                            # edit: RecipeListRepository, RecipeCardRow, RecipePage
├── adapters/persistence/recipe_lists.py            # new: SQL
├── adapters/persistence/migrations/versions/0006_unaccent.py
├── api/routes/notebooks.py                         # edit: two GET routes (before /{notebook_id})
├── api/schemas/recipe_lists.py                     # new: response models
├── api/deps.py                                     # edit: service providers
└── tests/                                          # test_recipe_search_domain.py, test_recipe_lists_application.py,
                                                    # test_recipe_lists_integration.py, test_unaccent_migration.py
ui/
├── app/api/notebooks/[notebookId]/recipes/route.ts
├── app/api/notebooks/kitchens/[kitchenId]/recipes/route.ts
├── app/notebooks/[notebookId]/page.tsx             # new notebook page
├── app/kitchens/KitchenNotebooksSection.tsx        # edit: cards link; add combined list
├── app/notebooks/NotebookTabScreen.tsx             # edit: cards link
├── components/NotebookCard/NotebookCard.tsx        # edit: optional href
├── components/RecipeCard/RecipeCard.tsx            # new
├── components/RecipeList/RecipeList.tsx            # new: filter, grid, pager, states
├── lib/recipesClient.ts                            # new
├── lib/i18n/recipeLists.ts                         # new: English messages
└── (capture return path)                           # edit: personal Save returns to /notebooks/{id}
```

**Structure Decision**: The existing web-application layout (hexagonal `api/` plus Next.js `ui/`). Routes sit in the existing `notebooks` router because they are reads of a notebook or kitchen; the list logic lives in its own `recipe_lists` module so `application/notebooks.py` does not grow.

## Complexity Tracking

No constitution violations. Nothing to justify.
