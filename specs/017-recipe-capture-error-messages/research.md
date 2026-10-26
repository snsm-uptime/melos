# Research: Clear Recipe Capture Error Messages

**Date**: 2026-10-25 | **Plan**: [plan.md](./plan.md)

No open NEEDS CLARIFICATION remain: the spec's two clarifications (2026-10-25) settle the required parts and the ingredient problem kinds. The items below record how the code works today and the decisions taken for the plan.

## R1. Collecting every missing part and line problem

**Current behaviour** (`api/domain/recipe_draft.py`): `check_draft` calls `_check_title`, `_check_steps`, `_check_servings` and `_check_line` in order. Each raises `InvalidDraftError` on the first failure. `_check_line` raises `"quantity"` for a missing or non-positive quantity, and `lookup_unit` returning `None` (including an empty unit) raises a unit error.

**Application today** (`api/application/recipe_extraction.py`, `_evaluate`): any `InvalidDraftError` is logged by rule name and turned into `InvalidOutput`, so the member sees the generic unreadable-answer message.

**Decision**: `check_draft` runs every check and collects:
- `missing`: a tuple of `"title"` and/or `"steps"` (empty title or no non-blank step).
- `line_problems`: a tuple of `(name, kind)` pairs, one per problem, where `name` is the ingredient's name as the domain normalizes it and `kind` is `quantity_missing`, `unit_missing` or `unit_not_recognized`. A line with neither quantity nor unit gives two entries with the same name. The name is cleaned by `clean_display_name` (plan Design Decision 5) before it leaves the api; the domain keeps the raw normalized name for matching.

If `missing` or `line_problems` is non-empty, `check_draft` raises `DraftProblems(missing, line_problems)`. Otherwise, if another rule breaks, it raises the existing `InvalidDraftError` (generic). Servings, name and vague-line checks run after the collection so that named problems take precedence.

**Rationale**: Spec FR-003 and US1 acceptance 3 require naming every missing part. Domain stays pure: it returns kinds, not text.

**Alternatives considered**:
- Return a list of messages from the domain. Rejected: moves English into `domain/` (FR-010, constitution §3).
- Keep first-failure raising and add a second pass in the use case. Rejected: duplicates the rules.

## R2. The not-a-recipe reason

**Current behaviour** (`api/adapters/llm/gemini_extractor.py`): `RESPONSE_SCHEMA.reason` is a free string, capped at 120 characters and rejected if it has a newline. `_payload_to_result` returns `NotARecipe(reason=<model text>)`. The route puts that text in `detail`, and `messageForCode` appends it to the fixed sentence in the ui. That shows assistant text to the member, which FR-007 forbids.

**Decision**: The `outcome` stays. For `not_a_recipe`, the model returns `reason` as one value of an enum: `question_or_request` (kept, confirmed 2026-10-25), `not_food`, `story_or_article`. It also returns an optional `ingredient` string when the text is a question about one ingredient (FR-013); the adapter cleans it with `clean_display_name` and passes `None` on failure. The adapter maps the value to a `NotRecipeReason` enum. An unknown or missing value is `InvalidOutput`. `prompt.py` lists each value with one line of meaning. The application and route use the enum; the ui shows one fixed sentence per value.

**Rationale**: Keeps the model's judgement (it already classifies the text) and removes free text from the member's view. A closed set is testable with the AI evaluation fixtures.

**Alternatives considered**:
- Drop the reason and show one fixed "doesn't look like a recipe" sentence. Rejected: spec FR-004 requires a reason in plain words.
- Keep free text and check it against a word list. Rejected: fragile, and the model still produces text the member sees.

**Open**: the three values are a proposal; see plan.md Design Decisions 4.

## R3. Route and client mapping

**Current behaviour**: `api/api/routes/recipe_capture.py` maps `NotARecipe` with `ONE_RECIPE_REASON` to `one_recipe_at_a_time`, and any other `NotARecipe` to `not_a_recipe` with the reason as `detail`. `InvalidOutput` maps to `ai_invalid_output`. `ui/lib/capture/captureClient.ts` copies `detail` into `reason` for `not_a_recipe`.

**Decision**:
- `NotRecipeReason` value → `not_a_recipe` with `detail` = the enum value (a fixed token, never prose) and the same 422 status.
- `DraftProblems` → 422 `draft_incomplete` with `missing` and `line_problems` lists, or `ingredient_line_problem` when only line problems exist. Both use `{detail, code}` plus the lists.
- `ONE_RECIPE_REASON` path keeps `one_recipe_at_a_time`.
- `InvalidOutput` keeps `ai_invalid_output`.
- The client drops the `reason` copy and reads the lists.

**Rationale**: Same status and code family as spec 016 (contracts/capture-api.md), so tests and the BFF keep working. Only the body of the 422 changes.

**Alternatives considered**: a new HTTP status per case. Rejected: PRD §1.7 maps by status family, and `code` already tells the cases apart.

## R4. Message wording

**Decision**: New fixed strings in `ui/lib/i18n/capture.ts` (English, one file, FR-010). Exact wording is in `contracts/capture-messages.md`. Every string is a fixed sentence with no interpolated assistant text; the only interpolated values are the numeric limit (already present) and the field names chosen by the app.

**Rationale**: Spec wording is the source of truth; contracts file lists each code, reason and message so reviewers can check SC-005.

## R5. Text kept in the box

**Current behaviour**: The sheet keeps the pasted text in client state on every failure (spec 016 FR-008, `captureStore.ts`).

**Decision**: No change to the store. Add a vitest case per new code asserting the text remains in the textarea after the message appears (SC-004).

## R6. Logging

**Current behaviour**: `_evaluate` logs the rule name only; `recipe_capture.py` logs the outcome type and text length.

**Decision**: Log the problem kinds (e.g., `missing=title,steps line_problems=unit_missing`) and the reason enum value. Never log ingredient names, titles or text. This keeps constitution §4.

## R7. Unchanged behaviour

Spec FR-011: the too-long, availability (`ai_unavailable`), usage-limit (`ai_limit_reached`) and not-set-up (`ai_misconfigured`) messages keep spec 016 wording. Notebook and kitchen access refusals (`notebook_not_found`, `kitchen_archived`) are unchanged.
