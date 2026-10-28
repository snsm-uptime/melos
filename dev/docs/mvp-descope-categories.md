# Plan: main ingredients and cuisines out of the MVP

Decided 2026-10-27. Main ingredients and cuisines (together "categories") leave the MVP and move to *Later*.
Nothing is deleted: docs keep the design in one deferred section, and code is commented out under one greppable
marker so it can be restored.

## Guardrails

- **Ingredient catalog matching (S-018) stays exactly as built.** Not touched: `domain/ingredient_catalog.py`,
  `match_line`, `_match_lines`, `LineMatch`, `NameChange`, `text_name`, `catalog_match`, the matching prompt rules,
  `ui/lib/capture/nameChanges.ts`, the "matched / new ingredient" labels and the undo list.
- **Units, sizes, preparation, vague amounts and `max_text_chars` stay.** `GET /recipe-vocabulary` also serves them, so the
  route stays and only loses its category keys.
- Data files (`categories.yaml`, `cuisine.yml`, `category-prompt.md`, `cuisine.*`) are data, not code: left in place, unread.
- Marker for commented code: `MVP-OUT:` (Python `# MVP-OUT:`, TS `// MVP-OUT:`). Restore with `grep -rn "MVP-OUT"`.
- Each phase ends with a **Validate** block. A box is ticked only after its check was run and passed.
- No commits, no pushes. Everything stays in the working tree.

## Decisions (defaults, change before Phase 2 if wrong)

| Question | Decision |
|---|---|
| Draft response (`POST /recipes/capture/text`) | `main_ingredients` and `cuisines` keys removed, not sent empty |
| `GET /recipe-vocabulary` | keeps `units`, `sizes`, `max_text_chars`; drops `max_main_ingredients`, `max_cuisines`, `main_ingredients`, `cuisines` |
| Gemini output schema and system prompt | rule for `main_ingredients` removed; model no longer asked for it |
| `INTERNATIONAL` fallback and AC2.1 cuisine clause | out with cuisines |
| PRD | removed text moves to new Appendix E "Deferred: main ingredients and cuisines"; MVP sections lose it |
| Backlog | new story S-061 (later) holds the deferred work; S-021 loses "category filters" |
| Pre-existing failures | not fixed here, reported as they are (see baseline) |

## Baseline (before any change, 2026-10-27)

- api, host `uv run pytest -q`: **402 passed, 2 failed, 152 skipped** (no database on the host).
  Failures predate this work: `test_prompt_characterization.py::test_system_instruction_matches_golden` and
  `test_recipe_draft_domain.py::test_vocabulary_copies_in_domain_match_dev_docs[categories.yaml]`.
- api, Compose test overlay: 554 passed, 2 skipped (spec 018 notes, run with `RECIPE_TEXT_MAX_CHARS=5000`).
- ui `npx vitest run`: **391 passed** (70 files). Lint and typecheck clean.

- [x] P0.1 Baselines recorded above
- [x] P0.2 Impact map built from `grep` over api, ui, docs and specs

## Phase 1 · Documentation

- [x] P1.1 `prd.md`: add Appendix E (deferred design: flow F category filters, data model columns, normalization categories paragraph, J2 category rules, AC2.1 cuisine clause, J3 category edit and filter, B.1 rule 8, B.3 `categories`, Appendix D "Categories")
- [x] P1.2 `prd.md`: remove those from the MVP sections (lines 145, 200, 205-206, 234-235, 249, 362, 372, 379, 386-387, 436, 513, 529, 543, 550, 586, 626) and mark Appendix C: main ingredients and cuisines under *Later*
- [x] P1.3 `backlog.yaml`: add S-061 (later); S-021 title and S-020 note lose categories; S-016 note records the descope
- [x] P1.4 `AGENTS.md` lines 89-91: categories paragraph replaced by a one-line "later" pointer
- [x] P1.5 specs 015 and 016 (15 files: spec, plan, tasks, data-model, research, quickstart, contracts, checklists): scope banner under the title, plus the contract change in `capture-api.md`; done tasks are not edited. Spec 018 is left alone on purpose (FR-009 stays true, notes.md is a record)
- [x] P1.6 `dev/memory/271026.md` and `history.md`: dated entry for the decision

**Validate P1**
- [x] V1.1 `grep -nEi "main[_ -]?ingredient|cuisine" dev/docs/prd.md` lists only Appendix E, Appendix C *Later* and the pointers
- [x] V1.2 No PRD sentence about catalog matching, notebooks, units, cart or chat changed (`git diff dev/docs/prd.md` reviewed hunk by hunk)
- [x] V1.3 `backlog.yaml` still parses (`python -c "import yaml; yaml.safe_load(open(...))"`) and S-018 is unchanged

## Phase 2 · API code (comment out)

