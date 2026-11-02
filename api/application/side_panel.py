"""The side panel's data: the default kitchen and the recipe count (spec 064).

The default is resolved on read and stored when it changes, so a fallback stays the default
even after the old kitchen is restored (research R2). A non-member gets KitchenNotFoundError (404).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from domain.default_kitchen import resolve_default_kitchen
from domain.errors import KitchenArchivedError, KitchenNotFoundError

from application.ports import SidePanelRepository


@dataclass(frozen=True, slots=True)
class SidePanelView:
    default_kitchen_id: UUID | None
    recipes_added: int
    notebooks: int
    # The caller's own flag, set on the server by the owner (spec 055 FR-017a).
    is_admin: bool = False


def _view(repo: SidePanelRepository, user_id: UUID, kitchen_id: UUID | None) -> SidePanelView:
    return SidePanelView(
        kitchen_id,
        repo.count_recipes_added(user_id),
        repo.count_notebooks(user_id),
        repo.is_admin(user_id),
    )


class GetSidePanelService:
    def __init__(self, repo: SidePanelRepository) -> None:
        self._repo = repo

    def execute(self, user_id: UUID) -> SidePanelView:
        stored = self._repo.stored_default_kitchen(user_id)
        resolved = resolve_default_kitchen(stored, self._repo.member_kitchens(user_id))
        if resolved != stored:
            self._repo.set_default_kitchen(user_id, resolved)
        return _view(self._repo, user_id, resolved)


class SetDefaultKitchenService:
    def __init__(self, repo: SidePanelRepository) -> None:
        self._repo = repo

    def execute(self, user_id: UUID, kitchen_id: UUID) -> SidePanelView:
        kitchen = next((k for k in self._repo.member_kitchens(user_id) if k.id == kitchen_id), None)
        if kitchen is None:
            raise KitchenNotFoundError()
        if kitchen.is_archived:
            raise KitchenArchivedError()
        self._repo.set_default_kitchen(user_id, kitchen_id)
        return _view(self._repo, user_id, kitchen_id)
