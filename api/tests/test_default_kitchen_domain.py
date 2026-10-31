"""The four steps of the default kitchen rule (spec 064, data-model.md)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from domain.default_kitchen import MemberKitchen, resolve_default_kitchen


def kitchen(day: int = 1, joined: int = 1, *, owner: bool = True, archived: bool = False):
    return MemberKitchen(
        id=uuid4(),
        is_archived=archived,
        is_owner=owner,
        created_at=datetime(2026, 1, day, tzinfo=UTC),
        joined_at=datetime(2026, 2, joined, tzinfo=UTC),
    )


def test_keeps_the_stored_kitchen_when_active_and_a_member() -> None:
    first, second = kitchen(1), kitchen(2)
    assert resolve_default_kitchen(second.id, [first, second]) == second.id


def test_stored_kitchen_may_be_one_the_person_only_joined() -> None:
    owned, joined = kitchen(1), kitchen(2, owner=False)
    assert resolve_default_kitchen(joined.id, [owned, joined]) == joined.id


def test_falls_to_earliest_created_owned_kitchen() -> None:
    later, earlier = kitchen(5), kitchen(2)
    guest = kitchen(1, owner=False)
    assert resolve_default_kitchen(None, [later, guest, earlier]) == earlier.id


def test_archived_stored_kitchen_is_not_kept() -> None:
    archived, active = kitchen(1, archived=True), kitchen(2)
    assert resolve_default_kitchen(archived.id, [archived, active]) == active.id


def test_stored_kitchen_the_person_left_is_not_kept() -> None:
    remaining = kitchen(2)
    gone: UUID = uuid4()
    assert resolve_default_kitchen(gone, [remaining]) == remaining.id


def test_falls_to_earliest_joined_when_nothing_is_owned() -> None:
    later = kitchen(1, joined=9, owner=False)
    earlier = kitchen(2, joined=3, owner=False)
    assert resolve_default_kitchen(None, [later, earlier]) == earlier.id


def test_none_when_no_active_kitchen_remains() -> None:
    assert resolve_default_kitchen(uuid4(), [kitchen(archived=True)]) is None
    assert resolve_default_kitchen(None, []) is None
