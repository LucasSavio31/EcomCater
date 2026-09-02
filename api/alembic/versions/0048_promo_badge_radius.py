"""Raio das bordas do selo de promoção (-XX%).

Revision ID: 0048_promo_badge_radius
Revises: 0047_promo_badge_border
Create Date: 2026-08-31

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0048_promo_badge_radius"
down_revision: str | None = "0047_promo_badge_border"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"
_COL = "promo_badge_radius_px"


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABLE not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    have = _cols()
    if not have or _COL in have:
        return
    op.add_column(
        _TABLE, sa.Column(_COL, sa.Integer(), nullable=False, server_default="6")
    )


def downgrade() -> None:
    if _COL in _cols():
        op.drop_column(_TABLE, _COL)
