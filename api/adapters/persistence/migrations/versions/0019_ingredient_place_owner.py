"""an ingredient's place must be the same person's place (spec 070).

The service already refuses another person's place; the composite key makes the database refuse
it too. `place` gains a unique (id, user_id) for the key to point at.

Revision ID: 0019_ingredient_place_owner
Revises: 0018_shopping_places
Create Date: 2026-11-05
"""

from alembic import op

revision: str = "0019_ingredient_place_owner"
down_revision: str | None = "0018_shopping_places"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_place_id_user", "place", ["id", "user_id"])
    op.drop_constraint("ingredient_place_place_id_fkey", "ingredient_place", type_="foreignkey")
    op.create_foreign_key(
        "fk_ingredient_place_own_place",
        "ingredient_place",
        "place",
        ["place_id", "user_id"],
        ["id", "user_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_ingredient_place_own_place", "ingredient_place", type_="foreignkey")
    op.create_foreign_key(
        "ingredient_place_place_id_fkey",
        "ingredient_place",
        "place",
        ["place_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("uq_place_id_user", "place", type_="unique")
