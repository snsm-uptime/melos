"""Settling the personal notebooks of a person whose account is being deleted (spec 058).

Each notebook passes to its longest-standing member, or is deleted when it has none. Account
deletion (S-054) calls this first and deletes the user row after it, in one transaction, so this
service never commits: see specs/058-notebook-ownership-passing/contracts/ownership-rule.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from domain.errors import NotebookNotFoundError
from domain.notebook import JoinedMember, longest_standing

from application.ports import NotebookRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PassOwnedNotebooksCommand:
    user_id: UUID


@dataclass(frozen=True, slots=True)
class PassedNotebook:
    notebook_id: UUID
    new_owner_id: UUID


@dataclass(frozen=True, slots=True)
class PassOwnedNotebooksResult:
    passed: list[PassedNotebook] = field(default_factory=list)
    deleted: list[UUID] = field(default_factory=list)


class PassOwnedNotebooksService:
    def __init__(self, notebooks: NotebookRepository) -> None:
        self._notebooks = notebooks

    def execute(self, command: PassOwnedNotebooksCommand) -> PassOwnedNotebooksResult:
        result = PassOwnedNotebooksResult()
        # Sorted, so two deletions that overlap can't deadlock on each other's notebooks.
        for notebook_id in sorted(self._notebooks.owned_personal_ids(command.user_id)):
            try:
                self._notebooks.lock_notebook(notebook_id)
            except NotebookNotFoundError:
                continue
            # Read again under the lock, which also makes a repeated run harmless.
            if self._notebooks.role_of(notebook_id, command.user_id) != "owner":
                continue
            heir = longest_standing(
                JoinedMember(user_id=row.user_id, role=row.role, joined_at=row.joined_at)
                for row in self._notebooks.members_of(notebook_id)
            )
            if heir is None:
                self._notebooks.delete(notebook_id)
                result.deleted.append(notebook_id)
                logger.info("notebook_deleted_with_owner notebook_id=%s", notebook_id)
                continue
            # The old owner first: the one-owner index refuses the other order.
            self._notebooks.delete_membership(notebook_id, command.user_id)
            self._notebooks.make_owner(notebook_id, heir)
            result.passed.append(PassedNotebook(notebook_id=notebook_id, new_owner_id=heir))
            logger.info("notebook_passed notebook_id=%s new_owner_id=%s", notebook_id, heir)
        return result
