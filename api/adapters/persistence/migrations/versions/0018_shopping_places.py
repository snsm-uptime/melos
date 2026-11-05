"""shopping by store (spec 070).

`shopping_list_item.bought`: shared by the kitchen, frozen at Done.
`place`: a person's custom places; the seven default places are code constants (research R4).
`ingredient_place`: one person's place for one normalized ingredient name; no row means
Supermarket (research R5).

Revision ID: 0018_shopping_places
Revises: 0017_merge_0016_heads
Create Date: 2026-11-05
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0018_shopping_places"
down_revision: str | None = "0017_merge_0016_heads"
branch_labels: str | None = None
depends_on: str | None = None

_DEFAULT_KEYS = (
    "'supermarket', 'farmers_market', 'butcher', 'fish_market', 'bakery', 'pharmacy', 'other'"
)


def upgrade() -> None:
    op.add_column(
        "shopping_list_item",
        sa.Column("bought", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "place",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_key", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "name_key", name="uq_place_user_name_key"),
    )
    op.create_table(
        "ingredient_place",
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("name", sa.Text(), primary_key=True),
        sa.Column("default_key", sa.Text(), nullable=True),
        sa.Column(
            "place_id",
            UUID(as_uuid=True),
            sa.ForeignKey("place.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            f"default_key IS NULL OR default_key IN ({_DEFAULT_KEYS})",
            name="ck_ingredient_place_default_key",
        ),
        sa.CheckConstraint(
            "(default_key IS NULL) <> (place_id IS NULL)",
            name="ck_ingredient_place_one_place",
        ),
    )
    op.create_index("ix_ingredient_place_place", "ingredient_place", ["place_id"])


def downgrade() -> None:
    op.drop_index("ix_ingredient_place_place", table_name="ingredient_place")
    op.drop_table("ingredient_place")
    op.drop_table("place")
    op.drop_column("shopping_list_item", "bought")
