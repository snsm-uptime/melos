"""notebook_invite: an offer for one email to join one personal notebook (spec 057).

One unused row per notebook and email. Cancelling or replacing an invite deletes its row, and
used_at matches the name claim_single_use_email_token expects (research R2).

Revision ID: 0012_notebook_invite
Revises: 0011_notebook_snapshot_key
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_notebook_invite"
down_revision: str | None = "0011_notebook_snapshot_key"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "notebook_invite",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "notebook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notebook.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "invited_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "uq_notebook_invite_open",
        "notebook_invite",
        ["notebook_id", "email"],
        unique=True,
        postgresql_where=sa.text("used_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_notebook_invite_open", table_name="notebook_invite")
    op.drop_table("notebook_invite")
