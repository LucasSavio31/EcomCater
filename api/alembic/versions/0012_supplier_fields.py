"""Fornecedor: products.supplier + order_items.supplier (uso interno).

Revision ID: 0012_supplier
Revises: 0011_mini_cart
Create Date: 2026-08-29

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_supplier"
down_revision: str | None = "0011_mini_cart"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    if "supplier" not in _cols("products"):
        op.add_column("products", sa.Column("supplier", sa.String(160), nullable=True))
        op.create_index("ix_products_supplier", "products", ["supplier"])
    if "supplier" not in _cols("order_items"):
        op.add_column("order_items", sa.Column("supplier", sa.String(160), nullable=True))


def downgrade() -> None:
    if "supplier" in _cols("order_items"):
        op.drop_column("order_items", "supplier")
    if "supplier" in _cols("products"):
        op.drop_index("ix_products_supplier", table_name="products")
        op.drop_column("products", "supplier")
