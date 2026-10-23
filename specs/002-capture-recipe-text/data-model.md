# Data Model: Capture a Recipe from Pasted Text

This feature writes nothing (FR-019, SC-005). It adds one table that it only
reads, one in-memory use-case value, and a client-only store. The draft shape is
the S-015 one ([spec 003 data model](../003-gemini-recipe-extractor/data-model.md)),
with one added field (`preparation`, research R2).

## Persisted (created by spec 004-notebooks, read-only in capture)

A notebook is its own entity: a kitchen has a notebook, a member has a
notebook, and neither is the notebook itself (research R1). The notebook id is
what recipes, copies and the ingredient catalog point at.

### `notebook` (spec 004, Alembic `0003_notebooks_ingredients`)

| Column | Type | Rules |
|--------|------|-------|
| `id` | uuid | PK, server default. |
| `kitchen_id` | uuid, nullable | FK `kitchens.id`, `ON DELETE CASCADE`, `UNIQUE`. |
| `user_id` | uuid, nullable | FK `users.id`, `ON DELETE CASCADE`. Not unique: the schema allows many notebooks per member. |
| `created_at` | timestamptz | Server default `now()`. |

Constraint: `CHECK ((kitchen_id IS NULL) <> (user_id IS NULL))` (exactly one
owner). `kitchen_id` is unique, so a kitchen has one notebook. The user table gains
a nullable `default_notebook_id` (FK `notebook.id`), set when the member first asks
for their default notebook. The migration backfills a notebook for every existing
kitchen and every existing user with an alias. A member notebook's `name` is
"{alias}'s Notebook"; a kitchen notebook has no name. `default_notebook_id` is
`ON DELETE SET NULL`. After that, a kitchen's notebook is created with the kitchen
(spec 004; research R13).

### `ingredient` (spec 004, same revision)

| Column | Type | Rules |
|--------|------|-------|
| `id` | uuid | PK, server default. |
| `notebook_id` | uuid | FK `notebook.id`, `ON DELETE CASCADE`. |
| `name` | text | Trimmed, lower-case, singular (written by S-019). |
| `created_at` | timestamptz | Server default `now()`. |

Constraint: `UNIQUE (notebook_id, name)`. Written first by S-019. This replaces
the `kitchen_id?` / `user_id?` owner columns in PRD Appendix A (cross-spec
change for review).

Reads in this feature:

| Step | Query |
|------|-------|
| Load the notebook | Kitchen route: `... WHERE kitchen_id = :kitchen_id`. Member route: `... WHERE id = :notebook_id AND user_id = :caller` |
| Catalog | `SELECT name FROM ingredient WHERE notebook_id = :notebook_id ORDER BY name`, only after access is granted |
| Member's language | `users.language` (existing), through `effective_language` |

### Existing tables read

| Table | Field | Why |
|-------|-------|-----|
| `kitchens` | `name`, `is_archived` | Notebook label, archive refusal (FR-033). |
| `kitchen_memberships` | row for (kitchen, actor) | Access (FR-022, FR-030). |
| `users` | `language` | Chip label language (research R4). |

## Domain changes

### `IngredientLine` (`domain/recipe_draft.py`, edit)

| Field | Type | Rules |
|-------|------|-------|
| `preparation` | str or None | **New.** How the ingredient is cut or prepared ("chopped"). Trimmed, and blank becomes None. Never part of `name` (FR-010). No other rule. |

All other fields and rules are unchanged from spec 003.

### Notebook (`domain/notebook.py`, new)

| Field | Type | Rules |
|-------|------|-------|
| `id` | UUID | |
| `kitchen_id` | UUID or None | Exactly one of `kitchen_id` and `user_id` is set. |
| `user_id` | UUID or None | |

`kind` is derived: `"kitchen"` when `kitchen_id` is set, otherwise `"member"`.

### Chip labels (`domain/notebook.py`)

`pick_label(labels: {"en", "es"}, language) -> str`: the label in `language`,
otherwise the other language. No text detection (research R4).

### Kitchen access (`domain/kitchen_access.py`, edit)

| Action | Who | Deny as |
|--------|-----|---------|
| `capture_recipe` | Any member (owner or member role) | 404 `kitchen_not_found` |

## Application values (`application/recipe_capture.py`, new; not stored)

### Capture attempt (spec Key Entity)

`CaptureRecipeText.execute(actor_user_id, owner, text, language) -> CaptureOutcome`, where `owner` is a kitchen id, or a user id and notebook id

