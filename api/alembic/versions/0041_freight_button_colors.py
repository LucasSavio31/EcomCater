"""Cores próprias do botão 'Calcular frete' na PDP.

Revision ID: 0041_freight_button_colors
Revises: 0040_pdp_reassurance
Create Date: 2026-08-31

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0041_freight_button_colors"
down_revision: str | None = "0040_pdp_reassurance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"
_COLS = {
    "promo_badge_bg_color": "#DC2626",
    "promo_badge_text_color": "#FFFFFF",
    "freight_button_bg_color": "#111111",
    "freight_button_text_color": "#FFFFFF",
    "freight_button_hover_color": "#333333",
    "freight_button_border_color": "#111111",
}


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABLE not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    have = _cols()
    if not have:
        return
    for name, default in _COLS.items():
        if name not in have:
            op.add_column(
                _TABLE, sa.Column(name, sa.String(9), nullable=False, server_default=default)
            )


def downgrade() -> None:
    have = _cols()
    for name in _COLS:
        if name in have:
            op.drop_column(_TABLE, name)
