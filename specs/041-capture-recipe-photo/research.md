# Research: Capture a Recipe from a Photo

No `NEEDS CLARIFICATION` remains in the spec. The decisions below are checked against the code as of 2026-11-07. Sections **Image pipeline** supersede the earlier R2, R4, R6 and R7 where they conflict; the plan's own R1 to R10 summary maps onto these.

## Upload and checks (R1, R2)

**Decision**: the browser posts `{ "image_base64": "<base64>", "handwritten": true }` through the BFF to the api. The browser has already downscaled and recompressed the picture (FR-024), so the typical body is well under 2 MB. The api still accepts an original of up to 10 MB, because the browser downscale can fail on some devices and FR-005 applies to whatever arrives.

**Rationale**:
- No multipart library. `python-multipart` is not in `api/pyproject.toml`; a JSON body follows the profile-photo and preview patterns and the text and link routes.
- The length cap is checked in `check_picture` before decoding, so the refusal carries `picture_too_large`, not FastAPI's generic 422.
- The type comes from the file's bytes, never from its name or announced type (FR-005).

**Byte-level checks stay in the domain** (`domain/recipe_picture.py`): JPEG `FF D8 FF`; PNG signature with `IHDR` first and `IEND` present; HEIC/HEIF `ftyp` with an accepted brand; `avif` refused; size 1 to 10,000,000 bytes.

**JPEG end marker (revised, plan issue I3)**: only the JPEG signature is checked. A missing end marker is not a refusal, because some phone photos carry trailing data (for example a motion-photo video) and a truncated image fails later as "unreadable". PNG and HEIC structure checks stay, because they are reliable.

## Image pipeline (plan R1 to R10; supersedes earlier R2, R4, R6, R7)

**Decoding (R1, approved)**: Pillow decodes JPEG and PNG; `pillow-heif` registers the HEIC and HEIF openers (approved 2026-11-07, constitution 2.1.1). Native wheels must install in the api Dockerfile; the build is checked in T001-equivalent setup.

**Decompression bombs (R4)**: The pixel limit is 64,000,000, checked explicitly before decoding; `Image.MAX_IMAGE_PIXELS` is set above it so Pillow's own bomb error never fires first. JPEG is decoded at reduced scale with `draft()`. A larger image is refused as `picture_unsupported` before any resize.

**Orientation (R5)**: `ImageOps.exif_transpose` runs before measuring and encoding. Orientation is therefore a server guarantee; the earlier model-side orientation check (old R4) is no longer needed, although the prompt still says the image may be sideways as a second safeguard.

**Sharpness (R2 in the plan)**: a true 3×3 Laplacian on the grayscale array, kernel `[[0,1,0],[1,-4,1],[0,1,0]]`, computed with NumPy slicing (no SciPy, no OpenCV). Score = variance of the response divided by the pixel count, so the score does not depend on image size. The earlier gradient formula in the PRD is replaced: it measured gradient magnitude, not curvature.

**Thresholds (R3)**: no numbers in code. `api/domain/picture_calibration.json` holds the thresholds per tier, the labelled-set identifier, the calibration date and `status` (`provisional` or `calibrated`). The release check refuses `provisional`. The initial values (100 and 500 from the PRD) are placeholders. `scripts/calibrate_picture_tiers.py` computes the sharpness distribution on the labelled set and writes the table.

**Tier rules (pure domain, `domain/picture_tiers.py`)**:
- Handwritten on → Tier 3, no measurement (FR-025).
- Handwritten off → sharpness is measured: low → Tier 3, middle → Tier 2, high → Tier 1.

**Encoding and the size cap (R5, R8 of the plan; decided 2026-11-07)**: resize with LANCZOS to the tier's maximum side (Tier 1 1600 px, Tier 2 2000 px, Tier 3 2400 px), encode WebP with `method=6` at the tier's quality (70, 80, 90). Caps: Tier 3 500 KB; Tiers 1 and 2 300 KB. When over cap, the **step-down ladder** runs: quality down by 5, then longest side down by 10%, until the floor (Tier 3: quality 60, side 1200 px; Tiers 1 and 2: quality 60, side 1000 px). The ladder is produced by pure domain code (`plan_encoding(tier)`), and the adapter walks it. A picture still over cap at the floor is refused as `picture_too_large`. The steps taken go into the metadata.

**What the assistant receives (plan R6)**: the compressed WebP, with media type `image/webp`, not the original. This keeps the request small and removes HEIC from the assistant path.

