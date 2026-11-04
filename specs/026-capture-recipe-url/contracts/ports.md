# Contract: ports for link capture (spec 026)

All in `api/application/ports.py` unless noted. Adapters never raise for network, site or service problems; they return a result value.

## PageFetcher (new, PRD §1.4)

```python
class PageFetcher(Protocol):
    def fetch_page(self, url: str) -> FetchedPage | PageFetchFailed: ...
    def fetch_image(self, url: str) -> FetchedImage | None: ...
```

- Adapter: `adapters/web/page_fetcher.py` (`HttpxPageFetcher`). Fake: `adapters/web/fake_page_fetcher.py` (`FakePageFetcher`: a dict of URL → result, records every call, never opens a socket).
- Both methods apply, for the first request and each redirect: `domain.page_link.check_link`, DNS resolution bounded by the deadline, `domain.page_link.is_public_address` on every resolved address, connection pinned to a checked address (research R2), at most 3 redirects (R3).
- `fetch_page`: 10 s in total, 2 MB, 2xx only, HTML only (R4). Returns the final URL and the decoded HTML.
- `fetch_image`: 5 s, 2 MB, 2xx only, JPEG, PNG or WebP by magic bytes. Any failure → `None`.
- Sends no cookie, no session, no auth header, no `Referer`, and a fixed `User-Agent`.
- Tests: the adapter takes an injectable resolver (`host → list[str]`) and an `httpx.MockTransport`, so blocked-address, rebinding, redirect, size, type and timeout cases run without a network (SC-003).

## PageReader (new)

```python
class PageReader(Protocol):
    def read(self, html: str, base_url: str) -> PageContent: ...
```

- Adapter: `adapters/web/page_reader.py` (`TrafilaturaPageReader`), using `adapters/web/jsonld.py` for the `<script type="application/ld+json">` blocks and the og:image tag, `domain.recipe_page.recipes_from_jsonld` for the mapping, and trafilatura for the Markdown (research R6).
- Pure in effect: no network, no file access. Never raises for bad HTML; an unreadable page gives `PageContent(recipes=(), main_image_url=None, markdown="")`.
- Fake: `FakePageReader` returns a fixed `PageContent`.

## RecipeExtractor (spec 015, extended)

```python
class ExtractionMode(StrEnum):
    WHOLE = "whole"
    PAGE_PART = "page_part"

class RecipeExtractor(Protocol):
    def extract(
        self,
        text: str,
        ingredient_names: Sequence[str],
        timeout_s: float,
        *,
        mode: ExtractionMode = ExtractionMode.WHOLE,
        part: tuple[int, int] | None = None,   # (index from 1, total), only in PAGE_PART
    ) -> ExtractionResult: ...
```

- `WHOLE`: unchanged in every way (prompt, schema, results). Text capture keeps calling it with no new arguments.
- `PAGE_PART`: system template `adapters/llm/prompts/recipe_extraction_page_part_system.md`; user template `recipe_extraction_user.md` plus the part line; response schema with outcome `recipe_part | no_recipe_content | multiple_recipes` and no required recipe fields. Returns `DraftPart`, `NoRecipeContent`, `NotARecipe(MULTIPLE_RECIPES)` or one of the failure results.
- `ExtractionResult` gains `DraftPart | NoRecipeContent`. Callers of whole mode never receive them.
- `RecipeExtraction.extract(..., mode=..., part=...)` passes them through; it runs `check_draft` only on a whole-mode `Draft`. The in-flight key includes mode and part.
- `FakeRecipeExtractor` records `mode` and `part` in `ExtractionCall`.
- Prompt rules shared by both templates (line rules, vague phrases, units, security rule) are kept identical; `tests/test_prompt_characterization.py` gains a check that the shared block is the same in both.

## CaptureRecipeUrl (new use case, `application/recipe_capture_url.py`)

```python
@dataclass(frozen=True, slots=True)
class CaptureRecipeUrlCommand:
    actor_user_id: UUID
    notebook_id: UUID
    url: str
    language: str

class CaptureRecipeUrl:
    def __init__(self, notebooks, catalog, extraction, fetcher: PageFetcher, reader: PageReader,
                 *, units, timeout_s: float, batch_chars: int, max_batches: int) -> None: ...
    def execute(self, command: CaptureRecipeUrlCommand) -> CapturedPageDraft | ExtractionResult | PageRefusal: ...
```

- `PageRefusal`: `PageLinkRefused(kind)`, `PageFetchFailed(kind)`, `PageNoRecipe()`.
- Raises `NotebookNotFoundError` and `KitchenArchivedError` as text capture does, before any fetch.
- No HTTP types, so the S-032 MCP tool can reuse it (FR-026).
