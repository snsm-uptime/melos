# Notes: Catalog Management (S-043)

Work happens on the worktree branch `worktree-43-catalog-management`, which serves as the story
branch (`043-catalog-rename-merge` in plan.md). The worktree has its own Compose project and data
folder, so `./scripts/compose-test.sh` runs against an isolated test database.

## Decisions made while building

- **T002, `recipe.language` default.** The column has `server_default 'es'` after the fill.
  This is the last FR-005a fallback. Without it, existing raw-SQL fixtures and any writer that
  names no language failed NOT NULL. The app always passes a language.
- **T005.** The guard in `test_recipe_manage_integration.py` only lists tables with a key to
  `recipe.id`. The new tables have none, so the list is unchanged.
- **T007, draft line names.** A matched draft line takes its ingredient's name in the draft's
  language ("cebolla" in a Spanish draft), and the listed change shows the same name. Save
  resolves every kept or other name to the kept name (`resolve_line_names` through the index),
  so the stored line always carries the kept name (R1).
- **T007, plain lists still accepted.** `match_line`, `propose_entry`, `names_to_add`,
  `resolve_line_names` and `check_draft` take a `CatalogIndex` or a list of kept names. A list is
  read as an index with no other names, which keeps the S-018 answers unchanged.
- **T012, page parts.** Each page part returns a language too. The merged draft takes the
  language most of its parts give, weighted by lines and steps. When no part gives one, the
  capture response falls back to the interface language, then Spanish.
- **T013, applying a detected language.** `PUT /recipes/{id}` accepts `language` and
  `proposed_language: null`, as the contract says. A full PUT needs the edit lock and the
  whole recipe body, so the banner uses a small `PATCH /recipes/{id}/language` with
  `{"language": "en" | "es" | null}` instead (null dismisses). It needs write access and is
  refused while another person is editing the recipe.

- **T016, merge names resolve by the matching rule.** `plan_merge` resolves each name with
  the S-018 rule, so "onions" finds "onion" in another notebook. The preview starts from the
  chosen notebook and then checks every notebook the person can write to.
- **T018, writable notebooks.** These are found in the application layer, with
  `visible_facts_for` and the existing access rules, and not with SQL in the catalog adapter.
- **T024, the viewer's language.** The services read it from the viewer's account language
  (`users.language`). The response picks the word and re-sorts each section by it. The sort is
  stable, so lines of one name keep their kind and size order. Services built without the new
  optional ports behave exactly as before.
- **T032, normalizing a new name.** The singular is used only when the S-018 rules give
  exactly one shorter form. "Plum Tomatoes" has two possible singulars ("plum tomato" and
  "plum tomatoe"), so it is kept as typed.
- **T047, rate limit.** Capture has no per-user limit of its own, so pair suggestions use the
  shared sliding-window limiter with their own key: 10 requests per 10 minutes per person.
- **T038 and T046, prompt registration.** `prompt_templates.py` loads templates by file name
  and has no list to register them in. The two new templates are listed in
  `adapters/llm/prompts/README.md`, and their system prompts are built next to their adapters.
- **Tests, grouped.** The BFF route tests are in one file, `ui/app/api/catalog.bff.test.ts`,
  as `places.bff.test.ts` does it. The merge, rename, delete, split and pair dialogs are tested
  through `CatalogManager.test.tsx`. The recipe language tests are in
  `RecipeDetail/RecipeLanguage.test.tsx`. Application tests for pairs are in
  `test_catalog_manage_application.py`, not a separate `test_pair_suggest_application.py`.
- **Language field.** One shared `components/LanguageField` radio group serves the merge
  dialog, the rename dialog, the recipe edit form and the capture draft. It is used instead of
  `ButtonGroup`, which holds icon buttons only.
- **T056, mypy.** mypy is not a project dependency (`api/pyproject.toml` has pytest and ruff
  only), and adding it would be a new dependency, so it was not run.

- **Language detection is offline (owner decision, 2026-11-06).** The owner asked to stop
  using AI to identify the language. lingua-py (`lingua-language-detector==2.2.0`), limited to
  English and Spanish, now does it in `adapters/language/lingua_detector.py`, behind the
  `LanguageDetector` port:
  - `RecipeExtraction` sets each draft's and each page part's language from its text, before
    matching. The extractor prompt and its response schema no longer have a `language` field.
  - `scripts.recipe_languages detect` uses the same detector, so it needs no API key.
  - The Gemini language detector and its prompt are gone.
  - The proposal still waits for a person to apply it (FR-005a, unchanged).
  - This adds one library, against plan principle 2's "No new library"; the owner approved it.
    The wheel is about 160 MB, which grows the api image.
  - The ten language evaluation cases now run as a test, and all ten pass. T059's
    language-detection part is covered by that test.
  - Verified the same day: the api image rebuilds with lingua, and the Compose suite has
    **2133 passed** with the same 3 environmental failures. The host unit suite has 1455
    passed.

## Verification

- Phase 2 checkpoint (2026-11-06): the six T015 suites pass in Compose (174 tests).
- T057 (2026-11-06), the api suite in Compose: **2125 passed, 3 failed**. The 3 failures are
  environmental and do not touch this story's code:
  - `test_gemini_embedder_adapter.py::test_live_model_returns_768_values` makes a live
    Gemini call, which fails here with `AIProviderError`.
  - `test_recipe_capture_integration.py::test_empty_and_too_long_text_are_refused_with_no_assistant_call`
    and `::test_vocabulary_lists_the_controlled_values` expect a 5000-character limit, but
    this worktree's `.env` sets `RECIPE_TEXT_MAX_CHARS=10000`.
- T057, the ui: `npx vitest run` gives **1556 passed** (179 files). `npm run lint` and
  `npm run typecheck` are clean.
- T056: `uv run ruff check` and `uv run ruff format --check` are clean (305 files).
- Convergence (T061 to T064, 2026-11-06):
  - **T061:** copy-to-kitchen now matches names through the target's index. This uses the
    shared `match_copied_names` in `application/catalog_manage.py`, which sharing uses too.
  - **T062:** the owner kept `PATCH /recipes/{id}/language`, and it is now recorded in
    `contracts/catalog.md`.
  - **T063:** a rename to the ingredient's own other name is refused as
    `409 name_is_own_other_name`, with no merge offer.
  - **T064:** the places view lists each ingredient's other names under it.
  - Results: the api in Compose has **2130 passed** and the same 3 environmental failures.
    The ui has **1557 passed**, and lint and typecheck are clean.
- **Not done:** T058, the browser walk (scenarios 1 to 12 at 360 and 1280 px, en and es, by
  keyboard, with the SC-001 tap count and the SC-004 and SC-006 timings), needs an isolated
  stack and Playwright on the host. T059, the manual AI evaluation, needs a working live model;
  the live call fails in this environment. T060 waits for the owner to accept the story.
