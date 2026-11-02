"""Renaming, deleting and adding notebooks against fake ports (spec 059)."""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from application.notebooks import (
    CreateKitchenNotebookCommand,
    CreateKitchenNotebookService,
    DeleteNotebookCommand,
    DeleteNotebookService,
    NotebookView,
    RenameNotebookCommand,
    RenameNotebookService,
)
from domain.errors import (
    InvalidNotebookNameError,
    KitchenArchivedError,
    KitchenNotFoundError,
    NotebookNotFoundError,
    NotebookOwnerOnlyError,
)
from domain.notebook import Notebook
from tests.test_notebooks_application import World, _join, _kitchen, _personal, _world

ANA, BEN, CARL = uuid4(), uuid4(), uuid4()


@pytest.fixture
def world() -> World:
    return _world({ANA: "ana", BEN: "ben", CARL: "carl"})


def _rename(world: World, notebook_id: UUID, name: str, actor: UUID = ANA) -> NotebookView:
    return RenameNotebookService(world.notebooks, world.committer).execute(
        RenameNotebookCommand(actor_user_id=actor, notebook_id=notebook_id, name=name)
    )


def _delete(world: World, notebook_id: UUID, actor: UUID = ANA) -> None:
    DeleteNotebookService(world.notebooks, world.committer).execute(
        DeleteNotebookCommand(actor_user_id=actor, notebook_id=notebook_id)
    )


def _add(world: World, kitchen_id: UUID, name: str, actor: UUID = ANA) -> NotebookView:
    return CreateKitchenNotebookService(
        world.kitchens, world.notebooks, world.catalog, world.committer
    ).execute(CreateKitchenNotebookCommand(actor_user_id=actor, kitchen_id=kitchen_id, name=name))


def _in_kitchen(world: World, kitchen_id: UUID, name: str = "Home notebook") -> UUID:
    notebook = Notebook(id=uuid4(), name=name, kitchen_id=kitchen_id, owner_user_id=ANA)
    world.notebooks.create(notebook)
    world.notebooks.calls.clear()
    return notebook.id


def _archive(world: World, kitchen_id: UUID) -> None:
    kitchens = world.kitchens.kitchens
    kitchens[kitchen_id] = replace(kitchens[kitchen_id], is_archived=True)


# --- The checks both actions share (research R2) ----------------------------------------------


def test_a_kitchen_notebook_locks_the_kitchen_then_the_notebook(world: World) -> None:
    notebook = _in_kitchen(world, _kitchen(world, ANA))

    _rename(world, notebook, "Weeknight")

    assert world.notebooks.calls == ["lock_kitchen", "lock_notebook", "rename"]


def test_a_personal_notebook_locks_only_the_notebook(world: World) -> None:
    notebook = _personal(world, ANA, "Soups")
    world.notebooks.calls.clear()

    _rename(world, notebook, "Winter soups")

    assert world.notebooks.calls == ["lock_notebook", "rename"]


def test_an_outsider_takes_no_lock(world: World) -> None:
    notebook = _personal(world, BEN, "Soups")
    world.notebooks.calls.clear()

    with pytest.raises(NotebookNotFoundError):
        _rename(world, notebook, "Mine now")

    assert world.notebooks.calls == []


def test_a_missing_notebook_is_not_found(world: World) -> None:
    with pytest.raises(NotebookNotFoundError):
        _delete(world, uuid4())


def test_a_kitchen_gone_at_the_lock_reads_as_the_notebook_gone(world: World) -> None:
    home = _kitchen(world, ANA)
    notebook = _in_kitchen(world, home)

    def kitchen_deleted_first(_: UUID) -> None:
        raise KitchenNotFoundError()

    world.notebooks.on_kitchen_lock = kitchen_deleted_first

    with pytest.raises(NotebookNotFoundError):
        _rename(world, notebook, "Weeknight")

    assert "rename" not in world.notebooks.calls


