"""Menu "Carrinho" na Aparência: cores dos botões e das caixinhas de quantidade.

Revision ID: 0042_cart_appearance
Revises: 0041_freight_button_colors
Create Date: 2026-08-31

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0042_cart_appearance"
down_revision: str | None = "0041_freight_button_colors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"
_COLS = {
    "cart_checkout_btn_bg_color": "#111111",
    "cart_checkout_btn_text_color": "#FFFFFF",
    "cart_checkout_btn_hover_color": "#333333",
    "cart_checkout_btn_border_color": "#111111",
    "cart_freight_btn_bg_color": "#111111",
    "cart_freight_btn_text_color": "#FFFFFF",
    "cart_freight_btn_hover_color": "#333333",
    "cart_freight_btn_border_color": "#111111",
    "cart_qty_bg_color": "#FFFFFF",
    "cart_qty_text_color": "#111111",
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
