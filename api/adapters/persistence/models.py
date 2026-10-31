"""SQLAlchemy ORM models for users, kitchens, memberships, sessions, and notebooks."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
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
    # Origin label of a snapshot (S-035). Never set by this feature.
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


UNITS_SQL = "('g', 'kg', 'oz', 'lb', 'ml', 'l', 'cup', 'tbsp', 'tsp', 'unit')"


class SourceModel(Base):
    """Where a recipe came from (spec 020). Deleting a source keeps the recipe."""

    __tablename__ = "source"
    __table_args__ = (
        CheckConstraint("type IN ('text', 'url', 'photo')", name="ck_source_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RecipeModel(Base):
    """A saved recipe, in exactly one notebook (spec 020)."""

    __tablename__ = "recipe"
    __table_args__ = (
        CheckConstraint("btrim(title) <> ''", name="ck_recipe_title_not_blank"),
        CheckConstraint("base_servings >= 1", name="ck_recipe_base_servings"),
        CheckConstraint("cart_add_count >= 0", name="ck_recipe_cart_add_count"),
        Index(
            "uq_recipe_author_save_key",
            "author_id",
            "save_key",
            unique=True,
            postgresql_where=text("save_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notebook.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Null reads "unknown" once the author's account is gone.
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    base_servings: Mapped[int] = mapped_column(Integer, nullable=False)
    servings_estimated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    # The draft key the ui makes, so a repeated Save returns this recipe (research R5).
    save_key: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Additions to a kitchen's cart, raised by each cart save; never lowered (spec 022 FR-013).
    cart_add_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class RecipeIngredientModel(Base):
    __tablename__ = "recipe_ingredient"
    __table_args__ = (
        UniqueConstraint("recipe_id", "position", name="uq_recipe_ingredient_position"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_recipe_ingredient_quantity"),
        CheckConstraint(
            f"unit IS NULL OR unit IN {UNITS_SQL}", name="ck_recipe_ingredient_unit"
        ),
        CheckConstraint(
            "size IS NULL OR (size IN ('small', 'medium', 'large') AND unit = 'unit')",
            name="ck_recipe_ingredient_size",
        ),
        CheckConstraint(
            "(vague_note IS NOT NULL AND quantity IS NULL AND unit IS NULL)"
            " OR (vague_note IS NULL AND quantity IS NOT NULL AND unit IS NOT NULL)",
            name="ck_recipe_ingredient_vague_or_measured",
        ),
        CheckConstraint("btrim(name) <> ''", name="ck_recipe_ingredient_name_not_blank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipe.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    unit: Mapped[str | None] = mapped_column(Text, nullable=True)
    size: Mapped[str | None] = mapped_column(Text, nullable=True)
    preparation: Mapped[str | None] = mapped_column(Text, nullable=True)
    vague_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class StepModel(Base):
    __tablename__ = "step"
    __table_args__ = (
        UniqueConstraint("recipe_id", "position", name="uq_step_position"),
        CheckConstraint("btrim(text) <> ''", name="ck_step_text_not_blank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipe.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)


class CartModel(Base):
    """A kitchen's one shared cart (spec 022), created on first use."""

    __tablename__ = "cart"
    __table_args__ = (
        UniqueConstraint("kitchen_id", name="uq_cart_kitchen_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    kitchen_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kitchens.id", ondelete="CASCADE"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CartItemModel(Base):
    __tablename__ = "cart_item"
    __table_args__ = (CheckConstraint("servings BETWEEN 1 AND 99", name="ck_cart_item_servings"),)

    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cart.id", ondelete="CASCADE"), primary_key=True
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipe.id", ondelete="CASCADE"), primary_key=True
    )
    servings: Mapped[int] = mapped_column(Integer, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ShoppingListModel(Base):
    """A kitchen's saved list; active while closing_date is null (spec 025)."""

    __tablename__ = "shopping_list"
    __table_args__ = (
        Index(
            "uq_shopping_list_active",
            "kitchen_id",
            unique=True,
            postgresql_where=text("closing_date IS NULL"),
        ),
        Index("ix_shopping_list_closed", "kitchen_id", text("closing_date DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    kitchen_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    closing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ShoppingListItemModel(Base):
    """One saved line. Recipes are copied as JSON so a line outlives them (spec 025 R6)."""

    __tablename__ = "shopping_list_item"
    __table_args__ = (
        CheckConstraint("origin IN ('cart', 'hand')", name="ck_shopping_list_item_origin"),
        CheckConstraint(
            "section IN ('measured', 'your_call')", name="ck_shopping_list_item_section"
        ),
        CheckConstraint(
            "kind IS NULL OR kind IN ('mass', 'volume', 'count')",
            name="ck_shopping_list_item_kind",
        ),
        Index("ix_shopping_list_item_list", "shopping_list_id", "origin", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shopping_list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shopping_list.id", ondelete="CASCADE"), nullable=False
    )
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    section: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str | None] = mapped_column(Text, nullable=True)
    size: Mapped[str | None] = mapped_column(Text, nullable=True)
    amounts: Mapped[list] = mapped_column(JSONB, nullable=False)
    notes: Mapped[list] = mapped_column(JSONB, nullable=False)
    recipes: Mapped[list] = mapped_column(JSONB, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class CartEditLockModel(Base):
    """The one session editing a cart, and its draft (spec 022 research R3, R6, R10, R11)."""

    __tablename__ = "cart_edit_lock"

    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cart.id", ondelete="CASCADE"), primary_key=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kitchen_memberships.id", ondelete="CASCADE"),
        nullable=False,
    )
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    draft: Mapped[dict] = mapped_column(JSONB, nullable=False)


class RecipeEditLockModel(Base):
    """The one session editing a recipe (spec 022 research R8, R10, R11)."""

    __tablename__ = "recipe_edit_lock"
    __table_args__ = (
        CheckConstraint(
            "(kitchen_membership_id IS NULL) <> (notebook_id IS NULL)",
            name="ck_recipe_edit_lock_one_access",
        ),
        ForeignKeyConstraint(
            ["notebook_id", "user_id"],
            ["notebook_membership.notebook_id", "notebook_membership.user_id"],
            ondelete="CASCADE",
            name="fk_recipe_edit_lock_notebook_membership",
        ),
    )

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipe.id", ondelete="CASCADE"), primary_key=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kitchen_membership_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("kitchen_memberships.id", ondelete="CASCADE"),
        nullable=True,
    )
    notebook_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
