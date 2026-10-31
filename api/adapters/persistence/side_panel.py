"""The side panel's reads and the default kitchen write in Postgres (spec 064)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from domain.default_kitchen import MemberKitchen
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from adapters.persistence.models import (
    KitchenMembershipModel,
    KitchenModel,
    NotebookMembershipModel,
    NotebookModel,
    RecipeModel,
    UserModel,
)


class SqlAlchemySidePanelRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def stored_default_kitchen(self, user_id: uuid.UUID) -> uuid.UUID | None:
        return self._db.scalar(select(UserModel.default_kitchen_id).where(UserModel.id == user_id))

    def member_kitchens(self, user_id: uuid.UUID) -> Sequence[MemberKitchen]:
        rows = self._db.execute(
            select(
                KitchenModel.id,
                KitchenModel.is_archived,
                KitchenMembershipModel.role,
                KitchenModel.created_at,
                KitchenMembershipModel.created_at,
            )
            .join(KitchenMembershipModel, KitchenMembershipModel.kitchen_id == KitchenModel.id)
            .where(KitchenMembershipModel.user_id == user_id)
        ).all()
        return [
            MemberKitchen(
                id=kitchen_id,
                is_archived=is_archived,
                is_owner=role == "owner",
                created_at=created_at,
                joined_at=joined_at,
            )
            for kitchen_id, is_archived, role, created_at, joined_at in rows
        ]

    def set_default_kitchen(self, user_id: uuid.UUID, kitchen_id: uuid.UUID | None) -> None:
        self._db.execute(
            update(UserModel).where(UserModel.id == user_id).values(default_kitchen_id=kitchen_id)
        )

    def count_notebooks(self, user_id: uuid.UUID) -> int:
        """The personal notebooks the Notebooks page lists."""
        return self._db.scalar(
            select(func.count())
            .select_from(NotebookMembershipModel)
            .where(NotebookMembershipModel.user_id == user_id)
        ) or 0

    def count_recipes_added(self, user_id: uuid.UUID) -> int:
        """Archived kitchens count: they stay reachable through the archive toggle (research R3)."""
        kitchens = select(KitchenMembershipModel.kitchen_id).where(
            KitchenMembershipModel.user_id == user_id
        )
        notebooks = select(NotebookMembershipModel.notebook_id).where(
            NotebookMembershipModel.user_id == user_id
        )
        return self._db.scalar(
            select(func.count())
            .select_from(RecipeModel)
            .join(NotebookModel, NotebookModel.id == RecipeModel.notebook_id)
            .where(
                RecipeModel.author_id == user_id,
                or_(NotebookModel.kitchen_id.in_(kitchens), NotebookModel.id.in_(notebooks)),
            )
        ) or 0
