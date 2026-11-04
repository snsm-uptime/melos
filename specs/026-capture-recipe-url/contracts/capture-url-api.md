# Contract: link capture, save and detail (spec 026)

All routes need the session cookie. The browser calls the same paths under `/api/` on the ui (BFF), which forwards them unchanged.

## POST `/notebooks/{notebook_id}/captures/url`

Request:

```json
{ "url": "https://example.test/recipes/lentil-soup" }
```

- `url`: string, at most 4,096 characters in the body (guard); the link rules (research R5) then allow 2,048.

Order of checks (each refusal stops before the next step):
1. Link rules → `link_empty`, `link_too_long`, `link_invalid` (no fetch).
2. Notebook visible to the caller → `notebook_not_found`; kitchen archived → `kitchen_archived` (no fetch).
3. Fetch the page → `page_fetch_failed`.
4. Read the page; schema.org path or Markdown batches; extractor → draft or refusal.

### 200: draft

Same body as `POST /notebooks/{id}/captures/text` (spec 016 `contracts/capture-api.md`), plus a `page` object:

```json
{
  "outcome": "draft",
  "notebook": { "id": "…", "kind": "kitchen", "name": "…", "kitchen_id": "…" },
  "language": "es",
  "catalog": ["onion", "salt"],
  "draft": { "title": "…", "base_servings": 4, "servings_estimated": false,
             "changes": [], "ingredient_lines": [ … ], "unknown_units": [], "steps": [ … ] },
  "page": {
    "source_url": "https://example.test/recipes/lentil-soup",
    "preview_image": "data:image/jpeg;base64,…",
    "cut": false
  }
}
```

- `page.source_url`: the final address after redirects.
- `page.preview_image`: data URI or `null`. Never the site's image URL.
- `page.cut`: `true` when Markdown beyond the batch cap was not read (the draft shows the long-page note).

### Refusals

| Status | `code` | When | Extra fields |
|---|---|---|---|
| 422 | `link_empty` | empty or spaces only | |
| 422 | `link_too_long` | over 2,048 characters | `max` |
| 422 | `link_invalid` | not a link, other scheme | |
| 422 | `page_fetch_failed` | any fetch failure: blocked address, credentials or port, DNS, timeout, status, redirects, not HTML, too large | none (the kind is never sent) |
| 422 | `page_no_recipe` | the page opened but holds no recipe (FR-021a) | |
| 422 | `one_recipe_at_a_time` | two or more Recipe items, or the reader or merge finds two recipes | |
| 422 | `draft_incomplete` | merged or single draft misses a title or steps | `missing`, `line_problems` (spec 017) |
| 422 | `ingredient_line_problem` | line problems only | `line_problems` |
| 422 | `ai_invalid_output` | unreadable answer | |
| 429 | `ai_limit_reached` | usage limit | `Retry-After` header when known |
| 503 | `ai_unavailable` | no answer in time, network, 5xx | |
| 503 | `ai_misconfigured` | no key or model | |
| 404 | `notebook_not_found` | not visible to the caller | |
| 409 | `kitchen_archived` | archived kitchen | |

`detail` is fixed app text or empty; it never carries site text, addresses or service errors (FR-024).

Credentials and ports: a link with a user name, password or another port is refused by the link rules **before** any request with `page_fetch_failed` (not `link_invalid`), as the spec's edge case says ("refused with the page message").

## BFF `POST /api/notebooks/{notebook_id}/captures/url` (ui)

Same as the text route (`ui/app/api/notebooks/[notebookId]/captures/text/route.ts`), with the deadline `(10 + GEMINI_TEXT_TIMEOUT_S + 2) s`. On timeout or network failure it answers 503 `ai_unavailable`.

## POST `/recipes` (spec 020, changed)

Body gains two optional fields:

```json
{ "source_url": "https://example.test/recipes/lentil-soup",
  "preview_image": "data:image/jpeg;base64,…" }
```

- `source_url`: when present, `source_text` must be empty; the URL must pass the link rules (scheme http or https, ≤ 2,048). Stored as `source.type='url'`, `source.url`, no `raw_text`. A bad value → 422 `invalid_draft`.
- `preview_image`: optional; only accepted together with `source_url`; must pass `validate_preview_image` (JPEG, PNG or WebP data URI, ≤ 300 KB decoded) → otherwise 422 `invalid_preview_image`.
- Without `source_url`, behaviour is unchanged (text source).

## GET `/recipes/{id}` (spec 027, changed)

Response gains `preview_image: string | null`. `source: {type, url} | null` already exists (`api/api/routes/recipes.py`), and `RecipeDetailView.tsx` already shows the link when `source.url` is set (spec 027 FR-003); no change there beyond checking it opens in a new tab with `rel="noopener noreferrer"`. The detail adds the image at the top when present.
