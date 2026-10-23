"""Read-only ingredient catalog per notebook (spec 055). Nothing writes it until S-019."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adapters.persistence.models import IngredientModel


class SqlAlchemyIngredientCatalogReader:
    def __init__(self, session: Session) -> None:
        self._session = session

    def names_for_notebook(self, notebook_id: UUID) -> list[str]:
        stmt = (
            select(IngredientModel.name)
            .where(IngredientModel.notebook_id == notebook_id)
            .order_by(IngredientModel.name)
        )
        return list(self._session.scalars(stmt).all())
