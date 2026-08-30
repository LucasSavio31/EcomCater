"""theme_settings.mini_cart_enabled — mini-carrinho lateral ao adicionar.

Revision ID: 0011_mini_cart
Revises: 0010_filters
Create Date: 2026-08-29

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_mini_cart"
down_revision: str | None = "0010_filters"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has() -> bool:
    insp = sa.inspect(op.get_bind())
    if "theme_settings" not in insp.get_table_names():
        return False
    return "mini_cart_enabled" in {c["name"] for c in insp.get_columns("theme_settings")}


def upgrade() -> None:
    if not _has():
        op.add_column(
            "theme_settings",
            sa.Column("mini_cart_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    if _has():
        op.drop_column("theme_settings", "mini_cart_enabled")
