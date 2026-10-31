"""The shopping list use case against fake ports (spec 023)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from application.ports import (
    CartDraft,
    CartDraftItem,
    CartIngredientLine,
    IngredientLineReader,
    LockHolder,
    SavedCart,
    SessionRef,
)
from application.shopping_list import GetShoppingListService
from domain.shopping_list import SavedLine, SavedList
from tests.test_carts_application import Setup, _setup


@dataclass
class FakeLines:
    """Ingredient lines per recipe, in memory, with a log of reads."""

    lines: dict[UUID, tuple[CartIngredientLine, ...]] = field(default_factory=dict)
    reads: list[tuple[UUID, ...]] = field(default_factory=list)

    def lines_for(self, recipe_ids: Sequence[UUID]) -> dict[UUID, tuple[CartIngredientLine, ...]]:
        self.reads.append(tuple(recipe_ids))
        return {rid: self.lines[rid] for rid in recipe_ids if rid in self.lines}


@dataclass
class FakeLists:
    """Saved lists in memory."""

    lists: dict[UUID, SavedList] = field(default_factory=dict)

    def active(self, kitchen_id: UUID) -> SavedList | None:
        for saved in self.lists.values():
            if saved.kitchen_id == kitchen_id and saved.closing_date is None:
                return saved
        return None

    def get_or_create_active(self, kitchen_id: UUID) -> SavedList:
        found = self.active(kitchen_id)
        if found is not None:
            return found
        saved = SavedList(uuid4(), kitchen_id, None, datetime.now(UTC), ())
        self.lists[saved.id] = saved
        return saved

    def replace_cart_lines(self, list_id: UUID, lines: Sequence[SavedLine]) -> None:
        saved = self.lists[list_id]
        hand = tuple(i for i in saved.items if i.origin == "hand")
        cart = tuple(replace(line, id=uuid4()) for line in lines)
        self.lists[list_id] = replace(saved, items=cart + hand)

    def add_item(self, list_id: UUID, item: SavedLine) -> None:
        saved = self.lists[list_id]
        self.lists[list_id] = replace(saved, items=(*saved.items, replace(item, id=uuid4())))

    def remove_hand_item(self, list_id: UUID, item_id: UUID) -> bool:
        saved = self.lists[list_id]
        kept = tuple(i for i in saved.items if not (i.id == item_id and i.origin == "hand"))
        self.lists[list_id] = replace(saved, items=kept)
        return len(kept) != len(saved.items)

    def close(self, list_id: UUID, closing_date: date) -> bool:
        saved = self.lists[list_id]
        if saved.closing_date is not None:
            return False
        self.lists[list_id] = replace(saved, closing_date=closing_date)
        return True

    def closed(self, kitchen_id: UUID) -> tuple[SavedList, ...]:
        rows = [
            s for s in self.lists.values() if s.kitchen_id == kitchen_id and s.closing_date
        ]
        return tuple(sorted(rows, key=lambda s: s.created_at, reverse=True))

    def closed_by_id(self, kitchen_id: UUID, list_id: UUID) -> SavedList | None:
        saved = self.lists.get(list_id)
        if saved is None or saved.kitchen_id != kitchen_id or saved.closing_date is None:
            return None
        return saved


class ReadOnlyLocks:
    """Only the two lock reads exist, so any lock write made by the service fails the test."""

    def __init__(self, inner) -> None:  # noqa: ANN001
        self._inner = inner
        self.calls: list[str] = []

    def cart_holder(self, kitchen_id: UUID) -> LockHolder | None:
        self.calls.append("cart_holder")
        return self._inner.cart_holder(kitchen_id)

    def cart_draft(self, kitchen_id: UUID, session_id: UUID) -> CartDraft | None:
        self.calls.append("cart_draft")
        return self._inner.cart_draft(kitchen_id, session_id)


def measured(name: str, quantity: str, unit: str, size: str | None = None) -> CartIngredientLine:
    return CartIngredientLine(name, Decimal(quantity), unit, size, None)


def vague(name: str, note: str) -> CartIngredientLine:
    return CartIngredientLine(name, None, None, None, note)


class Fixture:
    def __init__(self, *, archived: bool = False) -> None:
        self.s: Setup = _setup(archived=archived)
        self.lines = FakeLines()
        self.locks = ReadOnlyLocks(self.s.locks)
        self.lists = FakeLists()

    def recipe(self, title: str, lines: Sequence[CartIngredientLine], base: int = 4) -> UUID:
        rid = self.s.carts.add_recipe(self.s.notebook, title, base)
        self.lines.lines[rid] = tuple(lines)
        return rid

    def cart(self, *items: tuple[UUID, int]) -> None:
        self.s.carts.carts[self.s.kitchen] = SavedCart(
            self.s.kitchen, tuple(CartDraftItem(rid, servings) for rid, servings in items)
        )

    def service(self) -> GetShoppingListService:
        return GetShoppingListService(
            self.s.world.kitchens,
            self.s.carts,
            self.locks,
            self.lines,  # type: ignore[arg-type]
            self.lists,
        )

    def get(self, ref: SessionRef | None = None, kitchen_id: UUID | None = None):  # noqa: ANN201
        return self.service().execute(ref or self.s.ana, kitchen_id or self.s.kitchen)


def shown(view) -> list[tuple[str, str | None, tuple[tuple[str, str], ...]]]:  # noqa: ANN001
    return [
        (ln.name, ln.size, tuple((a.quantity, a.unit) for a in ln.amounts))
        for ln in view.shopping_list.lines
    ]


def test_fake_satisfies_the_port() -> None:
    reader: IngredientLineReader = FakeLines()
    assert reader is not None


def test_saved_cart_is_scaled_by_servings_and_base_servings() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("flour", "1", "cup")], base=4)
    b = f.recipe("B", [measured("flour", "1", "cup")], base=2)
    f.cart((a, 2), (b, 4))  # 1/2 + 2
    view = f.get()
    assert not view.is_empty
    assert shown(view) == [("flour", None, (("2.5", "cup"),))]


def test_saved_servings_scale_counts() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("egg", "2", "unit")], base=4)
    f.cart((a, 3))  # factor 3/4 → 1.5 eggs → 2
    assert shown(f.get()) == [("egg", None, (("2", "unit"),))]
    f.cart((a, 8))  # factor 2 → 4 eggs
    assert shown(f.get()) == [("egg", None, (("4", "unit"),))]


# --- US4: the editor's list follows their draft, everyone else sees the saved cart -----------


def _editing(f: Fixture, *items: tuple[UUID, int]) -> None:
    f.s.start(f.s.ana)
    f.s.put(f.s.ana, list(items))


def test_the_editor_sees_the_draft_and_another_member_the_saved_cart() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("flour", "1", "cup")], base=4)
    f.cart((a, 2))  # saved: factor 1/2
    _editing(f, (a, 8))  # draft: factor 2

    assert shown(f.get(f.s.ana)) == [("flour", None, (("2", "cup"),))]
    assert shown(f.get(f.s.ben)) == [("flour", None, (("0.5", "cup"),))]


def test_the_draft_can_add_and_drop_recipes() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("rice", "1", "cup")])
    b = f.recipe("B", [measured("beans", "1", "cup")])
    f.cart((a, 1))
    _editing(f, (b, 1))

    assert [n for n, _, _ in shown(f.get(f.s.ana))] == ["beans"]
    assert [n for n, _, _ in shown(f.get(f.s.ben))] == ["rice"]


def test_after_a_discard_the_editor_sees_the_saved_cart_again() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("flour", "1", "cup")])
    f.cart((a, 2))
    _editing(f, (a, 8))
    f.s.discard(f.s.ana)
    assert shown(f.get(f.s.ana)) == [("flour", None, (("0.5", "cup"),))]


def test_after_a_save_everyone_sees_the_new_amounts() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("flour", "1", "cup")])
    f.cart((a, 2))
    _editing(f, (a, 8))
    f.s.save(f.s.ana)
    for ref in (f.s.ana, f.s.ben):
        assert shown(f.get(ref)) == [("flour", None, (("2", "cup"),))]


def test_an_expired_lock_no_longer_shows_the_draft() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("flour", "1", "cup")])
    f.cart((a, 2))
    _editing(f, (a, 8))
    f.s.locks.clock.advance(timedelta(minutes=5))
    assert shown(f.get(f.s.ana)) == [("flour", None, (("0.5", "cup"),))]


def test_a_drafted_recipe_deleted_since_is_skipped() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("rice", "1", "cup")])
    b = f.recipe("B", [measured("beans", "1", "cup")])
    f.cart((a, 1))
    _editing(f, (a, 1), (b, 1))
    f.s.carts.delete_recipe(b)
    assert [n for n, _, _ in shown(f.get(f.s.ana))] == ["rice"]


def test_an_empty_draft_is_an_empty_list_for_the_editor_only() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("rice", "1", "cup")])
    f.cart((a, 1))
    _editing(f)
    assert f.get(f.s.ana).is_empty
    assert not f.get(f.s.ben).is_empty


def test_reading_as_the_editor_does_not_renew_the_lock() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("rice", "1", "cup")])
    f.cart((a, 1))
    _editing(f, (a, 1))
    before = f.s.locks.cart_locks[f.s.kitchen].last_active_at
    f.s.locks.clock.advance(timedelta(minutes=2))
    f.get(f.s.ana)
    assert f.s.locks.cart_locks[f.s.kitchen].last_active_at == before
