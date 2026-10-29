"""One member edits a recipe at a time (spec 022 US4, contracts/recipe-lock-api.md).

The lock belongs to the editor's session and depends on the access that allowed it, so
sign-out, session end, 5 minutes without activity or lost access end it (research R8, R10,
R11). Spec 027's services stay the one place a recipe is edited or deleted; they call
`require_recipe_lock` and `refuse_if_locked_by_other`.
"""

from __future__ import annotations

import logging
from uuid import UUID

from domain.errors import (
    NotEditingError,
    RecipeLockedError,
    RecipeNotFoundError,
    RecipeReadOnlyError,
)

from application.carts import EditorView, editor_view
from application.ports import EditLockRepository, NotebookRepository, RecipeRepository, SessionRef

logger = logging.getLogger(__name__)


def recipe_editor(locks: EditLockRepository, recipe_id: UUID, ref: SessionRef) -> EditorView | None:
    return editor_view(locks.recipe_holder(recipe_id), ref)


class AcquireRecipeLockService:
    """Take the recipe lock, or for its holder keep it alive."""

    def __init__(
        self, recipes: RecipeRepository, notebooks: NotebookRepository, locks: EditLockRepository
    ) -> None:
        self._recipes = recipes
        self._notebooks = notebooks
        self._locks = locks

    def execute(self, ref: SessionRef, recipe_id: UUID) -> EditorView:
        # recipe_manage imports this module for the lock rules; import its access check here.
        from application.recipe_manage import _recipe_for

        _recipe_for(self._recipes, self._notebooks, ref.user_id, recipe_id, write=True)
        if not self._locks.lock_recipe_row(recipe_id):
            raise RecipeNotFoundError()
        holder = self._locks.recipe_holder(recipe_id)
        if holder is not None and holder.session_id != ref.session_id:
            raise RecipeLockedError(holder.alias)
        if holder is not None:
            self._locks.touch_recipe(recipe_id, ref.session_id)
        else:
            access = self._locks.recipe_lock_access(recipe_id, ref.user_id)
            if access is None:
                raise RecipeReadOnlyError()
            self._locks.take_recipe(recipe_id, ref, access)
            logger.info("recipe lock outcome=locked")
        editor = recipe_editor(self._locks, recipe_id, ref)
        assert editor is not None
        return editor


class ReleaseRecipeLockService:
    """Free the recipe if the caller's session holds it. Idempotent."""

    def __init__(self, locks: EditLockRepository) -> None:
        self._locks = locks

    def execute(self, ref: SessionRef, recipe_id: UUID) -> None:
        self._locks.release_recipe(recipe_id, ref.session_id)


def require_recipe_lock(
    locks: EditLockRepository, recipe_id: UUID, session_id: UUID | None
) -> None:
    """An edit needs the caller's live lock: another holder → RecipeLockedError, none →
    NotEditingError."""
    holder = locks.recipe_holder(recipe_id)
    if holder is None:
        raise NotEditingError()
    if holder.session_id != session_id:
        raise RecipeLockedError(holder.alias)


def refuse_if_locked_by_other(
    locks: EditLockRepository, recipe_id: UUID, session_id: UUID | None
) -> None:
    holder = locks.recipe_holder(recipe_id)
    if holder is not None and holder.session_id != session_id:
        raise RecipeLockedError(holder.alias)
