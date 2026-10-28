# Data Model: Recipe Extraction Assistant Adapter

> **Scope change 2026-10-27:** main ingredients and cuisines are out of the MVP (backlog S-061, PRD Appendix E). Anything below about them (main ingredient keys, cuisine scoring, category chips, the `main_ingredients` and `cuisines` fields, the category lists of `GET /recipe-vocabulary`) is not in force; the code is commented out under `MVP-OUT:`. Ingredient catalog matching (S-018) is unchanged. Plan: `dev/docs/mvp-descope-categories.md`.

Nothing here is persisted (FR-011, SC-007). All types are in-memory values
returned to the caller. No table, no Alembic revision.

## Extraction request (input value)

| Field | Type | Rules |
|-------|------|-------|
| `text` | str | Required. Refused before any call when empty or whitespace-only (FR-012). Refused with an input refusal when longer than 10,000 characters; that refusal is not a service failure. |
| `ingredient_names` | list[str] | Kitchen's existing names. Used only as a preference hint. |
| `timeout_s` | float | 10 for text and URL input, 30 for image input (FR-013). Supplied by the caller. |

## Draft recipe (`domain/recipe_draft.py`)

| Field | Type | Rules |
|-------|------|-------|
| `title` | str | Non-empty. |
| `base_servings` | int | A whole number of at least 1 (FR-006). |
| `servings_estimated` | bool | True when the text gives no servings and the value was estimated (User Story 1, scenario 4). |
| `main_ingredients` | list[str] | Zero to two keys from `categories.yaml#/categories/main_ingredient`. Zero is allowed (FR-006). |
| `cuisines` | list[str] | Zero to two tag or variant ids from `cuisine.yml`, scored on the title and steps and ranked by total matches, one per tag (`categories.yaml#/matching/cuisine`). A variant is shown with its tag. If none matches, `[international]` (FR-006). |
| `ingredient_lines` | list[IngredientLine] | See below. |
| `steps` | list[str] | Same shape the capture review screen shows. |

### IngredientLine

| Field | Type | Rules |
|-------|------|-------|
| `name` | str | Lower-case, singular (FR-006). Existing catalog spelling preferred when it matches. |
| `vague` | bool | True for amounts such as "a pinch of salt". |
| `quantity` | number or None | Non-vague: greater than 0. Vague: must be None. |
| `unit` | enum or None | Allowed set: `g, kg, oz, lb, ml, l, cup, tbsp, tsp, unit`. Non-vague: required. Vague: must be None. A unit matched through the FR-006a table is replaced by its allowed unit without converting the quantity (e.g. "tablespoon" → "tbsp"). A unit with no exact match that is one edit away from a table spelling (e.g. "tablespon") and is 5 or more characters long is matched the same way; one edit away from the spellings of more than one allowed unit, or any other unknown unit, is invalid output. |
| `size` | enum or None | One of `small, medium, large`, and only when `unit == "unit"`. Otherwise, or when the value is not one of those three, the size is removed and the line is kept (spec Edge Cases). |
| `note` | str or None | Free text, used for vague notes (e.g. "to taste"). |
| `preparation` | str or None | Added 2026-10-22 (spec 016 plan review). How the ingredient is cut or prepared ("chopped"). Trimmed; blank becomes None. Never part of `name`. No other rule. |

**Validation (FR-006, enforced in domain)**:
- A non-vague line has `quantity > 0` and a `unit`. An empty unit is invalid output.
- A vague line has no `quantity` and no `unit`.
- `size` is set only when `unit == "unit"`.
- Any rule failure makes the whole draft "invalid output". A draft that breaks a rule is never returned (SC-003).

## Extraction result (`application/recipe_extraction.py`)

Closed set; exactly one per call.

| Variant | Carries | Notes |
|---------|---------|-------|
| `Draft` | `recipe: DraftRecipe` | Passed all rules. |
| `NotARecipe` | `reason: str` | Includes two or more recipes (reason "Only one recipe at a time"). S-016 shows the member "Upload only one recipe at a time". Normal result, not a failure (FR-002). |
| `Unavailable` | — | Timeout, unreachable, or server error. |
| `LimitReached` | `retry_after_seconds: int or None` | Carries the wait hint only when the service gave one, as a whole number of seconds. Zero, negative or non-numeric hints are None; fractions are rounded (FR-004). |
| `InvalidOutput` | — | Unreadable result or rule break. |
| `AIProviderError` | — | Key or model name missing or empty. No call is made to the service. |

No variant carries raw service text, the key, or a stack trace (FR-008, SC-006).

## Stand-in result set (test-only)

| Field | Type | Notes |
|-------|------|-------|
| `results` | sequence of `ExtractionResult` | Returned in order per call; the same value is returned for every call when a single value is given. |

## State transitions

One piece of in-progress state: a map from text hash (SHA-256 of the trimmed text) to the single in-flight service call. An entry exists only while that call runs and is removed when it ends (FR-016). Nothing is written to storage.
