"""custom units, cart activity and the admin flag (spec 055).

`unit` holds one row per name. Recipe lines keep plain text, so the table check on the ten units
goes and any stored unit works for every reader. The app decides who may use a word.

Revision ID: 0013_custom_units
Revises: 0012_notebook_invite
Create Date: 2026-11-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_custom_units"
down_revision: str | None = "0012_notebook_invite"
branch_labels: str | None = None
depends_on: str | None = None

UNITS = ("g", "kg", "oz", "lb", "ml", "l", "cup", "tbsp", "tsp", "unit")
UNITS_SQL = "('g', 'kg', 'oz', 'lb', 'ml', 'l', 'cup', 'tbsp', 'tsp', 'unit')"


def upgrade() -> None:
    op.create_table(
        "unit",
        sa.Column("name", sa.Text(), primary_key=True),
        sa.Column(
            "user_references",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "reference_count",
            sa.Integer(),
            sa.Computed("cardinality(user_references)", persisted=True),
            nullable=False,
        ),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("name = lower(btrim(name))", name="ck_unit_name_normalized"),
        sa.CheckConstraint("char_length(name) BETWEEN 1 AND 32", name="ck_unit_name_length"),
    )
    values = ", ".join(f"('{name}', true)" for name in UNITS)
    op.execute(f"INSERT INTO unit (name, is_default) VALUES {values}")

    op.create_table(
        "cart_activity",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "action IN ('created', 'edited', 'closed')", name="ck_cart_activity_action"
        ),
    )
    op.create_index("ix_cart_activity_user_id", "cart_activity", ["user_id"])

    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.drop_constraint("ck_recipe_ingredient_unit", "recipe_ingredient", type_="check")
    op.create_check_constraint(
        "ck_recipe_ingredient_unit_not_blank",
        "recipe_ingredient",
        "unit IS NULL OR btrim(unit) <> ''",
    )
    op.drop_constraint("ck_shopping_list_item_kind", "shopping_list_item", type_="check")
    op.create_check_constraint(
        "ck_shopping_list_item_kind",
        "shopping_list_item",
        "kind IS NULL OR kind IN ('mass', 'volume', 'count', 'custom')",
    )


def downgrade() -> None:
    # Old code skips these lines on a shopping list, and changing them would destroy what people
    # wrote, so the rows must be cleared by hand first (research R19).
    connection = op.get_bind()
    lines = connection.execute(
        sa.text(f"SELECT count(*) FROM recipe_ingredient WHERE unit NOT IN {UNITS_SQL}")
    ).scalar_one()
    items = connection.execute(
        sa.text("SELECT count(*) FROM shopping_list_item WHERE kind = 'custom'")
    ).scalar_one()
    if lines or items:
        raise RuntimeError(
            "Cannot downgrade 0013_custom_units: "
            f"{lines} recipe line(s) and {items} shopping list item(s) use a custom unit. "
            "Change or delete them first."
        )

    op.drop_constraint("ck_shopping_list_item_kind", "shopping_list_item", type_="check")
    op.create_check_constraint(
        "ck_shopping_list_item_kind",
        "shopping_list_item",
        "kind IS NULL OR kind IN ('mass', 'volume', 'count')",
    )
    op.drop_constraint("ck_recipe_ingredient_unit_not_blank", "recipe_ingredient", type_="check")
    op.create_check_constraint(
        "ck_recipe_ingredient_unit", "recipe_ingredient", f"unit IS NULL OR unit IN {UNITS_SQL}"
    )
    op.drop_column("users", "is_admin")
    op.drop_index("ix_cart_activity_user_id", table_name="cart_activity")
    op.drop_table("cart_activity")
    op.drop_table("unit")
