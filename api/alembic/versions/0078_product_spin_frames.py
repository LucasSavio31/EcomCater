"""Sequência de URLs pro giro 360° gerado por IA (fotos originais + quadros
intermediários interpolados entre pares de ângulo parecido).

Revision ID: 0078_product_spin_frames
Revises: 0077_product_360_enabled
Create Date: 2026-09-20

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0078_product_spin_frames"
down_revision: str | None = "0077_product_360_enabled"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _cols() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("products")}


def upgrade() -> None:
    if "spin_frames_json" not in _cols():
        op.add_column(
            "products",
            sa.Column("spin_frames_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        )


def downgrade() -> None:
    if "spin_frames_json" in _cols():
        op.drop_column("products", "spin_frames_json")
