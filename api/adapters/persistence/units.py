"""SQLAlchemy adapter for the unit table (spec 055 R2, R3)."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from domain.recipe_draft import ALLOWED_UNITS
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from adapters.persistence.models import UnitModel

# The only statement that adds to user_references: a check constraint can't stop duplicates in
# an array, and ON CONFLICT re-checks the WHERE on the newest row, so a race counts once.
_ADD_USER = text(
    """
    INSERT INTO unit (name, user_references)
    VALUES (:name, ARRAY[CAST(:user_id AS uuid)])
    ON CONFLICT (name) DO UPDATE
      SET user_references = array_append(unit.user_references, CAST(:user_id AS uuid))
      WHERE NOT (CAST(:user_id AS uuid) = ANY (unit.user_references))
    """
)


class SqlAlchemyUnitRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def extras_for(self, user_id: UUID) -> list[str]:
        rows = self._session.scalars(
            select(UnitModel.name)
            .where(UnitModel.is_default | UnitModel.user_references.any(user_id))
            .where(UnitModel.name.not_in(ALLOWED_UNITS))
            .order_by(UnitModel.name)
        )
        return list(rows)

    def add_user(self, names: Sequence[str], user_id: UUID) -> None:
        # Sorted, so two saves that add the same words take the row locks in one order.
        for name in sorted(set(names)):
            self._session.execute(_ADD_USER, {"name": name, "user_id": user_id})
