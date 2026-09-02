"""Tabelas de medidas + vínculo com produto.

Revision ID: 0034_size_charts
Revises: 0033_filters_home_pdp_related
Create Date: 2026-08-31

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID

from alembic import op

revision: str = "0034_size_charts"
down_revision: str | None = "0033_filters_home_pdp_related"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _cols(t: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    if t not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(t)}


def upgrade() -> None:
    if "size_charts" not in _tables():
        op.create_table(
            "size_charts",
            sa.Column("id", PgUUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("columns", JSONB, nullable=False, server_default="[]"),
            sa.Column("rows", JSONB, nullable=False, server_default="[]"),
            sa.Column("note", sa.String(400), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "products" in _tables() and "size_chart_id" not in _cols("products"):
        op.add_column(
            "products",
            sa.Column(
                "size_chart_id",
                PgUUID(as_uuid=True),
                sa.ForeignKey("size_charts.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    if "size_chart_id" in _cols("products"):
        op.drop_column("products", "size_chart_id")
    if "size_charts" in _tables():
        op.drop_table("size_charts")
