"""Saved shopping lists: shopping_list and shopping_list_item (spec 025).

A list is active while closing_date is null, with at most one active list per kitchen. Lines
copy their recipes as JSON with no foreign key, so a list outlives them.

Revision ID: 0010_shopping_lists
Revises: 0009_default_kitchen
Create Date: 2026-10-30
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_shopping_lists"
down_revision: str | None = "0009_default_kitchen"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "shopping_list",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "kitchen_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("kitchens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("closing_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "uq_shopping_list_active",
        "shopping_list",
        ["kitchen_id"],
        unique=True,
        postgresql_where=sa.text("closing_date IS NULL"),
    )
    op.create_index(
        "ix_shopping_list_closed", "shopping_list", ["kitchen_id", sa.text("closing_date DESC")]
    )
    op.create_table(
        "shopping_list_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "shopping_list_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("shopping_list.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("section", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=True),
        sa.Column("size", sa.Text(), nullable=True),
        sa.Column("amounts", postgresql.JSONB(), nullable=False),
        sa.Column("notes", postgresql.JSONB(), nullable=False),
        sa.Column("recipes", postgresql.JSONB(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint("origin IN ('cart', 'hand')", name="ck_shopping_list_item_origin"),
        sa.CheckConstraint(
            "section IN ('measured', 'your_call')", name="ck_shopping_list_item_section"
        ),
        sa.CheckConstraint(
            "kind IS NULL OR kind IN ('mass', 'volume', 'count')",
            name="ck_shopping_list_item_kind",
        ),
    )
    op.create_index(
        "ix_shopping_list_item_list",
        "shopping_list_item",
        ["shopping_list_id", "origin", "position"],
    )


def downgrade() -> None:
    op.drop_table("shopping_list_item")
    op.drop_table("shopping_list")
