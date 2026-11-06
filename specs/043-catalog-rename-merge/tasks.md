# Tasks: Catalog Management (rename and merge ingredient names)

**Input**: Design documents from `specs/043-catalog-rename-merge/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/catalog.md](contracts/catalog.md), [quickstart.md](quickstart.md)

**Tests**: Included. Constitution principle 6 requires domain, application (fake ports), integration (Compose test overlay), vitest and a browser walk.

**Format**: `- [ ] Txxx [P?] [Story?] Description with file path`. `[P]` means a different file with no open dependency.

## Phase 1: Setup

- [X] T001 Create the branch `043-catalog-rename-merge` from `main`, and start `specs/043-catalog-rename-merge/notes.md` with a "Verification" heading for results

---

## Phase 2: Foundational (blocks every story)

**Purpose**: The data model, the catalog index, and the recipe language. When this phase is done, nothing behaves differently yet, because no notebook has other names.

- [X] T002 Add the migration `api/adapters/persistence/migrations/versions/0020_catalog_other_names.py` (down revision `0019_ingredient_place_owner`):
  - `recipe.language varchar(2)` with check `language IN ('en','es')`. Add it nullable, then fill it by the FR-005a fallback: a kitchen notebook's recipe gets `kitchens.content_language`; a personal one gets the author's `users.language` when its first two letters (lower-cased) are 'en' or 'es'; anything else gets 'es'. Then set NOT NULL.
  - `recipe.language_detected_at timestamptz NULL`.
  - `recipe.proposed_language varchar(2) NULL` with check `proposed_language IS NULL OR proposed_language IN ('en','es')`.
  - `ingredient.language varchar(2) NULL`, with check `language IS NULL OR language IN ('en','es')`.
  - Table `ingredient_name`: `id uuid PK default gen_random_uuid()`, `ingredient_id uuid NOT NULL FK ingredient.id ON DELETE CASCADE`, `notebook_id uuid NOT NULL FK notebook.id ON DELETE CASCADE`, `name text NOT NULL`, `kind text NOT NULL` with check `kind IN ('variant','spelling')`, `language varchar(2) NULL` with check `(kind = 'variant' AND language IN ('en','es')) OR (kind = 'spelling' AND language IS NULL)`, `created_at timestamptz default now()`. Add `unique(notebook_id, name)`, a partial unique index `(ingredient_id, language) WHERE kind = 'variant'`, and an index on `ingredient_id`.
  - Table `ingredient_pair_dismissal`: `notebook_id uuid FK notebook.id ON DELETE CASCADE`, `name_a text`, `name_b text`, PK `(notebook_id, name_a, name_b)`, check `name_a < name_b`, `dismissed_by uuid NULL FK users.id ON DELETE SET NULL`, `created_at timestamptz default now()`.
  - `shopping_list_item.names jsonb NOT NULL default '{}'`.
  - Write a full downgrade.
- [X] T003 Add `RecipeModel.language`, `language_detected_at` and `proposed_language`, `IngredientModel.language`, `IngredientNameModel`, `IngredientPairDismissalModel` and `ShoppingListItemModel.names` in `api/adapters/persistence/models.py`, matching T002
- [X] T004 [P] Add a migration test in `api/tests/test_catalog_other_names_migration.py`, following `api/tests/test_shopping_places_migration.py`. It covers the fallback fill for a kitchen recipe ('en' kitchen), a personal recipe whose author's language is 'en', and an author with no language ('es'). It also checks the downgrade to 0019 and a second upgrade.
- [X] T005 Add `ingredient_name` and `ingredient_pair_dismissal` to the schema guard list of every table in `api/tests/test_recipe_manage_integration.py`
- [X] T006 Add these pure rules to `api/domain/ingredient_catalog.py`:
  - `Language = Literal["en","es"]`.
  - `CatalogEntry(name, language, variants: dict[Language,str], spellings: tuple[str,...])`.
  - `CatalogIndex.build(entries)`: maps `normalize_name` of every kept and other name, and every `singular_forms` of each, to the kept name. `kept_for(name)` returns the kept name or None; `entry(kept)` returns the entry; `kept_names()` lists the kept names.
  - `shown_name(entry, language)`: the kept name when `entry.language == language`, else the variant for `language`, else the kept name.
  - `name_taken(index, name)`.
- [X] T007 Change `match_line`, `propose_entry` and `names_to_add` in `api/domain/ingredient_catalog.py`, and `resolve_line_names` in `api/domain/recipe.py`, to take a `CatalogIndex` instead of a sequence of names (research R4). A line that hits an other name resolves to the kept name and is listed as a `NameChange` whose `to` is `shown_name(entry, draft language)`; the stored line name stays the kept name. Pass the draft's language in as a parameter (it comes from T012). Keep the old behaviour when the index has no other names. Update `_match_lines` in `api/domain/recipe_draft.py` to match.
- [X] T008 [P] Extend `api/tests/test_ingredient_catalog_domain.py`:
  - "cebollas" matches "onion" through the variant "cebolla".
  - A spelling matches.
  - `shown_name` covers an entry with no language, an entry whose language is the one asked, and an entry with a variant.
  - `names_to_add` skips a name that is an other name.
  - Every existing case still passes when the index has no other names.
- [X] T009 In `api/application/ports.py`, replace `IngredientCatalog.names_for_notebook` with `index_for_notebook(notebook_id) -> CatalogIndex`. Keep `names_for_notebook` as the kept names only, for the admin and places readers. Make `copy_names` also copy `ingredient.language` and the `ingredient_name` rows (data-model "Snapshots and copies").
- [X] T010 Implement T009 in `api/adapters/persistence/ingredient_catalog.py`. `index_for_notebook` reads `ingredient` and `ingredient_name` for the notebook in one query.
- [X] T011 Switch every matching call site to `index_for_notebook`:
  - `api/application/recipe_capture.py` and `api/application/recipe_capture_url.py`: the extractor's `ingredient_names` becomes kept names plus other names.
  - `api/application/recipe_save.py`, `api/application/recipe_manage.py`, `api/application/recipe_share.py` and `api/application/notebook_invites.py`.
  - Update their fakes in `api/tests/` (`notebook_sharing_fakes.py` and any fake catalog).
- [X] T012 Add recipe language end to end:
  - Add `language` (`'en'` or `'es'`) to the extraction schema and the parsed output in `api/adapters/llm/gemini_extractor.py`.
  - Add one rule to `api/adapters/llm/prompts/recipe_extraction_system.md`: "language: en or es, the language most of the pasted text is in." Update `api/tests/fixtures/prompts` characterization snapshots.
  - Add `language` to the draft in `api/domain/recipe_draft.py`, `NewRecipe` and `RecipeDetail` in `api/application/ports.py`, and the recipe repository insert, read and update in `api/adapters/persistence/`.
  - Make `api/adapters/llm/fake_extractor.py` return 'en' unless told otherwise.
- [X] T013 Add `language` to the capture draft response and the save request in `api/api/routes/recipe_capture.py` and `api/api/routes/recipes.py`, and add `language` to `GET /recipes/{id}` and `PUT /recipes/{id}` (contracts "Changed routes"). The PUT edit service in `api/application/recipe_manage.py` accepts a change of language, which also clears `proposed_language`, and `proposed_language: null` alone (dismiss). `GET /recipes/{id}` also returns `proposed_language`.
- [X] T014 Add `shown_name` to each line of `GET /recipes/{id}` in `api/application/recipe_manage.py` and its schema in `api/api/schemas/`, using the notebook's index and `shown_name(entry, recipe.language)` (FR-006)
- [X] T015 [P] Run the existing suites, which must still pass: `test_ingredient_matching_integration.py`, `test_recipe_save_integration.py`, `test_recipe_manage_integration.py`, `test_recipe_share_integration.py`, `test_notebook_invites_integration.py`, `test_notebook_snapshots_integration.py`. Add a snapshot case to `api/tests/test_notebook_snapshots_integration.py`: the snapshot copies other names and the ingredient's language.

**Checkpoint**: Every existing test passes, and recipes have a language.

---

## Phase 3: User Story 1, merge two names, also across languages (P1) 🎯 MVP

**Goal**: Merge "cebolla" into "onion" in every notebook the person can write to that has both names. Recipes show the name in their own language, the shopping list adds both up on one line, and later captures match.

**Independent Test**: quickstart scenarios 3, 4, 5 and 11.

- [X] T016 [P] [US1] Add `plan_merge(index, merged, kept, merged_language, kept_language)` to `api/domain/ingredient_catalog.py` (data-model "State transitions"). It returns the kept entry's new `language` (`kept_language` when the entry has none) and the other names to add. The merged name becomes a variant when its language differs from the kept language and the kept entry has no variant in that language; otherwise it becomes a spelling. Each of the merged entry's own other names follows the same rule. It raises `SameIngredient` when both names already resolve to the same kept name, and `UnknownName` when either is missing.
- [X] T017 [P] [US1] Add domain tests in `api/tests/test_catalog_manage_domain.py` for `plan_merge`: es into en makes a variant; same language makes a spelling; when the kept entry already has a Spanish variant, a Spanish name becomes a spelling; the merged entry's other names are carried; same ingredient is refused; an unknown name is refused
- [X] T018 [US1] Add these writes to the `IngredientCatalog` port in `api/application/ports.py` and implement them in `api/adapters/persistence/ingredient_catalog.py`:
  - `lock_entries(notebook_id, names)` does `SELECT ... FOR UPDATE` and returns the current entries (research R6).
  - `apply_merge(notebook_id, merged, kept, plan)` updates `recipe_ingredient.name` from `merged` to `kept` for the notebook's recipes, moves the merged entry's `ingredient_name` rows to the kept entry, inserts the merged name as an other name, sets `ingredient.language`, deletes the merged `ingredient` row, deletes the notebook's `ingredient_pair_dismissal` rows that name `merged`, and returns the changed recipe ids.
  - `writable_notebooks_with(user_id, names)` lists the notebooks the person can write to whose index has both names, with the count of recipes using the merged name in each.
- [X] T019 [US1] Add `move_choices(old_name, new_name)` to `PlaceRepository` in `api/application/ports.py` and `api/adapters/persistence/places.py` (research R8). For every person with a row for the old name and none for the new one, rename the row; keep the old-name row when the person also has one for the new name (FR-009: any other choice is unchanged).
- [X] T020 [US1] Create `api/application/catalog_manage.py` with these services:
  - `MergePreviewService`: prefills each name's language from the most common `recipe.language` among the recipes that use it, else `ingredient.language`.
  - `MergeService`: for each requested notebook id, re-checks write access (spec 056 rules) and both names under a savepoint. It skips with `name_changed` or `no_access` and otherwise applies `plan_merge` and `apply_merge`. Then it calls `move_choices` once and enqueues the changed recipe ids on `EmbeddingJobs` (research R10). Logs carry counts only.
- [X] T021 [P] [US1] Add application tests in `api/tests/test_catalog_manage_application.py` with fake ports: the preview lists only writable notebooks with both names; a merge across two notebooks; one notebook skipped after its name changed; a read-only notebook is never touched; places move; embeddings are enqueued
- [X] T022 [US1] Add schemas in `api/api/schemas/catalog.py` and routes in `api/api/routes/catalog.py` for `POST /catalog/merge-preview` and `POST /catalog/merge` (contracts/catalog.md), and register the router in `api/api/app.py`
- [X] T023 [US1] Add `GET /notebooks/{notebook_id}/catalog` to `api/api/routes/catalog.py`, with a `GetCatalogService` in `api/application/catalog_manage.py`. A person who cannot read the notebook gets 404. The response includes `can_write` and `recipe_count` per ingredient.
- [X] T024 [US1] Show each shopping list line in the viewer's language (research R7):
  - In `api/application/shopping_list.py` `build_cart_list`, keep grouping by kept name. Gather the variants of each group's ingredient from the kitchen notebook with the most recipes in the group whose ingredient has variants (ties broken by notebook id), and store them as `names` on cart lines through `cart_lines` in `api/domain/shopping_list.py` and `replace_cart_lines` in `api/adapters/persistence/shopping_lists.py`.
  - In the list views (`GetShoppingListService`, `ClosedShoppingListsService`), set each item's `name` to `names[viewer language]` or the kept name, and add `kept_name`.
  - Look up places by the kept name first, then each variant (FR-007a).
  - Sort each section by `name_sort_key` of the name shown to the viewer, not the kept name (FR-007).
- [X] T025 [P] [US1] Add shopping list domain and application tests in `api/tests/test_shopping_list_saved_domain.py` and `api/tests/test_shopping_list_application.py`: an English viewer sees "onion" and a Spanish viewer sees "cebolla" on one line with summed amounts; hand items are unchanged; a closed list keeps its stored `names`; a place set on "onion" applies to the Spanish view; a Spanish viewer sees "ajo" before "cebolla" while an English viewer sees "garlic" before "onion" on the same list
- [X] T026 [P] [US1] Add HTTP tests against Postgres in `api/tests/test_catalog_manage_integration.py`:
  - Merge cebolla into onion across a kitchen notebook and a personal notebook.
  - Recipe lines are rewritten, and `GET /recipes/{id}` shows "cebolla" for the Spanish recipe.
  - A capture with "cebollas" lists a change and adds no name.
  - A person with no access gets 404 and a read-only person gets 403.
  - Two concurrent merges: the second reports a skip.
  - SC-005: every `recipe_ingredient.name` equals an `ingredient.name` of its notebook.
- [X] T027 [US1] Add BFF routes `ui/app/api/catalog/merge-preview/route.ts`, `ui/app/api/catalog/merge/route.ts` and `ui/app/api/notebooks/[notebookId]/catalog/route.ts`, following `ui/app/api/me/places/route.ts`, each with a `route.test.ts`
- [X] T028 [US1] Create `ui/components/CatalogManager/CatalogManager.tsx`. It has a notebook selector ("All" keeps today's places view in `ui/components/Ingredients/IngredientsScreen.tsx`; a notebook shows its catalog in `DataTable` with each ingredient's other names and language). Add a Merge action that opens `MergeDialog.tsx` (built on `ActionDialog`): pick the name to keep with `SearchableSelect`, show the language of each name (editable, en or es), and list every notebook with its recipe count; on confirm, show the merged and skipped notebooks. Hide all actions when `can_write` is false. Wire it into `ui/app/ingredients/page.tsx`.
- [X] T029 [P] [US1] Add English and Spanish strings for the catalog view and the merge dialog in `ui/lib/i18n/catalog.ts`, and register them so `ui/lib/i18n/parity.test.ts` checks them
- [X] T030 [P] [US1] Add vitest tests in `ui/components/CatalogManager/CatalogManager.test.tsx` and `MergeDialog.test.tsx`: the preview lists notebooks, editing a language, the result with a skipped notebook, no actions on a read-only notebook, keyboard use; the merge, rename, delete and split results are announced through a polite live region, checked with `getByRole('status')`
- [X] T031 [US1] Show `shown_name` on recipe lines in `ui/components/RecipeDetail/RecipeDetailView.tsx`. Show the shopping list item `name` (already per viewer) and use `kept_name` for place lookups in `ui/components/ShoppingList/`. Update the tests next to them.
- [X] T041 [US1] Show the recipe's language in `ui/components/RecipeDetail/RecipeDetailView.tsx`. Add a language choice (en or es, reusing `ButtonGroup`) to `ui/components/RecipeEdit/RecipeEditForm.tsx` and the capture draft in `ui/components/RecipeDraft/`. Add the strings to `ui/lib/i18n/recipeDetail.ts` and `capture.ts`, and update the neighbouring tests. Show the "Detected: {language}. Apply? / Dismiss" banner on `RecipeDetailView` when `proposed_language` is set: Apply sends `PUT /recipes/{id}` with `language`, Dismiss sends `proposed_language: null`.

**Checkpoint**: A bilingual merge works end to end, and people can see and correct each recipe's language. Existing recipes have the fallback language until Phase 5 runs the language proposal. Stop here for the MVP review.

---

## Phase 4: User Story 2, rename a name (P1)

**Goal**: Fix "tomatoe" to "tomato". Recipe lines, places and dismissals follow, and an existing name leads to an offer to merge.

**Independent Test**: quickstart scenario 6.

- [X] T032 [P] [US2] Add `check_rename(index, old, new)` to `api/domain/ingredient_catalog.py`. It normalizes the new name (trim, lower-case, the singular from `singular_forms` when the S-018 rules give exactly one shorter form, else as typed). It returns `Blank`, `Exists(kept_name)` when `name_taken` or the index resolves the name to another entry, `Unchanged` when the new name is the same after normalization, or the new name. Add tests to `api/tests/test_catalog_manage_domain.py`.
- [X] T033 [US2] Add `apply_rename(notebook_id, old, new)` to the catalog port and adapter in `api/adapters/persistence/ingredient_catalog.py`. It updates `ingredient.name`, `recipe_ingredient.name` for the notebook's recipes, and `ingredient_pair_dismissal` names (re-sorted), and returns the changed recipe ids.
- [X] T034 [US2] Add `RenameService` to `api/application/catalog_manage.py`. It locks the entry, runs `check_rename`, calls `apply_rename`, calls `move_choices(old, new)` (FR-012) and enqueues embeddings. It raises `NameChanged` when the old name is gone. A rename with an unchanged name may still set `ingredient.language` (contracts PATCH).
- [X] T035 [US2] Add `PATCH /notebooks/{notebook_id}/catalog/{name}` to `api/api/routes/catalog.py`, returning 409 `name_exists` with `existing`, 409 `name_changed` or 422 `name_blank`. Add the BFF route `ui/app/api/notebooks/[notebookId]/catalog/[name]/route.ts` (PATCH) with a test.
- [X] T036 [P] [US2] Add application and integration tests in `api/tests/test_catalog_manage_application.py` and `api/tests/test_catalog_manage_integration.py`: a rename rewrites the lines; "tomatoes" when "tomato" exists gives `name_exists`; a blank name is refused; the place moves; a concurrent rename gives `name_changed`
- [X] T037 [US2] Add `RenameDialog.tsx` in `ui/components/CatalogManager/`. On `name_exists`, it offers "Merge into {existing}", which opens `MergeDialog` prefilled. Add its strings to `ui/lib/i18n/catalog.ts` and tests to `RenameDialog.test.tsx`.

---

## Phase 5: User Story 1 (continued), one-time language proposal (FR-005a)

**Goal**: The model proposes a language for each existing recipe once; a person applies or dismisses it (T041 banner).

**Independent Test**: quickstart scenarios 1 and 2.

- [X] T038 [P] [US1] Add `LanguageDetector` to `api/application/ports.py` with `detect(text) -> Language | None` (None when unsure or on a model error). Add the prompt `api/adapters/llm/prompts/recipe_language_system.md`, an entry in `api/adapters/llm/prompt_templates.py`, the adapter `api/adapters/llm/gemini_language_detector.py` (model from `GEMINI_CHAT_MODEL`, errors mapped as in `gemini_errors.py`) and a fake in `api/tests/`
- [X] T039 [US1] Create `api/scripts/recipe_languages.py` with the subcommands `detect [--limit N]` and `status`, following `api/scripts/embeddings.py`. `detect` reads recipes with `language_detected_at IS NULL` in batches. It sends the title, ingredient names and steps to the detector, sets `proposed_language` when the detector returns a language different from `language` (it never writes `language`), and sets `language_detected_at` either way. It prints counts and exits 0, or 1 on a database error. Document it in `api/scripts/README.md` and the deployment docs (run once after deploy).
- [X] T040 [P] [US1] Add tests in `api/tests/test_recipe_languages_script_integration.py` with the fake detector: it stores a differing proposal and leaves `language` unchanged, stores nothing when the detector agrees or is unsure, and changes nothing when run twice

---

## Phase 6: User Story 3, delete an unused name (P2)

**Goal**: Remove "saffron" when no recipe uses it, and refuse "onion" with a count.

**Independent Test**: quickstart scenario 7.

- [X] T042 [US3] Add `delete_unused(notebook_id, name) -> int | None` to the catalog port and adapter. It returns the recipe count and deletes nothing when the count is above 0; otherwise it deletes the `ingredient` row, which cascades to `ingredient_name`. Add `DeleteService` to `api/application/catalog_manage.py`, and `DELETE /notebooks/{notebook_id}/catalog/{name}` to `api/api/routes/catalog.py`, returning 204, 409 `name_in_use` with `recipe_count`, or 409 `name_changed`.
- [X] T043 [P] [US3] Add application and integration tests to `api/tests/test_catalog_manage_application.py` and `api/tests/test_catalog_manage_integration.py`: an unused name is deleted; a used name is refused with its count
- [X] T044 [US3] Add the DELETE handler to `ui/app/api/notebooks/[notebookId]/catalog/[name]/route.ts`, and add `DeleteNameDialog.tsx` in `ui/components/CatalogManager/` (confirm, or show the count with a "Merge instead" button). Add its strings and tests.

---

## Phase 7: User Story 5, suggested cross-language pairs (P2)

**Goal**: "Suggest pairs" lists likely English and Spanish pairs. The person accepts one into the merge confirmation, or dismisses it for good.

**Independent Test**: quickstart scenario 9.

- [X] T045 [P] [US5] Add `filter_pairs(index, dismissed, proposed)` to `api/domain/ingredient_catalog.py`. It keeps a pair only when both names are kept names of the index, they are different entries, and the sorted pair is not in `dismissed`. Add tests to `api/tests/test_catalog_manage_domain.py`.
- [X] T046 [US5] Add the `IngredientPairSuggester` port to `api/application/ports.py` (`suggest(names_with_language) -> list[tuple[str,str]]`; it raises the existing domain AI errors). Add the prompt `api/adapters/llm/prompts/ingredient_pairs_system.md` (input: names and languages as TOON; output: a JSON list of `{en, es}`; "only pairs that are the same ingredient; never invent names") and register it in `api/adapters/llm/prompt_templates.py`. Add the adapter `api/adapters/llm/gemini_pair_suggester.py`, which sends batches of 300 names, and `FakePairSuggester` in `api/tests/`.
- [X] T047 [US5] Add `SuggestPairsService` and `DismissPairService` to `api/application/catalog_manage.py`, with the dismissal reads and writes on the catalog adapter. Add `POST /notebooks/{notebook_id}/catalog/pair-suggestions` (503 `ai_unavailable`, using the same per-user rate limit as capture) and `POST /notebooks/{notebook_id}/catalog/pair-dismissals` to `api/api/routes/catalog.py`.
- [X] T048 [P] [US5] Add application and integration tests in `api/tests/test_pair_suggest_application.py` and `api/tests/test_catalog_manage_integration.py`: invented names are dropped; a dismissed pair is not suggested again; the AI being unavailable gives 503; a read-only notebook gets 403
- [X] T049 [P] [US5] Add 10 AI evaluation fixtures to `api/tests/fixtures/ai_eval/pairs/`, each a catalog with its expected pairs, and a README line for the manual run (SC-006). Add 10 language-detection fixtures to `api/tests/fixtures/ai_eval/language/`.
- [X] T050 [US5] Add the BFF routes `ui/app/api/notebooks/[notebookId]/catalog/pair-suggestions/route.ts` and `pair-dismissals/route.ts` with tests. Add `PairSuggestions.tsx` in `ui/components/CatalogManager/`: a "Suggest pairs" button with `CauldronLoader` while waiting, a list of pairs with Accept (opens `MergeDialog` prefilled) and Dismiss, an empty state and an error state. Add its strings and tests.

---

## Phase 8: User Story 4, see other names and split one back out (P3)

**Goal**: Undo a wrong merge without changing any text a recipe shows.

**Independent Test**: quickstart scenario 8.

- [X] T051 [P] [US4] Add `split_plan(entry, other_name)` to `api/domain/ingredient_catalog.py`. For a variant, the recipes whose `language` equals the variant's language move to the new kept name; for a spelling, no recipe moves. Add tests to `api/tests/test_catalog_manage_domain.py`.
- [X] T052 [US4] Add `apply_split(notebook_id, kept, other_name, language)` to the catalog port and adapter. It deletes the `ingredient_name` row, inserts an `ingredient` with that name and language, and, for a variant, updates `recipe_ingredient.name` from the kept name to the split name for the notebook's recipes in that language. Add `SplitService` to `api/application/catalog_manage.py` (it enqueues embeddings) and `POST /notebooks/{notebook_id}/catalog/{name}/split` to `api/api/routes/catalog.py`.
- [X] T053 [P] [US4] Add integration tests to `api/tests/test_catalog_manage_integration.py`: after a split, the Spanish recipe still shows "cebolla", the shopping list has two lines again, and a capture with "cebolla" matches the split-out name
- [X] T054 [US4] Add the split route proxy to the BFF, and a Split action on each other name in `ui/components/CatalogManager/CatalogManager.tsx` with a confirmation. Add its strings and tests.

---

## Phase 9: Polish and cross-cutting

- [X] T055 [P] Update `AGENTS.md` "Domain rules". A catalog ingredient has a kept name and other names (variants per language, spellings). Lines carry the kept name. A recipe has a language. The shopping list shows the viewer's variant. Also add notes to `dev/docs/prd.md` J3 "Catalog management" and Appendix A (Ingredient, Recipe).
- [X] T056 [P] Run `uv run ruff check`, `uv run ruff format --check` and `uv run mypy` in `api/`, and `npm run lint` and `npm run typecheck` in `ui/`. Fix every finding.
- [X] T057 Run the full api test suite in the Compose test overlay (`./scripts/compose-test.sh`) and the ui vitest suite, and record the counts in `specs/043-catalog-rename-merge/notes.md`
- [ ] T058 Do the browser walk of quickstart scenarios 1 to 12 at 360 px and 1280 px, in en and es, once by keyboard, on an isolated stack. Record the results, the SC-001 tap count, and the SC-004 and SC-006 timings in `specs/043-catalog-rename-merge/notes.md`.
- [ ] T059 Run the manual AI evaluation (T049 fixtures), and record the share of suggested pairs that are real (SC-006: at least 8 of 10) and the language-detection results in `specs/043-catalog-rename-merge/notes.md`
- [ ] T060 Move S-043 to `dev/docs/backlog-done.yaml` with a verification note once the owner accepts it

---

## Dependencies

- Phase 2 blocks every story. Within it: T002 → T003 → T004 and T005; T006 → T007 → T008 (T007 also needs the draft language from T012); T009 → T010 → T011; T012 → T013 → T014; T015 comes last.
- US1 (Phase 3) needs Phase 2. US2 (Phase 4) needs T018's locking and T019, and reuses `MergeDialog` (T028) for its "merge instead" offer.
- Phase 5 (recipe language UI and detection) needs only Phase 2. It can run beside US1.
- US3 (Phase 6) needs Phase 2 and T023, T028.
- US5 (Phase 7) needs US1, because accepting a pair opens the merge.
- US4 (Phase 8) needs US1, because only a merge makes other names to split.
- Polish comes after the stories that ship.

```text
Setup → Foundational → US1 (Phase 3) → US2 (Phase 4) → US3 (Phase 6)
                     ↘ US1 language proposal (Phase 5, beside Phase 3)
                       US1 → US5 (Phase 7) and US4 (Phase 8)
                       all shipped stories → Polish (Phase 9)
