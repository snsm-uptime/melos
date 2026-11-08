"""standard ingredient table, admin review of custom names, job runs (spec 073).

Additive only: four new tables and two indexes on existing tables. The notebook and kitchen
catalogs (`ingredient`, `ingredient_name`) and `recipe_ingredient` are not changed. Downgrade
drops the four tables and the indexes it created.

Revision ID: 0022_standard_ingredients
Revises: 0021_catalog_other_names
Create Date: 2026-11-07
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0022_standard_ingredients"
down_revision: str | None = "0021_catalog_other_names"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "standard_ingredient",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("normalized_name", sa.Text(), nullable=False, unique=True),
        sa.Column("language", sa.String(2), nullable=False),
        sa.Column("ai_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("language IN ('en', 'es')", name="ck_standard_ingredient_language"),
    )

    op.create_table(
        "standard_ingredient_name",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "standard_ingredient_id",
            UUID(as_uuid=True),
            sa.ForeignKey("standard_ingredient.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("language", sa.String(2), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "standard_ingredient_id", "language", name="uq_standard_ingredient_name_language"
        ),
        sa.CheckConstraint("language IN ('en', 'es')", name="ck_standard_ingredient_name_language"),
        sa.CheckConstraint(
            "source IN ('discovery', 'ai', 'admin')", name="ck_standard_ingredient_name_source"
        ),
        sa.CheckConstraint("source <> 'ai' OR model IS NOT NULL", name="ck_standard_name_ai_model"),
    )

    op.create_table(
        "standard_ingredient_review",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "standard_ingredient_id",
            UUID(as_uuid=True),
            sa.ForeignKey("standard_ingredient.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("replaces_name", sa.Text(), nullable=False),
        sa.Column("proposed_name", sa.Text(), nullable=False),
        sa.Column("proposed_language", sa.String(2), nullable=False),
        sa.Column(
            "proposed_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("decided_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')",
            name="ck_standard_review_status",
        ),
        sa.CheckConstraint(
            "(status = 'pending') = (decided_by IS NULL)",
            name="ck_standard_review_decided",
        ),
    )
    op.create_index(
        "ix_standard_review_status_created",
        "standard_ingredient_review",
        ["status", "created_at"],
    )

    op.create_table(
        "job_run",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("translated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'skipped')",
            name="ck_job_run_status",
        ),
        sa.CheckConstraint(
            "found >= 0 AND translated >= 0 AND rejected >= 0 AND failed >= 0",
            name="ck_job_run_counts",
        ),
    )
    op.create_index("ix_job_run_status_started", "job_run", ["status", "started_at"])

    op.create_index("ix_recipe_updated_at", "recipe", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_recipe_updated_at", table_name="recipe")
    op.drop_index("ix_job_run_status_started", table_name="job_run")
    op.drop_table("job_run")
    op.drop_index("ix_standard_review_status_created", table_name="standard_ingredient_review")
    op.drop_table("standard_ingredient_review")
    op.drop_table("standard_ingredient_name")
    op.drop_table("standard_ingredient")
