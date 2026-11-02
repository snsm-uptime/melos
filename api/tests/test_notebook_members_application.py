"""Notebook member use cases against fake ports (spec 057 User Story 3)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from application.notebook_members import (
    LeaveNotebookCommand,
    LeaveNotebookService,
    ListNotebookMembersCommand,
    ListNotebookMembersService,
    RemoveNotebookMemberCommand,
    RemoveNotebookMemberService,
)
from domain.errors import (
    NotebookMemberNotFoundError,
    NotebookNotFoundError,
    NotebookNotShareableError,
    NotebookOwnerOnlyError,
    NotebookOwnerStaysError,
)
from tests.notebook_sharing_fakes import FakeNotebooks

OWNER, MEMBER, OTHER = uuid4(), uuid4(), uuid4()


@pytest.fixture
def notebooks() -> FakeNotebooks:
    repo = FakeNotebooks(aliases={OWNER: "ana", MEMBER: "ben", OTHER: None})
    repo.personal_id = repo.personal(OWNER)  # type: ignore[attr-defined]
    repo.roles[(repo.personal_id, MEMBER)] = "member"  # type: ignore[attr-defined]
    return repo


def _list(repo: FakeNotebooks, actor):
    return ListNotebookMembersService(repo).execute(
        ListNotebookMembersCommand(actor_user_id=actor, notebook_id=repo.personal_id)  # type: ignore[attr-defined]
    )


def _leave(repo: FakeNotebooks, actor) -> None:
    LeaveNotebookService(repo).execute(
        LeaveNotebookCommand(actor_user_id=actor, notebook_id=repo.personal_id)  # type: ignore[attr-defined]
    )


def _remove(repo: FakeNotebooks, actor, target) -> None:
    RemoveNotebookMemberService(repo).execute(
        RemoveNotebookMemberCommand(
            actor_user_id=actor,
            notebook_id=repo.personal_id,  # type: ignore[attr-defined]
            user_id=target,
        )
    )


@pytest.mark.parametrize("actor", [OWNER, MEMBER])
def test_owner_and_member_see_owner_first_and_themselves_marked(
    notebooks: FakeNotebooks, actor
) -> None:
    rows = _list(notebooks, actor)
    assert [(row.alias, row.role) for row in rows] == [("ana", "owner"), ("ben", "member")]
    assert [row.is_self for row in rows] == [actor == OWNER, actor == MEMBER]


def test_stranger_cannot_list(notebooks: FakeNotebooks) -> None:
    with pytest.raises(NotebookNotFoundError):
        _list(notebooks, OTHER)


def test_member_leaves(notebooks: FakeNotebooks) -> None:
    _leave(notebooks, MEMBER)
    assert notebooks.role_of(notebooks.personal_id, MEMBER) is None  # type: ignore[attr-defined]


def test_member_leaves_under_the_lock(notebooks: FakeNotebooks) -> None:
    _leave(notebooks, MEMBER)
    assert notebooks.log == ["lock", "delete_membership"]


def test_a_member_who_became_owner_while_waiting_for_the_lock_stays(
    notebooks: FakeNotebooks,
) -> None:
    def promoted(notebook_id) -> None:  # noqa: ANN001
        del notebooks.roles[(notebook_id, OWNER)]
        notebooks.roles[(notebook_id, MEMBER)] = "owner"

    notebooks.on_lock = promoted
    with pytest.raises(NotebookOwnerStaysError):
        _leave(notebooks, MEMBER)
    assert notebooks.role_of(notebooks.personal_id, MEMBER) == "owner"  # type: ignore[attr-defined]
    assert "delete_membership" not in notebooks.log


def test_a_member_removed_while_waiting_for_the_lock_gets_not_found(
    notebooks: FakeNotebooks,
) -> None:
    notebooks.on_lock = lambda notebook_id: notebooks.roles.pop((notebook_id, MEMBER))
    with pytest.raises(NotebookNotFoundError):
        _leave(notebooks, MEMBER)


def test_owner_cannot_leave(notebooks: FakeNotebooks) -> None:
    with pytest.raises(NotebookOwnerStaysError):
        _leave(notebooks, OWNER)
    assert notebooks.role_of(notebooks.personal_id, OWNER) == "owner"  # type: ignore[attr-defined]


def test_stranger_cannot_leave(notebooks: FakeNotebooks) -> None:
    with pytest.raises(NotebookNotFoundError):
        _leave(notebooks, OTHER)


def test_owner_removes_a_member_under_the_lock(notebooks: FakeNotebooks) -> None:
    _remove(notebooks, OWNER, MEMBER)
    assert notebooks.log == ["lock", "delete_membership"]
    assert notebooks.role_of(notebooks.personal_id, MEMBER) is None  # type: ignore[attr-defined]


def test_member_cannot_remove(notebooks: FakeNotebooks) -> None:
    with pytest.raises(NotebookOwnerOnlyError):
        _remove(notebooks, MEMBER, OWNER)
    assert notebooks.log == []


def test_owner_cannot_be_removed(notebooks: FakeNotebooks) -> None:
    with pytest.raises(NotebookOwnerStaysError):
        _remove(notebooks, OWNER, OWNER)


def test_missing_target(notebooks: FakeNotebooks) -> None:
    with pytest.raises(NotebookMemberNotFoundError):
        _remove(notebooks, OWNER, OTHER)


def test_kitchen_notebook_is_refused_everywhere(notebooks: FakeNotebooks) -> None:
    notebooks.personal_id = notebooks.kitchen(OWNER)  # type: ignore[attr-defined]
    with pytest.raises(NotebookNotShareableError):
        _list(notebooks, OWNER)
    with pytest.raises(NotebookNotShareableError):
        _leave(notebooks, OWNER)
    with pytest.raises(NotebookNotShareableError):
        _remove(notebooks, OWNER, MEMBER)
