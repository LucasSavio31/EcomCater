"""Cores da bolinha da sacola + do coração de favoritos na PDP.

Revision ID: 0045_cart_badge_wishlist
Revises: 0044_cart_coupon_button
Create Date: 2026-08-31

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0045_cart_badge_wishlist"
down_revision: str | None = "0044_cart_coupon_button"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"
_COLS: tuple[tuple[str, str], ...] = (
    ("cart_badge_bg_color", "#111111"),
    ("cart_badge_text_color", "#FFFFFF"),
    ("pdp_wishlist_bg_color", "#FFFFFF"),
    ("pdp_wishlist_border_color", "#DC2626"),
    ("pdp_wishlist_icon_color", "#DC2626"),
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
    for name, default in _COLS:
        if name not in have:
            op.add_column(
                _TABLE,
                sa.Column(name, sa.String(length=9), nullable=False, server_default=default),
            )


def downgrade() -> None:
    have = _cols()
    for name, _default in _COLS:
        if name in have:
            op.drop_column(_TABLE, name)
