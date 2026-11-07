"""SQLAlchemy ORM models for users, kitchens, memberships, sessions, and notebooks."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Double,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from adapters.persistence.base import Base
from adapters.persistence.vector import Vector


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
    # The kitchen Home opens. Null until first resolved, and again after it is deleted.
    default_kitchen_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kitchens.id", ondelete="SET NULL"), nullable=True
    )
    # Null until the member first asks for their default notebook, and again
    # after it is deleted. users and notebook reference each other: use_alter.
    default_notebook_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notebook.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    # Set on the server by the owner; no route or body writes it (spec 055 FR-017a).
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
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
        CheckConstraint(
            "snapshot_key IS NULL OR kitchen_id IS NOT NULL",
            name="ck_notebook_snapshot_is_kitchen",
        ),
        Index(
            "uq_notebook_kitchen_snapshot_key",
            "kitchen_id",
            "snapshot_key",
            unique=True,
            postgresql_where=text("snapshot_key IS NOT NULL"),
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
    # Origin label of a snapshot (spec 035), cleared when the original is deleted.
    source_notebook_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notebook.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Set once on a snapshot and never cleared: it marks one for good, unlike the label above,
    # and makes a repeated request safe (spec 035 research R1, R3).
    snapshot_key: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
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


class NotebookInviteModel(Base):
    """An offer for one email to join one personal notebook (spec 057).

    Cancelling or replacing an invite deletes its row (research R2). The sender is nullable
    because an invite belongs to the notebook and outlives them (research R3).
    """

    __tablename__ = "notebook_invite"
    __table_args__ = (
        Index(
            "uq_notebook_invite_open",
            "notebook_id",
            "email",
            unique=True,
            postgresql_where=text("used_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notebook.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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


class UnitModel(Base):
    """One row per unit name (spec 055). Recipe lines hold plain text, so nothing points here."""

    __tablename__ = "unit"
    __table_args__ = (
        CheckConstraint("name = lower(btrim(name))", name="ck_unit_name_normalized"),
        CheckConstraint("char_length(name) BETWEEN 1 AND 32", name="ck_unit_name_length"),
    )

    name: Mapped[str] = mapped_column(Text, primary_key=True)
    # Active accounts that kept the unit. adapters.persistence.units is the only writer (R2).
    user_references: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, server_default=text("'{}'")
    )
    reference_count: Mapped[int] = mapped_column(
        Integer, Computed("cardinality(user_references)", persisted=True), nullable=False
    )
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SourceModel(Base):
    """Where a recipe came from (spec 020). Deleting a source keeps the recipe."""

    __tablename__ = "source"
    __table_args__ = (CheckConstraint("type IN ('text', 'url', 'photo')", name="ck_source_type"),)

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
    # The recipe image as a data URI, at most 300 KB decoded (spec 026, domain.recipe_preview).
    preview_image_base64: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The personal recipe this one was copied from (spec 069 FR-011). Only for repeat checks;
    # never returned by any read. Cleared when the source is deleted.
    copied_from_recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipe.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class RecipeIngredientModel(Base):
    __tablename__ = "recipe_ingredient"
    __table_args__ = (
        UniqueConstraint("recipe_id", "position", name="uq_recipe_ingredient_position"),
        CheckConstraint("quantity IS NULL OR quantity > 0", name="ck_recipe_ingredient_quantity"),
        CheckConstraint(
            "unit IS NULL OR btrim(unit) <> ''", name="ck_recipe_ingredient_unit_not_blank"
        ),
        CheckConstraint(
            "size IS NULL OR (size IN ('small', 'medium', 'large') AND unit = 'unit')",
            name="ck_recipe_ingredient_size",
        ),
        CheckConstraint(
            "(vague AND quantity IS NULL AND unit IS NULL AND vague_note IS NOT NULL)"
            " OR (NOT vague AND quantity IS NOT NULL AND unit IS NOT NULL)",
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
    # Whether the amount is vague. The only thing that says so.
    vague: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    # The words of a vague amount ("to taste"). On a measured line they are hidden text: kept so
    # that checking "Vague amount" again brings them back, and never shown or used as an amount.
    vague_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # A free note for the ingredient (a recommendation or disclaimer). Any line.
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


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
    __table_args__ = (UniqueConstraint("kitchen_id", name="uq_cart_kitchen_id"),)

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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
            "kind IS NULL OR kind IN ('mass', 'volume', 'count', 'custom')",
            name="ck_shopping_list_item_kind",
        ),
        Index("ix_shopping_list_item_list", "shopping_list_id", "origin", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    # Shared by the kitchen; frozen once the list is closed (spec 070 FR-001, FR-004).
    bought: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"), default=False
    )


class PlaceModel(Base):
    """A person's own place to buy things; default places are not rows (spec 070 R4)."""

    __tablename__ = "place"
    __table_args__ = (
        UniqueConstraint("user_id", "name_key", name="uq_place_user_name_key"),
        # The target of ingredient_place's owner key.
        UniqueConstraint("id", "user_id", name="uq_place_id_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # Lower case, no accents: what uniqueness compares (spec 070 R6).
    name_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class IngredientPlaceModel(Base):
    """One person's place for one normalized ingredient name; no row means Supermarket (R5)."""

    __tablename__ = "ingredient_place"
    __table_args__ = (
        CheckConstraint(
            "default_key IS NULL OR default_key IN ('supermarket', 'farmers_market', 'butcher', "
            "'fish_market', 'bakery', 'pharmacy', 'other')",
            name="ck_ingredient_place_default_key",
        ),
        CheckConstraint(
            "(default_key IS NULL) <> (place_id IS NULL)", name="ck_ingredient_place_one_place"
        ),
        Index("ix_ingredient_place_place", "place_id"),
        # Only the person's own place (graphify review): place_id with user_id, not place_id alone.
        ForeignKeyConstraint(
            ["place_id", "user_id"],
            ["place.id", "place.user_id"],
            ondelete="CASCADE",
            name="fk_ingredient_place_own_place",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    name: Mapped[str] = mapped_column(Text, primary_key=True)
    default_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    place_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CartActivityModel(Base):
    """One cart action by one person, for the dashboard only; no cart rule reads it (spec 055)."""

    __tablename__ = "cart_activity"
    __table_args__ = (
        CheckConstraint(
            "action IN ('created', 'edited', 'closed')", name="ck_cart_activity_action"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


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


# The column dimension; GEMINI_EMBED_DIM must equal it (spec 019 FR-025, checked by the worker).
EMBEDDING_DIM = 768


class RecipeEmbeddingModel(Base):
    """A recipe's search fingerprint for one model (spec 019). Internal only (FR-024)."""

    __tablename__ = "recipe_embedding"
    __table_args__ = (
        CheckConstraint("btrim(model) <> ''", name="ck_recipe_embedding_model_not_blank"),
        CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0", name="ck_recipe_embedding_input_tokens"
        ),
    )

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipe.id", ondelete="CASCADE"), primary_key=True
    )
    model: Mapped[str] = mapped_column(Text, primary_key=True)
    embedding: Mapped[tuple[float, ...]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    strategy_used: Mapped[str] = mapped_column(Text, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_truncated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    # The recipe's updated_at when its content was read; current while it still matches (R5).
    recipe_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EmbeddingJobModel(Base):
    """A recipe waiting for an embedding (spec 019 research R4)."""

    __tablename__ = "embedding_job"
    __table_args__ = (CheckConstraint("attempts >= 0", name="ck_embedding_job_attempts"),)

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipe.id", ondelete="CASCADE"), primary_key=True
    )
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_wait_s: Mapped[float | None] = mapped_column(Double, nullable=True)
    claimed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Result class name only (Unavailable, LimitReached, …), never a message (FR-023).
    last_failure: Mapped[str | None] = mapped_column(Text, nullable=True)
    enqueued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SearchEventModel(Base):
    """One search, with no person, question, kitchen or notebook (spec 019 FR-017b)."""

    __tablename__ = "search_event"
    __table_args__ = (
        CheckConstraint(
            "feature IN ('assistant', 'list_search', 'mcp', 'test')",
            name="ck_search_event_feature",
        ),
        CheckConstraint(
            "scope_kind IN ('kitchen', 'my_notebooks', 'notebook')",
            name="ck_search_event_scope_kind",
        ),
        CheckConstraint("result_count BETWEEN 0 AND 5", name="ck_search_event_result_count"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    feature: Mapped[str] = mapped_column(Text, nullable=False)
    scope_kind: Mapped[str] = mapped_column(Text, nullable=False)
    result_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    strategy: Mapped[str] = mapped_column(Text, nullable=False)
    min_closeness: Mapped[float] = mapped_column(Double, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class SearchResultModel(Base):
    """One result a search returned, and whether it was used (spec 019 FR-017b, FR-017c)."""

    __tablename__ = "search_result"
    __table_args__ = (
        CheckConstraint("rank BETWEEN 1 AND 5", name="ck_search_result_rank"),
        CheckConstraint("mark IN ('close', 'weak')", name="ck_search_result_mark"),
    )

    search_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_event.id", ondelete="CASCADE"), primary_key=True
    )
    # Indexed so deleting a recipe finds its records without a scan.
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipe.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    score: Mapped[float] = mapped_column(Double, nullable=False)
    mark: Mapped[str] = mapped_column(Text, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RefusedSiteModel(Base):
    """One registrable domain that refused a link capture (spec 067)."""

    __tablename__ = "refused_site"
    __table_args__ = (
        CheckConstraint("last_status IN (401, 402, 403, 451)", name="ck_refused_site_last_status"),
        CheckConstraint("char_length(last_message) <= 1000", name="ck_refused_site_last_message"),
        CheckConstraint("char_length(domain) <= 253", name="ck_refused_site_domain"),
    )

    domain: Mapped[str] = mapped_column(Text, primary_key=True)
    total_refusals: Mapped[int] = mapped_column(Integer, nullable=False)
    distinct_members: Mapped[int] = mapped_column(Integer, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_status: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    last_message: Mapped[str] = mapped_column(Text, nullable=False, server_default="")


class RefusedSiteMemberModel(Base):
    """An HMAC fingerprint of one member per domain; holds no user id (spec 067 R4)."""

    __tablename__ = "refused_site_member"
    __table_args__ = (
        CheckConstraint("octet_length(member_key) = 32", name="ck_refused_site_member_key"),
    )

    domain: Mapped[str] = mapped_column(
        Text, ForeignKey("refused_site.domain", ondelete="CASCADE"), primary_key=True
    )
    member_key: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
