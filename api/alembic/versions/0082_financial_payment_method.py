"""Livro-caixa: snapshot do método de pagamento por fato financeiro.

Revision ID: 0082_financial_payment_method
Revises: 0081_merchant_center
Create Date: 2026-09-22

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0082_financial_payment_method"
down_revision: str | None = "0081_merchant_center"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("financial_events")}


def upgrade() -> None:
    if "payment_method" not in _cols():
        op.add_column(
            "financial_events",
            sa.Column("payment_method", sa.String(16), nullable=True),
        )


def downgrade() -> None:
    if "payment_method" in _cols():
        op.drop_column("financial_events", "payment_method")
