"""Livro-caixa financeiro persistente + custo do produto.

- products.cost_cents           (custo pago pela loja — opcional)
- order_items.unit_cost_cents   (snapshot do custo no momento do pedido)
- financial_events              (append-only: placed | paid | refunded | canceled)
  sobrevive à exclusão de pedidos → faturamento/estorno/cancelamento cumulativos.

Revision ID: 0061_financial_ledger
Revises: 0060_smtp_order_bcc
Create Date: 2026-09-04

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0061_financial_ledger"
down_revision: str | None = "0060_smtp_order_bcc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "cost_cents" not in _cols("products"):
        op.add_column("products", sa.Column("cost_cents", sa.Integer(), nullable=True))
    if "unit_cost_cents" not in _cols("order_items"):
        op.add_column("order_items", sa.Column("unit_cost_cents", sa.Integer(), nullable=True))

    if "financial_events" not in _tables():
        op.create_table(
            "financial_events",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("kind", sa.String(16), nullable=False),  # placed|paid|refunded|canceled
            sa.Column("order_number", sa.String(20), nullable=False),
            sa.Column(
                "order_id",
                sa.dialects.postgresql.UUID(as_uuid=True),
                sa.ForeignKey("orders.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("gross_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("cost_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("items_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint("order_number", "kind", name="uq_financial_events_order_kind"),
        )
        op.create_index(
            "ix_financial_events_kind_occurred", "financial_events", ["kind", "occurred_at"]
        )
        op.create_index(
            "ix_financial_events_occurred_at", "financial_events", ["occurred_at"]
        )


def downgrade() -> None:
    if "financial_events" in _tables():
        op.drop_table("financial_events")
    if "unit_cost_cents" in _cols("order_items"):
        op.drop_column("order_items", "unit_cost_cents")
    if "cost_cents" in _cols("products"):
        op.drop_column("products", "cost_cents")
