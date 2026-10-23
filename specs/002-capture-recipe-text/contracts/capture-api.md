# Contract: Capture API (HTTP)

Normative status: this contract is normative for paths, status codes, `code`
values and field names. `spec.md` is normative for behaviour and member-facing
wording. The ui shows its own i18n text for each `code`. It never shows
`detail` or any upstream text (FR-029).

All routes need the session cookie and an alias (`require_user_alias`):
401 when signed out, 403 `alias_required` without an alias (existing
behaviour). The browser calls them only through the BFF (below).

## Notebook reads (defined in spec 004-notebooks)

This feature uses two reads that spec 004 delivers. Their shapes are listed here
for reference only.

- `GET /notebooks/kitchens/{kitchen_id}`: any member may read it. A missing kitchen
  and a non-member give the same 404 `kitchen_not_found`.

  ```json
  { "id": "<uuid>", "kind": "kitchen", "kitchen_id": "<uuid>", "name": "Test Kitchen", "is_archived": false }
  ```

- `GET /notebooks/members/{user_id}/{notebook_id}`: only the owner may read it. Any
  other caller, and a missing notebook, get the same 404 `notebook_not_found`.

  ```json
  { "id": "<uuid>", "kind": "member", "user_id": "<uuid>", "name": "Ana's Notebook" }
  ```

- `GET /notebooks/members/{user_id}`: returns the member's default notebook in the
  same shape. The first call creates it when the member has none, and a deleted
  default is created again on the next call. The answer has the same shape and
  status either way, so the ui never sees whether it was created. The member's
  page uses this route.

## `POST /notebooks/kitchens/{kitchen_id}/captures/text` and `POST /notebooks/members/{user_id}/{notebook_id}/captures/text`

Capture for one notebook. The kitchen route targets the kitchen's notebook: the
caller must be a member, and then the kitchen's archive state is checked
(FR-022, FR-030, FR-033). The member route targets the member's own notebook: the
path `user_id` must be the caller, and any other caller gets 404
`notebook_not_found`.

### Request

```json
{ "text": "string" }
```

The body is guarded by pydantic at twice `RECIPE_TEXT_MAX_CHARS` (10,000 with
the default) to reject grossly oversized payloads. Over that guard the response
is 422 `text_too_long`, with the same message as the use case. The limit after
trimming, `RECIPE_TEXT_MAX_CHARS` (5,000 by default), is checked in `application/`
before any assistant call.

### 200: draft

```json
{
  "outcome": "draft",
  "notebook": { "id": "<uuid>", "kind": "member", "label": null },
  "language": "en",
  "draft": {
    "title": "Onion soup",
    "base_servings": 4,
    "servings_estimated": true,
    "main_ingredients": [ { "id": "poultry", "label": "Poultry" } ],
    "cuisines": [
      { "id": "international", "label": "International", "tag": null }
    ],
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

- For a kitchen notebook, `notebook` is `{ "id": "<uuid>", "kind": "kitchen", "label": "<kitchen name>" }`.
- A cuisine `tag` is `{ "id", "label" }` when the cuisine is a variant, otherwise null.
- `language` is the member's configured language. Chip labels use it, and the other language for a label missing in it (research R4).
- Ingredient names are exactly as returned by the assistant (FR-024).

### Errors

| Status | `code` | When | Extra fields |
|--------|--------|------|--------------|
| 404 | `notebook_not_found` | Notebook missing, another member's, or a kitchen notebook the caller is not a member of. Same body in every case. | |
| 409 | `kitchen_archived` | The notebook's kitchen is archived. No assistant call. | |
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

Read-only controlled lists for the draft editor (FR-011, FR-012). Same for
every member, so it can be cached.

### 200

```json
{
  "units": ["g", "kg", "oz", "lb", "ml", "l", "cup", "tbsp", "tsp", "unit"],
  "sizes": ["small", "medium", "large"],
  "max_main_ingredients": 2,
  "max_cuisines": 2,
  "max_text_chars": 5000,
  "main_ingredients": [
    { "id": "poultry", "label": { "en": "Poultry", "es": "Aves" } }
  ],
  "cuisines": [
    { "id": "mexican", "label": { "en": "Mexican", "es": "Mexicana" }, "tag": null },
    { "id": "oaxacan", "label": { "en": "Oaxacan", "es": "Oaxaqueña" }, "tag": "mexican" },
    { "id": "international", "label": { "en": "International", "es": "Internacional" }, "tag": null }
  ]
}
```

`max_text_chars` is the configured paste limit (`RECIPE_TEXT_MAX_CHARS`), so the ui
shows the same limit as the api.

Cuisines include every tag and variant node that `score_cuisines` can assign,
plus the fallback. `tag` is the parent tag id for a variant.

## BFF (ui → api)

| ui route | Method | api route |
|----------|--------|-----------|
| `/api/notebooks/kitchens/[kitchenId]/captures/text` | POST | `/notebooks/kitchens/{kitchen_id}/captures/text` |
| `/api/notebooks/members/[userId]/[notebookId]/captures/text` | POST | `/notebooks/members/{user_id}/{notebook_id}/captures/text` |
| `/api/recipe-vocabulary` | GET | `/recipe-vocabulary` |

The two read BFF routes (`/api/notebooks/kitchens/[kitchenId]`, `/api/notebooks/members/[userId]/[notebookId]`) are delivered by spec 004.

- Forwards the `cookie` header, `Content-Type: application/json`, and the
  status, body and `Retry-After` as received.
- The capture routes abort the upstream call after
  `(GEMINI_TEXT_TIMEOUT_S || 10) + 2` seconds. On abort or network failure they
  answer 503 `{ "code": "ai_unavailable" }` (research R9). Other upstream
  failures answer 502 `bad_gateway`, as the existing BFF routes do. The ui
  treats 502 like `ai_unavailable` for messages.
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
| `notebook_not_found`, `kitchen_not_found` | The sheet shows the kitchen's not-found text (`kitchensMessages.detailNotFound`), and the text is kept. |
| any other | The `ai_unavailable` message. |
