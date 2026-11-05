"""recipe copied_from_recipe_id (spec 069).

A nullable `recipe.copied_from_recipe_id` referencing `recipe.id` ON DELETE SET NULL, indexed.
Set only when a personal recipe is copied into a kitchen; used to detect a repeat add and never
returned by a read. Existing rows stay null.

Revision ID: 0016_recipe_copied_from
Revises: 0015_recipe_preview_image
Create Date: 2026-11-04
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0016_recipe_copied_from"
down_revision: str | None = "0015_recipe_preview_image"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "recipe",
        sa.Column(
            "copied_from_recipe_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "recipe.id", ondelete="SET NULL", name="recipe_copied_from_recipe_id_fkey"
            ),
            nullable=True,
        ),
    )
    op.create_index("ix_recipe_copied_from_recipe_id", "recipe", ["copied_from_recipe_id"])


def downgrade() -> None:
    op.drop_index("ix_recipe_copied_from_recipe_id", table_name="recipe")
    op.drop_column("recipe", "copied_from_recipe_id")
