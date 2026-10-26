# Data Model: Capture a Recipe from Pasted Text

This feature writes nothing (FR-019, SC-005). It adds no table. It reads notebooks
and their catalogs, uses one in-memory use-case value, and has a client-only store.
The draft shape is the S-015 one ([spec 015 data model](../015-gemini-recipe-extractor/data-model.md)),
with one added field (`preparation`, research R2).

Revised 2026-10-25 to spec 056's final model (`specs/056-notebooks/data-model.md`).

## Persisted (created by spec 056-notebooks, read-only in capture)

A notebook is its own entity. A personal notebook has an owner and members; a kitchen
notebook belongs to one kitchen, which can have several (research R1).

### `notebook` (spec 056)

| Column | Type | Rules |
|--------|------|-------|
| `id` | uuid | PK, `gen_random_uuid()`. |
| `name` | text | Not blank. Fixed at creation (for example "ana's Notebook"). |
| `kitchen_id` | uuid, nullable | FK `kitchens.id`, `ON DELETE CASCADE`. Set: a kitchen notebook. Null: a personal notebook. |
| `owner_user_id` | uuid, nullable | FK `users.id`, `ON DELETE SET NULL`. Set on a kitchen notebook: the member who first opened or captured into it (FR-002). Null on a personal notebook, whose owner is its `notebook_membership` row with role `owner`. |
| `source_notebook_id` | uuid, nullable | Origin label of a snapshot. Never set by this feature (S-035). |
| `created_at` | timestamptz | `now()` default. |

A kitchen's first notebook is created on the first open of its notebook list, or on the
first saved capture (spec 056 FR-008a, FR-009). The migration backfills existing kitchens
and users (spec 056).

### `notebook_membership` (spec 056, personal notebooks only)

| Column | Type | Rules |
|--------|------|-------|
| `notebook_id` | uuid | FK `notebook.id`, `ON DELETE CASCADE`. |
| `user_id` | uuid | FK `users.id`, `ON DELETE CASCADE`. |
| `role` | text | `owner` or `member`. |
| `created_at` | timestamptz | `now()` default. |

Primary key `(notebook_id, user_id)`.

### `ingredient` (spec 056)

| Column | Type | Rules |
|--------|------|-------|
| `id` | uuid | PK, `gen_random_uuid()`. |
| `notebook_id` | uuid | FK `notebook.id`, `ON DELETE CASCADE`. |
| `name` | text | A normalized name (trimmed, lower-case, singular). Written first by S-020. |
| `created_at` | timestamptz | `now()` default. |

Constraint: `UNIQUE (notebook_id, name)`. Each notebook has its own catalog.

### `users` (spec 056)

`default_notebook_id` (uuid, nullable, FK `notebook.id`, `ON DELETE SET NULL`): the
member's default personal notebook, created on first use.

Reads in this feature:

| Step | Query |
|------|-------|
| Load the notebook | By id (spec 056 `NotebookRepository.get`). |
| Access to a personal notebook | `notebook_membership` row for (notebook, caller). Otherwise 404. |
| Access to a kitchen notebook | Kitchen membership for (kitchen, caller). Otherwise 404. |
| Archive state | `kitchens.is_archived` of the notebook's kitchen, after access is granted (FR-033). |
| Catalog | `SELECT name FROM ingredient WHERE notebook_id = :notebook_id ORDER BY name`, only after access is granted. Spec 056 `IngredientCatalog.names_for_notebook`. |
| Member's language | `users.language` (existing), through `effective_language`. |

### Existing tables read

| Table | Field | Why |
|-------|-------|-----|
| `kitchens` | `name`, `is_archived` | Notebook label, archive refusal (FR-033). |
| `kitchen_memberships` | row for (kitchen, actor) | Access (FR-022, FR-030). |
| `users` | `language` | Chip label language (research R4). |

## Domain changes

### `IngredientLine` (`domain/recipe_draft.py`, edit)

| Field | Type | Rules |
|--------|------|-------|
| `preparation` | str or None | **New.** How the ingredient is cut or prepared ("chopped"). Trimmed, and blank becomes None. Never part of `name` (FR-010). No other rule. |

All other fields and rules are unchanged from spec 015.

### Notebook kind (spec 056 `domain/notebook.py`, reused)

`kind` is `"personal"` when `kitchen_id` is null, otherwise `"kitchen"`. Capture uses
the spec 056 value and adds no new notebook type.

### Chip labels (`domain/notebook.py` or `domain/labels.py`)

`pick_label(labels: {"en", "es"}, language) -> str`: the label in `language`,
otherwise the other language. No text detection (research R4).

### Kitchen access (`domain/kitchen_access.py`, edit)

| Action | Who | Deny as |
|--------|-----|---------|
| `capture_recipe` | Any member (owner or member role) | 404 `notebook_not_found` (the capture route's answer; the kitchen is not revealed) |

## Application values (`application/recipe_capture.py`, new; not stored)

### Capture attempt (spec Key Entity)

`CaptureRecipeText.execute(actor_user_id, notebook_id, text, language) -> CaptureOutcome`.

| Outcome | Carries | From |
|---------|---------|------|
| `CapturedDraft` | `recipe: DraftRecipe`, `language: "en" \| "es"`, `notebook: Notebook` | S-015 `Draft` |
| S-015 `NotARecipe`, `Unavailable`, `LimitReached`, `InvalidOutput`, `AIProviderError` | as in spec 015 | passed through |

Raised before any assistant call (not outcomes):

| Error | When | HTTP |
|-------|------|------|
| `RecipeTextRefusedError` (S-015) | empty, or more than the configured limit after trimming (`RECIPE_TEXT_MAX_CHARS`, default 5,000; spec 015's own limit is 10,000) | 422 `text_empty` / `text_too_long` |
| `NotebookNotFoundError` (spec 056, reused) | notebook missing, not one the caller belongs to, or a kitchen notebook of a kitchen the caller is not a member of. Same body in every case. | 404 `notebook_not_found` |
| `KitchenArchivedError` (spec 056, reused) | the kitchen notebook's kitchen is archived (checked after membership) | 409 `kitchen_archived` |

### Ports (`application/ports.py`; the notebook and catalog ports are spec 056's)

```text
NotebookRepository.get(notebook_id: UUID) -> Notebook | None      # spec 056
IngredientCatalog.names_for_notebook(notebook_id: UUID) -> list[str]   # spec 056
```

## Client-only state (`ui/lib/capture/captureStore.ts`)

One store per browser tab. Reload clears it.

| Field | Type | Notes |
|-------|------|-------|
| `notebook` | `{ id, kind: "personal" \| "kitchen", name }` | The notebook the capture is for, chosen in the sheet's picker and fixed when the sheet opens. Unchanged by kitchen switching (FR-001a). |
| `text` | string | The pasted text. Kept on every failure and on Back. Cleared on Discard. |
| `sheetOpen` | boolean | Reopened by Back from the draft page. |
| `phase` | `"idle" \| "submitting" \| "draft"` | `submitting` blocks a second submit (FR-004). |
| `message` | `{ key, reason? } \| null` | The last refusal or failure, shown in the sheet. |
| `draft` | `DraftView \| null` | The editable draft (below). |
| `originalHash` | string | Hash of the draft's editable content (title, servings, categories, ingredient lines, steps, in order) taken when the draft was first shown. |
| `edited` | boolean | Derived, not stored: true when the hash of the current content differs from `originalHash`. A change reverted by hand is not an edit. Turns on `LeaveDraftGuard`. |
| `language` | `"en" \| "es"` | From the response (the member's account language). Picks chip labels. |

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
