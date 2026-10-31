"""Default kitchen: users.default_kitchen_id, the kitchen Home opens (spec 064).

No backfill: the default is resolved on read and stored then (research R2).

Revision ID: 0009_default_kitchen
Revises: 0008_cart_servings
Create Date: 2026-10-30
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_default_kitchen"
down_revision: str | None = "0008_cart_servings"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("default_kitchen_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_users_default_kitchen_id",
        "users",
        "kitchens",
        ["default_kitchen_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_default_kitchen_id", "users", type_="foreignkey")
    op.drop_column("users", "default_kitchen_id")
