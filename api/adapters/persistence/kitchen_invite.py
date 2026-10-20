"""SQLAlchemy repository for kitchen invite tokens (Story 2.3)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from application.kitchen_invite import KitchenInviteTokenRecord
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from adapters.persistence.models import KitchenInviteTokenModel


class SqlAlchemyKitchenInviteTokenRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def invalidate_outstanding_for_kitchen_email(self, kitchen_id: UUID, email: str) -> None:
        now = datetime.now(UTC)
        self._session.execute(
            update(KitchenInviteTokenModel)
            .where(
                KitchenInviteTokenModel.kitchen_id == kitchen_id,
                KitchenInviteTokenModel.email == email,
                KitchenInviteTokenModel.used_at.is_(None),
            )
            .values(used_at=now)
        )

    def create_token(
        self,
        *,
        token_id: UUID,
        kitchen_id: UUID,
        email: str,
        token_hash: str,
        inviter_user_id: UUID,
        locale: str,
        expires_at: datetime,
    ) -> None:
        self._session.add(
            KitchenInviteTokenModel(
                id=token_id,
                kitchen_id=kitchen_id,
                email=email,
                token_hash=token_hash,
                inviter_user_id=inviter_user_id,
                locale=locale,
                expires_at=expires_at,
            )
        )
        self._session.flush()

    def get_by_token_hash(self, token_hash: str) -> KitchenInviteTokenRecord | None:
        row = self._session.scalars(
            select(KitchenInviteTokenModel).where(KitchenInviteTokenModel.token_hash == token_hash)
        ).first()
        if row is None:
            return None
        return KitchenInviteTokenRecord(
            id=row.id,
            kitchen_id=row.kitchen_id,
            email=row.email,
            token_hash=row.token_hash,
            inviter_user_id=row.inviter_user_id,
            locale=row.locale,
            expires_at=row.expires_at,
            used_at=row.used_at,
        )

    def claim_token(self, token_id: UUID, *, used_at: datetime) -> bool:
        from adapters.persistence.token_claim import claim_single_use_email_token

        return claim_single_use_email_token(
            self._session,
            KitchenInviteTokenModel,
            token_id,
            used_at=used_at,
        )
