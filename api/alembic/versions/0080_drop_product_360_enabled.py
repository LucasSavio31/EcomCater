"""Remove `theme_settings.product_360_enabled` -- o giro 360° da PDP foi
removido. Migração nova (em vez de apagar a 0077) porque essa coluna já
tinha sido aplicada em produção.

Revision ID: 0080_drop_product_360_enabled
Revises: 0079_drop_product_spin_frames
Create Date: 2026-09-21

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0080_drop_product_360_enabled"
down_revision: str | None = "0079_drop_product_spin_frames"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("theme_settings")}


def upgrade() -> None:
    if "product_360_enabled" in _cols():
        op.drop_column("theme_settings", "product_360_enabled")


def downgrade() -> None:
    if "product_360_enabled" not in _cols():
        op.add_column(
            "theme_settings",
            sa.Column("product_360_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
