"""The kitchen's shopping list (specs 023 and 025).

With no active list, the list is built from the cart on every read. Saving a cart, or adding the
first item by hand, starts the stored active list; Done closes it for good. A read never takes,
renews or releases the cart lock (spec 023 FR-014). Non-members and unknown kitchens get
KitchenNotFoundError (404); an archived kitchen can still be read.

Every list write holds the cart row lock, which serializes them (spec 025 R3).

Nothing is logged but outcomes and counts (constitution §4).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from fractions import Fraction
from typing import Literal
from uuid import UUID

from domain.cart import (
    ScaledRecipe,
    ShoppingLine,
    ShoppingList,
    build_shopping_list,
    scale_factor,
)
from domain.errors import (
    KitchenArchivedError,
    KitchenNotFoundError,
    ShoppingItemNotFoundError,
    ShoppingListEmptyError,
    ShoppingListNotActiveError,
    ShoppingListNotFoundError,
)
from domain.shopping_list import (
    SavedLine,
    SavedList,
    cart_lines,
    closing_date,
    hand_item,
    hand_lines,
    recipe_titles,
    stored_cart_list,
)

from application.kitchens import KitchenRepository
from application.ports import (
    CartDraft,
    CartDraftItem,
    CartRepository,
    EditLockRepository,
    IngredientLineReader,
    SessionRef,
    ShoppingListRepository,
)

logger = logging.getLogger(__name__)

ListStatus = Literal["live", "active", "draft"]


def build_cart_list(
    carts: CartRepository,
    lines: IngredientLineReader,
    kitchen_id: UUID,
    items: Sequence[CartDraftItem],
) -> ShoppingList:
    """The one calculation from cart entries to a list (spec 025 R1)."""
    ids = list(dict.fromkeys(item.recipe_id for item in items))
    facts = carts.recipe_facts(ids)
    recipe_lines = lines.lines_for([rid for rid in ids if rid in facts])
    recipes: list[ScaledRecipe] = []
    for item in items:
        fact = facts.get(item.recipe_id)
        if fact is None or fact.kitchen_id != kitchen_id:
            continue
        recipes.append(
            ScaledRecipe(
                recipe_id=fact.recipe_id,
                title=fact.title,
                factor=scale_factor(item.servings, fact.base_servings),
                lines=tuple(
                    ShoppingLine(
                        name=line.name,
                        # Exact: a Decimal becomes a Fraction with no float in between.
                        quantity=None if line.quantity is None else Fraction(line.quantity),
                        unit=line.unit,
                        size=line.size,
                        vague_note=line.vague_note,
                    )
                    for line in recipe_lines.get(item.recipe_id, ())
                ),
            )
        )
    return build_shopping_list(recipes)


class ActiveListSync:
    """Keeps the stored list in line with the saved cart; hand items are never touched."""

    def __init__(
        self,
        carts: CartRepository,
        lines: IngredientLineReader,
        lists: ShoppingListRepository,
    ) -> None:
        self._carts = carts
        self._lines = lines
        self._lists = lists

    def _replace(self, list_id: UUID, kitchen_id: UUID) -> None:
        items = self._carts.read(kitchen_id).items
        built = build_cart_list(self._carts, self._lines, kitchen_id, items)
        self._lists.replace_cart_lines(list_id, cart_lines(built))

    def refresh(self, kitchen_id: UUID) -> None:
        active = self._lists.active(kitchen_id)
        if active is None:
            # An empty cart does not start a list (FR-001).
            if not self._carts.read(kitchen_id).items:
                return
            active = self._lists.get_or_create_active(kitchen_id)
        self._replace(active.id, kitchen_id)
        logger.info("shopping list outcome=refreshed")

    def ensure_active(self, kitchen_id: UUID) -> SavedList:
        """The active list, started from the saved cart when there is none."""
        active = self._lists.active(kitchen_id)
        if active is not None:
            return active
        active = self._lists.get_or_create_active(kitchen_id)
        self._replace(active.id, kitchen_id)
        return active


@dataclass(frozen=True, slots=True)
class ShoppingListView:
    # True when there is nothing at all: no cart recipes and no saved items.
    is_empty: bool
    shopping_list: ShoppingList
    status: ListStatus = "live"
    list_id: UUID | None = None
    hand_items: tuple[SavedLine, ...] = ()
    # Saved chips whose recipe is gone; they show as plain text (spec 025 R6).
    missing_recipe_ids: frozenset[UUID] = frozenset()
    kitchen_is_archived: bool = False


@dataclass(frozen=True, slots=True)
class ClosedListView:
    saved: SavedList
    shopping_list: ShoppingList
    hand_items: tuple[SavedLine, ...]
    missing_recipe_ids: frozenset[UUID]


def _missing(carts: CartRepository, saved: Sequence[SavedList]) -> frozenset[UUID]:
    ids = {ref.recipe_id for s in saved for item in s.items for ref in item.recipes}
    if not ids:
        return frozenset()
    return frozenset(ids - set(carts.recipe_facts(list(ids))))


def _member_kitchen(kitchens: KitchenRepository, ref: SessionRef, kitchen_id: UUID):  # noqa: ANN202
    kitchen = kitchens.get_kitchen(kitchen_id)
    if kitchen is None or kitchens.get_membership(kitchen_id, ref.user_id) is None:
        raise KitchenNotFoundError()
    return kitchen


class GetShoppingListService:
    def __init__(
        self,
        kitchens: KitchenRepository,
        carts: CartRepository,
        locks: EditLockRepository,
        lines: IngredientLineReader,
        lists: ShoppingListRepository,
    ) -> None:
        self._kitchens = kitchens
        self._carts = carts
        self._locks = locks
        self._lines = lines
        self._lists = lists

    def execute(self, ref: SessionRef, kitchen_id: UUID) -> ShoppingListView:
        kitchen = _member_kitchen(self._kitchens, ref, kitchen_id)
        archived = kitchen.is_archived
        active = self._lists.active(kitchen_id)
        hand = hand_lines(active.items) if active is not None else ()
        list_id = active.id if active is not None else None

        draft = self._my_draft(ref, kitchen_id)
        if draft is not None:
            built = build_cart_list(self._carts, self._lines, kitchen_id, draft)
            return ShoppingListView(
                is_empty=not draft and not hand,
                shopping_list=built,
                status="draft",
                list_id=list_id,
                hand_items=hand,
                kitchen_is_archived=archived,
            )
        if active is not None:
            return ShoppingListView(
                is_empty=not active.items,
                shopping_list=stored_cart_list(active.items),
                status="active",
                list_id=list_id,
                hand_items=hand,
                missing_recipe_ids=_missing(self._carts, [active]),
                kitchen_is_archived=archived,
            )
        items = self._carts.read(kitchen_id).items
        if not items:
            return ShoppingListView(
                is_empty=True,
                shopping_list=build_shopping_list([]),
                kitchen_is_archived=archived,
            )
        built = build_cart_list(self._carts, self._lines, kitchen_id, items)
        logger.info(
            "shopping list outcome=built lines=%d your_call=%d",
            len(built.lines),
            len(built.your_call),
        )
        return ShoppingListView(
            is_empty=False, shopping_list=built, kitchen_is_archived=archived
        )

    def _my_draft(self, ref: SessionRef, kitchen_id: UUID) -> tuple[CartDraftItem, ...] | None:
        """My draft while my session holds the live cart lock (spec 023 FR-001).

        Only reads the lock: it is never taken, renewed or released here (FR-014).
        """
        holder = self._locks.cart_holder(kitchen_id)
        if holder is None or holder.session_id != ref.session_id:
            return None
        draft = self._locks.cart_draft(kitchen_id, ref.session_id)
        return None if draft is None else draft.items


class _ListChange:
    def __init__(
        self,
        kitchens: KitchenRepository,
        carts: CartRepository,
        lists: ShoppingListRepository,
        sync: ActiveListSync,
    ) -> None:
        self._kitchens = kitchens
        self._carts = carts
        self._lists = lists
        self._sync = sync

    def _writable(self, ref: SessionRef, kitchen_id: UUID) -> None:
        """Access, archive check, then the cart row lock that serializes list writes."""
        if _member_kitchen(self._kitchens, ref, kitchen_id).is_archived:
            raise KitchenArchivedError()
        self._carts.get_or_create_for_update(kitchen_id)


class AddShoppingItemService(_ListChange):
    def execute(
        self,
        ref: SessionRef,
        kitchen_id: UUID,
        name: object,
        quantity: object = None,
        unit: object = None,
        size: object = None,
    ) -> None:
        item = hand_item(name, quantity, unit, size)
        self._writable(ref, kitchen_id)
        active = self._sync.ensure_active(kitchen_id)
        self._lists.add_item(active.id, item)
        logger.info("shopping item outcome=added")


class RemoveShoppingItemService(_ListChange):
    def execute(self, ref: SessionRef, kitchen_id: UUID, item_id: UUID) -> None:
        self._writable(ref, kitchen_id)
        active = self._lists.active(kitchen_id)
        if active is None or not self._lists.remove_hand_item(active.id, item_id):
            raise ShoppingItemNotFoundError()
        logger.info("shopping item outcome=removed")


class CloseShoppingListService(_ListChange):
    """Done: the member's date, for good, and the saved cart is emptied (FR-009)."""

    def execute(
        self,
        ref: SessionRef,
        kitchen_id: UUID,
        list_id: UUID,
        local_date: date | None = None,
    ) -> ClosedListView:
        closes_on = closing_date(local_date, datetime.now(UTC).date())
        self._writable(ref, kitchen_id)
        active = self._lists.active(kitchen_id)
        if active is None or active.id != list_id:
            raise ShoppingListNotActiveError()
        if not active.items:
            raise ShoppingListEmptyError()
        if not self._lists.close(list_id, closes_on):
            raise ShoppingListNotActiveError()
        self._carts.save(kitchen_id, CartDraft(()), ref.user_id)
        closed = self._lists.closed_by_id(kitchen_id, list_id)
        assert closed is not None
        logger.info("shopping list outcome=closed items=%d", len(closed.items))
        return _closed_view(closed, _missing(self._carts, [closed]))


