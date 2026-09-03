"""orders.processing_error — motivo de falha na finalização assíncrona do pedido.

Revision ID: 0058_order_processing_error
Revises: 0057_password_resets
Create Date: 2026-09-03

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0058_order_processing_error"
down_revision: str | None = "0057_password_resets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "orders"
_COL = "processing_error"


def _has_col() -> bool:
    insp = sa.inspect(op.get_bind())
    return any(c["name"] == _COL for c in insp.get_columns(_TABLE))


def upgrade() -> None:
    if not _has_col():
        op.add_column(_TABLE, sa.Column(_COL, sa.Text(), nullable=True))


def downgrade() -> None:
    if _has_col():
        op.drop_column(_TABLE, _COL)
