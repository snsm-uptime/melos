"""SQLAlchemy notebook repository, default-notebook pointer and committer (spec 056)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from application.ports import NotebookFacts
from domain.errors import PrincipalNotFoundError
from domain.notebook import Notebook
from sqlalchemy import Row, Select, and_, func, or_, select
from sqlalchemy.orm import Session, aliased

from adapters.persistence.models import (
    KitchenMembershipModel,
    KitchenModel,
    NotebookMembershipModel,
    NotebookModel,
    UserModel,
)


def _notebook(row: NotebookModel) -> Notebook:
    return Notebook(
        id=row.id,
        name=row.name,
        kitchen_id=row.kitchen_id,
        source_notebook_id=row.source_notebook_id,
        owner_user_id=row.owner_user_id,
    )


# The caller's own membership of a personal notebook.
_CallerMembership = aliased(NotebookMembershipModel)
# The owner membership of a personal notebook (its owner's alias is shown).
_OwnerMembership = aliased(NotebookMembershipModel)
_PersonalOwner = aliased(UserModel)
# The owner stored on a kitchen notebook (FR-002) and the kitchen's owner, its fallback.
_StoredOwner = aliased(UserModel)
_KitchenOwner = aliased(UserModel)
# The caller's kitchen membership (access to a kitchen notebook follows it).
_KitchenMember = aliased(KitchenMembershipModel)


def _facts_query(user_id: UUID) -> Select[Any]:
    default_id = (
        select(UserModel.default_notebook_id)
        .where(UserModel.id == user_id)
        .correlate(None)
        .scalar_subquery()
    )
    return (
        select(
            NotebookModel,
            _CallerMembership.role,
            _KitchenMember.user_id.is_not(None).label("in_kitchen"),
            func.coalesce(_PersonalOwner.alias, _StoredOwner.alias, _KitchenOwner.alias).label(
                "owner_alias"
            ),
            KitchenModel.is_archived,
            func.coalesce(NotebookModel.id == default_id, False).label("is_default"),
        )
        .outerjoin(KitchenModel, KitchenModel.id == NotebookModel.kitchen_id)
        .outerjoin(
            _CallerMembership,
            and_(
                _CallerMembership.notebook_id == NotebookModel.id,
                _CallerMembership.user_id == user_id,
            ),
        )
        .outerjoin(
            _KitchenMember,
            and_(
                _KitchenMember.kitchen_id == NotebookModel.kitchen_id,
                _KitchenMember.user_id == user_id,
            ),
        )
        .outerjoin(
            _OwnerMembership,
            and_(
                _OwnerMembership.notebook_id == NotebookModel.id,
                _OwnerMembership.role == "owner",
            ),
        )
        .outerjoin(_PersonalOwner, _PersonalOwner.id == _OwnerMembership.user_id)
        .outerjoin(_StoredOwner, _StoredOwner.id == NotebookModel.owner_user_id)
        .outerjoin(_KitchenOwner, _KitchenOwner.id == KitchenModel.owner_id)
    )


def _facts(row: Row[Any]) -> NotebookFacts:
    notebook_row, role, in_kitchen, owner_alias, is_archived, is_default = row
    return NotebookFacts(
        notebook=_notebook(notebook_row),
        role=role,
        in_kitchen=bool(in_kitchen),
        owner_alias=owner_alias,
        kitchen_is_archived=is_archived,
        is_default=bool(is_default),
    )


class SqlAlchemyNotebookRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, notebook_id: UUID) -> Notebook | None:
        row = self._session.get(NotebookModel, notebook_id)
        return _notebook(row) if row is not None else None

    def facts_for(self, user_id: UUID, notebook_id: UUID) -> NotebookFacts | None:
        row = self._session.execute(
            _facts_query(user_id).where(NotebookModel.id == notebook_id)
        ).first()
        return _facts(row) if row is not None else None

    def visible_facts_for(self, user_id: UUID) -> list[NotebookFacts]:
        rows = self._session.execute(
            _facts_query(user_id)
            .where(
                or_(
                    _CallerMembership.user_id.is_not(None),
                    _KitchenMember.user_id.is_not(None),
                )
            )
            .order_by(NotebookModel.created_at, NotebookModel.id)
        ).all()
        return [_facts(row) for row in rows]

    def kitchen_notebooks(self, kitchen_id: UUID) -> list[Notebook]:
        rows = self._session.scalars(
            select(NotebookModel)
            .where(NotebookModel.kitchen_id == kitchen_id)
            .order_by(NotebookModel.created_at, NotebookModel.id)
        ).all()
        return [_notebook(row) for row in rows]

    def personal_ids_for(self, user_id: UUID) -> list[UUID]:
        return list(
            self._session.scalars(
                select(NotebookModel.id)
                .join(
                    NotebookMembershipModel,
                    NotebookMembershipModel.notebook_id == NotebookModel.id,
                )
                .where(
                    NotebookMembershipModel.user_id == user_id,
                    NotebookModel.kitchen_id.is_(None),
                )
                .order_by(NotebookModel.created_at, NotebookModel.id)
            ).all()
        )

    def kitchen_ids_for(self, kitchen_id: UUID) -> list[UUID]:
        return list(
            self._session.scalars(
                select(NotebookModel.id)
                .where(NotebookModel.kitchen_id == kitchen_id)
                .order_by(NotebookModel.created_at, NotebookModel.id)
            ).all()
        )

    def user_kitchen_notebook(self, user_id: UUID, kitchen_id: UUID) -> UUID | None:
        """The kitchen notebook created by this user in this kitchen, or None."""
        return self._session.scalar(
            select(NotebookModel.id)
            .where(
                and_(
                    NotebookModel.kitchen_id == kitchen_id,
                    NotebookModel.owner_user_id == user_id,
                )
            )
            .order_by(NotebookModel.created_at, NotebookModel.id)
        )

    def create(self, notebook: Notebook) -> None:
        self._session.add(
            NotebookModel(
                id=notebook.id,
                name=notebook.name,
                kitchen_id=notebook.kitchen_id,
                source_notebook_id=notebook.source_notebook_id,
                owner_user_id=notebook.owner_user_id,
            )
        )
        self._session.flush()

    def add_owner(self, notebook_id: UUID, user_id: UUID) -> None:
        self._session.add(
            NotebookMembershipModel(notebook_id=notebook_id, user_id=user_id, role="owner")
        )
        self._session.flush()

    def lock_kitchen(self, kitchen_id: UUID) -> None:
        # FOR NO KEY UPDATE: serializes first creations in one kitchen without blocking
        # the FOR KEY SHARE locks that foreign-key inserts take (research R6).
        self._session.execute(
            select(KitchenModel.id)
            .where(KitchenModel.id == kitchen_id)
            .with_for_update(key_share=True)
        ).one()


class SqlAlchemyUserDefaultNotebook:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_update(self, user_id: UUID) -> UUID | None:
        row = self._session.execute(
            select(UserModel.id, UserModel.default_notebook_id)
            .where(UserModel.id == user_id)
            .with_for_update()
        ).first()
        if row is None:
            raise PrincipalNotFoundError()
        return row.default_notebook_id

    def set(self, user_id: UUID, notebook_id: UUID) -> None:
        row = self._session.get(UserModel, user_id)
        if row is None:
            raise PrincipalNotFoundError()
        row.default_notebook_id = notebook_id
        self._session.flush()


class SqlAlchemyTransactionCommitter:
    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        self._session.commit()
