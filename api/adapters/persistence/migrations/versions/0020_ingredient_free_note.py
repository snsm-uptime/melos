"""free notes, an explicit vague flag, and hidden vague text on recipe ingredients

Two columns are added to `recipe_ingredient`:

- `note` (nullable): a free note for the ingredient, a recommendation or disclaimer, on any line.
  Free notes were never stored before, so there is nothing to move into it.
- `vague` (boolean, not null): whether the amount is vague. Before, `vague_note` being set meant
  vague, so a measured line could not keep words. Every row with `vague_note` set was vague, so the
  flag is backfilled from it and no words move.

`vague_note` keeps the words of a vague amount. It may also hold hidden words on a measured line:
they stay there when "Vague amount" is unchecked, so checking it again brings them back. Only
`vague` says what a line is. Hidden words are never shown as an amount and never used as one.

The downgrade refuses to run while a row holds a free note or hidden words, because the old schema
has nowhere to keep them. It changes nothing in that case.

Revision ID: 0020_ingredient_free_note
Revises: 0019_ingredient_place_owner
Create Date: 2026-11-06
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0020_ingredient_free_note"
down_revision: str | None = "0019_ingredient_place_owner"
branch_labels: str | None = None
depends_on: str | None = None

CHECK = "ck_recipe_ingredient_vague_or_measured"


def upgrade() -> None:
    op.add_column("recipe_ingredient", sa.Column("note", sa.Text(), nullable=True))
    op.add_column(
        "recipe_ingredient",
        sa.Column("vague", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.execute("UPDATE recipe_ingredient SET vague = true WHERE vague_note IS NOT NULL")
    op.drop_constraint(CHECK, "recipe_ingredient", type_="check")
    op.create_check_constraint(
        CHECK,
        "recipe_ingredient",
        "(vague AND quantity IS NULL AND unit IS NULL AND vague_note IS NOT NULL)"
        " OR (NOT vague AND quantity IS NOT NULL AND unit IS NOT NULL)",
    )


def downgrade() -> None:
    kept = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT count(*) FROM recipe_ingredient"
                " WHERE note IS NOT NULL OR (NOT vague AND vague_note IS NOT NULL)"
            )
        )
        .scalar_one()
    )
    if kept:
        raise RuntimeError(
            f"{kept} ingredient line(s) hold a free note or hidden vague text, which the previous"
            " schema cannot keep. Clear them first; nothing was changed."
        )
    op.drop_constraint(CHECK, "recipe_ingredient", type_="check")
    op.create_check_constraint(
        CHECK,
        "recipe_ingredient",
        "(vague_note IS NOT NULL AND quantity IS NULL AND unit IS NULL)"
        " OR (vague_note IS NULL AND quantity IS NOT NULL AND unit IS NOT NULL)",
    )
    op.drop_column("recipe_ingredient", "vague")
    op.drop_column("recipe_ingredient", "note")
