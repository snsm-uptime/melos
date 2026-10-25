"""Personal and kitchen notebooks, ingredient catalogs and the default notebook (spec 055).

A personal notebook belongs to people through notebook_membership (one owner, any
number of members). A kitchen notebook has a kitchen_id, one stored owner
(owner_user_id) and no membership rows. users.default_notebook_id points at the
person's default personal notebook. No backfill: notebooks are created on first use.

Revision ID: 0003_personal_kitchen_notebooks
Revises: 0002_pgvector_kitchen_lang
Create Date: 2026-10-24
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_personal_kitchen_notebooks"
down_revision: str | None = "0002_pgvector_kitchen_lang"
branch_labels: str | None = None
depends_on: str | None = None


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "notebook",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_notebook_id", postgresql.UUID(as_uuid=True), nullable=True),
        _created_at(),
        sa.CheckConstraint("btrim(name) <> ''", name="ck_notebook_name_not_blank"),
        sa.CheckConstraint(
            "source_notebook_id IS NULL OR kitchen_id IS NOT NULL",
            name="ck_notebook_source_is_kitchen",
        ),
        sa.CheckConstraint("source_notebook_id <> id", name="ck_notebook_source_not_self"),
        sa.CheckConstraint(
            "owner_user_id IS NULL OR kitchen_id IS NOT NULL",
            name="ck_notebook_owner_is_kitchen",
        ),
        sa.ForeignKeyConstraint(["kitchen_id"], ["kitchens.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_notebook_id"], ["notebook.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notebook_kitchen_id", "notebook", ["kitchen_id"], unique=False)
    op.create_index("ix_notebook_owner_user_id", "notebook", ["owner_user_id"], unique=False)
    op.create_index(
        "ix_notebook_source_notebook_id", "notebook", ["source_notebook_id"], unique=False
    )

    op.create_table(
        "notebook_membership",
        sa.Column("notebook_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        _created_at(),
        sa.CheckConstraint("role IN ('owner', 'member')", name="ck_notebook_membership_role"),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebook.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("notebook_id", "user_id"),
    )
    op.create_index(
        "ix_notebook_membership_user_id", "notebook_membership", ["user_id"], unique=False
    )
    op.create_index(
        "uq_notebook_one_owner",
        "notebook_membership",
        ["notebook_id"],
        unique=True,
        postgresql_where=sa.text("role = 'owner'"),
    )

    op.create_table(
        "ingredient",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("notebook_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebook.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notebook_id", "name", name="uq_ingredient_notebook_name"),
    )

    op.add_column(
        "users",
        sa.Column("default_notebook_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "users_default_notebook_id_fkey",
        "users",
        "notebook",
        ["default_notebook_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("users_default_notebook_id_fkey", "users", type_="foreignkey")
    op.drop_column("users", "default_notebook_id")
    op.drop_table("ingredient")
    op.drop_index("uq_notebook_one_owner", table_name="notebook_membership")
    op.drop_index("ix_notebook_membership_user_id", table_name="notebook_membership")
    op.drop_table("notebook_membership")
    op.drop_index("ix_notebook_source_notebook_id", table_name="notebook")
    op.drop_index("ix_notebook_owner_user_id", table_name="notebook")
    op.drop_index("ix_notebook_kitchen_id", table_name="notebook")
    op.drop_table("notebook")
