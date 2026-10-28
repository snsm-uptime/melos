"""Recipes, their ingredient lines and steps, and their sources (spec 020).

A recipe lives in exactly one notebook. `save_key` is the draft key the ui makes, so a
repeated Save returns the recipe already stored. Downgrade drops the four tables; the
notebooks and catalogs are untouched.

Revision ID: 0005_recipes
Revises: 0004_drop_kitchen_hide
Create Date: 2026-10-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_recipes"
down_revision: str | None = "0004_drop_kitchen_hide"
branch_labels: str | None = None
depends_on: str | None = None

UNITS_SQL = "('g', 'kg', 'oz', 'lb', 'ml', 'l', 'cup', 'tbsp', 'tsp', 'unit')"


def _id() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def _created_at(name: str = "created_at") -> sa.Column:
    return sa.Column(
        name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "source",
        _id(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        _created_at(),
        sa.CheckConstraint("type IN ('text', 'url', 'photo')", name="ck_source_type"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "recipe",
        _id(),
        sa.Column("notebook_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("base_servings", sa.Integer(), nullable=False),
        sa.Column(
            "servings_estimated", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("save_key", postgresql.UUID(as_uuid=True), nullable=True),
        _created_at(),
        _created_at("updated_at"),
        sa.CheckConstraint("btrim(title) <> ''", name="ck_recipe_title_not_blank"),
        sa.CheckConstraint("base_servings >= 1", name="ck_recipe_base_servings"),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebook.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["source.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recipe_notebook_id", "recipe", ["notebook_id"], unique=False)
    op.create_index(
        "uq_recipe_author_save_key",
        "recipe",
        ["author_id", "save_key"],
        unique=True,
        postgresql_where=sa.text("save_key IS NOT NULL"),
    )

    op.create_table(
        "recipe_ingredient",
        _id(),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(), nullable=True),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("size", sa.Text(), nullable=True),
        sa.Column("preparation", sa.Text(), nullable=True),
        sa.Column("vague_note", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity > 0", name="ck_recipe_ingredient_quantity"
        ),
        sa.CheckConstraint(
            f"unit IS NULL OR unit IN {UNITS_SQL}", name="ck_recipe_ingredient_unit"
        ),
        sa.CheckConstraint(
            "size IS NULL OR (size IN ('small', 'medium', 'large') AND unit = 'unit')",
            name="ck_recipe_ingredient_size",
        ),
        sa.CheckConstraint(
            "(vague_note IS NOT NULL AND quantity IS NULL AND unit IS NULL)"
            " OR (vague_note IS NULL AND quantity IS NOT NULL AND unit IS NOT NULL)",
            name="ck_recipe_ingredient_vague_or_measured",
        ),
        sa.CheckConstraint("btrim(name) <> ''", name="ck_recipe_ingredient_name_not_blank"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipe.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipe_id", "position", name="uq_recipe_ingredient_position"),
    )
    op.create_index(
        "ix_recipe_ingredient_recipe_id", "recipe_ingredient", ["recipe_id"], unique=False
    )

    op.create_table(
        "step",
        _id(),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.CheckConstraint("btrim(text) <> ''", name="ck_step_text_not_blank"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipe.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipe_id", "position", name="uq_step_position"),
    )
    op.create_index("ix_step_recipe_id", "step", ["recipe_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_step_recipe_id", table_name="step")
    op.drop_table("step")
    op.drop_index("ix_recipe_ingredient_recipe_id", table_name="recipe_ingredient")
    op.drop_table("recipe_ingredient")
    op.drop_index("uq_recipe_author_save_key", table_name="recipe")
    op.drop_index("ix_recipe_notebook_id", table_name="recipe")
    op.drop_table("recipe")
    op.drop_table("source")
