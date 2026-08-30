"""order_items.variant_attrs (JSONB) — variação estruturada (cor/número) editável.

Revision ID: 0015_variant_attrs
Revises: 0014_theme_discount_badge
Create Date: 2026-08-30

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_variant_attrs"
down_revision: str | None = "0014_discount_badge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    if "variant_attrs" not in _cols("order_items"):
        op.add_column(
            "order_items",
            sa.Column("variant_attrs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )


def downgrade() -> None:
    if "variant_attrs" in _cols("order_items"):
        op.drop_column("order_items", "variant_attrs")
