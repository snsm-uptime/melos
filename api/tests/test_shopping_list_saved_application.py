"""The saved list use cases against fake ports (spec 025)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from application.ports import CartDraft, CartDraftItem
from application.shopping_list import (
    ActiveListSync,
    AddShoppingItemService,
    ClosedShoppingListsService,
    CloseShoppingListService,
    RemoveShoppingItemService,
)
from domain.errors import (
    KitchenArchivedError,
    KitchenNotFoundError,
    ShoppingItemNotFoundError,
    ShoppingListEmptyError,
    ShoppingListNotActiveError,
    ShoppingListNotFoundError,
)
from tests.test_shopping_list_application import Fixture, measured, shown


class Saved(Fixture):
    def __init__(self, *, archived: bool = False) -> None:
        super().__init__(archived=archived)
        self.sync = ActiveListSync(self.s.carts, self.lines, self.lists)  # type: ignore[arg-type]

    def change(self, cls):  # noqa: ANN001, ANN201
        return cls(self.s.world.kitchens, self.s.carts, self.lists, self.sync)

    def add(self, name: str = "soap", **amount: str) -> None:
        self.change(AddShoppingItemService).execute(self.s.ana, self.s.kitchen, name, **amount)

    def done(self, list_id=None):  # noqa: ANN001, ANN201
        return self.change(CloseShoppingListService).execute(
            self.s.ana, self.s.kitchen, list_id or self.get().list_id
        )

    def rice(self) -> None:
        self.rid = self.recipe("Rice", [measured("rice", "2", "cup")])
        self.cart((self.rid, 4))
        self.sync.refresh(self.s.kitchen)


def test_refresh_starts_a_list_only_for_a_cart_with_recipes() -> None:
    f = Saved()
    f.sync.refresh(f.s.kitchen)
    assert f.get().status == "live"
    f.rice()
    view = f.get()
    assert view.status == "active"
    assert shown(view) == [("rice", None, (("2", "cup"),))]


def test_refresh_follows_the_cart_and_keeps_hand_items() -> None:
    f = Saved()
    f.rice()
    f.add()
    f.cart((f.rid, 8))
    f.sync.refresh(f.s.kitchen)
    view = f.get()
    assert shown(view) == [("rice", None, (("4", "cup"),))]
    assert [i.name for i in view.hand_items] == ["soap"]


def test_saved_list_ignores_recipe_edits_until_the_next_save() -> None:
    f = Saved()
    f.rice()
    f.lines.lines[f.rid] = (measured("rice", "9", "cup"),)
    assert shown(f.get()) == [("rice", None, (("2", "cup"),))]
    f.sync.refresh(f.s.kitchen)
    assert shown(f.get()) == [("rice", None, (("9", "cup"),))]


def test_a_cart_emptied_keeps_the_list_and_its_hand_items() -> None:
    f = Saved()
    f.rice()
    f.add()
    f.cart()
    f.sync.refresh(f.s.kitchen)
    view = f.get()
    assert (view.status, view.is_empty, shown(view)) == ("active", False, [])
    assert len(view.hand_items) == 1


def test_my_draft_is_shown_and_not_written() -> None:
    f = Saved()
    f.rice()
    saved = f.lists.active(f.s.kitchen)
    f.locks = type(f.locks)(_Draft(f, f.s.ana.session_id, ((f.rid, 8),)))
    view = f.get()
    assert view.status == "draft"
    assert shown(view) == [("rice", None, (("4", "cup"),))]
    assert f.lists.active(f.s.kitchen) == saved
    # Someone else still sees the saved list.
    other = f.get(f.s.ben)
    assert other.status == "active"
    assert shown(other) == [("rice", None, (("2", "cup"),))]


class _Draft:
    def __init__(self, f: Fixture, session_id, items) -> None:  # noqa: ANN001
        self._session = session_id
        self._items = items

    def cart_holder(self, kitchen_id):  # noqa: ANN001, ANN201
        return type("Holder", (), {"session_id": self._session})

    def cart_draft(self, kitchen_id, session_id):  # noqa: ANN001, ANN201
        return CartDraft(tuple(CartDraftItem(r, s) for r, s in self._items))


def test_a_first_item_starts_a_list_with_the_saved_cart() -> None:
    f = Saved()
    rid = f.recipe("Rice", [measured("rice", "2", "cup")])
    f.cart((rid, 4))
    f.add()
    view = f.get()
    assert view.status == "active"
    assert shown(view) == [("rice", None, (("2", "cup"),))]
    assert f.s.carts.for_update == [f.s.kitchen]


def test_a_first_item_with_an_empty_cart() -> None:
    f = Saved()
    f.add()
    view = f.get()
    assert (view.status, view.is_empty) == ("active", False)


def test_same_name_stays_a_separate_line() -> None:
    f = Saved()
    f.rice()
    f.add("rice", quantity="1", unit="kg")
    view = f.get()
    assert len(view.shopping_list.lines) == 1
    assert len(view.hand_items) == 1


def test_only_hand_items_can_be_removed() -> None:
    f = Saved()
    f.rice()
    f.add()
    remove = f.change(RemoveShoppingItemService)
    saved = f.lists.active(f.s.kitchen)
    cart_line = next(i for i in saved.items if i.origin == "cart")
    with pytest.raises(ShoppingItemNotFoundError):
        remove.execute(f.s.ana, f.s.kitchen, cart_line.id)
    remove.execute(f.s.ana, f.s.kitchen, f.get().hand_items[0].id)
    assert f.get().hand_items == ()


def test_remove_with_no_active_list() -> None:
    f = Saved()
    with pytest.raises(ShoppingItemNotFoundError):
        f.change(RemoveShoppingItemService).execute(f.s.ana, f.s.kitchen, uuid4())


def test_archived_refuses_changes_and_outsiders_get_not_found() -> None:
    f = Saved(archived=True)
    assert f.get().kitchen_is_archived
    with pytest.raises(KitchenArchivedError):
        f.add()
    with pytest.raises(KitchenArchivedError):
        f.change(CloseShoppingListService).execute(f.s.ana, f.s.kitchen, uuid4())
    g = Saved()
    with pytest.raises(KitchenNotFoundError):
        g.change(AddShoppingItemService).execute(g.s.ana, uuid4(), "soap")


def test_done_closes_and_empties_the_cart() -> None:
    f = Saved()
    f.rice()
    closed = f.done()
    assert closed.saved.closing_date == datetime.now(UTC).date()
    assert f.s.carts.read(f.s.kitchen).items == ()
    view = f.get()
    assert (view.status, view.is_empty) == ("live", True)
    # What was bought stays on the closed list.
    assert [i.name for i in closed.saved.items] == ["rice"]


def test_done_twice_and_on_an_empty_list_are_refused() -> None:
    f = Saved()
    f.rice()
    list_id = f.get().list_id
    f.done()
    with pytest.raises(ShoppingListNotActiveError):
        f.done(list_id)
    g = Saved()
    g.add()
    g.change(RemoveShoppingItemService).execute(g.s.ana, g.s.kitchen, g.get().hand_items[0].id)
    with pytest.raises(ShoppingListEmptyError):
        g.done()


def test_after_done_the_next_save_or_item_starts_a_new_list() -> None:
    f = Saved()
    f.rice()
    first = f.get().list_id
    f.done()
    f.sync.refresh(f.s.kitchen)
    assert f.get().list_id is None
    f.cart((f.rid, 4))
    f.sync.refresh(f.s.kitchen)
    second = f.get().list_id
    assert second not in (None, first)
    f.done()
    f.add()
    assert f.get().list_id not in (None, first, second)
    assert shown(f.get()) == []


def test_closed_lists_and_their_access() -> None:
    f = Saved()
    f.rice()
    closed = f.done()
    service = ClosedShoppingListsService(f.s.world.kitchens, f.s.carts, f.lists)
    summaries = service.list(f.s.ana, f.s.kitchen)
    assert [(s.id, s.recipe_titles) for s in summaries] == [(closed.saved.id, ("Rice",))]
    assert service.get(f.s.ana, f.s.kitchen, closed.saved.id).missing_recipe_ids == frozenset()
    f.s.carts.recipes.pop(f.rid)
    assert service.get(f.s.ana, f.s.kitchen, closed.saved.id).missing_recipe_ids == {f.rid}
    with pytest.raises(ShoppingListNotFoundError):
        service.get(f.s.ana, f.s.kitchen, uuid4())
