"""Saved shopping lists in Postgres (spec 025 research R2, R3, R7)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from uuid import UUID

from domain.cart import Amount, RecipeRef
from domain.shopping_list import SavedLine, SavedList
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from adapters.persistence.models import ShoppingListItemModel, ShoppingListModel


def _row(list_id: uuid.UUID, item: SavedLine, position: int) -> dict[str, object]:
    return {
        "id": uuid.uuid4(),
        "shopping_list_id": list_id,
        "origin": item.origin,
        "section": item.section,
        "name": item.name,
        "kind": item.kind,
        "size": item.size,
        "amounts": [{"quantity": a.quantity, "unit": a.unit} for a in item.amounts],
        "notes": list(item.notes),
        "recipes": [{"recipe_id": str(r.recipe_id), "title": r.title} for r in item.recipes],
        "position": position,
    }


def _line(row: ShoppingListItemModel) -> SavedLine:
    return SavedLine(
        origin=row.origin,  # type: ignore[arg-type]
        section=row.section,  # type: ignore[arg-type]
        name=row.name,
        kind=row.kind,  # type: ignore[arg-type]
        size=row.size,
        amounts=tuple(Amount(a["quantity"], a["unit"]) for a in row.amounts),
        notes=tuple(row.notes),
        recipes=tuple(RecipeRef(UUID(r["recipe_id"]), r["title"]) for r in row.recipes),
        id=row.id,
    )


class SqlAlchemyShoppingListRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _with_items(self, rows: Sequence[ShoppingListModel]) -> tuple[SavedList, ...]:
        if not rows:
            return ()
        items = self._db.scalars(
            select(ShoppingListItemModel)
            .where(ShoppingListItemModel.shopping_list_id.in_([r.id for r in rows]))
            # "cart" sorts before "hand", the order the list is shown in.
            .order_by(ShoppingListItemModel.origin, ShoppingListItemModel.position)
        ).all()
        by_list: dict[uuid.UUID, list[SavedLine]] = {}
        for item in items:
            by_list.setdefault(item.shopping_list_id, []).append(_line(item))
        return tuple(
            SavedList(
                r.id, r.kitchen_id, r.closing_date, r.created_at, tuple(by_list.get(r.id, ()))
            )
            for r in rows
        )

    def active(self, kitchen_id: UUID) -> SavedList | None:
        row = self._db.scalar(
            select(ShoppingListModel).where(
                ShoppingListModel.kitchen_id == kitchen_id,
                ShoppingListModel.closing_date.is_(None),
            )
        )
        return None if row is None else self._with_items([row])[0]

    def get_or_create_active(self, kitchen_id: UUID) -> SavedList:
        self._db.execute(
            insert(ShoppingListModel)
            .values(id=uuid.uuid4(), kitchen_id=kitchen_id, created_at=func.clock_timestamp())
            .on_conflict_do_nothing(
                index_elements=["kitchen_id"], index_where=text("closing_date IS NULL")
            )
        )
        active = self.active(kitchen_id)
        assert active is not None
        return active

    def replace_cart_lines(self, list_id: UUID, lines: Sequence[SavedLine]) -> None:
        self._db.execute(
            delete(ShoppingListItemModel).where(
                ShoppingListItemModel.shopping_list_id == list_id,
                ShoppingListItemModel.origin == "cart",
            )
        )
        if lines:
            self._db.execute(
                insert(ShoppingListItemModel),
                [_row(list_id, line, position) for position, line in enumerate(lines)],
            )

    def add_item(self, list_id: UUID, item: SavedLine) -> None:
        last = self._db.scalar(
            select(func.max(ShoppingListItemModel.position)).where(
                ShoppingListItemModel.shopping_list_id == list_id,
                ShoppingListItemModel.origin == item.origin,
            )
        )
        position = 0 if last is None else last + 1
        self._db.execute(insert(ShoppingListItemModel).values(**_row(list_id, item, position)))

    def remove_hand_item(self, list_id: UUID, item_id: UUID) -> bool:
        result = self._db.execute(
            delete(ShoppingListItemModel).where(
                ShoppingListItemModel.id == item_id,
                ShoppingListItemModel.shopping_list_id == list_id,
                ShoppingListItemModel.origin == "hand",
            )
        )
        return result.rowcount > 0

    def close(self, list_id: UUID, closing_date: date) -> bool:
        result = self._db.execute(
            update(ShoppingListModel)
            .where(ShoppingListModel.id == list_id, ShoppingListModel.closing_date.is_(None))
            .values(closing_date=closing_date)
        )
        return result.rowcount > 0

    def closed(self, kitchen_id: UUID) -> tuple[SavedList, ...]:
        rows = self._db.scalars(
            select(ShoppingListModel)
            .where(
                ShoppingListModel.kitchen_id == kitchen_id,
                ShoppingListModel.closing_date.is_not(None),
            )
            .order_by(ShoppingListModel.closing_date.desc(), ShoppingListModel.created_at.desc())
        ).all()
        return self._with_items(rows)

    def closed_by_id(self, kitchen_id: UUID, list_id: UUID) -> SavedList | None:
        row = self._db.scalar(
            select(ShoppingListModel).where(
                ShoppingListModel.id == list_id,
                ShoppingListModel.kitchen_id == kitchen_id,
                ShoppingListModel.closing_date.is_not(None),
            )
        )
        return None if row is None else self._with_items([row])[0]
