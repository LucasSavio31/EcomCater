"""Raio das caixas de variação (PDP).

Revision ID: 0039_variation_radius
Revises: 0038_lead_popup_logo
Create Date: 2026-08-31

Idempotente.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0039_variation_radius"
down_revision: str | None = "0038_lead_popup_logo"
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
    if cols and "variation_radius_px" not in cols:
        op.add_column(
            _TABLE,
            sa.Column("variation_radius_px", sa.Integer(), nullable=False, server_default="12"),
        )


def downgrade() -> None:
    if "variation_radius_px" in _cols():
        op.drop_column(_TABLE, "variation_radius_px")
