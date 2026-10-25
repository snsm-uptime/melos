# Research: Capture a Recipe from Pasted Text

No NEEDS CLARIFICATION markers remained in the Technical Context. The spec's two
clarify sessions settled scope, entry points, notebooks, messages and the
archive rule. The items below resolve the remaining technical choices, found by
reading the current code (S-015 adapter, kitchens access layer, ui shell).

## R1. Notebook as an entity, and where the ingredient catalog comes from

- **Decision**: A notebook is its own entity, not a synonym for a kitchen or a
  member. Alembic `0003` creates:
  - `notebook(id, kitchen_id?, user_id?, created_at)` with exactly one owner
    (`CHECK ((kitchen_id IS NULL) <> (user_id IS NULL))`) and `UNIQUE (kitchen_id)`:
    one notebook per kitchen. `user_id` is not unique, so the schema allows many
    notebooks per member; the user table gains a nullable `default_notebook_id`
    (2026-10-22). Spec 055-notebooks creates these tables.
  - `ingredient(id, notebook_id, name, created_at)` with
    `UNIQUE (notebook_id, name)`. Each notebook has its own catalog.
  The migration backfills one notebook for every existing kitchen and for every
  existing user that has an alias.
  Recipes, when S-019 adds them, point at `notebook_id`. A copy between
  notebooks (S-034, S-047) finds its source and target by notebook id. Reading
  the catalog goes through an `IngredientCatalogReader` port
  (`names_for_notebook(notebook)`). Nothing in this feature writes to either
  table; notebooks are created by spec 055 (R13).
- **Rationale**: The notebook id is what identifies the source and the target
  of a copy, and a kitchen and its notebook are different concepts. FR-003 and
  FR-022 need a real catalog read, so tests can prove that a capture only sees
  its own notebook's names.
- **Alternatives considered**: (a) `kitchen_id?` / `user_id?` on every recipe
  and ingredient, as in the PRD today. Rejected: the owner is repeated on every
  table and a copy cannot name its source notebook. (b) An "empty catalog"
  stub. Rejected: production would run a stub and FR-022 would be untested.
- **Cross-spec change for review**: PRD §1.6 and Appendix A, and the AGENTS.md
  domain rules, speak of `kitchen_id` or `user_id` on recipes and ingredients.
  They become `notebook_id`. This plan does not edit them.

## R2. `preparation` is missing from the S-015 result

- **Finding**: spec 016 FR-007, FR-010 and FR-012 show and edit a preparation
  ("onion" + "chopped"). PRD §1.6 and Appendix B.1 rule 2 ask for it. The S-015
  `IngredientLine`, `_LinePayload` and prompt have no such field, so "2 onions,
  chopped" loses "chopped" or puts it in `note`.
