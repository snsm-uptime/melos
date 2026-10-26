"""SQLAlchemy ingredient catalog per notebook and the personal catalog (spec 056, research R9)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Select, literal, select
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from adapters.persistence.models import (
    IngredientModel,
    NotebookMembershipModel,
    NotebookModel,
)


def _personal_names(user_id: UUID) -> Select[Any]:
    """Names in the personal notebooks the user owns or is a member of, never kitchen notebooks."""
    return (
        select(IngredientModel.name)
        .join(NotebookModel, NotebookModel.id == IngredientModel.notebook_id)
        .join(
            NotebookMembershipModel,
            NotebookMembershipModel.notebook_id == NotebookModel.id,
        )
        .where(
            NotebookMembershipModel.user_id == user_id,
            NotebookModel.kitchen_id.is_(None),
        )
    )


class SqlAlchemyIngredientCatalog:
    def __init__(self, session: Session) -> None:
        self._session = session

    def names_for_notebook(self, notebook_id: UUID) -> list[str]:
        stmt = (
            select(IngredientModel.name)
            .where(IngredientModel.notebook_id == notebook_id)
            .order_by(IngredientModel.name)
        )
        return list(self._session.scalars(stmt).all())

    def names_for_person(self, user_id: UUID) -> list[str]:
        stmt = _personal_names(user_id).distinct().order_by(IngredientModel.name)
        return list(self._session.scalars(stmt).all())

    def seed_from_person(self, notebook_id: UUID, user_id: UUID) -> None:
        names = _personal_names(user_id).distinct().subquery()
        source = select(literal(notebook_id, PgUUID(as_uuid=True)), names.c.name)
        self._session.execute(
            insert(IngredientModel)
            .from_select(["notebook_id", "name"], source)
            .on_conflict_do_nothing(index_elements=["notebook_id", "name"])
        )
