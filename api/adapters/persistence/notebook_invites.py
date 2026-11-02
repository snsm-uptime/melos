"""SQLAlchemy notebook invites (spec 057)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from application.ports import NotebookInviteRecord
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from adapters.persistence.models import NotebookInviteModel
from adapters.persistence.token_claim import claim_single_use_email_token


def _record(row: NotebookInviteModel) -> NotebookInviteRecord:
    return NotebookInviteRecord(
        id=row.id,
        notebook_id=row.notebook_id,
        email=row.email,
        token_hash=row.token_hash,
        invited_by=row.invited_by,
        expires_at=row.expires_at,
        used_at=row.used_at,
    )


class SqlAlchemyNotebookInviteRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        invite_id: UUID,
        notebook_id: UUID,
        email: str,
        token_hash: str,
        invited_by: UUID,
        expires_at: datetime,
    ) -> None:
        self._session.add(
            NotebookInviteModel(
                id=invite_id,
                notebook_id=notebook_id,
                email=email,
                token_hash=token_hash,
                invited_by=invited_by,
                expires_at=expires_at,
            )
        )
        self._session.flush()

    def delete_open_for_email(self, notebook_id: UUID, email: str) -> None:
        self._session.execute(
            delete(NotebookInviteModel).where(
                NotebookInviteModel.notebook_id == notebook_id,
                NotebookInviteModel.email == email,
                NotebookInviteModel.used_at.is_(None),
            )
        )

    def list_unused(self, notebook_id: UUID) -> list[NotebookInviteRecord]:
        # expires_at, not created_at: a resent invite counts as sent when it was resent.
        rows = self._session.scalars(
            select(NotebookInviteModel)
            .where(
                NotebookInviteModel.notebook_id == notebook_id,
                NotebookInviteModel.used_at.is_(None),
            )
            .order_by(NotebookInviteModel.expires_at.desc(), NotebookInviteModel.id)
        ).all()
        return [_record(row) for row in rows]

    def get(self, notebook_id: UUID, invite_id: UUID) -> NotebookInviteRecord | None:
        row = self._session.scalar(
            select(NotebookInviteModel).where(
                NotebookInviteModel.id == invite_id,
                NotebookInviteModel.notebook_id == notebook_id,
            )
        )
        return _record(row) if row is not None else None

    def get_by_token_hash(self, token_hash: str) -> NotebookInviteRecord | None:
        row = self._session.scalar(
            select(NotebookInviteModel).where(NotebookInviteModel.token_hash == token_hash)
        )
        return _record(row) if row is not None else None

    def rotate(
        self, invite_id: UUID, *, token_hash: str, invited_by: UUID, expires_at: datetime
    ) -> None:
        self._session.execute(
            update(NotebookInviteModel)
            .where(NotebookInviteModel.id == invite_id)
            .values(token_hash=token_hash, invited_by=invited_by, expires_at=expires_at)
        )

    def delete(self, notebook_id: UUID, invite_id: UUID) -> bool:
        result = self._session.execute(
            delete(NotebookInviteModel).where(
                NotebookInviteModel.id == invite_id,
                NotebookInviteModel.notebook_id == notebook_id,
                NotebookInviteModel.used_at.is_(None),
            )
        )
        return bool(result.rowcount)

    def claim(self, invite_id: UUID, *, used_at: datetime) -> bool:
        return claim_single_use_email_token(
            self._session, NotebookInviteModel, invite_id, used_at=used_at
        )
