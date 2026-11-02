"""The cart activity log in Postgres (spec 055 R18)."""

from __future__ import annotations

from uuid import UUID

from domain.cart import CartAction
from sqlalchemy.orm import Session

from adapters.persistence.models import CartActivityModel


class SqlAlchemyCartActivityLog:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(self, user_id: UUID, action: CartAction) -> None:
        self._session.add(CartActivityModel(user_id=user_id, action=action))
