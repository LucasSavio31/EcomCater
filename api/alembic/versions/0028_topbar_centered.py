"""Barra superior: opção de texto centralizado.

Revision ID: 0028_topbar_centered
Revises: 0027_topbar_carousel
Create Date: 2026-08-30

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028_topbar_centered"
down_revision: str | None = "0027_topbar_carousel"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABLE not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    if _cols() and "top_bar_centered" not in _cols():
        op.add_column(
            _TABLE,
            sa.Column(
                "top_bar_centered",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    if "top_bar_centered" in _cols():
        op.drop_column(_TABLE, "top_bar_centered")
