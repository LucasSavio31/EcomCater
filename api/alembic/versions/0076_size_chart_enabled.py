"""Toggle pra mostrar/esconder o link "Tabela de medidas" na PDP.

Revision ID: 0076_size_chart_enabled
Revises: 0075_pdp_buy_button_colors
Create Date: 2026-09-20

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0076_size_chart_enabled"
down_revision: str | None = "0075_pdp_buy_button_colors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("theme_settings")}


def upgrade() -> None:
    if "size_chart_enabled" not in _cols():
        op.add_column(
            "theme_settings",
            sa.Column("size_chart_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    if "size_chart_enabled" in _cols():
        op.drop_column("theme_settings", "size_chart_enabled")
