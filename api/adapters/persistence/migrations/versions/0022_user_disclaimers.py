"""user disclaimers: the account option that shows the picture-capture disclaimer (spec 041).

`users.disclaimers` is a boolean, true by default, so every account keeps the disclaimer shown
until it turns the option off.

Revision ID: 0022_user_disclaimers
Revises: 0021_catalog_other_names
Create Date: 2026-11-07
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0022_user_disclaimers"
down_revision: str | None = "0021_catalog_other_names"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("disclaimers", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("users", "disclaimers")
