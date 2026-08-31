"""Cores do popup "Tabela de medidas" na PDP.

Revision ID: 0035_size_chart_popup
Revises: 0034_size_charts
Create Date: 2026-08-31

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035_size_chart_popup"
down_revision: str | None = "0034_size_charts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"
_COLS = {
    "size_chart_bg_color": "#FFFFFF",
    "size_chart_header_bg_color": "#FFC400",
    "size_chart_header_text_color": "#111111",
    "size_chart_text_color": "#374151",
}


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABLE not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    existing = _cols()
    if not existing:
        return
    for name, default in _COLS.items():
        if name not in existing:
            op.add_column(
                _TABLE,
                sa.Column(name, sa.String(9), nullable=False, server_default=default),
            )


def downgrade() -> None:
    existing = _cols()
    for name in _COLS:
        if name in existing:
            op.drop_column(_TABLE, name)
