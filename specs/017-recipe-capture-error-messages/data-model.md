# Data Model: Clear Recipe Capture Error Messages

**Date**: 2026-10-25 | **Plan**: [plan.md](./plan.md)

**Persistence**: None. This feature adds no table, column or stored value (spec: Key Entities N/A). The values below exist only while a capture request is handled, and in the browser's memory on the capture sheet.

## Value types (api, in-memory)

### `DraftProblems` (domain, `api/domain/recipe_draft.py`)

Raised by `check_draft` when at least one named problem exists.

| Field | Type | Rule |
|-------|------|------|
| `missing` | tuple of `"title"` \| `"steps"` | In that order; empty tuple when both present |
| `line_problems` | tuple of `LineProblem` | One entry per problem; a line with no quantity and no unit gives `quantity_missing` and `unit_missing` |

### `LineProblem` (domain)

| Field | Type | Rule |
|-------|------|------|
| `name` | string | The ingredient's normalized name (for "1/4 butter", `butter`). Cleaned to a display name before it leaves the api; `null` when the cleaning check fails |
| `kind` | `LineProblemKind` | As below |

### `clean_display_name(raw) -> str | None` (domain, pure)

Trims, collapses spaces, allows at most 40 characters, letters (any language), spaces, hyphens and apostrophes only. Returns `None` otherwise, including for empty input.

### `LineProblemKind` (domain, string enum)

| Value | Meaning | Spec |
|-------|---------|------|
| `quantity_missing` | No quantity, or a quantity that is not a positive finite number | FR-012 |
| `unit_missing` | Non-vague line with no unit | FR-012 |
| `unit_not_recognized` | Unit not in the app's unit list | FR-012 |

Vague lines (`vague: true`) never produce these kinds.

### `NotRecipeReason` (application, string enum)

| Value | Meaning |
|-------|---------|
| `question_or_request` | The text asks something instead of giving a recipe |
| `not_food` | The text is about something other than food |
| `story_or_article` | The text is a story, article or list, not a recipe |

The model returns one of these in `reason`; any other value is `InvalidOutput`.

### Outcomes (application, `api/application/recipe_extraction.py`)

| Outcome | Change |
|---------|--------|
| `Draft` | unchanged |
| `NotARecipe(reason: NotRecipeReason, ingredient: str \| None)` | `reason` was free text; now the enum. `ingredient` is the cleaned name for a question about one ingredient (FR-013). `ONE_RECIPE` remains a separate path, see below |
| `DraftIncomplete(problems: DraftProblems)` | new: returned for named problems |
| `InvalidOutput` | unchanged: generic breaks and unreadable answers |
| `Unavailable`, `LimitReached`, `AIProviderError` | unchanged |

`NotARecipe` for several recipes keeps its `multiple_recipes` path; the enum gains `multiple_recipes` as a fourth value so the route can tell it apart without string comparison. (Decision recorded here; the route maps it to `one_recipe_at_a_time`.)

## Relationships

- `DraftProblems` → `missing` and `line_problems` (no other link).
- Each `LineProblemKind` value maps to one fixed sentence in `ui/lib/i18n/capture.ts` through its API code (see `contracts/capture-messages.md`).

## Validation rules

- Missing parts and line problems are checked in the same pass, so one refusal names all of them (FR-003, US1 AS3).
- The ingredient list is not checked for presence (spec Assumptions).
- `missing` and `line_problems` are never both empty when `DraftProblems` is raised.
