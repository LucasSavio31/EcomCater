"""Flag separada: link de captura de lead na página do produto.

Revision ID: 0049_lead_popup_pdp
Revises: 0048_promo_badge_radius
Create Date: 2026-08-31

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0049_lead_popup_pdp"
down_revision: str | None = "0048_promo_badge_radius"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"
_COL = "lead_popup_pdp_enabled"


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
        _TABLE, sa.Column(_COL, sa.Boolean(), nullable=False, server_default=sa.false())
    )


def downgrade() -> None:
    if _COL in _cols():
        op.drop_column(_TABLE, _COL)
