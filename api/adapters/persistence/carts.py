"""The kitchen cart in Postgres (spec 022 research R1, R6)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import timedelta

from application.ports import (
    CartDraft,
    CartDraftItem,
    CartIngredientLine,
    CartRecipeFacts,
    SavedCart,
)
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from adapters.persistence.models import (
    CartItemModel,
    CartModel,
    NotebookModel,
    RecipeIngredientModel,
    RecipeModel,
)

_MICRO = timedelta(microseconds=1)


class SqlAlchemyCartRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _items(self, cart_id: uuid.UUID) -> tuple[CartDraftItem, ...]:
        rows = self._db.execute(
            select(CartItemModel.recipe_id, CartItemModel.servings)
            .where(CartItemModel.cart_id == cart_id)
            .order_by(CartItemModel.added_at, CartItemModel.recipe_id)
        ).all()
        return tuple(CartDraftItem(recipe_id=r, servings=s) for r, s in rows)

    def get_or_create_for_update(self, kitchen_id: uuid.UUID) -> SavedCart:
        self._db.execute(
            insert(CartModel)
            .values(kitchen_id=kitchen_id)
            .on_conflict_do_nothing(index_elements=["kitchen_id"])
        )
        row = self._db.scalar(
            select(CartModel).where(CartModel.kitchen_id == kitchen_id).with_for_update()
        )
        assert row is not None
        return SavedCart(kitchen_id, self._items(row.id))

    def read(self, kitchen_id: uuid.UUID) -> SavedCart:
        cart_id = self._db.scalar(select(CartModel.id).where(CartModel.kitchen_id == kitchen_id))
        if cart_id is None:
            return SavedCart(kitchen_id, ())
        return SavedCart(kitchen_id, self._items(cart_id))

    def recipe_facts(self, recipe_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, CartRecipeFacts]:
        if not recipe_ids:
            return {}
        rows = self._db.execute(
            select(
                RecipeModel.id,
                RecipeModel.title,
                NotebookModel.id,
                NotebookModel.name,
                RecipeModel.base_servings,
                NotebookModel.kitchen_id,
            )
            .join(NotebookModel, NotebookModel.id == RecipeModel.notebook_id)
            .where(RecipeModel.id.in_(list(recipe_ids)))
        ).all()
        return {row[0]: CartRecipeFacts(*row) for row in rows}

    def save(
        self, kitchen_id: uuid.UUID, draft: CartDraft, user_id: uuid.UUID
    ) -> tuple[uuid.UUID, ...]:
        cart_id = self._db.scalar(select(CartModel.id).where(CartModel.kitchen_id == kitchen_id))
        assert cart_id is not None
        before = dict(
            self._db.execute(
                select(CartItemModel.recipe_id, CartItemModel.added_at).where(
                    CartItemModel.cart_id == cart_id
                )
            ).all()
        )
        added = tuple(i.recipe_id for i in draft.items if i.recipe_id not in before)
        self._db.execute(delete(CartItemModel).where(CartItemModel.cart_id == cart_id))
        if draft.items:
            now = self._db.scalar(select(func.clock_timestamp()))
            self._db.execute(
                insert(CartItemModel),
                [
                    {
                        "cart_id": cart_id,
                        "recipe_id": item.recipe_id,
                        "servings": item.servings,
                        # Kept items keep their place; new ones go last in draft order.
                        "added_at": before.get(item.recipe_id) or now + (position * _MICRO),
                    }
                    for position, item in enumerate(draft.items)
                ],
            )
        self._db.execute(
            update(CartModel)
            .where(CartModel.id == cart_id)
            .values(updated_at=func.now(), updated_by=user_id)
        )
        if added:
            self._db.execute(
                update(RecipeModel)
                .where(RecipeModel.id.in_(added))
                .values(cart_add_count=RecipeModel.cart_add_count + 1)
            )
        return added


class SqlAlchemyIngredientLineReader:
    """Ingredient lines for the shopping list, all recipes in one query (spec 023 research R4)."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def lines_for(
        self, recipe_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[CartIngredientLine, ...]]:
        if not recipe_ids:
            return {}
        rows = self._db.execute(
            select(
                RecipeIngredientModel.recipe_id,
                RecipeIngredientModel.name,
                RecipeIngredientModel.quantity,
                RecipeIngredientModel.unit,
                RecipeIngredientModel.size,
                RecipeIngredientModel.vague_note,
            )
            .where(RecipeIngredientModel.recipe_id.in_(list(recipe_ids)))
            .order_by(RecipeIngredientModel.recipe_id, RecipeIngredientModel.position)
        ).all()
        grouped: dict[uuid.UUID, list[CartIngredientLine]] = {}
        for recipe_id, name, quantity, unit, size, vague_note in rows:
            grouped.setdefault(recipe_id, []).append(
                CartIngredientLine(name, quantity, unit, size, vague_note)
            )
        return {recipe_id: tuple(lines) for recipe_id, lines in grouped.items()}
