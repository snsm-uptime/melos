"""Add pgvector extension and kitchen content_language column.

Enables pgvector for recipe embeddings (future). Adds content_language
column to kitchens to support multi-language ingredient/category names
(default 'en', also supports 'es').

Revision ID: 0002_pgvector_and_kitchen_language
Revises: 0001_melos_baseline
Create Date: 2026-10-19
"""

from alembic import op
import sqlalchemy as sa


revision: str = "0002_pgvector_and_kitchen_language"
down_revision: str | None = "0001_melos_baseline"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "kitchens",
        sa.Column(
            "content_language",
            sa.String(length=2),
            nullable=False,
            server_default="en",
        ),
    )
    op.create_check_constraint(
        "ck_kitchens_content_language",
        "kitchens",
        "content_language IN ('en', 'es')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_kitchens_content_language", "kitchens")
    op.drop_column("kitchens", "content_language")
    op.execute("DROP EXTENSION IF EXISTS vector")
