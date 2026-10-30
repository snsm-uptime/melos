"""The shopping list use case against fake ports (spec 023)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from application.ports import (
    CartDraft,
    CartDraftItem,
    CartIngredientLine,
    CartRecipeFacts,
    IngredientLineReader,
    LockHolder,
    SavedCart,
    SessionRef,
)
from application.shopping_list import GetShoppingListService
from domain.errors import KitchenNotFoundError
from tests.test_carts_application import ANA, BEN, CAT, Setup, _setup


@dataclass
class FakeLines:
    """Ingredient lines per recipe, in memory, with a log of reads."""

    lines: dict[UUID, tuple[CartIngredientLine, ...]] = field(default_factory=dict)
    reads: list[tuple[UUID, ...]] = field(default_factory=list)

    def lines_for(self, recipe_ids: Sequence[UUID]) -> dict[UUID, tuple[CartIngredientLine, ...]]:
        self.reads.append(tuple(recipe_ids))
        return {rid: self.lines[rid] for rid in recipe_ids if rid in self.lines}


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

    def recipe(self, title: str, lines: Sequence[CartIngredientLine], base: int = 4) -> UUID:
        rid = self.s.carts.add_recipe(self.s.notebook, title, base)
        self.lines.lines[rid] = tuple(lines)
        return rid

    def cart(self, *items: tuple[UUID, int], people: int | None = None) -> None:
        self.s.carts.carts[self.s.kitchen] = SavedCart(
            self.s.kitchen, people, tuple(CartDraftItem(rid, meals) for rid, meals in items)
        )

    def service(self) -> GetShoppingListService:
        return GetShoppingListService(
            self.s.world.kitchens,
            self.s.carts,
            self.locks,
            self.lines,  # type: ignore[arg-type]
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


def test_saved_cart_is_scaled_by_people_meals_and_base_servings() -> None:
    f = Fixture()
    # People defaults to the 2 members. A: 2×1/4 = 1/2; B: 2×2/2 = 2.
    a = f.recipe("A", [measured("flour", "1", "cup")], base=4)
    b = f.recipe("B", [measured("flour", "1", "cup")], base=2)
    f.cart((a, 1), (b, 2))
    view = f.get()
    assert not view.is_empty
    assert shown(view) == [("flour", None, (("2.5", "cup"),))]


def test_saved_people_overrides_the_member_count() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("egg", "2", "unit")], base=4)
    f.cart((a, 1), people=3)  # factor 3/4 → 1.5 eggs → 2
    assert shown(f.get()) == [("egg", None, (("2", "unit"),))]
    f.cart((a, 1), people=8)  # factor 2 → 4 eggs
    assert shown(f.get()) == [("egg", None, (("4", "unit"),))]


def test_decimal_quantities_are_used_exactly() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("cream", "0.25", "cup")], base=4)
    f.cart((a, 1))  # factor 1/2 → exactly 0.125 → half up 0.13
    assert shown(f.get()) == [("cream", None, (("0.13", "cup"),))]


def test_chips_follow_cart_order_not_title_order() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("flour", "1", "cup")])
    b = f.recipe("B", [measured("flour", "1", "cup")])
    f.cart((b, 1), (a, 1))
    view = f.get()
    assert [r.title for r in view.shopping_list.lines[0].recipes] == ["B", "A"]


def test_deleted_and_non_kitchen_recipes_are_skipped() -> None:
    f = Fixture()
    kept = f.recipe("Kept", [measured("rice", "1", "cup")])
    gone = f.recipe("Gone", [measured("salt", "1", "tsp")])
    other = f.recipe("Other", [measured("sugar", "1", "tsp")])
    f.cart((kept, 1), (gone, 1), (other, 1))
    del f.s.carts.recipes[gone]
    facts = f.s.carts.recipes[other]
    f.s.carts.recipes[other] = CartRecipeFacts(
        facts.recipe_id, facts.title, facts.notebook_id, facts.notebook_name, 4, None
    )
    assert [n for n, _, _ in shown(f.get())] == ["rice"]


def test_lines_are_read_once_for_all_recipes() -> None:
    f = Fixture()
    ids = [f.recipe(f"R{n}", [measured("rice", "1", "cup")]) for n in range(5)]
    f.cart(*((rid, 1) for rid in ids))
    f.get()
    assert len(f.lines.reads) == 1 and set(f.lines.reads[0]) == set(ids)


def test_empty_cart_is_empty_and_reads_no_lines() -> None:
    f = Fixture()
    view = f.get()
    assert view.is_empty
    assert view.shopping_list.lines == () and view.shopping_list.your_call == ()
    assert f.lines.reads == []


def test_cart_whose_recipes_have_no_lines_is_not_empty() -> None:
    f = Fixture()
    a = f.recipe("Bare", [])
    f.cart((a, 1))
    view = f.get()
    assert not view.is_empty and view.shopping_list.lines == ()


def test_non_member_and_unknown_kitchen_are_not_found() -> None:
    f = Fixture()
    outsider = SessionRef(CAT, uuid4())
    with pytest.raises(KitchenNotFoundError):
        f.get(outsider)
    with pytest.raises(KitchenNotFoundError):
        f.get(f.s.ana, uuid4())


def test_archived_kitchen_can_be_read() -> None:
    f = Fixture(archived=True)
    a = f.recipe("A", [measured("rice", "1", "cup")])
    f.cart((a, 1))
    assert shown(f.get()) == [("rice", None, (("0.5", "cup"),))]  # factor 2 × 1 / 4


def test_reading_only_looks_at_the_lock_and_never_writes() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("rice", "1", "cup")])
    f.cart((a, 1))
    f.get(f.s.ben)
    assert set(f.locks.calls) <= {"cart_holder", "cart_draft"}
    assert f.s.carts.saves == [] and f.s.carts.for_update == []
    assert f.s.carts.counts[a] == 0


def test_both_members_see_the_same_saved_list() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("rice", "1", "cup")])
    f.cart((a, 1))
    assert shown(f.get(SessionRef(ANA, uuid4()))) == shown(f.get(SessionRef(BEN, uuid4())))


# --- US4: the editor's list follows their draft, everyone else sees the saved cart -----------


def _editing(f: Fixture, people: int | None, *items: tuple[UUID, int]) -> None:
    f.s.start(f.s.ana)
    f.s.put(f.s.ana, people, list(items))


def test_the_editor_sees_the_draft_and_another_member_the_saved_cart() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("flour", "1", "cup")], base=4)
    f.cart((a, 1))  # saved: People 2 (members), Meals 1 → factor 1/2
    _editing(f, 4, (a, 2))  # draft: factor 4×2/4 = 2

    assert shown(f.get(f.s.ana)) == [("flour", None, (("2", "cup"),))]
    assert shown(f.get(f.s.ben)) == [("flour", None, (("0.5", "cup"),))]


def test_the_draft_can_add_and_drop_recipes() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("rice", "1", "cup")])
    b = f.recipe("B", [measured("beans", "1", "cup")])
    f.cart((a, 1))
    _editing(f, None, (b, 1))

    assert [n for n, _, _ in shown(f.get(f.s.ana))] == ["beans"]
    assert [n for n, _, _ in shown(f.get(f.s.ben))] == ["rice"]


def test_a_draft_that_follows_the_member_count_uses_it() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("egg", "2", "unit")], base=4)
    f.cart((a, 1), people=8)
    _editing(f, None, (a, 1))  # People null → 2 members → factor 1/2 → 1 egg
    assert shown(f.get(f.s.ana)) == [("egg", None, (("1", "unit"),))]
    assert shown(f.get(f.s.ben)) == [("egg", None, (("4", "unit"),))]


def test_after_a_discard_the_editor_sees_the_saved_cart_again() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("flour", "1", "cup")])
    f.cart((a, 1))
    _editing(f, 4, (a, 2))
    f.s.discard(f.s.ana)
    assert shown(f.get(f.s.ana)) == [("flour", None, (("0.5", "cup"),))]


def test_after_a_save_everyone_sees_the_new_amounts() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("flour", "1", "cup")])
    f.cart((a, 1))
    _editing(f, 4, (a, 2))
    f.s.save(f.s.ana)
    for ref in (f.s.ana, f.s.ben):
        assert shown(f.get(ref)) == [("flour", None, (("2", "cup"),))]


def test_an_expired_lock_no_longer_shows_the_draft() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("flour", "1", "cup")])
    f.cart((a, 1))
    _editing(f, 4, (a, 2))
    f.s.locks.clock.advance(timedelta(minutes=5))
    assert shown(f.get(f.s.ana)) == [("flour", None, (("0.5", "cup"),))]


def test_a_drafted_recipe_deleted_since_is_skipped() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("rice", "1", "cup")])
    b = f.recipe("B", [measured("beans", "1", "cup")])
    f.cart((a, 1))
    _editing(f, None, (a, 1), (b, 1))
    f.s.carts.delete_recipe(b)
    assert [n for n, _, _ in shown(f.get(f.s.ana))] == ["rice"]


def test_an_empty_draft_is_an_empty_list_for_the_editor_only() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("rice", "1", "cup")])
    f.cart((a, 1))
    _editing(f, None)
    assert f.get(f.s.ana).is_empty
    assert not f.get(f.s.ben).is_empty


def test_reading_as_the_editor_does_not_renew_the_lock() -> None:
    f = Fixture()
    a = f.recipe("A", [measured("rice", "1", "cup")])
    f.cart((a, 1))
    _editing(f, None, (a, 1))
    before = f.s.locks.cart_locks[f.s.kitchen].last_active_at
    f.s.locks.clock.advance(timedelta(minutes=2))
    f.get(f.s.ana)
    assert f.s.locks.cart_locks[f.s.kitchen].last_active_at == before
