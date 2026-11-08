# Implementation Plan: Capture a Recipe from a Photo

**Branch**: `worktree-41` | **Date**: 2026-11-07 | **Spec**: [spec.md](spec.md)

**Input**: `specs/041-capture-recipe-photo/spec.md` (clarified 2026-11-07), with `image-processing-prd.md` adopted as implementation detail (FR-022 to FR-028).

## Summary

The member picks one picture (JPEG, PNG or HEIC). The browser downscales and recompresses it (FR-024), then posts it to a new picture route. The api checks the bytes (FR-005), checks the notebook and archived-kitchen rules, and runs the image pipeline (FR-026, adapter `adapters/image/`): normalise to RGB, a true 3×3 Laplacian sharpness, tier selection, resize and WebP encode. The compressed WebP goes to the assistant as the image, in one picture-mode call (`GEMINI_IMAGE_TIMEOUT_S`). The result goes through the same merge and check path as link capture; a partial draft opens unmatched, flagged, with Save disabled. On Save, the compressed WebP is stored as the recipe's preview image (FR-022), and the source is `photo`. The preview pop-up (FR-027) shows it to members who can read the notebook. The sheet shows a Handwritten switch (FR-025) and a progress bar with phrases (FR-028). The disclaimers option (FR-013c) is a boolean on the account, served by `/auth/me` (approved).

## Technical Context

**Language/Version**: Python 3.12 (api, uv); TypeScript, Next.js 16, React 19, Tailwind 4 (ui)

**Primary Dependencies**: existing FastAPI, SQLAlchemy, Alembic, `google-genai`. **New, approved for this story (constitution 2.1.0)**: `Pillow` and `NumPy` (FR-026). `pillow-heif` is approved for spec 041 (constitution 2.1.1) for HEIC decoding.

**Storage**: PostgreSQL 16. Migration `0022_user_disclaimers` adds `users.disclaimers`. The compressed WebP is stored in the existing nullable `recipe.preview_image_base64` (no new column). `source.type='photo'` is already allowed.

**Testing**: pytest (domain pure; application with fakes; adapter tests for the pipeline with generated images; Compose integration), vitest (ui), browser walk at 360 px and 1280 px, English and Spanish, and a manual evaluation with the real assistant

**Target Platform**: Linux server, Docker Compose (four services unchanged)

**Project Type**: Web application (api + ui BFF)

**Performance Goals**: draft or message within 32 s (SC-002). Preprocessing within 150 ms per image on a standard worker, excluding the assistant (SC-008a).

**Constraints**: constitution 4 and 5 as amended (stored image designed for quality and size; visibility follows the recipe; the image is data, never instructions); nothing stored before Save; no image bytes in logs; English and Spanish strings.

**Scale/Scope**: a household of a few people; one assistant call per capture; one new route, one BFF route, one migration, one adapter package, one pop-up component.

## Constitution Check

*Checked against constitution 2.1.0.*

| Principle | Check | Result |
|---|---|---|
| 1. Simplicity and reuse | No new service or worker. The pipeline runs inside the request. Draft screen, save, toast, preview pop-up and settings panel are reused. The disclaimers field follows `theme` and `language` on `/auth/me`, approved by the owner. | Pass |
| 2. Tech stack | Pillow and NumPy are approved for spec 041 (2.1.0). `pillow-heif` is approved (constitution 2.1.1). Model and timeout come from settings. | Pass, with one open item (R1) |
| 3. Hexagonal | `domain/picture_tiers.py` (tier rules, threshold table, no I/O). `adapters/image/pipeline.py` (Pillow and NumPy). Membership and archived checks in `application/` before any work. | Pass |
| 4. Security and privacy | Bytes checked before decoding (FR-005). Decode runs under a pixel limit (Pillow `MAX_IMAGE_PIXELS`) to stop decompression bombs. The image is wrapped as data in the prompt. Logs keep media type, byte count, tier and sharpness only. | Pass |
| 5. No AI shortcuts | Draft never saved without Save. Stored image is the designed compressed copy (2.1.0), not the original. Visibility follows the notebook (FR-027). | Pass |
| 6. Testing | Domain tiers and thresholds tested without I/O; pipeline tested on generated images; evaluation by hand. | Pass |
| 7. Deployment | No proxy or server config beyond the `next.config.ts` body limit (FR-024). No new setting. | Pass |
| 8. Git discipline | Migration through Alembic. Constitution commit waits for owner go-ahead. | Pass |
| 9. Scope | S-041 is a Should, picked by the owner after the MVP. | Pass |

