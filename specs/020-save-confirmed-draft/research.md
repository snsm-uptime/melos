# Research: Save a Confirmed Draft into Its Notebook

Resolves the design questions for [plan.md](./plan.md). No NEEDS CLARIFICATION markers remain.

## R1. Recipe tables

- **Decision**: Migration `0005_recipes` creates `source`, `recipe`, `recipe_ingredient`, `step` as in PRD 1.6, minus `preview_image_base64`, `cart_add_count` and the category columns (later stories add them by their own migration).
- **Rationale**: Checked in code: only `ingredient` and `notebook` tables exist. Adding unused columns now breaks "build only what the story needs" (constitution §1).
- **Alternatives considered**: Creating the full PRD shape now (extra nullable columns with no reader or test).

## R2. Where the "new name" decision is made

- **Decision**: The server decides. The request carries each line's confirmed name; for each, the domain looks for a catalog entry with the same spelling (`same_spelling`, spec 018). Found: the line stores the entry's spelling. Not found: the name is new and is added to the catalog. The client sends no "matched" flag.
- **Rationale**: Satisfies FR-006/FR-007 and the edge case "different case or spacing resolves to the same entry". A client flag could be stale (catalog changed) or forged.
- **Alternatives considered**: Trusting the draft's `match` (stale-catalog risk); re-running the full spec 018 matcher with singular rules at save (would silently rename lines the member already confirmed, and contradicts "the confirmed name is stored").

## R3. Re-checking the edited draft

- **Decision**: Add a public `check_edited_draft` to `domain/recipe_draft.py` that runs the existing title, steps, servings and `_check_line` checks and the `DraftProblems` collection, without the matching step. `domain/recipe.py` wraps the result into `NewRecipe` (lines with resolved names, steps, flags).
- **Rationale**: One set of rules for capture and save (FR-005). The private helpers already hold every rule.
- **Alternatives considered**: Duplicating the rules in a new module (drift risk); calling `check_draft` with the catalog (it rewrites names, see R2).

## R4. Atomicity and "nothing before checks"

- **Decision**: The use case runs all checks and reads first (empty/length, notebook access, archived, rules, catalog read), then calls the repository once to insert source, recipe, lines, steps and catalog names. `get_db` commits after the request, even when the route returns a JSON error, so refusals must happen before any insert, and an insert failure must raise (not be caught) so `get_db` rolls back. The one deliberate early commit is the notebook created by `ResolveCaptureNotebookService` (FR-011), which already commits itself.
- **Rationale**: Matches the existing dependency behaviour; no new transaction machinery.
- **Alternatives considered**: An explicit unit-of-work port (new abstraction for one use case).

## R5. Repeated Save (idempotency)

- **Decision**: The ui makes a `save_key` (UUID) when it shows the draft and sends it with every Save of that draft. `recipe` gets a nullable `save_key` with a unique index on `(author_id, save_key)`. The use case first looks the pair up and, if found, returns that recipe with status 200 (first save 201). Two concurrent first saves: the second insert hits the unique index, the repository catches it in a savepoint, and the use case returns the stored recipe.
- **Rationale**: FR-013 and Story 3 scenario 5. The key lives on the recipe row, so no separate table. The draft itself is still never stored before Save.
- **Alternatives considered**: Disabling the button only (does not cover a dropped connection or a second tab); a content hash (two identical recipes saved on purpose would collide).

## R6. Capture notebook step

- **Decision**: The body carries `notebook_id` or, when the kitchen has none, `kitchen_id`. With `notebook_id` the draft's own notebook is used and never replaced (the capture step would ignore a stale pick when a kitchen has one notebook): `facts_for` (404 when missing or not visible), then the kitchen-archived check. With only `kitchen_id`: `ResolveCaptureNotebookService` (spec 056), which may create the kitchen notebook and commits it. `NotebookChoiceRequiredError` maps to 409 `notebook_choice_required`.
- **Rationale**: The text capture route needs an existing `notebook_id`, so the ui always sends one; the `kitchen_id` path exists for FR-011 and is covered by an application test.
- **Alternatives considered**: Dropping the `kitchen_id` path (leaves FR-011 untested and unreachable).

## R6a. Size limits

- **Decision**: The route schema limits `ingredient_lines` and `steps` to 100 each (spec FR-019); over the limit is 422 `invalid_recipe`. The text limit is `load_recipe_text_max_chars`.
- **Rationale**: Capture sets no line or step limit in code; the limit stops oversized bodies before any write.

## R7. Write access

- **Decision**: A caller who can read a notebook (owner or member of a personal notebook; member of the kitchen of a kitchen notebook) can write to it. `facts_for` plus the existing access rule in `domain/notebook.py` decide; no one else gets a row written.
- **Rationale**: PRD Appendix D: those who can write to the notebook are its members; spec 056 has no read-only role.

## R8. Source record

- **Decision**: Insert `source(type='text', raw_text=<pasted text>, user_id)` and link it from the recipe. The text is the capture input trimmed, limited by the same `load_recipe_text_max_chars`. It is not logged.
- **Rationale**: PRD 1.6 and spec FR-009. Deleting the source later keeps the recipe (`source_id` set null).
- **Alternatives considered**: Not storing the text (PRD says Source keeps it; "Imported recipes keep their source link").

## R9. Success notice

- **Decision**: `captureStore` holds a one-shot `savedNotice` (notebook id) set on success. `NotebookTabScreen` shows "Recipe saved" and clears it. A reload clears it.
- **Rationale**: Spec clarification: return to the notebook with a message. The store already survives client navigation and is already the home of capture state.
- **Alternatives considered**: A query parameter (stays in the URL and reappears on reload).

## R10. Error mapping

- **Decision**: 201 saved, 200 replay. 404 `notebook_not_found`. 409 `kitchen_archived`, 409 `notebook_choice_required`. 422 `draft_incomplete` and `ingredient_line_problem` (same body shapes as capture), 422 `invalid_recipe` for any other broken rule, 422 `text_too_long`. 401 from the auth dependency.
- **Rationale**: Reuses the capture route's codes so the ui message code is shared.

## R11. Logging

- **Decision**: Log the outcome, line count and step count; never the title, text or names (constitution §4).
