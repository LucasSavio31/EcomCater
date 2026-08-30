"""Filtros da vitrine (menu "Filtros" no admin).

Revision ID: 0010_filters
Revises: 0009_orderbump_slug
Create Date: 2026-08-29

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_filters"
down_revision: str | None = "0009_orderbump_slug"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = ["filter_size_enabled", "filter_price_enabled", "filter_category_enabled"]


def _existing() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if "theme_settings" not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns("theme_settings")}


def upgrade() -> None:
    have = _existing()
    for name in _COLUMNS:
        if name not in have:
            op.add_column(
                "theme_settings",
                sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.true()),
            )


def downgrade() -> None:
    have = _existing()
    for name in _COLUMNS:
        if name in have:
            op.drop_column("theme_settings", name)
