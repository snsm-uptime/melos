# Data Model: Capture a Recipe from a Photo

The stored changes are one new column on `users`, a `photo` source on Save, and the compressed picture kept in the recipe's preview field. Capturing, editing or discarding a draft stores nothing.

## Stored

### `users.disclaimers` (new column)

| Field | Type | Rule |
|---|---|---|
| `disclaimers` | boolean, `NOT NULL`, default `true` | The member's "Show disclaimers" option (FR-013c). Existing rows read `true` through the server default. Changed by `PATCH /auth/me` (approved 2026-11-07). |

Migration `0022_user_disclaimers` (down revision `0021_catalog_other_names`): `add_column("users", Column("disclaimers", Boolean, nullable=False, server_default=true()))`; downgrade drops it.

### `source` (existing, used with `type = 'photo'`)

| Field | Photo capture value |
|---|---|
| `type` | `'photo'` (already allowed by `ck_source_type`) |
| `user_id` | the recipe's author |
| `url` | `NULL` |
| `raw_text` | `NULL` (no text read from the picture is stored) |

Deleted with the recipe (spec 027). The recipe detail shows no source link for a photo source.

### `recipe.preview_image_base64` (existing field, new content)

| Field | Picture capture value |
|---|---|
| `preview_image_base64` | `data:image/webp;base64,…` of the compressed picture from the pipeline (FR-022, FR-026). Stored on Save only. |

Rules for a picture preview:

| Rule | Value | Where |
|---|---|---|
| Media type | `image/webp` (picture pipeline output) | `validate_picture_preview` |
| Decoded size cap | Tier 3 500 KB; Tiers 1 and 2 300 KB | `domain/picture_tiers.py` (passed in) |
| Link and draft-photo previews | 300 KB, unchanged | `domain/recipe_preview.py` (existing rule) |

The cap is passed in explicitly, so the link rule and the picture rule stay separate. The field is deleted with the recipe (spec 027).

### `recipe` (other columns)

No other change.

## Transient (never stored)

### Picture (as received)

`data: bytes` (1 to 10,000,000), `media_type` from `check_picture`: `image/jpeg | image/png | image/heic | image/heif`. Lives for one request.

### Picture (as processed)

`ProcessedPicture`: `webp: bytes`, `media_type: "image/webp"`, `tier: Tier`, `sharpness: float | None` (`None` when Handwritten is on, FR-025), `original_dimensions: (int, int)`, `final_dimensions: (int, int)`, `size_kb: float`, `steps_taken: tuple[str, ...]` (for example `"quality 70→65"`, `"side 1600→1440"`). Sent to the assistant as `image/webp`. Only the tier, sharpness, dimensions, size and steps are logged.

### Tier

`Tier` enum: `TIER_1` (aggressive, max side 1600, quality 70), `TIER_2` (balanced, 2000, 80), `TIER_3` (high preservation, 2400, 90). The table and the floors are in `domain/picture_tiers.py`.

### Calibration table

`CalibrationTable` loaded from `api/domain/picture_calibration.json`:

| Field | Type | Rule |
|---|---|---|
| `thresholds.low` | float | sharpness below this → Tier 3 (when measured) |
| `thresholds.high` | float | sharpness at or above this → Tier 1; between → Tier 2 |
| `labelled_set` | string | identifier of the labelled set used |
| `calibrated_on` | date | when the thresholds were fitted |
| `status` | `"provisional" \| "calibrated"` | release refused while `provisional` |

### Encoding ladder

`plan_encoding(tier) -> tuple[Step, ...]`: the ordered `(quality, max_side)` pairs the adapter tries until the WebP is under the tier's cap, ending at the floor. Pure; produced in `domain/picture_tiers.py`.

### Picture capture outcome

`CapturedPictureDraft`: `recipe: DraftRecipe`, `notebook: NotebookView`, `language: str`, `catalog: tuple[str, ...]`, `picture: ProcessedPicture`. Or one of: `NotARecipe(reason | MULTIPLE_RECIPES)`, `InvalidOutput` (nothing readable), `Unavailable`, `LimitReached`, `AIProviderError`. Or `PictureRefused` raised before any call (`unsupported`, `too_large`, `empty`).

### Draft (from a picture)

The spec 016 `DraftRecipe`, built by `merge_parts([part])` and `check_draft`, or opened by `open_incomplete` when a rule breaks (blank title kept blank, no steps kept empty, lines kept as read, servings 4 and flagged estimated when the picture gave none). Nothing absent from the picture is invented, except that servings estimate.

## Client-only state

| Where | Change |
|---|---|
| `CaptureSource` | adds `{ kind: "picture"; file: File \| null }` |
| `DraftView` | adds `fromPicture?: boolean` and `picturePreview?: string` (the processed WebP data URI, shown on the draft and saved as `preview_image`) |
| `MePreferences` | adds `disclaimers: boolean` |
| `Toast` | adds optional `durationMs` |
| Progress | `{ step: "upload" \| "prepare" \| "identify" \| "compress" \| "read" \| "draft"; phrase: string }` |

## Validation rules

| Rule | Where it holds |
|---|---|
| Type by content, JPEG/PNG/HEIC only (FR-005) | `domain/recipe_picture.py`, `pictureRules.ts` |
| 1 to 10,000,000 bytes (FR-005, FR-017) | the same two |
| PNG and HEIC structure; JPEG signature only (plan I3) | the same two |
| Decompression bomb: pixels ≤ 64,000,000, checked before decoding (plan R4) | `adapters/image/pipeline.py` |
| Size under the tier cap after the ladder (FR-026) | `adapters/image/pipeline.py` using `plan_encoding` |
| Calibration `status = calibrated` at release | `scripts/calibrate_picture_tiers.py` and the release check |
| Draft rules before Save (FR-013a) | `check_edited_draft` at Save; unchanged |
| `source_kind = "photo"` needs empty `source_text` and no `source_url` | `SaveRecipeDraft` |
| Picture preview ≤ tier cap, `image/webp` | `SaveRecipeDraft` via the picture rule |
| `disclaimers` is a boolean | `PatchMeBody` (`bool \| None`) |

## State transitions

```text
sheet (no picture) → picture chosen → submitting (progress bar) → draft (toast if disclaimers on)
                          ↑   ↑                │                     │
                          │   └── refusal ─────┘                     ├─ Save → recipe + source(photo) + preview (WebP)
                          └──────── Back ────────────────────────────┤
                       empty sheet ←──── Discard ────────────────────┘

recipe card / detail → author avatar or own side panel → preview pop-up (read-only)
```

A refused file never changes the chosen picture, and a failed capture keeps it.
