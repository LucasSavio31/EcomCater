"""Cores + raio do botão "Aplicar" do cupom no carrinho.

Revision ID: 0044_cart_coupon_button
Revises: 0043_cart_button_radius
Create Date: 2026-08-31

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0044_cart_coupon_button"
down_revision: str | None = "0043_cart_button_radius"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"
_COLS: tuple[tuple[str, str, str], ...] = (
    ("cart_coupon_btn_bg_color", sa.String(length=9), "#FFFFFF"),
    ("cart_coupon_btn_text_color", sa.String(length=9), "#111111"),
    ("cart_coupon_btn_hover_color", sa.String(length=9), "#F3F3F3"),
    ("cart_coupon_btn_border_color", sa.String(length=9), "#111111"),
    ("cart_coupon_btn_radius_px", sa.Integer(), "12"),
)


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABLE not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    have = _cols()
    if not have:
        return
    for name, coltype, default in _COLS:
        if name not in have:
            op.add_column(
                _TABLE, sa.Column(name, coltype, nullable=False, server_default=default)
            )


def downgrade() -> None:
    have = _cols()
    for name, _coltype, _default in _COLS:
        if name in have:
            op.drop_column(_TABLE, name)
