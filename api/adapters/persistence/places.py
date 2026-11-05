"""A person's places and their place per ingredient name in Postgres (spec 070 R5 to R8)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from uuid import UUID

from application.ports import PlaceSource
from domain.places import CustomPlace, PlaceRef
from sqlalchemy import delete, func, select, union, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased

from adapters.persistence.models import (
    IngredientModel,
    IngredientPlaceModel,
    KitchenMembershipModel,
    NotebookMembershipModel,
    NotebookModel,
    PlaceModel,
    UserModel,
)


class SqlAlchemyPlaceRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_custom(self, user_id: UUID) -> Sequence[CustomPlace]:
        rows = self._db.execute(
            select(PlaceModel.id, PlaceModel.name)
            .where(PlaceModel.user_id == user_id)
            .order_by(PlaceModel.name_key, PlaceModel.name)
        ).all()
        return [CustomPlace(r.id, r.name) for r in rows]

    def name_keys(self, user_id: UUID, *, except_id: UUID | None = None) -> set[str]:
        stmt = select(PlaceModel.name_key).where(PlaceModel.user_id == user_id)
        if except_id is not None:
            stmt = stmt.where(PlaceModel.id != except_id)
        return set(self._db.scalars(stmt).all())

    def add(self, user_id: UUID, name: str, name_key: str) -> CustomPlace:
        place_id = uuid.uuid4()
        self._db.execute(
            insert(PlaceModel).values(id=place_id, user_id=user_id, name=name, name_key=name_key)
        )
        return CustomPlace(place_id, name)

    def rename(self, user_id: UUID, place_id: UUID, name: str, name_key: str) -> CustomPlace | None:
        found = self._db.scalar(
            update(PlaceModel)
            .where(PlaceModel.id == place_id, PlaceModel.user_id == user_id)
            .values(name=name, name_key=name_key)
            .returning(PlaceModel.id)
        )
        return None if found is None else CustomPlace(place_id, name)

    def delete(self, user_id: UUID, place_id: UUID) -> bool:
        result = self._db.execute(
            delete(PlaceModel).where(PlaceModel.id == place_id, PlaceModel.user_id == user_id)
        )
        return result.rowcount > 0

    def choices(self, user_id: UUID) -> dict[str, PlaceRef]:
        rows = self._db.execute(
            select(
                IngredientPlaceModel.name,
                IngredientPlaceModel.default_key,
                PlaceModel.id,
                PlaceModel.name.label("place_name"),
            )
            .outerjoin(PlaceModel, PlaceModel.id == IngredientPlaceModel.place_id)
            .where(IngredientPlaceModel.user_id == user_id)
        ).all()
        return {
            r.name: (
                PlaceRef(key=r.default_key)
                if r.default_key is not None
                else PlaceRef(id=r.id, name=r.place_name)
            )
            for r in rows
        }

    def set_choice(self, user_id: UUID, name: str, place: PlaceRef) -> None:
        values = {"default_key": place.key, "place_id": None if place.key else place.id}
        self._db.execute(
            insert(IngredientPlaceModel)
            .values(user_id=user_id, name=name, **values)
            .on_conflict_do_update(
                index_elements=["user_id", "name"],
                set_={**values, "updated_at": func.now()},
            )
        )

    def catalog_names(self, user_id: UUID) -> Sequence[str]:
        personal = (
            select(IngredientModel.name)
            .join(NotebookModel, NotebookModel.id == IngredientModel.notebook_id)
            .join(NotebookMembershipModel, NotebookMembershipModel.notebook_id == NotebookModel.id)
            .where(NotebookMembershipModel.user_id == user_id, NotebookModel.kitchen_id.is_(None))
        )
        kitchen = (
            select(IngredientModel.name)
            .join(NotebookModel, NotebookModel.id == IngredientModel.notebook_id)
            .join(
                KitchenMembershipModel,
                KitchenMembershipModel.kitchen_id == NotebookModel.kitchen_id,
            )
            .where(KitchenMembershipModel.user_id == user_id)
        )
        chosen = select(IngredientPlaceModel.name).where(IngredientPlaceModel.user_id == user_id)
        return list(self._db.scalars(union(personal, kitchen, chosen)).all())

    def sources(self, user_id: UUID) -> Sequence[PlaceSource]:
        mine_k = aliased(KitchenMembershipModel)
        other_k = aliased(KitchenMembershipModel)
        mine_n = aliased(NotebookMembershipModel)
        other_n = aliased(NotebookMembershipModel)
        via_kitchen = (
            select(other_k.user_id)
            .join(mine_k, mine_k.kitchen_id == other_k.kitchen_id)
            .where(mine_k.user_id == user_id)
        )
        via_notebook = (
            select(other_n.user_id)
            .join(mine_n, mine_n.notebook_id == other_n.notebook_id)
            .where(mine_n.user_id == user_id)
        )
        ids = union(via_kitchen, via_notebook).subquery()
        rows = self._db.execute(
            select(UserModel.id, UserModel.alias)
            .where(UserModel.id.in_(select(ids.c[0])), UserModel.id != user_id)
            .order_by(UserModel.alias)
        ).all()
        return [PlaceSource(r.id, r.alias or "") for r in rows]

    def replace_with_copy(self, target_id: UUID, source_id: UUID) -> None:
        self._db.execute(
            delete(IngredientPlaceModel).where(IngredientPlaceModel.user_id == target_id)
        )
        self._db.execute(delete(PlaceModel).where(PlaceModel.user_id == target_id))
        places = self._db.execute(
            select(PlaceModel.id, PlaceModel.name, PlaceModel.name_key).where(
                PlaceModel.user_id == source_id
            )
        ).all()
        new_ids = {p.id: uuid.uuid4() for p in places}
        if places:
            self._db.execute(
                insert(PlaceModel),
                [
                    {
                        "id": new_ids[p.id],
                        "user_id": target_id,
                        "name": p.name,
                        "name_key": p.name_key,
                    }
                    for p in places
                ],
            )
        choices = self._db.execute(
            select(
                IngredientPlaceModel.name,
                IngredientPlaceModel.default_key,
                IngredientPlaceModel.place_id,
            ).where(IngredientPlaceModel.user_id == source_id)
        ).all()
        if choices:
            self._db.execute(
                insert(IngredientPlaceModel),
                [
                    {
                        "user_id": target_id,
                        "name": c.name,
                        "default_key": c.default_key,
                        "place_id": None if c.place_id is None else new_ids[c.place_id],
                    }
                    for c in choices
                ],
            )