def _closed_view(saved: SavedList, missing: frozenset[UUID]) -> ClosedListView:
    return ClosedListView(saved, stored_cart_list(saved.items), hand_lines(saved.items), missing)


@dataclass(frozen=True, slots=True)
class ClosedListSummary:
    id: UUID
    closing_date: date
    recipe_titles: tuple[str, ...]


class ClosedShoppingListsService:
    def __init__(
        self,
        kitchens: KitchenRepository,
        carts: CartRepository,
        lists: ShoppingListRepository,
    ) -> None:
        self._kitchens = kitchens
        self._carts = carts
        self._lists = lists

    def list(self, ref: SessionRef, kitchen_id: UUID) -> tuple[ClosedListSummary, ...]:
        _member_kitchen(self._kitchens, ref, kitchen_id)
        return tuple(
            ClosedListSummary(s.id, s.closing_date, recipe_titles(s.items))
            for s in self._lists.closed(kitchen_id)
        )

    def get(self, ref: SessionRef, kitchen_id: UUID, list_id: UUID) -> ClosedListView:
        _member_kitchen(self._kitchens, ref, kitchen_id)
        saved = self._lists.closed_by_id(kitchen_id, list_id)
        if saved is None:
            raise ShoppingListNotFoundError()
        return _closed_view(saved, _missing(self._carts, [saved]))
