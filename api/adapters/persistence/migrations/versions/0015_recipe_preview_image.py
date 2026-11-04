"""recipe preview image (spec 026).

A nullable `recipe.preview_image_base64`: the page's main photo from link capture, as a
`data:image/jpeg|png|webp;base64,` URI of at most 300 KB decoded (`domain.recipe_preview`).
PRD §1.6 names the column. Existing rows stay null.

Revision ID: 0015_recipe_preview_image
Revises: 0014_recipe_embeddings
Create Date: 2026-11-04
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0015_recipe_preview_image"
down_revision: str | None = "0014_recipe_embeddings"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("recipe", sa.Column("preview_image_base64", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("recipe", "preview_image_base64")