def test_a_notebook_gone_at_the_lock_is_not_found(world: World) -> None:
    notebook = _personal(world, ANA, "Soups")

    def deleted_first(notebook_id: UUID) -> None:
        del world.notebooks.notebooks[notebook_id]
        raise NotebookNotFoundError()

    world.notebooks.on_notebook_lock = deleted_first

    with pytest.raises(NotebookNotFoundError):
        _delete(world, notebook)

    assert "delete" not in world.notebooks.calls


def test_a_kitchen_archived_while_waiting_is_seen_under_the_lock(world: World) -> None:
    home = _kitchen(world, ANA)
    notebook = _in_kitchen(world, home)
    world.notebooks.on_kitchen_lock = lambda kitchen_id: _archive(world, kitchen_id)

    with pytest.raises(KitchenArchivedError):
        _delete(world, notebook)

    assert notebook in world.notebooks.notebooks


def test_leaving_a_kitchen_while_waiting_ends_access(world: World) -> None:
    home = _kitchen(world, ANA)
    _join(world, home, BEN)
    notebook = _in_kitchen(world, home)

    def ben_left(_: UUID) -> None:
        world.kitchens.memberships = [m for m in world.kitchens.memberships if m.user_id != BEN]

    world.notebooks.on_notebook_lock = ben_left

    with pytest.raises(NotebookNotFoundError):
        _rename(world, notebook, "Weeknight", actor=BEN)

    assert world.notebooks.notebooks[notebook].name == "Home notebook"


def test_ownership_passing_while_waiting_refuses_the_old_owner(world: World) -> None:
    notebook = _personal(world, ANA, "Soups")

    def passed_on(notebook_id: UUID) -> None:
        world.notebooks.roles[(notebook_id, ANA)] = "member"

    world.notebooks.on_notebook_lock = passed_on

    with pytest.raises(NotebookOwnerOnlyError):
        _delete(world, notebook)

    assert notebook in world.notebooks.notebooks


# --- Rename ------------------------------------------------------------------------------------


def test_rename_trims_stores_and_commits_once(world: World) -> None:
    notebook = _personal(world, ANA, "Soups")

    view = _rename(world, notebook, "  Winter soups  ")

    assert view.name == "Winter soups"
    assert world.notebooks.notebooks[notebook].name == "Winter soups"
    assert world.committer.commits == 1


@pytest.mark.parametrize("name", ["Soups", "  Soups "])
def test_the_same_name_changes_nothing(world: World, name: str) -> None:
    notebook = _personal(world, ANA, "Soups")
    world.notebooks.calls.clear()

    view = _rename(world, notebook, name)

    assert view.name == "Soups"
    assert "rename" not in world.notebooks.calls
    assert world.committer.commits == 0


def test_a_stored_name_over_the_limit_can_be_saved_unchanged(world: World) -> None:
    long_name = "n" * 240
    notebook = _personal(world, ANA, long_name)

    assert _rename(world, notebook, long_name).name == long_name
    assert world.committer.commits == 0


@pytest.mark.parametrize("name", ["", "   ", "x" * 201])
def test_a_bad_name_is_refused_and_changes_nothing(world: World, name: str) -> None:
    notebook = _personal(world, ANA, "Soups")

    with pytest.raises(InvalidNotebookNameError):
        _rename(world, notebook, name)

    assert world.notebooks.notebooks[notebook].name == "Soups"
    assert world.committer.commits == 0


def test_two_hundred_characters_pass(world: World) -> None:
    notebook = _personal(world, ANA, "Soups")

    assert _rename(world, notebook, "x" * 200).name == "x" * 200


