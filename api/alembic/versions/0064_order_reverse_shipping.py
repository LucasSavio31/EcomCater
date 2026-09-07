"""Logística reversa: coluna nova em `orders` pra guardar o envio de volta
(cliente -> loja), espelhando o formato de `shipping_service_json` sem
mexer nele. Nullable, aditiva -- nenhum pedido existente é tocado.

Revision ID: 0064_order_reverse_shipping
Revises: 0063_presence_module_off
Create Date: 2026-09-08

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0064_order_reverse_shipping"
down_revision: str | None = "0063_presence_module_off"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("orders")}


def upgrade() -> None:
    if "reverse_shipping_json" not in _cols():
        op.add_column(
            "orders",
            sa.Column("reverse_shipping_json", postgresql.JSONB(), nullable=True),
        )


def downgrade() -> None:
    if "reverse_shipping_json" in _cols():
        op.drop_column("orders", "reverse_shipping_json")