- [x] P2.1 `domain/recipe_draft.py`: `MAX_MAIN_INGREDIENTS`, `MAX_CUISINES`, `INTERNATIONAL`, `DraftRecipe.main_ingredients/cuisines`, `_Matching`, `_CuisineNode`, `Vocabulary`, `_build_matching`, `_build_cuisine_nodes`, `build_vocabulary`, `score_cuisines` and its helpers (only helpers with no other caller), `_main_ingredients`, the `vocabulary` argument of `check_draft`
- [x] P2.2 `adapters/llm/vocabulary.py` (whole module), `prompt.py` (`MAIN_KEYS`), `gemini_extractor.py` (schema key, model field, mapping, `vocabulary` argument), `prompts/recipe_extraction_system.md` rule, `tests/fixtures/prompts/recipe_extraction_system.golden.txt` regenerated
- [x] P2.3 `application/recipe_extraction.py` (`vocabulary` argument), `application/recipe_vocabulary.py` (category keys and helpers; units, sizes and `max_text_chars` stay)
- [x] P2.4 `api/deps.py` (`load_vocabulary`, `load_vocabulary_documents`; the units/sizes answer stays), `api/routes/recipe_capture.py` (`_draft_body` category keys and label lookups)

**Validate P2**
- [x] V2.1 `uv run ruff check .` clean
- [x] V2.2 `grep -rnE "main_ingredient|cuisine|Vocabulary\b|score_cuisines" api --include='*.py' | grep -v MVP-OUT` shows no live use
- [x] V2.3 `git diff` shows no change inside `match_line`, `_match_lines`, `same_spelling`, `ingredient_catalog.py`
- [x] V2.4 Import check: `create_app()` builds (10 routes)

## Phase 3 · API tests

- [x] P3.1 Tests that only cover categories are commented out: `test_recipe_draft_domain.py` (cuisine scoring, main ingredient filtering, vocabulary copy test), `test_gemini_extractor_adapter.py`, `test_recipe_extraction_application.py`, `test_recipe_capture_application.py`, `test_recipe_capture_integration.py` (vocabulary test keeps its units/sizes/max_text_chars asserts)
- [x] P3.2 Tests that pass categories incidentally lose those arguments (`test_ingredient_matching_integration.py`, `test_notebook_integration.py`, `test_prompt_characterization.py`)

**Validate P3**
- [x] V3.1 Host pytest: no new failure versus baseline. Both baseline failures are gone: the golden prompt was regenerated (its drift from the committed template predates this work: line wrapping, `VAGUE_PHRASES`, trailing newline, plus the removed main-ingredient rule), and the `categories.yaml` copy test is one of the 10 category tests commented out, so that drift is hidden, not fixed
- [x] V3.2 Skipped count unchanged (152) on the host. In Compose the 2 skipped before were the two copy tests, now commented out
- [x] V3.3 Every S-018 test still present and passing: `-k "matching or catalog or name_change or match_line"`
- [x] V3.4 Compose test overlay: all tests pass. `RECIPE_TEXT_MAX_CHARS=5000` must reach the container with `run -e`; set only in the host shell, two `.env`-dependent tests fail (10000 vs 5000)

## Phase 4 · UI code (comment out)

- [x] P4.1 `lib/capture/captureClient.ts` (response types), `captureStore.ts` (`mainIngredients`, `cuisines`, `CategoryRef` if unused elsewhere), `draftHash.ts`, `draftRules.ts` (counts and constants), `lib/i18n/capture.ts` (labels and max messages)
- [x] P4.2 `components/RecipeDraft/RecipeDraftEditor.tsx` (two `CategoryChips`, vocabulary options for categories; units and sizes stay), `CategoryChips.tsx` (whole file), `index.ts` export, `AddRecipeCallToAction/TextCaptureSheet.tsx` (draft mapping; `max_text_chars` stays)
- [x] P4.3 `app/api/recipe-vocabulary/route.ts`: unchanged (still serves units, sizes, max length)
- [x] P4.4 UI tests: category-only tests commented out; shared fixtures lose the two fields

**Validate P4**
- [x] V4.1 `npm run typecheck` clean
- [x] V4.2 `npm run lint` clean
- [x] V4.3 `npx vitest run`: no new failure; count stays 391 because no UI test was category-only (fixtures and two assertions changed; the editor test now asserts the chips are absent)
- [x] V4.4 S-018 UI tests all present and passing: `NameMatching.test.tsx`, `captureMatch.test.ts`, `nameChanges` tests, `captureStore` undo tests
- [x] V4.5 `grep -rnEi "mainIngredient|cuisine|CategoryChips" ui --include='*.ts*' --exclude-dir=node_modules | grep -v MVP-OUT` shows no live use

## Phase 5 · Whole-repo check

- [x] V5.1 Final counts versus baseline written in the table below
- [x] V5.2 `grep -rn "MVP-OUT"` lists every commented block once, each with a restore hint
- [x] V5.3 `git status` shows only the files named in this plan; data files (`categories.yaml`, `cuisine.yml`) unchanged
- [x] V5.4 Contract: `capture-api.md` matches the live response (keys listed in Decisions)
- [x] V5.5 Not covered here, reported as such: browser walkthrough (needs the live model), AI evaluation T039 of spec 018

| Check | Baseline | After |
|---|---|---|
| api host passed / failed / skipped | 402 / 2 / 152 | 394 / 0 / 152 |
| api Compose passed / failed / skipped | 554 / 0 / 2 | 546 / 0 / 0 |
| ui passed | 391 | 391 |
| ruff, lint, typecheck | clean | clean |

The 10 fewer api tests are the commented category tests in `test_recipe_draft_domain.py` (8 passed, 2 parametrized copy tests that failed on the host and skipped in Compose). S-018 tests: 38 matching, catalog and change tests before and after; the only S-018 files with a diff are three test fixtures that lost the two category fields.