def test_refusals_come_before_the_name_is_checked(world: World) -> None:
    shared = _personal(world, ANA, "Soups")
    world.notebooks.roles[(shared, BEN)] = "member"
    home = _kitchen(world, ANA, archived=True)
    archived = _in_kitchen(world, home)

    with pytest.raises(NotebookOwnerOnlyError):
        _rename(world, shared, "", actor=BEN)
    with pytest.raises(NotebookNotFoundError):
        _rename(world, shared, "", actor=CARL)
    with pytest.raises(KitchenArchivedError):
        _rename(world, archived, "")


# --- Delete ------------------------------------------------------------------------------------


def test_delete_runs_after_the_checks_and_commits_once(world: World) -> None:
    notebook = _in_kitchen(world, _kitchen(world, ANA))

    _delete(world, notebook)

    assert world.notebooks.calls == ["lock_kitchen", "lock_notebook", "delete"]
    assert world.committer.commits == 1
    assert notebook not in world.notebooks.notebooks


def test_a_refused_delete_neither_deletes_nor_commits(world: World) -> None:
    shared = _personal(world, ANA, "Soups")
    world.notebooks.roles[(shared, BEN)] = "member"
    archived = _in_kitchen(world, _kitchen(world, ANA, archived=True))

    with pytest.raises(NotebookOwnerOnlyError):
        _delete(world, shared, actor=BEN)
    with pytest.raises(NotebookNotFoundError):
        _delete(world, shared, actor=CARL)
    with pytest.raises(KitchenArchivedError):
        _delete(world, archived)

    assert "delete" not in world.notebooks.calls
    assert world.committer.commits == 0


# --- Add an empty kitchen notebook (research R11) ---------------------------------------------


def test_a_non_member_learns_nothing_even_with_a_bad_name(world: World) -> None:
    home = _kitchen(world, BEN)

    with pytest.raises(KitchenNotFoundError):
        _add(world, home, "")

    assert world.notebooks.calls == []


def test_a_missing_kitchen_reads_the_same(world: World) -> None:
    with pytest.raises(KitchenNotFoundError):
        _add(world, uuid4(), "Holidays")


def test_a_kitchen_archived_while_waiting_gets_no_notebook(world: World) -> None:
    home = _kitchen(world, ANA)
    world.notebooks.on_kitchen_lock = lambda kitchen_id: _archive(world, kitchen_id)

    with pytest.raises(KitchenArchivedError):
        _add(world, home, "Holidays")

    assert "create" not in world.notebooks.calls


def test_leaving_the_kitchen_while_waiting_reads_as_not_found(world: World) -> None:
    home = _kitchen(world, ANA)
    _join(world, home, BEN)

    def ben_left(_: UUID) -> None:
        world.kitchens.memberships = [m for m in world.kitchens.memberships if m.user_id != BEN]

    world.notebooks.on_kitchen_lock = ben_left

    with pytest.raises(KitchenNotFoundError):
        _add(world, home, "Holidays", actor=BEN)

    assert "create" not in world.notebooks.calls


@pytest.mark.parametrize("name", ["", "   ", "x" * 201])
def test_a_bad_name_creates_nothing(world: World, name: str) -> None:
    home = _kitchen(world, ANA)

    with pytest.raises(InvalidNotebookNameError):
        _add(world, home, name)

    assert "create" not in world.notebooks.calls
    assert world.committer.commits == 0


def test_the_new_notebook_is_the_callers_with_their_catalog(world: World) -> None:
    home = _kitchen(world, ANA)
    _join(world, home, BEN)
    _personal(world, BEN, "Ben's", names={"salt", "onion"})
    world.notebooks.calls.clear()

    view = _add(world, home, "  Holidays ", actor=BEN)

    stored = world.notebooks.notebooks[view.id]
    assert view.name == "Holidays"
    assert view.access == "kitchen_member"
    assert stored.kitchen_id == home
    assert stored.owner_user_id == BEN
    assert stored.snapshot_key is None
    assert world.catalog.names[view.id] == {"salt", "onion"}
    assert world.notebooks.calls.index("lock_kitchen") < world.notebooks.calls.index("create")
    assert world.committer.commits == 1
