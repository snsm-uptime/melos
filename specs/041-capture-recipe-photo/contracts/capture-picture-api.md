# Contract: `POST /notebooks/{notebook_id}/captures/picture`

Same-origin browser route: `POST /api/notebooks/{notebookId}/captures/picture` (BFF), forwarding to the api route above. Auth, notebook access and the archived-kitchen rule are as for `captures/text` and `captures/url`.

## Request

```json
{
  "image_base64": "<standard base64 of one picture: JPEG, PNG or HEIC, browser-downscaled when possible>",
  "handwritten": true
}
```

- `image_base64`: required string. No data-URI prefix. Up to 13,333,336 characters (10,000,000 bytes encoded). The browser sends a downscaled, recompressed copy under 1.5 MB when it can (FR-024).
- `handwritten`: optional boolean, default `true` (FR-025). `true` → Tier 3, no sharpness measurement. `false` → sharpness measured; Tier 1, 2 or 3 by the calibrated thresholds (FR-026).
- The api decodes the bytes, and `check_picture` decides the type from them. Nothing in the body names the type.
- One attempt. The BFF deadline is `GEMINI_IMAGE_TIMEOUT_S + 2` seconds (32 by default). A timeout or network failure is answered by the BFF as `ai_unavailable` (503). A truncated or unreadable body is answered as `picture_too_large` (422), not `invalid_body`.

## Order of checks (nothing reaches the pipeline or the assistant before step 3 passes)

1. Body shape and length (422 `picture_empty` for an empty string; `picture_too_large` when over the length cap).
2. `check_picture`: type, decoded size, signature and container (422 `picture_unsupported` or `picture_too_large`).
3. Notebook visible to the caller (404 `notebook_not_found`); kitchen not archived (409 `kitchen_archived`).
4. Image pipeline (FR-026): decode, EXIF orientation, RGB, Laplacian sharpness (measured only when `handwritten` is false), tier, resize, WebP encode, step-down ladder to the tier cap. Pixel count over 64,000,000 or an unreadable image → 422 `picture_unsupported`. A picture still over cap at the floor → 422 `picture_too_large`.
5. The assistant call (picture mode), with the processed WebP.

## Success: `200`

The same body as a text or link draft (`outcome: "draft"`, `notebook`, `language`, `catalog`, `draft`), with a `picture` object in place of `page`. The image itself is returned as a data URI for the draft preview; it is not stored until Save.

The draft may break draft rules (a blank `title`, empty `steps`, a line with no `quantity` and `unit` while not `vague`). The form flags them and Save stays disabled (FR-013a). Such a draft is never a refusal for those reasons. Partial drafts stay unmatched (FR-013).

```json
{
  "outcome": "draft",
  "notebook": { "id": "…", "kind": "personal", "name": "…", "kitchen_id": null },
  "language": "es",
  "catalog": ["cebolla", "…"],
  "draft": {
    "title": "",
    "base_servings": 4,
    "servings_estimated": true,
    "language": "es",
    "changes": [],
    "ingredient_lines": [ { "name": "mantequilla", "vague": false, "quantity": null, "unit": null, "size": null,
                            "preparation": null, "vague_text": null, "note": null,
                            "text_name": "mantequilla", "match": { "kind": "new", "entry": null } } ],
    "unknown_units": [],
    "steps": []
  },
  "picture": {
    "preview_image": "data:image/webp;base64,…",
    "tier": "tier_3",
    "sharpness": null,
    "original_dimensions": [3024, 4032],
    "final_dimensions": [1200, 1600],
    "size_kb": 212.4,
    "steps_taken": ["quality 90→85"]
  }
}
```

`sharpness` is `null` when `handwritten` is true. The `picture` object carries only what the sheet and the metadata need; it contains no file name and no original bytes.

## Errors

| Status | `code` | When | UI message (en) |
|---|---|---|---|
| 422 | `picture_empty` | empty `image_base64` | "Choose a picture first." |
| 422 | `picture_unsupported` | not JPEG, PNG or HEIC by content, damaged container, or over 64 MP | "That file isn't a supported picture. Use a JPEG, PNG or HEIC image." |
| 422 | `picture_too_large` | over 10,000,000 bytes, or still over the tier cap at its floor | "That picture is too large. Use one up to 10 MB." |
| 404 | `notebook_not_found` | no such notebook, or the caller may not see it | as spec 016 |
| 409 | `kitchen_archived` | the notebook's kitchen is archived | "This kitchen is archived, so recipes can't be added." |
| 422 | `not_a_recipe` | no recipe in the picture; `detail` is `not_food` or `story_or_article` | "That doesn't look like a recipe." + the reason |
| 422 | `one_recipe_at_a_time` | two or more complete recipes in the picture | "Upload only one recipe at a time" |
| 422 | `ai_invalid_output` | nothing readable, or the answer failed the schema | "We couldn't read that recipe. Try a clearer photo." |
| 503 | `ai_unavailable` | no answer in time, network, 5xx | "The assistant isn't responding. Your picture is kept — try again." |
| 429 | `ai_limit_reached` (+ `Retry-After`) | usage limit | "We've hit the assistant's limit. Try again in a minute." |
| 503 | `ai_misconfigured` | assistant not set up | "Assistant misconfigured. Your picture is kept" |

Every error body is `{ "detail": <fixed text or empty>, "code": <code> }`. No body, log line or message holds the image, base64, a file name, raw service text, keys or traces (FR-021). Spanish wording lives in `ui/lib/i18n/capture.ts` (FR-022).

## Save (existing `POST /recipes`), change

| Field | Meaning |
|---|---|
| `source_kind` (new, optional) | `null` or absent: as today (`source_url` set → `url`, else `text`). `"photo"`: stores `source(type='photo', url=NULL, raw_text=NULL)`; `source_text` must be `""` and `source_url` absent. `"text"` and `"url"` must agree with the other fields. Anything else → 422 `invalid_draft`. |
| `preview_image` (existing) | For a picture draft: the processed WebP data URI from the draft. Checked against the tier cap and `image/webp` (data-model). Removing it stores no preview. |

The save response and recipe detail are unchanged in shape. A photo source has no `source.url`, so the detail shows no source link. The recipe detail returns `preview_image` for the pop-up (FR-027), to members who can read the notebook.
