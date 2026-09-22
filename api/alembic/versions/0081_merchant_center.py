"""Google Merchant Center — verificação de propriedade do site (meta tag).

Revision ID: 0081_merchant_center
Revises: 0080_drop_product_360_enabled
Create Date: 2026-09-22

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0081_merchant_center"
down_revision: str | None = "0080_drop_product_360_enabled"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("analytics_settings")}


def upgrade() -> None:
    cols = _cols()
    if "merchant_center_enabled" not in cols:
        op.add_column(
            "analytics_settings",
            sa.Column("merchant_center_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if "merchant_center_verification_code" not in cols:
        op.add_column(
            "analytics_settings",
            sa.Column("merchant_center_verification_code", sa.String(100), nullable=True),
        )


def downgrade() -> None:
    cols = _cols()
    for name in ("merchant_center_enabled", "merchant_center_verification_code"):
        if name in cols:
            op.drop_column("analytics_settings", name)
