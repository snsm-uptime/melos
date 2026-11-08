"""Picture capture (spec 041): one cookbook photo in, one checked draft out. Nothing is stored.

Order: check the picture → notebook facts → archived kitchen → pipeline (compress, measure) →
catalog and units → assistant → merge and check. Refusals of the picture itself are raised
before any notebook read; the assistant's failures come back as the extractor's results.
No HTTP types here, so the MCP capture tool can call it (FR-023).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from domain.errors import KitchenArchivedError, NotebookNotFoundError
from domain.ingredient_catalog import CatalogIndex
from domain.picture_tiers import CalibrationTable
from domain.recipe_draft import (
    DraftProblems,
    DraftRecipe,
    InvalidDraftError,
    check_draft,
    open_incomplete,
)
from domain.recipe_page import DraftPart, MultipleRecipes, NoRecipeContent, merge_parts
from domain.recipe_picture import check_picture

from application.notebooks import NotebookView, notebook_view
from application.ports import (
    IngredientCatalog,
    NotebookRepository,
    Picture,
    PicturePipeline,
    ProcessedPicture,
    UnitRepository,
)
from application.recipe_extraction import (
    ExtractionResult,
    InvalidOutput,
    RecipeExtraction,
)
from application.units import available_units

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CapturePictureCommand:
    actor_user_id: UUID
    notebook_id: UUID
    image_base64: str
    # Handwritten pictures skip the sharpness measure and use Tier 3 (FR-025). Default on.
    handwritten: bool = True
    # The member's account language (`users.language`, through effective_language).
    language: str = "es"


@dataclass(frozen=True, slots=True)
class CapturedPictureDraft:
    """A draft for review, with the processed picture as its preview. Not saved, no original."""

    recipe: DraftRecipe
    notebook: NotebookView
    language: str
    catalog: tuple[str, ...]
    picture: ProcessedPicture


CapturePictureOutcome = CapturedPictureDraft | ExtractionResult


class CapturePictureRecipe:
    def __init__(
        self,
        notebooks: NotebookRepository,
        catalog: IngredientCatalog,
        extraction: RecipeExtraction,
        pipeline: PicturePipeline,
        *,
        units: UnitRepository,
        timeout_s: float,
        table: CalibrationTable,
    ) -> None:
        self._notebooks = notebooks
        self._catalog = catalog
        self._extraction = extraction
        self._pipeline = pipeline
        self._units = units
        self._timeout_s = timeout_s
        self._table = table

    def execute(self, command: CapturePictureCommand) -> CapturePictureOutcome:
        checked = check_picture(command.image_base64)

        facts = self._notebooks.facts_for(command.actor_user_id, command.notebook_id)
        if facts is None:
            raise NotebookNotFoundError()
        view = notebook_view(facts)
        if view.kitchen_is_archived:
            raise KitchenArchivedError()

        processed = self._pipeline.process(
            checked, handwritten=command.handwritten, table=self._table
        )

        names: CatalogIndex = self._catalog.index_for_notebook(command.notebook_id)
        units = available_units(self._units.extras_for(command.actor_user_id))
        result = self._extraction.extract_picture(
            Picture(data=processed.webp, media_type="image/webp"),
            names,
            self._timeout_s,
        )

        outcome = self._draft(result, names, units, command, view, processed)
        logger.info(
            "picture capture outcome=%s tier=%s bytes=%d",
            type(outcome).__name__,
            processed.tier.value,
            len(checked.data),
        )
        return outcome

    def _draft(
        self,
        result: ExtractionResult,
        names: CatalogIndex,
        units: tuple[str, ...],
        command: CapturePictureCommand,
        view: NotebookView,
        processed: ProcessedPicture,
    ) -> CapturePictureOutcome:
        if not isinstance(result, DraftPart):
            return result
        merged = merge_parts([result])
        if isinstance(merged, (MultipleRecipes, NoRecipeContent)):
            return InvalidOutput()
        try:
            recipe = check_draft(merged, names, units)
        except DraftProblems:
            recipe = open_incomplete(merged)
        except InvalidDraftError:
            return InvalidOutput()
        return CapturedPictureDraft(
            recipe=recipe,
            notebook=view,
            language=command.language,
            catalog=tuple(names.all_names()),
            picture=processed,
        )