- **Decision**: Add `preparation: str | None = None` to `IngredientLine`
  (domain), to `_LinePayload` (adapter) and to the prompt's ingredient fields
  ("preparation: how the ingredient is cut or prepared, for example 'chopped';
  never in the name"). `check_draft` trims it and turns blank into None. Update
  the spec 015 data model and contract with a dated note.
- **Rationale**: It is the smallest change that meets FR-010. It is additive, so
  existing fake scripts and tests still build.
- **Alternatives considered**: Put preparation in `note` and split it in the ui.
  Rejected: this mixes vague notes and preparation, and S-019 stores them in
  separate columns (`recipe_ingredient.preparation`, `vague_note`).

## R3. Use-case shape and check order

- **Decision**: `CaptureRecipeText` in `application/recipe_capture.py`:

  ```text
  execute(actor_user_id, notebook_id, text, language) -> CaptureOutcome
  ```

  The order is: (1) trim the text and check its length (refused → domain
  error), (2) load the notebook (missing → `NotebookNotFoundError`, 404),
  (3) a member-owned notebook must belong to the caller, otherwise the same 404,
  (4) a kitchen-owned notebook goes through `capture_recipe` authorization
  (404), then is refused when its kitchen is archived (`KitchenArchivedError`,
  409), (5) read the notebook's catalog, (6) call
  `RecipeExtraction.extract(text, names, timeout_s)`, (7) on a draft, pick chip
  labels in `language`. `CaptureOutcome` is the S-015 `ExtractionResult`, plus
  the notebook for a draft.
- **Rationale**: Ownership and membership come before the archive check, so a
  non-member cannot learn that a kitchen exists or is archived. A length check
  first means a too-long text costs nothing. A missing notebook and another
  member's notebook give the same 404, so ids are no existence oracle.
- **Access action**: add `capture_recipe` to the member actions that deny as
  not found (`_MEMBER_READ_ACTIONS`), with a comment that capture writes
  nothing. S-019's save will need its own action.
- **Alternatives considered**: Put the checks in the route. Rejected: the
  constitution requires membership checks in `application/`.

## R4. Chip labels in the member's language

- **Finding**: `DraftRecipe` has no language. Category values are ids
  (`poultry`, `mexican`). Labels exist in `categories.yaml` and `cuisine.yml` as
  `{en, es}`. Members already have a configured language (`users.language`,
  `en` or `es`, with `effective_language` as the fallback).
- **Decision (approved 2026-10-22)**: The capture route reads the member's
  configured language and returns each chip as `{id, label}` in it, using the
  other language when a label is missing. There is no detection logic. The draft
  text (title, names, steps) still follows the pasted text, with no translation
  (spec 015). `GET /recipe-vocabulary` returns both languages for the editor's
  pickers, and the ui picks by the same configured language.
- **Rationale**: Less logic, and it needs no new rules to test.
- **Alternatives considered**: Detect the text's language by stopword counts
  (rejected by the product owner: more logic). Ask Gemini for a `language`
  field (adds model dependence). A second extraction attempt in the other
  language (rejected: conflicts with the one-attempt rule, FR-025).
- **Spec follow-up**: FR-011 and the edge case "pasted text in Spanish in an
  English kitchen" say the labels follow the pasted text. They should say the
  labels follow the member's configured language.

## R5. Draft state between the text sheet and the draft page

- **Decision**: A client module store, `ui/lib/capture/captureStore.ts`, using
  `useSyncExternalStore` like `membershipKitchensStore.ts`. Its state is
  `{ notebook, text, sheetOpen, phase, draft, originalHash, edited (derived), language, message }`.
  Draft pages read it. When there is no draft (after a reload or a direct
  visit), they `router.replace` to the notebook's Notebook page.
- **Rationale**: The spec says the draft is gone on reload (Edge Cases) and is
  never saved, so no server or browser storage is needed. A module store
  survives client navigation between the Notebook page and the draft page.
- **Alternatives considered**: sessionStorage (would survive a reload, which
  goes against the spec). URL state (too large). React context in the layout
  (the two notebooks have different layouts, so it would have to live in
  AppShell anyway).

## R6. Configured paste limit and too-long message

- **Finding**: `RecipeTextRefusedError.TOO_LONG` (S-015) says "The text is longer
  than 10,000 characters. Paste one recipe at a time." FR-002 needs a message
  with the limit the member sees.
- **Decision (2026-10-22)**: The paste limit is the environment variable
  `RECIPE_TEXT_MAX_CHARS`, default 5,000, checked after trimming. The capture use
  case refuses with `text_too_long` and the configured limit in the message, "That
  text is too long. Paste up to {limit} characters.", before any assistant call.
  The pydantic body guard is twice the limit. The vocabulary route serves the
  limit so the ui shows the same number. S-015's 10,000-character refusal stays
  as spec 015's upper bound and is not changed.
- **Alternatives considered**: Change the S-015 constant to the new wording
  (rejected: it would fix one number in code). Hard-code 5,000 in the ui
  (rejected: two sources for one rule).

## R7. Asking before leaving an edited draft (FR-032)

- **Finding**: Next.js 16 App Router has no supported navigation-blocking API.
- **Decision**: `LeaveDraftGuard`, mounted on the draft page while
  `edited === true`:
  - A `click` listener on `document` in the capture phase. For a same-origin
    `<a href>` that leads away from the draft page (bottom tabs, kitchen
    switcher, chrome links), it calls `preventDefault()` and opens an
    `ActionDialog` with "Leave without saving? Your changes to this draft will
    be lost.", Leave and Stay. Leave clears the draft and `router.push(href)`.
  - `beforeunload` shows the browser's own warning on reload or close (the spec
    accepts this).
  - The draft page's Back and Discard controls call the store directly and are
    not intercepted.
- **Browser back gesture**: treated as Back (FR-031). The text sheet reopens
  with the text kept and no prompt. The store keeps the text, so nothing is
  lost.
- **Alternatives considered**: Patch `router.push`. Rejected: fragile across
  Next.js versions. Intercepting `popstate`: rejected because FR-031 exempts
  Back.

## R8. Draft rule checks in the ui