| Outcome | Carries | From |
|---------|---------|------|
| `CapturedDraft` | `recipe: DraftRecipe`, `language: "en" \| "es"`, `notebook: Notebook`, `kitchen_name: str \| None` | S-015 `Draft` |
| S-015 `NotARecipe`, `Unavailable`, `LimitReached`, `InvalidOutput`, `AIProviderError` | as in spec 003 | passed through |

Raised before any assistant call (not outcomes):

| Error | When | HTTP |
|-------|------|------|
| `RecipeTextRefusedError` (S-015) | empty, or more than the configured limit after trimming (`RECIPE_TEXT_MAX_CHARS`, default 5,000; spec 003's own limit is 10,000) | 422 `text_empty` / `text_too_long` |
| `NotebookNotFoundError` (new, `domain/errors.py`) | notebook missing, another member's, or a kitchen notebook the caller is not a member of. Same body in every case. | 404 `notebook_not_found` |
| `KitchenArchivedError` (new, `domain/errors.py`) | the notebook's kitchen is archived | 409 `kitchen_archived` |

### Ports (`application/ports.py`; the notebook and catalog ports are spec 004's)

```text
NotebookRepository.get(notebook_id: UUID) -> Notebook | None
NotebookRepository.for_kitchen(kitchen_id: UUID) -> Notebook | None
NotebookRepository.for_member(user_id: UUID) -> Notebook | None
NotebookRepository.create(notebook: Notebook) -> None        # used by spec 004 when a notebook is created
IngredientCatalogReader.names_for_notebook(notebook_id: UUID) -> list[str]
```

## Client-only state (`ui/lib/capture/captureStore.ts`)

One store per browser tab. Reload clears it.

| Field | Type | Notes |
|-------|------|-------|
| `notebook` | `{ id, kind: "member" \| "kitchen", label }` | `label` is "My notebook" or the kitchen's name. Fixed when the sheet opens. Unchanged by kitchen switching (FR-001a). |
| `text` | string | The pasted text. Kept on every failure and on Back. Cleared on Discard. |
| `sheetOpen` | boolean | Reopened by Back from the draft page. |
| `phase` | `"idle" \| "submitting" \| "draft"` | `submitting` blocks a second submit (FR-004). |
| `message` | `{ key, reason? } \| null` | The last refusal or failure, shown in the sheet. |
| `draft` | `DraftView \| null` | The editable draft (below). |
| `originalHash` | string | Hash of the draft's editable content (title, servings, categories, ingredient lines, steps, in order) taken when the draft was first shown. |
| `edited` | boolean | Derived, not stored: true when the hash of the current content differs from `originalHash`. A change reverted by hand is not an edit. Turns on `LeaveDraftGuard`. |
| `language` | `"en" \| "es"` | From the response (the member's configured language). Picks chip labels. |

### `DraftView` (editable copy of the response draft)

| Field | Type | Edit rules (FR-012, FR-013) |
|-------|------|-----------------------------|
| `title` | string | 1–200 characters after trimming. |
| `baseServings` | number | An integer of at least 1. Editing clears the `servingsEstimated` badge. |
| `servingsEstimated` | boolean | Shown as the "estimated" badge. |
| `mainIngredients` | string[] (ids) | 0–2, from the vocabulary only. |
| `cuisines` | string[] (ids) | 0–2, from the vocabulary only. Variants show their tag. |
| `lines` | `LineView[]` | Can be added, removed and reordered. |
| `steps` | `{ id, text }[]` | Can be added, removed and reordered. At least one non-empty step. |

`LineView`: `{ id, name, vague, quantity, unit, size, preparation, note }`.
`id` is a client key for reordering only. Measured: `quantity > 0` and a unit
from `g, kg, oz, lb, ml, l, cup, tbsp, tsp, unit`. Vague: no quantity and no
unit. `size` is one of small, medium or large, and only when `unit === "unit"`.

### State transitions

```text
idle ──submit──▶ submitting ──200──▶ draft (navigate to draft page)
                    │
                    └──non-200──▶ idle + message (text kept)
draft ──Back────▶ idle, sheetOpen, text kept, draft dropped           (FR-031)
draft ──Discard─▶ idle, sheetOpen, text "", draft dropped             (FR-020)
draft ──leave (edited) ─▶ dialog: Stay → draft | Leave → idle, store cleared  (FR-032)
draft ──leave (not edited) ─▶ idle, store cleared
reload ─▶ store empty; draft page redirects to its Notebook page
```
