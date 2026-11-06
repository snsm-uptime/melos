"""Co-members: people who share a kitchen or a notebook with the caller (spec 071, R-1, R-2).

One query over the existing membership tables. For each shared context, the shared time is the
later of the two join times; a person's shared time is the latest over all shared contexts.
"""

from __future__ import annotations

from uuid import UUID

from application.ports import CoMemberRecord
from sqlalchemy import Subquery, and_, func, select, union_all
from sqlalchemy.orm import Session, aliased

from adapters.persistence.models import KitchenMembershipModel, NotebookMembershipModel, UserModel


class SqlAlchemyCoMemberDirectory:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_co_members(self, user_id: UUID) -> list[CoMemberRecord]:
        peers = _peers(user_id)
        latest = (
            select(peers.c.user_id, func.max(peers.c.shared_at).label("shared_at"))
            .group_by(peers.c.user_id)
            .subquery("latest")
        )
        rows = self._session.execute(
            select(UserModel.id, UserModel.alias, latest.c.shared_at)
            .join(latest, latest.c.user_id == UserModel.id)
            .where(UserModel.alias.is_not(None))
            .order_by(
                latest.c.shared_at.desc().nulls_last(),
                func.lower(UserModel.alias),
                UserModel.id,
            )
        ).all()
        return [
            CoMemberRecord(user_id=row.id, alias=row.alias or "", shared_at=row.shared_at)
            for row in rows
        ]

    def is_co_member(self, user_id: UUID, other_id: UUID) -> bool:
        if other_id == user_id:
            return False
        peers = _peers(user_id)
        found = self._session.execute(
            select(peers.c.user_id).where(peers.c.user_id == other_id).limit(1)
        ).first()
        return found is not None


def _peers(user_id: UUID) -> Subquery:
    """(user_id, shared_at) for every person sharing a kitchen or notebook with the caller."""
    my_kitchen = aliased(KitchenMembershipModel, name="my_kitchen")
    their_kitchen = aliased(KitchenMembershipModel, name="their_kitchen")
    kitchen_peers = (
        select(
            their_kitchen.user_id.label("user_id"),
            func.greatest(my_kitchen.created_at, their_kitchen.created_at).label("shared_at"),
        )
        .select_from(their_kitchen)
        .join(
            my_kitchen,
            and_(
                my_kitchen.kitchen_id == their_kitchen.kitchen_id,
                my_kitchen.user_id == user_id,
            ),
        )
        .where(their_kitchen.user_id != user_id)
    )
    my_notebook = aliased(NotebookMembershipModel, name="my_notebook")
    their_notebook = aliased(NotebookMembershipModel, name="their_notebook")
    notebook_peers = (
        select(
            their_notebook.user_id.label("user_id"),
            func.greatest(my_notebook.created_at, their_notebook.created_at).label("shared_at"),
        )
        .select_from(their_notebook)
        .join(
            my_notebook,
            and_(
                my_notebook.notebook_id == their_notebook.notebook_id,
                my_notebook.user_id == user_id,
            ),
        )
        .where(their_notebook.user_id != user_id)
    )
    return union_all(kitchen_peers, notebook_peers).subquery("peers")