```
## Parallel examples

- **Phase 2**: T004, T008 and T015 (tests) run beside each other once their code task is done. T006 and T012 touch different files and can start together.
- **US1**: T016 and T017 (domain), then T021, T025 and T026 (tests in separate files) together. T029 and T030 (ui strings and tests) run beside T022 to T024.
- **US5**: T045 and T049 can start at once. T048 runs beside T050.

## Implementation strategy

1. **MVP**: Phases 1 to 3. A bilingual merge works, recipes show their own language, and the shopping list shows one line in each viewer's language. Stop and review with the owner.
2. Add US2 (rename) and Phase 5 (language UI and the detection command). Then the P1 scope is complete and deployable, with the operator running `scripts.recipe_languages detect` once.
3. Add US3 and US5 (P2), then US4 (P3).
4. Finish with Polish (docs, the full suite, the browser walk, the AI evaluation).

---

## Phase 10: Convergence

- [X] T061 Match a copy-to-kitchen against the target notebook's `CatalogIndex` in `api/application/recipe_copy.py`, as `recipe_share.py` does: rename each copied line to its kept name with `rename_line_names`, add only names that match nothing, and add an application test plus an integration test where "cebolla" is an other name of "onion" in the target per FR-008, US1/AC4 (partial)
- [X] T062 Reconcile the detected-language banner with the contract: with the owner, either record `PATCH /recipes/{id}/language` in `specs/043-catalog-rename-merge/contracts/catalog.md` "Changed routes", or switch `ui/components/RecipeDetail/LanguageProposal.tsx` to `PUT /recipes/{id}` per plan contract "Changed routes", T041 (contradicts)
- [X] T063 Handle a rename of a kept name to one of its own other names in `api/domain/ingredient_catalog.py` `check_rename` and `ui/components/CatalogManager/RenameDialog.tsx`: refuse it with a clear message, or swap the kept name and the variant, and never offer "Merge into" the same ingredient; add domain and vitest cases per FR-011, edge case "rename to an other name" (partial)
- [X] T064 Show each ingredient's other names under it in the person-wide places view (`api/adapters/persistence/places.py` `catalog_names`/`recipe_uses`, `ui/components/Ingredients/IngredientsScreen.tsx`) per plan R8 (partial)
