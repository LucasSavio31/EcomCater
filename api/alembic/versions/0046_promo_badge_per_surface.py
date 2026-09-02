"""Ativar/desativar o selo de promoção (-XX%) por superfície (vitrine x PDP).

Revision ID: 0046_promo_badge_surface
Revises: 0045_cart_badge_wishlist
Create Date: 2026-08-31

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0046_promo_badge_surface"
down_revision: str | None = "0045_cart_badge_wishlist"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"
_COLS = ("promo_badge_card_enabled", "promo_badge_pdp_enabled")


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
                _TABLE, sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.true())
            )


def downgrade() -> None:
    have = _cols()
    for name in _COLS:
        if name in have:
            op.drop_column(_TABLE, name)
