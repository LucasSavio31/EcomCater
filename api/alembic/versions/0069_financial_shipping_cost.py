"""Custo de frete no livro-caixa: `financial_events.shipping_cents` --
lucro passa a ser valor de venda - (custo do produto + custo de frete).

Backfill: pra eventos já existentes cujo pedido ainda existe, copia
`orders.shipping_cents` (o pedido já foi excluído -> fica 0, mesma limitação
que já existe pra outros dados desse livro-caixa quando o pedido some).

Revision ID: 0069_financial_shipping_cost
Revises: 0068_notifications
Create Date: 2026-09-18

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0069_financial_shipping_cost"
down_revision: str | None = "0068_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("financial_events")}


def upgrade() -> None:
    if "shipping_cents" not in _cols():
        op.add_column(
            "financial_events",
            sa.Column("shipping_cents", sa.Integer(), nullable=False, server_default="0"),
        )
        op.execute(
            "UPDATE financial_events fe SET shipping_cents = o.shipping_cents "
            "FROM orders o WHERE fe.order_id = o.id"
        )


def downgrade() -> None:
    if "shipping_cents" in _cols():
        op.drop_column("financial_events", "shipping_cents")
