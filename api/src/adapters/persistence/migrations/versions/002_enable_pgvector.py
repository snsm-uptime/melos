"""Enable pgvector extension

Revision ID: 002
Revises: 001
Create Date: 2026-10-18 18:35:00.000000

"""
from alembic import op

# revision identifiers
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
