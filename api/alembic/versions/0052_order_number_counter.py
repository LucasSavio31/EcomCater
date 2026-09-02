"""Contador monotônico da numeração de pedidos (nunca reutiliza número).

Revision ID: 0052_order_number_counter
Revises: 0051_checkout_steps
Create Date: 2026-08-31

Idempotente. Semeia o contador a partir do maior número já existente por ano.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0052_order_number_counter"
down_revision: str | None = "0051_checkout_steps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "order_number_counters"


def _has_table(name: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return name in insp.get_table_names()


def upgrade() -> None:
    if not _has_table(_TABLE):
        op.create_table(
            _TABLE,
            sa.Column("year", sa.Integer(), primary_key=True),
            sa.Column("last_seq", sa.Integer(), nullable=False, server_default="0"),
        )

    if _has_table("orders"):
        # Semeia a partir do maior sufixo já usado por ano (formato AAAA-NNNNNN).
        op.execute(
            sa.text(
                """
                INSERT INTO order_number_counters (year, last_seq)
                SELECT split_part(number, '-', 1)::int AS y,
                       MAX(split_part(number, '-', 2)::int) AS m
                  FROM orders
                 WHERE number ~ '^[0-9]{4}-[0-9]+$'
                 GROUP BY 1
                ON CONFLICT (year) DO UPDATE
                   SET last_seq = GREATEST(order_number_counters.last_seq, EXCLUDED.last_seq)
                """
            )
        )


def downgrade() -> None:
    if _has_table(_TABLE):
        op.drop_table(_TABLE)
