# Implementation Plan: Catalog Management (rename and merge ingredient names)

**Branch**: `043-catalog-rename-merge` (story S-043) | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/043-catalog-rename-merge/spec.md`

## Summary

People who can write to a notebook rename, merge and delete names in its ingredient catalog. For
bilingual users, two names in different languages ("cebolla", "onion") can be merged into one
ingredient, with a name variant per language. Recipes get a language. Each recipe line shows the
variant in its recipe's language, and the shopping list shows the variant in the viewer's
interface language. One merge applies to every notebook the person can write to that has both
names. The AI model suggests English and Spanish pairs, and the person confirms each one. Existing
recipes get a fallback language, and the model proposes a correction once for a person to apply.

Technical approach ([research.md](research.md)): lines keep carrying a plain name, always the
ingredient's **kept name**, so merge and rename rewrite `recipe_ingredient.name` (R1). Other names
live in a new `ingredient_name` table, and `ingredient.language` records the kept name's language
(R2). `recipe.language` is filled by a fallback rule in the migration and then an operator
command asks the model once and stores a proposal that a person applies or dismisses (R3). One pure `CatalogIndex` in
`domain/ingredient_catalog.py` gives every matching call site the other names (R4). Cart-based
shopping list items store their variants for display per viewer (R7). The pair suggester is a new
port with a Gemini adapter and a prompt file (R9).

## Technical Context

**Language/Version**: Python 3.12 (api), TypeScript with Next.js 16 and React 19 (ui)

**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, `google-genai` (through ports only), Tailwind 4. No new dependency.

**Storage**: PostgreSQL 16. One migration, `0020_catalog_other_names`: `recipe.language`, `recipe.language_detected_at`, `ingredient.language`, new tables `ingredient_name` and `ingredient_pair_dismissal`, and `shopping_list_item.names`.

**Testing**: pytest (domain pure; application with fake ports, including a new `FakePairSuggester`; integration in the Compose test overlay), vitest for ui, a browser walk, and manual AI evaluation fixtures.

**Target Platform**: The existing four Compose services. Only `api` and `ui` change.

**Project Type**: Web application (hexagonal api + Next.js BFF ui)

**Performance Goals**: SC-004 under 2 s for a merge across 10 notebooks with 200 recipes in all. SC-006 under 10 s for suggestions over 300 names.

**Constraints**: The domain stays pure. No new service, queue or worker: the language backfill is an operator command, and suggestions are synchronous calls. Lines keep carrying names, not ids (PRD 1.6). AI output is never applied without the person confirming it.

**Scale/Scope**: A household: tens of notebooks per person, hundreds of names per catalog, hundreds of recipes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| 1 Simplicity and reuse | No new service or worker. The backfill copies the `scripts.embeddings` operator pattern. The UI reuses `DataTable`, `ActionDialog`, `Sheet` and the `/ingredients` page. Auth is untouched | Pass |
| 2 Tech stack | No new library | Pass |
| 3 Hexagonal | The rules (index, merge plan, rename check, split plan, pair filter, shown name) live in `domain/ingredient_catalog.py`. Use cases and the new `IngredientPairSuggester` port are in `application/`. Gemini is only in `adapters/llm/`. Access checks are in `application/` (404 when the person can't read the notebook, 403 for writes when they can only read) | Pass |
| 4 Security and privacy | Only notebooks the person can write to are listed or merged. A pair request sends only names to the model, never recipe text. The pair route is rate limited | Pass |
| 5 No AI shortcuts | Suggested pairs and detected languages are proposals. A pair changes nothing until the merge is confirmed. A detected language is only stored as a proposal; the recipe's language changes when a person applies it | Pass |
| 6 Testing | Domain tests first. Application tests use fakes. There are integration tests and a migration test, plus new AI eval fixtures for pairs and language | Pass |
| 7 Deployment | One forward migration. The operator runs the backfill command once after deploy (noted in the deployment docs) | Pass |
| 8 Git | Feature work goes on the story branch, with small commits | Pass |
| 9 Scope | S-043 is a *should*. The owner picked it on 2026-11-06. Recipe language and pair suggestions were added in the spec clarifications | Pass |

There are no violations, so Complexity Tracking is empty. The post-design re-check also passes: the
data model adds tables and columns only, and every new external call goes through a port.

## Project Structure

### Documentation (this feature)

```text
specs/043-catalog-rename-merge/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/catalog.md # Phase 1
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
api/
├── domain/
│   ├── ingredient_catalog.py      # CatalogIndex, shown_name, plan_merge, check_rename, split_plan, filter_pairs
│   ├── recipe.py                  # resolve_line_names through the index; RecipeLanguage
│   ├── recipe_draft.py            # draft carries language; matching through the index
│   └── cart.py                    # unchanged grouping (kept names)
├── application/
│   ├── ports.py                   # IngredientCatalog: index_for_notebook, other-name writes; IngredientPairSuggester; LanguageDetector
│   ├── catalog_manage.py          # new: Rename, Delete, MergePreview, Merge, Split, SuggestPairs, DismissPair services
│   ├── recipe_capture*.py, recipe_save.py, recipe_manage.py, recipe_share.py, notebook_invites.py  # names_for_notebook → index
│   ├── notebooks.py               # snapshot copies other names
│   └── shopping_list.py           # item names per language; places by any name
├── adapters/
│   ├── llm/gemini_pair_suggester.py, gemini_language_detector.py
│   ├── llm/prompts/ingredient_pairs_system.md, recipe_language_system.md; recipe_extraction_system.md (+language)
│   └── persistence/models.py, catalog.py, migrations/versions/0020_catalog_other_names.py
├── api/routes/catalog.py          # new, per contracts/catalog.md; recipes.py, shopping_list.py (fields)
├── scripts/recipe_languages.py    # operator command: detect | status
└── tests/                         # test_catalog_manage_{domain,application,integration}.py, migration test, fixtures/ai_eval/pairs/

ui/
├── app/ingredients/page.tsx       # notebook selector, catalog actions, Suggest pairs
├── app/api/notebooks/[id]/catalog/**, app/api/catalog/**  # BFF proxies
├── components/CatalogManager/     # table, rename/merge/delete/split dialogs, pair list
├── app/recipes/…                  # language on recipe detail and edit; lines show shown_name
└── lib/i18n/catalog.ts            # en, es
```

**Structure Decision**: This is the existing web application layout (hexagonal `api/`, Next.js BFF `ui/`). New code sits next to the spec 070 places code and the spec 027 recipe edit code.

## Phasing for tasks

1. Migration, domain index and shown name, with matching moved to the index (no behaviour change until other names exist).
2. US1 merge, including preview, multi-notebook merge, places, the shopping list display, and showing and editing a recipe's language. US2 rename. Both are P1.
3. The one-time language proposal command and its Apply/Dismiss banner.
4. US3 delete, US5 suggested pairs (P2), then US4 split (P3).
5. UI on `/ingredients`, i18n, browser walk, and AI eval.

## Complexity Tracking

No constitution violations.
