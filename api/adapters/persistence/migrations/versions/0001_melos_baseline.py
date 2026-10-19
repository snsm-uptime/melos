"""Melos baseline — auth tables plus kitchens, memberships and invites.

Squashes the finance-dashboard history (0001–0042) into one revision. The auth
tables (users, sessions, password_reset_tokens, email_verification_tokens) keep
their finance-dashboard shape; lists became kitchens and the finance-only
tables and columns (ledger, cards, budgets, imports, splits, FX) were dropped.

Revision ID: 0001_melos_baseline
Revises:
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_melos_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("alias", sa.String(length=32), nullable=True),
        sa.Column("photo_base64", sa.Text(), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("language", sa.String(length=8), nullable=True),
        sa.Column("theme", sa.String(length=16), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("uq_users_alias_lower", "users", [sa.text("lower(alias)")], unique=True)

    op.create_table(
        "kitchens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        _created_at(),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # users ↔ kitchens is circular: add the last-opened pointer once kitchens exists.
    op.add_column(
        "users",
        sa.Column(
            "last_opened_kitchen_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("kitchens.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.create_table(
        "kitchen_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
        _created_at(),
        sa.ForeignKeyConstraint(["kitchen_id"], ["kitchens.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kitchen_id", "user_id", name="uq_kitchen_membership"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        _created_at(),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_sessions_token", "sessions", ["token"], unique=False)

    for table in ("password_reset_tokens", "email_verification_tokens"):
        op.create_table(
            table,
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            _created_at(),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash"),
        )
        op.create_index(f"ix_{table}_user_id", table, ["user_id"], unique=False)

    op.create_table(
        "kitchen_invite_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("inviter_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        sa.ForeignKeyConstraint(["kitchen_id"], ["kitchens.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inviter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_kitchen_invite_tokens_kitchen_id_email",
        "kitchen_invite_tokens",
        ["kitchen_id", "email"],
        unique=False,
    )
    op.create_index(
        "ix_kitchen_invite_tokens_inviter_user_id",
        "kitchen_invite_tokens",
        ["inviter_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("kitchen_invite_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_table("sessions")
    op.drop_table("kitchen_memberships")
    op.drop_column("users", "last_opened_kitchen_id")
    op.drop_table("kitchens")
    op.drop_table("users")
