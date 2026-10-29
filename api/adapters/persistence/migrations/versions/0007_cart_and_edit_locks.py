"""The kitchen cart, its edit lock and draft, recipe edit locks, and recipe.cart_add_count.

Spec 022. Lock rows reference the session (sign-out frees them) and the membership that
allowed them (losing access deletes them for good). No backfill: a kitchen without a cart
row reads as an empty cart. Downgrade drops the four tables and the column.

Revision ID: 0007_cart_and_edit_locks
Revises: 0006_unaccent
Create Date: 2026-10-29
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_cart_and_edit_locks"
down_revision: str | None = "0006_unaccent"
branch_labels: str | None = None
depends_on: str | None = None

_UUID = postgresql.UUID(as_uuid=True)


def _now(name: str) -> sa.Column:
    return sa.Column(
        name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


def upgrade() -> None:
    op.add_column(
        "recipe",
        sa.Column("cart_add_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.create_check_constraint("ck_recipe_cart_add_count", "recipe", "cart_add_count >= 0")

    op.create_table(
        "cart",
        sa.Column("id", _UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("kitchen_id", _UUID, nullable=False),
        sa.Column("people", sa.Integer(), nullable=True),
        _now("updated_at"),
        sa.Column("updated_by", _UUID, nullable=True),
        sa.CheckConstraint("people IS NULL OR people BETWEEN 1 AND 99", name="ck_cart_people"),
        sa.ForeignKeyConstraint(["kitchen_id"], ["kitchens.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kitchen_id", name="uq_cart_kitchen_id"),
    )

    op.create_table(
        "cart_item",
        sa.Column("cart_id", _UUID, nullable=False),
        sa.Column("recipe_id", _UUID, nullable=False),
        sa.Column("meals", sa.Integer(), server_default=sa.text("1"), nullable=False),
        _now("added_at"),
        sa.CheckConstraint("meals BETWEEN 1 AND 99", name="ck_cart_item_meals"),
        sa.ForeignKeyConstraint(["cart_id"], ["cart.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipe.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("cart_id", "recipe_id"),
    )
    op.create_index("ix_cart_item_recipe_id", "cart_item", ["recipe_id"])

    op.create_table(
        "cart_edit_lock",
        sa.Column("cart_id", _UUID, nullable=False),
        sa.Column("session_id", _UUID, nullable=False),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("membership_id", _UUID, nullable=False),
        _now("acquired_at"),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("draft", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["cart_id"], ["cart.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["membership_id"], ["kitchen_memberships.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("cart_id"),
    )

    op.create_table(
        "recipe_edit_lock",
        sa.Column("recipe_id", _UUID, nullable=False),
        sa.Column("session_id", _UUID, nullable=False),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("kitchen_membership_id", _UUID, nullable=True),
        sa.Column("notebook_id", _UUID, nullable=True),
        _now("acquired_at"),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(kitchen_membership_id IS NULL) <> (notebook_id IS NULL)",
            name="ck_recipe_edit_lock_one_access",
        ),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipe.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["kitchen_membership_id"], ["kitchen_memberships.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["notebook_id", "user_id"],
            ["notebook_membership.notebook_id", "notebook_membership.user_id"],
            ondelete="CASCADE",
            name="fk_recipe_edit_lock_notebook_membership",
        ),
        sa.PrimaryKeyConstraint("recipe_id"),
    )


def downgrade() -> None:
    op.drop_table("recipe_edit_lock")
    op.drop_table("cart_edit_lock")
    op.drop_index("ix_cart_item_recipe_id", table_name="cart_item")
    op.drop_table("cart_item")
    op.drop_table("cart")
    op.drop_constraint("ck_recipe_cart_add_count", "recipe", type_="check")
    op.drop_column("recipe", "cart_add_count")
