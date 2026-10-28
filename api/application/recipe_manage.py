"""Read, edit and delete a saved recipe (spec 027).

Every use case starts with `_recipe_for`, the one place that decides who may read and who may
write. A person who may not read the recipe's notebook gets the same `RecipeNotFoundError` as
for a missing recipe (FR-006). `DeleteRecipeService` and `UpdateRecipeService` are the single
places where later stories hook in: cart and citation cleanup on delete (S-022, S-030) and
re-embedding on edit (S-019) (research R10).

Nothing is logged but outcomes and counts (constitution §4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.errors import NotebookNotFoundError, RecipeNotFoundError, RecipeReadOnlyError
from domain.ingredient_catalog import propose_entry
from domain.notebook import can_write_recipes
from domain.recipe import MAX_LINES, MAX_STEPS, EditedRecipe, resolve_line_names
from domain.recipe_draft import (
    DraftProblems,
    DraftRecipe,
    IngredientLine,
    InvalidDraftError,
    check_edited_draft,
)

from application.notebooks import NotebookView, notebook_view
from application.ports import IngredientCatalog, NotebookRepository, RecipeDetail, RecipeRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RecipeView:
    """A recipe, its notebook as the caller sees it, and whether the caller may change it."""

    detail: RecipeDetail
    notebook: NotebookView
    can_write: bool


def _recipe_for(
    recipes: RecipeRepository,
    notebooks: NotebookRepository,
    actor_user_id: UUID,
    recipe_id: UUID,
    *,
    write: bool,
) -> RecipeView:
    detail = recipes.get_detail(recipe_id)
    if detail is None:
        raise RecipeNotFoundError()
    facts = notebooks.facts_for(actor_user_id, detail.notebook_id)
    if facts is None:
        raise RecipeNotFoundError()
    try:
        view = notebook_view(facts)
    except NotebookNotFoundError:
        raise RecipeNotFoundError() from None
    can_write = can_write_recipes(view.access, view.kitchen_is_archived)
    if write and not can_write:
        raise RecipeReadOnlyError()
    return RecipeView(detail=detail, notebook=view, can_write=can_write)


@dataclass(frozen=True, slots=True)
class GetRecipeCommand:
    actor_user_id: UUID
    recipe_id: UUID


class GetRecipeService:
    """Open one recipe. Reads only (FR-018)."""

    def __init__(self, recipes: RecipeRepository, notebooks: NotebookRepository) -> None:
        self._recipes = recipes
        self._notebooks = notebooks

    def execute(self, command: GetRecipeCommand) -> RecipeView:
        return _recipe_for(
            self._recipes, self._notebooks, command.actor_user_id, command.recipe_id, write=False
        )


@dataclass(frozen=True, slots=True)
class MatchRecipeNamesCommand:
    actor_user_id: UUID
    recipe_id: UUID
    names: tuple[str, ...]


class MatchRecipeNamesService:
    """For each typed name, the catalog entry of the recipe's notebook it matches (FR-009)."""

    def __init__(
        self,
        recipes: RecipeRepository,
        notebooks: NotebookRepository,
        catalog: IngredientCatalog,
    ) -> None:
        self._recipes = recipes
        self._notebooks = notebooks
        self._catalog = catalog

    def execute(self, command: MatchRecipeNamesCommand) -> list[tuple[str, str | None]]:
        view = _recipe_for(
            self._recipes, self._notebooks, command.actor_user_id, command.recipe_id, write=True
        )
        entries = self._catalog.names_for_notebook(view.notebook.id)
        return [(name, propose_entry(name, entries)) for name in command.names]


@dataclass(frozen=True, slots=True)
class UpdateRecipeCommand:
    actor_user_id: UUID
    recipe_id: UUID
    version: datetime
    title: str
    base_servings: int
    servings_estimated: bool
    lines: tuple[IngredientLine, ...]
    steps: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UpdatedRecipe:
    view: RecipeView
    created_catalog_names: tuple[str, ...]


class UpdateRecipeService:
    """Replace a recipe's content.

    Order of checks, so that a refused edit stores nothing: size limits, access, the recipe
    rules, the catalog spelling, then the version-checked write; catalog names are added only
    after the write succeeds.
    """

    def __init__(
        self,
        recipes: RecipeRepository,
        notebooks: NotebookRepository,
        catalog: IngredientCatalog,
    ) -> None:
        self._recipes = recipes
        self._notebooks = notebooks
        self._catalog = catalog

    def execute(self, command: UpdateRecipeCommand) -> UpdatedRecipe:
        if len(command.lines) > MAX_LINES or len(command.steps) > MAX_STEPS:
            raise InvalidDraftError("too long")
        current = _recipe_for(
            self._recipes, self._notebooks, command.actor_user_id, command.recipe_id, write=True
        )
        # An edit needs at least one ingredient line (spec 027 FR-008); the first save does not
        # check this, so the edit adds it to the parts the member is told about.
        no_lines = not command.lines
        try:
            checked = check_edited_draft(
                DraftRecipe(
                    title=command.title,
                    base_servings=command.base_servings,
                    servings_estimated=command.servings_estimated,
                    ingredient_lines=command.lines,
                    steps=command.steps,
                )
            )
        except DraftProblems as exc:
            missing = exc.missing + (("ingredients",) if no_lines else ())
            raise DraftProblems(missing=missing, line_problems=exc.line_problems) from None
        if no_lines:
            raise DraftProblems(missing=("ingredients",))
        lines, new_names = resolve_line_names(
            checked.ingredient_lines, self._catalog.names_for_notebook(current.notebook.id)
        )
        assert checked.base_servings is not None
        stored = self._recipes.replace(
            command.recipe_id,
            command.version,
            EditedRecipe(
                title=checked.title,
                base_servings=checked.base_servings,
                servings_estimated=checked.servings_estimated,
                lines=lines,
                steps=checked.steps,
            ),
        )
        self._catalog.add_names(current.notebook.id, new_names)
        logger.info(
            "recipe edit outcome=updated lines=%d steps=%d new_names=%d",
            len(lines),
            len(checked.steps),
            len(new_names),
        )
        return UpdatedRecipe(
            view=RecipeView(detail=stored, notebook=current.notebook, can_write=True),
            created_catalog_names=new_names,
        )


@dataclass(frozen=True, slots=True)
class DeleteRecipeCommand:
    actor_user_id: UUID
    recipe_id: UUID


class DeleteRecipeService:
    """Remove a recipe, its lines, steps and source.

    This is the one place a recipe is deleted. The cart (S-022), search data (S-019) and chat
    citations (S-030) do not exist yet; each adds its cleanup here, and the schema guard test
    in tests/test_recipe_manage_integration.py fails until it does (spec 027 FR-016).
    """

    def __init__(self, recipes: RecipeRepository, notebooks: NotebookRepository) -> None:
        self._recipes = recipes
        self._notebooks = notebooks

    def execute(self, command: DeleteRecipeCommand) -> None:
        _recipe_for(
            self._recipes, self._notebooks, command.actor_user_id, command.recipe_id, write=True
        )
        self._recipes.delete(command.recipe_id)
        logger.info("recipe delete outcome=deleted")
