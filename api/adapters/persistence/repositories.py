# Reused from finance-dashboard/api/adapters/persistence/repositories.py
"""SQLAlchemy signup / auth user / kitchen repositories."""

from __future__ import annotations

from uuid import UUID

from application.kitchens import (
    KitchenMemberLabel,
    KitchenMembershipSummary,
    KitchenMemberView,
    KitchenRecord,
    MembershipRecord,
)
from application.ports import (
    KitchenAccessGrant,
    NewKitchenRecord,
    NewMembershipRecord,
    NewUserRecord,
    UserPreferencesRecord,
)
from application.signin import AuthUserRecord
from domain.errors import (
    AliasAlreadySetError,
    AliasTakenError,
    DuplicateEmailError,
    KitchenNotFoundError,
    KitchenWriteError,
    NotKitchenMemberError,
    PrincipalNotFoundError,
)
from sqlalchemy import case, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from adapters.persistence.models import (
    KitchenMembershipModel,
    KitchenModel,
    UserModel,
)


def _preferences_record(row: UserModel) -> UserPreferencesRecord:
    return UserPreferencesRecord(
        id=row.id,
        email=row.email,
        language=row.language,
        theme=row.theme,
        last_opened_kitchen_id=row.last_opened_kitchen_id,
        alias=row.alias,
        photo_base64=row.photo_base64,
    )


class SqlAlchemySignupRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def email_exists(self, email: str) -> bool:
        stmt = select(UserModel.id).where(UserModel.email == email).limit(1)
        return self._session.scalar(stmt) is not None

    def create_user_with_personal_kitchen(
        self,
        *,
        user: NewUserRecord,
        personal_kitchen: NewKitchenRecord,
        membership: NewMembershipRecord,
    ) -> None:
        try:
            with self._session.begin_nested():
                self._session.add(
                    UserModel(
                        id=user.id,
                        email=user.email,
                        password_hash=user.password_hash,
                    )
                )
                self._session.flush()
        except IntegrityError as exc:
            raise DuplicateEmailError("An account with this email already exists.") from exc
        self._session.add(
            KitchenModel(
                id=personal_kitchen.id,
                name=personal_kitchen.name,
                owner_id=personal_kitchen.owner_id,
            )
        )
        self._session.flush()
        self._session.add(
            KitchenMembershipModel(
                id=membership.id,
                kitchen_id=membership.kitchen_id,
                user_id=membership.user_id,
                role=membership.role,
            )
        )


class SqlAlchemyAuthUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> AuthUserRecord | None:
        row = self._session.scalar(select(UserModel).where(UserModel.email == email).limit(1))
        if row is None:
            return None
        return AuthUserRecord(id=row.id, email=row.email, password_hash=row.password_hash)

    def get_by_id(self, user_id: UUID) -> AuthUserRecord | None:
        row = self._session.get(UserModel, user_id)
        if row is None:
            return None
        return AuthUserRecord(id=row.id, email=row.email, password_hash=row.password_hash)

    def get_preferences(self, user_id: UUID) -> UserPreferencesRecord | None:
        row = self._session.get(UserModel, user_id)
        if row is None:
            return None
        return _preferences_record(row)

    def claim_alias(self, user_id: UUID, alias: str) -> UserPreferencesRecord:
        """Set-once claim; row lock + lower(alias) unique index arbitrate races."""
        row = self._session.scalar(
            select(UserModel).where(UserModel.id == user_id).with_for_update()
        )
        if row is None:
            raise PrincipalNotFoundError()
        if row.alias:
            raise AliasAlreadySetError()
        try:
            # Assign inside the savepoint — begin_nested() autoflushes pending
            # state, which would push the UPDATE outside the savepoint and
            # poison the outer transaction when the unique index rejects it.
            with self._session.begin_nested():
                row.alias = alias
                self._session.flush()
        except IntegrityError as exc:
            raise AliasTakenError() from exc
        return _preferences_record(row)

    def update_preferences(
        self,
        user_id: UUID,
        *,
        language: str | None = None,
        theme: str | None = None,
        last_opened_kitchen_id: UUID | None = None,
        clear_last_opened_kitchen_id: bool = False,
        photo_base64: str | None = None,
        clear_photo: bool = False,
    ) -> UserPreferencesRecord:
        row = self._session.get(UserModel, user_id)
        if row is None:
            raise PrincipalNotFoundError()
        if language is not None:
            row.language = language
        if theme is not None:
            row.theme = theme
        if clear_last_opened_kitchen_id:
            row.last_opened_kitchen_id = None
        elif last_opened_kitchen_id is not None:
            row.last_opened_kitchen_id = last_opened_kitchen_id
        if clear_photo:
            row.photo_base64 = None
        elif photo_base64 is not None:
            row.photo_base64 = photo_base64
        try:
            self._session.flush()
        except IntegrityError as exc:
            if last_opened_kitchen_id is not None:
                raise NotKitchenMemberError() from exc
            raise
        return _preferences_record(row)


class SqlAlchemyKitchenRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_owned_kitchen(
        self,
        *,
        owned_kitchen: NewKitchenRecord,
        membership: NewMembershipRecord,
    ) -> None:
        try:
            with self._session.begin_nested():
                self._session.add(
                    KitchenModel(
                        id=owned_kitchen.id,
                        name=owned_kitchen.name,
                        owner_id=owned_kitchen.owner_id,
                    )
                )
                self._session.flush()
                self._session.add(
                    KitchenMembershipModel(
                        id=membership.id,
                        kitchen_id=membership.kitchen_id,
                        user_id=membership.user_id,
                        role=membership.role,
                    )
                )
                self._session.flush()
        except IntegrityError as exc:
            raise KitchenWriteError() from exc

    def get_kitchen(self, kitchen_id: UUID) -> KitchenRecord | None:
        row = self._session.get(KitchenModel, kitchen_id)
        if row is None:
            return None
        return KitchenRecord(
            id=row.id, name=row.name, owner_id=row.owner_id, is_archived=row.is_archived
        )

    def get_membership(self, kitchen_id: UUID, user_id: UUID) -> MembershipRecord | None:
        row = self._session.scalar(
            select(KitchenMembershipModel)
            .where(
                KitchenMembershipModel.kitchen_id == kitchen_id,
                KitchenMembershipModel.user_id == user_id,
            )
            .limit(1)
        )
        if row is None:
            return None
        return MembershipRecord(kitchen_id=row.kitchen_id, user_id=row.user_id, role=row.role)

    def add_membership(self, membership: NewMembershipRecord) -> None:
        try:
            with self._session.begin_nested():
                self._session.add(
                    KitchenMembershipModel(
                        id=membership.id,
                        kitchen_id=membership.kitchen_id,
                        user_id=membership.user_id,
                        role=membership.role,
                    )
                )
                self._session.flush()
        except IntegrityError as exc:
            raise KitchenWriteError() from exc

    def update_kitchen_name(self, kitchen_id: UUID, name: str) -> KitchenRecord:
        row = self._session.get(KitchenModel, kitchen_id)
        if row is None:
            raise KitchenNotFoundError()
        row.name = name
        self._session.flush()
        return KitchenRecord(
            id=row.id, name=row.name, owner_id=row.owner_id, is_archived=row.is_archived
        )

    def delete_kitchen(self, kitchen_id: UUID) -> None:
        row = self._session.get(KitchenModel, kitchen_id)
        if row is None:
            raise KitchenNotFoundError()
        self._session.delete(row)
        self._session.flush()

    def archive_kitchen(self, kitchen_id: UUID) -> None:
        row = self._session.get(KitchenModel, kitchen_id)
        if row is None:
            raise KitchenNotFoundError()
        row.is_archived = True
        self._session.flush()

    def unarchive_kitchen(self, kitchen_id: UUID) -> None:
        row = self._session.get(KitchenModel, kitchen_id)
        if row is None:
            raise KitchenNotFoundError()
        row.is_archived = False
        self._session.flush()

    def hide_kitchen_for_member(self, kitchen_id: UUID, user_id: UUID) -> None:
        row = self._session.scalar(
            select(KitchenMembershipModel).where(
                KitchenMembershipModel.kitchen_id == kitchen_id,
                KitchenMembershipModel.user_id == user_id,
            )
        )
        if row is None:
            raise KitchenNotFoundError()
        row.is_hidden = True
        self._session.flush()

    def unhide_kitchen_for_member(self, kitchen_id: UUID, user_id: UUID) -> None:
        row = self._session.scalar(
            select(KitchenMembershipModel).where(
                KitchenMembershipModel.kitchen_id == kitchen_id,
                KitchenMembershipModel.user_id == user_id,
            )
        )
        if row is None:
            raise KitchenNotFoundError()
        row.is_hidden = False
        self._session.flush()

    def kitchens_for_user(
        self, user_id: UUID, *, archived: bool = False
    ) -> list[KitchenMembershipSummary]:
        # Effective archived state is per-row. The owner's own copy follows
        # kitchens.is_archived alone. A non-owner member's follows the OR of
        # both: the owner archiving still moves it to everyone's archived
        # view (pre-existing Story 9.1 behavior, unchanged), and a member's
        # own personal hide is an *additional*, independent reason for it
        # to appear archived in their view only — never the inverse (a
        # member can't unhide their way out of an owner's archive).
        effective_archived = case(
            (KitchenModel.owner_id == user_id, KitchenModel.is_archived),
            else_=KitchenModel.is_archived | KitchenMembershipModel.is_hidden,
        )
        stmt = (
            select(KitchenModel, KitchenMembershipModel.role)
            .join(
                KitchenMembershipModel,
                KitchenMembershipModel.kitchen_id == KitchenModel.id,
            )
            .where(
                KitchenMembershipModel.user_id == user_id,
                effective_archived == archived,
            )
            .order_by(KitchenModel.created_at.asc())
        )
        rows = self._session.execute(stmt).all()
        kitchen_ids = [kitchen.id for kitchen, _ in rows]
        members_by_kitchen: dict[UUID, list[KitchenMemberLabel]] = {lid: [] for lid in kitchen_ids}
        if kitchen_ids:
            member_stmt = (
                select(
                    KitchenMembershipModel.kitchen_id,
                    KitchenMembershipModel.user_id,
                    UserModel.alias,
                    UserModel.photo_base64,
                )
                .join(UserModel, UserModel.id == KitchenMembershipModel.user_id)
                .where(KitchenMembershipModel.kitchen_id.in_(kitchen_ids))
                .order_by(KitchenMembershipModel.created_at.asc())
            )
            for kitchen_id, member_id, alias, photo_base64 in self._session.execute(
                member_stmt
            ).all():
                members_by_kitchen[kitchen_id].append(
                    KitchenMemberLabel(user_id=member_id, alias=alias, photo_base64=photo_base64)
                )
        return [
            KitchenMembershipSummary(
                id=kitchen.id,
                name=kitchen.name,
                owner_id=kitchen.owner_id,
                role=role,
                members=tuple(members_by_kitchen.get(kitchen.id, ())),
            )
            for kitchen, role in rows
        ]

    def get_kitchen_with_grant(self, grant: KitchenAccessGrant, kitchen_id: UUID) -> KitchenRecord:
        from application.kitchen_access import assert_grant_kitchen_id

        assert_grant_kitchen_id(grant, kitchen_id)
        row = self._session.get(KitchenModel, kitchen_id)
        if row is None:
            raise KitchenNotFoundError()
        return KitchenRecord(
            id=row.id, name=row.name, owner_id=row.owner_id, is_archived=row.is_archived
        )

    def kitchen_members_with_alias(self, kitchen_id: UUID) -> list[KitchenMemberView]:
        """Roster labels are aliases — email is an identity surface, never a label."""
        stmt = (
            select(KitchenMembershipModel.user_id, UserModel.alias, UserModel.photo_base64)
            .join(UserModel, UserModel.id == KitchenMembershipModel.user_id)
            .where(KitchenMembershipModel.kitchen_id == kitchen_id)
            .order_by(KitchenMembershipModel.created_at.asc())
        )
        return [
            KitchenMemberView(user_id=user_id, alias=alias, photo_base64=photo_base64)
            for user_id, alias, photo_base64 in self._session.execute(stmt).all()
        ]
