"""Merge the two 0022 heads (user_disclaimers, standard_ingredients).

Revision ID: 0023_merge_0022_heads
Revises: 0022_user_disclaimers, 0022_standard_ingredients
"""

from collections.abc import Sequence

revision: str = "0023_merge_0022_heads"
down_revision: str | Sequence[str] | None = ("0022_user_disclaimers", "0022_standard_ingredients")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
