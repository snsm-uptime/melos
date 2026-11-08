# Contract: ports and domain functions

## `domain/recipe_picture.py` (pure)

```python
PICTURE_MAX_BYTES = 10_000_000
PICTURE_MAX_ENCODED_CHARS = 13_333_336          # ceil(10_000_000 / 3) * 4

@dataclass(frozen=True, slots=True)
class CheckedPicture:
    data: bytes
    media_type: Literal["image/jpeg", "image/png", "image/heic", "image/heif"]

class PictureRefused(DomainError):
    kind: Literal["empty", "unsupported", "too_large"]

def check_picture(image_base64: str) -> CheckedPicture: ...
```

- `PictureRefused("empty")` for an empty string; `"too_large"` when the string exceeds `PICTURE_MAX_ENCODED_CHARS` (checked before decoding) or the decoded bytes exceed `PICTURE_MAX_BYTES`; `"unsupported"` for invalid base64, an unknown signature, an `avif` brand, or a broken PNG or HEIC container. JPEG is checked by signature only (plan I3).
- Never reads the file name or any client-announced type. No I/O; no imports from `application/`, `adapters/` or frameworks.

## `domain/picture_tiers.py` (pure)

```python
class Tier(StrEnum):
    TIER_1 = "tier_1"    # aggressive: max side 1600, quality 70, cap 300 KB
    TIER_2 = "tier_2"    # balanced:   max side 2000, quality 80, cap 300 KB
    TIER_3 = "tier_3"    # high:       max side 2400, quality 90, cap 500 KB

@dataclass(frozen=True, slots=True)
class CalibrationTable:
    low: float
    high: float
    labelled_set: str
    calibrated_on: date
    status: Literal["provisional", "calibrated"]

@dataclass(frozen=True, slots=True)
class EncodingStep:
    quality: int
    max_side: int

def choose_tier(handwritten: bool, sharpness: float | None, table: CalibrationTable) -> Tier: ...
def plan_encoding(tier: Tier) -> tuple[EncodingStep, ...]: ...
def cap_bytes(tier: Tier) -> int: ...
def require_calibrated(table: CalibrationTable) -> None: ...   # raises when status is "provisional" (release check)
```

- `choose_tier`: handwritten → `TIER_3`; otherwise `sharpness` is required (`ValueError` when `None`); `sharpness < table.low` → `TIER_3`; `sharpness >= table.high` → `TIER_1`; otherwise `TIER_2`.
- `plan_encoding`: the ordered steps. Quality 90→60 by 5 at the tier's starting side, then the side reduced by 10% per step to the floor (Tier 3 side 1200; Tiers 1 and 2 side 1000), quality 60. The adapter takes the first step whose WebP is within `cap_bytes`.
- `cap_bytes`: 500 KB for Tier 3, 300 KB for Tiers 1 and 2.
- No I/O. The table is passed in; loading it is the adapter's job.

## `domain/recipe_draft.py`, addition

```python
def open_incomplete(recipe: DraftRecipe) -> DraftRecipe: ...
```

The helper formerly named `_as_is` in `application/recipe_capture_url.py`, moved here and keeping `language=recipe.language`. Blanks stay blank; servings below 1 or missing become 4 and are flagged estimated. Link capture calls it; link behaviour is unchanged.

## `application/ports.py`, additions

```python
@dataclass(frozen=True, slots=True)
class Picture:
    data: bytes
    media_type: str                  # "image/webp" for the assistant

@dataclass(frozen=True, slots=True)
class ProcessedPicture:
    webp: bytes
    tier: Tier
    sharpness: float | None          # None when handwritten is true
    original_dimensions: tuple[int, int]
    final_dimensions: tuple[int, int]
    size_kb: float
    steps_taken: tuple[str, ...]

class PicturePipeline(Protocol):
    """Port: checked bytes in, processed WebP out. Raises PictureRefused for an image it cannot
    use (unreadable, over 64 MP, or still over cap at the floor). Never returns the original."""

    def process(self, picture: CheckedPicture, *, handwritten: bool, table: CalibrationTable) -> ProcessedPicture: ...
```

`CheckedPicture` and `Tier` are domain types; the port's signature names them, so the adapter imports the domain, which is allowed (adapters depend inward).

## `application/recipe_extraction.py`, additions

```python
class ExtractionMode(StrEnum):
    WHOLE = "whole"
    PAGE_PART = "page_part"
    PICTURE = "picture"

class RecipeExtractor(Protocol):
    def extract(...) -> ExtractionResult: ...          # unchanged
    def extract_picture(
        self,
        picture: Picture,
        ingredient_names: Sequence[str],
        timeout_s: float,
    ) -> ExtractionResult: ...
```

