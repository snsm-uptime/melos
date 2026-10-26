"""Drop the per-member kitchen hide (spec 056 FR-024).

Archive is the only way to put a kitchen away. The downgrade restores the column
as false for every membership, which is the state the hide feature started from.

Revision ID: 0004_drop_kitchen_hide
Revises: 0003_personal_kitchen_notebooks
Create Date: 2026-10-25
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0004_drop_kitchen_hide"
down_revision: str | None = "0003_personal_kitchen_notebooks"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_column("kitchen_memberships", "is_hidden")


def downgrade() -> None:
    op.add_column(
        "kitchen_memberships",
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
