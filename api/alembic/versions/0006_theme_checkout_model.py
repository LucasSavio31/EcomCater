"""Modelo do checkout em theme_settings (menu "Checkout" no admin).

Revision ID: 0006_checkout_model
Revises: 0005_cart_redirect
Create Date: 2026-08-29

Idempotente: só adiciona a coluna que ainda não existe.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_checkout_model"
down_revision: str | None = "0005_cart_redirect"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = [
    ("checkout_email_first", sa.Boolean(), sa.false()),
    ("checkout_container_width_px", sa.Integer(), sa.text("1100")),
    ("checkout_items_layout", sa.String(12), sa.text("'with_thumb'")),
    ("checkout_show_coupon", sa.Boolean(), sa.true()),
    ("checkout_allow_qty_change", sa.Boolean(), sa.true()),
    ("checkout_button_color", sa.String(9), sa.text("'#111111'")),
    ("checkout_header_bg_color", sa.String(9), sa.text("'#FFFFFF'")),
    ("checkout_footer_note", sa.String(240), None),
]


def _existing() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if "theme_settings" not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns("theme_settings")}


def upgrade() -> None:
    have = _existing()
    for name, type_, default in _COLUMNS:
        if name in have:
            continue
        col = (
            sa.Column(name, type_, nullable=True)
            if default is None
            else sa.Column(name, type_, nullable=False, server_default=default)
        )
        op.add_column("theme_settings", col)


def downgrade() -> None:
    have = _existing()
    for name, _, _ in _COLUMNS:
        if name in have:
            op.drop_column("theme_settings", name)