- `extract_picture` never raises for service, network or output problems. It returns `DraftPart`, `NotARecipe(reason)`, `NotARecipe(MULTIPLE_RECIPES)`, `InvalidOutput`, `Unavailable`, `LimitReached` or `AIProviderError`. It never returns `Draft`, `DraftIncomplete` or `NoRecipeContent`.
- `RecipeExtraction.extract_picture`: calls the port; on a `DraftPart`, sets `language` by offline detection over the part's text; no in-flight sharing. Logs media type, byte count and result class only.

## `application/recipe_capture_picture.py` (new)

```python
@dataclass(frozen=True, slots=True)
class CapturePictureCommand:
    actor_user_id: UUID
    notebook_id: UUID
    image_base64: str
    handwritten: bool
    language: str

@dataclass(frozen=True, slots=True)
class CapturedPictureDraft:
    recipe: DraftRecipe
    notebook: NotebookView
    language: str
    catalog: tuple[str, ...]
    picture: ProcessedPicture

CapturePictureOutcome = CapturedPictureDraft | ExtractionResult

class CapturePictureRecipe:
    def __init__(self, notebooks, catalog, extraction, pipeline: PicturePipeline, *,
                 units, timeout_s: float, table: CalibrationTable) -> None: ...
    def execute(self, command: CapturePictureCommand) -> CapturePictureOutcome: ...
```

Order: `check_picture` (`PictureRefused`) → notebook facts (`NotebookNotFoundError`) → archived (`KitchenArchivedError`) → `pipeline.process` (`PictureRefused` for an unusable image) → catalog and units → `extract_picture(Picture(webp, "image/webp"), names, timeout_s)` → for a `DraftPart`: `merge_parts([part])`, `check_draft`; on `DraftProblems`, `open_incomplete`. Returns `CapturedPictureDraft` or the extractor's result unchanged. No HTTP types, so the MCP capture tool (S-032) can call it (FR-023). Nothing is stored.

## `adapters/image/pipeline.py` (new, Pillow, NumPy, pillow-heif)

- `PillowPicturePipeline(...)` implements `PicturePipeline`.
- Refuses over `64_000_000` pixels explicitly before decoding; sets `Image.MAX_IMAGE_PIXELS = 128_000_000` so Pillow's bomb error sits above it; registers the HEIF opener (`pillow_heif.register_heif_opener()`) once at import.
- Steps: open → `ImageOps.exif_transpose` → convert to RGB (palette and alpha) → Laplacian (computed only when `handwritten` is false, FR-025) → `choose_tier` → for each `plan_encoding` step: resize (LANCZOS, `thumbnail`) and encode WebP `method=6`; the first step within `cap_bytes` wins → `ProcessedPicture`.
- Returns `PictureRefused("too_large")` when no step fits; `PictureRefused("unsupported")` for decode failures or the pixel limit.
- Logs tier, sharpness, dimensions, size and steps only.

## `adapters/image/laplacian.py` (new, NumPy)

```python
def laplacian_sharpness(gray: np.ndarray) -> float: ...
```

3×3 kernel `[[0,1,0],[1,-4,1],[0,1,0]]` on a grayscale `float32` array, by slicing (no SciPy, no OpenCV); returns the variance of the response divided by the pixel count. Pure function over arrays, tested with synthetic images (flat = 0, checkerboard highest).

## `adapters/llm/gemini_extractor.py`, additions

- `PICTURE_RESPONSE_SCHEMA`: `outcome` in `recipe | not_a_recipe | multiple_recipes | unreadable`; `reason` in `not_food | story_or_article`; `recipe` with `title`, `base_servings`, `ingredient_lines` (whole-mode item schema) and `steps`, none required.
- `extract_picture` builds `contents = [Part.from_bytes(data, "image/webp"), Part.from_text(names block + one line)]`, with the picture system instruction, `response_json_schema=PICTURE_RESPONSE_SCHEMA`, `timeout=round(timeout_s * 1000)`, `attempts=1`. Errors go through `gemini_errors.classify`; logs carry class and request reference only.
- Whole-recipe and page-part schemas, prompts and code paths are not touched.

## `adapters/llm/fake_extractor.py`, addition

`FakeRecipeExtractor.extract_picture(...)` returns scripted results in order and records a `PictureCall(media_type, byte_count, ingredient_names, timeout_s)` (never the bytes).

## Preferences (see `disclaimers-preference.md`)

`UserPreferencesRecord` gains `disclaimers: bool`; `PreferencesRepository.update_preferences(..., disclaimers: bool | None = None)`.
