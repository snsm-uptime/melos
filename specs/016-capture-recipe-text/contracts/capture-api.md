# Contract: Capture API (HTTP)

> **Scope change 2026-10-27:** main ingredients and cuisines are out of the MVP (backlog S-061, PRD Appendix E). Anything below about them (main ingredient keys, cuisine scoring, category chips, the `main_ingredients` and `cuisines` fields, the category lists of `GET /recipe-vocabulary`) is not in force; the code is commented out under `MVP-OUT:`. Ingredient catalog matching (S-018) is unchanged. Plan: `dev/docs/mvp-descope-categories.md`.

Normative status: this contract is normative for paths, status codes, `code`
values and field names. `spec.md` is normative for behaviour and member-facing
wording. The ui shows its own text for each `code`. It never shows `detail` or
any upstream text (FR-029).

All routes need the session cookie and an alias (`require_user_alias`):
401 when signed out, 403 `alias_required` without an alias (existing
behaviour). The browser calls them only through the BFF (below).

Revised 2026-10-25 to spec 056's final routes. A capture is addressed by one
notebook id, personal or kitchen, so there is one capture route.

## Notebook reads (defined in spec 056-notebooks)

This feature uses these reads. Their answers are the `NotebookResponse` shape of
[spec 056's contract](../../056-notebooks/contracts/notebooks-api.md#the-notebook-object);
`kind` is `"personal"` or `"kitchen"`.

- `GET /notebooks/default`: the caller's default personal notebook (created on the first call).
  The member's Notebook page uses it.
- `GET /notebooks`: the caller's personal notebooks, for the picker outside a kitchen.
- `GET /notebooks/kitchens/{kitchen_id}`: the kitchen's notebooks. Its first call creates
  the kitchen's notebook (FR-008a). The kitchen's Notebook page uses it, so a capture from
  that page always has a notebook id.
- `GET /notebooks/{notebook_id}`: one notebook, with `kitchen_is_archived` for a kitchen
  notebook. A missing notebook and one the caller does not belong to give the same
  404 `notebook_not_found`.

## `POST /notebooks/{notebook_id}/captures/text`

Capture for one notebook the caller can write to: a personal notebook the caller owns or
belongs to, or a kitchen notebook of a kitchen the caller is a member of (FR-001a,
FR-022). Membership is checked first; then, for a kitchen notebook, the archive state is
checked (FR-030, FR-033). Nothing is stored (FR-019).

### Request

```json
{ "text": "string" }
```

The body is guarded by pydantic at twice `RECIPE_TEXT_MAX_CHARS` (10,000 with the
default). Over that guard the response is 422 `text_too_long`, with the same message as
the use case. The limit after trimming, `RECIPE_TEXT_MAX_CHARS` (5,000 by default), is
checked in `application/` before any assistant call.

### 200: draft

```json
{
  "outcome": "draft",
  "notebook": { "id": "<uuid>", "kind": "personal", "name": "ana's Notebook" },
  "language": "en",
  "draft": {
    "title": "Onion soup",
    "base_servings": 4,
    "servings_estimated": true,
    "ingredient_lines": [
      { "name": "salt", "vague": true, "quantity": null, "unit": null,
        "size": null, "preparation": null, "note": "a pinch" },
      { "name": "onion", "vague": false, "quantity": 2, "unit": "unit",
        "size": "large", "preparation": "chopped", "note": null }
    ],
    "steps": [ "Chop the onions.", "Cook with salt." ]
  }
}
```

- `notebook` is the notebook the capture was made for: `kind` `"personal"` or `"kitchen"`,
  with `name` (the stored name, spec 056) and, for a kitchen, `kitchen_id`.
- `language` is the member's account language (`users.language`, through
  `effective_language`). Chip labels use it, and the other language for a label missing in
  it (research R4).
- Ingredient names are exactly as returned by the assistant (FR-024).

### Errors

