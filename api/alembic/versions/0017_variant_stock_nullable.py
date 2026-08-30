"""product_variants.stock_qty nullable — NULL = estoque ilimitado.

Revision ID: 0017_stock_nullable
Revises: 0016_option_color
Create Date: 2026-08-30

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_stock_nullable"
down_revision: str | None = "0016_option_color"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _col(table: str, name: str) -> dict | None:
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return None
    for c in insp.get_columns(table):
        if c["name"] == name:
            return c
    return None


def upgrade() -> None:
    col = _col("product_variants", "stock_qty")
    if col is not None and not col["nullable"]:
        op.alter_column("product_variants", "stock_qty", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    col = _col("product_variants", "stock_qty")
    if col is not None and col["nullable"]:
        op.execute("UPDATE product_variants SET stock_qty = 0 WHERE stock_qty IS NULL")
        op.alter_column("product_variants", "stock_qty", existing_type=sa.Integer(), nullable=False)
