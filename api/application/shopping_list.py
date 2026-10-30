"""The kitchen's shopping list, built from its cart on every read (spec 023).

Read only: the list is derived data and is never stored, and a read never takes, renews or
releases the cart lock (FR-002, FR-014). Non-members and unknown kitchens get
KitchenNotFoundError (404); an archived kitchen can still be read.

Nothing is logged but outcomes and counts (constitution §4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from fractions import Fraction
from uuid import UUID

from domain.cart import (
    ScaledRecipe,
    ShoppingLine,
    ShoppingList,
    build_shopping_list,
    effective_people,
    scale_factor,
)
from domain.errors import KitchenNotFoundError

from application.kitchens import KitchenRepository
from application.ports import (
    CartDraftItem,
    CartRepository,
    EditLockRepository,
    IngredientLineReader,
    SessionRef,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _SeenCart:
    people: int | None
    items: tuple[CartDraftItem, ...]
    is_draft: bool


@dataclass(frozen=True, slots=True)
class ShoppingListView:
    # True when the cart has no recipes; the ui then shows nothing (FR-011).
    is_empty: bool
    shopping_list: ShoppingList


class GetShoppingListService:
    def __init__(
        self,
        kitchens: KitchenRepository,
        carts: CartRepository,
        locks: EditLockRepository,
        lines: IngredientLineReader,
    ) -> None:
        self._kitchens = kitchens
        self._carts = carts
        self._locks = locks
        self._lines = lines

    def execute(self, ref: SessionRef, kitchen_id: UUID) -> ShoppingListView:
        if (
            self._kitchens.get_kitchen(kitchen_id) is None
            or self._kitchens.get_membership(kitchen_id, ref.user_id) is None
        ):
            raise KitchenNotFoundError()

        seen = self._cart_seen_by(ref, kitchen_id)
        people = effective_people(seen.people, self._carts.member_count(kitchen_id))
        items = seen.items
        if not items:
            return ShoppingListView(is_empty=True, shopping_list=build_shopping_list([]))

        ids = list(dict.fromkeys(item.recipe_id for item in items))
        facts = self._carts.recipe_facts(ids)
        lines = self._lines.lines_for([rid for rid in ids if rid in facts])
        recipes: list[ScaledRecipe] = []
        for item in items:
            fact = facts.get(item.recipe_id)
            if fact is None or fact.kitchen_id != kitchen_id:
                continue
            recipes.append(
                ScaledRecipe(
                    recipe_id=fact.recipe_id,
                    title=fact.title,
                    factor=scale_factor(people, item.meals, fact.base_servings),
                    lines=tuple(
                        ShoppingLine(
                            name=line.name,
                            # Exact: a Decimal becomes a Fraction with no float in between.
                            quantity=None if line.quantity is None else Fraction(line.quantity),
                            unit=line.unit,
                            size=line.size,
                            vague_note=line.vague_note,
                        )
                        for line in lines.get(item.recipe_id, ())
                    ),
                )
            )
        result = build_shopping_list(recipes)
        logger.info(
            "shopping list outcome=built draft=%s recipes=%d lines=%d your_call=%d",
            seen.is_draft,
            len(recipes),
            len(result.lines),
            len(result.your_call),
        )
        return ShoppingListView(is_empty=False, shopping_list=result)

    def _cart_seen_by(self, ref: SessionRef, kitchen_id: UUID) -> _SeenCart:
        """My draft while my session holds the live cart lock, else the saved cart (FR-001).

        Only reads the lock: it is never taken, renewed or released here (FR-014).
        """
        holder = self._locks.cart_holder(kitchen_id)
        if holder is not None and holder.session_id == ref.session_id:
            draft = self._locks.cart_draft(kitchen_id, ref.session_id)
            if draft is not None:
                return _SeenCart(draft.people, draft.items, is_draft=True)
        saved = self._carts.read(kitchen_id)
        return _SeenCart(saved.people, saved.items, is_draft=False)