| Status | `code` | When | Extra fields |
|--------|--------|------|--------------|
| 404 | `notebook_not_found` | Notebook missing, a personal notebook the caller neither owns nor belongs to, or a kitchen notebook of a kitchen the caller is not a member of. Same body in every case. | |
| 409 | `kitchen_archived` | The kitchen notebook's kitchen is archived. Only members get this answer. No assistant call. | |
| 422 | `text_empty` | Empty or whitespace-only. No assistant call. | |
| 422 | `text_too_long` | More than `RECIPE_TEXT_MAX_CHARS` after trimming (default 5,000). No assistant call. | |
| 422 | `not_a_recipe` | `NotARecipe` with any reason other than the one-recipe reason. | `reason` (string, at most 120 characters) |
| 422 | `one_recipe_at_a_time` | `NotARecipe` with reason "Only one recipe at a time". | |
| 422 | `ai_invalid_output` | `InvalidOutput`. | |
| 429 | `ai_limit_reached` | `LimitReached`. `Retry-After` header when `retry_after_seconds` is set. | |
| 503 | `ai_unavailable` | `Unavailable`. | |
| 503 | `ai_misconfigured` | `AIProviderError`. | |

Error body shape (as in the existing routes):

```json
{ "detail": "<plain sentence>", "code": "<code>" }
```

`detail` never contains service error text, keys or traces.

## `GET /recipe-vocabulary`

Read-only controlled lists for the draft editor (FR-011, FR-012). Same for every member,
so it can be cached.

### 200

```json
{
  "units": ["g", "kg", "oz", "lb", "ml", "l", "cup", "tbsp", "tsp", "unit"],
  "sizes": ["small", "medium", "large"],
  "max_text_chars": 5000
}
```

`max_text_chars` is the configured paste limit (`RECIPE_TEXT_MAX_CHARS`), so the ui
shows the same limit as the api.

Out of the MVP (2026-10-27, S-061): `max_main_ingredients`, `max_cuisines`, `main_ingredients`
and `cuisines` were removed from this answer, and `main_ingredients` and `cuisines` from the
draft above.

## BFF (ui → api)

| ui route | Method | api route |
|----------|--------|-----------|
| `/api/notebooks/[notebookId]/captures/text` | POST | `/notebooks/{notebook_id}/captures/text` |
| `/api/recipe-vocabulary` | GET | `/recipe-vocabulary` |

The read BFF routes (`/api/notebooks/default`, `/api/notebooks`,
`/api/notebooks/kitchens/[kitchenId]`, `/api/notebooks/[notebookId]`) are delivered by
spec 056.

- Forwards the `cookie` header, `Content-Type: application/json`, and the status, body
  and `Retry-After` as received.
- The capture route aborts the upstream call after `(GEMINI_TEXT_TIMEOUT_S || 10) + 2`
  seconds. On abort or network failure it answers 503 `{ "code": "ai_unavailable" }`
  (research R9). Other upstream failures answer 502 `bad_gateway`, as the existing BFF
  routes do. The ui treats 502 like `ai_unavailable` for messages.
- An invalid JSON body answers 400 `invalid_body` without calling the api.

## ui message per code (`ui/lib/i18n/capture.ts`, en)

| `code` | Message |
|--------|---------|
| `not_a_recipe` | "That doesn't look like a recipe." + `reason` |
| `one_recipe_at_a_time` | "Upload only one recipe at a time" |
| `ai_unavailable`, `bad_gateway` | "The assistant isn't responding. Your text is kept — try again." |
| `ai_limit_reached` | "We've hit the assistant's limit. Try again in a minute." |
| `ai_invalid_output` | "We couldn't read that recipe. Try rephrasing or adding detail." |
| `ai_misconfigured` | "Assistant misconfigured. Your text is kept" |
| `text_too_long` | "That text is too long. Paste up to {max_text_chars} characters." (the configured limit) |
| `text_empty` | (not shown; submit is disabled) |
| `kitchen_archived` | "This kitchen is archived, so recipes can't be added." |
| `notebook_not_found` | The sheet shows the kitchen's not-found text (`kitchensMessages.detailNotFound`), and the text is kept. |
| any other | The `ai_unavailable` message. |
