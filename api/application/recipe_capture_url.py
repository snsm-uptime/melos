"""Capture a recipe from a web page link into a draft, for one notebook (spec 026).

Order of checks, so that refused input costs no fetch and no assistant call:
1. the link rules (`domain.page_link`), raising PageLinkRefused;
2. the notebook exists and the caller may see it; its kitchen is not archived;
3. the page is fetched through the PageFetcher (`PageFetchFailed` on any problem);
4. the page is read: one schema.org Recipe with ingredients → its text; two or more → refused;
   else the page's Markdown. One batch goes through whole-recipe mode, like pasted text; more
   go at the same time through partial page mode and are merged, then checked (research R8).
The main photo is fetched alongside the assistant call and returned as a data URI.

Nothing is stored (FR-019). Logs keep the outcome, host, byte count, Markdown length, batch
count and cut, never the address path, page text or photo (research R12). No HTTP types, so
the S-032 MCP tool can reuse it (R13).
"""

from __future__ import annotations

import base64
import logging
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import urlsplit
from uuid import UUID

from domain.errors import KitchenArchivedError, NotebookNotFoundError
from domain.page_link import normalize_link
from domain.recipe_draft import (
    DEFAULT_SERVINGS,
    DraftProblems,
    DraftRecipe,
    InvalidDraftError,
    check_draft,
)
from domain.recipe_page import (
    DraftPart,
    MultipleRecipes,
    NoRecipeContent,
    PageRecipe,
    apply_page_recipe,
    markdown_from,
    merge_parts,
    split_markdown,
)

from application.notebooks import NotebookView, notebook_view
from application.ports import (
    FetchedImage,
    IngredientCatalog,
    NotebookRepository,
    PageFetcher,
    PageFetchFailed,
    PageReader,
    UnitRepository,
)
from application.recipe_extraction import (
    AIProviderError,
    Draft,
    DraftIncomplete,
    ExtractionMode,
    ExtractionResult,
    InvalidOutput,
    LimitReached,
    NotARecipe,
    NotRecipeReason,
    RecipeExtraction,
    Unavailable,
)
from application.units import available_units

logger = logging.getLogger(__name__)

_FAILURES = (Unavailable, LimitReached, InvalidOutput, AIProviderError)


@dataclass(frozen=True, slots=True)
class CaptureRecipeUrlCommand:
    actor_user_id: UUID
    notebook_id: UUID
    url: str
    # The member's account language (`users.language`, through effective_language).
    language: str


@dataclass(frozen=True, slots=True)
class CapturedPageDraft:
    """A draft for review, with where it came from. Not saved (FR-019)."""

    recipe: DraftRecipe
    notebook: NotebookView
    language: str
    catalog: tuple[str, ...]
    # The address after redirects, which Save stores.
    source_url: str
    # The page's main photo as a data URI, never the site's address; None when there is none.
    preview_image: str | None
    # Markdown beyond the batch cap was not read.
    page_cut: bool


@dataclass(frozen=True, slots=True)
class PageNoRecipe:
    """The page opened but holds no recipe (FR-021a)."""


CaptureUrlOutcome = CapturedPageDraft | ExtractionResult | PageFetchFailed | PageNoRecipe


@dataclass(frozen=True, slots=True)
class _Source:
    markdown: str
    # Set on the schema.org path: its title, steps and servings win over the model's (AC2.3).
    page_recipe: PageRecipe | None


