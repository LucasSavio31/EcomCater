"""theme_settings: toggles de PDP/cards (qty, wishlist, hover zoom, botão do card).

Revision ID: 0023_pdp_card
Revises: 0022_leads_popup
Create Date: 2026-08-30

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0023_pdp_card"
down_revision: str | None = "0022_leads_popup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLS: list[tuple[str, sa.types.TypeEngine, object]] = [
    ("pdp_qty_selector_enabled", sa.Boolean(), sa.true()),
    ("wishlist_enabled", sa.Boolean(), sa.true()),
    ("card_hover_zoom_enabled", sa.Boolean(), sa.true()),
    ("card_buy_button_enabled", sa.Boolean(), sa.false()),
    ("card_buy_button_label", sa.String(40), "COMPRAR"),
]


def _have() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if "theme_settings" not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns("theme_settings")}


def upgrade() -> None:
    have = _have()
    for name, type_, default in _COLS:
        if name not in have:
            op.add_column(
                "theme_settings",
                sa.Column(name, type_, nullable=False, server_default=default),
            )


def downgrade() -> None:
    have = _have()
    for name, _t, _d in _COLS:
        if name in have:
            op.drop_column("theme_settings", name)
