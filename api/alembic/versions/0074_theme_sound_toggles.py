"""Toggles de som do painel admin (venda paga / devolução entregue).

Revision ID: 0074_theme_sound_toggles
Revises: 0073_nfe_documents
Create Date: 2026-09-20

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0074_theme_sound_toggles"
down_revision: str | None = "0073_nfe_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("theme_settings")}


def upgrade() -> None:
    cols = _cols()
    if "sound_sale_enabled" not in cols:
        op.add_column(
            "theme_settings",
            sa.Column("sound_sale_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
    if "sound_return_enabled" not in cols:
        op.add_column(
            "theme_settings",
            sa.Column("sound_return_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    cols = _cols()
    for name in ("sound_sale_enabled", "sound_return_enabled"):
        if name in cols:
            op.drop_column("theme_settings", name)
