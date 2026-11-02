"""Who is in a personal notebook: the list, leaving and removal (spec 057 User Story 3).

Leaving and removal delete the membership, and its foreign key ends the person's edit locks
(FR-026). Recipes and catalog names stay. No email goes out (FR-028).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from domain.errors import NotebookMemberNotFoundError, NotebookOwnerStaysError
from domain.notebook import NotebookRole
from domain.notebook_invite import assert_can_manage_sharing, assert_shareable

from application.notebook_invites import visible_notebook
from application.ports import NotebookRepository


@dataclass(frozen=True, slots=True)
class NotebookMemberView:
    user_id: UUID
    alias: str | None
    role: NotebookRole
    is_self: bool


@dataclass(frozen=True, slots=True)
class ListNotebookMembersCommand:
    actor_user_id: UUID
    notebook_id: UUID


class ListNotebookMembersService:
    """The owner and members see each other by alias, with no emails (FR-021)."""

    def __init__(self, notebooks: NotebookRepository) -> None:
        self._notebooks = notebooks

    def execute(self, command: ListNotebookMembersCommand) -> list[NotebookMemberView]:
        notebook, _ = visible_notebook(self._notebooks, command.actor_user_id, command.notebook_id)
        assert_shareable(notebook.kind)
        return [
            NotebookMemberView(
                user_id=row.user_id,
                alias=row.alias,
                role=row.role,
                is_self=row.user_id == command.actor_user_id,
            )
            for row in self._notebooks.members_of(notebook.id)
        ]


@dataclass(frozen=True, slots=True)
class LeaveNotebookCommand:
    actor_user_id: UUID
    notebook_id: UUID


class LeaveNotebookService:
    def __init__(self, notebooks: NotebookRepository) -> None:
        self._notebooks = notebooks

    def execute(self, command: LeaveNotebookCommand) -> None:
        notebook, access = visible_notebook(
            self._notebooks, command.actor_user_id, command.notebook_id
        )
        assert_shareable(notebook.kind)
        if access == "owner":
            raise NotebookOwnerStaysError()
        self._notebooks.delete_membership(notebook.id, command.actor_user_id)


@dataclass(frozen=True, slots=True)
class RemoveNotebookMemberCommand:
    actor_user_id: UUID
    notebook_id: UUID
    user_id: UUID


class RemoveNotebookMemberService:
    def __init__(self, notebooks: NotebookRepository) -> None:
        self._notebooks = notebooks

    def execute(self, command: RemoveNotebookMemberCommand) -> None:
        notebook, access = visible_notebook(
            self._notebooks, command.actor_user_id, command.notebook_id
        )
        assert_can_manage_sharing(notebook.kind, access)
        self._notebooks.lock_notebook(notebook.id)
        role = self._notebooks.role_of(notebook.id, command.user_id)
        if role == "owner":
            raise NotebookOwnerStaysError()
        if role is None:
            raise NotebookMemberNotFoundError()
        self._notebooks.delete_membership(notebook.id, command.user_id)
