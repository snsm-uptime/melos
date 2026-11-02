"""Settling an owner's notebooks against fake ports (spec 058)."""

from __future__ import annotations

from uuid import uuid4

from application.notebook_ownership import (
    PassedNotebook,
    PassOwnedNotebooksCommand,
    PassOwnedNotebooksResult,
    PassOwnedNotebooksService,
)
from tests.notebook_sharing_fakes import FakeNotebooks

OWNER, BEN, CARLA = uuid4(), uuid4(), uuid4()


def _settle(repo: FakeNotebooks, user_id=OWNER) -> PassOwnedNotebooksResult:  # noqa: ANN001
    return PassOwnedNotebooksService(repo).execute(PassOwnedNotebooksCommand(user_id=user_id))


def _shared(repo: FakeNotebooks, *members) -> object:  # noqa: ANN002
    notebook_id = repo.personal(OWNER)
    for member in members:
        repo.roles[(notebook_id, member)] = "member"
    return notebook_id


def test_the_earliest_member_inherits_and_the_others_stay() -> None:
    repo = FakeNotebooks()
    notebook_id = _shared(repo, BEN, CARLA)

    result = _settle(repo)

    assert result.passed == [PassedNotebook(notebook_id=notebook_id, new_owner_id=BEN)]
    assert result.deleted == []
    assert repo.roles == {(notebook_id, BEN): "owner", (notebook_id, CARLA): "member"}


def test_the_old_owner_goes_before_the_new_one_comes() -> None:
    """The one-owner index refuses the other order (research R4); the fake asserts it too."""
    repo = FakeNotebooks()
    _shared(repo, BEN)
    _settle(repo)
    assert repo.log == ["lock", "delete_membership", "make_owner"]


def test_notebooks_lock_in_sorted_order() -> None:
    repo = FakeNotebooks()
    ids = [_shared(repo, BEN) for _ in range(4)]
    _settle(repo)
    assert repo.locked == sorted(ids)


def test_each_notebook_is_settled_on_its_own() -> None:
    repo = FakeNotebooks()
    to_ben = _shared(repo, BEN)
    to_carla = _shared(repo, CARLA)
    alone = _shared(repo)

    result = _settle(repo)

    assert sorted(result.passed, key=lambda row: str(row.notebook_id)) == sorted(
        [
            PassedNotebook(notebook_id=to_ben, new_owner_id=BEN),
            PassedNotebook(notebook_id=to_carla, new_owner_id=CARLA),
        ],
        key=lambda row: str(row.notebook_id),
    )
    assert result.deleted == [alone]


def test_a_notebook_no_longer_owned_once_the_lock_is_held_is_skipped() -> None:
    repo = FakeNotebooks()
    notebook_id = _shared(repo, BEN)

    def another_request_got_there_first(locked) -> None:  # noqa: ANN001
        del repo.roles[(locked, OWNER)]
        repo.roles[(locked, BEN)] = "owner"

    repo.on_lock = another_request_got_there_first

    assert _settle(repo) == PassOwnedNotebooksResult(passed=[], deleted=[])
    assert repo.roles == {(notebook_id, BEN): "owner"}
    assert repo.log == ["lock"]


def test_a_notebook_gone_before_the_lock_is_skipped() -> None:
    repo = FakeNotebooks()
    repo.owned_personal_ids = lambda _user: [uuid4()]  # type: ignore[method-assign]

    assert _settle(repo) == PassOwnedNotebooksResult(passed=[], deleted=[])


def test_a_second_run_changes_nothing() -> None:
    repo = FakeNotebooks()
    notebook_id = _shared(repo, BEN)
    _settle(repo)
    before = dict(repo.roles)

    assert _settle(repo) == PassOwnedNotebooksResult(passed=[], deleted=[])
    assert repo.roles == before
    assert (notebook_id, BEN) in repo.roles


def test_a_person_with_no_notebooks_gets_an_empty_result() -> None:
    repo = FakeNotebooks()
    assert _settle(repo) == PassOwnedNotebooksResult(passed=[], deleted=[])
    assert repo.log == []


def test_notebooks_the_person_is_only_a_member_of_are_left_alone() -> None:
    repo = FakeNotebooks()
    someone_elses = repo.personal(BEN)
    repo.roles[(someone_elses, OWNER)] = "member"
    assert _settle(repo) == PassOwnedNotebooksResult(passed=[], deleted=[])
    assert repo.roles[(someone_elses, BEN)] == "owner"


def test_a_notebook_with_no_members_is_deleted() -> None:
    repo = FakeNotebooks()
    notebook_id = _shared(repo)

    result = _settle(repo)

    assert result == PassOwnedNotebooksResult(passed=[], deleted=[notebook_id])
    assert repo.log == ["lock", "delete_personal"]
    assert notebook_id not in repo.notebooks