class CaptureRecipeUrl:
    def __init__(
        self,
        notebooks: NotebookRepository,
        catalog: IngredientCatalog,
        extraction: RecipeExtraction,
        fetcher: PageFetcher,
        reader: PageReader,
        *,
        units: UnitRepository,
        timeout_s: float,
        batch_chars: int,
        max_batches: int,
    ) -> None:
        self._notebooks = notebooks
        self._catalog = catalog
        self._extraction = extraction
        self._fetcher = fetcher
        self._reader = reader
        self._units = units
        self._timeout_s = timeout_s
        self._batch_chars = batch_chars
        self._max_batches = max_batches

    def execute(self, command: CaptureRecipeUrlCommand) -> CaptureUrlOutcome:
        link = normalize_link(command.url)

        facts = self._notebooks.facts_for(command.actor_user_id, command.notebook_id)
        if facts is None:
            raise NotebookNotFoundError()
        view = notebook_view(facts)
        if view.kitchen_is_archived:
            raise KitchenArchivedError()

        page = self._fetcher.fetch_page(link.url)
        if isinstance(page, PageFetchFailed):
            self._log("PageFetchFailed", link.host, kind=page.kind)
            return page
        content = self._reader.read(page.html, page.final_url)
        host = _host(page.final_url)

        if len(content.recipes) >= 2:
            self._log("MultipleRecipes", host, page_bytes=page.byte_count)
            return NotARecipe(reason=NotRecipeReason.MULTIPLE_RECIPES)
        source = _source(content.recipes, content.markdown)
        batches = split_markdown(source.markdown, self._batch_chars, self._max_batches)
        if not batches.batches:
            self._log("PageNoRecipe", host, page_bytes=page.byte_count, markdown_chars=0)
            return PageNoRecipe()

        names = self._catalog.names_for_notebook(command.notebook_id)
        units = available_units(self._units.extras_for(command.actor_user_id))
        pool = ThreadPoolExecutor(
            max_workers=len(batches.batches) + 1, thread_name_prefix="page-capture"
        )
        try:
            photo: Future[FetchedImage | None] | None = None
            if content.main_image_url:
                photo = pool.submit(self._fetcher.fetch_image, content.main_image_url)
            result = self._draft(pool, batches.batches, names, units)
            if isinstance(result, DraftIncomplete) and result.recipe is not None:
                # Whatever the page gave opens in the form, which marks the missing parts.
                result = Draft(recipe=_as_is(result.recipe))
            if isinstance(result, Draft) and source.page_recipe is not None:
                result = Draft(recipe=apply_page_recipe(result.recipe, source.page_recipe))
            self._log(
                type(result).__name__,
                host,
                page_bytes=page.byte_count,
                markdown_chars=len(source.markdown),
                batches=len(batches.batches),
                cut=batches.cut,
                schema_org=source.page_recipe is not None,
            )
            if not isinstance(result, Draft):
                return result
            return CapturedPageDraft(
                recipe=result.recipe,
                notebook=view,
                language=command.language,
                catalog=tuple(names),
                source_url=page.final_url,
                preview_image=_data_uri(photo),
                page_cut=batches.cut,
            )
        finally:
            # Futures still running (after a failed part) finish on their own and are dropped.
            pool.shutdown(wait=False)

    def _draft(
        self,
        pool: ThreadPoolExecutor,
        batches: tuple[str, ...],
        names: list[str],
        units: tuple[str, ...],
    ) -> ExtractionResult | PageNoRecipe:
        if len(batches) == 1:
            result = self._extraction.extract(batches[0], names, self._timeout_s, units)
            if isinstance(result, NotARecipe) and result.reason != NotRecipeReason.MULTIPLE_RECIPES:
                return PageNoRecipe()
            return result

        total = len(batches)
        futures = [
            pool.submit(
                self._extraction.extract,
                batch,
                names,
                self._timeout_s,
                units,
                mode=ExtractionMode.PAGE_PART,
                part=(index, total),
            )
            for index, batch in enumerate(batches, 1)
        ]
        parts: list[DraftPart | NoRecipeContent | MultipleRecipes] = []
        for future in futures:  # batch order: the first failure wins
            result = future.result()
            if isinstance(result, _FAILURES):
                return result
            if isinstance(result, DraftPart):
                parts.append(result)
            elif isinstance(result, NotARecipe):
                if result.reason == NotRecipeReason.MULTIPLE_RECIPES:
                    parts.append(MultipleRecipes())
                else:
                    parts.append(NoRecipeContent())
            else:
                parts.append(NoRecipeContent())

        merged = merge_parts(parts)
        if isinstance(merged, MultipleRecipes):
            return NotARecipe(reason=NotRecipeReason.MULTIPLE_RECIPES)
        if isinstance(merged, NoRecipeContent):
            return PageNoRecipe()
        try:
            return Draft(recipe=check_draft(merged, names, units))
        except DraftProblems as exc:
            return DraftIncomplete(problems=exc, recipe=merged)
        except InvalidDraftError as exc:
            logger.warning("merged page draft rejected by a recipe rule: %s", exc.MESSAGE)
            return InvalidOutput()

    def _log(self, outcome: str, host: str, **counts: object) -> None:
        details = " ".join(f"{key}={value}" for key, value in counts.items())
        logger.info("link capture outcome=%s host=%s %s", outcome, host, details)


def _as_is(recipe: DraftRecipe) -> DraftRecipe:
    """An incomplete draft, unchecked: blanks stay blank and the form asks for them.

    Lines are not matched to the catalog (they show as new). Servings left out by the page take
    the usual default, marked estimated.
    """
    servings = recipe.base_servings if recipe.base_servings and recipe.base_servings >= 1 else None
    return DraftRecipe(
        title=(recipe.title or "").strip(),
        base_servings=servings or DEFAULT_SERVINGS,
        servings_estimated=servings is None,
        ingredient_lines=recipe.ingredient_lines,
        steps=tuple(step.strip() for step in recipe.steps if step and step.strip()),
    )


def _source(recipes: tuple[PageRecipe, ...], markdown: str) -> _Source:
    if len(recipes) == 1 and recipes[0].ingredients:
        return _Source(markdown=markdown_from(recipes[0]), page_recipe=recipes[0])
    return _Source(markdown=markdown, page_recipe=None)


def _data_uri(photo: Future[FetchedImage | None] | None) -> str | None:
    if photo is None:
        return None
    try:
        image = photo.result()  # the fetcher stops itself at 5 s
    except Exception:
        logger.warning("photo fetch raised")
        return None
    if image is None:
        return None
    return f"data:{image.media_type};base64,{base64.b64encode(image.data).decode('ascii')}"


def _host(url: str) -> str:
    try:
        return urlsplit(url).hostname or "-"
    except ValueError:
        return "-"
