"""Recipe lists for a notebook and for a kitchen (spec 021).

Reads only: nothing here creates a notebook, a recipe or a catalog entry (FR-012). The
kitchen list does not run the first-open notebook creation of spec 056.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from domain.errors import NotebookNotFoundError
from domain.recipe_search import PAGE_SIZE, clamp_page, search_key

from application.kitchen_access import (
    AuthorizeKitchenAccessCommand,
    AuthorizeKitchenAccessService,
)
from application.kitchens import KitchenRepository
from application.notebooks import notebook_view
from application.ports import (
    NotebookRepository,
    RecipeCardRow,
    RecipeListRepository,
)


@dataclass(frozen=True, slots=True)
class RecipeListResult:
    items: list[RecipeCardRow]
    page: int
    page_size: int
    total: int
    total_pages: int


def _page_of(
    recipes: RecipeListRepository, notebook_ids: list[UUID], text: str, requested: int
) -> RecipeListResult:
    key = search_key(text)
    clamp_page(requested, 0)  # rejects a page below 1 before any read
    found = recipes.list_page(notebook_ids, key, (requested - 1) * PAGE_SIZE, PAGE_SIZE)
    page, total_pages = clamp_page(requested, found.total)
    if page != requested:  # past the last page: show the last one
        found = recipes.list_page(notebook_ids, key, (page - 1) * PAGE_SIZE, PAGE_SIZE)
    return RecipeListResult(
        items=found.items,
        page=page,
        page_size=PAGE_SIZE,
        total=found.total,
        total_pages=total_pages,
    )


@dataclass(frozen=True, slots=True)
class ListNotebookRecipesCommand:
    actor_user_id: UUID
    notebook_id: UUID
    page: int = 1
    q: str = ""


class ListNotebookRecipesService:
    """One notebook's recipes for a caller who may read it; anyone else gets not found."""

    def __init__(self, notebooks: NotebookRepository, recipes: RecipeListRepository) -> None:
        self._notebooks = notebooks
        self._recipes = recipes

    def execute(self, command: ListNotebookRecipesCommand) -> RecipeListResult:
        facts = self._notebooks.facts_for(command.actor_user_id, command.notebook_id)
        if facts is None:
            raise NotebookNotFoundError()
        notebook_view(facts)  # raises NotebookNotFoundError when the caller has no access
        return _page_of(self._recipes, [command.notebook_id], command.q, command.page)


@dataclass(frozen=True, slots=True)
class ListKitchenRecipesCommand:
    actor_user_id: UUID
    kitchen_id: UUID
    page: int = 1
    q: str = ""


class ListKitchenRecipesService:
    """The recipes of every notebook of a kitchen, for a member. Archived kitchens allowed."""

    def __init__(
        self,
        kitchens: KitchenRepository,
        notebooks: NotebookRepository,
        recipes: RecipeListRepository,
    ) -> None:
        self._kitchens = kitchens
        self._notebooks = notebooks
        self._recipes = recipes

    def execute(self, command: ListKitchenRecipesCommand) -> RecipeListResult:
        grant = AuthorizeKitchenAccessService(self._kitchens).execute(
            AuthorizeKitchenAccessCommand(
                acting_user_id=command.actor_user_id,
                kitchen_id=command.kitchen_id,
                action="read_kitchen",
            )
        )
        kitchen = self._kitchens.get_kitchen_with_grant(grant, command.kitchen_id)
        notebook_ids = self._notebooks.kitchen_ids_for(kitchen.id)
        return _page_of(self._recipes, notebook_ids, command.q, command.page)
