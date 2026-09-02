"""coupons.audience — 'general' | 'lead_signup'.

Revision ID: 0024_coupon_audience
Revises: 0023_pdp_card
Create Date: 2026-08-30

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0024_coupon_audience"
down_revision: str | None = "0023_pdp_card"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    if "audience" not in _cols("coupons"):
        op.add_column(
            "coupons",
            sa.Column("audience", sa.String(16), nullable=False, server_default="general"),
        )


def downgrade() -> None:
    if "audience" in _cols("coupons"):
        op.drop_column("coupons", "audience")
