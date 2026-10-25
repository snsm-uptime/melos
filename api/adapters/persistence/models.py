"""SQLAlchemy ORM models for users, kitchens, memberships, sessions, and notebooks."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from adapters.persistence.base import Base


class UserModel(Base):
    __tablename__ = "users"
    # Aliases are compared case-insensitively; the DB owns that invariant.
    __table_args__ = (Index("uq_users_alias_lower", text("lower(alias)"), unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    alias: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Base64 data URI (data:image/png|jpeg;base64,...) — no separate media storage.
    photo_base64: Mapped[str | None] = mapped_column(Text, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    theme: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_opened_kitchen_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kitchens.id", ondelete="SET NULL"), nullable=True
    )
    # Null until the member first asks for their default notebook, and again
    # after it is deleted. users and notebook reference each other: use_alter.
    default_notebook_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notebook.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owned_kitchens: Mapped[list[KitchenModel]] = relationship(
        back_populates="owner",
        foreign_keys="KitchenModel.owner_id",
    )
    memberships: Mapped[list[KitchenMembershipModel]] = relationship(back_populates="user")
    sessions: Mapped[list[SessionModel]] = relationship(back_populates="user")
    password_reset_tokens: Mapped[list[PasswordResetTokenModel]] = relationship(
        back_populates="user"
    )
    email_verification_tokens: Mapped[list[EmailVerificationTokenModel]] = relationship(
        back_populates="user"
    )
    sent_kitchen_invites: Mapped[list[KitchenInviteTokenModel]] = relationship(
        back_populates="inviter",
        foreign_keys="KitchenInviteTokenModel.inviter_user_id",
    )


class KitchenModel(Base):
    __tablename__ = "kitchens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    content_language: Mapped[str] = mapped_column(String(2), nullable=False, server_default="en")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner: Mapped[UserModel] = relationship(
        back_populates="owned_kitchens",
        foreign_keys=[owner_id],
    )
    memberships: Mapped[list[KitchenMembershipModel]] = relationship(
        back_populates="kitchen",
        cascade="all, delete-orphan",
    )
    invite_tokens: Mapped[list[KitchenInviteTokenModel]] = relationship(
        back_populates="kitchen",
        cascade="all, delete-orphan",
    )


class KitchenMembershipModel(Base):
    __tablename__ = "kitchen_memberships"
    __table_args__ = (UniqueConstraint("kitchen_id", "user_id", name="uq_kitchen_membership"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="owner")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    kitchen: Mapped[KitchenModel] = relationship(back_populates="memberships")
    user: Mapped[UserModel] = relationship(back_populates="memberships")


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[UserModel] = relationship(back_populates="sessions")


class PasswordResetTokenModel(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[UserModel] = relationship(back_populates="password_reset_tokens")


class EmailVerificationTokenModel(Base):
    __tablename__ = "email_verification_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[UserModel] = relationship(back_populates="email_verification_tokens")


class KitchenInviteTokenModel(Base):
    __tablename__ = "kitchen_invite_tokens"
    __table_args__ = (Index("ix_kitchen_invite_tokens_kitchen_id_email", "kitchen_id", "email"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    inviter_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    locale: Mapped[str] = mapped_column(String(8), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    kitchen: Mapped[KitchenModel] = relationship(back_populates="invite_tokens")
    inviter: Mapped[UserModel] = relationship(
        back_populates="sent_kitchen_invites",
        foreign_keys=[inviter_user_id],
    )


class NotebookModel(Base):
    __tablename__ = "notebook"
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="ck_notebook_name_not_blank"),
        CheckConstraint(
            "source_notebook_id IS NULL OR kitchen_id IS NOT NULL",
            name="ck_notebook_source_is_kitchen",
        ),
        CheckConstraint("source_notebook_id <> id", name="ck_notebook_source_not_self"),
        CheckConstraint(
            "owner_user_id IS NULL OR kitchen_id IS NOT NULL",
            name="ck_notebook_owner_is_kitchen",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # Set: a kitchen notebook. Null: a personal notebook. Not unique: a kitchen can have several.
    kitchen_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kitchens.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # The member who created a kitchen notebook (FR-002). Personal notebooks keep their owner
    # in notebook_membership instead.
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Origin label of a snapshot (S-034). Never set by this feature.
    source_notebook_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notebook.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class NotebookMembershipModel(Base):
    """A person's place in a personal notebook. Kitchen notebooks have no rows here."""

    __tablename__ = "notebook_membership"
    __table_args__ = (
        CheckConstraint("role IN ('owner', 'member')", name="ck_notebook_membership_role"),
        Index(
            "uq_notebook_one_owner",
            "notebook_id",
            unique=True,
            postgresql_where=text("role = 'owner'"),
        ),
    )

    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notebook.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class IngredientModel(Base):
    __tablename__ = "ingredient"
    __table_args__ = (UniqueConstraint("notebook_id", "name", name="uq_ingredient_notebook_name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebook.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
