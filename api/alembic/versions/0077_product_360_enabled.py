"""Toggle pra ligar/desligar o giro 360° (fotos do produto) na PDP.

Revision ID: 0077_product_360_enabled
Revises: 0076_size_chart_enabled
Create Date: 2026-09-20

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0077_product_360_enabled"
down_revision: str | None = "0076_size_chart_enabled"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("theme_settings")}


def upgrade() -> None:
    if "product_360_enabled" not in _cols():
        op.add_column(
            "theme_settings",
            sa.Column("product_360_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    if "product_360_enabled" in _cols():
        op.drop_column("theme_settings", "product_360_enabled")