**Storage (plan R8)**: the WebP is stored as a data URI in `recipe.preview_image_base64`, the existing field. Link previews keep their 300 KB rule; the picture cap is passed in explicitly so the two rules stay separate.

**Browser downscale (plan R7, FR-024)**: canvas, longest side 2400 px, WebP where the browser encodes it, JPEG otherwise; quality stepped until the upload is under 1.5 MB. Reuses the approach of `ui/lib/imageEncode.ts`. The sheet shows the chosen file's preview with an object URL; a file the browser cannot display (HEIC outside Safari) shows a placeholder with the file name and size.

**Progress (plan R9)**: the api does not stream progress. The sheet advances the bar through the fixed steps (upload, prepare, identify, compress, read, draft) as the request advances, using the measured upload time for the first step. Phrases are arrays in the wording files, chosen at random per capture.

**Preview (plan R10, FR-027)**: a pop-up opened from the author's avatar on the recipe card and detail, and from the side panel's own entry. The image is served inside the recipe response, which already checks notebook access, so there is no new public route.

## Partial draft: reuse the link-capture path (R5)

**Decision**: `CapturePictureRecipe` builds the draft with `merge_parts([part])` and `check_draft`. On `DraftProblems` it opens the draft with `open_incomplete` (moved from `application/recipe_capture_url._as_is`, now keeping `language`). Partial drafts stay unmatched (FR-013, decided 2026-11-07), as link capture does.

**Language**: found offline from the draft's own text (spec 043 FR-005a).

**Known limit**: unmatched lines show as "new ingredient". Matching partial drafts is a later improvement for both capture paths.

## Disclaimers option (R8)

A boolean `users.disclaimers`, `NOT NULL DEFAULT true`, migration `0022_user_disclaimers`. `GET /auth/me` returns it; `PATCH /auth/me` accepts `disclaimers: bool | None` (approved 2026-11-07). The preferences path follows `theme`. The UI reads `me.disclaimers`; it is not cached in `localStorage`, and the toast waits while preferences load.

## Save and the photo source (R6, revised)

Save stores a `source` row with `type='photo'`, `url=NULL`, `raw_text=NULL`, and keeps the compressed WebP as `preview_image_base64`. The save body gains `source_kind: "text" | "url" | "photo" | null`; `"photo"` requires empty `source_text` and no `source_url`. The original upload is never stored or logged. Replacing or removing the preview uses the draft's existing photo controls (spec 026, S-067).

## The 10-second toast (R9)

`Toast` gains optional `durationMs` (default `TOAST_MS`, 4 s, so no existing toast changes). The draft page shows `picture-disclaimer` for 10 s once per draft, when `fromPicture` is set and `me.disclaimers` is true. Tapping closes it, as for any non-persistent toast. The draft page must render inside the `AppShell` that mounts `ToastViewport`; T041 checks this.

## Messages and codes (R10)

New codes: `picture_unsupported`, `picture_too_large`, `picture_empty` (all 422). Reused: `not_a_recipe`, `one_recipe_at_a_time`, `ai_invalid_output`, `ai_unavailable`, `ai_limit_reached`, `ai_misconfigured`, `notebook_not_found`, `kitchen_archived`. `messageForCode` takes the source kind (`text | url | picture`); the English and Spanish strings sit side by side under the parity test.

## BFF deadline and body (R11)

The picture route deadline is `(GEMINI_IMAGE_TIMEOUT_S + 2)` seconds (32 s by default, SC-002). `next.config.ts` raises `experimental.proxyClientMaxBodySize` to 14 MB as a fallback (FR-024), because Next.js silently truncates bodies over its 10 MB default. The BFF answers an unreadable or truncated body as `picture_too_large`, not `invalid_body`.

## Concurrency (R12)

No in-flight sharing for pictures. Each submission is one assistant call; the submit control is disabled while submitting (FR-006).

## Evaluation and calibration (R13)

- `api/tests/fixtures/ai_eval/pictures/`: invented cookbook pages, English and Spanish, with accents and fractions, two-column, angled, sideways, upside-down, instruction-injection, no-recipe, title-and-ingredients-only, and blurred pages, each with an expected draft (`CASES.md`) and a sharpness label for calibration.
- `scripts/eval_picture_capture.py`: runs the real assistant by hand (constitution 6).
- `scripts/calibrate_picture_tiers.py`: computes the sharpness distribution on the labelled set and writes `picture_calibration.json`.
- One invented HEIC and one PNG with a broken tail are kept for refusal tests. No test calls the real assistant.
