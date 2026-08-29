"""theme_settings.cart_redirect_after_add — ir para o carrinho após adicionar.

Revision ID: 0005_cart_redirect
Revises: 0004_hero_seals
Create Date: 2026-08-29

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_cart_redirect"
down_revision: str | None = "0004_hero_seals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column() -> bool:
    insp = sa.inspect(op.get_bind())
    if "theme_settings" not in insp.get_table_names():
        return False
    return "cart_redirect_after_add" in {c["name"] for c in insp.get_columns("theme_settings")}


def upgrade() -> None:
    if not _has_column():
        op.add_column(
            "theme_settings",
            sa.Column(
                "cart_redirect_after_add",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    if _has_column():
        op.drop_column("theme_settings", "cart_redirect_after_add")
