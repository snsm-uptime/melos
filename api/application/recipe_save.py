"""Save a confirmed draft as a recipe in its notebook (spec 020).

Order of checks, so that a refused save stores nothing (research R4):
1. the pasted text and the draft size are within their limits (FR-019);
2. a repeated Save with the same key returns the recipe already stored (FR-013);
3. the notebook exists, the caller may see it, and its kitchen is not archived (FR-012);
   with only a kitchen given, the capture-notebook step picks or creates one (FR-011);
4. the edited draft passes the recipe rules again (FR-005);
5. the catalog is read, names are resolved, and the recipe and the new names are stored.

Nothing is logged but the outcome and the counts (constitution §4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from domain.errors import KitchenArchivedError, NotebookNotFoundError
from domain.recipe import MAX_LINES, MAX_STEPS, NewRecipe, resolve_line_names
from domain.recipe_draft import DraftRecipe, IngredientLine, InvalidDraftError, check_edited_draft

from application.notebooks import (
    NotebookView,
    ResolveCaptureNotebookCommand,
    ResolveCaptureNotebookService,
    notebook_view,
)
from application.ports import (
    DuplicateSaveKeyError,
    IngredientCatalog,
    NotebookRepository,
    RecipeRepository,
    StoredRecipe,
)
from application.recipe_capture import TextTooLongError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SaveRecipeCommand:
    actor_user_id: UUID
    save_key: UUID
    source_text: str
    title: str
    base_servings: int
    servings_estimated: bool
    lines: tuple[IngredientLine, ...]
    steps: tuple[str, ...]
    # Exactly one of these is set (research R6).
    notebook_id: UUID | None = None
    kitchen_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class SavedRecipe:
    recipe: StoredRecipe
    notebook: NotebookView
    # False when this was a repeated Save that returned the recipe already stored.
    created: bool
    created_catalog_names: tuple[str, ...] = ()


class SaveRecipeDraft:
    def __init__(
        self,
        notebooks: NotebookRepository,
        catalog: IngredientCatalog,
        recipes: RecipeRepository,
        capture_notebook: ResolveCaptureNotebookService,
        *,
        max_text_chars: int,
    ) -> None:
        self._notebooks = notebooks
        self._catalog = catalog
        self._recipes = recipes
        self._capture_notebook = capture_notebook
        self._max_text_chars = max_text_chars

    def execute(self, command: SaveRecipeCommand) -> SavedRecipe:
        if (command.notebook_id is None) == (command.kitchen_id is None):
            raise InvalidDraftError("notebook")
        source_text = command.source_text.strip()
        if len(source_text) > self._max_text_chars:
            raise TextTooLongError(self._max_text_chars)
        if len(command.lines) > MAX_LINES or len(command.steps) > MAX_STEPS:
            raise InvalidDraftError("too long")

        stored = self._recipes.find_by_save_key(command.actor_user_id, command.save_key)
        if stored is not None:
            return self._replay(command, stored)

        view = self._notebook(command)
        if view.kitchen_is_archived:
            raise KitchenArchivedError()

        checked = check_edited_draft(
            DraftRecipe(
                title=command.title,
                base_servings=command.base_servings,
                servings_estimated=command.servings_estimated,
                ingredient_lines=command.lines,
                steps=command.steps,
            )
        )
        lines, new_names = resolve_line_names(
            checked.ingredient_lines, self._catalog.names_for_notebook(view.id)
        )
        assert checked.base_servings is not None
        recipe = NewRecipe(
            title=checked.title,
            base_servings=checked.base_servings,
            servings_estimated=checked.servings_estimated,
            lines=lines,
            steps=checked.steps,
            source_text=source_text,
            author_id=command.actor_user_id,
            notebook_id=view.id,
            save_key=command.save_key,
        )
        try:
            stored = self._recipes.add(recipe)
        except DuplicateSaveKeyError:
            # A concurrent Save with the same key won; return its recipe.
            winner = self._recipes.find_by_save_key(command.actor_user_id, command.save_key)
            assert winner is not None
            return self._replay(command, winner)
        self._catalog.add_names(view.id, new_names)
        logger.info(
            "recipe save outcome=created lines=%d steps=%d new_names=%d",
            len(lines),
            len(checked.steps),
            len(new_names),
        )
        return SavedRecipe(
            recipe=stored, notebook=view, created=True, created_catalog_names=new_names
        )

    def _notebook(self, command: SaveRecipeCommand) -> NotebookView:
        notebook_id = command.notebook_id
        if notebook_id is None:
            assert command.kitchen_id is not None
            notebook_id = self._capture_notebook.execute(
                ResolveCaptureNotebookCommand(
                    actor_user_id=command.actor_user_id, kitchen_id=command.kitchen_id
                )
            ).notebook_id
        facts = self._notebooks.facts_for(command.actor_user_id, notebook_id)
        if facts is None:
            raise NotebookNotFoundError()
        return notebook_view(facts)

    def _replay(self, command: SaveRecipeCommand, stored: StoredRecipe) -> SavedRecipe:
        facts = self._notebooks.facts_for(command.actor_user_id, stored.notebook_id)
        if facts is None:
            raise NotebookNotFoundError()
        logger.info("recipe save outcome=replayed")
        return SavedRecipe(recipe=stored, notebook=notebook_view(facts), created=False)
