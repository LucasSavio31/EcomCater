"""Variação de cor = produtos irmãos: products.color_group_id + color_name.

Revision ID: 0019_color_group
Revises: 0018_theme_extras
Create Date: 2026-08-30

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_color_group"
down_revision: str | None = "0018_theme_extras"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    have = _cols("products")
    if "color_group_id" not in have:
        op.add_column("products", sa.Column("color_group_id", sa.UUID(), nullable=True))
        op.create_index("ix_products_color_group_id", "products", ["color_group_id"])
    if "color_name" not in have:
        op.add_column("products", sa.Column("color_name", sa.String(60), nullable=True))


def downgrade() -> None:
    have = _cols("products")
    if "color_name" in have:
        op.drop_column("products", "color_name")
    if "color_group_id" in have:
        op.drop_index("ix_products_color_group_id", table_name="products")
        op.drop_column("products", "color_group_id")
