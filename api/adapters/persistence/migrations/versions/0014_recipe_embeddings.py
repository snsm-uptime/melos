"""recipe embeddings, embedding jobs and search records (spec 019).

`recipe_embedding` holds one 768-value vector per recipe and model; it is current while its
`recipe_updated_at` equals the recipe's `updated_at`. `embedding_job` is the worker's queue in
Postgres. `search_event` and `search_result` record what searches returned, with no person and
no question. Every row that points at a recipe leaves with it by cascade (spec 027 FR-016).

The `vector` extension comes from 0002 and is left alone by the downgrade.

Revision ID: 0014_recipe_embeddings
Revises: 0013_custom_units
Create Date: 2026-11-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_recipe_embeddings"
down_revision: str | None = "0013_custom_units"
branch_labels: str | None = None
depends_on: str | None = None

EMBEDDING_DIM = 768


class _Vector(sa.types.UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **_: object) -> str:
        return f"vector({EMBEDDING_DIM})"


def _recipe_fk() -> sa.ForeignKey:
    return sa.ForeignKey("recipe.id", ondelete="CASCADE")


def _now(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "recipe_embedding",
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), _recipe_fk(), primary_key=True),
        sa.Column("model", sa.Text(), primary_key=True),
        sa.Column("embedding", _Vector(), nullable=False),
        sa.Column("strategy_used", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("input_truncated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("recipe_updated_at", sa.DateTime(timezone=True), nullable=False),
        _now("updated_at"),
        sa.CheckConstraint("btrim(model) <> ''", name="ck_recipe_embedding_model_not_blank"),
        sa.CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0", name="ck_recipe_embedding_input_tokens"
        ),
    )

    op.create_table(
        "embedding_job",
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), _recipe_fk(), primary_key=True),
        _now("due_at"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_wait_s", sa.Double(), nullable=True),
        sa.Column("claimed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure", sa.Text(), nullable=True),
        _now("enqueued_at"),
        sa.CheckConstraint("attempts >= 0", name="ck_embedding_job_attempts"),
    )
    op.create_index("ix_embedding_job_due_at", "embedding_job", ["due_at"])

    op.create_table(
        "search_event",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("feature", sa.Text(), nullable=False),
        sa.Column("scope_kind", sa.Text(), nullable=False),
        sa.Column("result_count", sa.SmallInteger(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("strategy", sa.Text(), nullable=False),
        sa.Column("min_closeness", sa.Double(), nullable=False),
        _now("created_at"),
        sa.CheckConstraint(
            "feature IN ('assistant', 'list_search', 'mcp', 'test')",
            name="ck_search_event_feature",
        ),
        sa.CheckConstraint(
            "scope_kind IN ('kitchen', 'my_notebooks', 'notebook')",
            name="ck_search_event_scope_kind",
        ),
        sa.CheckConstraint("result_count BETWEEN 0 AND 5", name="ck_search_event_result_count"),
    )
    op.create_index("ix_search_event_created_at", "search_event", ["created_at"])

    op.create_table(
        "search_result",
        sa.Column(
            "search_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("search_event.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), _recipe_fk(), primary_key=True),
        sa.Column("rank", sa.SmallInteger(), nullable=False),
        sa.Column("score", sa.Double(), nullable=False),
        sa.Column("mark", sa.Text(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("rank BETWEEN 1 AND 5", name="ck_search_result_rank"),
        sa.CheckConstraint("mark IN ('close', 'weak')", name="ck_search_result_mark"),
    )
    op.create_index("ix_search_result_recipe_id", "search_result", ["recipe_id"])


def downgrade() -> None:
    op.drop_index("ix_search_result_recipe_id", table_name="search_result")
    op.drop_table("search_result")
    op.drop_index("ix_search_event_created_at", table_name="search_event")
    op.drop_table("search_event")
    op.drop_index("ix_embedding_job_due_at", table_name="embedding_job")
    op.drop_table("embedding_job")
    op.drop_table("recipe_embedding")
