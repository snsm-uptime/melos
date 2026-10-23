"""Notebook reads for kitchens and members, and the member's default notebook (spec 055)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from domain.errors import AliasRequiredError, NotebookNotFoundError
from domain.notebook import Notebook, default_notebook_name

from application.kitchen_access import (
    AuthorizeKitchenAccessCommand,
    AuthorizeKitchenAccessService,
)
from application.kitchens import KitchenRepository
from application.ports import NotebookRepository, PreferencesRepository, UserDefaultNotebook


@dataclass(frozen=True, slots=True)
class GetKitchenNotebookCommand:
    actor_user_id: UUID
    kitchen_id: UUID


@dataclass(frozen=True, slots=True)
class KitchenNotebookView:
    notebook: Notebook
    kitchen_name: str
    is_archived: bool


@dataclass(frozen=True, slots=True)
class GetDefaultNotebookCommand:
    actor_user_id: UUID
    user_id: UUID


@dataclass(frozen=True, slots=True)
class GetMemberNotebookCommand:
    actor_user_id: UUID
    user_id: UUID
    notebook_id: UUID


class GetKitchenNotebookService:
    """Kitchen notebook for any member — authorize_kitchen_access(read_kitchen) → 404."""

    def __init__(self, kitchens: KitchenRepository, notebooks: NotebookRepository) -> None:
        self._kitchens = kitchens
        self._notebooks = notebooks

    def execute(self, command: GetKitchenNotebookCommand) -> KitchenNotebookView:
        grant = AuthorizeKitchenAccessService(self._kitchens).execute(
            AuthorizeKitchenAccessCommand(
                acting_user_id=command.actor_user_id,
                kitchen_id=command.kitchen_id,
                action="read_kitchen",
            )
        )
        kitchen = self._kitchens.get_kitchen_with_grant(grant, command.kitchen_id)
        notebook = self._notebooks.for_kitchen(kitchen.id)
        if notebook is None:
            # The personal kitchen made at signup has no notebook, because signup
            # is not changed (FR-009). It gets one on its first read.
            self._notebooks.create(Notebook(id=uuid4(), kitchen_id=kitchen.id))
            notebook = self._notebooks.for_kitchen(kitchen.id)
            assert notebook is not None
        return KitchenNotebookView(
            notebook=notebook, kitchen_name=kitchen.name, is_archived=kitchen.is_archived
        )


class GetDefaultNotebookService:
    """The member's default notebook, created silently when unset (FR-002, FR-010).

    Owner-only: any other caller gets NotebookNotFoundError.
    """

    def __init__(
        self,
        notebooks: NotebookRepository,
        defaults: UserDefaultNotebook,
        prefs: PreferencesRepository,
    ) -> None:
        self._notebooks = notebooks
        self._defaults = defaults
        self._prefs = prefs

    def execute(self, command: GetDefaultNotebookCommand) -> Notebook:
        if command.user_id != command.actor_user_id:
            raise NotebookNotFoundError()
        existing = self._notebooks.for_member(command.user_id)
        if existing is not None:
            return existing

        # Lock the user row and re-check: a simultaneous first call may have
        # set the default while this one was reading.
        current = self._defaults.get_for_update(command.user_id)
        if current is not None:
            notebook = self._notebooks.get(current)
            if notebook is not None:
                return notebook

        prefs = self._prefs.get_preferences(command.user_id)
        if prefs is None or not prefs.alias:
            raise AliasRequiredError()
        notebook = Notebook(
            id=uuid4(), user_id=command.user_id, name=default_notebook_name(prefs.alias)
        )
        self._notebooks.create(notebook)
        self._defaults.set(command.user_id, notebook.id)
        return notebook


class GetMemberNotebookService:
    """A member's notebook by id — owner-only; anything else is NotebookNotFoundError."""

    def __init__(self, notebooks: NotebookRepository) -> None:
        self._notebooks = notebooks

    def execute(self, command: GetMemberNotebookCommand) -> Notebook:
        if command.user_id != command.actor_user_id:
            raise NotebookNotFoundError()
        notebook = self._notebooks.get(command.notebook_id)
        if notebook is None or notebook.user_id != command.user_id:
            raise NotebookNotFoundError()
        return notebook
