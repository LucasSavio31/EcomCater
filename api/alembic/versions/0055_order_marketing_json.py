"""Atribuição de marketing no pedido (fbp/fbc/IP/UA p/ Meta CAPI + Google EC).

Revision ID: 0055_order_marketing
Revises: 0054_unaccent_extension
Create Date: 2026-09-01

Idempotente. Coluna JSONB nullable — nenhum backfill.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0055_order_marketing"
down_revision: str | None = "0054_unaccent_extension"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orders"
_COL = "marketing_json"


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABLE not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    have = _cols()
    if not have or _COL in have:
        return
    op.add_column(_TABLE, sa.Column(_COL, postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    if _COL in _cols():
        op.drop_column(_TABLE, _COL)
