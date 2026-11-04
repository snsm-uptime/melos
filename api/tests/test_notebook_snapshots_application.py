"""Adding a snapshot against fake ports, in contract order (spec 035)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from application.notebooks import (
    AddNotebookSnapshotCommand,
    AddNotebookSnapshotService,
    notebook_view,
)
from domain.errors import (
    KitchenArchivedError,
    KitchenNotFoundError,
    NotebookNotFoundError,
    SnapshotExistsError,
)
from domain.notebook import Notebook
from tests.embedding_fakes import FakeEmbeddingJobs
from tests.test_notebooks_application import World, _join, _kitchen, _personal, _world

ANA, BEN = uuid4(), uuid4()


@dataclass
class FakeRecipes:
    copies: list[tuple[UUID, UUID]] = field(default_factory=list)

    def copy_all(self, source_id: UUID, target_id: UUID) -> int:
        self.copies.append((source_id, target_id))
        return 3


@pytest.fixture
def world() -> World:
    return _world({ANA: "ana", BEN: "ben"})


def _add(
    world: World,
    kitchen_id: UUID,
    source_id: UUID,
    *,
    actor: UUID = ANA,
    key: UUID | None = None,
    confirm: bool = False,
    recipes: FakeRecipes | None = None,
    jobs: FakeEmbeddingJobs | None = None,
):
    service = AddNotebookSnapshotService(
        world.kitchens,
        world.notebooks,
        world.catalog,
        recipes or FakeRecipes(),
        embedding_jobs=jobs,
    )
    return service.execute(
        AddNotebookSnapshotCommand(
            actor_user_id=actor,
            kitchen_id=kitchen_id,
            source_notebook_id=source_id,
            snapshot_key=key or uuid4(),
            confirm_repeat=confirm,
        )
    )


def _kitchen_rows(world: World, kitchen_id: UUID) -> list[Notebook]:
    return [n for n in world.notebooks.notebooks.values() if n.kitchen_id == kitchen_id]


def test_check_1_a_non_member_is_told_the_kitchen_is_not_found(world: World) -> None:
    kitchen = _kitchen(world, BEN)
    source = _personal(world, ANA, "ana's Notebook")

    with pytest.raises(KitchenNotFoundError):
        _add(world, kitchen, source)

    assert _kitchen_rows(world, kitchen) == []


def test_check_1_a_missing_kitchen_reads_the_same(world: World) -> None:
    with pytest.raises(KitchenNotFoundError):
        _add(world, uuid4(), _personal(world, ANA, "ana's Notebook"))


def test_check_2_an_archived_kitchen_refuses_before_the_key_is_read(world: World) -> None:
    kitchen = _kitchen(world, ANA, archived=True)
    source = _personal(world, ANA, "ana's Notebook")

    with pytest.raises(KitchenArchivedError):
        _add(world, kitchen, source)

    assert "find_snapshot" not in world.notebooks.calls
    assert _kitchen_rows(world, kitchen) == []


def test_check_3_a_used_key_returns_the_snapshot_and_copies_nothing(world: World) -> None:
    kitchen = _kitchen(world, ANA)
    source = _personal(world, ANA, "ana's Notebook")
    key = uuid4()
    recipes = FakeRecipes()
    first = _add(world, kitchen, source, key=key, recipes=recipes)

    second = _add(world, kitchen, source, key=key, recipes=recipes)

    assert first.created is True
    assert second.created is False
    assert second.notebook.id == first.notebook.id
    assert len(recipes.copies) == 1


def test_check_3_runs_before_the_source_and_repeat_checks(world: World) -> None:
    kitchen = _kitchen(world, ANA)
    source = _personal(world, ANA, "ana's Notebook")
    key = uuid4()
    first = _add(world, kitchen, source, key=key)

    # The source is gone and no confirmation is sent: the key alone answers.
    replay = _add(world, kitchen, uuid4(), key=key)

    assert replay.notebook.id == first.notebook.id


def test_check_3_runs_under_the_kitchen_lock(world: World) -> None:
    kitchen = _kitchen(world, ANA)
    _add(world, kitchen, _personal(world, ANA, "ana's Notebook"))

    calls = world.notebooks.calls
    assert calls.index("lock_kitchen") < calls.index("find_snapshot")


@pytest.mark.parametrize("case", ["missing", "someone_else", "member_only", "kitchen_notebook"])
def test_check_4_only_a_personal_notebook_the_caller_owns_is_accepted(
    world: World, case: str
) -> None:
    kitchen = _kitchen(world, ANA)
    _join(world, kitchen, BEN)
    if case == "missing":
        source = uuid4()
    elif case == "someone_else":
        source = _personal(world, BEN, "ben's Notebook")
    elif case == "member_only":
        source = _personal(world, BEN, "Shared")
        world.notebooks.roles[(source, ANA)] = "member"
    else:
        other = _kitchen(world, ANA, "Other")
        source = uuid4()
        world.notebooks.create(Notebook(id=source, name="Kitchen notebook", kitchen_id=other))

    with pytest.raises(NotebookNotFoundError):
        _add(world, kitchen, source)

    assert _kitchen_rows(world, kitchen) == []


def test_check_4_runs_again_under_the_source_lock(world: World) -> None:
    kitchen = _kitchen(world, ANA)
    source = _personal(world, ANA, "ana's Notebook")

    _add(world, kitchen, source)

    calls = world.notebooks.calls
    assert calls.index("lock_kitchen") < calls.index("lock_notebook")
    assert calls.index("lock_notebook") < calls.index("has_snapshot_of")


def test_check_4_an_original_deleted_while_waiting_is_not_found(world: World) -> None:
    kitchen = _kitchen(world, ANA)
    source = _personal(world, ANA, "ana's Notebook")

    def deleted_first(notebook_id: UUID) -> None:
        del world.notebooks.notebooks[notebook_id]

    world.notebooks.on_notebook_lock = deleted_first

    with pytest.raises(NotebookNotFoundError):
        _add(world, kitchen, source)

    assert _kitchen_rows(world, kitchen) == []


def test_check_4_an_original_no_longer_owned_once_locked_is_not_found(world: World) -> None:
    kitchen = _kitchen(world, ANA)
    source = _personal(world, ANA, "ana's Notebook")

    def passed_on(notebook_id: UUID) -> None:
        world.notebooks.roles[(notebook_id, ANA)] = "member"

    world.notebooks.on_notebook_lock = passed_on

    with pytest.raises(NotebookNotFoundError):
        _add(world, kitchen, source)

    assert _kitchen_rows(world, kitchen) == []


def test_check_5_a_repeat_needs_a_confirmation(world: World) -> None:
    kitchen = _kitchen(world, ANA)
    source = _personal(world, ANA, "ana's Notebook")
    _add(world, kitchen, source)

    with pytest.raises(SnapshotExistsError):
        _add(world, kitchen, source)

    assert len(_kitchen_rows(world, kitchen)) == 1


def test_check_5_a_snapshot_in_another_kitchen_needs_no_confirmation(world: World) -> None:
    source = _personal(world, ANA, "ana's Notebook")
    _add(world, _kitchen(world, ANA, "Home"), source)

    assert _add(world, _kitchen(world, ANA, "Cabin"), source).created is True


def test_check_6_a_confirmed_repeat_makes_a_second_snapshot(world: World) -> None:
    kitchen = _kitchen(world, ANA)
    source = _personal(world, ANA, "ana's Notebook")
    first = _add(world, kitchen, source)

    second = _add(world, kitchen, source, confirm=True)

    assert second.created is True
    assert second.notebook.id != first.notebook.id


def test_check_6_makes_a_labelled_kitchen_notebook_with_the_original_name(world: World) -> None:
    kitchen = _kitchen(world, BEN)
    _join(world, kitchen, ANA)
    source = _personal(world, ANA, "Cuaderno de ana", {"onion", "unused"})
    key = uuid4()
    recipes = FakeRecipes()

    added = _add(world, kitchen, source, key=key, recipes=recipes)

    made = world.notebooks.notebooks[added.notebook.id]
    assert made.name == "Cuaderno de ana"
    assert made.kitchen_id == kitchen
    assert made.owner_user_id == ANA
    assert made.source_notebook_id == source
    assert made.snapshot_key == key
    assert world.catalog.names[made.id] == {"onion", "unused"}
    assert recipes.copies == [(source, made.id)]
    assert (made.id, ANA) not in world.notebooks.roles


def test_a_member_of_any_role_may_add(world: World) -> None:
    kitchen = _kitchen(world, BEN)
    _join(world, kitchen, ANA)

    assert _add(world, kitchen, _personal(world, ANA, "ana's Notebook")).created is True


def test_a_failed_copy_reaches_the_caller_so_the_request_rolls_back(world: World) -> None:
    class Failing(FakeRecipes):
        def copy_all(self, source_id: UUID, target_id: UUID) -> int:
            raise RuntimeError("boom")

    kitchen = _kitchen(world, ANA)

    with pytest.raises(RuntimeError):
        _add(world, kitchen, _personal(world, ANA, "x"), recipes=Failing())


def test_the_view_reports_a_snapshot(world: World) -> None:
    kitchen = _kitchen(world, ANA)
    added = _add(world, kitchen, _personal(world, ANA, "ana's Notebook"))

    facts = world.notebooks.facts_for(ANA, added.notebook.id)

    assert facts is not None
    assert notebook_view(facts).is_snapshot is True
    assert added.notebook.is_snapshot is True
    assert added.notebook.is_own_capture_notebook is False


# --- Spec 019: the copies are queued for embedding -------------------------------------------


def test_a_created_snapshot_enqueues_its_notebook_once(world: World) -> None:
    kitchen = _kitchen(world, ANA)
    source = _personal(world, ANA, "ana's Notebook")
    jobs = FakeEmbeddingJobs()

    added = _add(world, kitchen, source, jobs=jobs)

    assert jobs.enqueued_notebooks == [added.notebook.id]


def test_a_replayed_snapshot_enqueues_nothing(world: World) -> None:
    kitchen = _kitchen(world, ANA)
    source = _personal(world, ANA, "ana's Notebook")
    key = uuid4()
    jobs = FakeEmbeddingJobs()
    _add(world, kitchen, source, key=key, jobs=jobs)

    _add(world, kitchen, source, key=key, jobs=jobs)

    assert len(jobs.enqueued_notebooks) == 1
