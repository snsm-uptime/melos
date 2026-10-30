"""Cart by servings: cart_item.meals becomes servings and cart.people goes.

Spec 023, amendment of 2026-10-30. Each entry's servings is people × meals, capped at 99, with
the member count where people was never set, so saved amounts stay the same. Open cart drafts
are discarded and their locks freed. Downgrade keeps the amounts with people 1, meals = servings;
the original split cannot be recovered.

Revision ID: 0008_cart_servings
Revises: 0007_cart_and_edit_locks
Create Date: 2026-10-30
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0008_cart_servings"
down_revision: str | None = "0007_cart_and_edit_locks"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("DELETE FROM cart_edit_lock")
    op.drop_constraint("ck_cart_item_meals", "cart_item", type_="check")
    op.execute(
        """
        UPDATE cart_item AS item
        SET meals = LEAST(
            99,
            item.meals * COALESCE(
                cart.people,
                GREATEST(
                    1,
                    (
                        SELECT count(*)
                        FROM kitchen_memberships AS m
                        WHERE m.kitchen_id = cart.kitchen_id
                    )
                )
            )
        )
        FROM cart
        WHERE cart.id = item.cart_id
        """
    )
    op.alter_column("cart_item", "meals", new_column_name="servings", server_default=None)
    op.create_check_constraint("ck_cart_item_servings", "cart_item", "servings BETWEEN 1 AND 99")
    op.drop_constraint("ck_cart_people", "cart", type_="check")
    op.drop_column("cart", "people")


def downgrade() -> None:
    op.add_column("cart", sa.Column("people", sa.Integer(), nullable=True))
    op.execute("UPDATE cart SET people = 1")
    op.create_check_constraint(
        "ck_cart_people", "cart", "people IS NULL OR people BETWEEN 1 AND 99"
    )
    op.drop_constraint("ck_cart_item_servings", "cart_item", type_="check")
    op.alter_column("cart_item", "servings", new_column_name="meals", server_default=sa.text("1"))
    op.create_check_constraint("ck_cart_item_meals", "cart_item", "meals BETWEEN 1 AND 99")
