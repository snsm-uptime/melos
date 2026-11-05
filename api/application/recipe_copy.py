"""Copy one personal recipe into a kitchen (spec 069).

The copy goes to the caller's own kitchen notebook of the kitchen, made first if missing, under
the kitchen lock the capture and snapshot paths take. A hidden `copied_from_recipe_id` turns a
second add of the same recipe into a question: add another copy, overwrite the latest, or cancel.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from domain.errors import (
    KitchenArchivedError,
    RecipeAlreadyInKitchenError,
    RecipeLockedError,
    RecipeNotFoundError,
)

from application.kitchen_access import (
    AuthorizeKitchenAccessCommand,
    AuthorizeKitchenAccessService,
)
from application.kitchens import KitchenRepository
from application.notebooks import _naming_profile, ensure_member_kitchen_notebook
from application.ports import (
    EditLockRepository,
    EmbeddingJobs,
    IngredientCatalog,
    NotebookRepository,
    PreferencesRepository,
    RecipeRepository,
)

logger = logging.getLogger(__name__)

OnRepeat = Literal["ask", "add", "overwrite"]


@dataclass(frozen=True, slots=True)
class CopyRecipeToKitchenCommand:
    actor_id: UUID
    kitchen_id: UUID
    source_recipe_id: UUID
    on_repeat: OnRepeat = "ask"


@dataclass(frozen=True, slots=True)
class CopiedRecipe:
    recipe_id: UUID
    notebook_id: UUID
    notebook_name: str
    overwritten: bool


class CopyRecipeToKitchenService:
    """Not committed here: the request's one transaction makes it all or nothing."""

    def __init__(
        self,
        kitchens: KitchenRepository,
        notebooks: NotebookRepository,
        recipes: RecipeRepository,
        catalog: IngredientCatalog,
        prefs: PreferencesRepository,
        locks: EditLockRepository,
        *,
        embedding_jobs: EmbeddingJobs | None = None,
    ) -> None:
        self._kitchens = kitchens
        self._notebooks = notebooks
        self._recipes = recipes
        self._catalog = catalog
        self._prefs = prefs
        self._locks = locks
        self._embedding_jobs = embedding_jobs

    def execute(self, command: CopyRecipeToKitchenCommand) -> CopiedRecipe:
        grant = AuthorizeKitchenAccessService(self._kitchens).execute(
            AuthorizeKitchenAccessCommand(
                acting_user_id=command.actor_id,
                kitchen_id=command.kitchen_id,
                action="read_kitchen",
            )
        )
        kitchen = self._kitchens.get_kitchen_with_grant(grant, command.kitchen_id)
        if kitchen.is_archived:
            raise KitchenArchivedError()

        names = self._readable_personal_source(command)

        alias, language = _naming_profile(self._prefs, command.actor_id)
        # Takes the kitchen lock, so two adds of the same recipe run one after the other.
        notebook_id, _ = ensure_member_kitchen_notebook(
            kitchen,
            command.actor_id,
            alias,
            language,
            notebooks=self._notebooks,
            catalog=self._catalog,
        )

        existing = self._recipes.latest_copy_in_kitchen(command.source_recipe_id, kitchen.id)
        if existing is not None and command.on_repeat == "ask":
            raise RecipeAlreadyInKitchenError(existing.recipe_id, existing.notebook_name)

        if existing is not None and command.on_repeat == "overwrite":
            if not self._locks.lock_recipe_row(existing.recipe_id):
                raise RecipeNotFoundError()
            holder = self._locks.recipe_holder(existing.recipe_id)
            if holder is not None:
                raise RecipeLockedError(holder.alias)
            if not self._recipes.overwrite_from(
                existing.recipe_id, command.source_recipe_id, command.actor_id
            ):
                raise RecipeNotFoundError()
            self._catalog.add_names(existing.notebook_id, names)
            self._enqueue(existing.recipe_id)
            logger.info("recipe copy outcome=overwritten")
            return CopiedRecipe(
                recipe_id=existing.recipe_id,
                notebook_id=existing.notebook_id,
                notebook_name=existing.notebook_name,
                overwritten=True,
            )

        recipe_id = self._recipes.copy_one(command.source_recipe_id, notebook_id, command.actor_id)
        if recipe_id is None:
            raise RecipeNotFoundError()
        self._catalog.add_names(notebook_id, names)
        self._enqueue(recipe_id)
        facts = self._notebooks.facts_for(command.actor_id, notebook_id)
        assert facts is not None
        logger.info("recipe copy outcome=created")
        return CopiedRecipe(
            recipe_id=recipe_id,
            notebook_id=notebook_id,
            notebook_name=facts.notebook.name,
            overwritten=False,
        )

    def _readable_personal_source(self, command: CopyRecipeToKitchenCommand) -> list[str]:
        """The source's distinct line names, if it sits in a personal notebook the caller owns or
        is a member of; otherwise the same 404 as a missing recipe (FR-008)."""
        detail = self._recipes.get_detail(command.source_recipe_id)
        if detail is None:
            raise RecipeNotFoundError()
        facts = self._notebooks.facts_for(command.actor_id, detail.notebook_id)
        if facts is None or facts.notebook.kind != "personal" or facts.role is None:
            raise RecipeNotFoundError()
        return list(dict.fromkeys(line.name for line in detail.lines))

    def _enqueue(self, recipe_id: UUID) -> None:
        if self._embedding_jobs is not None:
            # Written in this transaction; the worker embeds it after commit (spec 019 FR-006).
            self._embedding_jobs.enqueue([recipe_id])
