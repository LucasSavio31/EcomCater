"""GA4 Measurement Protocol api_secret (para o evento `refund` server-side).

Revision ID: 0056_ga4_api_secret
Revises: 0055_order_marketing
Create Date: 2026-09-01

Idempotente. Coluna Text nullable — segredo, sem backfill.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0056_ga4_api_secret"
down_revision: str | None = "0055_order_marketing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "analytics_settings"
_COL = "ga4_api_secret"


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABLE not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    have = _cols()
    if not have or _COL in have:
        return
    op.add_column(_TABLE, sa.Column(_COL, sa.Text(), nullable=True))


def downgrade() -> None:
    if _COL in _cols():
        op.drop_column(_TABLE, _COL)
