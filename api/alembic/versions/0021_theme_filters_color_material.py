"""theme_settings: filter_color_enabled + filter_material_enabled.

Revision ID: 0021_filters_extra
Revises: 0020_orderbump_list
Create Date: 2026-08-30

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_filters_extra"
down_revision: str | None = "0020_orderbump_list"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLS = ("filter_color_enabled", "filter_material_enabled")


def _have() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if "theme_settings" not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns("theme_settings")}


def upgrade() -> None:
    have = _have()
    for name in _COLS:
        if name not in have:
            op.add_column(
                "theme_settings",
                sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.true()),
            )


def downgrade() -> None:
    have = _have()
    for name in _COLS:
        if name in have:
            op.drop_column("theme_settings", name)
