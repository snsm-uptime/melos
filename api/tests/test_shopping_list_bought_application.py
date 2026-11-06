"""Marking items bought against fake ports (spec 070 US1)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from application.ports import SessionRef
from application.shopping_list import SetItemBoughtService
from domain.errors import (
    KitchenArchivedError,
    KitchenNotFoundError,
    ShoppingItemNotFoundError,
    ShoppingListClosedError,
)
from tests.test_shopping_list_saved_application import Saved


def _mark(f: Saved, item_id, bought: bool, who=None):  # noqa: ANN001, ANN202
    return f.change(SetItemBoughtService).execute(who or f.s.ana, f.s.kitchen, item_id, bought)


def _rice_id(f: Saved):  # noqa: ANN202
    active = f.lists.active(f.s.kitchen)
    assert active is not None
    return active.items[0].id


def test_a_member_sets_and_clears_the_flag() -> None:
    f = Saved()
    f.rice()
    item = _mark(f, _rice_id(f), True)
    assert item.bought
    assert f.lists.active(f.s.kitchen).items[0].bought
    assert not _mark(f, _rice_id(f), False).bought


def test_unknown_item_and_outsider() -> None:
    f = Saved()
    f.rice()
    with pytest.raises(ShoppingItemNotFoundError):
        _mark(f, uuid4(), True)
    outsider = SessionRef(user_id=uuid4(), session_id=uuid4())
    with pytest.raises(KitchenNotFoundError):
        _mark(f, _rice_id(f), True, who=outsider)


def test_a_closed_list_is_refused() -> None:
    f = Saved()
    f.rice()
    item_id = _rice_id(f)
    f.done()
    with pytest.raises(ShoppingListClosedError):
        _mark(f, item_id, False)


def test_an_archived_kitchen_is_refused() -> None:
    f = Saved(archived=True)
    with pytest.raises(KitchenArchivedError):
        _mark(f, uuid4(), True)
