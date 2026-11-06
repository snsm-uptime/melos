"""Share one recipe with a co-member (spec 071).

The caller picks a person who shares a kitchen or a notebook with them. The recipe is copied into
that person's default notebook, authored by them, with no link back to the source. Ingredient
names are matched to the target notebook's catalog (the S-018 rule), and target names win.
The copy is not committed here: the request's one transaction makes it all or nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from domain.errors import (
    NotebookNotFoundError,
    RecipeNotFoundError,
    ShareRecipientNoDefaultNotebookError,
    ShareRecipientNotFoundError,
    ShareSelfError,
)
from domain.ingredient_catalog import propose_entry

from application.notebooks import _naming_profile, ensure_default_notebook
from application.ports import (
    CoMemberDirectory,
    CoMemberRecord,
    EmbeddingJobs,
    IngredientCatalog,
    NotebookRepository,
    PreferencesRepository,
    RecipeRepository,
    UserDefaultNotebook,
)
from application.recipe_manage import _recipe_for

__all__ = [
    "CoMemberRecord",
    "ListShareCandidatesService",
    "ShareRecipeCommand",
    "ShareRecipeService",
    "SharedRecipe",
]


class ListShareCandidatesService:
    """The people the caller can share with: co-members, most recent shared activity first."""

    def __init__(self, directory: CoMemberDirectory) -> None:
        self._directory = directory

    def execute(self, user_id: UUID) -> list[CoMemberRecord]:
        return self._directory.list_co_members(user_id)


@dataclass(frozen=True, slots=True)
class ShareRecipeCommand:
    actor_id: UUID
    recipe_id: UUID
    recipient_id: UUID


@dataclass(frozen=True, slots=True)
class SharedRecipe:
    recipe_id: UUID
    recipient_alias: str
    notebook_id: UUID


class ShareRecipeService:
    """Checks run before any write, so a refused share stores nothing."""

    def __init__(
        self,
        recipes: RecipeRepository,
        notebooks: NotebookRepository,
        catalog: IngredientCatalog,
        prefs: PreferencesRepository,
        directory: CoMemberDirectory,
        defaults: UserDefaultNotebook,
        *,
        embedding_jobs: EmbeddingJobs | None = None,
    ) -> None:
        self._recipes = recipes
        self._notebooks = notebooks
        self._catalog = catalog
        self._prefs = prefs
        self._directory = directory
        self._defaults = defaults
        self._embedding_jobs = embedding_jobs

    def execute(self, command: ShareRecipeCommand) -> SharedRecipe:
        # The caller must be able to read the source; otherwise the same 404 as a missing recipe.
        source = _recipe_for(
            self._recipes, self._notebooks, command.actor_id, command.recipe_id, write=False
        )
        if command.recipient_id == command.actor_id:
            raise ShareSelfError()
        if not self._directory.is_co_member(command.actor_id, command.recipient_id):
            raise ShareRecipientNotFoundError()

        recipient_alias, language = _naming_profile(self._prefs, command.recipient_id)
        try:
            notebook_id, _ = ensure_default_notebook(
                command.recipient_id,
                notebooks=self._notebooks,
                defaults=self._defaults,
                prefs=self._prefs,
                catalog=self._catalog,
            )
        except NotebookNotFoundError:
            raise ShareRecipientNoDefaultNotebookError() from None

        recipe_id = self._recipes.copy_one(
            command.recipe_id, notebook_id, command.recipient_id, link_source=False
        )
        if recipe_id is None:
            raise RecipeNotFoundError()

        names = list(dict.fromkeys(line.name for line in source.detail.lines))
        entries = self._catalog.names_for_notebook(notebook_id)
        renames: dict[str, str] = {}
        for name in names:
            entry = propose_entry(name, entries)
            if entry is not None and entry != name:
                renames[name] = entry
        if renames:
            self._recipes.rename_line_names(recipe_id, renames)
        self._catalog.add_names(notebook_id, [renames.get(name, name) for name in names])
        self._enqueue(recipe_id)
        return SharedRecipe(
            recipe_id=recipe_id,
            recipient_alias=recipient_alias,
            notebook_id=notebook_id,
        )

    def _enqueue(self, recipe_id: UUID) -> None:
        if self._embedding_jobs is not None:
            # Written in this transaction; the worker embeds it after commit (spec 019 FR-006).
            self._embedding_jobs.enqueue([recipe_id])
