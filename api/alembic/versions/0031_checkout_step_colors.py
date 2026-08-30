"""Cores do checkout: botões de etapa + etapa ativa.

Revision ID: 0031_checkout_step_colors
Revises: 0030_footer_social
Create Date: 2026-08-31

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_checkout_step_colors"
down_revision: str | None = "0030_footer_social"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"
_COLS = {
    "checkout_step_button_color": "#111111",
    "checkout_step_button_text_color": "#FFFFFF",
    "checkout_step_active_bg_color": "#111111",
    "checkout_step_active_text_color": "#FFFFFF",
}


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABLE not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    existing = _cols()
    if not existing:
        return
    for name, default in _COLS.items():
        if name not in existing:
            op.add_column(
                _TABLE,
                sa.Column(name, sa.String(9), nullable=False, server_default=default),
            )


def downgrade() -> None:
    existing = _cols()
    for name in _COLS:
        if name in existing:
            op.drop_column(_TABLE, name)
