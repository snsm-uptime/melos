"""Enable the unaccent extension so recipe lists can filter ignoring accents (spec 021).

No table changes. Downgrade does nothing: other objects may use the extension, and dropping
it is left to the database owner.

Revision ID: 0006_unaccent
Revises: 0005_recipes
Create Date: 2026-10-27
"""

from alembic import op

revision: str = "0006_unaccent"
down_revision: str | None = "0005_recipes"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")


def downgrade() -> None:
    pass
