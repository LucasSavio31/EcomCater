"""Raio dos botões do carrinho + do botão calcular frete da PDP.

Revision ID: 0043_cart_button_radius
Revises: 0042_cart_appearance
Create Date: 2026-08-31

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0043_cart_button_radius"
down_revision: str | None = "0042_cart_appearance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"
_COLS = (
    "freight_button_radius_px",
    "cart_checkout_btn_radius_px",
    "cart_freight_btn_radius_px",
    "cart_qty_radius_px",
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
    for name in _COLS:
        if name not in have:
            op.add_column(
                _TABLE, sa.Column(name, sa.Integer(), nullable=False, server_default="12")
            )


def downgrade() -> None:
    have = _cols()
    for name in _COLS:
        if name in have:
            op.drop_column(_TABLE, name)
