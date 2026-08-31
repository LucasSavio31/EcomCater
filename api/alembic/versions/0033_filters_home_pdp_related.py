"""Toggles: filtros na home + relacionados na PDP.

Revision ID: 0033_filters_home_pdp_related
Revises: 0032_checkout_require_terms
Create Date: 2026-08-31

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_filters_home_pdp_related"
down_revision: str | None = "0032_checkout_require_terms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "theme_settings"
_COLS = ("filters_on_home", "pdp_related_enabled")


def _cols() -> set[str]:
    insp = sa.inspect(op.get_bind())
    if _TABLE not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    existing = _cols()
    if not existing:
        return
    for name in _COLS:
        if name not in existing:
            op.add_column(
                _TABLE,
                sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.true()),
            )


def downgrade() -> None:
    existing = _cols()
    for name in _COLS:
        if name in existing:
            op.drop_column(_TABLE, name)
