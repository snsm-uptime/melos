"""notebook.snapshot_key marks a notebook as a snapshot for good (spec 035 research R1).

It is unique per kitchen, so a repeated add returns the same snapshot. Existing notebooks stay
null: this feature is the first to make snapshots.

Revision ID: 0011_notebook_snapshot_key
Revises: 0010_shopping_lists
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_notebook_snapshot_key"
down_revision: str | None = "0010_shopping_lists"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "notebook", sa.Column("snapshot_key", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_check_constraint(
        "ck_notebook_snapshot_is_kitchen",
        "notebook",
        "snapshot_key IS NULL OR kitchen_id IS NOT NULL",
    )
    op.create_index(
        "uq_notebook_kitchen_snapshot_key",
        "notebook",
        ["kitchen_id", "snapshot_key"],
        unique=True,
        postgresql_where=sa.text("snapshot_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_notebook_kitchen_snapshot_key", table_name="notebook")
    op.drop_constraint("ck_notebook_snapshot_is_kitchen", "notebook", type_="check")
    op.drop_column("notebook", "snapshot_key")