- **Decision**: `ui/lib/capture/draftRules.ts` implements the FR-013 rules
  (measured line has quantity > 0 and unit; vague line has neither; size only
  with `unit` and only small/medium/large; servings an integer of at least 1;
  title 1 to 200 characters after trimming; at least one step; at most two main
  ingredients and two cuisines). It returns a map from field path to message
  key. The units list and limits are constants in the same file, with a test
  that they match the api's `GET /recipe-vocabulary` `units` field.
- **Rationale**: Edits never leave the browser in this feature, so a
  server round trip per edit would add latency for no safety gain. S-019 runs
  `check_draft` on save.
- **Alternatives considered**: A `POST /drafts/check` route. Rejected for now:
  it adds no value until there is a save.

## R9. Meeting FR-026 end to end

- **Decision**: The api bounds the assistant call with the S-015 timeout
  (`GEMINI_TEXT_TIMEOUT_S`, default 10 s). The BFF capture routes add
  `AbortSignal.timeout((GEMINI_TEXT_TIMEOUT_S + 2) * 1000)`. They read the env
  var the ui container already gets through `env_file: .env`, with a default of
  10 when it is unset. On abort or network error the BFF returns 503
  `ai_unavailable`. The ui keeps the text in every non-200 case.
- **Rationale**: The member sees an answer within the bound even if the api is
  slow to answer for a reason other than the assistant.
- **Alternatives considered**: A ui-only constant of 12 s. Rejected: it would
  drift from the configured wait.

## R10. Kitchen page Notebook tab

- **Decision**: Add `ui/app/kitchens/KitchenSectionTabs.tsx`, two links
  (Members → `/kitchens/[id]`, Notebook → `/kitchens/[id]/notebook`) under the
  chrome header, styled like `ButtonGroup`. The Members content stays at
  `/kitchens/[id]`. The Notebook page fetches the kitchen detail (`name`,
  `is_archived`) the same way the current page does, and renders the call to
  action only when the kitchen is not archived (FR-033).
- **Rationale**: Existing links, tests and the invite flow stay as they are,
  and members and invites stay reachable (FR-001b).
- **Alternatives considered**: Make Notebook the default kitchen view. Deferred
  to S-020/S-046, when the kitchen has a recipe list to show.

## R11. Extraction use-case lifetime

- **Decision**: `get_recipe_extraction(request)` in `api/deps.py` builds one
  `RecipeExtraction(GeminiRecipeExtractor(...), load_vocabulary())` per app,
  cached on `app.state`, like `get_rate_limiter`. Tests replace it with
  `app.dependency_overrides[get_recipe_extraction]`, built on
  `FakeRecipeExtractor`.
- **Rationale**: The S-015 in-flight sharing (concurrent identical texts share
  one call) works only with one instance per process. The vocabulary is parsed
  once.

## R12. Bottom-bar Notebook tab

- **Decision (2026-10-22)**: Add a `{ key: "notebook", href: "/notebook", Icon: BookIcon }` item
  after Home in `AppShell`, labelled "Notebook". Add `/notebook` to `APP_CHROME_PREFIXES`, and map
  `/notebook` and `/notebook/*` to `"notebook"` in `tabKeyFromPath`. The kitchen's
  Notebook tab sits at `/kitchens/[id]/notebook` and stays on the `"home"` tab. A new
  `BookIcon` follows `ui/app/icons/README.md`.
- **Rationale**: `TabBar` is already data-driven. No `TabBar` change is needed.

## R13. Creating notebooks (moved to spec 055-notebooks)

- **Decision (2026-10-22, revised)**: Notebook creation and the notebook reads are
  delivered by `specs/055-notebooks`, merged before this feature starts.
  - A kitchen's notebook is created with the kitchen, in the same transaction as
    the kitchen and its owner membership (`CreateOwnedKitchenService`).
  - A member's notebook is created the first time the member asks for their
    default notebook (`GET /notebooks/members/{user_id}`). Its id is stored in the
    new nullable `users.default_notebook_id`, and a null value triggers the
    creation. The alias claim and the auth routes are not changed; the user
    model gains one column, approved by the owner on 2026-10-22. This replaces
    the earlier alias-claim hook.
  - Backfill in `0003` (spec 055): one notebook per existing kitchen and per
    existing user that has an alias, named "{alias}'s Notebook". Deleting the
    default notebook sets `default_notebook_id` to null, and the next call
    creates a new one silently.
- **Consequence for this feature**: capture reads notebooks and creates none, so
  FR-019 and SC-005 hold as written. The member's read route is owner-only: any
  other caller gets 404 `notebook_not_found`. The member's page calls the default
  route, so it does not need to know the notebook id first.
