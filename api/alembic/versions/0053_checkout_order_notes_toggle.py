"""Liga/desliga a caixa "Observações do pedido" no checkout.

Revision ID: 0053_checkout_notes
Revises: 0052_order_number_counter
Create Date: 2026-09-01

Idempotente. Entra DESLIGADO por padrão (server_default false).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0053_checkout_notes"
down_revision: str | None = "0052_order_number_counter"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"
_COL = "checkout_order_notes_enabled"


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
