"""Merge the two 0016 heads (refused_sites, recipe_copied_from).

Revision ID: 0017_merge_0016_heads
Revises: 0016_refused_sites, 0016_recipe_copied_from
"""

from collections.abc import Sequence

revision: str = "0017_merge_0016_heads"
down_revision: str | Sequence[str] | None = ("0016_refused_sites", "0016_recipe_copied_from")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