## Design overview

```text
UI  PictureCaptureSheet
     · Handwritten switch (top left, on by default)            FR-025
     · file check (type, size)                                 FR-005
     · browser downscale + recompress (≤2400 px, WebP/JPEG)    FR-024
     · submit → progress bar + random phrase                   FR-028
     POST /api/notebooks/{id}/captures/picture {image_base64, handwritten}
API CapturePictureRecipe (application/recipe_capture_picture.py)
     1. check_picture(bytes)                                   → PictureRefused
     2. notebook visible, kitchen not archived                 → 404 | 409 (before any work)
     3. adapters/image: decode → RGB → Laplacian → tier → resize → WebP   FR-026
        domain/picture_tiers.choose_tier(handwritten, sharpness) → Tier 1|2|3
     4. extract_picture(webp, names, image timeout)            → DraftPart | refusals
     5. merge_parts → check_draft | open_incomplete (partial)  FR-013, FR-013a
     6. CapturedPictureDraft{recipe, notebook, language, catalog, picture_webp, metadata}
UI  draft opens → toast (if disclaimers on)                    FR-013b
     Save → POST /recipes {source_kind:"photo", preview_image: webp}   FR-022
     Recipe card / detail → author avatar or own side panel → preview pop-up   FR-027
```

Handwritten on (FR-025): no sharpness measurement and Tier 3. Handwritten off: sharpness is measured and the tier is chosen by the calibrated thresholds (Tier 1, 2 or 3). The assistant gets the same WebP in both cases.

## Research decisions (summary; full text in research.md)

- **R1 HEIC decoding (approved 2026-11-07)**: `pillow-heif` is approved for spec 041, so the server decodes HEIC for measurement and storage. It needs native wheels; the Dockerfile build must be checked. Principle 2 names it as of constitution 2.1.1.
- **R2 Laplacian**: 3×3 kernel `[[0,1,0],[1,-4,1],[0,1,0]]` on the grayscale array, computed with NumPy slicing (no SciPy, no OpenCV). Sharpness = variance of the response divided by image area, so the score does not depend on size. The earlier PRD function is replaced: it summed neighbour differences, which is a gradient, not a Laplacian.
- **R3 Thresholds**: no fixed numbers in code. `domain/picture_tiers.py` holds a `CalibrationTable` loaded from a versioned file `api/domain/picture_calibration.json`, with the calibration date and the labelled set's id. Until the calibration task (T077) is done, the table is marked `provisional` and the release check refuses `provisional`. Initial values (PRD: 100 and 500) are placeholders only.
- **R4 Decompression bombs**: pixel limit 64 million, checked explicitly before any decode, with `Image.MAX_IMAGE_PIXELS` set above it; JPEG is decoded at reduced scale with `draft()`; larger images are refused as unsupported before resize.
- **R5 Resize and encode**: `thumbnail` with LANCZOS to the tier's maximum side; WebP `method=6` at quality 70/80/90 (PRD). EXIF orientation applied with `ImageOps.exif_transpose` before measuring, so sideways photos are upright (FR-010 becomes a server guarantee, not only a prompt rule).
- **R6 Image sent to the assistant**: the compressed WebP, not the original. This also removes HEIC from the assistant path once R1 is settled and keeps the request small.
- **R7 Browser downscale**: canvas, longest side 2400 px, WebP with a JPEG fallback, quality stepped until under 1.5 MB. Reuses the approach of `ui/lib/imageEncode.ts`.
- **R8 Storage**: the WebP goes in `recipe.preview_image_base64` as a data URI, the same field as the link preview. The existing size check (`validate_preview_image`, 300 KB) is replaced by a per-tier cap: Tier 3 500 KB, Tiers 1 and 2 300 KB (owner decision, 2026-11-07). When the encoded picture is over its cap, the pipeline steps down in order: quality by 5 at a time, then the longest side by 10% at a time, and stops at the tier's floor (quality 60, side 1200 px for Tier 3; quality 60, side 1000 px for Tiers 1 and 2). A picture still over cap at the floor is refused as unsupported with `picture_too_large`. The steps taken are kept in the metadata. The PRD's 50 to 150 KB is the typical target, not the cap. Visibility follows the notebook; no separate media store.
- **R9 Progress**: the api does not stream progress. The sheet shows steps as the request advances: upload (browser, measured), prepare (browser encode), identify (before the call), compress (api pipeline), read (assistant), draft (merge). Steps the browser cannot time are shown as a fixed sequence over the measured total. Phrases come from the i18n wording files; each phrase list is an array, chosen at random per capture.
- **R10 Preview pop-up**: a dialog opened from the author's avatar on the recipe card and detail and from the side panel's own entry. The image is served only inside the recipe response for members who can read the notebook (the recipe detail already checks this); no new public route.

