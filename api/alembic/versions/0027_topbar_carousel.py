"""Barra superior: carrossel de 3 mensagens + cores.

Revision ID: 0027_topbar_carousel
Revises: 0026_backfill_addr
Create Date: 2026-08-30

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_topbar_carousel"
down_revision: str | None = "0026_backfill_addr"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABLE not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    cols = _cols()
    if not cols:
        return
    if "top_bar_carousel" not in cols:
        op.add_column(
            _TABLE,
            sa.Column(
                "top_bar_carousel",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    if "top_bar_message_2" not in cols:
        op.add_column(_TABLE, sa.Column("top_bar_message_2", sa.String(240), nullable=True))
    if "top_bar_message_3" not in cols:
        op.add_column(_TABLE, sa.Column("top_bar_message_3", sa.String(240), nullable=True))
    if "top_bar_bg_color" not in cols:
        op.add_column(
            _TABLE,
            sa.Column(
                "top_bar_bg_color", sa.String(9), nullable=False, server_default="#111111"
            ),
        )
    if "top_bar_text_color" not in cols:
        op.add_column(
            _TABLE,
            sa.Column(
                "top_bar_text_color", sa.String(9), nullable=False, server_default="#FFFFFF"
            ),
        )


def downgrade() -> None:
    cols = _cols()
    for name in (
        "top_bar_carousel",
        "top_bar_message_2",
        "top_bar_message_3",
        "top_bar_bg_color",
        "top_bar_text_color",
    ):
        if name in cols:
            op.drop_column(_TABLE, name)
