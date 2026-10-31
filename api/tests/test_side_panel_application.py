"""Side panel use cases against a fake repository (spec 064)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from application.side_panel import GetSidePanelService, SetDefaultKitchenService
from domain.default_kitchen import MemberKitchen
from domain.errors import KitchenArchivedError, KitchenNotFoundError

USER = uuid4()


def kitchen(day: int, *, archived: bool = False) -> MemberKitchen:
    moment = datetime(2026, 1, day, tzinfo=UTC)
    return MemberKitchen(uuid4(), archived, True, moment, moment)


class FakeRepo:
    def __init__(self, kitchens: list[MemberKitchen], stored: UUID | None = None) -> None:
        self.kitchens = kitchens
        self.stored = stored
        self.writes: list[UUID | None] = []

    def stored_default_kitchen(self, user_id: UUID) -> UUID | None:
        return self.stored

    def member_kitchens(self, user_id: UUID) -> list[MemberKitchen]:
        return self.kitchens

    def set_default_kitchen(self, user_id: UUID, kitchen_id: UUID | None) -> None:
        self.stored = kitchen_id
        self.writes.append(kitchen_id)

    def count_notebooks(self, user_id: UUID) -> int:
        return 2

    def count_recipes_added(self, user_id: UUID) -> int:
        return 5


def test_read_stores_a_resolved_kitchen_that_differs() -> None:
    first = kitchen(1)
    repo = FakeRepo([first])
    view = GetSidePanelService(repo).execute(USER)
    assert (view.default_kitchen_id, view.recipes_added, view.notebooks) == (first.id, 5, 2)
    assert repo.writes == [first.id]


def test_read_does_not_write_when_nothing_changed() -> None:
    first = kitchen(1)
    repo = FakeRepo([first], first.id)
    GetSidePanelService(repo).execute(USER)
    assert repo.writes == []


def test_read_clears_the_stored_kitchen_when_none_remains() -> None:
    repo = FakeRepo([], uuid4())
    assert GetSidePanelService(repo).execute(USER).default_kitchen_id is None
    assert repo.writes == [None]


def test_restoring_an_archived_old_default_does_not_switch_back() -> None:
    old, fallback = kitchen(1, archived=True), kitchen(2)
    repo = FakeRepo([old, fallback], old.id)
    GetSidePanelService(repo).execute(USER)
    repo.kitchens = [kitchen_restored(old), fallback]
    assert GetSidePanelService(repo).execute(USER).default_kitchen_id == fallback.id


def kitchen_restored(archived: MemberKitchen) -> MemberKitchen:
    return MemberKitchen(
        archived.id, False, archived.is_owner, archived.created_at, archived.joined_at
    )


def test_set_stores_an_active_kitchen() -> None:
    first, second = kitchen(1), kitchen(2)
    repo = FakeRepo([first, second], first.id)
    assert SetDefaultKitchenService(repo).execute(USER, second.id).default_kitchen_id == second.id
    assert repo.stored == second.id


def test_set_rejects_a_kitchen_the_person_is_not_in() -> None:
    repo = FakeRepo([kitchen(1)])
    with pytest.raises(KitchenNotFoundError):
        SetDefaultKitchenService(repo).execute(USER, uuid4())
    assert repo.writes == []


def test_set_rejects_an_archived_kitchen() -> None:
    archived = kitchen(1, archived=True)
    repo = FakeRepo([archived])
    with pytest.raises(KitchenArchivedError):
        SetDefaultKitchenService(repo).execute(USER, archived.id)
    assert repo.writes == []