## Project Structure

### Documentation (this feature)

```text
specs/041-capture-recipe-photo/
├── spec.md
├── plan.md              # this file
├── research.md          # R1–R10 (summary above; detail in the file)
├── data-model.md        # updated: stored WebP, metadata, calibration table
├── quickstart.md
├── contracts/
│   ├── capture-picture-api.md   # updated: handwritten flag, metadata
│   ├── ports.md                 # updated: pipeline port
│   └── disclaimers-preference.md
├── image-processing-prd.md      # source, adopted
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks, regenerated after this plan
```

### Source Code

```text
api/
├── domain/
│   ├── picture_tiers.py             # new: choose_tier, CalibrationTable, Tier enum (pure)
│   ├── picture_calibration.json     # new: thresholds, labelled-set id, date, status
│   ├── recipe_picture.py            # new: check_picture (type by content, size, structure)
│   └── recipe_draft.py              # + open_incomplete (shared with link capture)
├── application/
│   ├── ports.py                     # + Picture, PicturePipeline port, PictureResult
│   ├── recipe_extraction.py         # + ExtractionMode.PICTURE, extract_picture
│   ├── recipe_capture_picture.py    # new: CapturePictureRecipe
│   ├── recipe_capture_url.py        # _as_is → domain open_incomplete
│   ├── recipe_save.py               # + source_kind; photo keeps preview
│   └── preferences.py               # + disclaimers
├── adapters/
│   ├── image/__init__.py            # new package (Pillow, NumPy)
│   ├── image/pipeline.py            # new: PillowPicturePipeline (decode, RGB, exif, Laplacian, resize, WebP)
│   ├── image/laplacian.py           # new: 3×3 Laplacian variance with NumPy
│   ├── llm/gemini_extractor.py      # + PICTURE schema, image part
│   ├── llm/prompt.py                # + picture prompt builders
│   ├── llm/prompts/recipe_extraction_picture_system.md   # new
│   ├── llm/prompts/recipe_extraction_picture_user.md     # new
│   ├── llm/fake_extractor.py        # + extract_picture
│   └── persistence/
│       ├── models.py                # + UserModel.disclaimers
│       ├── repositories.py          # preferences carry disclaimers
│       ├── recipes.py               # add(): type='photo' source; preview kept
│       └── migrations/versions/0022_user_disclaimers.py
├── api/
│   ├── routes/recipe_capture.py     # + POST /notebooks/{id}/captures/picture
│   ├── routes/recipes.py            # save: source_kind
│   ├── routes/auth.py               # GET/PATCH /auth/me carry disclaimers (approved)
│   ├── schemas/recipe_capture.py    # + CapturePictureBody (image_base64, handwritten)
│   ├── schemas/recipes.py           # + source_kind
│   ├── schemas/auth.py              # + disclaimers
│   ├── deps.py                      # + get_capture_recipe_picture, get_picture_pipeline
│   └── settings.py                  # none new (GEMINI_IMAGE_TIMEOUT_S exists)
├── scripts/eval_picture_capture.py  # new: manual evaluation
├── scripts/calibrate_picture_tiers.py  # new: computes sharpness on the labelled set, writes calibration
└── tests/
    ├── fixtures/ai_eval/pictures/   # invented pages, expected drafts, labels for calibration
    ├── test_picture_tiers_domain.py
    ├── test_recipe_picture_domain.py
    ├── test_picture_pipeline_adapter.py
    ├── test_recipe_capture_picture_application.py
    ├── test_recipe_capture_picture_integration.py
    ├── test_user_disclaimers_migration.py
    └── (extended) gemini adapter, prompts, save, preferences, url application

ui/
├── next.config.ts                   # + experimental.proxyClientMaxBodySize (fallback, FR-024)
├── app/api/notebooks/[notebookId]/captures/picture/route.ts   # new BFF (+ test)
├── components/AddRecipeCallToAction/
│   ├── AddRecipeOptionsDialog.tsx   # Picture enabled
│   ├── PictureCaptureSheet.tsx      # new: drop area, Handwritten switch, progress, phrases
│   └── AddRecipeCallToAction.tsx    # route Picture to the sheet (quick add inherits via opener)
├── components/Picture/
│   ├── PicturePreview.tsx           # new: pop-up preview (FR-027)
│   └── PictureProgress.tsx          # new: thin bar and phrase (FR-028)
├── components/RecipeDetail/…        # author avatar opens PicturePreview
├── components/SidePanel/…           # own entry opens PicturePreview
├── components/RecipeDraft/RecipeDraftPage.tsx   # disclaimer toast
├── components/Toast/ToastProvider.tsx           # + durationMs
├── components/SidePanel/SidePanelSettings.tsx   # + Show disclaimers switch
├── components/PreferencesProvider.tsx           # + disclaimers
├── lib/capture/
│   ├── pictureRules.ts              # new: same rules as domain/recipe_picture.py
│   ├── pictureDownscale.ts          # new: canvas downscale and WebP/JPEG encode (FR-024)
│   ├── captureClient.ts             # + submitPictureCapture
│   ├── captureStore.ts              # + picture source, file, progress
│   └── saveClient.ts                # + source_kind photo, preview
└── lib/i18n/…                       # phrases as arrays, en and es, parity test
```

**Structure Decision**: the api hexagon, with the image pipeline as a new adapter package `adapters/image/`, as Gemini and web fetching are. The tier rules are pure domain. No new service.

## Complexity Tracking

| Item | Why needed | Simpler alternative rejected because |
|---|---|---|
| Pillow and NumPy in the api | Decode, resize, WebP encode and Laplacian on the server (FR-026, owner decision) | Client-only processing cannot be trusted for the stored copy or the calibration |
| `pillow-heif` (pending approval) | HEIC decode for measurement and storage | Without it HEIC is refused server-side; see R1 |

## Open items that block implementation

1. **R3, calibration**: the labelled set and the thresholds are needed before release (T077). The provisional table allows development, not release.
2. **R8, size cap (decided 2026-11-07)**: per-tier caps (Tier 3 500 KB; Tiers 1 and 2 300 KB) with a stepped quality and size fallback to a floor (R8). Spec FR-026 must record the caps and the floors on its next edit.