# Data Model: Capture a Recipe from a URL (spec 026)

## Stored data

### `recipe` (changed)

| Column | Type | Rule |
|---|---|---|
| `preview_image_base64` | `text`, nullable | New (migration `0015_recipe_preview_image`). A `data:image/jpeg|png|webp;base64,` URI, at most 300 KB decoded (`domain.recipe_preview`). Null for recipes from text and for link captures with no photo or whose photo the member removed. Named in PRD §1.6. |

- Written only by Save (spec 020) from the draft. Edit (spec 027) leaves it unchanged. Delete removes it with the row. Snapshots (`copy_all`, spec 035) copy it.
- Migration: `ALTER TABLE recipe ADD COLUMN preview_image_base64 text NULL`; downgrade drops it. Existing rows stay null.

### `source` (no schema change)

The table already allows `type='url'` and has `url` (migration 0005). A link capture saves `type='url'`, `url` = the final page address after redirects, `raw_text` = null (FR-019: no page HTML or text is stored). Text capture is unchanged (`type='text'`, `raw_text` = pasted text).

## Domain values (not stored)

### `PageLink` (`domain/page_link.py`)
- `url`: normalized link (scheme added, scheme and host lower-case, host IDNA-encoded).
- `host`, `port` (80 or 443), `scheme`.
- Refusals (`PageLinkRefused.kind`): `empty`, `too_long` (> 2,048), `invalid` (no host, whitespace, other scheme), `credentials`, `port`.

### `PageRecipe` (`domain/recipe_page.py`)
From one schema.org Recipe item.
- `title: str | None`, `yield_text: str | None`, `ingredients: tuple[str, ...]`, `steps: tuple[str, ...]` (flattened, in page order, plain text), `image_urls: tuple[str, ...]`.

### `PageContent` (port value, `application/ports.py`)
What `PageReader` returns from one page.
- `recipes: tuple[PageRecipe, ...]`, `main_image_url: str | None`, `markdown: str` (may be empty).

### `PageBatches` (`domain/recipe_page.py`)
- `batches: tuple[str, ...]` (1 to `RECIPE_PAGE_MAX_BATCHES`), `cut: bool`.

### Extraction results (`application/recipe_extraction.py`, extended)
- `ExtractionMode`: `WHOLE` (default, text capture and single-batch pages) or `PAGE_PART`.
- `DraftPart(title: str | None, base_servings: int | None, ingredient_lines: tuple[IngredientLine, ...], steps: tuple[str, ...])`: a part, returned only in `PAGE_PART` mode, not checked by `check_draft`.
- `NoRecipeContent()`: a part with nothing of a recipe in it.
- Existing results unchanged: `Draft`, `NotARecipe`, `DraftIncomplete`, `Unavailable`, `LimitReached`, `InvalidOutput`, `AIProviderError`.

### Merge (`domain.recipe_page.merge_parts`)
Input: the parts in batch order. Output: a raw `DraftRecipe` (then `check_draft`), or `MultipleRecipes`, or `NoRecipeContent`. Rules in research R8.

### `CapturedPageDraft` (`application/recipe_capture_url.py`)
Extends what text capture returns:
- `recipe: DraftRecipe` (checked), `notebook: NotebookView`, `language`, `catalog`.
- `source_url: str` (final address), `preview_image: str | None` (data URI as fetched, before the browser shrinks it), `page_cut: bool`.

## Fetch results (`application/ports.py`)

- `FetchedPage(final_url: str, html: str, byte_count: int)`.
- `PageFetchFailed(kind)` with `kind` in `blocked`, `dns`, `timeout`, `connect`, `redirect`, `status`, `not_html`, `too_large`. All map to one member message (R10); the kind is for logs and tests.
- `FetchedImage(media_type: "image/jpeg" | "image/png" | "image/webp", data: bytes)` or `None`.

## Client-only state (ui)

`captureStore` gains, for a link capture:
- `source: { kind: "text" } | { kind: "url"; link: string }`: what the sheet shows again on Back or after an error (the link, unchanged).
- On the draft: `sourceUrl`, `previewImage` (data URI or null; the remove control sets it to null), `pageCut`.
- Save sends `source_url` and `preview_image` (shrunk by `encodeRecipePreview`) instead of `source_text`.

## Settings (`api/api/settings.py`, `.env.example`)

| Name | Default | Rule |
|---|---|---|
| `RECIPE_PAGE_BATCH_CHARS` | 10000 | 1,000 to 10,000 (the extraction limit) |
| `RECIPE_PAGE_MAX_BATCHES` | 4 | 1 to 8 |

Fixed in code (security limits from PRD §1.7 and the spec, not tunable): page 10 s and 2 MB, photo 5 s and 2 MB, 3 redirects, ports 80 and 443, link 2,048 characters, stored preview 300 KB.
