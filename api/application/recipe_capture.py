"""Capture a recipe from pasted text into a draft, for one notebook (spec 016, FR-001a to FR-033).

Order of checks, so that refused input costs no read and no assistant call:
1. the trimmed text is empty or over the configured limit (FR-002);
2. the notebook exists and the caller may see it (membership first, FR-022);
3. a kitchen notebook's kitchen is not archived (FR-033);
4. the notebook's catalog is read, then the S-015 use case runs once.

Nothing is stored (FR-019). The log keeps the text length and the outcome, never the text
(constitution §4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from domain.errors import KitchenArchivedError, NotebookNotFoundError
from domain.recipe_draft import DraftRecipe

from application.notebooks import NotebookView, notebook_view
from application.ports import IngredientCatalog, NotebookRepository
from application.recipe_extraction import (
    Draft,
    ExtractionResult,
    RecipeExtraction,
    RecipeTextRefusedError,
)

logger = logging.getLogger(__name__)


class TextEmptyError(RecipeTextRefusedError):
    """Empty or whitespace-only text (FR-002). Maps to 422 `text_empty`."""

    CODE = "text_empty"

    def __init__(self) -> None:
        super().__init__(RecipeTextRefusedError.EMPTY)


class TextTooLongError(RecipeTextRefusedError):
    """Text over the configured limit after trimming (FR-002). Maps to 422 `text_too_long`."""

    CODE = "text_too_long"

    def __init__(self, limit: int) -> None:
        super().__init__(f"That text is too long. Paste up to {limit} characters.")


@dataclass(frozen=True, slots=True)
class CaptureRecipeCommand:
    actor_user_id: UUID
    notebook_id: UUID
    text: str
    # The member's account language (`users.language`, through effective_language).
    language: str


@dataclass(frozen=True, slots=True)
class CapturedDraft:
    """A draft for review. Not saved (FR-019)."""

    recipe: DraftRecipe
    notebook: NotebookView
    language: str


# A CapturedDraft, or one of the S-015 results that are not a draft (passed through unchanged).
CaptureOutcome = CapturedDraft | ExtractionResult


class CaptureRecipeText:
    def __init__(
        self,
        notebooks: NotebookRepository,
        catalog: IngredientCatalog,
        extraction: RecipeExtraction,
        *,
        max_chars: int,
        timeout_s: float,
    ) -> None:
        self._notebooks = notebooks
        self._catalog = catalog
        self._extraction = extraction
        self._max_chars = max_chars
        self._timeout_s = timeout_s

    def execute(self, command: CaptureRecipeCommand) -> CaptureOutcome:
        text = command.text.strip()
        if not text:
            raise TextEmptyError()
        if len(text) > self._max_chars:
            raise TextTooLongError(self._max_chars)

        facts = self._notebooks.facts_for(command.actor_user_id, command.notebook_id)
        if facts is None:
            raise NotebookNotFoundError()
        view = notebook_view(facts)
        if view.kitchen_is_archived:
            raise KitchenArchivedError()

        names = self._catalog.names_for_notebook(command.notebook_id)
        result = self._extraction.extract(text, names, self._timeout_s)
        logger.info(
            "recipe capture outcome=%s chars=%d",
            type(result).__name__,
            len(text),
        )
        if isinstance(result, Draft):
            return CapturedDraft(recipe=result.recipe, notebook=view, language=command.language)
        return result
