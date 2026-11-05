"""refused sites (spec 067).

`refused_site`: one row per registrable domain that answered a link capture with 401/402/403/451.
`refused_site_member`: one HMAC fingerprint per (domain, member) for the distinct-member count;
no user id (spec 067 R4). Neither table references `users`.

Revision ID: 0016_refused_sites
Revises: 0015_recipe_preview_image
Create Date: 2026-11-04
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0016_refused_sites"
down_revision: str | None = "0015_recipe_preview_image"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "refused_site",
        sa.Column("domain", sa.Text(), primary_key=True),
        sa.Column("total_refusals", sa.Integer(), nullable=False),
        sa.Column("distinct_members", sa.Integer(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_status", sa.SmallInteger(), nullable=False),
        sa.Column("last_message", sa.Text(), nullable=False, server_default=""),
        sa.CheckConstraint(
            "last_status IN (401, 402, 403, 451)", name="ck_refused_site_last_status"
        ),
        sa.CheckConstraint(
            "char_length(last_message) <= 1000", name="ck_refused_site_last_message"
        ),
        sa.CheckConstraint("char_length(domain) <= 253", name="ck_refused_site_domain"),
    )
    op.create_table(
        "refused_site_member",
        sa.Column(
            "domain",
            sa.Text(),
            sa.ForeignKey("refused_site.domain", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("member_key", sa.LargeBinary(), primary_key=True),
        sa.CheckConstraint("octet_length(member_key) = 32", name="ck_refused_site_member_key"),
    )


def downgrade() -> None:
    op.drop_table("refused_site_member")
    op.drop_table("refused_site")
