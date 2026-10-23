"""Notebooks and per-notebook ingredient catalogs (spec 055).

A notebook is owned by exactly one kitchen or one member. Each kitchen has one
notebook; the schema allows many per member, and users.default_notebook_id
points at the member's default. Backfills one notebook per existing kitchen and
one default notebook per existing user with an alias.

Revision ID: 0003_notebooks_ingredients
Revises: 0002_pgvector_kitchen_lang
Create Date: 2026-10-22
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_notebooks_ingredients"
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
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.Text(), nullable=True),
        _created_at(),
        sa.CheckConstraint(
            "(kitchen_id IS NULL) <> (user_id IS NULL)", name="ck_notebook_one_owner"
        ),
        sa.ForeignKeyConstraint(["kitchen_id"], ["kitchens.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kitchen_id"),
    )
    op.create_index("ix_notebook_user_id", "notebook", ["user_id"], unique=False)

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

    op.execute("INSERT INTO notebook (kitchen_id) SELECT id FROM kitchens")
    op.execute(
        "INSERT INTO notebook (user_id, name) "
        "SELECT id, alias || '''s Notebook' FROM users WHERE alias IS NOT NULL"
    )
    op.execute(
        "UPDATE users SET default_notebook_id = notebook.id "
        "FROM notebook WHERE notebook.user_id = users.id"
    )


def downgrade() -> None:
    op.drop_constraint("users_default_notebook_id_fkey", "users", type_="foreignkey")
    op.drop_column("users", "default_notebook_id")
    op.drop_table("ingredient")
    op.drop_index("ix_notebook_user_id", table_name="notebook")
    op.drop_table("notebook")
