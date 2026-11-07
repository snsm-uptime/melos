"""catalog other names, recipe language, pair dismissals (spec 043).

`recipe.language` is added nullable, filled by the FR-005a fallback, then made NOT NULL: a kitchen
notebook's recipe takes the kitchen's content language, a personal one its author's account
language when that is English or Spanish, and anything else Spanish.

Revision ID: 0021_catalog_other_names
Revises: 0020_ingredient_free_note
Create Date: 2026-11-06
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0021_catalog_other_names"
down_revision: str | None = "0020_ingredient_free_note"
branch_labels: str | None = None
depends_on: str | None = None

# Subqueries, not joins: an UPDATE's FROM list cannot join on the target row.
_FALLBACK = """
UPDATE recipe AS r
SET language = COALESCE(
    (
        SELECT k.content_language
        FROM notebook AS n
        JOIN kitchens AS k ON k.id = n.kitchen_id
        WHERE n.id = r.notebook_id AND k.content_language IN ('en', 'es')
    ),
    (
        SELECT lower(left(u.language, 2))
        FROM notebook AS n
        JOIN users AS u ON u.id = r.author_id
        WHERE n.id = r.notebook_id
          AND n.kitchen_id IS NULL
          AND lower(left(u.language, 2)) IN ('en', 'es')
    ),
    'es'
)
"""


def upgrade() -> None:
    op.add_column("recipe", sa.Column("language", sa.String(2), nullable=True))
    op.add_column(
        "recipe", sa.Column("language_detected_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("recipe", sa.Column("proposed_language", sa.String(2), nullable=True))
    op.execute(_FALLBACK)
    # The FR-005a last fallback, so a writer that names no language still stores one.
    op.alter_column("recipe", "language", nullable=False, server_default="es")
    op.create_check_constraint("ck_recipe_language", "recipe", "language IN ('en', 'es')")
    op.create_check_constraint(
        "ck_recipe_proposed_language",
        "recipe",
        "proposed_language IS NULL OR proposed_language IN ('en', 'es')",
    )

    op.add_column("ingredient", sa.Column("language", sa.String(2), nullable=True))
    op.create_check_constraint(
        "ck_ingredient_language", "ingredient", "language IS NULL OR language IN ('en', 'es')"
    )

    op.create_table(
        "ingredient_name",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "ingredient_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ingredient.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "notebook_id",
            UUID(as_uuid=True),
            sa.ForeignKey("notebook.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("language", sa.String(2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("notebook_id", "name", name="uq_ingredient_name_notebook_name"),
        sa.CheckConstraint("kind IN ('variant', 'spelling')", name="ck_ingredient_name_kind"),
        sa.CheckConstraint(
            "(kind = 'variant' AND language IN ('en', 'es')) "
            "OR (kind = 'spelling' AND language IS NULL)",
            name="ck_ingredient_name_language",
        ),
    )
    op.create_index(
        "uq_ingredient_name_variant_language",
        "ingredient_name",
        ["ingredient_id", "language"],
        unique=True,
        postgresql_where=sa.text("kind = 'variant'"),
    )
    op.create_index("ix_ingredient_name_ingredient", "ingredient_name", ["ingredient_id"])

    op.create_table(
        "ingredient_pair_dismissal",
        sa.Column(
            "notebook_id",
            UUID(as_uuid=True),
            sa.ForeignKey("notebook.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("name_a", sa.Text(), primary_key=True),
        sa.Column("name_b", sa.Text(), primary_key=True),
        sa.Column(
            "dismissed_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("name_a < name_b", name="ck_ingredient_pair_dismissal_sorted"),
    )

    op.add_column(
        "shopping_list_item",
        sa.Column("names", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("shopping_list_item", "names")
    op.drop_table("ingredient_pair_dismissal")
    op.drop_index("ix_ingredient_name_ingredient", table_name="ingredient_name")
    op.drop_index("uq_ingredient_name_variant_language", table_name="ingredient_name")
    op.drop_table("ingredient_name")
    op.drop_constraint("ck_ingredient_language", "ingredient", type_="check")
    op.drop_column("ingredient", "language")
    op.drop_constraint("ck_recipe_proposed_language", "recipe", type_="check")
    op.drop_constraint("ck_recipe_language", "recipe", type_="check")
    op.drop_column("recipe", "proposed_language")
    op.drop_column("recipe", "language_detected_at")
    op.drop_column("recipe", "language")
